package api

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/gorilla/mux"
	"github.com/rs/cors"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/auth"
	"github.com/newrelic/go-agent/v3/newrelic"
)

// Server represents the REST API server
type Server struct {
	router        *mux.Router
	httpServer    *http.Server
	handler       *Handler
	config        Config
	jwtManager    *auth.JWTManager
	apiKeyManager *auth.APIKeyManager
	nrApp         interface{} // *newrelic.Application, but using interface{} to avoid import
}

// Config holds API server configuration
type Config struct {
	Host            string
	Port            int
	ReadTimeout     time.Duration
	WriteTimeout    time.Duration
	MaxRequestSize  int64
	EnableCORS      bool
	EnableSwagger   bool
	RateLimitPerMin int
}

// SetNewRelicApp sets the New Relic application for APM instrumentation
func (s *Server) SetNewRelicApp(app interface{}) {
	s.nrApp = app
}

// NewServer creates a new REST API server
func NewServer(config Config, handler *Handler) *Server {
	// Initialize JWT manager
	jwtSecret := os.Getenv("JWT_SECRET")
	if jwtSecret == "" {
		jwtSecret = "default-jwt-secret-change-in-production"
	}
	jwtManager := auth.NewJWTManager(jwtSecret, "uds-api", 24*time.Hour)

	// Initialize API key manager
	apiKeySalt := os.Getenv("API_KEY_SALT")
	if apiKeySalt == "" {
		apiKeySalt = "default-api-key-salt-change-in-production"
	}
	apiKeyStore := auth.NewInMemoryAPIKeyStore()
	apiKeyManager := auth.NewAPIKeyManager(apiKeySalt, apiKeyStore)

	s := &Server{
		router:        mux.NewRouter(),
		handler:       handler,
		config:        config,
		jwtManager:    jwtManager,
		apiKeyManager: apiKeyManager,
	}

	// Setup routes
	s.setupRoutes()

	// Setup middleware
	s.setupMiddleware()

	return s
}

// Start starts the API server
func (s *Server) Start(ctx context.Context) error {
	addr := fmt.Sprintf("%s:%d", s.config.Host, s.config.Port)
	
	s.httpServer = &http.Server{
		Addr:         addr,
		Handler:      s.router,
		ReadTimeout:  s.config.ReadTimeout,
		WriteTimeout: s.config.WriteTimeout,
	}

	// Start server in goroutine
	errChan := make(chan error, 1)
	go func() {
		if err := s.httpServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			errChan <- err
		}
	}()

	// Wait for context cancellation or error
	select {
	case <-ctx.Done():
		return s.Stop(context.Background())
	case err := <-errChan:
		return err
	}
}

// Stop gracefully stops the API server
func (s *Server) Stop(ctx context.Context) error {
	if s.httpServer != nil {
		return s.httpServer.Shutdown(ctx)
	}
	return nil
}

// setupRoutes configures all API routes
func (s *Server) setupRoutes() {
	api := s.router.PathPrefix("/api/v1").Subrouter()

	// Public endpoints (no auth required)
	api.HandleFunc("/health", s.handler.GetHealth).Methods("GET")
	
	// Auth endpoints
	api.HandleFunc("/auth/login", s.handleLogin).Methods("POST")
	api.HandleFunc("/auth/refresh", s.handleRefreshToken).Methods("POST")
	api.HandleFunc("/auth/logout", s.handleLogout).Methods("POST")
	
	// API key management endpoints (require JWT auth)
	authAPI := api.PathPrefix("").Subrouter()
	authAPI.Use(auth.RequireAuth(s.jwtManager, nil))
	authAPI.HandleFunc("/apikeys", s.handleListAPIKeys).Methods("GET")
	authAPI.HandleFunc("/apikeys", s.handleCreateAPIKey).Methods("POST")
	authAPI.HandleFunc("/apikeys/{id}", s.handleRevokeAPIKey).Methods("DELETE")

	// Protected endpoints (require auth)
	protected := api.PathPrefix("").Subrouter()
	protected.Use(auth.RequireAuth(s.jwtManager, s.apiKeyManager))
	
	// Discovery endpoints
	protected.HandleFunc("/discovery/schemas", s.handler.ListSchemas).Methods("GET")
	protected.HandleFunc("/discovery/schemas/{eventType}", s.handler.GetSchemaProfile).Methods("GET")
	protected.HandleFunc("/discovery/relationships", s.handler.FindRelationships).Methods("POST")
	protected.HandleFunc("/discovery/quality/{eventType}", s.handler.AssessQuality).Methods("GET")

	// Pattern analysis endpoints
	protected.HandleFunc("/patterns/analyze", s.handler.AnalyzePatterns).Methods("POST")

	// Query generation endpoints
	protected.HandleFunc("/query/generate", s.handler.GenerateQuery).Methods("POST")

	// Dashboard endpoints
	protected.HandleFunc("/dashboard/create", s.handler.CreateDashboard).Methods("POST")

	// Swagger UI
	if s.config.EnableSwagger {
		s.router.PathPrefix("/swagger/").Handler(http.StripPrefix("/swagger/", http.FileServer(http.Dir("./swagger-ui/"))))
		s.router.HandleFunc("/openapi.yaml", s.serveOpenAPISpec).Methods("GET")
	}
}

// setupMiddleware configures middleware
func (s *Server) setupMiddleware() {
	// New Relic APM middleware (should be first)
	if app, ok := s.nrApp.(*newrelic.Application); ok && app != nil {
		s.router.Use(newRelicMiddleware(app))
		
		// Also set the app on the handler
		if s.handler != nil {
			s.handler.SetNewRelicApp(app)
		}
	}

	// Request logging
	s.router.Use(loggingMiddleware)

	// Request ID
	s.router.Use(requestIDMiddleware)

	// Recovery
	s.router.Use(recoveryMiddleware)

	// CORS
	if s.config.EnableCORS {
		c := cors.New(cors.Options{
			AllowedOrigins:   []string{"*"},
			AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
			AllowedHeaders:   []string{"*"},
			ExposedHeaders:   []string{"X-Request-ID"},
			AllowCredentials: true,
			MaxAge:           300,
		})
		s.router.Use(c.Handler)
	}

	// Rate limiting
	if s.config.RateLimitPerMin > 0 {
		s.router.Use(rateLimitMiddleware(s.config.RateLimitPerMin))
	}

	// Request size limiting
	if s.config.MaxRequestSize > 0 {
		s.router.Use(maxRequestSizeMiddleware(s.config.MaxRequestSize))
	}
}

// serveOpenAPISpec serves the OpenAPI specification
func (s *Server) serveOpenAPISpec(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/yaml")
	http.ServeFile(w, r, "./openapi.yaml")
}

// Helper functions are in helpers.go