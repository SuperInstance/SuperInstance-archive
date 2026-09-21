"""
Hands-Free Operation Capabilities for Voice Excellence System

This module enables comprehensive hands-free voice operation for marine and
industrial environments, including gesture integration, eye tracking,
and advanced voice-only workflows.

Author: Claude
Date: 2025-08-24
"""

import json
import time
import asyncio
from typing import Dict, List, Optional, Any, Callable, Tuple
from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import sqlite3
import threading
from pathlib import Path
import cv2
import numpy as np

class HandsFreeMode(Enum):
    """Different hands-free operation modes"""
    VOICE_ONLY = "voice_only"
    VOICE_GESTURE = "voice_gesture"
    VOICE_EYE_TRACKING = "voice_eye_tracking"
    VOICE_HEAD_TRACKING = "voice_head_tracking"
    VOICE_PROXIMITY = "voice_proximity"
    FULL_MULTIMODAL = "full_multimodal"
    EMERGENCY_VOICE = "emergency_voice"

class GestureType(Enum):
    """Types of recognized gestures"""
    NOD_YES = "nod_yes"
    SHAKE_NO = "shake_no"
    POINT_LEFT = "point_left"
    POINT_RIGHT = "point_right"
    POINT_UP = "point_up"
    POINT_DOWN = "point_down"
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    OPEN_PALM_STOP = "open_palm_stop"
    FIST_CONFIRM = "fist_confirm"
    WAVE_ATTENTION = "wave_attention"

class EyeGazeZone(Enum):
    """Eye gaze zones for interface control"""
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    MIDDLE_LEFT = "middle_left"
    MIDDLE_CENTER = "middle_center"
    MIDDLE_RIGHT = "middle_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"

@dataclass
class HandsFreeSession:
    """Hands-free operation session"""
    session_id: str
    user_id: str
    mode: HandsFreeMode
    started_at: datetime
    last_interaction: datetime
    total_commands: int
    successful_commands: int
    gesture_enabled: bool
    eye_tracking_enabled: bool
    voice_sensitivity: float
    environmental_context: str
    active_workflows: List[str]
    calibration_data: Dict[str, Any]

@dataclass
class VoiceGesturePair:
    """Voice command paired with gesture recognition"""
    voice_command: str
    gesture_type: Optional[GestureType]
    eye_gaze_zone: Optional[EyeGazeZone]
    confidence_voice: float
    confidence_gesture: float
    confidence_gaze: float
    timestamp: datetime
    combined_intent: str
    requires_confirmation: bool

@dataclass
class WorkflowStep:
    """Step in a hands-free workflow"""
    step_id: str
    step_name: str
    voice_prompts: List[str]
    expected_responses: List[str]
    gesture_alternatives: List[GestureType]
    eye_gaze_alternatives: List[EyeGazeZone]
    timeout_seconds: int
    retry_attempts: int
    success_criteria: str
    failure_actions: List[str]

