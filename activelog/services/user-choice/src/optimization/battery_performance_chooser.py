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
    User, UserChoice, ChoiceType, DeviceProfile,
    DeviceType, BatteryPerformanceDecision, PowerProfile
)

logger = logging.getLogger(__name__)

class BatteryVsPerformanceChooser:
    """Intelligent chooser for battery vs performance trade-offs on mobile/portable devices"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def choose_battery_performance_profile(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        task: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        user_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Choose optimal battery vs performance profile for a task"""
        
        try:
            # Get device information
            device = await self._get_device_profile(device_id)
            if not device:
                return {"success": False, "error": "Device not found"}
            
            # Check if device is battery-powered
            if device.device_type not in [DeviceType.LAPTOP, DeviceType.MOBILE]:
                return {
                    "success": False, 
                    "error": "Battery optimization only applicable to laptops and mobile devices"
                }
            
            # Get current battery status and context
            battery_context = await self._get_battery_context(device_id, context)
            
            # Analyze task requirements
            task_analysis = await self._analyze_task_power_requirements(task)
            
            # Get user's historical preferences
            user_history = await self._get_battery_performance_history(user_id, device_id)
            
            # Generate profile options
            profile_options = await self._generate_power_profiles(
                device, task_analysis, battery_context
            )
            
            # Evaluate each profile option
            evaluations = []
            for profile in profile_options:
                evaluation = await self._evaluate_power_profile(
                    device, task_analysis, profile, battery_context
                )
                evaluations.append(evaluation)
            
            # Apply user preferences and learning
            preference_weights = await self._calculate_battery_preference_weights(
                user_id, user_history, user_preferences, battery_context
            )
            
            # Select optimal profile
            optimal_profile = await self._select_optimal_power_profile(
                evaluations, preference_weights, battery_context, task_analysis
            )
            
            # Generate recommendations and alternatives
            alternatives = await self._generate_power_profile_alternatives(
                evaluations, optimal_profile
            )
            
            recommendations = await self._generate_battery_recommendations(
                device, battery_context, optimal_profile
            )
            
            # Store decision for learning
            await self._store_battery_performance_decision(
                user_id, device_id, task, optimal_profile, evaluations, preference_weights
            )
            
            return {
                "user_id": str(user_id),
                "device_id": str(device_id),
                "task_name": task.get("name", "Unknown"),
                "selected_profile": optimal_profile,
                "battery_impact_analysis": {
                    "estimated_battery_life_hours": optimal_profile["estimated_battery_hours"],
                    "estimated_completion_time": optimal_profile["estimated_completion_minutes"],
                    "power_consumption_watts": optimal_profile["power_consumption"],
                    "performance_level": optimal_profile["performance_level"],
                    "thermal_impact": optimal_profile["thermal_impact"]
                },
                "profile_options": evaluations[:4],  # Top 4 options
                "alternatives": alternatives,
                "battery_recommendations": recommendations,
                "current_battery_level": battery_context.get("battery_level", "unknown"),
                "charging_status": battery_context.get("charging", False),
                "confidence_score": optimal_profile["confidence"],
                "optimization_reasoning": optimal_profile["reasoning"],
                "decision_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to choose battery vs performance profile: {e}")
            raise
    
    async def evaluate_battery_performance_outcome(
        self,
        decision_id: uuid.UUID,
        actual_metrics: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Evaluate the outcome of a battery vs performance decision"""
        
        try:
            # Get the decision
            result = await self.db.execute(
                select(BatteryPerformanceDecision).where(BatteryPerformanceDecision.id == decision_id)
            )
            decision = result.scalar_one_or_none()
            
            if not decision:
                return {"success": False, "error": "Decision not found"}
            
            # Update with actual metrics
            decision.actual_battery_consumption = actual_metrics.get("battery_consumed_percentage")
            decision.actual_completion_time = actual_metrics.get("completion_time_minutes")
            decision.actual_performance_score = actual_metrics.get("performance_score")
            decision.thermal_throttling_occurred = actual_metrics.get("thermal_throttling", False)
            decision.user_satisfaction = user_feedback.get("satisfaction") if user_feedback else None
            decision.outcome_recorded = True
            decision.outcome_timestamp = datetime.utcnow()
            
            # Calculate prediction accuracy
            accuracy_analysis = await self._analyze_battery_prediction_accuracy(decision, actual_metrics)
            
            # Update learning models
            await self._update_battery_performance_models(decision.user_id, decision, accuracy_analysis)
            
            await self.db.commit()
            
            return {
                "success": True,
                "decision_id": str(decision_id),
                "accuracy_analysis": accuracy_analysis,
                "prediction_quality": {
                    "battery_prediction_error": accuracy_analysis.get("battery_error_pct", 0),
                    "time_prediction_error": accuracy_analysis.get("time_error_pct", 0),
                    "overall_accuracy": accuracy_analysis.get("overall_accuracy", 0)
                },
                "learning_updates": "Battery performance models updated",
                "thermal_analysis": {
                    "throttling_occurred": decision.thermal_throttling_occurred,
                    "throttling_predicted": decision.selected_profile.get("thermal_risk", False)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to evaluate battery performance outcome: {e}")
            raise
    
    async def get_battery_performance_analytics(
        self,
        user_id: uuid.UUID,
        device_id: Optional[uuid.UUID] = None,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get analytics on user's battery vs performance decisions"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Build query
            query = select(BatteryPerformanceDecision).where(
                and_(
                    BatteryPerformanceDecision.user_id == user_id,
                    BatteryPerformanceDecision.decision_date >= start_date
                )
            )
            
            if device_id:
                query = query.where(BatteryPerformanceDecision.device_id == device_id)
            
            result = await self.db.execute(query.order_by(BatteryPerformanceDecision.decision_date.desc()))
            decisions = result.scalars().all()
            
            if not decisions:
                return {
                    "user_id": str(user_id),
                    "device_id": str(device_id) if device_id else "all_devices",
                    "period_days": period_days,
                    "message": "No battery vs performance decisions found for this period"
                }
            
            # Analyze decisions
            total_decisions = len(decisions)
            battery_optimized = len([d for d in decisions if d.optimization_target == "battery"])
            performance_optimized = len([d for d in decisions if d.optimization_target == "performance"])
            balanced_decisions = len([d for d in decisions if d.optimization_target == "balanced"])
            
            # Battery consumption analysis
            battery_consumptions = [
                d.actual_battery_consumption for d in decisions 
                if d.actual_battery_consumption is not None
            ]
            avg_battery_consumption = sum(battery_consumptions) / len(battery_consumptions) if battery_consumptions else 0
            
            # Performance analysis
            performance_scores = [
                d.actual_performance_score for d in decisions 
                if d.actual_performance_score is not None
            ]
            avg_performance = sum(performance_scores) / len(performance_scores) if performance_scores else 0
            
            # Thermal analysis
            thermal_events = len([d for d in decisions if d.thermal_throttling_occurred])
            
            # Satisfaction analysis
            satisfaction_scores = [d.user_satisfaction for d in decisions if d.user_satisfaction]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            # Device-specific analysis
            device_breakdown = {}
            for decision in decisions:
                device_id_str = str(decision.device_id)
                if device_id_str not in device_breakdown:
                    device_breakdown[device_id_str] = {
                        "total_decisions": 0,
                        "battery_optimized": 0,
                        "performance_optimized": 0,
                        "avg_battery_consumption": 0
                    }
                
                device_breakdown[device_id_str]["total_decisions"] += 1
                if decision.optimization_target == "battery":
                    device_breakdown[device_id_str]["battery_optimized"] += 1
                elif decision.optimization_target == "performance":
                    device_breakdown[device_id_str]["performance_optimized"] += 1
            
            # Usage patterns
            usage_patterns = await self._analyze_battery_usage_patterns(decisions)
            
            return {
                "user_id": str(user_id),
                "device_id": str(device_id) if device_id else "all_devices",
                "period_days": period_days,
                "decision_summary": {
                    "total_decisions": total_decisions,
                    "battery_optimized_count": battery_optimized,
                    "performance_optimized_count": performance_optimized,
                    "balanced_count": balanced_decisions,
                    "dominant_preference": await self._determine_dominant_preference(decisions)
                },
                "battery_analysis": {
                    "average_battery_consumption_percent": round(avg_battery_consumption, 2),
                    "thermal_throttling_events": thermal_events,
                    "thermal_throttling_rate": (thermal_events / total_decisions) * 100,
                    "battery_efficiency_trend": usage_patterns.get("battery_trend", "stable")
                },
                "performance_analysis": {
                    "average_performance_score": round(avg_performance, 2),
                    "performance_trend": usage_patterns.get("performance_trend", "stable"),
                    "high_performance_usage_rate": usage_patterns.get("high_performance_rate", 0)
                },
                "satisfaction_metrics": {
                    "average_satisfaction": round(avg_satisfaction, 2),
                    "satisfaction_trend": usage_patterns.get("satisfaction_trend", "stable"),
                    "total_feedback_responses": len(satisfaction_scores)
                },
                "device_breakdown": device_breakdown,
                "usage_patterns": usage_patterns,
                "optimization_recommendations": await self._generate_battery_optimization_recommendations(
                    user_id, decisions
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get battery performance analytics: {e}")
            raise
    
    async def recommend_power_profile_for_situation(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        situation: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Recommend power profile for a specific situation"""
        
        try:
            # Get device information
            device = await self._get_device_profile(device_id)
            if not device:
                return {"success": False, "error": "Device not found"}
            
            # Analyze situation
            situation_analysis = await self._analyze_situation(situation)
            
            # Get user's preferences for similar situations
            similar_situations = await self._get_similar_situation_history(
                user_id, device_id, situation_analysis
            )
            
            # Generate recommendation based on situation
            if situation_analysis["battery_critical"]:
                # Battery saver mode
                recommendation = {
                    "profile_name": "Battery Saver",
                    "cpu_frequency": "low",
                    "gpu_frequency": "minimal",
                    "display_brightness": "reduced",
                    "background_processes": "limited",
                    "network_optimization": "enabled",
                    "expected_battery_extension": "50-70%",
                    "performance_impact": "30-50% reduction",
                    "reasoning": ["Battery level critical", "Maximize remaining usage time"]
                }
            elif situation_analysis["high_performance_needed"]:
                # Performance mode
                recommendation = {
                    "profile_name": "High Performance",
                    "cpu_frequency": "maximum",
                    "gpu_frequency": "high",
                    "display_brightness": "optimal",
                    "background_processes": "unrestricted",
                    "network_optimization": "disabled",
                    "expected_battery_drain": "150-200% of normal",
                    "performance_boost": "40-60%",
                    "reasoning": ["High performance requirements", "Power source likely available"]
                }
            elif situation_analysis["traveling"]:
                # Travel mode
                recommendation = {
                    "profile_name": "Travel Optimized",
                    "cpu_frequency": "adaptive",
                    "gpu_frequency": "moderate",
                    "display_brightness": "auto",
                    "background_processes": "essential_only",
                    "network_optimization": "adaptive",
                    "expected_battery_life": "Extended by 20-30%",
                    "performance_impact": "Minimal during light usage",
                    "reasoning": ["Travel scenario detected", "Balance battery life with usability"]
                }
            else:
                # Balanced mode
                recommendation = {
                    "profile_name": "Balanced",
                    "cpu_frequency": "adaptive",
                    "gpu_frequency": "adaptive",
                    "display_brightness": "auto",
                    "background_processes": "managed",
                    "network_optimization": "smart",
                    "expected_battery_life": "Standard",
                    "performance_impact": "None",
                    "reasoning": ["Standard usage scenario", "Optimal balance of battery and performance"]
                }
            
            # Add user-specific customizations
            if similar_situations:
                customizations = await self._apply_user_customizations(
                    recommendation, similar_situations
                )
                recommendation.update(customizations)
            
            return {
                "user_id": str(user_id),
                "device_id": str(device_id),
                "situation": situation_analysis,
                "recommended_profile": recommendation,
                "confidence_score": await self._calculate_recommendation_confidence(
                    user_id, device_id, situation_analysis, similar_situations
                ),
                "alternative_profiles": await self._generate_situation_alternatives(
                    situation_analysis, recommendation
                ),
                "implementation_steps": await self._generate_implementation_steps(
                    device, recommendation
                ),
                "recommendation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to recommend power profile: {e}")
            raise
    
    # Helper methods
    
    async def _get_device_profile(self, device_id: uuid.UUID) -> Optional[DeviceProfile]:
        """Get device profile by ID"""
        result = await self.db.execute(
            select(DeviceProfile).where(DeviceProfile.id == device_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_battery_context(
        self,
        device_id: uuid.UUID,
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Get current battery and power context"""
        
        battery_context = {
            "battery_level": 100,  # Default values
            "charging": False,
            "power_source": "battery",
            "estimated_remaining_hours": 8,
            "thermal_state": "normal"
        }
        
        # Update with provided context
        if context:
            battery_context.update({
                "battery_level": context.get("battery_level", battery_context["battery_level"]),
                "charging": context.get("charging", battery_context["charging"]),
                "power_source": context.get("power_source", battery_context["power_source"]),
                "estimated_remaining_hours": context.get("remaining_hours", battery_context["estimated_remaining_hours"]),
                "thermal_state": context.get("thermal_state", battery_context["thermal_state"])
            })
        
        # Classify battery situation
        battery_level = battery_context["battery_level"]
        if battery_level <= 10:
            battery_context["battery_status"] = "critical"
        elif battery_level <= 20:
            battery_context["battery_status"] = "low"
        elif battery_level <= 50:
            battery_context["battery_status"] = "moderate"
        else:
            battery_context["battery_status"] = "good"
        
        return battery_context
    
    async def _analyze_task_power_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze power requirements of the task"""
        
        analysis = {
            "name": task.get("name", "Unknown"),
            "type": task.get("type", "general"),
            "cpu_intensive": task.get("cpu_intensive", False),
            "gpu_intensive": task.get("gpu_intensive", False),
            "network_intensive": task.get("network_intensive", False),
            "display_intensive": task.get("display_intensive", False),
            "estimated_duration_minutes": task.get("duration_minutes", 30),
            "priority": task.get("priority", 5),  # 1-10 scale
            "interruptible": task.get("interruptible", True)
        }
        
        # Calculate power intensity score
        power_score = 1
        if analysis["cpu_intensive"]:
            power_score += 3
        if analysis["gpu_intensive"]:
            power_score += 4
        if analysis["network_intensive"]:
            power_score += 1
        if analysis["display_intensive"]:
            power_score += 2
        
        analysis["power_intensity"] = min(10, power_score)
        
        # Determine power profile requirements
        if analysis["power_intensity"] <= 3:
            analysis["power_profile"] = "low"
        elif analysis["power_intensity"] <= 6:
            analysis["power_profile"] = "moderate"
        else:
            analysis["power_profile"] = "high"
        
        return analysis
    
    async def _get_battery_performance_history(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID
    ) -> List[BatteryPerformanceDecision]:
        """Get user's battery vs performance decision history for the device"""
        
        lookback_date = datetime.utcnow() - timedelta(days=60)
        result = await self.db.execute(
            select(BatteryPerformanceDecision).where(
                and_(
                    BatteryPerformanceDecision.user_id == user_id,
                    BatteryPerformanceDecision.device_id == device_id,
                    BatteryPerformanceDecision.decision_date >= lookback_date
                )
            ).order_by(BatteryPerformanceDecision.decision_date.desc())
        )
        return result.scalars().all()
    
    async def _generate_power_profiles(
        self,
        device: DeviceProfile,
        task_analysis: Dict[str, Any],
        battery_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate power profile options"""
        
        profiles = []
        
        # Battery Saver Profile
        profiles.append({
            "name": "Battery Saver",
            "optimization_target": "battery",
            "cpu_frequency_percent": 50,
            "gpu_frequency_percent": 30,
            "display_brightness_percent": 60,
            "background_apps": "minimal",
            "network_optimization": True,
            "estimated_power_reduction": 60
        })
        
        # Balanced Profile
        profiles.append({
            "name": "Balanced",
            "optimization_target": "balanced",
            "cpu_frequency_percent": 75,
            "gpu_frequency_percent": 70,
            "display_brightness_percent": 80,
            "background_apps": "managed",
            "network_optimization": True,
            "estimated_power_reduction": 25
        })
        
        # Performance Profile
        profiles.append({
            "name": "Performance",
            "optimization_target": "performance",
            "cpu_frequency_percent": 100,
            "gpu_frequency_percent": 100,
            "display_brightness_percent": 100,
            "background_apps": "unrestricted",
            "network_optimization": False,
            "estimated_power_reduction": 0
        })
        
        # Adaptive Profile
        profiles.append({
            "name": "Adaptive",
            "optimization_target": "adaptive",
            "cpu_frequency_percent": 85,
            "gpu_frequency_percent": 80,
            "display_brightness_percent": 90,
            "background_apps": "smart",
            "network_optimization": True,
            "estimated_power_reduction": 15
        })
        
        # Task-specific optimizations
        if task_analysis["cpu_intensive"]:
            profiles.append({
                "name": "CPU Optimized",
                "optimization_target": "performance",
                "cpu_frequency_percent": 100,
                "gpu_frequency_percent": 50,  # Lower GPU to save power
                "display_brightness_percent": 70,
                "background_apps": "minimal",
                "network_optimization": True,
                "estimated_power_reduction": 20
            })
        
        if task_analysis["gpu_intensive"]:
            profiles.append({
                "name": "Graphics Optimized",
                "optimization_target": "performance",
                "cpu_frequency_percent": 80,
                "gpu_frequency_percent": 100,
                "display_brightness_percent": 100,
                "background_apps": "minimal",
                "network_optimization": True,
                "estimated_power_reduction": 10
            })
        
        return profiles
    
    async def _evaluate_power_profile(
        self,
        device: DeviceProfile,
        task_analysis: Dict[str, Any],
        profile: Dict[str, Any],
        battery_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate a power profile for the given task and context"""
        
        evaluation = {
            "profile": profile,
            "estimated_battery_hours": 0,
            "estimated_completion_minutes": 0,
            "power_consumption": 0,
            "performance_level": 0,
            "thermal_impact": "low",
            "feasibility_score": 1.0,
            "confidence": 0.8,
            "reasoning": [],
            "pros": [],
            "cons": []
        }
        
        # Calculate base power consumption (watts)
        base_power = {
            DeviceType.LAPTOP: 45,
            DeviceType.MOBILE: 5
        }.get(device.device_type, 30)
        
        # Adjust for profile settings
        cpu_multiplier = profile["cpu_frequency_percent"] / 100.0
        gpu_multiplier = profile["gpu_frequency_percent"] / 100.0
        display_multiplier = profile["display_brightness_percent"] / 100.0
        
        # Calculate power consumption
        cpu_power = base_power * 0.6 * cpu_multiplier  # 60% of base is CPU
        gpu_power = base_power * 0.3 * gpu_multiplier  # 30% is GPU/graphics
        display_power = base_power * 0.1 * display_multiplier  # 10% is display
        
        total_power = cpu_power + gpu_power + display_power
        
        # Apply power reduction from optimizations
        power_reduction = profile["estimated_power_reduction"] / 100.0
        evaluation["power_consumption"] = total_power * (1 - power_reduction)
        
        # Calculate estimated battery life
        if device.device_type == DeviceType.LAPTOP:
            battery_capacity_wh = 50  # Typical laptop battery
        else:  # Mobile
            battery_capacity_wh = 15   # Typical phone battery
        
        current_battery_wh = battery_capacity_wh * (battery_context["battery_level"] / 100.0)
        evaluation["estimated_battery_hours"] = current_battery_wh / evaluation["power_consumption"]
        
        # Calculate task completion time
        base_completion_time = task_analysis["estimated_duration_minutes"]
        
        # Performance impact on completion time
        performance_factor = (cpu_multiplier + gpu_multiplier) / 2.0
        if task_analysis["cpu_intensive"]:
            performance_factor = cpu_multiplier
        elif task_analysis["gpu_intensive"]:
            performance_factor = gpu_multiplier
        
        evaluation["estimated_completion_minutes"] = base_completion_time / max(0.3, performance_factor)
        
        # Calculate performance level (1-10 scale)
        evaluation["performance_level"] = performance_factor * 10
        
        # Thermal impact assessment
        if cpu_multiplier > 0.9 and gpu_multiplier > 0.9:
            evaluation["thermal_impact"] = "high"
            evaluation["reasoning"].append("High CPU and GPU usage may cause thermal throttling")
        elif cpu_multiplier > 0.8 or gpu_multiplier > 0.8:
            evaluation["thermal_impact"] = "moderate"
        else:
            evaluation["thermal_impact"] = "low"
        
        # Feasibility assessment
        task_completion_hours = evaluation["estimated_completion_minutes"] / 60.0
        if task_completion_hours > evaluation["estimated_battery_hours"]:
            evaluation["feasibility_score"] = evaluation["estimated_battery_hours"] / task_completion_hours
            evaluation["cons"].append("May not complete task before battery depletes")
        
        # Add profile-specific pros and cons
        if profile["optimization_target"] == "battery":
            evaluation["pros"].extend(["Maximizes battery life", "Reduces heat generation"])
            evaluation["cons"].extend(["Slower performance", "May impact user experience"])
        elif profile["optimization_target"] == "performance":
            evaluation["pros"].extend(["Maximum performance", "Fastest task completion"])
            evaluation["cons"].extend(["Higher power consumption", "Potential thermal issues"])
        else:  # balanced or adaptive
            evaluation["pros"].extend(["Good balance", "Adaptive to needs"])
            evaluation["cons"].extend(["May not be optimal for specific scenarios"])
        
        return evaluation
    
    async def _calculate_battery_preference_weights(
        self,
        user_id: uuid.UUID,
        user_history: List[BatteryPerformanceDecision],
        user_preferences: Optional[Dict[str, Any]],
        battery_context: Dict[str, Any]
    ) -> Dict[str, float]:
        """Calculate user preference weights for battery vs performance"""
        
        weights = {
            "battery_priority": 0.4,
            "performance_priority": 0.4,
            "convenience_priority": 0.2
        }
        
        # Adjust based on current battery status
        battery_status = battery_context["battery_status"]
        if battery_status == "critical":
            weights["battery_priority"] = 0.8
            weights["performance_priority"] = 0.1
            weights["convenience_priority"] = 0.1
        elif battery_status == "low":
            weights["battery_priority"] = 0.6
            weights["performance_priority"] = 0.3
            weights["convenience_priority"] = 0.1
        
        # Adjust based on charging status
        if battery_context["charging"]:
            weights["performance_priority"] += 0.2
            weights["battery_priority"] -= 0.1
            weights["convenience_priority"] -= 0.1
        
        # Adjust based on user preferences
        if user_preferences:
            if "battery_importance" in user_preferences:
                weights["battery_priority"] = float(user_preferences["battery_importance"])
            if "performance_importance" in user_preferences:
                weights["performance_priority"] = float(user_preferences["performance_importance"])
        
        # Adjust based on historical decisions
        if user_history:
            battery_decisions = len([d for d in user_history if d.optimization_target == "battery"])
            performance_decisions = len([d for d in user_history if d.optimization_target == "performance"])
            total_decisions = len(user_history)
            
            historical_battery_preference = battery_decisions / total_decisions
            historical_performance_preference = performance_decisions / total_decisions
            
            # Blend with historical preferences
            weights["battery_priority"] = (weights["battery_priority"] + historical_battery_preference) / 2
            weights["performance_priority"] = (weights["performance_priority"] + historical_performance_preference) / 2
        
        # Normalize weights
        total_weight = sum(weights.values())
        for key in weights:
            weights[key] /= total_weight
        
        return weights
    
    async def _select_optimal_power_profile(
        self,
        evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float],
        battery_context: Dict[str, Any],
        task_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Select the optimal power profile"""
        
        if not evaluations:
            return {"error": "No profiles available"}
        
        scored_evaluations = []
        
        for evaluation in evaluations:
            score = 0.0
            
            # Battery life score (higher is better)
            battery_hours = evaluation["estimated_battery_hours"]
            battery_score = min(1.0, battery_hours / 8.0)  # Normalize to 8 hours
            
            # Performance score (higher is better)
            performance_score = evaluation["performance_level"] / 10.0
            
            # Completion feasibility score
            completion_score = evaluation["feasibility_score"]
            
            # Weighted scoring
            weighted_score = (
                preference_weights["battery_priority"] * battery_score +
                preference_weights["performance_priority"] * performance_score +
                preference_weights["convenience_priority"] * completion_score
            )
            
            # Apply thermal penalty
            if evaluation["thermal_impact"] == "high":
                weighted_score *= 0.8
            elif evaluation["thermal_impact"] == "moderate":
                weighted_score *= 0.9
            
            # Apply feasibility multiplier
            weighted_score *= evaluation["feasibility_score"]
            
            # Priority boost for urgent tasks
            if task_analysis["priority"] >= 8:
                if evaluation["profile"]["optimization_target"] == "performance":
                    weighted_score *= 1.1
            
            scored_evaluation = {
                **evaluation,
                "weighted_score": weighted_score,
                "battery_score": battery_score,
                "performance_score": performance_score,
                "completion_score": completion_score
            }
            
            scored_evaluations.append(scored_evaluation)
        
        # Sort by weighted score
        scored_evaluations.sort(key=lambda x: x["weighted_score"], reverse=True)
        
        optimal = scored_evaluations[0]
        optimal["confidence"] = min(1.0, optimal["weighted_score"] + 0.2)
        optimal["reasoning"] = [
            f"Selected based on weighted score: {optimal['weighted_score']:.2f}",
            f"Battery life: {optimal['estimated_battery_hours']:.1f} hours",
            f"Performance level: {optimal['performance_level']:.1f}/10",
            f"Task completion: {optimal['estimated_completion_minutes']:.0f} minutes"
        ] + optimal.get("reasoning", [])
        
        return optimal
    
    async def _generate_power_profile_alternatives(
        self,
        evaluations: List[Dict[str, Any]],
        optimal_profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alternative power profiles"""
        
        alternatives = []
        
        # Sort evaluations by weighted score
        sorted_evals = sorted(evaluations, key=lambda x: x.get("weighted_score", 0), reverse=True)
        
        # Take alternatives (skip the optimal one)
        for eval_profile in sorted_evals[1:3]:
            alternative = {
                "name": eval_profile["profile"]["name"],
                "optimization_target": eval_profile["profile"]["optimization_target"],
                "estimated_battery_hours": eval_profile["estimated_battery_hours"],
                "estimated_completion_minutes": eval_profile["estimated_completion_minutes"],
                "performance_level": eval_profile["performance_level"],
                "trade_offs": await self._compare_profiles(eval_profile, optimal_profile),
                "when_to_choose": await self._suggest_when_to_choose_profile(eval_profile)
            }
            alternatives.append(alternative)
        
        return alternatives
    
    async def _generate_battery_recommendations(
        self,
        device: DeviceProfile,
        battery_context: Dict[str, Any],
        optimal_profile: Dict[str, Any]
    ) -> List[str]:
        """Generate battery-related recommendations"""
        
        recommendations = []
        
        battery_level = battery_context["battery_level"]
        
        if battery_level <= 20 and not battery_context["charging"]:
            recommendations.append("Consider connecting to power source for optimal performance")
            recommendations.append("Enable battery saver mode for extended usage")
        
        if optimal_profile["thermal_impact"] == "high":
            recommendations.append("Ensure good ventilation to prevent thermal throttling")
            recommendations.append("Consider taking breaks to let device cool down")
        
        if optimal_profile["performance_level"] < 7:
            recommendations.append("Performance is reduced to conserve battery")
            recommendations.append("Connect to power for full performance if needed")
        
        if battery_context["thermal_state"] != "normal":
            recommendations.append("Device thermal state is elevated - performance may be limited")
        
        return recommendations
    
    async def _store_battery_performance_decision(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        task: Dict[str, Any],
        optimal_profile: Dict[str, Any],
        all_evaluations: List[Dict[str, Any]],
        preference_weights: Dict[str, float]
    ):
        """Store the battery vs performance decision"""
        
        decision = BatteryPerformanceDecision(
            user_id=user_id,
            device_id=device_id,
            task_name=task.get("name", "Unknown"),
            task_metadata=task,
            optimization_target=optimal_profile["profile"]["optimization_target"],
            selected_profile=optimal_profile,
            alternative_profiles=all_evaluations[:3],
            estimated_battery_consumption=100 - (optimal_profile["estimated_battery_hours"] * 
                                                 (optimal_profile["power_consumption"] / 100)),
            estimated_completion_time=optimal_profile["estimated_completion_minutes"],
            preference_weights=preference_weights,
            decision_date=datetime.utcnow()
        )
        
        self.db.add(decision)
        await self.db.commit()
    
    # Additional helper methods for analysis and recommendations...
    
    async def _analyze_battery_prediction_accuracy(
        self,
        decision: BatteryPerformanceDecision,
        actual_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze battery prediction accuracy"""
        
        analysis = {}
        
        # Battery consumption accuracy
        if decision.actual_battery_consumption and decision.estimated_battery_consumption:
            battery_error = abs(decision.actual_battery_consumption - decision.estimated_battery_consumption)
            battery_error_pct = (battery_error / decision.estimated_battery_consumption) * 100
            analysis["battery_error_pct"] = battery_error_pct
            analysis["battery_accurate"] = battery_error_pct < 25  # Within 25%
        
        # Time prediction accuracy
        if decision.actual_completion_time and decision.estimated_completion_time:
            time_error = abs(decision.actual_completion_time - decision.estimated_completion_time)
            time_error_pct = (time_error / decision.estimated_completion_time) * 100
            analysis["time_error_pct"] = time_error_pct
            analysis["time_accurate"] = time_error_pct < 30  # Within 30%
        
        # Overall accuracy
        accuracy_factors = []
        if "battery_accurate" in analysis:
            accuracy_factors.append(1.0 if analysis["battery_accurate"] else 0.0)
        if "time_accurate" in analysis:
            accuracy_factors.append(1.0 if analysis["time_accurate"] else 0.0)
        if decision.user_satisfaction:
            accuracy_factors.append(1.0 if decision.user_satisfaction >= 7 else 0.0)
        
        if accuracy_factors:
            analysis["overall_accuracy"] = sum(accuracy_factors) / len(accuracy_factors)
        else:
            analysis["overall_accuracy"] = 0.5
        
        return analysis
    
    async def _update_battery_performance_models(
        self,
        user_id: uuid.UUID,
        decision: BatteryPerformanceDecision,
        accuracy_analysis: Dict[str, Any]
    ):
        """Update battery performance models with outcome data"""
        
        logger.info(f"Updating battery/performance models for user {user_id}, accuracy: {accuracy_analysis.get('overall_accuracy', 0)}")
        
        # In production, this would update ML models
        pass
    
    async def _analyze_battery_usage_patterns(
        self,
        decisions: List[BatteryPerformanceDecision]
    ) -> Dict[str, Any]:
        """Analyze battery usage patterns"""
        
        if len(decisions) < 5:
            return {"insufficient_data": True}
        
        # Sort by date
        sorted_decisions = sorted(decisions, key=lambda x: x.decision_date)
        
        # Analyze optimization trends
        recent_decisions = sorted_decisions[-10:]
        battery_optimized_recent = len([d for d in recent_decisions if d.optimization_target == "battery"])
        performance_optimized_recent = len([d for d in recent_decisions if d.optimization_target == "performance"])
        
        if battery_optimized_recent > performance_optimized_recent:
            battery_trend = "increasing_battery_focus"
        elif performance_optimized_recent > battery_optimized_recent:
            battery_trend = "increasing_performance_focus"
        else:
            battery_trend = "balanced_usage"
        
        # Performance usage rate
        total_decisions = len(decisions)
        high_performance_count = len([d for d in decisions if d.optimization_target == "performance"])
        high_performance_rate = (high_performance_count / total_decisions) * 100
        
        return {
            "battery_trend": battery_trend,
            "performance_trend": "increasing" if high_performance_rate > 40 else "moderate",
            "high_performance_rate": high_performance_rate,
            "satisfaction_trend": "stable"  # Would calculate from satisfaction scores
        }
    
    async def _determine_dominant_preference(
        self,
        decisions: List[BatteryPerformanceDecision]
    ) -> str:
        """Determine user's dominant battery vs performance preference"""
        
        battery_count = len([d for d in decisions if d.optimization_target == "battery"])
        performance_count = len([d for d in decisions if d.optimization_target == "performance"])
        balanced_count = len([d for d in decisions if d.optimization_target == "balanced"])
        
        if battery_count > performance_count and battery_count > balanced_count:
            return "battery_focused"
        elif performance_count > battery_count and performance_count > balanced_count:
            return "performance_focused"
        elif balanced_count > battery_count and balanced_count > performance_count:
            return "balanced_approach"
        else:
            return "no_clear_preference"
    
    async def _generate_battery_optimization_recommendations(
        self,
        user_id: uuid.UUID,
        decisions: List[BatteryPerformanceDecision]
    ) -> List[str]:
        """Generate battery optimization recommendations"""
        
        recommendations = []
        
        # Analyze thermal throttling frequency
        thermal_events = len([d for d in decisions if d.thermal_throttling_occurred])
        if thermal_events > len(decisions) * 0.3:
            recommendations.append("Consider lower performance profiles to reduce thermal throttling")
            recommendations.append("Ensure proper device ventilation during intensive tasks")
        
        # Analyze battery consumption patterns
        high_consumption_decisions = len([
            d for d in decisions 
            if d.actual_battery_consumption and d.actual_battery_consumption > 20
        ])
        
        if high_consumption_decisions > len(decisions) * 0.4:
            recommendations.append("Consider more battery-efficient profiles for longer usage")
            recommendations.append("Review background app usage to reduce power consumption")
        
        # Analyze satisfaction scores
        satisfaction_scores = [d.user_satisfaction for d in decisions if d.user_satisfaction]
        if satisfaction_scores:
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores)
            if avg_satisfaction < 6:
                recommendations.append("Consider adjusting power profile preferences")
                recommendations.append("Review task performance requirements")
        
        if not recommendations:
            recommendations.append("Battery usage patterns look optimal")
        
        return recommendations
    
    async def _analyze_situation(self, situation: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the current situation for power profile recommendation"""
        
        analysis = {
            "battery_level": situation.get("battery_level", 100),
            "charging_available": situation.get("charging_available", True),
            "location": situation.get("location", "home"),
            "time_until_next_charge": situation.get("hours_until_charge", 8),
            "task_urgency": situation.get("task_urgency", "normal"),
            "expected_usage_duration": situation.get("expected_duration_hours", 4)
        }
        
        # Determine situation characteristics
        analysis["battery_critical"] = analysis["battery_level"] <= 15 and not analysis["charging_available"]
        analysis["high_performance_needed"] = (
            analysis["task_urgency"] == "high" and 
            analysis["charging_available"]
        )
        analysis["traveling"] = analysis["location"] in ["airplane", "car", "train", "outdoor"]
        analysis["long_session"] = analysis["expected_usage_duration"] > 6
        
        return analysis
    
    async def _get_similar_situation_history(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        situation_analysis: Dict[str, Any]
    ) -> List[BatteryPerformanceDecision]:
        """Get historical decisions for similar situations"""
        
        # This would use ML to find similar situations
        # For now, return recent decisions as a simplified approach
        result = await self.db.execute(
            select(BatteryPerformanceDecision).where(
                and_(
                    BatteryPerformanceDecision.user_id == user_id,
                    BatteryPerformanceDecision.device_id == device_id
                )
            ).order_by(BatteryPerformanceDecision.decision_date.desc()).limit(10)
        )
        return result.scalars().all()
    
    async def _apply_user_customizations(
        self,
        recommendation: Dict[str, Any],
        similar_situations: List[BatteryPerformanceDecision]
    ) -> Dict[str, Any]:
        """Apply user-specific customizations based on history"""
        
        customizations = {}
        
        if similar_situations:
            # Find most common optimization target in similar situations
            optimization_targets = [d.optimization_target for d in similar_situations]
            most_common_target = max(set(optimization_targets), key=optimization_targets.count)
            
            if most_common_target != recommendation.get("optimization_preference"):
                customizations["user_preference_note"] = f"User typically prefers {most_common_target} in similar situations"
        
        return customizations
    
    async def _calculate_recommendation_confidence(
        self,
        user_id: uuid.UUID,
        device_id: uuid.UUID,
        situation_analysis: Dict[str, Any],
        similar_situations: List[BatteryPerformanceDecision]
    ) -> float:
        """Calculate confidence in the recommendation"""
        
        base_confidence = 0.7
        
        # Increase confidence with more historical data
        if len(similar_situations) > 10:
            base_confidence += 0.2
        elif len(similar_situations) > 5:
            base_confidence += 0.1
        
        # Adjust based on situation clarity
        if situation_analysis["battery_critical"]:
            base_confidence += 0.2  # Clear battery-saving need
        elif situation_analysis["high_performance_needed"]:
            base_confidence += 0.15  # Clear performance need
        
        return min(1.0, base_confidence)
    
    async def _generate_situation_alternatives(
        self,
        situation_analysis: Dict[str, Any],
        recommendation: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate alternative profiles for the situation"""
        
        alternatives = []
        
        # If recommending battery saver, offer balanced
        if recommendation["profile_name"] == "Battery Saver":
            alternatives.append({
                "name": "Balanced",
                "reason": "Better performance with moderate battery usage",
                "trade_off": "15-20% less battery life for 40% better performance"
            })
        
        # If recommending high performance, offer balanced
        elif recommendation["profile_name"] == "High Performance":
            alternatives.append({
                "name": "Balanced",
                "reason": "Conserve battery while maintaining good performance",
                "trade_off": "20% battery savings for 15% performance reduction"
            })
        
        # Always offer opposite extreme as alternative
        if recommendation["profile_name"] != "Battery Saver":
            alternatives.append({
                "name": "Battery Saver",
                "reason": "Maximum battery conservation",
                "trade_off": "50% longer battery life for reduced performance"
            })
        
        return alternatives
    
    async def _generate_implementation_steps(
        self,
        device: DeviceProfile,
        recommendation: Dict[str, Any]
    ) -> List[str]:
        """Generate steps to implement the recommended profile"""
        
        steps = []
        
        if device.device_type == DeviceType.LAPTOP:
            steps.extend([
                "Open power management settings",
                f"Set CPU frequency to {recommendation.get('cpu_frequency', 'adaptive')}",
                f"Set display brightness to {recommendation.get('display_brightness', 'auto')}",
                "Configure background app restrictions"
            ])
        
        elif device.device_type == DeviceType.MOBILE:
            steps.extend([
                "Open battery settings",
                f"Enable {recommendation['profile_name']} mode",
                "Configure app background restrictions",
                "Adjust display settings"
            ])
        
        if recommendation.get("network_optimization"):
            steps.append("Enable network power optimization")
        
        return steps
    
    async def _compare_profiles(
        self,
        alternative: Dict[str, Any],
        optimal: Dict[str, Any]
    ) -> List[str]:
        """Compare alternative profile with optimal"""
        
        comparisons = []
        
        battery_diff = alternative["estimated_battery_hours"] - optimal["estimated_battery_hours"]
        time_diff = alternative["estimated_completion_minutes"] - optimal["estimated_completion_minutes"]
        performance_diff = alternative["performance_level"] - optimal["performance_level"]
        
        if battery_diff > 0:
            comparisons.append(f"{battery_diff:.1f} hours longer battery life")
        elif battery_diff < 0:
            comparisons.append(f"{abs(battery_diff):.1f} hours shorter battery life")
        
        if time_diff > 0:
            comparisons.append(f"{time_diff:.0f} minutes longer to complete")
        elif time_diff < 0:
            comparisons.append(f"{abs(time_diff):.0f} minutes faster completion")
        
        if performance_diff > 0:
            comparisons.append(f"{performance_diff:.1f} points higher performance")
        elif performance_diff < 0:
            comparisons.append(f"{abs(performance_diff):.1f} points lower performance")
        
        return comparisons
    
    async def _suggest_when_to_choose_profile(self, profile: Dict[str, Any]) -> str:
        """Suggest when to choose this profile"""
        
        target = profile["profile"]["optimization_target"]
        
        if target == "battery":
            return "Choose when battery is low and charging not available"
        elif target == "performance":
            return "Choose when plugged in or performance is critical"
        elif target == "balanced":
            return "Choose for everyday tasks with moderate battery life"
        else:
            return "Choose for adaptive power management based on current needs"