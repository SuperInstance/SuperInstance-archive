"""
Tests for Healthcare Audit Trail System
"""
import unittest
import datetime
import tempfile
import shutil
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from ..src.audit_trail import (
    AuditTrail, AuditEvent, AuditUser, AuditableResource,
    AuditEventType, AuditSeverity, AuditOutcome,
    AuditStorage, AuditEncryption, AuditAnalyzer
)


class TestAuditEncryption(unittest.TestCase):
    
    def setUp(self):
        self.encryption = AuditEncryption()
    
    def test_hash_identifier(self):
        """Test identifier hashing"""
        patient_id = "12345"
        hash1 = self.encryption.hash_identifier(patient_id)
        hash2 = self.encryption.hash_identifier(patient_id)
        
        self.assertEqual(hash1, hash2)  # Consistent hashing
        self.assertNotEqual(hash1, patient_id)  # Actually hashed
        self.assertEqual(len(hash1), 16)  # Truncated to 16 chars
    
    @patch('healthcare.audit.src.audit_trail.Fernet')
    def test_encryption_without_cryptography(self, mock_fernet):
        """Test graceful handling when cryptography is not available"""
        mock_fernet.side_effect = ImportError("cryptography not available")
        
        encryption = AuditEncryption()
        self.assertIsNone(encryption.cipher)
        
        # Should return original data when encryption not available
        data = "sensitive data"
        encrypted = encryption.encrypt_sensitive_data(data)
        self.assertEqual(encrypted, data)


class TestAuditStorage(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = AuditStorage(self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_store_and_retrieve_event(self):
        """Test storing and retrieving audit events"""
        user = AuditUser(user_id="test_user", user_type="provider")
        resource = AuditableResource(resource_type="Patient", resource_id="123", patient_id="patient123")
        
        event = AuditEvent(
            id="test_event_1",
            timestamp=datetime.datetime.utcnow(),
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.MEDIUM,
            outcome=AuditOutcome.SUCCESS,
            user=user,
            resource=resource,
            action_description="Test data access"
        )
        
        # Store event
        success = self.storage.store_event(event)
        self.assertTrue(success)
        
        # Retrieve event
        start_date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        end_date = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        
        retrieved_events = self.storage.retrieve_events(start_date, end_date)
        
        self.assertEqual(len(retrieved_events), 1)
        self.assertEqual(retrieved_events[0].id, "test_event_1")
        self.assertEqual(retrieved_events[0].user.user_id, "test_user")
    
    def test_event_filtering(self):
        """Test event retrieval with filters"""
        user1 = AuditUser(user_id="user1", user_type="provider")
        user2 = AuditUser(user_id="user2", user_type="admin")
        
        # Create events with different characteristics
        event1 = AuditEvent(
            id="event1",
            timestamp=datetime.datetime.utcnow(),
            event_type=AuditEventType.DATA_ACCESS,
            severity=AuditSeverity.MEDIUM,
            outcome=AuditOutcome.SUCCESS,
            user=user1
        )
        
        event2 = AuditEvent(
            id="event2",
            timestamp=datetime.datetime.utcnow(),
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.LOW,
            outcome=AuditOutcome.SUCCESS,
            user=user2
        )
        
        # Store events
        self.storage.store_event(event1)
        self.storage.store_event(event2)
        
        # Test filtering by event type
        start_date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        end_date = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        
        access_events = self.storage.retrieve_events(
            start_date, end_date, 
            event_types=[AuditEventType.DATA_ACCESS]
        )
        
        self.assertEqual(len(access_events), 1)
        self.assertEqual(access_events[0].event_type, AuditEventType.DATA_ACCESS)
        
        # Test filtering by user
        user1_events = self.storage.retrieve_events(
            start_date, end_date,
            user_id="user1"
        )
        
        self.assertEqual(len(user1_events), 1)
        self.assertEqual(user1_events[0].user.user_id, "user1")


class TestAuditTrail(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit_trail = AuditTrail(storage_path=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_event(self):
        """Test basic event logging"""
        user = AuditUser(user_id="test_user", user_type="provider")
        resource = AuditableResource(resource_type="Patient", resource_id="123")
        
        event_id = self.audit_trail.log_event(
            event_type=AuditEventType.DATA_ACCESS,
            user=user,
            resource=resource,
            action_description="Test access"
        )
        
        self.assertIsNotNone(event_id)
        
        # Verify event was stored
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, event_id)
    
    def test_log_data_access(self):
        """Test data access logging"""
        user = AuditUser(user_id="doctor1", user_type="provider")
        resource = AuditableResource(
            resource_type="Patient",
            resource_id="patient123",
            patient_id="patient123",
            sensitive_data_categories=["mental_health"]
        )
        
        event_id = self.audit_trail.log_data_access(
            user=user,
            resource=resource,
            ip_address="192.168.1.100"
        )
        
        self.assertIsNotNone(event_id)
        
        # Check that sensitive data access gets high severity
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].severity, AuditSeverity.HIGH)
    
    def test_log_phi_disclosure(self):
        """Test PHI disclosure logging"""
        user = AuditUser(user_id="provider1", user_type="provider")
        
        event_id = self.audit_trail.log_phi_disclosure(
            user=user,
            patient_id="patient123",
            disclosed_to="Insurance Company",
            purpose="Claims Processing",
            data_categories=["demographics", "diagnosis"]
        )
        
        self.assertIsNotNone(event_id)
        
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, AuditEventType.PHI_DISCLOSURE)
        self.assertEqual(events[0].severity, AuditSeverity.HIGH)
    
    def test_log_security_incident(self):
        """Test security incident logging"""
        event_id = self.audit_trail.log_security_incident(
            incident_type="Unauthorized Access Attempt",
            description="Multiple failed login attempts detected",
            affected_resources=["user_accounts", "patient_data"],
            severity=AuditSeverity.CRITICAL
        )
        
        self.assertIsNotNone(event_id)
        
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        )
        
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_type, AuditEventType.SECURITY_INCIDENT)
        self.assertEqual(events[0].severity, AuditSeverity.CRITICAL)
        self.assertEqual(events[0].outcome, AuditOutcome.FAILURE)
    
    def test_log_user_authentication(self):
        """Test user authentication logging"""
        # Successful login
        success_event_id = self.audit_trail.log_user_authentication(
            user_id="doctor1",
            user_type="provider",
            login_success=True,
            ip_address="192.168.1.100"
        )
        
        # Failed login
        fail_event_id = self.audit_trail.log_user_authentication(
            user_id="doctor1",
            user_type="provider",
            login_success=False,
            ip_address="192.168.1.100",
            failure_reason="Invalid password"
        )
        
        self.assertIsNotNone(success_event_id)
        self.assertIsNotNone(fail_event_id)
        
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        )
        
        self.assertEqual(len(events), 2)
        
        # Check outcomes and severities
        success_event = next(e for e in events if e.outcome == AuditOutcome.SUCCESS)
        fail_event = next(e for e in events if e.outcome == AuditOutcome.FAILURE)
        
        self.assertEqual(success_event.severity, AuditSeverity.MEDIUM)
        self.assertEqual(fail_event.severity, AuditSeverity.HIGH)
    
    def test_generate_compliance_report(self):
        """Test compliance report generation"""
        # Create sample events
        user = AuditUser(user_id="provider1", user_type="provider")
        resource = AuditableResource(
            resource_type="Patient",
            resource_id="patient123",
            patient_id="patient123"
        )
        
        # Data access event
        self.audit_trail.log_data_access(user=user, resource=resource)
        
        # Security incident
        self.audit_trail.log_security_incident(
            incident_type="Test Incident",
            description="Test security incident",
            affected_resources=["system"]
        )
        
        # Generate report
        start_date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        end_date = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        
        report = self.audit_trail.generate_compliance_report(start_date, end_date)
        
        self.assertIn('summary', report)
        self.assertIn('phi_access', report)
        self.assertIn('security_incidents', report)
        
        self.assertEqual(report['summary']['total_events'], 2)
        self.assertEqual(report['phi_access']['total_access_events'], 1)
        self.assertEqual(len(report['security_incidents']), 1)
    
    def test_patient_id_hashing(self):
        """Test that patient IDs are hashed in audit logs"""
        user = AuditUser(user_id="provider1", user_type="provider")
        original_patient_id = "patient123"
        resource = AuditableResource(
            resource_type="Patient",
            resource_id="patient123",
            patient_id=original_patient_id
        )
        
        self.audit_trail.log_data_access(user=user, resource=resource)
        
        # Search by original patient ID should work (internally hashed)
        events = self.audit_trail.search_events(
            datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
            datetime.datetime.utcnow() + datetime.timedelta(minutes=1),
            patient_id=original_patient_id
        )
        
        self.assertEqual(len(events), 1)
        
        # But the stored patient ID should be hashed
        self.assertNotEqual(events[0].resource.patient_id, original_patient_id)
        self.assertEqual(len(events[0].resource.patient_id), 16)  # Hashed and truncated


class TestAuditAnalyzer(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.audit_trail = AuditTrail(storage_path=self.temp_dir)
        self.analyzer = AuditAnalyzer(self.audit_trail)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_detect_unusual_access_patterns(self):
        """Test detection of unusual access patterns"""
        user_normal = AuditUser(user_id="normal_user", user_type="provider")
        user_high_volume = AuditUser(user_id="high_volume_user", user_type="provider")
        
        resource = AuditableResource(resource_type="Patient", resource_id="123")
        
        # Create normal access pattern (5 accesses)
        for _ in range(5):
            self.audit_trail.log_data_access(user=user_normal, resource=resource)
        
        # Create high volume access pattern (50 accesses)
        for _ in range(50):
            self.audit_trail.log_data_access(user=user_high_volume, resource=resource)
        
        # Detect anomalies
        anomalies = self.analyzer.detect_unusual_access_patterns(days_back=1)
        
        # Should detect high volume user
        high_volume_anomalies = [a for a in anomalies if a['type'] == 'high_volume_access']
        self.assertEqual(len(high_volume_anomalies), 1)
        self.assertEqual(high_volume_anomalies[0]['user_id'], 'high_volume_user')
    
    def test_generate_user_activity_report(self):
        """Test user activity report generation"""
        user = AuditUser(user_id="test_user", user_type="provider")
        resource = AuditableResource(resource_type="Patient", resource_id="123")
        
        # Create various events for the user
        self.audit_trail.log_data_access(user=user, resource=resource)
        self.audit_trail.log_user_authentication(
            user_id="test_user",
            user_type="provider",
            login_success=True,
            ip_address="192.168.1.100"
        )
        self.audit_trail.log_user_authentication(
            user_id="test_user",
            user_type="provider",
            login_success=False,
            ip_address="192.168.1.100",
            failure_reason="Invalid password"
        )
        
        # Generate report
        report = self.analyzer.generate_user_activity_report("test_user", days_back=1)
        
        self.assertEqual(report['user_id'], 'test_user')
        self.assertEqual(report['total_events'], 3)
        self.assertEqual(report['failed_actions'], 1)
        self.assertIn('data_access', report['event_breakdown'])
        self.assertIn('user_login', report['event_breakdown'])


if __name__ == '__main__':
    unittest.main()