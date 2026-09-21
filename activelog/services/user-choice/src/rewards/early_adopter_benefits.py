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
    User, UserChoice, ChoiceType, EarlyAdopterBenefit,
    AdopterTier, BetaProgram, EarlyAccessFeature,
    AdopterReward, BenefitType
)

logger = logging.getLogger(__name__)

class EarlyAdopterBenefits:
    """Comprehensive early adopter benefits system for rewarding early users and beta testers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def assess_early_adopter_status(
        self,
        user_id: uuid.UUID,
        assessment_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Assess user's early adopter status and benefits eligibility"""
        
        try:
            # Get user information
            user = await self._get_user_info(user_id)
            
            if not user:
                return {"success": False, "error": "User not found"}
            
            # Calculate early adopter metrics
            adopter_metrics = await self._calculate_adopter_metrics(user_id, user)
            
            # Determine adopter tier
            adopter_tier = await self._determine_adopter_tier(adopter_metrics, user)
            
            # Get available benefits
            available_benefits = await self._get_available_benefits(user_id, adopter_tier)
            
            # Check beta program eligibility
            beta_eligibility = await self._assess_beta_program_eligibility(user_id, adopter_metrics)
            
            # Calculate exclusive access features
            exclusive_features = await self._get_exclusive_access_features(user_id, adopter_tier)
            
            # Generate benefit recommendations
            benefit_recommendations = await self._generate_benefit_recommendations(
                user_id, adopter_metrics, adopter_tier
            )
            
            # Check for special recognition
            special_recognition = await self._check_special_recognition(user_id, adopter_metrics)
            
            return {
                "user_id": str(user_id),
                "early_adopter_status": {
                    "is_early_adopter": adopter_metrics["is_early_adopter"],
                    "adopter_tier": adopter_tier["tier_name"],
                    "tier_level": adopter_tier["tier_level"],
                    "join_date": user["join_date"].isoformat(),
                    "days_since_launch": adopter_metrics["days_since_launch"],
                    "early_adopter_score": adopter_metrics["early_adopter_score"]
                },
                "adopter_metrics": adopter_metrics,
                "tier_benefits": adopter_tier["benefits"],
                "available_benefits": available_benefits,
                "beta_program_eligibility": beta_eligibility,
                "exclusive_features": exclusive_features,
                "benefit_recommendations": benefit_recommendations,
                "special_recognition": special_recognition,
                "next_tier_requirements": await self._get_next_tier_requirements(adopter_tier),
                "legacy_status": await self._check_legacy_status(user_id, user),
                "assessment_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to assess early adopter status: {e}")
            raise
    
    async def claim_early_adopter_benefit(
        self,
        user_id: uuid.UUID,
        benefit_id: uuid.UUID,
        claim_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Claim an early adopter benefit"""
        
        try:
            # Validate benefit eligibility
            eligibility_check = await self._validate_benefit_eligibility(user_id, benefit_id)
            
            if not eligibility_check["eligible"]:
                return {
                    "success": False,
                    "error": eligibility_check["reason"],
                    "requirements": eligibility_check.get("requirements", [])
                }
            
            # Get benefit details
            benefit = eligibility_check["benefit"]
            
            # Process benefit claim
            claim_result = await self._process_benefit_claim(
                user_id, benefit, claim_context
            )
            
            # Update user's benefit status
            await self._update_user_benefit_status(user_id, benefit, claim_result)
            
            # Generate benefit delivery
            delivery_details = await self._generate_benefit_delivery(
                user_id, benefit, claim_result
            )
            
            # Record benefit usage analytics
            await self._record_benefit_analytics(user_id, benefit, claim_result)
            
            return {
                "success": True,
                "user_id": str(user_id),
                "benefit_claimed": {
                    "benefit_id": str(benefit_id),
                    "benefit_name": benefit["name"],
                    "benefit_type": benefit["type"],
                    "benefit_value": benefit["value"],
                    "claim_date": datetime.utcnow().isoformat()
                },
                "delivery_details": delivery_details,
                "claim_confirmation": claim_result["confirmation"],
                "remaining_benefits": await self._get_remaining_benefits(user_id),
                "next_benefit_unlock": await self._get_next_benefit_unlock(user_id),
                "special_messages": await self._generate_claim_messages(user_id, benefit),
                "claim_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to claim early adopter benefit: {e}")
            raise
    
    async def enroll_beta_program(
        self,
        user_id: uuid.UUID,
        program_id: uuid.UUID,
        enrollment_preferences: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Enroll user in a beta program"""
        
        try:
            # Get beta program details
            program = await self._get_beta_program(program_id)
            
            if not program:
                return {"success": False, "error": "Beta program not found"}
            
            # Check enrollment eligibility
            eligibility = await self._check_beta_program_eligibility(user_id, program)
            
            if not eligibility["eligible"]:
                return {
                    "success": False,
                    "error": eligibility["reason"],
                    "requirements": eligibility.get("requirements", [])
                }
            
            # Process enrollment
            enrollment_result = await self._process_beta_enrollment(
                user_id, program, enrollment_preferences
            )
            
            # Set up beta access
            beta_access = await self._setup_beta_access(user_id, program)
            
            # Generate onboarding materials
            onboarding = await self._generate_beta_onboarding(user_id, program)
            
            # Schedule beta communications
            await self._schedule_beta_communications(user_id, program)
            
            return {
                "success": True,
                "user_id": str(user_id),
                "enrollment_confirmed": True,
                "beta_program": {
                    "program_id": str(program_id),
                    "program_name": program["name"],
                    "program_type": program["type"],
                    "start_date": program["start_date"].isoformat(),
                    "expected_duration": program["duration_weeks"],
                    "participant_benefits": program["benefits"]
                },
                "beta_access": beta_access,
                "onboarding": onboarding,
                "expectations": {
                    "feedback_frequency": program["feedback_requirements"]["frequency"],
                    "testing_commitment": program["testing_requirements"],
                    "communication_channels": program["communication_channels"]
                },
                "exclusive_perks": await self._get_beta_program_perks(user_id, program),
                "enrollment_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to enroll in beta program: {e}")
            raise
    
    async def track_early_adopter_activity(
        self,
        user_id: uuid.UUID,
        activities: List[Dict[str, Any]],
        tracking_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track early adopter activities and update benefits accordingly"""
        
        try:
            # Get current adopter status
            current_status = await self._get_current_adopter_status(user_id)
            
            # Process each activity
            activity_results = []
            total_points_earned = 0
            
            for activity in activities:
                result = await self._process_adopter_activity(
                    user_id, activity, current_status
                )
                activity_results.append(result)
                total_points_earned += result.get("points_earned", 0)
            
            # Check for tier progression
            tier_progression = await self._check_tier_progression(
                user_id, current_status, total_points_earned
            )
            
            # Check for new benefit unlocks
            benefit_unlocks = await self._check_benefit_unlocks(
                user_id, current_status, activities, total_points_earned
            )
            
            # Update achievement progress
            achievement_progress = await self._update_achievement_progress(
                user_id, activities
            )
            
            # Generate activity insights
            activity_insights = await self._generate_activity_insights(
                user_id, activities, activity_results
            )
            
            return {
                "user_id": str(user_id),
                "activity_tracking": {
                    "activities_processed": len(activities),
                    "total_points_earned": total_points_earned,
                    "activity_results": activity_results
                },
                "status_updates": {
                    "tier_progression": tier_progression,
                    "benefit_unlocks": benefit_unlocks,
                    "achievement_progress": achievement_progress
                },
                "current_status": {
                    "adopter_tier": current_status["tier_name"],
                    "total_points": current_status["total_points"] + total_points_earned,
                    "benefits_claimed": current_status["benefits_claimed"],
                    "beta_programs": current_status["active_beta_programs"]
                },
                "insights": activity_insights,
                "recommendations": await self._generate_activity_recommendations(
                    user_id, activity_results, current_status
                ),
                "tracking_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track early adopter activity: {e}")
            raise
    
    async def get_early_adopter_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 90,
        analytics_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get comprehensive early adopter analytics"""
        
        try:
            # Get user's early adopter journey
            adopter_journey = await self._analyze_adopter_journey(user_id, period_days)
            
            # Get benefit utilization analytics
            benefit_analytics = await self._analyze_benefit_utilization(user_id, period_days)
            
            # Get beta program participation
            beta_participation = await self._analyze_beta_participation(user_id)
            
            # Calculate early adopter value
            adopter_value = await self._calculate_adopter_value(user_id, period_days)
            
            # Get community standing
            community_standing = await self._analyze_community_standing(user_id)
            
            # Generate insights and predictions
            insights = await self._generate_adopter_insights(
                user_id, adopter_journey, benefit_analytics, beta_participation
            )
            
            analytics_result = {
                "user_id": str(user_id),
                "period_days": period_days,
                "early_adopter_journey": adopter_journey,
                "benefit_analytics": benefit_analytics,
                "beta_program_analytics": beta_participation,
                "value_analysis": adopter_value,
                "community_standing": community_standing,
                "insights_and_predictions": insights,
                "recommendations": await self._generate_adopter_recommendations(
                    user_id, analytics_result
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # Add detailed breakdown for comprehensive analytics
            if analytics_type == "comprehensive":
                analytics_result["detailed_breakdown"] = {
                    "monthly_activity_trends": await self._analyze_monthly_trends(user_id, 12),
                    "feature_adoption_timeline": await self._analyze_feature_adoption(user_id),
                    "feedback_contribution_analysis": await self._analyze_feedback_contributions(user_id),
                    "peer_comparison": await self._generate_peer_comparison(user_id),
                    "future_opportunities": await self._identify_future_opportunities(user_id)
                }
            
            return analytics_result
            
        except Exception as e:
            logger.error(f"Failed to get early adopter analytics: {e}")
            raise
    
    # Helper methods
    
    async def _get_user_info(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """Get basic user information"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        return {
            "user_id": str(user.id),
            "join_date": user.created_date,
            "email": user.email,
            "user_type": getattr(user, 'user_type', 'regular')
        }
    
    async def _calculate_adopter_metrics(
        self,
        user_id: uuid.UUID,
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate early adopter metrics"""
        
        # Platform launch date (would be configurable)
        PLATFORM_LAUNCH = datetime(2024, 1, 1)
        EARLY_ADOPTER_CUTOFF = PLATFORM_LAUNCH + timedelta(days=90)  # First 90 days
        
        join_date = user["join_date"]
        days_since_launch = (join_date - PLATFORM_LAUNCH).days
        is_early_adopter = join_date <= EARLY_ADOPTER_CUTOFF
        
        # Calculate adoption speed metrics
        first_choice_date = await self._get_first_choice_date(user_id)
        time_to_first_action = None
        if first_choice_date:
            time_to_first_action = (first_choice_date - join_date).days
        
        # Calculate engagement metrics
        total_choices = await self._get_total_user_choices(user_id)
        feature_usage_count = await self._get_feature_usage_count(user_id)
        
        # Calculate early adopter score
        early_adopter_score = await self._calculate_early_adopter_score(
            days_since_launch, total_choices, feature_usage_count, time_to_first_action
        )
        
        return {
            "is_early_adopter": is_early_adopter,
            "join_date": join_date,
            "days_since_launch": days_since_launch,
            "days_since_join": (datetime.utcnow() - join_date).days,
            "time_to_first_action": time_to_first_action,
            "total_choices": total_choices,
            "feature_usage_count": feature_usage_count,
            "early_adopter_score": early_adopter_score,
            "adoption_speed": "fast" if time_to_first_action and time_to_first_action <= 1 else "normal"
        }
    
    async def _determine_adopter_tier(
        self,
        adopter_metrics: Dict[str, Any],
        user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine user's early adopter tier"""
        
        if not adopter_metrics["is_early_adopter"]:
            return {
                "tier_name": "regular",
                "tier_level": 0,
                "benefits": [],
                "tier_requirements": "Not an early adopter"
            }
        
        score = adopter_metrics["early_adopter_score"]
        days_since_launch = adopter_metrics["days_since_launch"]
        
        # Define tier thresholds
        if days_since_launch <= 7 and score >= 80:
            tier = "founder"
            tier_level = 5
        elif days_since_launch <= 30 and score >= 70:
            tier = "pioneer"
            tier_level = 4
        elif days_since_launch <= 60 and score >= 60:
            tier = "early_supporter"
            tier_level = 3
        elif days_since_launch <= 90 and score >= 50:
            tier = "early_adopter"
            tier_level = 2
        else:
            tier = "beta_user"
            tier_level = 1
        
        # Get tier benefits
        tier_benefits = await self._get_tier_benefits(tier)
        
        return {
            "tier_name": tier,
            "tier_level": tier_level,
            "benefits": tier_benefits,
            "tier_requirements": f"Joined within {90 if tier != 'regular' else 'N/A'} days of launch",
            "tier_description": await self._get_tier_description(tier)
        }
    
    async def _get_available_benefits(
        self,
        user_id: uuid.UUID,
        adopter_tier: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get available benefits for user's tier"""
        
        # Get benefits from database
        result = await self.db.execute(
            select(EarlyAdopterBenefit).where(
                and_(
                    EarlyAdopterBenefit.required_tier_level <= adopter_tier["tier_level"],
                    EarlyAdopterBenefit.is_active == True,
                    or_(
                        EarlyAdopterBenefit.expiration_date.is_(None),
                        EarlyAdopterBenefit.expiration_date >= datetime.utcnow()
                    )
                )
            )
        )
        benefits = result.scalars().all()
        
        # Check which benefits user has already claimed
        claimed_benefits = await self._get_claimed_benefits(user_id)
        claimed_benefit_ids = {str(b.benefit_id) for b in claimed_benefits}
        
        available_benefits = []
        for benefit in benefits:
            if str(benefit.id) not in claimed_benefit_ids:
                available_benefits.append({
                    "benefit_id": str(benefit.id),
                    "name": benefit.benefit_name,
                    "description": benefit.description,
                    "type": benefit.benefit_type.value,
                    "value": benefit.benefit_value,
                    "required_tier": benefit.required_tier_level,
                    "claim_deadline": benefit.expiration_date.isoformat() if benefit.expiration_date else None,
                    "estimated_value": float(benefit.estimated_monetary_value) if benefit.estimated_monetary_value else None
                })
        
        return available_benefits
    
    async def _assess_beta_program_eligibility(
        self,
        user_id: uuid.UUID,
        adopter_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Assess eligibility for beta programs"""
        
        # Get active beta programs
        result = await self.db.execute(
            select(BetaProgram).where(
                and_(
                    BetaProgram.is_active == True,
                    BetaProgram.enrollment_end_date >= datetime.utcnow()
                )
            )
        )
        beta_programs = result.scalars().all()
        
        eligible_programs = []
        
        for program in beta_programs:
            eligibility = await self._check_single_program_eligibility(
                user_id, program, adopter_metrics
            )
            
            if eligibility["eligible"]:
                eligible_programs.append({
                    "program_id": str(program.id),
                    "program_name": program.program_name,
                    "description": program.description,
                    "start_date": program.start_date.isoformat(),
                    "duration_weeks": program.duration_weeks,
                    "participant_limit": program.participant_limit,
                    "current_participants": program.current_participants or 0,
                    "eligibility_score": eligibility["score"],
                    "requirements_met": eligibility["requirements_met"]
                })
        
        return {
            "eligible_programs": eligible_programs,
            "total_eligible": len(eligible_programs),
            "eligibility_factors": {
                "early_adopter_status": adopter_metrics["is_early_adopter"],
                "adoption_score": adopter_metrics["early_adopter_score"],
                "activity_level": "high" if adopter_metrics["total_choices"] > 50 else "moderate"
            }
        }
    
    async def _get_exclusive_access_features(
        self,
        user_id: uuid.UUID,
        adopter_tier: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get exclusive access features for user's tier"""
        
        result = await self.db.execute(
            select(EarlyAccessFeature).where(
                and_(
                    EarlyAccessFeature.required_tier_level <= adopter_tier["tier_level"],
                    EarlyAccessFeature.is_active == True,
                    EarlyAccessFeature.access_start_date <= datetime.utcnow()
                )
            )
        )
        features = result.scalars().all()
        
        exclusive_features = []
        for feature in features:
            exclusive_features.append({
                "feature_id": str(feature.id),
                "feature_name": feature.feature_name,
                "description": feature.description,
                "access_type": feature.access_type,
                "required_tier": feature.required_tier_level,
                "access_start_date": feature.access_start_date.isoformat(),
                "general_release_date": feature.general_release_date.isoformat() if feature.general_release_date else None,
                "exclusive_period_days": (feature.general_release_date - feature.access_start_date).days if feature.general_release_date else None
            })
        
        return exclusive_features
    
    async def _generate_benefit_recommendations(
        self,
        user_id: uuid.UUID,
        adopter_metrics: Dict[str, Any],
        adopter_tier: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate personalized benefit recommendations"""
        
        recommendations = []
        
        # Recommend high-value benefits first
        available_benefits = await self._get_available_benefits(user_id, adopter_tier)
        
        # Sort by estimated value
        high_value_benefits = sorted(
            [b for b in available_benefits if b.get("estimated_value", 0) > 50],
            key=lambda x: x.get("estimated_value", 0),
            reverse=True
        )
        
        for benefit in high_value_benefits[:3]:
            recommendations.append({
                "type": "high_value_benefit",
                "benefit_id": benefit["benefit_id"],
                "benefit_name": benefit["name"],
                "recommendation_reason": f"High value benefit worth ${benefit.get('estimated_value', 'unknown')}",
                "urgency": "high" if benefit.get("claim_deadline") else "medium",
                "action": "claim_now"
            })
        
        # Recommend beta program participation if eligible
        beta_eligibility = await self._assess_beta_program_eligibility(user_id, adopter_metrics)
        if beta_eligibility["eligible_programs"]:
            top_program = beta_eligibility["eligible_programs"][0]
            recommendations.append({
                "type": "beta_program",
                "program_id": top_program["program_id"],
                "program_name": top_program["program_name"],
                "recommendation_reason": "Get early access to new features and influence development",
                "urgency": "medium",
                "action": "enroll"
            })
        
        # Recommend tier progression activities
        if adopter_tier["tier_level"] < 5:
            next_tier_requirements = await self._get_next_tier_requirements(adopter_tier)
            if next_tier_requirements:
                recommendations.append({
                    "type": "tier_progression",
                    "current_tier": adopter_tier["tier_name"],
                    "next_tier": next_tier_requirements["next_tier"],
                    "recommendation_reason": "Unlock more exclusive benefits and features",
                    "urgency": "low",
                    "action": "increase_activity"
                })
        
        return recommendations
    
    async def _check_special_recognition(
        self,
        user_id: uuid.UUID,
        adopter_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for special recognition achievements"""
        
        recognitions = []
        
        # Day 1 user recognition
        if adopter_metrics["days_since_launch"] == 0:
            recognitions.append({
                "type": "day_one_user",
                "title": "Day One Pioneer",
                "description": "Among the very first users on launch day",
                "rarity": "legendary",
                "badge_url": "/badges/day-one-pioneer.svg"
            })
        
        # First week user
        elif adopter_metrics["days_since_launch"] <= 7:
            recognitions.append({
                "type": "first_week_user",
                "title": "First Week Explorer",
                "description": "Joined in the first week of launch",
                "rarity": "rare",
                "badge_url": "/badges/first-week-explorer.svg"
            })
        
        # Super early adopter (high activity in first month)
        if (adopter_metrics["days_since_launch"] <= 30 and 
            adopter_metrics["total_choices"] >= 100):
            recognitions.append({
                "type": "super_early_adopter",
                "title": "Super Early Adopter",
                "description": "Highly active user in the first month",
                "rarity": "epic",
                "badge_url": "/badges/super-early-adopter.svg"
            })
        
        # Beta hero (participated in multiple beta programs)
        beta_participation_count = await self._get_beta_participation_count(user_id)
        if beta_participation_count >= 3:
            recognitions.append({
                "type": "beta_hero",
                "title": "Beta Testing Hero",
                "description": f"Participated in {beta_participation_count} beta programs",
                "rarity": "rare",
                "badge_url": "/badges/beta-hero.svg"
            })
        
        return {
            "recognitions": recognitions,
            "total_recognitions": len(recognitions),
            "highest_rarity": max([r["rarity"] for r in recognitions], 
                                 default="common", 
                                 key=lambda x: ["common", "rare", "epic", "legendary"].index(x))
        }
    
    # Additional helper methods (simplified implementations)
    
    async def _calculate_early_adopter_score(
        self,
        days_since_launch: int,
        total_choices: int,
        feature_usage_count: int,
        time_to_first_action: Optional[int]
    ) -> float:
        """Calculate early adopter score"""
        
        score = 0
        
        # Timing score (earlier = higher)
        if days_since_launch <= 7:
            score += 40
        elif days_since_launch <= 30:
            score += 30
        elif days_since_launch <= 60:
            score += 20
        elif days_since_launch <= 90:
            score += 10
        
        # Activity score
        score += min(30, total_choices * 0.5)  # Cap at 30
        
        # Feature adoption score
        score += min(20, feature_usage_count * 2)  # Cap at 20
        
        # Quick adoption bonus
        if time_to_first_action is not None and time_to_first_action <= 1:
            score += 10
        
        return min(100, score)
    
    async def _get_tier_benefits(self, tier: str) -> List[str]:
        """Get benefits for a specific tier"""
        tier_benefits = {
            "founder": [
                "Lifetime premium access",
                "Exclusive founder badge",
                "Priority customer support",
                "Access to founder-only features",
                "Annual founders meetup invitation",
                "Product roadmap input"
            ],
            "pioneer": [
                "6 months premium access",
                "Pioneer badge",
                "Beta program priority",
                "Early feature access",
                "Quarterly feedback sessions"
            ],
            "early_supporter": [
                "3 months premium access",
                "Early supporter badge",
                "Beta program access",
                "Feature preview access"
            ],
            "early_adopter": [
                "1 month premium access",
                "Early adopter badge",
                "Feature sneak peeks"
            ],
            "beta_user": [
                "Beta user badge",
                "Community recognition"
            ]
        }
        return tier_benefits.get(tier, [])
    
    async def _get_tier_description(self, tier: str) -> str:
        """Get description for a tier"""
        descriptions = {
            "founder": "The pioneering users who joined on day one and shaped the platform",
            "pioneer": "Early champions who joined in the first week and helped establish the community",
            "early_supporter": "Dedicated users who joined in the first month and provided valuable feedback",
            "early_adopter": "Forward-thinking users who joined in the first 60 days",
            "beta_user": "Early users who joined during the initial 90-day period"
        }
        return descriptions.get(tier, "Regular user")
    
    async def _get_first_choice_date(self, user_id: uuid.UUID) -> Optional[datetime]:
        """Get date of user's first choice"""
        result = await self.db.execute(
            select(UserChoice.choice_date)
            .where(UserChoice.user_id == user_id)
            .order_by(UserChoice.choice_date.asc())
            .limit(1)
        )
        first_choice = result.scalar_one_or_none()
        return first_choice
    
    async def _get_total_user_choices(self, user_id: uuid.UUID) -> int:
        """Get total number of choices made by user"""
        result = await self.db.execute(
            select(func.count(UserChoice.id)).where(UserChoice.user_id == user_id)
        )
        return result.scalar() or 0
    
    async def _get_feature_usage_count(self, user_id: uuid.UUID) -> int:
        """Get count of distinct features used by user"""
        # Simplified - would count distinct feature usage
        return min(10, await self._get_total_user_choices(user_id) // 5)
    
    async def _get_claimed_benefits(self, user_id: uuid.UUID) -> List[AdopterReward]:
        """Get benefits already claimed by user"""
        result = await self.db.execute(
            select(AdopterReward).where(AdopterReward.user_id == user_id)
        )
        return result.scalars().all()
    
    async def _check_single_program_eligibility(
        self,
        user_id: uuid.UUID,
        program: BetaProgram,
        adopter_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check eligibility for a single beta program"""
        
        eligibility_score = 0
        requirements_met = []
        
        # Check early adopter requirement
        if program.requires_early_adopter and adopter_metrics["is_early_adopter"]:
            eligibility_score += 0.4
            requirements_met.append("Early adopter status")
        elif not program.requires_early_adopter:
            eligibility_score += 0.4
            requirements_met.append("No early adopter requirement")
        
        # Check minimum activity requirement
        if adopter_metrics["total_choices"] >= (program.minimum_activity or 0):
            eligibility_score += 0.3
            requirements_met.append("Minimum activity level")
        
        # Check program capacity
        if (program.current_participants or 0) < (program.participant_limit or 999999):
            eligibility_score += 0.3
            requirements_met.append("Program has capacity")
        
        return {
            "eligible": eligibility_score >= 0.7,
            "score": eligibility_score,
            "requirements_met": requirements_met
        }
    
    async def _get_beta_participation_count(self, user_id: uuid.UUID) -> int:
        """Get number of beta programs user has participated in"""
        # Simplified implementation
        return 1  # Placeholder
    
    async def _get_next_tier_requirements(self, current_tier: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get requirements for next tier"""
        tier_progression = {
            "beta_user": {"next_tier": "early_adopter", "additional_activity": 25},
            "early_adopter": {"next_tier": "early_supporter", "additional_activity": 50},
            "early_supporter": {"next_tier": "pioneer", "additional_activity": 75},
            "pioneer": {"next_tier": "founder", "additional_activity": 100}
        }
        
        return tier_progression.get(current_tier["tier_name"])
    
    async def _check_legacy_status(self, user_id: uuid.UUID, user: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user qualifies for legacy status"""
        
        # Legacy status for very early users with sustained engagement
        days_since_join = (datetime.utcnow() - user["join_date"]).days
        total_activity = await self._get_total_user_choices(user_id)
        
        is_legacy = (
            days_since_join > 180 and  # At least 6 months
            total_activity >= 200      # High activity
        )
        
        return {
            "is_legacy_user": is_legacy,
            "legacy_benefits": ["Legacy user badge", "Grandfather pricing"] if is_legacy else [],
            "qualification_date": user["join_date"].isoformat() if is_legacy else None
        }
    
    # Placeholder methods for benefit claiming, beta enrollment, etc.
    
    async def _validate_benefit_eligibility(self, user_id: uuid.UUID, benefit_id: uuid.UUID) -> Dict[str, Any]:
        result = await self.db.execute(
            select(EarlyAdopterBenefit).where(EarlyAdopterBenefit.id == benefit_id)
        )
        benefit = result.scalar_one_or_none()
        
        if not benefit:
            return {"eligible": False, "reason": "Benefit not found"}
        
        # Check if already claimed
        claimed = await self.db.execute(
            select(AdopterReward).where(
                and_(
                    AdopterReward.user_id == user_id,
                    AdopterReward.benefit_id == benefit_id
                )
            )
        )
        
        if claimed.scalar_one_or_none():
            return {"eligible": False, "reason": "Benefit already claimed"}
        
        return {
            "eligible": True,
            "benefit": {
                "id": str(benefit.id),
                "name": benefit.benefit_name,
                "type": benefit.benefit_type.value,
                "value": benefit.benefit_value
            }
        }
    
    async def _process_benefit_claim(self, user_id: uuid.UUID, benefit: Dict[str, Any], claim_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {"confirmation": f"Benefit {benefit['name']} claimed successfully", "tracking_id": "CLAIM-123"}
    
    async def _update_user_benefit_status(self, user_id: uuid.UUID, benefit: Dict[str, Any], claim_result: Dict[str, Any]):
        # Create reward record
        reward = AdopterReward(
            user_id=user_id,
            benefit_id=uuid.UUID(benefit["id"]),
            reward_type=BenefitType(benefit["type"]),
            reward_value=benefit["value"],
            claim_date=datetime.utcnow(),
            is_claimed=True
        )
        self.db.add(reward)
        await self.db.commit()
    
    async def _generate_benefit_delivery(self, user_id: uuid.UUID, benefit: Dict[str, Any], claim_result: Dict[str, Any]) -> Dict[str, Any]:
        return {"delivery_method": "immediate", "instructions": f"Your {benefit['name']} is now active"}
    
    async def _record_benefit_analytics(self, user_id: uuid.UUID, benefit: Dict[str, Any], claim_result: Dict[str, Any]):
        pass  # Would record analytics
    
    async def _get_remaining_benefits(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        return [{"name": "Premium upgrade", "value": "3 months"}]
    
    async def _get_next_benefit_unlock(self, user_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        return {"benefit": "Exclusive webinar access", "unlock_requirement": "10 more activities"}
    
    async def _generate_claim_messages(self, user_id: uuid.UUID, benefit: Dict[str, Any]) -> List[str]:
        return [f"Congratulations on claiming {benefit['name']}!", "Thank you for being an early adopter!"]
    
    # Additional placeholder methods for beta programs and analytics
    
    async def _get_beta_program(self, program_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        result = await self.db.execute(
            select(BetaProgram).where(BetaProgram.id == program_id)
        )
        program = result.scalar_one_or_none()
        
        if not program:
            return None
        
        return {
            "id": str(program.id),
            "name": program.program_name,
            "type": program.program_type,
            "start_date": program.start_date,
            "duration_weeks": program.duration_weeks,
            "benefits": ["Early access", "Direct developer feedback"],
            "feedback_requirements": {"frequency": "weekly"},
            "testing_requirements": "5 hours per week",
            "communication_channels": ["Slack", "Email"]
        }
    
    async def _check_beta_program_eligibility(self, user_id: uuid.UUID, program: Dict[str, Any]) -> Dict[str, Any]:
        return {"eligible": True, "reason": "Meets all requirements"}
    
    async def _process_beta_enrollment(self, user_id: uuid.UUID, program: Dict[str, Any], enrollment_preferences: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {"enrollment_id": "BETA-456", "status": "enrolled"}
    
    async def _setup_beta_access(self, user_id: uuid.UUID, program: Dict[str, Any]) -> Dict[str, Any]:
        return {"access_token": "beta-token-789", "dashboard_url": "https://beta.activelog.com"}
    
    async def _generate_beta_onboarding(self, user_id: uuid.UUID, program: Dict[str, Any]) -> Dict[str, Any]:
        return {"welcome_guide_url": "https://beta.activelog.com/welcome", "first_tasks": ["Complete profile", "Try new feature"]}
    
    async def _schedule_beta_communications(self, user_id: uuid.UUID, program: Dict[str, Any]):
        pass  # Would schedule communications
    
    async def _get_beta_program_perks(self, user_id: uuid.UUID, program: Dict[str, Any]) -> List[str]:
        return ["Direct line to product team", "Exclusive beta tester badge", "Priority feature requests"]
    
    # Analytics placeholder methods
    
    async def _get_current_adopter_status(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {
            "tier_name": "early_adopter",
            "total_points": 850,
            "benefits_claimed": 3,
            "active_beta_programs": 1
        }
    
    async def _process_adopter_activity(self, user_id: uuid.UUID, activity: Dict[str, Any], current_status: Dict[str, Any]) -> Dict[str, Any]:
        points_map = {"choice_made": 10, "feature_used": 5, "feedback_given": 15}
        points = points_map.get(activity.get("type", "other"), 1)
        return {"activity": activity["type"], "points_earned": points, "processed": True}
    
    async def _check_tier_progression(self, user_id: uuid.UUID, current_status: Dict[str, Any], points_earned: int) -> Dict[str, Any]:
        return {"tier_changed": False, "current_tier": current_status["tier_name"], "points_to_next": 150}
    
    async def _check_benefit_unlocks(self, user_id: uuid.UUID, current_status: Dict[str, Any], activities: List[Dict[str, Any]], points_earned: int) -> List[Dict[str, Any]]:
        return [{"benefit": "New feature preview", "unlocked": True}] if points_earned > 50 else []
    
    async def _update_achievement_progress(self, user_id: uuid.UUID, activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"achievements_updated": 2, "progress": {"choice_master": 0.75, "beta_hero": 0.33}}
    
    async def _generate_activity_insights(self, user_id: uuid.UUID, activities: List[Dict[str, Any]], activity_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"insights": ["High engagement this week", "Consistent feature usage"], "patterns": ["Morning activity peak"]}
    
    async def _generate_activity_recommendations(self, user_id: uuid.UUID, activity_results: List[Dict[str, Any]], current_status: Dict[str, Any]) -> List[str]:
        return ["Try the new comparison feature", "Provide feedback on recent changes"]
    
    # Comprehensive analytics placeholder methods
    
    async def _analyze_adopter_journey(self, user_id: uuid.UUID, period_days: int) -> Dict[str, Any]:
        return {"journey_stage": "advanced_adopter", "milestone_completion": 0.85, "engagement_trend": "increasing"}
    
    async def _analyze_benefit_utilization(self, user_id: uuid.UUID, period_days: int) -> Dict[str, Any]:
        return {"benefits_claimed": 5, "benefits_available": 8, "utilization_rate": 0.625, "value_realized": 250}
    
    async def _analyze_beta_participation(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"programs_joined": 2, "feedback_submissions": 15, "impact_score": 8.5}
    
    async def _calculate_adopter_value(self, user_id: uuid.UUID, period_days: int) -> Dict[str, Any]:
        return {"total_value_received": 500, "contributions_value": 200, "net_value": 300}
    
    async def _analyze_community_standing(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"community_rank": 25, "total_members": 1000, "recognition_score": 7.8}
    
    async def _generate_adopter_insights(self, user_id: uuid.UUID, *args) -> Dict[str, Any]:
        return {"key_insights": ["Highly engaged early adopter", "Strong community contributor"], "predictions": ["Likely to remain long-term user"]}
    
    async def _generate_adopter_recommendations(self, user_id: uuid.UUID, analytics_result: Dict[str, Any]) -> List[str]:
        return ["Consider becoming a community moderator", "Apply for the advanced beta program"]