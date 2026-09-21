#!/usr/bin/env python3
"""
Claude Delegation Orchestrator
Manages Claude bots breaking down complex tasks for local AI assistant delegation
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
import os

from delegation_controller import HierarchicalTaskDelegator, DelegationResult, TaskComplexity
from prompt_optimization_engine import PromptOptimizationEngine, PromptPerformanceMetric

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SubTask:
    """Represents a subtask created from task breakdown"""
    id: str
    description: str
    complexity: TaskComplexity
    dependencies: List[str]  # IDs of subtasks this depends on
    file_context: Optional[str]
    language: str
    estimated_effort: int  # 1-10 scale
    priority: int  # 1-10, higher is more important

@dataclass
class TaskBreakdownResult:
    """Result of breaking down a complex task"""
    original_task: str
    subtasks: List[SubTask]
    execution_strategy: str
    total_estimated_time: int
    can_parallelize: bool
    claude_oversight_needed: bool

@dataclass
class DelegationSession:
    """Tracks a complete delegation session"""
    session_id: str
    original_task: str
    breakdown: TaskBreakdownResult
    subtask_results: Dict[str, DelegationResult]
    start_time: datetime
    end_time: Optional[datetime]
    overall_success: bool
    quality_score: float
    lessons_learned: List[str]

class TaskBreakdownEngine:
    """Breaks complex tasks into subtasks suitable for local assistants"""
    
    def __init__(self):
        self.breakdown_patterns = self._initialize_breakdown_patterns()
    
    def _initialize_breakdown_patterns(self) -> Dict[str, List[str]]:
        """Initialize patterns for breaking down different types of tasks"""
        return {
            "api_development": [
                "Design API endpoints structure",
                "Implement basic request handling",
                "Add input validation",
                "Implement business logic",
                "Add error handling",
                "Add authentication/authorization",
                "Add logging and monitoring",
                "Write API documentation",
                "Create unit tests",
                "Add integration tests"
            ],
            "ui_development": [
                "Design component structure",
                "Create basic HTML/JSX layout",
                "Add CSS styling",
                "Implement state management",
                "Add user interactions",
                "Implement data fetching",
                "Add form validation",
                "Add responsive design",
                "Implement error boundaries",
                "Add accessibility features",
                "Write component tests"
            ],
            "refactoring": [
                "Analyze current code structure",
                "Identify refactoring opportunities",
                "Extract common functions",
                "Rename variables/functions for clarity",
                "Simplify complex logic",
                "Add proper error handling",
                "Update documentation",
                "Add missing tests",
                "Verify functionality unchanged"
            ],
            "database_work": [
                "Design database schema",
                "Create migration scripts",
                "Implement data access layer",
                "Add query optimization",
                "Implement data validation",
                "Add error handling",
                "Create database tests",
                "Add indexing strategy",
                "Implement backup procedures"
            ],
            "testing": [
                "Analyze code to test",
                "Design test strategy",
                "Create unit tests",
                "Add integration tests",
                "Implement edge case tests",
                "Add performance tests",
                "Create test data fixtures",
                "Add test documentation"
            ]
        }
    
    def breakdown_task(self, task_description: str, file_context: Optional[str] = None) -> TaskBreakdownResult:
        """Break down a complex task into manageable subtasks"""
        
        # Classify the main task type
        task_type = self._classify_main_task_type(task_description)
        
        # Get appropriate breakdown pattern
        if task_type in self.breakdown_patterns:
            base_subtasks = self.breakdown_patterns[task_type]
        else:
            base_subtasks = self._generate_generic_breakdown(task_description)
        
        # Create specific subtasks
        subtasks = []
        for i, subtask_desc in enumerate(base_subtasks):
            # Customize subtask for specific context
            customized_desc = self._customize_subtask(subtask_desc, task_description, task_type)
            
            # Create subtask
            subtask = SubTask(
                id=f"subtask_{i+1}",
                description=customized_desc,
                complexity=TaskComplexity(score=25, category="simple", reasoning="Generated subtask", 
                                        estimated_time=300, requires_context=bool(file_context), can_delegate=True),
                dependencies=self._determine_dependencies(i, base_subtasks),
                file_context=file_context if i > 0 else None,  # First task gets full context
                language=self._detect_language(file_context or task_description),
                estimated_effort=self._estimate_effort(customized_desc),
                priority=self._calculate_priority(i, len(base_subtasks), customized_desc)
            )
            
            subtasks.append(subtask)
        
        # Determine execution strategy
        can_parallelize = self._can_parallelize_subtasks(subtasks)
        execution_strategy = "parallel" if can_parallelize else "sequential"
        
        # Calculate totals
        total_time = sum(st.complexity.estimated_time for st in subtasks)
        if can_parallelize:
            total_time = max(st.complexity.estimated_time for st in subtasks)  # Parallel execution
        
        claude_oversight = any(st.estimated_effort > 7 for st in subtasks)
        
        return TaskBreakdownResult(
            original_task=task_description,
            subtasks=subtasks,
            execution_strategy=execution_strategy,
            total_estimated_time=total_time,
            can_parallelize=can_parallelize,
            claude_oversight_needed=claude_oversight
        )
    
    def _classify_main_task_type(self, task: str) -> str:
        """Classify the main type of task"""
        task_lower = task.lower()
        
        if any(word in task_lower for word in ["api", "endpoint", "rest", "graphql", "service"]):
            return "api_development"
        elif any(word in task_lower for word in ["ui", "component", "react", "frontend", "interface"]):
            return "ui_development"
        elif any(word in task_lower for word in ["refactor", "cleanup", "improve", "restructure"]):
            return "refactoring"
        elif any(word in task_lower for word in ["database", "sql", "table", "schema", "migration"]):
            return "database_work"
        elif any(word in task_lower for word in ["test", "testing", "unit test", "integration"]):
            return "testing"
        else:
            return "general"
    
    def _generate_generic_breakdown(self, task: str) -> List[str]:
        """Generate generic breakdown for unclassified tasks"""
        return [
            "Analyze requirements and current state",
            "Design the solution approach",
            "Implement core functionality",
            "Add error handling and validation",
            "Add logging and debugging support",
            "Test the implementation",
            "Update documentation",
            "Perform final review and cleanup"
        ]
    
    def _customize_subtask(self, generic_subtask: str, main_task: str, task_type: str) -> str:
        """Customize generic subtask for specific context"""
        
        # Extract key terms from main task
        main_task_lower = main_task.lower()
        
        if "fitness" in main_task_lower:
            generic_subtask = generic_subtask.replace("API", "fitness tracking API")
            generic_subtask = generic_subtask.replace("component", "fitness dashboard component")
        
        if "user" in main_task_lower:
            generic_subtask = generic_subtask.replace("data", "user data")
            generic_subtask = generic_subtask.replace("validation", "user input validation")
        
        return f"{generic_subtask} for {main_task[:50]}..." if len(main_task) > 50 else f"{generic_subtask} for {main_task}"
    
    def _determine_dependencies(self, current_index: int, all_subtasks: List[str]) -> List[str]:
        """Determine dependencies for a subtask"""
        dependencies = []
        
        # Simple dependency logic - each task depends on previous ones for certain patterns
        if current_index > 0:
            current_desc = all_subtasks[current_index].lower()
            
            # Tasks that typically depend on design/planning phases
            if any(word in current_desc for word in ["implement", "add", "create", "write"]):
                if current_index > 0 and any(word in all_subtasks[0].lower() for word in ["design", "analyze", "plan"]):
                    dependencies.append("subtask_1")
            
            # Testing typically depends on implementation
            if "test" in current_desc and current_index > 2:
                dependencies.extend([f"subtask_{i+1}" for i in range(current_index-2, current_index)])
        
        return dependencies
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language from content"""
        if not content:
            return "python"
        
        content_lower = content.lower()
        
        if "def " in content or "import " in content or ".py" in content:
            return "python"
        elif "function" in content or "const " in content or ".js" in content:
            return "javascript"
        elif "interface" in content or "class " in content and ".ts" in content:
            return "typescript"
        elif "public class" in content or ".java" in content:
            return "java"
        else:
            return "python"  # Default
    
    def _estimate_effort(self, subtask_desc: str) -> int:
        """Estimate effort for subtask (1-10 scale)"""
        desc_lower = subtask_desc.lower()
        
        # High effort tasks
        if any(word in desc_lower for word in ["design", "architecture", "algorithm", "complex"]):
            return 8
        
        # Medium effort tasks
        elif any(word in desc_lower for word in ["implement", "create", "develop"]):
            return 6
        
        # Lower effort tasks
        elif any(word in desc_lower for word in ["add", "update", "modify", "fix"]):
            return 4
        
        # Simple tasks
        elif any(word in desc_lower for word in ["rename", "format", "comment", "document"]):
            return 2
        
        return 5  # Default medium
    
    def _calculate_priority(self, index: int, total_tasks: int, subtask_desc: str) -> int:
        """Calculate priority for subtask (1-10, higher is more important)"""
        desc_lower = subtask_desc.lower()
        
        # Foundation tasks are high priority
        if any(word in desc_lower for word in ["design", "structure", "schema", "analyze"]):
            return 9
        
        # Core implementation is medium-high priority
        elif any(word in desc_lower for word in ["implement", "create", "develop"]):
            return 7
        
        # Polish tasks are lower priority
        elif any(word in desc_lower for word in ["document", "test", "cleanup"]):
            return 4
        
        # Earlier tasks generally higher priority
        return max(8 - index, 3)
    
    def _can_parallelize_subtasks(self, subtasks: List[SubTask]) -> bool:
        """Determine if subtasks can be executed in parallel"""
        
        # Check dependency chains
        total_dependencies = sum(len(st.dependencies) for st in subtasks)
        
        # If few dependencies, can parallelize
        if total_dependencies < len(subtasks) * 0.3:
            return True
        
        # Check if any subtasks have no dependencies
        independent_tasks = [st for st in subtasks if not st.dependencies]
        
        return len(independent_tasks) > 1

