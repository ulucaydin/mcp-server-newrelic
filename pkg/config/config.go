package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/joho/godotenv"
	"github.com/newrelic/go-agent/v3/newrelic"
)

// Config holds all configuration for the application
type Config struct {
	// New Relic API Configuration
	NewRelic NewRelicConfig

	// New Relic APM Configuration
	APM APMConfig

	// Server Configuration
	Server ServerConfig

	// Discovery Configuration
	Discovery DiscoveryConfig

	// Intelligence Configuration
	Intelligence IntelligenceConfig

	// Redis Configuration
	Redis RedisConfig

	// Security Configuration
	Security SecurityConfig

	// Monitoring Configuration
	Monitoring MonitoringConfig

	// Feature Flags
	Features FeatureFlags

	// Development Configuration
	Development DevelopmentConfig
}

// NewRelicConfig holds New Relic API configuration
type NewRelicConfig struct {
	APIKey          string
	AccountID       string
	Region          string
	GraphQLEndpoint string
}

// APMConfig holds New Relic APM configuration
type APMConfig struct {
	Enabled           bool
	LicenseKey        string
	AppName           string
	Environment       string
	DistributedTracing bool
	LogLevel          string
}

// ServerConfig holds server configuration
type ServerConfig struct {
	Host                  string
	Port                  int
	MCPTransport          string
	MCPHTTPPort           int
	MCPSSEPort            int
	RequestTimeout        time.Duration
	MaxConcurrentRequests int
}

// DiscoveryConfig holds discovery engine configuration
type DiscoveryConfig struct {
	CacheTTL         time.Duration
	MaxWorkers       int
	SampleSize       int
	PatternMinConfidence float64
}

// IntelligenceConfig holds intelligence engine configuration
type IntelligenceConfig struct {
	GRPCHost            string
	GRPCPort            int
	EnableMetrics       bool
	MetricsPort         int
	PatternMinConfidence float64
	QueryCacheSize      int
	QueryOptimizerMode  string
}

// RedisConfig holds Redis configuration
type RedisConfig struct {
	URL         string
	Password    string
	DB          int
	PoolSize    int
	MaxRetries  int
	Timeout     time.Duration
}

// SecurityConfig holds security configuration
type SecurityConfig struct {
	AuthEnabled     bool
	JWTSecret       string
	JWTExpiry       time.Duration
	APIKeySalt      string
	RateLimitEnabled bool
	RateLimitPerMin int
	RateLimitBurst  int
}

// MonitoringConfig holds monitoring configuration
type MonitoringConfig struct {
	MetricsEnabled  bool
	MetricsPort     int
	MetricsPath     string
	TracingEnabled  bool
	TracingSampleRate float64
	JaegerAgentHost string
	JaegerAgentPort int
}

// FeatureFlags holds feature flags
type FeatureFlags struct {
	PatternDetection            bool
	QueryGeneration             bool
	VisualizationRecommendations bool
	AnomalyDetection            bool
	RelationshipMining          bool
	QualityAssessment           bool
	IntelligentSampling         bool
	A2AProtocol                 bool
	ExperimentalFeatures        bool
}

// DevelopmentConfig holds development configuration
type DevelopmentConfig struct {
	DevMode         bool
	Debug           bool
	VerboseLogging  bool
	EnableProfiling bool
	PProfPort       int
	MockMode        bool
	MockDataFile    string
}

