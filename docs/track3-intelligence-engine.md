# Track 3: Intelligence Engine - Ultra Detailed Implementation

## Overview
The Intelligence Engine is the brain of UDS - implementing ML-enhanced pattern detection, intelligent query generation, and visualization recommendations. This track starts with Python for rapid ML prototyping, then provides Go interfaces for production integration.

## Architecture

```python
# intelligence/architecture.py
"""
Intelligence Engine Architecture:

┌─────────────────────────────────────────────────────────────────┐
│                      Intelligence Engine                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Pattern Detection Layer                 │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ Statistical │  │ Time Series  │  │   Anomaly     │  │   │
│  │  │  Analyzer   │  │  Analyzer    │  │  Detector     │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │Distribution │  │ Correlation  │  │   Custom ML   │  │   │
│  │  │  Analyzer   │  │   Engine     │  │   Models      │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                Query Generation Layer                    │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │Intent Parser │  │Query Builder  │  │  Optimizer   │ │   │
│  │  │     (NLP)    │  │  (Templates)  │  │   Engine     │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Visualization Intelligence                  │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │ Data Shape   │  │ Visualization │  │  Layout      │ │   │
│  │  │  Analyzer    │  │  Recommender  │  │  Optimizer   │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    ML Model Registry                     │   │
│  │  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │   │
│  │  │Pre-trained   │  │  Fine-tuned   │  │   Custom     │ │   │
│  │  │   Models     │  │    Models     │  │   Models     │ │   │
│  │  └──────────────┘  └───────────────┘  └──────────────┘ │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
"""
```

## Week 1: Pattern Detection Foundation

### Day 1-2: Core Pattern Detection Framework

```python
# intelligence/patterns/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from enum import Enum

class PatternType(Enum):
    TREND = "trend"
    SEASONAL = "seasonal"
    CYCLIC = "cyclic"
    ANOMALY = "anomaly"
    DISTRIBUTION = "distribution"
    CORRELATION = "correlation"
    CHANGE_POINT = "change_point"
    CLUSTERING = "clustering"
    SEQUENCE = "sequence"
    MISSING = "missing_data"

@dataclass
class Pattern:
    type: PatternType
    confidence: float  # 0.0 to 1.0
    description: str
    parameters: Dict[str, Any]
    evidence: List[Dict[str, Any]]
    visual_hints: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "confidence": self.confidence,
            "description": self.description,
            "parameters": self.parameters,
            "evidence": self.evidence,
            "visual_hints": self.visual_hints
        }

class PatternDetector(ABC):
    """Base class for all pattern detectors"""
    
    @abstractmethod
    def detect(self, data: pd.DataFrame, columns: List[str]) -> List[Pattern]:
        """Detect patterns in the specified columns"""
        pass
    
    @abstractmethod
    def get_required_data_type(self) -> List[str]:
        """Return data types this detector can handle"""
        pass

# intelligence/patterns/statistical.py
import scipy.stats as stats
from sklearn.preprocessing import StandardScaler
import warnings

class StatisticalPatternDetector(PatternDetector):
    """Detects statistical patterns in data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_samples = self.config.get('min_samples', 30)
        
    def detect(self, data: pd.DataFrame, columns: List[str]) -> List[Pattern]:
        patterns = []
        
        for col in columns:
            if col not in data.columns:
                continue
                
            series = data[col].dropna()
            
            if len(series) < self.min_samples:
                continue
            
            # Check data type
            if pd.api.types.is_numeric_dtype(series):
                patterns.extend(self._detect_numeric_patterns(series, col))
            elif pd.api.types.is_string_dtype(series):
                patterns.extend(self._detect_categorical_patterns(series, col))
            elif pd.api.types.is_datetime64_any_dtype(series):
                patterns.extend(self._detect_temporal_patterns(series, col))
                
        return patterns
    
    def _detect_numeric_patterns(self, series: pd.Series, col_name: str) -> List[Pattern]:
        patterns = []
        
        # Distribution detection
        distribution_pattern = self._detect_distribution(series, col_name)
        if distribution_pattern:
            patterns.append(distribution_pattern)
        
        # Outlier detection
        outlier_patterns = self._detect_outliers(series, col_name)
        patterns.extend(outlier_patterns)
        
        # Trend detection
        if len(series) > 50:  # Need enough data for trend
            trend_pattern = self._detect_trend(series, col_name)
            if trend_pattern:
                patterns.append(trend_pattern)
        
        return patterns
    
    def _detect_distribution(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect the distribution type of numeric data"""
        
        # Standardize the data
        data_std = StandardScaler().fit_transform(series.values.reshape(-1, 1)).flatten()
        
        # Test for normality
        _, p_normal = stats.normaltest(data_std)
        
        # Test for other distributions
        distributions = {
            'normal': (stats.norm, p_normal),
            'exponential': (stats.expon, None),
            'uniform': (stats.uniform, None),
            'lognormal': (stats.lognorm, None),
            'powerlaw': (stats.powerlaw, None)
        }
        
        best_dist = None
        best_score = -np.inf
        
        for dist_name, (dist_func, p_value) in distributions.items():
            if dist_name == 'normal' and p_value is not None:
                # Use pre-calculated p-value for normal
                score = p_value
            else:
                # Fit distribution and calculate goodness of fit
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    try:
                        params = dist_func.fit(data_std)
                        # Kolmogorov-Smirnov test
                        _, p_value = stats.kstest(data_std, dist_func.cdf, args=params)
                        score = p_value
                    except:
                        score = 0
            
            if score > best_score:
                best_score = score
                best_dist = dist_name
        
        if best_score > 0.05:  # 5% significance level
            return Pattern(
                type=PatternType.DISTRIBUTION,
                confidence=min(best_score, 0.99),
                description=f"{col_name} follows {best_dist} distribution",
                parameters={
                    "distribution": best_dist,
                    "goodness_of_fit": best_score,
                    "mean": float(series.mean()),
                    "std": float(series.std()),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurtosis())
                },
                evidence=[{
                    "test": "distribution_fit",
                    "p_value": best_score,
                    "distribution": best_dist
                }],
                visual_hints={
                    "recommended_chart": "histogram_with_distribution",
                    "distribution_overlay": best_dist
                }
            )
        
        return None
    
    def _detect_outliers(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect outliers using multiple methods"""
        patterns = []
        
        # Method 1: IQR method
        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outliers_iqr = series[(series < lower_bound) | (series > upper_bound)]
        
        if len(outliers_iqr) > 0:
            outlier_ratio = len(outliers_iqr) / len(series)
            
            if outlier_ratio > 0.001:  # More than 0.1% outliers
                patterns.append(Pattern(
                    type=PatternType.ANOMALY,
                    confidence=min(0.9, outlier_ratio * 10),  # Scale confidence
                    description=f"{col_name} contains {len(outliers_iqr)} outliers ({outlier_ratio:.1%})",
                    parameters={
                        "method": "IQR",
                        "outlier_count": len(outliers_iqr),
                        "outlier_ratio": outlier_ratio,
                        "lower_bound": lower_bound,
                        "upper_bound": upper_bound,
                        "outlier_values": outliers_iqr.tolist()[:10]  # First 10
                    },
                    evidence=[{
                        "method": "IQR",
                        "Q1": Q1,
                        "Q3": Q3,
                        "IQR": IQR
                    }],
                    visual_hints={
                        "highlight_outliers": True,
                        "show_bounds": True
                    }
                ))
        
        # Method 2: Z-score method
        z_scores = np.abs(stats.zscore(series))
        outliers_z = series[z_scores > 3]
        
        if len(outliers_z) > 0 and len(outliers_z) != len(outliers_iqr):
            patterns.append(Pattern(
                type=PatternType.ANOMALY,
                confidence=0.85,
                description=f"{col_name} has {len(outliers_z)} extreme values (|z-score| > 3)",
                parameters={
                    "method": "z-score",
                    "outlier_count": len(outliers_z),
                    "threshold": 3
                },
                evidence=[{
                    "method": "z-score",
                    "threshold": 3
                }]
            ))
        
        return patterns
    
    def get_required_data_type(self) -> List[str]:
        return ["numeric", "string", "datetime"]

# intelligence/patterns/timeseries.py
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller, acf, pacf
import ruptures as rpt
from scipy import signal
from scipy.fft import fft, fftfreq

class TimeSeriesPatternDetector(PatternDetector):
    """Detects patterns specific to time series data"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_periods = self.config.get('min_periods', 50)
        
    def detect(self, data: pd.DataFrame, columns: List[str]) -> List[Pattern]:
        patterns = []
        
        # Ensure we have a time index
        if not isinstance(data.index, pd.DatetimeIndex):
            return patterns
        
        # Check if data is evenly spaced
        freq = pd.infer_freq(data.index)
        if not freq:
            patterns.append(self._irregular_sampling_pattern(data))
            return patterns
        
        for col in columns:
            if col not in data.columns:
                continue
                
            series = data[col].dropna()
            
            if len(series) < self.min_periods:
                continue
                
            if pd.api.types.is_numeric_dtype(series):
                # Trend detection
                trend_pattern = self._detect_trend(series, col)
                if trend_pattern:
                    patterns.append(trend_pattern)
                
                # Seasonality detection
                seasonal_patterns = self._detect_seasonality(series, col, freq)
                patterns.extend(seasonal_patterns)
                
                # Change point detection
                change_points = self._detect_change_points(series, col)
                patterns.extend(change_points)
                
                # Stationarity test
                stationarity = self._test_stationarity(series, col)
                if stationarity:
                    patterns.append(stationarity)
                    
        return patterns
    
    def _detect_trend(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Detect trend using multiple methods"""
        
        # Method 1: Linear regression
        x = np.arange(len(series))
        y = series.values
        
        # Fit linear model
        z = np.polyfit(x, y, 1)
        slope = z[0]
        
        # Calculate R-squared
        p = np.poly1d(z)
        yhat = p(x)
        ybar = np.mean(y)
        ssreg = np.sum((yhat - ybar)**2)
        sstot = np.sum((y - ybar)**2)
        r_squared = ssreg / sstot if sstot > 0 else 0
        
        if abs(r_squared) > 0.3:  # Moderate to strong linear trend
            # Determine trend direction and strength
            if slope > 0:
                direction = "increasing"
            else:
                direction = "decreasing"
                
            # Calculate percentage change
            pct_change = (series.iloc[-1] - series.iloc[0]) / series.iloc[0] * 100
            
            return Pattern(
                type=PatternType.TREND,
                confidence=min(abs(r_squared), 0.95),
                description=f"{col_name} shows {direction} trend ({pct_change:.1f}% change)",
                parameters={
                    "direction": direction,
                    "slope": float(slope),
                    "r_squared": float(r_squared),
                    "start_value": float(series.iloc[0]),
                    "end_value": float(series.iloc[-1]),
                    "percentage_change": float(pct_change)
                },
                evidence=[{
                    "method": "linear_regression",
                    "slope": float(slope),
                    "r_squared": float(r_squared)
                }],
                visual_hints={
                    "add_trend_line": True,
                    "trend_type": "linear"
                }
            )
        
        return None
    
    def _detect_seasonality(self, series: pd.Series, col_name: str, freq: str) -> List[Pattern]:
        """Detect seasonal patterns using decomposition and FFT"""
        patterns = []
        
        # Skip if too few periods
        if len(series) < self.min_periods * 2:
            return patterns
        
        # Method 1: Seasonal decomposition
        try:
            # Determine period based on frequency
            period_map = {
                'D': 7,      # Daily -> weekly seasonality
                'H': 24,     # Hourly -> daily seasonality  
                'T': 60*24,  # Minute -> daily seasonality
                'M': 12,     # Monthly -> yearly seasonality
                'W': 52,     # Weekly -> yearly seasonality
            }
            
            period = period_map.get(freq, 7)
            
            if len(series) >= period * 2:
                decomposition = seasonal_decompose(series, model='additive', period=period)
                
                # Calculate strength of seasonality
                seasonal_strength = np.var(decomposition.seasonal) / np.var(series)
                
                if seasonal_strength > 0.1:  # At least 10% of variance
                    patterns.append(Pattern(
                        type=PatternType.SEASONAL,
                        confidence=min(seasonal_strength * 2, 0.95),
                        description=f"{col_name} has {freq} seasonality with period {period}",
                        parameters={
                            "period": period,
                            "frequency": freq,
                            "seasonal_strength": float(seasonal_strength),
                            "model": "additive"
                        },
                        evidence=[{
                            "method": "seasonal_decompose",
                            "variance_explained": float(seasonal_strength)
                        }],
                        visual_hints={
                            "show_decomposition": True,
                            "highlight_seasons": True
                        }
                    ))
        except:
            pass
        
        # Method 2: FFT for complex seasonality
        try:
            # Remove trend first
            detrended = signal.detrend(series.values)
            
            # Compute FFT
            fft_vals = fft(detrended)
            fft_freq = fftfreq(len(detrended), d=1)  # Assuming unit spacing
            
            # Find peaks in frequency domain
            power = np.abs(fft_vals)**2
            peaks, properties = signal.find_peaks(power[:len(power)//2], 
                                                prominence=np.max(power)*0.1)
            
            if len(peaks) > 0:
                # Get top 3 frequencies
                top_peaks = peaks[np.argsort(power[peaks])[-3:]]
                
                for peak in top_peaks:
                    if fft_freq[peak] > 0:
                        period = int(1 / fft_freq[peak])
                        if 2 <= period <= len(series) // 2:
                            patterns.append(Pattern(
                                type=PatternType.CYCLIC,
                                confidence=0.8,
                                description=f"{col_name} has cyclic pattern with period ~{period}",
                                parameters={
                                    "period": period,
                                    "frequency": float(fft_freq[peak]),
                                    "power": float(power[peak])
                                },
                                evidence=[{
                                    "method": "FFT",
                                    "peak_frequency": float(fft_freq[peak])
                                }]
                            ))
        except:
            pass
        
        return patterns
    
    def _detect_change_points(self, series: pd.Series, col_name: str) -> List[Pattern]:
        """Detect significant changes in time series behavior"""
        patterns = []
        
        try:
            # Use ruptures for change point detection
            signal = series.values
            
            # Pelt method for unknown number of change points
            algo = rpt.Pelt(model="rbf").fit(signal)
            change_points = algo.predict(pen=10)
            
            if len(change_points) > 1:  # Exclude the last point (end of series)
                for i, cp in enumerate(change_points[:-1]):
                    # Calculate statistics before and after change point
                    before = series.iloc[:cp]
                    after = series.iloc[cp:]
                    
                    mean_change = (after.mean() - before.mean()) / before.mean() * 100
                    std_change = (after.std() - before.std()) / before.std() * 100
                    
                    patterns.append(Pattern(
                        type=PatternType.CHANGE_POINT,
                        confidence=0.85,
                        description=f"Significant change in {col_name} at position {cp}",
                        parameters={
                            "change_point_index": int(cp),
                            "change_point_time": str(series.index[cp]),
                            "mean_change_pct": float(mean_change),
                            "std_change_pct": float(std_change),
                            "before_mean": float(before.mean()),
                            "after_mean": float(after.mean())
                        },
                        evidence=[{
                            "method": "PELT",
                            "penalty": 10
                        }],
                        visual_hints={
                            "mark_change_points": True,
                            "show_segments": True
                        }
                    ))
        except:
            pass
        
        return patterns
    
    def _test_stationarity(self, series: pd.Series, col_name: str) -> Optional[Pattern]:
        """Test if time series is stationary"""
        
        # Augmented Dickey-Fuller test
        result = adfuller(series.dropna())
        
        adf_statistic = result[0]
        p_value = result[1]
        critical_values = result[4]
        
        is_stationary = p_value < 0.05
        
        if not is_stationary:
            return Pattern(
                type=PatternType.TREND,
                confidence=0.9,
                description=f"{col_name} is non-stationary (requires differencing)",
                parameters={
                    "stationary": False,
                    "adf_statistic": float(adf_statistic),
                    "p_value": float(p_value),
                    "recommendation": "Consider differencing or detrending"
                },
                evidence=[{
                    "test": "Augmented Dickey-Fuller",
                    "p_value": float(p_value)
                }]
            )
        
        return None
    
    def get_required_data_type(self) -> List[str]:
        return ["numeric"]
```

