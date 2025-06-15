package discovery

import (
	"encoding/json"
	"fmt"
	"os"
	"time"

	"gopkg.in/yaml.v3"
)

// Config represents the discovery engine configuration
type Config struct {
	// NRDB configuration
	NRDB NRDBConfig `yaml:"nrdb" json:"nrdb"`
	
	// Discovery settings
	Discovery DiscoveryConfig `yaml:"discovery" json:"discovery"`
	
	// Cache configuration
	Cache CacheConfig `yaml:"cache" json:"cache"`
	
	// Performance settings
	Performance PerformanceConfig `yaml:"performance" json:"performance"`
	
	// Security settings
	Security SecurityConfig `yaml:"security" json:"security"`
	
	// Observability settings
	Observability ObservabilityConfig `yaml:"observability" json:"observability"`
}

// NRDBConfig contains NRDB connection settings
type NRDBConfig struct {
	BaseURL       string        `yaml:"base_url" json:"base_url"`
	APIKey        string        `yaml:"api_key" json:"api_key"`
	AccountID     string        `yaml:"account_id" json:"account_id"`
	Region        string        `yaml:"region" json:"region"`
	Timeout       time.Duration `yaml:"timeout" json:"timeout"`
	MaxRetries    int           `yaml:"max_retries" json:"max_retries"`
	RateLimit     int           `yaml:"rate_limit" json:"rate_limit"` // requests per minute
	InsightsKey   string        `yaml:"insights_key" json:"insights_key"`
}

// DiscoveryConfig contains discovery engine settings
type DiscoveryConfig struct {
	MaxConcurrency      int           `yaml:"max_concurrency" json:"max_concurrency"`
	DefaultSampleSize   int64         `yaml:"default_sample_size" json:"default_sample_size"`
	MaxSampleSize       int64         `yaml:"max_sample_size" json:"max_sample_size"`
	DiscoveryTimeout    time.Duration `yaml:"discovery_timeout" json:"discovery_timeout"`
	CacheTTL            time.Duration `yaml:"cache_ttl" json:"cache_ttl"`
	EnableMLPatterns    bool          `yaml:"enable_ml_patterns" json:"enable_ml_patterns"`
	MinSchemaRecords    int64         `yaml:"min_schema_records" json:"min_schema_records"`
	ProfileDepth        ProfileDepth  `yaml:"profile_depth" json:"profile_depth"`
	SamplingStrategies  []string      `yaml:"sampling_strategies" json:"sampling_strategies"`
}

// CacheConfig contains caching configuration
type CacheConfig struct {
	Enabled          bool          `yaml:"enabled" json:"enabled"`
	MaxMemorySize    string        `yaml:"max_memory_size" json:"max_memory_size"` // e.g., "1GB"
	DefaultTTL       time.Duration `yaml:"default_ttl" json:"default_ttl"`
	SchemaTTL        time.Duration `yaml:"schema_ttl" json:"schema_ttl"`
	PatternTTL       time.Duration `yaml:"pattern_ttl" json:"pattern_ttl"`
	RedisURL         string        `yaml:"redis_url" json:"redis_url"`
	EnablePredictive bool          `yaml:"enable_predictive" json:"enable_predictive"`
}

// PerformanceConfig contains performance tuning settings
type PerformanceConfig struct {
	WorkerPoolSize      int           `yaml:"worker_pool_size" json:"worker_pool_size"`
	QueryBatchSize      int           `yaml:"query_batch_size" json:"query_batch_size"`
	StreamingEnabled    bool          `yaml:"streaming_enabled" json:"streaming_enabled"`
	CompressionEnabled  bool          `yaml:"compression_enabled" json:"compression_enabled"`
	RequestTimeout      time.Duration `yaml:"request_timeout" json:"request_timeout"`
	CircuitBreakerLimit int           `yaml:"circuit_breaker_limit" json:"circuit_breaker_limit"`
}

// SecurityConfig contains security settings
type SecurityConfig struct {
	EnableTLS        bool     `yaml:"enable_tls" json:"enable_tls"`
	TLSCertPath      string   `yaml:"tls_cert_path" json:"tls_cert_path"`
	TLSKeyPath       string   `yaml:"tls_key_path" json:"tls_key_path"`
	AllowedDomains   []string `yaml:"allowed_domains" json:"allowed_domains"`
	EnableAuditLog   bool     `yaml:"enable_audit_log" json:"enable_audit_log"`
	SensitiveFields  []string `yaml:"sensitive_fields" json:"sensitive_fields"`
	MaskingEnabled   bool     `yaml:"masking_enabled" json:"masking_enabled"`
}

// ObservabilityConfig contains monitoring and observability settings
type ObservabilityConfig struct {
	MetricsEnabled     bool     `yaml:"metrics_enabled" json:"metrics_enabled"`
	MetricsPort        int      `yaml:"metrics_port" json:"metrics_port"`
	TracingEnabled     bool     `yaml:"tracing_enabled" json:"tracing_enabled"`
	TracingEndpoint    string   `yaml:"tracing_endpoint" json:"tracing_endpoint"`
	LogLevel           string   `yaml:"log_level" json:"log_level"`
	LogFormat          string   `yaml:"log_format" json:"log_format"`
	HealthCheckPort    int      `yaml:"health_check_port" json:"health_check_port"`
	ProfilerEnabled    bool     `yaml:"profiler_enabled" json:"profiler_enabled"`
	CustomDimensions   map[string]string `yaml:"custom_dimensions" json:"custom_dimensions"`
}

