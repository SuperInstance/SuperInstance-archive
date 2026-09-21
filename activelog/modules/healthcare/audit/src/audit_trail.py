"""
Healthcare Audit Trail System
Comprehensive audit logging for HIPAA compliance and security monitoring.
"""
import datetime
import json
import hashlib
import logging
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from pathlib import Path


class AuditEventType(Enum):
    """Types of auditable events"""
    DATA_ACCESS = "data_access"
    DATA_CREATE = "data_create"
    DATA_UPDATE = "data_update"
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    CONSENT_CREATE = "consent_create"
    CONSENT_UPDATE = "consent_update"
    CONSENT_WITHDRAW = "consent_withdraw"
    PHI_DISCLOSURE = "phi_disclosure"
    SYSTEM_ACCESS = "system_access"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    ENCRYPTION_KEY_ACCESS = "encryption_key_access"
    SECURITY_INCIDENT = "security_incident"
    COMPLIANCE_CHECK = "compliance_check"


class AuditSeverity(Enum):
    """Audit event severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AuditOutcome(Enum):
    """Outcome of audited action"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"


@dataclass
class AuditableResource:
    """Resource being audited"""
    resource_type: str
    resource_id: str
    patient_id: Optional[str] = None
    sensitive_data_categories: Optional[List[str]] = None


@dataclass
class AuditUser:
    """User performing the audited action"""
    user_id: str
    user_type: str  # patient, provider, admin, system
    user_name: Optional[str] = None
    roles: Optional[List[str]] = None
    organization: Optional[str] = None


@dataclass
class AuditEvent:
    """Complete audit event record"""
    id: str
    timestamp: datetime.datetime
    event_type: AuditEventType
    severity: AuditSeverity
    outcome: AuditOutcome
    user: AuditUser
    resource: Optional[AuditableResource] = None
    action_description: Optional[str] = None
    source_system: Optional[str] = None
    destination_system: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None
    compliance_tags: Optional[List[str]] = None
    retention_until: Optional[datetime.datetime] = None


class AuditEncryption:
    """Encryption utilities for audit logs"""
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        try:
            from cryptography.fernet import Fernet
            self.encryption_key = encryption_key or Fernet.generate_key()
            self.cipher = Fernet(self.encryption_key)
        except ImportError:
            logging.warning("Cryptography library not available. Audit logs will not be encrypted.")
            self.cipher = None
    
    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data in audit logs"""
        if not self.cipher:
            return data
        
        try:
            return self.cipher.encrypt(data.encode()).decode()
        except Exception as e:
            logging.error(f"Failed to encrypt audit data: {e}")
            return data
    
    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data from audit logs"""
        if not self.cipher:
            return encrypted_data
        
        try:
            return self.cipher.decrypt(encrypted_data.encode()).decode()
        except Exception as e:
            logging.error(f"Failed to decrypt audit data: {e}")
            return encrypted_data
    
    def hash_identifier(self, identifier: str, salt: str = None) -> str:
        """Create secure hash of identifier"""
        if salt is None:
            salt = "audit_salt_2024"
        return hashlib.sha256(f"{identifier}{salt}".encode()).hexdigest()[:16]


