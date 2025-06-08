"""
Performance benchmarks for the MCP Server

These tests measure performance characteristics and help identify
bottlenecks and regressions.
"""

import pytest
import asyncio
import time
import statistics
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock, patch
import psutil
import os
import json

from core.nerdgraph_client import NerdGraphClient
from core.cache_improved import MemoryLimitedCache, create_cache
from core.plugin_manager import EnhancedPluginManager
from core.security import NRQLValidator


@pytest.mark.benchmark
class TestQueryPerformance:
    """Benchmark query performance"""
    
    @pytest.mark.asyncio
    async def test_nerdgraph_query_latency(self):
        """Benchmark NerdGraph query latency"""
        
        with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"data": {"result": "success"}}
            mock_response.raise_for_status.return_value = None
            
            # Simulate network latency
            async def delayed_post(*args, **kwargs):
                await asyncio.sleep(0.05)  # 50ms simulated latency
                return mock_response
            
            mock_client.post = delayed_post
            mock_client_class.return_value = mock_client
            
            client = NerdGraphClient(
                api_key="test-key",
                endpoint="https://api.test.com/graphql"
            )
            
            # Benchmark single query
            query = "SELECT count(*) FROM Transaction SINCE 1 hour ago"
            
            start_time = time.perf_counter()
            result = await client.query(query)
            end_time = time.perf_counter()
            
            latency = (end_time - start_time) * 1000  # Convert to ms
            
            assert result["data"]["result"] == "success"
            assert latency < 100  # Should complete in under 100ms (including mock delay)
            
            print(f"Single query latency: {latency:.2f}ms")
            
            await client.close()
    
    @pytest.mark.asyncio
    async def test_concurrent_query_throughput(self):
        """Benchmark concurrent query throughput"""
        
        with patch('core.nerdgraph_client.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = {"data": {"result": "success"}}
            mock_response.raise_for_status.return_value = None
            
            # Simulate realistic latency
            async def delayed_post(*args, **kwargs):
                await asyncio.sleep(0.02)  # 20ms latency
                return mock_response
            
            mock_client.post = delayed_post
            mock_client_class.return_value = mock_client
            
            client = NerdGraphClient(
                api_key="test-key",
                endpoint="https://api.test.com/graphql"
            )
            
            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20, 50]
            results = {}
            
            for concurrency in concurrency_levels:
                queries = [f"SELECT count(*) FROM Transaction LIMIT {i}" 
                          for i in range(concurrency)]
                
                start_time = time.perf_counter()
                tasks = [client.query(query) for query in queries]
                responses = await asyncio.gather(*tasks)
                end_time = time.perf_counter()
                
                total_time = end_time - start_time
                throughput = len(queries) / total_time  # queries per second
                
                results[concurrency] = {
                    'total_time': total_time,
                    'throughput': throughput,
                    'avg_latency': (total_time / len(queries)) * 1000  # ms
                }
                
                # Verify all succeeded
                assert len(responses) == concurrency
                for response in responses:
                    assert response["data"]["result"] == "success"
            
            # Print benchmark results
            print("\nConcurrency Benchmark Results:")
            print("Concurrency | Total Time | Throughput | Avg Latency")
            print("-" * 50)
            for concurrency, metrics in results.items():
                print(f"{concurrency:10d} | {metrics['total_time']:9.3f}s | "
                      f"{metrics['throughput']:9.2f}/s | {metrics['avg_latency']:10.2f}ms")
            
            # Performance assertions
            assert results[1]['throughput'] > 10  # At least 10 QPS for single query
            assert results[10]['throughput'] > 50  # Should scale with concurrency
            
            await client.close()


