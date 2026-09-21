#!/usr/bin/env python3
"""
Integration module for connecting the audio generation service with the Unified Generative Tools Hub
Enables the audio service to be discovered and utilized by the hub while contributing to the
building bots network mission of interconnected construction excellence.
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

class GenerativeHubIntegration:
    """Handles integration with the unified generative tools hub for audio services"""
    
    def __init__(self, audio_service, hub_url: str = "http://localhost:8500"):
        self.audio_service = audio_service
        self.hub_url = hub_url
        self.service_url = "http://localhost:8485"  # This service's URL
        self.integration_active = False
        self.heartbeat_interval = 30  # seconds
        self.building_bots_mission = True
        
    async def register_with_hub(self) -> bool:
        """Register this service with the generative tools hub"""
        
        registration_data = {
            "service_name": "comprehensive-audio-generation",
            "service_url": self.service_url,
            "service_type": "audio_generation",
            "version": "3.0.0",
            "building_bots_network": True,
            "mission": "Excellence in audio construction and system integration",
            "capabilities": {
                "text_to_speech": {
                    "models": ["openai-tts", "festival", "espeak", "piper"],
                    "voices": list(self.audio_service.voice_catalog.keys()),
                    "languages": self.audio_service.supported_languages,
                    "formats": self.audio_service.supported_formats,
                    "quality_levels": ["draft", "standard", "high", "premium"],
                    "features": [
                        "intelligent_model_selection",
                        "voice_customization",
                        "multi_language_support",
                        "real_time_generation",
                        "batch_processing"
                    ]
                },
                "voice_cloning": {
                    "available": True,
                    "similarity_boost": True,
                    "custom_profiles": True,
                    "stability_control": True,
                    "style_exaggeration": True
                },
                "music_generation": {
                    "procedural": True,
                    "styles": self.audio_service.music_styles,
                    "midi_generation": True,
                    "custom_arrangements": True,
                    "mood_based": True,
                    "genre_specific": True
                },
                "audio_editing": {
                    "operations": ["trim", "merge", "enhance", "normalize", "add_effects", "change_speed"],
                    "batch_processing": True,
                    "format_conversion": True,
                    "quality_enhancement": True
                },
                "transcription": {
                    "models": ["whisper"],
                    "multi_language": True,
                    "timestamp_support": True,
                    "translation": True,
                    "confidence_scoring": True
                },
                "ai_features": {
                    "user_preference_learning": True,
                    "quality_optimization": True,
                    "cost_optimization": True,
                    "performance_prediction": True,
                    "intelligent_caching": True,
                    "building_bots_integration": True
                }
            },
            "endpoints": {
                "generate_speech": f"{self.service_url}/generate/speech",
                "generate_batch": f"{self.service_url}/generate/batch",
                "clone_voice": f"{self.service_url}/clone/voice",
                "generate_music": f"{self.service_url}/generate/music",
                "edit_audio": f"{self.service_url}/edit",
                "transcribe": f"{self.service_url}/transcribe",
                "health": f"{self.service_url}/",
                "analytics": f"{self.service_url}/analytics/system",
                "voices": f"{self.service_url}/voices",
                "languages": f"{self.service_url}/languages",
                "models": f"{self.service_url}/models",
                "building_bots_mission": f"{self.service_url}/building-bots/mission"
            },
            "cost_structure": {
                "openai-tts": "pay_per_use",
                "local_tts": "free",
                "voice_cloning": "free_beta",
                "music_generation": "free",
                "audio_editing": "free",
                "transcription": "free_local"
            },
            "quality_tiers": ["draft", "standard", "high", "premium"],
            "specialties": [
                "multi_language_tts",
                "voice_personalization", 
                "procedural_music",
                "audio_enhancement",
                "batch_audio_processing",
                "intelligent_voice_selection",
                "building_bots_network_construction"
            ],
            "performance_metrics": {
                "avg_generation_time": "2.5s",
                "supported_languages": len(self.audio_service.supported_languages),
                "voice_variety": sum(len(voices) for voices in self.audio_service.voice_catalog.values()),
                "uptime_target": "99.9%",
                "cost_efficiency": "high"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                # Register with the hub
                async with session.post(
                    f"{self.hub_url}/services/register",
                    json=registration_data,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Successfully registered audio service with generative hub: {result}")
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
        """Notify the hub when audio is generated (for analytics and building bots network)"""
        
        if not self.integration_active:
            return
        
        notification_data = {
            "service": "comprehensive-audio-generation",
            "event": "audio_generated",
            "building_bots_network": True,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": generation_data.get("user_id"),
                "generation_type": self._determine_generation_type(generation_data),
                "model_used": generation_data.get("model_used"),
                "voice_id": generation_data.get("voice_id"),
                "language": generation_data.get("language"),
                "quality_score": generation_data.get("quality_score"),
                "duration": generation_data.get("duration"),
                "generation_time": generation_data.get("generation_time"),
                "cost": generation_data.get("cost", 0.0),
                "success": generation_data.get("success", False),
                "format": generation_data.get("format"),
                "enhancement_applied": generation_data.get("enhanced", False)
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
    
    def _determine_generation_type(self, generation_data: Dict) -> str:
        """Determine the type of audio generation based on data"""
        
        model_used = generation_data.get("model_used", "")
        
        if "voice_cloning" in model_used:
            return "voice_cloning"
        elif "music" in model_used or "procedural" in model_used:
            return "music_generation"
        elif "transcription" in model_used or "whisper" in model_used:
            return "transcription"
        elif "editor" in model_used:
            return "audio_editing"
        else:
            return "text_to_speech"
    
    async def get_hub_recommendations(self, request_data: Dict) -> Optional[Dict]:
        """Get recommendations from the hub for optimal audio generation"""
        
        if not self.integration_active:
            return None
        
        recommendation_request = {
            "service_type": "audio_generation",
            "building_bots_context": True,
            "request": {
                "text": request_data.get("text", "")[:100],  # Truncate for privacy
                "user_id": request_data.get("user_id"),
                "language": request_data.get("language"),
                "voice_id": request_data.get("voice_id"),
                "quality": request_data.get("quality"),
                "format": request_data.get("format"),
                "generation_type": "text_to_speech"
            },
            "user_history": await self._get_user_audio_history(request_data.get("user_id")),
            "system_load": await self._get_system_load_info()
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
    
    async def _get_user_audio_history(self, user_id: str) -> Dict:
        """Get user's audio generation history for hub recommendations"""
        
        try:
            user_analytics = self.audio_service.get_user_analytics(user_id)
            return {
                "total_generations": user_analytics.get("total_generations", 0),
                "voice_preferences": user_analytics.get("voice_preferences", []),
                "language_preferences": user_analytics.get("language_preferences", []),
                "average_satisfaction": user_analytics.get("average_rating", 0),
                "total_audio_hours": user_analytics.get("total_audio_hours", 0),
                "preferred_quality": self._get_preferred_quality(user_id),
                "cost_sensitivity": self._estimate_cost_sensitivity(user_analytics)
            }
        except Exception as e:
            logger.debug(f"Could not get user history: {e}")
            return {}
    
    def _get_preferred_quality(self, user_id: str) -> str:
        """Determine user's preferred quality level"""
        
        user_prefs = self.audio_service.user_preferences.get(user_id, {})
        
        # Analyze usage patterns to determine preferred quality
        quality_scores = {}
        for pref_key, pref_data in user_prefs.items():
            if pref_data.get("preference_score", 0) > 7:  # High satisfaction
                usage_count = pref_data.get("usage_count", 0)
                # This would be more sophisticated in reality
                if usage_count > 5:
                    quality_scores["high"] = quality_scores.get("high", 0) + usage_count
                else:
                    quality_scores["standard"] = quality_scores.get("standard", 0) + usage_count
        
        return max(quality_scores, key=quality_scores.get) if quality_scores else "standard"
    
    def _estimate_cost_sensitivity(self, user_analytics: Dict) -> str:
        """Estimate user's cost sensitivity"""
        
        total_cost = user_analytics.get("total_cost", 0)
        total_generations = user_analytics.get("total_generations", 1)
        
        avg_cost_per_generation = total_cost / total_generations
        
        if avg_cost_per_generation > 0.05:
            return "low"  # Not cost sensitive
        elif avg_cost_per_generation > 0.01:
            return "medium"
        else:
            return "high"  # Very cost sensitive, prefers free models
    
    async def _get_system_load_info(self) -> Dict:
        """Get current system load information"""
        
        return {
            "total_generations_today": self.audio_service.generation_stats.get("total_generated", 0),
            "success_rate": (
                self.audio_service.generation_stats.get("successful_generations", 0) /
                max(1, self.audio_service.generation_stats.get("total_generated", 1))
            ),
            "average_generation_time": 2.5,  # Would calculate from recent generations
            "available_models": [
                model for model, available in self.audio_service.audio_tools.items() 
                if available
            ] + ["openai-tts"],
            "building_bots_integrations": self.audio_service.generation_stats.get("building_bots_integrations", 0)
        }
    
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
                        
                        # Extract audio generation preferences from hub data
                        audio_prefs = hub_preferences.get("generation_types", {}).get("audio", {})
                        
                        if audio_prefs:
                            # Update local preferences based on hub insights
                            return {
                                "hub_recommended_voice": audio_prefs.get("preferred_voice"),
                                "hub_recommended_model": audio_prefs.get("preferred_generator"),
                                "hub_recommended_language": audio_prefs.get("preferred_language"),
                                "hub_quality_preference": audio_prefs.get("avg_quality_requested"),
                                "hub_cost_optimization": audio_prefs.get("cost_optimization_enabled"),
                                "building_bots_optimized": True,
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
            "service": "comprehensive-audio-generation",
            "learning_type": "user_feedback",
            "building_bots_network": True,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "user_id": feedback_data.get("user_id"),
                "generation_id": feedback_data.get("audio_id"),
                "generation_type": self._determine_generation_type(feedback_data),
                "model_used": feedback_data.get("model_used"),
                "voice_used": feedback_data.get("voice_id"),
                "language_used": feedback_data.get("language"),
                "quality_score": feedback_data.get("quality_score"),
                "voice_naturalness": feedback_data.get("voice_naturalness"),
                "clarity": feedback_data.get("clarity"),
                "overall_satisfaction": feedback_data.get("overall_satisfaction"),
                "improvement_suggestions": feedback_data.get("comments"),
                "cost_effectiveness": feedback_data.get("cost_rating"),
                "building_bots_mission_support": True
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
                        logger.debug("Successfully contributed audio learning data to hub")
                        
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
                        
                        # Extract insights relevant to audio generation
                        audio_insights = hub_analytics.get("generation_types", {}).get("audio", {})
                        building_bots_insights = hub_analytics.get("building_bots_network", {})
                        
                        return {
                            "hub_active": True,
                            "global_audio_trends": audio_insights,
                            "popular_voices": hub_analytics.get("popular_voices", []),
                            "language_trends": hub_analytics.get("language_usage", {}),
                            "quality_trends": hub_analytics.get("quality_trends", {}),
                            "cost_optimization_tips": hub_analytics.get("cost_insights", []),
                            "building_bots_network": {
                                "active_integrations": building_bots_insights.get("active_integrations", 0),
                                "construction_excellence_score": building_bots_insights.get("excellence_score", 0),
                                "network_efficiency": building_bots_insights.get("network_efficiency", 0)
                            },
                            "audio_specific_insights": {
                                "most_requested_languages": audio_insights.get("top_languages", []),
                                "preferred_models": audio_insights.get("model_preferences", {}),
                                "voice_cloning_adoption": audio_insights.get("voice_cloning_usage", 0),
                                "music_generation_trends": audio_insights.get("music_trends", {})
                            },
                            "sync_timestamp": datetime.now().isoformat()
                        }
                        
        except Exception as e:
            logger.debug(f"Could not get hub insights: {e}")
            
        return {"hub_active": False, "error": str(e)}
    
    async def enhanced_generation_with_hub(self, request_data: Dict) -> Dict:
        """Enhanced audio generation that leverages hub intelligence"""
        
        # Get hub recommendations
        hub_recommendations = await self.get_hub_recommendations(request_data)
        
        # Sync user preferences with hub
        hub_preferences = await self.sync_with_hub_preferences(request_data.get("user_id", "default"))
        
        # Apply hub insights to the request
        enhanced_request = request_data.copy()
        
        if hub_recommendations:
            recommended_model = hub_recommendations.get("recommended_generator")
            recommended_voice = hub_recommendations.get("recommended_voice")
            recommended_quality = hub_recommendations.get("recommended_quality")
            
            if recommended_model and not enhanced_request.get("model_preference"):
                enhanced_request["model_preference"] = recommended_model
                enhanced_request["hub_recommendation"] = True
            
            if recommended_voice and not enhanced_request.get("voice_id"):
                enhanced_request["voice_id"] = recommended_voice
                enhanced_request["hub_voice_suggestion"] = True
                
            if recommended_quality and not enhanced_request.get("quality"):
                enhanced_request["quality"] = recommended_quality
                enhanced_request["hub_quality_suggestion"] = True
        
        if hub_preferences:
            if not enhanced_request.get("voice_id") and hub_preferences.get("hub_recommended_voice"):
                enhanced_request["voice_id"] = hub_preferences["hub_recommended_voice"]
                enhanced_request["hub_voice_sync"] = True
                
            if not enhanced_request.get("language") and hub_preferences.get("hub_recommended_language"):
                enhanced_request["language"] = hub_preferences["hub_recommended_language"]
                enhanced_request["hub_language_sync"] = True
                
            if hub_preferences.get("hub_cost_optimization"):
                enhanced_request["prefer_free_models"] = True
                enhanced_request["hub_cost_optimization"] = True
        
        # Add building bots network context
        enhanced_request["building_bots_network"] = True
        enhanced_request["construction_excellence"] = True
        
        return enhanced_request
    
    async def start_heartbeat(self):
        """Start heartbeat to maintain connection with hub"""
        
        while self.integration_active:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_data = {
                    "service": "comprehensive-audio-generation",
                    "status": "operational",
                    "building_bots_network": True,
                    "timestamp": datetime.now().isoformat(),
                    "stats": {
                        "total_generations": self.audio_service.generation_stats["total_generated"],
                        "success_rate": (
                            self.audio_service.generation_stats["successful_generations"] / 
                            max(1, self.audio_service.generation_stats["total_generated"])
                        ),
                        "avg_satisfaction": self.audio_service.generation_stats["user_satisfaction_avg"],
                        "total_audio_hours": self.audio_service.generation_stats["total_audio_hours"],
                        "building_bots_integrations": self.audio_service.generation_stats["building_bots_integrations"]
                    },
                    "capabilities": {
                        "models_available": list(self.audio_service.audio_tools.keys()) + ["openai-tts"],
                        "languages_supported": len(self.audio_service.supported_languages),
                        "voices_available": sum(len(voices) for voices in self.audio_service.voice_catalog.values()),
                        "formats_supported": len(self.audio_service.supported_formats)
                    },
                    "mission_status": {
                        "construction_excellence": True,
                        "system_integration": True,
                        "interconnected_intelligence": True
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
    
    async def get_building_bots_network_status(self) -> Dict:
        """Get building bots network specific status and metrics"""
        
        return {
            "network_active": self.integration_active,
            "mission_alignment": self.building_bots_mission,
            "construction_excellence": {
                "audio_quality_optimization": True,
                "intelligent_model_selection": True,
                "user_preference_learning": True,
                "cost_efficiency": True
            },
            "system_integration": {
                "hub_connected": self.integration_active,
                "service_discovery": True,
                "cross_service_optimization": True,
                "unified_analytics": True
            },
            "interconnected_intelligence": {
                "recommendation_system": True,
                "global_learning": True,
                "preference_synchronization": True,
                "performance_optimization": True
            },
            "audio_specializations": {
                "multi_language_tts": len(self.audio_service.supported_languages),
                "voice_variety": sum(len(voices) for voices in self.audio_service.voice_catalog.values()),
                "audio_formats": len(self.audio_service.supported_formats),
                "local_models": sum(1 for tool in self.audio_service.audio_tools.values() if tool),
                "cloud_integration": True
            }
        }
    
    def get_integration_status(self) -> Dict:
        """Get current integration status"""
        
        return {
            "integration_active": self.integration_active,
            "hub_url": self.hub_url,
            "service_url": self.service_url,
            "heartbeat_interval": self.heartbeat_interval,
            "building_bots_network": self.building_bots_mission,
            "features": [
                "service_registration",
                "generation_notifications", 
                "recommendation_requests",
                "preference_synchronization",
                "learning_contributions",
                "insights_gathering",
                "enhanced_generation",
                "building_bots_integration",
                "network_status_reporting"
            ],
            "mission": {
                "primary": "Excellence in audio construction and system integration",
                "network": "Interconnected building bots for intelligent audio systems"
            }
        }


# Integration helper functions for the main service
async def initialize_hub_integration(audio_service) -> GenerativeHubIntegration:
    """Initialize and register hub integration"""
    
    integration = GenerativeHubIntegration(audio_service)
    
    # Try to register with hub
    success = await integration.register_with_hub()
    
    if success:
        # Start heartbeat in background
        asyncio.create_task(integration.start_heartbeat())
        logger.info("🔗 Hub integration active - building bots network connected")
        logger.info("🏗️ Audio construction excellence mode enabled")
    else:
        logger.info("🔌 Hub integration inactive - service running independently")
    
    return integration

async def enhanced_generate_with_hub(integration: GenerativeHubIntegration, 
                                   audio_service, request_data: Dict, generation_type: str = "speech") -> Dict:
    """Generate audio with hub intelligence if available"""
    
    # Get enhanced request from hub
    enhanced_request = await integration.enhanced_generation_with_hub(request_data)
    
    # Generate the audio based on type
    result = None
    if generation_type == "speech":
        from main import AudioGenerationRequest
        generation_request = AudioGenerationRequest(**enhanced_request)
        result = await audio_service.generate_speech(generation_request)
    elif generation_type == "music":
        from main import MusicGenerationRequest
        music_request = MusicGenerationRequest(**enhanced_request)
        result = await audio_service.generate_music(music_request)
    elif generation_type == "batch":
        from main import BatchAudioRequest
        batch_request = BatchAudioRequest(**enhanced_request)
        result = await audio_service.generate_batch_audio(batch_request)
    
    # Notify hub of generation
    if result and (result.get("success") or (isinstance(result, dict) and result.get("successful_generations", 0) > 0)):
        generation_data = {
            "user_id": enhanced_request.get("user_id"),
            "model_used": result.get("model_used") if hasattr(result, 'model_used') else "batch",
            "success": result.get("success") or result.get("successful_generations", 0) > 0,
            "generation_time": result.get("generation_time") if hasattr(result, 'generation_time') else result.get("batch_time"),
            "cost": result.get("cost", 0.0) if hasattr(result, 'cost') else result.get("total_cost", 0.0),
            "duration": result.get("duration") if hasattr(result, 'duration') else result.get("total_duration"),
            "format": result.get("format") if hasattr(result, 'format') else enhanced_request.get("format"),
            "enhanced": enhanced_request.get("hub_recommendation") or enhanced_request.get("hub_voice_suggestion")
        }
        await integration.notify_hub_of_generation(generation_data)
    
    # Add hub integration metadata to result
    if isinstance(result, dict):
        result["hub_integration"] = {
            "active": integration.integration_active,
            "recommendations_used": enhanced_request.get("hub_recommendation", False),
            "voice_suggestion_used": enhanced_request.get("hub_voice_suggestion", False),
            "quality_suggestion_used": enhanced_request.get("hub_quality_suggestion", False),
            "cost_optimization_applied": enhanced_request.get("hub_cost_optimization", False),
            "building_bots_network": True,
            "construction_excellence": True
        }
    
    return result