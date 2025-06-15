"""Configuration management for Intelligence Engine"""

import os
import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
import logging
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class ConfigSource(Enum):
    """Configuration sources in priority order"""
    ENVIRONMENT = "environment"
    FILE = "file"
    DEFAULT = "default"


class PatternDetectionConfig(BaseModel):
    """Pattern detection configuration"""
    
    # General settings
    min_confidence: float = Field(0.7, ge=0.0, le=1.0, description="Minimum pattern confidence threshold")
    enable_caching: bool = Field(True, description="Enable result caching")
    cache_ttl_seconds: int = Field(3600, gt=0, description="Cache TTL in seconds")
    
    # Feature toggles
    enable_statistical: bool = Field(True, description="Enable statistical pattern detection")
    enable_timeseries: bool = Field(True, description="Enable time series pattern detection")
    enable_anomaly: bool = Field(True, description="Enable anomaly detection")
    enable_correlation: bool = Field(True, description="Enable correlation detection")
    
    # Statistical detector config
    statistical_config: Dict[str, Any] = Field(default_factory=lambda: {
        "outlier_method": "iqr",
        "distribution_tests": ["shapiro", "kstest"],
        "missing_data_threshold": 0.1
    })
    
    # Time series detector config
    timeseries_config: Dict[str, Any] = Field(default_factory=lambda: {
        "stationarity_alpha": 0.05,
        "seasonality_methods": ["fft", "acf"],
        "min_seasonality_strength": 0.5,
        "trend_methods": ["linear", "polynomial"]
    })
    
    # Anomaly detector config
    anomaly_config: Dict[str, Any] = Field(default_factory=lambda: {
        "ensemble_methods": ["iforest", "lof", "knn"],
        "contamination": 0.1,
        "n_estimators": 100,
        "n_neighbors": 20
    })
    
    # Correlation detector config
    correlation_config: Dict[str, Any] = Field(default_factory=lambda: {
        "min_correlation": 0.5,
        "check_nonlinear": True,
        "max_lag": 50,
        "mutual_info_neighbors": 3
    })


class QueryGenerationConfig(BaseModel):
    """Query generation configuration"""
    
    # Cache settings
    cache_size: int = Field(100, gt=0, description="Query cache size")
    history_size: int = Field(1000, gt=0, description="Query history size")
    
    # Parser config
    parser_config: Dict[str, Any] = Field(default_factory=lambda: {
        "confidence_threshold": 0.6,
        "enable_spell_correction": True,
        "spacy_model": "en_core_web_sm",
        "max_query_length": 500
    })
    
    # Builder config
    builder_config: Dict[str, Any] = Field(default_factory=lambda: {
        "default_limit": 100,
        "max_limit": 10000,
        "default_time_range": "1 hour ago",
        "max_time_range_days": 90
    })
    
    # Optimizer config
    optimizer_config: Dict[str, Any] = Field(default_factory=lambda: {
        "performance_mode": "balanced",  # cost, speed, balanced
        "aggressive": False,
        "cost_threshold": 100.0,
        "cost_model": {
            "base_cost_per_gb": 0.25,
            "timeseries_multiplier": 1.5,
            "facet_multiplier": 1.2,
            "percentile_multiplier": 2.0
        }
    })


class VisualizationConfig(BaseModel):
    """Visualization intelligence configuration"""
    
    # Data shape analyzer config
    shape_analyzer_config: Dict[str, Any] = Field(default_factory=lambda: {
        "sample_size": 10000,
        "correlation_threshold": 0.5,
        "outlier_method": "iqr",
        "cardinality_threshold": 0.5
    })
    
    # Chart recommender config
    recommender_config: Dict[str, Any] = Field(default_factory=lambda: {
        "max_recommendations": 5,
        "confidence_boost_preferred": 0.1,
        "confidence_penalty_large_data": 0.2
    })
    
    # Layout optimizer config
    layout_config: Dict[str, Any] = Field(default_factory=lambda: {
        "default_grid_columns": 4,
        "optimization_iterations": 100,
        "annealing_temperature": 1.0,
        "cooling_rate": 0.95
    })


class GRPCConfig(BaseModel):
    """gRPC server configuration"""
    
    host: str = Field("0.0.0.0", description="gRPC server host")
    port: int = Field(50051, gt=0, le=65535, description="gRPC server port")
    max_workers: int = Field(10, gt=0, description="Maximum worker threads")
    max_message_size: int = Field(100 * 1024 * 1024, gt=0, description="Max message size in bytes")
    keepalive_time_ms: int = Field(30000, gt=0, description="Keepalive time in milliseconds")


class IntelligenceConfig(BaseModel):
    """Main intelligence engine configuration"""
    
    # Component configs
    pattern_detection: PatternDetectionConfig = Field(default_factory=PatternDetectionConfig)
    query_generation: QueryGenerationConfig = Field(default_factory=QueryGenerationConfig)
    visualization: VisualizationConfig = Field(default_factory=VisualizationConfig)
    grpc: GRPCConfig = Field(default_factory=GRPCConfig)
    
    # General settings
    log_level: str = Field("INFO", description="Logging level")
    enable_metrics: bool = Field(True, description="Enable performance metrics")
    metrics_port: int = Field(8080, gt=0, le=65535, description="Metrics endpoint port")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()


