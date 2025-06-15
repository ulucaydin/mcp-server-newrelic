package nrdb

import (
	"context"
	"fmt"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/telemetry"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// InstrumentedClient wraps an NRDB client with OpenTelemetry tracing
type InstrumentedClient struct {
	client discovery.NRDBClient
	tracer *telemetry.Tracer
}

// NewInstrumentedClient creates a new instrumented NRDB client
func NewInstrumentedClient(client discovery.NRDBClient, tracer *telemetry.Tracer) *InstrumentedClient {
	return &InstrumentedClient{
		client: client,
		tracer: tracer,
	}
}

// Query executes a NRQL query with tracing
func (ic *InstrumentedClient) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	ctx, span := ic.tracer.Start(ctx, telemetry.SpanNRDBQuery,
		trace.WithAttributes(
			attribute.String("nrdb.query", truncateQuery(nrql)),
			attribute.Int("nrdb.query.length", len(nrql)),
		),
	)
	defer span.End()

	start := time.Now()
	result, err := ic.client.Query(ctx, nrql)
	duration := time.Since(start)

	span.SetAttributes(
		attribute.Int64(telemetry.AttrQueryDuration, duration.Milliseconds()),
	)

	if result != nil {
		span.SetAttributes(
			attribute.Int("nrdb.result.count", len(result.Results)),
		)
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		
		// Categorize error type
		errorType := categorizeError(err)
		span.SetAttributes(attribute.String(telemetry.AttrErrorType, errorType))
		
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return result, nil
}

// QueryWithOptions executes a NRQL query with options and tracing
func (ic *InstrumentedClient) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	ctx, span := ic.tracer.Start(ctx, telemetry.SpanNRDBQuery,
		trace.WithAttributes(
			attribute.String("nrdb.query", truncateQuery(nrql)),
			attribute.Int("nrdb.query.length", len(nrql)),
			attribute.String("nrdb.account_id", opts.AccountID),
			attribute.Int64("nrdb.timeout_ms", opts.Timeout.Milliseconds()),
			attribute.Int("nrdb.limit", opts.Limit),
		),
	)
	defer span.End()

	start := time.Now()
	result, err := ic.client.QueryWithOptions(ctx, nrql, opts)
	duration := time.Since(start)

	span.SetAttributes(
		attribute.Int64(telemetry.AttrQueryDuration, duration.Milliseconds()),
	)

	if result != nil {
		span.SetAttributes(
			attribute.Int("nrdb.result.count", len(result.Results)),
		)
		
		// Add metadata if present
		if result.Metadata != nil {
			if facets, ok := result.Metadata["facets"].([]interface{}); ok {
				span.SetAttributes(attribute.Int("nrdb.result.facet_count", len(facets)))
			}
			if totalResult, ok := result.Metadata["totalResult"].(map[string]interface{}); ok {
				if count, ok := totalResult["count"].(float64); ok {
					span.SetAttributes(attribute.Float64("nrdb.result.total_count", count))
				}
			}
		}
	}

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		
		// Categorize error type
		errorType := categorizeError(err)
		span.SetAttributes(attribute.String(telemetry.AttrErrorType, errorType))
		
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return result, nil
}

// GetEventTypes retrieves available event types with tracing
func (ic *InstrumentedClient) GetEventTypes(ctx context.Context, filter discovery.EventTypeFilter) ([]string, error) {
	ctx, span := ic.tracer.Start(ctx, "nrdb.get_event_types",
		trace.WithAttributes(
			attribute.String("filter.account_id", filter.AccountID),
			attribute.String("filter.pattern", filter.Pattern),
			attribute.Int("filter.limit", filter.Limit),
		),
	)
	defer span.End()

	start := time.Now()
	eventTypes, err := ic.client.GetEventTypes(ctx, filter)
	duration := time.Since(start)

	span.SetAttributes(
		attribute.Int64(telemetry.AttrQueryDuration, duration.Milliseconds()),
		attribute.Int("event_type.count", len(eventTypes)),
	)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	span.SetStatus(codes.Ok, "")
	return eventTypes, nil
}

