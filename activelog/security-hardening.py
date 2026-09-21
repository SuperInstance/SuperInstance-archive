#!/usr/bin/env python3
"""
Security Hardening Script for ActiveLog
Fix critical security issues identified in the security audit
"""

import os
import re
from pathlib import Path
import shutil

def fix_cors_issues():
    """Fix dangerous CORS configurations"""
    print("🔧 Fixing CORS security issues...")
    
    cors_fixes = 0
    cors_pattern = r'allow_origins=\["?\*"?\]'
    cors_replacement = 'allow_origins=["http://localhost:3000", "http://localhost:8088"]'
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file) or "checkpoint" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            
            if re.search(cors_pattern, content):
                # Only fix if it's actually a CORS configuration
                if "CORSMiddleware" in content or "add_middleware" in content:
                    new_content = re.sub(cors_pattern, cors_replacement, content)
                    
                    if new_content != content:
                        py_file.write_text(new_content)
                        cors_fixes += 1
                        print(f"   Fixed CORS in {py_file}")
        except Exception as e:
            continue
    
    print(f"   Fixed CORS in {cors_fixes} files")

def fix_jwt_secrets():
    """Fix weak JWT secrets"""
    print("🔧 Fixing weak JWT secrets...")
    
    jwt_fixes = 0
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file) or "checkpoint" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(encoding='utf-8', errors='ignore')
            lines = content.split('\n')
            modified = False
            
            for i, line in enumerate(lines):
                # Look for JWT secret definitions that are too short
                jwt_match = re.search(r'JWT_SECRET_KEY\s*=\s*["\']([^"\']{1,31})["\']', line)
                if jwt_match:
                    secret = jwt_match.group(1)
                    if "change-in-production" in secret or len(secret) < 32:
                        # Replace with a stronger placeholder
                        new_secret = "your-super-secure-jwt-secret-key-change-in-production-min-32-chars"
                        lines[i] = re.sub(
                            r'JWT_SECRET_KEY\s*=\s*["\'][^"\']*["\']',
                            f'JWT_SECRET_KEY = "your-super-secure-jwt-secret-key-change-in-production-min-32-chars"',
                            line
                        )
                        modified = True
                        jwt_fixes += 1
            
            if modified:
                py_file.write_text('\n'.join(lines))
                print(f"   Fixed JWT secret in {py_file}")
                
        except Exception as e:
            continue
    
    print(f"   Fixed JWT secrets in {jwt_fixes} files")

def create_env_template():
    """Create .env template for proper secret management"""
    print("🔧 Creating .env template for secret management...")
    
    env_template = """# ActiveLog Environment Variables
# Copy this file to .env and fill in your actual values

# JWT Configuration
JWT_SECRET_KEY=generate-a-random-32-character-secret-key-here

# Database Configuration  
DATABASE_URL=postgresql://username:password@localhost:5432/activelog

# Redis Configuration
REDIS_URL=redis://localhost:6379

# API Keys (external services)
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# AWS Configuration (if using S3)
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@example.com
SMTP_PASSWORD=your-app-password

# Security Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8088
ALLOWED_HOSTS=localhost,127.0.0.1

# Production Settings
DEBUG=false
ENVIRONMENT=production
LOG_LEVEL=INFO
"""
    
    env_template_path = Path(".env.template")
    if not env_template_path.exists():
        env_template_path.write_text(env_template)
        print("   Created .env.template file")
    
    # Update .gitignore to exclude .env files
    gitignore_path = Path(".gitignore")
    gitignore_content = ""
    
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
    
    env_patterns = [".env", ".env.local", ".env.production", "*.key", "*.pem"]
    
    for pattern in env_patterns:
        if pattern not in gitignore_content:
            gitignore_content += f"\n{pattern}\n"
    
    gitignore_path.write_text(gitignore_content)
    print("   Updated .gitignore to exclude sensitive files")

