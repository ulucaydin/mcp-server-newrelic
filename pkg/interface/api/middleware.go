package api

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/newrelic/go-agent/v3/newrelic"
	"golang.org/x/time/rate"
)

// Middleware functions for the REST API

// loggingMiddleware logs HTTP requests
func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		
		// Wrap response writer to capture status code
		wrapped := &responseWriter{ResponseWriter: w, statusCode: http.StatusOK}
		
		next.ServeHTTP(wrapped, r)
		
		// Log request details
		log.Printf(
			"[%s] %s %s %d %s %s",
			r.Method,
			r.RequestURI,
			r.RemoteAddr,
			wrapped.statusCode,
			time.Since(start),
			r.Header.Get("X-Request-ID"),
		)
	})
}

// requestIDMiddleware adds a unique request ID to each request
func requestIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}
		
		// Add to request context
		ctx := context.WithValue(r.Context(), "requestID", requestID)
		r = r.WithContext(ctx)
		
		// Add to response header
		w.Header().Set("X-Request-ID", requestID)
		
		next.ServeHTTP(w, r)
	})
}

// recoveryMiddleware recovers from panics
func recoveryMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if err := recover(); err != nil {
				log.Printf("Panic recovered: %v", err)
				writeError(w, http.StatusInternalServerError, "Internal server error", nil)
			}
		}()
		
		next.ServeHTTP(w, r)
	})
}

// rateLimitMiddleware implements rate limiting per IP
func rateLimitMiddleware(requestsPerMinute int) func(http.Handler) http.Handler {
	// Store rate limiters per IP
	limiters := &sync.Map{}
	
	// Cleanup old limiters periodically
	go func() {
		for range time.Tick(10 * time.Minute) {
			limiters.Range(func(key, value interface{}) bool {
				if limiter, ok := value.(*rateLimiter); ok {
					if time.Since(limiter.lastSeen) > 10*time.Minute {
						limiters.Delete(key)
					}
				}
				return true
			})
		}
	}()
	
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Extract client IP
			ip := getClientIP(r)
			
			// Get or create rate limiter
			value, _ := limiters.LoadOrStore(ip, &rateLimiter{
				limiter:  rate.NewLimiter(rate.Limit(requestsPerMinute)/60, 10),
				lastSeen: time.Now(),
			})
			
			limiter := value.(*rateLimiter)
			limiter.lastSeen = time.Now()
			
			// Check rate limit
			if !limiter.limiter.Allow() {
				writeError(w, http.StatusTooManyRequests, "Rate limit exceeded", map[string]interface{}{
					"limit": fmt.Sprintf("%d requests per minute", requestsPerMinute),
				})
				return
			}
			
			next.ServeHTTP(w, r)
		})
	}
}

// maxRequestSizeMiddleware limits request body size
func maxRequestSizeMiddleware(maxSize int64) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			r.Body = http.MaxBytesReader(w, r.Body, maxSize)
			next.ServeHTTP(w, r)
		})
	}
}

// Helper types

type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

type rateLimiter struct {
	limiter  *rate.Limiter
	lastSeen time.Time
}

// getClientIP extracts client IP from request
func getClientIP(r *http.Request) string {
	// Check X-Forwarded-For header
	if xff := r.Header.Get("X-Forwarded-For"); xff != "" {
		parts := strings.Split(xff, ",")
		return strings.TrimSpace(parts[0])
	}
	
	// Check X-Real-IP header
	if xri := r.Header.Get("X-Real-IP"); xri != "" {
		return xri
	}
	
	// Fall back to remote address
	return strings.Split(r.RemoteAddr, ":")[0]
}

// newRelicMiddleware adds New Relic APM instrumentation to HTTP handlers
func newRelicMiddleware(app *newrelic.Application) func(http.Handler) http.Handler {
	if app == nil {
		// Return a no-op middleware if APM is not available
		return func(next http.Handler) http.Handler {
			return next
		}
	}
	
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			// Start transaction with the request pattern as the name
			txn := app.StartTransaction(r.Method + " " + r.URL.Path)
			defer txn.End()
			
			// Add transaction to request context
			r = newrelic.RequestWithTransactionContext(r, txn)
			
			// Set transaction attributes
			txn.AddAttribute("http.method", r.Method)
			txn.AddAttribute("http.url", r.URL.String())
			txn.AddAttribute("http.host", r.Host)
			txn.AddAttribute("http.scheme", r.URL.Scheme)
			
			// Add request ID if available
			if requestID := r.Header.Get("X-Request-ID"); requestID != "" {
				txn.AddAttribute("request.id", requestID)
			}
			
			// Wrap response writer to capture status code
			wrapped := &nrResponseWriter{
				ResponseWriter: txn.SetWebResponse(w),
				txn:           txn,
			}
			
			// Serve the request
			next.ServeHTTP(wrapped, r)
			
			// Record response status
			if wrapped.statusCode != 0 {
				txn.AddAttribute("http.statusCode", wrapped.statusCode)
			}
		})
	}
}

// nrResponseWriter wraps http.ResponseWriter for New Relic
type nrResponseWriter struct {
	http.ResponseWriter
	txn        *newrelic.Transaction
	statusCode int
}

func (w *nrResponseWriter) WriteHeader(code int) {
	w.statusCode = code
	w.ResponseWriter.WriteHeader(code)
}