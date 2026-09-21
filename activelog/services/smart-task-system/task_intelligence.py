#!/usr/bin/env python3
"""
Smart Task Classification System for SuperInstance
Automatically selects optimal Claude model based on task complexity
Maximizes token efficiency and cost optimization
"""

import re
import json
import logging
import asyncio
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import tiktoken
from datetime import datetime

logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    TRIVIAL = "trivial"           # Simple operations, file reads
    SIMPLE = "simple"             # Basic coding, formatting, simple fixes  
    MODERATE = "moderate"         # Standard development tasks, debugging
    COMPLEX = "complex"           # Architecture, complex algorithms, integration
    EXPERT = "expert"             # Advanced reasoning, novel solutions, research

class ModelTier(Enum):
    HAIKU = "haiku"              # Fast, cheap - simple tasks
    SONNET = "sonnet"            # Balanced - most development work
    OPUS = "opus"                # Premium - complex reasoning
    
@dataclass
class ModelConfig:
    model_name: str
    cost_per_1k_input: float
    cost_per_1k_output: float
    max_tokens: int
    speed_factor: float          # Relative speed (higher = faster)
    capability_score: float      # Reasoning capability (1-10)
    best_for: List[str]         # Task types this model excels at

# Model configurations based on Claude pricing and capabilities
MODEL_CONFIGS = {
    ModelTier.HAIKU: ModelConfig(
        model_name="claude-3-haiku-20240307",
        cost_per_1k_input=0.00025,
        cost_per_1k_output=0.00125, 
        max_tokens=200000,
        speed_factor=10.0,
        capability_score=6.0,
        best_for=["formatting", "simple_edits", "file_operations", "basic_debugging", "documentation"]
    ),
    
    ModelTier.SONNET: ModelConfig(
        model_name="claude-3-5-sonnet-20241022", 
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
        max_tokens=200000,
        speed_factor=5.0,
        capability_score=8.5,
        best_for=["development", "refactoring", "api_design", "testing", "optimization", "integration"]
    ),
    
    ModelTier.OPUS: ModelConfig(
        model_name="claude-3-opus-20240229",
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
        max_tokens=200000, 
        speed_factor=1.0,
        capability_score=10.0,
        best_for=["architecture", "complex_algorithms", "research", "novel_solutions", "system_design"]
    )
}

@dataclass
class TaskAnalysis:
    complexity: TaskComplexity
    recommended_model: ModelTier
    confidence: float           # 0-1 confidence in recommendation
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost: float
    reasoning: str             # Why this model was chosen
    task_categories: List[str] # Identified task categories
    requires_reasoning: bool   # Needs advanced reasoning
    requires_creativity: bool  # Needs creative problem solving
    is_time_sensitive: bool    # Needs fast completion

