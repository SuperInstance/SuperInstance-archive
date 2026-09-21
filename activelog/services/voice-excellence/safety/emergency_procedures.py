"""
Emergency Procedures and Safety Commands for Voice Excellence System

This module implements comprehensive emergency response procedures and
safety command processing for marine and industrial environments.

Author: Claude
Date: 2025-08-24
"""

import json
import time
import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable, Set
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import sqlite3
import threading
from pathlib import Path
import re

class EmergencyType(Enum):
    """Types of emergency situations"""
    FIRE = "fire"
    MEDICAL = "medical"
    COLLISION = "collision"
    FLOODING = "flooding"
    MACHINERY_FAILURE = "machinery_failure"
    POWER_FAILURE = "power_failure"
    TOXIC_GAS = "toxic_gas"
    EXPLOSION = "explosion"
    ABANDON_SHIP = "abandon_ship"
    MAN_OVERBOARD = "man_overboard"
    SEVERE_WEATHER = "severe_weather"
    SECURITY_BREACH = "security_breach"
    ENVIRONMENTAL = "environmental"
    GENERAL_ALARM = "general_alarm"

class EmergencyPriority(Enum):
    """Emergency priority levels"""
    IMMEDIATE = 1    # Life-threatening, requires instant response
    URGENT = 2       # Serious threat, requires rapid response
    HIGH = 3         # Significant risk, requires prompt response
    ELEVATED = 4     # Potential risk, requires monitoring

class SafetyCommandType(Enum):
    """Types of safety commands"""
    EMERGENCY_STOP = "emergency_stop"
    EVACUATION = "evacuation"
    LOCKDOWN = "lockdown"
    ISOLATION = "isolation"
    ALERT = "alert"
    COMMUNICATION = "communication"
    SYSTEM_SHUTDOWN = "system_shutdown"
    OVERRIDE = "override"
    STATUS_CHECK = "status_check"
    RESCUE_OPERATION = "rescue_operation"

@dataclass
class EmergencyProcedure:
    """Emergency procedure definition"""
    procedure_id: str
    emergency_type: EmergencyType
    priority: EmergencyPriority
    trigger_keywords: List[str]
    immediate_actions: List[str]
    sequential_steps: List[Dict[str, Any]]
    required_personnel: List[str]
    equipment_needed: List[str]
    communication_plan: List[str]
    safety_precautions: List[str]
    duration_estimate_minutes: int
    confirmation_required: bool
    witness_required: bool

@dataclass
class EmergencyEvent:
    """Active emergency event"""
    event_id: str
    emergency_type: EmergencyType
    priority: EmergencyPriority
    location: str
    initiated_by: str
    initiated_at: datetime
    description: str
    current_status: str
    actions_taken: List[str]
    personnel_assigned: List[str]
    resources_deployed: List[str]
    estimated_resolution: Optional[datetime]
    communications_log: List[Dict[str, str]]

@dataclass
class SafetyCommand:
    """Safety command execution record"""
    command_id: str
    command_type: SafetyCommandType
    original_voice_command: str
    interpreted_command: str
    executed_by: str
    executed_at: datetime
    target_systems: List[str]
    confirmation_received: bool
    execution_successful: bool
    impact_assessment: str
    rollback_available: bool

