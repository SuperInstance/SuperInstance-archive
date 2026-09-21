"""
ActiveLog Education AI Suite - Educational Game Generation

Advanced AI-powered system for creating dynamic, curriculum-aligned educational games
that adapt to learning objectives, student skill levels, and engagement patterns.
"""

import asyncio
import json
import uuid
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import numpy as np
from pathlib import Path
import sqlite3

class GameType(Enum):
    QUIZ = "quiz"
    PUZZLE = "puzzle"
    ADVENTURE = "adventure"
    SIMULATION = "simulation"
    STRATEGY = "strategy"
    WORD_GAME = "word_game"
    MATH_GAME = "math_game"
    SCIENCE_LAB = "science_lab"
    HISTORY_TIMELINE = "history_timeline"
    LANGUAGE_IMMERSION = "language_immersion"
    CODING_CHALLENGE = "coding_challenge"
    ART_CREATION = "art_creation"

class GameMechanic(Enum):
    POINTS = "points"
    LEVELS = "levels"
    BADGES = "badges"
    LEADERBOARD = "leaderboard"
    TIME_CHALLENGE = "time_challenge"
    COLLABORATION = "collaboration"
    COMPETITION = "competition"
    STORY_PROGRESSION = "story_progression"
    RESOURCE_MANAGEMENT = "resource_management"
    EXPLORATION = "exploration"

