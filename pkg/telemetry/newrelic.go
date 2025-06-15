package telemetry

import (
	"fmt"
	"net/http"
	"os"
	
	"github.com/newrelic/go-agent/v3/newrelic"
)

// NewRelicConfig holds New Relic APM configuration
type NewRelicConfig struct {
	AppName    string
	LicenseKey string
	Enabled    bool
}

// InitNewRelic initializes New Relic APM
func InitNewRelic() (*newrelic.Application, error) {
	appName := os.Getenv("OTEL_SERVICE_NAME")
	if appName == "" {
		appName = "mcp-server-newrelic"
	}
	
	licenseKey := os.Getenv("NEW_RELIC_LICENSE_KEY")
	if licenseKey == "" {
		// Extract from OTEL headers if available
		headers := os.Getenv("OTEL_EXPORTER_OTLP_HEADERS")
		if headers != "" && len(headers) > 8 {
			// Parse Api-Key=xxx format
			if idx := len("Api-Key="); len(headers) > idx {
				licenseKey = headers[idx:]
			}
		}
	}
	
	if licenseKey == "" {
		return nil, fmt.Errorf("NEW_RELIC_LICENSE_KEY not set")
	}
	
	app, err := newrelic.NewApplication(
		newrelic.ConfigAppName(appName),
		newrelic.ConfigLicense(licenseKey),
		newrelic.ConfigDistributedTracerEnabled(true),
		newrelic.ConfigAppLogForwardingEnabled(true),
		func(cfg *newrelic.Config) {
			// Set environment from OTEL attributes
			if attrs := os.Getenv("OTEL_RESOURCE_ATTRIBUTES"); attrs != "" {
				// Parse environment from attributes
				cfg.Labels = parseAttributes(attrs)
			}
		},
	)
	
	if err != nil {
		return nil, fmt.Errorf("failed to create New Relic app: %w", err)
	}
	
	return app, nil
}

// parseAttributes parses OTEL resource attributes
func parseAttributes(attrs string) map[string]string {
	labels := make(map[string]string)
	// Simple parser for key=value,key=value format
	pairs := splitString(attrs, ',')
	for _, pair := range pairs {
		kv := splitString(pair, '=')
		if len(kv) == 2 {
			labels[kv[0]] = kv[1]
		}
	}
	return labels
}

// splitString is a simple string splitter
func splitString(s string, sep rune) []string {
	var result []string
	var current string
	
	for _, r := range s {
		if r == sep {
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

// WrapHandler wraps an HTTP handler with New Relic instrumentation
func WrapHandler(app *newrelic.Application, pattern string, handler http.Handler) http.Handler {
	if app == nil {
		return handler
	}
	
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		txn := app.StartTransaction(pattern)
		defer txn.End()
		
		w = txn.SetWebResponse(w)
		txn.SetWebRequestHTTP(r)
		
		r = newrelic.RequestWithTransactionContext(r, txn)
		
		handler.ServeHTTP(w, r)
	})
}

// WrapHandlerFunc wraps an HTTP handler function with New Relic instrumentation
func WrapHandlerFunc(app *newrelic.Application, pattern string, handler http.HandlerFunc) http.HandlerFunc {
	if app == nil {
		return handler
	}
	
	return func(w http.ResponseWriter, r *http.Request) {
		txn := app.StartTransaction(pattern)
		defer txn.End()
		
		w = txn.SetWebResponse(w)
		txn.SetWebRequestHTTP(r)
		
		r = newrelic.RequestWithTransactionContext(r, txn)
		
		handler(w, r)
	}
}

// StartSegment starts a New Relic segment
func StartSegment(txn *newrelic.Transaction, name string) *newrelic.Segment {
	if txn == nil {
		return nil
	}
	return txn.StartSegment(name)
}

// RecordCustomEvent records a custom event
func RecordCustomEvent(app *newrelic.Application, eventType string, params map[string]interface{}) {
	if app != nil {
		app.RecordCustomEvent(eventType, params)
	}
}

// RecordCustomMetric records a custom metric
func RecordCustomMetric(app *newrelic.Application, name string, value float64) {
	if app != nil {
		app.RecordCustomMetric(name, value)
	}
}