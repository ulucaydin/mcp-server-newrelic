package testutil

import (
	"fmt"
	"math/rand"
	"time"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// TestDataGenerator generates test data for integration tests
type TestDataGenerator struct {
	rand *rand.Rand
}

// NewTestDataGenerator creates a new test data generator
func NewTestDataGenerator(seed int64) *TestDataGenerator {
	return &TestDataGenerator{
		rand: rand.New(rand.NewSource(seed)),
	}
}

// GenerateSchema creates a test schema with realistic data
func (g *TestDataGenerator) GenerateSchema(name string, attributeCount int) discovery.Schema {
	attributes := make([]discovery.Attribute, attributeCount)
	
	// Common attributes
	attributes[0] = discovery.Attribute{
		Name:         "id",
		DataType:     discovery.DataTypeString,
		SemanticType: discovery.SemanticTypeID,
		Cardinality: discovery.CardinalityInfo{
			Unique:            attributeCount,
			Total:             attributeCount,
			Ratio:             1.0,
			IsHighCardinality: true,
		},
	}
	
	attributes[1] = discovery.Attribute{
		Name:     "timestamp",
		DataType: discovery.DataTypeTimestamp,
	}
	
	// Generate random attributes
	for i := 2; i < attributeCount; i++ {
		attributes[i] = g.generateRandomAttribute(i)
	}
	
	return discovery.Schema{
		ID:          fmt.Sprintf("schema-%s", name),
		Name:        name,
		EventType:   name,
		Attributes:  attributes,
		SampleCount: int64(g.rand.Intn(1000000) + 1000),
		DataVolume: discovery.DataVolumeProfile{
			TotalRecords:   int64(g.rand.Intn(10000000)),
			RecordsPerDay:  float64(g.rand.Intn(1000000)),
			RecordsPerHour: float64(g.rand.Intn(50000)),
		},
		Quality: discovery.QualityMetrics{
			OverallScore: 0.75 + g.rand.Float64()*0.25,
			Completeness: 0.8 + g.rand.Float64()*0.2,
			Consistency:  0.7 + g.rand.Float64()*0.3,
			Timeliness:   0.9 + g.rand.Float64()*0.1,
			Uniqueness:   0.95 + g.rand.Float64()*0.05,
			Validity:     0.85 + g.rand.Float64()*0.15,
		},
		DiscoveredAt:   time.Now(),
		LastAnalyzedAt: time.Now(),
	}
}

func (g *TestDataGenerator) generateRandomAttribute(index int) discovery.Attribute {
	dataTypes := []discovery.DataType{
		discovery.DataTypeString,
		discovery.DataTypeNumeric,
		discovery.DataTypeBoolean,
		discovery.DataTypeTimestamp,
	}
	
	semanticTypes := []discovery.SemanticType{
		discovery.SemanticTypeEmail,
		discovery.SemanticTypeURL,
		discovery.SemanticTypeIP,
		discovery.SemanticTypeMetric,
		discovery.SemanticTypeCategory,
	}
	
	dataType := dataTypes[g.rand.Intn(len(dataTypes))]
	
	attr := discovery.Attribute{
		Name:     fmt.Sprintf("attribute_%d", index),
		DataType: dataType,
	}
	
	// Randomly assign semantic type
	if g.rand.Float64() > 0.5 {
		attr.SemanticType = semanticTypes[g.rand.Intn(len(semanticTypes))]
	}
	
	// Generate cardinality info
	total := g.rand.Intn(10000) + 100
	unique := g.rand.Intn(total) + 1
	ratio := float64(unique) / float64(total)
	
	attr.Cardinality = discovery.CardinalityInfo{
		Unique:            unique,
		Total:             total,
		Ratio:             ratio,
		IsHighCardinality: ratio > 0.8,
	}
	
	return attr
}

// GenerateDataSample creates a test data sample
func (g *TestDataGenerator) GenerateDataSample(schema discovery.Schema, sampleSize int) discovery.DataSample {
	records := make([]map[string]interface{}, sampleSize)
	
	for i := 0; i < sampleSize; i++ {
		record := make(map[string]interface{})
		
		for _, attr := range schema.Attributes {
			record[attr.Name] = g.generateValue(attr, i)
		}
		
		records[i] = record
	}
	
	return discovery.DataSample{
		SampleSize: sampleSize,
		Records:    records,
		TimeRange: discovery.TimeRange{
			Start: time.Now().Add(-24 * time.Hour),
			End:   time.Now(),
		},
		Strategy: "test",
	}
}

func (g *TestDataGenerator) generateValue(attr discovery.Attribute, index int) interface{} {
	switch attr.DataType {
	case discovery.DataTypeString:
		switch attr.SemanticType {
		case discovery.SemanticTypeEmail:
			return fmt.Sprintf("user%d@example.com", index)
		case discovery.SemanticTypeURL:
			return fmt.Sprintf("https://example.com/page%d", index)
		case discovery.SemanticTypeIP:
			return fmt.Sprintf("192.168.1.%d", index%256)
		case discovery.SemanticTypeID:
			return fmt.Sprintf("ID-%d", index)
		default:
			return fmt.Sprintf("value_%d", index)
		}
		
	case discovery.DataTypeNumeric:
		if attr.SemanticType == discovery.SemanticTypeMetric {
			// Generate realistic metric values
			return 100.0 + g.rand.Float64()*50.0 + float64(index%10)
		}
		return float64(g.rand.Intn(1000))
		
	case discovery.DataTypeBoolean:
		return g.rand.Float64() > 0.5
		
	case discovery.DataTypeTimestamp:
		return time.Now().Add(-time.Duration(index) * time.Minute)
		
	default:
		return nil
	}
}

// GenerateTimeSeriesData creates time series data with patterns
func (g *TestDataGenerator) GenerateTimeSeriesData(size int, pattern string) []interface{} {
	data := make([]interface{}, size)
	
	switch pattern {
	case "trend":
		// Linear trend with noise
		for i := 0; i < size; i++ {
			data[i] = float64(i)*2.5 + g.rand.Float64()*5.0
		}
		
	case "seasonal":
		// Seasonal pattern
		for i := 0; i < size; i++ {
			data[i] = 50.0 + 20.0*math.Sin(float64(i)*2*math.Pi/12) + g.rand.Float64()*5.0
		}
		
	case "anomaly":
		// Normal data with anomalies
		for i := 0; i < size; i++ {
			if i%50 == 0 && i > 0 {
				// Inject anomaly
				data[i] = 100.0 + g.rand.Float64()*50.0
			} else {
				data[i] = 20.0 + g.rand.Float64()*10.0
			}
		}
		
	default:
		// Random data
		for i := 0; i < size; i++ {
			data[i] = g.rand.Float64() * 100.0
		}
	}
	
	return data
}

// GenerateStringData creates string data with patterns
func (g *TestDataGenerator) GenerateStringData(size int, format string) []interface{} {
	data := make([]interface{}, size)
	
	switch format {
	case "email":
		for i := 0; i < size; i++ {
			data[i] = fmt.Sprintf("user%d@example.com", i)
		}
		
	case "url":
		for i := 0; i < size; i++ {
			data[i] = fmt.Sprintf("https://example.com/page/%d", i)
		}
		
	case "uuid":
		for i := 0; i < size; i++ {
			data[i] = fmt.Sprintf("550e8400-e29b-41d4-a716-%012d", i)
		}
		
	case "mixed":
		formats := []string{"email", "url", "plain"}
		for i := 0; i < size; i++ {
			switch formats[i%3] {
			case "email":
				data[i] = fmt.Sprintf("user%d@test.com", i)
			case "url":
				data[i] = fmt.Sprintf("http://site%d.com", i)
			default:
				data[i] = fmt.Sprintf("string_%d", i)
			}
		}
		
	default:
		for i := 0; i < size; i++ {
			data[i] = fmt.Sprintf("value_%d", i)
		}
	}
	
	return data
}

// CreateTestSchemas creates a set of related schemas for testing
func CreateTestSchemas() []discovery.Schema {
	gen := NewTestDataGenerator(42)
	
	schemas := []discovery.Schema{
		// APM schemas
		gen.GenerateSchema("Transaction", 15),
		gen.GenerateSchema("TransactionError", 12),
		gen.GenerateSchema("PageView", 10),
		
		// Infrastructure schemas
		gen.GenerateSchema("SystemSample", 20),
		gen.GenerateSchema("ProcessSample", 18),
		gen.GenerateSchema("NetworkSample", 16),
		
		// Custom schemas with relationships
		{
			Name:      "User",
			EventType: "User",
			Attributes: []discovery.Attribute{
				{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "email", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeEmail},
				{Name: "createdAt", DataType: discovery.DataTypeTimestamp},
			},
		},
		{
			Name:      "Order",
			EventType: "Order",
			Attributes: []discovery.Attribute{
				{Name: "orderId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "userId", DataType: discovery.DataTypeString, SemanticType: discovery.SemanticTypeID},
				{Name: "total", DataType: discovery.DataTypeNumeric, SemanticType: discovery.SemanticTypeMetric},
				{Name: "timestamp", DataType: discovery.DataTypeTimestamp},
			},
		},
	}
	
	// Set quality scores
	for i := range schemas {
		schemas[i].Quality = discovery.QualityMetrics{
			OverallScore: 0.85,
			Completeness: 0.9,
			Consistency:  0.85,
			Timeliness:   0.95,
			Uniqueness:   0.9,
			Validity:     0.8,
		}
		schemas[i].SampleCount = int64(10000 + i*1000)
	}
	
	return schemas
}

// CreateLowQualityData creates data with quality issues for testing
func CreateLowQualityData(size int) discovery.DataSample {
	records := make([]map[string]interface{}, size)
	
	for i := 0; i < size; i++ {
		record := make(map[string]interface{})
		
		// Add required fields
		record["id"] = fmt.Sprintf("ID-%d", i)
		record["timestamp"] = time.Now().Add(-time.Duration(i) * time.Hour)
		
		// Introduce quality issues
		if i%5 == 0 {
			// Missing values (20%)
			// Skip adding optional fields
		} else {
			record["name"] = fmt.Sprintf("Name-%d", i)
			record["value"] = float64(i)
		}
		
		if i%10 == 0 {
			// Null values
			record["name"] = nil
		}
		
		if i%20 == 0 {
			// Duplicate IDs
			record["id"] = "ID-0"
		}
		
		if i%15 == 0 {
			// Invalid format
			record["email"] = "not-an-email"
		} else {
			record["email"] = fmt.Sprintf("user%d@example.com", i)
		}
		
		// Add stale data
		if i > size/2 {
			record["timestamp"] = time.Now().Add(-30 * 24 * time.Hour)
		}
		
		records[i] = record
	}
	
	return discovery.DataSample{
		SampleSize: size,
		Records:    records,
		TimeRange: discovery.TimeRange{
			Start: time.Now().Add(-30 * 24 * time.Hour),
			End:   time.Now(),
		},
	}
}