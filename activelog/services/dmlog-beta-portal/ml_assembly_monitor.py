#!/usr/bin/env python3
"""
ML Assembly Monitor - Bot Assembly Learning System
=================================================

Advanced ML system that monitors bot assembly processes to generate
superior training material for bot improvement. Creates feedback loops
between assembly success and bot training optimization.

Key Features:
- Real-time assembly pattern analysis
- Success/failure correlation with bot configurations
- Automated training data generation and curation
- Adaptive learning from assembly outcomes
- Progressive bot improvement through assembly insights
"""

import asyncio
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict, deque
from enum import Enum
import logging
import pickle
import sqlite3
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
import joblib

logger = logging.getLogger(__name__)

class AssemblyPhase(Enum):
    """Phases of bot assembly process"""
    INITIALIZATION = "initialization"
    COMPONENT_SELECTION = "component_selection"
    CONFIGURATION = "configuration"
    INTEGRATION = "integration"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"

class AssemblyOutcome(Enum):
    """Assembly outcome classifications"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

class LearningObjective(Enum):
    """Types of learning objectives for bot training"""
    PERFORMANCE_OPTIMIZATION = "performance_optimization"
    ERROR_REDUCTION = "error_reduction"
    RESOURCE_EFFICIENCY = "resource_efficiency"
    INTEGRATION_IMPROVEMENT = "integration_improvement"
    PATTERN_RECOGNITION = "pattern_recognition"

@dataclass
class AssemblyEvent:
    """Individual event during bot assembly"""
    event_id: str
    assembly_id: str
    bot_id: str
    phase: AssemblyPhase
    timestamp: float
    duration_ms: float
    parameters: Dict[str, Any]
    outcome: str
    metrics: Dict[str, float]
    context: Dict[str, Any]

@dataclass
class AssemblySession:
    """Complete bot assembly session"""
    session_id: str
    bot_type: str
    bot_configuration: Dict[str, Any]
    start_time: float
    end_time: float
    total_duration_ms: float
    events: List[AssemblyEvent]
    final_outcome: AssemblyOutcome
    performance_metrics: Dict[str, float]
    success_indicators: Dict[str, float]
    failure_reasons: List[str]
    lessons_learned: Dict[str, Any]

@dataclass
class TrainingPattern:
    """Extracted pattern for bot training"""
    pattern_id: str
    pattern_type: LearningObjective
    source_assemblies: List[str]
    feature_vector: np.ndarray
    target_outcome: float
    confidence_score: float
    applicable_contexts: List[str]
    training_weight: float
    creation_time: float

@dataclass
class BotTrainingMaterial:
    """Curated training material for bot improvement"""
    material_id: str
    bot_type: str
    learning_objective: LearningObjective
    training_patterns: List[TrainingPattern]
    feature_descriptions: List[str]
    success_examples: List[Dict[str, Any]]
    failure_examples: List[Dict[str, Any]]
    optimization_recommendations: List[str]
    estimated_improvement: float
    validation_score: float

class AssemblyDataCollector:
    """Collects and processes assembly data for ML analysis"""
    
    def __init__(self, db_path: str = "/tmp/assembly_monitoring.db"):
        self.db_path = db_path
        self.active_sessions: Dict[str, AssemblySession] = {}
        self.event_buffer = deque(maxlen=10000)
        self.session_buffer = deque(maxlen=1000)
        
        # Initialize database
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize SQLite database for assembly data"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS assembly_sessions (
                    session_id TEXT PRIMARY KEY,
                    bot_type TEXT,
                    bot_configuration TEXT,
                    start_time REAL,
                    end_time REAL,
                    total_duration_ms REAL,
                    final_outcome TEXT,
                    performance_metrics TEXT,
                    success_indicators TEXT,
                    failure_reasons TEXT,
                    lessons_learned TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS assembly_events (
                    event_id TEXT PRIMARY KEY,
                    assembly_id TEXT,
                    bot_id TEXT,
                    phase TEXT,
                    timestamp REAL,
                    duration_ms REAL,
                    parameters TEXT,
                    outcome TEXT,
                    metrics TEXT,
                    context TEXT,
                    FOREIGN KEY(assembly_id) REFERENCES assembly_sessions(session_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS training_patterns (
                    pattern_id TEXT PRIMARY KEY,
                    pattern_type TEXT,
                    source_assemblies TEXT,
                    feature_vector BLOB,
                    target_outcome REAL,
                    confidence_score REAL,
                    applicable_contexts TEXT,
                    training_weight REAL,
                    creation_time REAL
                )
            ''')
    
    def start_assembly_session(self, session_id: str, bot_type: str, 
                             bot_configuration: Dict[str, Any]) -> bool:
        """Start monitoring a new assembly session"""
        if session_id in self.active_sessions:
            logger.warning(f"Assembly session {session_id} already active")
            return False
        
        session = AssemblySession(
            session_id=session_id,
            bot_type=bot_type,
            bot_configuration=bot_configuration,
            start_time=time.time(),
            end_time=0.0,
            total_duration_ms=0.0,
            events=[],
            final_outcome=AssemblyOutcome.SUCCESS,  # Default, will be updated
            performance_metrics={},
            success_indicators={},
            failure_reasons=[],
            lessons_learned={}
        )
        
        self.active_sessions[session_id] = session
        logger.info(f"Started assembly monitoring for session: {session_id}")
        return True
    
    def log_assembly_event(self, session_id: str, bot_id: str, phase: AssemblyPhase,
                          duration_ms: float, parameters: Dict[str, Any],
                          outcome: str, metrics: Dict[str, float],
                          context: Dict[str, Any] = None) -> str:
        """Log an assembly event"""
        if session_id not in self.active_sessions:
            logger.error(f"No active session found: {session_id}")
            return ""
        
        event_id = f"evt_{session_id}_{len(self.active_sessions[session_id].events)}"
        
        event = AssemblyEvent(
            event_id=event_id,
            assembly_id=session_id,
            bot_id=bot_id,
            phase=phase,
            timestamp=time.time(),
            duration_ms=duration_ms,
            parameters=parameters,
            outcome=outcome,
            metrics=metrics,
            context=context or {}
        )
        
        # Add to session and buffer
        self.active_sessions[session_id].events.append(event)
        self.event_buffer.append(event)
        
        return event_id
    
    def complete_assembly_session(self, session_id: str, final_outcome: AssemblyOutcome,
                                performance_metrics: Dict[str, float],
                                failure_reasons: List[str] = None) -> bool:
        """Complete an assembly session with final results"""
        if session_id not in self.active_sessions:
            logger.error(f"No active session found: {session_id}")
            return False
        
        session = self.active_sessions[session_id]
        session.end_time = time.time()
        session.total_duration_ms = (session.end_time - session.start_time) * 1000
        session.final_outcome = final_outcome
        session.performance_metrics = performance_metrics
        session.failure_reasons = failure_reasons or []
        
        # Calculate success indicators
        session.success_indicators = self._calculate_success_indicators(session)
        
        # Extract lessons learned
        session.lessons_learned = self._extract_lessons_learned(session)
        
        # Save to database
        self._save_session_to_db(session)
        
        # Move to completed buffer
        self.session_buffer.append(session)
        del self.active_sessions[session_id]
        
        logger.info(f"Completed assembly session: {session_id} -> {final_outcome.value}")
        return True
    
    def _calculate_success_indicators(self, session: AssemblySession) -> Dict[str, float]:
        """Calculate success indicators for the assembly session"""
        indicators = {}
        
        if not session.events:
            return indicators
        
        # Phase completion rate
        phases_attempted = set(event.phase for event in session.events)
        total_phases = len(AssemblyPhase)
        indicators['phase_completion_rate'] = len(phases_attempted) / total_phases
        
        # Average event success rate
        successful_events = sum(1 for event in session.events if event.outcome == 'success')
        indicators['event_success_rate'] = successful_events / len(session.events)
        
        # Performance efficiency
        total_duration = sum(event.duration_ms for event in session.events)
        if total_duration > 0:
            indicators['time_efficiency'] = 1.0 / (total_duration / 1000.0)  # Inverse of total seconds
        
        # Error density
        error_events = sum(1 for event in session.events if 'error' in event.outcome.lower())
        indicators['error_density'] = error_events / len(session.events)
        
        # Integration complexity handling
        integration_events = [e for e in session.events if e.phase == AssemblyPhase.INTEGRATION]
        if integration_events:
            avg_integration_time = np.mean([e.duration_ms for e in integration_events])
            indicators['integration_efficiency'] = 1.0 / (avg_integration_time / 100.0)  # Normalized
        
        return indicators
    
    def _extract_lessons_learned(self, session: AssemblySession) -> Dict[str, Any]:
        """Extract lessons learned from assembly session"""
        lessons = {}
        
        # Performance patterns
        if session.performance_metrics:
            lessons['performance_insights'] = {
                'peak_performance': max(session.performance_metrics.values()),
                'performance_variance': np.var(list(session.performance_metrics.values())),
                'performance_trend': 'improving' if list(session.performance_metrics.values())[-1] > list(session.performance_metrics.values())[0] else 'declining'
            }
        
        # Phase-specific insights
        phase_performance = defaultdict(list)
        for event in session.events:
            phase_performance[event.phase.value].append(event.duration_ms)
        
        lessons['phase_insights'] = {}
        for phase, durations in phase_performance.items():
            lessons['phase_insights'][phase] = {
                'avg_duration': np.mean(durations),
                'consistency': 1.0 / (np.std(durations) + 1),  # Higher = more consistent
                'success_rate': sum(1 for event in session.events 
                                  if event.phase.value == phase and event.outcome == 'success') / len(durations)
            }
        
        # Configuration effectiveness
        config_score = session.success_indicators.get('event_success_rate', 0.5)
        lessons['configuration_effectiveness'] = {
            'overall_score': config_score,
            'recommended_changes': self._suggest_config_changes(session),
            'strengths': self._identify_config_strengths(session),
            'weaknesses': self._identify_config_weaknesses(session)
        }
        
        return lessons
    
    def _suggest_config_changes(self, session: AssemblySession) -> List[str]:
        """Suggest configuration changes based on session analysis"""
        suggestions = []
        
        # Analyze failure patterns
        if session.final_outcome != AssemblyOutcome.SUCCESS:
            error_phases = [event.phase.value for event in session.events if 'error' in event.outcome.lower()]
            if error_phases:
                most_common_error_phase = max(set(error_phases), key=error_phases.count)
                suggestions.append(f"Focus on improving {most_common_error_phase} phase reliability")
        
        # Performance optimization suggestions
        slow_phases = []
        phase_times = defaultdict(list)
        for event in session.events:
            phase_times[event.phase.value].append(event.duration_ms)
        
        for phase, times in phase_times.items():
            if np.mean(times) > 1000:  # Slower than 1 second average
                slow_phases.append(phase)
        
        if slow_phases:
            suggestions.append(f"Optimize performance in phases: {', '.join(slow_phases)}")
        
        return suggestions
    
    def _identify_config_strengths(self, session: AssemblySession) -> List[str]:
        """Identify configuration strengths"""
        strengths = []
        
        # High success rate phases
        phase_success = defaultdict(list)
        for event in session.events:
            phase_success[event.phase.value].append(event.outcome == 'success')
        
        for phase, successes in phase_success.items():
            success_rate = sum(successes) / len(successes)
            if success_rate > 0.9:  # 90%+ success rate
                strengths.append(f"Excellent {phase} phase reliability")
        
        # Fast execution phases
        phase_times = defaultdict(list)
        for event in session.events:
            phase_times[event.phase.value].append(event.duration_ms)
        
        for phase, times in phase_times.items():
            if np.mean(times) < 100:  # Faster than 100ms average
                strengths.append(f"Efficient {phase} phase execution")
        
        return strengths
    
    def _identify_config_weaknesses(self, session: AssemblySession) -> List[str]:
        """Identify configuration weaknesses"""
        weaknesses = []
        
        # Low success rate phases
        phase_success = defaultdict(list)
        for event in session.events:
            phase_success[event.phase.value].append(event.outcome == 'success')
        
        for phase, successes in phase_success.items():
            success_rate = sum(successes) / len(successes)
            if success_rate < 0.7:  # Less than 70% success rate
                weaknesses.append(f"Low {phase} phase reliability ({success_rate:.1%})")
        
        # High error density
        error_density = session.success_indicators.get('error_density', 0)
        if error_density > 0.2:  # More than 20% error rate
            weaknesses.append(f"High error density ({error_density:.1%})")
        
        return weaknesses
    
    def _save_session_to_db(self, session: AssemblySession):
        """Save completed session to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Save session
                conn.execute('''
                    INSERT OR REPLACE INTO assembly_sessions
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    session.session_id,
                    session.bot_type,
                    json.dumps(session.bot_configuration),
                    session.start_time,
                    session.end_time,
                    session.total_duration_ms,
                    session.final_outcome.value,
                    json.dumps(session.performance_metrics),
                    json.dumps(session.success_indicators),
                    json.dumps(session.failure_reasons),
                    json.dumps(session.lessons_learned)
                ))
                
                # Save events
                for event in session.events:
                    conn.execute('''
                        INSERT OR REPLACE INTO assembly_events
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.event_id,
                        event.assembly_id,
                        event.bot_id,
                        event.phase.value,
                        event.timestamp,
                        event.duration_ms,
                        json.dumps(event.parameters),
                        event.outcome,
                        json.dumps(event.metrics),
                        json.dumps(event.context)
                    ))
                
        except Exception as e:
            logger.error(f"Error saving session to database: {e}")
    
    async def _simulate_historical_data(self, num_sessions: int = 5):
        """Simulate historical assembly data for demonstration purposes"""
        try:
            import random
            current_time = time.time()
            
            for i in range(num_sessions):
                # Create simulated session
                session_id = f"sim_{int(current_time)}_{i}"
                bot_config = {
                    'optimization_goal': random.choice(['performance', 'resource_efficiency', 'error_reduction']),
                    'target_components': [f'comp_{j}' for j in range(random.randint(2, 5))],
                    'complexity_score': random.uniform(0.3, 0.9)
                }
                
                # Start session
                await self.monitor_bot_assembly(session_id, 'imaginary_bot', bot_config)
                
                # Add some events
                events = ['initialization', 'validation', 'optimization', 'finalization']
                for event in events:
                    success_prob = 0.8 if bot_config['complexity_score'] < 0.6 else 0.6
                    success = random.random() < success_prob
                    
                    await self.log_assembly_step(session_id, f'bot_{i}', event, 
                                               random.uniform(50, 200), success, {
                        'resource_usage': random.uniform(0.2, 0.8)
                    })
                
                # End session
                overall_success = random.random() < (0.9 if bot_config['complexity_score'] < 0.5 else 0.7)
                await self.complete_assembly(session_id, overall_success, {
                    'final_score': random.uniform(0.6, 0.95) if overall_success else random.uniform(0.3, 0.6)
                })
                
                # Offset time slightly for each session
                current_time -= random.uniform(300, 1800)  # 5-30 minutes ago
                
            logger.info(f"✅ Simulated {num_sessions} historical assembly sessions")
            
        except Exception as e:
            logger.error(f"Error simulating historical data: {e}")

