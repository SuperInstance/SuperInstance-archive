"""
Advanced Dashboard Engine
Real-time interactive dashboards with customizable widgets and layouts
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
import hashlib
import base64

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

logger = logging.getLogger(__name__)

class WidgetType(Enum):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart" 
    PIE_CHART = "pie_chart"
    SCATTER_PLOT = "scatter_plot"
    HEATMAP = "heatmap"
    GAUGE = "gauge"
    TABLE = "table"
    METRIC = "metric"
    LOG_VIEWER = "log_viewer"
    ALERT_PANEL = "alert_panel"
    SYSTEM_STATUS = "system_status"
    CUSTOM = "custom"

class LayoutType(Enum):
    GRID = "grid"
    MASONRY = "masonry"
    TABS = "tabs"
    ACCORDION = "accordion"
    SPLIT = "split"

class ThemeType(Enum):
    LIGHT = "light"
    DARK = "dark"
    AUTO = "auto"
    CUSTOM = "custom"

class RefreshInterval(Enum):
    REAL_TIME = 1      # 1 second
    FAST = 5          # 5 seconds
    NORMAL = 30       # 30 seconds
    SLOW = 60         # 1 minute
    VERY_SLOW = 300   # 5 minutes
    MANUAL = 0        # Manual refresh only

@dataclass
class WidgetConfig:
    widget_id: str
    title: str
    widget_type: WidgetType
    data_source: str
    query: str
    position: Dict[str, int]  # x, y, width, height
    refresh_interval: RefreshInterval
    style_config: Dict[str, Any]
    filter_config: Dict[str, Any]
    alert_config: Optional[Dict[str, Any]] = None
    custom_options: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DashboardConfig:
    dashboard_id: str
    name: str
    description: str
    layout_type: LayoutType
    theme: ThemeType
    widgets: List[WidgetConfig]
    global_filters: Dict[str, Any]
    auto_refresh: bool
    refresh_interval: RefreshInterval
    permissions: Dict[str, List[str]]
    tags: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

@dataclass
class DashboardData:
    dashboard_id: str
    widget_data: Dict[str, Any]
    last_updated: datetime
    data_sources: Dict[str, str]
    refresh_status: Dict[str, str]

class ChartGenerator:
    """Advanced chart generation with Plotly"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Chart themes and styles
        self.themes = {
            'light': {
                'background_color': '#ffffff',
                'grid_color': '#e0e0e0',
                'text_color': '#333333',
                'accent_color': '#007acc'
            },
            'dark': {
                'background_color': '#1e1e1e',
                'grid_color': '#404040',
                'text_color': '#ffffff',
                'accent_color': '#00d4ff'
            }
        }
        
        # Color palettes
        self.color_palettes = {
            'default': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
            'pastel': ['#8dd3c7', '#ffffb3', '#bebada', '#fb8072', '#80b1d3'],
            'vibrant': ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00'],
            'corporate': ['#003f5c', '#374c80', '#7a5195', '#bc5090', '#ef5675']
        }
    
    async def generate_chart(self, 
                            widget_config: WidgetConfig, 
                            data: Dict[str, Any],
                            theme: str = 'light') -> Optional[str]:
        """Generate chart based on widget configuration and data"""
        try:
            if not PLOTLY_AVAILABLE:
                self.logger.warning("Plotly not available, generating fallback chart")
                return await self._generate_fallback_chart(widget_config, data)
            
            chart_type = widget_config.widget_type
            
            if chart_type == WidgetType.LINE_CHART:
                fig = await self._create_line_chart(widget_config, data, theme)
            elif chart_type == WidgetType.BAR_CHART:
                fig = await self._create_bar_chart(widget_config, data, theme)
            elif chart_type == WidgetType.PIE_CHART:
                fig = await self._create_pie_chart(widget_config, data, theme)
            elif chart_type == WidgetType.SCATTER_PLOT:
                fig = await self._create_scatter_plot(widget_config, data, theme)
            elif chart_type == WidgetType.HEATMAP:
                fig = await self._create_heatmap(widget_config, data, theme)
            elif chart_type == WidgetType.GAUGE:
                fig = await self._create_gauge(widget_config, data, theme)
            else:
                return await self._generate_fallback_chart(widget_config, data)
            
            if fig:
                # Apply theme and styling
                await self._apply_chart_theme(fig, theme, widget_config.style_config)
                
                # Convert to HTML
                html_chart = pio.to_html(fig, include_plotlyjs='cdn', div_id=f"chart_{widget_config.widget_id}")
                return html_chart
            
            return None
            
        except Exception as e:
            self.logger.error(f"Chart generation failed: {e}")
            return await self._generate_fallback_chart(widget_config, data)
    
    async def _create_line_chart(self, 
                                widget_config: WidgetConfig, 
                                data: Dict[str, Any], 
                                theme: str) -> Optional[go.Figure]:
        """Create line chart"""
        try:
            if not data or 'x' not in data or 'y' not in data:
                return None
            
            fig = go.Figure()
            
            # Handle multiple series
            if isinstance(data['y'], dict):
                for series_name, y_values in data['y'].items():
                    fig.add_trace(go.Scatter(
                        x=data['x'],
                        y=y_values,
                        mode='lines+markers',
                        name=series_name,
                        line=dict(width=2),
                        marker=dict(size=6)
                    ))
            else:
                fig.add_trace(go.Scatter(
                    x=data['x'],
                    y=data['y'],
                    mode='lines+markers',
                    name=widget_config.title,
                    line=dict(width=2),
                    marker=dict(size=6)
                ))
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Line chart creation failed: {e}")
            return None
    
    async def _create_bar_chart(self, 
                               widget_config: WidgetConfig, 
                               data: Dict[str, Any], 
                               theme: str) -> Optional[go.Figure]:
        """Create bar chart"""
        try:
            if not data or 'x' not in data or 'y' not in data:
                return None
            
            fig = go.Figure()
            
            # Handle multiple series
            if isinstance(data['y'], dict):
                for series_name, y_values in data['y'].items():
                    fig.add_trace(go.Bar(
                        x=data['x'],
                        y=y_values,
                        name=series_name,
                        opacity=0.8
                    ))
            else:
                fig.add_trace(go.Bar(
                    x=data['x'],
                    y=data['y'],
                    name=widget_config.title,
                    opacity=0.8
                ))
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Bar chart creation failed: {e}")
            return None
    
    async def _create_pie_chart(self, 
                               widget_config: WidgetConfig, 
                               data: Dict[str, Any], 
                               theme: str) -> Optional[go.Figure]:
        """Create pie chart"""
        try:
            if not data or 'labels' not in data or 'values' not in data:
                return None
            
            fig = go.Figure(data=[go.Pie(
                labels=data['labels'],
                values=data['values'],
                hole=0.3,  # Donut chart
                textinfo='label+percent',
                textposition='inside'
            )])
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Pie chart creation failed: {e}")
            return None
    
    async def _create_gauge(self, 
                           widget_config: WidgetConfig, 
                           data: Dict[str, Any], 
                           theme: str) -> Optional[go.Figure]:
        """Create gauge chart"""
        try:
            if not data or 'value' not in data:
                return None
            
            value = data['value']
            max_value = data.get('max_value', 100)
            min_value = data.get('min_value', 0)
            
            fig = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=value,
                delta={'reference': data.get('reference', 0)},
                gauge={
                    'axis': {'range': [min_value, max_value]},
                    'bar': {'color': self.themes[theme]['accent_color']},
                    'steps': [
                        {'range': [min_value, max_value * 0.5], 'color': "lightgray"},
                        {'range': [max_value * 0.5, max_value * 0.8], 'color': "yellow"},
                        {'range': [max_value * 0.8, max_value], 'color': "red"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': max_value * 0.9
                    }
                },
                title={'text': widget_config.title}
            ))
            
            return fig
            
        except Exception as e:
            self.logger.error(f"Gauge chart creation failed: {e}")
            return None
    
    async def _apply_chart_theme(self, 
                                fig: go.Figure, 
                                theme: str, 
                                style_config: Dict[str, Any]):
        """Apply theme and styling to chart"""
        try:
            theme_config = self.themes.get(theme, self.themes['light'])
            
            fig.update_layout(
                plot_bgcolor=theme_config['background_color'],
                paper_bgcolor=theme_config['background_color'],
                font_color=theme_config['text_color'],
                font_family=style_config.get('font_family', 'Arial, sans-serif'),
                font_size=style_config.get('font_size', 12),
                showlegend=style_config.get('show_legend', True),
                margin=dict(t=50, l=50, r=50, b=50)
            )
            
            # Update axes styling
            fig.update_xaxes(
                gridcolor=theme_config['grid_color'],
                zerolinecolor=theme_config['grid_color']
            )
            fig.update_yaxes(
                gridcolor=theme_config['grid_color'],
                zerolinecolor=theme_config['grid_color']
            )
            
        except Exception as e:
            self.logger.error(f"Theme application failed: {e}")
    
    async def _generate_fallback_chart(self, 
                                      widget_config: WidgetConfig, 
                                      data: Dict[str, Any]) -> str:
        """Generate fallback chart when Plotly is not available"""
        return f"""
        <div class="fallback-chart" id="chart_{widget_config.widget_id}">
            <h3>{widget_config.title}</h3>
            <p>Chart type: {widget_config.widget_type.value}</p>
            <p>Data points: {len(data) if data else 0}</p>
            <div class="chart-placeholder">
                📊 Chart visualization not available
            </div>
        </div>
        """

