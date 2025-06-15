package state

import (
	"context"
	"encoding/json"
	"fmt"
	"time"
)

// StoreType defines the type of store backend
type StoreType string

const (
	StoreTypeMemory StoreType = "memory"
	StoreTypeRedis  StoreType = "redis"
)

// FactoryConfig holds configuration for creating state managers
type FactoryConfig struct {
	StoreType       StoreType
	ManagerConfig   ManagerConfig
	RedisConfig     *RedisConfig // Optional, only needed for Redis
}

// NewStateManager creates a state manager based on configuration
func NewStateManager(config FactoryConfig) (StateManager, error) {
	switch config.StoreType {
	case StoreTypeMemory:
		return NewManager(config.ManagerConfig), nil
		
	case StoreTypeRedis:
		if config.RedisConfig == nil {
			return nil, fmt.Errorf("redis config required for redis store type")
		}
		
		return NewRedisManager(*config.RedisConfig, config.ManagerConfig)
		
	default:
		return nil, fmt.Errorf("unknown store type: %s", config.StoreType)
	}
}

// RedisManager implements StateManager using Redis for both session and cache storage
type RedisManager struct {
	store *RedisStore
	cache *RedisCache
	
	config ManagerConfig
}

// NewRedisManager creates a new Redis-based state manager
func NewRedisManager(redisConfig RedisConfig, managerConfig ManagerConfig) (*RedisManager, error) {
	// Create Redis store
	store, err := NewRedisStore(redisConfig)
	if err != nil {
		return nil, fmt.Errorf("create redis store: %w", err)
	}
	
	// Create Redis cache using the same client
	cache := NewRedisCache(store.client, redisConfig.KeyPrefix, managerConfig.CacheTTL)
	
	return &RedisManager{
		store:  store,
		cache:  cache,
		config: managerConfig,
	}, nil
}

// Session operations - delegate to store

func (rm *RedisManager) CreateSession(ctx context.Context, goal string) (*Session, error) {
	return rm.store.CreateSession(ctx, goal)
}

func (rm *RedisManager) GetSession(ctx context.Context, sessionID string) (*Session, error) {
	return rm.store.GetSession(ctx, sessionID)
}

func (rm *RedisManager) UpdateSession(ctx context.Context, session *Session) error {
	return rm.store.UpdateSession(ctx, session)
}

func (rm *RedisManager) DeleteSession(ctx context.Context, sessionID string) error {
	return rm.store.DeleteSession(ctx, sessionID)
}

func (rm *RedisManager) GetContext(ctx context.Context, sessionID string, key string) (interface{}, error) {
	return rm.store.GetContext(ctx, sessionID, key)
}

func (rm *RedisManager) SetContext(ctx context.Context, sessionID string, key string, value interface{}) error {
	return rm.store.SetContext(ctx, sessionID, key, value)
}

func (rm *RedisManager) CleanupExpired(ctx context.Context) error {
	return rm.store.CleanupExpired(ctx)
}

// Cache operations - delegate to cache

func (rm *RedisManager) Get(ctx context.Context, key string) (interface{}, bool) {
	return rm.cache.Get(ctx, key)
}

func (rm *RedisManager) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	return rm.cache.Set(ctx, key, value, ttl)
}

func (rm *RedisManager) Delete(ctx context.Context, key string) error {
	return rm.cache.Delete(ctx, key)
}

func (rm *RedisManager) Clear(ctx context.Context) error {
	return rm.cache.Clear(ctx)
}

func (rm *RedisManager) Stats(ctx context.Context) (CacheStats, error) {
	return rm.cache.Stats(ctx)
}

// Advanced operations

func (rm *RedisManager) GetSessionWithCache(ctx context.Context, sessionID string) (*Session, map[string]interface{}, error) {
	// Get session
	session, err := rm.store.GetSession(ctx, sessionID)
	if err != nil {
		return nil, nil, err
	}
	
	// Retrieve cached discovery results
	cachedResults := make(map[string]interface{})
	
	for _, schema := range session.DiscoveredSchemas {
		cacheKey := rm.discoveryCacheKey(sessionID, "schema", schema)
		if value, found := rm.cache.Get(ctx, cacheKey); found {
			cachedResults[schema] = value
		}
	}
	
	return session, cachedResults, nil
}

func (rm *RedisManager) WarmCache(ctx context.Context, sessionID string) error {
	session, err := rm.store.GetSession(ctx, sessionID)
	if err != nil {
		return fmt.Errorf("get session: %w", err)
	}
	
	// Pre-load data based on user goal
	if session.UserGoal == "explore transaction performance" {
		commonSchemas := []string{"Transaction", "TransactionError", "TransactionTrace"}
		for _, schema := range commonSchemas {
			cacheKey := rm.discoveryCacheKey(sessionID, "schema", schema)
			rm.cache.Set(ctx, cacheKey, fmt.Sprintf("pre-loaded schema: %s", schema), rm.config.CacheTTL)
		}
	}
	
	return nil
}

func (rm *RedisManager) Close() error {
	if err := rm.cache.Close(); err != nil {
		return err
	}
	return rm.store.Close()
}

// Helper methods

func (rm *RedisManager) discoveryCacheKey(sessionID string, resultType string, key string) string {
	return fmt.Sprintf("discovery:%s:%s:%s", sessionID, resultType, key)
}

// Additional Redis-specific features

// PublishSessionEvent publishes a session event for real-time notifications
func (rm *RedisManager) PublishSessionEvent(ctx context.Context, sessionID string, event string, data interface{}) error {
	channel := fmt.Sprintf("%s:session:%s:events", rm.store.keyPrefix, sessionID)
	
	eventData := map[string]interface{}{
		"event":      event,
		"data":       data,
		"timestamp": time.Now().Unix(),
	}
	
	payload, err := json.Marshal(eventData)
	if err != nil {
		return fmt.Errorf("marshal event data: %w", err)
	}
	
	return rm.store.client.Publish(ctx, channel, payload).Err()
}

// SubscribeSessionEvents subscribes to session events
func (rm *RedisManager) SubscribeSessionEvents(ctx context.Context, sessionID string) (<-chan string, error) {
	channel := fmt.Sprintf("%s:session:%s:events", rm.store.keyPrefix, sessionID)
	
	pubsub := rm.store.client.Subscribe(ctx, channel)
	
	// Create channel for events
	events := make(chan string, 100)
	
	// Start goroutine to read events
	go func() {
		defer close(events)
		defer pubsub.Close()
		
		for {
			select {
			case <-ctx.Done():
				return
			case msg := <-pubsub.Channel():
				events <- msg.Payload
			}
		}
	}()
	
	return events, nil
}