package mcp

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"
)

// SSETransport implements MCP over Server-Sent Events
type SSETransport struct {
	*HTTPTransport
	connections sync.Map // connection ID -> *SSEConnection
	mu          sync.RWMutex
}

// SSEConnection represents a single SSE client connection
type SSEConnection struct {
	ID       string
	Writer   http.ResponseWriter
	Flusher  http.Flusher
	Messages chan SSEMessage
	Done     chan struct{}
}

// SSEMessage represents a server-sent event
type SSEMessage struct {
	Event string      `json:"event"`
	Data  interface{} `json:"data"`
}

// NewSSETransport creates a new SSE transport
func NewSSETransport(addr string) *SSETransport {
	httpTransport := NewHTTPTransport(addr)
	
	return &SSETransport{
		HTTPTransport: httpTransport,
	}
}

// Start begins listening for SSE connections
func (t *SSETransport) Start(ctx context.Context, handler MessageHandler) error {
	t.mu.Lock()
	t.handler = handler
	t.mu.Unlock()
	
	// Setup routes
	t.mux.HandleFunc("/mcp", t.handleMCP)
	t.mux.HandleFunc("/mcp/stream", t.handleSSE)
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

// handleSSE handles SSE connections
func (t *SSETransport) handleSSE(w http.ResponseWriter, r *http.Request) {
	// Check if SSE is supported
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming not supported", http.StatusInternalServerError)
		return
	}
	
	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("X-Accel-Buffering", "no") // Disable Nginx buffering
	
	// CORS headers for browser clients
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
	
	// Handle OPTIONS for CORS
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	
	// Create connection
	conn := &SSEConnection{
		ID:       generateConnectionID(),
		Writer:   w,
		Flusher:  flusher,
		Messages: make(chan SSEMessage, 100),
		Done:     make(chan struct{}),
	}
	
	// Register connection
	t.connections.Store(conn.ID, conn)
	defer t.connections.Delete(conn.ID)
	
	// Send initial connection event
	t.sendSSE(conn, SSEMessage{
		Event: "connected",
		Data: map[string]string{
			"connectionId": conn.ID,
			"timestamp":    time.Now().Format(time.RFC3339),
		},
	})
	
	// Start heartbeat
	heartbeat := time.NewTicker(30 * time.Second)
	defer heartbeat.Stop()
	
	// Message loop
	for {
		select {
		case msg := <-conn.Messages:
			if err := t.sendSSE(conn, msg); err != nil {
				return
			}
			
		case <-heartbeat.C:
			if err := t.sendHeartbeat(conn); err != nil {
				return
			}
			
		case <-r.Context().Done():
			t.sendSSE(conn, SSEMessage{
				Event: "disconnected",
				Data:  map[string]string{"reason": "client_disconnect"},
			})
			return
			
		case <-conn.Done:
			return
		}
	}
}

// SendToConnection sends a message to a specific SSE connection
func (t *SSETransport) SendToConnection(connID string, message SSEMessage) error {
	if conn, ok := t.connections.Load(connID); ok {
		connection := conn.(*SSEConnection)
		select {
		case connection.Messages <- message:
			return nil
		default:
			return fmt.Errorf("connection %s message buffer full", connID)
		}
	}
	return fmt.Errorf("connection %s not found", connID)
}

// BroadcastMessage sends a message to all SSE connections
func (t *SSETransport) BroadcastMessage(message SSEMessage) {
	t.connections.Range(func(key, value interface{}) bool {
		conn := value.(*SSEConnection)
		select {
		case conn.Messages <- message:
			// Sent successfully
		default:
			// Connection is slow, skip
		}
		return true
	})
}

// sendSSE sends an SSE message to a connection
func (t *SSETransport) sendSSE(conn *SSEConnection, msg SSEMessage) error {
	data, err := json.Marshal(msg.Data)
	if err != nil {
		return fmt.Errorf("marshal data: %w", err)
	}
	
	// Format SSE message
	_, err = fmt.Fprintf(conn.Writer, "event: %s\n", msg.Event)
	if err != nil {
		return err
	}
	
	_, err = fmt.Fprintf(conn.Writer, "data: %s\n\n", data)
	if err != nil {
		return err
	}
	
	conn.Flusher.Flush()
	return nil
}

// sendHeartbeat sends a keepalive message
func (t *SSETransport) sendHeartbeat(conn *SSEConnection) error {
	return t.sendSSE(conn, SSEMessage{
		Event: "heartbeat",
		Data: map[string]interface{}{
			"timestamp": time.Now().Unix(),
		},
	})
}

// generateConnectionID creates a unique connection ID
func generateConnectionID() string {
	return fmt.Sprintf("conn_%d_%d", time.Now().UnixNano(), generateRandomInt())
}

// generateRandomInt generates a random integer
func generateRandomInt() int64 {
	return time.Now().UnixNano()
}