class WidgetManager:
    """Widget management and data binding"""
    
    def __init__(self, chart_generator: ChartGenerator):
        self.chart_generator = chart_generator
        self.widgets: Dict[str, WidgetConfig] = {}
        self.widget_data: Dict[str, Any] = {}
        self.data_sources: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
    
    async def register_widget(self, widget_config: WidgetConfig) -> bool:
        """Register new widget"""
        try:
            # Validate widget configuration
            if not self._validate_widget_config(widget_config):
                return False
            
            # Store widget
            self.widgets[widget_config.widget_id] = widget_config
            
            # Initialize widget data
            self.widget_data[widget_config.widget_id] = {
                'data': {},
                'last_updated': datetime.utcnow(),
                'status': 'initialized'
            }
            
            self.logger.info(f"Widget registered: {widget_config.title}")
            return True
            
        except Exception as e:
            self.logger.error(f"Widget registration failed: {e}")
            return False
    
    async def update_widget_data(self, widget_id: str, data: Dict[str, Any]) -> bool:
        """Update widget data"""
        try:
            if widget_id not in self.widgets:
                return False
            
            self.widget_data[widget_id] = {
                'data': data,
                'last_updated': datetime.utcnow(),
                'status': 'updated'
            }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Widget data update failed: {e}")
            return False
    
    async def render_widget(self, 
                           widget_id: str, 
                           theme: str = 'light') -> Optional[str]:
        """Render widget to HTML"""
        try:
            if widget_id not in self.widgets:
                return None
            
            widget_config = self.widgets[widget_id]
            widget_data_info = self.widget_data.get(widget_id, {})
            widget_data = widget_data_info.get('data', {})
            
            if widget_config.widget_type in [WidgetType.LINE_CHART, WidgetType.BAR_CHART, 
                                           WidgetType.PIE_CHART, WidgetType.SCATTER_PLOT,
                                           WidgetType.HEATMAP, WidgetType.GAUGE]:
                # Chart widgets
                return await self.chart_generator.generate_chart(widget_config, widget_data, theme)
            
            elif widget_config.widget_type == WidgetType.METRIC:
                return await self._render_metric_widget(widget_config, widget_data, theme)
            
            elif widget_config.widget_type == WidgetType.TABLE:
                return await self._render_table_widget(widget_config, widget_data, theme)
            
            elif widget_config.widget_type == WidgetType.SYSTEM_STATUS:
                return await self._render_status_widget(widget_config, widget_data, theme)
            
            else:
                return await self._render_generic_widget(widget_config, widget_data, theme)
            
        except Exception as e:
            self.logger.error(f"Widget rendering failed: {e}")
            return self._render_error_widget(widget_id, str(e))
    
    async def _render_metric_widget(self, 
                                   widget_config: WidgetConfig, 
                                   data: Dict[str, Any], 
                                   theme: str) -> str:
        """Render metric widget"""
        value = data.get('value', 0)
        unit = data.get('unit', '')
        change = data.get('change', 0)
        change_percent = data.get('change_percent', 0)
        
        change_class = 'positive' if change >= 0 else 'negative'
        change_symbol = '↑' if change >= 0 else '↓'
        
        return f"""
        <div class="metric-widget {theme}" id="widget_{widget_config.widget_id}">
            <div class="metric-header">
                <h3>{widget_config.title}</h3>
            </div>
            <div class="metric-value">
                <span class="value">{value}</span>
                <span class="unit">{unit}</span>
            </div>
            <div class="metric-change {change_class}">
                <span class="change-symbol">{change_symbol}</span>
                <span class="change-value">{abs(change)} ({abs(change_percent):.1f}%)</span>
            </div>
        </div>
        """
    
    async def _render_table_widget(self, 
                                  widget_config: WidgetConfig, 
                                  data: Dict[str, Any], 
                                  theme: str) -> str:
        """Render table widget"""
        if not data or 'columns' not in data or 'rows' not in data:
            return self._render_error_widget(widget_config.widget_id, "No table data available")
        
        columns = data['columns']
        rows = data['rows']
        
        table_html = f"""
        <div class="table-widget {theme}" id="widget_{widget_config.widget_id}">
            <div class="table-header">
                <h3>{widget_config.title}</h3>
            </div>
            <div class="table-container">
                <table class="data-table">
                    <thead>
                        <tr>
                            {''.join(f'<th>{col}</th>' for col in columns)}
                        </tr>
                    </thead>
                    <tbody>
        """
        
        for row in rows[:100]:  # Limit to 100 rows for performance
            table_html += "<tr>"
            for cell in row:
                table_html += f"<td>{cell}</td>"
            table_html += "</tr>"
        
        table_html += """
                    </tbody>
                </table>
            </div>
        </div>
        """
        
        return table_html
    
    def _render_error_widget(self, widget_id: str, error_msg: str) -> str:
        """Render error widget"""
        return f"""
        <div class="error-widget" id="widget_{widget_id}">
            <div class="error-header">
                <h3>Widget Error</h3>
            </div>
            <div class="error-message">
                <p>{error_msg}</p>
            </div>
        </div>
        """
    
    def _validate_widget_config(self, widget_config: WidgetConfig) -> bool:
        """Validate widget configuration"""
        if not widget_config.widget_id or not widget_config.title:
            return False
        
        if not widget_config.data_source:
            return False
        
        if not isinstance(widget_config.position, dict):
            return False
        
        required_position_keys = ['x', 'y', 'width', 'height']
        if not all(key in widget_config.position for key in required_position_keys):
            return False
        
        return True

