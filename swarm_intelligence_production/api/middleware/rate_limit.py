"""
Rate limiting middleware
"""

from fastapi import HTTPException, status, Depends, Request
from datetime import datetime, timedelta
from typing import Dict
import asyncio
from collections import defaultdict

from ..models import RateLimitTier
from .auth import verify_api_key, get_api_key_tier


class RateLimiter:
    """Rate limiter with tiered limits"""

    def __init__(self):
        # Map of api_key -> [timestamps]
        self.request_log: Dict[str, list] = defaultdict(list)

        # Tier limits (requests per minute)
        self.tier_limits = {
            RateLimitTier.FREE: 60,
            RateLimitTier.PRO: 600,
            RateLimitTier.TEAM: 3000,
            RateLimitTier.ENTERPRISE: float('inf')
        }

        # Concurrent swarm limits
        self.swarm_limits = {
            RateLimitTier.FREE: 3,
            RateLimitTier.PRO: 20,
            RateLimitTier.TEAM: 100,
            RateLimitTier.ENTERPRISE: float('inf')
        }

        # Total agent limits
        self.agent_limits = {
            RateLimitTier.FREE: 30,
            RateLimitTier.PRO: 500,
            RateLimitTier.TEAM: 5000,
            RateLimitTier.ENTERPRISE: float('inf')
        }

        # Cleanup task
        asyncio.create_task(self.cleanup_old_requests())

    def get_tier_limits(self, tier: RateLimitTier) -> Dict:
        """Get all limits for tier"""
        return {
            "requests_per_minute": self.tier_limits[tier],
            "concurrent_swarms": self.swarm_limits[tier],
            "total_agents": self.agent_limits[tier]
        }

    async def check_rate_limit(
        self,
        request: Request,
        api_key: str = Depends(verify_api_key)
    ):
        """Check if request is within rate limit"""
        tier = await get_api_key_tier(api_key)
        limit = self.tier_limits[tier]

        # Enterprise has no limits
        if tier == RateLimitTier.ENTERPRISE:
            return

        # Get current minute window
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)

        # Filter requests in last minute
        recent_requests = [
            ts for ts in self.request_log[api_key]
            if ts > minute_ago
        ]

        # Check limit
        if len(recent_requests) >= limit:
            reset_time = int((recent_requests[0] + timedelta(minutes=1)).timestamp())

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(60)
                }
            )

        # Log this request
        self.request_log[api_key].append(now)

        # Add rate limit headers to response
        remaining = limit - len(recent_requests) - 1
        request.state.rate_limit_headers = {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int((now + timedelta(minutes=1)).timestamp()))
        }

    async def check_swarm_limit(self, api_key: str, current_swarm_count: int):
        """Check if user can create more swarms"""
        tier = await get_api_key_tier(api_key)
        limit = self.swarm_limits[tier]

        if current_swarm_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Swarm limit reached. Your {tier} tier allows {limit} concurrent swarms."
            )

    async def check_agent_limit(self, api_key: str, total_agent_count: int):
        """Check if user can create more agents"""
        tier = await get_api_key_tier(api_key)
        limit = self.agent_limits[tier]

        if total_agent_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent limit reached. Your {tier} tier allows {limit} total agents."
            )

    async def cleanup_old_requests(self):
        """Periodically cleanup old request logs"""
        while True:
            await asyncio.sleep(300)  # Every 5 minutes

            cutoff_time = datetime.utcnow() - timedelta(minutes=5)

            for api_key in list(self.request_log.keys()):
                self.request_log[api_key] = [
                    ts for ts in self.request_log[api_key]
                    if ts > cutoff_time
                ]

                # Remove empty entries
                if not self.request_log[api_key]:
                    del self.request_log[api_key]
