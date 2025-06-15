package state

import (
	"context"
	"testing"
	"time"
)

func TestMemoryStore_CreateSession(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	defer store.Close()
	
	ctx := context.Background()
	
	// Test creating a session
	session, err := store.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	if session.ID == "" {
		t.Error("Session ID should not be empty")
	}
	
	if session.UserGoal != "test goal" {
		t.Errorf("Expected goal 'test goal', got '%s'", session.UserGoal)
	}
	
	if session.Context == nil {
		t.Error("Session context should be initialized")
	}
	
	if session.TTL != 1*time.Hour {
		t.Errorf("Expected TTL 1 hour, got %v", session.TTL)
	}
}

func TestMemoryStore_GetSession(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create a session
	created, err := store.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Get the session
	retrieved, err := store.GetSession(ctx, created.ID)
	if err != nil {
		t.Fatalf("Failed to get session: %v", err)
	}
	
	if retrieved.ID != created.ID {
		t.Errorf("Session ID mismatch: expected %s, got %s", created.ID, retrieved.ID)
	}
	
	if retrieved.UserGoal != created.UserGoal {
		t.Errorf("Goal mismatch: expected %s, got %s", created.UserGoal, retrieved.UserGoal)
	}
	
	// Test getting non-existent session
	_, err = store.GetSession(ctx, "non-existent")
	if err == nil {
		t.Error("Expected error for non-existent session")
	}
}

func TestMemoryStore_UpdateSession(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create a session
	session, err := store.CreateSession(ctx, "original goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Update the session
	session.UserGoal = "updated goal"
	session.DiscoveredSchemas = []string{"schema1", "schema2"}
	
	err = store.UpdateSession(ctx, session)
	if err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}
	
	// Retrieve and verify
	updated, err := store.GetSession(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to get updated session: %v", err)
	}
	
	if updated.UserGoal != "updated goal" {
		t.Errorf("Goal not updated: expected 'updated goal', got '%s'", updated.UserGoal)
	}
	
	if len(updated.DiscoveredSchemas) != 2 {
		t.Errorf("Schemas not updated: expected 2, got %d", len(updated.DiscoveredSchemas))
	}
}

func TestMemoryStore_Context(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create a session
	session, err := store.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Set context
	err = store.SetContext(ctx, session.ID, "key1", "value1")
	if err != nil {
		t.Fatalf("Failed to set context: %v", err)
	}
	
	err = store.SetContext(ctx, session.ID, "key2", map[string]interface{}{
		"nested": "value",
	})
	if err != nil {
		t.Fatalf("Failed to set complex context: %v", err)
	}
	
	// Get context
	value1, err := store.GetContext(ctx, session.ID, "key1")
	if err != nil {
		t.Fatalf("Failed to get context: %v", err)
	}
	
	if value1 != "value1" {
		t.Errorf("Context value mismatch: expected 'value1', got '%v'", value1)
	}
	
	// Get non-existent key
	_, err = store.GetContext(ctx, session.ID, "non-existent")
	if err == nil {
		t.Error("Expected error for non-existent context key")
	}
}

func TestMemoryStore_DeleteSession(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create a session
	session, err := store.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Delete the session
	err = store.DeleteSession(ctx, session.ID)
	if err != nil {
		t.Fatalf("Failed to delete session: %v", err)
	}
	
	// Verify it's gone
	_, err = store.GetSession(ctx, session.ID)
	if err == nil {
		t.Error("Expected error when getting deleted session")
	}
	
	// Delete non-existent session
	err = store.DeleteSession(ctx, "non-existent")
	if err == nil {
		t.Error("Expected error when deleting non-existent session")
	}
}

func TestMemoryStore_Expiration(t *testing.T) {
	// Use short TTL for testing
	store := NewMemoryStore(100 * time.Millisecond)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create a session
	session, err := store.CreateSession(ctx, "test goal")
	if err != nil {
		t.Fatalf("Failed to create session: %v", err)
	}
	
	// Session should be accessible immediately
	_, err = store.GetSession(ctx, session.ID)
	if err != nil {
		t.Errorf("Session should be accessible immediately: %v", err)
	}
	
	// Wait for expiration
	time.Sleep(200 * time.Millisecond)
	
	// Session should be expired
	_, err = store.GetSession(ctx, session.ID)
	if err == nil {
		t.Error("Expected error for expired session")
	}
}

func TestMemoryStore_CleanupExpired(t *testing.T) {
	// Use short TTL for testing
	store := NewMemoryStore(100 * time.Millisecond)
	defer store.Close()
	
	ctx := context.Background()
	
	// Create multiple sessions
	for i := 0; i < 5; i++ {
		_, err := store.CreateSession(ctx, "test goal")
		if err != nil {
			t.Fatalf("Failed to create session %d: %v", i, err)
		}
	}
	
	// Check initial stats
	stats := store.Stats()
	if stats.TotalSessions != 5 {
		t.Errorf("Expected 5 sessions, got %d", stats.TotalSessions)
	}
	
	// Wait for expiration
	time.Sleep(200 * time.Millisecond)
	
	// Run cleanup
	err := store.CleanupExpired(ctx)
	if err != nil {
		t.Fatalf("Failed to cleanup: %v", err)
	}
	
	// Check stats after cleanup
	stats = store.Stats()
	if stats.TotalSessions != 0 {
		t.Errorf("Expected 0 sessions after cleanup, got %d", stats.TotalSessions)
	}
}

func TestMemoryStore_MaxSessions(t *testing.T) {
	store := NewMemoryStore(1 * time.Hour)
	store.maxSessions = 3 // Set low limit for testing
	defer store.Close()
	
	ctx := context.Background()
	
	// Create sessions up to the limit
	for i := 0; i < 3; i++ {
		_, err := store.CreateSession(ctx, "test goal")
		if err != nil {
			t.Fatalf("Failed to create session %d: %v", i, err)
		}
	}
	
	// Try to create one more
	_, err := store.CreateSession(ctx, "test goal")
	if err == nil {
		t.Error("Expected error when exceeding session limit")
	}
}