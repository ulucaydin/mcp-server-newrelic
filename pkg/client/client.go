package client

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

)

// Client is the main UDS API client
type Client struct {
	baseURL    string
	httpClient *http.Client
	apiKey     string
	userAgent  string
	
	// Service clients
	Discovery *DiscoveryService
	Patterns  *PatternsService
	Query     *QueryService
	Dashboard *DashboardService
}

// Config holds client configuration
type Config struct {
	BaseURL    string
	APIKey     string
	HTTPClient *http.Client
	UserAgent  string
	Timeout    time.Duration
	RetryMax   int
	RetryWait  time.Duration
}

// NewClient creates a new UDS API client
func NewClient(config Config) (*Client, error) {
	if config.BaseURL == "" {
		config.BaseURL = "http://localhost:8080/api/v1"
	}
	
	if config.HTTPClient == nil {
		config.HTTPClient = &http.Client{
			Timeout: config.Timeout,
		}
	}
	
	if config.UserAgent == "" {
		config.UserAgent = "uds-go-client/1.0.0"
	}
	
	// Wrap HTTP client with retry logic
	if config.RetryMax > 0 {
		config.HTTPClient = NewRetryClient(config.HTTPClient, config.RetryMax, config.RetryWait)
	}
	
	c := &Client{
		baseURL:    config.BaseURL,
		httpClient: config.HTTPClient,
		apiKey:     config.APIKey,
		userAgent:  config.UserAgent,
	}
	
	// Initialize service clients
	c.Discovery = &DiscoveryService{client: c}
	c.Patterns = &PatternsService{client: c}
	c.Query = &QueryService{client: c}
	c.Dashboard = &DashboardService{client: c}
	
	return c, nil
}

// request is the internal method for making HTTP requests
func (c *Client) request(ctx context.Context, method, path string, params url.Values, body interface{}) (*http.Response, error) {
	// Build URL
	u, err := url.Parse(c.baseURL + path)
	if err != nil {
		return nil, fmt.Errorf("invalid URL: %w", err)
	}
	
	if params != nil {
		u.RawQuery = params.Encode()
	}
	
	// Build request body
	var bodyReader io.Reader
	if body != nil {
		jsonBody, err := json.Marshal(body)
		if err != nil {
			return nil, fmt.Errorf("failed to marshal request body: %w", err)
		}
		bodyReader = bytes.NewReader(jsonBody)
	}
	
	// Create request
	req, err := http.NewRequestWithContext(ctx, method, u.String(), bodyReader)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	
	// Set headers
	req.Header.Set("User-Agent", c.userAgent)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}
	
	// Execute request
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("request failed: %w", err)
	}
	
	// Check status code
	if resp.StatusCode >= 400 {
		defer resp.Body.Close()
		var apiErr APIError
		if err := json.NewDecoder(resp.Body).Decode(&apiErr); err != nil {
			return nil, fmt.Errorf("API error (status %d)", resp.StatusCode)
		}
		apiErr.StatusCode = resp.StatusCode
		return nil, &apiErr
	}
	
	return resp, nil
}

// get performs a GET request
func (c *Client) get(ctx context.Context, path string, params url.Values, result interface{}) error {
	resp, err := c.request(ctx, "GET", path, params, nil)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if result != nil {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return fmt.Errorf("failed to decode response: %w", err)
		}
	}
	
	return nil
}

// post performs a POST request
func (c *Client) post(ctx context.Context, path string, body, result interface{}) error {
	resp, err := c.request(ctx, "POST", path, nil, body)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	
	if result != nil {
		if err := json.NewDecoder(resp.Body).Decode(result); err != nil {
			return fmt.Errorf("failed to decode response: %w", err)
		}
	}
	
	return nil
}

// Health checks the API health status
func (c *Client) Health(ctx context.Context) (*HealthStatus, error) {
	var health HealthStatus
	err := c.get(ctx, "/health", nil, &health)
	return &health, err
}

// APIError represents an API error response
type APIError struct {
	ErrorType  string                 `json:"error"`
	Message    string                 `json:"message"`
	Details    map[string]interface{} `json:"details,omitempty"`
	StatusCode int                    `json:"-"`
}

func (e *APIError) Error() string {
	return fmt.Sprintf("API error %d: %s", e.StatusCode, e.Message)
}

// Common response types

// HealthStatus represents the API health status
type HealthStatus struct {
	Status     string                            `json:"status"`
	Version    string                            `json:"version"`
	Uptime     string                            `json:"uptime"`
	Components map[string]map[string]interface{} `json:"components"`
}