package quality_test

import (
	"context"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/quality"
)

func TestAssessor_AssessSchema(t *testing.T) {
	config := quality.DefaultConfig()
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	// Create test schema
	schema := discovery.Schema{
		Name:      "TestSchema",
		EventType: "TestEvent",
		Attributes: []discovery.Attribute{
			{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
			{Name: "name", DataType: discovery.DataTypeString},
			{Name: "value", DataType: discovery.DataTypeNumeric},
			{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
			{Name: "optional", DataType: discovery.DataTypeString},
		},
	}

	// Create test sample with various quality issues
	sample := discovery.DataSample{
		SampleSize: 100,
		TimeRange: discovery.TimeRange{
			Start: time.Now().Add(-1 * time.Hour),
			End:   time.Now(),
		},
		Records: make([]map[string]interface{}, 100),
	}

	// Generate sample records with quality issues
	for i := 0; i < 100; i++ {
		record := map[string]interface{}{
			"id":        "ID" + string(rune(i)),
			"name":      "Name" + string(rune(i)),
			"value":     float64(i),
			"timestamp": time.Now().Add(-time.Duration(i) * time.Minute),
		}

		// Add quality issues
		if i%10 == 0 {
			// Missing optional field (10% missing)
			delete(record, "optional")
		} else {
			record["optional"] = "optional_value"
		}

		if i%20 == 0 {
			// Null values
			record["name"] = nil
		}

		if i == 50 {
			// Duplicate ID
			record["id"] = "ID0"
		}

		sample.Records[i] = record
	}

	// Assess quality
	report := assessor.AssessSchema(ctx, schema, sample)

	// Verify report structure
	assert.Equal(t, "TestSchema", report.SchemaName)
	assert.Equal(t, 100, report.SampleSize)
	assert.NotZero(t, report.AssessmentTime)

	// Check dimensions
	assert.NotNil(t, report.Dimensions.Completeness)
	assert.NotNil(t, report.Dimensions.Consistency)
	assert.NotNil(t, report.Dimensions.Timeliness)
	assert.NotNil(t, report.Dimensions.Uniqueness)
	assert.NotNil(t, report.Dimensions.Validity)

	// Verify overall score is calculated
	assert.Greater(t, report.OverallScore, 0.0)
	assert.LessOrEqual(t, report.OverallScore, 1.0)

	// Should identify some issues
	assert.NotEmpty(t, report.Issues)
	assert.NotEmpty(t, report.Recommendations)
}

func TestAssessor_Completeness(t *testing.T) {
	config := quality.DefaultConfig()
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	schema := discovery.Schema{
		Name: "TestSchema",
		Attributes: []discovery.Attribute{
			{Name: "required1", DataType: discovery.DataTypeString},
			{Name: "required2", DataType: discovery.DataTypeString},
			{Name: "optional", DataType: discovery.DataTypeString},
		},
	}

	tests := []struct {
		name           string
		records        []map[string]interface{}
		expectScore    float64
		expectIssues   bool
	}{
		{
			name: "100% complete",
			records: []map[string]interface{}{
				{"required1": "val1", "required2": "val2", "optional": "opt1"},
				{"required1": "val3", "required2": "val4", "optional": "opt2"},
			},
			expectScore:  1.0,
			expectIssues: false,
		},
		{
			name: "missing values",
			records: []map[string]interface{}{
				{"required1": "val1", "required2": "val2"},
				{"required1": "val3"}, // missing required2
				{"required2": "val4"}, // missing required1
			},
			expectScore:  0.55, // Approximate
			expectIssues: true,
		},
		{
			name: "null values",
			records: []map[string]interface{}{
				{"required1": "val1", "required2": nil, "optional": "opt1"},
				{"required1": nil, "required2": "val2", "optional": nil},
			},
			expectScore:  0.5, // 3/6 fields are null
			expectIssues: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sample := discovery.DataSample{
				SampleSize: len(tt.records),
				Records:    tt.records,
				TimeRange: discovery.TimeRange{
					Start: time.Now().Add(-1 * time.Hour),
					End:   time.Now(),
				},
			}

			report := assessor.AssessSchema(ctx, schema, sample)
			
			assert.InDelta(t, tt.expectScore, report.Dimensions.Completeness.Score, 0.1,
				"Completeness score should be close to expected")

			if tt.expectIssues {
				hasCompletenessIssue := false
				for _, issue := range report.Issues {
					if issue.Dimension == "Completeness" {
						hasCompletenessIssue = true
						break
					}
				}
				assert.True(t, hasCompletenessIssue, "Should identify completeness issues")
			}
		})
	}
}

func TestAssessor_Timeliness(t *testing.T) {
	config := quality.DefaultConfig()
	config.TimelinessThreshold = 5 * time.Minute
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	schema := discovery.Schema{
		Name: "TestSchema",
		Attributes: []discovery.Attribute{
			{Name: "id", DataType: discovery.DataTypeString},
			{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
		},
	}

	now := time.Now()

	tests := []struct {
		name         string
		timestamps   []time.Time
		expectScore  float64
		expectIssues bool
	}{
		{
			name: "fresh data",
			timestamps: []time.Time{
				now.Add(-1 * time.Minute),
				now.Add(-2 * time.Minute),
				now.Add(-3 * time.Minute),
			},
			expectScore:  1.0,
			expectIssues: false,
		},
		{
			name: "stale data",
			timestamps: []time.Time{
				now.Add(-10 * time.Minute),
				now.Add(-15 * time.Minute),
				now.Add(-20 * time.Minute),
			},
			expectScore:  0.3, // Approximate
			expectIssues: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			records := make([]map[string]interface{}, len(tt.timestamps))
			for i, ts := range tt.timestamps {
				records[i] = map[string]interface{}{
					"id":        i,
					"timestamp": ts,
				}
			}

			sample := discovery.DataSample{
				SampleSize: len(records),
				Records:    records,
				TimeRange: discovery.TimeRange{
					Start: tt.timestamps[len(tt.timestamps)-1],
					End:   tt.timestamps[0],
				},
			}

			report := assessor.AssessSchema(ctx, schema, sample)
			
			assert.InDelta(t, tt.expectScore, report.Dimensions.Timeliness.Score, 0.2,
				"Timeliness score should be close to expected")

			if tt.expectIssues {
				hasTimelinessIssue := false
				for _, issue := range report.Issues {
					if issue.Dimension == "Timeliness" {
						hasTimelinessIssue = true
						break
					}
				}
				assert.True(t, hasTimelinessIssue, "Should identify timeliness issues")
			}
		})
	}
}

func TestAssessor_Uniqueness(t *testing.T) {
	config := quality.DefaultConfig()
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	schema := discovery.Schema{
		Name: "TestSchema",
		Attributes: []discovery.Attribute{
			{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
			{Name: "email", DataType: discovery.DataTypeString},
		},
	}

	tests := []struct {
		name         string
		records      []map[string]interface{}
		expectScore  float64
		expectIssues bool
	}{
		{
			name: "all unique",
			records: []map[string]interface{}{
				{"userId": "user1", "email": "user1@example.com"},
				{"userId": "user2", "email": "user2@example.com"},
				{"userId": "user3", "email": "user3@example.com"},
			},
			expectScore:  1.0,
			expectIssues: false,
		},
		{
			name: "duplicates present",
			records: []map[string]interface{}{
				{"userId": "user1", "email": "user1@example.com"},
				{"userId": "user1", "email": "user1@example.com"}, // duplicate
				{"userId": "user2", "email": "user2@example.com"},
				{"userId": "user2", "email": "different@example.com"}, // duplicate userId
			},
			expectScore:  0.5, // 2 duplicates out of 4 records
			expectIssues: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			sample := discovery.DataSample{
				SampleSize: len(tt.records),
				Records:    tt.records,
				TimeRange: discovery.TimeRange{
					Start: time.Now().Add(-1 * time.Hour),
					End:   time.Now(),
				},
			}

			report := assessor.AssessSchema(ctx, schema, sample)
			
			assert.InDelta(t, tt.expectScore, report.Dimensions.Uniqueness.Score, 0.1,
				"Uniqueness score should be close to expected")

			if tt.expectIssues {
				hasUniquenessIssue := false
				for _, issue := range report.Issues {
					if issue.Dimension == "Uniqueness" {
						hasUniquenessIssue = true
						break
					}
				}
				assert.True(t, hasUniquenessIssue, "Should identify uniqueness issues")
			}
		})
	}
}

func TestAssessor_Consistency(t *testing.T) {
	config := quality.DefaultConfig()
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	schema := discovery.Schema{
		Name: "TestSchema",
		Attributes: []discovery.Attribute{
			{Name: "email", DataType: discovery.DataTypeString},
			{Name: "value", DataType: discovery.DataTypeNumeric},
		},
	}

	// Test format consistency
	sample := discovery.DataSample{
		SampleSize: 5,
		Records: []map[string]interface{}{
			{"email": "user@example.com", "value": 10.0},
			{"email": "admin@test.org", "value": 20.0},
			{"email": "not-an-email", "value": 30.0}, // Inconsistent format
			{"email": "support@company.net", "value": 40.0},
			{"email": "also-not-email", "value": 500.0}, // Outlier value
		},
		TimeRange: discovery.TimeRange{
			Start: time.Now().Add(-1 * time.Hour),
			End:   time.Now(),
		},
	}

	report := assessor.AssessSchema(ctx, schema, sample)
	
	// Should detect consistency issues
	assert.Less(t, report.Dimensions.Consistency.Score, 1.0,
		"Consistency score should be less than perfect due to format inconsistencies")

	// Should generate consistency recommendations
	hasConsistencyRec := false
	for _, rec := range report.Recommendations {
		if rec == "Create data transformation rules to standardize formats" ||
		   rec == "Document expected data formats for each attribute" {
			hasConsistencyRec = true
			break
		}
	}
	assert.True(t, hasConsistencyRec, "Should recommend consistency improvements")
}

func TestAssessor_OverallScore(t *testing.T) {
	config := quality.DefaultConfig()
	assessor := quality.NewAssessor(config)
	ctx := context.Background()

	// Create a perfect quality sample
	schema := discovery.Schema{
		Name: "PerfectSchema",
		Attributes: []discovery.Attribute{
			{Name: "id", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
			{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
		},
	}

	records := make([]map[string]interface{}, 10)
	now := time.Now()
	for i := 0; i < 10; i++ {
		records[i] = map[string]interface{}{
			"id":        i,
			"timestamp": now.Add(-time.Duration(i) * time.Second),
		}
	}

	sample := discovery.DataSample{
		SampleSize: len(records),
		Records:    records,
		TimeRange: discovery.TimeRange{
			Start: now.Add(-10 * time.Second),
			End:   now,
		},
	}

	report := assessor.AssessSchema(ctx, schema, sample)

	// Verify overall score calculation
	expectedScore := report.Dimensions.Completeness.Score*config.CompletenessWeight +
		report.Dimensions.Consistency.Score*config.ConsistencyWeight +
		report.Dimensions.Timeliness.Score*config.TimelinessWeight +
		report.Dimensions.Uniqueness.Score*config.UniquenessWeight +
		report.Dimensions.Validity.Score*config.ValidityWeight

	assert.InDelta(t, expectedScore, report.OverallScore, 0.01,
		"Overall score should be weighted average of dimensions")
}

func TestAssessor_Configuration(t *testing.T) {
	// Test custom configuration
	config := quality.Config{
		CompletenessThreshold: 0.99,
		ConsistencyThreshold:  0.95,
		TimelinessThreshold:   1 * time.Minute,
		UniquenessThreshold:   1.0,
		ValidityThreshold:     0.99,
		CompletenessWeight:    0.4,
		ConsistencyWeight:     0.2,
		TimelinessWeight:      0.2,
		UniquenessWeight:      0.1,
		ValidityWeight:        0.1,
	}

	assessor := quality.NewAssessor(config)
	require.NotNil(t, assessor)

	// Test default configuration
	defaultConfig := quality.DefaultConfig()
	assert.Equal(t, 0.95, defaultConfig.CompletenessThreshold)
	assert.Equal(t, 0.90, defaultConfig.ConsistencyThreshold)
	assert.Equal(t, 5*time.Minute, defaultConfig.TimelinessThreshold)
	assert.Equal(t, 0.25, defaultConfig.CompletenessWeight)
}