class AuditStorage:
    """Storage backend for audit logs"""
    
    def __init__(self, storage_path: str = "audit_logs"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.current_file = None
        self.file_lock = threading.Lock()
        self.max_file_size = 100 * 1024 * 1024  # 100MB
    
    def store_event(self, event: AuditEvent) -> bool:
        """Store audit event to persistent storage"""
        try:
            with self.file_lock:
                # Create daily log file
                date_str = event.timestamp.strftime("%Y-%m-%d")
                log_file = self.storage_path / f"audit_{date_str}.jsonl"
                
                # Check file size and rotate if necessary
                if log_file.exists() and log_file.stat().st_size > self.max_file_size:
                    # Rotate file
                    counter = 1
                    while True:
                        rotated_file = self.storage_path / f"audit_{date_str}_{counter}.jsonl"
                        if not rotated_file.exists():
                            log_file.rename(rotated_file)
                            break
                        counter += 1
                
                # Write event to file
                event_json = json.dumps(asdict(event), default=str)
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(event_json + '\n')
                
                return True
                
        except Exception as e:
            logging.error(f"Failed to store audit event: {e}")
            return False
    
    def retrieve_events(self, start_date: datetime.datetime, 
                       end_date: datetime.datetime,
                       event_types: Optional[List[AuditEventType]] = None,
                       user_id: Optional[str] = None,
                       patient_id: Optional[str] = None) -> List[AuditEvent]:
        """Retrieve audit events from storage"""
        events = []
        
        # Generate date range for file search
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            date_str = current_date.strftime("%Y-%m-%d")
            log_pattern = f"audit_{date_str}*.jsonl"
            
            for log_file in self.storage_path.glob(log_pattern):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                event_data = json.loads(line)
                                event = self._dict_to_audit_event(event_data)
                                
                                # Apply filters
                                if not self._event_matches_filters(event, start_date, end_date,
                                                                 event_types, user_id, patient_id):
                                    continue
                                
                                events.append(event)
                                
                except Exception as e:
                    logging.error(f"Error reading audit log file {log_file}: {e}")
            
            current_date += datetime.timedelta(days=1)
        
        return sorted(events, key=lambda e: e.timestamp)
    
    def _dict_to_audit_event(self, data: Dict) -> AuditEvent:
        """Convert dictionary to AuditEvent object"""
        # Convert string timestamps back to datetime
        if isinstance(data['timestamp'], str):
            data['timestamp'] = datetime.datetime.fromisoformat(data['timestamp'])
        
        # Convert enums
        data['event_type'] = AuditEventType(data['event_type'])
        data['severity'] = AuditSeverity(data['severity'])
        data['outcome'] = AuditOutcome(data['outcome'])
        
        # Convert nested objects
        if data.get('user'):
            data['user'] = AuditUser(**data['user'])
        if data.get('resource'):
            data['resource'] = AuditableResource(**data['resource'])
        
        return AuditEvent(**data)
    
    def _event_matches_filters(self, event: AuditEvent, start_date: datetime.datetime,
                             end_date: datetime.datetime, event_types: Optional[List[AuditEventType]],
                             user_id: Optional[str], patient_id: Optional[str]) -> bool:
        """Check if event matches search filters"""
        # Time range
        if not (start_date <= event.timestamp <= end_date):
            return False
        
        # Event types
        if event_types and event.event_type not in event_types:
            return False
        
        # User ID
        if user_id and event.user.user_id != user_id:
            return False
        
        # Patient ID
        if patient_id and (not event.resource or event.resource.patient_id != patient_id):
            return False
        
        return True


class AuditTrail:
    """Main audit trail system"""
    
    def __init__(self, storage_path: str = "audit_logs", encryption_key: Optional[bytes] = None):
        self.storage = AuditStorage(storage_path)
        self.encryption = AuditEncryption(encryption_key)
        self.retention_policies = {
            AuditEventType.DATA_ACCESS: datetime.timedelta(days=2190),  # 6 years
            AuditEventType.PHI_DISCLOSURE: datetime.timedelta(days=2190),  # 6 years
            AuditEventType.SECURITY_INCIDENT: datetime.timedelta(days=2555),  # 7 years
            'default': datetime.timedelta(days=2190)  # 6 years default
        }
    
    def log_event(self, event_type: AuditEventType, user: AuditUser,
                  resource: Optional[AuditableResource] = None,
                  outcome: AuditOutcome = AuditOutcome.SUCCESS,
                  severity: AuditSeverity = AuditSeverity.MEDIUM,
                  action_description: Optional[str] = None,
                  source_system: Optional[str] = None,
                  destination_system: Optional[str] = None,
                  ip_address: Optional[str] = None,
                  user_agent: Optional[str] = None,
                  session_id: Optional[str] = None,
                  additional_metadata: Optional[Dict[str, Any]] = None) -> str:
        """Log an audit event"""
        
        event_id = str(uuid.uuid4())
        timestamp = datetime.datetime.utcnow()
        
        # Calculate retention date
        retention_period = self.retention_policies.get(event_type, 
                                                     self.retention_policies['default'])
        retention_until = timestamp + retention_period
        
        # Determine compliance tags
        compliance_tags = self._determine_compliance_tags(event_type, resource)
        
        # Create audit event
        event = AuditEvent(
            id=event_id,
            timestamp=timestamp,
            event_type=event_type,
            severity=severity,
            outcome=outcome,
            user=user,
            resource=resource,
            action_description=action_description,
            source_system=source_system,
            destination_system=destination_system,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id,
            additional_metadata=additional_metadata,
            compliance_tags=compliance_tags,
            retention_until=retention_until
        )
        
        # Hash sensitive identifiers
        if event.resource and event.resource.patient_id:
            event.resource.patient_id = self.encryption.hash_identifier(event.resource.patient_id)
        
        # Store event
        success = self.storage.store_event(event)
        
        if not success:
            logging.critical(f"Failed to store audit event {event_id}")
        
        # Log to system logger as well
        self._log_to_system(event)
        
        return event_id
    
    def log_data_access(self, user: AuditUser, resource: AuditableResource,
                       outcome: AuditOutcome = AuditOutcome.SUCCESS,
                       ip_address: Optional[str] = None,
                       session_id: Optional[str] = None) -> str:
        """Log data access event"""
        severity = AuditSeverity.HIGH if resource.sensitive_data_categories else AuditSeverity.MEDIUM
        
        return self.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            user=user,
            resource=resource,
            outcome=outcome,
            severity=severity,
            action_description=f"Access to {resource.resource_type}",
            ip_address=ip_address,
            session_id=session_id
        )
    
    def log_phi_disclosure(self, user: AuditUser, patient_id: str,
                          disclosed_to: str, purpose: str,
                          data_categories: List[str]) -> str:
        """Log PHI disclosure event"""
        resource = AuditableResource(
            resource_type="PHI",
            resource_id="disclosure",
            patient_id=patient_id,
            sensitive_data_categories=data_categories
        )
        
        return self.log_event(
            event_type=AuditEventType.PHI_DISCLOSURE,
            user=user,
            resource=resource,
            severity=AuditSeverity.HIGH,
            action_description=f"PHI disclosed to {disclosed_to} for {purpose}",
            additional_metadata={
                'disclosed_to': disclosed_to,
                'purpose': purpose,
                'data_categories': data_categories
            }
        )
    
    def log_security_incident(self, incident_type: str, description: str,
                            affected_resources: List[str],
                            severity: AuditSeverity = AuditSeverity.CRITICAL,
                            user: Optional[AuditUser] = None) -> str:
        """Log security incident"""
        # Use system user if no user specified
        if not user:
            user = AuditUser(
                user_id="system",
                user_type="system",
                user_name="System Monitor"
            )
        
        return self.log_event(
            event_type=AuditEventType.SECURITY_INCIDENT,
            user=user,
            severity=severity,
            outcome=AuditOutcome.FAILURE,
            action_description=f"Security incident: {incident_type}",
            additional_metadata={
                'incident_type': incident_type,
                'description': description,
                'affected_resources': affected_resources
            }
        )
    
    def log_user_authentication(self, user_id: str, user_type: str,
                              login_success: bool, ip_address: str,
                              user_agent: Optional[str] = None,
                              failure_reason: Optional[str] = None) -> str:
        """Log user authentication event"""
        user = AuditUser(
            user_id=user_id,
            user_type=user_type
        )
        
        event_type = AuditEventType.USER_LOGIN
        outcome = AuditOutcome.SUCCESS if login_success else AuditOutcome.FAILURE
        severity = AuditSeverity.MEDIUM if login_success else AuditSeverity.HIGH
        
        description = "User login successful" if login_success else f"User login failed: {failure_reason}"
        
        return self.log_event(
            event_type=event_type,
            user=user,
            outcome=outcome,
            severity=severity,
            action_description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_metadata={'failure_reason': failure_reason} if failure_reason else None
        )
    
    def search_events(self, start_date: datetime.datetime, end_date: datetime.datetime,
                     event_types: Optional[List[AuditEventType]] = None,
                     user_id: Optional[str] = None,
                     patient_id: Optional[str] = None,
                     severity: Optional[AuditSeverity] = None) -> List[AuditEvent]:
        """Search audit events by criteria"""
        # Hash patient ID for search if provided
        if patient_id:
            patient_id = self.encryption.hash_identifier(patient_id)
        
        events = self.storage.retrieve_events(start_date, end_date, event_types, user_id, patient_id)
        
        # Additional filtering
        if severity:
            events = [e for e in events if e.severity == severity]
        
        return events
    
    def generate_compliance_report(self, start_date: datetime.datetime,
                                 end_date: datetime.datetime) -> Dict[str, Any]:
        """Generate compliance audit report"""
        events = self.search_events(start_date, end_date)
        
        report = {
            'report_period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_events': len(events),
                'by_type': {},
                'by_severity': {},
                'by_outcome': {},
                'high_risk_events': 0
            },
            'phi_access': {
                'total_access_events': 0,
                'unique_users': set(),
                'unique_patients': set()
            },
            'security_incidents': [],
            'compliance_violations': [],
            'generated_at': datetime.datetime.utcnow().isoformat()
        }
        
        # Analyze events
        for event in events:
            # Summary statistics
            event_type_str = event.event_type.value
            report['summary']['by_type'][event_type_str] = report['summary']['by_type'].get(event_type_str, 0) + 1
            
            severity_str = event.severity.value
            report['summary']['by_severity'][severity_str] = report['summary']['by_severity'].get(severity_str, 0) + 1
            
            outcome_str = event.outcome.value
            report['summary']['by_outcome'][outcome_str] = report['summary']['by_outcome'].get(outcome_str, 0) + 1
            
            if event.severity in [AuditSeverity.HIGH, AuditSeverity.CRITICAL]:
                report['summary']['high_risk_events'] += 1
            
            # PHI access analysis
            if event.event_type == AuditEventType.DATA_ACCESS:
                report['phi_access']['total_access_events'] += 1
                report['phi_access']['unique_users'].add(event.user.user_id)
                if event.resource and event.resource.patient_id:
                    report['phi_access']['unique_patients'].add(event.resource.patient_id)
            
            # Security incidents
            if event.event_type == AuditEventType.SECURITY_INCIDENT:
                report['security_incidents'].append({
                    'timestamp': event.timestamp.isoformat(),
                    'description': event.action_description,
                    'severity': event.severity.value,
                    'metadata': event.additional_metadata
                })
        
        # Convert sets to counts
        report['phi_access']['unique_users'] = len(report['phi_access']['unique_users'])
        report['phi_access']['unique_patients'] = len(report['phi_access']['unique_patients'])
        
        return report
    
    def cleanup_expired_events(self) -> int:
        """Remove audit events past their retention period"""
        # This is a simplified implementation
        # In production, this would need to scan stored files and remove expired events
        logging.info("Audit cleanup process would run here")
        return 0
    
    def _determine_compliance_tags(self, event_type: AuditEventType, 
                                 resource: Optional[AuditableResource]) -> List[str]:
        """Determine compliance tags for event"""
        tags = []
        
        # HIPAA-related events
        if event_type in [AuditEventType.DATA_ACCESS, AuditEventType.PHI_DISCLOSURE]:
            tags.append("HIPAA")
        
        # SOX-related events (if applicable)
        if event_type in [AuditEventType.DATA_DELETE, AuditEventType.DATA_UPDATE]:
            tags.append("SOX")
        
        # High-risk data categories
        if resource and resource.sensitive_data_categories:
            sensitive_categories = {'mental_health', 'substance_abuse', 'hiv_aids', 'genetic_info'}
            if any(cat in sensitive_categories for cat in resource.sensitive_data_categories):
                tags.append("HIGH_SENSITIVITY")
        
        return tags
    
    def _log_to_system(self, event: AuditEvent):
        """Log audit event to system logger"""
        level = {
            AuditSeverity.LOW: logging.INFO,
            AuditSeverity.MEDIUM: logging.INFO,
            AuditSeverity.HIGH: logging.WARNING,
            AuditSeverity.CRITICAL: logging.CRITICAL
        }.get(event.severity, logging.INFO)
        
        message = (f"AUDIT: {event.event_type.value} by {event.user.user_id} "
                  f"[{event.outcome.value}] - {event.action_description}")
        
        logging.log(level, message)


