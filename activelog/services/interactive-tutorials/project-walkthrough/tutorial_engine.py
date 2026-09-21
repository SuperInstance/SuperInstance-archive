#!/usr/bin/env python3

import asyncio
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random
import uuid
import time

class ProjectType(Enum):
    CODING = "coding"
    CRAFTING = "crafting"
    COOKING = "cooking"
    SCIENCE_EXPERIMENT = "science_experiment"
    ART_PROJECT = "art_project"
    ENGINEERING = "engineering"
    MUSIC_COMPOSITION = "music_composition"
    GARDENING = "gardening"
    ELECTRONICS = "electronics"
    WOODWORKING = "woodworking"

class StepType(Enum):
    PREPARATION = "preparation"
    ACTION = "action"
    VERIFICATION = "verification"
    TROUBLESHOOTING = "troubleshooting"
    CLEANUP = "cleanup"
    REFLECTION = "reflection"

class DifficultyLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class MediaType(Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    INTERACTIVE_3D = "interactive_3d"
    DIAGRAM = "diagram"
    ANIMATION = "animation"

@dataclass
class Material:
    id: str
    name: str
    description: str
    quantity: str
    optional: bool
    alternatives: List[str]
    cost_estimate: Optional[float]
    where_to_find: str
    safety_notes: List[str]

@dataclass
class Tool:
    id: str
    name: str
    description: str
    required: bool
    alternatives: List[str]
    safety_instructions: List[str]
    skill_level_needed: DifficultyLevel

@dataclass
class MediaContent:
    id: str
    type: MediaType
    title: str
    content: str  # URL, text, or data
    description: str
    duration: Optional[int]  # for video/audio in seconds
    interactive_elements: Dict[str, Any]

@dataclass
class CheckPoint:
    id: str
    title: str
    description: str
    verification_method: str  # visual, measurement, test, etc.
    success_criteria: List[str]
    common_mistakes: List[str]
    troubleshooting_tips: List[str]
    media_content: List[MediaContent]

@dataclass
class TutorialStep:
    id: str
    step_number: int
    title: str
    description: str
    step_type: StepType
    estimated_time: int  # minutes
    difficulty: DifficultyLevel
    instructions: List[str]
    materials_needed: List[str]  # Material IDs
    tools_needed: List[str]     # Tool IDs
    safety_warnings: List[str]
    tips_and_tricks: List[str]
    common_mistakes: List[str]
    checkpoints: List[CheckPoint]
    media_content: List[MediaContent]
    prerequisites: List[str]    # Previous step IDs that must be completed
    optional: bool
    branch_conditions: Dict[str, str]  # Conditions for branching paths

@dataclass
class ProjectTutorial:
    id: str
    title: str
    description: str
    project_type: ProjectType
    difficulty_level: DifficultyLevel
    estimated_total_time: int  # minutes
    skill_level_required: str
    learning_objectives: List[str]
    final_outcome: str
    materials: List[Material]
    tools: List[Tool]
    steps: List[TutorialStep]
    tags: List[str]
    prerequisites: List[str]
    variations: List[Dict[str, Any]]  # Alternative approaches
    troubleshooting_guide: Dict[str, List[str]]
    created_by: str
    created_at: str
    updated_at: str

@dataclass
class UserProgress:
    user_id: str
    tutorial_id: str
    current_step: int
    completed_steps: List[str]
    skipped_steps: List[str]
    time_spent: Dict[str, int]  # step_id: minutes
    mistakes_made: List[Dict[str, Any]]
    achievements_earned: List[str]
    notes: Dict[str, str]  # step_id: user_notes
    photos_taken: List[str]  # URLs to user's progress photos
    start_time: str
    last_accessed: str
    completion_status: str

class StepValidationEngine:
    def __init__(self):
        self.validation_methods = {
            "visual": self._validate_visual,
            "measurement": self._validate_measurement,
            "test": self._validate_test,
            "photo_comparison": self._validate_photo_comparison,
            "code_execution": self._validate_code_execution,
            "self_assessment": self._validate_self_assessment
        }

    async def validate_step_completion(self, step: TutorialStep, 
                                     user_input: Dict[str, Any],
                                     checkpoint_id: str = None) -> Dict[str, Any]:
        """Validate if a step has been completed correctly."""
        
        if checkpoint_id:
            checkpoint = next((cp for cp in step.checkpoints if cp.id == checkpoint_id), None)
            if not checkpoint:
                return {"valid": False, "error": "Checkpoint not found"}
        else:
            checkpoint = step.checkpoints[0] if step.checkpoints else None
        
        if not checkpoint:
            # No validation criteria - assume completed
            return {"valid": True, "message": "Step completed"}
        
        validation_method = checkpoint.verification_method
        validator = self.validation_methods.get(validation_method)
        
        if validator:
            return await validator(checkpoint, user_input)
        else:
            return {"valid": False, "error": f"Unknown validation method: {validation_method}"}

    async def _validate_visual(self, checkpoint: CheckPoint, 
                             user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate through visual confirmation."""
        
        user_confirms = user_input.get("visual_confirmation", False)
        
        if user_confirms:
            return {
                "valid": True,
                "message": "Visual confirmation received",
                "next_action": "Continue to next step"
            }
        else:
            return {
                "valid": False,
                "message": "Visual confirmation required",
                "help": checkpoint.troubleshooting_tips,
                "common_mistakes": checkpoint.common_mistakes
            }

    async def _validate_measurement(self, checkpoint: CheckPoint, 
                                  user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate through measurements."""
        
        user_measurement = user_input.get("measurement")
        expected_range = user_input.get("expected_range", {})
        
        if not user_measurement:
            return {
                "valid": False,
                "message": "Measurement required",
                "help": "Please provide the measurement as requested"
            }
        
        # Simple range validation
        min_val = expected_range.get("min", 0)
        max_val = expected_range.get("max", float('inf'))
        
        try:
            measured_value = float(user_measurement)
            if min_val <= measured_value <= max_val:
                return {
                    "valid": True,
                    "message": f"Measurement {measured_value} is within acceptable range",
                    "accuracy": "good"
                }
            else:
                return {
                    "valid": False,
                    "message": f"Measurement {measured_value} is outside expected range ({min_val}-{max_val})",
                    "help": checkpoint.troubleshooting_tips
                }
        except ValueError:
            return {
                "valid": False,
                "message": "Invalid measurement format",
                "help": "Please provide a numeric measurement"
            }

    async def _validate_test(self, checkpoint: CheckPoint, 
                           user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate through functional testing."""
        
        test_results = user_input.get("test_results", {})
        
        success_count = 0
        total_criteria = len(checkpoint.success_criteria)
        
        feedback = []
        
        for criterion in checkpoint.success_criteria:
            test_name = criterion.lower().replace(" ", "_")
            result = test_results.get(test_name, False)
            
            if result:
                success_count += 1
                feedback.append(f"✓ {criterion}: Passed")
            else:
                feedback.append(f"✗ {criterion}: Failed")
        
        success_rate = success_count / total_criteria if total_criteria > 0 else 0
        
        if success_rate >= 0.8:  # 80% success rate required
            return {
                "valid": True,
                "message": f"Tests passed ({success_count}/{total_criteria})",
                "feedback": feedback,
                "success_rate": success_rate
            }
        else:
            return {
                "valid": False,
                "message": f"Tests failed ({success_count}/{total_criteria})",
                "feedback": feedback,
                "help": checkpoint.troubleshooting_tips,
                "success_rate": success_rate
            }

    async def _validate_photo_comparison(self, checkpoint: CheckPoint, 
                                       user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate by comparing user's photo with reference."""
        
        user_photo = user_input.get("photo_url")
        
        if not user_photo:
            return {
                "valid": False,
                "message": "Photo required for validation",
                "help": "Please take a photo of your current progress"
            }
        
        # In a real implementation, this would use image recognition
        # For now, we'll simulate the validation
        confidence_score = random.uniform(0.7, 0.95)  # Simulated AI confidence
        
        if confidence_score >= 0.8:
            return {
                "valid": True,
                "message": "Photo validation successful",
                "confidence": confidence_score,
                "feedback": "Your work matches the expected result"
            }
        else:
            return {
                "valid": False,
                "message": "Photo validation indicates issues",
                "confidence": confidence_score,
                "help": checkpoint.troubleshooting_tips,
                "feedback": "Please review the reference images and adjust your work"
            }

    async def _validate_code_execution(self, checkpoint: CheckPoint, 
                                     user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate code execution results."""
        
        code_output = user_input.get("code_output", "")
        expected_output = user_input.get("expected_output", "")
        
        # Simple string comparison (in real implementation, would be more sophisticated)
        if code_output.strip() == expected_output.strip():
            return {
                "valid": True,
                "message": "Code execution successful",
                "output_match": True
            }
        else:
            return {
                "valid": False,
                "message": "Code output doesn't match expected result",
                "expected": expected_output,
                "actual": code_output,
                "help": checkpoint.troubleshooting_tips
            }

    async def _validate_self_assessment(self, checkpoint: CheckPoint, 
                                      user_input: Dict[str, Any]) -> Dict[str, Any]:
        """Validate through self-assessment questions."""
        
        self_assessment = user_input.get("self_assessment", {})
        confidence_level = user_input.get("confidence_level", 0)
        
        if confidence_level >= 7:  # Scale of 1-10
            return {
                "valid": True,
                "message": "Self-assessment indicates good understanding",
                "confidence": confidence_level
            }
        elif confidence_level >= 5:
            return {
                "valid": True,
                "message": "Moderate confidence - consider reviewing",
                "confidence": confidence_level,
                "suggestion": "You might want to review this step before continuing"
            }
        else:
            return {
                "valid": False,
                "message": "Low confidence indicates need for review",
                "confidence": confidence_level,
                "help": checkpoint.troubleshooting_tips,
                "suggestion": "Please review the step and try again"
            }

class AdaptiveTutorialEngine:
    def __init__(self):
        self.learning_styles = {
            "visual": {"media_preference": [MediaType.IMAGE, MediaType.VIDEO, MediaType.DIAGRAM]},
            "auditory": {"media_preference": [MediaType.AUDIO, MediaType.VIDEO]},
            "kinesthetic": {"media_preference": [MediaType.INTERACTIVE_3D, MediaType.VIDEO]},
            "reading": {"media_preference": [MediaType.TEXT, MediaType.DIAGRAM]}
        }

    async def personalize_tutorial(self, tutorial: ProjectTutorial, 
                                 user_profile: Dict[str, Any]) -> ProjectTutorial:
        """Personalize tutorial based on user profile and preferences."""
        
        user_level = user_profile.get("skill_level", "beginner")
        learning_style = user_profile.get("learning_style", "visual")
        time_available = user_profile.get("time_available", tutorial.estimated_total_time)
        previous_experience = user_profile.get("previous_experience", [])
        
        # Create personalized copy
        personalized_tutorial = tutorial
        
        # Adjust difficulty and steps based on user level
        if user_level == "advanced" and tutorial.difficulty_level == DifficultyLevel.BEGINNER:
            personalized_tutorial = await self._increase_tutorial_difficulty(tutorial)
        elif user_level == "beginner" and tutorial.difficulty_level == DifficultyLevel.ADVANCED:
            personalized_tutorial = await self._simplify_tutorial(tutorial)
        
        # Adjust media content based on learning style
        personalized_tutorial = await self._adjust_media_for_learning_style(
            personalized_tutorial, learning_style
        )
        
        # Adjust timing if user has limited time
        if time_available < tutorial.estimated_total_time * 0.8:
            personalized_tutorial = await self._create_express_version(
                personalized_tutorial, time_available
            )
        
        return personalized_tutorial

    async def _increase_tutorial_difficulty(self, tutorial: ProjectTutorial) -> ProjectTutorial:
        """Increase tutorial difficulty for advanced users."""
        
        # Add more challenging variations
        for step in tutorial.steps:
            if step.step_type == StepType.ACTION:
                step.tips_and_tricks.append("Challenge: Try this alternative advanced technique")
                
                # Add advanced checkpoints
                if len(step.checkpoints) < 2:
                    advanced_checkpoint = CheckPoint(
                        id=str(uuid.uuid4()),
                        title="Advanced Validation",
                        description="Additional validation for advanced users",
                        verification_method="measurement",
                        success_criteria=["Meets advanced precision standards"],
                        common_mistakes=["Not achieving sufficient precision"],
                        troubleshooting_tips=["Use more precise measuring tools"],
                        media_content=[]
                    )
                    step.checkpoints.append(advanced_checkpoint)
        
        tutorial.difficulty_level = DifficultyLevel.ADVANCED
        return tutorial

    async def _simplify_tutorial(self, tutorial: ProjectTutorial) -> ProjectTutorial:
        """Simplify tutorial for beginner users."""
        
        # Break down complex steps
        simplified_steps = []
        
        for step in tutorial.steps:
            if len(step.instructions) > 5:  # Complex step
                # Split into multiple smaller steps
                mid_point = len(step.instructions) // 2
                
                # First part
                step1 = step
                step1.instructions = step.instructions[:mid_point]
                step1.title = f"{step.title} - Part 1"
                step1.estimated_time = step.estimated_time // 2
                
                # Second part
                step2 = TutorialStep(
                    id=str(uuid.uuid4()),
                    step_number=step.step_number,
                    title=f"{step.title} - Part 2",
                    description=step.description,
                    step_type=step.step_type,
                    estimated_time=step.estimated_time - step1.estimated_time,
                    difficulty=DifficultyLevel.BEGINNER,
                    instructions=step.instructions[mid_point:],
                    materials_needed=step.materials_needed,
                    tools_needed=step.tools_needed,
                    safety_warnings=step.safety_warnings,
                    tips_and_tricks=step.tips_and_tricks,
                    common_mistakes=step.common_mistakes,
                    checkpoints=step.checkpoints,
                    media_content=step.media_content,
                    prerequisites=[step1.id],
                    optional=step.optional,
                    branch_conditions=step.branch_conditions
                )
                
                simplified_steps.extend([step1, step2])
            else:
                simplified_steps.append(step)
        
        tutorial.steps = simplified_steps
        tutorial.difficulty_level = DifficultyLevel.BEGINNER
        return tutorial

    async def _adjust_media_for_learning_style(self, tutorial: ProjectTutorial, 
                                             learning_style: str) -> ProjectTutorial:
        """Adjust media content based on learning style."""
        
        preferred_media = self.learning_styles.get(learning_style, {}).get("media_preference", [])
        
        for step in tutorial.steps:
            # Sort media content by preference
            step.media_content.sort(
                key=lambda media: 0 if media.type in preferred_media else 1
            )
            
            # Add learning style specific content
            if learning_style == "auditory" and not any(m.type == MediaType.AUDIO for m in step.media_content):
                audio_content = MediaContent(
                    id=str(uuid.uuid4()),
                    type=MediaType.AUDIO,
                    title="Audio Instructions",
                    content=f"audio_instructions_{step.id}.mp3",
                    description="Spoken instructions for this step",
                    duration=step.estimated_time * 60,  # Estimate based on step time
                    interactive_elements={}
                )
                step.media_content.insert(0, audio_content)
        
        return tutorial

    async def _create_express_version(self, tutorial: ProjectTutorial, 
                                    time_available: int) -> ProjectTutorial:
        """Create express version fitting available time."""
        
        # Calculate time compression ratio
        compression_ratio = time_available / tutorial.estimated_total_time
        
        # Remove optional steps
        tutorial.steps = [step for step in tutorial.steps if not step.optional]
        
        # Reduce time estimates
        for step in tutorial.steps:
            step.estimated_time = int(step.estimated_time * compression_ratio)
        
        # Mark as express version
        tutorial.title = f"{tutorial.title} (Express Version)"
        tutorial.estimated_total_time = time_available
        
        return tutorial

    async def suggest_next_step(self, tutorial: ProjectTutorial, 
                              user_progress: UserProgress) -> Dict[str, Any]:
        """Suggest the next best step for the user."""
        
        current_step_index = user_progress.current_step
        completed_steps = set(user_progress.completed_steps)
        
        # Find next available step
        for i, step in enumerate(tutorial.steps[current_step_index:], current_step_index):
            # Check prerequisites
            prerequisites_met = all(prereq in completed_steps for prereq in step.prerequisites)
            
            if prerequisites_met:
                # Calculate estimated time including user's pace
                user_pace_factor = self._calculate_user_pace_factor(user_progress)
                adjusted_time = int(step.estimated_time * user_pace_factor)
                
                return {
                    "step_index": i,
                    "step": step,
                    "estimated_time": adjusted_time,
                    "difficulty_match": self._assess_difficulty_match(step, user_progress),
                    "preparation_needed": self._check_preparation_needs(step, tutorial),
                    "motivation_message": self._generate_motivation_message(step, user_progress)
                }
        
        # If no steps available, tutorial might be complete
        return {
            "message": "Congratulations! Tutorial completed!",
            "completion_status": "finished",
            "next_actions": ["review_work", "share_results", "try_variations"]
        }

    def _calculate_user_pace_factor(self, user_progress: UserProgress) -> float:
        """Calculate user's pace compared to estimated times."""
        
        if not user_progress.time_spent:
            return 1.0  # Default pace
        
        total_actual_time = sum(user_progress.time_spent.values())
        total_estimated_time = sum(
            # This would need tutorial step data to calculate properly
            # For now, assuming average of 15 minutes per step
            15 for _ in user_progress.time_spent
        )
        
        if total_estimated_time == 0:
            return 1.0
        
        pace_factor = total_actual_time / total_estimated_time
        
        # Cap the factor to reasonable bounds
        return max(0.5, min(2.0, pace_factor))

    def _assess_difficulty_match(self, step: TutorialStep, 
                               user_progress: UserProgress) -> str:
        """Assess if step difficulty matches user's demonstrated ability."""
        
        user_mistakes = len(user_progress.mistakes_made)
        completed_steps = len(user_progress.completed_steps)
        
        if completed_steps == 0:
            return "appropriate"  # No data yet
        
        mistake_rate = user_mistakes / completed_steps
        
        if mistake_rate < 0.1 and step.difficulty == DifficultyLevel.BEGINNER:
            return "too_easy"
        elif mistake_rate > 0.3 and step.difficulty == DifficultyLevel.ADVANCED:
            return "too_hard"
        else:
            return "appropriate"

    def _check_preparation_needs(self, step: TutorialStep, 
                               tutorial: ProjectTutorial) -> Dict[str, Any]:
        """Check what preparation is needed for the step."""
        
        materials_needed = []
        tools_needed = []
        
        for material_id in step.materials_needed:
            material = next((m for m in tutorial.materials if m.id == material_id), None)
            if material:
                materials_needed.append({
                    "name": material.name,
                    "quantity": material.quantity,
                    "optional": material.optional
                })
        
        for tool_id in step.tools_needed:
            tool = next((t for t in tutorial.tools if t.id == tool_id), None)
            if tool:
                tools_needed.append({
                    "name": tool.name,
                    "required": tool.required,
                    "alternatives": tool.alternatives
                })
        
        return {
            "materials_needed": materials_needed,
            "tools_needed": tools_needed,
            "setup_time": 5,  # Estimated setup time in minutes
            "safety_check": step.safety_warnings
        }

    def _generate_motivation_message(self, step: TutorialStep, 
                                   user_progress: UserProgress) -> str:
        """Generate encouraging message for the user."""
        
        completed_count = len(user_progress.completed_steps)
        
        messages = [
            f"Great progress! You've completed {completed_count} steps already.",
            f"You're doing fantastic! Ready for '{step.title}'?",
            f"Next up: {step.title}. You've got this!",
            f"Time for the next challenge: {step.title}. Let's go!",
            f"Excellent work so far! '{step.title}' is up next."
        ]
        
        return random.choice(messages)

class ProjectTutorialSystem:
    def __init__(self, db_path: str = "project_tutorials.db"):
        self.db_path = db_path
        self.step_validator = StepValidationEngine()
        self.adaptive_engine = AdaptiveTutorialEngine()
        self._init_database()

    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_tutorials (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            project_type TEXT,
            difficulty_level TEXT,
            estimated_total_time INTEGER,
            skill_level_required TEXT,
            learning_objectives TEXT,
            final_outcome TEXT,
            materials TEXT,
            tools TEXT,
            steps TEXT,
            tags TEXT,
            prerequisites TEXT,
            variations TEXT,
            troubleshooting_guide TEXT,
            created_by TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tutorial_id TEXT,
            current_step INTEGER,
            completed_steps TEXT,
            skipped_steps TEXT,
            time_spent TEXT,
            mistakes_made TEXT,
            achievements_earned TEXT,
            notes TEXT,
            photos_taken TEXT,
            start_time TEXT,
            last_accessed TEXT,
            completion_status TEXT,
            FOREIGN KEY (tutorial_id) REFERENCES project_tutorials (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tutorial_sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            tutorial_id TEXT,
            session_start TEXT,
            session_end TEXT,
            steps_completed INTEGER,
            mistakes_count INTEGER,
            session_notes TEXT,
            created_at TEXT
        )
        ''')
        
        conn.commit()
        conn.close()

    async def create_tutorial(self, title: str, description: str, 
                            project_type: str, difficulty: str,
                            steps_data: List[Dict[str, Any]]) -> ProjectTutorial:
        """Create a new project tutorial."""
        
        tutorial_id = str(uuid.uuid4())
        
        # Create materials and tools from steps data
        all_materials = []
        all_tools = []
        steps = []
        
        total_time = 0
        
        for i, step_data in enumerate(steps_data):
            step_id = str(uuid.uuid4())
            
            # Create step
            step = TutorialStep(
                id=step_id,
                step_number=i + 1,
                title=step_data.get("title", f"Step {i + 1}"),
                description=step_data.get("description", ""),
                step_type=StepType(step_data.get("step_type", "action")),
                estimated_time=step_data.get("estimated_time", 15),
                difficulty=DifficultyLevel(step_data.get("difficulty", difficulty)),
                instructions=step_data.get("instructions", []),
                materials_needed=step_data.get("materials_needed", []),
                tools_needed=step_data.get("tools_needed", []),
                safety_warnings=step_data.get("safety_warnings", []),
                tips_and_tricks=step_data.get("tips_and_tricks", []),
                common_mistakes=step_data.get("common_mistakes", []),
                checkpoints=[],  # Will be populated if provided
                media_content=[],  # Will be populated if provided
                prerequisites=step_data.get("prerequisites", []),
                optional=step_data.get("optional", False),
                branch_conditions=step_data.get("branch_conditions", {})
            )
            
            # Create checkpoints if provided
            for cp_data in step_data.get("checkpoints", []):
                checkpoint = CheckPoint(
                    id=str(uuid.uuid4()),
                    title=cp_data.get("title", "Checkpoint"),
                    description=cp_data.get("description", ""),
                    verification_method=cp_data.get("verification_method", "visual"),
                    success_criteria=cp_data.get("success_criteria", []),
                    common_mistakes=cp_data.get("common_mistakes", []),
                    troubleshooting_tips=cp_data.get("troubleshooting_tips", []),
                    media_content=[]
                )
                step.checkpoints.append(checkpoint)
            
            steps.append(step)
            total_time += step.estimated_time
        
        # Generate sample materials and tools
        materials = self._generate_sample_materials(project_type)
        tools = self._generate_sample_tools(project_type)
        
        tutorial = ProjectTutorial(
            id=tutorial_id,
            title=title,
            description=description,
            project_type=ProjectType(project_type),
            difficulty_level=DifficultyLevel(difficulty),
            estimated_total_time=total_time,
            skill_level_required=difficulty,
            learning_objectives=self._generate_learning_objectives(project_type, steps),
            final_outcome=f"Completed {title.lower()} project",
            materials=materials,
            tools=tools,
            steps=steps,
            tags=self._generate_tags(project_type, difficulty),
            prerequisites=[],
            variations=[],
            troubleshooting_guide={},
            created_by="system",
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO project_tutorials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tutorial.id, tutorial.title, tutorial.description,
            tutorial.project_type.value, tutorial.difficulty_level.value,
            tutorial.estimated_total_time, tutorial.skill_level_required,
            json.dumps(tutorial.learning_objectives), tutorial.final_outcome,
            json.dumps([asdict(m) for m in tutorial.materials]),
            json.dumps([asdict(t) for t in tutorial.tools]),
            json.dumps([asdict(s) for s in tutorial.steps]),
            json.dumps(tutorial.tags), json.dumps(tutorial.prerequisites),
            json.dumps(tutorial.variations), json.dumps(tutorial.troubleshooting_guide),
            tutorial.created_by, tutorial.created_at, tutorial.updated_at
        ))
        
        conn.commit()
        conn.close()
        
        return tutorial

    def _generate_sample_materials(self, project_type: str) -> List[Material]:
        """Generate sample materials for project type."""
        
        material_sets = {
            "coding": [
                Material(
                    id="computer",
                    name="Computer",
                    description="Computer with text editor or IDE",
                    quantity="1",
                    optional=False,
                    alternatives=["Laptop", "Tablet with keyboard"],
                    cost_estimate=0.0,
                    where_to_find="Already owned or borrow",
                    safety_notes=[]
                )
            ],
            "crafting": [
                Material(
                    id="glue",
                    name="Craft Glue",
                    description="All-purpose craft glue",
                    quantity="1 bottle",
                    optional=False,
                    alternatives=["Hot glue gun", "Double-sided tape"],
                    cost_estimate=3.99,
                    where_to_find="Craft store, supermarket",
                    safety_notes=["Keep away from children", "Ensure good ventilation"]
                ),
                Material(
                    id="scissors",
                    name="Scissors",
                    description="Sharp crafting scissors",
                    quantity="1 pair",
                    optional=False,
                    alternatives=["Craft knife", "Box cutter"],
                    cost_estimate=8.99,
                    where_to_find="Craft store, office supplies",
                    safety_notes=["Handle with care", "Keep away from children"]
                )
            ]
        }
        
        return material_sets.get(project_type, [])

    def _generate_sample_tools(self, project_type: str) -> List[Tool]:
        """Generate sample tools for project type."""
        
        tool_sets = {
            "coding": [
                Tool(
                    id="text_editor",
                    name="Text Editor or IDE",
                    description="Software for writing and editing code",
                    required=True,
                    alternatives=["VS Code", "Sublime Text", "Notepad++"],
                    safety_instructions=[],
                    skill_level_needed=DifficultyLevel.BEGINNER
                )
            ],
            "crafting": [
                Tool(
                    id="cutting_mat",
                    name="Cutting Mat",
                    description="Self-healing cutting mat",
                    required=False,
                    alternatives=["Cardboard", "Old magazine"],
                    safety_instructions=["Provides safe cutting surface"],
                    skill_level_needed=DifficultyLevel.BEGINNER
                )
            ]
        }
        
        return tool_sets.get(project_type, [])

    def _generate_learning_objectives(self, project_type: str, 
                                    steps: List[TutorialStep]) -> List[str]:
        """Generate learning objectives based on project type and steps."""
        
        base_objectives = {
            "coding": ["Understand basic programming concepts", "Write functional code", "Debug common issues"],
            "crafting": ["Follow detailed instructions", "Use tools safely", "Create finished product"],
            "cooking": ["Practice cooking techniques", "Understand ingredient functions", "Create delicious meal"]
        }
        
        objectives = base_objectives.get(project_type, ["Complete project successfully"])
        
        # Add specific objectives based on step types
        step_types = [step.step_type for step in steps]
        if StepType.TROUBLESHOOTING in step_types:
            objectives.append("Develop problem-solving skills")
        
        return objectives

    def _generate_tags(self, project_type: str, difficulty: str) -> List[str]:
        """Generate relevant tags for the tutorial."""
        
        tags = [project_type, difficulty]
        
        type_tags = {
            "coding": ["programming", "software", "development"],
            "crafting": ["diy", "handmade", "creative"],
            "cooking": ["culinary", "recipe", "kitchen"]
        }
        
        tags.extend(type_tags.get(project_type, []))
        
        return tags

    async def start_tutorial_session(self, tutorial_id: str, user_id: str,
                                   user_profile: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start a new tutorial session for a user."""
        
        # Get tutorial
        tutorial = await self.get_tutorial(tutorial_id)
        if not tutorial:
            return {"error": "Tutorial not found"}
        
        # Personalize tutorial if profile provided
        if user_profile:
            tutorial = await self.adaptive_engine.personalize_tutorial(tutorial, user_profile)
        
        # Create or update user progress
        progress = UserProgress(
            user_id=user_id,
            tutorial_id=tutorial_id,
            current_step=0,
            completed_steps=[],
            skipped_steps=[],
            time_spent={},
            mistakes_made=[],
            achievements_earned=[],
            notes={},
            photos_taken=[],
            start_time=datetime.now().isoformat(),
            last_accessed=datetime.now().isoformat(),
            completion_status="in_progress"
        )
        
        # Save progress to database
        await self._save_user_progress(progress)
        
        # Get first step suggestion
        next_step_info = await self.adaptive_engine.suggest_next_step(tutorial, progress)
        
        return {
            "session_started": True,
            "tutorial": {
                "id": tutorial.id,
                "title": tutorial.title,
                "description": tutorial.description,
                "estimated_time": tutorial.estimated_total_time,
                "difficulty": tutorial.difficulty_level.value,
                "total_steps": len(tutorial.steps)
            },
            "user_progress": asdict(progress),
            "next_step": next_step_info,
            "materials_overview": [{"name": m.name, "required": not m.optional} for m in tutorial.materials],
            "tools_overview": [{"name": t.name, "required": t.required} for t in tutorial.tools]
        }

    async def get_tutorial(self, tutorial_id: str) -> Optional[ProjectTutorial]:
        """Get tutorial by ID."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM project_tutorials WHERE id = ?', (tutorial_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # Reconstruct tutorial object
        materials = [Material(**m) for m in json.loads(row[9])]
        tools = [Tool(**t) for t in json.loads(row[10])]
        steps = [TutorialStep(**s) for s in json.loads(row[11])]
        
        return ProjectTutorial(
            id=row[0], title=row[1], description=row[2],
            project_type=ProjectType(row[3]), difficulty_level=DifficultyLevel(row[4]),
            estimated_total_time=row[5], skill_level_required=row[6],
            learning_objectives=json.loads(row[7]), final_outcome=row[8],
            materials=materials, tools=tools, steps=steps,
            tags=json.loads(row[12]), prerequisites=json.loads(row[13]),
            variations=json.loads(row[14]), troubleshooting_guide=json.loads(row[15]),
            created_by=row[16], created_at=row[17], updated_at=row[18]
        )

    async def _save_user_progress(self, progress: UserProgress):
        """Save user progress to database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO user_progress VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"{progress.user_id}_{progress.tutorial_id}",
            progress.user_id, progress.tutorial_id, progress.current_step,
            json.dumps(progress.completed_steps), json.dumps(progress.skipped_steps),
            json.dumps(progress.time_spent), json.dumps(progress.mistakes_made),
            json.dumps(progress.achievements_earned), json.dumps(progress.notes),
            json.dumps(progress.photos_taken), progress.start_time,
            progress.last_accessed, progress.completion_status
        ))
        
        conn.commit()
        conn.close()

    async def submit_step_completion(self, user_id: str, tutorial_id: str,
                                   step_id: str, validation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit step completion and validate."""
        
        # Get tutorial and progress
        tutorial = await self.get_tutorial(tutorial_id)
        progress = await self._get_user_progress(user_id, tutorial_id)
        
        if not tutorial or not progress:
            return {"error": "Tutorial or progress not found"}
        
        # Find the step
        step = next((s for s in tutorial.steps if s.id == step_id), None)
        if not step:
            return {"error": "Step not found"}
        
        # Validate step completion
        validation_result = await self.step_validator.validate_step_completion(
            step, validation_data
        )
        
        response = {
            "step_id": step_id,
            "step_title": step.title,
            "validation_result": validation_result
        }
        
        if validation_result["valid"]:
            # Mark step as completed
            if step_id not in progress.completed_steps:
                progress.completed_steps.append(step_id)
            
            # Update progress
            progress.current_step = min(progress.current_step + 1, len(tutorial.steps))
            progress.last_accessed = datetime.now().isoformat()
            
            # Record time spent (if provided)
            time_spent = validation_data.get("time_spent", 0)
            if time_spent > 0:
                progress.time_spent[step_id] = time_spent
            
            # Save progress
            await self._save_user_progress(progress)
            
            # Get next step suggestion
            next_step_info = await self.adaptive_engine.suggest_next_step(tutorial, progress)
            response["next_step"] = next_step_info
            
            # Check for achievements
            achievements = await self._check_step_achievements(progress, step)
            if achievements:
                response["achievements"] = achievements
                progress.achievements_earned.extend([a["id"] for a in achievements])
                await self._save_user_progress(progress)
        
        else:
            # Record mistake
            mistake = {
                "step_id": step_id,
                "timestamp": datetime.now().isoformat(),
                "error_type": validation_result.get("error", "validation_failed"),
                "user_input": validation_data
            }
            progress.mistakes_made.append(mistake)
            await self._save_user_progress(progress)
            
            response["help_available"] = True
        
        return response

    async def _get_user_progress(self, user_id: str, tutorial_id: str) -> Optional[UserProgress]:
        """Get user progress from database."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM user_progress WHERE user_id = ? AND tutorial_id = ?
        ''', (user_id, tutorial_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return UserProgress(
            user_id=row[1], tutorial_id=row[2], current_step=row[3],
            completed_steps=json.loads(row[4]), skipped_steps=json.loads(row[5]),
            time_spent=json.loads(row[6]), mistakes_made=json.loads(row[7]),
            achievements_earned=json.loads(row[8]), notes=json.loads(row[9]),
            photos_taken=json.loads(row[10]), start_time=row[11],
            last_accessed=row[12], completion_status=row[13]
        )

    async def _check_step_achievements(self, progress: UserProgress, 
                                     step: TutorialStep) -> List[Dict[str, Any]]:
        """Check for achievements unlocked by completing this step."""
        
        achievements = []
        
        # First step achievement
        if len(progress.completed_steps) == 1:
            achievements.append({
                "id": "first_step",
                "title": "Getting Started",
                "description": "Completed your first step!",
                "icon": "🚀",
                "points": 10
            })
        
        # Milestone achievements
        completed_count = len(progress.completed_steps)
        if completed_count == 5:
            achievements.append({
                "id": "making_progress",
                "title": "Making Progress",
                "description": "Completed 5 steps!",
                "icon": "⭐",
                "points": 25
            })
        elif completed_count == 10:
            achievements.append({
                "id": "steady_learner",
                "title": "Steady Learner",
                "description": "Completed 10 steps!",
                "icon": "🏆",
                "points": 50
            })
        
        # Perfect step achievement
        if step.checkpoints and not any(m["step_id"] == step.id for m in progress.mistakes_made):
            achievements.append({
                "id": f"perfect_{step.id}",
                "title": "Perfect Execution",
                "description": f"Completed '{step.title}' without mistakes!",
                "icon": "💎",
                "points": 15
            })
        
        return achievements

    async def get_tutorial_catalog(self, project_type: str = None, 
                                 difficulty: str = None,
                                 tags: List[str] = None) -> List[Dict[str, Any]]:
        """Get catalog of available tutorials."""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
        SELECT id, title, description, project_type, difficulty_level, 
               estimated_total_time, tags, created_at
        FROM project_tutorials
        '''
        
        conditions = []
        params = []
        
        if project_type:
            conditions.append("project_type = ?")
            params.append(project_type)
        
        if difficulty:
            conditions.append("difficulty_level = ?")
            params.append(difficulty)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        catalog = []
        for row in rows:
            tutorial_tags = json.loads(row[6])
            
            # Filter by tags if specified
            if tags and not any(tag in tutorial_tags for tag in tags):
                continue
            
            catalog.append({
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "project_type": row[3],
                "difficulty": row[4],
                "estimated_time": row[5],
                "tags": tutorial_tags,
                "created_at": row[7]
            })
        
        return catalog

if __name__ == "__main__":
    async def main():
        tutorial_system = ProjectTutorialSystem()
        
        # Create a sample coding tutorial
        steps_data = [
            {
                "title": "Set up development environment",
                "description": "Install and configure necessary tools",
                "step_type": "preparation",
                "estimated_time": 20,
                "instructions": [
                    "Download and install Python",
                    "Install a text editor (VS Code recommended)",
                    "Create a new project folder"
                ],
                "checkpoints": [{
                    "title": "Environment Check",
                    "description": "Verify setup is correct",
                    "verification_method": "code_execution",
                    "success_criteria": ["Python version displays correctly"]
                }]
            },
            {
                "title": "Write your first function",
                "description": "Create a simple greeting function",
                "step_type": "action",
                "estimated_time": 15,
                "instructions": [
                    "Create a new file called main.py",
                    "Write a function that takes a name parameter",
                    "Make the function return a greeting message"
                ],
                "checkpoints": [{
                    "title": "Function Test",
                    "description": "Test the function works",
                    "verification_method": "code_execution",
                    "success_criteria": ["Function returns expected greeting"]
                }]
            }
        ]
        
        tutorial = await tutorial_system.create_tutorial(
            title="Python Basics: Your First Function",
            description="Learn to write your first Python function",
            project_type="coding",
            difficulty="beginner",
            steps_data=steps_data
        )
        
        print(f"Created tutorial: {tutorial.title}")
        print(f"Type: {tutorial.project_type.value}")
        print(f"Difficulty: {tutorial.difficulty_level.value}")
        print(f"Steps: {len(tutorial.steps)}")
        print(f"Estimated time: {tutorial.estimated_total_time} minutes")
        
        # Start a tutorial session
        session_info = await tutorial_system.start_tutorial_session(
            tutorial.id, "user123", 
            {"skill_level": "beginner", "learning_style": "visual", "time_available": 45}
        )
        
        print(f"\nStarted session for: {session_info['tutorial']['title']}")
        print(f"Next step: {session_info['next_step']['step']['title']}")
        
        # Simulate step completion
        completion_result = await tutorial_system.submit_step_completion(
            "user123", tutorial.id, tutorial.steps[0].id,
            {"visual_confirmation": True, "time_spent": 18}
        )
        
        print(f"\nStep completion: {completion_result['validation_result']['valid']}")
        if completion_result.get('achievements'):
            print(f"Achievements unlocked: {[a['title'] for a in completion_result['achievements']]}")
    
    asyncio.run(main())