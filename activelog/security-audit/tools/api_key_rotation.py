"""
API Key Rotation Mechanism for ActiveLog
Implements secure API key generation, rotation, and management system.
"""

import os
import secrets
import hashlib
import hmac
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import sqlite3
import asyncio
import aioredis
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import logging


class APIKeyManager:
    """Manages API key generation, rotation, and validation."""
    
    def __init__(self, db_path: str = None, redis_url: str = None, encryption_key: bytes = None):
        self.db_path = db_path or "/tmp/api_keys.db"
        self.redis_url = redis_url or "redis://localhost:6379"
        self.redis = None
        
        # Setup encryption
        if encryption_key:
            self.fernet = Fernet(encryption_key)
        else:
            self.fernet = Fernet(Fernet.generate_key())
        
        # Key configuration
        self.key_config = {
            'length': 32,  # 256 bits
            'prefix': 'ak_',  # ActiveLog Key prefix
            'default_ttl': 86400 * 30,  # 30 days
            'rotation_window': 86400 * 7,  # 7 days overlap
            'max_requests_per_hour': 1000,
            'algorithms': ['HS256', 'HS384', 'HS512']
        }
        
        # Initialize database
        self._init_database()
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def _init_database(self):
        """Initialize SQLite database for API key storage."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create API keys table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                encrypted_key TEXT NOT NULL,
                user_id TEXT NOT NULL,
                service_name TEXT,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                last_used_at TIMESTAMP,
                request_count INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT 1,
                rotation_group TEXT,
                metadata TEXT
            )
        ''')
        
        # Create key rotation log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_rotation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                old_key_id TEXT,
                new_key_id TEXT,
                user_id TEXT,
                rotation_reason TEXT,
                rotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
        ''')
        
        # Create key usage log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS key_usage_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT,
                user_id TEXT,
                endpoint TEXT,
                ip_address TEXT,
                user_agent TEXT,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_key_id ON api_keys(key_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_expires_at ON api_keys(expires_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_key_usage_log_key_id ON key_usage_log(key_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_key_usage_log_used_at ON key_usage_log(used_at)')
        
        conn.commit()
        conn.close()
    
    async def _get_redis(self):
        """Get Redis connection for caching."""
        if not self.redis:
            try:
                self.redis = await aioredis.from_url(self.redis_url)
            except Exception as e:
                self.logger.warning(f"Failed to connect to Redis: {e}")
        return self.redis
    
    def generate_api_key(self, user_id: str, service_name: str = None, 
                        permissions: List[str] = None, ttl_days: int = 30) -> Dict[str, Any]:
        """
        Generate a new API key.
        
        Args:
            user_id: User identifier
            service_name: Optional service name
            permissions: List of permissions for this key
            ttl_days: Time to live in days
            
        Returns:
            Dictionary with key information
        """
        # Generate cryptographically secure random key
        raw_key = secrets.token_urlsafe(self.key_config['length'])
        key_id = f"{self.key_config['prefix']}{secrets.token_urlsafe(16)}"
        
        # Create full API key
        api_key = f"{key_id}.{raw_key}"
        
        # Hash the key for storage
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Encrypt the key for storage
        encrypted_key = self.fernet.encrypt(api_key.encode()).decode()
        
        # Calculate expiration
        expires_at = datetime.now() + timedelta(days=ttl_days)
        
        # Generate rotation group ID
        rotation_group = f"rg_{secrets.token_hex(8)}"
        
        # Prepare metadata
        metadata = {
            'created_by': 'api_key_manager',
            'algorithm': 'HS256',
            'key_type': 'bearer'
        }
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO api_keys (
                    key_id, key_hash, encrypted_key, user_id, service_name,
                    permissions, expires_at, rotation_group, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                key_id, key_hash, encrypted_key, user_id, service_name,
                json.dumps(permissions or []), expires_at, rotation_group,
                json.dumps(metadata)
            ))
            
            conn.commit()
            
            result = {
                'api_key': api_key,
                'key_id': key_id,
                'user_id': user_id,
                'service_name': service_name,
                'permissions': permissions or [],
                'expires_at': expires_at.isoformat(),
                'rotation_group': rotation_group,
                'created_at': datetime.now().isoformat()
            }
            
            self.logger.info(f"Generated API key for user {user_id}: {key_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to generate API key: {e}")
            raise
        finally:
            conn.close()
    
    def validate_api_key(self, api_key: str, endpoint: str = None, 
                        ip_address: str = None) -> Dict[str, Any]:
        """
        Validate an API key and log usage.
        
        Args:
            api_key: The API key to validate
            endpoint: Optional endpoint being accessed
            ip_address: Optional IP address of request
            
        Returns:
            Validation result with key information
        """
        result = {
            'valid': False,
            'key_id': None,
            'user_id': None,
            'permissions': [],
            'error': None,
            'rate_limited': False
        }
        
        try:
            # Extract key_id from API key
            if '.' not in api_key or not api_key.startswith(self.key_config['prefix']):
                result['error'] = 'Invalid API key format'
                return result
            
            key_parts = api_key.split('.', 1)
            key_id = key_parts[0]
            
            # Hash the provided key
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            # Look up key in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT key_id, key_hash, user_id, service_name, permissions,
                       expires_at, is_active, request_count, last_used_at
                FROM api_keys
                WHERE key_id = ? AND key_hash = ?
            ''', (key_id, key_hash))
            
            row = cursor.fetchone()
            if not row:
                result['error'] = 'API key not found'
                self._log_key_usage(key_id, None, endpoint, ip_address, False, 'Key not found')
                return result
            
            (stored_key_id, stored_hash, user_id, service_name, permissions_json,
             expires_at_str, is_active, request_count, last_used_at) = row
            
            # Check if key is active
            if not is_active:
                result['error'] = 'API key is inactive'
                self._log_key_usage(key_id, user_id, endpoint, ip_address, False, 'Key inactive')
                return result
            
            # Check expiration
            expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
            if datetime.now() > expires_at:
                result['error'] = 'API key expired'
                self._log_key_usage(key_id, user_id, endpoint, ip_address, False, 'Key expired')
                return result
            
            # Check rate limiting
            if self._is_rate_limited(key_id, request_count):
                result['error'] = 'Rate limit exceeded'
                result['rate_limited'] = True
                self._log_key_usage(key_id, user_id, endpoint, ip_address, False, 'Rate limited')
                return result
            
            # Update usage statistics
            cursor.execute('''
                UPDATE api_keys
                SET request_count = request_count + 1, last_used_at = CURRENT_TIMESTAMP
                WHERE key_id = ?
            ''', (key_id,))
            
            conn.commit()
            
            # Log successful usage
            self._log_key_usage(key_id, user_id, endpoint, ip_address, True, None)
            
            # Return successful result
            result.update({
                'valid': True,
                'key_id': key_id,
                'user_id': user_id,
                'service_name': service_name,
                'permissions': json.loads(permissions_json) if permissions_json else [],
                'expires_at': expires_at_str
            })
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            result['error'] = 'Internal validation error'
            return result
        finally:
            if 'conn' in locals():
                conn.close()
    
    def _is_rate_limited(self, key_id: str, current_count: int) -> bool:
        """Check if API key is rate limited."""
        max_requests = self.key_config['max_requests_per_hour']
        
        # Check requests in the last hour
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        one_hour_ago = datetime.now() - timedelta(hours=1)
        cursor.execute('''
            SELECT COUNT(*) FROM key_usage_log
            WHERE key_id = ? AND used_at > ? AND success = 1
        ''', (key_id, one_hour_ago))
        
        recent_requests = cursor.fetchone()[0]
        conn.close()
        
        return recent_requests >= max_requests
    
    def _log_key_usage(self, key_id: str, user_id: str, endpoint: str, 
                      ip_address: str, success: bool, error_message: str):
        """Log API key usage."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO key_usage_log (
                    key_id, user_id, endpoint, ip_address, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (key_id, user_id, endpoint, ip_address, success, error_message))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to log key usage: {e}")
    
    def rotate_api_key(self, key_id: str, reason: str = "scheduled_rotation") -> Dict[str, Any]:
        """
        Rotate an API key by creating a new one and marking the old one for deprecation.
        
        Args:
            key_id: The key ID to rotate
            reason: Reason for rotation
            
        Returns:
            New key information
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Get current key info
            cursor.execute('''
                SELECT user_id, service_name, permissions, rotation_group
                FROM api_keys
                WHERE key_id = ? AND is_active = 1
            ''', (key_id,))
            
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"API key {key_id} not found or inactive")
            
            user_id, service_name, permissions_json, rotation_group = row
            permissions = json.loads(permissions_json) if permissions_json else []
            
            # Generate new key with same permissions
            new_key_info = self.generate_api_key(
                user_id=user_id,
                service_name=service_name,
                permissions=permissions,
                ttl_days=30
            )
            
            # Update rotation group for new key
            cursor.execute('''
                UPDATE api_keys
                SET rotation_group = ?
                WHERE key_id = ?
            ''', (rotation_group, new_key_info['key_id']))
            
            # Mark old key as inactive after rotation window
            deactivation_time = datetime.now() + timedelta(days=7)  # 7 day overlap
            cursor.execute('''
                UPDATE api_keys
                SET expires_at = ?
                WHERE key_id = ?
            ''', (deactivation_time, key_id))
            
            # Log rotation
            cursor.execute('''
                INSERT INTO key_rotation_log (
                    old_key_id, new_key_id, user_id, rotation_reason, metadata
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                key_id, new_key_info['key_id'], user_id, reason,
                json.dumps({'rotation_window_days': 7})
            ))
            
            conn.commit()
            
            self.logger.info(f"Rotated API key {key_id} -> {new_key_info['key_id']}")
            
            return {
                'old_key_id': key_id,
                'new_key_id': new_key_info['key_id'],
                'new_api_key': new_key_info['api_key'],
                'rotation_reason': reason,
                'overlap_period_days': 7,
                'old_key_expires_at': deactivation_time.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to rotate API key {key_id}: {e}")
            raise
        finally:
            conn.close()
    
    def revoke_api_key(self, key_id: str, reason: str = "manual_revocation") -> bool:
        """
        Immediately revoke an API key.
        
        Args:
            key_id: The key ID to revoke
            reason: Reason for revocation
            
        Returns:
            True if successfully revoked
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Deactivate the key
            cursor.execute('''
                UPDATE api_keys
                SET is_active = 0, expires_at = CURRENT_TIMESTAMP
                WHERE key_id = ?
            ''', (key_id,))
            
            if cursor.rowcount == 0:
                return False
            
            # Log revocation
            cursor.execute('''
                INSERT INTO key_rotation_log (
                    old_key_id, rotation_reason, metadata
                ) VALUES (?, ?, ?)
            ''', (key_id, reason, json.dumps({'action': 'revoked'})))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Revoked API key {key_id}: {reason}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to revoke API key {key_id}: {e}")
            return False
    
    def list_user_keys(self, user_id: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all API keys for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        where_clause = "WHERE user_id = ?"
        params = [user_id]
        
        if not include_inactive:
            where_clause += " AND is_active = 1"
        
        cursor.execute(f'''
            SELECT key_id, service_name, permissions, created_at, expires_at,
                   last_used_at, request_count, is_active, rotation_group
            FROM api_keys
            {where_clause}
            ORDER BY created_at DESC
        ''', params)
        
        keys = []
        for row in cursor.fetchall():
            (key_id, service_name, permissions_json, created_at, expires_at,
             last_used_at, request_count, is_active, rotation_group) = row
            
            keys.append({
                'key_id': key_id,
                'service_name': service_name,
                'permissions': json.loads(permissions_json) if permissions_json else [],
                'created_at': created_at,
                'expires_at': expires_at,
                'last_used_at': last_used_at,
                'request_count': request_count,
                'is_active': bool(is_active),
                'rotation_group': rotation_group
            })
        
        conn.close()
        return keys
    
    def get_key_usage_stats(self, key_id: str = None, user_id: str = None,
                           hours: int = 24) -> Dict[str, Any]:
        """Get usage statistics for API keys."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since = datetime.now() - timedelta(hours=hours)
        
        where_conditions = ["used_at > ?"]
        params = [since]
        
        if key_id:
            where_conditions.append("key_id = ?")
            params.append(key_id)
        
        if user_id:
            where_conditions.append("user_id = ?")
            params.append(user_id)
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Get usage counts
        cursor.execute(f'''
            SELECT 
                COUNT(*) as total_requests,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful_requests,
                COUNT(CASE WHEN success = 0 THEN 1 END) as failed_requests,
                COUNT(DISTINCT key_id) as unique_keys,
                COUNT(DISTINCT user_id) as unique_users
            FROM key_usage_log
            {where_clause}
        ''', params)
        
        stats = cursor.fetchone()
        
        # Get top endpoints
        cursor.execute(f'''
            SELECT endpoint, COUNT(*) as request_count
            FROM key_usage_log
            {where_clause}
            GROUP BY endpoint
            ORDER BY request_count DESC
            LIMIT 10
        ''', params)
        
        top_endpoints = [{'endpoint': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Get error breakdown
        cursor.execute(f'''
            SELECT error_message, COUNT(*) as error_count
            FROM key_usage_log
            {where_clause} AND success = 0
            GROUP BY error_message
            ORDER BY error_count DESC
            LIMIT 10
        ''', params)
        
        error_breakdown = [{'error': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'period_hours': hours,
            'total_requests': stats[0],
            'successful_requests': stats[1],
            'failed_requests': stats[2],
            'unique_keys': stats[3],
            'unique_users': stats[4],
            'success_rate': (stats[1] / stats[0] * 100) if stats[0] > 0 else 0,
            'top_endpoints': top_endpoints,
            'error_breakdown': error_breakdown
        }
    
    def schedule_automatic_rotation(self, rotation_interval_days: int = 30):
        """Schedule automatic API key rotation."""
        # This would typically be implemented with a task scheduler like Celery
        # For now, we'll provide a method to check for keys that need rotation
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        rotation_threshold = datetime.now() + timedelta(days=7)  # Rotate 7 days before expiry
        
        cursor.execute('''
            SELECT key_id, user_id, expires_at
            FROM api_keys
            WHERE is_active = 1 AND expires_at < ?
            ORDER BY expires_at ASC
        ''', (rotation_threshold,))
        
        keys_to_rotate = []
        for row in cursor.fetchall():
            key_id, user_id, expires_at = row
            keys_to_rotate.append({
                'key_id': key_id,
                'user_id': user_id,
                'expires_at': expires_at
            })
        
        conn.close()
        
        self.logger.info(f"Found {len(keys_to_rotate)} keys needing rotation")
        
        # Rotate keys
        rotation_results = []
        for key_info in keys_to_rotate:
            try:
                result = self.rotate_api_key(key_info['key_id'], "automatic_rotation")
                rotation_results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to auto-rotate key {key_info['key_id']}: {e}")
        
        return rotation_results
    
    def cleanup_expired_keys(self):
        """Remove expired and revoked keys from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Remove keys expired for more than 30 days
        cleanup_threshold = datetime.now() - timedelta(days=30)
        
        cursor.execute('''
            DELETE FROM api_keys
            WHERE (is_active = 0 OR expires_at < ?) AND expires_at < ?
        ''', (datetime.now(), cleanup_threshold))
        
        deleted_count = cursor.rowcount
        
        # Cleanup old usage logs (keep last 90 days)
        log_cleanup_threshold = datetime.now() - timedelta(days=90)
        cursor.execute('''
            DELETE FROM key_usage_log
            WHERE used_at < ?
        ''', (log_cleanup_threshold,))
        
        log_deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Cleaned up {deleted_count} expired keys and {log_deleted_count} old logs")
        
        return {
            'expired_keys_removed': deleted_count,
            'old_logs_removed': log_deleted_count
        }


class APIKeyRotationService:
    """Service for managing API key rotation in production."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.key_manager = APIKeyManager(
            db_path=config.get('db_path'),
            redis_url=config.get('redis_url'),
            encryption_key=config.get('encryption_key')
        )
        
        # Setup automatic rotation schedule
        self.rotation_schedule = {
            'interval_hours': config.get('rotation_interval_hours', 24),
            'enabled': config.get('auto_rotation_enabled', True)
        }
    
    async def start_rotation_service(self):
        """Start the background rotation service."""
        if not self.rotation_schedule['enabled']:
            return
        
        while True:
            try:
                # Check for keys needing rotation
                results = self.key_manager.schedule_automatic_rotation()
                
                if results:
                    print(f"Auto-rotated {len(results)} API keys")
                
                # Cleanup expired keys
                cleanup_results = self.key_manager.cleanup_expired_keys()
                print(f"Cleaned up {cleanup_results['expired_keys_removed']} expired keys")
                
                # Wait for next rotation check
                await asyncio.sleep(self.rotation_schedule['interval_hours'] * 3600)
                
            except Exception as e:
                print(f"Error in rotation service: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes before retrying


def main():
    """Demo of API key rotation system."""
    print("🔑 Setting up API Key Rotation System...")
    
    # Initialize key manager
    key_manager = APIKeyManager()
    
    # Generate test API keys
    print("\n📋 Generating test API keys...")
    
    # User 1: Admin with full permissions
    admin_key = key_manager.generate_api_key(
        user_id="admin_user",
        service_name="activelog_admin",
        permissions=["read", "write", "delete", "admin"],
        ttl_days=30
    )
    print(f"Admin API Key: {admin_key['key_id']}")
    
    # User 2: Regular user with limited permissions
    user_key = key_manager.generate_api_key(
        user_id="regular_user",
        service_name="activelog_api",
        permissions=["read", "write"],
        ttl_days=30
    )
    print(f"User API Key: {user_key['key_id']}")
    
    # Test key validation
    print("\n🔍 Testing key validation...")
    validation_result = key_manager.validate_api_key(
        admin_key['api_key'],
        endpoint="/api/v1/files",
        ip_address="192.168.1.100"
    )
    print(f"Validation result: {validation_result['valid']}")
    print(f"User ID: {validation_result['user_id']}")
    print(f"Permissions: {validation_result['permissions']}")
    
    # Test key rotation
    print("\n🔄 Testing key rotation...")
    rotation_result = key_manager.rotate_api_key(
        admin_key['key_id'],
        reason="security_audit"
    )
    print(f"Rotated {rotation_result['old_key_id']} -> {rotation_result['new_key_id']}")
    print(f"Overlap period: {rotation_result['overlap_period_days']} days")
    
    # Test usage statistics
    print("\n📊 Getting usage statistics...")
    stats = key_manager.get_key_usage_stats(hours=24)
    print(f"Total requests: {stats['total_requests']}")
    print(f"Success rate: {stats['success_rate']:.1f}%")
    
    # List user keys
    print("\n📝 Listing user keys...")
    user_keys = key_manager.list_user_keys("admin_user")
    for key in user_keys:
        print(f"  Key: {key['key_id']}, Active: {key['is_active']}, Requests: {key['request_count']}")
    
    # Test automatic rotation
    print("\n⚙️ Testing automatic rotation...")
    auto_rotation_results = key_manager.schedule_automatic_rotation()
    print(f"Keys auto-rotated: {len(auto_rotation_results)}")
    
    # Cleanup
    print("\n🧹 Testing cleanup...")
    cleanup_results = key_manager.cleanup_expired_keys()
    print(f"Expired keys removed: {cleanup_results['expired_keys_removed']}")
    print(f"Old logs removed: {cleanup_results['old_logs_removed']}")
    
    print("\n✅ API Key Rotation System demo completed!")
    
    # Generate configuration file
    config_path = Path(__file__).parent.parent / "configs" / "api_key_rotation_config.yaml"
    config_path.parent.mkdir(exist_ok=True)
    
    config = {
        'api_key_rotation': {
            'database': {
                'path': '/var/lib/activelog/api_keys.db',
                'backup_enabled': True,
                'backup_interval_hours': 24
            },
            'redis': {
                'url': 'redis://localhost:6379',
                'key_prefix': 'activelog:api_keys:'
            },
            'rotation': {
                'auto_rotation_enabled': True,
                'rotation_interval_hours': 24,
                'rotation_window_days': 7,
                'max_key_age_days': 30
            },
            'security': {
                'key_length': 32,
                'encryption_enabled': True,
                'rate_limiting': {
                    'max_requests_per_hour': 1000,
                    'burst_limit': 50
                }
            },
            'monitoring': {
                'log_usage': True,
                'alert_on_suspicious_activity': True,
                'usage_stats_retention_days': 90
            }
        }
    }
    
    import yaml
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"\n📄 Configuration saved to: {config_path}")


if __name__ == "__main__":
    main()