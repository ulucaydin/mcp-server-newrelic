package state

import (
	"context"
	"fmt"
	"sync"
	"time"
	
	"github.com/google/uuid"
)

// MemoryStore implements an in-memory session store
type MemoryStore struct {
	sessions map[string]*Session
	mu       sync.RWMutex
	
	// Configuration
	defaultTTL time.Duration
	maxSessions int
	
	// Cleanup
	cleanupInterval time.Duration
	stopCleanup     chan struct{}
}

// NewMemoryStore creates a new in-memory session store
func NewMemoryStore(defaultTTL time.Duration) *MemoryStore {
	ms := &MemoryStore{
		sessions:        make(map[string]*Session),
		defaultTTL:      defaultTTL,
		maxSessions:     10000, // Default max sessions
		cleanupInterval: 5 * time.Minute,
		stopCleanup:     make(chan struct{}),
	}
	
	// Start cleanup goroutine
	go ms.cleanupLoop()
	
	return ms
}

// CreateSession creates a new session with the given goal
func (ms *MemoryStore) CreateSession(ctx context.Context, goal string) (*Session, error) {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	// Check session limit
	if len(ms.sessions) >= ms.maxSessions {
		// Try to cleanup expired sessions first
		ms.cleanupExpiredLocked()
		
		if len(ms.sessions) >= ms.maxSessions {
			return nil, fmt.Errorf("session limit reached: %d", ms.maxSessions)
		}
	}
	
	session := &Session{
		ID:                uuid.New().String(),
		UserGoal:          goal,
		Context:           make(map[string]interface{}),
		CreatedAt:         time.Now(),
		LastAccess:        time.Now(),
		TTL:               ms.defaultTTL,
		DiscoveredSchemas: []string{},
		Preferences:       make(map[string]interface{}),
	}
	
	ms.sessions[session.ID] = session
	
	return session, nil
}

// GetSession retrieves a session by ID
func (ms *MemoryStore) GetSession(ctx context.Context, sessionID string) (*Session, error) {
	ms.mu.RLock()
	defer ms.mu.RUnlock()
	
	session, exists := ms.sessions[sessionID]
	if !exists {
		return nil, fmt.Errorf("session not found: %s", sessionID)
	}
	
	// Check if session has expired
	if ms.isExpired(session) {
		return nil, fmt.Errorf("session expired: %s", sessionID)
	}
	
	// Update last access time
	session.LastAccess = time.Now()
	
	// Return a copy to prevent external modifications
	sessionCopy := *session
	return &sessionCopy, nil
}

// UpdateSession updates an existing session
func (ms *MemoryStore) UpdateSession(ctx context.Context, session *Session) error {
	if session == nil {
		return fmt.Errorf("session cannot be nil")
	}
	
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	existing, exists := ms.sessions[session.ID]
	if !exists {
		return fmt.Errorf("session not found: %s", session.ID)
	}
	
	// Preserve creation time and update last access
	session.CreatedAt = existing.CreatedAt
	session.LastAccess = time.Now()
	
	ms.sessions[session.ID] = session
	
	return nil
}

// DeleteSession removes a session
func (ms *MemoryStore) DeleteSession(ctx context.Context, sessionID string) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	if _, exists := ms.sessions[sessionID]; !exists {
		return fmt.Errorf("session not found: %s", sessionID)
	}
	
	delete(ms.sessions, sessionID)
	return nil
}

// GetContext retrieves a specific context value from a session
func (ms *MemoryStore) GetContext(ctx context.Context, sessionID string, key string) (interface{}, error) {
	session, err := ms.GetSession(ctx, sessionID)
	if err != nil {
		return nil, err
	}
	
	value, exists := session.Context[key]
	if !exists {
		return nil, fmt.Errorf("context key not found: %s", key)
	}
	
	return value, nil
}

// SetContext sets a specific context value in a session
func (ms *MemoryStore) SetContext(ctx context.Context, sessionID string, key string, value interface{}) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	session, exists := ms.sessions[sessionID]
	if !exists {
		return fmt.Errorf("session not found: %s", sessionID)
	}
	
	if ms.isExpired(session) {
		return fmt.Errorf("session expired: %s", sessionID)
	}
	
	session.Context[key] = value
	session.LastAccess = time.Now()
	
	return nil
}

// CleanupExpired removes all expired sessions
func (ms *MemoryStore) CleanupExpired(ctx context.Context) error {
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	ms.cleanupExpiredLocked()
	return nil
}

// cleanupExpiredLocked removes expired sessions (must be called with lock held)
func (ms *MemoryStore) cleanupExpiredLocked() {
	now := time.Now()
	for id, session := range ms.sessions {
		if now.Sub(session.LastAccess) > session.TTL {
			delete(ms.sessions, id)
		}
	}
}

// isExpired checks if a session has expired
func (ms *MemoryStore) isExpired(session *Session) bool {
	return time.Since(session.LastAccess) > session.TTL
}

// cleanupLoop runs periodic cleanup of expired sessions
func (ms *MemoryStore) cleanupLoop() {
	ticker := time.NewTicker(ms.cleanupInterval)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			ms.CleanupExpired(context.Background())
		case <-ms.stopCleanup:
			return
		}
	}
}

// Close stops the cleanup loop and clears all sessions
func (ms *MemoryStore) Close() error {
	close(ms.stopCleanup)
	
	ms.mu.Lock()
	defer ms.mu.Unlock()
	
	ms.sessions = make(map[string]*Session)
	return nil
}

// Stats returns current store statistics
func (ms *MemoryStore) Stats() StoreStats {
	ms.mu.RLock()
	defer ms.mu.RUnlock()
	
	var expiredCount int
	now := time.Now()
	
	for _, session := range ms.sessions {
		if now.Sub(session.LastAccess) > session.TTL {
			expiredCount++
		}
	}
	
	return StoreStats{
		TotalSessions:  len(ms.sessions),
		ActiveSessions: len(ms.sessions) - expiredCount,
		ExpiredSessions: expiredCount,
	}
}

// StoreStats provides session store statistics
type StoreStats struct {
	TotalSessions   int
	ActiveSessions  int
	ExpiredSessions int
}