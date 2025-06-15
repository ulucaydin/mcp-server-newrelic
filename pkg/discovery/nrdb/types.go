package nrdb

import "time"

// NRDBConfig holds NRDB connection configuration
type NRDBConfig struct {
	APIKey       string
	AccountID    string
	BaseURL      string
	Region       string // US or EU
	Timeout      time.Duration
	MaxRetries   int
	RateLimit    int // queries per minute
}

// QueryResult represents NRDB query results
type QueryResult struct {
	Results         []map[string]interface{} `json:"results"`
	Metadata        QueryMetadata            `json:"metadata"`
	PerformanceInfo *PerformanceInfo         `json:"performanceInfo,omitempty"`
}

// QueryMetadata contains query execution metadata
type QueryMetadata struct {
	EventTypes     []string      `json:"eventTypes"`
	EventCount     int64         `json:"eventCount"`
	RawQuery       string        `json:"rawQuery"`
	Messages       []string      `json:"messages"`
	TimeWindow     TimeWindow    `json:"timeWindow"`
	ExecutionTime  int64         `json:"executionTimeMs"`
}

// TimeWindow represents the time range of the query
type TimeWindow struct {
	Begin time.Time `json:"begin"`
	End   time.Time `json:"end"`
}


// QueryOptions provides options for query execution
type QueryOptions struct {
	Timeout    time.Duration
	Streaming  bool
	MaxResults int
}

// EventTypeFilter filters event type discovery
type EventTypeFilter struct {
	Pattern         string
	Limit           int
	MinRecordCount  int
	Since           time.Time
}

// AccountInfo contains New Relic account information
type AccountInfo struct {
	AccountID      string
	AccountName    string
	Region         string
	DataRetention  int
	EventTypes     []string
	Limits         AccountLimits
}

// AccountLimits contains account usage limits
type AccountLimits struct {
	MaxNRQLLengthBytes int
	MaxQueryDuration   time.Duration
	MaxResultCount     int
	MaxResultsPerQuery int
	RateLimitPerMinute int
}

// PerformanceInfo contains query performance metrics
type PerformanceInfo struct {
	InspectedCount int64
	OmittedCount   int64
	QueryTime      time.Duration
	RecordsScanned int64
}