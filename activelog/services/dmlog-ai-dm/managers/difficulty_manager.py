"""
Adaptive Difficulty Manager for dynamic challenge adjustment based on player success
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import statistics

from ..models.base import Player, GameMetrics, SessionState, DifficultyLevel
from ..config import DIFFICULTY_CONFIG
from ..utils.ai_client import AIClient


logger = logging.getLogger(__name__)


class DifficultyManager:
    """Manages adaptive difficulty based on player performance"""
    
    def __init__(self, ai_client: AIClient):
        self.ai_client = ai_client
        
        # Performance tracking
        self.success_history: Dict[str, deque] = {}  # player_id -> success history
        self.encounter_history: deque = deque(maxlen=50)
        self.last_adjustment_time: datetime = datetime.utcnow()
        
        # Current difficulty state
        self.base_difficulty: DifficultyLevel = DifficultyLevel.MODERATE
        self.player_adjustments: Dict[str, float] = {}  # player_id -> adjustment modifier
        self.encounter_adjustments: Dict[str, float] = {}  # encounter_type -> adjustment
        
        # Analysis data
        self.player_metrics: Dict[str, Dict[str, float]] = {}
        self.adjustment_cooldown: Dict[str, datetime] = {}
        
    async def initialize_difficulty_tracking(self, players: List[Player]) -> None:
        """Initialize difficulty tracking for players"""
        try:
            for player in players:
                self.success_history[player.id] = deque(
                    maxlen=DIFFICULTY_CONFIG["success_tracking_window"]
                )
                self.player_adjustments[player.id] = 0.0
                self.player_metrics[player.id] = {
                    "success_rate": 0.6,
                    "resource_depletion": 0.5,
                    "health_percentage": 1.0,
                    "engagement_level": 0.7,
                    "strategic_thinking": 0.5
                }
                
            logger.info(f"Difficulty tracking initialized for {len(players)} players")
            
        except Exception as e:
            logger.error(f"Error initializing difficulty tracking: {e}")
            raise
    
    async def record_player_outcome(self, player_id: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a player's action or check"""
        try:
            success = outcome.get("success", False)
            challenge_type = outcome.get("type", "unknown")
            difficulty = outcome.get("difficulty", "moderate")
            roll_result = outcome.get("roll_result", 0)
            target_dc = outcome.get("dc", 15)
            
            # Record success/failure
            if player_id not in self.success_history:
                self.success_history[player_id] = deque(
                    maxlen=DIFFICULTY_CONFIG["success_tracking_window"]
                )
            
            self.success_history[player_id].append({
                "success": success,
                "type": challenge_type,
                "difficulty": difficulty,
                "roll_result": roll_result,
                "dc": target_dc,
                "timestamp": datetime.utcnow(),
                "margin": roll_result - target_dc if roll_result and target_dc else 0
            })
            
            # Update player metrics
            await self._update_player_metrics(player_id, outcome)
            
            # Check if adjustment is needed
            await self._check_difficulty_adjustment(player_id)
            
        except Exception as e:
            logger.error(f"Error recording player outcome: {e}")
    
    async def record_encounter_outcome(self, encounter_data: Dict[str, Any]) -> None:
        """Record the outcome of an encounter"""
        try:
            encounter_type = encounter_data.get("type", "combat")
            difficulty = encounter_data.get("difficulty", DifficultyLevel.MODERATE)
            outcome = encounter_data.get("outcome", "success")
            duration_minutes = encounter_data.get("duration", 30)
            resources_used = encounter_data.get("resources_used", {})
            player_performances = encounter_data.get("player_performances", {})
            
            encounter_record = {
                "type": encounter_type,
                "difficulty": difficulty,
                "outcome": outcome,
                "duration": duration_minutes,
                "resources_used": resources_used,
                "player_performances": player_performances,
                "timestamp": datetime.utcnow()
            }
            
            self.encounter_history.append(encounter_record)
            
            # Analyze encounter for difficulty insights
            await self._analyze_encounter_difficulty(encounter_record)
            
            # Update encounter-specific adjustments
            await self._update_encounter_adjustments(encounter_type, encounter_record)
            
        except Exception as e:
            logger.error(f"Error recording encounter outcome: {e}")
    
    async def get_adjusted_difficulty(self, base_difficulty: DifficultyLevel,
                                    encounter_type: str = "combat",
                                    target_player: Optional[str] = None) -> Dict[str, Any]:
        """Get difficulty adjusted for current player performance"""
        try:
            # Start with base difficulty
            adjusted_difficulty = base_difficulty
            adjustment_factors = []
            
            # Apply global difficulty trends
            global_adjustment = await self._calculate_global_adjustment()
            adjustment_factors.append(("global_trend", global_adjustment))
            
            # Apply encounter-type specific adjustments
            encounter_adjustment = self.encounter_adjustments.get(encounter_type, 0.0)
            adjustment_factors.append(("encounter_specific", encounter_adjustment))
            
            # Apply player-specific adjustments if targeting specific player
            if target_player and target_player in self.player_adjustments:
                player_adjustment = self.player_adjustments[target_player]
                adjustment_factors.append(("player_specific", player_adjustment))
            else:
                # Use average player adjustment
                avg_adjustment = statistics.mean(self.player_adjustments.values()) if self.player_adjustments else 0.0
                adjustment_factors.append(("average_player", avg_adjustment))
            
            # Calculate total adjustment
            total_adjustment = sum(factor[1] for factor in adjustment_factors)
            
            # Apply adjustment to difficulty
            adjusted_difficulty = self._apply_difficulty_adjustment(
                base_difficulty, total_adjustment
            )
            
            # Generate specific recommendations
            recommendations = await self._generate_difficulty_recommendations(
                adjusted_difficulty, encounter_type, adjustment_factors
            )
            
            return {
                "base_difficulty": base_difficulty.value,
                "adjusted_difficulty": adjusted_difficulty.value,
                "total_adjustment": total_adjustment,
                "adjustment_factors": adjustment_factors,
                "recommendations": recommendations,
                "confidence": self._calculate_adjustment_confidence()
            }
            
        except Exception as e:
            logger.error(f"Error calculating adjusted difficulty: {e}")
            return {
                "base_difficulty": base_difficulty.value,
                "adjusted_difficulty": base_difficulty.value,
                "error": str(e)
            }
    
    async def get_player_performance_analysis(self, player_id: str) -> Dict[str, Any]:
        """Analyze a specific player's performance"""
        try:
            if player_id not in self.success_history:
                return {"error": "No performance data for player"}
            
            history = list(self.success_history[player_id])
            if not history:
                return {"error": "No performance history available"}
            
            # Calculate success rates by category
            success_rates = await self._calculate_success_rates_by_category(history)
            
            # Analyze trends
            trends = self._analyze_performance_trends(history)
            
            # Get current metrics
            current_metrics = self.player_metrics.get(player_id, {})
            
            # Generate performance insights
            insights = await self._generate_performance_insights(
                player_id, success_rates, trends, current_metrics
            )
            
            # Calculate difficulty recommendation
            recommended_adjustment = self._calculate_player_difficulty_recommendation(
                success_rates, trends, current_metrics
            )
            
            return {
                "player_id": player_id,
                "overall_success_rate": sum(1 for h in history if h["success"]) / len(history),
                "success_rates_by_category": success_rates,
                "performance_trends": trends,
                "current_metrics": current_metrics,
                "insights": insights,
                "recommended_adjustment": recommended_adjustment,
                "sample_size": len(history)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing player performance: {e}")
            return {"error": str(e)}
    
    async def get_party_difficulty_report(self) -> Dict[str, Any]:
        """Generate comprehensive difficulty report for the entire party"""
        try:
            party_analysis = {}
            
            # Analyze each player
            for player_id in self.success_history.keys():
                party_analysis[player_id] = await self.get_player_performance_analysis(player_id)
            
            # Calculate party-wide metrics
            party_metrics = await self._calculate_party_metrics(party_analysis)
            
            # Analyze encounter trends
            encounter_analysis = self._analyze_encounter_trends()
            
            # Generate party recommendations
            recommendations = await self._generate_party_recommendations(
                party_metrics, encounter_analysis
            )
            
            return {
                "party_analysis": party_analysis,
                "party_metrics": party_metrics,
                "encounter_trends": encounter_analysis,
                "recommendations": recommendations,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating party difficulty report: {e}")
            return {"error": str(e)}
    
    async def suggest_encounter_modifications(self, encounter_template: Dict[str, Any]) -> Dict[str, Any]:
        """Suggest modifications to make an encounter appropriately challenging"""
        try:
            base_cr = encounter_template.get("cr", 5)
            encounter_type = encounter_template.get("type", "combat")
            estimated_difficulty = encounter_template.get("difficulty", "moderate")
            
            # Get current difficulty adjustment
            adjustment_info = await self.get_adjusted_difficulty(
                DifficultyLevel(estimated_difficulty), encounter_type
            )
            
            # Calculate CR adjustment
            cr_adjustment = self._convert_difficulty_to_cr_adjustment(
                adjustment_info["total_adjustment"]
            )
            
            suggested_cr = max(1, base_cr + cr_adjustment)
            
            # Generate specific modifications
            modifications = await self._generate_encounter_modifications(
                encounter_template, cr_adjustment, adjustment_info
            )
            
            return {
                "original_cr": base_cr,
                "suggested_cr": suggested_cr,
                "cr_adjustment": cr_adjustment,
                "difficulty_reasoning": adjustment_info["adjustment_factors"],
                "specific_modifications": modifications,
                "confidence": adjustment_info["confidence"]
            }
            
        except Exception as e:
            logger.error(f"Error suggesting encounter modifications: {e}")
            return {"error": str(e)}
    
    # Private methods
    
    async def _update_player_metrics(self, player_id: str, outcome: Dict[str, Any]) -> None:
        """Update comprehensive player metrics"""
        if player_id not in self.player_metrics:
            return
        
        metrics = self.player_metrics[player_id]
        
        # Update success rate (recent weighted average)
        recent_success = outcome.get("success", False)
        metrics["success_rate"] = metrics["success_rate"] * 0.9 + (1.0 if recent_success else 0.0) * 0.1
        
        # Update resource depletion if provided
        if "resource_depletion" in outcome:
            metrics["resource_depletion"] = outcome["resource_depletion"]
        
        # Update health percentage if provided
        if "health_percentage" in outcome:
            metrics["health_percentage"] = outcome["health_percentage"]
        
        # Update engagement level if provided
        if "engagement_level" in outcome:
            metrics["engagement_level"] = outcome["engagement_level"]
        
        # Assess strategic thinking based on outcome margin
        margin = outcome.get("margin", 0)
        if margin > 5:  # Significant success
            metrics["strategic_thinking"] = min(1.0, metrics["strategic_thinking"] + 0.02)
        elif margin < -3:  # Significant failure
            metrics["strategic_thinking"] = max(0.0, metrics["strategic_thinking"] - 0.01)
    
    async def _check_difficulty_adjustment(self, player_id: str) -> None:
        """Check if difficulty adjustment is needed for a player"""
        try:
            # Check cooldown
            if (player_id in self.adjustment_cooldown and 
                datetime.utcnow() - self.adjustment_cooldown[player_id] < 
                timedelta(seconds=DIFFICULTY_CONFIG["min_adjustment_interval"])):
                return
            
            if player_id not in self.success_history or not self.success_history[player_id]:
                return
            
            history = list(self.success_history[player_id])
            if len(history) < 5:  # Need minimum sample size
                return
            
            # Calculate recent success rate
            recent_successes = sum(1 for h in history[-5:] if h["success"])
            success_rate = recent_successes / 5
            
            # Get target success rate based on current difficulty
            target_rate = DIFFICULTY_CONFIG["success_rates"][self.base_difficulty]
            deviation = abs(success_rate - target_rate)
            
            # Check if adjustment is needed
            if deviation > DIFFICULTY_CONFIG["adjustment_threshold"]:
                adjustment = await self._calculate_player_adjustment(
                    player_id, success_rate, target_rate
                )
                
                # Apply adjustment with limits
                max_adjustment = DIFFICULTY_CONFIG["max_adjustment_per_session"]
                adjustment = max(-max_adjustment, min(max_adjustment, adjustment))
                
                old_adjustment = self.player_adjustments.get(player_id, 0.0)
                self.player_adjustments[player_id] = old_adjustment + adjustment
                
                # Set cooldown
                self.adjustment_cooldown[player_id] = datetime.utcnow()
                
                logger.info(f"Adjusted difficulty for player {player_id}: "
                           f"{adjustment:+.2f} (total: {self.player_adjustments[player_id]:+.2f})")
                
        except Exception as e:
            logger.error(f"Error checking difficulty adjustment: {e}")
    
    async def _calculate_player_adjustment(self, player_id: str, 
                                         success_rate: float, target_rate: float) -> float:
        """Calculate difficulty adjustment for a player"""
        # Basic adjustment based on success rate deviation
        rate_deviation = success_rate - target_rate
        base_adjustment = -rate_deviation * 2.0  # Negative because we adjust difficulty opposite to success
        
        # Consider other factors
        metrics = self.player_metrics.get(player_id, {})
        
        # Adjust based on engagement level
        engagement = metrics.get("engagement_level", 0.7)
        if engagement < 0.4:  # Low engagement, reduce difficulty
            base_adjustment -= 0.3
        elif engagement > 0.8:  # High engagement, can handle more challenge
            base_adjustment += 0.2
        
        # Adjust based on strategic thinking
        strategy = metrics.get("strategic_thinking", 0.5)
        if strategy > 0.7:
            base_adjustment += 0.1
        elif strategy < 0.3:
            base_adjustment -= 0.1
        
        # Adjust based on resource state
        health = metrics.get("health_percentage", 1.0)
        resources = 1.0 - metrics.get("resource_depletion", 0.5)
        resource_factor = (health + resources) / 2.0
        
        if resource_factor < 0.3:  # Low resources, reduce difficulty
            base_adjustment -= 0.2
        elif resource_factor > 0.8:  # High resources, can handle more
            base_adjustment += 0.1
        
        return base_adjustment
    
    async def _analyze_encounter_difficulty(self, encounter_record: Dict[str, Any]) -> None:
        """Analyze encounter difficulty and outcomes"""
        encounter_type = encounter_record["type"]
        outcome = encounter_record["outcome"]
        duration = encounter_record["duration"]
        
        # Track encounter success rates by type
        if encounter_type not in self.encounter_adjustments:
            self.encounter_adjustments[encounter_type] = 0.0
        
        # Analyze duration vs expected
        expected_duration = self._get_expected_encounter_duration(encounter_type)
        duration_ratio = duration / expected_duration if expected_duration > 0 else 1.0
        
        # If encounter took much longer/shorter than expected, adjust difficulty
        if duration_ratio > 2.0:  # Too long, reduce difficulty
            self.encounter_adjustments[encounter_type] -= 0.1
        elif duration_ratio < 0.5:  # Too short, increase difficulty
            self.encounter_adjustments[encounter_type] += 0.1
        
        # Analyze outcome
        if outcome == "failure" or outcome == "pyrrhic_victory":
            self.encounter_adjustments[encounter_type] -= 0.05
        elif outcome == "easy_success":
            self.encounter_adjustments[encounter_type] += 0.05
    
    async def _update_encounter_adjustments(self, encounter_type: str, 
                                          encounter_record: Dict[str, Any]) -> None:
        """Update encounter-specific difficulty adjustments"""
        # Implementation for encounter-specific learning
        # This would analyze patterns in encounter outcomes
        pass
    
    async def _calculate_global_adjustment(self) -> float:
        """Calculate global difficulty adjustment based on overall trends"""
        if not self.encounter_history:
            return 0.0
        
        recent_encounters = list(self.encounter_history)[-10:]  # Last 10 encounters
        
        # Count outcomes
        success_count = sum(1 for e in recent_encounters if e["outcome"] in ["success", "easy_success"])
        total_count = len(recent_encounters)
        
        if total_count == 0:
            return 0.0
        
        success_rate = success_count / total_count
        target_rate = 0.7  # Target 70% success rate globally
        
        # Calculate adjustment
        deviation = success_rate - target_rate
        return -deviation * 0.5  # Moderate global adjustment
    
    def _apply_difficulty_adjustment(self, base_difficulty: DifficultyLevel, 
                                   adjustment: float) -> DifficultyLevel:
        """Apply numerical adjustment to difficulty level"""
        difficulty_order = [
            DifficultyLevel.TRIVIAL,
            DifficultyLevel.EASY,
            DifficultyLevel.MODERATE,
            DifficultyLevel.HARD,
            DifficultyLevel.LEGENDARY
        ]
        
        current_index = difficulty_order.index(base_difficulty)
        
        # Convert adjustment to index change
        index_change = round(adjustment)
        new_index = max(0, min(len(difficulty_order) - 1, current_index + index_change))
        
        return difficulty_order[new_index]
    
    async def _generate_difficulty_recommendations(self, adjusted_difficulty: DifficultyLevel,
                                                 encounter_type: str,
                                                 adjustment_factors: List[Tuple[str, float]]) -> List[str]:
        """Generate specific recommendations for implementing difficulty adjustments"""
        recommendations = []
        
        total_adjustment = sum(factor[1] for factor in adjustment_factors)
        
        if total_adjustment > 0.3:  # Increase difficulty
            if encounter_type == "combat":
                recommendations.extend([
                    "Add additional enemies or increase HP",
                    "Use more tactical enemy behavior",
                    "Include environmental hazards"
                ])
            elif encounter_type == "skill_challenge":
                recommendations.extend([
                    "Increase DCs by 1-2",
                    "Add time pressure",
                    "Require more successes"
                ])
                
        elif total_adjustment < -0.3:  # Decrease difficulty
            if encounter_type == "combat":
                recommendations.extend([
                    "Reduce enemy HP or remove weak enemies",
                    "Provide environmental advantages",
                    "Have enemies make tactical mistakes"
                ])
            elif encounter_type == "skill_challenge":
                recommendations.extend([
                    "Reduce DCs by 1-2",
                    "Allow creative solutions",
                    "Provide helpful NPCs or tools"
                ])
        
        # Add factor-specific recommendations
        for factor_name, factor_value in adjustment_factors:
            if factor_name == "player_specific" and abs(factor_value) > 0.2:
                if factor_value > 0:
                    recommendations.append("Player performing well - can handle more challenge")
                else:
                    recommendations.append("Player struggling - provide support opportunities")
        
        return recommendations
    
    def _calculate_adjustment_confidence(self) -> float:
        """Calculate confidence in difficulty adjustments"""
        # Base confidence on amount of data available
        total_samples = sum(len(history) for history in self.success_history.values())
        
        if total_samples < 10:
            return 0.3
        elif total_samples < 50:
            return 0.6
        elif total_samples < 100:
            return 0.8
        else:
            return 0.9
    
    async def _calculate_success_rates_by_category(self, history: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate success rates broken down by challenge category"""
        categories = {}
        
        for record in history:
            category = record.get("type", "unknown")
            if category not in categories:
                categories[category] = {"successes": 0, "total": 0}
            
            categories[category]["total"] += 1
            if record.get("success", False):
                categories[category]["successes"] += 1
        
        return {
            category: data["successes"] / data["total"] if data["total"] > 0 else 0.0
            for category, data in categories.items()
        }
    
    def _analyze_performance_trends(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends in player performance over time"""
        if len(history) < 5:
            return {"trend": "insufficient_data"}
        
        # Split history into first and second half
        mid_point = len(history) // 2
        first_half = history[:mid_point]
        second_half = history[mid_point:]
        
        first_success_rate = sum(1 for h in first_half if h["success"]) / len(first_half)
        second_success_rate = sum(1 for h in second_half if h["success"]) / len(second_half)
        
        trend_direction = second_success_rate - first_success_rate
        
        if trend_direction > 0.1:
            trend = "improving"
        elif trend_direction < -0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        # Calculate recent margin trends
        recent_margins = [h.get("margin", 0) for h in history[-5:]]
        avg_margin = statistics.mean(recent_margins) if recent_margins else 0
        
        return {
            "trend": trend,
            "trend_magnitude": abs(trend_direction),
            "first_half_success": first_success_rate,
            "second_half_success": second_success_rate,
            "recent_avg_margin": avg_margin,
            "consistency": 1.0 - statistics.stdev([1 if h["success"] else 0 for h in history[-10:]]) if len(history) >= 10 else 0.5
        }
    
    async def _generate_performance_insights(self, player_id: str,
                                           success_rates: Dict[str, float],
                                           trends: Dict[str, Any],
                                           current_metrics: Dict[str, float]) -> List[str]:
        """Generate insights about player performance"""
        insights = []
        
        # Overall performance insight
        overall_rate = statistics.mean(success_rates.values()) if success_rates else 0.5
        if overall_rate > 0.8:
            insights.append("Player is performing exceptionally well")
        elif overall_rate > 0.6:
            insights.append("Player is performing well")
        elif overall_rate < 0.4:
            insights.append("Player is struggling with challenges")
        
        # Trend insights
        trend = trends.get("trend", "stable")
        if trend == "improving":
            insights.append("Player performance is improving over time")
        elif trend == "declining":
            insights.append("Player performance has declined recently")
        
        # Category-specific insights
        for category, rate in success_rates.items():
            if rate < 0.3:
                insights.append(f"Player struggles particularly with {category} challenges")
            elif rate > 0.9:
                insights.append(f"Player excels at {category} challenges")
        
        # Engagement insights
        engagement = current_metrics.get("engagement_level", 0.5)
        if engagement < 0.4:
            insights.append("Player engagement is low - consider personal stakes or preferred content")
        elif engagement > 0.8:
            insights.append("Player is highly engaged")
        
        return insights
    
    def _calculate_player_difficulty_recommendation(self, success_rates: Dict[str, float],
                                                  trends: Dict[str, Any],
                                                  current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """Calculate difficulty recommendation for a specific player"""
        overall_rate = statistics.mean(success_rates.values()) if success_rates else 0.5
        trend = trends.get("trend", "stable")
        engagement = current_metrics.get("engagement_level", 0.5)
        
        # Calculate recommended adjustment
        adjustment = 0.0
        
        # Based on success rate
        if overall_rate > 0.8:
            adjustment += 0.3
        elif overall_rate < 0.4:
            adjustment -= 0.3
        
        # Based on trend
        if trend == "improving":
            adjustment += 0.1
        elif trend == "declining":
            adjustment -= 0.1
        
        # Based on engagement
        if engagement < 0.4:
            adjustment -= 0.2  # Reduce difficulty if not engaged
        elif engagement > 0.8:
            adjustment += 0.1  # Can handle more if highly engaged
        
        return {
            "adjustment": adjustment,
            "reasoning": f"Based on {overall_rate:.1%} success rate, {trend} trend, "
                        f"{engagement:.1%} engagement",
            "confidence": min(1.0, len(success_rates) * 0.2)
        }
    
    async def _calculate_party_metrics(self, party_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate party-wide metrics"""
        if not party_analysis:
            return {}
        
        # Extract individual success rates
        success_rates = []
        engagement_levels = []
        
        for player_id, analysis in party_analysis.items():
            if "overall_success_rate" in analysis:
                success_rates.append(analysis["overall_success_rate"])
            if "current_metrics" in analysis and "engagement_level" in analysis["current_metrics"]:
                engagement_levels.append(analysis["current_metrics"]["engagement_level"])
        
        party_metrics = {}
        
        if success_rates:
            party_metrics["average_success_rate"] = statistics.mean(success_rates)
            party_metrics["success_rate_variance"] = statistics.variance(success_rates) if len(success_rates) > 1 else 0.0
            party_metrics["min_success_rate"] = min(success_rates)
            party_metrics["max_success_rate"] = max(success_rates)
        
        if engagement_levels:
            party_metrics["average_engagement"] = statistics.mean(engagement_levels)
            party_metrics["min_engagement"] = min(engagement_levels)
        
        return party_metrics
    
    def _analyze_encounter_trends(self) -> Dict[str, Any]:
        """Analyze trends in encounter outcomes"""
        if not self.encounter_history:
            return {"trend": "no_data"}
        
        recent_encounters = list(self.encounter_history)[-10:]
        
        # Success rate trend
        success_count = sum(1 for e in recent_encounters if e["outcome"] == "success")
        success_rate = success_count / len(recent_encounters)
        
        # Duration trends
        durations = [e["duration"] for e in recent_encounters]
        avg_duration = statistics.mean(durations) if durations else 0
        
        # Encounter type distribution
        type_counts = {}
        for encounter in recent_encounters:
            enc_type = encounter["type"]
            type_counts[enc_type] = type_counts.get(enc_type, 0) + 1
        
        return {
            "recent_success_rate": success_rate,
            "average_duration": avg_duration,
            "encounter_distribution": type_counts,
            "total_recent_encounters": len(recent_encounters)
        }
    
    async def _generate_party_recommendations(self, party_metrics: Dict[str, Any],
                                            encounter_analysis: Dict[str, Any]) -> List[str]:
        """Generate recommendations for the party"""
        recommendations = []
        
        # Success rate recommendations
        avg_success = party_metrics.get("average_success_rate", 0.6)
        if avg_success > 0.8:
            recommendations.append("Party is doing very well - consider increasing difficulty")
        elif avg_success < 0.4:
            recommendations.append("Party is struggling - consider reducing difficulty or providing support")
        
        # Engagement recommendations
        min_engagement = party_metrics.get("min_engagement", 0.5)
        if min_engagement < 0.4:
            recommendations.append("Some players have low engagement - focus on their interests")
        
        # Variance recommendations
        success_variance = party_metrics.get("success_rate_variance", 0.0)
        if success_variance > 0.1:
            recommendations.append("Large variance in player success - consider individual adjustments")
        
        # Encounter recommendations
        recent_success = encounter_analysis.get("recent_success_rate", 0.6)
        if recent_success > 0.8:
            recommendations.append("Recent encounters have been too easy")
        elif recent_success < 0.4:
            recommendations.append("Recent encounters have been too difficult")
        
        return recommendations
    
    def _convert_difficulty_to_cr_adjustment(self, difficulty_adjustment: float) -> int:
        """Convert difficulty adjustment to CR adjustment"""
        # Each difficulty level roughly corresponds to 1-2 CR levels
        return round(difficulty_adjustment * 1.5)
    
    async def _generate_encounter_modifications(self, encounter_template: Dict[str, Any],
                                              cr_adjustment: int,
                                              adjustment_info: Dict[str, Any]) -> List[str]:
        """Generate specific modifications for an encounter"""
        modifications = []
        encounter_type = encounter_template.get("type", "combat")
        
        if cr_adjustment > 0:  # Make harder
            if encounter_type == "combat":
                modifications.extend([
                    f"Increase enemy CR by {cr_adjustment}",
                    "Add environmental hazards",
                    "Use more intelligent tactics"
                ])
            else:
                modifications.extend([
                    f"Increase DCs by {cr_adjustment}",
                    "Add time pressure",
                    "Require more successes"
                ])
                
        elif cr_adjustment < 0:  # Make easier
            if encounter_type == "combat":
                modifications.extend([
                    f"Reduce enemy CR by {abs(cr_adjustment)}",
                    "Provide environmental advantages",
                    "Reduce enemy numbers"
                ])
            else:
                modifications.extend([
                    f"Reduce DCs by {abs(cr_adjustment)}",
                    "Provide helpful hints",
                    "Allow alternative solutions"
                ])
        
        return modifications
    
    def _get_expected_encounter_duration(self, encounter_type: str) -> int:
        """Get expected duration for encounter type in minutes"""
        durations = {
            "combat": 30,
            "social": 20,
            "exploration": 25,
            "puzzle": 15,
            "skill_challenge": 10
        }
        return durations.get(encounter_type, 20)