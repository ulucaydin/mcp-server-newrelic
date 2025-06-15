package discovery

import (
	"context"
	"fmt"
	"log"
	"net/http"
	"sort"
	"strings"
	"time"
)

// runBackgroundTasks runs periodic background tasks
func (e *Engine) runBackgroundTasks() {
	ticker := time.NewTicker(5 * time.Minute)
	defer ticker.Stop()
	
	for {
		select {
		case <-e.ctx.Done():
			return
		case <-ticker.C:
			// Periodic cache cleanup
			if stats := e.cache.Stats(); stats.Size > 0 {
				log.Printf("Cache stats: hits=%d, misses=%d, size=%d, hit_rate=%.2f%%",
					stats.Hits, stats.Misses, stats.Size, stats.HitRate*100)
			}
			
			// Update metrics
			e.mu.RLock()
			discoveryRate := float64(e.discoveryCount) / time.Since(e.startTime).Minutes()
			e.mu.RUnlock()
			
			log.Printf("Discovery rate: %.2f/min", discoveryRate)
		}
	}
}

// runHealthCheckServer runs a simple health check HTTP server
func (e *Engine) runHealthCheckServer() {
	if e.config.Observability.HealthCheckPort == 0 {
		return
	}
	
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		health := e.Health()
		if health.Status != "healthy" {
			w.WriteHeader(http.StatusServiceUnavailable)
		}
		fmt.Fprintf(w, "Status: %s\nUptime: %s\n", health.Status, health.Uptime)
	})
	
	server := &http.Server{
		Addr:    fmt.Sprintf(":%d", e.config.Observability.HealthCheckPort),
		Handler: mux,
	}
	
	go func() {
		<-e.ctx.Done()
		server.Close()
	}()
	
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Printf("Health check server error: %v", err)
	}
}

// recordShutdownMetrics records final metrics before shutdown
func (e *Engine) recordShutdownMetrics() {
	e.mu.RLock()
	defer e.mu.RUnlock()
	
	log.Printf("Shutdown metrics: discoveries=%d, uptime=%s",
		e.discoveryCount, time.Since(e.startTime))
}

// createIntelligentFilter creates a filter based on discovery hints
func (e *Engine) createIntelligentFilter(hints DiscoveryHints) DiscoveryFilter {
	filter := DiscoveryFilter{
		MaxSchemas: 50, // Start with reasonable limit
	}
	
	// Convert keywords to patterns
	if len(hints.Keywords) > 0 {
		patterns := make([]string, 0, len(hints.Keywords))
		for _, keyword := range hints.Keywords {
			patterns = append(patterns, fmt.Sprintf("*%s*", keyword))
		}
		filter.IncludePatterns = patterns
	}
	
	// Add domain-specific filters
	switch hints.Domain {
	case "performance":
		filter.IncludePatterns = append(filter.IncludePatterns, 
			"*Transaction*", "*PageView*", "*Synthetics*")
	case "infrastructure":
		filter.IncludePatterns = append(filter.IncludePatterns,
			"*SystemSample*", "*ProcessSample*", "*NetworkSample*")
	case "logs":
		filter.IncludePatterns = append(filter.IncludePatterns,
			"*Log*", "*LogEntry*")
	}
	
	// Set minimum record count to avoid empty schemas
	filter.MinRecordCount = 100
	
	return filter
}

// rankSchemasByRelevance ranks schemas based on relevance to hints
func (e *Engine) rankSchemasByRelevance(schemas []Schema, hints DiscoveryHints) []Schema {
	type rankedSchema struct {
		schema Schema
		score  float64
	}
	
	ranked := make([]rankedSchema, len(schemas))
	
	for i, schema := range schemas {
		score := 0.0
		
		// Score based on keyword matches
		schemaNameLower := strings.ToLower(schema.Name)
		for _, keyword := range hints.Keywords {
			if strings.Contains(schemaNameLower, strings.ToLower(keyword)) {
				score += 10.0
			}
		}
		
		// Score based on data volume (prefer schemas with more data)
		if schema.DataVolume.TotalRecords > 0 {
			score += float64(schema.DataVolume.TotalRecords) / 1000000.0 // 1 point per million records
		}
		
		// Score based on quality
		score += schema.Quality.OverallScore * 5.0
		
		// Score based on number of patterns found
		score += float64(len(schema.Patterns))
		
		ranked[i] = rankedSchema{schema: schema, score: score}
	}
	
	// Sort by score descending
	sort.Slice(ranked, func(i, j int) bool {
		return ranked[i].score > ranked[j].score
	})
	
	// Extract sorted schemas
	result := make([]Schema, len(schemas))
	for i, r := range ranked {
		result[i] = r.schema
	}
	
	return result
}