class TaskIntelligenceClassifier:
    """Intelligent task classification and model selection"""
    
    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Task complexity patterns (regex patterns and weights)
        self.complexity_patterns = {
            TaskComplexity.TRIVIAL: [
                (r"read\s+file|list\s+files|check\s+status", 2.0),
                (r"format\s+code|indent|whitespace", 2.0),
                (r"copy|move|rename|delete\s+file", 2.0),
                (r"simple\s+fix|typo|spelling", 1.5),
                (r"add\s+comment|comment\s+code", 1.5),
            ],
            
            TaskComplexity.SIMPLE: [
                (r"basic\s+debugging|simple\s+bug|syntax\s+error", 2.0),
                (r"update\s+configuration|config\s+change", 1.8),
                (r"add\s+logging|log\s+statement", 1.5),
                (r"simple\s+validation|input\s+check", 1.5),
                (r"basic\s+test|unit\s+test", 1.5),
                (r"documentation|readme|comment", 1.3),
            ],
            
            TaskComplexity.MODERATE: [
                (r"implement\s+function|create\s+method", 2.0),
                (r"refactor|restructure|reorganize", 1.8),
                (r"api\s+endpoint|rest\s+api|api\s+design", 1.8),
                (r"database\s+query|sql|orm", 1.5),
                (r"integration\s+test|e2e\s+test", 1.5),
                (r"performance\s+optimization|optimize", 1.5),
                (r"error\s+handling|exception", 1.3),
            ],
            
            TaskComplexity.COMPLEX: [
                (r"algorithm|data\s+structure|complex\s+logic", 2.5),
                (r"system\s+integration|microservice", 2.0),
                (r"security\s+implementation|authentication|authorization", 2.0),
                (r"caching\s+strategy|distributed\s+system", 1.8),
                (r"concurrent|parallel|threading|async", 1.8),
                (r"machine\s+learning|ai\s+integration", 1.5),
                (r"complex\s+debugging|production\s+issue", 1.5),
            ],
            
            TaskComplexity.EXPERT: [
                (r"architecture\s+design|system\s+architecture", 3.0),
                (r"research|investigation|analysis|discovery", 2.5),
                (r"novel\s+solution|innovative|creative", 2.5),
                (r"scalability|high\s+availability|fault\s+tolerance", 2.0),
                (r"advanced\s+algorithm|optimization\s+problem", 2.0),
                (r"cross\s+domain|multi\s+system|enterprise", 1.8),
                (r"performance\s+critical|low\s+latency", 1.5),
            ]
        }
        
        # Task category patterns for specialization matching
        self.category_patterns = {
            "infrastructure": [
                r"kubernetes|k8s|docker|container",
                r"deployment|devops|ci/cd|pipeline",
                r"monitoring|grafana|prometheus|alerting",
                r"load\s+balancer|nginx|ingress",
                r"ssl|tls|certificate|security"
            ],
            "services": [
                r"api|endpoint|rest|graphql",
                r"database|sql|postgres|mysql|redis",
                r"authentication|auth|jwt|oauth", 
                r"microservice|service|backend",
                r"caching|performance|optimization"
            ],
            "domains": [
                r"ui|frontend|react|vue|angular",
                r"user\s+experience|ux|interface",
                r"business\s+logic|workflow|process",
                r"analytics|dashboard|reporting",
                r"fitness|health|tracking|activelog"
            ],
            "ai_integration": [
                r"machine\s+learning|ml|ai",
                r"claude|openai|llm|gpt",
                r"embeddings|vector|semantic",
                r"natural\s+language|nlp|text\s+processing",
                r"recommendation|intelligence|smart"
            ]
        }
        
        # Priority keywords that influence model selection
        self.priority_keywords = {
            "urgent": 1.5,
            "critical": 2.0,
            "production": 1.3,
            "bug": 1.2,
            "security": 1.8,
            "performance": 1.4,
            "scalability": 1.6,
            "user": 1.1
        }
        
    def analyze_task(self, task_description: str, context: str = "", 
                    priority: str = "MEDIUM", files: List[str] = None) -> TaskAnalysis:
        """Analyze task and recommend optimal model"""
        
        full_text = f"{task_description} {context}".lower()
        files = files or []
        
        # 1. Determine complexity
        complexity = self._classify_complexity(full_text)
        
        # 2. Identify categories
        categories = self._identify_categories(full_text)
        
        # 3. Assess reasoning requirements
        requires_reasoning = self._requires_advanced_reasoning(full_text)
        requires_creativity = self._requires_creativity(full_text)
        is_time_sensitive = priority.upper() in ["URGENT", "CRITICAL"]
        
        # 4. Estimate token usage
        input_tokens = self._estimate_input_tokens(task_description, context, files)
        output_tokens = self._estimate_output_tokens(complexity, categories)
        
        # 5. Select optimal model
        recommended_model, confidence, reasoning = self._select_model(
            complexity=complexity,
            requires_reasoning=requires_reasoning,
            requires_creativity=requires_creativity,
            is_time_sensitive=is_time_sensitive,
            priority=priority,
            categories=categories,
            input_tokens=input_tokens
        )
        
        # 6. Calculate cost
        model_config = MODEL_CONFIGS[recommended_model]
        estimated_cost = (
            (input_tokens / 1000) * model_config.cost_per_1k_input +
            (output_tokens / 1000) * model_config.cost_per_1k_output
        )
        
        return TaskAnalysis(
            complexity=complexity,
            recommended_model=recommended_model,
            confidence=confidence,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost=estimated_cost,
            reasoning=reasoning,
            task_categories=categories,
            requires_reasoning=requires_reasoning,
            requires_creativity=requires_creativity,
            is_time_sensitive=is_time_sensitive
        )
        
    def _classify_complexity(self, text: str) -> TaskComplexity:
        """Classify task complexity based on patterns"""
        complexity_scores = {complexity: 0.0 for complexity in TaskComplexity}
        
        for complexity, patterns in self.complexity_patterns.items():
            for pattern, weight in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                complexity_scores[complexity] += matches * weight
                
        # Apply priority multipliers
        for keyword, multiplier in self.priority_keywords.items():
            if keyword in text:
                for complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]:
                    complexity_scores[complexity] *= multiplier
                    
        # Return highest scoring complexity (with minimum threshold)
        max_complexity = max(complexity_scores.items(), key=lambda x: x[1])
        
        if max_complexity[1] < 0.5:  # No strong indicators
            return TaskComplexity.MODERATE  # Default to moderate
            
        return max_complexity[0]
        
    def _identify_categories(self, text: str) -> List[str]:
        """Identify task categories for specialization matching"""
        categories = []
        
        for category, patterns in self.category_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
                
            if score > 0:
                categories.append(category)
                
        return categories
        
    def _requires_advanced_reasoning(self, text: str) -> bool:
        """Check if task requires advanced reasoning capabilities"""
        reasoning_indicators = [
            r"design|architect|plan|strategy",
            r"analyze|investigate|research|explore",
            r"solve|problem|challenge|complex",
            r"optimize|improve|enhance|refactor",
            r"integrate|connect|coordinate|orchestrate",
            r"decision|choice|alternative|approach",
            r"scalability|performance|efficiency"
        ]
        
        score = 0
        for pattern in reasoning_indicators:
            score += len(re.findall(pattern, text, re.IGNORECASE))
            
        return score >= 2  # Requires reasoning if multiple indicators
        
    def _requires_creativity(self, text: str) -> bool:
        """Check if task requires creative problem solving"""
        creativity_indicators = [
            r"creative|innovative|novel|unique",
            r"brainstorm|ideate|invent|design",
            r"user\s+experience|ux|interface|ui",
            r"solution|approach|method|way",
            r"improve|enhance|better|optimize"
        ]
        
        score = 0
        for pattern in creativity_indicators:
            score += len(re.findall(pattern, text, re.IGNORECASE))
            
        return score >= 1
        
    def _estimate_input_tokens(self, description: str, context: str, files: List[str]) -> int:
        """Estimate input token count"""
        total_text = f"{description}\n{context}"
        
        # Add estimated file content (if files are involved)
        for file_path in files:
            if any(ext in file_path for ext in ['.py', '.js', '.ts', '.sql', '.md']):
                total_text += " " + "x" * 2000  # Estimate average file size
                
        return len(self.encoding.encode(total_text))
        
    def _estimate_output_tokens(self, complexity: TaskComplexity, categories: List[str]) -> int:
        """Estimate output token count based on complexity and categories"""
        base_tokens = {
            TaskComplexity.TRIVIAL: 500,
            TaskComplexity.SIMPLE: 1000,
            TaskComplexity.MODERATE: 2000,
            TaskComplexity.COMPLEX: 4000,
            TaskComplexity.EXPERT: 6000
        }
        
        tokens = base_tokens[complexity]
        
        # Adjust based on categories
        if "infrastructure" in categories:
            tokens *= 1.2  # Often involves configuration
        if "services" in categories:
            tokens *= 1.1  # Code generation
        if "domains" in categories:
            tokens *= 1.3  # UI/UX often needs more explanation
        if "ai_integration" in categories:
            tokens *= 1.4  # Complex integration patterns
            
        return int(tokens)
        
    def _select_model(self, complexity: TaskComplexity, requires_reasoning: bool,
                     requires_creativity: bool, is_time_sensitive: bool,
                     priority: str, categories: List[str], input_tokens: int) -> Tuple[ModelTier, float, str]:
        """Select optimal model based on task characteristics"""
        
        # Base model selection by complexity
        complexity_model_map = {
            TaskComplexity.TRIVIAL: ModelTier.HAIKU,
            TaskComplexity.SIMPLE: ModelTier.HAIKU,
            TaskComplexity.MODERATE: ModelTier.SONNET,
            TaskComplexity.COMPLEX: ModelTier.SONNET,
            TaskComplexity.EXPERT: ModelTier.OPUS
        }
        
        base_model = complexity_model_map[complexity]
        reasoning_parts = []
        
        # Factor 1: Complexity drives base selection
        if complexity in [TaskComplexity.TRIVIAL, TaskComplexity.SIMPLE]:
            if not requires_reasoning and not requires_creativity:
                model = ModelTier.HAIKU
                reasoning_parts.append(f"Simple {complexity.value} task suitable for efficient Haiku")
            else:
                model = ModelTier.SONNET  
                reasoning_parts.append(f"Simple task but requires reasoning/creativity - upgraded to Sonnet")
        
        elif complexity == TaskComplexity.MODERATE:
            if requires_reasoning or requires_creativity or "ai_integration" in categories:
                model = ModelTier.SONNET
                reasoning_parts.append("Moderate complexity with reasoning needs - Sonnet optimal")
            elif is_time_sensitive:
                model = ModelTier.HAIKU
                reasoning_parts.append("Moderate task but time-sensitive - Haiku for speed")
            else:
                model = ModelTier.SONNET
                reasoning_parts.append("Standard development task - Sonnet balanced choice")
                
        elif complexity == TaskComplexity.COMPLEX:
            if requires_reasoning and requires_creativity:
                model = ModelTier.OPUS
                reasoning_parts.append("Complex task requiring advanced reasoning - Opus needed")
            elif "infrastructure" in categories and not requires_creativity:
                model = ModelTier.SONNET
                reasoning_parts.append("Complex infrastructure but standard patterns - Sonnet sufficient")
            else:
                model = ModelTier.SONNET
                reasoning_parts.append("Complex task but within Sonnet capabilities")
                
        else:  # EXPERT
            model = ModelTier.OPUS
            reasoning_parts.append("Expert-level task requires Opus reasoning capabilities")
            
        # Factor 2: Priority overrides
        if priority.upper() == "CRITICAL":
            if complexity in [TaskComplexity.EXPERT, TaskComplexity.COMPLEX]:
                model = ModelTier.OPUS  # Critical complex tasks need best model
                reasoning_parts.append("CRITICAL priority - using Opus for reliability")
            elif is_time_sensitive and complexity == TaskComplexity.MODERATE:
                model = ModelTier.SONNET  # Balance speed and capability
                reasoning_parts.append("CRITICAL + time sensitive - Sonnet for balanced performance")
                
        # Factor 3: Token efficiency check
        model_config = MODEL_CONFIGS[model]
        if input_tokens > model_config.max_tokens * 0.8:  # Near token limit
            if model == ModelTier.HAIKU:
                model = ModelTier.SONNET  # Upgrade for token headroom
                reasoning_parts.append("Large input - upgraded to Sonnet for token capacity")
                
        # Factor 4: Cost optimization for batch tasks
        if not is_time_sensitive and complexity == TaskComplexity.MODERATE:
            estimated_cost_current = (input_tokens / 1000) * model_config.cost_per_1k_input
            if estimated_cost_current < 0.01:  # Very cheap task
                if model == ModelTier.SONNET:
                    model = ModelTier.HAIKU  # Downgrade for cost efficiency
                    reasoning_parts.append("Low-cost task - optimized to Haiku for efficiency")
                    
        # Calculate confidence based on how clear the decision was
        confidence = 0.7  # Base confidence
        if len(reasoning_parts) == 1:
            confidence = 0.9  # Clear single reason
        elif requires_reasoning and complexity in [TaskComplexity.EXPERT, TaskComplexity.COMPLEX]:
            confidence = 0.95  # Very clear need for advanced model
        elif complexity == TaskComplexity.TRIVIAL and not requires_reasoning:
            confidence = 0.95  # Very clear need for simple model
            
        reasoning = "; ".join(reasoning_parts)
        
        return model, confidence, reasoning
        
    def batch_analyze_tasks(self, tasks: List[Dict[str, Any]]) -> List[TaskAnalysis]:
        """Analyze multiple tasks for batch optimization"""
        analyses = []
        
        for task in tasks:
            analysis = self.analyze_task(
                task_description=task.get('description', ''),
                context=task.get('context', ''),
                priority=task.get('priority', 'MEDIUM'),
                files=task.get('files', [])
            )
            analyses.append(analysis)
            
        return analyses
        
    def optimize_task_distribution(self, analyses: List[TaskAnalysis]) -> Dict[ModelTier, List[int]]:
        """Optimize task distribution across models for cost efficiency"""
        distribution = {tier: [] for tier in ModelTier}
        
        # Group tasks by recommended model
        for i, analysis in enumerate(analyses):
            distribution[analysis.recommended_model].append(i)
            
        # Calculate costs and suggest optimizations
        total_cost = sum(analysis.estimated_cost for analysis in analyses)
        model_costs = {}
        
        for tier in ModelTier:
            task_indices = distribution[tier]
            tier_cost = sum(analyses[i].estimated_cost for i in task_indices)
            model_costs[tier] = tier_cost
            
        logger.info(f"Task distribution optimization: {len(analyses)} tasks, ${total_cost:.4f} total")
        for tier, cost in model_costs.items():
            task_count = len(distribution[tier])
            if task_count > 0:
                logger.info(f"  {tier.value}: {task_count} tasks, ${cost:.4f} ({cost/total_cost*100:.1f}%)")
                
        return distribution
        
    def get_model_stats(self) -> Dict[str, Any]:
        """Get statistics about available models"""
        stats = {}
        
        for tier, config in MODEL_CONFIGS.items():
            stats[tier.value] = {
                "model_name": config.model_name,
                "cost_per_1k_input": config.cost_per_1k_input,
                "cost_per_1k_output": config.cost_per_1k_output,
                "max_tokens": config.max_tokens,
                "speed_factor": config.speed_factor,
                "capability_score": config.capability_score,
                "best_for": config.best_for
            }
            
        return stats