### Day 3-4: Anomaly Detection

```python
# intelligence/patterns/anomaly.py
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import DBSCAN
import numpy as np

class AnomalyDetector(PatternDetector):
    """Advanced anomaly detection using ensemble methods"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.contamination = self.config.get('contamination', 0.1)
        self.use_ensemble = self.config.get('use_ensemble', True)
        
    def detect(self, data: pd.DataFrame, columns: List[str]) -> List[Pattern]:
        patterns = []
        
        # Get numeric columns
        numeric_cols = [col for col in columns if col in data.columns 
                       and pd.api.types.is_numeric_dtype(data[col])]
        
        if not numeric_cols:
            return patterns
        
        # Single column anomalies
        for col in numeric_cols:
            col_patterns = self._detect_univariate_anomalies(data[[col]], col)
            patterns.extend(col_patterns)
        
        # Multi-column anomalies
        if len(numeric_cols) > 1:
            multi_patterns = self._detect_multivariate_anomalies(
                data[numeric_cols], numeric_cols
            )
            patterns.extend(multi_patterns)
        
        return patterns
    
    def _detect_univariate_anomalies(self, data: pd.DataFrame, col_name: str) -> List[Pattern]:
        """Detect anomalies in a single column"""
        patterns = []
        
        # Prepare data
        X = data.dropna().values.reshape(-1, 1)
        if len(X) < 10:
            return patterns
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # Ensemble of methods
        anomaly_scores = np.zeros(len(X))
        methods_used = []
        
        # Method 1: Isolation Forest
        try:
            iso_forest = IsolationForest(
                contamination=self.contamination,
                random_state=42
            )
            iso_predictions = iso_forest.fit_predict(X_scaled)
            iso_scores = iso_forest.score_samples(X_scaled)
            
            # Convert to anomaly probability
            anomaly_scores += (1 - (iso_scores - iso_scores.min()) / 
                             (iso_scores.max() - iso_scores.min()))
            methods_used.append("Isolation Forest")
        except:
            pass
        
        # Method 2: Local Outlier Factor
        try:
            lof = LocalOutlierFactor(
                contamination=self.contamination,
                novelty=False
            )
            lof_predictions = lof.fit_predict(X_scaled)
            lof_scores = lof.negative_outlier_factor_
            
            # Convert to anomaly probability
            anomaly_scores += (1 - (lof_scores - lof_scores.min()) / 
                             (lof_scores.max() - lof_scores.min()))
            methods_used.append("Local Outlier Factor")
        except:
            pass
        
        # Method 3: Statistical methods
        z_scores = np.abs(stats.zscore(X_scaled.flatten()))
        anomaly_scores += z_scores / z_scores.max()
        methods_used.append("Z-score")
        
        # Average scores
        if methods_used:
            anomaly_scores /= len(methods_used)
            
            # Find anomalies (top contamination %)
            threshold = np.percentile(anomaly_scores, (1 - self.contamination) * 100)
            anomaly_indices = np.where(anomaly_scores > threshold)[0]
            
            if len(anomaly_indices) > 0:
                anomaly_values = X[anomaly_indices].flatten()
                
                patterns.append(Pattern(
                    type=PatternType.ANOMALY,
                    confidence=0.85,
                    description=f"{col_name} contains {len(anomaly_indices)} anomalies",
                    parameters={
                        "anomaly_count": int(len(anomaly_indices)),
                        "anomaly_ratio": float(len(anomaly_indices) / len(X)),
                        "methods": methods_used,
                        "threshold": float(threshold),
                        "anomaly_indices": anomaly_indices.tolist(),
                        "anomaly_values": anomaly_values.tolist()[:20],  # First 20
                        "anomaly_scores": anomaly_scores[anomaly_indices].tolist()[:20]
                    },
                    evidence=[{
                        "ensemble_methods": methods_used,
                        "contamination": self.contamination
                    }],
                    visual_hints={
                        "highlight_anomalies": True,
                        "show_anomaly_scores": True,
                        "color_by_score": True
                    }
                ))
        
        return patterns
    
    def _detect_multivariate_anomalies(self, data: pd.DataFrame, col_names: List[str]) -> List[Pattern]:
        """Detect anomalies across multiple columns"""
        patterns = []
        
        # Prepare data
        X = data.dropna()
        if len(X) < 20 or len(col_names) < 2:
            return patterns
        
        # Scale data
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # DBSCAN for clustering-based anomaly detection
        try:
            dbscan = DBSCAN(eps=0.5, min_samples=5)
            clusters = dbscan.fit_predict(X_scaled)
            
            # Points labeled as -1 are anomalies
            anomaly_mask = clusters == -1
            anomaly_count = np.sum(anomaly_mask)
            
            if anomaly_count > 0:
                anomaly_indices = np.where(anomaly_mask)[0]
                
                # Calculate which features contribute most to anomalies
                normal_data = X_scaled[~anomaly_mask]
                anomaly_data = X_scaled[anomaly_mask]
                
                if len(normal_data) > 0:
                    feature_importance = []
                    for i, col in enumerate(col_names):
                        normal_std = normal_data[:, i].std()
                        anomaly_mean_deviation = np.abs(
                            anomaly_data[:, i].mean() - normal_data[:, i].mean()
                        )
                        importance = anomaly_mean_deviation / (normal_std + 1e-6)
                        feature_importance.append((col, importance))
                    
                    feature_importance.sort(key=lambda x: x[1], reverse=True)
                    
                    patterns.append(Pattern(
                        type=PatternType.ANOMALY,
                        confidence=0.8,
                        description=f"Multivariate anomalies detected across {', '.join(col_names)}",
                        parameters={
                            "anomaly_count": int(anomaly_count),
                            "anomaly_ratio": float(anomaly_count / len(X)),
                            "method": "DBSCAN clustering",
                            "feature_importance": feature_importance[:5],  # Top 5
                            "anomaly_indices": anomaly_indices.tolist()[:20]
                        },
                        evidence=[{
                            "method": "DBSCAN",
                            "eps": 0.5,
                            "min_samples": 5
                        }],
                        visual_hints={
                            "plot_type": "scatter_matrix",
                            "highlight_anomalies": True,
                            "color_by_cluster": True
                        }
                    ))
        except:
            pass
        
        return patterns
    
    def get_required_data_type(self) -> List[str]:
        return ["numeric"]

# intelligence/patterns/correlation.py
from scipy.stats import pearsonr, spearmanr, kendalltau
from sklearn.feature_selection import mutual_info_regression
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from itertools import combinations

class CorrelationDetector(PatternDetector):
    """Detects correlations and relationships between variables"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.min_correlation = self.config.get('min_correlation', 0.5)
        self.significance_level = self.config.get('significance_level', 0.05)
        
    def detect(self, data: pd.DataFrame, columns: List[str]) -> List[Pattern]:
        patterns = []
        
        # Get numeric columns
        numeric_cols = [col for col in columns if col in data.columns 
                       and pd.api.types.is_numeric_dtype(data[col])]
        
        # Need at least 2 columns for correlation
        if len(numeric_cols) < 2:
            return patterns
        
        # Pairwise correlations
        for col1, col2 in combinations(numeric_cols, 2):
            correlation_patterns = self._detect_correlation(data, col1, col2)
            patterns.extend(correlation_patterns)
        
        # Multivariate relationships
        if len(numeric_cols) > 2:
            multi_patterns = self._detect_multivariate_relationships(
                data[numeric_cols]
            )
            patterns.extend(multi_patterns)
        
        return patterns
    
    def _detect_correlation(self, data: pd.DataFrame, col1: str, col2: str) -> List[Pattern]:
        """Detect correlation between two columns"""
        patterns = []
        
        # Get clean data
        clean_data = data[[col1, col2]].dropna()
        if len(clean_data) < 30:
            return patterns
        
        x = clean_data[col1].values
        y = clean_data[col2].values
        
        # Pearson correlation (linear)
        pearson_r, pearson_p = pearsonr(x, y)
        
        # Spearman correlation (monotonic)
        spearman_r, spearman_p = spearmanr(x, y)
        
        # Determine strongest correlation
        if abs(pearson_r) > abs(spearman_r):
            correlation = pearson_r
            p_value = pearson_p
            method = "Pearson"
            relationship = "linear"
        else:
            correlation = spearman_r
            p_value = spearman_p
            method = "Spearman"
            relationship = "monotonic"
        
        # Check if significant
        if p_value < self.significance_level and abs(correlation) > self.min_correlation:
            # Determine strength and direction
            strength = "strong" if abs(correlation) > 0.7 else "moderate"
            direction = "positive" if correlation > 0 else "negative"
            
            # Calculate R-squared
            r_squared = correlation ** 2
            
            patterns.append(Pattern(
                type=PatternType.CORRELATION,
                confidence=min(abs(correlation), 0.95),
                description=f"{strength.capitalize()} {direction} {relationship} correlation between {col1} and {col2}",
                parameters={
                    "column1": col1,
                    "column2": col2,
                    "correlation": float(correlation),
                    "p_value": float(p_value),
                    "method": method,
                    "relationship_type": relationship,
                    "r_squared": float(r_squared),
                    "sample_size": len(clean_data)
                },
                evidence=[{
                    "test": f"{method} correlation",
                    "statistic": float(correlation),
                    "p_value": float(p_value)
                }],
                visual_hints={
                    "plot_type": "scatter",
                    "add_regression_line": True,
                    "show_correlation": True
                }
            ))
        
        # Check for non-linear relationships
        if abs(pearson_r) < 0.3 and abs(spearman_r) > 0.5:
            patterns.append(Pattern(
                type=PatternType.CORRELATION,
                confidence=0.7,
                description=f"Non-linear relationship detected between {col1} and {col2}",
                parameters={
                    "column1": col1,
                    "column2": col2,
                    "pearson_r": float(pearson_r),
                    "spearman_r": float(spearman_r),
                    "relationship_type": "non-linear"
                },
                evidence=[{
                    "observation": "Low linear correlation but high rank correlation"
                }],
                visual_hints={
                    "plot_type": "scatter",
                    "add_smoothing": True
                }
            ))
        
        return patterns
    
    def _detect_multivariate_relationships(self, data: pd.DataFrame) -> List[Pattern]:
        """Detect relationships among multiple variables"""
        patterns = []
        
        # Correlation matrix
        corr_matrix = data.corr()
        
        # Find clusters of correlated variables
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                corr_value = corr_matrix.iloc[i, j]
                if abs(corr_value) > self.min_correlation:
                    high_corr_pairs.append((
                        corr_matrix.columns[i],
                        corr_matrix.columns[j],
                        corr_value
                    ))
        
        # Group correlated variables
        if len(high_corr_pairs) > 2:
            # Simple clustering based on correlation
            groups = self._cluster_correlated_variables(high_corr_pairs)
            
            for group in groups:
                if len(group) > 2:
                    # Calculate average correlation within group
                    group_corrs = []
                    for v1, v2 in combinations(group, 2):
                        corr = corr_matrix.loc[v1, v2]
                        group_corrs.append(abs(corr))
                    
                    avg_corr = np.mean(group_corrs)
                    
                    patterns.append(Pattern(
                        type=PatternType.CORRELATION,
                        confidence=min(avg_corr, 0.9),
                        description=f"Correlated variable group: {', '.join(group)}",
                        parameters={
                            "variables": group,
                            "average_correlation": float(avg_corr),
                            "correlation_matrix": corr_matrix.loc[group, group].to_dict()
                        },
                        evidence=[{
                            "method": "correlation_clustering",
                            "threshold": self.min_correlation
                        }],
                        visual_hints={
                            "plot_type": "correlation_heatmap",
                            "variables": group
                        }
                    ))
        
        return patterns
    
    def _cluster_correlated_variables(self, high_corr_pairs: List[Tuple]) -> List[List[str]]:
        """Simple clustering of correlated variables"""
        # Create adjacency list
        graph = {}
        for v1, v2, _ in high_corr_pairs:
            if v1 not in graph:
                graph[v1] = set()
            if v2 not in graph:
                graph[v2] = set()
            graph[v1].add(v2)
            graph[v2].add(v1)
        
        # Find connected components
        visited = set()
        groups = []
        
        for node in graph:
            if node not in visited:
                group = []
                stack = [node]
                
                while stack:
                    current = stack.pop()
                    if current not in visited:
                        visited.add(current)
                        group.append(current)
                        stack.extend(graph[current] - visited)
                
                groups.append(group)
        
        return groups
    
    def get_required_data_type(self) -> List[str]:
        return ["numeric"]
```

