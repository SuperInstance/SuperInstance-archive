#!/usr/bin/env python3
"""
Unified Model Orchestrator
Intelligently coordinates between Claude, OpenAI, and local AI models with user preference learning
"""

import asyncio
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os

from openai_model_manager import OpenAIModelManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ModelProvider:
    """Represents a model provider (Claude, OpenAI, Local)"""
    name: str
    models: Dict[str, Any]
    rate_limits: Dict[str, Any]
    cost_structure: str  # 'subscription', 'pay_per_use', 'free'
    strengths: List[str]
    weaknesses: List[str]

@dataclass
class TaskRequest:
    """Unified task request structure"""
    user_id: str
    task_description: str
    context: Optional[str] = None
    priority: int = 5  # 1-10
    user_initiated: bool = False  # True if user directly requested, False if bot-automated
    max_cost: Optional[float] = None
    preferred_provider: Optional[str] = None  # 'claude', 'openai', 'local'
    quality_requirement: int = 7  # 1-10
    speed_requirement: int = 5  # 1-10
    creativity_needed: bool = False
    multimodal_needed: bool = False

@dataclass
class ExecutionResult:
    """Result from model execution"""
    provider_used: str
    model_used: str
    success: bool
    content: str
    tokens_used: int
    cost: float
    execution_time: float
    quality_score: float
    user_satisfaction: Optional[float] = None
    feedback: Optional[str] = None

