package grpc

import (
	"context"
	"encoding/json"
	"fmt"
	"net"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/telemetry"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/health"
	"google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
)

// DiscoveryServer implements a gRPC server for the discovery engine
type DiscoveryServer struct {
	engine *discovery.InstrumentedEngine
	tracer *telemetry.Tracer
	server *grpc.Server
}

// Config holds gRPC server configuration
type Config struct {
	Port              int
	MaxMessageSize    int
	ConnectionTimeout time.Duration
	EnableReflection  bool
	EnableHealth      bool
}

// DefaultConfig returns default gRPC configuration
func DefaultConfig() Config {
	return Config{
		Port:              8081,
		MaxMessageSize:    10 * 1024 * 1024, // 10MB
		ConnectionTimeout: 30 * time.Second,
		EnableReflection:  true,
		EnableHealth:      true,
	}
}

// NewDiscoveryServer creates a new gRPC server for discovery
func NewDiscoveryServer(engine *discovery.InstrumentedEngine, config Config) (*DiscoveryServer, error) {
	// Create tracer
	tracerConfig := telemetry.DefaultConfig()
	tracer, err := telemetry.NewTracer(tracerConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create tracer: %w", err)
	}

	// Create gRPC server with options
	opts := []grpc.ServerOption{
		grpc.MaxRecvMsgSize(config.MaxMessageSize),
		grpc.MaxSendMsgSize(config.MaxMessageSize),
		grpc.ConnectionTimeout(config.ConnectionTimeout),
		grpc.UnaryInterceptor(unaryInterceptor(tracer)),
		grpc.StreamInterceptor(streamInterceptor(tracer)),
	}

	server := grpc.NewServer(opts...)

	// Create discovery server
	ds := &DiscoveryServer{
		engine: engine,
		tracer: tracer,
		server: server,
	}

	// Register services
	RegisterDiscoveryServiceServer(server, ds)

	// Enable reflection for debugging
	if config.EnableReflection {
		reflection.Register(server)
	}

	// Enable health checks
	if config.EnableHealth {
		healthServer := health.NewServer()
		grpc_health_v1.RegisterHealthServer(server, healthServer)
		healthServer.SetServingStatus("discovery.DiscoveryService", grpc_health_v1.HealthCheckResponse_SERVING)
	}

	return ds, nil
}

// Start starts the gRPC server
func (s *DiscoveryServer) Start(port int) error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return fmt.Errorf("failed to listen: %w", err)
	}

	go func() {
		if err := s.server.Serve(lis); err != nil {
			fmt.Printf("gRPC server error: %v\n", err)
		}
	}()

	return nil
}

// Stop gracefully stops the server
func (s *DiscoveryServer) Stop(ctx context.Context) error {
	s.server.GracefulStop()
	return s.tracer.Shutdown(ctx)
}

// DiscoverSchemas implements the gRPC method
func (s *DiscoveryServer) DiscoverSchemas(ctx context.Context, req *DiscoverSchemasRequest) (*DiscoverSchemasResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.DiscoverSchemas")
	defer span.End()

	// Convert request to discovery filter
	filter := discovery.DiscoveryFilter{
		AccountID:   req.AccountID,
		Pattern:     req.Pattern,
		MaxSchemas:  int(req.MaxSchemas),
		EventTypes:  req.EventTypes,
		Tags:        req.Tags,
	}

	// Call engine
	start := time.Now()
	schemas, err := s.engine.DiscoverSchemas(ctx, filter)
	duration := time.Since(start)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Convert response
	resp := &DiscoverSchemasResponse{
		Schemas:           convertSchemas(schemas),
		TotalCount:        int32(len(schemas)),
		DiscoveryDuration: duration.Milliseconds(),
		Metadata: map[string]string{
			"trace_id": telemetry.ExtractTraceID(ctx),
		},
	}

	span.SetStatus(codes.Ok, "")
	return resp, nil
}

