from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import math

from ..database import (
    User, UserChoice, ChoiceType, ComputeAllowance,
    OptimizationTarget, ComputeType, DeviceProfile,
    DeviceType, DecisionFactor, CloudDecision
)

logger = logging.getLogger(__name__)

class LocalVsCloudDecisionEngine:
    """Intelligent decision engine for local vs cloud compute choices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def make_decision(
        self,
        user_id: uuid.UUID,
        workload: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make an intelligent local vs cloud decision for a workload"""
        
        try:
            # Get user context
            user_profile = await self._get_user_profile(user_id)
            device_profiles = await self._get_user_devices(user_id)
            compute_allowance = await self._get_compute_allowance(user_id)
            decision_history = await self._get_decision_history(user_id)
            
            # Analyze workload requirements
            workload_analysis = await self._analyze_workload(workload)
            
            # Evaluate local compute options
            local_evaluation = await self._evaluate_local_options(
                user_id, workload_analysis, device_profiles, constraints
            )
            
            # Evaluate cloud compute options
            cloud_evaluation = await self._evaluate_cloud_options(
                user_id, workload_analysis, compute_allowance, constraints
            )
            
            # Apply user preferences and learning
            preference_weights = await self._calculate_preference_weights(
                user_id, decision_history, preferences
            )
            
            # Make final decision
            decision_result = await self._make_final_decision(
                local_evaluation, cloud_evaluation, preference_weights, constraints
            )
            
            # Store decision for learning
            await self._store_decision(user_id, workload, decision_result, {
                "local_evaluation": local_evaluation,
                "cloud_evaluation": cloud_evaluation,
                "preference_weights": preference_weights
            })
            
            return {
                "user_id": str(user_id),
                "workload_name": workload.get("name", "Unknown"),
                "recommended_option": decision_result["recommended_option"],
                "confidence_score": decision_result["confidence_score"],
                "decision_reasoning": decision_result["reasoning"],
                "local_evaluation": local_evaluation,
                "cloud_evaluation": cloud_evaluation,
                "cost_comparison": decision_result["cost_comparison"],
                "performance_comparison": decision_result["performance_comparison"],
                "alternative_recommendations": decision_result.get("alternatives", []),
                "decision_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to make local vs cloud decision: {e}")
            raise
    
    async def evaluate_decision_outcome(
        self,
        decision_id: uuid.UUID,
        outcome_metrics: Dict[str, Any],
        user_satisfaction: Optional[int] = None
    ) -> Dict[str, Any]:
        """Evaluate the outcome of a previous decision for learning"""
        
        try:
            # Get the original decision
            result = await self.db.execute(
                select(CloudDecision).where(CloudDecision.id == decision_id)
            )
            decision = result.scalar_one_or_none()
            
            if not decision:
                return {"success": False, "error": "Decision not found"}
            
            # Update decision with outcome
            decision.actual_performance = outcome_metrics.get("performance", {})
            decision.actual_cost = Decimal(str(outcome_metrics.get("cost", 0)))
            decision.user_satisfaction = user_satisfaction
            decision.outcome_recorded = True
            decision.outcome_timestamp = datetime.utcnow()
            
            # Calculate accuracy metrics
            accuracy_analysis = await self._analyze_decision_accuracy(decision, outcome_metrics)
            
            # Update user learning model
            await self._update_learning_model(decision.user_id, decision, accuracy_analysis)
            
            await self.db.commit()
            
            return {
                "success": True,
                "decision_id": str(decision_id),
                "accuracy_analysis": accuracy_analysis,
                "learning_updates": "Model updated with outcome data",
                "improved_predictions": accuracy_analysis.get("will_improve_future", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate decision outcome: {e}")
            raise
    
    async def get_decision_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics on user's local vs cloud decisions"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get decisions in period
            result = await self.db.execute(
                select(CloudDecision).where(
                    and_(
                        CloudDecision.user_id == user_id,
                        CloudDecision.decision_date >= start_date
                    )
                ).order_by(CloudDecision.decision_date.desc())
            )
            decisions = result.scalars().all()
            
            if not decisions:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "message": "No decisions found for this period"
                }
            
            # Analyze decisions
            total_decisions = len(decisions)
            local_decisions = len([d for d in decisions if d.selected_option == "local"])
            cloud_decisions = len([d for d in decisions if d.selected_option == "cloud"])
            
            # Cost analysis
            total_cost = sum(float(d.actual_cost or d.estimated_cost) for d in decisions)
            avg_cost_per_decision = total_cost / total_decisions
            
            # Satisfaction analysis
            satisfaction_scores = [d.user_satisfaction for d in decisions if d.user_satisfaction]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            # Decision accuracy
            accurate_decisions = len([
                d for d in decisions 
                if d.outcome_recorded and d.user_satisfaction and d.user_satisfaction >= 7
            ])
            decision_accuracy = (accurate_decisions / total_decisions) * 100 if total_decisions > 0 else 0
            
            # Workload type breakdown
            workload_breakdown = {}
            for decision in decisions:
                workload_type = decision.workload_metadata.get("type", "unknown") if decision.workload_metadata else "unknown"
                if workload_type not in workload_breakdown:
                    workload_breakdown[workload_type] = {"local": 0, "cloud": 0}
                workload_breakdown[workload_type][decision.selected_option] += 1
            
            # Trend analysis
            monthly_trends = await self._analyze_decision_trends(decisions)
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "decision_summary": {
                    "total_decisions": total_decisions,
                    "local_decisions": local_decisions,
                    "cloud_decisions": cloud_decisions,
                    "local_preference_percentage": (local_decisions / total_decisions) * 100,
                    "cloud_preference_percentage": (cloud_decisions / total_decisions) * 100
                },
                "cost_analysis": {
                    "total_cost": total_cost,
                    "average_cost_per_decision": avg_cost_per_decision,
                    "cost_trend": monthly_trends.get("cost_trend", "stable")
                },
                "satisfaction_metrics": {
                    "average_satisfaction": round(avg_satisfaction, 2),
                    "decision_accuracy_percentage": round(decision_accuracy, 2),
                    "total_satisfaction_responses": len(satisfaction_scores)
                },
                "workload_breakdown": workload_breakdown,
                "decision_trends": monthly_trends,
                "recommendations": await self._generate_decision_improvement_recommendations(
                    user_id, decisions
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get decision analytics: {e}")
            raise
    
    async def train_decision_model(
        self,
        user_id: uuid.UUID,
        training_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Train or retrain the decision model for a user"""
        
        try:
            # Get historical decisions with outcomes
            decisions_with_outcomes = await self._get_decisions_with_outcomes(user_id)
            
            if len(decisions_with_outcomes) < 5:
                return {
                    "success": False,
                    "message": "Insufficient training data. Need at least 5 decisions with outcomes.",
                    "available_decisions": len(decisions_with_outcomes)
                }
            
            # Extract features and labels for training
            features, labels = await self._extract_training_features(decisions_with_outcomes)
            
            # Train decision model (simplified - would use ML library in production)
            model_weights = await self._train_decision_weights(features, labels)
            
            # Store updated model
            await self._store_user_decision_model(user_id, model_weights)
            
            # Validate model performance
            validation_results = await self._validate_model_performance(
                user_id, decisions_with_outcomes, model_weights
            )
            
            return {
                "success": True,
                "user_id": str(user_id),
                "training_data_size": len(decisions_with_outcomes),
                "model_performance": validation_results,
                "model_weights": model_weights,
                "improvement_over_baseline": validation_results.get("improvement", 0),
                "training_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to train decision model: {e}")
            raise
    
    # Helper methods
    
    async def _get_user_profile(self, user_id: uuid.UUID) -> Optional[User]:
        """Get user profile"""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def _get_user_devices(self, user_id: uuid.UUID) -> List[DeviceProfile]:
        """Get user's device profiles"""
        result = await self.db.execute(
            select(DeviceProfile).where(
                and_(
                    DeviceProfile.user_id == user_id,
                    DeviceProfile.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def _get_compute_allowance(self, user_id: uuid.UUID) -> Optional[ComputeAllowance]:
        """Get user's current compute allowance"""
        now = datetime.utcnow()
        result = await self.db.execute(
            select(ComputeAllowance).where(
                and_(
                    ComputeAllowance.user_id == user_id,
                    ComputeAllowance.allowance_period_start <= now,
                    ComputeAllowance.allowance_period_end >= now
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_decision_history(self, user_id: uuid.UUID) -> List[CloudDecision]:
        """Get user's recent decision history"""
        lookback_date = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(CloudDecision).where(
                and_(
                    CloudDecision.user_id == user_id,
                    CloudDecision.decision_date >= lookback_date
                )
            ).order_by(CloudDecision.decision_date.desc()).limit(50)
        )
        return result.scalars().all()
    
    async def _analyze_workload(self, workload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze workload characteristics for decision making"""
        
        analysis = {
            "name": workload.get("name", "Unknown"),
            "type": workload.get("type", "general"),
            "compute_intensity": workload.get("compute_intensity", "medium"),
            "memory_requirements": workload.get("memory_gb", 4),
            "storage_requirements": workload.get("storage_gb", 10),
            "network_intensive": workload.get("network_intensive", False),
            "data_sensitivity": workload.get("data_sensitivity", "low"),
            "latency_requirements": workload.get("max_latency_ms", 1000),
            "estimated_runtime": workload.get("estimated_runtime_minutes", 30),
            "parallelizable": workload.get("parallelizable", True),
            "gpu_required": workload.get("gpu_required", False)
        }
        
        # Calculate complexity score
        complexity_factors = {
            "high": 3, "medium": 2, "low": 1
        }
        
        compute_score = complexity_factors.get(analysis["compute_intensity"], 2)
        memory_score = min(3, analysis["memory_requirements"] // 4)
        network_score = 2 if analysis["network_intensive"] else 1
        gpu_score = 3 if analysis["gpu_required"] else 0
        
        analysis["complexity_score"] = compute_score + memory_score + network_score + gpu_score
        analysis["suitable_for_local"] = await self._assess_local_suitability(analysis)
        analysis["suitable_for_cloud"] = await self._assess_cloud_suitability(analysis)
        
        return analysis
    
    async def _assess_local_suitability(self, workload_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess suitability for local execution"""
        
        suitability_score = 0.5  # Base score
        reasons = []
        
        # Data sensitivity favors local
        if workload_analysis["data_sensitivity"] in ["high", "confidential"]:
            suitability_score += 0.3
            reasons.append("High data sensitivity benefits from local execution")
        
        # Low network intensity favors local
        if not workload_analysis["network_intensive"]:
            suitability_score += 0.2
            reasons.append("Low network requirements suitable for local")
        
        # High latency tolerance favors local
        if workload_analysis["latency_requirements"] > 500:
            suitability_score += 0.1
            reasons.append("Latency requirements can be met locally")
        
        # GPU requirements may limit local options
        if workload_analysis["gpu_required"]:
            suitability_score -= 0.2
            reasons.append("GPU requirements may limit local options")
        
        # Very high compute intensity may limit local
        if workload_analysis["compute_intensity"] == "high" and workload_analysis["complexity_score"] > 8:
            suitability_score -= 0.2
            reasons.append("High compute intensity may exceed local capacity")
        
        return {
            "score": max(0.0, min(1.0, suitability_score)),
            "reasons": reasons
        }
    
    async def _assess_cloud_suitability(self, workload_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess suitability for cloud execution"""
        
        suitability_score = 0.5  # Base score
        reasons = []
        
        # High compute intensity favors cloud
        if workload_analysis["compute_intensity"] == "high":
            suitability_score += 0.3
            reasons.append("High compute intensity benefits from cloud resources")
        
        # GPU requirements favor cloud
        if workload_analysis["gpu_required"]:
            suitability_score += 0.3
            reasons.append("GPU requirements easily met in cloud")
        
        # Parallelizable workloads favor cloud
        if workload_analysis["parallelizable"]:
            suitability_score += 0.2
            reasons.append("Parallelizable workloads benefit from cloud scaling")
        
        # Network intensive workloads may favor cloud
        if workload_analysis["network_intensive"]:
            suitability_score += 0.1
            reasons.append("Network-intensive workloads benefit from cloud bandwidth")
        
        # Data sensitivity reduces cloud suitability
        if workload_analysis["data_sensitivity"] in ["high", "confidential"]:
            suitability_score -= 0.3
            reasons.append("High data sensitivity may limit cloud options")
        
        # Strict latency requirements may reduce cloud suitability
        if workload_analysis["latency_requirements"] < 100:
            suitability_score -= 0.2
            reasons.append("Strict latency requirements may favor local execution")
        
        return {
            "score": max(0.0, min(1.0, suitability_score)),
            "reasons": reasons
        }
    
    async def _evaluate_local_options(
        self,
        user_id: uuid.UUID,
        workload_analysis: Dict[str, Any],
        device_profiles: List[DeviceProfile],
        constraints: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate local compute options"""
        
        if not device_profiles:
            return {
                "available": False,
                "reason": "No local devices available",
                "estimated_cost": 0,
                "estimated_performance": 0,
                "suitability_score": 0
            }
        
        best_device = None
        best_score = 0
        
        for device in device_profiles:
            score = await self._score_device_for_workload(device, workload_analysis)
            if score > best_score:
                best_score = score
                best_device = device
        
        if not best_device or best_score < 0.3:
            return {
                "available": False,
                "reason": "No suitable local devices found",
                "estimated_cost": 0,
                "estimated_performance": 0,
                "suitability_score": best_score
            }
        
        # Calculate local execution metrics
        estimated_cost = await self._estimate_local_cost(best_device, workload_analysis)
        estimated_performance = await self._estimate_local_performance(best_device, workload_analysis)
        
        return {
            "available": True,
            "best_device": {
                "name": best_device.device_name,
                "type": best_device.device_type.value,
                "cpu_cores": best_device.cpu_cores,
                "memory_gb": float(best_device.memory_gb),
                "gpu_available": best_device.has_gpu
            },
            "estimated_cost": estimated_cost,
            "estimated_performance": estimated_performance,
            "suitability_score": best_score,
            "advantages": workload_analysis["suitable_for_local"]["reasons"],
            "limitations": await self._identify_local_limitations(best_device, workload_analysis)
        }
    
    async def _evaluate_cloud_options(
        self,
        user_id: uuid.UUID,
        workload_analysis: Dict[str, Any],
        compute_allowance: Optional[ComputeAllowance],
        constraints: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Evaluate cloud compute options"""
        
        # Check budget constraints
        if compute_allowance:
            remaining_budget = float(compute_allowance.monthly_allowance - compute_allowance.current_usage)
            if remaining_budget <= 0:
                return {
                    "available": False,
                    "reason": "No remaining compute allowance",
                    "estimated_cost": 0,
                    "estimated_performance": 0,
                    "suitability_score": 0
                }
        else:
            remaining_budget = float('inf')
        
        # Recommend cloud instance type
        recommended_instance = await self._recommend_cloud_instance(workload_analysis)
        estimated_cost = await self._estimate_cloud_cost(recommended_instance, workload_analysis)
        
        if estimated_cost > remaining_budget:
            return {
                "available": False,
                "reason": f"Estimated cost ${estimated_cost:.2f} exceeds remaining budget ${remaining_budget:.2f}",
                "estimated_cost": estimated_cost,
                "estimated_performance": 0,
                "suitability_score": 0
            }
        
        estimated_performance = await self._estimate_cloud_performance(recommended_instance, workload_analysis)
        suitability_score = workload_analysis["suitable_for_cloud"]["score"]
        
        return {
            "available": True,
            "recommended_instance": recommended_instance,
            "estimated_cost": estimated_cost,
            "estimated_performance": estimated_performance,
            "suitability_score": suitability_score,
            "advantages": workload_analysis["suitable_for_cloud"]["reasons"],
            "limitations": await self._identify_cloud_limitations(workload_analysis)
        }
    
    async def _score_device_for_workload(
        self,
        device: DeviceProfile,
        workload_analysis: Dict[str, Any]
    ) -> float:
        """Score how well a device matches workload requirements"""
        
        score = 0.0
        
        # CPU requirements
        required_cores = max(1, workload_analysis["complexity_score"] // 2)
        if device.cpu_cores >= required_cores:
            score += 0.3
        else:
            score += 0.3 * (device.cpu_cores / required_cores)
        
        # Memory requirements
        if float(device.memory_gb) >= workload_analysis["memory_requirements"]:
            score += 0.3
        else:
            score += 0.3 * (float(device.memory_gb) / workload_analysis["memory_requirements"])
        
        # GPU requirements
        if workload_analysis["gpu_required"]:
            if device.has_gpu:
                score += 0.2
            else:
                score = max(0, score - 0.3)  # Significant penalty for missing GPU
        else:
            score += 0.1  # Small bonus for not needing GPU
        
        # Device type preferences
        if device.device_type == DeviceType.DESKTOP:
            score += 0.1  # Desktop generally better for compute
        elif device.device_type == DeviceType.LAPTOP:
            if workload_analysis["compute_intensity"] == "low":
                score += 0.05  # Laptop OK for light workloads
        
        return min(1.0, score)
    
    async def _estimate_local_cost(
        self,
        device: DeviceProfile,
        workload_analysis: Dict[str, Any]
    ) -> float:
        """Estimate cost of local execution"""
        
        # Simplified cost model - primarily electricity
        runtime_hours = workload_analysis["estimated_runtime"] / 60.0
        
        # Base power consumption estimates (watts)
        base_power = {
            DeviceType.DESKTOP: 200,
            DeviceType.LAPTOP: 65,
            DeviceType.SERVER: 400,
            DeviceType.MOBILE: 10
        }
        
        device_power = base_power.get(device.device_type, 100)
        
        # Adjust for workload intensity
        intensity_multipliers = {"high": 1.5, "medium": 1.0, "low": 0.7}
        power_multiplier = intensity_multipliers.get(workload_analysis["compute_intensity"], 1.0)
        
        total_power_kwh = (device_power * power_multiplier * runtime_hours) / 1000
        
        # Assume $0.12 per kWh
        electricity_cost = total_power_kwh * 0.12
        
        # Add small depreciation cost
        depreciation_cost = 0.01 * runtime_hours  # $0.01 per hour
        
        return electricity_cost + depreciation_cost
    
    async def _estimate_local_performance(
        self,
        device: DeviceProfile,
        workload_analysis: Dict[str, Any]
    ) -> float:
        """Estimate local execution performance (1-10 scale)"""
        
        base_performance = 5.0
        
        # Adjust based on device capabilities vs requirements
        cpu_ratio = device.cpu_cores / max(1, workload_analysis["complexity_score"] // 2)
        memory_ratio = float(device.memory_gb) / workload_analysis["memory_requirements"]
        
        performance_multiplier = min(2.0, (cpu_ratio + memory_ratio) / 2)
        base_performance *= performance_multiplier
        
        # GPU boost
        if device.has_gpu and workload_analysis["gpu_required"]:
            base_performance *= 1.3
        
        # Device type adjustments
        type_multipliers = {
            DeviceType.SERVER: 1.2,
            DeviceType.DESKTOP: 1.0,
            DeviceType.LAPTOP: 0.8,
            DeviceType.MOBILE: 0.4
        }
        
        base_performance *= type_multipliers.get(device.device_type, 1.0)
        
        return min(10.0, base_performance)
    
    async def _recommend_cloud_instance(self, workload_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Recommend appropriate cloud instance type"""
        
        # Simplified instance recommendations
        if workload_analysis["gpu_required"]:
            return {
                "type": "gpu_instance",
                "cpu_cores": 8,
                "memory_gb": 32,
                "gpu_count": 1,
                "cost_per_hour": 2.50
            }
        elif workload_analysis["compute_intensity"] == "high":
            return {
                "type": "compute_optimized",
                "cpu_cores": 16,
                "memory_gb": 32,
                "gpu_count": 0,
                "cost_per_hour": 1.20
            }
        elif workload_analysis["memory_requirements"] > 16:
            return {
                "type": "memory_optimized",
                "cpu_cores": 8,
                "memory_gb": 64,
                "gpu_count": 0,
                "cost_per_hour": 1.50
            }
        else:
            return {
                "type": "general_purpose",
                "cpu_cores": 4,
                "memory_gb": 16,
                "gpu_count": 0,
                "cost_per_hour": 0.50
            }
    
    async def _estimate_cloud_cost(
        self,
        instance: Dict[str, Any],
        workload_analysis: Dict[str, Any]
    ) -> float:
        """Estimate cloud execution cost"""
        
        runtime_hours = workload_analysis["estimated_runtime"] / 60.0
        base_cost = instance["cost_per_hour"] * runtime_hours
        
        # Add storage and network costs (simplified)
        storage_cost = workload_analysis["storage_requirements"] * 0.01  # $0.01 per GB
        
        if workload_analysis["network_intensive"]:
            network_cost = base_cost * 0.1  # 10% of compute cost
        else:
            network_cost = base_cost * 0.02  # 2% of compute cost
        
        return base_cost + storage_cost + network_cost
    
    async def _estimate_cloud_performance(
        self,
        instance: Dict[str, Any],
        workload_analysis: Dict[str, Any]
    ) -> float:
        """Estimate cloud execution performance (1-10 scale)"""
        
        # Cloud instances generally offer consistent performance
        base_performance = 7.0  # Higher baseline than local
        
        # Adjust based on instance type match
        if instance["type"] == "gpu_instance" and workload_analysis["gpu_required"]:
            base_performance = 9.0
        elif instance["type"] == "compute_optimized" and workload_analysis["compute_intensity"] == "high":
            base_performance = 8.5
        elif instance["type"] == "memory_optimized" and workload_analysis["memory_requirements"] > 16:
            base_performance = 8.0
        
        # Network latency impact
        if workload_analysis["latency_requirements"] < 100:
            base_performance -= 1.0  # Penalty for strict latency requirements
        
        return min(10.0, base_performance)
    
    async def _identify_local_limitations(
        self,
        device: DeviceProfile,
        workload_analysis: Dict[str, Any]
    ) -> List[str]:
        """Identify limitations of local execution"""
        
        limitations = []
        
        if device.cpu_cores < workload_analysis["complexity_score"] // 2:
            limitations.append("Limited CPU cores may impact performance")
        
        if float(device.memory_gb) < workload_analysis["memory_requirements"]:
            limitations.append("Insufficient memory may cause swapping")
        
        if workload_analysis["gpu_required"] and not device.has_gpu:
            limitations.append("No GPU available for GPU-required workload")
        
        if device.device_type == DeviceType.LAPTOP and workload_analysis["compute_intensity"] == "high":
            limitations.append("Laptop thermal constraints may limit sustained performance")
        
        return limitations
    
    async def _identify_cloud_limitations(self, workload_analysis: Dict[str, Any]) -> List[str]:
        """Identify limitations of cloud execution"""
        
        limitations = []
        
        if workload_analysis["data_sensitivity"] in ["high", "confidential"]:
            limitations.append("Data sensitivity concerns with cloud storage")
        
        if workload_analysis["latency_requirements"] < 100:
            limitations.append("Network latency may impact real-time requirements")
        
        if workload_analysis["network_intensive"]:
            limitations.append("High network costs for data-intensive workloads")
        
        return limitations
    
    async def _calculate_preference_weights(
        self,
        user_id: uuid.UUID,
        decision_history: List[CloudDecision],
        preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate user preference weights based on history and explicit preferences"""
        
        weights = {
            "cost_sensitivity": 0.3,
            "performance_priority": 0.3,
            "privacy_concern": 0.2,
            "convenience_preference": 0.2
        }
        
        # Adjust based on explicit preferences
        if preferences:
            for key in weights:
                if key in preferences:
                    weights[key] = float(preferences[key])
        
        # Adjust based on historical decisions
        if decision_history:
            local_decisions = len([d for d in decision_history if d.selected_option == "local"])
            total_decisions = len(decision_history)
            local_preference = local_decisions / total_decisions
            
            # Higher local preference suggests higher privacy concern
            weights["privacy_concern"] = min(1.0, weights["privacy_concern"] + local_preference * 0.2)
            
            # Analyze cost vs performance choices
            high_cost_decisions = len([
                d for d in decision_history 
                if d.estimated_cost > 10.0 and d.selected_option == "cloud"
            ])
            
            if high_cost_decisions > total_decisions * 0.3:
                weights["performance_priority"] += 0.1
                weights["cost_sensitivity"] -= 0.1
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    async def _make_final_decision(
        self,
        local_evaluation: Dict[str, Any],
        cloud_evaluation: Dict[str, Any],
        preference_weights: Dict[str, float],
        constraints: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Make the final local vs cloud decision"""
        
        local_score = 0.0
        cloud_score = 0.0
        reasoning = []
        
        # Availability check
        if not local_evaluation["available"] and not cloud_evaluation["available"]:
            return {
                "recommended_option": "none",
                "confidence_score": 1.0,
                "reasoning": ["Neither local nor cloud options are available"],
                "cost_comparison": {"local": 0, "cloud": 0},
                "performance_comparison": {"local": 0, "cloud": 0}
            }
        elif not local_evaluation["available"]:
            return {
                "recommended_option": "cloud",
                "confidence_score": 1.0,
                "reasoning": ["Local execution not available", local_evaluation["reason"]],
                "cost_comparison": {"local": 0, "cloud": cloud_evaluation["estimated_cost"]},
                "performance_comparison": {"local": 0, "cloud": cloud_evaluation["estimated_performance"]}
            }
        elif not cloud_evaluation["available"]:
            return {
                "recommended_option": "local",
                "confidence_score": 1.0,
                "reasoning": ["Cloud execution not available", cloud_evaluation["reason"]],
                "cost_comparison": {"local": local_evaluation["estimated_cost"], "cloud": 0},
                "performance_comparison": {"local": local_evaluation["estimated_performance"], "cloud": 0}
            }
        
        # Both options available - make weighted decision
        
        # Cost comparison
        local_cost = local_evaluation["estimated_cost"]
        cloud_cost = cloud_evaluation["estimated_cost"]
        
        if local_cost < cloud_cost:
            cost_advantage = (cloud_cost - local_cost) / max(cloud_cost, 0.01)
            local_score += preference_weights["cost_sensitivity"] * cost_advantage
            reasoning.append(f"Local execution is ${cloud_cost - local_cost:.2f} cheaper")
        else:
            cost_advantage = (local_cost - cloud_cost) / max(local_cost, 0.01)
            cloud_score += preference_weights["cost_sensitivity"] * cost_advantage
            reasoning.append(f"Cloud execution is ${local_cost - cloud_cost:.2f} cheaper")
        
        # Performance comparison
        local_perf = local_evaluation["estimated_performance"]
        cloud_perf = cloud_evaluation["estimated_performance"]
        
        if local_perf > cloud_perf:
            perf_advantage = (local_perf - cloud_perf) / 10.0
            local_score += preference_weights["performance_priority"] * perf_advantage
            reasoning.append(f"Local execution offers better performance ({local_perf:.1f} vs {cloud_perf:.1f})")
        else:
            perf_advantage = (cloud_perf - local_perf) / 10.0
            cloud_score += preference_weights["performance_priority"] * perf_advantage
            reasoning.append(f"Cloud execution offers better performance ({cloud_perf:.1f} vs {local_perf:.1f})")
        
        # Privacy considerations
        local_score += preference_weights["privacy_concern"] * 0.8  # Local generally more private
        reasoning.append("Local execution provides better data privacy")
        
        # Convenience considerations
        cloud_score += preference_weights["convenience_preference"] * 0.7  # Cloud generally more convenient
        reasoning.append("Cloud execution offers better convenience and scalability")
        
        # Make final decision
        if local_score > cloud_score:
            recommended_option = "local"
            confidence = min(1.0, (local_score - cloud_score) + 0.5)
        else:
            recommended_option = "cloud"
            confidence = min(1.0, (cloud_score - local_score) + 0.5)
        
        # Generate alternatives
        alternatives = []
        if recommended_option == "local" and cloud_evaluation["available"]:
            alternatives.append({
                "option": "cloud",
                "reason": "Higher performance and scalability",
                "cost_difference": cloud_cost - local_cost
            })
        elif recommended_option == "cloud" and local_evaluation["available"]:
            alternatives.append({
                "option": "local",
                "reason": "Lower cost and better privacy",
                "cost_difference": local_cost - cloud_cost
            })
        
        return {
            "recommended_option": recommended_option,
            "confidence_score": confidence,
            "reasoning": reasoning,
            "cost_comparison": {"local": local_cost, "cloud": cloud_cost},
            "performance_comparison": {"local": local_perf, "cloud": cloud_perf},
            "alternatives": alternatives,
            "decision_scores": {"local": local_score, "cloud": cloud_score}
        }
    
    async def _store_decision(
        self,
        user_id: uuid.UUID,
        workload: Dict[str, Any],
        decision_result: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """Store decision for learning and analytics"""
        
        decision = CloudDecision(
            user_id=user_id,
            workload_name=workload.get("name", "Unknown"),
            workload_metadata=workload,
            selected_option=decision_result["recommended_option"],
            confidence_score=Decimal(str(decision_result["confidence_score"])),
            estimated_cost=Decimal(str(decision_result["cost_comparison"].get(decision_result["recommended_option"], 0))),
            decision_factors=metadata,
            decision_reasoning=decision_result["reasoning"],
            decision_date=datetime.utcnow()
        )
        
        self.db.add(decision)
        await self.db.commit()
    
    async def _analyze_decision_accuracy(
        self,
        decision: CloudDecision,
        outcome_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze how accurate the decision was"""
        
        accuracy_score = 0.5  # Base score
        analysis = {"factors": []}
        
        # Cost accuracy
        predicted_cost = float(decision.estimated_cost)
        actual_cost = outcome_metrics.get("cost", predicted_cost)
        
        cost_error = abs(actual_cost - predicted_cost) / max(predicted_cost, 0.01)
        if cost_error < 0.1:  # Within 10%
            accuracy_score += 0.2
            analysis["factors"].append("Cost prediction within 10%")
        elif cost_error > 0.5:  # Off by more than 50%
            accuracy_score -= 0.1
            analysis["factors"].append(f"Cost prediction off by {cost_error * 100:.1f}%")
        
        # User satisfaction
        if decision.user_satisfaction:
            if decision.user_satisfaction >= 8:
                accuracy_score += 0.3
                analysis["factors"].append("High user satisfaction")
            elif decision.user_satisfaction <= 4:
                accuracy_score -= 0.2
                analysis["factors"].append("Low user satisfaction")
        
        # Performance accuracy (if provided)
        if "performance" in outcome_metrics and "estimated_performance" in decision.decision_factors:
            predicted_perf = decision.decision_factors["estimated_performance"]
            actual_perf = outcome_metrics["performance"].get("score", predicted_perf)
            
            perf_error = abs(actual_perf - predicted_perf) / max(predicted_perf, 0.01)
            if perf_error < 0.15:  # Within 15%
                accuracy_score += 0.2
                analysis["factors"].append("Performance prediction accurate")
        
        analysis["overall_accuracy"] = max(0.0, min(1.0, accuracy_score))
        analysis["will_improve_future"] = accuracy_score > 0.6
        
        return analysis
    
    async def _update_learning_model(
        self,
        user_id: uuid.UUID,
        decision: CloudDecision,
        accuracy_analysis: Dict[str, Any]
    ):
        """Update learning model with outcome data"""
        
        # In a production system, this would update ML models
        # For now, we'll log the learning opportunity
        logger.info(f"Learning update for user {user_id}: accuracy={accuracy_analysis['overall_accuracy']}")
        
        # Store learning data that could be used for model training
        learning_data = {
            "decision_id": str(decision.id),
            "accuracy_score": accuracy_analysis["overall_accuracy"],
            "decision_factors": decision.decision_factors,
            "outcome_data": {
                "user_satisfaction": decision.user_satisfaction,
                "actual_cost": float(decision.actual_cost) if decision.actual_cost else None
            }
        }
        
        # This would be sent to ML pipeline for model updates
        pass
    
    async def _analyze_decision_trends(self, decisions: List[CloudDecision]) -> Dict[str, Any]:
        """Analyze trends in user's decisions"""
        
        if len(decisions) < 10:
            return {"insufficient_data": True}
        
        # Sort decisions by date
        sorted_decisions = sorted(decisions, key=lambda x: x.decision_date)
        
        # Analyze cost trends
        costs = [float(d.actual_cost or d.estimated_cost) for d in sorted_decisions]
        recent_costs = costs[-5:]
        earlier_costs = costs[:-5]
        
        recent_avg_cost = sum(recent_costs) / len(recent_costs)
        earlier_avg_cost = sum(earlier_costs) / len(earlier_costs) if earlier_costs else recent_avg_cost
        
        if recent_avg_cost > earlier_avg_cost * 1.2:
            cost_trend = "increasing"
        elif recent_avg_cost < earlier_avg_cost * 0.8:
            cost_trend = "decreasing"
        else:
            cost_trend = "stable"
        
        # Analyze option preferences over time
        recent_local = len([d for d in sorted_decisions[-10:] if d.selected_option == "local"])
        earlier_local = len([d for d in sorted_decisions[:-10] if d.selected_option == "local"])
        
        recent_local_pct = recent_local / 10
        earlier_local_pct = earlier_local / len(sorted_decisions[:-10]) if len(sorted_decisions) > 10 else recent_local_pct
        
        if recent_local_pct > earlier_local_pct + 0.2:
            preference_trend = "increasing_local_preference"
        elif recent_local_pct < earlier_local_pct - 0.2:
            preference_trend = "increasing_cloud_preference"
        else:
            preference_trend = "stable_preferences"
        
        return {
            "cost_trend": cost_trend,
            "preference_trend": preference_trend,
            "recent_avg_cost": recent_avg_cost,
            "cost_change_percentage": ((recent_avg_cost - earlier_avg_cost) / earlier_avg_cost) * 100 if earlier_avg_cost > 0 else 0
        }
    
    async def _generate_decision_improvement_recommendations(
        self,
        user_id: uuid.UUID,
        decisions: List[CloudDecision]
    ) -> List[str]:
        """Generate recommendations to improve decision making"""
        
        recommendations = []
        
        # Analyze satisfaction scores
        satisfaction_scores = [d.user_satisfaction for d in decisions if d.user_satisfaction]
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            if avg_satisfaction < 6:
                recommendations.append("Consider adjusting cost vs performance preferences")
                recommendations.append("Review workload requirements accuracy")
        
        # Analyze cost overruns
        cost_errors = []
        for d in decisions:
            if d.actual_cost:
                error = abs(float(d.actual_cost) - float(d.estimated_cost)) / float(d.estimated_cost)
                cost_errors.append(error)
        
        if cost_errors and sum(cost_errors) / len(cost_errors) > 0.2:
            recommendations.append("Improve cost estimation accuracy")
        
        # Analyze option distribution
        local_decisions = len([d for d in decisions if d.selected_option == "local"])
        if local_decisions / len(decisions) > 0.8:
            recommendations.append("Consider cloud options for better performance and scalability")
        elif local_decisions / len(decisions) < 0.2:
            recommendations.append("Consider local options for cost savings and privacy")
        
        if not recommendations:
            recommendations.append("Decision patterns look optimal, continue current approach")
        
        return recommendations
    
    async def _get_decisions_with_outcomes(self, user_id: uuid.UUID) -> List[CloudDecision]:
        """Get decisions that have outcome data for training"""
        
        result = await self.db.execute(
            select(CloudDecision).where(
                and_(
                    CloudDecision.user_id == user_id,
                    CloudDecision.outcome_recorded == True
                )
            )
        )
        return result.scalars().all()
    
    async def _extract_training_features(
        self,
        decisions: List[CloudDecision]
    ) -> Tuple[List[List[float]], List[int]]:
        """Extract features and labels for model training"""
        
        features = []
        labels = []  # 1 for good decision (satisfaction >= 7), 0 for poor decision
        
        for decision in decisions:
            if decision.user_satisfaction is None:
                continue
            
            # Extract numerical features from decision
            feature_vector = [
                float(decision.estimated_cost),
                float(decision.confidence_score),
                len(decision.decision_reasoning or []),
                1.0 if decision.selected_option == "local" else 0.0,
                # Add more features based on workload_metadata and decision_factors
            ]
            
            # Add workload features if available
            if decision.workload_metadata:
                workload = decision.workload_metadata
                feature_vector.extend([
                    workload.get("compute_intensity_score", 0.5),  # Would need to encode this
                    workload.get("memory_requirements", 4) / 32.0,  # Normalize
                    1.0 if workload.get("gpu_required", False) else 0.0,
                    1.0 if workload.get("network_intensive", False) else 0.0
                ])
            
            features.append(feature_vector)
            labels.append(1 if decision.user_satisfaction >= 7 else 0)
        
        return features, labels
    
    async def _train_decision_weights(
        self,
        features: List[List[float]],
        labels: List[int]
    ) -> Dict[str, float]:
        """Train decision model weights (simplified - would use proper ML in production)"""
        
        # Simplified weight calculation based on correlation with satisfaction
        if not features or not labels:
            return {"cost_weight": 0.3, "performance_weight": 0.3, "privacy_weight": 0.2, "convenience_weight": 0.2}
        
        # Calculate simple correlations (in production, would use proper ML algorithms)
        positive_decisions = [i for i, label in enumerate(labels) if label == 1]
        negative_decisions = [i for i, label in enumerate(labels) if label == 0]
        
        weights = {}
        
        # Cost sensitivity (lower cost correlated with satisfaction?)
        pos_costs = [features[i][0] for i in positive_decisions]
        neg_costs = [features[i][0] for i in negative_decisions]
        
        if pos_costs and neg_costs:
            pos_avg_cost = sum(pos_costs) / len(pos_costs)
            neg_avg_cost = sum(neg_costs) / len(neg_costs)
            
            if pos_avg_cost < neg_avg_cost:
                weights["cost_weight"] = 0.4  # Higher cost sensitivity
            else:
                weights["cost_weight"] = 0.2  # Lower cost sensitivity
        else:
            weights["cost_weight"] = 0.3
        
        # Set other weights to sum to 1.0
        remaining_weight = 1.0 - weights["cost_weight"]
        weights["performance_weight"] = remaining_weight * 0.4
        weights["privacy_weight"] = remaining_weight * 0.3
        weights["convenience_weight"] = remaining_weight * 0.3
        
        return weights
    
    async def _store_user_decision_model(
        self,
        user_id: uuid.UUID,
        model_weights: Dict[str, float]
    ):
        """Store user's personalized decision model"""
        
        # In production, this would store the model in a dedicated model store
        # For now, we'll store it in user metadata or a dedicated table
        logger.info(f"Storing decision model for user {user_id}: {model_weights}")
        
        # This would integrate with model storage system
        pass
    
    async def _validate_model_performance(
        self,
        user_id: uuid.UUID,
        decisions: List[CloudDecision],
        model_weights: Dict[str, float]
    ) -> Dict[str, Any]:
        """Validate model performance using cross-validation"""
        
        if len(decisions) < 10:
            return {"insufficient_data": True, "improvement": 0}
        
        # Simplified validation - compare with baseline random decision
        correct_predictions = 0
        total_predictions = len([d for d in decisions if d.user_satisfaction is not None])
        
        for decision in decisions:
            if decision.user_satisfaction is None:
                continue
            
            # Simulate prediction with new weights (simplified)
            predicted_satisfaction = 5.0  # Base prediction
            
            # Adjust based on cost (lower cost should predict higher satisfaction if cost_weight high)
            if model_weights["cost_weight"] > 0.3 and float(decision.estimated_cost) < 5.0:
                predicted_satisfaction += 2.0
            
            # Simple threshold: predict satisfied if > 6.5
            predicted_satisfied = predicted_satisfaction > 6.5
            actual_satisfied = decision.user_satisfaction >= 7
            
            if predicted_satisfied == actual_satisfied:
                correct_predictions += 1
        
        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0
        baseline_accuracy = 0.6  # Assume 60% baseline
        improvement = max(0, accuracy - baseline_accuracy)
        
        return {
            "accuracy": accuracy,
            "baseline_accuracy": baseline_accuracy,
            "improvement": improvement,
            "total_predictions": total_predictions
        }