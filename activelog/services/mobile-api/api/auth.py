"""
Mobile Authentication API
Optimized for mobile devices with battery-efficient auth flows
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio
import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import jwt

from ..core.config import settings
from ..core.database import get_database
from ..services.auth_service import AuthService, TokenService, DeviceService
from ..services.security_service import SecurityService
from ..middleware.rate_limiting import rate_limit
from ..middleware.mobile_optimization import get_device_info, get_connection_info
from ..protobuf.generated.mobile_pb import (
    AuthRequest, AuthResponse, DeviceInfo, UserProfile, 
    ServerCapabilities, StorageQuota, UserSettings
)

router = APIRouter()
security = HTTPBearer(auto_error=False)

# Pydantic models for JSON API
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str
    device_name: Optional[str] = None
    platform: str = "mobile"
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    totp_code: Optional[str] = None
    remember_device: bool = True
    biometric_enabled: bool = False

class RefreshTokenRequest(BaseModel):
    refresh_token: str
    device_id: str

class BiometricAuthRequest(BaseModel):
    device_id: str
    biometric_signature: str
    challenge: str

class DeviceRegistrationRequest(BaseModel):
    device_id: str
    device_name: str
    platform: str
    os_version: str
    app_version: str
    push_token: Optional[str] = None
    biometric_public_key: Optional[str] = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    totp_code: Optional[str] = None

    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

# Dependency injection
async def get_auth_service(request: Request) -> AuthService:
    return AuthService(request.app.state.database)

async def get_token_service(request: Request) -> TokenService:
    return TokenService(request.app.state.database)

async def get_device_service(request: Request) -> DeviceService:
    return DeviceService(request.app.state.database)

async def get_security_service(request: Request) -> SecurityService:
    return SecurityService(request.app.state.database)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current authenticated user with mobile-optimized validation"""
    if not credentials:
        raise HTTPException(
            status_code=401, 
            detail={
                "error": "unauthorized",
                "message": "Authentication required",
                "battery_impact": "minimal"
            }
        )
    
    try:
        # Validate token with mobile-specific optimizations
        user_data = await auth_service.validate_token(
            credentials.credentials,
            check_device=True,
            battery_efficient=True
        )
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "invalid_token",
                "message": "Invalid or expired token",
                "battery_impact": "minimal"
            }
        )

# Authentication endpoints
@router.post("/login", response_model=Dict[str, Any])
@rate_limit("auth_login", per_minute=10, per_hour=50)
async def login(
    request: LoginRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
    device_service: DeviceService = Depends(get_device_service),
    security_service: SecurityService = Depends(get_security_service)
):
    """
    Mobile-optimized login endpoint
    Features:
    - Battery-efficient authentication
    - Device fingerprinting
    - Adaptive security based on device trust
    - Connection-aware token expiry
    """
    
    device_info = get_device_info(http_request)
    connection_info = get_connection_info(http_request)
    
    try:
        # Security checks
        client_ip = http_request.client.host
        await security_service.check_rate_limits(client_ip, "login")
        await security_service.check_suspicious_activity(client_ip, request.device_id)
        
        # Authenticate user
        user = await auth_service.authenticate_user(
            email=request.email,
            password=request.password,
            totp_code=request.totp_code
        )
        
        if not user:
            # Add delay to prevent timing attacks
            await asyncio.sleep(1)
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_credentials",
                    "message": "Invalid email or password",
                    "battery_impact": "minimal"
                }
            )
        
        # Register or update device
        device = await device_service.register_device(
            user_id=user["id"],
            device_id=request.device_id,
            device_name=request.device_name or device_info.get("model", "Unknown"),
            platform=request.platform,
            os_version=request.os_version or device_info.get("os_version"),
            app_version=request.app_version,
            push_token=None,  # Will be set separately
            trusted=await device_service.is_device_trusted(request.device_id, user["id"])
        )
        
        # Generate tokens with mobile optimization
        token_expiry = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 2  # Longer for mobile
            if connection_info.get("type") == "wifi" 
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        access_token = await auth_service.create_access_token(
            user_id=user["id"],
            device_id=request.device_id,
            expires_delta=token_expiry,
            scopes=["mobile", "offline"]
        )
        
        refresh_token = await auth_service.create_refresh_token(
            user_id=user["id"],
            device_id=request.device_id,
            expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        ) if request.remember_device else None
        
        # Background tasks
        background_tasks.add_task(
            security_service.log_successful_login,
            user["id"], request.device_id, client_ip
        )
        
        background_tasks.add_task(
            device_service.update_device_last_seen,
            request.device_id, datetime.utcnow()
        )
        
        # Prepare response with mobile optimizations
        response_data = {
            "success": True,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_in": int(token_expiry.total_seconds()),
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name", ""),
                "avatar_url": user.get("avatar_url"),
                "settings": await auth_service.get_user_mobile_settings(user["id"])
            },
            "device": {
                "id": device["id"],
                "trusted": device["trusted"],
                "requires_verification": not device["trusted"]
            },
            "server_capabilities": {
                "protobuf_enabled": True,
                "offline_sync": True,
                "push_notifications": True,
                "max_file_size": settings.MAX_UPLOAD_SIZE,
                "supported_formats": settings.ALLOWED_FILE_TYPES,
                "compression_types": ["gzip", "brotli", "lz4"]
            },
            "battery_hints": {
                "sync_interval_seconds": 300 if connection_info.get("type") == "wifi" else 600,
                "background_sync_enabled": connection_info.get("type") == "wifi",
                "adaptive_quality": True
            }
        }
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error and return generic response
        await security_service.log_failed_login(
            request.email, request.device_id, client_ip, str(e)
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "authentication_error",
                "message": "Authentication failed",
                "battery_impact": "minimal",
                "retry_after": 30
            }
        )

