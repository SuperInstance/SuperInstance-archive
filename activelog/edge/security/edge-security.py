#!/usr/bin/env python3
"""
ActiveLog Edge Security Manager
Comprehensive security implementation for edge devices including encryption, authentication, and monitoring
"""

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import ssl
import time
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.x509 import load_pem_x509_certificate
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sqlite3
import subprocess
import ipaddress

class SecurityLevel:
    """Security level definitions"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    MAXIMUM = "maximum"

class EncryptionManager:
    """Handles encryption/decryption operations"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.encryption_key = None
        self.device_keypair = None
        self.certificate = None
        self.logger = logging.getLogger(__name__)
        
        # Initialize encryption components
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption keys and certificates"""
        security_dir = Path(self.config.get("security_dir", "/etc/activelog/security"))
        security_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or generate device key
        key_file = security_dir / "device.key"
        if key_file.exists():
            self.encryption_key = self._load_key(key_file)
        else:
            self.encryption_key = self._generate_key()
            self._save_key(key_file, self.encryption_key)
        
        # Load or generate RSA keypair
        keypair_file = security_dir / "device_rsa.key"
        if keypair_file.exists():
            self.device_keypair = self._load_rsa_keypair(keypair_file)
        else:
            self.device_keypair = self._generate_rsa_keypair()
            self._save_rsa_keypair(keypair_file, self.device_keypair)
        
        # Load certificate if available
        cert_file = security_dir / "device.crt"
        if cert_file.exists():
            self.certificate = self._load_certificate(cert_file)
        
        self.logger.info("Encryption manager initialized")
    
    def _generate_key(self) -> bytes:
        """Generate a new encryption key"""
        return Fernet.generate_key()
    
    def _save_key(self, key_file: Path, key: bytes):
        """Save encryption key to file"""
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Restrict permissions
    
    def _load_key(self, key_file: Path) -> bytes:
        """Load encryption key from file"""
        return key_file.read_bytes()
    
    def _generate_rsa_keypair(self):
        """Generate RSA keypair"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        return private_key
    
    def _save_rsa_keypair(self, keypair_file: Path, keypair):
        """Save RSA keypair to file"""
        pem = keypair.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        keypair_file.write_bytes(pem)
        keypair_file.chmod(0o600)
    
    def _load_rsa_keypair(self, keypair_file: Path):
        """Load RSA keypair from file"""
        pem_data = keypair_file.read_bytes()
        return serialization.load_pem_private_key(pem_data, password=None)
    
    def _load_certificate(self, cert_file: Path):
        """Load X.509 certificate"""
        cert_data = cert_file.read_bytes()
        return load_pem_x509_certificate(cert_data)
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet symmetric encryption"""
        fernet = Fernet(self.encryption_key)
        return fernet.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet symmetric encryption"""
        fernet = Fernet(self.encryption_key)
        return fernet.decrypt(encrypted_data)
    
    def encrypt_with_rsa(self, data: bytes, public_key) -> bytes:
        """Encrypt data using RSA public key"""
        return public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt_with_rsa(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using RSA private key"""
        return self.device_keypair.decrypt(
            encrypted_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def sign_data(self, data: bytes) -> bytes:
        """Sign data using RSA private key"""
        return self.device_keypair.sign(
            data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def verify_signature(self, data: bytes, signature: bytes, public_key) -> bool:
        """Verify signature using RSA public key"""
        try:
            public_key.verify(
                signature,
                data,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except:
            return False
    
    def get_public_key_pem(self) -> bytes:
        """Get public key in PEM format"""
        public_key = self.device_keypair.public_key()
        return public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
    
    def generate_session_key(self) -> bytes:
        """Generate a random session key"""
        return secrets.token_bytes(32)

class AuthenticationManager:
    """Manages device authentication and authorization"""
    
    def __init__(self, encryption_manager: EncryptionManager, config: Dict):
        self.encryption = encryption_manager
        self.config = config
        self.active_sessions = {}
        self.device_registry = {}
        self.api_keys = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize authentication database
        self._init_auth_database()
    
    def _init_auth_database(self):
        """Initialize authentication database"""
        db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    public_key TEXT NOT NULL,
                    trust_level TEXT DEFAULT 'low',
                    last_seen TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    key_id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL,
                    device_id TEXT,
                    permissions TEXT,
                    expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (device_id) REFERENCES devices (device_id)
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS auth_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    device_id TEXT,
                    event_type TEXT,
                    success BOOLEAN,
                    ip_address TEXT,
                    details TEXT
                )
            ''')
    
    def register_device(self, device_id: str, public_key_pem: bytes, 
                       trust_level: str = SecurityLevel.LOW, 
                       metadata: Dict = None) -> bool:
        """Register a new device"""
        try:
            db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO devices 
                    (device_id, public_key, trust_level, last_seen, metadata)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    device_id,
                    public_key_pem.decode('utf-8'),
                    trust_level,
                    datetime.now().isoformat(),
                    json.dumps(metadata or {})
                ))
            
            self.device_registry[device_id] = {
                "public_key": public_key_pem,
                "trust_level": trust_level,
                "metadata": metadata or {}
            }
            
            self._log_auth_event(device_id, "device_registered", True)
            self.logger.info(f"Device registered: {device_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register device {device_id}: {e}")
            self._log_auth_event(device_id, "device_registration_failed", False)
            return False
    
    def authenticate_device(self, device_id: str, challenge_response: bytes,
                          original_challenge: bytes) -> Optional[str]:
        """Authenticate a device using challenge-response"""
        try:
            # Get device from registry
            device = self._get_device(device_id)
            if not device:
                self._log_auth_event(device_id, "auth_failed_unknown_device", False)
                return None
            
            # Load public key
            public_key = serialization.load_pem_public_key(device["public_key"].encode())
            
            # Verify challenge response
            if not self.encryption.verify_signature(original_challenge, challenge_response, public_key):
                self._log_auth_event(device_id, "auth_failed_invalid_signature", False)
                return None
            
            # Generate session token
            session_token = self._generate_session_token(device_id)
            
            # Store active session
            self.active_sessions[session_token] = {
                "device_id": device_id,
                "created_at": time.time(),
                "trust_level": device["trust_level"],
                "expires_at": time.time() + self.config.get("session_timeout", 3600)
            }
            
            self._log_auth_event(device_id, "auth_success", True)
            self.logger.info(f"Device authenticated: {device_id}")
            return session_token
            
        except Exception as e:
            self.logger.error(f"Authentication failed for {device_id}: {e}")
            self._log_auth_event(device_id, "auth_failed_error", False)
            return None
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate an active session"""
        if session_token not in self.active_sessions:
            return None
        
        session = self.active_sessions[session_token]
        
        # Check if session has expired
        if time.time() > session["expires_at"]:
            del self.active_sessions[session_token]
            return None
        
        return session
    
    def create_api_key(self, device_id: str, permissions: List[str], 
                      expires_days: int = 365) -> Optional[str]:
        """Create an API key for a device"""
        try:
            # Generate API key
            api_key = secrets.token_urlsafe(32)
            key_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            
            expires_at = datetime.now() + timedelta(days=expires_days)
            
            db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO api_keys 
                    (key_id, key_hash, device_id, permissions, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    key_id,
                    key_hash,
                    device_id,
                    json.dumps(permissions),
                    expires_at.isoformat()
                ))
            
            self.api_keys[api_key] = {
                "device_id": device_id,
                "permissions": permissions,
                "expires_at": expires_at
            }
            
            self.logger.info(f"API key created for device: {device_id}")
            return api_key
            
        except Exception as e:
            self.logger.error(f"Failed to create API key for {device_id}: {e}")
            return None
    
    def validate_api_key(self, api_key: str) -> Optional[Dict]:
        """Validate an API key"""
        # Check memory cache first
        if api_key in self.api_keys:
            key_info = self.api_keys[api_key]
            if datetime.now() < key_info["expires_at"]:
                return key_info
            else:
                del self.api_keys[api_key]
        
        # Check database
        try:
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()
            db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT device_id, permissions, expires_at 
                    FROM api_keys 
                    WHERE key_hash = ? AND expires_at > ?
                ''', (key_hash, datetime.now().isoformat()))
                
                row = cursor.fetchone()
                if row:
                    key_info = {
                        "device_id": row[0],
                        "permissions": json.loads(row[1]),
                        "expires_at": datetime.fromisoformat(row[2])
                    }
                    
                    # Cache for next time
                    self.api_keys[api_key] = key_info
                    return key_info
        
        except Exception as e:
            self.logger.error(f"API key validation error: {e}")
        
        return None
    
    def _get_device(self, device_id: str) -> Optional[Dict]:
        """Get device from registry"""
        if device_id in self.device_registry:
            return self.device_registry[device_id]
        
        # Load from database
        try:
            db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute('''
                    SELECT public_key, trust_level, metadata 
                    FROM devices 
                    WHERE device_id = ?
                ''', (device_id,))
                
                row = cursor.fetchone()
                if row:
                    device = {
                        "public_key": row[0],
                        "trust_level": row[1],
                        "metadata": json.loads(row[2] or "{}")
                    }
                    
                    # Cache for next time
                    self.device_registry[device_id] = device
                    return device
        
        except Exception as e:
            self.logger.error(f"Failed to get device {device_id}: {e}")
        
        return None
    
    def _generate_session_token(self, device_id: str) -> str:
        """Generate a secure session token"""
        token_data = f"{device_id}:{time.time()}:{secrets.token_hex(16)}"
        return base64.urlsafe_b64encode(token_data.encode()).decode()
    
    def _log_auth_event(self, device_id: str, event_type: str, success: bool, 
                       ip_address: str = None, details: str = None):
        """Log authentication event"""
        try:
            db_path = self.config.get("auth_db", "/var/lib/activelog/auth.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO auth_logs 
                    (device_id, event_type, success, ip_address, details)
                    VALUES (?, ?, ?, ?, ?)
                ''', (device_id, event_type, success, ip_address, details))
        
        except Exception as e:
            self.logger.error(f"Failed to log auth event: {e}")