// detectCrossSchemaPatterns finds patterns across multiple schemas
func (e *Engine) detectCrossSchemaPatterns(ctx context.Context, schemas []Schema) []CrossSchemaPattern {
	patterns := []CrossSchemaPattern{}
	
	// Pattern 1: Common attributes across schemas
	attrFrequency := make(map[string][]string)
	for _, schema := range schemas {
		for _, attr := range schema.Attributes {
			attrFrequency[attr.Name] = append(attrFrequency[attr.Name], schema.Name)
		}
	}
	
	for attrName, schemaNames := range attrFrequency {
		if len(schemaNames) > 1 {
			patterns = append(patterns, CrossSchemaPattern{
				Name:        fmt.Sprintf("Common attribute: %s", attrName),
				Schemas:     schemaNames,
				Type:        "common_attribute",
				Confidence:  0.9,
				Description: fmt.Sprintf("Attribute '%s' appears in %d schemas", attrName, len(schemaNames)),
			})
		}
	}
	
	// Pattern 2: Temporal alignment
	hasTimestamp := []string{}
	for _, schema := range schemas {
		for _, attr := range schema.Attributes {
			if attr.DataType == DataTypeTimestamp || attr.Name == "timestamp" {
				hasTimestamp = append(hasTimestamp, schema.Name)
				break
			}
		}
	}
	
	if len(hasTimestamp) > 1 {
		patterns = append(patterns, CrossSchemaPattern{
			Name:        "Temporal alignment possible",
			Schemas:     hasTimestamp,
			Type:        "temporal_alignment",
			Confidence:  0.95,
			Description: fmt.Sprintf("%d schemas have timestamp fields for correlation", len(hasTimestamp)),
		})
	}
	
	// Pattern 3: ID-based relationships
	idAttributes := make(map[string][]string)
	for _, schema := range schemas {
		for _, attr := range schema.Attributes {
			if attr.SemanticType == SemanticTypeID || strings.HasSuffix(attr.Name, "Id") || strings.HasSuffix(attr.Name, "ID") {
				idAttributes[attr.Name] = append(idAttributes[attr.Name], schema.Name)
			}
		}
	}
	
	for idName, schemaNames := range idAttributes {
		if len(schemaNames) > 1 {
			patterns = append(patterns, CrossSchemaPattern{
				Name:        fmt.Sprintf("Potential join key: %s", idName),
				Schemas:     schemaNames,
				Type:        "join_candidate",
				Confidence:  0.8,
				Description: fmt.Sprintf("ID field '%s' could link %d schemas", idName, len(schemaNames)),
			})
		}
	}
	
	return patterns
}

