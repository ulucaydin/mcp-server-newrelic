# Track 1: Discovery Core - Ultra Detailed Implementation

## Overview
The Discovery Core is the bedrock of UDS - a Go-based engine that discovers, profiles, and understands any data schema without prior knowledge. This track implements the comprehensive discovery primitives with ML enhancement, intelligent sampling, and relationship mining.

## Architecture

```go
// pkg/discovery/architecture.go
package discovery

/*
Discovery Core Architecture:

┌─────────────────────────────────────────────────────────────┐
│                     Discovery Engine                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │   Schema    │  │   Sampling   │  │  Relationship   │  │
│  │ Discovery   │  │   Engine     │  │    Miner        │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────┘  │
│         │                 │                    │           │
│  ┌──────▼──────────────────▼──────────────────▼────────┐  │
│  │              Intelligent Profiler                    │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌──────────┐ │  │
│  │  │Numeric │  │ String │  │  Time  │  │ Pattern  │ │  │
│  │  │Analyzer│  │Analyzer│  │Analyzer│  │ Library  │ │  │
│  │  └────────┘  └────────┘  └────────┘  └──────────┘ │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                  Knowledge Cache                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │  Schema  │  │ Pattern  │  │  Relationship    │ │  │
│  │  │  Store   │  │  Store   │  │     Graph        │ │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
*/
```

## Week 1: Core Primitives & Interfaces

### Day 1-2: Project Setup & Core Interfaces

```go
// pkg/discovery/types.go
package discovery

import (
    "context"
    "time"
)

// Core domain types
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

// Sampling strategies
type SamplingStrategy interface {
    Sample(ctx context.Context, params SamplingParams) (DataSample, error)
    EstimateSampleSize(totalRecords int64) int64
    GetStrategyName() string
}

type SamplingParams struct {
    EventType       string
    TimeRange       TimeRange
    MaxSamples      int64
    Attributes      []string
    Filter          string
}

// Quality assessment
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

// Discovery interfaces
type DiscoveryEngine interface {
    // Core discovery operations
    DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error)
    DiscoverWithIntelligence(ctx context.Context, hints DiscoveryHints) (*DiscoveryResult, error)
    ProfileSchema(ctx context.Context, eventType string, depth ProfileDepth) (*Schema, error)
    
    // Sampling operations
    GetSamplingStrategy(ctx context.Context, eventType string) (SamplingStrategy, error)
    SampleData(ctx context.Context, params SamplingParams) (DataSample, error)
    
    // Quality operations
    AssessQuality(ctx context.Context, schema string) (*QualityReport, error)
    
    // Relationship operations
    FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error)
}
```

### Day 3-4: NRDB Client & Mock Implementation

```go
// pkg/discovery/nrdb/client.go
package nrdb

import (
    "context"
    "encoding/json"
    "fmt"
    "net/http"
    "time"
)

type Client struct {
    apiKey      string
    accountID   string
    httpClient  *http.Client
    baseURL     string
    rateLimiter *RateLimiter
}

type QueryResult struct {
    Results  []map[string]interface{} `json:"results"`
    Metadata QueryMetadata            `json:"metadata"`
}

func (c *Client) Query(ctx context.Context, nrql string) (*QueryResult, error) {
    // Rate limiting
    if err := c.rateLimiter.Wait(ctx); err != nil {
        return nil, fmt.Errorf("rate limit: %w", err)
    }
    
    req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL, nil)
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Api-Key", c.apiKey)
    req.Header.Set("Content-Type", "application/json")
    
    // Query payload
    payload := map[string]interface{}{
        "query": nrql,
        "account": c.accountID,
    }
    
    // Execute with retries
    var result QueryResult
    err = c.executeWithRetry(ctx, req, payload, &result)
    
    return &result, err
}

// pkg/discovery/nrdb/mock.go
package nrdb

type MockClient struct {
    schemas map[string][]map[string]interface{}
}

func NewMockClient() *MockClient {
    return &MockClient{
        schemas: map[string][]map[string]interface{}{
            "Transaction": {
                {"duration": 1.23, "error": false, "name": "/api/users", "timestamp": time.Now().Unix()},
                {"duration": 0.45, "error": true, "name": "/api/orders", "timestamp": time.Now().Unix()},
                {"duration": 2.10, "error": false, "name": "/api/users", "timestamp": time.Now().Unix()},
            },
            "NrConsumption": {
                {"cost": 123.45, "service": "APM", "usage": 1000000, "timestamp": time.Now().Unix()},
                {"cost": 67.89, "service": "Logs", "usage": 500000, "timestamp": time.Now().Unix()},
            },
            "PageView": {
                {"duration": 2.5, "userAgent": "Mozilla/5.0", "countryCode": "US", "timestamp": time.Now().Unix()},
                {"duration": 1.8, "userAgent": "Chrome/90", "countryCode": "GB", "timestamp": time.Now().Unix()},
            },
        },
    }
}
```

