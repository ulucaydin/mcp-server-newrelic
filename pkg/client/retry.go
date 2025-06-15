package client

import (
	"bytes"
	"fmt"
	"io"
	"math"
	"math/rand"
	"net/http"
	"time"
)

// RetryClient wraps an http.Client with retry logic
type RetryClient struct {
	client    *http.Client
	maxRetries int
	waitTime  time.Duration
}

// NewRetryClient creates a new HTTP client with retry logic
func NewRetryClient(client *http.Client, maxRetries int, waitTime time.Duration) *http.Client {
	if client == nil {
		client = &http.Client{}
	}
	
	
	// Wrap the transport
	transport := client.Transport
	if transport == nil {
		transport = http.DefaultTransport
	}
	
	client.Transport = &retryTransport{
		transport:  transport,
		maxRetries: maxRetries,
		waitTime:   waitTime,
	}
	
	return client
}

// retryTransport implements http.RoundTripper with retry logic
type retryTransport struct {
	transport  http.RoundTripper
	maxRetries int
	waitTime   time.Duration
}

func (rt *retryTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	var resp *http.Response
	var err error
	
	// Clone request body for retries
	var bodyBytes []byte
	if req.Body != nil {
		bodyBytes, err = io.ReadAll(req.Body)
		if err != nil {
			return nil, fmt.Errorf("failed to read request body: %w", err)
		}
		req.Body.Close()
	}
	
	for attempt := 0; attempt <= rt.maxRetries; attempt++ {
		// Clone request for each attempt
		clonedReq := req.Clone(req.Context())
		if bodyBytes != nil {
			clonedReq.Body = io.NopCloser(bytes.NewReader(bodyBytes))
		}
		
		resp, err = rt.transport.RoundTrip(clonedReq)
		
		// Check if we should retry
		if !shouldRetry(resp, err) {
			return resp, err
		}
		
		// Don't retry if context is cancelled
		if req.Context().Err() != nil {
			return resp, err
		}
		
		// Calculate backoff with jitter
		backoff := rt.calculateBackoff(attempt)
		
		// Wait before retry
		timer := time.NewTimer(backoff)
		select {
		case <-timer.C:
			// Continue with retry
		case <-req.Context().Done():
			timer.Stop()
			return nil, req.Context().Err()
		}
		
		// Close response body before retry
		if resp != nil && resp.Body != nil {
			io.Copy(io.Discard, resp.Body)
			resp.Body.Close()
		}
	}
	
	return resp, err
}

// shouldRetry determines if a request should be retried
func shouldRetry(resp *http.Response, err error) bool {
	// Retry on network errors
	if err != nil {
		return true
	}
	
	// Retry on specific status codes
	if resp != nil {
		switch resp.StatusCode {
		case http.StatusTooManyRequests,
			http.StatusRequestTimeout,
			http.StatusBadGateway,
			http.StatusServiceUnavailable,
			http.StatusGatewayTimeout:
			return true
		}
	}
	
	return false
}

// calculateBackoff calculates the backoff duration with exponential backoff and jitter
func (rt *retryTransport) calculateBackoff(attempt int) time.Duration {
	// Exponential backoff: wait * 2^attempt
	backoff := rt.waitTime * time.Duration(math.Pow(2, float64(attempt)))
	
	// Add jitter (±25%)
	jitter := time.Duration(rand.Float64() * float64(backoff) * 0.5)
	if rand.Intn(2) == 0 {
		backoff += jitter
	} else {
		backoff -= jitter
	}
	
	// Cap at 30 seconds
	maxBackoff := 30 * time.Second
	if backoff > maxBackoff {
		backoff = maxBackoff
	}
	
	return backoff
}

// RetryPolicy defines a custom retry policy
type RetryPolicy struct {
	MaxRetries    int
	WaitTime      time.Duration
	MaxWaitTime   time.Duration
	RetryableFunc func(*http.Response, error) bool
}

// DefaultRetryPolicy returns the default retry policy
func DefaultRetryPolicy() *RetryPolicy {
	return &RetryPolicy{
		MaxRetries:    3,
		WaitTime:      1 * time.Second,
		MaxWaitTime:   30 * time.Second,
		RetryableFunc: shouldRetry,
	}
}