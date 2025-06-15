//go:build test || nodiscovery

package mcp

import (
	"context"
	"fmt"
	"time"
)

// mockDiscoveryEngineImpl is a mock implementation for testing
type mockDiscoveryEngineImpl struct{}

func newMockDiscoveryEngine() mockDiscoveryEngine {
	return &mockDiscoveryEngineImpl{}
}

func (m *mockDiscoveryEngineImpl) DiscoverSchemas(ctx context.Context, filter mockDiscoveryFilter) ([]mockSchema, error) {
	// Return mock schemas
	return []mockSchema{
		{
			Name:      "Transaction",
			EventType: "Transaction",
			Attributes: []mockAttribute{
				{
					Name:     "duration",
					DataType: "numeric",
					NullRatio: 0.01,
					Cardinality: mockCardinalityProfile{
						Unique: 1000,
						Total:  10000,
					},
				},
				{
					Name:     "error",
					DataType: "boolean",
					NullRatio: 0.0,
				},
				{
					Name:     "name",
					DataType: "string",
					NullRatio: 0.0,
					SemanticType: "url",
				},
			},
			SampleCount: 1000000,
			DataVolume: mockDataVolumeProfile{
				EstimatedCount: 1000000,
			},
			Quality: mockQualityMetrics{
				OverallScore: 0.85,
				Completeness: 0.99,
				Consistency:  0.88,
				Timeliness:   0.85,
				Uniqueness:   0.82,
				Validity:     0.83,
			},
			LastAnalyzedAt: time.Now(),
		},
		{
			Name:      "PageView",
			EventType: "PageView",
			Attributes: []mockAttribute{
				{
					Name:     "url",
					DataType: "string",
					SemanticType: "url",
				},
				{
					Name:     "duration",
					DataType: "numeric",
				},
				{
					Name:     "userAgent",
					DataType: "string",
					SemanticType: "user_agent",
				},
			},
			SampleCount: 500000,
			DataVolume: mockDataVolumeProfile{
				EstimatedCount: 500000,
			},
			Quality: mockQualityMetrics{
				OverallScore: 0.92,
			},
			LastAnalyzedAt: time.Now(),
		},
	}, nil
}

func (m *mockDiscoveryEngineImpl) DiscoverWithIntelligence(ctx context.Context, hints mockDiscoveryHints) (*mockDiscoveryResult, error) {
	schemas, err := m.DiscoverSchemas(ctx, mockDiscoveryFilter{})
	if err != nil {
		return nil, err
	}
	
	return &mockDiscoveryResult{
		Schemas: schemas,
		Patterns: []mockDetectedPattern{
			{
				Type:        "trend",
				Confidence:  0.85,
				Description: "Increasing transaction duration trend",
			},
		},
		Insights: []mockInsight{
			{
				Type:        "performance",
				Title:       "High Error Rate Detected",
				Description: "Error rate has increased by 15% in the last hour",
				Severity:    "high",
				Confidence:  0.92,
			},
		},
	}, nil
}

func (m *mockDiscoveryEngineImpl) ProfileSchema(ctx context.Context, eventType string, depth mockProfileDepth) (*mockSchema, error) {
	schemas, _ := m.DiscoverSchemas(ctx, mockDiscoveryFilter{})
	for _, schema := range schemas {
		if schema.EventType == eventType {
			// Add more detail based on depth
			if depth == mockProfileDepthFull {
				// Add patterns to attributes
				for i := range schema.Attributes {
					schema.Attributes[i].Patterns = []mockPattern{
						{
							Type:        "range",
							Confidence:  0.9,
							Description: "Values typically between 0.1 and 5.0",
						},
					}
				}
			}
			return &schema, nil
		}
	}
	return nil, fmt.Errorf("schema not found: %s", eventType)
}

func (m *mockDiscoveryEngineImpl) GetSamplingStrategy(ctx context.Context, eventType string) (interface{}, error) {
	return nil, fmt.Errorf("not implemented in mock")
}

func (m *mockDiscoveryEngineImpl) SampleData(ctx context.Context, params mockSamplingParams) (*mockDataSample, error) {
	return &mockDataSample{}, fmt.Errorf("not implemented in mock")
}

func (m *mockDiscoveryEngineImpl) AssessQuality(ctx context.Context, schema string) (*mockQualityReport, error) {
	return &mockQualityReport{
		SchemaName: schema,
		Timestamp:  time.Now(),
		Metrics: mockQualityMetrics{
			OverallScore: 0.85,
			Completeness: 0.90,
			Consistency:  0.88,
			Timeliness:   0.85,
			Uniqueness:   0.82,
			Validity:     0.83,
			Issues: []mockQualityIssue{
				{
					Type:        "completeness",
					Severity:    "medium",
					Attribute:   "user_id",
					Description: "15% null values detected",
				},
			},
		},
	}, nil
}

func (m *mockDiscoveryEngineImpl) FindRelationships(ctx context.Context, schemas []mockSchema) ([]mockRelationship, error) {
	if len(schemas) < 2 {
		return []mockRelationship{}, nil
	}
	
	return []mockRelationship{
		{
			Type:            "join",
			SourceSchema:    schemas[0].Name,
			TargetSchema:    schemas[1].Name,
			SourceAttribute: "sessionId",
			TargetAttribute: "sessionId",
			Confidence:      0.95,
			Evidence: []mockEvidence{
				{
					Type:  "cardinality_match",
					Value: 0.98,
				},
				{
					Type:  "value_overlap",
					Value: 0.95,
				},
			},
		},
	}, nil
}

func (m *mockDiscoveryEngineImpl) Start(ctx context.Context) error {
	return nil
}

func (m *mockDiscoveryEngineImpl) Stop(ctx context.Context) error {
	return nil
}

func (m *mockDiscoveryEngineImpl) Health() mockHealthStatus {
	return mockHealthStatus{Status: "healthy"}
}