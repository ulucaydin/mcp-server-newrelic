"""
Configuration settings for Intelligence Engine
Loads from environment variables with .env support
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Try to load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass


@dataclass
class NewRelicConfig:
    """New Relic API configuration"""
    api_key: str
    account_id: str
    region: str = "US"
    graphql_endpoint: Optional[str] = None
    
    def __post_init__(self):
        if not self.graphql_endpoint:
            if self.region.upper() == "EU":
                self.graphql_endpoint = "https://api.eu.newrelic.com/graphql"
            else:
                self.graphql_endpoint = "https://api.newrelic.com/graphql"


@dataclass
class APMConfig:
    """New Relic APM configuration"""
    enabled: bool = True
    license_key: str = ""
    app_name: str = "intelligence-engine"
    environment: str = "development"
    monitor_mode: bool = True
    high_security: bool = False
    distributed_tracing: bool = True
    log_level: str = "info"


@dataclass
class ServerConfig:
    """gRPC server configuration"""
    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 10
    enable_metrics: bool = True
    metrics_port: int = 8080


@dataclass
class PatternConfig:
    """Pattern detection configuration"""
    min_confidence: float = 0.7
    enable_statistical: bool = True
    enable_timeseries: bool = True
    enable_anomaly: bool = True
    enable_correlation: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 3600


@dataclass
class QueryConfig:
    """Query generation configuration"""
    cache_size: int = 100
    optimizer_mode: str = "balanced"
    enable_caching: bool = True
    max_query_length: int = 10000
    default_time_range: str = "1 hour"


@dataclass
class ModelConfig:
    """Model registry configuration"""
    model_dir: str = "/app/models"
    auto_download: bool = True
    cache_models: bool = True


@dataclass
class PerformanceConfig:
    """Performance configuration"""
    max_concurrent_requests: int = 100
    request_timeout: int = 30
    max_data_points: int = 10000
    enable_profiling: bool = False


@dataclass
class Config:
    """Main configuration class"""
    newrelic: NewRelicConfig
    apm: APMConfig
    server: ServerConfig
    patterns: PatternConfig
    query: QueryConfig
    models: ModelConfig
    performance: PerformanceConfig


def load_config() -> Config:
    """Load configuration from environment variables"""
    
    # New Relic API configuration
    newrelic = NewRelicConfig(
        api_key=os.getenv("NEW_RELIC_API_KEY", ""),
        account_id=os.getenv("NEW_RELIC_ACCOUNT_ID", ""),
        region=os.getenv("NEW_RELIC_REGION", "US"),
        graphql_endpoint=os.getenv("NEW_RELIC_GRAPHQL_ENDPOINT")
    )
    
    # APM configuration
    apm = APMConfig(
        enabled=os.getenv("NEW_RELIC_MONITOR_MODE", "true").lower() == "true",
        license_key=os.getenv("NEW_RELIC_LICENSE_KEY", ""),
        app_name=os.getenv("NEW_RELIC_APP_NAME", "intelligence-engine"),
        environment=os.getenv("NEW_RELIC_ENVIRONMENT", "development"),
        monitor_mode=os.getenv("NEW_RELIC_MONITOR_MODE", "true").lower() == "true",
        high_security=os.getenv("NEW_RELIC_HIGH_SECURITY", "false").lower() == "true",
        distributed_tracing=os.getenv("NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", "true").lower() == "true",
        log_level=os.getenv("NEW_RELIC_LOG_LEVEL", "info")
    )
    
    # Server configuration
    server = ServerConfig(
        host=os.getenv("INTELLIGENCE_GRPC_HOST", "0.0.0.0"),
        port=int(os.getenv("INTELLIGENCE_GRPC_PORT", "50051")),
        max_workers=int(os.getenv("WORKER_POOL_SIZE", "10")),
        enable_metrics=os.getenv("INTELLIGENCE_ENABLE_METRICS", "true").lower() == "true",
        metrics_port=int(os.getenv("INTELLIGENCE_METRICS_PORT", "8080"))
    )
    
    # Pattern configuration
    patterns = PatternConfig(
        min_confidence=float(os.getenv("INTELLIGENCE_PATTERN_MIN_CONFIDENCE", "0.7")),
        enable_statistical=os.getenv("ENABLE_PATTERN_DETECTION", "true").lower() == "true",
        enable_timeseries=os.getenv("ENABLE_PATTERN_DETECTION", "true").lower() == "true",
        enable_anomaly=os.getenv("ENABLE_ANOMALY_DETECTION", "true").lower() == "true",
        enable_correlation=os.getenv("ENABLE_PATTERN_DETECTION", "true").lower() == "true",
        cache_enabled=os.getenv("ENABLE_CACHING", "true").lower() == "true",
        cache_ttl=int(os.getenv("CACHE_DEFAULT_TTL", "3600"))
    )
    
    # Query configuration
    query = QueryConfig(
        cache_size=int(os.getenv("INTELLIGENCE_QUERY_CACHE_SIZE", "100")),
        optimizer_mode=os.getenv("INTELLIGENCE_QUERY_OPTIMIZER_MODE", "balanced"),
        enable_caching=os.getenv("ENABLE_CACHING", "true").lower() == "true",
        max_query_length=10000,
        default_time_range="1 hour"
    )
    
    # Model configuration
    models = ModelConfig(
        model_dir=os.getenv("MODEL_DIR", "/app/models"),
        auto_download=True,
        cache_models=True
    )
    
    # Performance configuration
    performance = PerformanceConfig(
        max_concurrent_requests=int(os.getenv("MAX_CONCURRENT_REQUESTS", "100")),
        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        max_data_points=10000,
        enable_profiling=os.getenv("ENABLE_PROFILING", "false").lower() == "true"
    )
    
    return Config(
        newrelic=newrelic,
        apm=apm,
        server=server,
        patterns=patterns,
        query=query,
        models=models,
        performance=performance
    )


def validate_config(config: Config) -> None:
    """Validate configuration"""
    if not config.newrelic.api_key:
        raise ValueError("NEW_RELIC_API_KEY is required")
    
    if not config.newrelic.account_id:
        raise ValueError("NEW_RELIC_ACCOUNT_ID is required")
    
    if config.apm.enabled and not config.apm.license_key:
        raise ValueError("NEW_RELIC_LICENSE_KEY is required when APM is enabled")


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = load_config()
        validate_config(_config)
    return _config