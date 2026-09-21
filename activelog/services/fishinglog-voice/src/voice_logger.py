"""
Voice-Activated Log Entry System
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)

class VoiceLogger:
    def __init__(self):
        self.log_entries = []
        logger.info("Voice Logger initialized")
    
    def log_voice_command(self, command_text: str):
        """Log voice command for audit trail"""
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'voice_command',
            'content': command_text,
            'source': 'voice_input'
        }
        
        self.log_entries.append(entry)
        logger.info(f"Voice command logged: {command_text}")
    
    def create_voice_log(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Create log entry from voice command"""
        content = command.get('params', {}).get('content', '')
        
        if not content:
            return {"status": "error", "message": "No log content provided"}
        
        entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'type': 'voice_log',
            'content': content,
            'source': 'voice_input'
        }
        
        self.log_entries.append(entry)
        
        return {
            "status": "success",
            "message": f"Log entry created: {content[:50]}...",
            "entry_id": len(self.log_entries)
        }
    
    def get_recent_logs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent log entries"""
        return self.log_entries[-limit:]