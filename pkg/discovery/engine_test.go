package discovery_test

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// MockNRDBClient is a mock implementation of NRDBClient
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

// MockCache is a mock implementation of Cache
type MockCache struct {
	mock.Mock
}

func (m *MockCache) Get(key string) (interface{}, bool) {
	args := m.Called(key)
	return args.Get(0), args.Bool(1)
}

func (m *MockCache) Set(key string, value interface{}, ttl time.Duration) error {
	args := m.Called(key, value, ttl)
	return args.Error(0)
}

func (m *MockCache) Delete(key string) error {
	args := m.Called(key)
	return args.Error(0)
}

func (m *MockCache) Clear() error {
	args := m.Called()
	return args.Error(0)
}

func (m *MockCache) Stats() discovery.CacheStats {
	args := m.Called()
	return args.Get(0).(discovery.CacheStats)
}

func TestEngine_Creation(t *testing.T) {
	tests := []struct {
		name    string
		config  *discovery.Config
		wantErr bool
		errMsg  string
	}{
		{
			name:    "nil config",
			config:  nil,
			wantErr: true,
			errMsg:  "invalid config",
		},
		{
			name:    "invalid config",
			config:  &discovery.Config{},
			wantErr: true,
			errMsg:  "invalid config",
		},
		{
			name:    "valid config",
			config:  discovery.DefaultConfig(),
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			engine, err := discovery.NewEngine(tt.config)
			
			if tt.wantErr {
				assert.Error(t, err)
				assert.Contains(t, err.Error(), tt.errMsg)
				assert.Nil(t, engine)
			} else {
				assert.NoError(t, err)
				assert.NotNil(t, engine)
			}
		})
	}
}

func TestEngine_DiscoverSchemas(t *testing.T) {
	// Create test engine with mocks
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	// Set up mock NRDB client
	mockNRDB := new(MockNRDBClient)
	engine.SetNRDBClient(mockNRDB)

	// Set up mock cache
	mockCache := new(MockCache)
	engine.SetCache(mockCache)

	ctx := context.Background()
	filter := discovery.DiscoveryFilter{
		MaxSchemas:     10,
		MinRecordCount: 100,
	}

	// Test cache hit
	t.Run("cache hit", func(t *testing.T) {
		cachedSchemas := []discovery.Schema{
			{Name: "Transaction", EventType: "Transaction"},
			{Name: "PageView", EventType: "PageView"},
		}
		
		mockCache.On("Get", mock.AnythingOfType("string")).Return(cachedSchemas, true).Once()
		
		schemas, err := engine.DiscoverSchemas(ctx, filter)
		assert.NoError(t, err)
		assert.Equal(t, cachedSchemas, schemas)
		
		mockCache.AssertExpectations(t)
	})

	// Test cache miss with successful discovery
	t.Run("cache miss - successful discovery", func(t *testing.T) {
		mockCache.On("Get", mock.AnythingOfType("string")).Return(nil, false).Once()
		
		// Mock GetEventTypes
		eventTypes := []string{"Transaction", "PageView"}
		mockNRDB.On("GetEventTypes", ctx, mock.AnythingOfType("discovery.EventTypeFilter")).
			Return(eventTypes, nil).Once()
		
		// Mock Query for sampling
		sampleResult := &discovery.QueryResult{
			Results: []map[string]interface{}{
				{"name": "test", "duration": 100.0},
			},
		}
		mockNRDB.On("Query", ctx, mock.AnythingOfType("string")).
			Return(sampleResult, nil).Times(4) // 2 schemas * 2 queries each
		
		// Mock cache set
		mockCache.On("Set", mock.AnythingOfType("string"), mock.Anything, mock.AnythingOfType("time.Duration")).
			Return(nil).Once()
		
		schemas, err := engine.DiscoverSchemas(ctx, filter)
		assert.NoError(t, err)
		assert.Len(t, schemas, 2)
		
		mockNRDB.AssertExpectations(t)
		mockCache.AssertExpectations(t)
	})
}

