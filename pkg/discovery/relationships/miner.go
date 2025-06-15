package relationships

import (
	"context"
	"fmt"
	"math"
	"sort"
	"strings"
	"sync"

	"github.com/deepaucksharma/mcp-server-newrelic/pkg/discovery"
)

// Miner implements the RelationshipMiner interface
type Miner struct {
	nrdb       discovery.NRDBClient
	config     Config
	cache      sync.Map // Simple cache for correlation results
	enableML   bool
}

// Config holds configuration for the relationship miner
type Config struct {
	MinCorrelation      float64 // Minimum correlation threshold
	MinSampleSize       int     // Minimum sample size for analysis
	MaxJoinCandidates   int     // Maximum join candidates to evaluate
	EnableMLDetection   bool    // Enable ML-based relationship detection
	ParallelWorkers     int     // Number of parallel workers
}

// DefaultConfig returns default configuration
func DefaultConfig() Config {
	return Config{
		MinCorrelation:    0.7,
		MinSampleSize:     100,
		MaxJoinCandidates: 50,
		EnableMLDetection: false,
		ParallelWorkers:   4,
	}
}

// NewMiner creates a new relationship miner
func NewMiner(nrdb discovery.NRDBClient, config Config) *Miner {
	return &Miner{
		nrdb:     nrdb,
		config:   config,
		enableML: config.EnableMLDetection,
	}
}

// FindRelationships discovers relationships between schemas
func (m *Miner) FindRelationships(ctx context.Context, schemas []discovery.Schema) ([]discovery.Relationship, error) {
	relationships := []discovery.Relationship{}
	
	// Find relationships in parallel
	type pair struct {
		schema1, schema2 int
	}
	
	// Generate all pairs to check
	pairs := []pair{}
	for i := 0; i < len(schemas); i++ {
		for j := i + 1; j < len(schemas); j++ {
			pairs = append(pairs, pair{i, j})
		}
	}
	
	// Process pairs in parallel
	results := make(chan discovery.Relationship, len(pairs))
	errors := make(chan error, len(pairs))
	
	// Worker pool
	numWorkers := m.config.ParallelWorkers
	if numWorkers > len(pairs) {
		numWorkers = len(pairs)
	}
	
	var wg sync.WaitGroup
	pairChan := make(chan pair, len(pairs))
	
	// Start workers
	for w := 0; w < numWorkers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for p := range pairChan {
				rels, err := m.findPairRelationships(ctx, schemas[p.schema1], schemas[p.schema2])
				if err != nil {
					errors <- err
					continue
				}
				for _, rel := range rels {
					results <- rel
				}
			}
		}()
	}
	
	// Send pairs to workers
	for _, p := range pairs {
		pairChan <- p
	}
	close(pairChan)
	
	// Wait for workers to finish
	wg.Wait()
	close(results)
	close(errors)
	
	// Collect results
	for rel := range results {
		relationships = append(relationships, rel)
	}
	
	// Check for errors
	var errs []error
	for err := range errors {
		errs = append(errs, err)
	}
	if len(errs) > 0 {
		// Return first error for simplicity
		return relationships, errs[0]
	}
	
	// Sort by confidence
	sort.Slice(relationships, func(i, j int) bool {
		return relationships[i].Confidence > relationships[j].Confidence
	})
	
	return relationships, nil
}

// findPairRelationships finds relationships between two schemas
func (m *Miner) findPairRelationships(ctx context.Context, schema1, schema2 discovery.Schema) ([]discovery.Relationship, error) {
	relationships := []discovery.Relationship{}
	
	// 1. Join-based relationships
	if joins := m.findJoinRelationships(ctx, schema1, schema2); len(joins) > 0 {
		relationships = append(relationships, joins...)
	}
	
	// 2. Temporal relationships
	if temporal := m.findTemporalRelationships(ctx, schema1, schema2); temporal != nil {
		relationships = append(relationships, *temporal)
	}
	
	// 3. Statistical correlations
	if correlations := m.findStatisticalCorrelations(ctx, schema1, schema2); len(correlations) > 0 {
		relationships = append(relationships, correlations...)
	}
	
	// 4. Semantic relationships (based on naming patterns)
	if semantic := m.findSemanticRelationships(schema1, schema2); semantic != nil {
		relationships = append(relationships, *semantic)
	}
	
	return relationships, nil
}

