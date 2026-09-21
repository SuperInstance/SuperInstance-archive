#!/usr/bin/env python3
"""
Integration module for connecting with the Unified Generative Tools Hub
Enables the image generation service to be discovered and utilized by the hub
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
    
    def __init__(self, image_service, hub_url: str = "http://localhost:8500"):
        self.image_service = image_service
        self.hub_url = hub_url
        self.service_url = "http://localhost:8480"  # This service's URL
        self.integration_active = False
        self.heartbeat_interval = 30  # seconds
        
    async def register_with_hub(self) -> bool:
        """Register this service with the generative tools hub"""
        
        registration_data = {
            "service_name": "comprehensive-image-generation",
            "service_url": self.service_url,
            "service_type": "image_generation",
            "version": "2.0.0",
            "capabilities": {
                "image_generation": {
                    "models": ["dall-e-3", "stable-diffusion"],
                    "styles": list(self.image_service.style_keywords.keys()),
                    "formats": self.image_service.supported_formats,
                    "sizes": self.image_service.supported_sizes,
                    "features": [
                        "intelligent_style_detection",
                        "ml_prompt_optimization",
                        "batch_generation", 
                        "image_editing",
                        "quality_scoring",
                        "user_preference_learning",
                        "multiple_format_output"
                    ]
                },
                "image_editing": {
                    "operations": ["enhance", "upscale", "style_transfer", "inpaint", "outpaint"],
                    "supported_formats": ["png", "jpeg", "webp", "bmp"]
                },
                "ai_features": {
                    "prompt_enhancement": True,
                    "style_analysis": True,
                    "quality_prediction": True,
                    "user_learning": True,
                    "batch_processing": True
                }
            },
            "endpoints": {
                "generate": f"{self.service_url}/generate",
                "generate_batch": f"{self.service_url}/generate/batch",
                "analyze_style": f"{self.service_url}/analyze/style",
                "optimize_prompt": f"{self.service_url}/optimize/prompt",
                "edit_image": f"{self.service_url}/edit",
                "health": f"{self.service_url}/",
                "analytics": f"{self.service_url}/analytics/system"
            },
            "cost_structure": {
                "dall-e-3": "pay_per_use",
                "stable-diffusion": "free_local"
            },
            "quality_tiers": ["draft", "standard", "high", "professional"],
            "specialties": [
                "ui_mockups",
                "concept_art", 
                "marketing_visuals",
                "photorealistic_images",
                "artistic_content"
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Check if hub has a registration endpoint
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
        """Notify the hub when an image is generated (for analytics)"""
        
        if not self.integration_active:
            return
        
        notification_data = {
            "service": "comprehensive-image-generation",
            "event": "image_generated",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": generation_data.get("user_id"),
                "model_used": generation_data.get("model_used"),
                "style": generation_data.get("detected_style"),
                "quality_score": generation_data.get("quality_score"),
                "generation_time": generation_data.get("generation_time"),
                "cost": generation_data.get("cost", 0.0),
                "success": generation_data.get("success", False)
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
            "service_type": "image_generation",
            "request": {
                "prompt": request_data.get("prompt"),
                "user_id": request_data.get("user_id"),
                "quality": request_data.get("quality"),
                "style": request_data.get("style")
            },
            "user_history": await self._get_user_generation_history(request_data.get("user_id"))
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
            user_analytics = self.image_service.get_user_analytics(user_id)
            return {
                "total_generations": user_analytics.get("total_generations", 0),
                "style_preferences": user_analytics.get("style_preferences", []),
                "model_preferences": user_analytics.get("model_preferences", []),
                "average_satisfaction": user_analytics.get("average_rating", 0)
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
                        
                        # Extract image generation preferences from hub data
                        image_prefs = hub_preferences.get("generation_types", {}).get("image", {})
                        
                        if image_prefs:
                            # Update local preferences based on hub insights
                            return {
                                "hub_recommended_style": image_prefs.get("preferred_style"),
                                "hub_recommended_model": image_prefs.get("preferred_generator"),
                                "hub_quality_preference": image_prefs.get("avg_quality_requested"),
                                "sync_timestamp": datetime.now().isoformat()
                            }
                    
        except Exception as e:
            logger.debug(f"Could not sync with hub preferences: {e}")
            
        return {}
    
    async def contribute_to_hub_learning(self, feedback_data: Dict):
        """Contribute user feedback to hub's global learning system"""
        
        if not self.integration_active:
            return
        
        learning_data = {
            "service": "comprehensive-image-generation",
            "learning_type": "user_feedback",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": feedback_data.get("user_id"),
                "generation_id": feedback_data.get("image_id"),
                "model_used": feedback_data.get("model_used"),
                "style_used": feedback_data.get("style_used"),
                "quality_score": feedback_data.get("quality_score"),
                "style_accuracy": feedback_data.get("style_accuracy"),
                "prompt_adherence": feedback_data.get("prompt_adherence"),
                "overall_satisfaction": feedback_data.get("overall_satisfaction"),
                "improvement_suggestions": feedback_data.get("comments")
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.hub_url}/learning/contribute",
                    json=learning_data,
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
                        
                        # Extract insights relevant to image generation
                        image_insights = hub_analytics.get("generation_types", {}).get("image", {})
                        
                        return {
                            "hub_active": True,
                            "global_image_trends": image_insights,
                            "popular_styles": hub_analytics.get("popular_styles", []),
                            "quality_trends": hub_analytics.get("quality_trends", {}),
                            "cost_optimization_tips": hub_analytics.get("cost_insights", []),
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
        
        # Apply hub insights to the request
        enhanced_request = request_data.copy()
        
        if hub_recommendations:
            recommended_model = hub_recommendations.get("recommended_generator")
            if recommended_model and not enhanced_request.get("model_preference"):
                enhanced_request["model_preference"] = recommended_model
                enhanced_request["hub_recommendation"] = True
        
        if hub_preferences:
            if not enhanced_request.get("style") and hub_preferences.get("hub_recommended_style"):
                enhanced_request["style"] = hub_preferences["hub_recommended_style"]
                enhanced_request["hub_style_suggestion"] = True
        
        return enhanced_request
    
    async def start_heartbeat(self):
        """Start heartbeat to maintain connection with hub"""
        
        while self.integration_active:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_data = {
                    "service": "comprehensive-image-generation",
                    "status": "operational",
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "total_generations": self.image_service.generation_stats["total_generated"],
                        "success_rate": (
                            self.image_service.generation_stats["successful_generations"] / 
                            max(1, self.image_service.generation_stats["total_generated"])
                        ),
                        "avg_satisfaction": self.image_service.generation_stats["user_satisfaction_avg"]
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
    
    def get_integration_status(self) -> Dict:
        """Get current integration status"""
        
        return {
            "integration_active": self.integration_active,
            "hub_url": self.hub_url,
            "service_url": self.service_url,
            "heartbeat_interval": self.heartbeat_interval,
            "features": [
                "service_registration",
                "generation_notifications", 
                "recommendation_requests",
                "preference_synchronization",
                "learning_contributions",
                "insights_gathering",
                "enhanced_generation"
            ]
        }


# Integration helper functions for the main service
async def initialize_hub_integration(image_service) -> GenerativeHubIntegration:
    """Initialize and register hub integration"""
    
    integration = GenerativeHubIntegration(image_service)
    
    # Try to register with hub
    success = await integration.register_with_hub()
    
    if success:
        # Start heartbeat in background
        asyncio.create_task(integration.start_heartbeat())
        logger.info("🔗 Hub integration active - enhanced features enabled")
    else:
        logger.info("🔌 Hub integration inactive - service running independently")
    
    return integration

async def enhanced_generate_with_hub(integration: GenerativeHubIntegration, 
                                   image_service, request_data: Dict) -> Dict:
    """Generate image with hub intelligence if available"""
    
    # Get enhanced request from hub
    enhanced_request = await integration.enhanced_generation_with_hub(request_data)
    
    # Generate the image
    from main import ImageGenerationRequest
    generation_request = ImageGenerationRequest(**enhanced_request)
    result = await image_service.generate_image(generation_request)
    
    # Notify hub of generation
    if result.get("success"):
        await integration.notify_hub_of_generation(result)
    
    # Add hub integration metadata
    result["hub_integration"] = {
        "active": integration.integration_active,
        "recommendations_used": enhanced_request.get("hub_recommendation", False),
        "style_suggestion_used": enhanced_request.get("hub_style_suggestion", False)
    }
    
    return result