class ConfigManager:
    """Manages configuration for the Intelligence Engine"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config: Optional[IntelligenceConfig] = None
        self._env_prefix = "INTELLIGENCE_"
        
    def _find_config_file(self) -> Optional[str]:
        """Find configuration file in standard locations"""
        search_paths = [
            Path.cwd() / "intelligence.yaml",
            Path.cwd() / "intelligence.yml",
            Path.cwd() / "config" / "intelligence.yaml",
            Path.home() / ".config" / "intelligence" / "config.yaml",
            Path("/etc/intelligence/config.yaml")
        ]
        
        for path in search_paths:
            if path.exists():
                logger.info(f"Found config file: {path}")
                return str(path)
        
        return None
    
    def load(self) -> IntelligenceConfig:
        """Load configuration from all sources"""
        if self._config:
            return self._config
        
        # Start with defaults
        config_dict = {}
        
        # Load from file if available
        if self.config_path and Path(self.config_path).exists():
            config_dict = self._load_from_file(self.config_path)
        
        # Override with environment variables
        config_dict = self._merge_env_vars(config_dict)
        
        # Create config object
        self._config = IntelligenceConfig(**config_dict)
        
        # Configure logging
        self._configure_logging(self._config.log_level)
        
        logger.info("Configuration loaded successfully")
        return self._config
    
    def _load_from_file(self, path: str) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file"""
        path_obj = Path(path)
        
        try:
            with open(path_obj, 'r') as f:
                if path_obj.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                elif path_obj.suffix == '.json':
                    return json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {path_obj.suffix}")
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return {}
    
    def _merge_env_vars(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Merge environment variables into config"""
        
        # Map of environment variables to config paths
        env_mappings = {
            f"{self._env_prefix}LOG_LEVEL": "log_level",
            f"{self._env_prefix}ENABLE_METRICS": "enable_metrics",
            f"{self._env_prefix}METRICS_PORT": "metrics_port",
            
            # Pattern detection
            f"{self._env_prefix}PATTERN_MIN_CONFIDENCE": "pattern_detection.min_confidence",
            f"{self._env_prefix}PATTERN_ENABLE_CACHING": "pattern_detection.enable_caching",
            
            # Query generation
            f"{self._env_prefix}QUERY_CACHE_SIZE": "query_generation.cache_size",
            f"{self._env_prefix}QUERY_OPTIMIZER_MODE": "query_generation.optimizer_config.performance_mode",
            
            # gRPC
            f"{self._env_prefix}GRPC_HOST": "grpc.host",
            f"{self._env_prefix}GRPC_PORT": "grpc.port",
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value is not None:
                self._set_nested_value(config_dict, config_path, self._parse_env_value(value))
        
        return config_dict
    
    def _set_nested_value(self, d: Dict[str, Any], path: str, value: Any):
        """Set a value in a nested dictionary using dot notation"""
        keys = path.split('.')
        current = d
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Float
        try:
            return float(value)
        except ValueError:
            pass
        
        # String
        return value
    
    def _configure_logging(self, level: str):
        """Configure logging based on config"""
        logging.basicConfig(
            level=getattr(logging, level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def save(self, path: Optional[str] = None):
        """Save current configuration to file"""
        save_path = path or self.config_path
        if not save_path:
            raise ValueError("No path specified for saving configuration")
        
        config_dict = self._config.dict() if self._config else {}
        
        path_obj = Path(save_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w') as f:
            if path_obj.suffix in ['.yaml', '.yml']:
                yaml.dump(config_dict, f, default_flow_style=False)
            else:
                json.dump(config_dict, f, indent=2)
        
        logger.info(f"Configuration saved to: {save_path}")
    
    def get_component_config(self, component: str) -> Dict[str, Any]:
        """Get configuration for a specific component"""
        if not self._config:
            self.load()
        
        component_map = {
            'pattern': self._config.pattern_detection,
            'query': self._config.query_generation,
            'visualization': self._config.visualization,
            'grpc': self._config.grpc
        }
        
        if component not in component_map:
            raise ValueError(f"Unknown component: {component}")
        
        return component_map[component].dict()
    
    def validate(self) -> List[str]:
        """Validate configuration and return any issues"""
        issues = []
        
        if not self._config:
            self.load()
        
        # Validate pattern detection
        if self._config.pattern_detection.min_confidence < 0.5:
            issues.append("Pattern detection confidence threshold is very low (<0.5)")
        
        # Validate query generation
        if self._config.query_generation.cache_size > 10000:
            issues.append("Query cache size is very large (>10000)")
        
        # Validate gRPC
        if self._config.grpc.port < 1024:
            issues.append("gRPC port is in privileged range (<1024)")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        if not self._config:
            self.load()
        return self._config.dict()
    
    def __repr__(self) -> str:
        return f"ConfigManager(config_path='{self.config_path}')"


# Singleton instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager(config_path: Optional[str] = None) -> ConfigManager:
    """Get or create config manager singleton"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    
    return _config_manager


def load_config(config_path: Optional[str] = None) -> IntelligenceConfig:
    """Convenience function to load configuration"""
    manager = get_config_manager(config_path)
    return manager.load()