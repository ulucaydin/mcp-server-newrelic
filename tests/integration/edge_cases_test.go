package integration_test

import (
	"context"
	"errors"
	"fmt"
	"math"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// TestEdgeCases tests various edge cases and error conditions
func TestEdgeCases(t *testing.T) {
	// Test 1: Empty Results
	t.Run("empty_results", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &EmptyResultsClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		// Should handle empty results gracefully
		schemas, err := engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		assert.NoError(t, err)
		assert.Empty(t, schemas)
	})

	// Test 2: Very Large Schema
	t.Run("large_schema", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &LargeSchemaClient{attributeCount: 1000}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		// Should handle large schemas
		schema, err := engine.ProfileSchema(ctx, "LargeSchema", discovery.ProfileDepthBasic)
		assert.NoError(t, err)
		assert.Equal(t, 1000, len(schema.Attributes))
	})

	// Test 3: Special Characters in Names
	t.Run("special_characters", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &SpecialCharClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		schemas, err := engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		assert.NoError(t, err)
		assert.NotEmpty(t, schemas)
		
		// Verify special characters are handled
		for _, schema := range schemas {
			assert.NotEmpty(t, schema.Name)
			for _, attr := range schema.Attributes {
				assert.NotEmpty(t, attr.Name)
			}
		}
	})

	// Test 4: Null and Missing Values
	t.Run("null_values", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &NullValueClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		// Quality assessment should handle nulls
		report, err := engine.AssessQuality(ctx, "NullSchema")
		assert.NoError(t, err)
		assert.Less(t, report.Dimensions.Completeness.Score, 1.0)
	})

	// Test 5: Timeout Handling
	t.Run("timeout_handling", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &SlowClient{delay: 5 * time.Second}
		engine.SetNRDBClient(mockClient)

		ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
		defer cancel()
		
		// Should respect context timeout
		_, err = engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "context deadline exceeded")
	})

	// Test 6: Invalid Data Types
	t.Run("invalid_data_types", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &InvalidDataClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		// Should handle invalid data gracefully
		schemas, err := engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		assert.NoError(t, err)
		assert.NotEmpty(t, schemas)
		
		// Verify unknown types are handled
		for _, schema := range schemas {
			for _, attr := range schema.Attributes {
				assert.NotEqual(t, "", attr.DataType)
			}
		}
	})

	// Test 7: Circular References in Relationships
	t.Run("circular_relationships", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		// Create schemas with potential circular references
		schemas := []discovery.Schema{
			{
				Name:      "A",
				EventType: "A",
				Attributes: []discovery.Attribute{
					{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
					{Name: "b_id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				},
			},
			{
				Name:      "B",
				EventType: "B",
				Attributes: []discovery.Attribute{
					{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
					{Name: "c_id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				},
			},
			{
				Name:      "C",
				EventType: "C",
				Attributes: []discovery.Attribute{
					{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
					{Name: "a_id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				},
			},
		}

		ctx := context.Background()
		
		// Should handle circular references without infinite loop
		relationships, err := engine.FindRelationships(ctx, schemas)
		assert.NoError(t, err)
		assert.NotEmpty(t, relationships)
	})

	// Test 8: Extreme Values in Pattern Detection
	t.Run("extreme_values", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &ExtremeValueClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		// Should handle extreme values in pattern detection
		schema, err := engine.ProfileSchema(ctx, "ExtremeSchema", discovery.ProfileDepthStandard)
		assert.NoError(t, err)
		assert.NotEmpty(t, schema.Patterns)
	})

	// Test 9: Unicode and International Characters
	t.Run("unicode_handling", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		mockClient := &UnicodeClient{}
		engine.SetNRDBClient(mockClient)

		ctx := context.Background()
		
		schemas, err := engine.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		assert.NoError(t, err)
		assert.NotEmpty(t, schemas)
		
		// Verify unicode is preserved
		foundUnicode := false
		for _, schema := range schemas {
			if schema.Name == "用户数据" || schema.Name == "Données" {
				foundUnicode = true
				break
			}
		}
		assert.True(t, foundUnicode, "Should handle unicode schema names")
	})

	// Test 10: Zero and Negative Values
	t.Run("zero_negative_values", func(t *testing.T) {
		config := discovery.DefaultConfig()
		engine, err := discovery.NewEngine(config)
		require.NoError(t, err)

		// Test with zero schemas requested
		ctx := context.Background()
		filter := discovery.DiscoveryFilter{
			MaxSchemas: 0,
		}
		
		schemas, err := engine.DiscoverSchemas(ctx, filter)
		assert.NoError(t, err)
		assert.Empty(t, schemas)
		
		// Test with negative time range (should be handled gracefully)
		mockClient := &EdgeCaseTimeClient{}
		engine.SetNRDBClient(mockClient)
		
		report, err := engine.AssessQuality(ctx, "TestSchema")
		assert.NoError(t, err)
		assert.NotNil(t, report)
	})
}

// Mock clients for edge case testing

type EmptyResultsClient struct{}

func (c *EmptyResultsClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{Results: []map[string]interface{}{}}, nil
}

func (c *EmptyResultsClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *EmptyResultsClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{}, nil
}

func (c *EmptyResultsClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{}, nil
}

type LargeSchemaClient struct {
	attributeCount int
}

func (c *LargeSchemaClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	records := make([]map[string]interface{}, 10)
	for i := 0; i < 10; i++ {
		record := make(map[string]interface{})
		for j := 0; j < c.attributeCount; j++ {
			record[fmt.Sprintf("attr_%d", j)] = fmt.Sprintf("value_%d_%d", i, j)
		}
		records[i] = record
	}
	return &discovery.QueryResult{Results: records}, nil
}

func (c *LargeSchemaClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *LargeSchemaClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"LargeSchema"}, nil
}

func (c *LargeSchemaClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type SpecialCharClient struct{}

func (c *SpecialCharClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{
				"attr-with-dash":   "value1",
				"attr.with.dots":   "value2",
				"attr_with_under":  "value3",
				"attr with spaces": "value4",
				"attr@special":     "value5",
			},
		},
	}, nil
}

func (c *SpecialCharClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *SpecialCharClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"Schema-With-Dash", "Schema.With.Dots", "Schema With Spaces"}, nil
}

func (c *SpecialCharClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type NullValueClient struct{}

func (c *NullValueClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{"id": "1", "name": "Test", "value": 10.0},
			{"id": "2", "name": nil, "value": 20.0},
			{"id": "3", "value": nil},
			{"id": "4", "name": "", "value": 0.0},
		},
	}, nil
}

func (c *NullValueClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *NullValueClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"NullSchema"}, nil
}