class UnifiedModelOrchestrator:
    """Orchestrates between Claude, OpenAI, and local AI models with intelligent selection"""
    
    def __init__(self):
        self.openai_manager = OpenAIModelManager()
        self.providers = self._initialize_providers()
        
        # User preference learning (enhanced)
        self.user_model_preferences: Dict[str, Dict] = {}  # user_id -> preferences
        self.execution_history: List[Dict] = []
        
        # Cost tracking per user
        self.user_cost_tracking: Dict[str, Dict] = {}
        
        # Provider availability and performance
        self.provider_health: Dict[str, Dict] = {
            "claude": {"available": True, "response_time": 0.0, "success_rate": 1.0},
            "openai": {"available": True, "response_time": 0.0, "success_rate": 1.0},
            "local": {"available": True, "response_time": 0.0, "success_rate": 0.8}
        }
        
        # Learning parameters
        self.learning_rate = 0.15
        self.preference_decay = 0.02  # Gradual forgetting of old preferences
    
    def _initialize_providers(self) -> Dict[str, ModelProvider]:
        """Initialize model provider configurations"""
        return {
            "claude": ModelProvider(
                name="Claude (Anthropic)",
                models={
                    "opus": {"reasoning": 10, "cost": 0.015, "speed": 6, "context": 200000},
                    "sonnet": {"reasoning": 8, "cost": 0.003, "speed": 8, "context": 100000},
                    "haiku": {"reasoning": 6, "cost": 0.00025, "speed": 10, "context": 50000}
                },
                rate_limits={"requests_per_hour": 1000, "tokens_per_hour": 1000000},
                cost_structure="subscription",
                strengths=["reasoning", "analysis", "coding", "safety", "consistency"],
                weaknesses=["image_generation", "audio_processing", "real_time"]
            ),
            
            "openai": ModelProvider(
                name="OpenAI",
                models={
                    "gpt-4-turbo": {"reasoning": 9, "cost": 0.01, "speed": 7, "context": 128000},
                    "gpt-4o": {"reasoning": 9, "cost": 0.005, "speed": 8, "context": 128000, "multimodal": True},
                    "gpt-4o-mini": {"reasoning": 7, "cost": 0.00015, "speed": 9, "context": 128000, "multimodal": True},
                    "dall-e-3": {"reasoning": 0, "cost": 0.04, "speed": 5, "image_gen": True},
                    "whisper-1": {"reasoning": 0, "cost": 0.006, "speed": 7, "audio": True}
                },
                rate_limits={"user_requests": "unlimited", "bot_requests": "10min_interval"},
                cost_structure="pay_per_use",
                strengths=["multimodal", "image_generation", "audio", "creativity", "variety"],
                weaknesses=["cost_predictability", "consistency"]
            ),
            
            "local": ModelProvider(
                name="Local AI Assistants",
                models={
                    "aixcoder": {"reasoning": 4, "cost": 0.0, "speed": 10, "coding": True},
                    "tabnine": {"reasoning": 3, "cost": 0.0, "speed": 10, "completion": True},
                    "continue": {"reasoning": 5, "cost": 0.0, "speed": 9, "refactoring": True},
                    "fauxpilot": {"reasoning": 5, "cost": 0.0, "speed": 9, "generation": True}
                },
                rate_limits={"unlimited": True},
                cost_structure="free",
                strengths=["cost_free", "privacy", "speed", "offline"],
                weaknesses=["limited_reasoning", "no_multimodal", "basic_tasks_only"]
            )
        }
    
    async def execute_task(self, request: TaskRequest) -> ExecutionResult:
        """Execute task with intelligent provider selection"""
        
        logger.info(f"🎯 Executing task for {request.user_id}: {request.task_description[:60]}...")
        
        # Select optimal provider and model
        provider, model = await self._intelligent_provider_selection(request)
        
        if not provider or not model:
            return ExecutionResult(
                provider_used="none",
                model_used="none", 
                success=False,
                content="No suitable provider available",
                tokens_used=0,
                cost=0.0,
                execution_time=0.0,
                quality_score=0.0
            )
        
        # Execute with selected provider
        start_time = datetime.now()
        
        try:
            result = await self._execute_with_provider(provider, model, request)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Track execution
            execution_record = {
                "timestamp": start_time,
                "user_id": request.user_id,
                "task": request.task_description,
                "user_initiated": request.user_initiated,
                "provider": provider,
                "model": model,
                "result": result
            }
            
            self.execution_history.append(execution_record)
            self._update_cost_tracking(request.user_id, provider, result)
            self._update_provider_health(provider, True, execution_time)
            
            logger.info(f"✅ Task completed: {provider}/{model} - Cost: ${result.cost:.4f}")
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_provider_health(provider, False, execution_time)
            
            logger.error(f"❌ Task execution failed with {provider}/{model}: {e}")
            
            return ExecutionResult(
                provider_used=provider,
                model_used=model,
                success=False,
                content=f"Execution failed: {str(e)}",
                tokens_used=0,
                cost=0.0,
                execution_time=execution_time,
                quality_score=0.0
            )
    
    async def _intelligent_provider_selection(self, request: TaskRequest) -> Tuple[Optional[str], Optional[str]]:
        """Intelligently select provider and model based on task and user preferences"""
        
        # If user specified preference, respect it (with validation)
        if request.preferred_provider:
            if request.preferred_provider in self.providers:
                model = await self._select_model_from_provider(request.preferred_provider, request)
                if model:
                    return request.preferred_provider, model
        
        # Score each provider/model combination
        provider_scores = {}
        
        for provider_name, provider in self.providers.items():
            if not self.provider_health[provider_name]["available"]:
                continue
            
            best_model, best_score = await self._score_provider(provider_name, provider, request)
            if best_model:
                provider_scores[provider_name] = {
                    "model": best_model,
                    "score": best_score,
                    "provider": provider
                }
        
        if not provider_scores:
            return None, None
        
        # Apply user preference learning
        adjusted_scores = self._apply_user_preferences(request.user_id, provider_scores)
        
        # Select best option
        best_provider_name = max(adjusted_scores, key=lambda k: adjusted_scores[k]["score"])
        best_option = adjusted_scores[best_provider_name]
        
        logger.info(f"🧠 Selected: {best_provider_name}/{best_option['model']} (score: {best_option['score']:.1f})")
        
        return best_provider_name, best_option["model"]
    
    async def _score_provider(self, provider_name: str, provider: ModelProvider, 
                            request: TaskRequest) -> Tuple[Optional[str], float]:
        """Score a provider's suitability for the task"""
        
        best_model = None
        best_score = -float('inf')
        
        for model_name, model_config in provider.models.items():
            score = 0.0
            
            # Base capability scoring
            if "reasoning" in model_config:
                reasoning_score = model_config["reasoning"]
                if request.quality_requirement > 7:
                    score += reasoning_score * 2  # Premium quality needs good reasoning
                else:
                    score += reasoning_score
            
            # Speed requirements
            if "speed" in model_config:
                speed_score = model_config["speed"]
                if request.speed_requirement > 7:
                    score += speed_score * 1.5
                else:
                    score += speed_score * 0.5
            
            # Cost considerations
            cost = model_config.get("cost", 0.0)
            if request.user_initiated:
                # User-initiated: cost is less important, quality matters more
                if provider.cost_structure == "pay_per_use":
                    score += 5  # User is okay paying for OpenAI
                cost_penalty = cost * 2  # Reduced cost penalty
            else:
                # Bot-initiated: cost is very important
                cost_penalty = cost * 10
                if provider.cost_structure == "free":
                    score += 15  # Strong preference for free local models
            
            score -= cost_penalty
            
            # Multimodal requirements
            if request.multimodal_needed:
                if model_config.get("multimodal") or model_config.get("image_gen") or model_config.get("audio"):
                    score += 20
                else:
                    score -= 10  # Can't handle requirement
            
            # Creativity boost
            if request.creativity_needed and provider_name == "openai":
                score += 8  # OpenAI often provides different creative perspectives
            
            # Context length requirements
            if request.context and len(request.context) > 50000:
                required_context = len(request.context) * 2  # Safety margin
                model_context = model_config.get("context", 4000)
                if required_context > model_context:
                    score -= 20  # Cannot handle context
                else:
                    score += 5  # Adequate context
            
            # Provider-specific bonuses
            if provider_name == "claude":
                score += 3  # Slight bias toward Claude for consistency
            elif provider_name == "local":
                score += 2  # Privacy and speed bonus
            
            # Special OpenAI handling for user requests
            if provider_name == "openai":
                if request.user_initiated:
                    score += 5  # User is okay with paying
                else:
                    # Bot requests: check rate limiting
                    can_use, reason = self.openai_manager.can_make_request()
                    if not can_use and "user" not in reason.lower():  # Respect user vs bot distinction
                        score -= 50  # Heavy penalty for rate limited bot requests
            
            # Task-specific scoring
            task_lower = request.task_description.lower()
            
            # Image-related tasks
            if any(word in task_lower for word in ["image", "visual", "picture", "mockup", "ui design"]):
                if model_config.get("image_gen") or model_config.get("multimodal"):
                    score += 15
                elif provider_name != "openai":
                    score -= 10
            
            # Creative tasks
            if any(word in task_lower for word in ["creative", "brainstorm", "alternative", "different approach"]):
                if provider_name == "openai":
                    score += 10  # OpenAI often provides different perspectives
            
            # Coding tasks
            if any(word in task_lower for word in ["code", "programming", "debug", "refactor"]):
                if model_config.get("coding") or provider_name == "claude":
                    score += 8
            
            # Update best score
            if score > best_score:
                best_score = score
                best_model = model_name
        
        return best_model, best_score
    
    def _apply_user_preferences(self, user_id: str, provider_scores: Dict) -> Dict:
        """Apply learned user preferences to provider scores"""
        
        if user_id not in self.user_model_preferences:
            return provider_scores  # No preferences learned yet
        
        user_prefs = self.user_model_preferences[user_id]
        adjusted_scores = provider_scores.copy()
        
        for provider_name in adjusted_scores:
            provider_key = f"{provider_name}"
            model_key = f"{provider_name}/{adjusted_scores[provider_name]['model']}"
            
            # Apply provider-level preference
            if provider_key in user_prefs:
                pref_score = user_prefs[provider_key]["preference_score"]
                adjusted_scores[provider_name]["score"] += pref_score * 8
            
            # Apply model-level preference
            if model_key in user_prefs:
                model_pref_score = user_prefs[model_key]["preference_score"]
                adjusted_scores[provider_name]["score"] += model_pref_score * 5
        
        return adjusted_scores
    
    async def _select_model_from_provider(self, provider_name: str, request: TaskRequest) -> Optional[str]:
        """Select best model from specific provider"""
        
        provider = self.providers.get(provider_name)
        if not provider:
            return None
        
        best_model, _ = await self._score_provider(provider_name, provider, request)
        return best_model
    
    async def _execute_with_provider(self, provider_name: str, model_name: str, 
                                   request: TaskRequest) -> ExecutionResult:
        """Execute task with specific provider"""
        
        if provider_name == "openai":
            # Use OpenAI manager
            result = await self.openai_manager.make_openai_request(
                model_name, request.task_description, request.user_id, "general"
            )
            
            return ExecutionResult(
                provider_used="openai",
                model_used=model_name,
                success=result.get("success", False),
                content=result.get("content", ""),
                tokens_used=result.get("tokens_used", 0),
                cost=result.get("cost", 0.0),
                execution_time=result.get("execution_time", 0.0),
                quality_score=8.0 if result.get("success") else 0.0  # Placeholder
            )
        
        elif provider_name == "claude":
            # Simulate Claude API call (in real implementation, would call Claude API)
            await asyncio.sleep(2)  # Simulate processing
            
            model_config = self.providers["claude"].models[model_name]
            estimated_tokens = len(request.task_description.split()) * 3
            cost = estimated_tokens * (model_config["cost"] / 1000)
            
            return ExecutionResult(
                provider_used="claude",
                model_used=model_name,
                success=True,
                content=f"Claude {model_name} response (simulated): Task completed successfully",
                tokens_used=estimated_tokens,
                cost=cost,
                execution_time=2.0,
                quality_score=model_config["reasoning"]
            )
        
        elif provider_name == "local":
            # Simulate local AI execution
            await asyncio.sleep(0.5)  # Local is faster
            
            return ExecutionResult(
                provider_used="local",
                model_used=model_name,
                success=True,
                content=f"Local {model_name} response (simulated): Basic task completion",
                tokens_used=0,  # Local models don't count tokens
                cost=0.0,
                execution_time=0.5,
                quality_score=5.0  # Moderate quality
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider_name}")
    
    def learn_from_feedback(self, user_id: str, provider: str, model: str, 
                          task_category: str, satisfaction_score: float, 
                          feedback_text: str = ""):
        """Learn from user feedback to improve future selections"""
        
        if user_id not in self.user_model_preferences:
            self.user_model_preferences[user_id] = {}
        
        user_prefs = self.user_model_preferences[user_id]
        
        # Learn preferences for both provider and specific model
        provider_key = provider
        model_key = f"{provider}/{model}"
        
        # Normalize satisfaction (1-10 to -1 to 1)
        normalized_satisfaction = (satisfaction_score - 5.5) / 4.5
        
        # Update provider preference
        if provider_key not in user_prefs:
            user_prefs[provider_key] = {
                "preference_score": normalized_satisfaction,
                "usage_count": 1,
                "avg_satisfaction": satisfaction_score,
                "last_used": datetime.now()
            }
        else:
            pref = user_prefs[provider_key]
            # Exponential moving average
            pref["preference_score"] = (1 - self.learning_rate) * pref["preference_score"] + \
                                     self.learning_rate * normalized_satisfaction
            pref["avg_satisfaction"] = (1 - self.learning_rate) * pref["avg_satisfaction"] + \
                                     self.learning_rate * satisfaction_score
            pref["usage_count"] += 1
            pref["last_used"] = datetime.now()
        
        # Update model-specific preference
        if model_key not in user_prefs:
            user_prefs[model_key] = {
                "preference_score": normalized_satisfaction,
                "usage_count": 1,
                "avg_satisfaction": satisfaction_score,
                "last_used": datetime.now()
            }
        else:
            pref = user_prefs[model_key]
            pref["preference_score"] = (1 - self.learning_rate) * pref["preference_score"] + \
                                     self.learning_rate * normalized_satisfaction
            pref["avg_satisfaction"] = (1 - self.learning_rate) * pref["avg_satisfaction"] + \
                                     self.learning_rate * satisfaction_score
            pref["usage_count"] += 1
            pref["last_used"] = datetime.now()
        
        # Also update OpenAI manager if relevant
        if provider == "openai":
            self.openai_manager.learn_user_preference(
                user_id, model, task_category, satisfaction_score, feedback_text
            )
        
        logger.info(f"📚 Updated preferences: {user_id} rates {provider}/{model} {satisfaction_score}/10")
    
    def _update_cost_tracking(self, user_id: str, provider: str, result: ExecutionResult):
        """Update cost tracking per user"""
        
        if user_id not in self.user_cost_tracking:
            self.user_cost_tracking[user_id] = {
                "total_cost": 0.0,
                "provider_costs": {},
                "request_count": 0,
                "last_activity": datetime.now()
            }
        
        user_costs = self.user_cost_tracking[user_id]
        user_costs["total_cost"] += result.cost
        user_costs["request_count"] += 1
        user_costs["last_activity"] = datetime.now()
        
        if provider not in user_costs["provider_costs"]:
            user_costs["provider_costs"][provider] = {"cost": 0.0, "requests": 0}
        
        user_costs["provider_costs"][provider]["cost"] += result.cost
        user_costs["provider_costs"][provider]["requests"] += 1
    
    def _update_provider_health(self, provider: str, success: bool, response_time: float):
        """Update provider health metrics"""
        
        if provider not in self.provider_health:
            return
        
        health = self.provider_health[provider]
        alpha = 0.1  # Learning rate for health metrics
        
        # Update success rate
        if success:
            health["success_rate"] = (1 - alpha) * health["success_rate"] + alpha * 1.0
        else:
            health["success_rate"] = (1 - alpha) * health["success_rate"] + alpha * 0.0
        
        # Update response time
        health["response_time"] = (1 - alpha) * health["response_time"] + alpha * response_time
        
        # Update availability
        health["available"] = health["success_rate"] > 0.5  # Available if >50% success rate
    
    async def get_recommendation(self, task_description: str, user_id: str = "default",
                               user_initiated: bool = False) -> Dict:
        """Get provider/model recommendation without executing"""
        
        request = TaskRequest(
            user_id=user_id,
            task_description=task_description,
            user_initiated=user_initiated,
            priority=5,
            quality_requirement=7,
            speed_requirement=5
        )
        
        provider, model = await self._intelligent_provider_selection(request)
        
        if not provider or not model:
            return {"error": "No suitable provider available"}
        
        provider_info = self.providers[provider]
        model_info = provider_info.models[model]
        
        # Estimate cost
        estimated_tokens = len(task_description.split()) * 3
        estimated_cost = estimated_tokens * (model_info.get("cost", 0.0) / 1000)
        
        return {
            "recommended_provider": provider,
            "recommended_model": model,
            "provider_info": {
                "name": provider_info.name,
                "cost_structure": provider_info.cost_structure,
                "strengths": provider_info.strengths
            },
            "model_info": model_info,
            "estimated_cost": estimated_cost,
            "reasoning": f"Selected based on task requirements and user preferences"
        }
    
    def get_user_analytics(self, user_id: str) -> Dict:
        """Get analytics for specific user"""
        
        if user_id not in self.user_cost_tracking:
            return {"message": "No activity found for user"}
        
        user_costs = self.user_cost_tracking[user_id]
        user_prefs = self.user_model_preferences.get(user_id, {})
        
        # Analyze user's execution history
        user_executions = [e for e in self.execution_history if e["user_id"] == user_id]
        
        provider_usage = {}
        for execution in user_executions:
            provider = execution["provider"]
            if provider not in provider_usage:
                provider_usage[provider] = {"count": 0, "avg_quality": 0}
            provider_usage[provider]["count"] += 1
            provider_usage[provider]["avg_quality"] += execution["result"].quality_score
        
        # Calculate averages
        for provider in provider_usage:
            if provider_usage[provider]["count"] > 0:
                provider_usage[provider]["avg_quality"] /= provider_usage[provider]["count"]
        
        return {
            "user_id": user_id,
            "total_requests": user_costs["request_count"],
            "total_cost": user_costs["total_cost"],
            "cost_breakdown": user_costs["provider_costs"],
            "provider_usage": provider_usage,
            "learned_preferences": user_prefs,
            "insights": self._generate_user_insights(user_id, user_executions, user_prefs)
        }
    
    def _generate_user_insights(self, user_id: str, executions: List, preferences: Dict) -> List[str]:
        """Generate insights about user's AI usage patterns"""
        
        insights = []
        
        if not executions:
            return ["No usage history available"]
        
        # Cost insights
        total_cost = sum(e["result"].cost for e in executions)
        if total_cost > 10.0:
            insights.append(f"High API usage: ${total_cost:.2f} total spend")
        elif total_cost < 1.0:
            insights.append("Cost-efficient AI usage with mostly free/cheap models")
        
        # Provider preferences
        provider_usage = {}
        for exec in executions:
            provider = exec["provider"]
            provider_usage[provider] = provider_usage.get(provider, 0) + 1
        
        if provider_usage:
            most_used = max(provider_usage, key=provider_usage.get)
            insights.append(f"Most frequently uses {most_used}")
        
        # User vs bot initiated
        user_initiated = len([e for e in executions if e["user_initiated"]])
        bot_initiated = len(executions) - user_initiated
        
        if user_initiated > bot_initiated:
            insights.append("Actively uses AI directly (not just automated)")
        else:
            insights.append("Primarily benefits from automated AI assistance")
        
        # Quality preferences
        if preferences:
            high_rated_models = [k for k, v in preferences.items() if v.get("avg_satisfaction", 5) > 7.5]
            if high_rated_models:
                insights.append(f"Highly satisfied with: {', '.join(high_rated_models[:3])}")
        
        return insights
    
    def get_system_analytics(self) -> Dict:
        """Get system-wide analytics"""
        
        total_executions = len(self.execution_history)
        if total_executions == 0:
            return {"message": "No execution history"}
        
        # Provider usage statistics
        provider_stats = {}
        total_cost = 0.0
        
        for execution in self.execution_history:
            provider = execution["provider"]
            result = execution["result"]
            
            if provider not in provider_stats:
                provider_stats[provider] = {
                    "count": 0,
                    "total_cost": 0.0,
                    "avg_quality": 0.0,
                    "success_rate": 0.0
                }
            
            stats = provider_stats[provider]
            stats["count"] += 1
            stats["total_cost"] += result.cost
            stats["avg_quality"] += result.quality_score
            if result.success:
                stats["success_rate"] += 1
            
            total_cost += result.cost
        
        # Calculate averages
        for provider in provider_stats:
            stats = provider_stats[provider]
            if stats["count"] > 0:
                stats["avg_quality"] /= stats["count"]
                stats["success_rate"] /= stats["count"]
        
        # User vs bot usage
        user_initiated = len([e for e in self.execution_history if e["user_initiated"]])
        bot_initiated = total_executions - user_initiated
        
        return {
            "total_executions": total_executions,
            "total_cost": total_cost,
            "provider_statistics": provider_stats,
            "user_vs_bot": {
                "user_initiated": user_initiated,
                "bot_initiated": bot_initiated,
                "user_percentage": (user_initiated / total_executions) * 100
            },
            "provider_health": self.provider_health,
            "total_users": len(self.user_cost_tracking),
            "learning_insights": [
                "System learns user preferences for better model selection",
                "OpenAI usage intelligently managed with user vs bot distinction",
                "Cost optimization through provider selection",
                "Quality tracking enables continuous improvement"
            ]
        }