### Day 5: Schema Discovery Implementation

```go
// pkg/discovery/schema_discovery.go
package discovery

import (
    "context"
    "fmt"
    "sync"
    "time"
)

type SchemaDiscoveryEngine struct {
    nrdb            NRDBClient
    cache           *SchemaCache
    patternLib      *PatternLibrary
    config          DiscoveryConfig
    metrics         *Metrics
}

func (e *SchemaDiscoveryEngine) DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error) {
    startTime := time.Now()
    defer func() {
        e.metrics.RecordDiscoveryDuration(time.Since(startTime))
    }()
    
    // Check cache first
    if cached := e.cache.GetSchemas(filter); cached != nil {
        e.metrics.IncrementCacheHit()
        return cached, nil
    }
    
    // Discover event types
    eventTypes, err := e.discoverEventTypes(ctx, filter)
    if err != nil {
        return nil, fmt.Errorf("discover event types: %w", err)
    }
    
    // Parallel schema discovery
    schemas := make([]Schema, 0, len(eventTypes))
    schemaChan := make(chan Schema, len(eventTypes))
    errorChan := make(chan error, len(eventTypes))
    
    var wg sync.WaitGroup
    semaphore := make(chan struct{}, e.config.MaxConcurrency)
    
    for _, eventType := range eventTypes {
        wg.Add(1)
        go func(et string) {
            defer wg.Done()
            
            // Acquire semaphore
            semaphore <- struct{}{}
            defer func() { <-semaphore }()
            
            schema, err := e.discoverSingleSchema(ctx, et)
            if err != nil {
                errorChan <- fmt.Errorf("schema %s: %w", et, err)
                return
            }
            
            schemaChan <- schema
        }(eventType)
    }
    
    // Wait for completion
    go func() {
        wg.Wait()
        close(schemaChan)
        close(errorChan)
    }()
    
    // Collect results
    var errors []error
    for schema := range schemaChan {
        schemas = append(schemas, schema)
    }
    
    for err := range errorChan {
        errors = append(errors, err)
    }
    
    if len(errors) > 0 {
        e.metrics.RecordDiscoveryErrors(errors)
        // Continue with partial results
    }
    
    // Cache results
    e.cache.SetSchemas(filter, schemas, e.config.CacheTTL)
    
    return schemas, nil
}

func (e *SchemaDiscoveryEngine) discoverSingleSchema(ctx context.Context, eventType string) (Schema, error) {
    schema := Schema{
        ID:           generateSchemaID(eventType),
        Name:         eventType,
        EventType:    eventType,
        DiscoveredAt: time.Now(),
    }
    
    // Get sample data
    samples, err := e.getSamples(ctx, eventType)
    if err != nil {
        return schema, fmt.Errorf("get samples: %w", err)
    }
    
    // Discover attributes
    attributes := e.discoverAttributes(samples)
    
    // Deep analysis of each attribute
    for i, attr := range attributes {
        analyzed := e.analyzeAttribute(ctx, eventType, attr, samples)
        attributes[i] = analyzed
    }
    
    schema.Attributes = attributes
    
    // Assess data volume
    schema.DataVolume = e.assessDataVolume(ctx, eventType)
    
    // Detect patterns
    schema.Patterns = e.detectSchemaPatterns(attributes, samples)
    
    // Calculate quality
    schema.Quality = e.calculateQuality(attributes, samples)
    
    return schema, nil
}
```

## Week 2: Intelligence Layer

### Day 6-7: Intelligent Sampling

