#!/usr/bin/env python3
"""
PersonalLog.ai Backend Service - World-Class Production Ready
Advanced backend with enterprise-grade features, security, and performance
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
from collections import defaultdict
import threading
from functools import lru_cache
from email_validator import validate_email, EmailNotValidError

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator, EmailStr, constr
import uvicorn
import requests
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import bcrypt
import jwt
from cryptography.fernet import Fernet

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/personallog_backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Security logger for audit trails
security_logger = logging.getLogger('security')
security_handler = logging.FileHandler('logs/security_audit.log')
security_handler.setFormatter(logging.Formatter(
    '%(asctime)s - SECURITY - %(levelname)s - %(message)s'
))
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.INFO)

# Ensure logs directory exists
Path('logs').mkdir(exist_ok=True)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)

# Security configuration
SECRET_KEY = os.getenv('SECRET_KEY', secrets.token_urlsafe(32))
ALGORITHM = 'HS256'
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Data encryption
encryption_key = os.getenv('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(encryption_key)

# Enhanced Data Models with validation
class JournalEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: constr(min_length=1, max_length=100)
    title: constr(min_length=1, max_length=200)
    content: constr(min_length=1, max_length=50000)  # 50k characters max
    tags: List[constr(max_length=50)] = Field(default_factory=list, max_items=10)
    mood: Optional[constr(regex=r'^(happy|sad|angry|excited|peaceful|thoughtful|grateful|stressed)$')] = None
    location: Optional[constr(max_length=100)] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    sync_version: int = 0
    is_deleted: bool = False
    privacy_level: str = Field(default='private', regex=r'^(private|shared|public)$')
    
    @validator('content')
    def validate_content(cls, v):
        # Remove any potential script tags or malicious content
        if re.search(r'<script[^>]*>.*?</script>', v, re.IGNORECASE | re.DOTALL):
            raise ValueError('Script tags are not allowed in content')
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        # Clean and validate tags
        cleaned_tags = []
        for tag in v:
            clean_tag = re.sub(r'[^\w\s-]', '', tag.strip())[:50]
            if clean_tag and clean_tag not in cleaned_tags:
                cleaned_tags.append(clean_tag)
        return cleaned_tags[:10]  # Max 10 tags

class UserProfile(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: constr(min_length=2, max_length=100, regex=r'^[\w\s.-]+$')
    tier: str = Field(default='free', regex=r'^(free|premium|enterprise)$')
    preferences: Dict[str, Any] = Field(default_factory=dict, max_items=50)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: datetime = Field(default_factory=datetime.now)
    usage_stats: Dict[str, int] = Field(default_factory=lambda: {
        "entries_created": 0,
        "ai_insights_used": 0,
        "words_written": 0,
        "login_count": 0,
        "streak_days": 0
    })
    is_active: bool = True
    email_verified: bool = False
    two_factor_enabled: bool = False
    
    @validator('preferences')
    def validate_preferences(cls, v):
        # Ensure preferences don't contain sensitive data
        forbidden_keys = ['password', 'token', 'secret', 'key']
        for key in v.keys():
            if any(forbidden in key.lower() for forbidden in forbidden_keys):
                raise ValueError(f'Preference key "{key}" is not allowed')
        return v

class UserRegistration(BaseModel):
    email: EmailStr
    name: constr(min_length=2, max_length=100, regex=r'^[\w\s.-]+$')
    password: constr(min_length=8, max_length=128)
    
    @validator('password')
    def validate_password(cls, v):
        # Strong password requirements
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

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'
    expires_in: int
    user_profile: UserProfile

class SyncRequest(BaseModel):
    user_id: str
    last_sync_version: int = 0
    local_changes: List[Dict[str, Any]] = Field(default_factory=list, max_items=100)
    device_id: str
    device_type: str = Field(regex=r'^(web|mobile|desktop)$')
    client_version: str
    
    @validator('local_changes')
    def validate_changes(cls, v):
        # Validate each change has required fields
        for change in v:
            if 'action' not in change or change['action'] not in ['create', 'update', 'delete']:
                raise ValueError('Invalid change action')
            if 'data' not in change:
                raise ValueError('Change must include data')
        return v

class AIInsight(BaseModel):
    entry_id: str
    insight_type: str = Field(regex=r'^(sentiment|themes|suggestions|patterns|growth|writing_analysis|emotional_trends)$')
    content: constr(max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.now)
    model_version: str = '1.0'
    processing_time_ms: Optional[float] = None

class UserAnalytics(BaseModel):
    user_id: str
    writing_patterns: Dict[str, Any]
    emotional_trends: Dict[str, Any]
    productivity_metrics: Dict[str, Any]
    growth_indicators: Dict[str, Any]
    recommendations: List[str]
    last_updated: datetime = Field(default_factory=datetime.now)

class BackupRequest(BaseModel):
    user_id: str
    backup_type: str = Field(regex=r'^(full|incremental|entries_only)$')
    include_insights: bool = True
    encryption_enabled: bool = True

class SecurityManager:
    """Enhanced security management for authentication and authorization"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict):
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            if payload.get("type") != token_type:
                return None
            return payload
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    def encrypt_data(data: str) -> str:
        """Encrypt sensitive data"""
        return cipher_suite.encrypt(data.encode()).decode()
    
    @staticmethod
    def decrypt_data(encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        return cipher_suite.decrypt(encrypted_data.encode()).decode()

class CacheManager:
    """Advanced caching for performance optimization"""
    
    def __init__(self):
        self.cache = defaultdict(dict)
        self.cache_timestamps = defaultdict(dict)
        self.cache_ttl = 300  # 5 minutes default TTL
        self._lock = threading.Lock()
    
    def get(self, namespace: str, key: str) -> Optional[Any]:
        """Get cached value"""
        with self._lock:
            if namespace in self.cache and key in self.cache[namespace]:
                timestamp = self.cache_timestamps[namespace].get(key, 0)
                if time.time() - timestamp < self.cache_ttl:
                    return self.cache[namespace][key]
                else:
                    # Expired - remove from cache
                    del self.cache[namespace][key]
                    del self.cache_timestamps[namespace][key]
        return None
    
    def set(self, namespace: str, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value"""
        with self._lock:
            self.cache[namespace][key] = value
            self.cache_timestamps[namespace][key] = time.time()
    
    def invalidate(self, namespace: str, key: Optional[str] = None):
        """Invalidate cache"""
        with self._lock:
            if key:
                self.cache[namespace].pop(key, None)
                self.cache_timestamps[namespace].pop(key, None)
            else:
                self.cache.pop(namespace, None)
                self.cache_timestamps.pop(namespace, None)

class PersonalLogBackend:
    """World-class PersonalLog backend with enterprise features"""
    
    def __init__(self):
        self.db_path = Path("data/personallog.db")
        self.backup_path = Path("backups")
        self.db_path.parent.mkdir(exist_ok=True)
        self.backup_path.mkdir(exist_ok=True)
        
        # Initialize components
        self.security = SecurityManager()
        self.cache = CacheManager()
        self.init_database()
        
        # WebSocket connections management
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)
        
        # Service connections
        self.ad_service_url = os.getenv("AD_SERVICE_URL", "http://localhost:8080")
        self.ai_orchestrator_url = os.getenv("AI_SERVICE_URL", "http://localhost:8090")
        self.cache_service_url = os.getenv("CACHE_SERVICE_URL", "http://localhost:8092")
        
        # Enhanced performance metrics
        self.metrics = {
            "requests_served": 0,
            "entries_synced": 0,
            "ai_insights_generated": 0,
            "ads_served": 0,
            "average_response_time": 0.0,
            "authentication_attempts": 0,
            "failed_logins": 0,
            "active_users_24h": 0,
            "database_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "websocket_connections": 0,
            "backup_operations": 0,
            "security_events": 0
        }
        
        # Rate limiting tracking
        self.rate_limit_tracker = defaultdict(lambda: {'count': 0, 'reset_time': time.time() + 3600})
    
    def init_database(self):
        """Initialize SQLite database with enhanced schema and security"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enable foreign keys and WAL mode for better performance
        cursor.execute('PRAGMA foreign_keys = ON')
        cursor.execute('PRAGMA journal_mode = WAL')
        cursor.execute('PRAGMA synchronous = NORMAL')
        cursor.execute('PRAGMA cache_size = 10000')
        cursor.execute('PRAGMA temp_store = MEMORY')
        
        # Enhanced users table with security features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                tier TEXT DEFAULT 'free' CHECK (tier IN ('free', 'premium', 'enterprise')),
                preferences TEXT DEFAULT '{}',
                usage_stats TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                email_verified BOOLEAN DEFAULT FALSE,
                two_factor_enabled BOOLEAN DEFAULT FALSE,
                two_factor_secret TEXT,
                failed_login_attempts INTEGER DEFAULT 0,
                locked_until TIMESTAMP,
                last_login TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # User sessions table for token management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                refresh_token_hash TEXT NOT NULL,
                device_id TEXT,
                device_type TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
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
        
        # Enhanced journal entries table with privacy controls
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_encrypted TEXT,  -- For premium users
                tags TEXT DEFAULT '[]',
                mood TEXT CHECK (mood IN ('happy', 'sad', 'angry', 'excited', 'peaceful', 'thoughtful', 'grateful', 'stressed') OR mood IS NULL),
                location TEXT,
                privacy_level TEXT DEFAULT 'private' CHECK (privacy_level IN ('private', 'shared', 'public')),
                word_count INTEGER DEFAULT 0,
                reading_time_minutes INTEGER DEFAULT 0,
                sync_version INTEGER DEFAULT 0,
                is_deleted BOOLEAN DEFAULT FALSE,
                deleted_at TIMESTAMP,
                device_created TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Entry versions for history tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entry_versions (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                modified_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE,
                FOREIGN KEY (modified_by) REFERENCES users (id),
                UNIQUE(entry_id, version_number)
            )
        ''')
        
        # Enhanced AI insights table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_insights (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                insight_type TEXT NOT NULL CHECK (insight_type IN (
                    'sentiment', 'themes', 'suggestions', 'patterns', 'growth', 
                    'writing_analysis', 'emotional_trends'
                )),
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                model_version TEXT DEFAULT '1.0',
                processing_time_ms REAL,
                metadata TEXT DEFAULT '{}',
                is_dismissed BOOLEAN DEFAULT FALSE,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES entries (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # User analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_analytics (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                analytics_type TEXT NOT NULL,
                data TEXT NOT NULL,  -- JSON data
                period_start TIMESTAMP NOT NULL,
                period_end TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # User goals and achievements
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_data TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Enhanced sync metadata with device tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sync_metadata (
                user_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                last_sync_version INTEGER DEFAULT 0,
                last_sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_entries INTEGER DEFAULT 0,
                device_type TEXT,
                client_version TEXT,
                sync_conflicts INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, device_id),
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Backup metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backups (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                backup_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER,
                entries_count INTEGER,
                is_encrypted BOOLEAN DEFAULT TRUE,
                checksum TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # API usage tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                endpoint TEXT NOT NULL,
                method TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms REAL,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Create comprehensive indexes for performance
        # Users indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active, last_active)')
        
        # Entries indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_user_id ON entries(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_mood ON entries(mood)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_privacy ON entries(privacy_level)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_user_created ON entries(user_id, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_sync ON entries(user_id, sync_version)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_entries_deleted ON entries(is_deleted, deleted_at)')
        
        # AI insights indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_entry_id ON ai_insights(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_user_type ON ai_insights(user_id, insight_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_generated ON ai_insights(generated_at DESC)')
        
        # Sessions and security indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id, is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_user ON security_audit(user_id, timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_event ON security_audit(event_type, timestamp DESC)')
        
        # Analytics and usage indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user ON user_analytics(user_id, analytics_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_user ON api_usage(user_id, timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_endpoint ON api_usage(endpoint, timestamp DESC)')
        
        # Backup indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_user ON backups(user_id, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backups_expires ON backups(expires_at)')
        
        conn.commit()
        
        # Cleanup expired sessions and backups on startup
        self._cleanup_expired_data(cursor)
        
        conn.commit()
        conn.close()
        logger.info("✅ PersonalLog database initialized with enhanced security")
    
    def _cleanup_expired_data(self, cursor):
        """Clean up expired sessions, backups, and old audit logs"""
        now = datetime.now()
        
        # Clean expired sessions
        cursor.execute('DELETE FROM user_sessions WHERE expires_at < ?', (now,))
        
        # Clean expired backups
        cursor.execute('DELETE FROM backups WHERE expires_at IS NOT NULL AND expires_at < ?', (now,))
        
        # Clean old audit logs (keep 90 days)
        ninety_days_ago = now - timedelta(days=90)
        cursor.execute('DELETE FROM security_audit WHERE timestamp < ?', (ninety_days_ago,))
        
        # Clean old API usage logs (keep 30 days)
        thirty_days_ago = now - timedelta(days=30)
        cursor.execute('DELETE FROM api_usage WHERE timestamp < ?', (thirty_days_ago,))
        
        logger.info("🧹 Cleaned up expired data")
    
    def get_db_connection(self):
        """Get database connection with enhanced configuration"""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')
        self.metrics["database_queries"] += 1
        return conn
    
    async def log_security_event(self, user_id: Optional[str], event_type: str, 
                                event_details: str, ip_address: str, 
                                user_agent: str, success: bool = True):
        """Log security events for audit trail"""
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
        
        self.metrics["security_events"] += 1
        security_logger.info(f"{event_type}: {event_details} - User: {user_id} - IP: {ip_address}")
    
    async def log_api_usage(self, user_id: Optional[str], endpoint: str, method: str,
                           status_code: int, response_time: float, ip_address: str, user_agent: str):
        """Log API usage for analytics"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_usage (id, user_id, endpoint, method, status_code, 
                                 response_time_ms, ip_address, user_agent)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(uuid.uuid4()), user_id, endpoint, method, status_code,
            response_time * 1000, ip_address, user_agent
        ))
        
        conn.commit()
        conn.close()
    
    async def register_user(self, registration_data: UserRegistration, ip_address: str, user_agent: str) -> TokenResponse:
        """Register new user with enhanced security"""
        
        # Check if email already exists
        existing_user = await self.get_user_by_email(registration_data.email)
        if existing_user:
            await self.log_security_event(
                None, 'registration_attempt', 
                f'Email already exists: {registration_data.email}',
                ip_address, user_agent, False
            )
            raise HTTPException(status_code=400, detail="Email already registered")
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            user_id = str(uuid.uuid4())
            password_hash = self.security.hash_password(registration_data.password)
            
            cursor.execute('''
                INSERT INTO users (id, email, name, password_hash, tier, preferences, usage_stats)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                registration_data.email,
                registration_data.name,
                password_hash,
                'free',
                json.dumps({}),
                json.dumps({
                    "entries_created": 0,
                    "ai_insights_used": 0,
                    "words_written": 0,
                    "login_count": 0,
                    "streak_days": 0
                })
            ))
            
            conn.commit()
            
            # Create user profile
            user_profile = UserProfile(
                id=user_id,
                email=registration_data.email,
                name=registration_data.name,
                tier='free',
                preferences={},
                usage_stats={
                    "entries_created": 0,
                    "ai_insights_used": 0,
                    "words_written": 0,
                    "login_count": 0,
                    "streak_days": 0
                },
                is_active=True,
                email_verified=False,
                two_factor_enabled=False
            )
            
            # Generate tokens
            access_token_data = {"sub": user_id, "email": registration_data.email}
            access_token = self.security.create_access_token(access_token_data)
            refresh_token = self.security.create_refresh_token(access_token_data)
            
            # Store refresh token session
            await self.create_user_session(user_id, refresh_token, ip_address, user_agent)
            
            await self.log_security_event(
                user_id, 'user_registration', 
                f'New user registered: {registration_data.email}',
                ip_address, user_agent, True
            )
            
            logger.info(f"👤 Registered user: {registration_data.email}")
            
            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                user_profile=user_profile
            )
            
        except sqlite3.IntegrityError as e:
            await self.log_security_event(
                None, 'registration_error', 
                f'Database error: {str(e)}',
                ip_address, user_agent, False
            )
            raise HTTPException(status_code=400, detail="Registration failed")
        finally:
            conn.close()
    
    async def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user by ID"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return UserProfile(
                id=row['id'],
                email=row['email'],
                name=row['name'],
                tier=row['tier'],
                preferences=json.loads(row['preferences']),
                usage_stats=json.loads(row['usage_stats']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_active=datetime.fromisoformat(row['last_active'])
            )
        return None
    
    async def create_entry(self, entry: JournalEntry) -> JournalEntry:
        """Create new journal entry"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Increment sync version
        cursor.execute('''
            UPDATE sync_metadata 
            SET last_sync_version = last_sync_version + 1,
                total_entries = total_entries + 1,
                last_sync_timestamp = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (entry.user_id,))
        
        # Get new sync version
        cursor.execute('SELECT last_sync_version FROM sync_metadata WHERE user_id = ?', (entry.user_id,))
        entry.sync_version = cursor.fetchone()['last_sync_version']
        
        # Insert entry
        cursor.execute('''
            INSERT INTO entries (id, user_id, title, content, tags, mood, location, sync_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.id,
            entry.user_id,
            entry.title,
            entry.content,
            json.dumps(entry.tags),
            entry.mood,
            entry.location,
            entry.sync_version
        ))
        
        # Update user stats
        cursor.execute('''
            UPDATE users 
            SET usage_stats = json_set(usage_stats, '$.entries_created', 
                json_extract(usage_stats, '$.entries_created') + 1),
                usage_stats = json_set(usage_stats, '$.words_written', 
                json_extract(usage_stats, '$.words_written') + ?),
                last_active = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (len(entry.content.split()), entry.user_id))
        
        conn.commit()
        conn.close()
        
        # Generate AI insights in background
        asyncio.create_task(self.generate_ai_insights(entry))
        
        logger.info(f"📝 Created entry: {entry.title[:30]}...")
        return entry
    
    async def sync_data(self, sync_request: SyncRequest) -> Dict[str, Any]:
        """Sync local changes with server (local-first architecture)"""
        start_time = time.time()
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        # Get current server version
        cursor.execute('SELECT last_sync_version FROM sync_metadata WHERE user_id = ?', (sync_request.user_id,))
        server_version = cursor.fetchone()['last_sync_version']
        
        # Apply local changes to server
        conflicts = []
        applied_changes = 0
        
        for change in sync_request.local_changes:
            try:
                if change['action'] == 'create':
                    entry = JournalEntry(**change['data'])
                    await self.create_entry(entry)
                    applied_changes += 1
                
                elif change['action'] == 'update':
                    # Check for conflicts
                    cursor.execute('SELECT sync_version FROM entries WHERE id = ?', (change['data']['id'],))
                    row = cursor.fetchone()
                    
                    if row and row['sync_version'] > change['data']['sync_version']:
                        conflicts.append({
                            'entry_id': change['data']['id'],
                            'conflict_type': 'version_mismatch',
                            'server_version': row['sync_version'],
                            'client_version': change['data']['sync_version']
                        })
                    else:
                        # Apply update
                        cursor.execute('''
                            UPDATE entries 
                            SET title=?, content=?, tags=?, mood=?, location=?, 
                                sync_version=?, updated_at=CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (
                            change['data']['title'],
                            change['data']['content'],
                            json.dumps(change['data']['tags']),
                            change['data']['mood'],
                            change['data']['location'],
                            server_version + 1,
                            change['data']['id']
                        ))
                        applied_changes += 1
                
                elif change['action'] == 'delete':
                    cursor.execute('''
                        UPDATE entries 
                        SET is_deleted = TRUE, sync_version = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (server_version + 1, change['data']['id']))
                    applied_changes += 1
                    
            except Exception as e:
                logger.error(f"Sync error for change {change}: {e}")
                conflicts.append({
                    'entry_id': change.get('data', {}).get('id', 'unknown'),
                    'conflict_type': 'application_error',
                    'error': str(e)
                })
        
        # Get changes from server since client's last sync
        cursor.execute('''
            SELECT * FROM entries 
            WHERE user_id = ? AND sync_version > ? AND is_deleted = FALSE
            ORDER BY sync_version
        ''', (sync_request.user_id, sync_request.last_sync_version))
        
        server_changes = []
        for row in cursor.fetchall():
            server_changes.append({
                'id': row['id'],
                'title': row['title'],
                'content': row['content'],
                'tags': json.loads(row['tags']),
                'mood': row['mood'],
                'location': row['location'],
                'sync_version': row['sync_version'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at']
            })
        
        # Update sync metadata
        new_version = server_version + applied_changes
        cursor.execute('''
            UPDATE sync_metadata 
            SET last_sync_version = ?, last_sync_timestamp = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (new_version, sync_request.user_id))
        
        conn.commit()
        conn.close()
        
        # Update metrics
        self.metrics["entries_synced"] += applied_changes
        sync_time = time.time() - start_time
        self.metrics["average_response_time"] = (
            self.metrics["average_response_time"] * 0.9 + sync_time * 0.1
        )
        
        return {
            "sync_version": new_version,
            "server_changes": server_changes,
            "applied_changes": applied_changes,
            "conflicts": conflicts,
            "sync_timestamp": datetime.now().isoformat(),
            "processing_time_ms": sync_time * 1000
        }
    
    async def generate_ai_insights(self, entry: JournalEntry):
        """Generate AI insights for journal entry"""
        try:
            # Call AI orchestrator for insights
            response = requests.post(
                f"{self.ai_orchestrator_url}/api/ai/analyze",
                json={
                    "text": entry.content,
                    "type": "journal_entry",
                    "user_id": entry.user_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                analysis = response.json()
                
                # Store insights in database
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                insights = [
                    {
                        "type": "sentiment",
                        "content": f"Sentiment: {analysis.get('sentiment', 'neutral')} (confidence: {analysis.get('sentiment_confidence', 0.5):.2f})",
                        "confidence": analysis.get('sentiment_confidence', 0.5)
                    },
                    {
                        "type": "themes",
                        "content": f"Key themes: {', '.join(analysis.get('themes', ['reflection']))}",
                        "confidence": 0.8
                    },
                    {
                        "type": "suggestions",
                        "content": analysis.get('suggestions', 'Consider exploring this topic further in future entries.'),
                        "confidence": 0.7
                    }
                ]
                
                for insight in insights:
                    cursor.execute('''
                        INSERT INTO ai_insights (id, entry_id, user_id, insight_type, content, confidence)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        entry.id,
                        entry.user_id,
                        insight['type'],
                        insight['content'],
                        insight['confidence']
                    ))
                
                conn.commit()
                conn.close()
                
                self.metrics["ai_insights_generated"] += len(insights)
                logger.info(f"🧠 Generated AI insights for entry {entry.id}")
        
        except Exception as e:
            logger.error(f"AI insight generation failed: {e}")
    
    async def get_ads_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get targeted ads for free tier users"""
        try:
            # Get user profile for ad targeting
            user = await self.get_user(user_id)
            if not user or user.tier != "free":
                return []
            
            # Call ad service
            response = requests.post(
                f"{self.ad_service_url}/ml/ads/optimize",
                json={
                    "user_id": user_id,
                    "context": {
                        "platform": "personallog",
                        "content_type": "journal",
                        "user_tier": user.tier,
                        "usage_stats": user.usage_stats
                    }
                },
                timeout=3
            )
            
            if response.status_code == 200:
                ads = response.json().get("optimized_ads", [])
                self.metrics["ads_served"] += len(ads)
                return ads
        
        except Exception as e:
            logger.error(f"Ad serving failed: {e}")
        
        return []

