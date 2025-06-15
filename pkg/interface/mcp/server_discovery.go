//go:build !test && !nodiscovery

package mcp

import (
	"context"
	"fmt"
	"sync"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// Server implements the Model Context Protocol server
type Server struct {
	// Core services - interfaces from Track 1
	discovery discovery.DiscoveryEngine
	// TODO: Add patterns, query, dashboard when Track 3/4 complete
	
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

// SetDiscovery sets the discovery engine from Track 1
func (s *Server) SetDiscovery(engine discovery.DiscoveryEngine) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.discovery = engine
}

// Start initializes and starts the MCP server
func (s *Server) Start(ctx context.Context) error {
	s.mu.Lock()
	if s.running {
		s.mu.Unlock()
		return fmt.Errorf("server already running")
	}
	s.running = true
	s.mu.Unlock()
	
	// Register all tools
	if err := s.registerTools(); err != nil {
		return fmt.Errorf("failed to register tools: %w", err)
	}
	
	// Initialize transport
	transport, err := s.createTransport()
	if err != nil {
		return fmt.Errorf("failed to create transport: %w", err)
	}
	s.transport = transport
	
	// Start transport
	if err := s.transport.Start(ctx, s.protocol); err != nil {
		return fmt.Errorf("failed to start transport: %w", err)
	}
	
	// Start background workers
	go s.sessionCleanup(ctx)
	
	return nil
}

// Stop gracefully shuts down the server
func (s *Server) Stop(ctx context.Context) error {
	s.mu.Lock()
	if !s.running {
		s.mu.Unlock()
		return nil
	}
	s.running = false
	close(s.shutdownCh)
	s.mu.Unlock()
	
	// Close transport
	if s.transport != nil {
		if err := s.transport.Close(); err != nil {
			return fmt.Errorf("failed to close transport: %w", err)
		}
	}
	
	// Cleanup sessions
	if err := s.sessions.Cleanup(); err != nil {
		return fmt.Errorf("failed to cleanup sessions: %w", err)
	}
	
	return nil
}

// createTransport creates the appropriate transport based on configuration
func (s *Server) createTransport() (Transport, error) {
	switch s.config.TransportType {
	case TransportStdio:
		return NewStdioTransport(), nil
	case TransportHTTP:
		return NewHTTPTransport(fmt.Sprintf("%s:%d", s.config.HTTPHost, s.config.HTTPPort)), nil
	case TransportSSE:
		return NewSSETransport(fmt.Sprintf("%s:%d", s.config.HTTPHost, s.config.HTTPPort)), nil
	default:
		return nil, fmt.Errorf("unsupported transport type: %s", s.config.TransportType)
	}
}

// sessionCleanup periodically cleans up expired sessions
func (s *Server) sessionCleanup(ctx context.Context) {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			return
		case <-s.shutdownCh:
			return
		case <-ticker.C:
			s.sessions.Cleanup()
		}
	}
}

// GetInfo returns server information for MCP discovery
func (s *Server) GetInfo() map[string]interface{} {
	return map[string]interface{}{
		"name":        "Universal Data Synthesizer",
		"version":     "2.0.0",
		"description": "AI-powered New Relic dashboard creation",
		"tools":       s.tools.List(),
	}
}