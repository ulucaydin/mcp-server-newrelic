import json
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import PluginBase

logger = logging.getLogger(__name__)


class SyntheticsPlugin(PluginBase):
    """Synthetic monitoring tools"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register synthetics-related tools"""
        
        nerdgraph = services["nerdgraph"]
        default_account_id = services.get("account_id")
        
        @app.tool()
        async def list_synthetics_monitors(target_account_id: Optional[int] = None) -> str:
            """
            Lists Synthetic monitors for the specified or default account.

            Args:
                target_account_id: The account ID to query. Uses default if omitted.

            Returns:
                JSON string containing a list of Synthetic monitors or errors.
            """
            account_to_use = target_account_id if target_account_id is not None else default_account_id
            if not account_to_use:
                 return json.dumps({"errors": [{"message": "Account ID must be provided."}]})

            search_query = f"accountId = {account_to_use} AND domain = 'SYNTH' AND type = 'MONITOR'"
            query = """
            query ($searchQuery: String!) {
              actor {
                entitySearch(query: $searchQuery, options: {limit: 250}) {
                  results {
                    entities {
                      guid
                      name
                      ... on SyntheticMonitorEntity { # Use fragment for specific fields
                        monitorType
                        period
                        status
                        locationsPublic # Array of strings
                        locationsPrivate { guid name } # Array of objects
                      }
                      tags { key value }
                    }
                    nextCursor
                  }
                  count
                }
              }
            }
            """
            variables = {"searchQuery": search_query}
            
            try:
                result = await nerdgraph.query(query, variables)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Failed to list synthetics monitors: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.tool()
        async def create_simple_browser_monitor(
            monitor_name: str,
            url: str,
            locations: List[str], # List of public location labels, e.g., ["AWS_US_EAST_1"]
            period: str = "EVERY_15_MINUTES", # e.g., EVERY_MINUTE, EVERY_5_MINUTES, etc.
            status: str = "ENABLED", # ENABLED or DISABLED
            target_account_id: Optional[int] = None,
            tags: Optional[List[Dict[str, str]]] = None # Example: [{"key": "team", "value": "frontend"}]
        ) -> str:
            """
            Creates a basic Synthetics 'SIMPLE_BROWSER' monitor.

            Args:
                monitor_name: Name for the new monitor.
                url: The URL the monitor should check.
                locations: List of public location labels (e.g., "AWS_US_EAST_1"). Find labels via NerdGraph or UI.
                period: Check frequency (e.g., "EVERY_MINUTE", "EVERY_5_MINUTES", "EVERY_15_MINUTES").
                status: Initial status ("ENABLED" or "DISABLED").
                target_account_id: The account ID where the monitor should be created. Uses default if omitted.
                tags: Optional list of tags (key-value dictionaries) to add to the monitor.

            Returns:
                JSON string with the result of the creation mutation (including the new monitor's GUID) or errors.
            """
            account_to_use = target_account_id if target_account_id is not None else default_account_id
            if not account_to_use:
                 return json.dumps({"errors": [{"message": "Account ID must be provided."}]})
            if not all([monitor_name, url, locations]):
                return json.dumps({"errors": [{"message": "monitor_name, url, and locations are required."}]})
            if not isinstance(locations, list) or not all(isinstance(loc, str) for loc in locations):
                 return json.dumps({"errors": [{"message": "locations must be a list of strings."}]})


            # Basic validation for period and status
            valid_periods = ["EVERY_MINUTE", "EVERY_5_MINUTES", "EVERY_10_MINUTES", "EVERY_15_MINUTES", "EVERY_30_MINUTES", "EVERY_HOUR", "EVERY_6_HOURS", "EVERY_12_HOURS", "EVERY_DAY"]
            if period not in valid_periods:
                 return json.dumps({"errors": [{"message": f"Invalid period '{period}'. Valid periods: {valid_periods}"}]})
            if status not in ["ENABLED", "DISABLED", "MUTED"]: # MUTED might also be valid
                 return json.dumps({"errors": [{"message": f"Invalid status '{status}'. Must be ENABLED or DISABLED."}]})

            mutation = """
            mutation ($accountId: Int!, $monitor: SyntheticsCreateSimpleBrowserMonitorInput!) {
              syntheticsCreateSimpleBrowserMonitor(accountId: $accountId, monitor: $monitor) {
                monitor {
                  guid
                  name
                  locations # Returns public locations
                  period
                  status
                  uri # The URL being monitored
                  type
                  tags { key value }
                }
                errors {
                  description
                  type
                }
              }
            }
            """
            monitor_input: Dict[str, Any] = {
                "name": monitor_name,
                "uri": url,
                "locations": {"public": locations}, # API expects locations under a 'public' key now
                "period": period,
                "status": status,
                # Add optional runtime settings if needed, defaults are usually okay
                # "runtime": {"runtimeType": "CHROME_BROWSER", "runtimeTypeVersion": "100", "scriptLanguage": "JAVASCRIPT"}
            }
            # Add optional tags if provided
            if tags and isinstance(tags, list):
                 # Ensure tags are in the correct format {"key": "...", "value": "..."}
                 valid_tags = [t for t in tags if isinstance(t, dict) and "key" in t and "value" in t]
                 if valid_tags:
                      monitor_input["tags"] = valid_tags # Synthetics tags are at the top level


            variables = {"accountId": account_to_use, "monitor": monitor_input}

            try:
                result = await nerdgraph.query(mutation, variables)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Failed to create synthetics monitor: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.tool()
        async def get_synthetics_results(
            monitor_guid: str,
            time_range: str = "SINCE 1 hour ago",
            limit: int = 10
        ) -> Dict[str, Any]:
            """
            Get recent check results for a synthetic monitor
            
            Args:
                monitor_guid: GUID of the synthetic monitor
                time_range: NRQL time range
                limit: Number of results to return
                
            Returns:
                Dictionary with check results
            """
            # Query for synthetic check results
            nrql = f"""
            SELECT monitorName, result, duration, locationLabel, timestamp
            FROM SyntheticCheck 
            WHERE entityGuid = '{monitor_guid}'
            {time_range}
            LIMIT {limit}
            """
            
            try:
                result = await nerdgraph.execute_nrql(
                    nrql=nrql,
                    account_id=int(default_account_id) if default_account_id else 0
                )
                
                check_results = result.get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return {
                    "monitor_guid": monitor_guid,
                    "time_range": time_range,
                    "check_results": check_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get synthetics results: {e}")
                return {"error": str(e)}


# Keep legacy register function
def register(mcp: FastMCP):
    """Legacy registration function"""
    plugin = SyntheticsPlugin()
    services = {
        "nerdgraph": None,
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID"),
    }
    plugin.register(mcp, services)