// findJoinRelationships discovers potential join relationships
func (m *Miner) findJoinRelationships(ctx context.Context, schema1, schema2 discovery.Schema) []discovery.Relationship {
	relationships := []discovery.Relationship{}
	
	// Find common attributes that could be join keys
	for _, attr1 := range schema1.Attributes {
		for _, attr2 := range schema2.Attributes {
			if m.isPotentialJoinKey(attr1, attr2) {
				// Evaluate join quality
				confidence := m.evaluateJoinQuality(ctx, schema1, schema2, attr1, attr2)
				
				if confidence >= m.config.MinCorrelation {
					relationships = append(relationships, discovery.Relationship{
						Type:       discovery.RelationshipTypeJoin,
						SourceSchema: schema1.Name,
						TargetSchema: schema2.Name,
						Confidence:  confidence,
						JoinKeys: &discovery.JoinKeyInfo{
							SourceKey: attr1.Name,
							TargetKey: attr2.Name,
							JoinType:  m.determineJoinType(attr1, attr2),
						},
						Evidence: map[string]interface{}{
							"source_attribute_type": attr1.DataType,
							"target_attribute_type": attr2.DataType,
							"semantic_match":        attr1.Name == attr2.Name,
						},
					})
				}
			}
		}
	}
	
	return relationships
}

// isPotentialJoinKey checks if two attributes could be join keys
func (m *Miner) isPotentialJoinKey(attr1, attr2 discovery.Attribute) bool {
	// Same name is strong indicator
	if attr1.Name == attr2.Name {
		return true
	}
	
	// Check semantic types
	if attr1.SemanticType == discovery.SemanticTypeID && attr2.SemanticType == discovery.SemanticTypeID {
		return true
	}
	
	// Check common ID patterns
	idPatterns := []string{"id", "Id", "ID", "_id", "_key", "Key"}
	for _, pattern := range idPatterns {
		if strings.HasSuffix(attr1.Name, pattern) && strings.HasSuffix(attr2.Name, pattern) {
			return true
		}
	}
	
	// Check if one references the other
	if strings.Contains(attr1.Name, attr2.Name) || strings.Contains(attr2.Name, attr1.Name) {
		return true
	}
	
	return false
}

// evaluateJoinQuality evaluates the quality of a potential join
func (m *Miner) evaluateJoinQuality(ctx context.Context, schema1, schema2 discovery.Schema, attr1, attr2 discovery.Attribute) float64 {
	// Check cache first
	cacheKey := fmt.Sprintf("%s.%s-%s.%s", schema1.Name, attr1.Name, schema2.Name, attr2.Name)
	if cached, ok := m.cache.Load(cacheKey); ok {
		return cached.(float64)
	}
	
	// In a real implementation, this would:
	// 1. Sample values from both attributes
	// 2. Calculate overlap percentage
	// 3. Check cardinality relationships
	// 4. Validate data types match
	
	// For now, use heuristics
	confidence := 0.5
	
	// Same name boost
	if attr1.Name == attr2.Name {
		confidence += 0.3
	}
	
	// Same data type boost
	if attr1.DataType == attr2.DataType {
		confidence += 0.1
	}
	
	// ID semantic type boost
	if attr1.SemanticType == discovery.SemanticTypeID || attr2.SemanticType == discovery.SemanticTypeID {
		confidence += 0.1
	}
	
	// Store in cache
	m.cache.Store(cacheKey, confidence)
	
	return confidence
}

// determineJoinType determines the type of join relationship
func (m *Miner) determineJoinType(attr1, attr2 discovery.Attribute) string {
	// Check cardinality to determine join type
	if attr1.Cardinality.IsHighCardinality && !attr2.Cardinality.IsHighCardinality {
		return "many-to-one"
	}
	if !attr1.Cardinality.IsHighCardinality && attr2.Cardinality.IsHighCardinality {
		return "one-to-many"
	}
	if attr1.Cardinality.IsHighCardinality && attr2.Cardinality.IsHighCardinality {
		return "many-to-many"
	}
	return "one-to-one"
}

