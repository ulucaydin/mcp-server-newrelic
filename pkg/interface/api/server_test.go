package api

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/gorilla/mux"
)

func TestServerLifecycle(t *testing.T) {
	config := Config{
		Host:         "localhost",
		Port:         0, // Use random port
		ReadTimeout:  5 * time.Second,
		WriteTimeout: 5 * time.Second,
	}

	handler := NewHandler()
	server := NewServer(config, handler)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Start server in goroutine
	errChan := make(chan error, 1)
	go func() {
		errChan <- server.Start(ctx)
	}()

	// Give server time to start
	time.Sleep(100 * time.Millisecond)

	// Stop server
	stopCtx, stopCancel := context.WithTimeout(context.Background(), 2*time.Second)
	defer stopCancel()

	if err := server.Stop(stopCtx); err != nil {
		t.Fatalf("Failed to stop server: %v", err)
	}

	// Cancel context
	cancel()

	// Check for errors
	select {
	case err := <-errChan:
		if err != nil && err != context.Canceled {
			t.Fatalf("Server error: %v", err)
		}
	case <-time.After(1 * time.Second):
		t.Fatal("Server did not stop")
	}
}

func TestHealthEndpoint(t *testing.T) {
	handler := NewHandler()
	
	req := httptest.NewRequest("GET", "/api/v1/health", nil)
	w := httptest.NewRecorder()

	handler.GetHealth(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if result["status"] == nil {
		t.Error("Response missing status field")
	}
}

func TestListSchemasEndpoint(t *testing.T) {
	handler := NewHandler()
	
	// Test without metadata
	req := httptest.NewRequest("GET", "/api/v1/discovery/schemas", nil)
	w := httptest.NewRecorder()

	handler.ListSchemas(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if result["schemas"] == nil {
		t.Error("Response missing schemas field")
	}

	// Test with metadata
	req = httptest.NewRequest("GET", "/api/v1/discovery/schemas?includeMetadata=true", nil)
	w = httptest.NewRecorder()

	handler.ListSchemas(w, req)

	resp = w.Result()
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if result["metadata"] == nil {
		t.Error("Response missing metadata field when requested")
	}
}

func TestGetSchemaProfileEndpoint(t *testing.T) {
	handler := NewHandler()
	router := mux.NewRouter()
	router.HandleFunc("/api/v1/discovery/schemas/{eventType}", handler.GetSchemaProfile)

	// Test existing schema
	req := httptest.NewRequest("GET", "/api/v1/discovery/schemas/Transaction", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	// Test non-existent schema
	req = httptest.NewRequest("GET", "/api/v1/discovery/schemas/NonExistent", nil)
	w = httptest.NewRecorder()

	router.ServeHTTP(w, req)

	resp = w.Result()
	if resp.StatusCode != http.StatusNotFound {
		t.Errorf("Expected status 404, got %d", resp.StatusCode)
	}
}

func TestFindRelationshipsEndpoint(t *testing.T) {
	handler := NewHandler()

	// Test valid request
	body := map[string]interface{}{
		"schemas": []string{"Transaction", "PageView"},
	}
	bodyBytes, _ := json.Marshal(body)

	req := httptest.NewRequest("POST", "/api/v1/discovery/relationships", bytes.NewReader(bodyBytes))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()

	handler.FindRelationships(w, req)

	resp := w.Result()
	if resp.StatusCode != http.StatusOK {
		t.Errorf("Expected status 200, got %d", resp.StatusCode)
	}

	var result map[string]interface{}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		t.Fatalf("Failed to decode response: %v", err)
	}

	if result["relationships"] == nil {
		t.Error("Response missing relationships field")
	}
}

func TestMiddleware(t *testing.T) {
	// Test request ID middleware
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Context().Value("requestID")
		if requestID == nil {
			t.Error("Request ID not found in context")
		}
		w.WriteHeader(http.StatusOK)
	})

	wrapped := requestIDMiddleware(handler)
	
	req := httptest.NewRequest("GET", "/test", nil)
	w := httptest.NewRecorder()

	wrapped.ServeHTTP(w, req)

	if w.Header().Get("X-Request-ID") == "" {
		t.Error("X-Request-ID header not set")
	}
}

func TestRateLimiting(t *testing.T) {
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	})

	// Create rate limiter with 60 requests per minute (1 per second)
	limited := rateLimitMiddleware(60)(handler)

	// Make 10 requests quickly (should succeed due to burst)
	for i := 0; i < 10; i++ {
		req := httptest.NewRequest("GET", "/test", nil)
		req.RemoteAddr = "127.0.0.1:1234"
		w := httptest.NewRecorder()
		limited.ServeHTTP(w, req)
		
		if w.Code != http.StatusOK {
			t.Errorf("Request %d failed with status %d", i+1, w.Code)
		}
	}

	// 11th request should be rate limited (burst is 10)
	req := httptest.NewRequest("GET", "/test", nil)
	req.RemoteAddr = "127.0.0.1:1234"
	w := httptest.NewRecorder()
	limited.ServeHTTP(w, req)

	if w.Code != http.StatusTooManyRequests {
		t.Errorf("Expected rate limit status 429, got %d", w.Code)
	}
}