//go:build test || nodiscovery

package mcp

import (
	"context"
)

// registerDiscoveryTools registers discovery-related tools (no-op for testing)
func (s *Server) registerDiscoveryTools() {
	// Register mock discovery tools for testing
	s.tools.Register(Tool{
		Name:        "discovery.list_schemas",
		Description: "List available data schemas (mock)",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"filter": {
					Type:        "object",
					Description: "Filter criteria",
				},
			},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			// Return mock schemas for testing
			return map[string]interface{}{
				"schemas": []map[string]interface{}{
					{
						"name":        "Transaction",
						"event_type":  "Transaction",
						"record_count": 1000000,
						"attributes": []map[string]interface{}{
							{
								"name":      "duration",
								"data_type": "numeric",
							},
							{
								"name":      "error",
								"data_type": "boolean",
							},
						},
					},
					{
						"name":        "PageView",
						"event_type":  "PageView",
						"record_count": 500000,
						"attributes": []map[string]interface{}{
							{
								"name":      "url",
								"data_type": "string",
							},
						},
					},
				},
			}, nil
		},
	})
	
	s.tools.Register(Tool{
		Name:        "discovery.profile_attribute",
		Description: "Get detailed profile of a schema attribute (mock)",
		Parameters: ToolParameters{
			Type: "object",
			Properties: map[string]Property{
				"schema": {
					Type:        "string",
					Description: "Schema name",
				},
				"attribute": {
					Type:        "string",
					Description: "Attribute name",
				},
			},
			Required: []string{"schema", "attribute"},
		},
		Handler: func(ctx context.Context, params map[string]interface{}) (interface{}, error) {
			schema := params["schema"].(string)
			attribute := params["attribute"].(string)
			
			return map[string]interface{}{
				"schema":    schema,
				"attribute": attribute,
				"profile": map[string]interface{}{
					"data_type":   "numeric",
					"null_ratio":  0.01,
					"cardinality": 1000,
					"patterns": []map[string]interface{}{
						{
							"type":        "range",
							"description": "Values between 0.1 and 5.0",
							"confidence":  0.9,
						},
					},
				},
			}, nil
		},
	})
}