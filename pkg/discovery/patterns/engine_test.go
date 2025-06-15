package patterns_test

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery/patterns"
)

func TestEngine_DetectPatterns(t *testing.T) {
	engine := patterns.NewEngine(false)

	tests := []struct {
		name         string
		data         []interface{}
		dataType     discovery.DataType
		expectCount  int
		expectTypes  []discovery.PatternType
	}{
		{
			name: "numeric time series with trend",
			data: []interface{}{
				10.0, 12.0, 14.0, 16.0, 18.0, 20.0, 22.0, 24.0, 26.0, 28.0,
			},
			dataType:    discovery.DataTypeNumeric,
			expectCount: 1,
			expectTypes: []discovery.PatternType{discovery.PatternTypeTrend},
		},
		{
			name: "string data with email format",
			data: []interface{}{
				"user1@example.com", "user2@example.com", "user3@example.com",
				"admin@company.org", "support@company.org",
			},
			dataType:    discovery.DataTypeString,
			expectCount: 1,
			expectTypes: []discovery.PatternType{discovery.PatternTypeFormat},
		},
		{
			name:         "insufficient data",
			data:         []interface{}{1, 2, 3},
			dataType:     discovery.DataTypeNumeric,
			expectCount:  0,
			expectTypes:  []discovery.PatternType{},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			patterns := engine.DetectPatterns(tt.data, tt.dataType)
			
			assert.Len(t, patterns, tt.expectCount)
			
			if tt.expectCount > 0 {
				// Check pattern types
				foundTypes := make(map[discovery.PatternType]bool)
				for _, p := range patterns {
					foundTypes[p.Type] = true
				}
				
				for _, expectedType := range tt.expectTypes {
					assert.True(t, foundTypes[expectedType], 
						"Expected pattern type %s not found", expectedType)
				}
			}
		})
	}
}

func TestTimeSeriesDetector_DetectPatterns(t *testing.T) {
	detector := patterns.NewTimeSeriesDetector()

	tests := []struct {
		name        string
		data        []interface{}
		expectTrend bool
		expectAnomaly bool
	}{
		{
			name: "linear increasing trend",
			data: []interface{}{
				1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
			},
			expectTrend: true,
			expectAnomaly: false,
		},
		{
			name: "data with outliers",
			data: []interface{}{
				10.0, 10.5, 9.8, 10.2, 100.0, 10.1, 9.9, 10.3, 10.0, 9.7,
			},
			expectTrend: false,
			expectAnomaly: true,
		},
		{
			name: "seasonal pattern",
			data: []interface{}{
				10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0,
				10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0, 10.0, 20.0,
			},
			expectTrend: false,
			expectAnomaly: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			patterns := detector.DetectPatterns(tt.data, discovery.DataTypeNumeric)
			
			hasTrend := false
			hasAnomaly := false
			
			for _, p := range patterns {
				if p.Type == discovery.PatternTypeTrend {
					hasTrend = true
				}
				if p.Type == discovery.PatternTypeAnomaly {
					hasAnomaly = true
				}
			}
			
			assert.Equal(t, tt.expectTrend, hasTrend, "Trend detection mismatch")
			assert.Equal(t, tt.expectAnomaly, hasAnomaly, "Anomaly detection mismatch")
		})
	}
}

func TestDistributionDetector_DetectPatterns(t *testing.T) {
	detector := patterns.NewDistributionDetector()

	tests := []struct {
		name               string
		data               []interface{}
		expectDistribution string
	}{
		{
			name: "uniform distribution",
			data: func() []interface{} {
				data := make([]interface{}, 100)
				for i := 0; i < 100; i++ {
					data[i] = float64(i)
				}
				return data
			}(),
			expectDistribution: "uniform",
		},
		{
			name: "normal-like distribution",
			data: func() []interface{} {
				// Simulate normal-like data
				data := make([]interface{}, 100)
				values := []float64{
					40, 42, 44, 45, 46, 47, 48, 48, 49, 49, 50, 50, 50, 51, 51, 52, 52, 53, 54, 56, 58, 60,
				}
				for i := 0; i < 100; i++ {
					data[i] = values[i%len(values)]
				}
				return data
			}(),
			expectDistribution: "",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			patterns := detector.DetectPatterns(tt.data, discovery.DataTypeNumeric)
			
			foundDistribution := ""
			for _, p := range patterns {
				if p.Type == discovery.PatternTypeDistribution && p.Subtype != "" {
					foundDistribution = p.Subtype
					break
				}
			}
			
			if tt.expectDistribution != "" {
				assert.Equal(t, tt.expectDistribution, foundDistribution)
			}
		})
	}
}

