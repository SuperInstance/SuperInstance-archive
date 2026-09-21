"""
Security middleware for ActiveLog services
Provides common security headers and protections
"""

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from typing import Callable

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "connect-src 'self' ws: wss:"
        )
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        return response

def add_security_headers(app):
    """Add security middleware to FastAPI app"""
    app.add_middleware(SecurityHeadersMiddleware)
