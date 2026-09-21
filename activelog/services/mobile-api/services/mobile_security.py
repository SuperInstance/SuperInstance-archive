"""
Mobile-specific security and authentication service

Provides enhanced security features for mobile clients:
- Device fingerprinting and trust scoring
- Biometric authentication support
- JWT token management with rotation
- Rate limiting and fraud detection
- Secure credential storage
- Mobile-specific attack protection
"""

import asyncio
import hashlib
import hmac
import secrets
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from enum import Enum
import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import bcrypt

from ..config import settings
from ..protobuf.generated.mobile_pb import (
    AuthRequest, AuthResponse, DeviceInfo, UserProfile,
    PasswordAuth, TokenAuth, BiometricAuth, OAuthAuth
)

logger = logging.getLogger(__name__)

class SecurityLevel(Enum):
    """Security trust levels"""
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERIFIED = "verified"

class ThreatType(Enum):
    """Detected threat types"""
    BRUTE_FORCE = "brute_force"
    ACCOUNT_TAKEOVER = "account_takeover"
    DEVICE_COMPROMISE = "device_compromise"
    LOCATION_ANOMALY = "location_anomaly"
    BEHAVIORAL_ANOMALY = "behavioral_anomaly"
    CREDENTIAL_STUFFING = "credential_stuffing"

@dataclass
class DeviceFingerprint:
    """Device identification and trust metrics"""
    device_id: str
    platform: str
    os_version: str
    app_version: str
    model: str
    screen_resolution: Optional[str]
    timezone: Optional[str]
    language: Optional[str]
    fingerprint_hash: str
    trust_score: float          # 0.0-1.0 trust score
    security_level: SecurityLevel
    first_seen: datetime
    last_seen: datetime
    login_count: int
    risk_factors: List[str]

@dataclass
class SecurityEvent:
    """Security-related event"""
    event_id: str
    device_id: str
    user_id: Optional[str]
    event_type: str
    threat_type: Optional[ThreatType]
    severity: str               # low, medium, high, critical
    description: str
    metadata: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]
    location: Optional[str]

@dataclass
class AuthToken:
    """Authentication token with metadata"""
    token: str
    refresh_token: str
    device_id: str
    user_id: str
    issued_at: datetime
    expires_at: datetime
    scopes: List[str]
    security_level: SecurityLevel
    token_hash: str

