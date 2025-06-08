import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP
import logging
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import PluginBase

logger = logging.getLogger(__name__)


class CommonPlugin(PluginBase):
    """Common tools for NRQL and NerdGraph queries"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register common tools and resources"""
        
        nerdgraph = services["nerdgraph"]
        account_id = services.get("account_id")
        session_manager = services.get("session_manager")

        @app.tool()
        async def query_nerdgraph(nerdgraph_query: str, variables: Optional[Dict[str, Any]] = None) -> str:
            """
        Executes an arbitrary NerdGraph query against the New Relic API.
        Use this for queries not covered by specific tools/resources.

        Args:
            nerdgraph_query: The GraphQL query string. Can include variables defined in the 'variables' arg.
                             Example: 'query($accountId: Int!) { actor { account(id: $accountId) { name } } }'
            variables: An optional JSON dictionary of variables to pass with the query.
                       Example: {"accountId": 1234567}

        Returns:
            A JSON string representing the result of the query, including data and/or errors.
        """
            if not isinstance(nerdgraph_query, str) or not nerdgraph_query.strip():
                return json.dumps({"errors": [{"message": "Invalid or empty query provided."}]})
            
            try:
                result = await nerdgraph.query(nerdgraph_query, variables)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"NerdGraph query failed: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.tool()
        async def run_nrql_query(nrql: str, target_account_id: Optional[int] = None) -> str:
            """
        Executes a NRQL (New Relic Query Language) query.

        Args:
            nrql: The NRQL query string. Example: "SELECT count(*) FROM Transaction TIMESERIES"
            target_account_id: The New Relic Account ID to run the query against.
                               If omitted, uses the globally configured ACCOUNT_ID from environment variables.

        Returns:
            A JSON string containing the NRQL query result or errors.
        """
            account_to_use = target_account_id if target_account_id is not None else account_id
            if not account_to_use:
                return json.dumps({"errors": [{"message": "Account ID must be provided either as an argument or configured."}]})
            
            if not isinstance(nrql, str) or not nrql.strip():
                return json.dumps({"errors": [{"message": "Invalid or empty NRQL query provided."}]})
            
            query = """
            query ($accountId: Int!, $nrqlQuery: Nrql!) {
              actor {
                account(id: $accountId) {
                  nrql(query: $nrqlQuery) {
                    results
                    metadata {
                      facets
                      eventTypes
                      timeWindow {
                        begin
                        end
                        compareWith
                      }
                    }
                    totalResult
                    query
                  }
                }
              }
            }
            """
            
            try:
                variables = {"accountId": int(account_to_use), "nrqlQuery": nrql}
                result = await nerdgraph.query(query, variables)
                
                # Store in session history if available
                # if session_manager:
                #     session = session_manager.get_or_create_session()
                #     session.add_recent_query(nrql, result)
                
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"NRQL query failed: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.resource("newrelic://account_details")
        async def get_account_details() -> str:
            """Provides basic details for the configured New Relic account."""
            if not account_id:
                return json.dumps({"error": "Account ID not configured, cannot fetch account details."})
            
            query = f"""
            {{
              actor {{
                account(id: {account_id}) {{
                  id
                  name
                }}
              }}
            }}
            """
            
            try:
                result = await nerdgraph.query(query)
                account_data = result.get("actor", {}).get("account")
                
                if account_data:
                    return json.dumps({"data": account_data}, indent=2)
                else:
                    return json.dumps({"errors": [{"message": "Could not fetch account details."}]})
            except Exception as e:
                logger.error(f"Failed to fetch account details: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})


# Keep legacy register function for backward compatibility
def register(mcp: FastMCP):
    """Legacy registration function - redirects to plugin"""
    # This allows the old import style to still work
    plugin = CommonPlugin()
    # Create minimal services dict for legacy support
    services = {
        "nerdgraph": None,  # Would need to be provided
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID")
    }
    plugin.register(mcp, services) 