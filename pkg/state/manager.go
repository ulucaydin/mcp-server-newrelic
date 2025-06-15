package state

import (
	"context"
	"fmt"
	"time"
)

// Manager implements the StateManager interface, coordinating session and cache
type Manager struct {
	store Store
	cache ResultCache
	
	// Configuration
	config ManagerConfig
}

// ManagerConfig holds configuration for the state manager
type ManagerConfig struct {
	SessionTTL      time.Duration
	CacheTTL        time.Duration
	MaxSessions     int
	MaxCacheEntries int
	MaxCacheMemory  int64
}

// DefaultManagerConfig returns default configuration
func DefaultManagerConfig() ManagerConfig {
	return ManagerConfig{
		SessionTTL:      1 * time.Hour,
		CacheTTL:        5 * time.Minute,
		MaxSessions:     10000,
		MaxCacheEntries: 100000,
		MaxCacheMemory:  1 << 30, // 1GB
	}
}

// NewManager creates a new state manager with in-memory storage
func NewManager(config ManagerConfig) *Manager {
	store := NewMemoryStore(config.SessionTTL)
	cache := NewMemoryCache(config.MaxCacheEntries, config.MaxCacheMemory, config.CacheTTL)
	
	return &Manager{
		store:  store,
		cache:  cache,
		config: config,
	}
}

// CreateSession creates a new session with the given goal
func (m *Manager) CreateSession(ctx context.Context, goal string) (*Session, error) {
	session, err := m.store.CreateSession(ctx, goal)
	if err != nil {
		return nil, fmt.Errorf("create session: %w", err)
	}
	
	// Initialize session-specific cache namespace
	cacheKey := m.sessionCacheKey(session.ID, "initialized")
	m.cache.Set(ctx, cacheKey, true, m.config.SessionTTL)
	
	return session, nil
}

// GetSession retrieves a session by ID
func (m *Manager) GetSession(ctx context.Context, sessionID string) (*Session, error) {
	return m.store.GetSession(ctx, sessionID)
}

// UpdateSession updates an existing session
func (m *Manager) UpdateSession(ctx context.Context, session *Session) error {
	return m.store.UpdateSession(ctx, session)
}

// DeleteSession removes a session and its associated cache entries
func (m *Manager) DeleteSession(ctx context.Context, sessionID string) error {
	// Delete session
	if err := m.store.DeleteSession(ctx, sessionID); err != nil {
		return err
	}
	
	// Clear session-specific cache entries
	// Note: This is a simplified implementation. In production, you might want
	// to track session-specific keys more efficiently
	
	return nil
}

// GetContext retrieves a specific context value from a session
func (m *Manager) GetContext(ctx context.Context, sessionID string, key string) (interface{}, error) {
	return m.store.GetContext(ctx, sessionID, key)
}

// SetContext sets a specific context value in a session
func (m *Manager) SetContext(ctx context.Context, sessionID string, key string, value interface{}) error {
	return m.store.SetContext(ctx, sessionID, key, value)
}

// CleanupExpired removes expired sessions and cache entries
func (m *Manager) CleanupExpired(ctx context.Context) error {
	if err := m.store.CleanupExpired(ctx); err != nil {
		return fmt.Errorf("cleanup sessions: %w", err)
	}
	
	// Cache cleanup is handled automatically by the cache implementation
	
	return nil
}

// Close closes the state manager
func (m *Manager) Close() error {
	if err := m.store.Close(); err != nil {
		return fmt.Errorf("close store: %w", err)
	}
	
	if cacheCloser, ok := m.cache.(*MemoryCache); ok {
		if err := cacheCloser.Close(); err != nil {
			return fmt.Errorf("close cache: %w", err)
		}
	}
	
	return nil
}

// Get retrieves a value from the cache
func (m *Manager) Get(ctx context.Context, key string) (interface{}, bool) {
	return m.cache.Get(ctx, key)
}

// Set stores a value in the cache
func (m *Manager) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	return m.cache.Set(ctx, key, value, ttl)
}

// Delete removes a value from the cache
func (m *Manager) Delete(ctx context.Context, key string) error {
	return m.cache.Delete(ctx, key)
}

// Clear removes all entries from the cache
func (m *Manager) Clear(ctx context.Context) error {
	return m.cache.Clear(ctx)
}

// Stats returns cache statistics
func (m *Manager) Stats(ctx context.Context) (CacheStats, error) {
	return m.cache.Stats(ctx)
}

// GetSessionWithCache retrieves a session along with its cached discovery results
func (m *Manager) GetSessionWithCache(ctx context.Context, sessionID string) (*Session, map[string]interface{}, error) {
	// Get session
	session, err := m.store.GetSession(ctx, sessionID)
	if err != nil {
		return nil, nil, err
	}
	
	// Retrieve cached discovery results for this session
	cachedResults := make(map[string]interface{})
	
	// Get discovered schemas from cache
	for _, schema := range session.DiscoveredSchemas {
		cacheKey := m.discoveryCacheKey(sessionID, "schema", schema)
		if value, found := m.cache.Get(ctx, cacheKey); found {
			cachedResults[schema] = value
		}
	}
	
	return session, cachedResults, nil
}

// WarmCache pre-loads commonly accessed data for a session
func (m *Manager) WarmCache(ctx context.Context, sessionID string) error {
	session, err := m.store.GetSession(ctx, sessionID)
	if err != nil {
		return fmt.Errorf("get session: %w", err)
	}
	
	// Pre-load data based on user goal and preferences
	// This is where intelligent caching strategies can be implemented
	
	// Example: If user is exploring transaction data, pre-load common transaction schemas
	if session.UserGoal == "explore transaction performance" {
		commonSchemas := []string{"Transaction", "TransactionError", "TransactionTrace"}
		for _, schema := range commonSchemas {
			cacheKey := m.discoveryCacheKey(sessionID, "schema", schema)
			// In a real implementation, this would fetch actual schema data
			m.cache.Set(ctx, cacheKey, fmt.Sprintf("pre-loaded schema: %s", schema), m.config.CacheTTL)
		}
	}
	
	return nil
}

// CacheDiscoveryResult caches a discovery result for a session
func (m *Manager) CacheDiscoveryResult(ctx context.Context, sessionID string, resultType string, key string, value interface{}) error {
	cacheKey := m.discoveryCacheKey(sessionID, resultType, key)
	return m.cache.Set(ctx, cacheKey, value, m.config.CacheTTL)
}

// GetDiscoveryResult retrieves a cached discovery result
func (m *Manager) GetDiscoveryResult(ctx context.Context, sessionID string, resultType string, key string) (interface{}, bool) {
	cacheKey := m.discoveryCacheKey(sessionID, resultType, key)
	return m.cache.Get(ctx, cacheKey)
}

// Helper methods

// sessionCacheKey generates a cache key for session-specific data
func (m *Manager) sessionCacheKey(sessionID string, key string) string {
	return fmt.Sprintf("session:%s:%s", sessionID, key)
}

// discoveryCacheKey generates a cache key for discovery results
func (m *Manager) discoveryCacheKey(sessionID string, resultType string, key string) string {
	return fmt.Sprintf("discovery:%s:%s:%s", sessionID, resultType, key)
}