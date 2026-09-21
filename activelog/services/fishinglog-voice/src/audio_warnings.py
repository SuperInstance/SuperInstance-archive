"""
Audio Collision Warning System
Professional audio alerts for marine safety
"""

import logging
import threading
import time
from typing import Dict, Any, List
# import pyttsx3

logger = logging.getLogger(__name__)

class AudioWarningSystem:
    def __init__(self):
        self.tts_engine = None  # Simulated TTS
        self.warning_active = False
        self.last_warning_time = {}
        
        logger.info("Audio Warning System initialized (simulation mode)")
    
    def process_collision_warnings(self, collision_data: Dict[str, Any]):
        """Process collision risk data and generate audio warnings"""
        try:
            risks = collision_data.get('risks', [])
            
            for risk in risks:
                risk_level = risk.get('risk_level', 'safe')
                vessel_id = risk.get('target_mmsi', 'unknown')
                
                if risk_level in ['danger', 'warning']:
                    self._generate_collision_warning(risk)
                    
        except Exception as e:
            logger.error(f"Collision warning processing error: {e}")
    
    def process_system_alerts(self, alerts: List[Dict[str, Any]]):
        """Process system alerts and generate audio warnings"""
        for alert in alerts:
            alert_type = alert.get('type', 'info')
            message = alert.get('message', '')
            
            if alert_type in ['critical', 'emergency']:
                self._speak_alert(message, urgent=True)
            elif alert_type == 'warning':
                self._speak_alert(message, urgent=False)
    
    def _generate_collision_warning(self, risk: Dict[str, Any]):
        """Generate collision warning announcement"""
        vessel_id = risk.get('target_mmsi', 'unknown vessel')
        risk_level = risk.get('risk_level', 'warning')
        cpa_distance = risk.get('cpa_distance', 0)
        tcpa_time = risk.get('tcpa_time', 0)
        
        # Check if we've warned about this vessel recently
        current_time = time.time()
        if vessel_id in self.last_warning_time:
            if current_time - self.last_warning_time[vessel_id] < 30:  # 30 second cooldown
                return
        
        self.last_warning_time[vessel_id] = current_time
        
        if risk_level == 'danger':
            warning_text = f"DANGER! COLLISION RISK! Vessel {vessel_id}. CPA {cpa_distance:.1f} nautical miles in {tcpa_time:.0f} minutes. Take immediate evasive action."
        else:
            warning_text = f"WARNING! Collision risk with vessel {vessel_id}. CPA {cpa_distance:.1f} nautical miles in {tcpa_time:.0f} minutes. Monitor closely."
        
        self._speak_alert(warning_text, urgent=(risk_level == 'danger'))
    
    def _speak_alert(self, text: str, urgent: bool = False):
        """Speak alert with appropriate priority"""
        def speak():
            try:
                # Simulate TTS output
                logger.info(f"AUDIO WARNING {'(URGENT)' if urgent else ''}: {text}")
                    
            except Exception as e:
                logger.error(f"TTS error: {e}")
        
        # Speak in background thread
        threading.Thread(target=speak, daemon=True).start()
    
    def announce_emergency(self, emergency_type: str, details: str = ""):
        """Announce emergency situation"""
        emergency_text = f"EMERGENCY! {emergency_type.upper()}! {details}"
        
        # Simulate emergency announcements
        def emergency_announce():
            for i in range(3):
                logger.critical(f"EMERGENCY ANNOUNCEMENT #{i+1}: {emergency_text}")
                time.sleep(1)
        
        threading.Thread(target=emergency_announce, daemon=True).start()
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "warning_active": self.warning_active,
            "tts_available": self.tts_engine is not None
        }