# Test the unified orchestrator
async def main():
    """Test unified model orchestrator"""
    
    orchestrator = UnifiedModelOrchestrator()
    
    print("🎭 Unified Model Orchestrator Test")
    print("===================================")
    
    # Test different scenarios
    test_requests = [
        TaskRequest(
            user_id="user_1",
            task_description="Create a mockup image for our fitness app dashboard",
            user_initiated=True,
            multimodal_needed=True,
            quality_requirement=8
        ),
        TaskRequest(
            user_id="user_1", 
            task_description="Fix indentation in Python function",
            user_initiated=False,  # Bot-initiated
            speed_requirement=9,
            quality_requirement=5
        ),
        TaskRequest(
            user_id="user_2",
            task_description="I'm stuck on this architecture problem, need creative alternatives",
            user_initiated=True,
            creativity_needed=True,
            quality_requirement=9
        ),
        TaskRequest(
            user_id="user_1",
            task_description="Simple code formatting task",
            user_initiated=False,
            speed_requirement=10,
            quality_requirement=4
        )
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\n🎯 Test {i}: {request.task_description}")
        print(f"👤 User: {request.user_id}, Direct request: {request.user_initiated}")
        
        # Get recommendation
        recommendation = await orchestrator.get_recommendation(
            request.task_description, request.user_id, request.user_initiated
        )
        print(f"💡 Recommended: {recommendation.get('recommended_provider')}/{recommendation.get('recommended_model')}")
        print(f"💰 Est. cost: ${recommendation.get('estimated_cost', 0):.4f}")
        
        # Execute task
        result = await orchestrator.execute_task(request)
        print(f"✅ Executed: {result.provider_used}/{result.model_used}")
        print(f"📊 Success: {result.success}, Quality: {result.quality_score:.1f}, Cost: ${result.cost:.4f}")
        
        # Simulate user feedback
        satisfaction = 8.5 if result.success else 3.0
        orchestrator.learn_from_feedback(
            request.user_id, result.provider_used, result.model_used,
            "general", satisfaction
        )
        print(f"📚 Learned from feedback: {satisfaction}/10")
        print("-" * 60)
    
    # Show analytics
    print(f"\n📈 User Analytics:")
    user_analytics = orchestrator.get_user_analytics("user_1")
    print(json.dumps(user_analytics, indent=2, default=str))
    
    print(f"\n🌍 System Analytics:")
    system_analytics = orchestrator.get_system_analytics()
    print(json.dumps(system_analytics, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())