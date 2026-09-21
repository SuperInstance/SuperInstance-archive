#!/usr/bin/env python3
"""
ML-Driven Video Intelligence System
Advanced video analysis, quality optimization, and intelligent decision-making
"""

import asyncio
import logging
import json
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import cv2
import sqlite3
from pathlib import Path
import tempfile

logger = logging.getLogger(__name__)


class VideoIntelligenceEngine:
    """Advanced ML-driven video analysis and optimization"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
        # Analysis models
        self.content_analyzer = ContentAnalyzer()
        self.quality_assessor = QualityAssessor()
        self.engagement_predictor = EngagementPredictor()
        self.style_optimizer = StyleOptimizer()
        self.cost_optimizer = CostOptimizer()
        
        # Learning systems
        self.user_preference_learner = UserPreferenceLearner(db_path)
        self.performance_optimizer = PerformanceOptimizer()
        
        # Caching for performance
        self.analysis_cache = {}
        self.model_performance_cache = {}
    
    async def analyze_video(self, video_path: str, analysis_types: List[str]) -> Dict:
        """Comprehensive video analysis"""
        
        analysis_id = f"analysis_{int(asyncio.get_event_loop().time())}"
        
        try:
            results = {
                "analysis_id": analysis_id,
                "video_path": video_path,
                "timestamp": datetime.now().isoformat(),
                "analyses": {}
            }
            
            # Load video for analysis
            video_info = await self._get_video_info(video_path)
            results["video_info"] = video_info
            
            # Perform requested analyses
            if "content" in analysis_types:
                results["analyses"]["content"] = await self.content_analyzer.analyze(video_path)
            
            if "quality" in analysis_types:
                results["analyses"]["quality"] = await self.quality_assessor.analyze(video_path)
            
            if "engagement" in analysis_types:
                results["analyses"]["engagement"] = await self.engagement_predictor.analyze(video_path)
            
            if "style" in analysis_types:
                results["analyses"]["style"] = await self._analyze_style(video_path)
            
            if "performance" in analysis_types:
                results["analyses"]["performance"] = await self._analyze_performance_metrics(video_path)
            
            # Generate overall insights
            results["insights"] = await self._generate_insights(results["analyses"])
            results["recommendations"] = await self._generate_recommendations(results["analyses"])
            
            # Store analysis results
            await self._store_analysis(analysis_id, results)
            
            return results
            
        except Exception as e:
            logger.error(f"Video analysis failed: {e}")
            return {
                "analysis_id": analysis_id,
                "success": False,
                "error": str(e)
            }
    
    async def predict_optimal_generation_params(self, request_params: Dict, 
                                              user_history: Optional[Dict] = None) -> Dict:
        """Predict optimal parameters for video generation"""
        
        try:
            # Analyze user preferences if available
            user_preferences = {}
            if user_history and request_params.get("user_id"):
                user_preferences = await self.user_preference_learner.get_user_preferences(
                    request_params["user_id"]
                )
            
            # Get performance data for different models
            model_performance = await self._get_model_performance_data()
            
            # Cost-quality optimization
            cost_quality_analysis = await self.cost_optimizer.optimize(
                request_params, user_preferences, model_performance
            )
            
            # Style optimization
            style_recommendations = await self.style_optimizer.optimize(
                request_params["prompt"], 
                request_params.get("style"),
                user_preferences.get("style_preferences", {})
            )
            
            # Generate optimal parameters
            optimized_params = {
                "recommended_model": cost_quality_analysis["optimal_model"],
                "recommended_quality": cost_quality_analysis["optimal_quality"],
                "recommended_resolution": style_recommendations["optimal_resolution"],
                "recommended_duration": self._optimize_duration(request_params, user_preferences),
                "recommended_effects": style_recommendations["recommended_effects"],
                "cost_savings": cost_quality_analysis["potential_savings"],
                "quality_improvement": cost_quality_analysis["quality_boost"],
                "confidence_score": self._calculate_optimization_confidence(
                    cost_quality_analysis, style_recommendations, user_preferences
                )
            }
            
            # Add reasoning
            optimized_params["optimization_reasoning"] = {
                "cost_factors": cost_quality_analysis["reasoning"],
                "style_factors": style_recommendations["reasoning"],
                "user_factors": user_preferences.get("preference_reasons", [])
            }
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Parameter optimization failed: {e}")
            return {"error": str(e)}
    
    async def learn_from_generation(self, generation_data: Dict, user_feedback: Optional[Dict] = None):
        """Learn from video generation results and user feedback"""
        
        try:
            # Update user preferences
            if user_feedback and generation_data.get("user_id"):
                await self.user_preference_learner.update_preferences(
                    generation_data["user_id"],
                    generation_data,
                    user_feedback
                )
            
            # Update model performance tracking
            await self.performance_optimizer.update_model_performance(generation_data)
            
            # Update cost-quality relationships
            await self.cost_optimizer.update_cost_quality_data(generation_data)
            
            # Clear relevant caches
            self._clear_relevant_caches(generation_data.get("user_id"))
            
            logger.debug(f"Learned from generation {generation_data.get('generation_id')}")
            
        except Exception as e:
            logger.error(f"Learning from generation failed: {e}")
    
    async def get_quality_score_prediction(self, generation_params: Dict) -> float:
        """Predict quality score for given generation parameters"""
        
        try:
            # Base quality from model
            model_base_quality = {
                "runway-ml": 8.5,
                "stable-video": 7.0,
                "luma-ai": 7.8
            }
            
            model = generation_params.get("model_used", "runway-ml")
            base_score = model_base_quality.get(model, 7.0)
            
            # Adjust for parameters
            adjustments = 0.0
            
            # Quality setting impact
            quality_impact = {
                "draft": -1.5,
                "standard": 0.0,
                "high": 0.8,
                "professional": 1.2
            }
            adjustments += quality_impact.get(generation_params.get("quality", "standard"), 0.0)
            
            # Resolution impact
            resolution = generation_params.get("resolution", "1280x720")
            if "1080" in resolution:
                adjustments += 0.5
            elif "2160" in resolution or "4K" in resolution:
                adjustments += 1.0
            
            # Duration impact (sweet spot optimization)
            duration = generation_params.get("duration", 5)
            if 3 <= duration <= 10:
                adjustments += 0.3
            elif duration > 20:
                adjustments -= 0.5
            
            # Prompt quality impact
            prompt = generation_params.get("prompt", "")
            if len(prompt) > 100:
                adjustments += 0.2
            if len(prompt) > 200:
                adjustments += 0.2
            
            # Style clarity impact
            if generation_params.get("style"):
                adjustments += 0.3
            
            final_score = base_score + adjustments
            return min(max(final_score, 1.0), 10.0)
            
        except Exception as e:
            logger.error(f"Quality prediction failed: {e}")
            return 7.0  # Default score
    
    async def _get_video_info(self, video_path: str) -> Dict:
        """Extract basic video information"""
        
        try:
            cap = cv2.VideoCapture(video_path)
            
            if not cap.isOpened():
                raise ValueError("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = frame_count / fps if fps > 0 else 0
            
            cap.release()
            
            # File size
            file_size = Path(video_path).stat().st_size
            
            return {
                "width": width,
                "height": height,
                "fps": fps,
                "frame_count": frame_count,
                "duration": duration,
                "file_size": file_size,
                "resolution": f"{width}x{height}",
                "aspect_ratio": round(width / height, 2) if height > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return {}
    
    async def _analyze_style(self, video_path: str) -> Dict:
        """Analyze video style characteristics"""
        
        try:
            # Extract frames for analysis
            frames = await self._extract_sample_frames(video_path, num_frames=10)
            
            style_analysis = {
                "color_palette": self._analyze_color_palette(frames),
                "motion_characteristics": self._analyze_motion_characteristics(video_path),
                "lighting_analysis": self._analyze_lighting(frames),
                "composition_analysis": self._analyze_composition(frames),
                "visual_complexity": self._calculate_visual_complexity(frames)
            }
            
            # Determine style category
            style_analysis["detected_style"] = self._classify_style(style_analysis)
            style_analysis["style_confidence"] = self._calculate_style_confidence(style_analysis)
            
            return style_analysis
            
        except Exception as e:
            logger.error(f"Style analysis failed: {e}")
            return {"error": str(e)}
    
    async def _analyze_performance_metrics(self, video_path: str) -> Dict:
        """Analyze video performance characteristics"""
        
        try:
            video_info = await self._get_video_info(video_path)
            
            # Calculate various performance metrics
            metrics = {
                "compression_efficiency": self._calculate_compression_efficiency(video_info),
                "bitrate_optimization": self._analyze_bitrate_efficiency(video_path),
                "visual_quality_score": await self.quality_assessor.get_visual_quality_score(video_path),
                "loading_performance": self._estimate_loading_performance(video_info),
                "compatibility_score": self._assess_compatibility(video_info),
                "streaming_optimization": self._analyze_streaming_readiness(video_info)
            }
            
            # Overall performance score
            metrics["overall_performance"] = self._calculate_overall_performance(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {"error": str(e)}
    
    async def _generate_insights(self, analyses: Dict) -> List[str]:
        """Generate insights from analysis results"""
        
        insights = []
        
        try:
            # Quality insights
            if "quality" in analyses:
                quality_data = analyses["quality"]
                if quality_data.get("overall_score", 0) > 8.0:
                    insights.append("Video demonstrates excellent visual quality")
                elif quality_data.get("overall_score", 0) < 6.0:
                    insights.append("Video quality could be improved with optimization")
            
            # Content insights
            if "content" in analyses:
                content_data = analyses["content"]
                if content_data.get("scene_variety", 0) > 0.8:
                    insights.append("Video has excellent scene variety and pacing")
                if content_data.get("motion_intensity", 0) > 0.7:
                    insights.append("High motion content - good for engagement")
            
            # Style insights
            if "style" in analyses:
                style_data = analyses["style"]
                detected_style = style_data.get("detected_style", "unknown")
                confidence = style_data.get("style_confidence", 0)
                if confidence > 0.8:
                    insights.append(f"Strong {detected_style} style characteristics detected")
            
            # Engagement insights
            if "engagement" in analyses:
                engagement_data = analyses["engagement"]
                predicted_engagement = engagement_data.get("predicted_score", 0)
                if predicted_engagement > 8.0:
                    insights.append("High engagement potential predicted")
                elif predicted_engagement < 5.0:
                    insights.append("Consider optimizations to improve engagement")
            
            if not insights:
                insights.append("Video analysis completed successfully")
            
            return insights
            
        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            return ["Analysis completed with limited insights"]
    
    async def _generate_recommendations(self, analyses: Dict) -> List[Dict]:
        """Generate actionable recommendations"""
        
        recommendations = []
        
        try:
            # Quality recommendations
            if "quality" in analyses:
                quality_data = analyses["quality"]
                if quality_data.get("sharpness_score", 0) < 0.7:
                    recommendations.append({
                        "type": "quality_improvement",
                        "action": "apply_sharpening",
                        "reason": "Video could benefit from sharpening enhancement",
                        "impact": "medium"
                    })
                
                if quality_data.get("color_accuracy", 0) < 0.8:
                    recommendations.append({
                        "type": "color_correction",
                        "action": "color_grading",
                        "reason": "Color accuracy could be improved",
                        "impact": "high"
                    })
            
            # Style recommendations
            if "style" in analyses:
                style_data = analyses["style"]
                if style_data.get("visual_complexity", 0) > 0.9:
                    recommendations.append({
                        "type": "simplification",
                        "action": "reduce_visual_complexity",
                        "reason": "High visual complexity may reduce clarity",
                        "impact": "medium"
                    })
            
            # Performance recommendations
            if "performance" in analyses:
                perf_data = analyses["performance"]
                if perf_data.get("compression_efficiency", 0) < 0.7:
                    recommendations.append({
                        "type": "optimization",
                        "action": "recompress_video",
                        "reason": "Video can be compressed more efficiently",
                        "impact": "high"
                    })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Recommendation generation failed: {e}")
            return []
    
    def _optimize_duration(self, request_params: Dict, user_preferences: Dict) -> int:
        """Optimize video duration based on content and preferences"""
        
        requested_duration = request_params.get("duration", 5)
        
        # User preference factor
        preferred_duration = user_preferences.get("avg_duration", requested_duration)
        
        # Content type factor
        style = request_params.get("style", "cinematic")
        style_duration_preferences = {
            "social_media": 3,
            "commercial": 15,
            "educational": 30,
            "cinematic": 10,
            "documentary": 60
        }
        
        optimal_duration = style_duration_preferences.get(style, requested_duration)
        
        # Blend preferences
        final_duration = int((requested_duration + preferred_duration + optimal_duration) / 3)
        
        # Ensure reasonable bounds
        return max(1, min(final_duration, 120))
    
    def _calculate_optimization_confidence(self, cost_analysis: Dict, 
                                         style_analysis: Dict, user_prefs: Dict) -> float:
        """Calculate confidence in optimization recommendations"""
        
        confidence_factors = []
        
        # Cost analysis confidence
        if cost_analysis.get("data_points", 0) > 10:
            confidence_factors.append(0.9)
        else:
            confidence_factors.append(0.6)
        
        # Style analysis confidence
        style_confidence = style_analysis.get("confidence", 0.5)
        confidence_factors.append(style_confidence)
        
        # User preference confidence
        usage_count = user_prefs.get("total_generations", 0)
        if usage_count > 10:
            confidence_factors.append(0.9)
        elif usage_count > 3:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
        
        return sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5
    
    async def _get_model_performance_data(self) -> Dict:
        """Get cached model performance data"""
        
        if "model_performance" in self.model_performance_cache:
            return self.model_performance_cache["model_performance"]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT model_name, style, avg_quality_score, avg_generation_time,
                       success_rate, avg_cost, usage_count
                FROM model_performance
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            performance_data = {}
            for result in results:
                model, style, quality, time, success, cost, usage = result
                if model not in performance_data:
                    performance_data[model] = {}
                
                performance_data[model][style] = {
                    "avg_quality": quality,
                    "avg_time": time,
                    "success_rate": success,
                    "avg_cost": cost,
                    "usage_count": usage
                }
            
            self.model_performance_cache["model_performance"] = performance_data
            return performance_data
            
        except Exception as e:
            logger.error(f"Failed to get model performance data: {e}")
            return {}
    
    async def _store_analysis(self, analysis_id: str, results: Dict):
        """Store analysis results in database"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store main analysis record
            cursor.execute('''
                INSERT INTO video_analysis 
                (id, video_id, analysis_type, content_tags, quality_metrics,
                 engagement_predictions, key_frames, summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis_id,
                results.get("video_path", ""),
                ",".join(results.get("analyses", {}).keys()),
                json.dumps(results.get("analyses", {}).get("content", {})),
                json.dumps(results.get("analyses", {}).get("quality", {})),
                json.dumps(results.get("analyses", {}).get("engagement", {})),
                json.dumps([]),  # key_frames placeholder
                json.dumps(results.get("insights", []))
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {e}")
    
    def _clear_relevant_caches(self, user_id: Optional[str] = None):
        """Clear relevant caches when data changes"""
        
        # Clear analysis cache
        self.analysis_cache.clear()
        
        # Clear model performance cache
        if "model_performance" in self.model_performance_cache:
            del self.model_performance_cache["model_performance"]


class ContentAnalyzer:
    """Advanced video content analysis"""
    
    async def analyze(self, video_path: str) -> Dict:
        """Analyze video content"""
        
        try:
            # Placeholder for comprehensive content analysis
            # In real implementation, would use computer vision models
            
            analysis = {
                "scene_count": await self._detect_scenes(video_path),
                "object_detection": await self._detect_objects(video_path),
                "motion_analysis": await self._analyze_motion(video_path),
                "color_analysis": await self._analyze_colors(video_path),
                "text_detection": await self._detect_text(video_path),
                "face_detection": await self._detect_faces(video_path),
                "scene_variety": 0.8,  # Placeholder
                "motion_intensity": 0.6,  # Placeholder
                "visual_complexity": 0.7  # Placeholder
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Content analysis failed: {e}")
            return {"error": str(e)}
    
    async def _detect_scenes(self, video_path: str) -> int:
        """Detect scene changes in video"""
        # Placeholder - would use scene detection algorithms
        return 3
    
    async def _detect_objects(self, video_path: str) -> List[str]:
        """Detect objects in video"""
        # Placeholder - would use object detection models
        return ["person", "car", "building"]
    
    async def _analyze_motion(self, video_path: str) -> Dict:
        """Analyze motion characteristics"""
        # Placeholder - would use optical flow analysis
        return {"average_motion": 0.6, "motion_vectors": []}
    
    async def _analyze_colors(self, video_path: str) -> Dict:
        """Analyze color characteristics"""
        # Placeholder - would use color histogram analysis
        return {"dominant_colors": ["blue", "green"], "color_diversity": 0.7}
    
    async def _detect_text(self, video_path: str) -> List[str]:
        """Detect text in video"""
        # Placeholder - would use OCR
        return ["Sample Text"]
    
    async def _detect_faces(self, video_path: str) -> int:
        """Detect faces in video"""
        # Placeholder - would use face detection
        return 1


class QualityAssessor:
    """Video quality assessment system"""
    
    async def analyze(self, video_path: str) -> Dict:
        """Analyze video quality"""
        
        try:
            quality_metrics = {
                "overall_score": await self.get_visual_quality_score(video_path),
                "sharpness_score": await self._assess_sharpness(video_path),
                "color_accuracy": await self._assess_color_accuracy(video_path),
                "noise_level": await self._assess_noise_level(video_path),
                "compression_artifacts": await self._detect_compression_artifacts(video_path),
                "stability_score": await self._assess_stability(video_path),
                "exposure_quality": await self._assess_exposure(video_path),
                "focus_quality": await self._assess_focus(video_path)
            }
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Quality assessment failed: {e}")
            return {"error": str(e)}
    
    async def get_visual_quality_score(self, video_path: str) -> float:
        """Get overall visual quality score"""
        # Placeholder - would use quality assessment models
        return 8.2
    
    async def _assess_sharpness(self, video_path: str) -> float:
        """Assess video sharpness"""
        # Placeholder - would use Laplacian variance or similar
        return 0.8
    
    async def _assess_color_accuracy(self, video_path: str) -> float:
        """Assess color accuracy"""
        # Placeholder - would analyze color distribution
        return 0.85
    
    async def _assess_noise_level(self, video_path: str) -> float:
        """Assess noise level (lower is better)"""
        # Placeholder - would analyze noise characteristics
        return 0.15
    
    async def _detect_compression_artifacts(self, video_path: str) -> float:
        """Detect compression artifacts (lower is better)"""
        # Placeholder - would detect blocking, ringing, etc.
        return 0.1
    
    async def _assess_stability(self, video_path: str) -> float:
        """Assess video stability"""
        # Placeholder - would analyze camera shake
        return 0.9
    
    async def _assess_exposure(self, video_path: str) -> float:
        """Assess exposure quality"""
        # Placeholder - would analyze histogram
        return 0.85
    
    async def _assess_focus(self, video_path: str) -> float:
        """Assess focus quality"""
        # Placeholder - would analyze edge definition
        return 0.9


class EngagementPredictor:
    """Predict video engagement potential"""
    
    async def analyze(self, video_path: str) -> Dict:
        """Predict engagement metrics"""
        
        try:
            # Placeholder for engagement prediction
            # Would use ML models trained on engagement data
            
            predictions = {
                "predicted_score": 7.5,  # 1-10 scale
                "engagement_factors": {
                    "visual_appeal": 8.0,
                    "pacing": 7.0,
                    "content_variety": 8.5,
                    "emotional_impact": 6.5
                },
                "target_audience": "general",
                "optimal_platforms": ["social_media", "web"],
                "retention_prediction": 0.75,  # Predicted % of viewers who will watch to end
                "shareability_score": 6.8
            }
            
            return predictions
            
        except Exception as e:
            logger.error(f"Engagement prediction failed: {e}")
            return {"error": str(e)}


class StyleOptimizer:
    """Video style optimization system"""
    
    async def optimize(self, prompt: str, current_style: Optional[str], 
                     user_style_preferences: Dict) -> Dict:
        """Optimize style parameters"""
        
        try:
            # Analyze prompt for style cues
            detected_styles = self._analyze_prompt_styles(prompt)
            
            # Consider user preferences
            preferred_style = user_style_preferences.get("most_used_style", current_style)
            
            # Determine optimal style
            optimal_style = self._determine_optimal_style(
                detected_styles, current_style, preferred_style
            )
            
            # Generate style-specific recommendations
            recommendations = {
                "optimal_style": optimal_style,
                "optimal_resolution": self._recommend_resolution(optimal_style),
                "recommended_effects": self._recommend_effects(optimal_style),
                "color_palette": self._recommend_color_palette(optimal_style),
                "motion_characteristics": self._recommend_motion(optimal_style),
                "confidence": 0.8,
                "reasoning": [
                    f"Style '{optimal_style}' best matches prompt characteristics",
                    f"User shows preference for {preferred_style} style",
                    "Optimized for current trends and effectiveness"
                ]
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Style optimization failed: {e}")
            return {"error": str(e)}
    
    def _analyze_prompt_styles(self, prompt: str) -> Dict:
        """Analyze prompt for style indicators"""
        # Placeholder - would use NLP analysis
        return {"cinematic": 0.8, "professional": 0.6}
    
    def _determine_optimal_style(self, detected: Dict, current: str, preferred: str) -> str:
        """Determine optimal style"""
        if detected:
            return max(detected, key=detected.get)
        return current or preferred or "cinematic"
    
    def _recommend_resolution(self, style: str) -> str:
        """Recommend resolution for style"""
        style_resolutions = {
            "social_media": "1080x1920",  # Vertical
            "cinematic": "1920x1080",
            "commercial": "1920x1080",
            "documentary": "1920x1080"
        }
        return style_resolutions.get(style, "1280x720")
    
    def _recommend_effects(self, style: str) -> List[str]:
        """Recommend effects for style"""
        style_effects = {
            "cinematic": ["color_grade", "vignette"],
            "vintage": ["sepia", "film_grain"],
            "modern": ["sharpen", "color_grade"],
            "artistic": ["stylized_effects", "creative_transitions"]
        }
        return style_effects.get(style, ["color_grade"])
    
    def _recommend_color_palette(self, style: str) -> List[str]:
        """Recommend color palette for style"""
        return ["warm", "vibrant"]  # Placeholder
    
    def _recommend_motion(self, style: str) -> str:
        """Recommend motion characteristics"""
        motion_mapping = {
            "cinematic": "moderate",
            "social_media": "high",
            "documentary": "minimal",
            "commercial": "high"
        }
        return motion_mapping.get(style, "moderate")


class CostOptimizer:
    """Cost-quality optimization system"""
    
    async def optimize(self, request_params: Dict, user_preferences: Dict, 
                     model_performance: Dict) -> Dict:
        """Optimize for cost-quality balance"""
        
        try:
            # Analyze cost-quality tradeoffs for each model
            models_analysis = {}
            
            for model in ["runway-ml", "stable-video", "luma-ai"]:
                analysis = self._analyze_model_cost_quality(
                    model, request_params, model_performance.get(model, {})
                )
                models_analysis[model] = analysis
            
            # Find optimal model
            optimal_model = self._select_optimal_model(models_analysis, user_preferences)
            
            # Optimize quality setting
            optimal_quality = self._optimize_quality_setting(
                optimal_model, request_params, models_analysis[optimal_model]
            )
            
            result = {
                "optimal_model": optimal_model,
                "optimal_quality": optimal_quality,
                "potential_savings": self._calculate_savings(models_analysis, optimal_model),
                "quality_boost": self._calculate_quality_improvement(models_analysis, optimal_model),
                "reasoning": [
                    f"Model {optimal_model} offers best cost-quality balance",
                    f"Quality setting '{optimal_quality}' optimizes value",
                    "Based on historical performance data"
                ],
                "cost_breakdown": models_analysis
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Cost optimization failed: {e}")
            return {"error": str(e)}
    
    def _analyze_model_cost_quality(self, model: str, params: Dict, performance: Dict) -> Dict:
        """Analyze cost-quality for a specific model"""
        # Placeholder cost-quality analysis
        base_costs = {"runway-ml": 0.50, "stable-video": 0.0, "luma-ai": 0.30}
        base_quality = {"runway-ml": 8.5, "stable-video": 7.0, "luma-ai": 7.8}
        
        duration = params.get("duration", 5)
        quality = params.get("quality", "standard")
        
        cost = base_costs[model] * duration
        quality_score = base_quality[model]
        
        if quality == "high":
            cost *= 1.5
            quality_score += 0.5
        elif quality == "professional":
            cost *= 2.0
            quality_score += 1.0
        
        return {
            "estimated_cost": cost,
            "predicted_quality": min(quality_score, 10.0),
            "value_ratio": quality_score / max(cost, 0.01),
            "processing_time": performance.get("avg_time", 20)
        }
    
    def _select_optimal_model(self, analysis: Dict, preferences: Dict) -> str:
        """Select optimal model based on analysis"""
        # Simple optimization - maximize value ratio
        best_model = max(analysis.keys(), key=lambda m: analysis[m]["value_ratio"])
        return best_model
    
    def _optimize_quality_setting(self, model: str, params: Dict, model_analysis: Dict) -> str:
        """Optimize quality setting for selected model"""
        requested_quality = params.get("quality", "standard")
        
        # If user typically uses higher quality and can afford it, recommend it
        if model_analysis["estimated_cost"] < 5.0:  # Arbitrary threshold
            return "high" if requested_quality != "professional" else "professional"
        
        return requested_quality
    
    def _calculate_savings(self, analysis: Dict, optimal_model: str) -> float:
        """Calculate potential savings"""
        optimal_cost = analysis[optimal_model]["estimated_cost"]
        max_cost = max(a["estimated_cost"] for a in analysis.values())
        return max_cost - optimal_cost
    
    def _calculate_quality_improvement(self, analysis: Dict, optimal_model: str) -> float:
        """Calculate quality improvement"""
        optimal_quality = analysis[optimal_model]["predicted_quality"]
        avg_quality = sum(a["predicted_quality"] for a in analysis.values()) / len(analysis)
        return optimal_quality - avg_quality
    
    async def update_cost_quality_data(self, generation_data: Dict):
        """Update cost-quality relationship data"""
        # Placeholder for updating ML models with new data
        pass


class UserPreferenceLearner:
    """Learn and track user preferences"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def get_user_preferences(self, user_id: str) -> Dict:
        """Get learned user preferences"""
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get user's generation history
            cursor.execute('''
                SELECT style, model_used, quality_requested, duration, user_rating,
                       resolution, COUNT(*) as usage_count, AVG(user_rating) as avg_rating
                FROM video_generations 
                WHERE user_id = ? AND user_rating IS NOT NULL
                GROUP BY style, model_used, quality_requested
                ORDER BY usage_count DESC, avg_rating DESC
            ''', (user_id,))
            
            results = cursor.fetchall()
            
            # Get overall statistics
            cursor.execute('''
                SELECT AVG(duration), AVG(user_rating), COUNT(*) as total_generations
                FROM video_generations WHERE user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()
            conn.close()
            
            if not results:
                return {"total_generations": 0}
            
            # Build preferences
            preferences = {
                "total_generations": stats[2],
                "avg_duration": stats[0],
                "avg_satisfaction": stats[1],
                "style_preferences": {},
                "model_preferences": {},
                "quality_preferences": {},
                "most_used_style": None,
                "most_used_model": None,
                "preference_reasons": []
            }
            
            # Process results
            for result in results:
                style, model, quality, duration, rating, resolution, count, avg_rating = result
                
                # Track most used
                if preferences["most_used_style"] is None:
                    preferences["most_used_style"] = style
                if preferences["most_used_model"] is None:
                    preferences["most_used_model"] = model
                
                # Style preferences
                if style not in preferences["style_preferences"]:
                    preferences["style_preferences"][style] = {
                        "usage_count": count,
                        "avg_rating": avg_rating,
                        "preference_score": count * avg_rating
                    }
                
                # Model preferences
                if model not in preferences["model_preferences"]:
                    preferences["model_preferences"][model] = {
                        "usage_count": count,
                        "avg_rating": avg_rating,
                        "preference_score": count * avg_rating
                    }
            
            # Add reasoning
            if preferences["avg_satisfaction"] > 8.0:
                preferences["preference_reasons"].append("User shows high satisfaction with current choices")
            
            if len(preferences["style_preferences"]) == 1:
                preferences["preference_reasons"].append("User shows strong style consistency")
            
            return preferences
            
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}
    
    async def update_preferences(self, user_id: str, generation_data: Dict, feedback: Dict):
        """Update user preferences based on feedback"""
        
        try:
            # This would update preference learning models
            # For now, the preferences are learned from the database queries
            pass
            
        except Exception as e:
            logger.error(f"Failed to update preferences: {e}")


class PerformanceOptimizer:
    """Optimize system performance based on usage patterns"""
    
    async def update_model_performance(self, generation_data: Dict):
        """Update model performance tracking"""
        
        try:
            model = generation_data.get("model_used")
            style = generation_data.get("detected_style", "unknown")
            
            if not model or not style:
                return
            
            conn = sqlite3.connect(generation_data.get("db_path", ""))
            cursor = conn.cursor()
            
            # Update or insert performance data
            cursor.execute('''
                INSERT OR REPLACE INTO model_performance 
                (model_name, style, avg_quality_score, avg_generation_time,
                 success_rate, avg_cost, usage_count, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, 
                        COALESCE((SELECT usage_count FROM model_performance 
                                WHERE model_name = ? AND style = ?), 0) + 1,
                        ?)
            ''', (
                model, style,
                generation_data.get("quality_score", 0),
                generation_data.get("generation_time", 0),
                1.0 if generation_data.get("success") else 0.0,
                generation_data.get("cost", 0),
                model, style,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to update model performance: {e}")