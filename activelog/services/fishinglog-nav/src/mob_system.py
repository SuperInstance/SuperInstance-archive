"""
MOB (Man Overboard) Instant Marking System
Professional MOB response system with GPS marking and recovery patterns
"""

import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import math
import threading
from geopy.distance import geodesic
# from geopy.bearing import bearing

logger = logging.getLogger(__name__)

class MOBSystem:
    """
    Professional Man Overboard system with instant GPS marking,
    search patterns, and recovery coordination
    """
    
    def __init__(self):
        self.mob_events = []
        self.active_mob = None
        self.search_patterns = {}
        self.mob_lock = threading.Lock()
        logger.info("MOB System initialized")
    
    def mark_mob(self, current_position: Dict[str, float]) -> Dict[str, Any]:
        """Instantly mark MOB position"""
        mob_time = datetime.now(timezone.utc)
        
        mob_event = {
            'mob_id': f"MOB_{mob_time.strftime('%Y%m%d_%H%M%S')}",
            'timestamp': mob_time,
            'position': {
                'lat': current_position['lat'],
                'lon': current_position['lon']
            },
            'vessel_heading': current_position.get('heading', 0.0),
            'vessel_speed': current_position.get('speed', 0.0),
            'status': 'active',
            'search_pattern': None,
            'recovery_time': None
        }
        
        with self.mob_lock:
            self.mob_events.append(mob_event)
            self.active_mob = mob_event
        
        # Generate search pattern
        self._generate_williamson_turn(mob_event)
        
        logger.critical(f"MOB MARKED: {mob_event['mob_id']} at {current_position}")
        
        return mob_event
    
    def _generate_williamson_turn(self, mob_event: Dict[str, Any]):
        """Generate Williamson Turn recovery pattern"""
        # Simplified Williamson Turn pattern
        mob_pos = mob_event['position']
        
        pattern = {
            'type': 'williamson_turn',
            'steps': [
                {'action': 'hard_starboard', 'duration': 60},
                {'action': 'course_180', 'target_heading': (mob_event['vessel_heading'] + 180) % 360},
                {'action': 'return_to_track', 'target_position': mob_pos}
            ]
        }
        
        mob_event['search_pattern'] = pattern
        return pattern
    
    def get_mob_status(self) -> Dict[str, Any]:
        """Get current MOB status"""
        with self.mob_lock:
            return {
                'active_mob': self.active_mob,
                'total_events': len(self.mob_events),
                'last_event': self.mob_events[-1] if self.mob_events else None
            }