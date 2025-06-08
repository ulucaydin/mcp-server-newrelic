"""
Telemetry and observability for the MCP server itself
"""

import time
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from functools import wraps
import asyncio
from collections import defaultdict
import json

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects metrics about MCP server operations"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.metrics = {
            "tool_calls": defaultdict(int),
            "tool_errors": defaultdict(int),
            "tool_duration_ms": defaultdict(list),
            "resource_access": defaultdict(int),
            "session_count": 0,
            "account_switches": 0,
            "start_time": datetime.utcnow()
        }
        self._lock = asyncio.Lock()
    
    async def record_tool_call(self, tool_name: str, duration_ms: float, 
                              success: bool, error: Optional[str] = None):
        """Record a tool execution
        
        Args:
            tool_name: Name of the tool
            duration_ms: Execution time in milliseconds
            success: Whether the call succeeded
            error: Optional error message
        """
        async with self._lock:
            self.metrics["tool_calls"][tool_name] += 1
            self.metrics["tool_duration_ms"][tool_name].append(duration_ms)
            
            if not success:
                self.metrics["tool_errors"][tool_name] += 1
                if error:
                    error_key = f"{tool_name}_errors"
                    if error_key not in self.metrics:
                        self.metrics[error_key] = []
                    self.metrics[error_key].append({
                        "timestamp": datetime.utcnow().isoformat(),
                        "error": error[:500]  # Truncate long errors
                    })
            
            # Keep only last 1000 duration samples per tool
            if len(self.metrics["tool_duration_ms"][tool_name]) > 1000:
                self.metrics["tool_duration_ms"][tool_name] = \
                    self.metrics["tool_duration_ms"][tool_name][-1000:]
    
    async def record_resource_access(self, resource_uri: str):
        """Record resource access
        
        Args:
            resource_uri: URI of the accessed resource
        """
        async with self._lock:
            self.metrics["resource_access"][resource_uri] += 1
    
    async def record_session_created(self):
        """Record a new session creation"""
        async with self._lock:
            self.metrics["session_count"] += 1
    
    async def record_account_switch(self):
        """Record an account switch"""
        async with self._lock:
            self.metrics["account_switches"] += 1
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of collected metrics
        
        Returns:
            Dictionary with metrics summary
        """
        async with self._lock:
            uptime_seconds = (datetime.utcnow() - self.metrics["start_time"]).total_seconds()
            
            summary = {
                "uptime_seconds": uptime_seconds,
                "total_tool_calls": sum(self.metrics["tool_calls"].values()),
                "total_errors": sum(self.metrics["tool_errors"].values()),
                "session_count": self.metrics["session_count"],
                "account_switches": self.metrics["account_switches"],
                "tools": {}
            }
            
            # Calculate per-tool statistics
            for tool_name, call_count in self.metrics["tool_calls"].items():
                durations = self.metrics["tool_duration_ms"].get(tool_name, [])
                errors = self.metrics["tool_errors"].get(tool_name, 0)
                
                tool_stats = {
                    "calls": call_count,
                    "errors": errors,
                    "error_rate": errors / call_count if call_count > 0 else 0,
                    "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                    "p95_duration_ms": self._percentile(durations, 95) if durations else 0,
                    "max_duration_ms": max(durations) if durations else 0
                }
                
                summary["tools"][tool_name] = tool_stats
            
            # Resource access stats
            summary["resources"] = dict(self.metrics["resource_access"])
            
            return summary
    
    def _percentile(self, values: list, percentile: float) -> float:
        """Calculate percentile of a list of values"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]


# Global metrics collector instance
_metrics_collector = MetricsCollector()


def track_tool_execution(func: Callable) -> Callable:
    """Decorator to track tool execution metrics
    
    Args:
        func: Async function to track
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        start_time = time.time()
        success = False
        error = None
        
        try:
            result = await func(*args, **kwargs)
            success = True
            return result
        except Exception as e:
            error = str(e)
            logger.error(f"Tool {tool_name} failed: {error}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            await _metrics_collector.record_tool_call(
                tool_name, duration_ms, success, error
            )
    
    return wrapper


def track_resource_access(func: Callable) -> Callable:
    """Decorator to track resource access
    
    Args:
        func: Async function to track
        
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Try to extract resource URI from function arguments
        resource_uri = kwargs.get("uri") or (args[0] if args else "unknown")
        await _metrics_collector.record_resource_access(str(resource_uri))
        return await func(*args, **kwargs)
    
    return wrapper


async def get_telemetry_summary() -> Dict[str, Any]:
    """Get current telemetry summary
    
    Returns:
        Telemetry metrics summary
    """
    return await _metrics_collector.get_metrics_summary()


async def record_session_created():
    """Record a new session creation"""
    await _metrics_collector.record_session_created()


async def record_account_switch():
    """Record an account switch"""
    await _metrics_collector.record_account_switch()


class TelemetryPlugin:
    """Plugin to expose telemetry as MCP tools"""
    
    @staticmethod
    def register(app, services):
        """Register telemetry tools"""
        
        @app.tool()
        async def get_server_metrics() -> Dict[str, Any]:
            """Get metrics about the MCP server's own performance
            
            Returns:
                Server metrics including tool usage, performance, and errors
            """
            return await get_telemetry_summary()
        
        @app.resource("mcp://telemetry/metrics")
        async def telemetry_metrics_resource() -> str:
            """Raw telemetry metrics in JSON format"""
            metrics = await get_telemetry_summary()
            return json.dumps(metrics, indent=2)
        
        # Export functions for other modules to use
        services["telemetry"] = {
            "track_tool": track_tool_execution,
            "track_resource": track_resource_access,
            "record_session": record_session_created,
            "record_account_switch": record_account_switch
        }