class NetworkSecurity:
    """Network security and firewall management"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.trusted_networks = set()
        self.blocked_ips = set()
        self.rate_limits = {}
        self.logger = logging.getLogger(__name__)
        
        self._load_network_config()
    
    def _load_network_config(self):
        """Load network security configuration"""
        network_config = self.config.get("network", {})
        
        # Load trusted networks
        for network in network_config.get("trusted_networks", []):
            try:
                self.trusted_networks.add(ipaddress.ip_network(network, strict=False))
            except ValueError as e:
                self.logger.error(f"Invalid network: {network} - {e}")
        
        # Load blocked IPs
        for ip in network_config.get("blocked_ips", []):
            try:
                self.blocked_ips.add(ipaddress.ip_address(ip))
            except ValueError as e:
                self.logger.error(f"Invalid IP: {ip} - {e}")
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP address is allowed"""
        try:
            ip = ipaddress.ip_address(ip_address)
            
            # Check if blocked
            if ip in self.blocked_ips:
                return False
            
            # Check if in trusted network
            for network in self.trusted_networks:
                if ip in network:
                    return True
            
            # If no trusted networks defined, allow by default
            if not self.trusted_networks:
                return True
            
            return False
            
        except ValueError:
            self.logger.warning(f"Invalid IP address: {ip_address}")
            return False
    
    def check_rate_limit(self, ip_address: str, endpoint: str = "default") -> bool:
        """Check rate limiting for IP address"""
        key = f"{ip_address}:{endpoint}"
        current_time = time.time()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = []
        
        # Clean old entries
        window = self.config.get("rate_limit_window", 60)  # 1 minute window
        self.rate_limits[key] = [
            timestamp for timestamp in self.rate_limits[key]
            if current_time - timestamp < window
        ]
        
        # Check limit
        limit = self.config.get("rate_limit", 100)  # 100 requests per minute
        if len(self.rate_limits[key]) >= limit:
            return False
        
        # Add current request
        self.rate_limits[key].append(current_time)
        return True
    
    def block_ip(self, ip_address: str, duration_seconds: int = 3600):
        """Block an IP address temporarily"""
        try:
            ip = ipaddress.ip_address(ip_address)
            self.blocked_ips.add(ip)
            
            self.logger.warning(f"Blocked IP: {ip_address} for {duration_seconds}s")
            
            # Schedule unblock
            if duration_seconds > 0:
                asyncio.create_task(self._unblock_ip_after_delay(ip, duration_seconds))
                
        except ValueError:
            self.logger.error(f"Invalid IP address to block: {ip_address}")
    
    async def _unblock_ip_after_delay(self, ip: ipaddress.IPv4Address, delay: int):
        """Unblock IP address after delay"""
        await asyncio.sleep(delay)
        if ip in self.blocked_ips:
            self.blocked_ips.remove(ip)
            self.logger.info(f"Unblocked IP: {ip}")

