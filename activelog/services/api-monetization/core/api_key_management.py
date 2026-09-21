import asyncio
import secrets
import string
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from models.monetization_models import *

class APIKeyManager:
    def __init__(self):
        self.api_keys = {}
        self.developer_keys = {}
        self.key_permissions = {}
        self.key_usage_stats = {}
        
    async def generate_api_key(self, request: APIKeyRequest) -> APIKeyResponse:
        api_key = self._generate_secure_key()
        key_id = str(uuid.uuid4())
        
        default_rate_limits = {
            PricingTier.FREE: 100,
            PricingTier.BASIC: 1000,
            PricingTier.PRO: 10000,
            PricingTier.ENTERPRISE: 100000
        }
        
        rate_limit = request.rate_limit or default_rate_limits[request.tier]
        
        key_data = {
            "key_id": key_id,
            "api_key": api_key,
            "developer_id": request.developer_id,
            "api_name": request.api_name,
            "tier": request.tier,
            "permissions": request.permissions,
            "rate_limit": rate_limit,
            "status": APIKeyStatus.ACTIVE,
            "created_at": datetime.now(),
            "expires_at": request.expires_at,
            "last_used": None,
            "usage_count": 0
        }
        
        self.api_keys[api_key] = key_data
        
        if request.developer_id not in self.developer_keys:
            self.developer_keys[request.developer_id] = []
        self.developer_keys[request.developer_id].append(api_key)
        
        self.key_permissions[api_key] = set(request.permissions)
        self.key_usage_stats[api_key] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_24h_requests": 0,
            "bandwidth_used": 0
        }
        
        return APIKeyResponse(
            api_key=api_key,
            developer_id=request.developer_id,
            api_name=request.api_name,
            tier=request.tier,
            permissions=request.permissions,
            rate_limit=rate_limit,
            status=APIKeyStatus.ACTIVE,
            created_at=key_data["created_at"],
            expires_at=request.expires_at,
            last_used=None
        )
    
    async def validate_api_key(self, api_key: str) -> Dict:
        if api_key not in self.api_keys:
            return {
                "valid": False,
                "reason": "API key not found",
                "key_data": None
            }
        
        key_data = self.api_keys[api_key]
        
        if key_data["status"] != APIKeyStatus.ACTIVE:
            return {
                "valid": False,
                "reason": f"API key status: {key_data['status']}",
                "key_data": key_data
            }
        
        if key_data["expires_at"] and datetime.now() > key_data["expires_at"]:
            await self._update_key_status(api_key, APIKeyStatus.EXPIRED)
            return {
                "valid": False,
                "reason": "API key expired",
                "key_data": key_data
            }
        
        await self._update_last_used(api_key)
        
        return {
            "valid": True,
            "reason": "Valid API key",
            "key_data": key_data
        }
    
    async def check_permission(self, api_key: str, required_permission: str) -> bool:
        if api_key not in self.key_permissions:
            return False
        
        permissions = self.key_permissions[api_key]
        return required_permission in permissions or "*" in permissions
    
    async def revoke_api_key(self, api_key: str, reason: str = "User revoked") -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        await self._update_key_status(api_key, APIKeyStatus.REVOKED)
        
        return {
            "success": True,
            "message": f"API key revoked: {reason}",
            "revoked_at": datetime.now()
        }
    
    async def suspend_api_key(self, api_key: str, reason: str = "Suspended by admin") -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        await self._update_key_status(api_key, APIKeyStatus.SUSPENDED)
        
        return {
            "success": True,
            "message": f"API key suspended: {reason}",
            "suspended_at": datetime.now()
        }
    
    async def reactivate_api_key(self, api_key: str) -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        key_data = self.api_keys[api_key]
        
        if key_data["status"] == APIKeyStatus.REVOKED:
            return {
                "success": False,
                "message": "Cannot reactivate revoked API key"
            }
        
        await self._update_key_status(api_key, APIKeyStatus.ACTIVE)
        
        return {
            "success": True,
            "message": "API key reactivated",
            "reactivated_at": datetime.now()
        }
    
    async def update_api_key_permissions(self, api_key: str, new_permissions: List[str]) -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        self.api_keys[api_key]["permissions"] = new_permissions
        self.key_permissions[api_key] = set(new_permissions)
        
        return {
            "success": True,
            "message": "Permissions updated",
            "new_permissions": new_permissions,
            "updated_at": datetime.now()
        }
    
    async def update_api_key_tier(self, api_key: str, new_tier: PricingTier) -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        old_tier = self.api_keys[api_key]["tier"]
        self.api_keys[api_key]["tier"] = new_tier
        
        new_rate_limits = {
            PricingTier.FREE: 100,
            PricingTier.BASIC: 1000,
            PricingTier.PRO: 10000,
            PricingTier.ENTERPRISE: 100000
        }
        
        self.api_keys[api_key]["rate_limit"] = new_rate_limits[new_tier]
        
        return {
            "success": True,
            "message": f"Tier updated from {old_tier} to {new_tier}",
            "old_tier": old_tier,
            "new_tier": new_tier,
            "new_rate_limit": new_rate_limits[new_tier],
            "updated_at": datetime.now()
        }
    
    async def get_developer_keys(self, developer_id: str) -> List[APIKeyResponse]:
        if developer_id not in self.developer_keys:
            return []
        
        keys = []
        for api_key in self.developer_keys[developer_id]:
            key_data = self.api_keys[api_key]
            keys.append(APIKeyResponse(
                api_key=api_key,
                developer_id=key_data["developer_id"],
                api_name=key_data["api_name"],
                tier=key_data["tier"],
                permissions=key_data["permissions"],
                rate_limit=key_data["rate_limit"],
                status=key_data["status"],
                created_at=key_data["created_at"],
                expires_at=key_data["expires_at"],
                last_used=key_data["last_used"]
            ))
        
        return keys
    
    async def get_key_usage_stats(self, api_key: str) -> Dict:
        if api_key not in self.key_usage_stats:
            return {}
        
        stats = self.key_usage_stats[api_key].copy()
        stats["key_info"] = self.api_keys.get(api_key, {})
        
        return stats
    
    async def record_key_usage(self, api_key: str, success: bool = True, bandwidth: int = 0):
        if api_key not in self.key_usage_stats:
            return
        
        stats = self.key_usage_stats[api_key]
        stats["total_requests"] += 1
        
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
        
        stats["bandwidth_used"] += bandwidth
        
        self.api_keys[api_key]["usage_count"] += 1
    
    async def rotate_api_key(self, api_key: str) -> Dict:
        if api_key not in self.api_keys:
            return {
                "success": False,
                "message": "API key not found"
            }
        
        old_key_data = self.api_keys[api_key]
        new_api_key = self._generate_secure_key()
        
        new_key_data = old_key_data.copy()
        new_key_data["api_key"] = new_api_key
        new_key_data["created_at"] = datetime.now()
        
        self.api_keys[new_api_key] = new_key_data
        self.key_permissions[new_api_key] = self.key_permissions[api_key]
        self.key_usage_stats[new_api_key] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_24h_requests": 0,
            "bandwidth_used": 0
        }
        
        developer_id = old_key_data["developer_id"]
        if developer_id in self.developer_keys:
            self.developer_keys[developer_id].remove(api_key)
            self.developer_keys[developer_id].append(new_api_key)
        
        await self._update_key_status(api_key, APIKeyStatus.REVOKED)
        
        return {
            "success": True,
            "old_api_key": api_key,
            "new_api_key": new_api_key,
            "rotated_at": datetime.now(),
            "message": "API key rotated successfully"
        }
    
    def _generate_secure_key(self) -> str:
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        return f"ak_{key}"
    
    async def _update_key_status(self, api_key: str, status: APIKeyStatus):
        if api_key in self.api_keys:
            self.api_keys[api_key]["status"] = status
    
    async def _update_last_used(self, api_key: str):
        if api_key in self.api_keys:
            self.api_keys[api_key]["last_used"] = datetime.now()

api_key_manager = APIKeyManager()