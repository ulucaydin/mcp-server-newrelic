package discovery

import (
	"context"
	"encoding/json"
	"time"
)

// Core domain types

// Schema represents a discovered data schema in NRDB
type Schema struct {
	ID               string                 `json:"id"`
	Name             string                 `json:"name"`
	EventType        string                 `json:"event_type"`
	Attributes       []Attribute            `json:"attributes"`
	SampleCount      int64                  `json:"sample_count"`
	DataVolume       DataVolumeProfile      `json:"data_volume"`
	Quality          QualityMetrics         `json:"quality"`
	Patterns         []DetectedPattern      `json:"patterns"`
	DiscoveredAt     time.Time             `json:"discovered_at"`
	LastAnalyzedAt   time.Time             `json:"last_analyzed_at"`
	Metadata         map[string]interface{} `json:"metadata"`
}

// Attribute represents a single attribute within a schema
type Attribute struct {
	Name             string              `json:"name"`
	DataType         DataType            `json:"data_type"`
	SemanticType     SemanticType        `json:"semantic_type"`
	Cardinality      CardinalityProfile  `json:"cardinality"`
	Statistics       Statistics          `json:"statistics"`
	NullRatio        float64            `json:"null_ratio"`
	Patterns         []Pattern          `json:"patterns"`
	Quality          AttributeQuality    `json:"quality"`
	SampleValues     []interface{}      `json:"sample_values,omitempty"`
}

// DataType represents the basic data type of an attribute
type DataType string

const (
	DataTypeString    DataType = "string"
	DataTypeNumeric   DataType = "numeric"
	DataTypeBoolean   DataType = "boolean"
	DataTypeTimestamp DataType = "timestamp"
	DataTypeJSON      DataType = "json"
	DataTypeArray     DataType = "array"
	DataTypeUnknown   DataType = "unknown"
)

// SemanticType represents the semantic meaning of an attribute
type SemanticType string

const (
	SemanticTypeID          SemanticType = "identifier"
	SemanticTypeEmail       SemanticType = "email"
	SemanticTypeURL         SemanticType = "url"
	SemanticTypeIP          SemanticType = "ip_address"
	SemanticTypeUserAgent   SemanticType = "user_agent"
	SemanticTypeCurrency    SemanticType = "currency"
	SemanticTypeCountry     SemanticType = "country"
	SemanticTypeLatLong     SemanticType = "lat_long"
	SemanticTypeDuration    SemanticType = "duration"
	SemanticTypePercentage  SemanticType = "percentage"
	SemanticTypeFilePath    SemanticType = "file_path"
	SemanticTypeJSON        SemanticType = "json_object"
	SemanticTypeCustom      SemanticType = "custom"
)

// CardinalityProfile describes the cardinality characteristics of an attribute
type CardinalityProfile struct {
	Unique          int64   `json:"unique"`
	Total           int64   `json:"total"`
	Ratio           float64 `json:"ratio"`
	IsHighCardinality bool   `json:"is_high_cardinality"`
	TopValues       []ValueFrequency `json:"top_values,omitempty"`
}

// ValueFrequency represents a value and its frequency
type ValueFrequency struct {
	Value     interface{} `json:"value"`
	Frequency int64       `json:"frequency"`
	Percentage float64    `json:"percentage"`
}

// Statistics holds statistical information about an attribute
type Statistics struct {
	NumericStats   *NumericStatistics   `json:"numeric_stats,omitempty"`
	StringStats    *StringStatistics    `json:"string_stats,omitempty"`
	TemporalStats  *TemporalStatistics  `json:"temporal_stats,omitempty"`
}

// NumericStatistics for numeric attributes
type NumericStatistics struct {
	Min        float64              `json:"min"`
	Max        float64              `json:"max"`
	Mean       float64              `json:"mean"`
	Median     float64              `json:"median"`
	StdDev     float64              `json:"std_dev"`
	Percentiles map[string]float64   `json:"percentiles"`
}

