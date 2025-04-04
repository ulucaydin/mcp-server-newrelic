import json
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP

# Use absolute imports
import client
import config
from features import entities # Absolute import for sibling module

def register(mcp: FastMCP):
    """Registers Synthetics-related tools and resources."""

    @mcp.tool() # Was resource
    def list_synthetics_monitors(target_account_id: Optional[int] = None) -> str:
        """
        Lists Synthetic monitors for the specified or default account.

        Args:
            target_account_id: The account ID to query. Uses default if omitted.

        Returns:
            JSON string containing a list of Synthetic monitors or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
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
        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)

    # Note: The resource URI is technically defined in entities.py, but having a specific
    # function here might be clearer for discovery, even if it just calls the other one.
    # Alternatively, just document that users should use `get_entity_details` from entities.
    # Let's keep it simple and rely on the entities module's resource.
    # If more specific synthetics details were needed beyond the entity fragment,
    # a dedicated resource/tool here would make sense.

    # @mcp.resource("newrelic://synthetics/monitor/{guid}")
    # def get_synthetics_monitor_details(guid: str) -> str:
    #     """Retrieves detailed information for a specific Synthetic monitor by its GUID."""
    #     # Reuse the generic entity detail function from the entities module
    #     return entities.get_entity_details(guid=guid) # Need to call the registered function


    @mcp.tool()
    def create_simple_browser_monitor(
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
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
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

        result = client.execute_nerdgraph_query(mutation, variables)
        return client.format_json_response(result)

    # Add tools/resources for other monitor types (scripted, API tests)
    # Add tools for updating/deleting monitors

    # @mcp.resource("newrelic://synthetics/monitor/{guid}")
    # def get_synthetics_monitor_details(guid: str) -> str:
    #     """Retrieves detailed information for a specific Synthetic monitor by its GUID."""
    #     # Reuse the generic entity detail function from the entities module
    #     return entities.get_entity_details(guid=guid) # Need to call the registered function 