package nrdb

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// RateLimiter implements token bucket rate limiting
type RateLimiter struct {
	rate       int           // requests per period
	period     time.Duration // time period
	tokens     int           // current tokens
	maxTokens  int           // max tokens (burst capacity)
	lastRefill time.Time
	mu         sync.Mutex
	waiters    []chan struct{}
}

// NewRateLimiter creates a new rate limiter
func NewRateLimiter(rate int, period time.Duration) *RateLimiter {
	return &RateLimiter{
		rate:       rate,
		period:     period,
		tokens:     rate,
		maxTokens:  rate,
		lastRefill: time.Now(),
	}
}

// Wait blocks until a token is available
func (r *RateLimiter) Wait(ctx context.Context) error {
	return r.WaitN(ctx, 1)
}

// WaitN blocks until n tokens are available
func (r *RateLimiter) WaitN(ctx context.Context, n int) error {
	if n > r.maxTokens {
		return fmt.Errorf("requested %d tokens exceeds maximum %d", n, r.maxTokens)
	}
	
	// Fast path - try to get tokens immediately
	if r.tryAcquire(n) {
		return nil
	}
	
	// Slow path - wait for tokens
	waiter := make(chan struct{})
	r.mu.Lock()
	r.waiters = append(r.waiters, waiter)
	r.mu.Unlock()
	
	// Create ticker for periodic checks
	ticker := time.NewTicker(10 * time.Millisecond)
	defer ticker.Stop()
	
	for {
		select {
		case <-ctx.Done():
			r.removeWaiter(waiter)
			return ctx.Err()
			
		case <-ticker.C:
			if r.tryAcquire(n) {
				r.removeWaiter(waiter)
				close(waiter)
				return nil
			}
			
		case <-waiter:
			// Another goroutine signaled us
			if r.tryAcquire(n) {
				return nil
			}
		}
	}
}

// tryAcquire attempts to acquire n tokens
func (r *RateLimiter) tryAcquire(n int) bool {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	// Refill tokens based on elapsed time
	r.refill()
	
	// Check if we have enough tokens
	if r.tokens >= n {
		r.tokens -= n
		return true
	}
	
	return false
}

// refill adds tokens based on elapsed time
func (r *RateLimiter) refill() {
	now := time.Now()
	elapsed := now.Sub(r.lastRefill)
	
	// Calculate new tokens
	newTokens := int(float64(r.rate) * (elapsed.Seconds() / r.period.Seconds()))
	if newTokens > 0 {
		r.tokens = min(r.tokens+newTokens, r.maxTokens)
		r.lastRefill = now
		
		// Notify waiters
		for _, waiter := range r.waiters {
			select {
			case waiter <- struct{}{}:
			default:
			}
		}
	}
}

// removeWaiter removes a waiter from the list
func (r *RateLimiter) removeWaiter(waiter chan struct{}) {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	for i, w := range r.waiters {
		if w == waiter {
			r.waiters = append(r.waiters[:i], r.waiters[i+1:]...)
			break
		}
	}
}

// Available returns the number of available tokens
func (r *RateLimiter) Available() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	
	r.refill()
	return r.tokens
}

// RetryPolicy implements exponential backoff retry logic
type RetryPolicy struct {
	MaxRetries     int
	InitialBackoff time.Duration
	MaxBackoff     time.Duration
	Multiplier     float64
}

// Execute executes a function with retries
func (p *RetryPolicy) Execute(ctx context.Context, fn func() error) error {
	var lastErr error
	backoff := p.InitialBackoff
	
	for attempt := 0; attempt <= p.MaxRetries; attempt++ {
		// Execute function
		err := fn()
		if err == nil {
			return nil
		}
		
		lastErr = err
		
		// Check if error is retryable
		if !isRetryable(err) {
			return err
		}
		
		// Don't retry if we've exhausted attempts
		if attempt == p.MaxRetries {
			break
		}
		
		// Wait with backoff
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-time.After(backoff):
			// Continue to next attempt
		}
		
		// Increase backoff
		backoff = time.Duration(float64(backoff) * p.Multiplier)
		if backoff > p.MaxBackoff {
			backoff = p.MaxBackoff
		}
	}
	
	return fmt.Errorf("failed after %d attempts: %w", p.MaxRetries+1, lastErr)
}

// isRetryable determines if an error should be retried
func isRetryable(err error) bool {
	// TODO: Implement proper error classification
	// For now, retry on any error except context cancellation
	return err != context.Canceled && err != context.DeadlineExceeded
}

// CircuitBreaker implements circuit breaker pattern
type CircuitBreaker struct {
	name            string
	maxFailures     int
	resetTimeout    time.Duration
	
	mu              sync.Mutex
	failures        int
	lastFailureTime time.Time
	state           string // "closed", "open", "half-open"
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(name string, maxFailures int, resetTimeout time.Duration) *CircuitBreaker {
	return &CircuitBreaker{
		name:         name,
		maxFailures:  maxFailures,
		resetTimeout: resetTimeout,
		state:        "closed",
	}
}

// Execute executes a function with circuit breaker protection
func (cb *CircuitBreaker) Execute(fn func() error) error {
	cb.mu.Lock()
	
	// Check state
	switch cb.state {
	case "open":
		// Check if we should transition to half-open
		if time.Since(cb.lastFailureTime) > cb.resetTimeout {
			cb.state = "half-open"
			cb.failures = 0
		} else {
			cb.mu.Unlock()
			return fmt.Errorf("circuit breaker %s is open", cb.name)
		}
		
	case "half-open":
		// Allow one request through
		
	case "closed":
		// Normal operation
	}
	
	cb.mu.Unlock()
	
	// Execute function
	err := fn()
	
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	if err != nil {
		cb.failures++
		cb.lastFailureTime = time.Now()
		
		if cb.failures >= cb.maxFailures {
			cb.state = "open"
			return fmt.Errorf("circuit breaker %s opened after %d failures: %w", cb.name, cb.failures, err)
		}
		
		return err
	}
	
	// Success - reset failures
	if cb.state == "half-open" {
		cb.state = "closed"
	}
	cb.failures = 0
	
	return nil
}

// min returns the minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}