//go:build test || nodiscovery

package api

import (
	"net/http"
	"time"

	"github.com/gorilla/mux"
)

// Handler implements all API endpoint handlers (without discovery dependency)
type Handler struct {
	// Mock services for testing
}

// NewHandler creates a new API handler
func NewHandler() *Handler {
	return &Handler{}
}

// SetDiscoveryEngine is a no-op in test mode
func (h *Handler) SetDiscoveryEngine(engine interface{}) {
	// No-op for testing
}

// GetHealth handles GET /health
func (h *Handler) GetHealth(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":  "healthy",
		"version": "1.0.0",
		"uptime":  "24h",
		"components": map[string]interface{}{
			"discovery": map[string]interface{}{
				"status":  "mocked",
				"message": "Running in test mode",
			},
		},
	}
	writeJSON(w, http.StatusOK, response)
}

// ListSchemas handles GET /discovery/schemas (mock)
func (h *Handler) ListSchemas(w http.ResponseWriter, r *http.Request) {
	schemas := []map[string]interface{}{
		{
			"name":        "Transaction",
			"eventType":   "Transaction",
			"recordCount": 1000000,
			"attributes": []map[string]interface{}{
				{
					"name":     "duration",
					"dataType": "numeric",
				},
				{
					"name":     "error",
					"dataType": "boolean",
				},
			},
			"quality": map[string]float64{
				"overallScore": 0.85,
			},
			"lastAnalyzed": time.Now().Format(time.RFC3339),
		},
		{
			"name":        "PageView",
			"eventType":   "PageView",
			"recordCount": 500000,
			"attributes": []map[string]interface{}{
				{
					"name":     "url",
					"dataType": "string",
				},
			},
			"quality": map[string]float64{
				"overallScore": 0.92,
			},
			"lastAnalyzed": time.Now().Format(time.RFC3339),
		},
	}

	response := map[string]interface{}{
		"schemas": schemas,
	}

	if r.URL.Query().Get("includeMetadata") == "true" {
		response["metadata"] = map[string]interface{}{
			"totalSchemas":  len(schemas),
			"executionTime": "100ms",
			"cacheHit":      false,
		}
	}

	writeJSON(w, http.StatusOK, response)
}

// GetSchemaProfile handles GET /discovery/schemas/{eventType} (mock)
func (h *Handler) GetSchemaProfile(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	eventType := vars["eventType"]

	if eventType != "Transaction" && eventType != "PageView" {
		writeError(w, http.StatusNotFound, "Schema not found", map[string]string{
			"eventType": eventType,
		})
		return
	}

	profile := map[string]interface{}{
		"name":      eventType,
		"eventType": eventType,
		"attributes": []map[string]interface{}{
			{
				"name":      "duration",
				"dataType":  "numeric",
				"nullRatio": 0.01,
				"patterns": []map[string]interface{}{
					{
						"type":        "range",
						"confidence":  0.9,
						"description": "Values between 0.1 and 5.0",
					},
				},
			},
		},
		"samples": []map[string]interface{}{
			{"duration": 1.23, "error": false},
			{"duration": 0.45, "error": false},
			{"duration": 2.67, "error": true},
		},
	}

	writeJSON(w, http.StatusOK, profile)
}

// FindRelationships handles POST /discovery/relationships (mock)
func (h *Handler) FindRelationships(w http.ResponseWriter, r *http.Request) {
	relationships := []map[string]interface{}{
		{
			"type":            "join",
			"sourceSchema":    "Transaction",
			"targetSchema":    "PageView",
			"sourceAttribute": "sessionId",
			"targetAttribute": "sessionId",
			"confidence":      0.95,
		},
	}

	response := map[string]interface{}{
		"relationships": relationships,
	}

	writeJSON(w, http.StatusOK, response)
}

// AssessQuality handles GET /discovery/quality/{eventType} (mock)
func (h *Handler) AssessQuality(w http.ResponseWriter, r *http.Request) {
	vars := mux.Vars(r)
	eventType := vars["eventType"]

	report := map[string]interface{}{
		"schemaName": eventType,
		"timestamp":  time.Now().Format(time.RFC3339),
		"metrics": map[string]float64{
			"overallScore": 0.85,
			"completeness": 0.90,
			"consistency":  0.88,
			"timeliness":   0.85,
			"uniqueness":   0.82,
			"validity":     0.83,
		},
		"issues": []map[string]interface{}{
			{
				"type":        "completeness",
				"severity":    "medium",
				"attribute":   "user_id",
				"description": "15% null values detected",
			},
		},
		"recommendations": []map[string]interface{}{
			{
				"type":        "improvement",
				"priority":    "medium",
				"description": "Add validation for user_id field",
				"impact":      "Improve data completeness by 15%",
			},
		},
	}

	writeJSON(w, http.StatusOK, report)
}

// AnalyzePatterns handles POST /patterns/analyze (mock)
func (h *Handler) AnalyzePatterns(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotImplemented, "Pattern analysis not yet implemented", nil)
}

// GenerateQuery handles POST /query/generate (mock)
func (h *Handler) GenerateQuery(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotImplemented, "Query generation not yet implemented", nil)
}

// CreateDashboard handles POST /dashboard/create (mock)
func (h *Handler) CreateDashboard(w http.ResponseWriter, r *http.Request) {
	writeError(w, http.StatusNotImplemented, "Dashboard creation not yet implemented", nil)
}