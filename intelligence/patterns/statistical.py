"""Statistical pattern detection for numeric and categorical data"""

import numpy as np
import pandas as pd
import scipy.stats as stats
from typing import List, Dict, Any, Optional, Tuple
import warnings
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture

from .base import (
    Pattern, PatternType, PatternDetector, PatternContext, 
    PatternEvidence
)


class StatisticalPatternDetector(PatternDetector):
    """Detects statistical patterns in data distributions"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.distribution_tests = self.config.get('distribution_tests', True)
        self.outlier_detection = self.config.get('outlier_detection', True)
        self.categorical_analysis = self.config.get('categorical_analysis', True)
        
    def get_supported_data_types(self) -> List[str]:
        return ['numeric', 'categorical', 'boolean']
    
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """Detect statistical patterns in specified columns"""
        
        if not self.validate_data(data, columns):
            return []
            
        patterns = []
        
        for col in columns:
            if col not in data.columns:
                continue
                
            series = data[col].dropna()
            
            if len(series) < self.min_samples:
                continue
            
            # Detect patterns based on data type
            if pd.api.types.is_numeric_dtype(series):
                patterns.extend(self._detect_numeric_patterns(series, col, data))
            elif pd.api.types.is_string_dtype(series) or pd.api.types.is_categorical_dtype(series):
                patterns.extend(self._detect_categorical_patterns(series, col))
            elif pd.api.types.is_bool_dtype(series):
                patterns.extend(self._detect_boolean_patterns(series, col))
                
        return patterns
    
    def _detect_numeric_patterns(self, 
                               series: pd.Series, 
                               col_name: str,
                               full_data: pd.DataFrame) -> List[Pattern]:
        """Detect patterns in numeric data"""
        patterns = []
        
        # Basic statistics
        stats_dict = {
            'mean': float(series.mean()),
            'median': float(series.median()),
            'std': float(series.std()),
            'skew': float(series.skew()),
            'kurtosis': float(series.kurtosis()),
            'min': float(series.min()),
            'max': float(series.max()),
            'q1': float(series.quantile(0.25)),
            'q3': float(series.quantile(0.75))
        }
        
        # Distribution detection
        if self.distribution_tests:
            dist_pattern = self._detect_distribution(series, col_name, stats_dict)
            if dist_pattern:
                patterns.append(dist_pattern)
        
        # Outlier detection
        if self.outlier_detection:
            outlier_patterns = self._detect_outliers(series, col_name, stats_dict)
            patterns.extend(outlier_patterns)
        
        # Bimodal/Multimodal detection
        multimodal_pattern = self._detect_multimodal(series, col_name)
        if multimodal_pattern:
            patterns.append(multimodal_pattern)
        
        # Missing data patterns
        missing_pattern = self._detect_missing_patterns(full_data[col_name], col_name)
        if missing_pattern:
            patterns.append(missing_pattern)
            
        return patterns
    
    def _detect_distribution(self, 
                           series: pd.Series, 
                           col_name: str,
                           stats_dict: Dict[str, float]) -> Optional[Pattern]:
        """Identify the distribution type of numeric data"""
        
        # Normalize the data
        data_normalized = (series - series.mean()) / series.std()
        
        # Test for normal distribution
        statistic, p_value = stats.normaltest(series)
        
        evidence = []
        test_results = {'normaltest_pvalue': p_value}
        
        if p_value > 0.05:
            # Likely normal distribution
            pattern_type = PatternType.NORMAL_DISTRIBUTION
            description = f"{col_name} follows a normal distribution"
            
            # Additional evidence
            evidence.append(PatternEvidence(
                description="Passed normality test",
                statistical_tests={'normaltest': p_value}
            ))
            
            # Shapiro-Wilk test for smaller samples
            if len(series) < 5000:
                shapiro_stat, shapiro_p = stats.shapiro(series)
                test_results['shapiro_pvalue'] = shapiro_p
                if shapiro_p > 0.05:
                    evidence.append(PatternEvidence(
                        description="Passed Shapiro-Wilk test",
                        statistical_tests={'shapiro': shapiro_p}
                    ))
                    
            confidence = self.calculate_confidence(evidence, len(series), test_results)
            
        else:
            # Check for skewed distribution
            skewness = stats_dict['skew']
            kurtosis = stats_dict['kurtosis']
            
            if abs(skewness) > 1:
                pattern_type = PatternType.SKEWED_DISTRIBUTION
                skew_direction = "right" if skewness > 0 else "left"
                description = f"{col_name} has a {skew_direction}-skewed distribution"
                
                evidence.append(PatternEvidence(
                    description=f"High skewness value: {skewness:.2f}",
                    statistical_tests={'skewness': abs(skewness)}
                ))
                
                confidence = min(1.0, abs(skewness) / 3)  # Scale confidence by skewness
                
            elif stats_dict['std'] < 0.1 * abs(stats_dict['mean']):
                # Very low variance - possibly uniform
                pattern_type = PatternType.UNIFORM_DISTRIBUTION
                description = f"{col_name} has low variance, possibly uniform distribution"
                
                evidence.append(PatternEvidence(
                    description=f"Low coefficient of variation: {stats_dict['std']/abs(stats_dict['mean']):.3f}",
                    statistical_tests={'cv': stats_dict['std']/abs(stats_dict['mean'])}
                ))
                
                confidence = 0.6
                
            else:
                # No clear distribution pattern
                return None
                
        return Pattern(
            type=pattern_type,
            confidence=confidence,
            description=description,
            column=col_name,
            parameters=stats_dict,
            evidence=evidence,
            recommendations=self.generate_recommendations_for_distribution(pattern_type, col_name),
            visual_hints={
                'chart_type': 'histogram',
                'overlay': 'distribution_curve',
                'bins': 30
            }
        )
    
    def _detect_outliers(self, 
                        series: pd.Series, 
                        col_name: str,
                        stats_dict: Dict[str, float]) -> List[Pattern]:
        """Detect outliers using multiple methods"""
        patterns = []
        
        # IQR method
        q1 = stats_dict['q1']
        q3 = stats_dict['q3']
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        outliers_iqr = series[(series < lower_bound) | (series > upper_bound)]
        
        if len(outliers_iqr) > 0:
            outlier_percentage = len(outliers_iqr) / len(series) * 100
            
            evidence = [
                PatternEvidence(
                    description=f"Found {len(outliers_iqr)} outliers using IQR method",
                    data_points=[
                        {'value': float(val), 'index': int(idx)} 
                        for idx, val in outliers_iqr.head(10).items()
                    ],
                    statistical_tests={'outlier_percentage': outlier_percentage}
                )
            ]
            
            # Z-score method for comparison
            z_scores = np.abs(stats.zscore(series))
            outliers_zscore = series[z_scores > 3]
            
            if len(outliers_zscore) > 0:
                evidence.append(PatternEvidence(
                    description=f"Found {len(outliers_zscore)} outliers using Z-score method (|z| > 3)",
                    statistical_tests={'zscore_outliers': len(outliers_zscore)}
                ))
            
            pattern = Pattern(
                type=PatternType.OUTLIER,
                confidence=min(1.0, outlier_percentage / 5),  # 5% outliers = high confidence
                description=f"{col_name} contains {outlier_percentage:.1f}% outliers",
                column=col_name,
                parameters={
                    'outlier_count': len(outliers_iqr),
                    'outlier_percentage': outlier_percentage,
                    'lower_bound': lower_bound,
                    'upper_bound': upper_bound,
                    'method': 'IQR'
                },
                evidence=evidence,
                impact="high" if outlier_percentage > 5 else "medium",
                recommendations=[
                    f"Investigate {len(outliers_iqr)} outlier values in {col_name}",
                    "Consider outlier removal or transformation for modeling",
                    "Check if outliers represent valid extreme values or data errors"
                ],
                visual_hints={
                    'chart_type': 'box_plot',
                    'highlight': 'outliers',
                    'show_threshold_lines': True
                }
            )
            
            patterns.append(pattern)
            
        return patterns
    
    def _detect_multimodal(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect if distribution has multiple modes"""
        
        # Use Gaussian Mixture Model to detect multiple components
        data_reshaped = series.values.reshape(-1, 1)
        
        # Test for 2 components
        try:
            gmm = GaussianMixture(n_components=2, random_state=42)
            gmm.fit(data_reshaped)
            
            # Get BIC scores for different numbers of components
            bic_scores = []
            for n in range(1, 4):
                gmm_test = GaussianMixture(n_components=n, random_state=42)
                gmm_test.fit(data_reshaped)
                bic_scores.append(gmm_test.bic(data_reshaped))
            
            # If 2+ components is better than 1 component
            if bic_scores[1] < bic_scores[0]:
                means = gmm.means_.flatten()
                weights = gmm.weights_
                
                evidence = [
                    PatternEvidence(
                        description=f"Detected {len(means)} distinct modes",
                        statistical_tests={
                            'bic_1_component': bic_scores[0],
                            'bic_2_components': bic_scores[1],
                            'improvement': (bic_scores[0] - bic_scores[1]) / bic_scores[0]
                        }
                    ),
                    PatternEvidence(
                        description=f"Mode centers: {', '.join([f'{m:.2f}' for m in means])}",
                        statistical_tests={
                            f'mode_{i}_weight': float(w) 
                            for i, w in enumerate(weights)
                        }
                    )
                ]
                
                return Pattern(
                    type=PatternType.BIMODAL_DISTRIBUTION,
                    confidence=min(0.9, (bic_scores[0] - bic_scores[1]) / bic_scores[0] * 10),
                    description=f"{col_name} shows bimodal distribution with peaks at {means[0]:.2f} and {means[1]:.2f}",
                    column=col_name,
                    parameters={
                        'n_modes': 2,
                        'mode_centers': means.tolist(),
                        'mode_weights': weights.tolist()
                    },
                    evidence=evidence,
                    recommendations=[
                        f"Consider segmenting {col_name} data by the two distinct groups",
                        "Investigate what causes the bimodal distribution",
                        "Use mixture models for more accurate analysis"
                    ],
                    visual_hints={
                        'chart_type': 'histogram',
                        'overlay': 'kde',
                        'show_modes': True
                    }
                )
                
        except Exception:
            # GMM fitting failed
            pass
            
        return None
    
    def _detect_categorical_patterns(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect patterns in categorical data"""
        patterns = []
        
        # Value counts and proportions
        value_counts = series.value_counts()
        proportions = value_counts / len(series)
        
        # Cardinality analysis
        cardinality = len(value_counts)
        cardinality_ratio = cardinality / len(series)
        
        # High cardinality detection
        if cardinality_ratio > 0.5:
            pattern = Pattern(
                type=PatternType.INCONSISTENT_DATA,
                confidence=min(1.0, cardinality_ratio),
                description=f"{col_name} has high cardinality ({cardinality} unique values)",
                column=col_name,
                parameters={
                    'cardinality': cardinality,
                    'total_records': len(series),
                    'cardinality_ratio': cardinality_ratio
                },
                evidence=[
                    PatternEvidence(
                        description=f"Column contains {cardinality} unique values out of {len(series)} records",
                        statistical_tests={'cardinality_ratio': cardinality_ratio}
                    )
                ],
                impact="high",
                recommendations=[
                    f"Consider grouping similar values in {col_name}",
                    "Check for data entry inconsistencies",
                    "May not be suitable for categorical encoding"
                ]
            )
            patterns.append(pattern)
        
        # Imbalanced distribution detection
        if len(proportions) > 1:
            max_prop = proportions.max()
            if max_prop > 0.8:  # One category dominates
                dominant_value = proportions.idxmax()
                
                pattern = Pattern(
                    type=PatternType.SKEWED_DISTRIBUTION,
                    confidence=max_prop,
                    description=f"{col_name} is dominated by value '{dominant_value}' ({max_prop:.1%})",
                    column=col_name,
                    parameters={
                        'dominant_value': str(dominant_value),
                        'dominant_proportion': float(max_prop),
                        'value_distribution': proportions.to_dict()
                    },
                    evidence=[
                        PatternEvidence(
                            description=f"Value '{dominant_value}' appears in {max_prop:.1%} of records",
                            data_points=[
                                {'value': str(val), 'count': int(count), 'proportion': float(prop)}
                                for val, count, prop in zip(
                                    value_counts.index[:5], 
                                    value_counts.values[:5],
                                    proportions.values[:5]
                                )
                            ]
                        )
                    ],
                    impact="medium",
                    recommendations=[
                        f"Consider if '{dominant_value}' should be the default value",
                        "May need to handle class imbalance for modeling",
                        "Investigate why this value dominates"
                    ],
                    visual_hints={
                        'chart_type': 'bar_chart',
                        'sort': 'descending',
                        'show_percentages': True
                    }
                )
                patterns.append(pattern)
                
        return patterns
    
    def _detect_boolean_patterns(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect patterns in boolean data"""
        patterns = []
        
        # Calculate true/false ratio
        true_count = series.sum()
        false_count = len(series) - true_count
        true_ratio = true_count / len(series)
        
        # Check for imbalance
        if true_ratio > 0.9 or true_ratio < 0.1:
            dominant_value = True if true_ratio > 0.5 else False
            dominant_ratio = max(true_ratio, 1 - true_ratio)
            
            pattern = Pattern(
                type=PatternType.SKEWED_DISTRIBUTION,
                confidence=dominant_ratio,
                description=f"{col_name} is heavily skewed towards {dominant_value} ({dominant_ratio:.1%})",
                column=col_name,
                parameters={
                    'true_count': int(true_count),
                    'false_count': int(false_count),
                    'true_ratio': float(true_ratio),
                    'dominant_value': dominant_value
                },
                evidence=[
                    PatternEvidence(
                        description=f"{dominant_value} appears in {dominant_ratio:.1%} of records",
                        statistical_tests={'imbalance_ratio': dominant_ratio}
                    )
                ],
                impact="medium",
                recommendations=[
                    f"Consider if {col_name} provides meaningful signal given the imbalance",
                    "May need special handling for modeling",
                    f"Investigate why {dominant_value} dominates"
                ]
            )
            patterns.append(pattern)
            
        return patterns
    
    def _detect_missing_patterns(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect patterns in missing data"""
        
        total_count = len(series)
        missing_count = series.isna().sum()
        missing_ratio = missing_count / total_count
        
        if missing_count == 0:
            return None
            
        # Analyze missing data pattern
        evidence = []
        
        # Check if missing data is random or has pattern
        if hasattr(series.index, 'date'):
            # Time-based analysis
            missing_by_time = series.isna().groupby(series.index.date).sum()
            if missing_by_time.std() > missing_by_time.mean() * 0.5:
                evidence.append(PatternEvidence(
                    description="Missing data varies significantly over time",
                    statistical_tests={'temporal_variation': float(missing_by_time.std())}
                ))
                
        # Severity based on percentage
        if missing_ratio > 0.5:
            impact = "high"
            recommendations = [
                f"Critical: {missing_ratio:.1%} of {col_name} is missing",
                "Consider dropping this column or advanced imputation",
                "Investigate data collection issues"
            ]
        elif missing_ratio > 0.2:
            impact = "medium"
            recommendations = [
                f"Significant missing data in {col_name} ({missing_ratio:.1%})",
                "Consider imputation strategies",
                "Analyze if missingness is informative"
            ]
        else:
            impact = "low"
            recommendations = [
                f"Some missing data in {col_name} ({missing_ratio:.1%})",
                "Simple imputation may be sufficient"
            ]
            
        return Pattern(
            type=PatternType.MISSING_DATA,
            confidence=0.95,  # High confidence in detecting missing data
            description=f"{col_name} has {missing_ratio:.1%} missing values",
            column=col_name,
            parameters={
                'missing_count': int(missing_count),
                'total_count': int(total_count),
                'missing_ratio': float(missing_ratio)
            },
            evidence=evidence,
            impact=impact,
            recommendations=recommendations,
            visual_hints={
                'chart_type': 'heatmap',
                'show_missing': True
            }
        )
    
    def generate_recommendations_for_distribution(self, 
                                                pattern_type: PatternType, 
                                                col_name: str) -> List[str]:
        """Generate specific recommendations based on distribution type"""
        
        if pattern_type == PatternType.NORMAL_DISTRIBUTION:
            return [
                f"{col_name} is normally distributed - suitable for parametric tests",
                "Can use mean and standard deviation for analysis",
                "Z-score normalization will be effective"
            ]
        elif pattern_type == PatternType.SKEWED_DISTRIBUTION:
            return [
                f"Consider log or Box-Cox transformation for {col_name}",
                "Use median instead of mean for central tendency",
                "Non-parametric tests may be more appropriate"
            ]
        elif pattern_type == PatternType.UNIFORM_DISTRIBUTION:
            return [
                f"{col_name} shows uniform distribution - check if this is expected",
                "May indicate synthetic or generated data",
                "Consider if binning or discretization is appropriate"
            ]
        else:
            return []