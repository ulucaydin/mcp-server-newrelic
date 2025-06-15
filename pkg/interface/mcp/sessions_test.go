package mcp

import (
	"testing"
	"time"
)

func TestSessionManagerConcurrency(t *testing.T) {
	manager := NewSessionManager()
	
	// Test concurrent session creation
	sessionIDs := make(chan string, 10)
	for i := 0; i < 10; i++ {
		go func() {
			session := manager.Create()
			sessionIDs <- session.ID
		}()
	}
	
	// Collect all session IDs
	ids := make(map[string]bool)
	for i := 0; i < 10; i++ {
		id := <-sessionIDs
		if ids[id] {
			t.Errorf("Duplicate session ID: %s", id)
		}
		ids[id] = true
	}
	
	// Verify all sessions exist
	for id := range ids {
		if _, exists := manager.Get(id); !exists {
			t.Errorf("Session %s not found", id)
		}
	}
}

func TestSessionManagerUpdates(t *testing.T) {
	manager := NewSessionManager()
	
	// Create session
	session := manager.Create()
	originalID := session.ID
	
	// Update session context
	session.Context["key1"] = "value1"
	session.Context["key2"] = 42
	session.LastUsed = time.Now()
	
	if err := manager.Update(session); err != nil {
		t.Fatalf("Failed to update session: %v", err)
	}
	
	// Retrieve and verify
	retrieved, exists := manager.Get(originalID)
	if !exists {
		t.Fatal("Session not found after update")
	}
	
	if retrieved.Context["key1"] != "value1" {
		t.Error("Context key1 not updated")
	}
	
	if retrieved.Context["key2"] != 42 {
		t.Error("Context key2 not updated")
	}
	
	// Test updating non-existent session
	fakeSession := &Session{
		ID:      "non-existent",
		Context: make(map[string]interface{}),
	}
	
	if err := manager.Update(fakeSession); err == nil {
		t.Error("Expected error updating non-existent session")
	}
}

func TestSessionManagerDeletion(t *testing.T) {
	manager := NewSessionManager()
	
	// Create multiple sessions
	created := make([]*Session, 5)
	for i := 0; i < 5; i++ {
		created[i] = manager.Create()
	}
	
	// Verify all sessions exist
	for _, session := range created {
		if _, exists := manager.Get(session.ID); !exists {
			t.Errorf("Session %s not found", session.ID)
		}
	}
	
	// Delete some sessions
	manager.Delete(created[1].ID)
	manager.Delete(created[3].ID)
	
	// Verify deleted sessions are gone
	if _, exists := manager.Get(created[1].ID); exists {
		t.Error("Deleted session 1 still exists")
	}
	if _, exists := manager.Get(created[3].ID); exists {
		t.Error("Deleted session 3 still exists")
	}
	
	// Verify other sessions still exist
	if _, exists := manager.Get(created[0].ID); !exists {
		t.Error("Session 0 should still exist")
	}
	if _, exists := manager.Get(created[2].ID); !exists {
		t.Error("Session 2 should still exist")
	}
	if _, exists := manager.Get(created[4].ID); !exists {
		t.Error("Session 4 should still exist")
	}
}

func TestSessionManagerExpiration(t *testing.T) {
	// Note: This test is a placeholder for future expiration functionality
	// In a real implementation, you might want to add session expiration
	manager := NewSessionManager()
	
	session := manager.Create()
	
	// Simulate time passing
	session.LastUsed = time.Now().Add(-2 * time.Hour)
	manager.Update(session)
	
	// In a real implementation, you might have a method like:
	// manager.CleanupExpired(1 * time.Hour)
	
	// For now, just verify the session still exists
	if _, exists := manager.Get(session.ID); !exists {
		t.Error("Session should still exist (no expiration implemented)")
	}
}