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


class APMPlugin(PluginBase):
    """Application Performance Monitoring tools"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register APM-related tools"""
        
        nerdgraph = services["nerdgraph"]
        default_account_id = services.get("account_id")
        entity_defs = services.get("entity_definitions")
        
        @app.tool()
        async def list_apm_applications(target_account_id: Optional[int] = None) -> str:
            """
            Lists APM applications for a given account.

            Args:
                target_account_id: The New Relic Account ID to query.
                                  If omitted, uses the default account.

            Returns:
                A JSON string containing a list of APM applications with their details.
            """
            account_to_use = target_account_id if target_account_id is not None else default_account_id
            if not account_to_use:
                return json.dumps({"errors": [{"message": "Account ID must be provided."}]})
            
            # Using entitySearch for flexibility
            search_query = f"accountId = {account_to_use} AND domain = 'APM' AND type = 'APPLICATION'"
            query = """
            query ($searchQuery: String!) {
              actor {
                entitySearch(query: $searchQuery, options: {limit: 250}) {
                  results {
                    entities {
                      guid
                      name
                      language
                      reporting
                      alertSeverity
                      tags { key value }
                      ... on ApmApplicationEntity {
                        runningAgentVersions {
                          minVersion
                          maxVersion
                        }
                      }
                    }
                    nextCursor
                  }
                  count
                }
              }
            }
            """
            
            try:
                variables = {"searchQuery": search_query}
                result = await nerdgraph.query(query, variables)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Failed to list APM applications: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})
        
        @app.tool()
        async def get_apm_metrics(
            application_name: str,
            metrics: Optional[List[str]] = None,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get performance metrics for an APM application
            
            Args:
                application_name: Name of the APM application
                metrics: List of metrics to fetch (defaults to golden metrics)
                time_range: NRQL time range (e.g., "SINCE 1 hour ago")
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with metric values
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Default to common APM metrics if none specified
            if not metrics:
                metrics = [
                    "throughput",
                    "response_time",
                    "error_rate",
                    "apdex"
                ]
            
            results = {"application": application_name, "time_range": time_range, "metrics": {}}
            
            # Build queries for each metric
            metric_queries = {
                "throughput": f"SELECT rate(count(*), 1 minute) FROM Transaction WHERE appName = '{application_name}' {time_range}",
                "response_time": f"SELECT average(duration) * 1000 FROM Transaction WHERE appName = '{application_name}' {time_range}",
                "error_rate": f"SELECT percentage(count(*), WHERE error IS true) FROM Transaction WHERE appName = '{application_name}' {time_range}",
                "apdex": f"SELECT apdex(duration, t: 0.5) FROM Transaction WHERE appName = '{application_name}' {time_range}"
            }
            
            # Execute queries
            for metric in metrics:
                if metric in metric_queries:
                    try:
                        query = """
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
                            "nrql": metric_queries[metric]
                        }
                        
                        result = await nerdgraph.query(query, variables)
                        nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                        
                        if nrql_results:
                            results["metrics"][metric] = nrql_results[0]
                        else:
                            results["metrics"][metric] = None
                            
                    except Exception as e:
                        logger.error(f"Failed to fetch {metric}: {e}")
                        results["metrics"][metric] = {"error": str(e)}
                else:
                    results["metrics"][metric] = {"error": "Unknown metric"}
            
            return results
        
        @app.tool()
        async def get_apm_transactions(
            application_name: str,
            transaction_type: str = "Web",
            limit: int = 10,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get top transactions for an APM application
            
            Args:
                application_name: Name of the APM application
                transaction_type: Type of transactions (Web or NonWeb)
                limit: Number of transactions to return
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with transaction details
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Query for top transactions by volume
            nrql = f"""
            SELECT count(*), average(duration) * 1000 as avg_duration_ms, 
                   percentile(duration, 95) * 1000 as p95_duration_ms,
                   percentage(count(*), WHERE error IS true) as error_rate
            FROM Transaction 
            WHERE appName = '{application_name}' 
            AND transactionType = '{transaction_type}'
            {time_range}
            FACET name 
            LIMIT {limit}
            """
            
            try:
                query = """
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
                
                result = await nerdgraph.query(query, variables)
                nrql_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "application": application_name,
                    "transaction_type": transaction_type,
                    "time_range": time_range,
                    "transactions": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get transactions: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def compare_deployments(
            application_name: str,
            deployment_marker: Optional[str] = None,
            before_minutes: int = 30,
            after_minutes: int = 30,
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Compare application metrics before and after a deployment
            
            Args:
                application_name: Name of the APM application
                deployment_marker: Optional deployment marker/revision
                before_minutes: Minutes before deployment to analyze
                after_minutes: Minutes after deployment to analyze
                target_account_id: Optional account ID override
                
            Returns:
                Comparison of key metrics
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Get recent deployment
            deployment_query = """
            query($accountId: Int!, $appName: String!) {
                actor {
                    account(id: $accountId) {
                        nrql(query: $appName) {
                            results
                        }
                    }
                }
            }
            """
            
            # Build NRQL to find deployment
            find_deployment_nrql = f"""
            SELECT latest(timestamp), latest(revision), latest(user) 
            FROM Deployment 
            WHERE appName = '{application_name}'
            SINCE 24 hours ago
            """
            
            if deployment_marker:
                find_deployment_nrql += f" WHERE revision = '{deployment_marker}'"
            
            try:
                # Find deployment
                variables = {
                    "accountId": int(account_to_use),
                    "appName": find_deployment_nrql
                }
                
                deployment_result = await nerdgraph.query(deployment_query, variables)
                deployments = deployment_result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                if not deployments:
                    return {
                        "application": application_name,
                        "error": "No recent deployments found"
                    }
                
                # Get deployment timestamp
                deployment = deployments[0]
                deployment_time = deployment.get("latest.timestamp")
                
                if not deployment_time:
                    return {"error": "Could not determine deployment time"}
                
                # Compare metrics before and after
                metrics_to_compare = ["throughput", "response_time", "error_rate"]
                comparison = {
                    "application": application_name,
                    "deployment": {
                        "timestamp": deployment_time,
                        "revision": deployment.get("latest.revision"),
                        "user": deployment.get("latest.user")
                    },
                    "before": {},
                    "after": {},
                    "changes": {}
                }
                
                # Get metrics before deployment
                before_time = f"SINCE {deployment_time - before_minutes*60000} UNTIL {deployment_time}"
                after_time = f"SINCE {deployment_time} UNTIL {deployment_time + after_minutes*60000}"
                
                for period, time_clause in [("before", before_time), ("after", after_time)]:
                    period_metrics = await get_apm_metrics(
                        application_name=application_name,
                        metrics=metrics_to_compare,
                        time_range=time_clause,
                        target_account_id=account_to_use
                    )
                    
                    if "metrics" in period_metrics:
                        comparison[period] = period_metrics["metrics"]
                
                # Calculate changes
                for metric in metrics_to_compare:
                    before_val = comparison["before"].get(metric)
                    after_val = comparison["after"].get(metric)
                    
                    if before_val and after_val and isinstance(before_val, dict) and isinstance(after_val, dict):
                        # Extract numeric values - this depends on the metric structure
                        # This is simplified - real implementation would handle different metric types
                        comparison["changes"][metric] = "Comparison logic needed"
                
                return comparison
                
            except Exception as e:
                logger.error(f"Failed to compare deployments: {e}")
                return {"error": str(e)}


# Keep legacy register function
def register(mcp: FastMCP):
    """Legacy registration function"""
    plugin = APMPlugin()
    services = {
        "nerdgraph": None,
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID"),
        "entity_definitions": None
    }
    plugin.register(mcp, services)