```go
// pkg/discovery/sampling/intelligent.go
package sampling

import (
    "context"
    "math"
    "time"
)

type IntelligentSampler struct {
    strategies map[string]SamplingStrategy
    analyzer   *DataCharacteristicsAnalyzer
}

func (s *IntelligentSampler) SelectStrategy(ctx context.Context, profile DataProfile) (SamplingStrategy, error) {
    // Analyze data characteristics
    characteristics := s.analyzer.Analyze(profile)
    
    switch {
    case characteristics.Volume > 1e9: // > 1 billion records
        return s.strategies["adaptive_stratified"], nil
        
    case characteristics.HasTimeSeries && characteristics.HasSeasonality:
        return s.strategies["seasonal_aware"], nil
        
    case characteristics.HighCardinality > 0.8:
        return s.strategies["reservoir"], nil
        
    case characteristics.IsSkewed:
        return s.strategies["weighted"], nil
        
    default:
        return s.strategies["random"], nil
    }
}

// Stratified sampling for high-volume data
type StratifiedSampling struct {
    stratifyBy   string
    sampleRatio  float64
    minPerStrata int
    maxPerStrata int
}

func (s *StratifiedSampling) Sample(ctx context.Context, params SamplingParams) (DataSample, error) {
    // First, get strata distribution
    strataQuery := fmt.Sprintf(`
        SELECT %s as stratum, count(*) as cnt 
        FROM %s 
        WHERE timestamp >= %d AND timestamp <= %d
        FACET %s 
        LIMIT 1000
    `, s.stratifyBy, params.EventType, params.TimeRange.Start, params.TimeRange.End, s.stratifyBy)
    
    strataResult, err := s.nrdb.Query(ctx, strataQuery)
    if err != nil {
        return DataSample{}, err
    }
    
    // Calculate samples per stratum
    samplePlan := s.calculateSampleDistribution(strataResult)
    
    // Parallel sampling from each stratum
    return s.executeSamplingPlan(ctx, samplePlan, params)
}

// Seasonal-aware sampling
type SeasonalSampling struct {
    seasonalityDetector *SeasonalityDetector
    baseStrategy        SamplingStrategy
}

func (s *SeasonalSampling) Sample(ctx context.Context, params SamplingParams) (DataSample, error) {
    // Detect seasonality period
    period, confidence := s.seasonalityDetector.DetectPeriod(ctx, params.EventType)
    
    if confidence < 0.7 {
        // Fall back to base strategy
        return s.baseStrategy.Sample(ctx, params)
    }
    
    // Sample across multiple periods
    samplesPerPeriod := params.MaxSamples / int64(math.Ceil(float64(params.TimeRange.Duration()) / float64(period)))
    
    var allSamples []map[string]interface{}
    
    for t := params.TimeRange.Start; t < params.TimeRange.End; t += period {
        periodParams := params
        periodParams.TimeRange = TimeRange{
            Start: t,
            End:   t + period,
        }
        periodParams.MaxSamples = samplesPerPeriod
        
        periodSample, err := s.baseStrategy.Sample(ctx, periodParams)
        if err != nil {
            return DataSample{}, err
        }
        
        allSamples = append(allSamples, periodSample.Records...)
    }
    
    return DataSample{
        Records:    allSamples,
        SampleSize: len(allSamples),
        Strategy:   "seasonal_aware",
        Metadata: map[string]interface{}{
            "period":     period,
            "confidence": confidence,
        },
    }, nil
}
```

### Day 8-9: Deep Attribute Analysis

