package grpc

// This file contains the simplified gRPC types without requiring protobuf generation
// These types match the proto definitions but are plain Go structs

// Request/Response types

type DiscoverSchemasRequest struct {
	AccountID   string
	Pattern     string
	MaxSchemas  int32
	EventTypes  []string
	TimeRange   int64 // Duration in seconds
	Tags        map[string]string
}

type DiscoverSchemasResponse struct {
	Schemas           []*Schema
	TotalCount        int32
	DiscoveryDuration int64 // milliseconds
	Metadata          map[string]string
}

type ProfileSchemaRequest struct {
	EventType       string
	ProfileDepth    string // basic, standard, deep
	IncludePatterns bool
	IncludeQuality  bool
	SampleSize      int32
	TimeRange       int64 // Duration in seconds
}

type ProfileSchemaResponse struct {
	Schema            *Schema
	ProfilingDuration int64 // milliseconds
	Metadata          map[string]string
}

type IntelligentDiscoveryRequest struct {
	FocusAreas          []string
	EventTypes          []string
	AnomalyDetection    bool
	PatternMining       bool
	QualityAssessment   bool
	ConfidenceThreshold float64
	Context             map[string]string
}

type IntelligentDiscoveryResponse struct {
	Schemas           []*Schema
	Insights          []*DiscoveryInsight
	Recommendations   []string
	DiscoveryDuration int64 // milliseconds
}

type FindRelationshipsRequest struct {
	SchemaNames             []string
	RelationshipTypes       []string
	MinConfidence           float64
	MaxRelationships        int32
	IncludeWeakRelationships bool
}

type FindRelationshipsResponse struct {
	Relationships    []*Relationship
	Graph            *RelationshipGraph
	AnalysisDuration int64 // milliseconds
}

type AssessQualityRequest struct {
	EventType         string
	SampleSize        int32
	TimeRange         int64 // Duration in seconds
	QualityDimensions []string
	DetailedAnalysis  bool
}

type AssessQualityResponse struct {
	Report             *QualityReport
	AssessmentDuration int64 // milliseconds
}

type GetHealthRequest struct {
	IncludeMetrics bool
}

type GetHealthResponse struct {
	IsHealthy bool
	Status    string
	Checks    []*HealthCheck
	Metrics   *HealthMetrics
	Timestamp int64 // Unix timestamp
}

// Data types

type Schema struct {
	Id             string
	Name           string
	EventType      string
	Attributes     []*Attribute
	SampleCount    int64
	DataVolume     *DataVolumeProfile
	Quality        *QualityMetrics
	Patterns       []*DetectedPattern
	DiscoveredAt   int64 // Unix timestamp
	LastAnalyzedAt int64 // Unix timestamp
	Metadata       string // JSON string
}

type Attribute struct {
	Name         string
	DataType     string
	SemanticType string
	IsRequired   bool
	IsUnique     bool
	IsIndexed    bool
	Cardinality  float64
	SampleValues []string
}

type DataVolumeProfile struct {
	TotalEvents     int64
	EventsPerMinute float64
	DataSizeBytes   int64
	FirstSeen       int64 // Unix timestamp
	LastSeen        int64 // Unix timestamp
}

type QualityMetrics struct {
	OverallScore float64
	Dimensions   *QualityDimensions
	Issues       []*QualityIssue
}

type QualityDimensions struct {
	Completeness *QualityDimension
	Consistency  *QualityDimension
	Timeliness   *QualityDimension
	Uniqueness   *QualityDimension
	Validity     *QualityDimension
}

type QualityDimension struct {
	Score  float64
	Issues []string
}

type QualityIssue struct {
	Severity           string
	Type               string
	Description        string
	AffectedAttributes []string
	OccurrenceCount    int64
}

type DetectedPattern struct {
	Type               string
	Subtype            string
	Confidence         float64
	Description        string
	Parameters         string // JSON string
	AffectedAttributes []string
}

type Relationship struct {
	Id             string
	Type           string
	SourceSchema   string
	TargetSchema   string
	JoinConditions []*JoinCondition
	Strength       float64
	Confidence     float64
	SampleMatches  int64
}

type JoinCondition struct {
	SourceAttribute string
	TargetAttribute string
	Operator        string
}

type DiscoveryInsight struct {
	Type            string
	Severity        string
	Title           string
	Description     string
	AffectedSchemas []string
	Confidence      float64
	Evidence        string // JSON string
}

type RelationshipGraph struct {
	Nodes      []*GraphNode
	Edges      []*GraphEdge
	Properties map[string]string
}

type GraphNode struct {
	Id         string
	SchemaName string
	Properties map[string]string
}

type GraphEdge struct {
	Source         string
	Target         string
	RelationshipId string
	Weight         float64
}

type QualityReport struct {
	EventType    string
	OverallScore float64
	Dimensions   *QualityDimensions
	Issues       []*QualityIssue
	AssessedAt   int64 // Unix timestamp
	Metadata     string // JSON string
}

type HealthCheck struct {
	Name      string
	IsHealthy bool
	Message   string
	Duration  int64 // milliseconds
}

type HealthMetrics struct {
	QueriesProcessed   int64
	ErrorsCount        int64
	CacheHitRate       float64
	Uptime             int64 // seconds
	AverageQueryTimeMs int64
	ActiveConnections  int64
	CustomMetrics      map[string]float64
}

// Service interface that will be implemented by the server
type DiscoveryServiceServer interface {
	DiscoverSchemas(context.Context, *DiscoverSchemasRequest) (*DiscoverSchemasResponse, error)
	ProfileSchema(context.Context, *ProfileSchemaRequest) (*ProfileSchemaResponse, error)
	IntelligentDiscovery(context.Context, *IntelligentDiscoveryRequest) (*IntelligentDiscoveryResponse, error)
	FindRelationships(context.Context, *FindRelationshipsRequest) (*FindRelationshipsResponse, error)
	AssessQuality(context.Context, *AssessQualityRequest) (*AssessQualityResponse, error)
	GetHealth(context.Context, *GetHealthRequest) (*GetHealthResponse, error)
}

// RegisterDiscoveryServiceServer registers the service with the gRPC server
func RegisterDiscoveryServiceServer(s *grpc.Server, srv DiscoveryServiceServer) {
	// This would normally be generated by protoc
	// For now, we'll implement a simplified version
	// The actual implementation would use the generated code
}