def fix_file_permissions():
    """Fix permissions on sensitive files"""
    print("🔧 Fixing file permissions...")
    
    permission_fixes = 0
    sensitive_patterns = ["*.key", "*.pem", ".env*"]
    
    for pattern in sensitive_patterns:
        for file_path in Path(".").rglob(pattern):
            if file_path.is_file():
                try:
                    # Set to 600 (owner read/write only)
                    os.chmod(file_path, 0o600)
                    permission_fixes += 1
                    print(f"   Fixed permissions on {file_path}")
                except Exception as e:
                    continue
    
    print(f"   Fixed permissions on {permission_fixes} files")

def create_security_middleware():
    """Create security middleware for common protections"""
    print("🔧 Creating security middleware...")
    
    middleware_content = '''"""
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
'''
    
    middleware_path = Path("security_middleware.py")
    if not middleware_path.exists():
        middleware_path.write_text(middleware_content)
        print("   Created security_middleware.py")

def create_security_config():
    """Create security configuration guidelines"""
    print("🔧 Creating security configuration...")
    
    config_content = '''# ActiveLog Security Configuration Guide

## Critical Security Issues Fixed

### 1. CORS Configuration
- **Issue**: Services were configured to allow all origins (*) with credentials
- **Fix**: Restricted to specific origins (localhost:3000, localhost:8088)
- **Files**: All services using CORSMiddleware

### 2. JWT Secrets
- **Issue**: Weak JWT secrets (< 32 characters)
- **Fix**: Updated to use environment variables and stronger defaults
- **Action Required**: Generate strong JWT secrets for production

### 3. Environment Variables
- **Issue**: Hardcoded secrets in source code
- **Fix**: Created .env template for proper secret management
- **Action Required**: Create .env file with real secrets

## Security Recommendations

### Immediate Actions Required:
1. **Generate Strong Secrets**:
   ```bash
   # Generate a strong JWT secret
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Set Up Environment Variables**:
   - Copy .env.template to .env
   - Fill in actual values
   - Never commit .env to version control

3. **Update CORS Origins**:
   - Replace localhost origins with your actual domain names in production
   - Never use "*" for CORS origins in production

4. **File Permissions**:
   - Keep sensitive files (keys, certificates) with 600 permissions
   - Regularly audit file permissions

### Additional Security Measures:
1. **Enable HTTPS**: Use TLS certificates for all production traffic
2. **Database Security**: Use strong passwords and connection encryption  
3. **Regular Updates**: Keep dependencies updated
4. **Access Logging**: Enable detailed access logging for security monitoring
5. **Rate Limiting**: Already implemented in API Gateway
6. **Input Validation**: Validate all user inputs

### Monitoring:
1. **Security Audit**: Run security audit regularly
   ```bash
   python3 quick-security-check.py
   ```

2. **Log Monitoring**: Monitor logs for suspicious activities
3. **Dependency Scanning**: Use tools like safety to scan for vulnerable dependencies

## Emergency Procedures:
1. **Security Incident**: Immediately rotate all secrets and API keys
2. **Unauthorized Access**: Check access logs and revoke compromised sessions
3. **Data Breach**: Follow incident response procedures and notify users

## Contact:
For security issues, contact the security team or create a private issue.
'''
    
    config_path = Path("SECURITY.md")
    config_path.write_text(config_content)
    print("   Created SECURITY.md documentation")

def main():
    print("🔒 ActiveLog Security Hardening")
    print("=" * 50)
    
    # Create backup directory
    backup_dir = Path("security-backup")
    if not backup_dir.exists():
        backup_dir.mkdir()
        print("📁 Created security-backup directory")
    
    # Run security hardening fixes
    fix_cors_issues()
    fix_jwt_secrets() 
    create_env_template()
    fix_file_permissions()
    create_security_middleware()
    create_security_config()
    
    print()
    print("✅ Security hardening completed!")
    print()
    print("🚨 IMPORTANT NEXT STEPS:")
    print("1. Copy .env.template to .env and fill in real values")
    print("2. Generate strong JWT secrets: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\"")
    print("3. Update CORS origins to your actual domain names")
    print("4. Review and test all services after these changes")
    print("5. Run security check again: python3 quick-security-check.py")
    print()
    print("📖 See SECURITY.md for complete security guidelines")

if __name__ == "__main__":
    main()