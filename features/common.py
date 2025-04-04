import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP

# Import necessary functions and config from parent directory files
# Use absolute imports assuming project root is in sys.path
import client
import config

def register(mcp: FastMCP):
    """Registers common tools and resources with the FastMCP instance."""

    @mcp.tool()
    def query_nerdgraph(nerdgraph_query: str, variables: Optional[Dict[str, Any]] = None) -> str:
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

        result = client.execute_nerdgraph_query(nerdgraph_query, variables)
        return client.format_json_response(result)

    @mcp.tool()
    def run_nrql_query(nrql: str, target_account_id: Optional[int] = None) -> str:
        """
        Executes a NRQL (New Relic Query Language) query.

        Args:
            nrql: The NRQL query string. Example: "SELECT count(*) FROM Transaction TIMESERIES"
            target_account_id: The New Relic Account ID to run the query against.
                               If omitted, uses the globally configured ACCOUNT_ID from environment variables.

        Returns:
            A JSON string containing the NRQL query result or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
        if not account_to_use:
             return json.dumps({"errors": [{"message": "Account ID must be provided either as an argument or via the NEW_RELIC_ACCOUNT_ID environment variable."}]})

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
                query # Included for reference
              }
            }
          }
        }
        """
        variables = {"accountId": account_to_use, "nrqlQuery": nrql}
        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)

    @mcp.resource("newrelic://account_details")
    def get_account_details() -> str:
        """Provides basic details for the configured New Relic account."""
        if not config.ACCOUNT_ID:
             return json.dumps({"error": "NEW_RELIC_ACCOUNT_ID not configured, cannot fetch account details."})

        query = f"""
        {{
          actor {{
            account(id: {config.ACCOUNT_ID}) {{
              id
              name
              # licenseKey # Avoid exposing sensitive data like license keys by default
            }}
          }}
        }}
        """
        result = client.execute_nerdgraph_query(query)
        # Filter data before returning to just the account info
        account_data = result.get("data", {}).get("actor", {}).get("account", None)
        if account_data:
            # Keep the 'data' wrapper for consistency maybe? Or return only account?
            # Let's return just the account dict within 'data' for cleaner resource output
            return json.dumps({"data": account_data}, indent=2)
        else:
             # Pass through errors if any, or provide a generic error
             if "errors" in result and result["errors"]:
                  return client.format_json_response(result)
             else:
                  return json.dumps({"errors": [{"message": "Could not fetch account details or account not found."}]}) 