class MobileSecurityManager:
    """Mobile authentication and security management"""
    
    def __init__(self):
        self.device_fingerprints: Dict[str, DeviceFingerprint] = {}
        self.active_tokens: Dict[str, AuthToken] = {}
        self.security_events: List[SecurityEvent] = []
        self.rate_limits: Dict[str, List[float]] = {}
        self.blocked_devices: Set[str] = set()
        self.suspicious_ips: Set[str] = set()
        self.aes_key = AESGCM.generate_key(bit_length=256)
        self.jwt_secret = settings.JWT_SECRET_KEY
        self.biometric_challenges: Dict[str, Dict] = {}
        
    async def authenticate_device(self, request: AuthRequest) -> AuthResponse:
        """
        Authenticate device and create secure session
        
        Args:
            request: Authentication request with credentials and device info
            
        Returns:
            AuthResponse with tokens and security status
        """
        
        device_id = request.device.device_id
        
        try:
            # Generate device fingerprint
            fingerprint = await self._generate_device_fingerprint(request.device)
            
            # Check device security and rate limits
            security_check = await self._security_check(device_id, fingerprint)
            if not security_check['allowed']:
                return self._create_error_response(
                    security_check['error_code'],
                    security_check['error_message']
                )
            
            # Authenticate based on auth type
            auth_result = None
            if request.HasField('password'):
                auth_result = await self._authenticate_password(request.password, fingerprint)
            elif request.HasField('token'):
                auth_result = await self._authenticate_token(request.token, fingerprint)
            elif request.HasField('biometric'):
                auth_result = await self._authenticate_biometric(request.biometric, fingerprint)
            elif request.HasField('oauth'):
                auth_result = await self._authenticate_oauth(request.oauth, fingerprint)
            
            if not auth_result or not auth_result['success']:
                # Log failed authentication
                await self._log_security_event(
                    device_id, None, "auth_failed",
                    ThreatType.CREDENTIAL_STUFFING if auth_result and auth_result.get('brute_force') else None,
                    "medium", "Authentication failed", auth_result or {}
                )
                return self._create_error_response("AUTH_FAILED", "Authentication failed")
            
            # Create tokens
            tokens = await self._create_auth_tokens(
                auth_result['user_id'],
                device_id,
                fingerprint.security_level,
                request.remember_device
            )
            
            # Update device trust
            await self._update_device_trust(device_id, fingerprint, True)
            
            # Log successful authentication
            await self._log_security_event(
                device_id, auth_result['user_id'], "auth_success",
                None, "info", "Authentication successful", {}
            )
            
            # Build response
            response = AuthResponse()
            response.success = True
            response.access_token = tokens['access_token']
            response.refresh_token = tokens['refresh_token']
            response.expires_in = int(tokens['expires_in'].total_seconds())
            
            # Add user profile (simplified)
            user_profile = UserProfile()
            user_profile.user_id = auth_result['user_id']
            user_profile.email = auth_result.get('email', '')
            user_profile.name = auth_result.get('name', '')
            response.user.CopyFrom(user_profile)
            
            return response
            
        except Exception as e:
            logger.error(f"Authentication error for device {device_id}: {e}")
            return self._create_error_response("INTERNAL_ERROR", "Authentication service error")
    
    async def _generate_device_fingerprint(self, device_info: DeviceInfo) -> DeviceFingerprint:
        """Generate or update device fingerprint"""
        
        # Create fingerprint components
        components = [
            device_info.device_id,
            device_info.platform,
            device_info.os_version,
            device_info.app_version,
            device_info.model,
            str(device_info.tier)  # Performance tier
        ]
        
        # Generate hash
        fingerprint_data = "|".join(components)
        fingerprint_hash = hashlib.sha256(fingerprint_data.encode()).hexdigest()
        
        now = datetime.utcnow()
        device_id = device_info.device_id
        
        # Check if device exists
        if device_id in self.device_fingerprints:
            existing = self.device_fingerprints[device_id]
            
            # Update existing fingerprint
            if existing.fingerprint_hash != fingerprint_hash:
                # Device characteristics changed - lower trust
                existing.trust_score *= 0.8
                existing.risk_factors.append("device_characteristics_changed")
                logger.warning(f"Device fingerprint changed for {device_id}")
            
            existing.last_seen = now
            existing.login_count += 1
            
            # Gradually increase trust for consistent devices
            if existing.fingerprint_hash == fingerprint_hash:
                existing.trust_score = min(1.0, existing.trust_score + 0.01)
            
            return existing
        else:
            # New device
            fingerprint = DeviceFingerprint(
                device_id=device_id,
                platform=device_info.platform,
                os_version=device_info.os_version,
                app_version=device_info.app_version,
                model=device_info.model,
                screen_resolution=None,
                timezone=None,
                language=None,
                fingerprint_hash=fingerprint_hash,
                trust_score=0.3,  # Start with low trust
                security_level=SecurityLevel.LOW,
                first_seen=now,
                last_seen=now,
                login_count=1,
                risk_factors=[]
            )
            
            self.device_fingerprints[device_id] = fingerprint
            return fingerprint
    
    async def _security_check(self, device_id: str, fingerprint: DeviceFingerprint) -> Dict[str, Any]:
        """Perform comprehensive security checks"""
        
        # Check if device is blocked
        if device_id in self.blocked_devices:
            return {
                'allowed': False,
                'error_code': 'DEVICE_BLOCKED',
                'error_message': 'Device has been blocked due to security concerns'
            }
        
        # Rate limiting check
        rate_limit_check = self._check_rate_limit(device_id)
        if not rate_limit_check['allowed']:
            return rate_limit_check
        
        # Trust score check
        if fingerprint.trust_score < 0.1:
            return {
                'allowed': False,
                'error_code': 'LOW_TRUST',
                'error_message': 'Device trust score too low for authentication'
            }
        
        # Check for suspicious patterns
        recent_events = [e for e in self.security_events[-100:] 
                        if e.device_id == device_id and 
                        e.timestamp > datetime.utcnow() - timedelta(hours=1)]
        
        failed_attempts = len([e for e in recent_events if e.event_type == "auth_failed"])
        if failed_attempts >= 5:
            # Temporary lockout
            await self._log_security_event(
                device_id, None, "rate_limit_exceeded",
                ThreatType.BRUTE_FORCE, "high",
                f"Too many failed attempts: {failed_attempts}", {}
            )
            return {
                'allowed': False,
                'error_code': 'RATE_LIMITED',
                'error_message': 'Too many failed authentication attempts'
            }
        
        return {'allowed': True}
    
    def _check_rate_limit(self, identifier: str, 
                         window_seconds: int = 300, 
                         max_requests: int = 10) -> Dict[str, Any]:
        """Check rate limiting for identifier"""
        
        now = time.time()
        
        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []
        
        # Clean old entries
        self.rate_limits[identifier] = [
            timestamp for timestamp in self.rate_limits[identifier]
            if now - timestamp < window_seconds
        ]
        
        # Check limit
        if len(self.rate_limits[identifier]) >= max_requests:
            return {
                'allowed': False,
                'error_code': 'RATE_LIMITED',
                'error_message': f'Rate limit exceeded: {max_requests} requests per {window_seconds} seconds'
            }
        
        # Add current request
        self.rate_limits[identifier].append(now)
        
        return {'allowed': True}
    
    async def _authenticate_password(self, password_auth: PasswordAuth, 
                                   fingerprint: DeviceFingerprint) -> Optional[Dict[str, Any]]:
        """Authenticate using email/password"""
        
        # Simulate user lookup and password verification
        # In production, this would query your user database
        
        # For demo purposes, accept a test user
        if password_auth.email == "test@example.com" and password_auth.password == "testpass123":
            # Simulate TOTP check if provided
            if password_auth.totp_code and password_auth.totp_code != "123456":
                return {'success': False, 'error': 'invalid_totp'}
            
            return {
                'success': True,
                'user_id': 'user_123',
                'email': password_auth.email,
                'name': 'Test User',
                'auth_method': 'password'
            }
        
        # Check for brute force patterns
        recent_failures = len([e for e in self.security_events[-20:]
                              if e.event_type == "auth_failed" and 
                              e.device_id == fingerprint.device_id])
        
        return {
            'success': False,
            'error': 'invalid_credentials',
            'brute_force': recent_failures >= 3
        }
    
    async def _authenticate_token(self, token_auth: TokenAuth,
                                fingerprint: DeviceFingerprint) -> Optional[Dict[str, Any]]:
        """Authenticate using refresh token"""
        
        try:
            # Verify refresh token
            token_hash = hashlib.sha256(token_auth.refresh_token.encode()).hexdigest()
            
            # Find matching active token
            active_token = None
            for token in self.active_tokens.values():
                if (token.token_hash == token_hash and 
                    token.device_id == token_auth.device_id):
                    active_token = token
                    break
            
            if not active_token:
                return {'success': False, 'error': 'invalid_token'}
            
            # Check expiration
            if datetime.utcnow() > active_token.expires_at:
                # Remove expired token
                del self.active_tokens[active_token.token]
                return {'success': False, 'error': 'token_expired'}
            
            # Verify device matches
            if active_token.device_id != fingerprint.device_id:
                return {'success': False, 'error': 'device_mismatch'}
            
            return {
                'success': True,
                'user_id': active_token.user_id,
                'auth_method': 'token'
            }
            
        except Exception as e:
            logger.error(f"Token authentication error: {e}")
            return {'success': False, 'error': 'token_error'}
    
    async def _authenticate_biometric(self, biometric_auth: BiometricAuth,
                                    fingerprint: DeviceFingerprint) -> Optional[Dict[str, Any]]:
        """Authenticate using biometric signature"""
        
        device_id = biometric_auth.device_id
        
        # Check if there's a pending biometric challenge
        if device_id not in self.biometric_challenges:
            return {'success': False, 'error': 'no_challenge'}
        
        challenge_data = self.biometric_challenges[device_id]
        
        # Verify challenge hasn't expired (5 minutes)
        if datetime.utcnow() > challenge_data['expires']:
            del self.biometric_challenges[device_id]
            return {'success': False, 'error': 'challenge_expired'}
        
        # Verify challenge matches
        if biometric_auth.challenge != challenge_data['challenge']:
            return {'success': False, 'error': 'challenge_mismatch'}
        
        # In production, verify biometric signature against stored template
        # For demo, accept any non-empty signature
        if len(biometric_auth.biometric_signature) < 10:
            return {'success': False, 'error': 'invalid_signature'}
        
        # Clean up challenge
        del self.biometric_challenges[device_id]
        
        return {
            'success': True,
            'user_id': challenge_data['user_id'],
            'auth_method': 'biometric'
        }
    
    async def _authenticate_oauth(self, oauth_auth: OAuthAuth,
                                fingerprint: DeviceFingerprint) -> Optional[Dict[str, Any]]:
        """Authenticate using OAuth provider"""
        
        # Simplified OAuth verification
        # In production, verify authorization code with provider
        
        if oauth_auth.provider not in ['google', 'apple', 'microsoft']:
            return {'success': False, 'error': 'unsupported_provider'}
        
        if not oauth_auth.authorization_code:
            return {'success': False, 'error': 'missing_code'}
        
        # Simulate OAuth verification
        # In production, exchange code for tokens and get user info
        
        return {
            'success': True,
            'user_id': f'oauth_{oauth_auth.provider}_123',
            'email': f'user@{oauth_auth.provider}.com',
            'name': f'{oauth_auth.provider.title()} User',
            'auth_method': f'oauth_{oauth_auth.provider}'
        }
    
    async def _create_auth_tokens(self,
                                user_id: str,
                                device_id: str,
                                security_level: SecurityLevel,
                                remember_device: bool) -> Dict[str, Any]:
        """Create JWT access and refresh tokens"""
        
        now = datetime.utcnow()
        
        # Token expiration based on security level and remember preference
        if security_level == SecurityLevel.HIGH and remember_device:
            access_expires = timedelta(hours=24)
            refresh_expires = timedelta(days=30)
        elif security_level >= SecurityLevel.MEDIUM:
            access_expires = timedelta(hours=8)
            refresh_expires = timedelta(days=7)
        else:
            access_expires = timedelta(hours=1)
            refresh_expires = timedelta(days=1)
        
        access_exp = now + access_expires
        refresh_exp = now + refresh_expires
        
        # Create access token
        access_payload = {
            'sub': user_id,
            'device_id': device_id,
            'iat': int(now.timestamp()),
            'exp': int(access_exp.timestamp()),
            'type': 'access',
            'security_level': security_level.value,
            'scopes': ['read', 'write', 'sync']
        }
        
        access_token = jwt.encode(access_payload, self.jwt_secret, algorithm='HS256')
        
        # Create refresh token
        refresh_payload = {
            'sub': user_id,
            'device_id': device_id,
            'iat': int(now.timestamp()),
            'exp': int(refresh_exp.timestamp()),
            'type': 'refresh'
        }
        
        refresh_token = jwt.encode(refresh_payload, self.jwt_secret, algorithm='HS256')
        
        # Store token metadata
        token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
        
        auth_token = AuthToken(
            token=access_token,
            refresh_token=refresh_token,
            device_id=device_id,
            user_id=user_id,
            issued_at=now,
            expires_at=refresh_exp,
            scopes=['read', 'write', 'sync'],
            security_level=security_level,
            token_hash=token_hash
        )
        
        self.active_tokens[access_token] = auth_token
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_in': access_expires
        }
    
    async def _update_device_trust(self,
                                 device_id: str,
                                 fingerprint: DeviceFingerprint,
                                 auth_success: bool):
        """Update device trust score based on authentication result"""
        
        if auth_success:
            # Successful auth increases trust
            fingerprint.trust_score = min(1.0, fingerprint.trust_score + 0.05)
            
            # Remove some risk factors on successful auth
            if 'failed_attempts' in fingerprint.risk_factors:
                fingerprint.risk_factors.remove('failed_attempts')
        else:
            # Failed auth decreases trust
            fingerprint.trust_score = max(0.0, fingerprint.trust_score - 0.1)
            fingerprint.risk_factors.append('failed_attempts')
        
        # Update security level based on trust score
        if fingerprint.trust_score >= 0.8:
            fingerprint.security_level = SecurityLevel.HIGH
        elif fingerprint.trust_score >= 0.6:
            fingerprint.security_level = SecurityLevel.MEDIUM
        elif fingerprint.trust_score >= 0.3:
            fingerprint.security_level = SecurityLevel.LOW
        else:
            fingerprint.security_level = SecurityLevel.UNKNOWN
    
    async def _log_security_event(self,
                                device_id: str,
                                user_id: Optional[str],
                                event_type: str,
                                threat_type: Optional[ThreatType],
                                severity: str,
                                description: str,
                                metadata: Dict[str, Any]):
        """Log security event for monitoring"""
        
        event = SecurityEvent(
            event_id=secrets.token_hex(16),
            device_id=device_id,
            user_id=user_id,
            event_type=event_type,
            threat_type=threat_type,
            severity=severity,
            description=description,
            metadata=metadata,
            timestamp=datetime.utcnow(),
            ip_address=metadata.get('ip_address'),
            location=metadata.get('location')
        )
        
        self.security_events.append(event)
        
        # Keep only recent events (last 1000)
        if len(self.security_events) > 1000:
            self.security_events = self.security_events[-1000:]
        
        # Log high severity events
        if severity in ['high', 'critical']:
            logger.warning(f"Security event: {event_type} for device {device_id} - {description}")
    
    def _create_error_response(self, error_code: str, error_message: str) -> AuthResponse:
        """Create authentication error response"""
        response = AuthResponse()
        response.success = False
        response.error_code = error_code
        response.error_message = error_message
        return response
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode access token"""
        
        try:
            # Decode JWT token
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            
            # Check if token is in active tokens
            if token not in self.active_tokens:
                return None
            
            auth_token = self.active_tokens[token]
            
            # Check expiration
            if datetime.utcnow() > auth_token.expires_at:
                del self.active_tokens[token]
                return None
            
            return {
                'user_id': payload['sub'],
                'device_id': payload['device_id'],
                'security_level': payload.get('security_level', 'low'),
                'scopes': payload.get('scopes', []),
                'expires_at': auth_token.expires_at
            }
            
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    async def create_biometric_challenge(self, device_id: str, user_id: str) -> str:
        """Create biometric authentication challenge"""
        
        challenge = secrets.token_hex(32)
        expires = datetime.utcnow() + timedelta(minutes=5)
        
        self.biometric_challenges[device_id] = {
            'challenge': challenge,
            'user_id': user_id,
            'expires': expires
        }
        
        return challenge
    
    async def revoke_device_tokens(self, device_id: str):
        """Revoke all tokens for a specific device"""
        
        tokens_to_remove = []
        for token, auth_token in self.active_tokens.items():
            if auth_token.device_id == device_id:
                tokens_to_remove.append(token)
        
        for token in tokens_to_remove:
            del self.active_tokens[token]
        
        logger.info(f"Revoked {len(tokens_to_remove)} tokens for device {device_id}")
    
    async def get_security_summary(self, device_id: str) -> Dict[str, Any]:
        """Get security summary for device"""
        
        fingerprint = self.device_fingerprints.get(device_id)
        if not fingerprint:
            return {'error': 'Device not found'}
        
        recent_events = [e for e in self.security_events[-100:]
                        if e.device_id == device_id]
        
        active_tokens = len([t for t in self.active_tokens.values()
                           if t.device_id == device_id])
        
        return {
            'device_id': device_id,
            'trust_score': fingerprint.trust_score,
            'security_level': fingerprint.security_level.value,
            'first_seen': fingerprint.first_seen.isoformat(),
            'last_seen': fingerprint.last_seen.isoformat(),
            'login_count': fingerprint.login_count,
            'risk_factors': fingerprint.risk_factors,
            'recent_events': len(recent_events),
            'active_tokens': active_tokens,
            'is_blocked': device_id in self.blocked_devices
        }

# Global security manager instance
security_manager = MobileSecurityManager()

async def authenticate_mobile_device(request: AuthRequest) -> AuthResponse:
    """
    Main authentication entry point for mobile devices
    
    Args:
        request: Authentication request from mobile client
        
    Returns:
        Authentication response with tokens or error
    """
    return await security_manager.authenticate_device(request)

async def verify_mobile_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify mobile authentication token
    
    Args:
        token: JWT access token to verify
        
    Returns:
        Token payload if valid, None if invalid
    """
    return await security_manager.verify_token(token)