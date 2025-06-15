"""Performance monitoring and metrics for Intelligence Engine"""

import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from contextlib import contextmanager
import logging
from dataclasses import dataclass, field
from enum import Enum
import json

from prometheus_client import Counter, Histogram, Gauge, Summary, Info
from prometheus_client import start_http_server, generate_latest

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricPoint:
    """A single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    # Timing metrics
    operation_durations: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Resource metrics
    cpu_usage: List[MetricPoint] = field(default_factory=list)
    memory_usage: List[MetricPoint] = field(default_factory=list)
    
    # Throughput metrics
    operations_per_second: Dict[str, float] = field(default_factory=dict)
    
    # Error metrics
    error_counts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # Custom metrics
    custom_metrics: Dict[str, List[MetricPoint]] = field(default_factory=lambda: defaultdict(list))


class PerformanceMonitor:
    """Monitor and track performance metrics for the Intelligence Engine"""
    
    def __init__(self, enable_prometheus: bool = True, prometheus_port: int = 8080):
        self.enable_prometheus = enable_prometheus
        self.prometheus_port = prometheus_port
        
        # Internal metrics storage
        self._metrics = PerformanceMetrics()
        self._operation_counts = defaultdict(int)
        self._operation_timers = {}
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Resource monitoring
        self._resource_monitor_thread = None
        self._monitoring = False
        
        # Prometheus metrics
        if self.enable_prometheus:
            self._setup_prometheus_metrics()
            self._start_prometheus_server()
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # Operation metrics
        self.operation_duration = Histogram(
            'intelligence_operation_duration_seconds',
            'Duration of operations in seconds',
            ['operation', 'component']
        )
        
        self.operation_counter = Counter(
            'intelligence_operations_total',
            'Total number of operations',
            ['operation', 'component', 'status']
        )
        
        # Pattern detection metrics
        self.patterns_detected = Counter(
            'intelligence_patterns_detected_total',
            'Total patterns detected',
            ['pattern_type', 'detector']
        )
        
        self.pattern_confidence = Summary(
            'intelligence_pattern_confidence',
            'Pattern detection confidence scores',
            ['pattern_type']
        )
        
        # Query generation metrics
        self.queries_generated = Counter(
            'intelligence_queries_generated_total',
            'Total queries generated',
            ['intent_type', 'query_type']
        )
        
        self.query_confidence = Summary(
            'intelligence_query_confidence',
            'Query generation confidence scores'
        )
        
        self.query_optimization_savings = Summary(
            'intelligence_query_optimization_savings_ratio',
            'Query cost reduction ratio from optimization'
        )
        
        # Visualization metrics
        self.charts_recommended = Counter(
            'intelligence_charts_recommended_total',
            'Total chart recommendations',
            ['chart_type', 'goal']
        )
        
        self.layout_quality = Gauge(
            'intelligence_layout_quality_score',
            'Dashboard layout quality score',
            ['strategy']
        )
        
        # Resource metrics
        self.cpu_usage = Gauge(
            'intelligence_cpu_usage_percent',
            'CPU usage percentage'
        )
        
        self.memory_usage = Gauge(
            'intelligence_memory_usage_bytes',
            'Memory usage in bytes'
        )
        
        # Error metrics
        self.error_counter = Counter(
            'intelligence_errors_total',
            'Total errors',
            ['component', 'error_type']
        )
        
        # Model registry metrics
        self.models_registered = Gauge(
            'intelligence_models_registered_total',
            'Total registered models',
            ['model_type']
        )
        
        self.model_load_duration = Histogram(
            'intelligence_model_load_duration_seconds',
            'Model loading duration',
            ['model_type']
        )
        
        # System info
        self.system_info = Info(
            'intelligence_system',
            'System information'
        )
        self.system_info.info({
            'version': '1.0.0',
            'python_version': '3.9+',
            'platform': 'linux'
        })
    
    def _start_prometheus_server(self):
        """Start Prometheus metrics server"""
        try:
            start_http_server(self.prometheus_port)
            logger.info(f"Prometheus metrics server started on port {self.prometheus_port}")
        except Exception as e:
            logger.error(f"Failed to start Prometheus server: {e}")
    
    def start_resource_monitoring(self, interval: float = 5.0):
        """Start monitoring system resources"""
        if self._monitoring:
            return
        
        self._monitoring = True
        self._resource_monitor_thread = threading.Thread(
            target=self._monitor_resources,
            args=(interval,),
            daemon=True
        )
        self._resource_monitor_thread.start()
        logger.info("Resource monitoring started")
    
    def stop_resource_monitoring(self):
        """Stop monitoring system resources"""
        self._monitoring = False
        if self._resource_monitor_thread:
            self._resource_monitor_thread.join(timeout=5)
        logger.info("Resource monitoring stopped")
    
    def _monitor_resources(self, interval: float):
        """Monitor system resources periodically"""
        while self._monitoring:
            try:
                # Get CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric('cpu_usage', cpu_percent)
                
                if self.enable_prometheus:
                    self.cpu_usage.set(cpu_percent)
                
                # Get memory usage
                memory = psutil.virtual_memory()
                memory_bytes = memory.used
                self.record_metric('memory_usage', memory_bytes)
                
                if self.enable_prometheus:
                    self.memory_usage.set(memory_bytes)
                
                # Sleep for interval
                time.sleep(interval - 1)  # Subtract CPU measurement time
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                time.sleep(interval)
    
    @contextmanager
    def measure_operation(self, operation: str, component: str = "general"):
        """
        Context manager to measure operation duration
        
        Usage:
            with monitor.measure_operation('pattern_detection', 'pattern_engine'):
                # Perform operation
                pass
        """
        start_time = time.time()
        success = True
        
        try:
            yield
        except Exception as e:
            success = False
            self.record_error(component, type(e).__name__)
            raise
        finally:
            duration = time.time() - start_time
            
            # Record duration
            with self._lock:
                self._metrics.operation_durations[operation].append(duration)
                self._operation_counts[operation] += 1
            
            # Update Prometheus metrics
            if self.enable_prometheus:
                self.operation_duration.labels(
                    operation=operation,
                    component=component
                ).observe(duration)
                
                self.operation_counter.labels(
                    operation=operation,
                    component=component,
                    status='success' if success else 'error'
                ).inc()
            
            logger.debug(f"Operation '{operation}' took {duration:.3f}s")
    
    def record_pattern_detection(self, pattern_type: str, detector: str, confidence: float):
        """Record pattern detection metrics"""
        if self.enable_prometheus:
            self.patterns_detected.labels(
                pattern_type=pattern_type,
                detector=detector
            ).inc()
            
            self.pattern_confidence.labels(
                pattern_type=pattern_type
            ).observe(confidence)
    
    def record_query_generation(self, intent_type: str, query_type: str, confidence: float):
        """Record query generation metrics"""
        if self.enable_prometheus:
            self.queries_generated.labels(
                intent_type=intent_type,
                query_type=query_type
            ).inc()
            
            self.query_confidence.observe(confidence)
    
    def record_query_optimization(self, cost_reduction_ratio: float):
        """Record query optimization metrics"""
        if self.enable_prometheus:
            self.query_optimization_savings.observe(cost_reduction_ratio)
    
    def record_chart_recommendation(self, chart_type: str, goal: str):
        """Record chart recommendation metrics"""
        if self.enable_prometheus:
            self.charts_recommended.labels(
                chart_type=chart_type,
                goal=goal
            ).inc()
    
    def record_layout_quality(self, strategy: str, quality_score: float):
        """Record layout optimization quality"""
        if self.enable_prometheus:
            self.layout_quality.labels(strategy=strategy).set(quality_score)
    
    def record_model_operation(self, operation: str, model_type: str, duration: float):
        """Record model registry operations"""
        if self.enable_prometheus:
            if operation == 'load':
                self.model_load_duration.labels(
                    model_type=model_type
                ).observe(duration)
    
    def update_model_count(self, counts_by_type: Dict[str, int]):
        """Update registered model counts"""
        if self.enable_prometheus:
            for model_type, count in counts_by_type.items():
                self.models_registered.labels(
                    model_type=model_type
                ).set(count)
    
    def record_error(self, component: str, error_type: str):
        """Record error occurrence"""
        with self._lock:
            self._metrics.error_counts[f"{component}_{error_type}"] += 1
        
        if self.enable_prometheus:
            self.error_counter.labels(
                component=component,
                error_type=error_type
            ).inc()
    
    def record_metric(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record a custom metric"""
        metric_point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )
        
        with self._lock:
            self._metrics.custom_metrics[name].append(metric_point)
    
    def get_operation_stats(self, operation: str) -> Dict[str, float]:
        """Get statistics for an operation"""
        with self._lock:
            durations = self._metrics.operation_durations.get(operation, [])
            
            if not durations:
                return {}
            
            return {
                'count': len(durations),
                'mean': sum(durations) / len(durations),
                'min': min(durations),
                'max': max(durations),
                'total': sum(durations)
            }
    
    def get_throughput(self, operation: str, window_seconds: int = 60) -> float:
        """Calculate operations per second over a time window"""
        with self._lock:
            count = self._operation_counts.get(operation, 0)
            # Simplified: assume uniform distribution
            return count / window_seconds
    
    def get_error_rate(self, component: str = None) -> float:
        """Get error rate for a component or overall"""
        with self._lock:
            if component:
                error_count = sum(
                    count for key, count in self._metrics.error_counts.items()
                    if key.startswith(component)
                )
                total_ops = sum(
                    count for op, count in self._operation_counts.items()
                    if component in op
                )
            else:
                error_count = sum(self._metrics.error_counts.values())
                total_ops = sum(self._operation_counts.values())
            
            return error_count / max(1, total_ops)
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        return {
            'cpu_percent': cpu_percent,
            'memory_used_bytes': memory.used,
            'memory_percent': memory.percent,
            'memory_available_bytes': memory.available
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        with self._lock:
            total_operations = sum(self._operation_counts.values())
            total_errors = sum(self._metrics.error_counts.values())
            
            operation_summaries = {}
            for op, durations in self._metrics.operation_durations.items():
                if durations:
                    operation_summaries[op] = {
                        'count': len(durations),
                        'avg_duration': sum(durations) / len(durations),
                        'total_duration': sum(durations)
                    }
            
            return {
                'total_operations': total_operations,
                'total_errors': total_errors,
                'error_rate': total_errors / max(1, total_operations),
                'operations': operation_summaries,
                'resource_usage': self.get_resource_usage()
            }
    
    def export_metrics(self, format: str = 'json') -> str:
        """Export metrics in specified format"""
        if format == 'prometheus':
            return generate_latest().decode('utf-8')
        
        elif format == 'json':
            summary = self.get_summary()
            
            # Add recent metrics
            with self._lock:
                # Get last 100 points for each custom metric
                recent_metrics = {}
                for name, points in self._metrics.custom_metrics.items():
                    recent_metrics[name] = [
                        {
                            'timestamp': p.timestamp.isoformat(),
                            'value': p.value,
                            'labels': p.labels
                        }
                        for p in points[-100:]
                    ]
                
                summary['recent_metrics'] = recent_metrics
            
            return json.dumps(summary, indent=2)
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self._metrics = PerformanceMetrics()
            self._operation_counts.clear()
        
        logger.info("Metrics reset")


# Global monitor instance
_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor(enable_prometheus: bool = True, 
                          prometheus_port: int = 8080) -> PerformanceMonitor:
    """Get or create performance monitor singleton"""
    global _monitor
    
    if _monitor is None:
        _monitor = PerformanceMonitor(enable_prometheus, prometheus_port)
        _monitor.start_resource_monitoring()
    
    return _monitor


def cleanup_monitor():
    """Cleanup monitor resources"""
    global _monitor
    
    if _monitor:
        _monitor.stop_resource_monitoring()
        _monitor = None