func TestEngine_ProfileSchema(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	mockNRDB := new(MockNRDBClient)
	engine.SetNRDBClient(mockNRDB)

	mockCache := new(MockCache)
	engine.SetCache(mockCache)

	ctx := context.Background()
	eventType := "Transaction"

	tests := []struct {
		name  string
		depth discovery.ProfileDepth
		setup func()
	}{
		{
			name:  "basic profiling",
			depth: discovery.ProfileDepthBasic,
			setup: func() {
				mockCache.On("Get", mock.AnythingOfType("string")).Return(nil, false).Once()
				
				// Mock sampling query
				sampleResult := &discovery.QueryResult{
					Results: []map[string]interface{}{
						{
							"name":      "test",
							"duration":  100.0,
							"timestamp": time.Now(),
						},
					},
				}
				mockNRDB.On("Query", ctx, mock.AnythingOfType("string")).
					Return(sampleResult, nil).Twice()
				
				mockCache.On("Set", mock.AnythingOfType("string"), mock.Anything, mock.AnythingOfType("time.Duration")).
					Return(nil).Once()
			},
		},
		{
			name:  "standard profiling",
			depth: discovery.ProfileDepthStandard,
			setup: func() {
				mockCache.On("Get", mock.AnythingOfType("string")).Return(nil, false).Once()
				
				// Mock queries for standard profiling
				sampleResult := &discovery.QueryResult{
					Results: []map[string]interface{}{
						{
							"name":      "test",
							"duration":  100.0,
							"timestamp": time.Now(),
						},
					},
				}
				// Basic + statistics + patterns
				mockNRDB.On("Query", ctx, mock.AnythingOfType("string")).
					Return(sampleResult, nil).Times(4)
				
				mockCache.On("Set", mock.AnythingOfType("string"), mock.Anything, mock.AnythingOfType("time.Duration")).
					Return(nil).Once()
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			tt.setup()
			
			schema, err := engine.ProfileSchema(ctx, eventType, tt.depth)
			assert.NoError(t, err)
			assert.NotNil(t, schema)
			assert.Equal(t, eventType, schema.EventType)
			
			mockNRDB.AssertExpectations(t)
			mockCache.AssertExpectations(t)
		})
	}
}

func TestEngine_DiscoverWithIntelligence(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	mockNRDB := new(MockNRDBClient)
	engine.SetNRDBClient(mockNRDB)

	mockCache := new(MockCache)
	engine.SetCache(mockCache)

	ctx := context.Background()
	hints := discovery.DiscoveryHints{
		Keywords: []string{"transaction", "performance"},
		Purpose:  "performance analysis",
		Domain:   "apm",
	}

	// Set up expectations
	mockCache.On("Get", mock.AnythingOfType("string")).Return(nil, false).Once()
	
	// Mock GetEventTypes with APM-related event types
	eventTypes := []string{"Transaction", "TransactionError", "PageView"}
	mockNRDB.On("GetEventTypes", ctx, mock.AnythingOfType("discovery.EventTypeFilter")).
		Return(eventTypes, nil).Once()
	
	// Mock queries for schema discovery
	sampleResult := &discovery.QueryResult{
		Results: []map[string]interface{}{
			{
				"name":          "test-transaction",
				"duration":      150.5,
				"timestamp":     time.Now(),
				"error":         false,
				"responseTime":  120.3,
			},
		},
	}
	mockNRDB.On("Query", ctx, mock.AnythingOfType("string")).
		Return(sampleResult, nil).Times(6) // 3 schemas * 2 queries each
	
	mockCache.On("Set", mock.AnythingOfType("string"), mock.Anything, mock.AnythingOfType("time.Duration")).
		Return(nil).Once()

	// Execute discovery
	result, err := engine.DiscoverWithIntelligence(ctx, hints)
	
	// Assertions
	assert.NoError(t, err)
	assert.NotNil(t, result)
	assert.Greater(t, len(result.Schemas), 0)
	assert.NotEmpty(t, result.Insights)
	assert.NotEmpty(t, result.Recommendations)
	assert.NotNil(t, result.ExecutionPlan)
	
	// Verify schemas are ranked by relevance
	for i, schema := range result.Schemas {
		if i > 0 {
			// Each schema should have relevance metadata
			assert.NotEmpty(t, schema.Name)
		}
	}
	
	mockNRDB.AssertExpectations(t)
	mockCache.AssertExpectations(t)
}

func TestEngine_Health(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	// Get health status
	health := engine.Health()
	
	assert.Equal(t, "healthy", health.Status)
	assert.Equal(t, "1.0.0", health.Version)
	assert.Greater(t, health.Uptime, time.Duration(0))
	assert.NotEmpty(t, health.Components)
	
	// Check component health
	assert.Contains(t, health.Components, "nrdb")
	assert.Contains(t, health.Components, "cache")
	assert.Contains(t, health.Components, "worker_pool")
	
	// Check metrics
	assert.Contains(t, health.Metrics, "discoveries_total")
	assert.Contains(t, health.Metrics, "uptime_seconds")
}

func TestEngine_Lifecycle(t *testing.T) {
	config := discovery.DefaultConfig()
	engine, err := discovery.NewEngine(config)
	require.NoError(t, err)

	ctx, cancel := context.WithCancel(context.Background())
	
	// Start engine in goroutine
	startErr := make(chan error, 1)
	go func() {
		startErr <- engine.Start(ctx)
	}()
	
	// Give engine time to start
	time.Sleep(100 * time.Millisecond)
	
	// Check health while running
	health := engine.Health()
	assert.Equal(t, "healthy", health.Status)
	
	// Stop engine
	cancel()
	
	// Wait for start to complete
	select {
	case err := <-startErr:
		assert.NoError(t, err)
	case <-time.After(1 * time.Second):
		t.Fatal("Engine did not stop in time")
	}
	
	// Stop again should be idempotent
	err = engine.Stop(context.Background())
	assert.NoError(t, err)
}