class RealTimeUpdater:
    """Real-time dashboard updates"""
    
    def __init__(self, widget_manager: WidgetManager):
        self.widget_manager = widget_manager
        self.update_tasks: Dict[str, asyncio.Task] = {}
        self.websocket_connections: Set[Any] = set()
        self.logger = logging.getLogger(__name__)
    
    async def start_real_time_updates(self, dashboard_config: DashboardConfig):
        """Start real-time updates for dashboard widgets"""
        try:
            for widget in dashboard_config.widgets:
                if widget.refresh_interval != RefreshInterval.MANUAL:
                    task = asyncio.create_task(
                        self._widget_update_loop(widget)
                    )
                    self.update_tasks[widget.widget_id] = task
            
            self.logger.info(f"Started real-time updates for {len(self.update_tasks)} widgets")
            
        except Exception as e:
            self.logger.error(f"Failed to start real-time updates: {e}")
    
    async def stop_real_time_updates(self):
        """Stop all real-time update tasks"""
        try:
            for task in self.update_tasks.values():
                task.cancel()
            
            # Wait for tasks to complete
            await asyncio.gather(*self.update_tasks.values(), return_exceptions=True)
            
            self.update_tasks.clear()
            self.logger.info("Stopped all real-time update tasks")
            
        except Exception as e:
            self.logger.error(f"Error stopping real-time updates: {e}")
    
    async def _widget_update_loop(self, widget_config: WidgetConfig):
        """Update loop for individual widget"""
        try:
            while True:
                # Update widget data
                await self._update_widget_data(widget_config)
                
                # Broadcast update to connected clients
                await self._broadcast_widget_update(widget_config.widget_id)
                
                # Wait for next update
                await asyncio.sleep(widget_config.refresh_interval.value)
                
        except asyncio.CancelledError:
            self.logger.info(f"Update loop cancelled for widget: {widget_config.widget_id}")
        except Exception as e:
            self.logger.error(f"Widget update loop error: {e}")
    
    async def _update_widget_data(self, widget_config: WidgetConfig):
        """Update data for specific widget"""
        try:
            # This would fetch data from the configured data source
            # For now, generate mock data
            mock_data = await self._generate_mock_data(widget_config)
            
            await self.widget_manager.update_widget_data(
                widget_config.widget_id,
                mock_data
            )
            
        except Exception as e:
            self.logger.error(f"Widget data update failed: {e}")
    
    async def _generate_mock_data(self, widget_config: WidgetConfig) -> Dict[str, Any]:
        """Generate mock data for demonstration"""
        import random
        import time
        
        current_time = datetime.utcnow()
        
        if widget_config.widget_type == WidgetType.LINE_CHART:
            return {
                'x': [current_time - timedelta(minutes=i) for i in range(10, 0, -1)],
                'y': [random.randint(50, 100) for _ in range(10)]
            }
        
        elif widget_config.widget_type == WidgetType.METRIC:
            return {
                'value': random.randint(0, 100),
                'unit': '%',
                'change': random.randint(-10, 10),
                'change_percent': random.uniform(-5, 5)
            }
        
        elif widget_config.widget_type == WidgetType.PIE_CHART:
            return {
                'labels': ['Success', 'Warning', 'Error'],
                'values': [random.randint(10, 50), random.randint(5, 20), random.randint(1, 10)]
            }
        
        return {}

