//go:build !test && !nodiscovery

package mcp

import (
	"context"
	"fmt"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// registerTools registers all available MCP tools
func (s *Server) registerTools() error {
	// Discovery tools
	if err := s.registerDiscoveryTools(); err != nil {
		return fmt.Errorf("failed to register discovery tools: %w", err)
	}
	
	// TODO: Register pattern analysis tools (Track 3)
	// TODO: Register query generation tools (Track 3)
	// TODO: Register dashboard tools (Track 4)
	
	return nil
}

// registerDiscoveryTools registers tools that interface with Track 1's discovery engine
func (s *Server) registerDiscoveryTools() error {
	// List schemas tool
	s.tools.Register(Tool{
		Name:        "discovery.list_schemas",
		Description: "List all available schemas in the data source",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"filter": {
					Type:        "string",
					Description: "Optional filter for schema names",
				},
				"include_quality": {
					Type:        "boolean",
					Description: "Include quality metrics",
					Default:     false,
				},
			},
		},
		Handler: s.handleListSchemas,
	})
	
	// Profile attribute tool
	s.tools.Register(Tool{
		Name:        "discovery.profile_attribute",
		Description: "Deep analysis of a specific data attribute",
		Parameters: ToolParameters{
			Type: "object",
			Required: []string{"schema", "attribute"},
			Properties: map[string]Property{
				"schema": {
					Type:        "string",
					Description: "Schema/event type name",
				},
				"attribute": {
					Type:        "string",
					Description: "Attribute name to profile",
				},
				"sample_size": {
					Type:        "integer",
					Description: "Number of samples to analyze",
					Default:     10000,
				},
			},
		},
		Handler:     s.handleProfileAttribute,
		Streaming:   true,
		StreamHandler: s.handleProfileAttributeStream,
	})
	
	// Find relationships tool
	s.tools.Register(Tool{
		Name:        "discovery.find_relationships",
		Description: "Discover relationships between schemas",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"schemas": {
					Type:        "array",
					Description: "List of schemas to analyze",
					Items:       &Property{Type: "string"},
				},
				"confidence_threshold": {
					Type:        "number",
					Description: "Minimum confidence for relationships",
					Default:     0.7,
				},
			},
		},
		Handler: s.handleFindRelationships,
	})
	
	// Assess quality tool
	s.tools.Register(Tool{
		Name:        "discovery.assess_quality",
		Description: "Assess data quality for a schema",
		Parameters: ToolParameters{
			Type: "object",
			Required: []string{"schema"},
			Properties: map[string]Property{
				"schema": {
					Type:        "string",
					Description: "Schema name to assess",
				},
				"detailed": {
					Type:        "boolean",
					Description: "Include detailed quality metrics",
					Default:     false,
				},
			},
		},
		Handler: s.handleAssessQuality,
	})
	
	return nil
}

// Tool handler implementations

func (s *Server) handleListSchemas(ctx context.Context, params map[string]interface{}) (interface{}, error) {
	if s.discovery == nil {
		return nil, fmt.Errorf("discovery engine not initialized")
	}
	
	// Extract parameters
	filter, _ := params["filter"].(string)
	includeQuality, _ := params["include_quality"].(bool)
	
	// Call discovery engine from Track 1
	schemas, err := s.discovery.DiscoverSchemas(ctx, discovery.DiscoveryFilter{
		NamePattern: filter,
	})
	
	if err != nil {
		return nil, fmt.Errorf("discovery failed: %w", err)
	}
	
	// Transform response for MCP
	type SchemaInfo struct {
		Name           string       `json:"name"`
		AttributeCount int          `json:"attribute_count"`
		RecordCount    int64        `json:"record_count"`
		LastUpdated    time.Time    `json:"last_updated"`
		Quality        *QualityInfo `json:"quality,omitempty"`
	}
	
	type QualityInfo struct {
		Score  float64 `json:"score"`
		Issues int     `json:"issues"`
	}
	
	response := struct {
		Schemas []SchemaInfo `json:"schemas"`
		Count   int          `json:"count"`
	}{
		Schemas: make([]SchemaInfo, len(schemas)),
		Count:   len(schemas),
	}
	
	for i, schema := range schemas {
		info := SchemaInfo{
			Name:           schema.Name,
			AttributeCount: len(schema.Attributes),
			RecordCount:    schema.DataVolume.EstimatedCount,
			LastUpdated:    schema.LastAnalyzedAt,
		}
		
		if includeQuality {
			info.Quality = &QualityInfo{
				Score:  schema.Quality.OverallScore,
				Issues: len(schema.Quality.Issues),
			}
		}
		
		response.Schemas[i] = info
	}
	
	return response, nil
}

