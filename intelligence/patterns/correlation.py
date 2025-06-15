"""Correlation and relationship detection between variables"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from scipy.stats import pearsonr, spearmanr, kendalltau
from sklearn.feature_selection import mutual_info_regression
from sklearn.preprocessing import StandardScaler
import networkx as nx
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

from .base import (
    Pattern, PatternType, PatternDetector, PatternContext, 
    PatternEvidence
)


class CorrelationDetector(PatternDetector):
    """Detects various types of correlations and relationships between variables"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.5)
        self.lag_analysis = self.config.get('lag_analysis', True)
        self.max_lag = self.config.get('max_lag', 10)
        self.detect_nonlinear = self.config.get('detect_nonlinear', True)
        
    def get_supported_data_types(self) -> List[str]:
        return ['numeric']
    
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """Detect correlation patterns between columns"""
        
        if not self.validate_data(data, columns):
            return []
            
        patterns = []
        
        # Filter numeric columns
        numeric_columns = [col for col in columns 
                          if col in data.columns and pd.api.types.is_numeric_dtype(data[col])]
        
        if len(numeric_columns) < 2:
            return patterns
        
        # Pairwise correlation analysis
        for col1, col2 in combinations(numeric_columns, 2):
            # Linear correlations
            linear_pattern = self._detect_linear_correlation(data, col1, col2)
            if linear_pattern:
                patterns.append(linear_pattern)
            
            # Non-linear correlations
            if self.detect_nonlinear:
                nonlinear_pattern = self._detect_nonlinear_correlation(data, col1, col2)
                if nonlinear_pattern:
                    patterns.append(nonlinear_pattern)
            
            # Lagged correlations
            if self.lag_analysis and isinstance(data.index, pd.DatetimeIndex):
                lag_patterns = self._detect_lag_correlation(data, col1, col2)
                patterns.extend(lag_patterns)
        
        # Multivariate correlation network
        if len(numeric_columns) >= 3:
            network_pattern = self._detect_correlation_network(data[numeric_columns])
            if network_pattern:
                patterns.append(network_pattern)
        
        return patterns
    
    def _detect_linear_correlation(self, 
                                 data: pd.DataFrame, 
                                 col1: str, 
                                 col2: str) -> Optional[Pattern]:
        """Detect linear correlation between two variables"""
        
        # Prepare data
        df = data[[col1, col2]].dropna()
        if len(df) < self.min_samples:
            return None
        
        # Calculate correlations
        pearson_r, pearson_p = pearsonr(df[col1], df[col2])
        spearman_r, spearman_p = spearmanr(df[col1], df[col2])
        kendall_tau, kendall_p = kendalltau(df[col1], df[col2])
        
        # Check if any correlation is significant
        if abs(pearson_r) < self.correlation_threshold and \
           abs(spearman_r) < self.correlation_threshold:
            return None
        
        # Determine correlation type and strength
        if abs(pearson_r) >= abs(spearman_r):
            primary_correlation = pearson_r
            primary_p_value = pearson_p
            correlation_type = "linear"
        else:
            primary_correlation = spearman_r
            primary_p_value = spearman_p
            correlation_type = "monotonic"
        
        # Determine direction
        if primary_correlation > 0:
            direction = "positive"
            description = f"{col1} and {col2} show strong {direction} {correlation_type} correlation"
        else:
            direction = "negative"
            description = f"{col1} and {col2} show strong {direction} {correlation_type} correlation"
        
        # Calculate additional statistics
        # Coefficient of determination
        r_squared = pearson_r ** 2
        
        # Simple linear regression for more insights
        from scipy.stats import linregress
        slope, intercept, _, _, std_err = linregress(df[col1], df[col2])
        
        evidence = [
            PatternEvidence(
                description=f"Pearson correlation: {pearson_r:.3f} (p={pearson_p:.4f})",
                statistical_tests={
                    'pearson_r': float(pearson_r),
                    'pearson_p': float(pearson_p)
                }
            ),
            PatternEvidence(
                description=f"Spearman correlation: {spearman_r:.3f} (p={spearman_p:.4f})",
                statistical_tests={
                    'spearman_r': float(spearman_r),
                    'spearman_p': float(spearman_p)
                }
            ),
            PatternEvidence(
                description=f"R-squared: {r_squared:.3f} ({r_squared*100:.1f}% variance explained)",
                statistical_tests={'r_squared': float(r_squared)}
            )
        ]
        
        # Determine impact based on correlation strength
        abs_corr = abs(primary_correlation)
        if abs_corr > 0.8:
            impact = "high"
        elif abs_corr > 0.6:
            impact = "medium"
        else:
            impact = "low"
        
        return Pattern(
            type=PatternType.LINEAR_CORRELATION,
            confidence=min(0.95, abs_corr),
            description=description,
            column=f"{col1},{col2}",
            parameters={
                'column1': col1,
                'column2': col2,
                'pearson_r': float(pearson_r),
                'spearman_r': float(spearman_r),
                'kendall_tau': float(kendall_tau),
                'r_squared': float(r_squared),
                'slope': float(slope),
                'intercept': float(intercept),
                'direction': direction,
                'correlation_type': correlation_type
            },
            evidence=evidence,
            impact=impact,
            recommendations=self._generate_correlation_recommendations(
                col1, col2, primary_correlation, correlation_type
            ),
            visual_hints={
                'chart_type': 'scatter_plot',
                'x_axis': col1,
                'y_axis': col2,
                'show_regression_line': True,
                'show_confidence_interval': True
            }
        )
    
    def _detect_nonlinear_correlation(self, 
                                    data: pd.DataFrame, 
                                    col1: str, 
                                    col2: str) -> Optional[Pattern]:
        """Detect non-linear relationships using mutual information"""
        
        # Prepare data
        df = data[[col1, col2]].dropna()
        if len(df) < self.min_samples:
            return None
        
        # Already detected linear correlation?
        pearson_r, _ = pearsonr(df[col1], df[col2])
        
        # Calculate mutual information
        X = df[col1].values.reshape(-1, 1)
        y = df[col2].values
        
        # Normalize mutual information score
        mi_score = mutual_info_regression(X, y, random_state=42)[0]
        
        # Normalize by entropy for comparison
        from scipy.stats import entropy
        y_discrete = pd.qcut(y, q=10, duplicates='drop', labels=False)
        y_entropy = entropy(y_discrete.value_counts(normalize=True))
        
        normalized_mi = mi_score / y_entropy if y_entropy > 0 else 0
        
        # Only report if non-linear relationship is stronger than linear
        if normalized_mi > 0.3 and normalized_mi > abs(pearson_r):
            # Detect pattern type
            # Check for quadratic relationship
            X_squared = X ** 2
            quad_mi = mutual_info_regression(X_squared, y, random_state=42)[0]
            
            # Check for exponential/log relationship
            X_pos = X[X > 0]
            y_pos = y[X.flatten() > 0]
            if len(X_pos) > self.min_samples * 0.8:
                log_mi = mutual_info_regression(np.log(X_pos), y_pos, random_state=42)[0]
            else:
                log_mi = 0
            
            # Determine relationship type
            if quad_mi > mi_score * 1.2:
                relationship_type = "quadratic"
                description = f"{col1} and {col2} show quadratic relationship"
            elif log_mi > mi_score * 1.2:
                relationship_type = "logarithmic"
                description = f"{col1} and {col2} show logarithmic relationship"
            else:
                relationship_type = "complex non-linear"
                description = f"{col1} and {col2} show complex non-linear relationship"
            
            evidence = [
                PatternEvidence(
                    description=f"Mutual information score: {normalized_mi:.3f}",
                    statistical_tests={
                        'mutual_information': float(mi_score),
                        'normalized_mi': float(normalized_mi)
                    }
                ),
                PatternEvidence(
                    description=f"Stronger than linear correlation (r={pearson_r:.3f})",
                    statistical_tests={
                        'linear_correlation': float(pearson_r),
                        'nonlinear_strength': float(normalized_mi - abs(pearson_r))
                    }
                )
            ]
            
            return Pattern(
                type=PatternType.NON_LINEAR_CORRELATION,
                confidence=min(0.9, normalized_mi),
                description=description,
                column=f"{col1},{col2}",
                parameters={
                    'column1': col1,
                    'column2': col2,
                    'mutual_information': float(mi_score),
                    'normalized_mi': float(normalized_mi),
                    'relationship_type': relationship_type,
                    'linear_correlation': float(pearson_r)
                },
                evidence=evidence,
                impact="medium",
                recommendations=[
                    f"Consider {relationship_type} transformation for modeling",
                    "Non-linear relationship detected - linear models may not capture this",
                    "Use tree-based models or polynomial features"
                ],
                visual_hints={
                    'chart_type': 'scatter_plot',
                    'x_axis': col1,
                    'y_axis': col2,
                    'show_lowess': True,
                    'overlay_type': relationship_type
                }
            )
        
        return None
    
    def _detect_lag_correlation(self, 
                              data: pd.DataFrame, 
                              col1: str, 
                              col2: str) -> List[Pattern]:
        """Detect lagged correlations between time series"""
        patterns = []
        
        # Prepare data
        df = data[[col1, col2]].dropna()
        if len(df) < self.min_samples:
            return patterns
        
        # Test different lags
        significant_lags = []
        
        for lag in range(1, min(self.max_lag + 1, len(df) // 4)):
            # Create lagged series
            series1 = df[col1].values[:-lag]
            series2_lagged = df[col2].values[lag:]
            
            if len(series1) < self.min_samples:
                continue
            
            # Calculate correlation at this lag
            corr, p_value = pearsonr(series1, series2_lagged)
            
            if abs(corr) >= self.correlation_threshold and p_value < 0.05:
                significant_lags.append({
                    'lag': lag,
                    'correlation': float(corr),
                    'p_value': float(p_value)
                })
        
        # Also test negative lags (col2 leads col1)
        for lag in range(1, min(self.max_lag + 1, len(df) // 4)):
            series1_lagged = df[col1].values[lag:]
            series2 = df[col2].values[:-lag]
            
            if len(series2) < self.min_samples:
                continue
            
            corr, p_value = pearsonr(series1_lagged, series2)
            
            if abs(corr) >= self.correlation_threshold and p_value < 0.05:
                significant_lags.append({
                    'lag': -lag,
                    'correlation': float(corr),
                    'p_value': float(p_value)
                })
        
        if significant_lags:
            # Find best lag
            best_lag = max(significant_lags, key=lambda x: abs(x['correlation']))
            
            # Determine lead/lag relationship
            if best_lag['lag'] > 0:
                leader, follower = col1, col2
                lag_desc = f"{col2} follows {col1} by {best_lag['lag']} periods"
            else:
                leader, follower = col2, col1
                lag_desc = f"{col1} follows {col2} by {abs(best_lag['lag'])} periods"
            
            evidence = [
                PatternEvidence(
                    description=f"Strongest correlation at lag {best_lag['lag']}: r={best_lag['correlation']:.3f}",
                    statistical_tests=best_lag
                ),
                PatternEvidence(
                    description=f"Found {len(significant_lags)} significant lag correlations",
                    data_points=significant_lags[:5]
                )
            ]
            
            pattern = Pattern(
                type=PatternType.LAG_CORRELATION,
                confidence=min(0.9, abs(best_lag['correlation'])),
                description=f"{lag_desc} with correlation {best_lag['correlation']:.3f}",
                column=f"{col1},{col2}",
                parameters={
                    'column1': col1,
                    'column2': col2,
                    'best_lag': best_lag['lag'],
                    'best_correlation': best_lag['correlation'],
                    'leader': leader,
                    'follower': follower,
                    'all_significant_lags': significant_lags
                },
                evidence=evidence,
                impact="high" if abs(best_lag['correlation']) > 0.7 else "medium",
                recommendations=[
                    f"{leader} can be used to predict {follower} with {abs(best_lag['lag'])} period lead time",
                    "Consider using lagged features in predictive models",
                    "Investigate causal relationship between variables"
                ],
                visual_hints={
                    'chart_type': 'dual_line_chart',
                    'show_lag': best_lag['lag'],
                    'highlight_correlation': True
                }
            )
            
            patterns.append(pattern)
        
        return patterns
    
    def _detect_correlation_network(self, data: pd.DataFrame) -> Optional[Pattern]:
        """Detect network of correlations among multiple variables"""
        
        # Calculate correlation matrix
        corr_matrix = data.corr(method='pearson')
        
        # Create network graph
        G = nx.Graph()
        
        # Add edges for significant correlations
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]
                
                if abs(corr_value) >= self.correlation_threshold:
                    G.add_edge(col1, col2, weight=abs(corr_value), correlation=corr_value)
        
        if G.number_of_edges() == 0:
            return None
        
        # Analyze network structure
        # Find connected components
        components = list(nx.connected_components(G))
        
        # Calculate centrality measures
        degree_centrality = nx.degree_centrality(G)
        betweenness_centrality = nx.betweenness_centrality(G)
        
        # Find most central variables
        central_vars = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:3]
        
        # Find strongest correlations
        edges_with_weights = [(u, v, d['correlation']) for u, v, d in G.edges(data=True)]
        strongest_correlations = sorted(edges_with_weights, key=lambda x: abs(x[2]), reverse=True)[:5]
        
        evidence = [
            PatternEvidence(
                description=f"Correlation network with {G.number_of_nodes()} variables and {G.number_of_edges()} significant correlations",
                statistical_tests={
                    'nodes': G.number_of_nodes(),
                    'edges': G.number_of_edges(),
                    'components': len(components)
                }
            ),
            PatternEvidence(
                description=f"Most connected variables: {', '.join([v[0] for v in central_vars])}",
                data_points=[
                    {'variable': var, 'connections': int(deg * (G.number_of_nodes() - 1))}
                    for var, deg in central_vars
                ]
            ),
            PatternEvidence(
                description="Strongest correlations in network",
                data_points=[
                    {'var1': u, 'var2': v, 'correlation': float(corr)}
                    for u, v, corr in strongest_correlations
                ]
            )
        ]
        
        # Determine if there are distinct clusters
        if len(components) > 1:
            cluster_desc = f"with {len(components)} distinct clusters"
            recommendations = [
                "Variables form distinct correlation clusters",
                "Consider analyzing each cluster separately",
                "Different clusters may represent different underlying systems"
            ]
        else:
            cluster_desc = "forming a single connected network"
            recommendations = [
                "All variables are interconnected through correlations",
                f"{central_vars[0][0]} is the most central variable",
                "Consider dimension reduction techniques like PCA"
            ]
        
        return Pattern(
            type=PatternType.LINEAR_CORRELATION,
            confidence=0.85,
            description=f"Complex correlation network detected among {G.number_of_nodes()} variables {cluster_desc}",
            column=','.join(data.columns),
            parameters={
                'num_variables': G.number_of_nodes(),
                'num_correlations': G.number_of_edges(),
                'num_components': len(components),
                'central_variables': [v[0] for v in central_vars],
                'avg_correlation': float(np.mean([abs(d['correlation']) for _, _, d in G.edges(data=True)])),
                'network_density': float(nx.density(G))
            },
            evidence=evidence,
            impact="high",
            recommendations=recommendations,
            visual_hints={
                'chart_type': 'network_graph',
                'layout': 'force_directed',
                'color_by': 'centrality',
                'edge_width_by': 'correlation_strength'
            }
        )
    
    def _generate_correlation_recommendations(self,
                                            col1: str,
                                            col2: str,
                                            correlation: float,
                                            correlation_type: str) -> List[str]:
        """Generate recommendations based on correlation findings"""
        
        recommendations = []
        
        if abs(correlation) > 0.8:
            recommendations.extend([
                f"Very strong {correlation_type} correlation between {col1} and {col2}",
                "Consider multicollinearity issues if using both in predictive models",
                "One variable might be redundant"
            ])
        elif abs(correlation) > 0.6:
            recommendations.extend([
                f"Strong {correlation_type} correlation between {col1} and {col2}",
                "These variables provide related but not identical information",
                "Consider interaction effects in models"
            ])
        else:
            recommendations.extend([
                f"Moderate {correlation_type} correlation between {col1} and {col2}",
                "Both variables likely provide unique information",
                "Monitor this relationship over time"
            ])
        
        if correlation > 0:
            recommendations.append("Variables move in the same direction")
        else:
            recommendations.append("Variables move in opposite directions")
        
        return recommendations