class HandsFreeOperator:
    """
    Comprehensive hands-free operation system enabling voice-only
    and multimodal interaction for marine/industrial environments.
    """
    
    def __init__(self, db_path: str = "hands_free.db"):
        """
        Initialize hands-free operation system.
        
        Args:
            db_path: Path to the hands-free database
        """
        self.db_path = db_path
        self.active_sessions: Dict[str, HandsFreeSession] = {}
        self.voice_gesture_pairs: List[VoiceGesturePair] = []
        self.workflows: Dict[str, List[WorkflowStep]] = {}
        self.gesture_detector = None
        self.eye_tracker = None
        self.voice_processor = None
        self.calibration_data: Dict[str, Any] = {}
        self.interaction_history: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        
        # Initialize database
        self._init_database()
        
        # Initialize detection systems
        self._init_gesture_detection()
        self._init_eye_tracking()
        self._init_voice_processing()
        
        # Load default workflows
        self._load_default_workflows()
        
        # Start monitoring loop
        self._start_monitoring()
        
        self.logger.info("Hands-Free Operator initialized")
    
    def _init_database(self):
        """Initialize the hands-free database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hands_free_sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                total_commands INTEGER DEFAULT 0,
                successful_commands INTEGER DEFAULT 0,
                gesture_enabled BOOLEAN DEFAULT FALSE,
                eye_tracking_enabled BOOLEAN DEFAULT FALSE,
                voice_sensitivity REAL DEFAULT 0.5,
                environmental_context TEXT,
                calibration_data TEXT,
                performance_metrics TEXT
            )
        """)
        
        # Voice-gesture pairs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voice_gesture_pairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                voice_command TEXT NOT NULL,
                gesture_type TEXT,
                eye_gaze_zone TEXT,
                confidence_voice REAL NOT NULL,
                confidence_gesture REAL,
                confidence_gaze REAL,
                timestamp TEXT NOT NULL,
                combined_intent TEXT NOT NULL,
                execution_successful BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (session_id) REFERENCES hands_free_sessions (session_id)
            )
        """)
        
        # Workflows table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                workflow_id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                description TEXT NOT NULL,
                steps TEXT NOT NULL,
                estimated_duration INTEGER NOT NULL,
                hands_free_compatible BOOLEAN DEFAULT TRUE,
                safety_level TEXT DEFAULT 'standard',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Calibration data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS calibration_data (
                user_id TEXT NOT NULL,
                calibration_type TEXT NOT NULL,
                calibration_values TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at DATETIME,
                PRIMARY KEY (user_id, calibration_type)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _init_gesture_detection(self):
        """Initialize gesture detection system"""
        try:
            # Initialize gesture recognition (simplified for demonstration)
            self.gesture_detector = {
                "initialized": True,
                "model_loaded": False,
                "confidence_threshold": 0.7,
                "supported_gestures": [g.value for g in GestureType],
                "calibration_required": True
            }
            self.logger.info("Gesture detection initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize gesture detection: {e}")
            self.gesture_detector = {"initialized": False}
    
    def _init_eye_tracking(self):
        """Initialize eye tracking system"""
        try:
            # Initialize eye tracking (simplified for demonstration)
            self.eye_tracker = {
                "initialized": True,
                "model_loaded": False,
                "gaze_zones": [z.value for z in EyeGazeZone],
                "calibration_required": True,
                "accuracy_threshold": 0.8
            }
            self.logger.info("Eye tracking initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize eye tracking: {e}")
            self.eye_tracker = {"initialized": False}
    
    def _init_voice_processing(self):
        """Initialize enhanced voice processing for hands-free operation"""
        self.voice_processor = {
            "initialized": True,
            "continuous_listening": True,
            "noise_suppression": True,
            "speaker_recognition": True,
            "command_timeout": 10.0,
            "sensitivity_levels": {
                "low": 0.3,
                "medium": 0.5,
                "high": 0.7,
                "max": 0.9
            }
        }
        self.logger.info("Voice processing initialized for hands-free operation")
    
    def _load_default_workflows(self):
        """Load default hands-free workflows"""
        default_workflows = {
            "engine_startup": [
                WorkflowStep(
                    step_id="engine_startup_01",
                    step_name="Pre-start checks",
                    voice_prompts=["Please confirm all pre-start checks complete"],
                    expected_responses=["checks complete", "all clear", "confirmed"],
                    gesture_alternatives=[GestureType.THUMBS_UP, GestureType.NOD_YES],
                    eye_gaze_alternatives=[EyeGazeZone.MIDDLE_CENTER],
                    timeout_seconds=30,
                    retry_attempts=2,
                    success_criteria="confirmation_received",
                    failure_actions=["request_manual_check", "alert_supervisor"]
                ),
                WorkflowStep(
                    step_id="engine_startup_02",
                    step_name="Start sequence",
                    voice_prompts=["Say 'start engine' to begin startup sequence"],
                    expected_responses=["start engine", "begin startup", "initiate"],
                    gesture_alternatives=[GestureType.POINT_UP, GestureType.FIST_CONFIRM],
                    eye_gaze_alternatives=[EyeGazeZone.TOP_CENTER],
                    timeout_seconds=15,
                    retry_attempts=1,
                    success_criteria="engine_started",
                    failure_actions=["abort_startup", "check_systems"]
                )
            ],
            "emergency_response": [
                WorkflowStep(
                    step_id="emergency_01",
                    step_name="Emergency type identification",
                    voice_prompts=["State the type of emergency"],
                    expected_responses=["fire", "medical", "collision", "flooding"],
                    gesture_alternatives=[GestureType.WAVE_ATTENTION],
                    eye_gaze_alternatives=[EyeGazeZone.TOP_LEFT],
                    timeout_seconds=5,
                    retry_attempts=0,
                    success_criteria="emergency_type_identified",
                    failure_actions=["general_alarm", "all_hands_alert"]
                )
            ],
            "navigation_check": [
                WorkflowStep(
                    step_id="nav_check_01",
                    step_name="Position verification",
                    voice_prompts=["Please verify current position"],
                    expected_responses=["position confirmed", "GPS good", "verified"],
                    gesture_alternatives=[GestureType.THUMBS_UP],
                    eye_gaze_alternatives=[EyeGazeZone.MIDDLE_CENTER],
                    timeout_seconds=20,
                    retry_attempts=1,
                    success_criteria="position_verified",
                    failure_actions=["request_manual_plot", "alert_navigation_officer"]
                )
            ]
        }
        
        for workflow_id, steps in default_workflows.items():
            self.workflows[workflow_id] = steps
            self._save_workflow_to_db(workflow_id, steps)
    
    def _save_workflow_to_db(self, workflow_id: str, steps: List[WorkflowStep]):
        """Save workflow to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        workflow_name = workflow_id.replace("_", " ").title()
        steps_data = [asdict(step) for step in steps]
        
        # Convert enums to strings
        for step_data in steps_data:
            if "gesture_alternatives" in step_data:
                step_data["gesture_alternatives"] = [g.value if hasattr(g, 'value') else str(g) for g in step_data["gesture_alternatives"]]
            if "eye_gaze_alternatives" in step_data:
                step_data["eye_gaze_alternatives"] = [z.value if hasattr(z, 'value') else str(z) for z in step_data["eye_gaze_alternatives"]]
        
        cursor.execute("""
            INSERT OR REPLACE INTO workflows 
            (workflow_id, workflow_name, description, steps, estimated_duration)
            VALUES (?, ?, ?, ?, ?)
        """, (
            workflow_id,
            workflow_name,
            f"Hands-free workflow for {workflow_name.lower()}",
            json.dumps(steps_data),
            sum(step.timeout_seconds for step in steps)
        ))
        
        conn.commit()
        conn.close()
    
    def _start_monitoring(self):
        """Start background monitoring for hands-free operations"""
        def monitor_loop():
            while True:
                try:
                    self._process_continuous_input()
                    self._update_session_metrics()
                    self._cleanup_expired_sessions()
                    time.sleep(0.1)  # 100ms monitoring cycle
                except Exception as e:
                    self.logger.error(f"Monitoring error: {e}")
                    time.sleep(1)
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
    
    def _process_continuous_input(self):
        """Process continuous voice, gesture, and gaze input"""
        # Simulate continuous processing
        # In real implementation, would process actual audio/video streams
        pass
    
    def _update_session_metrics(self):
        """Update metrics for active sessions"""
        current_time = datetime.now()
        
        with self.lock:
            for session in self.active_sessions.values():
                # Update last interaction time if recent activity
                if hasattr(self, '_recent_activity') and self._recent_activity:
                    session.last_interaction = current_time
    
    def _cleanup_expired_sessions(self):
        """Clean up expired hands-free sessions"""
        current_time = datetime.now()
        expired_sessions = []
        
        with self.lock:
            for session_id, session in self.active_sessions.items():
                # Mark sessions as expired after 1 hour of inactivity
                if (current_time - session.last_interaction).total_seconds() > 3600:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                self._end_session(session_id)
    
    async def start_hands_free_session(
        self, 
        user_id: str, 
        mode: HandsFreeMode = HandsFreeMode.VOICE_ONLY,
        environmental_context: str = "marine_bridge"
    ) -> str:
        """
        Start a hands-free operation session.
        
        Args:
            user_id: ID of the user starting the session
            mode: Hands-free operation mode
            environmental_context: Context for operation environment
            
        Returns:
            Session ID
        """
        session_id = f"hf_{user_id}_{int(time.time())}"
        current_time = datetime.now()
        
        # Load user calibration data
        calibration_data = await self._load_user_calibration(user_id)
        
        session = HandsFreeSession(
            session_id=session_id,
            user_id=user_id,
            mode=mode,
            started_at=current_time,
            last_interaction=current_time,
            total_commands=0,
            successful_commands=0,
            gesture_enabled=mode in [HandsFreeMode.VOICE_GESTURE, HandsFreeMode.FULL_MULTIMODAL],
            eye_tracking_enabled=mode in [HandsFreeMode.VOICE_EYE_TRACKING, HandsFreeMode.FULL_MULTIMODAL],
            voice_sensitivity=0.5,
            environmental_context=environmental_context,
            active_workflows=[],
            calibration_data=calibration_data
        )
        
        # Store session
        with self.lock:
            self.active_sessions[session_id] = session
        
        # Save to database
        self._save_session_to_db(session)
        
        # Perform initial calibration if needed
        await self._perform_initial_calibration(session)
        
        self.logger.info(f"Started hands-free session {session_id} for user {user_id} in mode {mode.value}")
        
        return session_id
    
    async def _load_user_calibration(self, user_id: str) -> Dict[str, Any]:
        """Load user calibration data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT calibration_type, calibration_values 
            FROM calibration_data 
            WHERE user_id = ? AND (expires_at IS NULL OR expires_at > datetime('now'))
        """, (user_id,))
        
        calibration_data = {}
        for calibration_type, values_json in cursor.fetchall():
            calibration_data[calibration_type] = json.loads(values_json)
        
        conn.close()
        return calibration_data
    
    async def _perform_initial_calibration(self, session: HandsFreeSession):
        """Perform initial calibration for new session"""
        calibrations_needed = []
        
        if session.gesture_enabled and "gesture" not in session.calibration_data:
            calibrations_needed.append("gesture")
        
        if session.eye_tracking_enabled and "eye_tracking" not in session.calibration_data:
            calibrations_needed.append("eye_tracking")
        
        if "voice" not in session.calibration_data:
            calibrations_needed.append("voice")
        
        for calibration_type in calibrations_needed:
            await self._run_calibration(session, calibration_type)
    
    async def _run_calibration(self, session: HandsFreeSession, calibration_type: str):
        """Run calibration for specific input type"""
        self.logger.info(f"Running {calibration_type} calibration for session {session.session_id}")
        
        calibration_results = {}
        
        if calibration_type == "voice":
            calibration_results = await self._calibrate_voice(session)
        elif calibration_type == "gesture":
            calibration_results = await self._calibrate_gesture(session)
        elif calibration_type == "eye_tracking":
            calibration_results = await self._calibrate_eye_tracking(session)
        
        # Store calibration results
        session.calibration_data[calibration_type] = calibration_results
        await self._save_user_calibration(session.user_id, calibration_type, calibration_results)
    
    async def _calibrate_voice(self, session: HandsFreeSession) -> Dict[str, Any]:
        """Calibrate voice recognition for user"""
        # Simulate voice calibration
        calibration_data = {
            "background_noise_level": 45.0,  # dB
            "user_voice_profile": f"profile_{session.user_id}",
            "optimal_sensitivity": 0.6,
            "voice_pitch_range": [80, 300],  # Hz
            "accent_adaptation": session.environmental_context,
            "calibrated_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Voice calibration completed for user {session.user_id}")
        return calibration_data
    
    async def _calibrate_gesture(self, session: HandsFreeSession) -> Dict[str, Any]:
        """Calibrate gesture recognition for user"""
        # Simulate gesture calibration
        calibration_data = {
            "hand_size_ratio": 1.0,
            "gesture_range": {"min_x": 0.2, "max_x": 0.8, "min_y": 0.2, "max_y": 0.8},
            "dominant_hand": "right",
            "gesture_speed": "medium",
            "lighting_conditions": session.environmental_context,
            "calibrated_gestures": [g.value for g in GestureType],
            "calibrated_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Gesture calibration completed for user {session.user_id}")
        return calibration_data
    
    async def _calibrate_eye_tracking(self, session: HandsFreeSession) -> Dict[str, Any]:
        """Calibrate eye tracking for user"""
        # Simulate eye tracking calibration
        calibration_data = {
            "eye_distance": 65.0,  # cm from screen
            "gaze_zone_offsets": {zone.value: {"x": 0, "y": 0} for zone in EyeGazeZone},
            "blink_threshold": 150,  # ms
            "fixation_duration": 500,  # ms
            "accuracy_score": 0.85,
            "calibrated_at": datetime.now().isoformat()
        }
        
        self.logger.info(f"Eye tracking calibration completed for user {session.user_id}")
        return calibration_data
    
    async def _save_user_calibration(self, user_id: str, calibration_type: str, calibration_data: Dict[str, Any]):
        """Save user calibration data"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Set expiration to 30 days from now
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        cursor.execute("""
            INSERT OR REPLACE INTO calibration_data 
            (user_id, calibration_type, calibration_values, expires_at)
            VALUES (?, ?, ?, ?)
        """, (
            user_id,
            calibration_type,
            json.dumps(calibration_data),
            expires_at
        ))
        
        conn.commit()
        conn.close()
    
    async def process_multimodal_input(
        self, 
        session_id: str, 
        voice_input: Optional[str] = None,
        gesture_data: Optional[Dict[str, Any]] = None,
        gaze_data: Optional[Dict[str, Any]] = None
    ) -> VoiceGesturePair:
        """
        Process multimodal input (voice + gesture + gaze).
        
        Args:
            session_id: Active session ID
            voice_input: Voice command text
            gesture_data: Gesture recognition data
            gaze_data: Eye gaze tracking data
            
        Returns:
            VoiceGesturePair with combined interpretation
        """
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        current_time = datetime.now()
        
        # Process voice input
        voice_confidence = 0.0
        if voice_input:
            voice_confidence = await self._analyze_voice_confidence(voice_input, session)
        
        # Process gesture input
        gesture_type = None
        gesture_confidence = 0.0
        if gesture_data and session.gesture_enabled:
            gesture_type, gesture_confidence = await self._analyze_gesture(gesture_data, session)
        
        # Process gaze input
        gaze_zone = None
        gaze_confidence = 0.0
        if gaze_data and session.eye_tracking_enabled:
            gaze_zone, gaze_confidence = await self._analyze_gaze(gaze_data, session)
        
        # Combine inputs for intent recognition
        combined_intent = await self._combine_multimodal_intent(
            voice_input, gesture_type, gaze_zone, session
        )
        
        # Create voice-gesture pair
        pair = VoiceGesturePair(
            voice_command=voice_input or "",
            gesture_type=gesture_type,
            eye_gaze_zone=gaze_zone,
            confidence_voice=voice_confidence,
            confidence_gesture=gesture_confidence,
            confidence_gaze=gaze_confidence,
            timestamp=current_time,
            combined_intent=combined_intent,
            requires_confirmation=self._requires_confirmation(combined_intent)
        )
        
        # Store pair
        self.voice_gesture_pairs.append(pair)
        
        # Update session
        session.total_commands += 1
        session.last_interaction = current_time
        
        # Save to database
        self._save_voice_gesture_pair(session_id, pair)
        
        self.logger.info(f"Processed multimodal input: '{combined_intent}' (confidences: V={voice_confidence:.2f}, G={gesture_confidence:.2f}, E={gaze_confidence:.2f})")
        
        return pair
    
    async def _analyze_voice_confidence(self, voice_input: str, session: HandsFreeSession) -> float:
        """Analyze voice input confidence"""
        # Simulate voice analysis based on calibration and environmental factors
        base_confidence = 0.8
        
        # Adjust for environmental context
        if session.environmental_context in ["engine_room", "deck_high_wind"]:
            base_confidence -= 0.2
        
        # Adjust for voice calibration
        voice_calibration = session.calibration_data.get("voice", {})
        if voice_calibration:
            optimal_sensitivity = voice_calibration.get("optimal_sensitivity", 0.5)
            base_confidence += (optimal_sensitivity - 0.5) * 0.2
        
        # Adjust for command clarity
        if len(voice_input.split()) < 2:
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    async def _analyze_gesture(self, gesture_data: Dict[str, Any], session: HandsFreeSession) -> Tuple[Optional[GestureType], float]:
        """Analyze gesture input"""
        # Simulate gesture analysis
        detected_gesture = gesture_data.get("detected_gesture")
        confidence = gesture_data.get("confidence", 0.0)
        
        if detected_gesture and confidence > 0.7:
            try:
                gesture_type = GestureType(detected_gesture)
                return gesture_type, confidence
            except ValueError:
                pass
        
        return None, 0.0
    
    async def _analyze_gaze(self, gaze_data: Dict[str, Any], session: HandsFreeSession) -> Tuple[Optional[EyeGazeZone], float]:
        """Analyze eye gaze input"""
        # Simulate gaze analysis
        detected_zone = gaze_data.get("gaze_zone")
        confidence = gaze_data.get("confidence", 0.0)
        fixation_duration = gaze_data.get("fixation_duration", 0)
        
        # Require minimum fixation duration
        if detected_zone and confidence > 0.8 and fixation_duration > 300:
            try:
                gaze_zone = EyeGazeZone(detected_zone)
                return gaze_zone, confidence
            except ValueError:
                pass
        
        return None, 0.0
    
    async def _combine_multimodal_intent(
        self, 
        voice: Optional[str], 
        gesture: Optional[GestureType], 
        gaze: Optional[EyeGazeZone],
        session: HandsFreeSession
    ) -> str:
        """Combine multimodal inputs to determine intent"""
        intents = []
        
        # Voice intent
        if voice:
            voice_intent = voice.lower().strip().replace(" ", "_")
            intents.append(f"voice:{voice_intent}")
        
        # Gesture intent
        if gesture:
            gesture_intent = self._gesture_to_intent(gesture)
            intents.append(f"gesture:{gesture_intent}")
        
        # Gaze intent
        if gaze:
            gaze_intent = self._gaze_to_intent(gaze)
            intents.append(f"gaze:{gaze_intent}")
        
        # Combine intents with priority
        if voice and gesture:
            # Voice + gesture combinations
            if gesture == GestureType.NOD_YES and "confirm" in voice.lower():
                return "confirmed_yes"
            elif gesture == GestureType.SHAKE_NO and any(word in voice.lower() for word in ["no", "cancel", "stop"]):
                return "confirmed_no"
            elif gesture in [GestureType.POINT_LEFT, GestureType.POINT_RIGHT] and "turn" in voice.lower():
                direction = "left" if gesture == GestureType.POINT_LEFT else "right"
                return f"turn_{direction}_gesture_confirmed"
        
        # Default combined intent
        return "_".join(intents) if intents else "unknown_intent"
    
    def _gesture_to_intent(self, gesture: GestureType) -> str:
        """Convert gesture to intent"""
        gesture_intents = {
            GestureType.NOD_YES: "yes",
            GestureType.SHAKE_NO: "no",
            GestureType.POINT_LEFT: "left",
            GestureType.POINT_RIGHT: "right",
            GestureType.POINT_UP: "up",
            GestureType.POINT_DOWN: "down",
            GestureType.THUMBS_UP: "approve",
            GestureType.THUMBS_DOWN: "reject",
            GestureType.OPEN_PALM_STOP: "stop",
            GestureType.FIST_CONFIRM: "confirm",
            GestureType.WAVE_ATTENTION: "attention"
        }
        return gesture_intents.get(gesture, "unknown_gesture")
    
    def _gaze_to_intent(self, gaze: EyeGazeZone) -> str:
        """Convert gaze to intent"""
        gaze_intents = {
            EyeGazeZone.TOP_LEFT: "menu",
            EyeGazeZone.TOP_CENTER: "status",
            EyeGazeZone.TOP_RIGHT: "alerts",
            EyeGazeZone.MIDDLE_LEFT: "navigation",
            EyeGazeZone.MIDDLE_CENTER: "main_display",
            EyeGazeZone.MIDDLE_RIGHT: "controls",
            EyeGazeZone.BOTTOM_LEFT: "settings",
            EyeGazeZone.BOTTOM_CENTER: "commands",
            EyeGazeZone.BOTTOM_RIGHT: "help"
        }
        return gaze_intents.get(gaze, "unknown_gaze")
    
    def _requires_confirmation(self, intent: str) -> bool:
        """Determine if intent requires confirmation"""
        high_risk_intents = [
            "emergency", "stop", "shutdown", "override", "delete",
            "confirmed_yes", "confirmed_no", "turn_left_gesture_confirmed",
            "turn_right_gesture_confirmed"
        ]
        
        return any(risk_intent in intent.lower() for risk_intent in high_risk_intents)
    
    async def execute_hands_free_workflow(self, session_id: str, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a hands-free workflow.
        
        Args:
            session_id: Active session ID
            workflow_id: Workflow to execute
            
        Returns:
            Workflow execution results
        """
        if session_id not in self.active_sessions:
            return {"success": False, "message": "Session not found"}
        
        if workflow_id not in self.workflows:
            return {"success": False, "message": "Workflow not found"}
        
        session = self.active_sessions[session_id]
        workflow_steps = self.workflows[workflow_id]
        
        # Add to active workflows
        session.active_workflows.append(workflow_id)
        
        results = {
            "success": True,
            "workflow_id": workflow_id,
            "total_steps": len(workflow_steps),
            "completed_steps": 0,
            "step_results": [],
            "start_time": datetime.now().isoformat()
        }
        
        self.logger.info(f"Starting hands-free workflow '{workflow_id}' for session {session_id}")
        
        for i, step in enumerate(workflow_steps):
            step_result = await self._execute_workflow_step(session, step, i + 1)
            results["step_results"].append(step_result)
            
            if step_result["success"]:
                results["completed_steps"] += 1
            else:
                # Handle step failure
                if step.retry_attempts > 0:
                    # Retry logic would go here
                    pass
                else:
                    # Execute failure actions
                    for action in step.failure_actions:
                        await self._execute_failure_action(action, session, step)
                    break
        
        # Remove from active workflows
        if workflow_id in session.active_workflows:
            session.active_workflows.remove(workflow_id)
        
        results["end_time"] = datetime.now().isoformat()
        results["success"] = results["completed_steps"] == results["total_steps"]
        
        self.logger.info(f"Completed workflow '{workflow_id}': {results['completed_steps']}/{results['total_steps']} steps")
        
        return results
    
    async def _execute_workflow_step(self, session: HandsFreeSession, step: WorkflowStep, step_number: int) -> Dict[str, Any]:
        """Execute a single workflow step"""
        self.logger.info(f"Executing step {step_number}: {step.step_name}")
        
        # Present voice prompts
        for prompt in step.voice_prompts:
            # In real implementation, would use TTS to speak prompt
            self.logger.info(f"Voice prompt: {prompt}")
        
        # Wait for response with timeout
        start_time = time.time()
        response_received = False
        
        while time.time() - start_time < step.timeout_seconds and not response_received:
            # Simulate waiting for multimodal response
            await asyncio.sleep(0.5)
            
            # In real implementation, would process actual input
            # For demo, randomly succeed after some time
            if time.time() - start_time > step.timeout_seconds / 2:
                response_received = True
        
        step_result = {
            "step_id": step.step_id,
            "step_name": step.step_name,
            "success": response_received,
            "duration": time.time() - start_time,
            "response_method": "voice" if response_received else "timeout"
        }
        
        if response_received:
            session.successful_commands += 1
        
        return step_result
    
    async def _execute_failure_action(self, action: str, session: HandsFreeSession, step: WorkflowStep):
        """Execute failure action for workflow step"""
        self.logger.warning(f"Executing failure action: {action} for step {step.step_name}")
        
        # In real implementation, would execute actual failure recovery actions
        if action == "alert_supervisor":
            # Send alert to supervisor
            pass
        elif action == "request_manual_check":
            # Request manual verification
            pass
        elif action == "abort_startup":
            # Abort startup sequence
            pass
    
    def _save_session_to_db(self, session: HandsFreeSession):
        """Save session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO hands_free_sessions 
            (session_id, user_id, mode, started_at, total_commands, successful_commands,
             gesture_enabled, eye_tracking_enabled, voice_sensitivity, environmental_context,
             calibration_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.session_id,
            session.user_id,
            session.mode.value,
            session.started_at.isoformat(),
            session.total_commands,
            session.successful_commands,
            session.gesture_enabled,
            session.eye_tracking_enabled,
            session.voice_sensitivity,
            session.environmental_context,
            json.dumps(session.calibration_data)
        ))
        
        conn.commit()
        conn.close()
    
    def _save_voice_gesture_pair(self, session_id: str, pair: VoiceGesturePair):
        """Save voice-gesture pair to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO voice_gesture_pairs 
            (session_id, voice_command, gesture_type, eye_gaze_zone, confidence_voice,
             confidence_gesture, confidence_gaze, timestamp, combined_intent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            pair.voice_command,
            pair.gesture_type.value if pair.gesture_type else None,
            pair.eye_gaze_zone.value if pair.eye_gaze_zone else None,
            pair.confidence_voice,
            pair.confidence_gesture,
            pair.confidence_gaze,
            pair.timestamp.isoformat(),
            pair.combined_intent
        ))
        
        conn.commit()
        conn.close()
    
    def _end_session(self, session_id: str):
        """End a hands-free session"""
        if session_id in self.active_sessions:
            session = self.active_sessions[session_id]
            
            # Update database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE hands_free_sessions 
                SET ended_at = ?, total_commands = ?, successful_commands = ?
                WHERE session_id = ?
            """, (
                datetime.now().isoformat(),
                session.total_commands,
                session.successful_commands,
                session_id
            ))
            
            conn.commit()
            conn.close()
            
            # Remove from active sessions
            del self.active_sessions[session_id]
            
            self.logger.info(f"Ended hands-free session {session_id}")
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status of hands-free session"""
        if session_id not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "mode": session.mode.value,
            "started_at": session.started_at.isoformat(),
            "last_interaction": session.last_interaction.isoformat(),
            "total_commands": session.total_commands,
            "successful_commands": session.successful_commands,
            "success_rate": (session.successful_commands / session.total_commands * 100) if session.total_commands > 0 else 0,
            "gesture_enabled": session.gesture_enabled,
            "eye_tracking_enabled": session.eye_tracking_enabled,
            "active_workflows": session.active_workflows,
            "environmental_context": session.environmental_context
        }
    
    def get_hands_free_statistics(self) -> Dict[str, Any]:
        """Get hands-free system statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Session statistics
        cursor.execute("SELECT COUNT(*) FROM hands_free_sessions")
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute("SELECT mode, COUNT(*) FROM hands_free_sessions GROUP BY mode")
        mode_distribution = dict(cursor.fetchall())
        
        # Command statistics
        cursor.execute("SELECT SUM(total_commands), SUM(successful_commands) FROM hands_free_sessions")
        command_stats = cursor.fetchone()
        total_commands = command_stats[0] or 0
        successful_commands = command_stats[1] or 0
        success_rate = (successful_commands / total_commands * 100) if total_commands > 0 else 0
        
        # Multimodal usage
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN gesture_type IS NOT NULL THEN 1 END) as gesture_usage,
                COUNT(CASE WHEN eye_gaze_zone IS NOT NULL THEN 1 END) as gaze_usage,
                COUNT(*) as total_interactions
            FROM voice_gesture_pairs
        """)
        multimodal_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "active_sessions": len(self.active_sessions),
            "mode_distribution": mode_distribution,
            "total_commands": total_commands,
            "command_success_rate": round(success_rate, 2),
            "gesture_usage_rate": round((multimodal_stats[0] / multimodal_stats[2] * 100) if multimodal_stats[2] > 0 else 0, 2),
            "gaze_usage_rate": round((multimodal_stats[1] / multimodal_stats[2] * 100) if multimodal_stats[2] > 0 else 0, 2),
            "available_workflows": len(self.workflows),
            "gesture_detection_enabled": self.gesture_detector.get("initialized", False),
            "eye_tracking_enabled": self.eye_tracker.get("initialized", False)
        }