class AuditAnalyzer:
    """Analyze audit logs for patterns and anomalies"""
    
    def __init__(self, audit_trail: AuditTrail):
        self.audit_trail = audit_trail
    
    def detect_unusual_access_patterns(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Detect unusual access patterns in audit logs"""
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        events = self.audit_trail.search_events(
            start_date, end_date, 
            [AuditEventType.DATA_ACCESS]
        )
        
        # Analyze access patterns
        user_access_counts = {}
        time_based_access = {}
        
        for event in events:
            user_id = event.user.user_id
            hour = event.timestamp.hour
            
            user_access_counts[user_id] = user_access_counts.get(user_id, 0) + 1
            
            if user_id not in time_based_access:
                time_based_access[user_id] = {}
            time_based_access[user_id][hour] = time_based_access[user_id].get(hour, 0) + 1
        
        anomalies = []
        
        # Detect high-volume access
        if user_access_counts:
            avg_access = sum(user_access_counts.values()) / len(user_access_counts)
            threshold = avg_access * 3  # 3x average
            
            for user_id, count in user_access_counts.items():
                if count > threshold:
                    anomalies.append({
                        'type': 'high_volume_access',
                        'user_id': user_id,
                        'access_count': count,
                        'threshold': threshold,
                        'severity': 'medium'
                    })
        
        # Detect unusual time access
        for user_id, hourly_access in time_based_access.items():
            # Check for access during unusual hours (11 PM - 5 AM)
            unusual_hours = sum(hourly_access.get(hour, 0) for hour in range(23, 24)) + \
                          sum(hourly_access.get(hour, 0) for hour in range(0, 6))
            
            if unusual_hours > 0:
                total_access = sum(hourly_access.values())
                if unusual_hours / total_access > 0.3:  # 30% of access during unusual hours
                    anomalies.append({
                        'type': 'unusual_time_access',
                        'user_id': user_id,
                        'unusual_access_count': unusual_hours,
                        'total_access': total_access,
                        'severity': 'low'
                    })
        
        return anomalies
    
    def generate_user_activity_report(self, user_id: str, days_back: int = 90) -> Dict[str, Any]:
        """Generate detailed activity report for a user"""
        end_date = datetime.datetime.utcnow()
        start_date = end_date - datetime.timedelta(days=days_back)
        
        events = self.audit_trail.search_events(start_date, end_date, user_id=user_id)
        
        report = {
            'user_id': user_id,
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_events': len(events),
            'event_breakdown': {},
            'access_patterns': {
                'by_hour': {},
                'by_day_of_week': {},
                'most_accessed_resources': {}
            },
            'security_events': 0,
            'failed_actions': 0
        }
        
        for event in events:
            # Event type breakdown
            event_type = event.event_type.value
            report['event_breakdown'][event_type] = report['event_breakdown'].get(event_type, 0) + 1
            
            # Time patterns
            hour = event.timestamp.hour
            day_of_week = event.timestamp.strftime('%A')
            
            report['access_patterns']['by_hour'][hour] = report['access_patterns']['by_hour'].get(hour, 0) + 1
            report['access_patterns']['by_day_of_week'][day_of_week] = report['access_patterns']['by_day_of_week'].get(day_of_week, 0) + 1
            
            # Resource access
            if event.resource:
                resource_key = f"{event.resource.resource_type}:{event.resource.resource_id}"
                report['access_patterns']['most_accessed_resources'][resource_key] = \
                    report['access_patterns']['most_accessed_resources'].get(resource_key, 0) + 1
            
            # Security and failure tracking
            if event.event_type == AuditEventType.SECURITY_INCIDENT:
                report['security_events'] += 1
            
            if event.outcome == AuditOutcome.FAILURE:
                report['failed_actions'] += 1
        
        return report