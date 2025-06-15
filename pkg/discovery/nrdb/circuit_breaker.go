package nrdb

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// CircuitBreakerState represents the state of the circuit breaker
type CircuitBreakerState int

const (
	// StateClosed allows requests to pass through
	StateClosed CircuitBreakerState = iota
	// StateOpen blocks all requests
	StateOpen
	// StateHalfOpen allows limited requests to test recovery
	StateHalfOpen
)

func (s CircuitBreakerState) String() string {
	switch s {
	case StateClosed:
		return "closed"
	case StateOpen:
		return "open"
	case StateHalfOpen:
		return "half-open"
	default:
		return "unknown"
	}
}

// CircuitBreakerConfig holds configuration for the circuit breaker
type CircuitBreakerConfig struct {
	// FailureThreshold is the number of failures before opening the circuit
	FailureThreshold int
	// SuccessThreshold is the number of successes in half-open before closing
	SuccessThreshold int
	// OpenDuration is how long to stay in open state
	OpenDuration time.Duration
	// HalfOpenRequests is the number of requests allowed in half-open state
	HalfOpenRequests int
}

// DefaultCircuitBreakerConfig returns sensible defaults
func DefaultCircuitBreakerConfig() CircuitBreakerConfig {
	return CircuitBreakerConfig{
		FailureThreshold: 5,
		SuccessThreshold: 2,
		OpenDuration:     30 * time.Second,
		HalfOpenRequests: 3,
	}
}

// CircuitBreaker implements the circuit breaker pattern
type CircuitBreaker struct {
	config CircuitBreakerConfig
	
	mu              sync.RWMutex
	state           CircuitBreakerState
	failures        int
	successes       int
	lastFailureTime time.Time
	openUntil       time.Time
	halfOpenCount   int
}

// NewCircuitBreaker creates a new circuit breaker
func NewCircuitBreaker(config CircuitBreakerConfig) *CircuitBreaker {
	return &CircuitBreaker{
		config: config,
		state:  StateClosed,
	}
}

// State returns the current state of the circuit breaker
func (cb *CircuitBreaker) State() CircuitBreakerState {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.state
}

// Failures returns the current failure count
func (cb *CircuitBreaker) Failures() int {
	cb.mu.RLock()
	defer cb.mu.RUnlock()
	return cb.failures
}

// Allow checks if a request should be allowed
func (cb *CircuitBreaker) Allow() bool {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	now := time.Now()

	switch cb.state {
	case StateClosed:
		return true
		
	case StateOpen:
		if now.After(cb.openUntil) {
			// Transition to half-open
			cb.state = StateHalfOpen
			cb.halfOpenCount = 0
			cb.successes = 0
			return true
		}
		return false
		
	case StateHalfOpen:
		if cb.halfOpenCount < cb.config.HalfOpenRequests {
			cb.halfOpenCount++
			return true
		}
		return false
		
	default:
		return false
	}
}

// RecordSuccess records a successful request
func (cb *CircuitBreaker) RecordSuccess() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	switch cb.state {
	case StateClosed:
		// Reset failure count on success
		cb.failures = 0
		
	case StateHalfOpen:
		cb.successes++
		if cb.successes >= cb.config.SuccessThreshold {
			// Transition to closed
			cb.state = StateClosed
			cb.failures = 0
			cb.successes = 0
		}
	}
}

// RecordFailure records a failed request
func (cb *CircuitBreaker) RecordFailure() {
	cb.mu.Lock()
	defer cb.mu.Unlock()

	now := time.Now()
	cb.lastFailureTime = now

	switch cb.state {
	case StateClosed:
		cb.failures++
		if cb.failures >= cb.config.FailureThreshold {
			// Transition to open
			cb.state = StateOpen
			cb.openUntil = now.Add(cb.config.OpenDuration)
		}
		
	case StateHalfOpen:
		// Any failure in half-open goes back to open
		cb.state = StateOpen
		cb.openUntil = now.Add(cb.config.OpenDuration)
		cb.failures = cb.config.FailureThreshold // Keep it at threshold
	}
}

// Reset resets the circuit breaker to closed state
func (cb *CircuitBreaker) Reset() {
	cb.mu.Lock()
	defer cb.mu.Unlock()
	
	cb.state = StateClosed
	cb.failures = 0
	cb.successes = 0
	cb.halfOpenCount = 0
}

// ClientWithCircuitBreaker wraps an NRDB client with circuit breaker protection
type ClientWithCircuitBreaker struct {
	client  discovery.NRDBClient
	breaker *CircuitBreaker
}

// NewClientWithCircuitBreaker creates a new client with circuit breaker
func NewClientWithCircuitBreaker(client discovery.NRDBClient, config CircuitBreakerConfig) discovery.NRDBClient {
	return &ClientWithCircuitBreaker{
		client:  client,
		breaker: NewCircuitBreaker(config),
	}
}

// ErrCircuitOpen is returned when the circuit breaker is open
var ErrCircuitOpen = errors.New("circuit breaker is open")

// Query executes a query with circuit breaker protection
func (c *ClientWithCircuitBreaker) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	if !c.breaker.Allow() {
		return nil, fmt.Errorf("%w: too many failures", ErrCircuitOpen)
	}

	result, err := c.client.Query(ctx, nrql)
	if err != nil {
		c.breaker.RecordFailure()
		return nil, err
	}

	c.breaker.RecordSuccess()
	return result, nil
}

// QueryWithOptions executes a query with options and circuit breaker protection
func (c *ClientWithCircuitBreaker) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	if !c.breaker.Allow() {
		return nil, fmt.Errorf("%w: too many failures", ErrCircuitOpen)
	}

	result, err := c.client.QueryWithOptions(ctx, nrql, opts)
	if err != nil {
		c.breaker.RecordFailure()
		return nil, err
	}

	c.breaker.RecordSuccess()
	return result, nil
}

// GetEventTypes gets event types with circuit breaker protection
func (c *ClientWithCircuitBreaker) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	if !c.breaker.Allow() {
		return nil, fmt.Errorf("%w: too many failures", ErrCircuitOpen)
	}

	types, err := c.client.GetEventTypes(ctx, filter)
	if err != nil {
		c.breaker.RecordFailure()
		return nil, err
	}

	c.breaker.RecordSuccess()
	return types, nil
}

// GetAccounts gets accounts with circuit breaker protection
func (c *ClientWithCircuitBreaker) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	if !c.breaker.Allow() {
		return nil, fmt.Errorf("%w: too many failures", ErrCircuitOpen)
	}

	accounts, err := c.client.GetAccounts(ctx)
	if err != nil {
		c.breaker.RecordFailure()
		return nil, err
	}

	c.breaker.RecordSuccess()
	return accounts, nil
}

// GetState returns the current circuit breaker state (for monitoring)
func (c *ClientWithCircuitBreaker) GetState() CircuitBreakerState {
	return c.breaker.State()
}

// GetFailures returns the current failure count (for monitoring)
func (c *ClientWithCircuitBreaker) GetFailures() int {
	return c.breaker.Failures()
}

// Reset resets the circuit breaker (for admin operations)
func (c *ClientWithCircuitBreaker) Reset() {
	c.breaker.Reset()
}