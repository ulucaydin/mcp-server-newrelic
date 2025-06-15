package client

import (
	"context"
)

// PatternsService handles pattern analysis API calls
type PatternsService struct {
	client *Client
}

// PatternAnalysisRequest contains the request for pattern analysis
type PatternAnalysisRequest struct {
	EventType  string                 `json:"eventType"`
	Attributes []string               `json:"attributes,omitempty"`
	TimeRange  string                 `json:"timeRange,omitempty"`
	Options    map[string]interface{} `json:"options,omitempty"`
}

// PatternAnalysisResult contains the pattern analysis results
type PatternAnalysisResult struct {
	Patterns  []DetectedPattern `json:"patterns"`
	Anomalies []Anomaly        `json:"anomalies"`
	Insights  []Insight        `json:"insights"`
}

// DetectedPattern represents a detected pattern
type DetectedPattern struct {
	Type        string                 `json:"type"`
	Confidence  float64                `json:"confidence"`
	Description string                 `json:"description"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// Anomaly represents a detected anomaly
type Anomaly struct {
	Type      string    `json:"type"`
	Severity  string    `json:"severity"`
	Timestamp string    `json:"timestamp"`
	Message   string    `json:"message"`
	Context   map[string]interface{} `json:"context,omitempty"`
}

// Insight represents an analytical insight
type Insight struct {
	Type        string   `json:"type"`
	Title       string   `json:"title"`
	Description string   `json:"description"`
	Impact      string   `json:"impact"`
	Actions     []string `json:"suggestedActions,omitempty"`
}

// AnalyzePatterns analyzes patterns in the specified event type
func (s *PatternsService) AnalyzePatterns(ctx context.Context, req *PatternAnalysisRequest) (*PatternAnalysisResult, error) {
	var result PatternAnalysisResult
	err := s.client.post(ctx, "/patterns/analyze", req, &result)
	return &result, err
}