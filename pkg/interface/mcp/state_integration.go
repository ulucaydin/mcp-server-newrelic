package mcp

import (
	"context"
	"fmt"
	"sync"
	"time"
	
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/state"
)

// StateAwareSessionManager wraps our state manager to implement MCP's SessionManager interface
type StateAwareSessionManager struct {
	stateManager state.StateManager
	mcpManager   *state.MCPSessionManager
	mu           sync.RWMutex
}

// NewStateAwareSessionManager creates a new session manager backed by state management
func NewStateAwareSessionManager(stateManager state.StateManager) SessionManager {
	return &StateAwareSessionManager{
		stateManager: stateManager,
		mcpManager:   state.NewMCPSessionManager(stateManager),
	}
}

// Create creates a new session with discovery context
func (sm *StateAwareSessionManager) Create() *Session {
	ctx := context.Background()
	
	// Create state session with default goal
	stateSession, err := sm.mcpManager.StartDiscoverySession(ctx, "MCP interactive session")
	if err != nil {
		// Fallback to simple session
		return &Session{
			ID:        generateSessionID(),
			CreatedAt: time.Now(),
			LastUsed:  time.Now(),
			Context:   make(map[string]interface{}),
		}
	}
	
	// Convert to MCP session
	return &Session{
		ID:        stateSession.ID,
		CreatedAt: stateSession.CreatedAt,
		LastUsed:  stateSession.LastAccess,
		Context:   stateSession.Context,
	}
}

// Get retrieves a session by ID
func (sm *StateAwareSessionManager) Get(id string) (*Session, bool) {
	ctx := context.Background()
	
	stateSession, err := sm.stateManager.GetSession(ctx, id)
	if err != nil {
		return nil, false
	}
	
	// Convert to MCP session
	return &Session{
		ID:        stateSession.ID,
		CreatedAt: stateSession.CreatedAt,
		LastUsed:  stateSession.LastAccess,
		Context:   stateSession.Context,
	}, true
}

// Update updates a session
func (sm *StateAwareSessionManager) Update(session *Session) error {
	ctx := context.Background()
	
	// Get existing state session
	stateSession, err := sm.stateManager.GetSession(ctx, session.ID)
	if err != nil {
		return fmt.Errorf("session not found: %w", err)
	}
	
	// Update context
	stateSession.Context = session.Context
	stateSession.LastAccess = time.Now()
	
	return sm.stateManager.UpdateSession(ctx, stateSession)
}

// Delete removes a session
func (sm *StateAwareSessionManager) Delete(id string) error {
	ctx := context.Background()
	
	// End discovery session
	if err := sm.mcpManager.EndDiscoverySession(ctx, id); err != nil {
		// Log error but continue
	}
	
	return sm.stateManager.DeleteSession(ctx, id)
}

// Cleanup removes expired sessions
func (sm *StateAwareSessionManager) Cleanup() error {
	ctx := context.Background()
	return sm.stateManager.CleanupExpired(ctx)
}

// EnhancedServer extends the MCP server with state management
type EnhancedServer struct {
	*Server
	stateManager state.StateManager
	mcpManager   *state.MCPSessionManager
}

// NewEnhancedServer creates a new MCP server with state management
func NewEnhancedServer(config ServerConfig, stateManager state.StateManager) *EnhancedServer {
	// Create base server
	baseServer := NewServer(config)
	
	// Replace session manager with state-aware version
	baseServer.sessions = NewStateAwareSessionManager(stateManager)
	
	return &EnhancedServer{
		Server:       baseServer,
		stateManager: stateManager,
		mcpManager:   state.NewMCPSessionManager(stateManager),
	}
}

// ExecuteToolWithState executes a tool with state management
func (es *EnhancedServer) ExecuteToolWithState(ctx context.Context, sessionID string, toolName string, params map[string]interface{}) (interface{}, error) {
	// Get tool
	tool, exists := es.tools.Get(toolName)
	if !exists {
		return nil, fmt.Errorf("tool not found: %s", toolName)
	}
	
	// Record tool execution start
	es.stateManager.SetContext(ctx, sessionID, fmt.Sprintf("tool:%s:start", toolName), time.Now())
	
	// Check cache for similar requests
	cacheKey := fmt.Sprintf("tool:%s:%v", toolName, params)
	if cached, found := es.stateManager.Get(ctx, cacheKey); found {
		// Return cached result
		es.stateManager.SetContext(ctx, sessionID, fmt.Sprintf("tool:%s:cache_hit", toolName), true)
		return cached, nil
	}
	
	// Execute tool
	result, err := tool.Handler(ctx, params)
	if err != nil {
		es.stateManager.SetContext(ctx, sessionID, fmt.Sprintf("tool:%s:error", toolName), err.Error())
		return nil, err
	}
	
	// Cache result
	es.stateManager.Set(ctx, cacheKey, result, 5*time.Minute)
	
	// Record completion
	es.stateManager.SetContext(ctx, sessionID, fmt.Sprintf("tool:%s:end", toolName), time.Now())
	
	// If this is a discovery tool, record in session
	if isDiscoveryTool(toolName) {
		es.recordDiscoveryResult(ctx, sessionID, toolName, params, result)
	}
	
	return result, nil
}

// recordDiscoveryResult records discovery results in the session
func (es *EnhancedServer) recordDiscoveryResult(ctx context.Context, sessionID string, toolName string, params map[string]interface{}, result interface{}) {
	// Extract schema name from params if available
	schemaName := ""
	if schema, ok := params["schema"].(string); ok {
		schemaName = schema
	} else if eventType, ok := params["event_type"].(string); ok {
		schemaName = eventType
	}
	
	if schemaName != "" {
		// Record discovery
		es.mcpManager.RecordDiscovery(ctx, sessionID, schemaName, result)
	}
}

// GetSessionContext retrieves the full discovery context for a session
func (es *EnhancedServer) GetSessionContext(ctx context.Context, sessionID string) (*state.DiscoveryContext, error) {
	return es.mcpManager.GetDiscoveryContext(ctx, sessionID)
}

// WarmCache pre-loads commonly accessed data for a session
func (es *EnhancedServer) WarmCache(ctx context.Context, sessionID string) error {
	return es.stateManager.WarmCache(ctx, sessionID)
}

// Helper functions

func isDiscoveryTool(toolName string) bool {
	discoveryTools := []string{
		"discovery.list_schemas",
		"discovery.profile_schema",
		"discovery.profile_attribute",
		"discovery.find_relationships",
		"discovery.assess_quality",
	}
	
	for _, dt := range discoveryTools {
		if toolName == dt {
			return true
		}
	}
	
	return false
}