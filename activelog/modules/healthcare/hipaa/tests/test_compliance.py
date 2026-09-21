"""
Tests for HIPAA compliance framework
"""
import unittest
import datetime
from unittest.mock import patch
from ..src.compliance import (
    HIPAACompliance, PHIClassification, AccessLevel, 
    DataRetentionManager, BusinessAssociateAgreement
)


class TestHIPAACompliance(unittest.TestCase):
    
    def setUp(self):
        self.compliance = HIPAACompliance()
    
    def test_phi_encryption(self):
        """Test PHI encryption and decryption"""
        original_data = "123-45-6789"
        encrypted = self.compliance.encrypt_phi(original_data)
        decrypted = self.compliance.decrypt_phi(encrypted)
        
        self.assertNotEqual(original_data, encrypted)
        self.assertEqual(original_data, decrypted)
    
    def test_identifier_hashing(self):
        """Test consistent hashing of identifiers"""
        ssn = "123-45-6789"
        hash1 = self.compliance.hash_identifier(ssn)
        hash2 = self.compliance.hash_identifier(ssn)
        
        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, ssn)
    
    def test_access_validation(self):
        """Test access validation for different roles and purposes"""
        fields = ['name', 'ssn', 'diagnosis']
        
        # Treatment access should allow more fields
        treatment_access = self.compliance.validate_access(
            'doctor', fields, AccessLevel.TREATMENT
        )
        self.assertTrue(treatment_access['diagnosis'])
        
        # Minimum necessary should be more restrictive
        minimum_access = self.compliance.validate_access(
            'billing', fields, AccessLevel.MINIMUM_NECESSARY
        )
        self.assertTrue(minimum_access['name'])
    
    def test_de_identification(self):
        """Test data de-identification"""
        patient_data = {
            'name': 'John Doe',
            'ssn': '123-45-6789',
            'age': 35,
            'diagnosis': 'Hypertension'
        }
        
        de_identified = self.compliance.de_identify_data(patient_data)
        
        self.assertNotIn('name', de_identified)  # Direct identifier removed
        self.assertIn('ssn', de_identified)      # SSN hashed, not removed
        self.assertIn('age', de_identified)      # Non-PHI preserved
        self.assertNotEqual(de_identified['ssn'], patient_data['ssn'])
    
    def test_breach_notification_logic(self):
        """Test breach notification requirements"""
        # Large breach should require notification
        large_breach = self.compliance.check_breach_notification_required(
            600, ['name', 'address']
        )
        self.assertTrue(large_breach)
        
        # Small breach with high-risk data should require notification
        high_risk_breach = self.compliance.check_breach_notification_required(
            10, ['ssn', 'medical_record_number']
        )
        self.assertTrue(high_risk_breach)
        
        # Small breach with low-risk data should not require notification
        low_risk_breach = self.compliance.check_breach_notification_required(
            10, ['name', 'address']
        )
        self.assertFalse(low_risk_breach)


class TestDataRetentionManager(unittest.TestCase):
    
    def setUp(self):
        self.retention_manager = DataRetentionManager()
    
    def test_retention_expiry_check(self):
        """Test retention period expiry checking"""
        # Record from 7 years ago should be expired for medical records
        old_date = datetime.datetime.utcnow() - datetime.timedelta(days=365*7)
        expired = self.retention_manager.check_retention_expiry('medical_records', old_date)
        self.assertTrue(expired)
        
        # Recent record should not be expired
        recent_date = datetime.datetime.utcnow() - datetime.timedelta(days=365)
        not_expired = self.retention_manager.check_retention_expiry('medical_records', recent_date)
        self.assertFalse(not_expired)


class TestBusinessAssociateAgreement(unittest.TestCase):
    
    def setUp(self):
        self.baa_manager = BusinessAssociateAgreement()
    
    def test_third_party_validation(self):
        """Test third party access validation"""
        # Register a valid agreement
        self.baa_manager.register_agreement(
            'vendor123',
            ['billing', 'claims'],
            datetime.datetime.utcnow() + datetime.timedelta(days=365)
        )
        
        # Valid access should be allowed
        valid_access = self.baa_manager.validate_third_party_access('vendor123', 'billing')
        self.assertTrue(valid_access)
        
        # Invalid access should be denied
        invalid_access = self.baa_manager.validate_third_party_access('vendor123', 'treatment')
        self.assertFalse(invalid_access)
        
        # Unregistered vendor should be denied
        unregistered = self.baa_manager.validate_third_party_access('vendor456', 'billing')
        self.assertFalse(unregistered)


if __name__ == '__main__':
    unittest.main()