// generateInsights creates insights from schemas and patterns
func (e *Engine) generateInsights(schemas []Schema, patterns []CrossSchemaPattern) []Insight {
	insights := []Insight{}
	
	// Insight 1: Data quality issues
	for _, schema := range schemas {
		if schema.Quality.OverallScore < 0.7 {
			insights = append(insights, Insight{
				ID:          fmt.Sprintf("quality-%s", schema.Name),
				Type:        "data_quality",
				Severity:    "warning",
				Title:       fmt.Sprintf("Low data quality in %s", schema.Name),
				Description: fmt.Sprintf("Schema %s has quality score of %.2f", schema.Name, schema.Quality.OverallScore),
				Impact:      "May affect accuracy of analysis and dashboards",
				Evidence: map[string]interface{}{
					"quality_score": schema.Quality.OverallScore,
					"completeness":  schema.Quality.Completeness,
				},
				Actions: []string{
					"Review data collection for this schema",
					"Check for missing required fields",
					"Validate data sources",
				},
			})
		}
	}
	
	// Insight 2: High cardinality warnings
	for _, schema := range schemas {
		for _, attr := range schema.Attributes {
			if attr.Cardinality.IsHighCardinality && attr.Cardinality.Ratio > 0.9 {
				insights = append(insights, Insight{
					ID:          fmt.Sprintf("cardinality-%s-%s", schema.Name, attr.Name),
					Type:        "performance",
					Severity:    "info",
					Title:       fmt.Sprintf("High cardinality attribute: %s.%s", schema.Name, attr.Name),
					Description: fmt.Sprintf("Attribute has %.0f%% unique values", attr.Cardinality.Ratio*100),
					Impact:      "May impact query performance when used in GROUP BY",
					Evidence: map[string]interface{}{
						"unique_values": attr.Cardinality.Unique,
						"total_values":  attr.Cardinality.Total,
					},
					Actions: []string{
						"Consider sampling when grouping by this attribute",
						"Use time-based aggregations to reduce cardinality",
					},
				})
			}
		}
	}
	
	// Insight 3: Relationship opportunities
	if len(patterns) > 0 {
		joinCandidates := 0
		for _, pattern := range patterns {
			if pattern.Type == "join_candidate" {
				joinCandidates++
			}
		}
		
		if joinCandidates > 0 {
			insights = append(insights, Insight{
				ID:          "relationships",
				Type:        "opportunity",
				Severity:    "info",
				Title:       fmt.Sprintf("Found %d potential data relationships", joinCandidates),
				Description: "Multiple schemas share common ID fields that could be used for joins",
				Impact:      "Can create richer dashboards by combining data from multiple sources",
				Evidence: map[string]interface{}{
					"join_candidates": joinCandidates,
					"total_patterns":  len(patterns),
				},
				Actions: []string{
					"Explore JOIN queries between related schemas",
					"Create unified dashboards with correlated data",
				},
			})
		}
	}
	
	return insights
}

// createExecutionPlan creates a plan for discovery execution
func (e *Engine) createExecutionPlan(hints DiscoveryHints, schemas []Schema) *ExecutionPlan {
	steps := []ExecutionStep{
		{
			Name:     "Schema Discovery",
			Type:     "discovery",
			Duration: 2 * time.Second,
			Status:   "completed",
			Details:  fmt.Sprintf("Discovered %d schemas", len(schemas)),
		},
	}
	
	// Add analysis steps based on purpose
	switch hints.Purpose {
	case "performance analysis":
		steps = append(steps, ExecutionStep{
			Name:     "Performance Pattern Analysis",
			Type:     "analysis",
			Duration: 1 * time.Second,
			Status:   "planned",
			Details:  "Analyze response times, error rates, and throughput patterns",
		})
	case "cost optimization":
		steps = append(steps, ExecutionStep{
			Name:     "Usage Analysis",
			Type:     "analysis",
			Duration: 1 * time.Second,
			Status:   "planned",
			Details:  "Analyze data ingestion rates and storage patterns",
		})
	}
	
	// Add visualization step
	steps = append(steps, ExecutionStep{
		Name:     "Dashboard Generation",
		Type:     "visualization",
		Duration: 3 * time.Second,
		Status:   "planned",
		Details:  "Generate optimized dashboard with discovered insights",
	})
	
	totalDuration := time.Duration(0)
	for _, step := range steps {
		totalDuration += step.Duration
	}
	
	return &ExecutionPlan{
		Steps:       steps,
		TotalTime:   totalDuration,
		Parallelism: e.config.Performance.WorkerPoolSize,
	}
}

// generateRecommendations creates recommendations from insights
func (e *Engine) generateRecommendations(insights []Insight) []string {
	recommendations := []string{}
	
	// Count insights by type
	typeCounts := make(map[string]int)
	for _, insight := range insights {
		typeCounts[insight.Type]++
	}
	
	// Generate recommendations based on insight patterns
	if typeCounts["data_quality"] > 0 {
		recommendations = append(recommendations,
			fmt.Sprintf("Address %d data quality issues before creating production dashboards", typeCounts["data_quality"]))
	}
	
	if typeCounts["performance"] > 0 {
		recommendations = append(recommendations,
			"Consider performance optimizations for high-cardinality attributes")
	}
	
	if typeCounts["opportunity"] > 0 {
		recommendations = append(recommendations,
			"Explore data relationships to create comprehensive views")
	}
	
	// Always recommend caching for better performance
	recommendations = append(recommendations,
		"Enable result caching for frequently accessed schemas")
	
	return recommendations
}

// Helper method implementations for discoverSingleSchema

