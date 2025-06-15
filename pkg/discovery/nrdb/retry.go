package nrdb

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"time"
)

// RetryConfig holds configuration for retry logic
type RetryConfig struct {
	// MaxAttempts is the maximum number of retry attempts
	MaxAttempts int
	// InitialInterval is the initial retry interval
	InitialInterval time.Duration
	// MaxInterval is the maximum retry interval
	MaxInterval time.Duration
	// Multiplier is the exponential backoff multiplier
	Multiplier float64
	// RandomizationFactor adds jitter to prevent thundering herd
	RandomizationFactor float64
	// RetryableErrors defines which errors should trigger a retry
	RetryableErrors func(error) bool
}

// DefaultRetryConfig returns sensible retry defaults
func DefaultRetryConfig() RetryConfig {
	return RetryConfig{
		MaxAttempts:         3,
		InitialInterval:     100 * time.Millisecond,
		MaxInterval:         10 * time.Second,
		Multiplier:          2.0,
		RandomizationFactor: 0.1,
		RetryableErrors:     defaultRetryableErrors,
	}
}

// defaultRetryableErrors determines if an error is retryable
func defaultRetryableErrors(err error) bool {
	if err == nil {
		return false
	}
	
	// Don't retry circuit breaker open errors
	if errors.Is(err, ErrCircuitOpen) {
		return false
	}
	
	errStr := err.Error()
	
	// Retry on transient errors
	transientErrors := []string{
		"timeout",
		"connection",
		"network",
		"temporary",
		"unavailable",
		"502",
		"503",
		"504",
		"429", // Rate limited - retry with backoff
	}
	
	for _, pattern := range transientErrors {
		if contains(errStr, pattern) {
			return true
		}
	}
	
	// Don't retry on permanent errors
	permanentErrors := []string{
		"unauthorized",
		"401",
		"403",
		"invalid",
		"validation",
		"not found",
		"404",
	}
	
	for _, pattern := range permanentErrors {
		if contains(errStr, pattern) {
			return false
		}
	}
	
	// Default to not retrying unknown errors
	return false
}

// ClientWithRetry wraps an NRDB client with retry logic
type ClientWithRetry struct {
	client NRDBClient
	config RetryConfig
}

// NewClientWithRetry creates a new client with retry logic
func NewClientWithRetry(client NRDBClient, config RetryConfig) NRDBClient {
	return &ClientWithRetry{
		client: client,
		config: config,
	}
}

// Query executes a query with retry logic
func (c *ClientWithRetry) Query(ctx context.Context, nrql string) (*QueryResult, error) {
	return retry(ctx, c.config, func() (*QueryResult, error) {
		return c.client.Query(ctx, nrql)
	})
}

// QueryWithOptions executes a query with options and retry logic
func (c *ClientWithRetry) QueryWithOptions(ctx context.Context, nrql string, opts QueryOptions) (*QueryResult, error) {
	return retry(ctx, c.config, func() (*QueryResult, error) {
		return c.client.QueryWithOptions(ctx, nrql, opts)
	})
}

// GetEventTypes gets event types with retry logic
func (c *ClientWithRetry) GetEventTypes(ctx context.Context, filter EventTypeFilter) ([]string, error) {
	return retryTyped(ctx, c.config, func() ([]string, error) {
		return c.client.GetEventTypes(ctx, filter)
	})
}

// GetAccountInfo gets account info with retry logic
func (c *ClientWithRetry) GetAccountInfo(ctx context.Context) (*AccountInfo, error) {
	return retryTyped(ctx, c.config, func() (*AccountInfo, error) {
		return c.client.GetAccountInfo(ctx)
	})
}

// retry implements the generic retry logic
func retry[T any](ctx context.Context, config RetryConfig, fn func() (T, error)) (T, error) {
	var result T
	var lastErr error
	
	for attempt := 0; attempt <= config.MaxAttempts; attempt++ {
		// Check context cancellation
		if err := ctx.Err(); err != nil {
			return result, fmt.Errorf("context cancelled: %w", err)
		}
		
		// Execute the function
		result, lastErr = fn()
		
		// Success!
		if lastErr == nil {
			return result, nil
		}
		
		// Check if we should retry
		if attempt == config.MaxAttempts || !config.RetryableErrors(lastErr) {
			break
		}
		
		// Calculate backoff duration
		backoff := calculateBackoff(attempt, config)
		
		// Wait with context cancellation support
		select {
		case <-ctx.Done():
			return result, fmt.Errorf("context cancelled during retry: %w", ctx.Err())
		case <-time.After(backoff):
			// Continue to next attempt
		}
	}
	
	// All attempts failed
	return result, fmt.Errorf("failed after %d attempts: %w", config.MaxAttempts+1, lastErr)
}

// retryTyped is a typed version of retry for common types
func retryTyped[T any](ctx context.Context, config RetryConfig, fn func() (T, error)) (T, error) {
	return retry(ctx, config, fn)
}

// calculateBackoff calculates the backoff duration for a given attempt
func calculateBackoff(attempt int, config RetryConfig) time.Duration {
	// Calculate base interval with exponential backoff
	baseInterval := config.InitialInterval
	for i := 0; i < attempt; i++ {
		baseInterval = time.Duration(float64(baseInterval) * config.Multiplier)
		if baseInterval > config.MaxInterval {
			baseInterval = config.MaxInterval
			break
		}
	}
	
	// Add jitter to prevent thundering herd
	jitter := config.RandomizationFactor * float64(baseInterval)
	jitterRange := 2 * jitter
	actualJitter := (rand.Float64() * jitterRange) - jitter
	
	// Calculate final duration
	duration := float64(baseInterval) + actualJitter
	
	// Ensure we don't go negative
	if duration < 0 {
		duration = 0
	}
	
	return time.Duration(duration)
}

