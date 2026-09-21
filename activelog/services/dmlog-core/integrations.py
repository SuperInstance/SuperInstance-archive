"""
DMLog SuperInstance Integration Module
Connects DMlog services to the broader SuperInstance ecosystem
"""

import httpx
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)

class SuperInstanceIntegration:
    """Integration client for SuperInstance services"""
    
    def __init__(self):
        self.api_gateway_url = os.getenv("API_GATEWAY_URL", "http://localhost:8088")
        self.ai_insights_url = os.getenv("AI_INSIGHTS_URL", "http://localhost:8090")
        self.user_management_url = os.getenv("USER_MANAGEMENT_URL", "http://localhost:8092")
        self.dmlog_ai_url = os.getenv("DMLOG_AI_URL", "http://localhost:8097")
        
    async def register_with_gateway(self, service_info: Dict[str, Any]) -> bool:
        """Register DMlog service with API Gateway"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_gateway_url}/api/v1/services/register",
                    json={
                        "name": "dmlog-core",
                        "version": "1.0.0",
                        "url": "http://localhost:8012",
                        "health_check": "/health",
                        "capabilities": [
                            "rpg_rules_engine",
                            "character_management", 
                            "campaign_tools",
                            "cross_domain_gaming"
                        ],
                        "integration_points": {
                            "ai_insights": "cross_domain_character_enhancement",
                            "user_management": "gaming_profiles",
                            "compute_capital": "dm_rewards_system"
                        }
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to register with API Gateway: {e}")
            return False

    async def get_user_gaming_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user gaming profile from User Management"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.user_management_url}/api/v1/users/{user_id}/gaming-profile"
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get gaming profile: {e}")
        return None

    async def enhance_character_with_cross_domain_data(self, character_id: str, user_id: str) -> Dict[str, Any]:
        """Use cross-domain AI to enhance character with real-world data"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.dmlog_ai_url}/api/v1/character-enhancement",
                    json={
                        "character_id": character_id,
                        "user_id": user_id,
                        "domains": ["fitness", "business", "personal_development", "marine"]
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to enhance character: {e}")
        return {}

    async def track_dm_rewards(self, user_id: str, campaign_id: str, session_quality: float) -> bool:
        """Track DM performance for compute capital rewards"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_gateway_url}/api/v1/compute-capital/dm-rewards",
                    json={
                        "user_id": user_id,
                        "campaign_id": campaign_id,
                        "session_quality": session_quality,
                        "timestamp": "2025-08-27T22:59:29.000Z"
                    }
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to track DM rewards: {e}")
            return False

    async def get_ai_campaign_suggestions(self, user_id: str, campaign_context: Dict[str, Any]) -> Dict[str, Any]:
        """Get AI-powered campaign suggestions based on user data"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.ai_insights_url}/api/v1/campaign-ai",
                    json={
                        "user_id": user_id,
                        "campaign_context": campaign_context,
                        "cross_domain_analysis": True
                    }
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Failed to get AI suggestions: {e}")
        return {}

# Global integration instance
superinstance = SuperInstanceIntegration()