// Load loads configuration from environment variables
func Load() (*Config, error) {
	// Load .env file if it exists
	if err := godotenv.Load(); err != nil {
		// It's okay if .env doesn't exist
		if !os.IsNotExist(err) {
			return nil, fmt.Errorf("error loading .env file: %w", err)
		}
	}

	cfg := &Config{
		NewRelic: NewRelicConfig{
			APIKey:    getEnv("NEW_RELIC_API_KEY", ""),
			AccountID: getEnv("NEW_RELIC_ACCOUNT_ID", ""),
			Region:    getEnv("NEW_RELIC_REGION", "US"),
		},
		APM: APMConfig{
			Enabled:            getBoolEnv("NEW_RELIC_MONITOR_MODE", true),
			LicenseKey:         getEnv("NEW_RELIC_LICENSE_KEY", ""),
			AppName:            getEnv("NEW_RELIC_APP_NAME", "mcp-server-newrelic"),
			Environment:        getEnv("NEW_RELIC_ENVIRONMENT", "development"),
			DistributedTracing: getBoolEnv("NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", true),
			LogLevel:           getEnv("NEW_RELIC_LOG_LEVEL", "info"),
		},
		Server: ServerConfig{
			Host:                  getEnv("SERVER_HOST", "0.0.0.0"),
			Port:                  getIntEnv("SERVER_PORT", 8080),
			MCPTransport:          getEnv("MCP_TRANSPORT", "stdio"),
			MCPHTTPPort:           getIntEnv("MCP_HTTP_PORT", 8081),
			MCPSSEPort:            getIntEnv("MCP_SSE_PORT", 8082),
			RequestTimeout:        getDurationEnv("REQUEST_TIMEOUT", 30*time.Second),
			MaxConcurrentRequests: getIntEnv("MAX_CONCURRENT_REQUESTS", 100),
		},
		Discovery: DiscoveryConfig{
			CacheTTL:             getDurationEnv("DISCOVERY_CACHE_TTL", 3600*time.Second),
			MaxWorkers:           getIntEnv("DISCOVERY_MAX_WORKERS", 10),
			SampleSize:           getIntEnv("DISCOVERY_SAMPLE_SIZE", 1000),
			PatternMinConfidence: getFloatEnv("DISCOVERY_PATTERN_MIN_CONFIDENCE", 0.7),
		},
		Intelligence: IntelligenceConfig{
			GRPCHost:             getEnv("INTELLIGENCE_GRPC_HOST", "localhost"),
			GRPCPort:             getIntEnv("INTELLIGENCE_GRPC_PORT", 50051),
			EnableMetrics:        getBoolEnv("INTELLIGENCE_ENABLE_METRICS", true),
			MetricsPort:          getIntEnv("INTELLIGENCE_METRICS_PORT", 8080),
			PatternMinConfidence: getFloatEnv("INTELLIGENCE_PATTERN_MIN_CONFIDENCE", 0.7),
			QueryCacheSize:       getIntEnv("INTELLIGENCE_QUERY_CACHE_SIZE", 100),
			QueryOptimizerMode:   getEnv("INTELLIGENCE_QUERY_OPTIMIZER_MODE", "balanced"),
		},
		Redis: RedisConfig{
			URL:        getEnv("REDIS_URL", "redis://localhost:6379"),
			Password:   getEnv("REDIS_PASSWORD", ""),
			DB:         getIntEnv("REDIS_DB", 0),
			PoolSize:   getIntEnv("REDIS_POOL_SIZE", 10),
			MaxRetries: getIntEnv("REDIS_MAX_RETRIES", 3),
			Timeout:    getDurationEnv("REDIS_TIMEOUT", 5*time.Second),
		},
		Security: SecurityConfig{
			AuthEnabled:      getBoolEnv("AUTH_ENABLED", false),
			JWTSecret:        getEnv("JWT_SECRET", "change-me-in-production"),
			JWTExpiry:        getDurationEnv("JWT_EXPIRY", 24*time.Hour),
			APIKeySalt:       getEnv("API_KEY_SALT", "change-me-in-production"),
			RateLimitEnabled: getBoolEnv("RATE_LIMIT_ENABLED", true),
			RateLimitPerMin:  getIntEnv("RATE_LIMIT_PER_MIN", 60),
			RateLimitBurst:   getIntEnv("RATE_LIMIT_BURST", 10),
		},
		Monitoring: MonitoringConfig{
			MetricsEnabled:    getBoolEnv("METRICS_ENABLED", true),
			MetricsPort:       getIntEnv("METRICS_PORT", 9090),
			MetricsPath:       getEnv("METRICS_PATH", "/metrics"),
			TracingEnabled:    getBoolEnv("TRACING_ENABLED", true),
			TracingSampleRate: getFloatEnv("TRACING_SAMPLE_RATE", 1.0),
			JaegerAgentHost:   getEnv("JAEGER_AGENT_HOST", "localhost"),
			JaegerAgentPort:   getIntEnv("JAEGER_AGENT_PORT", 6831),
		},
		Features: FeatureFlags{
			PatternDetection:             getBoolEnv("ENABLE_PATTERN_DETECTION", true),
			QueryGeneration:              getBoolEnv("ENABLE_QUERY_GENERATION", true),
			VisualizationRecommendations: getBoolEnv("ENABLE_VISUALIZATION_RECOMMENDATIONS", true),
			AnomalyDetection:             getBoolEnv("ENABLE_ANOMALY_DETECTION", true),
			RelationshipMining:           getBoolEnv("ENABLE_RELATIONSHIP_MINING", true),
			QualityAssessment:            getBoolEnv("ENABLE_QUALITY_ASSESSMENT", true),
			IntelligentSampling:          getBoolEnv("ENABLE_INTELLIGENT_SAMPLING", true),
			A2AProtocol:                  getBoolEnv("ENABLE_A2A_PROTOCOL", false),
			ExperimentalFeatures:         getBoolEnv("ENABLE_EXPERIMENTAL_FEATURES", false),
		},
		Development: DevelopmentConfig{
			DevMode:         getBoolEnv("DEV_MODE", false),
			Debug:           getBoolEnv("DEBUG", false),
			VerboseLogging:  getBoolEnv("VERBOSE_LOGGING", false),
			EnableProfiling: getBoolEnv("ENABLE_PROFILING", false),
			PProfPort:       getIntEnv("PPROF_PORT", 6060),
			MockMode:        getBoolEnv("MOCK_MODE", false),
			MockDataFile:    getEnv("MOCK_DATA_FILE", ""),
		},
	}

	// Set GraphQL endpoint based on region
	if cfg.NewRelic.Region == "EU" {
		cfg.NewRelic.GraphQLEndpoint = "https://api.eu.newrelic.com/graphql"
	} else {
		cfg.NewRelic.GraphQLEndpoint = "https://api.newrelic.com/graphql"
	}

	// Override with explicit endpoint if provided
	if endpoint := getEnv("NEW_RELIC_GRAPHQL_ENDPOINT", ""); endpoint != "" {
		cfg.NewRelic.GraphQLEndpoint = endpoint
	}

	return cfg, nil
}