// findTemporalRelationships discovers time-based relationships
func (m *Miner) findTemporalRelationships(ctx context.Context, schema1, schema2 discovery.Schema) *discovery.Relationship {
	// Check if both schemas have timestamp fields
	var ts1, ts2 *discovery.Attribute
	
	for i := range schema1.Attributes {
		if schema1.Attributes[i].DataType == discovery.DataTypeTimestamp || 
		   schema1.Attributes[i].Name == "timestamp" {
			ts1 = &schema1.Attributes[i]
			break
		}
	}
	
	for i := range schema2.Attributes {
		if schema2.Attributes[i].DataType == discovery.DataTypeTimestamp || 
		   schema2.Attributes[i].Name == "timestamp" {
			ts2 = &schema2.Attributes[i]
			break
		}
	}
	
	if ts1 == nil || ts2 == nil {
		return nil
	}
	
	// Both have timestamps - they can be temporally correlated
	return &discovery.Relationship{
		Type:         discovery.RelationshipTypeTemporal,
		SourceSchema: schema1.Name,
		TargetSchema: schema2.Name,
		Confidence:   0.9, // High confidence for temporal alignment
		Evidence: map[string]interface{}{
			"source_timestamp": ts1.Name,
			"target_timestamp": ts2.Name,
			"alignment_type":   "timestamp",
		},
	}
}

// findStatisticalCorrelations finds statistical relationships
func (m *Miner) findStatisticalCorrelations(ctx context.Context, schema1, schema2 discovery.Schema) []discovery.Relationship {
	relationships := []discovery.Relationship{}
	
	// Find numeric attributes
	numericAttrs1 := m.getNumericAttributes(schema1)
	numericAttrs2 := m.getNumericAttributes(schema2)
	
	// Check correlations between numeric attributes
	for _, attr1 := range numericAttrs1 {
		for _, attr2 := range numericAttrs2 {
			// In real implementation, would calculate actual correlation
			// For now, use pattern matching heuristics
			correlation := m.estimateCorrelation(attr1, attr2)
			
			if math.Abs(correlation) >= m.config.MinCorrelation {
				relationships = append(relationships, discovery.Relationship{
					Type:         discovery.RelationshipTypeCorrelation,
					SourceSchema: schema1.Name,
					TargetSchema: schema2.Name,
					Confidence:   math.Abs(correlation),
					Evidence: map[string]interface{}{
						"source_attribute": attr1.Name,
						"target_attribute": attr2.Name,
						"correlation":      correlation,
						"correlation_type": m.getCorrelationType(correlation),
					},
				})
			}
		}
	}
	
	return relationships
}

// getNumericAttributes returns numeric attributes from a schema
func (m *Miner) getNumericAttributes(schema discovery.Schema) []discovery.Attribute {
	numeric := []discovery.Attribute{}
	for _, attr := range schema.Attributes {
		if attr.DataType == discovery.DataTypeNumeric {
			numeric = append(numeric, attr)
		}
	}
	return numeric
}

// estimateCorrelation estimates correlation between attributes
func (m *Miner) estimateCorrelation(attr1, attr2 discovery.Attribute) float64 {
	// Heuristic correlation based on naming patterns
	name1, name2 := strings.ToLower(attr1.Name), strings.ToLower(attr2.Name)
	
	// Response time and duration often correlate
	if strings.Contains(name1, "response") && strings.Contains(name2, "duration") ||
	   strings.Contains(name2, "response") && strings.Contains(name1, "duration") {
		return 0.8
	}
	
	// Error rate and response time often correlate
	if strings.Contains(name1, "error") && strings.Contains(name2, "response") ||
	   strings.Contains(name2, "error") && strings.Contains(name1, "response") {
		return 0.7
	}
	
	// Count and sum attributes often correlate
	if strings.Contains(name1, "count") && strings.Contains(name2, "sum") ||
	   strings.Contains(name2, "count") && strings.Contains(name1, "sum") {
		return 0.9
	}
	
	return 0.0
}

