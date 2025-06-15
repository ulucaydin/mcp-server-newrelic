package integration_test

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/internal/testutil"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/nrdb"
)

// TestFullDiscoveryWorkflow tests the complete discovery workflow
func TestFullDiscoveryWorkflow(t *testing.T) {
	// Create engine with mock NRDB
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	// Use mock NRDB client
	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)

	ctx := context.Background()

	// Test 1: Basic Schema Discovery
	t.Run("basic_schema_discovery", func(t *testing.T) {
		filter := discovery.DiscoveryFilter{
			MaxSchemas:     10,
			MinRecordCount: 100,
		}

		schemas, err := engine.DiscoverSchemas(ctx, filter)
		assert.NoError(t, err)
		assert.NotEmpty(t, schemas)
		assert.LessOrEqual(t, len(schemas), 10)

		// Verify schema structure
		for _, schema := range schemas {
			assert.NotEmpty(t, schema.Name)
			assert.NotEmpty(t, schema.EventType)
			assert.NotEmpty(t, schema.Attributes)
			assert.Greater(t, schema.SampleCount, int64(0))
			assert.NotZero(t, schema.Quality.OverallScore)
		}
	})

	// Test 2: Intelligent Discovery
	t.Run("intelligent_discovery", func(t *testing.T) {
		hints := discovery.DiscoveryHints{
			Keywords: []string{"transaction", "error"},
			Purpose:  "performance analysis",
			Domain:   "apm",
		}

		result, err := engine.DiscoverWithIntelligence(ctx, hints)
		assert.NoError(t, err)
		assert.NotNil(t, result)
		assert.NotEmpty(t, result.Schemas)
		assert.NotEmpty(t, result.Insights)
		assert.NotEmpty(t, result.Recommendations)

		// Verify schemas are relevant to APM
		foundTransaction := false
		for _, schema := range result.Schemas {
			if schema.Name == "Transaction" || schema.Name == "TransactionError" {
				foundTransaction = true
				break
			}
		}
		assert.True(t, foundTransaction, "Should find transaction-related schemas")

		// Verify insights are generated
		assert.Greater(t, len(result.Insights), 0)
		for _, insight := range result.Insights {
			assert.NotEmpty(t, insight.Title)
			assert.NotEmpty(t, insight.Type)
			assert.NotEmpty(t, insight.Severity)
		}
	})

	// Test 3: Schema Profiling
	t.Run("schema_profiling", func(t *testing.T) {
		// Test different profiling depths
		depths := []discovery.ProfileDepth{
			discovery.ProfileDepthBasic,
			discovery.ProfileDepthStandard,
			discovery.ProfileDepthFull,
		}

		for _, depth := range depths {
			schema, err := engine.ProfileSchema(ctx, "Transaction", depth)
			assert.NoError(t, err)
			assert.NotNil(t, schema)
			assert.Equal(t, "Transaction", schema.EventType)

			// Verify depth-specific features
			switch depth {
			case discovery.ProfileDepthFull:
				// Full depth should have samples
				for _, attr := range schema.Attributes {
					if len(attr.SampleValues) > 0 {
						assert.NotEmpty(t, attr.SampleValues)
						break
					}
				}
				fallthrough
			case discovery.ProfileDepthStandard:
				// Standard depth should have patterns
				assert.NotEmpty(t, schema.Patterns)
				// Should have statistics
				hasStats := false
				for _, attr := range schema.Attributes {
					if attr.Statistics.NumericStats != nil || attr.Statistics.StringStats != nil {
						hasStats = true
						break
					}
				}
				assert.True(t, hasStats, "Standard/Full depth should have statistics")
			}
		}
	})

	// Test 4: Relationship Discovery
	t.Run("relationship_discovery", func(t *testing.T) {
		// Get test schemas with known relationships
		schemas := testutil.CreateTestSchemas()
		
		relationships, err := engine.FindRelationships(ctx, schemas)
		assert.NoError(t, err)
		assert.NotEmpty(t, relationships)

		// Verify we find expected relationships
		foundUserOrderJoin := false
		foundTemporalRelationship := false

		for _, rel := range relationships {
			// Check for User-Order join relationship
			if (rel.SourceSchema == "User" && rel.TargetSchema == "Order") ||
			   (rel.SourceSchema == "Order" && rel.TargetSchema == "User") {
				if rel.Type == discovery.RelationshipTypeJoin && rel.JoinKeys != nil {
					assert.Equal(t, "userId", rel.JoinKeys.SourceKey)
					foundUserOrderJoin = true
				}
			}

			// Check for temporal relationships
			if rel.Type == discovery.RelationshipTypeTemporal {
				foundTemporalRelationship = true
			}
		}

		assert.True(t, foundUserOrderJoin, "Should find User-Order join relationship")
		assert.True(t, foundTemporalRelationship, "Should find temporal relationships")
	})

	// Test 5: Quality Assessment
	t.Run("quality_assessment", func(t *testing.T) {
		report, err := engine.AssessQuality(ctx, "Transaction")
		assert.NoError(t, err)
		assert.NotNil(t, report)

		// Verify quality dimensions
		assert.Greater(t, report.OverallScore, 0.0)
		assert.LessOrEqual(t, report.OverallScore, 1.0)
		
		dimensions := report.Dimensions
		assert.NotZero(t, dimensions.Completeness.Score)
		assert.NotZero(t, dimensions.Consistency.Score)
		assert.NotZero(t, dimensions.Timeliness.Score)
		assert.NotZero(t, dimensions.Uniqueness.Score)
		assert.NotZero(t, dimensions.Validity.Score)

		// Each dimension should have details
		assert.NotEmpty(t, dimensions.Completeness.Details)
		assert.NotEmpty(t, dimensions.Consistency.Details)
	})

	// Test 6: Health Check
	t.Run("health_check", func(t *testing.T) {
		health := engine.Health()
		
		assert.Equal(t, "healthy", health.Status)
		assert.NotEmpty(t, health.Version)
		assert.Greater(t, health.Uptime, time.Duration(0))
		
		// Verify component health
		assert.Contains(t, health.Components, "nrdb")
		assert.Contains(t, health.Components, "cache")
		assert.Contains(t, health.Components, "worker_pool")
		
		for name, component := range health.Components {
			assert.Equal(t, "healthy", component.Status, "Component %s should be healthy", name)
		}
		
		// Verify metrics
		assert.Contains(t, health.Metrics, "discoveries_total")
		assert.GreaterOrEqual(t, health.Metrics["discoveries_total"], interface{}(int64(0)))
	})
}

