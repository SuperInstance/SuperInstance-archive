"""
Advanced Task Decomposition Engine
Intelligently breaks down complex tasks into smaller, manageable subtasks
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from ..director.claude_director import Task, TaskPriority, TaskStatus
from ..integrations.local_llm_connector import LocalLLMConnector

logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    TRIVIAL = 1      # Single-step tasks
    SIMPLE = 2       # 2-3 step tasks
    MODERATE = 3     # 4-7 step tasks
    COMPLEX = 4      # 8-15 step tasks
    EXPERT = 5       # 15+ step tasks

class TaskCategory(Enum):
    CODE_DEVELOPMENT = "code_development"
    DATA_ANALYSIS = "data_analysis"
    RESEARCH = "research"
    CONTENT_CREATION = "content_creation"
    SYSTEM_ADMINISTRATION = "system_administration"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    PROJECT_MANAGEMENT = "project_management"
    GENERAL = "general"

@dataclass
class TaskAnalysis:
    """Analysis result for a task"""
    complexity: TaskComplexity
    category: TaskCategory
    estimated_steps: int
    skill_requirements: List[str]
    dependencies: List[str]
    parallel_opportunities: List[str]
    risk_factors: List[str]
    confidence_score: float
    reasoning: str

@dataclass
class Subtask:
    """Detailed subtask definition"""
    id: str
    description: str
    category: TaskCategory
    complexity: TaskComplexity
    estimated_tokens: int
    estimated_time_minutes: int
    dependencies: List[str]
    prerequisite_skills: List[str]
    success_criteria: List[str]
    risk_level: float
    can_parallelize: bool
    preferred_model_type: str  # local, claude-haiku, claude-sonnet, claude-opus
    priority_adjustment: float  # Relative to parent task priority

@dataclass 
class DecompositionResult:
    """Result of task decomposition"""
    original_task_id: str
    subtasks: List[Subtask]
    execution_plan: Dict[str, Any]
    total_estimated_time: int
    total_estimated_cost: float
    success_probability: float
    decomposition_strategy: str

class TaskDecompositionEngine:
    """Advanced engine for breaking down complex tasks"""
    
    def __init__(self, claude_api, local_llm_connector: Optional[LocalLLMConnector] = None):
        self.claude_api = claude_api
        self.local_llm_connector = local_llm_connector
        
        # Pattern recognition for common task types
        self.task_patterns = {
            TaskCategory.CODE_DEVELOPMENT: [
                r"implement|code|develop|build.*function|create.*class|write.*script",
                r"fix.*bug|debug|refactor|optimize.*code",
                r"add.*feature|enhance.*functionality"
            ],
            TaskCategory.DATA_ANALYSIS: [
                r"analyze.*data|process.*dataset|statistics|metrics",
                r"visualize|chart|graph|plot",
                r"clean.*data|transform.*data|etl"
            ],
            TaskCategory.RESEARCH: [
                r"research|investigate|find.*information|study",
                r"compare|evaluate.*options|survey",
                r"gather.*requirements|collect.*data"
            ],
            TaskCategory.CONTENT_CREATION: [
                r"write.*article|create.*content|draft",
                r"design.*document|compose|author",
                r"translate|summarize|rewrite"
            ],
            TaskCategory.SYSTEM_ADMINISTRATION: [
                r"deploy|configure|setup.*system|install",
                r"monitor|maintain|backup|restore",
                r"manage.*server|administer|provision"
            ],
            TaskCategory.TESTING: [
                r"test|validate|verify|check",
                r"quality.*assurance|qa|review",
                r"benchmark|performance.*test"
            ],
            TaskCategory.DOCUMENTATION: [
                r"document|readme|manual|guide",
                r"api.*documentation|specification",
                r"help.*text|tutorial|instruction"
            ]
        }
        
        # Complexity indicators
        self.complexity_indicators = {
            TaskComplexity.TRIVIAL: [
                r"simple|basic|quick|easy|straightforward"
            ],
            TaskComplexity.SIMPLE: [
                r"update|modify|small.*change|minor",
                r"single.*file|one.*function|brief"
            ],
            TaskComplexity.MODERATE: [
                r"multiple.*files?|several.*components?",
                r"integrate|connect|coordinate",
                r"medium.*size|moderate.*complexity"
            ],
            TaskComplexity.COMPLEX: [
                r"system|architecture|comprehensive",
                r"multiple.*systems?|end.*to.*end|full.*implementation",
                r"complex|sophisticated|advanced"
            ],
            TaskComplexity.EXPERT: [
                r"enterprise|scalable|production.*ready",
                r"distributed|microservices|large.*scale",
                r"optimization|performance.*critical|high.*availability"
            ]
        }
        
        # Decomposition templates for different categories
        self.decomposition_templates = {
            TaskCategory.CODE_DEVELOPMENT: {
                "phases": ["planning", "design", "implementation", "testing", "documentation"],
                "typical_subtasks": {
                    "planning": ["analyze_requirements", "define_scope", "identify_dependencies"],
                    "design": ["create_architecture", "design_interfaces", "plan_data_structures"],
                    "implementation": ["write_core_logic", "implement_features", "handle_edge_cases"],
                    "testing": ["unit_tests", "integration_tests", "manual_testing"],
                    "documentation": ["code_comments", "api_docs", "usage_examples"]
                }
            },
            TaskCategory.DATA_ANALYSIS: {
                "phases": ["data_collection", "data_preparation", "analysis", "visualization", "reporting"],
                "typical_subtasks": {
                    "data_collection": ["identify_sources", "extract_data", "validate_data_quality"],
                    "data_preparation": ["clean_data", "transform_data", "handle_missing_values"],
                    "analysis": ["exploratory_analysis", "statistical_analysis", "pattern_detection"],
                    "visualization": ["create_charts", "design_dashboards", "interactive_plots"],
                    "reporting": ["summarize_findings", "create_presentation", "document_methodology"]
                }
            },
            TaskCategory.RESEARCH: {
                "phases": ["planning", "information_gathering", "analysis", "synthesis", "reporting"],
                "typical_subtasks": {
                    "planning": ["define_research_questions", "identify_sources", "create_methodology"],
                    "information_gathering": ["literature_review", "data_collection", "interviews"],
                    "analysis": ["categorize_information", "identify_patterns", "evaluate_credibility"],
                    "synthesis": ["combine_findings", "draw_conclusions", "identify_gaps"],
                    "reporting": ["write_report", "create_summary", "prepare_recommendations"]
                }
            }
        }
    
    async def analyze_task(self, task: Task) -> TaskAnalysis:
        """Analyze a task to understand its complexity and requirements"""
        description = task.description.lower()
        
        # Determine category
        category = self._categorize_task(description)
        
        # Estimate complexity
        complexity = self._estimate_complexity(description, task.estimated_tokens)
        
        # Estimate steps
        estimated_steps = self._estimate_steps(complexity, category)
        
        # Identify skill requirements
        skill_requirements = self._identify_skills(description, category)
        
        # Detect dependencies
        dependencies = self._detect_dependencies(description)
        
        # Find parallel opportunities
        parallel_opportunities = self._find_parallel_opportunities(description, category)
        
        # Assess risk factors
        risk_factors = self._assess_risks(description, complexity)
        
        # Calculate confidence
        confidence_score = self._calculate_confidence(task, category, complexity)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(task, category, complexity, estimated_steps)
        
        return TaskAnalysis(
            complexity=complexity,
            category=category,
            estimated_steps=estimated_steps,
            skill_requirements=skill_requirements,
            dependencies=dependencies,
            parallel_opportunities=parallel_opportunities,
            risk_factors=risk_factors,
            confidence_score=confidence_score,
            reasoning=reasoning
        )
    
    async def decompose_task(self, task: Task) -> DecompositionResult:
        """Decompose a task into subtasks"""
        # First analyze the task
        analysis = await self.analyze_task(task)
        
        # Choose decomposition strategy
        if analysis.complexity == TaskComplexity.TRIVIAL:
            return self._create_trivial_decomposition(task, analysis)
        elif analysis.complexity == TaskComplexity.SIMPLE:
            return await self._create_simple_decomposition(task, analysis)
        else:
            return await self._create_complex_decomposition(task, analysis)
    
    def _categorize_task(self, description: str) -> TaskCategory:
        """Categorize task based on description"""
        for category, patterns in self.task_patterns.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return category
        return TaskCategory.GENERAL
    
    def _estimate_complexity(self, description: str, estimated_tokens: int) -> TaskComplexity:
        """Estimate task complexity"""
        # Check for explicit complexity indicators
        for complexity, patterns in self.complexity_indicators.items():
            for pattern in patterns:
                if re.search(pattern, description, re.IGNORECASE):
                    return complexity
        
        # Use token count as fallback
        if estimated_tokens < 500:
            return TaskComplexity.TRIVIAL
        elif estimated_tokens < 1500:
            return TaskComplexity.SIMPLE
        elif estimated_tokens < 5000:
            return TaskComplexity.MODERATE
        elif estimated_tokens < 15000:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPERT
    
    def _estimate_steps(self, complexity: TaskComplexity, category: TaskCategory) -> int:
        """Estimate number of steps required"""
        base_steps = {
            TaskComplexity.TRIVIAL: 1,
            TaskComplexity.SIMPLE: 3,
            TaskComplexity.MODERATE: 6,
            TaskComplexity.COMPLEX: 12,
            TaskComplexity.EXPERT: 20
        }
        
        # Adjust based on category
        category_multipliers = {
            TaskCategory.CODE_DEVELOPMENT: 1.2,
            TaskCategory.DATA_ANALYSIS: 1.1,
            TaskCategory.RESEARCH: 1.3,
            TaskCategory.SYSTEM_ADMINISTRATION: 1.1,
            TaskCategory.GENERAL: 1.0
        }
        
        steps = base_steps[complexity] * category_multipliers.get(category, 1.0)
        return max(1, int(steps))
    
    def _identify_skills(self, description: str, category: TaskCategory) -> List[str]:
        """Identify required skills"""
        skill_patterns = {
            "programming": r"code|develop|implement|function|class|script",
            "data_analysis": r"data|statistics|analysis|metrics|visualization",
            "research": r"research|investigate|study|survey|information",
            "writing": r"write|document|draft|compose|content",
            "system_admin": r"deploy|configure|server|system|infrastructure",
            "testing": r"test|qa|validate|verify|quality",
            "design": r"design|architecture|plan|structure|ui|ux"
        }
        
        skills = []
        for skill, pattern in skill_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                skills.append(skill)
        
        return skills or ["general"]
    
    def _detect_dependencies(self, description: str) -> List[str]:
        """Detect task dependencies"""
        dependency_patterns = [
            r"after|once|when.*complete|depends.*on|requires.*first",
            r"prerequisite|before.*can|need.*to.*finish",
            r"blocking|blocked.*by|waiting.*for"
        ]
        
        dependencies = []
        for pattern in dependency_patterns:
            if re.search(pattern, description, re.IGNORECASE):
                dependencies.append("sequential_dependency")
        
        return dependencies
    
    def _find_parallel_opportunities(self, description: str, category: TaskCategory) -> List[str]:
        """Find opportunities for parallel execution"""
        parallel_indicators = [
            r"multiple|several|various|different",
            r"independent|separate|isolated",
            r"parallel|concurrent|simultaneously"
        ]
        
        opportunities = []
        for indicator in parallel_indicators:
            if re.search(indicator, description, re.IGNORECASE):
                opportunities.append("parallel_execution_possible")
        
        # Category-specific parallel opportunities
        if category == TaskCategory.CODE_DEVELOPMENT:
            opportunities.append("parallel_module_development")
        elif category == TaskCategory.DATA_ANALYSIS:
            opportunities.append("parallel_data_processing")
        elif category == TaskCategory.TESTING:
            opportunities.append("parallel_test_execution")
        
        return opportunities
    
    def _assess_risks(self, description: str, complexity: TaskComplexity) -> List[str]:
        """Assess risk factors"""
        risk_patterns = {
            "high_complexity": r"complex|sophisticated|advanced|difficult",
            "time_pressure": r"urgent|asap|quickly|deadline|rush",
            "external_dependency": r"api|external|third.*party|integration",
            "new_technology": r"new|unfamiliar|first.*time|experimental",
            "legacy_system": r"legacy|old|deprecated|outdated",
            "critical_system": r"critical|production|live|important"
        }
        
        risks = []
        for risk_type, pattern in risk_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                risks.append(risk_type)
        
        # Add complexity-based risks
        if complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]:
            risks.append("high_complexity_risk")
        
        return risks
    
    def _calculate_confidence(self, task: Task, category: TaskCategory, complexity: TaskComplexity) -> float:
        """Calculate confidence in decomposition"""
        base_confidence = 0.8
        
        # Adjust based on category familiarity
        category_confidence = {
            TaskCategory.CODE_DEVELOPMENT: 0.9,
            TaskCategory.DATA_ANALYSIS: 0.85,
            TaskCategory.RESEARCH: 0.8,
            TaskCategory.CONTENT_CREATION: 0.85,
            TaskCategory.TESTING: 0.9,
            TaskCategory.GENERAL: 0.7
        }
        
        # Adjust based on complexity
        complexity_penalty = {
            TaskComplexity.TRIVIAL: 0.0,
            TaskComplexity.SIMPLE: 0.0,
            TaskComplexity.MODERATE: -0.1,
            TaskComplexity.COMPLEX: -0.2,
            TaskComplexity.EXPERT: -0.3
        }
        
        confidence = category_confidence.get(category, base_confidence)
        confidence += complexity_penalty.get(complexity, 0)
        
        # Adjust based on description clarity
        description_words = len(task.description.split())
        if description_words < 5:
            confidence -= 0.2  # Very brief descriptions are harder to decompose
        elif description_words > 100:
            confidence -= 0.1  # Very long descriptions may be unclear
        
        return max(0.1, min(1.0, confidence))
    
    def _generate_reasoning(self, task: Task, category: TaskCategory, complexity: TaskComplexity, steps: int) -> str:
        """Generate reasoning for the analysis"""
        return f"""
        Task categorized as {category.value} with {complexity.name} complexity.
        Estimated {steps} steps required based on task description analysis.
        Priority: {task.priority.name}
        Token estimate: {task.estimated_tokens}
        
        Decomposition approach: {'Template-based' if category != TaskCategory.GENERAL else 'Pattern-based'}
        """
    
    def _create_trivial_decomposition(self, task: Task, analysis: TaskAnalysis) -> DecompositionResult:
        """Create decomposition for trivial tasks (no decomposition needed)"""
        single_subtask = Subtask(
            id=f"{task.id}_single",
            description=task.description,
            category=analysis.category,
            complexity=analysis.complexity,
            estimated_tokens=task.estimated_tokens,
            estimated_time_minutes=5,
            dependencies=[],
            prerequisite_skills=analysis.skill_requirements,
            success_criteria=["Task completed successfully"],
            risk_level=0.1,
            can_parallelize=False,
            preferred_model_type="local" if analysis.complexity == TaskComplexity.TRIVIAL else "claude-haiku",
            priority_adjustment=0.0
        )
        
        return DecompositionResult(
            original_task_id=task.id,
            subtasks=[single_subtask],
            execution_plan={"strategy": "single_step", "parallel_groups": []},
            total_estimated_time=5,
            total_estimated_cost=0.0 if single_subtask.preferred_model_type == "local" else 0.01,
            success_probability=0.95,
            decomposition_strategy="no_decomposition"
        )
    
    async def _create_simple_decomposition(self, task: Task, analysis: TaskAnalysis) -> DecompositionResult:
        """Create decomposition for simple tasks"""
        # Use local LLM for simple decomposition if available
        if self.local_llm_connector and self.local_llm_connector.connected:
            try:
                return await self._llm_assisted_decomposition(task, analysis, prefer_local=True)
            except Exception as e:
                logger.warning(f"Local LLM decomposition failed: {e}")
        
        # Fallback to template-based decomposition
        return self._template_based_decomposition(task, analysis)
    
    async def _create_complex_decomposition(self, task: Task, analysis: TaskAnalysis) -> DecompositionResult:
        """Create decomposition for complex tasks"""
        # Use Claude for complex decomposition
        try:
            return await self._llm_assisted_decomposition(task, analysis, prefer_local=False)
        except Exception as e:
            logger.error(f"LLM-assisted decomposition failed: {e}")
            return self._template_based_decomposition(task, analysis)
    
    async def _llm_assisted_decomposition(self, task: Task, analysis: TaskAnalysis, prefer_local: bool = False) -> DecompositionResult:
        """Use LLM to assist with task decomposition"""
        decomposition_prompt = self._build_decomposition_prompt(task, analysis)
        
        subtasks_text = ""
        if prefer_local and self.local_llm_connector:
            # Try local LLM first
            request = {
                "task_id": f"decompose_{task.id}",
                "description": decomposition_prompt,
                "task_type": "reasoning",
                "max_tokens": 3000,
                "temperature": 0.2
            }
            
            result = await self.local_llm_connector.execute_task(request)
            if result["success"]:
                subtasks_text = result["response"]
        
        # Fallback to Claude if local failed or not preferred
        if not subtasks_text and self.claude_api:
            subtasks_text = await self.claude_api.complete(decomposition_prompt, max_tokens=3000)
        
        if not subtasks_text:
            raise Exception("No LLM response for decomposition")
        
        return self._parse_llm_decomposition(task, analysis, subtasks_text)
    
    def _build_decomposition_prompt(self, task: Task, analysis: TaskAnalysis) -> str:
        """Build prompt for LLM-assisted decomposition"""
        return f"""
        Break down this task into detailed subtasks:
        
        TASK: {task.description}
        CATEGORY: {analysis.category.value}
        COMPLEXITY: {analysis.complexity.name}
        PRIORITY: {task.priority.name}
        ESTIMATED STEPS: {analysis.estimated_steps}
        
        Return a JSON array of subtasks with this exact format:
        [
            {{
                "id": "unique_subtask_id",
                "description": "Clear, actionable subtask description",
                "estimated_tokens": 1000,
                "estimated_time_minutes": 30,
                "dependencies": ["other_subtask_id"],
                "success_criteria": ["Specific success criterion"],
                "risk_level": 0.3,
                "can_parallelize": true,
                "preferred_model_type": "local|claude-haiku|claude-sonnet|claude-opus"
            }}
        ]
        
        Guidelines:
        1. Create {analysis.estimated_steps} subtasks maximum
        2. Each subtask should be independently executable
        3. Prefer "local" model_type for simple tasks
        4. Use specific, measurable success criteria
        5. Consider parallel execution opportunities
        6. Keep token estimates realistic (500-2000 per subtask)
        """
    
    def _parse_llm_decomposition(self, task: Task, analysis: TaskAnalysis, llm_response: str) -> DecompositionResult:
        """Parse LLM response into decomposition result"""
        try:
            # Extract JSON from response
            json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON array found in LLM response")
            
            subtasks_data = json.loads(json_match.group())
            
            subtasks = []
            total_time = 0
            total_cost = 0.0
            
            for i, subtask_data in enumerate(subtasks_data):
                subtask = Subtask(
                    id=subtask_data.get("id", f"{task.id}_sub_{i}"),
                    description=subtask_data["description"],
                    category=analysis.category,
                    complexity=TaskComplexity.SIMPLE,  # Subtasks are simpler
                    estimated_tokens=subtask_data.get("estimated_tokens", 1000),
                    estimated_time_minutes=subtask_data.get("estimated_time_minutes", 30),
                    dependencies=subtask_data.get("dependencies", []),
                    prerequisite_skills=analysis.skill_requirements,
                    success_criteria=subtask_data.get("success_criteria", ["Task completed"]),
                    risk_level=subtask_data.get("risk_level", 0.2),
                    can_parallelize=subtask_data.get("can_parallelize", False),
                    preferred_model_type=subtask_data.get("preferred_model_type", "local"),
                    priority_adjustment=0.0
                )
                
                subtasks.append(subtask)
                total_time += subtask.estimated_time_minutes
                
                # Estimate cost based on model type
                if subtask.preferred_model_type == "local":
                    total_cost += 0.0
                elif subtask.preferred_model_type == "claude-haiku":
                    total_cost += (subtask.estimated_tokens / 1000) * 0.0025
                elif subtask.preferred_model_type == "claude-sonnet":
                    total_cost += (subtask.estimated_tokens / 1000) * 0.003
                else:  # claude-opus
                    total_cost += (subtask.estimated_tokens / 1000) * 0.015
            
            # Create execution plan
            execution_plan = self._create_execution_plan(subtasks)
            
            return DecompositionResult(
                original_task_id=task.id,
                subtasks=subtasks,
                execution_plan=execution_plan,
                total_estimated_time=total_time,
                total_estimated_cost=total_cost,
                success_probability=max(0.5, 1.0 - (len(subtasks) * 0.05)),  # More subtasks = higher risk
                decomposition_strategy="llm_assisted"
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse LLM decomposition: {e}")
            return self._template_based_decomposition(task, analysis)
    
    def _template_based_decomposition(self, task: Task, analysis: TaskAnalysis) -> DecompositionResult:
        """Create decomposition using templates"""
        template = self.decomposition_templates.get(analysis.category)
        if not template:
            # Generic decomposition
            return self._create_generic_decomposition(task, analysis)
        
        subtasks = []
        subtask_id = 0
        total_time = 0
        total_cost = 0.0
        
        for phase, phase_subtasks in template["typical_subtasks"].items():
            for subtask_name in phase_subtasks[:2]:  # Limit to 2 per phase
                subtask_id += 1
                
                subtask = Subtask(
                    id=f"{task.id}_sub_{subtask_id}",
                    description=f"{subtask_name.replace('_', ' ').title()} for: {task.description}",
                    category=analysis.category,
                    complexity=TaskComplexity.SIMPLE,
                    estimated_tokens=max(500, task.estimated_tokens // analysis.estimated_steps),
                    estimated_time_minutes=20,
                    dependencies=[f"{task.id}_sub_{subtask_id-1}"] if subtask_id > 1 else [],
                    prerequisite_skills=analysis.skill_requirements,
                    success_criteria=[f"{subtask_name.replace('_', ' ').title()} completed successfully"],
                    risk_level=0.2,
                    can_parallelize=phase != template["phases"][0],  # First phase usually can't parallelize
                    preferred_model_type="local" if subtask_name in ["validate", "format", "check"] else "claude-haiku",
                    priority_adjustment=0.0
                )
                
                subtasks.append(subtask)
                total_time += subtask.estimated_time_minutes
                
                if subtask.preferred_model_type != "local":
                    total_cost += (subtask.estimated_tokens / 1000) * 0.0025
        
        execution_plan = self._create_execution_plan(subtasks)
        
        return DecompositionResult(
            original_task_id=task.id,
            subtasks=subtasks,
            execution_plan=execution_plan,
            total_estimated_time=total_time,
            total_estimated_cost=total_cost,
            success_probability=0.8,
            decomposition_strategy="template_based"
        )
    
    def _create_generic_decomposition(self, task: Task, analysis: TaskAnalysis) -> DecompositionResult:
        """Create generic decomposition for unknown task types"""
        num_subtasks = min(analysis.estimated_steps, 5)  # Cap at 5 subtasks
        
        subtasks = []
        for i in range(num_subtasks):
            subtask = Subtask(
                id=f"{task.id}_part_{i+1}",
                description=f"Part {i+1} of: {task.description}",
                category=analysis.category,
                complexity=TaskComplexity.SIMPLE,
                estimated_tokens=task.estimated_tokens // num_subtasks,
                estimated_time_minutes=30,
                dependencies=[f"{task.id}_part_{i}"] if i > 0 else [],
                prerequisite_skills=analysis.skill_requirements,
                success_criteria=[f"Part {i+1} completed successfully"],
                risk_level=0.3,
                can_parallelize=False,  # Generic tasks assumed sequential
                preferred_model_type="claude-haiku",
                priority_adjustment=0.0
            )
            subtasks.append(subtask)
        
        return DecompositionResult(
            original_task_id=task.id,
            subtasks=subtasks,
            execution_plan={"strategy": "sequential", "parallel_groups": []},
            total_estimated_time=num_subtasks * 30,
            total_estimated_cost=(task.estimated_tokens / 1000) * 0.0025,
            success_probability=0.7,
            decomposition_strategy="generic"
        )
    
    def _create_execution_plan(self, subtasks: List[Subtask]) -> Dict[str, Any]:
        """Create execution plan for subtasks"""
        # Group parallelizable tasks
        parallel_groups = []
        sequential_tasks = []
        
        for subtask in subtasks:
            if subtask.can_parallelize and not subtask.dependencies:
                # Find or create parallel group
                group_found = False
                for group in parallel_groups:
                    if not any(dep in [t.id for t in group] for dep in subtask.dependencies):
                        group.append(subtask)
                        group_found = True
                        break
                
                if not group_found:
                    parallel_groups.append([subtask])
            else:
                sequential_tasks.append(subtask)
        
        return {
            "strategy": "hybrid" if parallel_groups else "sequential",
            "parallel_groups": [[t.id for t in group] for group in parallel_groups],
            "sequential_tasks": [t.id for t in sequential_tasks],
            "execution_order": "parallel_first" if parallel_groups else "sequential"
        }
    
    async def validate_decomposition(self, result: DecompositionResult) -> Dict[str, Any]:
        """Validate a decomposition result"""
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "recommendations": [],
            "score": 0.0
        }
        
        # Check for circular dependencies
        task_ids = {st.id for st in result.subtasks}
        for subtask in result.subtasks:
            for dep in subtask.dependencies:
                if dep not in task_ids and dep != result.original_task_id:
                    validation_result["warnings"].append(f"Unknown dependency: {dep}")
                    validation_result["is_valid"] = False
        
        # Check token distribution
        total_tokens = sum(st.estimated_tokens for st in result.subtasks)
        if total_tokens > 50000:
            validation_result["warnings"].append("High token count may be expensive")
        
        # Check time estimates
        if result.total_estimated_time > 480:  # 8 hours
            validation_result["recommendations"].append("Consider further decomposition - task is very time-consuming")
        
        # Score the decomposition
        base_score = 0.8
        
        # Penalty for too many subtasks
        if len(result.subtasks) > 10:
            base_score -= 0.2
        
        # Bonus for parallel execution opportunities
        if result.execution_plan.get("parallel_groups"):
            base_score += 0.1
        
        # Bonus for cost optimization
        local_tasks = sum(1 for st in result.subtasks if st.preferred_model_type == "local")
        if local_tasks > len(result.subtasks) * 0.5:
            base_score += 0.1
        
        validation_result["score"] = max(0.0, min(1.0, base_score))
        
        return validation_result