class DashboardEngine:
    """Main dashboard engine"""
    
    def __init__(self, storage_path: str):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.chart_generator = ChartGenerator()
        self.widget_manager = WidgetManager(self.chart_generator)
        self.real_time_updater = RealTimeUpdater(self.widget_manager)
        
        self.dashboards: Dict[str, DashboardConfig] = {}
        self.dashboard_templates: Dict[str, DashboardConfig] = {}
        
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> bool:
        """Initialize dashboard engine"""
        try:
            # Load existing dashboards
            await self._load_dashboards()
            
            # Create default dashboard templates
            await self._create_default_templates()
            
            self.logger.info("Dashboard engine initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard engine initialization failed: {e}")
            return False
    
    async def create_dashboard(self, dashboard_config: DashboardConfig) -> bool:
        """Create new dashboard"""
        try:
            # Validate dashboard configuration
            if not self._validate_dashboard_config(dashboard_config):
                return False
            
            # Register widgets
            for widget in dashboard_config.widgets:
                if not await self.widget_manager.register_widget(widget):
                    self.logger.warning(f"Failed to register widget: {widget.widget_id}")
            
            # Store dashboard
            self.dashboards[dashboard_config.dashboard_id] = dashboard_config
            
            # Save to persistent storage
            await self._save_dashboard(dashboard_config)
            
            # Start real-time updates if enabled
            if dashboard_config.auto_refresh:
                await self.real_time_updater.start_real_time_updates(dashboard_config)
            
            self.logger.info(f"Dashboard created: {dashboard_config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Dashboard creation failed: {e}")
            return False
    
    async def render_dashboard(self, 
                              dashboard_id: str, 
                              theme: str = 'light') -> Optional[str]:
        """Render complete dashboard to HTML"""
        try:
            if dashboard_id not in self.dashboards:
                return None
            
            dashboard_config = self.dashboards[dashboard_id]
            
            # Generate dashboard HTML
            dashboard_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{dashboard_config.name}</title>
                <style>
                    {await self._get_dashboard_css(theme)}
                </style>
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            </head>
            <body class="{theme}">
                <header class="dashboard-header">
                    <h1>{dashboard_config.name}</h1>
                    <p>{dashboard_config.description}</p>
                    <div class="dashboard-controls">
                        <button onclick="refreshDashboard()">🔄 Refresh</button>
                        <button onclick="toggleTheme()">🌙 Theme</button>
                    </div>
                </header>
                
                <main class="dashboard-content">
                    <div class="widget-grid" style="{await self._get_grid_style(dashboard_config)}">
            """
            
            # Render widgets
            for widget in dashboard_config.widgets:
                widget_html = await self.widget_manager.render_widget(widget.widget_id, theme)
                if widget_html:
                    dashboard_html += f"""
                    <div class="widget-container" style="{self._get_widget_style(widget)}">
                        {widget_html}
                    </div>
                    """
            
            dashboard_html += """
                    </div>
                </main>
                
                <script>
                    function refreshDashboard() {
                        location.reload();
                    }
                    
                    function toggleTheme() {
                        document.body.classList.toggle('dark');
                        document.body.classList.toggle('light');
                    }
                    
                    // Auto-refresh if enabled
                    if (true) {  // dashboard_config.auto_refresh
                        setInterval(refreshDashboard, 30000);  // 30 seconds
                    }
                </script>
            </body>
            </html>
            """
            
            return dashboard_html
            
        except Exception as e:
            self.logger.error(f"Dashboard rendering failed: {e}")
            return None
    
    async def _get_dashboard_css(self, theme: str) -> str:
        """Get dashboard CSS styles"""
        return f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: {'#f5f5f5' if theme == 'light' else '#1a1a1a'};
            color: {'#333' if theme == 'light' else '#fff'};
        }}
        
        .dashboard-header {{
            background: {'#fff' if theme == 'light' else '#2d2d2d'};
            padding: 20px;
            border-bottom: 1px solid {'#e0e0e0' if theme == 'light' else '#404040'};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .dashboard-header h1 {{
            font-size: 24px;
            margin-bottom: 8px;
        }}
        
        .dashboard-controls {{
            margin-top: 16px;
        }}
        
        .dashboard-controls button {{
            background: #007acc;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            margin-right: 8px;
            cursor: pointer;
        }}
        
        .dashboard-content {{
            padding: 20px;
        }}
        
        .widget-grid {{
            display: grid;
            gap: 20px;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        }}
        
        .widget-container {{
            background: {'#fff' if theme == 'light' else '#2d2d2d'};
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border: 1px solid {'#e0e0e0' if theme == 'light' else '#404040'};
        }}
        
        .metric-widget {{
            text-align: center;
            padding: 24px;
        }}
        
        .metric-value {{
            font-size: 48px;
            font-weight: bold;
            margin: 16px 0;
        }}
        
        .metric-change.positive {{
            color: #28a745;
        }}
        
        .metric-change.negative {{
            color: #dc3545;
        }}
        
        .table-widget .data-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        .table-widget th,
        .table-widget td {{
            padding: 8px 12px;
            border-bottom: 1px solid {'#e0e0e0' if theme == 'light' else '#404040'};
            text-align: left;
        }}
        
        .table-widget th {{
            font-weight: 600;
            background: {'#f8f9fa' if theme == 'light' else '#3d3d3d'};
        }}
        
        .error-widget {{
            background: #f8d7da;
            color: #721c24;
            padding: 16px;
            border-radius: 4px;
            border: 1px solid #f5c6cb;
        }}
        """
    
    def _get_widget_style(self, widget_config: WidgetConfig) -> str:
        """Get CSS style for widget positioning"""
        pos = widget_config.position
        return f"grid-column: span {pos.get('width', 1)}; grid-row: span {pos.get('height', 1)};"
    
    def _validate_dashboard_config(self, dashboard_config: DashboardConfig) -> bool:
        """Validate dashboard configuration"""
        if not dashboard_config.dashboard_id or not dashboard_config.name:
            return False
        
        if not dashboard_config.widgets:
            return False
        
        # Check for duplicate widget IDs
        widget_ids = [w.widget_id for w in dashboard_config.widgets]
        if len(widget_ids) != len(set(widget_ids)):
            return False
        
        return True