"""
Follow Vessel Mode with Safety Parameters
Voice-controlled vessel following system
"""

import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FollowVesselController:
    def __init__(self):
        self.nav_system_url = "http://localhost:8365"
        self.following_enabled = False
        self.target_vessel = None
        self.follow_distance = 0.5  # nautical miles
        self.safety_distance = 0.2  # minimum distance
        
        logger.info("Follow Vessel Controller initialized")
    
    def execute_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = command.get('action')
        params = command.get('params', {})
        
        if action == 'engage':
            return self._engage_follow(params)
        elif action == 'disengage':
            return self._disengage_follow()
        elif action == 'set_distance':
            return self._set_follow_distance(params)
        else:
            return {"status": "error", "message": f"Unknown follow action: {action}"}
    
    def _engage_follow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get('target')
        if not target:
            return {"status": "error", "message": "No target vessel specified"}
        
        self.target_vessel = target
        self.following_enabled = True
        
        return {
            "status": "success",
            "message": f"Following vessel {target} at {self.follow_distance}nm",
            "target": target,
            "distance": self.follow_distance
        }
    
    def _disengage_follow(self) -> Dict[str, Any]:
        self.following_enabled = False
        self.target_vessel = None
        
        return {"status": "success", "message": "Follow mode disengaged"}
    
    def _set_follow_distance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        distance = params.get('distance', 0.5)
        
        if distance < self.safety_distance:
            return {"status": "error", "message": f"Distance too small. Minimum: {self.safety_distance}nm"}
        
        self.follow_distance = distance
        
        return {
            "status": "success",
            "message": f"Follow distance set to {distance}nm",
            "distance": distance
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "following_enabled": self.following_enabled,
            "target_vessel": self.target_vessel,
            "follow_distance": self.follow_distance,
            "safety_distance": self.safety_distance
        }