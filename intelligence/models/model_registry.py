"""ML Model Registry for pattern detection models"""

import os
import json
import pickle
import joblib
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
import hashlib
import logging
from enum import Enum

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Types of ML models"""
    ANOMALY_DETECTOR = "anomaly_detector"
    TIME_SERIES_FORECASTER = "time_series_forecaster"
    CLASSIFIER = "classifier"
    REGRESSOR = "regressor"
    CLUSTERING = "clustering"
    CUSTOM = "custom"


class ModelFormat(Enum):
    """Model serialization formats"""
    PICKLE = "pickle"
    JOBLIB = "joblib"
    ONNX = "onnx"
    CUSTOM = "custom"


@dataclass
class ModelMetadata:
    """Metadata for a registered model"""
    model_id: str
    name: str
    version: str
    model_type: ModelType
    description: str
    created_at: datetime
    updated_at: datetime
    
    # Training metadata
    training_data_hash: Optional[str] = None
    training_samples: Optional[int] = None
    training_features: Optional[List[str]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    
    # Performance metrics
    metrics: Optional[Dict[str, float]] = None
    validation_score: Optional[float] = None
    
    # Technical details
    model_class: Optional[str] = None
    dependencies: Optional[List[str]] = None
    file_size: Optional[int] = None
    file_format: ModelFormat = ModelFormat.JOBLIB
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert enums and datetimes
        data['model_type'] = self.model_type.value
        data['file_format'] = self.file_format.value
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        if self.last_used:
            data['last_used'] = self.last_used.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelMetadata':
        """Create from dictionary"""
        # Convert strings back to enums and datetimes
        data['model_type'] = ModelType(data['model_type'])
        data['file_format'] = ModelFormat(data['file_format'])
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        if data.get('last_used'):
            data['last_used'] = datetime.fromisoformat(data['last_used'])
        return cls(**data)


class ModelRegistry:
    """Registry for managing ML models"""
    
    def __init__(self, registry_path: Optional[str] = None):
        self.registry_path = Path(registry_path or self._get_default_path())
        self.registry_path.mkdir(parents=True, exist_ok=True)
        
        self.models_dir = self.registry_path / "models"
        self.models_dir.mkdir(exist_ok=True)
        
        self.metadata_file = self.registry_path / "registry.json"
        self._metadata_cache: Dict[str, ModelMetadata] = {}
        
        self._load_metadata()
    
    def _get_default_path(self) -> Path:
        """Get default registry path"""
        # Try common locations
        paths = [
            Path.home() / ".intelligence" / "models",
            Path("/var/lib/intelligence/models"),
            Path("./models")
        ]
        
        for path in paths:
            try:
                path.mkdir(parents=True, exist_ok=True)
                return path
            except PermissionError:
                continue
        
        # Fallback to current directory
        return Path("./models")
    
    def _load_metadata(self):
        """Load metadata from disk"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    for model_id, metadata_dict in data.items():
                        self._metadata_cache[model_id] = ModelMetadata.from_dict(metadata_dict)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk"""
        data = {
            model_id: metadata.to_dict()
            for model_id, metadata in self._metadata_cache.items()
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def register(self,
                model: Any,
                name: str,
                model_type: ModelType,
                version: str = "1.0.0",
                description: str = "",
                metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Register a new model
        
        Args:
            model: The model object to register
            name: Human-readable model name
            model_type: Type of model
            version: Model version
            description: Model description
            metadata: Additional metadata
            
        Returns:
            model_id: Unique identifier for the registered model
        """
        # Generate model ID
        model_id = self._generate_model_id(name, version)
        
        # Create metadata
        model_metadata = ModelMetadata(
            model_id=model_id,
            name=name,
            version=version,
            model_type=model_type,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            model_class=f"{model.__class__.__module__}.{model.__class__.__name__}"
        )
        
        # Add additional metadata
        if metadata:
            for key, value in metadata.items():
                if hasattr(model_metadata, key):
                    setattr(model_metadata, key, value)
        
        # Determine file format
        file_format = self._determine_format(model)
        model_metadata.file_format = file_format
        
        # Save model
        model_path = self.models_dir / f"{model_id}.{file_format.value}"
        self._save_model(model, model_path, file_format)
        
        # Update file size
        model_metadata.file_size = model_path.stat().st_size
        
        # Extract dependencies
        model_metadata.dependencies = self._extract_dependencies(model)
        
        # Store metadata
        self._metadata_cache[model_id] = model_metadata
        self._save_metadata()
        
        logger.info(f"Registered model: {model_id} ({name} v{version})")
        return model_id
    
    def load(self, model_id: str) -> Any:
        """
        Load a registered model
        
        Args:
            model_id: Model identifier
            
        Returns:
            The loaded model object
        """
        if model_id not in self._metadata_cache:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self._metadata_cache[model_id]
        model_path = self.models_dir / f"{model_id}.{metadata.file_format.value}"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Load model
        model = self._load_model(model_path, metadata.file_format)
        
        # Update usage tracking
        metadata.usage_count += 1
        metadata.last_used = datetime.utcnow()
        self._save_metadata()
        
        logger.info(f"Loaded model: {model_id}")
        return model
    
    def update(self,
              model_id: str,
              model: Any,
              version: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Update an existing model
        
        Args:
            model_id: Model identifier
            model: Updated model object
            version: New version (optional)
            metadata: Updated metadata
            
        Returns:
            New model_id if version changed
        """
        if model_id not in self._metadata_cache:
            raise ValueError(f"Model not found: {model_id}")
        
        old_metadata = self._metadata_cache[model_id]
        
        # If version changed, create new entry
        if version and version != old_metadata.version:
            new_id = self.register(
                model=model,
                name=old_metadata.name,
                model_type=old_metadata.model_type,
                version=version,
                description=old_metadata.description,
                metadata=metadata
            )
            logger.info(f"Created new version: {old_metadata.name} v{version}")
            return new_id
        
        # Update existing model
        model_path = self.models_dir / f"{model_id}.{old_metadata.file_format.value}"
        self._save_model(model, model_path, old_metadata.file_format)
        
        # Update metadata
        old_metadata.updated_at = datetime.utcnow()
        if metadata:
            for key, value in metadata.items():
                if hasattr(old_metadata, key):
                    setattr(old_metadata, key, value)
        
        self._save_metadata()
        logger.info(f"Updated model: {model_id}")
        return model_id
    
    def delete(self, model_id: str):
        """Delete a model from the registry"""
        if model_id not in self._metadata_cache:
            raise ValueError(f"Model not found: {model_id}")
        
        metadata = self._metadata_cache[model_id]
        model_path = self.models_dir / f"{model_id}.{metadata.file_format.value}"
        
        # Delete model file
        if model_path.exists():
            model_path.unlink()
        
        # Remove metadata
        del self._metadata_cache[model_id]
        self._save_metadata()
        
        logger.info(f"Deleted model: {model_id}")
    
    def list_models(self,
                   model_type: Optional[ModelType] = None,
                   name_filter: Optional[str] = None) -> List[ModelMetadata]:
        """
        List registered models
        
        Args:
            model_type: Filter by model type
            name_filter: Filter by name (substring match)
            
        Returns:
            List of model metadata
        """
        models = list(self._metadata_cache.values())
        
        # Apply filters
        if model_type:
            models = [m for m in models if m.model_type == model_type]
        
        if name_filter:
            models = [m for m in models if name_filter.lower() in m.name.lower()]
        
        # Sort by updated time
        models.sort(key=lambda m: m.updated_at, reverse=True)
        
        return models
    
    def get_metadata(self, model_id: str) -> ModelMetadata:
        """Get metadata for a model"""
        if model_id not in self._metadata_cache:
            raise ValueError(f"Model not found: {model_id}")
        
        return self._metadata_cache[model_id]
    
    def search(self, query: str) -> List[ModelMetadata]:
        """
        Search models by query
        
        Args:
            query: Search query
            
        Returns:
            List of matching models
        """
        query_lower = query.lower()
        matches = []
        
        for metadata in self._metadata_cache.values():
            # Search in name, description, and type
            if (query_lower in metadata.name.lower() or
                query_lower in metadata.description.lower() or
                query_lower in metadata.model_type.value):
                matches.append(metadata)
        
        return matches
    
    def get_versions(self, name: str) -> List[ModelMetadata]:
        """Get all versions of a model by name"""
        versions = [
            m for m in self._metadata_cache.values()
            if m.name == name
        ]
        
        # Sort by version
        versions.sort(key=lambda m: m.version)
        return versions
    
    def export_model(self, model_id: str, export_path: str, format: Optional[ModelFormat] = None):
        """
        Export a model to a specific path
        
        Args:
            model_id: Model identifier
            export_path: Path to export to
            format: Export format (optional)
        """
        model = self.load(model_id)
        metadata = self.get_metadata(model_id)
        
        format = format or metadata.file_format
        export_path = Path(export_path)
        
        # Export model
        self._save_model(model, export_path, format)
        
        # Export metadata
        metadata_path = export_path.with_suffix('.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata.to_dict(), f, indent=2)
        
        logger.info(f"Exported model {model_id} to {export_path}")
    
    def import_model(self, model_path: str, metadata_path: Optional[str] = None) -> str:
        """
        Import a model from file
        
        Args:
            model_path: Path to model file
            metadata_path: Path to metadata file (optional)
            
        Returns:
            model_id of imported model
        """
        model_path = Path(model_path)
        
        # Load metadata
        if metadata_path:
            with open(metadata_path, 'r') as f:
                metadata_dict = json.load(f)
                metadata = ModelMetadata.from_dict(metadata_dict)
        else:
            # Create basic metadata
            metadata = ModelMetadata(
                model_id=self._generate_model_id("imported", "1.0.0"),
                name="imported_model",
                version="1.0.0",
                model_type=ModelType.CUSTOM,
                description="Imported model",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        
        # Determine format from extension
        ext_map = {
            '.pkl': ModelFormat.PICKLE,
            '.joblib': ModelFormat.JOBLIB,
            '.onnx': ModelFormat.ONNX
        }
        format = ext_map.get(model_path.suffix, ModelFormat.CUSTOM)
        
        # Load and register model
        model = self._load_model(model_path, format)
        
        return self.register(
            model=model,
            name=metadata.name,
            model_type=metadata.model_type,
            version=metadata.version,
            description=metadata.description,
            metadata=metadata.to_dict()
        )
    
    def cleanup(self, days_unused: int = 30):
        """
        Clean up unused models
        
        Args:
            days_unused: Delete models not used in this many days
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_unused)
        models_to_delete = []
        
        for model_id, metadata in self._metadata_cache.items():
            if metadata.last_used and metadata.last_used < cutoff_date:
                models_to_delete.append(model_id)
        
        for model_id in models_to_delete:
            self.delete(model_id)
        
        logger.info(f"Cleaned up {len(models_to_delete)} unused models")
    
    def _generate_model_id(self, name: str, version: str) -> str:
        """Generate unique model ID"""
        base = f"{name}_{version}".replace(" ", "_").lower()
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        return f"{base}_{timestamp}"
    
    def _determine_format(self, model: Any) -> ModelFormat:
        """Determine best format for model"""
        # Check if model supports ONNX
        if hasattr(model, 'to_onnx'):
            return ModelFormat.ONNX
        
        # Default to joblib for sklearn models
        if isinstance(model, BaseEstimator):
            return ModelFormat.JOBLIB
        
        # Default to pickle
        return ModelFormat.PICKLE
    
    def _save_model(self, model: Any, path: Path, format: ModelFormat):
        """Save model to disk"""
        if format == ModelFormat.JOBLIB:
            joblib.dump(model, path)
        elif format == ModelFormat.PICKLE:
            with open(path, 'wb') as f:
                pickle.dump(model, f)
        elif format == ModelFormat.ONNX:
            # Placeholder for ONNX export
            raise NotImplementedError("ONNX format not yet implemented")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _load_model(self, path: Path, format: ModelFormat) -> Any:
        """Load model from disk"""
        if format == ModelFormat.JOBLIB:
            return joblib.load(path)
        elif format == ModelFormat.PICKLE:
            with open(path, 'rb') as f:
                return pickle.load(f)
        elif format == ModelFormat.ONNX:
            # Placeholder for ONNX import
            raise NotImplementedError("ONNX format not yet implemented")
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def _extract_dependencies(self, model: Any) -> List[str]:
        """Extract model dependencies"""
        dependencies = []
        
        # Get module dependencies
        if hasattr(model, '__module__'):
            module = model.__module__
            if module:
                base_module = module.split('.')[0]
                dependencies.append(base_module)
        
        # Add sklearn if it's a sklearn model
        if isinstance(model, BaseEstimator):
            dependencies.append('sklearn')
        
        return list(set(dependencies))


# Singleton instance
_registry: Optional[ModelRegistry] = None


def get_model_registry(registry_path: Optional[str] = None) -> ModelRegistry:
    """Get or create model registry singleton"""
    global _registry
    
    if _registry is None:
        _registry = ModelRegistry(registry_path)
    
    return _registry