"""Main client implementations for the UDS API."""

import asyncio
from typing import Any, Dict, Optional, Type, TypeVar, Union
from urllib.parse import urljoin

import httpx
from tenacity import (
    AsyncRetrying,
    RetryError,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .models import APIError, ClientConfig, HealthStatus
from .services.discovery import AsyncDiscoveryService, SyncDiscoveryService
from .services.patterns import AsyncPatternsService, SyncPatternsService
from .services.query import AsyncQueryService, SyncQueryService
from .services.dashboard import AsyncDashboardService, SyncDashboardService

T = TypeVar("T")


class BaseClient:
    """Base client with common functionality."""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        self.config = config or ClientConfig()
        self._setup_headers()
    
    def _setup_headers(self) -> None:
        """Set up common headers."""
        self.headers = {
            "User-Agent": self.config.user_agent,
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            self.headers["Authorization"] = f"Bearer {self.config.api_key}"
    
    def _build_url(self, path: str) -> str:
        """Build full URL from base and path."""
        return urljoin(self.config.base_url, path.lstrip("/"))
    
    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        if response.status_code < 400:
            return
        
        try:
            error_data = response.json()
            raise APIError(
                error=error_data.get("error", "unknown_error"),
                message=error_data.get("message", "Unknown error occurred"),
                details=error_data.get("details"),
                status_code=response.status_code,
            )
        except (ValueError, KeyError):
            raise APIError(
                error="http_error",
                message=f"HTTP {response.status_code}: {response.text}",
                status_code=response.status_code,
            )


class AsyncUDSClient(BaseClient):
    """Async client for the UDS API."""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        super().__init__(config)
        self._client: Optional[httpx.AsyncClient] = None
        
        # Initialize service clients
        self.discovery = AsyncDiscoveryService(self)
        self.patterns = AsyncPatternsService(self)
        self.query = AsyncQueryService(self)
        self.dashboard = AsyncDashboardService(self)
    
    async def __aenter__(self) -> "AsyncUDSClient":
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            headers=self.headers,
            timeout=self.config.timeout,
        )
        return self
    
    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    @property
    def client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self.headers,
                timeout=self.config.timeout,
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        url = self._build_url(path)
        request_headers = {**self.headers, **(headers or {})}
        
        async def _make_request() -> httpx.Response:
            response = await self.client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=request_headers,
            )
            self._handle_error_response(response)
            return response
        
        # Configure retry logic
        retry = AsyncRetrying(
            stop=stop_after_attempt(self.config.max_retries),
            wait=wait_exponential_jitter(
                initial=self.config.retry_wait,
                max=self.config.retry_max_wait,
            ),
            retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
            reraise=True,
        )
        
        try:
            async for attempt in retry:
                with attempt:
                    return await _make_request()
        except RetryError:
            # Last attempt failed, re-raise the original exception
            return await _make_request()
        
        # This should never be reached, but satisfies type checker
        raise RuntimeError("Unexpected retry behavior")
    
    async def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a GET request."""
        response = await self.request("GET", path, params=params)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    async def post(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a POST request."""
        response = await self.request("POST", path, json=json)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    async def put(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a PUT request."""
        response = await self.request("PUT", path, json=json)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    async def delete(self, path: str) -> None:
        """Make a DELETE request."""
        await self.request("DELETE", path)
    
    async def health(self) -> HealthStatus:
        """Check the health of the API."""
        return await self.get("/health", response_model=HealthStatus)
    
    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        self.config.api_key = api_key
        self._setup_headers()
        if self._client:
            self._client.headers.update(self.headers)


class SyncUDSClient(BaseClient):
    """Synchronous client for the UDS API."""
    
    def __init__(self, config: Optional[ClientConfig] = None):
        super().__init__(config)
        self._client = httpx.Client(
            headers=self.headers,
            timeout=self.config.timeout,
        )
        
        # Initialize service clients
        self.discovery = SyncDiscoveryService(self)
        self.patterns = SyncPatternsService(self)
        self.query = SyncQueryService(self)
        self.dashboard = SyncDashboardService(self)
    
    def __enter__(self) -> "SyncUDSClient":
        """Context manager entry."""
        return self
    
    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self._client.close()
    
    def close(self) -> None:
        """Close the HTTP client."""
        self._client.close()
    
    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """Make an HTTP request with retry logic."""
        url = self._build_url(path)
        request_headers = {**self.headers, **(headers or {})}
        
        # For sync client, we'll use a simple retry loop
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                response = self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=request_headers,
                )
                self._handle_error_response(response)
                return response
            except (httpx.NetworkError, httpx.TimeoutException) as e:
                last_error = e
                if attempt < self.config.max_retries - 1:
                    # Exponential backoff with jitter
                    wait_time = min(
                        self.config.retry_wait * (2 ** attempt),
                        self.config.retry_max_wait,
                    )
                    import random
                    import time
                    
                    jitter = wait_time * 0.25 * (random.random() * 2 - 1)
                    time.sleep(wait_time + jitter)
        
        # All retries failed
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected retry behavior")
    
    def get(
        self,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a GET request."""
        response = self.request("GET", path, params=params)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    def post(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a POST request."""
        response = self.request("POST", path, json=json)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    def put(
        self,
        path: str,
        *,
        json: Optional[Dict[str, Any]] = None,
        response_model: Optional[Type[T]] = None,
    ) -> Union[Dict[str, Any], T]:
        """Make a PUT request."""
        response = self.request("PUT", path, json=json)
        data = response.json()
        
        if response_model:
            return response_model(**data)
        return data
    
    def delete(self, path: str) -> None:
        """Make a DELETE request."""
        self.request("DELETE", path)
    
    def health(self) -> HealthStatus:
        """Check the health of the API."""
        return self.get("/health", response_model=HealthStatus)
    
    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        self.config.api_key = api_key
        self._setup_headers()
        self._client.headers.update(self.headers)