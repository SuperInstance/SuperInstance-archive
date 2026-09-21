"""
🏆 COMPUTE CAPITAL GAMING ECONOMY INTEGRATION
Revolutionary system where gaming achievements generate real economic value.
DM skills, campaign quality, and player engagement earn compute capital rewards.

Part of the $2/month SuperInstance gaming revolution.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import uuid

logger = logging.getLogger(__name__)

class EconomicEventType(str, Enum):
    """Types of gaming events that generate economic value."""
    CAMPAIGN_MASTERY = "campaign_mastery"
    PLAYER_ENGAGEMENT = "player_engagement" 
    CREATIVE_CONTENT = "creative_content"
    COMMUNITY_BUILDING = "community_building"
    SKILL_DEVELOPMENT = "skill_development"
    COLLABORATIVE_ACHIEVEMENT = "collaborative_achievement"

class ComputeCapitalCategory(str, Enum):
    """Categories of compute capital rewards."""
    GAMING_MASTERY = "gaming_mastery"
    SOCIAL_IMPACT = "social_impact"
    CREATIVE_CONTRIBUTION = "creative_contribution"
    KNOWLEDGE_SHARING = "knowledge_sharing"
    PLATFORM_GROWTH = "platform_growth"

@dataclass
class EconomicEvent:
    """A gaming event that generates economic value."""
    event_id: str
    user_id: str
    event_type: EconomicEventType
    description: str
    value_generated: Decimal
    compute_capital_earned: Decimal
    timestamp: datetime
    session_id: Optional[str] = None
    campaign_id: Optional[str] = None
    participants: List[str] = None
    quality_score: float = 0.0  # 0.0 to 1.0
    community_impact: float = 0.0  # 0.0 to 1.0

@dataclass
class ComputeCapitalReward:
    """Compute capital reward for gaming activities."""
    reward_id: str
    user_id: str
    category: ComputeCapitalCategory
    amount: Decimal
    source_event: str
    description: str
    timestamp: datetime
    multiplier: float = 1.0
    bonus_reason: str = ""

class GamingEconomicEngine:
    """Engine for integrating gaming achievements with compute capital economy."""
    
    def __init__(self):
        self.base_rates = {
            EconomicEventType.CAMPAIGN_MASTERY: Decimal("0.50"),  # Base rate per hour of quality DMing
            EconomicEventType.PLAYER_ENGAGEMENT: Decimal("0.25"),  # Per engaged player per session
            EconomicEventType.CREATIVE_CONTENT: Decimal("1.00"),   # Per quality content creation
            EconomicEventType.COMMUNITY_BUILDING: Decimal("0.75"), # Per community interaction
            EconomicEventType.SKILL_DEVELOPMENT: Decimal("0.30"),  # Per skill milestone
            EconomicEventType.COLLABORATIVE_ACHIEVEMENT: Decimal("0.40")  # Per group achievement
        }
        
        self.quality_multipliers = {
            "legendary": 3.0,    # Exceptional quality/impact
            "excellent": 2.0,    # High quality/impact
            "good": 1.5,         # Above average
            "standard": 1.0,     # Base rate
            "developing": 0.7    # Learning/improving
        }
        
        self.economic_events = []
        self.user_balances = {}
        
    async def evaluate_gaming_session(
        self,
        session_data: Dict[str, Any]
    ) -> List[EconomicEvent]:
        """Evaluate a gaming session for economic value generation."""
        
        events = []
        session_id = session_data.get("session_id")
        dm_user_id = session_data.get("dm_user_id")
        players = session_data.get("players", [])
        duration_hours = session_data.get("duration_hours", 0)
        session_quality = session_data.get("quality_metrics", {})
        
        # DM Campaign Mastery Evaluation
        if dm_user_id and duration_hours > 0:
            dm_quality = self._evaluate_dm_quality(session_quality, session_data)
            dm_event = self._create_campaign_mastery_event(
                dm_user_id, session_id, duration_hours, dm_quality, session_data
            )
            events.append(dm_event)
        
        # Player Engagement Evaluation
        for player_data in players:
            player_id = player_data.get("user_id")
            engagement_score = self._evaluate_player_engagement(player_data, session_data)
            
            if engagement_score > 0.3:  # Minimum engagement threshold
                player_event = self._create_engagement_event(
                    player_id, session_id, engagement_score, session_data
                )
                events.append(player_event)
        
        # Collaborative Achievement Evaluation
        collaborative_events = self._evaluate_collaborative_achievements(session_data)
        events.extend(collaborative_events)
        
        # Community Building Assessment
        if len(players) >= 3:  # Multi-player session
            community_events = self._evaluate_community_building(session_data)
            events.extend(community_events)
        
        return events
    
    def _evaluate_dm_quality(
        self, 
        quality_metrics: Dict[str, Any],
        session_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Evaluate DM quality across multiple dimensions."""
        
        quality_score = {
            "narrative_creativity": quality_metrics.get("story_rating", 0.7),
            "player_satisfaction": quality_metrics.get("player_feedback", 0.8),
            "rule_mastery": quality_metrics.get("rule_accuracy", 0.6),
            "improvisation": quality_metrics.get("adaptation_rating", 0.7),
            "engagement_facilitation": quality_metrics.get("participation_rate", 0.75),
            "world_building": quality_metrics.get("immersion_rating", 0.7)
        }
        
        # Bonus for using cross-domain enhancements
        if session_data.get("cross_domain_enhancements_used", False):
            quality_score["innovation_bonus"] = 0.2
        
        # Bonus for new player onboarding
        new_players = sum(1 for p in session_data.get("players", []) if p.get("is_new_player", False))
        if new_players > 0:
            quality_score["mentorship_bonus"] = new_players * 0.1
        
        return quality_score
    
    def _create_campaign_mastery_event(
        self,
        dm_user_id: str,
        session_id: str,
        duration_hours: float,
        quality_scores: Dict[str, float],
        session_data: Dict[str, Any]
    ) -> EconomicEvent:
        """Create economic event for campaign mastery."""
        
        base_value = self.base_rates[EconomicEventType.CAMPAIGN_MASTERY] * Decimal(str(duration_hours))
        
        # Calculate quality multiplier
        avg_quality = sum(quality_scores.values()) / len(quality_scores)
        quality_tier = self._get_quality_tier(avg_quality)
        multiplier = self.quality_multipliers[quality_tier]
        
        final_value = base_value * Decimal(str(multiplier))
        
        # Compute capital earned (gaming mastery category)
        compute_capital = final_value * Decimal("0.8")  # 80% conversion rate
        
        return EconomicEvent(
            event_id=str(uuid.uuid4()),
            user_id=dm_user_id,
            event_type=EconomicEventType.CAMPAIGN_MASTERY,
            description=f"Exceptional DM performance: {quality_tier} quality session ({duration_hours}h)",
            value_generated=final_value,
            compute_capital_earned=compute_capital,
            timestamp=datetime.now(),
            session_id=session_id,
            campaign_id=session_data.get("campaign_id"),
            quality_score=avg_quality,
            community_impact=len(session_data.get("players", [])) * 0.1
        )
    
    def _evaluate_player_engagement(
        self,
        player_data: Dict[str, Any],
        session_data: Dict[str, Any]
    ) -> float:
        """Evaluate player engagement score."""
        
        engagement_factors = {
            "participation_rate": player_data.get("participation_percentage", 0.7),
            "roleplay_quality": player_data.get("roleplay_rating", 0.6),
            "collaboration": player_data.get("team_play_score", 0.8),
            "creative_problem_solving": player_data.get("creativity_score", 0.5),
            "positive_interaction": player_data.get("social_score", 0.7)
        }
        
        # Bonus for helping new players
        if player_data.get("mentored_new_players", False):
            engagement_factors["mentorship"] = 0.3
        
        # Bonus for character development
        if player_data.get("character_growth_events", 0) > 0:
            engagement_factors["character_development"] = 0.2
        
        return sum(engagement_factors.values()) / len(engagement_factors)
    
    def _create_engagement_event(
        self,
        player_id: str,
        session_id: str,
        engagement_score: float,
        session_data: Dict[str, Any]
    ) -> EconomicEvent:
        """Create economic event for player engagement."""
        
        base_value = self.base_rates[EconomicEventType.PLAYER_ENGAGEMENT]
        engagement_multiplier = engagement_score * 2  # Scale engagement to multiplier
        
        final_value = base_value * Decimal(str(engagement_multiplier))
        compute_capital = final_value * Decimal("0.6")  # 60% conversion rate for players
        
        quality_tier = self._get_quality_tier(engagement_score)
        
        return EconomicEvent(
            event_id=str(uuid.uuid4()),
            user_id=player_id,
            event_type=EconomicEventType.PLAYER_ENGAGEMENT,
            description=f"Outstanding player engagement: {quality_tier} participation",
            value_generated=final_value,
            compute_capital_earned=compute_capital,
            timestamp=datetime.now(),
            session_id=session_id,
            quality_score=engagement_score,
            community_impact=0.1
        )
    
    def _evaluate_collaborative_achievements(
        self,
        session_data: Dict[str, Any]
    ) -> List[EconomicEvent]:
        """Evaluate collaborative achievements that generate economic value."""
        
        events = []
        achievements = session_data.get("group_achievements", [])
        
        for achievement in achievements:
            participants = achievement.get("participants", [])
            achievement_type = achievement.get("type", "general")
            difficulty = achievement.get("difficulty", "standard")
            
            base_value = self.base_rates[EconomicEventType.COLLABORATIVE_ACHIEVEMENT]
            difficulty_multiplier = {
                "trivial": 0.5,
                "standard": 1.0,
                "challenging": 1.5,
                "heroic": 2.0,
                "legendary": 3.0
            }.get(difficulty, 1.0)
            
            value_per_participant = base_value * Decimal(str(difficulty_multiplier))
            
            for participant_id in participants:
                event = EconomicEvent(
                    event_id=str(uuid.uuid4()),
                    user_id=participant_id,
                    event_type=EconomicEventType.COLLABORATIVE_ACHIEVEMENT,
                    description=f"Collaborative achievement: {achievement_type} ({difficulty})",
                    value_generated=value_per_participant,
                    compute_capital_earned=value_per_participant * Decimal("0.7"),
                    timestamp=datetime.now(),
                    session_id=session_data.get("session_id"),
                    participants=participants,
                    quality_score=difficulty_multiplier / 3.0,
                    community_impact=len(participants) * 0.05
                )
                events.append(event)
        
        return events
    
    def _evaluate_community_building(
        self,
        session_data: Dict[str, Any]
    ) -> List[EconomicEvent]:
        """Evaluate community building activities."""
        
        events = []
        community_actions = session_data.get("community_actions", [])
        
        for action in community_actions:
            action_type = action.get("type")
            user_id = action.get("user_id")
            impact_score = action.get("impact", 0.5)
            
            if action_type in ["new_player_welcome", "rule_explanation", "conflict_resolution", "group_coordination"]:
                base_value = self.base_rates[EconomicEventType.COMMUNITY_BUILDING]
                impact_multiplier = impact_score * 2
                
                event = EconomicEvent(
                    event_id=str(uuid.uuid4()),
                    user_id=user_id,
                    event_type=EconomicEventType.COMMUNITY_BUILDING,
                    description=f"Community building: {action_type}",
                    value_generated=base_value * Decimal(str(impact_multiplier)),
                    compute_capital_earned=base_value * Decimal(str(impact_multiplier)) * Decimal("0.9"),
                    timestamp=datetime.now(),
                    session_id=session_data.get("session_id"),
                    quality_score=impact_score,
                    community_impact=impact_score
                )
                events.append(event)
        
        return events
    
    def _get_quality_tier(self, score: float) -> str:
        """Convert quality score to tier."""
        if score >= 0.9:
            return "legendary"
        elif score >= 0.8:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.6:
            return "standard"
        else:
            return "developing"
    
    async def process_economic_events(
        self,
        events: List[EconomicEvent]
    ) -> List[ComputeCapitalReward]:
        """Process economic events and generate compute capital rewards."""
        
        rewards = []
        
        for event in events:
            # Determine reward category
            category = self._map_event_to_category(event.event_type)
            
            # Apply any applicable bonuses
            multiplier = 1.0
            bonus_reason = ""
            
            # Quality bonus
            if event.quality_score > 0.8:
                multiplier *= 1.2
                bonus_reason += "Quality Excellence Bonus; "
            
            # Community impact bonus
            if event.community_impact > 0.5:
                multiplier *= 1.1
                bonus_reason += "Community Impact Bonus; "
            
            # Create reward
            reward = ComputeCapitalReward(
                reward_id=str(uuid.uuid4()),
                user_id=event.user_id,
                category=category,
                amount=event.compute_capital_earned * Decimal(str(multiplier)),
                source_event=event.event_id,
                description=f"Gaming Economy: {event.description}",
                timestamp=datetime.now(),
                multiplier=multiplier,
                bonus_reason=bonus_reason.rstrip("; ")
            )
            
            rewards.append(reward)
            
            # Update user balance
            if event.user_id not in self.user_balances:
                self.user_balances[event.user_id] = Decimal("0")
            self.user_balances[event.user_id] += reward.amount
        
        return rewards
    
    def _map_event_to_category(self, event_type: EconomicEventType) -> ComputeCapitalCategory:
        """Map economic event types to compute capital categories."""
        mapping = {
            EconomicEventType.CAMPAIGN_MASTERY: ComputeCapitalCategory.GAMING_MASTERY,
            EconomicEventType.PLAYER_ENGAGEMENT: ComputeCapitalCategory.SOCIAL_IMPACT,
            EconomicEventType.CREATIVE_CONTENT: ComputeCapitalCategory.CREATIVE_CONTRIBUTION,
            EconomicEventType.COMMUNITY_BUILDING: ComputeCapitalCategory.SOCIAL_IMPACT,
            EconomicEventType.SKILL_DEVELOPMENT: ComputeCapitalCategory.KNOWLEDGE_SHARING,
            EconomicEventType.COLLABORATIVE_ACHIEVEMENT: ComputeCapitalCategory.GAMING_MASTERY
        }
        return mapping.get(event_type, ComputeCapitalCategory.GAMING_MASTERY)
    
    async def generate_economic_report(
        self,
        user_id: str,
        time_period_days: int = 30
    ) -> Dict[str, Any]:
        """Generate economic performance report for a user."""
        
        cutoff_date = datetime.now() - timedelta(days=time_period_days)
        user_events = [e for e in self.economic_events if e.user_id == user_id and e.timestamp > cutoff_date]
        
        total_value_generated = sum(e.value_generated for e in user_events)
        total_compute_capital = sum(e.compute_capital_earned for e in user_events)
        
        # Event type breakdown
        event_breakdown = {}
        for event in user_events:
            event_type = event.event_type.value
            if event_type not in event_breakdown:
                event_breakdown[event_type] = {"count": 0, "value": Decimal("0"), "capital": Decimal("0")}
            
            event_breakdown[event_type]["count"] += 1
            event_breakdown[event_type]["value"] += event.value_generated
            event_breakdown[event_type]["capital"] += event.compute_capital_earned
        
        # Quality trends
        quality_scores = [e.quality_score for e in user_events if e.quality_score > 0]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # Community impact
        total_community_impact = sum(e.community_impact for e in user_events)
        
        return {
            "user_id": user_id,
            "period_days": time_period_days,
            "performance_summary": {
                "total_events": len(user_events),
                "total_value_generated": float(total_value_generated),
                "total_compute_capital_earned": float(total_compute_capital),
                "current_balance": float(self.user_balances.get(user_id, Decimal("0"))),
                "average_quality_score": avg_quality,
                "community_impact_score": total_community_impact
            },
            "event_breakdown": {
                k: {
                    "count": v["count"],
                    "total_value": float(v["value"]),
                    "total_capital": float(v["capital"]),
                    "avg_value_per_event": float(v["value"] / v["count"]) if v["count"] > 0 else 0
                }
                for k, v in event_breakdown.items()
            },
            "gaming_economy_status": "🏆 Active participant in the $2/month SuperInstance revolution",
            "next_milestones": self._calculate_next_milestones(user_events)
        }
    
    def _calculate_next_milestones(self, user_events: List[EconomicEvent]) -> List[str]:
        """Calculate next economic milestones for the user."""
        milestones = []
        
        dm_events = [e for e in user_events if e.event_type == EconomicEventType.CAMPAIGN_MASTERY]
        player_events = [e for e in user_events if e.event_type == EconomicEventType.PLAYER_ENGAGEMENT]
        
        # DM milestones
        if dm_events:
            total_dm_hours = sum(1 for _ in dm_events)  # Simplified calculation
            if total_dm_hours < 10:
                milestones.append("🎯 Reach 10 DM sessions for 'Campaign Veteran' status")
            elif total_dm_hours < 25:
                milestones.append("🎯 Reach 25 DM sessions for 'Master Storyteller' bonus")
        
        # Player milestones
        if player_events:
            avg_engagement = sum(e.quality_score for e in player_events) / len(player_events)
            if avg_engagement < 0.8:
                milestones.append("🎯 Achieve 0.8+ average engagement for 'Exemplary Player' rewards")
        
        # Community milestones
        community_events = [e for e in user_events if e.event_type == EconomicEventType.COMMUNITY_BUILDING]
        if len(community_events) < 5:
            milestones.append("🎯 Complete 5 community building actions for 'Community Champion' title")
        
        return milestones[:3]  # Return top 3 milestones

