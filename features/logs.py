import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
import logging
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import PluginBase

logger = logging.getLogger(__name__)


class LogsPlugin(PluginBase):
    """Log monitoring and search tools"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register logs-related tools"""
        
        nerdgraph = services["nerdgraph"]
        default_account_id = services.get("account_id")
        
        @app.tool()
        async def search_logs(
            query: str,
            time_range: str = "SINCE 1 hour ago",
            limit: int = 100,
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Search logs using NRQL
            
            Args:
                query: Search query (will be added to WHERE clause)
                time_range: NRQL time range
                limit: Maximum number of results
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with log entries
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build NRQL query
            nrql = f"""
            SELECT *
            FROM Log
            WHERE {query}
            {time_range}
            LIMIT {limit}
            """
            
            try:
                query_gql = """
                query($accountId: Int!, $nrql: Nrql!) {
                    actor {
                        account(id: $accountId) {
                            nrql(query: $nrql) {
                                results
                            }
                        }
                    }
                }
                """
                
                variables = {
                    "accountId": int(account_to_use),
                    "nrql": nrql
                }
                
                result = await nerdgraph.query(query_gql, variables)
                nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "query": query,
                    "time_range": time_range,
                    "count": len(nrql_results),
                    "logs": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to search logs: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_log_patterns(
            application_name: Optional[str] = None,
            hostname: Optional[str] = None,
            log_level: Optional[str] = None,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Analyze log patterns and get summary statistics
            
            Args:
                application_name: Filter by application
                hostname: Filter by host
                log_level: Filter by log level (ERROR, WARN, INFO, etc.)
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with log pattern analysis
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build WHERE clause
            where_parts = []
            if application_name:
                where_parts.append(f"application = '{application_name}'")
            if hostname:
                where_parts.append(f"hostname = '{hostname}'")
            if log_level:
                where_parts.append(f"level = '{log_level.upper()}'")
            
            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            # Query for log patterns
            nrql = f"""
            SELECT 
                count(*) as log_count,
                uniqueCount(message) as unique_messages,
                percentage(count(*), WHERE level = 'ERROR') as error_rate,
                percentage(count(*), WHERE level = 'WARN') as warn_rate
            FROM Log
            {where_clause}
            {time_range}
            FACET level, application, hostname
            LIMIT 50
            """
            
            try:
                query_gql = """
                query($accountId: Int!, $nrql: Nrql!) {
                    actor {
                        account(id: $accountId) {
                            nrql(query: $nrql) {
                                results
                            }
                        }
                    }
                }
                """
                
                variables = {
                    "accountId": int(account_to_use),
                    "nrql": nrql
                }
                
                result = await nerdgraph.query(query_gql, variables)
                nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                # Also get top error messages if requested
                error_messages = []
                if not log_level or log_level.upper() == "ERROR":
                    error_query = f"""
                    SELECT count(*), latest(timestamp)
                    FROM Log
                    {where_clause + ' AND ' if where_clause else 'WHERE'} level = 'ERROR'
                    {time_range}
                    FACET message
                    LIMIT 10
                    """
                    
                    error_result = await nerdgraph.query(query_gql, {
                        "accountId": int(account_to_use),
                        "nrql": error_query
                    })
                    
                    error_messages = error_result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "filter": {
                        "application": application_name,
                        "hostname": hostname,
                        "log_level": log_level
                    },
                    "time_range": time_range,
                    "patterns": nrql_results,
                    "top_errors": error_messages
                }
                
            except Exception as e:
                logger.error(f"Failed to get log patterns: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_log_timeline(
            query: str,
            bucket_size: str = "5 minutes",
            time_range: str = "SINCE 6 hours ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get log volume timeline
            
            Args:
                query: Filter query (WHERE clause)
                bucket_size: Time bucket size (e.g., "5 minutes", "1 hour")
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with timeline data
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            nrql = f"""
            SELECT count(*) 
            FROM Log
            WHERE {query}
            {time_range}
            TIMESERIES {bucket_size}
            """
            
            try:
                query_gql = """
                query($accountId: Int!, $nrql: Nrql!) {
                    actor {
                        account(id: $accountId) {
                            nrql(query: $nrql) {
                                results
                            }
                        }
                    }
                }
                """
                
                variables = {
                    "accountId": int(account_to_use),
                    "nrql": nrql
                }
                
                result = await nerdgraph.query(query_gql, variables)
                nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "query": query,
                    "bucket_size": bucket_size,
                    "time_range": time_range,
                    "timeline": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get log timeline: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def analyze_error_logs(
            time_range: str = "SINCE 1 hour ago",
            group_by: Optional[List[str]] = None,
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Analyze error logs and provide insights
            
            Args:
                time_range: NRQL time range
                group_by: Fields to group by (e.g., ["application", "error.class"])
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with error analysis
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Default grouping
            if not group_by:
                group_by = ["application", "hostname", "error.class"]
            
            facet_clause = f"FACET {', '.join(group_by)}" if group_by else ""
            
            # Main error analysis query
            error_query = f"""
            SELECT 
                count(*) as error_count,
                uniqueCount(message) as unique_errors,
                latest(timestamp) as last_seen,
                rate(count(*), 1 minute) as errors_per_minute
            FROM Log
            WHERE level = 'ERROR'
            {time_range}
            {facet_clause}
            LIMIT 100
            """
            
            # Error trend query
            trend_query = f"""
            SELECT count(*)
            FROM Log
            WHERE level = 'ERROR'
            {time_range}
            TIMESERIES 15 minutes
            """
            
            try:
                # Execute both queries
                batch_queries = {
                    "errors": ("""
                        query($accountId: Int!, $nrql: Nrql!) {
                            actor {
                                account(id: $accountId) {
                                    nrql(query: $nrql) {
                                        results
                                    }
                                }
                            }
                        }
                    """, {
                        "accountId": int(account_to_use),
                        "nrql": error_query
                    }),
                    "trend": ("""
                        query($accountId: Int!, $nrql: Nrql!) {
                            actor {
                                account(id: $accountId) {
                                    nrql(query: $nrql) {
                                        results
                                    }
                                }
                            }
                        }
                    """, {
                        "accountId": int(account_to_use),
                        "nrql": trend_query
                    })
                }
                
                batch_results = await nerdgraph.batch_query(batch_queries)
                
                error_results = batch_results.get("errors", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                trend_results = batch_results.get("trend", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                # Sort errors by count
                sorted_errors = sorted(
                    error_results,
                    key=lambda x: x.get("count", 0),
                    reverse=True
                )
                
                return {
                    "time_range": time_range,
                    "group_by": group_by,
                    "top_errors": sorted_errors[:10],
                    "error_trend": trend_results,
                    "total_error_groups": len(error_results)
                }
                
            except Exception as e:
                logger.error(f"Failed to analyze error logs: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def tail_logs(
            query: str = "*",
            since_minutes: int = 5,
            limit: int = 50,
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get recent logs (similar to tail -f)
            
            Args:
                query: Filter query
                since_minutes: How many minutes back to look
                limit: Maximum number of logs
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with recent log entries
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build query
            where_clause = f"WHERE {query}" if query != "*" else ""
            
            nrql = f"""
            SELECT 
                timestamp,
                level,
                message,
                hostname,
                application,
                error.class,
                error.message
            FROM Log
            {where_clause}
            SINCE {since_minutes} minutes ago
            ORDER BY timestamp DESC
            LIMIT {limit}
            """
            
            try:
                query_gql = """
                query($accountId: Int!, $nrql: Nrql!) {
                    actor {
                        account(id: $accountId) {
                            nrql(query: $nrql) {
                                results
                            }
                        }
                    }
                }
                """
                
                variables = {
                    "accountId": int(account_to_use),
                    "nrql": nrql
                }
                
                result = await nerdgraph.query(query_gql, variables)
                nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "query": query,
                    "since_minutes": since_minutes,
                    "count": len(nrql_results),
                    "logs": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to tail logs: {e}")
                return {"error": str(e)}


# Keep legacy register function
def register(mcp: FastMCP):
    """Legacy registration function"""
    plugin = LogsPlugin()
    services = {
        "nerdgraph": None,
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID")
    }
    plugin.register(mcp, services)