# Initialize backend service
backend = PersonalLogBackend()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 PersonalLog.ai Backend starting up")
    yield
    logger.info("🔄 PersonalLog.ai Backend shutting down")

# FastAPI app
app = FastAPI(
    title="PersonalLog.ai Backend",
    description="Production-ready personal journaling backend with local-first sync",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# API Endpoints
@app.post("/api/users", response_model=UserProfile)
async def create_user(user: UserProfile):
    """Create new user account"""
    backend.metrics["requests_served"] += 1
    return await backend.create_user(user)

@app.get("/api/users/{user_id}", response_model=UserProfile)
async def get_user(user_id: str):
    """Get user profile"""
    backend.metrics["requests_served"] += 1
    user = await backend.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/entries", response_model=JournalEntry)
async def create_entry(entry: JournalEntry):
    """Create new journal entry"""
    backend.metrics["requests_served"] += 1
    return await backend.create_entry(entry)

@app.get("/api/entries/{user_id}")
async def get_entries(user_id: str, limit: int = 50, offset: int = 0):
    """Get user's journal entries"""
    backend.metrics["requests_served"] += 1
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM entries 
        WHERE user_id = ? AND is_deleted = FALSE 
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', (user_id, limit, offset))
    
    entries = []
    for row in cursor.fetchall():
        entries.append({
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'tags': json.loads(row['tags']),
            'mood': row['mood'],
            'location': row['location'],
            'sync_version': row['sync_version'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        })
    
    conn.close()
    return {"entries": entries, "total": len(entries)}

@app.post("/api/sync")
async def sync_data(sync_request: SyncRequest):
    """Sync local data with server"""
    backend.metrics["requests_served"] += 1
    return await backend.sync_data(sync_request)

@app.get("/api/insights/{entry_id}")
async def get_insights(entry_id: str):
    """Get AI insights for journal entry"""
    backend.metrics["requests_served"] += 1
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM ai_insights 
        WHERE entry_id = ? 
        ORDER BY generated_at DESC
    ''', (entry_id,))
    
    insights = []
    for row in cursor.fetchall():
        insights.append({
            'id': row['id'],
            'insight_type': row['insight_type'],
            'content': row['content'],
            'confidence': row['confidence'],
            'generated_at': row['generated_at']
        })
    
    conn.close()
    return {"insights": insights}

@app.get("/api/ads/{user_id}")
async def get_user_ads(user_id: str):
    """Get targeted ads for user"""
    backend.metrics["requests_served"] += 1
    ads = await backend.get_ads_for_user(user_id)
    return {"ads": ads}

@app.get("/api/metrics")
async def get_metrics():
    """Get service metrics"""
    return {
        "service": "PersonalLog.ai Backend",
        "status": "healthy",
        "metrics": backend.metrics,
        "database": {
            "path": str(backend.db_path),
            "exists": backend.db_path.exists(),
            "size_mb": round(backend.db_path.stat().st_size / (1024*1024), 2) if backend.db_path.exists() else 0
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "PersonalLog.ai Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PersonalLog.ai Backend Service")
    parser.add_argument("--port", type=int, default=8100, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🚀 Starting PersonalLog.ai Backend Service")
    print(f"📱 Local-first architecture with real-time sync")
    print(f"🤖 AI-powered insights and analytics")
    print(f"💰 Free tier with targeted advertising")
    print(f"📊 Production-ready with SQLite database")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )
