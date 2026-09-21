"""
Voice Command Integration System
Integrates voice commands with ActiveLog marine and fishing services
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging
import requests
from pathlib import Path

from .marine_commands import MarineVoiceCommands, ParsedMarineCommand, MarineParameter
from .voice_control import VoiceControlManager

logger = logging.getLogger(__name__)

@dataclass
class ServiceEndpoint:
    service_name: str
    base_url: str
    health_endpoint: str
    timeout: int = 30
    
    def is_available(self) -> bool:
        """Check if service is available"""
        try:
            response = requests.get(f"{self.base_url}{self.health_endpoint}", timeout=5)
            return response.status_code == 200
        except:
            return False

class MarineServiceIntegrator:
    """Integrates voice commands with ActiveLog marine services"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        
        # Service endpoints
        self.services = {
            'marine_autopilot': ServiceEndpoint(
                'marine_autopilot',
                'http://localhost:8367',
                '/'
            ),
            'fishing_pro': ServiceEndpoint(
                'fishing_pro', 
                'http://localhost:8368',
                '/'
            ),
            'weather_service': ServiceEndpoint(
                'weather_service',
                'http://localhost:8369',
                '/health'
            ),
            'chart_service': ServiceEndpoint(
                'chart_service',
                'http://localhost:8370', 
                '/health'
            )
        }
        
        # Command execution results cache
        self.execution_cache: Dict[str, Any] = {}
        
        # Current vessel state
        self.vessel_state = {
            'position': {'latitude': 0.0, 'longitude': 0.0},
            'heading': 0.0,
            'speed': 0.0,
            'depth': 0.0,
            'following_vessel': False,
            'track_recording': False,
            'night_mode': False
        }
    
    def execute_marine_command(self, parsed_command: ParsedMarineCommand) -> Dict[str, Any]:
        """Execute parsed marine command via service integration"""
        try:
            result = {
                'command_id': str(uuid.uuid4()),
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'command_type': parsed_command.command_type.value,
                'action': parsed_command.action,
                'success': False,
                'message': '',
                'data': {}
            }
            
            # Route command to appropriate service
            if parsed_command.command_type.value in ['chart_control', 'display']:
                result = self._execute_chart_command(parsed_command, result)
            elif parsed_command.command_type.value in ['navigation', 'tracking']:
                result = self._execute_autopilot_command(parsed_command, result)
            elif parsed_command.command_type.value == 'waypoints':
                result = self._execute_waypoint_command(parsed_command, result)
            elif parsed_command.command_type.value == 'weather':
                result = self._execute_weather_command(parsed_command, result)
            elif parsed_command.command_type.value == 'fish_finder':
                result = self._execute_fishing_command(parsed_command, result)
            elif parsed_command.command_type.value == 'alerts':
                result = self._execute_alert_command(parsed_command, result)
            elif parsed_command.command_type.value == 'recording':
                result = self._execute_recording_command(parsed_command, result)
            elif parsed_command.command_type.value == 'ais_radar':
                result = self._execute_ais_command(parsed_command, result)
            elif parsed_command.command_type.value == 'calculations':
                result = self._execute_calculation_command(parsed_command, result)
            
            # Cache successful results
            if result['success']:
                self.execution_cache[result['command_id']] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing marine command: {e}")
            return {
                'success': False,
                'message': f"Command execution failed: {str(e)}",
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
    
    def _execute_chart_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute chart control commands"""
        action = command.action
        
        if action == 'center_chart_on_vessel':
            # Center chart on current vessel position
            if self._call_service('chart_service', 'POST', '/chart/center', {
                'latitude': self.vessel_state['position']['latitude'],
                'longitude': self.vessel_state['position']['longitude']
            }):
                result['success'] = True
                result['message'] = "Chart centered on vessel position"
                result['data'] = {'position': self.vessel_state['position']}
        
        elif action == 'zoom_to_time_range':
            time_param = command.get_parameter('time')
            if time_param:
                minutes = time_param.value
                # Calculate zoom based on current speed and time
                speed_knots = self.vessel_state['speed']
                distance_nm = (speed_knots * minutes) / 60
                
                if self._call_service('chart_service', 'POST', '/chart/zoom', {
                    'range_nautical_miles': distance_nm * 2  # Show range ahead and behind
                }):
                    result['success'] = True
                    result['message'] = f"Chart zoomed to {minutes}-minute range"
                    result['data'] = {'range_minutes': minutes, 'range_nm': distance_nm}
        
        elif action == 'zoom_to_distance':
            distance_param = command.get_parameter('distance')
            if distance_param:
                # Convert distance to nautical miles if needed
                distance_nm = self._convert_to_nautical_miles(distance_param.value, distance_param.unit)
                
                if self._call_service('chart_service', 'POST', '/chart/zoom', {
                    'range_nautical_miles': distance_nm
                }):
                    result['success'] = True
                    result['message'] = f"Chart zoomed to {distance_param.value} {distance_param.unit}"
                    result['data'] = {'range_nm': distance_nm}
        
        elif action == 'switch_to_night_mode':
            if self._call_service('chart_service', 'POST', '/display/mode', {'mode': 'night'}):
                self.vessel_state['night_mode'] = True
                result['success'] = True
                result['message'] = "Switched to night mode"
        
        elif action == 'switch_to_day_mode':
            if self._call_service('chart_service', 'POST', '/display/mode', {'mode': 'day'}):
                self.vessel_state['night_mode'] = False
                result['success'] = True
                result['message'] = "Switched to day mode"
        
        elif action == 'display_fish_finder_on_screen':
            screen_param = command.get_parameter('screen_number')
            if screen_param:
                screen_num = int(screen_param.value)
                if self._call_service('chart_service', 'POST', '/display/fish-finder', {
                    'screen': screen_num, 'enabled': True
                }):
                    result['success'] = True
                    result['message'] = f"Fish finder displayed on screen {screen_num}"
                    result['data'] = {'screen': screen_num}
        
        return result
    
    def _execute_autopilot_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute autopilot commands"""
        action = command.action
        
        if action == 'follow_vessel_with_distance':
            distance_param = command.get_parameter('distance')
            if distance_param:
                distance_m = self._convert_to_meters(distance_param.value, distance_param.unit)
                
                if self._call_service('marine_autopilot', 'POST', '/follow-vessel', {
                    'target_vessel_id': 'nearest',  # Would get from AIS/radar
                    'follow_distance': distance_m,
                    'relative_bearing': 180.0  # Follow behind
                }):
                    self.vessel_state['following_vessel'] = True
                    result['success'] = True
                    result['message'] = f"Following vessel at {distance_param.value} {distance_param.unit}"
                    result['data'] = {'distance_meters': distance_m}
        
        elif action == 'follow_vessel':
            # Default follow distance
            if self._call_service('marine_autopilot', 'POST', '/follow-vessel', {
                'target_vessel_id': 'nearest',
                'follow_distance': 200.0,  # 200 meters default
                'relative_bearing': 180.0
            }):
                self.vessel_state['following_vessel'] = True
                result['success'] = True
                result['message'] = "Following vessel at default distance"
        
        elif action == 'stop_following':
            if self._call_service('marine_autopilot', 'POST', '/stop', {}):
                self.vessel_state['following_vessel'] = False
                result['success'] = True
                result['message'] = "Stopped following vessel"
        
        return result
    
    def _execute_waypoint_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute waypoint commands"""
        action = command.action
        
        if action == 'mark_spot_with_name':
            name_param = command.get_parameter('name')
            if name_param:
                waypoint_data = {
                    'name': name_param.value,
                    'latitude': self.vessel_state['position']['latitude'],
                    'longitude': self.vessel_state['position']['longitude'],
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'type': 'fishing_spot'
                }
                
                # Save to fishing spots database
                if self._call_service('fishing_pro', 'POST', '/spots', waypoint_data):
                    result['success'] = True
                    result['message'] = f"Marked current location as '{name_param.value}'"
                    result['data'] = waypoint_data
        
        elif action == 'navigate_to_nearest_harbor':
            # Query for nearest harbor
            current_pos = self.vessel_state['position']
            harbor_response = self._call_service('chart_service', 'GET', '/pois/harbors/nearest', {
                'latitude': current_pos['latitude'],
                'longitude': current_pos['longitude']
            })
            
            if harbor_response:
                # Set navigation waypoint
                if self._call_service('marine_autopilot', 'POST', '/navigation/set-destination', {
                    'latitude': harbor_response.get('latitude'),
                    'longitude': harbor_response.get('longitude'),
                    'name': harbor_response.get('name', 'Nearest Harbor')
                }):
                    result['success'] = True
                    result['message'] = f"Navigating to {harbor_response.get('name', 'nearest harbor')}"
                    result['data'] = harbor_response
        
        return result
    
    def _execute_weather_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute weather commands"""
        action = command.action
        
        if action == 'show_weather_forecast_hours':
            time_param = command.get_parameter('time')
            if time_param:
                hours = int(time_param.value)
                current_pos = self.vessel_state['position']
                
                weather_data = self._call_service('weather_service', 'GET', '/forecast', {
                    'latitude': current_pos['latitude'],
                    'longitude': current_pos['longitude'],
                    'hours': hours
                })
                
                if weather_data:
                    result['success'] = True
                    result['message'] = f"Weather forecast for next {hours} hours retrieved"
                    result['data'] = weather_data
        
        elif action == 'show_current_weather':
            current_pos = self.vessel_state['position']
            weather_data = self._call_service('weather_service', 'GET', '/current', {
                'latitude': current_pos['latitude'],
                'longitude': current_pos['longitude']
            })
            
            if weather_data:
                result['success'] = True
                result['message'] = "Current weather conditions retrieved"
                result['data'] = weather_data
        
        return result
    
    def _execute_fishing_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute fishing-related commands"""
        action = command.action
        
        if action == 'show_fish_finder':
            if self._call_service('fishing_pro', 'POST', '/fish-finder/enable', {}):
                result['success'] = True
                result['message'] = "Fish finder display enabled"
        
        elif action == 'mark_fish_on_sonar':
            fish_data = {
                'latitude': self.vessel_state['position']['latitude'],
                'longitude': self.vessel_state['position']['longitude'],
                'depth': self.vessel_state['depth'],
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'type': 'fish_mark'
            }
            
            if self._call_service('fishing_pro', 'POST', '/fish-marks', fish_data):
                result['success'] = True
                result['message'] = "Fish marked on sonar"
                result['data'] = fish_data
        
        return result
    
    def _execute_alert_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute alert commands"""
        action = command.action
        
        if action == 'set_depth_alert_under':
            depth_param = command.get_parameter('depth')
            if depth_param:
                depth_m = self._convert_to_meters(depth_param.value, depth_param.unit)
                
                alert_data = {
                    'alert_type': 'shallow_water',
                    'threshold': depth_m,
                    'unit': 'meters',
                    'enabled': True
                }
                
                if self._call_service('marine_autopilot', 'POST', '/alerts/depth', alert_data):
                    result['success'] = True
                    result['message'] = f"Depth alert set for less than {depth_param.value} {depth_param.unit}"
                    result['data'] = alert_data
        
        return result
    
    def _execute_recording_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute track recording commands"""
        action = command.action
        
        if action == 'start_track_recording':
            if self._call_service('marine_autopilot', 'POST', '/tracking/start', {}):
                self.vessel_state['track_recording'] = True
                result['success'] = True
                result['message'] = "Track recording started"
        
        elif action == 'stop_track_recording':
            if self._call_service('marine_autopilot', 'POST', '/tracking/stop', {}):
                self.vessel_state['track_recording'] = False
                result['success'] = True
                result['message'] = "Track recording stopped"
        
        return result
    
    def _execute_ais_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AIS/radar commands"""
        action = command.action
        
        if action == 'show_ais_targets_within_range':
            distance_param = command.get_parameter('distance')
            if distance_param:
                range_nm = self._convert_to_nautical_miles(distance_param.value, distance_param.unit)
                current_pos = self.vessel_state['position']
                
                ais_data = self._call_service('marine_autopilot', 'GET', '/ais/targets', {
                    'latitude': current_pos['latitude'],
                    'longitude': current_pos['longitude'],
                    'range_nm': range_nm
                })
                
                if ais_data:
                    result['success'] = True
                    result['message'] = f"AIS targets within {distance_param.value} {distance_param.unit} retrieved"
                    result['data'] = ais_data
        
        return result
    
    def _execute_calculation_command(self, command: ParsedMarineCommand, result: Dict[str, Any]) -> Dict[str, Any]:
        """Execute calculation commands"""
        action = command.action
        
        if action == 'calculate_eta_current_speed':
            # Get current destination from autopilot
            nav_data = self._call_service('marine_autopilot', 'GET', '/navigation/current', {})
            
            if nav_data and nav_data.get('destination'):
                destination = nav_data['destination']
                current_speed = self.vessel_state['speed']
                
                # Calculate distance and ETA
                distance_nm = self._calculate_distance(
                    self.vessel_state['position']['latitude'],
                    self.vessel_state['position']['longitude'],
                    destination['latitude'],
                    destination['longitude']
                )
                
                if current_speed > 0:
                    eta_hours = distance_nm / current_speed
                    eta_time = datetime.now(timezone.utc) + timedelta(hours=eta_hours)
                    
                    result['success'] = True
                    result['message'] = f"ETA calculated: {eta_time.strftime('%H:%M UTC')}"
                    result['data'] = {
                        'distance_nm': distance_nm,
                        'speed_knots': current_speed,
                        'eta_hours': eta_hours,
                        'eta_time': eta_time.isoformat(),
                        'destination': destination
                    }
                else:
                    result['message'] = "Cannot calculate ETA: vessel not moving"
            else:
                result['message'] = "No destination set for ETA calculation"
        
        return result
    
    def _call_service(self, service_name: str, method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Any]:
        """Make HTTP call to service"""
        if service_name not in self.services:
            logger.error(f"Unknown service: {service_name}")
            return None
        
        service = self.services[service_name]
        if not service.is_available():
            logger.warning(f"Service {service_name} is not available")
            return None
        
        try:
            url = f"{service.base_url}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, params=data, timeout=service.timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=service.timeout)
            else:
                return None
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Service call failed: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling service {service_name}: {e}")
            return None
    
    def _convert_to_nautical_miles(self, value: float, unit: str) -> float:
        """Convert distance to nautical miles"""
        conversions = {
            'nautical_miles': 1.0,
            'miles': 0.868976,
            'kilometers': 0.539957,
            'meters': 0.000539957,
            'feet': 0.000164579,
            'yards': 0.000493737
        }
        return value * conversions.get(unit, 1.0)
    
    def _convert_to_meters(self, value: float, unit: str) -> float:
        """Convert distance to meters"""
        conversions = {
            'meters': 1.0,
            'feet': 0.3048,
            'yards': 0.9144,
            'nautical_miles': 1852.0,
            'kilometers': 1000.0,
            'miles': 1609.34
        }
        return value * conversions.get(unit, 1.0)
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in nautical miles"""
        import math
        
        # Haversine formula
        R = 3440.065  # Earth radius in nautical miles
        
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def update_vessel_state(self, position: Dict[str, float], heading: float, speed: float, depth: float):
        """Update current vessel state"""
        self.vessel_state.update({
            'position': position,
            'heading': heading,
            'speed': speed,
            'depth': depth
        })
    
    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all integrated services"""
        return {name: service.is_available() for name, service in self.services.items()}

async def main():
    """Example usage of marine service integration"""
    
    # Initialize integration system
    integrator = MarineServiceIntegrator()
    
    # Initialize voice control with marine commands
    voice_manager = VoiceControlManager()
    marine_commands = MarineVoiceCommands(voice_manager)
    
    print("=== Marine Service Integration Demo ===")
    
    # Update vessel state (simulated)
    integrator.update_vessel_state(
        position={'latitude': 40.7128, 'longitude': -74.0060},
        heading=90.0,
        speed=15.5,
        depth=25.3
    )
    
    print("Vessel state updated:")
    print(f"  Position: {integrator.vessel_state['position']}")
    print(f"  Speed: {integrator.vessel_state['speed']} knots")
    print(f"  Depth: {integrator.vessel_state['depth']} meters")
    
    # Check service availability
    service_status = integrator.get_service_status()
    print(f"\nService Status:")
    for service, available in service_status.items():
        status = "✓ Available" if available else "✗ Unavailable"
        print(f"  {service}: {status}")
    
    # Test natural language commands
    test_commands = [
        "Center the chart on my vessel",
        "Zoom to 15-minute range ahead",
        "Mark this spot as 'Good Fishing Spot'", 
        "Show me the weather for next 6 hours",
        "Alert if depth less than 10 feet",
        "Calculate ETA at current speed"
    ]
    
    print(f"\nTesting {len(test_commands)} integrated commands:")
    
    for i, command_text in enumerate(test_commands, 1):
        print(f"\n{i}. \"{command_text}\"")
        
        # Parse command
        parsed = marine_commands.process_natural_language_command(command_text)
        if parsed:
            print(f"   → Parsed: {parsed.action}")
            
            # Execute through integrator
            result = integrator.execute_marine_command(parsed)
            
            status_icon = "✓" if result['success'] else "✗"
            print(f"   → {status_icon} {result['message']}")
            
            if result['success'] and result.get('data'):
                # Show key data points
                data = result['data']
                if 'range_minutes' in data:
                    print(f"     Range: {data['range_minutes']} minutes")
                elif 'distance_meters' in data:
                    print(f"     Distance: {data['distance_meters']} meters")
                elif 'eta_time' in data:
                    eta = datetime.fromisoformat(data['eta_time'].replace('Z', '+00:00'))
                    print(f"     ETA: {eta.strftime('%H:%M UTC')}")
        else:
            print("   → Could not parse command")
    
    print(f"\nExecution cache contains {len(integrator.execution_cache)} successful commands")
    print("Marine service integration demo completed")

if __name__ == "__main__":
    asyncio.run(main())