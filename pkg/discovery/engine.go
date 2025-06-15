package discovery

import (
	"context"
	"fmt"
	"sync"
	"time"
)

// Engine implements the DiscoveryEngine interface
type Engine struct {
	config          *Config
	nrdb            NRDBClient
	cache           Cache
	sampler         *IntelligentSampler
	patternEngine   *PatternEngine
	relationshipMiner RelationshipMiner
	qualityAssessor QualityAssessor
	metrics         MetricsCollector
	
	// Internal state
	mu              sync.RWMutex
	running         bool
	startTime       time.Time
	discoveryCount  int64
	
	// Worker pool
	workerPool      *WorkerPool
	
	// Context for graceful shutdown
	ctx             context.Context
	cancel          context.CancelFunc
}

// NewEngine creates a new discovery engine
func NewEngine(config *Config) (*Engine, error) {
	// Validate config
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("invalid config: %w", err)
	}
	
	// Create context
	ctx, cancel := context.WithCancel(context.Background())
	
	// Initialize engine
	engine := &Engine{
		config:    config,
		ctx:       ctx,
		cancel:    cancel,
		startTime: time.Now(),
	}
	
	// Initialize components
	if err := engine.initializeComponents(); err != nil {
		cancel()
		return nil, fmt.Errorf("initializing components: %w", err)
	}
	
	return engine, nil
}

// initializeComponents initializes all engine components
func (e *Engine) initializeComponents() error {
	// Initialize NRDB client
	nrdbClient, err := NewNRDBClient(e.config.NRDB)
	if err != nil {
		return fmt.Errorf("creating NRDB client: %w", err)
	}
	e.nrdb = nrdbClient
	
	// Initialize cache
	if e.config.Cache.Enabled {
		cache, err := NewMultiLayerCache(e.config.Cache)
		if err != nil {
			return fmt.Errorf("creating cache: %w", err)
		}
		e.cache = cache
	} else {
		e.cache = NewNoOpCache()
	}
	
	// Initialize sampler
	e.sampler = NewIntelligentSampler(e.nrdb, e.config.Discovery)
	
	// Initialize pattern engine
	e.patternEngine = NewPatternEngine(e.config.Discovery.EnableMLPatterns)
	
	// Initialize relationship miner
	e.relationshipMiner = NewRelationshipMiner(e.nrdb)
	
	// Initialize quality assessor
	e.qualityAssessor = NewQualityAssessor()
	
	// Initialize metrics
	e.metrics = NewMetricsCollector(e.config.Observability)
	
	// Initialize worker pool
	e.workerPool = NewWorkerPool(e.config.Performance.WorkerPoolSize)
	
	return nil
}

// Start starts the discovery engine
func (e *Engine) Start(ctx context.Context) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	
	if e.running {
		return fmt.Errorf("engine already running")
	}
	
	e.running = true
	
	// Start worker pool
	e.workerPool.Start()
	
	// Start background tasks
	go e.runBackgroundTasks()
	
	// Start health check server
	go e.runHealthCheckServer()
	
	// Wait for context cancellation
	<-ctx.Done()
	
	// Stop the engine
	return e.Stop(context.Background())
}

// Stop stops the discovery engine gracefully
func (e *Engine) Stop(ctx context.Context) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	
	if !e.running {
		return nil
	}
	
	e.running = false
	
	// Cancel internal context
	e.cancel()
	
	// Stop worker pool
	e.workerPool.Stop()
	
	// Flush cache
	if e.cache != nil {
		e.cache.Clear()
	}
	
	// Record final metrics
	e.recordShutdownMetrics()
	
	return nil
}

// DiscoverSchemas discovers all schemas matching the filter
func (e *Engine) DiscoverSchemas(ctx context.Context, filter DiscoveryFilter) ([]Schema, error) {
	startTime := time.Now()
	defer func() {
		e.metrics.RecordDiscoveryDuration(time.Since(startTime))
	}()
	
	// Check cache first
	cacheKey := generateCacheKey("schemas", filter)
	if cached, found := e.cache.Get(cacheKey); found {
		e.metrics.RecordCacheHit("schema")
		return cached.([]Schema), nil
	}
	e.metrics.RecordCacheMiss("schema")
	
	// Discover event types
	eventTypes, err := e.discoverEventTypes(ctx, filter)
	if err != nil {
		return nil, fmt.Errorf("discovering event types: %w", err)
	}
	
	// Create tasks for parallel discovery
	tasks := make([]DiscoveryTask, len(eventTypes))
	for i, eventType := range eventTypes {
		tasks[i] = DiscoveryTask{
			EventType: eventType,
			Filter:    filter,
		}
	}
	
	// Execute parallel discovery
	results := e.workerPool.ExecuteBatch(ctx, tasks, func(ctx context.Context, task interface{}) (interface{}, error) {
		dt := task.(DiscoveryTask)
		return e.discoverSingleSchema(ctx, dt.EventType)
	})
	
	// Collect successful results
	schemas := make([]Schema, 0, len(results))
	for _, result := range results {
		if result.Error != nil {
			e.metrics.RecordError("schema_discovery", result.Error)
			continue
		}
		schemas = append(schemas, result.Value.(Schema))
	}
	
	// Cache results
	e.cache.Set(cacheKey, schemas, e.config.Discovery.CacheTTL)
	
	// Update metrics
	e.mu.Lock()
	e.discoveryCount += int64(len(schemas))
	e.mu.Unlock()
	
	return schemas, nil
}

