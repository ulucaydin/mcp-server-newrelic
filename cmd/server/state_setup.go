package main

import (
	"context"
	"log"
	"os"
	"time"
	
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/config"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/interface/mcp"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/state"
	"github.com/newrelic/go-agent/v3/newrelic"
)

// setupStateManagement initializes the state management system
func setupStateManagement(cfg *config.Config) (state.StateManager, error) {
	log.Println("Initializing state management...")
	
	// Create state manager from environment configuration
	stateManager, err := state.CreateStateManagerFromEnv()
	if err != nil {
		// Fallback to default in-memory state manager
		log.Printf("Warning: Failed to create state manager from env, using in-memory: %v", err)
		
		config := state.DefaultManagerConfig()
		stateManager = state.NewManager(config)
	}
	
	log.Printf("State management initialized with store type: %s", getStoreType())
	
	return stateManager, nil
}

// createMCPServerWithState creates an MCP server with state management
func createMCPServerWithState(cfg *config.Config, stateManager state.StateManager) (*mcp.EnhancedServer, error) {
	// Set transport type based on configuration
	var transportType mcp.TransportType
	switch cfg.Server.MCPTransport {
	case "stdio":
		transportType = mcp.TransportStdio
	case "http":
		transportType = mcp.TransportHTTP
	case "sse":
		transportType = mcp.TransportSSE
	default:
		transportType = mcp.TransportStdio
	}
	
	mcpConfig := mcp.ServerConfig{
		TransportType:    transportType,
		MaxConcurrent:    cfg.Server.MaxConcurrentRequests,
		RequestTimeout:   cfg.Server.RequestTimeout,
		StreamingEnabled: true,
		AuthEnabled:      cfg.Security.AuthEnabled,
		HTTPHost:         cfg.Server.Host,
		HTTPPort:         cfg.Server.MCPHTTPPort,
	}
	
	// Create enhanced server with state management
	server := mcp.NewEnhancedServer(mcpConfig, stateManager)
	
	return server, nil
}

// instrumentStateManager adds APM instrumentation to state operations
func instrumentStateManager(stateManager state.StateManager, nrApp *newrelic.Application) state.StateManager {
	if nrApp == nil {
		return stateManager
	}
	
	// Wrap state manager with APM instrumentation
	return &instrumentedStateManager{
		StateManager: stateManager,
		nrApp:       nrApp,
	}
}

type instrumentedStateManager struct {
	state.StateManager
	nrApp *newrelic.Application
}

func (ism *instrumentedStateManager) CreateSession(ctx context.Context, goal string) (*state.Session, error) {
	txn := ism.nrApp.StartTransaction("StateManager.CreateSession")
	defer txn.End()
	
	txn.AddAttribute("session.goal", goal)
	ctx = newrelic.NewContext(ctx, txn)
	
	session, err := ism.StateManager.CreateSession(ctx, goal)
	if err != nil {
		txn.NoticeError(err)
		return nil, err
	}
	
	txn.AddAttribute("session.id", session.ID)
	return session, nil
}

func (ism *instrumentedStateManager) Get(ctx context.Context, key string) (interface{}, bool) {
	segment := newrelic.FromContext(ctx).StartSegment("StateManager.Cache.Get")
	defer segment.End()
	
	value, found := ism.StateManager.Get(ctx, key)
	
	segment.AddAttribute("cache.hit", found)
	segment.AddAttribute("cache.key", key)
	
	return value, found
}

func (ism *instrumentedStateManager) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	segment := newrelic.FromContext(ctx).StartSegment("StateManager.Cache.Set")
	defer segment.End()
	
	segment.AddAttribute("cache.key", key)
	segment.AddAttribute("cache.ttl", ttl.String())
	
	return ism.StateManager.Set(ctx, key, value, ttl)
}

// getStoreType returns the configured store type
func getStoreType() string {
	storeType := os.Getenv("STATE_STORE_TYPE")
	if storeType == "" {
		return "memory"
	}
	return storeType
}