// ProfileSchema implements the gRPC method
func (s *DiscoveryServer) ProfileSchema(ctx context.Context, req *ProfileSchemaRequest) (*ProfileSchemaResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.ProfileSchema")
	defer span.End()

	// Convert profile depth
	depth := discovery.ProfileDepth(req.ProfileDepth)
	if depth == "" {
		depth = discovery.ProfileDepthStandard
	}

	// Call engine
	start := time.Now()
	schema, err := s.engine.ProfileSchema(ctx, req.EventType, depth)
	duration := time.Since(start)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Convert response
	resp := &ProfileSchemaResponse{
		Schema:            convertSchema(schema),
		ProfilingDuration: duration.Milliseconds(),
		Metadata: map[string]string{
			"trace_id": telemetry.ExtractTraceID(ctx),
		},
	}

	span.SetStatus(codes.Ok, "")
	return resp, nil
}

// IntelligentDiscovery implements the gRPC method
func (s *DiscoveryServer) IntelligentDiscovery(ctx context.Context, req *IntelligentDiscoveryRequest) (*IntelligentDiscoveryResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.IntelligentDiscovery")
	defer span.End()

	// Convert hints
	hints := discovery.DiscoveryHints{
		FocusAreas:          req.FocusAreas,
		EventTypes:          req.EventTypes,
		AnomalyDetection:    req.AnomalyDetection,
		PatternMining:       req.PatternMining,
		QualityAssessment:   req.QualityAssessment,
		ConfidenceThreshold: req.ConfidenceThreshold,
		Context:             req.Context,
	}

	// Call engine
	start := time.Now()
	schemas, err := s.engine.IntelligentDiscovery(ctx, hints)
	duration := time.Since(start)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Convert response
	resp := &IntelligentDiscoveryResponse{
		Schemas:           convertSchemas(schemas),
		DiscoveryDuration: duration.Milliseconds(),
		Insights:          generateInsights(schemas),
		Recommendations:   generateRecommendations(schemas),
	}

	span.SetStatus(codes.Ok, "")
	return resp, nil
}

// FindRelationships implements the gRPC method
func (s *DiscoveryServer) FindRelationships(ctx context.Context, req *FindRelationshipsRequest) (*FindRelationshipsResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.FindRelationships")
	defer span.End()

	// Get schemas for relationship discovery
	schemas := make([]discovery.Schema, 0, len(req.SchemaNames))
	for _, name := range req.SchemaNames {
		schema, err := s.engine.ProfileSchema(ctx, name, discovery.ProfileDepthBasic)
		if err != nil {
			continue // Skip schemas that can't be profiled
		}
		schemas = append(schemas, *schema)
	}

	// Call engine
	start := time.Now()
	relationships, err := s.engine.FindRelationships(ctx, schemas)
	duration := time.Since(start)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Convert response
	resp := &FindRelationshipsResponse{
		Relationships:    convertRelationships(relationships),
		Graph:            buildRelationshipGraph(schemas, relationships),
		AnalysisDuration: duration.Milliseconds(),
	}

	span.SetStatus(codes.Ok, "")
	return resp, nil
}

// AssessQuality implements the gRPC method
func (s *DiscoveryServer) AssessQuality(ctx context.Context, req *AssessQualityRequest) (*AssessQualityResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.AssessQuality")
	defer span.End()

	// Call engine
	start := time.Now()
	report, err := s.engine.AssessQuality(ctx, req.EventType)
	duration := time.Since(start)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Convert response
	resp := &AssessQualityResponse{
		Report:             convertQualityReport(report),
		AssessmentDuration: duration.Milliseconds(),
	}

	span.SetStatus(codes.Ok, "")
	return resp, nil
}

// GetHealth implements the gRPC method
func (s *DiscoveryServer) GetHealth(ctx context.Context, req *GetHealthRequest) (*GetHealthResponse, error) {
	ctx, span := s.tracer.Start(ctx, "grpc.GetHealth")
	defer span.End()

	health := s.engine.GetHealth(ctx)

	resp := &GetHealthResponse{
		IsHealthy: health.IsHealthy,
		Status:    health.Status,
		Timestamp: time.Now().Unix(),
		Checks:    convertHealthChecks(health),
	}

	if req.IncludeMetrics {
		resp.Metrics = &HealthMetrics{
			QueriesProcessed:   health.QueriesProcessed,
			ErrorsCount:        health.ErrorsCount,
			CacheHitRate:       health.CacheHitRate,
			Uptime:             int64(health.Uptime.Seconds()),
			AverageQueryTimeMs: health.AverageQueryTime.Milliseconds(),
		}
	}

	if health.IsHealthy {
		span.SetStatus(codes.Ok, "Healthy")
	} else {
		span.SetStatus(codes.Error, health.LastError)
	}

	return resp, nil
}

