import httpx
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import logging
import json
import time
from datetime import datetime, timedelta

from .errors import NerdGraphError, ErrorCode, MCPError, ValidationError, RateLimitError
from .security import NRQLValidator, InputValidator, check_rate_limit
from .cache import get_cache, CacheKeyBuilder, QueryResultCache

logger = logging.getLogger(__name__)


class QueryComplexityAnalyzer:
    """Analyzes query complexity to prevent expensive operations"""
    
    MAX_QUERY_DEPTH = 10
    MAX_SELECTION_SETS = 100
    
    @staticmethod
    def analyze_complexity(query: str) -> Dict[str, Any]:
        """Analyze GraphQL query complexity"""
        # Simple heuristic-based analysis
        depth = query.count('{')
        selections = query.count('\n') + query.count(',')
        
        return {
            "depth": depth,
            "selections": selections,
            "estimated_cost": depth * selections,
            "is_complex": depth > QueryComplexityAnalyzer.MAX_QUERY_DEPTH or 
                         selections > QueryComplexityAnalyzer.MAX_SELECTION_SETS
        }


class NerdGraphClient:
    """Async NerdGraph client with retries, caching, and connection pooling"""
    
    # Class-level connection pools and reference counts
    _connection_pools: Dict[str, httpx.AsyncClient] = {}
    _pool_ref_counts: Dict[str, int] = {}
    _pool_lock = asyncio.Lock()
    
    def __init__(self, api_key: str, endpoint: str = "https://api.newrelic.com/graphql",
                 account_id: Optional[str] = None, timeout: float = 30.0,
                 max_connections: int = 20, enable_cache: bool = True):
        """Initialize the NerdGraph client
        
        Args:
            api_key: New Relic API key
            endpoint: NerdGraph endpoint URL
            account_id: Default account ID for rate limiting
            timeout: Request timeout in seconds
            max_connections: Maximum concurrent connections
            enable_cache: Whether to enable query result caching
        """
        # Validate API key
        self.api_key = InputValidator.validate_api_key(api_key)
        self.endpoint = endpoint
        self.account_id = account_id
        self.timeout = timeout
        self.max_connections = max_connections
        self.enable_cache = enable_cache
        
        # Initialize connection pool
        self._init_connection_pool()
        
        # Initialize cache if enabled
        self.cache = QueryResultCache(get_cache()) if enable_cache and get_cache() else None
        
        # Metrics
        self.request_count = 0
        self.error_count = 0
        self.total_latency = 0.0
    
    def _init_connection_pool(self):
        """Initialize or get connection pool for this endpoint"""
        self.pool_key = f"{self.endpoint}:{self.api_key[:8]}"
        
        if self.pool_key not in self._connection_pools:
            limits = httpx.Limits(
                max_keepalive_connections=self.max_connections,
                max_connections=self.max_connections * 2,
                keepalive_expiry=30.0
            )
            
            self._connection_pools[self.pool_key] = httpx.AsyncClient(
                headers={
                    "Api-Key": self.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "NewRelic-MCP-Server/1.0"
                },
                timeout=httpx.Timeout(self.timeout),
                limits=limits
            )
            self._pool_ref_counts[self.pool_key] = 0
        
        self.client = self._connection_pools[self.pool_key]
        self._pool_ref_counts[self.pool_key] += 1
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError))
    )
    async def query(self, query: str, variables: Optional[Dict[str, Any]] = None,
                   cache_ttl: int = 300, skip_cache: bool = False) -> Dict[str, Any]:
        """
        Execute a GraphQL query with retries and caching
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            cache_ttl: Cache time-to-live in seconds
            skip_cache: Whether to skip cache for this query
            
        Returns:
            Response data dictionary
            
        Raises:
            NerdGraphError: If the API returns errors
            ValidationError: For invalid inputs
            RateLimitError: If rate limit exceeded
            MCPError: For other errors
        """
        start_time = time.time()
        
        # Check rate limit
        account_id = self.account_id or (variables or {}).get('accountId', 'default')
        if not check_rate_limit(account_id):
            raise RateLimitError(
                "Rate limit exceeded for account",
                limit=100,
                reset_time=time.time() + 60
            )
        
        # Analyze query complexity
        complexity = QueryComplexityAnalyzer.analyze_complexity(query)
        if complexity["is_complex"]:
            logger.warning(f"Complex query detected: {complexity}")
            # Could reject or add to a slow queue
        
        # Check cache if enabled
        if self.cache and not skip_cache and self.enable_cache:
            cache_key = CacheKeyBuilder.build(
                "nerdgraph",
                query_hash=hash(query),
                variables_hash=hash(json.dumps(variables or {}, sort_keys=True))
            )
            
            cached_result = await self.cache.cache.get(cache_key)
            if cached_result is not None:
                logger.debug("Returning cached NerdGraph result")
                return cached_result
        
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables
        
        logger.debug(f"Executing NerdGraph query: {query[:100]}...")
        
        try:
            response = await self.client.post(self.endpoint, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Update metrics
            self.request_count += 1
            self.total_latency += time.time() - start_time
            
            # Check for GraphQL errors
            if "errors" in data and data["errors"]:
                self.error_count += 1
                logger.error(f"NerdGraph errors: {data['errors']}")
                raise NerdGraphError(
                    "GraphQL query failed",
                    graphql_errors=data["errors"],
                    query=query[:500]
                )
            
            result = data.get("data", {})
            
            # Cache successful result if enabled
            if self.cache and not skip_cache and self.enable_cache:
                await self.cache.cache.set(cache_key, result, cache_ttl)
            
            return result
            
        except httpx.TimeoutException as e:
            self.error_count += 1
            logger.error("NerdGraph request timed out")
            raise MCPError(
                ErrorCode.NERDGRAPH_TIMEOUT,
                "NerdGraph request timed out",
                {"timeout": self.timeout},
                cause=e
            )
        except httpx.HTTPStatusError as e:
            self.error_count += 1
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text[:500]}")
            
            # Handle specific status codes
            if e.response.status_code == 429:
                raise RateLimitError("NerdGraph API rate limit exceeded")
            elif e.response.status_code == 401:
                raise MCPError(
                    ErrorCode.AUTHENTICATION_FAILED,
                    "Invalid API key",
                    cause=e
                )
            else:
                raise MCPError(
                    ErrorCode.NERDGRAPH_ERROR,
                    f"HTTP {e.response.status_code} error",
                    {"status_code": e.response.status_code},
                    cause=e
                )
        except json.JSONDecodeError as e:
            self.error_count += 1
            logger.error(f"Failed to decode JSON response: {e}")
            raise MCPError(
                ErrorCode.NERDGRAPH_INVALID_RESPONSE,
                "Invalid JSON response from NerdGraph",
                cause=e
            )
    
    async def batch_query(self, queries: Dict[str, Tuple[str, Optional[Dict]]],
                         cache_ttl: int = 300) -> Dict[str, Any]:
        """Execute multiple queries in a single request
        
        Args:
            queries: Dictionary of {alias: (query, variables)} pairs
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Dictionary of {alias: result} pairs
        """
        # Rate limit check for batch queries
        account_id = self.account_id or 'batch'
        if not check_rate_limit(account_id):
            raise RateLimitError("Rate limit exceeded for batch query")
        
        # Build a combined query
        combined_parts = []
        combined_variables = {}
        
        for i, (alias, (query, variables)) in enumerate(queries.items()):
            # Validate alias to prevent injection
            if not alias.isidentifier():
                raise ValidationError(f"Invalid alias: {alias}")
            
            # Extract just the query body
            query_body = query.strip()
            if query_body.startswith("query"):
                brace_pos = query_body.find("{")
                if brace_pos != -1:
                    query_body = query_body[brace_pos+1:].rstrip("}")
            
            combined_parts.append(f'{alias}: {query_body}')
            
            # Merge variables with unique prefixes
            if variables:
                for var_name, var_value in variables.items():
                    combined_variables[f"{alias}_{var_name}"] = var_value
        
        combined_query = "query { " + " ".join(combined_parts) + " }"
        
        result = await self.query(combined_query, combined_variables, cache_ttl=cache_ttl)
        return result
    
    async def execute_nrql(self, nrql: str, account_id: int, 
                          cache_ttl: int = 300) -> Dict[str, Any]:
        """Execute NRQL query with validation and caching
        
        Args:
            nrql: NRQL query string
            account_id: New Relic account ID
            cache_ttl: Cache TTL in seconds
            
        Returns:
            Query results
        """
        # Validate NRQL query
        validated_nrql = NRQLValidator.validate_nrql(nrql)
        validated_account_id = InputValidator.validate_account_id(account_id)
        
        query = """
        query($accountId: Int!, $nrql: Nrql!) {
            actor {
                account(id: $accountId) {
                    nrql(query: $nrql) {
                        results
                        metadata {
                            facets
                            eventTypes
                            messages
                            timeWindow {
                                begin
                                end
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "accountId": validated_account_id,
            "nrql": validated_nrql
        }
        
        return await self.query(query, variables, cache_ttl=cache_ttl)
    
    async def close(self):
        """Close the HTTP client gracefully"""
        async with self._pool_lock:
            if hasattr(self, "pool_key") and self.pool_key in self._connection_pools:
                self._pool_ref_counts[self.pool_key] -= 1
                if self._pool_ref_counts[self.pool_key] <= 0:
                    await self.client.aclose()
                    del self._connection_pools[self.pool_key]
                    del self._pool_ref_counts[self.pool_key]
                    logger.debug(f"Closed connection pool for {self.pool_key}")
    
    @classmethod
    async def close_all_pools(cls):
        """Close all connection pools (call on shutdown)"""
        async with cls._pool_lock:
            for client in cls._connection_pools.values():
                await client.aclose()
            cls._connection_pools.clear()
            cls._pool_ref_counts.clear()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        avg_latency = self.total_latency / self.request_count if self.request_count > 0 else 0
        error_rate = self.error_count / self.request_count if self.request_count > 0 else 0
        
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": error_rate,
            "average_latency_ms": avg_latency * 1000,
            "connection_pool_size": len(self._connection_pools)
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()