class SecurityMonitor:
    """Security monitoring and intrusion detection"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.security_events = []
        self.threat_score = 0.0
        self.logger = logging.getLogger(__name__)
        
        # Initialize monitoring database
        self._init_monitoring_database()
    
    def _init_monitoring_database(self):
        """Initialize security monitoring database"""
        db_path = self.config.get("monitoring_db", "/var/lib/activelog/security.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS security_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source_ip TEXT,
                    target TEXT,
                    details TEXT,
                    threat_score REAL DEFAULT 0.0
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS intrusion_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_ip TEXT NOT NULL,
                    attempt_type TEXT NOT NULL,
                    blocked BOOLEAN DEFAULT FALSE,
                    details TEXT
                )
            ''')
    
    def log_security_event(self, event_type: str, severity: str,
                          source_ip: str = None, target: str = None,
                          details: Dict = None, threat_score: float = 0.0):
        """Log a security event"""
        try:
            event = {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "severity": severity,
                "source_ip": source_ip,
                "target": target,
                "details": json.dumps(details or {}),
                "threat_score": threat_score
            }
            
            # Store in memory for recent access
            self.security_events.append(event)
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-500:]  # Keep last 500
            
            # Store in database
            db_path = self.config.get("monitoring_db", "/var/lib/activelog/security.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO security_events 
                    (event_type, severity, source_ip, target, details, threat_score)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (event_type, severity, source_ip, target, event["details"], threat_score))
            
            # Update threat score
            self._update_threat_score(threat_score)
            
            self.logger.info(f"Security event: {event_type} (severity: {severity})")
            
            # Alert on high severity events
            if severity in ["HIGH", "CRITICAL"]:
                self._trigger_security_alert(event)
                
        except Exception as e:
            self.logger.error(f"Failed to log security event: {e}")
    
    def detect_intrusion_attempt(self, source_ip: str, attempt_type: str,
                               details: Dict = None) -> bool:
        """Detect and log intrusion attempt"""
        try:
            # Calculate threat score based on attempt type
            threat_scores = {
                "brute_force": 0.8,
                "port_scan": 0.6,
                "malformed_request": 0.4,
                "unauthorized_access": 0.9,
                "suspicious_activity": 0.5
            }
            
            threat_score = threat_scores.get(attempt_type, 0.3)
            
            # Log the attempt
            db_path = self.config.get("monitoring_db", "/var/lib/activelog/security.db")
            
            with sqlite3.connect(db_path) as conn:
                conn.execute('''
                    INSERT INTO intrusion_attempts 
                    (source_ip, attempt_type, blocked, details)
                    VALUES (?, ?, ?, ?)
                ''', (source_ip, attempt_type, True, json.dumps(details or {})))
            
            # Log as security event
            self.log_security_event(
                event_type=f"intrusion_attempt_{attempt_type}",
                severity="HIGH" if threat_score > 0.7 else "MEDIUM",
                source_ip=source_ip,
                details=details,
                threat_score=threat_score
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to detect intrusion attempt: {e}")
            return False
    
    def _update_threat_score(self, new_score: float):
        """Update overall threat score"""
        # Use exponential moving average
        alpha = 0.1
        self.threat_score = alpha * new_score + (1 - alpha) * self.threat_score
        
        # Cap at 1.0
        self.threat_score = min(1.0, self.threat_score)
    
    def _trigger_security_alert(self, event: Dict):
        """Trigger security alert for high-priority events"""
        alert_config = self.config.get("alerts", {})
        
        if alert_config.get("email_enabled"):
            asyncio.create_task(self._send_email_alert(event))
        
        if alert_config.get("webhook_enabled"):
            asyncio.create_task(self._send_webhook_alert(event))
    
    async def _send_email_alert(self, event: Dict):
        """Send email security alert"""
        # Implementation would depend on email service
        self.logger.info(f"Email alert triggered for: {event['event_type']}")
    
    async def _send_webhook_alert(self, event: Dict):
        """Send webhook security alert"""
        # Implementation would make HTTP request to webhook URL
        self.logger.info(f"Webhook alert triggered for: {event['event_type']}")
    
    def get_threat_assessment(self) -> Dict:
        """Get current threat assessment"""
        return {
            "threat_score": self.threat_score,
            "threat_level": self._get_threat_level(self.threat_score),
            "recent_events": len(self.security_events),
            "last_24h_events": self._count_recent_events(24),
            "last_hour_events": self._count_recent_events(1)
        }
    
    def _get_threat_level(self, score: float) -> str:
        """Convert threat score to level"""
        if score < 0.2:
            return "LOW"
        elif score < 0.5:
            return "MEDIUM"
        elif score < 0.8:
            return "HIGH"
        else:
            return "CRITICAL"
    
    def _count_recent_events(self, hours: int) -> int:
        """Count security events in recent hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        count = 0
        for event in self.security_events:
            event_time = datetime.fromisoformat(event["timestamp"])
            if event_time > cutoff_time:
                count += 1
        
        return count