class SmartTaskQueue:
    """Smart task queue with automatic model selection"""
    
    def __init__(self):
        self.classifier = TaskIntelligenceClassifier()
        self.tasks = {}
        self.task_counter = 0
        
    def add_task(self, description: str, context: str = "", priority: str = "MEDIUM",
                files: List[str] = None, metadata: Dict[str, Any] = None) -> str:
        """Add task with automatic analysis"""
        
        task_id = f"smart_task_{int(datetime.now().timestamp())}_{self.task_counter}"
        self.task_counter += 1
        
        # Analyze task
        analysis = self.classifier.analyze_task(description, context, priority, files)
        
        # Create task record
        task_record = {
            "id": task_id,
            "description": description,
            "context": context,
            "priority": priority,
            "files": files or [],
            "metadata": metadata or {},
            "analysis": asdict(analysis),
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        self.tasks[task_id] = task_record
        
        logger.info(f"Added smart task {task_id}: {analysis.recommended_model.value} "
                   f"({analysis.complexity.value}, ${analysis.estimated_cost:.4f})")
                   
        return task_id
        
    def get_optimal_tasks_for_model(self, model_tier: ModelTier, limit: int = 10) -> List[Dict]:
        """Get tasks optimally suited for specific model"""
        
        suitable_tasks = []
        
        for task_id, task in self.tasks.items():
            if task["status"] != "pending":
                continue
                
            analysis = TaskAnalysis(**task["analysis"])
            if analysis.recommended_model == model_tier:
                suitable_tasks.append(task)
                
        # Sort by confidence and priority
        def sort_key(task):
            analysis = TaskAnalysis(**task["analysis"])
            priority_weight = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
            return (analysis.confidence * priority_weight.get(task["priority"], 2))
            
        suitable_tasks.sort(key=sort_key, reverse=True)
        
        return suitable_tasks[:limit]
        
    def get_queue_summary(self) -> Dict[str, Any]:
        """Get summary of current task queue"""
        
        pending_tasks = [task for task in self.tasks.values() if task["status"] == "pending"]
        
        model_distribution = {tier.value: 0 for tier in ModelTier}
        complexity_distribution = {comp.value: 0 for comp in TaskComplexity}
        total_estimated_cost = 0.0
        
        for task in pending_tasks:
            analysis = TaskAnalysis(**task["analysis"])
            model_distribution[analysis.recommended_model.value] += 1
            complexity_distribution[analysis.complexity.value] += 1
            total_estimated_cost += analysis.estimated_cost
            
        return {
            "total_pending_tasks": len(pending_tasks),
            "model_distribution": model_distribution,
            "complexity_distribution": complexity_distribution,
            "total_estimated_cost": total_estimated_cost,
            "average_cost_per_task": total_estimated_cost / max(len(pending_tasks), 1)
        }

# Example usage and testing
if __name__ == "__main__":
    # Initialize system
    classifier = TaskIntelligenceClassifier()
    queue = SmartTaskQueue()
    
    # Test tasks of varying complexity
    test_tasks = [
        {
            "description": "Fix typo in README.md file",
            "priority": "LOW"
        },
        {
            "description": "Implement user authentication API with JWT tokens and role-based access control",
            "context": "Need secure authentication for ActiveLog fitness tracking application",
            "priority": "HIGH",
            "files": ["src/auth.py", "src/models/user.py"]
        },
        {
            "description": "Design scalable microservices architecture for cross-domain analytics engine",
            "context": "Handle millions of fitness data points with real-time correlation analysis",
            "priority": "CRITICAL"
        },
        {
            "description": "Add logging to existing function",
            "priority": "MEDIUM"
        },
        {
            "description": "Research and implement novel machine learning approach for personalized fitness recommendations",
            "context": "Combine multiple data sources with advanced AI for breakthrough user experience",
            "priority": "HIGH"
        }
    ]
    
    print("🧠 Smart Task Classification Results:")
    print("=" * 60)
    
    task_ids = []
    for task in test_tasks:
        task_id = queue.add_task(**task)
        task_ids.append(task_id)
        
        analysis = classifier.analyze_task(
            task.get("description", ""),
            task.get("context", ""),
            task.get("priority", "MEDIUM"),
            task.get("files", [])
        )
        
        print(f"\n📋 Task: {task['description'][:60]}...")
        print(f"🤖 Model: {analysis.recommended_model.value.upper()} "
              f"({analysis.confidence:.1%} confidence)")
        print(f"🧩 Complexity: {analysis.complexity.value}")
        print(f"💰 Cost: ${analysis.estimated_cost:.4f}")
        print(f"🎯 Reasoning: {analysis.reasoning}")
        
    print(f"\n📊 Queue Summary:")
    summary = queue.get_queue_summary()
    print(f"  Total tasks: {summary['total_pending_tasks']}")
    print(f"  Total cost: ${summary['total_estimated_cost']:.4f}")
    print(f"  Model distribution: {summary['model_distribution']}")
    
    print(f"\n🎯 Optimal task distribution:")
    for tier in ModelTier:
        tasks = queue.get_optimal_tasks_for_model(tier, 5)
        if tasks:
            print(f"  {tier.value}: {len(tasks)} tasks recommended")