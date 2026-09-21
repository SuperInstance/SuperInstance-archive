"""
Tests for Patient Consent Management System
"""
import unittest
import datetime
from unittest.mock import Mock, patch
from ..src.consent_manager import (
    ConsentManager, PatientConsent, ConsentProvision, ConsentParty,
    ConsentStatus, ConsentType, ConsentScope, DataCategory,
    ConsentValidator, ConsentTemplateManager
)


class TestConsentValidator(unittest.TestCase):
    
    def setUp(self):
        self.validator = ConsentValidator()
    
    def test_validate_valid_consent(self):
        """Test validation of valid consent"""
        provision = ConsentProvision(
            id="prov1",
            type="permit",
            purpose=[ConsentType.TREATMENT],
            data_categories=[DataCategory.DEMOGRAPHICS],
            actors=[]
        )
        
        consent = PatientConsent(
            id="consent1",
            patient_id="patient123",
            status=ConsentStatus.ACTIVE,
            scope=ConsentScope.GENERAL,
            category=[ConsentType.TREATMENT],
            provisions=[provision],
            date_recorded=datetime.datetime.utcnow(),
            effective_date=datetime.datetime.utcnow()
        )
        
        errors = self.validator.validate_consent(consent)
        self.assertEqual(len(errors), 0)
    
    def test_validate_missing_patient_id(self):
        """Test validation fails for missing patient ID"""
        provision = ConsentProvision(
            id="prov1",
            type="permit",
            purpose=[ConsentType.TREATMENT],
            data_categories=[DataCategory.DEMOGRAPHICS],
            actors=[]
        )
        
        consent = PatientConsent(
            id="consent1",
            patient_id="",  # Missing patient ID
            status=ConsentStatus.ACTIVE,
            scope=ConsentScope.GENERAL,
            category=[ConsentType.TREATMENT],
            provisions=[provision],
            date_recorded=datetime.datetime.utcnow(),
            effective_date=datetime.datetime.utcnow()
        )
        
        errors = self.validator.validate_consent(consent)
        self.assertIn("Patient ID is required", errors)
    
    def test_validate_special_category_consent(self):
        """Test validation of special category data consent"""
        provision = ConsentProvision(
            id="prov1",
            type="permit",
            purpose=[ConsentType.TREATMENT],
            data_categories=[DataCategory.MENTAL_HEALTH],  # Special category
            actors=[]
        )
        
        # General scope should fail for special categories
        consent = PatientConsent(
            id="consent1",
            patient_id="patient123",
            status=ConsentStatus.ACTIVE,
            scope=ConsentScope.GENERAL,  # General scope not allowed
            category=[ConsentType.TREATMENT],
            provisions=[provision],
            date_recorded=datetime.datetime.utcnow(),
            effective_date=datetime.datetime.utcnow()
        )
        
        errors = self.validator.validate_consent(consent)
        self.assertTrue(any("Explicit consent required for mental_health" in error for error in errors))


