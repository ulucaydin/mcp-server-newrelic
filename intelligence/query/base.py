"""Base classes and types for query generation"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Union
from pydantic import BaseModel, Field as PydanticField


class QueryType(Enum):
    """Types of queries that can be generated"""
    SELECT = "select"
    FACET = "facet"
    TIMESERIES = "timeseries"
    FUNNEL = "funnel"
    HISTOGRAM = "histogram"
    PERCENTILE = "percentile"
    RATE = "rate"
    COMPARE = "compare"


class TimeRangeType(Enum):
    """Common time range patterns"""
    LAST_HOUR = "last_hour"
    LAST_DAY = "last_day"
    LAST_WEEK = "last_week"
    LAST_MONTH = "last_month"
    LAST_QUARTER = "last_quarter"
    CUSTOM = "custom"
    RELATIVE = "relative"
    ABSOLUTE = "absolute"


class AggregationType(Enum):
    """Aggregation functions"""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    PERCENTILE = "percentile"
    UNIQUE_COUNT = "uniqueCount"
    LATEST = "latest"
    RATE = "rate"
    HISTOGRAM = "histogram"


class IntentType(Enum):
    """High-level user intents"""
    EXPLORE = "explore"  # General data exploration
    MONITOR = "monitor"  # Real-time monitoring
    ANALYZE = "analyze"  # Deep analysis
    COMPARE = "compare"  # Comparison analysis
    TROUBLESHOOT = "troubleshoot"  # Problem investigation
    FORECAST = "forecast"  # Predictive analysis
    ALERT = "alert"  # Alert creation
    REPORT = "report"  # Reporting


@dataclass
class TimeRange:
    """Represents a time range for queries"""
    type: TimeRangeType
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    duration: Optional[timedelta] = None
    relative_expression: Optional[str] = None  # e.g., "SINCE 1 hour ago"
    
    def to_nrql(self) -> str:
        """Convert to NRQL time clause"""
        if self.type == TimeRangeType.LAST_HOUR:
            return "SINCE 1 hour ago"
        elif self.type == TimeRangeType.LAST_DAY:
            return "SINCE 1 day ago"
        elif self.type == TimeRangeType.LAST_WEEK:
            return "SINCE 1 week ago"
        elif self.type == TimeRangeType.LAST_MONTH:
            return "SINCE 1 month ago"
        elif self.type == TimeRangeType.LAST_QUARTER:
            return "SINCE 3 months ago"
        elif self.type == TimeRangeType.RELATIVE and self.relative_expression:
            return self.relative_expression
        elif self.type == TimeRangeType.ABSOLUTE and self.start and self.end:
            # Format: SINCE '2024-01-01 00:00:00' UNTIL '2024-01-02 00:00:00'
            return f"SINCE '{self.start.strftime('%Y-%m-%d %H:%M:%S')}' UNTIL '{self.end.strftime('%Y-%m-%d %H:%M:%S')}'"
        else:
            return "SINCE 1 hour ago"  # Default


@dataclass
class QueryEntity:
    """Represents an entity in a query (metric, attribute, etc.)"""
    name: str
    type: str  # metric, attribute, event_type
    aggregation: Optional[AggregationType] = None
    alias: Optional[str] = None
    filters: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_nrql_select(self) -> str:
        """Convert to NRQL SELECT expression"""
        if self.aggregation:
            expr = f"{self.aggregation.value}({self.name})"
        else:
            expr = self.name
            
        if self.alias:
            expr += f" AS '{self.alias}'"
            
        return expr


@dataclass
class QueryFilter:
    """Represents a filter condition"""
    field: str
    operator: str  # =, !=, >, <, >=, <=, IN, NOT IN, LIKE, NOT LIKE
    value: Union[str, int, float, List[Any]]
    
    def to_nrql(self) -> str:
        """Convert to NRQL WHERE clause"""
        if isinstance(self.value, list):
            values = ", ".join([f"'{v}'" if isinstance(v, str) else str(v) for v in self.value])
            return f"{self.field} {self.operator} ({values})"
        elif isinstance(self.value, str):
            return f"{self.field} {self.operator} '{self.value}'"
        else:
            return f"{self.field} {self.operator} {self.value}"


@dataclass
class QueryIntent:
    """Parsed user intent for query generation"""
    intent_type: IntentType
    query_type: QueryType
    entities: List[QueryEntity]
    event_types: List[str]
    filters: List[QueryFilter]
    time_range: TimeRange
    group_by: List[str] = field(default_factory=list)
    order_by: Optional[str] = None
    limit: Optional[int] = None
    confidence: float = 1.0
    raw_query: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_primary_event_type(self) -> Optional[str]:
        """Get the primary event type for the query"""
        return self.event_types[0] if self.event_types else None
    
    def has_aggregation(self) -> bool:
        """Check if query has any aggregation"""
        return any(entity.aggregation for entity in self.entities)


@dataclass
class QueryContext:
    """Context information for query generation"""
    available_schemas: List[Dict[str, Any]]
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    cost_constraints: Optional[Dict[str, Any]] = None
    performance_hints: Optional[Dict[str, Any]] = None
    previous_queries: List[str] = field(default_factory=list)
    domain_knowledge: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Result of query generation"""
    nrql: str
    intent: QueryIntent
    confidence: float
    estimated_cost: Optional[float] = None
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'nrql': self.nrql,
            'intent_type': self.intent.intent_type.value,
            'query_type': self.intent.query_type.value,
            'confidence': self.confidence,
            'estimated_cost': self.estimated_cost,
            'warnings': self.warnings,
            'suggestions': self.suggestions,
            'alternatives': self.alternatives,
            'metadata': self.metadata
        }


