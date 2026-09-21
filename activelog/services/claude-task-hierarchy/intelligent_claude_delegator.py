#!/usr/bin/env python3
"""
Intelligent Claude Delegator
Manages hierarchical task delegation between different Claude model tiers
"""

import asyncio
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ClaudeModel:
    """Represents a Claude model tier"""
    name: str
    model_id: str
    capabilities: List[str]
    cost_per_token: float
    max_context: int
    reasoning_strength: int  # 1-10
    speed: int  # 1-10, higher is faster
    best_for: List[str]

@dataclass
class TaskAnalysis:
    """Analysis of task complexity and requirements"""
    complexity_score: int  # 1-100
    reasoning_required: bool
    context_size_needed: int
    domain_expertise_required: List[str]
    estimated_tokens: int
    time_sensitivity: str  # 'low', 'medium', 'high'
    delegation_strategy: str  # 'local', 'haiku', 'sonnet', 'opus'
    reasoning: str

@dataclass
class DelegationPlan:
    """Plan for hierarchical task delegation"""
    primary_model: str
    task_breakdown: List[Dict]  # Each subtask with assigned model
    coordination_model: str  # Model that coordinates subtasks
    estimated_total_cost: float
    estimated_completion_time: int
    quality_expectation: float  # 1-10

class ClaudeModelManager:
    """Manages Claude model capabilities and selection"""
    
    def __init__(self):
        self.models = self._initialize_models()
        
    def _initialize_models(self) -> Dict[str, ClaudeModel]:
        """Initialize Claude model configurations"""
        return {
            "opus": ClaudeModel(
                name="Claude Opus 4.1",
                model_id="claude-opus-4-1-20250805",
                capabilities=["advanced_reasoning", "complex_analysis", "architecture_design", 
                            "strategic_planning", "creative_problem_solving"],
                cost_per_token=0.015,  # Higher cost
                max_context=200000,
                reasoning_strength=10,
                speed=6,
                best_for=["architecture", "strategy", "complex_logic", "creative_tasks"]
            ),
            "sonnet": ClaudeModel(
                name="Claude Sonnet 3.5",
                model_id="claude-3-5-sonnet-20241022", 
                capabilities=["good_reasoning", "code_analysis", "implementation", 
                            "debugging", "optimization"],
                cost_per_token=0.003,  # Medium cost
                max_context=100000,
                reasoning_strength=8,
                speed=8,
                best_for=["implementation", "analysis", "debugging", "optimization"]
            ),
            "haiku": ClaudeModel(
                name="Claude Haiku 3.5",
                model_id="claude-3-5-haiku-20241022",
                capabilities=["fast_processing", "simple_tasks", "formatting", 
                            "basic_analysis", "routine_operations"],
                cost_per_token=0.00025,  # Low cost
                max_context=50000,
                reasoning_strength=6,
                speed=10,
                best_for=["simple_tasks", "formatting", "basic_operations", "quick_responses"]
            )
        }
    
    def get_model(self, model_name: str) -> Optional[ClaudeModel]:
        """Get model by name"""
        return self.models.get(model_name.lower())
    
    def get_models_by_capability(self, capability: str) -> List[ClaudeModel]:
        """Get models that have a specific capability"""
        return [m for m in self.models.values() if capability in m.capabilities]
    
    def rank_models_for_task(self, task_analysis: TaskAnalysis) -> List[Tuple[str, float]]:
        """Rank models by suitability for a task"""
        scores = []
        
        for name, model in self.models.items():
            score = 0.0
            
            # Reasoning requirement
            if task_analysis.reasoning_required:
                score += model.reasoning_strength * 0.3
            else:
                score += (10 - model.reasoning_strength) * 0.1  # Prefer simpler for non-reasoning
            
            # Context size
            if task_analysis.context_size_needed > model.max_context:
                score -= 20  # Heavy penalty
            else:
                score += 5  # Bonus for sufficient context
            
            # Domain expertise
            domain_matches = len(set(task_analysis.domain_expertise_required) & set(model.best_for))
            score += domain_matches * 5
            
            # Time sensitivity (prefer faster models for urgent tasks)
            if task_analysis.time_sensitivity == "high":
                score += model.speed * 0.2
            elif task_analysis.time_sensitivity == "low":
                score += (10 - model.speed) * 0.1  # Don't care about speed
            
            # Cost efficiency (bonus for appropriate cost level)
            if task_analysis.complexity_score < 30:  # Simple task
                if name == "haiku":
                    score += 10  # Big bonus for using cheap model
                elif name == "opus":
                    score -= 15  # Penalty for expensive model on simple task
            elif task_analysis.complexity_score > 70:  # Complex task
                if name == "opus":
                    score += 8  # Bonus for using powerful model
                elif name == "haiku":
                    score -= 10  # Penalty for weak model on complex task
            
            scores.append((name, score))
        
        return sorted(scores, key=lambda x: x[1], reverse=True)