func (s *Server) handleProfileAttribute(ctx context.Context, params map[string]interface{}) (interface{}, error) {
	if s.discovery == nil {
		return nil, fmt.Errorf("discovery engine not initialized")
	}
	
	schemaName, ok := params["schema"].(string)
	if !ok {
		return nil, fmt.Errorf("schema parameter is required")
	}
	
	attributeName, ok := params["attribute"].(string)
	if !ok {
		return nil, fmt.Errorf("attribute parameter is required")
	}
	
	// For non-streaming, just return basic profile
	schema, err := s.discovery.ProfileSchema(ctx, schemaName, discovery.ProfileDepthStandard)
	if err != nil {
		return nil, fmt.Errorf("profile failed: %w", err)
	}
	
	// Find the specific attribute
	for _, attr := range schema.Attributes {
		if attr.Name == attributeName {
			return map[string]interface{}{
				"schema":    schemaName,
				"attribute": attr,
			}, nil
		}
	}
	
	return nil, fmt.Errorf("attribute %s not found in schema %s", attributeName, schemaName)
}

func (s *Server) handleProfileAttributeStream(ctx context.Context, params map[string]interface{}, stream chan<- StreamChunk) {
	defer close(stream)
	
	if s.discovery == nil {
		stream <- StreamChunk{
			Type:  "error",
			Error: fmt.Errorf("discovery engine not initialized"),
		}
		return
	}
	
	schemaName, _ := params["schema"].(string)
	attributeName, _ := params["attribute"].(string)
	
	// Stream progress updates
	stream <- StreamChunk{
		Type: "progress",
		Data: map[string]interface{}{
			"message":  fmt.Sprintf("Starting analysis of %s.%s", schemaName, attributeName),
			"progress": 0,
		},
	}
	
	// Deep profile with progress updates
	stream <- StreamChunk{
		Type: "progress",
		Data: map[string]interface{}{
			"message":  "Retrieving schema information...",
			"progress": 20,
		},
	}
	
	schema, err := s.discovery.ProfileSchema(ctx, schemaName, discovery.ProfileDepthFull)
	if err != nil {
		stream <- StreamChunk{
			Type:  "error",
			Error: err,
		}
		return
	}
	
	stream <- StreamChunk{
		Type: "progress",
		Data: map[string]interface{}{
			"message":  "Analyzing attribute patterns...",
			"progress": 60,
		},
	}
	
	// Find and analyze the attribute
	for _, attr := range schema.Attributes {
		if attr.Name == attributeName {
			stream <- StreamChunk{
				Type: "progress",
				Data: map[string]interface{}{
					"message":  "Generating insights...",
					"progress": 80,
				},
			}
			
			// Send final result
			stream <- StreamChunk{
				Type: "result",
				Data: map[string]interface{}{
					"schema":    schemaName,
					"attribute": attr,
					"insights":  generateAttributeInsights(attr),
				},
			}
			
			stream <- StreamChunk{
				Type: "complete",
				Data: map[string]interface{}{
					"message":  "Analysis complete",
					"progress": 100,
				},
			}
			return
		}
	}
	
	stream <- StreamChunk{
		Type:  "error",
		Error: fmt.Errorf("attribute %s not found in schema %s", attributeName, schemaName),
	}
}

