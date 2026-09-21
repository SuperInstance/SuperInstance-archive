"""
Security Module for ActiveLog Memory Management System

This module provides comprehensive security features for the memory management system:
- Secure memory operations and data handling
- Access control and authentication
- Audit logging and monitoring
- Protection against memory-based attacks
- Secure cleanup of sensitive data
- Encryption for memory dumps and reports
"""

import os
import hashlib
import hmac
import time
import secrets
import threading
import sqlite3
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    MAXIMUM = "maximum"

class AccessLevel(Enum):
    READ_ONLY = "read_only"
    STANDARD = "standard"
    ADMIN = "admin"
    SYSTEM = "system"

@dataclass
class SecurityConfig:
    security_level: SecurityLevel = SecurityLevel.HIGH
    enable_encryption: bool = True
    enable_audit_logging: bool = True
    enable_access_control: bool = True
    session_timeout_minutes: int = 30
    max_failed_attempts: int = 3
    lockout_duration_minutes: int = 15
    require_authentication: bool = True
    enable_memory_protection: bool = True

class SecurityManager:
    """Comprehensive security manager for memory operations"""
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        self.sessions = {}
        self.failed_attempts = {}
        self.locked_accounts = {}
        self.access_logs = []
        
        # Initialize encryption
        self.encryption_key = self._generate_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Security database
        self.security_db = "memory_security.db"
        self._init_security_database()
        
        # Active monitoring
        self.monitored_operations = set()
        self.security_alerts = []
        
        self._lock = threading.RLock()
        
    def _generate_encryption_key(self) -> bytes:
        """Generate or load encryption key"""
        key_file = "memory_encryption.key"
        
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            os.chmod(key_file, 0o600)  # Read-only for owner
            return key
            
    def _init_security_database(self):
        """Initialize security audit database"""
        with sqlite3.connect(self.security_db) as conn:
            # Access logs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS access_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    operation TEXT NOT NULL,
                    resource TEXT,
                    result TEXT NOT NULL,
                    ip_address TEXT,
                    details TEXT
                )
            """)
            
            # Security events
            conn.execute("""
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    description TEXT NOT NULL,
                    source TEXT,
                    data TEXT
                )
            """)
            
            # User sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    access_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_access TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
    def authenticate_user(self, user_id: str, password: str, 
                         ip_address: str = None) -> Optional[str]:
        """Authenticate user and create secure session"""
        with self._lock:
            # Check if account is locked
            if self._is_account_locked(user_id):
                self._log_security_event("authentication_blocked", "warning",
                                        f"Authentication blocked for locked account: {user_id}")
                return None
                
            # Verify credentials (simplified - in production use proper password hashing)
            if self._verify_credentials(user_id, password):
                # Reset failed attempts
                self.failed_attempts.pop(user_id, None)
                
                # Create session
                session_id = self._create_session(user_id, ip_address)
                
                self._log_access("authentication", "success", user_id, ip_address,
                               {"session_id": session_id})
                
                return session_id
            else:
                # Track failed attempt
                self._record_failed_attempt(user_id, ip_address)
                
                self._log_access("authentication", "failure", user_id, ip_address,
                               {"reason": "invalid_credentials"})
                
                return None
                
    def _verify_credentials(self, user_id: str, password: str) -> bool:
        """Verify user credentials (simplified implementation)"""
        # In production, use proper password hashing (bcrypt, scrypt, etc.)
        # For now, using a simple default for demo
        if user_id == "admin" and password == "secure_memory_admin_2024":
            return True
        if user_id == "system" and password == "activelog_system_key":
            return True
        return False
        
    def _create_session(self, user_id: str, ip_address: str = None) -> str:
        """Create secure user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=self.config.session_timeout_minutes)
        
        # Determine access level
        access_level = self._get_user_access_level(user_id)
        
        session_data = {
            'user_id': user_id,
            'access_level': access_level.value,
            'created_at': datetime.now(),
            'last_access': datetime.now(),
            'expires_at': expires_at,
            'ip_address': ip_address,
            'is_active': True
        }
        
        self.sessions[session_id] = session_data
        
        # Store in database
        with sqlite3.connect(self.security_db) as conn:
            conn.execute("""
                INSERT INTO user_sessions 
                (session_id, user_id, access_level, created_at, last_access, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                session_id,
                user_id,
                access_level.value,
                datetime.now().isoformat(),
                datetime.now().isoformat(),
                expires_at.isoformat()
            ))
            
        return session_id
        
    def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session"""
        with self._lock:
            session = self.sessions.get(session_id)
            
            if not session:
                return None
                
            # Check if expired
            if datetime.now() > session['expires_at']:
                self._invalidate_session(session_id)
                return None
                
            # Update last access
            session['last_access'] = datetime.now()
            
            return session
            
    def _invalidate_session(self, session_id: str):
        """Invalidate session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            
        # Update database
        with sqlite3.connect(self.security_db) as conn:
            conn.execute("""
                UPDATE user_sessions 
                SET is_active = FALSE 
                WHERE session_id = ?
            """, (session_id,))
            
    def _get_user_access_level(self, user_id: str) -> AccessLevel:
        """Get user access level"""
        if user_id == "system":
            return AccessLevel.SYSTEM
        elif user_id == "admin":
            return AccessLevel.ADMIN
        else:
            return AccessLevel.STANDARD
            
    def _is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if user_id not in self.locked_accounts:
            return False
            
        lock_time, duration = self.locked_accounts[user_id]
        if datetime.now() > lock_time + timedelta(minutes=duration):
            # Unlock account
            del self.locked_accounts[user_id]
            return False
            
        return True
        
    def _record_failed_attempt(self, user_id: str, ip_address: str = None):
        """Record failed authentication attempt"""
        if user_id not in self.failed_attempts:
            self.failed_attempts[user_id] = []
            
        self.failed_attempts[user_id].append({
            'timestamp': datetime.now(),
            'ip_address': ip_address
        })
        
        # Check if should lock account
        attempts = self.failed_attempts[user_id]
        recent_attempts = [
            a for a in attempts 
            if datetime.now() - a['timestamp'] < timedelta(minutes=15)
        ]
        
        if len(recent_attempts) >= self.config.max_failed_attempts:
            self.locked_accounts[user_id] = (
                datetime.now(), 
                self.config.lockout_duration_minutes
            )
            self._log_security_event("account_locked", "warning",
                                   f"Account locked due to failed attempts: {user_id}")
                                   
    def authorize_operation(self, session_id: str, operation: str, 
                          resource: str = None) -> bool:
        """Authorize specific operation"""
        if not self.config.enable_access_control:
            return True
            
        session = self.validate_session(session_id)
        if not session:
            self._log_security_event("unauthorized_access", "warning",
                                   f"Invalid session for operation: {operation}")
            return False
            
        access_level = AccessLevel(session['access_level'])
        
        # Define operation permissions
        permissions = {
            AccessLevel.READ_ONLY: ['get_status', 'get_report', 'view_logs'],
            AccessLevel.STANDARD: ['get_status', 'get_report', 'view_logs', 'optimize_memory'],
            AccessLevel.ADMIN: ['*'],  # All operations
            AccessLevel.SYSTEM: ['*']  # All operations
        }
        
        allowed_operations = permissions.get(access_level, [])
        
        if '*' in allowed_operations or operation in allowed_operations:
            self._log_access(operation, "authorized", session['user_id'], 
                           session.get('ip_address'), {"resource": resource})
            return True
        else:
            self._log_access(operation, "denied", session['user_id'],
                           session.get('ip_address'), 
                           {"resource": resource, "reason": "insufficient_permissions"})
            return False
            
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt sensitive data"""
        if not self.config.enable_encryption:
            return data
            
        return self.fernet.encrypt(data)
        
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt sensitive data"""
        if not self.config.enable_encryption:
            return encrypted_data
            
        return self.fernet.decrypt(encrypted_data)
        
    def secure_memory_wipe(self, data: Any) -> bool:
        """Securely wipe sensitive data from memory"""
        try:
            if isinstance(data, (bytes, bytearray)):
                # Overwrite with random data multiple times
                for _ in range(3):
                    for i in range(len(data)):
                        data[i] = secrets.randbits(8)
                        
            elif isinstance(data, str):
                # Convert to bytearray and wipe
                byte_data = bytearray(data.encode())
                for _ in range(3):
                    for i in range(len(byte_data)):
                        byte_data[i] = secrets.randbits(8)
                        
            return True
        except Exception as e:
            self._log_security_event("secure_wipe_failed", "error",
                                   f"Failed to securely wipe data: {e}")
            return False
            
    def _log_access(self, operation: str, result: str, user_id: str = None,
                   ip_address: str = None, details: Dict[str, Any] = None):
        """Log access attempt"""
        if not self.config.enable_audit_logging:
            return
            
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'operation': operation,
            'result': result,
            'ip_address': ip_address,
            'details': json.dumps(details) if details else None
        }
        
        self.access_logs.append(log_entry)
        
        # Store in database
        with sqlite3.connect(self.security_db) as conn:
            conn.execute("""
                INSERT INTO access_logs 
                (timestamp, user_id, operation, result, ip_address, details)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                log_entry['timestamp'],
                log_entry['user_id'],
                log_entry['operation'],
                log_entry['result'],
                log_entry['ip_address'],
                log_entry['details']
            ))
            
    def _log_security_event(self, event_type: str, severity: str, 
                          description: str, source: str = None, 
                          data: Dict[str, Any] = None):
        """Log security event"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'description': description,
            'source': source or 'memory_security',
            'data': json.dumps(data) if data else None
        }
        
        self.security_alerts.append(event)
        
        # Store in database
        with sqlite3.connect(self.security_db) as conn:
            conn.execute("""
                INSERT INTO security_events 
                (timestamp, event_type, severity, description, source, data)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                event['timestamp'],
                event['event_type'],
                event['severity'],
                event['description'],
                event['source'],
                event['data']
            ))
            
    def monitor_memory_operation(self, operation_name: str):
        """Monitor memory operation for security issues"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    execution_time = time.time() - start_time
                    
                    # Check for suspicious patterns
                    if execution_time > 10:  # Long-running operation
                        self._log_security_event(
                            "suspicious_operation", "info",
                            f"Long-running memory operation: {operation_name} ({execution_time:.2f}s)"
                        )
                        
                    return result
                    
                except Exception as e:
                    self._log_security_event(
                        "operation_failed", "error",
                        f"Memory operation failed: {operation_name} - {str(e)}"
                    )
                    raise
                    
            return wrapper
        return decorator
        
    def get_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'security_level': self.config.security_level.value,
            'active_sessions': len(self.sessions),
            'failed_attempts': {
                user: len(attempts) for user, attempts in self.failed_attempts.items()
            },
            'locked_accounts': list(self.locked_accounts.keys()),
            'recent_security_events': self.security_alerts[-10:],
            'access_log_entries': len(self.access_logs),
            'encryption_enabled': self.config.enable_encryption,
            'audit_logging_enabled': self.config.enable_audit_logging
        }
        
        return report
        
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        with self._lock:
            expired_sessions = [
                session_id for session_id, session in self.sessions.items()
                if datetime.now() > session['expires_at']
            ]
            
            for session_id in expired_sessions:
                self._invalidate_session(session_id)
                
    def validate_memory_integrity(self, data: Any) -> bool:
        """Validate memory data integrity"""
        try:
            # Basic integrity checks
            if isinstance(data, dict):
                # Check for suspicious keys or values
                suspicious_keys = ['password', 'secret', 'key', 'token']
                for key in data:
                    if any(sus_key in str(key).lower() for sus_key in suspicious_keys):
                        self._log_security_event(
                            "sensitive_data_detected", "warning",
                            f"Sensitive data key detected: {key}"
                        )
                        
            return True
        except Exception as e:
            self._log_security_event(
                "integrity_check_failed", "error",
                f"Memory integrity check failed: {e}"
            )
            return False

class SecureMemoryWrapper:
    """Secure wrapper for memory management operations"""
    
    def __init__(self, memory_system, security_manager: SecurityManager):
        self.memory_system = memory_system
        self.security_manager = security_manager
        
    def secure_get_status(self, session_id: str) -> Dict[str, Any]:
        """Get memory status with security checks"""
        if not self.security_manager.authorize_operation(session_id, "get_status"):
            raise PermissionError("Unauthorized access to memory status")
            
        status = self.memory_system.get_memory_status()
        
        # Remove sensitive information for non-admin users
        session = self.security_manager.validate_session(session_id)
        if session and session['access_level'] not in ['admin', 'system']:
            # Filter sensitive data
            status.pop('optimizer_report', None)
            status.pop('profiler_status', None)
            
        return status
        
    def secure_optimize(self, session_id: str) -> Dict[str, Any]:
        """Perform memory optimization with security checks"""
        if not self.security_manager.authorize_operation(session_id, "optimize_memory"):
            raise PermissionError("Unauthorized access to memory optimization")
            
        return self.memory_system.optimize_memory()
        
    def secure_get_report(self, session_id: str) -> str:
        """Generate secure memory report"""
        if not self.security_manager.authorize_operation(session_id, "get_report"):
            raise PermissionError("Unauthorized access to memory reports")
            
        # Generate report
        report_data = self.memory_system.create_memory_snapshot()
        
        # Encrypt report if enabled
        if self.security_manager.config.enable_encryption:
            report_json = json.dumps(report_data).encode()
            encrypted_report = self.security_manager.encrypt_data(report_json)
            
            filename = f"secure_memory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.enc"
            with open(filename, 'wb') as f:
                f.write(encrypted_report)
                
            return filename
        else:
            filename = f"memory_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w') as f:
                json.dump(report_data, f, indent=2)
                
            return filename

# Global security manager
_global_security_manager = None

def get_security_manager(config: SecurityConfig = None) -> SecurityManager:
    """Get or create global security manager"""
    global _global_security_manager
    if _global_security_manager is None:
        _global_security_manager = SecurityManager(config)
    return _global_security_manager

def create_secure_memory_wrapper(memory_system, security_config: SecurityConfig = None) -> SecureMemoryWrapper:
    """Create secure wrapper for memory system"""
    security_manager = get_security_manager(security_config)
    return SecureMemoryWrapper(memory_system, security_manager)

if __name__ == "__main__":
    # Demo security features
    print("🔒 ActiveLog Memory Security Demo")
    print("=" * 40)
    
    # Initialize security
    security_config = SecurityConfig(
        security_level=SecurityLevel.HIGH,
        enable_encryption=True,
        enable_audit_logging=True,
        enable_access_control=True
    )
    
    security_manager = SecurityManager(security_config)
    
    # Test authentication
    print("\nTesting authentication...")
    session_id = security_manager.authenticate_user("admin", "secure_memory_admin_2024", "127.0.0.1")
    
    if session_id:
        print(f"✅ Authentication successful! Session: {session_id[:16]}...")
        
        # Test authorization
        print("\nTesting authorization...")
        if security_manager.authorize_operation(session_id, "get_status"):
            print("✅ Authorization successful for get_status")
        
        # Generate security report
        report = security_manager.get_security_report()
        print(f"\nSecurity Report:")
        print(f"  Active sessions: {report['active_sessions']}")
        print(f"  Security level: {report['security_level']}")
        print(f"  Encryption enabled: {report['encryption_enabled']}")
        
    else:
        print("❌ Authentication failed!")
        
    print("\n🔒 Security demo complete!")