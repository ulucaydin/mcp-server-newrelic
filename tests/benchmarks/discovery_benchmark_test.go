package benchmarks_test

import (
	"context"
	"fmt"
	"testing"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/internal/testutil"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/nrdb"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/patterns"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/quality"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/relationships"
)

// BenchmarkSchemaDiscovery benchmarks schema discovery performance
func BenchmarkSchemaDiscovery(b *testing.B) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	if err != nil {
		b.Fatal(err)
	}

	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)

	ctx := context.Background()
	filter := discovery.DiscoveryFilter{
		MaxSchemas:     50,
		MinRecordCount: 100,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		schemas, err := engine.DiscoverSchemas(ctx, filter)
		if err != nil {
			b.Fatal(err)
		}
		if len(schemas) == 0 {
			b.Fatal("No schemas discovered")
		}
	}
}

// BenchmarkParallelDiscovery benchmarks parallel schema discovery
func BenchmarkParallelDiscovery(b *testing.B) {
	workerCounts := []int{1, 5, 10, 20}

	for _, workers := range workerCounts {
		b.Run(fmt.Sprintf("workers_%d", workers), func(b *testing.B) {
			config := discovery.DefaultConfig()
			config.Performance.WorkerPoolSize = workers
			
			engine, err := discovery.NewEngine(config)
			if err != nil {
				b.Fatal(err)
			}

			mockClient := nrdb.NewMockClient()
			engine.SetNRDBClient(mockClient)

			ctx := context.Background()
			filter := discovery.DiscoveryFilter{
				MaxSchemas:     100,
				MinRecordCount: 100,
			}

			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				schemas, err := engine.DiscoverSchemas(ctx, filter)
				if err != nil {
					b.Fatal(err)
				}
				if len(schemas) == 0 {
					b.Fatal("No schemas discovered")
				}
			}
		})
	}
}

// BenchmarkPatternDetection benchmarks pattern detection performance
func BenchmarkPatternDetection(b *testing.B) {
	dataSizes := []int{100, 1000, 10000}
	gen := testutil.NewTestDataGenerator(42)

	for _, size := range dataSizes {
		b.Run(fmt.Sprintf("size_%d", size), func(b *testing.B) {
			engine := patterns.NewEngine(false)
			data := gen.GenerateTimeSeriesData(size, "trend")

			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				patterns := engine.DetectPatterns(data, discovery.DataTypeNumeric)
				if len(patterns) == 0 {
					b.Fatal("No patterns detected")
				}
			}
		})
	}
}

// BenchmarkRelationshipMining benchmarks relationship discovery
func BenchmarkRelationshipMining(b *testing.B) {
	schemaCounts := []int{10, 50, 100}
	
	for _, count := range schemaCounts {
		b.Run(fmt.Sprintf("schemas_%d", count), func(b *testing.B) {
			// Generate test schemas
			gen := testutil.NewTestDataGenerator(42)
			schemas := make([]discovery.Schema, count)
			for i := 0; i < count; i++ {
				schemas[i] = gen.GenerateSchema(fmt.Sprintf("Schema%d", i), 10)
			}

			// Add some common attributes for relationships
			for i := 0; i < count/2; i++ {
				schemas[i].Attributes = append(schemas[i].Attributes, discovery.Attribute{
					Name:         "commonId",
					DataType:     discovery.DataTypeString,
					SemanticType: discovery.SemanticTypeID,
				})
			}

			mockClient := nrdb.NewMockClient()
			config := relationships.DefaultConfig()
			miner := relationships.NewMiner(mockClient, config)

			ctx := context.Background()

			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				rels, err := miner.FindRelationships(ctx, schemas)
				if err != nil {
					b.Fatal(err)
				}
				if len(rels) == 0 {
					b.Fatal("No relationships found")
				}
			}
		})
	}
}

// BenchmarkQualityAssessment benchmarks quality assessment
func BenchmarkQualityAssessment(b *testing.B) {
	sampleSizes := []int{100, 1000, 10000}
	
	for _, size := range sampleSizes {
		b.Run(fmt.Sprintf("samples_%d", size), func(b *testing.B) {
			assessor := quality.NewAssessor(quality.DefaultConfig())
			
			// Create test schema
			schema := discovery.Schema{
				Name:      "BenchmarkSchema",
				EventType: "BenchmarkEvent",
				Attributes: []discovery.Attribute{
					{Name: "id", DataType: discovery.DataTypeString},
					{Name: "value", DataType: discovery.DataTypeNumeric},
					{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
				},
			}

			// Generate test data
			sample := testutil.CreateLowQualityData(size)
			ctx := context.Background()

			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				report := assessor.AssessSchema(ctx, schema, sample)
				if report.OverallScore == 0 {
					b.Fatal("Quality assessment failed")
				}
			}
		})
	}
}

// BenchmarkIntelligentDiscovery benchmarks intelligent discovery with hints
func BenchmarkIntelligentDiscovery(b *testing.B) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	if err != nil {
		b.Fatal(err)
	}

	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)

	ctx := context.Background()
	hints := discovery.DiscoveryHints{
		Keywords: []string{"transaction", "error", "performance"},
		Purpose:  "performance analysis",
		Domain:   "apm",
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		result, err := engine.DiscoverWithIntelligence(ctx, hints)
		if err != nil {
			b.Fatal(err)
		}
		if len(result.Schemas) == 0 {
			b.Fatal("No schemas discovered")
		}
	}
}

