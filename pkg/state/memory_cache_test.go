package state

import (
	"context"
	"fmt"
	"testing"
	"time"
)

func TestMemoryCache_SetAndGet(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Set a value
	err := cache.Set(ctx, "key1", "value1", 1*time.Hour)
	if err != nil {
		t.Fatalf("Failed to set value: %v", err)
	}
	
	// Get the value
	value, found := cache.Get(ctx, "key1")
	if !found {
		t.Error("Value should be found")
	}
	
	if value != "value1" {
		t.Errorf("Expected 'value1', got '%v'", value)
	}
	
	// Get non-existent key
	_, found = cache.Get(ctx, "non-existent")
	if found {
		t.Error("Non-existent key should not be found")
	}
}

func TestMemoryCache_ComplexTypes(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Test with map
	mapValue := map[string]interface{}{
		"field1": "value1",
		"field2": 42,
		"field3": []string{"a", "b", "c"},
	}
	
	err := cache.Set(ctx, "map-key", mapValue, 1*time.Hour)
	if err != nil {
		t.Fatalf("Failed to set map value: %v", err)
	}
	
	retrieved, found := cache.Get(ctx, "map-key")
	if !found {
		t.Error("Map value should be found")
	}
	
	retrievedMap, ok := retrieved.(map[string]interface{})
	if !ok {
		t.Error("Retrieved value should be a map")
	}
	
	if retrievedMap["field1"] != "value1" {
		t.Errorf("Map field mismatch")
	}
	
	// Test with slice
	sliceValue := []interface{}{"item1", "item2", "item3"}
	err = cache.Set(ctx, "slice-key", sliceValue, 1*time.Hour)
	if err != nil {
		t.Fatalf("Failed to set slice value: %v", err)
	}
	
	retrieved, found = cache.Get(ctx, "slice-key")
	if !found {
		t.Error("Slice value should be found")
	}
	
	retrievedSlice, ok := retrieved.([]interface{})
	if !ok || len(retrievedSlice) != 3 {
		t.Error("Retrieved value should be a slice of length 3")
	}
}

func TestMemoryCache_TTL(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Set value with short TTL
	err := cache.Set(ctx, "short-ttl", "value", 100*time.Millisecond)
	if err != nil {
		t.Fatalf("Failed to set value: %v", err)
	}
	
	// Should be available immediately
	_, found := cache.Get(ctx, "short-ttl")
	if !found {
		t.Error("Value should be found immediately")
	}
	
	// Wait for expiration
	time.Sleep(200 * time.Millisecond)
	
	// Should be expired
	_, found = cache.Get(ctx, "short-ttl")
	if found {
		t.Error("Value should be expired")
	}
}

func TestMemoryCache_Delete(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Set and delete
	cache.Set(ctx, "key1", "value1", 1*time.Hour)
	
	err := cache.Delete(ctx, "key1")
	if err != nil {
		t.Fatalf("Failed to delete: %v", err)
	}
	
	_, found := cache.Get(ctx, "key1")
	if found {
		t.Error("Deleted value should not be found")
	}
}

func TestMemoryCache_Clear(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Add multiple values
	for i := 0; i < 10; i++ {
		cache.Set(ctx, fmt.Sprintf("key%d", i), fmt.Sprintf("value%d", i), 1*time.Hour)
	}
	
	// Clear cache
	err := cache.Clear(ctx)
	if err != nil {
		t.Fatalf("Failed to clear: %v", err)
	}
	
	// Verify all values are gone
	for i := 0; i < 10; i++ {
		_, found := cache.Get(ctx, fmt.Sprintf("key%d", i))
		if found {
			t.Errorf("Key %d should not be found after clear", i)
		}
	}
}

func TestMemoryCache_Stats(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Initial stats
	stats, err := cache.Stats(ctx)
	if err != nil {
		t.Fatalf("Failed to get stats: %v", err)
	}
	
	if stats.TotalEntries != 0 {
		t.Errorf("Expected 0 entries initially, got %d", stats.TotalEntries)
	}
	
	// Add some entries
	cache.Set(ctx, "key1", "value1", 1*time.Hour)
	cache.Set(ctx, "key2", "value2", 1*time.Hour)
	
	// Trigger some hits and misses
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "missing") // miss
	
	stats, err = cache.Stats(ctx)
	if err != nil {
		t.Fatalf("Failed to get stats: %v", err)
	}
	
	if stats.TotalEntries != 2 {
		t.Errorf("Expected 2 entries, got %d", stats.TotalEntries)
	}
	
	if stats.HitCount != 2 {
		t.Errorf("Expected 2 hits, got %d", stats.HitCount)
	}
	
	if stats.MissCount != 1 {
		t.Errorf("Expected 1 miss, got %d", stats.MissCount)
	}
}

func TestMemoryCache_Eviction(t *testing.T) {
	// Small cache for testing eviction
	cache := NewMemoryCache(3, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Fill cache to capacity
	for i := 0; i < 3; i++ {
		err := cache.Set(ctx, fmt.Sprintf("key%d", i), fmt.Sprintf("value%d", i), 1*time.Hour)
		if err != nil {
			t.Fatalf("Failed to set value %d: %v", i, err)
		}
	}
	
	// Access some keys to set their access count
	cache.Get(ctx, "key1") // key1 has higher access count
	cache.Get(ctx, "key1")
	cache.Get(ctx, "key2") // key2 has medium access count
	// key0 has lowest access count (never accessed)
	
	// Add new key, should evict key0
	err := cache.Set(ctx, "key3", "value3", 1*time.Hour)
	if err != nil {
		t.Fatalf("Failed to set value: %v", err)
	}
	
	// key0 should be evicted (lowest access count)
	_, found := cache.Get(ctx, "key0")
	if found {
		t.Error("key0 should have been evicted")
	}
	
	// Other keys should still exist
	_, found = cache.Get(ctx, "key1")
	if !found {
		t.Error("key1 should still exist")
	}
	
	stats, _ := cache.Stats(ctx)
	if stats.EvictCount != 1 {
		t.Errorf("Expected 1 eviction, got %d", stats.EvictCount)
	}
}

func TestMemoryCache_HitRate(t *testing.T) {
	cache := NewMemoryCache(100, 1<<20, 5*time.Minute)
	defer cache.Close()
	
	ctx := context.Background()
	
	// Set some values
	cache.Set(ctx, "key1", "value1", 1*time.Hour)
	cache.Set(ctx, "key2", "value2", 1*time.Hour)
	
	// Generate hits and misses
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "key1") // hit
	cache.Get(ctx, "key2") // hit
	cache.Get(ctx, "miss1") // miss
	cache.Get(ctx, "miss2") // miss
	
	hitRate := cache.HitRate()
	expectedRate := 3.0 / 5.0 // 3 hits out of 5 total requests
	
	if hitRate != expectedRate {
		t.Errorf("Expected hit rate %.2f, got %.2f", expectedRate, hitRate)
	}
}