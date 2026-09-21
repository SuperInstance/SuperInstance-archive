"""
SuperInstance Gaming Economy Integration
Manages compute capital rewards for DMlog gaming activities
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class GamingEconomyManager:
    """Manages compute capital economy for gaming activities"""
    
    def __init__(self):
        self.dm_base_rate = 10.0  # Base compute capital per DM session
        self.player_base_rate = 2.0  # Base compute capital per player session
        self.quality_multipliers = {
            "poor": 0.5,
            "fair": 0.8,
            "good": 1.0,
            "excellent": 1.5,
            "legendary": 2.0
        }
        self.activity_rates = {
            "dm_session": 10.0,
            "player_session": 2.0,
            "campaign_completion": 50.0,
            "character_creation": 1.0,
            "community_content": 5.0,
            "marketplace_sale": 3.0,
            "review_contribution": 1.5,
            "tutorial_creation": 15.0
        }
    
    async def calculate_dm_rewards(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compute capital rewards for DM activities"""
        base_reward = self.dm_base_rate
        quality_score = session_data.get("quality_score", 1.0)
        session_duration = session_data.get("duration_hours", 3.0)
        player_count = session_data.get("player_count", 4)
        
        # Quality multiplier
        quality_multiplier = min(quality_score, 2.0)  # Cap at 2x
        
        # Duration bonus (longer sessions get slight bonus)
        duration_multiplier = 1.0 + (session_duration - 2.0) * 0.1 if session_duration > 2.0 else 1.0
        
        # Player engagement bonus
        engagement_multiplier = 1.0 + (player_count - 3) * 0.05 if player_count > 3 else 1.0
        
        total_reward = base_reward * quality_multiplier * duration_multiplier * engagement_multiplier
        
        return {
            "base_reward": base_reward,
            "quality_multiplier": quality_multiplier,
            "duration_multiplier": duration_multiplier,
            "engagement_multiplier": engagement_multiplier,
            "total_compute_capital": round(total_reward, 2),
            "reward_breakdown": {
                "session_base": base_reward,
                "quality_bonus": (quality_multiplier - 1.0) * base_reward,
                "duration_bonus": (duration_multiplier - 1.0) * base_reward * quality_multiplier,
                "engagement_bonus": (engagement_multiplier - 1.0) * base_reward * quality_multiplier * duration_multiplier
            }
        }
    
    async def calculate_player_rewards(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compute capital rewards for player activities"""
        base_reward = self.player_base_rate
        participation_score = session_data.get("participation_score", 1.0)
        roleplay_quality = session_data.get("roleplay_quality", 1.0)
        teamwork_score = session_data.get("teamwork_score", 1.0)
        
        # Combined player performance
        performance_multiplier = (participation_score + roleplay_quality + teamwork_score) / 3.0
        performance_multiplier = min(performance_multiplier, 2.0)  # Cap at 2x
        
        total_reward = base_reward * performance_multiplier
        
        return {
            "base_reward": base_reward,
            "participation_score": participation_score,
            "roleplay_quality": roleplay_quality,
            "teamwork_score": teamwork_score,
            "performance_multiplier": performance_multiplier,
            "total_compute_capital": round(total_reward, 2)
        }
    
    async def calculate_campaign_milestone_rewards(self, milestone_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate rewards for campaign milestones"""
        milestone_type = milestone_data.get("type", "session_completion")
        base_reward = self.activity_rates.get(milestone_type, 5.0)
        
        # Special bonuses for significant milestones
        milestone_bonuses = {
            "campaign_launch": 25.0,
            "major_story_arc": 35.0,
            "campaign_completion": 100.0,
            "player_character_death": 15.0,
            "epic_battle_victory": 20.0
        }
        
        bonus_reward = milestone_bonuses.get(milestone_data.get("significance"), 0.0)
        total_reward = base_reward + bonus_reward
        
        return {
            "milestone_type": milestone_type,
            "base_reward": base_reward,
            "bonus_reward": bonus_reward,
            "total_compute_capital": total_reward
        }
    
    async def calculate_cross_domain_gaming_bonuses(self, user_id: str, gaming_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate bonuses based on cross-domain SuperInstance participation"""
        bonuses = {}
        
        # Fitness domain bonus - active users get endurance bonuses
        fitness_participation = gaming_data.get("fitness_engagement", 0.5)
        bonuses["fitness_endurance_bonus"] = fitness_participation * 5.0
        
        # Business domain bonus - leadership skills enhance DM rewards
        business_participation = gaming_data.get("business_engagement", 0.5)
        bonuses["leadership_dm_bonus"] = business_participation * 8.0
        
        # Personal development bonus - goal achievement improves character progression
        personal_participation = gaming_data.get("personal_engagement", 0.5)
        bonuses["character_development_bonus"] = personal_participation * 6.0
        
        # Marine domain bonus - maritime expertise enhances naval campaigns
        marine_participation = gaming_data.get("marine_engagement", 0.5)
        bonuses["maritime_adventure_bonus"] = marine_participation * 7.0
        
        total_cross_domain_bonus = sum(bonuses.values())
        
        return {
            "individual_bonuses": bonuses,
            "total_cross_domain_bonus": round(total_cross_domain_bonus, 2),
            "cross_domain_multiplier": 1.0 + (total_cross_domain_bonus / 100.0)
        }
    
    async def calculate_marketplace_economy(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate compute capital for marketplace transactions"""
        transaction_type = transaction_data.get("type", "purchase")
        transaction_value = transaction_data.get("value", 0.0)
        
        # Different rates for different transaction types
        commission_rates = {
            "content_sale": 0.15,  # 15% to seller
            "3d_print_commission": 0.20,  # 20% to designer
            "campaign_template_sale": 0.25,  # 25% to creator
            "character_portrait_commission": 0.18,
            "custom_miniature_design": 0.22
        }
        
        commission_rate = commission_rates.get(transaction_type, 0.10)
        compute_capital_earned = transaction_value * commission_rate
        
        return {
            "transaction_type": transaction_type,
            "transaction_value": transaction_value,
            "commission_rate": commission_rate,
            "compute_capital_earned": round(compute_capital_earned, 2),
            "marketplace_fee": transaction_value * 0.05  # 5% marketplace fee
        }
    
    async def get_gaming_economy_summary(self, user_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive gaming economy summary for user"""
        # Mock data - in production would query actual user gaming activity
        return {
            "period_days": period_days,
            "total_compute_capital_earned": 285.50,
            "breakdown": {
                "dm_sessions": 180.00,
                "player_sessions": 45.00,
                "campaign_milestones": 35.00,
                "marketplace_sales": 12.50,
                "cross_domain_bonuses": 13.00
            },
            "gaming_rank": "Advanced DM",
            "next_tier_requirements": {
                "compute_capital_needed": 214.50,
                "tier": "Expert DM",
                "benefits": [
                    "20% bonus to all DM rewards",
                    "Access to premium campaign templates",
                    "Priority marketplace placement"
                ]
            },
            "cross_domain_enhancement_impact": {
                "fitness_bonus": "+15% endurance campaigns",
                "business_bonus": "+12% economic storylines", 
                "personal_bonus": "+18% character development",
                "marine_bonus": "+22% maritime adventures"
            }
        }

# Global gaming economy manager
gaming_economy = GamingEconomyManager()