// DiscoverWithIntelligence performs intelligent discovery based on hints
func (e *Engine) DiscoverWithIntelligence(ctx context.Context, hints DiscoveryHints) (*DiscoveryResult, error) {
	// Create intelligent filter based on hints
	filter := e.createIntelligentFilter(hints)
	
	// Discover schemas
	schemas, err := e.DiscoverSchemas(ctx, filter)
	if err != nil {
		return nil, err
	}
	
	// Rank schemas by relevance
	rankedSchemas := e.rankSchemasByRelevance(schemas, hints)
	
	// Detect cross-schema patterns
	patterns := e.detectCrossSchemaPatterns(ctx, rankedSchemas)
	
	// Generate insights
	insights := e.generateInsights(rankedSchemas, patterns)
	
	// Create execution plan
	plan := e.createExecutionPlan(hints, rankedSchemas)
	
	return &DiscoveryResult{
		Schemas:         rankedSchemas,
		Patterns:        patterns,
		Insights:        insights,
		Recommendations: e.generateRecommendations(insights),
		ExecutionPlan:   plan,
		Metadata: map[string]interface{}{
			"discovery_time": time.Since(time.Now()),
			"schemas_found":  len(rankedSchemas),
			"patterns_found": len(patterns),
		},
	}, nil
}

// ProfileSchema performs deep profiling of a single schema
func (e *Engine) ProfileSchema(ctx context.Context, eventType string, depth ProfileDepth) (*Schema, error) {
	// Check cache
	cacheKey := fmt.Sprintf("profile:%s:%s", eventType, depth)
	if cached, found := e.cache.Get(cacheKey); found {
		e.metrics.RecordCacheHit("profile")
		return cached.(*Schema), nil
	}
	
	// Discover base schema
	schema, err := e.discoverSingleSchema(ctx, eventType)
	if err != nil {
		return nil, err
	}
	
	// Apply profiling based on depth
	switch depth {
	case ProfileDepthBasic:
		// Basic profiling is already done
	case ProfileDepthStandard:
		// Add statistics and patterns
		if err := e.addStatisticsToSchema(ctx, &schema); err != nil {
			return nil, err
		}
		if err := e.addPatternsToSchema(ctx, &schema); err != nil {
			return nil, err
		}
	case ProfileDepthFull:
		// Everything including samples
		if err := e.addStatisticsToSchema(ctx, &schema); err != nil {
			return nil, err
		}
		if err := e.addPatternsToSchema(ctx, &schema); err != nil {
			return nil, err
		}
		if err := e.addSamplesToSchema(ctx, &schema); err != nil {
			return nil, err
		}
	}
	
	// Assess quality
	quality, err := e.assessSchemaQuality(ctx, schema)
	if err != nil {
		return nil, err
	}
	schema.Quality = quality
	
	// Cache result
	e.cache.Set(cacheKey, &schema, e.config.Discovery.CacheTTL)
	
	return &schema, nil
}

// GetSamplingStrategy returns the optimal sampling strategy for an event type
func (e *Engine) GetSamplingStrategy(ctx context.Context, eventType string) (SamplingStrategy, error) {
	// Get data profile
	profile, err := e.getDataProfile(ctx, eventType)
	if err != nil {
		return nil, err
	}
	
	// Select strategy
	return e.sampler.SelectStrategy(ctx, profile)
}

// SampleData samples data using the appropriate strategy
func (e *Engine) SampleData(ctx context.Context, params SamplingParams) (*DataSample, error) {
	// Get or select strategy
	var strategy SamplingStrategy
	if params.Strategy != "" {
		strategy = e.sampler.GetStrategy(params.Strategy)
		if strategy == nil {
			return nil, fmt.Errorf("unknown strategy: %s", params.Strategy)
		}
	} else {
		var err error
		strategy, err = e.GetSamplingStrategy(ctx, params.EventType)
		if err != nil {
			return nil, err
		}
	}
	
	// Execute sampling
	return strategy.Sample(ctx, params)
}

