#!/usr/bin/env python3

import os
import sys
import json
import uuid
import hashlib
import secrets
import base64
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import aioredis
import asyncpg
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import bcrypt
import jwt
from fastapi import FastAPI, HTTPException, Depends, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class APIKeyStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"
    REVOKED = "revoked"

class APIKeyScope(Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"
    UPLOAD = "upload"
    DELETE = "delete"

@dataclass
class APIKey:
    id: str
    key_prefix: str
    key_hash: str
    name: str
    description: str
    user_id: str
    organization_id: str
    scopes: List[str]
    status: APIKeyStatus
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit: int
    rate_window: int
    ip_whitelist: List[str]
    metadata: Dict[str, Any]

class CreateAPIKeyRequest(BaseModel):
    name: str = Field(..., max_length=100)
    description: str = Field("", max_length=500)
    scopes: List[str]
    expires_days: Optional[int] = Field(None, ge=1, le=365)
    rate_limit: int = Field(1000, ge=1, le=100000)
    rate_window: int = Field(3600, ge=60, le=86400)
    ip_whitelist: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class UpdateAPIKeyRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scopes: Optional[List[str]] = None
    status: Optional[str] = None
    rate_limit: Optional[int] = Field(None, ge=1, le=100000)
    rate_window: Optional[int] = Field(None, ge=60, le=86400)
    ip_whitelist: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class APIKeyResponse(BaseModel):
    id: str
    key_prefix: str
    name: str
    description: str
    scopes: List[str]
    status: str
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    rate_limit: int
    rate_window: int
    ip_whitelist: List[str]
    metadata: Dict[str, Any]

class APIKeyService:
    def __init__(self):
        self.redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')
        self.postgres_url = os.getenv('DATABASE_URL', 'postgresql://user:pass@postgres:5432/activelog')
        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        self.jwt_secret = os.getenv('JWT_SECRET', 'your-jwt-secret-here')
        
    def _get_encryption_key(self) -> bytes:
        """Get or generate encryption key for API keys."""
        key_env = os.getenv('API_KEY_ENCRYPTION_KEY')
        if key_env:
            return base64.urlsafe_b64decode(key_env)
        
        # Generate key from password
        password = os.getenv('API_KEY_PASSWORD', 'default-password').encode()
        salt = b'activelog-api-keys'  # In production, use random salt stored securely
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))
    
    async def initialize(self):
        """Initialize database connections and schema."""
        self.redis = await aioredis.from_url(self.redis_url)
        self.db = await asyncpg.connect(self.postgres_url)
        await self._create_tables()
    
    async def _create_tables(self):
        """Create database tables for API keys."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id VARCHAR(36) PRIMARY KEY,
                key_prefix VARCHAR(20) NOT NULL,
                key_hash VARCHAR(255) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                description TEXT,
                user_id VARCHAR(36) NOT NULL,
                organization_id VARCHAR(36) NOT NULL,
                scopes JSONB NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'active',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                expires_at TIMESTAMP WITH TIME ZONE,
                last_used_at TIMESTAMP WITH TIME ZONE,
                usage_count INTEGER DEFAULT 0,
                rate_limit INTEGER DEFAULT 1000,
                rate_window INTEGER DEFAULT 3600,
                ip_whitelist JSONB DEFAULT '[]',
                metadata JSONB DEFAULT '{}'
            );
            
            CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
            CREATE INDEX IF NOT EXISTS idx_api_keys_organization_id ON api_keys(organization_id);
            CREATE INDEX IF NOT EXISTS idx_api_keys_status ON api_keys(status);
            CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON api_keys(key_prefix);
            
            CREATE TABLE IF NOT EXISTS api_key_usage (
                id SERIAL PRIMARY KEY,
                api_key_id VARCHAR(36) NOT NULL,
                endpoint VARCHAR(255) NOT NULL,
                method VARCHAR(10) NOT NULL,
                status_code INTEGER NOT NULL,
                response_time_ms INTEGER,
                ip_address INET,
                user_agent TEXT,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                request_size INTEGER,
                response_size INTEGER
            );
            
            CREATE INDEX IF NOT EXISTS idx_api_key_usage_key_id ON api_key_usage(api_key_id);
            CREATE INDEX IF NOT EXISTS idx_api_key_usage_timestamp ON api_key_usage(timestamp);
        """)
    
    def _generate_api_key(self) -> tuple[str, str, str]:
        """Generate a new API key with prefix and hash."""
        # Generate random key
        key_bytes = secrets.token_bytes(32)
        key_b64 = base64.urlsafe_b64encode(key_bytes).decode().rstrip('=')
        
        # Create prefix (first 8 characters)
        prefix = f"ak_{key_b64[:8]}"
        
        # Full key
        full_key = f"{prefix}_{key_b64[8:]}"
        
        # Hash for storage
        key_hash = bcrypt.hashpw(full_key.encode(), bcrypt.gensalt()).decode()
        
        return full_key, prefix, key_hash
    
    def _verify_api_key(self, provided_key: str, stored_hash: str) -> bool:
        """Verify API key against stored hash."""
        return bcrypt.checkpw(provided_key.encode(), stored_hash.encode())
    
    async def create_api_key(self, request: CreateAPIKeyRequest, user_id: str, organization_id: str) -> tuple[str, APIKey]:
        """Create a new API key."""
        # Validate scopes
        valid_scopes = [scope.value for scope in APIKeyScope]
        for scope in request.scopes:
            if scope not in valid_scopes:
                raise ValueError(f"Invalid scope: {scope}")
        
        # Generate key
        full_key, prefix, key_hash = self._generate_api_key()
        
        # Calculate expiry
        expires_at = None
        if request.expires_days:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
        
        # Create API key record
        api_key_id = str(uuid.uuid4())
        api_key = APIKey(
            id=api_key_id,
            key_prefix=prefix,
            key_hash=key_hash,
            name=request.name,
            description=request.description,
            user_id=user_id,
            organization_id=organization_id,
            scopes=request.scopes,
            status=APIKeyStatus.ACTIVE,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            last_used_at=None,
            usage_count=0,
            rate_limit=request.rate_limit,
            rate_window=request.rate_window,
            ip_whitelist=request.ip_whitelist,
            metadata=request.metadata
        )
        
        # Store in database
        await self.db.execute("""
            INSERT INTO api_keys (
                id, key_prefix, key_hash, name, description, user_id, organization_id,
                scopes, status, created_at, expires_at, rate_limit, rate_window,
                ip_whitelist, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
        """, api_key_id, prefix, key_hash, request.name, request.description,
            user_id, organization_id, json.dumps(request.scopes), 
            api_key.status.value, api_key.created_at, expires_at,
            request.rate_limit, request.rate_window,
            json.dumps(request.ip_whitelist), json.dumps(request.metadata))
        
        # Log creation
        logger.info(f"Created API key {api_key_id} for user {user_id}")
        
        return full_key, api_key
    
    async def validate_api_key(self, provided_key: str, ip_address: str = None) -> Optional[APIKey]:
        """Validate an API key and return associated data."""
        if not provided_key.startswith('ak_'):
            return None
        
        try:
            # Extract prefix
            parts = provided_key.split('_', 2)
            if len(parts) != 3:
                return None
            
            prefix = f"{parts[0]}_{parts[1]}"
            
            # Get key from database
            row = await self.db.fetchrow("""
                SELECT * FROM api_keys WHERE key_prefix = $1 AND status = 'active'
            """, prefix)
            
            if not row:
                return None
            
            # Verify key hash
            if not self._verify_api_key(provided_key, row['key_hash']):
                return None
            
            # Check expiry
            if row['expires_at'] and row['expires_at'] < datetime.utcnow():
                await self._update_key_status(row['id'], APIKeyStatus.EXPIRED)
                return None
            
            # Check IP whitelist
            if row['ip_whitelist'] and ip_address:
                whitelist = json.loads(row['ip_whitelist'])
                if whitelist and ip_address not in whitelist:
                    logger.warning(f"API key {row['id']} accessed from unauthorized IP {ip_address}")
                    return None
            
            # Check rate limit
            if not await self._check_rate_limit(row['id'], row['rate_limit'], row['rate_window']):
                logger.warning(f"Rate limit exceeded for API key {row['id']}")
                return None
            
            # Update last used
            await self._update_last_used(row['id'])
            
            # Convert to APIKey object
            api_key = APIKey(
                id=row['id'],
                key_prefix=row['key_prefix'],
                key_hash=row['key_hash'],
                name=row['name'],
                description=row['description'] or "",
                user_id=row['user_id'],
                organization_id=row['organization_id'],
                scopes=json.loads(row['scopes']),
                status=APIKeyStatus(row['status']),
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                last_used_at=row['last_used_at'],
                usage_count=row['usage_count'],
                rate_limit=row['rate_limit'],
                rate_window=row['rate_window'],
                ip_whitelist=json.loads(row['ip_whitelist']),
                metadata=json.loads(row['metadata'])
            )
            
            return api_key
            
        except Exception as e:
            logger.error(f"Error validating API key: {e}")
            return None
    
    async def _check_rate_limit(self, api_key_id: str, rate_limit: int, rate_window: int) -> bool:
        """Check if API key is within rate limits."""
        current_time = datetime.utcnow()
        window_start = current_time - timedelta(seconds=rate_window)
        
        # Count requests in window
        count = await self.redis.eval("""
            local key = KEYS[1]
            local window_start = ARGV[1]
            local window_end = ARGV[2]
            local limit = tonumber(ARGV[3])
            
            -- Remove old entries
            redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
            
            -- Count current entries
            local current = redis.call('ZCARD', key)
            
            if current < limit then
                -- Add current request
                redis.call('ZADD', key, window_end, window_end)
                redis.call('EXPIRE', key, 3600)  -- 1 hour TTL
                return 1
            else
                return 0
            end
        """, 1, f"rate_limit:{api_key_id}", window_start.timestamp(), 
            current_time.timestamp(), rate_limit)
        
        return bool(count)
    
    async def _update_last_used(self, api_key_id: str):
        """Update last used timestamp and increment usage count."""
        await self.db.execute("""
            UPDATE api_keys 
            SET last_used_at = NOW(), usage_count = usage_count + 1 
            WHERE id = $1
        """, api_key_id)
    
    async def _update_key_status(self, api_key_id: str, status: APIKeyStatus):
        """Update API key status."""
        await self.db.execute("""
            UPDATE api_keys SET status = $1 WHERE id = $2
        """, status.value, api_key_id)
    
    async def get_user_api_keys(self, user_id: str) -> List[APIKey]:
        """Get all API keys for a user."""
        rows = await self.db.fetch("""
            SELECT * FROM api_keys WHERE user_id = $1 ORDER BY created_at DESC
        """, user_id)
        
        api_keys = []
        for row in rows:
            api_key = APIKey(
                id=row['id'],
                key_prefix=row['key_prefix'],
                key_hash=row['key_hash'],
                name=row['name'],
                description=row['description'] or "",
                user_id=row['user_id'],
                organization_id=row['organization_id'],
                scopes=json.loads(row['scopes']),
                status=APIKeyStatus(row['status']),
                created_at=row['created_at'],
                expires_at=row['expires_at'],
                last_used_at=row['last_used_at'],
                usage_count=row['usage_count'],
                rate_limit=row['rate_limit'],
                rate_window=row['rate_window'],
                ip_whitelist=json.loads(row['ip_whitelist']),
                metadata=json.loads(row['metadata'])
            )
            api_keys.append(api_key)
        
        return api_keys
    
    async def update_api_key(self, api_key_id: str, user_id: str, request: UpdateAPIKeyRequest) -> Optional[APIKey]:
        """Update an API key."""
        # Verify ownership
        row = await self.db.fetchrow("""
            SELECT * FROM api_keys WHERE id = $1 AND user_id = $2
        """, api_key_id, user_id)
        
        if not row:
            return None
        
        # Build update query
        updates = []
        values = []
        param_count = 0
        
        if request.name is not None:
            param_count += 1
            updates.append(f"name = ${param_count}")
            values.append(request.name)
        
        if request.description is not None:
            param_count += 1
            updates.append(f"description = ${param_count}")
            values.append(request.description)
        
        if request.scopes is not None:
            # Validate scopes
            valid_scopes = [scope.value for scope in APIKeyScope]
            for scope in request.scopes:
                if scope not in valid_scopes:
                    raise ValueError(f"Invalid scope: {scope}")
            
            param_count += 1
            updates.append(f"scopes = ${param_count}")
            values.append(json.dumps(request.scopes))
        
        if request.status is not None:
            try:
                status = APIKeyStatus(request.status)
                param_count += 1
                updates.append(f"status = ${param_count}")
                values.append(status.value)
            except ValueError:
                raise ValueError(f"Invalid status: {request.status}")
        
        if request.rate_limit is not None:
            param_count += 1
            updates.append(f"rate_limit = ${param_count}")
            values.append(request.rate_limit)
        
        if request.rate_window is not None:
            param_count += 1
            updates.append(f"rate_window = ${param_count}")
            values.append(request.rate_window)
        
        if request.ip_whitelist is not None:
            param_count += 1
            updates.append(f"ip_whitelist = ${param_count}")
            values.append(json.dumps(request.ip_whitelist))
        
        if request.metadata is not None:
            param_count += 1
            updates.append(f"metadata = ${param_count}")
            values.append(json.dumps(request.metadata))
        
        if not updates:
            # No updates
            return await self.get_api_key(api_key_id, user_id)
        
        # Add WHERE clause parameters
        param_count += 1
        values.append(api_key_id)
        param_count += 1
        values.append(user_id)
        
        query = f"""
            UPDATE api_keys 
            SET {', '.join(updates)} 
            WHERE id = ${param_count-1} AND user_id = ${param_count}
        """
        
        await self.db.execute(query, *values)
        
        # Return updated key
        return await self.get_api_key(api_key_id, user_id)
    
    async def get_api_key(self, api_key_id: str, user_id: str) -> Optional[APIKey]:
        """Get a specific API key."""
        row = await self.db.fetchrow("""
            SELECT * FROM api_keys WHERE id = $1 AND user_id = $2
        """, api_key_id, user_id)
        
        if not row:
            return None
        
        return APIKey(
            id=row['id'],
            key_prefix=row['key_prefix'],
            key_hash=row['key_hash'],
            name=row['name'],
            description=row['description'] or "",
            user_id=row['user_id'],
            organization_id=row['organization_id'],
            scopes=json.loads(row['scopes']),
            status=APIKeyStatus(row['status']),
            created_at=row['created_at'],
            expires_at=row['expires_at'],
            last_used_at=row['last_used_at'],
            usage_count=row['usage_count'],
            rate_limit=row['rate_limit'],
            rate_window=row['rate_window'],
            ip_whitelist=json.loads(row['ip_whitelist']),
            metadata=json.loads(row['metadata'])
        )
    
    async def revoke_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Revoke an API key."""
        result = await self.db.execute("""
            UPDATE api_keys SET status = 'revoked' 
            WHERE id = $1 AND user_id = $2
        """, api_key_id, user_id)
        
        if result == "UPDATE 1":
            # Remove from Redis cache
            await self.redis.delete(f"rate_limit:{api_key_id}")
            logger.info(f"Revoked API key {api_key_id} for user {user_id}")
            return True
        
        return False
    
    async def log_api_usage(self, api_key_id: str, endpoint: str, method: str, 
                           status_code: int, response_time_ms: int, ip_address: str,
                           user_agent: str, request_size: int, response_size: int):
        """Log API key usage."""
        await self.db.execute("""
            INSERT INTO api_key_usage (
                api_key_id, endpoint, method, status_code, response_time_ms,
                ip_address, user_agent, request_size, response_size
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """, api_key_id, endpoint, method, status_code, response_time_ms,
            ip_address, user_agent, request_size, response_size)
    
    async def get_usage_stats(self, api_key_id: str, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get usage statistics for an API key."""
        # Verify ownership
        key_exists = await self.db.fetchval("""
            SELECT 1 FROM api_keys WHERE id = $1 AND user_id = $2
        """, api_key_id, user_id)
        
        if not key_exists:
            return {}
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Total requests
        total_requests = await self.db.fetchval("""
            SELECT COUNT(*) FROM api_key_usage 
            WHERE api_key_id = $1 AND timestamp >= $2
        """, api_key_id, since_date)
        
        # Requests by status code
        status_codes = await self.db.fetch("""
            SELECT status_code, COUNT(*) as count
            FROM api_key_usage 
            WHERE api_key_id = $1 AND timestamp >= $2
            GROUP BY status_code
            ORDER BY status_code
        """, api_key_id, since_date)
        
        # Requests by endpoint
        endpoints = await self.db.fetch("""
            SELECT endpoint, COUNT(*) as count
            FROM api_key_usage 
            WHERE api_key_id = $1 AND timestamp >= $2
            GROUP BY endpoint
            ORDER BY count DESC
            LIMIT 10
        """, api_key_id, since_date)
        
        # Average response time
        avg_response_time = await self.db.fetchval("""
            SELECT AVG(response_time_ms) FROM api_key_usage 
            WHERE api_key_id = $1 AND timestamp >= $2
        """, api_key_id, since_date)
        
        # Requests over time (daily)
        daily_usage = await self.db.fetch("""
            SELECT DATE(timestamp) as date, COUNT(*) as count
            FROM api_key_usage 
            WHERE api_key_id = $1 AND timestamp >= $2
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, api_key_id, since_date)
        
        return {
            'total_requests': total_requests or 0,
            'status_codes': {str(row['status_code']): row['count'] for row in status_codes},
            'top_endpoints': [{'endpoint': row['endpoint'], 'count': row['count']} for row in endpoints],
            'average_response_time_ms': float(avg_response_time) if avg_response_time else 0,
            'daily_usage': [{'date': row['date'].isoformat(), 'count': row['count']} for row in daily_usage],
            'period_days': days
        }

# FastAPI Application
app = FastAPI(title="ActiveLog API Key Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
api_key_service = APIKeyService()
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> Dict[str, str]:
    """Get current user from JWT token."""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, api_key_service.jwt_secret, algorithms=["HS256"])
        user_id = payload.get("user_id")
        organization_id = payload.get("organization_id")
        
        if not user_id or not organization_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        return {"user_id": user_id, "organization_id": organization_id}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.on_event("startup")
async def startup():
    await api_key_service.initialize()

@app.post("/api/v1/keys", response_model=Dict[str, Any])
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user: Dict[str, str] = Depends(get_current_user)
):
    """Create a new API key."""
    try:
        full_key, api_key = await api_key_service.create_api_key(
            request, current_user["user_id"], current_user["organization_id"]
        )
        
        return {
            "api_key": full_key,
            "key_info": APIKeyResponse(
                id=api_key.id,
                key_prefix=api_key.key_prefix,
                name=api_key.name,
                description=api_key.description,
                scopes=api_key.scopes,
                status=api_key.status.value,
                created_at=api_key.created_at,
                expires_at=api_key.expires_at,
                last_used_at=api_key.last_used_at,
                usage_count=api_key.usage_count,
                rate_limit=api_key.rate_limit,
                rate_window=api_key.rate_window,
                ip_whitelist=api_key.ip_whitelist,
                metadata=api_key.metadata
            ).dict()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/keys", response_model=List[APIKeyResponse])
async def list_api_keys(current_user: Dict[str, str] = Depends(get_current_user)):
    """List all API keys for the current user."""
    api_keys = await api_key_service.get_user_api_keys(current_user["user_id"])
    
    return [
        APIKeyResponse(
            id=key.id,
            key_prefix=key.key_prefix,
            name=key.name,
            description=key.description,
            scopes=key.scopes,
            status=key.status.value,
            created_at=key.created_at,
            expires_at=key.expires_at,
            last_used_at=key.last_used_at,
            usage_count=key.usage_count,
            rate_limit=key.rate_limit,
            rate_window=key.rate_window,
            ip_whitelist=key.ip_whitelist,
            metadata=key.metadata
        ) for key in api_keys
    ]

@app.get("/api/v1/keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: Dict[str, str] = Depends(get_current_user)
):
    """Get a specific API key."""
    api_key = await api_key_service.get_api_key(key_id, current_user["user_id"])
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return APIKeyResponse(
        id=api_key.id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        description=api_key.description,
        scopes=api_key.scopes,
        status=api_key.status.value,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        last_used_at=api_key.last_used_at,
        usage_count=api_key.usage_count,
        rate_limit=api_key.rate_limit,
        rate_window=api_key.rate_window,
        ip_whitelist=api_key.ip_whitelist,
        metadata=api_key.metadata
    )

@app.put("/api/v1/keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: str,
    request: UpdateAPIKeyRequest,
    current_user: Dict[str, str] = Depends(get_current_user)
):
    """Update an API key."""
    try:
        api_key = await api_key_service.update_api_key(key_id, current_user["user_id"], request)
        
        if not api_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        return APIKeyResponse(
            id=api_key.id,
            key_prefix=api_key.key_prefix,
            name=api_key.name,
            description=api_key.description,
            scopes=api_key.scopes,
            status=api_key.status.value,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            last_used_at=api_key.last_used_at,
            usage_count=api_key.usage_count,
            rate_limit=api_key.rate_limit,
            rate_window=api_key.rate_window,
            ip_whitelist=api_key.ip_whitelist,
            metadata=api_key.metadata
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/v1/keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: Dict[str, str] = Depends(get_current_user)
):
    """Revoke an API key."""
    success = await api_key_service.revoke_api_key(key_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return {"message": "API key revoked successfully"}

@app.get("/api/v1/keys/{key_id}/usage")
async def get_api_key_usage(
    key_id: str,
    days: int = 30,
    current_user: Dict[str, str] = Depends(get_current_user)
):
    """Get usage statistics for an API key."""
    stats = await api_key_service.get_usage_stats(key_id, current_user["user_id"], days)
    
    if not stats:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return stats

@app.post("/api/v1/validate")
async def validate_api_key_endpoint(api_key: str, ip_address: str = None):
    """Validate an API key (internal endpoint)."""
    key_data = await api_key_service.validate_api_key(api_key, ip_address)
    
    if not key_data:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return {
        "valid": True,
        "key_id": key_data.id,
        "user_id": key_data.user_id,
        "organization_id": key_data.organization_id,
        "scopes": key_data.scopes,
        "rate_limit": key_data.rate_limit,
        "rate_window": key_data.rate_window
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)