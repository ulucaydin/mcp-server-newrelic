package mcp

import (
	"context"
	"errors"
	"strings"
	
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/auth"
)

// AuthProvider handles authentication for MCP connections
type AuthProvider interface {
	// Authenticate validates credentials and returns user context
	Authenticate(ctx context.Context, credentials map[string]interface{}) (context.Context, error)
	
	// IsAuthorized checks if a user has permission for a specific tool
	IsAuthorized(ctx context.Context, tool string) bool
}

// JWTAuthProvider implements JWT-based authentication for MCP
type JWTAuthProvider struct {
	jwtManager    *auth.JWTManager
	apiKeyManager *auth.APIKeyManager
}

// NewJWTAuthProvider creates a new JWT auth provider
func NewJWTAuthProvider(jwtManager *auth.JWTManager, apiKeyManager *auth.APIKeyManager) *JWTAuthProvider {
	return &JWTAuthProvider{
		jwtManager:    jwtManager,
		apiKeyManager: apiKeyManager,
	}
}

// Authenticate validates JWT token or API key from credentials
func (p *JWTAuthProvider) Authenticate(ctx context.Context, credentials map[string]interface{}) (context.Context, error) {
	// Check for Bearer token
	if tokenValue, ok := credentials["token"]; ok {
		if token, ok := tokenValue.(string); ok {
			// Validate JWT token
			if claims, err := p.jwtManager.ValidateToken(token); err == nil {
				ctx = context.WithValue(ctx, auth.ContextKeyClaims, claims)
				ctx = context.WithValue(ctx, auth.ContextKeyUserID, claims.UserID)
				ctx = context.WithValue(ctx, auth.ContextKeyAccountID, claims.AccountID)
				return ctx, nil
			}
		}
	}
	
	// Check for API key
	if apiKeyValue, ok := credentials["apiKey"]; ok {
		if apiKey, ok := apiKeyValue.(string); ok && p.apiKeyManager != nil {
			// Validate API key
			if keyInfo, err := p.apiKeyManager.ValidateAPIKey(apiKey); err == nil {
				ctx = context.WithValue(ctx, auth.ContextKeyAPIKey, keyInfo)
				ctx = context.WithValue(ctx, auth.ContextKeyUserID, keyInfo.UserID)
				ctx = context.WithValue(ctx, auth.ContextKeyAccountID, keyInfo.AccountID)
				return ctx, nil
			}
		}
	}
	
	return ctx, errors.New("invalid credentials")
}

// IsAuthorized checks if the authenticated user can access a tool
func (p *JWTAuthProvider) IsAuthorized(ctx context.Context, tool string) bool {
	// Map tools to permissions
	requiredPermission := toolToPermission(tool)
	
	// Check JWT claims
	if claims, ok := auth.GetClaims(ctx); ok {
		// Admin role has access to all tools
		for _, role := range claims.Roles {
			if role == "admin" {
				return true
			}
		}
	}
	
	// Check API key permissions
	if apiKey, ok := auth.GetAPIKey(ctx); ok {
		for _, perm := range apiKey.Permissions {
			if perm == requiredPermission || perm == "*" {
				return true
			}
		}
	}
	
	return false
}

// toolToPermission maps tool names to required permissions
func toolToPermission(tool string) string {
	switch {
	case strings.HasPrefix(tool, "discovery"):
		return "read:schemas"
	case strings.HasPrefix(tool, "pattern"):
		return "read:patterns"
	case strings.HasPrefix(tool, "query"):
		return "read:queries"
	case strings.HasPrefix(tool, "dashboard"):
		return "write:dashboards"
	default:
		return "read:general"
	}
}

// NoOpAuthProvider provides no authentication (for testing or public access)
type NoOpAuthProvider struct{}

// Authenticate always succeeds
func (p *NoOpAuthProvider) Authenticate(ctx context.Context, credentials map[string]interface{}) (context.Context, error) {
	return ctx, nil
}

// IsAuthorized always returns true
func (p *NoOpAuthProvider) IsAuthorized(ctx context.Context, tool string) bool {
	return true
}