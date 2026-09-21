"""
Dramatic Timing Manager for orchestrating reveals, twists, and dramatic moments
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import random
import math

from ..models.base import (
    Campaign, PlotThread, NarrativeEvent, SessionState, 
    Player, TensionLevel, EngagementLevel
)
from ..config import TIMING_CONFIG, FORESHADOWING_CONFIG
from ..utils.ai_client import AIClient


logger = logging.getLogger(__name__)


class DramaticReveal:
    """Represents a dramatic reveal or twist"""
    def __init__(self, reveal_id: str, reveal_type: str, content: str, 
                 impact_level: float, prerequisites: List[str] = None):
        self.id = reveal_id
        self.type = reveal_type  # character_secret, plot_twist, villain_identity, etc.
        self.content = content
        self.impact_level = impact_level  # 0.0 to 1.0
        self.prerequisites = prerequisites or []
        
        # Timing data
        self.optimal_timing_score: float = 0.0
        self.buildup_sessions: int = 0
        self.foreshadowing_count: int = 0
        self.player_curiosity_level: float = 0.0
        
        # State
        self.revealed: bool = False
        self.queued: bool = False
        self.foreshadowed: List[str] = []  # Session IDs where this was foreshadowed


class DramaticTimingManager:
    """Manages dramatic timing for reveals, twists, and climactic moments"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        
        # Reveal management
        self.pending_reveals: Dict[str, DramaticReveal] = {}
        self.revealed_items: List[DramaticReveal] = []
        self.foreshadowing_opportunities: List[Dict[str, Any]] = []
        
        # Timing analysis
        self.player_curiosity_levels: Dict[str, float] = {}
        self.story_momentum: float = 0.5
        self.dramatic_tension_curve: List[float] = []
        self.session_time_tracking: Dict[str, int] = {}  # session_id -> minutes elapsed
        
        # Pattern analysis
        self.reveal_patterns: Dict[str, Any] = {}
        self.player_response_history: List[Dict[str, Any]] = []
        
    async def initialize_dramatic_timing(self, campaign: Campaign, 
                                       active_plotlines: List[PlotThread]) -> None:
        """Initialize dramatic timing system for a campaign"""
        try:
            # Extract potential reveals from plotlines
            await self._extract_plotline_reveals(active_plotlines)
            
            # Initialize player curiosity tracking
            for player in campaign.players:
                self.player_curiosity_levels[player.id] = 0.5
            
            # Set up timing patterns based on campaign theme
            self._initialize_timing_patterns(campaign.theme)
            
            logger.info(f"Dramatic timing initialized: {len(self.pending_reveals)} pending reveals")
            
        except Exception as e:
            logger.error(f"Error initializing dramatic timing: {e}")
            raise
    
    async def register_reveal(self, reveal_type: str, content: str, 
                            impact_level: float, plotline_id: Optional[str] = None,
                            prerequisites: List[str] = None) -> str:
        """Register a new dramatic reveal"""
        try:
            reveal_id = f"{reveal_type}_{len(self.pending_reveals)}"
            
            reveal = DramaticReveal(
                reveal_id=reveal_id,
                reveal_type=reveal_type,
                content=content,
                impact_level=impact_level,
                prerequisites=prerequisites or []
            )
            
            # Calculate initial buildup requirements
            buildup_config = TIMING_CONFIG["reveal_types"].get(reveal_type, {})
            reveal.buildup_sessions = buildup_config.get("buildup", 2)
            
            self.pending_reveals[reveal_id] = reveal
            
            logger.info(f"Registered reveal: {reveal_id} (type: {reveal_type}, impact: {impact_level})")
            return reveal_id
            
        except Exception as e:
            logger.error(f"Error registering reveal: {e}")
            raise
    
    async def analyze_dramatic_timing(self, session_state: SessionState,
                                    player_states: Dict[str, Player]) -> Dict[str, Any]:
        """Analyze current dramatic timing opportunities"""
        try:
            # Update player curiosity levels
            await self._update_player_curiosity(session_state, player_states)
            
            # Analyze current timing factors
            timing_factors = await self._calculate_timing_factors(session_state)
            
            # Evaluate ready reveals
            ready_reveals = await self._evaluate_ready_reveals(timing_factors, session_state)
            
            # Generate foreshadowing opportunities
            foreshadowing_ops = await self._generate_foreshadowing_opportunities(
                session_state, timing_factors
            )
            
            # Calculate optimal timing scores
            timing_recommendations = await self._generate_timing_recommendations(
                ready_reveals, foreshadowing_ops, timing_factors
            )
            
            return {
                "timing_factors": timing_factors,
                "ready_reveals": ready_reveals,
                "foreshadowing_opportunities": foreshadowing_ops,
                "recommendations": timing_recommendations,
                "overall_dramatic_potential": self._calculate_dramatic_potential(timing_factors)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing dramatic timing: {e}")
            return {"error": str(e)}
    
    async def trigger_reveal(self, reveal_id: str, session_state: SessionState) -> Dict[str, Any]:
        """Trigger a dramatic reveal"""
        try:
            if reveal_id not in self.pending_reveals:
                return {"error": "Reveal not found"}
            
            reveal = self.pending_reveals[reveal_id]
            
            # Check prerequisites
            unmet_prerequisites = await self._check_prerequisites(reveal, session_state)
            if unmet_prerequisites:
                return {
                    "success": False,
                    "reason": "Prerequisites not met",
                    "unmet_prerequisites": unmet_prerequisites
                }
            
            # Execute the reveal
            reveal_execution = await self._execute_reveal(reveal, session_state)
            
            # Move to revealed items
            reveal.revealed = True
            self.revealed_items.append(reveal)
            del self.pending_reveals[reveal_id]
            
            # Update story state
            await self._update_story_state_after_reveal(reveal, session_state)
            
            # Generate follow-up opportunities
            follow_ups = await self._generate_reveal_follow_ups(reveal, session_state)
            
            logger.info(f"Triggered reveal: {reveal_id}")
            
            return {
                "success": True,
                "reveal": {
                    "id": reveal.id,
                    "type": reveal.type,
                    "content": reveal.content,
                    "impact_level": reveal.impact_level
                },
                "execution": reveal_execution,
                "follow_ups": follow_ups,
                "story_impact": self._calculate_reveal_impact(reveal)
            }
            
        except Exception as e:
            logger.error(f"Error triggering reveal: {e}")
            return {"error": str(e)}
    
    async def schedule_foreshadowing(self, reveal_id: str, foreshadowing_type: str,
                                   sessions_ahead: int = 1) -> Dict[str, Any]:
        """Schedule foreshadowing for a future reveal"""
        try:
            if reveal_id not in self.pending_reveals:
                return {"error": "Reveal not found"}
            
            reveal = self.pending_reveals[reveal_id]
            
            # Generate foreshadowing content
            foreshadowing_content = await self._generate_foreshadowing_content(
                reveal, foreshadowing_type
            )
            
            # Schedule the foreshadowing
            foreshadowing_opportunity = {
                "reveal_id": reveal_id,
                "type": foreshadowing_type,
                "content": foreshadowing_content,
                "sessions_ahead": sessions_ahead,
                "subtlety_level": self._calculate_foreshadowing_subtlety(reveal, sessions_ahead),
                "delivery_methods": await self._suggest_foreshadowing_delivery(foreshadowing_type)
            }
            
            self.foreshadowing_opportunities.append(foreshadowing_opportunity)
            
            return {
                "success": True,
                "foreshadowing": foreshadowing_opportunity,
                "timing_advice": await self._generate_foreshadowing_timing_advice(
                    reveal, foreshadowing_type, sessions_ahead
                )
            }
            
        except Exception as e:
            logger.error(f"Error scheduling foreshadowing: {e}")
            return {"error": str(e)}
    
    async def get_dramatic_pacing_report(self, session_state: SessionState) -> Dict[str, Any]:
        """Generate report on dramatic pacing and timing"""
        try:
            # Analyze current pacing
            pacing_analysis = await self._analyze_dramatic_pacing(session_state)
            
            # Evaluate reveal distribution
            reveal_distribution = self._analyze_reveal_distribution()
            
            # Check tension curve health
            tension_analysis = self._analyze_tension_curve(session_state)
            
            # Generate pacing recommendations
            pacing_recommendations = await self._generate_pacing_recommendations(
                pacing_analysis, reveal_distribution, tension_analysis
            )
            
            return {
                "pacing_analysis": pacing_analysis,
                "reveal_distribution": reveal_distribution,
                "tension_analysis": tension_analysis,
                "recommendations": pacing_recommendations,
                "overall_pacing_score": self._calculate_overall_pacing_score(
                    pacing_analysis, reveal_distribution, tension_analysis
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating dramatic pacing report: {e}")
            return {"error": str(e)}
    
    async def suggest_dramatic_moment_enhancements(self, 
                                                 moment_context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest ways to enhance a dramatic moment"""
        try:
            moment_type = moment_context.get("type", "unknown")
            current_tension = moment_context.get("tension_level", TensionLevel.MODERATE)
            player_investment = moment_context.get("player_investment", 0.5)
            
            # Analyze enhancement opportunities
            enhancements = await self._generate_moment_enhancements(
                moment_type, current_tension, player_investment, moment_context
            )
            
            # Suggest timing modifications
            timing_adjustments = await self._suggest_timing_adjustments(moment_context)
            
            # Recommend atmosphere elements
            atmosphere_suggestions = await self._suggest_atmosphere_enhancements(
                moment_type, current_tension
            )
            
            return {
                "enhancements": enhancements,
                "timing_adjustments": timing_adjustments,
                "atmosphere_suggestions": atmosphere_suggestions,
                "effectiveness_prediction": self._predict_enhancement_effectiveness(
                    enhancements, moment_context
                )
            }
            
        except Exception as e:
            logger.error(f"Error suggesting dramatic enhancements: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _extract_plotline_reveals(self, plotlines: List[PlotThread]) -> None:
        """Extract potential reveals from plotlines"""
        for plotline in plotlines:
            for reveal_data in plotline.reveals:
                await self.register_reveal(
                    reveal_type=reveal_data.get("type", "plot_twist"),
                    content=reveal_data.get("content", ""),
                    impact_level=reveal_data.get("impact", 0.7),
                    plotline_id=plotline.id,
                    prerequisites=reveal_data.get("prerequisites", [])
                )
    
    def _initialize_timing_patterns(self, campaign_theme: str) -> None:
        """Initialize timing patterns based on campaign theme"""
        theme_patterns = {
            "mystery": "gradual",
            "horror": "explosive", 
            "political": "slow_burn",
            "heroic_fantasy": "classic_arc"
        }
        
        pattern = theme_patterns.get(campaign_theme, "classic_arc")
        self.reveal_patterns = TIMING_CONFIG["reveal_patterns"].get(pattern, {})
    
    async def _update_player_curiosity(self, session_state: SessionState,
                                     player_states: Dict[str, Player]) -> None:
        """Update player curiosity levels based on recent behavior"""
        for player_id, player in player_states.items():
            current_curiosity = self.player_curiosity_levels.get(player_id, 0.5)
            
            # Factors that increase curiosity
            curiosity_boost = 0.0
            
            # High engagement typically correlates with curiosity
            if player.engagement_level == EngagementLevel.HIGH:
                curiosity_boost += 0.1
            elif player.engagement_level == EngagementLevel.IMMERSED:
                curiosity_boost += 0.2
            
            # Active participation and questions indicate curiosity
            # (This would be tracked from actual gameplay)
            
            # Update curiosity with decay
            new_curiosity = current_curiosity * 0.9 + curiosity_boost
            self.player_curiosity_levels[player_id] = max(0.0, min(1.0, new_curiosity))
    
    async def _calculate_timing_factors(self, session_state: SessionState) -> Dict[str, float]:
        """Calculate factors that influence dramatic timing"""
        factors = {}
        
        # Player curiosity factor
        avg_curiosity = sum(self.player_curiosity_levels.values()) / len(self.player_curiosity_levels) if self.player_curiosity_levels else 0.5
        factors["player_curiosity"] = avg_curiosity
        
        # Story pacing factor
        factors["story_pacing"] = self._calculate_story_pacing_factor(session_state)
        
        # Tension level factor
        tension_values = {
            TensionLevel.CALM: 0.2,
            TensionLevel.BUILDING: 0.4,
            TensionLevel.MODERATE: 0.6,
            TensionLevel.HIGH: 0.8,
            TensionLevel.CLIMACTIC: 1.0
        }
        factors["tension_level"] = tension_values.get(session_state.current_tension, 0.6)
        
        # Session time factor
        factors["session_time_remaining"] = self._calculate_time_remaining_factor(session_state)
        
        # Dramatic appropriateness factor
        factors["dramatic_appropriateness"] = await self._calculate_dramatic_appropriateness(session_state)
        
        return factors
    
    async def _evaluate_ready_reveals(self, timing_factors: Dict[str, float],
                                    session_state: SessionState) -> List[Dict[str, Any]]:
        """Evaluate which reveals are ready to be triggered"""
        ready_reveals = []
        
        for reveal_id, reveal in self.pending_reveals.items():
            # Check if prerequisites are met
            unmet_prereqs = await self._check_prerequisites(reveal, session_state)
            if unmet_prereqs:
                continue
            
            # Calculate timing score
            timing_score = self._calculate_reveal_timing_score(reveal, timing_factors)
            
            # Check if reveal has had sufficient buildup
            if reveal.foreshadowing_count >= reveal.buildup_sessions:
                ready_reveals.append({
                    "reveal_id": reveal_id,
                    "reveal": reveal,
                    "timing_score": timing_score,
                    "readiness": "ready" if timing_score > 0.7 else "moderate" if timing_score > 0.5 else "not_ready"
                })
        
        # Sort by timing score
        ready_reveals.sort(key=lambda x: x["timing_score"], reverse=True)
        
        return ready_reveals
    
    async def _generate_foreshadowing_opportunities(self, session_state: SessionState,
                                                  timing_factors: Dict[str, float]) -> List[Dict[str, Any]]:
        """Generate opportunities for foreshadowing"""
        opportunities = []
        
        for reveal_id, reveal in self.pending_reveals.items():
            if reveal.foreshadowing_count < reveal.buildup_sessions:
                # Generate foreshadowing opportunity
                opportunity = await self._create_foreshadowing_opportunity(
                    reveal, session_state, timing_factors
                )
                opportunities.append(opportunity)
        
        return opportunities
    
    async def _generate_timing_recommendations(self, ready_reveals: List[Dict[str, Any]],
                                             foreshadowing_ops: List[Dict[str, Any]],
                                             timing_factors: Dict[str, float]) -> List[str]:
        """Generate recommendations for dramatic timing"""
        recommendations = []
        
        # Reveal recommendations
        high_score_reveals = [r for r in ready_reveals if r["timing_score"] > 0.8]
        if high_score_reveals:
            reveal = high_score_reveals[0]
            recommendations.append(f"Excellent timing for '{reveal['reveal']['type']}' reveal")
        
        moderate_reveals = [r for r in ready_reveals if 0.5 < r["timing_score"] <= 0.8]
        if moderate_reveals and not high_score_reveals:
            recommendations.append("Consider building more tension before major reveal")
        
        # Foreshadowing recommendations
        if foreshadowing_ops:
            recommendations.append(f"Opportunity to foreshadow {len(foreshadowing_ops)} upcoming reveals")
        
        # Tension management
        tension_factor = timing_factors.get("tension_level", 0.5)
        if tension_factor < 0.3:
            recommendations.append("Consider building tension before dramatic moments")
        elif tension_factor > 0.9:
            recommendations.append("Tension is high - good time for climactic reveals")
        
        return recommendations
    
    def _calculate_dramatic_potential(self, timing_factors: Dict[str, float]) -> float:
        """Calculate overall dramatic potential of the current moment"""
        weights = TIMING_CONFIG["timing_factors"]
        
        weighted_score = sum(
            timing_factors.get(factor, 0.5) * weight
            for factor, weight in weights.items()
        )
        
        return min(1.0, max(0.0, weighted_score))
    
    async def _check_prerequisites(self, reveal: DramaticReveal,
                                 session_state: SessionState) -> List[str]:
        """Check if reveal prerequisites are met"""
        unmet_prerequisites = []
        
        for prereq in reveal.prerequisites:
            if not await self._is_prerequisite_met(prereq, session_state):
                unmet_prerequisites.append(prereq)
        
        return unmet_prerequisites
    
    async def _is_prerequisite_met(self, prerequisite: str, session_state: SessionState) -> bool:
        """Check if a specific prerequisite is met"""
        # This would check various conditions like:
        # - Player has discovered certain information
        # - Specific NPCs have been encountered
        # - Certain plotlines have progressed
        # - Location has been visited
        
        # Placeholder implementation
        return True
    
    async def _execute_reveal(self, reveal: DramaticReveal,
                            session_state: SessionState) -> Dict[str, Any]:
        """Execute a dramatic reveal"""
        execution = {
            "delivery_method": await self._choose_delivery_method(reveal, session_state),
            "atmosphere_setting": await self._generate_reveal_atmosphere(reveal),
            "player_reactions_predicted": await self._predict_player_reactions(reveal),
            "follow_up_hooks": await self._generate_reveal_hooks(reveal)
        }
        
        return execution
    
    async def _update_story_state_after_reveal(self, reveal: DramaticReveal,
                                             session_state: SessionState) -> None:
        """Update story state after a reveal"""
        # Update story momentum
        self.story_momentum = min(1.0, self.story_momentum + reveal.impact_level * 0.3)
        
        # Record the reveal in narrative events
        # This would integrate with the narrative manager
        
        # Update player knowledge state
        # This would track what players now know
    
    async def _generate_reveal_follow_ups(self, reveal: DramaticReveal,
                                        session_state: SessionState) -> List[str]:
        """Generate follow-up opportunities after a reveal"""
        follow_ups = []
        
        if reveal.type == "character_secret":
            follow_ups.extend([
                "Explore character's reaction to exposure",
                "Consider impact on relationships",
                "Potential for blackmail or leverage"
            ])
        elif reveal.type == "plot_twist":
            follow_ups.extend([
                "Reassess previous assumptions",
                "Look for additional clues",
                "Plan response to new information"
            ])
        elif reveal.type == "villain_identity":
            follow_ups.extend([
                "Confront the revealed villain",
                "Investigate their past actions",
                "Warn potential victims"
            ])
        
        return follow_ups
    
    def _calculate_reveal_impact(self, reveal: DramaticReveal) -> Dict[str, float]:
        """Calculate the impact of a reveal on the story"""
        return {
            "narrative_momentum": reveal.impact_level * 0.5,
            "player_knowledge_change": reveal.impact_level * 0.8,
            "story_direction_shift": reveal.impact_level * 0.6,
            "emotional_impact": reveal.impact_level * 0.7
        }
    
    async def _generate_foreshadowing_content(self, reveal: DramaticReveal,
                                            foreshadowing_type: str) -> str:
        """Generate foreshadowing content for a reveal"""
        try:
            prompt = f"""
            Generate {foreshadowing_type} foreshadowing for this upcoming reveal:
            
            Reveal type: {reveal.type}
            Reveal content: {reveal.content}
            Impact level: {reveal.impact_level}
            
            The foreshadowing should be:
            1. Subtle enough not to give away the reveal
            2. Meaningful in hindsight
            3. Appropriate for the {foreshadowing_type} delivery method
            
            Generate specific foreshadowing content.
            """
            
            response = await self.ai_client.generate_completion(prompt, max_tokens=200)
            return response
            
        except Exception as e:
            logger.error(f"Error generating foreshadowing content: {e}")
            return f"Subtle hint related to {reveal.type}"
    
    def _calculate_foreshadowing_subtlety(self, reveal: DramaticReveal,
                                        sessions_ahead: int) -> float:
        """Calculate appropriate subtlety level for foreshadowing"""
        # More sessions ahead = more subtle
        # Higher impact reveals need more buildup
        base_subtlety = 0.8
        
        # Adjust based on sessions ahead
        if sessions_ahead > 3:
            base_subtlety = 0.9  # Very subtle
        elif sessions_ahead < 2:
            base_subtlety = 0.6  # More obvious
        
        # Adjust based on impact
        impact_adjustment = reveal.impact_level * 0.2
        
        return min(1.0, base_subtlety + impact_adjustment)
    
    async def _suggest_foreshadowing_delivery(self, foreshadowing_type: str) -> List[str]:
        """Suggest delivery methods for foreshadowing"""
        delivery_methods = {
            "subtle_hint": [
                "Casual NPC comment",
                "Environmental detail",
                "Overheard conversation"
            ],
            "symbolic_reference": [
                "Visual metaphor",
                "Meaningful item placement",
                "Atmospheric description"
            ],
            "prophetic_statement": [
                "Oracle or wise character",
                "Ancient text or inscription",
                "Dream or vision"
            ],
            "ominous_warning": [
                "Worried NPC warning",
                "Foreboding environmental signs",
                "Mysterious message"
            ]
        }
        
        return delivery_methods.get(foreshadowing_type, ["Direct narrative"])
    
    async def _generate_foreshadowing_timing_advice(self, reveal: DramaticReveal,
                                                  foreshadowing_type: str,
                                                  sessions_ahead: int) -> Dict[str, Any]:
        """Generate advice for timing foreshadowing"""
        return {
            "optimal_scene_position": "mid_session",
            "tension_level_needed": "building_to_moderate",
            "player_attention_required": "focused_but_not_suspicious",
            "delivery_pacing": "casual_and_natural",
            "follow_up_needed": sessions_ahead > 2
        }
    
    def _calculate_reveal_timing_score(self, reveal: DramaticReveal,
                                     timing_factors: Dict[str, float]) -> float:
        """Calculate timing score for a reveal"""
        score = 0.0
        weights = TIMING_CONFIG["timing_factors"]
        
        for factor, factor_value in timing_factors.items():
            weight = weights.get(factor, 0.1)
            
            # Different reveals benefit from different timing factors
            if reveal.type == "character_secret" and factor == "player_curiosity":
                weight *= 1.5  # Character secrets benefit more from curiosity
            elif reveal.type == "plot_twist" and factor == "story_pacing":
                weight *= 1.3  # Plot twists benefit from good pacing
            elif reveal.type == "villain_identity" and factor == "tension_level":
                weight *= 1.4  # Villain reveals benefit from high tension
            
            score += factor_value * weight
        
        # Bonus for sufficient buildup
        if reveal.foreshadowing_count >= reveal.buildup_sessions:
            score += 0.2
        
        # Penalty for insufficient buildup
        elif reveal.foreshadowing_count == 0:
            score -= 0.3
        
        return max(0.0, min(1.0, score))
    
    def _calculate_story_pacing_factor(self, session_state: SessionState) -> float:
        """Calculate story pacing factor"""
        # This would analyze scene changes, player actions, narrative beats
        # For now, return a moderate value
        return 0.6
    
    def _calculate_time_remaining_factor(self, session_state: SessionState) -> float:
        """Calculate factor based on session time remaining"""
        # Assuming 4-hour sessions (240 minutes)
        session_duration = 240
        elapsed = session_state.time_elapsed
        
        if elapsed < 60:  # First hour
            return 0.3  # Early in session
        elif elapsed < 180:  # Middle hours
            return 0.8  # Good timing for reveals
        else:  # Final hour
            return 0.6  # Ending/wrapping up
    
    async def _calculate_dramatic_appropriateness(self, session_state: SessionState) -> float:
        """Calculate how dramatically appropriate the current moment is"""
        # This would analyze current scene type, player actions, etc.
        # For now, return moderate appropriateness
        return 0.7
    
    async def _create_foreshadowing_opportunity(self, reveal: DramaticReveal,
                                             session_state: SessionState,
                                             timing_factors: Dict[str, float]) -> Dict[str, Any]:
        """Create a foreshadowing opportunity"""
        foreshadowing_types = list(FORESHADOWING_CONFIG["foreshadowing_types"].keys())
        suitable_type = random.choice(foreshadowing_types)  # Could be more sophisticated
        
        return {
            "reveal_id": reveal.id,
            "foreshadowing_type": suitable_type,
            "urgency": "medium" if reveal.foreshadowing_count == 0 else "low",
            "suggested_delivery": await self._suggest_foreshadowing_delivery(suitable_type),
            "timing_score": timing_factors.get("dramatic_appropriateness", 0.5)
        }
    
    async def _choose_delivery_method(self, reveal: DramaticReveal,
                                    session_state: SessionState) -> str:
        """Choose the best delivery method for a reveal"""
        delivery_methods = {
            "character_secret": "emotional_confrontation",
            "plot_twist": "dramatic_discovery",
            "villain_identity": "shocking_revelation",
            "world_truth": "profound_realization",
            "prophecy_fulfillment": "climactic_moment"
        }
        
        return delivery_methods.get(reveal.type, "narrative_exposition")
    
    async def _generate_reveal_atmosphere(self, reveal: DramaticReveal) -> Dict[str, str]:
        """Generate atmosphere setting for a reveal"""
        return {
            "lighting": "dramatic",
            "music_mood": "tense_to_climactic",
            "pacing": "slow_buildup_to_impact",
            "focus": "all_attention_on_reveal"
        }
    
    async def _predict_player_reactions(self, reveal: DramaticReveal) -> List[str]:
        """Predict likely player reactions to a reveal"""
        reactions = {
            "character_secret": ["shock", "betrayal", "understanding"],
            "plot_twist": ["surprise", "reevaluation", "excitement"],
            "villain_identity": ["anger", "determination", "fear"],
            "world_truth": ["awe", "confusion", "philosophical_discussion"]
        }
        
        return reactions.get(reveal.type, ["surprise", "interest"])
    
    async def _generate_reveal_hooks(self, reveal: DramaticReveal) -> List[str]:
        """Generate hooks that come from a reveal"""
        return [
            "Immediate consequences to address",
            "New questions raised",
            "Changed relationships to explore",
            "Strategic implications to consider"
        ]
    
    async def _analyze_dramatic_pacing(self, session_state: SessionState) -> Dict[str, Any]:
        """Analyze current dramatic pacing"""
        return {
            "pacing_score": 0.7,
            "tension_progression": "appropriate",
            "reveal_distribution": "balanced",
            "buildup_quality": "good"
        }
    
    def _analyze_reveal_distribution(self) -> Dict[str, Any]:
        """Analyze distribution of reveals across sessions"""
        total_reveals = len(self.revealed_items)
        recent_reveals = [r for r in self.revealed_items if True]  # Would check recent sessions
        
        return {
            "total_reveals": total_reveals,
            "recent_reveal_rate": len(recent_reveals),
            "distribution_balance": "even",
            "upcoming_reveals": len(self.pending_reveals)
        }
    
    def _analyze_tension_curve(self, session_state: SessionState) -> Dict[str, Any]:
        """Analyze tension curve health"""
        return {
            "current_tension": session_state.current_tension.value,
            "tension_trend": "building",
            "peak_management": "good",
            "valley_management": "adequate"
        }
    
    async def _generate_pacing_recommendations(self, pacing_analysis: Dict[str, Any],
                                             reveal_distribution: Dict[str, Any],
                                             tension_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for pacing improvement"""
        recommendations = []
        
        if reveal_distribution["recent_reveal_rate"] > 3:
            recommendations.append("Consider spacing out major reveals")
        elif reveal_distribution["recent_reveal_rate"] == 0:
            recommendations.append("Look for opportunities to advance storylines")
        
        if tension_analysis["current_tension"] == "calm":
            recommendations.append("Build tension before next major reveal")
        
        return recommendations
    
    def _calculate_overall_pacing_score(self, pacing_analysis: Dict[str, Any],
                                      reveal_distribution: Dict[str, Any],
                                      tension_analysis: Dict[str, Any]) -> float:
        """Calculate overall pacing score"""
        pacing_score = pacing_analysis.get("pacing_score", 0.5)
        # Would incorporate other factors
        return pacing_score
    
    async def _generate_moment_enhancements(self, moment_type: str,
                                          current_tension: TensionLevel,
                                          player_investment: float,
                                          context: Dict[str, Any]) -> List[str]:
        """Generate enhancements for a dramatic moment"""
        enhancements = []
        
        if current_tension.value in ["calm", "building"]:
            enhancements.append("Build tension with environmental details")
        
        if player_investment < 0.6:
            enhancements.append("Connect moment to character backstories")
        
        if moment_type == "revelation":
            enhancements.extend([
                "Pause for impact after reveal",
                "Allow player reactions and questions",
                "Build on emotional resonance"
            ])
        
        return enhancements
    
    async def _suggest_timing_adjustments(self, moment_context: Dict[str, Any]) -> List[str]:
        """Suggest timing adjustments for a dramatic moment"""
        return [
            "Consider building more anticipation",
            "Allow emotional beats to breathe",
            "Time revelation for maximum impact"
        ]
    
    async def _suggest_atmosphere_enhancements(self, moment_type: str,
                                             current_tension: TensionLevel) -> List[str]:
        """Suggest atmosphere enhancements"""
        return [
            "Lower your voice for intimate moments",
            "Use pauses for dramatic effect",
            "Describe environmental reactions",
            "Focus on sensory details"
        ]
    
    def _predict_enhancement_effectiveness(self, enhancements: List[str],
                                         context: Dict[str, Any]) -> float:
        """Predict effectiveness of suggested enhancements"""
        # Would use AI to predict based on context and player history
        return 0.75