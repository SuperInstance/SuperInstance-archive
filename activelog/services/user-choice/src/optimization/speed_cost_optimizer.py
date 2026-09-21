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
    SpeedCostDecision, OptimizationHistory
)

logger = logging.getLogger(__name__)

class SpeedVsCostOptimizer:
    """Optimize the trade-off between execution speed and cost"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def optimize_speed_cost_tradeoff(
        self,
        user_id: uuid.UUID,
        task: Dict[str, Any],
        constraints: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Find optimal speed vs cost configuration for a task"""
        
        try:
            # Get user context
            compute_allowance = await self._get_compute_allowance(user_id)
            user_history = await self._get_speed_cost_history(user_id)
            device_profiles = await self._get_device_profiles(user_id)
            
            # Analyze task requirements
            task_analysis = await self._analyze_task_requirements(task)
            
            # Generate configuration options
            config_options = await self._generate_configuration_options(
                task_analysis, device_profiles, constraints
            )
            
            # Evaluate each configuration
            evaluations = []
            for config in config_options:
                evaluation = await self._evaluate_configuration(
                    user_id, task_analysis, config, compute_allowance
                )
                evaluations.append(evaluation)
            
            # Apply user preferences and learning
            preference_weights = await self._calculate_preference_weights(
                user_id, user_history, user_preferences
            )
            
            # Find optimal configuration
            optimal_config = await self._select_optimal_configuration(
                evaluations, preference_weights, constraints
            )
            
            # Generate alternatives and recommendations
            alternatives = await self._generate_alternatives(
                evaluations, optimal_config, preference_weights
            )
            
            # Store decision for learning
            await self._store_speed_cost_decision(
                user_id, task, optimal_config, evaluations, preference_weights
            )
            
            return {
                "user_id": str(user_id),
                "task_name": task.get("name", "Unknown"),
                "optimal_configuration": optimal_config,
                "speed_cost_analysis": {
                    "estimated_execution_time": optimal_config["estimated_time_minutes"],
                    "estimated_cost": optimal_config["estimated_cost"],
                    "cost_per_minute": optimal_config["estimated_cost"] / max(optimal_config["estimated_time_minutes"], 1),
                    "efficiency_score": optimal_config["efficiency_score"]
                },
                "configuration_options": evaluations[:5],  # Top 5 options
                "alternatives": alternatives,
                "optimization_reasoning": optimal_config["reasoning"],
                "confidence_score": optimal_config["confidence"],
                "trade_off_analysis": await self._analyze_tradeoffs(evaluations),
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize speed vs cost: {e}")
            raise
    
    async def evaluate_speed_cost_outcome(
        self,
        decision_id: uuid.UUID,
        actual_metrics: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate the actual outcome of a speed vs cost optimization"""
        
        try:
            # Get the decision
            result = await self.db.execute(
                select(SpeedCostDecision).where(SpeedCostDecision.id == decision_id)
            )
            decision = result.scalar_one_or_none()
            
            if not decision:
                return {"success": False, "error": "Decision not found"}
            
            # Update with actual metrics
            decision.actual_execution_time = actual_metrics.get("execution_time_minutes")
            decision.actual_cost = Decimal(str(actual_metrics.get("cost", 0)))
            decision.actual_performance_score = actual_metrics.get("performance_score")
            decision.user_satisfaction = user_feedback.get("satisfaction") if user_feedback else None
            decision.outcome_recorded = True
            decision.outcome_timestamp = datetime.utcnow()
            
            # Calculate accuracy metrics
            accuracy_analysis = await self._analyze_prediction_accuracy(decision, actual_metrics)
            
            # Update learning models
            await self._update_speed_cost_models(decision.user_id, decision, accuracy_analysis)
            
            await self.db.commit()
            
            return {
                "success": True,
                "decision_id": str(decision_id),
                "accuracy_analysis": accuracy_analysis,
                "prediction_errors": {
                    "time_error_percentage": accuracy_analysis.get("time_error_pct", 0),
                    "cost_error_percentage": accuracy_analysis.get("cost_error_pct", 0),
                    "overall_accuracy": accuracy_analysis.get("overall_accuracy", 0)
                },
                "learning_impact": "Model updated with outcome data",
                "future_improvements": accuracy_analysis.get("will_improve_predictions", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate speed cost outcome: {e}")
            raise
    
    async def get_speed_cost_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics on user's speed vs cost optimizations"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get decisions in period
            result = await self.db.execute(
                select(SpeedCostDecision).where(
                    and_(
                        SpeedCostDecision.user_id == user_id,
                        SpeedCostDecision.decision_date >= start_date
                    )
                ).order_by(SpeedCostDecision.decision_date.desc())
            )
            decisions = result.scalars().all()
            
            if not decisions:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "message": "No speed vs cost decisions found for this period"
                }
            
            # Calculate analytics
            total_decisions = len(decisions)
            total_estimated_cost = sum(float(d.estimated_cost) for d in decisions)
            total_actual_cost = sum(float(d.actual_cost) for d in decisions if d.actual_cost)
            
            estimated_time = sum(d.estimated_execution_time or 0 for d in decisions)
            actual_time = sum(d.actual_execution_time or 0 for d in decisions if d.actual_execution_time)
            
            # Accuracy metrics
            accurate_decisions = len([
                d for d in decisions 
                if d.outcome_recorded and d.user_satisfaction and d.user_satisfaction >= 7
            ])
            
            accuracy_rate = (accurate_decisions / total_decisions) * 100 if total_decisions > 0 else 0
            
            # Preference analysis
            speed_optimized = len([d for d in decisions if d.optimization_target == "speed"])
            cost_optimized = len([d for d in decisions if d.optimization_target == "cost"])
            balanced_optimized = len([d for d in decisions if d.optimization_target == "balanced"])
            
            # Efficiency analysis
            efficiency_scores = [
                float(d.selected_configuration.get("efficiency_score", 0)) 
                for d in decisions if d.selected_configuration
            ]
            avg_efficiency = sum(efficiency_scores) / len(efficiency_scores) if efficiency_scores else 0
            
            # Cost vs speed trends
            trends = await self._analyze_speed_cost_trends(decisions)
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "decision_summary": {
                    "total_decisions": total_decisions,
                    "speed_optimized_count": speed_optimized,
                    "cost_optimized_count": cost_optimized,
                    "balanced_optimized_count": balanced_optimized,
                    "optimization_preference": "speed" if speed_optimized > cost_optimized else "cost" if cost_optimized > speed_optimized else "balanced"
                },
                "cost_analysis": {
                    "total_estimated_cost": total_estimated_cost,
                    "total_actual_cost": total_actual_cost,
                    "cost_prediction_accuracy": abs(total_actual_cost - total_estimated_cost) / max(total_estimated_cost, 1) * 100 if total_actual_cost > 0 else 0,
                    "average_cost_per_decision": total_estimated_cost / total_decisions
                },
                "time_analysis": {
                    "total_estimated_time_minutes": estimated_time,
                    "total_actual_time_minutes": actual_time,
                    "time_prediction_accuracy": abs(actual_time - estimated_time) / max(estimated_time, 1) * 100 if actual_time > 0 else 0,
                    "average_time_per_decision": estimated_time / total_decisions
                },
                "efficiency_metrics": {
                    "average_efficiency_score": round(avg_efficiency, 2),
                    "decision_accuracy_rate": round(accuracy_rate, 2),
                    "cost_time_ratio": total_estimated_cost / max(estimated_time, 1) if estimated_time > 0 else 0
                },
                "trends": trends,
                "recommendations": await self._generate_optimization_recommendations(user_id, decisions),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get speed cost analytics: {e}")
            raise
    
    async def recommend_speed_cost_settings(
        self,
        user_id: uuid.UUID,
        task_type: str,
        budget_constraint: Optional[Decimal] = None,
        time_constraint: Optional[int] = None
    ) -> Dict[str, Any]:
        """Recommend optimal speed vs cost settings for a task type"""
        
        try:
            # Get user's historical performance for this task type
            task_history = await self._get_task_type_history(user_id, task_type)
            
            # Analyze user's preferences based on history
            preference_analysis = await self._analyze_user_preferences(user_id, task_history)
            
            # Generate recommendations based on constraints and preferences
            recommendations = []
            
            if budget_constraint:
                budget_rec = await self._recommend_budget_optimized_settings(
                    user_id, task_type, budget_constraint, preference_analysis
                )
                recommendations.append(budget_rec)
            
            if time_constraint:
                time_rec = await self._recommend_time_optimized_settings(
                    user_id, task_type, time_constraint, preference_analysis
                )
                recommendations.append(time_rec)
            
            # Default balanced recommendation
            balanced_rec = await self._recommend_balanced_settings(
                user_id, task_type, preference_analysis
            )
            recommendations.append(balanced_rec)
            
            # Select best recommendation
            best_recommendation = await self._select_best_recommendation(
                recommendations, preference_analysis, budget_constraint, time_constraint
            )
            
            return {
                "user_id": str(user_id),
                "task_type": task_type,
                "recommended_settings": best_recommendation,
                "all_recommendations": recommendations,
                "user_preferences": preference_analysis,
                "constraints": {
                    "budget_limit": float(budget_constraint) if budget_constraint else None,
                    "time_limit_minutes": time_constraint
                },
                "confidence_score": best_recommendation.get("confidence", 0.5),
                "expected_outcomes": best_recommendation.get("expected_outcomes", {}),
                "recommendation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to recommend speed cost settings: {e}")
            raise
    
    # Helper methods
    
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
    
    async def _get_speed_cost_history(self, user_id: uuid.UUID) -> List[SpeedCostDecision]:
        """Get user's speed vs cost decision history"""
        lookback_date = datetime.utcnow() - timedelta(days=90)
        result = await self.db.execute(
            select(SpeedCostDecision).where(
                and_(
                    SpeedCostDecision.user_id == user_id,
                    SpeedCostDecision.decision_date >= lookback_date
                )
            ).order_by(SpeedCostDecision.decision_date.desc())
        )
        return result.scalars().all()
    
    async def _get_device_profiles(self, user_id: uuid.UUID) -> List[DeviceProfile]:
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
    
    async def _analyze_task_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze task requirements for speed vs cost optimization"""
        
        analysis = {
            "name": task.get("name", "Unknown"),
            "type": task.get("type", "general"),
            "priority": task.get("priority", 5),  # 1-10 scale
            "complexity": task.get("complexity", "medium"),
            "data_size_gb": task.get("data_size_gb", 1),
            "cpu_intensive": task.get("cpu_intensive", False),
            "memory_intensive": task.get("memory_intensive", False),
            "io_intensive": task.get("io_intensive", False),
            "parallelizable": task.get("parallelizable", True),
            "deadline_hours": task.get("deadline_hours", 24),
            "quality_requirements": task.get("quality_requirements", "standard")
        }
        
        # Calculate urgency score
        if analysis["deadline_hours"] <= 1:
            analysis["urgency_score"] = 10
        elif analysis["deadline_hours"] <= 6:
            analysis["urgency_score"] = 8
        elif analysis["deadline_hours"] <= 24:
            analysis["urgency_score"] = 6
        else:
            analysis["urgency_score"] = 4
        
        # Calculate resource intensity score
        intensity_score = 1
        if analysis["cpu_intensive"]:
            intensity_score += 3
        if analysis["memory_intensive"]:
            intensity_score += 2
        if analysis["io_intensive"]:
            intensity_score += 1
        if analysis["data_size_gb"] > 10:
            intensity_score += 2
        
        analysis["resource_intensity"] = min(10, intensity_score)
        
        return analysis
    
    async def _generate_configuration_options(
        self,
        task_analysis: Dict[str, Any],
        device_profiles: List[DeviceProfile],
        constraints: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate different configuration options for speed vs cost optimization"""
        
        options = []
        
        # Local execution options
        for device in device_profiles:
            # Speed-optimized local
            options.append({
                "name": f"Speed-Optimized Local ({device.device_name})",
                "execution_type": "local",
                "device_id": str(device.id),
                "compute_allocation": "maximum",
                "optimization_target": "speed",
                "parallel_execution": task_analysis["parallelizable"],
                "resource_allocation": {
                    "cpu_cores": device.cpu_cores,
                    "memory_gb": float(device.memory_gb),
                    "gpu_enabled": device.has_gpu
                }
            })
            
            # Cost-optimized local
            options.append({
                "name": f"Cost-Optimized Local ({device.device_name})",
                "execution_type": "local",
                "device_id": str(device.id),
                "compute_allocation": "efficient",
                "optimization_target": "cost",
                "parallel_execution": False,
                "resource_allocation": {
                    "cpu_cores": max(1, device.cpu_cores // 2),
                    "memory_gb": min(8, float(device.memory_gb)),
                    "gpu_enabled": False
                }
            })
        
        # Cloud execution options
        cloud_instances = await self._get_cloud_instance_options(task_analysis)
        
        for instance in cloud_instances:
            # Speed-optimized cloud
            options.append({
                "name": f"Speed-Optimized Cloud ({instance['type']})",
                "execution_type": "cloud",
                "instance_type": instance["type"],
                "compute_allocation": "maximum",
                "optimization_target": "speed",
                "parallel_execution": True,
                "resource_allocation": instance["specs"],
                "auto_scaling": True
            })
            
            # Cost-optimized cloud
            options.append({
                "name": f"Cost-Optimized Cloud ({instance['type']})",
                "execution_type": "cloud",
                "instance_type": instance["type"],
                "compute_allocation": "efficient",
                "optimization_target": "cost",
                "parallel_execution": False,
                "resource_allocation": {
                    **instance["specs"],
                    "cpu_cores": max(1, instance["specs"]["cpu_cores"] // 2)
                },
                "auto_scaling": False
            })
        
        # Hybrid options
        if len(device_profiles) > 0 and len(cloud_instances) > 0:
            options.append({
                "name": "Hybrid Local+Cloud",
                "execution_type": "hybrid",
                "optimization_target": "balanced",
                "local_portion": 0.6,
                "cloud_portion": 0.4,
                "resource_allocation": {
                    "local_device": device_profiles[0].id,
                    "cloud_instance": cloud_instances[0]["type"]
                }
            })
        
        # Filter options based on constraints
        if constraints:
            options = await self._filter_options_by_constraints(options, constraints)
        
        return options
    
    async def _evaluate_configuration(
        self,
        user_id: uuid.UUID,
        task_analysis: Dict[str, Any],
        config: Dict[str, Any],
        compute_allowance: Optional[ComputeAllowance]
    ) -> Dict[str, Any]:
        """Evaluate a specific configuration option"""
        
        evaluation = {
            "configuration": config,
            "estimated_time_minutes": 0,
            "estimated_cost": 0,
            "performance_score": 0,
            "efficiency_score": 0,
            "feasibility_score": 1.0,
            "reasoning": [],
            "pros": [],
            "cons": []
        }
        
        # Estimate execution time
        base_time = await self._estimate_base_execution_time(task_analysis)
        
        if config["execution_type"] == "local":
            # Local execution time calculation
            device_multiplier = await self._calculate_device_performance_multiplier(
                config["device_id"], task_analysis
            )
            
            if config["optimization_target"] == "speed":
                speed_multiplier = 0.7  # 30% faster
                evaluation["reasoning"].append("Speed optimization reduces execution time")
            else:
                speed_multiplier = 1.2  # 20% slower for efficiency
                evaluation["reasoning"].append("Cost optimization may increase execution time")
            
            evaluation["estimated_time_minutes"] = base_time * device_multiplier * speed_multiplier
            
            # Local cost calculation
            evaluation["estimated_cost"] = await self._calculate_local_cost(
                config, evaluation["estimated_time_minutes"]
            )
            
            evaluation["pros"].extend(["No cloud costs", "Data stays local", "No network latency"])
            evaluation["cons"].extend(["Limited by local hardware", "May tie up device"])
            
        elif config["execution_type"] == "cloud":
            # Cloud execution time calculation
            cloud_multiplier = 0.8  # Cloud generally faster
            
            if config["optimization_target"] == "speed":
                cloud_multiplier *= 0.6  # Much faster with optimized cloud
                evaluation["reasoning"].append("Cloud speed optimization with high-performance instances")
            
            evaluation["estimated_time_minutes"] = base_time * cloud_multiplier
            
            # Cloud cost calculation
            evaluation["estimated_cost"] = await self._calculate_cloud_cost(
                config, evaluation["estimated_time_minutes"]
            )
            
            evaluation["pros"].extend(["High performance", "Scalable resources", "No local resource usage"])
            evaluation["cons"].extend(["Network latency", "Data transfer costs", "Variable pricing"])
            
        elif config["execution_type"] == "hybrid":
            # Hybrid execution calculation
            local_time = base_time * 1.1 * config["local_portion"]  # Slightly slower for coordination
            cloud_time = base_time * 0.8 * config["cloud_portion"]
            evaluation["estimated_time_minutes"] = max(local_time, cloud_time)  # Limited by slower component
            
            local_cost = await self._calculate_local_cost(config, local_time)
            cloud_cost = await self._calculate_cloud_cost(config, cloud_time)
            evaluation["estimated_cost"] = local_cost + cloud_cost
            
            evaluation["pros"].extend(["Best of both worlds", "Risk mitigation"])
            evaluation["cons"].extend(["Coordination complexity", "Potential bottlenecks"])
        
        # Calculate performance score (1-10)
        performance_factors = {
            "speed": 10 - (evaluation["estimated_time_minutes"] / max(base_time, 1)),
            "resource_utilization": 8 if config["optimization_target"] == "speed" else 6,
            "reliability": 9 if config["execution_type"] == "cloud" else 7
        }
        
        evaluation["performance_score"] = sum(performance_factors.values()) / len(performance_factors)
        
        # Calculate efficiency score (cost-effectiveness)
        if evaluation["estimated_cost"] > 0 and evaluation["estimated_time_minutes"] > 0:
            time_cost_ratio = evaluation["estimated_time_minutes"] / evaluation["estimated_cost"]
            evaluation["efficiency_score"] = min(10, time_cost_ratio * 2)  # Normalize to 0-10
        else:
            evaluation["efficiency_score"] = 5
        
        # Check feasibility
        if compute_allowance and evaluation["estimated_cost"] > float(compute_allowance.monthly_allowance - compute_allowance.current_usage):
            evaluation["feasibility_score"] *= 0.3
            evaluation["cons"].append("Exceeds available budget")
        
        # Adjust scores based on task urgency
        urgency_multiplier = task_analysis["urgency_score"] / 10.0
        if config["optimization_target"] == "speed":
            evaluation["performance_score"] *= (1 + urgency_multiplier * 0.2)
        
        return evaluation
    
    async def _calculate_preference_weights(
        self,
        user_id: uuid.UUID,
        user_history: List[SpeedCostDecision],
        user_preferences: Optional[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate user preference weights for speed vs cost"""
        
        weights = {
            "speed_preference": 0.4,
            "cost_preference": 0.4,
            "efficiency_preference": 0.2
        }
        
        # Adjust based on explicit preferences
        if user_preferences:
            if "speed_priority" in user_preferences:
                weights["speed_preference"] = float(user_preferences["speed_priority"])
            if "cost_priority" in user_preferences:
                weights["cost_preference"] = float(user_preferences["cost_priority"])
            if "efficiency_priority" in user_preferences:
                weights["efficiency_preference"] = float(user_preferences["efficiency_priority"])
        
        # Adjust based on historical decisions
        if user_history:
            speed_decisions = len([d for d in user_history if d.optimization_target == "speed"])
            cost_decisions = len([d for d in user_history if d.optimization_target == "cost"])
            total_decisions = len(user_history)
            
            if speed_decisions > cost_decisions:
                weights["speed_preference"] += 0.1
                weights["cost_preference"] -= 0.05
            elif cost_decisions > speed_decisions:
                weights["cost_preference"] += 0.1
                weights["speed_preference"] -= 0.05
            
            # Analyze satisfaction with different choices
            speed_satisfaction = [
                d.user_satisfaction for d in user_history 
                if d.optimization_target == "speed" and d.user_satisfaction
            ]
            cost_satisfaction = [
                d.user_satisfaction for d in user_history 
                if d.optimization_target == "cost" and d.user_satisfaction
            ]
            
            if speed_satisfaction and cost_satisfaction:
                avg_speed_sat = sum(speed_satisfaction) / len(speed_satisfaction)
                avg_cost_sat = sum(cost_satisfaction) / len(cost_satisfaction)
                
                if avg_speed_sat > avg_cost_sat + 1:
                    weights["speed_preference"] += 0.05
                elif avg_cost_sat > avg_speed_sat + 1:
                    weights["cost_preference"] += 0.05
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    async def _select_optimal_configuration(
        self,
        evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float],
        constraints: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Select the optimal configuration based on evaluations and preferences"""
        
        if not evaluations:
            return {"error": "No configurations available"}
        
        scored_evaluations = []
        
        for evaluation in evaluations:
            # Calculate weighted score
            speed_score = (60 - evaluation["estimated_time_minutes"]) / 60.0  # Normalize time to score
            speed_score = max(0, min(1, speed_score))
            
            cost_score = max(0, 1 - (evaluation["estimated_cost"] / 100.0))  # Lower cost = higher score
            
            efficiency_score = evaluation["efficiency_score"] / 10.0
            
            weighted_score = (
                preference_weights["speed_preference"] * speed_score +
                preference_weights["cost_preference"] * cost_score +
                preference_weights["efficiency_preference"] * efficiency_score
            )
            
            # Apply feasibility multiplier
            weighted_score *= evaluation["feasibility_score"]
            
            scored_evaluation = {
                **evaluation,
                "weighted_score": weighted_score,
                "speed_score": speed_score,
                "cost_score": cost_score,
                "confidence": min(1.0, weighted_score + 0.2)
            }
            
            scored_evaluations.append(scored_evaluation)
        
        # Sort by weighted score
        scored_evaluations.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        optimal = scored_evaluations[0]
        optimal["reasoning"] = [
            f"Selected based on weighted score: {optimal['weighted_score']:.2f}",
            f"Speed score: {optimal['speed_score']:.2f}, Cost score: {optimal['cost_score']:.2f}",
            f"Estimated time: {optimal['estimated_time_minutes']:.1f} minutes",
            f"Estimated cost: ${optimal['estimated_cost']:.2f}"
        ] + optimal.get("reasoning", [])
        
        return optimal
    
    async def _generate_alternatives(
        self,
        evaluations: List[Dict[str, Any]],
        optimal_config: Dict[str, Any],
        preference_weights: Dict[str, float]
    ) -> List[Dict[str, Any]]:
        """Generate alternative configurations"""
        
        alternatives = []
        
        # Sort evaluations by weighted score
        sorted_evals = sorted(evaluations, key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        # Skip the optimal (first) and take next 3
        for eval_config in sorted_evals[1:4]:
            alternative = {
                "name": eval_config["configuration"]["name"],
                "optimization_target": eval_config["configuration"]["optimization_target"],
                "estimated_time": eval_config["estimated_time_minutes"],
                "estimated_cost": eval_config["estimated_cost"],
                "efficiency_score": eval_config["efficiency_score"],
                "trade_offs": await self._compare_with_optimal(eval_config, optimal_config),
                "when_to_choose": await self._suggest_when_to_choose(eval_config)
            }
            alternatives.append(alternative)
        
        return alternatives
    
    async def _store_speed_cost_decision(
        self,
        user_id: uuid.UUID,
        task: Dict[str, Any],
        optimal_config: Dict[str, Any],
        all_evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float]
    ):
        """Store the speed vs cost decision for learning"""
        
        decision = SpeedCostDecision(
            user_id=user_id,
            task_name=task.get("name", "Unknown"),
            task_metadata=task,
            optimization_target=optimal_config["configuration"]["optimization_target"],
            selected_configuration=optimal_config,
            alternative_configurations=all_evaluations[:5],
            estimated_execution_time=optimal_config["estimated_time_minutes"],
            estimated_cost=Decimal(str(optimal_config["estimated_cost"])),
            preference_weights=preference_weights,
            decision_date=datetime.utcnow()
        )
        
        self.db.add(decision)
        await self.db.commit()
    
    async def _analyze_prediction_accuracy(
        self,
        decision: SpeedCostDecision,
        actual_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze how accurate the predictions were"""
        
        analysis = {}
        
        # Time prediction accuracy
        if decision.actual_execution_time and decision.estimated_execution_time:
            time_error = abs(decision.actual_execution_time - decision.estimated_execution_time)
            time_error_pct = (time_error / decision.estimated_execution_time) * 100
            analysis["time_error_pct"] = time_error_pct
            analysis["time_accurate"] = time_error_pct < 20  # Within 20%
        
        # Cost prediction accuracy
        if decision.actual_cost and decision.estimated_cost:
            cost_error = abs(float(decision.actual_cost) - float(decision.estimated_cost))
            cost_error_pct = (cost_error / float(decision.estimated_cost)) * 100
            analysis["cost_error_pct"] = cost_error_pct
            analysis["cost_accurate"] = cost_error_pct < 15  # Within 15%
        
        # Overall accuracy
        accuracy_factors = []
        if "time_accurate" in analysis:
            accuracy_factors.append(1.0 if analysis["time_accurate"] else 0.0)
        if "cost_accurate" in analysis:
            accuracy_factors.append(1.0 if analysis["cost_accurate"] else 0.0)
        if decision.user_satisfaction:
            accuracy_factors.append(1.0 if decision.user_satisfaction >= 7 else 0.0)
        
        if accuracy_factors:
            analysis["overall_accuracy"] = sum(accuracy_factors) / len(accuracy_factors)
        else:
            analysis["overall_accuracy"] = 0.5
        
        analysis["will_improve_predictions"] = analysis["overall_accuracy"] > 0.6
        
        return analysis
    
    async def _update_speed_cost_models(
        self,
        user_id: uuid.UUID,
        decision: SpeedCostDecision,
        accuracy_analysis: Dict[str, Any]
    ):
        """Update speed vs cost models with outcome data"""
        
        # Log learning opportunity
        logger.info(f"Updating speed/cost models for user {user_id}, accuracy: {accuracy_analysis.get('overall_accuracy', 0)}")
        
        # In production, this would update ML models with the outcome data
        # For now, we'll store the learning data for future model training
        pass
    
    async def _analyze_speed_cost_trends(
        self,
        decisions: List[SpeedCostDecision]
    ) -> Dict[str, Any]:
        """Analyze trends in speed vs cost decisions"""
        
        if len(decisions) < 5:
            return {"insufficient_data": True}
        
        # Sort by date
        sorted_decisions = sorted(decisions, key=lambda x: x.decision_date)
        
        # Analyze optimization target trends
        recent_decisions = sorted_decisions[-10:]
        earlier_decisions = sorted_decisions[:-10] if len(sorted_decisions) > 10 else []
        
        recent_speed = len([d for d in recent_decisions if d.optimization_target == "speed"])
        recent_cost = len([d for d in recent_decisions if d.optimization_target == "cost"])
        
        if earlier_decisions:
            earlier_speed = len([d for d in earlier_decisions if d.optimization_target == "speed"])
            earlier_cost = len([d for d in earlier_decisions if d.optimization_target == "cost"])
            
            if recent_speed > earlier_speed:
                trend = "increasing_speed_preference"
            elif recent_cost > earlier_cost:
                trend = "increasing_cost_preference"
            else:
                trend = "stable_preferences"
        else:
            trend = "insufficient_history"
        
        # Cost efficiency trends
        recent_efficiency = [
            float(d.selected_configuration.get("efficiency_score", 0)) 
            for d in recent_decisions if d.selected_configuration
        ]
        avg_recent_efficiency = sum(recent_efficiency) / len(recent_efficiency) if recent_efficiency else 0
        
        return {
            "preference_trend": trend,
            "recent_speed_preference": recent_speed / len(recent_decisions),
            "recent_cost_preference": recent_cost / len(recent_decisions),
            "average_efficiency": avg_recent_efficiency,
            "trend_confidence": 0.7 if len(decisions) >= 15 else 0.5
        }
    
    async def _generate_optimization_recommendations(
        self,
        user_id: uuid.UUID,
        decisions: List[SpeedCostDecision]
    ) -> List[str]:
        """Generate recommendations to improve speed vs cost optimization"""
        
        recommendations = []
        
        # Analyze satisfaction scores
        satisfactions = [d.user_satisfaction for d in decisions if d.user_satisfaction]
        if satisfactions:
            avg_satisfaction = sum(satisfactions) / len(satisfactions)
            if avg_satisfaction < 6:
                recommendations.append("Consider adjusting speed vs cost preferences")
                recommendations.append("Review task complexity estimates for better predictions")
        
        # Analyze cost overruns
        cost_overruns = []
        for d in decisions:
            if d.actual_cost and d.estimated_cost:
                overrun = (float(d.actual_cost) - float(d.estimated_cost)) / float(d.estimated_cost)
                if overrun > 0.2:  # 20% over budget
                    cost_overruns.append(overrun)
        
        if len(cost_overruns) > len(decisions) * 0.3:  # More than 30% of decisions
            recommendations.append("Improve cost estimation accuracy")
            recommendations.append("Consider adding buffer to cost estimates")
        
        # Analyze execution time accuracy
        time_errors = []
        for d in decisions:
            if d.actual_execution_time and d.estimated_execution_time:
                error = abs(d.actual_execution_time - d.estimated_execution_time) / d.estimated_execution_time
                time_errors.append(error)
        
        if time_errors and sum(time_errors) / len(time_errors) > 0.25:  # 25% average error
            recommendations.append("Refine execution time predictions")
            recommendations.append("Consider task complexity factors more carefully")
        
        # Optimization target analysis
        speed_decisions = len([d for d in decisions if d.optimization_target == "speed"])
        cost_decisions = len([d for d in decisions if d.optimization_target == "cost"])
        
        if speed_decisions > cost_decisions * 3:
            recommendations.append("Consider cost-optimized alternatives to reduce expenses")
        elif cost_decisions > speed_decisions * 3:
            recommendations.append("Consider speed-optimized options for time-sensitive tasks")
        
        if not recommendations:
            recommendations.append("Optimization patterns look good, continue current approach")
        
        return recommendations
    
    # Additional helper methods for cloud instances, cost calculations, etc.
    
    async def _get_cloud_instance_options(self, task_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get available cloud instance options for the task"""
        
        instances = []
        
        # General purpose
        instances.append({
            "type": "general_purpose_small",
            "specs": {"cpu_cores": 2, "memory_gb": 8, "gpu_enabled": False},
            "cost_per_minute": 0.01
        })
        
        instances.append({
            "type": "general_purpose_large",
            "specs": {"cpu_cores": 8, "memory_gb": 32, "gpu_enabled": False},
            "cost_per_minute": 0.04
        })
        
        # Compute optimized
        if task_analysis["cpu_intensive"] or task_analysis["resource_intensity"] > 6:
            instances.append({
                "type": "compute_optimized",
                "specs": {"cpu_cores": 16, "memory_gb": 32, "gpu_enabled": False},
                "cost_per_minute": 0.06
            })
        
        # Memory optimized
        if task_analysis["memory_intensive"] or task_analysis["data_size_gb"] > 10:
            instances.append({
                "type": "memory_optimized",
                "specs": {"cpu_cores": 8, "memory_gb": 64, "gpu_enabled": False},
                "cost_per_minute": 0.08
            })
        
        # GPU instances
        if task_analysis.get("gpu_required", False):
            instances.append({
                "type": "gpu_instance",
                "specs": {"cpu_cores": 8, "memory_gb": 32, "gpu_enabled": True},
                "cost_per_minute": 0.15
            })
        
        return instances
    
    async def _filter_options_by_constraints(
        self,
        options: List[Dict[str, Any]],
        constraints: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter configuration options based on constraints"""
        
        filtered_options = []
        
        for option in options:
            meets_constraints = True
            
            # Budget constraint
            if "max_cost" in constraints:
                # We'll estimate cost later, for now assume it meets constraint
                pass
            
            # Time constraint
            if "max_time_minutes" in constraints:
                # We'll estimate time later, for now assume it meets constraint
                pass
            
            # Execution type constraints
            if "allowed_execution_types" in constraints:
                if option["execution_type"] not in constraints["allowed_execution_types"]:
                    meets_constraints = False
            
            # Resource constraints
            if "min_cpu_cores" in constraints:
                if option["resource_allocation"]["cpu_cores"] < constraints["min_cpu_cores"]:
                    meets_constraints = False
            
            if meets_constraints:
                filtered_options.append(option)
        
        return filtered_options
    
    async def _estimate_base_execution_time(self, task_analysis: Dict[str, Any]) -> float:
        """Estimate base execution time for the task"""
        
        # Simple model based on task characteristics
        base_time = 30.0  # 30 minutes base
        
        # Adjust for complexity
        complexity_multipliers = {"low": 0.5, "medium": 1.0, "high": 2.0}
        base_time *= complexity_multipliers.get(task_analysis["complexity"], 1.0)
        
        # Adjust for resource intensity
        base_time *= (task_analysis["resource_intensity"] / 5.0)
        
        # Adjust for data size
        if task_analysis["data_size_gb"] > 1:
            base_time *= (1 + math.log10(task_analysis["data_size_gb"]))
        
        return max(1.0, base_time)
    
    async def _calculate_device_performance_multiplier(
        self,
        device_id: str,
        task_analysis: Dict[str, Any]
    ) -> float:
        """Calculate performance multiplier for a specific device"""
        
        # Get device profile
        result = await self.db.execute(
            select(DeviceProfile).where(DeviceProfile.id == uuid.UUID(device_id))
        )
        device = result.scalar_one_or_none()
        
        if not device:
            return 2.0  # Conservative estimate
        
        # Calculate multiplier based on device capabilities
        multiplier = 1.0
        
        # CPU factor
        if device.cpu_cores >= 8:
            multiplier *= 0.7  # Faster with more cores
        elif device.cpu_cores >= 4:
            multiplier *= 0.9
        else:
            multiplier *= 1.3  # Slower with fewer cores
        
        # Memory factor
        if float(device.memory_gb) >= 16:
            multiplier *= 0.9  # Faster with more memory
        elif float(device.memory_gb) < 8:
            multiplier *= 1.2  # Slower with less memory
        
        # GPU factor
        if device.has_gpu and task_analysis.get("gpu_beneficial", False):
            multiplier *= 0.6  # Much faster with GPU
        
        return max(0.3, multiplier)
    
    async def _calculate_local_cost(self, config: Dict[str, Any], execution_time_minutes: float) -> float:
        """Calculate cost of local execution"""
        
        # Simple cost model - primarily electricity
        power_consumption_watts = 150  # Base consumption
        
        if config["optimization_target"] == "speed":
            power_consumption_watts *= 1.5  # Higher power for speed
        
        if config.get("resource_allocation", {}).get("gpu_enabled", False):
            power_consumption_watts += 200  # GPU power
        
        execution_time_hours = execution_time_minutes / 60.0
        energy_kwh = (power_consumption_watts * execution_time_hours) / 1000.0
        
        # $0.12 per kWh electricity cost
        electricity_cost = energy_kwh * 0.12
        
        # Add depreciation cost
        depreciation_cost = execution_time_hours * 0.02  # $0.02 per hour
        
        return electricity_cost + depreciation_cost
    
    async def _calculate_cloud_cost(self, config: Dict[str, Any], execution_time_minutes: float) -> float:
        """Calculate cost of cloud execution"""
        
        # Get instance type cost
        instance_costs = {
            "general_purpose_small": 0.01,
            "general_purpose_large": 0.04,
            "compute_optimized": 0.06,
            "memory_optimized": 0.08,
            "gpu_instance": 0.15
        }
        
        cost_per_minute = instance_costs.get(config.get("instance_type", "general_purpose_small"), 0.02)
        
        # Speed optimization may use more expensive instances
        if config["optimization_target"] == "speed":
            cost_per_minute *= 1.3
        
        base_cost = cost_per_minute * execution_time_minutes
        
        # Add storage and network costs
        storage_cost = 0.5  # Fixed storage cost
        network_cost = base_cost * 0.1  # 10% of compute for network
        
        return base_cost + storage_cost + network_cost
    
    async def _compare_with_optimal(
        self,
        alternative: Dict[str, Any],
        optimal: Dict[str, Any]
    ) -> List[str]:
        """Compare alternative configuration with optimal"""
        
        comparisons = []
        
        time_diff = alternative["estimated_time_minutes"] - optimal["estimated_time_minutes"]
        cost_diff = alternative["estimated_cost"] - optimal["estimated_cost"]
        
        if time_diff > 0:
            comparisons.append(f"{time_diff:.1f} minutes slower")
        elif time_diff < 0:
            comparisons.append(f"{abs(time_diff):.1f} minutes faster")
        
        if cost_diff > 0:
            comparisons.append(f"${cost_diff:.2f} more expensive")
        elif cost_diff < 0:
            comparisons.append(f"${abs(cost_diff):.2f} cheaper")
        
        if alternative["efficiency_score"] > optimal["efficiency_score"]:
            comparisons.append("More efficient")
        elif alternative["efficiency_score"] < optimal["efficiency_score"]:
            comparisons.append("Less efficient")
        
        return comparisons
    
    async def _suggest_when_to_choose(self, config: Dict[str, Any]) -> str:
        """Suggest when to choose this configuration"""
        
        target = config["configuration"]["optimization_target"]
        
        if target == "speed":
            return "Choose when time is critical and budget allows"
        elif target == "cost":
            return "Choose when budget is tight and time is flexible"
        else:
            return "Choose for balanced performance and cost"
    
    async def _get_task_type_history(
        self,
        user_id: uuid.UUID,
        task_type: str
    ) -> List[SpeedCostDecision]:
        """Get user's history for a specific task type"""
        
        result = await self.db.execute(
            select(SpeedCostDecision).where(
                and_(
                    SpeedCostDecision.user_id == user_id,
                    SpeedCostDecision.task_metadata.has_key("type"),  # Check if key exists
                    SpeedCostDecision.task_metadata["type"].astext == task_type
                )
            ).limit(20)
        )
        return result.scalars().all()
    
    async def _analyze_user_preferences(
        self,
        user_id: uuid.UUID,
        task_history: List[SpeedCostDecision]
    ) -> Dict[str, Any]:
        """Analyze user preferences from task history"""
        
        if not task_history:
            return {
                "speed_preference": 0.4,
                "cost_preference": 0.4,
                "efficiency_preference": 0.2,
                "confidence": 0.3
            }
        
        # Analyze historical choices
        speed_choices = len([d for d in task_history if d.optimization_target == "speed"])
        cost_choices = len([d for d in task_history if d.optimization_target == "cost"])
        balanced_choices = len([d for d in task_history if d.optimization_target == "balanced"])
        
        total_choices = len(task_history)
        
        return {
            "speed_preference": speed_choices / total_choices,
            "cost_preference": cost_choices / total_choices,
            "efficiency_preference": balanced_choices / total_choices,
            "confidence": min(1.0, total_choices / 10.0),  # Higher confidence with more history
            "historical_satisfaction": sum(
                d.user_satisfaction for d in task_history if d.user_satisfaction
            ) / len([d for d in task_history if d.user_satisfaction]) if any(d.user_satisfaction for d in task_history) else 7
        }
    
    async def _recommend_budget_optimized_settings(
        self,
        user_id: uuid.UUID,
        task_type: str,
        budget_constraint: Decimal,
        preference_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend settings optimized for budget constraint"""
        
        return {
            "name": "Budget Optimized",
            "optimization_target": "cost",
            "execution_type": "local",  # Prefer local for cost savings
            "resource_allocation": "efficient",
            "expected_cost": min(float(budget_constraint), float(budget_constraint) * 0.8),
            "expected_time": "flexible",
            "confidence": 0.8,
            "reasoning": ["Optimized to stay within budget", "Uses cost-efficient resources"],
            "expected_outcomes": {
                "cost_savings": float(budget_constraint) * 0.2,
                "time_increase": "10-20%"
            }
        }
    
    async def _recommend_time_optimized_settings(
        self,
        user_id: uuid.UUID,
        task_type: str,
        time_constraint: int,
        preference_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend settings optimized for time constraint"""
        
        return {
            "name": "Time Optimized",
            "optimization_target": "speed",
            "execution_type": "cloud",  # Prefer cloud for speed
            "resource_allocation": "maximum",
            "expected_time": min(time_constraint, int(time_constraint * 0.8)),
            "expected_cost": "flexible",
            "confidence": 0.8,
            "reasoning": ["Optimized to meet time deadline", "Uses high-performance resources"],
            "expected_outcomes": {
                "time_savings": f"{time_constraint * 0.2:.0f} minutes",
                "cost_increase": "20-40%"
            }
        }
    
    async def _recommend_balanced_settings(
        self,
        user_id: uuid.UUID,
        task_type: str,
        preference_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend balanced settings"""
        
        return {
            "name": "Balanced",
            "optimization_target": "balanced",
            "execution_type": "hybrid" if preference_analysis["efficiency_preference"] > 0.3 else "cloud",
            "resource_allocation": "balanced",
            "expected_cost": "moderate",
            "expected_time": "moderate",
            "confidence": 0.9,
            "reasoning": ["Balanced approach based on user history", "Good cost-time trade-off"],
            "expected_outcomes": {
                "cost_efficiency": "Good",
                "time_efficiency": "Good"
            }
        }
    
    async def _select_best_recommendation(
        self,
        recommendations: List[Dict[str, Any]],
        preference_analysis: Dict[str, Any],
        budget_constraint: Optional[Decimal],
        time_constraint: Optional[int]
    ) -> Dict[str, Any]:
        """Select the best recommendation based on constraints and preferences"""
        
        # Score each recommendation
        scored_recommendations = []
        
        for rec in recommendations:
            score = 0.0
            
            # Preference alignment
            if rec["optimization_target"] == "cost":
                score += preference_analysis["cost_preference"] * 2
            elif rec["optimization_target"] == "speed":
                score += preference_analysis["speed_preference"] * 2
            else:  # balanced
                score += preference_analysis["efficiency_preference"] * 2
            
            # Constraint satisfaction
            if budget_constraint and "expected_cost" in rec:
                if isinstance(rec["expected_cost"], (int, float)) and rec["expected_cost"] <= float(budget_constraint):
                    score += 1.0
                elif rec["expected_cost"] == "flexible":
                    score += 0.5
            
            if time_constraint and "expected_time" in rec:
                if isinstance(rec["expected_time"], (int, float)) and rec["expected_time"] <= time_constraint:
                    score += 1.0
                elif rec["expected_time"] == "flexible":
                    score += 0.5
            
            # Confidence boost
            score += rec.get("confidence", 0.5)
            
            scored_recommendations.append((score, rec))
        
        # Return highest scoring recommendation
        scored_recommendations.sort(key=lambda x: x[0], reverse=True)
        return scored_recommendations[0][1]