### Day 5: Pattern Engine Integration

```python
# intelligence/patterns/engine.py
from typing import Dict, List, Type
import concurrent.futures
import json

class PatternEngine:
    """Main engine that orchestrates all pattern detectors"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.detectors: Dict[str, PatternDetector] = {}
        self._initialize_detectors()
        self.max_workers = self.config.get('max_workers', 4)
        
    def _initialize_detectors(self):
        """Initialize all available pattern detectors"""
        self.detectors['statistical'] = StatisticalPatternDetector(self.config)
        self.detectors['timeseries'] = TimeSeriesPatternDetector(self.config)
        self.detectors['anomaly'] = AnomalyDetector(self.config)
        self.detectors['correlation'] = CorrelationDetector(self.config)
        
        # Add custom detectors if configured
        custom_detectors = self.config.get('custom_detectors', [])
        for detector_config in custom_detectors:
            detector_class = detector_config['class']
            detector_name = detector_config['name']
            self.detectors[detector_name] = detector_class(detector_config.get('config', {}))
    
    def detect_patterns(
        self, 
        data: pd.DataFrame, 
        columns: Optional[List[str]] = None,
        pattern_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Detect all patterns in the data
        
        Args:
            data: DataFrame to analyze
            columns: Specific columns to analyze (None = all)
            pattern_types: Specific pattern types to detect (None = all)
            
        Returns:
            Dictionary with patterns, metadata, and recommendations
        """
        
        if columns is None:
            columns = data.columns.tolist()
        
        # Filter detectors based on requested pattern types
        active_detectors = self.detectors
        if pattern_types:
            active_detectors = {
                name: detector for name, detector in self.detectors.items()
                if any(pt in name for pt in pattern_types)
            }
        
        # Run detectors in parallel
        all_patterns = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_detector = {
                executor.submit(detector.detect, data, columns): name
                for name, detector in active_detectors.items()
            }
            
            for future in concurrent.futures.as_completed(future_to_detector):
                detector_name = future_to_detector[future]
                try:
                    patterns = future.result()
                    for pattern in patterns:
                        pattern.detector = detector_name
                    all_patterns.extend(patterns)
                except Exception as e:
                    print(f"Error in {detector_name}: {e}")
        
        # Post-process patterns
        all_patterns = self._deduplicate_patterns(all_patterns)
        all_patterns = self._rank_patterns(all_patterns)
        
        # Generate insights
        insights = self._generate_insights(all_patterns, data)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(all_patterns, data)
        
        return {
            "patterns": [p.to_dict() for p in all_patterns],
            "pattern_count": len(all_patterns),
            "pattern_types": list(set(p.type.value for p in all_patterns)),
            "insights": insights,
            "recommendations": recommendations,
            "metadata": {
                "rows_analyzed": len(data),
                "columns_analyzed": len(columns),
                "detectors_used": list(active_detectors.keys())
            }
        }
    
    def _deduplicate_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Remove duplicate or very similar patterns"""
        unique_patterns = []
        
        for pattern in patterns:
            is_duplicate = False
            
            for existing in unique_patterns:
                if (pattern.type == existing.type and
                    self._patterns_similar(pattern, existing)):
                    # Keep the one with higher confidence
                    if pattern.confidence > existing.confidence:
                        unique_patterns.remove(existing)
                        unique_patterns.append(pattern)
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_patterns.append(pattern)
        
        return unique_patterns
    
    def _patterns_similar(self, p1: Pattern, p2: Pattern) -> bool:
        """Check if two patterns are similar"""
        # Type-specific similarity checks
        if p1.type == PatternType.CORRELATION:
            # Same columns involved
            cols1 = {p1.parameters.get('column1'), p1.parameters.get('column2')}
            cols2 = {p2.parameters.get('column1'), p2.parameters.get('column2')}
            return cols1 == cols2
        
        # Default: check description similarity
        return p1.description == p2.description
    
    def _rank_patterns(self, patterns: List[Pattern]) -> List[Pattern]:
        """Rank patterns by importance"""
        # Simple ranking by confidence and type priority
        type_priority = {
            PatternType.ANOMALY: 1.0,
            PatternType.CHANGE_POINT: 0.9,
            PatternType.TREND: 0.8,
            PatternType.CORRELATION: 0.7,
            PatternType.SEASONAL: 0.6,
            PatternType.DISTRIBUTION: 0.5
        }
        
        for pattern in patterns:
            priority = type_priority.get(pattern.type, 0.5)
            pattern.importance_score = pattern.confidence * priority
        
        return sorted(patterns, key=lambda p: p.importance_score, reverse=True)
    
    def _generate_insights(self, patterns: List[Pattern], data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate high-level insights from detected patterns"""
        insights = []
        
        # Insight 1: Data quality
        anomaly_patterns = [p for p in patterns if p.type == PatternType.ANOMALY]
        if anomaly_patterns:
            total_anomalies = sum(p.parameters.get('anomaly_count', 0) for p in anomaly_patterns)
            insights.append({
                "type": "data_quality",
                "title": "Data Quality Issues Detected",
                "description": f"Found {total_anomalies} anomalous data points across {len(anomaly_patterns)} columns",
                "severity": "medium" if total_anomalies < len(data) * 0.05 else "high",
                "affected_columns": list(set(p.parameters.get('column1', p.description.split()[0]) 
                                           for p in anomaly_patterns))
            })
        
        # Insight 2: Strong relationships
        correlation_patterns = [p for p in patterns if p.type == PatternType.CORRELATION]
        strong_correlations = [p for p in correlation_patterns 
                              if abs(p.parameters.get('correlation', 0)) > 0.7]
        if strong_correlations:
            insights.append({
                "type": "relationships",
                "title": "Strong Relationships Found",
                "description": f"Discovered {len(strong_correlations)} strong correlations between variables",
                "details": [
                    {
                        "variables": [p.parameters['column1'], p.parameters['column2']],
                        "correlation": p.parameters['correlation'],
                        "type": p.parameters.get('relationship_type', 'linear')
                    }
                    for p in strong_correlations[:5]  # Top 5
                ]
            })
        
        # Insight 3: Temporal patterns
        temporal_patterns = [p for p in patterns 
                           if p.type in [PatternType.TREND, PatternType.SEASONAL, PatternType.CYCLIC]]
        if temporal_patterns:
            insights.append({
                "type": "temporal",
                "title": "Temporal Patterns Detected",
                "description": "Data shows time-based patterns",
                "patterns": [
                    {
                        "type": p.type.value,
                        "description": p.description,
                        "confidence": p.confidence
                    }
                    for p in temporal_patterns
                ]
            })
        
        return insights
    
    def _generate_recommendations(self, patterns: List[Pattern], data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on patterns"""
        recommendations = []
        
        # Recommendation 1: Handle anomalies
        anomaly_patterns = [p for p in patterns if p.type == PatternType.ANOMALY]
        if anomaly_patterns:
            recommendations.append({
                "type": "data_cleaning",
                "priority": "high",
                "title": "Review and Handle Anomalies",
                "description": "Anomalies detected in the data may affect analysis accuracy",
                "actions": [
                    "Review flagged anomalous values",
                    "Determine if anomalies are errors or valid extreme values",
                    "Consider removing or imputing anomalous values",
                    "Document any data cleaning decisions"
                ]
            })
        
        # Recommendation 2: Leverage correlations
        correlation_patterns = [p for p in patterns if p.type == PatternType.CORRELATION]
        if len(correlation_patterns) > 3:
            recommendations.append({
                "type": "feature_engineering",
                "priority": "medium",
                "title": "Consider Dimensionality Reduction",
                "description": "Multiple correlated variables detected",
                "actions": [
                    "Consider using PCA or factor analysis",
                    "Select representative variables from correlated groups",
                    "Create composite indices from related variables"
                ]
            })
        
        # Recommendation 3: Time series modeling
        has_trend = any(p.type == PatternType.TREND for p in patterns)
        has_seasonality = any(p.type in [PatternType.SEASONAL, PatternType.CYCLIC] 
                            for p in patterns)
        
        if has_trend or has_seasonality:
            actions = []
            if has_trend:
                actions.append("Use ARIMA or similar models for forecasting")
            if has_seasonality:
                actions.append("Include seasonal components in models")
            actions.extend([
                "Consider decomposition to separate trend and seasonal components",
                "Validate any forecasts with out-of-sample data"
            ])
            
            recommendations.append({
                "type": "modeling",
                "priority": "high",
                "title": "Apply Time Series Analysis",
                "description": "Temporal patterns suggest time series modeling would be valuable",
                "actions": actions
            })
        
        return recommendations

# intelligence/patterns/api.py
from flask import Flask, request, jsonify
import pandas as pd
import io

app = Flask(__name__)
engine = PatternEngine()

@app.route('/detect_patterns', methods=['POST'])
def detect_patterns():
    """API endpoint for pattern detection"""
    try:
        # Get data from request
        if 'file' in request.files:
            # Handle file upload
            file = request.files['file']
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
        else:
            # Handle JSON data
            data = request.json
            df = pd.DataFrame(data['data'])
        
        # Get parameters
        columns = request.args.getlist('columns')
        pattern_types = request.args.getlist('pattern_types')
        
        # Detect patterns
        results = engine.detect_patterns(df, columns, pattern_types)
        
        return jsonify(results)
        
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8081)
```

