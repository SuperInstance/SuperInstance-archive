"""
Multi-layer Chart Overlay System
Professional nautical chart overlay management with layer prioritization
"""

import logging
import json
import numpy as np
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from datetime import datetime, timezone
import threading
import math
from collections import defaultdict
# import cv2
# from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import LineCollection, PatchCollection

logger = logging.getLogger(__name__)

class LayerType(Enum):
    CHART_BASE = "chart_base"
    DEPTH_CONTOURS = "depth_contours"
    NAVIGATION_AIDS = "navigation_aids"
    SAFETY_ZONES = "safety_zones"
    TRAFFIC_SEPARATION = "traffic_separation"
    ANCHORAGE_AREAS = "anchorage_areas"
    RESTRICTED_AREAS = "restricted_areas"
    WEATHER_OVERLAY = "weather_overlay"
    AIS_TARGETS = "ais_targets"
    RADAR_OVERLAY = "radar_overlay"
    ROUTE_PLAN = "route_plan"
    VESSEL_TRACK = "vessel_track"
    TIDE_CURRENT = "tide_current"
    FISHING_ZONES = "fishing_zones"
    MARINERS_OBJECTS = "mariners_objects"
    TEXT_LABELS = "text_labels"

class LayerPriority(IntEnum):
    BACKGROUND = 0
    CHART_BASE = 10
    BATHYMETRY = 20
    NAVIGATION_AIDS = 30
    SAFETY_FEATURES = 40
    TRAFFIC_FEATURES = 50
    ENVIRONMENTAL = 60
    VESSEL_TRACKS = 70
    AIS_RADAR = 80
    ROUTE_PLANNING = 90
    ALERTS_WARNINGS = 95
    TEXT_OVERLAYS = 100

@dataclass
class LayerStyle:
    color: str = "#000000"
    line_width: float = 1.0
    fill_color: Optional[str] = None
    opacity: float = 1.0
    dash_pattern: Optional[List[float]] = None
    marker_size: float = 5.0
    marker_style: str = "circle"
    font_size: int = 12
    font_family: str = "Arial"

@dataclass
class LayerObject:
    object_id: str
    geometry_type: str  # point, line, polygon, text
    coordinates: List[Tuple[float, float]]
    properties: Dict[str, Any] = field(default_factory=dict)
    style: Optional[LayerStyle] = None
    visible: bool = True
    interactive: bool = True
    z_order: int = 0

@dataclass
class ChartLayer:
    layer_id: str
    layer_type: LayerType
    name: str
    priority: LayerPriority
    visible: bool = True
    opacity: float = 1.0
    min_zoom: float = 0.0
    max_zoom: float = float('inf')
    objects: List[LayerObject] = field(default_factory=list)
    update_callback: Optional[Callable] = None
    last_update: Optional[datetime] = None

