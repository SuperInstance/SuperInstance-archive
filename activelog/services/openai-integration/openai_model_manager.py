#!/usr/bin/env python3
"""
OpenAI Model Manager
Manages OpenAI API integration with intelligent usage patterns and rate limiting
"""

import asyncio
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class OpenAIModel:
    """Represents an OpenAI model"""
    name: str
    model_id: str
    capabilities: List[str]
    cost_per_1k_tokens: float
    context_length: int
    multimodal: bool
    strengths: List[str]
    use_cases: List[str]
    speed_tier: int  # 1-10, higher is faster

@dataclass
class UsageWindow:
    """Tracks API usage within time windows"""
    start_time: datetime
    end_time: datetime
    request_count: int
    total_tokens: int
    total_cost: float
    models_used: List[str]

@dataclass
class ModelPreference:
    """User preference data for specific models"""
    user_id: str
    model_name: str
    task_category: str
    preference_score: float  # -1 to 1, higher means preferred
    usage_count: int
    avg_satisfaction: float  # 1-10 user satisfaction
    last_used: datetime

class OpenAIModelManager:
    """Manages OpenAI models with intelligent selection and rate limiting"""
    
    def __init__(self, api_key: Optional[str] = None, rate_limit_window: int = 600):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.rate_limit_window = rate_limit_window  # 10 minutes in seconds
        self.models = self._initialize_models()
        
        # Usage tracking
        self.usage_history: List[UsageWindow] = []
        self.last_request_time: Optional[datetime] = None
        
        # User preference learning
        self.user_preferences: Dict[str, List[ModelPreference]] = {}
        
        # Model performance tracking
        self.model_performance: Dict[str, Dict] = {}
        
        # Rate limiting state
        self.rate_limit_enforced = True
        self.emergency_override = False
    
    def _initialize_models(self) -> Dict[str, OpenAIModel]:
        """Initialize OpenAI model configurations"""
        return {
            "gpt-4-turbo": OpenAIModel(
                name="GPT-4 Turbo",
                model_id="gpt-4-turbo",
                capabilities=["reasoning", "coding", "analysis", "creative_writing"],
                cost_per_1k_tokens=0.01,  # Input tokens
                context_length=128000,
                multimodal=False,
                strengths=["complex_reasoning", "code_quality", "detailed_analysis"],
                use_cases=["complex_problems", "code_review", "strategic_planning"],
                speed_tier=7
            ),
            "gpt-4o": OpenAIModel(
                name="GPT-4o",
                model_id="gpt-4o",
                capabilities=["vision", "reasoning", "multimodal", "real_time"],
                cost_per_1k_tokens=0.005,
                context_length=128000,
                multimodal=True,
                strengths=["vision_analysis", "multimodal_tasks", "real_time_processing"],
                use_cases=["image_analysis", "ui_feedback", "visual_debugging"],
                speed_tier=8
            ),
            "gpt-4o-mini": OpenAIModel(
                name="GPT-4o Mini",
                model_id="gpt-4o-mini",
                capabilities=["fast_processing", "vision", "basic_reasoning"],
                cost_per_1k_tokens=0.00015,  # Very cheap
                context_length=128000,
                multimodal=True,
                strengths=["cost_efficiency", "speed", "vision_capability"],
                use_cases=["quick_analysis", "image_generation_prompts", "simple_vision_tasks"],
                speed_tier=9
            ),
            "gpt-3.5-turbo": OpenAIModel(
                name="GPT-3.5 Turbo",
                model_id="gpt-3.5-turbo",
                capabilities=["fast_processing", "general_tasks", "coding"],
                cost_per_1k_tokens=0.0005,
                context_length=16385,
                multimodal=False,
                strengths=["speed", "cost_efficiency", "general_purpose"],
                use_cases=["simple_tasks", "quick_responses", "basic_coding"],
                speed_tier=10
            ),
            "dall-e-3": OpenAIModel(
                name="DALL-E 3",
                model_id="dall-e-3",
                capabilities=["image_generation", "creative_visual", "high_quality"],
                cost_per_1k_tokens=0.04,  # Per image, not tokens
                context_length=4000,
                multimodal=True,
                strengths=["image_quality", "creative_generation", "prompt_adherence"],
                use_cases=["ui_mockups", "visual_concepts", "creative_assets"],
                speed_tier=5
            ),
            "whisper-1": OpenAIModel(
                name="Whisper",
                model_id="whisper-1",
                capabilities=["speech_to_text", "audio_processing", "multilingual"],
                cost_per_1k_tokens=0.006,  # Per minute
                context_length=0,  # Audio model
                multimodal=True,
                strengths=["audio_transcription", "multilingual_support", "accuracy"],
                use_cases=["meeting_transcription", "voice_commands", "accessibility"],
                speed_tier=7
            )
        }
    
    def can_make_request(self, user_initiated: bool = False) -> Tuple[bool, str]:
        """Check if we can make a request within rate limits"""
        if self.emergency_override:
            return True, "Emergency override active"
        
        if not self.rate_limit_enforced:
            return True, "Rate limiting disabled"
        
        # USER-initiated requests are NOT rate limited (user pays as they go)
        if user_initiated:
            return True, "User-initiated request allowed (pay-as-you-go)"
        
        now = datetime.now()
        
        # Only apply rate limits to BOT-initiated requests (automated background tasks)
        if self.last_request_time:
            time_since_last = (now - self.last_request_time).total_seconds()
            if time_since_last < self.rate_limit_window:
                remaining_time = self.rate_limit_window - time_since_last
                return False, f"Bot rate limit: {remaining_time:.0f}s remaining until next automated OpenAI request"
        
        return True, "Bot request allowed"
    
    async def intelligent_model_selection(self, task_description: str, user_id: str = "default",
                                        context: Optional[str] = None, 
                                        claude_failed: bool = False, user_initiated: bool = False) -> Optional[str]:
        """Intelligently select OpenAI model based on task and user preferences"""
        
        # Check rate limits first (pass user_initiated flag)
        can_request, reason = self.can_make_request(user_initiated)
        if not can_request:
            logger.info(f"🚫 OpenAI request blocked: {reason}")
            return None
        
        # Analyze task requirements
        task_analysis = self._analyze_task_for_openai(task_description, context, claude_failed)
        
        # Get user preferences for this task category
        user_prefs = self._get_user_preferences(user_id, task_analysis["category"])
        
        # Score models based on task + user preferences
        model_scores = {}
        
        for model_name, model in self.models.items():
            score = 0.0
            
            # Base capability matching
            capability_matches = len(set(task_analysis["required_capabilities"]) & set(model.capabilities))
            score += capability_matches * 10
            
            # Use case alignment
            use_case_matches = len(set(task_analysis["use_cases"]) & set(model.use_cases))
            score += use_case_matches * 8
            
            # Cost consideration (lower cost = higher score for non-critical tasks)
            if not task_analysis["high_priority"]:
                cost_score = max(0, (1 - model.cost_per_1k_tokens / 0.04) * 5)  # Normalize against DALL-E
                score += cost_score
            
            # Speed requirement
            if task_analysis["speed_required"]:
                score += model.speed_tier * 2
            
            # Multimodal requirement
            if task_analysis["multimodal_needed"] and model.multimodal:
                score += 15
            elif task_analysis["multimodal_needed"] and not model.multimodal:
                score -= 20
            
            # User preference boost
            user_pref_score = user_prefs.get(model_name, 0)
            score += user_pref_score * 5
            
            # Claude failure boost (try different approach)
            if claude_failed:
                if "creative" in task_analysis["category"] and "creative" in model.strengths:
                    score += 10
                if "vision" in model.capabilities and "analysis" in task_description.lower():
                    score += 8
            
            # Performance history
            if model_name in self.model_performance:
                perf = self.model_performance[model_name]
                score += perf.get("avg_satisfaction", 5) - 5  # Adjust based on past performance
            
            model_scores[model_name] = score
        
        # Select best model
        if not model_scores:
            return None
        
        best_model = max(model_scores, key=model_scores.get)
        best_score = model_scores[best_model]
        
        # Only use OpenAI if it's significantly better than threshold
        if best_score < 15:  # Minimum threshold
            logger.info(f"🤔 No OpenAI model scores high enough (best: {best_score:.1f})")
            return None
        
        logger.info(f"🎯 Selected OpenAI model: {best_model} (score: {best_score:.1f})")
        return best_model
    
    def _analyze_task_for_openai(self, task_description: str, context: Optional[str], 
                               claude_failed: bool) -> Dict:
        """Analyze task to determine OpenAI model requirements"""
        
        task_lower = task_description.lower()
        context_lower = (context or "").lower()
        full_text = f"{task_lower} {context_lower}"
        
        analysis = {
            "category": "general",
            "required_capabilities": [],
            "use_cases": [],
            "high_priority": False,
            "speed_required": False,
            "multimodal_needed": False
        }
        
        # Determine category and capabilities
        if any(word in full_text for word in ["image", "visual", "ui", "mockup", "design", "screenshot"]):
            analysis["category"] = "visual"
            analysis["required_capabilities"].extend(["vision", "image_generation"])
            analysis["use_cases"].extend(["image_analysis", "ui_feedback", "visual_concepts"])
            analysis["multimodal_needed"] = True
        
        elif any(word in full_text for word in ["creative", "brainstorm", "innovative", "alternative", "different"]):
            analysis["category"] = "creative"
            analysis["required_capabilities"].extend(["creative_writing", "reasoning"])
            analysis["use_cases"].extend(["creative_assets", "strategic_planning"])
        
        elif any(word in full_text for word in ["stuck", "failed", "different approach", "alternative"]):
            analysis["category"] = "problem_solving"
            analysis["required_capabilities"].extend(["reasoning", "analysis"])
            analysis["use_cases"].extend(["complex_problems", "code_review"])
            analysis["high_priority"] = True
        
        elif any(word in full_text for word in ["audio", "speech", "transcribe", "voice"]):
            analysis["category"] = "audio"
            analysis["required_capabilities"].extend(["speech_to_text", "audio_processing"])
            analysis["use_cases"].extend(["meeting_transcription", "voice_commands"])
            analysis["multimodal_needed"] = True
        
        elif any(word in full_text for word in ["quick", "fast", "urgent", "immediate"]):
            analysis["speed_required"] = True
        
        # Special considerations for Claude failures
        if claude_failed:
            analysis["high_priority"] = True
            analysis["required_capabilities"].append("different_perspective")
        
        return analysis
    
    def _get_user_preferences(self, user_id: str, category: str) -> Dict[str, float]:
        """Get user preferences for models in a specific category"""
        
        if user_id not in self.user_preferences:
            return {}
        
        prefs = {}
        for preference in self.user_preferences[user_id]:
            if preference.task_category == category or preference.task_category == "general":
                prefs[preference.model_name] = preference.preference_score
        
        return prefs
    
    async def make_openai_request(self, model_name: str, prompt: str, user_id: str = "default",
                                task_category: str = "general", user_initiated: bool = False) -> Dict:
        """Make request to OpenAI API with tracking"""
        
        if not self.api_key:
            raise ValueError("OpenAI API key not configured")
        
        # Check rate limits (pass user_initiated flag)
        can_request, reason = self.can_make_request(user_initiated)
        if not can_request:
            return {"error": reason, "rate_limited": True}
        
        model = self.models.get(model_name)
        if not model:
            return {"error": f"Unknown model: {model_name}"}
        
        try:
            start_time = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                # Prepare request based on model type
                if model_name == "dall-e-3":
                    payload = {
                        "model": model.model_id,
                        "prompt": prompt,
                        "n": 1,
                        "size": "1024x1024"
                    }
                    url = "https://api.openai.com/v1/images/generations"
                
                elif model_name == "whisper-1":
                    # For Whisper, we'd need audio file - this is a placeholder
                    return {"error": "Audio file required for Whisper", "model_type": "audio"}
                
                else:
                    # Text completion models
                    payload = {
                        "model": model.model_id,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": min(4096, model.context_length // 4),
                        "temperature": 0.7
                    }
                    url = "https://api.openai.com/v1/chat/completions"
                
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract response content
                        if model_name == "dall-e-3":
                            content = result["data"][0]["url"] if result.get("data") else "Image generation failed"
                            tokens_used = 1  # Placeholder for image
                        else:
                            content = result["choices"][0]["message"]["content"] if result.get("choices") else "No response"
                            tokens_used = result.get("usage", {}).get("total_tokens", 0)
                        
                        execution_time = (datetime.now() - start_time).total_seconds()
                        estimated_cost = tokens_used * (model.cost_per_1k_tokens / 1000)
                        
                        # Update usage tracking
                        self.last_request_time = datetime.now()
                        self._track_usage(model_name, tokens_used, estimated_cost)
                        
                        # Track performance
                        self._track_model_performance(model_name, user_id, task_category, 
                                                    execution_time, True)
                        
                        logger.info(f"✅ OpenAI {model_name} request successful - "
                                   f"Tokens: {tokens_used}, Cost: ${estimated_cost:.4f}")
                        
                        return {
                            "success": True,
                            "model_used": model_name,
                            "content": content,
                            "tokens_used": tokens_used,
                            "cost": estimated_cost,
                            "execution_time": execution_time
                        }
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ OpenAI API error {response.status}: {error_text}")
                        
                        self._track_model_performance(model_name, user_id, task_category, 0, False)
                        
                        return {
                            "success": False,
                            "error": f"API error {response.status}: {error_text}",
                            "model_used": model_name
                        }
        
        except Exception as e:
            logger.error(f"❌ OpenAI request exception: {e}")
            self._track_model_performance(model_name, user_id, task_category, 0, False)
            
            return {
                "success": False,
                "error": str(e),
                "model_used": model_name
            }
    
    def _track_usage(self, model_name: str, tokens: int, cost: float):
        """Track API usage for rate limiting and analytics"""
        
        now = datetime.now()
        
        # Create usage window
        usage_window = UsageWindow(
            start_time=now,
            end_time=now,
            request_count=1,
            total_tokens=tokens,
            total_cost=cost,
            models_used=[model_name]
        )
        
        self.usage_history.append(usage_window)
        
        # Clean up old usage data (keep last 24 hours)
        cutoff_time = now - timedelta(hours=24)
        self.usage_history = [u for u in self.usage_history if u.start_time >= cutoff_time]
    
    def _track_model_performance(self, model_name: str, user_id: str, category: str,
                                execution_time: float, success: bool):
        """Track model performance for learning"""
        
        if model_name not in self.model_performance:
            self.model_performance[model_name] = {
                "total_requests": 0,
                "successful_requests": 0,
                "total_execution_time": 0.0,
                "avg_execution_time": 0.0,
                "success_rate": 0.0,
                "avg_satisfaction": 5.0  # Neutral starting point
            }
        
        perf = self.model_performance[model_name]
        perf["total_requests"] += 1
        
        if success:
            perf["successful_requests"] += 1
            perf["total_execution_time"] += execution_time
        
        perf["success_rate"] = perf["successful_requests"] / perf["total_requests"]
        if perf["successful_requests"] > 0:
            perf["avg_execution_time"] = perf["total_execution_time"] / perf["successful_requests"]
    
    def learn_user_preference(self, user_id: str, model_name: str, task_category: str,
                            satisfaction_score: float, feedback_text: str = ""):
        """Learn from user feedback to improve model selection"""
        
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = []
        
        # Find existing preference or create new one
        existing_pref = None
        for pref in self.user_preferences[user_id]:
            if pref.model_name == model_name and pref.task_category == task_category:
                existing_pref = pref
                break
        
        if existing_pref:
            # Update existing preference with exponential moving average
            alpha = 0.2  # Learning rate
            existing_pref.avg_satisfaction = (1 - alpha) * existing_pref.avg_satisfaction + alpha * satisfaction_score
            existing_pref.usage_count += 1
            existing_pref.last_used = datetime.now()
            
            # Update preference score (-1 to 1)
            normalized_satisfaction = (satisfaction_score - 5) / 5  # Convert 1-10 to -1 to 1
            existing_pref.preference_score = (1 - alpha) * existing_pref.preference_score + alpha * normalized_satisfaction
        
        else:
            # Create new preference
            normalized_satisfaction = (satisfaction_score - 5) / 5
            new_pref = ModelPreference(
                user_id=user_id,
                model_name=model_name,
                task_category=task_category,
                preference_score=normalized_satisfaction,
                usage_count=1,
                avg_satisfaction=satisfaction_score,
                last_used=datetime.now()
            )
            self.user_preferences[user_id].append(new_pref)
        
        # Update global model performance
        if model_name in self.model_performance:
            perf = self.model_performance[model_name]
            alpha = 0.1
            perf["avg_satisfaction"] = (1 - alpha) * perf["avg_satisfaction"] + alpha * satisfaction_score
        
        logger.info(f"📚 Learned user preference: {user_id} rates {model_name} {satisfaction_score}/10 for {task_category}")
    
    def get_usage_analytics(self) -> Dict:
        """Get usage analytics and insights"""
        
        if not self.usage_history:
            return {"message": "No usage data available"}
        
        # Aggregate usage data
        total_requests = len(self.usage_history)
        total_cost = sum(u.total_cost for u in self.usage_history)
        total_tokens = sum(u.total_tokens for u in self.usage_history)
        
        # Model usage breakdown
        model_usage = {}
        for usage in self.usage_history:
            for model in usage.models_used:
                model_usage[model] = model_usage.get(model, 0) + 1
        
        # Recent activity (last 24 hours)
        now = datetime.now()
        recent_usage = [u for u in self.usage_history if (now - u.start_time).total_seconds() < 86400]
        
        return {
            "total_requests": total_requests,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "average_cost_per_request": total_cost / max(total_requests, 1),
            "model_usage_distribution": model_usage,
            "recent_24h_requests": len(recent_usage),
            "rate_limit_status": {
                "enforced": self.rate_limit_enforced,
                "last_request": self.last_request_time.isoformat() if self.last_request_time else None,
                "next_allowed": (self.last_request_time + timedelta(seconds=self.rate_limit_window)).isoformat() if self.last_request_time else "now"
            },
            "model_performance": self.model_performance
        }
    
    def get_user_preference_insights(self, user_id: str = None) -> Dict:
        """Get user preference insights"""
        
        if user_id and user_id in self.user_preferences:
            user_prefs = self.user_preferences[user_id]
            
            # Analyze preferences
            preferred_models = [p for p in user_prefs if p.preference_score > 0.2]
            disliked_models = [p for p in user_prefs if p.preference_score < -0.2]
            
            category_preferences = {}
            for pref in user_prefs:
                if pref.task_category not in category_preferences:
                    category_preferences[pref.task_category] = []
                category_preferences[pref.task_category].append({
                    "model": pref.model_name,
                    "score": pref.preference_score,
                    "satisfaction": pref.avg_satisfaction,
                    "usage": pref.usage_count
                })
            
            return {
                "user_id": user_id,
                "total_preferences": len(user_prefs),
                "preferred_models": [(p.model_name, p.preference_score) for p in preferred_models],
                "disliked_models": [(p.model_name, p.preference_score) for p in disliked_models],
                "category_preferences": category_preferences
            }
        
        else:
            # Global insights
            all_users = list(self.user_preferences.keys())
            
            # Most popular models across users
            model_popularity = {}
            for user_prefs in self.user_preferences.values():
                for pref in user_prefs:
                    if pref.model_name not in model_popularity:
                        model_popularity[pref.model_name] = {"total_score": 0, "user_count": 0}
                    model_popularity[pref.model_name]["total_score"] += pref.preference_score
                    model_popularity[pref.model_name]["user_count"] += 1
            
            # Calculate average preferences
            for model in model_popularity:
                stats = model_popularity[model]
                stats["avg_preference"] = stats["total_score"] / stats["user_count"]
            
            return {
                "total_users": len(all_users),
                "model_popularity": model_popularity,
                "insights": [
                    "OpenAI models used strategically for specific scenarios",
                    "User preferences being learned and applied",
                    "Rate limiting prevents overuse and cost control"
                ]
            }
    
    def set_emergency_override(self, enabled: bool, reason: str = ""):
        """Enable/disable emergency override for rate limiting"""
        self.emergency_override = enabled
        if enabled:
            logger.warning(f"🚨 OpenAI emergency override ENABLED: {reason}")
        else:
            logger.info("✅ OpenAI emergency override disabled")
    
    def set_rate_limiting(self, enabled: bool):
        """Enable/disable rate limiting"""
        self.rate_limit_enforced = enabled
        logger.info(f"🚦 OpenAI rate limiting {'enabled' if enabled else 'disabled'}")