// RetryMetrics tracks retry statistics
type RetryMetrics struct {
	TotalAttempts   int64
	SuccessfulCalls int64
	FailedCalls     int64
	TotalRetries    int64
}

// ClientWithRetryAndMetrics wraps a client with retry logic and metrics
type ClientWithRetryAndMetrics struct {
	*ClientWithRetry
	metrics *RetryMetrics
}

// NewClientWithRetryAndMetrics creates a client with retry and metrics
func NewClientWithRetryAndMetrics(client NRDBClient, config RetryConfig) *ClientWithRetryAndMetrics {
	return &ClientWithRetryAndMetrics{
		ClientWithRetry: &ClientWithRetry{
			client: client,
			config: config,
		},
		metrics: &RetryMetrics{},
	}
}

// GetMetrics returns the current retry metrics
func (c *ClientWithRetryAndMetrics) GetMetrics() RetryMetrics {
	return *c.metrics
}

// Query with metrics tracking
func (c *ClientWithRetryAndMetrics) Query(ctx context.Context, nrql string) (*QueryResult, error) {
	attempts := 0
	result, err := retryWithMetrics(ctx, c.config, func() (*QueryResult, error) {
		attempts++
		return c.client.Query(ctx, nrql)
	}, &attempts)
	
	// Update metrics
	c.metrics.TotalAttempts += int64(attempts)
	if err == nil {
		c.metrics.SuccessfulCalls++
	} else {
		c.metrics.FailedCalls++
	}
	if attempts > 1 {
		c.metrics.TotalRetries += int64(attempts - 1)
	}
	
	return result, err
}

// retryWithMetrics is like retry but tracks attempt count
func retryWithMetrics[T any](ctx context.Context, config RetryConfig, fn func() (T, error), attempts *int) (T, error) {
	var result T
	var lastErr error
	
	for attempt := 0; attempt <= config.MaxAttempts; attempt++ {
		// Check context cancellation
		if err := ctx.Err(); err != nil {
			return result, fmt.Errorf("context cancelled: %w", err)
		}
		
		// Execute the function
		result, lastErr = fn()
		
		// Success!
		if lastErr == nil {
			return result, nil
		}
		
		// Check if we should retry
		if attempt == config.MaxAttempts || !config.RetryableErrors(lastErr) {
			break
		}
		
		// Calculate backoff duration
		backoff := calculateBackoff(attempt, config)
		
		// Wait with context cancellation support
		select {
		case <-ctx.Done():
			return result, fmt.Errorf("context cancelled during retry: %w", ctx.Err())
		case <-time.After(backoff):
			// Continue to next attempt
		}
	}
	
	// All attempts failed
	return result, fmt.Errorf("failed after %d attempts: %w", config.MaxAttempts+1, lastErr)
}

// ExponentialBackoff is a simple exponential backoff calculator
type ExponentialBackoff struct {
	Initial     time.Duration
	Max         time.Duration
	Multiplier  float64
	Jitter      bool
	currentWait time.Duration
}

// NewExponentialBackoff creates a new exponential backoff
func NewExponentialBackoff(initial, max time.Duration) *ExponentialBackoff {
	return &ExponentialBackoff{
		Initial:     initial,
		Max:         max,
		Multiplier:  2.0,
		Jitter:      true,
		currentWait: initial,
	}
}

// Next returns the next backoff duration
func (b *ExponentialBackoff) Next() time.Duration {
	defer func() {
		// Update for next call
		b.currentWait = time.Duration(float64(b.currentWait) * b.Multiplier)
		if b.currentWait > b.Max {
			b.currentWait = b.Max
		}
	}()
	
	wait := b.currentWait
	if b.Jitter {
		// Add up to 10% jitter
		jitter := time.Duration(rand.Float64() * float64(wait) * 0.1)
		wait = wait + jitter
	}
	
	return wait
}

// Reset resets the backoff to initial state
func (b *ExponentialBackoff) Reset() {
	b.currentWait = b.Initial
}

// LinearBackoff provides linear backoff with optional jitter
type LinearBackoff struct {
	Interval time.Duration
	Jitter   bool
}

// Next returns the next backoff duration
func (b *LinearBackoff) Next() time.Duration {
	wait := b.Interval
	if b.Jitter {
		// Add up to 10% jitter
		jitter := time.Duration(rand.Float64() * float64(wait) * 0.1)
		wait = wait + jitter
	}
	return wait
}

// FibonacciBackoff provides Fibonacci sequence based backoff
type FibonacciBackoff struct {
	Unit     time.Duration
	Max      time.Duration
	current  int
	previous int
}

// NewFibonacciBackoff creates a new Fibonacci backoff
func NewFibonacciBackoff(unit, max time.Duration) *FibonacciBackoff {
	return &FibonacciBackoff{
		Unit:     unit,
		Max:      max,
		current:  1,
		previous: 0,
	}
}

// Next returns the next backoff duration
func (b *FibonacciBackoff) Next() time.Duration {
	next := b.current + b.previous
	b.previous = b.current
	b.current = next
	
	wait := time.Duration(b.current) * b.Unit
	if wait > b.Max {
		wait = b.Max
	}
	
	return wait
}

// Reset resets the sequence
func (b *FibonacciBackoff) Reset() {
	b.current = 1
	b.previous = 0
}