# Integration API
class GamingEconomyAPI:
    """API for gaming economy integration."""
    
    def __init__(self):
        self.engine = GamingEconomicEngine()
    
    async def process_gaming_session_economics(
        self,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Main endpoint for processing gaming session economics."""
        
        # Evaluate session for economic events
        economic_events = await self.engine.evaluate_gaming_session(session_data)
        
        # Process events into compute capital rewards
        rewards = await self.engine.process_economic_events(economic_events)
        
        # Store events
        self.engine.economic_events.extend(economic_events)
        
        return {
            "session_id": session_data.get("session_id"),
            "economic_events_generated": len(economic_events),
            "compute_capital_rewards": len(rewards),
            "total_value_generated": float(sum(e.value_generated for e in economic_events)),
            "total_compute_capital_earned": float(sum(r.amount for r in rewards)),
            "events": [
                {
                    "type": e.event_type.value,
                    "description": e.description,
                    "value": float(e.value_generated),
                    "capital": float(e.compute_capital_earned),
                    "quality": e.quality_score
                }
                for e in economic_events
            ],
            "revolution_message": "🏆 Gaming achievements converted to compute capital!",
            "superinstance_economics": "Your gaming skills now generate real economic value"
        }

# Global instance
gaming_economy_api = GamingEconomyAPI()