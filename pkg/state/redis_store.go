package state

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
	
	"github.com/go-redis/redis/v8"
	"github.com/google/uuid"
)

// RedisStore implements a Redis-based session store
type RedisStore struct {
	client *redis.Client
	
	// Configuration
	defaultTTL time.Duration
	keyPrefix  string
}

// RedisConfig holds Redis connection configuration
type RedisConfig struct {
	URL        string
	MaxRetries int
	PoolSize   int
	KeyPrefix  string
	DefaultTTL time.Duration
}

// NewRedisStore creates a new Redis-based session store
func NewRedisStore(config RedisConfig) (*RedisStore, error) {
	// Parse Redis URL
	opt, err := redis.ParseURL(config.URL)
	if err != nil {
		return nil, fmt.Errorf("parse redis URL: %w", err)
	}
	
	// Apply additional configuration
	opt.MaxRetries = config.MaxRetries
	opt.PoolSize = config.PoolSize
	
	// Create client
	client := redis.NewClient(opt)
	
	// Test connection
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	if err := client.Ping(ctx).Err(); err != nil {
		return nil, fmt.Errorf("connect to Redis: %w", err)
	}
	
	return &RedisStore{
		client:     client,
		defaultTTL: config.DefaultTTL,
		keyPrefix:  config.KeyPrefix,
	}, nil
}

// CreateSession creates a new session with the given goal
func (rs *RedisStore) CreateSession(ctx context.Context, goal string) (*Session, error) {
	session := &Session{
		ID:                uuid.New().String(),
		UserGoal:          goal,
		Context:           make(map[string]interface{}),
		CreatedAt:         time.Now(),
		LastAccess:        time.Now(),
		TTL:               rs.defaultTTL,
		DiscoveredSchemas: []string{},
		Preferences:       make(map[string]interface{}),
	}
	
	// Serialize session
	data, err := json.Marshal(session)
	if err != nil {
		return nil, fmt.Errorf("marshal session: %w", err)
	}
	
	// Store in Redis
	key := rs.sessionKey(session.ID)
	err = rs.client.Set(ctx, key, data, session.TTL).Err()
	if err != nil {
		return nil, fmt.Errorf("store session: %w", err)
	}
	
	// Add to active sessions set
	err = rs.client.SAdd(ctx, rs.activeSessionsKey(), session.ID).Err()
	if err != nil {
		// Log error but don't fail - this is for tracking only
	}
	
	return session, nil
}

// GetSession retrieves a session by ID
func (rs *RedisStore) GetSession(ctx context.Context, sessionID string) (*Session, error) {
	key := rs.sessionKey(sessionID)
	
	// Get from Redis
	data, err := rs.client.Get(ctx, key).Bytes()
	if err != nil {
		if err == redis.Nil {
			return nil, fmt.Errorf("session not found: %s", sessionID)
		}
		return nil, fmt.Errorf("get session: %w", err)
	}
	
	// Deserialize
	var session Session
	if err := json.Unmarshal(data, &session); err != nil {
		return nil, fmt.Errorf("unmarshal session: %w", err)
	}
	
	// Update last access time
	session.LastAccess = time.Now()
	
	// Update in Redis (async to avoid blocking)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		
		if data, err := json.Marshal(session); err == nil {
			rs.client.Set(ctx, key, data, session.TTL)
		}
	}()
	
	return &session, nil
}

// UpdateSession updates an existing session
func (rs *RedisStore) UpdateSession(ctx context.Context, session *Session) error {
	if session == nil {
		return fmt.Errorf("session cannot be nil")
	}
	
	// Update last access time
	session.LastAccess = time.Now()
	
	// Serialize
	data, err := json.Marshal(session)
	if err != nil {
		return fmt.Errorf("marshal session: %w", err)
	}
	
	// Store in Redis
	key := rs.sessionKey(session.ID)
	err = rs.client.Set(ctx, key, data, session.TTL).Err()
	if err != nil {
		return fmt.Errorf("update session: %w", err)
	}
	
	return nil
}

// DeleteSession removes a session
func (rs *RedisStore) DeleteSession(ctx context.Context, sessionID string) error {
	key := rs.sessionKey(sessionID)
	
	// Delete from Redis
	deleted, err := rs.client.Del(ctx, key).Result()
	if err != nil {
		return fmt.Errorf("delete session: %w", err)
	}
	
	if deleted == 0 {
		return fmt.Errorf("session not found: %s", sessionID)
	}
	
	// Remove from active sessions set
	rs.client.SRem(ctx, rs.activeSessionsKey(), sessionID)
	
	return nil
}

// GetContext retrieves a specific context value from a session
func (rs *RedisStore) GetContext(ctx context.Context, sessionID string, key string) (interface{}, error) {
	session, err := rs.GetSession(ctx, sessionID)
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
func (rs *RedisStore) SetContext(ctx context.Context, sessionID string, key string, value interface{}) error {
	// Get current session
	session, err := rs.GetSession(ctx, sessionID)
	if err != nil {
		return err
	}
	
	// Update context
	session.Context[key] = value
	
	// Save back to Redis
	return rs.UpdateSession(ctx, session)
}

// CleanupExpired removes all expired sessions
func (rs *RedisStore) CleanupExpired(ctx context.Context) error {
	// Redis handles expiration automatically based on TTL
	// This method can be used to clean up the active sessions set
	
	members, err := rs.client.SMembers(ctx, rs.activeSessionsKey()).Result()
	if err != nil {
		return fmt.Errorf("get active sessions: %w", err)
	}
	
	// Check each session and remove from set if expired
	for _, sessionID := range members {
		key := rs.sessionKey(sessionID)
		exists, err := rs.client.Exists(ctx, key).Result()
		if err != nil {
			continue
		}
		
		if exists == 0 {
			// Session expired, remove from active set
			rs.client.SRem(ctx, rs.activeSessionsKey(), sessionID)
		}
	}
	
	return nil
}

// Close closes the Redis connection
func (rs *RedisStore) Close() error {
	return rs.client.Close()
}

// Helper methods

func (rs *RedisStore) sessionKey(sessionID string) string {
	return fmt.Sprintf("%s:session:%s", rs.keyPrefix, sessionID)
}

func (rs *RedisStore) activeSessionsKey() string {
	return fmt.Sprintf("%s:sessions:active", rs.keyPrefix)
}

// Stats returns current store statistics
func (rs *RedisStore) Stats(ctx context.Context) (StoreStats, error) {
	// Get active session count
	activeCount, err := rs.client.SCard(ctx, rs.activeSessionsKey()).Result()
	if err != nil {
		return StoreStats{}, fmt.Errorf("get active sessions count: %w", err)
	}
	
	return StoreStats{
		TotalSessions:   int(activeCount),
		ActiveSessions:  int(activeCount),
		ExpiredSessions: 0, // Redis handles expiration automatically
	}, nil
}