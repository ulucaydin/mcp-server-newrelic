package discovery_test

import (
	"context"
	"testing"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/nrdb"
)

func TestEngineCreation(t *testing.T) {
	// Create mock config
	config := &discovery.Config{
		NRDB: discovery.NRDBConfig{
			BaseURL:    "https://api.newrelic.com",
			APIKey:     "test-api-key",
			AccountID:  "123456",
			Timeout:    30 * time.Second,
			MaxRetries: 3,
			RateLimit:  60,
		},
		Discovery: discovery.DiscoveryConfig{
			MaxConcurrency:    5,
			DefaultSampleSize: 100,
			MaxSampleSize:     1000,
			DiscoveryTimeout:  1 * time.Minute,
			CacheTTL:          5 * time.Minute,
			EnableMLPatterns:  false,
			MinSchemaRecords:  10,
			ProfileDepth:      discovery.ProfileDepthBasic,
		},
		Cache: discovery.CacheConfig{
			Enabled:    false,
			DefaultTTL: 5 * time.Minute,
		},
		Performance: discovery.PerformanceConfig{
			WorkerPoolSize: 5,
			QueryBatchSize: 10,
		},
		Observability: discovery.ObservabilityConfig{
			MetricsEnabled: false,
			LogLevel:       "info",
		},
	}
	
	// Create engine
	engine, err := discovery.NewEngine(config)
	if err != nil {
		t.Fatalf("Failed to create engine: %v", err)
	}
	
	// Check health
	health := engine.Health()
	if health.Status != "healthy" {
		t.Errorf("Expected healthy status, got %s", health.Status)
	}
}

func TestMockNRDBClient(t *testing.T) {
	// Create mock client
	client := nrdb.NewMockClient()
	
	// Test GetEventTypes
	ctx := context.Background()
	eventTypes, err := client.GetEventTypes(ctx, discovery.EventTypeFilter{})
	if err != nil {
		t.Fatalf("Failed to get event types: %v", err)
	}
	
	// Should have default mock schemas
	if len(eventTypes) == 0 {
		t.Error("Expected at least one event type")
	}
	
	// Test Query
	result, err := client.Query(ctx, "SELECT * FROM Transaction LIMIT 10")
	if err != nil {
		t.Fatalf("Failed to execute query: %v", err)
	}
	
	if len(result.Results) == 0 {
		t.Error("Expected query results")
	}
}

func TestRateLimiter(t *testing.T) {
	// Create rate limiter - 10 requests per second
	limiter := nrdb.NewRateLimiter(10, time.Second)
	
	ctx := context.Background()
	
	// Should be able to make 10 requests immediately
	for i := 0; i < 10; i++ {
		if err := limiter.Wait(ctx); err != nil {
			t.Fatalf("Request %d failed: %v", i+1, err)
		}
	}
	
	// 11th request should take time
	start := time.Now()
	if err := limiter.Wait(ctx); err != nil {
		t.Fatalf("11th request failed: %v", err)
	}
	
	// Should have waited at least some time
	elapsed := time.Since(start)
	if elapsed < 50*time.Millisecond {
		t.Errorf("Expected rate limiting delay, but elapsed time was %v", elapsed)
	}
}