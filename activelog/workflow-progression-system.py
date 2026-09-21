#!/usr/bin/env python3
"""
SuperInstance Workflow Progression System
Ensures bots never get stuck and always know what to do next

This system guides bots through complex multi-step processes,
handles obstacles, and maintains forward momentum.
"""

import json
import sqlite3
import datetime
import enum
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

class TaskStatus(enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class Priority(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class WorkflowStep:
    """Individual step in a workflow"""
    step_id: str
    name: str
    description: str
    prerequisites: List[str]
    estimated_time: int  # minutes
    priority: Priority
    status: TaskStatus
    completion_criteria: List[str]
    resources_needed: List[str]
    learning_opportunities: List[str]
    fallback_options: List[str]

@dataclass
class WorkflowTask:
    """Complete task composed of multiple steps"""
    task_id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    current_step: Optional[str]
    progress_percentage: float
    estimated_completion: datetime.datetime
    bot_assigned: str
    collaboration_needed: List[str]

@dataclass
class BotState:
    """Current state and capabilities of a bot"""
    bot_id: str
    current_skills: List[str]
    skill_levels: Dict[str, int]
    current_focus: str
    available_time: int  # minutes
    collaboration_partners: List[str]
    learning_goals: List[str]
    blocked_on: Optional[str]

class WorkflowProgressionSystem:
    """Manages bot workflow progression and obstacle handling"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/workflow_progression.db"):
        self.db_path = Path(db_path)
        self.init_database()
        
    def init_database(self):
        """Initialize workflow tracking database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS workflows (
                    task_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    steps TEXT,
                    current_step TEXT,
                    progress_percentage REAL,
                    estimated_completion TEXT,
                    bot_assigned TEXT,
                    collaboration_needed TEXT,
                    created_time TEXT,
                    last_updated TEXT
                );
                
                CREATE TABLE IF NOT EXISTS bot_states (
                    bot_id TEXT PRIMARY KEY,
                    current_skills TEXT,
                    skill_levels TEXT,
                    current_focus TEXT,
                    available_time INTEGER,
                    collaboration_partners TEXT,
                    learning_goals TEXT,
                    blocked_on TEXT,
                    last_updated TEXT
                );
                
                CREATE TABLE IF NOT EXISTS step_history (
                    history_id TEXT PRIMARY KEY,
                    task_id TEXT,
                    step_id TEXT,
                    bot_id TEXT,
                    action_taken TEXT,
                    result TEXT,
                    time_spent INTEGER,
                    learning_captured TEXT,
                    timestamp TEXT
                );
                
                CREATE TABLE IF NOT EXISTS workflow_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT,
                    description TEXT,
                    template_steps TEXT,
                    use_cases TEXT,
                    success_rate REAL,
                    average_completion_time INTEGER,
                    created_time TEXT
                );
                
                CREATE TABLE IF NOT EXISTS obstacle_solutions (
                    solution_id TEXT PRIMARY KEY,
                    obstacle_type TEXT,
                    context TEXT,
                    solution_strategy TEXT,
                    success_rate REAL,
                    learning_generated TEXT,
                    created_time TEXT
                );
            """)
    
    def get_next_action(self, bot_id: str, current_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        The core function that ensures bots always know what to do next
        This is the "never get stuck" guarantee
        """
        
        # Load bot state and current workflow
        bot_state = self._load_bot_state(bot_id)
        current_workflow = self._get_current_workflow(bot_id)
        
        # Check if bot is blocked
        if bot_state and bot_state.blocked_on:
            return self._handle_blocked_state(bot_state, current_context)
        
        # If no current workflow, assign one
        if not current_workflow:
            return self._assign_new_workflow(bot_id, bot_state, current_context)
        
        # Get next step in current workflow
        next_step = self._get_next_workflow_step(current_workflow, bot_state)
        
        if next_step:
            return self._prepare_step_action(next_step, bot_state, current_context)
        else:
            # Workflow complete or stuck - handle completion
            return self._handle_workflow_completion(current_workflow, bot_state)
    
    def _load_bot_state(self, bot_id: str) -> Optional[BotState]:
        """Load current bot state from database"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT * FROM bot_states WHERE bot_id = ?
            """, (bot_id,)).fetchone()
            
            if not result:
                # Create default bot state
                default_state = BotState(
                    bot_id=bot_id,
                    current_skills=["pattern_recognition", "basic_documentation"],
                    skill_levels={"pattern_recognition": 1, "basic_documentation": 1},
                    current_focus="learning",
                    available_time=120,  # 2 hours
                    collaboration_partners=[],
                    learning_goals=["component_extraction", "system_integration"],
                    blocked_on=None
                )
                self._save_bot_state(default_state)
                return default_state
            
            return BotState(
                bot_id=result[0],
                current_skills=json.loads(result[1]),
                skill_levels=json.loads(result[2]),
                current_focus=result[3],
                available_time=result[4],
                collaboration_partners=json.loads(result[5]),
                learning_goals=json.loads(result[6]),
                blocked_on=result[7]
            )
    
    def _get_current_workflow(self, bot_id: str) -> Optional[WorkflowTask]:
        """Get bot's current active workflow"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT * FROM workflows 
                WHERE bot_assigned = ? AND current_step IS NOT NULL
                ORDER BY last_updated DESC LIMIT 1
            """, (bot_id,)).fetchone()
            
            if not result:
                return None
            
            return WorkflowTask(
                task_id=result[0],
                name=result[1],
                description=result[2],
                steps=[WorkflowStep(**step) for step in json.loads(result[3])],
                current_step=result[4],
                progress_percentage=result[5],
                estimated_completion=datetime.datetime.fromisoformat(result[6]),
                bot_assigned=result[7],
                collaboration_needed=json.loads(result[8]) if result[8] else []
            )
    
    def _handle_blocked_state(self, bot_state: BotState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle when bot is blocked and provide unblocking strategy"""
        
        blocked_on = bot_state.blocked_on
        
        # Try to find solution from previous successful unblockings
        solution = self._find_obstacle_solution(blocked_on, context)
        
        if solution:
            return {
                "action_type": "unblock",
                "strategy": solution["solution_strategy"],
                "description": f"Apply proven solution for: {blocked_on}",
                "success_probability": solution["success_rate"],
                "next_steps": json.loads(solution["solution_strategy"]),
                "learning_opportunity": f"Master obstacle handling for: {blocked_on}",
                "time_estimate": 30  # minutes
            }
        else:
            # Create new unblocking strategy
            return self._create_unblocking_strategy(blocked_on, bot_state, context)
    
    def _assign_new_workflow(self, bot_id: str, bot_state: BotState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Assign optimal workflow based on bot capabilities and context"""
        
        # Find workflows that match bot's current skills and learning goals
        suitable_workflows = self._find_suitable_workflows(bot_state, context)
        
        if not suitable_workflows:
            # Create custom workflow based on context
            return self._create_custom_workflow(bot_id, bot_state, context)
        
        # Select best workflow
        best_workflow = self._select_optimal_workflow(suitable_workflows, bot_state)
        
        # Assign workflow to bot
        self._assign_workflow_to_bot(best_workflow, bot_id)
        
        return {
            "action_type": "start_workflow",
            "workflow_name": best_workflow.name,
            "description": best_workflow.description,
            "first_step": best_workflow.steps[0].description,
            "estimated_time": sum(step.estimated_time for step in best_workflow.steps),
            "learning_opportunities": [step.learning_opportunities for step in best_workflow.steps],
            "success_probability": 0.8  # Based on workflow template success rate
        }
    
    def _get_next_workflow_step(self, workflow: WorkflowTask, bot_state: BotState) -> Optional[WorkflowStep]:
        """Get the next step bot should work on in current workflow"""
        
        if not workflow.current_step:
            # Start with first step
            return workflow.steps[0] if workflow.steps else None
        
        # Find current step
        current_step_index = next(
            (i for i, step in enumerate(workflow.steps) if step.step_id == workflow.current_step),
            -1
        )
        
        if current_step_index == -1:
            # Current step not found, restart from beginning
            return workflow.steps[0] if workflow.steps else None
        
        current_step = workflow.steps[current_step_index]
        
        # If current step is complete, move to next
        if current_step.status == TaskStatus.COMPLETED:
            next_index = current_step_index + 1
            if next_index < len(workflow.steps):
                return workflow.steps[next_index]
            else:
                return None  # Workflow complete
        
        # Check if current step can be worked on
        if self._can_work_on_step(current_step, bot_state):
            return current_step
        else:
            # Step blocked, find alternative or create unblocking strategy
            return self._find_alternative_step(workflow, current_step_index, bot_state)
    
    def _prepare_step_action(self, step: WorkflowStep, bot_state: BotState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare specific actionable instructions for a workflow step"""
        
        # Check if bot has required skills
        missing_skills = [skill for skill in step.resources_needed 
                         if skill not in bot_state.current_skills]
        
        if missing_skills:
            return self._create_skill_learning_action(step, missing_skills, bot_state)
        
        # Create specific action based on step type
        action = {
            "action_type": "execute_step",
            "step_name": step.name,
            "description": step.description,
            "specific_instructions": self._generate_specific_instructions(step, context),
            "completion_criteria": step.completion_criteria,
            "estimated_time": step.estimated_time,
            "priority": step.priority.value,
            "resources_available": self._list_available_resources(step.resources_needed),
            "learning_opportunity": step.learning_opportunities,
            "progress_tracking": self._create_progress_tracker(step),
            "fallback_options": step.fallback_options
        }
        
        return action
    
    def _create_skill_learning_action(self, step: WorkflowStep, missing_skills: List[str], bot_state: BotState) -> Dict[str, Any]:
        """Create learning action to acquire missing skills"""
        
        return {
            "action_type": "skill_learning",
            "target_skills": missing_skills,
            "learning_goal": f"Acquire skills needed for: {step.name}",
            "learning_approach": self._design_skill_learning_approach(missing_skills, bot_state),
            "estimated_learning_time": len(missing_skills) * 15,  # 15 minutes per skill
            "practice_opportunities": self._find_practice_opportunities(missing_skills),
            "success_criteria": [f"Demonstrate {skill} competency" for skill in missing_skills],
            "next_action_after_learning": f"Return to execute: {step.name}"
        }
    
    def _generate_specific_instructions(self, step: WorkflowStep, context: Dict[str, Any]) -> List[str]:
        """Generate specific, actionable instructions for a step"""
        
        # This would use the step type and context to generate detailed instructions
        instructions = [
            f"1. Review: {step.description}",
            f"2. Prepare: Gather resources - {', '.join(step.resources_needed)}",
            f"3. Execute: Follow completion criteria",
            f"4. Validate: Check each completion criterion",
            f"5. Document: Record patterns and learning discovered",
            f"6. Share: Update micro_updates.log with progress"
        ]
        
        # Add context-specific instructions
        if "component_extraction" in step.description.lower():
            instructions.extend([
                "7. Analyze existing code for reusable patterns",
                "8. Design clean interfaces for extracted components",
                "9. Create documentation with usage examples",
                "10. Test component compatibility with existing systems"
            ])
        
        return instructions
    
    def _create_progress_tracker(self, step: WorkflowStep) -> Dict[str, Any]:
        """Create progress tracking system for a step"""
        
        return {
            "progress_indicators": [
                f"✅ {criterion}" for criterion in step.completion_criteria
            ],
            "time_tracking": {
                "estimated": step.estimated_time,
                "started": None,
                "completed": None,
                "time_spent": 0
            },
            "quality_checks": [
                "Code follows SuperInstance patterns",
                "Documentation is comprehensive",
                "Learning is captured and documented",
                "Integration points are identified"
            ]
        }
    
    def report_step_progress(self, bot_id: str, step_id: str, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Report progress on current step and get next guidance"""
        
        # Update step progress in database
        self._update_step_progress(bot_id, step_id, progress)
        
        # Analyze progress and determine next action
        if progress.get("status") == "completed":
            return self._handle_step_completion(bot_id, step_id, progress)
        elif progress.get("status") == "blocked":
            return self._handle_step_blocking(bot_id, step_id, progress)
        elif progress.get("status") == "needs_help":
            return self._handle_collaboration_request(bot_id, step_id, progress)
        else:
            return self._provide_progress_guidance(bot_id, step_id, progress)
    
    def _handle_step_completion(self, bot_id: str, step_id: str, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Handle completion of a workflow step"""
        
        # Capture learning from completed step
        learning_captured = progress.get("learning_captured", {})
        self._store_step_learning(bot_id, step_id, learning_captured)
        
        # Update workflow progress
        self._advance_workflow_progress(bot_id, step_id)
        
        # Get next action
        return self.get_next_action(bot_id, progress)
    
    def _handle_step_blocking(self, bot_id: str, step_id: str, progress: Dict[str, Any]) -> Dict[str, Any]:
        """Handle when bot gets blocked on a step"""
        
        obstacle = progress.get("obstacle", "Unknown obstacle")
        
        # Mark bot as blocked
        self._mark_bot_blocked(bot_id, obstacle)
        
        # Try to find unblocking strategy
        return self._create_unblocking_strategy(obstacle, self._load_bot_state(bot_id), progress)
    
    def _create_unblocking_strategy(self, obstacle: str, bot_state: BotState, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create strategy to overcome obstacle"""
        
        strategies = {
            "missing_information": {
                "strategy": "Research and information gathering",
                "actions": [
                    "Search SuperInstance knowledge base",
                    "Review similar completed projects",
                    "Request assistance from specialist bots"
                ]
            },
            "technical_complexity": {
                "strategy": "Break down and simplify",
                "actions": [
                    "Decompose complex task into smaller steps",
                    "Find simpler alternative approaches",
                    "Create prototype to test concepts"
                ]
            },
            "missing_skills": {
                "strategy": "Just-in-time learning",
                "actions": [
                    "Identify specific skills needed",
                    "Find learning resources and examples",
                    "Practice with simple examples first"
                ]
            },
            "integration_challenges": {
                "strategy": "Component-by-component approach",
                "actions": [
                    "Test each integration point separately",
                    "Create minimal working examples",
                    "Build integration step by step"
                ]
            }
        }
        
        # Classify obstacle type
        obstacle_type = self._classify_obstacle(obstacle, context)
        
        # Get appropriate strategy
        strategy = strategies.get(obstacle_type, strategies["technical_complexity"])
        
        return {
            "action_type": "unblock",
            "obstacle": obstacle,
            "strategy": strategy["strategy"],
            "specific_actions": strategy["actions"],
            "estimated_time": 45,  # minutes
            "success_indicators": [
                "Understanding of obstacle is clear",
                "Path forward is identified",
                "Required resources are available"
            ],
            "fallback_plan": "Request collaboration from other bots"
        }
    
    def _classify_obstacle(self, obstacle: str, context: Dict[str, Any]) -> str:
        """Classify type of obstacle to determine appropriate strategy"""
        
        obstacle_lower = obstacle.lower()
        
        if any(word in obstacle_lower for word in ["don't know", "unclear", "understand", "information"]):
            return "missing_information"
        elif any(word in obstacle_lower for word in ["complex", "difficult", "too hard", "overwhelming"]):
            return "technical_complexity"
        elif any(word in obstacle_lower for word in ["can't", "unable", "skill", "experience"]):
            return "missing_skills"
        elif any(word in obstacle_lower for word in ["integration", "connection", "compatibility", "interface"]):
            return "integration_challenges"
        else:
            return "technical_complexity"  # Default
    
    def _find_collaboration_opportunities(self, bot_id: str, current_task: str) -> List[Dict[str, Any]]:
        """Find other bots that can help with current task"""
        
        # This would analyze micro_updates.log and bot capabilities
        opportunities = [
            {
                "bot_type": "component_architect",
                "help_with": "Component design and extraction",
                "availability": "active",
                "expertise_match": 0.9
            },
            {
                "bot_type": "integration_specialist", 
                "help_with": "System integration challenges",
                "availability": "available",
                "expertise_match": 0.8
            }
        ]
        
        return opportunities
    
    def create_workflow_template(self, name: str, description: str, steps: List[Dict]) -> str:
        """Create reusable workflow template"""
        
        template_id = f"workflow_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO workflow_templates 
                (template_id, name, description, template_steps, use_cases, success_rate, average_completion_time, created_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                template_id,
                name,
                description,
                json.dumps(steps),
                json.dumps(["general_development", "component_creation"]),
                0.0,  # Will be updated based on usage
                sum(step.get("estimated_time", 30) for step in steps),
                datetime.datetime.now().isoformat()
            ))
        
        return template_id
    
    def _save_bot_state(self, bot_state: BotState):
        """Save bot state to database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO bot_states 
                (bot_id, current_skills, skill_levels, current_focus, available_time, 
                 collaboration_partners, learning_goals, blocked_on, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                bot_state.bot_id,
                json.dumps(bot_state.current_skills),
                json.dumps(bot_state.skill_levels),
                bot_state.current_focus,
                bot_state.available_time,
                json.dumps(bot_state.collaboration_partners),
                json.dumps(bot_state.learning_goals),
                bot_state.blocked_on,
                datetime.datetime.now().isoformat()
            ))

# Predefined workflow templates for common SuperInstance tasks
WORKFLOW_TEMPLATES = {
    "component_extraction": {
        "name": "Component Extraction Workflow",
        "description": "Extract reusable components from existing code",
        "steps": [
            {
                "step_id": "analyze_code",
                "name": "Code Analysis",
                "description": "Analyze existing code for reusable patterns",
                "prerequisites": [],
                "estimated_time": 45,
                "priority": "high",
                "completion_criteria": [
                    "Identified at least 3 reusable patterns",
                    "Documented pattern interfaces",
                    "Assessed reusability potential"
                ],
                "resources_needed": ["pattern_recognition", "code_analysis"],
                "learning_opportunities": ["Advanced pattern recognition", "Interface design"],
                "fallback_options": ["Start with simpler patterns", "Focus on one component type"]
            },
            {
                "step_id": "design_interfaces",
                "name": "Interface Design",
                "description": "Design clean, reusable interfaces for components",
                "prerequisites": ["analyze_code"],
                "estimated_time": 60,
                "priority": "high",
                "completion_criteria": [
                    "Interface contracts defined",
                    "Configuration options specified",
                    "Integration points identified"
                ],
                "resources_needed": ["interface_design", "api_design"],
                "learning_opportunities": ["Component architecture", "API design principles"],
                "fallback_options": ["Use existing interface patterns", "Simplify interface design"]
            },
            {
                "step_id": "extract_components",
                "name": "Component Extraction",
                "description": "Extract and implement reusable components",
                "prerequisites": ["design_interfaces"],
                "estimated_time": 90,
                "priority": "critical",
                "completion_criteria": [
                    "Components implemented with clean code",
                    "All interfaces working correctly",
                    "Components tested independently"
                ],
                "resources_needed": ["component_implementation", "testing"],
                "learning_opportunities": ["Clean code practices", "Component testing"],
                "fallback_options": ["Extract one component at a time", "Create minimal viable component"]
            },
            {
                "step_id": "document_components",
                "name": "Component Documentation",
                "description": "Create comprehensive documentation for components",
                "prerequisites": ["extract_components"],
                "estimated_time": 45,
                "priority": "medium",
                "completion_criteria": [
                    "Usage examples provided",
                    "Integration guide written",
                    "Configuration options documented"
                ],
                "resources_needed": ["technical_writing", "documentation_tools"],
                "learning_opportunities": ["Technical writing", "Educational content creation"],
                "fallback_options": ["Create basic documentation", "Use template format"]
            }
        ]
    }
}

def create_next_action_prompt(action: Dict[str, Any]) -> str:
    """Create clear, actionable prompt for bot's next action"""
    
    if action["action_type"] == "execute_step":
        return f"""
🎯 NEXT ACTION: {action['step_name']}
=======================================

📋 OBJECTIVE: {action['description']}

⚡ SPECIFIC INSTRUCTIONS:
{chr(10).join(f"{i+1}. {instruction}" for i, instruction in enumerate(action['specific_instructions']))}

✅ COMPLETION CRITERIA (Check each when done):
{chr(10).join(f"□ {criterion}" for criterion in action['completion_criteria'])}

⏱️ ESTIMATED TIME: {action['estimated_time']} minutes
🔥 PRIORITY: {action['priority'].upper()}

📚 LEARNING OPPORTUNITIES:
{chr(10).join(f"- {opportunity}" for opportunity in action['learning_opportunity'])}

🔧 RESOURCES AVAILABLE:
{chr(10).join(f"- {resource}" for resource in action['resources_available'])}

🆘 IF YOU GET STUCK:
{chr(10).join(f"- {fallback}" for fallback in action['fallback_options'])}

📊 PROGRESS TRACKING:
Update your progress by calling report_step_progress() with:
- Current status (in_progress/completed/blocked/needs_help)
- Work accomplished so far
- Any obstacles encountered
- Learning discoveries made

Ready to build amazing Lego components! 🧩
"""
    
    elif action["action_type"] == "skill_learning":
        return f"""
🎓 LEARNING ACTION: Skill Development
====================================

🎯 TARGET SKILLS: {', '.join(action['target_skills'])}
📋 LEARNING GOAL: {action['learning_goal']}

📚 LEARNING APPROACH:
{chr(10).join(f"- {step}" for step in action['learning_approach'])}

⏱️ ESTIMATED TIME: {action['estimated_learning_time']} minutes

🏋️ PRACTICE OPPORTUNITIES:
{chr(10).join(f"- {opportunity}" for opportunity in action['practice_opportunities'])}

✅ SUCCESS CRITERIA:
{chr(10).join(f"□ {criterion}" for criterion in action['success_criteria'])}

➡️ AFTER LEARNING: {action['next_action_after_learning']}

💡 REMEMBER: Every skill learned makes you more valuable to the SuperInstance network!
"""
    
    elif action["action_type"] == "unblock":
        return f"""
🔧 UNBLOCKING ACTION: Obstacle Resolution
========================================

🚧 OBSTACLE: {action['obstacle']}
📋 STRATEGY: {action['strategy']}

⚡ SPECIFIC ACTIONS:
{chr(10).join(f"{i+1}. {act}" for i, act in enumerate(action['specific_actions']))}

⏱️ ESTIMATED TIME: {action['estimated_time']} minutes

✅ SUCCESS INDICATORS:
{chr(10).join(f"□ {indicator}" for indicator in action['success_indicators'])}

🆘 FALLBACK PLAN: {action['fallback_plan']}

💪 REMEMBER: Every obstacle overcome makes the entire SuperInstance system stronger!
"""
    
    else:
        return f"""
🚀 ACTION: {action['action_type'].title()}
=========================

{action.get('description', 'Execute this action to continue progress')}

Follow the guidance provided and remember to document your learning!
"""

# Example usage
if __name__ == "__main__":
    # Initialize workflow system
    workflow_system = WorkflowProgressionSystem()
    
    # Get next action for a bot
    next_action = workflow_system.get_next_action(
        bot_id="component_architect_001",
        current_context={
            "task_focus": "Extract authentication patterns from services",
            "available_resources": ["auth-service", "user-management", "frontend"],
            "time_available": 120
        }
    )
    
    # Print actionable prompt
    print(create_next_action_prompt(next_action))