class ClaudeDelegationOrchestrator:
    """Main orchestrator for Claude delegation to local assistants"""
    
    def __init__(self, claude_api_key: Optional[str] = None):
        self.api_key = claude_api_key or os.getenv("ANTHROPIC_API_KEY")
        self.breakdown_engine = TaskBreakdownEngine()
        self.delegator = HierarchicalTaskDelegator()
        self.prompt_optimizer = PromptOptimizationEngine()
        self.active_sessions: Dict[str, DelegationSession] = {}
        
    async def execute_delegated_task(self, task_description: str, file_context: Optional[str] = None) -> DelegationSession:
        """Execute a task using Claude delegation to local assistants"""
        
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"🚀 Starting delegation session {session_id}")
        
        # Step 1: Break down the task
        logger.info("📋 Breaking down task into subtasks...")
        breakdown = self.breakdown_engine.breakdown_task(task_description, file_context)
        
        # Create session
        session = DelegationSession(
            session_id=session_id,
            original_task=task_description,
            breakdown=breakdown,
            subtask_results={},
            start_time=datetime.now(),
            end_time=None,
            overall_success=True,
            quality_score=0.0,
            lessons_learned=[]
        )
        
        self.active_sessions[session_id] = session
        
        # Step 2: Execute subtasks
        logger.info(f"🔧 Executing {len(breakdown.subtasks)} subtasks ({breakdown.execution_strategy} mode)")
        
        if breakdown.execution_strategy == "parallel":
            await self._execute_parallel_subtasks(session)
        else:
            await self._execute_sequential_subtasks(session)
        
        # Step 3: Finalize session
        session.end_time = datetime.now()
        session.quality_score = self._calculate_overall_quality(session)
        session.overall_success = all(result.success for result in session.subtask_results.values())
        
        # Learn from the session
        await self._learn_from_session(session)
        
        logger.info(f"✅ Delegation session completed: Success={session.overall_success}, Quality={session.quality_score:.1f}")
        
        return session
    
    async def _execute_parallel_subtasks(self, session: DelegationSession):
        """Execute subtasks in parallel"""
        
        # Group subtasks by dependency level
        dependency_levels = self._organize_by_dependency_levels(session.breakdown.subtasks)
        
        for level, subtasks in dependency_levels.items():
            logger.info(f"📊 Executing dependency level {level} ({len(subtasks)} tasks)")
            
            # Execute all tasks at this level in parallel
            tasks = []
            for subtask in subtasks:
                task = self._execute_single_subtask(session, subtask)
                tasks.append(task)
            
            # Wait for all tasks at this level to complete
            level_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for subtask, result in zip(subtasks, level_results):
                if isinstance(result, Exception):
                    logger.error(f"❌ Subtask {subtask.id} failed: {result}")
                    session.subtask_results[subtask.id] = DelegationResult(
                        success=False,
                        assistant_used="error",
                        execution_time=0,
                        quality_score=0,
                        output=str(result),
                        lessons_learned=f"Subtask execution failed: {result}",
                        should_retry_with_claude=True
                    )
                else:
                    session.subtask_results[subtask.id] = result
    
    async def _execute_sequential_subtasks(self, session: DelegationSession):
        """Execute subtasks sequentially"""
        
        for subtask in session.breakdown.subtasks:
            logger.info(f"🔧 Executing subtask: {subtask.description[:60]}...")
            
            result = await self._execute_single_subtask(session, subtask)
            session.subtask_results[subtask.id] = result
            
            # Check if we should continue
            if not result.success and subtask.priority > 7:
                logger.warning(f"⚠️ High-priority subtask failed, considering early termination")
                # Could implement early termination logic here
    
    async def _execute_single_subtask(self, session: DelegationSession, subtask: SubTask) -> DelegationResult:
        """Execute a single subtask"""
        
        # Optimize prompt for local assistant
        optimization = self.prompt_optimizer.optimize_prompt(
            subtask.description,
            "continue",  # Default assistant for now
            subtask.file_context,
            subtask.language
        )
        
        # Delegate to local assistant
        result = await self.delegator.delegate_task(
            optimization.optimized_prompt,
            None,  # file_path
            subtask.file_context
        )
        
        # Learn from the result
        performance = PromptPerformanceMetric(
            prompt_id=f"{session.session_id}_{subtask.id}",
            assistant_used=result.assistant_used,
            task_type=self.breakdown_engine._classify_main_task_type(subtask.description),
            success=result.success,
            quality_score=result.quality_score,
            execution_time=result.execution_time,
            user_feedback=None,
            timestamp=datetime.now()
        )
        
        self.prompt_optimizer.learn_from_result(performance)
        
        return result
    
    def _organize_by_dependency_levels(self, subtasks: List[SubTask]) -> Dict[int, List[SubTask]]:
        """Organize subtasks by dependency levels for parallel execution"""
        levels = {}
        task_levels = {}
        
        def get_task_level(task_id: str) -> int:
            if task_id in task_levels:
                return task_levels[task_id]
            
            task = next(t for t in subtasks if t.id == task_id)
            if not task.dependencies:
                task_levels[task_id] = 0
                return 0
            
            max_dep_level = max(get_task_level(dep_id) for dep_id in task.dependencies)
            task_levels[task_id] = max_dep_level + 1
            return max_dep_level + 1
        
        # Calculate levels for all tasks
        for subtask in subtasks:
            level = get_task_level(subtask.id)
            if level not in levels:
                levels[level] = []
            levels[level].append(subtask)
        
        return levels
    
    def _calculate_overall_quality(self, session: DelegationSession) -> float:
        """Calculate overall quality score for the session"""
        if not session.subtask_results:
            return 0.0
        
        results = list(session.subtask_results.values())
        
        # Weight by subtask priority
        weighted_scores = []
        total_weight = 0
        
        for subtask in session.breakdown.subtasks:
            if subtask.id in session.subtask_results:
                result = session.subtask_results[subtask.id]
                weight = subtask.priority
                weighted_scores.append(result.quality_score * weight)
                total_weight += weight
        
        return sum(weighted_scores) / total_weight if total_weight > 0 else 0.0
    
    async def _learn_from_session(self, session: DelegationSession):
        """Learn patterns from completed session"""
        
        lessons = []
        
        # Analyze success patterns
        successful_subtasks = [st for st in session.breakdown.subtasks 
                             if st.id in session.subtask_results and session.subtask_results[st.id].success]
        
        failed_subtasks = [st for st in session.breakdown.subtasks 
                          if st.id in session.subtask_results and not session.subtask_results[st.id].success]
        
        if successful_subtasks:
            lessons.append(f"Successfully delegated {len(successful_subtasks)} subtasks to local assistants")
        
        if failed_subtasks:
            lessons.append(f"Failed to delegate {len(failed_subtasks)} subtasks - may need Claude intervention")
        
        # Analyze time efficiency
        total_time = sum(result.execution_time for result in session.subtask_results.values())
        if total_time < session.breakdown.total_estimated_time * 0.8:
            lessons.append("Delegation was more efficient than estimated")
        elif total_time > session.breakdown.total_estimated_time * 1.5:
            lessons.append("Delegation took longer than expected - review task breakdown")
        
        # Analyze quality patterns
        avg_quality = session.quality_score
        if avg_quality > 8.0:
            lessons.append("High quality results from local assistant delegation")
        elif avg_quality < 6.0:
            lessons.append("Quality concerns with local assistant delegation")
        
        session.lessons_learned = lessons
    
    def get_session_report(self, session_id: str) -> Dict[str, Any]:
        """Get detailed report for a delegation session"""
        
        if session_id not in self.active_sessions:
            return {"error": "Session not found"}
        
        session = self.active_sessions[session_id]
        
        return {
            "session_id": session_id,
            "original_task": session.original_task,
            "execution_strategy": session.breakdown.execution_strategy,
            "subtask_count": len(session.breakdown.subtasks),
            "overall_success": session.overall_success,
            "quality_score": session.quality_score,
            "execution_time": (session.end_time - session.start_time).total_seconds() if session.end_time else None,
            "subtask_results": [
                {
                    "id": st.id,
                    "description": st.description[:60] + "...",
                    "success": session.subtask_results[st.id].success if st.id in session.subtask_results else False,
                    "assistant_used": session.subtask_results[st.id].assistant_used if st.id in session.subtask_results else "none",
                    "quality": session.subtask_results[st.id].quality_score if st.id in session.subtask_results else 0
                }
                for st in session.breakdown.subtasks
            ],
            "lessons_learned": session.lessons_learned
        }
    
    def get_delegation_insights(self) -> Dict[str, Any]:
        """Get insights across all delegation sessions"""
        
        if not self.active_sessions:
            return {"message": "No delegation sessions available"}
        
        sessions = list(self.active_sessions.values())
        completed_sessions = [s for s in sessions if s.end_time is not None]
        
        if not completed_sessions:
            return {"message": "No completed delegation sessions"}
        
        # Overall statistics
        total_subtasks = sum(len(s.breakdown.subtasks) for s in completed_sessions)
        successful_sessions = sum(1 for s in completed_sessions if s.overall_success)
        avg_quality = sum(s.quality_score for s in completed_sessions) / len(completed_sessions)
        
        # Assistant usage patterns
        assistant_usage = {}
        for session in completed_sessions:
            for result in session.subtask_results.values():
                assistant = result.assistant_used
                if assistant not in assistant_usage:
                    assistant_usage[assistant] = {"count": 0, "success_rate": 0, "avg_quality": 0}
                
                assistant_usage[assistant]["count"] += 1
                if result.success:
                    assistant_usage[assistant]["success_rate"] += 1
                assistant_usage[assistant]["avg_quality"] += result.quality_score
        
        # Calculate averages
        for assistant in assistant_usage:
            stats = assistant_usage[assistant]
            stats["success_rate"] = stats["success_rate"] / stats["count"] if stats["count"] > 0 else 0
            stats["avg_quality"] = stats["avg_quality"] / stats["count"] if stats["count"] > 0 else 0
        
        return {
            "total_sessions": len(completed_sessions),
            "successful_sessions": successful_sessions,
            "session_success_rate": successful_sessions / len(completed_sessions),
            "total_subtasks_delegated": total_subtasks,
            "average_quality_score": avg_quality,
            "assistant_usage_patterns": assistant_usage,
            "common_lessons": self._extract_common_lessons(completed_sessions)
        }
    
    def _extract_common_lessons(self, sessions: List[DelegationSession]) -> List[str]:
        """Extract common lessons learned across sessions"""
        
        all_lessons = []
        for session in sessions:
            all_lessons.extend(session.lessons_learned)
        
        # Count frequency of similar lessons
        lesson_patterns = {}
        for lesson in all_lessons:
            # Simple pattern matching
            if "efficient" in lesson.lower():
                lesson_patterns["efficiency"] = lesson_patterns.get("efficiency", 0) + 1
            elif "quality" in lesson.lower():
                lesson_patterns["quality"] = lesson_patterns.get("quality", 0) + 1
            elif "failed" in lesson.lower() or "fail" in lesson.lower():
                lesson_patterns["failures"] = lesson_patterns.get("failures", 0) + 1
        
        # Return most common patterns
        return [f"{pattern}: {count} occurrences" for pattern, count in sorted(lesson_patterns.items(), key=lambda x: x[1], reverse=True)]

# Test the orchestrator
async def main():
    """Test the delegation orchestrator"""
    
    orchestrator = ClaudeDelegationOrchestrator()
    
    test_task = """
    Create a comprehensive fitness tracking API that allows users to log workouts, 
    track progress, and get AI-powered insights. The API should include user 
    authentication, data validation, real-time updates, and integration with 
    wearable devices.
    """
    
    print("🎯 Claude Delegation Orchestrator")
    print("=================================")
    
    # Execute the delegated task
    session = await orchestrator.execute_delegated_task(test_task)
    
    # Get session report
    report = orchestrator.get_session_report(session.session_id)
    
    print(f"\n📋 Session Report:")
    print(json.dumps(report, indent=2, default=str))
    
    # Get overall insights
    insights = orchestrator.get_delegation_insights()
    
    print(f"\n📊 Delegation Insights:")
    print(json.dumps(insights, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())