"""
Track Recording with Automatic Logging
"""

import logging
from typing import Dict, List
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger(__name__)

class TrackRecorder:
    def __init__(self):
        self.track_points = deque(maxlen=10000)
        self.recording = True
        logger.info("Track Recorder initialized")
    
    def add_position(self, position: Dict[str, float]):
        """Add position to track log"""
        if self.recording and position:
            track_point = {
                'timestamp': datetime.now(timezone.utc),
                'lat': position['lat'],
                'lon': position['lon'],
                'speed': position.get('speed', 0.0),
                'heading': position.get('heading', 0.0)
            }
            self.track_points.append(track_point)
    
    def get_track_data(self) -> List[Dict]:
        """Get track data"""
        return list(self.track_points)