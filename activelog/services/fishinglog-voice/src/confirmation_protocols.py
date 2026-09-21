"""
Confirmation Protocols for Critical Commands
Safety protocols requiring voice confirmation for critical navigation operations
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class ConfirmationProtocol:
    """
    Professional confirmation protocol system for critical marine operations
    """
    
    def __init__(self):
        self.pending_confirmations = {}
        self.confirmation_timeout = 30  # seconds
        self.execute_callback: Optional[Callable] = None
        
        # Critical commands that always require confirmation
        self.always_confirm = {
            'autopilot_engage', 'autopilot_disengage', 'autopilot_set_heading',
            'follow_vessel_engage', 'navigation_mob', 'emergency_*'
        }
        
        # Confirmation phrases
        self.confirmation_phrases = [
            'confirm', 'confirmed', 'yes', 'affirmative', 'execute',
            'proceed', 'roger', 'approved', 'authorize', 'correct'
        ]
        
        self.cancellation_phrases = [
            'cancel', 'cancelled', 'no', 'negative', 'abort',
            'stop', 'belay', 'disregard'
        ]
        
        logger.info("Confirmation Protocol initialized")
    
    def set_execute_callback(self, callback: Callable):
        """Set callback for executing confirmed commands"""
        self.execute_callback = callback
    
    def requires_confirmation(self, command: Dict[str, Any]) -> bool:
        """Check if command requires confirmation"""
        command_type = command.get('type', '')
        action = command.get('action', '')
        command_id = f"{command_type}_{action}"
        
        # Check against always-confirm list
        for pattern in self.always_confirm:
            if pattern.endswith('*'):
                if command_id.startswith(pattern[:-1]):
                    return True
            elif command_id == pattern:
                return True
        
        # Check confidence level
        confidence = command.get('confidence', 1.0)
        if confidence < 0.7:
            return True
        
        # Check if command has safety implications
        if self._has_safety_implications(command):
            return True
        
        return False
    
    def request_confirmation(self, command: Dict[str, Any]) -> str:
        """Request confirmation for command"""
        confirmation_id = self._generate_confirmation_id()
        
        confirmation_request = {
            'id': confirmation_id,
            'command': command,
            'requested_at': datetime.now(timezone.utc),
            'status': 'pending',
            'timeout_thread': None
        }
        
        # Generate confirmation message
        confirmation_message = self._generate_confirmation_message(command)
        
        # Store pending confirmation
        self.pending_confirmations[confirmation_id] = confirmation_request
        
        # Start timeout timer
        timeout_thread = threading.Thread(
            target=self._confirmation_timeout_handler,
            args=(confirmation_id,),
            daemon=True
        )
        timeout_thread.start()
        confirmation_request['timeout_thread'] = timeout_thread
        
        logger.info(f"Confirmation requested for command: {command}")
        
        return confirmation_message
    
    def process_confirmation_response(self, response_text: str) -> Dict[str, Any]:
        """Process confirmation response"""
        response_lower = response_text.lower().strip()
        
        # Find pending confirmation
        if not self.pending_confirmations:
            return {"status": "error", "message": "No pending confirmations"}
        
        # Get most recent pending confirmation
        confirmation_id = max(self.pending_confirmations.keys(), 
                            key=lambda x: self.pending_confirmations[x]['requested_at'])
        confirmation = self.pending_confirmations[confirmation_id]
        
        if confirmation['status'] != 'pending':
            return {"status": "error", "message": "Confirmation already processed"}
        
        # Check confirmation phrases
        if any(phrase in response_lower for phrase in self.confirmation_phrases):
            return self._process_confirmation(confirmation_id, True)
        
        # Check cancellation phrases
        elif any(phrase in response_lower for phrase in self.cancellation_phrases):
            return self._process_confirmation(confirmation_id, False)
        
        else:
            return {
                "status": "unclear",
                "message": "Please respond with 'confirm' or 'cancel'",
                "confirmation_id": confirmation_id
            }
    
    def _process_confirmation(self, confirmation_id: str, confirmed: bool) -> Dict[str, Any]:
        """Process confirmation decision"""
        if confirmation_id not in self.pending_confirmations:
            return {"status": "error", "message": "Confirmation not found"}
        
        confirmation = self.pending_confirmations[confirmation_id]
        command = confirmation['command']
        
        # Update confirmation status
        confirmation['status'] = 'confirmed' if confirmed else 'cancelled'
        confirmation['processed_at'] = datetime.now(timezone.utc)
        
        if confirmed:
            logger.info(f"Command confirmed: {command}")
            
            # Execute the command
            if self.execute_callback:
                try:
                    self.execute_callback(command)
                except Exception as e:
                    logger.error(f"Command execution error: {e}")
                    return {"status": "error", "message": "Command execution failed"}
            
            # Clean up
            del self.pending_confirmations[confirmation_id]
            
            return {
                "status": "success",
                "message": "Command confirmed and executed",
                "command": command
            }
        
        else:
            logger.info(f"Command cancelled: {command}")
            
            # Clean up
            del self.pending_confirmations[confirmation_id]
            
            return {
                "status": "cancelled",
                "message": "Command cancelled by user",
                "command": command
            }
    
    def _confirmation_timeout_handler(self, confirmation_id: str):
        """Handle confirmation timeout"""
        time.sleep(self.confirmation_timeout)
        
        if confirmation_id in self.pending_confirmations:
            confirmation = self.pending_confirmations[confirmation_id]
            
            if confirmation['status'] == 'pending':
                logger.warning(f"Confirmation timeout for command: {confirmation['command']}")
                
                confirmation['status'] = 'timeout'
                confirmation['timeout_at'] = datetime.now(timezone.utc)
                
                # Remove from pending
                del self.pending_confirmations[confirmation_id]
    
    def _generate_confirmation_id(self) -> str:
        """Generate unique confirmation ID"""
        timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
        return f"conf_{timestamp}"
    
    def _generate_confirmation_message(self, command: Dict[str, Any]) -> str:
        """Generate human-readable confirmation message"""
        command_type = command.get('type', '')
        action = command.get('action', '')
        params = command.get('params', {})
        
        if command_type == 'autopilot':
            if action == 'engage':
                heading = params.get('heading', 'current')
                return f"CONFIRM: Engage autopilot on heading {heading} degrees?"
            
            elif action == 'disengage':
                return "CONFIRM: Disengage autopilot and return to manual control?"
            
            elif action == 'set_heading':
                heading = params.get('heading', 0)
                return f"CONFIRM: Set autopilot heading to {heading} degrees?"
        
        elif command_type == 'follow_vessel':
            if action == 'engage':
                target = params.get('target', 'unknown')
                distance = params.get('distance', 0.5)
                return f"CONFIRM: Follow vessel {target} at {distance} nautical miles?"
        
        elif command_type == 'navigation':
            if action == 'mob':
                return "CONFIRM: Mark man overboard position and initiate search pattern?"
        
        elif command_type == 'emergency_command':
            emergency_type = params.get('type', 'unknown')
            return f"CONFIRM: Execute emergency procedure: {emergency_type}?"
        
        # Generic confirmation message
        return f"CONFIRM: Execute {command_type} {action}?"
    
    def _has_safety_implications(self, command: Dict[str, Any]) -> bool:
        """Check if command has safety implications"""
        command_type = command.get('type', '')
        action = command.get('action', '')
        params = command.get('params', {})
        
        # Large heading changes
        if command_type == 'autopilot' and action == 'set_heading':
            heading_change = params.get('heading_change', 0)
            if heading_change > 30:  # Large heading change
                return True
        
        # High-speed maneuvers
        if command_type == 'autopilot' and action == 'adjust_heading':
            degrees = params.get('degrees', 0)
            if degrees > 20:  # Large adjustment
                return True
        
        # Close following distances
        if command_type == 'follow_vessel' and action == 'set_distance':
            distance = params.get('distance', 1.0)
            if distance < 0.3:  # Very close following
                return True
        
        return False
    
    def get_pending_confirmations(self) -> Dict[str, Any]:
        """Get list of pending confirmations"""
        pending = {}
        
        for conf_id, conf_data in self.pending_confirmations.items():
            if conf_data['status'] == 'pending':
                pending[conf_id] = {
                    'command': conf_data['command'],
                    'requested_at': conf_data['requested_at'].isoformat(),
                    'timeout_remaining': self._calculate_timeout_remaining(conf_data)
                }
        
        return pending
    
    def _calculate_timeout_remaining(self, confirmation: Dict[str, Any]) -> float:
        """Calculate remaining timeout for confirmation"""
        requested_at = confirmation['requested_at']
        elapsed = (datetime.now(timezone.utc) - requested_at).total_seconds()
        remaining = max(0, self.confirmation_timeout - elapsed)
        return remaining
    
    def cancel_all_pending(self) -> int:
        """Cancel all pending confirmations"""
        count = 0
        
        for conf_id in list(self.pending_confirmations.keys()):
            if self.pending_confirmations[conf_id]['status'] == 'pending':
                self.pending_confirmations[conf_id]['status'] = 'cancelled'
                del self.pending_confirmations[conf_id]
                count += 1
        
        logger.info(f"Cancelled {count} pending confirmations")
        return count
    
    def get_status(self) -> Dict[str, Any]:
        """Get confirmation protocol status"""
        return {
            'pending_confirmations': len([c for c in self.pending_confirmations.values() 
                                        if c['status'] == 'pending']),
            'confirmation_timeout': self.confirmation_timeout,
            'total_confirmations': len(self.pending_confirmations),
            'confirmation_phrases': self.confirmation_phrases,
            'cancellation_phrases': self.cancellation_phrases
        }