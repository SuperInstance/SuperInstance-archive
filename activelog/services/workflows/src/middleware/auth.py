"""Authentication middleware for workflow service"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Simple authentication middleware"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for docs, health, and webhook endpoints
        skip_paths = ["/", "/docs", "/redoc", "/openapi.json", "/health", "/metrics"]
        
        if (request.url.path in skip_paths or 
            request.url.path.startswith("/webhook/") or
            request.url.path.startswith("/marketplace/")):
            response = await call_next(request)
            return response
        
        # For development, skip authentication
        # In production, implement proper JWT/token validation here
        
        response = await call_next(request)
        return response