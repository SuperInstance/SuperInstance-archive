"""
Input Sanitization Middleware for ActiveLog
Provides comprehensive input validation and sanitization to prevent injection attacks.
"""

import re
import html
import json
import bleach
import urllib.parse
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, Request
from fastapi.security.utils import get_authorization_scheme_param
import sqlparse
from pathlib import Path


class InputSanitizer:
    """Comprehensive input sanitization and validation."""
    
    def __init__(self):
        # XSS prevention - allowed HTML tags and attributes
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote'
        ]
        
        self.allowed_attributes = {
            '*': ['class'],
            'a': ['href', 'title'],
            'img': ['src', 'alt', 'width', 'height']
        }
        
        # SQL injection patterns
        self.sql_injection_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|SCRIPT)\b)",
            r"(--|\/\*|\*\/|xp_|sp_)",
            r"(\bOR\b.*\b=\b|\bAND\b.*\b=\b)",
            r"(\'|\"|;|\||&|\$)",
            r"(\b(INFORMATION_SCHEMA|SYSOBJECTS|SYSCOLUMNS)\b)"
        ]
        
        # XSS patterns
        self.xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
            r"<form[^>]*>.*?</form>",
            r"eval\s*\(",
            r"expression\s*\("
        ]
        
        # Command injection patterns
        self.command_injection_patterns = [
            r"(;|\||&|`|\$\(|\${)",
            r"(\.\./|\.\.\\\\)",
            r"(\b(cat|ls|pwd|whoami|id|uname|ps|netstat|chmod|chown|rm|mv|cp)\b)",
            r"(>|<|>>|&&|\|\|)"
        ]
        
        # Path traversal patterns
        self.path_traversal_patterns = [
            r"(\.\./|\.\.\x5c)",
            r"(\x2e\x2e\x2f|\x2e\x2e\x5c)",
            r"(\.\.%2f|\.\.%5c)",
            r"(%2e%2e%2f|%2e%2e%5c)"
        ]
        
        # LDAP injection patterns
        self.ldap_injection_patterns = [
            r"(\(|\)|\*|\||&)",
            r"(\\[0-9a-f]{2})",
            r"(\x00|\x01|\x02|\x03|\x04|\x05|\x06|\x07)"
        ]