// GetAccounts retrieves available accounts with tracing
func (ic *InstrumentedClient) GetAccounts(ctx context.Context) ([]discovery.Account, error) {
	ctx, span := ic.tracer.Start(ctx, "nrdb.get_accounts")
	defer span.End()

	start := time.Now()
	accounts, err := ic.client.GetAccounts(ctx)
	duration := time.Since(start)

	span.SetAttributes(
		attribute.Int64(telemetry.AttrQueryDuration, duration.Milliseconds()),
		attribute.Int("account.count", len(accounts)),
	)

	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
		return nil, err
	}

	// Record account IDs (if not too many)
	if len(accounts) <= 10 {
		accountIDs := make([]string, len(accounts))
		for i, acc := range accounts {
			accountIDs[i] = acc.AccountID
		}
		span.SetAttributes(attribute.StringSlice("account.ids", accountIDs))
	}

	span.SetStatus(codes.Ok, "")
	return accounts, nil
}

// Helper functions

// truncateQuery truncates long queries for span attributes
func truncateQuery(query string) string {
	const maxLength = 500
	if len(query) <= maxLength {
		return query
	}
	return query[:maxLength] + "..."
}

// categorizeError categorizes errors for better observability
func categorizeError(err error) string {
	if err == nil {
		return "none"
	}
	
	errStr := err.Error()
	switch {
	case contains(errStr, "timeout"):
		return "timeout"
	case contains(errStr, "rate limit"):
		return "rate_limit"
	case contains(errStr, "unauthorized") || contains(errStr, "401"):
		return "auth"
	case contains(errStr, "not found") || contains(errStr, "404"):
		return "not_found"
	case contains(errStr, "validation") || contains(errStr, "invalid"):
		return "validation"
	case contains(errStr, "connection") || contains(errStr, "network"):
		return "network"
	case contains(errStr, "circuit"):
		return "circuit_breaker"
	default:
		return "unknown"
	}
}

func contains(s, substr string) bool {
	return len(s) >= len(substr) && indexOf(s, substr) >= 0
}

func indexOf(s, substr string) int {
	for i := 0; i <= len(s)-len(substr); i++ {
		if s[i:i+len(substr)] == substr {
			return i
		}
	}
	return -1
}

// InstrumentedClientWithCircuitBreaker combines instrumentation with circuit breaker
type InstrumentedClientWithCircuitBreaker struct {
	*InstrumentedClient
	circuitBreaker *CircuitBreaker
}

// NewInstrumentedClientWithCircuitBreaker creates a client with both tracing and circuit breaker
func NewInstrumentedClientWithCircuitBreaker(baseClient discovery.NRDBClient, tracer *telemetry.Tracer, cbConfig CircuitBreakerConfig) *InstrumentedClientWithCircuitBreaker {
	// Wrap with circuit breaker first
	cbClient := NewClientWithCircuitBreaker(baseClient, cbConfig)
	
	// Then wrap with instrumentation
	instrumentedClient := NewInstrumentedClient(cbClient, tracer)
	
	return &InstrumentedClientWithCircuitBreaker{
		InstrumentedClient: instrumentedClient,
		circuitBreaker:     cbClient.(*ClientWithCircuitBreaker).breaker,
	}
}

// Query with circuit breaker state tracking
func (ic *InstrumentedClientWithCircuitBreaker) Query(ctx context.Context, nrql string) (*discovery.QueryResult, error) {
	// Add circuit breaker state to span
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		span.SetAttributes(
			attribute.String("circuit_breaker.state", ic.circuitBreaker.State().String()),
			attribute.Int64("circuit_breaker.failures", int64(ic.circuitBreaker.Failures())),
		)
	}
	
	return ic.InstrumentedClient.Query(ctx, nrql)
}

// QueryWithOptions with circuit breaker state tracking
func (ic *InstrumentedClientWithCircuitBreaker) QueryWithOptions(ctx context.Context, nrql string, opts discovery.QueryOptions) (*discovery.QueryResult, error) {
	// Add circuit breaker state to span
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		span.SetAttributes(
			attribute.String("circuit_breaker.state", ic.circuitBreaker.State().String()),
			attribute.Int64("circuit_breaker.failures", int64(ic.circuitBreaker.Failures())),
		)
	}
	
	return ic.InstrumentedClient.QueryWithOptions(ctx, nrql, opts)
}