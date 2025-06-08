"""
Health checks and metrics export for the MCP server
"""

import asyncio
import time
import os
import psutil
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY
from prometheus_client.core import CollectorRegistry

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Individual health check"""
    
    def __init__(self, name: str, check_fn: Callable, 
                 critical: bool = True, timeout: float = 5.0):
        """
        Initialize health check
        
        Args:
            name: Check name
            check_fn: Async function that returns (status, details)
            critical: Whether this check is critical for overall health
            timeout: Check timeout in seconds
        """
        self.name = name
        self.check_fn = check_fn
        self.critical = critical
        self.timeout = timeout
        self.last_status = HealthStatus.HEALTHY
        self.last_check_time = None
        self.consecutive_failures = 0
    
    async def run(self) -> Dict[str, Any]:
        """Run the health check"""
        start_time = time.time()
        
        try:
            # Run check with timeout
            status, details = await asyncio.wait_for(
                self.check_fn(),
                timeout=self.timeout
            )
            
            duration = time.time() - start_time
            self.last_check_time = datetime.utcnow()
            self.last_status = status
            
            if status == HealthStatus.HEALTHY:
                self.consecutive_failures = 0
            else:
                self.consecutive_failures += 1
            
            return {
                "name": self.name,
                "status": status.value,
                "critical": self.critical,
                "duration_ms": duration * 1000,
                "details": details,
                "consecutive_failures": self.consecutive_failures,
                "last_check": self.last_check_time.isoformat()
            }
            
        except asyncio.TimeoutError:
            self.consecutive_failures += 1
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY.value,
                "critical": self.critical,
                "error": "Health check timed out",
                "timeout": self.timeout,
                "consecutive_failures": self.consecutive_failures
            }
        except Exception as e:
            self.consecutive_failures += 1
            logger.error(f"Health check {self.name} failed: {e}")
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY.value,
                "critical": self.critical,
                "error": str(e),
                "consecutive_failures": self.consecutive_failures
            }


class HealthMonitor:
    """Manages health checks and metrics"""
    
    def __init__(self):
        """Initialize health monitor"""
        self.checks: List[HealthCheck] = []
        self.start_time = time.time()
        
        # Initialize Prometheus metrics
        self._init_metrics()
    
    def _init_metrics(self):
        """Initialize Prometheus metrics"""
        # Request metrics
        self.request_counter = Counter(
            'mcp_requests_total',
            'Total number of MCP requests',
            ['tool', 'status']
        )
        
        self.request_duration = Histogram(
            'mcp_request_duration_seconds',
            'Request duration in seconds',
            ['tool']
        )
        
        # System metrics
        self.cpu_usage = Gauge('mcp_cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('mcp_memory_usage_bytes', 'Memory usage in bytes')
        self.active_connections = Gauge('mcp_active_connections', 'Active connections')
        
        # Cache metrics
        self.cache_hits = Counter('mcp_cache_hits_total', 'Total cache hits')
        self.cache_misses = Counter('mcp_cache_misses_total', 'Total cache misses')
        self.cache_size = Gauge('mcp_cache_size_bytes', 'Cache size in bytes')
        
        # NerdGraph metrics
        self.nerdgraph_requests = Counter(
            'mcp_nerdgraph_requests_total',
            'Total NerdGraph requests',
            ['status']
        )
        self.nerdgraph_latency = Histogram(
            'mcp_nerdgraph_latency_seconds',
            'NerdGraph request latency'
        )
        
        # Health check metrics
        self.health_check_status = Gauge(
            'mcp_health_check_status',
            'Health check status (1=healthy, 0=unhealthy)',
            ['check_name']
        )
    
    def add_check(self, check: HealthCheck):
        """Add a health check"""
        self.checks.append(check)
    
    async def run_checks(self) -> Dict[str, Any]:
        """Run all health checks"""
        results = await asyncio.gather(
            *[check.run() for check in self.checks],
            return_exceptions=True
        )
        
        # Process results
        checks_results = []
        overall_status = HealthStatus.HEALTHY
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Health check exception: {result}")
                checks_results.append({
                    "status": HealthStatus.UNHEALTHY.value,
                    "error": str(result)
                })
                overall_status = HealthStatus.UNHEALTHY
            else:
                checks_results.append(result)
                
                # Update metrics
                status_value = 1 if result["status"] == HealthStatus.HEALTHY.value else 0
                self.health_check_status.labels(
                    check_name=result["name"]
                ).set(status_value)
                
                # Update overall status
                if result["status"] != HealthStatus.HEALTHY.value:
                    if result.get("critical", True):
                        overall_status = HealthStatus.UNHEALTHY
                    elif overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
        
        # Update system metrics
        self._update_system_metrics()
        
        return {
            "status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "checks": checks_results
        }
    
    def _update_system_metrics(self):
        """Update system metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.cpu_usage.set(cpu_percent)
            
            # Memory usage
            memory = psutil.Process().memory_info()
            self.memory_usage.set(memory.rss)
            
        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")
    
    def get_metrics(self) -> bytes:
        """Get Prometheus metrics"""
        return generate_latest(REGISTRY)
    
    def record_request(self, tool: str, duration: float, success: bool):
        """Record a request metric"""
        status = "success" if success else "error"
        self.request_counter.labels(tool=tool, status=status).inc()
        self.request_duration.labels(tool=tool).observe(duration)
    
    def record_cache_access(self, hit: bool):
        """Record cache access"""
        if hit:
            self.cache_hits.inc()
        else:
            self.cache_misses.inc()
    
    def update_cache_size(self, size_bytes: int):
        """Update cache size metric"""
        self.cache_size.set(size_bytes)
    
    def record_nerdgraph_request(self, duration: float, success: bool):
        """Record NerdGraph request"""
        status = "success" if success else "error"
        self.nerdgraph_requests.labels(status=status).inc()
        self.nerdgraph_latency.observe(duration)