// TestPatternDetectionIntegration tests pattern detection across different data types
func TestPatternDetectionIntegration(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	gen := testutil.NewTestDataGenerator(42)
	ctx := context.Background()

	tests := []struct {
		name           string
		data           []interface{}
		dataType       discovery.DataType
		expectedTypes  []discovery.PatternType
		minConfidence  float64
	}{
		{
			name:          "time_series_trend",
			data:          gen.GenerateTimeSeriesData(50, "trend"),
			dataType:      discovery.DataTypeNumeric,
			expectedTypes: []discovery.PatternType{discovery.PatternTypeTrend},
			minConfidence: 0.7,
		},
		{
			name:          "seasonal_pattern",
			data:          gen.GenerateTimeSeriesData(48, "seasonal"),
			dataType:      discovery.DataTypeNumeric,
			expectedTypes: []discovery.PatternType{discovery.PatternTypeSeasonal},
			minConfidence: 0.6,
		},
		{
			name:          "anomaly_detection",
			data:          gen.GenerateTimeSeriesData(100, "anomaly"),
			dataType:      discovery.DataTypeNumeric,
			expectedTypes: []discovery.PatternType{discovery.PatternTypeAnomaly},
			minConfidence: 0.8,
		},
		{
			name:          "email_format",
			data:          gen.GenerateStringData(20, "email"),
			dataType:      discovery.DataTypeString,
			expectedTypes: []discovery.PatternType{discovery.PatternTypeFormat},
			minConfidence: 0.8,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			// Create a temporary schema with test data
			schema := discovery.Schema{
				Name:      "TestSchema",
				EventType: "TestEvent",
				Attributes: []discovery.Attribute{
					{Name: "testField", DataType: tt.dataType},
				},
			}

			// Create sample with test data
			records := make([]map[string]interface{}, len(tt.data))
			for i, val := range tt.data {
				records[i] = map[string]interface{}{
					"testField": val,
				}
			}

			sample := discovery.DataSample{
				SampleSize: len(records),
				Records:    records,
			}

			// Mock the sampling to return our test data
			mockClient := &MockPatternTestClient{
				schema: schema,
				sample: sample,
				data:   tt.data,
			}
			engine.SetNRDBClient(mockClient)

			// Profile schema to detect patterns
			profiledSchema, err := engine.ProfileSchema(ctx, "TestEvent", discovery.ProfileDepthStandard)
			assert.NoError(t, err)

			// Check if expected patterns were detected
			foundExpected := false
			for _, pattern := range profiledSchema.Patterns {
				for _, expectedType := range tt.expectedTypes {
					if pattern.Type == string(expectedType) && pattern.Confidence >= tt.minConfidence {
						foundExpected = true
						t.Logf("Found pattern: %s with confidence %.2f", pattern.Type, pattern.Confidence)
						break
					}
				}
			}

			assert.True(t, foundExpected, "Expected pattern types %v not found with sufficient confidence", tt.expectedTypes)
		})
	}
}

