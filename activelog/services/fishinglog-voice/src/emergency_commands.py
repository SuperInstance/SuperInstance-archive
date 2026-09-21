"""
Emergency Voice Commands System
Critical emergency command processing with immediate execution
"""

import logging
import requests
from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class EmergencyCommandHandler:
    """
    Emergency command handler for critical maritime situations
    """
    
    def __init__(self):
        self.nav_system_url = "http://localhost:8365"
        self.emergency_callback: Optional[Callable] = None
        
        # Emergency command patterns
        self.emergency_patterns = {
            'man_overboard': [
                'man overboard', 'mob', 'person overboard', 'emergency mark',
                'man in water', 'crew overboard'
            ],
            'collision_avoidance': [
                'collision', 'emergency turn', 'hard starboard', 'hard port',
                'emergency maneuver', 'avoid collision'
            ],
            'fire': [
                'fire', 'fire emergency', 'smoke', 'fire alarm'
            ],
            'medical_emergency': [
                'medical emergency', 'medical', 'injured crew', 'medical assistance'
            ],
            'flooding': [
                'flooding', 'water ingress', 'breach', 'taking on water'
            ],
            'engine_failure': [
                'engine failure', 'power loss', 'propulsion failure',
                'dead in water'
            ],
            'abandon_ship': [
                'abandon ship', 'evacuate', 'all hands abandon ship'
            ],
            'mayday': [
                'mayday', 'distress', 'emergency transmission',
                'require immediate assistance'
            ]
        }
        
        logger.info("Emergency Command Handler initialized")
    
    def set_emergency_callback(self, callback: Callable):
        """Set callback for emergency situations"""
        self.emergency_callback = callback
    
    def is_emergency_command(self, command: Dict[str, Any]) -> bool:
        """Check if command is an emergency command"""
        command_text = command.get('original_text', '').lower()
        
        for emergency_type, patterns in self.emergency_patterns.items():
            for pattern in patterns:
                if pattern in command_text:
                    return True
        
        return False
    
    def process_emergency_command(self, command: Dict[str, Any]):
        """Process emergency command immediately"""
        try:
            command_text = command.get('original_text', '').lower()
            
            # Identify emergency type
            emergency_type = self._identify_emergency_type(command_text)
            
            if not emergency_type:
                logger.warning(f"Could not identify emergency type: {command_text}")
                return
            
            # Execute emergency procedures
            emergency_data = {
                'type': emergency_type,
                'command': command,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'position': self._get_current_position(),
                'automatic_actions': self._get_automatic_actions(emergency_type)
            }
            
            logger.critical(f"EMERGENCY COMMAND: {emergency_type}")
            
            # Execute immediate actions
            self._execute_immediate_actions(emergency_type, emergency_data)
            
            # Notify emergency callback
            if self.emergency_callback:
                self.emergency_callback(emergency_data)
            
        except Exception as e:
            logger.error(f"Emergency command processing error: {e}")
    
    def _identify_emergency_type(self, command_text: str) -> Optional[str]:
        """Identify type of emergency from command text"""
        for emergency_type, patterns in self.emergency_patterns.items():
            for pattern in patterns:
                if pattern in command_text:
                    return emergency_type
        
        return None
    
    def _execute_immediate_actions(self, emergency_type: str, emergency_data: Dict[str, Any]):
        """Execute immediate emergency actions"""
        try:
            if emergency_type == 'man_overboard':
                self._execute_mob_procedures(emergency_data)
            
            elif emergency_type == 'collision_avoidance':
                self._execute_collision_avoidance(emergency_data)
            
            elif emergency_type == 'fire':
                self._execute_fire_procedures(emergency_data)
            
            elif emergency_type == 'medical_emergency':
                self._execute_medical_procedures(emergency_data)
            
            elif emergency_type == 'mayday':
                self._execute_mayday_procedures(emergency_data)
            
            # Log emergency action
            self._log_emergency_action(emergency_type, emergency_data)
            
        except Exception as e:
            logger.error(f"Emergency action execution error: {e}")
    
    def _execute_mob_procedures(self, emergency_data: Dict[str, Any]):
        """Execute man overboard procedures"""
        try:
            # Mark MOB position immediately
            response = requests.post(f"{self.nav_system_url}/api/mob/mark", 
                                   json={}, timeout=3)
            
            if response.status_code == 200:
                logger.info("MOB position marked")
                
                # Additional MOB actions could include:
                # - Sound general alarm
                # - Display MOB on all screens
                # - Begin Williamson Turn
                # - Prepare rescue equipment
                
        except Exception as e:
            logger.error(f"MOB procedure error: {e}")
    
    def _execute_collision_avoidance(self, emergency_data: Dict[str, Any]):
        """Execute collision avoidance procedures"""
        command_text = emergency_data['command'].get('original_text', '').lower()
        
        try:
            # Determine evasive action from command
            if 'hard starboard' in command_text:
                # Emergency turn to starboard
                heading_change = 90  # Hard right turn
                direction = 'starboard'
            elif 'hard port' in command_text:
                # Emergency turn to port
                heading_change = -90  # Hard left turn
                direction = 'port'
            else:
                # Default evasive action
                heading_change = 45
                direction = 'starboard'
            
            # Send emergency turn command
            response = requests.post(f"{self.nav_system_url}/api/autopilot/emergency_turn",
                                   json={
                                       'direction': direction,
                                       'degrees': abs(heading_change),
                                       'emergency': True
                                   }, timeout=3)
            
            if response.status_code == 200:
                logger.info(f"Emergency evasive action: {direction} {abs(heading_change)}°")
            
        except Exception as e:
            logger.error(f"Collision avoidance error: {e}")
    
    def _execute_fire_procedures(self, emergency_data: Dict[str, Any]):
        """Execute fire emergency procedures"""
        try:
            # Fire emergency actions
            fire_actions = {
                'sound_alarm': True,
                'close_vents': True,
                'prepare_extinguishers': True,
                'radio_alert': True
            }
            
            logger.critical("FIRE EMERGENCY PROCEDURES ACTIVATED")
            
            # In production, would interface with fire suppression systems
            
        except Exception as e:
            logger.error(f"Fire procedure error: {e}")
    
    def _execute_medical_procedures(self, emergency_data: Dict[str, Any]):
        """Execute medical emergency procedures"""
        try:
            medical_actions = {
                'prepare_medical_kit': True,
                'radio_medical_assistance': True,
                'log_medical_emergency': True
            }
            
            logger.critical("MEDICAL EMERGENCY PROCEDURES ACTIVATED")
            
        except Exception as e:
            logger.error(f"Medical procedure error: {e}")
    
    def _execute_mayday_procedures(self, emergency_data: Dict[str, Any]):
        """Execute mayday/distress procedures"""
        try:
            # Mayday procedures
            position = emergency_data.get('position', {})
            
            mayday_message = {
                'call': 'MAYDAY MAYDAY MAYDAY',
                'vessel_name': 'Vessel Name',  # Would get from config
                'position': position,
                'nature_of_distress': 'Unknown',
                'assistance_required': 'Immediate assistance',
                'timestamp': emergency_data['timestamp']
            }
            
            logger.critical(f"MAYDAY TRANSMISSION PREPARED: {mayday_message}")
            
            # In production, would automatically transmit on Channel 16
            
        except Exception as e:
            logger.error(f"Mayday procedure error: {e}")
    
    def _get_current_position(self) -> Dict[str, float]:
        """Get current vessel position"""
        try:
            response = requests.get(f"{self.nav_system_url}/api/position", timeout=2)
            
            if response.status_code == 200:
                return response.json()
            
        except Exception as e:
            logger.error(f"Position request error: {e}")
        
        return {"lat": 0.0, "lon": 0.0}
    
    def _get_automatic_actions(self, emergency_type: str) -> List[str]:
        """Get list of automatic actions for emergency type"""
        action_lists = {
            'man_overboard': [
                'Mark MOB position',
                'Sound alarm',
                'Display MOB on screens',
                'Begin search pattern'
            ],
            'collision_avoidance': [
                'Execute evasive maneuver',
                'Sound collision alarm',
                'Log incident'
            ],
            'fire': [
                'Sound fire alarm',
                'Close ventilation',
                'Prepare fire suppression'
            ],
            'medical_emergency': [
                'Prepare medical kit',
                'Contact medical assistance',
                'Log medical event'
            ],
            'mayday': [
                'Prepare distress call',
                'Record position',
                'Activate emergency beacon'
            ]
        }
        
        return action_lists.get(emergency_type, [])
    
    def _log_emergency_action(self, emergency_type: str, emergency_data: Dict[str, Any]):
        """Log emergency action to permanent record"""
        try:
            log_entry = {
                'timestamp': emergency_data['timestamp'],
                'type': 'EMERGENCY',
                'subtype': emergency_type,
                'command': emergency_data['command']['original_text'],
                'position': emergency_data['position'],
                'actions_taken': emergency_data['automatic_actions']
            }
            
            # In production, would write to permanent emergency log
            logger.critical(f"EMERGENCY LOG: {log_entry}")
            
        except Exception as e:
            logger.error(f"Emergency logging error: {e}")
    
    def execute_emergency_procedures(self, emergency_data: Dict[str, Any]):
        """Execute comprehensive emergency procedures"""
        emergency_type = emergency_data.get('type', 'unknown')
        
        try:
            logger.critical(f"EXECUTING EMERGENCY PROCEDURES: {emergency_type}")
            
            # Execute type-specific procedures
            self._execute_immediate_actions(emergency_type, emergency_data)
            
            # General emergency procedures
            self._activate_general_alarm()
            self._notify_all_stations()
            self._prepare_emergency_equipment()
            
        except Exception as e:
            logger.error(f"Emergency procedure execution error: {e}")
    
    def _activate_general_alarm(self):
        """Activate general alarm system"""
        logger.critical("GENERAL ALARM ACTIVATED")
        # In production, would interface with ship's alarm system
    
    def _notify_all_stations(self):
        """Notify all bridge stations of emergency"""
        logger.critical("ALL STATIONS NOTIFIED OF EMERGENCY")
        # In production, would send alerts to all connected systems
    
    def _prepare_emergency_equipment(self):
        """Prepare emergency equipment"""
        logger.critical("EMERGENCY EQUIPMENT PREPARATION INITIATED")
        # In production, would interface with emergency systems
    
    def get_emergency_commands_help(self) -> str:
        """Get help for emergency voice commands"""
        return """
EMERGENCY VOICE COMMANDS:

IMMEDIATE EXECUTION - NO CONFIRMATION REQUIRED

Man Overboard:
- "Man overboard!" / "MOB!" / "Person overboard!"

Collision Avoidance:
- "Hard starboard!" / "Hard port!"
- "Emergency turn!" / "Avoid collision!"

Fire Emergency:
- "Fire!" / "Fire emergency!" / "Smoke!"

Medical Emergency:
- "Medical emergency!" / "Injured crew!"

Engine/Power:
- "Engine failure!" / "Power loss!"

Distress:
- "Mayday!" / "Distress!" / "Require immediate assistance!"

NOTE: Emergency commands execute immediately without confirmation.
All emergency actions are logged automatically.
        """.strip()
    
    def get_status(self) -> Dict[str, Any]:
        """Get emergency command handler status"""
        return {
            'emergency_patterns': len(self.emergency_patterns),
            'nav_system_connected': self._check_nav_system_connection(),
            'emergency_callback_set': self.emergency_callback is not None
        }
    
    def _check_nav_system_connection(self) -> bool:
        """Check connection to navigation system"""
        try:
            response = requests.get(f"{self.nav_system_url}/api/position", timeout=1)
            return response.status_code == 200
        except:
            return False