"""Authentication middleware"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware(BaseHTTPMiddleware):
    """Simple authentication middleware - to be implemented based on your auth system"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for docs and health endpoints
        if request.url.path in ["/", "/docs", "/redoc", "/openapi.json", "/health"]:
            response = await call_next(request)
            return response
        
        # For development, skip authentication
        # In production, implement proper JWT/token validation here
        
        response = await call_next(request)
        return response