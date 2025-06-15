package auth

import (
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
	"sync"
	"time"
)

// APIKeyManager manages API keys
type APIKeyManager struct {
	salt      string
	store     APIKeyStore
	mu        sync.RWMutex
	cache     map[string]*APIKey
	cacheSize int
}

// APIKey represents an API key
type APIKey struct {
	ID          string    `json:"id"`
	Name        string    `json:"name"`
	Key         string    `json:"key,omitempty"` // Only set when creating
	KeyHash     string    `json:"-"`
	UserID      string    `json:"user_id"`
	AccountID   string    `json:"account_id"`
	Permissions []string  `json:"permissions"`
	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	LastUsedAt  *time.Time `json:"last_used_at,omitempty"`
	Active      bool      `json:"active"`
}

// APIKeyStore interface for storing API keys
type APIKeyStore interface {
	Create(key *APIKey) error
	Get(id string) (*APIKey, error)
	GetByHash(keyHash string) (*APIKey, error)
	Update(key *APIKey) error
	Delete(id string) error
	List(userID string) ([]*APIKey, error)
}

// NewAPIKeyManager creates a new API key manager
func NewAPIKeyManager(salt string, store APIKeyStore) *APIKeyManager {
	return &APIKeyManager{
		salt:      salt,
		store:     store,
		cache:     make(map[string]*APIKey),
		cacheSize: 1000,
	}
}

// GenerateAPIKey generates a new API key
func (m *APIKeyManager) GenerateAPIKey(name, userID, accountID string, permissions []string, expiresAt *time.Time) (*APIKey, error) {
	// Generate random key
	keyBytes := make([]byte, 32)
	if _, err := rand.Read(keyBytes); err != nil {
		return nil, fmt.Errorf("failed to generate random key: %w", err)
	}

	// Format as readable API key
	rawKey := hex.EncodeToString(keyBytes)
	formattedKey := fmt.Sprintf("nr_%s", rawKey)

	// Hash the key for storage
	keyHash := m.hashKey(formattedKey)

	apiKey := &APIKey{
		ID:          generateID(),
		Name:        name,
		Key:         formattedKey,
		KeyHash:     keyHash,
		UserID:      userID,
		AccountID:   accountID,
		Permissions: permissions,
		ExpiresAt:   expiresAt,
		CreatedAt:   time.Now(),
		Active:      true,
	}

	// Store the key
	if err := m.store.Create(apiKey); err != nil {
		return nil, fmt.Errorf("failed to store API key: %w", err)
	}

	// Cache the key
	m.mu.Lock()
	m.cache[keyHash] = apiKey
	m.mu.Unlock()

	return apiKey, nil
}

// ValidateAPIKey validates an API key
func (m *APIKeyManager) ValidateAPIKey(key string) (*APIKey, error) {
	if !strings.HasPrefix(key, "nr_") {
		return nil, errors.New("invalid API key format")
	}

	keyHash := m.hashKey(key)

	// Check cache first
	m.mu.RLock()
	if apiKey, ok := m.cache[keyHash]; ok {
		m.mu.RUnlock()
		if m.isValidKey(apiKey) {
			// Update last used time asynchronously
			go m.updateLastUsed(apiKey.ID)
			return apiKey, nil
		}
		// Remove expired key from cache
		m.mu.Lock()
		delete(m.cache, keyHash)
		m.mu.Unlock()
		return nil, errors.New("API key expired or inactive")
	}
	m.mu.RUnlock()

	// Not in cache, fetch from store
	apiKey, err := m.store.GetByHash(keyHash)
	if err != nil {
		return nil, fmt.Errorf("invalid API key: %w", err)
	}

	if !m.isValidKey(apiKey) {
		return nil, errors.New("API key expired or inactive")
	}

	// Add to cache
	m.mu.Lock()
	if len(m.cache) >= m.cacheSize {
		// Simple eviction: remove first item
		for k := range m.cache {
			delete(m.cache, k)
			break
		}
	}
	m.cache[keyHash] = apiKey
	m.mu.Unlock()

	// Update last used time asynchronously
	go m.updateLastUsed(apiKey.ID)

	return apiKey, nil
}

// RevokeAPIKey revokes an API key
func (m *APIKeyManager) RevokeAPIKey(id string) error {
	apiKey, err := m.store.Get(id)
	if err != nil {
		return fmt.Errorf("failed to get API key: %w", err)
	}

	apiKey.Active = false
	if err := m.store.Update(apiKey); err != nil {
		return fmt.Errorf("failed to update API key: %w", err)
	}

	// Remove from cache
	m.mu.Lock()
	delete(m.cache, apiKey.KeyHash)
	m.mu.Unlock()

	return nil
}

// ListAPIKeys lists all API keys for a user
func (m *APIKeyManager) ListAPIKeys(userID string) ([]*APIKey, error) {
	keys, err := m.store.List(userID)
	if err != nil {
		return nil, fmt.Errorf("failed to list API keys: %w", err)
	}

	// Clear the Key field for security
	for _, key := range keys {
		key.Key = ""
	}

	return keys, nil
}

// hashKey hashes an API key with salt
func (m *APIKeyManager) hashKey(key string) string {
	h := sha256.New()
	h.Write([]byte(key + m.salt))
	return hex.EncodeToString(h.Sum(nil))
}

// isValidKey checks if an API key is valid
func (m *APIKeyManager) isValidKey(key *APIKey) bool {
	if !key.Active {
		return false
	}

	if key.ExpiresAt != nil && key.ExpiresAt.Before(time.Now()) {
		return false
	}

	return true
}

// updateLastUsed updates the last used timestamp
func (m *APIKeyManager) updateLastUsed(id string) {
	apiKey, err := m.store.Get(id)
	if err != nil {
		return
	}

	now := time.Now()
	apiKey.LastUsedAt = &now
	m.store.Update(apiKey)
}

// generateID generates a unique ID
func generateID() string {
	return fmt.Sprintf("key_%d_%s", time.Now().UnixNano(), randomString(8))
}