```go
// pkg/discovery/analysis/attribute_analyzer.go
package analysis

import (
    "context"
    "regexp"
    "strings"
)

type AttributeAnalyzer struct {
    typeInferrer     *TypeInferrer
    semanticAnalyzer *SemanticAnalyzer
    patternDetector  *PatternDetector
    statisticsCalc   *StatisticsCalculator
}

func (a *AttributeAnalyzer) AnalyzeAttribute(ctx context.Context, name string, values []interface{}) AttributeProfile {
    profile := AttributeProfile{
        Name: name,
    }
    
    // Infer data type
    profile.DataType = a.typeInferrer.InferType(values)
    
    // Calculate statistics based on type
    switch profile.DataType {
    case DataTypeNumeric:
        profile.Statistics = a.statisticsCalc.CalculateNumeric(values)
    case DataTypeString:
        profile.Statistics = a.statisticsCalc.CalculateString(values)
    case DataTypeTimestamp:
        profile.Statistics = a.statisticsCalc.CalculateTemporal(values)
    }
    
    // Semantic type inference
    profile.SemanticType = a.semanticAnalyzer.InferSemantic(name, values, profile.DataType)
    
    // Pattern detection
    profile.Patterns = a.patternDetector.DetectPatterns(values, profile.DataType)
    
    // Cardinality analysis
    profile.Cardinality = a.analyzeCardinality(values)
    
    // Quality assessment
    profile.Quality = a.assessAttributeQuality(values)
    
    return profile
}

// Semantic type inference with ML enhancement
type SemanticAnalyzer struct {
    patterns map[SemanticType]*regexp.Regexp
    ml       *MLInferenceEngine
}

func (s *SemanticAnalyzer) InferSemantic(name string, values []interface{}, dataType DataType) SemanticType {
    // Rule-based inference first
    semanticType := s.ruleBasedInference(name, values)
    if semanticType != SemanticTypeCustom {
        return semanticType
    }
    
    // ML-based inference for uncertain cases
    if s.ml != nil {
        mlPrediction := s.ml.PredictSemanticType(name, values)
        if mlPrediction.Confidence > 0.8 {
            return mlPrediction.Type
        }
    }
    
    return SemanticTypeCustom
}

func (s *SemanticAnalyzer) ruleBasedInference(name string, values []interface{}) SemanticType {
    nameLower := strings.ToLower(name)
    
    // Name-based hints
    switch {
    case strings.Contains(nameLower, "email"):
        return SemanticTypeEmail
    case strings.Contains(nameLower, "url") || strings.Contains(nameLower, "link"):
        return SemanticTypeURL
    case strings.Contains(nameLower, "ip") || strings.Contains(nameLower, "address"):
        return SemanticTypeIP
    case strings.Contains(nameLower, "country"):
        return SemanticTypeCountry
    case strings.Contains(nameLower, "duration") || strings.Contains(nameLower, "elapsed"):
        return SemanticTypeDuration
    }
    
    // Pattern-based detection
    sampleSize := min(100, len(values))
    for semanticType, pattern := range s.patterns {
        matches := 0
        for i := 0; i < sampleSize; i++ {
            if str, ok := values[i].(string); ok {
                if pattern.MatchString(str) {
                    matches++
                }
            }
        }
        
        if float64(matches)/float64(sampleSize) > 0.9 {
            return semanticType
        }
    }
    
    return SemanticTypeCustom
}
```

### Day 10: Pattern Detection Engine

```go
// pkg/discovery/patterns/engine.go
package patterns

import (
    "context"
    "math"
    "sort"
)

type PatternEngine struct {
    detectors []PatternDetector
    library   *PatternLibrary
    ml        *MLPatternDetector
}

type PatternDetector interface {
    DetectPatterns(data []interface{}, dataType DataType) []Pattern
    GetDetectorName() string
}

// Time series pattern detection
type TimeSeriesPatternDetector struct {
    statsAnalyzer *StatisticalAnalyzer
}

func (d *TimeSeriesPatternDetector) DetectPatterns(data []interface{}, dataType DataType) []Pattern {
    if dataType != DataTypeNumeric {
        return nil
    }
    
    patterns := []Pattern{}
    values := convertToFloat64Array(data)
    
    // Trend detection
    if trend := d.detectTrend(values); trend != nil {
        patterns = append(patterns, *trend)
    }
    
    // Seasonality detection
    if seasonal := d.detectSeasonality(values); seasonal != nil {
        patterns = append(patterns, *seasonal)
    }
    
    // Anomaly detection
    anomalies := d.detectAnomalies(values)
    patterns = append(patterns, anomalies...)
    
    // Change point detection
    changePoints := d.detectChangePoints(values)
    patterns = append(patterns, changePoints...)
    
    return patterns
}

func (d *TimeSeriesPatternDetector) detectSeasonality(values []float64) *Pattern {
    // FFT-based seasonality detection
    fft := d.computeFFT(values)
    
    // Find dominant frequencies
    peaks := d.findFrequencyPeaks(fft)
    
    if len(peaks) == 0 {
        return nil
    }
    
    // Convert to period
    dominantPeriod := len(values) / peaks[0].Frequency
    
    // Validate seasonality strength
    strength := d.calculateSeasonalityStrength(values, dominantPeriod)
    
    if strength < 0.5 {
        return nil
    }
    
    return &Pattern{
        Type:       PatternTypeSeasonal,
        Confidence: strength,
        Description: fmt.Sprintf("Seasonal pattern with period %d", dominantPeriod),
        Parameters: map[string]interface{}{
            "period":    dominantPeriod,
            "strength":  strength,
            "frequency": peaks[0].Frequency,
        },
    }
}

// Distribution pattern detection
type DistributionPatternDetector struct{}

func (d *DistributionPatternDetector) DetectPatterns(data []interface{}, dataType DataType) []Pattern {
    patterns := []Pattern{}
    
    if dataType == DataTypeNumeric {
        values := convertToFloat64Array(data)
        
        // Check for normal distribution
        if d.isNormallyDistributed(values) {
            patterns = append(patterns, Pattern{
                Type:        PatternTypeDistribution,
                Subtype:     "normal",
                Confidence:  d.calculateNormalityScore(values),
                Description: "Data follows normal distribution",
            })
        }
        
        // Check for power law
        if d.followsPowerLaw(values) {
            patterns = append(patterns, Pattern{
                Type:        PatternTypeDistribution,
                Subtype:     "power_law",
                Confidence:  d.calculatePowerLawScore(values),
                Description: "Data follows power law distribution",
            })
        }
    }
    
    return patterns
}
```

