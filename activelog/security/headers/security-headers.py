#!/usr/bin/env python3

import json
import logging
import os
import re
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from fastapi import FastAPI, Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
import yaml

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SecurityHeadersConfig:
    # Content Security Policy
    csp_enabled: bool = True
    csp_directives: Dict[str, List[str]] = None
    csp_report_only: bool = False
    csp_report_uri: Optional[str] = None
    
    # HTTP Strict Transport Security
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    
    # X-Frame-Options
    x_frame_options: str = "DENY"  # DENY, SAMEORIGIN, or ALLOW-FROM uri
    
    # X-Content-Type-Options
    x_content_type_options: bool = True
    
    # X-XSS-Protection
    x_xss_protection: str = "1; mode=block"
    
    # Referrer Policy
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Permissions Policy (Feature Policy)
    permissions_policy_enabled: bool = True
    permissions_policy_directives: Dict[str, List[str]] = None
    
    # Cross-Origin Resource Sharing (CORS)
    cors_enabled: bool = True
    cors_allow_origins: List[str] = None
    cors_allow_methods: List[str] = None
    cors_allow_headers: List[str] = None
    cors_allow_credentials: bool = False
    cors_max_age: int = 86400
    
    # Cross-Origin Embedder Policy
    coep_enabled: bool = True
    coep_value: str = "require-corp"
    
    # Cross-Origin Opener Policy
    coop_enabled: bool = True
    coop_value: str = "same-origin"
    
    # Cross-Origin Resource Policy
    corp_enabled: bool = True
    corp_value: str = "same-origin"
    
    # Additional security headers
    server_header: Optional[str] = None  # Remove or customize server header
    x_powered_by: bool = False  # Remove X-Powered-By header
    
    # Environment-specific settings
    environment: str = "production"  # production, staging, development

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, config: SecurityHeadersConfig):
        super().__init__(app)
        self.config = config
        self.csp_cache = {}
        
    async def dispatch(self, request: Request, call_next):
        # Process request
        response = await call_next(request)
        
        # Apply security headers
        self._apply_security_headers(request, response)
        
        return response
    
    def _apply_security_headers(self, request: Request, response: Response):
        """Apply all configured security headers to the response."""
        
        # Content Security Policy
        if self.config.csp_enabled:
            csp_header = self._build_csp_header(request)
            if csp_header:
                header_name = "Content-Security-Policy-Report-Only" if self.config.csp_report_only else "Content-Security-Policy"
                response.headers[header_name] = csp_header
        
        # HTTP Strict Transport Security
        if self.config.hsts_enabled and request.url.scheme == "https":
            hsts_value = f"max-age={self.config.hsts_max_age}"
            if self.config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if self.config.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # X-Frame-Options
        if self.config.x_frame_options:
            response.headers["X-Frame-Options"] = self.config.x_frame_options
        
        # X-Content-Type-Options
        if self.config.x_content_type_options:
            response.headers["X-Content-Type-Options"] = "nosniff"
        
        # X-XSS-Protection
        if self.config.x_xss_protection:
            response.headers["X-XSS-Protection"] = self.config.x_xss_protection
        
        # Referrer Policy
        if self.config.referrer_policy:
            response.headers["Referrer-Policy"] = self.config.referrer_policy
        
        # Permissions Policy
        if self.config.permissions_policy_enabled:
            permissions_policy = self._build_permissions_policy()
            if permissions_policy:
                response.headers["Permissions-Policy"] = permissions_policy
        
        # Cross-Origin Embedder Policy
        if self.config.coep_enabled:
            response.headers["Cross-Origin-Embedder-Policy"] = self.config.coep_value
        
        # Cross-Origin Opener Policy
        if self.config.coop_enabled:
            response.headers["Cross-Origin-Opener-Policy"] = self.config.coop_value
        
        # Cross-Origin Resource Policy
        if self.config.corp_enabled:
            response.headers["Cross-Origin-Resource-Policy"] = self.config.corp_value
        
        # Remove/customize server headers
        if self.config.server_header is not None:
            if self.config.server_header:
                response.headers["Server"] = self.config.server_header
            else:
                response.headers.pop("Server", None)
        
        # Remove X-Powered-By header
        if not self.config.x_powered_by:
            response.headers.pop("X-Powered-By", None)
        
        # CORS headers (if not handled by CORS middleware)
        if self.config.cors_enabled and not hasattr(response, '_cors_headers_applied'):
            self._apply_cors_headers(request, response)
    
    def _build_csp_header(self, request: Request) -> str:
        """Build Content Security Policy header value."""
        if not self.config.csp_directives:
            return self._get_default_csp(request)
        
        directives = []
        for directive, sources in self.config.csp_directives.items():
            if sources:
                directive_value = f"{directive} {' '.join(sources)}"
                directives.append(directive_value)
        
        csp_value = "; ".join(directives)
        
        # Add report-uri if specified
        if self.config.csp_report_uri:
            csp_value += f"; report-uri {self.config.csp_report_uri}"
        
        return csp_value
    
    def _get_default_csp(self, request: Request) -> str:
        """Get default CSP based on environment and request context."""
        base_csp = {
            "default-src": ["'self'"],
            "script-src": ["'self'", "'unsafe-inline'"] if self.config.environment == "development" else ["'self'"],
            "style-src": ["'self'", "'unsafe-inline'"],
            "img-src": ["'self'", "data:", "https:"],
            "font-src": ["'self'", "https://fonts.gstatic.com"],
            "connect-src": ["'self'"],
            "frame-ancestors": ["'none'"],
            "base-uri": ["'self'"],
            "form-action": ["'self'"],
            "upgrade-insecure-requests": []
        }
        
        # Environment-specific adjustments
        if self.config.environment == "development":
            base_csp["connect-src"].extend(["ws:", "wss:"])  # For hot reload
            base_csp["script-src"].append("'unsafe-eval'")  # For development tools
        
        # Build CSP string
        directives = []
        for directive, sources in base_csp.items():
            if sources:
                directive_value = f"{directive} {' '.join(sources)}"
            else:
                directive_value = directive
            directives.append(directive_value)
        
        return "; ".join(directives)
    
    def _build_permissions_policy(self) -> str:
        """Build Permissions Policy header value."""
        if not self.config.permissions_policy_directives:
            return self._get_default_permissions_policy()
        
        directives = []
        for feature, allowlist in self.config.permissions_policy_directives.items():
            if allowlist:
                directive_value = f"{feature}=({' '.join(allowlist)})"
            else:
                directive_value = f"{feature}=()"
            directives.append(directive_value)
        
        return ", ".join(directives)
    
    def _get_default_permissions_policy(self) -> str:
        """Get default Permissions Policy."""
        default_policy = {
            "accelerometer": [],
            "ambient-light-sensor": [],
            "autoplay": ["'self'"],
            "camera": [],
            "encrypted-media": ["'self'"],
            "fullscreen": ["'self'"],
            "geolocation": [],
            "gyroscope": [],
            "magnetometer": [],
            "microphone": [],
            "midi": [],
            "payment": [],
            "picture-in-picture": ["'self'"],
            "usb": [],
            "vr": []
        }
        
        directives = []
        for feature, allowlist in default_policy.items():
            if allowlist:
                directive_value = f"{feature}=({' '.join(allowlist)})"
            else:
                directive_value = f"{feature}=()"
            directives.append(directive_value)
        
        return ", ".join(directives)
    
    def _apply_cors_headers(self, request: Request, response: Response):
        """Apply CORS headers if enabled."""
        origin = request.headers.get("Origin")
        
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif not origin and self.config.cors_allow_origins and "*" in self.config.cors_allow_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        if self.config.cors_allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        if self.config.cors_allow_methods:
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.config.cors_allow_methods)
        
        if self.config.cors_allow_headers:
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.config.cors_allow_headers)
        
        response.headers["Access-Control-Max-Age"] = str(self.config.cors_max_age)
        
        # Mark CORS headers as applied
        setattr(response, '_cors_headers_applied', True)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed by CORS configuration."""
        if not self.config.cors_allow_origins:
            return False
        
        if "*" in self.config.cors_allow_origins:
            return True
        
        for allowed_origin in self.config.cors_allow_origins:
            if origin == allowed_origin:
                return True
            # Support wildcard subdomains (e.g., *.example.com)
            if allowed_origin.startswith("*."):
                domain = allowed_origin[2:]
                if origin.endswith(f".{domain}") or origin == domain:
                    return True
        
        return False

class SecurityHeadersService:
    def __init__(self, config_file: str = "configs/security-headers.yaml"):
        self.app = FastAPI(title="ActiveLog Security Headers Service")
        self.config = self._load_config(config_file)
        self._setup_routes()
    
    def _load_config(self, config_file: str) -> SecurityHeadersConfig:
        """Load security headers configuration."""
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                return SecurityHeadersConfig(**config_data)
            else:
                logger.warning(f"Config file not found: {config_file}, using defaults")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> SecurityHeadersConfig:
        """Get default security headers configuration."""
        return SecurityHeadersConfig(
            csp_directives={
                "default-src": ["'self'"],
                "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
                "style-src": ["'self'", "'unsafe-inline'"],
                "img-src": ["'self'", "data:", "https:"],
                "font-src": ["'self'", "https://fonts.gstatic.com"],
                "connect-src": ["'self'", "wss:", "ws:"],
                "frame-ancestors": ["'none'"],
                "base-uri": ["'self'"],
                "form-action": ["'self'"]
            },
            permissions_policy_directives={
                "accelerometer": [],
                "camera": [],
                "geolocation": [],
                "microphone": [],
                "payment": [],
                "autoplay": ["'self'"],
                "fullscreen": ["'self'"]
            },
            cors_allow_origins=["http://localhost:3000", "https://activelog.com"],
            cors_allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            cors_allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
            environment=os.getenv("ENVIRONMENT", "production")
        )
    
    def get_middleware(self) -> SecurityHeadersMiddleware:
        """Get the security headers middleware instance."""
        return SecurityHeadersMiddleware(self.app, self.config)
    
    def _setup_routes(self):
        """Set up API routes for security headers management."""
        
        @self.app.get("/api/v1/security-headers/config")
        async def get_config():
            """Get current security headers configuration."""
            return {
                "csp_enabled": self.config.csp_enabled,
                "csp_report_only": self.config.csp_report_only,
                "hsts_enabled": self.config.hsts_enabled,
                "hsts_max_age": self.config.hsts_max_age,
                "x_frame_options": self.config.x_frame_options,
                "referrer_policy": self.config.referrer_policy,
                "environment": self.config.environment
            }
        
        @self.app.post("/api/v1/security-headers/test")
        async def test_headers(request: Request):
            """Test endpoint to verify security headers."""
            return {
                "message": "Security headers test endpoint",
                "request_url": str(request.url),
                "user_agent": request.headers.get("User-Agent"),
                "origin": request.headers.get("Origin")
            }
        
        @self.app.get("/api/v1/security-headers/csp-report")
        async def csp_report_endpoint(request: Request):
            """Endpoint for CSP violation reports."""
            try:
                report_data = await request.json()
                logger.warning("CSP Violation Report", extra={"csp_report": report_data})
                
                # Store report in database or send alert
                # Implementation depends on your monitoring system
                
                return {"status": "received"}
            except Exception as e:
                logger.error(f"CSP report processing failed: {e}")
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid report format"}
                )
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "service": "security-headers",
                "version": "1.0.0"
            }

# Nginx configuration generator
class NginxSecurityConfig:
    @staticmethod
    def generate_nginx_config(config: SecurityHeadersConfig) -> str:
        """Generate Nginx configuration for security headers."""
        nginx_config = []
        
        # Security headers block
        nginx_config.append("# ActiveLog Security Headers Configuration")
        nginx_config.append("add_header X-Content-Type-Options nosniff always;")
        nginx_config.append("add_header X-Frame-Options DENY always;")
        nginx_config.append("add_header X-XSS-Protection '1; mode=block' always;")
        nginx_config.append(f"add_header Referrer-Policy '{config.referrer_policy}' always;")
        
        if config.hsts_enabled:
            hsts_value = f"max-age={config.hsts_max_age}"
            if config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if config.hsts_preload:
                hsts_value += "; preload"
            nginx_config.append(f"add_header Strict-Transport-Security '{hsts_value}' always;")
        
        # Content Security Policy
        if config.csp_enabled and config.csp_directives:
            csp_directives = []
            for directive, sources in config.csp_directives.items():
                if sources:
                    csp_directives.append(f"{directive} {' '.join(sources)}")
                else:
                    csp_directives.append(directive)
            
            csp_value = "; ".join(csp_directives)
            if config.csp_report_uri:
                csp_value += f"; report-uri {config.csp_report_uri}"
            
            header_name = "Content-Security-Policy-Report-Only" if config.csp_report_only else "Content-Security-Policy"
            nginx_config.append(f"add_header {header_name} '{csp_value}' always;")
        
        # Permissions Policy
        if config.permissions_policy_enabled and config.permissions_policy_directives:
            pp_directives = []
            for feature, allowlist in config.permissions_policy_directives.items():
                if allowlist:
                    pp_directives.append(f"{feature}=({' '.join(allowlist)})")
                else:
                    pp_directives.append(f"{feature}=()")
            
            pp_value = ", ".join(pp_directives)
            nginx_config.append(f"add_header Permissions-Policy '{pp_value}' always;")
        
        # Cross-Origin headers
        if config.coep_enabled:
            nginx_config.append(f"add_header Cross-Origin-Embedder-Policy '{config.coep_value}' always;")
        
        if config.coop_enabled:
            nginx_config.append(f"add_header Cross-Origin-Opener-Policy '{config.coop_value}' always;")
        
        if config.corp_enabled:
            nginx_config.append(f"add_header Cross-Origin-Resource-Policy '{config.corp_value}' always;")
        
        # Server header customization
        if config.server_header is not None:
            if config.server_header:
                nginx_config.append(f"server_tokens off;")
                nginx_config.append(f"more_set_headers 'Server: {config.server_header}';")
            else:
                nginx_config.append("server_tokens off;")
                nginx_config.append("more_clear_headers 'Server';")
        
        return "\n".join(nginx_config)

# Apache configuration generator  
class ApacheSecurityConfig:
    @staticmethod
    def generate_apache_config(config: SecurityHeadersConfig) -> str:
        """Generate Apache configuration for security headers."""
        apache_config = []
        
        # Security headers
        apache_config.append("# ActiveLog Security Headers Configuration")
        apache_config.append("Header always set X-Content-Type-Options nosniff")
        apache_config.append("Header always set X-Frame-Options DENY")
        apache_config.append("Header always set X-XSS-Protection '1; mode=block'")
        apache_config.append(f"Header always set Referrer-Policy '{config.referrer_policy}'")
        
        if config.hsts_enabled:
            hsts_value = f"max-age={config.hsts_max_age}"
            if config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if config.hsts_preload:
                hsts_value += "; preload"
            apache_config.append(f"Header always set Strict-Transport-Security '{hsts_value}'")
        
        # CSP and other complex headers would need similar treatment
        
        return "\n".join(apache_config)

# CLI tool for generating configurations
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Security Headers Configuration Tool")
    parser.add_argument("--config", default="configs/security-headers.yaml", help="Configuration file path")
    parser.add_argument("--generate-nginx", action="store_true", help="Generate Nginx configuration")
    parser.add_argument("--generate-apache", action="store_true", help="Generate Apache configuration")
    parser.add_argument("--output", help="Output file path")
    
    args = parser.parse_args()
    
    # Load configuration
    service = SecurityHeadersService(args.config)
    
    if args.generate_nginx:
        config_content = NginxSecurityConfig.generate_nginx_config(service.config)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(config_content)
            print(f"Nginx configuration written to {args.output}")
        else:
            print(config_content)
    
    elif args.generate_apache:
        config_content = ApacheSecurityConfig.generate_apache_config(service.config)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(config_content)
            print(f"Apache configuration written to {args.output}")
        else:
            print(config_content)
    
    else:
        # Start the service
        import uvicorn
        uvicorn.run(service.app, host="0.0.0.0", port=8090)

if __name__ == "__main__":
    main()