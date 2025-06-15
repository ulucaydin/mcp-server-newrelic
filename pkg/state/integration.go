package state

import (
	"context"
	"fmt"
	"os"
	"time"
)

// CreateStateManagerFromEnv creates a state manager based on environment configuration
func CreateStateManagerFromEnv() (StateManager, error) {
	storeType := os.Getenv("STATE_STORE_TYPE")
	if storeType == "" {
		storeType = "memory"
	}
	
	// Parse common configuration
	sessionTTL := parseDuration(os.Getenv("SESSION_TTL"), 1*time.Hour)
	cacheTTL := parseDuration(os.Getenv("CACHE_TTL"), 5*time.Minute)
	
	config := FactoryConfig{
		StoreType: StoreType(storeType),
		ManagerConfig: ManagerConfig{
			SessionTTL:      sessionTTL,
			CacheTTL:        cacheTTL,
			MaxSessions:     parseInt(os.Getenv("MAX_SESSIONS"), 10000),
			MaxCacheEntries: parseInt(os.Getenv("MAX_CACHE_ENTRIES"), 100000),
			MaxCacheMemory:  parseInt64(os.Getenv("MAX_CACHE_MEMORY"), 1<<30), // 1GB default
		},
	}
	
	// Configure Redis if needed
	if storeType == "redis" {
		redisURL := os.Getenv("REDIS_URL")
		if redisURL == "" {
			redisURL = "redis://localhost:6379"
		}
		
		config.RedisConfig = &RedisConfig{
			URL:        redisURL,
			MaxRetries: parseInt(os.Getenv("REDIS_MAX_RETRIES"), 3),
			PoolSize:   parseInt(os.Getenv("REDIS_POOL_SIZE"), 10),
			KeyPrefix:  os.Getenv("REDIS_KEY_PREFIX"),
			DefaultTTL: sessionTTL,
		}
		
		if config.RedisConfig.KeyPrefix == "" {
			config.RedisConfig.KeyPrefix = "uds"
		}
	}
	
	return NewStateManager(config)
}

// Helper functions for parsing environment variables

func parseDuration(s string, defaultValue time.Duration) time.Duration {
	if s == "" {
		return defaultValue
	}
	
	d, err := time.ParseDuration(s)
	if err != nil {
		return defaultValue
	}
	
	return d
}

func parseInt(s string, defaultValue int) int {
	if s == "" {
		return defaultValue
	}
	
	var i int
	_, err := fmt.Sscanf(s, "%d", &i)
	if err != nil {
		return defaultValue
	}
	
	return i
}

func parseInt64(s string, defaultValue int64) int64 {
	if s == "" {
		return defaultValue
	}
	
	var i int64
	_, err := fmt.Sscanf(s, "%d", &i)
	if err != nil {
		return defaultValue
	}
	
	return i
}

// MCPSessionManager provides MCP-specific session management helpers
type MCPSessionManager struct {
	manager StateManager
}

// NewMCPSessionManager creates a new MCP session manager
func NewMCPSessionManager(manager StateManager) *MCPSessionManager {
	return &MCPSessionManager{
		manager: manager,
	}
}

// StartDiscoverySession starts a new discovery session for an MCP request
func (msm *MCPSessionManager) StartDiscoverySession(ctx context.Context, goal string) (*Session, error) {
	session, err := msm.manager.CreateSession(ctx, goal)
	if err != nil {
		return nil, fmt.Errorf("create session: %w", err)
	}
	
	// Set initial context
	msm.manager.SetContext(ctx, session.ID, "mcp_active", true)
	msm.manager.SetContext(ctx, session.ID, "start_time", time.Now())
	
	return session, nil
}

// RecordDiscovery records a schema discovery in the session
func (msm *MCPSessionManager) RecordDiscovery(ctx context.Context, sessionID string, schema string, result interface{}) error {
	// Get current session
	session, err := msm.manager.GetSession(ctx, sessionID)
	if err != nil {
		return err
	}
	
	// Add to discovered schemas if not already present
	found := false
	for _, s := range session.DiscoveredSchemas {
		if s == schema {
			found = true
			break
		}
	}
	
	if !found {
		session.DiscoveredSchemas = append(session.DiscoveredSchemas, schema)
		session.CurrentSchema = schema
		
		if err := msm.manager.UpdateSession(ctx, session); err != nil {
			return fmt.Errorf("update session: %w", err)
		}
	}
	
	// Cache the discovery result
	if m, ok := msm.manager.(*Manager); ok {
		return m.CacheDiscoveryResult(ctx, sessionID, "schema", schema, result)
	} else if _, ok := msm.manager.(*RedisManager); ok {
		cacheKey := fmt.Sprintf("discovery:%s:schema:%s", sessionID, schema)
		return msm.manager.Set(ctx, cacheKey, result, 5*time.Minute)
	}
	
	return nil
}

// GetDiscoveryContext retrieves the full discovery context for a session
func (msm *MCPSessionManager) GetDiscoveryContext(ctx context.Context, sessionID string) (*DiscoveryContext, error) {
	session, cachedResults, err := msm.manager.GetSessionWithCache(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	
	// Build discovery context
	context := &DiscoveryContext{
		SessionID:         session.ID,
		Goal:              session.UserGoal,
		DiscoveredSchemas: session.DiscoveredSchemas,
		CurrentSchema:     session.CurrentSchema,
		CachedResults:     cachedResults,
		StartTime:         session.CreatedAt,
		LastActivity:      session.LastAccess,
	}
	
	return context, nil
}

// DiscoveryContext represents the full context of a discovery session
type DiscoveryContext struct {
	SessionID         string
	Goal              string
	DiscoveredSchemas []string
	CurrentSchema     string
	CachedResults     map[string]interface{}
	StartTime         time.Time
	LastActivity      time.Time
}

// EndDiscoverySession ends a discovery session
func (msm *MCPSessionManager) EndDiscoverySession(ctx context.Context, sessionID string) error {
	// Set session as inactive
	msm.manager.SetContext(ctx, sessionID, "mcp_active", false)
	msm.manager.SetContext(ctx, sessionID, "end_time", time.Now())
	
	// Could optionally delete the session here, but keeping it for history
	// return msm.manager.DeleteSession(ctx, sessionID)
	
	return nil
}