"""Time series pattern detection including trends, seasonality, and cycles"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.stats.diagnostic import acorr_ljungbox
import statsmodels.api as sm
from scipy import signal
from scipy.stats import linregress
import warnings
warnings.filterwarnings('ignore')

from .base import (
    Pattern, PatternType, PatternDetector, PatternContext, 
    PatternEvidence
)


class TimeSeriesPatternDetector(PatternDetector):
    """Detects patterns in time series data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.min_periods = self.config.get('min_periods', 50)
        self.seasonality_threshold = self.config.get('seasonality_threshold', 0.1)
        self.trend_threshold = self.config.get('trend_threshold', 0.05)
        
    def get_supported_data_types(self) -> List[str]:
        return ['numeric', 'datetime']
    
    def detect(self, 
              data: pd.DataFrame, 
              columns: List[str],
              context: Optional[PatternContext] = None) -> List[Pattern]:
        """Detect time series patterns in specified columns"""
        
        if not self.validate_data(data, columns):
            return []
            
        patterns = []
        
        # Ensure data is sorted by time index if datetime index exists
        if isinstance(data.index, pd.DatetimeIndex):
            data = data.sort_index()
        
        for col in columns:
            if col not in data.columns:
                continue
                
            series = data[col].dropna()
            
            if len(series) < self.min_periods:
                continue
            
            # Only analyze numeric columns
            if pd.api.types.is_numeric_dtype(series):
                # Trend detection
                trend_pattern = self._detect_trend(series, col)
                if trend_pattern:
                    patterns.append(trend_pattern)
                
                # Seasonality detection
                if isinstance(series.index, pd.DatetimeIndex):
                    seasonal_patterns = self._detect_seasonality(series, col)
                    patterns.extend(seasonal_patterns)
                
                # Stationarity analysis
                stationarity_pattern = self._detect_stationarity(series, col)
                if stationarity_pattern:
                    patterns.append(stationarity_pattern)
                
                # Autocorrelation patterns
                autocorr_pattern = self._detect_autocorrelation(series, col)
                if autocorr_pattern:
                    patterns.append(autocorr_pattern)
                    
                # Change point detection
                change_patterns = self._detect_change_points(series, col)
                patterns.extend(change_patterns)
                
        return patterns
    
    def _detect_trend(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect linear or exponential trends"""
        
        # Prepare data for trend analysis
        x = np.arange(len(series))
        y = series.values
        
        # Linear regression
        slope, intercept, r_value, p_value, std_err = linregress(x, y)
        
        # Calculate trend strength
        trend_strength = abs(r_value)
        
        # Check if trend is significant
        if p_value > 0.05 or trend_strength < self.trend_threshold:
            return None
        
        # Determine trend direction and type
        if slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # Check for exponential trend
        try:
            log_y = np.log(y[y > 0])  # Only positive values
            if len(log_y) > self.min_periods * 0.8:
                log_x = x[:len(log_y)]
                exp_slope, _, exp_r_value, exp_p_value, _ = linregress(log_x, log_y)
                
                if abs(exp_r_value) > abs(r_value) and exp_p_value < 0.05:
                    pattern_type = PatternType.TREND_EXPONENTIAL
                    description = f"{col_name} shows {direction} exponential trend"
                    growth_rate = (np.exp(exp_slope) - 1) * 100
                    
                    parameters = {
                        'trend_type': 'exponential',
                        'growth_rate_percent': growth_rate,
                        'r_squared': exp_r_value ** 2,
                        'p_value': exp_p_value
                    }
                else:
                    pattern_type = PatternType.TREND_LINEAR
                    description = f"{col_name} shows {direction} linear trend"
                    parameters = {
                        'trend_type': 'linear',
                        'slope': float(slope),
                        'intercept': float(intercept),
                        'r_squared': r_value ** 2,
                        'p_value': p_value
                    }
            else:
                pattern_type = PatternType.TREND_LINEAR
                description = f"{col_name} shows {direction} linear trend"
                parameters = {
                    'trend_type': 'linear',
                    'slope': float(slope),
                    'intercept': float(intercept),
                    'r_squared': r_value ** 2,
                    'p_value': p_value
                }
        except:
            pattern_type = PatternType.TREND_LINEAR
            description = f"{col_name} shows {direction} linear trend"
            parameters = {
                'trend_type': 'linear',
                'slope': float(slope),
                'intercept': float(intercept),
                'r_squared': r_value ** 2,
                'p_value': p_value
            }
        
        # Calculate trend impact
        y_range = y.max() - y.min()
        trend_impact = abs(slope * len(y)) / y_range if y_range > 0 else 0
        
        evidence = [
            PatternEvidence(
                description=f"Statistical significance: p-value = {p_value:.4f}",
                statistical_tests={'p_value': p_value, 'r_squared': r_value ** 2}
            ),
            PatternEvidence(
                description=f"Trend accounts for {trend_impact:.1%} of value range",
                statistical_tests={'trend_impact': trend_impact}
            )
        ]
        
        return Pattern(
            type=pattern_type,
            confidence=min(0.95, trend_strength),
            description=description,
            column=col_name,
            parameters=parameters,
            evidence=evidence,
            impact="high" if trend_impact > 0.5 else "medium",
            recommendations=self._generate_trend_recommendations(direction, pattern_type, col_name),
            visual_hints={
                'chart_type': 'line_chart',
                'overlay': 'trend_line',
                'show_confidence_interval': True
            }
        )
    
    def _detect_seasonality(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect seasonal patterns using multiple methods"""
        patterns = []
        
        # Determine frequency
        if hasattr(series.index, 'freq') and series.index.freq:
            freq = series.index.freq
        else:
            # Try to infer frequency
            freq = pd.infer_freq(series.index)
        
        if not freq:
            return patterns
        
        # Determine period based on frequency
        freq_str = str(freq)
        if 'D' in freq_str:
            periods_to_test = [7, 30, 365]  # Weekly, monthly, yearly
        elif 'H' in freq_str:
            periods_to_test = [24, 168]  # Daily, weekly
        elif 'T' in freq_str or 'min' in freq_str:
            periods_to_test = [60, 1440]  # Hourly, daily
        else:
            periods_to_test = [12, 52]  # Monthly, yearly for unknown
        
        for period in periods_to_test:
            if len(series) < period * 2:
                continue
                
            try:
                # Seasonal decomposition
                decomposition = seasonal_decompose(
                    series, 
                    model='additive', 
                    period=period,
                    extrapolate_trend='freq'
                )
                
                seasonal_component = decomposition.seasonal
                
                # Calculate seasonality strength
                var_seasonal = seasonal_component.var()
                var_total = series.var()
                seasonality_strength = var_seasonal / var_total if var_total > 0 else 0
                
                if seasonality_strength > self.seasonality_threshold:
                    # Determine seasonality type
                    if period == 7:
                        season_type = "weekly"
                    elif period == 24:
                        season_type = "daily"
                    elif period == 30:
                        season_type = "monthly"
                    elif period == 365:
                        season_type = "yearly"
                    else:
                        season_type = f"{period}-period"
                    
                    # Find peak and trough days/hours
                    seasonal_avg = seasonal_component[:period].values
                    peak_idx = np.argmax(seasonal_avg)
                    trough_idx = np.argmin(seasonal_avg)
                    
                    evidence = [
                        PatternEvidence(
                            description=f"Seasonality accounts for {seasonality_strength:.1%} of variance",
                            statistical_tests={'seasonality_strength': seasonality_strength}
                        ),
                        PatternEvidence(
                            description=f"Peak at position {peak_idx}, trough at position {trough_idx}",
                            data_points=[
                                {'position': int(peak_idx), 'type': 'peak', 'value': float(seasonal_avg[peak_idx])},
                                {'position': int(trough_idx), 'type': 'trough', 'value': float(seasonal_avg[trough_idx])}
                            ]
                        )
                    ]
                    
                    pattern = Pattern(
                        type=PatternType.SEASONAL,
                        confidence=min(0.95, seasonality_strength * 2),
                        description=f"{col_name} shows {season_type} seasonality",
                        column=col_name,
                        parameters={
                            'period': period,
                            'seasonality_type': season_type,
                            'seasonality_strength': float(seasonality_strength),
                            'peak_position': int(peak_idx),
                            'trough_position': int(trough_idx),
                            'amplitude': float(seasonal_avg.max() - seasonal_avg.min())
                        },
                        evidence=evidence,
                        impact="high" if seasonality_strength > 0.3 else "medium",
                        recommendations=[
                            f"Account for {season_type} seasonality in forecasting",
                            f"Peak activity at position {peak_idx} of {period}",
                            "Consider seasonal adjustments for fair comparisons"
                        ],
                        visual_hints={
                            'chart_type': 'line_chart',
                            'show_decomposition': True,
                            'highlight_period': period
                        }
                    )
                    
                    patterns.append(pattern)
                    
            except Exception as e:
                # Decomposition failed for this period
                continue
                
        return patterns
    
    def _detect_stationarity(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Test for stationarity using ADF and KPSS tests"""
        
        try:
            # Augmented Dickey-Fuller test
            adf_result = adfuller(series, autolag='AIC')
            adf_statistic = adf_result[0]
            adf_pvalue = adf_result[1]
            adf_critical = adf_result[4]
            
            # KPSS test
            kpss_result = kpss(series, regression='c', nlags='auto')
            kpss_statistic = kpss_result[0]
            kpss_pvalue = kpss_result[1]
            kpss_critical = kpss_result[3]
            
            # Interpret results
            is_stationary_adf = adf_pvalue < 0.05
            is_stationary_kpss = kpss_pvalue > 0.05
            
            if is_stationary_adf and is_stationary_kpss:
                stationarity = "stationary"
                confidence = 0.9
                recommendations = [
                    f"{col_name} is stationary - suitable for many time series models",
                    "Can use ARIMA models without differencing",
                    "Statistical properties are consistent over time"
                ]
            elif not is_stationary_adf and not is_stationary_kpss:
                stationarity = "non-stationary"
                confidence = 0.9
                recommendations = [
                    f"{col_name} is non-stationary - consider differencing",
                    "May need transformation before modeling",
                    "Check for trends or structural breaks"
                ]
            else:
                stationarity = "uncertain"
                confidence = 0.5
                recommendations = [
                    f"Stationarity of {col_name} is unclear",
                    "Consider visual inspection and domain knowledge",
                    "May have complex patterns"
                ]
            
            if stationarity != "uncertain":
                evidence = [
                    PatternEvidence(
                        description=f"ADF test: statistic={adf_statistic:.4f}, p-value={adf_pvalue:.4f}",
                        statistical_tests={'adf_statistic': adf_statistic, 'adf_pvalue': adf_pvalue}
                    ),
                    PatternEvidence(
                        description=f"KPSS test: statistic={kpss_statistic:.4f}, p-value={kpss_pvalue:.4f}",
                        statistical_tests={'kpss_statistic': kpss_statistic, 'kpss_pvalue': kpss_pvalue}
                    )
                ]
                
                pattern_type = PatternType.TREND_LINEAR if stationarity == "non-stationary" else PatternType.NORMAL_DISTRIBUTION
                
                return Pattern(
                    type=pattern_type,
                    confidence=confidence,
                    description=f"{col_name} is {stationarity}",
                    column=col_name,
                    parameters={
                        'stationarity': stationarity,
                        'adf_pvalue': float(adf_pvalue),
                        'kpss_pvalue': float(kpss_pvalue)
                    },
                    evidence=evidence,
                    impact="medium",
                    recommendations=recommendations
                )
                
        except Exception:
            # Tests failed
            pass
            
        return None
    
    def _detect_autocorrelation(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect autocorrelation patterns"""
        
        try:
            # Ljung-Box test for autocorrelation
            lb_result = acorr_ljungbox(series, lags=min(40, len(series)//4), return_df=True)
            
            # Find significant lags
            significant_lags = lb_result[lb_result['lb_pvalue'] < 0.05].index.tolist()
            
            if len(significant_lags) > 0:
                # Calculate ACF values for significant lags
                from statsmodels.tsa.stattools import acf
                acf_values = acf(series, nlags=max(significant_lags))
                
                # Find the most significant lags
                lag_acf_pairs = [(lag, acf_values[lag]) for lag in significant_lags[:5]]
                lag_acf_pairs.sort(key=lambda x: abs(x[1]), reverse=True)
                
                evidence = [
                    PatternEvidence(
                        description=f"Significant autocorrelation at {len(significant_lags)} lags",
                        statistical_tests={
                            f'lag_{lag}': float(lb_result.loc[lag, 'lb_pvalue']) 
                            for lag in significant_lags[:5]
                        }
                    ),
                    PatternEvidence(
                        description=f"Strongest correlation at lag {lag_acf_pairs[0][0]} (r={lag_acf_pairs[0][1]:.3f})",
                        data_points=[
                            {'lag': lag, 'acf': float(acf)} 
                            for lag, acf in lag_acf_pairs
                        ]
                    )
                ]
                
                # Determine pattern interpretation
                if 1 in significant_lags[:3]:
                    pattern_desc = "strong temporal dependence"
                    recommendations = [
                        "Consider autoregressive (AR) models",
                        "Previous values strongly predict future values",
                        "May need to account for momentum"
                    ]
                elif any(lag % 7 == 0 for lag in significant_lags[:5] if lag > 0):
                    pattern_desc = "weekly autocorrelation pattern"
                    recommendations = [
                        "Weekly patterns detected in autocorrelation",
                        "Consider seasonal ARIMA models",
                        "Day-of-week effects may be important"
                    ]
                else:
                    pattern_desc = "complex autocorrelation structure"
                    recommendations = [
                        "Complex temporal dependencies detected",
                        "Consider ARIMA or state-space models",
                        "May benefit from advanced time series methods"
                    ]
                
                return Pattern(
                    type=PatternType.CYCLIC,
                    confidence=min(0.9, len(significant_lags) / 10),
                    description=f"{col_name} shows {pattern_desc}",
                    column=col_name,
                    parameters={
                        'significant_lags': significant_lags[:10],
                        'max_lag_tested': int(len(lb_result)),
                        'strongest_lag': int(lag_acf_pairs[0][0]),
                        'strongest_acf': float(lag_acf_pairs[0][1])
                    },
                    evidence=evidence,
                    impact="medium",
                    recommendations=recommendations,
                    visual_hints={
                        'chart_type': 'acf_plot',
                        'max_lags': max(significant_lags[:10]) + 5
                    }
                )
                
        except Exception:
            pass
            
        return None
    
    def _detect_change_points(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect significant changes in time series behavior"""
        patterns = []
        
        try:
            # Simple change point detection using rolling statistics
            window = max(10, len(series) // 20)
            
            # Rolling mean and std
            rolling_mean = series.rolling(window=window, center=True).mean()
            rolling_std = series.rolling(window=window, center=True).std()
            
            # Detect changes in mean
            mean_diff = rolling_mean.diff().abs()
            mean_threshold = mean_diff.std() * 2
            
            change_points = []
            
            for i in range(window, len(series) - window):
                if mean_diff.iloc[i] > mean_threshold:
                    # Verify this is a sustained change
                    before_mean = series.iloc[i-window:i].mean()
                    after_mean = series.iloc[i:i+window].mean()
                    
                    change_magnitude = abs(after_mean - before_mean)
                    relative_change = change_magnitude / abs(before_mean) if before_mean != 0 else float('inf')
                    
                    if relative_change > 0.2:  # 20% change
                        change_points.append({
                            'index': i,
                            'timestamp': series.index[i] if hasattr(series.index[i], 'isoformat') else i,
                            'before_mean': float(before_mean),
                            'after_mean': float(after_mean),
                            'change_magnitude': float(change_magnitude),
                            'relative_change': float(relative_change)
                        })
            
            if change_points:
                # Limit to most significant change points
                change_points = sorted(change_points, key=lambda x: x['relative_change'], reverse=True)[:3]
                
                for cp in change_points:
                    evidence = [
                        PatternEvidence(
                            description=f"Mean changed from {cp['before_mean']:.2f} to {cp['after_mean']:.2f}",
                            data_points=[cp]
                        ),
                        PatternEvidence(
                            description=f"Relative change: {cp['relative_change']:.1%}",
                            statistical_tests={'relative_change': cp['relative_change']}
                        )
                    ]
                    
                    pattern = Pattern(
                        type=PatternType.CHANGE_POINT,
                        confidence=min(0.9, cp['relative_change']),
                        description=f"Significant change detected in {col_name} at index {cp['index']}",
                        column=col_name,
                        parameters=cp,
                        evidence=evidence,
                        impact="high" if cp['relative_change'] > 0.5 else "medium",
                        recommendations=[
                            f"Investigate what happened around {cp['timestamp']}",
                            "Consider separate models before/after change point",
                            "May indicate system change or external event"
                        ],
                        visual_hints={
                            'chart_type': 'line_chart',
                            'highlight_points': [cp['index']],
                            'show_change_annotation': True
                        }
                    )
                    
                    patterns.append(pattern)
                    
        except Exception:
            pass
            
        return patterns
    
    def _generate_trend_recommendations(self, 
                                      direction: str, 
                                      pattern_type: PatternType,
                                      col_name: str) -> List[str]:
        """Generate recommendations based on trend type"""
        
        base_recs = [
            f"Monitor {direction} trend in {col_name}",
            "Consider trend-adjusted analysis",
            "Set up alerts for trend reversals"
        ]
        
        if pattern_type == PatternType.TREND_EXPONENTIAL:
            base_recs.extend([
                "Exponential growth/decay detected - may not be sustainable",
                "Consider log transformation for analysis",
                "Review capacity or limits that might affect trend"
            ])
        
        if direction == "increasing":
            base_recs.append("Investigate drivers of growth")
        else:
            base_recs.append("Investigate causes of decline")
            
        return base_recs