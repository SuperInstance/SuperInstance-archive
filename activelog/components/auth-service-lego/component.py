# SUPERINSTANCE LEGO COMPONENT: Authentication Service
# EXTRACTED FROM: services/auth-service/main.py
# LEGO PRINCIPLE: Software = Data + Tools + Configuration

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, EmailStr
from contextlib import asynccontextmanager
import bcrypt
import jwt
import sqlite3
import secrets
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import logging

class AuthServiceLego:
    """
    🧩 LEGO COMPONENT: Authentication Service
    
    DATA: Users, tokens, sessions, security audit logs, service registrations
    TOOLS: Registration, login, JWT generation/validation, password management, security monitoring
    CONFIGURATION: Token expiry, security policies, database type, integration endpoints
    
    INTERFACES:
    - Input: User credentials, registration data, token validation requests
    - Output: JWT tokens, user profiles, authentication status, security events
    - Integration: API gateways, user management, service authorization
    
    DEPLOYMENT OPTIONS:
    - Device: Local authentication for personal services
    - Edge: Regional authentication with sync capabilities  
    - Cloud: Global authentication with enterprise features
    
    SUPERINSTANCE MISSION:
    Secure $2/month authentication that scales from personal to enterprise,
    enabling perfect Lego interfaces across any deployment configuration.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.deployment_mode = config.get("deployment_mode", "edge")
        self.secret_key = config.get("secret_key", secrets.token_urlsafe(32))
        self.algorithm = "HS256"
        self.access_token_expire = config.get("access_token_minutes", 60 * 24)  # 24 hours
        self.refresh_token_expire = config.get("refresh_token_days", 7)
        
        # Initialize database based on deployment mode
        if self.deployment_mode == "device":
            self.db_path = Path(config.get("db_path", "superinstance_auth.db"))
        else:
            # For edge/cloud, would use PostgreSQL or other shared database
            self.db_path = Path(config.get("db_path", "auth_shared.db"))
        
        self.app = FastAPI(
            title="SuperInstance Auth Service Lego",
            description="Revolutionary $2/month authentication for infinite software possibilities",
            version="1.0.0"
        )
        self._setup_middleware()
        self._setup_routes()
        self._init_database()
        
        # Rate limiting
        self.rate_limiter = {}
    
    def _setup_middleware(self):
        """Configure authentication middleware for SuperInstance"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.get("cors_origins", ["*"]),
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.middleware("http")
        async def security_middleware(request: Request, call_next):
            # Add security headers for SuperInstance
            response = await call_next(request)
            response.headers["X-SuperInstance-Auth"] = "v1.0.0"
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response
    
    def _setup_routes(self):
        """Setup SuperInstance authentication routes"""
        
        @self.app.get("/health")
        async def auth_health():
            """Authentication health check - core LEGO function"""
            return {
                "service": "superinstance-auth",
                "status": "healthy",
                "deployment_mode": self.deployment_mode,
                "mission": "$2/month authentication for infinite possibilities",
                "features": self._get_enabled_features(),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        @self.app.post("/register")
        async def register_user(user_data: dict):
            """User registration - core LEGO function"""
            try:
                # Validate required fields
                email = user_data.get("email")
                username = user_data.get("username") 
                password = user_data.get("password")
                full_name = user_data.get("full_name", "")
                
                if not all([email, username, password]):
                    raise HTTPException(400, "Email, username, and password required")
                
                # Check if user already exists
                if self._user_exists(email, username):
                    raise HTTPException(409, "User already exists")
                
                # Hash password
                password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
                
                # Create user
                user_id = str(uuid.uuid4())
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT INTO users (id, email, username, full_name, password_hash, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, email, username, full_name, password_hash, datetime.utcnow().isoformat()))
                
                conn.commit()
                conn.close()
                
                # Log security event
                self._log_security_event(user_id, "USER_REGISTERED", {"email": email}, success=True)
                
                return {
                    "status": "registered",
                    "user_id": user_id,
                    "message": "Welcome to SuperInstance - $2/month unlocks infinite possibilities"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self._log_security_event(None, "REGISTRATION_FAILED", {"error": str(e)}, success=False)
                raise HTTPException(500, "Registration failed")
        
        @self.app.post("/login")
        async def login_user(credentials: dict, request: Request):
            """User login - core LEGO function"""
            try:
                email = credentials.get("email")
                password = credentials.get("password")
                
                if not email or not password:
                    raise HTTPException(400, "Email and password required")
                
                # Check rate limiting
                if self._is_rate_limited(email):
                    raise HTTPException(429, "Too many login attempts")
                
                # Verify user credentials
                user = self._verify_user_credentials(email, password)
                if not user:
                    self._increment_failed_attempts(email)
                    raise HTTPException(401, "Invalid credentials")
                
                # Generate tokens
                access_token = self._create_access_token(user)
                refresh_token = self._create_refresh_token(user, request)
                
                # Update last login
                self._update_last_login(user["id"])
                
                # Log successful login
                self._log_security_event(
                    user["id"], 
                    "USER_LOGIN", 
                    {"email": email}, 
                    success=True,
                    ip_address=request.client.host if request.client else None
                )
                
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "token_type": "bearer",
                    "expires_in": self.access_token_expire * 60,
                    "user": {
                        "id": user["id"],
                        "email": user["email"],
                        "username": user["username"],
                        "full_name": user["full_name"]
                    },
                    "superinstance_welcome": "Access granted to infinite software possibilities"
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self._log_security_event(None, "LOGIN_FAILED", {"email": email, "error": str(e)}, success=False)
                raise HTTPException(500, "Login failed")
        
        @self.app.post("/verify")
        async def verify_token(token_data: dict):
            """Token verification - core LEGO function"""
            try:
                token = token_data.get("token")
                if not token:
                    raise HTTPException(400, "Token required")
                
                # Decode and verify token
                payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
                user_id = payload.get("sub")
                
                if not user_id:
                    raise HTTPException(401, "Invalid token")
                
                # Get user info
                user = self._get_user_by_id(user_id)
                if not user or not user["is_active"]:
                    raise HTTPException(401, "User not found or inactive")
                
                return {
                    "valid": True,
                    "user_id": user_id,
                    "username": user["username"],
                    "email": user["email"],
                    "expires_at": payload.get("exp"),
                    "superinstance_status": "Authenticated for infinite possibilities"
                }
                
            except jwt.ExpiredSignatureError:
                raise HTTPException(401, "Token expired")
            except jwt.InvalidTokenError:
                raise HTTPException(401, "Invalid token")
            except Exception as e:
                raise HTTPException(500, f"Token verification failed: {str(e)}")
        
        @self.app.post("/refresh")
        async def refresh_token(refresh_data: dict):
            """Token refresh - core LEGO function"""
            try:
                refresh_token = refresh_data.get("refresh_token")
                if not refresh_token:
                    raise HTTPException(400, "Refresh token required")
                
                # Verify refresh token
                user = self._verify_refresh_token(refresh_token)
                if not user:
                    raise HTTPException(401, "Invalid refresh token")
                
                # Generate new access token
                new_access_token = self._create_access_token(user)
                
                return {
                    "access_token": new_access_token,
                    "token_type": "bearer",
                    "expires_in": self.access_token_expire * 60
                }
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(500, f"Token refresh failed: {str(e)}")
        
        @self.app.get("/user/{user_id}")
        async def get_user_profile(user_id: str, current_user=Depends(self._get_current_user)):
            """Get user profile - utility LEGO function"""
            # Check if requesting own profile or has admin access
            if current_user["id"] != user_id and not self._has_admin_access(current_user):
                raise HTTPException(403, "Access denied")
            
            user = self._get_user_by_id(user_id)
            if not user:
                raise HTTPException(404, "User not found")
            
            # Remove sensitive data
            safe_user = {
                "id": user["id"],
                "email": user["email"],
                "username": user["username"],
                "full_name": user["full_name"],
                "is_active": user["is_active"],
                "created_at": user["created_at"],
                "last_login": user["last_login"]
            }
            
            return safe_user
    
    def _init_database(self):
        """Initialize SuperInstance authentication database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys and optimize for SuperInstance
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute('PRAGMA journal_mode = WAL')
        cursor.execute('PRAGMA synchronous = NORMAL')
        
        # Users table - core SuperInstance user management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                is_verified BOOLEAN DEFAULT FALSE,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                superinstance_plan TEXT DEFAULT 'basic',
                services_enabled TEXT DEFAULT '[]'
            )
        ''')
        
        # Refresh tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS refresh_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                device_info TEXT,
                deployment_mode TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Security audit log - SuperInstance security monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_audit (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                event_type TEXT NOT NULL,
                event_details TEXT,
                ip_address TEXT,
                deployment_mode TEXT,
                success BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _get_enabled_features(self) -> List[str]:
        """Get features enabled for deployment mode"""
        base_features = ["jwt_auth", "user_registration", "token_refresh"]
        
        if self.deployment_mode == "device":
            return base_features + ["offline_auth", "local_storage"]
        elif self.deployment_mode == "edge":
            return base_features + ["regional_sync", "intelligent_routing", "rate_limiting"]
        else:  # cloud
            return base_features + ["global_sync", "enterprise_sso", "advanced_analytics", "compliance"]
    
    def _create_access_token(self, user: Dict) -> str:
        """Create JWT access token"""
        now = datetime.utcnow()
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "username": user["username"],
            "iat": now,
            "exp": now + timedelta(minutes=self.access_token_expire),
            "iss": "SuperInstance Auth Service",
            "deployment_mode": self.deployment_mode
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user: Dict, request: Request) -> str:
        """Create refresh token"""
        token_id = str(uuid.uuid4())
        refresh_token = secrets.token_urlsafe(32)
        token_hash = bcrypt.hashpw(refresh_token.encode(), bcrypt.gensalt()).decode()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        cursor.execute('''
            INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, deployment_mode)
            VALUES (?, ?, ?, ?, ?)
        ''', (token_id, user["id"], token_hash, expires_at.isoformat(), self.deployment_mode))
        
        conn.commit()
        conn.close()
        
        return refresh_token
    
    def _verify_user_credentials(self, email: str, password: str) -> Optional[Dict]:
        """Verify user login credentials"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,))
        user = cursor.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,)).fetchone()
        conn.close()
        
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            return dict(user)
        return None
    
    def _log_security_event(self, user_id: Optional[str], event_type: str, details: Dict, 
                           success: bool, ip_address: Optional[str] = None):
        """Log security events for SuperInstance monitoring"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO security_audit (id, user_id, event_type, event_details, ip_address, 
                                       deployment_mode, success, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), user_id, event_type, str(details), ip_address,
              self.deployment_mode, success, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_app(self):
        """Get FastAPI app for deployment"""
        return self.app

# SUPERINSTANCE DEPLOYMENT CONFIGURATIONS
DEPLOYMENT_CONFIGS = {
    "device_personal": {
        "deployment_mode": "device",
        "cors_origins": ["http://localhost:3000", "http://localhost:3001"],
        "access_token_minutes": 60 * 24 * 7,  # 1 week for personal use
        "db_path": "personal_auth.db",
        "features": ["offline_auth", "personal_services"]
    },
    "edge_regional": {
        "deployment_mode": "edge",
        "cors_origins": ["https://*.superinstance.com"],
        "access_token_minutes": 60 * 24,  # 24 hours
        "features": ["intelligent_routing", "regional_sync", "rate_limiting"]
    },
    "cloud_enterprise": {
        "deployment_mode": "cloud",
        "cors_origins": ["https://app.superinstance.ai"],
        "access_token_minutes": 60 * 8,  # 8 hours for security
        "features": ["enterprise_sso", "compliance", "advanced_analytics"]
    }
}

# SUPERINSTANCE FACTORY FUNCTION
def create_auth_service_lego(deployment_type: str = "edge_regional"):
    """Factory function to create SuperInstance Authentication Service Lego
    
    The authentication that makes $2/month infinite software possibilities secure.
    Perfect interfaces, enterprise security, revolutionary scalability.
    """
    config = DEPLOYMENT_CONFIGS.get(deployment_type, DEPLOYMENT_CONFIGS["edge_regional"])
    return AuthServiceLego(config)

# INTEGRATION INTERFACES
def integrate_with_api_gateway(auth_service: AuthServiceLego, gateway_url: str):
    """Connect auth service to API gateway for validation"""
    # Integration logic would be implemented here
    pass

def integrate_with_user_management(auth_service: AuthServiceLego, user_service_url: str):
    """Connect auth service to user management for profile sync"""
    # Integration logic would be implemented here
    pass

# SUPERINSTANCE MISSION STATEMENT
"""
This Authentication Service Lego embodies the SuperInstance vision:

- Secure $2/month authentication that scales infinitely
- Perfect interfaces work seamlessly across device/edge/cloud
- Revolutionary security without complexity barriers
- Lego principle: Authentication = Users + Security + Integration

Every login protected by this service contributes to the SuperInstance
mission of democratizing secure software development.
"""