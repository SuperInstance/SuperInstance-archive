"""
Audit Trail Management System
Comprehensive logging and tracking of all permission changes and access attempts
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of events to audit"""
    PERMISSION_GRANT = "permission_grant"
    PERMISSION_REVOKE = "permission_revoke" 
    PERMISSION_CHECK = "permission_check"
    PERMISSION_DENIED = "permission_denied"
    ROLE_CREATE = "role_create"
    ROLE_MODIFY = "role_modify"
    ROLE_DELETE = "role_delete"
    USER_CREATE = "user_create"
    USER_MODIFY = "user_modify"
    USER_DELETE = "user_delete"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    SESSION_EXPIRE = "session_expire"
    EMERGENCY_OVERRIDE = "emergency_override"
    POLICY_CHANGE = "policy_change"
    BULK_OPERATION = "bulk_operation"
    COMPLIANCE_VIOLATION = "compliance_violation"


class AuditSeverity(Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Individual audit event record"""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    target_user_id: Optional[str]
    resource_id: Optional[str]
    resource_type: Optional[str]
    action: str
    result: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    session_id: Optional[str]
    device_id: Optional[str]
    risk_score: float
    requires_review: bool
    metadata: Dict[str, Any]


@dataclass
class AuditSummary:
    """Audit summary statistics"""
    total_events: int
    events_by_type: Dict[str, int]
    events_by_severity: Dict[str, int]
    failed_attempts: int
    successful_operations: int
    high_risk_events: int
    compliance_violations: int
    time_range: Dict[str, datetime]


class AuditManager:
    """Comprehensive audit trail management system"""
    
    def __init__(self, data_dir: str = "audit_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        
        # In-memory cache for recent events
        self.recent_events: List[AuditEvent] = []
        self.max_recent_events = 10000
        
        # Risk scoring settings
        self.risk_weights = {
            "failed_login_attempts": 10,
            "permission_escalation": 20,
            "bulk_operations": 15,
            "after_hours_access": 5,
            "new_device": 8,
            "compliance_violation": 25
        }
        
        # Compliance settings
        self.retention_days = 2555  # 7 years for compliance
        self.immutable_logs = True
        self.log_integrity_checking = True
        
        # Alert thresholds
        self.alert_thresholds = {
            "failed_logins_per_hour": 10,
            "permission_changes_per_hour": 50,
            "high_risk_score_threshold": 80,
            "bulk_operation_size": 100
        }
        
        logger.info("AuditManager initialized")
    
    async def log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        target_user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        action: str = "",
        result: str = "",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        device_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None
    ) -> str:
        """Log an audit event"""
        try:
            event_id = f"audit_{uuid.uuid4().hex[:16]}"
            
            # Auto-determine severity if not provided
            if not severity:
                severity = self._determine_severity(event_type, details or {})
            
            # Calculate risk score
            risk_score = await self._calculate_risk_score(
                event_type, user_id, details or {}, ip_address, device_id
            )
            
            event = AuditEvent(
                event_id=event_id,
                event_type=event_type,
                severity=severity,
                timestamp=datetime.now(timezone.utc),
                user_id=user_id,
                target_user_id=target_user_id,
                resource_id=resource_id,
                resource_type=resource_type,
                action=action,
                result=result,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                device_id=device_id,
                risk_score=risk_score,
                requires_review=risk_score > self.alert_thresholds["high_risk_score_threshold"],
                metadata={}
            )
            
            # Add to recent events cache
            self.recent_events.append(event)
            if len(self.recent_events) > self.max_recent_events:
                self.recent_events.pop(0)
            
            # Persist to disk
            await self._persist_event(event)
            
            # Check for alerts
            await self._check_alert_conditions(event)
            
            logger.debug(f"Logged audit event {event_id}")
            return event_id
            
        except Exception as e:
            logger.error(f"Error logging audit event: {e}")
            # Always try to log audit failures
            try:
                await self._log_audit_failure(e, event_type, user_id)
            except:
                pass
            raise
    
    def _determine_severity(self, event_type: AuditEventType, details: Dict[str, Any]) -> AuditSeverity:
        """Automatically determine event severity"""
        high_severity_events = {
            AuditEventType.EMERGENCY_OVERRIDE,
            AuditEventType.COMPLIANCE_VIOLATION,
            AuditEventType.PERMISSION_DENIED
        }
        
        medium_severity_events = {
            AuditEventType.PERMISSION_GRANT,
            AuditEventType.PERMISSION_REVOKE,
            AuditEventType.LOGIN_FAILURE,
            AuditEventType.POLICY_CHANGE
        }
        
        if event_type in high_severity_events:
            return AuditSeverity.CRITICAL if details.get("is_critical") else AuditSeverity.HIGH
        elif event_type in medium_severity_events:
            return AuditSeverity.MEDIUM
        else:
            return AuditSeverity.LOW
    
    async def _calculate_risk_score(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        details: Dict[str, Any],
        ip_address: Optional[str],
        device_id: Optional[str]
    ) -> float:
        """Calculate risk score for event"""
        try:
            risk_score = 0.0
            
            # Base risk by event type
            base_risks = {
                AuditEventType.EMERGENCY_OVERRIDE: 90,
                AuditEventType.COMPLIANCE_VIOLATION: 85,
                AuditEventType.LOGIN_FAILURE: 30,
                AuditEventType.PERMISSION_DENIED: 40,
                AuditEventType.BULK_OPERATION: 50,
                AuditEventType.PERMISSION_GRANT: 20
            }
            
            risk_score += base_risks.get(event_type, 10)
            
            # Failed login attempt patterns
            if event_type == AuditEventType.LOGIN_FAILURE and user_id:
                recent_failures = await self._count_recent_events(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=user_id,
                    hours=1
                )
                if recent_failures >= 5:
                    risk_score += self.risk_weights["failed_login_attempts"] * (recent_failures - 4)
            
            # After hours access
            current_hour = datetime.now().hour
            if current_hour < 6 or current_hour > 22:
                risk_score += self.risk_weights["after_hours_access"]
            
            # New device access
            if device_id and user_id:
                device_seen_before = await self._device_seen_before(user_id, device_id)
                if not device_seen_before:
                    risk_score += self.risk_weights["new_device"]
            
            # Permission escalation
            if details.get("permission_escalation"):
                risk_score += self.risk_weights["permission_escalation"]
            
            # Bulk operations
            if details.get("operation_count", 0) > self.alert_thresholds["bulk_operation_size"]:
                risk_score += self.risk_weights["bulk_operations"]
            
            # Compliance violations
            if event_type == AuditEventType.COMPLIANCE_VIOLATION:
                risk_score += self.risk_weights["compliance_violation"]
            
            # Cap at 100
            return min(risk_score, 100.0)
            
        except Exception as e:
            logger.error(f"Error calculating risk score: {e}")
            return 50.0  # Default medium risk
    
    async def _count_recent_events(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        hours: int = 1
    ) -> int:
        """Count recent events of specific type"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        count = 0
        for event in self.recent_events:
            if (event.event_type == event_type and
                event.timestamp >= cutoff_time and
                (not user_id or event.user_id == user_id)):
                count += 1
        
        return count
    
    async def _device_seen_before(self, user_id: str, device_id: str) -> bool:
        """Check if device has been used by user before"""
        for event in self.recent_events:
            if (event.user_id == user_id and 
                event.device_id == device_id and
                event.event_type in [AuditEventType.LOGIN_SUCCESS, AuditEventType.PERMISSION_CHECK]):
                return True
        
        # Also check persisted logs (simplified check)
        return False
    
    async def _persist_event(self, event: AuditEvent):
        """Persist audit event to disk"""
        try:
            # Create date-based log files for organization
            date_str = event.timestamp.strftime("%Y%m%d")
            log_file = self.data_dir / f"audit_{date_str}.jsonl"
            
            # Convert to JSON line
            event_data = asdict(event)
            event_data["timestamp"] = event.timestamp.isoformat()
            # Convert enums to strings for JSON serialization
            event_data["event_type"] = event.event_type.value
            event_data["severity"] = event.severity.value
            
            # Add integrity hash if enabled
            if self.log_integrity_checking:
                event_data["_integrity_hash"] = self._calculate_integrity_hash(event_data)
            
            # Append to log file
            with open(log_file, 'a') as f:
                f.write(json.dumps(event_data) + '\n')
            
        except Exception as e:
            logger.error(f"Error persisting audit event: {e}")
            raise
    
    def _calculate_integrity_hash(self, event_data: Dict[str, Any]) -> str:
        """Calculate integrity hash for audit event"""
        # Remove hash field if present and sort keys for consistency
        hash_data = {k: v for k, v in event_data.items() if k != "_integrity_hash"}
        data_string = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    async def _check_alert_conditions(self, event: AuditEvent):
        """Check if event triggers any alerts"""
        try:
            alerts = []
            
            # High risk score alert
            if event.risk_score > self.alert_thresholds["high_risk_score_threshold"]:
                alerts.append({
                    "type": "high_risk_event",
                    "message": f"High risk event detected: {event.event_type.value}",
                    "risk_score": event.risk_score,
                    "event_id": event.event_id
                })
            
            # Failed login pattern
            if event.event_type == AuditEventType.LOGIN_FAILURE and event.user_id:
                recent_failures = await self._count_recent_events(
                    AuditEventType.LOGIN_FAILURE,
                    user_id=event.user_id,
                    hours=1
                )
                if recent_failures >= self.alert_thresholds["failed_logins_per_hour"]:
                    alerts.append({
                        "type": "login_failure_pattern",
                        "message": f"Multiple failed logins for user {event.user_id}",
                        "failure_count": recent_failures,
                        "user_id": event.user_id
                    })
            
            # Permission change rate
            if event.event_type in [AuditEventType.PERMISSION_GRANT, AuditEventType.PERMISSION_REVOKE]:
                recent_changes = await self._count_recent_events(
                    AuditEventType.PERMISSION_GRANT, hours=1
                ) + await self._count_recent_events(
                    AuditEventType.PERMISSION_REVOKE, hours=1
                )
                
                if recent_changes >= self.alert_thresholds["permission_changes_per_hour"]:
                    alerts.append({
                        "type": "high_permission_change_rate",
                        "message": "Unusually high permission change rate detected",
                        "change_count": recent_changes
                    })
            
            # Process alerts
            for alert in alerts:
                await self._process_alert(alert, event)
                
        except Exception as e:
            logger.error(f"Error checking alert conditions: {e}")
    
    async def _process_alert(self, alert: Dict[str, Any], event: AuditEvent):
        """Process security alert"""
        logger.warning(f"SECURITY ALERT: {alert['message']}")
        
        # Log the alert as an audit event
        await self.log_event(
            event_type=AuditEventType.POLICY_CHANGE,  # Using as generic alert type
            user_id=event.user_id,
            action="security_alert_triggered",
            result="alert_logged",
            details=alert,
            severity=AuditSeverity.HIGH
        )
    
    async def _log_audit_failure(self, error: Exception, event_type: AuditEventType, user_id: Optional[str]):
        """Log audit system failures"""
        try:
            failure_file = self.data_dir / "audit_failures.log"
            with open(failure_file, 'a') as f:
                f.write(f"{datetime.now().isoformat()} - AUDIT_FAILURE: {event_type.value} - {user_id} - {str(error)}\n")
        except:
            pass  # Can't do much if audit failure logging fails
    
    async def search_events(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        requires_review: Optional[bool] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """Search audit events with filters"""
        try:
            results = []
            
            # Search recent events first
            for event in reversed(self.recent_events):  # Most recent first
                if self._event_matches_filters(
                    event, start_date, end_date, event_types, 
                    user_id, resource_id, severity, requires_review
                ):
                    results.append(event)
                    if len(results) >= limit:
                        break
            
            # If we need more results, search persisted logs
            if len(results) < limit:
                persisted_results = await self._search_persisted_events(
                    start_date, end_date, event_types, user_id, 
                    resource_id, severity, requires_review, limit - len(results)
                )
                results.extend(persisted_results)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching events: {e}")
            return []
    
    def _event_matches_filters(
        self,
        event: AuditEvent,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[List[AuditEventType]],
        user_id: Optional[str],
        resource_id: Optional[str],
        severity: Optional[AuditSeverity],
        requires_review: Optional[bool]
    ) -> bool:
        """Check if event matches search filters"""
        if start_date and event.timestamp < start_date:
            return False
        if end_date and event.timestamp > end_date:
            return False
        if event_types and event.event_type not in event_types:
            return False
        if user_id and event.user_id != user_id:
            return False
        if resource_id and event.resource_id != resource_id:
            return False
        if severity and event.severity != severity:
            return False
        if requires_review is not None and event.requires_review != requires_review:
            return False
        return True
    
    async def _search_persisted_events(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        event_types: Optional[List[AuditEventType]],
        user_id: Optional[str],
        resource_id: Optional[str],
        severity: Optional[AuditSeverity],
        requires_review: Optional[bool],
        limit: int
    ) -> List[AuditEvent]:
        """Search persisted audit events"""
        try:
            results = []
            
            # Determine which log files to search based on date range
            log_files = []
            if start_date or end_date:
                start = start_date or datetime.now() - timedelta(days=30)
                end = end_date or datetime.now()
                
                current_date = start.date()
                while current_date <= end.date():
                    date_str = current_date.strftime("%Y%m%d")
                    log_file = self.data_dir / f"audit_{date_str}.jsonl"
                    if log_file.exists():
                        log_files.append(log_file)
                    current_date += timedelta(days=1)
            else:
                # Search all log files (limited for performance)
                log_files = list(self.data_dir.glob("audit_*.jsonl"))[-30:]  # Last 30 days
            
            # Search log files
            for log_file in sorted(log_files, reverse=True):  # Most recent first
                try:
                    with open(log_file, 'r') as f:
                        for line in f:
                            if len(results) >= limit:
                                break
                                
                            try:
                                event_data = json.loads(line.strip())
                                # Convert back to AuditEvent object
                                event_data["timestamp"] = datetime.fromisoformat(event_data["timestamp"].replace("Z", "+00:00"))
                                event_data["event_type"] = AuditEventType(event_data["event_type"])
                                event_data["severity"] = AuditSeverity(event_data["severity"])
                                
                                # Remove integrity hash for object creation
                                event_data.pop("_integrity_hash", None)
                                
                                event = AuditEvent(**event_data)
                                
                                if self._event_matches_filters(
                                    event, start_date, end_date, event_types,
                                    user_id, resource_id, severity, requires_review
                                ):
                                    results.append(event)
                                    
                            except (json.JSONDecodeError, ValueError, KeyError) as e:
                                logger.warning(f"Error parsing audit log line: {e}")
                                continue
                                
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching persisted events: {e}")
            return []
    
    async def generate_audit_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> AuditSummary:
        """Generate audit summary statistics"""
        try:
            if not start_date:
                start_date = datetime.now(timezone.utc) - timedelta(days=30)
            if not end_date:
                end_date = datetime.now(timezone.utc)
            
            events = await self.search_events(
                start_date=start_date,
                end_date=end_date,
                limit=10000  # High limit for comprehensive summary
            )
            
            events_by_type = {}
            events_by_severity = {}
            failed_attempts = 0
            successful_operations = 0
            high_risk_events = 0
            compliance_violations = 0
            
            for event in events:
                # Count by type
                event_type_str = event.event_type.value
                events_by_type[event_type_str] = events_by_type.get(event_type_str, 0) + 1
                
                # Count by severity
                severity_str = event.severity.value
                events_by_severity[severity_str] = events_by_severity.get(severity_str, 0) + 1
                
                # Count failures and successes
                if "failure" in event.result.lower() or "denied" in event.result.lower():
                    failed_attempts += 1
                else:
                    successful_operations += 1
                
                # High risk events
                if event.risk_score > self.alert_thresholds["high_risk_score_threshold"]:
                    high_risk_events += 1
                
                # Compliance violations
                if event.event_type == AuditEventType.COMPLIANCE_VIOLATION:
                    compliance_violations += 1
            
            return AuditSummary(
                total_events=len(events),
                events_by_type=events_by_type,
                events_by_severity=events_by_severity,
                failed_attempts=failed_attempts,
                successful_operations=successful_operations,
                high_risk_events=high_risk_events,
                compliance_violations=compliance_violations,
                time_range={"start": start_date, "end": end_date}
            )
            
        except Exception as e:
            logger.error(f"Error generating audit summary: {e}")
            return AuditSummary(
                total_events=0,
                events_by_type={},
                events_by_severity={},
                failed_attempts=0,
                successful_operations=0,
                high_risk_events=0,
                compliance_violations=0,
                time_range={"start": start_date or datetime.now(), "end": end_date or datetime.now()}
            )
    
    async def cleanup_old_logs(self):
        """Clean up old audit logs based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for log_file in self.data_dir.glob("audit_*.jsonl"):
                try:
                    # Extract date from filename
                    date_str = log_file.stem.replace("audit_", "")
                    file_date = datetime.strptime(date_str, "%Y%m%d")
                    
                    if file_date < cutoff_date:
                        if self.immutable_logs:
                            # Move to archive instead of deleting
                            archive_dir = self.data_dir / "archive"
                            archive_dir.mkdir(exist_ok=True)
                            log_file.rename(archive_dir / log_file.name)
                            logger.info(f"Archived old audit log: {log_file.name}")
                        else:
                            log_file.unlink()
                            logger.info(f"Deleted old audit log: {log_file.name}")
                            
                except (ValueError, OSError) as e:
                    logger.warning(f"Error processing log file {log_file}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")