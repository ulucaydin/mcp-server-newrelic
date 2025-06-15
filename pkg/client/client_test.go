package client

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewClient(t *testing.T) {
	tests := []struct {
		name   string
		config Config
		want   Config
	}{
		{
			name:   "Default config",
			config: Config{},
			want: Config{
				BaseURL:   "http://localhost:8080/api/v1",
				UserAgent: "uds-go-client/1.0.0",
			},
		},
		{
			name: "Custom config",
			config: Config{
				BaseURL:   "https://api.example.com",
				APIKey:    "test-key",
				RetryMax:  5,
				RetryWait: 2 * time.Second,
			},
			want: Config{
				BaseURL:   "https://api.example.com",
				UserAgent: "uds-go-client/1.0.0",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			client, err := NewClient(tt.config)
			require.NoError(t, err)
			assert.Equal(t, tt.want.BaseURL, client.baseURL)
			assert.Equal(t, tt.want.UserAgent, client.userAgent)
			assert.NotNil(t, client.Discovery)
			assert.NotNil(t, client.Patterns)
			assert.NotNil(t, client.Query)
			assert.NotNil(t, client.Dashboard)
		})
	}
}

func TestClient_Health(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/api/v1/health", r.URL.Path)
		assert.Equal(t, "GET", r.Method)
		
		health := HealthStatus{
			Status:  "healthy",
			Version: "1.0.0",
			Uptime:  "24h",
			Components: map[string]map[string]interface{}{
				"discovery": {
					"status": "healthy",
				},
			},
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(health)
	}))
	defer server.Close()

	client, err := NewClient(Config{BaseURL: server.URL + "/api/v1"})
	require.NoError(t, err)

	ctx := context.Background()
	health, err := client.Health(ctx)
	require.NoError(t, err)
	assert.Equal(t, "healthy", health.Status)
	assert.Equal(t, "1.0.0", health.Version)
}

func TestClient_ErrorHandling(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		apiErr := APIError{
			ErrorType: "not_found",
			Message:   "Resource not found",
			Details: map[string]interface{}{
				"resource": "schema",
			},
		}
		
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(apiErr)
	}))
	defer server.Close()

	client, err := NewClient(Config{BaseURL: server.URL + "/api/v1"})
	require.NoError(t, err)

	ctx := context.Background()
	_, err = client.Health(ctx)
	require.Error(t, err)
	
	apiErr, ok := err.(*APIError)
	require.True(t, ok)
	assert.Equal(t, 404, apiErr.StatusCode)
	assert.Equal(t, "Resource not found", apiErr.Message)
}

func TestDiscoveryService_ListSchemas(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		assert.Equal(t, "/api/v1/discovery/schemas", r.URL.Path)
		assert.Equal(t, "GET", r.Method)
		
		// Check query parameters
		assert.Equal(t, "Transaction", r.URL.Query().Get("eventType"))
		assert.Equal(t, "1000", r.URL.Query().Get("minRecordCount"))
		assert.Equal(t, "10", r.URL.Query().Get("maxSchemas"))
		assert.Equal(t, "true", r.URL.Query().Get("includeMetadata"))
		
		resp := ListSchemasResponse{
			Schemas: []Schema{
				{
					Name:        "Transaction",
					EventType:   "Transaction",
					RecordCount: 1000000,
					Quality: QualityMetrics{
						OverallScore: 0.85,
					},
				},
			},
			Metadata: &DiscoveryMetadata{
				TotalSchemas:  1,
				ExecutionTime: "100ms",
				CacheHit:      false,
			},
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(resp)
	}))
	defer server.Close()

	client, err := NewClient(Config{BaseURL: server.URL + "/api/v1"})
	require.NoError(t, err)

	ctx := context.Background()
	opts := &ListSchemasOptions{
		EventType:       "Transaction",
		MinRecordCount:  1000,
		MaxSchemas:      10,
		IncludeMetadata: true,
	}
	
	resp, err := client.Discovery.ListSchemas(ctx, opts)
	require.NoError(t, err)
	assert.Len(t, resp.Schemas, 1)
	assert.Equal(t, "Transaction", resp.Schemas[0].Name)
	assert.NotNil(t, resp.Metadata)
	assert.Equal(t, "100ms", resp.Metadata.ExecutionTime)
}

func TestRetryLogic(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		if attempts < 3 {
			w.WriteHeader(http.StatusServiceUnavailable)
			return
		}
		
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(HealthStatus{Status: "healthy"})
	}))
	defer server.Close()

	client, err := NewClient(Config{
		BaseURL:   server.URL + "/api/v1",
		RetryMax:  3,
		RetryWait: 10 * time.Millisecond,
	})
	require.NoError(t, err)

	ctx := context.Background()
	health, err := client.Health(ctx)
	require.NoError(t, err)
	assert.Equal(t, "healthy", health.Status)
	assert.Equal(t, 3, attempts)
}