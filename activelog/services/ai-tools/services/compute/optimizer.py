"""
Local vs Cloud Compute Optimizer
Intelligently routes AI operations based on cost, performance, and resource availability
"""

import asyncio
import psutil
import subprocess
import GPUtil
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.ai_operations import (
    AIOperation, ComputeOptimization, AIOperationType, AIProvider, 
    ComputeLocation, OperationStatus
)
from ...config.settings import settings, COMPUTE_OPTIMIZATION_RULES

logger = logging.getLogger(__name__)

class ComputeOptimizer:
    """Intelligent compute optimization and routing system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.settings = settings.compute_optimizer
        
        # System capabilities cache
        self._system_info = None
        self._last_system_check = None
        self._gpu_info = None
        
        # Performance history
        self._performance_cache = {}
        
        # Cost multipliers
        self.local_cost_multiplier = self.settings.local_cost_multiplier
        self.cloud_premium_threshold = self.settings.cloud_premium_threshold
    
    async def select_optimal_provider(
        self,
        operation_type: AIOperationType,
        operation_params: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> AIProvider:
        """Select optimal provider based on operation requirements and system capabilities"""
        
        # Get system capabilities
        system_info = await self._get_system_capabilities()
        
        # Analyze operation requirements
        requirements = await self._analyze_operation_requirements(operation_type, operation_params)
        
        # Get cost estimates for local vs cloud
        cost_analysis = await self._analyze_cost_implications(
            operation_type, requirements, system_info
        )
        
        # Get performance predictions
        performance_analysis = await self._predict_performance(
            operation_type, requirements, system_info
        )
        
        # Make optimization decision
        decision = await self._make_optimization_decision(
            operation_type,
            requirements,
            cost_analysis,
            performance_analysis,
            user_preferences
        )
        
        # Store optimization record
        await self._store_optimization_decision(
            operation_type,
            requirements,
            cost_analysis,
            performance_analysis,
            decision
        )
        
        return decision["provider"]
    
    async def _get_system_capabilities(self) -> Dict[str, Any]:
        """Get current system capabilities and resource availability"""
        
        # Check if we need to refresh system info
        now = datetime.utcnow()
        if (self._last_system_check is None or 
            (now - self._last_system_check).seconds > 60):  # Refresh every minute
            
            self._system_info = await self._detect_system_capabilities()
            self._last_system_check = now
        
        return self._system_info
    
    async def _detect_system_capabilities(self) -> Dict[str, Any]:
        """Detect current system hardware and software capabilities"""
        
        capabilities = {
            "cpu": {
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True),
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
                "usage_percent": psutil.cpu_percent(interval=1),
                "available": True
            },
            "memory": {
                "total_gb": psutil.virtual_memory().total / (1024**3),
                "available_gb": psutil.virtual_memory().available / (1024**3),
                "usage_percent": psutil.virtual_memory().percent,
                "available": psutil.virtual_memory().available > (2 * 1024**3)  # At least 2GB free
            },
            "gpu": await self._detect_gpu_capabilities(),
            "storage": {
                "total_gb": psutil.disk_usage('/').total / (1024**3),
                "free_gb": psutil.disk_usage('/').free / (1024**3),
                "usage_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
            },
            "network": {
                "connected": await self._check_internet_connectivity(),
                "speed_mbps": await self._estimate_network_speed()
            }
        }
        
        # Overall system load assessment
        capabilities["system_load"] = self._calculate_system_load(capabilities)
        
        return capabilities
    
    async def _detect_gpu_capabilities(self) -> Dict[str, Any]:
        """Detect GPU capabilities for local AI processing"""
        
        gpu_info = {
            "available": False,
            "count": 0,
            "total_memory_gb": 0,
            "free_memory_gb": 0,
            "gpus": []
        }
        
        try:
            # Try to get GPU information using GPUtil
            gpus = GPUtil.getGPUs()
            
            if gpus:
                gpu_info["available"] = True
                gpu_info["count"] = len(gpus)
                
                for gpu in gpus:
                    gpu_data = {
                        "id": gpu.id,
                        "name": gpu.name,
                        "memory_total_gb": gpu.memoryTotal / 1024,
                        "memory_free_gb": gpu.memoryFree / 1024,
                        "memory_used_gb": gpu.memoryUsed / 1024,
                        "load_percent": gpu.load * 100,
                        "temperature_c": gpu.temperature,
                        "suitable_for_ai": gpu.memoryTotal >= (self.settings.min_gpu_memory_gb * 1024)
                    }
                    gpu_info["gpus"].append(gpu_data)
                    gpu_info["total_memory_gb"] += gpu_data["memory_total_gb"]
                    gpu_info["free_memory_gb"] += gpu_data["memory_free_gb"]
        
        except Exception as e:
            logger.debug(f"GPU detection failed: {str(e)}")
            
            # Fallback: try nvidia-smi
            try:
                result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.free', '--format=csv,nounits,noheader'], 
                                     capture_output=True, text=True, timeout=5)
                
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for i, line in enumerate(lines):
                        parts = line.split(', ')
                        if len(parts) >= 3:
                            name = parts[0]
                            total_mb = int(parts[1])
                            free_mb = int(parts[2])
                            
                            gpu_data = {
                                "id": i,
                                "name": name,
                                "memory_total_gb": total_mb / 1024,
                                "memory_free_gb": free_mb / 1024,
                                "memory_used_gb": (total_mb - free_mb) / 1024,
                                "suitable_for_ai": total_mb >= (self.settings.min_gpu_memory_gb * 1024)
                            }
                            gpu_info["gpus"].append(gpu_data)
                            gpu_info["total_memory_gb"] += gpu_data["memory_total_gb"]
                            gpu_info["free_memory_gb"] += gpu_data["memory_free_gb"]
                    
                    if gpu_info["gpus"]:
                        gpu_info["available"] = True
                        gpu_info["count"] = len(gpu_info["gpus"])
            
            except Exception as e2:
                logger.debug(f"nvidia-smi fallback failed: {str(e2)}")
        
        return gpu_info
    
    async def _check_internet_connectivity(self) -> bool:
        """Check internet connectivity for cloud services"""
        
        try:
            # Simple connectivity check
            process = await asyncio.create_subprocess_exec(
                'ping', '-c', '1', '-W', '3', '8.8.8.8',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await process.wait()
            return process.returncode == 0
        except:
            return False
    
    async def _estimate_network_speed(self) -> float:
        """Estimate network speed for cloud API calls"""
        
        # This is a simplified estimation
        # In production, you might want to periodically test actual API response times
        return 100.0  # Default assumption: 100 Mbps
    
    def _calculate_system_load(self, capabilities: Dict) -> float:
        """Calculate overall system load score (0-1, lower is better)"""
        
        cpu_load = capabilities["cpu"]["usage_percent"] / 100
        memory_load = capabilities["memory"]["usage_percent"] / 100
        
        # GPU load (if available)
        gpu_load = 0.0
        if capabilities["gpu"]["available"] and capabilities["gpu"]["gpus"]:
            gpu_loads = [gpu.get("load_percent", 0) / 100 for gpu in capabilities["gpu"]["gpus"]]
            gpu_load = sum(gpu_loads) / len(gpu_loads)
        
        # Weighted average
        system_load = (cpu_load * 0.3 + memory_load * 0.4 + gpu_load * 0.3)
        return system_load
    
    async def _analyze_operation_requirements(
        self,
        operation_type: AIOperationType,
        operation_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze operation requirements for resource planning"""
        
        requirements = {
            "estimated_duration_minutes": 1.0,
            "memory_gb_required": 2.0,
            "gpu_memory_gb_required": 0.0,
            "cpu_intensive": False,
            "gpu_required": False,
            "network_bandwidth_required": "low",
            "storage_gb_required": 0.1,
            "parallelizable": False
        }
        
        if operation_type == AIOperationType.IMAGE_GENERATION:
            num_images = operation_params.get("num_images", 1)
            resolution = operation_params.get("resolution", "1024x1024")
            
            # Parse resolution
            width, height = resolution.split("x") if "x" in resolution else ("1024", "1024")
            pixels = int(width) * int(height)
            
            requirements.update({
                "estimated_duration_minutes": num_images * (pixels / (1024 * 1024)) * 0.5,  # Scale with resolution
                "memory_gb_required": max(4.0, num_images * 0.5),
                "gpu_memory_gb_required": max(6.0, (pixels / (1024 * 1024)) * 2),
                "gpu_required": True,
                "storage_gb_required": num_images * 0.01,  # ~10MB per image
                "parallelizable": num_images > 1
            })
        
        elif operation_type == AIOperationType.TEXT_GENERATION:
            messages = operation_params.get("messages", [])
            max_tokens = operation_params.get("max_tokens", 1000)
            
            # Estimate context length
            context_length = sum(len(msg.get("content", "")) for msg in messages) + max_tokens
            
            requirements.update({
                "estimated_duration_minutes": max(0.1, context_length / 10000),  # Rough estimate
                "memory_gb_required": max(2.0, context_length / 50000),  # Scale with context
                "gpu_memory_gb_required": max(4.0, context_length / 20000),
                "gpu_required": context_length > 4000,  # Larger contexts benefit from GPU
                "cpu_intensive": context_length > 10000,
                "network_bandwidth_required": "medium" if context_length > 5000 else "low"
            })
        
        elif operation_type == AIOperationType.VOICE_SYNTHESIS:
            text = operation_params.get("text", "")
            character_count = len(text)
            voice_clone = operation_params.get("voice_clone", False)
            
            requirements.update({
                "estimated_duration_minutes": max(0.1, character_count / 1000),  # ~1000 chars per minute
                "memory_gb_required": max(2.0, character_count / 10000),
                "gpu_memory_gb_required": 4.0 if voice_clone else 2.0,
                "gpu_required": voice_clone or character_count > 5000,
                "storage_gb_required": character_count / 100000  # Audio files
            })
        
        elif operation_type == AIOperationType.VIDEO_GENERATION:
            duration_seconds = operation_params.get("duration_seconds", 5)
            resolution = operation_params.get("resolution", "1024x576")
            fps = operation_params.get("fps", 24)
            
            frame_count = duration_seconds * fps
            
            requirements.update({
                "estimated_duration_minutes": duration_seconds * 2,  # 2 minutes per second of video
                "memory_gb_required": max(8.0, frame_count * 0.001),
                "gpu_memory_gb_required": max(12.0, frame_count * 0.002),
                "gpu_required": True,
                "storage_gb_required": duration_seconds * 0.1,  # ~100MB per second
                "network_bandwidth_required": "high"
            })
        
        elif operation_type == AIOperationType.MODEL_TRAINING:
            training_type = operation_params.get("training_type", "lora")
            estimated_hours = operation_params.get("estimated_hours", 4)
            
            requirements.update({
                "estimated_duration_minutes": estimated_hours * 60,
                "memory_gb_required": 16.0 if training_type == "full_fine_tune" else 8.0,
                "gpu_memory_gb_required": 24.0 if training_type == "full_fine_tune" else 12.0,
                "gpu_required": True,
                "cpu_intensive": True,
                "storage_gb_required": 10.0 if training_type == "full_fine_tune" else 2.0
            })
        
        return requirements
    
    async def _analyze_cost_implications(
        self,
        operation_type: AIOperationType,
        requirements: Dict[str, Any],
        system_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze cost implications of local vs cloud processing"""
        
        # Get base costs from settings
        from ...config.settings import AI_OPERATION_COSTS
        
        operation_costs = AI_OPERATION_COSTS.get(operation_type.value.replace("_", " "), {})
        
        # Estimate local costs
        local_cost_factors = {
            "electricity": requirements["estimated_duration_minutes"] * 0.001,  # $0.001 per minute
            "hardware_wear": requirements["gpu_memory_gb_required"] * 0.0001,  # Depreciation
            "cooling": requirements["estimated_duration_minutes"] * 0.0005  # Cooling costs
        }
        
        estimated_local_cost_usd = sum(local_cost_factors.values())
        
        # Estimate cloud costs (find cheapest cloud option)
        cloud_costs = []
        for provider, cost_data in operation_costs.items():
            if "local" not in provider:
                if "cost_per_image" in cost_data:
                    cloud_costs.append(float(cost_data["cost_per_image"]))
                elif "cost_per_1k_tokens" in cost_data:
                    # Estimate tokens
                    estimated_tokens = requirements.get("context_length", 1000)
                    cloud_costs.append(float(cost_data["cost_per_1k_tokens"]) * (estimated_tokens / 1000))
                elif "cost_per_character" in cost_data:
                    estimated_chars = requirements.get("character_count", 1000)
                    cloud_costs.append(float(cost_data["cost_per_character"]) * estimated_chars)
                elif "cost_per_second" in cost_data:
                    estimated_seconds = requirements.get("duration_seconds", 5)
                    cloud_costs.append(float(cost_data["cost_per_second"]) * estimated_seconds)
                elif "cost_per_hour" in cost_data:
                    estimated_hours = requirements["estimated_duration_minutes"] / 60
                    cloud_costs.append(float(cost_data["cost_per_hour"]) * estimated_hours)
        
        min_cloud_cost_usd = min(cloud_costs) if cloud_costs else 1.0
        
        # Cost comparison
        cost_analysis = {
            "local_cost_usd": estimated_local_cost_usd,
            "cloud_cost_usd": min_cloud_cost_usd,
            "local_cheaper": estimated_local_cost_usd < min_cloud_cost_usd,
            "cost_difference_usd": abs(min_cloud_cost_usd - estimated_local_cost_usd),
            "cost_savings_percentage": 0.0,
            "local_cost_breakdown": local_cost_factors
        }
        
        if min_cloud_cost_usd > 0:
            if estimated_local_cost_usd < min_cloud_cost_usd:
                cost_analysis["cost_savings_percentage"] = (
                    (min_cloud_cost_usd - estimated_local_cost_usd) / min_cloud_cost_usd * 100
                )
            else:
                cost_analysis["cost_savings_percentage"] = -(
                    (estimated_local_cost_usd - min_cloud_cost_usd) / min_cloud_cost_usd * 100
                )
        
        return cost_analysis
    
    async def _predict_performance(
        self,
        operation_type: AIOperationType,
        requirements: Dict[str, Any],
        system_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Predict performance characteristics for local vs cloud processing"""
        
        # Check if local processing is feasible
        local_feasible = True
        feasibility_issues = []
        
        # Check GPU requirements
        if requirements["gpu_required"]:
            if not system_info["gpu"]["available"]:
                local_feasible = False
                feasibility_issues.append("No GPU detected")
            elif system_info["gpu"]["free_memory_gb"] < requirements["gpu_memory_gb_required"]:
                local_feasible = False
                feasibility_issues.append(
                    f"Insufficient GPU memory: need {requirements['gpu_memory_gb_required']:.1f}GB, "
                    f"have {system_info['gpu']['free_memory_gb']:.1f}GB"
                )
        
        # Check RAM requirements
        if system_info["memory"]["available_gb"] < requirements["memory_gb_required"]:
            local_feasible = False
            feasibility_issues.append(
                f"Insufficient RAM: need {requirements['memory_gb_required']:.1f}GB, "
                f"have {system_info['memory']['available_gb']:.1f}GB"
            )
        
        # Check storage requirements
        if system_info["storage"]["free_gb"] < requirements["storage_gb_required"]:
            local_feasible = False
            feasibility_issues.append(
                f"Insufficient storage: need {requirements['storage_gb_required']:.1f}GB, "
                f"have {system_info['storage']['free_gb']:.1f}GB"
            )
        
        # Check network for cloud processing
        cloud_feasible = system_info["network"]["connected"]
        cloud_issues = [] if cloud_feasible else ["No internet connection"]
        
        # Estimate performance metrics
        local_performance = {
            "feasible": local_feasible,
            "issues": feasibility_issues,
            "estimated_time_minutes": requirements["estimated_duration_minutes"],
            "quality_score": 0.8,  # Local processing might be slightly lower quality
            "reliability_score": 0.9,  # High reliability, no network dependency
            "privacy_score": 1.0  # Perfect privacy
        }
        
        # Adjust local performance based on system load
        system_load = system_info["system_load"]
        if system_load > 0.8:
            local_performance["estimated_time_minutes"] *= 1.5  # Slower when system is busy
            local_performance["reliability_score"] *= 0.9
        
        cloud_performance = {
            "feasible": cloud_feasible,
            "issues": cloud_issues,
            "estimated_time_minutes": requirements["estimated_duration_minutes"] * 0.5,  # Cloud is typically faster
            "quality_score": 1.0,  # Cloud typically has best quality
            "reliability_score": 0.85,  # Network dependency reduces reliability
            "privacy_score": 0.7  # Data leaves local system
        }
        
        # Adjust cloud performance based on network speed
        if system_info["network"]["speed_mbps"] < 50:
            cloud_performance["estimated_time_minutes"] *= 1.2  # Slower upload/download
            cloud_performance["reliability_score"] *= 0.9
        
        return {
            "local": local_performance,
            "cloud": cloud_performance,
            "recommendation_factors": {
                "cost_factor": 0.4,
                "speed_factor": 0.3,
                "quality_factor": 0.2,
                "privacy_factor": 0.1
            }
        }
    
    async def _make_optimization_decision(
        self,
        operation_type: AIOperationType,
        requirements: Dict[str, Any],
        cost_analysis: Dict[str, Any],
        performance_analysis: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make final optimization decision based on all factors"""
        
        # Default weights
        weights = {
            "cost": 0.4,
            "speed": 0.3,
            "quality": 0.2,
            "privacy": 0.1
        }
        
        # Adjust weights based on user preferences
        if user_preferences:
            if user_preferences.get("cost_sensitive", False):
                weights["cost"] = 0.6
                weights["speed"] = 0.2
            if user_preferences.get("speed_critical", False):
                weights["speed"] = 0.5
                weights["cost"] = 0.2
            if user_preferences.get("privacy_required", False):
                weights["privacy"] = 0.3
                weights["cost"] = 0.3
        
        # Calculate scores for local vs cloud
        local_score = 0.0
        cloud_score = 0.0
        
        # Cost scoring (lower cost = higher score)
        if cost_analysis["local_cheaper"]:
            local_score += weights["cost"] * 1.0
            cloud_score += weights["cost"] * 0.3
        else:
            local_score += weights["cost"] * 0.3
            cloud_score += weights["cost"] * 1.0
        
        # Speed scoring (lower time = higher score)
        local_time = performance_analysis["local"]["estimated_time_minutes"]
        cloud_time = performance_analysis["cloud"]["estimated_time_minutes"]
        
        if local_time < cloud_time:
            local_score += weights["speed"] * 1.0
            cloud_score += weights["speed"] * (cloud_time / max(local_time, 0.1))
        else:
            local_score += weights["speed"] * (local_time / max(cloud_time, 0.1))
            cloud_score += weights["speed"] * 1.0
        
        # Quality scoring
        local_quality = performance_analysis["local"]["quality_score"]
        cloud_quality = performance_analysis["cloud"]["quality_score"]
        
        local_score += weights["quality"] * local_quality
        cloud_score += weights["quality"] * cloud_quality
        
        # Privacy scoring
        local_privacy = performance_analysis["local"]["privacy_score"]
        cloud_privacy = performance_analysis["cloud"]["privacy_score"]
        
        local_score += weights["privacy"] * local_privacy
        cloud_score += weights["privacy"] * cloud_privacy
        
        # Feasibility check
        if not performance_analysis["local"]["feasible"]:
            local_score = 0.0
        
        if not performance_analysis["cloud"]["feasible"]:
            cloud_score = 0.0
        
        # Make decision
        if local_score > cloud_score:
            recommended_location = ComputeLocation.LOCAL
            recommended_provider = AIProvider.LOCAL
            reason = f"Local processing recommended (score: {local_score:.2f} vs {cloud_score:.2f})"
        else:
            recommended_location = ComputeLocation.CLOUD
            # Select best cloud provider for this operation type
            recommended_provider = await self._select_best_cloud_provider(operation_type)
            reason = f"Cloud processing recommended (score: {cloud_score:.2f} vs {local_score:.2f})"
        
        return {
            "compute_location": recommended_location,
            "provider": recommended_provider,
            "local_score": local_score,
            "cloud_score": cloud_score,
            "reason": reason,
            "confidence": abs(local_score - cloud_score),  # Higher difference = higher confidence
            "factors": {
                "cost_favors": "local" if cost_analysis["local_cheaper"] else "cloud",
                "speed_favors": "local" if local_time < cloud_time else "cloud",
                "quality_favors": "local" if local_quality > cloud_quality else "cloud",
                "privacy_favors": "local" if local_privacy > cloud_privacy else "cloud"
            }
        }
    
    async def _select_best_cloud_provider(self, operation_type: AIOperationType) -> AIProvider:
        """Select the best cloud provider for a given operation type"""
        
        # This is a simplified selection - in practice you'd consider:
        # - Current API availability and rate limits
        # - Historical performance data
        # - Cost differences
        # - Feature requirements
        
        provider_preferences = {
            AIOperationType.TEXT_GENERATION: AIProvider.OPENAI,  # GPT models are excellent
            AIOperationType.IMAGE_GENERATION: AIProvider.STABILITY_AI,  # Good balance of cost/quality
            AIOperationType.VOICE_SYNTHESIS: AIProvider.ELEVENLABS,  # Best voice quality
            AIOperationType.VIDEO_GENERATION: AIProvider.RUNWAY_ML,  # Leading video AI
            AIOperationType.MODEL_TRAINING: AIProvider.REPLICATE  # Good for training jobs
        }
        
        return provider_preferences.get(operation_type, AIProvider.OPENAI)
    
    async def _store_optimization_decision(
        self,
        operation_type: AIOperationType,
        requirements: Dict[str, Any],
        cost_analysis: Dict[str, Any],
        performance_analysis: Dict[str, Any],
        decision: Dict[str, Any]
    ) -> ComputeOptimization:
        """Store optimization decision for learning and analytics"""
        
        optimization_record = ComputeOptimization(
            local_available=performance_analysis["local"]["feasible"],
            local_gpu_memory_gb=int(requirements.get("gpu_memory_gb_required", 0)),
            estimated_local_time_minutes=Decimal(str(performance_analysis["local"]["estimated_time_minutes"])),
            estimated_cloud_time_minutes=Decimal(str(performance_analysis["cloud"]["estimated_time_minutes"])),
            local_cost_cc=Decimal(str(cost_analysis["local_cost_usd"] / settings.compute_credits.cc_to_usd_rate)),
            cloud_cost_cc=Decimal(str(cost_analysis["cloud_cost_usd"] / settings.compute_credits.cc_to_usd_rate)),
            chosen_compute=decision["compute_location"],
            decision_reason=decision["reason"],
            cost_savings_cc=Decimal(str(abs(cost_analysis["cost_difference_usd"]) / settings.compute_credits.cc_to_usd_rate))
        )
        
        self.db.add(optimization_record)
        self.db.commit()
        
        return optimization_record
    
    async def update_performance_results(
        self,
        optimization_id: str,
        actual_time_minutes: float,
        performance_score: float
    ):
        """Update optimization record with actual performance results"""
        
        optimization = (
            self.db.query(ComputeOptimization)
            .filter(ComputeOptimization.id == optimization_id)
            .first()
        )
        
        if optimization:
            optimization.actual_time_minutes = Decimal(str(actual_time_minutes))
            optimization.performance_score = Decimal(str(performance_score))
            self.db.commit()
    
    async def get_optimization_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get optimization performance analytics"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        optimizations = (
            self.db.query(ComputeOptimization)
            .filter(ComputeOptimization.created_at >= start_date)
            .all()
        )
        
        if not optimizations:
            return {"message": "No optimization data available"}
        
        # Calculate statistics
        local_choices = [opt for opt in optimizations if opt.chosen_compute == ComputeLocation.LOCAL]
        cloud_choices = [opt for opt in optimizations if opt.chosen_compute == ComputeLocation.CLOUD]
        
        total_cost_saved = sum(float(opt.cost_savings_cc or 0) for opt in optimizations)
        
        # Accuracy analysis (for completed operations)
        completed_opts = [opt for opt in optimizations if opt.actual_time_minutes is not None]
        
        time_prediction_accuracy = []
        for opt in completed_opts:
            if opt.chosen_compute == ComputeLocation.LOCAL:
                predicted = float(opt.estimated_local_time_minutes)
            else:
                predicted = float(opt.estimated_cloud_time_minutes)
            
            actual = float(opt.actual_time_minutes)
            if predicted > 0:
                accuracy = max(0, 1 - abs(actual - predicted) / predicted)
                time_prediction_accuracy.append(accuracy)
        
        avg_prediction_accuracy = (
            sum(time_prediction_accuracy) / len(time_prediction_accuracy)
            if time_prediction_accuracy else 0
        )
        
        return {
            "period_days": days,
            "total_optimizations": len(optimizations),
            "local_vs_cloud": {
                "local_chosen": len(local_choices),
                "cloud_chosen": len(cloud_choices),
                "local_percentage": (len(local_choices) / len(optimizations)) * 100
            },
            "cost_savings": {
                "total_saved_cc": total_cost_saved,
                "average_saved_per_operation": total_cost_saved / len(optimizations),
                "estimated_monthly_savings": total_cost_saved * (30 / days)
            },
            "prediction_accuracy": {
                "time_predictions": f"{avg_prediction_accuracy * 100:.1f}%",
                "predictions_analyzed": len(time_prediction_accuracy)
            },
            "system_utilization": await self._get_system_utilization_stats()
        }
    
    async def _get_system_utilization_stats(self) -> Dict[str, Any]:
        """Get current system utilization statistics"""
        
        system_info = await self._get_system_capabilities()
        
        return {
            "cpu_usage": f"{system_info['cpu']['usage_percent']:.1f}%",
            "memory_usage": f"{system_info['memory']['usage_percent']:.1f}%",
            "gpu_available": system_info['gpu']['available'],
            "gpu_utilization": (
                f"{sum(gpu.get('load_percent', 0) for gpu in system_info['gpu']['gpus']) / max(len(system_info['gpu']['gpus']), 1):.1f}%"
                if system_info['gpu']['available'] else "N/A"
            ),
            "system_load_score": f"{system_info['system_load']:.2f}",
            "optimization_recommendation": (
                "System is under high load, prefer cloud processing" 
                if system_info['system_load'] > 0.8 
                else "System has available capacity for local processing"
            )
        }
    
    async def force_provider_selection(
        self,
        provider: AIProvider,
        reason: str = "Manual override"
    ) -> Dict[str, Any]:
        """Force selection of a specific provider (for testing/debugging)"""
        
        return {
            "compute_location": ComputeLocation.LOCAL if provider == AIProvider.LOCAL else ComputeLocation.CLOUD,
            "provider": provider,
            "local_score": 1.0 if provider == AIProvider.LOCAL else 0.0,
            "cloud_score": 1.0 if provider != AIProvider.LOCAL else 0.0,
            "reason": reason,
            "confidence": 1.0,
            "forced": True
        }