class TestConsentManager(unittest.TestCase):
    
    def setUp(self):
        self.consent_manager = ConsentManager()
    
    def test_create_consent_success(self):
        """Test successful consent creation"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }]
        }
        
        consent_id = self.consent_manager.create_consent('patient123', consent_data)
        
        self.assertIsNotNone(consent_id)
        self.assertIn(consent_id, self.consent_manager.storage)
        
        # Check consent was stored correctly
        stored_consent = self.consent_manager.get_consent(consent_id)
        self.assertEqual(stored_consent.patient_id, 'patient123')
        self.assertEqual(stored_consent.status, ConsentStatus.ACTIVE)
    
    def test_create_consent_validation_failure(self):
        """Test consent creation fails validation"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': []  # No provisions - should fail validation
        }
        
        with self.assertRaises(ValueError) as context:
            self.consent_manager.create_consent('patient123', consent_data)
        
        self.assertIn("validation failed", str(context.exception))
    
    def test_get_patient_consents(self):
        """Test retrieving all consents for a patient"""
        # Create multiple consents for same patient
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }]
        }
        
        consent_id1 = self.consent_manager.create_consent('patient123', consent_data)
        consent_id2 = self.consent_manager.create_consent('patient123', consent_data)
        
        # Should not return consents for different patient
        self.consent_manager.create_consent('patient456', consent_data)
        
        consents = self.consent_manager.get_patient_consents('patient123')
        
        self.assertEqual(len(consents), 2)
        consent_ids = [c.id for c in consents]
        self.assertIn(consent_id1, consent_ids)
        self.assertIn(consent_id2, consent_ids)
    
    def test_update_consent_status(self):
        """Test updating consent status"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }]
        }
        
        consent_id = self.consent_manager.create_consent('patient123', consent_data)
        
        # Update status
        success = self.consent_manager.update_consent_status(consent_id, ConsentStatus.WITHDRAWN)
        self.assertTrue(success)
        
        # Check status was updated
        consent = self.consent_manager.get_consent(consent_id)
        self.assertEqual(consent.status, ConsentStatus.WITHDRAWN)
    
    def test_withdraw_consent(self):
        """Test withdrawing consent"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }]
        }
        
        consent_id = self.consent_manager.create_consent('patient123', consent_data)
        
        # Withdraw consent
        success = self.consent_manager.withdraw_consent(consent_id, "Patient request")
        self.assertTrue(success)
        
        # Check status was updated
        consent = self.consent_manager.get_consent(consent_id)
        self.assertEqual(consent.status, ConsentStatus.WITHDRAWN)
    
    def test_check_access_permission_allowed(self):
        """Test access permission check - allowed case"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics', 'clinical_notes'],
                'actors': []
            }]
        }
        
        consent_id = self.consent_manager.create_consent('patient123', consent_data)
        
        # Check access
        result = self.consent_manager.check_access_permission(
            'patient123', 'doctor1', ConsentType.TREATMENT, [DataCategory.DEMOGRAPHICS]
        )
        
        self.assertTrue(result['permitted'])
        self.assertEqual(len(result['denied_categories']), 0)
        self.assertIn(consent_id, result['applicable_consents'])
    
    def test_check_access_permission_denied(self):
        """Test access permission check - denied case"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],  # Only demographics allowed
                'actors': []
            }]
        }
        
        self.consent_manager.create_consent('patient123', consent_data)
        
        # Check access for non-permitted category
        result = self.consent_manager.check_access_permission(
            'patient123', 'doctor1', ConsentType.TREATMENT, [DataCategory.MENTAL_HEALTH]
        )
        
        self.assertFalse(result['permitted'])
        self.assertIn(DataCategory.MENTAL_HEALTH, result['denied_categories'])
    
    def test_emergency_access_override(self):
        """Test emergency access overrides consent restrictions"""
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'deny',  # Deny all access
                'purpose': ['treatment'],
                'data_categories': ['demographics', 'clinical_notes'],
                'actors': []
            }]
        }
        
        self.consent_manager.create_consent('patient123', consent_data)
        
        # Emergency access should override denial
        result = self.consent_manager.check_access_permission(
            'patient123', 'emergency_doctor', ConsentType.EMERGENCY, 
            [DataCategory.DEMOGRAPHICS, DataCategory.CLINICAL_NOTES]
        )
        
        self.assertTrue(result['permitted'])
        self.assertEqual(len(result['denied_categories']), 0)
        self.assertIn('Emergency access', result['conditions'][0])
    
    def test_generate_consent_summary(self):
        """Test consent summary generation"""
        # Create multiple consents with different statuses
        active_consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }]
        }
        
        consent_id1 = self.consent_manager.create_consent('patient123', active_consent_data)
        consent_id2 = self.consent_manager.create_consent('patient123', active_consent_data)
        
        # Withdraw one consent
        self.consent_manager.withdraw_consent(consent_id2)
        
        summary = self.consent_manager.generate_consent_summary('patient123')
        
        self.assertEqual(summary['patient_id'], 'patient123')
        self.assertEqual(summary['total_consents'], 2)
        self.assertEqual(summary['active_consents'], 1)
        self.assertEqual(summary['withdrawn_consents'], 1)
        self.assertIn('treatment', summary['permitted_purposes'])
        self.assertIn('demographics', summary['permitted_categories'])
    
    def test_expire_old_consents(self):
        """Test automatic expiry of old consents"""
        # Create consent that expires in the past
        past_date = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        consent_data = {
            'status': 'active',
            'scope': 'general',
            'category': ['treatment'],
            'provisions': [{
                'type': 'permit',
                'purpose': ['treatment'],
                'data_categories': ['demographics'],
                'actors': []
            }],
            'expiry_date': past_date
        }
        
        consent_id = self.consent_manager.create_consent('patient123', consent_data)
        
        # Expire old consents
        expired_count = self.consent_manager.expire_old_consents()
        
        self.assertEqual(expired_count, 1)
        
        # Check consent status was updated
        consent = self.consent_manager.get_consent(consent_id)
        self.assertEqual(consent.status, ConsentStatus.EXPIRED)


class TestConsentTemplateManager(unittest.TestCase):
    
    def setUp(self):
        self.template_manager = ConsentTemplateManager()
    
    def test_get_default_template(self):
        """Test retrieving default templates"""
        template = self.template_manager.get_template('general_treatment')
        
        self.assertIsNotNone(template)
        self.assertEqual(template['name'], 'General Treatment Consent')
        self.assertIn('treatment', template['category'])
    
    def test_create_consent_from_template(self):
        """Test creating consent from template"""
        consent_data = self.template_manager.create_consent_from_template(
            'general_treatment', 'patient123'
        )
        
        self.assertIn('category', consent_data)
        self.assertIn('provisions', consent_data)
        self.assertIn('effective_date', consent_data)
    
    def test_create_consent_from_template_with_customizations(self):
        """Test creating consent from template with customizations"""
        customizations = {
            'expiry_date': datetime.datetime.utcnow() + datetime.timedelta(days=365)
        }
        
        consent_data = self.template_manager.create_consent_from_template(
            'general_treatment', 'patient123', customizations
        )
        
        self.assertIn('expiry_date', consent_data)
        self.assertIsInstance(consent_data['expiry_date'], datetime.datetime)
    
    def test_invalid_template_id(self):
        """Test error handling for invalid template ID"""
        with self.assertRaises(ValueError):
            self.template_manager.create_consent_from_template(
                'nonexistent_template', 'patient123'
            )


if __name__ == '__main__':
    unittest.main()