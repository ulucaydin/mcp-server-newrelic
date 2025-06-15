"""Dashboard Layout Optimizer - Optimizes dashboard layouts for visual effectiveness"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from loguru import logger
import math

from .chart_recommender import ChartType, ChartRecommendation


class LayoutStrategy(Enum):
    """Dashboard layout strategies"""
    GRID = "grid"
    MASONRY = "masonry"
    FLOW = "flow"
    FIXED = "fixed"
    RESPONSIVE = "responsive"


class WidgetSize(Enum):
    """Standard widget sizes"""
    SMALL = (1, 1)      # 1x1 grid units
    MEDIUM = (2, 1)     # 2x1 grid units
    LARGE = (2, 2)      # 2x2 grid units
    WIDE = (3, 1)       # 3x1 grid units
    TALL = (1, 2)       # 1x2 grid units
    XLARGE = (3, 2)     # 3x2 grid units
    FULL_WIDTH = (4, 1) # Full width


class WidgetPriority(Enum):
    """Widget priority levels"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    OPTIONAL = 1


@dataclass
class Widget:
    """Dashboard widget definition"""
    id: str
    title: str
    chart_type: ChartType
    data_query: str
    
    # Size and position
    size: WidgetSize = WidgetSize.MEDIUM
    position: Optional[Tuple[int, int]] = None  # (x, y) in grid units
    
    # Priority and relationships
    priority: WidgetPriority = WidgetPriority.MEDIUM
    related_widgets: List[str] = field(default_factory=list)
    
    # Visual properties
    color_scheme: Optional[str] = None
    refresh_interval: int = 60  # seconds
    
    # Constraints
    min_size: Optional[WidgetSize] = None
    max_size: Optional[WidgetSize] = None
    fixed_position: bool = False
    
    def get_width(self) -> int:
        """Get widget width in grid units"""
        return self.size.value[0]
    
    def get_height(self) -> int:
        """Get widget height in grid units"""
        return self.size.value[1]
    
    def get_area(self) -> int:
        """Get widget area in grid units"""
        return self.get_width() * self.get_height()


@dataclass
class WidgetPlacement:
    """Optimized widget placement"""
    widget_id: str
    position: Tuple[int, int]  # (x, y)
    size: WidgetSize
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'widget_id': self.widget_id,
            'position': {'x': self.position[0], 'y': self.position[1]},
            'size': {'width': self.size.value[0], 'height': self.size.value[1]}
        }


@dataclass
class DashboardLayout:
    """Optimized dashboard layout"""
    strategy: LayoutStrategy
    grid_columns: int
    grid_rows: int
    placements: List[WidgetPlacement]
    
    # Layout quality metrics
    space_utilization: float = 0.0
    visual_balance: float = 0.0
    relationship_score: float = 0.0
    overall_score: float = 0.0
    
    # Metadata
    optimization_time: float = 0.0
    iterations: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'strategy': self.strategy.value,
            'grid': {
                'columns': self.grid_columns,
                'rows': self.grid_rows
            },
            'placements': [p.to_dict() for p in self.placements],
            'metrics': {
                'space_utilization': self.space_utilization,
                'visual_balance': self.visual_balance,
                'relationship_score': self.relationship_score,
                'overall_score': self.overall_score
            },
            'optimization': {
                'time_seconds': self.optimization_time,
                'iterations': self.iterations
            }
        }


@dataclass
class LayoutConstraints:
    """Constraints for layout optimization"""
    max_columns: int = 4
    max_rows: int = 20
    min_widget_width: int = 1
    min_widget_height: int = 1
    
    # Visual constraints
    maintain_aspect_ratio: bool = True
    group_related_widgets: bool = True
    
    # Performance constraints
    max_widgets_per_row: int = 4
    max_total_widgets: int = 20
    
    # Responsive constraints
    mobile_friendly: bool = False
    tablet_friendly: bool = True


