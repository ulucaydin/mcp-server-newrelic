//go:build test || nodiscovery

package mcp

import (
	"context"
	"fmt"
	"sync"
)

// Server implements the Model Context Protocol server (without discovery dependency)
type Server struct {
	// MCP components
	transport  Transport
	tools      ToolRegistry
	sessions   SessionManager
	protocol   *ProtocolHandler
	
	// Configuration
	config     ServerConfig
	
	// Internal state
	mu         sync.RWMutex
	running    bool
	shutdownCh chan struct{}
}

// NewServer creates a new MCP server instance
func NewServer(config ServerConfig) *Server {
	s := &Server{
		config:     config,
		tools:      NewToolRegistry(),
		sessions:   NewSessionManager(),
		shutdownCh: make(chan struct{}),
	}
	
	s.protocol = &ProtocolHandler{
		server:   s,
		requests: sync.Map{},
	}
	
	return s
}

// SetDiscoveryEngine is a no-op in test mode
func (s *Server) SetDiscoveryEngine(engine interface{}) {
	// No-op for testing
}

// Start starts the MCP server
func (s *Server) Start(ctx context.Context) error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("server already running")
	}
	
	// Create transport based on type
	transport, err := s.createTransport()
	if err != nil {
		s.mu.Unlock()
		return fmt.Errorf("failed to create transport: %w", err)
	}
	s.transport = transport
	
	// Register built-in tools (without discovery tools)
	s.registerBuiltinTools()
	
	s.running = true
	s.mu.Unlock()
	
	// Start transport
	return s.transport.Start(ctx, s)
}

// Stop gracefully stops the server
func (s *Server) Stop(ctx context.Context) error {
	s.mu.Lock()
	if !s.running {
		s.mu.Unlock()
		return nil
	}
	
	s.running = false
	close(s.shutdownCh)
	s.mu.Unlock()
	
	if s.transport != nil {
		return s.transport.Close()
	}
	
	return nil
}

// HandleMessage processes incoming JSON-RPC messages
func (s *Server) HandleMessage(ctx context.Context, message []byte) ([]byte, error) {
	return s.protocol.HandleMessage(ctx, message)
}

// HandleStreamingMessage processes streaming messages
func (s *Server) HandleStreamingMessage(ctx context.Context, message []byte, stream chan<- StreamChunk) error {
	// For now, just handle as regular message
	resp, err := s.HandleMessage(ctx, message)
	if err != nil {
		stream <- StreamChunk{Type: "error", Error: err}
		return err
	}
	stream <- StreamChunk{Type: "result", Data: resp}
	close(stream)
	return nil
}

// OnError handles transport errors
func (s *Server) OnError(err error) {
	// Log error (in production would use proper logging)
	fmt.Printf("Transport error: %v\n", err)
}

// GetInfo returns server information
func (s *Server) GetInfo() map[string]interface{} {
	return map[string]interface{}{
		"protocol_version": "1.0",
		"server_name":      "MCP Server",
		"capabilities": map[string]interface{}{
			"tools":     true,
			"streaming": s.config.StreamingEnabled,
			"sessions":  true,
		},
	}
}

// createTransport creates the appropriate transport based on config
func (s *Server) createTransport() (Transport, error) {
	switch s.config.TransportType {
	case TransportStdio:
		return NewStdioTransport(), nil
	case TransportHTTP:
		addr := fmt.Sprintf("%s:%d", s.config.HTTPHost, s.config.HTTPPort)
		return NewHTTPTransport(addr), nil
	case TransportSSE:
		addr := fmt.Sprintf("%s:%d", s.config.HTTPHost, s.config.HTTPPort)
		return NewSSETransport(addr), nil
	default:
		return nil, fmt.Errorf("unsupported transport type: %s", s.config.TransportType)
	}
}

// registerBuiltinTools registers the built-in MCP tools
func (s *Server) registerBuiltinTools() {
	// Session management tools
	s.tools.Register(Tool{
		Name:        "session.create",
		Description: "Create a new session",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			session := s.sessions.Create()
			return map[string]interface{}{
				"session_id": session.ID,
				"created_at": session.CreatedAt,
			}, nil
		},
	})
	
	s.tools.Register(Tool{
		Name:        "session.end",
		Description: "End a session",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"session_id": {
					Type:        "string",
					Description: "Session ID to end",
				},
			},
			Required: []string{"session_id"},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			sessionID, _ := params["session_id"].(string)
			if err := s.sessions.Delete(sessionID); err != nil {
				return nil, err
			}
			return map[string]string{"status": "ended"}, nil
		},
	})
}