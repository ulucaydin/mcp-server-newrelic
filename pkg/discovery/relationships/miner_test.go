package relationships_test

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/relationships"
)

// MockNRDBClient for testing
type MockNRDBClient struct {
	mock.Mock
}

func (m *MockNRDBClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	args := m.Called(ctx, nrql)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*discovery.QueryResult), args.Error(1)
}

func (m *MockNRDBClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	args := m.Called(ctx, nrql, opts)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*discovery.QueryResult), args.Error(1)
}

func (m *MockNRDBClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	args := m.Called(ctx, filter)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]string), args.Error(1)
}

func (m *MockNRDBClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	args := m.Called(ctx)
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).([]discovery.Account), args.Error(1)
}

func TestMiner_FindRelationships(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	config := relationships.DefaultConfig()
	miner := relationships.NewMiner(mockNRDB, config)

	ctx := context.Background()

	// Create test schemas
	schemas := []discovery.Schema{
		{
			Name:      "Transaction",
			EventType: "Transaction",
			Attributes: []discovery.Attribute{
				{Name: "transactionId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "duration", DataType: discovery.DataTypeNumeric},
				{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
			},
		},
		{
			Name:      "User",
			EventType: "User",
			Attributes: []discovery.Attribute{
				{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "email", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeEmail},
				{Name: "createdAt", DataType: discovery.DataTypeTimestamp},
			},
		},
		{
			Name:      "PageView",
			EventType: "PageView",
			Attributes: []discovery.Attribute{
				{Name: "pageId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
				{Name: "duration", DataType: discovery.DataTypeNumeric},
			},
		},
	}

	relationships, err := miner.FindRelationships(ctx, schemas)
	require.NoError(t, err)
	assert.NotEmpty(t, relationships)

	// Check for expected relationships
	foundJoins := 0
	foundTemporal := 0
	
	for _, rel := range relationships {
		switch rel.Type {
		case discovery.RelationshipTypeJoin:
			foundJoins++
			// Should find userId as common join key
			if rel.JoinKeys != nil {
				assert.Contains(t, []string{"userId"}, rel.JoinKeys.SourceKey)
			}
		case discovery.RelationshipTypeTemporal:
			foundTemporal++
		}
	}

	assert.Greater(t, foundJoins, 0, "Should find join relationships")
	assert.Greater(t, foundTemporal, 0, "Should find temporal relationships")
}

func TestMiner_JoinRelationships(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	config := relationships.DefaultConfig()
	miner := relationships.NewMiner(mockNRDB, config)

	ctx := context.Background()

	tests := []struct {
		name          string
		schema1       discovery.Schema
		schema2       discovery.Schema
		expectJoin    bool
		expectJoinKey string
	}{
		{
			name: "common ID field",
			schema1: discovery.Schema{
				Name: "Orders",
				Attributes: []discovery.Attribute{
					{Name: "orderId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
					{Name: "customerId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				},
			},
			schema2: discovery.Schema{
				Name: "Customers",
				Attributes: []discovery.Attribute{
					{Name: "customerId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
					{Name: "email", DataType: discovery.DataTypeString},
				},
			},
			expectJoin:    true,
			expectJoinKey: "customerId",
		},
		{
			name: "no common fields",
			schema1: discovery.Schema{
				Name: "Products",
				Attributes: []discovery.Attribute{
					{Name: "productId", DataType: discovery.DataTypeString},
					{Name: "name", DataType: discovery.DataTypeString},
				},
			},
			schema2: discovery.Schema{
				Name: "Logs",
				Attributes: []discovery.Attribute{
					{Name: "message", DataType: discovery.DataTypeString},
					{Name: "level", DataType: discovery.DataTypeString},
				},
			},
			expectJoin: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			schemas := []discovery.Schema{tt.schema1, tt.schema2}
			relationships, err := miner.FindRelationships(ctx, schemas)
			require.NoError(t, err)

			foundJoin := false
			foundKey := ""
			
			for _, rel := range relationships {
				if rel.Type == discovery.RelationshipTypeJoin {
					foundJoin = true
					if rel.JoinKeys != nil {
						foundKey = rel.JoinKeys.SourceKey
					}
					break
				}
			}

			assert.Equal(t, tt.expectJoin, foundJoin)
			if tt.expectJoin {
				assert.Equal(t, tt.expectJoinKey, foundKey)
			}
		})
	}
}

func TestMiner_TemporalRelationships(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	config := relationships.DefaultConfig()
	miner := relationships.NewMiner(mockNRDB, config)

	ctx := context.Background()

	// Schemas with timestamp fields
	schemas := []discovery.Schema{
		{
			Name: "Events",
			Attributes: []discovery.Attribute{
				{Name: "eventId", DataType: discovery.DataTypeString},
				{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
			},
		},
		{
			Name: "Metrics",
			Attributes: []discovery.Attribute{
				{Name: "metricName", DataType: discovery.DataTypeString},
				{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
				{Name: "value", DataType: discovery.DataTypeNumeric},
			},
		},
		{
			Name: "NoTimestamp",
			Attributes: []discovery.Attribute{
				{Name: "id", DataType: discovery.DataTypeString},
				{Name: "name", DataType: discovery.DataTypeString},
			},
		},
	}

	relationships, err := miner.FindRelationships(ctx, schemas)
	require.NoError(t, err)

	// Count temporal relationships
	temporalCount := 0
	for _, rel := range relationships {
		if rel.Type == discovery.RelationshipTypeTemporal {
			temporalCount++
			// Should only find temporal relationships between schemas with timestamps
			assert.NotEqual(t, "NoTimestamp", rel.SourceSchema)
			assert.NotEqual(t, "NoTimestamp", rel.TargetSchema)
		}
	}

	// Should find temporal relationship between Events and Metrics
	assert.Greater(t, temporalCount, 0)
}

func TestMiner_SemanticRelationships(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	config := relationships.DefaultConfig()
	miner := relationships.NewMiner(mockNRDB, config)

	ctx := context.Background()

	// Schemas with hierarchical naming
	schemas := []discovery.Schema{
		{Name: "Application", Attributes: []discovery.Attribute{{Name: "appId", DataType: discovery.DataTypeString}}},
		{Name: "ApplicationTransaction", Attributes: []discovery.Attribute{{Name: "transactionId", DataType: discovery.DataTypeString}}},
		{Name: "Host", Attributes: []discovery.Attribute{{Name: "hostId", DataType: discovery.DataTypeString}}},
		{Name: "HostProcess", Attributes: []discovery.Attribute{{Name: "processId", DataType: discovery.DataTypeString}}},
	}

	relationships, err := miner.FindRelationships(ctx, schemas)
	require.NoError(t, err)

	// Check for hierarchical relationships
	hierarchyCount := 0
	for _, rel := range relationships {
		if rel.Type == discovery.RelationshipTypeHierarchy {
			hierarchyCount++
			t.Logf("Found hierarchy: %s -> %s", rel.SourceSchema, rel.TargetSchema)
		}
	}

	assert.Greater(t, hierarchyCount, 0, "Should find hierarchical relationships")
}

func TestMiner_RelationshipGraph(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	config := relationships.DefaultConfig()
	miner := relationships.NewMiner(mockNRDB, config)

	// Create test relationships
	testRelationships := []discovery.Relationship{
		{
			Type:         discovery.RelationshipTypeJoin,
			SourceSchema: "Orders",
			TargetSchema: "Customers",
			Confidence:   0.9,
		},
		{
			Type:         discovery.RelationshipTypeJoin,
			SourceSchema: "Orders",
			TargetSchema: "Products",
			Confidence:   0.8,
		},
		{
			Type:         discovery.RelationshipTypeJoin,
			SourceSchema: "Orders",
			TargetSchema: "Shipping",
			Confidence:   0.7,
		},
		{
			Type:         discovery.RelationshipTypeTemporal,
			SourceSchema: "Customers",
			TargetSchema: "Events",
			Confidence:   0.85,
		},
	}

	graph := miner.AnalyzeRelationshipGraph(testRelationships)

	// Verify graph analysis
	assert.Equal(t, 5, graph.Nodes) // 5 unique schemas
	assert.Equal(t, 4, graph.Edges) // 4 relationships
	assert.NotEmpty(t, graph.Hubs)
	assert.Contains(t, graph.Hubs, "Orders") // Orders connects to 3 other schemas
	assert.Greater(t, graph.AverageDegree, 0.0)
}

func TestMiner_Configuration(t *testing.T) {
	mockNRDB := new(MockNRDBClient)
	
	// Test with custom configuration
	config := relationships.Config{
		MinCorrelation:    0.9,
		MinSampleSize:     1000,
		MaxJoinCandidates: 10,
		EnableMLDetection: true,
		ParallelWorkers:   8,
	}
	
	miner := relationships.NewMiner(mockNRDB, config)
	assert.NotNil(t, miner)

	// Test with default configuration
	defaultConfig := relationships.DefaultConfig()
	assert.Equal(t, 0.7, defaultConfig.MinCorrelation)
	assert.Equal(t, 100, defaultConfig.MinSampleSize)
	assert.Equal(t, 50, defaultConfig.MaxJoinCandidates)
	assert.False(t, defaultConfig.EnableMLDetection)
	assert.Equal(t, 4, defaultConfig.ParallelWorkers)
}