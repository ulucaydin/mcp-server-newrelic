package discovery

import (
	"context"
	"time"
)

// DiscoveryEngine is the main interface for schema discovery operations
type DiscoveryEngine interface {
	// Core discovery operations
	DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error)
	DiscoverWithIntelligence(ctx context.Context, hints DiscoveryHints) (*DiscoveryResult, error)
	ProfileSchema(ctx context.Context, eventType string, depth ProfileDepth) (*Schema, error)
	
	// Sampling operations
	GetSamplingStrategy(ctx context.Context, eventType string) (SamplingStrategy, error)
	SampleData(ctx context.Context, params SamplingParams) (*DataSample, error)
	
	// Quality operations
	AssessQuality(ctx context.Context, schema string) (*QualityReport, error)
	
	// Relationship operations
	FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error)
	
	// Engine lifecycle
	Start(ctx context.Context) error
	Stop(ctx context.Context) error
	Health() HealthStatus
}

// SamplingStrategy defines the interface for different sampling approaches
type SamplingStrategy interface {
	Sample(ctx context.Context, params SamplingParams) (*DataSample, error)
	EstimateSampleSize(totalRecords int64) int64
	GetStrategyName() string
}

// PatternDetector defines the interface for pattern detection
type PatternDetector interface {
	DetectPatterns(data []interface{}, dataType DataType) []Pattern
	GetDetectorName() string
}

// QualityAssessor defines the interface for quality assessment
type QualityAssessor interface {
	AssessSchema(ctx context.Context, schema Schema, samples DataSample) QualityReport
	AssessAttribute(ctx context.Context, attr Attribute, values []interface{}) AttributeQuality
	GenerateRecommendations(report QualityReport) []QualityRecommendation
}

// RelationshipMiner defines the interface for discovering relationships
type RelationshipMiner interface {
	FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error)
	TestJoinability(ctx context.Context, source, target SchemaAttribute) (*JoinabilityResult, error)
	FindCorrelations(ctx context.Context, attributes []SchemaAttribute) ([]Correlation, error)
}

// NRDBClient defines the interface for NRDB interactions
type NRDBClient interface {
	Query(ctx context.Context, nrql string) (*QueryResult, error)
	QueryWithOptions(ctx context.Context, nrql string, opts QueryOptions) (*QueryResult, error)
	GetEventTypes(ctx context.Context, filter EventTypeFilter) ([]string, error)
	GetAccountInfo(ctx context.Context) (*AccountInfo, error)
}

// Cache defines the interface for caching operations
type Cache interface {
	Get(key string) (interface{}, bool)
	Set(key string, value interface{}, ttl time.Duration) error
	Delete(key string) error
	Clear() error
	Stats() CacheStats
}

// MetricsCollector defines the interface for metrics collection
type MetricsCollector interface {
	RecordDiscoveryDuration(duration time.Duration)
	RecordCacheHit(cacheType string)
	RecordCacheMiss(cacheType string)
	RecordError(operation string, err error)
	RecordSchemaDiscovered(eventType string)
	GetMetrics() map[string]interface{}
}

// Supporting types for interfaces

// DiscoveryFilter filters schemas during discovery
type DiscoveryFilter struct {
	EventTypes      []string      `json:"event_types,omitempty"`
	TimeRange       *TimeRange    `json:"time_range,omitempty"`
	MinRecordCount  int64         `json:"min_record_count,omitempty"`
	MaxSchemas      int           `json:"max_schemas,omitempty"`
	IncludePatterns []string      `json:"include_patterns,omitempty"`
	ExcludePatterns []string      `json:"exclude_patterns,omitempty"`
	Tags            map[string]string `json:"tags,omitempty"`
}

// DiscoveryHints provides hints for intelligent discovery
type DiscoveryHints struct {
	Keywords        []string               `json:"keywords"`
	Purpose         string                 `json:"purpose"`
	PreferredTypes  []string               `json:"preferred_types"`
	Domain          string                 `json:"domain"`
	Examples        []string               `json:"examples"`
	Constraints     map[string]interface{} `json:"constraints"`
}

// DiscoveryResult contains the results of intelligent discovery
type DiscoveryResult struct {
	Schemas         []Schema               `json:"schemas"`
	Patterns        []CrossSchemaPattern   `json:"patterns"`
	Insights        []Insight              `json:"insights"`
	Recommendations []string               `json:"recommendations"`
	ExecutionPlan   *ExecutionPlan         `json:"execution_plan"`
	Metadata        map[string]interface{} `json:"metadata"`
}