func (s *Server) handleFindRelationships(ctx context.Context, params map[string]interface{}) (interface{}, error) {
	if s.discovery == nil {
		return nil, fmt.Errorf("discovery engine not initialized")
	}
	
	// Extract schema names
	schemasRaw, ok := params["schemas"].([]interface{})
	if !ok || len(schemasRaw) == 0 {
		// If no schemas specified, discover all and find relationships
		allSchemas, err := s.discovery.DiscoverSchemas(ctx, discovery.DiscoveryFilter{})
		if err != nil {
			return nil, fmt.Errorf("failed to discover schemas: %w", err)
		}
		
		relationships, err := s.discovery.FindRelationships(ctx, allSchemas)
		if err != nil {
			return nil, fmt.Errorf("failed to find relationships: %w", err)
		}
		
		return map[string]interface{}{
			"relationships": relationships,
			"count":         len(relationships),
		}, nil
	}
	
	// Convert schema names and fetch schemas
	schemas := make([]discovery.Schema, 0, len(schemasRaw))
	for _, name := range schemasRaw {
		schemaName, ok := name.(string)
		if !ok {
			continue
		}
		
		schema, err := s.discovery.ProfileSchema(ctx, schemaName, discovery.ProfileDepthBasic)
		if err != nil {
			continue // Skip schemas that can't be profiled
		}
		
		schemas = append(schemas, *schema)
	}
	
	relationships, err := s.discovery.FindRelationships(ctx, schemas)
	if err != nil {
		return nil, fmt.Errorf("failed to find relationships: %w", err)
	}
	
	// Filter by confidence threshold if specified
	threshold, _ := params["confidence_threshold"].(float64)
	if threshold > 0 {
		filtered := make([]discovery.Relationship, 0)
		for _, rel := range relationships {
			if rel.Confidence >= threshold {
				filtered = append(filtered, rel)
			}
		}
		relationships = filtered
	}
	
	return map[string]interface{}{
		"relationships": relationships,
		"count":         len(relationships),
	}, nil
}

func (s *Server) handleAssessQuality(ctx context.Context, params map[string]interface{}) (interface{}, error) {
	if s.discovery == nil {
		return nil, fmt.Errorf("discovery engine not initialized")
	}
	
	schemaName, ok := params["schema"].(string)
	if !ok {
		return nil, fmt.Errorf("schema parameter is required")
	}
	
	detailed, _ := params["detailed"].(bool)
	
	report, err := s.discovery.AssessQuality(ctx, schemaName)
	if err != nil {
		return nil, fmt.Errorf("quality assessment failed: %w", err)
	}
	
	if !detailed {
		// Return summary only
		return map[string]interface{}{
			"schema":        schemaName,
			"overall_score": report.Metrics.OverallScore,
			"status":        getQualityStatus(report.Metrics.OverallScore),
			"issue_count":   len(report.Metrics.Issues),
		}, nil
	}
	
	return report, nil
}

// Helper functions

func generateAttributeInsights(attr discovery.Attribute) []map[string]interface{} {
	insights := []map[string]interface{}{}
	
	// Cardinality insight
	if attr.Cardinality.Unique == attr.Cardinality.Total {
		insights = append(insights, map[string]interface{}{
			"type":        "uniqueness",
			"title":       "Unique Identifier",
			"description": fmt.Sprintf("%s appears to be a unique identifier", attr.Name),
			"confidence":  0.95,
		})
	}
	
	// Null ratio insight
	if attr.NullRatio > 0.5 {
		insights = append(insights, map[string]interface{}{
			"type":        "completeness",
			"title":       "High Null Rate",
			"description": fmt.Sprintf("%s has %.1f%% null values", attr.Name, attr.NullRatio*100),
			"confidence":  1.0,
		})
	}
	
	// Pattern insights
	for _, pattern := range attr.Patterns {
		insights = append(insights, map[string]interface{}{
			"type":        "pattern",
			"title":       fmt.Sprintf("%s Pattern Detected", pattern.Type),
			"description": pattern.Description,
			"confidence":  pattern.Confidence,
		})
	}
	
	return insights
}

func getQualityStatus(score float64) string {
	switch {
	case score >= 0.9:
		return "excellent"
	case score >= 0.7:
		return "good"
	case score >= 0.5:
		return "fair"
	default:
		return "poor"
	}
}