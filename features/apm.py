import json
from typing import Optional
from fastmcp import FastMCP

# Use absolute imports
import client
import config

def register(mcp: FastMCP):
    """Registers APM-related tools."""

    @mcp.tool() # Was previously a resource, changed in last step
    def list_apm_applications(target_account_id: Optional[int] = None) -> str:
        """
        Lists APM applications for the specified or default account.

        Args:
            target_account_id: The account ID to query. Uses default (from env) if omitted.

        Returns:
            JSON string containing a list of APM applications or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
        if not account_to_use:
             return json.dumps({"errors": [{"message": "Account ID must be provided either as an argument or via NEW_RELIC_ACCOUNT_ID environment variable."}]})

        # Using entitySearch is generally more flexible than older APM-specific APIs
        search_query = f"accountId = {account_to_use} AND domain = 'APM' AND type = 'APPLICATION'"
        query = """
        query ($searchQuery: String!) {
          actor {
            entitySearch(query: $searchQuery, options: {limit: 250}) { # Increased limit slightly
              results {
                entities {
                  guid
                  name
                  language
                  reporting
                  alertSeverity
                  tags { key value }
                }
                nextCursor # TODO: Implement pagination for tools/resources if needed
              }
              count
            }
          }
        }
        """
        variables = {"searchQuery": search_query}
        result = client.execute_nerdgraph_query(query, variables)
        # Maybe filter results for clarity? Let's return the full structure for now.
        return client.format_json_response(result)

    # Add other APM-specific tools/resources here, e.g.,
    # - Get deployment markers
    # - Get key transactions
    # - Get instance details 