class TaskComplexityAnalyzer:
    """Analyzes tasks to determine complexity and requirements"""
    
    def __init__(self):
        self.complexity_patterns = self._initialize_complexity_patterns()
        self.domain_keywords = self._initialize_domain_keywords()
    
    def _initialize_complexity_patterns(self) -> Dict[str, int]:
        """Initialize patterns that indicate task complexity"""
        return {
            # High complexity (70-100)
            "architecture": 90,
            "design system": 85,
            "strategy": 80,
            "algorithm design": 85,
            "performance optimization": 75,
            "security analysis": 80,
            "complex business logic": 75,
            "integration design": 70,
            
            # Medium complexity (40-70)
            "implementation": 60,
            "debugging": 55,
            "analysis": 50,
            "refactoring": 45,
            "testing": 40,
            "documentation": 35,
            
            # Low complexity (10-40)
            "formatting": 15,
            "simple fix": 20,
            "basic validation": 25,
            "routine task": 20,
            "copy/paste": 10,
            "renaming": 15,
        }
    
    def _initialize_domain_keywords(self) -> Dict[str, List[str]]:
        """Initialize domain-specific keywords"""
        return {
            "architecture": ["system design", "microservices", "scalability", "patterns"],
            "strategy": ["planning", "roadmap", "approach", "methodology"],
            "implementation": ["code", "develop", "build", "create"],
            "analysis": ["examine", "investigate", "review", "assess"],
            "optimization": ["performance", "efficiency", "speed", "memory"],
            "debugging": ["fix", "error", "bug", "issue", "problem"],
            "testing": ["test", "validation", "verify", "check"],
            "simple_tasks": ["format", "rename", "copy", "basic"]
        }
    
    def analyze_task(self, task_description: str, context: Optional[str] = None) -> TaskAnalysis:
        """Analyze a task to determine complexity and requirements"""
        
        task_lower = task_description.lower()
        context_lower = (context or "").lower()
        full_text = f"{task_lower} {context_lower}"
        
        # Calculate complexity score
        complexity_score = 30  # Base score
        matched_patterns = []
        
        for pattern, score in self.complexity_patterns.items():
            if pattern in full_text:
                complexity_score = max(complexity_score, score)
                matched_patterns.append(pattern)
        
        # Determine reasoning requirement
        reasoning_keywords = [
            "why", "how", "analyze", "design", "strategy", "approach", 
            "decide", "recommend", "evaluate", "compare", "optimize"
        ]
        reasoning_required = any(keyword in full_text for keyword in reasoning_keywords)
        
        # Estimate context size needed
        context_size = len(context or "") + len(task_description)
        if "entire codebase" in full_text or "whole project" in full_text:
            context_size *= 10
        elif "file" in full_text or "function" in full_text:
            context_size = min(context_size, 10000)
        
        # Determine domain expertise needed
        domain_expertise = []
        for domain, keywords in self.domain_keywords.items():
            if any(keyword in full_text for keyword in keywords):
                domain_expertise.append(domain)
        
        # Estimate token usage
        estimated_tokens = len(full_text.split()) * 2  # Rough estimate
        if reasoning_required:
            estimated_tokens *= 1.5
        
        # Determine time sensitivity
        urgency_keywords = ["urgent", "asap", "immediately", "quick", "fast"]
        time_sensitivity = "high" if any(k in full_text for k in urgency_keywords) else "medium"
        
        # Determine delegation strategy
        if complexity_score >= 80:
            delegation_strategy = "opus"
        elif complexity_score >= 50:
            delegation_strategy = "sonnet"
        elif complexity_score >= 30:
            delegation_strategy = "haiku"
        else:
            delegation_strategy = "local"
        
        # Override for reasoning requirements
        if reasoning_required and complexity_score >= 60:
            delegation_strategy = "opus"
        elif reasoning_required:
            delegation_strategy = "sonnet"
        
        reasoning = f"Complexity: {complexity_score} (patterns: {', '.join(matched_patterns)})"
        if reasoning_required:
            reasoning += " | Reasoning required"
        if domain_expertise:
            reasoning += f" | Domain: {', '.join(domain_expertise)}"
        
        return TaskAnalysis(
            complexity_score=complexity_score,
            reasoning_required=reasoning_required,
            context_size_needed=context_size,
            domain_expertise_required=domain_expertise,
            estimated_tokens=estimated_tokens,
            time_sensitivity=time_sensitivity,
            delegation_strategy=delegation_strategy,
            reasoning=reasoning
        )

