"""NRQL Query Builder - Constructs syntactically correct NRQL queries"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import re
from loguru import logger

from .base import (
    QueryIntent, QueryType, QueryEntity, QueryFilter,
    TimeRange, AggregationType, QUERY_TEMPLATES
)


class NRQLBuilder:
    """Builds NRQL queries from structured intents"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.validate_syntax = self.config.get('validate_syntax', True)
        self.auto_optimize = self.config.get('auto_optimize', True)
        
        # NRQL keywords for validation
        self.nrql_keywords = {
            'SELECT', 'FROM', 'WHERE', 'SINCE', 'UNTIL', 'TIMESERIES',
            'FACET', 'LIMIT', 'COMPARE', 'WITH', 'AS', 'BY', 'ORDER',
            'ASC', 'DESC', 'AND', 'OR', 'NOT', 'IN', 'LIKE'
        }
        
        # Reserved field names that need escaping
        self.reserved_fields = {
            'timestamp', 'type', 'name', 'host', 'user', 'message'
        }
    
    def build(self, intent: QueryIntent) -> str:
        """
        Build NRQL query from intent
        
        Args:
            intent: Structured query intent
            
        Returns:
            NRQL query string
        """
        # Select appropriate builder based on query type
        builders = {
            QueryType.SELECT: self._build_select_query,
            QueryType.FACET: self._build_facet_query,
            QueryType.TIMESERIES: self._build_timeseries_query,
            QueryType.PERCENTILE: self._build_percentile_query,
            QueryType.HISTOGRAM: self._build_histogram_query,
            QueryType.RATE: self._build_rate_query,
            QueryType.COMPARE: self._build_compare_query,
            QueryType.FUNNEL: self._build_funnel_query
        }
        
        builder = builders.get(intent.query_type, self._build_select_query)
        query = builder(intent)
        
        # Validate syntax if enabled
        if self.validate_syntax:
            self._validate_query(query)
        
        # Auto-optimize if enabled
        if self.auto_optimize:
            query = self._optimize_query(query, intent)
        
        return query
    
    def _build_select_query(self, intent: QueryIntent) -> str:
        """Build basic SELECT query"""
        parts = []
        
        # SELECT clause
        select_clause = self._build_select_clause(intent.entities)
        parts.append(select_clause)
        
        # FROM clause
        from_clause = self._build_from_clause(intent.event_types)
        parts.append(from_clause)
        
        # WHERE clause
        if intent.filters:
            where_clause = self._build_where_clause(intent.filters)
            parts.append(where_clause)
        
        # Time range
        time_clause = intent.time_range.to_nrql()
        parts.append(time_clause)
        
        # ORDER BY clause
        if intent.order_by:
            order_clause = f"ORDER BY {self._get_order_field(intent)} {intent.order_by}"
            parts.append(order_clause)
        
        # LIMIT clause
        if intent.limit:
            parts.append(f"LIMIT {intent.limit}")
        
        return ' '.join(parts)
    
    def _build_facet_query(self, intent: QueryIntent) -> str:
        """Build FACET query"""
        # Start with basic SELECT query
        base_query = self._build_select_query(intent)
        
        # Remove LIMIT and ORDER BY if present (they go after FACET)
        base_parts = base_query.split()
        query_parts = []
        i = 0
        while i < len(base_parts):
            if base_parts[i] in ['LIMIT', 'ORDER']:
                break
            query_parts.append(base_parts[i])
            i += 1
        
        # Add FACET clause
        if intent.group_by:
            facet_fields = ', '.join(self._escape_field(f) for f in intent.group_by)
            query_parts.append(f"FACET {facet_fields}")
        
        # Re-add ORDER BY and LIMIT after FACET
        if intent.order_by:
            order_field = self._get_order_field(intent)
            query_parts.append(f"ORDER BY {order_field} {intent.order_by}")
        
        if intent.limit:
            query_parts.append(f"LIMIT {intent.limit}")
        
        return ' '.join(query_parts)
    
    def _build_timeseries_query(self, intent: QueryIntent) -> str:
        """Build TIMESERIES query"""
        # Start with basic SELECT query
        base_query = self._build_select_query(intent)
        
        # Insert TIMESERIES before any ORDER BY or LIMIT
        parts = base_query.split()
        timeseries_inserted = False
        result_parts = []
        
        for i, part in enumerate(parts):
            if part in ['ORDER', 'LIMIT'] and not timeseries_inserted:
                result_parts.append('TIMESERIES')
                timeseries_inserted = True
            result_parts.append(part)
        
        if not timeseries_inserted:
            result_parts.append('TIMESERIES')
        
        # Add bucket size if specified
        bucket_size = intent.metadata.get('bucket_size', 'AUTO')
        if bucket_size != 'AUTO':
            # Find TIMESERIES and add bucket size
            for i, part in enumerate(result_parts):
                if part == 'TIMESERIES':
                    result_parts[i] = f'TIMESERIES {bucket_size}'
                    break
        
        return ' '.join(result_parts)
    
    def _build_percentile_query(self, intent: QueryIntent) -> str:
        """Build percentile query"""
        parts = []
        
        # Build SELECT with percentile function
        percentile_entities = []
        percentiles = intent.metadata.get('percentiles', [50, 95, 99])
        
        for entity in intent.entities:
            if entity.aggregation == AggregationType.PERCENTILE:
                for p in percentiles:
                    percentile_entities.append(
                        f"percentile({self._escape_field(entity.name)}, {p}) AS 'p{p}'"
                    )
            else:
                percentile_entities.append(entity.to_nrql_select())
        
        parts.append(f"SELECT {', '.join(percentile_entities)}")
        
        # FROM clause
        parts.append(self._build_from_clause(intent.event_types))
        
        # WHERE clause
        if intent.filters:
            parts.append(self._build_where_clause(intent.filters))
        
        # Time range
        parts.append(intent.time_range.to_nrql())
        
        # FACET if needed
        if intent.group_by:
            facet_fields = ', '.join(self._escape_field(f) for f in intent.group_by)
            parts.append(f"FACET {facet_fields}")
        
        return ' '.join(parts)
    
    def _build_histogram_query(self, intent: QueryIntent) -> str:
        """Build histogram query"""
        parts = []
        
        # Build SELECT with histogram function
        histogram_entities = []
        
        for entity in intent.entities:
            if entity.aggregation == AggregationType.HISTOGRAM:
                bucket_size = intent.metadata.get('bucket_size', 'AUTO')
                if bucket_size == 'AUTO':
                    histogram_entities.append(
                        f"histogram({self._escape_field(entity.name)})"
                    )
                else:
                    histogram_entities.append(
                        f"histogram({self._escape_field(entity.name)}, {bucket_size})"
                    )
            else:
                histogram_entities.append(entity.to_nrql_select())
        
        parts.append(f"SELECT {', '.join(histogram_entities)}")
        
        # Rest of the query
        parts.append(self._build_from_clause(intent.event_types))
        
        if intent.filters:
            parts.append(self._build_where_clause(intent.filters))
        
        parts.append(intent.time_range.to_nrql())
        
        return ' '.join(parts)
    
    def _build_rate_query(self, intent: QueryIntent) -> str:
        """Build rate calculation query"""
        parts = []
        
        # Build SELECT with rate function
        rate_entities = []
        rate_interval = intent.metadata.get('rate_interval', '1 minute')
        
        for entity in intent.entities:
            if entity.aggregation == AggregationType.RATE:
                if entity.name == '*':
                    rate_entities.append(f"rate(count(*), {rate_interval})")
                else:
                    rate_entities.append(
                        f"rate(sum({self._escape_field(entity.name)}), {rate_interval})"
                    )
            else:
                rate_entities.append(entity.to_nrql_select())
        
        parts.append(f"SELECT {', '.join(rate_entities)}")
        
        # Rest of the query
        parts.append(self._build_from_clause(intent.event_types))
        
        if intent.filters:
            parts.append(self._build_where_clause(intent.filters))
        
        parts.append(intent.time_range.to_nrql())
        
        # Rate queries typically need TIMESERIES
        parts.append('TIMESERIES')
        
        return ' '.join(parts)
    
    def _build_compare_query(self, intent: QueryIntent) -> str:
        """Build COMPARE WITH query"""
        # Start with base query
        base_query = self._build_select_query(intent)
        
        # Add COMPARE WITH clause
        compare_period = intent.metadata.get('compare_period', '1 week')
        compare_query = f"{base_query} COMPARE WITH {compare_period} ago"
        
        return compare_query
    
    def _build_funnel_query(self, intent: QueryIntent) -> str:
        """Build funnel query"""
        # Funnel queries are complex and need step definitions
        steps = intent.metadata.get('funnel_steps', [])
        
        if not steps:
            # Fall back to regular query
            return self._build_select_query(intent)
        
        parts = []
        parts.append("SELECT funnel(")
        
        # Build step definitions
        step_defs = []
        for i, step in enumerate(steps):
            step_def = f"  step{i+1} AS '{step['name']}' WHERE {step['condition']}"
            step_defs.append(step_def)
        
        parts.append(',\n'.join(step_defs))
        parts.append(")")
        
        # FROM clause
        parts.append(self._build_from_clause(intent.event_types))
        
        # Time range
        parts.append(intent.time_range.to_nrql())
        
        return ' '.join(parts)
    
    def _build_select_clause(self, entities: List[QueryEntity]) -> str:
        """Build SELECT clause from entities"""
        if not entities:
            return "SELECT count(*)"
        
        select_items = []
        for entity in entities:
            # Handle special case for count(*)
            if entity.name == '*' and entity.aggregation == AggregationType.COUNT:
                select_items.append('count(*)')
            else:
                select_items.append(self._format_entity(entity))
        
        return f"SELECT {', '.join(select_items)}"
    
    def _build_from_clause(self, event_types: List[str]) -> str:
        """Build FROM clause"""
        if not event_types:
            return "FROM Transaction"  # Default
        
        # Escape event type names if needed
        escaped_types = [self._escape_event_type(et) for et in event_types]
        
        if len(escaped_types) == 1:
            return f"FROM {escaped_types[0]}"
        else:
            return f"FROM {', '.join(escaped_types)}"
    
    def _build_where_clause(self, filters: List[QueryFilter]) -> str:
        """Build WHERE clause from filters"""
        if not filters:
            return ""
        
        conditions = []
        for filter in filters:
            condition = self._format_filter(filter)
            conditions.append(condition)
        
        return f"WHERE {' AND '.join(conditions)}"
    
    def _format_entity(self, entity: QueryEntity) -> str:
        """Format a single entity for SELECT clause"""
        field_name = self._escape_field(entity.name)
        
        if entity.aggregation:
            # Apply aggregation function
            if entity.aggregation == AggregationType.UNIQUE_COUNT:
                expr = f"uniqueCount({field_name})"
            else:
                expr = f"{entity.aggregation.value}({field_name})"
        else:
            expr = field_name
        
        # Add alias if specified
        if entity.alias:
            expr += f" AS '{entity.alias}'"
        
        return expr
    
    def _format_filter(self, filter: QueryFilter) -> str:
        """Format a single filter condition"""
        field = self._escape_field(filter.field)
        
        if isinstance(filter.value, list):
            # Handle IN/NOT IN operators
            values = []
            for v in filter.value:
                if isinstance(v, str):
                    values.append(f"'{self._escape_string(v)}'")
                else:
                    values.append(str(v))
            return f"{field} {filter.operator} ({', '.join(values)})"
        
        elif isinstance(filter.value, str):
            if filter.operator in ['LIKE', 'NOT LIKE']:
                # LIKE operators use % wildcards
                return f"{field} {filter.operator} '{self._escape_string(filter.value)}'"
            else:
                return f"{field} {filter.operator} '{self._escape_string(filter.value)}'"
        
        else:
            # Numeric values
            return f"{field} {filter.operator} {filter.value}"
    
    def _escape_field(self, field: str) -> str:
        """Escape field name if needed"""
        # Check if field needs escaping
        if field.lower() in self.reserved_fields or ' ' in field or '-' in field:
            return f'`{field}`'
        return field
    
    def _escape_event_type(self, event_type: str) -> str:
        """Escape event type name if needed"""
        # Event types with spaces or special chars need backticks
        if ' ' in event_type or '-' in event_type:
            return f'`{event_type}`'
        return event_type
    
    def _escape_string(self, value: str) -> str:
        """Escape string value for NRQL"""
        # Escape single quotes
        return value.replace("'", "\\'")
    
    def _get_order_field(self, intent: QueryIntent) -> str:
        """Determine field to order by"""
        # If specific order field is set
        if intent.metadata.get('order_field'):
            return self._escape_field(intent.metadata['order_field'])
        
        # Order by first aggregated field
        for entity in intent.entities:
            if entity.aggregation:
                if entity.alias:
                    return f"'{entity.alias}'"
                else:
                    return self._format_entity(entity)
        
        # Default to count
        return 'count(*)'
    
    def _validate_query(self, query: str) -> bool:
        """Basic NRQL syntax validation"""
        # Check for required components
        if 'SELECT' not in query:
            logger.warning("Query missing SELECT clause")
            return False
        
        if 'FROM' not in query:
            logger.warning("Query missing FROM clause")
            return False
        
        # Check for balanced quotes
        single_quotes = query.count("'")
        if single_quotes % 2 != 0:
            logger.warning("Unbalanced single quotes in query")
            return False
        
        # Check for balanced parentheses
        if query.count('(') != query.count(')'):
            logger.warning("Unbalanced parentheses in query")
            return False
        
        return True
    
    def _optimize_query(self, query: str, intent: QueryIntent) -> str:
        """Apply query optimizations"""
        # Add LIMIT if not present and query might return many results
        if 'LIMIT' not in query and 'TIMESERIES' not in query:
            # Add reasonable default limit
            query += ' LIMIT 100'
        
        # Optimize time ranges for better performance
        if 'SINCE 1 month ago' in query and not any(
            keyword in query for keyword in ['TIMESERIES', 'FACET', 'rate(']
        ):
            # For simple queries, suggest shorter time range
            logger.info("Consider using shorter time range for better performance")
        
        return query
    
    def build_from_template(self, template_name: str, params: Dict[str, Any]) -> Optional[str]:
        """Build query from a predefined template"""
        template = QUERY_TEMPLATES.get(template_name)
        
        if not template:
            logger.error(f"Template '{template_name}' not found")
            return None
        
        if not template.validate_parameters(params):
            logger.error(f"Missing required parameters for template '{template_name}'")
            return None
        
        try:
            query = template.fill(**params)
            if self.validate_syntax:
                self._validate_query(query)
            return query
        except Exception as e:
            logger.error(f"Error building query from template: {e}")
            return None