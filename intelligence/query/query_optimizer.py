"""Query Optimizer - Optimizes NRQL queries for cost and performance"""

import re
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from .base import QueryIntent, QueryContext, QueryType, TimeRangeType


class QueryOptimizer:
    """
    Optimizes NRQL queries for better performance and lower cost
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.aggressive_optimization = self.config.get('aggressive', False)
        self.cost_threshold = self.config.get('cost_threshold', 100.0)
        self.performance_mode = self.config.get('performance_mode', 'balanced')
        
        # Optimization rules
        self.optimization_rules = self._load_optimization_rules()
        
        # Cost model parameters
        self.cost_model = {
            'base_cost_per_gb': 0.25,
            'timeseries_multiplier': 1.5,
            'facet_multiplier': 1.2,
            'percentile_multiplier': 2.0,
            'unique_count_multiplier': 1.8,
            'no_limit_penalty': 2.0
        }
    
    def optimize(self,
                nrql: str,
                intent: QueryIntent,
                context: QueryContext) -> Tuple[str, Dict[str, Any]]:
        """
        Optimize NRQL query based on intent and context
        
        Args:
            nrql: Original NRQL query
            intent: Parsed query intent
            context: Query context with schemas and constraints
            
        Returns:
            Tuple of (optimized_nrql, optimization_metadata)
        """
        original_nrql = nrql
        optimizations_applied = []
        
        # Estimate original cost
        original_cost = self._estimate_cost(nrql, intent, context)
        
        # Apply optimization rules based on mode
        if self.performance_mode == 'cost':
            nrql = self._optimize_for_cost(nrql, intent, context, optimizations_applied)
        elif self.performance_mode == 'speed':
            nrql = self._optimize_for_speed(nrql, intent, context, optimizations_applied)
        else:  # balanced
            nrql = self._optimize_balanced(nrql, intent, context, optimizations_applied)
        
        # Apply general optimizations
        nrql = self._apply_general_optimizations(nrql, intent, context, optimizations_applied)
        
        # Validate optimized query
        if not self._validate_optimization(original_nrql, nrql, intent):
            logger.warning("Optimization validation failed, reverting to original")
            nrql = original_nrql
            optimizations_applied = ["validation_failed"]
        
        # Estimate new cost
        new_cost = self._estimate_cost(nrql, intent, context)
        
        # Create metadata
        metadata = {
            'original_cost': original_cost,
            'optimized_cost': new_cost,
            'cost_reduction': (original_cost - new_cost) / original_cost if original_cost > 0 else 0,
            'optimizations_applied': optimizations_applied,
            'optimization_mode': self.performance_mode
        }
        
        return nrql, metadata
    
    def _optimize_for_cost(self,
                          nrql: str,
                          intent: QueryIntent,
                          context: QueryContext,
                          optimizations: List[str]) -> str:
        """Optimize primarily for cost reduction"""
        
        # 1. Reduce time range if possible
        if intent.time_range.type in [TimeRangeType.LAST_MONTH, TimeRangeType.LAST_QUARTER]:
            if intent.intent_type.value not in ['report', 'forecast']:
                # Suggest shorter time range
                nrql = self._reduce_time_range(nrql, intent, optimizations)
        
        # 2. Add sampling for large datasets
        nrql = self._add_sampling(nrql, intent, context, optimizations)
        
        # 3. Limit facet cardinality
        if intent.query_type == QueryType.FACET:
            nrql = self._limit_facet_cardinality(nrql, optimizations)
        
        # 4. Replace expensive aggregations
        nrql = self._replace_expensive_aggregations(nrql, intent, optimizations)
        
        # 5. Add aggressive LIMIT
        if 'LIMIT' not in nrql:
            nrql = self._add_limit(nrql, 100, optimizations)
        
        return nrql
    
    def _optimize_for_speed(self,
                           nrql: str,
                           intent: QueryIntent,
                           context: QueryContext,
                           optimizations: List[str]) -> str:
        """Optimize primarily for query speed"""
        
        # 1. Use indexes effectively
        nrql = self._optimize_where_clause(nrql, context, optimizations)
        
        # 2. Reduce result set size early
        if 'WHERE' in nrql and 'LIMIT' not in nrql:
            nrql = self._add_limit(nrql, 1000, optimizations)
        
        # 3. Avoid expensive operations on large datasets
        if self._is_large_dataset(context, intent):
            nrql = self._simplify_aggregations(nrql, optimizations)
        
        # 4. Use approximate algorithms where possible
        nrql = self._use_approximations(nrql, intent, optimizations)
        
        return nrql
    
    def _optimize_balanced(self,
                          nrql: str,
                          intent: QueryIntent,
                          context: QueryContext,
                          optimizations: List[str]) -> str:
        """Balance between cost and performance"""
        
        # Apply moderate optimizations from both strategies
        
        # 1. Moderate time range reduction
        if self._get_time_range_hours(intent.time_range) > 168:  # > 1 week
            nrql = self._reduce_time_range(nrql, intent, optimizations, moderate=True)
        
        # 2. Smart sampling based on data volume
        estimated_volume = self._estimate_data_volume(intent, context)
        if estimated_volume > 1_000_000:
            nrql = self._add_sampling(nrql, intent, context, optimizations)
        
        # 3. Optimize WHERE clause
        nrql = self._optimize_where_clause(nrql, context, optimizations)
        
        # 4. Add reasonable LIMIT
        if 'LIMIT' not in nrql and 'TIMESERIES' not in nrql:
            nrql = self._add_limit(nrql, 500, optimizations)
        
        return nrql
    
    def _apply_general_optimizations(self,
                                   nrql: str,
                                   intent: QueryIntent,
                                   context: QueryContext,
                                   optimizations: List[str]) -> str:
        """Apply general optimizations that always make sense"""
        
        # 1. Remove redundant operations
        nrql = self._remove_redundancies(nrql, optimizations)
        
        # 2. Reorder WHERE conditions for better performance
        nrql = self._reorder_where_conditions(nrql, context, optimizations)
        
        # 3. Use column pruning
        nrql = self._prune_unnecessary_columns(nrql, intent, optimizations)
        
        # 4. Optimize time bucket sizes
        if 'TIMESERIES' in nrql:
            nrql = self._optimize_timeseries_buckets(nrql, intent, optimizations)
        
        return nrql
    
    def _reduce_time_range(self,
                          nrql: str,
                          intent: QueryIntent,
                          optimizations: List[str],
                          moderate: bool = False) -> str:
        """Reduce time range to lower cost"""
        
        # Map current range to suggested range
        range_reductions = {
            TimeRangeType.LAST_QUARTER: ('SINCE 1 month ago', 'SINCE 3 months ago'),
            TimeRangeType.LAST_MONTH: ('SINCE 1 week ago', 'SINCE 1 month ago'),
            TimeRangeType.LAST_WEEK: ('SINCE 1 day ago', 'SINCE 1 week ago')
        }
        
        if moderate:
            # Less aggressive reduction
            range_reductions = {
                TimeRangeType.LAST_QUARTER: ('SINCE 2 months ago', 'SINCE 3 months ago'),
                TimeRangeType.LAST_MONTH: ('SINCE 2 weeks ago', 'SINCE 1 month ago')
            }
        
        for time_type, (new_range, old_range) in range_reductions.items():
            if intent.time_range.type == time_type and old_range in nrql:
                nrql = nrql.replace(old_range, new_range)
                optimizations.append(f"reduced_time_range_to_{new_range}")
                break
        
        return nrql
    
    def _add_sampling(self,
                     nrql: str,
                     intent: QueryIntent,
                     context: QueryContext,
                     optimizations: List[str]) -> str:
        """Add sampling to reduce data scanned"""
        
        # Don't sample if already has LIMIT or sampling
        if 'LIMIT' in nrql or 'SAMPLE' in nrql:
            return nrql
        
        # Don't sample for certain query types
        if intent.query_type in [QueryType.PERCENTILE, QueryType.HISTOGRAM]:
            return nrql
        
        # Estimate sample size based on data volume
        volume = self._estimate_data_volume(intent, context)
        
        if volume > 10_000_000:
            sample_rate = 0.01  # 1%
        elif volume > 1_000_000:
            sample_rate = 0.1   # 10%
        else:
            return nrql  # No sampling needed
        
        # Add SAMPLE clause after FROM
        from_match = re.search(r'(FROM\s+\S+)', nrql)
        if from_match:
            from_clause = from_match.group(1)
            new_from = f"{from_clause} SAMPLE({sample_rate})"
            nrql = nrql.replace(from_clause, new_from)
            optimizations.append(f"added_sampling_{sample_rate}")
        
        return nrql
    
    def _limit_facet_cardinality(self, nrql: str, optimizations: List[str]) -> str:
        """Limit number of facet results"""
        
        if 'FACET' in nrql and 'LIMIT' not in nrql:
            # Add LIMIT after FACET
            nrql += ' LIMIT 100'
            optimizations.append("added_facet_limit")
        
        return nrql
    
    def _replace_expensive_aggregations(self,
                                      nrql: str,
                                      intent: QueryIntent,
                                      optimizations: List[str]) -> str:
        """Replace expensive aggregations with cheaper alternatives"""
        
        replacements = {
            'uniqueCount': 'approximateCount',  # If available
            'percentile\\((.*?),\\s*99\\)': 'max',  # P99 -> max for cost savings
            'percentile\\((.*?),\\s*50\\)': 'average'  # P50 -> average
        }
        
        for pattern, replacement in replacements.items():
            if re.search(pattern, nrql):
                if self.aggressive_optimization:
                    nrql = re.sub(pattern, replacement, nrql)
                    optimizations.append(f"replaced_{pattern}_with_{replacement}")
        
        return nrql
    
    def _optimize_where_clause(self,
                             nrql: str,
                             context: QueryContext,
                             optimizations: List[str]) -> str:
        """Optimize WHERE clause for better index usage"""
        
        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+SINCE|\s+FACET|\s+LIMIT|$)', nrql)
        if not where_match:
            return nrql
        
        where_clause = where_match.group(1)
        
        # Add high-selectivity filters first
        # This is a simplified version - real implementation would analyze selectivity
        high_selectivity_fields = ['appName', 'host', 'entityGuid']
        
        conditions = where_clause.split(' AND ')
        high_priority = []
        low_priority = []
        
        for condition in conditions:
            if any(field in condition for field in high_selectivity_fields):
                high_priority.append(condition)
            else:
                low_priority.append(condition)
        
        if high_priority:
            new_where = ' AND '.join(high_priority + low_priority)
            if new_where != where_clause:
                nrql = nrql.replace(where_clause, new_where)
                optimizations.append("reordered_where_conditions")
        
        return nrql
    
    def _add_limit(self, nrql: str, limit: int, optimizations: List[str]) -> str:
        """Add LIMIT clause to query"""
        
        if 'LIMIT' not in nrql and 'TIMESERIES' not in nrql:
            nrql += f' LIMIT {limit}'
            optimizations.append(f"added_limit_{limit}")
        
        return nrql
    
    def _simplify_aggregations(self, nrql: str, optimizations: List[str]) -> str:
        """Simplify complex aggregations for large datasets"""
        
        # Replace multiple percentiles with min/avg/max
        if nrql.count('percentile') > 3:
            # Keep only essential percentiles
            nrql = re.sub(r'percentile\([^,]+,\s*(?:25|75)\)', '', nrql)
            optimizations.append("reduced_percentile_calculations")
        
        return nrql
    
    def _use_approximations(self, nrql: str, intent: QueryIntent, optimizations: List[str]) -> str:
        """Use approximate algorithms where acceptable"""
        
        # Use approximate unique count for large cardinality
        if 'uniqueCount' in nrql and self.aggressive_optimization:
            nrql = nrql.replace('uniqueCount', 'approximateUniqueCount')
            optimizations.append("using_approximate_unique_count")
        
        return nrql
    
    def _optimize_timeseries_buckets(self,
                                   nrql: str,
                                   intent: QueryIntent,
                                   optimizations: List[str]) -> str:
        """Optimize TIMESERIES bucket size"""
        
        # Get time range in hours
        hours = self._get_time_range_hours(intent.time_range)
        
        # Determine optimal bucket size
        if hours <= 1:
            bucket = '1 minute'
        elif hours <= 24:
            bucket = '5 minutes'
        elif hours <= 168:  # 1 week
            bucket = '1 hour'
        else:
            bucket = '1 day'
        
        # Check if TIMESERIES already has bucket size
        if re.search(r'TIMESERIES\s+\d+', nrql):
            return nrql
        
        # Add bucket size
        nrql = nrql.replace('TIMESERIES', f'TIMESERIES {bucket}')
        optimizations.append(f"set_timeseries_bucket_{bucket}")
        
        return nrql
    
    def _remove_redundancies(self, nrql: str, optimizations: List[str]) -> str:
        """Remove redundant operations"""
        
        # Remove duplicate conditions in WHERE
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+SINCE|\s+FACET|\s+LIMIT|$)', nrql)
        if where_match:
            where_clause = where_match.group(1)
            conditions = where_clause.split(' AND ')
            unique_conditions = list(dict.fromkeys(conditions))  # Preserve order
            
            if len(unique_conditions) < len(conditions):
                new_where = ' AND '.join(unique_conditions)
                nrql = nrql.replace(where_clause, new_where)
                optimizations.append("removed_duplicate_conditions")
        
        return nrql
    
    def _reorder_where_conditions(self,
                                nrql: str,
                                context: QueryContext,
                                optimizations: List[str]) -> str:
        """Reorder WHERE conditions for better performance"""
        
        # This is already done in _optimize_where_clause
        # Additional logic could go here
        
        return nrql
    
    def _prune_unnecessary_columns(self,
                                 nrql: str,
                                 intent: QueryIntent,
                                 optimizations: List[str]) -> str:
        """Remove unnecessary columns from SELECT"""
        
        # If SELECT *, consider replacing with specific columns
        if 'SELECT *' in nrql and context and context.available_schemas:
            # This would require more complex logic to determine needed columns
            pass
        
        return nrql
    
    def _estimate_cost(self,
                      nrql: str,
                      intent: QueryIntent,
                      context: QueryContext) -> float:
        """Estimate query cost"""
        
        base_cost = 1.0
        
        # Factor 1: Data volume
        volume = self._estimate_data_volume(intent, context)
        volume_cost = (volume / 1_000_000) * self.cost_model['base_cost_per_gb']
        
        # Factor 2: Query type multipliers
        if 'TIMESERIES' in nrql:
            base_cost *= self.cost_model['timeseries_multiplier']
        if 'FACET' in nrql:
            base_cost *= self.cost_model['facet_multiplier']
        if 'percentile' in nrql:
            base_cost *= self.cost_model['percentile_multiplier']
        if 'uniqueCount' in nrql:
            base_cost *= self.cost_model['unique_count_multiplier']
        
        # Factor 3: No LIMIT penalty
        if 'LIMIT' not in nrql and 'TIMESERIES' not in nrql:
            base_cost *= self.cost_model['no_limit_penalty']
        
        # Factor 4: Sampling discount
        if 'SAMPLE' in nrql:
            sample_match = re.search(r'SAMPLE\(([\d.]+)\)', nrql)
            if sample_match:
                sample_rate = float(sample_match.group(1))
                base_cost *= sample_rate
        
        return base_cost * volume_cost
    
    def _estimate_data_volume(self,
                            intent: QueryIntent,
                            context: QueryContext) -> int:
        """Estimate data volume for query"""
        
        if not context or not context.available_schemas:
            return 100_000  # Default estimate
        
        # Find matching schema
        primary_event = intent.get_primary_event_type()
        for schema in context.available_schemas:
            if schema.get('name') == primary_event:
                records_per_hour = schema.get('records_per_hour', 10_000)
                hours = self._get_time_range_hours(intent.time_range)
                return int(records_per_hour * hours)
        
        return 100_000
    
    def _get_time_range_hours(self, time_range) -> float:
        """Convert time range to hours"""
        mapping = {
            TimeRangeType.LAST_HOUR: 1,
            TimeRangeType.LAST_DAY: 24,
            TimeRangeType.LAST_WEEK: 168,
            TimeRangeType.LAST_MONTH: 720,
            TimeRangeType.LAST_QUARTER: 2160
        }
        return mapping.get(time_range.type, 1)
    
    def _is_large_dataset(self, context: QueryContext, intent: QueryIntent) -> bool:
        """Check if dataset is large"""
        volume = self._estimate_data_volume(intent, context)
        return volume > 1_000_000
    
    def _validate_optimization(self,
                             original: str,
                             optimized: str,
                             intent: QueryIntent) -> bool:
        """Validate that optimization preserves query semantics"""
        
        # Basic validation - ensure key components are preserved
        essential_components = ['SELECT', 'FROM']
        
        for component in essential_components:
            if component in original and component not in optimized:
                return False
        
        # Ensure event types are preserved
        for event_type in intent.event_types:
            if event_type in original and event_type not in optimized:
                return False
        
        # More sophisticated validation could be added here
        
        return True
    
    def _load_optimization_rules(self) -> List[Dict[str, Any]]:
        """Load optimization rules"""
        return [
            {
                'name': 'reduce_time_range',
                'condition': lambda i, c: self._get_time_range_hours(i.time_range) > 168,
                'action': 'reduce_time_range'
            },
            {
                'name': 'add_sampling',
                'condition': lambda i, c: self._estimate_data_volume(i, c) > 1_000_000,
                'action': 'add_sampling'
            },
            {
                'name': 'limit_results',
                'condition': lambda i, c: i.limit is None,
                'action': 'add_limit'
            }
        ]