class IntelligentClaudeDelegator:
    """Main delegator for intelligent Claude task hierarchy"""
    
    def __init__(self):
        self.model_manager = ClaudeModelManager()
        self.task_analyzer = TaskComplexityAnalyzer()
        self.delegation_history: List[Dict] = []
        self.cost_tracker = {"total_cost": 0.0, "tokens_used": 0}
        
    def create_delegation_plan(self, task_description: str, context: Optional[str] = None,
                             max_cost: Optional[float] = None) -> DelegationPlan:
        """Create an intelligent delegation plan for a task"""
        
        # Analyze the main task
        main_analysis = self.task_analyzer.analyze_task(task_description, context)
        
        logger.info(f"📋 Task Analysis: {main_analysis.reasoning}")
        
        # Determine if task needs to be broken down
        if main_analysis.complexity_score >= 70:
            return self._create_hierarchical_plan(task_description, context, main_analysis, max_cost)
        else:
            return self._create_simple_plan(task_description, context, main_analysis, max_cost)
    
    def _create_hierarchical_plan(self, task: str, context: Optional[str], 
                                analysis: TaskAnalysis, max_cost: Optional[float]) -> DelegationPlan:
        """Create hierarchical plan for complex tasks"""
        
        # Use Opus for high-level breakdown and coordination
        coordination_model = "opus"
        
        # Simulate task breakdown (in real implementation, this would call Opus)
        subtasks = self._simulate_task_breakdown(task, analysis)
        
        # Assign appropriate models to each subtask
        task_breakdown = []
        total_cost = 0.0
        total_time = 0
        
        for subtask in subtasks:
            subtask_analysis = self.task_analyzer.analyze_task(subtask["description"])
            
            # Get best model for this subtask
            model_rankings = self.model_manager.rank_models_for_task(subtask_analysis)
            best_model = model_rankings[0][0]
            
            # Consider cost constraints
            if max_cost:
                model_obj = self.model_manager.get_model(best_model)
                estimated_cost = subtask_analysis.estimated_tokens * model_obj.cost_per_token
                
                if total_cost + estimated_cost > max_cost:
                    # Downgrade to cheaper model
                    for model_name, score in model_rankings:
                        model_obj = self.model_manager.get_model(model_name)
                        estimated_cost = subtask_analysis.estimated_tokens * model_obj.cost_per_token
                        if total_cost + estimated_cost <= max_cost:
                            best_model = model_name
                            break
            
            model_obj = self.model_manager.get_model(best_model)
            estimated_cost = subtask_analysis.estimated_tokens * model_obj.cost_per_token
            estimated_time = subtask_analysis.estimated_tokens / (model_obj.speed * 10)  # Rough estimate
            
            task_breakdown.append({
                "id": subtask["id"],
                "description": subtask["description"],
                "assigned_model": best_model,
                "complexity": subtask_analysis.complexity_score,
                "estimated_cost": estimated_cost,
                "estimated_time": estimated_time,
                "dependencies": subtask.get("dependencies", [])
            })
            
            total_cost += estimated_cost
            total_time += estimated_time
        
        # Add coordination overhead
        opus_model = self.model_manager.get_model("opus")
        coordination_cost = 500 * opus_model.cost_per_token  # Coordination tokens
        total_cost += coordination_cost
        
        return DelegationPlan(
            primary_model="opus",
            task_breakdown=task_breakdown,
            coordination_model="opus", 
            estimated_total_cost=total_cost,
            estimated_completion_time=int(total_time),
            quality_expectation=9.0  # High quality expected with hierarchical approach
        )
    
    def _create_simple_plan(self, task: str, context: Optional[str], 
                          analysis: TaskAnalysis, max_cost: Optional[float]) -> DelegationPlan:
        """Create simple plan for straightforward tasks"""
        
        # Get best single model for the task
        model_rankings = self.model_manager.rank_models_for_task(analysis)
        best_model = model_rankings[0][0]
        
        # Check cost constraints
        if max_cost:
            for model_name, score in model_rankings:
                model_obj = self.model_manager.get_model(model_name)
                estimated_cost = analysis.estimated_tokens * model_obj.cost_per_token
                if estimated_cost <= max_cost:
                    best_model = model_name
                    break
        
        model_obj = self.model_manager.get_model(best_model)
        estimated_cost = analysis.estimated_tokens * model_obj.cost_per_token
        estimated_time = analysis.estimated_tokens / (model_obj.speed * 10)
        
        return DelegationPlan(
            primary_model=best_model,
            task_breakdown=[{
                "id": "main_task",
                "description": task,
                "assigned_model": best_model,
                "complexity": analysis.complexity_score,
                "estimated_cost": estimated_cost,
                "estimated_time": estimated_time,
                "dependencies": []
            }],
            coordination_model=best_model,
            estimated_total_cost=estimated_cost,
            estimated_completion_time=int(estimated_time),
            quality_expectation=model_obj.reasoning_strength / 10 * 10
        )
    
    def _simulate_task_breakdown(self, task: str, analysis: TaskAnalysis) -> List[Dict]:
        """Simulate how Opus would break down a complex task"""
        
        # This simulates what Claude Opus would do - in real implementation,
        # this would be an actual API call to Opus
        
        if "api" in task.lower():
            return [
                {"id": "design", "description": "Design API architecture and endpoints"},
                {"id": "implement", "description": "Implement core API functionality", "dependencies": ["design"]},
                {"id": "validation", "description": "Add input validation and error handling", "dependencies": ["implement"]},
                {"id": "testing", "description": "Create comprehensive tests", "dependencies": ["validation"]},
                {"id": "documentation", "description": "Write API documentation", "dependencies": ["implement"]}
            ]
        elif "ui" in task.lower() or "interface" in task.lower():
            return [
                {"id": "design", "description": "Design component structure and user flow"},
                {"id": "layout", "description": "Create HTML/JSX layout", "dependencies": ["design"]},
                {"id": "styling", "description": "Implement CSS styling and responsive design", "dependencies": ["layout"]},
                {"id": "interaction", "description": "Add user interactions and state management", "dependencies": ["styling"]},
                {"id": "integration", "description": "Integrate with backend APIs", "dependencies": ["interaction"]},
                {"id": "testing", "description": "Add component tests and accessibility", "dependencies": ["integration"]}
            ]
        elif "system" in task.lower() and "design" in task.lower():
            return [
                {"id": "requirements", "description": "Analyze requirements and constraints"},
                {"id": "architecture", "description": "Design system architecture", "dependencies": ["requirements"]},
                {"id": "components", "description": "Design individual components", "dependencies": ["architecture"]},
                {"id": "interfaces", "description": "Define interfaces and protocols", "dependencies": ["components"]},
                {"id": "scalability", "description": "Plan scalability and performance", "dependencies": ["interfaces"]},
                {"id": "documentation", "description": "Create architecture documentation", "dependencies": ["scalability"]}
            ]
        else:
            # Generic breakdown
            return [
                {"id": "analysis", "description": f"Analyze requirements for: {task}"},
                {"id": "planning", "description": f"Plan implementation approach", "dependencies": ["analysis"]},
                {"id": "implementation", "description": f"Implement solution", "dependencies": ["planning"]},
                {"id": "testing", "description": f"Test and validate solution", "dependencies": ["implementation"]}
            ]
    
    async def execute_delegation_plan(self, plan: DelegationPlan) -> Dict:
        """Execute a delegation plan (simulation)"""
        
        logger.info(f"🚀 Executing delegation plan with {len(plan.task_breakdown)} subtasks")
        logger.info(f"💰 Estimated cost: ${plan.estimated_total_cost:.4f}")
        
        results = {
            "plan_id": f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "execution_start": datetime.now(),
            "primary_model": plan.primary_model,
            "coordination_model": plan.coordination_model,
            "subtask_results": {},
            "total_tokens_used": 0,
            "actual_cost": 0.0,
            "quality_scores": []
        }
        
        # Execute subtasks in dependency order
        completed_tasks = set()
        
        for subtask in plan.task_breakdown:
            # Check dependencies
            while not all(dep in completed_tasks for dep in subtask.get("dependencies", [])):
                await asyncio.sleep(0.1)  # Wait for dependencies
            
            # Simulate task execution
            logger.info(f"🔧 Executing: {subtask['description'][:60]}... ({subtask['assigned_model']})")
            
            # Simulate execution time
            await asyncio.sleep(min(subtask["estimated_time"], 2))  # Cap simulation time
            
            # Simulate results
            model = self.model_manager.get_model(subtask["assigned_model"])
            quality_score = min(model.reasoning_strength + (10 - subtask["complexity"] / 10), 10)
            
            actual_tokens = int(subtask["estimated_cost"] / model.cost_per_token)
            actual_cost = actual_tokens * model.cost_per_token
            
            results["subtask_results"][subtask["id"]] = {
                "model_used": subtask["assigned_model"],
                "tokens_used": actual_tokens,
                "cost": actual_cost,
                "quality_score": quality_score,
                "execution_time": subtask["estimated_time"],
                "status": "completed"
            }
            
            results["total_tokens_used"] += actual_tokens
            results["actual_cost"] += actual_cost
            results["quality_scores"].append(quality_score)
            
            completed_tasks.add(subtask["id"])
            
            logger.info(f"✅ Completed: {subtask['id']} (Quality: {quality_score:.1f}/10)")
        
        # Final results
        results["execution_end"] = datetime.now()
        results["overall_quality"] = sum(results["quality_scores"]) / len(results["quality_scores"])
        results["cost_efficiency"] = plan.estimated_total_cost / results["actual_cost"] if results["actual_cost"] > 0 else 1.0
        
        # Update cost tracking
        self.cost_tracker["total_cost"] += results["actual_cost"]
        self.cost_tracker["tokens_used"] += results["total_tokens_used"]
        
        # Log results
        self.delegation_history.append({
            "timestamp": datetime.now(),
            "plan": asdict(plan),
            "results": results
        })
        
        logger.info(f"🎯 Plan execution complete - Quality: {results['overall_quality']:.1f}/10, Cost: ${results['actual_cost']:.4f}")
        
        return results
    
    def get_model_recommendations(self, task_description: str, context: Optional[str] = None) -> Dict:
        """Get model recommendations for a task"""
        
        analysis = self.task_analyzer.analyze_task(task_description, context)
        model_rankings = self.model_manager.rank_models_for_task(analysis)
        
        recommendations = []
        for model_name, score in model_rankings:
            model = self.model_manager.get_model(model_name)
            estimated_cost = analysis.estimated_tokens * model.cost_per_token
            
            recommendations.append({
                "model": model_name,
                "suitability_score": score,
                "estimated_cost": estimated_cost,
                "reasoning_strength": model.reasoning_strength,
                "speed": model.speed,
                "recommended_for": model.best_for
            })
        
        return {
            "task_analysis": asdict(analysis),
            "recommendations": recommendations,
            "top_choice": recommendations[0] if recommendations else None
        }
    
    def get_cost_analysis(self) -> Dict:
        """Get cost analysis and efficiency metrics"""
        
        if not self.delegation_history:
            return {"message": "No delegation history available"}
        
        # Analyze cost patterns
        total_plans = len(self.delegation_history)
        avg_cost = self.cost_tracker["total_cost"] / total_plans
        
        model_usage = {}
        quality_by_model = {}
        
        for session in self.delegation_history:
            plan = session["plan"]
            results = session["results"]
            
            for subtask in plan["task_breakdown"]:
                model = subtask["assigned_model"]
                model_usage[model] = model_usage.get(model, 0) + 1
                
                if model not in quality_by_model:
                    quality_by_model[model] = []
                
                if subtask["id"] in results["subtask_results"]:
                    quality_by_model[model].append(results["subtask_results"][subtask["id"]]["quality_score"])
        
        # Calculate averages
        for model in quality_by_model:
            if quality_by_model[model]:
                quality_by_model[model] = sum(quality_by_model[model]) / len(quality_by_model[model])
        
        return {
            "total_cost": self.cost_tracker["total_cost"],
            "total_tokens": self.cost_tracker["tokens_used"],
            "total_plans": total_plans,
            "average_cost_per_plan": avg_cost,
            "model_usage_distribution": model_usage,
            "quality_by_model": quality_by_model,
            "cost_efficiency_trends": "improving"  # Placeholder
        }

