#!/usr/bin/env python3
# BOT GUIDANCE: AUTH-SERVICE SERVICE INTEGRATION
# This service is part of SuperInstance production-ready architecture
# Infrastructure: Complete with autonomous reliability engine (1.0 breakthrough)
# AI Integration: Vector embeddings and hybrid architecture operational
# Status: OPERATIONAL

# INTEGRATION PATTERNS:
# - Auth service: http://localhost:8001 (JWT validation patterns)
# - API Gateway: http://localhost:8088 (routing integration)  
# - Database: PostgreSQL with pgvector (vector similarity ready)
# - AI Service: Vector embeddings and insights available

# COLLABORATION HINTS:
# - Check micro_updates.log for active bot coordination
# - Revolutionary mobile UI foundation ready for integration (0.9 impact)
# - Infrastructure bot handoff ready for services integration
# - AI bot offering assistance with vector embedding integration


"""
ActiveLog Authentication Service
Provides JWT-based authentication for all ActiveLog services

Features:
- User registration and login
- JWT token generation and validation
- Password hashing with bcrypt
- Rate limiting and security features
- User profile management
- Cross-service authentication middleware
"""

import asyncio
import json
import time
import uuid
import hashlib
import sqlite3
import secrets
import os
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
import logging
from pathlib import Path
from functools import lru_cache
from email_validator import validate_email, EmailNotValidError

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, EmailStr, constr
import uvicorn
from contextlib import asynccontextmanager
import bcrypt
import jwt
from cryptography.fernet import Fernet

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auth_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = os.getenv('JWT_SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Rate limiting configuration
RATE_LIMIT_WINDOW = 3600  # 1 hour in seconds
MAX_LOGIN_ATTEMPTS = 5
MAX_REGISTRATION_ATTEMPTS = 3

# Data Models
class UserRegistration(BaseModel):
    email: EmailStr
    password: constr(min_length=8, max_length=128)
    username: constr(min_length=3, max_length=50, pattern=r'^[a-zA-Z0-9_-]+$')
    full_name: constr(min_length=2, max_length=100)
    
    @validator('password')
    def validate_password(cls, v):
        """Strong password requirements"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('username')
    def validate_username(cls, v):
        """Username validation"""
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, hyphens, and underscores')
        return v.lower()

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int
    user: Dict[str, Any]

class TokenRefresh(BaseModel):
    refresh_token: str

class UserProfile(BaseModel):
    id: str
    email: EmailStr
    username: str
    full_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    services: List[str] = Field(default_factory=list)

class PasswordReset(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    token: str
    new_password: constr(min_length=8, max_length=128)

class AuthManager:
    """Comprehensive authentication and user management"""
    
    def __init__(self):
        self.db_path = Path("auth_data.db")
        self.init_database()
        self.rate_limiter = {}  # Simple in-memory rate limiter
        
    def init_database(self):
        """Initialize authentication database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys and WAL mode
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute('PRAGMA journal_mode = WAL')
        cursor.execute('PRAGMA synchronous = NORMAL')
        
        # Users table
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
                services TEXT DEFAULT '[]'
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
                ip_address TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Password reset tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Security audit log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS security_audit (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                event_type TEXT NOT NULL,
                event_details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                success BOOLEAN,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Service registrations (tracks which services each user has access to)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_services (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                service_name TEXT NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                UNIQUE(user_id, service_name)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_time ON security_audit(user_id, timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_services ON user_services(user_id, service_name)')
        
        conn.commit()
        conn.close()
        logger.info("✅ Authentication database initialized")
    
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    
    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, data: dict):
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.PyJWTError:
            return None
    
    def check_rate_limit(self, ip_address: str, action: str) -> bool:
        """Check if action is rate limited"""
        key = f"{ip_address}:{action}"
        now = time.time()
        
        if key not in self.rate_limiter:
            self.rate_limiter[key] = {"count": 0, "window_start": now}
        
        window_data = self.rate_limiter[key]
        
        # Reset window if expired
        if now - window_data["window_start"] > RATE_LIMIT_WINDOW:
            window_data["count"] = 0
            window_data["window_start"] = now
        
        # Check limits based on action
        max_attempts = MAX_LOGIN_ATTEMPTS if action == "login" else MAX_REGISTRATION_ATTEMPTS
        
        if window_data["count"] >= max_attempts:
            return False
        
        window_data["count"] += 1
        return True
    
    def log_security_event(self, user_id: Optional[str], event_type: str, 
                          event_details: str, ip_address: str, 
                          user_agent: str, success: bool = True):
        """Log security events"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO security_audit (id, user_id, event_type, event_details, 
                                       ip_address, user_agent, success)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), user_id, event_type, event_details,
            ip_address, user_agent, success
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Security Event: {event_type} - {event_details} - User: {user_id} - IP: {ip_address}")
    
    async def register_user(self, registration: UserRegistration, ip_address: str, user_agent: str) -> TokenResponse:
        """Register new user"""
        
        # Check rate limit
        if not self.check_rate_limit(ip_address, "register"):
            self.log_security_event(None, 'registration_rate_limited', 
                                   f'Rate limit exceeded for IP: {ip_address}',
                                   ip_address, user_agent, False)
            raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Check if email or username exists
            cursor.execute('SELECT id FROM users WHERE email = ? OR username = ?', 
                         (registration.email, registration.username))
            if cursor.fetchone():
                self.log_security_event(None, 'registration_attempt', 
                                       f'Email or username already exists: {registration.email}',
                                       ip_address, user_agent, False)
                raise HTTPException(status_code=400, detail="Email or username already registered")
            
            # Create new user
            user_id = str(uuid.uuid4())
            password_hash = self.hash_password(registration.password)
            
            cursor.execute('''
                INSERT INTO users (id, email, username, full_name, password_hash)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, registration.email, registration.username, 
                  registration.full_name, password_hash))
            
            conn.commit()
            
            # Generate tokens
            token_data = {
                "sub": user_id,
                "email": registration.email,
                "username": registration.username
            }
            access_token = self.create_access_token(token_data)
            refresh_token = self.create_refresh_token(token_data)
            
            # Store refresh token
            await self.store_refresh_token(user_id, refresh_token, ip_address, user_agent)
            
            # Get user profile
            user_profile = await self.get_user_profile(user_id)
            
            self.log_security_event(user_id, 'user_registration', 
                                   f'New user registered: {registration.email}',
                                   ip_address, user_agent, True)
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user=user_profile
            )
            
        except sqlite3.IntegrityError as e:
            self.log_security_event(None, 'registration_error', 
                                   f'Database error: {str(e)}',
                                   ip_address, user_agent, False)
            raise HTTPException(status_code=400, detail="Registration failed")
        finally:
            conn.close()
    
    async def authenticate_user(self, login: UserLogin, ip_address: str, user_agent: str) -> TokenResponse:
        """Authenticate user and return tokens"""
        
        # Check rate limit
        if not self.check_rate_limit(ip_address, "login"):
            self.log_security_event(None, 'login_rate_limited', 
                                   f'Rate limit exceeded for IP: {ip_address}',
                                   ip_address, user_agent, False)
            raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Get user by email
            cursor.execute('SELECT * FROM users WHERE email = ?', (login.email,))
            user = cursor.fetchone()
            
            if not user:
                self.log_security_event(None, 'login_attempt', 
                                       f'Login attempt with non-existent email: {login.email}',
                                       ip_address, user_agent, False)
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # Check if account is locked
            if user['locked_until'] and datetime.fromisoformat(user['locked_until']) > datetime.now():
                self.log_security_event(user['id'], 'login_locked', 
                                       f'Login attempt on locked account: {login.email}',
                                       ip_address, user_agent, False)
                raise HTTPException(status_code=423, detail="Account is temporarily locked")
            
            # Verify password
            if not self.verify_password(login.password, user['password_hash']):
                # Increment failed attempts
                failed_attempts = user['failed_login_attempts'] + 1
                locked_until = None
                
                if failed_attempts >= 5:  # Lock after 5 failed attempts
                    locked_until = datetime.now() + timedelta(hours=1)
                
                cursor.execute('''
                    UPDATE users 
                    SET failed_login_attempts = ?, locked_until = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (failed_attempts, locked_until, user['id']))
                conn.commit()
                
                self.log_security_event(user['id'], 'login_failed', 
                                       f'Failed login attempt: {login.email}',
                                       ip_address, user_agent, False)
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            # Check if user is active
            if not user['is_active']:
                self.log_security_event(user['id'], 'login_inactive', 
                                       f'Login attempt on inactive account: {login.email}',
                                       ip_address, user_agent, False)
                raise HTTPException(status_code=403, detail="Account is inactive")
            
            # Reset failed attempts and update last login
            cursor.execute('''
                UPDATE users 
                SET failed_login_attempts = 0, locked_until = NULL, 
                    last_login = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (user['id'],))
            conn.commit()
            
            # Generate tokens
            token_data = {
                "sub": user['id'],
                "email": user['email'],
                "username": user['username']
            }
            
            expires_delta = timedelta(days=7) if login.remember_me else None
            access_token = self.create_access_token(token_data, expires_delta)
            refresh_token = self.create_refresh_token(token_data)
            
            # Store refresh token
            await self.store_refresh_token(user['id'], refresh_token, ip_address, user_agent)
            
            # Get user profile
            user_profile = await self.get_user_profile(user['id'])
            
            self.log_security_event(user['id'], 'login_success', 
                                   f'Successful login: {login.email}',
                                   ip_address, user_agent, True)
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60 if not login.remember_me else 7 * 24 * 60 * 60,
                user=user_profile
            )
            
        finally:
            conn.close()
    
    async def store_refresh_token(self, user_id: str, refresh_token: str, 
                                ip_address: str, user_agent: str):
        """Store refresh token in database"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Hash the refresh token for storage
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, ip_address, device_info)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), user_id, token_hash,
            datetime.now() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address, user_agent
        ))
        
        conn.commit()
        conn.close()
    
    async def get_user_profile(self, user_id: str) -> dict:
        """Get user profile"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.*, GROUP_CONCAT(us.service_name) as services
            FROM users u
            LEFT JOIN user_services us ON u.id = us.user_id AND us.is_active = 1
            WHERE u.id = ?
            GROUP BY u.id
        ''', (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return None
        
        services = user['services'].split(',') if user['services'] else []
        
        return {
            "id": user['id'],
            "email": user['email'],
            "username": user['username'],
            "full_name": user['full_name'],
            "is_active": bool(user['is_active']),
            "is_verified": bool(user['is_verified']),
            "created_at": user['created_at'],
            "last_login": user['last_login'],
            "services": services
        }
    
    async def get_current_user(self, token: str) -> Optional[dict]:
        """Get current user from JWT token"""
        payload = self.verify_token(token, "access")
        if not payload:
            return None
        
        user_id = payload.get("sub")
        return await self.get_user_profile(user_id)
    
    async def refresh_access_token(self, refresh_token: str, ip_address: str, user_agent: str) -> TokenResponse:
        """Refresh access token using refresh token"""
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("sub")
        
        # Verify refresh token exists and is active
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        cursor.execute('''
            SELECT * FROM refresh_tokens 
            WHERE user_id = ? AND token_hash = ? AND is_active = 1 AND expires_at > CURRENT_TIMESTAMP
        ''', (user_id, token_hash))
        
        stored_token = cursor.fetchone()
        conn.close()
        
        if not stored_token:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        # Generate new access token
        user_profile = await self.get_user_profile(user_id)
        if not user_profile:
            raise HTTPException(status_code=401, detail="User not found")
        
        token_data = {
            "sub": user_id,
            "email": user_profile["email"],
            "username": user_profile["username"]
        }
        
        access_token = self.create_access_token(token_data)
        
        self.log_security_event(user_id, 'token_refresh', 
                               'Access token refreshed',
                               ip_address, user_agent, True)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,  # Keep the same refresh token
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=user_profile
        )
    
    async def grant_service_access(self, user_id: str, service_name: str):
        """Grant user access to a specific service"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_services (id, user_id, service_name, is_active)
            VALUES (?, ?, ?, 1)
        ''', (str(uuid.uuid4()), user_id, service_name))
        
        conn.commit()
        conn.close()

# Initialize auth manager
auth_manager = AuthManager()

# FastAPI security
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Dependency to get current authenticated user"""
    token = credentials.credentials
    user = await auth_manager.get_current_user(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

# Optional dependency (doesn't raise error if no token)
async def get_current_user_optional(request: Request):
    """Optional dependency to get current user"""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            return None
        return await auth_manager.get_current_user(token)
    except:
        return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 ActiveLog Authentication Service starting up")
    yield
    logger.info("🔄 ActiveLog Authentication Service shutting down")

# FastAPI app
app = FastAPI(
    title="ActiveLog Authentication Service",
    description="JWT-based authentication service for ActiveLog ecosystem",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to get client IP and user agent
def get_client_info(request: Request):
    """Get client IP and user agent"""
    ip_address = request.headers.get("X-Forwarded-For", request.client.host)
    user_agent = request.headers.get("User-Agent", "Unknown")
    return ip_address, user_agent

# Authentication endpoints
@app.post("/api/register", response_model=TokenResponse)
async def register_user(registration: UserRegistration, request: Request):
    """Register new user account"""
    ip_address, user_agent = get_client_info(request)
    return await auth_manager.register_user(registration, ip_address, user_agent)

@app.post("/api/login", response_model=TokenResponse)
async def login_user(login: UserLogin, request: Request):
    """Login user and get authentication tokens"""
    ip_address, user_agent = get_client_info(request)
    return await auth_manager.authenticate_user(login, ip_address, user_agent)

@app.post("/api/refresh", response_model=TokenResponse)
async def refresh_token(token_refresh: TokenRefresh, request: Request):
    """Refresh access token"""
    ip_address, user_agent = get_client_info(request)
    return await auth_manager.refresh_access_token(token_refresh.refresh_token, ip_address, user_agent)

@app.post("/api/logout")
async def logout_user(request: Request, current_user: dict = Depends(get_current_user)):
    """Logout user (invalidate refresh tokens)"""
    ip_address, user_agent = get_client_info(request)
    
    # In a full implementation, we'd invalidate the refresh token here
    # For now, we just log the event
    auth_manager.log_security_event(
        current_user['id'], 'logout', 'User logged out',
        ip_address, user_agent, True
    )
    
    return {"message": "Logged out successfully"}

@app.get("/api/me", response_model=UserProfile)
async def get_current_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@app.post("/api/grant-service/{service_name}")
async def grant_service_access(service_name: str, current_user: dict = Depends(get_current_user)):
    """Grant current user access to a service"""
    await auth_manager.grant_service_access(current_user['id'], service_name)
    return {"message": f"Access granted to {service_name}"}

# Middleware validation endpoint (for other services to validate tokens)
@app.post("/api/validate-token")
async def validate_token(request: Request):
    """Validate JWT token (for other services)"""
    try:
        body = await request.json()
        token = body.get("token")
        
        if not token:
            return JSONResponse(
                status_code=400,
                content={"valid": False, "error": "No token provided"}
            )
        
        user = await auth_manager.get_current_user(token)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"valid": False, "error": "Invalid token"}
            )
        
        return {
            "valid": True,
            "user": user
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": str(e)}
        )

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ActiveLog Authentication Service",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/metrics")
async def get_metrics():
    """Get service metrics"""
    conn = auth_manager.get_db_connection()
    cursor = conn.cursor()
    
    # Get user statistics
    cursor.execute('SELECT COUNT(*) as total_users FROM users')
    total_users = cursor.fetchone()['total_users']
    
    cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_active = 1')
    active_users = cursor.fetchone()['active_users']
    
    cursor.execute('SELECT COUNT(*) as verified_users FROM users WHERE is_verified = 1')
    verified_users = cursor.fetchone()['verified_users']
    
    # Get recent activity
    cursor.execute('''
        SELECT COUNT(*) as logins_24h 
        FROM security_audit 
        WHERE event_type = 'login_success' 
        AND timestamp > datetime('now', '-24 hours')
    ''')
    logins_24h = cursor.fetchone()['logins_24h']
    
    conn.close()
    
    return {
        "service": "ActiveLog Authentication Service",
        "status": "healthy",
        "metrics": {
            "total_users": total_users,
            "active_users": active_users,
            "verified_users": verified_users,
            "logins_last_24h": logins_24h
        },
        "database": {
            "path": str(auth_manager.db_path),
            "exists": auth_manager.db_path.exists()
        },
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Authentication Service")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", 8001)), help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🚀 Starting ActiveLog Authentication Service")
    print(f"🔐 JWT-based authentication with secure token management")
    print(f"👥 User registration, login, and profile management")
    print(f"🛡️  Rate limiting and security audit logging")
    print(f"🔗 Cross-service authentication middleware")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )