"""
Confirmation Protocols for Voice Excellence System

This module implements comprehensive safety confirmation protocols ensuring
critical commands require appropriate verification before execution in
marine and industrial environments.

Author: Claude
Date: 2025-08-24
"""

import json
import time
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import sqlite3
import threading
from pathlib import Path
import uuid

class ConfirmationType(Enum):
    """Types of confirmation protocols"""
    VERBAL_CONFIRMATION = "verbal_confirmation"
    VISUAL_CONFIRMATION = "visual_confirmation"
    BIOMETRIC_CONFIRMATION = "biometric_confirmation"
    WITNESS_CONFIRMATION = "witness_confirmation"
    DIGITAL_SIGNATURE = "digital_signature"
    TWO_FACTOR_AUTH = "two_factor_auth"
    SUPERVISOR_APPROVAL = "supervisor_approval"
    EMERGENCY_OVERRIDE = "emergency_override"
    SAFETY_CHECKLIST = "safety_checklist"
    TIME_DELAY = "time_delay"

class ConfirmationLevel(Enum):
    """Confirmation security levels"""
    STANDARD = 1      # Basic verbal confirmation
    ENHANCED = 2      # Multiple confirmation types
    CRITICAL = 3      # Maximum security with witnesses
    EMERGENCY = 4     # Emergency override protocols

class CommandRiskLevel(Enum):
    """Risk levels for commands"""
    LOW = "low"           # No confirmation needed
    MEDIUM = "medium"     # Basic confirmation
    HIGH = "high"         # Enhanced confirmation
    CRITICAL = "critical" # Maximum confirmation required

@dataclass
class ConfirmationRequest:
    """Confirmation request details"""
    request_id: str
    command: str
    user_id: str
    risk_level: CommandRiskLevel
    required_confirmations: List[ConfirmationType]
    confirmation_level: ConfirmationLevel
    timeout_seconds: int
    created_at: datetime
    expires_at: datetime
    context: Dict[str, Any]
    safety_checks: List[str]
    witnesses_required: int
    emergency_contacts: List[str]

@dataclass
class ConfirmationResponse:
    """Confirmation response from user"""
    request_id: str
    confirmation_type: ConfirmationType
    user_id: str
    confirmed: bool
    response_data: Dict[str, Any]
    timestamp: datetime
    biometric_hash: Optional[str] = None
    witness_id: Optional[str] = None
    signature_data: Optional[str] = None

@dataclass
class SafetyChecklist:
    """Safety checklist for critical operations"""
    checklist_id: str
    command: str
    items: List[Dict[str, str]]  # {"item": "description", "required": bool}
    completed_items: List[str]
    completion_percentage: float
    verified_by: Optional[str] = None
    verification_timestamp: Optional[datetime] = None