class LayoutOptimizer:
    """Optimizes dashboard layouts for visual effectiveness and usability"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.default_grid_columns = self.config.get('default_grid_columns', 4)
        self.optimization_iterations = self.config.get('optimization_iterations', 100)
        
    def optimize(self,
                widgets: List[Widget],
                constraints: Optional[LayoutConstraints] = None,
                strategy: LayoutStrategy = LayoutStrategy.GRID) -> DashboardLayout:
        """
        Optimize dashboard layout for given widgets
        
        Args:
            widgets: List of widgets to place
            constraints: Layout constraints
            strategy: Layout strategy to use
            
        Returns:
            Optimized dashboard layout
        """
        start_time = datetime.utcnow()
        constraints = constraints or LayoutConstraints()
        
        logger.info(f"Optimizing layout for {len(widgets)} widgets using {strategy.value} strategy")
        
        # Validate inputs
        if not widgets:
            return self._create_empty_layout(strategy)
        
        # Sort widgets by priority
        sorted_widgets = sorted(widgets, key=lambda w: w.priority.value, reverse=True)
        
        # Choose optimization method based on strategy
        if strategy == LayoutStrategy.GRID:
            layout = self._optimize_grid_layout(sorted_widgets, constraints)
        elif strategy == LayoutStrategy.MASONRY:
            layout = self._optimize_masonry_layout(sorted_widgets, constraints)
        elif strategy == LayoutStrategy.FLOW:
            layout = self._optimize_flow_layout(sorted_widgets, constraints)
        elif strategy == LayoutStrategy.RESPONSIVE:
            layout = self._optimize_responsive_layout(sorted_widgets, constraints)
        else:  # FIXED
            layout = self._create_fixed_layout(sorted_widgets, constraints)
        
        # Calculate layout metrics
        self._calculate_layout_metrics(layout, widgets)
        
        # Record optimization time
        layout.optimization_time = (datetime.utcnow() - start_time).total_seconds()
        
        return layout
    
    def _optimize_grid_layout(self,
                            widgets: List[Widget],
                            constraints: LayoutConstraints) -> DashboardLayout:
        """Optimize using grid-based layout"""
        
        grid_cols = min(self.default_grid_columns, constraints.max_columns)
        
        # Initialize layout
        layout = DashboardLayout(
            strategy=LayoutStrategy.GRID,
            grid_columns=grid_cols,
            grid_rows=0,
            placements=[]
        )
        
        # Create occupancy grid
        max_rows = constraints.max_rows
        grid = np.zeros((max_rows, grid_cols), dtype=bool)
        
        # Place widgets using best-fit algorithm
        current_row = 0
        
        for widget in widgets:
            # Try to place widget
            placement = self._find_best_grid_position(
                widget, grid, current_row, constraints
            )
            
            if placement:
                # Mark grid cells as occupied
                x, y = placement.position
                w, h = placement.size.value
                
                for row in range(y, min(y + h, max_rows)):
                    for col in range(x, min(x + w, grid_cols)):
                        grid[row][col] = True
                
                layout.placements.append(placement)
                
                # Update current row
                current_row = max(current_row, y)
            else:
                logger.warning(f"Could not place widget {widget.id}")
        
        # Calculate actual grid rows used
        layout.grid_rows = self._calculate_used_rows(grid)
        
        return layout
    
    def _optimize_masonry_layout(self,
                               widgets: List[Widget],
                               constraints: LayoutConstraints) -> DashboardLayout:
        """Optimize using masonry (Pinterest-style) layout"""
        
        grid_cols = min(self.default_grid_columns, constraints.max_columns)
        
        # Initialize layout
        layout = DashboardLayout(
            strategy=LayoutStrategy.MASONRY,
            grid_columns=grid_cols,
            grid_rows=0,
            placements=[]
        )
        
        # Track column heights
        column_heights = [0] * grid_cols
        
        for widget in widgets:
            # Adjust widget size if needed
            size = self._adjust_widget_size_for_masonry(widget, grid_cols)
            
            # Find best column(s) to place widget
            if size.value[0] == 1:
                # Single column widget - place in shortest column
                min_col = column_heights.index(min(column_heights))
                x = min_col
                y = column_heights[min_col]
            else:
                # Multi-column widget - find best consecutive columns
                best_x = 0
                best_height = float('inf')
                
                for start_col in range(grid_cols - size.value[0] + 1):
                    max_height = max(column_heights[start_col:start_col + size.value[0]])
                    if max_height < best_height:
                        best_height = max_height
                        best_x = start_col
                
                x = best_x
                y = best_height
            
            # Create placement
            placement = WidgetPlacement(
                widget_id=widget.id,
                position=(x, y),
                size=size
            )
            layout.placements.append(placement)
            
            # Update column heights
            for col in range(x, x + size.value[0]):
                column_heights[col] = y + size.value[1]
        
        # Set grid rows to max column height
        layout.grid_rows = max(column_heights)
        
        return layout
    
    def _optimize_flow_layout(self,
                            widgets: List[Widget],
                            constraints: LayoutConstraints) -> DashboardLayout:
        """Optimize using flow layout (left-to-right, top-to-bottom)"""
        
        grid_cols = min(self.default_grid_columns, constraints.max_columns)
        
        # Initialize layout
        layout = DashboardLayout(
            strategy=LayoutStrategy.FLOW,
            grid_columns=grid_cols,
            grid_rows=0,
            placements=[]
        )
        
        # Current position
        x, y = 0, 0
        row_height = 0
        
        for widget in widgets:
            # Get widget size
            size = self._get_optimal_widget_size(widget, constraints)
            width, height = size.value
            
            # Check if widget fits in current row
            if x + width > grid_cols:
                # Move to next row
                x = 0
                y += row_height
                row_height = 0
            
            # Place widget
            placement = WidgetPlacement(
                widget_id=widget.id,
                position=(x, y),
                size=size
            )
            layout.placements.append(placement)
            
            # Update position
            x += width
            row_height = max(row_height, height)
        
        # Calculate total rows
        layout.grid_rows = y + row_height
        
        return layout
    
    def _optimize_responsive_layout(self,
                                  widgets: List[Widget],
                                  constraints: LayoutConstraints) -> DashboardLayout:
        """Optimize for responsive design"""
        
        # Start with standard grid layout
        layout = self._optimize_grid_layout(widgets, constraints)
        layout.strategy = LayoutStrategy.RESPONSIVE
        
        # Apply responsive adjustments
        if constraints.mobile_friendly:
            # Stack widgets vertically for mobile
            self._apply_mobile_adjustments(layout)
        elif constraints.tablet_friendly:
            # Use 2-column layout for tablets
            self._apply_tablet_adjustments(layout)
        
        return layout
    
    def _create_fixed_layout(self,
                           widgets: List[Widget],
                           constraints: LayoutConstraints) -> DashboardLayout:
        """Create layout respecting fixed positions"""
        
        grid_cols = min(self.default_grid_columns, constraints.max_columns)
        
        layout = DashboardLayout(
            strategy=LayoutStrategy.FIXED,
            grid_columns=grid_cols,
            grid_rows=0,
            placements=[]
        )
        
        # Separate fixed and non-fixed widgets
        fixed_widgets = [w for w in widgets if w.fixed_position and w.position]
        floating_widgets = [w for w in widgets if not w.fixed_position or not w.position]
        
        # Place fixed widgets first
        for widget in fixed_widgets:
            placement = WidgetPlacement(
                widget_id=widget.id,
                position=widget.position,
                size=widget.size
            )
            layout.placements.append(placement)
        
        # Create occupancy grid for floating widgets
        grid = np.zeros((constraints.max_rows, grid_cols), dtype=bool)
        
        # Mark fixed widget positions
        for placement in layout.placements:
            x, y = placement.position
            w, h = placement.size.value
            for row in range(y, min(y + h, constraints.max_rows)):
                for col in range(x, min(x + w, grid_cols)):
                    grid[row][col] = True
        
        # Place floating widgets
        for widget in floating_widgets:
            placement = self._find_best_grid_position(widget, grid, 0, constraints)
            if placement:
                layout.placements.append(placement)
                # Update grid
                x, y = placement.position
                w, h = placement.size.value
                for row in range(y, min(y + h, constraints.max_rows)):
                    for col in range(x, min(x + w, grid_cols)):
                        grid[row][col] = True
        
        # Calculate grid rows
        layout.grid_rows = self._calculate_used_rows(grid)
        
        return layout
    
    def _find_best_grid_position(self,
                               widget: Widget,
                               grid: np.ndarray,
                               start_row: int,
                               constraints: LayoutConstraints) -> Optional[WidgetPlacement]:
        """Find best position for widget in grid"""
        
        size = self._get_optimal_widget_size(widget, constraints)
        width, height = size.value
        
        max_rows, max_cols = grid.shape
        
        # Try to place widget starting from start_row
        for y in range(start_row, max_rows - height + 1):
            for x in range(max_cols - width + 1):
                # Check if space is available
                if self._is_space_available(grid, x, y, width, height):
                    return WidgetPlacement(
                        widget_id=widget.id,
                        position=(x, y),
                        size=size
                    )
        
        return None
    
    def _is_space_available(self,
                          grid: np.ndarray,
                          x: int, y: int,
                          width: int, height: int) -> bool:
        """Check if space is available in grid"""
        
        max_rows, max_cols = grid.shape
        
        # Check bounds
        if x + width > max_cols or y + height > max_rows:
            return False
        
        # Check if all cells are empty
        for row in range(y, y + height):
            for col in range(x, x + width):
                if grid[row][col]:
                    return False
        
        return True
    
    def _get_optimal_widget_size(self,
                               widget: Widget,
                               constraints: LayoutConstraints) -> WidgetSize:
        """Get optimal size for widget based on chart type and constraints"""
        
        # Chart type to optimal size mapping
        size_recommendations = {
            ChartType.LINE: WidgetSize.LARGE,
            ChartType.TIMESERIES_LINE: WidgetSize.LARGE,
            ChartType.AREA: WidgetSize.LARGE,
            ChartType.BAR: WidgetSize.MEDIUM,
            ChartType.PIE: WidgetSize.MEDIUM,
            ChartType.BILLBOARD: WidgetSize.SMALL,
            ChartType.TABLE: WidgetSize.WIDE,
            ChartType.HEATMAP: WidgetSize.LARGE,
            ChartType.SCATTER: WidgetSize.LARGE,
            ChartType.HISTOGRAM: WidgetSize.MEDIUM,
            ChartType.GAUGE: WidgetSize.SMALL,
            ChartType.SPARKLINE: WidgetSize.SMALL
        }
        
        # Get recommended size
        recommended = size_recommendations.get(widget.chart_type, WidgetSize.MEDIUM)
        
        # Apply widget constraints
        if widget.size:
            return widget.size
        
        # Apply min/max constraints
        if widget.min_size:
            if recommended.value[0] * recommended.value[1] < widget.min_size.value[0] * widget.min_size.value[1]:
                recommended = widget.min_size
        
        if widget.max_size:
            if recommended.value[0] * recommended.value[1] > widget.max_size.value[0] * widget.max_size.value[1]:
                recommended = widget.max_size
        
        return recommended
    
    def _adjust_widget_size_for_masonry(self,
                                      widget: Widget,
                                      grid_cols: int) -> WidgetSize:
        """Adjust widget size for masonry layout"""
        
        # In masonry, prefer consistent widths
        if grid_cols == 4:
            # 4-column masonry
            if widget.chart_type in [ChartType.TABLE, ChartType.HEATMAP]:
                return WidgetSize.WIDE  # 3 columns
            elif widget.chart_type in [ChartType.BILLBOARD, ChartType.GAUGE]:
                return WidgetSize.SMALL  # 1 column
            else:
                return WidgetSize.MEDIUM  # 2 columns
        elif grid_cols == 3:
            # 3-column masonry
            if widget.chart_type in [ChartType.TABLE]:
                return WidgetSize.WIDE  # Full width
            else:
                return WidgetSize.SMALL  # 1 column
        else:
            # 2-column masonry
            return WidgetSize.SMALL  # 1 column
    
    def _calculate_used_rows(self, grid: np.ndarray) -> int:
        """Calculate number of rows actually used"""
        
        for row in range(grid.shape[0] - 1, -1, -1):
            if np.any(grid[row]):
                return row + 1
        return 0
    
    def _calculate_layout_metrics(self,
                                layout: DashboardLayout,
                                widgets: List[Widget]):
        """Calculate quality metrics for layout"""
        
        if not layout.placements:
            return
        
        # Create widget lookup
        widget_map = {w.id: w for w in widgets}
        
        # Calculate space utilization
        total_cells = layout.grid_columns * layout.grid_rows
        used_cells = sum(
            p.size.value[0] * p.size.value[1]
            for p in layout.placements
        )
        layout.space_utilization = used_cells / max(1, total_cells)
        
        # Calculate visual balance
        layout.visual_balance = self._calculate_visual_balance(layout)
        
        # Calculate relationship score
        layout.relationship_score = self._calculate_relationship_score(
            layout, widget_map
        )
        
        # Calculate overall score
        layout.overall_score = (
            0.3 * layout.space_utilization +
            0.3 * layout.visual_balance +
            0.4 * layout.relationship_score
        )
    
    def _calculate_visual_balance(self, layout: DashboardLayout) -> float:
        """Calculate visual balance of layout"""
        
        if not layout.placements:
            return 0.0
        
        # Calculate center of mass for widgets
        total_weight = 0
        weighted_x = 0
        weighted_y = 0
        
        for placement in layout.placements:
            x, y = placement.position
            w, h = placement.size.value
            
            # Widget center
            cx = x + w / 2
            cy = y + h / 2
            
            # Weight by area
            weight = w * h
            weighted_x += cx * weight
            weighted_y += cy * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        # Center of mass
        com_x = weighted_x / total_weight
        com_y = weighted_y / total_weight
        
        # Dashboard center
        center_x = layout.grid_columns / 2
        center_y = layout.grid_rows / 2
        
        # Calculate distance from center
        distance = math.sqrt((com_x - center_x)**2 + (com_y - center_y)**2)
        max_distance = math.sqrt(center_x**2 + center_y**2)
        
        # Convert to balance score (1 = perfectly balanced)
        balance = 1 - (distance / max_distance) if max_distance > 0 else 1.0
        
        return balance
    
    def _calculate_relationship_score(self,
                                    layout: DashboardLayout,
                                    widget_map: Dict[str, Widget]) -> float:
        """Calculate how well related widgets are placed together"""
        
        if not layout.placements:
            return 0.0
        
        # Create position lookup
        position_map = {
            p.widget_id: p.position
            for p in layout.placements
        }
        
        total_relationships = 0
        good_relationships = 0
        
        for placement in layout.placements:
            widget = widget_map.get(placement.widget_id)
            if not widget or not widget.related_widgets:
                continue
            
            widget_pos = position_map[widget.id]
            
            for related_id in widget.related_widgets:
                if related_id not in position_map:
                    continue
                
                total_relationships += 1
                related_pos = position_map[related_id]
                
                # Calculate Manhattan distance
                distance = abs(widget_pos[0] - related_pos[0]) + abs(widget_pos[1] - related_pos[1])
                
                # Consider "close" if within 2 grid units
                if distance <= 2:
                    good_relationships += 1
        
        if total_relationships == 0:
            return 1.0  # No relationships to optimize
        
        return good_relationships / total_relationships
    
    def _apply_mobile_adjustments(self, layout: DashboardLayout):
        """Apply mobile-friendly adjustments"""
        
        # Stack all widgets vertically
        layout.grid_columns = 1
        y = 0
        
        for placement in layout.placements:
            # Adjust size to single column
            if placement.size.value[0] > 1:
                placement.size = WidgetSize.SMALL
            
            # Update position
            placement.position = (0, y)
            y += placement.size.value[1]
        
        layout.grid_rows = y
    
    def _apply_tablet_adjustments(self, layout: DashboardLayout):
        """Apply tablet-friendly adjustments"""
        
        # Use 2-column layout
        layout.grid_columns = 2
        
        # Adjust widget sizes
        for placement in layout.placements:
            if placement.size.value[0] > 2:
                placement.size = WidgetSize.MEDIUM
    
    def _create_empty_layout(self, strategy: LayoutStrategy) -> DashboardLayout:
        """Create empty layout"""
        
        return DashboardLayout(
            strategy=strategy,
            grid_columns=self.default_grid_columns,
            grid_rows=0,
            placements=[]
        )
    
    def suggest_improvements(self, layout: DashboardLayout) -> List[str]:
        """Suggest improvements for existing layout"""
        
        suggestions = []
        
        # Check space utilization
        if layout.space_utilization < 0.6:
            suggestions.append("Consider using larger widget sizes to better utilize space")
        elif layout.space_utilization > 0.9:
            suggestions.append("Layout may be too dense - consider spacing widgets more")
        
        # Check visual balance
        if layout.visual_balance < 0.7:
            suggestions.append("Layout appears unbalanced - try distributing widgets more evenly")
        
        # Check relationship score
        if layout.relationship_score < 0.5:
            suggestions.append("Related widgets are far apart - consider grouping them")
        
        # Check grid usage
        if layout.grid_rows > 10:
            suggestions.append("Dashboard is very tall - consider using wider widgets or multiple pages")
        
        # Strategy-specific suggestions
        if layout.strategy == LayoutStrategy.GRID and layout.space_utilization < 0.7:
            suggestions.append("Consider using masonry layout for better space utilization")
        
        return suggestions