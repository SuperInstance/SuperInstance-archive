# SUPERINSTANCE LEGO COMPONENT: Macro Analysis AI
# EXTRACTED FROM: services/nutrition-tracking/main.py:635-1071
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import asyncio
import requests

class MacroAnalysisAILego:
    """
    🧩 LEGO COMPONENT: Macro Analysis AI
    
    DATA: Nutrition patterns, meal timing, macro ratios, performance correlations
    TOOLS: Pattern recognition, timing optimization, AI recommendations, vector analysis
    CONFIGURATION: AI models, analysis depth, recommendation focus
    
    INTERFACES:
    - Input: User nutrition data, time period, analysis preferences
    - Output: Pattern insights, timing recommendations, personalized suggestions
    - Integration: Nutrition APIs, workout services, user preferences
    
    DEPLOYMENT OPTIONS:
    - Device: Local analysis for privacy-focused users
    - Edge: Regional pattern recognition with shared insights
    - Cloud: Advanced AI with global pattern recognition
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.analysis_mode = config.get("analysis_mode", "comprehensive")
        self.ai_endpoint = config.get("ai_endpoint", None)
        self.recommendation_focus = config.get("focus", "performance_optimization")
        self.privacy_mode = config.get("privacy_mode", False)
    
    async def analyze_nutrition_patterns(self, nutrition_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Core pattern analysis - identifies eating habits and consistency
        
        Args:
            nutrition_data: Raw nutrition data from nutrition API Lego
            
        Returns:
            Comprehensive pattern analysis with actionable insights
        """
        if not nutrition_data or nutrition_data.get("status") == "insufficient_data":
            return self._generate_baseline_analysis()
        
        data = nutrition_data.get("data", [])
        if not data:
            return {"status": "insufficient_data"}
        
        # Multi-dimensional pattern analysis
        meal_frequency = await self._analyze_meal_frequency(data)
        macro_consistency = await self._analyze_macro_consistency(data)
        eating_window = await self._analyze_eating_window(data)
        behavioral_patterns = await self._identify_behavioral_patterns(data)
        
        return {
            "meal_frequency": meal_frequency,
            "macro_consistency": macro_consistency,
            "eating_window": eating_window,
            "behavioral_patterns": behavioral_patterns,
            "analysis_confidence": self._calculate_confidence_score(data),
            "total_days_analyzed": len(set(entry["consumed_at"].date() for entry in data)),
            "total_entries": len(data),
            "generated_at": datetime.utcnow().isoformat()
        }
    
    async def _analyze_meal_frequency(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze meal frequency patterns and regularity"""
        meal_counts = {}
        daily_patterns = {}
        
        # Group by date and meal type
        for entry in data:
            date_str = entry["consumed_at"].date().isoformat()
            meal_type = entry["meal_type"]
            
            if date_str not in daily_patterns:
                daily_patterns[date_str] = set()
            daily_patterns[date_str].add(meal_type)
            
            meal_counts[meal_type] = meal_counts.get(meal_type, 0) + 1
        
        total_days = max(1, len(daily_patterns))
        
        # Calculate frequency scores
        meal_frequency = {}
        for meal_type, count in meal_counts.items():
            frequency = count / total_days
            meal_frequency[meal_type] = {
                "frequency": round(frequency, 2),
                "consistency": "high" if frequency > 0.8 else "medium" if frequency > 0.5 else "low",
                "total_occurrences": count
            }
        
        # Analyze meal timing consistency
        regularity_score = self._calculate_meal_regularity(daily_patterns)
        
        return {
            "meal_frequency": meal_frequency,
            "average_meals_per_day": round(sum(len(meals) for meals in daily_patterns.values()) / total_days, 1),
            "regularity_score": regularity_score,
            "most_consistent_meal": max(meal_frequency.keys(), key=lambda x: meal_frequency[x]["frequency"]) if meal_frequency else None,
            "patterns_identified": self._identify_frequency_patterns(meal_frequency)
        }
    
    async def _analyze_macro_consistency(self, data: List[Dict]) -> Dict[str, Any]:
        """Advanced macro consistency analysis with variance scoring"""
        daily_macros = {}
        
        # Aggregate daily macro totals
        for entry in data:
            date_str = entry["consumed_at"].date().isoformat()
            if date_str not in daily_macros:
                daily_macros[date_str] = {"calories": 0, "protein": 0, "carbs": 0, "fat": 0}
            
            nutrition = entry["nutrition"]
            for macro in daily_macros[date_str]:
                daily_macros[date_str][macro] += nutrition.get(macro, 0)
        
        if len(daily_macros) < 2:
            return {"status": "insufficient_data", "days_analyzed": len(daily_macros)}
        
        # Calculate consistency scores using coefficient of variation
        consistency_scores = {}
        macro_stats = {}
        
        for macro in ["calories", "protein", "carbs", "fat"]:
            values = [day[macro] for day in daily_macros.values() if day[macro] > 0]
            if len(values) > 1:
                mean_val = np.mean(values)
                std_val = np.std(values)
                cv = std_val / mean_val if mean_val > 0 else 1.0  # Coefficient of variation
                
                # Consistency score (lower CV = higher consistency)
                consistency = max(0, 1 - cv)
                consistency_scores[macro] = round(consistency, 3)
                
                macro_stats[macro] = {
                    "mean": round(mean_val, 1),
                    "std": round(std_val, 1),
                    "coefficient_of_variation": round(cv, 3),
                    "min": round(min(values), 1),
                    "max": round(max(values), 1)
                }
            else:
                consistency_scores[macro] = 0.5
                macro_stats[macro] = {"status": "insufficient_data"}
        
        overall_consistency = np.mean(list(consistency_scores.values()))
        
        return {
            "consistency_scores": consistency_scores,
            "overall_consistency": round(overall_consistency, 3),
            "consistency_rating": self._rate_consistency(overall_consistency),
            "macro_statistics": macro_stats,
            "days_analyzed": len(daily_macros),
            "recommendations": self._generate_consistency_recommendations(consistency_scores)
        }
    
    async def _analyze_eating_window(self, data: List[Dict]) -> Dict[str, Any]:
        """Analyze eating window patterns and circadian alignment"""
        meal_times = []
        daily_windows = {}
        
        # Extract meal timing data
        for entry in data:
            if entry["timing"]["hour"] is not None:
                hour = entry["timing"]["hour"]
                date_str = entry["consumed_at"].date().isoformat()
                
                meal_times.append(hour)
                
                if date_str not in daily_windows:
                    daily_windows[date_str] = {"earliest": hour, "latest": hour}
                else:
                    daily_windows[date_str]["earliest"] = min(daily_windows[date_str]["earliest"], hour)
                    daily_windows[date_str]["latest"] = max(daily_windows[date_str]["latest"], hour)
        
        if not meal_times:
            return {"status": "insufficient_timing_data"}
        
        # Calculate eating window statistics
        avg_earliest = np.mean([day["earliest"] for day in daily_windows.values()])
        avg_latest = np.mean([day["latest"] for day in daily_windows.values()])
        avg_duration = avg_latest - avg_earliest
        
        # Analyze window consistency
        durations = [day["latest"] - day["earliest"] for day in daily_windows.values()]
        duration_consistency = 1 - (np.std(durations) / np.mean(durations)) if np.mean(durations) > 0 else 0
        
        return {
            "average_eating_window": {
                "start": f"{int(avg_earliest):02d}:{int((avg_earliest % 1) * 60):02d}",
                "end": f"{int(avg_latest):02d}:{int((avg_latest % 1) * 60):02d}",
                "duration_hours": round(avg_duration, 1)
            },
            "window_consistency": round(max(0, duration_consistency), 3),
            "circadian_alignment": self._assess_circadian_alignment(avg_earliest, avg_latest),
            "meal_distribution": self._analyze_meal_distribution(meal_times),
            "optimization_opportunities": self._identify_timing_optimizations(avg_earliest, avg_latest, avg_duration)
        }
    
    async def _identify_behavioral_patterns(self, data: List[Dict]) -> Dict[str, Any]:
        """Identify deeper behavioral eating patterns using AI"""
        patterns = {}
        
        # Day-of-week patterns
        dow_patterns = {}
        for entry in data:
            dow = entry["timing"]["day_of_week"]  # 0=Sunday, 6=Saturday
            if dow not in dow_patterns:
                dow_patterns[dow] = {"meal_count": 0, "total_calories": 0}
            
            dow_patterns[dow]["meal_count"] += 1
            dow_patterns[dow]["total_calories"] += entry["nutrition"].get("calories", 0)
        
        # Convert to interpretable format
        day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        weekly_patterns = {}
        for dow, stats in dow_patterns.items():
            if 0 <= dow <= 6:
                weekly_patterns[day_names[dow]] = {
                    "avg_meals": round(stats["meal_count"] / max(1, len(set(entry["consumed_at"].date() for entry in data if entry["timing"]["day_of_week"] == dow))), 1),
                    "avg_calories": round(stats["total_calories"] / max(1, stats["meal_count"]), 1) if stats["meal_count"] > 0 else 0
                }
        
        # Food variety analysis
        unique_foods = set(entry["food_item"] for entry in data)
        food_frequency = {}
        for entry in data:
            food = entry["food_item"]
            food_frequency[food] = food_frequency.get(food, 0) + 1
        
        # Calculate variety metrics
        total_entries = len(data)
        variety_score = len(unique_foods) / total_entries if total_entries > 0 else 0
        
        return {
            "weekly_patterns": weekly_patterns,
            "food_variety": {
                "unique_foods": len(unique_foods),
                "variety_score": round(variety_score, 3),
                "most_frequent_foods": sorted(food_frequency.items(), key=lambda x: x[1], reverse=True)[:5]
            },
            "behavioral_insights": self._generate_behavioral_insights(weekly_patterns, variety_score)
        }
    
    async def generate_timing_recommendations(self, nutrition_data: Dict[str, Any]) -> List[Dict]:
        """Generate meal timing optimization recommendations"""
        if not nutrition_data or nutrition_data.get("status") == "insufficient_data":
            return self._generate_baseline_timing_recommendations()
        
        data = nutrition_data.get("data", [])
        recommendations = []
        
        # Analyze current timing patterns
        meal_hours = {}
        for entry in data:
            meal_type = entry["meal_type"]
            hour = entry["timing"]["hour"]
            if hour is not None:
                if meal_type not in meal_hours:
                    meal_hours[meal_type] = []
                meal_hours[meal_type].append(hour)
        
        # Generate specific timing recommendations
        for meal_type, hours in meal_hours.items():
            avg_hour = np.mean(hours)
            
            if meal_type == "breakfast" and avg_hour > 9:
                recommendations.append({
                    "meal_type": meal_type,
                    "insight": "Late breakfast pattern detected",
                    "recommendation": "Consider eating breakfast earlier (7-8 AM) to optimize metabolism and energy levels",
                    "impact": "medium",
                    "current_avg_time": f"{int(avg_hour):02d}:{int((avg_hour % 1) * 60):02d}",
                    "optimal_time": "07:30-08:30"
                })
            
            elif meal_type == "dinner" and avg_hour > 20:
                recommendations.append({
                    "meal_type": meal_type,
                    "insight": "Late dinner pattern detected", 
                    "recommendation": "Earlier dinners (6-7 PM) may improve sleep quality and recovery",
                    "impact": "high",
                    "current_avg_time": f"{int(avg_hour):02d}:{int((avg_hour % 1) * 60):02d}",
                    "optimal_time": "18:00-19:00"
                })
        
        # Pre/post workout timing (if workout integration available)
        if self.config.get("workout_integration"):
            workout_recommendations = await self._generate_workout_timing_recommendations(data)
            recommendations.extend(workout_recommendations)
        
        return recommendations[:8]  # Limit to top recommendations
    
    async def generate_personalized_recommendations(
        self, 
        user_id: str, 
        pattern_analysis: Dict, 
        macro_insights: Dict,
        user_goals: Optional[Dict] = None
    ) -> List[Dict]:
        """Generate AI-powered personalized nutrition recommendations"""
        
        recommendations = []
        
        # Pattern-based recommendations
        meal_frequency = pattern_analysis.get("meal_frequency", {})
        if meal_frequency.get("breakfast", {}).get("frequency", 0) < 0.7:
            recommendations.append({
                "type": "habit",
                "priority": "high",
                "category": "meal_timing",
                "action": "establish_breakfast_routine",
                "title": "Establish Regular Breakfast",
                "description": "Regular breakfast improves energy stability and metabolic health",
                "specific_actions": [
                    "Set a consistent wake-up time",
                    "Prepare breakfast ingredients the night before",
                    "Start with simple options like overnight oats or protein smoothies"
                ],
                "expected_impact": "Improved morning energy and metabolism"
            })
        
        # Macro balance recommendations
        consistency_scores = macro_insights.get("consistency_scores", {})
        if consistency_scores.get("protein", 0) < 0.6:
            recommendations.append({
                "type": "nutrition",
                "priority": "medium",
                "category": "macro_balance",
                "action": "improve_protein_consistency",
                "title": "Stabilize Protein Intake",
                "description": "More consistent protein intake supports muscle maintenance and satiety",
                "specific_actions": [
                    "Include protein source in every meal",
                    "Plan protein portions ahead of time",
                    "Consider protein supplements for busy days"
                ],
                "target_consistency": 0.8
            })
        
        # AI-enhanced recommendations (if AI endpoint available)
        if self.ai_endpoint and not self.privacy_mode:
            ai_recommendations = await self._get_ai_recommendations(
                user_id, pattern_analysis, macro_insights, user_goals
            )
            recommendations.extend(ai_recommendations)
        
        return recommendations[:10]  # Limit to top recommendations
    
    async def correlate_with_performance(
        self, 
        nutrition_data: Dict, 
        performance_data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """Analyze nutrition-performance correlations"""
        if not performance_data:
            return None
        
        try:
            # Cross-domain pattern analysis
            correlation_insights = {
                "pre_workout_nutrition": await self._analyze_pre_workout_patterns(nutrition_data, performance_data),
                "post_workout_recovery": await self._analyze_recovery_patterns(nutrition_data, performance_data),
                "energy_correlation": await self._analyze_energy_correlations(nutrition_data, performance_data),
                "macro_performance_relationship": await self._analyze_macro_performance(nutrition_data, performance_data)
            }
            
            return {
                "correlation_analysis": correlation_insights,
                "performance_nutrition_score": self._calculate_performance_nutrition_score(correlation_insights),
                "optimization_opportunities": self._identify_performance_optimizations(correlation_insights)
            }
            
        except Exception as e:
            print(f"Performance correlation error: {e}")
            return None
    
    # UTILITY FUNCTIONS
    def _generate_baseline_analysis(self) -> Dict[str, Any]:
        """Generate baseline analysis for new users"""
        return {
            "status": "building_profile",
            "message": "Continue logging meals to build your nutrition profile",
            "recommended_actions": [
                "Log all meals consistently for 7 days",
                "Include portion sizes and timing information",
                "Track both weekday and weekend patterns"
            ]
        }
    
    def _calculate_confidence_score(self, data: List[Dict]) -> float:
        """Calculate analysis confidence based on data quality and quantity"""
        if not data:
            return 0.0
        
        # Factors affecting confidence
        days_with_data = len(set(entry["consumed_at"].date() for entry in data))
        entries_per_day = len(data) / max(1, days_with_data)
        completeness_score = min(1.0, entries_per_day / 3.0)  # 3 meals = full day
        
        # Time span factor
        time_span_days = max(1, days_with_data)
        time_span_score = min(1.0, time_span_days / 7.0)  # 7 days = good span
        
        # Data completeness
        complete_entries = sum(1 for entry in data if all(entry["nutrition"].get(macro, 0) > 0 for macro in ["calories", "protein", "carbs", "fat"]))
        completeness_ratio = complete_entries / len(data) if data else 0
        
        confidence = (completeness_score + time_span_score + completeness_ratio) / 3
        return round(confidence, 3)
    
    def _rate_consistency(self, score: float) -> str:
        """Convert consistency score to readable rating"""
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "moderate"
        else:
            return "needs_improvement"

# LEGO CONFIGURATION OPTIONS
DEPLOYMENT_CONFIGS = {
    "device_private": {
        "analysis_mode": "basic",
        "privacy_mode": True,
        "ai_endpoint": None,
        "features": ["local_analysis", "privacy_focused"]
    },
    "edge_enhanced": {
        "analysis_mode": "comprehensive", 
        "privacy_mode": False,
        "ai_endpoint": "http://localhost:8090/nutrition/ai-analyze",
        "features": ["advanced_patterns", "regional_insights", "workout_integration"]
    },
    "cloud_ai_powered": {
        "analysis_mode": "comprehensive",
        "privacy_mode": False,
        "ai_endpoint": "https://ai-service/nutrition/analyze",
        "features": ["ml_recommendations", "global_patterns", "predictive_analytics"]
    }
}

# USAGE EXAMPLES
def create_macro_analysis_lego(deployment_type: str = "edge_enhanced"):
    """Factory function to create configured Macro Analysis AI Lego"""
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_enhanced"])
    return MacroAnalysisAILego(config)

# INTEGRATION INTERFACES
def integrate_with_workout_tracking(macro_ai: MacroAnalysisAILego, workout_service_url: str):
    """Connect to workout tracking for performance correlations"""
    macro_ai.config["workout_integration"] = True
    macro_ai.config["workout_service_url"] = workout_service_url

def integrate_with_ai_insights(macro_ai: MacroAnalysisAILego, ai_service_url: str):
    """Connect to advanced AI service for enhanced recommendations"""
    macro_ai.config["ai_endpoint"] = ai_service_url
    macro_ai.ai_endpoint = ai_service_url