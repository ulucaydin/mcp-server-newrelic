import json
from typing import List, Optional, Dict, Any
from fastmcp import FastMCP

# Use absolute imports
import client
import config

def register(mcp: FastMCP):
    """Registers entity-related tools, resources, and prompts."""

    @mcp.tool()
    def search_entities(
        name: Optional[str] = None,
        entity_type: Optional[str] = None,
        domain: Optional[str] = None,
        tags: Optional[List[Dict[str, str]]] = None, # Example: [{"key": "env", "value": "production"}]
        target_account_id: Optional[int] = None, # Allow overriding account ID for search
        limit: int = 50
    ) -> str:
        """
        Searches for New Relic entities based on various criteria.

        Args:
            name: Filter by entity name (supports fuzzy matching).
            entity_type: Filter by entity type (e.g., 'APPLICATION', 'HOST', 'DASHBOARD').
            domain: Filter by entity domain (e.g., 'APM', 'INFRA', 'BROWSER').
            tags: Filter by tags. A list of dictionaries, each with 'key' and 'value'.
            target_account_id: Explicitly search within this account ID. If omitted, searches across accounts accessible by the API key.
            limit: Maximum number of entities to return (default 50).

        Returns:
            A JSON string with the search results (list of entities with basic details) or errors.
        """
        conditions = []
        # Add account condition *only* if target_account_id is specified
        if target_account_id is not None:
             # Ensure it's a valid integer if provided
             try:
                 acc_id = int(target_account_id)
                 conditions.append(f"accountId = {acc_id}")
             except (ValueError, TypeError):
                  return json.dumps({"errors": [{"message": f"Invalid target_account_id: {target_account_id}. Must be an integer."}]})
        elif config.ACCOUNT_ID:
             # If no target is specified, but a global one exists, maybe default to it?
             # Or keep it broad? Let's keep it broad unless specified.
             # conditions.append(f"accountId = {config.ACCOUNT_ID}")
             print("Searching across all accessible accounts. Specify target_account_id to limit.")


        if name:
            # Basic escaping for potential single quotes in name
            escaped_name = name.replace("'", "\\'")
            conditions.append(f"name LIKE '%{escaped_name}%'")
        if entity_type:
            conditions.append(f"type = '{entity_type}'")
        if domain:
            conditions.append(f"domain = '{domain}'")
        if tags:
            tag_conditions = []
            for tag in tags:
                if isinstance(tag, dict) and "key" in tag and "value" in tag:
                     # Escape single quotes in tag values too
                     escaped_tag_value = str(tag['value']).replace("'", "\\'")
                     tag_conditions.append(f"tags.`{tag['key']}` = '{escaped_tag_value}'") # Use backticks for keys that might have special chars
            if tag_conditions:
                 conditions.append(" AND ".join(tag_conditions))

        # Require at least one *non-account* search criterion
        # Need to check if conditions list only contains the accountId condition
        non_account_conditions_exist = any(not cond.strip().startswith("accountId") for cond in conditions)
        if not non_account_conditions_exist:
             return json.dumps({"errors": [{"message": "At least one non-account search criterion (name, type, domain, tags) must be provided."}]})


        search_query = " AND ".join(conditions)

        query = """
        query ($searchQuery: String!, $limit: Int) {
          actor {
            # entitySearch doesn't allow specifying account ID directly in the call, only via the query string
            entitySearch(query: $searchQuery, options: {limit: $limit}) {
              results {
                entities {
                  guid
                  name
                  entityType
                  domain
                  accountId
                  tags { key value }
                }
                nextCursor
              }
              count
            }
          }
        }
        """
        variables = {"searchQuery": search_query, "limit": limit}
        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)

    @mcp.resource("newrelic://entity/{guid}")
    def get_entity_details(guid: str) -> str:
        """
        Retrieves detailed information for a specific New Relic entity by its GUID.

        Args:
            guid: The unique identifier (GUID) of the entity.

        Returns:
            A JSON string containing the entity's details or errors.
        """
        if not guid or not isinstance(guid, str):
            return json.dumps({"errors": [{"message": "Valid entity GUID must be provided."}]})

        # This query is now quite large, maybe split fragments later if needed
        query = """
        query ($guid: EntityGuid!) {
          actor {
            entity(guid: $guid) {
              guid
              name
              accountId
              domain
              entityType
              tags { key value }
              # Common fields first
              reporting
              permalink
              alertSeverity
              recentAlertViolations(count: 5) { # Get recent violations
                violationId
                label
                level
                openedAt
                closedAt
              }
              alertConditions { # Get associated conditions
                    name
                    id
                    enabled
                    policy { id name } # Link to policy
              }
              relationships { # Get relationships
                source { entity { guid name type } }
                target { entity { guid name type } }
                type
              }

              # Type-specific fragments
              ... on ApmApplicationEntity {
                language
                settings { applicationName }
                runningAgentVersions { minVersion maxVersion }
                applicationInstances(filter: { state: "RUNNING" }, count: 5) { # Get a few running instances
                    host
                    port
                    agentSettings { agentVersion }
                }
              }
              ... on BrowserApplicationEntity {
                servingAgentVersion
                settings { applicationName }
                applicationId # Old ID
              }
              ... on MobileApplicationEntity {
                 # Add relevant mobile fields, e.g., platform, versions
              }
               ... on InfrastructureHostEntity {
                hostSummary {
                    cpuUtilizationPercent
                    diskUsedPercent
                    memoryUsedPercent
                    networkReceiveRate
                    networkTransmitRate
                    # Add more summary fields if useful
                }
                operatingSystem
                systemMemoryBytes
                processorCount
                kernelVersion
                agentVersion
              }
               ... on SyntheticMonitorEntity {
                monitorType
                period
                status
                locationsPublic
                locationsPrivate { guid name }
                script { # Get script for scripted monitors
                    text # Careful: might be large/sensitive
                }
              }
               ... on DashboardEntity {
                # Fetch dashboard pages/widgets if needed (can be complex)
                pages(count: 10) { # Get first 10 pages
                    guid
                    name
                    widgets(count: 10) { # Get first 10 widgets per page
                        id
                        title
                        visualization # Type of widget
                        # rawConfiguration # JSON config, might be too verbose
                    }
                }
               }
              # Add fragments for other entity types as needed (Lambda, K8s, etc.)

            }
          }
        }
        """
        variables = {"guid": guid}
        result = client.execute_nerdgraph_query(query, variables)
        return client.format_json_response(result)

    @mcp.prompt()
    def generate_entity_search_query(entity_name: str, entity_domain: Optional[str] = None, entity_type: Optional[str] = None, target_account_id: Optional[int] = None) -> str:
        """Generates a NerdGraph `entitySearch` query string condition to find an entity."""
        conditions = []
        if target_account_id:
             try:
                 conditions.append(f"accountId = {int(target_account_id)}")
             except (ValueError, TypeError):
                  return f"Error: Invalid target_account_id '{target_account_id}'"
        elif config.ACCOUNT_ID:
             # Default to configured account if one exists and none is specified
             conditions.append(f"accountId = {config.ACCOUNT_ID}")


        # Basic escaping for the name within the query string
        escaped_name = entity_name.replace("'", "\\'")
        conditions.append(f"name = '{escaped_name}'") # Use exact match for prompt generation? Or LIKE? Let's try exact first.

        if entity_domain:
            conditions.append(f"domain = '{entity_domain}'")
        if entity_type:
            conditions.append(f"type = '{entity_type}'")

        search_query_string = " AND ".join(conditions)
        # Return just the query *string* part
        return search_query_string 