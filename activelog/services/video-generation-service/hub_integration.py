#!/usr/bin/env python3
"""
Generative Hub Integration for Video Generation Service
Seamless integration with the unified generative tools hub at localhost:8500
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class GenerativeHubIntegration:
    """Handles integration with the unified generative tools hub"""
    
    def __init__(self, video_service, hub_url: str = "http://localhost:8500"):
        self.video_service = video_service
        self.hub_url = hub_url
        self.service_url = "http://localhost:8481"  # This service's URL
        self.integration_active = False
        self.heartbeat_interval = 30  # seconds
        
    async def register_with_hub(self) -> bool:
        """Register this service with the generative tools hub"""
        
        registration_data = {
            "service_name": "comprehensive-video-generation",
            "service_url": self.service_url,
            "service_type": "video_generation",
            "network_affiliation": "building_bots_network",
            "version": "1.0.0",
            "capabilities": {
                "video_generation": {
                    "models": ["runway-ml", "stable-video", "luma-ai"],
                    "styles": list(self.video_service.style_keywords.keys()),
                    "formats": self.video_service.supported_formats,
                    "resolutions": self.video_service.supported_resolutions,
                    "max_duration": 120,
                    "min_duration": 1,
                    "features": [
                        "text_to_video_generation",
                        "image_to_video_conversion", 
                        "intelligent_style_detection",
                        "ml_prompt_optimization",
                        "batch_processing",
                        "video_editing_suite",
                        "quality_optimization",
                        "user_preference_learning",
                        "cross_service_integration",
                        "cost_quality_optimization",
                        "multiple_format_output",
                        "production_ready_output"
                    ]
                },
                "video_editing": {
                    "operations": [
                        "trim", "merge", "effects", "transitions", 
                        "enhance", "compress", "format_conversion"
                    ],
                    "supported_formats": ["mp4", "webm", "avi", "mov", "mkv", "gif"],
                    "effects": [
                        "color_grade", "blur", "sharpen", "vintage", "black_white",
                        "sepia", "vignette", "film_grain", "speed_ramp", "stabilization"
                    ],
                    "transitions": [
                        "fade", "slide_left", "slide_right", "zoom_in", "zoom_out",
                        "crossfade", "wipe", "dissolve"
                    ]
                },
                "ai_features": {
                    "video_intelligence": True,
                    "content_analysis": True,
                    "quality_assessment": True,
                    "engagement_prediction": True,
                    "style_optimization": True,
                    "cost_optimization": True,
                    "user_learning": True,
                    "batch_processing": True,
                    "performance_optimization": True
                },
                "network_features": {
                    "construction_excellence": True,
                    "cross_service_learning": True,
                    "network_optimization": True,
                    "mission_aligned": True,
                    "continuous_improvement": True
                }
            },
            "endpoints": {
                "generate_video": f"{self.service_url}/generate/video",
                "generate_text_to_video": f"{self.service_url}/generate/text-to-video",
                "generate_image_to_video": f"{self.service_url}/generate/image-to-video",
                "generate_batch": f"{self.service_url}/batch/submit",
                "edit_video": f"{self.service_url}/edit/video",
                "analyze_video": f"{self.service_url}/analyze/video",
                "health": f"{self.service_url}/",
                "analytics": f"{self.service_url}/analytics/system",
                "batch_status": f"{self.service_url}/batch/status"
            },
            "cost_structure": {
                "runway-ml": "pay_per_second",
                "stable-video": "free_local",
                "luma-ai": "pay_per_second",
                "editing": "free"
            },
            "quality_tiers": ["draft", "standard", "high", "professional"],
            "specialties": [
                "production_ready_videos",
                "intelligent_optimization",
                "batch_processing_efficiency",
                "cross_modal_integration",
                "building_bots_network_excellence",
                "cost_quality_balance",
                "user_centric_learning"
            ],
            "mission_statement": "Excellence in video construction with production-ready output and continuous learning"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/services/register",
                    json=registration_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Successfully registered with generative hub: {result}")
                        self.integration_active = True
                        return True
                    else:
                        logger.warning(f"Hub registration returned {response.status}")
                        # Continue anyway - hub might not support registration yet
                        self.integration_active = True
                        return True
                        
        except aiohttp.ClientError as e:
            logger.warning(f"Could not register with hub (hub may not be running): {e}")
            # Service can still operate independently
            return False
        except Exception as e:
            logger.error(f"Unexpected error during hub registration: {e}")
            return False
    
    async def notify_hub_of_generation(self, generation_data: Dict):
        """Notify the hub when a video is generated (for analytics)"""
        
        if not self.integration_active:
            return
        
        notification_data = {
            "service": "comprehensive-video-generation",
            "event": "video_generated",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": generation_data.get("user_id"),
                "generation_id": generation_data.get("generation_id"),
                "model_used": generation_data.get("model_used"),
                "style": generation_data.get("detected_style"),
                "quality_score": generation_data.get("quality_score"),
                "generation_time": generation_data.get("generation_time"),
                "duration": generation_data.get("duration"),
                "cost": generation_data.get("cost", 0.0),
                "success": generation_data.get("success", False),
                "resolution": generation_data.get("metadata", {}).get("resolution"),
                "format": generation_data.get("metadata", {}).get("format")
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/events/notify",
                    json=notification_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        logger.debug(f"Hub notification failed: {response.status}")
                        
        except Exception as e:
            logger.debug(f"Could not notify hub: {e}")
            # Non-critical error - continue operation
    
    async def get_hub_recommendations(self, request_data: Dict) -> Optional[Dict]:
        """Get recommendations from the hub for optimal generation"""
        
        if not self.integration_active:
            return None
        
        recommendation_request = {
            "service_type": "video_generation",
            "request": {
                "prompt": request_data.get("prompt"),
                "user_id": request_data.get("user_id"),
                "style": request_data.get("style"),
                "duration": request_data.get("duration"),
                "quality": request_data.get("quality"),
                "model_preference": request_data.get("model_preference")
            },
            "user_history": await self._get_user_generation_history(request_data.get("user_id")),
            "network_context": {
                "service": "building_bots_network",
                "mission": "construction_excellence",
                "optimization_focus": "quality_and_efficiency"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/recommend/optimal_generator",
                    json=recommendation_request,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    
        except Exception as e:
            logger.debug(f"Could not get hub recommendations: {e}")
            
        return None
    
    async def _get_user_generation_history(self, user_id: str) -> Dict:
        """Get user's generation history for hub recommendations"""
        
        try:
            # Use video intelligence system to get comprehensive user data
            from video_intelligence import VideoIntelligenceEngine
            intelligence = VideoIntelligenceEngine(self.video_service.db_path)
            
            user_prefs = await intelligence.user_preference_learner.get_user_preferences(user_id)
            
            return {
                "total_generations": user_prefs.get("total_generations", 0),
                "avg_duration": user_prefs.get("avg_duration", 5),
                "style_preferences": user_prefs.get("style_preferences", {}),
                "model_preferences": user_prefs.get("model_preferences", {}),
                "average_satisfaction": user_prefs.get("avg_satisfaction", 0),
                "most_used_style": user_prefs.get("most_used_style"),
                "most_used_model": user_prefs.get("most_used_model"),
                "preference_reasons": user_prefs.get("preference_reasons", [])
            }
        except Exception as e:
            logger.debug(f"Could not get user history: {e}")
            return {}
    
    async def sync_with_hub_preferences(self, user_id: str) -> Dict:
        """Sync user preferences with the hub's global learning"""
        
        if not self.integration_active:
            return {}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.hub_url}/analytics/user/{user_id}",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        hub_preferences = await response.json()
                        
                        # Extract video generation preferences from hub data
                        video_prefs = hub_preferences.get("generation_types", {}).get("video", {})
                        
                        if video_prefs:
                            # Update local preferences based on hub insights
                            return {
                                "hub_recommended_style": video_prefs.get("preferred_style"),
                                "hub_recommended_model": video_prefs.get("preferred_generator"),
                                "hub_quality_preference": video_prefs.get("avg_quality_requested"),
                                "hub_duration_preference": video_prefs.get("avg_duration"),
                                "hub_cost_preference": video_prefs.get("cost_sensitivity"),
                                "network_insights": video_prefs.get("network_recommendations", []),
                                "sync_timestamp": datetime.now().isoformat()
                            }
                    
        except Exception as e:
            logger.debug(f"Could not sync with hub preferences: {e}")
            
        return {}
    
    async def contribute_to_hub_learning(self, learning_data: Dict):
        """Contribute learning data to hub's global learning system"""
        
        if not self.integration_active:
            return
        
        contribution_data = {
            "service": "comprehensive-video-generation",
            "network": "building_bots_network",
            "learning_type": "video_generation_feedback",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": learning_data.get("user_id"),
                "generation_id": learning_data.get("video_id"),
                "model_used": learning_data.get("model_used"),
                "style_used": learning_data.get("style_used"),
                "quality_score": learning_data.get("quality_score"),
                "content_relevance": learning_data.get("content_relevance"),
                "visual_appeal": learning_data.get("visual_appeal"),
                "overall_satisfaction": learning_data.get("overall_satisfaction"),
                "generation_params": learning_data.get("generation_params", {}),
                "optimization_applied": learning_data.get("optimization_applied", []),
                "cost_efficiency": learning_data.get("cost_efficiency"),
                "improvement_suggestions": learning_data.get("comments"),
                "network_contribution": {
                    "excellence_focus": True,
                    "construction_quality": learning_data.get("construction_quality"),
                    "production_readiness": learning_data.get("production_readiness")
                }
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/learning/contribute",
                    json=contribution_data,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        logger.debug("Successfully contributed learning data to hub")
                        
        except Exception as e:
            logger.debug(f"Could not contribute to hub learning: {e}")
    
    async def get_hub_insights(self) -> Dict:
        """Get insights and trends from the hub"""
        
        if not self.integration_active:
            return {"hub_active": False}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.hub_url}/analytics",
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status == 200:
                        hub_analytics = await response.json()
                        
                        # Extract insights relevant to video generation
                        video_insights = hub_analytics.get("generation_types", {}).get("video", {})
                        network_insights = hub_analytics.get("networks", {}).get("building_bots_network", {})
                        
                        return {
                            "hub_active": True,
                            "global_video_trends": video_insights,
                            "network_performance": network_insights,
                            "popular_styles": hub_analytics.get("popular_styles", []),
                            "quality_trends": hub_analytics.get("quality_trends", {}),
                            "cost_optimization_insights": hub_analytics.get("cost_insights", []),
                            "model_performance_comparison": hub_analytics.get("model_comparison", {}),
                            "user_satisfaction_trends": hub_analytics.get("satisfaction_trends", {}),
                            "network_excellence_metrics": network_insights.get("excellence_metrics", {}),
                            "cross_service_optimizations": hub_analytics.get("cross_service_insights", []),
                            "sync_timestamp": datetime.now().isoformat()
                        }
                        
        except Exception as e:
            logger.debug(f"Could not get hub insights: {e}")
            
        return {"hub_active": False, "error": str(e)}
    
    async def enhanced_generation_with_hub(self, request_data: Dict) -> Dict:
        """Enhanced generation that leverages hub intelligence"""
        
        # Get hub recommendations
        hub_recommendations = await self.get_hub_recommendations(request_data)
        
        # Sync user preferences with hub
        hub_preferences = await self.sync_with_hub_preferences(request_data.get("user_id", "default"))
        
        # Get hub insights
        hub_insights = await self.get_hub_insights()
        
        # Apply hub intelligence to the request
        enhanced_request = request_data.copy()
        enhancements_applied = []
        
        # Apply hub recommendations
        if hub_recommendations:
            recommended_model = hub_recommendations.get("recommended_generator")
            if recommended_model and not enhanced_request.get("model_preference"):
                enhanced_request["model_preference"] = recommended_model
                enhancements_applied.append(f"hub_recommended_model: {recommended_model}")
            
            recommended_quality = hub_recommendations.get("recommended_quality")
            if recommended_quality:
                enhanced_request["quality"] = recommended_quality
                enhancements_applied.append(f"hub_recommended_quality: {recommended_quality}")
        
        # Apply hub preferences
        if hub_preferences:
            if not enhanced_request.get("style") and hub_preferences.get("hub_recommended_style"):
                enhanced_request["style"] = hub_preferences["hub_recommended_style"]
                enhancements_applied.append(f"hub_style_preference: {hub_preferences['hub_recommended_style']}")
            
            # Optimize duration based on hub insights
            if hub_preferences.get("hub_duration_preference"):
                hub_duration = hub_preferences["hub_duration_preference"]
                current_duration = enhanced_request.get("duration", 5)
                # Blend current with hub preference
                optimized_duration = int((current_duration + hub_duration) / 2)
                enhanced_request["duration"] = optimized_duration
                enhancements_applied.append(f"hub_duration_optimization: {optimized_duration}s")
        
        # Apply network excellence standards
        if hub_insights.get("hub_active") and hub_insights.get("network_excellence_metrics"):
            excellence_metrics = hub_insights["network_excellence_metrics"]
            
            # Ensure high quality for network excellence
            if excellence_metrics.get("quality_standards", 8.0) > 8.0:
                if enhanced_request.get("quality", "standard") == "standard":
                    enhanced_request["quality"] = "high"
                    enhancements_applied.append("network_excellence_quality_boost")
            
            # Apply cost optimization insights
            cost_insights = hub_insights.get("cost_optimization_insights", [])
            if cost_insights and enhanced_request.get("model_preference") is None:
                # Find most cost-effective model from insights
                for insight in cost_insights:
                    if "video" in insight.lower() and "model" in insight.lower():
                        # Parse model recommendation from insight
                        if "stable-video" in insight.lower():
                            enhanced_request["model_preference"] = "stable-video"
                            enhancements_applied.append("hub_cost_optimization: stable-video")
                        break
        
        # Add hub integration metadata
        enhanced_request["hub_enhancements"] = {
            "applied": enhancements_applied,
            "hub_active": hub_insights.get("hub_active", False),
            "network_optimized": len(enhancements_applied) > 0,
            "excellence_aligned": "network_excellence" in str(enhancements_applied)
        }
        
        return enhanced_request
    
    async def start_heartbeat(self):
        """Start heartbeat to maintain connection with hub"""
        
        while self.integration_active:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_data = {
                    "service": "comprehensive-video-generation",
                    "network": "building_bots_network",
                    "status": "operational",
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "total_generations": self.video_service.generation_stats["total_generated"],
                        "successful_generations": self.video_service.generation_stats["successful_generations"],
                        "total_duration_generated": self.video_service.generation_stats["total_duration_generated"],
                        "success_rate": (
                            self.video_service.generation_stats["successful_generations"] / 
                            max(1, self.video_service.generation_stats["total_generated"])
                        ),
                        "avg_satisfaction": self.video_service.generation_stats["user_satisfaction_avg"],
                        "cost_savings": self.video_service.generation_stats["cost_optimization_savings"]
                    },
                    "capabilities_status": {
                        "video_generation": "active",
                        "batch_processing": "active", 
                        "video_editing": "active",
                        "ai_optimization": "active",
                        "user_learning": "active"
                    },
                    "network_contribution": {
                        "construction_excellence": True,
                        "continuous_learning": True,
                        "performance_optimization": True,
                        "cross_service_integration": True
                    }
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.hub_url}/services/heartbeat",
                        json=heartbeat_data,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status != 200:
                            logger.debug(f"Heartbeat failed: {response.status}")
                            
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")
                # Continue heartbeat loop even on errors
    
    async def request_cross_service_collaboration(self, collaboration_request: Dict) -> Optional[Dict]:
        """Request collaboration with other services in the network"""
        
        if not self.integration_active:
            return None
        
        collaboration_data = {
            "requesting_service": "comprehensive-video-generation",
            "network": "building_bots_network",
            "collaboration_type": collaboration_request.get("type"),
            "request_details": collaboration_request,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/collaborate/request",
                    json=collaboration_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                        
        except Exception as e:
            logger.debug(f"Cross-service collaboration request failed: {e}")
        
        return None
    
    async def optimize_with_network_intelligence(self, generation_request: Dict) -> Dict:
        """Apply network-wide intelligence for optimization"""
        
        try:
            # Get network-wide optimization recommendations
            optimization_request = {
                "service_type": "video_generation",
                "network": "building_bots_network",
                "optimization_goal": "construction_excellence",
                "request_context": generation_request,
                "user_context": await self._get_user_generation_history(
                    generation_request.get("user_id", "default")
                )
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/network/optimize",
                    json=optimization_request,
                    timeout=aiohttp.ClientTimeout(total=8)
                ) as response:
                    if response.status == 200:
                        optimization_result = await response.json()
                        return optimization_result.get("optimizations", {})
                        
        except Exception as e:
            logger.debug(f"Network optimization failed: {e}")
        
        return {}
    
    def get_integration_status(self) -> Dict:
        """Get current integration status"""
        
        return {
            "integration_active": self.integration_active,
            "hub_url": self.hub_url,
            "service_url": self.service_url,
            "network_affiliation": "building_bots_network",
            "heartbeat_interval": self.heartbeat_interval,
            "features": [
                "service_registration",
                "generation_notifications",
                "recommendation_requests", 
                "preference_synchronization",
                "learning_contributions",
                "insights_gathering",
                "enhanced_generation",
                "cross_service_collaboration",
                "network_optimization",
                "construction_excellence_alignment"
            ],
            "mission_alignment": {
                "construction_excellence": True,
                "continuous_learning": True,
                "network_optimization": True,
                "cross_service_integration": True,
                "user_centric_focus": True
            }
        }


# Integration helper functions
async def initialize_hub_integration(video_service) -> GenerativeHubIntegration:
    """Initialize and register hub integration"""
    
    integration = GenerativeHubIntegration(video_service)
    
    # Try to register with hub
    success = await integration.register_with_hub()
    
    if success:
        # Start heartbeat in background
        asyncio.create_task(integration.start_heartbeat())
        logger.info("🌟 Building Bots Network hub integration active - enhanced features enabled")
    else:
        logger.info("🔌 Hub integration inactive - service running independently")
    
    return integration


async def enhanced_generate_with_hub(integration: GenerativeHubIntegration,
                                   video_service, request_data: Dict) -> Dict:
    """Generate video with hub intelligence if available"""
    
    # Get enhanced request from hub
    enhanced_request = await integration.enhanced_generation_with_hub(request_data)
    
    # Apply network-wide optimizations
    network_optimizations = await integration.optimize_with_network_intelligence(enhanced_request)
    if network_optimizations:
        enhanced_request.update(network_optimizations)
        enhanced_request["hub_enhancements"]["applied"].extend(
            [f"network_optimization: {k}" for k in network_optimizations.keys()]
        )
    
    # Generate the video
    from main import VideoGenerationRequest
    generation_request = VideoGenerationRequest(**{
        k: v for k, v in enhanced_request.items() 
        if k in VideoGenerationRequest.__fields__
    })
    result = await video_service.generate_video(generation_request)
    
    # Notify hub of generation
    if result.get("success"):
        await integration.notify_hub_of_generation(result)
    
    # Add hub integration metadata to result
    result["hub_integration"] = {
        "active": integration.integration_active,
        "enhancements_applied": enhanced_request.get("hub_enhancements", {}).get("applied", []),
        "network_optimized": enhanced_request.get("hub_enhancements", {}).get("network_optimized", False),
        "excellence_aligned": enhanced_request.get("hub_enhancements", {}).get("excellence_aligned", False),
        "cross_service_collaboration": bool(network_optimizations)
    }
    
    return result