## Week 3: Relationship Mining & Quality

### Day 11-12: Relationship Discovery

```go
// pkg/discovery/relationships/miner.go
package relationships

import (
    "context"
    "strings"
)

type RelationshipMiner struct {
    joinAnalyzer     *JoinAnalyzer
    correlationCalc  *CorrelationCalculator
    graphBuilder     *GraphBuilder
}

type Relationship struct {
    Type            RelationType
    SourceSchema    string
    TargetSchema    string
    SourceAttribute string
    TargetAttribute string
    Confidence      float64
    Evidence        []Evidence
    Metadata        map[string]interface{}
}

func (m *RelationshipMiner) FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error) {
    relationships := []Relationship{}
    
    // Phase 1: Name-based relationship hints
    nameHints := m.findNameBasedHints(schemas)
    
    // Phase 2: Test join relationships
    for _, hint := range nameHints {
        if rel := m.testJoinRelationship(ctx, hint); rel != nil {
            relationships = append(relationships, *rel)
        }
    }
    
    // Phase 3: Statistical correlations
    correlations := m.findStatisticalCorrelations(ctx, schemas)
    relationships = append(relationships, correlations...)
    
    // Phase 4: Temporal relationships
    temporal := m.findTemporalRelationships(ctx, schemas)
    relationships = append(relationships, temporal...)
    
    // Build relationship graph
    graph := m.graphBuilder.BuildGraph(relationships)
    
    // Find transitive relationships
    transitive := m.findTransitiveRelationships(graph)
    relationships = append(relationships, transitive...)
    
    return relationships, nil
}

func (m *RelationshipMiner) testJoinRelationship(ctx context.Context, hint JoinHint) *Relationship {
    // Sample data from both schemas
    sourceSample := m.sampleAttribute(ctx, hint.SourceSchema, hint.SourceAttr)
    targetSample := m.sampleAttribute(ctx, hint.TargetSchema, hint.TargetAttr)
    
    // Calculate join statistics
    stats := m.joinAnalyzer.AnalyzeJoin(sourceSample, targetSample)
    
    if stats.MatchRatio < 0.1 {
        return nil // Too few matches
    }
    
    // Test actual join
    joinResult := m.testActualJoin(ctx, hint, stats)
    
    if joinResult.Success {
        return &Relationship{
            Type:            RelationshipTypeJoin,
            SourceSchema:    hint.SourceSchema,
            TargetSchema:    hint.TargetSchema,
            SourceAttribute: hint.SourceAttr,
            TargetAttribute: hint.TargetAttr,
            Confidence:      joinResult.Confidence,
            Evidence: []Evidence{
                {Type: "match_ratio", Value: stats.MatchRatio},
                {Type: "cardinality", Value: stats.CardinalityRatio},
                {Type: "null_handling", Value: stats.NullHandling},
            },
            Metadata: map[string]interface{}{
                "join_type":      joinResult.JoinType,
                "estimated_rows": joinResult.EstimatedRows,
            },
        }
    }
    
    return nil
}

// Advanced correlation detection
func (m *RelationshipMiner) findStatisticalCorrelations(ctx context.Context, schemas []Schema) []Relationship {
    relationships := []Relationship{}
    
    // Find numeric attributes across schemas
    numericAttrs := m.findNumericAttributes(schemas)
    
    // Test correlations between numeric attributes
    for i, attr1 := range numericAttrs {
        for j, attr2 := range numericAttrs {
            if i >= j {
                continue // Avoid duplicates
            }
            
            correlation := m.testCorrelation(ctx, attr1, attr2)
            if math.Abs(correlation.Coefficient) > 0.7 {
                relationships = append(relationships, Relationship{
                    Type:            RelationshipTypeCorrelation,
                    SourceSchema:    attr1.Schema,
                    TargetSchema:    attr2.Schema,
                    SourceAttribute: attr1.Name,
                    TargetAttribute: attr2.Name,
                    Confidence:      math.Abs(correlation.Coefficient),
                    Evidence: []Evidence{
                        {Type: "pearson_r", Value: correlation.Coefficient},
                        {Type: "p_value", Value: correlation.PValue},
                        {Type: "sample_size", Value: correlation.SampleSize},
                    },
                })
            }
        }
    }
    
    return relationships
}
```