class EdgeSecurityManager:
    """Main edge security manager"""
    
    def __init__(self, config_path: str = "/etc/activelog/security.conf"):
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        
        # Initialize logging
        self.logger = self._setup_logging()
        
        # Initialize security components
        self.encryption = EncryptionManager(self.config.get("encryption", {}))
        self.auth = AuthenticationManager(self.encryption, self.config.get("auth", {}))
        self.network = NetworkSecurity(self.config.get("network", {}))
        self.monitor = SecurityMonitor(self.config.get("monitoring", {}))
        
        self.logger.info("Edge Security Manager initialized")
    
    def _load_config(self) -> Dict:
        """Load security configuration"""
        default_config = {
            "encryption": {
                "security_dir": "/etc/activelog/security",
                "algorithm": "AES-256-GCM"
            },
            "auth": {
                "auth_db": "/var/lib/activelog/auth.db",
                "session_timeout": 3600,
                "max_failed_attempts": 5,
                "lockout_duration": 1800
            },
            "network": {
                "trusted_networks": ["192.168.0.0/16", "10.0.0.0/8"],
                "blocked_ips": [],
                "rate_limit": 100,
                "rate_limit_window": 60
            },
            "monitoring": {
                "monitoring_db": "/var/lib/activelog/security.db",
                "log_retention_days": 90,
                "threat_threshold": 0.7
            },
            "alerts": {
                "email_enabled": False,
                "webhook_enabled": False,
                "email_recipients": [],
                "webhook_url": ""
            }
        }
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    loaded_config = json.load(f)
                    self._merge_config(default_config, loaded_config)
        except Exception as e:
            print(f"Error loading security config: {e}")
        
        return default_config
    
    def _merge_config(self, default: Dict, loaded: Dict):
        """Recursively merge configurations"""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def _setup_logging(self):
        """Setup security logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler("/var/log/activelog/security.log"),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)
    
    async def start(self):
        """Start security manager"""
        self.running = True
        self.logger.info("Starting Edge Security Manager")
        
        # Start background security monitoring
        tasks = [
            asyncio.create_task(self._security_monitoring_loop()),
            asyncio.create_task(self._cleanup_loop())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop security manager"""
        self.running = False
        self.logger.info("Edge Security Manager stopped")
    
    async def _security_monitoring_loop(self):
        """Background security monitoring"""
        while self.running:
            try:
                # Check system security status
                await self._check_system_security()
                
                # Monitor threat level
                threat_assessment = self.monitor.get_threat_assessment()
                
                if threat_assessment["threat_level"] in ["HIGH", "CRITICAL"]:
                    self.logger.warning(f"Elevated threat level: {threat_assessment['threat_level']}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Security monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _check_system_security(self):
        """Check overall system security"""
        # Check for suspicious processes
        await self._check_processes()
        
        # Check file system integrity
        await self._check_file_integrity()
        
        # Check network connections
        await self._check_network_connections()
    
    async def _check_processes(self):
        """Check for suspicious processes"""
        try:
            # Get list of running processes
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                suspicious_processes = []
                
                for line in result.stdout.split('\n')[1:]:  # Skip header
                    if not line.strip():
                        continue
                    
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        command = parts[10]
                        
                        # Check for suspicious patterns
                        if any(pattern in command.lower() for pattern in 
                              ['nc -l', 'ncat -l', 'python -c', 'bash -c', 'sh -c']):
                            suspicious_processes.append(command)
                
                if suspicious_processes:
                    self.monitor.log_security_event(
                        event_type="suspicious_processes",
                        severity="MEDIUM",
                        details={"processes": suspicious_processes},
                        threat_score=0.5
                    )
        
        except Exception as e:
            self.logger.debug(f"Process check error: {e}")
    
    async def _check_file_integrity(self):
        """Check critical file integrity"""
        critical_files = [
            "/etc/passwd",
            "/etc/shadow",
            "/etc/sudoers",
            "/etc/activelog/security/device.key"
        ]
        
        for file_path in critical_files:
            try:
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    
                    # Check permissions
                    if file_path.endswith(('.key', 'shadow')) and stat.st_mode & 0o077:
                        self.monitor.log_security_event(
                            event_type="insecure_file_permissions",
                            severity="HIGH",
                            target=file_path,
                            details={"permissions": oct(stat.st_mode)},
                            threat_score=0.7
                        )
            
            except Exception as e:
                self.logger.debug(f"File integrity check error for {file_path}: {e}")
    
    async def _check_network_connections(self):
        """Check for suspicious network connections"""
        try:
            # Get network connections
            connections = psutil.net_connections(kind='inet')
            
            suspicious_connections = []
            
            for conn in connections:
                if conn.status == 'ESTABLISHED' and conn.raddr:
                    remote_ip = conn.raddr.ip
                    
                    # Check if remote IP is suspicious
                    if not self.network.is_ip_allowed(remote_ip):
                        suspicious_connections.append({
                            "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "remote": f"{remote_ip}:{conn.raddr.port}",
                            "pid": conn.pid
                        })
            
            if suspicious_connections:
                self.monitor.log_security_event(
                    event_type="suspicious_connections",
                    severity="MEDIUM",
                    details={"connections": suspicious_connections},
                    threat_score=0.6
                )
        
        except Exception as e:
            self.logger.debug(f"Network connections check error: {e}")
    
    async def _cleanup_loop(self):
        """Cleanup old data periodically"""
        while self.running:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Cleanup old security events
                retention_days = self.config["monitoring"]["log_retention_days"]
                cutoff_date = datetime.now() - timedelta(days=retention_days)
                
                for db_path in [
                    self.config["auth"]["auth_db"],
                    self.config["monitoring"]["monitoring_db"]
                ]:
                    if os.path.exists(db_path):
                        with sqlite3.connect(db_path) as conn:
                            conn.execute('''
                                DELETE FROM security_events 
                                WHERE timestamp < ?
                            ''', (cutoff_date.isoformat(),))
                            
                            conn.execute('''
                                DELETE FROM auth_logs 
                                WHERE timestamp < ?
                            ''', (cutoff_date.isoformat(),))
                
                self.logger.info("Completed security data cleanup")
                
            except Exception as e:
                self.logger.error(f"Cleanup error: {e}")
    
    # Public API methods
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data"""
        return self.encryption.encrypt_data(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data"""
        return self.encryption.decrypt_data(encrypted_data)
    
    def register_device(self, device_id: str, public_key_pem: bytes) -> bool:
        """Register a new device"""
        return self.auth.register_device(device_id, public_key_pem)
    
    def authenticate_device(self, device_id: str, challenge_response: bytes,
                          original_challenge: bytes) -> Optional[str]:
        """Authenticate a device"""
        return self.auth.authenticate_device(device_id, challenge_response, original_challenge)
    
    def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate a session"""
        return self.auth.validate_session(session_token)
    
    def is_ip_allowed(self, ip_address: str) -> bool:
        """Check if IP is allowed"""
        return self.network.is_ip_allowed(ip_address)
    
    def log_security_event(self, event_type: str, severity: str, **kwargs):
        """Log a security event"""
        self.monitor.log_security_event(event_type, severity, **kwargs)
    
    def get_security_status(self) -> Dict:
        """Get overall security status"""
        threat_assessment = self.monitor.get_threat_assessment()
        
        return {
            "security_level": self._calculate_security_level(),
            "threat_assessment": threat_assessment,
            "active_sessions": len(self.auth.active_sessions),
            "registered_devices": len(self.auth.device_registry),
            "blocked_ips": len(self.network.blocked_ips)
        }
    
    def _calculate_security_level(self) -> str:
        """Calculate overall security level"""
        threat_score = self.monitor.threat_score
        
        if threat_score < 0.3:
            return "SECURE"
        elif threat_score < 0.6:
            return "ELEVATED"
        elif threat_score < 0.8:
            return "HIGH_RISK"
        else:
            return "CRITICAL"

async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ActiveLog Edge Security Manager")
    parser.add_argument("--config", default="/etc/activelog/security.conf",
                        help="Configuration file path")
    
    args = parser.parse_args()
    
    security_manager = EdgeSecurityManager(args.config)
    
    try:
        await security_manager.start()
    except KeyboardInterrupt:
        print("Security manager stopped")

if __name__ == "__main__":
    asyncio.run(main())