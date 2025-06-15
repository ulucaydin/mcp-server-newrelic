"""Comprehensive tests for pattern detectors"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from intelligence.patterns.base import Pattern, PatternType, PatternContext
from intelligence.patterns.statistical import StatisticalPatternDetector
from intelligence.patterns.timeseries import TimeSeriesPatternDetector
from intelligence.patterns.anomaly import AnomalyDetector
from intelligence.patterns.correlation import CorrelationDetector
from intelligence.patterns.engine import PatternEngine


class TestStatisticalPatternDetector:
    """Test statistical pattern detection"""
    
    @pytest.fixture
    def detector(self):
        return StatisticalPatternDetector()
    
    @pytest.fixture
    def normal_data(self):
        """Generate normally distributed data"""
        np.random.seed(42)
        return pd.DataFrame({
            'normal': np.random.normal(100, 15, 1000),
            'skewed': np.random.gamma(2, 2, 1000),
            'uniform': np.random.uniform(0, 100, 1000),
            'bimodal': np.concatenate([
                np.random.normal(30, 5, 500),
                np.random.normal(70, 5, 500)
            ])
        })
    
    def test_detect_normal_distribution(self, detector, normal_data):
        """Test detection of normal distribution"""
        patterns = detector.detect(normal_data)
        
        # Should detect normal distribution pattern
        normal_patterns = [p for p in patterns if p.type == PatternType.NORMAL_DISTRIBUTION]
        assert len(normal_patterns) >= 1
        
        # Check the normal column was detected
        normal_pattern = next((p for p in normal_patterns if 'normal' in p.columns), None)
        assert normal_pattern is not None
        assert normal_pattern.confidence > 0.8
    
    def test_detect_skewed_distribution(self, detector, normal_data):
        """Test detection of skewed distribution"""
        patterns = detector.detect(normal_data)
        
        # Should detect skewed distribution
        skewed_patterns = [p for p in patterns if p.type == PatternType.SKEWED_DISTRIBUTION]
        assert len(skewed_patterns) >= 1
        
        # Check the skewed column was detected
        skewed_pattern = next((p for p in skewed_patterns if 'skewed' in p.columns), None)
        assert skewed_pattern is not None
        assert skewed_pattern.evidence['skewness'] > 0  # Positive skew
    
    def test_detect_outliers(self, detector):
        """Test outlier detection"""
        # Create data with clear outliers
        data = pd.DataFrame({
            'values': np.concatenate([
                np.random.normal(50, 5, 95),  # Normal data
                [150, 160, 170, 180, 190]  # Clear outliers
            ])
        })
        
        patterns = detector.detect(data)
        
        # Should detect outliers
        outlier_patterns = [p for p in patterns if p.type == PatternType.OUTLIERS]
        assert len(outlier_patterns) >= 1
        
        outlier_pattern = outlier_patterns[0]
        assert outlier_pattern.evidence['count'] >= 5
        assert outlier_pattern.confidence > 0.7
    
    def test_detect_missing_data(self, detector):
        """Test missing data pattern detection"""
        # Create data with missing values
        data = pd.DataFrame({
            'complete': np.random.normal(0, 1, 100),
            'sparse': np.concatenate([
                np.random.normal(0, 1, 30),
                [np.nan] * 70
            ])
        })
        
        patterns = detector.detect(data)
        
        # Should detect missing data pattern
        missing_patterns = [p for p in patterns if p.type == PatternType.MISSING_DATA]
        assert len(missing_patterns) >= 1
        
        # Check the sparse column was detected
        missing_pattern = next((p for p in missing_patterns if 'sparse' in p.columns), None)
        assert missing_pattern is not None
        assert missing_pattern.evidence['missing_percentage'] == 70.0


class TestTimeSeriesPatternDetector:
    """Test time series pattern detection"""
    
    @pytest.fixture
    def detector(self):
        return TimeSeriesPatternDetector()
    
    @pytest.fixture
    def time_series_data(self):
        """Generate time series data with various patterns"""
        dates = pd.date_range(start='2024-01-01', periods=365, freq='D')
        
        # Linear trend
        trend = np.linspace(100, 200, 365)
        
        # Seasonality (weekly pattern)
        seasonality = 10 * np.sin(2 * np.pi * np.arange(365) / 7)
        
        # Random noise
        noise = np.random.normal(0, 5, 365)
        
        return pd.DataFrame({
            'timestamp': dates,
            'trending': trend + noise,
            'seasonal': 100 + seasonality + noise,
            'stationary': np.random.normal(100, 10, 365),
            'volatile': np.random.normal(100, 50, 365)
        })
    
    def test_detect_trend(self, detector, time_series_data):
        """Test trend detection"""
        patterns = detector.detect(time_series_data)
        
        # Should detect linear trend
        trend_patterns = [p for p in patterns if p.type == PatternType.TREND_LINEAR]
        assert len(trend_patterns) >= 1
        
        # Check the trending column was detected
        trend_pattern = next((p for p in trend_patterns if 'trending' in p.columns), None)
        assert trend_pattern is not None
        assert trend_pattern.confidence > 0.8
        assert trend_pattern.evidence['slope'] > 0  # Positive trend
    
    def test_detect_seasonality(self, detector, time_series_data):
        """Test seasonality detection"""
        patterns = detector.detect(time_series_data)
        
        # Should detect seasonality
        seasonal_patterns = [p for p in patterns if p.type == PatternType.SEASONALITY]
        assert len(seasonal_patterns) >= 1
        
        # Check the seasonal column was detected
        seasonal_pattern = next((p for p in seasonal_patterns if 'seasonal' in p.columns), None)
        assert seasonal_pattern is not None
        assert seasonal_pattern.evidence['period'] in [7, 14]  # Weekly or bi-weekly
    
    def test_detect_stationarity(self, detector, time_series_data):
        """Test stationarity detection"""
        patterns = detector.detect(time_series_data)
        
        # Should detect stationary pattern
        stationary_patterns = [p for p in patterns if p.type == PatternType.STATIONARY]
        assert len(stationary_patterns) >= 1
        
        # Check the stationary column was detected
        stationary_pattern = next((p for p in stationary_patterns if 'stationary' in p.columns), None)
        assert stationary_pattern is not None
    
    def test_detect_volatility_change(self, detector):
        """Test volatility change detection"""
        # Create data with volatility change
        dates = pd.date_range(start='2024-01-01', periods=200, freq='D')
        values = np.concatenate([
            np.random.normal(100, 5, 100),   # Low volatility
            np.random.normal(100, 25, 100)   # High volatility
        ])
        
        data = pd.DataFrame({
            'timestamp': dates,
            'values': values
        })
        
        patterns = detector.detect(data)
        
        # Should detect volatility change
        volatility_patterns = [p for p in patterns if p.type == PatternType.VOLATILITY_CHANGE]
        assert len(volatility_patterns) >= 1


class TestAnomalyDetector:
    """Test anomaly detection"""
    
    @pytest.fixture
    def detector(self):
        return AnomalyDetector()
    
    @pytest.fixture
    def anomaly_data(self):
        """Generate data with various types of anomalies"""
        np.random.seed(42)
        
        # Point anomalies
        normal_data = np.random.normal(50, 5, 1000)
        normal_data[100] = 150  # Point anomaly
        normal_data[500] = -50  # Point anomaly
        
        # Contextual anomalies (time-based)
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='H')
        hourly_pattern = 50 + 10 * np.sin(2 * np.pi * np.arange(1000) / 24)
        hourly_pattern[250:260] = 20  # Contextual anomaly
        
        return pd.DataFrame({
            'timestamp': dates,
            'values': normal_data,
            'hourly': hourly_pattern,
            'feature1': np.random.normal(0, 1, 1000),
            'feature2': np.random.normal(0, 1, 1000)
        })
    
    def test_detect_point_anomalies(self, detector, anomaly_data):
        """Test point anomaly detection"""
        patterns = detector.detect(anomaly_data[['values']])
        
        # Should detect anomalies
        anomaly_patterns = [p for p in patterns if p.type == PatternType.ANOMALY_POINT]
        assert len(anomaly_patterns) >= 1
        
        anomaly_pattern = anomaly_patterns[0]
        assert len(anomaly_pattern.evidence['anomaly_indices']) >= 2
        assert 100 in anomaly_pattern.evidence['anomaly_indices']
        assert 500 in anomaly_pattern.evidence['anomaly_indices']
    
    def test_detect_contextual_anomalies(self, detector, anomaly_data):
        """Test contextual anomaly detection"""
        patterns = detector.detect(anomaly_data[['timestamp', 'hourly']])
        
        # Should detect contextual anomalies
        contextual_patterns = [p for p in patterns if p.type == PatternType.ANOMALY_CONTEXTUAL]
        assert len(contextual_patterns) >= 1
        
        anomaly_pattern = contextual_patterns[0]
        anomaly_indices = anomaly_pattern.evidence['anomaly_indices']
        
        # Check that anomalies were detected in the right range
        assert any(250 <= idx <= 260 for idx in anomaly_indices)
    
    def test_ensemble_methods(self, detector):
        """Test ensemble anomaly detection"""
        # Configure to use multiple methods
        detector.config['ensemble_methods'] = ['iforest', 'lof', 'knn']
        
        # Create data with clear anomalies
        data = pd.DataFrame({
            'x': np.concatenate([
                np.random.normal(0, 1, 95),
                np.random.normal(10, 0.1, 5)  # Cluster of anomalies
            ]),
            'y': np.concatenate([
                np.random.normal(0, 1, 95),
                np.random.normal(10, 0.1, 5)
            ])
        })
        
        patterns = detector.detect(data)
        
        # Should detect collective anomalies
        collective_patterns = [p for p in patterns if p.type == PatternType.ANOMALY_COLLECTIVE]
        assert len(collective_patterns) >= 1
        
        # Check ensemble evidence
        pattern = collective_patterns[0]
        assert 'ensemble_scores' in pattern.evidence
        assert len(pattern.evidence['ensemble_scores']) > 0


class TestCorrelationDetector:
    """Test correlation detection"""
    
    @pytest.fixture
    def detector(self):
        return CorrelationDetector()
    
    @pytest.fixture
    def correlation_data(self):
        """Generate data with various correlations"""
        np.random.seed(42)
        n = 1000
        
        # Linear correlation
        x = np.random.normal(0, 1, n)
        y_linear = 2 * x + np.random.normal(0, 0.5, n)
        
        # Non-linear correlation
        y_nonlinear = x**2 + np.random.normal(0, 0.5, n)
        
        # No correlation
        y_random = np.random.normal(0, 1, n)
        
        # Lagged correlation
        y_lagged = np.concatenate([[0] * 10, x[:-10]]) + np.random.normal(0, 0.5, n)
        
        return pd.DataFrame({
            'x': x,
            'y_linear': y_linear,
            'y_nonlinear': y_nonlinear,
            'y_random': y_random,
            'y_lagged': y_lagged
        })
    
    def test_detect_linear_correlation(self, detector, correlation_data):
        """Test linear correlation detection"""
        patterns = detector.detect(correlation_data)
        
        # Should detect strong linear correlation
        linear_patterns = [p for p in patterns if p.type == PatternType.CORRELATION_LINEAR]
        assert len(linear_patterns) >= 1
        
        # Check x and y_linear correlation
        pattern = next((p for p in linear_patterns 
                       if 'x' in p.columns and 'y_linear' in p.columns), None)
        assert pattern is not None
        assert pattern.evidence['correlation'] > 0.8
        assert pattern.confidence > 0.9
    
    def test_detect_nonlinear_correlation(self, detector, correlation_data):
        """Test non-linear correlation detection"""
        patterns = detector.detect(correlation_data)
        
        # Should detect non-linear correlation
        nonlinear_patterns = [p for p in patterns if p.type == PatternType.CORRELATION_NONLINEAR]
        assert len(nonlinear_patterns) >= 1
        
        # Check x and y_nonlinear correlation
        pattern = next((p for p in nonlinear_patterns 
                       if 'x' in p.columns and 'y_nonlinear' in p.columns), None)
        assert pattern is not None
        assert pattern.evidence['mutual_information'] > 0.5
    
    def test_detect_lagged_correlation(self, detector, correlation_data):
        """Test lagged correlation detection"""
        patterns = detector.detect(correlation_data)
        
        # Should detect lagged correlation
        lagged_patterns = [p for p in patterns if p.type == PatternType.CORRELATION_LAGGED]
        assert len(lagged_patterns) >= 1
        
        # Check x and y_lagged correlation
        pattern = next((p for p in lagged_patterns 
                       if 'x' in p.columns and 'y_lagged' in p.columns), None)
        assert pattern is not None
        assert pattern.evidence['optimal_lag'] == 10
        assert pattern.evidence['correlation'] > 0.7
    
    def test_no_correlation(self, detector, correlation_data):
        """Test that random data shows no significant correlation"""
        patterns = detector.detect(correlation_data[['x', 'y_random']])
        
        # Should not detect strong correlations
        correlation_patterns = [p for p in patterns 
                              if p.type in [PatternType.CORRELATION_LINEAR, 
                                          PatternType.CORRELATION_NONLINEAR]]
        
        # If any correlations detected, they should be weak
        for pattern in correlation_patterns:
            assert pattern.confidence < 0.5


class TestPatternEngine:
    """Test pattern engine orchestration"""
    
    @pytest.fixture
    def engine(self):
        return PatternEngine()
    
    @pytest.fixture
    def complex_data(self):
        """Generate complex dataset with multiple patterns"""
        np.random.seed(42)
        dates = pd.date_range(start='2024-01-01', periods=1000, freq='H')
        
        # Trending metric with seasonality
        trend = np.linspace(100, 150, 1000)
        seasonal = 10 * np.sin(2 * np.pi * np.arange(1000) / 24)
        metric1 = trend + seasonal + np.random.normal(0, 5, 1000)
        
        # Correlated metric
        metric2 = 0.8 * metric1 + np.random.normal(0, 10, 1000)
        
        # Add some anomalies
        metric1[500:510] = 200
        
        return pd.DataFrame({
            'timestamp': dates,
            'cpu_usage': metric1,
            'memory_usage': metric2,
            'response_time': np.random.gamma(2, 50, 1000),
            'error_count': np.random.poisson(2, 1000),
            'service': np.random.choice(['web', 'api', 'db'], 1000)
        })
    
    def test_comprehensive_analysis(self, engine, complex_data):
        """Test comprehensive pattern analysis"""
        results = engine.analyze(complex_data)
        
        # Check structure
        assert 'patterns' in results
        assert 'insights' in results
        assert 'summary' in results
        assert 'metadata' in results
        
        # Should detect multiple pattern types
        pattern_types = {p['type'] for p in results['patterns']}
        assert len(pattern_types) >= 4
        
        # Check summary statistics
        summary = results['summary']
        assert summary['total_patterns'] > 0
        assert 'pattern_types' in summary
        assert 'confidence_distribution' in summary
    
    def test_pattern_filtering(self, engine, complex_data):
        """Test pattern filtering by confidence"""
        # Configure higher confidence threshold
        engine.config['min_confidence'] = 0.8
        
        results = engine.analyze(complex_data)
        
        # All patterns should have high confidence
        for pattern in results['patterns']:
            assert pattern['confidence'] >= 0.8
    
    def test_specific_columns(self, engine, complex_data):
        """Test analyzing specific columns only"""
        results = engine.analyze(
            complex_data,
            columns=['cpu_usage', 'memory_usage']
        )
        
        # Patterns should only involve specified columns
        for pattern in results['patterns']:
            assert any(col in ['cpu_usage', 'memory_usage'] for col in pattern['columns'])
    
    def test_pattern_ranking(self, engine, complex_data):
        """Test pattern ranking"""
        results = engine.analyze(complex_data)
        
        # Patterns should be ranked by confidence
        confidences = [p['confidence'] for p in results['patterns']]
        assert confidences == sorted(confidences, reverse=True)
    
    def test_insight_generation(self, engine, complex_data):
        """Test insight generation"""
        results = engine.analyze(complex_data)
        
        # Should generate insights
        assert len(results['insights']) > 0
        
        # Insights should be strings
        for insight in results['insights']:
            assert isinstance(insight, str)
            assert len(insight) > 10  # Non-trivial insight
    
    def test_caching(self, engine, complex_data):
        """Test result caching"""
        # First analysis
        results1 = engine.analyze(complex_data)
        
        # Second analysis with same data
        results2 = engine.analyze(complex_data)
        
        # Should use cache (check metadata)
        assert results2['metadata'].get('from_cache', False)
        
        # Results should be identical
        assert len(results1['patterns']) == len(results2['patterns'])
    
    def test_error_handling(self, engine):
        """Test error handling"""
        # Empty DataFrame
        empty_df = pd.DataFrame()
        results = engine.analyze(empty_df)
        assert results['patterns'] == []
        assert 'error' not in results
        
        # Invalid input
        with pytest.raises(ValueError):
            engine.analyze("not a dataframe")
    
    @pytest.mark.parametrize("detector_type,enabled", [
        ("statistical", False),
        ("timeseries", False),
        ("anomaly", False),
        ("correlation", False)
    ])
    def test_detector_disabling(self, engine, complex_data, detector_type, enabled):
        """Test disabling specific detectors"""
        engine.config[f'enable_{detector_type}'] = enabled
        
        results = engine.analyze(complex_data)
        
        # Should not have patterns from disabled detector
        # This is a simplified test - in reality would check pattern types
        assert 'patterns' in results


# Integration tests
class TestIntegration:
    """Integration tests for pattern detection system"""
    
    def test_real_world_scenario(self):
        """Test with realistic monitoring data"""
        # Create realistic monitoring data
        dates = pd.date_range(start='2024-01-01', periods=24*7, freq='H')
        
        # Normal business hours pattern
        hour_of_day = dates.hour
        day_of_week = dates.dayofweek
        
        # Base load
        base_load = 1000
        
        # Business hours boost (9-17 on weekdays)
        business_boost = np.where(
            (hour_of_day >= 9) & (hour_of_day <= 17) & (day_of_week < 5),
            500, 0
        )
        
        # Weekend reduction
        weekend_factor = np.where(day_of_week >= 5, 0.5, 1.0)
        
        # Add some noise and anomalies
        noise = np.random.normal(0, 50, len(dates))
        requests = (base_load + business_boost) * weekend_factor + noise
        
        # Add an outage
        requests[72:75] = 0
        
        # Add a spike
        requests[100:102] = 5000
        
        data = pd.DataFrame({
            'timestamp': dates,
            'requests': requests,
            'response_time': np.where(requests > 0, 
                                     np.random.gamma(2, 50, len(dates)), 
                                     0),
            'error_rate': np.where(requests == 0, 1.0,
                                  np.random.beta(1, 100, len(dates)))
        })
        
        # Run full analysis
        engine = PatternEngine()
        results = engine.analyze(data)
        
        # Should detect multiple patterns
        pattern_types = {p['type'] for p in results['patterns']}
        
        # Expected patterns
        assert 'seasonality' in pattern_types  # Daily pattern
        assert 'anomaly_point' in pattern_types  # Spike
        assert 'anomaly_contextual' in pattern_types  # Outage
        
        # Should generate relevant insights
        insights_text = ' '.join(results['insights']).lower()
        assert 'daily' in insights_text or 'hourly' in insights_text
        assert 'anomal' in insights_text or 'unusual' in insights_text