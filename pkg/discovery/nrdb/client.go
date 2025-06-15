package nrdb

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync"
	"time"
)

// Client implements the NRDBClient interface
type Client struct {
	config       NRDBConfig
	httpClient   *http.Client
	rateLimiter  *RateLimiter
	retryPolicy  *RetryPolicy
	
	// Metrics
	queryCount   int64
	errorCount   int64
	mu           sync.RWMutex
}

// NewClient creates a new NRDB client
func NewClient(config NRDBConfig) (*Client, error) {
	// Validate config
	if config.APIKey == "" {
		return nil, fmt.Errorf("API key is required")
	}
	if config.AccountID == "" {
		return nil, fmt.Errorf("account ID is required")
	}
	
	// Create HTTP client
	httpClient := &http.Client{
		Timeout: config.Timeout,
		Transport: &http.Transport{
			MaxIdleConns:        100,
			MaxIdleConnsPerHost: 10,
			IdleConnTimeout:     90 * time.Second,
		},
	}
	
	// Create rate limiter
	rateLimiter := NewRateLimiter(config.RateLimit, time.Minute)
	
	// Create retry policy
	retryPolicy := &RetryPolicy{
		MaxRetries:     config.MaxRetries,
		InitialBackoff: 100 * time.Millisecond,
		MaxBackoff:     10 * time.Second,
		Multiplier:     2,
	}
	
	return &Client{
		config:      config,
		httpClient:  httpClient,
		rateLimiter: rateLimiter,
		retryPolicy: retryPolicy,
	}, nil
}

// Query executes an NRQL query
func (c *Client) Query(ctx context.Context, nrql string) (*QueryResult, error) {
	return c.QueryWithOptions(ctx, nrql, QueryOptions{})
}

// QueryWithOptions executes an NRQL query with options
func (c *Client) QueryWithOptions(ctx context.Context, nrql string, opts QueryOptions) (*QueryResult, error) {
	// Apply rate limiting
	if err := c.rateLimiter.Wait(ctx); err != nil {
		return nil, fmt.Errorf("rate limit: %w", err)
	}
	
	// Track metrics
	c.mu.Lock()
	c.queryCount++
	c.mu.Unlock()
	
	// Build request
	req, err := c.buildRequest(ctx, nrql, opts)
	if err != nil {
		return nil, fmt.Errorf("building request: %w", err)
	}
	
	// Execute with retries
	var result *QueryResult
	err = c.retryPolicy.Execute(ctx, func() error {
		resp, err := c.httpClient.Do(req)
		if err != nil {
			return fmt.Errorf("executing request: %w", err)
		}
		defer resp.Body.Close()
		
		// Check status code
		if resp.StatusCode != http.StatusOK {
			body, _ := io.ReadAll(resp.Body)
			return fmt.Errorf("NRDB returned status %d: %s", resp.StatusCode, string(body))
		}
		
		// Parse response
		result, err = c.parseResponse(resp.Body)
		return err
	})
	
	if err != nil {
		c.mu.Lock()
		c.errorCount++
		c.mu.Unlock()
		return nil, err
	}
	
	return result, nil
}

// GetEventTypes retrieves all event types
func (c *Client) GetEventTypes(ctx context.Context, filter EventTypeFilter) ([]string, error) {
	// Build query
	query := "SHOW EVENT TYPES"
	if filter.MinRecordCount > 0 {
		query = fmt.Sprintf("SHOW EVENT TYPES WHERE eventCount() > %d", filter.MinRecordCount)
	}
	if !filter.Since.IsZero() {
		sinceMinutes := int(time.Since(filter.Since).Minutes())
		query += fmt.Sprintf(" SINCE %d minutes ago", sinceMinutes)
	}
	
	// Execute query
	result, err := c.Query(ctx, query)
	if err != nil {
		return nil, err
	}
	
	// Extract event types
	eventTypes := make([]string, 0, len(result.Results))
	for _, r := range result.Results {
		if eventType, ok := r["eventType"].(string); ok {
			// Apply pattern filter if specified
			if filter.Pattern == "" || matchesPattern(eventType, filter.Pattern) {
				eventTypes = append(eventTypes, eventType)
			}
		}
	}
	
	return eventTypes, nil
}

// GetAccountInfo retrieves account information
func (c *Client) GetAccountInfo(ctx context.Context) (*AccountInfo, error) {
	// This would typically use NerdGraph API instead of NRDB
	// For now, return basic info
	return &AccountInfo{
		AccountID:     c.config.AccountID,
		AccountName:   "Account " + c.config.AccountID,
		DataRetention: 30, // Default 30 days
		Limits: AccountLimits{
			MaxQueryDuration:   5 * time.Minute,
			MaxResultsPerQuery: 2000,
			RateLimitPerMinute: c.config.RateLimit,
		},
	}, nil
}

// buildRequest builds an HTTP request for NRDB
func (c *Client) buildRequest(ctx context.Context, nrql string, opts QueryOptions) (*http.Request, error) {
	// Build URL
	url := fmt.Sprintf("%s/v1/accounts/%s/query", c.config.BaseURL, c.config.AccountID)
	
	// Build request body
	body := map[string]interface{}{
		"nrql": nrql,
	}
	
	if opts.Timeout > 0 {
		body["timeout"] = int(opts.Timeout.Seconds())
	}
	
	jsonBody, err := json.Marshal(body)
	if err != nil {
		return nil, err
	}
	
	// Create request
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(jsonBody))
	if err != nil {
		return nil, err
	}
	
	// Set headers
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Api-Key", c.config.APIKey)
	req.Header.Set("Accept", "application/json")
	
	return req, nil
}

// parseResponse parses the NRDB response
func (c *Client) parseResponse(body io.Reader) (*QueryResult, error) {
	var response struct {
		Results         []map[string]interface{} `json:"results"`
		Metadata        QueryMetadata            `json:"metadata"`
		PerformanceInfo struct {
			InspectedCount int64 `json:"inspectedCount"`
			WallClockTime  int64 `json:"wallClockTime"`
		} `json:"performanceInfo"`
	}
	
	if err := json.NewDecoder(body).Decode(&response); err != nil {
		return nil, fmt.Errorf("decoding response: %w", err)
	}
	
	result := &QueryResult{
		Results:  response.Results,
		Metadata: response.Metadata,
	}
	
	// Add performance info if available
	if response.PerformanceInfo.WallClockTime > 0 {
		result.PerformanceInfo = &PerformanceInfo{
			QueryTime:      time.Duration(response.PerformanceInfo.WallClockTime) * time.Millisecond,
			RecordsScanned: response.PerformanceInfo.InspectedCount,
		}
	}
	
	return result, nil
}

// GetMetrics returns client metrics
func (c *Client) GetMetrics() map[string]int64 {
	c.mu.RLock()
	defer c.mu.RUnlock()
	
	return map[string]int64{
		"query_count": c.queryCount,
		"error_count": c.errorCount,
	}
}

// matchesPattern checks if a string matches a pattern (simple wildcard support)
func matchesPattern(s, pattern string) bool {
	// This is duplicated from helpers.go - in real implementation would be shared
	if pattern == "*" {
		return true
	}
	// Simple contains check for now
	return strings.Contains(s, strings.Trim(pattern, "*"))
}