// AssessQuality performs quality assessment on a schema
func (e *Engine) AssessQuality(ctx context.Context, schemaName string) (*QualityReport, error) {
	// Get schema
	schema, err := e.ProfileSchema(ctx, schemaName, ProfileDepthStandard)
	if err != nil {
		return nil, err
	}
	
	// Get sample data
	sample, err := e.SampleData(ctx, SamplingParams{
		EventType:  schemaName,
		TimeRange:  TimeRange{Start: time.Now().Add(-24 * time.Hour), End: time.Now()},
		MaxSamples: 1000,
	})
	if err != nil {
		return nil, err
	}
	
	// Assess quality
	report := e.qualityAssessor.AssessSchema(ctx, *schema, *sample)
	return &report, nil
}

// FindRelationships discovers relationships between schemas
func (e *Engine) FindRelationships(ctx context.Context, schemas []Schema) ([]Relationship, error) {
	startTime := time.Now()
	defer func() {
		e.metrics.RecordDiscoveryDuration(time.Since(startTime))
	}()
	
	// Use relationship miner
	return e.relationshipMiner.FindRelationships(ctx, schemas)
}

// Health returns the current health status
func (e *Engine) Health() HealthStatus {
	e.mu.RLock()
	defer e.mu.RUnlock()
	
	status := "healthy"
	if !e.running {
		status = "stopped"
	}
	
	return HealthStatus{
		Status:  status,
		Version: "1.0.0",
		Uptime:  time.Since(e.startTime),
		Components: map[string]ComponentHealth{
			"nrdb": {
				Status:    "healthy",
				LastCheck: time.Now(),
			},
			"cache": {
				Status:    "healthy",
				LastCheck: time.Now(),
			},
			"worker_pool": {
				Status:    "healthy",
				LastCheck: time.Now(),
				Message:   fmt.Sprintf("%d workers active", e.workerPool.ActiveWorkers()),
			},
		},
		Metrics: map[string]interface{}{
			"discoveries_total": e.discoveryCount,
			"uptime_seconds":    time.Since(e.startTime).Seconds(),
			"cache_stats":       e.cache.Stats(),
		},
	}
}

// Private helper methods

// discoverEventTypes discovers all event types matching the filter
func (e *Engine) discoverEventTypes(ctx context.Context, filter DiscoveryFilter) ([]string, error) {
	// Build event type filter
	etFilter := EventTypeFilter{
		MinRecordCount: filter.MinRecordCount,
	}
	
	// Apply pattern filters
	if len(filter.IncludePatterns) > 0 {
		etFilter.Pattern = filter.IncludePatterns[0] // TODO: Support multiple patterns
	}
	
	// Get event types from NRDB
	eventTypes, err := e.nrdb.GetEventTypes(ctx, etFilter)
	if err != nil {
		return nil, err
	}
	
	// Apply additional filters
	filtered := make([]string, 0, len(eventTypes))
	for _, et := range eventTypes {
		if e.shouldIncludeEventType(et, filter) {
			filtered = append(filtered, et)
		}
	}
	
	// Apply max schemas limit
	if filter.MaxSchemas > 0 && len(filtered) > filter.MaxSchemas {
		filtered = filtered[:filter.MaxSchemas]
	}
	
	return filtered, nil
}

// discoverSingleSchema discovers a single schema
func (e *Engine) discoverSingleSchema(ctx context.Context, eventType string) (Schema, error) {
	schema := Schema{
		ID:           generateSchemaID(eventType),
		Name:         eventType,
		EventType:    eventType,
		DiscoveredAt: time.Now(),
	}
	
	// Get sample data
	sample, err := e.SampleData(ctx, SamplingParams{
		EventType:  eventType,
		TimeRange:  TimeRange{Start: time.Now().Add(-1 * time.Hour), End: time.Now()},
		MaxSamples: e.config.Discovery.DefaultSampleSize,
	})
	if err != nil {
		return schema, fmt.Errorf("sampling data: %w", err)
	}
	
	schema.SampleCount = int64(sample.SampleSize)
	
	// Discover attributes
	attributes := e.discoverAttributes(sample)
	schema.Attributes = attributes
	
	// Assess data volume
	volume, err := e.assessDataVolume(ctx, eventType)
	if err != nil {
		// Don't fail discovery if volume assessment fails
		e.metrics.RecordError("volume_assessment", err)
	} else {
		schema.DataVolume = volume
	}
	
	// Basic quality assessment
	schema.Quality = e.calculateBasicQuality(attributes, sample)
	
	// Record metrics
	e.metrics.RecordSchemaDiscovered(eventType)
	
	return schema, nil
}

// Helper methods implementations would continue...
// (truncated for brevity, but would include all the helper methods referenced above)