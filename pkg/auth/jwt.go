package auth

import (
	"errors"
	"fmt"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

// JWTManager handles JWT token generation and validation
type JWTManager struct {
	secret        []byte
	issuer        string
	tokenDuration time.Duration
}

// Claims represents the JWT claims
type Claims struct {
	UserID    string   `json:"user_id"`
	Email     string   `json:"email"`
	AccountID string   `json:"account_id"`
	Roles     []string `json:"roles"`
	jwt.RegisteredClaims
}

// TokenInfo contains token information
type TokenInfo struct {
	Token     string    `json:"token"`
	ExpiresAt time.Time `json:"expires_at"`
	TokenType string    `json:"token_type"`
}

// NewJWTManager creates a new JWT manager
func NewJWTManager(secret string, issuer string, tokenDuration time.Duration) *JWTManager {
	return &JWTManager{
		secret:        []byte(secret),
		issuer:        issuer,
		tokenDuration: tokenDuration,
	}
}

// GenerateToken generates a new JWT token
func (m *JWTManager) GenerateToken(userID, email, accountID string, roles []string) (*TokenInfo, error) {
	expiresAt := time.Now().Add(m.tokenDuration)
	
	claims := &Claims{
		UserID:    userID,
		Email:     email,
		AccountID: accountID,
		Roles:     roles,
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    m.issuer,
			Subject:   userID,
			ExpiresAt: jwt.NewNumericDate(expiresAt),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			NotBefore: jwt.NewNumericDate(time.Now()),
			ID:        generateTokenID(),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)
	tokenString, err := token.SignedString(m.secret)
	if err != nil {
		return nil, fmt.Errorf("failed to sign token: %w", err)
	}

	return &TokenInfo{
		Token:     tokenString,
		ExpiresAt: expiresAt,
		TokenType: "Bearer",
	}, nil
}

// ValidateToken validates a JWT token and returns the claims
func (m *JWTManager) ValidateToken(tokenString string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(tokenString, &Claims{}, func(token *jwt.Token) (interface{}, error) {
		// Validate the signing method
		if _, ok := token.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", token.Header["alg"])
		}
		return m.secret, nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to parse token: %w", err)
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, errors.New("invalid token")
	}

	return claims, nil
}

// RefreshToken generates a new token from existing claims
func (m *JWTManager) RefreshToken(tokenString string) (*TokenInfo, error) {
	claims, err := m.ValidateToken(tokenString)
	if err != nil {
		return nil, fmt.Errorf("failed to validate token for refresh: %w", err)
	}

	// Check if token is expired but within refresh window (7 days)
	if claims.ExpiresAt != nil && claims.ExpiresAt.Time.Before(time.Now()) {
		refreshWindow := time.Now().Add(-7 * 24 * time.Hour)
		if claims.ExpiresAt.Time.Before(refreshWindow) {
			return nil, errors.New("token is too old to refresh")
		}
	}

	// Generate new token with same claims
	return m.GenerateToken(claims.UserID, claims.Email, claims.AccountID, claims.Roles)
}

// generateTokenID generates a unique token ID
func generateTokenID() string {
	return fmt.Sprintf("%d-%s", time.Now().UnixNano(), randomString(8))
}

// randomString generates a random string of given length
func randomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[time.Now().UnixNano()%int64(len(charset))]
	}
	return string(b)
}