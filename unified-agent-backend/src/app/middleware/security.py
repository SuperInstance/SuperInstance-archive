"""
Security headers middleware.

This module provides middleware for adding security-related HTTP headers
to responses to enhance application security.
"""

from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging import get_logger

logger = get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Security headers middleware.

    This middleware adds various security-related HTTP headers to responses
    to protect against common web vulnerabilities.
    """

    def __init__(
        self,
        app: ASGIApp,
        include_content_security_policy: bool = True,
        include_hsts: bool = True,
        include_x_frame_options: bool = True,
        include_x_content_type_options: bool = True,
        include_x_xss_protection: bool = True,
        include_referrer_policy: bool = True,
        include_permissions_policy: bool = True,
        custom_headers: dict = None,
    ) -> None:
        """
        Initialize security headers middleware.

        Args:
            app: ASGI application
            include_content_security_policy: Whether to include CSP header
            include_hsts: Whether to include HSTS header
            include_x_frame_options: Whether to include X-Frame-Options header
            include_x_content_type_options: Whether to include X-Content-Type-Options header
            include_x_xss_protection: Whether to include X-XSS-Protection header
            include_referrer_policy: Whether to include Referrer-Policy header
            include_permissions_policy: Whether to include Permissions-Policy header
            custom_headers: Additional custom headers to add
        """
        super().__init__(app)
        self.include_content_security_policy = include_content_security_policy
        self.include_hsts = include_hsts
        self.include_x_frame_options = include_x_frame_options
        self.include_x_content_type_options = include_x_content_type_options
        self.include_x_xss_protection = include_x_xss_protection
        self.include_referrer_policy = include_referrer_policy
        self.include_permissions_policy = include_permissions_policy
        self.custom_headers = custom_headers or {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: FastAPI request object
            call_next: Next middleware in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # Add security headers
        self._add_security_headers(response, request)

        return response

    def _add_security_headers(self, response: Response, request: Request) -> None:
        """
        Add security headers to response.

        Args:
            response: FastAPI response object
            request: FastAPI request object
        """
        # Content Security Policy
        if self.include_content_security_policy:
            csp_header = self._get_content_security_policy(request)
            response.headers["Content-Security-Policy"] = csp_header

        # HTTP Strict Transport Security (HSTS)
        if self.include_hsts and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # X-Frame-Options
        if self.include_x_frame_options:
            response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options
        if self.include_x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection
        if self.include_x_xss_protection:
            response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        if self.include_referrer_policy:
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature Policy)
        if self.include_permissions_policy:
            permissions_policy = self._get_permissions_policy()
            response.headers["Permissions-Policy"] = permissions_policy

        # Additional security headers
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Remove server information
        if "Server" in response.headers:
            del response.headers["Server"]

        # Add custom headers
        for header_name, header_value in self.custom_headers.items():
            response.headers[header_name] = header_value

    def _get_content_security_policy(self, request: Request) -> str:
        """
        Generate Content Security Policy header value.

        Args:
            request: FastAPI request object

        Returns:
            CSP header value
        """
        # Base CSP directives
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: https:",
            "font-src 'self' data:",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]

        # Add directives for API endpoints
        if request.url.path.startswith("/api/"):
            # More restrictive CSP for API endpoints
            directives = [
                "default-src 'self'",
                "script-src 'none'",
                "style-src 'none'",
                "img-src 'none'",
                "font-src 'none'",
                "connect-src 'self'",
                "frame-ancestors 'none'",
                "base-uri 'self'",
                "form-action 'none'",
            ]

        # Add development-specific directives
        if request.url.hostname in ["localhost", "127.0.0.1"]:
            directives.extend([
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "style-src 'self' 'unsafe-inline'",
                "connect-src 'self' ws: wss:",
            ])

        return "; ".join(directives)

    def _get_permissions_policy(self) -> str:
        """
        Generate Permissions Policy header value.

        Returns:
            Permissions Policy header value
        """
        # Disable most features for security
        policies = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=()",
            "encrypted-media=()",
            "fullscreen=()",
            "picture-in-picture=()",
            "publickey-credentials-create=()",
            "publickey-credentials-get=()",
            "screen-wake-lock=()",
            "web-share=()",
        ]

        # Allow some features for legitimate use
        allowed_policies = [
            "clipboard-read=(self)",
            "clipboard-write=(self)",
            "sync-xhr=(self)",
        ]

        return ", ".join(policies + allowed_policies)