# Test the intelligent delegator
async def main():
    """Test the intelligent Claude delegator"""
    
    delegator = IntelligentClaudeDelegator()
    
    print("🧠 Intelligent Claude Delegator Test")
    print("=====================================")
    
    # Test different types of tasks
    test_tasks = [
        "Add error handling to this function",  # Simple task
        "Create a comprehensive user authentication system with JWT tokens, password hashing, and role-based access control",  # Complex task
        "Design a microservices architecture for a fitness tracking platform that can scale to millions of users",  # Very complex
        "Fix the CSS formatting on the login button",  # Very simple
    ]
    
    for i, task in enumerate(test_tasks, 1):
        print(f"\n🎯 Task {i}: {task}")
        
        # Get recommendations
        recommendations = delegator.get_model_recommendations(task)
        print(f"📊 Analysis: {recommendations['task_analysis']['reasoning']}")
        print(f"🏆 Recommended: {recommendations['top_choice']['model']} (${recommendations['top_choice']['estimated_cost']:.4f})")
        
        # Create and execute delegation plan
        plan = delegator.create_delegation_plan(task, max_cost=0.50)
        print(f"📋 Plan: {len(plan.task_breakdown)} subtasks, Est. cost: ${plan.estimated_total_cost:.4f}")
        
        results = await delegator.execute_delegation_plan(plan)
        print(f"✅ Completed: Quality {results['overall_quality']:.1f}/10, Actual cost: ${results['actual_cost']:.4f}")
        print("-" * 60)
    
    # Final cost analysis
    cost_analysis = delegator.get_cost_analysis()
    print(f"\n💰 Cost Analysis:")
    print(json.dumps(cost_analysis, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())