## Week 2: Query Generation

### Day 6-7: Intent Understanding & Query Building

```python
# intelligence/query/intent_parser.py
from typing import List, Dict, Any, Tuple
import spacy
from dataclasses import dataclass
import re

@dataclass
class QueryIntent:
    """Represents the parsed intent of a natural language query"""
    action: str  # aggregate, filter, compare, trend, etc.
    metrics: List[str]
    dimensions: List[str]
    filters: List[Dict[str, Any]]
    time_range: Optional[str]
    aggregation: Optional[str]
    comparison: Optional[Dict[str, Any]]
    confidence: float

class IntentParser:
    """Parse natural language into structured query intent"""
    
    def __init__(self):
        # Load spaCy model
        self.nlp = spacy.load("en_core_web_sm")
        
        # Define patterns
        self.metric_patterns = [
            "count", "sum", "average", "avg", "mean", "max", "maximum",
            "min", "minimum", "total", "percentage", "percent", "ratio"
        ]
        
        self.time_patterns = {
            "last hour": "SINCE 1 hour ago",
            "last day": "SINCE 1 day ago",
            "last week": "SINCE 1 week ago",
            "last month": "SINCE 1 month ago",
            "yesterday": "SINCE yesterday",
            "today": "SINCE today",
            "this week": "SINCE this week",
            "this month": "SINCE this month"
        }
        
        self.comparison_words = ["vs", "versus", "compared to", "compare"]
        
    def parse(self, query: str, available_schemas: List[Dict[str, Any]]) -> QueryIntent:
        """Parse natural language query into structured intent"""
        
        # Process with spaCy
        doc = self.nlp(query.lower())
        
        # Extract components
        action = self._identify_action(doc)
        metrics = self._extract_metrics(doc, available_schemas)
        dimensions = self._extract_dimensions(doc, available_schemas)
        filters = self._extract_filters(doc, available_schemas)
        time_range = self._extract_time_range(query)
        aggregation = self._identify_aggregation(doc)
        comparison = self._extract_comparison(doc)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            action, metrics, dimensions, available_schemas
        )
        
        return QueryIntent(
            action=action,
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            time_range=time_range,
            aggregation=aggregation,
            comparison=comparison,
            confidence=confidence
        )
    
    def _identify_action(self, doc) -> str:
        """Identify the main action requested"""
        
        # Look for key verbs
        verbs = [token.lemma_ for token in doc if token.pos_ == "VERB"]
        
        action_mapping = {
            "show": "display",
            "get": "display",
            "find": "search",
            "calculate": "aggregate",
            "count": "aggregate",
            "compare": "compare",
            "analyze": "analyze",
            "trend": "trend",
            "forecast": "forecast"
        }
        
        for verb in verbs:
            if verb in action_mapping:
                return action_mapping[verb]
        
        # Default based on other indicators
        if any(word in doc.text for word in self.comparison_words):
            return "compare"
        
        return "display"
    
    def _extract_metrics(self, doc, schemas: List[Dict[str, Any]]) -> List[str]:
        """Extract metrics/measures from the query"""
        metrics = []
        
        # Get all available numeric attributes
        numeric_attrs = set()
        for schema in schemas:
            for attr in schema.get('attributes', []):
                if attr['data_type'] in ['numeric', 'float', 'integer']:
                    numeric_attrs.add(attr['name'].lower())
        
        # Look for metric keywords
        for token in doc:
            # Check if token matches a numeric attribute
            if token.text in numeric_attrs:
                metrics.append(token.text)
            
            # Check for aggregation functions
            if token.text in self.metric_patterns:
                # Find the object of the aggregation
                for child in token.children:
                    if child.dep_ == "pobj" and child.text in numeric_attrs:
                        metrics.append(f"{token.text}({child.text})")
        
        # Default metrics based on action
        if not metrics and self.action == "aggregate":
            # Use count as default
            metrics = ["count(*)"]
        
        return metrics
    
    def _extract_dimensions(self, doc, schemas: List[Dict[str, Any]]) -> List[str]:
        """Extract grouping dimensions from the query"""
        dimensions = []
        
        # Get all available attributes
        all_attrs = set()
        for schema in schemas:
            for attr in schema.get('attributes', []):
                all_attrs.add(attr['name'].lower())
        
        # Look for "by" phrases
        for token in doc:
            if token.text == "by" and token.dep_ == "prep":
                # Get the object of "by"
                for child in token.children:
                    if child.text in all_attrs:
                        dimensions.append(child.text)
        
        # Look for categorical attributes mentioned
        categorical_attrs = set()
        for schema in schemas:
            for attr in schema.get('attributes', []):
                if attr['data_type'] in ['string', 'category']:
                    categorical_attrs.add(attr['name'].lower())
        
        for token in doc:
            if token.text in categorical_attrs and token.text not in dimensions:
                # Check if it's used as a dimension
                if any(parent.text in ["per", "by", "for"] for parent in token.ancestors):
                    dimensions.append(token.text)
        
        return dimensions
    
    def _extract_filters(self, doc, schemas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract filter conditions from the query"""
        filters = []
        
        # Patterns for filter extraction
        filter_patterns = [
            (r"where (\w+) (?:is|equals|=) (\w+)", "equals"),
            (r"(\w+) (?:greater than|>) (\d+)", "greater_than"),
            (r"(\w+) (?:less than|<) (\d+)", "less_than"),
            (r"(\w+) (?:contains|like) (\w+)", "contains"),
            (r"(?:only|just) (\w+)", "equals")
        ]
        
        text = doc.text
        for pattern, operator in filter_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                field = match.group(1)
                value = match.group(2) if len(match.groups()) > 1 else True
                
                filters.append({
                    "field": field,
                    "operator": operator,
                    "value": value
                })
        
        return filters
    
    def _extract_time_range(self, query: str) -> Optional[str]:
        """Extract time range from the query"""
        
        query_lower = query.lower()
        
        # Check predefined patterns
        for pattern, nrql_time in self.time_patterns.items():
            if pattern in query_lower:
                return nrql_time
        
        # Check for custom time ranges
        time_regex = r"(?:since|from|between) (.+?)(?:\s+(?:to|until)\s+(.+?))?(?:\s|$)"
        match = re.search(time_regex, query_lower)
        
        if match:
            start_time = match.group(1)
            end_time = match.group(2)
            
            if end_time:
                return f"SINCE {start_time} UNTIL {end_time}"
            else:
                return f"SINCE {start_time}"
        
        # Default
        return "SINCE 1 hour ago"
    
    def _calculate_confidence(self, action: str, metrics: List[str], 
                            dimensions: List[str], schemas: List[Dict[str, Any]]) -> float:
        """Calculate confidence in the parsed intent"""
        
        confidence = 0.5  # Base confidence
        
        # Increase confidence for identified components
        if action != "display":
            confidence += 0.1
        
        if metrics:
            confidence += 0.2
        
        if dimensions:
            confidence += 0.1
        
        # Decrease if no schema match
        if not any(self._matches_schema(metrics + dimensions, schema) 
                  for schema in schemas):
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def _matches_schema(self, fields: List[str], schema: Dict[str, Any]) -> bool:
        """Check if fields match a schema"""
        schema_attrs = {attr['name'].lower() for attr in schema.get('attributes', [])}
        return any(field.lower() in schema_attrs for field in fields)

# intelligence/query/generator.py
class QueryGenerator:
    """Generate optimized NRQL queries from intent"""
    
    def __init__(self):
        self.intent_parser = IntentParser()
        self.query_builder = QueryBuilder()
        self.optimizer = QueryOptimizer()
        
    def generate(self, natural_language: str, schemas: List[Dict[str, Any]], 
                config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate NRQL query from natural language"""
        
        # Parse intent
        intent = self.intent_parser.parse(natural_language, schemas)
        
        # Select appropriate schema
        selected_schema = self._select_schema(intent, schemas)
        
        if not selected_schema:
            return {
                "success": False,
                "error": "Could not find appropriate data schema",
                "suggestions": self._generate_suggestions(schemas)
            }
        
        # Build base query
        base_query = self.query_builder.build(intent, selected_schema)
        
        # Optimize query
        optimized = self.optimizer.optimize(base_query, config)
        
        # Generate alternatives
        alternatives = self._generate_alternatives(intent, selected_schema)
        
        return {
            "success": True,
            "query": optimized.query,
            "intent": intent.__dict__,
            "schema_used": selected_schema['name'],
            "estimated_cost": optimized.estimated_cost,
            "performance_hints": optimized.hints,
            "alternatives": alternatives,
            "explanation": self._generate_explanation(intent, optimized)
        }
    
    def _select_schema(self, intent: QueryIntent, schemas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Select the best schema for the query intent"""
        
        scores = []
        
        for schema in schemas:
            score = 0
            schema_attrs = {attr['name'].lower() for attr in schema.get('attributes', [])}
            
            # Score based on metric matches
            for metric in intent.metrics:
                # Extract attribute name from aggregation function
                metric_attr = re.sub(r'^\w+\((.*)\)', r'\1', metric).lower()
                if metric_attr in schema_attrs:
                    score += 2
            
            # Score based on dimension matches
            for dim in intent.dimensions:
                if dim.lower() in schema_attrs:
                    score += 1
            
            # Score based on filter matches
            for filter_cond in intent.filters:
                if filter_cond['field'].lower() in schema_attrs:
                    score += 1
            
            scores.append((schema, score))
        
        # Return schema with highest score
        if scores:
            best_schema, best_score = max(scores, key=lambda x: x[1])
            if best_score > 0:
                return best_schema
        
        return None

# intelligence/query/builder.py
class QueryBuilder:
    """Build NRQL queries from structured intent"""
    
    def __init__(self):
        self.templates = self._load_templates()
        
    def build(self, intent: QueryIntent, schema: Dict[str, Any]) -> Query:
        """Build NRQL query from intent"""
        
        # Start with SELECT clause
        select_clause = self._build_select(intent, schema)
        
        # FROM clause
        from_clause = f"FROM {schema['name']}"
        
        # WHERE clause
        where_clause = self._build_where(intent, schema)
        
        # GROUP BY clause
        group_by_clause = self._build_group_by(intent)
        
        # TIME clause
        time_clause = intent.time_range or "SINCE 1 hour ago"
        
        # Construct query
        query_parts = [
            select_clause,
            from_clause
        ]
        
        if where_clause:
            query_parts.append(where_clause)
        
        if group_by_clause:
            query_parts.append(group_by_clause)
        
        query_parts.append(time_clause)
        
        # Add LIMIT
        query_parts.append("LIMIT 100")
        
        return Query(
            nrql=" ".join(query_parts),
            intent=intent,
            schema=schema
        )
    
    def _build_select(self, intent: QueryIntent, schema: Dict[str, Any]) -> str:
        """Build SELECT clause"""
        
        if not intent.metrics:
            # Default selection
            if intent.dimensions:
                # Count by dimensions
                return f"SELECT count(*)"
            else:
                # Select all
                return "SELECT *"
        
        # Build metric expressions
        select_items = []
        
        for metric in intent.metrics:
            if "(" in metric:
                # Already has aggregation function
                select_items.append(metric)
            else:
                # Add default aggregation
                attr_type = self._get_attribute_type(metric, schema)
                
                if attr_type == "numeric":
                    select_items.append(f"average({metric})")
                else:
                    select_items.append(f"count({metric})")
        
        # Add dimensions if grouping
        if intent.dimensions:
            select_items.extend(intent.dimensions)
        
        return f"SELECT {', '.join(select_items)}"
    
    def _build_where(self, intent: QueryIntent, schema: Dict[str, Any]) -> Optional[str]:
        """Build WHERE clause"""
        
        if not intent.filters:
            return None
        
        conditions = []
        
        for filter_cond in intent.filters:
            field = filter_cond['field']
            operator = filter_cond['operator']
            value = filter_cond['value']
            
            # Map operators to NRQL
            if operator == "equals":
                conditions.append(f"{field} = '{value}'")
            elif operator == "greater_than":
                conditions.append(f"{field} > {value}")
            elif operator == "less_than":
                conditions.append(f"{field} < {value}")
            elif operator == "contains":
                conditions.append(f"{field} LIKE '%{value}%'")
        
        if conditions:
            return f"WHERE {' AND '.join(conditions)}"
        
        return None
    
    def _build_group_by(self, intent: QueryIntent) -> Optional[str]:
        """Build GROUP BY clause (FACET in NRQL)"""
        
        if intent.dimensions:
            return f"FACET {', '.join(intent.dimensions)}"
        
        return None
    
    def _get_attribute_type(self, attr_name: str, schema: Dict[str, Any]) -> str:
        """Get the data type of an attribute"""
        
        for attr in schema.get('attributes', []):
            if attr['name'].lower() == attr_name.lower():
                return attr['data_type']
        
        return "unknown"

# intelligence/query/optimizer.py
class QueryOptimizer:
    """Optimize queries for performance and cost"""
    
    def __init__(self):
        self.rules = self._load_optimization_rules()
        
    def optimize(self, query: Query, config: Optional[Dict[str, Any]] = None) -> OptimizedQuery:
        """Optimize query for performance"""
        
        optimized_nrql = query.nrql
        hints = []
        
        # Apply optimization rules
        for rule in self.rules:
            if rule.applies(query):
                optimized_nrql = rule.apply(optimized_nrql)
                hints.append(rule.hint)
        
        # Estimate cost
        estimated_cost = self._estimate_cost(optimized_nrql, query.schema)
        
        # Performance analysis
        performance = self._analyze_performance(optimized_nrql, query.schema)
        
        return OptimizedQuery(
            query=optimized_nrql,
            original_query=query.nrql,
            estimated_cost=estimated_cost,
            performance=performance,
            hints=hints
        )
    
    def _estimate_cost(self, nrql: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate query cost"""
        
        # Simple cost model based on data volume and query complexity
        base_cost = 1.0
        
        # Factor 1: Data volume
        data_volume = schema.get('estimated_volume', 1000000)
        volume_factor = math.log10(data_volume) / 6  # Normalize to ~1 for 1M records
        
        # Factor 2: Query complexity
        complexity_factor = 1.0
        if "FACET" in nrql:
            complexity_factor += 0.5
        if "JOIN" in nrql:
            complexity_factor += 1.0
        if re.search(r'percentile|histogram|funnel', nrql):
            complexity_factor += 0.5
        
        # Factor 3: Time range
        time_factor = 1.0
        if "SINCE 1 hour ago" in nrql:
            time_factor = 0.1
        elif "SINCE 1 day ago" in nrql:
            time_factor = 0.5
        elif "SINCE 1 week ago" in nrql:
            time_factor = 1.0
        else:
            time_factor = 2.0
        
        total_cost = base_cost * volume_factor * complexity_factor * time_factor
        
        return {
            "estimated_cost": round(total_cost, 2),
            "factors": {
                "data_volume": volume_factor,
                "complexity": complexity_factor,
                "time_range": time_factor
            },
            "cost_rating": "low" if total_cost < 2 else "medium" if total_cost < 5 else "high"
        }

# intelligence/query/templates.py
class QueryTemplates:
    """Pre-defined query templates for common patterns"""
    
    def __init__(self):
        self.templates = {
            "error_rate": {
                "pattern": r"error rate|failure rate|success rate",
                "template": "SELECT percentage(count(*), WHERE error = true) FROM {schema} {time_range}",
                "description": "Calculate error rate percentage"
            },
            "top_n": {
                "pattern": r"top (\d+) (.+)",
                "template": "SELECT count(*) FROM {schema} FACET {dimension} {time_range} LIMIT {n}",
                "description": "Find top N items by count"
            },
            "percentile": {
                "pattern": r"(\d+)(?:th|st|nd|rd)? percentile (?:of )?(.+)",
                "template": "SELECT percentile({metric}, {percentile}) FROM {schema} {time_range}",
                "description": "Calculate percentile of a metric"
            },
            "comparison": {
                "pattern": r"compare (.+) (?:between|across) (.+)",
                "template": "SELECT {metric} FROM {schema} FACET {dimension} {time_range} COMPARE WITH {comparison_period} ago",
                "description": "Compare metrics across time periods"
            },
            "funnel": {
                "pattern": r"funnel|conversion|drop.?off",
                "template": "SELECT funnel({step1}, {step2}, {step3}) FROM {schema} {time_range}",
                "description": "Analyze conversion funnel"
            },
            "histogram": {
                "pattern": r"distribution|histogram|buckets",
                "template": "SELECT histogram({metric}, {buckets}) FROM {schema} {time_range}",
                "description": "Show distribution of values"
            }
        }
```

