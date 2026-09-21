"""
ActiveLog Authentication Middleware
For integration with other ActiveLog services

Usage:
    from auth_service.middleware import AuthMiddleware, get_current_user
    
    app.add_middleware(AuthMiddleware, auth_service_url="http://localhost:8080")
    
    @app.get("/protected")
    def protected_route(current_user: dict = Depends(get_current_user)):
        return {"message": f"Hello {current_user['username']}"}
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
import httpx
from fastapi import FastAPI, Request, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from functools import lru_cache

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for ActiveLog services"""
    
    def __init__(self, app: FastAPI, auth_service_url: str = "http://localhost:8080", 
                 cache_ttl: int = 300):
        super().__init__(app)
        self.auth_service_url = auth_service_url.rstrip('/')
        self.cache_ttl = cache_ttl  # 5 minutes default
        self.token_cache = {}  # Simple in-memory cache
        
    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication if needed"""
        
        # Skip auth for public endpoints
        if self.is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=401,
                content={"error": "Authorization header required"}
            )
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return JSONResponse(
                    status_code=401,
                    content={"error": "Invalid authorization scheme"}
                )
        except ValueError:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid authorization header format"}
            )
        
        # Validate token
        user = await self.validate_token(token)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"error": "Invalid or expired token"}
            )
        
        # Add user info to request state
        request.state.current_user = user
        
        return await call_next(request)
    
    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint should be publicly accessible"""
        public_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/api/register",
            "/api/login",
            "/api/refresh"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate token with auth service (with caching)"""
        
        # Check cache first
        cache_key = f"token:{token[:20]}..."  # Use partial token as key for security
        cached_result = self.get_cached_token(cache_key)
        if cached_result:
            return cached_result
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/validate-token",
                    json={"token": token},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        user = data.get("user")
                        # Cache the result
                        self.cache_token(cache_key, user)
                        return user
                
        except Exception as e:
            logger.error(f"Token validation error: {e}")
        
        return None
    
    def get_cached_token(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached token validation result"""
        if cache_key in self.token_cache:
            cached_data = self.token_cache[cache_key]
            if time.time() - cached_data["timestamp"] < self.cache_ttl:
                return cached_data["user"]
            else:
                # Remove expired cache entry
                del self.token_cache[cache_key]
        return None
    
    def cache_token(self, cache_key: str, user: Dict[str, Any]):
        """Cache token validation result"""
        self.token_cache[cache_key] = {
            "user": user,
            "timestamp": time.time()
        }
        
        # Simple cache cleanup - remove oldest entries if cache gets too large
        if len(self.token_cache) > 1000:
            oldest_key = min(self.token_cache.keys(), 
                           key=lambda k: self.token_cache[k]["timestamp"])
            del self.token_cache[oldest_key]

class AuthDependency:
    """Authentication dependency for FastAPI routes"""
    
    def __init__(self, auth_service_url: str = "http://localhost:8080"):
        self.auth_service_url = auth_service_url.rstrip('/')
        self.security = HTTPBearer()
    
    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Validate token and return current user"""
        token = credentials.credentials
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/validate-token",
                    json={"token": token},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        return data.get("user")
        
        except Exception as e:
            logger.error(f"Token validation error: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Global instances for easy import
auth_dependency = AuthDependency()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Dependency to get current authenticated user"""
    return auth_dependency(credentials)

async def get_current_user_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """Get current user from request state (when using middleware)"""
    return getattr(request.state, 'current_user', None)

def require_service_access(service_name: str):
    """Decorator to require access to specific service"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Get current user from request or dependency
            current_user = None
            
            # Try to get from request state first (middleware)
            request = kwargs.get('request') or args[0] if args else None
            if hasattr(request, 'state'):
                current_user = getattr(request.state, 'current_user', None)
            
            # If not found, try dependency injection
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check service access
            user_services = current_user.get('services', [])
            if service_name not in user_services:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to {service_name} service is required"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

# Utility functions for service integration

class AuthServiceClient:
    """Client for interacting with the authentication service"""
    
    def __init__(self, auth_service_url: str = "http://localhost:8080"):
        self.auth_service_url = auth_service_url.rstrip('/')
    
    async def validate_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate a JWT token"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/validate-token",
                    json={"token": token},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("valid"):
                        return data.get("user")
        except Exception as e:
            logger.error(f"Token validation error: {e}")
        
        return None
    
    async def get_user_profile(self, user_id: str, admin_token: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID (requires admin token)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.auth_service_url}/api/users/{user_id}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=5.0
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
        
        return None
    
    async def grant_service_access(self, user_id: str, service_name: str, admin_token: str) -> bool:
        """Grant user access to a service (requires admin token)"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.auth_service_url}/api/users/{user_id}/services/{service_name}",
                    headers={"Authorization": f"Bearer {admin_token}"},
                    timeout=5.0
                )
                
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Grant service access error: {e}")
            
        return False

# Example service integration
def setup_auth_for_service(app: FastAPI, service_name: str, auth_service_url: str = "http://localhost:8080"):
    """
    Setup authentication for a service
    
    Usage:
        from auth_service.middleware import setup_auth_for_service
        
        app = FastAPI(title="My Service")
        setup_auth_for_service(app, "my-service")
    """
    
    # Add middleware
    app.add_middleware(AuthMiddleware, auth_service_url=auth_service_url)
    
    # Add helper endpoints
    @app.get("/api/auth/me")
    async def get_current_user_endpoint(request: Request):
        """Get current authenticated user"""
        user = await get_current_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return user
    
    @app.post("/api/auth/grant-access")
    async def grant_service_access_endpoint(request: Request):
        """Grant current user access to this service"""
        user = await get_current_user_from_request(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # This would typically be done automatically or by an admin
        # For now, we'll auto-grant access
        try:
            client = AuthServiceClient(auth_service_url)
            # In a real implementation, you'd need an admin token
            success = await client.grant_service_access(user['id'], service_name, "admin_token")
            if success:
                return {"message": f"Access granted to {service_name}"}
            else:
                raise HTTPException(status_code=500, detail="Failed to grant access")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

# Simple authentication helper for non-FastAPI services
def create_auth_headers(token: str) -> Dict[str, str]:
    """Create authentication headers for API requests"""
    return {"Authorization": f"Bearer {token}"}

def extract_user_from_token(token: str, auth_service_url: str = "http://localhost:8080") -> Optional[Dict[str, Any]]:
    """Extract user information from JWT token (synchronous)"""
    import asyncio
    
    async def _validate():
        client = AuthServiceClient(auth_service_url)
        return await client.validate_token(token)
    
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_validate())
    except RuntimeError:
        # No event loop running, create one
        return asyncio.run(_validate())