class ChartOverlaySystem:
    """
    Professional multi-layer chart overlay system
    Manages rendering order, visibility, and interaction of chart elements
    """
    
    def __init__(self):
        self.layers: Dict[str, ChartLayer] = {}
        self.layer_order: List[str] = []
        self.render_lock = threading.RLock()
        self.viewport = {"center_lat": 0.0, "center_lon": 0.0, "zoom": 1.0}
        self.display_bounds = {"width": 1920, "height": 1080}
        
        # Rendering settings
        self.anti_aliasing = True
        self.high_dpi = True
        self.render_quality = "high"
        
        # Performance settings
        self.max_objects_per_layer = 10000
        self.culling_enabled = True
        self.level_of_detail = True
        
        # ECDIS compliance settings
        self.ecdis_mode = True
        self.safety_highlighting = True
        self.standardized_symbols = True
        
        self._initialize_default_layers()
        logger.info("Chart Overlay System initialized")
    
    def _initialize_default_layers(self):
        """Initialize standard ECDIS layers"""
        default_layers = [
            ("chart_base", LayerType.CHART_BASE, LayerPriority.CHART_BASE, "Chart Base"),
            ("depth_contours", LayerType.DEPTH_CONTOURS, LayerPriority.BATHYMETRY, "Depth Contours"),
            ("navigation_aids", LayerType.NAVIGATION_AIDS, LayerPriority.NAVIGATION_AIDS, "Navigation Aids"),
            ("safety_zones", LayerType.SAFETY_ZONES, LayerPriority.SAFETY_FEATURES, "Safety Zones"),
            ("traffic_separation", LayerType.TRAFFIC_SEPARATION, LayerPriority.TRAFFIC_FEATURES, "Traffic Separation"),
            ("weather_overlay", LayerType.WEATHER_OVERLAY, LayerPriority.ENVIRONMENTAL, "Weather"),
            ("ais_targets", LayerType.AIS_TARGETS, LayerPriority.AIS_RADAR, "AIS Targets"),
            ("radar_overlay", LayerType.RADAR_OVERLAY, LayerPriority.AIS_RADAR, "Radar"),
            ("route_plan", LayerType.ROUTE_PLAN, LayerPriority.ROUTE_PLANNING, "Route Plan"),
            ("vessel_track", LayerType.VESSEL_TRACK, LayerPriority.VESSEL_TRACKS, "Vessel Track"),
            ("mariners_objects", LayerType.MARINERS_OBJECTS, LayerPriority.ROUTE_PLANNING, "Mariner's Objects"),
            ("text_labels", LayerType.TEXT_LABELS, LayerPriority.TEXT_OVERLAYS, "Labels")
        ]
        
        for layer_id, layer_type, priority, name in default_layers:
            self.add_layer(layer_id, layer_type, priority, name)
    
    def add_layer(self, layer_id: str, layer_type: LayerType, priority: LayerPriority, 
                  name: str, visible: bool = True) -> ChartLayer:
        """Add new chart layer"""
        with self.render_lock:
            layer = ChartLayer(
                layer_id=layer_id,
                layer_type=layer_type,
                name=name,
                priority=priority,
                visible=visible
            )
            
            self.layers[layer_id] = layer
            self._update_layer_order()
            
            logger.info(f"Layer added: {layer_id} ({name})")
            return layer
    
    def remove_layer(self, layer_id: str):
        """Remove chart layer"""
        with self.render_lock:
            if layer_id in self.layers:
                del self.layers[layer_id]
                self._update_layer_order()
                logger.info(f"Layer removed: {layer_id}")
    
    def _update_layer_order(self):
        """Update rendering order based on layer priorities"""
        self.layer_order = sorted(
            self.layers.keys(),
            key=lambda lid: self.layers[lid].priority
        )
    
    def add_object_to_layer(self, layer_id: str, obj: LayerObject):
        """Add object to specific layer"""
        if layer_id not in self.layers:
            raise ValueError(f"Layer not found: {layer_id}")
        
        layer = self.layers[layer_id]
        
        # Check object limit
        if len(layer.objects) >= self.max_objects_per_layer:
            logger.warning(f"Layer {layer_id} object limit exceeded")
            return False
        
        layer.objects.append(obj)
        layer.last_update = datetime.now(timezone.utc)
        
        return True
    
    def remove_object_from_layer(self, layer_id: str, object_id: str):
        """Remove object from layer"""
        if layer_id not in self.layers:
            return False
        
        layer = self.layers[layer_id]
        layer.objects = [obj for obj in layer.objects if obj.object_id != object_id]
        layer.last_update = datetime.now(timezone.utc)
        
        return True
    
    def update_object(self, layer_id: str, object_id: str, updates: Dict[str, Any]):
        """Update object properties"""
        if layer_id not in self.layers:
            return False
        
        layer = self.layers[layer_id]
        for obj in layer.objects:
            if obj.object_id == object_id:
                for key, value in updates.items():
                    if hasattr(obj, key):
                        setattr(obj, key, value)
                layer.last_update = datetime.now(timezone.utc)
                return True
        
        return False
    
    def set_layer_visibility(self, layer_id: str, visible: bool):
        """Toggle layer visibility"""
        if layer_id in self.layers:
            self.layers[layer_id].visible = visible
            logger.info(f"Layer {layer_id} visibility: {visible}")
    
    def set_layer_opacity(self, layer_id: str, opacity: float):
        """Set layer opacity (0.0 - 1.0)"""
        if layer_id in self.layers:
            self.layers[layer_id].opacity = max(0.0, min(1.0, opacity))
    
    def set_viewport(self, center_lat: float, center_lon: float, zoom: float):
        """Update viewport for rendering"""
        self.viewport = {
            "center_lat": center_lat,
            "center_lon": center_lon,
            "zoom": zoom
        }
    
    def get_visible_objects(self, layer_id: str = None) -> List[Tuple[str, LayerObject]]:
        """Get all visible objects in rendering order"""
        visible_objects = []
        
        layers_to_check = [layer_id] if layer_id else self.layer_order
        
        for lid in layers_to_check:
            if lid not in self.layers:
                continue
                
            layer = self.layers[lid]
            if not layer.visible:
                continue
            
            # Check zoom level constraints
            if (self.viewport["zoom"] < layer.min_zoom or 
                self.viewport["zoom"] > layer.max_zoom):
                continue
            
            for obj in layer.objects:
                if obj.visible and self._is_object_in_viewport(obj):
                    visible_objects.append((lid, obj))
        
        return visible_objects
    
    def _is_object_in_viewport(self, obj: LayerObject) -> bool:
        """Check if object is within current viewport"""
        if not self.culling_enabled:
            return True
        
        # Calculate viewport bounds
        viewport_bounds = self._calculate_viewport_bounds()
        
        # Check if object intersects viewport
        for lat, lon in obj.coordinates:
            if (viewport_bounds["south"] <= lat <= viewport_bounds["north"] and
                viewport_bounds["west"] <= lon <= viewport_bounds["east"]):
                return True
        
        return False
    
    def _calculate_viewport_bounds(self) -> Dict[str, float]:
        """Calculate geographic bounds of current viewport"""
        center_lat = self.viewport["center_lat"]
        center_lon = self.viewport["center_lon"]
        zoom = self.viewport["zoom"]
        
        # Calculate degrees per pixel at current zoom
        lat_range = 180.0 / (zoom * 100)  # Simplified calculation
        lon_range = 360.0 / (zoom * 100)
        
        return {
            "north": center_lat + lat_range/2,
            "south": center_lat - lat_range/2,
            "east": center_lon + lon_range/2,
            "west": center_lon - lon_range/2
        }
    
    def render_layers(self, output_format: str = "canvas") -> Any:
        """Render all visible layers to output format"""
        with self.render_lock:
            if output_format == "canvas":
                return self._render_to_canvas()
            elif output_format == "image":
                return self._render_to_image()
            elif output_format == "svg":
                return self._render_to_svg()
            else:
                raise ValueError(f"Unsupported output format: {output_format}")
    
    def _render_to_canvas(self) -> Dict[str, Any]:
        """Render to HTML5 canvas format"""
        canvas_commands = []
        
        visible_objects = self.get_visible_objects()
        
        for layer_id, obj in visible_objects:
            layer = self.layers[layer_id]
            
            # Apply layer opacity
            canvas_commands.append({
                "command": "globalAlpha",
                "value": layer.opacity * obj.style.opacity if obj.style else layer.opacity
            })
            
            # Render object based on geometry type
            if obj.geometry_type == "point":
                canvas_commands.extend(self._render_point_to_canvas(obj))
            elif obj.geometry_type == "line":
                canvas_commands.extend(self._render_line_to_canvas(obj))
            elif obj.geometry_type == "polygon":
                canvas_commands.extend(self._render_polygon_to_canvas(obj))
            elif obj.geometry_type == "text":
                canvas_commands.extend(self._render_text_to_canvas(obj))
        
        return {
            "type": "canvas",
            "commands": canvas_commands,
            "viewport": self.viewport,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def _render_point_to_canvas(self, obj: LayerObject) -> List[Dict[str, Any]]:
        """Render point object to canvas commands"""
        if not obj.coordinates:
            return []
        
        lat, lon = obj.coordinates[0]
        x, y = self._geo_to_screen(lat, lon)
        
        style = obj.style or LayerStyle()
        
        commands = [
            {"command": "fillStyle", "value": style.fill_color or style.color},
            {"command": "strokeStyle", "value": style.color},
            {"command": "lineWidth", "value": style.line_width},
            {"command": "beginPath"},
            {"command": "arc", "x": x, "y": y, "radius": style.marker_size, 
             "startAngle": 0, "endAngle": 2 * math.pi},
            {"command": "fill"},
            {"command": "stroke"}
        ]
        
        return commands
    
    def _render_line_to_canvas(self, obj: LayerObject) -> List[Dict[str, Any]]:
        """Render line object to canvas commands"""
        if len(obj.coordinates) < 2:
            return []
        
        style = obj.style or LayerStyle()
        
        commands = [
            {"command": "strokeStyle", "value": style.color},
            {"command": "lineWidth", "value": style.line_width},
            {"command": "beginPath"}
        ]
        
        # Set dash pattern if specified
        if style.dash_pattern:
            commands.append({
                "command": "setLineDash", 
                "value": style.dash_pattern
            })
        
        # Move to first point
        lat, lon = obj.coordinates[0]
        x, y = self._geo_to_screen(lat, lon)
        commands.append({"command": "moveTo", "x": x, "y": y})
        
        # Draw line segments
        for lat, lon in obj.coordinates[1:]:
            x, y = self._geo_to_screen(lat, lon)
            commands.append({"command": "lineTo", "x": x, "y": y})
        
        commands.append({"command": "stroke"})
        
        return commands
    
    def _render_polygon_to_canvas(self, obj: LayerObject) -> List[Dict[str, Any]]:
        """Render polygon object to canvas commands"""
        if len(obj.coordinates) < 3:
            return []
        
        style = obj.style or LayerStyle()
        
        commands = [
            {"command": "fillStyle", "value": style.fill_color or style.color},
            {"command": "strokeStyle", "value": style.color},
            {"command": "lineWidth", "value": style.line_width},
            {"command": "beginPath"}
        ]
        
        # Move to first point
        lat, lon = obj.coordinates[0]
        x, y = self._geo_to_screen(lat, lon)
        commands.append({"command": "moveTo", "x": x, "y": y})
        
        # Draw polygon edges
        for lat, lon in obj.coordinates[1:]:
            x, y = self._geo_to_screen(lat, lon)
            commands.append({"command": "lineTo", "x": x, "y": y})
        
        commands.append({"command": "closePath"})
        
        if style.fill_color:
            commands.append({"command": "fill"})
        
        commands.append({"command": "stroke"})
        
        return commands
    
    def _render_text_to_canvas(self, obj: LayerObject) -> List[Dict[str, Any]]:
        """Render text object to canvas commands"""
        if not obj.coordinates:
            return []
        
        lat, lon = obj.coordinates[0]
        x, y = self._geo_to_screen(lat, lon)
        
        style = obj.style or LayerStyle()
        text = obj.properties.get('text', '')
        
        commands = [
            {"command": "font", "value": f"{style.font_size}px {style.font_family}"},
            {"command": "fillStyle", "value": style.color},
            {"command": "fillText", "text": text, "x": x, "y": y}
        ]
        
        return commands
    
    def _geo_to_screen(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert geographic coordinates to screen coordinates"""
        # Simplified Mercator projection
        center_lat = self.viewport["center_lat"]
        center_lon = self.viewport["center_lon"]
        zoom = self.viewport["zoom"]
        
        # Calculate offset from viewport center
        lat_offset = lat - center_lat
        lon_offset = lon - center_lon
        
        # Convert to screen coordinates
        x = self.display_bounds["width"] / 2 + (lon_offset * zoom * 100)
        y = self.display_bounds["height"] / 2 - (lat_offset * zoom * 100)
        
        return x, y
    
    def add_depth_contours(self, contour_data: List[Dict[str, Any]]):
        """Add depth contour lines to chart"""
        layer_id = "depth_contours"
        
        for i, contour in enumerate(contour_data):
            depth = contour.get('depth', 0)
            coordinates = contour.get('coordinates', [])
            
            # Determine contour style based on depth
            if depth <= 2:  # Shallow water
                color = "#8B4513"  # Brown
                line_width = 2.0
            elif depth <= 10:  # Safety contour
                color = "#FF0000"  # Red
                line_width = 3.0
            elif depth <= 30:  # Intermediate depth
                color = "#0000FF"  # Blue
                line_width = 1.5
            else:  # Deep water
                color = "#000080"  # Navy
                line_width = 1.0
            
            style = LayerStyle(
                color=color,
                line_width=line_width
            )
            
            obj = LayerObject(
                object_id=f"depth_contour_{i}_{depth}m",
                geometry_type="line",
                coordinates=coordinates,
                properties={"depth": depth, "type": "depth_contour"},
                style=style
            )
            
            self.add_object_to_layer(layer_id, obj)
    
    def add_navigation_aid(self, aid_type: str, lat: float, lon: float, properties: Dict[str, Any]):
        """Add navigation aid to chart"""
        layer_id = "navigation_aids"
        
        # Standardized navigation aid symbols
        aid_styles = {
            "lighthouse": LayerStyle(color="#FFFF00", marker_size=8, marker_style="star"),
            "buoy_lateral_port": LayerStyle(color="#FF0000", marker_size=6, marker_style="circle"),
            "buoy_lateral_starboard": LayerStyle(color="#00FF00", marker_size=6, marker_style="circle"),
            "buoy_cardinal_north": LayerStyle(color="#000000", marker_size=6, marker_style="triangle"),
            "beacon": LayerStyle(color="#FFFF00", marker_size=7, marker_style="square"),
            "wreck": LayerStyle(color="#800080", marker_size=8, marker_style="cross")
        }
        
        style = aid_styles.get(aid_type, LayerStyle(color="#FFFFFF", marker_size=5))
        
        obj = LayerObject(
            object_id=f"navaid_{aid_type}_{lat}_{lon}",
            geometry_type="point",
            coordinates=[(lat, lon)],
            properties={**properties, "aid_type": aid_type},
            style=style
        )
        
        self.add_object_to_layer(layer_id, obj)
    
    def add_safety_zone(self, zone_type: str, coordinates: List[Tuple[float, float]], 
                       properties: Dict[str, Any]):
        """Add safety zone to chart"""
        layer_id = "safety_zones"
        
        # Safety zone styling
        zone_styles = {
            "restricted": LayerStyle(color="#FF0000", fill_color="#FF000033", line_width=2),
            "anchorage": LayerStyle(color="#0000FF", fill_color="#0000FF33", line_width=1.5),
            "no_fishing": LayerStyle(color="#800080", fill_color="#80008033", line_width=2),
            "military": LayerStyle(color="#FF6600", fill_color="#FF660033", line_width=3)
        }
        
        style = zone_styles.get(zone_type, LayerStyle(color="#808080", fill_color="#80808033"))
        
        obj = LayerObject(
            object_id=f"safety_zone_{zone_type}_{len(coordinates)}",
            geometry_type="polygon",
            coordinates=coordinates,
            properties={**properties, "zone_type": zone_type},
            style=style
        )
        
        self.add_object_to_layer(layer_id, obj)
    
    def get_layer_statistics(self) -> Dict[str, Any]:
        """Get overlay system statistics"""
        stats = {
            "total_layers": len(self.layers),
            "visible_layers": sum(1 for layer in self.layers.values() if layer.visible),
            "total_objects": sum(len(layer.objects) for layer in self.layers.values()),
            "objects_per_layer": {
                lid: len(layer.objects) for lid, layer in self.layers.items()
            },
            "layer_priorities": {
                lid: layer.priority for lid, layer in self.layers.items()
            }
        }
        
        return stats