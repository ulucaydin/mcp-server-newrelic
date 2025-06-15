package nrdb

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

)

// MockClient is a mock implementation of NRDBClient for testing
type MockClient struct {
	// Predefined schemas and data
	schemas map[string]MockSchema
	
	// Behavior controls
	shouldFail     bool
	failureMessage string
	latency        time.Duration
	
	// Metrics
	queryCount int
}

// MockSchema represents a mock schema with sample data
type MockSchema struct {
	EventType   string
	Attributes  []string
	SampleData  []map[string]interface{}
	RecordCount int64
}

// NewMockClient creates a new mock NRDB client
func NewMockClient() *MockClient {
	return &MockClient{
		schemas: createDefaultMockSchemas(),
		latency: 10 * time.Millisecond,
	}
}

// Query executes a mock query
func (m *MockClient) Query(ctx context.Context, nrql string) (*QueryResult, error) {
	return m.QueryWithOptions(ctx, nrql, QueryOptions{})
}

// QueryWithOptions executes a mock query with options
func (m *MockClient) QueryWithOptions(ctx context.Context, nrql string, opts QueryOptions) (*QueryResult, error) {
	m.queryCount++
	
	// Simulate latency
	if m.latency > 0 {
		select {
		case <-time.After(m.latency):
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	
	// Check for failure
	if m.shouldFail {
		return nil, fmt.Errorf("mock error: %s", m.failureMessage)
	}
	
	// Parse query to determine what to return
	result := &QueryResult{
		Results: []map[string]interface{}{},
		Metadata: QueryMetadata{
			EventTypes: []string{},
		},
	}
	
	// Handle different query types
	switch {
	case contains(nrql, "SHOW EVENT TYPES"):
		return m.handleShowEventTypes(nrql)
		
	case contains(nrql, "SELECT"):
		return m.handleSelect(nrql)
		
	case contains(nrql, "keyset()"):
		return m.handleKeyset(nrql)
		
	default:
		return result, nil
	}
}

// GetEventTypes returns mock event types
func (m *MockClient) GetEventTypes(ctx context.Context, filter EventTypeFilter) ([]string, error) {
	if m.shouldFail {
		return nil, fmt.Errorf("mock error: %s", m.failureMessage)
	}
	
	eventTypes := make([]string, 0, len(m.schemas))
	for eventType, schema := range m.schemas {
		// Apply filters
		if filter.MinRecordCount > 0 && schema.RecordCount < int64(filter.MinRecordCount) {
			continue
		}
		
		if filter.Pattern != "" && !matchesPattern(eventType, filter.Pattern) {
			continue
		}
		
		eventTypes = append(eventTypes, eventType)
	}
	
	return eventTypes, nil
}

// GetAccountInfo returns mock account info
func (m *MockClient) GetAccountInfo(ctx context.Context) (*AccountInfo, error) {
	if m.shouldFail {
		return nil, fmt.Errorf("mock error: %s", m.failureMessage)
	}
	
	return &AccountInfo{
		AccountID:     "123456",
		AccountName:   "Mock Account",
		DataRetention: 30,
		EventTypes:    m.getEventTypeList(),
		Limits: AccountLimits{
			MaxQueryDuration:   5 * time.Minute,
			MaxResultsPerQuery: 2000,
			RateLimitPerMinute: 60,
		},
	}, nil
}

// Mock control methods

// SetShouldFail sets whether the mock should fail
func (m *MockClient) SetShouldFail(shouldFail bool, message string) {
	m.shouldFail = shouldFail
	m.failureMessage = message
}

// SetLatency sets the simulated latency
func (m *MockClient) SetLatency(latency time.Duration) {
	m.latency = latency
}

// AddMockSchema adds a mock schema
func (m *MockClient) AddMockSchema(schema MockSchema) {
	m.schemas[schema.EventType] = schema
}

// GetQueryCount returns the number of queries executed
func (m *MockClient) GetQueryCount() int {
	return m.queryCount
}

// Private helper methods

func (m *MockClient) handleShowEventTypes(nrql string) (*QueryResult, error) {
	results := make([]map[string]interface{}, 0, len(m.schemas))
	
	for eventType, schema := range m.schemas {
		results = append(results, map[string]interface{}{
			"eventType": eventType,
			"count":     float64(schema.RecordCount),
		})
	}
	
	return &QueryResult{
		Results: results,
		Metadata: QueryMetadata{
			EventTypes: m.getEventTypeList(),
		},
	}, nil
}

func (m *MockClient) handleSelect(nrql string) (*QueryResult, error) {
	// Extract event type from query
	eventType := extractEventType(nrql)
	schema, ok := m.schemas[eventType]
	if !ok {
		return &QueryResult{Results: []map[string]interface{}{}}, nil
	}
	
	// Return sample data or count
	if contains(nrql, "count(*)") {
		return &QueryResult{
			Results: []map[string]interface{}{
				{"count": float64(schema.RecordCount)},
			},
		}, nil
	}
	
	// Return sample records
	limit := 100
	if len(schema.SampleData) < limit {
		limit = len(schema.SampleData)
	}
	
	return &QueryResult{
		Results: schema.SampleData[:limit],
		Metadata: QueryMetadata{
			EventTypes: []string{eventType},
		},
	}, nil
}

func (m *MockClient) handleKeyset(nrql string) (*QueryResult, error) {
	eventType := extractEventType(nrql)
	schema, ok := m.schemas[eventType]
	if !ok {
		return &QueryResult{Results: []map[string]interface{}{}}, nil
	}
	
	// Return keyset
	keyset := make([]string, len(schema.Attributes))
	copy(keyset, schema.Attributes)
	
	return &QueryResult{
		Results: []map[string]interface{}{
			{"keyset": keyset},
		},
	}, nil
}

func (m *MockClient) getEventTypeList() []string {
	eventTypes := make([]string, 0, len(m.schemas))
	for et := range m.schemas {
		eventTypes = append(eventTypes, et)
	}
	return eventTypes
}

// Helper functions

func contains(s, substr string) bool {
	return strings.Contains(strings.ToUpper(s), strings.ToUpper(substr))
}

func extractEventType(nrql string) string {
	// Simple extraction - find FROM clause
	parts := strings.Split(strings.ToUpper(nrql), "FROM")
	if len(parts) < 2 {
		return ""
	}
	
	// Extract event type
	words := strings.Fields(parts[1])
	if len(words) > 0 {
		return strings.Trim(words[0], "`")
	}
	
	return ""
}


// createDefaultMockSchemas creates default mock schemas
func createDefaultMockSchemas() map[string]MockSchema {
	schemas := make(map[string]MockSchema)
	
	// Transaction schema
	schemas["Transaction"] = MockSchema{
		EventType: "Transaction",
		Attributes: []string{
			"duration", "name", "error", "timestamp", "appName",
			"host", "request.uri", "response.status", "databaseCallCount",
		},
		RecordCount: 2500000,
		SampleData:  generateTransactionData(100),
	}
	
	// PageView schema
	schemas["PageView"] = MockSchema{
		EventType: "PageView",
		Attributes: []string{
			"duration", "timestamp", "userAgent", "countryCode",
			"city", "deviceType", "pageUrl", "referrerUrl",
		},
		RecordCount: 1800000,
		SampleData:  generatePageViewData(100),
	}
	
	// NrConsumption schema
	schemas["NrConsumption"] = MockSchema{
		EventType: "NrConsumption",
		Attributes: []string{
			"cost", "usage", "service", "timestamp", "metric",
		},
		RecordCount: 50000,
		SampleData:  generateConsumptionData(100),
	}
	
	// Log schema
	schemas["Log"] = MockSchema{
		EventType: "Log",
		Attributes: []string{
			"message", "level", "timestamp", "service.name",
			"host.name", "trace.id", "span.id",
		},
		RecordCount: 5000000,
		SampleData:  generateLogData(100),
	}
	
	// Metric schema
	schemas["Metric"] = MockSchema{
		EventType: "Metric",
		Attributes: []string{
			"metricName", "value", "timestamp", "host",
			"app", "component", "unit",
		},
		RecordCount: 10000000,
		SampleData:  generateMetricData(100),
	}
	
	return schemas
}

// Data generation functions

func generateTransactionData(count int) []map[string]interface{} {
	data := make([]map[string]interface{}, count)
	endpoints := []string{"/api/users", "/api/orders", "/api/products", "/api/checkout", "/api/login"}
	hosts := []string{"server-1", "server-2", "server-3"}
	
	for i := 0; i < count; i++ {
		data[i] = map[string]interface{}{
			"duration":          rand.Float64() * 5.0,
			"name":              endpoints[rand.Intn(len(endpoints))],
			"error":             rand.Float64() < 0.05, // 5% error rate
			"timestamp":         time.Now().Add(-time.Duration(rand.Intn(3600)) * time.Second).Unix(),
			"appName":           "mock-app",
			"host":              hosts[rand.Intn(len(hosts))],
			"request.uri":       endpoints[rand.Intn(len(endpoints))],
			"response.status":   200 + rand.Intn(300),
			"databaseCallCount": float64(rand.Intn(10)),
		}
	}
	
	return data
}

func generatePageViewData(count int) []map[string]interface{} {
	data := make([]map[string]interface{}, count)
	countries := []string{"US", "GB", "DE", "JP", "BR"}
	devices := []string{"Desktop", "Mobile", "Tablet"}
	pages := []string{"/home", "/products", "/about", "/contact", "/blog"}
	
	for i := 0; i < count; i++ {
		data[i] = map[string]interface{}{
			"duration":     rand.Float64() * 10.0,
			"timestamp":    time.Now().Add(-time.Duration(rand.Intn(3600)) * time.Second).Unix(),
			"userAgent":    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
			"countryCode":  countries[rand.Intn(len(countries))],
			"city":         "City" + fmt.Sprintf("%d", rand.Intn(100)),
			"deviceType":   devices[rand.Intn(len(devices))],
			"pageUrl":      pages[rand.Intn(len(pages))],
			"referrerUrl":  "https://google.com",
		}
	}
	
	return data
}

func generateConsumptionData(count int) []map[string]interface{} {
	data := make([]map[string]interface{}, count)
	services := []string{"APM", "Infrastructure", "Logs", "Synthetics", "Browser"}
	
	for i := 0; i < count; i++ {
		data[i] = map[string]interface{}{
			"cost":      rand.Float64() * 1000,
			"usage":     float64(rand.Intn(1000000)),
			"service":   services[rand.Intn(len(services))],
			"timestamp": time.Now().Add(-time.Duration(rand.Intn(86400)) * time.Second).Unix(),
			"metric":    "consumption",
		}
	}
	
	return data
}

func generateLogData(count int) []map[string]interface{} {
	data := make([]map[string]interface{}, count)
	levels := []string{"INFO", "WARN", "ERROR", "DEBUG"}
	services := []string{"api-service", "auth-service", "payment-service"}
	
	for i := 0; i < count; i++ {
		data[i] = map[string]interface{}{
			"message":      fmt.Sprintf("Log message %d", i),
			"level":        levels[rand.Intn(len(levels))],
			"timestamp":    time.Now().Add(-time.Duration(rand.Intn(3600)) * time.Second).Unix(),
			"service.name": services[rand.Intn(len(services))],
			"host.name":    fmt.Sprintf("host-%d", rand.Intn(10)),
			"trace.id":     fmt.Sprintf("%016x", rand.Int63()),
			"span.id":      fmt.Sprintf("%016x", rand.Int63()),
		}
	}
	
	return data
}

func generateMetricData(count int) []map[string]interface{} {
	data := make([]map[string]interface{}, count)
	metrics := []string{"cpu.usage", "memory.usage", "disk.io", "network.throughput"}
	
	for i := 0; i < count; i++ {
		data[i] = map[string]interface{}{
			"metricName": metrics[rand.Intn(len(metrics))],
			"value":      rand.Float64() * 100,
			"timestamp":  time.Now().Add(-time.Duration(rand.Intn(3600)) * time.Second).Unix(),
			"host":       fmt.Sprintf("host-%d", rand.Intn(10)),
			"app":        "mock-app",
			"component":  "mock-component",
			"unit":       "percent",
		}
	}
	
	return data
}