// LoadConfig loads configuration from a file
func LoadConfig(path string) (*Config, error) {
	// Check if file exists
	if _, err := os.Stat(path); os.IsNotExist(err) {
		// Return default config if file doesn't exist
		return DefaultConfig(), nil
	}
	
	// Read file
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("reading config file: %w", err)
	}
	
	// Parse based on extension
	config := &Config{}
	
	switch {
	case hasExtension(path, ".yaml", ".yml"):
		if err := yaml.Unmarshal(data, config); err != nil {
			return nil, fmt.Errorf("parsing YAML config: %w", err)
		}
	case hasExtension(path, ".json"):
		if err := json.Unmarshal(data, config); err != nil {
			return nil, fmt.Errorf("parsing JSON config: %w", err)
		}
	default:
		return nil, fmt.Errorf("unsupported config format, use .yaml or .json")
	}
	
	// Apply environment variable overrides
	config.applyEnvOverrides()
	
	// Validate configuration
	if err := config.Validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}
	
	return config, nil
}

// DefaultConfig returns a default configuration
func DefaultConfig() *Config {
	return &Config{
		NRDB: NRDBConfig{
			BaseURL:    "https://api.newrelic.com",
			Timeout:    30 * time.Second,
			MaxRetries: 3,
			RateLimit:  60, // 60 requests per minute
		},
		Discovery: DiscoveryConfig{
			MaxConcurrency:    10,
			DefaultSampleSize: 1000,
			MaxSampleSize:     10000,
			DiscoveryTimeout:  5 * time.Minute,
			CacheTTL:          1 * time.Hour,
			EnableMLPatterns:  true,
			MinSchemaRecords:  100,
			ProfileDepth:      ProfileDepthStandard,
			SamplingStrategies: []string{"adaptive", "stratified", "random"},
		},
		Cache: CacheConfig{
			Enabled:          true,
			MaxMemorySize:    "1GB",
			DefaultTTL:       1 * time.Hour,
			SchemaTTL:        4 * time.Hour,
			PatternTTL:       24 * time.Hour,
			EnablePredictive: true,
		},
		Performance: PerformanceConfig{
			WorkerPoolSize:      20,
			QueryBatchSize:      10,
			StreamingEnabled:    true,
			CompressionEnabled:  true,
			RequestTimeout:      30 * time.Second,
			CircuitBreakerLimit: 5,
		},
		Security: SecurityConfig{
			EnableTLS:       true,
			EnableAuditLog:  true,
			MaskingEnabled:  true,
			SensitiveFields: []string{"password", "apikey", "token", "secret"},
		},
		Observability: ObservabilityConfig{
			MetricsEnabled:  true,
			MetricsPort:     9090,
			TracingEnabled:  true,
			LogLevel:        "info",
			LogFormat:       "json",
			HealthCheckPort: 8080,
		},
	}
}

// Validate validates the configuration
func (c *Config) Validate() error {
	// Validate NRDB config
	if c.NRDB.APIKey == "" {
		return fmt.Errorf("NRDB API key is required")
	}
	if c.NRDB.AccountID == "" {
		return fmt.Errorf("NRDB account ID is required")
	}
	
	// Validate discovery config
	if c.Discovery.MaxConcurrency < 1 {
		return fmt.Errorf("max concurrency must be at least 1")
	}
	if c.Discovery.DefaultSampleSize < 10 {
		return fmt.Errorf("default sample size must be at least 10")
	}
	if c.Discovery.MaxSampleSize < c.Discovery.DefaultSampleSize {
		return fmt.Errorf("max sample size must be >= default sample size")
	}
	
	// Validate performance config
	if c.Performance.WorkerPoolSize < 1 {
		return fmt.Errorf("worker pool size must be at least 1")
	}
	
	return nil
}

// applyEnvOverrides applies environment variable overrides
func (c *Config) applyEnvOverrides() {
	// NRDB overrides
	if apiKey := os.Getenv("NEWRELIC_API_KEY"); apiKey != "" {
		c.NRDB.APIKey = apiKey
	}
	if accountID := os.Getenv("NEWRELIC_ACCOUNT_ID"); accountID != "" {
		c.NRDB.AccountID = accountID
	}
	if insightsKey := os.Getenv("NEWRELIC_INSIGHTS_KEY"); insightsKey != "" {
		c.NRDB.InsightsKey = insightsKey
	}
	
	// Redis override
	if redisURL := os.Getenv("REDIS_URL"); redisURL != "" {
		c.Cache.RedisURL = redisURL
	}
	
	// Tracing endpoint override
	if tracingEndpoint := os.Getenv("OTEL_EXPORTER_OTLP_ENDPOINT"); tracingEndpoint != "" {
		c.Observability.TracingEndpoint = tracingEndpoint
	}
}

// hasExtension checks if a file has one of the given extensions
func hasExtension(path string, extensions ...string) bool {
	for _, ext := range extensions {
		if len(path) >= len(ext) && path[len(path)-len(ext):] == ext {
			return true
		}
	}
	return false
}