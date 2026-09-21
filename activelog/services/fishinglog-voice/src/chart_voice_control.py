"""
Chart Voice Control System
Natural language control for chart display and navigation
"""

import logging
import requests
from typing import Dict, Any, Optional
import json

logger = logging.getLogger(__name__)

class ChartVoiceController:
    """
    Voice control interface for chart display and navigation functions
    """
    
    def __init__(self):
        self.nav_system_url = "http://localhost:8365"
        self.current_zoom = 1.0
        self.current_center = {"lat": 0.0, "lon": 0.0}
        
        # Chart layer mappings
        self.layer_mappings = {
            'ais': 'ais_targets',
            'radar': 'radar_overlay', 
            'weather': 'weather_overlay',
            'depth': 'depth_contours',
            'navigation aids': 'navigation_aids',
            'traffic': 'traffic_separation',
            'safety zones': 'safety_zones',
            'routes': 'route_plan',
            'tracks': 'vessel_track',
            'tide': 'tide_current',
            'fishing': 'fishing_zones'
        }
        
        # Zoom level mappings
        self.zoom_levels = {
            'close': 5.0,
            'medium': 2.0,
            'far': 0.5,
            'harbor': 10.0,
            'coastal': 1.0,
            'ocean': 0.1
        }
        
        logger.info("Chart Voice Controller initialized")
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chart control voice command"""
        try:
            action = command.get('action')
            params = command.get('params', {})
            
            if action == 'zoom_in':
                return self._zoom_in(params)
            elif action == 'zoom_out':
                return self._zoom_out(params)
            elif action == 'pan':
                return self._pan_chart(params)
            elif action == 'show_layer':
                return self._show_layer(params)
            elif action == 'hide_layer':
                return self._hide_layer(params)
            elif action == 'center_on':
                return self._center_on(params)
            elif action == 'set_zoom':
                return self._set_zoom_level(params)
            else:
                return {"status": "error", "message": f"Unknown chart action: {action}"}
                
        except Exception as e:
            logger.error(f"Chart command execution error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _zoom_in(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Zoom in on chart"""
        try:
            zoom_level = params.get('level')
            
            if zoom_level:
                new_zoom = float(zoom_level)
            else:
                # Default zoom in by factor of 2
                new_zoom = min(self.current_zoom * 2.0, 50.0)
            
            # Send zoom command to navigation system
            response = self._send_chart_command('zoom', {'level': new_zoom})
            
            if response and response.get('status') == 'success':
                self.current_zoom = new_zoom
                return {
                    "status": "success",
                    "message": f"Zoomed in to level {new_zoom:.1f}",
                    "zoom_level": new_zoom
                }
            else:
                return {"status": "error", "message": "Failed to zoom in"}
                
        except Exception as e:
            logger.error(f"Zoom in error: {e}")
            return {"status": "error", "message": "Zoom in failed"}
    
    def _zoom_out(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Zoom out on chart"""
        try:
            zoom_level = params.get('level')
            
            if zoom_level:
                new_zoom = float(zoom_level)
            else:
                # Default zoom out by factor of 0.5
                new_zoom = max(self.current_zoom * 0.5, 0.1)
            
            # Send zoom command to navigation system
            response = self._send_chart_command('zoom', {'level': new_zoom})
            
            if response and response.get('status') == 'success':
                self.current_zoom = new_zoom
                return {
                    "status": "success",
                    "message": f"Zoomed out to level {new_zoom:.1f}",
                    "zoom_level": new_zoom
                }
            else:
                return {"status": "error", "message": "Failed to zoom out"}
                
        except Exception as e:
            logger.error(f"Zoom out error: {e}")
            return {"status": "error", "message": "Zoom out failed"}
    
    def _pan_chart(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Pan chart in specified direction"""
        try:
            direction = params.get('direction', '').lower()
            
            # Calculate pan offset based on current zoom
            pan_distance = 0.01 / self.current_zoom  # Smaller pan at higher zoom
            
            lat_offset = 0.0
            lon_offset = 0.0
            
            if direction in ['north', 'up']:
                lat_offset = pan_distance
            elif direction in ['south', 'down']:
                lat_offset = -pan_distance
            elif direction in ['east', 'right']:
                lon_offset = pan_distance
            elif direction in ['west', 'left']:
                lon_offset = -pan_distance
            else:
                return {"status": "error", "message": f"Invalid pan direction: {direction}"}
            
            # Calculate new center position
            new_lat = self.current_center['lat'] + lat_offset
            new_lon = self.current_center['lon'] + lon_offset
            
            # Send pan command to navigation system
            response = self._send_chart_command('pan', {
                'lat': new_lat,
                'lon': new_lon
            })
            
            if response and response.get('status') == 'success':
                self.current_center = {'lat': new_lat, 'lon': new_lon}
                return {
                    "status": "success", 
                    "message": f"Panned chart {direction}",
                    "center": self.current_center
                }
            else:
                return {"status": "error", "message": "Failed to pan chart"}
                
        except Exception as e:
            logger.error(f"Pan chart error: {e}")
            return {"status": "error", "message": "Pan chart failed"}
    
    def _show_layer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Show specified chart layer"""
        try:
            layer_name = params.get('layer', '').lower()
            
            # Map voice layer name to system layer name
            system_layer = self._map_layer_name(layer_name)
            
            if not system_layer:
                return {"status": "error", "message": f"Unknown layer: {layer_name}"}
            
            # Send show layer command
            response = self._send_chart_command('show_layer', {'layer': system_layer})
            
            if response and response.get('status') == 'success':
                return {
                    "status": "success",
                    "message": f"Showing {layer_name} layer",
                    "layer": system_layer
                }
            else:
                return {"status": "error", "message": f"Failed to show {layer_name} layer"}
                
        except Exception as e:
            logger.error(f"Show layer error: {e}")
            return {"status": "error", "message": "Show layer failed"}
    
    def _hide_layer(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Hide specified chart layer"""
        try:
            layer_name = params.get('layer', '').lower()
            
            # Map voice layer name to system layer name
            system_layer = self._map_layer_name(layer_name)
            
            if not system_layer:
                return {"status": "error", "message": f"Unknown layer: {layer_name}"}
            
            # Send hide layer command
            response = self._send_chart_command('hide_layer', {'layer': system_layer})
            
            if response and response.get('status') == 'success':
                return {
                    "status": "success",
                    "message": f"Hiding {layer_name} layer",
                    "layer": system_layer
                }
            else:
                return {"status": "error", "message": f"Failed to hide {layer_name} layer"}
                
        except Exception as e:
            logger.error(f"Hide layer error: {e}")
            return {"status": "error", "message": "Hide layer failed"}
    
    def _center_on(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Center chart on specified location"""
        try:
            location = params.get('location', '')
            
            # Try to parse coordinates or location name
            coordinates = self._parse_location(location)
            
            if not coordinates:
                return {"status": "error", "message": f"Could not find location: {location}"}
            
            # Send center command
            response = self._send_chart_command('center', {
                'lat': coordinates['lat'],
                'lon': coordinates['lon']
            })
            
            if response and response.get('status') == 'success':
                self.current_center = coordinates
                return {
                    "status": "success",
                    "message": f"Centered chart on {location}",
                    "center": coordinates
                }
            else:
                return {"status": "error", "message": f"Failed to center on {location}"}
                
        except Exception as e:
            logger.error(f"Center on error: {e}")
            return {"status": "error", "message": "Center on failed"}
    
    def _set_zoom_level(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set specific zoom level"""
        try:
            level_name = params.get('level', '').lower()
            
            # Map named zoom level to numeric value
            if level_name in self.zoom_levels:
                zoom_level = self.zoom_levels[level_name]
            else:
                # Try to parse as numeric
                try:
                    zoom_level = float(level_name)
                except ValueError:
                    return {"status": "error", "message": f"Invalid zoom level: {level_name}"}
            
            # Send zoom command
            response = self._send_chart_command('zoom', {'level': zoom_level})
            
            if response and response.get('status') == 'success':
                self.current_zoom = zoom_level
                return {
                    "status": "success",
                    "message": f"Set zoom to {level_name} ({zoom_level:.1f})",
                    "zoom_level": zoom_level
                }
            else:
                return {"status": "error", "message": f"Failed to set zoom level"}
                
        except Exception as e:
            logger.error(f"Set zoom level error: {e}")
            return {"status": "error", "message": "Set zoom level failed"}
    
    def _map_layer_name(self, voice_name: str) -> Optional[str]:
        """Map voice layer name to system layer name"""
        # Direct mapping
        if voice_name in self.layer_mappings:
            return self.layer_mappings[voice_name]
        
        # Fuzzy matching for common variations
        voice_name = voice_name.replace(' ', '_').replace('-', '_')
        
        for voice_layer, system_layer in self.layer_mappings.items():
            if voice_name in voice_layer or voice_layer in voice_name:
                return system_layer
        
        # Common aliases
        aliases = {
            'targets': 'ais_targets',
            'ships': 'ais_targets',
            'vessels': 'ais_targets',
            'weather': 'weather_overlay',
            'wind': 'weather_overlay',
            'depths': 'depth_contours',
            'soundings': 'depth_contours',
            'buoys': 'navigation_aids',
            'lights': 'navigation_aids',
            'beacons': 'navigation_aids'
        }
        
        if voice_name in aliases:
            return aliases[voice_name]
        
        return None
    
    def _parse_location(self, location_text: str) -> Optional[Dict[str, float]]:
        """Parse location from text"""
        # Try to parse coordinates (lat, lon format)
        import re
        
        # Pattern for decimal degrees: "12.34, -56.78" or "12.34 N, 56.78 W"
        coord_pattern = r'([+-]?\d+\.?\d*)\s*[,\s]\s*([+-]?\d+\.?\d*)'
        match = re.search(coord_pattern, location_text)
        
        if match:
            try:
                lat = float(match.group(1))
                lon = float(match.group(2))
                
                # Basic validation
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return {'lat': lat, 'lon': lon}
            except ValueError:
                pass
        
        # Try to geocode location name (placeholder)
        # In production, this would use a geocoding service
        known_locations = {
            'home': {'lat': 40.7128, 'lon': -74.0060},  # New York
            'port': {'lat': 40.7128, 'lon': -74.0060},
            'harbor': {'lat': 40.7128, 'lon': -74.0060},
            'current position': None  # Would get from GPS
        }
        
        location_lower = location_text.lower()
        if location_lower in known_locations:
            return known_locations[location_lower]
        
        return None
    
    def _send_chart_command(self, command: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send command to navigation system"""
        try:
            url = f"{self.nav_system_url}/api/chart/{command}"
            
            response = requests.post(url, json=params, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Chart command failed: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Chart command request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Chart command error: {e}")
            return None
    
    def get_current_view(self) -> Dict[str, Any]:
        """Get current chart view settings"""
        return {
            'zoom_level': self.current_zoom,
            'center': self.current_center,
            'available_layers': list(self.layer_mappings.keys()),
            'zoom_presets': list(self.zoom_levels.keys())
        }
    
    def get_voice_commands_help(self) -> str:
        """Get help text for chart voice commands"""
        return """
Chart Voice Commands:

Zoom Control:
- "Zoom in" / "Zoom out" 
- "Zoom to [level]" (1-50)
- "Close view" / "Far view" / "Harbor view"

Pan Control:
- "Pan north" / "Pan south" / "Pan east" / "Pan west"
- "Move up" / "Move down" / "Move left" / "Move right"

Layer Control:
- "Show [layer]" / "Hide [layer]"
- Available layers: AIS, radar, weather, depth, navigation aids, 
  traffic, safety zones, routes, tracks, tide, fishing

Location Control:  
- "Center on [coordinates]"
- "Go to [location]"
- "Navigate to [waypoint]"

Examples:
- "Zoom in to harbor view"
- "Show AIS targets"
- "Pan north"
- "Center on 40.7, -74.0"
        """.strip()