class MLPatternExtractor:
    """Extract ML patterns from assembly data for training"""
    
    def __init__(self, data_collector: AssemblyDataCollector):
        self.data_collector = data_collector
        self.feature_extractors = {
            LearningObjective.PERFORMANCE_OPTIMIZATION: self._extract_performance_features,
            LearningObjective.ERROR_REDUCTION: self._extract_error_features,
            LearningObjective.RESOURCE_EFFICIENCY: self._extract_resource_features,
            LearningObjective.INTEGRATION_IMPROVEMENT: self._extract_integration_features,
            LearningObjective.PATTERN_RECOGNITION: self._extract_pattern_features
        }
        
        # ML models for different objectives
        self.models = {}
        self.scalers = {}
        
    def extract_training_patterns(self, objective: LearningObjective,
                                min_sessions: int = 10) -> List[TrainingPattern]:
        """Extract training patterns for specific learning objective"""
        
        # Get relevant sessions from database
        sessions = self._load_sessions_from_db(min_sessions * 2)  # Load extra for filtering
        
        if len(sessions) < min_sessions:
            logger.warning(f"Not enough sessions for pattern extraction: {len(sessions)} < {min_sessions}")
            return []
        
        patterns = []
        feature_extractor = self.feature_extractors.get(objective)
        
        if not feature_extractor:
            logger.error(f"No feature extractor for objective: {objective}")
            return []
        
        for session in sessions:
            try:
                # Extract features for this session
                features = feature_extractor(session)
                
                # Calculate target outcome based on objective
                target = self._calculate_target_outcome(session, objective)
                
                # Calculate confidence score
                confidence = self._calculate_pattern_confidence(session, objective)
                
                if confidence > 0.5:  # Only include confident patterns
                    pattern = TrainingPattern(
                        pattern_id=f"pattern_{objective.value}_{session.session_id}",
                        pattern_type=objective,
                        source_assemblies=[session.session_id],
                        feature_vector=np.array(features),
                        target_outcome=target,
                        confidence_score=confidence,
                        applicable_contexts=[session.bot_type],
                        training_weight=confidence,
                        creation_time=time.time()
                    )
                    patterns.append(pattern)
                    
            except Exception as e:
                logger.error(f"Error extracting pattern from session {session.session_id}: {e}")
        
        logger.info(f"Extracted {len(patterns)} training patterns for {objective.value}")
        return patterns
    
    def _load_sessions_from_db(self, limit: int = 100) -> List[AssemblySession]:
        """Load assembly sessions from database"""
        sessions = []
        
        try:
            with sqlite3.connect(self.data_collector.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM assembly_sessions
                    ORDER BY end_time DESC
                    LIMIT ?
                ''', (limit,))
                
                for row in cursor.fetchall():
                    session = AssemblySession(
                        session_id=row[0],
                        bot_type=row[1],
                        bot_configuration=json.loads(row[2]),
                        start_time=row[3],
                        end_time=row[4],
                        total_duration_ms=row[5],
                        events=[],  # Will load separately if needed
                        final_outcome=AssemblyOutcome(row[6]),
                        performance_metrics=json.loads(row[7]),
                        success_indicators=json.loads(row[8]),
                        failure_reasons=json.loads(row[9]),
                        lessons_learned=json.loads(row[10])
                    )
                    sessions.append(session)
                    
        except Exception as e:
            logger.error(f"Error loading sessions from database: {e}")
        
        return sessions
    
    def _extract_performance_features(self, session: AssemblySession) -> List[float]:
        """Extract features for performance optimization"""
        features = []
        
        # Basic session metrics
        features.append(session.total_duration_ms / 1000.0)  # Total time in seconds
        features.append(len(session.events))  # Number of events
        features.append(session.success_indicators.get('event_success_rate', 0.0))
        features.append(session.success_indicators.get('phase_completion_rate', 0.0))
        features.append(session.success_indicators.get('time_efficiency', 0.0))
        
        # Performance metrics (pad to fixed size)
        perf_values = list(session.performance_metrics.values())[:5]
        while len(perf_values) < 5:
            perf_values.append(0.0)
        features.extend(perf_values)
        
        # Configuration complexity (simple heuristic)
        config_complexity = len(str(session.bot_configuration)) / 1000.0  # Normalized
        features.append(config_complexity)
        
        return features
    
    def _extract_error_features(self, session: AssemblySession) -> List[float]:
        """Extract features for error reduction"""
        features = []
        
        # Error-specific metrics
        features.append(session.success_indicators.get('error_density', 0.0))
        features.append(len(session.failure_reasons))
        features.append(1.0 if session.final_outcome == AssemblyOutcome.FAILURE else 0.0)
        
        # Add performance features as well (errors often correlate with performance)
        features.extend(self._extract_performance_features(session)[:5])
        
        return features
    
    def _extract_resource_features(self, session: AssemblySession) -> List[float]:
        """Extract features for resource efficiency"""
        features = []
        
        # Resource utilization proxies
        features.append(session.total_duration_ms / 1000.0)  # Time is a resource
        features.append(session.success_indicators.get('time_efficiency', 0.0))
        features.append(len(session.events))  # Event count as complexity measure
        
        # Configuration size as resource complexity
        config_size = len(json.dumps(session.bot_configuration))
        features.append(config_size / 1000.0)  # Normalized
        
        # Success efficiency (success per unit time)
        success_rate = session.success_indicators.get('event_success_rate', 0.0)
        time_factor = session.total_duration_ms / 1000.0 if session.total_duration_ms > 0 else 1.0
        features.append(success_rate / time_factor)
        
        return features
    
    def _extract_integration_features(self, session: AssemblySession) -> List[float]:
        """Extract features for integration improvement"""
        features = []
        
        # Integration-specific metrics
        features.append(session.success_indicators.get('integration_efficiency', 0.0))
        features.append(session.success_indicators.get('phase_completion_rate', 0.0))
        
        # Add performance features for integration context
        features.extend(self._extract_performance_features(session)[:6])
        
        return features
    
    def _extract_pattern_features(self, session: AssemblySession) -> List[float]:
        """Extract features for pattern recognition"""
        features = []
        
        # Pattern-related metrics
        features.append(session.success_indicators.get('event_success_rate', 0.0))
        features.append(len(set(session.failure_reasons)))  # Unique failure types
        
        # Lessons learned complexity
        lessons_complexity = len(str(session.lessons_learned)) / 1000.0
        features.append(lessons_complexity)
        
        # Add base performance features
        features.extend(self._extract_performance_features(session)[:5])
        
        return features
    
    def _calculate_target_outcome(self, session: AssemblySession, 
                                objective: LearningObjective) -> float:
        """Calculate target outcome based on learning objective"""
        
        if objective == LearningObjective.PERFORMANCE_OPTIMIZATION:
            # Target: time efficiency (higher is better)
            return session.success_indicators.get('time_efficiency', 0.0)
            
        elif objective == LearningObjective.ERROR_REDUCTION:
            # Target: inverse of error density (higher is better)
            error_density = session.success_indicators.get('error_density', 1.0)
            return max(0.0, 1.0 - error_density)
            
        elif objective == LearningObjective.RESOURCE_EFFICIENCY:
            # Target: success rate per unit time
            success_rate = session.success_indicators.get('event_success_rate', 0.0)
            time_factor = session.total_duration_ms / 1000.0 if session.total_duration_ms > 0 else 1.0
            return success_rate / max(0.1, time_factor)
            
        elif objective == LearningObjective.INTEGRATION_IMPROVEMENT:
            # Target: integration efficiency
            return session.success_indicators.get('integration_efficiency', 0.0)
            
        elif objective == LearningObjective.PATTERN_RECOGNITION:
            # Target: overall success score
            return session.success_indicators.get('event_success_rate', 0.0)
        
        return 0.0
    
    def _calculate_pattern_confidence(self, session: AssemblySession,
                                    objective: LearningObjective) -> float:
        """Calculate confidence in the extracted pattern"""
        confidence_factors = []
        
        # Session completeness
        if session.final_outcome != AssemblyOutcome.TIMEOUT:
            confidence_factors.append(0.3)  # Complete sessions are more reliable
        
        # Event count (more events = more data = higher confidence)
        event_count_factor = min(1.0, len(session.events) / 10.0)  # Normalize to 10 events
        confidence_factors.append(event_count_factor * 0.2)
        
        # Success indicators completeness
        indicator_count = len([v for v in session.success_indicators.values() if v > 0])
        indicator_factor = indicator_count / 5.0  # Assuming 5 key indicators
        confidence_factors.append(indicator_factor * 0.3)
        
        # Objective-specific confidence
        if objective == LearningObjective.PERFORMANCE_OPTIMIZATION:
            if 'time_efficiency' in session.success_indicators:
                confidence_factors.append(0.2)
        elif objective == LearningObjective.ERROR_REDUCTION:
            if session.failure_reasons:  # Have failure data to learn from
                confidence_factors.append(0.2)
        
        return sum(confidence_factors)

class TrainingMaterialGenerator:
    """Generate curated training materials from ML patterns"""
    
    def __init__(self, pattern_extractor: MLPatternExtractor):
        self.pattern_extractor = pattern_extractor
        self.material_cache = {}
        
    def generate_training_material(self, bot_type: str, objective: LearningObjective,
                                 min_patterns: int = 20) -> Optional[BotTrainingMaterial]:
        """Generate comprehensive training material for bot type and objective"""
        
        # Extract patterns
        patterns = self.pattern_extractor.extract_training_patterns(objective, min_patterns)
        
        if len(patterns) < min_patterns:
            logger.warning(f"Not enough patterns for training material: {len(patterns)} < {min_patterns}")
            return None
        
        # Filter patterns for specific bot type
        relevant_patterns = [p for p in patterns if bot_type in p.applicable_contexts]
        
        if len(relevant_patterns) < min_patterns // 2:
            logger.info(f"Using general patterns for {bot_type} (not enough specific patterns)")
            relevant_patterns = patterns[:min_patterns]  # Use general patterns
        
        # Generate success/failure examples
        success_examples = self._generate_success_examples(relevant_patterns)
        failure_examples = self._generate_failure_examples(relevant_patterns)
        
        # Generate optimization recommendations
        recommendations = self._generate_recommendations(relevant_patterns, objective)
        
        # Calculate estimated improvement
        estimated_improvement = self._estimate_improvement_potential(relevant_patterns)
        
        # Validate training material
        validation_score = self._validate_training_material(relevant_patterns)
        
        # Create feature descriptions
        feature_descriptions = self._create_feature_descriptions(objective)
        
        material = BotTrainingMaterial(
            material_id=f"training_{bot_type}_{objective.value}_{int(time.time())}",
            bot_type=bot_type,
            learning_objective=objective,
            training_patterns=relevant_patterns,
            feature_descriptions=feature_descriptions,
            success_examples=success_examples,
            failure_examples=failure_examples,
            optimization_recommendations=recommendations,
            estimated_improvement=estimated_improvement,
            validation_score=validation_score
        )
        
        # Cache for future use
        cache_key = f"{bot_type}_{objective.value}"
        self.material_cache[cache_key] = material
        
        logger.info(f"Generated training material for {bot_type}/{objective.value}: "
                   f"{len(relevant_patterns)} patterns, {validation_score:.2f} validation score")
        
        return material
    
    def _generate_success_examples(self, patterns: List[TrainingPattern]) -> List[Dict[str, Any]]:
        """Generate success examples from high-performing patterns"""
        success_examples = []
        
        # Sort patterns by target outcome (higher is better for success examples)
        sorted_patterns = sorted(patterns, key=lambda x: x.target_outcome, reverse=True)
        
        for pattern in sorted_patterns[:5]:  # Top 5 success examples
            example = {
                'pattern_id': pattern.pattern_id,
                'features': pattern.feature_vector.tolist(),
                'outcome_score': pattern.target_outcome,
                'confidence': pattern.confidence_score,
                'key_insights': self._extract_key_insights(pattern),
                'recommended_approach': self._recommend_approach(pattern)
            }
            success_examples.append(example)
        
        return success_examples
    
    def _generate_failure_examples(self, patterns: List[TrainingPattern]) -> List[Dict[str, Any]]:
        """Generate failure examples from low-performing patterns"""
        failure_examples = []
        
        # Sort patterns by target outcome (lower for failure examples)
        sorted_patterns = sorted(patterns, key=lambda x: x.target_outcome)
        
        for pattern in sorted_patterns[:3]:  # Top 3 failure examples
            example = {
                'pattern_id': pattern.pattern_id,
                'features': pattern.feature_vector.tolist(),
                'outcome_score': pattern.target_outcome,
                'confidence': pattern.confidence_score,
                'failure_indicators': self._identify_failure_indicators(pattern),
                'avoidance_strategies': self._suggest_avoidance_strategies(pattern)
            }
            failure_examples.append(example)
        
        return failure_examples
    
    def _generate_recommendations(self, patterns: List[TrainingPattern],
                                objective: LearningObjective) -> List[str]:
        """Generate optimization recommendations based on patterns"""
        recommendations = []
        
        # Analyze feature importance
        feature_analysis = self._analyze_feature_importance(patterns)
        
        # Generate objective-specific recommendations
        if objective == LearningObjective.PERFORMANCE_OPTIMIZATION:
            recommendations.extend([
                "Focus on reducing total assembly time through parallel processing",
                "Optimize phase transition efficiency to minimize overhead",
                "Implement caching for repeated operations within assemblies"
            ])
            
        elif objective == LearningObjective.ERROR_REDUCTION:
            recommendations.extend([
                "Implement robust validation at each assembly phase",
                "Add retry mechanisms for transient failures",
                "Improve error detection and early intervention"
            ])
            
        elif objective == LearningObjective.RESOURCE_EFFICIENCY:
            recommendations.extend([
                "Optimize resource allocation based on assembly complexity",
                "Implement dynamic scaling based on workload patterns",
                "Cache and reuse expensive computations"
            ])
        
        # Add pattern-specific recommendations
        if feature_analysis:
            most_important_feature = max(feature_analysis, key=feature_analysis.get)
            recommendations.append(f"Focus optimization efforts on feature: {most_important_feature}")
        
        return recommendations
    
    def _analyze_feature_importance(self, patterns: List[TrainingPattern]) -> Dict[str, float]:
        """Analyze which features are most important for outcomes"""
        if len(patterns) < 5:
            return {}
        
        try:
            # Prepare data for analysis
            X = np.array([p.feature_vector for p in patterns])
            y = np.array([p.target_outcome for p in patterns])
            
            # Use random forest for feature importance
            rf = RandomForestClassifier(n_estimators=50, random_state=42)
            
            # Convert continuous targets to discrete classes for classification
            y_discrete = np.digitize(y, bins=np.percentile(y, [33, 66]))
            
            rf.fit(X, y_discrete)
            
            # Get feature importance
            feature_importance = {}
            for i, importance in enumerate(rf.feature_importances_):
                feature_importance[f"feature_{i}"] = importance
            
            return feature_importance
            
        except Exception as e:
            logger.error(f"Error analyzing feature importance: {e}")
            return {}
    
    def _estimate_improvement_potential(self, patterns: List[TrainingPattern]) -> float:
        """Estimate potential improvement from training material"""
        if not patterns:
            return 0.0
        
        # Calculate improvement potential based on pattern variance
        outcomes = [p.target_outcome for p in patterns]
        
        if len(outcomes) < 2:
            return 0.0
        
        # Improvement potential based on gap between best and average performance
        best_outcome = max(outcomes)
        avg_outcome = np.mean(outcomes)
        
        if avg_outcome == 0:
            return 0.0
        
        improvement_potential = (best_outcome - avg_outcome) / avg_outcome
        return min(1.0, improvement_potential)  # Cap at 100%
    
    def _validate_training_material(self, patterns: List[TrainingPattern]) -> float:
        """Validate quality of training material"""
        if not patterns:
            return 0.0
        
        validation_factors = []
        
        # Pattern count factor
        count_factor = min(1.0, len(patterns) / 50.0)  # Normalize to 50 patterns
        validation_factors.append(count_factor * 0.3)
        
        # Confidence factor
        avg_confidence = np.mean([p.confidence_score for p in patterns])
        validation_factors.append(avg_confidence * 0.4)
        
        # Diversity factor (based on feature variance)
        features = np.array([p.feature_vector for p in patterns])
        if features.size > 0:
            feature_variance = np.mean(np.var(features, axis=0))
            diversity_factor = min(1.0, feature_variance)
            validation_factors.append(diversity_factor * 0.3)
        
        return sum(validation_factors)
    
    def _create_feature_descriptions(self, objective: LearningObjective) -> List[str]:
        """Create human-readable descriptions of features"""
        base_descriptions = [
            "Total assembly duration (seconds)",
            "Number of assembly events",
            "Event success rate",
            "Phase completion rate",
            "Time efficiency score"
        ]
        
        if objective == LearningObjective.PERFORMANCE_OPTIMIZATION:
            base_descriptions.extend([
                "Peak performance metric",
                "Performance variance",
                "Configuration complexity",
                "Resource utilization efficiency",
                "Optimization potential score"
            ])
        elif objective == LearningObjective.ERROR_REDUCTION:
            base_descriptions.extend([
                "Error density",
                "Number of failure reasons",
                "Failure outcome indicator",
                "Error pattern consistency",
                "Recovery success rate"
            ])
        
        return base_descriptions
    
    def _extract_key_insights(self, pattern: TrainingPattern) -> List[str]:
        """Extract key insights from successful patterns"""
        insights = []
        
        # Analyze feature vector for insights
        features = pattern.feature_vector
        
        if len(features) > 0:
            if features[0] < 5.0:  # Fast assembly time
                insights.append("Fast assembly execution (< 5 seconds)")
            
            if len(features) > 2 and features[2] > 0.9:  # High success rate
                insights.append("High event success rate (> 90%)")
            
            if len(features) > 4 and features[4] > 0.8:  # High efficiency
                insights.append("Excellent time efficiency")
        
        if pattern.confidence_score > 0.8:
            insights.append("High-confidence pattern suitable for replication")
        
        return insights
    
    def _recommend_approach(self, pattern: TrainingPattern) -> str:
        """Recommend approach based on successful pattern"""
        if pattern.target_outcome > 0.8:
            return "Replicate this configuration and approach for similar scenarios"
        elif pattern.target_outcome > 0.6:
            return "Use as baseline with minor optimizations"
        else:
            return "Study for understanding but avoid direct replication"
    
    def _identify_failure_indicators(self, pattern: TrainingPattern) -> List[str]:
        """Identify indicators that predict failure"""
        indicators = []
        
        features = pattern.feature_vector
        
        if len(features) > 0 and features[0] > 30.0:  # Very slow
            indicators.append("Excessive assembly duration (> 30 seconds)")
        
        if len(features) > 2 and features[2] < 0.5:  # Low success rate
            indicators.append("Low event success rate (< 50%)")
        
        if pattern.confidence_score < 0.3:
            indicators.append("Low confidence in pattern reliability")
        
        return indicators
    
    def _suggest_avoidance_strategies(self, pattern: TrainingPattern) -> List[str]:
        """Suggest strategies to avoid failure patterns"""
        strategies = []
        
        # Based on failure indicators, suggest opposite strategies
        features = pattern.feature_vector
        
        if len(features) > 0 and features[0] > 20.0:
            strategies.append("Implement timeout mechanisms and parallel processing")
        
        if len(features) > 2 and features[2] < 0.6:
            strategies.append("Add validation steps and error handling")
        
        strategies.append("Monitor these indicators during assembly and intervene early")
        
        return strategies

class MLAssemblyMonitor:
    """Main ML Assembly Monitor orchestrating all components"""
    
    def __init__(self, db_path: str = "/tmp/assembly_monitoring.db"):
        self.data_collector = AssemblyDataCollector(db_path)
        self.pattern_extractor = MLPatternExtractor(self.data_collector)
        self.material_generator = TrainingMaterialGenerator(self.pattern_extractor)
        
        self.active_monitoring = False
        self.training_materials = {}
        
    async def start_monitoring(self):
        """Start ML assembly monitoring"""
        self.active_monitoring = True
        logger.info("🤖 ML Assembly Monitor started")
    
    async def stop_monitoring(self):
        """Stop ML assembly monitoring"""
        self.active_monitoring = False
        logger.info("🛑 ML Assembly Monitor stopped")
    
    async def monitor_bot_assembly(self, session_id: str, bot_type: str,
                                 bot_configuration: Dict[str, Any]) -> bool:
        """Start monitoring a bot assembly process"""
        if not self.active_monitoring:
            return False
        
        return self.data_collector.start_assembly_session(session_id, bot_type, bot_configuration)
    
    async def log_assembly_step(self, session_id: str, bot_id: str, phase: AssemblyPhase,
                              duration_ms: float, success: bool,
                              metrics: Dict[str, float] = None,
                              context: Dict[str, Any] = None) -> bool:
        """Log an individual assembly step"""
        if not self.active_monitoring:
            return False
        
        outcome = "success" if success else "failure"
        event_id = self.data_collector.log_assembly_event(
            session_id, bot_id, phase, duration_ms,
            context or {}, outcome, metrics or {}, context or {}
        )
        
        return bool(event_id)
    
    async def complete_assembly(self, session_id: str, success: bool,
                              performance_metrics: Dict[str, float],
                              failure_reasons: List[str] = None) -> bool:
        """Complete assembly monitoring and extract lessons"""
        if not self.active_monitoring:
            return False
        
        final_outcome = AssemblyOutcome.SUCCESS if success else AssemblyOutcome.FAILURE
        
        return self.data_collector.complete_assembly_session(
            session_id, final_outcome, performance_metrics, failure_reasons
        )
    
    async def generate_training_materials(self, bot_type: str,
                                        objectives: List[LearningObjective] = None) -> Dict[str, BotTrainingMaterial]:
        """Generate training materials for specified objectives"""
        if objectives is None:
            objectives = list(LearningObjective)
        
        materials = {}
        
        for objective in objectives:
            material = self.material_generator.generate_training_material(bot_type, objective)
            if material:
                materials[objective.value] = material
                self.training_materials[f"{bot_type}_{objective.value}"] = material
        
        logger.info(f"Generated {len(materials)} training materials for {bot_type}")
        return materials
    
    async def get_training_recommendations(self, bot_type: str) -> Dict[str, Any]:
        """Get comprehensive training recommendations for a bot type"""
        recommendations = {
            'bot_type': bot_type,
            'timestamp': time.time(),
            'materials_available': [],
            'priority_objectives': [],
            'estimated_improvements': {},
            'implementation_suggestions': []
        }
        
        # Check available training materials
        for key, material in self.training_materials.items():
            if bot_type in key:
                recommendations['materials_available'].append({
                    'objective': material.learning_objective.value,
                    'pattern_count': len(material.training_patterns),
                    'validation_score': material.validation_score,
                    'estimated_improvement': material.estimated_improvement
                })
        
        # Determine priority objectives based on validation scores and improvement potential
        material_scores = []
        for material_info in recommendations['materials_available']:
            score = material_info['validation_score'] * material_info['estimated_improvement']
            material_scores.append((material_info['objective'], score))
        
        # Sort by score and take top priorities
        material_scores.sort(key=lambda x: x[1], reverse=True)
        recommendations['priority_objectives'] = [obj for obj, score in material_scores[:3]]
        
        # Implementation suggestions
        if material_scores:
            top_objective = material_scores[0][0]
            recommendations['implementation_suggestions'] = [
                f"Start with {top_objective} training - highest impact potential",
                "Implement incremental training with validation checkpoints",
                "Monitor assembly performance before and after training updates",
                "Use A/B testing to validate training effectiveness"
            ]
        
        return recommendations
    
    def get_monitoring_statistics(self) -> Dict[str, Any]:
        """Get comprehensive monitoring statistics"""
        return {
            'active_monitoring': self.active_monitoring,
            'active_sessions': len(self.data_collector.active_sessions),
            'completed_sessions': len(self.data_collector.session_buffer),
            'total_events': len(self.data_collector.event_buffer),
            'training_materials_generated': len(self.training_materials),
            'available_objectives': [obj.value for obj in LearningObjective]
        }

# Global ML assembly monitor
ml_assembly_monitor = MLAssemblyMonitor()

# Easy integration functions
async def start_ml_monitoring():
    """Start ML assembly monitoring"""
    await ml_assembly_monitor.start_monitoring()

async def stop_ml_monitoring():
    """Stop ML assembly monitoring"""
    await ml_assembly_monitor.stop_monitoring()

async def monitor_bot_assembly(session_id: str, bot_type: str, bot_config: Dict[str, Any]) -> bool:
    """Monitor a bot assembly process"""
    return await ml_assembly_monitor.monitor_bot_assembly(session_id, bot_type, bot_config)

async def log_assembly_step(session_id: str, bot_id: str, phase: str,
                          duration_ms: float, success: bool,
                          metrics: Dict[str, float] = None) -> bool:
    """Log an assembly step"""
    phase_enum = AssemblyPhase(phase)
    return await ml_assembly_monitor.log_assembly_step(
        session_id, bot_id, phase_enum, duration_ms, success, metrics
    )

async def complete_assembly_monitoring(session_id: str, success: bool,
                                     performance_metrics: Dict[str, float]) -> bool:
    """Complete assembly monitoring"""
    return await ml_assembly_monitor.complete_assembly(session_id, success, performance_metrics)

async def generate_bot_training_materials(bot_type: str) -> Dict[str, Any]:
    """Generate training materials for a bot type"""
    return await ml_assembly_monitor.generate_training_materials(bot_type)

async def initialize_ml_assembly_monitor(db_path: str = "/tmp/assembly_monitoring.db") -> MLAssemblyMonitor:
    """Initialize and return ML Assembly Monitor instance"""
    monitor = MLAssemblyMonitor(db_path)
    await monitor.start_monitoring()
    return monitor

if __name__ == "__main__":
    # Test the ML Assembly Monitor
    async def test_ml_monitoring():
        print("🧪 Testing ML Assembly Monitor")
        print("=" * 50)
        
        # Start monitoring
        await start_ml_monitoring()
        
        # Simulate bot assembly process
        session_id = "test_assembly_001"
        bot_type = "file_processor_bot"
        bot_config = {"threads": 4, "batch_size": 100, "timeout": 30}
        
        print(f"📊 Starting assembly monitoring: {session_id}")
        await monitor_bot_assembly(session_id, bot_type, bot_config)
        
        # Simulate assembly steps
        phases = [
            ("initialization", 150.0, True, {"cpu_usage": 0.2}),
            ("component_selection", 200.0, True, {"selected_components": 5}),
            ("configuration", 100.0, True, {"config_complexity": 0.6}),
            ("integration", 300.0, True, {"integration_points": 3}),
            ("validation", 80.0, True, {"tests_passed": 15}),
            ("deployment", 120.0, True, {"deployment_success": 1.0})
        ]
        
        for phase, duration, success, metrics in phases:
            await log_assembly_step(session_id, bot_type, phase, duration, success, metrics)
            print(f"   ✅ {phase}: {duration}ms ({'success' if success else 'failure'})")
        
        # Complete assembly
        performance_metrics = {
            "overall_performance": 0.85,
            "resource_efficiency": 0.78,
            "integration_score": 0.92
        }
        
        await complete_assembly_monitoring(session_id, True, performance_metrics)
        print(f"✅ Assembly completed successfully")
        
        # Generate multiple sessions for pattern extraction
        for i in range(5):
            sim_session_id = f"sim_assembly_{i:03d}"
            await monitor_bot_assembly(sim_session_id, bot_type, bot_config)
            
            for phase, duration, success, metrics in phases:
                # Add some variance
                var_duration = duration + (i * 20) - 40
                var_success = success and (i != 2)  # Make one fail
                await log_assembly_step(sim_session_id, bot_type, phase, var_duration, var_success, metrics)
            
            var_performance = {k: v + (i * 0.05) - 0.1 for k, v in performance_metrics.items()}
            await complete_assembly_monitoring(sim_session_id, var_success, var_performance)
        
        print(f"📊 Generated 6 assembly sessions for analysis")
        
        # Generate training materials
        print(f"🤖 Generating training materials...")
        training_materials = await generate_bot_training_materials(bot_type)
        
        for objective, material in training_materials.items():
            print(f"   📚 {objective}: {len(material.training_patterns)} patterns, "
                  f"validation={material.validation_score:.2f}, "
                  f"improvement={material.estimated_improvement:.2f}")
        
        # Get recommendations
        recommendations = await ml_assembly_monitor.get_training_recommendations(bot_type)
        print(f"\n🎯 Training Recommendations:")
        print(f"   Priority objectives: {recommendations['priority_objectives']}")
        for suggestion in recommendations['implementation_suggestions']:
            print(f"   💡 {suggestion}")
        
        # Show statistics
        stats = ml_assembly_monitor.get_monitoring_statistics()
        print(f"\n📊 Monitoring Statistics:")
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # Stop monitoring
        await stop_ml_monitoring()
        
        print("\n✅ ML Assembly Monitor test completed!")
    
    asyncio.run(test_ml_monitoring())