"""Data Shape Analyzer - Analyzes data characteristics to inform visualization choices"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger


class DataType(Enum):
    """Types of data for visualization purposes"""
    NUMERIC_CONTINUOUS = "numeric_continuous"
    NUMERIC_DISCRETE = "numeric_discrete"
    CATEGORICAL_NOMINAL = "categorical_nominal"
    CATEGORICAL_ORDINAL = "categorical_ordinal"
    TEMPORAL = "temporal"
    GEOGRAPHIC = "geographic"
    TEXT = "text"
    BOOLEAN = "boolean"
    MIXED = "mixed"


class DistributionType(Enum):
    """Common distribution patterns"""
    NORMAL = "normal"
    SKEWED_LEFT = "skewed_left"
    SKEWED_RIGHT = "skewed_right"
    BIMODAL = "bimodal"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    POWER_LAW = "power_law"
    UNKNOWN = "unknown"


class TrendType(Enum):
    """Trend patterns in data"""
    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    CYCLIC = "cyclic"
    SEASONAL = "seasonal"
    VOLATILE = "volatile"
    NO_TREND = "no_trend"


@dataclass
class DataCharacteristics:
    """Detailed characteristics of a data column"""
    name: str
    data_type: DataType
    cardinality: int
    null_percentage: float
    unique_percentage: float
    
    # Numeric characteristics
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    distribution_type: Optional[DistributionType] = None
    outlier_percentage: Optional[float] = None
    
    # Temporal characteristics
    time_range: Optional[Tuple[datetime, datetime]] = None
    frequency: Optional[str] = None
    trend_type: Optional[TrendType] = None
    seasonality_period: Optional[int] = None
    
    # Categorical characteristics
    top_categories: List[Tuple[str, float]] = field(default_factory=list)
    category_distribution: Optional[str] = None  # "balanced", "imbalanced", "dominant"
    
    # Relationships
    correlations: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'name': self.name,
            'data_type': self.data_type.value,
            'cardinality': self.cardinality,
            'null_percentage': self.null_percentage,
            'unique_percentage': self.unique_percentage,
            'numeric_stats': {
                'min': self.min_value,
                'max': self.max_value,
                'mean': self.mean,
                'median': self.median,
                'std_dev': self.std_dev,
                'distribution': self.distribution_type.value if self.distribution_type else None,
                'outlier_percentage': self.outlier_percentage
            } if self.data_type == DataType.NUMERIC_CONTINUOUS else None,
            'temporal_stats': {
                'time_range': [self.time_range[0].isoformat(), self.time_range[1].isoformat()] if self.time_range else None,
                'frequency': self.frequency,
                'trend': self.trend_type.value if self.trend_type else None,
                'seasonality_period': self.seasonality_period
            } if self.data_type == DataType.TEMPORAL else None,
            'categorical_stats': {
                'top_categories': self.top_categories,
                'distribution': self.category_distribution
            } if self.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL] else None,
            'correlations': self.correlations
        }


@dataclass
class DataShape:
    """Overall shape and characteristics of a dataset"""
    row_count: int
    column_count: int
    column_characteristics: List[DataCharacteristics]
    has_time_series: bool
    time_column: Optional[str] = None
    primary_metrics: List[str] = field(default_factory=list)
    primary_dimensions: List[str] = field(default_factory=list)
    data_quality_score: float = 1.0
    
    # Analysis metadata
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    analysis_duration: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def get_numeric_columns(self) -> List[str]:
        """Get list of numeric column names"""
        return [
            char.name for char in self.column_characteristics
            if char.data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]
        ]
    
    def get_categorical_columns(self) -> List[str]:
        """Get list of categorical column names"""
        return [
            char.name for char in self.column_characteristics
            if char.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'row_count': self.row_count,
            'column_count': self.column_count,
            'columns': [col.to_dict() for col in self.column_characteristics],
            'has_time_series': self.has_time_series,
            'time_column': self.time_column,
            'primary_metrics': self.primary_metrics,
            'primary_dimensions': self.primary_dimensions,
            'data_quality_score': self.data_quality_score,
            'analysis_metadata': {
                'timestamp': self.analysis_timestamp.isoformat(),
                'duration': self.analysis_duration,
                'warnings': self.warnings
            }
        }


class DataShapeAnalyzer:
    """Analyzes data shape and characteristics for visualization purposes"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.sample_size = self.config.get('sample_size', 10000)
        self.correlation_threshold = self.config.get('correlation_threshold', 0.5)
        self.outlier_method = self.config.get('outlier_method', 'iqr')
        
    def analyze(self, 
               data: pd.DataFrame,
               target_columns: Optional[List[str]] = None) -> DataShape:
        """
        Analyze data shape and characteristics
        
        Args:
            data: DataFrame to analyze
            target_columns: Specific columns to focus on (None = all)
            
        Returns:
            DataShape object with analysis results
        """
        start_time = datetime.utcnow()
        warnings = []
        
        # Sample if data is too large
        if len(data) > self.sample_size:
            logger.info(f"Sampling {self.sample_size} rows from {len(data)} total")
            data = data.sample(n=self.sample_size, random_state=42)
            warnings.append(f"Analysis based on sample of {self.sample_size} rows")
        
        # Select columns to analyze
        if target_columns:
            columns_to_analyze = [col for col in target_columns if col in data.columns]
        else:
            columns_to_analyze = list(data.columns)
        
        # Analyze each column
        column_characteristics = []
        for col in columns_to_analyze:
            char = self._analyze_column(data[col], data)
            column_characteristics.append(char)
        
        # Detect time series
        has_time_series, time_column = self._detect_time_series(data)
        
        # Identify primary metrics and dimensions
        primary_metrics = self._identify_primary_metrics(column_characteristics)
        primary_dimensions = self._identify_primary_dimensions(column_characteristics)
        
        # Calculate data quality score
        quality_score = self._calculate_quality_score(column_characteristics)
        
        # Create DataShape
        shape = DataShape(
            row_count=len(data),
            column_count=len(columns_to_analyze),
            column_characteristics=column_characteristics,
            has_time_series=has_time_series,
            time_column=time_column,
            primary_metrics=primary_metrics,
            primary_dimensions=primary_dimensions,
            data_quality_score=quality_score,
            analysis_duration=(datetime.utcnow() - start_time).total_seconds(),
            warnings=warnings
        )
        
        return shape
    
    def _analyze_column(self, 
                       series: pd.Series,
                       full_data: pd.DataFrame) -> DataCharacteristics:
        """Analyze a single column"""
        
        # Basic stats
        name = str(series.name)
        cardinality = series.nunique()
        null_percentage = series.isna().sum() / len(series)
        unique_percentage = cardinality / len(series)
        
        # Determine data type
        data_type = self._determine_data_type(series)
        
        # Create base characteristics
        char = DataCharacteristics(
            name=name,
            data_type=data_type,
            cardinality=cardinality,
            null_percentage=null_percentage,
            unique_percentage=unique_percentage
        )
        
        # Analyze based on data type
        if data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            self._analyze_numeric(series, char)
        elif data_type == DataType.TEMPORAL:
            self._analyze_temporal(series, char)
        elif data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
            self._analyze_categorical(series, char)
        elif data_type == DataType.BOOLEAN:
            self._analyze_boolean(series, char)
        
        # Calculate correlations with other numeric columns
        if data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
            char.correlations = self._calculate_correlations(series, full_data)
        
        return char
    
    def _determine_data_type(self, series: pd.Series) -> DataType:
        """Determine the visualization-relevant data type"""
        
        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return DataType.TEMPORAL
        
        # Check for boolean
        if pd.api.types.is_bool_dtype(series):
            return DataType.BOOLEAN
        
        # Check for numeric
        if pd.api.types.is_numeric_dtype(series):
            # Distinguish between continuous and discrete
            unique_ratio = series.nunique() / len(series)
            if unique_ratio < 0.05 and series.nunique() < 20:
                return DataType.NUMERIC_DISCRETE
            else:
                return DataType.NUMERIC_CONTINUOUS
        
        # Check for geographic (simple heuristic)
        if isinstance(series.iloc[0], str):
            sample_values = series.dropna().head(100)
            if any(val in ['lat', 'latitude', 'lon', 'longitude', 'country', 'state', 'city'] 
                   for val in [series.name.lower()]):
                return DataType.GEOGRAPHIC
        
        # Default to categorical
        if series.nunique() < len(series) * 0.5:
            # Could add logic to detect ordinal vs nominal
            return DataType.CATEGORICAL_NOMINAL
        
        return DataType.TEXT
    
    def _analyze_numeric(self, series: pd.Series, char: DataCharacteristics):
        """Analyze numeric column"""
        clean_series = series.dropna()
        
        if len(clean_series) == 0:
            return
        
        # Basic statistics
        char.min_value = float(clean_series.min())
        char.max_value = float(clean_series.max())
        char.mean = float(clean_series.mean())
        char.median = float(clean_series.median())
        char.std_dev = float(clean_series.std())
        
        # Distribution type
        char.distribution_type = self._detect_distribution(clean_series)
        
        # Outliers
        outliers = self._detect_outliers(clean_series)
        char.outlier_percentage = len(outliers) / len(clean_series)
    
    def _analyze_temporal(self, series: pd.Series, char: DataCharacteristics):
        """Analyze temporal column"""
        clean_series = series.dropna()
        
        if len(clean_series) == 0:
            return
        
        # Time range
        char.time_range = (clean_series.min(), clean_series.max())
        
        # Frequency detection
        if len(clean_series) > 1:
            # Try to infer frequency
            try:
                freq = pd.infer_freq(clean_series)
                char.frequency = freq
            except:
                pass
        
        # For trend analysis, would need associated values
        # This is a placeholder
        char.trend_type = TrendType.NO_TREND
    
    def _analyze_categorical(self, series: pd.Series, char: DataCharacteristics):
        """Analyze categorical column"""
        # Top categories
        value_counts = series.value_counts()
        total = len(series)
        
        # Get top 10 categories with percentages
        top_10 = value_counts.head(10)
        char.top_categories = [(str(cat), count/total) for cat, count in top_10.items()]
        
        # Distribution type
        if len(value_counts) == 1:
            char.category_distribution = "single_value"
        elif value_counts.iloc[0] / total > 0.8:
            char.category_distribution = "dominant"
        elif value_counts.std() / value_counts.mean() < 0.5:
            char.category_distribution = "balanced"
        else:
            char.category_distribution = "imbalanced"
    
    def _analyze_boolean(self, series: pd.Series, char: DataCharacteristics):
        """Analyze boolean column"""
        # Treat as special categorical
        char.data_type = DataType.BOOLEAN
        true_pct = series.sum() / len(series)
        char.top_categories = [("True", true_pct), ("False", 1 - true_pct)]
        
        if true_pct > 0.9 or true_pct < 0.1:
            char.category_distribution = "dominant"
        else:
            char.category_distribution = "balanced"
    
    def _detect_distribution(self, series: pd.Series) -> DistributionType:
        """Detect distribution type of numeric data"""
        
        # Calculate skewness and kurtosis
        skewness = series.skew()
        kurtosis = series.kurtosis()
        
        # Simple heuristics for distribution detection
        if abs(skewness) < 0.5 and abs(kurtosis) < 1:
            return DistributionType.NORMAL
        elif skewness > 1:
            return DistributionType.SKEWED_RIGHT
        elif skewness < -1:
            return DistributionType.SKEWED_LEFT
        elif abs(kurtosis) > 3:
            # High kurtosis might indicate bimodal
            return DistributionType.BIMODAL
        elif series.std() / series.mean() < 0.1:
            return DistributionType.UNIFORM
        else:
            return DistributionType.UNKNOWN
    
    def _detect_outliers(self, series: pd.Series) -> pd.Series:
        """Detect outliers in numeric data"""
        
        if self.outlier_method == 'iqr':
            Q1 = series.quantile(0.25)
            Q3 = series.quantile(0.75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            return series[(series < lower_bound) | (series > upper_bound)]
        
        elif self.outlier_method == 'zscore':
            z_scores = np.abs((series - series.mean()) / series.std())
            return series[z_scores > 3]
        
        return pd.Series()
    
    def _calculate_correlations(self, 
                              series: pd.Series,
                              full_data: pd.DataFrame) -> Dict[str, float]:
        """Calculate correlations with other numeric columns"""
        correlations = {}
        
        for col in full_data.columns:
            if col == series.name:
                continue
            
            if pd.api.types.is_numeric_dtype(full_data[col]):
                try:
                    corr = series.corr(full_data[col])
                    if abs(corr) > self.correlation_threshold:
                        correlations[col] = round(corr, 3)
                except:
                    pass
        
        return correlations
    
    def _detect_time_series(self, data: pd.DataFrame) -> Tuple[bool, Optional[str]]:
        """Detect if data has time series characteristics"""
        
        # Check index first
        if isinstance(data.index, pd.DatetimeIndex):
            return True, 'index'
        
        # Check columns
        for col in data.columns:
            if pd.api.types.is_datetime64_any_dtype(data[col]):
                return True, col
        
        # Check for timestamp-like column names
        time_keywords = ['time', 'date', 'timestamp', 'datetime', 'created', 'updated']
        for col in data.columns:
            if any(keyword in col.lower() for keyword in time_keywords):
                try:
                    # Try to parse as datetime
                    pd.to_datetime(data[col].head(10))
                    return True, col
                except:
                    pass
        
        return False, None
    
    def _identify_primary_metrics(self, 
                                characteristics: List[DataCharacteristics]) -> List[str]:
        """Identify primary metric columns"""
        metrics = []
        
        # Look for numeric columns with certain patterns
        metric_keywords = ['count', 'sum', 'total', 'amount', 'value', 'score', 
                          'rate', 'ratio', 'percentage', 'duration', 'latency',
                          'cpu', 'memory', 'disk', 'network']
        
        for char in characteristics:
            if char.data_type in [DataType.NUMERIC_CONTINUOUS, DataType.NUMERIC_DISCRETE]:
                # Check if name contains metric keywords
                name_lower = char.name.lower()
                if any(keyword in name_lower for keyword in metric_keywords):
                    metrics.append(char.name)
                # Also include high-variance numeric columns
                elif char.std_dev and char.mean and char.std_dev / char.mean > 0.1:
                    metrics.append(char.name)
        
        return metrics[:5]  # Limit to top 5
    
    def _identify_primary_dimensions(self,
                                   characteristics: List[DataCharacteristics]) -> List[str]:
        """Identify primary dimension columns"""
        dimensions = []
        
        # Look for categorical columns with reasonable cardinality
        dimension_keywords = ['name', 'type', 'category', 'group', 'class', 
                            'status', 'region', 'country', 'department']
        
        for char in characteristics:
            if char.data_type in [DataType.CATEGORICAL_NOMINAL, DataType.CATEGORICAL_ORDINAL]:
                # Good dimensions have moderate cardinality
                if 2 <= char.cardinality <= 50:
                    # Check name patterns
                    name_lower = char.name.lower()
                    if any(keyword in name_lower for keyword in dimension_keywords):
                        dimensions.append(char.name)
                    # Or if well-distributed
                    elif char.category_distribution == "balanced":
                        dimensions.append(char.name)
        
        return dimensions[:5]  # Limit to top 5
    
    def _calculate_quality_score(self,
                               characteristics: List[DataCharacteristics]) -> float:
        """Calculate overall data quality score"""
        
        if not characteristics:
            return 0.0
        
        scores = []
        
        for char in characteristics:
            # Penalize high null percentage
            null_penalty = 1 - char.null_percentage
            
            # Penalize single-value columns
            diversity_score = min(1.0, char.unique_percentage * 10) if char.unique_percentage < 0.1 else 1.0
            
            # Penalize extreme outliers in numeric columns
            outlier_penalty = 1.0
            if char.outlier_percentage is not None:
                outlier_penalty = 1 - min(0.5, char.outlier_percentage * 5)
            
            # Calculate column score
            column_score = null_penalty * diversity_score * outlier_penalty
            scores.append(column_score)
        
        return sum(scores) / len(scores)