// ProfileDepth controls how deep schema profiling goes
type ProfileDepth string

const (
	ProfileDepthBasic    ProfileDepth = "basic"    // Just schema and attribute names
	ProfileDepthStandard ProfileDepth = "standard" // Include statistics and patterns
	ProfileDepthFull     ProfileDepth = "full"     // Everything including samples
)

// SamplingParams contains parameters for data sampling
type SamplingParams struct {
	EventType       string     `json:"event_type"`
	TimeRange       TimeRange  `json:"time_range"`
	MaxSamples      int64      `json:"max_samples"`
	Attributes      []string   `json:"attributes,omitempty"`
	Filter          string     `json:"filter,omitempty"`
	Strategy        string     `json:"strategy,omitempty"`
	Seed            int64      `json:"seed,omitempty"`
}

// DataSample contains sampled data from NRDB
type DataSample struct {
	EventType       string                   `json:"event_type"`
	Records         []map[string]interface{} `json:"records"`
	SampleSize      int                      `json:"sample_size"`
	TotalSize       int64                    `json:"total_size"`
	SamplingRate    float64                  `json:"sampling_rate"`
	Strategy        string                   `json:"strategy"`
	TimeRange       TimeRange                `json:"time_range"`
	Metadata        map[string]interface{}   `json:"metadata"`
}

// QueryResult represents the result of an NRDB query
type QueryResult struct {
	Results         []map[string]interface{} `json:"results"`
	Metadata        QueryMetadata            `json:"metadata"`
	PerformanceInfo *PerformanceInfo         `json:"performance_info,omitempty"`
}

// QueryMetadata contains metadata about a query
type QueryMetadata struct {
	EventTypes      []string               `json:"eventTypes"`
	Messages        []string               `json:"messages,omitempty"`
	Facets          []string               `json:"facets,omitempty"`
	Contents        map[string]interface{} `json:"contents,omitempty"`
}

// QueryOptions provides options for NRDB queries
type QueryOptions struct {
	Timeout         time.Duration          `json:"timeout,omitempty"`
	MaxResults      int                    `json:"max_results,omitempty"`
	IncludeMetadata bool                   `json:"include_metadata"`
	Account         string                 `json:"account,omitempty"`
}

// QualityReport contains comprehensive quality assessment
type QualityReport struct {
	SchemaName      string                 `json:"schema_name"`
	Timestamp       time.Time              `json:"timestamp"`
	OverallScore    float64                `json:"overall_score"`
	Dimensions      QualityDimensions      `json:"dimensions"`
	Issues          []QualityIssue         `json:"issues"`
	Recommendations []QualityRecommendation `json:"recommendations"`
	Trend           *QualityTrend          `json:"trend,omitempty"`
}

// QualityDimensions breaks down quality by dimension
type QualityDimensions struct {
	Completeness    DimensionScore `json:"completeness"`
	Consistency     DimensionScore `json:"consistency"`
	Timeliness      DimensionScore `json:"timeliness"`
	Uniqueness      DimensionScore `json:"uniqueness"`
	Validity        DimensionScore `json:"validity"`
}

// DimensionScore represents a score for a quality dimension
type DimensionScore struct {
	Score       float64  `json:"score"`
	Details     string   `json:"details"`
	Issues      []string `json:"issues,omitempty"`
}

// Relationship represents a discovered relationship between schemas
type Relationship struct {
	ID              string                 `json:"id"`
	Type            RelationType           `json:"type"`
	SourceSchema    string                 `json:"source_schema"`
	TargetSchema    string                 `json:"target_schema"`
	SourceAttribute string                 `json:"source_attribute"`
	TargetAttribute string                 `json:"target_attribute"`
	Confidence      float64                `json:"confidence"`
	Evidence        []Evidence             `json:"evidence"`
	Metadata        map[string]interface{} `json:"metadata"`
}

// RelationType defines types of relationships
type RelationType string

const (
	RelationTypeJoin        RelationType = "join"
	RelationTypeCorrelation RelationType = "correlation"
	RelationTypeTemporal    RelationType = "temporal"
	RelationTypeHierarchy   RelationType = "hierarchy"
	RelationTypeDerived     RelationType = "derived"
)

// Evidence supports a discovered relationship
type Evidence struct {
	Type        string      `json:"type"`
	Value       interface{} `json:"value"`
	Confidence  float64     `json:"confidence"`
	Description string      `json:"description"`
}

