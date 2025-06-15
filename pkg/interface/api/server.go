package api

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/gorilla/mux"
	"github.com/rs/cors"
)

// Server represents the REST API server
type Server struct {
	router     *mux.Router
	httpServer *http.Server
	handler    *Handler
	config     Config
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

// NewServer creates a new REST API server
func NewServer(config Config, handler *Handler) *Server {
	s := &Server{
		router:  mux.NewRouter(),
		handler: handler,
		config:  config,
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

	// Health endpoints
	api.HandleFunc("/health", s.handler.GetHealth).Methods("GET")

	// Discovery endpoints
	api.HandleFunc("/discovery/schemas", s.handler.ListSchemas).Methods("GET")
	api.HandleFunc("/discovery/schemas/{eventType}", s.handler.GetSchemaProfile).Methods("GET")
	api.HandleFunc("/discovery/relationships", s.handler.FindRelationships).Methods("POST")
	api.HandleFunc("/discovery/quality/{eventType}", s.handler.AssessQuality).Methods("GET")

	// Pattern analysis endpoints
	api.HandleFunc("/patterns/analyze", s.handler.AnalyzePatterns).Methods("POST")

	// Query generation endpoints
	api.HandleFunc("/query/generate", s.handler.GenerateQuery).Methods("POST")

	// Dashboard endpoints
	api.HandleFunc("/dashboard/create", s.handler.CreateDashboard).Methods("POST")

	// Swagger UI
	if s.config.EnableSwagger {
		s.router.PathPrefix("/swagger/").Handler(http.StripPrefix("/swagger/", http.FileServer(http.Dir("./swagger-ui/"))))
		s.router.HandleFunc("/openapi.yaml", s.serveOpenAPISpec).Methods("GET")
	}
}

// setupMiddleware configures middleware
func (s *Server) setupMiddleware() {
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

// Helper functions for JSON responses
func writeJSON(w http.ResponseWriter, status int, data interface{}) error {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	return json.NewEncoder(w).Encode(data)
}

func writeError(w http.ResponseWriter, status int, err string, details interface{}) {
	writeJSON(w, status, map[string]interface{}{
		"error":   err,
		"message": err,
		"details": details,
	})
}