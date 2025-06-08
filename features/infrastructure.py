import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
import logging
import sys
import os
import time

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import PluginBase

logger = logging.getLogger(__name__)


class InfrastructurePlugin(PluginBase):
    """Infrastructure monitoring tools"""
    
    # Plugin metadata for enhanced plugin system
    metadata = {
        "name": "InfrastructurePlugin",
        "version": "1.0.0",
        "description": "Monitor infrastructure components like hosts, containers, and processes",
        "author": "New Relic MCP Team",
        "dependencies": [],  # No dependencies on other plugins
        "required_services": ["nerdgraph", "entity_definitions"],
        "provides_services": [],
        "config_schema": {
            "type": "object",
            "properties": {
                "max_hosts": {"type": "integer", "default": 500},
                "enable_container_monitoring": {"type": "boolean", "default": True},
                "enable_kubernetes_monitoring": {"type": "boolean", "default": True}
            }
        },
        "enabled": True,
        "priority": 50
    }
    
    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register infrastructure-related tools"""
        
        nerdgraph = services["nerdgraph"]
        default_account_id = services.get("account_id")
        entity_defs = services.get("entity_definitions")
        
        @app.tool()
        async def list_hosts(
            target_account_id: Optional[int] = None,
            filter_tag: Optional[Dict[str, str]] = None
        ) -> str:
            """
            List infrastructure hosts
            
            Args:
                target_account_id: Account ID to query
                filter_tag: Optional tag filter (e.g., {"environment": "production"})
                
            Returns:
                JSON string with host information
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return json.dumps({"errors": [{"message": "Account ID required"}]})
            
            # Build search query
            search_parts = [f"accountId = {account_to_use}", "domain = 'INFRA'", "type = 'HOST'"]
            
            if filter_tag:
                for key, value in filter_tag.items():
                    search_parts.append(f"tags.`{key}` = '{value}'")
            
            search_query = " AND ".join(search_parts)
            
            query = """
            query($searchQuery: String!) {
                actor {
                    entitySearch(query: $searchQuery, options: {limit: 500}) {
                        results {
                            entities {
                                guid
                                name
                                ... on InfrastructureHostEntity {
                                    systemMemoryBytes
                                    processorCount
                                    agentVersion
                                    kernelVersion
                                    operatingSystem
                                    reporting
                                    alertSeverity
                                    recentAlertViolations {
                                        alertSeverity
                                        violationId
                                        openedAt
                                        label
                                    }
                                }
                                tags { key value }
                            }
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
                logger.error(f"Failed to list hosts: {e}")
                return json.dumps({"errors": [{"message": str(e)}]})
        
        @app.tool()
        async def get_host_metrics(
            hostname: str,
            metrics: Optional[List[str]] = None,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get performance metrics for a host
            
            Args:
                hostname: Name of the host
                metrics: List of metrics to fetch (defaults to key metrics)
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with metric values
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Default to key infrastructure metrics
            if not metrics:
                metrics = [
                    "cpu_percent",
                    "memory_percent", 
                    "disk_used_percent",
                    "network_transmit_bytes_per_second",
                    "network_receive_bytes_per_second"
                ]
            
            results = {"host": hostname, "time_range": time_range, "metrics": {}}
            
            # Build queries for each metric
            metric_queries = {
                "cpu_percent": f"SELECT average(cpuPercent) FROM SystemSample WHERE hostname = '{hostname}' {time_range}",
                "memory_percent": f"SELECT average(memoryUsedPercent) FROM SystemSample WHERE hostname = '{hostname}' {time_range}",
                "disk_used_percent": f"SELECT average(diskUsedPercent) FROM SystemSample WHERE hostname = '{hostname}' {time_range}",
                "network_transmit_bytes_per_second": f"SELECT average(transmitBytesPerSecond) FROM NetworkSample WHERE hostname = '{hostname}' {time_range}",
                "network_receive_bytes_per_second": f"SELECT average(receiveBytesPerSecond) FROM NetworkSample WHERE hostname = '{hostname}' {time_range}",
                "load_average": f"SELECT average(loadAverageOneMinute) FROM SystemSample WHERE hostname = '{hostname}' {time_range}"
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
                        
                        if nrql_results and len(nrql_results) > 0:
                            # Extract the value from the first result
                            first_result = nrql_results[0]
                            if "average" in first_result:
                                results["metrics"][metric] = first_result["average"]
                            else:
                                results["metrics"][metric] = first_result
                        else:
                            results["metrics"][metric] = None
                            
                    except Exception as e:
                        logger.error(f"Failed to fetch {metric}: {e}")
                        results["metrics"][metric] = {"error": str(e)}
                else:
                    results["metrics"][metric] = {"error": "Unknown metric"}
            
            return results
        
        @app.tool()
        async def get_container_metrics(
            container_name: Optional[str] = None,
            host: Optional[str] = None,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get Docker container metrics
            
            Args:
                container_name: Name of the container (optional)
                host: Host running the container (optional)
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with container metrics
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build WHERE clause
            where_parts = []
            if container_name:
                where_parts.append(f"containerName = '{container_name}'")
            if host:
                where_parts.append(f"hostname = '{host}'")
            
            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            # Query for container metrics
            nrql = f"""
            SELECT 
                average(cpuPercent) as cpu_percent,
                average(memoryUsagePercent) as memory_percent,
                sum(networkRxBytesPerSecond) as network_rx_bytes,
                sum(networkTxBytesPerSecond) as network_tx_bytes,
                uniqueCount(containerId) as container_count
            FROM ContainerSample 
            {where_clause}
            {time_range}
            FACET containerName, hostname
            LIMIT 100
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
                    "time_range": time_range,
                    "filter": {
                        "container_name": container_name,
                        "host": host
                    },
                    "containers": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get container metrics: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_kubernetes_metrics(
            cluster_name: Optional[str] = None,
            namespace: Optional[str] = None,
            time_range: str = "SINCE 1 hour ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get Kubernetes cluster and pod metrics
            
            Args:
                cluster_name: Name of the K8s cluster (optional)
                namespace: Kubernetes namespace (optional)
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with Kubernetes metrics
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            results = {
                "time_range": time_range,
                "filter": {
                    "cluster": cluster_name,
                    "namespace": namespace
                }
            }
            
            # Build WHERE clause
            where_parts = []
            if cluster_name:
                where_parts.append(f"clusterName = '{cluster_name}'")
            if namespace:
                where_parts.append(f"namespaceName = '{namespace}'")
            
            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            # Query for pod metrics
            pod_query = f"""
            SELECT 
                average(cpuCoresUtilization) as avg_cpu_cores,
                average(memoryWorkingSetUtilization) as avg_memory_util,
                uniqueCount(podName) as pod_count,
                sum(restartCount) as total_restarts
            FROM K8sPodSample
            {where_clause}
            {time_range}
            FACET namespaceName, deploymentName
            LIMIT 50
            """
            
            # Query for node metrics
            node_query = f"""
            SELECT 
                average(cpuUsedCores) as avg_cpu_used,
                average(memoryUsedBytes) / 1e9 as avg_memory_gb,
                uniqueCount(nodeName) as node_count
            FROM K8sNodeSample
            {where_clause}
            {time_range}
            """
            
            try:
                # Execute both queries
                batch_queries = {
                    "pods": ("""
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
                        "nrql": pod_query
                    }),
                    "nodes": ("""
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
                        "nrql": node_query
                    })
                }
                
                batch_results = await nerdgraph.batch_query(batch_queries)
                
                results["pods"] = batch_results.get("pods", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                results["nodes"] = batch_results.get("nodes", {}).get("actor", {}).get("account", {}).get("nrql", {}).get("results", [])
                
                return results
                
            except Exception as e:
                logger.error(f"Failed to get Kubernetes metrics: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_process_metrics(
            hostname: str,
            process_name: Optional[str] = None,
            top_n: int = 10,
            time_range: str = "SINCE 5 minutes ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get process-level metrics for a host
            
            Args:
                hostname: Name of the host
                process_name: Optional process name filter
                top_n: Number of top processes to return
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with process metrics
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build WHERE clause
            where_parts = [f"hostname = '{hostname}'"]
            if process_name:
                where_parts.append(f"processDisplayName LIKE '%{process_name}%'")
            
            where_clause = " AND ".join(where_parts)
            
            nrql = f"""
            SELECT 
                average(cpuPercent) as cpu_percent,
                average(memoryResidentSizeBytes) / 1e6 as memory_mb,
                uniqueCount(processId) as process_count
            FROM ProcessSample
            WHERE {where_clause}
            {time_range}
            FACET processDisplayName, commandLine
            LIMIT {top_n}
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
                    "host": hostname,
                    "time_range": time_range,
                    "process_filter": process_name,
                    "processes": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get process metrics: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_disk_usage(
            hostname: Optional[str] = None,
            mount_point: Optional[str] = None,
            threshold_percent: Optional[float] = None,
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get disk usage information for hosts
            
            Args:
                hostname: Optional host filter
                mount_point: Optional mount point filter (e.g., "/", "/var")
                threshold_percent: Only show disks above this usage percentage
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with disk usage information
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build WHERE clause
            where_parts = []
            if hostname:
                where_parts.append(f"hostname = '{hostname}'")
            if mount_point:
                where_parts.append(f"mountPoint = '{mount_point}'")
            if threshold_percent is not None:
                where_parts.append(f"diskUsedPercent > {threshold_percent}")
            
            where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
            
            nrql = f"""
            SELECT 
                latest(diskUsedPercent) as used_percent,
                latest(diskUsedBytes) / 1e9 as used_gb,
                latest(diskTotalBytes) / 1e9 as total_gb,
                latest(diskFreeBytes) / 1e9 as free_gb
            FROM StorageSample
            {where_clause}
            SINCE 5 minutes ago
            FACET hostname, mountPoint, filesystemType
            LIMIT 100
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
                
                # Sort by usage percentage
                sorted_results = sorted(
                    nrql_results, 
                    key=lambda x: x.get("latest.diskUsedPercent", 0), 
                    reverse=True
                )
                
                return {
                    "filter": {
                        "hostname": hostname,
                        "mount_point": mount_point,
                        "threshold_percent": threshold_percent
                    },
                    "disk_usage": sorted_results,
                    "total_disks": len(sorted_results)
                }
                
            except Exception as e:
                logger.error(f"Failed to get disk usage: {e}")
                return {"error": str(e)}
        
        @app.tool()
        async def get_network_interfaces(
            hostname: str,
            interface_name: Optional[str] = None,
            time_range: str = "SINCE 30 minutes ago",
            target_account_id: Optional[int] = None
        ) -> Dict[str, Any]:
            """
            Get network interface statistics
            
            Args:
                hostname: Host to query
                interface_name: Optional interface filter (e.g., "eth0")
                time_range: NRQL time range
                target_account_id: Optional account ID override
                
            Returns:
                Dictionary with network interface metrics
            """
            account_to_use = target_account_id or default_account_id
            if not account_to_use:
                return {"error": "Account ID required"}
            
            # Build WHERE clause
            where_parts = [f"hostname = '{hostname}'"]
            if interface_name:
                where_parts.append(f"interfaceName = '{interface_name}'")
            
            where_clause = " AND ".join(where_parts)
            
            nrql = f"""
            SELECT 
                average(receiveBytesPerSecond) / 1e6 as avg_rx_mbps,
                average(transmitBytesPerSecond) / 1e6 as avg_tx_mbps,
                max(receiveBytesPerSecond) / 1e6 as max_rx_mbps,
                max(transmitBytesPerSecond) / 1e6 as max_tx_mbps,
                sum(receiveErrors) as rx_errors,
                sum(transmitErrors) as tx_errors
            FROM NetworkSample
            WHERE {where_clause}
            {time_range}
            FACET interfaceName
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
                    "host": hostname,
                    "time_range": time_range,
                    "interfaces": nrql_results
                }
                
            except Exception as e:
                logger.error(f"Failed to get network interfaces: {e}")
                return {"error": str(e)}
        
        @app.resource("newrelic://infrastructure/summary")
        async def infrastructure_summary() -> str:
            """Get a summary of infrastructure health"""
            if not default_account_id:
                return json.dumps({"error": "Account ID not configured"})
            
            try:
                # Query for infrastructure summary
                summary_query = """
                query($accountId: Int!) {
                    actor {
                        account(id: $accountId) {
                            hosts: nrql(query: "SELECT uniqueCount(hostname) FROM SystemSample SINCE 1 hour ago") {
                                results
                            }
                            containers: nrql(query: "SELECT uniqueCount(containerId) FROM ContainerSample SINCE 1 hour ago") {
                                results
                            }
                            criticalHosts: nrql(query: "SELECT uniqueCount(hostname) FROM SystemSample WHERE cpuPercent > 90 OR memoryUsedPercent > 90 SINCE 5 minutes ago") {
                                results
                            }
                        }
                    }
                }
                """
                
                variables = {"accountId": int(default_account_id)}
                result = await nerdgraph.query(summary_query, variables)
                
                account_data = result.get("actor", {}).get("account", {})
                
                summary = {
                    "infrastructure_summary": {
                        "total_hosts": account_data.get("hosts", {}).get("results", [{}])[0].get("uniqueCount.hostname", 0),
                        "total_containers": account_data.get("containers", {}).get("results", [{}])[0].get("uniqueCount.containerId", 0),
                        "critical_hosts": account_data.get("criticalHosts", {}).get("results", [{}])[0].get("uniqueCount.hostname", 0),
                        "timestamp": time.time()
                    }
                }
                
                return json.dumps(summary, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to get infrastructure summary: {e}")
                return json.dumps({"error": str(e)})


# Keep legacy register function
def register(mcp: FastMCP):
    """Legacy registration function"""
    plugin = InfrastructurePlugin()
    services = {
        "nerdgraph": None,
        "account_id": os.getenv("NEW_RELIC_ACCOUNT_ID"),
        "entity_definitions": None
    }
    plugin.register(mcp, services)