### Day 13-14: Quality Assessment

```go
// pkg/discovery/quality/assessor.go
package quality

import (
    "context"
    "math"
)

type QualityAssessor struct {
    rules      []QualityRule
    ml         *QualityMLModel
    benchmarks *QualityBenchmarks
}

func (a *QualityAssessor) AssessSchema(ctx context.Context, schema Schema, samples DataSample) QualityReport {
    report := QualityReport{
        SchemaName: schema.Name,
        Timestamp:  time.Now(),
    }
    
    // Dimension 1: Completeness
    completeness := a.assessCompleteness(schema, samples)
    report.Completeness = completeness
    
    // Dimension 2: Consistency
    consistency := a.assessConsistency(schema, samples)
    report.Consistency = consistency
    
    // Dimension 3: Timeliness
    timeliness := a.assessTimeliness(schema, samples)
    report.Timeliness = timeliness
    
    // Dimension 4: Validity
    validity := a.assessValidity(schema, samples)
    report.Validity = validity
    
    // Dimension 5: Uniqueness
    uniqueness := a.assessUniqueness(schema, samples)
    report.Uniqueness = uniqueness
    
    // Calculate overall score
    report.OverallScore = a.calculateOverallScore(report)
    
    // Identify issues
    report.Issues = a.identifyIssues(report)
    
    // Generate recommendations
    report.Recommendations = a.generateRecommendations(report)
    
    return report
}

func (a *QualityAssessor) assessCompleteness(schema Schema, samples DataSample) CompletenessScore {
    score := CompletenessScore{
        AttributeScores: make(map[string]float64),
    }
    
    for _, attr := range schema.Attributes {
        nullCount := 0
        totalCount := len(samples.Records)
        
        for _, record := range samples.Records {
            if record[attr.Name] == nil {
                nullCount++
            }
        }
        
        attrCompleteness := 1.0 - float64(nullCount)/float64(totalCount)
        score.AttributeScores[attr.Name] = attrCompleteness
        
        // Check against expected completeness
        if expected, ok := a.benchmarks.GetExpectedCompleteness(schema.Name, attr.Name); ok {
            if attrCompleteness < expected {
                score.Issues = append(score.Issues, QualityIssue{
                    Type:     "completeness",
                    Severity: "warning",
                    Attribute: attr.Name,
                    Message:  fmt.Sprintf("Completeness %.2f%% below expected %.2f%%", 
                             attrCompleteness*100, expected*100),
                })
            }
        }
    }
    
    // Overall completeness
    sum := 0.0
    for _, v := range score.AttributeScores {
        sum += v
    }
    score.Overall = sum / float64(len(score.AttributeScores))
    
    return score
}

// ML-enhanced quality prediction
type QualityMLModel struct {
    model *tensorflow.Model
}

func (m *QualityMLModel) PredictQualityTrend(historical []QualityReport) QualityPrediction {
    // Convert historical reports to feature vectors
    features := m.extractFeatures(historical)
    
    // Run prediction
    prediction := m.model.Predict(features)
    
    return QualityPrediction{
        FutureScore: prediction.Score,
        Confidence:  prediction.Confidence,
        Risks:       m.identifyRisks(prediction),
        Timeline:    "next_7_days",
    }
}
```

### Day 15: Integration & Testing

