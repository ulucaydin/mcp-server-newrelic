# Improvement Action Plan for New Relic MCP Server

Based on the comprehensive review, here's a prioritized action plan for improving the MCP Server.

## Priority 0: Critical Security Fixes (Immediate)

### 1. Fix Memory Leak in Cache Implementation
**Issue**: Unbounded cache growth can lead to OOM
```python
# Current problematic code in core/cache.py
self._cache = {}  # No size limit

# Fix: Implement LRU eviction
from cachetools import LRUCache
self._cache = LRUCache(maxsize=self.max_size)
```
**Timeline**: 1 day
**Owner**: Core team

### 2. Add Thread Safety to Plugin Manager
**Issue**: Race condition in plugin loading
```python
# Add locking to plugin operations
import threading
self._lock = threading.RLock()

def load_plugin(self, plugin: PluginInstance):
    with self._lock:
        # Thread-safe plugin loading
```
**Timeline**: 1 day
**Owner**: Core team

### 3. Sanitize Error Messages
**Issue**: Internal details exposed in errors
```python
# Create error sanitizer
def sanitize_error(error: Exception) -> str:
    if isinstance(error, PublicError):
        return str(error)
    return "An internal error occurred"
```
**Timeline**: 2 days
**Owner**: Security team

## Priority 1: Test Coverage Improvements (Week 1)

### 1. Increase Unit Test Coverage to 80%
**Current**: ~65% coverage
**Target**: 80% minimum

Key areas needing tests:
- Features modules (currently 45%)
- Plugin lifecycle management
- Error handling paths
- Cache eviction logic

### 2. Add Integration Tests
```python
# tests/integration/test_full_workflow.py
@pytest.mark.integration
async def test_apm_to_alert_workflow():
    """Test complete workflow from APM query to alert creation"""
    # 1. Query APM metrics
    # 2. Detect anomaly
    # 3. Create alert policy
    # 4. Verify alert triggers
```

### 3. Add Performance Benchmarks
```python
# tests/benchmarks/test_query_performance.py
@pytest.mark.benchmark
def test_concurrent_nrql_queries(benchmark):
    """Benchmark 100 concurrent NRQL queries"""
    result = benchmark(run_concurrent_queries, 100)
    assert result.avg_time < 100  # ms
```

## Priority 2: Documentation Enhancements (Week 2)

### 1. Create API Reference Documentation
```bash
# Generate from docstrings
sphinx-apidoc -o docs/api core features
make html
```

### 2. Write Plugin Development Guide
```markdown
# docs/PLUGIN_DEVELOPMENT.md
1. Plugin Architecture
2. Creating Your First Plugin
3. Testing Plugins
4. Best Practices
5. Publishing Plugins
```

### 3. Add Deployment Guides
- Kubernetes deployment with Helm chart
- AWS/GCP/Azure deployment templates
- Production configuration best practices

## Priority 3: Security Hardening (Week 3)

### 1. Implement Request Signing
```python
class RequestSigner:
    def sign_request(self, request: dict) -> str:
        timestamp = int(time.time())
        payload = json.dumps(request) + str(timestamp)
        signature = hmac.new(
            self.secret_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{timestamp}:{signature}"
```

### 2. Add Role-Based Access Control
```python
class RBACManager:
    def check_permission(
        self,
        user: str,
        resource: str,
        action: str
    ) -> bool:
        role = self.get_user_role(user)
        return self.role_has_permission(role, resource, action)
```

### 3. Implement Audit Log Signing
```python
class TamperProofAuditLogger:
    def log_event(self, event: AuditEvent):
        event.hash = self.calculate_hash(event)
        event.previous_hash = self.last_hash
        self.write_event(event)
        self.last_hash = event.hash
```

## Priority 4: Performance Optimizations (Week 4)

### 1. Implement Worker Process Pool
```python
from multiprocessing import Pool

class QueryExecutor:
    def __init__(self, workers: int = 4):
        self.pool = Pool(processes=workers)
    
    async def execute_heavy_query(self, query: str):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.pool,
            self._execute_query,
            query
        )
```

### 2. Add Query Result Streaming
```python
async def stream_large_results(query: str):
    async for chunk in nerdgraph.stream_query(query):
        yield process_chunk(chunk)
```

### 3. Optimize Entity Search
```python
# Create indexed search
class EntitySearchIndex:
    def __init__(self):
        self.name_index = {}
        self.tag_index = defaultdict(set)
    
    def search(self, keyword: str) -> List[Entity]:
        # O(1) lookup instead of O(n) scan
        return self.name_index.get(keyword.lower(), [])
```

## Priority 5: Operational Improvements (Month 2)

### 1. Add OpenTelemetry Support
```python
from opentelemetry import trace
from opentelemetry.exporter.otlp import OTLPSpanExporter

tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("nerdgraph_query")
async def traced_query(query: str):
    span = trace.get_current_span()
    span.set_attribute("query.type", "nerdgraph")
    return await self.query(query)
```

### 2. Implement Circuit Breakers
```python
from pybreaker import CircuitBreaker

nerdgraph_breaker = CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    exclude=[ValidationError]
)

@nerdgraph_breaker
async def query_with_breaker(query: str):
    return await nerdgraph.query(query)
```

### 3. Add Feature Flags
```python
from feature_flags import FeatureFlags

flags = FeatureFlags()

@flags.check("enhanced_metrics")
async def get_metrics():
    if flags.is_enabled("enhanced_metrics"):
        return await get_enhanced_metrics()
    return await get_basic_metrics()
```

## Implementation Timeline

| Week | Focus Area | Deliverables |
|------|------------|--------------|
| 1 | Critical Fixes | Security patches, memory leak fix |
| 2 | Testing | 80% coverage, integration tests |
| 3 | Documentation | API docs, guides, examples |
| 4 | Security | RBAC, signing, audit improvements |
| 5-6 | Performance | Worker pools, streaming, indexing |
| 7-8 | Operations | Telemetry, circuit breakers, flags |

## Success Metrics

1. **Security**: Zero critical vulnerabilities in security scan
2. **Testing**: 80%+ code coverage, <5% test flakiness
3. **Performance**: <100ms p95 latency for queries
4. **Reliability**: 99.9% uptime, <1% error rate
5. **Documentation**: 100% public API documented

## Resources Required

- 2 senior engineers for 2 months
- 1 security engineer for 2 weeks
- 1 technical writer for 2 weeks
- CI/CD infrastructure upgrades
- Security scanning tools license

## Risk Mitigation

1. **Breaking Changes**: Version all APIs, maintain backwards compatibility
2. **Performance Regression**: Benchmark all changes, load test before release
3. **Security Issues**: Regular security audits, penetration testing
4. **Plugin Ecosystem**: Provide migration guides, deprecation warnings

## Next Steps

1. Review and approve action plan
2. Assign team members to priorities
3. Set up tracking dashboard
4. Begin implementation of P0 items
5. Schedule weekly progress reviews

---

This action plan addresses all critical issues identified in the comprehensive review while providing a clear path to production readiness and long-term maintainability.