func (c *NullValueClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type SlowClient struct {
	delay time.Duration
}

func (c *SlowClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(c.delay):
		return &discovery.QueryResult{}, nil
	}
}

func (c *SlowClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *SlowClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	select {
	case <-ctx.Done():
		return nil, ctx.Err()
	case <-time.After(c.delay):
		return []string{"SlowSchema"}, nil
	}
}

func (c *SlowClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type InvalidDataClient struct{}

func (c *InvalidDataClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{
				"valid_string": "test",
				"valid_number": 42.0,
				"invalid_type": struct{ X int }{X: 1}, // Unsupported type
				"channel":      make(chan int),         // Invalid type
				"func":         func() {},              // Invalid type
			},
		},
	}, nil
}

func (c *InvalidDataClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *InvalidDataClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"InvalidSchema"}, nil
}

func (c *InvalidDataClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type ExtremeValueClient struct{}

func (c *ExtremeValueClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{"value": 1e-10},    // Very small
			{"value": 1e10},     // Very large
			{"value": -1e10},    // Very negative
			{"value": 0.0},      // Zero
			{"value": math.Inf(1)},  // Positive infinity
			{"value": math.Inf(-1)}, // Negative infinity
			{"value": math.NaN()},   // NaN
		},
	}, nil
}

func (c *ExtremeValueClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *ExtremeValueClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"ExtremeSchema"}, nil
}

func (c *ExtremeValueClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}

type UnicodeClient struct{}

func (c *UnicodeClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{
				"名前":     "田中",
				"città":   "Roma",
				"emoji":   "🚀",
				"russian": "Привет",
				"arabic":  "مرحبا",
			},
		},
	}, nil
}

func (c *UnicodeClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *UnicodeClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"用户数据", "Données", "UnicodeTest"}, nil
}

func (c *UnicodeClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "テスト"}}, nil
}

type EdgeCaseTimeClient struct{}

func (c *EdgeCaseTimeClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	return &discovery.QueryResult{
		Results: []map[string]interface{}{
			{
				"id":        "1",
				"timestamp": time.Now().Add(24 * time.Hour), // Future timestamp
			},
			{
				"id":        "2",
				"timestamp": time.Time{}, // Zero time
			},
		},
	}, nil
}

func (c *EdgeCaseTimeClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	return c.Query(ctx, nrql)
}

func (c *EdgeCaseTimeClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	return []string{"TestSchema"}, nil
}

func (c *EdgeCaseTimeClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	return []discovery.Account{{AccountID: "123456", Name: "Test"}}, nil
}