```go
// pkg/discovery/integration_test.go
package discovery

import (
    "context"
    "testing"
    "time"
)

func TestFullDiscoveryWorkflow(t *testing.T) {
    // Setup
    engine := NewDiscoveryEngine(Config{
        NRDBClient:      NewMockNRDBClient(),
        CacheEnabled:    true,
        MLEnabled:       true,
        MaxConcurrency:  5,
    })
    
    ctx := context.Background()
    
    // Test 1: Basic discovery
    t.Run("BasicDiscovery", func(t *testing.T) {
        schemas, err := engine.DiscoverSchemas(ctx, DiscoveryFilter{})
        assert.NoError(t, err)
        assert.Greater(t, len(schemas), 0)
        
        // Verify schema structure
        for _, schema := range schemas {
            assert.NotEmpty(t, schema.ID)
            assert.NotEmpty(t, schema.Name)
            assert.Greater(t, len(schema.Attributes), 0)
            assert.Greater(t, schema.Quality.OverallScore, 0.0)
        }
    })
    
    // Test 2: Intelligent discovery with hints
    t.Run("IntelligentDiscovery", func(t *testing.T) {
        hints := DiscoveryHints{
            Keywords: []string{"transaction", "error", "latency"},
            Purpose:  "performance analysis",
        }
        
        result, err := engine.DiscoverWithIntelligence(ctx, hints)
        assert.NoError(t, err)
        assert.NotNil(t, result)
        
        // Should prioritize performance-related schemas
        assert.Contains(t, result.Schemas[0].Name, "Transaction")
        assert.Greater(t, len(result.Patterns), 0)
        assert.Greater(t, len(result.Insights), 0)
    })
    
    // Test 3: Relationship discovery
    t.Run("RelationshipDiscovery", func(t *testing.T) {
        schemas, _ := engine.DiscoverSchemas(ctx, DiscoveryFilter{})
        relationships, err := engine.FindRelationships(ctx, schemas)
        
        assert.NoError(t, err)
        assert.Greater(t, len(relationships), 0)
        
        // Verify relationship quality
        for _, rel := range relationships {
            assert.Greater(t, rel.Confidence, 0.5)
            assert.NotEmpty(t, rel.Evidence)
        }
    })
}

// Benchmark tests
func BenchmarkDiscoveryEngine(b *testing.B) {
    engine := NewDiscoveryEngine(Config{
        NRDBClient:     NewMockNRDBClient(),
        CacheEnabled:   false, // Disable cache for benchmarking
        MaxConcurrency: 10,
    })
    
    ctx := context.Background()
    
    b.Run("SingleSchema", func(b *testing.B) {
        for i := 0; i < b.N; i++ {
            _, _ = engine.ProfileSchema(ctx, "Transaction", ProfileDepthFull)
        }
    })
    
    b.Run("ParallelDiscovery", func(b *testing.B) {
        for i := 0; i < b.N; i++ {
            _, _ = engine.DiscoverSchemas(ctx, DiscoveryFilter{})
        }
    })
}
```

## Week 4: Production Readiness

### Day 16-17: Caching & Performance

```go
// pkg/discovery/cache/multi_layer.go
package cache

import (
    "context"
    "encoding/json"
    "time"
)

type MultiLayerCache struct {
    l1     *MemoryCache    // Hot data (microseconds)
    l2     *RedisCache     // Warm data (milliseconds)
    stats  *CacheStats
}

func (c *MultiLayerCache) Get(key string) (interface{}, bool) {
    // L1 lookup
    if val, ok := c.l1.Get(key); ok {
        c.stats.L1Hit()
        return val, true
    }
    
    // L2 lookup
    if val, ok := c.l2.Get(key); ok {
        c.stats.L2Hit()
        // Promote to L1
        c.l1.Set(key, val, 5*time.Minute)
        return val, true
    }
    
    c.stats.Miss()
    return nil, false
}

// Predictive prefetching
type PredictiveCache struct {
    base      Cache
    predictor *AccessPredictor
    prefetch  chan PrefetchRequest
}

func (p *PredictiveCache) Get(key string) (interface{}, bool) {
    // Regular get
    val, found := p.base.Get(key)
    
    // Predict next accesses
    predictions := p.predictor.PredictNext(key)
    
    // Async prefetch
    for _, prediction := range predictions {
        select {
        case p.prefetch <- PrefetchRequest{Key: prediction.Key, Priority: prediction.Score}:
        default:
            // Don't block on prefetch
        }
    }
    
    return val, found
}
```