// NewAPMApplication creates a New Relic APM application
func (c *Config) NewAPMApplication() (*newrelic.Application, error) {
	if !c.APM.Enabled || c.APM.LicenseKey == "" {
		return nil, nil
	}

	app, err := newrelic.NewApplication(
		newrelic.ConfigAppName(c.APM.AppName),
		newrelic.ConfigLicense(c.APM.LicenseKey),
		newrelic.ConfigDistributedTracerEnabled(c.APM.DistributedTracing),
		newrelic.ConfigEnabled(c.APM.Enabled),
		func(cfg *newrelic.Config) {
			// Set custom attributes
			cfg.Labels = map[string]string{
				"environment": c.APM.Environment,
				"service":     "mcp-server",
			}
			// Set log level
			if strings.ToLower(c.APM.LogLevel) == "debug" {
				cfg.Logger = newrelic.NewDebugLogger(os.Stdout)
			}
		},
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create New Relic application: %w", err)
	}

	return app, nil
}

// Helper functions

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getIntEnv(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}

func getFloatEnv(key string, defaultValue float64) float64 {
	if value := os.Getenv(key); value != "" {
		if floatValue, err := strconv.ParseFloat(value, 64); err == nil {
			return floatValue
		}
	}
	return defaultValue
}

func getBoolEnv(key string, defaultValue bool) bool {
	if value := os.Getenv(key); value != "" {
		if boolValue, err := strconv.ParseBool(value); err == nil {
			return boolValue
		}
	}
	return defaultValue
}

func getDurationEnv(key string, defaultValue time.Duration) time.Duration {
	if value := os.Getenv(key); value != "" {
		if duration, err := time.ParseDuration(value); err == nil {
			return duration
		}
	}
	return defaultValue
}

// Validate validates the configuration
func (c *Config) Validate() error {
	if c.NewRelic.APIKey == "" {
		return fmt.Errorf("NEW_RELIC_API_KEY is required")
	}
	if c.NewRelic.AccountID == "" {
		return fmt.Errorf("NEW_RELIC_ACCOUNT_ID is required")
	}
	if c.APM.Enabled && c.APM.LicenseKey == "" {
		return fmt.Errorf("NEW_RELIC_LICENSE_KEY is required when APM is enabled")
	}
	return nil
}