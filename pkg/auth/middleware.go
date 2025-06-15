package auth

import (
	"context"
	"net/http"
	"strings"
)

// contextKey is a custom type for context keys
type contextKey string

const (
	// ContextKeyClaims is the context key for JWT claims
	ContextKeyClaims contextKey = "claims"
	// ContextKeyAPIKey is the context key for API key info
	ContextKeyAPIKey contextKey = "apikey"
	// ContextKeyUserID is the context key for user ID
	ContextKeyUserID contextKey = "user_id"
	// ContextKeyAccountID is the context key for account ID
	ContextKeyAccountID contextKey = "account_id"
)

// AuthMiddleware provides authentication middleware
type AuthMiddleware struct {
	jwtManager    *JWTManager
	apiKeyManager *APIKeyManager
	required      bool
}

// NewAuthMiddleware creates a new authentication middleware
func NewAuthMiddleware(jwtManager *JWTManager, apiKeyManager *APIKeyManager, required bool) *AuthMiddleware {
	return &AuthMiddleware{
		jwtManager:    jwtManager,
		apiKeyManager: apiKeyManager,
		required:      required,
	}
}

// Middleware returns the HTTP middleware function
func (m *AuthMiddleware) Middleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Try to authenticate the request
		ctx, authenticated := m.authenticate(r)

		// If authentication is required and failed, return 401
		if m.required && !authenticated {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		// Continue with authenticated context
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

// authenticate tries to authenticate the request using JWT or API key
func (m *AuthMiddleware) authenticate(r *http.Request) (context.Context, bool) {
	ctx := r.Context()

	// Check Authorization header
	authHeader := r.Header.Get("Authorization")
	if authHeader != "" {
		// Try Bearer token (JWT)
		if strings.HasPrefix(authHeader, "Bearer ") {
			token := strings.TrimPrefix(authHeader, "Bearer ")
			if claims, err := m.jwtManager.ValidateToken(token); err == nil {
				ctx = context.WithValue(ctx, ContextKeyClaims, claims)
				ctx = context.WithValue(ctx, ContextKeyUserID, claims.UserID)
				ctx = context.WithValue(ctx, ContextKeyAccountID, claims.AccountID)
				return ctx, true
			}
		}
	}

	// Check X-API-Key header
	apiKey := r.Header.Get("X-API-Key")
	if apiKey == "" {
		// Also check query parameter as fallback
		apiKey = r.URL.Query().Get("api_key")
	}

	if apiKey != "" && m.apiKeyManager != nil {
		if keyInfo, err := m.apiKeyManager.ValidateAPIKey(apiKey); err == nil {
			ctx = context.WithValue(ctx, ContextKeyAPIKey, keyInfo)
			ctx = context.WithValue(ctx, ContextKeyUserID, keyInfo.UserID)
			ctx = context.WithValue(ctx, ContextKeyAccountID, keyInfo.AccountID)
			return ctx, true
		}
	}

	return ctx, false
}

// RequireAuth creates middleware that requires authentication
func RequireAuth(jwtManager *JWTManager, apiKeyManager *APIKeyManager) func(http.Handler) http.Handler {
	m := NewAuthMiddleware(jwtManager, apiKeyManager, true)
	return m.Middleware
}

// OptionalAuth creates middleware that allows but doesn't require authentication
func OptionalAuth(jwtManager *JWTManager, apiKeyManager *APIKeyManager) func(http.Handler) http.Handler {
	m := NewAuthMiddleware(jwtManager, apiKeyManager, false)
	return m.Middleware
}

// GetClaims retrieves JWT claims from context
func GetClaims(ctx context.Context) (*Claims, bool) {
	claims, ok := ctx.Value(ContextKeyClaims).(*Claims)
	return claims, ok
}

// GetAPIKey retrieves API key info from context
func GetAPIKey(ctx context.Context) (*APIKey, bool) {
	apiKey, ok := ctx.Value(ContextKeyAPIKey).(*APIKey)
	return apiKey, ok
}

// GetUserID retrieves user ID from context
func GetUserID(ctx context.Context) (string, bool) {
	userID, ok := ctx.Value(ContextKeyUserID).(string)
	return userID, ok
}

// GetAccountID retrieves account ID from context
func GetAccountID(ctx context.Context) (string, bool) {
	accountID, ok := ctx.Value(ContextKeyAccountID).(string)
	return accountID, ok
}

// HasRole checks if the authenticated user has a specific role
func HasRole(ctx context.Context, role string) bool {
	if claims, ok := GetClaims(ctx); ok {
		for _, r := range claims.Roles {
			if r == role {
				return true
			}
		}
	}
	return false
}

// HasPermission checks if the authenticated user has a specific permission
func HasPermission(ctx context.Context, permission string) bool {
	// Check JWT claims
	if claims, ok := GetClaims(ctx); ok {
		// Admin role has all permissions
		for _, role := range claims.Roles {
			if role == "admin" {
				return true
			}
		}
	}

	// Check API key permissions
	if apiKey, ok := GetAPIKey(ctx); ok {
		for _, p := range apiKey.Permissions {
			if p == permission || p == "*" {
				return true
			}
		}
	}

	return false
}