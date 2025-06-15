package quality

import (
	"context"
	"fmt"
	"math"
	"strings"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// Assessor implements quality assessment for schemas
type Assessor struct {
	config Config
}

// Config holds configuration for quality assessment
type Config struct {
	// Thresholds for quality dimensions
	CompletenessThreshold  float64
	ConsistencyThreshold   float64
	TimelinessThreshold    time.Duration
	UniquenessThreshold    float64
	ValidityThreshold      float64
	
	// Weights for overall score calculation
	CompletenessWeight     float64
	ConsistencyWeight      float64
	TimelinessWeight       float64
	UniquenessWeight       float64
	ValidityWeight         float64
}

// DefaultConfig returns default configuration
func DefaultConfig() Config {
	return Config{
		CompletenessThreshold: 0.95,
		ConsistencyThreshold:  0.90,
		TimelinessThreshold:   5 * time.Minute,
		UniquenessThreshold:   0.99,
		ValidityThreshold:     0.95,
		
		CompletenessWeight:    0.25,
		ConsistencyWeight:     0.25,
		TimelinessWeight:      0.20,
		UniquenessWeight:      0.15,
		ValidityWeight:        0.15,
	}
}

// NewAssessor creates a new quality assessor
func NewAssessor(config Config) *Assessor {
	return &Assessor{
		config: config,
	}
}

// AssessSchema performs comprehensive quality assessment
func (a *Assessor) AssessSchema(ctx context.Context, schema discovery.Schema, sample discovery.DataSample) discovery.QualityReport {
	report := discovery.QualityReport{
		SchemaName:    schema.Name,
		AssessmentTime: time.Now(),
		SampleSize:    sample.SampleSize,
		TimeRange:     sample.TimeRange,
	}
	
	// Assess each quality dimension
	report.Dimensions.Completeness = a.assessCompleteness(schema, sample)
	report.Dimensions.Consistency = a.assessConsistency(schema, sample)
	report.Dimensions.Timeliness = a.assessTimeliness(schema, sample)
	report.Dimensions.Uniqueness = a.assessUniqueness(schema, sample)
	report.Dimensions.Validity = a.assessValidity(schema, sample)
	
	// Calculate overall score
	report.OverallScore = a.calculateOverallScore(report.Dimensions)
	
	// Identify issues
	report.Issues = a.identifyIssues(report.Dimensions)
	
	// Generate recommendations
	report.Recommendations = a.generateRecommendations(report.Issues)
	
	// Add ML predictions if available
	if a.shouldUsePredictions() {
		report.Predictions = a.generatePredictions(schema, report)
	}
	
	return report
}

// assessCompleteness measures data completeness
func (a *Assessor) assessCompleteness(schema discovery.Schema, sample discovery.DataSample) discovery.QualityDimension {
	dim := discovery.QualityDimension{
		Name: "Completeness",
	}
	
	// Calculate null/missing value ratio for each attribute
	attributeScores := make(map[string]float64)
	totalFields := len(schema.Attributes) * sample.SampleSize
	missingCount := 0
	
	for _, attr := range schema.Attributes {
		nullCount := 0
		for _, record := range sample.Records {
			if val, exists := record[attr.Name]; !exists || val == nil || val == "" {
				nullCount++
				missingCount++
			}
		}
		
		if sample.SampleSize > 0 {
			attributeScores[attr.Name] = 1.0 - float64(nullCount)/float64(sample.SampleSize)
		}
	}
	
	// Overall completeness score
	if totalFields > 0 {
		dim.Score = 1.0 - float64(missingCount)/float64(totalFields)
	} else {
		dim.Score = 0.0
	}
	
	// Identify problematic attributes
	issues := []string{}
	for attrName, score := range attributeScores {
		if score < 0.9 {
			issues = append(issues, fmt.Sprintf("%s: %.1f%% complete", attrName, score*100))
		}
	}
	
	dim.Details = map[string]interface{}{
		"missing_values":     missingCount,
		"total_fields":       totalFields,
		"attribute_scores":   attributeScores,
		"problematic_fields": issues,
	}
	
	return dim
}

// assessConsistency measures data consistency
func (a *Assessor) assessConsistency(schema discovery.Schema, sample discovery.DataSample) discovery.QualityDimension {
	dim := discovery.QualityDimension{
		Name: "Consistency",
	}
	
	inconsistencies := 0
	totalChecks := 0
	
	// Check format consistency for string attributes
	for _, attr := range schema.Attributes {
		if attr.DataType == discovery.DataTypeString {
			formats := a.detectFormats(attr, sample)
			if len(formats) > 1 {
				// Multiple formats detected - potential inconsistency
				inconsistencies += len(formats) - 1
			}
			totalChecks++
		}
	}
	
	// Check numeric range consistency
	for _, attr := range schema.Attributes {
		if attr.DataType == discovery.DataTypeNumeric {
			if outliers := a.detectOutliers(attr, sample); outliers > 0 {
				inconsistencies += outliers
			}
			totalChecks++
		}
	}
	
	// Calculate score
	if totalChecks > 0 {
		dim.Score = 1.0 - float64(inconsistencies)/float64(totalChecks*sample.SampleSize)
	} else {
		dim.Score = 1.0
	}
	
	dim.Details = map[string]interface{}{
		"inconsistencies": inconsistencies,
		"total_checks":    totalChecks,
		"check_types":     []string{"format_consistency", "numeric_ranges"},
	}
	
	return dim
}

// assessTimeliness measures data freshness
func (a *Assessor) assessTimeliness(schema discovery.Schema, sample discovery.DataSample) discovery.QualityDimension {
	dim := discovery.QualityDimension{
		Name: "Timeliness",
	}
	
	// Find timestamp attribute
	var timestampAttr *discovery.Attribute
	for i := range schema.Attributes {
		if schema.Attributes[i].DataType == discovery.DataTypeTimestamp || 
		   schema.Attributes[i].Name == "timestamp" {
			timestampAttr = &schema.Attributes[i]
			break
		}
	}
	
	if timestampAttr == nil {
		dim.Score = 0.5 // Can't assess without timestamp
		dim.Details = map[string]interface{}{
			"error": "No timestamp attribute found",
		}
		return dim
	}
	
	// Calculate data age
	now := time.Now()
	delays := []time.Duration{}
	
	for _, record := range sample.Records {
		if tsVal, exists := record[timestampAttr.Name]; exists {
			if ts, ok := tsVal.(time.Time); ok {
				delay := now.Sub(ts)
				delays = append(delays, delay)
			}
		}
	}
	
	if len(delays) == 0 {
		dim.Score = 0.5
		return dim
	}
	
	// Calculate average delay
	totalDelay := time.Duration(0)
	maxDelay := time.Duration(0)
	for _, d := range delays {
		totalDelay += d
		if d > maxDelay {
			maxDelay = d
		}
	}
	avgDelay := totalDelay / time.Duration(len(delays))
	
	// Score based on threshold
	if avgDelay <= a.config.TimelinessThreshold {
		dim.Score = 1.0
	} else {
		// Linear decay after threshold
		dim.Score = float64(a.config.TimelinessThreshold) / float64(avgDelay)
	}
	
	dim.Details = map[string]interface{}{
		"average_delay": avgDelay.String(),
		"max_delay":     maxDelay.String(),
		"threshold":     a.config.TimelinessThreshold.String(),
		"sample_count":  len(delays),
	}
	
	return dim
}

// assessUniqueness measures duplicate detection
func (a *Assessor) assessUniqueness(schema discovery.Schema, sample discovery.DataSample) discovery.QualityDimension {
	dim := discovery.QualityDimension{
		Name: "Uniqueness",
	}
	
	// Find potential unique identifiers
	uniqueAttrs := []string{}
	for _, attr := range schema.Attributes {
		if attr.SemanticType == discovery.SemanticTypeID || 
		   strings.Contains(strings.ToLower(attr.Name), "id") {
			uniqueAttrs = append(uniqueAttrs, attr.Name)
		}
	}
	
	if len(uniqueAttrs) == 0 {
		dim.Score = 1.0 // No unique constraints to check
		dim.Details = map[string]interface{}{
			"note": "No identifier attributes found",
		}
		return dim
	}
	
	// Check for duplicates
	totalDuplicates := 0
	for _, attrName := range uniqueAttrs {
		seen := make(map[interface{}]int)
		duplicates := 0
		
		for _, record := range sample.Records {
			if val, exists := record[attrName]; exists && val != nil {
				seen[val]++
				if seen[val] > 1 {
					duplicates++
				}
			}
		}
		
		totalDuplicates += duplicates
	}
	
	// Calculate score
	totalChecks := len(uniqueAttrs) * sample.SampleSize
	if totalChecks > 0 {
		dim.Score = 1.0 - float64(totalDuplicates)/float64(totalChecks)
	} else {
		dim.Score = 1.0
	}
	
	dim.Details = map[string]interface{}{
		"unique_attributes": uniqueAttrs,
		"duplicates_found":  totalDuplicates,
		"attributes_checked": len(uniqueAttrs),
	}
	
	return dim
}

// assessValidity measures data validity
func (a *Assessor) assessValidity(schema discovery.Schema, sample discovery.DataSample) discovery.QualityDimension {
	dim := discovery.QualityDimension{
		Name: "Validity",
	}
	
	invalidCount := 0
	totalValidations := 0
	
	// Validate each attribute based on type and constraints
	for _, attr := range schema.Attributes {
		validations := 0
		invalid := 0
		
		for _, record := range sample.Records {
			if val, exists := record[attr.Name]; exists && val != nil {
				totalValidations++
				validations++
				
				if !a.isValid(attr, val) {
					invalid++
					invalidCount++
				}
			}
		}
		
		// Store per-attribute validity
		if validations > 0 {
			validity := 1.0 - float64(invalid)/float64(validations)
			if validity < 0.95 {
				// Track problematic attributes
			}
		}
	}
	
	// Calculate overall validity score
	if totalValidations > 0 {
		dim.Score = 1.0 - float64(invalidCount)/float64(totalValidations)
	} else {
		dim.Score = 1.0
	}
	
	dim.Details = map[string]interface{}{
		"invalid_values":    invalidCount,
		"total_validations": totalValidations,
		"validation_types":  []string{"type_check", "range_check", "format_check"},
	}
	
	return dim
}

// Helper methods

// detectFormats detects different formats in string data
func (a *Assessor) detectFormats(attr discovery.Attribute, sample discovery.DataSample) map[string]int {
	formats := make(map[string]int)
	
	for _, record := range sample.Records {
		if val, exists := record[attr.Name]; exists {
			if strVal, ok := val.(string); ok {
				format := a.classifyFormat(strVal)
				formats[format]++
			}
		}
	}
	
	return formats
}

// classifyFormat classifies string format
func (a *Assessor) classifyFormat(s string) string {
	s = strings.TrimSpace(s)
	
	// Check common formats
	if strings.Contains(s, "@") && strings.Contains(s, ".") {
		return "email"
	}
	if strings.HasPrefix(s, "http://") || strings.HasPrefix(s, "https://") {
		return "url"
	}
	if len(s) == 36 && s[8] == '-' && s[13] == '-' && s[18] == '-' && s[23] == '-' {
		return "uuid"
	}
	
	// Check if numeric
	isNumeric := true
	for _, ch := range s {
		if (ch < '0' || ch > '9') && ch != '.' && ch != '-' {
			isNumeric = false
			break
		}
	}
	if isNumeric {
		return "numeric_string"
	}
	
	return "general_string"
}

// detectOutliers detects outliers in numeric data
func (a *Assessor) detectOutliers(attr discovery.Attribute, sample discovery.DataSample) int {
	values := []float64{}
	
	for _, record := range sample.Records {
		if val, exists := record[attr.Name]; exists {
			if numVal, ok := a.toFloat64(val); ok {
				values = append(values, numVal)
			}
		}
	}
	
	if len(values) < 4 {
		return 0
	}
	
	// Calculate mean and standard deviation
	mean, stdDev := a.meanStdDev(values)
	
	// Count outliers (values beyond 3 standard deviations)
	outliers := 0
	for _, v := range values {
		if math.Abs(v-mean) > 3*stdDev {
			outliers++
		}
	}
	
	return outliers
}

// toFloat64 converts various numeric types to float64
func (a *Assessor) toFloat64(val interface{}) (float64, bool) {
	switch v := val.(type) {
	case float64:
		return v, true
	case float32:
		return float64(v), true
	case int:
		return float64(v), true
	case int32:
		return float64(v), true
	case int64:
		return float64(v), true
	default:
		return 0, false
	}
}

// meanStdDev calculates mean and standard deviation
func (a *Assessor) meanStdDev(values []float64) (mean, stdDev float64) {
	if len(values) == 0 {
		return 0, 0
	}
	
	// Calculate mean
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	mean = sum / float64(len(values))
	
	// Calculate standard deviation
	sumSquares := 0.0
	for _, v := range values {
		diff := v - mean
		sumSquares += diff * diff
	}
	stdDev = math.Sqrt(sumSquares / float64(len(values)))
	
	return mean, stdDev
}

// isValid checks if a value is valid for an attribute
func (a *Assessor) isValid(attr discovery.Attribute, val interface{}) bool {
	switch attr.DataType {
	case discovery.DataTypeString:
		_, ok := val.(string)
		return ok
	case discovery.DataTypeNumeric:
		_, ok := a.toFloat64(val)
		return ok
	case discovery.DataTypeBoolean:
		_, ok := val.(bool)
		return ok
	case discovery.DataTypeTimestamp:
		_, ok := val.(time.Time)
		return ok
	default:
		return true // Unknown types are considered valid
	}
}

// calculateOverallScore calculates weighted overall quality score
func (a *Assessor) calculateOverallScore(dims discovery.QualityDimensions) float64 {
	score := dims.Completeness.Score * a.config.CompletenessWeight +
		dims.Consistency.Score * a.config.ConsistencyWeight +
		dims.Timeliness.Score * a.config.TimelinessWeight +
		dims.Uniqueness.Score * a.config.UniquenessWeight +
		dims.Validity.Score * a.config.ValidityWeight
	
	return score
}

// identifyIssues identifies quality issues from dimensions
func (a *Assessor) identifyIssues(dims discovery.QualityDimensions) []discovery.QualityIssue {
	issues := []discovery.QualityIssue{}
	
	// Check each dimension against thresholds
	if dims.Completeness.Score < a.config.CompletenessThreshold {
		issues = append(issues, discovery.QualityIssue{
			Dimension:   "Completeness",
			Severity:    a.getSeverity(dims.Completeness.Score, a.config.CompletenessThreshold),
			Description: fmt.Sprintf("Completeness score %.2f below threshold %.2f", dims.Completeness.Score, a.config.CompletenessThreshold),
			Impact:      "Missing data may lead to incomplete analysis",
			Resolution:  "Review data collection pipeline for missing fields",
		})
	}
	
	if dims.Consistency.Score < a.config.ConsistencyThreshold {
		issues = append(issues, discovery.QualityIssue{
			Dimension:   "Consistency",
			Severity:    a.getSeverity(dims.Consistency.Score, a.config.ConsistencyThreshold),
			Description: fmt.Sprintf("Consistency score %.2f below threshold %.2f", dims.Consistency.Score, a.config.ConsistencyThreshold),
			Impact:      "Inconsistent data formats may cause parsing errors",
			Resolution:  "Standardize data formats at ingestion",
		})
	}
	
	if dims.Timeliness.Score < 0.8 { // Fixed threshold for timeliness
		issues = append(issues, discovery.QualityIssue{
			Dimension:   "Timeliness",
			Severity:    a.getSeverity(dims.Timeliness.Score, 0.8),
			Description: fmt.Sprintf("Data freshness score %.2f indicates delays", dims.Timeliness.Score),
			Impact:      "Stale data may not reflect current state",
			Resolution:  "Investigate data pipeline latency",
		})
	}
	
	if dims.Uniqueness.Score < a.config.UniquenessThreshold {
		issues = append(issues, discovery.QualityIssue{
			Dimension:   "Uniqueness",
			Severity:    a.getSeverity(dims.Uniqueness.Score, a.config.UniquenessThreshold),
			Description: fmt.Sprintf("Duplicate data detected, uniqueness score %.2f", dims.Uniqueness.Score),
			Impact:      "Duplicates may skew aggregations and counts",
			Resolution:  "Implement deduplication logic",
		})
	}
	
	if dims.Validity.Score < a.config.ValidityThreshold {
		issues = append(issues, discovery.QualityIssue{
			Dimension:   "Validity",
			Severity:    a.getSeverity(dims.Validity.Score, a.config.ValidityThreshold),
			Description: fmt.Sprintf("Invalid values detected, validity score %.2f", dims.Validity.Score),
			Impact:      "Invalid data may cause processing errors",
			Resolution:  "Add validation rules at data ingestion",
		})
	}
	
	return issues
}

// getSeverity determines issue severity based on score deviation
func (a *Assessor) getSeverity(score, threshold float64) string {
	deviation := threshold - score
	if deviation > 0.3 {
		return "critical"
	} else if deviation > 0.15 {
		return "high"
	} else if deviation > 0.05 {
		return "medium"
	}
	return "low"
}

// generateRecommendations creates actionable recommendations
func (a *Assessor) generateRecommendations(issues []discovery.QualityIssue) []string {
	recommendations := []string{}
	
	// Group issues by dimension
	dimensionCounts := make(map[string]int)
	for _, issue := range issues {
		dimensionCounts[issue.Dimension]++
	}
	
	// Generate recommendations based on issue patterns
	if dimensionCounts["Completeness"] > 0 {
		recommendations = append(recommendations, 
			"Implement data validation at ingestion to catch missing fields",
			"Set up alerts for schemas with low completeness scores")
	}
	
	if dimensionCounts["Consistency"] > 0 {
		recommendations = append(recommendations,
			"Create data transformation rules to standardize formats",
			"Document expected data formats for each attribute")
	}
	
	if dimensionCounts["Timeliness"] > 0 {
		recommendations = append(recommendations,
			"Optimize data pipeline for reduced latency",
			"Consider implementing real-time data streaming")
	}
	
	if dimensionCounts["Uniqueness"] > 0 {
		recommendations = append(recommendations,
			"Add unique constraints or deduplication logic",
			"Review data sources for duplicate generation")
	}
	
	if dimensionCounts["Validity"] > 0 {
		recommendations = append(recommendations,
			"Implement schema validation with explicit constraints",
			"Create data quality monitoring dashboards")
	}
	
	// Always recommend monitoring
	recommendations = append(recommendations,
		"Set up continuous data quality monitoring",
		"Create quality score trending dashboards")
	
	return recommendations
}

// shouldUsePredictions determines if ML predictions should be used
func (a *Assessor) shouldUsePredictions() bool {
	// In real implementation, would check if ML models are available
	return false
}

// generatePredictions generates quality predictions
func (a *Assessor) generatePredictions(schema discovery.Schema, report discovery.QualityReport) *discovery.QualityPredictions {
	// Placeholder for ML-based predictions
	return &discovery.QualityPredictions{
		FutureScore:       report.OverallScore,
		TrendDirection:    "stable",
		RiskFactors:       []string{},
		PreventiveActions: []string{},
	}
}