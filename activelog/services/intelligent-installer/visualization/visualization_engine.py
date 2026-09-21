"""
Advanced Visualization Engine
Interactive data visualization, custom charts, and dynamic visual analytics
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Set, Tuple, Callable
from enum import Enum
from pathlib import Path
import base64
import hashlib

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

logger = logging.getLogger(__name__)

class VisualizationType(Enum):
    TIME_SERIES = "time_series"
    SCATTER = "scatter"
    BAR = "bar"
    HISTOGRAM = "histogram"
    BOX_PLOT = "box_plot"
    VIOLIN_PLOT = "violin_plot"
    HEATMAP = "heatmap"
    TREEMAP = "treemap"
    SUNBURST = "sunburst"
    SANKEY = "sankey"
    NETWORK = "network"
    GEOGRAPHIC = "geographic"
    THREE_D_SURFACE = "3d_surface"
    RADAR = "radar"
    FUNNEL = "funnel"
    WATERFALL = "waterfall"
    CUSTOM = "custom"

class InteractivityLevel(Enum):
    STATIC = "static"
    BASIC = "basic"          # Hover, zoom, pan
    INTERMEDIATE = "intermediate"  # Brushing, linking
    ADVANCED = "advanced"    # Custom callbacks, real-time updates
    FULL = "full"           # All interactive features

class ColorScheme(Enum):
    DEFAULT = "default"
    VIRIDIS = "viridis"
    PLASMA = "plasma"
    INFERNO = "inferno"
    MAGMA = "magma"
    BLUES = "blues"
    REDS = "reds"
    GREENS = "greens"
    CATEGORICAL = "categorical"
    CUSTOM = "custom"

@dataclass
class VisualizationSpec:
    viz_id: str
    title: str
    viz_type: VisualizationType
    data_source: str
    dimensions: List[str]  # X-axis, grouping variables
    measures: List[str]    # Y-axis, values to plot
    color_scheme: ColorScheme
    interactivity: InteractivityLevel
    filters: Dict[str, Any]
    styling: Dict[str, Any]
    layout_config: Dict[str, Any]
    export_formats: List[str] = field(default_factory=lambda: ['html', 'png', 'svg'])
    refresh_interval: Optional[int] = None  # seconds, None for static
    custom_config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class VisualizationData:
    viz_id: str
    raw_data: Dict[str, Any]
    processed_data: Dict[str, Any]
    metadata: Dict[str, Any]
    last_updated: datetime
    data_quality_score: float

@dataclass
class InteractionEvent:
    event_id: str
    viz_id: str
    event_type: str  # click, hover, select, zoom, etc.
    event_data: Dict[str, Any]
    timestamp: datetime
    user_context: Dict[str, str]

class DataProcessor:
    """Advanced data processing for visualizations"""
    
    def __init__(self):
        self.transformations: Dict[str, Callable] = {}
        self.aggregations: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        self._register_default_transformations()
        self._register_default_aggregations()
    
    def _register_default_transformations(self):
        """Register default data transformations"""
        self.transformations.update({
            'normalize': self._normalize_data,
            'standardize': self._standardize_data,
            'log_transform': self._log_transform,
            'moving_average': self._moving_average,
            'cumulative_sum': self._cumulative_sum,
            'percentage': self._percentage_transform,
            'rank': self._rank_transform,
            'binning': self._binning_transform
        })
    
    def _register_default_aggregations(self):
        """Register default aggregation functions"""
        self.aggregations.update({
            'sum': lambda x: sum(x) if x else 0,
            'mean': lambda x: sum(x) / len(x) if x else 0,
            'median': lambda x: sorted(x)[len(x)//2] if x else 0,
            'min': lambda x: min(x) if x else 0,
            'max': lambda x: max(x) if x else 0,
            'count': lambda x: len(x),
            'std': lambda x: self._calculate_std(x),
            'percentile_95': lambda x: self._percentile(x, 0.95),
            'percentile_99': lambda x: self._percentile(x, 0.99)
        })
    
    async def process_data(self, 
                          raw_data: Dict[str, Any], 
                          spec: VisualizationSpec) -> VisualizationData:
        """Process raw data according to visualization specification"""
        try:
            processed_data = raw_data.copy()
            
            # Apply data transformations
            for transform in spec.custom_config.get('transformations', []):
                if transform in self.transformations:
                    processed_data = await self.transformations[transform](processed_data, spec)
            
            # Apply filters
            if spec.filters:
                processed_data = await self._apply_filters(processed_data, spec.filters)
            
            # Apply aggregations if specified
            aggregations = spec.custom_config.get('aggregations', {})
            if aggregations:
                processed_data = await self._apply_aggregations(processed_data, aggregations)
            
            # Calculate data quality score
            quality_score = await self._calculate_data_quality(processed_data)
            
            return VisualizationData(
                viz_id=spec.viz_id,
                raw_data=raw_data,
                processed_data=processed_data,
                metadata={
                    'rows': len(processed_data.get('data', [])),
                    'columns': len(processed_data.get('columns', [])),
                    'processing_time': datetime.utcnow().isoformat(),
                    'transformations_applied': spec.custom_config.get('transformations', [])
                },
                last_updated=datetime.utcnow(),
                data_quality_score=quality_score
            )
            
        except Exception as e:
            self.logger.error(f"Data processing failed: {e}")
            # Return minimal data structure
            return VisualizationData(
                viz_id=spec.viz_id,
                raw_data=raw_data,
                processed_data=raw_data,
                metadata={'error': str(e)},
                last_updated=datetime.utcnow(),
                data_quality_score=0.0
            )
    
    async def _apply_filters(self, data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to data"""
        try:
            if not PANDAS_AVAILABLE or 'data' not in data:
                return data
            
            # Convert to DataFrame for easier filtering
            df = pd.DataFrame(data['data'])
            
            for column, filter_config in filters.items():
                if column not in df.columns:
                    continue
                
                filter_type = filter_config.get('type', 'equals')
                filter_value = filter_config.get('value')
                
                if filter_type == 'equals':
                    df = df[df[column] == filter_value]
                elif filter_type == 'not_equals':
                    df = df[df[column] != filter_value]
                elif filter_type == 'greater_than':
                    df = df[df[column] > filter_value]
                elif filter_type == 'less_than':
                    df = df[df[column] < filter_value]
                elif filter_type == 'range':
                    min_val, max_val = filter_value
                    df = df[(df[column] >= min_val) & (df[column] <= max_val)]
                elif filter_type == 'contains':
                    df = df[df[column].astype(str).str.contains(filter_value, na=False)]
                elif filter_type == 'in':
                    df = df[df[column].isin(filter_value)]
            
            # Convert back to dict format
            filtered_data = data.copy()
            filtered_data['data'] = df.to_dict('records')
            
            return filtered_data
            
        except Exception as e:
            self.logger.error(f"Filter application failed: {e}")
            return data
    
    async def _normalize_data(self, data: Dict[str, Any], spec: VisualizationSpec) -> Dict[str, Any]:
        """Normalize numeric data to 0-1 range"""
        try:
            if not PANDAS_AVAILABLE:
                return data
            
            df = pd.DataFrame(data.get('data', []))
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            
            for col in numeric_columns:
                if col in spec.measures:
                    min_val = df[col].min()
                    max_val = df[col].max()
                    if max_val > min_val:
                        df[col] = (df[col] - min_val) / (max_val - min_val)
            
            normalized_data = data.copy()
            normalized_data['data'] = df.to_dict('records')
            
            return normalized_data
            
        except Exception as e:
            self.logger.error(f"Data normalization failed: {e}")
            return data
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if not values or len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(percentile * (len(sorted_values) - 1))
        return sorted_values[index]

