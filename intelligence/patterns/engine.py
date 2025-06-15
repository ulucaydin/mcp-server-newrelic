"""Pattern Engine - Orchestrates all pattern detectors and provides unified interface"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
from datetime import datetime
import json
from dataclasses import asdict
from loguru import logger

from .base import (
    Pattern, PatternType, PatternDetector, PatternContext,
    CompositePatternDetector, PatternEvidence
)
from .statistical import StatisticalPatternDetector
from .timeseries import TimeSeriesPatternDetector
from .anomaly import AnomalyDetector
from .correlation import CorrelationDetector


class PatternEngine:
    """
    Main pattern detection engine that orchestrates multiple detectors
    and provides intelligent pattern analysis
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.parallel_execution = self.config.get('parallel_execution', True)
        self.max_workers = self.config.get('max_workers', 4)
        self.confidence_threshold = self.config.get('confidence_threshold', 0.5)
        self.pattern_limit = self.config.get('pattern_limit', 50)
        
        # Initialize detectors
        self.detectors = self._initialize_detectors()
        
        # Pattern cache for performance
        self.pattern_cache = {}
        
        # Metrics
        self.detection_metrics = {
            'total_detections': 0,
            'cache_hits': 0,
            'detection_times': []
        }
        
    def _initialize_detectors(self) -> Dict[str, PatternDetector]:
        """Initialize all available pattern detectors"""
        
        detector_configs = {
            'statistical': self.config.get('statistical_config', {}),
            'timeseries': self.config.get('timeseries_config', {}),
            'anomaly': self.config.get('anomaly_config', {}),
            'correlation': self.config.get('correlation_config', {})
        }
        
        detectors = {
            'statistical': StatisticalPatternDetector(detector_configs['statistical']),
            'timeseries': TimeSeriesPatternDetector(detector_configs['timeseries']),
            'anomaly': AnomalyDetector(detector_configs['anomaly']),
            'correlation': CorrelationDetector(detector_configs['correlation'])
        }
        
        # Add composite detector for convenience
        detectors['composite'] = CompositePatternDetector(
            list(detectors.values()),
            self.config
        )
        
        return detectors
    
    def analyze(self,
               data: pd.DataFrame,
               columns: Optional[List[str]] = None,
               context: Optional[PatternContext] = None,
               detector_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Main analysis method that runs pattern detection
        
        Args:
            data: DataFrame to analyze
            columns: Specific columns to analyze (None = all numeric)
            context: Additional context for detection
            detector_types: Specific detectors to use (None = all)
            
        Returns:
            Dictionary containing patterns, summary, and recommendations
        """
        start_time = datetime.utcnow()
        
        # Validate input
        if data.empty:
            return self._empty_result("No data provided")
        
        # Select columns if not specified
        if columns is None:
            columns = self._select_analyzable_columns(data)
        
        if not columns:
            return self._empty_result("No analyzable columns found")
        
        # Check cache
        cache_key = self._generate_cache_key(data, columns, detector_types)
        if cache_key in self.pattern_cache:
            self.detection_metrics['cache_hits'] += 1
            logger.info(f"Cache hit for pattern detection")
            return self.pattern_cache[cache_key]
        
        # Select detectors
        if detector_types:
            selected_detectors = {
                name: det for name, det in self.detectors.items()
                if name in detector_types
            }
        else:
            selected_detectors = {
                name: det for name, det in self.detectors.items()
                if name != 'composite'  # Avoid duplicate detection
            }
        
        # Run detection
        if self.parallel_execution and len(selected_detectors) > 1:
            patterns = self._run_parallel_detection(data, columns, selected_detectors, context)
        else:
            patterns = self._run_sequential_detection(data, columns, selected_detectors, context)
        
        # Post-process patterns
        patterns = self._post_process_patterns(patterns)
        
        # Generate insights
        insights = self._generate_insights(patterns, data, columns)
        
        # Create result
        result = {
            'patterns': [p.to_dict() for p in patterns],
            'summary': self._generate_summary(patterns, data, columns),
            'insights': insights,
            'recommendations': self._generate_recommendations(patterns, insights),
            'metadata': {
                'analysis_time': (datetime.utcnow() - start_time).total_seconds(),
                'data_shape': data.shape,
                'columns_analyzed': columns,
                'detectors_used': list(selected_detectors.keys()),
                'patterns_found': len(patterns)
            }
        }
        
        # Cache result
        self.pattern_cache[cache_key] = result
        
        # Update metrics
        self.detection_metrics['total_detections'] += 1
        self.detection_metrics['detection_times'].append(result['metadata']['analysis_time'])
        
        logger.info(f"Pattern detection completed: {len(patterns)} patterns found in {result['metadata']['analysis_time']:.2f}s")
        
        return result
    
    def _run_parallel_detection(self,
                              data: pd.DataFrame,
                              columns: List[str],
                              detectors: Dict[str, PatternDetector],
                              context: Optional[PatternContext]) -> List[Pattern]:
        """Run detectors in parallel for better performance"""
        patterns = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit detection tasks
            future_to_detector = {
                executor.submit(
                    detector.detect, 
                    data, 
                    columns, 
                    context
                ): name
                for name, detector in detectors.items()
            }
            
            # Collect results
            for future in as_completed(future_to_detector):
                detector_name = future_to_detector[future]
                try:
                    detector_patterns = future.result()
                    patterns.extend(detector_patterns)
                    logger.debug(f"{detector_name} found {len(detector_patterns)} patterns")
                except Exception as e:
                    logger.error(f"Error in {detector_name}: {e}")
        
        return patterns
    
    def _run_sequential_detection(self,
                                data: pd.DataFrame,
                                columns: List[str],
                                detectors: Dict[str, PatternDetector],
                                context: Optional[PatternContext]) -> List[Pattern]:
        """Run detectors sequentially"""
        patterns = []
        
        for name, detector in detectors.items():
            try:
                detector_patterns = detector.detect(data, columns, context)
                patterns.extend(detector_patterns)
                logger.debug(f"{name} found {len(detector_patterns)} patterns")
            except Exception as e:
                logger.error(f"Error in {name}: {e}")
        
        return patterns
    
    def _post_process_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Post-process patterns: deduplicate, rank, and filter"""
        
        # Remove duplicates
        unique_patterns = self._deduplicate_patterns(patterns)
        
        # Filter by confidence
        filtered_patterns = [
            p for p in unique_patterns 
            if p.confidence >= self.confidence_threshold
        ]
        
        # Rank patterns
        ranked_patterns = self._rank_patterns(filtered_patterns)
        
        # Limit number of patterns
        if len(ranked_patterns) > self.pattern_limit:
            logger.info(f"Limiting patterns from {len(ranked_patterns)} to {self.pattern_limit}")
            ranked_patterns = ranked_patterns[:self.pattern_limit]
        
        return ranked_patterns
    
    def _deduplicate_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Remove duplicate patterns based on type, column, and parameters"""
        seen = set()
        unique = []
        
        for pattern in patterns:
            # Create unique key
            key = (
                pattern.type.value,
                pattern.column,
                json.dumps(pattern.parameters, sort_keys=True)
            )
            
            if key not in seen:
                seen.add(key)
                unique.append(pattern)
        
        return unique
    
    def _rank_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Rank patterns by importance"""
        
        # Define pattern type importance
        type_importance = {
            PatternType.ANOMALY_POINT: 1.0,
            PatternType.ANOMALY_COLLECTIVE: 0.9,
            PatternType.CHANGE_POINT: 0.9,
            PatternType.TREND_EXPONENTIAL: 0.8,
            PatternType.MISSING_DATA: 0.8,
            PatternType.TREND_LINEAR: 0.7,
            PatternType.SEASONAL: 0.7,
            PatternType.LAG_CORRELATION: 0.7,
            PatternType.LINEAR_CORRELATION: 0.6,
            PatternType.NON_LINEAR_CORRELATION: 0.6,
            PatternType.BIMODAL_DISTRIBUTION: 0.5,
            PatternType.SKEWED_DISTRIBUTION: 0.4,
            PatternType.NORMAL_DISTRIBUTION: 0.3,
        }
        
        # Calculate scores
        for pattern in patterns:
            type_score = type_importance.get(pattern.type, 0.5)
            impact_score = {'high': 1.0, 'medium': 0.5, 'low': 0.2}.get(pattern.impact, 0.5)
            
            # Combined score
            pattern.score = (
                0.4 * pattern.confidence +
                0.4 * type_score +
                0.2 * impact_score
            )
        
        # Sort by score
        return sorted(patterns, key=lambda p: p.score, reverse=True)
    
    def _generate_insights(self, 
                          patterns: List[Pattern], 
                          data: pd.DataFrame,
                          columns: List[str]) -> List[Dict[str, Any]]:
        """Generate high-level insights from detected patterns"""
        insights = []
        
        # Group patterns by type
        pattern_groups = {}
        for pattern in patterns:
            pattern_type = pattern.type.value
            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []
            pattern_groups[pattern_type].append(pattern)
        
        # Anomaly insights
        if 'anomaly_point' in pattern_groups or 'anomaly_collective' in pattern_groups:
            anomaly_patterns = pattern_groups.get('anomaly_point', []) + pattern_groups.get('anomaly_collective', [])
            total_anomalies = sum(p.parameters.get('anomaly_count', 0) for p in anomaly_patterns)
            
            insights.append({
                'type': 'anomaly_summary',
                'title': 'Anomaly Detection Summary',
                'description': f"Found {total_anomalies} anomalies across {len(anomaly_patterns)} features",
                'severity': 'high' if total_anomalies > 50 else 'medium',
                'affected_columns': list(set(p.column for p in anomaly_patterns))
            })
        
        # Trend insights
        trend_types = ['trend_linear', 'trend_exponential']
        trend_patterns = []
        for t in trend_types:
            trend_patterns.extend(pattern_groups.get(t, []))
        
        if trend_patterns:
            increasing = [p for p in trend_patterns if p.parameters.get('slope', 0) > 0]
            decreasing = [p for p in trend_patterns if p.parameters.get('slope', 0) < 0]
            
            insights.append({
                'type': 'trend_summary',
                'title': 'Trend Analysis Summary',
                'description': f"Found {len(increasing)} increasing and {len(decreasing)} decreasing trends",
                'details': {
                    'increasing_metrics': [p.column for p in increasing],
                    'decreasing_metrics': [p.column for p in decreasing],
                    'exponential_trends': [p.column for p in trend_patterns if p.type == PatternType.TREND_EXPONENTIAL]
                }
            })
        
        # Correlation insights
        if 'linear_correlation' in pattern_groups or 'lag_correlation' in pattern_groups:
            corr_patterns = pattern_groups.get('linear_correlation', []) + pattern_groups.get('lag_correlation', [])
            strong_correlations = [p for p in corr_patterns if abs(p.parameters.get('pearson_r', 0)) > 0.7]
            
            if strong_correlations:
                insights.append({
                    'type': 'correlation_summary',
                    'title': 'Strong Correlations Detected',
                    'description': f"Found {len(strong_correlations)} strong correlations between metrics",
                    'details': [
                        {
                            'variables': p.column.split(','),
                            'correlation': p.parameters.get('pearson_r', p.parameters.get('best_correlation', 0)),
                            'type': 'lagged' if p.type == PatternType.LAG_CORRELATION else 'direct'
                        }
                        for p in strong_correlations[:5]
                    ]
                })
        
        # Data quality insights
        if 'missing_data' in pattern_groups:
            missing_patterns = pattern_groups['missing_data']
            critical_missing = [p for p in missing_patterns if p.parameters.get('missing_ratio', 0) > 0.2]
            
            if critical_missing:
                insights.append({
                    'type': 'data_quality',
                    'title': 'Data Quality Issues',
                    'description': f"{len(critical_missing)} columns have significant missing data",
                    'severity': 'high',
                    'affected_columns': [p.column for p in critical_missing],
                    'recommendations': [
                        "Address missing data before analysis",
                        "Consider data imputation strategies"
                    ]
                })
        
        return insights
    
    def _generate_summary(self, 
                         patterns: List[Pattern], 
                         data: pd.DataFrame,
                         columns: List[str]) -> Dict[str, Any]:
        """Generate executive summary of findings"""
        
        pattern_counts = {}
        for pattern in patterns:
            pattern_type = pattern.type.value
            pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
        
        return {
            'total_patterns': len(patterns),
            'pattern_types': pattern_counts,
            'high_impact_count': len([p for p in patterns if p.impact == 'high']),
            'high_confidence_count': len([p for p in patterns if p.confidence > 0.8]),
            'columns_with_patterns': len(set(p.column for p in patterns)),
            'data_characteristics': {
                'rows': len(data),
                'columns': len(data.columns),
                'numeric_columns': len([c for c in data.columns if pd.api.types.is_numeric_dtype(data[c])]),
                'memory_usage': data.memory_usage().sum() / 1024**2  # MB
            }
        }
    
    def _generate_recommendations(self, 
                                patterns: List[Pattern],
                                insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on patterns and insights"""
        recommendations = []
        
        # Collect all individual recommendations
        pattern_recommendations = []
        for pattern in patterns[:10]:  # Top 10 patterns
            for rec in pattern.recommendations:
                pattern_recommendations.append({
                    'recommendation': rec,
                    'source': f"{pattern.type.value} in {pattern.column}",
                    'confidence': pattern.confidence
                })
        
        # Priority recommendations based on insights
        for insight in insights:
            if insight.get('severity') == 'high':
                recommendations.append({
                    'priority': 'high',
                    'category': insight['type'],
                    'title': insight['title'],
                    'actions': insight.get('recommendations', [])
                })
        
        # Add top pattern recommendations
        seen_recs = set()
        for rec in sorted(pattern_recommendations, key=lambda x: x['confidence'], reverse=True):
            if rec['recommendation'] not in seen_recs:
                seen_recs.add(rec['recommendation'])
                recommendations.append({
                    'priority': 'medium',
                    'category': 'pattern_based',
                    'title': rec['recommendation'],
                    'source': rec['source']
                })
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _select_analyzable_columns(self, data: pd.DataFrame) -> List[str]:
        """Select columns suitable for pattern analysis"""
        analyzable = []
        
        for col in data.columns:
            # Numeric columns
            if pd.api.types.is_numeric_dtype(data[col]):
                analyzable.append(col)
            # Datetime columns (if index is not datetime)
            elif pd.api.types.is_datetime64_any_dtype(data[col]):
                if not isinstance(data.index, pd.DatetimeIndex):
                    analyzable.append(col)
            # Low cardinality categorical
            elif pd.api.types.is_string_dtype(data[col]) or pd.api.types.is_categorical_dtype(data[col]):
                if data[col].nunique() < 50:  # Threshold for categorical
                    analyzable.append(col)
        
        return analyzable
    
    def _generate_cache_key(self, 
                           data: pd.DataFrame, 
                           columns: List[str],
                           detector_types: Optional[List[str]]) -> str:
        """Generate cache key for pattern detection results"""
        
        # Use data shape, columns, and detector types
        key_parts = [
            str(data.shape),
            ','.join(sorted(columns)),
            ','.join(sorted(detector_types)) if detector_types else 'all'
        ]
        
        # Add data sample for uniqueness
        if len(data) > 0:
            sample_hash = hash(tuple(data.iloc[0].values))
            key_parts.append(str(sample_hash))
        
        return '|'.join(key_parts)
    
    def _empty_result(self, reason: str) -> Dict[str, Any]:
        """Return empty result with reason"""
        return {
            'patterns': [],
            'summary': {'total_patterns': 0, 'reason': reason},
            'insights': [],
            'recommendations': [],
            'metadata': {'error': reason}
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        avg_time = np.mean(self.detection_metrics['detection_times']) if self.detection_metrics['detection_times'] else 0
        
        return {
            'total_detections': self.detection_metrics['total_detections'],
            'cache_hits': self.detection_metrics['cache_hits'],
            'cache_hit_rate': self.detection_metrics['cache_hits'] / max(1, self.detection_metrics['total_detections']),
            'average_detection_time': avg_time,
            'cache_size': len(self.pattern_cache)
        }
    
    def clear_cache(self):
        """Clear pattern cache"""
        self.pattern_cache.clear()
        logger.info("Pattern cache cleared")