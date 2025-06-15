package auth

import (
	"errors"
	"sync"
)

// InMemoryAPIKeyStore is an in-memory implementation of APIKeyStore
type InMemoryAPIKeyStore struct {
	mu      sync.RWMutex
	keys    map[string]*APIKey      // ID -> APIKey
	hashes  map[string]*APIKey      // KeyHash -> APIKey
	byUser  map[string][]*APIKey    // UserID -> []*APIKey
}

// NewInMemoryAPIKeyStore creates a new in-memory API key store
func NewInMemoryAPIKeyStore() *InMemoryAPIKeyStore {
	return &InMemoryAPIKeyStore{
		keys:   make(map[string]*APIKey),
		hashes: make(map[string]*APIKey),
		byUser: make(map[string][]*APIKey),
	}
}

// Create stores a new API key
func (s *InMemoryAPIKeyStore) Create(key *APIKey) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.keys[key.ID]; exists {
		return errors.New("API key with this ID already exists")
	}

	if _, exists := s.hashes[key.KeyHash]; exists {
		return errors.New("API key with this hash already exists")
	}

	s.keys[key.ID] = key
	s.hashes[key.KeyHash] = key
	s.byUser[key.UserID] = append(s.byUser[key.UserID], key)

	return nil
}

// Get retrieves an API key by ID
func (s *InMemoryAPIKeyStore) Get(id string) (*APIKey, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	key, exists := s.keys[id]
	if !exists {
		return nil, errors.New("API key not found")
	}

	return key, nil
}

// GetByHash retrieves an API key by hash
func (s *InMemoryAPIKeyStore) GetByHash(keyHash string) (*APIKey, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	key, exists := s.hashes[keyHash]
	if !exists {
		return nil, errors.New("API key not found")
	}

	return key, nil
}

// Update updates an existing API key
func (s *InMemoryAPIKeyStore) Update(key *APIKey) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	if _, exists := s.keys[key.ID]; !exists {
		return errors.New("API key not found")
	}

	s.keys[key.ID] = key
	s.hashes[key.KeyHash] = key

	// Update in user list
	userKeys := s.byUser[key.UserID]
	for i, k := range userKeys {
		if k.ID == key.ID {
			userKeys[i] = key
			break
		}
	}

	return nil
}

// Delete removes an API key
func (s *InMemoryAPIKeyStore) Delete(id string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	key, exists := s.keys[id]
	if !exists {
		return errors.New("API key not found")
	}

	delete(s.keys, id)
	delete(s.hashes, key.KeyHash)

	// Remove from user list
	userKeys := s.byUser[key.UserID]
	for i, k := range userKeys {
		if k.ID == id {
			s.byUser[key.UserID] = append(userKeys[:i], userKeys[i+1:]...)
			break
		}
	}

	return nil
}

// List returns all API keys for a user
func (s *InMemoryAPIKeyStore) List(userID string) ([]*APIKey, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	keys := s.byUser[userID]
	if keys == nil {
		return []*APIKey{}, nil
	}

	// Return a copy to avoid mutations
	result := make([]*APIKey, len(keys))
	copy(result, keys)
	return result, nil
}