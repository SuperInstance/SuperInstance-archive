#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import hashlib
import boto3
import hvac
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecretConfig(BaseModel):
    name: str
    type: str = Field(..., description="Type of secret (database, api_key, jwt, etc.)")
    rotation_interval_days: int = Field(default=30)
    auto_rotate: bool = Field(default=True)
    backup_versions: int = Field(default=3)
    notification_before_expiry_hours: int = Field(default=24)
    environments: List[str] = Field(default=["production", "staging"])

class SecretValue(BaseModel):
    value: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    version: int
    is_active: bool = True

class RotationResult(BaseModel):
    secret_name: str
    old_version: int
    new_version: int
    status: str
    message: str
    rotated_at: datetime

class SecretsRotationService:
    def __init__(self):
        self.app = FastAPI(title="ActiveLog Secrets Rotation Service")
        self.db_pool = None
        self.redis_client = None
        self.vault_client = None
        self.aws_session = None
        self.scheduler = AsyncIOScheduler()
        
        # Encryption key for local storage
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
        self._setup_routes()
        self._setup_database()
        self._setup_redis()
        self._setup_vault_client()
        self._setup_aws_client()
        self._setup_scheduler()
        
    def _get_or_create_encryption_key(self) -> bytes:
        key_file = "/tmp/secrets_rotation_key"
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)
            return key

    def _setup_database(self):
        try:
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                database=os.getenv("POSTGRES_DB", "activelog_secrets"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                port=int(os.getenv("POSTGRES_PORT", "5432"))
            )
            self._create_tables()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database setup failed: {e}")

    def _setup_redis(self):
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "2")),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis setup failed: {e}")

    def _setup_vault_client(self):
        vault_url = os.getenv("VAULT_URL")
        vault_token = os.getenv("VAULT_TOKEN")
        
        if vault_url and vault_token:
            try:
                self.vault_client = hvac.Client(url=vault_url, token=vault_token)
                if self.vault_client.is_authenticated():
                    logger.info("HashiCorp Vault connection established")
                else:
                    logger.warning("Vault authentication failed")
                    self.vault_client = None
            except Exception as e:
                logger.error(f"Vault setup failed: {e}")

    def _setup_aws_client(self):
        try:
            aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
            aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            aws_region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
            
            if aws_access_key and aws_secret_key:
                self.aws_session = boto3.Session(
                    aws_access_key_id=aws_access_key,
                    aws_secret_access_key=aws_secret_key,
                    region_name=aws_region
                )
                
                # Test connection
                sm_client = self.aws_session.client('secretsmanager')
                sm_client.describe_secret(SecretId='test')  # This will fail but validates credentials
                logger.info("AWS Secrets Manager connection established")
            else:
                logger.info("AWS credentials not provided, AWS Secrets Manager disabled")
        except Exception as e:
            if "ResourceNotFoundException" in str(e):
                logger.info("AWS Secrets Manager connection established")
            else:
                logger.error(f"AWS setup failed: {e}")

    def _create_tables(self):
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS secret_configs (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) UNIQUE NOT NULL,
                        type VARCHAR(100) NOT NULL,
                        rotation_interval_days INTEGER DEFAULT 30,
                        auto_rotate BOOLEAN DEFAULT TRUE,
                        backup_versions INTEGER DEFAULT 3,
                        notification_before_expiry_hours INTEGER DEFAULT 24,
                        environments JSONB DEFAULT '["production"]',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS secret_versions (
                        id SERIAL PRIMARY KEY,
                        secret_name VARCHAR(255) REFERENCES secret_configs(name) ON DELETE CASCADE,
                        version INTEGER NOT NULL,
                        encrypted_value TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        metadata JSONB DEFAULT '{}',
                        UNIQUE(secret_name, version)
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS rotation_history (
                        id SERIAL PRIMARY KEY,
                        secret_name VARCHAR(255) NOT NULL,
                        old_version INTEGER,
                        new_version INTEGER NOT NULL,
                        status VARCHAR(50) NOT NULL,
                        message TEXT,
                        rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        rotated_by VARCHAR(255) DEFAULT 'system'
                    )
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_secret_versions_active 
                    ON secret_versions(secret_name, is_active)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_secret_versions_expires 
                    ON secret_versions(expires_at) WHERE expires_at IS NOT NULL
                """)
                
                conn.commit()
                logger.info("Database tables created/verified")
                
        finally:
            self.db_pool.putconn(conn)

    def _setup_scheduler(self):
        # Schedule rotation checks every hour
        self.scheduler.add_job(
            self._check_and_rotate_secrets,
            CronTrigger(minute=0),
            id='rotation_check',
            replace_existing=True
        )
        
        # Schedule expiry notifications every 6 hours
        self.scheduler.add_job(
            self._check_expiry_notifications,
            CronTrigger(hour='0,6,12,18'),
            id='expiry_notifications',
            replace_existing=True
        )
        
        # Cleanup old versions daily
        self.scheduler.add_job(
            self._cleanup_old_versions,
            CronTrigger(hour=2),
            id='cleanup_versions',
            replace_existing=True
        )

    def _generate_secret_by_type(self, secret_type: str, length: int = 32) -> str:
        if secret_type == "password":
            alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        elif secret_type == "api_key":
            return secrets.token_urlsafe(length)
        elif secret_type == "jwt_secret":
            return secrets.token_urlsafe(64)
        elif secret_type == "encryption_key":
            return Fernet.generate_key().decode()
        elif secret_type == "database_password":
            # Database passwords without special characters that might cause issues
            alphabet = string.ascii_letters + string.digits
            return ''.join(secrets.choice(alphabet) for _ in range(length))
        else:
            return secrets.token_urlsafe(length)

    async def _check_and_rotate_secrets(self):
        try:
            conn = self.db_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT sc.*, sv.version, sv.created_at as last_rotation
                    FROM secret_configs sc
                    LEFT JOIN secret_versions sv ON sc.name = sv.secret_name AND sv.is_active = TRUE
                    WHERE sc.auto_rotate = TRUE
                """)
                
                configs = cursor.fetchall()
                
                for config in configs:
                    if self._should_rotate_secret(config):
                        await self._rotate_secret(config['name'])
                        
        except Exception as e:
            logger.error(f"Error in rotation check: {e}")
        finally:
            self.db_pool.putconn(conn)

    def _should_rotate_secret(self, config: Dict) -> bool:
        if not config.get('last_rotation'):
            return True
            
        last_rotation = config['last_rotation']
        rotation_interval = timedelta(days=config['rotation_interval_days'])
        
        return datetime.now() - last_rotation >= rotation_interval

    async def _rotate_secret(self, secret_name: str) -> RotationResult:
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get secret configuration
                cursor.execute(
                    "SELECT * FROM secret_configs WHERE name = %s",
                    (secret_name,)
                )
                config = cursor.fetchone()
                
                if not config:
                    raise HTTPException(status_code=404, message=f"Secret {secret_name} not found")
                
                # Get current version
                cursor.execute("""
                    SELECT version FROM secret_versions 
                    WHERE secret_name = %s AND is_active = TRUE
                    ORDER BY version DESC LIMIT 1
                """, (secret_name,))
                
                current_version_row = cursor.fetchone()
                old_version = current_version_row['version'] if current_version_row else 0
                new_version = old_version + 1
                
                # Generate new secret
                new_secret_value = self._generate_secret_by_type(config['type'])
                encrypted_value = self.cipher_suite.encrypt(new_secret_value.encode()).decode()
                
                # Calculate expiry
                expires_at = datetime.now() + timedelta(days=config['rotation_interval_days'])
                
                # Deactivate old version
                if old_version > 0:
                    cursor.execute("""
                        UPDATE secret_versions 
                        SET is_active = FALSE 
                        WHERE secret_name = %s AND version = %s
                    """, (secret_name, old_version))
                
                # Insert new version
                cursor.execute("""
                    INSERT INTO secret_versions 
                    (secret_name, version, encrypted_value, expires_at, is_active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (secret_name, new_version, encrypted_value, expires_at, True))
                
                # Update external services
                await self._update_external_services(secret_name, new_secret_value, config)
                
                # Record rotation history
                cursor.execute("""
                    INSERT INTO rotation_history 
                    (secret_name, old_version, new_version, status, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (secret_name, old_version, new_version, 'success', 'Automatic rotation'))
                
                conn.commit()
                
                # Clear cache
                if self.redis_client:
                    self.redis_client.delete(f"secret:{secret_name}")
                
                result = RotationResult(
                    secret_name=secret_name,
                    old_version=old_version,
                    new_version=new_version,
                    status='success',
                    message='Secret rotated successfully',
                    rotated_at=datetime.now()
                )
                
                logger.info(f"Secret {secret_name} rotated from v{old_version} to v{new_version}")
                return result
                
        except Exception as e:
            conn.rollback()
            
            # Record failed rotation
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO rotation_history 
                        (secret_name, old_version, new_version, status, message)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (secret_name, old_version if 'old_version' in locals() else None, 
                          new_version if 'new_version' in locals() else None, 'failed', str(e)))
                    conn.commit()
            except:
                pass
                
            logger.error(f"Failed to rotate secret {secret_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Rotation failed: {e}")
        finally:
            self.db_pool.putconn(conn)

    async def _update_external_services(self, secret_name: str, new_value: str, config: Dict):
        environments = config.get('environments', ['production'])
        
        for env in environments:
            # Update HashiCorp Vault
            if self.vault_client:
                try:
                    self.vault_client.secrets.kv.v2.create_or_update_secret(
                        path=f"{env}/{secret_name}",
                        secret={'value': new_value}
                    )
                    logger.info(f"Updated {secret_name} in Vault for {env}")
                except Exception as e:
                    logger.error(f"Failed to update Vault for {secret_name}: {e}")
            
            # Update AWS Secrets Manager
            if self.aws_session:
                try:
                    sm_client = self.aws_session.client('secretsmanager')
                    secret_id = f"{env}/{secret_name}"
                    
                    try:
                        sm_client.update_secret(
                            SecretId=secret_id,
                            SecretString=new_value
                        )
                    except sm_client.exceptions.ResourceNotFoundException:
                        sm_client.create_secret(
                            Name=secret_id,
                            SecretString=new_value,
                            Description=f"ActiveLog secret: {secret_name}"
                        )
                    
                    logger.info(f"Updated {secret_name} in AWS Secrets Manager for {env}")
                except Exception as e:
                    logger.error(f"Failed to update AWS Secrets Manager for {secret_name}: {e}")

    async def _check_expiry_notifications(self):
        try:
            conn = self.db_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT sc.name, sc.notification_before_expiry_hours, sv.expires_at
                    FROM secret_configs sc
                    JOIN secret_versions sv ON sc.name = sv.secret_name
                    WHERE sv.is_active = TRUE 
                    AND sv.expires_at IS NOT NULL
                    AND sv.expires_at <= NOW() + INTERVAL '%s hours'
                """, (24,))  # Check for secrets expiring in next 24 hours
                
                expiring_secrets = cursor.fetchall()
                
                for secret in expiring_secrets:
                    await self._send_expiry_notification(secret)
                    
        except Exception as e:
            logger.error(f"Error checking expiry notifications: {e}")
        finally:
            self.db_pool.putconn(conn)

    async def _send_expiry_notification(self, secret_info: Dict):
        # Implementation would send notifications via email, Slack, etc.
        logger.warning(f"Secret {secret_info['name']} expires at {secret_info['expires_at']}")

    async def _cleanup_old_versions(self):
        try:
            conn = self.db_pool.getconn()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT sc.name, sc.backup_versions
                    FROM secret_configs sc
                """)
                
                configs = cursor.fetchall()
                
                for config in configs:
                    cursor.execute("""
                        DELETE FROM secret_versions
                        WHERE secret_name = %s
                        AND is_active = FALSE
                        AND id NOT IN (
                            SELECT id FROM secret_versions
                            WHERE secret_name = %s AND is_active = FALSE
                            ORDER BY version DESC
                            LIMIT %s
                        )
                    """, (config['name'], config['name'], config['backup_versions']))
                
                conn.commit()
                logger.info("Cleaned up old secret versions")
                
        except Exception as e:
            logger.error(f"Error cleaning up old versions: {e}")
        finally:
            self.db_pool.putconn(conn)

    def _setup_routes(self):
        @self.app.post("/api/v1/secrets/config")
        async def create_secret_config(config: SecretConfig):
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO secret_configs 
                        (name, type, rotation_interval_days, auto_rotate, backup_versions, 
                         notification_before_expiry_hours, environments)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO UPDATE SET
                        type = EXCLUDED.type,
                        rotation_interval_days = EXCLUDED.rotation_interval_days,
                        auto_rotate = EXCLUDED.auto_rotate,
                        backup_versions = EXCLUDED.backup_versions,
                        notification_before_expiry_hours = EXCLUDED.notification_before_expiry_hours,
                        environments = EXCLUDED.environments,
                        updated_at = CURRENT_TIMESTAMP
                    """, (config.name, config.type, config.rotation_interval_days,
                          config.auto_rotate, config.backup_versions,
                          config.notification_before_expiry_hours,
                          json.dumps(config.environments)))
                    conn.commit()
                    
                return {"message": f"Secret configuration for {config.name} created/updated"}
            finally:
                self.db_pool.putconn(conn)

        @self.app.post("/api/v1/secrets/{secret_name}/rotate")
        async def rotate_secret_endpoint(secret_name: str):
            return await self._rotate_secret(secret_name)

        @self.app.get("/api/v1/secrets/{secret_name}/current")
        async def get_current_secret(secret_name: str):
            # Check cache first
            if self.redis_client:
                cached = self.redis_client.get(f"secret:{secret_name}")
                if cached:
                    return json.loads(cached)
            
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT version, created_at, expires_at, is_active
                        FROM secret_versions
                        WHERE secret_name = %s AND is_active = TRUE
                        ORDER BY version DESC LIMIT 1
                    """, (secret_name,))
                    
                    result = cursor.fetchone()
                    if not result:
                        raise HTTPException(status_code=404, detail="Secret not found")
                    
                    secret_info = {
                        "name": secret_name,
                        "version": result['version'],
                        "created_at": result['created_at'].isoformat(),
                        "expires_at": result['expires_at'].isoformat() if result['expires_at'] else None,
                        "is_active": result['is_active']
                    }
                    
                    # Cache for 5 minutes
                    if self.redis_client:
                        self.redis_client.setex(f"secret:{secret_name}", 300, json.dumps(secret_info))
                    
                    return secret_info
            finally:
                self.db_pool.putconn(conn)

        @self.app.get("/api/v1/secrets/status")
        async def get_rotation_status():
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT 
                            COUNT(*) as total_secrets,
                            COUNT(CASE WHEN sv.expires_at <= NOW() + INTERVAL '7 days' THEN 1 END) as expiring_soon,
                            COUNT(CASE WHEN sv.expires_at <= NOW() THEN 1 END) as expired
                        FROM secret_configs sc
                        LEFT JOIN secret_versions sv ON sc.name = sv.secret_name AND sv.is_active = TRUE
                    """)
                    
                    stats = cursor.fetchone()
                    
                    cursor.execute("""
                        SELECT secret_name, status, rotated_at
                        FROM rotation_history
                        WHERE rotated_at >= NOW() - INTERVAL '24 hours'
                        ORDER BY rotated_at DESC
                        LIMIT 10
                    """)
                    
                    recent_rotations = cursor.fetchall()
                    
                    return {
                        "stats": dict(stats),
                        "recent_rotations": [dict(r) for r in recent_rotations],
                        "scheduler_running": self.scheduler.running
                    }
            finally:
                self.db_pool.putconn(conn)

        @self.app.post("/api/v1/secrets/emergency-rotation")
        async def emergency_rotation_all():
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("SELECT name FROM secret_configs WHERE auto_rotate = TRUE")
                    secrets = cursor.fetchall()
                    
                    results = []
                    for secret in secrets:
                        try:
                            result = await self._rotate_secret(secret['name'])
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Emergency rotation failed for {secret['name']}: {e}")
                            results.append({
                                "secret_name": secret['name'],
                                "status": "failed",
                                "message": str(e)
                            })
                    
                    return {"rotated_secrets": results}
            finally:
                self.db_pool.putconn(conn)

    async def start_service(self):
        self.scheduler.start()
        logger.info("Secrets rotation service started")

    async def stop_service(self):
        self.scheduler.shutdown()
        if self.db_pool:
            self.db_pool.closeall()
        logger.info("Secrets rotation service stopped")

# Service instance
rotation_service = SecretsRotationService()

@rotation_service.app.on_event("startup")
async def startup_event():
    await rotation_service.start_service()

@rotation_service.app.on_event("shutdown")
async def shutdown_event():
    await rotation_service.stop_service()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rotation-service:rotation_service.app",
        host="0.0.0.0",
        port=8087,
        reload=False
    )