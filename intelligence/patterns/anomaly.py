"""Anomaly detection using multiple algorithms including isolation forest, LOF, and statistical methods"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple, Union
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
from pyod.models.iforest import IForest
from pyod.models.lof import LOF
from pyod.models.knn import KNN
from pyod.models.combination import average, maximization
import warnings
warnings.filterwarnings('ignore')

from .base import (
    Pattern, PatternType, PatternDetector, PatternContext, 
    PatternEvidence
)


class AnomalyDetector(PatternDetector):
    """Advanced anomaly detection using ensemble methods"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.contamination = self.config.get('contamination', 0.1)  # Expected anomaly rate
        self.ensemble_methods = self.config.get('ensemble_methods', ['iforest', 'lof', 'knn'])
        self.sensitivity = self.config.get('sensitivity', 'medium')  # low, medium, high
        
        # Adjust thresholds based on sensitivity
        sensitivity_map = {
            'low': {'contamination': 0.05, 'confidence_threshold': 0.8},
            'medium': {'contamination': 0.1, 'confidence_threshold': 0.7},
            'high': {'contamination': 0.15, 'confidence_threshold': 0.6}
        }
        
        if self.sensitivity in sensitivity_map:
            self.contamination = sensitivity_map[self.sensitivity]['contamination']
            self.confidence_threshold = sensitivity_map[self.sensitivity]['confidence_threshold']
    
    def get_supported_data_types(self) -> List[str]:
        return ['numeric', 'mixed']
    
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """Detect anomalies using ensemble of methods"""
        
        if not self.validate_data(data, columns):
            return []
            
        patterns = []
        
        # Handle single column anomalies
        for col in columns:
            if col not in data.columns:
                continue
                
            series = data[col].dropna()
            
            if len(series) < self.min_samples:
                continue
            
            if pd.api.types.is_numeric_dtype(series):
                # Univariate anomaly detection
                anomaly_pattern = self._detect_univariate_anomalies(series, col, data)
                if anomaly_pattern:
                    patterns.append(anomaly_pattern)
        
        # Handle multivariate anomalies if multiple numeric columns
        numeric_columns = [col for col in columns 
                          if col in data.columns and pd.api.types.is_numeric_dtype(data[col])]
        
        if len(numeric_columns) >= 2:
            multivariate_patterns = self._detect_multivariate_anomalies(data[numeric_columns])
            patterns.extend(multivariate_patterns)
        
        # Contextual anomalies (if time series)
        if isinstance(data.index, pd.DatetimeIndex):
            for col in numeric_columns:
                contextual_pattern = self._detect_contextual_anomalies(data[col], col)
                if contextual_pattern:
                    patterns.append(contextual_pattern)
        
        return patterns
    
    def _detect_univariate_anomalies(self, 
                                   series: pd.Series, 
                                   col_name: str,
                                   full_data: pd.DataFrame) -> Optional[Pattern]:
        """Detect anomalies in single variable"""
        
        X = series.values.reshape(-1, 1)
        
        # Ensemble anomaly detection
        anomaly_scores = []
        detectors = []
        
        # Isolation Forest
        if 'iforest' in self.ensemble_methods:
            try:
                iforest = IForest(contamination=self.contamination, random_state=42)
                iforest.fit(X)
                scores_if = iforest.decision_function(X)
                anomaly_scores.append(scores_if)
                detectors.append('IsolationForest')
            except:
                pass
        
        # Local Outlier Factor
        if 'lof' in self.ensemble_methods:
            try:
                lof = LOF(contamination=self.contamination)
                lof.fit(X)
                scores_lof = lof.decision_function(X)
                anomaly_scores.append(scores_lof)
                detectors.append('LOF')
            except:
                pass
        
        # K-Nearest Neighbors
        if 'knn' in self.ensemble_methods:
            try:
                knn = KNN(contamination=self.contamination)
                knn.fit(X)
                scores_knn = knn.decision_function(X)
                anomaly_scores.append(scores_knn)
                detectors.append('KNN')
            except:
                pass
        
        if not anomaly_scores:
            return None
        
        # Combine scores using average
        combined_scores = np.mean(anomaly_scores, axis=0)
        
        # Determine threshold
        threshold = np.percentile(combined_scores, (1 - self.contamination) * 100)
        
        # Identify anomalies
        anomaly_mask = combined_scores > threshold
        anomaly_indices = np.where(anomaly_mask)[0]
        
        if len(anomaly_indices) == 0:
            return None
        
        # Get anomaly values and scores
        anomaly_values = series.iloc[anomaly_indices]
        anomaly_scores_list = combined_scores[anomaly_indices]
        
        # Statistical validation
        z_scores = np.abs((series - series.mean()) / series.std())
        statistical_anomalies = z_scores > 3
        
        # Calculate confidence
        ensemble_agreement = np.mean([
            (scores > np.percentile(scores, (1 - self.contamination) * 100)).astype(int)
            for scores in anomaly_scores
        ], axis=0)[anomaly_indices]
        
        avg_confidence = np.mean(ensemble_agreement)
        
        # Create evidence
        evidence = [
            PatternEvidence(
                description=f"Found {len(anomaly_indices)} anomalies using {len(detectors)} methods",
                statistical_tests={
                    'anomaly_count': len(anomaly_indices),
                    'anomaly_rate': len(anomaly_indices) / len(series),
                    'methods_used': len(detectors)
                }
            ),
            PatternEvidence(
                description=f"Average ensemble agreement: {avg_confidence:.1%}",
                statistical_tests={'ensemble_agreement': float(avg_confidence)}
            )
        ]
        
        # Add top anomalies as evidence
        top_anomalies = []
        for idx in anomaly_indices[:5]:
            original_idx = series.index[idx]
            top_anomalies.append({
                'index': str(original_idx),
                'value': float(series.iloc[idx]),
                'anomaly_score': float(combined_scores[idx]),
                'z_score': float(z_scores.iloc[idx])
            })
        
        evidence.append(PatternEvidence(
            description="Top anomalies detected",
            data_points=top_anomalies
        ))
        
        # Categorize anomalies
        anomaly_stats = {
            'total': len(anomaly_indices),
            'extreme_high': len(series.iloc[anomaly_indices][series.iloc[anomaly_indices] > series.quantile(0.99)]),
            'extreme_low': len(series.iloc[anomaly_indices][series.iloc[anomaly_indices] < series.quantile(0.01)])
        }
        
        return Pattern(
            type=PatternType.ANOMALY_POINT,
            confidence=avg_confidence,
            description=f"{col_name} contains {len(anomaly_indices)} anomalous values ({len(anomaly_indices)/len(series)*100:.1f}%)",
            column=col_name,
            parameters={
                'anomaly_count': len(anomaly_indices),
                'anomaly_rate': float(len(anomaly_indices) / len(series)),
                'detection_methods': detectors,
                'contamination': self.contamination,
                'anomaly_stats': anomaly_stats
            },
            evidence=evidence,
            impact="high" if len(anomaly_indices) / len(series) > 0.05 else "medium",
            recommendations=self._generate_anomaly_recommendations(col_name, anomaly_stats),
            visual_hints={
                'chart_type': 'scatter_plot',
                'highlight_anomalies': True,
                'show_threshold': True,
                'color_by': 'anomaly_score'
            }
        )
    
    def _detect_multivariate_anomalies(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect anomalies in multivariate data"""
        patterns = []
        
        # Prepare data
        X = data.dropna()
        if len(X) < self.min_samples:
            return patterns
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Apply multivariate anomaly detection
        try:
            # Isolation Forest for multivariate
            iforest = IsolationForest(
                contamination=self.contamination,
                random_state=42,
                n_estimators=100
            )
            predictions = iforest.fit_predict(X_scaled)
            anomaly_scores = iforest.score_samples(X_scaled)
            
            # Find anomalies
            anomaly_mask = predictions == -1
            anomaly_indices = np.where(anomaly_mask)[0]
            
            if len(anomaly_indices) > 0:
                # Analyze which features contribute most to anomalies
                feature_contributions = []
                
                for col in data.columns:
                    col_values = X[col].iloc[anomaly_indices]
                    normal_values = X[col].iloc[~anomaly_mask]
                    
                    # Calculate how different anomalies are from normal
                    if len(normal_values) > 0:
                        anomaly_mean = col_values.mean()
                        normal_mean = normal_values.mean()
                        normal_std = normal_values.std()
                        
                        if normal_std > 0:
                            deviation = abs(anomaly_mean - normal_mean) / normal_std
                            feature_contributions.append({
                                'feature': col,
                                'deviation': float(deviation),
                                'anomaly_mean': float(anomaly_mean),
                                'normal_mean': float(normal_mean)
                            })
                
                # Sort by contribution
                feature_contributions.sort(key=lambda x: x['deviation'], reverse=True)
                
                evidence = [
                    PatternEvidence(
                        description=f"Detected {len(anomaly_indices)} multivariate anomalies",
                        statistical_tests={
                            'anomaly_count': len(anomaly_indices),
                            'dimensions': len(data.columns)
                        }
                    ),
                    PatternEvidence(
                        description="Top contributing features to anomalies",
                        data_points=feature_contributions[:3]
                    )
                ]
                
                pattern = Pattern(
                    type=PatternType.ANOMALY_COLLECTIVE,
                    confidence=0.8,
                    description=f"Multivariate anomalies detected across {len(data.columns)} features",
                    column=','.join(data.columns),
                    parameters={
                        'anomaly_count': len(anomaly_indices),
                        'anomaly_rate': float(len(anomaly_indices) / len(X)),
                        'top_contributors': feature_contributions[:3],
                        'detection_method': 'IsolationForest'
                    },
                    evidence=evidence,
                    impact="high",
                    recommendations=[
                        "Investigate combinations of features that create anomalies",
                        f"Focus on {feature_contributions[0]['feature']} which shows highest deviation",
                        "Consider multivariate monitoring for these feature combinations"
                    ],
                    visual_hints={
                        'chart_type': 'parallel_coordinates',
                        'highlight_anomalies': True,
                        'show_feature_importance': True
                    }
                )
                
                patterns.append(pattern)
                
        except Exception:
            pass
        
        return patterns
    
    def _detect_contextual_anomalies(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect anomalies that are contextual (e.g., time-based)"""
        
        if len(series) < self.min_samples * 2:
            return None
        
        try:
            # Create time-based features
            df = pd.DataFrame({'value': series})
            
            # Add time features if datetime index
            if isinstance(series.index, pd.DatetimeIndex):
                df['hour'] = series.index.hour
                df['dayofweek'] = series.index.dayofweek
                df['month'] = series.index.month
                
                # Group by time context and find anomalies within each group
                contextual_anomalies = []
                
                # Check hourly patterns (if applicable)
                if df['hour'].nunique() > 1:
                    for hour in df['hour'].unique():
                        hour_data = df[df['hour'] == hour]['value']
                        if len(hour_data) >= 10:
                            # Find anomalies within this hour
                            mean = hour_data.mean()
                            std = hour_data.std()
                            
                            if std > 0:
                                z_scores = np.abs((hour_data - mean) / std)
                                hour_anomalies = hour_data[z_scores > 3]
                                
                                for idx, val in hour_anomalies.items():
                                    contextual_anomalies.append({
                                        'index': str(idx),
                                        'value': float(val),
                                        'context': f'hour_{hour}',
                                        'expected_mean': float(mean),
                                        'z_score': float(z_scores[idx])
                                    })
                
                if contextual_anomalies:
                    # Group anomalies by context
                    context_groups = {}
                    for anom in contextual_anomalies:
                        ctx = anom['context']
                        if ctx not in context_groups:
                            context_groups[ctx] = []
                        context_groups[ctx].append(anom)
                    
                    evidence = [
                        PatternEvidence(
                            description=f"Found {len(contextual_anomalies)} contextual anomalies",
                            statistical_tests={'total_contextual_anomalies': len(contextual_anomalies)}
                        ),
                        PatternEvidence(
                            description=f"Anomalies found in {len(context_groups)} different contexts",
                            data_points=list(context_groups.keys())
                        )
                    ]
                    
                    # Add examples
                    example_anomalies = contextual_anomalies[:5]
                    evidence.append(PatternEvidence(
                        description="Example contextual anomalies",
                        data_points=example_anomalies
                    ))
                    
                    return Pattern(
                        type=PatternType.ANOMALY_COLLECTIVE,
                        confidence=0.75,
                        description=f"{col_name} shows contextual anomalies based on time patterns",
                        column=col_name,
                        parameters={
                            'anomaly_count': len(contextual_anomalies),
                            'contexts_affected': len(context_groups),
                            'context_types': list(context_groups.keys())[:5]
                        },
                        evidence=evidence,
                        impact="medium",
                        recommendations=[
                            "Consider time-based alerting thresholds",
                            "Anomalies vary by time context (hour, day, etc.)",
                            "Implement context-aware monitoring"
                        ],
                        visual_hints={
                            'chart_type': 'heatmap',
                            'group_by': 'time_context',
                            'highlight_anomalies': True
                        }
                    )
                    
        except Exception:
            pass
        
        return None
    
    def _generate_anomaly_recommendations(self, 
                                        col_name: str, 
                                        anomaly_stats: Dict[str, int]) -> List[str]:
        """Generate recommendations based on anomaly characteristics"""
        
        recommendations = [
            f"Investigate {anomaly_stats['total']} anomalous values in {col_name}",
            "Set up automated anomaly detection alerts"
        ]
        
        if anomaly_stats['extreme_high'] > anomaly_stats['extreme_low']:
            recommendations.append("Focus on unusually high values - possible system overload or data errors")
        elif anomaly_stats['extreme_low'] > anomaly_stats['extreme_high']:
            recommendations.append("Focus on unusually low values - possible system failures or missing data")
        else:
            recommendations.append("Anomalies occur in both directions - investigate root causes")
        
        if anomaly_stats['total'] > 10:
            recommendations.append("High number of anomalies - consider if this is expected behavior")
        
        return recommendations