"""Base classes and interfaces for pattern detection"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class PatternType(Enum):
    """Types of patterns that can be detected"""
    # Statistical patterns
    NORMAL_DISTRIBUTION = "normal_distribution"
    SKEWED_DISTRIBUTION = "skewed_distribution"
    BIMODAL_DISTRIBUTION = "bimodal_distribution"
    UNIFORM_DISTRIBUTION = "uniform_distribution"
    POWER_LAW = "power_law"
    
    # Time series patterns
    TREND_LINEAR = "trend_linear"
    TREND_EXPONENTIAL = "trend_exponential"
    SEASONAL = "seasonal"
    CYCLIC = "cyclic"
    
    # Anomaly patterns
    OUTLIER = "outlier"
    ANOMALY_POINT = "anomaly_point"
    ANOMALY_COLLECTIVE = "anomaly_collective"
    CHANGE_POINT = "change_point"
    
    # Correlation patterns
    LINEAR_CORRELATION = "linear_correlation"
    NON_LINEAR_CORRELATION = "non_linear_correlation"
    LAG_CORRELATION = "lag_correlation"
    CAUSALITY = "causality"
    
    # Data quality patterns
    MISSING_DATA = "missing_data"
    DUPLICATE_DATA = "duplicate_data"
    INCONSISTENT_DATA = "inconsistent_data"
    
    # Behavioral patterns
    USER_BEHAVIOR = "user_behavior"
    SYSTEM_BEHAVIOR = "system_behavior"
    ERROR_PATTERN = "error_pattern"
    PERFORMANCE_PATTERN = "performance_pattern"


@dataclass
class PatternEvidence:
    """Evidence supporting a detected pattern"""
    description: str
    data_points: Optional[List[Dict[str, Any]]] = None
    statistical_tests: Optional[Dict[str, float]] = None
    visual_indicators: Optional[Dict[str, Any]] = None
    

@dataclass
class Pattern:
    """Represents a detected pattern in data"""
    type: PatternType
    confidence: float  # 0.0 to 1.0
    description: str
    column: str
    parameters: Dict[str, Any]
    evidence: List[PatternEvidence]
    detected_at: datetime = field(default_factory=datetime.utcnow)
    impact: str = "medium"  # low, medium, high
    recommendations: List[str] = field(default_factory=list)
    visual_hints: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary for serialization"""
        return {
            "type": self.type.value,
            "confidence": round(self.confidence, 3),
            "description": self.description,
            "column": self.column,
            "parameters": self.parameters,
            "evidence": [
                {
                    "description": e.description,
                    "data_points": e.data_points,
                    "statistical_tests": e.statistical_tests,
                    "visual_indicators": e.visual_indicators
                }
                for e in self.evidence
            ],
            "detected_at": self.detected_at.isoformat(),
            "impact": self.impact,
            "recommendations": self.recommendations,
            "visual_hints": self.visual_hints
        }
    
    def __str__(self) -> str:
        return f"Pattern({self.type.value}, confidence={self.confidence:.2f}, column={self.column})"


@dataclass
class PatternContext:
    """Context information for pattern detection"""
    data_profile: Dict[str, Any]
    business_context: Optional[Dict[str, str]] = None
    detection_params: Optional[Dict[str, Any]] = None
    time_range: Optional[Tuple[datetime, datetime]] = None
    

class PatternDetector(ABC):
    """Abstract base class for all pattern detectors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_samples = self.config.get('min_samples', 30)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)
        
    @abstractmethod
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """
        Detect patterns in the specified columns
        
        Args:
            data: DataFrame containing the data to analyze
            columns: List of column names to analyze
            context: Optional context information
            
        Returns:
            List of detected patterns
        """
        pass
    
    @abstractmethod
    def get_supported_data_types(self) -> List[str]:
        """Return data types this detector can handle"""
        pass
    
    def validate_data(self, data: pd.DataFrame, columns: List[str]) -> bool:
        """Validate that data meets minimum requirements"""
        if data.empty:
            return False
            
        for col in columns:
            if col not in data.columns:
                return False
            
            if data[col].notna().sum() < self.min_samples:
                return False
                
        return True
    
    def calculate_confidence(self, 
                           evidence: List[PatternEvidence],
                           sample_size: int,
                           test_results: Dict[str, float]) -> float:
        """
        Calculate confidence score for a pattern
        
        Args:
            evidence: List of evidence supporting the pattern
            sample_size: Number of samples analyzed
            test_results: Statistical test results
            
        Returns:
            Confidence score between 0 and 1
        """
        # Base confidence from sample size
        sample_confidence = min(1.0, sample_size / 1000)
        
        # Confidence from statistical tests
        test_confidence = np.mean([
            v for v in test_results.values() 
            if isinstance(v, (int, float)) and 0 <= v <= 1
        ]) if test_results else 0.5
        
        # Evidence strength
        evidence_confidence = min(1.0, len(evidence) / 3)
        
        # Weighted average
        confidence = (
            0.3 * sample_confidence +
            0.5 * test_confidence +
            0.2 * evidence_confidence
        )
        
        return min(1.0, max(0.0, confidence))
    
    def generate_recommendations(self, pattern: Pattern) -> List[str]:
        """Generate actionable recommendations based on pattern"""
        recommendations = []
        
        if pattern.type in [PatternType.OUTLIER, PatternType.ANOMALY_POINT]:
            recommendations.append(f"Investigate anomalies in {pattern.column}")
            recommendations.append("Consider setting up alerts for similar patterns")
            
        elif pattern.type in [PatternType.TREND_LINEAR, PatternType.TREND_EXPONENTIAL]:
            if pattern.parameters.get('slope', 0) > 0:
                recommendations.append(f"Monitor increasing trend in {pattern.column}")
            else:
                recommendations.append(f"Monitor decreasing trend in {pattern.column}")
                
        elif pattern.type == PatternType.SEASONAL:
            recommendations.append(f"Account for seasonality when forecasting {pattern.column}")
            recommendations.append("Consider seasonal adjustments in analysis")
            
        elif pattern.type == PatternType.MISSING_DATA:
            recommendations.append(f"Address missing data in {pattern.column}")
            recommendations.append("Consider imputation strategies or data collection improvements")
            
        return recommendations


class CompositePatternDetector(PatternDetector):
    """Detector that combines multiple pattern detectors"""
    
    def __init__(self, detectors: List[PatternDetector], config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.detectors = detectors
        
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """Run all detectors and combine results"""
        all_patterns = []
        
        for detector in self.detectors:
            try:
                patterns = detector.detect(data, columns, context)
                all_patterns.extend(patterns)
            except Exception as e:
                # Log error but continue with other detectors
                print(f"Error in {detector.__class__.__name__}: {e}")
                
        # Sort by confidence
        all_patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return all_patterns
    
    def get_supported_data_types(self) -> List[str]:
        """Return union of all supported data types"""
        types = set()
        for detector in self.detectors:
            types.update(detector.get_supported_data_types())
        return list(types)