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


class EntitiesPlugin(PluginBase):
    """Entity search and management plugin"""
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register entity-related tools and resources"""
        
        nerdgraph = services["nerdgraph"]
        entity_defs = services.get("entity_definitions")
        session_manager = services.get("session_manager")
        default_account_id = services.get("account_id")

        @app.tool()
        async def search_entities(
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
            elif default_account_id:
                # Use default account if available
                logger.info("Using default account for search. Specify target_account_id to search other accounts.")
                conditions.append(f"accountId = {default_account_id}")


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
                        tag_conditions.append(f"tags.`{tag['key']}` = '{escaped_tag_value}'")
                if tag_conditions:
                    conditions.append(" AND ".join(tag_conditions))
            
            # Require at least one search criterion
            if not conditions:
                return json.dumps({"errors": [{"message": "At least one search criterion must be provided."}]})
            
            search_query = " AND ".join(conditions)
            
            query = """
            query ($searchQuery: String!, $limit: Int) {
              actor {
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
            
            try:
                variables = {"searchQuery": search_query, "limit": limit}
                result = await nerdgraph.query(query, variables)
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Entity search failed: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.resource("newrelic://entity/{guid}")
        async def get_entity_details(guid: str) -> str:
            """
        Retrieves detailed information for a specific New Relic entity by its GUID.

        Args:
            guid: The unique identifier (GUID) of the entity.

        Returns:
            A JSON string containing the entity's details or errors.
        """
            if not guid or not isinstance(guid, str):
                return json.dumps({"errors": [{"message": "Valid entity GUID must be provided."}]})
            
            # Check session cache first
            if session_manager:
                session = session_manager.get_or_create_session()
                cached = session.get_cached_entity(guid)
                if cached:
                    logger.debug(f"Returning cached entity data for {guid}")
                    return json.dumps(cached, indent=2)
            
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
            try:
                variables = {"guid": guid}
                result = await nerdgraph.query(query, variables)
                
                # Cache the result
                if session_manager and "actor" in result and "entity" in result["actor"]:
                    session = session_manager.get_or_create_session()
                    session.cache_entity(guid, result)
                
                return json.dumps(result, indent=2)
            except Exception as e:
                logger.error(f"Failed to get entity details: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})

        @app.tool()
        async def get_entity_golden_signals(
            guid: str,
            duration: int = 3600
        ) -> Dict[str, Any]:
            """
            Get golden signals (key metrics) for an entity
            
            Args:
                guid: Entity GUID
                duration: Time window in seconds (default: 1 hour)
            
            Returns:
                Dictionary with golden signal values
            """
            if not entity_defs:
                return {"error": "Entity definitions not available"}
            
            # First get entity type
            entity_query = """
            query($guid: EntityGuid!) {
                actor {
                    entity(guid: $guid) {
                        type
                        entityType
                        name
                        domain
                    }
                }
            }
            """
            
            try:
                entity_result = await nerdgraph.query(entity_query, {"guid": guid})
                entity = entity_result.get("actor", {}).get("entity")
                
                if not entity:
                    return {"error": "Entity not found"}
                
                entity_type = entity["entityType"]
                
                # Get golden metrics definition
                golden_metrics = entity_defs.get_golden_metrics(entity_type)
                
                if not golden_metrics:
                    return {
                        "entity_guid": guid,
                        "entity_name": entity["name"],
                        "entity_type": entity_type,
                        "message": "No golden metrics defined for this entity type"
                    }
                
                # For now, return the metric definitions
                # In a full implementation, we would query each metric's value
                return {
                    "entity_guid": guid,
                    "entity_name": entity["name"],
                    "entity_type": entity_type,
                    "duration": duration,
                    "golden_metrics": golden_metrics
                }
                
            except Exception as e:
                logger.error(f"Failed to get golden signals: {e}")
                return {"error": str(e)}


# Keep legacy register function for backward compatibility
def register(mcp: FastMCP):
    """Legacy registration function - redirects to plugin"""
    plugin = EntitiesPlugin()
    # Create minimal services dict for legacy support
    services = {
        "nerdgraph": None,  # Would need to be provided
        "entity_definitions": None,
        "session_manager": None,
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID")
    }
    plugin.register(mcp, services) 