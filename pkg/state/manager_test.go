package state

import (
	"context"
	"testing"
	"time"
)

func TestManager_SessionOperations(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Create session
	session, err := manager.CreateSession(ctx, "explore database performance")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	if session.ID == "" {
		t.Error("Session ID should not be empty")
	}
	
	// Get session
	retrieved, err := manager.GetSession(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to get session: %v", err)
	}
	
	if retrieved.UserGoal != "explore database performance" {
		t.Errorf("Goal mismatch: got %s", retrieved.UserGoal)
	}
	
	// Update session
	session.DiscoveredSchemas = []string{"Transaction", "DatabaseCall"}
	err = manager.UpdateSession(ctx, session)
	if err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}
	
	// Delete session
	err = manager.DeleteSession(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	
	// Verify deletion
	_, err = manager.GetSession(ctx, session.ID)
	if err == nil {
		t.Error("Expected error for deleted session")
	}
}

func TestManager_CacheOperations(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Test cache operations
	err := manager.Set(ctx, "test-key", "test-value", 5*time.Minute)
	if err != nil {
		t.Fatalf("Failed to set cache value: %v", err)
	}
	
	value, found := manager.Get(ctx, "test-key")
	if !found {
		t.Error("Cache value should be found")
	}
	
	if value != "test-value" {
		t.Errorf("Expected 'test-value', got '%v'", value)
	}
	
	// Test cache stats
	stats, err := manager.Stats(ctx)
	if err != nil {
		t.Fatalf("Failed to get stats: %v", err)
	}
	
	if stats.TotalEntries < 1 {
		t.Error("Should have at least one cache entry")
	}
}

func TestManager_SessionWithCache(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Create session
	session, err := manager.CreateSession(ctx, "analyze application errors")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Update session with discovered schemas
	session.DiscoveredSchemas = []string{"TransactionError", "JavaScriptError"}
	err = manager.UpdateSession(ctx, session)
	if err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}
	
	// Cache discovery results
	err = manager.CacheDiscoveryResult(ctx, session.ID, "schema", "TransactionError", map[string]interface{}{
		"attributes": []string{"error.message", "error.class", "duration"},
		"volume":     1000000,
	})
	if err != nil {
		t.Fatalf("Failed to cache discovery result: %v", err)
	}
	
	err = manager.CacheDiscoveryResult(ctx, session.ID, "schema", "JavaScriptError", map[string]interface{}{
		"attributes": []string{"errorMessage", "stackTrace", "pageUrl"},
		"volume":     500000,
	})
	if err != nil {
		t.Fatalf("Failed to cache discovery result: %v", err)
	}
	
	// Get session with cache
	retrievedSession, cachedResults, err := manager.GetSessionWithCache(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to get session with cache: %v", err)
	}
	
	if len(retrievedSession.DiscoveredSchemas) != 2 {
		t.Errorf("Expected 2 discovered schemas, got %d", len(retrievedSession.DiscoveredSchemas))
	}
	
	if len(cachedResults) != 2 {
		t.Errorf("Expected 2 cached results, got %d", len(cachedResults))
	}
	
	// Verify cached data
	if txError, ok := cachedResults["TransactionError"]; ok {
		if txMap, ok := txError.(map[string]interface{}); ok {
			if volume, ok := txMap["volume"].(int); ok && volume != 1000000 {
				t.Errorf("Expected volume 1000000, got %d", volume)
			}
		}
	} else {
		t.Error("TransactionError should be in cached results")
	}
}

func TestManager_GetDiscoveryResult(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Create session
	session, err := manager.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Cache a discovery result
	testData := map[string]interface{}{
		"schema": "TestSchema",
		"attributes": []string{"attr1", "attr2"},
	}
	
	err = manager.CacheDiscoveryResult(ctx, session.ID, "schema", "TestSchema", testData)
	if err != nil {
		t.Fatalf("Failed to cache result: %v", err)
	}
	
	// Retrieve the result
	result, found := manager.GetDiscoveryResult(ctx, session.ID, "schema", "TestSchema")
	if !found {
		t.Error("Discovery result should be found")
	}
	
	resultMap, ok := result.(map[string]interface{})
	if !ok {
		t.Error("Result should be a map")
	}
	
	if resultMap["schema"] != "TestSchema" {
		t.Errorf("Schema mismatch: got %v", resultMap["schema"])
	}
	
	// Try to get non-existent result
	_, found = manager.GetDiscoveryResult(ctx, session.ID, "schema", "NonExistent")
	if found {
		t.Error("Non-existent result should not be found")
	}
}

func TestManager_WarmCache(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Create session with specific goal
	session, err := manager.CreateSession(ctx, "explore transaction performance")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Warm cache
	err = manager.WarmCache(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to warm cache: %v", err)
	}
	
	// Check if pre-loaded data exists
	schemas := []string{"Transaction", "TransactionError", "TransactionTrace"}
	for _, schema := range schemas {
		result, found := manager.GetDiscoveryResult(ctx, session.ID, "schema", schema)
		if !found {
			t.Errorf("Schema %s should be pre-loaded", schema)
			continue
		}
		
		// Verify it's pre-loaded data
		if resultStr, ok := result.(string); ok {
			expectedPrefix := "pre-loaded schema:"
			if len(resultStr) <= len(expectedPrefix) || resultStr[:len(expectedPrefix)] != expectedPrefix {
				t.Errorf("Expected pre-loaded data for %s, got %v", schema, result)
			}
		}
	}
}

func TestManager_ContextOperations(t *testing.T) {
	config := DefaultManagerConfig()
	manager := NewManager(config)
	defer manager.Close()
	
	ctx := context.Background()
	
	// Create session
	session, err := manager.CreateSession(ctx, "test context operations")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Set various context values
	testCases := []struct {
		key   string
		value interface{}
	}{
		{"string_value", "test string"},
		{"int_value", 42},
		{"bool_value", true},
		{"map_value", map[string]interface{}{"nested": "value"}},
		{"slice_value", []string{"a", "b", "c"}},
	}
	
	for _, tc := range testCases {
		err := manager.SetContext(ctx, session.ID, tc.key, tc.value)
		if err != nil {
			t.Errorf("Failed to set context %s: %v", tc.key, err)
		}
	}
	
	// Retrieve and verify context values
	for _, tc := range testCases {
		value, err := manager.GetContext(ctx, session.ID, tc.key)
		if err != nil {
			t.Errorf("Failed to get context %s: %v", tc.key, err)
			continue
		}
		
		// Simple comparison for basic types
		switch tc.key {
		case "string_value":
			if value != tc.value {
				t.Errorf("Context %s mismatch: expected %v, got %v", tc.key, tc.value, value)
			}
		case "int_value":
			if value != tc.value {
				t.Errorf("Context %s mismatch: expected %v, got %v", tc.key, tc.value, value)
			}
		case "bool_value":
			if value != tc.value {
				t.Errorf("Context %s mismatch: expected %v, got %v", tc.key, tc.value, value)
			}
		}
	}
}