"""
ActiveLog Authentication Client
Simple client library for interacting with the authentication service from other services
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, List
import httpx
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AuthConfig:
    """Authentication service configuration"""
    auth_service_url: str = "http://localhost:8080"
    timeout: float = 5.0
    cache_ttl: int = 300  # 5 minutes
    
class AuthClient:
    """Client for ActiveLog Authentication Service"""
    
    def __init__(self, config: Optional[AuthConfig] = None):
        self.config = config or AuthConfig()
        self.base_url = self.config.auth_service_url.rstrip('/')
        self.token_cache = {}
        
    async def register_user(self, email: str, password: str, username: str, full_name: str) -> Optional[Dict[str, Any]]:
        """Register a new user"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/register",
                    json={
                        "email": email,
                        "password": password,
                        "username": username,
                        "full_name": full_name
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Registration failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Registration error: {e}")
            
        return None
    
    async def login_user(self, email: str, password: str, remember_me: bool = False) -> Optional[Dict[str, Any]]:
        """Login user and get tokens"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/login",
                    json={
                        "email": email,
                        "password": password,
                        "remember_me": remember_me
                    },
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Login failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Login error: {e}")
            
        return None
    
    async def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        """Refresh access token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/refresh",
                    json={"refresh_token": refresh_token},
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                    
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            
        return None
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and get user info"""
        
        # Check cache first
        cache_key = f"token_{hash(token)}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/validate-token",
                    json={"token": token},
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        user = data.get("user")
                        # Cache the result
                        self._cache_result(cache_key, user)
                        return user
                    else:
                        # Cache invalid result too (but for shorter time)
                        self._cache_result(cache_key, None, ttl=60)
                        
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            
        return None
    
    async def get_user_profile(self, token: str) -> Optional[Dict[str, Any]]:
        """Get current user profile"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/me",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    return response.json()
                    
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            
        return None
    
    async def grant_service_access(self, token: str, service_name: str) -> bool:
        """Grant current user access to a service"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/grant-service/{service_name}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.config.timeout
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Grant service access error: {e}")
            
        return False
    
    async def logout_user(self, token: str) -> bool:
        """Logout user"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/logout",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.config.timeout
                )
                
                # Clear cache for this token
                cache_key = f"token_{hash(token)}"
                if cache_key in self.token_cache:
                    del self.token_cache[cache_key]
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Logout error: {e}")
            
        return False
    
    async def health_check(self) -> bool:
        """Check if authentication service is healthy"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/health",
                    timeout=self.config.timeout
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Health check error: {e}")
            
        return False
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached result"""
        if cache_key in self.token_cache:
            cached_data = self.token_cache[cache_key]
            if time.time() - cached_data["timestamp"] < cached_data["ttl"]:
                return cached_data["data"]
            else:
                # Remove expired cache entry
                del self.token_cache[cache_key]
        return None
    
    def _cache_result(self, cache_key: str, data: Any, ttl: Optional[int] = None):
        """Cache result"""
        if ttl is None:
            ttl = self.config.cache_ttl
            
        self.token_cache[cache_key] = {
            "data": data,
            "timestamp": time.time(),
            "ttl": ttl
        }
        
        # Simple cache cleanup
        if len(self.token_cache) > 1000:
            oldest_key = min(self.token_cache.keys(), 
                           key=lambda k: self.token_cache[k]["timestamp"])
            del self.token_cache[oldest_key]

class SimpleAuthDecorator:
    """Simple authentication decorator for functions"""
    
    def __init__(self, auth_client: AuthClient):
        self.auth_client = auth_client
    
    def require_auth(self, func):
        """Decorator that requires valid authentication"""
        async def wrapper(*args, **kwargs):
            # Look for token in kwargs
            token = kwargs.get('token') or kwargs.get('auth_token')
            
            if not token:
                raise ValueError("Authentication token required")
            
            user = await self.auth_client.validate_token(token)
            if not user:
                raise ValueError("Invalid or expired authentication token")
            
            # Add user to kwargs
            kwargs['current_user'] = user
            
            return await func(*args, **kwargs)
        
        return wrapper
    
    def require_service(self, service_name: str):
        """Decorator that requires access to a specific service"""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Look for token in kwargs
                token = kwargs.get('token') or kwargs.get('auth_token')
                
                if not token:
                    raise ValueError("Authentication token required")
                
                user = await self.auth_client.validate_token(token)
                if not user:
                    raise ValueError("Invalid or expired authentication token")
                
                # Check service access
                user_services = user.get('services', [])
                if service_name not in user_services:
                    raise ValueError(f"Access to {service_name} service is required")
                
                # Add user to kwargs
                kwargs['current_user'] = user
                
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator

# Utility functions
def create_auth_client(auth_service_url: str = "http://localhost:8080") -> AuthClient:
    """Create an authentication client"""
    config = AuthConfig(auth_service_url=auth_service_url)
    return AuthClient(config)

async def quick_login(email: str, password: str, auth_service_url: str = "http://localhost:8080") -> Optional[str]:
    """Quick login function that returns just the access token"""
    client = create_auth_client(auth_service_url)
    result = await client.login_user(email, password)
    
    if result:
        return result.get('access_token')
    
    return None

async def quick_validate(token: str, auth_service_url: str = "http://localhost:8080") -> Optional[Dict[str, Any]]:
    """Quick token validation function"""
    client = create_auth_client(auth_service_url)
    return await client.validate_token(token)

# Synchronous versions for non-async code
def sync_login(email: str, password: str, auth_service_url: str = "http://localhost:8080") -> Optional[str]:
    """Synchronous login function"""
    return asyncio.run(quick_login(email, password, auth_service_url))

def sync_validate(token: str, auth_service_url: str = "http://localhost:8080") -> Optional[Dict[str, Any]]:
    """Synchronous token validation function"""
    return asyncio.run(quick_validate(token, auth_service_url))

# Example usage
if __name__ == "__main__":
    async def example():
        # Create client
        client = create_auth_client()
        
        # Check if service is healthy
        if not await client.health_check():
            print("Authentication service is not available")
            return
        
        # Register a test user
        print("Registering test user...")
        register_result = await client.register_user(
            email="test@example.com",
            password="TestPassword123!",
            username="testuser",
            full_name="Test User"
        )
        
        if register_result:
            print(f"Registration successful: {register_result['user']['username']}")
            
            # Test token validation
            token = register_result['access_token']
            user = await client.validate_token(token)
            
            if user:
                print(f"Token validation successful: {user['username']}")
            else:
                print("Token validation failed")
        else:
            print("Registration failed")
    
    # Run example
    asyncio.run(example())