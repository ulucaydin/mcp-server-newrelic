//go:build test || nodiscovery

package mcp

import (
	"context"
	"time"
)

// Mock types for testing without discovery dependency
type mockSchema struct {
	Name           string
	EventType      string
	Attributes     []mockAttribute
	SampleCount    int64
	DataVolume     mockDataVolumeProfile
	Quality        mockQualityMetrics
	LastAnalyzedAt time.Time
}

type mockAttribute struct {
	Name         string
	DataType     string
	NullRatio    float64
	Cardinality  mockCardinalityProfile
	SemanticType string
	Patterns     []mockPattern
}

type mockCardinalityProfile struct {
	Unique int64
	Total  int64
}

type mockDataVolumeProfile struct {
	EstimatedCount int64
}

type mockQualityMetrics struct {
	OverallScore float64
	Completeness float64
	Consistency  float64
	Timeliness   float64
	Uniqueness   float64
	Validity     float64
	Issues       []mockQualityIssue
}

type mockQualityIssue struct {
	Type        string
	Severity    string
	Attribute   string
	Description string
}

type mockPattern struct {
	Type        string
	Confidence  float64
	Description string
}

type mockDiscoveryResult struct {
	Schemas  []mockSchema
	Patterns []mockDetectedPattern
	Insights []mockInsight
}

type mockDetectedPattern struct {
	Type        string
	Confidence  float64
	Description string
}

type mockInsight struct {
	Type        string
	Title       string
	Description string
	Severity    string
	Confidence  float64
}

type mockRelationship struct {
	Type            string
	SourceSchema    string
	TargetSchema    string
	SourceAttribute string
	TargetAttribute string
	Confidence      float64
	Evidence        []mockEvidence
}

type mockEvidence struct {
	Type  string
	Value float64
}

type mockQualityReport struct {
	SchemaName      string
	Timestamp       time.Time
	Metrics         mockQualityMetrics
}

type mockQualityRecommendation struct {
	Type        string
	Priority    string
	Description string
	Impact      string
}

type mockDataSample struct{}

type mockSamplingParams struct {
	EventType  string
	TimeRange  mockTimeRange
	MaxSamples int64
}

type mockTimeRange struct {
	Start time.Time
	End   time.Time
}

type mockDiscoveryFilter struct{}
type mockDiscoveryHints struct{}
type mockProfileDepth string

const (
	mockProfileDepthBasic    mockProfileDepth = "basic"
	mockProfileDepthStandard mockProfileDepth = "standard"
	mockProfileDepthFull     mockProfileDepth = "full"
)

type mockHealthStatus struct {
	Status string
}

// Mock discovery engine interface for testing
type mockDiscoveryEngine interface {
	DiscoverSchemas(ctx context.Context, filter mockDiscoveryFilter) ([]mockSchema, error)
	DiscoverWithIntelligence(ctx context.Context, hints mockDiscoveryHints) (*mockDiscoveryResult, error)
	ProfileSchema(ctx context.Context, eventType string, depth mockProfileDepth) (*mockSchema, error)
	GetSamplingStrategy(ctx context.Context, eventType string) (interface{}, error)
	SampleData(ctx context.Context, params mockSamplingParams) (*mockDataSample, error)
	AssessQuality(ctx context.Context, schema string) (*mockQualityReport, error)
	FindRelationships(ctx context.Context, schemas []mockSchema) ([]mockRelationship, error)
	Start(ctx context.Context) error
	Stop(ctx context.Context) error
	Health() mockHealthStatus
}