// getCorrelationType determines the type of correlation
func (m *Miner) getCorrelationType(correlation float64) string {
	if correlation > 0.8 {
		return "strong_positive"
	} else if correlation > 0.5 {
		return "moderate_positive"
	} else if correlation < -0.8 {
		return "strong_negative"
	} else if correlation < -0.5 {
		return "moderate_negative"
	}
	return "weak"
}

// findSemanticRelationships finds relationships based on naming patterns
func (m *Miner) findSemanticRelationships(schema1, schema2 discovery.Schema) *discovery.Relationship {
	// Check for parent-child naming patterns
	name1, name2 := schema1.Name, schema2.Name
	
	// Common patterns
	patterns := []struct {
		parent string
		child  string
	}{
		{"Application", "Transaction"},
		{"Host", "Process"},
		{"Service", "Endpoint"},
		{"User", "Session"},
		{"Order", "OrderItem"},
	}
	
	for _, pattern := range patterns {
		if strings.Contains(name1, pattern.parent) && strings.Contains(name2, pattern.child) {
			return &discovery.Relationship{
				Type:         discovery.RelationshipTypeHierarchy,
				SourceSchema: schema1.Name,
				TargetSchema: schema2.Name,
				Confidence:   0.8,
				Evidence: map[string]interface{}{
					"relationship": "parent-child",
					"parent":       name1,
					"child":        name2,
				},
			}
		}
		if strings.Contains(name2, pattern.parent) && strings.Contains(name1, pattern.child) {
			return &discovery.Relationship{
				Type:         discovery.RelationshipTypeHierarchy,
				SourceSchema: schema2.Name,
				TargetSchema: schema1.Name,
				Confidence:   0.8,
				Evidence: map[string]interface{}{
					"relationship": "parent-child",
					"parent":       name2,
					"child":        name1,
				},
			}
		}
	}
	
	// Check for composition patterns
	if strings.HasPrefix(name2, name1) || strings.HasPrefix(name1, name2) {
		return &discovery.Relationship{
			Type:         discovery.RelationshipTypeComposition,
			SourceSchema: schema1.Name,
			TargetSchema: schema2.Name,
			Confidence:   0.7,
			Evidence: map[string]interface{}{
				"pattern": "naming_prefix",
			},
		}
	}
	
	return nil
}

// AnalyzeRelationshipGraph analyzes the overall relationship graph
func (m *Miner) AnalyzeRelationshipGraph(relationships []discovery.Relationship) discovery.RelationshipGraph {
	// Build adjacency map
	graph := make(map[string][]string)
	edgeCount := make(map[string]int)
	
	for _, rel := range relationships {
		graph[rel.SourceSchema] = append(graph[rel.SourceSchema], rel.TargetSchema)
		graph[rel.TargetSchema] = append(graph[rel.TargetSchema], rel.SourceSchema)
		edgeCount[rel.SourceSchema]++
		edgeCount[rel.TargetSchema]++
	}
	
	// Find hubs (highly connected schemas)
	hubs := []string{}
	for schema, count := range edgeCount {
		if count > 3 { // Arbitrary threshold
			hubs = append(hubs, schema)
		}
	}
	
	// Find isolated schemas
	isolated := []string{}
	for schema := range graph {
		if edgeCount[schema] == 0 {
			isolated = append(isolated, schema)
		}
	}
	
	// Calculate graph statistics
	totalSchemas := len(graph)
	totalEdges := len(relationships)
	avgDegree := 0.0
	if totalSchemas > 0 {
		avgDegree = float64(totalEdges*2) / float64(totalSchemas)
	}
	
	return discovery.RelationshipGraph{
		Nodes:         totalSchemas,
		Edges:         totalEdges,
		Hubs:          hubs,
		Isolated:      isolated,
		AverageDegree: avgDegree,
		Relationships: relationships,
	}
}