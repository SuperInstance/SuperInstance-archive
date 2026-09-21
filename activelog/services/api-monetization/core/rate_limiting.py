import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.monetization_models import *

class RateLimitManager:
    def __init__(self):
        self.rate_limits = {
            PricingTier.FREE: RateLimitTier(
                tier=PricingTier.FREE,
                requests_per_minute=10,
                requests_per_hour=100,
                requests_per_day=1000,
                burst_allowance=5,
                overage_pricing=None
            ),
            PricingTier.BASIC: RateLimitTier(
                tier=PricingTier.BASIC,
                requests_per_minute=100,
                requests_per_hour=1000,
                requests_per_day=10000,
                burst_allowance=50,
                overage_pricing=Decimal("0.01")
            ),
            PricingTier.PRO: RateLimitTier(
                tier=PricingTier.PRO,
                requests_per_minute=1000,
                requests_per_hour=10000,
                requests_per_day=100000,
                burst_allowance=500,
                overage_pricing=Decimal("0.005")
            ),
            PricingTier.ENTERPRISE: RateLimitTier(
                tier=PricingTier.ENTERPRISE,
                requests_per_minute=10000,
                requests_per_hour=100000,
                requests_per_day=1000000,
                burst_allowance=5000,
                overage_pricing=Decimal("0.001")
            )
        }
        
        self.request_windows = {}
        self.burst_tokens = {}
        self.overage_usage = {}
        
    async def check_rate_limit(self, api_key: str, tier: PricingTier) -> RateLimitResponse:
        now = datetime.now()
        
        if api_key not in self.request_windows:
            self.request_windows[api_key] = {
                "minute": {"count": 0, "reset_time": now + timedelta(minutes=1)},
                "hour": {"count": 0, "reset_time": now + timedelta(hours=1)},
                "day": {"count": 0, "reset_time": now + timedelta(days=1)}
            }
            self.burst_tokens[api_key] = self.rate_limits[tier].burst_allowance
        
        windows = self.request_windows[api_key]
        tier_limits = self.rate_limits[tier]
        
        self._reset_windows_if_expired(api_key, now)
        
        minute_remaining = max(0, tier_limits.requests_per_minute - windows["minute"]["count"])
        hour_remaining = max(0, tier_limits.requests_per_hour - windows["hour"]["count"])
        day_remaining = max(0, tier_limits.requests_per_day - windows["day"]["count"])
        
        remaining_requests = min(minute_remaining, hour_remaining, day_remaining)
        
        allowed = remaining_requests > 0 or self.burst_tokens[api_key] > 0
        
        if allowed:
            if remaining_requests > 0:
                windows["minute"]["count"] += 1
                windows["hour"]["count"] += 1
                windows["day"]["count"] += 1
            else:
                self.burst_tokens[api_key] -= 1
                await self._record_overage_usage(api_key, tier)
        
        next_reset = min(
            windows["minute"]["reset_time"],
            windows["hour"]["reset_time"],
            windows["day"]["reset_time"]
        )
        
        upgrade_suggestion = None
        if not allowed or remaining_requests < 10:
            upgrade_suggestion = await self._get_upgrade_suggestion(tier)
        
        return RateLimitResponse(
            allowed=allowed,
            remaining_requests=remaining_requests,
            reset_time=next_reset,
            current_tier=tier,
            upgrade_suggestion=upgrade_suggestion
        )
    
    async def get_tier_limits(self, tier: PricingTier) -> RateLimitTier:
        return self.rate_limits[tier]
    
    async def update_tier_limits(self, tier: PricingTier, new_limits: RateLimitTier) -> Dict:
        old_limits = self.rate_limits[tier]
        self.rate_limits[tier] = new_limits
        
        return {
            "success": True,
            "message": f"Updated rate limits for {tier}",
            "old_limits": old_limits,
            "new_limits": new_limits,
            "updated_at": datetime.now()
        }
    
    async def get_usage_stats(self, api_key: str, tier: PricingTier) -> Dict:
        if api_key not in self.request_windows:
            return {
                "current_usage": {"minute": 0, "hour": 0, "day": 0},
                "limits": self.rate_limits[tier],
                "burst_tokens_remaining": self.rate_limits[tier].burst_allowance,
                "overage_usage": 0,
                "overage_cost": Decimal("0.00")
            }
        
        windows = self.request_windows[api_key]
        tier_limits = self.rate_limits[tier]
        
        overage = self.overage_usage.get(api_key, 0)
        overage_cost = Decimal("0.00")
        if tier_limits.overage_pricing:
            overage_cost = Decimal(str(overage)) * tier_limits.overage_pricing
        
        return {
            "current_usage": {
                "minute": windows["minute"]["count"],
                "hour": windows["hour"]["count"], 
                "day": windows["day"]["count"]
            },
            "limits": tier_limits,
            "burst_tokens_remaining": self.burst_tokens.get(api_key, tier_limits.burst_allowance),
            "overage_usage": overage,
            "overage_cost": overage_cost,
            "window_reset_times": {
                "minute": windows["minute"]["reset_time"],
                "hour": windows["hour"]["reset_time"],
                "day": windows["day"]["reset_time"]
            }
        }
    
    async def reset_burst_tokens(self, api_key: str, tier: PricingTier):
        self.burst_tokens[api_key] = self.rate_limits[tier].burst_allowance
    
    async def whitelist_api_key(self, api_key: str, duration_hours: int = 24) -> Dict:
        expiry = datetime.now() + timedelta(hours=duration_hours)
        
        if not hasattr(self, 'whitelisted_keys'):
            self.whitelisted_keys = {}
        
        self.whitelisted_keys[api_key] = expiry
        
        return {
            "success": True,
            "message": f"API key whitelisted for {duration_hours} hours",
            "expires_at": expiry
        }
    
    async def is_whitelisted(self, api_key: str) -> bool:
        if not hasattr(self, 'whitelisted_keys'):
            return False
        
        if api_key not in self.whitelisted_keys:
            return False
        
        if datetime.now() > self.whitelisted_keys[api_key]:
            del self.whitelisted_keys[api_key]
            return False
        
        return True
    
    async def apply_temporary_limit(self, api_key: str, tier: PricingTier, 
                                   multiplier: float, duration_hours: int = 1) -> Dict:
        if not hasattr(self, 'temporary_limits'):
            self.temporary_limits = {}
        
        base_limits = self.rate_limits[tier]
        temp_limits = RateLimitTier(
            tier=tier,
            requests_per_minute=int(base_limits.requests_per_minute * multiplier),
            requests_per_hour=int(base_limits.requests_per_hour * multiplier),
            requests_per_day=int(base_limits.requests_per_day * multiplier),
            burst_allowance=int(base_limits.burst_allowance * multiplier),
            overage_pricing=base_limits.overage_pricing
        )
        
        expiry = datetime.now() + timedelta(hours=duration_hours)
        
        self.temporary_limits[api_key] = {
            "limits": temp_limits,
            "expires_at": expiry
        }
        
        return {
            "success": True,
            "message": f"Temporary limits applied with {multiplier}x multiplier for {duration_hours} hours",
            "temporary_limits": temp_limits,
            "expires_at": expiry
        }
    
    def _reset_windows_if_expired(self, api_key: str, now: datetime):
        windows = self.request_windows[api_key]
        
        if now >= windows["minute"]["reset_time"]:
            windows["minute"]["count"] = 0
            windows["minute"]["reset_time"] = now + timedelta(minutes=1)
        
        if now >= windows["hour"]["reset_time"]:
            windows["hour"]["count"] = 0
            windows["hour"]["reset_time"] = now + timedelta(hours=1)
        
        if now >= windows["day"]["reset_time"]:
            windows["day"]["count"] = 0
            windows["day"]["reset_time"] = now + timedelta(days=1)
            self.overage_usage[api_key] = 0
    
    async def _record_overage_usage(self, api_key: str, tier: PricingTier):
        if api_key not in self.overage_usage:
            self.overage_usage[api_key] = 0
        self.overage_usage[api_key] += 1
    
    async def _get_upgrade_suggestion(self, current_tier: PricingTier) -> Optional[str]:
        suggestions = {
            PricingTier.FREE: "Upgrade to Basic tier for 10x more requests and burst capacity",
            PricingTier.BASIC: "Upgrade to Pro tier for 10x more requests and lower overage costs",
            PricingTier.PRO: "Upgrade to Enterprise tier for maximum capacity and lowest costs",
            PricingTier.ENTERPRISE: None
        }
        return suggestions.get(current_tier)
    
    async def get_tier_comparison(self) -> Dict:
        return {
            "tiers": [
                {
                    "tier": tier.value,
                    "requests_per_minute": limits.requests_per_minute,
                    "requests_per_hour": limits.requests_per_hour,
                    "requests_per_day": limits.requests_per_day,
                    "burst_allowance": limits.burst_allowance,
                    "overage_pricing": str(limits.overage_pricing) if limits.overage_pricing else "N/A"
                }
                for tier, limits in self.rate_limits.items()
            ]
        }

rate_limit_manager = RateLimitManager()