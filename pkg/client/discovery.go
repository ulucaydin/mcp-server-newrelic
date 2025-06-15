package client

import (
	"context"
	"fmt"
	"net/url"
	"strconv"
	"time"
)

// DiscoveryService handles discovery-related API calls
type DiscoveryService struct {
	client *Client
}

// Schema represents a discovered data schema
type Schema struct {
	Name           string            `json:"name"`
	EventType      string            `json:"eventType"`
	Attributes     []Attribute       `json:"attributes"`
	RecordCount    int64             `json:"recordCount"`
	SampleCount    int               `json:"sampleCount"`
	Quality        QualityMetrics    `json:"quality"`
	LastAnalyzed   time.Time         `json:"lastAnalyzed"`
}

// Attribute represents a schema attribute
type Attribute struct {
	Name         string     `json:"name"`
	DataType     string     `json:"dataType"`
	NullRatio    float64    `json:"nullRatio"`
	Cardinality  int        `json:"cardinality"`
	SemanticType string     `json:"semanticType,omitempty"`
	Patterns     []Pattern  `json:"patterns,omitempty"`
}

// Pattern represents a data pattern
type Pattern struct {
	Type        string   `json:"type"`
	Confidence  float64  `json:"confidence"`
	Description string   `json:"description"`
	Examples    []string `json:"examples,omitempty"`
}

// QualityMetrics represents data quality metrics
type QualityMetrics struct {
	OverallScore float64 `json:"overallScore"`
	Completeness float64 `json:"completeness"`
	Consistency  float64 `json:"consistency"`
	Timeliness   float64 `json:"timeliness"`
	Uniqueness   float64 `json:"uniqueness"`
	Validity     float64 `json:"validity"`
}

// ListSchemasOptions contains options for listing schemas
type ListSchemasOptions struct {
	EventType         string
	MinRecordCount    int64
	MaxSchemas        int
	IncludeMetadata   bool
}

// ListSchemasResponse contains the list schemas response
type ListSchemasResponse struct {
	Schemas  []Schema          `json:"schemas"`
	Metadata *DiscoveryMetadata `json:"metadata,omitempty"`
}

// DiscoveryMetadata contains discovery metadata
type DiscoveryMetadata struct {
	TotalSchemas   int    `json:"totalSchemas"`
	FilteredCount  int    `json:"filteredCount"`
	ExecutionTime  string `json:"executionTime"`
	CacheHit       bool   `json:"cacheHit"`
}

// ListSchemas lists available data schemas
func (s *DiscoveryService) ListSchemas(ctx context.Context, opts *ListSchemasOptions) (*ListSchemasResponse, error) {
	params := url.Values{}
	
	if opts != nil {
		if opts.EventType != "" {
			params.Set("eventType", opts.EventType)
		}
		if opts.MinRecordCount > 0 {
			params.Set("minRecordCount", strconv.FormatInt(opts.MinRecordCount, 10))
		}
		if opts.MaxSchemas > 0 {
			params.Set("maxSchemas", strconv.Itoa(opts.MaxSchemas))
		}
		if opts.IncludeMetadata {
			params.Set("includeMetadata", "true")
		}
	}
	
	var resp ListSchemasResponse
	err := s.client.get(ctx, "/discovery/schemas", params, &resp)
	return &resp, err
}

// ProfileSchemaOptions contains options for profiling a schema
type ProfileSchemaOptions struct {
	Depth string // basic, standard, full
}

// GetSchemaProfile gets detailed profile of a schema
func (s *DiscoveryService) GetSchemaProfile(ctx context.Context, eventType string, opts *ProfileSchemaOptions) (*Schema, error) {
	params := url.Values{}
	
	if opts != nil && opts.Depth != "" {
		params.Set("depth", opts.Depth)
	}
	
	var schema Schema
	path := fmt.Sprintf("/discovery/schemas/%s", url.PathEscape(eventType))
	err := s.client.get(ctx, path, params, &schema)
	return &schema, err
}

// Relationship represents a relationship between schemas
type Relationship struct {
	Type            string                 `json:"type"`
	SourceSchema    string                 `json:"sourceSchema"`
	TargetSchema    string                 `json:"targetSchema"`
	SourceAttribute string                 `json:"sourceAttribute"`
	TargetAttribute string                 `json:"targetAttribute"`
	Confidence      float64                `json:"confidence"`
	Evidence        []map[string]interface{} `json:"evidence"`
}

// FindRelationshipsRequest contains the request for finding relationships
type FindRelationshipsRequest struct {
	Schemas []string                   `json:"schemas"`
	Options FindRelationshipsOptions   `json:"options,omitempty"`
}

// FindRelationshipsOptions contains options for finding relationships
type FindRelationshipsOptions struct {
	MaxRelationships int     `json:"maxRelationships,omitempty"`
	MinConfidence    float64 `json:"minConfidence,omitempty"`
}

// FindRelationshipsResponse contains the relationships response
type FindRelationshipsResponse struct {
	Relationships []Relationship `json:"relationships"`
}

// FindRelationships finds relationships between schemas
func (s *DiscoveryService) FindRelationships(ctx context.Context, schemas []string, opts *FindRelationshipsOptions) ([]Relationship, error) {
	if len(schemas) < 2 {
		return nil, fmt.Errorf("at least 2 schemas required")
	}
	
	req := FindRelationshipsRequest{
		Schemas: schemas,
	}
	
	if opts != nil {
		req.Options = *opts
	}
	
	var resp FindRelationshipsResponse
	err := s.client.post(ctx, "/discovery/relationships", req, &resp)
	return resp.Relationships, err
}

// QualityReport represents a data quality assessment report
type QualityReport struct {
	SchemaName      string                    `json:"schemaName"`
	Timestamp       time.Time                 `json:"timestamp"`
	Metrics         QualityMetrics            `json:"metrics"`
	Issues          []QualityIssue            `json:"issues"`
	Recommendations []QualityRecommendation   `json:"recommendations"`
}

// QualityIssue represents a data quality issue
type QualityIssue struct {
	Type        string `json:"type"`
	Severity    string `json:"severity"`
	Attribute   string `json:"attribute"`
	Description string `json:"description"`
}

// QualityRecommendation represents a quality improvement recommendation
type QualityRecommendation struct {
	Type        string `json:"type"`
	Priority    string `json:"priority"`
	Description string `json:"description"`
	Impact      string `json:"impact"`
}

// AssessQualityOptions contains options for quality assessment
type AssessQualityOptions struct {
	TimeRange string
}

// AssessQuality assesses data quality for a schema
func (s *DiscoveryService) AssessQuality(ctx context.Context, eventType string, opts *AssessQualityOptions) (*QualityReport, error) {
	params := url.Values{}
	
	if opts != nil && opts.TimeRange != "" {
		params.Set("timeRange", opts.TimeRange)
	}
	
	var report QualityReport
	path := fmt.Sprintf("/discovery/quality/%s", url.PathEscape(eventType))
	err := s.client.get(ctx, path, params, &report)
	return &report, err
}