class ConfirmationProtocols:
    """
    Comprehensive safety confirmation system ensuring critical commands
    require appropriate verification before execution.
    """
    
    def __init__(self, db_path: str = "confirmation_protocols.db"):
        """
        Initialize confirmation protocols system.
        
        Args:
            db_path: Path to the confirmation database
        """
        self.db_path = db_path
        self.active_requests: Dict[str, ConfirmationRequest] = {}
        self.responses: Dict[str, List[ConfirmationResponse]] = {}
        self.safety_checklists: Dict[str, SafetyChecklist] = {}
        self.command_risk_mappings: Dict[str, CommandRiskLevel] = {}
        self.confirmation_handlers: Dict[ConfirmationType, Callable] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Load default risk mappings
        self._load_default_risk_mappings()
        
        # Initialize confirmation handlers
        self._init_confirmation_handlers()
        
        # Start cleanup service
        self._start_cleanup_service()
        
        self.logger.info("Confirmation Protocols system initialized")
    
    def _init_database(self):
        """Initialize the confirmation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Confirmation requests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confirmation_requests (
                request_id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                user_id TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                required_confirmations TEXT NOT NULL,
                confirmation_level INTEGER NOT NULL,
                timeout_seconds INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                context TEXT,
                safety_checks TEXT,
                witnesses_required INTEGER DEFAULT 0,
                emergency_contacts TEXT,
                status TEXT DEFAULT 'pending',
                completed_at TEXT
            )
        """)
        
        # Confirmation responses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS confirmation_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id TEXT NOT NULL,
                confirmation_type TEXT NOT NULL,
                user_id TEXT NOT NULL,
                confirmed BOOLEAN NOT NULL,
                response_data TEXT,
                timestamp TEXT NOT NULL,
                biometric_hash TEXT,
                witness_id TEXT,
                signature_data TEXT,
                FOREIGN KEY (request_id) REFERENCES confirmation_requests (request_id)
            )
        """)
        
        # Safety checklists table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_checklists (
                checklist_id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                items TEXT NOT NULL,
                completed_items TEXT,
                completion_percentage REAL DEFAULT 0.0,
                verified_by TEXT,
                verification_timestamp TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Command risk mappings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS command_risk_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                command_pattern TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                confirmation_types TEXT NOT NULL,
                witnesses_required INTEGER DEFAULT 0,
                timeout_seconds INTEGER DEFAULT 300,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_default_risk_mappings(self):
        """Load default command risk mappings"""
        default_mappings = {
            # Emergency commands - Critical risk
            "emergency.*": CommandRiskLevel.CRITICAL,
            "fire.*": CommandRiskLevel.CRITICAL,
            "evacuat.*": CommandRiskLevel.CRITICAL,
            "mayday": CommandRiskLevel.CRITICAL,
            "abandon.*": CommandRiskLevel.CRITICAL,
            
            # System control commands - High risk
            "stop.*all.*": CommandRiskLevel.CRITICAL,
            "shutdown.*system": CommandRiskLevel.HIGH,
            "emergency.*stop": CommandRiskLevel.CRITICAL,
            "full.*stop": CommandRiskLevel.HIGH,
            "all.*stop": CommandRiskLevel.CRITICAL,
            
            # Engine/Navigation commands - High risk
            "engine.*stop": CommandRiskLevel.HIGH,
            "engine.*emergency": CommandRiskLevel.CRITICAL,
            "rudder.*hard": CommandRiskLevel.HIGH,
            "helm.*hard": CommandRiskLevel.HIGH,
            "course.*emergency": CommandRiskLevel.HIGH,
            
            # Industrial equipment - High/Critical risk
            "crane.*stop": CommandRiskLevel.HIGH,
            "conveyor.*stop": CommandRiskLevel.HIGH,
            "machinery.*shutdown": CommandRiskLevel.HIGH,
            "production.*halt": CommandRiskLevel.HIGH,
            "safety.*system.*disable": CommandRiskLevel.CRITICAL,
            
            # Security/Access commands - High risk
            "security.*disable": CommandRiskLevel.CRITICAL,
            "access.*override": CommandRiskLevel.HIGH,
            "lockout.*disable": CommandRiskLevel.CRITICAL,
            "safety.*bypass": CommandRiskLevel.CRITICAL,
            
            # Communications - Medium risk
            "radio.*emergency": CommandRiskLevel.HIGH,
            "distress.*call": CommandRiskLevel.CRITICAL,
            "pan.*pan": CommandRiskLevel.HIGH,
            
            # Standard operations - Medium/Low risk
            "status.*": CommandRiskLevel.LOW,
            "report.*": CommandRiskLevel.LOW,
            "check.*": CommandRiskLevel.LOW,
            "lights.*": CommandRiskLevel.MEDIUM,
            "navigation.*lights": CommandRiskLevel.MEDIUM,
            
            # Default for unmatched commands
            ".*": CommandRiskLevel.MEDIUM
        }
        
        for pattern, risk_level in default_mappings.items():
            self.command_risk_mappings[pattern] = risk_level
    
    def _init_confirmation_handlers(self):
        """Initialize confirmation type handlers"""
        self.confirmation_handlers = {
            ConfirmationType.VERBAL_CONFIRMATION: self._handle_verbal_confirmation,
            ConfirmationType.VISUAL_CONFIRMATION: self._handle_visual_confirmation,
            ConfirmationType.BIOMETRIC_CONFIRMATION: self._handle_biometric_confirmation,
            ConfirmationType.WITNESS_CONFIRMATION: self._handle_witness_confirmation,
            ConfirmationType.DIGITAL_SIGNATURE: self._handle_digital_signature,
            ConfirmationType.TWO_FACTOR_AUTH: self._handle_two_factor_auth,
            ConfirmationType.SUPERVISOR_APPROVAL: self._handle_supervisor_approval,
            ConfirmationType.EMERGENCY_OVERRIDE: self._handle_emergency_override,
            ConfirmationType.SAFETY_CHECKLIST: self._handle_safety_checklist,
            ConfirmationType.TIME_DELAY: self._handle_time_delay
        }
    
    def _start_cleanup_service(self):
        """Start background service to clean up expired requests"""
        def cleanup_loop():
            while True:
                try:
                    self._cleanup_expired_requests()
                    time.sleep(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Cleanup service error: {e}")
                    time.sleep(60)
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired_requests(self):
        """Clean up expired confirmation requests"""
        current_time = datetime.now()
        expired_requests = []
        
        with self.lock:
            for request_id, request in self.active_requests.items():
                if current_time > request.expires_at:
                    expired_requests.append(request_id)
            
            for request_id in expired_requests:
                del self.active_requests[request_id]
                if request_id in self.responses:
                    del self.responses[request_id]
                self.logger.warning(f"Confirmation request {request_id} expired")
    
    async def request_confirmation(
        self, 
        command: str, 
        user_id: str, 
        context: Dict[str, Any] = None
    ) -> ConfirmationRequest:
        """
        Request confirmation for a voice command.
        
        Args:
            command: The voice command requiring confirmation
            user_id: ID of the user issuing the command
            context: Additional context information
            
        Returns:
            ConfirmationRequest object
        """
        # Determine risk level and required confirmations
        risk_level = self._assess_command_risk(command)
        required_confirmations = self._get_required_confirmations(command, risk_level, context)
        confirmation_level = self._get_confirmation_level(risk_level, context)
        
        # Calculate timeout
        timeout_seconds = self._calculate_timeout(risk_level, confirmation_level)
        
        # Create request
        request_id = str(uuid.uuid4())
        current_time = datetime.now()
        expires_at = current_time + timedelta(seconds=timeout_seconds)
        
        # Determine witnesses and emergency contacts
        witnesses_required = self._get_witnesses_required(risk_level, context)
        emergency_contacts = self._get_emergency_contacts(risk_level, context)
        
        # Get required safety checks
        safety_checks = self._get_safety_checks(command, risk_level, context)
        
        request = ConfirmationRequest(
            request_id=request_id,
            command=command,
            user_id=user_id,
            risk_level=risk_level,
            required_confirmations=required_confirmations,
            confirmation_level=confirmation_level,
            timeout_seconds=timeout_seconds,
            created_at=current_time,
            expires_at=expires_at,
            context=context or {},
            safety_checks=safety_checks,
            witnesses_required=witnesses_required,
            emergency_contacts=emergency_contacts
        )
        
        # Store request
        with self.lock:
            self.active_requests[request_id] = request
            self.responses[request_id] = []
        
        # Save to database
        self._save_request_to_db(request)
        
        # Create safety checklist if needed
        if ConfirmationType.SAFETY_CHECKLIST in required_confirmations:
            await self._create_safety_checklist(request)
        
        self.logger.info(f"Confirmation requested for '{command}' (risk: {risk_level.value})")
        return request
    
    def _assess_command_risk(self, command: str) -> CommandRiskLevel:
        """Assess risk level of a command"""
        import re
        
        command_lower = command.lower().strip()
        
        # Check against risk patterns (highest priority first)
        patterns_by_priority = [
            (CommandRiskLevel.CRITICAL, ["emergency.*", "fire.*", "evacuat.*", "mayday", "abandon.*", 
                                        "stop.*all.*", "emergency.*stop", "all.*stop", "safety.*system.*disable",
                                        "security.*disable", "lockout.*disable", "safety.*bypass", "distress.*call"]),
            (CommandRiskLevel.HIGH, ["shutdown.*system", "full.*stop", "engine.*stop", "engine.*emergency",
                                   "rudder.*hard", "helm.*hard", "course.*emergency", "crane.*stop",
                                   "conveyor.*stop", "machinery.*shutdown", "production.*halt",
                                   "access.*override", "radio.*emergency", "pan.*pan"]),
            (CommandRiskLevel.MEDIUM, ["lights.*", "navigation.*lights", "speed.*", "course.*", "turn.*"]),
            (CommandRiskLevel.LOW, ["status.*", "report.*", "check.*", "weather.*", "time.*"])
        ]
        
        for risk_level, patterns in patterns_by_priority:
            for pattern in patterns:
                if re.search(pattern, command_lower):
                    return risk_level
        
        # Default to medium risk
        return CommandRiskLevel.MEDIUM
    
    def _get_required_confirmations(
        self, 
        command: str, 
        risk_level: CommandRiskLevel,
        context: Dict[str, Any]
    ) -> List[ConfirmationType]:
        """Get required confirmation types based on command and risk level"""
        confirmations = [ConfirmationType.VERBAL_CONFIRMATION]  # Always require verbal
        
        if risk_level == CommandRiskLevel.CRITICAL:
            confirmations.extend([
                ConfirmationType.WITNESS_CONFIRMATION,
                ConfirmationType.SAFETY_CHECKLIST,
                ConfirmationType.BIOMETRIC_CONFIRMATION
            ])
            
            # Add digital signature for shutdown commands
            if "shutdown" in command.lower() or "stop" in command.lower():
                confirmations.append(ConfirmationType.DIGITAL_SIGNATURE)
        
        elif risk_level == CommandRiskLevel.HIGH:
            confirmations.extend([
                ConfirmationType.VISUAL_CONFIRMATION,
                ConfirmationType.TWO_FACTOR_AUTH
            ])
            
            # Add witness for emergency situations
            if context and context.get("emergency_context"):
                confirmations.append(ConfirmationType.WITNESS_CONFIRMATION)
        
        elif risk_level == CommandRiskLevel.MEDIUM:
            confirmations.append(ConfirmationType.VISUAL_CONFIRMATION)
        
        # Add context-specific confirmations
        if context:
            if context.get("shift_supervisor_present"):
                confirmations.append(ConfirmationType.SUPERVISOR_APPROVAL)
            
            if context.get("training_mode"):
                confirmations.append(ConfirmationType.TIME_DELAY)
        
        return list(set(confirmations))  # Remove duplicates
    
    def _get_confirmation_level(self, risk_level: CommandRiskLevel, context: Dict[str, Any]) -> ConfirmationLevel:
        """Get confirmation level based on risk and context"""
        if risk_level == CommandRiskLevel.CRITICAL:
            return ConfirmationLevel.CRITICAL
        elif risk_level == CommandRiskLevel.HIGH:
            return ConfirmationLevel.ENHANCED
        elif context and context.get("emergency_context"):
            return ConfirmationLevel.EMERGENCY
        else:
            return ConfirmationLevel.STANDARD
    
    def _calculate_timeout(self, risk_level: CommandRiskLevel, confirmation_level: ConfirmationLevel) -> int:
        """Calculate timeout for confirmation request"""
        base_timeouts = {
            CommandRiskLevel.LOW: 60,
            CommandRiskLevel.MEDIUM: 120,
            CommandRiskLevel.HIGH: 300,
            CommandRiskLevel.CRITICAL: 600
        }
        
        level_multipliers = {
            ConfirmationLevel.STANDARD: 1.0,
            ConfirmationLevel.ENHANCED: 1.5,
            ConfirmationLevel.CRITICAL: 2.0,
            ConfirmationLevel.EMERGENCY: 0.5  # Shorter for emergencies
        }
        
        base_timeout = base_timeouts[risk_level]
        multiplier = level_multipliers[confirmation_level]
        
        return int(base_timeout * multiplier)
    
    def _get_witnesses_required(self, risk_level: CommandRiskLevel, context: Dict[str, Any]) -> int:
        """Get number of witnesses required"""
        if risk_level == CommandRiskLevel.CRITICAL:
            return 2
        elif risk_level == CommandRiskLevel.HIGH:
            return 1
        else:
            return 0
    
    def _get_emergency_contacts(self, risk_level: CommandRiskLevel, context: Dict[str, Any]) -> List[str]:
        """Get emergency contacts to notify"""
        contacts = []
        
        if risk_level == CommandRiskLevel.CRITICAL:
            contacts.extend(["bridge_officer", "chief_engineer", "safety_officer"])
        elif risk_level == CommandRiskLevel.HIGH:
            contacts.extend(["duty_officer", "shift_supervisor"])
        
        return contacts
    
    def _get_safety_checks(self, command: str, risk_level: CommandRiskLevel, context: Dict[str, Any]) -> List[str]:
        """Get required safety checks"""
        checks = []
        command_lower = command.lower()
        
        if "stop" in command_lower or "shutdown" in command_lower:
            checks.extend(["personnel_clear", "equipment_safe_state", "backup_systems_ready"])
        
        if "engine" in command_lower:
            checks.extend(["propulsion_safety", "navigation_impact"])
        
        if "emergency" in command_lower:
            checks.extend(["emergency_protocols", "evacuation_ready", "communication_active"])
        
        if risk_level == CommandRiskLevel.CRITICAL:
            checks.extend(["supervisor_informed", "incident_logged"])
        
        return checks
    
    def _save_request_to_db(self, request: ConfirmationRequest):
        """Save confirmation request to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO confirmation_requests 
            (request_id, command, user_id, risk_level, required_confirmations, 
             confirmation_level, timeout_seconds, created_at, expires_at, 
             context, safety_checks, witnesses_required, emergency_contacts)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            request.request_id,
            request.command,
            request.user_id,
            request.risk_level.value,
            json.dumps([c.value for c in request.required_confirmations]),
            request.confirmation_level.value,
            request.timeout_seconds,
            request.created_at.isoformat(),
            request.expires_at.isoformat(),
            json.dumps(request.context),
            json.dumps(request.safety_checks),
            request.witnesses_required,
            json.dumps(request.emergency_contacts)
        ))
        
        conn.commit()
        conn.close()
    
    async def _create_safety_checklist(self, request: ConfirmationRequest):
        """Create safety checklist for critical commands"""
        checklist_items = self._generate_checklist_items(request.command, request.context)
        
        checklist = SafetyChecklist(
            checklist_id=f"checklist_{request.request_id}",
            command=request.command,
            items=checklist_items,
            completed_items=[],
            completion_percentage=0.0
        )
        
        self.safety_checklists[checklist.checklist_id] = checklist
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO safety_checklists 
            (checklist_id, command, items, completed_items, completion_percentage)
            VALUES (?, ?, ?, ?, ?)
        """, (
            checklist.checklist_id,
            checklist.command,
            json.dumps(checklist.items),
            json.dumps(checklist.completed_items),
            checklist.completion_percentage
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Safety checklist created for '{request.command}'")
    
    def _generate_checklist_items(self, command: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate safety checklist items based on command"""
        items = []
        command_lower = command.lower()
        
        if "stop" in command_lower or "shutdown" in command_lower:
            items.extend([
                {"item": "All personnel accounted for and in safe location", "required": "true"},
                {"item": "No personnel in equipment operating areas", "required": "true"},
                {"item": "Emergency stop systems are functional", "required": "true"},
                {"item": "Backup power systems ready", "required": "true"},
                {"item": "Communication systems operational", "required": "true"}
            ])
        
        if "engine" in command_lower:
            items.extend([
                {"item": "Navigation safety confirmed", "required": "true"},
                {"item": "Propulsion backup available", "required": "false"},
                {"item": "Weather conditions suitable", "required": "true"},
                {"item": "Traffic situation assessed", "required": "true"}
            ])
        
        if "emergency" in command_lower:
            items.extend([
                {"item": "Emergency services alerted", "required": "true"},
                {"item": "Evacuation routes clear", "required": "true"},
                {"item": "Emergency equipment accessible", "required": "true"},
                {"item": "Personnel headcount complete", "required": "true"},
                {"item": "Emergency coordinator notified", "required": "true"}
            ])
        
        # Default safety items
        if not items:
            items.extend([
                {"item": "Command authorized by qualified personnel", "required": "true"},
                {"item": "No safety hazards present", "required": "true"},
                {"item": "Equipment status verified", "required": "true"}
            ])
        
        return items
    
    async def provide_confirmation(
        self, 
        request_id: str, 
        confirmation_type: ConfirmationType,
        user_id: str,
        confirmed: bool,
        response_data: Dict[str, Any] = None
    ) -> bool:
        """
        Provide confirmation response for a request.
        
        Args:
            request_id: ID of the confirmation request
            confirmation_type: Type of confirmation being provided
            user_id: ID of the user providing confirmation
            confirmed: Whether the command is confirmed
            response_data: Additional response data
            
        Returns:
            True if confirmation was accepted, False otherwise
        """
        if request_id not in self.active_requests:
            self.logger.warning(f"Confirmation request {request_id} not found or expired")
            return False
        
        request = self.active_requests[request_id]
        
        # Check if this confirmation type is required
        if confirmation_type not in request.required_confirmations:
            self.logger.warning(f"Confirmation type {confirmation_type.value} not required for request {request_id}")
            return False
        
        # Process confirmation through appropriate handler
        handler = self.confirmation_handlers.get(confirmation_type)
        if handler:
            success = await handler(request, user_id, confirmed, response_data or {})
            if not success:
                return False
        
        # Create response
        response = ConfirmationResponse(
            request_id=request_id,
            confirmation_type=confirmation_type,
            user_id=user_id,
            confirmed=confirmed,
            response_data=response_data or {},
            timestamp=datetime.now()
        )
        
        # Add response
        with self.lock:
            self.responses[request_id].append(response)
        
        # Save to database
        self._save_response_to_db(response)
        
        self.logger.info(f"Confirmation {confirmation_type.value} provided for request {request_id}")
        return True
    
    def _save_response_to_db(self, response: ConfirmationResponse):
        """Save confirmation response to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO confirmation_responses 
            (request_id, confirmation_type, user_id, confirmed, response_data, 
             timestamp, biometric_hash, witness_id, signature_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            response.request_id,
            response.confirmation_type.value,
            response.user_id,
            response.confirmed,
            json.dumps(response.response_data),
            response.timestamp.isoformat(),
            response.biometric_hash,
            response.witness_id,
            response.signature_data
        ))
        
        conn.commit()
        conn.close()
    
    async def check_confirmation_status(self, request_id: str) -> Dict[str, Any]:
        """
        Check the status of a confirmation request.
        
        Args:
            request_id: ID of the confirmation request
            
        Returns:
            Dictionary with confirmation status
        """
        if request_id not in self.active_requests:
            return {"status": "not_found", "message": "Request not found or expired"}
        
        request = self.active_requests[request_id]
        responses = self.responses.get(request_id, [])
        
        # Check if expired
        if datetime.now() > request.expires_at:
            with self.lock:
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
                if request_id in self.responses:
                    del self.responses[request_id]
            return {"status": "expired", "message": "Confirmation request expired"}
        
        # Check completion status
        required_types = set(request.required_confirmations)
        provided_types = set(r.confirmation_type for r in responses if r.confirmed)
        
        missing_types = required_types - provided_types
        
        if not missing_types:
            return {
                "status": "completed",
                "message": "All confirmations received",
                "command_authorized": True,
                "responses": len(responses)
            }
        else:
            return {
                "status": "pending",
                "message": f"Waiting for confirmations: {[t.value for t in missing_types]}",
                "command_authorized": False,
                "missing_confirmations": [t.value for t in missing_types],
                "responses_received": len(responses),
                "time_remaining": int((request.expires_at - datetime.now()).total_seconds())
            }
    
    # Confirmation handler methods
    async def _handle_verbal_confirmation(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle verbal confirmation"""
        if confirmed:
            # In real implementation, would verify voice pattern/biometrics
            self.logger.info(f"Verbal confirmation provided by {user_id}")
            return True
        return False
    
    async def _handle_visual_confirmation(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle visual confirmation (screen display, LED indicators)"""
        if confirmed and data.get("visual_acknowledged"):
            self.logger.info(f"Visual confirmation acknowledged by {user_id}")
            return True
        return False
    
    async def _handle_biometric_confirmation(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle biometric confirmation (fingerprint, voice print, etc.)"""
        if confirmed:
            # In real implementation, would verify against stored biometrics
            biometric_hash = hashlib.sha256(f"{user_id}_{time.time()}".encode()).hexdigest()
            self.logger.info(f"Biometric confirmation verified for {user_id}")
            return True
        return False
    
    async def _handle_witness_confirmation(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle witness confirmation"""
        if confirmed and data.get("witness_id"):
            witness_id = data["witness_id"]
            self.logger.info(f"Witness confirmation provided by {witness_id} for user {user_id}")
            return True
        return False
    
    async def _handle_digital_signature(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle digital signature confirmation"""
        if confirmed and data.get("signature_data"):
            # In real implementation, would verify digital signature
            self.logger.info(f"Digital signature provided by {user_id}")
            return True
        return False
    
    async def _handle_two_factor_auth(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle two-factor authentication"""
        if confirmed and data.get("auth_code"):
            # In real implementation, would verify 2FA code
            self.logger.info(f"Two-factor authentication verified for {user_id}")
            return True
        return False
    
    async def _handle_supervisor_approval(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle supervisor approval"""
        if confirmed and data.get("supervisor_id"):
            supervisor_id = data["supervisor_id"]
            self.logger.info(f"Supervisor approval provided by {supervisor_id}")
            return True
        return False
    
    async def _handle_emergency_override(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle emergency override"""
        if confirmed and data.get("override_code"):
            # Emergency overrides require special logging
            self.logger.critical(f"EMERGENCY OVERRIDE used by {user_id} for command: {request.command}")
            return True
        return False
    
    async def _handle_safety_checklist(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle safety checklist confirmation"""
        if confirmed:
            checklist_id = f"checklist_{request.request_id}"
            if checklist_id in self.safety_checklists:
                checklist = self.safety_checklists[checklist_id]
                if checklist.completion_percentage >= 100.0:
                    self.logger.info(f"Safety checklist completed by {user_id}")
                    return True
            return False
        return False
    
    async def _handle_time_delay(self, request: ConfirmationRequest, user_id: str, confirmed: bool, data: Dict) -> bool:
        """Handle time delay confirmation"""
        delay_seconds = data.get("delay_seconds", 30)
        self.logger.info(f"Time delay confirmation: waiting {delay_seconds} seconds")
        await asyncio.sleep(delay_seconds)
        return True
    
    def update_checklist_item(self, checklist_id: str, item_index: int, completed: bool, verified_by: str = None) -> bool:
        """Update a safety checklist item"""
        if checklist_id not in self.safety_checklists:
            return False
        
        checklist = self.safety_checklists[checklist_id]
        
        if 0 <= item_index < len(checklist.items):
            item_name = checklist.items[item_index]["item"]
            
            if completed and item_name not in checklist.completed_items:
                checklist.completed_items.append(item_name)
            elif not completed and item_name in checklist.completed_items:
                checklist.completed_items.remove(item_name)
            
            # Calculate completion percentage
            required_items = [item for item in checklist.items if item.get("required") == "true"]
            completed_required = [item for item in checklist.completed_items 
                                if any(ci["item"] == item and ci.get("required") == "true" for ci in checklist.items)]
            
            if required_items:
                checklist.completion_percentage = (len(completed_required) / len(required_items)) * 100
            else:
                checklist.completion_percentage = 100.0
            
            if verified_by:
                checklist.verified_by = verified_by
                checklist.verification_timestamp = datetime.now()
            
            self.logger.info(f"Checklist item updated: {item_name} (completed: {completed})")
            return True
        
        return False
    
    def get_active_requests(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get active confirmation requests"""
        requests = []
        
        with self.lock:
            for request in self.active_requests.values():
                if user_id is None or request.user_id == user_id:
                    request_dict = asdict(request)
                    request_dict["context_type"] = request_dict["context_type"] if isinstance(request_dict.get("context_type"), str) else "unknown"
                    request_dict["risk_level"] = request.risk_level.value
                    request_dict["required_confirmations"] = [c.value for c in request.required_confirmations]
                    request_dict["confirmation_level"] = request.confirmation_level.value
                    request_dict["created_at"] = request.created_at.isoformat()
                    request_dict["expires_at"] = request.expires_at.isoformat()
                    requests.append(request_dict)
        
        return requests
    
    def get_confirmation_statistics(self) -> Dict[str, Any]:
        """Get confirmation system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total requests
        cursor.execute("SELECT COUNT(*) FROM confirmation_requests")
        total_requests = cursor.fetchone()[0]
        
        # Requests by risk level
        cursor.execute("SELECT risk_level, COUNT(*) FROM confirmation_requests GROUP BY risk_level")
        risk_distribution = dict(cursor.fetchall())
        
        # Completion rate
        cursor.execute("SELECT COUNT(*) FROM confirmation_requests WHERE status = 'completed'")
        completed_requests = cursor.fetchone()[0]
        completion_rate = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Average response time
        cursor.execute("""
            SELECT AVG(
                CASE 
                    WHEN completed_at IS NOT NULL 
                    THEN (julianday(completed_at) - julianday(created_at)) * 86400
                    ELSE NULL 
                END
            ) 
            FROM confirmation_requests 
            WHERE completed_at IS NOT NULL
        """)
        avg_response_time = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_requests": total_requests,
            "active_requests": len(self.active_requests),
            "risk_distribution": risk_distribution,
            "completion_rate": round(completion_rate, 2),
            "average_response_time_seconds": round(avg_response_time, 2),
            "active_checklists": len(self.safety_checklists)
        }


# Example usage and testing
async def main():
    """Example usage of confirmation protocols"""
    protocols = ConfirmationProtocols()
    
    # Test different risk level commands
    test_commands = [
        ("check engine status", "user1", {}),
        ("turn left 15 degrees", "user1", {}),
        ("emergency stop all systems", "user1", {"emergency_context": True}),
        ("shutdown main engine", "user1", {"shift_supervisor_present": True}),
        ("fire alarm activate", "user1", {"emergency_context": True})
    ]
    
    for command, user_id, context in test_commands:
        print(f"\n=== Testing command: '{command}' ===")
        
        # Request confirmation
        request = await protocols.request_confirmation(command, user_id, context)
        print(f"Risk level: {request.risk_level.value}")
        print(f"Required confirmations: {[c.value for c in request.required_confirmations]}")
        print(f"Timeout: {request.timeout_seconds} seconds")
        
        # Simulate providing confirmations
        for confirmation_type in request.required_confirmations[:1]:  # Just provide first confirmation for demo
            await protocols.provide_confirmation(
                request.request_id,
                confirmation_type,
                user_id,
                True,
                {"demo": True}
            )
        
        # Check status
        status = await protocols.check_confirmation_status(request.request_id)
        print(f"Status: {status}")
    
    # Show statistics
    stats = protocols.get_confirmation_statistics()
    print(f"\nConfirmation statistics: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())