## Week 3: Visualization Intelligence

### Day 11-12: Data Shape Analysis

```python
# intelligence/visualization/analyzer.py
from typing import Dict, List, Any, Tuple
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class DataShape:
    """Describes the shape and characteristics of data"""
    data_type: str  # numeric, categorical, temporal, etc.
    cardinality: int
    distribution: str
    has_nulls: bool
    is_continuous: bool
    is_ordered: bool
    range: Tuple[Any, Any]
    unique_ratio: float
    patterns: List[str]

class DataShapeAnalyzer:
    """Analyze data shape to inform visualization selection"""
    
    def analyze(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Comprehensive data shape analysis"""
        
        shape_info = {
            "rows": len(data),
            "columns": len(data.columns),
            "column_shapes": {},
            "relationships": [],
            "overall_shape": None
        }
        
        # Analyze each column
        for col in data.columns:
            shape_info["column_shapes"][col] = self._analyze_column(data[col])
        
        # Analyze relationships
        if len(data.columns) > 1:
            shape_info["relationships"] = self._analyze_relationships(data)
        
        # Determine overall shape
        shape_info["overall_shape"] = self._determine_overall_shape(shape_info)
        
        return shape_info
    
    def _analyze_column(self, series: pd.Series) -> DataShape:
        """Analyze a single column"""
        
        # Basic info
        non_null = series.dropna()
        
        if len(non_null) == 0:
            return DataShape(
                data_type="empty",
                cardinality=0,
                distribution="none",
                has_nulls=True,
                is_continuous=False,
                is_ordered=False,
                range=(None, None),
                unique_ratio=0,
                patterns=[]
            )
        
        # Determine data type
        if pd.api.types.is_numeric_dtype(series):
            data_type = "numeric"
            is_continuous = self._is_continuous(non_null)
            distribution = self._detect_distribution(non_null)
            is_ordered = True
            range_vals = (float(non_null.min()), float(non_null.max()))
        
        elif pd.api.types.is_datetime64_any_dtype(series):
            data_type = "temporal"
            is_continuous = True
            distribution = "temporal"
            is_ordered = True
            range_vals = (non_null.min(), non_null.max())
        
        else:
            data_type = "categorical"
            is_continuous = False
            distribution = "categorical"
            is_ordered = self._is_ordered_categorical(non_null)
            range_vals = (None, None)
        
        # Calculate metrics
        cardinality = non_null.nunique()
        unique_ratio = cardinality / len(non_null)
        has_nulls = series.isnull().any()
        
        # Detect patterns
        patterns = self._detect_patterns(series, data_type)
        
        return DataShape(
            data_type=data_type,
            cardinality=cardinality,
            distribution=distribution,
            has_nulls=has_nulls,
            is_continuous=is_continuous,
            is_ordered=is_ordered,
            range=range_vals,
            unique_ratio=unique_ratio,
            patterns=patterns
        )
    
    def _is_continuous(self, series: pd.Series) -> bool:
        """Check if numeric data is continuous vs discrete"""
        
        if len(series) < 10:
            return False
        
        # Check if values are mostly integers
        is_int = np.all(series == series.astype(int))
        
        if is_int:
            # Check range vs unique values
            range_size = series.max() - series.min() + 1
            unique_count = series.nunique()
            
            # If unique values cover less than 50% of range, likely discrete
            return unique_count / range_size > 0.5
        
        return True
    
    def _detect_distribution(self, series: pd.Series) -> str:
        """Detect the distribution type of numeric data"""
        
        from scipy import stats
        
        # Normalize data
        data = (series - series.mean()) / series.std()
        
        # Test distributions
        distributions = {
            'normal': stats.normaltest(data)[1],
            'uniform': stats.kstest(data, 'uniform')[1],
            'exponential': stats.kstest(data, 'expon')[1]
        }
        
        # Return distribution with highest p-value
        best_dist = max(distributions.items(), key=lambda x: x[1])
        
        if best_dist[1] > 0.05:
            return best_dist[0]
        
        # Check for other patterns
        skewness = series.skew()
        if abs(skewness) > 1:
            return "skewed"
        
        return "unknown"
    
    def _analyze_relationships(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Analyze relationships between columns"""
        
        relationships = []
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        # Correlations between numeric columns
        if len(numeric_cols) > 1:
            corr_matrix = data[numeric_cols].corr()
            
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    corr = corr_matrix.iloc[i, j]
                    if abs(corr) > 0.5:
                        relationships.append({
                            "type": "correlation",
                            "columns": [numeric_cols[i], numeric_cols[j]],
                            "strength": abs(corr),
                            "direction": "positive" if corr > 0 else "negative"
                        })
        
        # Check for hierarchical relationships in categorical data
        cat_cols = data.select_dtypes(include=['object', 'category']).columns
        
        for col1 in cat_cols:
            for col2 in cat_cols:
                if col1 != col2:
                    # Check if col1 determines col2
                    groups = data.groupby(col1)[col2].nunique()
                    if groups.max() == 1:
                        relationships.append({
                            "type": "hierarchy",
                            "parent": col1,
                            "child": col2
                        })
        
        return relationships

# intelligence/visualization/recommender.py
class VisualizationRecommender:
    """Recommend appropriate visualizations based on data and intent"""
    
    def __init__(self):
        self.shape_analyzer = DataShapeAnalyzer()
        self.viz_rules = self._load_visualization_rules()
        
    def recommend(self, data: pd.DataFrame, intent: Optional[str] = None, 
                 patterns: Optional[List[Pattern]] = None) -> List[Dict[str, Any]]:
        """Recommend visualizations for the data"""
        
        # Analyze data shape
        shape_info = self.shape_analyzer.analyze(data)
        
        # Get candidate visualizations
        candidates = self._get_candidates(shape_info, intent)
        
        # Score each candidate
        scored_candidates = []
        for candidate in candidates:
            score = self._score_visualization(candidate, shape_info, intent, patterns)
            scored_candidates.append({
                **candidate,
                "score": score
            })
        
        # Sort by score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        
        # Add configuration for top candidates
        recommendations = []
        for candidate in scored_candidates[:5]:  # Top 5
            config = self._generate_config(candidate, data, shape_info)
            recommendations.append({
                "type": candidate["type"],
                "score": candidate["score"],
                "reasoning": candidate["reasoning"],
                "config": config,
                "preview": self._generate_preview(candidate["type"], data, config)
            })
        
        return recommendations
    
    def _get_candidates(self, shape_info: Dict[str, Any], intent: Optional[str]) -> List[Dict[str, Any]]:
        """Get candidate visualizations based on data shape"""
        
        candidates = []
        
        # Single numeric column
        if len(shape_info["columns"]) == 1:
            col_shape = list(shape_info["column_shapes"].values())[0]
            
            if col_shape.data_type == "numeric":
                candidates.extend([
                    {
                        "type": "histogram",
                        "reasoning": "Show distribution of numeric values"
                    },
                    {
                        "type": "box_plot",
                        "reasoning": "Show statistical summary and outliers"
                    }
                ])
                
                if col_shape.distribution == "normal":
                    candidates.append({
                        "type": "density_plot",
                        "reasoning": "Data appears normally distributed"
                    })
        
        # Time series
        temporal_cols = [col for col, shape in shape_info["column_shapes"].items()
                        if shape.data_type == "temporal"]
        
        if temporal_cols:
            numeric_cols = [col for col, shape in shape_info["column_shapes"].items()
                          if shape.data_type == "numeric"]
            
            if numeric_cols:
                candidates.append({
                    "type": "line_chart",
                    "reasoning": "Show trends over time"
                })
                
                if len(numeric_cols) > 1:
                    candidates.append({
                        "type": "multi_line_chart",
                        "reasoning": "Compare multiple metrics over time"
                    })
        
        # Categorical + Numeric
        cat_cols = [col for col, shape in shape_info["column_shapes"].items()
                   if shape.data_type == "categorical"]
        numeric_cols = [col for col, shape in shape_info["column_shapes"].items()
                      if shape.data_type == "numeric"]
        
        if cat_cols and numeric_cols:
            cat_shape = shape_info["column_shapes"][cat_cols[0]]
            
            if cat_shape.cardinality <= 10:
                candidates.extend([
                    {
                        "type": "bar_chart",
                        "reasoning": "Compare values across categories"
                    },
                    {
                        "type": "grouped_bar_chart",
                        "reasoning": "Compare multiple metrics by category"
                    }
                ])
            
            if cat_shape.cardinality <= 6:
                candidates.append({
                    "type": "pie_chart",
                    "reasoning": "Show proportions of categories"
                })
        
        # Two numeric columns
        if len(numeric_cols) == 2:
            candidates.append({
                "type": "scatter_plot",
                "reasoning": "Show relationship between two numeric variables"
            })
            
            # Check for correlation
            for rel in shape_info.get("relationships", []):
                if rel["type"] == "correlation" and rel["strength"] > 0.7:
                    candidates.append({
                        "type": "scatter_with_regression",
                        "reasoning": f"Strong {rel['direction']} correlation detected"
                    })
        
        # Many numeric columns
        if len(numeric_cols) > 3:
            candidates.extend([
                {
                    "type": "heatmap",
                    "reasoning": "Show patterns across multiple variables"
                },
                {
                    "type": "parallel_coordinates",
                    "reasoning": "Compare multiple dimensions simultaneously"
                }
            ])
        
        # Hierarchical categorical data
        hierarchies = [rel for rel in shape_info.get("relationships", [])
                      if rel["type"] == "hierarchy"]
        
        if hierarchies:
            candidates.append({
                "type": "treemap",
                "reasoning": "Visualize hierarchical categorical data"
            })
        
        return candidates
    
    def _score_visualization(self, candidate: Dict[str, Any], shape_info: Dict[str, Any],
                           intent: Optional[str], patterns: Optional[List[Pattern]]) -> float:
        """Score a visualization candidate"""
        
        score = 0.5  # Base score
        
        # Intent matching
        if intent:
            intent_lower = intent.lower()
            
            intent_viz_map = {
                "distribution": ["histogram", "density_plot", "box_plot"],
                "trend": ["line_chart", "area_chart"],
                "comparison": ["bar_chart", "grouped_bar_chart"],
                "correlation": ["scatter_plot", "scatter_with_regression"],
                "composition": ["pie_chart", "stacked_bar_chart", "treemap"]
            }
            
            for intent_key, viz_types in intent_viz_map.items():
                if intent_key in intent_lower and candidate["type"] in viz_types:
                    score += 0.3
        
        # Pattern matching
        if patterns:
            pattern_viz_map = {
                PatternType.TREND: ["line_chart", "area_chart"],
                PatternType.SEASONAL: ["line_chart", "heatmap"],
                PatternType.CORRELATION: ["scatter_plot", "scatter_with_regression"],
                PatternType.DISTRIBUTION: ["histogram", "density_plot"],
                PatternType.ANOMALY: ["scatter_plot", "box_plot"]
            }
            
            for pattern in patterns:
                if pattern.type in pattern_viz_map and candidate["type"] in pattern_viz_map[pattern.type]:
                    score += 0.2 * pattern.confidence
        
        # Data appropriateness
        viz_type = candidate["type"]
        
        # Penalize if too many categories for certain viz types
        if viz_type in ["pie_chart", "donut_chart"]:
            max_cardinality = max(shape.cardinality for shape in shape_info["column_shapes"].values()
                                if shape.data_type == "categorical")
            if max_cardinality > 6:
                score -= 0.3
        
        # Boost for appropriate data volume
        rows = shape_info["rows"]
        if viz_type in ["scatter_plot", "heatmap"] and rows > 100:
            score += 0.1
        elif viz_type in ["bar_chart", "pie_chart"] and rows < 50:
            score += 0.1
        
        return min(1.0, max(0.0, score))
    
    def _generate_config(self, candidate: Dict[str, Any], data: pd.DataFrame, 
                        shape_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate visualization configuration"""
        
        config = {
            "type": candidate["type"],
            "title": self._generate_title(candidate["type"], data.columns),
            "responsive": True
        }
        
        viz_type = candidate["type"]
        
        # Type-specific configuration
        if viz_type == "line_chart":
            temporal_col = next(col for col, shape in shape_info["column_shapes"].items()
                              if shape.data_type == "temporal")
            numeric_cols = [col for col, shape in shape_info["column_shapes"].items()
                          if shape.data_type == "numeric"]
            
            config.update({
                "x": temporal_col,
                "y": numeric_cols[0] if numeric_cols else None,
                "interpolation": "linear",
                "showPoints": len(data) < 50,
                "showArea": False
            })
        
        elif viz_type == "bar_chart":
            cat_col = next(col for col, shape in shape_info["column_shapes"].items()
                         if shape.data_type == "categorical")
            numeric_col = next(col for col, shape in shape_info["column_shapes"].items()
                             if shape.data_type == "numeric")
            
            config.update({
                "x": cat_col,
                "y": numeric_col,
                "orientation": "vertical",
                "showValues": True,
                "sortBy": "value"
            })
        
        elif viz_type == "scatter_plot":
            numeric_cols = [col for col, shape in shape_info["column_shapes"].items()
                          if shape.data_type == "numeric"]
            
            if len(numeric_cols) >= 2:
                config.update({
                    "x": numeric_cols[0],
                    "y": numeric_cols[1],
                    "showRegression": candidate.get("show_regression", False),
                    "pointSize": min(10, 1000 / len(data)),
                    "opacity": 0.7 if len(data) > 100 else 1.0
                })
        
        elif viz_type == "heatmap":
            config.update({
                "colorScheme": "viridis",
                "showValues": len(data) < 20,
                "cellBorder": True
            })
        
        # Add color configuration
        config["colors"] = self._select_color_scheme(viz_type, shape_info)
        
        # Add interactivity
        config["interactions"] = {
            "hover": True,
            "zoom": viz_type in ["line_chart", "scatter_plot"],
            "pan": viz_type in ["line_chart", "scatter_plot"],
            "selection": viz_type in ["scatter_plot", "bar_chart"]
        }
        
        return config
    
    def _generate_title(self, viz_type: str, columns: List[str]) -> str:
        """Generate appropriate title for visualization"""
        
        if len(columns) == 1:
            return f"Distribution of {columns[0]}"
        elif len(columns) == 2:
            if viz_type == "scatter_plot":
                return f"{columns[1]} vs {columns[0]}"
            else:
                return f"{columns[1]} by {columns[0]}"
        else:
            return f"Analysis of {', '.join(columns[:3])}"
    
    def _select_color_scheme(self, viz_type: str, shape_info: Dict[str, Any]) -> List[str]:
        """Select appropriate color scheme"""
        
        # Categorical color schemes
        categorical_schemes = [
            ["#3366CC", "#DC3912", "#FF9900", "#109618", "#990099"],
            ["#0099C6", "#DD4477", "#66AA00", "#B82E2E", "#316395"],
            ["#4285F4", "#DB4437", "#F4B400", "#0F9D58", "#AB47BC"]
        ]
        
        # Sequential color schemes
        sequential_schemes = [
            ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476"],
            ["#fff5eb", "#fee6ce", "#fdd0a2", "#fdae6b", "#fd8d3c"],
            ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6"]
        ]
        
        # Diverging color schemes
        diverging_schemes = [
            ["#d73027", "#fc8d59", "#fee090", "#e0f3f8", "#91bfdb", "#4575b4"],
            ["#b2182b", "#ef8a62", "#fddbc7", "#d1e5f0", "#67a9cf", "#2166ac"]
        ]
        
        # Select based on visualization type and data
        if viz_type in ["pie_chart", "bar_chart", "treemap"]:
            return categorical_schemes[0]
        elif viz_type in ["heatmap", "choropleth"]:
            # Check if data might be diverging
            numeric_shapes = [shape for shape in shape_info["column_shapes"].values()
                            if shape.data_type == "numeric"]
            if numeric_shapes and any(shape.range[0] < 0 < shape.range[1] for shape in numeric_shapes):
                return diverging_schemes[0]
            else:
                return sequential_schemes[0]
        else:
            return categorical_schemes[0]

# intelligence/visualization/layout.py
class LayoutOptimizer:
    """Optimize dashboard layout for multiple visualizations"""
    
    def optimize_layout(self, visualizations: List[Dict[str, Any]], 
                       constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Optimize layout for multiple visualizations"""
        
        constraints = constraints or {}
        max_cols = constraints.get("max_columns", 12)
        max_rows = constraints.get("max_rows", 100)
        
        # Score different layout options
        layout_options = []
        
        # Option 1: Priority-based layout
        priority_layout = self._priority_based_layout(visualizations, max_cols)
        layout_options.append(("priority", priority_layout))
        
        # Option 2: Grouped layout (by data source or type)
        grouped_layout = self._grouped_layout(visualizations, max_cols)
        layout_options.append(("grouped", grouped_layout))
        
        # Option 3: Responsive grid
        grid_layout = self._responsive_grid_layout(visualizations, max_cols)
        layout_options.append(("grid", grid_layout))
        
        # Score each layout
        best_score = -1
        best_layout = None
        
        for layout_type, layout in layout_options:
            score = self._score_layout(layout, visualizations)
            if score > best_score:
                best_score = score
                best_layout = (layout_type, layout)
        
        return {
            "type": best_layout[0],
            "layout": best_layout[1],
            "score": best_score,
            "responsive_breakpoints": self._generate_breakpoints(best_layout[1])
        }
    
    def _priority_based_layout(self, visualizations: List[Dict[str, Any]], 
                              max_cols: int) -> List[Dict[str, Any]]:
        """Layout based on visualization importance"""
        
        # Sort by score/importance
        sorted_viz = sorted(visualizations, key=lambda v: v.get("score", 0), reverse=True)
        
        layout = []
        current_row = 0
        current_col = 0
        
        for i, viz in enumerate(sorted_viz):
            # Determine size based on importance and type
            if i == 0:  # Most important
                width = min(max_cols, 8)
                height = 4
            elif viz["type"] in ["heatmap", "scatter_plot", "parallel_coordinates"]:
                width = min(max_cols // 2, 6)
                height = 3
            else:
                width = min(max_cols // 3, 4)
                height = 2
            
            # Check if fits in current row
            if current_col + width > max_cols:
                current_row += 1
                current_col = 0
            
            layout.append({
                "visualization": viz,
                "position": {
                    "row": current_row,
                    "col": current_col,
                    "width": width,
                    "height": height
                }
            })
            
            current_col += width
        
        return layout
    
    def _grouped_layout(self, visualizations: List[Dict[str, Any]], 
                       max_cols: int) -> List[Dict[str, Any]]:
        """Group related visualizations together"""
        
        # Group by data source or type
        groups = {}
        for viz in visualizations:
            group_key = viz.get("data_source", viz["type"])
            if group_key not in groups:
                groups[group_key] = []
            groups[group_key].append(viz)
        
        layout = []
        current_row = 0
        
        for group_key, group_viz in groups.items():
            # Add group header
            layout.append({
                "type": "header",
                "text": f"{group_key} Analysis",
                "position": {
                    "row": current_row,
                    "col": 0,
                    "width": max_cols,
                    "height": 1
                }
            })
            
            current_row += 1
            
            # Layout group items
            current_col = 0
            for viz in group_viz:
                width = max_cols // min(len(group_viz), 3)
                height = 3
                
                if current_col + width > max_cols:
                    current_row += 1
                    current_col = 0
                
                layout.append({
                    "visualization": viz,
                    "position": {
                        "row": current_row,
                        "col": current_col,
                        "width": width,
                        "height": height
                    }
                })
                
                current_col += width
            
            current_row += 1
        
        return layout
```