# Standard health checks
async def check_nerdgraph_connection(nerdgraph_client) -> tuple[HealthStatus, Dict[str, Any]]:
    """Check NerdGraph API connectivity"""
    try:
        start = time.time()
        result = await nerdgraph_client.query("{ actor { user { email } } }")
        latency = (time.time() - start) * 1000
        
        if result and "actor" in result:
            return HealthStatus.HEALTHY, {"latency_ms": latency}
        else:
            return HealthStatus.UNHEALTHY, {"error": "Invalid response"}
            
    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


async def check_cache_health(cache) -> tuple[HealthStatus, Dict[str, Any]]:
    """Check cache health"""
    if not cache:
        return HealthStatus.DEGRADED, {"message": "Cache not configured"}
    
    try:
        # Test cache operations
        test_key = "_health_check_test"
        test_value = {"timestamp": time.time()}
        
        await cache.set(test_key, test_value, ttl=10)
        retrieved = await cache.get(test_key)
        await cache.delete(test_key)
        
        if retrieved == test_value:
            # Get cache stats if available
            stats = {}
            if hasattr(cache, 'get_stats'):
                stats = cache.get_stats()
            
            return HealthStatus.HEALTHY, stats
        else:
            return HealthStatus.UNHEALTHY, {"error": "Cache verification failed"}
            
    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


async def check_disk_space() -> tuple[HealthStatus, Dict[str, Any]]:
    """Check available disk space"""
    try:
        disk = psutil.disk_usage('/')
        percent_used = disk.percent
        
        details = {
            "percent_used": percent_used,
            "free_gb": disk.free / (1024**3),
            "total_gb": disk.total / (1024**3)
        }
        
        if percent_used > 90:
            return HealthStatus.UNHEALTHY, details
        elif percent_used > 80:
            return HealthStatus.DEGRADED, details
        else:
            return HealthStatus.HEALTHY, details
            
    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


async def check_memory_usage() -> tuple[HealthStatus, Dict[str, Any]]:
    """Check memory usage"""
    try:
        memory = psutil.virtual_memory()
        process_memory = psutil.Process().memory_info()
        
        details = {
            "system_percent": memory.percent,
            "process_mb": process_memory.rss / (1024**2),
            "available_gb": memory.available / (1024**3)
        }
        
        if memory.percent > 90 or process_memory.rss > 1024**3:  # 1GB limit
            return HealthStatus.UNHEALTHY, details
        elif memory.percent > 80:
            return HealthStatus.DEGRADED, details
        else:
            return HealthStatus.HEALTHY, details
            
    except Exception as e:
        return HealthStatus.UNHEALTHY, {"error": str(e)}


# Global health monitor instance
_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> Optional[HealthMonitor]:
    """Get the global health monitor instance"""
    return _health_monitor


def initialize_health_monitor(nerdgraph_client=None, cache=None) -> HealthMonitor:
    """Initialize the global health monitor"""
    global _health_monitor
    
    _health_monitor = HealthMonitor()
    
    # Add standard health checks
    if nerdgraph_client:
        _health_monitor.add_check(
            HealthCheck(
                "nerdgraph_api",
                lambda: check_nerdgraph_connection(nerdgraph_client),
                critical=True
            )
        )
    
    if cache:
        _health_monitor.add_check(
            HealthCheck(
                "cache",
                lambda: check_cache_health(cache),
                critical=False
            )
        )
    
    _health_monitor.add_check(
        HealthCheck(
            "disk_space",
            check_disk_space,
            critical=False
        )
    )
    
    _health_monitor.add_check(
        HealthCheck(
            "memory",
            check_memory_usage,
            critical=False
        )
    )
    
    logger.info("Health monitor initialized")
    return _health_monitor