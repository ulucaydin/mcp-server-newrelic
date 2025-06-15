package discovery

import (
	"context"
	"fmt"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/telemetry"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// InstrumentedEngine wraps the discovery engine with OpenTelemetry tracing
type InstrumentedEngine struct {
	engine *Engine
	tracer *telemetry.Tracer
}

// NewInstrumentedEngine creates a new instrumented discovery engine
func NewInstrumentedEngine(config *Config) (*InstrumentedEngine, error) {
	// Initialize tracer
	tracerConfig := telemetry.DefaultConfig()
	tracer, err := telemetry.NewTracer(tracerConfig)
	if err != nil {
		return nil, fmt.Errorf("failed to create tracer: %w", err)
	}

	// Create underlying engine
	engine, err := NewEngine(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create engine: %w", err)
	}

	return &InstrumentedEngine{
		engine: engine,
		tracer: tracer,
	}, nil
}

// DiscoverSchemas discovers available schemas with tracing
func (ie *InstrumentedEngine) DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanDiscoverSchemas,
		trace.WithAttributes(
			attribute.String(telemetry.AttrAccountID, filter.AccountID),
			attribute.Int("filter.max_schemas", filter.MaxSchemas),
			attribute.String("filter.pattern", filter.Pattern),
		),
	)
	defer span.End()

	start := time.Now()
	schemas, err := ie.engine.DiscoverSchemas(ctx, filter)
	
	// Record metrics
	span.SetAttributes(
		attribute.Int(telemetry.AttrSchemaCount, len(schemas)),
		attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
	)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return schemas, nil
}

// ProfileSchema profiles a specific schema with tracing
func (ie *InstrumentedEngine) ProfileSchema(ctx context.Context, eventType string, depth ProfileDepth) (*Schema, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanProfileSchema,
		trace.WithAttributes(
			attribute.String(telemetry.AttrEventType, eventType),
			attribute.String(telemetry.AttrProfileDepth, string(depth)),
		),
	)
	defer span.End()

	start := time.Now()
	schema, err := ie.engine.ProfileSchema(ctx, eventType, depth)
	
	if schema != nil {
		span.SetAttributes(
			attribute.String(telemetry.AttrSchemaName, schema.Name),
			attribute.Int("attribute_count", len(schema.Attributes)),
			attribute.Int64("sample_count", schema.SampleCount),
			attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
		)
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return schema, nil
}

// IntelligentDiscovery performs intelligent schema discovery with tracing
func (ie *InstrumentedEngine) IntelligentDiscovery(ctx context.Context, hints DiscoveryHints) ([]Schema, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanIntelligentDiscovery,
		trace.WithAttributes(
			attribute.StringSlice("hints.focus_areas", hints.FocusAreas),
			attribute.StringSlice("hints.event_types", hints.EventTypes),
			attribute.Bool("hints.anomaly_detection", hints.AnomalyDetection),
		),
	)
	defer span.End()

	start := time.Now()
	schemas, err := ie.engine.IntelligentDiscovery(ctx, hints)
	
	span.SetAttributes(
		attribute.Int(telemetry.AttrSchemaCount, len(schemas)),
		attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
	)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return schemas, nil
}

// FindRelationships discovers relationships between schemas with tracing
func (ie *InstrumentedEngine) FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanFindRelationships,
		trace.WithAttributes(
			attribute.Int("schema_count", len(schemas)),
		),
	)
	defer span.End()

	start := time.Now()
	relationships, err := ie.engine.FindRelationships(ctx, schemas)
	
	span.SetAttributes(
		attribute.Int("relationship_count", len(relationships)),
		attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
	)

	// Record relationship types found
	typeCount := make(map[RelationshipType]int)
	for _, rel := range relationships {
		typeCount[rel.Type]++
	}
	for relType, count := range typeCount {
		span.SetAttributes(attribute.Int(fmt.Sprintf("relationships.%s", relType), count))
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return relationships, nil
}