// getDataProfile analyzes data characteristics for sampling strategy selection
func (e *Engine) getDataProfile(ctx context.Context, eventType string) (DataProfile, error) {
	// Query for basic statistics
	statsQuery := fmt.Sprintf(`
		SELECT 
			count(*) as total,
			min(timestamp) as earliest,
			max(timestamp) as latest
		FROM %s 
		SINCE 7 days ago
	`, eventType)
	
	result, err := e.nrdb.Query(ctx, statsQuery)
	if err != nil {
		return DataProfile{}, err
	}
	
	profile := DataProfile{}
	
	if len(result.Results) > 0 {
		if total, ok := result.Results[0]["total"].(float64); ok {
			profile.TotalRecords = int64(total)
		}
		
		// Calculate records per hour
		profile.RecordsPerHour = float64(profile.TotalRecords) / (7 * 24) // 7 days
	}
	
	// Simple heuristics for other characteristics
	profile.HasTimeSeries = true // Most NRDB data is time series
	profile.HasHighCardinality = profile.TotalRecords > 1000000
	
	return profile, nil
}

// addStatisticsToSchema enriches schema with detailed statistics
func (e *Engine) addStatisticsToSchema(ctx context.Context, schema *Schema) error {
	// This would query for detailed statistics for each attribute
	// For now, using placeholder implementation
	for i := range schema.Attributes {
		attr := &schema.Attributes[i]
		
		// Add basic statistics based on type
		switch attr.DataType {
		case DataTypeNumeric:
			attr.Statistics = Statistics{
				NumericStats: &NumericStatistics{
					Min:    0,
					Max:    100,
					Mean:   50,
					Median: 50,
					StdDev: 15,
					Percentiles: map[string]float64{
						"p50": 50,
						"p90": 80,
						"p99": 95,
					},
				},
			}
		case DataTypeString:
			attr.Statistics = Statistics{
				StringStats: &StringStatistics{
					MinLength:     5,
					MaxLength:     50,
					AvgLength:     20,
					EmptyCount:    0,
					DistinctCount: 100,
				},
			}
		}
	}
	
	return nil
}

// addPatternsToSchema detects and adds patterns to schema
func (e *Engine) addPatternsToSchema(ctx context.Context, schema *Schema) error {
	// Use pattern engine to detect patterns
	// For now, add some example patterns
	schema.Patterns = []DetectedPattern{
		{
			Name:        "Regular time series",
			Type:        "temporal",
			Confidence:  0.95,
			Attributes:  []string{"timestamp"},
			Description: "Data arrives at regular intervals",
			Evidence: map[string]interface{}{
				"interval": "1m",
				"gaps":     0,
			},
		},
	}
	
	return nil
}

// addSamplesToSchema adds sample values to attributes
func (e *Engine) addSamplesToSchema(ctx context.Context, schema *Schema) error {
	// Query for sample values
	sampleQuery := fmt.Sprintf("SELECT * FROM %s LIMIT 10", schema.EventType)
	result, err := e.nrdb.Query(ctx, sampleQuery)
	if err != nil {
		return err
	}
	
	// Extract sample values for each attribute
	for i := range schema.Attributes {
		attr := &schema.Attributes[i]
		samples := make([]interface{}, 0, len(result.Results))
		
		for _, record := range result.Results {
			if val, ok := record[attr.Name]; ok && val != nil {
				samples = append(samples, val)
				if len(samples) >= 5 {
					break // Limit samples
				}
			}
		}
		
		attr.SampleValues = samples
	}
	
	return nil
}

// assessSchemaQuality calculates comprehensive quality metrics
func (e *Engine) assessSchemaQuality(ctx context.Context, schema Schema) (QualityMetrics, error) {
	// Get a larger sample for quality assessment
	sample, err := e.SampleData(ctx, SamplingParams{
		EventType:  schema.EventType,
		TimeRange:  TimeRange{Start: time.Now().Add(-24 * time.Hour), End: time.Now()},
		MaxSamples: 1000,
	})
	if err != nil {
		return QualityMetrics{}, err
	}
	
	// Use quality assessor
	report := e.qualityAssessor.AssessSchema(ctx, schema, *sample)
	
	return QualityMetrics{
		OverallScore:    report.OverallScore,
		Completeness:    report.Dimensions.Completeness.Score,
		Consistency:     report.Dimensions.Consistency.Score,
		Timeliness:      report.Dimensions.Timeliness.Score,
		Uniqueness:      report.Dimensions.Uniqueness.Score,
		Validity:        report.Dimensions.Validity.Score,
		Issues:          report.Issues,
		Recommendations: report.Recommendations,
	}, nil
}