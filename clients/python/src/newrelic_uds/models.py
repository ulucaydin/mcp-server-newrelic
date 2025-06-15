"""Data models for the New Relic UDS client."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, ConfigDict


class ClientConfig(BaseModel):
    """Configuration for the UDS client."""
    
    base_url: str = "http://localhost:8080/api/v1"
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_retries: int = 3
    retry_wait: float = 1.0
    retry_max_wait: float = 30.0
    user_agent: str = "newrelic-uds-python/1.0.0"
    
    model_config = ConfigDict(validate_assignment=True)


class APIError(Exception):
    """API error response."""
    
    def __init__(
        self,
        error: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        self.error = error
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)


class HealthStatus(BaseModel):
    """Health status of the API."""
    
    status: str
    version: str
    uptime: str
    components: Dict[str, Dict[str, Any]]


# Discovery models
class AttributeStatistics(BaseModel):
    """Statistics for a schema attribute."""
    
    null_count: int
    distinct_count: int
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    avg_value: Optional[Any] = None


class SchemaAttribute(BaseModel):
    """Attribute within a schema."""
    
    name: str
    data_type: str
    nullable: bool
    cardinality: int
    sample_values: Optional[List[Any]] = None
    statistics: Optional[AttributeStatistics] = None


class QualityMetrics(BaseModel):
    """Quality metrics for a schema."""
    
    overall_score: float
    completeness: float
    consistency: float
    validity: float
    uniqueness: float
    details: Optional[Dict[str, Any]] = None


class Schema(BaseModel):
    """Data schema information."""
    
    name: str
    event_type: str
    attributes: List[SchemaAttribute]
    record_count: int
    first_seen: datetime
    last_seen: datetime
    quality: QualityMetrics
    metadata: Optional[Dict[str, Any]] = None


class DiscoveryMetadata(BaseModel):
    """Metadata for discovery operations."""
    
    total_schemas: int
    execution_time: str
    cache_hit: bool
    filters: Optional[Dict[str, Any]] = None


class ListSchemasOptions(BaseModel):
    """Options for listing schemas."""
    
    event_type: Optional[str] = None
    min_record_count: Optional[int] = None
    max_schemas: Optional[int] = None
    sort_by: Optional[str] = None
    include_metadata: Optional[bool] = None


class ListSchemasResponse(BaseModel):
    """Response from listing schemas."""
    
    schemas: List[Schema]
    metadata: Optional[DiscoveryMetadata] = None


# Pattern models
class Pattern(BaseModel):
    """Query pattern."""
    
    id: str
    name: str
    description: str
    query: str
    category: str
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class SearchPatternsOptions(BaseModel):
    """Options for searching patterns."""
    
    query: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class SearchPatternsResponse(BaseModel):
    """Response from searching patterns."""
    
    patterns: List[Pattern]
    total: int
    metadata: Optional[Dict[str, Any]] = None


# Query models
class TimeRange(BaseModel):
    """Time range for queries."""
    
    from_time: str = Field(alias="from")
    to_time: str = Field(alias="to")


class QueryOptions(BaseModel):
    """Options for query execution."""
    
    timeout: Optional[int] = None
    max_results: Optional[int] = None
    include_metadata: Optional[bool] = None


class QueryRequest(BaseModel):
    """Request to execute a query."""
    
    query: str
    time_range: Optional[TimeRange] = None
    variables: Optional[Dict[str, Any]] = None
    options: Optional[QueryOptions] = None


class Column(BaseModel):
    """Column information in query results."""
    
    name: str
    type: str
    nullable: Optional[bool] = None


class QueryResult(BaseModel):
    """Single query result set."""
    
    data: List[Any]
    columns: Optional[List[Column]] = None
    total_count: Optional[int] = None


class QueryMetadata(BaseModel):
    """Metadata for query execution."""
    
    execution_time: str
    bytes_processed: Optional[int] = None
    cached: Optional[bool] = None
    warnings: Optional[List[str]] = None


class QueryResponse(BaseModel):
    """Response from query execution."""
    
    results: List[QueryResult]
    metadata: Optional[QueryMetadata] = None


# Dashboard models
class Position(BaseModel):
    """Widget position on dashboard."""
    
    x: int
    y: int


class Size(BaseModel):
    """Widget size on dashboard."""
    
    width: int
    height: int


class VisualizationType(str, Enum):
    """Types of visualizations."""
    
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    TABLE = "table"
    GAUGE = "gauge"
    HEATMAP = "heatmap"
    SCATTER = "scatter"


class VisualizationConfig(BaseModel):
    """Configuration for widget visualization."""
    
    type: Union[VisualizationType, str]
    options: Optional[Dict[str, Any]] = None


class Widget(BaseModel):
    """Dashboard widget."""
    
    id: str
    type: str
    title: str
    query: str
    visualization: VisualizationConfig
    position: Optional[Position] = None
    size: Optional[Size] = None


class LayoutType(str, Enum):
    """Dashboard layout types."""
    
    GRID = "grid"
    FREEFORM = "freeform"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


class LayoutConfig(BaseModel):
    """Dashboard layout configuration."""
    
    type: Union[LayoutType, str]
    columns: Optional[int] = None
    rows: Optional[int] = None


class DashboardVariable(BaseModel):
    """Dashboard variable for parameterization."""
    
    name: str
    type: str
    default_value: Optional[Any] = None
    options: Optional[List[Any]] = None


class Dashboard(BaseModel):
    """Dashboard definition."""
    
    id: str
    name: str
    description: Optional[str] = None
    widgets: List[Widget]
    layout: Optional[LayoutConfig] = None
    variables: Optional[List[DashboardVariable]] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime


class ListDashboardsOptions(BaseModel):
    """Options for listing dashboards."""
    
    search: Optional[str] = None
    tags: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None


class ListDashboardsResponse(BaseModel):
    """Response from listing dashboards."""
    
    dashboards: List[Dashboard]
    total: int
    metadata: Optional[Dict[str, Any]] = None