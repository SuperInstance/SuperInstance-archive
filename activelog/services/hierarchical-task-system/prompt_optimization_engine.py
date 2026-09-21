#!/usr/bin/env python3
"""
Prompt Optimization Engine for Local AI Assistants
ML-powered system to optimize Claude prompts for delegating to local coding bots
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np
from pathlib import Path
import pickle
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class PromptTemplate:
    """Template for prompts sent to local assistants"""
    name: str
    template: str
    variables: List[str]  # Variables to substitute
    success_rate: float
    avg_quality: float
    usage_count: int
    best_for_tasks: List[str]  # Task types this works best for

@dataclass
class PromptOptimizationResult:
    """Result of prompt optimization"""
    original_prompt: str
    optimized_prompt: str
    confidence: float
    improvements: List[str]
    assistant_compatibility: Dict[str, float]  # How well it works with each assistant

@dataclass
class PromptPerformanceMetric:
    """Performance metrics for a specific prompt"""
    prompt_id: str
    assistant_used: str
    task_type: str
    success: bool
    quality_score: float
    execution_time: float
    user_feedback: Optional[float]  # 1-10 rating
    timestamp: datetime

class PromptTemplateLibrary:
    """Library of proven prompt templates for different scenarios"""
    
    def __init__(self):
        self.templates = self._initialize_templates()
        self.performance_data: List[PromptPerformanceMetric] = []
        
    def _initialize_templates(self) -> List[PromptTemplate]:
        """Initialize with proven prompt templates"""
        return [
            PromptTemplate(
                name="simple_refactoring",
                template="Refactor the following {language} code to {improvement_type}. Keep the functionality identical and maintain the existing code style:\n\n{code}\n\nTask: {specific_task}",
                variables=["language", "improvement_type", "code", "specific_task"],
                success_rate=0.85,
                avg_quality=7.8,
                usage_count=0,
                best_for_tasks=["refactoring", "cleanup", "style_improvement"]
            ),
            PromptTemplate(
                name="add_documentation",
                template="Add comprehensive {doc_type} to this {language} code. Follow standard conventions for {language}:\n\n{code}\n\nFocus on: {documentation_focus}",
                variables=["doc_type", "language", "code", "documentation_focus"],
                success_rate=0.92,
                avg_quality=8.2,
                usage_count=0,
                best_for_tasks=["documentation", "comments", "docstrings"]
            ),
            PromptTemplate(
                name="error_handling",
                template="Add robust error handling to this {language} code. Include appropriate exception types and meaningful error messages:\n\n{code}\n\nError scenarios to handle: {error_scenarios}",
                variables=["language", "code", "error_scenarios"],
                success_rate=0.78,
                avg_quality=7.5,
                usage_count=0,
                best_for_tasks=["error_handling", "validation", "robustness"]
            ),
            PromptTemplate(
                name="code_completion",
                template="Complete this {language} code snippet. The code should {completion_goal}:\n\n{partial_code}\n\nContext: {context_info}",
                variables=["language", "completion_goal", "partial_code", "context_info"],
                success_rate=0.88,
                avg_quality=8.0,
                usage_count=0,
                best_for_tasks=["completion", "generation", "implementation"]
            ),
            PromptTemplate(
                name="variable_renaming",
                template="Rename variables in this {language} code to be more descriptive and follow {naming_convention} conventions:\n\n{code}\n\nRename these specifically: {variables_to_rename}",
                variables=["language", "naming_convention", "code", "variables_to_rename"],
                success_rate=0.91,
                avg_quality=8.3,
                usage_count=0,
                best_for_tasks=["renaming", "readability", "conventions"]
            ),
            PromptTemplate(
                name="test_generation",
                template="Generate {test_type} tests for this {language} code using {test_framework}:\n\n{code}\n\nTest these scenarios: {test_scenarios}",
                variables=["test_type", "language", "test_framework", "code", "test_scenarios"],
                success_rate=0.73,
                avg_quality=7.2,
                usage_count=0,
                best_for_tasks=["testing", "unit_tests", "validation"]
            ),
            PromptTemplate(
                name="performance_optimization",
                template="Optimize this {language} code for {optimization_target}. Maintain functionality while improving {performance_metric}:\n\n{code}\n\nOptimization constraints: {constraints}",
                variables=["language", "optimization_target", "performance_metric", "code", "constraints"],
                success_rate=0.65,
                avg_quality=6.8,
                usage_count=0,
                best_for_tasks=["optimization", "performance", "efficiency"]
            )
        ]
    
    def get_best_template(self, task_type: str, assistant_name: str = "") -> Optional[PromptTemplate]:
        """Get best template for task type and assistant"""
        
        # Filter by task type
        matching_templates = [t for t in self.templates if task_type.lower() in [bt.lower() for bt in t.best_for_tasks]]
        
        if not matching_templates:
            # Try fuzzy matching
            matching_templates = [t for t in self.templates 
                                if any(task_word in task_type.lower() for task_word in [bt.lower() for bt in t.best_for_tasks])]
        
        if not matching_templates:
            return None
            
        # Score templates by performance
        scored_templates = []
        for template in matching_templates:
            score = (template.success_rate * 0.6 + (template.avg_quality / 10) * 0.4)
            
            # Boost score for frequently used templates (proven patterns)
            if template.usage_count > 5:
                score += 0.1
                
            scored_templates.append((score, template))
        
        # Return highest scoring template
        return max(scored_templates, key=lambda x: x[0])[1]
    
    def update_template_performance(self, template_name: str, performance: PromptPerformanceMetric):
        """Update template performance based on actual results"""
        template = next((t for t in self.templates if t.name == template_name), None)
        if not template:
            return
            
        # Store performance data
        self.performance_data.append(performance)
        
        # Update template metrics
        template.usage_count += 1
        
        # Recalculate success rate and quality (exponential moving average)
        alpha = 0.1  # Learning rate
        if performance.success:
            template.success_rate = (1 - alpha) * template.success_rate + alpha * 1.0
        else:
            template.success_rate = (1 - alpha) * template.success_rate + alpha * 0.0
            
        template.avg_quality = (1 - alpha) * template.avg_quality + alpha * performance.quality_score

class PromptOptimizationEngine:
    """ML-powered prompt optimization for local assistants"""
    
    def __init__(self):
        self.template_library = PromptTemplateLibrary()
        self.optimization_patterns = self._load_optimization_patterns()
        self.assistant_preferences = self._load_assistant_preferences()
        
    def _load_optimization_patterns(self) -> Dict[str, List[str]]:
        """Load patterns that improve prompt effectiveness"""
        return {
            "aiXcoder": [
                "Be specific about the programming language",
                "Provide clear context about the expected output",
                "Use structured format with clear sections",
                "Include examples when possible"
            ],
            "tabnine": [
                "Keep prompts concise and focused",
                "Use natural language descriptions",
                "Provide context about the surrounding code",
                "Specify desired completion length"
            ],
            "continue": [
                "Use conversational tone",
                "Break complex tasks into steps",
                "Provide file context when relevant",
                "Ask for specific improvements"
            ],
            "fauxpilot": [
                "Use clear, imperative instructions",
                "Provide type hints and structure",
                "Include error handling requirements",
                "Specify coding standards to follow"
            ]
        }
    
    def _load_assistant_preferences(self) -> Dict[str, Dict[str, float]]:
        """Load learned preferences for each assistant"""
        return {
            "aiXcoder": {
                "prompt_length": 0.7,  # Prefers moderate length
                "technical_detail": 0.8,  # Likes technical specifics
                "examples": 0.9,  # Benefits from examples
                "context": 0.6  # Moderate context needs
            },
            "tabnine": {
                "prompt_length": 0.3,  # Prefers short prompts
                "technical_detail": 0.4,  # Simple instructions
                "examples": 0.5,  # Some examples help
                "context": 0.8  # Needs context
            },
            "continue": {
                "prompt_length": 0.8,  # Can handle longer prompts
                "technical_detail": 0.7,  # Good with details
                "examples": 0.7,  # Examples are helpful
                "context": 0.9  # Highly context-dependent
            },
            "fauxpilot": {
                "prompt_length": 0.6,  # Moderate length
                "technical_detail": 0.9,  # Very technical
                "examples": 0.8,  # Good with examples
                "context": 0.7  # Moderate context needs
            }
        }
    
    def optimize_prompt(self, original_task: str, target_assistant: str, 
                       file_context: Optional[str] = None,
                       language: str = "python") -> PromptOptimizationResult:
        """Optimize prompt for specific assistant"""
        
        # Detect task type
        task_type = self._classify_task_type(original_task)
        
        # Get best template
        template = self.template_library.get_best_template(task_type, target_assistant)
        
        if template:
            # Use template-based optimization
            optimized = self._apply_template_optimization(original_task, template, target_assistant, 
                                                        file_context, language)
        else:
            # Use pattern-based optimization
            optimized = self._apply_pattern_optimization(original_task, target_assistant, 
                                                       file_context, language)
        
        return optimized
    
    def _classify_task_type(self, task: str) -> str:
        """Classify the type of coding task"""
        task_lower = task.lower()
        
        task_patterns = {
            "refactoring": ["refactor", "improve", "clean up", "restructure", "reorganize"],
            "documentation": ["add comment", "document", "docstring", "explain", "describe"],
            "error_handling": ["error", "exception", "handle", "try", "catch", "validate"],
            "completion": ["complete", "finish", "implement", "add", "create"],
            "renaming": ["rename", "change name", "update name", "variable name"],
            "testing": ["test", "unit test", "testing", "verify", "check"],
            "optimization": ["optimize", "performance", "speed up", "improve efficiency"],
            "formatting": ["format", "indent", "style", "spacing", "align"]
        }
        
        for task_type, patterns in task_patterns.items():
            if any(pattern in task_lower for pattern in patterns):
                return task_type
        
        return "general"
    
    def _apply_template_optimization(self, task: str, template: PromptTemplate, 
                                   assistant: str, context: Optional[str], 
                                   language: str) -> PromptOptimizationResult:
        """Apply template-based optimization"""
        
        # Extract variables from task and context
        variables = self._extract_template_variables(task, template, context, language)
        
        # Fill template
        optimized_prompt = template.template
        for var, value in variables.items():
            optimized_prompt = optimized_prompt.replace(f"{{{var}}}", str(value))
        
        # Apply assistant-specific tweaks
        optimized_prompt = self._apply_assistant_tweaks(optimized_prompt, assistant)
        
        improvements = [
            f"Used proven template: {template.name}",
            f"Template success rate: {template.success_rate:.1%}",
            f"Customized for {assistant}",
        ]
        
        # Calculate compatibility scores
        compatibility = {}
        for asst_name in self.assistant_preferences:
            if asst_name == assistant:
                compatibility[asst_name] = 0.9  # High compatibility for target
            else:
                # Estimate compatibility based on template performance
                compatibility[asst_name] = template.success_rate * 0.7
        
        return PromptOptimizationResult(
            original_prompt=task,
            optimized_prompt=optimized_prompt,
            confidence=template.success_rate,
            improvements=improvements,
            assistant_compatibility=compatibility
        )
    
    def _apply_pattern_optimization(self, task: str, assistant: str,
                                  context: Optional[str], language: str) -> PromptOptimizationResult:
        """Apply pattern-based optimization when no template matches"""
        
        optimized_prompt = task
        improvements = []
        
        # Get assistant-specific patterns
        patterns = self.optimization_patterns.get(assistant, [])
        preferences = self.assistant_preferences.get(assistant, {})
        
        # Apply language specification
        if language and language.lower() not in optimized_prompt.lower():
            optimized_prompt = f"For {language} code: {optimized_prompt}"
            improvements.append("Added language specification")
        
        # Add context if beneficial
        if context and preferences.get("context", 0) > 0.6:
            optimized_prompt += f"\n\nCode context:\n{context[:500]}..."
            improvements.append("Added relevant context")
        
        # Apply assistant-specific improvements
        if "Be specific about" in patterns:
            # Make prompt more specific
            optimized_prompt = self._make_more_specific(optimized_prompt, language)
            improvements.append("Made prompt more specific")
        
        if "Use structured format" in patterns:
            # Structure the prompt
            optimized_prompt = self._structure_prompt(optimized_prompt)
            improvements.append("Added structured format")
        
        if preferences.get("prompt_length", 0.5) < 0.4:
            # Make more concise
            optimized_prompt = self._make_concise(optimized_prompt)
            improvements.append("Made prompt more concise")
        
        # Calculate compatibility
        compatibility = {assistant: 0.7}  # Moderate confidence without template
        
        return PromptOptimizationResult(
            original_prompt=task,
            optimized_prompt=optimized_prompt,
            confidence=0.7,
            improvements=improvements,
            assistant_compatibility=compatibility
        )
    
    def _extract_template_variables(self, task: str, template: PromptTemplate,
                                  context: Optional[str], language: str) -> Dict[str, str]:
        """Extract variables needed for template"""
        variables = {}
        
        # Common variable mappings
        if "language" in template.variables:
            variables["language"] = language
        
        if "code" in template.variables:
            variables["code"] = context or "# Code will be provided"
        
        if "specific_task" in template.variables:
            variables["specific_task"] = task
        
        # Task-specific variables
        if "improvement_type" in template.variables:
            if "readable" in task.lower():
                variables["improvement_type"] = "improve readability"
            elif "performance" in task.lower():
                variables["improvement_type"] = "optimize performance"
            else:
                variables["improvement_type"] = "improve code quality"
        
        if "doc_type" in template.variables:
            if "docstring" in task.lower():
                variables["doc_type"] = "docstrings"
            elif "comment" in task.lower():
                variables["doc_type"] = "comments"
            else:
                variables["doc_type"] = "documentation"
        
        # Fill any missing variables with defaults
        for var in template.variables:
            if var not in variables:
                variables[var] = f"[{var}]"
        
        return variables
    
    def _apply_assistant_tweaks(self, prompt: str, assistant: str) -> str:
        """Apply assistant-specific tweaks"""
        patterns = self.optimization_patterns.get(assistant, [])
        
        if assistant == "aiXcoder":
            # Add structure for aiXcoder
            if not prompt.startswith("Task:"):
                prompt = f"Task: {prompt}"
        
        elif assistant == "tabnine":
            # Keep concise for TabNine
            sentences = prompt.split('.')
            if len(sentences) > 3:
                prompt = '. '.join(sentences[:3]) + '.'
        
        elif assistant == "continue":
            # Add conversational tone
            if not prompt.startswith(("Please", "Can you", "Would you")):
                prompt = f"Please {prompt.lower()}"
        
        elif assistant == "fauxpilot":
            # Add technical specificity
            if "function" in prompt and "def " not in prompt:
                prompt += "\nUse proper function definitions with type hints."
        
        return prompt
    
    def _make_more_specific(self, prompt: str, language: str) -> str:
        """Make prompt more specific"""
        if language == "python":
            prompt += f"\nFollow PEP 8 style guidelines."
        elif language == "javascript":
            prompt += f"\nUse modern ES6+ syntax."
        return prompt
    
    def _structure_prompt(self, prompt: str) -> str:
        """Add structure to prompt"""
        if "\n" not in prompt:
            return f"Objective: {prompt}\n\nRequirements:\n- Maintain existing functionality\n- Follow best practices"
        return prompt
    
    def _make_concise(self, prompt: str) -> str:
        """Make prompt more concise"""
        # Remove redundant words
        concise = re.sub(r'\b(please|kindly|would you|could you)\b', '', prompt, flags=re.IGNORECASE)
        concise = re.sub(r'\s+', ' ', concise).strip()
        return concise
    
    def learn_from_result(self, prompt_result: PromptPerformanceMetric):
        """Learn from prompt execution results"""
        
        # Find which template was likely used
        template_used = None
        for template in self.template_library.templates:
            if any(keyword in prompt_result.task_type for keyword in template.best_for_tasks):
                template_used = template.name
                break
        
        if template_used:
            self.template_library.update_template_performance(template_used, prompt_result)
        
        # Update assistant preferences based on result
        assistant = prompt_result.assistant_used
        if assistant in self.assistant_preferences:
            # Adjust preferences based on success
            if prompt_result.success and prompt_result.quality_score > 7.0:
                # This approach worked well, reinforce preferences
                pass
            elif not prompt_result.success or prompt_result.quality_score < 5.0:
                # This approach didn't work, adjust preferences
                prefs = self.assistant_preferences[assistant]
                # Reduce confidence in current settings
                for key in prefs:
                    prefs[key] = prefs[key] * 0.95
    
    def get_optimization_insights(self) -> Dict:
        """Get insights from optimization history"""
        performance_data = self.template_library.performance_data
        
        if not performance_data:
            return {"message": "No optimization data available"}
        
        # Assistant performance by task type
        assistant_performance = {}
        task_success_rates = {}
        
        for metric in performance_data:
            assistant = metric.assistant_used
            task_type = metric.task_type
            
            if assistant not in assistant_performance:
                assistant_performance[assistant] = {"total": 0, "successful": 0, "avg_quality": 0}
            
            if task_type not in task_success_rates:
                task_success_rates[task_type] = {"total": 0, "successful": 0}
            
            assistant_performance[assistant]["total"] += 1
            task_success_rates[task_type]["total"] += 1
            
            if metric.success:
                assistant_performance[assistant]["successful"] += 1
                task_success_rates[task_type]["successful"] += 1
                assistant_performance[assistant]["avg_quality"] += metric.quality_score
        
        # Calculate rates
        for assistant in assistant_performance:
            stats = assistant_performance[assistant]
            if stats["successful"] > 0:
                stats["success_rate"] = stats["successful"] / stats["total"]
                stats["avg_quality"] /= stats["successful"]
            else:
                stats["success_rate"] = 0
        
        for task_type in task_success_rates:
            stats = task_success_rates[task_type]
            stats["success_rate"] = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        
        return {
            "total_optimizations": len(performance_data),
            "assistant_performance": assistant_performance,
            "task_success_rates": task_success_rates,
            "template_performance": {t.name: {"success_rate": t.success_rate, "usage_count": t.usage_count} 
                                   for t in self.template_library.templates}
        }

# Test the system
async def main():
    """Test prompt optimization engine"""
    engine = PromptOptimizationEngine()
    
    test_tasks = [
        ("Add error handling to the database connection function", "aiXcoder"),
        ("Rename variable names to be more descriptive", "tabnine"),
        ("Add documentation to all the functions", "continue"),
        ("Complete this API endpoint implementation", "fauxpilot")
    ]
    
    print("🔧 Prompt Optimization Engine")
    print("==============================")
    
    for task, assistant in test_tasks:
        print(f"\nOriginal task: {task}")
        print(f"Target assistant: {assistant}")
        
        result = engine.optimize_prompt(task, assistant, "def connect_db():\n    # Connect to database", "python")
        
        print(f"\n📝 Optimized prompt:")
        print(f"{result.optimized_prompt}")
        print(f"\n🎯 Confidence: {result.confidence:.1%}")
        print(f"✨ Improvements:")
        for improvement in result.improvements:
            print(f"   • {improvement}")
        
        # Simulate result and learn from it
        performance = PromptPerformanceMetric(
            prompt_id=f"test_{len(engine.template_library.performance_data)}",
            assistant_used=assistant,
            task_type=engine._classify_task_type(task),
            success=True,
            quality_score=8.2,
            execution_time=2.5,
            user_feedback=8.0,
            timestamp=datetime.now()
        )
        
        engine.learn_from_result(performance)
        print("-" * 60)
    
    # Show insights
    insights = engine.get_optimization_insights()
    print(f"\n📊 Optimization Insights:")
    print(json.dumps(insights, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())