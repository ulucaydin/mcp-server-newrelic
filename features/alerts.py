import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP

import client
import config

def register(mcp: FastMCP):
    """Registers Alerts-related tools."""

    @mcp.tool() # Was resource
    def list_alert_policies(target_account_id: Optional[int] = None, policy_name_filter: Optional[str] = None) -> str:
        """
        Lists alert policies for the specified or default account, optionally filtering by name.

        Args:
            target_account_id: The account ID to query. Uses default if omitted.
            policy_name_filter: Filter policies where the name contains this string (case-insensitive).

        Returns:
            JSON string containing a list of alert policies or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
        if not account_to_use:
             return json.dumps({"errors": [{"message": "Account ID must be provided."}]})

        query = """
        query ($accountId: Int!, $cursor: String, $policyName: String) {
          actor {
            account(id: $accountId) {
              alerts {
                policiesSearch(cursor: $cursor, searchCriteria: {name: $policyName}) {
                  policies {
                    id
                    name
                    incidentPreference # PER_POLICY, PER_CONDITION, PER_CONDITION_AND_TARGET
                  }
                  nextCursor # Add pagination handling if needed
                  totalCount
                }
              }
            }
          }
        }
        """
        # Note: This query might need pagination for large numbers of policies.
        variables: Dict[str, Any] = {"accountId": account_to_use}
        if policy_name_filter:
             variables["policyName"] = policy_name_filter # Add filter only if provided

        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)


    @mcp.tool() # Was resource
    def list_open_incidents(target_account_id: Optional[int] = None, priority: Optional[str] = None) -> str:
        """
        Lists currently open alert incidents for the specified or default account.

        Args:
            target_account_id: The account ID to query. Uses default if omitted.
            priority: Filter by priority (e.g., 'CRITICAL', 'WARNING'). Must be uppercase.

        Returns:
            JSON string containing a list of open incidents or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
        if not account_to_use:
             return json.dumps({"errors": [{"message": "Account ID must be provided."}]})

        valid_priorities = ["CRITICAL", "WARNING", "INFO"] # Check NerdGraph docs for exact enum values
        if priority and priority.upper() not in valid_priorities:
             return json.dumps({"errors": [{"message": f"Invalid priority '{priority}'. Valid priorities: {valid_priorities}"}]})

        query = """
        query ($accountId: Int!, $cursor: String, $priority: AlertsIncidentPriority) {
          actor {
            account(id: $accountId) {
              alerts {
                incidents(cursor: $cursor, filter: {priority: $priority, state: OPEN}) {
                  incidents {
                    incidentId
                    title
                    priority
                    state # Should always be OPEN based on filter
                    policyName
                    conditionName
                    entity { guid name type } # Entity that triggered the incident
                    startedAt
                    updatedAt
                    description # Added description
                    violationUrl # Added violation URL
                  }
                  nextCursor # Add pagination handling if needed
                  totalCount
                }
              }
            }
          }
        }
        """
        variables: Dict[str, Any] = {"accountId": account_to_use}
        if priority:
            variables["priority"] = priority.upper() # Ensure uppercase for enum

        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)

    @mcp.tool()
    def acknowledge_alert_incident(incident_id: int, target_account_id: Optional[int] = None, message: Optional[str] = None) -> str:
        """
        Acknowledges an open alert incident.

        Args:
            incident_id: The ID of the incident to acknowledge (integer).
            target_account_id: The account ID where the incident occurred. Uses default if omitted.
            message: Optional message to include with the acknowledgement.

        Returns:
            JSON string with the result of the acknowledgement mutation or errors.
        """
        account_to_use = target_account_id if target_account_id is not None else config.ACCOUNT_ID
        if not account_to_use:
             return json.dumps({"errors": [{"message": "Account ID must be provided."}]})
        if not isinstance(incident_id, int) or incident_id <= 0:
             return json.dumps({"errors": [{"message": "Valid positive integer incident_id is required."}]})

        mutation = """
        mutation ($accountId: Int!, $incidentId: Int!, $message: String) {
          alertsIncidentAcknowledge(accountId: $accountId, incidentId: $incidentId, message: $message) {
            incident {
              incidentId
              state # Should transition to ACKNOWLEDGED
              acknowledgedBy
              acknowledgedAt
              title
            }
            errors {
              description
              type
            }
          }
        }
        """
        variables: Dict[str, Any] = {"accountId": account_to_use, "incidentId": incident_id}
        if message:
            variables["message"] = message

        result = client.execute_nerdgraph_query(mutation, variables)
        return client.format_json_response(result)

    # Add tools for:
    # - Creating/Managing Alert Policies/Conditions/Notification Channels
    # - Closing incidents 