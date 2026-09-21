"""
Marine Natural Language Command System
Advanced natural language processing for marine and fishing applications
"""

import asyncio
import json
import uuid
import re
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
import logging

from .voice_control import VoiceCommand, VoiceCommandType, VoiceControlManager

logger = logging.getLogger(__name__)

class MarineCommandCategory(Enum):
    NAVIGATION = "navigation"
    CHART_CONTROL = "chart_control"
    TRACKING = "tracking"
    WEATHER = "weather"
    FISH_FINDER = "fish_finder"
    AIS_RADAR = "ais_radar"
    WAYPOINTS = "waypoints"
    ALERTS = "alerts"
    DISPLAY = "display"
    CALCULATIONS = "calculations"
    RECORDING = "recording"

class DistanceUnit(Enum):
    METERS = "meters"
    FEET = "feet"
    YARDS = "yards"
    NAUTICAL_MILES = "nautical_miles"
    KILOMETERS = "kilometers"

class TimeUnit(Enum):
    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"

@dataclass
class MarineParameter:
    name: str
    value: Any
    unit: Optional[str] = None
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ParsedMarineCommand:
    command_type: MarineCommandCategory
    action: str
    parameters: List[MarineParameter]
    target: Optional[str] = None
    location: Optional[Dict[str, float]] = None  # lat, lon
    confidence: float = 1.0
    raw_text: str = ""
    
    def get_parameter(self, name: str) -> Optional[MarineParameter]:
        """Get parameter by name"""
        for param in self.parameters:
            if param.name == name:
                return param
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['command_type'] = self.command_type.value
        result['parameters'] = [p.to_dict() for p in self.parameters]
        return result

