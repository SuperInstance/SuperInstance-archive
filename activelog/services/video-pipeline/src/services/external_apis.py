"""
Integration with external ActiveLog services (auth, metadata, AI orchestrator)
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

import httpx
import structlog

from config.settings import settings

logger = structlog.get_logger()


class ExternalAPIService:
    """
    Service for integrating with other ActiveLog services
    """
    
    def __init__(self):
        self.auth_service_url = settings.auth_service_url
        self.metadata_service_url = settings.metadata_service_url
        self.ai_orchestrator_url = settings.ai_orchestrator_url
        self.api_gateway_url = settings.api_gateway_url
        
        self._http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize HTTP client with common settings"""
        self._http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers={
                "User-Agent": "VideoPipeline/1.0.0",
                "Content-Type": "application/json"
            }
        )
        
        logger.info("External API service initialized")

    async def close(self) -> None:
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()

    # Auth Service Integration
    async def validate_user_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate user authentication token"""
        try:
            response = await self._http_client.post(
                f"{self.auth_service_url}/api/validate-token",
                json={"token": token}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Token validation failed",
                             status_code=response.status_code,
                             response=response.text)
                return None
                
        except Exception as e:
            logger.error("Auth service validation failed", error=str(e))
            return None

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get user permissions from auth service"""
        try:
            response = await self._http_client.get(
                f"{self.auth_service_url}/api/users/{user_id}/permissions"
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("permissions", [])
            else:
                logger.warning("Failed to get user permissions",
                             user_id=user_id,
                             status_code=response.status_code)
                return []
                
        except Exception as e:
            logger.error("Get user permissions failed", 
                        user_id=user_id,
                        error=str(e))
            return []

    async def check_user_quota(self, user_id: str, resource_type: str) -> Dict[str, Any]:
        """Check user resource quota"""
        try:
            response = await self._http_client.get(
                f"{self.auth_service_url}/api/users/{user_id}/quota",
                params={"resource_type": resource_type}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning("Failed to check user quota",
                             user_id=user_id,
                             resource_type=resource_type)
                return {"available": False, "limit": 0, "used": 0}
                
        except Exception as e:
            logger.error("Check user quota failed",
                        user_id=user_id,
                        resource_type=resource_type,
                        error=str(e))
            return {"available": False, "limit": 0, "used": 0, "error": str(e)}

    # Metadata Service Integration
    async def create_video_metadata(
        self,
        video_id: str,
        user_id: str,
        metadata: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create video metadata record"""
        try:
            payload = {
                "video_id": video_id,
                "user_id": user_id,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat()
            }
            
            response = await self._http_client.post(
                f"{self.metadata_service_url}/api/videos",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                logger.error("Failed to create video metadata",
                           video_id=video_id,
                           status_code=response.status_code,
                           response=response.text)
                return None
                
        except Exception as e:
            logger.error("Create video metadata failed",
                        video_id=video_id,
                        error=str(e))
            return None

    async def update_video_metadata(
        self,
        video_id: str,
        updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update video metadata"""
        try:
            payload = {
                "updates": updates,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            response = await self._http_client.put(
                f"{self.metadata_service_url}/api/videos/{video_id}",
                json=payload
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error("Failed to update video metadata",
                           video_id=video_id,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Update video metadata failed",
                        video_id=video_id,
                        error=str(e))
            return None

    async def get_video_metadata(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video metadata from metadata service"""
        try:
            response = await self._http_client.get(
                f"{self.metadata_service_url}/api/videos/{video_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error("Failed to get video metadata",
                           video_id=video_id,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Get video metadata failed",
                        video_id=video_id,
                        error=str(e))
            return None

    async def index_video_content(
        self,
        video_id: str,
        content_data: Dict[str, Any]
    ) -> bool:
        """Index video content for search"""
        try:
            payload = {
                "video_id": video_id,
                "content": content_data,
                "indexed_at": datetime.utcnow().isoformat()
            }
            
            response = await self._http_client.post(
                f"{self.metadata_service_url}/api/search/index",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                logger.info("Video content indexed successfully", video_id=video_id)
                return True
            else:
                logger.error("Failed to index video content",
                           video_id=video_id,
                           status_code=response.status_code)
                return False
                
        except Exception as e:
            logger.error("Index video content failed",
                        video_id=video_id,
                        error=str(e))
            return False

    async def create_video_embeddings(
        self,
        video_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[List[float]]:
        """Create embeddings for video content"""
        try:
            payload = {
                "video_id": video_id,
                "text": text_content,
                "metadata": metadata or {}
            }
            
            response = await self._http_client.post(
                f"{self.metadata_service_url}/api/embeddings/create",
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embeddings")
            else:
                logger.error("Failed to create embeddings",
                           video_id=video_id,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Create embeddings failed",
                        video_id=video_id,
                        error=str(e))
            return None

    # AI Orchestrator Integration
    async def request_ai_analysis(
        self,
        video_id: str,
        analysis_type: str,
        input_data: Dict[str, Any],
        priority: int = 0
    ) -> Optional[str]:
        """Request AI analysis through orchestrator"""
        try:
            payload = {
                "video_id": video_id,
                "analysis_type": analysis_type,
                "input_data": input_data,
                "priority": priority,
                "callback_url": f"{settings.host}:{settings.port}/api/ai-callback",
                "requested_at": datetime.utcnow().isoformat()
            }
            
            response = await self._http_client.post(
                f"{self.ai_orchestrator_url}/api/analyze",
                json=payload
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data.get("job_id")
            else:
                logger.error("Failed to request AI analysis",
                           video_id=video_id,
                           analysis_type=analysis_type,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Request AI analysis failed",
                        video_id=video_id,
                        analysis_type=analysis_type,
                        error=str(e))
            return None

    async def get_ai_analysis_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get AI analysis result"""
        try:
            response = await self._http_client.get(
                f"{self.ai_orchestrator_url}/api/jobs/{job_id}/result"
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 202:
                # Still processing
                return {"status": "processing"}
            elif response.status_code == 404:
                return None
            else:
                logger.error("Failed to get AI analysis result",
                           job_id=job_id,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Get AI analysis result failed",
                        job_id=job_id,
                        error=str(e))
            return None

    async def cancel_ai_job(self, job_id: str) -> bool:
        """Cancel AI analysis job"""
        try:
            response = await self._http_client.delete(
                f"{self.ai_orchestrator_url}/api/jobs/{job_id}"
            )
            
            if response.status_code in [200, 204]:
                logger.info("AI job cancelled", job_id=job_id)
                return True
            else:
                logger.error("Failed to cancel AI job",
                           job_id=job_id,
                           status_code=response.status_code)
                return False
                
        except Exception as e:
            logger.error("Cancel AI job failed",
                        job_id=job_id,
                        error=str(e))
            return False

    # Health Checks
    async def health_check_all_services(self) -> Dict[str, Dict[str, Any]]:
        """Perform health check on all external services"""
        services = {
            "auth": self.auth_service_url,
            "metadata": self.metadata_service_url,
            "ai_orchestrator": self.ai_orchestrator_url
        }
        
        health_results = {}
        
        async def check_service(name: str, url: str) -> Dict[str, Any]:
            try:
                start_time = asyncio.get_event_loop().time()
                response = await self._http_client.get(f"{url}/health", timeout=5.0)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                
                return {
                    "healthy": response.status_code == 200,
                    "status_code": response.status_code,
                    "latency_ms": round(latency, 2),
                    "response": response.json() if response.status_code == 200 else None
                }
                
            except Exception as e:
                return {
                    "healthy": False,
                    "error": str(e),
                    "latency_ms": None
                }
        
        # Check all services concurrently
        tasks = [check_service(name, url) for name, url in services.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for (name, _), result in zip(services.items(), results):
            if isinstance(result, Exception):
                health_results[name] = {
                    "healthy": False,
                    "error": str(result)
                }
            else:
                health_results[name] = result
                
        return health_results

    # Utility Methods
    async def make_authenticated_request(
        self,
        method: str,
        url: str,
        user_token: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Make authenticated request to external service"""
        try:
            headers = {"Authorization": f"Bearer {user_token}"}
            
            response = await self._http_client.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            )
            
            if response.status_code in [200, 201, 202]:
                return response.json()
            else:
                logger.error("Authenticated request failed",
                           method=method,
                           url=url,
                           status_code=response.status_code)
                return None
                
        except Exception as e:
            logger.error("Authenticated request failed",
                        method=method,
                        url=url,
                        error=str(e))
            return None

    async def batch_request(
        self,
        requests: List[Dict[str, Any]],
        max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """Execute multiple requests concurrently with rate limiting"""
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def execute_request(req: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    response = await self._http_client.request(
                        method=req["method"],
                        url=req["url"],
                        json=req.get("data"),
                        params=req.get("params"),
                        headers=req.get("headers", {})
                    )
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "data": response.json() if response.status_code < 400 else None,
                        "request": req
                    }
                    
                except Exception as e:
                    return {
                        "success": False,
                        "error": str(e),
                        "request": req
                    }
        
        tasks = [execute_request(req) for req in requests]
        results = await asyncio.gather(*tasks)
        
        return results

    def _get_service_url(self, service_name: str) -> str:
        """Get service URL by name"""
        service_urls = {
            "auth": self.auth_service_url,
            "metadata": self.metadata_service_url,
            "ai_orchestrator": self.ai_orchestrator_url,
            "api_gateway": self.api_gateway_url
        }
        
        return service_urls.get(service_name, "")


# Global external API service instance
external_api_service = ExternalAPIService()