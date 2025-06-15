package mcp

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"sync"
	"time"
)

// HTTPTransport implements MCP over HTTP
type HTTPTransport struct {
	server  *http.Server
	handler MessageHandler
	mux     *http.ServeMux
	mu      sync.RWMutex
}

// NewHTTPTransport creates a new HTTP transport
func NewHTTPTransport(addr string) *HTTPTransport {
	mux := http.NewServeMux()
	
	return &HTTPTransport{
		server: &http.Server{
			Addr:         addr,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
			Handler:      mux,
		},
		mux: mux,
	}
}

// Start begins listening for HTTP requests
func (t *HTTPTransport) Start(ctx context.Context, handler MessageHandler) error {
	t.mu.Lock()
	t.handler = handler
	t.mu.Unlock()
	
	// Setup routes
	t.mux.HandleFunc("/mcp", t.handleMCP)
	t.mux.HandleFunc("/health", t.handleHealth)
	
	// Start server in goroutine
	errChan := make(chan error, 1)
	go func() {
		if err := t.server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errChan <- err
		}
	}()
	
	// Wait for context or error
	select {
	case <-ctx.Done():
		return t.server.Shutdown(context.Background())
	case err := <-errChan:
		return err
	}
}

// Send is not used for HTTP transport (responses are sent via HTTP response)
func (t *HTTPTransport) Send(message []byte) error {
	// HTTP transport sends responses directly in the HTTP handler
	return nil
}

// Close shuts down the HTTP server
func (t *HTTPTransport) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return t.server.Shutdown(ctx)
}

// handleMCP handles MCP requests
func (t *HTTPTransport) handleMCP(w http.ResponseWriter, r *http.Request) {
	// Only accept POST
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Check content type
	contentType := r.Header.Get("Content-Type")
	if contentType != "application/json" && contentType != "application/json-rpc" {
		http.Error(w, "Invalid content type", http.StatusBadRequest)
		return
	}
	
	// Read body
	body, err := io.ReadAll(io.LimitReader(r.Body, 10*1024*1024)) // 10MB limit
	if err != nil {
		http.Error(w, "Failed to read request body", http.StatusBadRequest)
		return
	}
	defer r.Body.Close()
	
	// Get handler
	t.mu.RLock()
	handler := t.handler
	t.mu.RUnlock()
	
	if handler == nil {
		http.Error(w, "Server not initialized", http.StatusInternalServerError)
		return
	}
	
	// Handle message
	response, err := handler.HandleMessage(r.Context(), body)
	if err != nil {
		handler.OnError(fmt.Errorf("handle message: %w", err))
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}
	
	// Send response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	
	if response != nil {
		if _, err := w.Write(response); err != nil {
			handler.OnError(fmt.Errorf("write response: %w", err))
		}
	}
}

// handleHealth provides a health check endpoint
func (t *HTTPTransport) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"healthy"}`))
}