// AssessQuality assesses data quality for a schema with tracing
func (ie *InstrumentedEngine) AssessQuality(ctx context.Context, eventType string) (*QualityReport, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanAssessQuality,
		trace.WithAttributes(
			attribute.String(telemetry.AttrEventType, eventType),
		),
	)
	defer span.End()

	start := time.Now()
	report, err := ie.engine.AssessQuality(ctx, eventType)
	
	if report != nil {
		span.SetAttributes(
			attribute.Float64(telemetry.AttrQualityScore, report.OverallScore),
			attribute.Float64("quality.completeness", report.Dimensions.Completeness.Score),
			attribute.Float64("quality.consistency", report.Dimensions.Consistency.Score),
			attribute.Float64("quality.timeliness", report.Dimensions.Timeliness.Score),
			attribute.Float64("quality.uniqueness", report.Dimensions.Uniqueness.Score),
			attribute.Float64("quality.validity", report.Dimensions.Validity.Score),
			attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
		)
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return report, nil
}

// GetHealth returns engine health status with tracing
func (ie *InstrumentedEngine) GetHealth(ctx context.Context) *HealthStatus {
	ctx, span := ie.tracer.Start(ctx, "discovery.engine.health")
	defer span.End()

	health := ie.engine.GetHealth(ctx)
	
	span.SetAttributes(
		attribute.Bool("health.is_healthy", health.IsHealthy),
		attribute.Int64("health.queries_processed", health.QueriesProcessed),
		attribute.Int64("health.errors_count", health.ErrorsCount),
		attribute.Float64("health.cache_hit_rate", health.CacheHitRate),
		attribute.Int64("health.uptime_seconds", int64(health.Uptime.Seconds())),
	)

	if health.IsHealthy {
		span.SetStatus(codes.Ok, "Engine is healthy")
	} else {
		span.SetStatus(codes.Error, health.LastError)
	}

	return health
}

// DetectPatterns detects patterns in schema data with tracing
func (ie *InstrumentedEngine) DetectPatterns(ctx context.Context, schema Schema) ([]DetectedPattern, error) {
	ctx, span := ie.tracer.Start(ctx, telemetry.SpanDetectPatterns,
		trace.WithAttributes(
			attribute.String(telemetry.AttrSchemaName, schema.Name),
			attribute.Int("attribute_count", len(schema.Attributes)),
		),
	)
	defer span.End()

	start := time.Now()
	patterns, err := ie.engine.detectPatterns(ctx, schema)
	
	span.SetAttributes(
		attribute.Int("pattern_count", len(patterns)),
		attribute.Int64(telemetry.AttrQueryDuration, time.Since(start).Milliseconds()),
	)

	// Record pattern types found
	typeCount := make(map[PatternType]int)
	for _, pattern := range patterns {
		typeCount[pattern.Type]++
		if pattern.Confidence > 0 {
			span.SetAttributes(
				attribute.Float64(fmt.Sprintf("pattern.%s.confidence", pattern.Type), pattern.Confidence),
			)
		}
	}
	for patternType, count := range typeCount {
		span.SetAttributes(attribute.Int(fmt.Sprintf("patterns.%s", patternType), count))
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return patterns, nil
}

// Start starts the instrumented engine
func (ie *InstrumentedEngine) Start(ctx context.Context) error {
	ctx, span := ie.tracer.Start(ctx, "discovery.engine.start")
	defer span.End()

	err := ie.engine.Start(ctx)
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return err
	}

	span.SetStatus(codes.Ok, "Engine started successfully")
	return nil
}

// Stop stops the instrumented engine and shuts down tracing
func (ie *InstrumentedEngine) Stop(ctx context.Context) error {
	ctx, span := ie.tracer.Start(ctx, "discovery.engine.stop")
	defer span.End()

	// Stop engine first
	engineErr := ie.engine.Stop(ctx)
	if engineErr != nil {
		span.RecordError(engineErr)
	}

	// Shutdown tracer
	tracerErr := ie.tracer.Shutdown(ctx)
	if tracerErr != nil {
		span.RecordError(tracerErr)
	}

	if engineErr != nil || tracerErr != nil {
		span.SetStatus(codes.Error, "Failed to stop cleanly")
		if engineErr != nil {
			return engineErr
		}
		return tracerErr
	}

	span.SetStatus(codes.Ok, "Engine stopped successfully")
	return nil
}

// SetNRDBClient sets the NRDB client (pass-through to underlying engine)
func (ie *InstrumentedEngine) SetNRDBClient(client NRDBClient) {
	ie.engine.SetNRDBClient(client)
}