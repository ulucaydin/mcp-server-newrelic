package telemetry

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/codes"
	"go.opentelemetry.io/otel/trace"
)

// HTTPMiddleware creates an HTTP middleware for tracing
func HTTPMiddleware(tracer *Tracer, next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Extract parent context from headers
		ctx := r.Context()
		
		// Start span
		spanName := fmt.Sprintf("%s %s", r.Method, r.URL.Path)
		ctx, span := tracer.Start(ctx, spanName,
			trace.WithAttributes(
				attribute.String("http.method", r.Method),
				attribute.String("http.url", r.URL.String()),
				attribute.String("http.path", r.URL.Path),
				attribute.String("http.host", r.Host),
				attribute.String("http.user_agent", r.UserAgent()),
			),
			trace.WithSpanKind(trace.SpanKindServer),
		)
		defer span.End()

		// Wrap response writer to capture status code
		wrapped := &responseWriter{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		// Process request
		start := time.Now()
		next.ServeHTTP(wrapped, r.WithContext(ctx))
		duration := time.Since(start)

		// Set span attributes
		span.SetAttributes(
			attribute.Int("http.status_code", wrapped.statusCode),
			attribute.Int64("http.duration_ms", duration.Milliseconds()),
		)

		// Set span status based on HTTP status code
		if wrapped.statusCode >= 400 {
			span.SetStatus(codes.Error, http.StatusText(wrapped.statusCode))
		} else {
			span.SetStatus(codes.Ok, "")
		}
	})
}

// responseWriter wraps http.ResponseWriter to capture status code
type responseWriter struct {
	http.ResponseWriter
	statusCode int
}

func (rw *responseWriter) WriteHeader(code int) {
	rw.statusCode = code
	rw.ResponseWriter.WriteHeader(code)
}

// InstrumentHandler wraps a handler function with tracing
func InstrumentHandler(tracer *Tracer, spanName string, handler func(context.Context) error) func(context.Context) error {
	return func(ctx context.Context) error {
		ctx, span := tracer.Start(ctx, spanName)
		defer span.End()

		err := handler(ctx)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		} else {
			span.SetStatus(codes.Ok, "")
		}

		return err
	}
}

// InstrumentHandlerWithResult wraps a handler that returns a result
func InstrumentHandlerWithResult[T any](tracer *Tracer, spanName string, handler func(context.Context) (T, error)) func(context.Context) (T, error) {
	return func(ctx context.Context) (T, error) {
		ctx, span := tracer.Start(ctx, spanName)
		defer span.End()

		result, err := handler(ctx)
		if err != nil {
			span.RecordError(err)
			span.SetStatus(codes.Error, err.Error())
		} else {
			span.SetStatus(codes.Ok, "")
		}

		return result, err
	}
}

// WithSpan executes a function within a span
func WithSpan(ctx context.Context, tracer *Tracer, spanName string, fn func(context.Context) error) error {
	ctx, span := tracer.Start(ctx, spanName)
	defer span.End()

	err := fn(ctx)
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
	} else {
		span.SetStatus(codes.Ok, "")
	}

	return err
}

// WithSpanResult executes a function within a span and returns a result
func WithSpanResult[T any](ctx context.Context, tracer *Tracer, spanName string, fn func(context.Context) (T, error)) (T, error) {
	ctx, span := tracer.Start(ctx, spanName)
	defer span.End()

	result, err := fn(ctx)
	if err != nil {
		span.RecordError(err)
		span.SetStatus(codes.Error, err.Error())
	} else {
		span.SetStatus(codes.Ok, "")
	}

	return result, err
}

// MeasureLatency measures and records latency as a span attribute
func MeasureLatency(span trace.Span, start time.Time, attrName string) {
	if span.IsRecording() {
		duration := time.Since(start)
		span.SetAttributes(attribute.Int64(attrName, duration.Milliseconds()))
	}
}

// RecordCount records a count metric as a span attribute
func RecordCount(span trace.Span, attrName string, count int) {
	if span.IsRecording() {
		span.SetAttributes(attribute.Int(attrName, count))
	}
}

// RecordSize records a size metric as a span attribute
func RecordSize(span trace.Span, attrName string, size int64) {
	if span.IsRecording() {
		span.SetAttributes(attribute.Int64(attrName, size))
	}
}

// RecordBool records a boolean metric as a span attribute
func RecordBool(span trace.Span, attrName string, value bool) {
	if span.IsRecording() {
		span.SetAttributes(attribute.Bool(attrName, value))
	}
}

// ExtractTraceID extracts the trace ID from context
func ExtractTraceID(ctx context.Context) string {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		return span.SpanContext().TraceID().String()
	}
	return ""
}

// ExtractSpanID extracts the span ID from context
func ExtractSpanID(ctx context.Context) string {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		return span.SpanContext().SpanID().String()
	}
	return ""
}