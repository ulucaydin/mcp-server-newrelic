package api

import (
	"encoding/json"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/auth"
)

// LoginRequest represents a login request
type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

// LoginResponse represents a login response
type LoginResponse struct {
	Token     string    `json:"token"`
	ExpiresAt time.Time `json:"expires_at"`
	TokenType string    `json:"token_type"`
	User      UserInfo  `json:"user"`
}

// UserInfo represents basic user information
type UserInfo struct {
	ID        string   `json:"id"`
	Email     string   `json:"email"`
	AccountID string   `json:"account_id"`
	Roles     []string `json:"roles"`
}

// RefreshRequest represents a token refresh request
type RefreshRequest struct {
	Token string `json:"token"`
}

// CreateAPIKeyRequest represents a request to create an API key
type CreateAPIKeyRequest struct {
	Name        string    `json:"name"`
	Permissions []string  `json:"permissions"`
	ExpiresAt   *time.Time `json:"expires_at,omitempty"`
}

// handleLogin handles user login
func (s *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	var req LoginRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid request body", nil)
		return
	}

	// TODO: Validate credentials against user store
	// For now, we'll use a simple mock validation
	if req.Email == "" || req.Password == "" {
		writeError(w, http.StatusBadRequest, "Email and password are required", nil)
		return
	}

	// Mock user data
	userID := "user_123"
	accountID := "account_456"
	roles := []string{"user"}
	
	// For demo purposes, admin@example.com gets admin role
	if req.Email == "admin@example.com" {
		roles = append(roles, "admin")
	}

	// Generate JWT token
	tokenInfo, err := s.jwtManager.GenerateToken(userID, req.Email, accountID, roles)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to generate token", nil)
		return
	}

	response := LoginResponse{
		Token:     tokenInfo.Token,
		ExpiresAt: tokenInfo.ExpiresAt,
		TokenType: tokenInfo.TokenType,
		User: UserInfo{
			ID:        userID,
			Email:     req.Email,
			AccountID: accountID,
			Roles:     roles,
		},
	}

	writeJSON(w, http.StatusOK, response)
}

// handleRefreshToken handles token refresh
func (s *Server) handleRefreshToken(w http.ResponseWriter, r *http.Request) {
	var req RefreshRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid request body", nil)
		return
	}

	tokenInfo, err := s.jwtManager.RefreshToken(req.Token)
	if err != nil {
		writeError(w, http.StatusUnauthorized, "Invalid or expired token", nil)
		return
	}

	writeJSON(w, http.StatusOK, tokenInfo)
}

// handleLogout handles user logout
func (s *Server) handleLogout(w http.ResponseWriter, r *http.Request) {
	// In a real implementation, you might want to:
	// - Add the token to a blacklist
	// - Clear any server-side sessions
	// - Log the logout event
	
	writeJSON(w, http.StatusOK, map[string]string{
		"message": "Successfully logged out",
	})
}

// handleListAPIKeys lists all API keys for the authenticated user
func (s *Server) handleListAPIKeys(w http.ResponseWriter, r *http.Request) {
	userID, ok := auth.GetUserID(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "User not authenticated", nil)
		return
	}

	keys, err := s.apiKeyManager.ListAPIKeys(userID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to list API keys", nil)
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"keys": keys,
	})
}

// handleCreateAPIKey creates a new API key
func (s *Server) handleCreateAPIKey(w http.ResponseWriter, r *http.Request) {
	userID, ok := auth.GetUserID(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "User not authenticated", nil)
		return
	}

	accountID, ok := auth.GetAccountID(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "Account not found", nil)
		return
	}

	var req CreateAPIKeyRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "Invalid request body", nil)
		return
	}

	if req.Name == "" {
		writeError(w, http.StatusBadRequest, "API key name is required", nil)
		return
	}

	// Default permissions if none specified
	if len(req.Permissions) == 0 {
		req.Permissions = []string{"read:schemas", "read:patterns", "read:queries"}
	}

	apiKey, err := s.apiKeyManager.GenerateAPIKey(req.Name, userID, accountID, req.Permissions, req.ExpiresAt)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to create API key", nil)
		return
	}

	writeJSON(w, http.StatusCreated, apiKey)
}

// handleRevokeAPIKey revokes an API key
func (s *Server) handleRevokeAPIKey(w http.ResponseWriter, r *http.Request) {
	userID, ok := auth.GetUserID(r.Context())
	if !ok {
		writeError(w, http.StatusUnauthorized, "User not authenticated", nil)
		return
	}

	vars := mux.Vars(r)
	keyID := vars["id"]

	// Verify the key belongs to the user
	keys, err := s.apiKeyManager.ListAPIKeys(userID)
	if err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to verify API key ownership", nil)
		return
	}

	found := false
	for _, key := range keys {
		if key.ID == keyID {
			found = true
			break
		}
	}

	if !found {
		writeError(w, http.StatusNotFound, "API key not found", nil)
		return
	}

	if err := s.apiKeyManager.RevokeAPIKey(keyID); err != nil {
		writeError(w, http.StatusInternalServerError, "Failed to revoke API key", nil)
		return
	}

	writeJSON(w, http.StatusOK, map[string]string{
		"message": "API key revoked successfully",
	})
}