class SecurityMiddleware:
    """FastAPI middleware for input sanitization and security validation."""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.max_payload_size = 10 * 1024 * 1024  # 10MB
        self.max_url_length = 2048
        self.max_header_value_length = 8192
        
        # Rate limiting (simple in-memory implementation)
        self.request_counts = {}
        self.max_requests_per_minute = 100
    
    async def __call__(self, request: Request, call_next):
        """Process request through security middleware."""
        try:
            # Validate request size
            await self._validate_request_size(request)
            
            # Validate URL length
            self._validate_url_length(request)
            
            # Validate headers
            self._validate_headers(request)
            
            # Rate limiting check
            self._check_rate_limit(request)
            
            # Sanitize and validate request body
            if request.method in ['POST', 'PUT', 'PATCH']:
                await self._sanitize_request_body(request)
            
            # Sanitize query parameters
            self._sanitize_query_params(request)
            
            # Sanitize path parameters
            self._sanitize_path_params(request)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers to response
            self._add_security_headers(response)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail="Internal security validation error"
            )
    
    async def _validate_request_size(self, request: Request):
        """Validate request payload size."""
        content_length = request.headers.get('content-length')
        if content_length and int(content_length) > self.max_payload_size:
            raise HTTPException(
                status_code=413,
                detail="Request payload too large"
            )
    
    def _validate_url_length(self, request: Request):
        """Validate URL length to prevent buffer overflow attacks."""
        url = str(request.url)
        if len(url) > self.max_url_length:
            raise HTTPException(
                status_code=414,
                detail="URL too long"
            )
    
    def _validate_headers(self, request: Request):
        """Validate HTTP headers for security issues."""
        for name, value in request.headers.items():
            # Check header value length
            if len(value) > self.max_header_value_length:
                raise HTTPException(
                    status_code=400,
                    detail=f"Header {name} value too long"
                )
            
            # Check for injection attempts in headers
            if self._detect_injection_attempt(value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Malicious content detected in header {name}"
                )
    
    def _check_rate_limit(self, request: Request):
        """Simple rate limiting implementation."""
        client_ip = request.client.host
        current_time = int(time.time() / 60)  # Current minute
        
        key = f"{client_ip}:{current_time}"
        self.request_counts[key] = self.request_counts.get(key, 0) + 1
        
        if self.request_counts[key] > self.max_requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded"
            )
        
        # Cleanup old entries (keep only last 2 minutes)
        cleanup_keys = [k for k in self.request_counts.keys() 
                       if int(k.split(':')[1]) < current_time - 1]
        for key in cleanup_keys:
            del self.request_counts[key]
    
    async def _sanitize_request_body(self, request: Request):
        """Sanitize request body content."""
        if not hasattr(request.state, 'body'):
            body = await request.body()
            request.state.body = body
        else:
            body = request.state.body
        
        if not body:
            return
        
        try:
            # Parse JSON if content-type is JSON
            content_type = request.headers.get('content-type', '').lower()
            if 'application/json' in content_type:
                data = json.loads(body)
                sanitized_data = self._sanitize_json_data(data)
                request.state.sanitized_body = json.dumps(sanitized_data)
            else:
                # For non-JSON, check for injection patterns
                body_str = body.decode('utf-8', errors='ignore')
                if self._detect_injection_attempt(body_str):
                    raise HTTPException(
                        status_code=400,
                        detail="Malicious content detected in request body"
                    )
        except json.JSONDecodeError:
            # If not valid JSON, treat as text and validate
            body_str = body.decode('utf-8', errors='ignore')
            if self._detect_injection_attempt(body_str):
                raise HTTPException(
                    status_code=400,
                    detail="Malicious content detected in request body"
                )
    
    def _sanitize_query_params(self, request: Request):
        """Sanitize URL query parameters."""
        for param, value in request.query_params.items():
            if isinstance(value, str):
                if self._detect_injection_attempt(value):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Malicious content detected in query parameter {param}"
                    )
    
    def _sanitize_path_params(self, request: Request):
        """Sanitize URL path parameters."""
        path = request.url.path
        
        # Check for path traversal attempts
        if self._detect_path_traversal(path):
            raise HTTPException(
                status_code=400,
                detail="Path traversal attempt detected"
            )
        
        # Check for other injection attempts in path
        if self._detect_injection_attempt(path):
            raise HTTPException(
                status_code=400,
                detail="Malicious content detected in URL path"
            )
    
    def _sanitize_json_data(self, data: Any) -> Any:
        """Recursively sanitize JSON data."""
        if isinstance(data, dict):
            return {key: self._sanitize_json_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_json_data(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            return data
    
    def _sanitize_string(self, value: str) -> str:
        """Sanitize string value."""
        # Check for injection attempts
        if self._detect_injection_attempt(value):
            raise HTTPException(
                status_code=400,
                detail="Malicious content detected in input"
            )
        
        # HTML encode to prevent XSS
        sanitized = html.escape(value)
        
        # Clean HTML with bleach for rich text fields
        if '<' in value and '>' in value:
            sanitized = bleach.clean(
                value,
                tags=self.sanitizer.allowed_tags,
                attributes=self.sanitizer.allowed_attributes,
                strip=True
            )
        
        return sanitized
    
    def _detect_injection_attempt(self, value: str) -> bool:
        """Detect various injection attempts."""
        if not isinstance(value, str):
            return False
        
        value_lower = value.lower()
        
        # SQL injection detection
        for pattern in self.sanitizer.sql_injection_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        # XSS detection
        for pattern in self.sanitizer.xss_patterns:
            if re.search(pattern, value_lower, re.IGNORECASE):
                return True
        
        # Command injection detection
        for pattern in self.sanitizer.command_injection_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        # LDAP injection detection
        for pattern in self.sanitizer.ldap_injection_patterns:
            if re.search(pattern, value):
                return True
        
        return False
    
    def _detect_path_traversal(self, path: str) -> bool:
        """Detect path traversal attempts."""
        for pattern in self.sanitizer.path_traversal_patterns:
            if re.search(pattern, path, re.IGNORECASE):
                return True
        return False
    
    def _add_security_headers(self, response):
        """Add security headers to response."""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https:; connect-src 'self' https:; frame-ancestors 'none';",
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Permissions-Policy': 'geolocation=(), microphone=(), camera=()'
        }
        
        for header, value in security_headers.items():
            response.headers[header] = value


# Utility functions for manual sanitization
def sanitize_sql_input(value: str) -> str:
    """Sanitize input for SQL queries."""
    if not isinstance(value, str):
        return value
    
    # Remove SQL injection patterns
    sanitizer = InputSanitizer()
    for pattern in sanitizer.sql_injection_patterns:
        value = re.sub(pattern, '', value, flags=re.IGNORECASE)
    
    # Escape single quotes
    value = value.replace("'", "''")
    
    return value


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal."""
    if not isinstance(filename, str):
        return filename
    
    # Remove path components
    filename = Path(filename).name
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = Path(filename).stem, Path(filename).suffix
        filename = name[:255-len(ext)] + ext
    
    return filename


def validate_email(email: str) -> bool:
    """Validate email address format."""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(email_pattern, email))


def validate_url(url: str) -> bool:
    """Validate URL format and scheme."""
    try:
        parsed = urllib.parse.urlparse(url)
        return parsed.scheme in ['http', 'https'] and parsed.netloc
    except:
        return False


def sanitize_html(content: str) -> str:
    """Sanitize HTML content to prevent XSS."""
    sanitizer = InputSanitizer()
    return bleach.clean(
        content,
        tags=sanitizer.allowed_tags,
        attributes=sanitizer.allowed_attributes,
        strip=True
    )


# Example FastAPI integration
def setup_security_middleware(app):
    """Setup security middleware in FastAPI app."""
    app.add_middleware(SecurityMiddleware)


# Testing utilities
def test_injection_patterns():
    """Test injection pattern detection."""
    sanitizer = InputSanitizer()
    middleware = SecurityMiddleware()
    
    # SQL injection test cases
    sql_tests = [
        "admin'; DROP TABLE users; --",
        "1 OR 1=1",
        "UNION SELECT * FROM passwords",
        "'; EXEC xp_cmdshell('dir'); --"
    ]
    
    # XSS test cases
    xss_tests = [
        "<script>alert('XSS')</script>",
        "javascript:alert('XSS')",
        "<img src=x onerror=alert('XSS')>",
        "<iframe src=javascript:alert('XSS')></iframe>"
    ]
    
    # Command injection test cases
    cmd_tests = [
        "; ls -la",
        "| cat /etc/passwd",
        "$(whoami)",
        "&& rm -rf /"
    ]
    
    print("Testing SQL injection patterns:")
    for test in sql_tests:
        result = middleware._detect_injection_attempt(test)
        print(f"  '{test}' -> {'BLOCKED' if result else 'ALLOWED'}")
    
    print("\nTesting XSS patterns:")
    for test in xss_tests:
        result = middleware._detect_injection_attempt(test)
        print(f"  '{test}' -> {'BLOCKED' if result else 'ALLOWED'}")
    
    print("\nTesting command injection patterns:")
    for test in cmd_tests:
        result = middleware._detect_injection_attempt(test)
        print(f"  '{test}' -> {'BLOCKED' if result else 'ALLOWED'}")


if __name__ == "__main__":
    import time
    test_injection_patterns()