// StringStatistics for string attributes
type StringStatistics struct {
	MinLength      int     `json:"min_length"`
	MaxLength      int     `json:"max_length"`
	AvgLength      float64 `json:"avg_length"`
	EmptyCount     int64   `json:"empty_count"`
	DistinctCount  int64   `json:"distinct_count"`
}

// TemporalStatistics for timestamp attributes
type TemporalStatistics struct {
	Earliest   time.Time `json:"earliest"`
	Latest     time.Time `json:"latest"`
	Range      Duration  `json:"range"`
	Frequency  string    `json:"frequency"` // e.g., "hourly", "daily"
}

// Duration is a custom type for JSON serialization
type Duration struct {
	time.Duration
}

// Pattern represents a detected pattern in data
type Pattern struct {
	Type        PatternType            `json:"type"`
	Subtype     string                 `json:"subtype,omitempty"`
	Confidence  float64                `json:"confidence"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters,omitempty"`
}

// PatternType represents different types of patterns
type PatternType string

const (
	PatternTypeSeasonal     PatternType = "seasonal"
	PatternTypeTrend        PatternType = "trend"
	PatternTypeAnomaly      PatternType = "anomaly"
	PatternTypeDistribution PatternType = "distribution"
	PatternTypeFormat       PatternType = "format"
	PatternTypeSequence     PatternType = "sequence"
)

// DataVolumeProfile describes the volume characteristics
type DataVolumeProfile struct {
	TotalRecords     int64              `json:"total_records"`
	RecordsPerHour   float64            `json:"records_per_hour"`
	RecordsPerDay    float64            `json:"records_per_day"`
	GrowthRate       float64            `json:"growth_rate"`
	RetentionDays    int                `json:"retention_days"`
	EstimatedSizeGB  float64            `json:"estimated_size_gb"`
}

// QualityMetrics represents data quality measurements
type QualityMetrics struct {
	OverallScore     float64                   `json:"overall_score"`
	Completeness     float64                   `json:"completeness"`
	Consistency      float64                   `json:"consistency"`
	Timeliness       float64                   `json:"timeliness"`
	Uniqueness       float64                   `json:"uniqueness"`
	Validity         float64                   `json:"validity"`
	Issues           []QualityIssue            `json:"issues"`
	Recommendations  []QualityRecommendation   `json:"recommendations"`
}

// QualityIssue represents a specific quality problem
type QualityIssue struct {
	Type        string    `json:"type"`
	Severity    string    `json:"severity"`
	Attribute   string    `json:"attribute,omitempty"`
	Description string    `json:"description"`
	Impact      float64   `json:"impact"`
	DetectedAt  time.Time `json:"detected_at"`
}

// QualityRecommendation suggests improvements
type QualityRecommendation struct {
	Type        string  `json:"type"`
	Priority    string  `json:"priority"`
	Description string  `json:"description"`
	Impact      float64 `json:"estimated_impact"`
	Effort      string  `json:"effort_level"`
}

// AttributeQuality represents quality metrics for a single attribute
type AttributeQuality struct {
	Score          float64  `json:"score"`
	Completeness   float64  `json:"completeness"`
	Validity       float64  `json:"validity"`
	Issues         []string `json:"issues,omitempty"`
}

// DetectedPattern represents patterns found in the overall schema
type DetectedPattern struct {
	Name        string                 `json:"name"`
	Type        string                 `json:"type"`
	Confidence  float64                `json:"confidence"`
	Attributes  []string               `json:"attributes"`
	Description string                 `json:"description"`
	Evidence    map[string]interface{} `json:"evidence"`
}

// TimeRange represents a time range for queries
type TimeRange struct {
	Start time.Time `json:"start"`
	End   time.Time `json:"end"`
}

// Duration methods for custom JSON marshaling
func (d Duration) MarshalJSON() ([]byte, error) {
	return []byte(`"` + d.Duration.String() + `"`), nil
}

func (d *Duration) UnmarshalJSON(b []byte) error {
	var s string
	if err := json.Unmarshal(b, &s); err != nil {
		return err
	}
	dur, err := time.ParseDuration(s)
	if err != nil {
		return err
	}
	d.Duration = dur
	return nil
}