class MarineNLUProcessor:
    """Natural Language Understanding processor for marine commands"""
    
    def __init__(self):
        # Distance patterns with units
        self.distance_patterns = {
            r'\b(\d+(?:\.\d+)?)\s*(?:nautical\s+)?mile[s]?\b': ('nautical_miles', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:nm|NM)\b': ('nautical_miles', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*meter[s]?\b': ('meters', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:m)\b': ('meters', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:feet|ft)\b': ('feet', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:yard[s]?|yd[s]?)\b': ('yards', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:kilometer[s]?|km)\b': ('kilometers', 1.0),
        }
        
        # Time patterns
        self.time_patterns = {
            r'\b(\d+(?:\.\d+)?)\s*(?:minute[s]?|min[s]?)\b': ('minutes', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:hour[s]?|hr[s]?)\b': ('hours', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:day[s]?)\b': ('days', 1.0),
        }
        
        # Speed patterns
        self.speed_patterns = {
            r'\b(\d+(?:\.\d+)?)\s*(?:knot[s]?|kt[s]?|kn)\b': ('knots', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:mph)\b': ('mph', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:km/h|kmh)\b': ('kmh', 1.0),
        }
        
        # Depth patterns
        self.depth_patterns = {
            r'\b(\d+(?:\.\d+)?)\s*(?:feet|ft)\s*(?:deep|depth)?\b': ('feet', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:meter[s]?|m)\s*(?:deep|depth)?\b': ('meters', 1.0),
            r'\b(\d+(?:\.\d+)?)\s*(?:fathom[s]?)\b': ('fathoms', 1.0),
        }
        
        # Direction patterns
        self.direction_patterns = {
            r'\b(north|N)\b': 0,
            r'\b(northeast|NE)\b': 45,
            r'\b(east|E)\b': 90,
            r'\b(southeast|SE)\b': 135,
            r'\b(south|S)\b': 180,
            r'\b(southwest|SW)\b': 225,
            r'\b(west|W)\b': 270,
            r'\b(northwest|NW)\b': 315,
            r'\b(\d+)\s*degrees?\b': None,  # Will use captured number
        }
        
        # Coordinate patterns
        self.coordinate_patterns = [
            r'(\d{1,2})[°\s]+(\d{1,2})[\'′\s]*(\d{1,2}(?:\.\d+)?)[\"″\s]*([NS])\s*,?\s*(\d{1,3})[°\s]+(\d{1,2})[\'′\s]*(\d{1,2}(?:\.\d+)?)[\"″\s]*([EW])',
            r'(\d{1,2}\.\d+)[°\s]*([NS])\s*,?\s*(\d{1,3}\.\d+)[°\s]*([EW])',
            r'(-?\d{1,2}\.\d+)\s*,\s*(-?\d{1,3}\.\d+)',
        ]
    
    def parse_command(self, text: str) -> Optional[ParsedMarineCommand]:
        """Parse natural language marine command"""
        text = text.lower().strip()
        
        # Try to match against known command patterns
        for category, patterns in self._get_command_patterns().items():
            for pattern, action in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    # Extract parameters from the matched text
                    parameters = self._extract_parameters(text, match)
                    
                    # Extract target if present
                    target = self._extract_target(text, match)
                    
                    # Extract location if present
                    location = self._extract_location(text)
                    
                    return ParsedMarineCommand(
                        command_type=category,
                        action=action,
                        parameters=parameters,
                        target=target,
                        location=location,
                        confidence=0.8,
                        raw_text=text
                    )
        
        return None
    
    def _get_command_patterns(self) -> Dict[MarineCommandCategory, List[Tuple[str, str]]]:
        """Get command patterns organized by category"""
        return {
            MarineCommandCategory.CHART_CONTROL: [
                (r'center.*chart.*(?:on\s+)?(?:my\s+)?vessel', 'center_chart_on_vessel'),
                (r'zoom.*to.*(\d+).*(?:minute|min).*(?:range|ahead)', 'zoom_to_time_range'),
                (r'zoom.*in', 'zoom_in'),
                (r'zoom.*out', 'zoom_out'),
                (r'zoom.*to.*(\d+(?:\.\d+)?).*(?:mile[s]?|nm|NM)', 'zoom_to_distance'),
                (r'pan.*(?:to|toward[s]?)\s*(.*)', 'pan_to_location'),
            ],
            
            MarineCommandCategory.TRACKING: [
                (r'follow.*(?:that\s+)?(?:boat|vessel|ship).*maintain.*(\d+(?:\.\d+)?)', 'follow_vessel_with_distance'),
                (r'follow.*(?:that\s+)?(?:boat|vessel|ship)', 'follow_vessel'),
                (r'stop.*follow', 'stop_following'),
                (r'track.*(?:that\s+)?(?:vessel|boat|ship)', 'start_tracking_vessel'),
            ],
            
            MarineCommandCategory.WAYPOINTS: [
                (r'mark.*(?:this\s+)?spot.*as.*[\'"]([^\'\"]+)[\'"]', 'mark_spot_with_name'),
                (r'mark.*(?:this\s+)?(?:spot|location|position)', 'mark_current_position'),
                (r'delete.*waypoint.*[\'"]([^\'\"]+)[\'"]', 'delete_waypoint_by_name'),
                (r'navigate.*to.*[\'"]([^\'\"]+)[\'"]', 'navigate_to_waypoint'),
                (r'navigate.*to.*nearest.*harbor', 'navigate_to_nearest_harbor'),
                (r'navigate.*to.*nearest.*marina', 'navigate_to_nearest_marina'),
                (r'navigate.*to.*nearest.*port', 'navigate_to_nearest_port'),
            ],
            
            MarineCommandCategory.WEATHER: [
                (r'show.*weather.*(?:for\s+)?(?:next\s+)?(\d+)\s*hour[s]?', 'show_weather_forecast_hours'),
                (r'show.*weather.*(?:for\s+)?(?:next\s+)?(\d+)\s*day[s]?', 'show_weather_forecast_days'),
                (r'show.*(?:current\s+)?weather', 'show_current_weather'),
                (r'weather.*forecast', 'show_weather_forecast'),
                (r'wind.*speed', 'show_wind_speed'),
                (r'wave.*(?:height|conditions)', 'show_wave_conditions'),
            ],
            
            MarineCommandCategory.ALERTS: [
                (r'alert.*(?:if|when).*depth.*(?:less\s+than|under|below)\s*(\d+(?:\.\d+)?)', 'set_depth_alert_under'),
                (r'alert.*(?:if|when).*depth.*(?:greater\s+than|over|above)\s*(\d+(?:\.\d+)?)', 'set_depth_alert_over'),
                (r'alert.*(?:if|when).*(?:boat|vessel|ship).*(?:within|closer\s+than)\s*(\d+(?:\.\d+)?)', 'set_proximity_alert'),
                (r'alert.*(?:if|when).*anchor.*drag', 'set_anchor_drag_alert'),
                (r'cancel.*(?:all\s+)?alert[s]?', 'cancel_alerts'),
            ],
            
            MarineCommandCategory.RECORDING: [
                (r'start.*record.*(?:our\s+)?track', 'start_track_recording'),
                (r'stop.*record.*track', 'stop_track_recording'),
                (r'save.*track.*as.*[\'"]([^\'\"]+)[\'"]', 'save_track_with_name'),
                (r'start.*log', 'start_logging'),
                (r'stop.*log', 'stop_logging'),
            ],
            
            MarineCommandCategory.AIS_RADAR: [
                (r'show.*AIS.*(?:targets|vessels).*within.*(\d+(?:\.\d+)?)', 'show_ais_targets_within_range'),
                (r'show.*(?:all\s+)?AIS.*(?:targets|vessels)', 'show_all_ais_targets'),
                (r'hide.*AIS.*(?:targets|vessels)', 'hide_ais_targets'),
                (r'filter.*AIS.*by.*size', 'filter_ais_by_size'),
                (r'identify.*(?:that\s+)?(?:vessel|boat|ship)', 'identify_vessel'),
            ],
            
            MarineCommandCategory.DISPLAY: [
                (r'switch.*to.*night.*mode', 'switch_to_night_mode'),
                (r'switch.*to.*day.*mode', 'switch_to_day_mode'),
                (r'display.*fish.*finder.*on.*screen.*(\d+)', 'display_fish_finder_on_screen'),
                (r'show.*fish.*finder', 'show_fish_finder'),
                (r'hide.*fish.*finder', 'hide_fish_finder'),
                (r'full.*screen', 'enter_fullscreen'),
                (r'split.*screen', 'split_screen_mode'),
            ],
            
            MarineCommandCategory.CALCULATIONS: [
                (r'calculate.*ETA.*(?:at\s+)?(?:current\s+)?speed', 'calculate_eta_current_speed'),
                (r'calculate.*ETA.*to.*[\'"]([^\'\"]+)[\'"]', 'calculate_eta_to_waypoint'),
                (r'calculate.*distance.*to.*[\'"]([^\'\"]+)[\'"]', 'calculate_distance_to_waypoint'),
                (r'calculate.*bearing.*to.*[\'"]([^\'\"]+)[\'"]', 'calculate_bearing_to_waypoint'),
                (r'calculate.*fuel.*consumption', 'calculate_fuel_consumption'),
                (r'how.*far.*to.*[\'"]([^\'\"]+)[\'"]', 'calculate_distance_to_waypoint'),
            ],
            
            MarineCommandCategory.FISH_FINDER: [
                (r'show.*fish.*(?:finder|sonar)', 'show_fish_finder'),
                (r'adjust.*fish.*finder.*(?:gain|sensitivity)', 'adjust_fish_finder_gain'),
                (r'change.*fish.*finder.*frequency', 'change_fish_finder_frequency'),
                (r'mark.*fish.*on.*sonar', 'mark_fish_on_sonar'),
                (r'bottom.*lock.*on', 'enable_bottom_lock'),
                (r'bottom.*lock.*off', 'disable_bottom_lock'),
            ],
        }
    
    def _extract_parameters(self, text: str, match: re.Match) -> List[MarineParameter]:
        """Extract parameters from matched text"""
        parameters = []
        
        # Extract distances
        for pattern, (unit, confidence) in self.distance_patterns.items():
            for distance_match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(distance_match.group(1))
                parameters.append(MarineParameter("distance", value, unit, confidence))
        
        # Extract times
        for pattern, (unit, confidence) in self.time_patterns.items():
            for time_match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(time_match.group(1))
                parameters.append(MarineParameter("time", value, unit, confidence))
        
        # Extract speeds
        for pattern, (unit, confidence) in self.speed_patterns.items():
            for speed_match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(speed_match.group(1))
                parameters.append(MarineParameter("speed", value, unit, confidence))
        
        # Extract depths
        for pattern, (unit, confidence) in self.depth_patterns.items():
            for depth_match in re.finditer(pattern, text, re.IGNORECASE):
                value = float(depth_match.group(1))
                parameters.append(MarineParameter("depth", value, unit, confidence))
        
        # Extract directions
        for pattern, bearing in self.direction_patterns.items():
            direction_match = re.search(pattern, text, re.IGNORECASE)
            if direction_match:
                if bearing is None:  # Pattern captures number
                    bearing = float(direction_match.group(1))
                parameters.append(MarineParameter("bearing", bearing, "degrees", 0.9))
        
        # Extract screen numbers
        screen_match = re.search(r'screen\s*(\d+)', text, re.IGNORECASE)
        if screen_match:
            screen_num = int(screen_match.group(1))
            parameters.append(MarineParameter("screen_number", screen_num, None, 1.0))
        
        # Extract quoted names/labels
        name_matches = re.findall(r'[\'"]([^\'\"]+)[\'"]', text)
        if name_matches:
            parameters.append(MarineParameter("name", name_matches[0], None, 1.0))
        
        return parameters
    
    def _extract_target(self, text: str, match: re.Match) -> Optional[str]:
        """Extract target object from text"""
        target_patterns = [
            r'(?:that\s+)?(boat|vessel|ship)',
            r'(?:the\s+)?(harbor|marina|port)',
            r'(?:my\s+)?(vessel|boat)',
            r'(?:the\s+)?(chart|display|screen)',
        ]
        
        for pattern in target_patterns:
            target_match = re.search(pattern, text, re.IGNORECASE)
            if target_match:
                return target_match.group(1).lower()
        
        return None
    
    def _extract_location(self, text: str) -> Optional[Dict[str, float]]:
        """Extract coordinates from text"""
        for pattern in self.coordinate_patterns:
            coord_match = re.search(pattern, text, re.IGNORECASE)
            if coord_match:
                groups = coord_match.groups()
                
                if len(groups) == 8:  # DMS format
                    lat_deg, lat_min, lat_sec, lat_hem, lon_deg, lon_min, lon_sec, lon_hem = groups
                    lat = self._dms_to_decimal(float(lat_deg), float(lat_min), float(lat_sec), lat_hem)
                    lon = self._dms_to_decimal(float(lon_deg), float(lon_min), float(lon_sec), lon_hem)
                elif len(groups) == 4:  # Decimal degrees with hemisphere
                    lat_val, lat_hem, lon_val, lon_hem = groups
                    lat = float(lat_val) * (1 if lat_hem.upper() == 'N' else -1)
                    lon = float(lon_val) * (1 if lon_hem.upper() == 'E' else -1)
                elif len(groups) == 2:  # Signed decimal degrees
                    lat, lon = float(groups[0]), float(groups[1])
                else:
                    continue
                
                return {"latitude": lat, "longitude": lon}
        
        return None
    
    def _dms_to_decimal(self, degrees: float, minutes: float, seconds: float, hemisphere: str) -> float:
        """Convert degrees/minutes/seconds to decimal degrees"""
        decimal = degrees + minutes/60 + seconds/3600
        if hemisphere.upper() in ['S', 'W']:
            decimal = -decimal
        return decimal

