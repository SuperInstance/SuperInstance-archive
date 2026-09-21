"""
AI Cost Estimation System
Provides accurate cost estimates before AI operations with optimization suggestions
"""

import asyncio
import aiohttp
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.ai_operations import (
    AIOperation, CostEstimate, AIOperationType, AIProvider, 
    ComputeOptimization, UsageAnalytics
)
from ...config.settings import settings, AI_OPERATION_COSTS, COMPUTE_OPTIMIZATION_RULES

logger = logging.getLogger(__name__)

class CostEstimator:
    """Comprehensive AI operation cost estimation with optimization recommendations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cost_models = AI_OPERATION_COSTS
        self.buffer_percentage = settings.cost_estimation.cost_estimation_buffer
        self.min_cost = settings.cost_estimation.min_operation_cost
        
        # Real-time pricing data (would be updated from external APIs)
        self._pricing_cache = {}
        self._last_pricing_update = None
    
    async def estimate_comprehensive_cost(
        self,
        operation_type: AIOperationType,
        input_params: Dict[str, Any],
        user_id: str,
        provider_preference: Optional[AIProvider] = None
    ) -> Dict[str, Any]:
        """Comprehensive cost estimation with multiple provider options"""
        
        # Get cost estimates for all compatible providers
        provider_estimates = {}
        
        if operation_type == AIOperationType.TEXT_GENERATION:
            provider_estimates = await self._estimate_text_generation_all_providers(input_params)
        elif operation_type == AIOperationType.IMAGE_GENERATION:
            provider_estimates = await self._estimate_image_generation_all_providers(input_params)
        elif operation_type == AIOperationType.VOICE_SYNTHESIS:
            provider_estimates = await self._estimate_voice_synthesis_all_providers(input_params)
        elif operation_type == AIOperationType.VIDEO_GENERATION:
            provider_estimates = await self._estimate_video_generation_all_providers(input_params)
        elif operation_type == AIOperationType.MODEL_TRAINING:
            provider_estimates = await self._estimate_training_all_providers(input_params)
        
        # Apply optimization rules
        optimization_analysis = await self._analyze_optimization_opportunities(
            operation_type, input_params, provider_estimates, user_id
        )
        
        # Get user's historical accuracy
        estimation_accuracy = await self._get_user_estimation_accuracy(user_id, operation_type)
        
        # Calculate final recommendations
        recommended_provider = self._select_recommended_provider(
            provider_estimates, optimization_analysis, provider_preference
        )
        
        return {
            "operation_type": operation_type.value,
            "provider_estimates": provider_estimates,
            "recommended_provider": {
                "provider": recommended_provider["provider"].value,
                "estimated_cost_cc": float(recommended_provider["cost_cc"]),
                "estimated_time_minutes": float(recommended_provider["time_minutes"]),
                "confidence_score": float(recommended_provider["confidence"]),
                "optimization_reason": recommended_provider["reason"]
            },
            "optimization_analysis": optimization_analysis,
            "cost_range": {
                "min_cost_cc": float(min(est["cost_cc"] for est in provider_estimates.values())),
                "max_cost_cc": float(max(est["cost_cc"] for est in provider_estimates.values())),
                "potential_savings_cc": float(optimization_analysis.get("potential_savings_cc", 0))
            },
            "estimation_metadata": {
                "accuracy_percentage": float(estimation_accuracy),
                "buffer_applied": float(self.buffer_percentage * 100),
                "estimated_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _estimate_text_generation_all_providers(self, params: Dict) -> Dict[str, Dict]:
        """Estimate text generation costs for all providers"""
        
        estimates = {}
        
        # Extract parameters
        messages = params.get("messages", [])
        max_tokens = params.get("max_tokens", 1000)
        model = params.get("model", "auto")
        
        # Estimate token count
        input_tokens = self._estimate_input_tokens(messages)
        total_tokens = input_tokens + max_tokens
        
        # OpenAI models
        if model in ["gpt-4", "auto"] and settings.llm.openai_api_key:
            gpt4_cost = self.cost_models["text_generation"]["gpt_4"]["cost_per_1k_tokens"]
            estimates["openai_gpt4"] = {
                "provider": AIProvider.OPENAI,
                "model": "gpt-4",
                "cost_cc": (gpt4_cost * total_tokens / 1000) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("2.0"),  # Typical response time
                "confidence": Decimal("0.95"),
                "availability": await self._check_provider_availability(AIProvider.OPENAI)
            }
        
        if model in ["gpt-3.5-turbo", "auto"] and settings.llm.openai_api_key:
            gpt35_cost = self.cost_models["text_generation"]["gpt_35_turbo"]["cost_per_1k_tokens"]
            estimates["openai_gpt35"] = {
                "provider": AIProvider.OPENAI,
                "model": "gpt-3.5-turbo",
                "cost_cc": (gpt35_cost * total_tokens / 1000) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("0.5"),
                "confidence": Decimal("0.95"),
                "availability": await self._check_provider_availability(AIProvider.OPENAI)
            }
        
        # Anthropic models
        if settings.llm.anthropic_api_key:
            claude_opus_cost = self.cost_models["text_generation"]["claude_opus"]["cost_per_1k_tokens"]
            estimates["anthropic_opus"] = {
                "provider": AIProvider.ANTHROPIC,
                "model": "claude-3-opus",
                "cost_cc": (claude_opus_cost * total_tokens / 1000) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("3.0"),
                "confidence": Decimal("0.90"),
                "availability": await self._check_provider_availability(AIProvider.ANTHROPIC)
            }
            
            claude_sonnet_cost = self.cost_models["text_generation"]["claude_sonnet"]["cost_per_1k_tokens"]
            estimates["anthropic_sonnet"] = {
                "provider": AIProvider.ANTHROPIC,
                "model": "claude-3-sonnet",
                "cost_cc": (claude_sonnet_cost * total_tokens / 1000) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("1.5"),
                "confidence": Decimal("0.90"),
                "availability": await self._check_provider_availability(AIProvider.ANTHROPIC)
            }
        
        # Local LLM
        if settings.llm.enable_local_llm:
            local_cost = self.cost_models["text_generation"]["local_llm"]["cost_per_1k_tokens"]
            estimates["local_llm"] = {
                "provider": AIProvider.LOCAL,
                "model": "local-llama",
                "cost_cc": (local_cost * total_tokens / 1000) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("5.0"),  # Slower but much cheaper
                "confidence": Decimal("0.75"),  # Lower confidence due to hardware variability
                "availability": await self._check_local_gpu_availability()
            }
        
        # Apply buffer to all estimates
        for estimate in estimates.values():
            estimate["cost_cc"] *= (1 + self.buffer_percentage)
            estimate["cost_cc"] = max(estimate["cost_cc"], self.min_cost / settings.compute_credits.cc_to_usd_rate)
        
        return estimates
    
    async def _estimate_image_generation_all_providers(self, params: Dict) -> Dict[str, Dict]:
        """Estimate image generation costs for all providers"""
        
        estimates = {}
        
        num_images = params.get("num_images", 1)
        resolution = params.get("resolution", "1024x1024")
        
        # Calculate resolution multiplier for cost adjustment
        base_pixels = 1024 * 1024
        actual_pixels = self._parse_resolution_pixels(resolution)
        resolution_multiplier = actual_pixels / base_pixels
        
        # DALL-E
        if settings.image_generation.openai_api_key:
            dalle_cost = self.cost_models["image_generation"]["dalle_3"]["cost_per_image"]
            estimates["dalle_3"] = {
                "provider": AIProvider.OPENAI,
                "model": "dall-e-3",
                "cost_cc": (dalle_cost * num_images * resolution_multiplier) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("1.0") * num_images,
                "confidence": Decimal("0.98"),
                "availability": await self._check_provider_availability(AIProvider.OPENAI)
            }
        
        # Stability AI
        if settings.image_generation.stability_api_key:
            stability_cost = self.cost_models["image_generation"]["stable_diffusion_cloud"]["cost_per_image"]
            estimates["stability_ai"] = {
                "provider": AIProvider.STABILITY_AI,
                "model": "stable-diffusion-xl",
                "cost_cc": (stability_cost * num_images * resolution_multiplier) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("0.5") * num_images,
                "confidence": Decimal("0.90"),
                "availability": await self._check_provider_availability(AIProvider.STABILITY_AI)
            }
        
        # Midjourney
        if settings.image_generation.midjourney_token:
            midjourney_cost = self.cost_models["image_generation"]["midjourney"]["cost_per_image"]
            estimates["midjourney"] = {
                "provider": AIProvider.MIDJOURNEY,
                "model": "midjourney-v6",
                "cost_cc": (midjourney_cost * num_images) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("2.0") * num_images,  # Midjourney is slower
                "confidence": Decimal("0.85"),  # Less predictable timing
                "availability": await self._check_provider_availability(AIProvider.MIDJOURNEY)
            }
        
        # Local Stable Diffusion
        if settings.image_generation.enable_local_sd:
            local_cost = self.cost_models["image_generation"]["stable_diffusion_local"]["cost_per_image"]
            estimates["local_sd"] = {
                "provider": AIProvider.LOCAL,
                "model": "stable-diffusion-local",
                "cost_cc": (local_cost * num_images * resolution_multiplier) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal("0.3") * num_images,  # Fast with good GPU
                "confidence": Decimal("0.80"),
                "availability": await self._check_local_gpu_availability()
            }
        
        # Apply buffer
        for estimate in estimates.values():
            estimate["cost_cc"] *= (1 + self.buffer_percentage)
            estimate["cost_cc"] = max(estimate["cost_cc"], self.min_cost / settings.compute_credits.cc_to_usd_rate)
        
        return estimates
    
    async def _estimate_voice_synthesis_all_providers(self, params: Dict) -> Dict[str, Dict]:
        """Estimate voice synthesis costs for all providers"""
        
        estimates = {}
        
        text = params.get("text", "")
        character_count = len(text)
        voice_clone = params.get("voice_clone", False)
        
        # ElevenLabs
        if settings.voice.elevenlabs_api_key:
            elevenlabs_cost = self.cost_models["voice_synthesis"]["elevenlabs"]["cost_per_character"]
            cost_multiplier = 2.0 if voice_clone else 1.0  # Voice cloning costs more
            
            estimates["elevenlabs"] = {
                "provider": AIProvider.ELEVENLABS,
                "model": "eleven-multilingual-v2",
                "cost_cc": (elevenlabs_cost * character_count * cost_multiplier) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(character_count / 500)),  # ~500 chars per minute
                "confidence": Decimal("0.95"),
                "availability": await self._check_provider_availability(AIProvider.ELEVENLABS)
            }
        
        # OpenAI TTS
        if settings.llm.openai_api_key:
            openai_tts_cost = self.cost_models["voice_synthesis"]["openai_tts"]["cost_per_character"]
            estimates["openai_tts"] = {
                "provider": AIProvider.OPENAI,
                "model": "tts-1",
                "cost_cc": (openai_tts_cost * character_count) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(character_count / 600)),
                "confidence": Decimal("0.90"),
                "availability": await self._check_provider_availability(AIProvider.OPENAI)
            }
        
        # Local TTS
        if settings.voice.enable_local_tts:
            local_tts_cost = self.cost_models["voice_synthesis"]["local_tts"]["cost_per_character"]
            estimates["local_tts"] = {
                "provider": AIProvider.LOCAL,
                "model": "tortoise-tts",
                "cost_cc": (local_tts_cost * character_count) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(character_count / 200)),  # Slower but free
                "confidence": Decimal("0.70"),
                "availability": await self._check_local_gpu_availability()
            }
        
        # Apply buffer
        for estimate in estimates.values():
            estimate["cost_cc"] *= (1 + self.buffer_percentage)
            estimate["cost_cc"] = max(estimate["cost_cc"], self.min_cost / settings.compute_credits.cc_to_usd_rate)
        
        return estimates
    
    async def _estimate_video_generation_all_providers(self, params: Dict) -> Dict[str, Dict]:
        """Estimate video generation costs for all providers"""
        
        estimates = {}
        
        duration_seconds = params.get("duration_seconds", 5)
        resolution = params.get("resolution", "1024x576")
        fps = params.get("fps", 24)
        
        # RunwayML
        if settings.video.runway_api_key:
            runway_cost = self.cost_models["video_generation"]["runway_ml"]["cost_per_second"]
            estimates["runway_ml"] = {
                "provider": AIProvider.RUNWAY_ML,
                "model": "gen-2",
                "cost_cc": (runway_cost * duration_seconds) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(duration_seconds * 2)),  # ~2 minutes per second
                "confidence": Decimal("0.85"),
                "availability": await self._check_provider_availability(AIProvider.RUNWAY_ML)
            }
        
        # Local Video Generation
        if settings.video.enable_local_video:
            local_cost = self.cost_models["video_generation"]["local_video"]["cost_per_second"]
            estimates["local_video"] = {
                "provider": AIProvider.LOCAL,
                "model": "stable-video-diffusion",
                "cost_cc": (local_cost * duration_seconds) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(duration_seconds * 0.5)),  # Much faster locally
                "confidence": Decimal("0.75"),
                "availability": await self._check_local_gpu_availability()
            }
        
        # Apply buffer
        for estimate in estimates.values():
            estimate["cost_cc"] *= (1 + self.buffer_percentage)
            estimate["cost_cc"] = max(estimate["cost_cc"], self.min_cost / settings.compute_credits.cc_to_usd_rate)
        
        return estimates
    
    async def _estimate_training_all_providers(self, params: Dict) -> Dict[str, Dict]:
        """Estimate model training costs"""
        
        estimates = {}
        
        training_type = params.get("training_type", "lora")
        estimated_hours = params.get("estimated_hours", 4)
        dataset_size_mb = params.get("dataset_size_mb", 100)
        
        # LoRA Training
        if training_type == "lora":
            lora_cost = self.cost_models["training"]["lora_training"]["cost_per_hour"]
            estimates["lora_training"] = {
                "provider": AIProvider.LOCAL,  # Usually done locally or on rented compute
                "model": "lora-adapter",
                "cost_cc": (lora_cost * estimated_hours) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(estimated_hours * 60)),
                "confidence": Decimal("0.80"),
                "availability": await self._check_local_gpu_availability()
            }
        
        # Full Fine-tuning
        elif training_type == "full_fine_tune":
            full_cost = self.cost_models["training"]["full_fine_tuning"]["cost_per_hour"]
            estimates["full_fine_tune"] = {
                "provider": AIProvider.CLOUD,
                "model": "custom-model",
                "cost_cc": (full_cost * estimated_hours) / settings.compute_credits.cc_to_usd_rate,
                "time_minutes": Decimal(str(estimated_hours * 60)),
                "confidence": Decimal("0.85"),
                "availability": True  # Cloud resources are generally available
            }
        
        # Add storage costs
        storage_cost = self.cost_models["training"]["model_storage"]["cost_per_gb_month"]
        storage_gb = dataset_size_mb / 1000 * 2  # Account for model output size
        monthly_storage_cost = storage_cost * storage_gb
        
        for estimate in estimates.values():
            estimate["storage_cost_cc_monthly"] = (monthly_storage_cost) / settings.compute_credits.cc_to_usd_rate
            estimate["cost_cc"] *= (1 + self.buffer_percentage)
        
        return estimates
    
    async def _analyze_optimization_opportunities(
        self,
        operation_type: AIOperationType,
        params: Dict,
        provider_estimates: Dict,
        user_id: str
    ) -> Dict[str, Any]:
        """Analyze optimization opportunities and provide recommendations"""
        
        optimization = {
            "local_vs_cloud": {},
            "batch_opportunities": {},
            "caching_potential": {},
            "cost_savings": {},
            "performance_trade_offs": {}
        }
        
        # Local vs Cloud Analysis
        local_estimates = {k: v for k, v in provider_estimates.items() if v["provider"] == AIProvider.LOCAL}
        cloud_estimates = {k: v for k, v in provider_estimates.items() if v["provider"] != AIProvider.LOCAL}
        
        if local_estimates and cloud_estimates:
            cheapest_local = min(local_estimates.values(), key=lambda x: x["cost_cc"])
            cheapest_cloud = min(cloud_estimates.values(), key=lambda x: x["cost_cc"])
            
            cost_difference = cheapest_cloud["cost_cc"] - cheapest_local["cost_cc"]
            time_difference = cheapest_local["time_minutes"] - cheapest_cloud["time_minutes"]
            
            optimization["local_vs_cloud"] = {
                "local_cheaper": cost_difference > 0,
                "cost_savings_cc": float(abs(cost_difference)),
                "time_difference_minutes": float(time_difference),
                "recommendation": "local" if cost_difference > Decimal("0.10") else "cloud"
            }
        
        # Batch Opportunities
        if operation_type in [AIOperationType.IMAGE_GENERATION, AIOperationType.VOICE_SYNTHESIS]:
            num_items = params.get("num_images", params.get("batch_size", 1))
            if num_items == 1:
                optimization["batch_opportunities"] = {
                    "recommended": True,
                    "potential_discount": "15-30%",
                    "minimum_batch_size": 5,
                    "reason": "Batch processing typically offers significant cost savings"
                }
        
        # Caching Potential
        cache_hit_rate = await self._get_cache_hit_rate(user_id, operation_type)
        optimization["caching_potential"] = {
            "current_hit_rate": float(cache_hit_rate),
            "potential_savings_cc": float(cache_hit_rate * min(est["cost_cc"] for est in provider_estimates.values())),
            "recommendation": "high" if cache_hit_rate > 0.3 else "medium"
        }
        
        # Historical Performance Analysis
        user_history = await self._get_user_operation_history(user_id, operation_type)
        if user_history:
            optimization["performance_trade_offs"] = {
                "user_prefers_speed": user_history["avg_priority"] > 2,
                "user_prefers_cost": user_history["avg_cost_sensitivity"] > 0.7,
                "typical_usage_pattern": user_history["usage_pattern"]
            }
        
        return optimization
    
    def _select_recommended_provider(
        self,
        provider_estimates: Dict,
        optimization_analysis: Dict,
        preference: Optional[AIProvider]
    ) -> Dict[str, Any]:
        """Select the optimal provider based on estimates and analysis"""
        
        if preference and any(est["provider"] == preference for est in provider_estimates.values()):
            # Use preferred provider if specified and available
            preferred_estimate = next(est for est in provider_estimates.values() if est["provider"] == preference)
            return {
                "provider": preference,
                "cost_cc": preferred_estimate["cost_cc"],
                "time_minutes": preferred_estimate["time_minutes"],
                "confidence": preferred_estimate["confidence"],
                "reason": "User preference"
            }
        
        # Filter only available providers
        available_estimates = {k: v for k, v in provider_estimates.items() if v["availability"]}
        
        if not available_estimates:
            raise Exception("No providers are currently available")
        
        # Score each provider based on multiple factors
        scored_providers = []
        
        for name, estimate in available_estimates.items():
            # Cost score (lower is better, normalized 0-1)
            min_cost = min(est["cost_cc"] for est in available_estimates.values())
            max_cost = max(est["cost_cc"] for est in available_estimates.values())
            cost_score = 1 - ((estimate["cost_cc"] - min_cost) / (max_cost - min_cost)) if max_cost > min_cost else 1
            
            # Time score (lower is better, normalized 0-1)
            min_time = min(est["time_minutes"] for est in available_estimates.values())
            max_time = max(est["time_minutes"] for est in available_estimates.values())
            time_score = 1 - ((estimate["time_minutes"] - min_time) / (max_time - min_time)) if max_time > min_time else 1
            
            # Confidence score (higher is better)
            confidence_score = float(estimate["confidence"])
            
            # Weighted overall score
            overall_score = (cost_score * 0.4 + time_score * 0.3 + confidence_score * 0.3)
            
            scored_providers.append({
                "name": name,
                "estimate": estimate,
                "score": overall_score,
                "cost_score": cost_score,
                "time_score": time_score,
                "confidence_score": confidence_score
            })
        
        # Select best provider
        best_provider = max(scored_providers, key=lambda x: x["score"])
        
        return {
            "provider": best_provider["estimate"]["provider"],
            "cost_cc": best_provider["estimate"]["cost_cc"],
            "time_minutes": best_provider["estimate"]["time_minutes"],
            "confidence": Decimal(str(best_provider["score"])),
            "reason": f"Optimal balance of cost ({best_provider['cost_score']:.2f}), speed ({best_provider['time_score']:.2f}), and reliability ({best_provider['confidence_score']:.2f})"
        }
    
    # Utility methods
    def _estimate_input_tokens(self, messages: List[Dict]) -> int:
        """Estimate token count for input messages"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return int(total_chars * 0.25)  # Rough estimation: ~4 chars per token
    
    def _parse_resolution_pixels(self, resolution: str) -> int:
        """Parse resolution string to pixel count"""
        try:
            width, height = resolution.split("x")
            return int(width) * int(height)
        except:
            return 1024 * 1024  # Default
    
    async def _check_provider_availability(self, provider: AIProvider) -> bool:
        """Check if a provider is currently available"""
        # In a real implementation, this would check API status, rate limits, etc.
        # For now, we'll simulate based on configuration
        if provider == AIProvider.OPENAI:
            return bool(settings.llm.openai_api_key)
        elif provider == AIProvider.ANTHROPIC:
            return bool(settings.llm.anthropic_api_key)
        elif provider == AIProvider.STABILITY_AI:
            return bool(settings.image_generation.stability_api_key)
        elif provider == AIProvider.ELEVENLABS:
            return bool(settings.voice.elevenlabs_api_key)
        elif provider == AIProvider.RUNWAY_ML:
            return bool(settings.video.runway_api_key)
        return True
    
    async def _check_local_gpu_availability(self) -> bool:
        """Check if local GPU is available for processing"""
        # This would check actual GPU availability and memory
        # For now, simulate based on settings
        return (settings.compute_optimizer.detect_gpu and 
                settings.compute_optimizer.min_gpu_memory_gb >= 8)
    
    async def _get_user_estimation_accuracy(self, user_id: str, operation_type: AIOperationType) -> Decimal:
        """Get historical estimation accuracy for user"""
        
        accuracy_data = (
            self.db.query(func.avg(CostEstimate.accuracy_percentage))
            .join(AIOperation, CostEstimate.operation_id == AIOperation.id)
            .filter(
                and_(
                    AIOperation.user_id == user_id,
                    AIOperation.operation_type == operation_type,
                    CostEstimate.accuracy_percentage.isnot(None)
                )
            )
            .scalar()
        )
        
        return Decimal(str(accuracy_data or 85.0))  # Default 85% accuracy
    
    async def _get_cache_hit_rate(self, user_id: str, operation_type: AIOperationType) -> Decimal:
        """Get cache hit rate for user and operation type"""
        
        # This would query actual cache statistics
        # For now, simulate based on operation type
        base_rates = {
            AIOperationType.IMAGE_GENERATION: 0.35,
            AIOperationType.TEXT_GENERATION: 0.15,
            AIOperationType.VOICE_SYNTHESIS: 0.45,
            AIOperationType.VIDEO_GENERATION: 0.20
        }
        
        return Decimal(str(base_rates.get(operation_type, 0.25)))
    
    async def _get_user_operation_history(self, user_id: str, operation_type: AIOperationType) -> Optional[Dict]:
        """Get user's operation history for pattern analysis"""
        
        # Query recent operations
        recent_ops = (
            self.db.query(AIOperation)
            .filter(
                and_(
                    AIOperation.user_id == user_id,
                    AIOperation.operation_type == operation_type,
                    AIOperation.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .limit(100)
            .all()
        )
        
        if not recent_ops:
            return None
        
        # Analyze patterns
        priorities = [op.queue_priority.value for op in recent_ops if op.queue_priority]
        avg_priority = sum(1 if p == "low" else 2 if p == "standard" else 3 if p == "high" else 4 for p in priorities) / len(priorities) if priorities else 2
        
        costs = [float(op.actual_cost_cc or 0) for op in recent_ops]
        avg_cost = sum(costs) / len(costs) if costs else 0
        
        return {
            "total_operations": len(recent_ops),
            "avg_priority": avg_priority,
            "avg_cost_sensitivity": 0.7 if avg_cost < 0.10 else 0.5,
            "usage_pattern": "frequent" if len(recent_ops) > 20 else "occasional"
        }
    
    async def store_cost_estimate(
        self,
        operation_id: str,
        estimate_data: Dict[str, Any]
    ) -> CostEstimate:
        """Store cost estimate in database for tracking accuracy"""
        
        recommended = estimate_data["recommended_provider"]
        
        cost_estimate = CostEstimate(
            operation_id=operation_id,
            base_cost_cc=recommended["estimated_cost_cc"],
            compute_cost_cc=recommended["estimated_cost_cc"] * Decimal("0.8"),  # Assume 80% is compute
            storage_cost_cc=recommended["estimated_cost_cc"] * Decimal("0.2"),  # 20% is storage
            total_estimated_cost_cc=recommended["estimated_cost_cc"],
            recommended_provider=AIProvider(recommended["provider"]),
            optimization_reason=recommended["optimization_reason"]
        )
        
        if estimate_data.get("optimization_analysis", {}).get("local_vs_cloud"):
            opt = estimate_data["optimization_analysis"]["local_vs_cloud"]
            if "local_cost_cc" in opt:
                cost_estimate.local_cost_cc = Decimal(str(opt.get("local_cost_cc", 0)))
            if "cloud_cost_cc" in opt:
                cost_estimate.cloud_cost_cc = Decimal(str(opt.get("cloud_cost_cc", 0)))
        
        self.db.add(cost_estimate)
        self.db.commit()
        
        return cost_estimate
    
    async def update_estimate_accuracy(
        self,
        operation_id: str,
        actual_cost_cc: Decimal
    ) -> None:
        """Update estimation accuracy after operation completion"""
        
        cost_estimate = (
            self.db.query(CostEstimate)
            .filter(CostEstimate.operation_id == operation_id)
            .first()
        )
        
        if cost_estimate and actual_cost_cc > 0:
            estimated = cost_estimate.total_estimated_cost_cc
            accuracy = min(100, (1 - abs(actual_cost_cc - estimated) / estimated) * 100)
            cost_estimate.accuracy_percentage = Decimal(str(accuracy))
            self.db.commit()
    
    async def get_user_cost_analytics(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get cost analytics for user"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Query user operations
        operations = (
            self.db.query(AIOperation)
            .filter(
                and_(
                    AIOperation.user_id == user_id,
                    AIOperation.created_at >= start_date
                )
            )
            .all()
        )
        
        if not operations:
            return {"message": "No operations found for this period"}
        
        # Analyze costs by operation type
        cost_by_type = {}
        for op in operations:
            op_type = op.operation_type.value
            if op_type not in cost_by_type:
                cost_by_type[op_type] = {"count": 0, "total_cost_cc": 0, "estimated_cost_cc": 0}
            
            cost_by_type[op_type]["count"] += 1
            cost_by_type[op_type]["total_cost_cc"] += float(op.actual_cost_cc or 0)
            cost_by_type[op_type]["estimated_cost_cc"] += float(op.estimated_cost_cc or 0)
        
        # Calculate total costs and savings
        total_actual = sum(float(op.actual_cost_cc or 0) for op in operations)
        total_estimated = sum(float(op.estimated_cost_cc or 0) for op in operations)
        total_saved = sum(float(op.cost_saved_cc or 0) for op in operations)
        
        # Estimation accuracy
        accuracy_ops = [op for op in operations if op.actual_cost_cc and op.estimated_cost_cc]
        avg_accuracy = 0
        if accuracy_ops:
            accuracies = []
            for op in accuracy_ops:
                estimated = float(op.estimated_cost_cc)
                actual = float(op.actual_cost_cc)
                if estimated > 0:
                    accuracy = (1 - abs(actual - estimated) / estimated) * 100
                    accuracies.append(min(100, max(0, accuracy)))
            avg_accuracy = sum(accuracies) / len(accuracies) if accuracies else 0
        
        return {
            "user_id": user_id,
            "analysis_period_days": days,
            "summary": {
                "total_operations": len(operations),
                "total_cost_cc": total_actual,
                "total_estimated_cc": total_estimated,
                "total_saved_cc": total_saved,
                "average_accuracy_percentage": round(avg_accuracy, 2)
            },
            "cost_by_operation_type": cost_by_type,
            "recommendations": await self._generate_user_recommendations(user_id, operations)
        }
    
    async def _generate_user_recommendations(self, user_id: str, operations: List) -> List[str]:
        """Generate personalized cost optimization recommendations"""
        
        recommendations = []
        
        # Analyze usage patterns
        image_ops = [op for op in operations if op.operation_type == AIOperationType.IMAGE_GENERATION]
        text_ops = [op for op in operations if op.operation_type == AIOperationType.TEXT_GENERATION]
        
        # Batch processing recommendation
        if len(image_ops) > 10:
            single_image_ops = [op for op in image_ops if op.input_data.get("num_images", 1) == 1]
            if len(single_image_ops) > 5:
                recommendations.append(
                    "Consider batch processing your image generations - you could save 15-30% by generating multiple images in single requests"
                )
        
        # Local processing recommendation
        local_ops = [op for op in operations if op.provider == AIProvider.LOCAL]
        cloud_ops = [op for op in operations if op.provider != AIProvider.LOCAL]
        
        if len(cloud_ops) > len(local_ops) * 2:
            potential_local_savings = sum(float(op.actual_cost_cc or 0) for op in cloud_ops) * 0.8
            if potential_local_savings > 5.0:  # If savings > 5 CC
                recommendations.append(
                    f"Setting up local AI processing could save you approximately {potential_local_savings:.1f} CC per month"
                )
        
        # Caching recommendation
        cached_ops = [op for op in operations if op.cost_saved_cc and op.cost_saved_cc > 0]
        if len(cached_ops) < len(operations) * 0.2:  # Low cache hit rate
            recommendations.append(
                "Your cache hit rate is low - consider reusing similar prompts or parameters to benefit from result caching"
            )
        
        return recommendations