@router.post("/refresh", response_model=Dict[str, Any])
@rate_limit("auth_refresh", per_minute=20, per_hour=100)
async def refresh_token(
    request: RefreshTokenRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    auth_service: AuthService = Depends(get_auth_service),
    token_service: TokenService = Depends(get_token_service)
):
    """
    Refresh access token using refresh token
    Optimized for battery efficiency with minimal validation
    """
    
    try:
        # Validate refresh token
        token_data = await token_service.validate_refresh_token(
            request.refresh_token,
            request.device_id
        )
        
        if not token_data:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "invalid_refresh_token",
                    "message": "Invalid or expired refresh token",
                    "battery_impact": "minimal"
                }
            )
        
        user_id = token_data["user_id"]
        
        # Generate new access token
        connection_info = get_connection_info(http_request)
        token_expiry = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 2
            if connection_info.get("type") == "wifi"
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        new_access_token = await auth_service.create_access_token(
            user_id=user_id,
            device_id=request.device_id,
            expires_delta=token_expiry,
            scopes=["mobile", "offline"]
        )
        
        # Optionally rotate refresh token for security
        new_refresh_token = None
        if token_data.get("should_rotate"):
            new_refresh_token = await auth_service.create_refresh_token(
                user_id=user_id,
                device_id=request.device_id,
                expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
            )
            
            # Invalidate old refresh token
            background_tasks.add_task(
                token_service.invalidate_refresh_token,
                request.refresh_token
            )
        
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token or request.refresh_token,
            "expires_in": int(token_expiry.total_seconds()),
            "battery_impact": "minimal"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "token_refresh_error",
                "message": "Failed to refresh token",
                "battery_impact": "minimal",
                "retry_after": 60
            }
        )

