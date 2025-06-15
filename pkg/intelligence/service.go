// Package intelligence provides Go wrapper for Python intelligence engine
package intelligence

import (
	"context"
	"encoding/json"
	"fmt"
	"os/exec"
	"time"

	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	
	pb "github.com/anthropics/mcp-server-newrelic/pkg/intelligence/proto"
)

// Service wraps the Python intelligence engine for Go consumption
type Service struct {
	logger       *logrus.Logger
	pythonPath   string
	grpcEndpoint string
	grpcClient   pb.IntelligenceServiceClient
	grpcConn     *grpc.ClientConn
	process      *exec.Cmd
}

// NewService creates a new intelligence service wrapper
func NewService(logger *logrus.Logger, pythonPath string) *Service {
	return &Service{
		logger:       logger,
		pythonPath:   pythonPath,
		grpcEndpoint: "localhost:50051", // Default gRPC port
	}
}

// Start launches the Python intelligence service
func (s *Service) Start(ctx context.Context) error {
	// Start Python gRPC server
	s.logger.Info("Starting Python intelligence service")
	
	s.process = exec.CommandContext(ctx, s.pythonPath, "-m", "intelligence.grpc_server")
	s.process.Dir = "/home/deepak/src/mcp-server-newrelic"
	
	// Start the process
	if err := s.process.Start(); err != nil {
		return fmt.Errorf("failed to start Python service: %w", err)
	}
	
	// Wait for service to be ready
	time.Sleep(2 * time.Second)
	
	// Connect to gRPC server
	conn, err := grpc.Dial(s.grpcEndpoint, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		s.Stop()
		return fmt.Errorf("failed to connect to gRPC server: %w", err)
	}
	
	s.grpcConn = conn
	s.grpcClient = pb.NewIntelligenceServiceClient(conn)
	
	// Test connection
	_, err = s.grpcClient.HealthCheck(ctx, &pb.Empty{})
	if err != nil {
		s.Stop()
		return fmt.Errorf("health check failed: %w", err)
	}
	
	s.logger.Info("Python intelligence service started successfully")
	return nil
}

// Stop gracefully shuts down the Python service
func (s *Service) Stop() error {
	s.logger.Info("Stopping Python intelligence service")
	
	// Close gRPC connection
	if s.grpcConn != nil {
		s.grpcConn.Close()
	}
	
	// Stop Python process
	if s.process != nil && s.process.Process != nil {
		s.process.Process.Kill()
		s.process.Wait()
	}
	
	return nil
}

// AnalyzePatterns detects patterns in the provided data
func (s *Service) AnalyzePatterns(ctx context.Context, data map[string]interface{}) (*PatternAnalysisResult, error) {
	// Convert data to JSON
	dataJSON, err := json.Marshal(data)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal data: %w", err)
	}
	
	// Call gRPC service
	req := &pb.AnalyzePatternsRequest{
		Data: string(dataJSON),
	}
	
	resp, err := s.grpcClient.AnalyzePatterns(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("pattern analysis failed: %w", err)
	}
	
	// Parse response
	var result PatternAnalysisResult
	if err := json.Unmarshal([]byte(resp.Result), &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal result: %w", err)
	}
	
	return &result, nil
}

// GenerateQuery converts natural language to NRQL
func (s *Service) GenerateQuery(ctx context.Context, naturalQuery string, context *QueryContext) (*QueryResult, error) {
	// Convert context to JSON
	contextJSON, err := json.Marshal(context)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal context: %w", err)
	}
	
	// Call gRPC service
	req := &pb.GenerateQueryRequest{
		NaturalQuery: naturalQuery,
		Context:      string(contextJSON),
	}
	
	resp, err := s.grpcClient.GenerateQuery(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("query generation failed: %w", err)
	}
	
	// Parse response
	var result QueryResult
	if err := json.Unmarshal([]byte(resp.Result), &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal result: %w", err)
	}
	
	return &result, nil
}

// RecommendCharts suggests optimal chart types for data
func (s *Service) RecommendCharts(ctx context.Context, dataShape map[string]interface{}) (*ChartRecommendations, error) {
	// Convert data shape to JSON
	dataJSON, err := json.Marshal(dataShape)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal data shape: %w", err)
	}
	
	// Call gRPC service
	req := &pb.RecommendChartsRequest{
		DataShape: string(dataJSON),
	}
	
	resp, err := s.grpcClient.RecommendCharts(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("chart recommendation failed: %w", err)
	}
	
	// Parse response
	var result ChartRecommendations
	if err := json.Unmarshal([]byte(resp.Result), &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal result: %w", err)
	}
	
	return &result, nil
}

