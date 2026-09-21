"""
Player Engagement Monitor for tracking and improving player participation and enjoyment
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque, defaultdict
import statistics

from ..models.base import Player, SessionState, EngagementLevel
from ..config import ENGAGEMENT_CONFIG
from ..utils.ai_client import AIClient


logger = logging.getLogger(__name__)


class PlayerEngagementMonitor:
    """Monitors and analyzes player engagement in real-time"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        
        # Engagement tracking
        self.engagement_history: Dict[str, deque] = {}  # player_id -> engagement readings
        self.current_engagement: Dict[str, EngagementLevel] = {}
        self.engagement_factors: Dict[str, Dict[str, float]] = {}
        
        # Behavioral tracking
        self.player_actions: Dict[str, deque] = {}  # player_id -> recent actions
        self.speaking_time: Dict[str, int] = {}  # player_id -> seconds speaking
        self.decision_times: Dict[str, deque] = {}  # player_id -> decision response times
        self.question_counts: Dict[str, int] = {}  # player_id -> questions asked
        self.creative_solutions: Dict[str, int] = {}  # player_id -> creative solution count
        
        # Analysis data
        self.last_engagement_check: datetime = datetime.utcnow()
        self.intervention_history: List[Dict[str, Any]] = []
        self.engagement_trends: Dict[str, List[float]] = {}
        
        # Session tracking
        self.session_start_time: Optional[datetime] = None
        self.total_session_time: int = 0  # minutes
    
    async def initialize_monitoring(self, players: List[Player]) -> None:
        """Initialize engagement monitoring for players"""
        try:
            for player in players:
                # Initialize tracking structures
                self.engagement_history[player.id] = deque(maxlen=50)
                self.current_engagement[player.id] = player.engagement_level
                self.engagement_factors[player.id] = {
                    factor: 0.5 for factor in ENGAGEMENT_CONFIG["engagement_factors"]
                }
                
                # Initialize behavioral tracking
                self.player_actions[player.id] = deque(maxlen=20)
                self.speaking_time[player.id] = 0
                self.decision_times[player.id] = deque(maxlen=10)
                self.question_counts[player.id] = 0
                self.creative_solutions[player.id] = 0
                self.engagement_trends[player.id] = []
            
            self.session_start_time = datetime.utcnow()
            
            logger.info(f"Engagement monitoring initialized for {len(players)} players")
            
        except Exception as e:
            logger.error(f"Error initializing engagement monitoring: {e}")
            raise
    
    async def record_player_action(self, player_id: str, action: Dict[str, Any]) -> None:
        """Record a player action and update engagement metrics"""
        try:
            if player_id not in self.player_actions:
                return
            
            action_timestamp = datetime.utcnow()
            action_data = {
                "type": action.get("type", "unknown"),
                "description": action.get("description", ""),
                "timestamp": action_timestamp,
                "initiative_level": action.get("initiative_level", 0.5),
                "creativity_score": action.get("creativity_score", 0.5),
                "roleplay_quality": action.get("roleplay_quality", 0.5)
            }
            
            self.player_actions[player_id].append(action_data)
            
            # Update specific metrics based on action type
            await self._update_action_specific_metrics(player_id, action_data)
            
            # Update engagement factors
            await self._update_engagement_factors(player_id, action_data)
            
        except Exception as e:
            logger.error(f"Error recording player action: {e}")
    
    async def record_speaking_time(self, player_id: str, duration_seconds: int) -> None:
        """Record speaking time for a player"""
        if player_id in self.speaking_time:
            self.speaking_time[player_id] += duration_seconds
    
    async def record_decision_time(self, player_id: str, decision_time_seconds: float) -> None:
        """Record decision response time for a player"""
        if player_id in self.decision_times:
            self.decision_times[player_id].append(decision_time_seconds)
    
    async def record_question(self, player_id: str, question_type: str = "general") -> None:
        """Record a question asked by a player"""
        if player_id in self.question_counts:
            self.question_counts[player_id] += 1
    
    async def record_creative_solution(self, player_id: str, solution_description: str) -> None:
        """Record a creative solution provided by a player"""
        if player_id in self.creative_solutions:
            self.creative_solutions[player_id] += 1
    
    async def check_engagement_levels(self, session_state: SessionState) -> Dict[str, Any]:
        """Check and analyze current engagement levels"""
        try:
            current_time = datetime.utcnow()
            time_since_last_check = (current_time - self.last_engagement_check).total_seconds()
            
            engagement_analysis = {}
            intervention_recommendations = []
            
            for player_id in self.current_engagement.keys():
                # Calculate current engagement level
                engagement_score = await self._calculate_engagement_score(player_id, session_state)
                engagement_level = self._score_to_engagement_level(engagement_score)
                
                # Update current engagement
                previous_engagement = self.current_engagement[player_id]
                self.current_engagement[player_id] = engagement_level
                
                # Record in history
                self.engagement_history[player_id].append({
                    "timestamp": current_time,
                    "level": engagement_level,
                    "score": engagement_score,
                    "factors": self.engagement_factors[player_id].copy()
                })
                
                # Analyze engagement change
                engagement_change = await self._analyze_engagement_change(
                    player_id, previous_engagement, engagement_level
                )
                
                # Check if intervention is needed
                intervention_needed = await self._check_intervention_needed(
                    player_id, engagement_level, engagement_change
                )
                
                engagement_analysis[player_id] = {
                    "current_level": engagement_level,
                    "current_score": engagement_score,
                    "previous_level": previous_engagement,
                    "change": engagement_change,
                    "factors": self.engagement_factors[player_id],
                    "intervention_needed": intervention_needed
                }
                
                if intervention_needed:
                    intervention = await self._generate_intervention_recommendation(
                        player_id, engagement_level, engagement_change, session_state
                    )
                    intervention_recommendations.append(intervention)
            
            # Calculate party-wide engagement metrics
            party_metrics = self._calculate_party_engagement_metrics()
            
            self.last_engagement_check = current_time
            
            return {
                "individual_analysis": engagement_analysis,
                "party_metrics": party_metrics,
                "intervention_recommendations": intervention_recommendations,
                "overall_engagement_trend": self._calculate_overall_trend()
            }
            
        except Exception as e:
            logger.error(f"Error checking engagement levels: {e}")
            return {"error": str(e)}
    
    async def get_player_engagement_report(self, player_id: str) -> Dict[str, Any]:
        """Generate detailed engagement report for a specific player"""
        try:
            if player_id not in self.engagement_history:
                return {"error": "Player not found"}
            
            # Recent engagement history
            recent_history = list(self.engagement_history[player_id])[-10:]
            
            # Calculate trends
            engagement_trend = self._calculate_player_engagement_trend(player_id)
            
            # Analyze behavioral patterns
            behavioral_analysis = await self._analyze_player_behavior(player_id)
            
            # Generate insights
            insights = await self._generate_player_insights(player_id, behavioral_analysis)
            
            # Recommend improvements
            recommendations = await self._generate_player_recommendations(
                player_id, behavioral_analysis, engagement_trend
            )
            
            return {
                "player_id": player_id,
                "current_engagement": self.current_engagement.get(player_id, EngagementLevel.MODERATE),
                "recent_history": recent_history,
                "engagement_trend": engagement_trend,
                "behavioral_analysis": behavioral_analysis,
                "insights": insights,
                "recommendations": recommendations,
                "factors_breakdown": self.engagement_factors.get(player_id, {})
            }
            
        except Exception as e:
            logger.error(f"Error generating player engagement report: {e}")
            return {"error": str(e)}
    
    async def get_party_engagement_summary(self) -> Dict[str, Any]:
        """Generate party-wide engagement summary"""
        try:
            party_summary = {}
            
            # Individual summaries
            for player_id in self.current_engagement.keys():
                summary = await self.get_player_engagement_report(player_id)
                party_summary[player_id] = {
                    "current_level": summary.get("current_engagement", EngagementLevel.MODERATE),
                    "trend": summary.get("engagement_trend", {}).get("direction", "stable"),
                    "needs_attention": summary.get("current_engagement") in [EngagementLevel.DISENGAGED, EngagementLevel.LOW]
                }
            
            # Party metrics
            party_metrics = self._calculate_party_engagement_metrics()
            
            # Identify patterns
            engagement_patterns = self._identify_party_engagement_patterns()
            
            # Generate party recommendations
            party_recommendations = await self._generate_party_recommendations(
                party_summary, party_metrics, engagement_patterns
            )
            
            return {
                "individual_summaries": party_summary,
                "party_metrics": party_metrics,
                "engagement_patterns": engagement_patterns,
                "recommendations": party_recommendations,
                "session_statistics": self._calculate_session_statistics()
            }
            
        except Exception as e:
            logger.error(f"Error generating party engagement summary: {e}")
            return {"error": str(e)}
    
    async def suggest_engagement_interventions(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest specific interventions to improve engagement"""
        try:
            current_scene = context.get("current_scene", "unknown")
            low_engagement_players = context.get("low_engagement_players", [])
            session_time_remaining = context.get("session_time_remaining", 120)
            
            interventions = []
            
            for player_id in low_engagement_players:
                player_interventions = await self._generate_targeted_interventions(
                    player_id, current_scene, session_time_remaining
                )
                interventions.extend(player_interventions)
            
            # Group interventions by type
            grouped_interventions = self._group_interventions_by_type(interventions)
            
            # Prioritize interventions
            prioritized_interventions = self._prioritize_interventions(
                grouped_interventions, context
            )
            
            return {
                "immediate_interventions": prioritized_interventions[:3],
                "medium_term_interventions": prioritized_interventions[3:6],
                "long_term_strategies": prioritized_interventions[6:],
                "implementation_guidance": await self._generate_implementation_guidance(
                    prioritized_interventions[:3]
                )
            }
            
        except Exception as e:
            logger.error(f"Error suggesting engagement interventions: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _update_action_specific_metrics(self, player_id: str, action_data: Dict[str, Any]) -> None:
        """Update metrics specific to the action type"""
        action_type = action_data.get("type", "unknown")
        
        if action_type == "initiative_taking":
            # Player proactively took action
            current_factor = self.engagement_factors[player_id]["initiative_taking"]
            self.engagement_factors[player_id]["initiative_taking"] = min(1.0, current_factor + 0.1)
        
        elif action_type == "creative_solution":
            # Player provided creative solution
            current_factor = self.engagement_factors[player_id]["creative_solutions"]
            self.engagement_factors[player_id]["creative_solutions"] = min(1.0, current_factor + 0.15)
        
        elif action_type == "roleplay":
            # Player engaged in roleplay
            roleplay_quality = action_data.get("roleplay_quality", 0.5)
            current_factor = self.engagement_factors[player_id]["roleplay_quality"]
            self.engagement_factors[player_id]["roleplay_quality"] = (current_factor * 0.8 + roleplay_quality * 0.2)
        
        elif action_type == "rule_engagement":
            # Player engaged with game mechanics
            current_factor = self.engagement_factors[player_id]["rule_engagement"]
            self.engagement_factors[player_id]["rule_engagement"] = min(1.0, current_factor + 0.05)
    
    async def _update_engagement_factors(self, player_id: str, action_data: Dict[str, Any]) -> None:
        """Update engagement factors based on action"""
        factors = self.engagement_factors[player_id]
        
        # Update speech frequency factor
        if "speech" in action_data.get("type", ""):
            factors["speech_frequency"] = min(1.0, factors["speech_frequency"] + 0.05)
        
        # Update decision speed factor
        if "decision" in action_data.get("type", ""):
            decision_speed = 1.0 - min(1.0, action_data.get("decision_time", 30) / 60.0)
            factors["decision_speed"] = factors["decision_speed"] * 0.7 + decision_speed * 0.3
        
        # Decay factors slightly over time
        for factor in factors:
            factors[factor] = max(0.0, factors[factor] - 0.01)
    
    async def _calculate_engagement_score(self, player_id: str, session_state: SessionState) -> float:
        """Calculate overall engagement score for a player"""
        if player_id not in self.engagement_factors:
            return 0.5
        
        factors = self.engagement_factors[player_id]
        weights = ENGAGEMENT_CONFIG["engagement_factors"]
        
        weighted_score = sum(
            factors.get(factor, 0.5) * weight
            for factor, weight in weights.items()
        )
        
        # Apply session-specific adjustments
        session_adjustment = self._calculate_session_adjustment(player_id, session_state)
        
        final_score = max(0.0, min(1.0, weighted_score + session_adjustment))
        return final_score
    
    def _score_to_engagement_level(self, score: float) -> EngagementLevel:
        """Convert engagement score to engagement level"""
        thresholds = ENGAGEMENT_CONFIG["engagement_thresholds"]
        
        for level in [EngagementLevel.IMMERSED, EngagementLevel.HIGH, 
                      EngagementLevel.MODERATE, EngagementLevel.LOW]:
            if score >= thresholds[level]:
                return level
        
        return EngagementLevel.DISENGAGED
    
    async def _analyze_engagement_change(self, player_id: str, 
                                       previous_level: EngagementLevel,
                                       current_level: EngagementLevel) -> Dict[str, Any]:
        """Analyze change in engagement level"""
        level_values = {
            EngagementLevel.DISENGAGED: 0,
            EngagementLevel.LOW: 1,
            EngagementLevel.MODERATE: 2,
            EngagementLevel.HIGH: 3,
            EngagementLevel.IMMERSED: 4
        }
        
        previous_value = level_values[previous_level]
        current_value = level_values[current_level]
        change = current_value - previous_value
        
        if change > 0:
            direction = "improving"
        elif change < 0:
            direction = "declining"
        else:
            direction = "stable"
        
        return {
            "direction": direction,
            "magnitude": abs(change),
            "previous_level": previous_level.value,
            "current_level": current_level.value
        }
    
    async def _check_intervention_needed(self, player_id: str, 
                                       engagement_level: EngagementLevel,
                                       engagement_change: Dict[str, Any]) -> bool:
        """Check if intervention is needed for a player"""
        # Intervention needed for low engagement
        if engagement_level in [EngagementLevel.DISENGAGED, EngagementLevel.LOW]:
            return True
        
        # Intervention needed for declining engagement
        if engagement_change["direction"] == "declining" and engagement_change["magnitude"] >= 2:
            return True
        
        # No intervention needed for stable or improving engagement above low
        return False
    
    async def _generate_intervention_recommendation(self, player_id: str,
                                                  engagement_level: EngagementLevel,
                                                  engagement_change: Dict[str, Any],
                                                  session_state: SessionState) -> Dict[str, Any]:
        """Generate intervention recommendation for a player"""
        strategies = ENGAGEMENT_CONFIG["intervention_strategies"].get(engagement_level, [])
        
        # Select appropriate strategy based on player factors
        player_factors = self.engagement_factors.get(player_id, {})
        
        # Find the factor that needs most improvement
        lowest_factor = min(player_factors.items(), key=lambda x: x[1])
        
        # Generate specific intervention
        intervention = {
            "player_id": player_id,
            "engagement_level": engagement_level.value,
            "primary_issue": lowest_factor[0],
            "strategies": strategies,
            "specific_action": await self._generate_specific_intervention_action(
                player_id, engagement_level, lowest_factor[0], session_state
            ),
            "urgency": "high" if engagement_level == EngagementLevel.DISENGAGED else "medium"
        }
        
        # Add to intervention history
        self.intervention_history.append({
            "timestamp": datetime.utcnow(),
            "player_id": player_id,
            "intervention": intervention,
            "implemented": False
        })
        
        return intervention
    
    async def _generate_specific_intervention_action(self, player_id: str,
                                                   engagement_level: EngagementLevel,
                                                   primary_issue: str,
                                                   session_state: SessionState) -> str:
        """Generate specific intervention action"""
        action_map = {
            "speech_frequency": "Directly ask the player for their character's opinion or reaction",
            "decision_speed": "Provide clearer options or ask for immediate decision",
            "creative_solutions": "Present a problem that requires creative thinking",
            "roleplay_quality": "Create opportunity for character development or personal stakes",
            "rule_engagement": "Involve player in tactical decision or rules clarification",
            "question_frequency": "Encourage questions by asking 'What would you like to know?'",
            "initiative_taking": "Ask 'What does your character want to do here?'"
        }
        
        return action_map.get(primary_issue, "Engage directly with personal conversation")
    
    def _calculate_party_engagement_metrics(self) -> Dict[str, Any]:
        """Calculate party-wide engagement metrics"""
        if not self.current_engagement:
            return {}
        
        engagement_values = {
            EngagementLevel.DISENGAGED: 0,
            EngagementLevel.LOW: 1,
            EngagementLevel.MODERATE: 2,
            EngagementLevel.HIGH: 3,
            EngagementLevel.IMMERSED: 4
        }
        
        scores = [engagement_values[level] for level in self.current_engagement.values()]
        
        return {
            "average_engagement": statistics.mean(scores) if scores else 0,
            "min_engagement": min(scores) if scores else 0,
            "max_engagement": max(scores) if scores else 0,
            "engagement_variance": statistics.variance(scores) if len(scores) > 1 else 0,
            "players_needing_attention": sum(1 for level in self.current_engagement.values() 
                                           if level in [EngagementLevel.DISENGAGED, EngagementLevel.LOW]),
            "highly_engaged_players": sum(1 for level in self.current_engagement.values()
                                        if level in [EngagementLevel.HIGH, EngagementLevel.IMMERSED])
        }
    
    def _calculate_overall_trend(self) -> str:
        """Calculate overall engagement trend"""
        if not self.engagement_history:
            return "unknown"
        
        # Get recent engagement scores
        recent_scores = []
        for player_history in self.engagement_history.values():
            if player_history:
                recent_scores.append(player_history[-1]["score"])
        
        if len(recent_scores) < 2:
            return "insufficient_data"
        
        # Compare current average to earlier average
        current_avg = statistics.mean(recent_scores)
        
        # Get earlier scores for comparison
        earlier_scores = []
        for player_history in self.engagement_history.values():
            if len(player_history) >= 5:
                earlier_scores.append(player_history[-5]["score"])
        
        if not earlier_scores:
            return "improving"  # Assume improvement if no earlier data
        
        earlier_avg = statistics.mean(earlier_scores)
        
        if current_avg > earlier_avg + 0.1:
            return "improving"
        elif current_avg < earlier_avg - 0.1:
            return "declining"
        else:
            return "stable"
    
    def _calculate_player_engagement_trend(self, player_id: str) -> Dict[str, Any]:
        """Calculate engagement trend for a specific player"""
        if player_id not in self.engagement_history or not self.engagement_history[player_id]:
            return {"direction": "unknown", "confidence": 0.0}
        
        history = list(self.engagement_history[player_id])
        if len(history) < 3:
            return {"direction": "insufficient_data", "confidence": 0.0}
        
        # Get recent scores
        recent_scores = [entry["score"] for entry in history[-5:]]
        
        # Calculate trend
        if len(recent_scores) >= 3:
            # Simple linear trend
            x_values = list(range(len(recent_scores)))
            slope = statistics.correlation(x_values, recent_scores) if len(recent_scores) > 1 else 0
            
            if slope > 0.1:
                direction = "improving"
            elif slope < -0.1:
                direction = "declining"
            else:
                direction = "stable"
            
            confidence = min(1.0, len(recent_scores) / 5.0)
        else:
            direction = "stable"
            confidence = 0.3
        
        return {
            "direction": direction,
            "confidence": confidence,
            "recent_average": statistics.mean(recent_scores),
            "sample_size": len(recent_scores)
        }
    
    async def _analyze_player_behavior(self, player_id: str) -> Dict[str, Any]:
        """Analyze behavioral patterns for a player"""
        if player_id not in self.player_actions:
            return {}
        
        recent_actions = list(self.player_actions[player_id])
        
        # Analyze action patterns
        action_types = [action["type"] for action in recent_actions]
        type_counts = defaultdict(int)
        for action_type in action_types:
            type_counts[action_type] += 1
        
        # Calculate behavioral metrics
        total_speaking_time = self.speaking_time.get(player_id, 0)
        session_duration = (datetime.utcnow() - self.session_start_time).total_seconds() if self.session_start_time else 3600
        speaking_percentage = (total_speaking_time / session_duration) * 100 if session_duration > 0 else 0
        
        avg_decision_time = statistics.mean(self.decision_times.get(player_id, [30])) if self.decision_times.get(player_id) else 30
        
        return {
            "total_actions": len(recent_actions),
            "action_type_distribution": dict(type_counts),
            "speaking_time_seconds": total_speaking_time,
            "speaking_percentage": speaking_percentage,
            "average_decision_time": avg_decision_time,
            "questions_asked": self.question_counts.get(player_id, 0),
            "creative_solutions": self.creative_solutions.get(player_id, 0),
            "initiative_score": sum(1 for action in recent_actions if action.get("initiative_level", 0) > 0.7),
            "roleplay_score": statistics.mean([action.get("roleplay_quality", 0.5) for action in recent_actions]) if recent_actions else 0.5
        }
    
    async def _generate_player_insights(self, player_id: str, 
                                       behavioral_analysis: Dict[str, Any]) -> List[str]:
        """Generate insights about a player's engagement"""
        insights = []
        
        # Speaking time insights
        speaking_percentage = behavioral_analysis.get("speaking_percentage", 0)
        if speaking_percentage < 5:
            insights.append("Player speaks very little - may be shy or disengaged")
        elif speaking_percentage > 40:
            insights.append("Player is very vocal - likely engaged but may dominate")
        
        # Decision time insights
        avg_decision_time = behavioral_analysis.get("average_decision_time", 30)
        if avg_decision_time > 60:
            insights.append("Player takes time to make decisions - may need clearer options")
        elif avg_decision_time < 10:
            insights.append("Player decides quickly - likely engaged and confident")
        
        # Creative solutions insights
        creative_solutions = behavioral_analysis.get("creative_solutions", 0)
        if creative_solutions > 2:
            insights.append("Player often provides creative solutions - highly engaged")
        elif creative_solutions == 0:
            insights.append("Player hasn't provided creative solutions - may need encouragement")
        
        # Questions insights
        questions_asked = behavioral_analysis.get("questions_asked", 0)
        if questions_asked > 5:
            insights.append("Player asks many questions - curious and engaged")
        elif questions_asked == 0:
            insights.append("Player asks few questions - may need prompting")
        
        return insights
    
    async def _generate_player_recommendations(self, player_id: str,
                                             behavioral_analysis: Dict[str, Any],
                                             engagement_trend: Dict[str, Any]) -> List[str]:
        """Generate recommendations for improving player engagement"""
        recommendations = []
        
        # Based on speaking time
        speaking_percentage = behavioral_analysis.get("speaking_percentage", 0)
        if speaking_percentage < 10:
            recommendations.append("Directly ask for this player's input more often")
        
        # Based on creative solutions
        creative_solutions = behavioral_analysis.get("creative_solutions", 0)
        if creative_solutions < 1:
            recommendations.append("Present problems that encourage creative thinking")
        
        # Based on engagement trend
        if engagement_trend.get("direction") == "declining":
            recommendations.append("Check in privately about what would make the game more enjoyable")
        
        # Based on questions
        questions_asked = behavioral_analysis.get("questions_asked", 0)
        if questions_asked == 0:
            recommendations.append("Encourage questions by pausing for 'Any questions?'")
        
        return recommendations
    
    def _identify_party_engagement_patterns(self) -> Dict[str, Any]:
        """Identify patterns in party engagement"""
        patterns = {}
        
        # Time-based patterns
        # (Would analyze engagement by time of session)
        
        # Player interaction patterns
        high_engagement_players = [
            player_id for player_id, level in self.current_engagement.items()
            if level in [EngagementLevel.HIGH, EngagementLevel.IMMERSED]
        ]
        
        low_engagement_players = [
            player_id for player_id, level in self.current_engagement.items()
            if level in [EngagementLevel.DISENGAGED, EngagementLevel.LOW]
        ]
        
        patterns["high_engagement_players"] = high_engagement_players
        patterns["low_engagement_players"] = low_engagement_players
        patterns["engagement_polarization"] = len(high_engagement_players) > 0 and len(low_engagement_players) > 0
        
        return patterns
    
    async def _generate_party_recommendations(self, party_summary: Dict[str, Any],
                                            party_metrics: Dict[str, Any],
                                            engagement_patterns: Dict[str, Any]) -> List[str]:
        """Generate party-wide recommendations"""
        recommendations = []
        
        # Based on average engagement
        avg_engagement = party_metrics.get("average_engagement", 2)
        if avg_engagement < 2:
            recommendations.append("Overall party engagement is low - consider changing approach")
        
        # Based on variance
        engagement_variance = party_metrics.get("engagement_variance", 0)
        if engagement_variance > 1:
            recommendations.append("Large variance in engagement - focus on individual needs")
        
        # Based on patterns
        if engagement_patterns.get("engagement_polarization"):
            recommendations.append("Some players highly engaged while others aren't - balance attention")
        
        # Based on needing attention
        players_needing_attention = party_metrics.get("players_needing_attention", 0)
        if players_needing_attention > len(self.current_engagement) / 2:
            recommendations.append("More than half the party needs attention - reassess session approach")
        
        return recommendations
    
    def _calculate_session_statistics(self) -> Dict[str, Any]:
        """Calculate session-wide statistics"""
        if not self.session_start_time:
            return {}
        
        session_duration = (datetime.utcnow() - self.session_start_time).total_seconds() / 60  # minutes
        
        # Calculate total actions across all players
        total_actions = sum(len(actions) for actions in self.player_actions.values())
        
        # Calculate total speaking time
        total_speaking_time = sum(self.speaking_time.values())
        
        return {
            "session_duration_minutes": session_duration,
            "total_player_actions": total_actions,
            "actions_per_minute": total_actions / session_duration if session_duration > 0 else 0,
            "total_speaking_time_seconds": total_speaking_time,
            "speaking_time_percentage": (total_speaking_time / (session_duration * 60)) * 100 if session_duration > 0 else 0,
            "total_questions_asked": sum(self.question_counts.values()),
            "total_creative_solutions": sum(self.creative_solutions.values())
        }
    
    def _calculate_session_adjustment(self, player_id: str, session_state: SessionState) -> float:
        """Calculate session-specific engagement adjustments"""
        adjustment = 0.0
        
        # Time-based adjustments
        if self.session_start_time:
            session_duration = (datetime.utcnow() - self.session_start_time).total_seconds() / 60
            
            # Engagement often drops in later hours
            if session_duration > 180:  # 3+ hours
                adjustment -= 0.1
            elif session_duration > 240:  # 4+ hours
                adjustment -= 0.2
        
        # Scene-based adjustments
        current_scene = session_state.current_scene
        if "combat" in current_scene.lower():
            # Combat usually increases engagement
            adjustment += 0.1
        elif "social" in current_scene.lower() or "roleplay" in current_scene.lower():
            # Social scenes may vary by player preference
            # Would need player preference data
            pass
        
        return adjustment
    
    async def _generate_targeted_interventions(self, player_id: str, 
                                             current_scene: str,
                                             time_remaining: int) -> List[Dict[str, Any]]:
        """Generate targeted interventions for a specific player"""
        interventions = []
        
        # Get player's current factors
        factors = self.engagement_factors.get(player_id, {})
        
        # Find areas that need improvement
        low_factors = [(factor, score) for factor, score in factors.items() if score < 0.4]
        
        for factor, score in low_factors:
            intervention = {
                "player_id": player_id,
                "factor": factor,
                "current_score": score,
                "intervention_type": self._map_factor_to_intervention(factor),
                "scene_specific": self._adapt_intervention_to_scene(factor, current_scene),
                "time_to_implement": self._estimate_intervention_time(factor),
                "priority": self._calculate_intervention_priority(factor, score, time_remaining)
            }
            interventions.append(intervention)
        
        return interventions
    
    def _map_factor_to_intervention(self, factor: str) -> str:
        """Map engagement factor to intervention type"""
        intervention_map = {
            "speech_frequency": "direct_engagement",
            "decision_speed": "decision_support",
            "creative_solutions": "creative_challenge",
            "roleplay_quality": "character_spotlight",
            "rule_engagement": "mechanical_involvement",
            "question_frequency": "information_encouragement",
            "initiative_taking": "agency_opportunity"
        }
        return intervention_map.get(factor, "general_engagement")
    
    def _adapt_intervention_to_scene(self, factor: str, scene: str) -> str:
        """Adapt intervention to current scene context"""
        if "combat" in scene.lower():
            return f"During combat: focus on {factor} through tactical decisions"
        elif "social" in scene.lower():
            return f"During social scene: encourage {factor} through character interaction"
        else:
            return f"In current scene: create opportunity for {factor}"
    
    def _estimate_intervention_time(self, factor: str) -> int:
        """Estimate time needed to implement intervention (minutes)"""
        time_estimates = {
            "speech_frequency": 2,
            "decision_speed": 1,
            "creative_solutions": 5,
            "roleplay_quality": 10,
            "rule_engagement": 3,
            "question_frequency": 1,
            "initiative_taking": 3
        }
        return time_estimates.get(factor, 5)
    
    def _calculate_intervention_priority(self, factor: str, score: float, time_remaining: int) -> float:
        """Calculate priority for intervention"""
        # Lower score = higher priority
        score_priority = 1.0 - score
        
        # Some factors are more critical
        factor_weights = {
            "speech_frequency": 1.2,
            "roleplay_quality": 1.1,
            "initiative_taking": 1.0,
            "creative_solutions": 0.9,
            "decision_speed": 0.8,
            "question_frequency": 0.7,
            "rule_engagement": 0.6
        }
        
        factor_weight = factor_weights.get(factor, 1.0)
        
        # Time sensitivity
        time_factor = min(1.0, time_remaining / 60.0)  # Normalize to hours
        
        return score_priority * factor_weight * time_factor
    
    def _group_interventions_by_type(self, interventions: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group interventions by type"""
        grouped = defaultdict(list)
        for intervention in interventions:
            intervention_type = intervention.get("intervention_type", "general")
            grouped[intervention_type].append(intervention)
        return dict(grouped)
    
    def _prioritize_interventions(self, grouped_interventions: Dict[str, List[Dict[str, Any]]],
                                context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prioritize interventions based on context"""
        all_interventions = []
        for intervention_type, interventions in grouped_interventions.items():
            all_interventions.extend(interventions)
        
        # Sort by priority
        return sorted(all_interventions, key=lambda x: x.get("priority", 0), reverse=True)
    
    async def _generate_implementation_guidance(self, interventions: List[Dict[str, Any]]) -> List[str]:
        """Generate guidance for implementing interventions"""
        guidance = []
        
        for intervention in interventions:
            intervention_type = intervention.get("intervention_type", "general")
            
            if intervention_type == "direct_engagement":
                guidance.append("Address the quiet player directly with a question or request for input")
            elif intervention_type == "creative_challenge":
                guidance.append("Present a problem that requires thinking outside the box")
            elif intervention_type == "character_spotlight":
                guidance.append("Create a moment that highlights this character's background or skills")
            else:
                guidance.append(f"Implement {intervention_type} intervention as appropriate")
        
        return guidance