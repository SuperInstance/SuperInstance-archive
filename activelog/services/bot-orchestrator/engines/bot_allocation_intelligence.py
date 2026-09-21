"""
Advanced Bot Allocation Intelligence System
Intelligently allocates tasks to the optimal bots based on capabilities, cost, performance, and load
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import math

from ..director.claude_director import Task, TaskPriority, TaskStatus
from ..engines.task_decomposition_engine import TaskComplexity, TaskCategory, Subtask
from ..integrations.local_llm_connector import LocalLLMConnector

logger = logging.getLogger(__name__)

class BotCapabilityLevel(Enum):
    BASIC = 1       # Simple tasks, local models
    INTERMEDIATE = 2 # Moderate complexity, some API models
    ADVANCED = 3    # Complex tasks, premium models
    EXPERT = 4      # Highest complexity, best models

class BotStatus(Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    OFFLINE = "offline"
    MAINTENANCE = "maintenance"

@dataclass
class BotCapabilities:
    """Detailed bot capabilities and metrics"""
    bot_id: str
    name: str
    provider: str
    capability_level: BotCapabilityLevel
    max_tokens: int
    max_concurrent_tasks: int
    cost_per_1k_tokens: float
    
    # Performance metrics
    avg_latency_ms: float
    success_rate: float
    quality_score: float
    uptime_percentage: float
    
    # Specializations
    strengths: List[str]
    weaknesses: List[str]
    preferred_categories: List[TaskCategory]
    
    # Current state
    current_load: int
    status: BotStatus
    last_used: Optional[datetime]
    total_tasks_completed: int
    
    # Cost and performance history
    performance_history: List[Dict[str, Any]]
    cost_efficiency_score: float
    
    def is_available(self) -> bool:
        return (self.status == BotStatus.AVAILABLE and 
                self.current_load < self.max_concurrent_tasks)
    
    def get_load_percentage(self) -> float:
        return (self.current_load / self.max_concurrent_tasks) * 100 if self.max_concurrent_tasks > 0 else 0

@dataclass
class AllocationDecision:
    """Result of bot allocation decision"""
    task_id: str
    allocated_bot_id: str
    confidence_score: float
    expected_cost: float
    expected_latency_ms: float
    expected_quality: float
    reasoning: str
    fallback_options: List[str]
    allocation_strategy: str

@dataclass
class AllocationConstraints:
    """Constraints for bot allocation"""
    max_cost: Optional[float] = None
    max_latency_ms: Optional[int] = None
    min_quality: Optional[float] = None
    preferred_providers: Optional[List[str]] = None
    excluded_bots: Optional[List[str]] = None
    require_local: Optional[bool] = None
    priority_multiplier: float = 1.0

class BotAllocationIntelligence:
    """Advanced bot allocation system with ML-like intelligence"""
    
    def __init__(self, local_llm_connector: Optional[LocalLLMConnector] = None):
        self.local_llm_connector = local_llm_connector
        self.bots: Dict[str, BotCapabilities] = {}
        self.allocation_history: List[Dict[str, Any]] = []
        self.performance_weights = {
            "cost": 0.3,
            "quality": 0.25,
            "latency": 0.2,
            "load_balancing": 0.15,
            "success_rate": 0.1
        }
        
        # Initialize default bot fleet
        self._initialize_default_bots()
        
        # Learning parameters
        self.learning_rate = 0.1
        self.performance_decay_factor = 0.95  # For aging historical data
        
        # Allocation strategies
        self.strategies = {
            "cost_optimized": self._cost_optimized_strategy,
            "performance_optimized": self._performance_optimized_strategy,
            "balanced": self._balanced_strategy,
            "quality_focused": self._quality_focused_strategy,
            "speed_focused": self._speed_focused_strategy,
            "load_balanced": self._load_balanced_strategy
        }
    
    def _initialize_default_bots(self):
        """Initialize the default bot fleet"""
        # Local LLM Pool - Free tier
        self.bots["local-llm-pool"] = BotCapabilities(
            bot_id="local-llm-pool",
            name="Local LLM Pool",
            provider="local",
            capability_level=BotCapabilityLevel.BASIC,
            max_tokens=8000,
            max_concurrent_tasks=10,
            cost_per_1k_tokens=0.0,
            avg_latency_ms=2000,
            success_rate=0.85,
            quality_score=0.75,
            uptime_percentage=0.95,
            strengths=["cost_effective", "privacy", "simple_tasks", "high_throughput"],
            weaknesses=["complex_reasoning", "latest_knowledge", "consistency"],
            preferred_categories=[TaskCategory.CONTENT_CREATION, TaskCategory.GENERAL],
            current_load=0,
            status=BotStatus.AVAILABLE,
            last_used=None,
            total_tasks_completed=0,
            performance_history=[],
            cost_efficiency_score=1.0
        )
        
        # Claude Haiku - Fast and cheap
        self.bots["claude-haiku"] = BotCapabilities(
            bot_id="claude-haiku",
            name="Claude 3 Haiku",
            provider="anthropic",
            capability_level=BotCapabilityLevel.INTERMEDIATE,
            max_tokens=100000,
            max_concurrent_tasks=8,
            cost_per_1k_tokens=0.25,
            avg_latency_ms=1200,
            success_rate=0.92,
            quality_score=0.85,
            uptime_percentage=0.99,
            strengths=["speed", "cost_effective", "simple_tasks", "summarization"],
            weaknesses=["complex_reasoning", "creative_writing"],
            preferred_categories=[TaskCategory.DOCUMENTATION, TaskCategory.TESTING],
            current_load=0,
            status=BotStatus.AVAILABLE,
            last_used=None,
            total_tasks_completed=0,
            performance_history=[],
            cost_efficiency_score=0.9
        )
        
        # Claude Sonnet - Balanced
        self.bots["claude-sonnet"] = BotCapabilities(
            bot_id="claude-sonnet",
            name="Claude 3.5 Sonnet",
            provider="anthropic",
            capability_level=BotCapabilityLevel.ADVANCED,
            max_tokens=200000,
            max_concurrent_tasks=5,
            cost_per_1k_tokens=3.0,
            avg_latency_ms=2500,
            success_rate=0.95,
            quality_score=0.92,
            uptime_percentage=0.99,
            strengths=["balanced", "code_generation", "analysis", "writing"],
            weaknesses=["very_complex_reasoning"],
            preferred_categories=[TaskCategory.CODE_DEVELOPMENT, TaskCategory.DATA_ANALYSIS],
            current_load=0,
            status=BotStatus.AVAILABLE,
            last_used=None,
            total_tasks_completed=0,
            performance_history=[],
            cost_efficiency_score=0.8
        )
        
        # Claude Opus - Premium
        self.bots["claude-opus"] = BotCapabilities(
            bot_id="claude-opus",
            name="Claude 3 Opus",
            provider="anthropic",
            capability_level=BotCapabilityLevel.EXPERT,
            max_tokens=200000,
            max_concurrent_tasks=3,
            cost_per_1k_tokens=15.0,
            avg_latency_ms=4000,
            success_rate=0.98,
            quality_score=0.97,
            uptime_percentage=0.99,
            strengths=["complex_reasoning", "research", "expert_analysis", "creative_problem_solving"],
            weaknesses=["cost", "speed"],
            preferred_categories=[TaskCategory.RESEARCH, TaskCategory.PROJECT_MANAGEMENT],
            current_load=0,
            status=BotStatus.AVAILABLE,
            last_used=None,
            total_tasks_completed=0,
            performance_history=[],
            cost_efficiency_score=0.6
        )
    
    async def allocate_bot(
        self,
        task: Task,
        constraints: Optional[AllocationConstraints] = None,
        strategy: str = "balanced"
    ) -> Optional[AllocationDecision]:
        """Allocate the optimal bot for a task"""
        
        if strategy not in self.strategies:
            logger.warning(f"Unknown strategy {strategy}, using balanced")
            strategy = "balanced"
        
        # Update bot availability
        await self._update_bot_availability()
        
        # Get available bots
        available_bots = [bot for bot in self.bots.values() if bot.is_available()]
        
        if not available_bots:
            logger.warning("No bots available for allocation")
            return None
        
        # Apply constraints
        if constraints:
            available_bots = self._apply_constraints(available_bots, constraints)
        
        if not available_bots:
            logger.warning("No bots available after applying constraints")
            return None
        
        # Use selected strategy to choose bot
        allocation_func = self.strategies[strategy]
        decision = await allocation_func(task, available_bots, constraints)
        
        if decision:
            # Reserve the bot
            await self._reserve_bot(decision.allocated_bot_id)
            
            # Record allocation decision
            self.allocation_history.append({
                "timestamp": datetime.now(),
                "task_id": task.id,
                "bot_id": decision.allocated_bot_id,
                "strategy": strategy,
                "confidence": decision.confidence_score,
                "expected_cost": decision.expected_cost,
                "expected_latency": decision.expected_latency_ms
            })
        
        return decision
    
    async def _update_bot_availability(self):
        """Update bot availability and status"""
        # Update local LLM availability
        if self.local_llm_connector:
            try:
                health = await self.local_llm_connector.health_check()
                local_bot = self.bots.get("local-llm-pool")
                if local_bot:
                    if health.get("status") == "healthy":
                        local_bot.status = BotStatus.AVAILABLE
                        local_bot.uptime_percentage = 0.95
                    else:
                        local_bot.status = BotStatus.OFFLINE
                        local_bot.uptime_percentage = 0.0
            except Exception as e:
                logger.warning(f"Failed to check local LLM health: {e}")
                local_bot = self.bots.get("local-llm-pool")
                if local_bot:
                    local_bot.status = BotStatus.OFFLINE
    
    def _apply_constraints(self, bots: List[BotCapabilities], constraints: AllocationConstraints) -> List[BotCapabilities]:
        """Apply allocation constraints to filter bots"""
        filtered_bots = bots.copy()
        
        # Cost constraint
        if constraints.max_cost is not None:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.cost_per_1k_tokens == 0 or  # Free models pass
                   self._estimate_task_cost(bot, 2000) <= constraints.max_cost  # Rough estimate
            ]
        
        # Latency constraint
        if constraints.max_latency_ms is not None:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.avg_latency_ms <= constraints.max_latency_ms
            ]
        
        # Quality constraint
        if constraints.min_quality is not None:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.quality_score >= constraints.min_quality
            ]
        
        # Provider preference
        if constraints.preferred_providers:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.provider in constraints.preferred_providers
            ]
        
        # Excluded bots
        if constraints.excluded_bots:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.bot_id not in constraints.excluded_bots
            ]
        
        # Local requirement
        if constraints.require_local:
            filtered_bots = [
                bot for bot in filtered_bots
                if bot.provider == "local"
            ]
        
        return filtered_bots
    
    async def _cost_optimized_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Cost-optimized allocation strategy"""
        
        # Sort by cost (free first, then cheapest)
        sorted_bots = sorted(available_bots, key=lambda b: b.cost_per_1k_tokens)
        
        for bot in sorted_bots:
            # Check if bot can handle the task
            if self._can_handle_task(bot, task):
                expected_cost = self._estimate_task_cost(bot, task.estimated_tokens)
                
                return AllocationDecision(
                    task_id=task.id,
                    allocated_bot_id=bot.bot_id,
                    confidence_score=0.8 if bot.cost_per_1k_tokens == 0 else 0.6,
                    expected_cost=expected_cost,
                    expected_latency_ms=bot.avg_latency_ms,
                    expected_quality=bot.quality_score,
                    reasoning=f"Selected {bot.name} for optimal cost ({expected_cost:.4f})",
                    fallback_options=[b.bot_id for b in sorted_bots[1:3]],
                    allocation_strategy="cost_optimized"
                )
        
        return None
    
    async def _performance_optimized_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Performance-optimized allocation strategy"""
        
        # Calculate performance scores
        bot_scores = []
        for bot in available_bots:
            if self._can_handle_task(bot, task):
                # Performance score based on success rate, quality, and uptime
                performance_score = (
                    bot.success_rate * 0.4 +
                    bot.quality_score * 0.4 +
                    bot.uptime_percentage * 0.2
                )
                bot_scores.append((bot, performance_score))
        
        if not bot_scores:
            return None
        
        # Sort by performance score (highest first)
        bot_scores.sort(key=lambda x: x[1], reverse=True)
        best_bot, best_score = bot_scores[0]
        
        expected_cost = self._estimate_task_cost(best_bot, task.estimated_tokens)
        
        return AllocationDecision(
            task_id=task.id,
            allocated_bot_id=best_bot.bot_id,
            confidence_score=best_score,
            expected_cost=expected_cost,
            expected_latency_ms=best_bot.avg_latency_ms,
            expected_quality=best_bot.quality_score,
            reasoning=f"Selected {best_bot.name} for optimal performance (score: {best_score:.2f})",
            fallback_options=[bot.bot_id for bot, _ in bot_scores[1:3]],
            allocation_strategy="performance_optimized"
        )
    
    async def _balanced_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Balanced allocation strategy considering multiple factors"""
        
        bot_scores = []
        for bot in available_bots:
            if self._can_handle_task(bot, task):
                score = self._calculate_balanced_score(bot, task)
                bot_scores.append((bot, score))
        
        if not bot_scores:
            return None
        
        # Sort by balanced score (highest first)
        bot_scores.sort(key=lambda x: x[1], reverse=True)
        best_bot, best_score = bot_scores[0]
        
        expected_cost = self._estimate_task_cost(best_bot, task.estimated_tokens)
        
        return AllocationDecision(
            task_id=task.id,
            allocated_bot_id=best_bot.bot_id,
            confidence_score=best_score,
            expected_cost=expected_cost,
            expected_latency_ms=best_bot.avg_latency_ms,
            expected_quality=best_bot.quality_score,
            reasoning=f"Selected {best_bot.name} for balanced optimization (score: {best_score:.2f})",
            fallback_options=[bot.bot_id for bot, _ in bot_scores[1:3]],
            allocation_strategy="balanced"
        )
    
    async def _quality_focused_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Quality-focused allocation strategy"""
        
        # Sort by quality score (highest first)
        quality_sorted = [
            bot for bot in available_bots 
            if self._can_handle_task(bot, task)
        ]
        quality_sorted.sort(key=lambda b: b.quality_score, reverse=True)
        
        if not quality_sorted:
            return None
        
        best_bot = quality_sorted[0]
        expected_cost = self._estimate_task_cost(best_bot, task.estimated_tokens)
        
        return AllocationDecision(
            task_id=task.id,
            allocated_bot_id=best_bot.bot_id,
            confidence_score=best_bot.quality_score,
            expected_cost=expected_cost,
            expected_latency_ms=best_bot.avg_latency_ms,
            expected_quality=best_bot.quality_score,
            reasoning=f"Selected {best_bot.name} for highest quality ({best_bot.quality_score:.2f})",
            fallback_options=[bot.bot_id for bot in quality_sorted[1:3]],
            allocation_strategy="quality_focused"
        )
    
    async def _speed_focused_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Speed-focused allocation strategy"""
        
        # Sort by latency (lowest first)
        speed_sorted = [
            bot for bot in available_bots
            if self._can_handle_task(bot, task)
        ]
        speed_sorted.sort(key=lambda b: b.avg_latency_ms)
        
        if not speed_sorted:
            return None
        
        fastest_bot = speed_sorted[0]
        expected_cost = self._estimate_task_cost(fastest_bot, task.estimated_tokens)
        
        return AllocationDecision(
            task_id=task.id,
            allocated_bot_id=fastest_bot.bot_id,
            confidence_score=0.8,
            expected_cost=expected_cost,
            expected_latency_ms=fastest_bot.avg_latency_ms,
            expected_quality=fastest_bot.quality_score,
            reasoning=f"Selected {fastest_bot.name} for fastest response ({fastest_bot.avg_latency_ms}ms)",
            fallback_options=[bot.bot_id for bot in speed_sorted[1:3]],
            allocation_strategy="speed_focused"
        )
    
    async def _load_balanced_strategy(
        self,
        task: Task,
        available_bots: List[BotCapabilities],
        constraints: Optional[AllocationConstraints]
    ) -> Optional[AllocationDecision]:
        """Load-balanced allocation strategy"""
        
        suitable_bots = [bot for bot in available_bots if self._can_handle_task(bot, task)]
        
        if not suitable_bots:
            return None
        
        # Find bot with lowest load percentage
        least_loaded_bot = min(suitable_bots, key=lambda b: b.get_load_percentage())
        
        expected_cost = self._estimate_task_cost(least_loaded_bot, task.estimated_tokens)
        
        return AllocationDecision(
            task_id=task.id,
            allocated_bot_id=least_loaded_bot.bot_id,
            confidence_score=0.7,
            expected_cost=expected_cost,
            expected_latency_ms=least_loaded_bot.avg_latency_ms,
            expected_quality=least_loaded_bot.quality_score,
            reasoning=f"Selected {least_loaded_bot.name} for load balancing ({least_loaded_bot.get_load_percentage():.1f}% load)",
            fallback_options=[bot.bot_id for bot in suitable_bots[1:3]],
            allocation_strategy="load_balanced"
        )
    
    def _calculate_balanced_score(self, bot: BotCapabilities, task: Task) -> float:
        """Calculate balanced score considering all factors"""
        # Normalize metrics to 0-1 scale
        
        # Cost score (lower cost = higher score)
        cost_score = 1.0 if bot.cost_per_1k_tokens == 0 else max(0, 1.0 - (bot.cost_per_1k_tokens / 20.0))
        
        # Quality score (already 0-1)
        quality_score = bot.quality_score
        
        # Latency score (lower latency = higher score)
        latency_score = max(0, 1.0 - (bot.avg_latency_ms / 10000.0))
        
        # Load balancing score (lower load = higher score)
        load_score = 1.0 - (bot.get_load_percentage() / 100.0)
        
        # Success rate score (already 0-1)
        success_score = bot.success_rate
        
        # Category matching bonus
        task_category = self._infer_task_category(task)
        category_bonus = 0.1 if task_category in bot.preferred_categories else 0.0
        
        # Priority adjustment
        priority_multiplier = {
            TaskPriority.LOW: 0.8,
            TaskPriority.MEDIUM: 1.0,
            TaskPriority.HIGH: 1.2,
            TaskPriority.CRITICAL: 1.5
        }.get(task.priority, 1.0)
        
        # Calculate weighted score
        weighted_score = (
            cost_score * self.performance_weights["cost"] +
            quality_score * self.performance_weights["quality"] +
            latency_score * self.performance_weights["latency"] +
            load_score * self.performance_weights["load_balancing"] +
            success_score * self.performance_weights["success_rate"] +
            category_bonus
        ) * priority_multiplier
        
        return min(1.0, weighted_score)
    
    def _can_handle_task(self, bot: BotCapabilities, task: Task) -> bool:
        """Check if bot can handle the task"""
        # Token capacity check
        if task.estimated_tokens > bot.max_tokens:
            return False
        
        # Capability level check
        task_complexity = self._infer_task_complexity(task)
        if task_complexity == TaskComplexity.EXPERT and bot.capability_level.value < 3:
            return False
        
        # Status check
        if not bot.is_available():
            return False
        
        return True
    
    def _infer_task_category(self, task: Task) -> TaskCategory:
        """Infer task category from description"""
        description = task.description.lower()
        
        # Simple keyword matching (could be enhanced with ML)
        if any(word in description for word in ["code", "implement", "function", "class", "script"]):
            return TaskCategory.CODE_DEVELOPMENT
        elif any(word in description for word in ["data", "analyze", "statistics", "metrics"]):
            return TaskCategory.DATA_ANALYSIS
        elif any(word in description for word in ["research", "investigate", "find", "study"]):
            return TaskCategory.RESEARCH
        elif any(word in description for word in ["write", "document", "create", "draft"]):
            return TaskCategory.CONTENT_CREATION
        elif any(word in description for word in ["test", "validate", "verify", "check"]):
            return TaskCategory.TESTING
        elif any(word in description for word in ["deploy", "configure", "setup", "admin"]):
            return TaskCategory.SYSTEM_ADMINISTRATION
        else:
            return TaskCategory.GENERAL
    
    def _infer_task_complexity(self, task: Task) -> TaskComplexity:
        """Infer task complexity"""
        description = task.description.lower()
        
        # Token-based complexity estimation
        if task.estimated_tokens < 500:
            return TaskComplexity.TRIVIAL
        elif task.estimated_tokens < 1500:
            return TaskComplexity.SIMPLE
        elif task.estimated_tokens < 5000:
            return TaskComplexity.MODERATE
        elif task.estimated_tokens < 15000:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.EXPERT
    
    def _estimate_task_cost(self, bot: BotCapabilities, estimated_tokens: int) -> float:
        """Estimate cost for running task on bot"""
        if bot.cost_per_1k_tokens == 0:
            return 0.0
        
        return (estimated_tokens / 1000.0) * bot.cost_per_1k_tokens
    
    async def _reserve_bot(self, bot_id: str):
        """Reserve a bot for task execution"""
        bot = self.bots.get(bot_id)
        if bot:
            bot.current_load += 1
            bot.last_used = datetime.now()
            
            # Update status based on load
            if bot.current_load >= bot.max_concurrent_tasks:
                bot.status = BotStatus.OVERLOADED
    
    async def release_bot(self, bot_id: str):
        """Release a bot after task completion"""
        bot = self.bots.get(bot_id)
        if bot:
            bot.current_load = max(0, bot.current_load - 1)
            bot.total_tasks_completed += 1
            
            # Update status
            if bot.current_load < bot.max_concurrent_tasks:
                bot.status = BotStatus.AVAILABLE
    
    async def update_bot_performance(self, bot_id: str, performance_data: Dict[str, Any]):
        """Update bot performance metrics based on execution results"""
        bot = self.bots.get(bot_id)
        if not bot:
            return
        
        # Update metrics with exponential moving average
        alpha = self.learning_rate
        
        if "latency_ms" in performance_data:
            bot.avg_latency_ms = (1 - alpha) * bot.avg_latency_ms + alpha * performance_data["latency_ms"]
        
        if "success" in performance_data:
            new_success = 1.0 if performance_data["success"] else 0.0
            bot.success_rate = (1 - alpha) * bot.success_rate + alpha * new_success
        
        if "quality_score" in performance_data:
            bot.quality_score = (1 - alpha) * bot.quality_score + alpha * performance_data["quality_score"]
        
        # Update cost efficiency
        if "cost" in performance_data and "success" in performance_data:
            efficiency = 1.0 / (performance_data["cost"] + 0.001) if performance_data["success"] else 0.1
            bot.cost_efficiency_score = (1 - alpha) * bot.cost_efficiency_score + alpha * efficiency
        
        # Add to performance history (keep last 100 entries)
        bot.performance_history.append({
            "timestamp": datetime.now().isoformat(),
            **performance_data
        })
        
        if len(bot.performance_history) > 100:
            bot.performance_history = bot.performance_history[-100:]
    
    def get_bot_stats(self) -> Dict[str, Any]:
        """Get comprehensive bot statistics"""
        stats = {
            "total_bots": len(self.bots),
            "available_bots": sum(1 for bot in self.bots.values() if bot.is_available()),
            "total_capacity": sum(bot.max_concurrent_tasks for bot in self.bots.values()),
            "current_load": sum(bot.current_load for bot in self.bots.values()),
            "bots": {}
        }
        
        for bot_id, bot in self.bots.items():
            stats["bots"][bot_id] = {
                "name": bot.name,
                "provider": bot.provider,
                "status": bot.status.value,
                "load_percentage": bot.get_load_percentage(),
                "success_rate": bot.success_rate,
                "avg_latency_ms": bot.avg_latency_ms,
                "quality_score": bot.quality_score,
                "cost_per_1k_tokens": bot.cost_per_1k_tokens,
                "total_tasks": bot.total_tasks_completed,
                "cost_efficiency": bot.cost_efficiency_score
            }
        
        return stats
    
    def get_allocation_analytics(self) -> Dict[str, Any]:
        """Get allocation decision analytics"""
        if not self.allocation_history:
            return {"total_allocations": 0}
        
        recent_allocations = [
            alloc for alloc in self.allocation_history 
            if alloc["timestamp"] > datetime.now() - timedelta(hours=24)
        ]
        
        strategies_used = {}
        total_cost = 0.0
        avg_confidence = 0.0
        
        for allocation in recent_allocations:
            strategy = allocation["strategy"]
            strategies_used[strategy] = strategies_used.get(strategy, 0) + 1
            total_cost += allocation["expected_cost"]
            avg_confidence += allocation["confidence"]
        
        if recent_allocations:
            avg_confidence /= len(recent_allocations)
        
        return {
            "total_allocations": len(self.allocation_history),
            "recent_allocations_24h": len(recent_allocations),
            "strategies_used": strategies_used,
            "total_expected_cost_24h": total_cost,
            "avg_confidence": avg_confidence,
            "most_used_strategy": max(strategies_used.items(), key=lambda x: x[1])[0] if strategies_used else None
        }
    
    async def recommend_strategy(self, task: Task) -> str:
        """Recommend the best allocation strategy for a task"""
        task_category = self._infer_task_category(task)
        task_complexity = self._infer_task_complexity(task)
        
        # Strategy recommendations based on task characteristics
        if task.priority == TaskPriority.CRITICAL:
            return "quality_focused"
        elif task.priority == TaskPriority.HIGH and task_complexity in [TaskComplexity.COMPLEX, TaskComplexity.EXPERT]:
            return "performance_optimized"
        elif task_complexity == TaskComplexity.TRIVIAL:
            return "cost_optimized"
        elif task_category in [TaskCategory.RESEARCH, TaskCategory.DATA_ANALYSIS]:
            return "quality_focused"
        elif task_category in [TaskCategory.TESTING, TaskCategory.DOCUMENTATION]:
            return "speed_focused"
        else:
            return "balanced"
    
    def optimize_weights(self, feedback_data: List[Dict[str, Any]]):
        """Optimize performance weights based on feedback"""
        # Simple gradient descent-like optimization
        # In a real system, this would use more sophisticated ML techniques
        
        for feedback in feedback_data:
            if feedback.get("user_satisfaction") and feedback.get("allocation_id"):
                satisfaction = feedback["user_satisfaction"]  # 0-1 scale
                
                # Find the allocation
                matching_alloc = None
                for alloc in self.allocation_history:
                    if alloc.get("allocation_id") == feedback["allocation_id"]:
                        matching_alloc = alloc
                        break
                
                if matching_alloc:
                    # Adjust weights based on what was prioritized and satisfaction
                    adjustment = (satisfaction - 0.5) * self.learning_rate
                    
                    if matching_alloc["strategy"] == "cost_optimized":
                        self.performance_weights["cost"] += adjustment
                    elif matching_alloc["strategy"] == "quality_focused":
                        self.performance_weights["quality"] += adjustment
                    elif matching_alloc["strategy"] == "speed_focused":
                        self.performance_weights["latency"] += adjustment
                    
                    # Normalize weights to sum to 1
                    total = sum(self.performance_weights.values())
                    for key in self.performance_weights:
                        self.performance_weights[key] /= total