class ChartFactory:
    """Factory for creating different types of charts"""
    
    def __init__(self):
        self.chart_builders: Dict[VisualizationType, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
        self._register_chart_builders()
    
    def _register_chart_builders(self):
        """Register chart builders for different visualization types"""
        if PLOTLY_AVAILABLE:
            self.chart_builders.update({
                VisualizationType.TIME_SERIES: self._create_time_series,
                VisualizationType.SCATTER: self._create_scatter_plot,
                VisualizationType.BAR: self._create_bar_chart,
                VisualizationType.HISTOGRAM: self._create_histogram,
                VisualizationType.BOX_PLOT: self._create_box_plot,
                VisualizationType.HEATMAP: self._create_heatmap,
                VisualizationType.TREEMAP: self._create_treemap,
                VisualizationType.SUNBURST: self._create_sunburst,
                VisualizationType.SANKEY: self._create_sankey,
                VisualizationType.THREE_D_SURFACE: self._create_3d_surface,
                VisualizationType.RADAR: self._create_radar_chart,
                VisualizationType.FUNNEL: self._create_funnel_chart,
                VisualizationType.WATERFALL: self._create_waterfall_chart
            })
        
        # Always available fallback
        self.chart_builders[VisualizationType.CUSTOM] = self._create_fallback_chart
    
    async def create_chart(self, 
                          viz_data: VisualizationData, 
                          spec: VisualizationSpec) -> Dict[str, Any]:
        """Create chart based on specification"""
        try:
            chart_builder = self.chart_builders.get(spec.viz_type, self._create_fallback_chart)
            
            # Create the chart
            chart_result = await chart_builder(viz_data, spec)
            
            # Apply common styling and interactivity
            if PLOTLY_AVAILABLE and 'figure' in chart_result:
                await self._apply_common_styling(chart_result['figure'], spec)
                await self._apply_interactivity(chart_result['figure'], spec)
            
            return chart_result
            
        except Exception as e:
            self.logger.error(f"Chart creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    async def _create_time_series(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create time series chart"""
        try:
            data = viz_data.processed_data
            
            if not data or 'data' not in data:
                return await self._create_error_chart("No data available")
            
            df = pd.DataFrame(data['data']) if PANDAS_AVAILABLE else None
            
            if df is None or df.empty:
                return await self._create_error_chart("Empty dataset")
            
            fig = go.Figure()
            
            # Assume first dimension is time, measures are Y values
            time_column = spec.dimensions[0] if spec.dimensions else df.columns[0]
            
            for measure in spec.measures:
                if measure in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df[time_column],
                        y=df[measure],
                        mode='lines+markers',
                        name=measure,
                        line=dict(width=2),
                        marker=dict(size=4)
                    ))
            
            fig.update_layout(
                title=spec.title,
                xaxis_title=time_column,
                yaxis_title="Value",
                hovermode='x unified'
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'export_formats': ['html', 'png', 'svg', 'pdf']
            }
            
        except Exception as e:
            self.logger.error(f"Time series creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    async def _create_scatter_plot(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create scatter plot"""
        try:
            data = viz_data.processed_data
            df = pd.DataFrame(data['data']) if PANDAS_AVAILABLE and 'data' in data else None
            
            if df is None or len(spec.dimensions) < 2 or len(spec.measures) < 1:
                return await self._create_error_chart("Insufficient data for scatter plot")
            
            x_col = spec.dimensions[0]
            y_col = spec.measures[0]
            
            # Optional color/size encoding
            color_col = spec.dimensions[1] if len(spec.dimensions) > 1 else None
            size_col = spec.measures[1] if len(spec.measures) > 1 else None
            
            scatter_kwargs = {
                'x': df[x_col],
                'y': df[y_col],
                'mode': 'markers',
                'marker': dict(size=8)
            }
            
            if color_col and color_col in df.columns:
                scatter_kwargs['marker']['color'] = df[color_col]
                scatter_kwargs['marker']['colorscale'] = self._get_color_scale(spec.color_scheme)
                scatter_kwargs['marker']['showscale'] = True
            
            if size_col and size_col in df.columns:
                scatter_kwargs['marker']['size'] = df[size_col]
                scatter_kwargs['marker']['sizemode'] = 'diameter'
                scatter_kwargs['marker']['sizeref'] = 2. * max(df[size_col]) / (40. ** 2)
            
            fig = go.Figure(data=go.Scatter(**scatter_kwargs))
            
            fig.update_layout(
                title=spec.title,
                xaxis_title=x_col,
                yaxis_title=y_col
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'export_formats': ['html', 'png', 'svg', 'pdf']
            }
            
        except Exception as e:
            self.logger.error(f"Scatter plot creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    async def _create_heatmap(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create heatmap visualization"""
        try:
            data = viz_data.processed_data
            
            if 'correlation_matrix' in data:
                # Correlation heatmap
                z_data = data['correlation_matrix']
                x_labels = data.get('columns', [])
                y_labels = data.get('columns', [])
            elif 'matrix' in data:
                # Generic matrix heatmap
                z_data = data['matrix']
                x_labels = data.get('x_labels', [])
                y_labels = data.get('y_labels', [])
            else:
                return await self._create_error_chart("No matrix data for heatmap")
            
            fig = go.Figure(data=go.Heatmap(
                z=z_data,
                x=x_labels,
                y=y_labels,
                colorscale=self._get_color_scale(spec.color_scheme),
                showscale=True,
                hoverongaps=False
            ))
            
            fig.update_layout(
                title=spec.title,
                xaxis_nticks=36
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'export_formats': ['html', 'png', 'svg']
            }
            
        except Exception as e:
            self.logger.error(f"Heatmap creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    async def _create_3d_surface(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create 3D surface plot"""
        try:
            data = viz_data.processed_data
            
            if 'z_matrix' not in data:
                return await self._create_error_chart("No Z-matrix data for 3D surface")
            
            z_data = data['z_matrix']
            x_data = data.get('x_values', list(range(len(z_data[0]))))
            y_data = data.get('y_values', list(range(len(z_data))))
            
            fig = go.Figure(data=[go.Surface(
                z=z_data,
                x=x_data,
                y=y_data,
                colorscale=self._get_color_scale(spec.color_scheme)
            )])
            
            fig.update_layout(
                title=spec.title,
                scene=dict(
                    xaxis_title=spec.dimensions[0] if spec.dimensions else 'X',
                    yaxis_title=spec.dimensions[1] if len(spec.dimensions) > 1 else 'Y',
                    zaxis_title=spec.measures[0] if spec.measures else 'Z'
                )
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'export_formats': ['html', 'png']
            }
            
        except Exception as e:
            self.logger.error(f"3D surface creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    async def _create_sankey(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create Sankey diagram"""
        try:
            data = viz_data.processed_data
            
            if not all(key in data for key in ['source', 'target', 'value']):
                return await self._create_error_chart("Missing source, target, or value data for Sankey")
            
            # Get unique nodes
            all_nodes = list(set(data['source'] + data['target']))
            node_dict = {node: i for i, node in enumerate(all_nodes)}
            
            # Map source/target to indices
            source_indices = [node_dict[node] for node in data['source']]
            target_indices = [node_dict[node] for node in data['target']]
            
            fig = go.Figure(data=[go.Sankey(
                node=dict(
                    pad=15,
                    thickness=20,
                    line=dict(color="black", width=0.5),
                    label=all_nodes,
                    color="blue"
                ),
                link=dict(
                    source=source_indices,
                    target=target_indices,
                    value=data['value']
                )
            )])
            
            fig.update_layout(
                title_text=spec.title,
                font_size=10
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'export_formats': ['html', 'png', 'svg']
            }
            
        except Exception as e:
            self.logger.error(f"Sankey creation failed: {e}")
            return await self._create_error_chart(str(e))
    
    def _get_color_scale(self, color_scheme: ColorScheme) -> str:
        """Get Plotly color scale from scheme"""
        color_map = {
            ColorScheme.VIRIDIS: 'Viridis',
            ColorScheme.PLASMA: 'Plasma',
            ColorScheme.INFERNO: 'Inferno',
            ColorScheme.MAGMA: 'Magma',
            ColorScheme.BLUES: 'Blues',
            ColorScheme.REDS: 'Reds',
            ColorScheme.GREENS: 'Greens'
        }
        return color_map.get(color_scheme, 'Viridis')
    
    async def _apply_common_styling(self, fig: go.Figure, spec: VisualizationSpec):
        """Apply common styling to figure"""
        try:
            styling = spec.styling
            
            # Font styling
            if 'font_family' in styling:
                fig.update_layout(font_family=styling['font_family'])
            
            if 'font_size' in styling:
                fig.update_layout(font_size=styling['font_size'])
            
            # Background colors
            if 'background_color' in styling:
                fig.update_layout(plot_bgcolor=styling['background_color'])
            
            if 'paper_bgcolor' in styling:
                fig.update_layout(paper_bgcolor=styling['paper_bgcolor'])
            
            # Grid styling
            if 'show_grid' in styling:
                fig.update_xaxes(showgrid=styling['show_grid'])
                fig.update_yaxes(showgrid=styling['show_grid'])
            
            # Title styling
            if 'title_font_size' in styling:
                fig.update_layout(title_font_size=styling['title_font_size'])
            
        except Exception as e:
            self.logger.error(f"Styling application failed: {e}")
    
    async def _apply_interactivity(self, fig: go.Figure, spec: VisualizationSpec):
        """Apply interactivity settings to figure"""
        try:
            if spec.interactivity == InteractivityLevel.STATIC:
                # Remove all interactivity
                fig.update_layout(
                    showlegend=True,
                    xaxis=dict(fixedrange=True),
                    yaxis=dict(fixedrange=True)
                )
                fig.update_traces(hoverinfo='skip')
                
            elif spec.interactivity == InteractivityLevel.BASIC:
                # Basic hover and zoom
                fig.update_layout(hovermode='closest')
                
            elif spec.interactivity in [InteractivityLevel.INTERMEDIATE, InteractivityLevel.ADVANCED, InteractivityLevel.FULL]:
                # Full interactivity
                fig.update_layout(
                    hovermode='closest',
                    clickmode='event+select'
                )
            
        except Exception as e:
            self.logger.error(f"Interactivity application failed: {e}")
    
    async def _create_error_chart(self, error_message: str) -> Dict[str, Any]:
        """Create error visualization"""
        if PLOTLY_AVAILABLE:
            fig = go.Figure()
            fig.add_annotation(
                text=f"Error: {error_message}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                xanchor='center', yanchor='middle',
                showarrow=False,
                font=dict(size=16, color="red")
            )
            fig.update_layout(
                title="Visualization Error",
                showlegend=False,
                xaxis=dict(showticklabels=False, showgrid=False),
                yaxis=dict(showticklabels=False, showgrid=False)
            )
            
            return {
                'figure': fig,
                'chart_type': 'plotly',
                'error': error_message
            }
        else:
            return {
                'chart_type': 'error',
                'error': error_message,
                'html': f'<div class="error-chart">Error: {error_message}</div>'
            }
    
    async def _create_fallback_chart(self, viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
        """Create fallback chart when specific type is not available"""
        return {
            'chart_type': 'fallback',
            'html': f"""
            <div class="fallback-chart">
                <h3>{spec.title}</h3>
                <p>Visualization type: {spec.viz_type.value}</p>
                <p>Data points: {len(viz_data.processed_data.get('data', []))}</p>
                <div class="chart-placeholder">
                    📊 Advanced visualization not available
                </div>
            </div>
            """
        }

class InteractiveVisualization:
    """Interactive visualization with real-time updates"""
    
    def __init__(self):
        self.active_visualizations: Dict[str, Dict[str, Any]] = {}
        self.interaction_handlers: Dict[str, List[Callable]] = {}
        self.update_queues: Dict[str, asyncio.Queue] = {}
        self.logger = logging.getLogger(__name__)
    
    async def create_interactive_viz(self, 
                                   spec: VisualizationSpec,
                                   initial_data: VisualizationData) -> str:
        """Create interactive visualization"""
        try:
            viz_id = spec.viz_id
            
            # Create chart factory
            chart_factory = ChartFactory()
            chart_result = await chart_factory.create_chart(initial_data, spec)
            
            # Store visualization state
            self.active_visualizations[viz_id] = {
                'spec': spec,
                'chart_result': chart_result,
                'last_update': datetime.utcnow(),
                'interaction_count': 0
            }
            
            # Setup update queue if real-time
            if spec.refresh_interval:
                self.update_queues[viz_id] = asyncio.Queue()
                asyncio.create_task(self._real_time_update_loop(viz_id))
            
            # Generate interactive HTML
            html_content = await self._generate_interactive_html(viz_id, chart_result, spec)
            
            self.logger.info(f"Interactive visualization created: {viz_id}")
            return html_content
            
        except Exception as e:
            self.logger.error(f"Interactive visualization creation failed: {e}")
            return f"<div class='error'>Failed to create visualization: {e}</div>"
    
    async def handle_interaction(self, interaction_event: InteractionEvent):
        """Handle interaction event"""
        try:
            viz_id = interaction_event.viz_id
            
            if viz_id not in self.active_visualizations:
                return
            
            # Update interaction count
            self.active_visualizations[viz_id]['interaction_count'] += 1
            
            # Call registered handlers
            if viz_id in self.interaction_handlers:
                for handler in self.interaction_handlers[viz_id]:
                    await handler(interaction_event)
            
            self.logger.debug(f"Interaction handled: {interaction_event.event_type} on {viz_id}")
            
        except Exception as e:
            self.logger.error(f"Interaction handling failed: {e}")
    
    async def update_visualization_data(self, viz_id: str, new_data: VisualizationData):
        """Update visualization with new data"""
        try:
            if viz_id not in self.active_visualizations:
                return
            
            viz_state = self.active_visualizations[viz_id]
            spec = viz_state['spec']
            
            # Recreate chart with new data
            chart_factory = ChartFactory()
            new_chart_result = await chart_factory.create_chart(new_data, spec)
            
            # Update state
            viz_state['chart_result'] = new_chart_result
            viz_state['last_update'] = datetime.utcnow()
            
            # Queue update if real-time
            if viz_id in self.update_queues:
                await self.update_queues[viz_id].put(new_chart_result)
            
            self.logger.debug(f"Visualization data updated: {viz_id}")
            
        except Exception as e:
            self.logger.error(f"Visualization data update failed: {e}")
    
    async def _real_time_update_loop(self, viz_id: str):
        """Real-time update loop for visualization"""
        try:
            while viz_id in self.active_visualizations:
                if viz_id in self.update_queues:
                    # Wait for update
                    new_chart = await self.update_queues[viz_id].get()
                    
                    # Broadcast update to connected clients
                    await self._broadcast_update(viz_id, new_chart)
                
                # Wait for refresh interval
                spec = self.active_visualizations[viz_id]['spec']
                await asyncio.sleep(spec.refresh_interval or 30)
                
        except Exception as e:
            self.logger.error(f"Real-time update loop failed: {e}")
    
    async def _generate_interactive_html(self, 
                                        viz_id: str, 
                                        chart_result: Dict[str, Any], 
                                        spec: VisualizationSpec) -> str:
        """Generate interactive HTML for visualization"""
        try:
            if chart_result.get('chart_type') == 'plotly' and 'figure' in chart_result:
                # Plotly visualization
                fig = chart_result['figure']
                
                # Convert to HTML with interactivity
                html_content = pio.to_html(
                    fig,
                    include_plotlyjs='cdn',
                    div_id=f"viz_{viz_id}",
                    config={
                        'displayModeBar': spec.interactivity != InteractivityLevel.STATIC,
                        'responsive': True,
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': f'{spec.title}_{datetime.now().strftime("%Y%m%d")}',
                            'height': 500,
                            'width': 700,
                            'scale': 1
                        }
                    }
                )
                
                # Add interaction handling script if needed
                if spec.interactivity in [InteractivityLevel.ADVANCED, InteractivityLevel.FULL]:
                    interaction_script = f"""
                    <script>
                        document.getElementById('viz_{viz_id}').on('plotly_click', function(data) {{
                            console.log('Chart clicked:', data);
                            // Send interaction event to server
                        }});
                        
                        document.getElementById('viz_{viz_id}').on('plotly_hover', function(data) {{
                            console.log('Chart hovered:', data);
                            // Send hover event to server
                        }});
                    </script>
                    """
                    html_content += interaction_script
                
                return html_content
                
            else:
                # Fallback HTML
                return chart_result.get('html', '<div>Chart not available</div>')
            
        except Exception as e:
            self.logger.error(f"Interactive HTML generation failed: {e}")
            return f"<div class='error'>HTML generation failed: {e}</div>"

class CustomVisualization:
    """Custom visualization creation and management"""
    
    def __init__(self):
        self.custom_viz_types: Dict[str, Callable] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.logger = logging.getLogger(__name__)
    
    async def register_custom_type(self, 
                                  type_name: str, 
                                  builder_function: Callable) -> bool:
        """Register custom visualization type"""
        try:
            self.custom_viz_types[type_name] = builder_function
            self.logger.info(f"Custom visualization type registered: {type_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Custom type registration failed: {e}")
            return False
    
    async def create_template(self, 
                             template_name: str, 
                             spec: VisualizationSpec) -> bool:
        """Create reusable visualization template"""
        try:
            template_config = {
                'spec': asdict(spec),
                'created_at': datetime.utcnow().isoformat(),
                'usage_count': 0
            }
            
            self.templates[template_name] = template_config
            self.logger.info(f"Visualization template created: {template_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Template creation failed: {e}")
            return False
    
    async def create_from_template(self, 
                                  template_name: str, 
                                  viz_id: str,
                                  data_overrides: Optional[Dict[str, Any]] = None) -> Optional[VisualizationSpec]:
        """Create visualization from template"""
        try:
            if template_name not in self.templates:
                return None
            
            template = self.templates[template_name]
            spec_data = template['spec'].copy()
            
            # Apply overrides
            if data_overrides:
                spec_data.update(data_overrides)
            
            # Update ID
            spec_data['viz_id'] = viz_id
            
            # Update usage count
            template['usage_count'] += 1
            
            # Create new spec
            spec = VisualizationSpec(**spec_data)
            
            self.logger.info(f"Visualization created from template: {template_name} -> {viz_id}")
            return spec
            
        except Exception as e:
            self.logger.error(f"Template instantiation failed: {e}")
            return None

class VisualizationEngine:
    """Main visualization engine orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Initialize components
        self.data_processor = DataProcessor()
        self.chart_factory = ChartFactory()
        self.interactive_viz = InteractiveVisualization()
        self.custom_viz = CustomVisualization()
        
        self.visualizations: Dict[str, VisualizationData] = {}
        self.export_cache: Dict[str, Dict[str, bytes]] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize visualization engine"""
        try:
            self.logger.info("Initializing advanced visualization engine...")
            
            # Setup default templates
            await self._create_default_templates()
            
            # Register custom types
            await self._register_default_custom_types()
            
            self.logger.info("Visualization engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Visualization engine initialization failed: {e}")
            return False
    
    async def create_visualization(self, 
                                  spec: VisualizationSpec,
                                  raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create complete visualization"""
        try:
            # Process data
            viz_data = await self.data_processor.process_data(raw_data, spec)
            
            # Store visualization data
            self.visualizations[spec.viz_id] = viz_data
            
            # Create chart
            chart_result = await self.chart_factory.create_chart(viz_data, spec)
            
            # Create interactive version if needed
            interactive_html = None
            if spec.interactivity != InteractivityLevel.STATIC:
                interactive_html = await self.interactive_viz.create_interactive_viz(spec, viz_data)
            
            # Prepare result
            result = {
                'viz_id': spec.viz_id,
                'chart_result': chart_result,
                'interactive_html': interactive_html,
                'data_quality_score': viz_data.data_quality_score,
                'metadata': viz_data.metadata,
                'export_options': chart_result.get('export_formats', []),
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Visualization created: {spec.viz_id} ({spec.viz_type.value})")
            return result
            
        except Exception as e:
            self.logger.error(f"Visualization creation failed: {e}")
            return {
                'viz_id': spec.viz_id,
                'error': str(e),
                'created_at': datetime.utcnow().isoformat()
            }
    
    async def export_visualization(self, 
                                  viz_id: str, 
                                  export_format: str) -> Optional[bytes]:
        """Export visualization in specified format"""
        try:
            if viz_id not in self.visualizations:
                return None
            
            # Check cache first
            cache_key = f"{viz_id}_{export_format}"
            if cache_key in self.export_cache:
                return self.export_cache[cache_key]
            
            viz_data = self.visualizations[viz_id]
            
            # Export based on format
            if export_format == 'png' and PLOTLY_AVAILABLE:
                # PNG export
                chart_result = await self.chart_factory.create_chart(
                    viz_data, 
                    VisualizationSpec(
                        viz_id=viz_id,
                        title="Export",
                        viz_type=VisualizationType.CUSTOM,
                        data_source="",
                        dimensions=[],
                        measures=[],
                        color_scheme=ColorScheme.DEFAULT,
                        interactivity=InteractivityLevel.STATIC,
                        filters={},
                        styling={},
                        layout_config={}
                    )
                )
                
                if 'figure' in chart_result:
                    img_bytes = pio.to_image(chart_result['figure'], format='png')
                    self.export_cache[cache_key] = img_bytes
                    return img_bytes
            
            elif export_format == 'svg' and PLOTLY_AVAILABLE:
                # SVG export
                chart_result = await self.chart_factory.create_chart(viz_data, VisualizationSpec(
                    viz_id=viz_id, title="Export", viz_type=VisualizationType.CUSTOM,
                    data_source="", dimensions=[], measures=[], 
                    color_scheme=ColorScheme.DEFAULT, interactivity=InteractivityLevel.STATIC,
                    filters={}, styling={}, layout_config={}
                ))
                
                if 'figure' in chart_result:
                    svg_bytes = pio.to_image(chart_result['figure'], format='svg')
                    self.export_cache[cache_key] = svg_bytes
                    return svg_bytes
            
            elif export_format == 'json':
                # JSON export of data
                json_data = json.dumps(asdict(viz_data), indent=2, default=str)
                json_bytes = json_data.encode('utf-8')
                self.export_cache[cache_key] = json_bytes
                return json_bytes
            
            return None
            
        except Exception as e:
            self.logger.error(f"Visualization export failed: {e}")
            return None
    
    async def _create_default_templates(self):
        """Create default visualization templates"""
        # System metrics dashboard template
        system_template = VisualizationSpec(
            viz_id="template_system_metrics",
            title="System Metrics Dashboard",
            viz_type=VisualizationType.TIME_SERIES,
            data_source="system_metrics",
            dimensions=["timestamp"],
            measures=["cpu_percent", "memory_percent", "disk_percent"],
            color_scheme=ColorScheme.VIRIDIS,
            interactivity=InteractivityLevel.BASIC,
            filters={},
            styling={"font_family": "Arial", "font_size": 12},
            layout_config={"height": 400},
            refresh_interval=30
        )
        
        await self.custom_viz.create_template("system_metrics", system_template)
    
    async def _register_default_custom_types(self):
        """Register default custom visualization types"""
        # Real-time meter
        async def create_realtime_meter(viz_data: VisualizationData, spec: VisualizationSpec) -> Dict[str, Any]:
            value = viz_data.processed_data.get('current_value', 0)
            max_value = viz_data.processed_data.get('max_value', 100)
            
            html = f"""
            <div class="realtime-meter">
                <div class="meter-title">{spec.title}</div>
                <div class="meter-gauge">
                    <div class="meter-fill" style="width: {(value/max_value)*100}%"></div>
                </div>
                <div class="meter-value">{value} / {max_value}</div>
            </div>
            """
            
            return {'chart_type': 'custom', 'html': html}
        
        await self.custom_viz.register_custom_type('realtime_meter', create_realtime_meter)