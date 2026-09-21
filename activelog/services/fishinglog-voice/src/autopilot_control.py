"""
Voice-Activated Autopilot Control System
Professional autopilot interface with safety protocols
"""

import logging
import requests
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class AutopilotController:
    """
    Voice-controlled autopilot system with comprehensive safety features
    """
    
    def __init__(self):
        self.nav_system_url = "http://localhost:8365"
        self.autopilot_engaged = False
        self.current_heading = 0.0
        self.target_heading = 0.0
        self.autopilot_mode = 'standby'  # standby, heading, track, nav
        
        # Safety parameters
        self.max_heading_change = 45.0  # degrees per command
        self.heading_change_rate = 2.0   # degrees per second
        self.safety_timeout = 300        # seconds before automatic disengagement
        self.last_command_time = None
        
        # Autopilot states
        self.valid_modes = ['standby', 'heading', 'track', 'nav', 'follow']
        
        logger.info("Autopilot Controller initialized")
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Execute autopilot voice command"""
        try:
            action = command.get('action')
            params = command.get('params', {})
            
            if action == 'engage':
                return self._engage_autopilot(params)
            elif action == 'disengage':
                return self._disengage_autopilot(params)
            elif action == 'set_heading':
                return self._set_heading(params)
            elif action == 'adjust_heading':
                return self._adjust_heading(params)
            elif action == 'set_mode':
                return self._set_mode(params)
            elif action == 'status':
                return self._get_status()
            else:
                return {"status": "error", "message": f"Unknown autopilot action: {action}"}
                
        except Exception as e:
            logger.error(f"Autopilot command execution error: {e}")
            return {"status": "error", "message": str(e)}
    
    def _engage_autopilot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Engage autopilot system"""
        try:
            if self.autopilot_engaged:
                return {
                    "status": "info", 
                    "message": "Autopilot already engaged",
                    "current_heading": self.target_heading
                }
            
            # Get current vessel heading
            current_status = self._get_vessel_status()
            if not current_status:
                return {"status": "error", "message": "Cannot get vessel status"}
            
            self.current_heading = current_status.get('heading', 0.0)
            
            # Set initial target heading to current heading
            initial_heading = params.get('heading', self.current_heading)
            
            # Validate heading
            if not self._validate_heading(initial_heading):
                return {"status": "error", "message": "Invalid heading value"}
            
            # Engage autopilot
            response = self._send_autopilot_command('engage', {
                'heading': initial_heading,
                'mode': 'heading'
            })
            
            if response and response.get('status') == 'success':
                self.autopilot_engaged = True
                self.target_heading = initial_heading
                self.autopilot_mode = 'heading'
                self.last_command_time = datetime.now(timezone.utc)
                
                return {
                    "status": "success",
                    "message": f"Autopilot engaged, heading {initial_heading:.0f} degrees",
                    "heading": initial_heading,
                    "mode": self.autopilot_mode
                }
            else:
                return {"status": "error", "message": "Failed to engage autopilot"}
                
        except Exception as e:
            logger.error(f"Autopilot engagement error: {e}")
            return {"status": "error", "message": "Autopilot engagement failed"}
    
    def _disengage_autopilot(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Disengage autopilot system"""
        try:
            if not self.autopilot_engaged:
                return {
                    "status": "info",
                    "message": "Autopilot already disengaged"
                }
            
            # Send disengage command
            response = self._send_autopilot_command('disengage', {})
            
            if response and response.get('status') == 'success':
                self.autopilot_engaged = False
                self.autopilot_mode = 'standby'
                self.last_command_time = None
                
                return {
                    "status": "success",
                    "message": "Autopilot disengaged - manual control",
                    "mode": "manual"
                }
            else:
                return {"status": "error", "message": "Failed to disengage autopilot"}
                
        except Exception as e:
            logger.error(f"Autopilot disengagement error: {e}")
            return {"status": "error", "message": "Autopilot disengagement failed"}
    
    def _set_heading(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set autopilot heading"""
        try:
            new_heading = params.get('heading')
            
            if new_heading is None:
                return {"status": "error", "message": "No heading specified"}
            
            # Validate heading
            if not self._validate_heading(new_heading):
                return {"status": "error", "message": "Invalid heading (0-360 degrees)"}
            
            # Check if autopilot is engaged
            if not self.autopilot_engaged:
                return {"status": "error", "message": "Autopilot not engaged"}
            
            # Check for excessive heading change
            heading_change = abs(new_heading - self.target_heading)
            if heading_change > 180:
                heading_change = 360 - heading_change
            
            if heading_change > self.max_heading_change:
                return {
                    "status": "error",
                    "message": f"Heading change too large ({heading_change:.0f}°). Maximum: {self.max_heading_change:.0f}°"
                }
            
            # Send heading command
            response = self._send_autopilot_command('set_heading', {
                'heading': new_heading,
                'rate': self.heading_change_rate
            })
            
            if response and response.get('status') == 'success':
                self.target_heading = new_heading
                self.last_command_time = datetime.now(timezone.utc)
                
                return {
                    "status": "success",
                    "message": f"Autopilot heading set to {new_heading:.0f} degrees",
                    "heading": new_heading,
                    "heading_change": heading_change
                }
            else:
                return {"status": "error", "message": "Failed to set heading"}
                
        except Exception as e:
            logger.error(f"Set heading error: {e}")
            return {"status": "error", "message": "Set heading failed"}
    
    def _adjust_heading(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Adjust current heading by specified amount"""
        try:
            direction = params.get('direction', '').lower()
            degrees = params.get('degrees', 0)
            
            if not direction or degrees <= 0:
                return {"status": "error", "message": "Invalid heading adjustment"}
            
            if not self.autopilot_engaged:
                return {"status": "error", "message": "Autopilot not engaged"}
            
            # Validate adjustment amount
            if degrees > self.max_heading_change:
                return {
                    "status": "error",
                    "message": f"Heading adjustment too large. Maximum: {self.max_heading_change:.0f}°"
                }
            
            # Calculate new heading
            if direction in ['right', 'starboard']:
                new_heading = (self.target_heading + degrees) % 360
            elif direction in ['left', 'port']:
                new_heading = (self.target_heading - degrees) % 360
            else:
                return {"status": "error", "message": f"Invalid direction: {direction}"}
            
            # Send heading adjustment
            response = self._send_autopilot_command('set_heading', {
                'heading': new_heading,
                'rate': self.heading_change_rate
            })
            
            if response and response.get('status') == 'success':
                self.target_heading = new_heading
                self.last_command_time = datetime.now(timezone.utc)
                
                return {
                    "status": "success",
                    "message": f"Adjusted heading {degrees}° {direction} to {new_heading:.0f}°",
                    "heading": new_heading,
                    "adjustment": f"{degrees}° {direction}"
                }
            else:
                return {"status": "error", "message": "Failed to adjust heading"}
                
        except Exception as e:
            logger.error(f"Adjust heading error: {e}")
            return {"status": "error", "message": "Adjust heading failed"}
    
    def _set_mode(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Set autopilot mode"""
        try:
            mode = params.get('mode', '').lower()
            
            if mode not in self.valid_modes:
                return {
                    "status": "error",
                    "message": f"Invalid mode. Valid modes: {', '.join(self.valid_modes)}"
                }
            
            if not self.autopilot_engaged and mode != 'standby':
                return {"status": "error", "message": "Autopilot must be engaged first"}
            
            # Send mode change command
            response = self._send_autopilot_command('set_mode', {'mode': mode})
            
            if response and response.get('status') == 'success':
                self.autopilot_mode = mode
                self.last_command_time = datetime.now(timezone.utc)
                
                return {
                    "status": "success",
                    "message": f"Autopilot mode set to {mode}",
                    "mode": mode
                }
            else:
                return {"status": "error", "message": f"Failed to set mode to {mode}"}
                
        except Exception as e:
            logger.error(f"Set mode error: {e}")
            return {"status": "error", "message": "Set mode failed"}
    
    def _get_status(self) -> Dict[str, Any]:
        """Get autopilot status"""
        return {
            "status": "success",
            "autopilot_engaged": self.autopilot_engaged,
            "current_heading": self.current_heading,
            "target_heading": self.target_heading,
            "mode": self.autopilot_mode,
            "last_command": self.last_command_time.isoformat() if self.last_command_time else None,
            "safety_parameters": {
                "max_heading_change": self.max_heading_change,
                "heading_change_rate": self.heading_change_rate,
                "safety_timeout": self.safety_timeout
            }
        }
    
    def _validate_heading(self, heading: float) -> bool:
        """Validate heading value"""
        try:
            return 0.0 <= float(heading) <= 360.0
        except (ValueError, TypeError):
            return False
    
    def _get_vessel_status(self) -> Optional[Dict[str, Any]]:
        """Get current vessel status"""
        try:
            response = requests.get(f"{self.nav_system_url}/api/position", timeout=3)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get vessel status: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Vessel status request error: {e}")
            return None
    
    def _send_autopilot_command(self, command: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send command to autopilot system"""
        try:
            url = f"{self.nav_system_url}/api/autopilot/{command}"
            
            response = requests.post(url, json=params, timeout=5)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Autopilot command failed: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Autopilot command request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Autopilot command error: {e}")
            return None
    
    def check_safety_timeout(self) -> bool:
        """Check if safety timeout has been exceeded"""
        if not self.autopilot_engaged or not self.last_command_time:
            return False
        
        time_since_command = (datetime.now(timezone.utc) - self.last_command_time).total_seconds()
        
        if time_since_command > self.safety_timeout:
            logger.warning("Autopilot safety timeout exceeded")
            self._emergency_disengage()
            return True
        
        return False
    
    def _emergency_disengage(self):
        """Emergency autopilot disengagement"""
        try:
            logger.critical("EMERGENCY: Autopilot disengaged due to safety timeout")
            
            self._send_autopilot_command('emergency_disengage', {
                'reason': 'safety_timeout',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            self.autopilot_engaged = False
            self.autopilot_mode = 'standby'
            self.last_command_time = None
            
        except Exception as e:
            logger.error(f"Emergency disengage error: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get controller status"""
        return self._get_status()
    
    def get_voice_commands_help(self) -> str:
        """Get help text for autopilot voice commands"""
        return """
Autopilot Voice Commands:

Engagement:
- "Engage autopilot" / "Turn on autopilot"
- "Disengage autopilot" / "Turn off autopilot" / "Manual control"

Heading Control:
- "Set heading [0-360]" / "Heading [0-360]" 
- "Turn to [0-360] degrees"
- "Steer [0-360] degrees"

Heading Adjustments:
- "Turn [degrees] degrees right/starboard"
- "Turn [degrees] degrees left/port"
- "Come right/left [degrees]"
- "Adjust heading right/left [degrees]"

Mode Control:
- "Set mode [heading/track/nav/follow]"
- "Autopilot mode [mode]"

Status:
- "Autopilot status"
- "Current heading"

Safety Features:
- Maximum heading change: 45° per command
- Safety timeout: 5 minutes
- Confirmation required for all commands
- Emergency disengagement on timeout

Examples:
- "Engage autopilot heading 090"
- "Turn 10 degrees starboard" 
- "Set heading 180"
- "Disengage autopilot"
        """.strip()