@router.post("/biometric/setup")
@rate_limit("biometric_setup", per_minute=5, per_hour=10)
async def setup_biometric_auth(
    request: DeviceRegistrationRequest,
    current_user: dict = Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Setup biometric authentication for device"""
    
    try:
        # Validate device ownership
        device = await device_service.get_device(request.device_id, current_user["id"])
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Store biometric public key
        await device_service.setup_biometric_auth(
            device_id=request.device_id,
            user_id=current_user["id"],
            public_key=request.biometric_public_key
        )
        
        return {
            "success": True,
            "message": "Biometric authentication enabled",
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "biometric_setup_error",
                "message": "Failed to setup biometric authentication",
                "battery_impact": "minimal"
            }
        )

@router.post("/biometric/authenticate")
@rate_limit("biometric_auth", per_minute=10, per_hour=50)
async def biometric_authenticate(
    request: BiometricAuthRequest,
    http_request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    device_service: DeviceService = Depends(get_device_service)
):
    """Authenticate using biometric signature"""
    
    try:
        # Validate biometric signature
        user = await device_service.authenticate_biometric(
            device_id=request.device_id,
            signature=request.biometric_signature,
            challenge=request.challenge
        )
        
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "biometric_auth_failed",
                    "message": "Biometric authentication failed",
                    "battery_impact": "minimal"
                }
            )
        
        # Generate access token
        connection_info = get_connection_info(http_request)
        token_expiry = timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 2
            if connection_info.get("type") == "wifi"
            else settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        
        access_token = await auth_service.create_access_token(
            user_id=user["id"],
            device_id=request.device_id,
            expires_delta=token_expiry,
            scopes=["mobile", "offline", "biometric"]
        )
        
        return {
            "success": True,
            "access_token": access_token,
            "expires_in": int(token_expiry.total_seconds()),
            "user": {
                "id": user["id"],
                "email": user["email"],
                "name": user.get("name", "")
            },
            "battery_impact": "minimal"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "biometric_auth_error",
                "message": "Biometric authentication error",
                "battery_impact": "minimal"
            }
        )

@router.post("/logout")
async def logout(
    http_request: Request,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    token_service: TokenService = Depends(get_token_service)
):
    """Logout and invalidate tokens"""
    
    try:
        # Get device ID from token
        auth_header = http_request.headers.get("authorization")
        if auth_header:
            token = auth_header.replace("Bearer ", "")
            device_id = await token_service.get_device_id_from_token(token)
            
            # Invalidate all tokens for this device
            background_tasks.add_task(
                token_service.invalidate_device_tokens,
                current_user["id"],
                device_id
            )
        
        return {
            "success": True,
            "message": "Logged out successfully",
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        return {
            "success": True,  # Always return success for logout
            "message": "Logged out",
            "battery_impact": "minimal"
        }

@router.get("/me")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current user profile with mobile-optimized data"""
    
    try:
        # Get user profile with mobile-specific settings
        profile = await auth_service.get_mobile_user_profile(current_user["id"])
        
        return {
            "success": True,
            "user": profile,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "profile_error",
                "message": "Failed to load profile",
                "battery_impact": "minimal"
            }
        )

@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change user password with mobile-friendly flow"""
    
    try:
        success = await auth_service.change_password(
            user_id=current_user["id"],
            current_password=request.current_password,
            new_password=request.new_password,
            totp_code=request.totp_code
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "password_change_failed",
                    "message": "Failed to change password",
                    "battery_impact": "minimal"
                }
            )
        
        return {
            "success": True,
            "message": "Password changed successfully",
            "battery_impact": "minimal"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "password_change_error",
                "message": "Password change error",
                "battery_impact": "minimal"
            }
        )

@router.get("/devices")
async def get_user_devices(
    current_user: dict = Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service)
):
    """Get list of user's registered devices"""
    
    try:
        devices = await device_service.get_user_devices(current_user["id"])
        
        return {
            "success": True,
            "devices": devices,
            "battery_impact": "minimal"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "devices_error",
                "message": "Failed to load devices",
                "battery_impact": "minimal"
            }
        )

@router.delete("/devices/{device_id}")
async def revoke_device(
    device_id: str,
    current_user: dict = Depends(get_current_user),
    device_service: DeviceService = Depends(get_device_service),
    token_service: TokenService = Depends(get_token_service)
):
    """Revoke access for a specific device"""
    
    try:
        # Verify device ownership
        device = await device_service.get_device(device_id, current_user["id"])
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Revoke device and invalidate tokens
        await device_service.revoke_device(device_id, current_user["id"])
        await token_service.invalidate_device_tokens(current_user["id"], device_id)
        
        return {
            "success": True,
            "message": "Device access revoked",
            "battery_impact": "minimal"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "device_revoke_error",
                "message": "Failed to revoke device",
                "battery_impact": "minimal"
            }
        )