# Example usage and testing
async def main():
    """Example usage of hands-free operation system"""
    hands_free = HandsFreeOperator()
    
    # Start a hands-free session
    session_id = await hands_free.start_hands_free_session(
        user_id="bridge_officer_1",
        mode=HandsFreeMode.FULL_MULTIMODAL,
        environmental_context="bridge"
    )
    
    print(f"Started hands-free session: {session_id}")
    
    # Test multimodal inputs
    test_inputs = [
        {
            "voice_input": "turn left 15 degrees",
            "gesture_data": {"detected_gesture": "point_left", "confidence": 0.85},
            "gaze_data": {"gaze_zone": "middle_center", "confidence": 0.90, "fixation_duration": 600}
        },
        {
            "voice_input": "confirm engine start",
            "gesture_data": {"detected_gesture": "thumbs_up", "confidence": 0.92},
            "gaze_data": None
        },
        {
            "voice_input": "emergency stop",
            "gesture_data": {"detected_gesture": "open_palm_stop", "confidence": 0.88},
            "gaze_data": {"gaze_zone": "top_right", "confidence": 0.85, "fixation_duration": 800}
        }
    ]
    
    for i, input_data in enumerate(test_inputs):
        print(f"\n=== Testing multimodal input {i+1} ===")
        
        pair = await hands_free.process_multimodal_input(
            session_id,
            input_data.get("voice_input"),
            input_data.get("gesture_data"),
            input_data.get("gaze_data")
        )
        
        print(f"Combined intent: {pair.combined_intent}")
        print(f"Confidences - Voice: {pair.confidence_voice:.2f}, Gesture: {pair.confidence_gesture:.2f}, Gaze: {pair.confidence_gaze:.2f}")
        print(f"Requires confirmation: {pair.requires_confirmation}")
    
    # Test workflow execution
    print(f"\n=== Testing workflow execution ===")
    workflow_result = await hands_free.execute_hands_free_workflow(session_id, "engine_startup")
    print(f"Workflow result: {workflow_result}")
    
    # Get session status
    status = hands_free.get_session_status(session_id)
    print(f"\nSession status: {status}")
    
    # Get statistics
    stats = hands_free.get_hands_free_statistics()
    print(f"System statistics: {stats}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())