# Test the OpenAI manager
async def main():
    """Test OpenAI model manager"""
    
    # Note: This requires actual OpenAI API key to test fully
    manager = OpenAIModelManager()
    
    print("🤖 OpenAI Model Manager Test")
    print("=============================")
    
    # Test model selection
    test_tasks = [
        "Create a mockup image for a fitness tracking dashboard",
        "I'm stuck on this architecture problem and Claude couldn't help",
        "Quick analysis of this code snippet",
        "Generate creative alternatives for our UI design"
    ]
    
    for task in test_tasks:
        print(f"\n🎯 Task: {task}")
        
        selected_model = await manager.intelligent_model_selection(
            task, user_id="test_user", claude_failed=("stuck" in task)
        )
        
        if selected_model:
            print(f"✅ Selected: {selected_model}")
            
            # Simulate making request (commented out to avoid API costs)
            # result = await manager.make_openai_request(selected_model, task, "test_user")
            # print(f"📊 Result: {result.get('success', False)}")
            
            # Simulate user feedback
            satisfaction = 8.5  # High satisfaction
            manager.learn_user_preference("test_user", selected_model, "visual", satisfaction)
            
        else:
            print("❌ No OpenAI model recommended")
    
    # Get analytics
    analytics = manager.get_usage_analytics()
    preferences = manager.get_user_preference_insights("test_user")
    
    print(f"\n📈 Analytics:")
    print(json.dumps(analytics, indent=2, default=str))
    
    print(f"\n👤 User Preferences:")
    print(json.dumps(preferences, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())