// OptimizeLayout optimizes dashboard widget layout
func (s *Service) OptimizeLayout(ctx context.Context, widgets []Widget, constraints *LayoutConstraints) (*DashboardLayout, error) {
	// Convert to request format
	widgetsJSON, err := json.Marshal(widgets)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal widgets: %w", err)
	}
	
	constraintsJSON, err := json.Marshal(constraints)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal constraints: %w", err)
	}
	
	// Call gRPC service
	req := &pb.OptimizeLayoutRequest{
		Widgets:     string(widgetsJSON),
		Constraints: string(constraintsJSON),
	}
	
	resp, err := s.grpcClient.OptimizeLayout(ctx, req)
	if err != nil {
		return nil, fmt.Errorf("layout optimization failed: %w", err)
	}
	
	// Parse response
	var result DashboardLayout
	if err := json.Unmarshal([]byte(resp.Result), &result); err != nil {
		return nil, fmt.Errorf("failed to unmarshal result: %w", err)
	}
	
	return &result, nil
}

// Types for intelligence service results

// PatternAnalysisResult contains detected patterns
type PatternAnalysisResult struct {
	Patterns []Pattern              `json:"patterns"`
	Insights []string               `json:"insights"`
	Metadata map[string]interface{} `json:"metadata"`
}

// Pattern represents a detected pattern
type Pattern struct {
	Type       string                 `json:"type"`
	Confidence float64                `json:"confidence"`
	Evidence   map[string]interface{} `json:"evidence"`
	Columns    []string               `json:"columns"`
}

// QueryContext provides context for query generation
type QueryContext struct {
	AvailableSchemas []SchemaInfo           `json:"available_schemas"`
	CostConstraints  map[string]interface{} `json:"cost_constraints,omitempty"`
	UserPreferences  map[string]interface{} `json:"user_preferences,omitempty"`
}

// SchemaInfo describes available data schema
type SchemaInfo struct {
	Name           string   `json:"name"`
	RecordsPerHour int64    `json:"records_per_hour"`
	CommonFacets   []string `json:"common_facets"`
}

// QueryResult contains generated NRQL query
type QueryResult struct {
	NRQL         string                 `json:"nrql"`
	Confidence   float64                `json:"confidence"`
	EstimatedCost float64               `json:"estimated_cost,omitempty"`
	Warnings     []string               `json:"warnings,omitempty"`
	Suggestions  []string               `json:"suggestions,omitempty"`
	Alternatives []string               `json:"alternatives,omitempty"`
	Metadata     map[string]interface{} `json:"metadata"`
}

// ChartRecommendations contains chart suggestions
type ChartRecommendations struct {
	Recommendations []ChartRecommendation `json:"recommendations"`
}

// ChartRecommendation describes a recommended chart
type ChartRecommendation struct {
	ChartType    string                 `json:"chart_type"`
	Confidence   float64                `json:"confidence"`
	Reasoning    string                 `json:"reasoning"`
	Configuration map[string]interface{} `json:"configuration"`
	Advantages   []string               `json:"advantages"`
	Limitations  []string               `json:"limitations"`
}

// Widget represents a dashboard widget
type Widget struct {
	ID        string                 `json:"id"`
	Title     string                 `json:"title"`
	ChartType string                 `json:"chart_type"`
	DataQuery string                 `json:"data_query"`
	Size      string                 `json:"size,omitempty"`
	Priority  string                 `json:"priority,omitempty"`
}

// LayoutConstraints defines layout optimization constraints
type LayoutConstraints struct {
	MaxColumns      int  `json:"max_columns"`
	MaxRows         int  `json:"max_rows"`
	MobileFriendly  bool `json:"mobile_friendly"`
	TabletFriendly  bool `json:"tablet_friendly"`
}

// DashboardLayout contains optimized layout
type DashboardLayout struct {
	Strategy   string            `json:"strategy"`
	Grid       GridDimensions    `json:"grid"`
	Placements []WidgetPlacement `json:"placements"`
	Metrics    LayoutMetrics     `json:"metrics"`
}

// GridDimensions defines dashboard grid size
type GridDimensions struct {
	Columns int `json:"columns"`
	Rows    int `json:"rows"`
}

// WidgetPlacement defines widget position
type WidgetPlacement struct {
	WidgetID string   `json:"widget_id"`
	Position Position `json:"position"`
	Size     Size     `json:"size"`
}

// Position defines x,y coordinates
type Position struct {
	X int `json:"x"`
	Y int `json:"y"`
}

// Size defines width and height
type Size struct {
	Width  int `json:"width"`
	Height int `json:"height"`
}

// LayoutMetrics contains layout quality metrics
type LayoutMetrics struct {
	SpaceUtilization  float64 `json:"space_utilization"`
	VisualBalance     float64 `json:"visual_balance"`
	RelationshipScore float64 `json:"relationship_score"`
	OverallScore      float64 `json:"overall_score"`
}