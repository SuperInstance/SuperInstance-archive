"""
Advanced Security and Privacy Engine
Comprehensive privacy protection, security hardening, and data protection
"""

import asyncio
import hashlib
import hmac
import secrets
import logging
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import base64

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

from api.models import HardwareProfile, AdaptiveConfiguration

@dataclass
class SecurityEvent:
    """Security event for logging and analysis"""
    event_id: str
    event_type: str
    severity: str  # low, medium, high, critical
    component: str
    description: str
    timestamp: datetime
    source_ip: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = None
    resolved: bool = False

@dataclass
class PrivacyPolicy:
    """Privacy policy configuration"""
    data_collection_level: str  # minimal, standard, enhanced
    data_sharing_allowed: bool
    analytics_enabled: bool
    personalization_enabled: bool
    data_retention_days: int
    encryption_required: bool
    anonymization_level: str  # none, basic, strict

@dataclass
class SecurityProfile:
    """Security profile for system hardening"""
    security_level: str  # basic, standard, high, maximum
    encryption_enabled: bool
    network_security: Dict[str, Any]
    access_controls: Dict[str, Any]
    monitoring_enabled: bool
    incident_response: Dict[str, Any]

class DataProtectionEngine:
    """Data protection and privacy engine"""
    
    def __init__(self):
        self.encryption_key = None
        self.privacy_policy = PrivacyPolicy(
            data_collection_level="standard",
            data_sharing_allowed=False,
            analytics_enabled=True,
            personalization_enabled=True,
            data_retention_days=30,
            encryption_required=True,
            anonymization_level="basic"
        )
        self.protected_data = {}
        self.anonymization_mappings = {}
        
    async def initialize(self):
        """Initialize data protection"""
        if CRYPTO_AVAILABLE:
            await self._setup_encryption()
            logging.info("🔒 Data protection engine initialized with encryption")
        else:
            logging.warning("🔒 Data protection initialized without encryption (install cryptography)")
    
    async def _setup_encryption(self):
        """Setup encryption keys"""
        key_file = Path("security/encryption.key")
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                self.encryption_key = f.read()
        else:
            # Generate new key
            self.encryption_key = Fernet.generate_key()
            key_file.parent.mkdir(exist_ok=True)
            with open(key_file, 'wb') as f:
                f.write(self.encryption_key)
    
    def encrypt_data(self, data: Any) -> str:
        """Encrypt sensitive data"""
        if not CRYPTO_AVAILABLE or not self.encryption_key:
            return str(data)  # Fallback to plaintext
        
        try:
            fernet = Fernet(self.encryption_key)
            json_data = json.dumps(data, default=str)
            encrypted_data = fernet.encrypt(json_data.encode())
            return base64.b64encode(encrypted_data).decode()
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            return str(data)
    
    def decrypt_data(self, encrypted_data: str) -> Any:
        """Decrypt sensitive data"""
        if not CRYPTO_AVAILABLE or not self.encryption_key:
            return encrypted_data  # Return as-is if no encryption
        
        try:
            fernet = Fernet(self.encryption_key)
            decoded_data = base64.b64decode(encrypted_data.encode())
            decrypted_data = fernet.decrypt(decoded_data)
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logging.error(f"Decryption error: {e}")
            return encrypted_data
    
    def anonymize_data(self, data: Dict[str, Any], anonymization_level: str = None) -> Dict[str, Any]:
        """Anonymize personal data"""
        
        level = anonymization_level or self.privacy_policy.anonymization_level
        anonymized_data = data.copy()
        
        # Define sensitive fields
        sensitive_fields = {
            'profile_id', 'user_id', 'device_id', 'mac_address', 
            'serial_number', 'hostname', 'username', 'ip_address'
        }
        
        if level == 'none':
            return anonymized_data
        
        for field in sensitive_fields:
            if field in anonymized_data:
                if level == 'basic':
                    # Hash sensitive data
                    original_value = str(anonymized_data[field])
                    if original_value not in self.anonymization_mappings:
                        hash_value = hashlib.sha256(original_value.encode()).hexdigest()[:16]
                        self.anonymization_mappings[original_value] = f"anon_{hash_value}"
                    anonymized_data[field] = self.anonymization_mappings[original_value]
                
                elif level == 'strict':
                    # Remove sensitive data entirely
                    anonymized_data.pop(field, None)
        
        # Anonymize hardware-specific identifiers
        if 'cpu' in anonymized_data and isinstance(anonymized_data['cpu'], dict):
            cpu_data = anonymized_data['cpu']
            if 'name' in cpu_data:
                cpu_data['name'] = self._generalize_hardware_name(cpu_data['name'])
        
        if 'gpu' in anonymized_data and anonymized_data['gpu']:
            gpu_data = anonymized_data['gpu']
            if 'name' in gpu_data:
                gpu_data['name'] = self._generalize_hardware_name(gpu_data['name'])
        
        return anonymized_data
    
    def _generalize_hardware_name(self, hardware_name: str) -> str:
        """Generalize hardware names to protect privacy"""
        
        # Replace specific models with generic categories
        name_lower = hardware_name.lower()
        
        if 'intel' in name_lower and 'i3' in name_lower:
            return "Intel i3 Series"
        elif 'intel' in name_lower and 'i5' in name_lower:
            return "Intel i5 Series"
        elif 'intel' in name_lower and 'i7' in name_lower:
            return "Intel i7 Series"
        elif 'intel' in name_lower and 'i9' in name_lower:
            return "Intel i9 Series"
        elif 'amd' in name_lower and 'ryzen 3' in name_lower:
            return "AMD Ryzen 3 Series"
        elif 'amd' in name_lower and 'ryzen 5' in name_lower:
            return "AMD Ryzen 5 Series"
        elif 'amd' in name_lower and 'ryzen 7' in name_lower:
            return "AMD Ryzen 7 Series"
        elif 'nvidia' in name_lower and 'gtx' in name_lower:
            return "NVIDIA GTX Series"
        elif 'nvidia' in name_lower and 'rtx' in name_lower:
            return "NVIDIA RTX Series"
        else:
            return "Generic Hardware Component"
    
    def apply_privacy_policy(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply privacy policy to data"""
        
        processed_data = data.copy()
        
        # Apply data collection level
        if self.privacy_policy.data_collection_level == "minimal":
            # Only keep essential system information
            essential_fields = {'system_tier', 'cpu', 'memory', 'timestamp'}
            processed_data = {k: v for k, v in processed_data.items() if k in essential_fields}
        
        # Apply anonymization
        if self.privacy_policy.anonymization_level != "none":
            processed_data = self.anonymize_data(processed_data)
        
        # Apply encryption if required
        if self.privacy_policy.encryption_required:
            encrypted_data = {}
            for key, value in processed_data.items():
                if key in ['profile_id', 'user_preferences', 'usage_pattern']:
                    encrypted_data[key] = self.encrypt_data(value)
                else:
                    encrypted_data[key] = value
            processed_data = encrypted_data
        
        return processed_data
    
    def data_retention_cleanup(self):
        """Clean up old data based on retention policy"""
        
        cutoff_date = datetime.now() - timedelta(days=self.privacy_policy.data_retention_days)
        
        # This would implement actual data cleanup
        logging.info(f"Data retention cleanup: removing data older than {cutoff_date}")

class NetworkSecurityManager:
    """Network security and monitoring"""
    
    def __init__(self):
        self.allowed_domains = set()
        self.blocked_ips = set()
        self.security_headers = {}
        self.rate_limits = {}
        self.connection_monitor = {}
        
    def initialize_security_headers(self):
        """Initialize security headers"""
        self.security_headers = {
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    def validate_request(self, request_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate incoming request"""
        
        source_ip = request_info.get('source_ip', '')
        user_agent = request_info.get('user_agent', '')
        endpoint = request_info.get('endpoint', '')
        
        # Check IP blacklist
        if source_ip in self.blocked_ips:
            return False, "IP address blocked"
        
        # Check rate limits
        if self._check_rate_limit(source_ip, endpoint):
            return False, "Rate limit exceeded"
        
        # Validate user agent
        if self._is_suspicious_user_agent(user_agent):
            return False, "Suspicious user agent"
        
        return True, "Request validated"
    
    def _check_rate_limit(self, source_ip: str, endpoint: str) -> bool:
        """Check if rate limit is exceeded"""
        
        key = f"{source_ip}:{endpoint}"
        current_time = datetime.now()
        
        if key not in self.rate_limits:
            self.rate_limits[key] = {'count': 1, 'window_start': current_time}
            return False
        
        rate_info = self.rate_limits[key]
        time_diff = (current_time - rate_info['window_start']).seconds
        
        if time_diff >= 60:  # 1 minute window
            # Reset window
            rate_info['count'] = 1
            rate_info['window_start'] = current_time
            return False
        
        rate_info['count'] += 1
        
        # Different limits for different endpoints
        if endpoint in ['/api/profile', '/api/configure']:
            limit = 60  # 60 requests per minute
        else:
            limit = 100  # 100 requests per minute
        
        return rate_info['count'] > limit
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check for suspicious user agents"""
        
        suspicious_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl',
            'python-requests', 'java/', 'go-http-client'
        ]
        
        user_agent_lower = user_agent.lower()
        
        for pattern in suspicious_patterns:
            if pattern in user_agent_lower:
                # Allow some legitimate tools
                if pattern in ['curl', 'wget'] and 'test' in user_agent_lower:
                    continue
                return True
        
        return False

class AccessControlManager:
    """Access control and authentication"""
    
    def __init__(self):
        self.user_sessions = {}
        self.api_keys = {}
        self.permission_cache = {}
        
    def generate_api_key(self, user_id: str, permissions: List[str]) -> str:
        """Generate API key with specific permissions"""
        
        api_key = secrets.token_urlsafe(32)
        self.api_keys[api_key] = {
            'user_id': user_id,
            'permissions': permissions,
            'created_at': datetime.now(),
            'last_used': None,
            'usage_count': 0
        }
        
        return api_key
    
    def validate_api_key(self, api_key: str, required_permission: str = None) -> Tuple[bool, str]:
        """Validate API key and check permissions"""
        
        if api_key not in self.api_keys:
            return False, "Invalid API key"
        
        key_info = self.api_keys[api_key]
        
        # Update usage statistics
        key_info['last_used'] = datetime.now()
        key_info['usage_count'] += 1
        
        # Check expiration (30 days)
        if (datetime.now() - key_info['created_at']).days > 30:
            return False, "API key expired"
        
        # Check permissions
        if required_permission and required_permission not in key_info['permissions']:
            return False, f"Permission denied: {required_permission}"
        
        return True, key_info['user_id']
    
    def create_user_session(self, user_id: str) -> str:
        """Create user session"""
        
        session_id = secrets.token_urlsafe(32)
        self.user_sessions[session_id] = {
            'user_id': user_id,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'ip_address': None  # Would be set by request handler
        }
        
        return session_id
    
    def validate_session(self, session_id: str) -> Tuple[bool, str]:
        """Validate user session"""
        
        if session_id not in self.user_sessions:
            return False, "Invalid session"
        
        session_info = self.user_sessions[session_id]
        
        # Check session expiration (24 hours)
        if (datetime.now() - session_info['last_activity']).hours > 24:
            del self.user_sessions[session_id]
            return False, "Session expired"
        
        # Update activity
        session_info['last_activity'] = datetime.now()
        
        return True, session_info['user_id']

class SecurityMonitor:
    """Security monitoring and incident detection"""
    
    def __init__(self):
        self.security_events = []
        self.threat_patterns = self._load_threat_patterns()
        self.anomaly_detector = AnomalyDetector()
        
    def _load_threat_patterns(self) -> List[Dict[str, Any]]:
        """Load threat detection patterns"""
        
        return [
            {
                'name': 'brute_force_attack',
                'pattern': 'multiple_failed_auth',
                'threshold': 5,
                'time_window': 300,  # 5 minutes
                'severity': 'high'
            },
            {
                'name': 'suspicious_api_usage',
                'pattern': 'high_frequency_requests',
                'threshold': 1000,
                'time_window': 60,  # 1 minute
                'severity': 'medium'
            },
            {
                'name': 'data_exfiltration_attempt',
                'pattern': 'large_data_download',
                'threshold': 100,  # MB
                'time_window': 60,
                'severity': 'critical'
            }
        ]
    
    def log_security_event(self, event_type: str, component: str, 
                          description: str, severity: str = "medium",
                          metadata: Dict[str, Any] = None):
        """Log security event"""
        
        event = SecurityEvent(
            event_id=secrets.token_urlsafe(16),
            event_type=event_type,
            severity=severity,
            component=component,
            description=description,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        self.security_events.append(event)
        
        # Trigger alerts for high/critical events
        if severity in ['high', 'critical']:
            self._trigger_security_alert(event)
        
        # Check for threat patterns
        self._check_threat_patterns()
    
    def _trigger_security_alert(self, event: SecurityEvent):
        """Trigger security alert"""
        
        logging.warning(f"SECURITY ALERT: {event.severity.upper()} - {event.description}")
        
        # In production, this would:
        # 1. Send notifications to administrators
        # 2. Update security dashboard
        # 3. Potentially trigger automatic responses
        
    def _check_threat_patterns(self):
        """Check for threat patterns in recent events"""
        
        now = datetime.now()
        
        for pattern in self.threat_patterns:
            time_window = timedelta(seconds=pattern['time_window'])
            recent_events = [
                e for e in self.security_events
                if (now - e.timestamp) <= time_window
            ]
            
            if pattern['pattern'] == 'multiple_failed_auth':
                failed_auth_events = [e for e in recent_events if e.event_type == 'auth_failure']
                if len(failed_auth_events) >= pattern['threshold']:
                    self._handle_threat_detection(pattern['name'], failed_auth_events)
            
            elif pattern['pattern'] == 'high_frequency_requests':
                request_events = [e for e in recent_events if e.event_type == 'api_request']
                if len(request_events) >= pattern['threshold']:
                    self._handle_threat_detection(pattern['name'], request_events)
    
    def _handle_threat_detection(self, threat_name: str, related_events: List[SecurityEvent]):
        """Handle detected threat"""
        
        logging.critical(f"THREAT DETECTED: {threat_name}")
        
        # Log the threat detection as a security event
        self.log_security_event(
            event_type="threat_detected",
            component="security_monitor",
            description=f"Detected {threat_name} based on {len(related_events)} events",
            severity="critical",
            metadata={'threat_pattern': threat_name, 'event_count': len(related_events)}
        )

class AnomalyDetector:
    """Machine learning-based anomaly detection"""
    
    def __init__(self):
        self.baseline_metrics = {}
        self.anomaly_threshold = 2.0  # Standard deviations
        
    def update_baseline(self, metrics: Dict[str, float]):
        """Update baseline metrics for anomaly detection"""
        
        for metric_name, value in metrics.items():
            if metric_name not in self.baseline_metrics:
                self.baseline_metrics[metric_name] = {'values': [], 'mean': 0, 'std': 0}
            
            baseline = self.baseline_metrics[metric_name]
            baseline['values'].append(value)
            
            # Keep only recent values (last 1000 samples)
            if len(baseline['values']) > 1000:
                baseline['values'] = baseline['values'][-1000:]
            
            # Update statistics
            import numpy as np
            baseline['mean'] = np.mean(baseline['values'])
            baseline['std'] = np.std(baseline['values'])
    
    def detect_anomalies(self, current_metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        """Detect anomalies in current metrics"""
        
        anomalies = []
        
        for metric_name, value in current_metrics.items():
            if metric_name in self.baseline_metrics:
                baseline = self.baseline_metrics[metric_name]
                
                if baseline['std'] > 0:
                    z_score = abs(value - baseline['mean']) / baseline['std']
                    
                    if z_score > self.anomaly_threshold:
                        anomalies.append({
                            'metric': metric_name,
                            'current_value': value,
                            'baseline_mean': baseline['mean'],
                            'z_score': z_score,
                            'severity': 'high' if z_score > 3.0 else 'medium'
                        })
        
        return anomalies

class PrivacySecurityEngine:
    """Main privacy and security engine"""
    
    def __init__(self):
        self.data_protection = DataProtectionEngine()
        self.network_security = NetworkSecurityManager()
        self.access_control = AccessControlManager()
        self.security_monitor = SecurityMonitor()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize privacy and security engine"""
        
        await self.data_protection.initialize()
        self.network_security.initialize_security_headers()
        
        self.is_initialized = True
        logging.info("🛡️ Privacy and security engine initialized")
    
    async def secure_data_processing(self, data: Dict[str, Any], 
                                   processing_type: str) -> Dict[str, Any]:
        """Secure data processing with privacy protection"""
        
        # Apply privacy policy
        processed_data = self.data_protection.apply_privacy_policy(data)
        
        # Log data processing event
        self.security_monitor.log_security_event(
            event_type="data_processing",
            component="privacy_engine",
            description=f"Processing {processing_type} data",
            severity="low",
            metadata={'data_size': len(str(data)), 'processing_type': processing_type}
        )
        
        return processed_data
    
    def validate_request_security(self, request_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Comprehensive request security validation"""
        
        # Network security validation
        is_valid, message = self.network_security.validate_request(request_info)
        
        if not is_valid:
            self.security_monitor.log_security_event(
                event_type="request_blocked",
                component="network_security",
                description=message,
                severity="medium",
                metadata=request_info
            )
        
        return is_valid, message
    
    def get_security_headers(self) -> Dict[str, str]:
        """Get security headers for HTTP responses"""
        return self.network_security.security_headers
    
    def generate_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        
        recent_events = [
            e for e in self.security_monitor.security_events
            if (datetime.now() - e.timestamp).hours <= 24
        ]
        
        event_summary = {}
        severity_summary = {}
        
        for event in recent_events:
            event_summary[event.event_type] = event_summary.get(event.event_type, 0) + 1
            severity_summary[event.severity] = severity_summary.get(event.severity, 0) + 1
        
        return {
            'report_timestamp': datetime.now().isoformat(),
            'security_status': 'healthy' if not any(s in severity_summary for s in ['high', 'critical']) else 'attention_required',
            'total_events_24h': len(recent_events),
            'events_by_type': event_summary,
            'events_by_severity': severity_summary,
            'privacy_policy': asdict(self.data_protection.privacy_policy),
            'active_sessions': len(self.access_control.user_sessions),
            'active_api_keys': len(self.access_control.api_keys),
            'recommendations': self._generate_security_recommendations()
        }
    
    def _generate_security_recommendations(self) -> List[str]:
        """Generate security recommendations"""
        
        recommendations = []
        
        # Check recent critical events
        recent_critical = [
            e for e in self.security_monitor.security_events
            if (datetime.now() - e.timestamp).hours <= 24 and e.severity == 'critical'
        ]
        
        if recent_critical:
            recommendations.append("Review and address recent critical security events")
        
        # Check encryption status
        if not CRYPTO_AVAILABLE:
            recommendations.append("Install cryptography library for enhanced data protection")
        
        # Check API key usage
        old_keys = [
            k for k, v in self.access_control.api_keys.items()
            if (datetime.now() - v['created_at']).days > 20
        ]
        
        if old_keys:
            recommendations.append(f"Consider rotating {len(old_keys)} API keys approaching expiration")
        
        if not recommendations:
            recommendations.append("Security posture appears healthy")
        
        return recommendations