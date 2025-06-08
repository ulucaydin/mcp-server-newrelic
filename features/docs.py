"""
Documentation search plugin for New Relic docs
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

from fastmcp import FastMCP

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plugin_loader import PluginBase
from core.docs_cache import DocsCache

logger = logging.getLogger(__name__)


class DocsPlugin(PluginBase):
    """Tools for searching and retrieving New Relic documentation"""

    metadata = {
        "name": "DocsPlugin",
        "version": "1.0.0",
        "description": "Search and retrieve New Relic documentation",
        "author": "New Relic MCP Team",
        "dependencies": [],
        "required_services": [],  # Docs cache is self-contained
        "provides_services": ["docs_cache"],
        "config_schema": {
            "type": "object",
            "properties": {
                "cache_dir": {"type": "string", "description": "Documentation cache directory"},
                "auto_update": {"type": "boolean", "default": False},
                "repo_url": {"type": "string", "description": "Documentation repository URL"}
            }
        },
        "enabled": True,
        "priority": 80,
    }

    @staticmethod
    def register(app: FastMCP, services: Dict[str, Any]):
        """Register documentation search tools"""
        
        # Get configuration
        config = services.get("config", {})
        cache_dir = config.get("cache_dir")
        
        # Initialize docs cache
        docs_cache = DocsCache(cache_dir=cache_dir)
        
        # Register the cache as a service for other plugins
        services["docs_cache"] = docs_cache
        
        @app.tool()
        async def search_docs(
            keyword: str, 
            limit: int = 5,
            include_whats_new: bool = True
        ) -> str:
            """
            Search the New Relic documentation for a keyword
            
            Args:
                keyword: Search term to look for
                limit: Maximum number of results (default: 5)
                include_whats_new: Include "What's New" posts in results
                
            Returns:
                JSON array of search results with title, excerpt, path, and URL
            """
            if not keyword:
                return json.dumps({
                    "error": "Keyword is required"
                })
            
            try:
                # Perform search
                results = docs_cache.search(keyword, limit=limit)
                
                # Filter out whats-new if requested
                if not include_whats_new:
                    results = [r for r in results if "whats-new" not in r.get("path", "")]
                
                # Enhance results with additional info
                for result in results:
                    # Add search relevance hint
                    if keyword.lower() in result.get("title", "").lower():
                        result["relevance"] = "high"
                    else:
                        result["relevance"] = "medium"
                
                return json.dumps({
                    "keyword": keyword,
                    "count": len(results),
                    "results": results
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Documentation search failed: {e}")
                return json.dumps({
                    "error": str(e),
                    "keyword": keyword
                })

        @app.resource("newrelic://docs/{path:path}")
        async def get_doc_content(path: str) -> str:
            """
            Get the content of a documentation file
            
            Args:
                path: Relative path to the documentation file
                
            Returns:
                Raw markdown content of the document
            """
            if not path:
                return json.dumps({
                    "error": "Path is required"
                })
            
            try:
                content = docs_cache.get_content(path)
                
                if not content:
                    return json.dumps({
                        "error": "Document not found",
                        "path": path
                    })
                
                # Return as JSON with metadata
                return json.dumps({
                    "path": path,
                    "content": content,
                    "length": len(content)
                })
                
            except Exception as e:
                logger.error(f"Failed to retrieve document: {e}")
                return json.dumps({
                    "error": str(e),
                    "path": path
                })

        @app.tool()
        async def update_docs_cache() -> str:
            """
            Manually update the documentation cache from the repository
            
            Returns:
                Status message about the update
            """
            try:
                docs_cache.update_cache()
                info = docs_cache.get_cache_info()
                
                return json.dumps({
                    "status": "success",
                    "message": "Documentation cache updated",
                    "cache_info": info
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to update docs cache: {e}")
                return json.dumps({
                    "status": "error",
                    "error": str(e)
                })

        @app.tool()
        async def get_docs_cache_info() -> str:
            """
            Get information about the documentation cache
            
            Returns:
                Cache statistics and status
            """
            try:
                info = docs_cache.get_cache_info()
                return json.dumps(info, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to get cache info: {e}")
                return json.dumps({
                    "error": str(e)
                })

        @app.resource("newrelic://docs/topics")
        async def list_doc_topics() -> str:
            """Get a list of main documentation topics"""
            
            # This is a curated list of main topics
            topics = {
                "getting_started": {
                    "title": "Getting Started",
                    "description": "Introduction to New Relic",
                    "keywords": ["setup", "install", "quickstart", "tutorial"]
                },
                "apm": {
                    "title": "APM (Application Performance Monitoring)",
                    "description": "Monitor application performance",
                    "keywords": ["application", "performance", "transactions", "errors"]
                },
                "infrastructure": {
                    "title": "Infrastructure Monitoring",
                    "description": "Monitor servers, hosts, and containers",
                    "keywords": ["server", "host", "cpu", "memory", "disk"]
                },
                "browser": {
                    "title": "Browser Monitoring",
                    "description": "Real user monitoring for web applications",
                    "keywords": ["browser", "javascript", "page load", "ajax"]
                },
                "mobile": {
                    "title": "Mobile Monitoring",
                    "description": "Monitor mobile applications",
                    "keywords": ["ios", "android", "mobile", "crash"]
                },
                "synthetics": {
                    "title": "Synthetic Monitoring",
                    "description": "Proactive monitoring with scripted checks",
                    "keywords": ["synthetic", "monitor", "scripted", "api test"]
                },
                "logs": {
                    "title": "Log Management",
                    "description": "Centralized log collection and analysis",
                    "keywords": ["logs", "logging", "log management"]
                },
                "alerts": {
                    "title": "Alerts and Applied Intelligence",
                    "description": "Intelligent alerting and incident management",
                    "keywords": ["alert", "incident", "notification", "threshold"]
                },
                "nrql": {
                    "title": "NRQL (New Relic Query Language)",
                    "description": "Query language for New Relic data",
                    "keywords": ["nrql", "query", "select", "from", "where"]
                },
                "distributed_tracing": {
                    "title": "Distributed Tracing",
                    "description": "Trace requests across distributed systems",
                    "keywords": ["trace", "distributed", "span", "latency"]
                },
                "kubernetes": {
                    "title": "Kubernetes Monitoring",
                    "description": "Monitor Kubernetes clusters and workloads",
                    "keywords": ["kubernetes", "k8s", "container", "pod", "cluster"]
                },
                "apis": {
                    "title": "APIs and Automation",
                    "description": "Programmatic access to New Relic",
                    "keywords": ["api", "graphql", "nerdgraph", "rest", "automation"]
                }
            }
            
            return json.dumps({
                "topics": topics,
                "count": len(topics)
            }, indent=2)

        # Log successful registration
        logger.info("DocsPlugin registered successfully")
        cache_info = docs_cache.get_cache_info()
        if cache_info.get("initialized"):
            logger.info(f"Documentation cache initialized at {cache_info.get('path')}")
        else:
            logger.warning("Documentation cache not fully initialized")


# Legacy support
def register(mcp: FastMCP):
    """Legacy registration function"""
    DocsPlugin.register(mcp, {})