"""
Faction reputation tracking service.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy.orm import Session
import logging

from ..models.faction import (
    FactionType, ReputationLevel, ReputationAction, FactionRelationType,
    FactionStanding, FactionSchema, FactionReputationSchema, ReputationEventSchema,
    ReputationUpdateResult, FactionInfluenceMap, ReputationAnalysis,
    FactionConflict, FactionQuest, FactionRankProgression,
    Faction, FactionReputation, FactionRelationship, ReputationEvent
)
from ..models.base import EmotionType
from ..models.personality import PersonalityProfileSchema
from ..config import Config

logger = logging.getLogger(__name__)

class FactionService:
    def __init__(self):
        self.config = Config()
        self.reputation_thresholds = self._initialize_reputation_thresholds()
        self.action_impacts = self._initialize_action_impacts()
        self.faction_relationships = self._initialize_faction_relationships()
        self.rank_progressions = self._initialize_rank_progressions()
        
    def _initialize_reputation_thresholds(self) -> Dict[ReputationLevel, Tuple[int, int]]:
        """Initialize reputation score thresholds for each level."""
        return {
            ReputationLevel.DESPISED: (-100, -81),
            ReputationLevel.HATED: (-80, -61),
            ReputationLevel.HOSTILE: (-60, -41),
            ReputationLevel.UNFRIENDLY: (-40, -21),
            ReputationLevel.NEUTRAL: (-20, 20),
            ReputationLevel.FRIENDLY: (21, 40),
            ReputationLevel.HONORED: (41, 60),
            ReputationLevel.EXALTED: (61, 80),
            ReputationLevel.REVERED: (81, 100)
        }
    
    def _initialize_action_impacts(self) -> Dict[ReputationAction, Dict[str, int]]:
        """Initialize reputation impact for different actions."""
        return {
            ReputationAction.QUEST_COMPLETION: {
                "minor": 5,
                "moderate": 15,
                "major": 30,
                "epic": 50
            },
            ReputationAction.QUEST_FAILURE: {
                "minor": -2,
                "moderate": -8,
                "major": -15,
                "epic": -25
            },
            ReputationAction.BETRAYAL: {
                "minor": -20,
                "moderate": -40,
                "major": -60,
                "epic": -80
            },
            ReputationAction.ALLIANCE: {
                "minor": 10,
                "moderate": 20,
                "major": 35,
                "epic": 50
            },
            ReputationAction.COMBAT_VICTORY: {
                "minor": 3,
                "moderate": 8,
                "major": 15,
                "epic": 25
            },
            ReputationAction.COMBAT_DEFEAT: {
                "minor": -1,
                "moderate": -5,
                "major": -10,
                "epic": -15
            },
            ReputationAction.MEMBER_HELPED: {
                "minor": 2,
                "moderate": 5,
                "major": 10,
                "epic": 15
            },
            ReputationAction.MEMBER_HARMED: {
                "minor": -5,
                "moderate": -15,
                "major": -25,
                "epic": -40
            },
            ReputationAction.RIVAL_FACTION_AIDED: {
                "minor": -3,
                "moderate": -10,
                "major": -20,
                "epic": -35
            },
            ReputationAction.SECRETS_REVEALED: {
                "minor": -10,
                "moderate": -25,
                "major": -45,
                "epic": -70
            }
        }
    
    def _initialize_faction_relationships(self) -> Dict[str, Dict[str, FactionRelationType]]:
        """Initialize relationships between factions."""
        # In a real implementation, this would be loaded from database
        return {
            "thieves_guild": {
                "city_guard": FactionRelationType.HOSTILE,
                "merchant_guild": FactionRelationType.RIVAL,
                "nobles": FactionRelationType.ENEMY
            },
            "city_guard": {
                "thieves_guild": FactionRelationType.HOSTILE,
                "nobles": FactionRelationType.ALLIED,
                "church": FactionRelationType.FRIENDLY
            },
            "merchant_guild": {
                "thieves_guild": FactionRelationType.RIVAL,
                "nobles": FactionRelationType.FRIENDLY,
                "adventurers_guild": FactionRelationType.ALLIED
            }
        }
    
    def _initialize_rank_progressions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize rank progression systems for different faction types."""
        return {
            FactionType.GUILD.value: [
                {"rank": "apprentice", "min_reputation": 0, "benefits": ["basic_access"]},
                {"rank": "journeyman", "min_reputation": 25, "benefits": ["advanced_training", "discount"]},
                {"rank": "expert", "min_reputation": 50, "benefits": ["leadership_roles", "special_missions"]},
                {"rank": "master", "min_reputation": 75, "benefits": ["faction_influence", "exclusive_resources"]}
            ],
            FactionType.MILITARY.value: [
                {"rank": "recruit", "min_reputation": 0, "benefits": ["basic_equipment"]},
                {"rank": "private", "min_reputation": 15, "benefits": ["better_equipment", "squad_assignment"]},
                {"rank": "sergeant", "min_reputation": 40, "benefits": ["command_authority", "officer_privileges"]},
                {"rank": "captain", "min_reputation": 65, "benefits": ["strategic_input", "elite_units"]},
                {"rank": "general", "min_reputation": 85, "benefits": ["faction_leadership", "major_influence"]}
            ]
        }

    async def get_character_reputation(
        self,
        character_id: str,
        faction_id: str,
        db_session: Optional[Session] = None
    ) -> Optional[FactionReputationSchema]:
        """Get character's reputation with a specific faction."""
        
        # In a real implementation, this would query the database
        # For now, return mock data
        return FactionReputationSchema(
            character_id=character_id,
            faction_id=faction_id,
            reputation_score=35,
            reputation_level=ReputationLevel.FRIENDLY,
            faction_standing=FactionStanding.MEMBER,
            is_member=True,
            member_rank="journeyman",
            join_date=datetime.utcnow() - timedelta(days=90),
            last_interaction=datetime.utcnow() - timedelta(days=5),
            interaction_frequency=0.7,
            reputation_trend="rising"
        )

    async def update_reputation(
        self,
        event: ReputationEventSchema,
        db_session: Optional[Session] = None
    ) -> ReputationUpdateResult:
        """Update character's reputation based on an action."""
        
        # Get current reputation
        current_reputation = await self.get_character_reputation(
            event.character_id, event.faction_id, db_session
        )
        
        if not current_reputation:
            # Create new reputation record
            current_reputation = FactionReputationSchema(
                character_id=event.character_id,
                faction_id=event.faction_id,
                reputation_score=0,
                reputation_level=ReputationLevel.NEUTRAL
            )
        
        # Calculate reputation change
        reputation_change = await self._calculate_reputation_change(
            event, current_reputation
        )
        
        # Apply the change
        old_reputation = current_reputation.copy()
        new_score = max(-100, min(100, current_reputation.reputation_score + reputation_change))
        
        # Update reputation level
        new_level = self._get_reputation_level(new_score)
        level_changed = new_level != current_reputation.reputation_level
        
        # Update reputation record
        current_reputation.reputation_score = new_score
        current_reputation.previous_level = current_reputation.reputation_level
        current_reputation.reputation_level = new_level
        current_reputation.last_interaction = datetime.utcnow()
        
        # Track reputation changes
        if not current_reputation.reputation_changes:
            current_reputation.reputation_changes = []
        
        current_reputation.reputation_changes.append({
            "timestamp": datetime.utcnow().isoformat(),
            "action": event.action_taken.value,
            "change": reputation_change,
            "new_score": new_score,
            "description": event.event_description
        })
        
        # Update trend
        current_reputation.reputation_trend = await self._calculate_reputation_trend(
            current_reputation.reputation_changes
        )
        
        # Check for standing changes
        await self._update_faction_standing(current_reputation)
        
        # Calculate secondary effects
        secondary_effects = await self._calculate_secondary_effects(
            event, old_reputation, current_reputation
        )
        
        # Find new/lost opportunities
        new_opportunities, lost_opportunities = await self._analyze_opportunities(
            old_reputation, current_reputation
        )
        
        # Save reputation event
        await self._save_reputation_event(
            event, old_reputation.reputation_score, new_score, reputation_change, db_session
        )
        
        return ReputationUpdateResult(
            character_id=event.character_id,
            faction_id=event.faction_id,
            old_reputation=old_reputation,
            new_reputation=current_reputation,
            reputation_change=reputation_change,
            level_changed=level_changed,
            secondary_effects=secondary_effects,
            new_opportunities=new_opportunities,
            lost_opportunities=lost_opportunities
        )

    async def get_all_character_reputations(
        self,
        character_id: str,
        db_session: Optional[Session] = None
    ) -> List[FactionReputationSchema]:
        """Get all of a character's faction reputations."""
        
        # In a real implementation, this would query the database
        # For now, return mock data
        return [
            FactionReputationSchema(
                character_id=character_id,
                faction_id="thieves_guild",
                reputation_score=45,
                reputation_level=ReputationLevel.HONORED,
                faction_standing=FactionStanding.VETERAN,
                is_member=True
            ),
            FactionReputationSchema(
                character_id=character_id,
                faction_id="city_guard",
                reputation_score=-15,
                reputation_level=ReputationLevel.NEUTRAL,
                faction_standing=FactionStanding.OUTSIDER,
                is_member=False
            ),
            FactionReputationSchema(
                character_id=character_id,
                faction_id="merchant_guild",
                reputation_score=25,
                reputation_level=ReputationLevel.FRIENDLY,
                faction_standing=FactionStanding.ASSOCIATE,
                is_member=False
            )
        ]

    async def analyze_character_reputation(
        self,
        character_id: str,
        db_session: Optional[Session] = None
    ) -> ReputationAnalysis:
        """Analyze character's overall reputation status."""
        
        reputations = await self.get_all_character_reputations(character_id, db_session)
        
        # Calculate statistics
        positive_count = sum(1 for rep in reputations if rep.reputation_score > 0)
        negative_count = sum(1 for rep in reputations if rep.reputation_score < 0)
        neutral_count = len(reputations) - positive_count - negative_count
        
        memberships = [rep.faction_id for rep in reputations if rep.is_member]
        
        # Find highest and lowest reputations
        highest_rep = max(reputations, key=lambda r: r.reputation_score, default=None)
        lowest_rep = min(reputations, key=lambda r: r.reputation_score, default=None)
        
        # Analyze trends
        reputation_trends = {
            rep.faction_id: rep.reputation_trend 
            for rep in reputations 
            if rep.reputation_trend
        }
        
        # Identify conflicts
        conflicts = await self._identify_reputation_conflicts(reputations)
        
        # Identify opportunities
        opportunities = await self._identify_reputation_opportunities(reputations)
        
        return ReputationAnalysis(
            character_id=character_id,
            total_factions_known=len(reputations),
            positive_reputations=positive_count,
            negative_reputations=negative_count,
            neutral_reputations=neutral_count,
            faction_memberships=memberships,
            highest_reputation={
                "faction_id": highest_rep.faction_id if highest_rep else None,
                "score": highest_rep.reputation_score if highest_rep else 0,
                "level": highest_rep.reputation_level.value if highest_rep else None
            },
            lowest_reputation={
                "faction_id": lowest_rep.faction_id if lowest_rep else None,
                "score": lowest_rep.reputation_score if lowest_rep else 0,
                "level": lowest_rep.reputation_level.value if lowest_rep else None
            },
            reputation_trends=reputation_trends,
            conflict_analysis=conflicts,
            opportunity_analysis=opportunities
        )

    async def get_available_faction_quests(
        self,
        character_id: str,
        faction_id: Optional[str] = None,
        db_session: Optional[Session] = None
    ) -> List[FactionQuest]:
        """Get available quests from factions based on reputation."""
        
        if faction_id:
            reputation = await self.get_character_reputation(character_id, faction_id, db_session)
            if not reputation:
                return []
            factions_to_check = [(faction_id, reputation)]
        else:
            reputations = await self.get_all_character_reputations(character_id, db_session)
            factions_to_check = [(rep.faction_id, rep) for rep in reputations]
        
        available_quests = []
        
        for faction_id, reputation in factions_to_check:
            # Get faction's available quests (mock implementation)
            faction_quests = await self._get_faction_quests(faction_id)
            
            for quest in faction_quests:
                # Check if character meets requirements
                if self._meets_quest_requirements(reputation, quest):
                    available_quests.append(quest)
        
        return available_quests

    async def get_faction_rank_progression(
        self,
        character_id: str,
        faction_id: str,
        db_session: Optional[Session] = None
    ) -> Optional[FactionRankProgression]:
        """Get character's rank progression within a faction."""
        
        reputation = await self.get_character_reputation(character_id, faction_id, db_session)
        if not reputation or not reputation.is_member:
            return None
        
        # Get faction information to determine type
        faction = await self._get_faction(faction_id, db_session)
        if not faction:
            return None
        
        # Get rank progression for faction type
        progressions = self.rank_progressions.get(faction.faction_type.value, [])
        if not progressions:
            return None
        
        # Find current and next rank
        current_rank = None
        next_rank = None
        
        for i, rank_info in enumerate(progressions):
            if reputation.reputation_score >= rank_info["min_reputation"]:
                current_rank = rank_info
                if i + 1 < len(progressions):
                    next_rank = progressions[i + 1]
        
        if not current_rank:
            current_rank = progressions[0]  # Default to first rank
            next_rank = progressions[1] if len(progressions) > 1 else None
        
        # Generate requirements for promotion
        requirements = await self._generate_promotion_requirements(
            reputation, current_rank, next_rank
        )
        
        return FactionRankProgression(
            faction_id=faction_id,
            character_id=character_id,
            current_rank=current_rank["rank"],
            next_rank=next_rank["rank"] if next_rank else None,
            requirements_for_promotion=requirements,
            benefits_of_current_rank=current_rank.get("benefits", []),
            benefits_of_next_rank=next_rank.get("benefits", []) if next_rank else None,
            reputation_required_for_next=next_rank["min_reputation"] if next_rank else None
        )

    async def _calculate_reputation_change(
        self,
        event: ReputationEventSchema,
        current_reputation: FactionReputationSchema
    ) -> int:
        """Calculate reputation change for an event."""
        
        # Get base impact for action
        action_impacts = self.action_impacts.get(event.action_taken, {"moderate": 0})
        
        # Determine impact level from context
        impact_level = event.context.get("impact_level", "moderate") if event.context else "moderate"
        base_change = action_impacts.get(impact_level, action_impacts["moderate"])
        
        # Apply modifiers
        
        # 1. Current reputation level affects change magnitude
        reputation_modifier = 1.0
        if event.action_taken in [ReputationAction.QUEST_COMPLETION, ReputationAction.MEMBER_HELPED]:
            # Positive actions have diminishing returns at high reputation
            if current_reputation.reputation_score > 50:
                reputation_modifier = 0.7
            elif current_reputation.reputation_score < -50:
                reputation_modifier = 1.3  # Easier to improve from very low reputation
        elif event.action_taken in [ReputationAction.BETRAYAL, ReputationAction.MEMBER_HARMED]:
            # Negative actions have more impact at high reputation
            if current_reputation.reputation_score > 50:
                reputation_modifier = 1.5
            elif current_reputation.reputation_score < -50:
                reputation_modifier = 0.8
        
        # 2. Witnesses affect impact
        witnesses = event.witnesses or []
        witness_modifier = 1.0 + (len(witnesses) * 0.1)  # More witnesses = more impact
        
        # 3. Location affects impact
        if event.location:
            location_modifier = 1.2  # Actions in important locations have more impact
        else:
            location_modifier = 1.0
        
        # 4. Faction member involvement
        member_involvement_modifier = 1.0
        if event.context and event.context.get("faction_member_involved"):
            member_involvement_modifier = 1.3
        
        # Calculate final change
        final_change = int(base_change * reputation_modifier * witness_modifier * 
                          location_modifier * member_involvement_modifier)
        
        return final_change

    def _get_reputation_level(self, score: int) -> ReputationLevel:
        """Get reputation level from numerical score."""
        for level, (min_score, max_score) in self.reputation_thresholds.items():
            if min_score <= score <= max_score:
                return level
        return ReputationLevel.NEUTRAL  # Fallback

    async def _calculate_reputation_trend(
        self,
        reputation_changes: List[Dict[str, Any]]
    ) -> str:
        """Calculate reputation trend from recent changes."""
        
        if not reputation_changes or len(reputation_changes) < 3:
            return "stable"
        
        # Look at last 5 changes
        recent_changes = reputation_changes[-5:]
        total_change = sum(change.get("change", 0) for change in recent_changes)
        
        if total_change > 10:
            return "rising"
        elif total_change < -10:
            return "falling"
        else:
            return "stable"

    async def _update_faction_standing(
        self,
        reputation: FactionReputationSchema
    ) -> None:
        """Update faction standing based on reputation level."""
        
        # Standing progression based on reputation level
        standing_progression = {
            ReputationLevel.DESPISED: FactionStanding.EXILE,
            ReputationLevel.HATED: FactionStanding.EXILE,
            ReputationLevel.HOSTILE: FactionStanding.OUTSIDER,
            ReputationLevel.UNFRIENDLY: FactionStanding.OUTSIDER,
            ReputationLevel.NEUTRAL: FactionStanding.OUTSIDER,
            ReputationLevel.FRIENDLY: FactionStanding.ASSOCIATE,
            ReputationLevel.HONORED: FactionStanding.MEMBER,
            ReputationLevel.EXALTED: FactionStanding.VETERAN,
            ReputationLevel.REVERED: FactionStanding.OFFICER
        }
        
        new_standing = standing_progression.get(reputation.reputation_level, FactionStanding.OUTSIDER)
        
        # Update standing if it changed
        if new_standing != reputation.faction_standing:
            reputation.faction_standing = new_standing
            
            # Update membership status
            if new_standing in [FactionStanding.MEMBER, FactionStanding.VETERAN, FactionStanding.OFFICER]:
                if not reputation.is_member:
                    reputation.is_member = True
                    reputation.join_date = datetime.utcnow()
            elif new_standing == FactionStanding.EXILE:
                reputation.is_member = False
                reputation.is_exile = True

    async def _calculate_secondary_effects(
        self,
        event: ReputationEventSchema,
        old_reputation: FactionReputationSchema,
        new_reputation: FactionReputationSchema
    ) -> List[Dict[str, Any]]:
        """Calculate secondary effects on other factions."""
        
        secondary_effects = []
        
        # Check if this action affects related factions
        faction_relations = self.faction_relationships.get(event.faction_id, {})
        
        for related_faction, relationship_type in faction_relations.items():
            effect_magnitude = 0
            
            # Determine how this faction's reputation change affects related factions
            if relationship_type == FactionRelationType.ALLIED:
                # Allied factions gain/lose reputation together (but less)
                effect_magnitude = int(new_reputation.reputation_score - old_reputation.reputation_score) // 3
            elif relationship_type == FactionRelationType.ENEMY:
                # Enemy factions have opposite reaction
                effect_magnitude = -int(new_reputation.reputation_score - old_reputation.reputation_score) // 2
            elif relationship_type == FactionRelationType.RIVAL:
                # Rivals have smaller opposite reaction
                effect_magnitude = -int(new_reputation.reputation_score - old_reputation.reputation_score) // 4
            
            if effect_magnitude != 0:
                secondary_effects.append({
                    "faction_id": related_faction,
                    "relationship_type": relationship_type.value,
                    "reputation_change": effect_magnitude,
                    "reason": f"Relationship with {event.faction_id}"
                })
        
        return secondary_effects

    async def _analyze_opportunities(
        self,
        old_reputation: FactionReputationSchema,
        new_reputation: FactionReputationSchema
    ) -> Tuple[List[str], List[str]]:
        """Analyze new opportunities gained and lost."""
        
        new_opportunities = []
        lost_opportunities = []
        
        # Check for level changes
        if new_reputation.reputation_level != old_reputation.reputation_level:
            level_values = {level: i for i, level in enumerate(ReputationLevel)}
            old_level_value = level_values[old_reputation.reputation_level]
            new_level_value = level_values[new_reputation.reputation_level]
            
            if new_level_value > old_level_value:
                # Reputation improved
                new_opportunities.extend([
                    "Access to higher-tier faction quests",
                    "Better rewards from faction missions",
                    "Increased trust from faction members"
                ])
                
                if new_reputation.reputation_level in [ReputationLevel.HONORED, ReputationLevel.EXALTED]:
                    new_opportunities.append("Potential faction leadership opportunities")
            else:
                # Reputation declined
                lost_opportunities.extend([
                    "Access to exclusive faction content",
                    "Favorable pricing from faction merchants",
                    "Protection from faction enemies"
                ])
                
                if new_reputation.reputation_level in [ReputationLevel.HOSTILE, ReputationLevel.HATED]:
                    lost_opportunities.append("Safe passage through faction territory")
        
        # Check for membership changes
        if new_reputation.is_member and not old_reputation.is_member:
            new_opportunities.extend([
                "Faction member benefits",
                "Internal faction missions",
                "Faction equipment and resources"
            ])
        elif not new_reputation.is_member and old_reputation.is_member:
            lost_opportunities.extend([
                "Faction member privileges",
                "Access to faction facilities",
                "Faction protection and support"
            ])
        
        return new_opportunities, lost_opportunities

    async def _identify_reputation_conflicts(
        self,
        reputations: List[FactionReputationSchema]
    ) -> List[str]:
        """Identify conflicts between faction reputations."""
        
        conflicts = []
        
        for i, rep_a in enumerate(reputations):
            for rep_b in reputations[i+1:]:
                faction_a_relations = self.faction_relationships.get(rep_a.faction_id, {})
                relationship = faction_a_relations.get(rep_b.faction_id)
                
                if relationship in [FactionRelationType.ENEMY, FactionRelationType.HOSTILE]:
                    if (rep_a.reputation_score > 20 and rep_b.reputation_score > 20):
                        conflicts.append(
                            f"High reputation with both {rep_a.faction_id} and {rep_b.faction_id} "
                            f"(these factions are {relationship.value})"
                        )
        
        return conflicts

    async def _identify_reputation_opportunities(
        self,
        reputations: List[FactionReputationSchema]
    ) -> List[str]:
        """Identify reputation-based opportunities."""
        
        opportunities = []
        
        # Check for high-reputation factions
        high_rep_factions = [rep for rep in reputations if rep.reputation_score >= 60]
        if high_rep_factions:
            opportunities.append(
                f"Leverage high reputation with {len(high_rep_factions)} factions for diplomatic missions"
            )
        
        # Check for potential alliances
        friendly_factions = [rep for rep in reputations if rep.reputation_score >= 30]
        for rep in friendly_factions:
            faction_allies = self.faction_relationships.get(rep.faction_id, {})
            allied_factions = [fid for fid, rel in faction_allies.items() 
                             if rel == FactionRelationType.ALLIED]
            
            if allied_factions:
                # Check if character has neutral/positive rep with allies
                opportunities.append(
                    f"Use reputation with {rep.faction_id} to improve standing with their allies"
                )
        
        # Check for redemption opportunities
        negative_factions = [rep for rep in reputations 
                           if rep.reputation_score < -20 and rep.redemption_possible]
        if negative_factions:
            opportunities.append(
                f"Potential redemption quests available for {len(negative_factions)} hostile factions"
            )
        
        return opportunities

    async def _save_reputation_event(
        self,
        event: ReputationEventSchema,
        old_score: int,
        new_score: int,
        reputation_change: int,
        db_session: Optional[Session]
    ) -> None:
        """Save reputation event to database."""
        
        # In a real implementation, this would save to database
        logger.info(
            f"Reputation event: {event.character_id} {event.action_taken.value} "
            f"with {event.faction_id}, change: {reputation_change}"
        )

    async def _get_faction_quests(
        self,
        faction_id: str
    ) -> List[FactionQuest]:
        """Get available quests from a faction (mock implementation)."""
        
        # Mock quests for demonstration
        return [
            FactionQuest(
                quest_id=f"quest_{faction_id}_001",
                faction_id=faction_id,
                quest_name="Retrieve Stolen Goods",
                description="Recover stolen merchandise from bandits",
                required_reputation_level=ReputationLevel.NEUTRAL,
                required_standing=FactionStanding.OUTSIDER,
                reputation_reward=15,
                reputation_penalty=5,
                difficulty="moderate",
                estimated_time="2-3 hours"
            ),
            FactionQuest(
                quest_id=f"quest_{faction_id}_002",
                faction_id=faction_id,
                quest_name="Diplomatic Mission",
                description="Negotiate with rival faction",
                required_reputation_level=ReputationLevel.HONORED,
                required_standing=FactionStanding.MEMBER,
                reputation_reward=25,
                reputation_penalty=10,
                difficulty="hard",
                estimated_time="4-6 hours"
            )
        ]

    def _meets_quest_requirements(
        self,
        reputation: FactionReputationSchema,
        quest: FactionQuest
    ) -> bool:
        """Check if character meets quest requirements."""
        
        # Check reputation level
        level_values = {level: i for i, level in enumerate(ReputationLevel)}
        required_level_value = level_values[quest.required_reputation_level]
        current_level_value = level_values[reputation.reputation_level]
        
        if current_level_value < required_level_value:
            return False
        
        # Check standing
        standing_values = {standing: i for i, standing in enumerate(FactionStanding)}
        required_standing_value = standing_values[quest.required_standing]
        current_standing_value = standing_values[reputation.faction_standing]
        
        if current_standing_value < required_standing_value:
            return False
        
        return True

    async def _get_faction(
        self,
        faction_id: str,
        db_session: Optional[Session]
    ) -> Optional[FactionSchema]:
        """Get faction information from database."""
        
        # Mock implementation
        faction_types = {
            "thieves_guild": FactionType.CRIMINAL,
            "city_guard": FactionType.MILITARY,
            "merchant_guild": FactionType.TRADING,
            "mages_college": FactionType.SCHOLARLY
        }
        
        faction_type = faction_types.get(faction_id, FactionType.GUILD)
        
        return FactionSchema(
            id=faction_id,
            name=faction_id.replace("_", " ").title(),
            faction_type=faction_type
        )

    async def _generate_promotion_requirements(
        self,
        reputation: FactionReputationSchema,
        current_rank: Dict[str, Any],
        next_rank: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Generate requirements for promotion to next rank."""
        
        if not next_rank:
            return ["Maximum rank achieved"]
        
        requirements = []
        
        # Reputation requirement
        rep_needed = next_rank["min_reputation"] - reputation.reputation_score
        if rep_needed > 0:
            requirements.append(f"Gain {rep_needed} more reputation points")
        
        # Generic requirements based on rank
        rank_requirements = {
            "journeyman": ["Complete 3 faction missions", "Demonstrate skill mastery"],
            "expert": ["Lead a successful operation", "Train new members"],
            "master": ["Make significant contribution to faction", "Gain approval from faction leadership"],
            "sergeant": ["Show leadership in combat", "Complete officer training"],
            "captain": ["Successfully command a unit", "Demonstrate strategic thinking"],
            "general": ["Achieve major military victory", "Gain political support"]
        }
        
        specific_requirements = rank_requirements.get(next_rank["rank"], ["Complete faction objectives"])
        requirements.extend(specific_requirements)
        
        return requirements