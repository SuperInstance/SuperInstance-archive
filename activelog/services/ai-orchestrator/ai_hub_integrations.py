# AI Hub Integration System
# Connects all AI services to the ai-orchestrator hub

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import hashlib
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class AIServiceType(Enum):
    DOCUMENT_AI = "document-ai"
    EMOTIONAL_AI = "emotional-ai"
    EDUCATION_AI = "education-ai"
    COGNITIVE = "cognitive"
    SOCIAL_AI = "social-ai"
    PREDICTIVE_AI = "predictive-ai"
    CREATIVE_SUITE = "creative-suite"
    ML_PIPELINE = "ml-pipeline"
    VIDEO_PROCESSOR = "video-processor"

@dataclass
class AIServiceEndpoint:
    name: str
    service_type: AIServiceType
    base_url: str
    port: int
    health_endpoint: str
    capabilities: List[str]
    priority: int = 1  # 1=critical, 2=high, 3=medium, 4=low

class AIHubIntegrator:
    """Central hub that orchestrates all AI services"""
    
    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.services = {}
        self.service_health = {}
        self.load_balancer = AILoadBalancer()
        self.request_router = AIRequestRouter()
        self.setup_services()
        
    def setup_services(self):
        """Initialize all AI service endpoints"""
        
        # Core AI Services
        self.services[AIServiceType.DOCUMENT_AI] = AIServiceEndpoint(
            name="document-ai",
            service_type=AIServiceType.DOCUMENT_AI,
            base_url="http://document-ai.activelog",
            port=8035,
            health_endpoint="/health",
            capabilities=[
                "text_extraction", "document_classification", "ner",
                "table_extraction", "summarization", "ocr"
            ],
            priority=1
        )
        
        self.services[AIServiceType.EMOTIONAL_AI] = AIServiceEndpoint(
            name="emotional-ai",
            service_type=AIServiceType.EMOTIONAL_AI,
            base_url="http://emotional-ai.activelog",
            port=8036,
            health_endpoint="/health",
            capabilities=[
                "mood_detection", "stress_analysis", "emotional_journey_mapping",
                "sentiment_analysis", "emotion_tracking"
            ],
            priority=2
        )
        
        self.services[AIServiceType.EDUCATION_AI] = AIServiceEndpoint(
            name="education-ai",
            service_type=AIServiceType.EDUCATION_AI,
            base_url="http://education-ai.activelog",
            port=8037,
            health_endpoint="/health",
            capabilities=[
                "curriculum_generation", "learning_style_detection", "auto_grading",
                "knowledge_gap_analysis", "educational_games", "tutoring"
            ],
            priority=1
        )
        
        self.services[AIServiceType.COGNITIVE] = AIServiceEndpoint(
            name="cognitive",
            service_type=AIServiceType.COGNITIVE,
            base_url="http://cognitive.activelog",
            port=8038,
            health_endpoint="/health",
            capabilities=[
                "reasoning", "problem_solving", "pattern_recognition",
                "cognitive_load_analysis", "decision_support"
            ],
            priority=1
        )
        
        self.services[AIServiceType.SOCIAL_AI] = AIServiceEndpoint(
            name="social-ai",
            service_type=AIServiceType.SOCIAL_AI,
            base_url="http://social-ai.activelog",
            port=8039,
            health_endpoint="/health",
            capabilities=[
                "relationship_mapping", "communication_adaptation", "gift_suggestions",
                "social_energy_tracking", "influence_mapping", "team_formation"
            ],
            priority=2
        )
        
        self.services[AIServiceType.PREDICTIVE_AI] = AIServiceEndpoint(
            name="predictive-ai",
            service_type=AIServiceType.PREDICTIVE_AI,
            base_url="http://predictive-ai.activelog",
            port=8034,
            health_endpoint="/health",
            capabilities=[
                "behavior_prediction", "future_needs_prediction", "smart_precaching",
                "folder_suggestions", "analytics"
            ],
            priority=2
        )
        
        self.services[AIServiceType.CREATIVE_SUITE] = AIServiceEndpoint(
            name="creative-suite",
            service_type=AIServiceType.CREATIVE_SUITE,
            base_url="http://creative-suite.activelog",
            port=8042,
            health_endpoint="/health",
            capabilities=[
                "style_transfer", "idea_combination", "creative_inspiration",
                "music_generation", "story_generation", "art_collaboration"
            ],
            priority=3
        )
        
        self.services[AIServiceType.ML_PIPELINE] = AIServiceEndpoint(
            name="ml-pipeline",
            service_type=AIServiceType.ML_PIPELINE,
            base_url="http://ml-pipeline.activelog",
            port=8032,
            health_endpoint="/health",
            capabilities=[
                "model_training", "feature_engineering", "model_deployment",
                "experiment_tracking", "hyperparameter_tuning", "model_versioning"
            ],
            priority=1
        )
        
        self.services[AIServiceType.VIDEO_PROCESSOR] = AIServiceEndpoint(
            name="video-processor",
            service_type=AIServiceType.VIDEO_PROCESSOR,
            base_url="http://video-processor.activelog",
            port=8041,
            health_endpoint="/health",
            capabilities=[
                "video_analysis", "frame_extraction", "scene_detection",
                "object_tracking", "video_summarization", "thumbnail_generation"
            ],
            priority=2
        )

    async def register_service(self, service_endpoint: AIServiceEndpoint):
        """Register a new AI service"""
        self.services[service_endpoint.service_type] = service_endpoint
        logger.info(f"Registered AI service: {service_endpoint.name}")
        
        # Store in Redis for persistence
        if self.redis_client:
            await self.redis_client.hset(
                "ai:services", 
                service_endpoint.name,
                json.dumps({
                    "name": service_endpoint.name,
                    "type": service_endpoint.service_type.value,
                    "base_url": service_endpoint.base_url,
                    "port": service_endpoint.port,
                    "capabilities": service_endpoint.capabilities,
                    "priority": service_endpoint.priority,
                    "registered_at": datetime.utcnow().isoformat()
                })
            )

    async def health_check_all_services(self) -> Dict[str, Any]:
        """Check health of all registered AI services"""
        health_results = {}
        
        async with aiohttp.ClientSession() as session:
            tasks = []
            for service_type, service in self.services.items():
                tasks.append(self._check_service_health(session, service))
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                service = list(self.services.values())[i]
                if isinstance(result, Exception):
                    health_results[service.name] = {
                        "status": "unhealthy",
                        "error": str(result),
                        "checked_at": datetime.utcnow().isoformat()
                    }
                else:
                    health_results[service.name] = result

        # Update service health cache
        self.service_health = health_results
        
        # Store in Redis
        if self.redis_client:
            await self.redis_client.set(
                "ai:health:all",
                json.dumps(health_results),
                ex=30  # Expire after 30 seconds
            )
        
        return health_results

    async def _check_service_health(self, session: aiohttp.ClientSession, service: AIServiceEndpoint):
        """Check health of individual service"""
        try:
            health_url = f"{service.base_url}:{service.port}{service.health_endpoint}"
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with session.get(health_url, timeout=timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "status": "healthy",
                        "response_time": response.headers.get("X-Response-Time"),
                        "data": data,
                        "checked_at": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "http_status": response.status,
                        "checked_at": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            return {
                "status": "unreachable",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }

    async def route_request(self, capability: str, request_data: Dict[str, Any], 
                           preferred_service: Optional[str] = None) -> Dict[str, Any]:
        """Route request to appropriate AI service based on capability"""
        
        # Find services that support this capability
        capable_services = []
        for service in self.services.values():
            if capability in service.capabilities:
                capable_services.append(service)
        
        if not capable_services:
            raise ValueError(f"No services found for capability: {capability}")
        
        # Use preferred service if specified and capable
        if preferred_service:
            for service in capable_services:
                if service.name == preferred_service:
                    capable_services = [service]
                    break
        
        # Select best service using load balancer
        selected_service = await self.load_balancer.select_service(
            capable_services, self.service_health
        )
        
        # Route the request
        return await self.request_router.route_request(
            selected_service, capability, request_data
        )

    async def batch_process(self, requests: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process multiple AI requests in parallel"""
        tasks = []
        
        for i, req in enumerate(requests):
            capability = req.get("capability")
            data = req.get("data", {})
            preferred_service = req.get("service")
            
            task = self._process_single_request(i, capability, data, preferred_service)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Format results
        formatted_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                formatted_results.append({
                    "index": i,
                    "status": "error",
                    "error": str(result)
                })
            else:
                formatted_results.append({
                    "index": i,
                    "status": "success",
                    "result": result
                })
        
        return formatted_results

    async def _process_single_request(self, index: int, capability: str, 
                                    data: Dict[str, Any], preferred_service: Optional[str]):
        """Process single AI request"""
        try:
            return await self.route_request(capability, data, preferred_service)
        except Exception as e:
            logger.error(f"Request {index} failed: {e}")
            raise

    async def get_service_capabilities(self) -> Dict[str, List[str]]:
        """Get capabilities of all registered services"""
        capabilities = {}
        for service in self.services.values():
            capabilities[service.name] = service.capabilities
        return capabilities

    async def get_service_stats(self) -> Dict[str, Any]:
        """Get statistics about AI services"""
        healthy_count = len([s for s in self.service_health.values() if s.get("status") == "healthy"])
        total_count = len(self.services)
        
        capability_count = {}
        for service in self.services.values():
            for cap in service.capabilities:
                capability_count[cap] = capability_count.get(cap, 0) + 1
        
        return {
            "total_services": total_count,
            "healthy_services": healthy_count,
            "unhealthy_services": total_count - healthy_count,
            "health_percentage": (healthy_count / total_count * 100) if total_count > 0 else 0,
            "total_capabilities": len(capability_count),
            "capability_distribution": capability_count,
            "service_priorities": {
                "critical": len([s for s in self.services.values() if s.priority == 1]),
                "high": len([s for s in self.services.values() if s.priority == 2]),
                "medium": len([s for s in self.services.values() if s.priority == 3]),
                "low": len([s for s in self.services.values() if s.priority == 4])
            }
        }

class AILoadBalancer:
    """Load balancer for AI services"""
    
    async def select_service(self, services: List[AIServiceEndpoint], 
                           health_status: Dict[str, Any]) -> AIServiceEndpoint:
        """Select the best service from available options"""
        
        # Filter healthy services
        healthy_services = []
        for service in services:
            service_health = health_status.get(service.name, {})
            if service_health.get("status") == "healthy":
                healthy_services.append(service)
        
        if not healthy_services:
            # If no healthy services, try any available service
            if services:
                logger.warning(f"No healthy services available, using first available: {services[0].name}")
                return services[0]
            else:
                raise RuntimeError("No services available")
        
        # Select by priority first, then by name for consistency
        best_service = min(healthy_services, key=lambda s: (s.priority, s.name))
        return best_service

class AIRequestRouter:
    """Routes requests to specific AI services"""
    
    async def route_request(self, service: AIServiceEndpoint, capability: str, 
                           request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Route request to specific service"""
        
        # Map capabilities to service endpoints
        endpoint_mapping = {
            # Document AI
            "text_extraction": "/extract/text",
            "document_classification": "/classify",
            "ner": "/ner",
            "table_extraction": "/extract/tables",
            "summarization": "/summarize",
            "ocr": "/ocr",
            
            # Emotional AI
            "mood_detection": "/analyze/mood",
            "stress_analysis": "/analyze/stress",
            "emotional_journey_mapping": "/journey/map",
            "sentiment_analysis": "/analyze/sentiment",
            "emotion_tracking": "/track/emotion",
            
            # Education AI
            "curriculum_generation": "/generate/curriculum",
            "learning_style_detection": "/detect/learning-style",
            "auto_grading": "/grade",
            "knowledge_gap_analysis": "/analyze/gaps",
            "educational_games": "/generate/games",
            "tutoring": "/tutor",
            
            # Social AI
            "relationship_mapping": "/map/relationships",
            "communication_adaptation": "/adapt/communication",
            "gift_suggestions": "/suggest/gifts",
            "social_energy_tracking": "/track/energy",
            "influence_mapping": "/map/influence",
            "team_formation": "/form/teams",
            
            # Predictive AI
            "behavior_prediction": "/predict/behavior",
            "future_needs_prediction": "/predict/needs",
            "smart_precaching": "/cache/predict",
            "folder_suggestions": "/suggest/folders",
            
            # Creative Suite
            "style_transfer": "/transfer/style",
            "idea_combination": "/combine/ideas",
            "creative_inspiration": "/inspire",
            "music_generation": "/generate/music",
            "story_generation": "/generate/story",
            
            # ML Pipeline
            "model_training": "/train",
            "feature_engineering": "/features",
            "model_deployment": "/deploy",
            "experiment_tracking": "/experiments",
            "hyperparameter_tuning": "/tune",
            
            # Video Processing
            "video_analysis": "/analyze/video",
            "frame_extraction": "/extract/frames",
            "scene_detection": "/detect/scenes",
            "object_tracking": "/track/objects",
            "video_summarization": "/summarize/video"
        }
        
        endpoint = endpoint_mapping.get(capability, f"/api/{capability}")
        url = f"{service.base_url}:{service.port}{endpoint}"
        
        timeout = aiohttp.ClientTimeout(total=60)  # AI operations can take longer
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=request_data, timeout=timeout) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "status": "success",
                            "service": service.name,
                            "capability": capability,
                            "result": result,
                            "response_time": response.headers.get("X-Response-Time"),
                            "processed_at": datetime.utcnow().isoformat()
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "status": "error",
                            "service": service.name,
                            "capability": capability,
                            "error": f"HTTP {response.status}: {error_text}",
                            "processed_at": datetime.utcnow().isoformat()
                        }
                        
            except Exception as e:
                logger.error(f"Request routing failed for {service.name}: {e}")
                return {
                    "status": "error",
                    "service": service.name,
                    "capability": capability,
                    "error": str(e),
                    "processed_at": datetime.utcnow().isoformat()
                }