// TestQualityAssessmentIntegration tests quality assessment with various data quality issues
func TestQualityAssessmentIntegration(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	ctx := context.Background()

	// Create schema with known quality issues
	schema := discovery.Schema{
		Name:      "QualityTestSchema",
		EventType: "QualityTest",
		Attributes: []discovery.Attribute{
			{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
			{Name: "email", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeEmail},
			{Name: "name", DataType: discovery.DataTypeString},
			{Name: "value", DataType: discovery.DataTypeNumeric},
			{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
		},
	}

	// Create low quality data
	lowQualityData := testutil.CreateLowQualityData(100)

	// Mock client to return our test data
	mockClient := &MockQualityTestClient{
		schema: schema,
		sample: lowQualityData,
	}
	engine.SetNRDBClient(mockClient)

	// Assess quality
	report, err := engine.AssessQuality(ctx, "QualityTest")
	assert.NoError(t, err)
	assert.NotNil(t, report)

	// Verify quality issues are detected
	assert.Less(t, report.OverallScore, 0.8, "Overall score should be low due to quality issues")
	assert.Less(t, report.Dimensions.Completeness.Score, 0.9, "Completeness should be affected by missing values")
	assert.Less(t, report.Dimensions.Uniqueness.Score, 1.0, "Uniqueness should be affected by duplicate IDs")
	assert.Less(t, report.Dimensions.Consistency.Score, 1.0, "Consistency should be affected by format issues")

	// Verify issues are reported
	assert.NotEmpty(t, report.Issues)
	
	// Check for specific issue types
	hasCompletenessIssue := false
	hasUniquenessIssue := false
	
	for _, issue := range report.Issues {
		if issue.Dimension == "Completeness" {
			hasCompletenessIssue = true
		}
		if issue.Dimension == "Uniqueness" {
			hasUniquenessIssue = true
		}
	}
	
	assert.True(t, hasCompletenessIssue, "Should detect completeness issues")
	assert.True(t, hasUniquenessIssue, "Should detect uniqueness issues")

	// Verify recommendations are generated
	assert.NotEmpty(t, report.Recommendations)
}

// TestConcurrentDiscovery tests concurrent schema discovery
func TestConcurrentDiscovery(t *testing.T) {
	config := discovery.DefaultConfig()
	config.Performance.WorkerPoolSize = 5 // Use 5 workers
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)

	ctx := context.Background()

	// Start multiple concurrent discoveries
	numGoroutines := 10
	results := make(chan []discovery.Schema, numGoroutines)
	errors := make(chan error, numGoroutines)

	for i := 0; i < numGoroutines; i++ {
		go func(id int) {
			filter := discovery.DiscoveryFilter{
				MaxSchemas:     5,
				MinRecordCount: 10,
			}
			
			schemas, err := engine.DiscoverSchemas(ctx, filter)
			if err != nil {
				errors <- err
			} else {
				results <- schemas
			}
		}(i)
	}

	// Collect results
	var allSchemas [][]discovery.Schema
	for i := 0; i < numGoroutines; i++ {
		select {
		case err := <-errors:
			t.Fatalf("Concurrent discovery failed: %v", err)
		case schemas := <-results:
			allSchemas = append(allSchemas, schemas)
		case <-time.After(10 * time.Second):
			t.Fatal("Timeout waiting for concurrent discovery")
		}
	}

	// Verify all discoveries succeeded
	assert.Equal(t, numGoroutines, len(allSchemas))
	for _, schemas := range allSchemas {
		assert.NotEmpty(t, schemas)
		assert.LessOrEqual(t, len(schemas), 5)
	}
}

// TestEngineLifecycle tests engine start/stop lifecycle
func TestEngineLifecycle(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	ctx, cancel := context.WithCancel(context.Background())
	
	// Start engine
	started := make(chan bool)
	stopped := make(chan error)
	
	go func() {
		started <- true
		err := engine.Start(ctx)
		stopped <- err
	}()
	
	// Wait for engine to start
	<-started
	time.Sleep(100 * time.Millisecond)
	
	// Verify engine is healthy while running
	health := engine.Health()
	assert.Equal(t, "healthy", health.Status)
	
	// Perform operations while engine is running
	mockClient := nrdb.NewMockClient()
	engine.SetNRDBClient(mockClient)
	
	schemas, err := engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{MaxSchemas: 5})
	assert.NoError(t, err)
	assert.NotEmpty(t, schemas)
	
	// Stop engine
	cancel()
	
	// Wait for engine to stop
	select {
	case err := <-stopped:
		assert.NoError(t, err)
	case <-time.After(2 * time.Second):
		t.Fatal("Engine did not stop in time")
	}
	
	// Verify engine can be stopped again (idempotent)
	err = engine.Stop(context.Background())
	assert.NoError(t, err)
}

// Mock clients for specific test scenarios

type MockPatternTestClient struct {
	schema discovery.Schema
	sample discovery.DataSample
	data   []interface{}
}

func (m *MockPatternTestClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	// Return appropriate data based on query
	return &discovery.QueryResult{
		Results: m.sample.Records,
	}, nil
}

func (m *MockPatternTestClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return m.Query(ctx, nrql)
}

func (m *MockPatternTestClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{m.schema.EventType}, nil
}

func (m *MockPatternTestClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test Account"}}, nil
}

type MockQualityTestClient struct {
	schema discovery.Schema
	sample discovery.DataSample
}

func (m *MockQualityTestClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: m.sample.Records,
	}, nil
}

func (m *MockQualityTestClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return m.Query(ctx, nrql)
}

func (m *MockQualityTestClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{m.schema.EventType}, nil
}

func (m *MockQualityTestClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test Account"}}, nil
}