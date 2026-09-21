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
    User, UserChoice, ChoiceType, LoyaltyReward,
    RewardTier, RewardProgram, UserRewardStatus,
    RewardTransaction, RewardType
)

logger = logging.getLogger(__name__)

class LoyaltyRewardsSystem:
    """Comprehensive loyalty rewards system for user choices and engagement"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_user_rewards(
        self,
        user_id: uuid.UUID,
        actions: List[Dict[str, Any]],
        calculation_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Calculate rewards for user actions and choices"""
        
        try:
            # Get user's current reward status
            user_reward_status = await self._get_user_reward_status(user_id)
            
            # Get active reward programs
            active_programs = await self._get_active_reward_programs()
            
            # Calculate rewards for each action
            action_rewards = []
            total_points = 0
            
            for action in actions:
                reward_calculation = await self._calculate_action_reward(
                    user_id, action, active_programs, user_reward_status
                )
                action_rewards.append(reward_calculation)
                total_points += reward_calculation["points_earned"]
            
            # Apply multipliers and bonuses
            bonus_calculation = await self._apply_loyalty_bonuses(
                user_id, total_points, user_reward_status, calculation_context
            )
            
            final_points = total_points + bonus_calculation["bonus_points"]
            
            # Check for tier progression
            tier_update = await self._check_tier_progression(
                user_id, user_reward_status, final_points
            )
            
            # Generate available rewards and redemption options
            available_rewards = await self._get_available_rewards(user_id, user_reward_status)
            
            # Store reward transactions
            await self._store_reward_transactions(
                user_id, action_rewards, bonus_calculation, tier_update
            )
            
            return {
                "user_id": str(user_id),
                "calculation_summary": {
                    "actions_processed": len(actions),
                    "base_points_earned": total_points,
                    "bonus_points": bonus_calculation["bonus_points"],
                    "total_points_earned": final_points,
                    "new_total_points": user_reward_status["current_points"] + final_points
                },
                "action_rewards": action_rewards,
                "loyalty_bonuses": bonus_calculation,
                "tier_information": {
                    "current_tier": user_reward_status["current_tier"],
                    "tier_progression": tier_update,
                    "next_tier_requirements": user_reward_status["next_tier_requirements"]
                },
                "available_rewards": available_rewards,
                "redemption_recommendations": await self._generate_redemption_recommendations(
                    user_id, user_reward_status, final_points
                ),
                "achievement_unlocks": await self._check_achievement_unlocks(
                    user_id, actions, user_reward_status
                ),
                "calculation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate user rewards: {e}")
            raise
    
    async def redeem_rewards(
        self,
        user_id: uuid.UUID,
        redemption_request: Dict[str, Any],
        redemption_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process reward redemption request"""
        
        try:
            # Get user's current reward status
            user_reward_status = await self._get_user_reward_status(user_id)
            
            # Validate redemption request
            validation_result = await self._validate_redemption_request(
                user_id, redemption_request, user_reward_status
            )
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "validation_details": validation_result
                }
            
            # Get reward details
            reward = await self._get_reward_details(redemption_request["reward_id"])
            
            # Calculate redemption cost and benefits
            redemption_calculation = await self._calculate_redemption_cost(
                reward, redemption_request, user_reward_status
            )
            
            # Process the redemption
            redemption_result = await self._process_reward_redemption(
                user_id, reward, redemption_calculation, redemption_context
            )
            
            # Update user reward status
            await self._update_user_reward_status(
                user_id, redemption_calculation, redemption_result
            )
            
            # Generate redemption confirmation
            confirmation = await self._generate_redemption_confirmation(
                user_id, reward, redemption_result
            )
            
            return {
                "success": True,
                "user_id": str(user_id),
                "redemption_id": str(redemption_result["redemption_id"]),
                "reward_redeemed": {
                    "reward_name": reward["name"],
                    "reward_type": reward["type"],
                    "points_cost": redemption_calculation["total_cost"],
                    "discount_applied": redemption_calculation["discount_amount"]
                },
                "user_balance": {
                    "points_before": user_reward_status["current_points"],
                    "points_after": user_reward_status["current_points"] - redemption_calculation["total_cost"],
                    "tier_maintained": user_reward_status["current_tier"]
                },
                "redemption_details": redemption_result,
                "confirmation": confirmation,
                "follow_up_actions": await self._generate_post_redemption_actions(
                    user_id, reward, redemption_result
                ),
                "redemption_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process reward redemption: {e}")
            raise
    
    async def get_loyalty_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """Get comprehensive loyalty program analytics for user"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get reward transactions
            result = await self.db.execute(
                select(RewardTransaction).where(
                    and_(
                        RewardTransaction.user_id == user_id,
                        RewardTransaction.transaction_date >= start_date
                    )
                ).order_by(RewardTransaction.transaction_date.desc())
            )
            reward_transactions = result.scalars().all()
            
            # Get user's current status
            user_status = await self._get_user_reward_status(user_id)
            
            # Analyze earning patterns
            earning_analysis = await self._analyze_earning_patterns(reward_transactions)
            
            # Analyze redemption patterns
            redemption_analysis = await self._analyze_redemption_patterns(
                user_id, reward_transactions, period_days
            )
            
            # Calculate engagement metrics
            engagement_metrics = await self._calculate_engagement_metrics(
                user_id, reward_transactions, period_days
            )
            
            # Analyze tier progression
            tier_analysis = await self._analyze_tier_progression(user_id, period_days)
            
            # Calculate program value and ROI
            value_analysis = await self._calculate_program_value(
                user_id, reward_transactions, period_days
            )
            
            return {
                "user_id": str(user_id),
                "period_days": period_days,
                "current_status": {
                    "current_tier": user_status["current_tier"],
                    "total_points": user_status["current_points"],
                    "lifetime_points": user_status["lifetime_points"],
                    "member_since": user_status["member_since"].isoformat() if user_status["member_since"] else None,
                    "tier_benefits": user_status["tier_benefits"]
                },
                "earning_analysis": {
                    "total_points_earned": earning_analysis["total_earned"],
                    "average_monthly_earning": earning_analysis["avg_monthly"],
                    "top_earning_activities": earning_analysis["top_activities"],
                    "earning_trend": earning_analysis["trend"],
                    "earning_consistency": earning_analysis["consistency_score"]
                },
                "redemption_analysis": {
                    "total_points_redeemed": redemption_analysis["total_redeemed"],
                    "redemption_frequency": redemption_analysis["frequency"],
                    "preferred_reward_types": redemption_analysis["preferred_types"],
                    "average_redemption_value": redemption_analysis["avg_value"],
                    "redemption_efficiency": redemption_analysis["efficiency_score"]
                },
                "engagement_metrics": {
                    "activity_frequency": engagement_metrics["activity_frequency"],
                    "loyalty_score": engagement_metrics["loyalty_score"],
                    "program_utilization": engagement_metrics["utilization_rate"],
                    "engagement_trend": engagement_metrics["trend"]
                },
                "tier_progression": {
                    "tier_changes": tier_analysis["tier_changes"],
                    "progression_rate": tier_analysis["progression_rate"],
                    "tier_maintenance": tier_analysis["maintenance_score"],
                    "next_tier_progress": tier_analysis["next_tier_progress"]
                },
                "value_analysis": {
                    "total_value_earned": value_analysis["total_value"],
                    "program_roi": value_analysis["roi_percentage"],
                    "value_per_interaction": value_analysis["value_per_action"],
                    "cost_savings": value_analysis["cost_savings"]
                },
                "recommendations": await self._generate_loyalty_recommendations(
                    user_id, earning_analysis, redemption_analysis, engagement_metrics
                ),
                "upcoming_opportunities": await self._identify_upcoming_opportunities(
                    user_id, user_status
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get loyalty analytics: {e}")
            raise
    
    async def update_reward_programs(
        self,
        program_updates: Dict[str, Any],
        admin_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update reward programs and tiers"""
        
        try:
            # Validate admin permissions
            if not admin_context or not admin_context.get("admin_privileges"):
                return {"success": False, "error": "Admin privileges required"}
            
            # Process program updates
            update_results = []
            
            for program_id, updates in program_updates.items():
                result = await self._update_reward_program(program_id, updates)
                update_results.append(result)
            
            # Recalculate affected user statuses
            affected_users = await self._identify_affected_users(program_updates)
            recalculation_results = []
            
            for user_id in affected_users:
                recalc_result = await self._recalculate_user_status(user_id)
                recalculation_results.append(recalc_result)
            
            # Update program configurations
            await self._update_program_configurations(program_updates)
            
            return {
                "success": True,
                "program_updates": update_results,
                "affected_users": len(affected_users),
                "recalculation_results": recalculation_results,
                "effective_date": datetime.utcnow().isoformat(),
                "admin_user": admin_context.get("admin_user_id"),
                "update_summary": await self._generate_update_summary(program_updates)
            }
            
        except Exception as e:
            logger.error(f"Failed to update reward programs: {e}")
            raise
    
    # Helper methods
    
    async def _get_user_reward_status(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's current reward status"""
        
        result = await self.db.execute(
            select(UserRewardStatus).where(UserRewardStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()
        
        if not status:
            # Create initial status for new user
            status = UserRewardStatus(
                user_id=user_id,
                current_tier="bronze",
                current_points=0,
                lifetime_points=0,
                member_since=datetime.utcnow()
            )
            self.db.add(status)
            await self.db.commit()
        
        return {
            "current_tier": status.current_tier,
            "current_points": status.current_points,
            "lifetime_points": status.lifetime_points,
            "member_since": status.member_since,
            "tier_benefits": await self._get_tier_benefits(status.current_tier),
            "next_tier_requirements": await self._get_next_tier_requirements(status.current_tier, status.lifetime_points)
        }
    
    async def _get_active_reward_programs(self) -> List[Dict[str, Any]]:
        """Get all active reward programs"""
        
        result = await self.db.execute(
            select(RewardProgram).where(
                and_(
                    RewardProgram.is_active == True,
                    RewardProgram.start_date <= datetime.utcnow(),
                    or_(
                        RewardProgram.end_date.is_(None),
                        RewardProgram.end_date >= datetime.utcnow()
                    )
                )
            )
        )
        programs = result.scalars().all()
        
        return [
            {
                "id": str(program.id),
                "name": program.program_name,
                "type": program.program_type,
                "multiplier": float(program.point_multiplier),
                "rules": program.reward_rules or {},
                "tier_bonuses": program.tier_bonuses or {}
            }
            for program in programs
        ]
    
    async def _calculate_action_reward(
        self,
        user_id: uuid.UUID,
        action: Dict[str, Any],
        active_programs: List[Dict[str, Any]],
        user_reward_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate rewards for a specific action"""
        
        action_type = action.get("type", "unknown")
        base_points = 0
        
        # Base point calculations by action type
        point_mappings = {
            "choice_made": 10,
            "comparison_completed": 15,
            "optimization_accepted": 20,
            "feedback_provided": 5,
            "feature_usage": 8,
            "referral_made": 50,
            "early_adoption": 25,
            "data_sharing_consent": 12,
            "privacy_review": 8
        }
        
        base_points = point_mappings.get(action_type, 5)  # Default 5 points
        
        # Apply program multipliers
        total_multiplier = 1.0
        program_bonuses = []
        
        for program in active_programs:
            if action_type in program["rules"].get("eligible_actions", []):
                multiplier = program["multiplier"]
                total_multiplier *= multiplier
                program_bonuses.append({
                    "program": program["name"],
                    "multiplier": multiplier,
                    "bonus_points": base_points * (multiplier - 1)
                })
        
        # Apply tier bonuses
        tier_bonus = user_reward_status["tier_benefits"].get("point_multiplier", 1.0)
        total_multiplier *= tier_bonus
        
        final_points = int(base_points * total_multiplier)
        
        return {
            "action": action,
            "base_points": base_points,
            "multipliers": total_multiplier,
            "program_bonuses": program_bonuses,
            "tier_bonus": tier_bonus,
            "points_earned": final_points,
            "calculation_details": {
                "base_calculation": f"{base_points} base points",
                "program_multiplier": f"×{total_multiplier:.2f}",
                "final_result": f"{final_points} points"
            }
        }
    
    async def _apply_loyalty_bonuses(
        self,
        user_id: uuid.UUID,
        base_points: int,
        user_reward_status: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Apply additional loyalty bonuses"""
        
        bonus_points = 0
        bonuses_applied = []
        
        # Consecutive day bonus
        consecutive_days = await self._calculate_consecutive_activity_days(user_id)
        if consecutive_days >= 7:
            consecutive_bonus = min(consecutive_days, 30) * 2  # Cap at 30 days
            bonus_points += consecutive_bonus
            bonuses_applied.append({
                "type": "consecutive_days",
                "days": consecutive_days,
                "bonus_points": consecutive_bonus
            })
        
        # High activity bonus
        monthly_activity = await self._calculate_monthly_activity_score(user_id)
        if monthly_activity >= 100:  # High activity threshold
            activity_bonus = int(base_points * 0.2)  # 20% bonus
            bonus_points += activity_bonus
            bonuses_applied.append({
                "type": "high_activity",
                "activity_score": monthly_activity,
                "bonus_points": activity_bonus
            })
        
        # Milestone bonus
        lifetime_points = user_reward_status["lifetime_points"]
        milestone_bonus = await self._check_milestone_bonus(lifetime_points + base_points)
        if milestone_bonus > 0:
            bonus_points += milestone_bonus
            bonuses_applied.append({
                "type": "milestone",
                "milestone_points": lifetime_points + base_points,
                "bonus_points": milestone_bonus
            })
        
        # Context-based bonuses
        if context:
            if context.get("special_event", False):
                event_bonus = int(base_points * 0.5)  # 50% bonus for special events
                bonus_points += event_bonus
                bonuses_applied.append({
                    "type": "special_event",
                    "event": context.get("event_name", "Special Event"),
                    "bonus_points": event_bonus
                })
        
        return {
            "base_points": base_points,
            "bonus_points": bonus_points,
            "total_bonus_percentage": (bonus_points / base_points * 100) if base_points > 0 else 0,
            "bonuses_applied": bonuses_applied,
            "bonus_summary": f"{bonus_points} bonus points from {len(bonuses_applied)} bonuses"
        }
    
    async def _check_tier_progression(
        self,
        user_id: uuid.UUID,
        user_reward_status: Dict[str, Any],
        points_earned: int
    ) -> Dict[str, Any]:
        """Check if user qualifies for tier progression"""
        
        current_tier = user_reward_status["current_tier"]
        current_lifetime_points = user_reward_status["lifetime_points"]
        new_lifetime_points = current_lifetime_points + points_earned
        
        # Define tier thresholds
        tier_thresholds = {
            "bronze": 0,
            "silver": 1000,
            "gold": 5000,
            "platinum": 15000,
            "diamond": 50000
        }
        
        # Determine new tier
        new_tier = "bronze"
        for tier, threshold in sorted(tier_thresholds.items(), key=lambda x: x[1], reverse=True):
            if new_lifetime_points >= threshold:
                new_tier = tier
                break
        
        tier_changed = new_tier != current_tier
        
        progression_result = {
            "tier_changed": tier_changed,
            "previous_tier": current_tier,
            "new_tier": new_tier,
            "lifetime_points": new_lifetime_points,
            "next_tier_threshold": None,
            "progress_to_next": 0
        }
        
        if tier_changed:
            # Update user's tier
            await self._update_user_tier(user_id, new_tier)
            progression_result["tier_upgrade_benefits"] = await self._get_tier_upgrade_benefits(current_tier, new_tier)
        
        # Calculate progress to next tier
        tier_order = ["bronze", "silver", "gold", "platinum", "diamond"]
        if new_tier in tier_order:
            current_index = tier_order.index(new_tier)
            if current_index < len(tier_order) - 1:
                next_tier = tier_order[current_index + 1]
                next_threshold = tier_thresholds[next_tier]
                progression_result["next_tier_threshold"] = next_threshold
                progression_result["progress_to_next"] = (new_lifetime_points / next_threshold) * 100
        
        return progression_result
    
    async def _get_available_rewards(
        self,
        user_id: uuid.UUID,
        user_reward_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get rewards available for redemption"""
        
        user_points = user_reward_status["current_points"]
        user_tier = user_reward_status["current_tier"]
        
        # Get rewards from database
        result = await self.db.execute(
            select(LoyaltyReward).where(
                and_(
                    LoyaltyReward.is_active == True,
                    LoyaltyReward.points_required <= user_points,
                    or_(
                        LoyaltyReward.required_tier.is_(None),
                        LoyaltyReward.required_tier == user_tier,
                        LoyaltyReward.required_tier.in_(await self._get_eligible_tiers(user_tier))
                    )
                )
            ).order_by(LoyaltyReward.points_required.asc())
        )
        rewards = result.scalars().all()
        
        available_rewards = []
        for reward in rewards:
            reward_details = {
                "reward_id": str(reward.id),
                "name": reward.reward_name,
                "description": reward.description,
                "type": reward.reward_type.value,
                "points_required": reward.points_required,
                "monetary_value": float(reward.monetary_value) if reward.monetary_value else None,
                "availability": "available",
                "tier_requirement": reward.required_tier,
                "expiration_date": reward.expiration_date.isoformat() if reward.expiration_date else None,
                "redemption_details": reward.redemption_details or {},
                "estimated_delivery": await self._estimate_reward_delivery(reward)
            }
            available_rewards.append(reward_details)
        
        return available_rewards
    
    async def _generate_redemption_recommendations(
        self,
        user_id: uuid.UUID,
        user_reward_status: Dict[str, Any],
        new_points: int
    ) -> List[Dict[str, Any]]:
        """Generate personalized redemption recommendations"""
        
        total_points = user_reward_status["current_points"] + new_points
        recommendations = []
        
        # Get user's redemption history to understand preferences
        redemption_history = await self._get_user_redemption_history(user_id)
        
        # Recommend based on previous preferences
        if redemption_history:
            preferred_types = await self._analyze_preferred_reward_types(redemption_history)
            for reward_type in preferred_types[:2]:  # Top 2 preferred types
                reward = await self._find_best_reward_by_type(reward_type, total_points)
                if reward:
                    recommendations.append({
                        "reward": reward,
                        "reason": f"Based on your preference for {reward_type} rewards",
                        "confidence": 0.8
                    })
        
        # Recommend high-value rewards
        high_value_reward = await self._find_highest_value_affordable_reward(total_points)
        if high_value_reward:
            recommendations.append({
                "reward": high_value_reward,
                "reason": "Best value for your points",
                "confidence": 0.9
            })
        
        # Recommend rewards expiring soon
        expiring_rewards = await self._find_expiring_affordable_rewards(total_points)
        for reward in expiring_rewards[:1]:  # One expiring reward
            recommendations.append({
                "reward": reward,
                "reason": "Limited time availability",
                "confidence": 0.7
            })
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def _check_achievement_unlocks(
        self,
        user_id: uuid.UUID,
        actions: List[Dict[str, Any]],
        user_reward_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check if user unlocked any achievements"""
        
        achievements = []
        
        # Choice Master Achievement
        choice_actions = [a for a in actions if a.get("type") == "choice_made"]
        if len(choice_actions) >= 10:
            total_choices = await self._get_user_total_choices(user_id)
            if total_choices >= 100:
                achievements.append({
                    "achievement": "Choice Master",
                    "description": "Made 100 intelligent choices",
                    "bonus_points": 500,
                    "rarity": "rare"
                })
        
        # Optimization Expert Achievement
        optimization_actions = [a for a in actions if a.get("type") == "optimization_accepted"]
        if len(optimization_actions) >= 5:
            achievements.append({
                "achievement": "Optimization Expert",
                "description": "Accepted multiple optimization suggestions",
                "bonus_points": 200,
                "rarity": "uncommon"
            })
        
        # Feedback Champion Achievement
        feedback_actions = [a for a in actions if a.get("type") == "feedback_provided"]
        if len(feedback_actions) >= 3:
            achievements.append({
                "achievement": "Feedback Champion",
                "description": "Provided valuable feedback",
                "bonus_points": 100,
                "rarity": "common"
            })
        
        return achievements
    
    # Additional helper methods for reward redemption, analytics, etc.
    
    async def _validate_redemption_request(
        self,
        user_id: uuid.UUID,
        redemption_request: Dict[str, Any],
        user_reward_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate reward redemption request"""
        
        reward_id = redemption_request.get("reward_id")
        if not reward_id:
            return {"valid": False, "error": "Reward ID required"}
        
        # Get reward details
        reward = await self._get_reward_details(reward_id)
        if not reward:
            return {"valid": False, "error": "Reward not found"}
        
        # Check point balance
        if user_reward_status["current_points"] < reward["points_required"]:
            return {
                "valid": False,
                "error": "Insufficient points",
                "required": reward["points_required"],
                "available": user_reward_status["current_points"]
            }
        
        # Check tier requirement
        if reward.get("required_tier"):
            eligible_tiers = await self._get_eligible_tiers(user_reward_status["current_tier"])
            if reward["required_tier"] not in eligible_tiers:
                return {
                    "valid": False,
                    "error": "Tier requirement not met",
                    "required_tier": reward["required_tier"],
                    "user_tier": user_reward_status["current_tier"]
                }
        
        # Check availability
        if reward.get("stock_limit") and reward.get("redeemed_count", 0) >= reward["stock_limit"]:
            return {"valid": False, "error": "Reward out of stock"}
        
        return {"valid": True}
    
    async def _get_reward_details(self, reward_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a reward"""
        
        result = await self.db.execute(
            select(LoyaltyReward).where(LoyaltyReward.id == uuid.UUID(reward_id))
        )
        reward = result.scalar_one_or_none()
        
        if not reward:
            return None
        
        return {
            "id": str(reward.id),
            "name": reward.reward_name,
            "description": reward.description,
            "type": reward.reward_type.value,
            "points_required": reward.points_required,
            "monetary_value": float(reward.monetary_value) if reward.monetary_value else None,
            "required_tier": reward.required_tier,
            "stock_limit": reward.stock_limit,
            "redeemed_count": reward.redeemed_count or 0,
            "expiration_date": reward.expiration_date,
            "redemption_details": reward.redemption_details or {}
        }
    
    async def _calculate_redemption_cost(
        self,
        reward: Dict[str, Any],
        redemption_request: Dict[str, Any],
        user_reward_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate the cost of redeeming a reward"""
        
        base_cost = reward["points_required"]
        discount_amount = 0
        
        # Apply tier discounts
        tier_discount = user_reward_status["tier_benefits"].get("redemption_discount", 0)
        if tier_discount > 0:
            discount_amount = int(base_cost * tier_discount)
        
        # Apply bulk redemption discount
        quantity = redemption_request.get("quantity", 1)
        if quantity > 1 and reward["type"] in ["service_credit", "discount_code"]:
            bulk_discount = min(quantity * 2, base_cost * 0.1)  # Max 10% bulk discount
            discount_amount += int(bulk_discount)
        
        total_cost = max(1, base_cost - discount_amount)  # Minimum 1 point
        
        return {
            "base_cost": base_cost,
            "discount_amount": discount_amount,
            "total_cost": total_cost,
            "quantity": quantity,
            "cost_per_item": total_cost // quantity if quantity > 0 else total_cost,
            "savings_percentage": (discount_amount / base_cost * 100) if base_cost > 0 else 0
        }
    
    async def _process_reward_redemption(
        self,
        user_id: uuid.UUID,
        reward: Dict[str, Any],
        redemption_calculation: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process the actual reward redemption"""
        
        redemption_id = uuid.uuid4()
        
        # Create redemption record
        redemption = RewardTransaction(
            id=redemption_id,
            user_id=user_id,
            reward_id=uuid.UUID(reward["id"]),
            transaction_type="redemption",
            points_amount=-redemption_calculation["total_cost"],  # Negative for redemption
            transaction_date=datetime.utcnow(),
            transaction_details={
                "reward_name": reward["name"],
                "quantity": redemption_calculation["quantity"],
                "discount_applied": redemption_calculation["discount_amount"]
            }
        )
        
        self.db.add(redemption)
        
        # Generate reward fulfillment details
        fulfillment_details = await self._generate_fulfillment_details(reward, redemption_calculation)
        
        await self.db.commit()
        
        return {
            "redemption_id": str(redemption_id),
            "fulfillment_details": fulfillment_details,
            "processing_status": "completed",
            "estimated_delivery": await self._estimate_reward_delivery(reward)
        }
    
    # Placeholder methods for completeness (would be fully implemented in production)
    
    async def _get_tier_benefits(self, tier: str) -> Dict[str, Any]:
        """Get benefits for a specific tier"""
        tier_benefits = {
            "bronze": {"point_multiplier": 1.0, "redemption_discount": 0.0},
            "silver": {"point_multiplier": 1.1, "redemption_discount": 0.05},
            "gold": {"point_multiplier": 1.2, "redemption_discount": 0.10},
            "platinum": {"point_multiplier": 1.3, "redemption_discount": 0.15},
            "diamond": {"point_multiplier": 1.5, "redemption_discount": 0.20}
        }
        return tier_benefits.get(tier, tier_benefits["bronze"])
    
    async def _get_next_tier_requirements(self, current_tier: str, current_points: int) -> Dict[str, Any]:
        """Get requirements for next tier"""
        tier_thresholds = {
            "bronze": 1000,
            "silver": 5000,
            "gold": 15000,
            "platinum": 50000,
            "diamond": None
        }
        
        if current_tier == "diamond":
            return {"next_tier": None, "points_needed": 0}
        
        tier_order = ["bronze", "silver", "gold", "platinum", "diamond"]
        current_index = tier_order.index(current_tier)
        next_tier = tier_order[current_index + 1]
        points_needed = tier_thresholds[next_tier] - current_points
        
        return {
            "next_tier": next_tier,
            "points_needed": max(0, points_needed),
            "threshold": tier_thresholds[next_tier]
        }
    
    async def _store_reward_transactions(self, user_id: uuid.UUID, action_rewards: List[Dict[str, Any]], bonus_calculation: Dict[str, Any], tier_update: Dict[str, Any]):
        """Store reward transactions in database"""
        # Implementation would store all reward earning transactions
        pass
    
    async def _calculate_consecutive_activity_days(self, user_id: uuid.UUID) -> int:
        """Calculate consecutive days of activity"""
        return 5  # Placeholder
    
    async def _calculate_monthly_activity_score(self, user_id: uuid.UUID) -> int:
        """Calculate user's monthly activity score"""
        return 75  # Placeholder
    
    async def _check_milestone_bonus(self, lifetime_points: int) -> int:
        """Check if user hit a milestone for bonus points"""
        milestones = [1000, 5000, 10000, 25000, 50000]
        for milestone in milestones:
            if lifetime_points == milestone:
                return milestone // 10  # 10% of milestone as bonus
        return 0
    
    async def _update_user_tier(self, user_id: uuid.UUID, new_tier: str):
        """Update user's tier in database"""
        result = await self.db.execute(
            select(UserRewardStatus).where(UserRewardStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()
        if status:
            status.current_tier = new_tier
            await self.db.commit()
    
    async def _get_tier_upgrade_benefits(self, old_tier: str, new_tier: str) -> Dict[str, Any]:
        """Get benefits from tier upgrade"""
        return {
            "new_point_multiplier": (await self._get_tier_benefits(new_tier))["point_multiplier"],
            "new_redemption_discount": (await self._get_tier_benefits(new_tier))["redemption_discount"],
            "welcome_bonus": 100,  # Points bonus for tier upgrade
            "exclusive_rewards_unlocked": 5
        }
    
    async def _get_eligible_tiers(self, user_tier: str) -> List[str]:
        """Get tiers that user is eligible for (current and below)"""
        tier_hierarchy = ["bronze", "silver", "gold", "platinum", "diamond"]
        user_index = tier_hierarchy.index(user_tier) if user_tier in tier_hierarchy else 0
        return tier_hierarchy[:user_index + 1]
    
    async def _estimate_reward_delivery(self, reward: Dict[str, Any]) -> str:
        """Estimate reward delivery time"""
        reward_type = reward.get("type", "unknown")
        delivery_times = {
            "discount_code": "Immediate",
            "service_credit": "1-2 business days",
            "physical_item": "5-7 business days",
            "experience": "Subject to availability"
        }
        return delivery_times.get(reward_type, "3-5 business days")
    
    # Analytics helper methods (simplified implementations)
    
    async def _analyze_earning_patterns(self, transactions: List[RewardTransaction]) -> Dict[str, Any]:
        """Analyze user's earning patterns"""
        earning_transactions = [t for t in transactions if t.points_amount > 0]
        total_earned = sum(t.points_amount for t in earning_transactions)
        
        return {
            "total_earned": total_earned,
            "avg_monthly": total_earned / 3 if len(earning_transactions) > 0 else 0,  # Assume 3 months
            "top_activities": ["choice_made", "optimization_accepted"],
            "trend": "increasing",
            "consistency_score": 0.8
        }
    
    async def _analyze_redemption_patterns(self, user_id: uuid.UUID, transactions: List[RewardTransaction], period_days: int) -> Dict[str, Any]:
        """Analyze user's redemption patterns"""
        redemption_transactions = [t for t in transactions if t.points_amount < 0]
        total_redeemed = abs(sum(t.points_amount for t in redemption_transactions))
        
        return {
            "total_redeemed": total_redeemed,
            "frequency": "monthly",
            "preferred_types": ["service_credit", "discount_code"],
            "avg_value": total_redeemed / max(1, len(redemption_transactions)),
            "efficiency_score": 0.75
        }
    
    async def _calculate_engagement_metrics(self, user_id: uuid.UUID, transactions: List[RewardTransaction], period_days: int) -> Dict[str, Any]:
        """Calculate engagement metrics"""
        return {
            "activity_frequency": "high",
            "loyalty_score": 8.5,
            "utilization_rate": 0.85,
            "trend": "stable"
        }
    
    async def _analyze_tier_progression(self, user_id: uuid.UUID, period_days: int) -> Dict[str, Any]:
        """Analyze tier progression"""
        return {
            "tier_changes": 1,
            "progression_rate": "normal",
            "maintenance_score": 0.9,
            "next_tier_progress": 0.65
        }
    
    async def _calculate_program_value(self, user_id: uuid.UUID, transactions: List[RewardTransaction], period_days: int) -> Dict[str, Any]:
        """Calculate program value for user"""
        return {
            "total_value": 150.00,
            "roi_percentage": 125,
            "value_per_action": 5.50,
            "cost_savings": 75.00
        }
    
    # Additional placeholder methods
    async def _generate_loyalty_recommendations(self, user_id: uuid.UUID, earning_analysis: Dict[str, Any], redemption_analysis: Dict[str, Any], engagement_metrics: Dict[str, Any]) -> List[str]:
        return ["Consider redeeming points for service credits", "Participate in bonus point events"]
    
    async def _identify_upcoming_opportunities(self, user_id: uuid.UUID, user_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"opportunity": "Double points weekend", "start_date": "2024-01-15", "potential_points": 200}]
    
    async def _update_reward_program(self, program_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return {"program_id": program_id, "updated": True, "changes": len(updates)}
    
    async def _identify_affected_users(self, program_updates: Dict[str, Any]) -> List[uuid.UUID]:
        return []  # Would return list of affected user IDs
    
    async def _recalculate_user_status(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"user_id": str(user_id), "recalculated": True}
    
    async def _update_program_configurations(self, program_updates: Dict[str, Any]):
        pass  # Would update program configurations
    
    async def _generate_update_summary(self, program_updates: Dict[str, Any]) -> Dict[str, Any]:
        return {"programs_updated": len(program_updates), "effective_immediately": True}