@pytest.mark.benchmark
class TestCachePerformance:
    """Benchmark cache performance"""
    
    @pytest.mark.asyncio
    async def test_cache_write_performance(self):
        """Benchmark cache write performance"""
        
        cache = MemoryLimitedCache(max_items=10000, max_memory_mb=50)
        
        # Test different value sizes
        value_sizes = [100, 1000, 10000]  # bytes
        write_times = {}
        
        for size in value_sizes:
            value = "x" * size
            num_writes = 1000
            
            start_time = time.perf_counter()
            
            for i in range(num_writes):
                await cache.set(f"key_{size}_{i}", value)
            
            end_time = time.perf_counter()
            
            total_time = end_time - start_time
            writes_per_second = num_writes / total_time
            
            write_times[size] = {
                'total_time': total_time,
                'writes_per_second': writes_per_second,
                'avg_write_time': (total_time / num_writes) * 1000  # ms
            }
        
        # Print results
        print("\nCache Write Performance:")
        print("Value Size | Total Time | Writes/sec | Avg Write Time")
        print("-" * 55)
        for size, metrics in write_times.items():
            print(f"{size:9d}B | {metrics['total_time']:9.3f}s | "
                  f"{metrics['writes_per_second']:9.0f}/s | {metrics['avg_write_time']:13.3f}ms")
        
        # Performance assertions
        assert write_times[100]['writes_per_second'] > 10000  # Small values should be very fast
        assert write_times[10000]['writes_per_second'] > 1000  # Large values should still be fast
    
    @pytest.mark.asyncio
    async def test_cache_read_performance(self):
        """Benchmark cache read performance"""
        
        cache = MemoryLimitedCache(max_items=10000)
        
        # Pre-populate cache
        num_items = 5000
        for i in range(num_items):
            await cache.set(f"key_{i}", f"value_{i}")
        
        # Benchmark reads
        num_reads = 10000
        read_times = []
        
        for i in range(num_reads):
            key = f"key_{i % num_items}"  # Cycle through existing keys
            
            start_time = time.perf_counter()
            value = await cache.get(key)
            end_time = time.perf_counter()
            
            read_time = (end_time - start_time) * 1000000  # microseconds
            read_times.append(read_time)
            
            assert value is not None
        
        # Calculate statistics
        avg_read_time = statistics.mean(read_times)
        p95_read_time = statistics.quantiles(read_times, n=20)[18]  # 95th percentile
        p99_read_time = statistics.quantiles(read_times, n=100)[98]  # 99th percentile
        reads_per_second = 1000000 / avg_read_time  # Convert from microseconds
        
        print(f"\nCache Read Performance ({num_reads:,} reads):")
        print(f"Average read time: {avg_read_time:.2f}μs")
        print(f"95th percentile: {p95_read_time:.2f}μs")
        print(f"99th percentile: {p99_read_time:.2f}μs")
        print(f"Reads per second: {reads_per_second:,.0f}/s")
        
        # Performance assertions
        assert avg_read_time < 100  # Should be under 100 microseconds on average
        assert p95_read_time < 500  # 95% of reads under 500 microseconds
        assert reads_per_second > 50000  # Should handle 50k+ reads per second
    
    @pytest.mark.asyncio
    async def test_cache_memory_efficiency(self):
        """Test cache memory usage efficiency"""
        
        cache = MemoryLimitedCache(max_items=1000, max_memory_mb=10)
        
        # Fill cache to capacity
        for i in range(2000):  # More than max_items to trigger eviction
            value = f"value_{i}" * 100  # ~800 bytes per value
            await cache.set(f"key_{i}", value)
        
        stats = cache.get_stats()
        
        # Verify memory limits are respected
        assert stats['items'] <= 1000
        assert stats['memory_mb'] <= 10.5  # Allow small buffer for overhead
        assert stats['evictions'] > 0
        
        # Memory efficiency should be reasonable
        avg_bytes_per_item = (stats['memory_bytes'] / stats['items'])
        assert avg_bytes_per_item < 2000  # Should be reasonably efficient
        
        print(f"\nCache Memory Efficiency:")
        print(f"Items: {stats['items']:,}")
        print(f"Memory usage: {stats['memory_mb']:.2f}MB")
        print(f"Average bytes per item: {avg_bytes_per_item:.0f}")
        print(f"Evictions: {stats['evictions']:,}")


@pytest.mark.benchmark
class TestPluginPerformance:
    """Benchmark plugin loading and execution performance"""
    
    @pytest.mark.asyncio
    async def test_plugin_loading_time(self):
        """Benchmark plugin loading performance"""
        
        with patch('core.plugin_manager.Path.glob') as mock_glob:
            # Mock plugin files
            mock_files = [Mock(name=f"plugin_{i}.py", stem=f"plugin_{i}") 
                         for i in range(20)]
            for f in mock_files:
                f.name = f"plugin_{f.stem}.py"
            mock_glob.return_value = mock_files
            
            with patch('core.plugin_manager.importlib.import_module') as mock_import:
                # Mock plugin modules
                mock_modules = []
                for i in range(20):
                    module = Mock()
                    plugin_class = Mock()
                    plugin_class.__name__ = f"TestPlugin{i}"
                    plugin_class.register = Mock()
                    plugin_class.__bases__ = (Mock(),)  # Mock inheritance
                    
                    # Mock the issubclass check
                    with patch('core.plugin_manager.issubclass', return_value=True):
                        module.__dict__ = {f"TestPlugin{i}": plugin_class}
                        mock_modules.append(module)
                
                mock_import.side_effect = mock_modules
                
                with patch('core.plugin_manager.issubclass', return_value=True):
                    with patch('core.plugin_manager.hasattr', return_value=True):
                        mock_app = Mock()
                        manager = EnhancedPluginManager(mock_app)
                        
                        start_time = time.perf_counter()
                        plugins = manager.discover_plugins()
                        end_time = time.perf_counter()
                        
                        discovery_time = (end_time - start_time) * 1000  # ms
                        
                        print(f"\nPlugin Discovery Performance:")
                        print(f"Plugins discovered: {len(plugins)}")
                        print(f"Discovery time: {discovery_time:.2f}ms")
                        print(f"Time per plugin: {discovery_time/len(plugins):.2f}ms")
                        
                        # Performance assertions
                        assert len(plugins) == 20
                        assert discovery_time < 1000  # Should discover 20 plugins in under 1 second
                        assert discovery_time/len(plugins) < 50  # Under 50ms per plugin


