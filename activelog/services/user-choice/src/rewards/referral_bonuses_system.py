from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any, Tuple
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json
import hashlib

from ..database import (
    User, UserChoice, ChoiceType, ReferralBonus,
    ReferralProgram, ReferralLink, UserReferralStatus,
    ReferralReward, ReferralType
)

logger = logging.getLogger(__name__)

class ReferralBonusesSystem:
    """Comprehensive referral bonuses system for user acquisition and engagement"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_referral_link(
        self,
        referrer_id: uuid.UUID,
        referral_context: Optional[Dict[str, Any]] = None,
        custom_parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a personalized referral link for a user"""
        
        try:
            # Get or create user referral status
            referrer_status = await self._get_user_referral_status(referrer_id)
            
            # Check if user is eligible for referrals
            eligibility_check = await self._check_referral_eligibility(referrer_id, referrer_status)
            
            if not eligibility_check["eligible"]:
                return {
                    "success": False,
                    "error": eligibility_check["reason"],
                    "eligibility_requirements": eligibility_check.get("requirements", [])
                }
            
            # Get active referral programs
            active_programs = await self._get_active_referral_programs()
            
            # Generate unique referral code
            referral_code = await self._generate_referral_code(referrer_id)
            
            # Create referral link
            referral_link = ReferralLink(
                referrer_id=referrer_id,
                referral_code=referral_code,
                program_ids=[p["id"] for p in active_programs],
                context_data=referral_context or {},
                custom_parameters=custom_parameters or {},
                created_date=datetime.utcnow(),
                is_active=True
            )
            
            self.db.add(referral_link)
            await self.db.commit()
            
            # Generate link URL and tracking information
            link_details = await self._generate_link_details(referral_link, active_programs)
            
            # Calculate potential rewards
            potential_rewards = await self._calculate_potential_rewards(
                referrer_id, active_programs, referrer_status
            )
            
            return {
                "success": True,
                "referrer_id": str(referrer_id),
                "referral_link": link_details,
                "potential_rewards": potential_rewards,
                "active_programs": [
                    {
                        "name": program["name"],
                        "description": program["description"],
                        "reward_structure": program["reward_structure"]
                    }
                    for program in active_programs
                ],
                "sharing_tools": await self._generate_sharing_tools(
                    link_details, referrer_status, potential_rewards
                ),
                "tracking_dashboard_url": await self._generate_tracking_dashboard_url(referrer_id),
                "terms_and_conditions": await self._get_referral_terms(),
                "creation_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create referral link: {e}")
            raise
    
    async def process_referral_signup(
        self,
        referral_code: str,
        new_user_data: Dict[str, Any],
        signup_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a new user signup from a referral"""
        
        try:
            # Validate referral code
            referral_validation = await self._validate_referral_code(referral_code)
            
            if not referral_validation["valid"]:
                return {
                    "success": False,
                    "error": referral_validation["error"],
                    "signup_processed": True,  # Still process signup, just no referral bonus
                    "new_user_id": new_user_data.get("user_id")
                }
            
            referral_link = referral_validation["referral_link"]
            referrer_id = referral_link.referrer_id
            
            # Check for fraud/abuse
            fraud_check = await self._check_referral_fraud(
                referrer_id, new_user_data, signup_context
            )
            
            if fraud_check["suspicious"]:
                logger.warning(f"Suspicious referral activity detected: {fraud_check['reasons']}")
                # Continue processing but flag for review
            
            # Get active referral programs
            active_programs = await self._get_referral_programs_by_ids(referral_link.program_ids)
            
            # Calculate referral rewards
            reward_calculations = []
            for program in active_programs:
                calculation = await self._calculate_referral_reward(
                    referrer_id, new_user_data["user_id"], program, referral_link
                )
                reward_calculations.append(calculation)
            
            # Create referral bonus records
            referral_bonus = ReferralBonus(
                referrer_id=referrer_id,
                referred_user_id=uuid.UUID(new_user_data["user_id"]),
                referral_code=referral_code,
                referral_source=signup_context.get("source", "direct"),
                signup_date=datetime.utcnow(),
                reward_calculations=reward_calculations,
                fraud_score=fraud_check.get("fraud_score", 0),
                is_verified=not fraud_check["suspicious"]
            )
            
            self.db.add(referral_bonus)
            
            # Process immediate rewards
            immediate_rewards = await self._process_immediate_rewards(
                referrer_id, new_user_data["user_id"], reward_calculations
            )
            
            # Schedule conditional rewards
            conditional_rewards = await self._schedule_conditional_rewards(
                referrer_id, new_user_data["user_id"], reward_calculations
            )
            
            # Update referrer statistics
            await self._update_referrer_statistics(referrer_id, referral_bonus)
            
            # Update referral link usage
            referral_link.usage_count = (referral_link.usage_count or 0) + 1
            referral_link.last_used = datetime.utcnow()
            
            await self.db.commit()
            
            # Generate welcome package for new user
            welcome_package = await self._generate_new_user_welcome_package(
                new_user_data["user_id"], referrer_id, reward_calculations
            )
            
            return {
                "success": True,
                "referral_processed": True,
                "referrer_id": str(referrer_id),
                "new_user_id": new_user_data["user_id"],
                "referral_bonus_id": str(referral_bonus.id),
                "immediate_rewards": immediate_rewards,
                "conditional_rewards": conditional_rewards,
                "new_user_welcome_package": welcome_package,
                "fraud_assessment": {
                    "fraud_score": fraud_check.get("fraud_score", 0),
                    "verification_required": not referral_bonus.is_verified,
                    "review_status": "approved" if referral_bonus.is_verified else "pending"
                },
                "referrer_notification": await self._generate_referrer_notification(
                    referrer_id, new_user_data, immediate_rewards
                ),
                "signup_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process referral signup: {e}")
            raise
    
    async def track_referral_milestone(
        self,
        user_id: uuid.UUID,
        milestone_type: str,
        milestone_data: Dict[str, Any],
        achievement_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Track and reward referral milestones"""
        
        try:
            # Check if this user was referred
            referral_bonus = await self._get_user_referral_bonus(user_id)
            
            if not referral_bonus:
                return {
                    "success": True,
                    "milestone_tracked": True,
                    "referral_rewards": [],
                    "message": "User was not referred - milestone tracked for other purposes"
                }
            
            # Get milestone reward configurations
            milestone_rewards = await self._get_milestone_reward_configs(
                milestone_type, referral_bonus.reward_calculations
            )
            
            if not milestone_rewards:
                return {
                    "success": True,
                    "milestone_tracked": True,
                    "referral_rewards": [],
                    "message": f"No referral rewards configured for milestone: {milestone_type}"
                }
            
            # Process milestone rewards
            processed_rewards = []
            for reward_config in milestone_rewards:
                reward_result = await self._process_milestone_reward(
                    referral_bonus.referrer_id,
                    user_id,
                    milestone_type,
                    milestone_data,
                    reward_config
                )
                processed_rewards.append(reward_result)
            
            # Update referral bonus with milestone achievement
            milestone_achievement = {
                "milestone_type": milestone_type,
                "achievement_date": datetime.utcnow().isoformat(),
                "milestone_data": milestone_data,
                "rewards_processed": len(processed_rewards)
            }
            
            if not referral_bonus.milestones_achieved:
                referral_bonus.milestones_achieved = []
            referral_bonus.milestones_achieved.append(milestone_achievement)
            
            # Update referrer statistics
            await self._update_referrer_milestone_stats(
                referral_bonus.referrer_id, milestone_type, milestone_data
            )
            
            await self.db.commit()
            
            return {
                "success": True,
                "milestone_tracked": True,
                "milestone_type": milestone_type,
                "referrer_id": str(referral_bonus.referrer_id),
                "referred_user_id": str(user_id),
                "referral_rewards": processed_rewards,
                "milestone_value": await self._calculate_milestone_value(
                    milestone_type, milestone_data
                ),
                "referrer_notification": await self._generate_milestone_notification(
                    referral_bonus.referrer_id, user_id, milestone_type, processed_rewards
                ),
                "achievement_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to track referral milestone: {e}")
            raise
    
    async def get_referral_analytics(
        self,
        user_id: uuid.UUID,
        period_days: int = 90,
        analytics_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get comprehensive referral analytics for a user"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get referral bonuses where user is referrer
            result = await self.db.execute(
                select(ReferralBonus).where(
                    and_(
                        ReferralBonus.referrer_id == user_id,
                        ReferralBonus.signup_date >= start_date
                    )
                ).order_by(ReferralBonus.signup_date.desc())
            )
            referrals_made = result.scalars().all()
            
            # Get referral bonuses where user was referred
            result = await self.db.execute(
                select(ReferralBonus).where(ReferralBonus.referred_user_id == user_id)
            )
            user_referral_bonus = result.scalar_one_or_none()
            
            # Get user's referral status
            user_status = await self._get_user_referral_status(user_id)
            
            # Analyze referral performance
            referral_performance = await self._analyze_referral_performance(
                user_id, referrals_made, period_days
            )
            
            # Analyze earnings and rewards
            earnings_analysis = await self._analyze_referral_earnings(
                user_id, referrals_made, period_days
            )
            
            # Analyze referral quality and engagement
            quality_analysis = await self._analyze_referral_quality(
                user_id, referrals_made
            )
            
            # Get active referral links
            active_links = await self._get_user_active_referral_links(user_id)
            
            # Calculate leaderboard position
            leaderboard_position = await self._calculate_leaderboard_position(
                user_id, period_days
            )
            
            analytics_result = {
                "user_id": str(user_id),
                "period_days": period_days,
                "referral_overview": {
                    "total_referrals": len(referrals_made),
                    "successful_referrals": len([r for r in referrals_made if r.is_verified]),
                    "pending_review": len([r for r in referrals_made if not r.is_verified]),
                    "referral_success_rate": referral_performance.get("success_rate", 0),
                    "was_referred": user_referral_bonus is not None,
                    "referrer_id": str(user_referral_bonus.referrer_id) if user_referral_bonus else None
                },
                "performance_metrics": referral_performance,
                "earnings_summary": earnings_analysis,
                "quality_metrics": quality_analysis,
                "active_referral_links": [
                    {
                        "code": link.referral_code,
                        "created_date": link.created_date.isoformat(),
                        "usage_count": link.usage_count or 0,
                        "link_url": await self._generate_link_url(link)
                    }
                    for link in active_links
                ],
                "leaderboard": leaderboard_position,
                "recommendations": await self._generate_referral_recommendations(
                    user_id, user_status, referral_performance, earnings_analysis
                ),
                "upcoming_opportunities": await self._identify_referral_opportunities(
                    user_id, user_status
                ),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
            # Add detailed breakdown if comprehensive analytics requested
            if analytics_type == "comprehensive":
                analytics_result["detailed_breakdown"] = {
                    "monthly_trends": await self._analyze_monthly_referral_trends(user_id, 12),
                    "referral_sources": await self._analyze_referral_sources(referrals_made),
                    "milestone_achievements": await self._analyze_milestone_achievements(referrals_made),
                    "reward_distribution": await self._analyze_reward_distribution(user_id),
                    "geographical_analysis": await self._analyze_geographical_distribution(referrals_made),
                    "conversion_funnel": await self._analyze_conversion_funnel(user_id)
                }
            
            return analytics_result
            
        except Exception as e:
            logger.error(f"Failed to get referral analytics: {e}")
            raise
    
    async def update_referral_programs(
        self,
        program_updates: Dict[str, Any],
        admin_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Update referral programs and reward structures"""
        
        try:
            # Validate admin permissions
            if not admin_context or not admin_context.get("admin_privileges"):
                return {"success": False, "error": "Admin privileges required"}
            
            update_results = []
            
            for program_id, updates in program_updates.items():
                # Get existing program
                result = await self.db.execute(
                    select(ReferralProgram).where(ReferralProgram.id == uuid.UUID(program_id))
                )
                program = result.scalar_one_or_none()
                
                if not program:
                    update_results.append({
                        "program_id": program_id,
                        "success": False,
                        "error": "Program not found"
                    })
                    continue
                
                # Apply updates
                program_update_result = await self._apply_program_updates(program, updates)
                update_results.append(program_update_result)
            
            # Recalculate affected referral bonuses
            recalculation_results = await self._recalculate_affected_bonuses(program_updates)
            
            # Update program configurations
            await self.db.commit()
            
            return {
                "success": True,
                "program_updates": update_results,
                "recalculation_results": recalculation_results,
                "effective_date": datetime.utcnow().isoformat(),
                "admin_user": admin_context.get("admin_user_id"),
                "update_summary": {
                    "programs_updated": len([r for r in update_results if r.get("success")]),
                    "users_affected": len(recalculation_results),
                    "changes_applied": sum(len(updates) for updates in program_updates.values())
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to update referral programs: {e}")
            raise
    
    # Helper methods
    
    async def _get_user_referral_status(self, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get user's referral status and statistics"""
        
        result = await self.db.execute(
            select(UserReferralStatus).where(UserReferralStatus.user_id == user_id)
        )
        status = result.scalar_one_or_none()
        
        if not status:
            # Create initial status for new user
            status = UserReferralStatus(
                user_id=user_id,
                total_referrals=0,
                successful_referrals=0,
                total_rewards_earned=Decimal('0'),
                referral_tier="bronze",
                created_date=datetime.utcnow()
            )
            self.db.add(status)
            await self.db.commit()
        
        return {
            "user_id": str(user_id),
            "total_referrals": status.total_referrals,
            "successful_referrals": status.successful_referrals,
            "total_rewards_earned": float(status.total_rewards_earned),
            "referral_tier": status.referral_tier,
            "member_since": status.created_date,
            "is_eligible": status.is_eligible,
            "fraud_score": float(status.fraud_score or 0)
        }
    
    async def _check_referral_eligibility(
        self,
        user_id: uuid.UUID,
        referrer_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if user is eligible to make referrals"""
        
        # Basic eligibility requirements
        requirements = []
        eligible = True
        
        # Check if user account is in good standing
        if referrer_status["fraud_score"] > 0.5:
            eligible = False
            requirements.append("Account must be in good standing (low fraud score)")
        
        # Check if user has been active (made choices)
        user_activity = await self._get_user_activity_level(user_id)
        if user_activity < 5:  # Minimum 5 interactions
            eligible = False
            requirements.append("Must have at least 5 platform interactions")
        
        # Check referral limits
        if referrer_status["total_referrals"] >= 100:  # Max 100 referrals per user
            eligible = False
            requirements.append("Maximum referral limit reached")
        
        return {
            "eligible": eligible,
            "reason": "Eligible for referrals" if eligible else "Not eligible for referrals",
            "requirements": requirements,
            "eligibility_score": 1.0 if eligible else 0.0
        }
    
    async def _get_active_referral_programs(self) -> List[Dict[str, Any]]:
        """Get all active referral programs"""
        
        result = await self.db.execute(
            select(ReferralProgram).where(
                and_(
                    ReferralProgram.is_active == True,
                    ReferralProgram.start_date <= datetime.utcnow(),
                    or_(
                        ReferralProgram.end_date.is_(None),
                        ReferralProgram.end_date >= datetime.utcnow()
                    )
                )
            )
        )
        programs = result.scalars().all()
        
        return [
            {
                "id": str(program.id),
                "name": program.program_name,
                "description": program.description,
                "program_type": program.program_type,
                "reward_structure": program.reward_structure or {},
                "tier_multipliers": program.tier_multipliers or {},
                "max_rewards": float(program.max_rewards_per_referrer) if program.max_rewards_per_referrer else None
            }
            for program in programs
        ]
    
    async def _generate_referral_code(self, referrer_id: uuid.UUID) -> str:
        """Generate a unique referral code"""
        
        # Create a unique code based on user ID and timestamp
        timestamp = str(int(datetime.utcnow().timestamp()))
        user_str = str(referrer_id)[-8:]  # Last 8 chars of UUID
        raw_string = f"{user_str}{timestamp}"
        
        # Hash and take first 8 characters
        hash_object = hashlib.md5(raw_string.encode())
        hash_hex = hash_object.hexdigest()
        
        return f"REF{hash_hex[:8].upper()}"
    
    async def _generate_link_details(
        self,
        referral_link: ReferralLink,
        active_programs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate detailed referral link information"""
        
        base_url = "https://activelog.com/signup"  # Would be configurable
        referral_url = f"{base_url}?ref={referral_link.referral_code}"
        
        # Add custom parameters
        if referral_link.custom_parameters:
            params = "&".join([f"{k}={v}" for k, v in referral_link.custom_parameters.items()])
            referral_url += f"&{params}"
        
        return {
            "referral_code": referral_link.referral_code,
            "referral_url": referral_url,
            "short_url": await self._generate_short_url(referral_url),
            "qr_code_url": await self._generate_qr_code(referral_url),
            "expiration_date": None,  # No expiration for now
            "usage_limit": None,  # No limit for now
            "current_usage": referral_link.usage_count or 0,
            "tracking_enabled": True
        }
    
    async def _calculate_potential_rewards(
        self,
        referrer_id: uuid.UUID,
        active_programs: List[Dict[str, Any]],
        referrer_status: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate potential rewards from referrals"""
        
        potential_rewards = {
            "immediate_rewards": [],
            "milestone_rewards": [],
            "total_potential_value": 0
        }
        
        for program in active_programs:
            reward_structure = program["reward_structure"]
            
            # Immediate signup rewards
            if "signup_bonus" in reward_structure:
                signup_reward = reward_structure["signup_bonus"]
                tier_multiplier = program["tier_multipliers"].get(referrer_status["referral_tier"], 1.0)
                
                potential_rewards["immediate_rewards"].append({
                    "program": program["name"],
                    "reward_type": "signup_bonus",
                    "base_amount": signup_reward,
                    "tier_multiplier": tier_multiplier,
                    "final_amount": signup_reward * tier_multiplier,
                    "currency": "points"  # or USD, depending on program
                })
                
                potential_rewards["total_potential_value"] += signup_reward * tier_multiplier
            
            # Milestone rewards
            if "milestone_rewards" in reward_structure:
                for milestone, reward in reward_structure["milestone_rewards"].items():
                    potential_rewards["milestone_rewards"].append({
                        "program": program["name"],
                        "milestone": milestone,
                        "reward_amount": reward,
                        "description": f"Reward when referred user achieves {milestone}"
                    })
        
        return potential_rewards
    
    async def _generate_sharing_tools(
        self,
        link_details: Dict[str, Any],
        referrer_status: Dict[str, Any],
        potential_rewards: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate sharing tools and templates"""
        
        return {
            "social_media_templates": {
                "twitter": f"Join me on ActiveLog and we both get rewards! Use my referral link: {link_details['short_url']} #ActiveLog #Referral",
                "facebook": f"I've been using ActiveLog to optimize my digital choices and it's amazing! Join me and we'll both get bonus rewards: {link_details['short_url']}",
                "linkedin": f"Discover ActiveLog - intelligent choice optimization platform. Join using my referral link for exclusive bonuses: {link_details['short_url']}"
            },
            "email_template": {
                "subject": "Join me on ActiveLog - Exclusive Referral Bonus",
                "body": f"Hi! I've been using ActiveLog to make smarter digital choices and I think you'd love it. Use my referral link to sign up and we'll both get {potential_rewards['total_potential_value']} bonus points: {link_details['referral_url']}"
            },
            "direct_message_template": f"Hey! Check out ActiveLog - it's helped me optimize my digital choices and save money. Use my referral code {link_details['referral_code']} when you sign up for bonus rewards!",
            "sharing_buttons": {
                "twitter_url": f"https://twitter.com/intent/tweet?text=Join%20me%20on%20ActiveLog&url={link_details['short_url']}",
                "facebook_url": f"https://www.facebook.com/sharer/sharer.php?u={link_details['short_url']}",
                "linkedin_url": f"https://www.linkedin.com/sharing/share-offsite/?url={link_details['short_url']}"
            }
        }
    
    async def _validate_referral_code(self, referral_code: str) -> Dict[str, Any]:
        """Validate a referral code"""
        
        result = await self.db.execute(
            select(ReferralLink).where(
                and_(
                    ReferralLink.referral_code == referral_code,
                    ReferralLink.is_active == True
                )
            )
        )
        referral_link = result.scalar_one_or_none()
        
        if not referral_link:
            return {
                "valid": False,
                "error": "Invalid or expired referral code"
            }
        
        # Check if referral link is still valid
        if referral_link.expiration_date and referral_link.expiration_date < datetime.utcnow():
            return {
                "valid": False,
                "error": "Referral code has expired"
            }
        
        return {
            "valid": True,
            "referral_link": referral_link
        }
    
    async def _check_referral_fraud(
        self,
        referrer_id: uuid.UUID,
        new_user_data: Dict[str, Any],
        signup_context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Check for potential referral fraud or abuse"""
        
        fraud_indicators = []
        fraud_score = 0.0
        
        # Check for same IP address
        if signup_context and "ip_address" in signup_context:
            referrer_ips = await self._get_user_ip_addresses(referrer_id)
            if signup_context["ip_address"] in referrer_ips:
                fraud_indicators.append("Same IP address as referrer")
                fraud_score += 0.3
        
        # Check for similar email patterns
        if "email" in new_user_data:
            referrer_email = await self._get_user_email(referrer_id)
            if self._emails_suspicious_similar(referrer_email, new_user_data["email"]):
                fraud_indicators.append("Similar email pattern to referrer")
                fraud_score += 0.4
        
        # Check referral velocity (too many referrals too quickly)
        recent_referrals = await self._get_recent_referrals(referrer_id, hours=24)
        if len(recent_referrals) > 5:  # More than 5 referrals in 24 hours
            fraud_indicators.append("High referral velocity")
            fraud_score += 0.2
        
        # Check device fingerprinting (if available)
        if signup_context and "device_fingerprint" in signup_context:
            referrer_fingerprints = await self._get_user_device_fingerprints(referrer_id)
            if signup_context["device_fingerprint"] in referrer_fingerprints:
                fraud_indicators.append("Same device fingerprint as referrer")
                fraud_score += 0.5
        
        return {
            "suspicious": fraud_score > 0.3,
            "fraud_score": fraud_score,
            "indicators": fraud_indicators,
            "requires_review": fraud_score > 0.5
        }
    
    async def _calculate_referral_reward(
        self,
        referrer_id: uuid.UUID,
        new_user_id: str,
        program: Dict[str, Any],
        referral_link: ReferralLink
    ) -> Dict[str, Any]:
        """Calculate rewards for a specific referral program"""
        
        reward_structure = program["reward_structure"]
        referrer_status = await self._get_user_referral_status(referrer_id)
        
        rewards = {
            "program_id": program["id"],
            "program_name": program["name"],
            "immediate_rewards": [],
            "conditional_rewards": [],
            "total_immediate_value": 0,
            "total_conditional_value": 0
        }
        
        # Calculate immediate signup bonus
        if "signup_bonus" in reward_structure:
            base_bonus = reward_structure["signup_bonus"]
            tier_multiplier = program["tier_multipliers"].get(referrer_status["referral_tier"], 1.0)
            final_bonus = base_bonus * tier_multiplier
            
            rewards["immediate_rewards"].append({
                "type": "signup_bonus",
                "base_amount": base_bonus,
                "tier_multiplier": tier_multiplier,
                "final_amount": final_bonus,
                "description": "Immediate reward for successful referral signup"
            })
            
            rewards["total_immediate_value"] += final_bonus
        
        # Calculate conditional milestone rewards
        if "milestone_rewards" in reward_structure:
            for milestone, reward_amount in reward_structure["milestone_rewards"].items():
                rewards["conditional_rewards"].append({
                    "type": "milestone_reward",
                    "milestone": milestone,
                    "reward_amount": reward_amount,
                    "condition": f"Referred user completes {milestone}",
                    "estimated_probability": await self._estimate_milestone_probability(milestone)
                })
                
                # Add to conditional value weighted by probability
                probability = await self._estimate_milestone_probability(milestone)
                rewards["total_conditional_value"] += reward_amount * probability
        
        return rewards
    
    # Additional helper methods (simplified implementations for brevity)
    
    async def _get_user_activity_level(self, user_id: uuid.UUID) -> int:
        """Get user's activity level (number of interactions)"""
        result = await self.db.execute(
            select(func.count(UserChoice.id)).where(UserChoice.user_id == user_id)
        )
        return result.scalar() or 0
    
    async def _generate_short_url(self, long_url: str) -> str:
        """Generate a short URL"""
        return f"https://actlog.co/r/{hashlib.md5(long_url.encode()).hexdigest()[:8]}"
    
    async def _generate_qr_code(self, url: str) -> str:
        """Generate QR code URL"""
        return f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={url}"
    
    async def _generate_tracking_dashboard_url(self, referrer_id: uuid.UUID) -> str:
        """Generate tracking dashboard URL"""
        return f"https://activelog.com/referrals/dashboard?user={referrer_id}"
    
    async def _get_referral_terms(self) -> Dict[str, Any]:
        """Get referral program terms and conditions"""
        return {
            "terms_url": "https://activelog.com/referral-terms",
            "key_points": [
                "Rewards are credited within 24 hours of qualifying action",
                "Self-referrals and fraudulent activity will result in account suspension",
                "Maximum 100 referrals per user",
                "Referral rewards may be subject to tax reporting"
            ]
        }
    
    # Placeholder methods for complex operations (would be fully implemented in production)
    
    async def _get_referral_programs_by_ids(self, program_ids: List[str]) -> List[Dict[str, Any]]:
        """Get referral programs by IDs"""
        return await self._get_active_referral_programs()  # Simplified
    
    async def _process_immediate_rewards(self, referrer_id: uuid.UUID, new_user_id: str, reward_calculations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process immediate rewards"""
        return [{"reward": "100 points", "status": "credited"}]
    
    async def _schedule_conditional_rewards(self, referrer_id: uuid.UUID, new_user_id: str, reward_calculations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Schedule conditional rewards"""
        return [{"milestone": "first_choice", "reward": "50 points", "status": "pending"}]
    
    async def _update_referrer_statistics(self, referrer_id: uuid.UUID, referral_bonus: ReferralBonus):
        """Update referrer's statistics"""
        result = await self.db.execute(
            select(UserReferralStatus).where(UserReferralStatus.user_id == referrer_id)
        )
        status = result.scalar_one()
        if status:
            status.total_referrals += 1
            if referral_bonus.is_verified:
                status.successful_referrals += 1
    
    async def _generate_new_user_welcome_package(self, new_user_id: str, referrer_id: uuid.UUID, reward_calculations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate welcome package for new referred user"""
        return {
            "welcome_bonus": "50 points",
            "premium_trial": "7 days",
            "referrer_name": "Anonymous User"  # Would get actual name
        }
    
    async def _generate_referrer_notification(self, referrer_id: uuid.UUID, new_user_data: Dict[str, Any], immediate_rewards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate notification for referrer"""
        return {
            "message": "Your referral was successful!",
            "reward_summary": "100 points credited",
            "notification_type": "referral_success"
        }
    
    # Additional placeholder methods
    async def _get_user_referral_bonus(self, user_id: uuid.UUID) -> Optional[ReferralBonus]:
        result = await self.db.execute(
            select(ReferralBonus).where(ReferralBonus.referred_user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_milestone_reward_configs(self, milestone_type: str, reward_calculations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [{"milestone": milestone_type, "reward": 50}]
    
    async def _process_milestone_reward(self, referrer_id: uuid.UUID, user_id: uuid.UUID, milestone_type: str, milestone_data: Dict[str, Any], reward_config: Dict[str, Any]) -> Dict[str, Any]:
        return {"reward_processed": True, "amount": 50, "type": "points"}
    
    async def _update_referrer_milestone_stats(self, referrer_id: uuid.UUID, milestone_type: str, milestone_data: Dict[str, Any]):
        pass
    
    async def _calculate_milestone_value(self, milestone_type: str, milestone_data: Dict[str, Any]) -> float:
        return 50.0
    
    async def _generate_milestone_notification(self, referrer_id: uuid.UUID, user_id: uuid.UUID, milestone_type: str, processed_rewards: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"message": f"Your referred user achieved {milestone_type}!", "reward": "50 points"}
    
    # Analytics helper methods (simplified)
    async def _analyze_referral_performance(self, user_id: uuid.UUID, referrals_made: List[ReferralBonus], period_days: int) -> Dict[str, Any]:
        return {"success_rate": 85.0, "conversion_rate": 12.5, "avg_time_to_convert": "3 days"}
    
    async def _analyze_referral_earnings(self, user_id: uuid.UUID, referrals_made: List[ReferralBonus], period_days: int) -> Dict[str, Any]:
        return {"total_earned": 1250, "avg_per_referral": 125, "earnings_trend": "increasing"}
    
    async def _analyze_referral_quality(self, user_id: uuid.UUID, referrals_made: List[ReferralBonus]) -> Dict[str, Any]:
        return {"quality_score": 8.5, "engagement_rate": 75.0, "retention_rate": 82.0}
    
    async def _get_user_active_referral_links(self, user_id: uuid.UUID) -> List[ReferralLink]:
        result = await self.db.execute(
            select(ReferralLink).where(
                and_(
                    ReferralLink.referrer_id == user_id,
                    ReferralLink.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def _calculate_leaderboard_position(self, user_id: uuid.UUID, period_days: int) -> Dict[str, Any]:
        return {"rank": 15, "total_participants": 1000, "percentile": 95}
    
    async def _generate_referral_recommendations(self, user_id: uuid.UUID, user_status: Dict[str, Any], referral_performance: Dict[str, Any], earnings_analysis: Dict[str, Any]) -> List[str]:
        return ["Share your link on social media", "Reach out to friends interested in optimization"]
    
    async def _identify_referral_opportunities(self, user_id: uuid.UUID, user_status: Dict[str, Any]) -> List[Dict[str, Any]]:
        return [{"opportunity": "Double rewards weekend", "date": "2024-01-20", "bonus": "2x points"}]
    
    # Additional analysis methods
    async def _analyze_monthly_referral_trends(self, user_id: uuid.UUID, months: int) -> Dict[str, Any]:
        return {"trend": "increasing", "monthly_average": 8.5}
    
    async def _analyze_referral_sources(self, referrals_made: List[ReferralBonus]) -> Dict[str, Any]:
        return {"social_media": 60, "email": 25, "direct": 15}
    
    async def _analyze_milestone_achievements(self, referrals_made: List[ReferralBonus]) -> Dict[str, Any]:
        return {"total_milestones": 45, "completion_rate": 78}
    
    async def _analyze_reward_distribution(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"immediate": 70, "milestone": 30}
    
    async def _analyze_geographical_distribution(self, referrals_made: List[ReferralBonus]) -> Dict[str, Any]:
        return {"US": 60, "CA": 20, "EU": 15, "Other": 5}
    
    async def _analyze_conversion_funnel(self, user_id: uuid.UUID) -> Dict[str, Any]:
        return {"link_clicks": 100, "signups": 25, "active_users": 20}
    
    # Program management methods
    async def _apply_program_updates(self, program: ReferralProgram, updates: Dict[str, Any]) -> Dict[str, Any]:
        return {"program_id": str(program.id), "success": True, "changes": len(updates)}
    
    async def _recalculate_affected_bonuses(self, program_updates: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []
    
    # Fraud detection helpers
    async def _get_user_ip_addresses(self, user_id: uuid.UUID) -> List[str]:
        return ["192.168.1.1"]  # Placeholder
    
    async def _get_user_email(self, user_id: uuid.UUID) -> str:
        return "user@example.com"  # Placeholder
    
    async def _emails_suspicious_similar(self, email1: str, email2: str) -> bool:
        # Simple similarity check - would be more sophisticated
        return email1.split('@')[0] in email2 or email2.split('@')[0] in email1
    
    async def _get_recent_referrals(self, referrer_id: uuid.UUID, hours: int) -> List[ReferralBonus]:
        return []  # Placeholder
    
    async def _get_user_device_fingerprints(self, user_id: uuid.UUID) -> List[str]:
        return []  # Placeholder
    
    async def _estimate_milestone_probability(self, milestone: str) -> float:
        milestone_probabilities = {
            "first_choice": 0.9,
            "first_purchase": 0.6,
            "active_month": 0.4,
            "power_user": 0.2
        }
        return milestone_probabilities.get(milestone, 0.5)
    
    async def _generate_link_url(self, link: ReferralLink) -> str:
        return f"https://activelog.com/signup?ref={link.referral_code}"