// Helper functions for conversions

func convertSchemas(schemas []discovery.Schema) []*Schema {
	result := make([]*Schema, len(schemas))
	for i, s := range schemas {
		result[i] = convertSchema(&s)
	}
	return result
}

func convertSchema(s *discovery.Schema) *Schema {
	if s == nil {
		return nil
	}

	metadata, _ := json.Marshal(s.Metadata)
	
	return &Schema{
		Id:             s.ID,
		Name:           s.Name,
		EventType:      s.EventType,
		Attributes:     convertAttributes(s.Attributes),
		SampleCount:    s.SampleCount,
		DataVolume:     convertDataVolume(s.DataVolume),
		Quality:        convertQualityMetrics(s.Quality),
		Patterns:       convertPatterns(s.Patterns),
		DiscoveredAt:   s.DiscoveredAt.Unix(),
		LastAnalyzedAt: s.LastAnalyzedAt.Unix(),
		Metadata:       string(metadata),
	}
}

func convertAttributes(attrs []discovery.Attribute) []*Attribute {
	result := make([]*Attribute, len(attrs))
	for i, a := range attrs {
		result[i] = &Attribute{
			Name:         a.Name,
			DataType:     string(a.DataType),
			SemanticType: string(a.SemanticType),
			IsRequired:   a.IsRequired,
			IsUnique:     a.IsUnique,
			IsIndexed:    a.IsIndexed,
			Cardinality:  a.Cardinality,
			SampleValues: a.SampleValues,
		}
	}
	return result
}

func convertDataVolume(dv discovery.DataVolumeProfile) *DataVolumeProfile {
	return &DataVolumeProfile{
		TotalEvents:      dv.TotalEvents,
		EventsPerMinute:  dv.EventsPerMinute,
		DataSizeBytes:    dv.DataSizeBytes,
		FirstSeen:        dv.FirstSeen.Unix(),
		LastSeen:         dv.LastSeen.Unix(),
	}
}

func convertQualityMetrics(qm discovery.QualityMetrics) *QualityMetrics {
	return &QualityMetrics{
		OverallScore: qm.OverallScore,
		Dimensions:   convertQualityDimensions(qm.Dimensions),
		Issues:       convertQualityIssues(qm.Issues),
	}
}

func convertQualityDimensions(qd discovery.QualityDimensions) *QualityDimensions {
	return &QualityDimensions{
		Completeness: convertQualityDimension(qd.Completeness),
		Consistency:  convertQualityDimension(qd.Consistency),
		Timeliness:   convertQualityDimension(qd.Timeliness),
		Uniqueness:   convertQualityDimension(qd.Uniqueness),
		Validity:     convertQualityDimension(qd.Validity),
	}
}

func convertQualityDimension(qd discovery.QualityDimension) *QualityDimension {
	return &QualityDimension{
		Score:  qd.Score,
		Issues: qd.Issues,
	}
}

func convertQualityIssues(issues []discovery.QualityIssue) []*QualityIssue {
	result := make([]*QualityIssue, len(issues))
	for i, issue := range issues {
		result[i] = &QualityIssue{
			Severity:           string(issue.Severity),
			Type:               string(issue.Type),
			Description:        issue.Description,
			AffectedAttributes: issue.AffectedAttributes,
			OccurrenceCount:    issue.OccurrenceCount,
		}
	}
	return result
}

func convertPatterns(patterns []discovery.DetectedPattern) []*DetectedPattern {
	result := make([]*DetectedPattern, len(patterns))
	for i, p := range patterns {
		params, _ := json.Marshal(p.Parameters)
		result[i] = &DetectedPattern{
			Type:               string(p.Type),
			Subtype:            p.Subtype,
			Confidence:         p.Confidence,
			Description:        p.Description,
			Parameters:         string(params),
			AffectedAttributes: p.AffectedAttributes,
		}
	}
	return result
}

func convertRelationships(relationships []discovery.Relationship) []*Relationship {
	result := make([]*Relationship, len(relationships))
	for i, r := range relationships {
		result[i] = &Relationship{
			Id:              r.ID,
			Type:            string(r.Type),
			SourceSchema:    r.SourceSchema,
			TargetSchema:    r.TargetSchema,
			JoinConditions:  convertJoinConditions(r.JoinConditions),
			Strength:        r.Strength,
			Confidence:      r.Confidence,
			SampleMatches:   r.SampleMatches,
		}
	}
	return result
}