@pytest.mark.benchmark
class TestSecurityPerformance:
    """Benchmark security validation performance"""
    
    def test_nrql_validation_performance(self):
        """Benchmark NRQL validation performance"""
        
        # Test queries of different lengths and complexity
        test_queries = [
            "SELECT count(*) FROM Transaction",
            "SELECT average(duration), percentile(duration, 95) FROM Transaction SINCE 1 hour ago",
            "SELECT count(*) FROM Transaction WHERE appName = 'MyApp' AND duration > 1.0 FACET name TIMESERIES",
            "FROM Transaction SELECT count(*), average(duration), max(duration), min(duration) WHERE duration > 0.5 FACET appName, host SINCE 2 hours ago UNTIL 1 hour ago LIMIT 100",
            "SELECT histogram(duration, 20, 10) FROM Transaction WHERE appName LIKE '%service%' AND host IN ('host1', 'host2', 'host3') FACET appName, browserName TIMESERIES AUTO SINCE 1 week ago"
        ]
        
        num_iterations = 1000
        validation_times = []
        
        for query in test_queries:
            times_for_query = []
            
            for _ in range(num_iterations):
                start_time = time.perf_counter()
                try:
                    validated = NRQLValidator.validate_nrql(query)
                    assert validated == query  # Should return the same query if valid
                except Exception:
                    pass  # Expected for some test cases
                end_time = time.perf_counter()
                
                validation_time = (end_time - start_time) * 1000000  # microseconds
                times_for_query.append(validation_time)
            
            avg_time = statistics.mean(times_for_query)
            validation_times.append((len(query), avg_time))
        
        # Print results
        print("\nNRQL Validation Performance:")
        print("Query Length | Avg Validation Time")
        print("-" * 35)
        for query_len, avg_time in validation_times:
            print(f"{query_len:11d} | {avg_time:15.2f}μs")
        
        # Performance assertions
        for query_len, avg_time in validation_times:
            assert avg_time < 1000  # Should validate in under 1ms (1000μs)
        
        # Validation should scale reasonably with query length
        max_time = max(time for _, time in validation_times)
        min_time = min(time for _, time in validation_times)
        assert max_time / min_time < 10  # Shouldn't be more than 10x slower for longest queries


@pytest.mark.benchmark
class TestMemoryUsage:
    """Test memory usage characteristics"""
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """Test memory usage under sustained load"""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create cache and fill it
        cache = MemoryLimitedCache(max_items=1000, max_memory_mb=10)
        
        # Simulate sustained load
        iterations = 5000
        memory_samples = []
        
        for i in range(iterations):
            # Create varying sized objects
            size = (i % 100) + 50  # 50-149 chars
            value = "x" * size
            await cache.set(f"key_{i}", value)
            
            # Sample memory every 100 iterations
            if i % 100 == 0:
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_samples.append(current_memory)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        print(f"\nMemory Usage Test:")
        print(f"Initial memory: {initial_memory:.2f}MB")
        print(f"Final memory: {final_memory:.2f}MB")
        print(f"Memory growth: {memory_growth:.2f}MB")
        print(f"Cache stats: {cache.get_stats()}")
        
        # Memory growth should be bounded
        assert memory_growth < 50  # Should not grow by more than 50MB
        
        # Memory should stabilize (not keep growing)
        if len(memory_samples) >= 10:
            early_avg = statistics.mean(memory_samples[:5])
            late_avg = statistics.mean(memory_samples[-5:])
            growth_rate = (late_avg - early_avg) / early_avg
            assert growth_rate < 0.5  # Memory shouldn't grow by more than 50% during test


if __name__ == "__main__":
    # Run benchmarks standalone
    pytest.main([__file__, "-v", "-m", "benchmark", "--tb=short"])