#!/usr/bin/env python3

import asyncio
import base64
import io
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import qrcode
import pyotp
import bcrypt
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, EmailStr
import psycopg2
from psycopg2.extras import RealDictCursor
import redis
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import jwt

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class User(BaseModel):
    user_id: str
    email: EmailStr
    phone: Optional[str] = None
    two_factor_enabled: bool = False
    two_factor_methods: List[str] = []
    backup_codes_remaining: int = 0

class TwoFactorSetupRequest(BaseModel):
    method: str = Field(..., regex="^(totp|sms|email|backup_codes)$")
    phone: Optional[str] = None

class TwoFactorVerifyRequest(BaseModel):
    method: str = Field(..., regex="^(totp|sms|email|backup_code)$")
    code: str = Field(..., min_length=6, max_length=8)
    trust_device: bool = False

class TwoFactorDisableRequest(BaseModel):
    password: str
    verification_code: str
    method: str = Field(..., regex="^(totp|sms|email)$")

class BackupCodesResponse(BaseModel):
    backup_codes: List[str]
    codes_remaining: int

class TwoFactorAuth:
    def __init__(self):
        self.app = FastAPI(title="ActiveLog Two-Factor Authentication", version="1.0.0")
        self.db_pool = None
        self.redis_client = None
        self.security = HTTPBearer()
        
        # Configuration
        self.jwt_secret = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")
        self.totp_issuer = os.getenv("TOTP_ISSUER", "ActiveLog")
        self.smtp_host = os.getenv("SMTP_HOST", "localhost")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", "noreply@activelog.com")
        
        # SMS configuration (using Twilio as example)
        self.twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_phone_number = os.getenv("TWILIO_PHONE_NUMBER")
        
        self._setup_database()
        self._setup_redis()
        self._setup_routes()
        self._setup_middleware()

    def _setup_database(self):
        """Set up PostgreSQL connection."""
        try:
            self.db_pool = psycopg2.pool.ThreadedConnectionPool(
                1, 20,
                host=os.getenv("POSTGRES_HOST", "localhost"),
                database=os.getenv("POSTGRES_DB", "activelog_auth"),
                user=os.getenv("POSTGRES_USER", "postgres"),
                password=os.getenv("POSTGRES_PASSWORD", "password"),
                port=int(os.getenv("POSTGRES_PORT", "5432"))
            )
            self._create_tables()
            logger.info("Database connection established")
        except Exception as e:
            logger.error(f"Database setup failed: {e}")

    def _setup_redis(self):
        """Set up Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "5")),
                decode_responses=True
            )
            self.redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Redis setup failed: {e}")

    def _create_tables(self):
        """Create database tables."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) UNIQUE NOT NULL,
                        email VARCHAR(255) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        phone VARCHAR(20),
                        two_factor_enabled BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS two_factor_methods (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
                        method VARCHAR(50) NOT NULL,
                        secret VARCHAR(255),
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS backup_codes (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
                        code_hash VARCHAR(255) NOT NULL,
                        used_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trusted_devices (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255) REFERENCES users(user_id) ON DELETE CASCADE,
                        device_fingerprint VARCHAR(255) NOT NULL,
                        device_name VARCHAR(255),
                        last_used TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS auth_attempts (
                        id SERIAL PRIMARY KEY,
                        user_id VARCHAR(255),
                        ip_address INET,
                        method VARCHAR(50),
                        success BOOLEAN,
                        failure_reason VARCHAR(255),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_two_factor_methods_user_id ON two_factor_methods(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_backup_codes_user_id ON backup_codes(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_trusted_devices_user_id ON trusted_devices(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_attempts_user_id ON auth_attempts(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_auth_attempts_ip ON auth_attempts(ip_address)")
                
                conn.commit()
                logger.info("Database tables created/verified")
        finally:
            self.db_pool.putconn(conn)

    async def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        """Get current user from JWT token."""
        try:
            payload = jwt.decode(credentials.credentials, self.jwt_secret, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user_id
        except jwt.PyJWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

    async def setup_totp(self, user_id: str) -> Tuple[str, str]:
        """Set up TOTP (Time-based One-Time Password) for a user."""
        # Generate secret
        secret = pyotp.random_base32()
        
        # Get user email for QR code
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                # Store the secret (temporarily until verified)
                cursor.execute("""
                    INSERT INTO two_factor_methods (user_id, method, secret, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, method) 
                    DO UPDATE SET secret = EXCLUDED.secret, is_active = FALSE
                """, (user_id, "totp", secret, False))
                
                conn.commit()
                
                # Generate QR code
                totp = pyotp.TOTP(secret)
                provisioning_uri = totp.provisioning_uri(
                    name=user['email'],
                    issuer_name=self.totp_issuer
                )
                
                # Generate QR code image
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(provisioning_uri)
                qr.make(fit=True)
                
                qr_img = qr.make_image(fill_color="black", back_color="white")
                
                # Convert to base64 for API response
                img_buffer = io.BytesIO()
                qr_img.save(img_buffer, format='PNG')
                img_buffer.seek(0)
                qr_code_base64 = base64.b64encode(img_buffer.read()).decode()
                
                return secret, qr_code_base64
                
        finally:
            self.db_pool.putconn(conn)

    async def verify_totp(self, user_id: str, code: str) -> bool:
        """Verify TOTP code."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT secret FROM two_factor_methods 
                    WHERE user_id = %s AND method = %s
                """, (user_id, "totp"))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                totp = pyotp.TOTP(result['secret'])
                return totp.verify(code, valid_window=1)  # Allow 1 window tolerance
                
        finally:
            self.db_pool.putconn(conn)

    async def setup_sms(self, user_id: str, phone: str) -> bool:
        """Set up SMS two-factor authentication."""
        # Generate and send verification code
        code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
        
        # Store code in Redis with 5-minute expiry
        self.redis_client.setex(f"sms_setup:{user_id}", 300, code)
        
        # Send SMS
        success = await self._send_sms(phone, f"Your ActiveLog verification code is: {code}")
        
        if success:
            # Store phone number temporarily
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO two_factor_methods (user_id, method, secret, is_active)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, method) 
                        DO UPDATE SET secret = EXCLUDED.secret, is_active = FALSE
                    """, (user_id, "sms", phone, False))
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)
        
        return success

    async def verify_sms_setup(self, user_id: str, code: str) -> bool:
        """Verify SMS setup code."""
        stored_code = self.redis_client.get(f"sms_setup:{user_id}")
        if stored_code and stored_code == code:
            # Activate SMS method
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE two_factor_methods 
                        SET is_active = TRUE 
                        WHERE user_id = %s AND method = %s
                    """, (user_id, "sms"))
                    
                    cursor.execute("""
                        UPDATE users 
                        SET two_factor_enabled = TRUE 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)
            
            # Clean up setup code
            self.redis_client.delete(f"sms_setup:{user_id}")
            return True
        
        return False

    async def send_sms_code(self, user_id: str) -> bool:
        """Send SMS verification code for login."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT secret FROM two_factor_methods 
                    WHERE user_id = %s AND method = %s AND is_active = TRUE
                """, (user_id, "sms"))
                
                result = cursor.fetchone()
                if not result:
                    return False
                
                phone = result['secret']
                code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
                
                # Store code with 5-minute expiry
                self.redis_client.setex(f"sms_auth:{user_id}", 300, code)
                
                return await self._send_sms(phone, f"Your ActiveLog login code is: {code}")
                
        finally:
            self.db_pool.putconn(conn)

    async def verify_sms_code(self, user_id: str, code: str) -> bool:
        """Verify SMS authentication code."""
        stored_code = self.redis_client.get(f"sms_auth:{user_id}")
        if stored_code and stored_code == code:
            self.redis_client.delete(f"sms_auth:{user_id}")
            return True
        return False

    async def setup_email(self, user_id: str) -> bool:
        """Set up email two-factor authentication."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False
                
                # Generate verification code
                code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
                self.redis_client.setex(f"email_setup:{user_id}", 300, code)
                
                # Send email
                success = await self._send_email(
                    user['email'],
                    "ActiveLog - Enable Email 2FA",
                    f"Your verification code is: {code}\n\nThis code will expire in 5 minutes."
                )
                
                if success:
                    cursor.execute("""
                        INSERT INTO two_factor_methods (user_id, method, secret, is_active)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, method) 
                        DO UPDATE SET is_active = FALSE
                    """, (user_id, "email", user['email'], False))
                    conn.commit()
                
                return success
                
        finally:
            self.db_pool.putconn(conn)

    async def verify_email_setup(self, user_id: str, code: str) -> bool:
        """Verify email setup code."""
        stored_code = self.redis_client.get(f"email_setup:{user_id}")
        if stored_code and stored_code == code:
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE two_factor_methods 
                        SET is_active = TRUE 
                        WHERE user_id = %s AND method = %s
                    """, (user_id, "email"))
                    
                    cursor.execute("""
                        UPDATE users 
                        SET two_factor_enabled = TRUE 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    conn.commit()
            finally:
                self.db_pool.putconn(conn)
            
            self.redis_client.delete(f"email_setup:{user_id}")
            return True
        
        return False

    async def send_email_code(self, user_id: str) -> bool:
        """Send email verification code for login."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
                user = cursor.fetchone()
                if not user:
                    return False
                
                code = str(secrets.randbelow(900000) + 100000)  # 6-digit code
                self.redis_client.setex(f"email_auth:{user_id}", 300, code)
                
                return await self._send_email(
                    user['email'],
                    "ActiveLog - Login Verification Code",
                    f"Your login verification code is: {code}\n\nThis code will expire in 5 minutes."
                )
                
        finally:
            self.db_pool.putconn(conn)

    async def verify_email_code(self, user_id: str, code: str) -> bool:
        """Verify email authentication code."""
        stored_code = self.redis_client.get(f"email_auth:{user_id}")
        if stored_code and stored_code == code:
            self.redis_client.delete(f"email_auth:{user_id}")
            return True
        return False

    async def generate_backup_codes(self, user_id: str) -> List[str]:
        """Generate backup codes for the user."""
        backup_codes = []
        conn = self.db_pool.getconn()
        
        try:
            with conn.cursor() as cursor:
                # Delete existing backup codes
                cursor.execute("DELETE FROM backup_codes WHERE user_id = %s", (user_id,))
                
                # Generate 10 backup codes
                for _ in range(10):
                    code = f"{secrets.randbelow(90000000) + 10000000:08d}"  # 8-digit code
                    code_hash = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
                    
                    cursor.execute("""
                        INSERT INTO backup_codes (user_id, code_hash)
                        VALUES (%s, %s)
                    """, (user_id, code_hash))
                    
                    backup_codes.append(code)
                
                # Ensure backup codes method is active
                cursor.execute("""
                    INSERT INTO two_factor_methods (user_id, method, secret, is_active)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, method) 
                    DO UPDATE SET is_active = TRUE
                """, (user_id, "backup_codes", "", True))
                
                conn.commit()
                
        finally:
            self.db_pool.putconn(conn)
        
        return backup_codes

    async def verify_backup_code(self, user_id: str, code: str) -> bool:
        """Verify and consume a backup code."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, code_hash FROM backup_codes 
                    WHERE user_id = %s AND used_at IS NULL
                """, (user_id,))
                
                codes = cursor.fetchall()
                
                for backup_code in codes:
                    if bcrypt.checkpw(code.encode(), backup_code['code_hash'].encode()):
                        # Mark code as used
                        cursor.execute("""
                            UPDATE backup_codes 
                            SET used_at = CURRENT_TIMESTAMP 
                            WHERE id = %s
                        """, (backup_code['id'],))
                        
                        conn.commit()
                        return True
                
                return False
                
        finally:
            self.db_pool.putconn(conn)

    async def add_trusted_device(self, user_id: str, device_fingerprint: str, device_name: str = None):
        """Add a trusted device for the user."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor() as cursor:
                expires_at = datetime.utcnow() + timedelta(days=30)  # Trust for 30 days
                
                cursor.execute("""
                    INSERT INTO trusted_devices (user_id, device_fingerprint, device_name, expires_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, device_fingerprint) 
                    DO UPDATE SET last_used = CURRENT_TIMESTAMP, expires_at = EXCLUDED.expires_at
                """, (user_id, device_fingerprint, device_name, expires_at))
                
                conn.commit()
                
        finally:
            self.db_pool.putconn(conn)

    async def is_trusted_device(self, user_id: str, device_fingerprint: str) -> bool:
        """Check if device is trusted and not expired."""
        conn = self.db_pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id FROM trusted_devices 
                    WHERE user_id = %s AND device_fingerprint = %s 
                    AND expires_at > CURRENT_TIMESTAMP
                """, (user_id, device_fingerprint))
                
                return cursor.fetchone() is not None
                
        finally:
            self.db_pool.putconn(conn)

    async def _send_sms(self, phone: str, message: str) -> bool:
        """Send SMS using Twilio (example implementation)."""
        if not all([self.twilio_account_sid, self.twilio_auth_token, self.twilio_phone_number]):
            logger.warning("Twilio not configured, SMS not sent")
            return False
        
        try:
            from twilio.rest import Client
            
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            message = client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=phone
            )
            
            logger.info(f"SMS sent successfully: {message.sid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            return False

    async def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _setup_middleware(self):
        """Set up middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8088"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routes(self):
        """Set up API routes."""
        
        @self.app.post("/api/v1/2fa/setup")
        async def setup_two_factor(
            request: TwoFactorSetupRequest,
            user_id: str = Depends(self.get_current_user)
        ):
            """Set up two-factor authentication method."""
            
            if request.method == "totp":
                secret, qr_code = await self.setup_totp(user_id)
                return {
                    "method": "totp",
                    "secret": secret,
                    "qr_code": f"data:image/png;base64,{qr_code}",
                    "message": "Scan the QR code with your authenticator app and verify with a code"
                }
            
            elif request.method == "sms":
                if not request.phone:
                    raise HTTPException(status_code=400, detail="Phone number required for SMS")
                
                success = await self.setup_sms(user_id, request.phone)
                if success:
                    return {
                        "method": "sms",
                        "message": f"Verification code sent to {request.phone}. Enter the code to complete setup."
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to send SMS")
            
            elif request.method == "email":
                success = await self.setup_email(user_id)
                if success:
                    return {
                        "method": "email",
                        "message": "Verification code sent to your email. Enter the code to complete setup."
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to send email")
            
            elif request.method == "backup_codes":
                backup_codes = await self.generate_backup_codes(user_id)
                return BackupCodesResponse(
                    backup_codes=backup_codes,
                    codes_remaining=len(backup_codes)
                )

        @self.app.post("/api/v1/2fa/verify-setup")
        async def verify_two_factor_setup(
            request: TwoFactorVerifyRequest,
            user_id: str = Depends(self.get_current_user)
        ):
            """Verify two-factor authentication setup."""
            
            success = False
            
            if request.method == "totp":
                success = await self.verify_totp(user_id, request.code)
                if success:
                    # Activate TOTP method
                    conn = self.db_pool.getconn()
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute("""
                                UPDATE two_factor_methods 
                                SET is_active = TRUE 
                                WHERE user_id = %s AND method = %s
                            """, (user_id, "totp"))
                            
                            cursor.execute("""
                                UPDATE users 
                                SET two_factor_enabled = TRUE 
                                WHERE user_id = %s
                            """, (user_id,))
                            
                            conn.commit()
                    finally:
                        self.db_pool.putconn(conn)
            
            elif request.method == "sms":
                success = await self.verify_sms_setup(user_id, request.code)
            
            elif request.method == "email":
                success = await self.verify_email_setup(user_id, request.code)
            
            if success:
                return {"message": f"{request.method.upper()} two-factor authentication enabled successfully"}
            else:
                raise HTTPException(status_code=400, detail="Invalid verification code")

        @self.app.post("/api/v1/2fa/authenticate")
        async def authenticate_two_factor(
            request: TwoFactorVerifyRequest,
            user_id: str = Depends(self.get_current_user)
        ):
            """Authenticate using two-factor method."""
            
            success = False
            
            if request.method == "totp":
                success = await self.verify_totp(user_id, request.code)
            elif request.method == "sms":
                success = await self.verify_sms_code(user_id, request.code)
            elif request.method == "email":
                success = await self.verify_email_code(user_id, request.code)
            elif request.method == "backup_code":
                success = await self.verify_backup_code(user_id, request.code)
            
            if success:
                # Generate authentication token
                token_payload = {
                    "user_id": user_id,
                    "two_factor_verified": True,
                    "exp": datetime.utcnow() + timedelta(hours=24)
                }
                
                token = jwt.encode(token_payload, self.jwt_secret, algorithm="HS256")
                
                # Add trusted device if requested
                if request.trust_device:
                    # In a real implementation, you'd get device fingerprint from request headers
                    device_fingerprint = "example_device_fingerprint"
                    await self.add_trusted_device(user_id, device_fingerprint)
                
                return {
                    "token": token,
                    "message": "Two-factor authentication successful"
                }
            else:
                raise HTTPException(status_code=401, detail="Invalid verification code")

        @self.app.get("/api/v1/2fa/status")
        async def get_two_factor_status(
            user_id: str = Depends(self.get_current_user)
        ):
            """Get user's two-factor authentication status."""
            
            conn = self.db_pool.getconn()
            try:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT u.two_factor_enabled,
                               COALESCE(array_agg(tfm.method) FILTER (WHERE tfm.is_active), '{}') as enabled_methods,
                               COUNT(bc.id) FILTER (WHERE bc.used_at IS NULL) as backup_codes_remaining
                        FROM users u
                        LEFT JOIN two_factor_methods tfm ON u.user_id = tfm.user_id
                        LEFT JOIN backup_codes bc ON u.user_id = bc.user_id
                        WHERE u.user_id = %s
                        GROUP BY u.user_id, u.two_factor_enabled
                    """, (user_id,))
                    
                    result = cursor.fetchone()
                    
                    if result:
                        return {
                            "two_factor_enabled": result['two_factor_enabled'],
                            "enabled_methods": result['enabled_methods'],
                            "backup_codes_remaining": result['backup_codes_remaining'] or 0
                        }
                    else:
                        return {
                            "two_factor_enabled": False,
                            "enabled_methods": [],
                            "backup_codes_remaining": 0
                        }
                        
            finally:
                self.db_pool.putconn(conn)

        @self.app.post("/api/v1/2fa/send-code")
        async def send_verification_code(
            method: str,
            user_id: str = Depends(self.get_current_user)
        ):
            """Send verification code for authentication."""
            
            if method == "sms":
                success = await self.send_sms_code(user_id)
            elif method == "email":
                success = await self.send_email_code(user_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid method")
            
            if success:
                return {"message": f"Verification code sent via {method}"}
            else:
                raise HTTPException(status_code=500, detail=f"Failed to send code via {method}")

        @self.app.delete("/api/v1/2fa/disable")
        async def disable_two_factor(
            request: TwoFactorDisableRequest,
            user_id: str = Depends(self.get_current_user)
        ):
            """Disable two-factor authentication."""
            
            # Verify current 2FA before disabling
            success = False
            if request.method == "totp":
                success = await self.verify_totp(user_id, request.verification_code)
            elif request.method == "sms":
                success = await self.verify_sms_code(user_id, request.verification_code)
            elif request.method == "email":
                success = await self.verify_email_code(user_id, request.verification_code)
            
            if not success:
                raise HTTPException(status_code=401, detail="Invalid verification code")
            
            # TODO: Also verify password
            
            # Disable all 2FA methods
            conn = self.db_pool.getconn()
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE users 
                        SET two_factor_enabled = FALSE 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    cursor.execute("""
                        UPDATE two_factor_methods 
                        SET is_active = FALSE 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    cursor.execute("""
                        DELETE FROM backup_codes 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    cursor.execute("""
                        DELETE FROM trusted_devices 
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    conn.commit()
                    
            finally:
                self.db_pool.putconn(conn)
            
            return {"message": "Two-factor authentication disabled successfully"}

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": "healthy" if self.db_pool else "unhealthy",
                    "redis": "healthy" if self.redis_client else "unhealthy"
                }
            }

# Service instance
two_factor_auth = TwoFactorAuth()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "two-factor-auth:two_factor_auth.app",
        host="0.0.0.0",
        port=8091,
        reload=False
    )