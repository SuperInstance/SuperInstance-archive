#!/usr/bin/env python3
"""
FishingLog.ai Backend Service - World-Class Production Ready
Advanced backend with fishing-specific features, AI insights, and performance
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
        logging.FileHandler('logs/fishinglog_backend.log'),
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

# Enhanced Data Models with fishing-specific validation
class FishingEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: constr(min_length=1, max_length=100)
    title: constr(min_length=1, max_length=200)
    content: constr(min_length=1, max_length=50000)  # 50k characters max
    fish_type: constr(min_length=1, max_length=100)  # Required fishing field
    location: constr(min_length=1, max_length=200)   # Required for fishing
    weight: Optional[float] = Field(ge=0.0, le=1000.0)  # Weight in pounds/kg
    length: Optional[float] = Field(ge=0.0, le=200.0)    # Length in inches/cm
    bait_used: Optional[constr(max_length=100)] = None
    technique: Optional[constr(max_length=100)] = None
    weather_conditions: Optional[constr(max_length=200)] = None
    water_temperature: Optional[float] = Field(ge=-10.0, le=50.0)  # Celsius
    water_clarity: Optional[constr(regex=r'^(clear|murky|stained|muddy)$')] = None
    tags: List[constr(max_length=50)] = Field(default_factory=list, max_items=10)
    mood: Optional[constr(regex=r'^(excited|peaceful|frustrated|accomplished|hopeful|disappointed|thrilled|relaxed)$')] = None
    catch_released: bool = Field(default=True)
    photo_urls: List[str] = Field(default_factory=list, max_items=5)
    gps_coordinates: Optional[Dict[str, float]] = None  # {"lat": 0.0, "lon": 0.0}
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
    
    @validator('fish_type')
    def validate_fish_type(cls, v):
        # Clean and validate fish type
        return v.strip().title()
    
    @validator('location')
    def validate_location(cls, v):
        # Ensure location is provided and clean
        return v.strip()
    
    @validator('weight')
    def validate_weight(cls, v):
        # Ensure reasonable weight values
        if v is not None and v < 0:
            raise ValueError('Weight cannot be negative')
        return v
    
    @validator('gps_coordinates')
    def validate_coordinates(cls, v):
        if v is not None:
            if not isinstance(v, dict):
                raise ValueError('GPS coordinates must be a dictionary')
            if 'lat' not in v or 'lon' not in v:
                raise ValueError('GPS coordinates must include lat and lon')
            if not (-90 <= v['lat'] <= 90):
                raise ValueError('Latitude must be between -90 and 90')
            if not (-180 <= v['lon'] <= 180):
                raise ValueError('Longitude must be between -180 and 180')
        return v
    
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
        "catches_logged": 0,
        "ai_insights_used": 0,
        "total_weight_caught": 0,
        "login_count": 0,
        "streak_days": 0,
        "favorite_locations": 0,
        "species_caught": 0
    })
    fishing_preferences: Dict[str, Any] = Field(default_factory=lambda: {
        "preferred_techniques": [],
        "favorite_species": [],
        "preferred_locations": [],
        "typical_fishing_times": [],
        "measurement_unit": "imperial"  # or "metric"
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

class FishingInsight(BaseModel):
    entry_id: str
    insight_type: str = Field(regex=r'^(species_analysis|location_patterns|seasonal_trends|technique_effectiveness|catch_predictions|weather_correlation|hotspot_identification)$')
    content: constr(max_length=2000)
    confidence: float = Field(ge=0.0, le=1.0)
    generated_at: datetime = Field(default_factory=datetime.now)
    model_version: str = '1.0'
    processing_time_ms: Optional[float] = None

class FishingAnalytics(BaseModel):
    user_id: str
    catch_patterns: Dict[str, Any]
    species_trends: Dict[str, Any]
    location_analytics: Dict[str, Any]
    seasonal_analysis: Dict[str, Any]
    success_metrics: Dict[str, Any]
    recommendations: List[str]
    last_updated: datetime = Field(default_factory=datetime.now)

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

class FishingLogBackend:
    """World-class FishingLog backend with enterprise features"""
    
    def __init__(self):
        self.db_path = Path("data/fishinglog.db")
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
        self.weather_service_url = os.getenv("WEATHER_SERVICE_URL", "http://localhost:8093")
        
        # Enhanced performance metrics
        self.metrics = {
            "requests_served": 0,
            "catches_synced": 0,
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
            "security_events": 0,
            "total_catches_logged": 0,
            "unique_species_logged": 0,
            "unique_locations_logged": 0
        }
        
        # Rate limiting tracking
        self.rate_limit_tracker = defaultdict(lambda: {'count': 0, 'reset_time': time.time() + 3600})
    
    def init_database(self):
        """Initialize SQLite database with enhanced schema and fishing-specific features"""
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
                fishing_preferences TEXT DEFAULT '{}',
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
        
        # Enhanced fishing entries table with fishing-specific fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_entries (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                content_encrypted TEXT,  -- For premium users
                fish_type TEXT NOT NULL,
                location TEXT NOT NULL,
                weight REAL,
                length REAL,
                bait_used TEXT,
                technique TEXT,
                weather_conditions TEXT,
                water_temperature REAL,
                water_clarity TEXT CHECK (water_clarity IN ('clear', 'murky', 'stained', 'muddy') OR water_clarity IS NULL),
                tags TEXT DEFAULT '[]',
                mood TEXT CHECK (mood IN ('excited', 'peaceful', 'frustrated', 'accomplished', 'hopeful', 'disappointed', 'thrilled', 'relaxed') OR mood IS NULL),
                catch_released BOOLEAN DEFAULT TRUE,
                photo_urls TEXT DEFAULT '[]',
                gps_coordinates TEXT,  -- JSON: {"lat": 0.0, "lon": 0.0}
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
                fish_type TEXT NOT NULL,
                location TEXT NOT NULL,
                weight REAL,
                modified_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES fishing_entries (id) ON DELETE CASCADE,
                FOREIGN KEY (modified_by) REFERENCES users (id),
                UNIQUE(entry_id, version_number)
            )
        ''')
        
        # Enhanced AI insights table for fishing-specific insights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_insights (
                id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                insight_type TEXT NOT NULL CHECK (insight_type IN (
                    'species_analysis', 'location_patterns', 'seasonal_trends', 
                    'technique_effectiveness', 'catch_predictions', 'weather_correlation',
                    'hotspot_identification'
                )),
                content TEXT NOT NULL,
                confidence REAL DEFAULT 0.0 CHECK (confidence >= 0.0 AND confidence <= 1.0),
                model_version TEXT DEFAULT '1.0',
                processing_time_ms REAL,
                metadata TEXT DEFAULT '{}',
                is_dismissed BOOLEAN DEFAULT FALSE,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entry_id) REFERENCES fishing_entries (id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Fishing-specific analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_analytics (
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
        
        # Species master table for standardization
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fish_species (
                id TEXT PRIMARY KEY,
                common_name TEXT NOT NULL,
                scientific_name TEXT,
                category TEXT,
                typical_weight_range TEXT,
                typical_length_range TEXT,
                habitat TEXT,
                season TEXT,
                popular_techniques TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Locations table for popular fishing spots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_locations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                gps_coordinates TEXT,
                location_type TEXT CHECK (location_type IN ('lake', 'river', 'ocean', 'pond', 'stream', 'bay')),
                popular_species TEXT DEFAULT '[]',
                access_info TEXT,
                regulations TEXT,
                user_added BOOLEAN DEFAULT FALSE,
                user_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # User achievements for fishing milestones
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fishing_achievements (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                achievement_type TEXT NOT NULL,
                achievement_data TEXT,
                species_related TEXT,
                weight_milestone REAL,
                count_milestone INTEGER,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        ''')
        
        # Weather data integration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weather_data (
                id TEXT PRIMARY KEY,
                location TEXT NOT NULL,
                date TEXT NOT NULL,
                temperature REAL,
                conditions TEXT,
                wind_speed REAL,
                pressure REAL,
                humidity REAL,
                precipitation REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(location, date)
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
        
        # Create comprehensive indexes for performance
        # Users indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active, last_active)')
        
        # Fishing entries indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_user_id ON fishing_entries(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_created_at ON fishing_entries(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_fish_type ON fishing_entries(fish_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_location ON fishing_entries(location)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_weight ON fishing_entries(weight)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_user_created ON fishing_entries(user_id, created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_sync ON fishing_entries(user_id, sync_version)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_deleted ON fishing_entries(is_deleted, deleted_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_fishing_entries_gps ON fishing_entries(gps_coordinates)')
        
        # AI insights indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_entry_id ON ai_insights(entry_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_user_type ON ai_insights(user_id, insight_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_insights_generated ON ai_insights(generated_at DESC)')
        
        # Species and locations indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_species_common_name ON fish_species(common_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_locations_name ON fishing_locations(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_locations_type ON fishing_locations(location_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_locations_gps ON fishing_locations(gps_coordinates)')
        
        # Sessions and security indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_user ON user_sessions(user_id, is_active)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_user ON security_audit(user_id, timestamp DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_security_event ON security_audit(event_type, timestamp DESC)')
        
        # Analytics and weather indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_analytics_user ON fishing_analytics(user_id, analytics_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_weather_location_date ON weather_data(location, date)')
        
        conn.commit()
        
        # Populate some default fish species
        self._populate_default_species(cursor)
        
        # Cleanup expired sessions and backups on startup
        self._cleanup_expired_data(cursor)
        
        conn.commit()
        conn.close()
        logger.info("✅ FishingLog database initialized with fishing-specific features")
    
    def _populate_default_species(self, cursor):
        """Populate database with common fish species"""
        default_species = [
            ('bass', 'Largemouth Bass', 'Micropterus salmoides', 'Freshwater Sport Fish', '1-15 lbs', '12-25 inches', 'Lakes, Ponds, Rivers', 'Spring-Fall', 'Plastic worms, crankbaits, jigs'),
            ('trout', 'Rainbow Trout', 'Oncorhynchus mykiss', 'Freshwater Game Fish', '0.5-5 lbs', '8-16 inches', 'Cold streams, lakes', 'Spring-Fall', 'Flies, small lures, bait'),
            ('salmon', 'Chinook Salmon', 'Oncorhynchus tshawytscha', 'Anadromous Game Fish', '10-50 lbs', '28-48 inches', 'Ocean, rivers', 'Summer-Fall', 'Trolling, drift fishing'),
            ('pike', 'Northern Pike', 'Esox lucius', 'Predator Fish', '2-25 lbs', '18-40 inches', 'Northern lakes, rivers', 'Spring-Fall', 'Spoons, spinnerbaits, large baits'),
            ('walleye', 'Walleye', 'Sander vitreus', 'Freshwater Game Fish', '1-10 lbs', '12-20 inches', 'Deep lakes, rivers', 'Year-round', 'Jigs, live bait, trolling')
        ]
        
        for species_data in default_species:
            cursor.execute('''
                INSERT OR IGNORE INTO fish_species (id, common_name, scientific_name, category, 
                    typical_weight_range, typical_length_range, habitat, season, popular_techniques)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (str(uuid.uuid4()), *species_data))
    
    def _cleanup_expired_data(self, cursor):
        """Clean up expired sessions, backups, and old audit logs"""
        now = datetime.now()
        
        # Clean expired sessions
        cursor.execute('DELETE FROM user_sessions WHERE expires_at < ?', (now,))
        
        # Clean old audit logs (keep 90 days)
        ninety_days_ago = now - timedelta(days=90)
        cursor.execute('DELETE FROM security_audit WHERE timestamp < ?', (ninety_days_ago,))
        
        # Clean old weather data (keep 1 year)
        one_year_ago = now - timedelta(days=365)
        cursor.execute('DELETE FROM weather_data WHERE created_at < ?', (one_year_ago,))
        
        logger.info("🧹 Cleaned up expired fishing data")
    
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
                fishing_preferences=json.loads(row['fishing_preferences']),
                usage_stats=json.loads(row['usage_stats']),
                created_at=datetime.fromisoformat(row['created_at']),
                last_active=datetime.fromisoformat(row['last_active'])
            )
        return None
    
    async def create_fishing_entry(self, entry: FishingEntry) -> FishingEntry:
        """Create new fishing entry"""
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
        sync_result = cursor.fetchone()
        if sync_result:
            entry.sync_version = sync_result['last_sync_version']
        
        # Insert fishing entry
        cursor.execute('''
            INSERT INTO fishing_entries (
                id, user_id, title, content, fish_type, location, weight, length,
                bait_used, technique, weather_conditions, water_temperature, water_clarity,
                tags, mood, catch_released, photo_urls, gps_coordinates, sync_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.id, entry.user_id, entry.title, entry.content, entry.fish_type,
            entry.location, entry.weight, entry.length, entry.bait_used, entry.technique,
            entry.weather_conditions, entry.water_temperature, entry.water_clarity,
            json.dumps(entry.tags), entry.mood, entry.catch_released,
            json.dumps(entry.photo_urls), 
            json.dumps(entry.gps_coordinates) if entry.gps_coordinates else None,
            entry.sync_version
        ))
        
        # Update user fishing stats
        weight_to_add = entry.weight or 0
        cursor.execute('''
            UPDATE users 
            SET usage_stats = json_set(usage_stats, '$.catches_logged', 
                json_extract(usage_stats, '$.catches_logged') + 1),
                usage_stats = json_set(usage_stats, '$.total_weight_caught', 
                json_extract(usage_stats, '$.total_weight_caught') + ?),
                last_active = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (weight_to_add, entry.user_id))
        
        conn.commit()
        conn.close()
        
        # Update global metrics
        self.metrics["total_catches_logged"] += 1
        
        # Generate AI insights in background
        asyncio.create_task(self.generate_fishing_insights(entry))
        
        logger.info(f"🎣 Created fishing entry: {entry.title[:30]}... - Fish: {entry.fish_type}")
        return entry
    
    async def generate_fishing_insights(self, entry: FishingEntry):
        """Generate AI insights for fishing entry"""
        try:
            # Prepare fishing-specific data for AI analysis
            fishing_context = {
                "text": entry.content,
                "fish_type": entry.fish_type,
                "location": entry.location,
                "weight": entry.weight,
                "technique": entry.technique,
                "weather": entry.weather_conditions,
                "water_temp": entry.water_temperature,
                "bait": entry.bait_used,
                "type": "fishing_entry",
                "user_id": entry.user_id
            }
            
            # Call AI orchestrator for fishing insights
            response = requests.post(
                f"{self.ai_orchestrator_url}/api/ai/analyze",
                json=fishing_context,
                timeout=5
            )
            
            if response.status_code == 200:
                analysis = response.json()
                
                # Store fishing-specific insights in database
                conn = self.get_db_connection()
                cursor = conn.cursor()
                
                insights = [
                    {
                        "type": "species_analysis",
                        "content": f"Species insight: {analysis.get('species_notes', f'{entry.fish_type} is a great catch!')} Success rate in this area is typically {analysis.get('area_success_rate', 65)}%.",
                        "confidence": analysis.get('species_confidence', 0.8)
                    },
                    {
                        "type": "location_patterns",
                        "content": f"Location analysis: {entry.location} shows good fishing potential. {analysis.get('location_insights', 'Consider trying different times of day for varied results.')}",
                        "confidence": 0.75
                    },
                    {
                        "type": "technique_effectiveness",
                        "content": f"Technique review: {entry.technique or 'Your technique'} {analysis.get('technique_feedback', 'appears effective for this species. Consider varying retrieval speeds.')}",
                        "confidence": 0.7
                    }
                ]
                
                # Add weather correlation if available
                if entry.weather_conditions:
                    insights.append({
                        "type": "weather_correlation",
                        "content": f"Weather impact: {entry.weather_conditions} conditions {analysis.get('weather_impact', 'can significantly affect fishing success. Similar conditions have shown good results.')}",
                        "confidence": 0.6
                    })
                
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
                logger.info(f"🧠 Generated fishing insights for entry {entry.id}")
        
        except Exception as e:
            logger.error(f"Fishing AI insight generation failed: {e}")

# Initialize backend service
backend = FishingLogBackend()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("🚀 FishingLog.ai Backend starting up")
    yield
    logger.info("🔄 FishingLog.ai Backend shutting down")

# FastAPI app
app = FastAPI(
    title="FishingLog.ai Backend",
    description="Production-ready fishing log backend with AI insights and analytics",
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

@app.post("/api/catches", response_model=FishingEntry)
async def create_catch(entry: FishingEntry):
    """Create new fishing catch entry"""
    backend.metrics["requests_served"] += 1
    return await backend.create_fishing_entry(entry)

@app.get("/api/catches/{user_id}")
async def get_catches(user_id: str, limit: int = 50, offset: int = 0, fish_type: str = None, location: str = None):
    """Get user's fishing catch entries with optional filtering"""
    backend.metrics["requests_served"] += 1
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    # Build dynamic query with filters
    where_conditions = ["user_id = ?", "is_deleted = FALSE"]
    params = [user_id]
    
    if fish_type:
        where_conditions.append("fish_type LIKE ?")
        params.append(f"%{fish_type}%")
    
    if location:
        where_conditions.append("location LIKE ?")
        params.append(f"%{location}%")
    
    where_clause = " AND ".join(where_conditions)
    params.extend([limit, offset])
    
    cursor.execute(f'''
        SELECT * FROM fishing_entries 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    ''', params)
    
    catches = []
    for row in cursor.fetchall():
        catch_data = {
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'fish_type': row['fish_type'],
            'location': row['location'],
            'weight': row['weight'],
            'length': row['length'],
            'bait_used': row['bait_used'],
            'technique': row['technique'],
            'weather_conditions': row['weather_conditions'],
            'water_temperature': row['water_temperature'],
            'water_clarity': row['water_clarity'],
            'tags': json.loads(row['tags']) if row['tags'] else [],
            'mood': row['mood'],
            'catch_released': bool(row['catch_released']),
            'photo_urls': json.loads(row['photo_urls']) if row['photo_urls'] else [],
            'gps_coordinates': json.loads(row['gps_coordinates']) if row['gps_coordinates'] else None,
            'sync_version': row['sync_version'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
        catches.append(catch_data)
    
    conn.close()
    return {"catches": catches, "total": len(catches)}

@app.get("/api/insights/{entry_id}")
async def get_insights(entry_id: str):
    """Get AI insights for fishing entry"""
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

@app.get("/api/species")
async def get_fish_species():
    """Get list of fish species"""
    backend.metrics["requests_served"] += 1
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM fish_species ORDER BY common_name')
    
    species = []
    for row in cursor.fetchall():
        species.append({
            'id': row['id'],
            'common_name': row['common_name'],
            'scientific_name': row['scientific_name'],
            'category': row['category'],
            'habitat': row['habitat'],
            'typical_weight_range': row['typical_weight_range'],
            'typical_length_range': row['typical_length_range']
        })
    
    conn.close()
    return {"species": species}

@app.get("/api/analytics/{user_id}")
async def get_fishing_analytics(user_id: str, days: int = 30):
    """Get fishing analytics for user"""
    backend.metrics["requests_served"] += 1
    conn = backend.get_db_connection()
    cursor = conn.cursor()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get catch statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total_catches,
            COUNT(DISTINCT fish_type) as species_count,
            COUNT(DISTINCT location) as locations_count,
            AVG(weight) as avg_weight,
            MAX(weight) as max_weight,
            SUM(CASE WHEN catch_released = 1 THEN 1 ELSE 0 END) as releases,
            COUNT(DISTINCT DATE(created_at)) as fishing_days
        FROM fishing_entries 
        WHERE user_id = ? AND created_at BETWEEN ? AND ? AND is_deleted = FALSE
    ''', (user_id, start_date, end_date))
    
    stats = cursor.fetchone()
    
    # Get top species
    cursor.execute('''
        SELECT fish_type, COUNT(*) as count, AVG(weight) as avg_weight
        FROM fishing_entries 
        WHERE user_id = ? AND created_at BETWEEN ? AND ? AND is_deleted = FALSE
        GROUP BY fish_type
        ORDER BY count DESC
        LIMIT 5
    ''', (user_id, start_date, end_date))
    
    top_species = [dict(row) for row in cursor.fetchall()]
    
    # Get top locations
    cursor.execute('''
        SELECT location, COUNT(*) as count
        FROM fishing_entries 
        WHERE user_id = ? AND created_at BETWEEN ? AND ? AND is_deleted = FALSE
        GROUP BY location
        ORDER BY count DESC
        LIMIT 5
    ''', (user_id, start_date, end_date))
    
    top_locations = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    analytics = {
        "period_days": days,
        "summary": {
            "total_catches": stats['total_catches'] or 0,
            "species_count": stats['species_count'] or 0,
            "locations_count": stats['locations_count'] or 0,
            "avg_weight": round(stats['avg_weight'] or 0, 2),
            "max_weight": stats['max_weight'] or 0,
            "releases": stats['releases'] or 0,
            "fishing_days": stats['fishing_days'] or 0,
            "release_rate": round((stats['releases'] or 0) / max(stats['total_catches'] or 1, 1) * 100, 1)
        },
        "top_species": top_species,
        "top_locations": top_locations
    }
    
    return analytics

@app.get("/api/metrics")
async def get_metrics():
    """Get service metrics"""
    return {
        "service": "FishingLog.ai Backend",
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
        "service": "FishingLog.ai Backend",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="FishingLog.ai Backend Service")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the service on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    
    args = parser.parse_args()
    
    print("🚀 Starting FishingLog.ai Backend Service")
    print(f"🎣 Comprehensive fishing log with catch tracking")
    print(f"🐟 Species identification and analytics")
    print(f"📍 Location-based insights and patterns")
    print(f"🧠 AI-powered fishing recommendations")
    print(f"📊 Production-ready with SQLite database")
    print(f"🌐 Running on http://{args.host}:{args.port}")
    
    uvicorn.run(
        "main:app",
        host=args.host,
        port=args.port,
        reload=False,
        access_log=True
    )