class MarineVoiceCommands:
    """Marine-specific voice command extensions"""
    
    def __init__(self, voice_manager: VoiceControlManager):
        self.voice_manager = voice_manager
        self.nlu_processor = MarineNLUProcessor()
        
        # Register marine command handlers
        self._register_marine_handlers()
        
        # Create marine-specific voice commands
        self._create_marine_commands()
    
    def _register_marine_handlers(self):
        """Register handlers for marine commands"""
        handlers = {
            # Chart control
            'center_chart_on_vessel': self._handle_center_chart,
            'zoom_to_time_range': self._handle_zoom_time_range,
            'zoom_to_distance': self._handle_zoom_distance,
            
            # Tracking
            'follow_vessel_with_distance': self._handle_follow_vessel_distance,
            'follow_vessel': self._handle_follow_vessel,
            
            # Waypoints
            'mark_spot_with_name': self._handle_mark_spot_named,
            'navigate_to_nearest_harbor': self._handle_navigate_nearest_harbor,
            
            # Weather
            'show_weather_forecast_hours': self._handle_weather_forecast_hours,
            
            # Alerts
            'set_depth_alert_under': self._handle_depth_alert_under,
            
            # Recording
            'start_track_recording': self._handle_start_track_recording,
            
            # AIS/Radar
            'show_ais_targets_within_range': self._handle_show_ais_range,
            
            # Display
            'switch_to_night_mode': self._handle_night_mode,
            'display_fish_finder_on_screen': self._handle_fish_finder_screen,
            
            # Calculations
            'calculate_eta_current_speed': self._handle_calculate_eta,
        }
        
        for action, handler in handlers.items():
            self.voice_manager.register_command_handler(action, handler)
    
    def _create_marine_commands(self):
        """Create marine-specific voice commands"""
        marine_commands = [
            # Natural language commands
            VoiceCommand(
                command_id="center-chart-vessel",
                patterns=["center the chart on my vessel", "center chart on vessel", "center on my position"],
                action="center_chart_on_vessel",
                command_type=VoiceCommandType.APPLICATION,
                description="Center chart display on vessel position",
                examples=["center the chart on my vessel", "center chart on vessel"]
            ),
            
            VoiceCommand(
                command_id="zoom-time-range",
                patterns=[r"zoom to (\d+).?minute range", r"zoom to (\d+).?min ahead"],
                action="zoom_to_time_range", 
                command_type=VoiceCommandType.APPLICATION,
                description="Zoom chart to time range ahead",
                examples=["zoom to 15-minute range ahead", "zoom to 30 min ahead"]
            ),
            
            VoiceCommand(
                command_id="follow-vessel-distance",
                patterns=[r"follow that boat.?maintain (\d+) meters", r"follow vessel.?keep (\d+) meter distance"],
                action="follow_vessel_with_distance",
                command_type=VoiceCommandType.APPLICATION,
                description="Follow vessel maintaining specified distance",
                examples=["follow that boat, maintain 200 meters", "follow vessel, keep 100 meter distance"]
            ),
            
            VoiceCommand(
                command_id="mark-spot-named",
                patterns=[r"mark this spot as ['\"]([^'\"]+)['\"]", r"mark location as ['\"]([^'\"]+)['\"]"],
                action="mark_spot_with_name",
                command_type=VoiceCommandType.APPLICATION,
                description="Mark current location with custom name",
                examples=["mark this spot as 'Tuna School'", "mark location as 'Fishing Spot 1'"]
            ),
            
            VoiceCommand(
                command_id="weather-forecast-hours",
                patterns=[r"show me the weather for next (\d+) hours", r"weather forecast (\d+) hours"],
                action="show_weather_forecast_hours",
                command_type=VoiceCommandType.APPLICATION,
                description="Show weather forecast for specified hours",
                examples=["show me the weather for next 6 hours", "weather forecast 12 hours"]
            ),
            
            VoiceCommand(
                command_id="navigate-nearest-harbor",
                patterns=["navigate to nearest harbor", "go to closest harbor", "find nearest harbor"],
                action="navigate_to_nearest_harbor",
                command_type=VoiceCommandType.APPLICATION,
                description="Navigate to the nearest harbor",
                examples=["navigate to nearest harbor", "go to closest harbor"]
            ),
            
            VoiceCommand(
                command_id="depth-alert",
                patterns=[r"alert if depth less than (\d+) feet", r"warn when depth under (\d+) meters"],
                action="set_depth_alert_under",
                command_type=VoiceCommandType.APPLICATION,
                description="Set depth alert for shallow water",
                examples=["alert if depth less than 10 feet", "warn when depth under 3 meters"]
            ),
            
            VoiceCommand(
                command_id="track-recording",
                patterns=["start recording our track", "begin track logging", "record our path"],
                action="start_track_recording",
                command_type=VoiceCommandType.APPLICATION,
                description="Start recording vessel track",
                examples=["start recording our track", "begin track logging"]
            ),
            
            VoiceCommand(
                command_id="ais-targets-range",
                patterns=[r"show AIS targets within (\d+) miles", r"display vessels within (\d+) nautical miles"],
                action="show_ais_targets_within_range",
                command_type=VoiceCommandType.APPLICATION,
                description="Show AIS targets within specified range",
                examples=["show AIS targets within 2 miles", "display vessels within 5 nautical miles"]
            ),
            
            VoiceCommand(
                command_id="night-mode",
                patterns=["switch to night mode", "enable night mode", "night display"],
                action="switch_to_night_mode",
                command_type=VoiceCommandType.APPLICATION,
                description="Switch display to night mode",
                examples=["switch to night mode", "enable night mode"]
            ),
            
            VoiceCommand(
                command_id="fish-finder-screen",
                patterns=[r"display fish finder on screen (\d+)", r"show sonar on display (\d+)"],
                action="display_fish_finder_on_screen",
                command_type=VoiceCommandType.APPLICATION,
                description="Display fish finder on specified screen",
                examples=["display fish finder on screen 2", "show sonar on display 1"]
            ),
            
            VoiceCommand(
                command_id="calculate-eta",
                patterns=["calculate ETA at current speed", "estimate arrival time", "how long to destination"],
                action="calculate_eta_current_speed",
                command_type=VoiceCommandType.APPLICATION,
                description="Calculate estimated time of arrival",
                examples=["calculate ETA at current speed", "estimate arrival time"]
            ),
        ]
        
        # Register all marine commands
        for command in marine_commands:
            self.voice_manager.register_command(command)
    
    def process_natural_language_command(self, text: str) -> Optional[ParsedMarineCommand]:
        """Process natural language command with marine context"""
        return self.nlu_processor.parse_command(text)
    
    # Command handlers
    def _handle_center_chart(self, command, parameters, text):
        """Center chart on vessel position"""
        logger.info("Centering chart on vessel position")
        # Integrate with marine autopilot service to get current position
        # Send command to chart display system
        return True
    
    def _handle_zoom_time_range(self, command, parameters, text):
        """Zoom chart to time range"""
        time_param = next((p for p in parameters if p.name == "time"), None)
        if time_param:
            minutes = time_param.value
            logger.info(f"Zooming chart to {minutes}-minute range ahead")
            # Calculate zoom level based on current speed and time
            # Send zoom command to chart system
            return True
        return False
    
    def _handle_zoom_distance(self, command, parameters, text):
        """Zoom chart to distance range"""
        distance_param = next((p for p in parameters if p.name == "distance"), None)
        if distance_param:
            logger.info(f"Zooming chart to {distance_param.value} {distance_param.unit}")
            return True
        return False
    
    def _handle_follow_vessel_distance(self, command, parameters, text):
        """Follow vessel with maintain distance"""
        distance_param = next((p for p in parameters if p.name == "distance"), None)
        if distance_param:
            distance = distance_param.value
            logger.info(f"Starting to follow vessel, maintaining {distance} {distance_param.unit}")
            # Integrate with marine autopilot follow vessel system
            return True
        return False
    
    def _handle_follow_vessel(self, command, parameters, text):
        """Follow vessel without distance specified"""
        logger.info("Starting to follow vessel with default distance")
        return True
    
    def _handle_mark_spot_named(self, command, parameters, text):
        """Mark current spot with custom name"""
        name_param = next((p for p in parameters if p.name == "name"), None)
        if name_param:
            spot_name = name_param.value
            logger.info(f"Marking current location as '{spot_name}'")
            # Integrate with fishing spots database
            # Get current GPS position and save waypoint
            return True
        return False
    
    def _handle_navigate_nearest_harbor(self, command, parameters, text):
        """Navigate to nearest harbor"""
        logger.info("Finding and navigating to nearest harbor")
        # Query marine database for nearest harbor
        # Set navigation waypoint
        return True
    
    def _handle_weather_forecast_hours(self, command, parameters, text):
        """Show weather forecast for hours"""
        time_param = next((p for p in parameters if p.name == "time"), None)
        if time_param:
            hours = time_param.value
            logger.info(f"Showing weather forecast for next {hours} hours")
            # Integrate with weather service
            return True
        return False
    
    def _handle_depth_alert_under(self, command, parameters, text):
        """Set depth alert for shallow water"""
        depth_param = next((p for p in parameters if p.name == "depth"), None)
        if depth_param:
            depth = depth_param.value
            unit = depth_param.unit
            logger.info(f"Setting depth alert for less than {depth} {unit}")
            # Configure depth alert in marine autopilot
            return True
        return False
    
    def _handle_start_track_recording(self, command, parameters, text):
        """Start recording vessel track"""
        logger.info("Starting track recording")
        # Start GPS track recording
        return True
    
    def _handle_show_ais_range(self, command, parameters, text):
        """Show AIS targets within range"""
        distance_param = next((p for p in parameters if p.name == "distance"), None)
        if distance_param:
            range_val = distance_param.value
            unit = distance_param.unit
            logger.info(f"Showing AIS targets within {range_val} {unit}")
            # Configure AIS display filter
            return True
        return False
    
    def _handle_night_mode(self, command, parameters, text):
        """Switch to night mode"""
        logger.info("Switching to night mode display")
        # Change display theme to night mode
        return True
    
    def _handle_fish_finder_screen(self, command, parameters, text):
        """Display fish finder on screen"""
        screen_param = next((p for p in parameters if p.name == "screen_number"), None)
        if screen_param:
            screen_num = screen_param.value
            logger.info(f"Displaying fish finder on screen {screen_num}")
            # Configure multi-display setup
            return True
        return False
    
    def _handle_calculate_eta(self, command, parameters, text):
        """Calculate ETA at current speed"""
        logger.info("Calculating ETA at current speed")
        # Get current speed, destination, and calculate ETA
        # Display result to user
        return True

async def main():
    """Example usage of marine natural language commands"""
    
    # Initialize voice control with marine extensions
    voice_manager = VoiceControlManager()
    marine_commands = MarineVoiceCommands(voice_manager)
    
    print("=== Marine Natural Language Commands Demo ===")
    
    # Test natural language commands
    test_commands = [
        "Center the chart on my vessel",
        "Zoom to 15-minute range ahead", 
        "Follow that boat, maintain 200 meters",
        "Mark this spot as 'Tuna School'",
        "Show me the weather for next 6 hours",
        "Navigate to nearest harbor",
        "Alert if depth less than 10 feet",
        "Start recording our track",
        "Show AIS targets within 2 miles",
        "Switch to night mode",
        "Display fish finder on screen 2",
        "Calculate ETA at current speed",
    ]
    
    voice_manager.start_session("marine_user")
    
    print(f"Processing {len(test_commands)} marine commands:")
    print()
    
    for i, command_text in enumerate(test_commands, 1):
        print(f"{i:2d}. \"{command_text}\"")
        
        # Parse with NLU processor
        parsed = marine_commands.process_natural_language_command(command_text)
        if parsed:
            print(f"    → Category: {parsed.command_type.value}")
            print(f"    → Action: {parsed.action}")
            if parsed.parameters:
                params_str = ", ".join([f"{p.name}={p.value} {p.unit or ''}" for p in parsed.parameters])
                print(f"    → Parameters: {params_str}")
        
        # Process with voice manager
        utterance = voice_manager.process_utterance(command_text, 0.9)
        if utterance:
            print(f"    → Status: {utterance.state.value}")
            if utterance.matched_command:
                print(f"    → Matched: {utterance.matched_command}")
        
        print()
    
    # Get marine-specific command help
    marine_help = voice_manager.get_available_commands(VoiceCommandType.APPLICATION)
    marine_count = len([cmd for cmd in marine_help if 'marine' in cmd.get('description', '').lower() or 
                       any(keyword in cmd.get('description', '').lower() 
                           for keyword in ['chart', 'vessel', 'harbor', 'weather', 'ais', 'depth'])])
    
    print(f"Marine-specific commands available: {marine_count}")
    
    # Show session statistics
    stats = voice_manager.get_session_stats()
    if stats:
        print(f"\nSession Statistics:")
        print(f"  • Total commands processed: {stats['total_utterances']}")
        print(f"  • Successfully executed: {stats['commands_executed']}")
        print(f"  • Success rate: {stats['success_rate']:.1%}")
    
    voice_manager.end_session()
    print("\nMarine voice command demo completed")

if __name__ == "__main__":
    asyncio.run(main())