### Day 18-19: Monitoring & Observability

```go
// pkg/discovery/observability/metrics.go
package observability

import (
    "github.com/prometheus/client_golang/prometheus"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/trace"
)

type Metrics struct {
    // Discovery metrics
    discoveriesTotal    prometheus.Counter
    discoveryDuration   prometheus.Histogram
    schemasDiscovered   prometheus.Gauge
    
    // Quality metrics
    qualityScores       *prometheus.GaugeVec
    qualityIssues       *prometheus.CounterVec
    
    // Performance metrics
    cacheHitRate        *prometheus.GaugeVec
    queryDuration       prometheus.Histogram
    concurrentQueries   prometheus.Gauge
    
    // Pattern metrics
    patternsDetected    *prometheus.CounterVec
    patternConfidence   *prometheus.HistogramVec
    
    // Tracer
    tracer trace.Tracer
}

func (m *Metrics) TrackDiscovery(ctx context.Context, operation string) (context.Context, func()) {
    // Start span
    ctx, span := m.tracer.Start(ctx, "discovery."+operation)
    
    // Start timer
    timer := prometheus.NewTimer(m.discoveryDuration)
    
    // Increment counter
    m.discoveriesTotal.Inc()
    
    // Return cleanup function
    return ctx, func() {
        timer.ObserveDuration()
        span.End()
    }
}

// Custom dashboard definition
func (m *Metrics) ExportGrafanaDashboard() string {
    return `{
        "dashboard": {
            "title": "UDS Discovery Core",
            "panels": [
                {
                    "title": "Discovery Rate",
                    "targets": [
                        {"expr": "rate(uds_discoveries_total[5m])"}
                    ]
                },
                {
                    "title": "Schema Quality Scores",
                    "targets": [
                        {"expr": "uds_quality_score"}
                    ]
                },
                {
                    "title": "Pattern Detection Confidence",
                    "targets": [
                        {"expr": "histogram_quantile(0.95, uds_pattern_confidence)"}
                    ]
                }
            ]
        }
    }`
}
```

### Day 20: Documentation & Handoff

```go
// pkg/discovery/doc.go
/*
Package discovery implements the Universal Data Synthesizer's core discovery engine.

Architecture:

    DiscoveryEngine (main interface)
    ├── SchemaDiscovery (finds and profiles schemas)
    ├── IntelligentSampler (optimal data sampling)
    ├── PatternEngine (ML-enhanced pattern detection)
    ├── RelationshipMiner (discovers data relationships)
    └── QualityAssessor (data quality scoring)

Basic Usage:

    engine := discovery.NewEngine(config)
    
    // Simple discovery
    schemas, err := engine.DiscoverSchemas(ctx, filter)
    
    // Intelligent discovery with ML
    result, err := engine.DiscoverWithIntelligence(ctx, hints)

Advanced Features:

    - Automatic sampling strategy selection based on data volume
    - ML-enhanced pattern detection for complex patterns
    - Relationship discovery across schemas
    - Continuous learning from discoveries
    - Multi-layer caching with predictive prefetch
    - Full observability with OpenTelemetry

Performance Characteristics:

    - Concurrent schema discovery (configurable parallelism)
    - Streaming results for large datasets
    - Typical discovery time: 100ms-5s per schema
    - Memory usage: O(sample_size), not O(total_records)

For detailed documentation, see: https://github.com/yourorg/uds/wiki/discovery
*/
package discovery
```

## Key Deliverables

1. **Fully functional discovery engine** with intelligent sampling
2. **ML-enhanced pattern detection** that finds non-obvious patterns  
3. **Relationship mining** across schemas with confidence scoring
4. **Production-ready caching** with predictive prefetch
5. **Complete observability** with Prometheus + OpenTelemetry
6. **90%+ test coverage** including benchmarks
7. **Clear interfaces** for other tracks to integrate

## Success Metrics

- Discovers 100% of schemas in test environment
- Detects 10+ pattern types with >80% accuracy
- Finds valid relationships with >70% confidence
- Sub-second discovery for cached schemas
- Handles 1M+ record schemas efficiently through sampling

This implementation provides the rigorous foundation that the LLM orchestrator needs to make intelligent decisions about data discovery and analysis.