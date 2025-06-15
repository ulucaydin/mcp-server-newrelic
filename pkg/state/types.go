package state

import (
	"context"
	"time"
)

// Session represents an active user session
type Session struct {
	ID          string                 `json:"id"`
	UserGoal    string                 `json:"user_goal"`
	Context     map[string]interface{} `json:"context"`
	CreatedAt   time.Time             `json:"created_at"`
	LastAccess  time.Time             `json:"last_access"`
	TTL         time.Duration         `json:"ttl"`
	
	// Discovery-specific context
	DiscoveredSchemas []string               `json:"discovered_schemas"`
	CurrentSchema     string                 `json:"current_schema,omitempty"`
	Preferences       map[string]interface{} `json:"preferences"`
}

// Store defines the interface for session storage
type Store interface {
	// Session operations
	CreateSession(ctx context.Context, goal string) (*Session, error)
	GetSession(ctx context.Context, sessionID string) (*Session, error)
	UpdateSession(ctx context.Context, session *Session) error
	DeleteSession(ctx context.Context, sessionID string) error
	
	// Context operations
	GetContext(ctx context.Context, sessionID string, key string) (interface{}, error)
	SetContext(ctx context.Context, sessionID string, key string, value interface{}) error
	
	// Maintenance
	CleanupExpired(ctx context.Context) error
	Close() error
}

// CacheEntry represents a cached discovery result
type CacheEntry struct {
	Key        string
	Value      interface{}
	CreatedAt  time.Time
	TTL        time.Duration
	AccessCount int64
}

// ResultCache defines the interface for caching discovery results
type ResultCache interface {
	Get(ctx context.Context, key string) (interface{}, bool)
	Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error
	Delete(ctx context.Context, key string) error
	Clear(ctx context.Context) error
	Stats(ctx context.Context) (CacheStats, error)
}

// CacheStats provides cache performance metrics
type CacheStats struct {
	TotalEntries int64
	MemoryUsage  int64
	HitCount     int64
	MissCount    int64
	EvictCount   int64
}

// StateManager coordinates session and cache management
type StateManager interface {
	Store
	ResultCache
	
	// Advanced operations
	GetSessionWithCache(ctx context.Context, sessionID string) (*Session, map[string]interface{}, error)
	WarmCache(ctx context.Context, sessionID string) error
}