package client

import (
	"context"
)

// QueryService handles query generation API calls
type QueryService struct {
	client *Client
}

// GenerateQueryRequest contains the request for query generation
type GenerateQueryRequest struct {
	Prompt  string              `json:"prompt"`
	Context QueryContext        `json:"context,omitempty"`
}

// QueryContext provides context for query generation
type QueryContext struct {
	Schemas   []string `json:"schemas,omitempty"`
	TimeRange string   `json:"timeRange,omitempty"`
	Examples  []string `json:"examples,omitempty"`
}

// GeneratedQuery contains the generated query and metadata
type GeneratedQuery struct {
	NRQL         string              `json:"nrql"`
	Explanation  string              `json:"explanation"`
	Warnings     []string            `json:"warnings,omitempty"`
	Alternatives []QueryAlternative  `json:"alternatives,omitempty"`
}

// QueryAlternative represents an alternative query
type QueryAlternative struct {
	NRQL        string `json:"nrql"`
	Description string `json:"description"`
}

// GenerateQuery generates a NRQL query from natural language
func (s *QueryService) GenerateQuery(ctx context.Context, prompt string, context *QueryContext) (*GeneratedQuery, error) {
	req := GenerateQueryRequest{
		Prompt: prompt,
	}
	
	if context != nil {
		req.Context = *context
	}
	
	var result GeneratedQuery
	err := s.client.post(ctx, "/query/generate", req, &result)
	return &result, err
}