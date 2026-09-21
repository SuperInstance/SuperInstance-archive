from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import math

from ..database import (
    ComputeAllowance, User, UserChoice, ChoiceType,
    OptimizationTarget, ComputeType, OptimizationRecommendation,
    OptimizationHistory, DeviceProfile
)

logger = logging.getLogger(__name__)

class ComputeAllowanceOptimizer:
    """Optimize compute allowance allocation and usage patterns"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        
    async def create_compute_allowance(
        self,
        user_id: uuid.UUID,
        monthly_allowance: Decimal,
        optimization_target: OptimizationTarget = OptimizationTarget.BALANCED,
        preferred_compute_type: ComputeType = ComputeType.CLOUD,
        cost_sensitivity: Decimal = Decimal('0.5'),
        performance_priority: Decimal = Decimal('0.5')
    ) -> Dict[str, Any]:
        """Create or update user's compute allowance configuration"""
        
        try:
            # Check if user already has an allowance for current period
            now = datetime.utcnow()
            period_start = datetime(now.year, now.month, 1)
            
            if now.month == 12:
                period_end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
            else:
                period_end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
            
            result = await self.db.execute(
                select(ComputeAllowance).where(
                    and_(
                        ComputeAllowance.user_id == user_id,
                        ComputeAllowance.allowance_period_start <= now,
                        ComputeAllowance.allowance_period_end >= now
                    )
                )
            )
            existing_allowance = result.scalar_one_or_none()
            
            if existing_allowance:
                # Update existing allowance
                existing_allowance.monthly_allowance = monthly_allowance
                existing_allowance.optimization_target = optimization_target
                existing_allowance.preferred_compute_type = preferred_compute_type
                existing_allowance.cost_sensitivity = cost_sensitivity
                existing_allowance.performance_priority = performance_priority
                
                allowance = existing_allowance
            else:
                # Create new allowance
                allowance = ComputeAllowance(
                    user_id=user_id,
                    monthly_allowance=monthly_allowance,
                    optimization_target=optimization_target,
                    preferred_compute_type=preferred_compute_type,
                    cost_sensitivity=cost_sensitivity,
                    performance_priority=performance_priority,
                    allowance_period_start=period_start,
                    allowance_period_end=period_end
                )
                self.db.add(allowance)
            
            await self.db.commit()
            await self.db.refresh(allowance)
            
            # Generate initial optimization recommendations
            recommendations = await self.generate_optimization_recommendations(user_id)
            
            return {
                "success": True,
                "allowance_id": str(allowance.id),
                "monthly_allowance": float(monthly_allowance),
                "current_usage": float(allowance.current_usage),
                "remaining_allowance": float(monthly_allowance - allowance.current_usage),
                "optimization_target": optimization_target.value,
                "preferred_compute_type": preferred_compute_type.value,
                "cost_sensitivity": float(cost_sensitivity),
                "performance_priority": float(performance_priority),
                "period_start": allowance.allowance_period_start.isoformat(),
                "period_end": allowance.allowance_period_end.isoformat(),
                "initial_recommendations": recommendations,
                "optimization_enabled": allowance.auto_optimization_enabled
            }
            
        except Exception as e:
            logger.error(f"Failed to create compute allowance: {e}")
            raise
    
    async def optimize_allowance_usage(
        self,
        user_id: uuid.UUID,
        upcoming_workloads: List[Dict[str, Any]],
        time_horizon_hours: int = 168  # 1 week default
    ) -> Dict[str, Any]:
        """Optimize compute allowance usage for upcoming workloads"""
        
        try:
            # Get current allowance
            allowance = await self._get_current_allowance(user_id)
            if not allowance:
                return {"success": False, "error": "No compute allowance found for user"}
            
            # Analyze current usage patterns
            usage_patterns = await self._analyze_usage_patterns(user_id)
            
            # Get user's device profiles for optimization context
            device_profiles = await self._get_user_device_profiles(user_id)
            
            # Calculate optimal allocation strategy
            optimization_strategy = await self._calculate_optimization_strategy(
                allowance, upcoming_workloads, usage_patterns, device_profiles, time_horizon_hours
            )
            
            # Generate specific recommendations
            recommendations = await self._generate_usage_recommendations(
                user_id, allowance, optimization_strategy, upcoming_workloads
            )
            
            # Calculate projected savings and performance impact
            impact_analysis = await self._analyze_optimization_impact(
                allowance, optimization_strategy, usage_patterns
            )
            
            return {
                "user_id": str(user_id),
                "current_allowance": float(allowance.monthly_allowance),
                "current_usage": float(allowance.current_usage),
                "remaining_allowance": float(allowance.monthly_allowance - allowance.current_usage),
                "optimization_strategy": optimization_strategy,
                "recommendations": recommendations,
                "impact_analysis": impact_analysis,
                "workload_analysis": {
                    "total_workloads": len(upcoming_workloads),
                    "estimated_compute_needed": sum(
                        w.get("estimated_compute_units", 0) for w in upcoming_workloads
                    ),
                    "priority_distribution": await self._analyze_workload_priorities(upcoming_workloads)
                },
                "optimization_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to optimize allowance usage: {e}")
            raise
    
    async def track_allowance_usage(
        self,
        user_id: uuid.UUID,
        compute_units_used: Decimal,
        workload_type: str,
        compute_type: ComputeType,
        cost_per_unit: Decimal,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Track compute allowance usage and update optimization models"""
        
        try:
            # Get current allowance
            allowance = await self._get_current_allowance(user_id)
            if not allowance:
                return {"success": False, "error": "No active compute allowance found"}
            
            # Calculate cost
            total_cost = compute_units_used * cost_per_unit
            
            # Update usage
            allowance.current_usage += total_cost
            
            # Check for overage
            is_over_budget = allowance.current_usage > allowance.monthly_allowance
            overage_amount = max(Decimal('0'), allowance.current_usage - allowance.monthly_allowance)
            
            # Record usage choice for learning
            await self._record_usage_choice(
                user_id, workload_type, compute_type, compute_units_used, 
                total_cost, metadata
            )
            
            # Update optimization models with new data
            if allowance.auto_optimization_enabled:
                await self._update_optimization_models(user_id, {
                    "workload_type": workload_type,
                    "compute_type": compute_type.value,
                    "units_used": float(compute_units_used),
                    "cost": float(total_cost),
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            await self.db.commit()
            
            # Generate alerts if needed
            alerts = []
            if is_over_budget and not allowance.overage_protection:
                alerts.append({
                    "type": "budget_exceeded",
                    "message": f"Compute allowance exceeded by ${overage_amount:.2f}",
                    "severity": "warning"
                })
            elif allowance.current_usage > allowance.monthly_allowance * Decimal('0.8'):
                alerts.append({
                    "type": "budget_warning",
                    "message": f"80% of compute allowance used",
                    "severity": "info"
                })
            
            # Generate new optimization recommendations if usage pattern changed significantly
            recommendations = []
            if len(alerts) > 0 or await self._should_reoptimize(user_id):
                recommendations = await self.generate_optimization_recommendations(user_id)
            
            return {
                "success": True,
                "usage_tracked": True,
                "current_usage": float(allowance.current_usage),
                "monthly_allowance": float(allowance.monthly_allowance),
                "remaining_allowance": float(allowance.monthly_allowance - allowance.current_usage),
                "usage_percentage": float((allowance.current_usage / allowance.monthly_allowance) * 100),
                "is_over_budget": is_over_budget,
                "overage_amount": float(overage_amount),
                "alerts": alerts,
                "new_recommendations": recommendations,
                "usage_efficiency": await self._calculate_usage_efficiency(user_id)
            }
            
        except Exception as e:
            logger.error(f"Failed to track allowance usage: {e}")
            raise
    
    async def generate_optimization_recommendations(
        self,
        user_id: uuid.UUID,
        recommendation_count: int = 5
    ) -> List[Dict[str, Any]]:
        """Generate personalized optimization recommendations"""
        
        try:
            # Get current allowance and usage patterns
            allowance = await self._get_current_allowance(user_id)
            if not allowance:
                return []
            
            usage_patterns = await self._analyze_usage_patterns(user_id)
            device_profiles = await self._get_user_device_profiles(user_id)
            
            recommendations = []
            
            # 1. Compute type optimization
            compute_type_rec = await self._recommend_compute_type_optimization(
                allowance, usage_patterns, device_profiles
            )
            if compute_type_rec:
                recommendations.append(compute_type_rec)
            
            # 2. Timing optimization
            timing_rec = await self._recommend_timing_optimization(
                user_id, usage_patterns
            )
            if timing_rec:
                recommendations.append(timing_rec)
            
            # 3. Workload batching
            batching_rec = await self._recommend_workload_batching(
                user_id, usage_patterns
            )
            if batching_rec:
                recommendations.append(batching_rec)
            
            # 4. Resource allocation optimization
            resource_rec = await self._recommend_resource_optimization(
                allowance, usage_patterns
            )
            if resource_rec:
                recommendations.append(resource_rec)
            
            # 5. Budget reallocation
            budget_rec = await self._recommend_budget_reallocation(
                allowance, usage_patterns
            )
            if budget_rec:
                recommendations.append(budget_rec)
            
            # Store recommendations in database
            for rec in recommendations[:recommendation_count]:
                await self._store_recommendation(user_id, rec)
            
            return recommendations[:recommendation_count]
            
        except Exception as e:
            logger.error(f"Failed to generate optimization recommendations: {e}")
            raise
    
    async def implement_optimization_recommendation(
        self,
        user_id: uuid.UUID,
        recommendation_id: uuid.UUID,
        implementation_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Implement an optimization recommendation and track results"""
        
        try:
            # Get recommendation
            result = await self.db.execute(
                select(OptimizationRecommendation).where(
                    OptimizationRecommendation.id == recommendation_id
                )
            )
            recommendation = result.scalar_one_or_none()
            
            if not recommendation:
                return {"success": False, "error": "Recommendation not found"}
            
            if recommendation.user_id != user_id:
                return {"success": False, "error": "Recommendation belongs to different user"}
            
            # Get current configuration for before/after comparison
            current_allowance = await self._get_current_allowance(user_id)
            before_configuration = {
                "optimization_target": current_allowance.optimization_target.value,
                "preferred_compute_type": current_allowance.preferred_compute_type.value,
                "cost_sensitivity": float(current_allowance.cost_sensitivity),
                "performance_priority": float(current_allowance.performance_priority),
                "auto_optimization": current_allowance.auto_optimization_enabled
            }
            
            # Implement the recommendation
            implementation_result = await self._apply_recommendation(
                user_id, recommendation
            )
            
            if not implementation_result["success"]:
                return implementation_result
            
            # Mark recommendation as accepted
            recommendation.was_accepted = True
            recommendation.acceptance_date = datetime.utcnow()
            
            # Create optimization history record
            optimization_history = OptimizationHistory(
                user_id=user_id,
                optimization_type=recommendation.recommendation_type,
                before_configuration=before_configuration,
                after_configuration=recommendation.recommended_configuration,
                optimization_trigger="user_accepted_recommendation",
                expected_benefits=recommendation.expected_benefits,
                implementation_date=datetime.utcnow(),
                measurement_period_days=7,  # Default measurement period
                metadata={
                    "recommendation_id": str(recommendation_id),
                    "implementation_notes": implementation_notes,
                    "confidence_score": float(recommendation.confidence_score)
                }
            )
            
            self.db.add(optimization_history)
            await self.db.commit()
            
            return {
                "success": True,
                "recommendation_id": str(recommendation_id),
                "implementation_result": implementation_result,
                "optimization_history_id": str(optimization_history.id),
                "expected_benefits": recommendation.expected_benefits,
                "measurement_period_days": optimization_history.measurement_period_days,
                "next_review_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to implement optimization recommendation: {e}")
            raise
    
    async def get_optimization_performance(
        self,
        user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for user's optimization history"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get optimization history
            result = await self.db.execute(
                select(OptimizationHistory).where(
                    and_(
                        OptimizationHistory.user_id == user_id,
                        OptimizationHistory.implementation_date >= start_date
                    )
                ).order_by(OptimizationHistory.implementation_date.desc())
            )
            optimizations = result.scalars().all()
            
            if not optimizations:
                return {
                    "user_id": str(user_id),
                    "period_days": period_days,
                    "message": "No optimization history found for this period"
                }
            
            # Analyze optimization performance
            total_optimizations = len(optimizations)
            successful_optimizations = len([o for o in optimizations if o.success_score and o.success_score >= 0.7])
            
            # Calculate aggregate benefits
            total_cost_savings = Decimal('0')
            total_performance_gain = Decimal('0')
            
            for opt in optimizations:
                if opt.actual_benefits:
                    total_cost_savings += Decimal(str(opt.actual_benefits.get("cost_savings", 0)))
                    total_performance_gain += Decimal(str(opt.actual_benefits.get("performance_gain", 0)))
                elif opt.expected_benefits:  # Use expected if actual not measured yet
                    total_cost_savings += Decimal(str(opt.expected_benefits.get("cost_savings", 0)))
                    total_performance_gain += Decimal(str(opt.expected_benefits.get("performance_gain", 0)))
            
            # Optimization type breakdown
            type_breakdown = {}
            for opt in optimizations:
                opt_type = opt.optimization_type
                if opt_type not in type_breakdown:
                    type_breakdown[opt_type] = {"count": 0, "success_rate": 0}
                type_breakdown[opt_type]["count"] += 1
                if opt.success_score and opt.success_score >= 0.7:
                    type_breakdown[opt_type]["success_rate"] += 1
            
            # Calculate success rates
            for type_data in type_breakdown.values():
                type_data["success_rate"] = (type_data["success_rate"] / type_data["count"]) * 100
            
            # User satisfaction analysis
            satisfaction_scores = [o.user_satisfaction for o in optimizations if o.user_satisfaction]
            avg_satisfaction = sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "optimization_summary": {
                    "total_optimizations": total_optimizations,
                    "successful_optimizations": successful_optimizations,
                    "success_rate": (successful_optimizations / total_optimizations) * 100 if total_optimizations > 0 else 0,
                    "average_user_satisfaction": round(avg_satisfaction, 2)
                },
                "aggregate_benefits": {
                    "total_cost_savings": float(total_cost_savings),
                    "total_performance_gain": float(total_performance_gain),
                    "average_cost_savings_per_optimization": float(total_cost_savings / total_optimizations) if total_optimizations > 0 else 0
                },
                "optimization_breakdown": type_breakdown,
                "recent_optimizations": [
                    {
                        "optimization_id": str(opt.id),
                        "type": opt.optimization_type,
                        "implementation_date": opt.implementation_date.isoformat(),
                        "success_score": float(opt.success_score) if opt.success_score else None,
                        "user_satisfaction": opt.user_satisfaction,
                        "cost_savings": opt.actual_benefits.get("cost_savings", 0) if opt.actual_benefits else 0
                    }
                    for opt in optimizations[:10]
                ],
                "optimization_trends": await self._analyze_optimization_trends(optimizations),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get optimization performance: {e}")
            raise
    
    async def _get_current_allowance(self, user_id: uuid.UUID) -> Optional[ComputeAllowance]:
        """Get user's current active compute allowance"""
        
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
    
    async def _analyze_usage_patterns(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Analyze user's compute usage patterns"""
        
        # Get usage choices from last 30 days
        start_date = datetime.utcnow() - timedelta(days=30)
        
        result = await self.db.execute(
            select(UserChoice).where(
                and_(
                    UserChoice.user_id == user_id,
                    UserChoice.choice_type.in_([
                        ChoiceType.COMPUTE_ALLOCATION,
                        ChoiceType.LOCAL_VS_CLOUD,
                        ChoiceType.SPEED_VS_COST
                    ]),
                    UserChoice.choice_date >= start_date
                )
            )
        )
        choices = result.scalars().all()
        
        if not choices:
            return {"no_data": True, "period_days": 30}
        
        # Analyze patterns
        compute_type_preferences = {}
        timing_patterns = {}
        cost_sensitivity_scores = []
        performance_priority_scores = []
        
        for choice in choices:
            # Compute type preferences
            if choice.selected_option and "compute_type" in choice.selected_option:
                compute_type = choice.selected_option["compute_type"]
                compute_type_preferences[compute_type] = compute_type_preferences.get(compute_type, 0) + 1
            
            # Timing patterns
            hour = choice.choice_date.hour
            timing_patterns[hour] = timing_patterns.get(hour, 0) + 1
            
            # Extract sensitivity scores from decision factors
            if choice.decision_factors:
                if "cost_sensitivity" in choice.decision_factors:
                    cost_sensitivity_scores.append(choice.decision_factors["cost_sensitivity"])
                if "performance_priority" in choice.decision_factors:
                    performance_priority_scores.append(choice.decision_factors["performance_priority"])
        
        return {
            "period_days": 30,
            "total_choices": len(choices),
            "compute_type_preferences": compute_type_preferences,
            "timing_patterns": timing_patterns,
            "avg_cost_sensitivity": sum(cost_sensitivity_scores) / len(cost_sensitivity_scores) if cost_sensitivity_scores else 0.5,
            "avg_performance_priority": sum(performance_priority_scores) / len(performance_priority_scores) if performance_priority_scores else 0.5,
            "most_active_hours": sorted(timing_patterns.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    async def _get_user_device_profiles(self, user_id: uuid.UUID) -> List[DeviceProfile]:
        """Get user's device profiles for optimization context"""
        
        result = await self.db.execute(
            select(DeviceProfile).where(
                and_(
                    DeviceProfile.user_id == user_id,
                    DeviceProfile.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def _generate_usage_recommendations(
        self,
        user_id: uuid.UUID,
        allowance: ComputeAllowance,
        optimization_strategy: Dict[str, Any],
        upcoming_workloads: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate specific usage recommendations based on optimization strategy"""
        
        recommendations = []
        
        for workload_info in optimization_strategy["workload_prioritization"]:
            workload_idx = workload_info["workload_index"]
            workload = upcoming_workloads[workload_idx]
            
            recommendation = {
                "workload_name": workload.get("name", f"Workload {workload_idx + 1}"),
                "recommended_compute_type": workload_info["recommended_compute_type"],
                "estimated_cost": workload_info["estimated_cost"],
                "priority_score": workload_info["priority_score"],
                "timing_recommendation": await self._get_optimal_timing(
                    user_id, workload, allowance
                ),
                "resource_optimization": await self._get_resource_optimization_tips(workload)
            }
            recommendations.append(recommendation)
        
        return recommendations
    
    async def _analyze_optimization_impact(
        self,
        allowance: ComputeAllowance,
        optimization_strategy: Dict[str, Any],
        usage_patterns: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze the projected impact of optimization strategy"""
        
        # Estimate cost savings based on optimization strategy
        baseline_cost = float(allowance.current_usage)
        projected_savings = 0.0
        
        # Cost optimization impact
        if allowance.optimization_target == OptimizationTarget.COST:
            projected_savings = baseline_cost * 0.15  # 15% savings estimate
        elif allowance.optimization_target == OptimizationTarget.BALANCED:
            projected_savings = baseline_cost * 0.08  # 8% savings estimate
        
        # Performance impact estimation
        performance_impact = 0.0
        if allowance.optimization_target == OptimizationTarget.SPEED:
            performance_impact = 0.25  # 25% performance improvement
        elif allowance.optimization_target == OptimizationTarget.BALANCED:
            performance_impact = 0.10  # 10% performance improvement
        
        return {
            "projected_cost_savings": projected_savings,
            "projected_performance_improvement": performance_impact,
            "optimization_confidence": 0.75,  # Based on historical data
            "implementation_effort": "low",
            "expected_roi": projected_savings / max(baseline_cost, 1) * 100
        }
    
    async def _analyze_workload_priorities(
        self,
        upcoming_workloads: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """Analyze the distribution of workload priorities"""
        
        priority_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for workload in upcoming_workloads:
            priority = workload.get("priority", 5)
            if priority >= 8:
                priority_distribution["high"] += 1
            elif priority >= 5:
                priority_distribution["medium"] += 1
            else:
                priority_distribution["low"] += 1
        
        return priority_distribution
    
    async def _record_usage_choice(
        self,
        user_id: uuid.UUID,
        workload_type: str,
        compute_type: ComputeType,
        compute_units_used: Decimal,
        total_cost: Decimal,
        metadata: Optional[Dict] = None
    ):
        """Record a usage choice for learning and optimization"""
        
        choice = UserChoice(
            user_id=user_id,
            choice_type=ChoiceType.COMPUTE_ALLOCATION,
            selected_option={
                "workload_type": workload_type,
                "compute_type": compute_type.value,
                "compute_units": float(compute_units_used),
                "cost": float(total_cost)
            },
            decision_factors=metadata or {},
            choice_date=datetime.utcnow()
        )
        
        self.db.add(choice)
    
    async def _update_optimization_models(
        self,
        user_id: uuid.UUID,
        usage_data: Dict[str, Any]
    ):
        """Update optimization models with new usage data"""
        
        # This would integrate with ML models for personalized optimization
        # For now, we'll store the data for future model training
        logger.info(f"Updating optimization models for user {user_id} with data: {usage_data}")
        
        # Store usage data in user metadata for model training
        # In a production system, this would feed into ML pipelines
        pass
    
    async def _should_reoptimize(self, user_id: uuid.UUID) -> bool:
        """Determine if user's usage patterns warrant reoptimization"""
        
        # Get recent choices
        recent_date = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(UserChoice).where(
                and_(
                    UserChoice.user_id == user_id,
                    UserChoice.choice_date >= recent_date
                )
            )
        )
        recent_choices = result.scalars().all()
        
        # Reoptimize if there have been significant usage pattern changes
        return len(recent_choices) >= 10  # Threshold for pattern change
    
    async def _calculate_usage_efficiency(self, user_id: uuid.UUID) -> float:
        """Calculate user's compute usage efficiency"""
        
        allowance = await self._get_current_allowance(user_id)
        if not allowance:
            return 0.0
        
        # Simple efficiency calculation based on budget utilization
        utilization = float(allowance.current_usage) / float(allowance.monthly_allowance)
        
        # Efficiency is optimal around 80-90% utilization
        if 0.8 <= utilization <= 0.9:
            return 1.0
        elif utilization < 0.8:
            return utilization / 0.8  # Underutilization penalty
        else:
            return max(0.0, 2.0 - utilization)  # Overutilization penalty
    
    async def _recommend_compute_type_optimization(
        self,
        allowance: ComputeAllowance,
        usage_patterns: Dict[str, Any],
        device_profiles: List[DeviceProfile]
    ) -> Optional[Dict[str, Any]]:
        """Recommend compute type optimization"""
        
        if "compute_type_preferences" not in usage_patterns:
            return None
        
        preferences = usage_patterns["compute_type_preferences"]
        current_preferred = allowance.preferred_compute_type.value
        
        # Find most used compute type
        most_used = max(preferences.items(), key=lambda x: x[1])[0] if preferences else current_preferred
        
        if most_used != current_preferred and preferences[most_used] > preferences.get(current_preferred, 0) * 2:
            return {
                "type": "compute_type_optimization",
                "title": f"Switch primary compute type to {most_used}",
                "description": f"You use {most_used} compute 2x more than your preferred {current_preferred}",
                "expected_savings": 15.0,
                "confidence": 0.8,
                "implementation_effort": "low"
            }
        
        return None
    
    async def _recommend_timing_optimization(
        self,
        user_id: uuid.UUID,
        usage_patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Recommend timing optimization based on usage patterns"""
        
        if "most_active_hours" not in usage_patterns:
            return None
        
        most_active_hours = usage_patterns["most_active_hours"]
        peak_hour = most_active_hours[0][0] if most_active_hours else 12
        
        # Recommend off-peak usage for cost savings
        if peak_hour in range(9, 17):  # Business hours
            return {
                "type": "timing_optimization",
                "title": "Shift workloads to off-peak hours",
                "description": f"Running workloads outside {peak_hour}:00-17:00 can save 20-30%",
                "expected_savings": 25.0,
                "confidence": 0.7,
                "implementation_effort": "medium"
            }
        
        return None
    
    async def _recommend_workload_batching(
        self,
        user_id: uuid.UUID,
        usage_patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Recommend workload batching for efficiency"""
        
        if usage_patterns.get("total_choices", 0) > 50:  # High usage user
            return {
                "type": "workload_batching",
                "title": "Batch similar workloads together",
                "description": "Grouping similar tasks can reduce overhead and improve efficiency",
                "expected_savings": 10.0,
                "confidence": 0.6,
                "implementation_effort": "medium"
            }
        
        return None
    
    async def _recommend_resource_optimization(
        self,
        allowance: ComputeAllowance,
        usage_patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Recommend resource allocation optimization"""
        
        utilization = float(allowance.current_usage) / float(allowance.monthly_allowance)
        
        if utilization > 0.9:
            return {
                "type": "resource_optimization",
                "title": "Consider increasing monthly allowance",
                "description": "You're using 90%+ of your allowance, consider upgrading",
                "expected_savings": 0.0,
                "confidence": 0.9,
                "implementation_effort": "low"
            }
        elif utilization < 0.3:
            return {
                "type": "resource_optimization", 
                "title": "Consider reducing monthly allowance",
                "description": "You're only using 30% of your allowance, consider reducing",
                "expected_savings": float(allowance.monthly_allowance) * 0.4,
                "confidence": 0.8,
                "implementation_effort": "low"
            }
        
        return None
    
    async def _recommend_budget_reallocation(
        self,
        allowance: ComputeAllowance,
        usage_patterns: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Recommend budget reallocation strategies"""
        
        avg_cost_sensitivity = usage_patterns.get("avg_cost_sensitivity", 0.5)
        
        if avg_cost_sensitivity > 0.7:  # Cost-sensitive user
            return {
                "type": "budget_reallocation",
                "title": "Optimize for maximum cost efficiency",
                "description": "Prioritize lowest-cost compute options for non-urgent tasks",
                "expected_savings": 18.0,
                "confidence": 0.75,
                "implementation_effort": "low"
            }
        
        return None
    
    async def _store_recommendation(
        self,
        user_id: uuid.UUID,
        recommendation: Dict[str, Any]
    ):
        """Store a recommendation in the database"""
        
        db_recommendation = OptimizationRecommendation(
            user_id=user_id,
            recommendation_type=recommendation["type"],
            title=recommendation["title"],
            description=recommendation["description"],
            recommended_configuration=recommendation,
            expected_benefits={
                "cost_savings": recommendation.get("expected_savings", 0),
                "performance_gain": recommendation.get("performance_gain", 0)
            },
            confidence_score=Decimal(str(recommendation.get("confidence", 0.5))),
            implementation_effort=recommendation.get("implementation_effort", "medium"),
            valid_until=datetime.utcnow() + timedelta(days=7),
            created_date=datetime.utcnow()
        )
        
        self.db.add(db_recommendation)
    
    async def _apply_recommendation(
        self,
        user_id: uuid.UUID,
        recommendation: OptimizationRecommendation
    ) -> Dict[str, Any]:
        """Apply an optimization recommendation"""
        
        allowance = await self._get_current_allowance(user_id)
        if not allowance:
            return {"success": False, "error": "No active allowance found"}
        
        # Apply the recommendation based on type
        config = recommendation.recommended_configuration
        
        if recommendation.recommendation_type == "compute_type_optimization":
            # Update preferred compute type
            new_type = config.get("new_compute_type", allowance.preferred_compute_type.value)
            if new_type in [ct.value for ct in ComputeType]:
                allowance.preferred_compute_type = ComputeType(new_type)
        
        elif recommendation.recommendation_type == "resource_optimization":
            # Update monthly allowance if recommended
            new_allowance = config.get("new_monthly_allowance")
            if new_allowance:
                allowance.monthly_allowance = Decimal(str(new_allowance))
        
        # Enable auto-optimization if not already enabled
        allowance.auto_optimization_enabled = True
        
        await self.db.commit()
        
        return {
            "success": True,
            "changes_applied": config,
            "message": f"Applied {recommendation.recommendation_type} optimization"
        }
    
    async def _analyze_optimization_trends(
        self,
        optimizations: List[OptimizationHistory]
    ) -> Dict[str, Any]:
        """Analyze trends in optimization performance"""
        
        if len(optimizations) < 3:
            return {"insufficient_data": True}
        
        # Sort by date for trend analysis
        sorted_opts = sorted(optimizations, key=lambda x: x.implementation_date)
        
        # Analyze success score trends
        success_scores = [o.success_score for o in sorted_opts if o.success_score]
        
        if len(success_scores) >= 3:
            recent_avg = sum(success_scores[-3:]) / 3
            earlier_avg = sum(success_scores[:-3]) / len(success_scores[:-3]) if len(success_scores) > 3 else recent_avg
            trend = "improving" if recent_avg > earlier_avg else "declining"
        else:
            trend = "stable"
        
        return {
            "optimization_trend": trend,
            "recent_success_rate": sum(success_scores[-5:]) / min(5, len(success_scores)) if success_scores else 0,
            "trend_confidence": 0.7,
            "recommendation": "Continue current optimization approach" if trend == "improving" else "Review optimization strategy"
        }
    
    async def _get_optimal_timing(
        self,
        user_id: uuid.UUID,
        workload: Dict[str, Any],
        allowance: ComputeAllowance
    ) -> str:
        """Get optimal timing recommendation for a workload"""
        
        urgency = workload.get("urgency", "medium")
        
        if urgency == "high":
            return "immediate"
        elif urgency == "low" and allowance.optimization_target == OptimizationTarget.COST:
            return "off_peak_hours"  # 2-6 AM typically cheaper
        else:
            return "flexible"
    
    async def _get_resource_optimization_tips(
        self,
        workload: Dict[str, Any]
    ) -> List[str]:
        """Get resource optimization tips for a workload"""
        
        tips = []
        
        compute_intensity = workload.get("compute_intensity", "medium")
        if compute_intensity == "high":
            tips.append("Consider using GPU instances for compute-intensive tasks")
            tips.append("Enable auto-scaling to handle peak loads efficiently")
        
        data_size = workload.get("data_size", "medium")
        if data_size == "large":
            tips.append("Use data compression to reduce transfer costs")
            tips.append("Consider data locality to minimize network overhead")
        
        if not tips:
            tips.append("Monitor resource usage and adjust allocation as needed")
        
        return tips
    
    async def _calculate_optimization_strategy(
        self,
        allowance: ComputeAllowance,
        upcoming_workloads: List[Dict[str, Any]],
        usage_patterns: Dict[str, Any],
        device_profiles: List[DeviceProfile],
        time_horizon_hours: int
    ) -> Dict[str, Any]:
        """Calculate optimal strategy for compute allocation"""
        
        strategy = {
            "optimization_approach": allowance.optimization_target.value,
            "time_horizon_hours": time_horizon_hours,
            "workload_prioritization": [],
            "compute_type_allocation": {},
            "timing_recommendations": {},
            "budget_allocation": {}
        }
        
        # Prioritize workloads based on urgency and importance
        for i, workload in enumerate(upcoming_workloads):
            priority_score = workload.get("priority", 5)  # 1-10 scale
            urgency = workload.get("urgency", "medium")
            estimated_cost = workload.get("estimated_cost", 0)
            
            strategy["workload_prioritization"].append({
                "workload_index": i,
                "priority_score": priority_score,
                "urgency": urgency,
                "estimated_cost": estimated_cost,
                "recommended_compute_type": await self._recommend_workload_compute_type(
                    workload, allowance, device_profiles
                )
            })
        
        # Allocate compute types based on optimization target
        if allowance.optimization_target == OptimizationTarget.COST:
            strategy["compute_type_allocation"] = {
                "local": 0.6,  # Prefer local for cost savings
                "cloud": 0.3,
                "edge": 0.1
            }
        elif allowance.optimization_target == OptimizationTarget.SPEED:
            strategy["compute_type_allocation"] = {
                "local": 0.2,
                "cloud": 0.7,  # Prefer cloud for speed
                "edge": 0.1
            }
        else:  # BALANCED
            strategy["compute_type_allocation"] = {
                "local": 0.4,
                "cloud": 0.5,
                "edge": 0.1
            }
        
        return strategy
    
    async def _recommend_workload_compute_type(
        self,
        workload: Dict[str, Any],
        allowance: ComputeAllowance,
        device_profiles: List[DeviceProfile]
    ) -> str:
        """Recommend compute type for a specific workload"""
        
        # Simplified recommendation logic
        workload_type = workload.get("type", "general")
        compute_intensity = workload.get("compute_intensity", "medium")
        data_sensitivity = workload.get("data_sensitivity", "low")
        
        # High sensitivity data should prefer local
        if data_sensitivity in ["high", "confidential"]:
            return "local"
        
        # High compute intensity and cost-sensitive users prefer cloud
        if compute_intensity == "high" and allowance.cost_sensitivity < 0.3:
            return "cloud"
        
        # Default recommendation based on user preference
        return allowance.preferred_compute_type.value