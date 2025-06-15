"""Query Generator - Main interface for natural language to NRQL conversion"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

from .base import QueryIntent, QueryContext, QueryResult
from .intent_parser import IntentParser
from .nrql_builder import NRQLBuilder
from .query_optimizer import QueryOptimizer


class QueryGenerator:
    """
    Main query generation engine that converts natural language to optimized NRQL
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Initialize components
        self.intent_parser = IntentParser(config.get('parser_config', {}))
        self.nrql_builder = NRQLBuilder(config.get('builder_config', {}))
        self.query_optimizer = QueryOptimizer(config.get('optimizer_config', {}))
        
        # Cache for common queries
        self.query_cache = {}
        self.cache_size = config.get('cache_size', 100)
        
        # Query history for learning
        self.query_history = []
        self.history_size = config.get('history_size', 1000)
    
    def generate(self, 
                natural_query: str,
                context: Optional[QueryContext] = None) -> QueryResult:
        """
        Generate NRQL query from natural language
        
        Args:
            natural_query: Natural language query string
            context: Optional context with schemas, preferences, etc.
            
        Returns:
            QueryResult with NRQL and metadata
        """
        start_time = datetime.utcnow()
        
        # Check cache
        cache_key = self._get_cache_key(natural_query, context)
        if cache_key in self.query_cache:
            logger.info(f"Cache hit for query: {natural_query[:50]}...")
            cached_result = self.query_cache[cache_key]
            cached_result.metadata['cache_hit'] = True
            return cached_result
        
        try:
            # Parse natural language to intent
            intent = self.intent_parser.parse(natural_query, context)
            logger.debug(f"Parsed intent: {intent.intent_type.value}, {intent.query_type.value}")
            
            # Build NRQL from intent
            nrql = self.nrql_builder.build(intent)
            logger.debug(f"Built NRQL: {nrql}")
            
            # Optimize query if context provided
            if context:
                optimized_nrql, optimization_metadata = self.query_optimizer.optimize(
                    nrql, intent, context
                )
                if optimized_nrql != nrql:
                    logger.info("Query optimized")
                    nrql = optimized_nrql
                else:
                    optimization_metadata = {}
            else:
                optimization_metadata = {}
            
            # Estimate cost if possible
            estimated_cost = self._estimate_query_cost(nrql, intent, context)
            
            # Generate warnings and suggestions
            warnings = self._generate_warnings(intent, context)
            suggestions = self._generate_suggestions(intent, context)
            alternatives = self._generate_alternatives(intent, context)
            
            # Create result
            result = QueryResult(
                nrql=nrql,
                intent=intent,
                confidence=intent.confidence,
                estimated_cost=estimated_cost,
                warnings=warnings,
                suggestions=suggestions,
                alternatives=alternatives,
                metadata={
                    'generation_time': (datetime.utcnow() - start_time).total_seconds(),
                    'optimization': optimization_metadata,
                    'cache_hit': False
                }
            )
            
            # Cache result
            self._cache_result(cache_key, result)
            
            # Add to history
            self._add_to_history(natural_query, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating query: {e}")
            # Return error result
            return QueryResult(
                nrql="",
                intent=QueryIntent(
                    intent_type=IntentType.EXPLORE,
                    query_type=QueryType.SELECT,
                    entities=[],
                    event_types=[],
                    filters=[],
                    time_range=TimeRange(type=TimeRangeType.LAST_HOUR),
                    raw_query=natural_query
                ),
                confidence=0.0,
                warnings=[f"Failed to generate query: {str(e)}"],
                metadata={'error': str(e)}
            )
    
    def generate_batch(self,
                      queries: List[str],
                      context: Optional[QueryContext] = None) -> List[QueryResult]:
        """Generate multiple queries in batch"""
        results = []
        
        # Share context across queries for efficiency
        for query in queries:
            result = self.generate(query, context)
            results.append(result)
        
        return results
    
    def suggest_queries(self,
                       partial_query: str,
                       context: Optional[QueryContext] = None) -> List[str]:
        """Suggest query completions based on partial input"""
        suggestions = []
        
        # Common query patterns
        patterns = [
            "Show me {metric} for {service} in the last {time}",
            "What is the average {metric} by {dimension}",
            "Compare {metric} between {period1} and {period2}",
            "Find anomalies in {metric} for {service}",
            "Top 10 {dimension} by {metric}",
            "Error rate for {service} over time",
            "Performance metrics for {application}",
            "Alert when {metric} exceeds {threshold}"
        ]
        
        # Match partial query to patterns
        partial_lower = partial_query.lower()
        
        for pattern in patterns:
            # Simple matching - could be enhanced with fuzzy matching
            pattern_start = pattern.split('{')[0].lower()
            if pattern_start.startswith(partial_lower):
                suggestions.append(pattern)
        
        # Add context-aware suggestions
        if context and context.available_schemas:
            # Suggest queries based on available data
            for schema in context.available_schemas[:5]:
                schema_name = schema.get('name', 'Unknown')
                suggestions.extend([
                    f"Show me all data from {schema_name}",
                    f"What are the top metrics in {schema_name}",
                    f"Analyze patterns in {schema_name}"
                ])
        
        # Learn from history
        if self.query_history:
            for entry in self.query_history[-10:]:
                if entry['query'].lower().startswith(partial_lower):
                    suggestions.append(entry['query'])
        
        # Deduplicate and limit
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique_suggestions.append(s)
        
        return unique_suggestions[:10]
    
    def explain_query(self, nrql: str) -> Dict[str, Any]:
        """Explain what a NRQL query does in natural language"""
        explanation = {
            'summary': '',
            'components': [],
            'data_source': '',
            'time_range': '',
            'aggregations': [],
            'filters': [],
            'grouping': []
        }
        
        # Parse NRQL components
        nrql_upper = nrql.upper()
        
        # Extract SELECT clause
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', nrql_upper)
        if select_match:
            select_clause = select_match.group(1)
            # Parse aggregations
            agg_patterns = {
                'COUNT': 'counting records',
                'SUM': 'summing',
                'AVERAGE': 'averaging',
                'MAX': 'finding maximum',
                'MIN': 'finding minimum',
                'PERCENTILE': 'calculating percentiles'
            }
            
            for agg, desc in agg_patterns.items():
                if agg in select_clause:
                    explanation['aggregations'].append(desc)
        
        # Extract FROM clause
        from_match = re.search(r'FROM\s+(\S+)', nrql)
        if from_match:
            explanation['data_source'] = from_match.group(1)
        
        # Extract time range
        time_patterns = [
            (r'SINCE\s+(\d+\s+\w+\s+ago)', 'Looking at data from {}'),
            (r'SINCE\s+\'([^\']+)\'', 'Data since {}'),
            (r'BETWEEN\s+(.+?)\s+AND\s+(.+?)(?:\s|$)', 'Data between {} and {}')
        ]
        
        for pattern, template in time_patterns:
            match = re.search(pattern, nrql)
            if match:
                explanation['time_range'] = template.format(*match.groups())
                break
        
        # Extract WHERE conditions
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+SINCE|\s+FACET|\s+LIMIT|$)', nrql)
        if where_match:
            conditions = where_match.group(1)
            explanation['filters'].append(f"Filtered by: {conditions}")
        
        # Extract FACET clause
        facet_match = re.search(r'FACET\s+(\S+)', nrql)
        if facet_match:
            explanation['grouping'].append(f"Grouped by {facet_match.group(1)}")
        
        # Generate summary
        summary_parts = []
        
        if explanation['aggregations']:
            summary_parts.append(f"This query is {', '.join(explanation['aggregations'])}")
        else:
            summary_parts.append("This query retrieves")
        
        summary_parts.append(f"data from {explanation['data_source']}")
        
        if explanation['time_range']:
            summary_parts.append(explanation['time_range'].lower())
        
        if explanation['filters']:
            summary_parts.append(f"with filters: {', '.join(explanation['filters'])}")
        
        if explanation['grouping']:
            summary_parts.append(', '.join(explanation['grouping']))
        
        explanation['summary'] = ' '.join(summary_parts) + '.'
        
        return explanation
    
    def _estimate_query_cost(self,
                           nrql: str,
                           intent: QueryIntent,
                           context: Optional[QueryContext]) -> Optional[float]:
        """Estimate query cost based on data volume and complexity"""
        
        if not context or 'available_schemas' not in context:
            return None
        
        # Find matching schema
        primary_event = intent.get_primary_event_type()
        schema_info = None
        
        for schema in context.available_schemas:
            if schema.get('name') == primary_event:
                schema_info = schema
                break
        
        if not schema_info:
            return None
        
        # Base cost factors
        base_cost = 1.0
        
        # Factor 1: Data volume
        records_per_hour = schema_info.get('records_per_hour', 10000)
        hours = self._get_time_range_hours(intent.time_range)
        estimated_records = records_per_hour * hours
        
        # Cost increases with data volume
        volume_factor = min(10.0, estimated_records / 100000)
        
        # Factor 2: Query complexity
        complexity_factor = 1.0
        
        if intent.query_type == QueryType.TIMESERIES:
            complexity_factor *= 1.5
        elif intent.query_type == QueryType.FACET:
            complexity_factor *= 1.2 * len(intent.group_by)
        elif intent.query_type == QueryType.PERCENTILE:
            complexity_factor *= 2.0
        
        # Factor 3: Aggregation complexity
        for entity in intent.entities:
            if entity.aggregation in [AggregationType.PERCENTILE, AggregationType.UNIQUE_COUNT]:
                complexity_factor *= 1.5
        
        # Calculate final cost
        estimated_cost = base_cost * volume_factor * complexity_factor
        
        return round(estimated_cost, 2)
    
    def _get_time_range_hours(self, time_range: TimeRange) -> float:
        """Convert time range to hours"""
        time_map = {
            TimeRangeType.LAST_HOUR: 1,
            TimeRangeType.LAST_DAY: 24,
            TimeRangeType.LAST_WEEK: 168,
            TimeRangeType.LAST_MONTH: 720,
            TimeRangeType.LAST_QUARTER: 2160
        }
        
        return time_map.get(time_range.type, 1)
    
    def _generate_warnings(self,
                         intent: QueryIntent,
                         context: Optional[QueryContext]) -> List[str]:
        """Generate warnings about potential issues"""
        warnings = []
        
        # Check for expensive operations
        if intent.query_type == QueryType.PERCENTILE and self._get_time_range_hours(intent.time_range) > 168:
            warnings.append("Percentile calculations over long time ranges can be expensive")
        
        # Check for high cardinality facets
        if intent.group_by:
            for field in intent.group_by:
                if field in ['userId', 'sessionId', 'requestId']:
                    warnings.append(f"Grouping by {field} may result in high cardinality")
        
        # Check for missing filters on large datasets
        if not intent.filters and self._get_time_range_hours(intent.time_range) > 24:
            warnings.append("Consider adding filters to reduce data volume")
        
        return warnings
    
    def _generate_suggestions(self,
                            intent: QueryIntent,
                            context: Optional[QueryContext]) -> List[str]:
        """Generate suggestions for query improvement"""
        suggestions = []
        
        # Suggest timeseries for time-based analysis
        if 'over time' in intent.raw_query.lower() and intent.query_type != QueryType.TIMESERIES:
            suggestions.append("Consider using TIMESERIES for time-based visualization")
        
        # Suggest percentiles for latency metrics
        for entity in intent.entities:
            if 'duration' in entity.name.lower() or 'latency' in entity.name.lower():
                if entity.aggregation != AggregationType.PERCENTILE:
                    suggestions.append(f"Consider using percentiles for {entity.name} to better understand distribution")
        
        # Suggest appropriate time ranges
        if intent.intent_type == IntentType.TROUBLESHOOT and intent.time_range.type == TimeRangeType.LAST_MONTH:
            suggestions.append("For troubleshooting, consider using a shorter time range for faster results")
        
        return suggestions
    
    def _generate_alternatives(self,
                             intent: QueryIntent,
                             context: Optional[QueryContext]) -> List[str]:
        """Generate alternative queries"""
        alternatives = []
        
        # If no aggregation, suggest one
        if not intent.has_aggregation():
            alt_intent = intent
            alt_intent.entities[0].aggregation = AggregationType.COUNT
            alt_nrql = self.nrql_builder.build(alt_intent)
            alternatives.append(alt_nrql)
        
        # If SELECT, suggest FACET
        if intent.query_type == QueryType.SELECT and context:
            # Find a good facet field from schema
            if context.available_schemas:
                for schema in context.available_schemas:
                    if schema.get('name') == intent.get_primary_event_type():
                        common_facets = schema.get('common_facets', ['appName', 'host'])
                        if common_facets:
                            alt_intent = intent
                            alt_intent.query_type = QueryType.FACET
                            alt_intent.group_by = [common_facets[0]]
                            alt_nrql = self.nrql_builder.build(alt_intent)
                            alternatives.append(alt_nrql)
                            break
        
        return alternatives[:3]  # Limit alternatives
    
    def _get_cache_key(self, query: str, context: Optional[QueryContext]) -> str:
        """Generate cache key for query"""
        # Include query and context elements in key
        key_parts = [query.lower().strip()]
        
        if context:
            if context.available_schemas:
                key_parts.append(f"schemas:{len(context.available_schemas)}")
            if context.cost_constraints:
                key_parts.append(f"cost:{context.cost_constraints}")
        
        return '|'.join(key_parts)
    
    def _cache_result(self, key: str, result: QueryResult):
        """Cache query result"""
        # Implement LRU cache
        if len(self.query_cache) >= self.cache_size:
            # Remove oldest entry
            oldest_key = next(iter(self.query_cache))
            del self.query_cache[oldest_key]
        
        self.query_cache[key] = result
    
    def _add_to_history(self, query: str, result: QueryResult):
        """Add to query history for learning"""
        entry = {
            'query': query,
            'nrql': result.nrql,
            'intent_type': result.intent.intent_type.value,
            'query_type': result.intent.query_type.value,
            'confidence': result.confidence,
            'timestamp': datetime.utcnow()
        }
        
        self.query_history.append(entry)
        
        # Trim history if needed
        if len(self.query_history) > self.history_size:
            self.query_history = self.query_history[-self.history_size:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get generator metrics"""
        cache_hits = sum(1 for r in self.query_cache.values() if r.metadata.get('cache_hit', False))
        total_queries = len(self.query_history)
        
        return {
            'total_queries': total_queries,
            'cache_size': len(self.query_cache),
            'cache_hit_rate': cache_hits / max(1, total_queries),
            'history_size': len(self.query_history),
            'average_confidence': sum(h['confidence'] for h in self.query_history) / max(1, len(self.query_history))
        }


# Import required types for the imports to work
from .base import IntentType, QueryType, TimeRange, TimeRangeType
import re