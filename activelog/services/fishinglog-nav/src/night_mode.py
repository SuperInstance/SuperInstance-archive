"""
Night Mode with Red-Light Preservation
"""

import logging

logger = logging.getLogger(__name__)

class NightModeManager:
    def __init__(self):
        self.night_mode_enabled = False
        logger.info("Night Mode Manager initialized")
    
    def set_mode(self, enabled: bool):
        """Enable/disable night mode"""
        self.night_mode_enabled = enabled
        logger.info(f"Night mode: {'enabled' if enabled else 'disabled'}")