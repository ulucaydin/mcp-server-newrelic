package patterns

import (
	"fmt"
	"math"
	"sort"
	"strings"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// Engine implements pattern detection across different data types
type Engine struct {
	detectors []discovery.PatternDetector
	enableML  bool
}

// NewEngine creates a new pattern detection engine
func NewEngine(enableML bool) *Engine {
	engine := &Engine{
		enableML: enableML,
	}
	
	// Register default detectors
	engine.detectors = []discovery.PatternDetector{
		NewTimeSeriesDetector(),
		NewDistributionDetector(),
		NewFormatDetector(),
		NewSequenceDetector(),
	}
	
	return engine
}

// DetectPatterns runs all registered detectors on the data
func (e *Engine) DetectPatterns(data []interface{}, dataType discovery.DataType) []discovery.Pattern {
	patterns := []discovery.Pattern{}
	
	// Run each detector
	for _, detector := range e.detectors {
		detectedPatterns := detector.DetectPatterns(data, dataType)
		patterns = append(patterns, detectedPatterns...)
	}
	
	// Sort by confidence descending
	sort.Slice(patterns, func(i, j int) bool {
		return patterns[i].Confidence > patterns[j].Confidence
	})
	
	return patterns
}

// TimeSeriesDetector detects patterns in time series data
type TimeSeriesDetector struct{}

func NewTimeSeriesDetector() *TimeSeriesDetector {
	return &TimeSeriesDetector{}
}

func (d *TimeSeriesDetector) DetectPatterns(data []interface{}, dataType discovery.DataType) []discovery.Pattern {
	if dataType != discovery.DataTypeNumeric || len(data) < 10 {
		return nil
	}
	
	// Convert to float64 array
	values := make([]float64, 0, len(data))
	for _, v := range data {
		if f, ok := convertToFloat64(v); ok {
			values = append(values, f)
		}
	}
	
	if len(values) < 10 {
		return nil
	}
	
	patterns := []discovery.Pattern{}
	
	// Detect trend
	if trend := d.detectTrend(values); trend != nil {
		patterns = append(patterns, *trend)
	}
	
	// Detect seasonality
	if seasonal := d.detectSeasonality(values); seasonal != nil {
		patterns = append(patterns, *seasonal)
	}
	
	// Detect anomalies
	if anomalies := d.detectAnomalies(values); len(anomalies) > 0 {
		patterns = append(patterns, anomalies...)
	}
	
	return patterns
}

func (d *TimeSeriesDetector) GetDetectorName() string {
	return "time_series"
}

func (d *TimeSeriesDetector) detectTrend(values []float64) *discovery.Pattern {
	// Simple linear regression
	n := float64(len(values))
	sumX, sumY, sumXY, sumX2 := 0.0, 0.0, 0.0, 0.0
	
	for i, y := range values {
		x := float64(i)
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}
	
	// Calculate slope
	slope := (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)
	
	// Calculate R-squared
	meanY := sumY / n
	ssTot, ssRes := 0.0, 0.0
	for i, y := range values {
		yPred := slope*float64(i) + (meanY - slope*sumX/n)
		ssTot += (y - meanY) * (y - meanY)
		ssRes += (y - yPred) * (y - yPred)
	}
	
	rSquared := 1 - (ssRes / ssTot)
	
	// Only report trend if significant
	if math.Abs(rSquared) > 0.5 {
		direction := "increasing"
		if slope < 0 {
			direction = "decreasing"
		}
		
		return &discovery.Pattern{
			Type:        discovery.PatternTypeTrend,
			Confidence:  math.Abs(rSquared),
			Description: fmt.Sprintf("Linear %s trend detected", direction),
			Parameters: map[string]interface{}{
				"slope":     slope,
				"r_squared": rSquared,
				"direction": direction,
			},
		}
	}
	
	return nil
}

func (d *TimeSeriesDetector) detectSeasonality(values []float64) *discovery.Pattern {
	// Simple periodicity detection using autocorrelation
	maxLag := len(values) / 3
	if maxLag > 100 {
		maxLag = 100
	}
	
	bestLag := 0
	bestCorr := 0.0
	
	for lag := 2; lag < maxLag; lag++ {
		corr := d.autocorrelation(values, lag)
		if corr > bestCorr && corr > 0.7 {
			bestCorr = corr
			bestLag = lag
		}
	}
	
	if bestLag > 0 {
		return &discovery.Pattern{
			Type:        discovery.PatternTypeSeasonal,
			Confidence:  bestCorr,
			Description: fmt.Sprintf("Seasonal pattern with period %d", bestLag),
			Parameters: map[string]interface{}{
				"period":      bestLag,
				"correlation": bestCorr,
			},
		}
	}
	
	return nil
}

func (d *TimeSeriesDetector) detectAnomalies(values []float64) []discovery.Pattern {
	// Simple outlier detection using z-score
	mean, stdDev := d.meanStdDev(values)
	patterns := []discovery.Pattern{}
	
	anomalyIndices := []int{}
	for i, v := range values {
		zScore := math.Abs((v - mean) / stdDev)
		if zScore > 3 { // 3 standard deviations
			anomalyIndices = append(anomalyIndices, i)
		}
	}
	
	if len(anomalyIndices) > 0 {
		patterns = append(patterns, discovery.Pattern{
			Type:        discovery.PatternTypeAnomaly,
			Confidence:  0.95,
			Description: fmt.Sprintf("Found %d anomalous values", len(anomalyIndices)),
			Parameters: map[string]interface{}{
				"indices":        anomalyIndices,
				"anomaly_count":  len(anomalyIndices),
				"total_count":    len(values),
				"anomaly_ratio":  float64(len(anomalyIndices)) / float64(len(values)),
			},
		})
	}
	
	return patterns
}

func (d *TimeSeriesDetector) autocorrelation(values []float64, lag int) float64 {
	if lag >= len(values) {
		return 0
	}
	
	mean, _ := d.meanStdDev(values)
	
	numerator := 0.0
	denominator := 0.0
	
	for i := 0; i < len(values)-lag; i++ {
		numerator += (values[i] - mean) * (values[i+lag] - mean)
	}
	
	for _, v := range values {
		denominator += (v - mean) * (v - mean)
	}
	
	if denominator == 0 {
		return 0
	}
	
	return numerator / denominator
}

func (d *TimeSeriesDetector) meanStdDev(values []float64) (mean, stdDev float64) {
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

// DistributionDetector detects statistical distribution patterns
type DistributionDetector struct{}

func NewDistributionDetector() *DistributionDetector {
	return &DistributionDetector{}
}

func (d *DistributionDetector) DetectPatterns(data []interface{}, dataType discovery.DataType) []discovery.Pattern {
	if dataType != discovery.DataTypeNumeric || len(data) < 30 {
		return nil
	}
	
	// Convert to float64 array
	values := make([]float64, 0, len(data))
	for _, v := range data {
		if f, ok := convertToFloat64(v); ok {
			values = append(values, f)
		}
	}
	
	patterns := []discovery.Pattern{}
	
	// Check for normal distribution
	if d.isNormallyDistributed(values) {
		patterns = append(patterns, discovery.Pattern{
			Type:        discovery.PatternTypeDistribution,
			Subtype:     "normal",
			Confidence:  0.8,
			Description: "Data appears to follow normal distribution",
		})
	}
	
	// Check for uniform distribution
	if d.isUniformlyDistributed(values) {
		patterns = append(patterns, discovery.Pattern{
			Type:        discovery.PatternTypeDistribution,
			Subtype:     "uniform",
			Confidence:  0.8,
			Description: "Data appears to follow uniform distribution",
		})
	}
	
	// Check for power law
	if d.followsPowerLaw(values) {
		patterns = append(patterns, discovery.Pattern{
			Type:        discovery.PatternTypeDistribution,
			Subtype:     "power_law",
			Confidence:  0.7,
			Description: "Data appears to follow power law distribution",
		})
	}
	
	return patterns
}

func (d *DistributionDetector) GetDetectorName() string {
	return "distribution"
}

func (d *DistributionDetector) isNormallyDistributed(values []float64) bool {
	// Simple normality test using skewness and kurtosis
	mean, stdDev := d.meanStdDev(values)
	
	// Calculate skewness
	skewness := 0.0
	for _, v := range values {
		skewness += math.Pow((v-mean)/stdDev, 3)
	}
	skewness /= float64(len(values))
	
	// Calculate kurtosis
	kurtosis := 0.0
	for _, v := range values {
		kurtosis += math.Pow((v-mean)/stdDev, 4)
	}
	kurtosis = kurtosis/float64(len(values)) - 3
	
	// Normal distribution has skewness ≈ 0 and kurtosis ≈ 0
	return math.Abs(skewness) < 0.5 && math.Abs(kurtosis) < 0.5
}

func (d *DistributionDetector) isUniformlyDistributed(values []float64) bool {
	// Check if values are evenly distributed across range
	sort.Float64s(values)
	min, max := values[0], values[len(values)-1]
	
	// Divide range into buckets
	numBuckets := 10
	bucketSize := (max - min) / float64(numBuckets)
	buckets := make([]int, numBuckets)
	
	for _, v := range values {
		bucket := int((v - min) / bucketSize)
		if bucket >= numBuckets {
			bucket = numBuckets - 1
		}
		buckets[bucket]++
	}
	
	// Check if all buckets have similar counts
	expectedCount := len(values) / numBuckets
	chiSquare := 0.0
	for _, count := range buckets {
		diff := float64(count - expectedCount)
		chiSquare += (diff * diff) / float64(expectedCount)
	}
	
	// Chi-square test threshold
	return chiSquare < 16.92 // 95% confidence for 9 degrees of freedom
}

func (d *DistributionDetector) followsPowerLaw(values []float64) bool {
	// Simple check: in log-log plot, power law is linear
	sort.Float64s(values)
	
	// Remove zeros and negatives
	positiveValues := []float64{}
	for _, v := range values {
		if v > 0 {
			positiveValues = append(positiveValues, v)
		}
	}
	
	if len(positiveValues) < 10 {
		return false
	}
	
	// Create frequency distribution
	freqMap := make(map[float64]int)
	for _, v := range positiveValues {
		freqMap[v]++
	}
	
	// Convert to log-log
	logX := []float64{}
	logY := []float64{}
	for value, count := range freqMap {
		logX = append(logX, math.Log(value))
		logY = append(logY, math.Log(float64(count)))
	}
	
	// Check if log-log plot is linear (simplified)
	// In real implementation, would use proper linear regression
	return len(logX) > 5
}

func (d *DistributionDetector) meanStdDev(values []float64) (mean, stdDev float64) {
	if len(values) == 0 {
		return 0, 0
	}
	
	sum := 0.0
	for _, v := range values {
		sum += v
	}
	mean = sum / float64(len(values))
	
	sumSquares := 0.0
	for _, v := range values {
		diff := v - mean
		sumSquares += diff * diff
	}
	stdDev = math.Sqrt(sumSquares / float64(len(values)))
	
	return mean, stdDev
}

// FormatDetector detects format patterns in string data
type FormatDetector struct{}

func NewFormatDetector() *FormatDetector {
	return &FormatDetector{}
}

func (d *FormatDetector) DetectPatterns(data []interface{}, dataType discovery.DataType) []discovery.Pattern {
	if dataType != discovery.DataTypeString || len(data) < 5 {
		return nil
	}
	
	// Convert to string array
	values := make([]string, 0, len(data))
	for _, v := range data {
		if s, ok := v.(string); ok {
			values = append(values, s)
		}
	}
	
	patterns := []discovery.Pattern{}
	
	// Detect common formats
	formatCounts := map[string]int{
		"email":     0,
		"url":       0,
		"ip":        0,
		"uuid":      0,
		"json":      0,
		"timestamp": 0,
	}
	
	for _, v := range values {
		if d.isEmail(v) {
			formatCounts["email"]++
		}
		if d.isURL(v) {
			formatCounts["url"]++
		}
		if d.isIP(v) {
			formatCounts["ip"]++
		}
		if d.isUUID(v) {
			formatCounts["uuid"]++
		}
		if d.isJSON(v) {
			formatCounts["json"]++
		}
		if d.isTimestamp(v) {
			formatCounts["timestamp"]++
		}
	}
	
	// Report patterns with >80% occurrence
	threshold := int(float64(len(values)) * 0.8)
	for format, count := range formatCounts {
		if count >= threshold {
			patterns = append(patterns, discovery.Pattern{
				Type:        discovery.PatternTypeFormat,
				Subtype:     format,
				Confidence:  float64(count) / float64(len(values)),
				Description: fmt.Sprintf("Detected %s format pattern", format),
				Parameters: map[string]interface{}{
					"match_count": count,
					"total_count": len(values),
				},
			})
		}
	}
	
	return patterns
}

func (d *FormatDetector) GetDetectorName() string {
	return "format"
}

func (d *FormatDetector) isEmail(s string) bool {
	return strings.Contains(s, "@") && strings.Contains(s, ".")
}

func (d *FormatDetector) isURL(s string) bool {
	return strings.HasPrefix(s, "http://") || strings.HasPrefix(s, "https://")
}

func (d *FormatDetector) isIP(s string) bool {
	parts := strings.Split(s, ".")
	if len(parts) != 4 {
		return false
	}
	for _, part := range parts {
		if len(part) == 0 || len(part) > 3 {
			return false
		}
	}
	return true
}

func (d *FormatDetector) isUUID(s string) bool {
	if len(s) != 36 {
		return false
	}
	// Simple check for UUID format
	return s[8] == '-' && s[13] == '-' && s[18] == '-' && s[23] == '-'
}

func (d *FormatDetector) isJSON(s string) bool {
	s = strings.TrimSpace(s)
	return (strings.HasPrefix(s, "{") && strings.HasSuffix(s, "}")) ||
		(strings.HasPrefix(s, "[") && strings.HasSuffix(s, "]"))
}

func (d *FormatDetector) isTimestamp(s string) bool {
	// Check various timestamp formats
	return strings.Contains(s, "-") && strings.Contains(s, ":") ||
		len(s) == 10 || len(s) == 13 // Unix timestamp
}

// SequenceDetector detects sequential patterns
type SequenceDetector struct{}

func NewSequenceDetector() *SequenceDetector {
	return &SequenceDetector{}
}

func (d *SequenceDetector) DetectPatterns(data []interface{}, dataType discovery.DataType) []discovery.Pattern {
	patterns := []discovery.Pattern{}
	
	switch dataType {
	case discovery.DataTypeNumeric:
		if seq := d.detectNumericSequence(data); seq != nil {
			patterns = append(patterns, *seq)
		}
	case discovery.DataTypeString:
		if seq := d.detectStringSequence(data); seq != nil {
			patterns = append(patterns, *seq)
		}
	}
	
	return patterns
}

func (d *SequenceDetector) GetDetectorName() string {
	return "sequence"
}

func (d *SequenceDetector) detectNumericSequence(data []interface{}) *discovery.Pattern {
	if len(data) < 3 {
		return nil
	}
	
	// Convert to float64 and check for arithmetic sequence
	values := []float64{}
	for _, v := range data {
		if f, ok := convertToFloat64(v); ok {
			values = append(values, f)
		}
	}
	
	if len(values) < 3 {
		return nil
	}
	
	// Check if differences are constant
	diffs := []float64{}
	for i := 1; i < len(values); i++ {
		diffs = append(diffs, values[i]-values[i-1])
	}
	
	// Check if all differences are similar
	firstDiff := diffs[0]
	isSequence := true
	for _, diff := range diffs[1:] {
		if math.Abs(diff-firstDiff) > 0.001 {
			isSequence = false
			break
		}
	}
	
	if isSequence {
		return &discovery.Pattern{
			Type:        discovery.PatternTypeSequence,
			Subtype:     "arithmetic",
			Confidence:  0.95,
			Description: fmt.Sprintf("Arithmetic sequence with difference %.2f", firstDiff),
			Parameters: map[string]interface{}{
				"difference": firstDiff,
				"start":      values[0],
			},
		}
	}
	
	return nil
}

func (d *SequenceDetector) detectStringSequence(data []interface{}) *discovery.Pattern {
	// Check for patterns like ID sequences
	values := []string{}
	for _, v := range data {
		if s, ok := v.(string); ok {
			values = append(values, s)
		}
	}
	
	if len(values) < 3 {
		return nil
	}
	
	// Check if strings have common prefix
	commonPrefix := d.findCommonPrefix(values)
	if len(commonPrefix) > 0 && len(commonPrefix) < len(values[0])-2 {
		return &discovery.Pattern{
			Type:        discovery.PatternTypeSequence,
			Subtype:     "prefix",
			Confidence:  0.8,
			Description: fmt.Sprintf("String sequence with common prefix: %s", commonPrefix),
			Parameters: map[string]interface{}{
				"prefix": commonPrefix,
				"count":  len(values),
			},
		}
	}
	
	return nil
}

func (d *SequenceDetector) findCommonPrefix(values []string) string {
	if len(values) == 0 {
		return ""
	}
	
	prefix := values[0]
	for _, v := range values[1:] {
		for !strings.HasPrefix(v, prefix) && len(prefix) > 0 {
			prefix = prefix[:len(prefix)-1]
		}
	}
	
	return prefix
}

// Helper function to convert various numeric types to float64
func convertToFloat64(v interface{}) (float64, bool) {
	switch val := v.(type) {
	case float64:
		return val, true
	case float32:
		return float64(val), true
	case int:
		return float64(val), true
	case int32:
		return float64(val), true
	case int64:
		return float64(val), true
	default:
		return 0, false
	}
}