class EmergencyProcedures:
    """
    Comprehensive emergency response system for marine and industrial
    voice command processing with safety protocols.
    """
    
    def __init__(self, db_path: str = "emergency_procedures.db"):
        """
        Initialize emergency procedures system.
        
        Args:
            db_path: Path to the emergency procedures database
        """
        self.db_path = db_path
        self.procedures: Dict[str, EmergencyProcedure] = {}
        self.active_emergencies: Dict[str, EmergencyEvent] = {}
        self.executed_commands: Dict[str, SafetyCommand] = {}
        self.emergency_contacts: Dict[str, List[str]] = {}
        self.system_status: Dict[str, Any] = {"operational": True}
        self.command_handlers: Dict[SafetyCommandType, Callable] = {}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Load default procedures
        self._load_default_procedures()
        
        # Initialize command handlers
        self._init_command_handlers()
        
        # Load emergency contacts
        self._load_emergency_contacts()
        
        self.logger.info("Emergency Procedures system initialized")
    
    def _init_database(self):
        """Initialize the emergency procedures database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Emergency procedures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_procedures (
                procedure_id TEXT PRIMARY KEY,
                emergency_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                trigger_keywords TEXT NOT NULL,
                immediate_actions TEXT NOT NULL,
                sequential_steps TEXT NOT NULL,
                required_personnel TEXT NOT NULL,
                equipment_needed TEXT NOT NULL,
                communication_plan TEXT NOT NULL,
                safety_precautions TEXT NOT NULL,
                duration_estimate_minutes INTEGER NOT NULL,
                confirmation_required BOOLEAN NOT NULL DEFAULT TRUE,
                witness_required BOOLEAN NOT NULL DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Emergency events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS emergency_events (
                event_id TEXT PRIMARY KEY,
                emergency_type TEXT NOT NULL,
                priority INTEGER NOT NULL,
                location TEXT NOT NULL,
                initiated_by TEXT NOT NULL,
                initiated_at TEXT NOT NULL,
                description TEXT NOT NULL,
                current_status TEXT NOT NULL,
                actions_taken TEXT,
                personnel_assigned TEXT,
                resources_deployed TEXT,
                estimated_resolution TEXT,
                communications_log TEXT,
                resolved_at TEXT,
                resolution_summary TEXT
            )
        """)
        
        # Safety commands table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS safety_commands (
                command_id TEXT PRIMARY KEY,
                command_type TEXT NOT NULL,
                original_voice_command TEXT NOT NULL,
                interpreted_command TEXT NOT NULL,
                executed_by TEXT NOT NULL,
                executed_at TEXT NOT NULL,
                target_systems TEXT NOT NULL,
                confirmation_received BOOLEAN NOT NULL DEFAULT FALSE,
                execution_successful BOOLEAN NOT NULL DEFAULT FALSE,
                impact_assessment TEXT,
                rollback_available BOOLEAN NOT NULL DEFAULT FALSE,
                emergency_event_id TEXT,
                FOREIGN KEY (emergency_event_id) REFERENCES emergency_events (event_id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_default_procedures(self):
        """Load default emergency procedures"""
        default_procedures = [
            EmergencyProcedure(
                procedure_id="fire_emergency",
                emergency_type=EmergencyType.FIRE,
                priority=EmergencyPriority.IMMEDIATE,
                trigger_keywords=["fire", "smoke", "flames", "burning", "fire alarm", "smoke detected"],
                immediate_actions=[
                    "Sound general alarm",
                    "Announce 'Fire, Fire, Fire' over PA system",
                    "Activate fire suppression systems",
                    "Alert emergency services",
                    "Initiate muster procedures"
                ],
                sequential_steps=[
                    {"step": 1, "action": "Identify fire location and type", "duration": 2, "responsible": "watch_officer"},
                    {"step": 2, "action": "Deploy appropriate fire fighting equipment", "duration": 5, "responsible": "fire_team"},
                    {"step": 3, "action": "Establish boundary cooling", "duration": 10, "responsible": "fire_team"},
                    {"step": 4, "action": "Ventilation control", "duration": 5, "responsible": "engineering"},
                    {"step": 5, "action": "Evacuation of non-essential personnel", "duration": 10, "responsible": "safety_officer"}
                ],
                required_personnel=["fire_team_leader", "safety_officer", "watch_officer", "engineering_officer"],
                equipment_needed=["fire_hoses", "foam_equipment", "breathing_apparatus", "fire_axes", "thermal_imaging"],
                communication_plan=["bridge", "engine_room", "coast_guard", "company_office"],
                safety_precautions=["ensure_escape_routes", "boundary_cooling", "breathing_protection", "electrical_isolation"],
                duration_estimate_minutes=30,
                confirmation_required=True,
                witness_required=True
            ),
            EmergencyProcedure(
                procedure_id="man_overboard",
                emergency_type=EmergencyType.MAN_OVERBOARD,
                priority=EmergencyPriority.IMMEDIATE,
                trigger_keywords=["man overboard", "person overboard", "overboard", "fallen overboard"],
                immediate_actions=[
                    "Sound 6 short blasts on whistle",
                    "Throw lifebuoy with marker light",
                    "Post continuous watch on person",
                    "Mark GPS position",
                    "Alert all hands"
                ],
                sequential_steps=[
                    {"step": 1, "action": "Execute Williamson turn or equivalent", "duration": 3, "responsible": "officer_of_watch"},
                    {"step": 2, "action": "Launch rescue boat", "duration": 8, "responsible": "boat_crew"},
                    {"step": 3, "action": "Maintain visual contact", "duration": 0, "responsible": "lookout"},
                    {"step": 4, "action": "Prepare recovery equipment", "duration": 5, "responsible": "deck_crew"},
                    {"step": 5, "action": "Medical team standby", "duration": 2, "responsible": "medical_officer"}
                ],
                required_personnel=["officer_of_watch", "boat_crew", "lookout", "medical_officer"],
                equipment_needed=["rescue_boat", "lifebuoys", "searchlight", "recovery_equipment"],
                communication_plan=["coast_guard", "nearby_vessels", "company"],
                safety_precautions=["maintain_visual_contact", "weather_assessment", "crew_safety"],
                duration_estimate_minutes=45,
                confirmation_required=True,
                witness_required=True
            ),
            EmergencyProcedure(
                procedure_id="machinery_failure",
                emergency_type=EmergencyType.MACHINERY_FAILURE,
                priority=EmergencyPriority.URGENT,
                trigger_keywords=["machinery failure", "engine failure", "propulsion failure", "steering failure"],
                immediate_actions=[
                    "Stop affected machinery",
                    "Isolate systems if safe",
                    "Alert bridge and engine room",
                    "Assess immediate danger",
                    "Prepare backup systems"
                ],
                sequential_steps=[
                    {"step": 1, "action": "Damage assessment", "duration": 10, "responsible": "chief_engineer"},
                    {"step": 2, "action": "Isolate affected systems", "duration": 15, "responsible": "engineering"},
                    {"step": 3, "action": "Activate backup systems", "duration": 20, "responsible": "engineering"},
                    {"step": 4, "action": "Test alternative operations", "duration": 30, "responsible": "engineering"},
                    {"step": 5, "action": "Report to authorities if required", "duration": 10, "responsible": "master"}
                ],
                required_personnel=["chief_engineer", "engineering_watch", "master"],
                equipment_needed=["tools", "spare_parts", "testing_equipment"],
                communication_plan=["bridge", "company", "port_authority"],
                safety_precautions=["lockout_tagout", "ventilation", "fire_prevention"],
                duration_estimate_minutes=90,
                confirmation_required=True,
                witness_required=False
            ),
            EmergencyProcedure(
                procedure_id="toxic_gas",
                emergency_type=EmergencyType.TOXIC_GAS,
                priority=EmergencyPriority.IMMEDIATE,
                trigger_keywords=["gas alarm", "toxic gas", "gas leak", "H2S", "CO", "chemical leak"],
                immediate_actions=[
                    "Sound gas alarm",
                    "Don breathing apparatus",
                    "Evacuate affected area",
                    "Isolate ventilation",
                    "Alert all personnel"
                ],
                sequential_steps=[
                    {"step": 1, "action": "Identify gas type and source", "duration": 5, "responsible": "safety_officer"},
                    {"step": 2, "action": "Establish safety perimeter", "duration": 5, "responsible": "safety_officer"},
                    {"step": 3, "action": "Isolate source if possible", "duration": 15, "responsible": "engineering"},
                    {"step": 4, "action": "Ventilate area when safe", "duration": 30, "responsible": "engineering"},
                    {"step": 5, "action": "Monitor atmosphere", "duration": 0, "responsible": "safety_officer"}
                ],
                required_personnel=["safety_officer", "engineering", "medical_officer"],
                equipment_needed=["breathing_apparatus", "gas_detectors", "isolation_equipment"],
                communication_plan=["all_hands", "medical", "emergency_services"],
                safety_precautions=["breathing_protection", "evacuation_routes", "continuous_monitoring"],
                duration_estimate_minutes=60,
                confirmation_required=True,
                witness_required=True
            )
        ]
        
        for procedure in default_procedures:
            self.procedures[procedure.procedure_id] = procedure
            self._save_procedure_to_db(procedure)
    
    def _save_procedure_to_db(self, procedure: EmergencyProcedure):
        """Save emergency procedure to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO emergency_procedures 
            (procedure_id, emergency_type, priority, trigger_keywords, immediate_actions,
             sequential_steps, required_personnel, equipment_needed, communication_plan,
             safety_precautions, duration_estimate_minutes, confirmation_required, witness_required)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            procedure.procedure_id,
            procedure.emergency_type.value,
            procedure.priority.value,
            json.dumps(procedure.trigger_keywords),
            json.dumps(procedure.immediate_actions),
            json.dumps(procedure.sequential_steps),
            json.dumps(procedure.required_personnel),
            json.dumps(procedure.equipment_needed),
            json.dumps(procedure.communication_plan),
            json.dumps(procedure.safety_precautions),
            procedure.duration_estimate_minutes,
            procedure.confirmation_required,
            procedure.witness_required
        ))
        
        conn.commit()
        conn.close()
    
    def _init_command_handlers(self):
        """Initialize safety command handlers"""
        self.command_handlers = {
            SafetyCommandType.EMERGENCY_STOP: self._handle_emergency_stop,
            SafetyCommandType.EVACUATION: self._handle_evacuation,
            SafetyCommandType.LOCKDOWN: self._handle_lockdown,
            SafetyCommandType.ISOLATION: self._handle_isolation,
            SafetyCommandType.ALERT: self._handle_alert,
            SafetyCommandType.COMMUNICATION: self._handle_communication,
            SafetyCommandType.SYSTEM_SHUTDOWN: self._handle_system_shutdown,
            SafetyCommandType.OVERRIDE: self._handle_override,
            SafetyCommandType.STATUS_CHECK: self._handle_status_check,
            SafetyCommandType.RESCUE_OPERATION: self._handle_rescue_operation
        }
    
    def _load_emergency_contacts(self):
        """Load emergency contact information"""
        self.emergency_contacts = {
            "coast_guard": ["emergency_frequency", "coast_guard_station"],
            "medical": ["medical_officer", "nearest_hospital", "helicopter_rescue"],
            "fire": ["fire_team_leader", "local_fire_department", "foam_team"],
            "security": ["security_chief", "port_security", "authorities"],
            "environmental": ["environmental_officer", "spill_response_team"],
            "company": ["operations_center", "fleet_manager", "emergency_coordinator"]
        }
    
    async def process_voice_command(self, voice_command: str, user_id: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a voice command for emergency/safety operations.
        
        Args:
            voice_command: The voice command to process
            user_id: ID of the user issuing the command
            context: Additional context information
            
        Returns:
            Dictionary with processing results
        """
        command_lower = voice_command.lower().strip()
        
        # Check for emergency keywords first
        emergency_type = self._detect_emergency_type(command_lower)
        
        if emergency_type:
            return await self._handle_emergency_declaration(
                voice_command, user_id, emergency_type, context
            )
        
        # Check for safety commands
        safety_command_type = self._detect_safety_command_type(command_lower)
        
        if safety_command_type:
            return await self._execute_safety_command(
                voice_command, user_id, safety_command_type, context
            )
        
        # Regular command processing
        return await self._process_regular_command(voice_command, user_id, context)
    
    def _detect_emergency_type(self, command: str) -> Optional[EmergencyType]:
        """Detect emergency type from voice command"""
        # Check each procedure's trigger keywords
        for procedure in self.procedures.values():
            for keyword in procedure.trigger_keywords:
                if re.search(rf'\b{re.escape(keyword.lower())}\b', command):
                    return procedure.emergency_type
        
        # Check for general emergency keywords
        emergency_patterns = {
            EmergencyType.FIRE: [r'\bfire\b', r'\bsmoke\b', r'\bflames\b', r'\bburning\b'],
            EmergencyType.MEDICAL: [r'\bmedical\b', r'\binjury\b', r'\baccident\b', r'\bheart attack\b'],
            EmergencyType.COLLISION: [r'\bcollision\b', r'\bcrash\b', r'\bhit\b', r'\bimpact\b'],
            EmergencyType.FLOODING: [r'\bflood\b', r'\bwater\b', r'\bleak\b', r'\bsinking\b'],
            EmergencyType.MAN_OVERBOARD: [r'\boverboard\b', r'\bfallen\b'],
            EmergencyType.GENERAL_ALARM: [r'\bemergency\b', r'\balarm\b', r'\bhelp\b', r'\bmayday\b']
        }
        
        for emergency_type, patterns in emergency_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command):
                    return emergency_type
        
        return None
    
    def _detect_safety_command_type(self, command: str) -> Optional[SafetyCommandType]:
        """Detect safety command type from voice command"""
        command_patterns = {
            SafetyCommandType.EMERGENCY_STOP: [r'\bemergency stop\b', r'\bstop all\b', r'\bfull stop\b', r'\bhalt\b'],
            SafetyCommandType.EVACUATION: [r'\bevacuat\w*\b', r'\babandon\b', r'\bleave\b', r'\bmuster\b'],
            SafetyCommandType.LOCKDOWN: [r'\blockdown\b', r'\bsecure\b', r'\bisolate\b'],
            SafetyCommandType.ALERT: [r'\balert\b', r'\bwarning\b', r'\bnotify\b'],
            SafetyCommandType.COMMUNICATION: [r'\bradio\b', r'\bcall\b', r'\bcontact\b', r'\bmessage\b'],
            SafetyCommandType.SYSTEM_SHUTDOWN: [r'\bshutdown\b', r'\bpower down\b', r'\bstop system\b'],
            SafetyCommandType.OVERRIDE: [r'\boverride\b', r'\bbypass\b', r'\bforce\b'],
            SafetyCommandType.STATUS_CHECK: [r'\bstatus\b', r'\bcheck\b', r'\breport\b', r'\bsituation\b'],
            SafetyCommandType.RESCUE_OPERATION: [r'\brescue\b', r'\bsave\b', r'\brecove\w*\b']
        }
        
        for command_type, patterns in command_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command):
                    return command_type
        
        return None
    
    async def _handle_emergency_declaration(
        self, 
        voice_command: str, 
        user_id: str, 
        emergency_type: EmergencyType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle emergency declaration"""
        # Get appropriate procedure
        procedure = self._get_procedure_by_type(emergency_type)
        if not procedure:
            return {
                "success": False,
                "message": f"No procedure found for emergency type: {emergency_type.value}",
                "requires_confirmation": False
            }
        
        # Create emergency event
        event_id = str(uuid.uuid4())
        event = EmergencyEvent(
            event_id=event_id,
            emergency_type=emergency_type,
            priority=procedure.priority,
            location=context.get("location", "Unknown"),
            initiated_by=user_id,
            initiated_at=datetime.now(),
            description=voice_command,
            current_status="INITIATED",
            actions_taken=[],
            personnel_assigned=[],
            resources_deployed=[],
            estimated_resolution=None,
            communications_log=[]
        )
        
        # Store emergency event
        with self.lock:
            self.active_emergencies[event_id] = event
        
        self._save_emergency_event(event)
        
        # Execute immediate actions
        immediate_results = await self._execute_immediate_actions(procedure, event)
        
        # Log critical emergency
        self.logger.critical(f"EMERGENCY DECLARED: {emergency_type.value} by {user_id} - Event ID: {event_id}")
        
        return {
            "success": True,
            "message": f"Emergency {emergency_type.value} declared. Immediate actions initiated.",
            "event_id": event_id,
            "procedure_id": procedure.procedure_id,
            "immediate_actions": procedure.immediate_actions,
            "immediate_results": immediate_results,
            "requires_confirmation": procedure.confirmation_required,
            "requires_witness": procedure.witness_required,
            "estimated_duration": procedure.duration_estimate_minutes
        }
    
    async def _execute_safety_command(
        self,
        voice_command: str,
        user_id: str,
        command_type: SafetyCommandType,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute safety command"""
        command_id = str(uuid.uuid4())
        
        # Get appropriate handler
        handler = self.command_handlers.get(command_type)
        if not handler:
            return {
                "success": False,
                "message": f"No handler found for command type: {command_type.value}",
                "requires_confirmation": False
            }
        
        # Create safety command record
        safety_command = SafetyCommand(
            command_id=command_id,
            command_type=command_type,
            original_voice_command=voice_command,
            interpreted_command=self._interpret_safety_command(voice_command, command_type),
            executed_by=user_id,
            executed_at=datetime.now(),
            target_systems=self._get_target_systems(command_type, context),
            confirmation_received=False,
            execution_successful=False,
            impact_assessment="",
            rollback_available=False
        )
        
        # Execute command
        execution_result = await handler(safety_command, context)
        
        # Update command record
        safety_command.execution_successful = execution_result.get("success", False)
        safety_command.impact_assessment = execution_result.get("impact", "")
        safety_command.rollback_available = execution_result.get("rollback_available", False)
        
        # Store command
        with self.lock:
            self.executed_commands[command_id] = safety_command
        
        self._save_safety_command(safety_command)
        
        self.logger.warning(f"SAFETY COMMAND EXECUTED: {command_type.value} by {user_id} - Command ID: {command_id}")
        
        return {
            "success": execution_result.get("success", False),
            "message": execution_result.get("message", "Safety command executed"),
            "command_id": command_id,
            "command_type": command_type.value,
            "impact_assessment": safety_command.impact_assessment,
            "rollback_available": safety_command.rollback_available,
            "requires_confirmation": execution_result.get("requires_confirmation", True)
        }
    
    async def _process_regular_command(self, voice_command: str, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Process regular (non-emergency) command"""
        return {
            "success": True,
            "message": "Regular command processed",
            "command": voice_command,
            "requires_confirmation": False,
            "emergency_context": False
        }
    
    def _get_procedure_by_type(self, emergency_type: EmergencyType) -> Optional[EmergencyProcedure]:
        """Get procedure by emergency type"""
        for procedure in self.procedures.values():
            if procedure.emergency_type == emergency_type:
                return procedure
        return None
    
    async def _execute_immediate_actions(self, procedure: EmergencyProcedure, event: EmergencyEvent) -> Dict[str, Any]:
        """Execute immediate actions for emergency procedure"""
        results = {}
        
        for action in procedure.immediate_actions:
            try:
                # Simulate action execution
                action_result = await self._execute_emergency_action(action, event)
                results[action] = action_result
                
                # Log action
                event.actions_taken.append(f"{datetime.now().isoformat()}: {action}")
                
                # Add communication log
                event.communications_log.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": action,
                    "result": "success" if action_result.get("success") else "failed"
                })
                
            except Exception as e:
                self.logger.error(f"Failed to execute immediate action '{action}': {e}")
                results[action] = {"success": False, "error": str(e)}
        
        return results
    
    async def _execute_emergency_action(self, action: str, event: EmergencyEvent) -> Dict[str, Any]:
        """Execute a specific emergency action"""
        action_lower = action.lower()
        
        if "sound" in action_lower and "alarm" in action_lower:
            return await self._sound_alarm(event.emergency_type)
        elif "announce" in action_lower:
            return await self._make_announcement(action, event)
        elif "activate" in action_lower:
            return await self._activate_system(action, event)
        elif "alert" in action_lower:
            return await self._send_alert(action, event)
        elif "muster" in action_lower:
            return await self._initiate_muster(event)
        else:
            # Generic action execution
            return {"success": True, "message": f"Action executed: {action}"}
    
    async def _sound_alarm(self, emergency_type: EmergencyType) -> Dict[str, Any]:
        """Sound appropriate alarm for emergency type"""
        alarm_patterns = {
            EmergencyType.FIRE: "7_short_1_long",
            EmergencyType.ABANDON_SHIP: "6_short_blasts",
            EmergencyType.MAN_OVERBOARD: "6_short_blasts",
            EmergencyType.GENERAL_ALARM: "general_alarm_continuous"
        }
        
        pattern = alarm_patterns.get(emergency_type, "general_alarm")
        
        self.logger.critical(f"ALARM SOUNDED: {pattern} for {emergency_type.value}")
        
        return {
            "success": True,
            "message": f"Alarm sounded: {pattern}",
            "alarm_pattern": pattern
        }
    
    async def _make_announcement(self, announcement: str, event: EmergencyEvent) -> Dict[str, Any]:
        """Make PA announcement"""
        self.logger.critical(f"PA ANNOUNCEMENT: {announcement}")
        
        return {
            "success": True,
            "message": f"Announcement made: {announcement}",
            "channels": ["pa_system", "intercom", "radio"]
        }
    
    async def _activate_system(self, system_description: str, event: EmergencyEvent) -> Dict[str, Any]:
        """Activate emergency system"""
        if "fire suppression" in system_description.lower():
            return await self._activate_fire_suppression(event)
        elif "emergency lighting" in system_description.lower():
            return await self._activate_emergency_lighting()
        else:
            return {"success": True, "message": f"System activated: {system_description}"}
    
    async def _activate_fire_suppression(self, event: EmergencyEvent) -> Dict[str, Any]:
        """Activate fire suppression system"""
        self.logger.critical("FIRE SUPPRESSION SYSTEM ACTIVATED")
        
        # In real implementation, would interface with actual fire suppression systems
        return {
            "success": True,
            "message": "Fire suppression system activated",
            "systems": ["sprinkler", "foam", "co2"],
            "location": event.location
        }
    
    async def _activate_emergency_lighting(self) -> Dict[str, Any]:
        """Activate emergency lighting"""
        self.logger.warning("EMERGENCY LIGHTING ACTIVATED")
        
        return {
            "success": True,
            "message": "Emergency lighting activated",
            "duration": "8_hours_battery"
        }
    
    async def _send_alert(self, alert_description: str, event: EmergencyEvent) -> Dict[str, Any]:
        """Send emergency alert"""
        contacts = self._get_emergency_contacts_for_type(event.emergency_type)
        
        self.logger.critical(f"EMERGENCY ALERT SENT: {alert_description} to {contacts}")
        
        return {
            "success": True,
            "message": f"Alert sent: {alert_description}",
            "recipients": contacts,
            "methods": ["radio", "satellite", "cellular"]
        }
    
    async def _initiate_muster(self, event: EmergencyEvent) -> Dict[str, Any]:
        """Initiate muster procedure"""
        self.logger.critical("MUSTER PROCEDURE INITIATED")
        
        return {
            "success": True,
            "message": "Muster procedure initiated",
            "muster_stations": ["lifeboat_station_1", "lifeboat_station_2", "bridge"],
            "headcount_required": True
        }
    
    def _get_emergency_contacts_for_type(self, emergency_type: EmergencyType) -> List[str]:
        """Get emergency contacts for specific emergency type"""
        contact_mapping = {
            EmergencyType.FIRE: self.emergency_contacts.get("fire", []),
            EmergencyType.MEDICAL: self.emergency_contacts.get("medical", []),
            EmergencyType.COLLISION: self.emergency_contacts.get("coast_guard", []),
            EmergencyType.MAN_OVERBOARD: self.emergency_contacts.get("coast_guard", []),
            EmergencyType.SECURITY_BREACH: self.emergency_contacts.get("security", []),
            EmergencyType.ENVIRONMENTAL: self.emergency_contacts.get("environmental", [])
        }
        
        specific_contacts = contact_mapping.get(emergency_type, [])
        general_contacts = self.emergency_contacts.get("company", [])
        
        return specific_contacts + general_contacts
    
    def _interpret_safety_command(self, voice_command: str, command_type: SafetyCommandType) -> str:
        """Interpret voice command for safety execution"""
        command_lower = voice_command.lower().strip()
        
        interpretations = {
            SafetyCommandType.EMERGENCY_STOP: "EMERGENCY_STOP_ALL_SYSTEMS",
            SafetyCommandType.EVACUATION: "INITIATE_EVACUATION_PROCEDURES",
            SafetyCommandType.LOCKDOWN: "ACTIVATE_SECURITY_LOCKDOWN",
            SafetyCommandType.ALERT: "SEND_EMERGENCY_ALERT",
            SafetyCommandType.SYSTEM_SHUTDOWN: "CONTROLLED_SYSTEM_SHUTDOWN"
        }
        
        base_interpretation = interpretations.get(command_type, command_lower.replace(" ", "_").upper())
        
        # Add specificity based on voice command content
        if "engine" in command_lower:
            base_interpretation += "_ENGINE"
        elif "all" in command_lower:
            base_interpretation += "_ALL"
        elif "main" in command_lower:
            base_interpretation += "_MAIN"
        
        return base_interpretation
    
    def _get_target_systems(self, command_type: SafetyCommandType, context: Dict[str, Any]) -> List[str]:
        """Get target systems for safety command"""
        system_mappings = {
            SafetyCommandType.EMERGENCY_STOP: ["propulsion", "machinery", "electrical", "hydraulics"],
            SafetyCommandType.SYSTEM_SHUTDOWN: ["non_essential_systems", "air_conditioning", "lighting"],
            SafetyCommandType.LOCKDOWN: ["access_control", "doors", "hatches"],
            SafetyCommandType.ISOLATION: ["fuel_systems", "electrical_panels", "ventilation"]
        }
        
        return system_mappings.get(command_type, ["general"])
    
    # Safety command handlers
    async def _handle_emergency_stop(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency stop command"""
        self.logger.critical(f"EMERGENCY STOP EXECUTED: {command.interpreted_command}")
        
        # In real implementation, would interface with actual emergency stop systems
        return {
            "success": True,
            "message": "Emergency stop executed - All systems halted",
            "impact": "All machinery stopped, vessel dead in water",
            "rollback_available": False,
            "requires_confirmation": True
        }
    
    async def _handle_evacuation(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle evacuation command"""
        self.logger.critical(f"EVACUATION INITIATED: {command.interpreted_command}")
        
        return {
            "success": True,
            "message": "Evacuation procedures initiated",
            "impact": "All personnel directed to muster stations",
            "rollback_available": False,
            "requires_confirmation": True
        }
    
    async def _handle_lockdown(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle lockdown command"""
        self.logger.warning(f"LOCKDOWN ACTIVATED: {command.interpreted_command}")
        
        return {
            "success": True,
            "message": "Security lockdown activated",
            "impact": "All access points secured",
            "rollback_available": True,
            "requires_confirmation": True
        }
    
    async def _handle_isolation(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system isolation command"""
        return {
            "success": True,
            "message": "System isolation executed",
            "impact": "Target systems isolated from main power",
            "rollback_available": True,
            "requires_confirmation": True
        }
    
    async def _handle_alert(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle alert command"""
        return {
            "success": True,
            "message": "Emergency alert sent",
            "impact": "All relevant parties notified",
            "rollback_available": False,
            "requires_confirmation": False
        }
    
    async def _handle_communication(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle emergency communication command"""
        return {
            "success": True,
            "message": "Emergency communication established",
            "impact": "Contact established with emergency services",
            "rollback_available": False,
            "requires_confirmation": False
        }
    
    async def _handle_system_shutdown(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system shutdown command"""
        return {
            "success": True,
            "message": "System shutdown executed",
            "impact": "Non-essential systems powered down",
            "rollback_available": True,
            "requires_confirmation": True
        }
    
    async def _handle_override(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle safety override command"""
        self.logger.critical(f"SAFETY OVERRIDE EXECUTED: {command.interpreted_command}")
        
        return {
            "success": True,
            "message": "Safety override executed - WARNING: Safety systems bypassed",
            "impact": "Safety interlocks bypassed - EXTREME CAUTION REQUIRED",
            "rollback_available": True,
            "requires_confirmation": True
        }
    
    async def _handle_status_check(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle status check command"""
        return {
            "success": True,
            "message": "Status check completed",
            "impact": "Current system status reported",
            "rollback_available": False,
            "requires_confirmation": False
        }
    
    async def _handle_rescue_operation(self, command: SafetyCommand, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle rescue operation command"""
        self.logger.critical(f"RESCUE OPERATION INITIATED: {command.interpreted_command}")
        
        return {
            "success": True,
            "message": "Rescue operation initiated",
            "impact": "Rescue teams deployed, emergency protocols active",
            "rollback_available": False,
            "requires_confirmation": True
        }
    
    def _save_emergency_event(self, event: EmergencyEvent):
        """Save emergency event to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO emergency_events 
            (event_id, emergency_type, priority, location, initiated_by, initiated_at,
             description, current_status, actions_taken, personnel_assigned,
             resources_deployed, communications_log)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.event_id,
            event.emergency_type.value,
            event.priority.value,
            event.location,
            event.initiated_by,
            event.initiated_at.isoformat(),
            event.description,
            event.current_status,
            json.dumps(event.actions_taken),
            json.dumps(event.personnel_assigned),
            json.dumps(event.resources_deployed),
            json.dumps(event.communications_log)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_safety_command(self, command: SafetyCommand):
        """Save safety command to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO safety_commands 
            (command_id, command_type, original_voice_command, interpreted_command,
             executed_by, executed_at, target_systems, confirmation_received,
             execution_successful, impact_assessment, rollback_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            command.command_id,
            command.command_type.value,
            command.original_voice_command,
            command.interpreted_command,
            command.executed_by,
            command.executed_at.isoformat(),
            json.dumps(command.target_systems),
            command.confirmation_received,
            command.execution_successful,
            command.impact_assessment,
            command.rollback_available
        ))
        
        conn.commit()
        conn.close()
    
    def get_active_emergencies(self) -> List[Dict[str, Any]]:
        """Get list of active emergencies"""
        emergencies = []
        
        with self.lock:
            for event in self.active_emergencies.values():
                event_dict = asdict(event)
                event_dict["emergency_type"] = event.emergency_type.value
                event_dict["priority"] = event.priority.value
                event_dict["initiated_at"] = event.initiated_at.isoformat()
                emergencies.append(event_dict)
        
        return emergencies
    
    def get_emergency_statistics(self) -> Dict[str, Any]:
        """Get emergency system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total emergency events
        cursor.execute("SELECT COUNT(*) FROM emergency_events")
        total_events = cursor.fetchone()[0]
        
        # Events by type
        cursor.execute("SELECT emergency_type, COUNT(*) FROM emergency_events GROUP BY emergency_type")
        events_by_type = dict(cursor.fetchall())
        
        # Safety commands executed
        cursor.execute("SELECT COUNT(*) FROM safety_commands")
        total_commands = cursor.fetchone()[0]
        
        # Commands by type
        cursor.execute("SELECT command_type, COUNT(*) FROM safety_commands GROUP BY command_type")
        commands_by_type = dict(cursor.fetchall())
        
        # Success rate
        cursor.execute("SELECT COUNT(*) FROM safety_commands WHERE execution_successful = 1")
        successful_commands = cursor.fetchone()[0]
        success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0
        
        conn.close()
        
        return {
            "total_emergency_events": total_events,
            "active_emergencies": len(self.active_emergencies),
            "events_by_type": events_by_type,
            "total_safety_commands": total_commands,
            "commands_by_type": commands_by_type,
            "command_success_rate": round(success_rate, 2),
            "loaded_procedures": len(self.procedures)
        }


# Example usage and testing
async def main():
    """Example usage of emergency procedures system"""
    emergency_system = EmergencyProcedures()
    
    # Test emergency commands
    test_commands = [
        ("fire in engine room", "officer1", {"location": "engine_room"}),
        ("man overboard starboard side", "lookout1", {"location": "deck"}),
        ("emergency stop all systems", "captain", {"authority": "master"}),
        ("toxic gas alarm in cargo hold", "safety_officer", {"location": "cargo_hold"}),
        ("evacuation all personnel", "master", {"authority": "master"})
    ]
    
    for command, user_id, context in test_commands:
        print(f"\n=== Testing command: '{command}' ===")
        
        result = await emergency_system.process_voice_command(command, user_id, context)
        print(f"Result: {result}")
        
        if result.get("success"):
            print(f"Emergency Type: {result.get('message', 'Unknown')}")
            if result.get("immediate_actions"):
                print(f"Immediate Actions: {result['immediate_actions']}")
    
    # Show active emergencies
    active_emergencies = emergency_system.get_active_emergencies()
    print(f"\nActive Emergencies: {len(active_emergencies)}")
    
    # Show statistics
    stats = emergency_system.get_emergency_statistics()
    print(f"Emergency Statistics: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())