"""Natural Language Intent Parser for converting user queries to structured intents"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import spacy
from spacy.matcher import Matcher
from loguru import logger

from .base import (
    QueryIntent, QueryType, IntentType, TimeRange, TimeRangeType,
    QueryEntity, QueryFilter, AggregationType
)


class IntentParser:
    """Parses natural language queries into structured intents"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Load spaCy model (small model for efficiency)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except:
            logger.warning("spaCy model not found, using basic parsing")
            self.nlp = None
        
        # Initialize pattern matchers
        self.time_patterns = self._compile_time_patterns()
        self.aggregation_patterns = self._compile_aggregation_patterns()
        self.filter_patterns = self._compile_filter_patterns()
        self.intent_keywords = self._load_intent_keywords()
        
    def parse(self, query: str, context: Optional[Dict[str, Any]] = None) -> QueryIntent:
        """
        Parse natural language query into structured intent
        
        Args:
            query: Natural language query string
            context: Optional context with available schemas, etc.
            
        Returns:
            Parsed QueryIntent
        """
        query = query.strip()
        
        # Detect intent type
        intent_type = self._detect_intent_type(query)
        
        # Extract components
        time_range = self._extract_time_range(query)
        entities = self._extract_entities(query, context)
        event_types = self._extract_event_types(query, context)
        filters = self._extract_filters(query)
        group_by = self._extract_group_by(query)
        
        # Determine query type
        query_type = self._determine_query_type(query, entities, group_by)
        
        # Extract additional parameters
        limit = self._extract_limit(query)
        order_by = self._extract_order_by(query)
        
        # Calculate confidence
        confidence = self._calculate_confidence(query, entities, event_types)
        
        return QueryIntent(
            intent_type=intent_type,
            query_type=query_type,
            entities=entities,
            event_types=event_types,
            filters=filters,
            time_range=time_range,
            group_by=group_by,
            order_by=order_by,
            limit=limit,
            confidence=confidence,
            raw_query=query,
            metadata={'parser_version': '1.0'}
        )
    
    def _detect_intent_type(self, query: str) -> IntentType:
        """Detect high-level intent from query"""
        query_lower = query.lower()
        
        # Check for specific intent keywords
        if any(word in query_lower for word in ['explore', 'show me', 'what is', 'list']):
            return IntentType.EXPLORE
        elif any(word in query_lower for word in ['monitor', 'watch', 'track', 'real-time']):
            return IntentType.MONITOR
        elif any(word in query_lower for word in ['analyze', 'investigate', 'deep dive', 'understand']):
            return IntentType.ANALYZE
        elif any(word in query_lower for word in ['compare', 'versus', 'vs', 'difference']):
            return IntentType.COMPARE
        elif any(word in query_lower for word in ['troubleshoot', 'debug', 'error', 'issue', 'problem']):
            return IntentType.TROUBLESHOOT
        elif any(word in query_lower for word in ['forecast', 'predict', 'trend', 'projection']):
            return IntentType.FORECAST
        elif any(word in query_lower for word in ['alert', 'notify', 'warn', 'threshold']):
            return IntentType.ALERT
        elif any(word in query_lower for word in ['report', 'summary', 'dashboard']):
            return IntentType.REPORT
        else:
            return IntentType.EXPLORE  # Default
    
    def _extract_time_range(self, query: str) -> TimeRange:
        """Extract time range from query"""
        query_lower = query.lower()
        
        # Check for common time expressions
        for pattern, time_type in self.time_patterns:
            match = pattern.search(query_lower)
            if match:
                if time_type == TimeRangeType.LAST_HOUR:
                    return TimeRange(type=time_type)
                elif time_type == TimeRangeType.LAST_DAY:
                    return TimeRange(type=time_type)
                elif time_type == TimeRangeType.LAST_WEEK:
                    return TimeRange(type=time_type)
                elif time_type == TimeRangeType.LAST_MONTH:
                    return TimeRange(type=time_type)
                elif time_type == TimeRangeType.RELATIVE:
                    # Extract the relative expression
                    duration_match = re.search(r'(\d+)\s*(hour|day|week|month|minute)s?', query_lower)
                    if duration_match:
                        num = int(duration_match.group(1))
                        unit = duration_match.group(2)
                        return TimeRange(
                            type=TimeRangeType.RELATIVE,
                            relative_expression=f"SINCE {num} {unit}{'s' if num > 1 else ''} ago"
                        )
        
        # Default to last hour
        return TimeRange(type=TimeRangeType.LAST_HOUR)
    
    def _extract_entities(self, query: str, context: Optional[Dict[str, Any]]) -> List[QueryEntity]:
        """Extract metrics and attributes from query"""
        entities = []
        query_lower = query.lower()
        
        # Common metric patterns
        metric_keywords = {
            'response time': ('duration', AggregationType.AVERAGE),
            'latency': ('duration', AggregationType.AVERAGE),
            'error rate': ('error', AggregationType.RATE),
            'error count': ('error', AggregationType.COUNT),
            'throughput': ('count', AggregationType.RATE),
            'cpu': ('cpuPercent', AggregationType.AVERAGE),
            'memory': ('memoryUsedPercent', AggregationType.AVERAGE),
            'count': ('*', AggregationType.COUNT),
            'total': ('*', AggregationType.COUNT),
            'average': (None, AggregationType.AVERAGE),
            'sum': (None, AggregationType.SUM),
            'max': (None, AggregationType.MAX),
            'min': (None, AggregationType.MIN)
        }
        
        # Check for metric keywords
        for keyword, (metric, agg) in metric_keywords.items():
            if keyword in query_lower:
                # Try to find what to aggregate
                if metric is None:
                    # Look for metric name after aggregation
                    pattern = rf'{keyword}\s+(?:of\s+)?(\w+)'
                    match = re.search(pattern, query_lower)
                    if match:
                        metric = match.group(1)
                
                if metric:
                    entities.append(QueryEntity(
                        name=metric,
                        type='metric',
                        aggregation=agg
                    ))
        
        # If no specific entities found, default to count
        if not entities:
            entities.append(QueryEntity(
                name='*',
                type='metric',
                aggregation=AggregationType.COUNT
            ))
        
        return entities
    
    def _extract_event_types(self, query: str, context: Optional[Dict[str, Any]]) -> List[str]:
        """Extract event types from query"""
        event_types = []
        query_lower = query.lower()
        
        # Common event type mappings
        event_type_keywords = {
            'transaction': 'Transaction',
            'error': 'TransactionError',
            'log': 'Log',
            'metric': 'Metric',
            'span': 'Span',
            'trace': 'Span',
            'browser': 'PageView',
            'mobile': 'Mobile',
            'synthetic': 'SyntheticCheck',
            'infrastructure': 'SystemSample',
            'process': 'ProcessSample'
        }
        
        # Check for event type keywords
        for keyword, event_type in event_type_keywords.items():
            if keyword in query_lower:
                event_types.append(event_type)
        
        # Check context for available schemas
        if context and 'available_schemas' in context:
            for schema in context['available_schemas']:
                schema_name_lower = schema.get('name', '').lower()
                if schema_name_lower in query_lower:
                    event_types.append(schema['name'])
        
        # Default to Transaction if no specific type found
        if not event_types:
            event_types.append('Transaction')
        
        return event_types
    
    def _extract_filters(self, query: str) -> List[QueryFilter]:
        """Extract filter conditions from query"""
        filters = []
        query_lower = query.lower()
        
        # Common filter patterns
        filter_patterns = [
            # where X = Y
            (r'where\s+(\w+)\s*=\s*["\']?([^"\']+)["\']?', '='),
            # X equals Y
            (r'(\w+)\s+equals?\s+["\']?([^"\']+)["\']?', '='),
            # X is Y
            (r'(\w+)\s+is\s+["\']?([^"\']+)["\']?', '='),
            # greater than
            (r'(\w+)\s+greater\s+than\s+(\d+)', '>'),
            # less than
            (r'(\w+)\s+less\s+than\s+(\d+)', '<'),
            # containing
            (r'(\w+)\s+containing\s+["\']?([^"\']+)["\']?', 'LIKE'),
            # not containing
            (r'(\w+)\s+not\s+containing\s+["\']?([^"\']+)["\']?', 'NOT LIKE')
        ]
        
        for pattern, operator in filter_patterns:
            matches = re.finditer(pattern, query_lower)
            for match in matches:
                field = match.group(1)
                value = match.group(2)
                
                # Try to parse numeric values
                try:
                    value = int(value)
                except:
                    try:
                        value = float(value)
                    except:
                        pass  # Keep as string
                
                filters.append(QueryFilter(
                    field=field,
                    operator=operator,
                    value=value
                ))
        
        # Check for specific service/app filters
        app_pattern = r'(?:for|from|in)\s+(?:app|application|service)\s+["\']?([^"\']+)["\']?'
        app_match = re.search(app_pattern, query_lower)
        if app_match:
            filters.append(QueryFilter(
                field='appName',
                operator='=',
                value=app_match.group(1)
            ))
        
        return filters
    
    def _extract_group_by(self, query: str) -> List[str]:
        """Extract group by fields from query"""
        group_by = []
        query_lower = query.lower()
        
        # Look for explicit group by
        group_pattern = r'(?:group\s+by|grouped\s+by|by)\s+(\w+(?:\s*,\s*\w+)*)'
        match = re.search(group_pattern, query_lower)
        if match:
            fields = match.group(1).split(',')
            group_by.extend([f.strip() for f in fields])
        
        # Look for facet indicators
        facet_keywords = ['per', 'by', 'for each', 'breakdown by']
        for keyword in facet_keywords:
            pattern = rf'{keyword}\s+(\w+)'
            match = re.search(pattern, query_lower)
            if match and match.group(1) not in group_by:
                group_by.append(match.group(1))
        
        return group_by
    
    def _determine_query_type(self, query: str, entities: List[QueryEntity], group_by: List[str]) -> QueryType:
        """Determine the type of query based on components"""
        query_lower = query.lower()
        
        # Check for specific query type indicators
        if 'timeseries' in query_lower or 'over time' in query_lower:
            return QueryType.TIMESERIES
        elif 'percentile' in query_lower:
            return QueryType.PERCENTILE
        elif 'histogram' in query_lower or 'distribution' in query_lower:
            return QueryType.HISTOGRAM
        elif 'rate' in query_lower:
            return QueryType.RATE
        elif 'compare' in query_lower or 'versus' in query_lower:
            return QueryType.COMPARE
        elif 'funnel' in query_lower:
            return QueryType.FUNNEL
        elif group_by:
            return QueryType.FACET
        else:
            return QueryType.SELECT
    
    def _extract_limit(self, query: str) -> Optional[int]:
        """Extract limit from query"""
        limit_patterns = [
            r'(?:top|first|limit)\s+(\d+)',
            r'(\d+)\s+(?:results?|records?|rows?)'
        ]
        
        for pattern in limit_patterns:
            match = re.search(pattern, query.lower())
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_order_by(self, query: str) -> Optional[str]:
        """Extract order by clause from query"""
        query_lower = query.lower()
        
        # Look for sorting indicators
        if 'highest' in query_lower or 'most' in query_lower or 'descending' in query_lower:
            return 'DESC'
        elif 'lowest' in query_lower or 'least' in query_lower or 'ascending' in query_lower:
            return 'ASC'
        
        return None
    
    def _calculate_confidence(self, query: str, entities: List[QueryEntity], event_types: List[str]) -> float:
        """Calculate confidence score for the parsed intent"""
        confidence = 1.0
        
        # Reduce confidence if query is vague
        vague_terms = ['something', 'anything', 'stuff', 'things']
        for term in vague_terms:
            if term in query.lower():
                confidence *= 0.8
        
        # Reduce confidence if no specific entities found
        if all(e.name == '*' for e in entities):
            confidence *= 0.9
        
        # Reduce confidence if using default event type
        if event_types == ['Transaction']:
            confidence *= 0.95
        
        # Increase confidence for explicit indicators
        explicit_terms = ['select', 'from', 'where', 'group by']
        for term in explicit_terms:
            if term in query.lower():
                confidence = min(1.0, confidence * 1.1)
        
        return max(0.1, min(1.0, confidence))
    
    def _compile_time_patterns(self) -> List[Tuple[re.Pattern, TimeRangeType]]:
        """Compile regular expressions for time extraction"""
        return [
            (re.compile(r'last\s+hour|past\s+hour|previous\s+hour'), TimeRangeType.LAST_HOUR),
            (re.compile(r'last\s+day|past\s+day|yesterday|previous\s+day'), TimeRangeType.LAST_DAY),
            (re.compile(r'last\s+week|past\s+week|previous\s+week'), TimeRangeType.LAST_WEEK),
            (re.compile(r'last\s+month|past\s+month|previous\s+month'), TimeRangeType.LAST_MONTH),
            (re.compile(r'last\s+(\d+)\s*(hour|day|week|month|minute)s?'), TimeRangeType.RELATIVE),
            (re.compile(r'since\s+(\d+)\s*(hour|day|week|month|minute)s?\s+ago'), TimeRangeType.RELATIVE)
        ]
    
    def _compile_aggregation_patterns(self) -> Dict[str, AggregationType]:
        """Compile aggregation keyword mappings"""
        return {
            'count': AggregationType.COUNT,
            'total': AggregationType.COUNT,
            'sum': AggregationType.SUM,
            'average': AggregationType.AVERAGE,
            'avg': AggregationType.AVERAGE,
            'mean': AggregationType.AVERAGE,
            'max': AggregationType.MAX,
            'maximum': AggregationType.MAX,
            'min': AggregationType.MIN,
            'minimum': AggregationType.MIN,
            'unique': AggregationType.UNIQUE_COUNT,
            'distinct': AggregationType.UNIQUE_COUNT,
            'latest': AggregationType.LATEST,
            'rate': AggregationType.RATE
        }
    
    def _compile_filter_patterns(self) -> List[Tuple[str, str]]:
        """Compile filter extraction patterns"""
        return [
            (r'where\s+(\w+)\s*=\s*["\']?([^"\']+)["\']?', '='),
            (r'(\w+)\s+equals?\s+["\']?([^"\']+)["\']?', '='),
            (r'(\w+)\s+is\s+["\']?([^"\']+)["\']?', '='),
            (r'(\w+)\s+greater\s+than\s+(\d+)', '>'),
            (r'(\w+)\s+less\s+than\s+(\d+)', '<')
        ]
    
    def _load_intent_keywords(self) -> Dict[IntentType, List[str]]:
        """Load keywords for intent detection"""
        return {
            IntentType.EXPLORE: ['explore', 'show', 'list', 'what', 'display'],
            IntentType.MONITOR: ['monitor', 'watch', 'track', 'real-time', 'live'],
            IntentType.ANALYZE: ['analyze', 'investigate', 'understand', 'deep dive'],
            IntentType.COMPARE: ['compare', 'versus', 'vs', 'difference', 'contrast'],
            IntentType.TROUBLESHOOT: ['troubleshoot', 'debug', 'error', 'issue', 'problem'],
            IntentType.FORECAST: ['forecast', 'predict', 'trend', 'projection', 'future'],
            IntentType.ALERT: ['alert', 'notify', 'warn', 'threshold', 'trigger'],
            IntentType.REPORT: ['report', 'summary', 'dashboard', 'overview']
        }