// BenchmarkCachePerformance benchmarks cache hit/miss performance
func BenchmarkCachePerformance(b *testing.B) {
	config := discovery.DefaultConfig()
	config.Cache.Enabled = true
	
	engine, err := discovery.NewEngine(config)
	if err != nil {
		b.Fatal(err)
	}

	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)

	ctx := context.Background()
	filter := discovery.DiscoveryFilter{
		MaxSchemas:     10,
		MinRecordCount: 100,
	}

	// Prime the cache
	_, err = engine.DiscoverSchemas(ctx, filter)
	if err != nil {
		b.Fatal(err)
	}

	b.Run("cache_hit", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			// Should hit cache
			schemas, err := engine.DiscoverSchemas(ctx, filter)
			if err != nil {
				b.Fatal(err)
			}
			if len(schemas) == 0 {
				b.Fatal("No schemas in cache")
			}
		}
	})

	b.Run("cache_miss", func(b *testing.B) {
		b.ResetTimer()
		for i := 0; i < b.N; i++ {
			// Different filter to cause cache miss
			missFilter := discovery.DiscoveryFilter{
				MaxSchemas:     10,
				MinRecordCount: 100,
				EventTypes:     []string{fmt.Sprintf("Type%d", i)},
			}
			
			schemas, err := engine.DiscoverSchemas(ctx, missFilter)
			if err != nil {
				b.Fatal(err)
			}
			if len(schemas) == 0 {
				b.Fatal("No schemas discovered")
			}
		}
	})
}

// BenchmarkMemoryUsage benchmarks memory usage for large datasets
func BenchmarkMemoryUsage(b *testing.B) {
	schemaCounts := []int{100, 500, 1000}
	
	for _, count := range schemaCounts {
		b.Run(fmt.Sprintf("schemas_%d", count), func(b *testing.B) {
			config := discovery.DefaultConfig()
			engine, err := discovery.NewEngine(config)
			if err != nil {
				b.Fatal(err)
			}

			// Create a mock client that returns many schemas
			mockClient := &BenchmarkMockClient{schemaCount: count}
			engine.SetNRDBClient(mockClient)

			ctx := context.Background()
			filter := discovery.DiscoveryFilter{
				MaxSchemas:     count,
				MinRecordCount: 10,
			}

			b.ResetTimer()
			b.ReportAllocs()
			
			for i := 0; i < b.N; i++ {
				schemas, err := engine.DiscoverSchemas(ctx, filter)
				if err != nil {
					b.Fatal(err)
				}
				if len(schemas) != count {
					b.Fatalf("Expected %d schemas, got %d", count, len(schemas))
				}
			}
		})
	}
}

// BenchmarkTimeSeriesPatternDetection benchmarks specific pattern types
func BenchmarkTimeSeriesPatternDetection(b *testing.B) {
	patterns := []string{"trend", "seasonal", "anomaly"}
	detector := patterns.NewTimeSeriesDetector()
	gen := testutil.NewTestDataGenerator(42)

	for _, pattern := range patterns {
		b.Run(pattern, func(b *testing.B) {
			data := gen.GenerateTimeSeriesData(1000, pattern)
			
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				detectedPatterns := detector.DetectPatterns(data, discovery.DataTypeNumeric)
				if len(detectedPatterns) == 0 {
					b.Fatal("No patterns detected")
				}
			}
		})
	}
}

// Custom mock client for benchmarking
type BenchmarkMockClient struct {
	schemaCount int
}

func (m *BenchmarkMockClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	// Return minimal data for benchmarking
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{"count": 10000},
		},
	}, nil
}

func (m *BenchmarkMockClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return m.Query(ctx, nrql)
}

func (m *BenchmarkMockClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	eventTypes := make([]string, m.schemaCount)
	for i := 0; i < m.schemaCount; i++ {
		eventTypes[i] = fmt.Sprintf("EventType%d", i)
	}
	return eventTypes, nil
}

func (m *BenchmarkMockClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Benchmark Account"}}, nil
}

// Benchmark results documentation
func TestPrintBenchmarkTargets(t *testing.T) {
	t.Skip("Run with -v to see benchmark targets")
	
	fmt.Println("Discovery Core Performance Targets:")
	fmt.Println("===================================")
	fmt.Println("Schema Discovery (50 schemas):")
	fmt.Println("  - Target: < 100ms")
	fmt.Println("  - With cache: < 10ms")
	fmt.Println("")
	fmt.Println("Pattern Detection (1000 points):")
	fmt.Println("  - Target: < 50ms")
	fmt.Println("")
	fmt.Println("Relationship Mining (50 schemas):")
	fmt.Println("  - Target: < 200ms")
	fmt.Println("")
	fmt.Println("Quality Assessment (1000 samples):")
	fmt.Println("  - Target: < 100ms")
	fmt.Println("")
	fmt.Println("Memory Usage (1000 schemas):")
	fmt.Println("  - Target: < 100MB")
	fmt.Println("")
	fmt.Println("Concurrent Discovery (10 workers):")
	fmt.Println("  - Target: Linear scaling up to CPU count")
}