func convertJoinConditions(conditions []discovery.JoinCondition) []*JoinCondition {
	result := make([]*JoinCondition, len(conditions))
	for i, c := range conditions {
		result[i] = &JoinCondition{
			SourceAttribute: c.SourceAttribute,
			TargetAttribute: c.TargetAttribute,
			Operator:        c.Operator,
		}
	}
	return result
}

func convertQualityReport(report *discovery.QualityReport) *QualityReport {
	if report == nil {
		return nil
	}
	
	metadata, _ := json.Marshal(report.Metadata)
	
	return &QualityReport{
		EventType:    report.EventType,
		OverallScore: report.OverallScore,
		Dimensions:   convertQualityDimensions(report.Dimensions),
		Issues:       convertQualityIssues(report.Issues),
		AssessedAt:   report.AssessedAt.Unix(),
		Metadata:     string(metadata),
	}
}

func convertHealthChecks(health *discovery.HealthStatus) []*HealthCheck {
	checks := []*HealthCheck{
		{
			Name:      "engine",
			IsHealthy: health.IsHealthy,
			Message:   health.Status,
		},
		{
			Name:      "cache",
			IsHealthy: health.CacheHitRate > 0.5,
			Message:   fmt.Sprintf("Hit rate: %.2f", health.CacheHitRate),
		},
	}
	return checks
}

func generateInsights(schemas []discovery.Schema) []*DiscoveryInsight {
	// This would analyze schemas and generate insights
	// For now, return empty
	return []*DiscoveryInsight{}
}

func generateRecommendations(schemas []discovery.Schema) []string {
	// This would analyze schemas and generate recommendations
	// For now, return empty
	return []string{}
}

func buildRelationshipGraph(schemas []discovery.Schema, relationships []discovery.Relationship) *RelationshipGraph {
	// Build graph representation
	nodes := make([]*GraphNode, len(schemas))
	for i, s := range schemas {
		nodes[i] = &GraphNode{
			Id:         s.ID,
			SchemaName: s.Name,
		}
	}

	edges := make([]*GraphEdge, len(relationships))
	for i, r := range relationships {
		edges[i] = &GraphEdge{
			Source:         r.SourceSchema,
			Target:         r.TargetSchema,
			RelationshipId: r.ID,
			Weight:         r.Strength,
		}
	}

	return &RelationshipGraph{
		Nodes: nodes,
		Edges: edges,
	}
}

// Interceptors for tracing

func unaryInterceptor(tracer *telemetry.Tracer) grpc.UnaryServerInterceptor {
	return func(ctx context.Context, req interface{}, info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
		ctx, span := tracer.Start(ctx, info.FullMethod,
			trace.WithAttributes(
				attribute.String("rpc.system", "grpc"),
				attribute.String("rpc.method", info.FullMethod),
				attribute.String("rpc.service", "discovery"),
			),
			trace.WithSpanKind(trace.SpanKindServer),
		)
		defer span.End()

		resp, err := handler(ctx, req)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		} else {
			span.SetStatus(codes.Ok, "")
		}

		return resp, err
	}
}

func streamInterceptor(tracer *telemetry.Tracer) grpc.StreamServerInterceptor {
	return func(srv interface{}, ss grpc.ServerStream, info *grpc.StreamServerInfo, handler grpc.StreamHandler) error {
		ctx, span := tracer.Start(ss.Context(), info.FullMethod,
			trace.WithAttributes(
				attribute.String("rpc.system", "grpc"),
				attribute.String("rpc.method", info.FullMethod),
				attribute.String("rpc.service", "discovery"),
				attribute.Bool("rpc.stream", true),
			),
			trace.WithSpanKind(trace.SpanKindServer),
		)
		defer span.End()

		wrapped := &wrappedServerStream{
			ServerStream: ss,
			ctx:          ctx,
		}

		err := handler(srv, wrapped)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		} else {
			span.SetStatus(codes.Ok, "")
		}

		return err
	}
}

type wrappedServerStream struct {
	grpc.ServerStream
	ctx context.Context
}

func (w *wrappedServerStream) Context() context.Context {
	return w.ctx
}