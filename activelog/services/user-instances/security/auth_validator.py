"""
Authentication validator for user instance service
"""
import jwt
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class AuthenticationError(Exception):
    """Authentication related errors"""
    pass

async def validate_user_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Validate user authentication token and return user information
    """
    try:
        # Get auth service URL from environment
        auth_service_url = os.getenv('AUTH_SERVICE_URL', 'http://localhost:8001')
        
        # Validate token with auth service
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{auth_service_url}/validate-token",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10.0
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # Validate required fields
                required_fields = ['user_id', 'email', 'tier_level']
                if not all(field in user_data for field in required_fields):
                    logger.error("Missing required fields in user data")
                    return None
                
                # Add additional user metadata
                user_info = {
                    'user_id': user_data['user_id'],
                    'email': user_data['email'], 
                    'tier_level': user_data['tier_level'],
                    'is_admin': user_data.get('is_admin', False),
                    'subscription_status': user_data.get('subscription_status', 'inactive'),
                    'validated_at': datetime.utcnow().isoformat()
                }
                
                # Check if user can access instance services
                if not can_access_instances(user_info):
                    logger.warning(f"User {user_info['user_id']} cannot access instance services")
                    return None
                
                logger.info(f"Successfully validated user {user_info['user_id']}")
                return user_info
                
            else:
                logger.warning(f"Token validation failed: {response.status_code}")
                return None
                
    except httpx.TimeoutException:
        logger.error("Timeout validating token with auth service")
        return None
    except httpx.RequestError as e:
        logger.error(f"Request error validating token: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating token: {e}")
        return None

def can_access_instances(user_info: Dict[str, Any]) -> bool:
    """
    Check if user can access instance management features
    """
    # Check subscription status
    if user_info.get('subscription_status') not in ['active', 'trial']:
        return False
    
    # Check tier level (must be paid tier)
    tier_level = user_info.get('tier_level', 0)
    if tier_level < 1:  # 0 = free tier
        return False
    
    return True

def get_user_tier_name(tier_level: int) -> str:
    """
    Convert numeric tier level to tier name
    """
    tier_mapping = {
        1: 'starter',
        2: 'professional', 
        3: 'business',
        4: 'enterprise',
        5: 'premium'
    }
    return tier_mapping.get(tier_level, 'starter')

def get_max_instance_resources(tier_level: int) -> Dict[str, Any]:
    """
    Get maximum instance resources allowed for user tier
    """
    resource_limits = {
        1: {  # starter
            'max_instance_type': 't3.small',
            'max_storage_gb': 100,
            'max_monthly_cost': 50.0
        },
        2: {  # professional  
            'max_instance_type': 't3.medium',
            'max_storage_gb': 250,
            'max_monthly_cost': 150.0
        },
        3: {  # business
            'max_instance_type': 't3.large', 
            'max_storage_gb': 500,
            'max_monthly_cost': 350.0
        },
        4: {  # enterprise
            'max_instance_type': 'm5.xlarge',
            'max_storage_gb': 1000,
            'max_monthly_cost': 750.0
        },
        5: {  # premium
            'max_instance_type': 'm5.2xlarge',
            'max_storage_gb': 2000,
            'max_monthly_cost': 1500.0
        }
    }
    
    return resource_limits.get(tier_level, resource_limits[1])

async def validate_admin_access(token: str) -> bool:
    """
    Validate if user has admin access
    """
    user_info = await validate_user_token(token)
    if not user_info:
        return False
    
    return user_info.get('is_admin', False)

def generate_user_session_id(user_id: str) -> str:
    """
    Generate unique session ID for user instance access
    """
    import hashlib
    import secrets
    
    timestamp = str(datetime.utcnow().timestamp())
    random_data = secrets.token_hex(16)
    session_data = f"{user_id}:{timestamp}:{random_data}"
    
    return hashlib.sha256(session_data.encode()).hexdigest()[:32]

class RateLimiter:
    """
    Simple rate limiter for API endpoints
    """
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, user_id: str, max_requests: int = 100, window_minutes: int = 60) -> bool:
        """
        Check if user is within rate limits
        """
        now = datetime.utcnow()
        window_start = now.timestamp() - (window_minutes * 60)
        
        if user_id not in self.requests:
            self.requests[user_id] = []
        
        # Clean old requests
        self.requests[user_id] = [
            req_time for req_time in self.requests[user_id] 
            if req_time > window_start
        ]
        
        # Check if under limit
        if len(self.requests[user_id]) >= max_requests:
            return False
        
        # Add current request
        self.requests[user_id].append(now.timestamp())
        return True

# Global rate limiter instance
rate_limiter = RateLimiter()

def check_rate_limit(user_id: str) -> bool:
    """
    Check if user is within rate limits
    """
    return rate_limiter.is_allowed(user_id)

async def log_security_event(user_id: str, event_type: str, details: Dict[str, Any]):
    """
    Log security events for audit trails
    """
    security_log = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user_id,
        'event_type': event_type,
        'details': details,
        'service': 'user-instances',
        'severity': 'INFO'
    }
    
    # In production, this would send to a security logging service
    logger.info(f"Security event: {security_log}")
    
    # Send to audit service if available
    try:
        audit_service_url = os.getenv('AUDIT_SERVICE_URL')
        if audit_service_url:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{audit_service_url}/security-events",
                    json=security_log,
                    timeout=5.0
                )
    except Exception as e:
        logger.warning(f"Failed to send security event to audit service: {e}")