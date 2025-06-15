package state

import (
	"context"
	"sync"
	"sync/atomic"
	"time"
)

// MemoryCache implements an in-memory result cache with TTL
type MemoryCache struct {
	entries map[string]*CacheEntry
	mu      sync.RWMutex
	
	// Configuration
	maxEntries      int
	maxMemory       int64
	defaultTTL      time.Duration
	
	// Metrics
	hits            int64
	misses          int64
	evictions       int64
	currentMemory   int64
	
	// Cleanup
	cleanupInterval time.Duration
	stopCleanup     chan struct{}
}

// NewMemoryCache creates a new in-memory cache
func NewMemoryCache(maxEntries int, maxMemory int64, defaultTTL time.Duration) *MemoryCache {
	mc := &MemoryCache{
		entries:         make(map[string]*CacheEntry),
		maxEntries:      maxEntries,
		maxMemory:       maxMemory,
		defaultTTL:      defaultTTL,
		cleanupInterval: 1 * time.Minute,
		stopCleanup:     make(chan struct{}),
	}
	
	// Start cleanup goroutine
	go mc.cleanupLoop()
	
	return mc
}

// Get retrieves a value from the cache
func (mc *MemoryCache) Get(ctx context.Context, key string) (interface{}, bool) {
	mc.mu.RLock()
	entry, exists := mc.entries[key]
	mc.mu.RUnlock()
	
	if !exists {
		atomic.AddInt64(&mc.misses, 1)
		return nil, false
	}
	
	// Check if entry has expired
	if mc.isExpired(entry) {
		mc.mu.Lock()
		delete(mc.entries, key)
		mc.mu.Unlock()
		
		atomic.AddInt64(&mc.misses, 1)
		return nil, false
	}
	
	// Update access count and return value
	atomic.AddInt64(&entry.AccessCount, 1)
	atomic.AddInt64(&mc.hits, 1)
	
	return entry.Value, true
}

// Set stores a value in the cache with TTL
func (mc *MemoryCache) Set(ctx context.Context, key string, value interface{}, ttl time.Duration) error {
	if ttl <= 0 {
		ttl = mc.defaultTTL
	}
	
	entry := &CacheEntry{
		Key:         key,
		Value:       value,
		CreatedAt:   time.Now(),
		TTL:         ttl,
		AccessCount: 0,
	}
	
	mc.mu.Lock()
	defer mc.mu.Unlock()
	
	// Check if we need to evict entries
	if len(mc.entries) >= mc.maxEntries {
		mc.evictLRU()
	}
	
	// Add or update entry
	if existing, exists := mc.entries[key]; exists {
		// Update existing entry
		mc.currentMemory -= mc.estimateSize(existing.Value)
	}
	
	mc.entries[key] = entry
	mc.currentMemory += mc.estimateSize(value)
	
	// Check memory limit
	for mc.currentMemory > mc.maxMemory && len(mc.entries) > 0 {
		mc.evictLRU()
	}
	
	return nil
}

// Delete removes an entry from the cache
func (mc *MemoryCache) Delete(ctx context.Context, key string) error {
	mc.mu.Lock()
	defer mc.mu.Unlock()
	
	if entry, exists := mc.entries[key]; exists {
		mc.currentMemory -= mc.estimateSize(entry.Value)
		delete(mc.entries, key)
	}
	
	return nil
}

// Clear removes all entries from the cache
func (mc *MemoryCache) Clear(ctx context.Context) error {
	mc.mu.Lock()
	defer mc.mu.Unlock()
	
	mc.entries = make(map[string]*CacheEntry)
	mc.currentMemory = 0
	
	return nil
}

// Stats returns cache statistics
func (mc *MemoryCache) Stats(ctx context.Context) (CacheStats, error) {
	mc.mu.RLock()
	defer mc.mu.RUnlock()
	
	return CacheStats{
		TotalEntries: int64(len(mc.entries)),
		MemoryUsage:  mc.currentMemory,
		HitCount:     atomic.LoadInt64(&mc.hits),
		MissCount:    atomic.LoadInt64(&mc.misses),
		EvictCount:   atomic.LoadInt64(&mc.evictions),
	}, nil
}

// isExpired checks if a cache entry has expired
func (mc *MemoryCache) isExpired(entry *CacheEntry) bool {
	return time.Since(entry.CreatedAt) > entry.TTL
}

// evictLRU evicts the least recently used entry (must be called with lock held)
func (mc *MemoryCache) evictLRU() {
	if len(mc.entries) == 0 {
		return
	}
	
	var lruKey string
	var lruEntry *CacheEntry
	var minAccessCount int64 = -1
	
	// Find LRU entry (simple implementation, could be optimized with heap)
	for key, entry := range mc.entries {
		if minAccessCount == -1 || entry.AccessCount < minAccessCount {
			lruKey = key
			lruEntry = entry
			minAccessCount = entry.AccessCount
		}
	}
	
	if lruKey != "" {
		mc.currentMemory -= mc.estimateSize(lruEntry.Value)
		delete(mc.entries, lruKey)
		atomic.AddInt64(&mc.evictions, 1)
	}
}

// estimateSize estimates the memory size of a value (simplified)
func (mc *MemoryCache) estimateSize(value interface{}) int64 {
	// This is a simplified estimation
	// In production, you might want to use a more accurate method
	switch v := value.(type) {
	case string:
		return int64(len(v))
	case []byte:
		return int64(len(v))
	case map[string]interface{}:
		// Rough estimate for maps
		return int64(len(v) * 100)
	case []interface{}:
		// Rough estimate for slices
		return int64(len(v) * 50)
	default:
		// Default size for other types
		return 64
	}
}

// cleanupLoop runs periodic cleanup of expired entries
func (mc *MemoryCache) cleanupLoop() {
	ticker := time.NewTicker(mc.cleanupInterval)
	defer ticker.Stop()
	
	for {
		select {
		case <-ticker.C:
			mc.cleanupExpired()
		case <-mc.stopCleanup:
			return
		}
	}
}

// cleanupExpired removes all expired entries
func (mc *MemoryCache) cleanupExpired() {
	mc.mu.Lock()
	defer mc.mu.Unlock()
	
	now := time.Now()
	for key, entry := range mc.entries {
		if now.Sub(entry.CreatedAt) > entry.TTL {
			mc.currentMemory -= mc.estimateSize(entry.Value)
			delete(mc.entries, key)
			atomic.AddInt64(&mc.evictions, 1)
		}
	}
}

// Close stops the cleanup loop
func (mc *MemoryCache) Close() error {
	close(mc.stopCleanup)
	return nil
}

// HitRate returns the cache hit rate
func (mc *MemoryCache) HitRate() float64 {
	hits := atomic.LoadInt64(&mc.hits)
	misses := atomic.LoadInt64(&mc.misses)
	total := hits + misses
	
	if total == 0 {
		return 0
	}
	
	return float64(hits) / float64(total)
}