## Week 4: Integration and Production

### Day 16-17: Go Service Wrapper

```go
// intelligence/service/server.go
package main

import (
    "context"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os/exec"
    "time"
    
    "github.com/gorilla/mux"
    "github.com/prometheus/client_golang/prometheus"
)

// IntelligenceService wraps the Python intelligence engine
type IntelligenceService struct {
    pythonPath   string
    scriptPath   string
    maxWorkers   int
    timeout      time.Duration
    metrics      *Metrics
}

type PatternRequest struct {
    Data        interface{}          `json:"data"`
    Columns     []string            `json:"columns,omitempty"`
    PatternTypes []string           `json:"pattern_types,omitempty"`
}

type PatternResponse struct {
    Patterns        []Pattern           `json:"patterns"`
    PatternCount    int                `json:"pattern_count"`
    PatternTypes    []string           `json:"pattern_types"`
    Insights        []Insight          `json:"insights"`
    Recommendations []Recommendation   `json:"recommendations"`
    Metadata        map[string]interface{} `json:"metadata"`
}

type QueryRequest struct {
    NaturalLanguage string              `json:"natural_language"`
    Schemas         []Schema            `json:"schemas"`
    Config          map[string]interface{} `json:"config,omitempty"`
}

type QueryResponse struct {
    Success         bool                `json:"success"`
    Query           string              `json:"query,omitempty"`
    Intent          interface{}         `json:"intent,omitempty"`
    SchemaUsed      string              `json:"schema_used,omitempty"`
    EstimatedCost   map[string]interface{} `json:"estimated_cost,omitempty"`
    Alternatives    []string            `json:"alternatives,omitempty"`
    Explanation     string              `json:"explanation,omitempty"`
    Error           string              `json:"error,omitempty"`
}

func (s *IntelligenceService) DetectPatterns(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    
    var req PatternRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // Call Python service
    result, err := s.callPythonService(ctx, "detect_patterns", req)
    if err != nil {
        s.metrics.RecordError("detect_patterns", err)
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    var resp PatternResponse
    if err := json.Unmarshal(result, &resp); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    s.metrics.RecordSuccess("detect_patterns")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func (s *IntelligenceService) GenerateQuery(w http.ResponseWriter, r *http.Request) {
    ctx := r.Context()
    
    var req QueryRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, err.Error(), http.StatusBadRequest)
        return
    }
    
    // Call Python service
    result, err := s.callPythonService(ctx, "generate_query", req)
    if err != nil {
        s.metrics.RecordError("generate_query", err)
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    var resp QueryResponse
    if err := json.Unmarshal(result, &resp); err != nil {
        http.Error(w, err.Error(), http.StatusInternalServerError)
        return
    }
    
    s.metrics.RecordSuccess("generate_query")
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(resp)
}

func (s *IntelligenceService) callPythonService(ctx context.Context, method string, data interface{}) ([]byte, error) {
    // Prepare request
    reqData, err := json.Marshal(map[string]interface{}{
        "method": method,
        "data":   data,
    })
    if err != nil {
        return nil, fmt.Errorf("marshal request: %w", err)
    }
    
    // Create command with timeout
    ctx, cancel := context.WithTimeout(ctx, s.timeout)
    defer cancel()
    
    cmd := exec.CommandContext(ctx, s.pythonPath, s.scriptPath, string(reqData))
    
    // Execute
    output, err := cmd.Output()
    if err != nil {
        if exitErr, ok := err.(*exec.ExitError); ok {
            return nil, fmt.Errorf("python service error: %s", exitErr.Stderr)
        }
        return nil, fmt.Errorf("execute python service: %w", err)
    }
    
    return output, nil
}

// Metrics collection
type Metrics struct {
    requests        *prometheus.CounterVec
    duration        *prometheus.HistogramVec
    errors          *prometheus.CounterVec
}

func NewMetrics() *Metrics {
    return &Metrics{
        requests: prometheus.NewCounterVec(
            prometheus.CounterOpts{
                Name: "intelligence_requests_total",
                Help: "Total number of intelligence service requests",
            },
            []string{"method"},
        ),
        duration: prometheus.NewHistogramVec(
            prometheus.HistogramOpts{
                Name: "intelligence_request_duration_seconds",
                Help: "Duration of intelligence service requests",
            },
            []string{"method"},
        ),
        errors: prometheus.NewCounterVec(
            prometheus.CounterOpts{
                Name: "intelligence_errors_total",
                Help: "Total number of intelligence service errors",
            },
            []string{"method"},
        ),
    }
}

func main() {
    service := &IntelligenceService{
        pythonPath: "/usr/bin/python3",
        scriptPath: "./intelligence/service.py",
        maxWorkers: 4,
        timeout:    30 * time.Second,
        metrics:    NewMetrics(),
    }
    
    router := mux.NewRouter()
    router.HandleFunc("/patterns/detect", service.DetectPatterns).Methods("POST")
    router.HandleFunc("/query/generate", service.GenerateQuery).Methods("POST")
    router.HandleFunc("/visualization/recommend", service.RecommendVisualization).Methods("POST")
    
    // Health check
    router.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        w.WriteHeader(http.StatusOK)
        json.NewEncoder(w).Encode(map[string]string{"status": "healthy"})
    })
    
    // Metrics endpoint
    router.Handle("/metrics", prometheus.Handler())
    
    log.Println("Intelligence service starting on :8081")
    log.Fatal(http.ListenAndServe(":8081", router))
}
```

