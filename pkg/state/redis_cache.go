package state

import (
	"context"
	"encoding/json"
	"fmt"
	"sync/atomic"
	"time"
	
	"github.com/go-redis/redis/v8"
)

// RedisCache implements a Redis-based result cache
type RedisCache struct {
	client *redis.Client
	
	// Configuration
	keyPrefix  string
	defaultTTL time.Duration
	
	// Local metrics (could be stored in Redis for distributed metrics)
	hits   int64
	misses int64
}

// NewRedisCache creates a new Redis-based cache
func NewRedisCache(client *redis.Client, keyPrefix string, defaultTTL time.Duration) *RedisCache {
	return &RedisCache{
		client:     client,
		keyPrefix:  keyPrefix,
		defaultTTL: defaultTTL,
	}
}

// Get retrieves a value from the cache
func (rc *RedisCache) Get(ctx context.Context, key string) (interface{}, bool) {
	fullKey := rc.cacheKey(key)
	
	// Get from Redis
	data, err := rc.client.Get(ctx, fullKey).Bytes()
	if err != nil {
		if err == redis.Nil {
			atomic.AddInt64(&rc.misses, 1)
			return nil, false
		}
		// Log error but return miss
		atomic.AddInt64(&rc.misses, 1)
		return nil, false
	}
	
	// Deserialize
	var entry CacheEntry
	if err := json.Unmarshal(data, &entry); err != nil {
		atomic.AddInt64(&rc.misses, 1)
		return nil, false
	}
	
	// Update access count (async to avoid blocking)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 1*time.Second)
		defer cancel()
		rc.incrementAccessCount(ctx, fullKey)
	}()
	
	atomic.AddInt64(&rc.hits, 1)
	return entry.Value, true
}

// Set stores a value in the cache with TTL
func (rc *RedisCache) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	if ttl <= 0 {
		ttl = rc.defaultTTL
	}
	
	entry := CacheEntry{
		Key:         key,
		Value:       value,
		CreatedAt:   time.Now(),
		TTL:         ttl,
		AccessCount: 0,
	}
	
	// Serialize
	data, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("marshal cache entry: %w", err)
	}
	
	// Store in Redis
	fullKey := rc.cacheKey(key)
	err = rc.client.Set(ctx, fullKey, data, ttl).Err()
	if err != nil {
		return fmt.Errorf("set cache entry: %w", err)
	}
	
	// Add to cache index for stats
	rc.client.SAdd(ctx, rc.cacheIndexKey(), key)
	
	return nil
}

// Delete removes an entry from the cache
func (rc *RedisCache) Delete(ctx context.Context, key string) error {
	fullKey := rc.cacheKey(key)
	
	// Delete from Redis
	err := rc.client.Del(ctx, fullKey).Err()
	if err != nil {
		return fmt.Errorf("delete cache entry: %w", err)
	}
	
	// Remove from index
	rc.client.SRem(ctx, rc.cacheIndexKey(), key)
	
	return nil
}

// Clear removes all entries from the cache
func (rc *RedisCache) Clear(ctx context.Context) error {
	// Get all cache keys from index
	keys, err := rc.client.SMembers(ctx, rc.cacheIndexKey()).Result()
	if err != nil {
		return fmt.Errorf("get cache index: %w", err)
	}
	
	if len(keys) == 0 {
		return nil
	}
	
	// Build full key list
	fullKeys := make([]string, len(keys))
	for i, key := range keys {
		fullKeys[i] = rc.cacheKey(key)
	}
	
	// Delete all keys
	pipe := rc.client.Pipeline()
	pipe.Del(ctx, fullKeys...)
	pipe.Del(ctx, rc.cacheIndexKey())
	
	_, err = pipe.Exec(ctx)
	if err != nil {
		return fmt.Errorf("clear cache: %w", err)
	}
	
	return nil
}

// Stats returns cache statistics
func (rc *RedisCache) Stats(ctx context.Context) (CacheStats, error) {
	// Get total entries from index
	totalEntries, err := rc.client.SCard(ctx, rc.cacheIndexKey()).Result()
	if err != nil {
		return CacheStats{}, fmt.Errorf("get cache size: %w", err)
	}
	
	// Get global stats from Redis (if stored)
	globalStats, _ := rc.getGlobalStats(ctx)
	
	return CacheStats{
		TotalEntries: totalEntries,
		MemoryUsage:  0, // Not easily available in Redis
		HitCount:     atomic.LoadInt64(&rc.hits) + globalStats.HitCount,
		MissCount:    atomic.LoadInt64(&rc.misses) + globalStats.MissCount,
		EvictCount:   globalStats.EvictCount,
	}, nil
}

// incrementAccessCount increments the access count for a cache entry
func (rc *RedisCache) incrementAccessCount(ctx context.Context, fullKey string) {
	// Get current entry
	data, err := rc.client.Get(ctx, fullKey).Bytes()
	if err != nil {
		return
	}
	
	var entry CacheEntry
	if err := json.Unmarshal(data, &entry); err != nil {
		return
	}
	
	// Increment access count
	entry.AccessCount++
	
	// Save back
	if data, err := json.Marshal(entry); err == nil {
		// Calculate remaining TTL
		ttl := rc.client.TTL(ctx, fullKey).Val()
		if ttl > 0 {
			rc.client.Set(ctx, fullKey, data, ttl)
		}
	}
}

// getGlobalStats retrieves global cache statistics from Redis
func (rc *RedisCache) getGlobalStats(ctx context.Context) (CacheStats, error) {
	statsKey := fmt.Sprintf("%s:stats", rc.keyPrefix)
	
	// Get stats from Redis
	data, err := rc.client.Get(ctx, statsKey).Bytes()
	if err != nil {
		return CacheStats{}, nil // Return empty stats on error
	}
	
	var stats CacheStats
	json.Unmarshal(data, &stats)
	return stats, nil
}

// updateGlobalStats updates global cache statistics in Redis
func (rc *RedisCache) updateGlobalStats(ctx context.Context) {
	stats := CacheStats{
		HitCount:  atomic.LoadInt64(&rc.hits),
		MissCount: atomic.LoadInt64(&rc.misses),
	}
	
	if data, err := json.Marshal(stats); err == nil {
		statsKey := fmt.Sprintf("%s:stats", rc.keyPrefix)
		rc.client.Set(ctx, statsKey, data, 24*time.Hour)
	}
}

// Helper methods

func (rc *RedisCache) cacheKey(key string) string {
	return fmt.Sprintf("%s:cache:%s", rc.keyPrefix, key)
}

func (rc *RedisCache) cacheIndexKey() string {
	return fmt.Sprintf("%s:cache:index", rc.keyPrefix)
}

// Close updates global stats before closing
func (rc *RedisCache) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	
	rc.updateGlobalStats(ctx)
	return nil
}

// HitRate returns the cache hit rate
func (rc *RedisCache) HitRate() float64 {
	hits := atomic.LoadInt64(&rc.hits)
	misses := atomic.LoadInt64(&rc.misses)
	total := hits + misses
	
	if total == 0 {
		return 0
	}
	
	return float64(hits) / float64(total)
}