// HealthStatus represents the health of the discovery engine
type HealthStatus struct {
	Status      string                 `json:"status"`
	Version     string                 `json:"version"`
	Uptime      time.Duration          `json:"uptime"`
	Components  map[string]ComponentHealth `json:"components"`
	Metrics     map[string]interface{} `json:"metrics"`
}

// ComponentHealth represents health of a single component
type ComponentHealth struct {
	Status      string    `json:"status"`
	LastCheck   time.Time `json:"last_check"`
	Message     string    `json:"message,omitempty"`
}

// Additional supporting types

// SchemaAttribute identifies an attribute within a schema
type SchemaAttribute struct {
	Schema    string `json:"schema"`
	Attribute string `json:"attribute"`
}

// JoinabilityResult contains results of join testing
type JoinabilityResult struct {
	Joinable        bool    `json:"joinable"`
	MatchRatio      float64 `json:"match_ratio"`
	CardinalityType string  `json:"cardinality_type"` // "one-to-one", "one-to-many", etc.
	SampleMatches   int     `json:"sample_matches"`
	TotalSamples    int     `json:"total_samples"`
}

// Correlation represents a statistical correlation
type Correlation struct {
	Attribute1  SchemaAttribute `json:"attribute1"`
	Attribute2  SchemaAttribute `json:"attribute2"`
	Coefficient float64         `json:"coefficient"`
	PValue      float64         `json:"p_value"`
	Type        string          `json:"type"` // "pearson", "spearman", etc.
}

// CrossSchemaPattern represents patterns across multiple schemas
type CrossSchemaPattern struct {
	Name        string   `json:"name"`
	Schemas     []string `json:"schemas"`
	Type        string   `json:"type"`
	Confidence  float64  `json:"confidence"`
	Description string   `json:"description"`
}

// Insight represents a discovered insight
type Insight struct {
	ID          string                 `json:"id"`
	Type        string                 `json:"type"`
	Severity    string                 `json:"severity"`
	Title       string                 `json:"title"`
	Description string                 `json:"description"`
	Impact      string                 `json:"impact"`
	Evidence    map[string]interface{} `json:"evidence"`
	Actions     []string               `json:"suggested_actions"`
}

// ExecutionPlan shows how the discovery was executed
type ExecutionPlan struct {
	Steps       []ExecutionStep `json:"steps"`
	TotalTime   time.Duration   `json:"total_time"`
	Parallelism int             `json:"parallelism"`
}

// ExecutionStep represents a single step in execution
type ExecutionStep struct {
	Name        string        `json:"name"`
	Type        string        `json:"type"`
	Duration    time.Duration `json:"duration"`
	Status      string        `json:"status"`
	Details     string        `json:"details,omitempty"`
}

// EventTypeFilter filters event types
type EventTypeFilter struct {
	Pattern         string    `json:"pattern,omitempty"`
	MinRecordCount  int64     `json:"min_record_count,omitempty"`
	Since           time.Time `json:"since,omitempty"`
}

// AccountInfo contains New Relic account information
type AccountInfo struct {
	AccountID       int      `json:"account_id"`
	AccountName     string   `json:"account_name"`
	DataRetention   int      `json:"data_retention_days"`
	EventTypes      []string `json:"event_types"`
	Limits          AccountLimits `json:"limits"`
}

// AccountLimits contains account limits
type AccountLimits struct {
	MaxQueryDuration    time.Duration `json:"max_query_duration"`
	MaxResultsPerQuery  int           `json:"max_results_per_query"`
	RateLimitPerMinute  int           `json:"rate_limit_per_minute"`
}

// CacheStats provides cache statistics
type CacheStats struct {
	Hits        int64   `json:"hits"`
	Misses      int64   `json:"misses"`
	Evictions   int64   `json:"evictions"`
	Size        int64   `json:"size"`
	HitRate     float64 `json:"hit_rate"`
}

// PerformanceInfo contains query performance information
type PerformanceInfo struct {
	QueryTime       time.Duration `json:"query_time"`
	ProcessingTime  time.Duration `json:"processing_time"`
	BytesScanned    int64         `json:"bytes_scanned"`
	RecordsScanned  int64         `json:"records_scanned"`
}

// QualityTrend shows quality changes over time
type QualityTrend struct {
	Direction       string  `json:"direction"` // "improving", "declining", "stable"
	ChangeRate      float64 `json:"change_rate"`
	PreviousScore   float64 `json:"previous_score"`
	DaysSinceChange int     `json:"days_since_change"`
}