### Day 18-19: Testing and Optimization

```python
# intelligence/tests/test_patterns.py
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from intelligence.patterns.engine import PatternEngine
from intelligence.patterns.base import PatternType

class TestPatternEngine:
    
    @pytest.fixture
    def engine(self):
        return PatternEngine()
    
    @pytest.fixture
    def sample_data(self):
        """Generate various types of test data"""
        np.random.seed(42)
        n = 1000
        
        # Time series with trend and seasonality
        dates = pd.date_range(start='2024-01-01', periods=n, freq='H')
        trend = np.linspace(100, 200, n)
        seasonal = 10 * np.sin(2 * np.pi * np.arange(n) / 24)  # Daily pattern
        noise = np.random.normal(0, 5, n)
        values = trend + seasonal + noise
        
        # Add some anomalies
        anomaly_indices = [100, 500, 800]
        for idx in anomaly_indices:
            values[idx] += 50
        
        # Categorical data
        categories = np.random.choice(['A', 'B', 'C', 'D'], n, p=[0.4, 0.3, 0.2, 0.1])
        
        # Correlated data
        x = np.random.normal(50, 10, n)
        y = 2 * x + np.random.normal(0, 5, n)
        
        return pd.DataFrame({
            'timestamp': dates,
            'value': values,
            'category': categories,
            'x': x,
            'y': y
        })
    
    def test_trend_detection(self, engine, sample_data):
        """Test trend pattern detection"""
        results = engine.detect_patterns(sample_data, ['value'])
        
        # Find trend patterns
        trend_patterns = [p for p in results['patterns'] 
                         if p['type'] == PatternType.TREND.value]
        
        assert len(trend_patterns) > 0
        assert trend_patterns[0]['parameters']['direction'] == 'increasing'
        assert trend_patterns[0]['confidence'] > 0.8
    
    def test_seasonality_detection(self, engine, sample_data):
        """Test seasonal pattern detection"""
        results = engine.detect_patterns(sample_data, ['value'])
        
        # Find seasonal patterns
        seasonal_patterns = [p for p in results['patterns'] 
                           if p['type'] == PatternType.SEASONAL.value]
        
        assert len(seasonal_patterns) > 0
        # Should detect daily seasonality (24-hour period)
        assert abs(seasonal_patterns[0]['parameters']['period'] - 24) < 2
    
    def test_anomaly_detection(self, engine, sample_data):
        """Test anomaly detection"""
        results = engine.detect_patterns(sample_data, ['value'])
        
        # Find anomaly patterns
        anomaly_patterns = [p for p in results['patterns'] 
                          if p['type'] == PatternType.ANOMALY.value]
        
        assert len(anomaly_patterns) > 0
        assert anomaly_patterns[0]['parameters']['anomaly_count'] >= 3
    
    def test_correlation_detection(self, engine, sample_data):
        """Test correlation detection"""
        results = engine.detect_patterns(sample_data, ['x', 'y'])
        
        # Find correlation patterns
        correlation_patterns = [p for p in results['patterns'] 
                              if p['type'] == PatternType.CORRELATION.value]
        
        assert len(correlation_patterns) > 0
        assert correlation_patterns[0]['parameters']['correlation'] > 0.9
        assert correlation_patterns[0]['parameters']['column1'] in ['x', 'y']
        assert correlation_patterns[0]['parameters']['column2'] in ['x', 'y']
    
    def test_distribution_detection(self, engine, sample_data):
        """Test distribution pattern detection"""
        # Add normally distributed column
        sample_data['normal'] = np.random.normal(100, 15, len(sample_data))
        
        results = engine.detect_patterns(sample_data, ['normal'])
        
        # Find distribution patterns
        dist_patterns = [p for p in results['patterns'] 
                        if p['type'] == PatternType.DISTRIBUTION.value]
        
        assert len(dist_patterns) > 0
        assert dist_patterns[0]['parameters']['distribution'] == 'normal'
    
    def test_empty_data_handling(self, engine):
        """Test handling of empty data"""
        empty_df = pd.DataFrame()
        results = engine.detect_patterns(empty_df)
        
        assert results['pattern_count'] == 0
        assert len(results['patterns']) == 0
    
    def test_missing_data_handling(self, engine):
        """Test handling of missing data"""
        data = pd.DataFrame({
            'col1': [1, 2, np.nan, 4, 5],
            'col2': [np.nan, np.nan, np.nan, np.nan, np.nan]
        })
        
        results = engine.detect_patterns(data)
        
        # Should detect missing data pattern
        missing_patterns = [p for p in results['patterns'] 
                          if p['type'] == PatternType.MISSING.value]
        
        assert len(missing_patterns) > 0

# intelligence/tests/test_query_generation.py
class TestQueryGeneration:
    
    @pytest.fixture
    def generator(self):
        from intelligence.query.generator import QueryGenerator
        return QueryGenerator()
    
    @pytest.fixture
    def sample_schemas(self):
        return [
            {
                'name': 'Transaction',
                'attributes': [
                    {'name': 'duration', 'data_type': 'numeric'},
                    {'name': 'error', 'data_type': 'boolean'},
                    {'name': 'endpoint', 'data_type': 'string'},
                    {'name': 'timestamp', 'data_type': 'timestamp'}
                ]
            },
            {
                'name': 'PageView',
                'attributes': [
                    {'name': 'loadTime', 'data_type': 'numeric'},
                    {'name': 'country', 'data_type': 'string'},
                    {'name': 'browser', 'data_type': 'string'},
                    {'name': 'timestamp', 'data_type': 'timestamp'}
                ]
            }
        ]
    
    def test_simple_query(self, generator, sample_schemas):
        """Test simple query generation"""
        result = generator.generate(
            "show me average duration",
            sample_schemas
        )
        
        assert result['success'] is True
        assert 'average(duration)' in result['query']
        assert 'Transaction' in result['query']
    
    def test_aggregation_query(self, generator, sample_schemas):
        """Test aggregation query generation"""
        result = generator.generate(
            "average load time by country",
            sample_schemas
        )
        
        assert result['success'] is True
        assert 'average(loadTime)' in result['query']
        assert 'FACET country' in result['query']
        assert 'PageView' in result['query']
    
    def test_filter_query(self, generator, sample_schemas):
        """Test query with filters"""
        result = generator.generate(
            "count errors in the last hour",
            sample_schemas
        )
        
        assert result['success'] is True
        assert 'count(*)' in result['query']
        assert 'WHERE error = true' in result['query']
        assert 'SINCE 1 hour ago' in result['query']
    
    def test_time_range_parsing(self, generator, sample_schemas):
        """Test various time range formats"""
        test_cases = [
            ("last week", "SINCE 1 week ago"),
            ("yesterday", "SINCE yesterday"),
            ("this month", "SINCE this month"),
            ("last 7 days", "SINCE 7 days ago")
        ]
        
        for nl_time, expected_nrql in test_cases:
            result = generator.generate(
                f"show data from {nl_time}",
                sample_schemas
            )
            
            assert expected_nrql in result['query']
    
    def test_comparison_query(self, generator, sample_schemas):
        """Test comparison query generation"""
        result = generator.generate(
            "compare this week vs last week",
            sample_schemas
        )
        
        assert result['success'] is True
        assert 'COMPARE WITH' in result['query']
    
    def test_optimization(self, generator, sample_schemas):
        """Test query optimization"""
        result = generator.generate(
            "show all transaction data",
            sample_schemas,
            config={'max_rows': 1000}
        )
        
        assert result['success'] is True
        assert 'LIMIT' in result['query']
        assert result['performance_hints'] is not None

# Benchmark tests
def test_pattern_detection_performance(benchmark):
    """Benchmark pattern detection performance"""
    engine = PatternEngine()
    
    # Generate large dataset
    n = 10000
    data = pd.DataFrame({
        'value1': np.random.normal(100, 15, n),
        'value2': np.random.exponential(2, n),
        'category': np.random.choice(['A', 'B', 'C'], n),
        'timestamp': pd.date_range('2024-01-01', periods=n, freq='T')
    })
    
    # Benchmark
    result = benchmark(engine.detect_patterns, data)
    
    # Should complete within reasonable time
    assert result is not None
    assert len(result['patterns']) > 0
```

