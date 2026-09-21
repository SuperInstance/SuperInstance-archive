"""
Context Awareness Engine for Voice Excellence System

This module provides intelligent context awareness that understands the current
operational state (marine navigation, industrial operation, emergency situation)
and adapts command interpretation accordingly.

Author: Claude
Date: 2025-08-24
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import sqlite3
import threading
from pathlib import Path

class ContextType(Enum):
    """Different operational contexts"""
    MARINE_NAVIGATION = "marine_navigation"
    MARINE_FISHING = "marine_fishing"
    MARINE_DOCKING = "marine_docking"
    INDUSTRIAL_MANUFACTURING = "industrial_manufacturing"
    INDUSTRIAL_MAINTENANCE = "industrial_maintenance"
    INDUSTRIAL_SAFETY = "industrial_safety"
    EMERGENCY_MEDICAL = "emergency_medical"
    EMERGENCY_FIRE = "emergency_fire"
    EMERGENCY_EVACUATION = "emergency_evacuation"
    OFFICE_MEETING = "office_meeting"
    OFFICE_PRESENTATION = "office_presentation"
    TRAINING_SESSION = "training_session"
    IDLE = "idle"

class ContextPriority(Enum):
    """Context priority levels"""
    EMERGENCY = 1
    CRITICAL = 2
    HIGH = 3
    NORMAL = 4
    LOW = 5

class EnvironmentalFactor(Enum):
    """Environmental factors that affect context"""
    NOISE_LEVEL = "noise_level"
    LIGHTING = "lighting"
    WEATHER = "weather"
    LOCATION = "location"
    TIME_OF_DAY = "time_of_day"
    PERSONNEL_COUNT = "personnel_count"
    EQUIPMENT_STATUS = "equipment_status"

@dataclass
class ContextState:
    """Current context state"""
    context_type: ContextType
    priority: ContextPriority
    confidence: float  # 0.0 to 1.0
    start_time: datetime
    last_updated: datetime
    environmental_factors: Dict[EnvironmentalFactor, Any]
    active_equipment: List[str]
    personnel_present: List[str]
    safety_level: str
    command_restrictions: List[str]
    preferred_confirmations: List[str]

@dataclass
class ContextRule:
    """Context detection rule"""
    rule_id: str
    name: str
    context_type: ContextType
    priority: ContextPriority
    conditions: Dict[str, Any]
    actions: List[str]
    min_confidence: float
    enabled: bool

@dataclass
class CommandContext:
    """Context-aware command interpretation"""
    original_command: str
    interpreted_command: str
    context_type: ContextType
    required_confirmations: List[str]
    safety_checks: List[str]
    priority_level: int
    timeout_seconds: int
    fallback_actions: List[str]

class ContextAwarenessEngine:
    """
    Intelligent context awareness system that understands operational states
    and adapts voice command interpretation accordingly.
    """
    
    def __init__(self, db_path: str = "context_awareness.db"):
        """
        Initialize the context awareness engine.
        
        Args:
            db_path: Path to the context database
        """
        self.db_path = db_path
        self.current_context: Optional[ContextState] = None
        self.context_history: List[ContextState] = []
        self.context_rules: Dict[str, ContextRule] = {}
        self.sensor_data: Dict[str, Any] = {}
        self.learning_data: Dict[str, List[Any]] = {"patterns": [], "corrections": []}
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Load default rules
        self._load_default_rules()
        
        # Start background monitoring
        self._start_monitoring()
        
        self.logger.info("Context Awareness Engine initialized")
    
    def _init_database(self):
        """Initialize the context database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Context history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                context_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                confidence REAL NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT,
                environmental_factors TEXT,
                active_equipment TEXT,
                personnel_present TEXT,
                safety_level TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Context rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS context_rules (
                rule_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                context_type TEXT NOT NULL,
                priority TEXT NOT NULL,
                conditions TEXT NOT NULL,
                actions TEXT NOT NULL,
                min_confidence REAL NOT NULL,
                enabled BOOLEAN NOT NULL DEFAULT TRUE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Sensor data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sensor_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_type TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Learning data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS learning_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                context_type TEXT,
                pattern_data TEXT NOT NULL,
                accuracy REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_default_rules(self):
        """Load default context detection rules"""
        default_rules = [
            ContextRule(
                rule_id="emergency_fire",
                name="Fire Emergency Detection",
                context_type=ContextType.EMERGENCY_FIRE,
                priority=ContextPriority.EMERGENCY,
                conditions={
                    "fire_alarm": True,
                    "smoke_detected": True,
                    "temperature_threshold": 80  # Celsius
                },
                actions=["activate_fire_protocol", "alert_emergency_services"],
                min_confidence=0.95,
                enabled=True
            ),
            ContextRule(
                rule_id="marine_navigation",
                name="Marine Navigation Mode",
                context_type=ContextType.MARINE_NAVIGATION,
                priority=ContextPriority.HIGH,
                conditions={
                    "gps_speed": ">5",  # knots
                    "radar_active": True,
                    "autopilot_engaged": True
                },
                actions=["enable_navigation_commands", "reduce_non_essential_alerts"],
                min_confidence=0.85,
                enabled=True
            ),
            ContextRule(
                rule_id="industrial_maintenance",
                name="Industrial Maintenance Mode",
                context_type=ContextType.INDUSTRIAL_MAINTENANCE,
                priority=ContextPriority.HIGH,
                conditions={
                    "maintenance_schedule": "active",
                    "equipment_status": "maintenance",
                    "safety_lockout": True
                },
                actions=["enable_maintenance_commands", "require_safety_confirmations"],
                min_confidence=0.80,
                enabled=True
            ),
            ContextRule(
                rule_id="office_meeting",
                name="Office Meeting Detection",
                context_type=ContextType.OFFICE_MEETING,
                priority=ContextPriority.NORMAL,
                conditions={
                    "calendar_meeting": True,
                    "personnel_count": ">3",
                    "microphone_usage": "high"
                },
                actions=["reduce_voice_volume", "enable_meeting_commands"],
                min_confidence=0.70,
                enabled=True
            )
        ]
        
        for rule in default_rules:
            self.context_rules[rule.rule_id] = rule
            self._save_rule_to_db(rule)
    
    def _save_rule_to_db(self, rule: ContextRule):
        """Save context rule to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO context_rules 
            (rule_id, name, context_type, priority, conditions, actions, min_confidence, enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule.rule_id,
            rule.name,
            rule.context_type.value,
            rule.priority.value,
            json.dumps(rule.conditions),
            json.dumps(rule.actions),
            rule.min_confidence,
            rule.enabled
        ))
        
        conn.commit()
        conn.close()
    
    def _start_monitoring(self):
        """Start background context monitoring"""
        def monitor_loop():
            while True:
                try:
                    self._update_sensor_data()
                    self._evaluate_context()
                    time.sleep(1)  # Check every second
                except Exception as e:
                    self.logger.error(f"Context monitoring error: {e}")
                    time.sleep(5)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _update_sensor_data(self):
        """Update sensor data (simulated - in real implementation would read from actual sensors)"""
        # Simulate sensor readings
        current_time = datetime.now()
        
        # Simulated environmental sensors
        self.sensor_data.update({
            "noise_level": 45.0 + (time.time() % 10),  # dB
            "temperature": 22.0 + (time.time() % 5),   # Celsius
            "humidity": 60.0 + (time.time() % 20),     # %
            "light_level": 300.0 + (time.time() % 100), # lux
            "personnel_count": 3,
            "equipment_active": ["radar", "autopilot", "sonar"],
            "gps_speed": 12.5,  # knots
            "timestamp": current_time.isoformat()
        })
        
        # Store in database
        self._store_sensor_data()
    
    def _store_sensor_data(self):
        """Store sensor data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for sensor_type, value in self.sensor_data.items():
            if sensor_type != "timestamp":
                cursor.execute("""
                    INSERT INTO sensor_data (sensor_type, value)
                    VALUES (?, ?)
                """, (sensor_type, json.dumps(value)))
        
        conn.commit()
        conn.close()
    
    def _evaluate_context(self):
        """Evaluate current context based on sensor data and rules"""
        with self.lock:
            best_match = None
            best_confidence = 0.0
            
            for rule in self.context_rules.values():
                if not rule.enabled:
                    continue
                
                confidence = self._evaluate_rule(rule)
                
                if confidence >= rule.min_confidence and confidence > best_confidence:
                    best_match = rule
                    best_confidence = confidence
            
            if best_match and (
                not self.current_context or 
                self.current_context.context_type != best_match.context_type or
                best_confidence > self.current_context.confidence
            ):
                self._set_context(best_match, best_confidence)
    
    def _evaluate_rule(self, rule: ContextRule) -> float:
        """Evaluate a context rule against current sensor data"""
        try:
            conditions_met = 0
            total_conditions = len(rule.conditions)
            
            for condition, expected_value in rule.conditions.items():
                if condition in self.sensor_data:
                    actual_value = self.sensor_data[condition]
                    
                    if isinstance(expected_value, bool):
                        if actual_value == expected_value:
                            conditions_met += 1
                    elif isinstance(expected_value, str) and expected_value.startswith(">"):
                        threshold = float(expected_value[1:])
                        if isinstance(actual_value, (int, float)) and actual_value > threshold:
                            conditions_met += 1
                    elif isinstance(expected_value, str) and expected_value.startswith("<"):
                        threshold = float(expected_value[1:])
                        if isinstance(actual_value, (int, float)) and actual_value < threshold:
                            conditions_met += 1
                    elif actual_value == expected_value:
                        conditions_met += 1
            
            return conditions_met / total_conditions if total_conditions > 0 else 0.0
        
        except Exception as e:
            self.logger.error(f"Rule evaluation error: {e}")
            return 0.0
    
    def _set_context(self, rule: ContextRule, confidence: float):
        """Set the current context"""
        current_time = datetime.now()
        
        # End previous context
        if self.current_context:
            self.current_context.last_updated = current_time
            self.context_history.append(self.current_context)
        
        # Create new context state
        self.current_context = ContextState(
            context_type=rule.context_type,
            priority=rule.priority,
            confidence=confidence,
            start_time=current_time,
            last_updated=current_time,
            environmental_factors={
                EnvironmentalFactor.NOISE_LEVEL: self.sensor_data.get("noise_level", 0),
                EnvironmentalFactor.LIGHTING: self.sensor_data.get("light_level", 0),
                EnvironmentalFactor.PERSONNEL_COUNT: self.sensor_data.get("personnel_count", 0),
                EnvironmentalFactor.EQUIPMENT_STATUS: self.sensor_data.get("equipment_active", [])
            },
            active_equipment=self.sensor_data.get("equipment_active", []),
            personnel_present=["operator1", "engineer2"],  # Simulated
            safety_level=self._determine_safety_level(rule.context_type),
            command_restrictions=self._get_command_restrictions(rule.context_type),
            preferred_confirmations=self._get_preferred_confirmations(rule.context_type)
        )
        
        # Execute rule actions
        self._execute_rule_actions(rule.actions)
        
        # Store in database
        self._store_context_history()
        
        self.logger.info(f"Context changed to {rule.context_type.value} (confidence: {confidence:.2f})")
    
    def _determine_safety_level(self, context_type: ContextType) -> str:
        """Determine safety level for context"""
        safety_levels = {
            ContextType.EMERGENCY_FIRE: "critical",
            ContextType.EMERGENCY_MEDICAL: "critical",
            ContextType.EMERGENCY_EVACUATION: "critical",
            ContextType.MARINE_NAVIGATION: "high",
            ContextType.INDUSTRIAL_MANUFACTURING: "high",
            ContextType.INDUSTRIAL_MAINTENANCE: "high",
            ContextType.INDUSTRIAL_SAFETY: "critical",
            ContextType.MARINE_FISHING: "medium",
            ContextType.MARINE_DOCKING: "high",
            ContextType.OFFICE_MEETING: "low",
            ContextType.OFFICE_PRESENTATION: "low",
            ContextType.TRAINING_SESSION: "medium",
            ContextType.IDLE: "low"
        }
        return safety_levels.get(context_type, "medium")
    
    def _get_command_restrictions(self, context_type: ContextType) -> List[str]:
        """Get command restrictions for context"""
        restrictions = {
            ContextType.EMERGENCY_FIRE: ["non_emergency_commands", "entertainment", "personal_calls"],
            ContextType.EMERGENCY_MEDICAL: ["non_emergency_commands", "entertainment", "personal_calls"],
            ContextType.MARINE_NAVIGATION: ["entertainment", "personal_calls", "system_shutdown"],
            ContextType.INDUSTRIAL_MAINTENANCE: ["production_commands", "non_maintenance_systems"],
            ContextType.OFFICE_MEETING: ["loud_commands", "personal_calls"],
            ContextType.TRAINING_SESSION: ["production_commands", "critical_system_changes"]
        }
        return restrictions.get(context_type, [])
    
    def _get_preferred_confirmations(self, context_type: ContextType) -> List[str]:
        """Get preferred confirmation types for context"""
        confirmations = {
            ContextType.EMERGENCY_FIRE: ["verbal_confirmation", "witness_confirmation"],
            ContextType.EMERGENCY_MEDICAL: ["verbal_confirmation", "witness_confirmation"],
            ContextType.MARINE_NAVIGATION: ["verbal_confirmation", "display_confirmation"],
            ContextType.INDUSTRIAL_MAINTENANCE: ["verbal_confirmation", "safety_confirmation"],
            ContextType.INDUSTRIAL_SAFETY: ["verbal_confirmation", "safety_confirmation", "witness_confirmation"],
            ContextType.OFFICE_MEETING: ["display_confirmation"],
            ContextType.TRAINING_SESSION: ["verbal_confirmation"]
        }
        return confirmations.get(context_type, ["verbal_confirmation"])
    
    def _execute_rule_actions(self, actions: List[str]):
        """Execute actions triggered by context rules"""
        for action in actions:
            try:
                if action == "activate_fire_protocol":
                    self._activate_fire_protocol()
                elif action == "alert_emergency_services":
                    self._alert_emergency_services()
                elif action == "enable_navigation_commands":
                    self._enable_navigation_commands()
                elif action == "reduce_non_essential_alerts":
                    self._reduce_non_essential_alerts()
                elif action == "enable_maintenance_commands":
                    self._enable_maintenance_commands()
                elif action == "require_safety_confirmations":
                    self._require_safety_confirmations()
                elif action == "reduce_voice_volume":
                    self._reduce_voice_volume()
                elif action == "enable_meeting_commands":
                    self._enable_meeting_commands()
                
                self.logger.info(f"Executed context action: {action}")
            except Exception as e:
                self.logger.error(f"Failed to execute action {action}: {e}")
    
    def _activate_fire_protocol(self):
        """Activate fire emergency protocol"""
        # In real implementation, this would trigger actual fire safety systems
        self.logger.critical("FIRE PROTOCOL ACTIVATED - EMERGENCY MODE")
    
    def _alert_emergency_services(self):
        """Alert emergency services"""
        # In real implementation, this would contact emergency services
        self.logger.critical("EMERGENCY SERVICES ALERTED")
    
    def _enable_navigation_commands(self):
        """Enable navigation-specific commands"""
        self.logger.info("Navigation commands enabled")
    
    def _reduce_non_essential_alerts(self):
        """Reduce non-essential alerts"""
        self.logger.info("Non-essential alerts reduced")
    
    def _enable_maintenance_commands(self):
        """Enable maintenance-specific commands"""
        self.logger.info("Maintenance commands enabled")
    
    def _require_safety_confirmations(self):
        """Require additional safety confirmations"""
        self.logger.info("Safety confirmations required")
    
    def _reduce_voice_volume(self):
        """Reduce voice volume for meeting context"""
        self.logger.info("Voice volume reduced for meeting")
    
    def _enable_meeting_commands(self):
        """Enable meeting-specific commands"""
        self.logger.info("Meeting commands enabled")
    
    def _store_context_history(self):
        """Store context change in database"""
        if not self.current_context:
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO context_history 
            (context_type, priority, confidence, start_time, environmental_factors, 
             active_equipment, personnel_present, safety_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            self.current_context.context_type.value,
            self.current_context.priority.value,
            self.current_context.confidence,
            self.current_context.start_time.isoformat(),
            json.dumps({k.value: v for k, v in self.current_context.environmental_factors.items()}),
            json.dumps(self.current_context.active_equipment),
            json.dumps(self.current_context.personnel_present),
            self.current_context.safety_level
        ))
        
        conn.commit()
        conn.close()
    
    async def interpret_command(self, command: str, user_id: str = "default") -> CommandContext:
        """
        Interpret a voice command in the current context.
        
        Args:
            command: The voice command to interpret
            user_id: ID of the user issuing the command
            
        Returns:
            CommandContext with context-aware interpretation
        """
        if not self.current_context:
            # Set idle context if none exists
            self._set_idle_context()
        
        context = self.current_context
        interpreted_command = await self._context_aware_interpretation(command, context)
        
        # Determine required confirmations
        required_confirmations = self._get_required_confirmations(command, context)
        
        # Determine safety checks
        safety_checks = self._get_safety_checks(command, context)
        
        # Set priority and timeout
        priority_level = self._get_command_priority(command, context)
        timeout_seconds = self._get_command_timeout(command, context)
        
        # Get fallback actions
        fallback_actions = self._get_fallback_actions(command, context)
        
        return CommandContext(
            original_command=command,
            interpreted_command=interpreted_command,
            context_type=context.context_type,
            required_confirmations=required_confirmations,
            safety_checks=safety_checks,
            priority_level=priority_level,
            timeout_seconds=timeout_seconds,
            fallback_actions=fallback_actions
        )
    
    def _set_idle_context(self):
        """Set idle context when no other context is detected"""
        idle_rule = ContextRule(
            rule_id="idle",
            name="Idle State",
            context_type=ContextType.IDLE,
            priority=ContextPriority.LOW,
            conditions={},
            actions=[],
            min_confidence=1.0,
            enabled=True
        )
        self._set_context(idle_rule, 1.0)
    
    async def _context_aware_interpretation(self, command: str, context: ContextState) -> str:
        """Interpret command based on current context"""
        command_lower = command.lower().strip()
        
        # Context-specific command mappings
        if context.context_type == ContextType.MARINE_NAVIGATION:
            if "turn" in command_lower:
                return f"helm_turn_{command_lower.split('turn')[-1].strip()}"
            elif "speed" in command_lower:
                return f"engine_speed_{command_lower.split('speed')[-1].strip()}"
            elif "course" in command_lower:
                return f"set_course_{command_lower.split('course')[-1].strip()}"
        
        elif context.context_type == ContextType.INDUSTRIAL_MAINTENANCE:
            if "stop" in command_lower:
                return f"emergency_stop_all_systems"
            elif "shutdown" in command_lower:
                return f"controlled_shutdown_{command_lower.split('shutdown')[-1].strip()}"
            elif "status" in command_lower:
                return f"maintenance_status_report"
        
        elif context.context_type in [ContextType.EMERGENCY_FIRE, ContextType.EMERGENCY_MEDICAL]:
            if "help" in command_lower or "emergency" in command_lower:
                return "activate_emergency_response"
            elif "evacuate" in command_lower:
                return "initiate_evacuation_procedure"
        
        elif context.context_type == ContextType.OFFICE_MEETING:
            if "record" in command_lower:
                return "start_meeting_recording"
            elif "mute" in command_lower:
                return "mute_microphone"
            elif "share" in command_lower:
                return "share_screen"
        
        # Default interpretation
        return command.lower().replace(" ", "_")
    
    def _get_required_confirmations(self, command: str, context: ContextState) -> List[str]:
        """Get required confirmations for command in context"""
        confirmations = []
        command_lower = command.lower()
        
        # High-risk commands always need confirmation
        if any(word in command_lower for word in ["stop", "shutdown", "emergency", "delete", "reset"]):
            confirmations.extend(context.preferred_confirmations)
        
        # Context-specific confirmations
        if context.context_type in [ContextType.EMERGENCY_FIRE, ContextType.EMERGENCY_MEDICAL]:
            confirmations.append("witness_confirmation")
        
        if context.safety_level == "critical":
            confirmations.extend(["verbal_confirmation", "safety_confirmation"])
        
        return list(set(confirmations))  # Remove duplicates
    
    def _get_safety_checks(self, command: str, context: ContextState) -> List[str]:
        """Get required safety checks for command in context"""
        checks = []
        command_lower = command.lower()
        
        if context.safety_level in ["critical", "high"]:
            checks.append("authorization_check")
        
        if any(word in command_lower for word in ["stop", "shutdown", "emergency"]):
            checks.extend(["system_state_check", "personnel_safety_check"])
        
        if context.context_type == ContextType.INDUSTRIAL_MAINTENANCE:
            checks.append("lockout_tagout_check")
        
        if context.context_type == ContextType.MARINE_NAVIGATION:
            checks.append("navigation_safety_check")
        
        return checks
    
    def _get_command_priority(self, command: str, context: ContextState) -> int:
        """Get command priority (1=highest, 10=lowest)"""
        command_lower = command.lower()
        
        if "emergency" in command_lower:
            return 1
        
        if context.context_type in [ContextType.EMERGENCY_FIRE, ContextType.EMERGENCY_MEDICAL]:
            return 1
        
        if "stop" in command_lower or "shutdown" in command_lower:
            return 2
        
        if context.priority == ContextPriority.EMERGENCY:
            return 2
        elif context.priority == ContextPriority.CRITICAL:
            return 3
        elif context.priority == ContextPriority.HIGH:
            return 4
        elif context.priority == ContextPriority.NORMAL:
            return 6
        else:
            return 8
    
    def _get_command_timeout(self, command: str, context: ContextState) -> int:
        """Get command timeout in seconds"""
        command_lower = command.lower()
        
        if "emergency" in command_lower:
            return 5  # Emergency commands must be executed quickly
        
        if context.context_type in [ContextType.EMERGENCY_FIRE, ContextType.EMERGENCY_MEDICAL]:
            return 5
        
        if context.safety_level == "critical":
            return 10
        elif context.safety_level == "high":
            return 30
        else:
            return 60
    
    def _get_fallback_actions(self, command: str, context: ContextState) -> List[str]:
        """Get fallback actions if command fails"""
        actions = []
        command_lower = command.lower()
        
        if "emergency" in command_lower:
            actions.extend(["alert_supervisor", "activate_backup_systems"])
        
        if context.context_type == ContextType.MARINE_NAVIGATION:
            actions.extend(["manual_override_notification", "log_navigation_event"])
        
        if context.context_type == ContextType.INDUSTRIAL_MAINTENANCE:
            actions.extend(["safety_system_alert", "maintenance_log_entry"])
        
        actions.append("command_failure_log")
        return actions
    
    def get_current_context(self) -> Optional[ContextState]:
        """Get the current context state"""
        return self.current_context
    
    def get_context_history(self, limit: int = 100) -> List[ContextState]:
        """Get recent context history"""
        return self.context_history[-limit:]
    
    def add_context_rule(self, rule: ContextRule) -> bool:
        """Add a new context detection rule"""
        try:
            self.context_rules[rule.rule_id] = rule
            self._save_rule_to_db(rule)
            self.logger.info(f"Added context rule: {rule.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add context rule: {e}")
            return False
    
    def update_sensor_data(self, sensor_type: str, value: Any):
        """Update sensor data from external sources"""
        self.sensor_data[sensor_type] = value
        self.sensor_data["timestamp"] = datetime.now().isoformat()
    
    def force_context(self, context_type: ContextType, duration_minutes: int = 60):
        """Force a specific context for testing or override"""
        forced_rule = ContextRule(
            rule_id=f"forced_{context_type.value}",
            name=f"Forced {context_type.value}",
            context_type=context_type,
            priority=ContextPriority.HIGH,
            conditions={},
            actions=[],
            min_confidence=1.0,
            enabled=True
        )
        
        self._set_context(forced_rule, 1.0)
        
        # Schedule context reset
        def reset_context():
            time.sleep(duration_minutes * 60)
            if (self.current_context and 
                self.current_context.context_type == context_type):
                self._set_idle_context()
        
        reset_thread = threading.Thread(target=reset_context, daemon=True)
        reset_thread.start()
        
        self.logger.info(f"Forced context to {context_type.value} for {duration_minutes} minutes")
    
    def get_context_statistics(self) -> Dict[str, Any]:
        """Get context usage statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get context type distribution
        cursor.execute("""
            SELECT context_type, COUNT(*) as count 
            FROM context_history 
            GROUP BY context_type
        """)
        context_distribution = dict(cursor.fetchall())
        
        # Get average confidence by context type
        cursor.execute("""
            SELECT context_type, AVG(confidence) as avg_confidence
            FROM context_history 
            GROUP BY context_type
        """)
        avg_confidence = dict(cursor.fetchall())
        
        # Get recent activity
        cursor.execute("""
            SELECT COUNT(*) as changes
            FROM context_history 
            WHERE created_at > datetime('now', '-1 hour')
        """)
        recent_changes = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "current_context": self.current_context.context_type.value if self.current_context else None,
            "current_confidence": self.current_context.confidence if self.current_context else 0,
            "context_distribution": context_distribution,
            "average_confidence": avg_confidence,
            "recent_changes": recent_changes,
            "active_rules": len([r for r in self.context_rules.values() if r.enabled]),
            "total_rules": len(self.context_rules)
        }


# Example usage and testing
async def main():
    """Example usage of the context awareness engine"""
    engine = ContextAwarenessEngine()
    
    # Wait for initial context detection
    await asyncio.sleep(2)
    
    print(f"Current context: {engine.get_current_context()}")
    
    # Test command interpretation
    test_commands = [
        "turn left 15 degrees",
        "stop all systems",
        "emergency help needed",
        "start meeting recording",
        "check engine status"
    ]
    
    for command in test_commands:
        context = await engine.interpret_command(command)
        print(f"Command: '{command}' -> '{context.interpreted_command}' "
              f"(context: {context.context_type.value})")
    
    # Show statistics
    stats = engine.get_context_statistics()
    print(f"Context statistics: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())