func TestFormatDetector_DetectPatterns(t *testing.T) {
	detector := patterns.NewFormatDetector()

	tests := []struct {
		name         string
		data         []interface{}
		expectFormat string
	}{
		{
			name: "email format",
			data: []interface{}{
				"user1@example.com", "user2@example.com", "admin@test.org",
				"support@company.net", "info@website.com",
			},
			expectFormat: "email",
		},
		{
			name: "URL format",
			data: []interface{}{
				"https://example.com", "http://test.org", "https://api.service.com",
				"https://www.website.net", "http://localhost:8080",
			},
			expectFormat: "url",
		},
		{
			name: "UUID format",
			data: []interface{}{
				"550e8400-e29b-41d4-a716-446655440000",
				"6ba7b810-9dad-11d1-80b4-00c04fd430c8",
				"6ba7b811-9dad-11d1-80b4-00c04fd430c8",
				"6ba7b812-9dad-11d1-80b4-00c04fd430c8",
				"6ba7b814-9dad-11d1-80b4-00c04fd430c8",
			},
			expectFormat: "uuid",
		},
		{
			name: "mixed formats",
			data: []interface{}{
				"user@example.com", "https://example.com", "192.168.1.1",
				"another string", "test@test.com",
			},
			expectFormat: "", // No dominant format
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			patterns := detector.DetectPatterns(tt.data, discovery.DataTypeString)
			
			foundFormat := ""
			for _, p := range patterns {
				if p.Type == discovery.PatternTypeFormat && p.Confidence > 0.7 {
					foundFormat = p.Subtype
					break
				}
			}
			
			assert.Equal(t, tt.expectFormat, foundFormat)
		})
	}
}

func TestSequenceDetector_DetectPatterns(t *testing.T) {
	detector := patterns.NewSequenceDetector()

	tests := []struct {
		name           string
		data           []interface{}
		dataType       discovery.DataType
		expectSequence bool
		expectSubtype  string
	}{
		{
			name:           "arithmetic sequence",
			data:           []interface{}{2.0, 4.0, 6.0, 8.0, 10.0},
			dataType:       discovery.DataTypeNumeric,
			expectSequence: true,
			expectSubtype:  "arithmetic",
		},
		{
			name:           "string prefix sequence",
			data:           []interface{}{"user001", "user002", "user003", "user004"},
			dataType:       discovery.DataTypeString,
			expectSequence: true,
			expectSubtype:  "prefix",
		},
		{
			name:           "random numeric data",
			data:           []interface{}{1.5, 7.2, 3.9, 11.0, 5.5},
			dataType:       discovery.DataTypeNumeric,
			expectSequence: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			patterns := detector.DetectPatterns(tt.data, tt.dataType)
			
			hasSequence := false
			foundSubtype := ""
			
			for _, p := range patterns {
				if p.Type == discovery.PatternTypeSequence {
					hasSequence = true
					foundSubtype = p.Subtype
					break
				}
			}
			
			assert.Equal(t, tt.expectSequence, hasSequence)
			if tt.expectSequence {
				assert.Equal(t, tt.expectSubtype, foundSubtype)
			}
		})
	}
}

func TestDetectorIntegration(t *testing.T) {
	engine := patterns.NewEngine(false)

	// Test with complex data that has multiple patterns
	complexData := []interface{}{
		10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0,
		60.0, 65.0, 70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 100.0, 105.0,
		110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0, 150.0, 500.0, // Outlier
	}

	patterns := engine.DetectPatterns(complexData, discovery.DataTypeNumeric)
	require.NotEmpty(t, patterns)

	// Should detect both trend and anomaly
	foundTypes := make(map[discovery.PatternType]bool)
	for _, p := range patterns {
		foundTypes[p.Type] = true
		t.Logf("Found pattern: %s (confidence: %.2f)", p.Type, p.Confidence)
	}

	assert.True(t, foundTypes[discovery.PatternTypeTrend], "Should detect trend")
	assert.True(t, foundTypes[discovery.PatternTypeAnomaly], "Should detect anomaly")

	// Patterns should be sorted by confidence
	for i := 1; i < len(patterns); i++ {
		assert.GreaterOrEqual(t, patterns[i-1].Confidence, patterns[i].Confidence,
			"Patterns should be sorted by confidence descending")
	}
}