### Day 20: Documentation and Deployment

```yaml
# intelligence/docker-compose.yml
version: '3.8'

services:
  intelligence-python:
    build:
      context: .
      dockerfile: Dockerfile.python
    ports:
      - "8081:8081"
    environment:
      - PYTHONUNBUFFERED=1
      - MAX_WORKERS=4
    volumes:
      - ./models:/app/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  intelligence-go:
    build:
      context: .
      dockerfile: Dockerfile.go
    ports:
      - "8082:8082"
    environment:
      - PYTHON_SERVICE_URL=http://intelligence-python:8081
    depends_on:
      - intelligence-python
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8082/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - ./dashboards:/etc/grafana/provisioning/dashboards
```

```dockerfile
# Dockerfile.python
FROM python:3.10-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download spaCy model
RUN python -m spacy download en_core_web_sm

# Copy application
COPY intelligence/ ./intelligence/

# Run service
CMD ["python", "-m", "intelligence.service"]
```

```python
# requirements.txt
pandas==2.0.3
numpy==1.24.3
scipy==1.11.1
scikit-learn==1.3.0
statsmodels==0.14.0
ruptures==1.1.8
spacy==3.6.0
flask==2.3.2
prometheus-client==0.17.1
```

## Key Deliverables

1. **Pattern Detection Engine** with statistical, time series, anomaly, and correlation detection
2. **Query Generation** from natural language with intent parsing and optimization
3. **Visualization Intelligence** with data shape analysis and recommendations
4. **ML Model Registry** for managing and deploying custom models
5. **Python Service** with REST API for all intelligence operations
6. **Go Service Wrapper** for production integration
7. **Comprehensive Testing** including unit tests and benchmarks
8. **Docker Deployment** with monitoring and health checks

## Success Metrics

- Detects 10+ pattern types with >80% accuracy
- Generates valid NRQL queries from natural language 90% of the time
- Recommends appropriate visualizations based on data shape
- Handles datasets up to 1M rows efficiently through sampling
- Sub-second response times for most operations
- Easy integration with other UDS components via REST API

This implementation provides the intelligence layer that makes UDS truly smart - able to understand data, detect patterns, generate queries, and recommend visualizations without human intervention.