class QueryTemplate:
    """Template for common query patterns"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 query_type: QueryType,
                 template: str,
                 parameters: List[str],
                 examples: List[Dict[str, Any]]):
        self.name = name
        self.description = description
        self.query_type = query_type
        self.template = template
        self.parameters = parameters
        self.examples = examples
    
    def fill(self, **kwargs) -> str:
        """Fill template with parameters"""
        return self.template.format(**kwargs)
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Validate that all required parameters are provided"""
        return all(param in params for param in self.parameters)


# Common query templates
QUERY_TEMPLATES = {
    'basic_count': QueryTemplate(
        name='basic_count',
        description='Count events over time',
        query_type=QueryType.SELECT,
        template='SELECT count(*) FROM {event_type} {time_range}',
        parameters=['event_type', 'time_range'],
        examples=[
            {'event_type': 'Transaction', 'time_range': 'SINCE 1 hour ago'}
        ]
    ),
    
    'faceted_count': QueryTemplate(
        name='faceted_count',
        description='Count events grouped by attribute',
        query_type=QueryType.FACET,
        template='SELECT count(*) FROM {event_type} {time_range} FACET {facet_field}',
        parameters=['event_type', 'time_range', 'facet_field'],
        examples=[
            {'event_type': 'Transaction', 'time_range': 'SINCE 1 hour ago', 'facet_field': 'appName'}
        ]
    ),
    
    'timeseries': QueryTemplate(
        name='timeseries',
        description='Time series data',
        query_type=QueryType.TIMESERIES,
        template='SELECT {aggregation}({metric}) FROM {event_type} {time_range} TIMESERIES',
        parameters=['aggregation', 'metric', 'event_type', 'time_range'],
        examples=[
            {
                'aggregation': 'average',
                'metric': 'duration',
                'event_type': 'Transaction',
                'time_range': 'SINCE 1 hour ago'
            }
        ]
    ),
    
    'percentile': QueryTemplate(
        name='percentile',
        description='Calculate percentiles',
        query_type=QueryType.PERCENTILE,
        template='SELECT percentile({metric}, {percentiles}) FROM {event_type} {time_range}',
        parameters=['metric', 'percentiles', 'event_type', 'time_range'],
        examples=[
            {
                'metric': 'duration',
                'percentiles': '50, 95, 99',
                'event_type': 'Transaction',
                'time_range': 'SINCE 1 hour ago'
            }
        ]
    ),
    
    'rate_calculation': QueryTemplate(
        name='rate_calculation',
        description='Calculate rate of change',
        query_type=QueryType.RATE,
        template='SELECT rate(count(*), 1 minute) FROM {event_type} {time_range} TIMESERIES',
        parameters=['event_type', 'time_range'],
        examples=[
            {'event_type': 'Transaction', 'time_range': 'SINCE 1 hour ago'}
        ]
    ),
    
    'comparison': QueryTemplate(
        name='comparison',
        description='Compare metrics across time periods',
        query_type=QueryType.COMPARE,
        template='SELECT {aggregation}({metric}) FROM {event_type} {time_range} COMPARE WITH {compare_period} ago',
        parameters=['aggregation', 'metric', 'event_type', 'time_range', 'compare_period'],
        examples=[
            {
                'aggregation': 'average',
                'metric': 'duration',
                'event_type': 'Transaction',
                'time_range': 'SINCE 1 hour ago',
                'compare_period': '1 day'
            }
        ]
    )
}