class DifficultyAdaptation(Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"
    PLAYER_CONTROLLED = "player_controlled"
    AI_DRIVEN = "ai_driven"

@dataclass
class GameElement:
    element_id: str
    element_type: str  # question, obstacle, reward, character, etc.
    content: Dict[str, Any]
    difficulty_level: float  # 0.0 to 1.0
    learning_objectives: List[str]
    estimated_time: int  # seconds
    prerequisites: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class GameTemplate:
    template_id: str
    name: str
    game_type: GameType
    description: str
    target_subjects: List[str]
    grade_levels: List[int]
    mechanics: List[GameMechanic]
    base_elements: List[GameElement]
    rules: Dict[str, Any]
    customization_options: Dict[str, Any]
    accessibility_features: List[str] = field(default_factory=list)

@dataclass 
class GeneratedGame:
    game_id: str
    title: str
    description: str
    game_type: GameType
    template_id: str
    learning_objectives: List[str]
    target_students: List[str]
    difficulty_range: Tuple[float, float]
    estimated_duration: int  # minutes
    game_elements: List[GameElement]
    mechanics: List[GameMechanic]
    scoring_system: Dict[str, Any]
    adaptation_rules: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class GameSession:
    session_id: str
    game_id: str
    student_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    current_level: int = 1
    score: float = 0.0
    progress: float = 0.0  # 0.0 to 1.0
    actions: List[Dict[str, Any]] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    difficulties_encountered: List[str] = field(default_factory=list)
    engagement_metrics: Dict[str, float] = field(default_factory=dict)

class EducationalGameGenerator:
    """Advanced educational game generation system"""
    
    def __init__(self, database_path: str = "/home/activeloguser/activelog/data/education_games.db"):
        self.db_path = database_path
        self.templates: Dict[str, GameTemplate] = {}
        self.generated_games: Dict[str, GeneratedGame] = {}
        self.active_sessions: Dict[str, GameSession] = {}
        
        # AI models for content generation
        self.difficulty_predictor = None
        self.engagement_predictor = None
        
        # Game element libraries
        self.question_banks: Dict[str, List[Dict]] = {}
        self.story_elements: Dict[str, List[Dict]] = {}
        self.visual_assets: Dict[str, List[str]] = {}
        
        # Initialize database and load templates
        asyncio.create_task(self.initialize())
    
    async def initialize(self):
        """Initialize the game generator system"""
        await self.setup_database()
        await self.load_game_templates()
        await self.load_content_libraries()
        print("Educational Game Generator initialized")
    
    async def setup_database(self):
        """Setup SQLite database for game data"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Game templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_templates (
                template_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                game_type TEXT NOT NULL,
                description TEXT,
                config JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Generated games table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_games (
                game_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                template_id TEXT,
                config JSON,
                learning_objectives JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (template_id) REFERENCES game_templates (template_id)
            )
        ''')
        
        # Game sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_sessions (
                session_id TEXT PRIMARY KEY,
                game_id TEXT,
                student_id TEXT,
                session_data JSON,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES generated_games (game_id)
            )
        ''')
        
        # Game analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS game_analytics (
                analytics_id TEXT PRIMARY KEY,
                game_id TEXT,
                student_id TEXT,
                metrics JSON,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES generated_games (game_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def load_game_templates(self):
        """Load predefined game templates"""
        # Math Quiz Game Template
        math_quiz_template = GameTemplate(
            template_id="math_quiz_basic",
            name="Math Quiz Adventure",
            game_type=GameType.QUIZ,
            description="Interactive math quiz with progressive difficulty",
            target_subjects=["mathematics", "arithmetic", "algebra"],
            grade_levels=list(range(1, 13)),
            mechanics=[GameMechanic.POINTS, GameMechanic.LEVELS, GameMechanic.TIME_CHALLENGE],
            base_elements=[],
            rules={
                "scoring": {"correct_answer": 10, "time_bonus": 5, "streak_multiplier": 1.5},
                "progression": {"questions_per_level": 5, "difficulty_increase": 0.1},
                "time_limits": {"easy": 30, "medium": 20, "hard": 15}
            },
            customization_options={
                "topics": ["addition", "subtraction", "multiplication", "division", "fractions"],
                "difficulty_adaptation": True,
                "hints_available": True,
                "visual_aids": True
            }
        )
        
        # Science Lab Simulation Template
        science_lab_template = GameTemplate(
            template_id="science_lab_sim",
            name="Virtual Science Laboratory",
            game_type=GameType.SIMULATION,
            description="Interactive science experiments and hypothesis testing",
            target_subjects=["chemistry", "physics", "biology"],
            grade_levels=list(range(6, 13)),
            mechanics=[GameMechanic.EXPLORATION, GameMechanic.RESOURCE_MANAGEMENT, GameMechanic.BADGES],
            base_elements=[],
            rules={
                "safety": {"required_equipment": True, "safety_protocols": True},
                "experimentation": {"hypothesis_required": True, "data_collection": True},
                "analysis": {"conclusion_writing": True, "peer_review": True}
            },
            customization_options={
                "experiment_types": ["chemical_reactions", "physics_mechanics", "biology_cells"],
                "complexity_levels": ["basic", "intermediate", "advanced"],
                "collaboration": True
            }
        )
        
        # Language Learning Adventure Template
        language_adventure_template = GameTemplate(
            template_id="language_adventure",
            name="Language Learning Quest",
            game_type=GameType.ADVENTURE,
            description="Story-driven language learning with cultural immersion",
            target_subjects=["english", "spanish", "french", "mandarin", "german"],
            grade_levels=list(range(1, 13)),
            mechanics=[GameMechanic.STORY_PROGRESSION, GameMechanic.BADGES, GameMechanic.COLLABORATION],
            base_elements=[],
            rules={
                "vocabulary": {"words_per_level": 10, "repetition_required": 3},
                "grammar": {"structure_practice": True, "contextual_usage": True},
                "culture": {"cultural_context": True, "real_world_scenarios": True}
            },
            customization_options={
                "languages": ["english", "spanish", "french", "mandarin"],
                "cultural_themes": ["food", "travel", "family", "school"],
                "difficulty_progression": "adaptive"
            }
        )
        
        # History Timeline Game Template
        history_timeline_template = GameTemplate(
            template_id="history_timeline",
            name="History Timeline Challenge",
            game_type=GameType.STRATEGY,
            description="Build historical timelines and understand cause-effect relationships",
            target_subjects=["history", "social_studies"],
            grade_levels=list(range(4, 13)),
            mechanics=[GameMechanic.STRATEGY, GameMechanic.POINTS, GameMechanic.LEADERBOARD],
            base_elements=[],
            rules={
                "timeline": {"chronological_accuracy": True, "cause_effect": True},
                "research": {"source_verification": True, "multiple_perspectives": True},
                "presentation": {"multimedia": True, "storytelling": True}
            },
            customization_options={
                "time_periods": ["ancient", "medieval", "renaissance", "modern", "contemporary"],
                "regions": ["world", "americas", "europe", "asia", "africa"],
                "themes": ["political", "social", "cultural", "technological"]
            }
        )
        
        # Coding Challenge Template
        coding_challenge_template = GameTemplate(
            template_id="coding_challenge",
            name="Programming Puzzle Master",
            game_type=GameType.CODING_CHALLENGE,
            description="Learn programming through interactive challenges and projects",
            target_subjects=["computer_science", "programming", "logic"],
            grade_levels=list(range(6, 13)),
            mechanics=[GameMechanic.LEVELS, GameMechanic.BADGES, GameMechanic.COLLABORATION],
            base_elements=[],
            rules={
                "progression": {"concept_mastery": True, "project_based": True},
                "debugging": {"error_analysis": True, "problem_solving": True},
                "collaboration": {"pair_programming": True, "code_review": True}
            },
            customization_options={
                "languages": ["scratch", "python", "javascript", "java"],
                "concepts": ["variables", "loops", "functions", "algorithms"],
                "project_types": ["games", "web_apps", "data_analysis", "robotics"]
            }
        )
        
        # Store templates
        templates = [
            math_quiz_template,
            science_lab_template,
            language_adventure_template,
            history_timeline_template,
            coding_challenge_template
        ]
        
        for template in templates:
            self.templates[template.template_id] = template
    
    async def load_content_libraries(self):
        """Load content libraries for game generation"""
        # Math question bank
        self.question_banks["mathematics"] = [
            {
                "type": "multiple_choice",
                "question": "What is 15 + 27?",
                "options": ["42", "41", "43", "40"],
                "correct_answer": "42",
                "difficulty": 0.3,
                "topic": "addition"
            },
            {
                "type": "fill_blank",
                "question": "If a rectangle has length 8 and width 5, its area is ___",
                "correct_answer": "40",
                "difficulty": 0.5,
                "topic": "geometry"
            },
            {
                "type": "word_problem",
                "question": "Sarah has 24 stickers. She gives 1/3 to her brother and 1/4 to her sister. How many stickers does she have left?",
                "correct_answer": "10",
                "difficulty": 0.7,
                "topic": "fractions"
            }
        ]
        
        # Science experiment library
        self.question_banks["science"] = [
            {
                "type": "experiment",
                "title": "Plant Growth Experiment",
                "description": "Investigate factors affecting plant growth",
                "materials": ["seeds", "pots", "soil", "water", "light_source"],
                "procedure": ["plant_seeds", "control_variables", "observe_daily", "record_data"],
                "difficulty": 0.4,
                "subject": "biology"
            },
            {
                "type": "virtual_lab",
                "title": "Chemical Reaction Simulation",
                "description": "Explore acid-base reactions safely",
                "chemicals": ["hcl", "naoh", "indicator"],
                "safety_notes": ["wear_goggles", "use_fume_hood", "proper_disposal"],
                "difficulty": 0.6,
                "subject": "chemistry"
            }
        ]
        
        # Story elements for adventure games
        self.story_elements["adventure"] = [
            {
                "type": "character",
                "name": "Professor Wisdom",
                "role": "mentor",
                "personality": "encouraging, knowledgeable, patient",
                "dialogue_style": "socratic_questioning"
            },
            {
                "type": "setting",
                "name": "Ancient Library",
                "description": "A magical library where knowledge comes alive",
                "interactions": ["book_quests", "riddle_doors", "knowledge_gems"],
                "atmosphere": "mysterious, scholarly, inspiring"
            },
            {
                "type": "challenge",
                "name": "Logic Puzzle Door",
                "description": "Solve puzzles to unlock new areas",
                "mechanics": ["pattern_recognition", "logical_reasoning", "trial_error"],
                "rewards": ["new_abilities", "story_progression", "achievement_badges"]
            }
        ]
    
    async def generate_game(self, learning_objectives: List[str], 
                           target_students: List[str],
                           preferences: Optional[Dict[str, Any]] = None) -> GeneratedGame:
        """Generate a customized educational game"""
        # Analyze learning objectives to determine best template
        template = await self.select_optimal_template(learning_objectives, preferences)
        
        # Analyze student profiles for personalization
        student_profiles = await self.analyze_student_profiles(target_students)
        
        # Generate game content
        game_elements = await self.generate_game_elements(
            template, learning_objectives, student_profiles
        )
        
        # Create adaptive difficulty system
        difficulty_range = self.calculate_difficulty_range(student_profiles)
        adaptation_rules = self.create_adaptation_rules(template, student_profiles)
        
        # Generate game
        game = GeneratedGame(
            game_id=str(uuid.uuid4()),
            title=await self.generate_game_title(template, learning_objectives),
            description=await self.generate_game_description(template, learning_objectives),
            game_type=template.game_type,
            template_id=template.template_id,
            learning_objectives=learning_objectives,
            target_students=target_students,
            difficulty_range=difficulty_range,
            estimated_duration=self.estimate_game_duration(game_elements),
            game_elements=game_elements,
            mechanics=template.mechanics,
            scoring_system=self.create_scoring_system(template),
            adaptation_rules=adaptation_rules
        )
        
        # Store generated game
        self.generated_games[game.game_id] = game
        await self.save_game_to_database(game)
        
        return game
    
    async def select_optimal_template(self, learning_objectives: List[str], 
                                    preferences: Optional[Dict[str, Any]] = None) -> GameTemplate:
        """Select the best template based on learning objectives"""
        objective_keywords = " ".join(learning_objectives).lower()
        
        # Template scoring based on content match
        template_scores = {}
        
        for template_id, template in self.templates.items():
            score = 0.0
            
            # Subject alignment
            for subject in template.target_subjects:
                if subject in objective_keywords:
                    score += 0.4
            
            # Game type preferences
            if preferences and preferences.get("preferred_game_type"):
                if template.game_type.value == preferences["preferred_game_type"]:
                    score += 0.3
            
            # Default scoring based on game type appropriateness
            if "math" in objective_keywords and template.game_type == GameType.QUIZ:
                score += 0.2
            elif "science" in objective_keywords and template.game_type == GameType.SIMULATION:
                score += 0.2
            elif "language" in objective_keywords and template.game_type == GameType.ADVENTURE:
                score += 0.2
            elif "history" in objective_keywords and template.game_type == GameType.STRATEGY:
                score += 0.2
            elif "programming" in objective_keywords and template.game_type == GameType.CODING_CHALLENGE:
                score += 0.2
            
            template_scores[template_id] = score
        
        # Return highest scoring template
        best_template_id = max(template_scores, key=template_scores.get)
        return self.templates[best_template_id]
    
    async def analyze_student_profiles(self, student_ids: List[str]) -> Dict[str, Any]:
        """Analyze student profiles for personalization"""
        # This would integrate with student profile systems
        # For now, return sample profile data
        
        profiles = {
            "skill_levels": {"average": 0.6, "min": 0.3, "max": 0.9},
            "learning_styles": {"visual": 0.4, "auditory": 0.2, "kinesthetic": 0.3, "reading": 0.1},
            "engagement_patterns": {
                "preferred_session_length": 25,  # minutes
                "peak_attention_times": ["morning", "early_afternoon"],
                "motivation_factors": ["competition", "achievement", "collaboration"]
            },
            "accessibility_needs": {
                "visual_impairment": False,
                "hearing_impairment": False,
                "motor_impairment": False,
                "cognitive_support": False
            }
        }
        
        return profiles
    
    async def generate_game_elements(self, template: GameTemplate, 
                                   learning_objectives: List[str],
                                   student_profiles: Dict[str, Any]) -> List[GameElement]:
        """Generate specific game elements for the game"""
        elements = []
        
        # Determine content based on template type
        if template.game_type == GameType.QUIZ:
            elements = await self.generate_quiz_elements(learning_objectives, student_profiles)
        elif template.game_type == GameType.SIMULATION:
            elements = await self.generate_simulation_elements(learning_objectives, student_profiles)
        elif template.game_type == GameType.ADVENTURE:
            elements = await self.generate_adventure_elements(learning_objectives, student_profiles)
        elif template.game_type == GameType.STRATEGY:
            elements = await self.generate_strategy_elements(learning_objectives, student_profiles)
        elif template.game_type == GameType.CODING_CHALLENGE:
            elements = await self.generate_coding_elements(learning_objectives, student_profiles)
        
        return elements
    
    async def generate_quiz_elements(self, learning_objectives: List[str], 
                                   student_profiles: Dict[str, Any]) -> List[GameElement]:
        """Generate quiz game elements"""
        elements = []
        
        # Determine subject from learning objectives
        subject = self.extract_subject_from_objectives(learning_objectives)
        
        # Get appropriate question bank
        questions = self.question_banks.get(subject, self.question_banks.get("mathematics", []))
        
        # Filter and adapt questions
        skill_level = student_profiles["skill_levels"]["average"]
        
        for i, question_data in enumerate(questions[:20]):  # Limit to 20 questions
            # Adapt difficulty based on student profile
            adapted_difficulty = self.adapt_question_difficulty(
                question_data["difficulty"], skill_level
            )
            
            element = GameElement(
                element_id=f"quiz_question_{i}",
                element_type="question",
                content={
                    "question": question_data["question"],
                    "type": question_data["type"],
                    "options": question_data.get("options", []),
                    "correct_answer": question_data["correct_answer"],
                    "explanation": self.generate_explanation(question_data),
                    "hints": self.generate_hints(question_data)
                },
                difficulty_level=adapted_difficulty,
                learning_objectives=learning_objectives,
                estimated_time=30 + int(adapted_difficulty * 60)  # 30-90 seconds
            )
            
            elements.append(element)
        
        return elements
    
    async def generate_simulation_elements(self, learning_objectives: List[str],
                                         student_profiles: Dict[str, Any]) -> List[GameElement]:
        """Generate simulation game elements"""
        elements = []
        
        # Create virtual lab scenarios
        lab_scenarios = [
            {
                "title": "Chemical Reaction Explorer",
                "description": "Mix chemicals and observe reactions",
                "equipment": ["beakers", "chemicals", "thermometer", "ph_strips"],
                "objectives": ["observe_reactions", "predict_outcomes", "record_data"]
            },
            {
                "title": "Physics Motion Lab",
                "description": "Experiment with forces and motion",
                "equipment": ["ramps", "balls", "timer", "ruler"],
                "objectives": ["measure_velocity", "calculate_acceleration", "analyze_graphs"]
            }
        ]
        
        for i, scenario in enumerate(lab_scenarios):
            element = GameElement(
                element_id=f"simulation_{i}",
                element_type="experiment",
                content=scenario,
                difficulty_level=0.5,
                learning_objectives=learning_objectives,
                estimated_time=300  # 5 minutes per experiment
            )
            elements.append(element)
        
        return elements
    
    def calculate_difficulty_range(self, student_profiles: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate appropriate difficulty range for students"""
        min_skill = student_profiles["skill_levels"]["min"]
        max_skill = student_profiles["skill_levels"]["max"]
        
        # Adjust range to provide appropriate challenge
        difficulty_min = max(0.1, min_skill - 0.2)
        difficulty_max = min(1.0, max_skill + 0.1)
        
        return (difficulty_min, difficulty_max)
    
    def create_adaptation_rules(self, template: GameTemplate, 
                               student_profiles: Dict[str, Any]) -> Dict[str, Any]:
        """Create adaptive difficulty rules"""
        return {
            "difficulty_adjustment": {
                "success_threshold": 0.8,  # Increase difficulty if success rate > 80%
                "struggle_threshold": 0.4,  # Decrease difficulty if success rate < 40%
                "adjustment_factor": 0.1,   # How much to adjust difficulty
                "cooldown_questions": 3     # Questions before next adjustment
            },
            "hint_system": {
                "auto_hint_threshold": 30,  # Show hint after 30 seconds
                "max_hints_per_question": 2,
                "hint_penalty": 0.1  # Reduce score by 10% per hint
            },
            "engagement_tracking": {
                "inactivity_threshold": 60,  # Seconds before engagement prompt
                "break_suggestion": 1200,    # Suggest break after 20 minutes
                "motivation_boosters": ["encouragement", "progress_reminder", "achievement"]
            }
        }
    
    async def start_game_session(self, game_id: str, student_id: str) -> GameSession:
        """Start a new game session"""
        if game_id not in self.generated_games:
            raise ValueError(f"Game {game_id} not found")
        
        session = GameSession(
            session_id=str(uuid.uuid4()),
            game_id=game_id,
            student_id=student_id,
            started_at=datetime.now()
        )
        
        self.active_sessions[session.session_id] = session
        await self.save_session_to_database(session)
        
        return session
    
    async def process_game_action(self, session_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process student action in game"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        game = self.generated_games[session.game_id]
        
        # Record action
        action["timestamp"] = datetime.now().isoformat()
        session.actions.append(action)
        
        # Process based on action type
        response = {}
        
        if action["type"] == "answer_question":
            response = await self.process_answer(session, game, action)
        elif action["type"] == "request_hint":
            response = await self.provide_hint(session, game, action)
        elif action["type"] == "experiment_action":
            response = await self.process_experiment_action(session, game, action)
        
        # Update session metrics
        await self.update_engagement_metrics(session, action)
        
        # Check for adaptive adjustments
        await self.check_adaptive_adjustments(session, game)
        
        # Save session updates
        await self.save_session_to_database(session)
        
        return response
    
    async def process_answer(self, session: GameSession, game: GeneratedGame, 
                           action: Dict[str, Any]) -> Dict[str, Any]:
        """Process student answer"""
        question_id = action["question_id"]
        student_answer = action["answer"]
        
        # Find the question element
        question_element = None
        for element in game.game_elements:
            if element.element_id == question_id:
                question_element = element
                break
        
        if not question_element:
            return {"error": "Question not found"}
        
        correct_answer = question_element.content["correct_answer"]
        is_correct = str(student_answer).lower().strip() == str(correct_answer).lower().strip()
        
        # Calculate score
        base_points = 10
        time_taken = action.get("time_taken", 30)
        time_bonus = max(0, 30 - time_taken) * 0.5  # Bonus for quick answers
        
        points_earned = base_points + time_bonus if is_correct else 0
        session.score += points_earned
        
        # Update progress
        session.progress = len(session.actions) / len(game.game_elements)
        
        # Prepare response
        response = {
            "correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": question_element.content.get("explanation", ""),
            "points_earned": points_earned,
            "total_score": session.score,
            "progress": session.progress
        }
        
        # Add encouragement or guidance
        if is_correct:
            response["feedback"] = self.generate_positive_feedback()
        else:
            response["feedback"] = self.generate_constructive_feedback()
            response["hint"] = question_element.content.get("hints", ["Try thinking about it differently"])[0]
        
        return response
    
    def generate_positive_feedback(self) -> str:
        """Generate encouraging feedback for correct answers"""
        feedback_options = [
            "Excellent work! You're really getting the hang of this!",
            "Great job! Your understanding is clearly improving!",
            "Perfect! You're showing real mastery of this concept!",
            "Wonderful! Keep up the fantastic progress!",
            "Outstanding! You're thinking like a true scholar!"
        ]
        return random.choice(feedback_options)
    
    def generate_constructive_feedback(self) -> str:
        """Generate helpful feedback for incorrect answers"""
        feedback_options = [
            "Not quite right, but you're on the right track! Let's try a different approach.",
            "Close! Take a moment to review the concept and try again.",
            "Good effort! Learning happens through trying. Let's work through this together.",
            "That's a common mistake - you're learning! Here's a hint to guide you.",
            "Don't worry, everyone learns at their own pace. You've got this!"
        ]
        return random.choice(feedback_options)
    
    async def get_game_analytics(self, game_id: str) -> Dict[str, Any]:
        """Get analytics for a specific game"""
        if game_id not in self.generated_games:
            return {"error": "Game not found"}
        
        game = self.generated_games[game_id]
        
        # Find all sessions for this game
        game_sessions = [s for s in self.active_sessions.values() if s.game_id == game_id]
        
        if not game_sessions:
            return {"message": "No sessions found for this game"}
        
        # Calculate analytics
        total_sessions = len(game_sessions)
        completed_sessions = len([s for s in game_sessions if s.ended_at is not None])
        average_score = sum(s.score for s in game_sessions) / total_sessions
        average_progress = sum(s.progress for s in game_sessions) / total_sessions
        
        # Engagement metrics
        total_time_played = sum(
            (s.ended_at - s.started_at).total_seconds() if s.ended_at else 
            (datetime.now() - s.started_at).total_seconds()
            for s in game_sessions
        )
        average_session_time = total_time_played / total_sessions / 60  # minutes
        
        return {
            "game_id": game_id,
            "game_title": game.title,
            "analytics": {
                "total_sessions": total_sessions,
                "completed_sessions": completed_sessions,
                "completion_rate": completed_sessions / total_sessions if total_sessions > 0 else 0,
                "average_score": average_score,
                "average_progress": average_progress,
                "average_session_time_minutes": average_session_time,
                "engagement_level": self.calculate_engagement_level(game_sessions)
            },
            "learning_objectives_mastery": await self.analyze_objectives_mastery(game, game_sessions)
        }
    
    def calculate_engagement_level(self, sessions: List[GameSession]) -> float:
        """Calculate overall engagement level from sessions"""
        if not sessions:
            return 0.0
        
        engagement_factors = []
        
        for session in sessions:
            # Factor 1: Session completion
            completion_factor = 1.0 if session.ended_at else session.progress
            
            # Factor 2: Time spent vs estimated
            if session.ended_at:
                actual_time = (session.ended_at - session.started_at).total_seconds() / 60
                # Assume 20 minutes is ideal session time
                time_factor = min(1.0, actual_time / 20)
            else:
                time_factor = 0.5  # Partial credit for ongoing sessions
            
            # Factor 3: Action frequency (indicates active participation)
            if session.actions:
                action_frequency = len(session.actions) / max(1, len(session.actions))
                action_factor = min(1.0, action_frequency / 10)  # Normalize
            else:
                action_factor = 0.0
            
            session_engagement = (completion_factor + time_factor + action_factor) / 3
            engagement_factors.append(session_engagement)
        
        return sum(engagement_factors) / len(engagement_factors)
    
    # Utility methods
    def extract_subject_from_objectives(self, objectives: List[str]) -> str:
        """Extract primary subject from learning objectives"""
        objective_text = " ".join(objectives).lower()
        
        subjects = {
            "mathematics": ["math", "arithmetic", "algebra", "geometry", "calculus"],
            "science": ["science", "chemistry", "physics", "biology"],
            "english": ["english", "literature", "writing", "reading"],
            "history": ["history", "social studies", "civics"],
            "programming": ["programming", "coding", "computer science"]
        }
        
        for subject, keywords in subjects.items():
            if any(keyword in objective_text for keyword in keywords):
                return subject
        
        return "mathematics"  # Default fallback
    
    def adapt_question_difficulty(self, original_difficulty: float, student_skill: float) -> float:
        """Adapt question difficulty based on student skill level"""
        # Adjust difficulty to be slightly above student skill level for optimal challenge
        target_difficulty = student_skill + 0.1
        
        # Blend original difficulty with target difficulty
        adapted_difficulty = (original_difficulty + target_difficulty) / 2
        
        return max(0.1, min(1.0, adapted_difficulty))
    
    def generate_explanation(self, question_data: Dict) -> str:
        """Generate explanation for question"""
        # This would use AI to generate contextual explanations
        # For now, return a basic explanation
        return f"This question tests your understanding of {question_data.get('topic', 'the concept')}."
    
    def generate_hints(self, question_data: Dict) -> List[str]:
        """Generate helpful hints for question"""
        # This would use AI to generate contextual hints
        # For now, return basic hints
        return [
            "Think about the key concept being tested.",
            "Break the problem down into smaller parts.",
            "Consider what you already know about this topic."
        ]
    
    async def generate_game_title(self, template: GameTemplate, objectives: List[str]) -> str:
        """Generate engaging game title"""
        subject = self.extract_subject_from_objectives(objectives)
        
        title_templates = {
            "mathematics": ["Math Master Challenge", "Number Ninja Quest", "Calculation Champions"],
            "science": ["Science Explorer", "Lab Legend", "Discovery Dynasty"],
            "english": ["Word Warrior", "Literature Legend", "Grammar Guardian"],
            "history": ["Time Traveler", "History Hero", "Chronicle Champion"],
            "programming": ["Code Crusher", "Logic Legend", "Algorithm Ace"]
        }
        
        titles = title_templates.get(subject, ["Learning Legend", "Knowledge Knight", "Study Star"])
        return random.choice(titles)
    
    async def generate_game_description(self, template: GameTemplate, objectives: List[str]) -> str:
        """Generate engaging game description"""
        return f"An engaging {template.game_type.value} game designed to help you master {', '.join(objectives[:3])} through interactive learning and adaptive challenges."
    
    def estimate_game_duration(self, elements: List[GameElement]) -> int:
        """Estimate total game duration in minutes"""
        total_seconds = sum(element.estimated_time for element in elements)
        return max(5, total_seconds // 60)  # Minimum 5 minutes
    
    def create_scoring_system(self, template: GameTemplate) -> Dict[str, Any]:
        """Create scoring system based on template"""
        base_scoring = {
            "correct_answer": 10,
            "time_bonus_max": 5,
            "hint_penalty": -2,
            "streak_multiplier": 1.5,
            "completion_bonus": 50
        }
        
        # Adjust scoring based on game type
        if template.game_type == GameType.SIMULATION:
            base_scoring.update({
                "experiment_completion": 25,
                "hypothesis_accuracy": 15,
                "data_analysis": 10
            })
        elif template.game_type == GameType.CODING_CHALLENGE:
            base_scoring.update({
                "code_correctness": 20,
                "code_efficiency": 10,
                "test_cases_passed": 5
            })
        
        return base_scoring
    
    async def save_game_to_database(self, game: GeneratedGame):
        """Save generated game to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO generated_games 
            (game_id, title, template_id, config, learning_objectives, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            game.game_id,
            game.title,
            game.template_id,
            json.dumps(asdict(game)),
            json.dumps(game.learning_objectives),
            game.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def save_session_to_database(self, session: GameSession):
        """Save game session to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO game_sessions 
            (session_id, game_id, student_id, session_data, started_at, ended_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.game_id,
            session.student_id,
            json.dumps(asdict(session)),
            session.started_at.isoformat(),
            session.ended_at.isoformat() if session.ended_at else None
        ))
        
        conn.commit()
        conn.close()
    
    # Additional helper methods would be implemented for:
    # - update_engagement_metrics()
    # - check_adaptive_adjustments() 
    # - provide_hint()
    # - process_experiment_action()
    # - analyze_objectives_mastery()
    
    async def update_engagement_metrics(self, session: GameSession, action: Dict[str, Any]):
        """Update engagement metrics based on student action"""
        # Track engagement patterns
        current_time = datetime.now()
        
        if "engagement_metrics" not in session.engagement_metrics:
            session.engagement_metrics = {
                "actions_per_minute": 0,
                "average_response_time": 0,
                "engagement_score": 0.5
            }
        
        # Calculate actions per minute
        session_duration = (current_time - session.started_at).total_seconds() / 60
        session.engagement_metrics["actions_per_minute"] = len(session.actions) / max(1, session_duration)
        
        # Update engagement score based on activity patterns
        if action.get("time_taken", 30) < 60:  # Quick responses indicate engagement
            session.engagement_metrics["engagement_score"] = min(1.0, 
                session.engagement_metrics["engagement_score"] + 0.05)
        elif action.get("time_taken", 30) > 120:  # Slow responses might indicate disengagement
            session.engagement_metrics["engagement_score"] = max(0.0, 
                session.engagement_metrics["engagement_score"] - 0.02)
    
    async def check_adaptive_adjustments(self, session: GameSession, game: GeneratedGame):
        """Check if adaptive adjustments are needed"""
        if len(session.actions) < 3:  # Need minimum actions for analysis
            return
        
        # Analyze recent performance
        recent_actions = session.actions[-5:]  # Last 5 actions
        correct_answers = sum(1 for action in recent_actions 
                            if action.get("type") == "answer_question" and action.get("correct", False))
        success_rate = correct_answers / max(1, len(recent_actions))
        
        # Apply adaptation rules
        adaptation_rules = game.adaptation_rules.get("difficulty_adjustment", {})
        
        if success_rate > adaptation_rules.get("success_threshold", 0.8):
            # Increase difficulty
            session.metadata = session.metadata or {}
            current_difficulty = session.metadata.get("difficulty_level", 0.5)
            session.metadata["difficulty_level"] = min(1.0, 
                current_difficulty + adaptation_rules.get("adjustment_factor", 0.1))
        elif success_rate < adaptation_rules.get("struggle_threshold", 0.4):
            # Decrease difficulty
            session.metadata = session.metadata or {}
            current_difficulty = session.metadata.get("difficulty_level", 0.5)
            session.metadata["difficulty_level"] = max(0.1, 
                current_difficulty - adaptation_rules.get("adjustment_factor", 0.1))


# Example usage
async def main():
    generator = EducationalGameGenerator()
    
    # Generate a math game for middle school students
    learning_objectives = [
        "Master fraction operations",
        "Understand decimal relationships", 
        "Apply mathematical reasoning"
    ]
    
    target_students = ["student_123", "student_456"]
    
    preferences = {
        "preferred_game_type": "quiz",
        "difficulty_adaptation": True,
        "collaboration_enabled": False
    }
    
    # Generate the game
    game = await generator.generate_game(learning_objectives, target_students, preferences)
    print(f"Generated game: {game.title}")
    print(f"Game ID: {game.game_id}")
    print(f"Estimated duration: {game.estimated_duration} minutes")
    print(f"Number of elements: {len(game.game_elements)}")
    
    # Start a game session
    session = await generator.start_game_session(game.game_id, "student_123")
    print(f"Started session: {session.session_id}")
    
    # Simulate student actions
    answer_action = {
        "type": "answer_question",
        "question_id": game.game_elements[0].element_id,
        "answer": "42",
        "time_taken": 25
    }
    
    response = await generator.process_game_action(session.session_id, answer_action)
    print(f"Answer response: {response}")
    
    # Get analytics
    analytics = await generator.get_game_analytics(game.game_id)
    print(f"Game analytics: {analytics}")

if __name__ == "__main__":
    asyncio.run(main())