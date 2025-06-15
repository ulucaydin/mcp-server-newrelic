package telemetry

import (
	"context"
	"fmt"
	"os"
	"time"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.17.0"
	"go.opentelemetry.io/otel/trace"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// Tracer provides OpenTelemetry tracing functionality
type Tracer struct {
	tracer   trace.Tracer
	provider *sdktrace.TracerProvider
}

// Config holds tracer configuration
type Config struct {
	ServiceName    string
	ServiceVersion string
	Environment    string
	Endpoint       string
	Headers        map[string]string
	Insecure       bool
	SampleRate     float64
}

// DefaultConfig returns default tracer configuration from environment
func DefaultConfig() Config {
	endpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
	if endpoint == "" {
		endpoint = "https://otlp.nr-data.net:4317"
	}

	return Config{
		ServiceName:    getEnvOrDefault("OTEL_SERVICE_NAME", "mcp-server-newrelic-discovery"),
		ServiceVersion: getEnvOrDefault("SERVICE_VERSION", "1.0.0"),
		Environment:    getEnvOrDefault("ENVIRONMENT", "development"),
		Endpoint:       endpoint,
		Headers:        parseHeaders(os.Getenv("OTEL_EXPORTER_OTLP_HEADERS")),
		Insecure:       os.Getenv("OTEL_EXPORTER_OTLP_INSECURE") == "true",
		SampleRate:     1.0, // Sample all traces by default
	}
}

// NewTracer creates a new OpenTelemetry tracer
func NewTracer(config Config) (*Tracer, error) {
	// Create resource
	res, err := resource.Merge(
		resource.Default(),
		resource.NewWithAttributes(
			semconv.SchemaURL,
			semconv.ServiceNameKey.String(config.ServiceName),
			semconv.ServiceVersionKey.String(config.ServiceVersion),
			attribute.String("environment", config.Environment),
			attribute.String("service.namespace", "discovery"),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Create OTLP exporter
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	opts := []otlptracegrpc.Option{
		otlptracegrpc.WithEndpoint(config.Endpoint),
		otlptracegrpc.WithHeaders(config.Headers),
	}

	if config.Insecure {
		opts = append(opts, otlptracegrpc.WithDialOption(grpc.WithTransportCredentials(insecure.NewCredentials())))
	}

	client := otlptracegrpc.NewClient(opts...)
	exporter, err := otlptrace.New(ctx, client)
	if err != nil {
		return nil, fmt.Errorf("failed to create exporter: %w", err)
	}

	// Create trace provider
	provider := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.TraceIDRatioBased(config.SampleRate)),
	)

	// Register as global provider
	otel.SetTracerProvider(provider)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	return &Tracer{
		tracer:   provider.Tracer(config.ServiceName),
		provider: provider,
	}, nil
}

// Shutdown gracefully shuts down the tracer
func (t *Tracer) Shutdown(ctx context.Context) error {
	return t.provider.Shutdown(ctx)
}

// Start begins a new span
func (t *Tracer) Start(ctx context.Context, spanName string, opts ...trace.SpanStartOption) (context.Context, trace.Span) {
	return t.tracer.Start(ctx, spanName, opts...)
}

// StartWithAttributes begins a new span with attributes
func (t *Tracer) StartWithAttributes(ctx context.Context, spanName string, attrs map[string]interface{}) (context.Context, trace.Span) {
	spanAttrs := make([]attribute.KeyValue, 0, len(attrs))
	for k, v := range attrs {
		spanAttrs = append(spanAttrs, attributeFromValue(k, v))
	}
	
	return t.tracer.Start(ctx, spanName, trace.WithAttributes(spanAttrs...))
}

// RecordError records an error on the current span
func RecordError(ctx context.Context, err error, attrs ...attribute.KeyValue) {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		span.RecordError(err, trace.WithAttributes(attrs...))
	}
}

// SetAttributes sets attributes on the current span
func SetAttributes(ctx context.Context, attrs map[string]interface{}) {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		spanAttrs := make([]attribute.KeyValue, 0, len(attrs))
		for k, v := range attrs {
			spanAttrs = append(spanAttrs, attributeFromValue(k, v))
		}
		span.SetAttributes(spanAttrs...)
	}
}

// SetStatus sets the status of the current span
func SetStatus(ctx context.Context, code trace.StatusCode, description string) {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		span.SetStatus(code, description)
	}
}

// Helper functions

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func parseHeaders(headerStr string) map[string]string {
	headers := make(map[string]string)
	if headerStr == "" {
		return headers
	}

	// Parse headers in format "key1=value1,key2=value2"
	pairs := splitByComma(headerStr)
	for _, pair := range pairs {
		if idx := indexOf(pair, '='); idx > 0 {
			key := pair[:idx]
			value := pair[idx+1:]
			headers[key] = value
		}
	}
	return headers
}

func splitByComma(s string) []string {
	var result []string
	var current string
	for _, r := range s {
		if r == ',' {
			if current != "" {
				result = append(result, current)
				current = ""
			}
		} else {
			current += string(r)
		}
	}
	if current != "" {
		result = append(result, current)
	}
	return result
}

func indexOf(s string, c rune) int {
	for i, r := range s {
		if r == c {
			return i
		}
	}
	return -1
}

func attributeFromValue(key string, value interface{}) attribute.KeyValue {
	switch v := value.(type) {
	case string:
		return attribute.String(key, v)
	case int:
		return attribute.Int(key, v)
	case int64:
		return attribute.Int64(key, v)
	case float64:
		return attribute.Float64(key, v)
	case bool:
		return attribute.Bool(key, v)
	case []string:
		return attribute.StringSlice(key, v)
	case []int:
		return attribute.IntSlice(key, v)
	case []int64:
		return attribute.Int64Slice(key, v)
	case []float64:
		return attribute.Float64Slice(key, v)
	case []bool:
		return attribute.BoolSlice(key, v)
	default:
		return attribute.String(key, fmt.Sprintf("%v", v))
	}
}

// Span names for consistency
const (
	SpanDiscoverSchemas      = "discovery.schemas.discover"
	SpanProfileSchema        = "discovery.schema.profile"
	SpanIntelligentDiscovery = "discovery.intelligent.discover"
	SpanFindRelationships    = "discovery.relationships.find"
	SpanAssessQuality        = "discovery.quality.assess"
	SpanDetectPatterns       = "discovery.patterns.detect"
	SpanNRDBQuery            = "nrdb.query"
	SpanCacheGet             = "cache.get"
	SpanCacheSet             = "cache.set"
	SpanWorkerProcess        = "worker.process"
)

// Attribute keys for consistency
const (
	AttrSchemaCount       = "discovery.schema.count"
	AttrSchemaName        = "discovery.schema.name"
	AttrEventType         = "discovery.event.type"
	AttrAccountID         = "discovery.account.id"
	AttrProfileDepth      = "discovery.profile.depth"
	AttrPatternType       = "discovery.pattern.type"
	AttrPatternConfidence = "discovery.pattern.confidence"
	AttrQualityScore      = "discovery.quality.score"
	AttrCacheHit          = "cache.hit"
	AttrQueryDuration     = "query.duration.ms"
	AttrWorkerID          = "worker.id"
	AttrBatchSize         = "batch.size"
	AttrErrorType         = "error.type"
	AttrRetryCount        = "retry.count"
)