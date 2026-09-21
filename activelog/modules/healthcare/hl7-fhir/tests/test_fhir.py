"""
Tests for HL7/FHIR data integration module
"""
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from ..src.fhir_client import (
    FHIRClient, FHIRPatient, FHIRObservation, FHIRVersion,
    HL7MessageParser, FHIRToHL7Converter, FHIRBundleBuilder, FHIRValidator
)


class TestFHIRClient(unittest.TestCase):
    
    def setUp(self):
        self.client = FHIRClient('http://test-fhir-server.com', auth_token='test_token')
    
    def test_client_initialization(self):
        """Test FHIR client initialization"""
        self.assertEqual(self.client.base_url, 'http://test-fhir-server.com')
        self.assertEqual(self.client.version, FHIRVersion.R4)
        self.assertIn('Authorization', self.client.session.headers)
    
    @patch('requests.Session.request')
    def test_get_capability_statement(self, mock_request):
        """Test capability statement retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'resourceType': 'CapabilityStatement'}
        mock_request.return_value = mock_response
        
        capability = self.client.get_capability_statement()
        
        self.assertIsNotNone(capability)
        self.assertEqual(capability['resourceType'], 'CapabilityStatement')
    
    @patch('requests.Session.request')
    def test_search_patients(self, mock_request):
        """Test patient search functionality"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'resourceType': 'Bundle',
            'entry': [
                {'resource': {'resourceType': 'Patient', 'id': '123'}},
                {'resource': {'resourceType': 'Patient', 'id': '456'}}
            ]
        }
        mock_request.return_value = mock_response
        
        results = self.client.search_patients({'name': 'John'})
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['id'], '123')
    
    @patch('requests.Session.request')
    def test_create_patient(self, mock_request):
        """Test patient creation"""
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {'id': 'new_patient_123'}
        mock_request.return_value = mock_response
        
        patient = FHIRPatient(
            name=[{'family': 'Doe', 'given': ['John']}],
            gender='male',
            birthDate='1990-01-01'
        )
        
        patient_id = self.client.create_patient(patient)
        
        self.assertEqual(patient_id, 'new_patient_123')
    
    @patch('requests.Session.request')
    def test_get_patient_observations(self, mock_request):
        """Test retrieving patient observations"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'resourceType': 'Bundle',
            'entry': [
                {'resource': {'resourceType': 'Observation', 'id': 'obs1'}},
                {'resource': {'resourceType': 'Observation', 'id': 'obs2'}}
            ]
        }
        mock_request.return_value = mock_response
        
        observations = self.client.get_patient_observations('patient123')
        
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0]['id'], 'obs1')


class TestHL7MessageParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = HL7MessageParser()
    
    def test_parse_msh_segment(self):
        """Test MSH segment parsing"""
        msh_line = "MSH|^~\\&|SENDING_APP|SENDING_FAC|RECEIVING_APP|RECEIVING_FAC|20240101120000||ADT^A01^ADT_A01|MSG123|P|2.5"
        
        msh = self.parser._parse_msh_segment(msh_line)
        
        self.assertEqual(msh['segment_type'], 'MSH')
        self.assertEqual(msh['sending_application'], 'SENDING_APP')
        self.assertEqual(msh['message_control_id'], 'MSG123')
        self.assertEqual(msh['version_id'], '2.5')
    
    def test_parse_message(self):
        """Test complete HL7 message parsing"""
        hl7_message = """MSH|^~\\&|SENDING|FACILITY|RECEIVING|FACILITY|20240101120000||ADT^A01|123|P|2.5
PID|1||12345^^^HOSPITAL^MR||DOE^JOHN^||19900101|M|||123 MAIN ST^ANYTOWN^ST^12345||(555)555-5555"""
        
        parsed = self.parser.parse_message(hl7_message)
        
        self.assertIsNotNone(parsed['message_header'])
        self.assertEqual(parsed['message_type'], 'ADT')
        self.assertEqual(len(parsed['segments']), 1)
        self.assertEqual(parsed['segments'][0]['segment_type'], 'PID')


class TestFHIRToHL7Converter(unittest.TestCase):
    
    def setUp(self):
        self.converter = FHIRToHL7Converter()
    
    def test_fhir_patient_to_hl7_pid(self):
        """Test FHIR Patient to HL7 PID conversion"""
        fhir_patient = {
            'resourceType': 'Patient',
            'identifier': [{'value': '12345'}],
            'name': [{'family': 'Doe', 'given': ['John', 'Middle']}],
            'gender': 'male',
            'birthDate': '1990-01-01'
        }
        
        pid_segment = self.converter.fhir_patient_to_hl7_pid(fhir_patient)
        
        self.assertIn('PID', pid_segment)
        self.assertIn('12345', pid_segment)
        self.assertIn('Doe^John Middle', pid_segment)
        self.assertIn('19900101', pid_segment)  # Date format conversion
        self.assertIn('M', pid_segment)  # Gender conversion
    
    def test_hl7_pid_to_fhir_patient(self):
        """Test HL7 PID to FHIR Patient conversion"""
        pid_segment = "PID|1||12345|||DOE^JOHN^||19900101|M"
        
        fhir_patient = self.converter.hl7_pid_to_fhir_patient(pid_segment)
        
        self.assertEqual(fhir_patient['resourceType'], 'Patient')
        self.assertEqual(fhir_patient['identifier'][0]['value'], '12345')
        self.assertEqual(fhir_patient['name'][0]['family'], 'DOE')
        self.assertEqual(fhir_patient['name'][0]['given'], ['JOHN'])
        self.assertEqual(fhir_patient['gender'], 'male')
        self.assertEqual(fhir_patient['birthDate'], '1990-01-01')


class TestFHIRBundleBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = FHIRBundleBuilder()
    
    def test_bundle_initialization(self):
        """Test bundle builder initialization"""
        bundle = self.builder.get_bundle()
        
        self.assertEqual(bundle['resourceType'], 'Bundle')
        self.assertEqual(bundle['type'], 'batch')
        self.assertEqual(len(bundle['entry']), 0)
    
    def test_add_patient_create(self):
        """Test adding patient creation to bundle"""
        patient = FHIRPatient(
            name=[{'family': 'Doe', 'given': ['John']}],
            gender='male'
        )
        
        self.builder.add_patient_create(patient)
        bundle = self.builder.get_bundle()
        
        self.assertEqual(len(bundle['entry']), 1)
        entry = bundle['entry'][0]
        self.assertEqual(entry['resource']['resourceType'], 'Patient')
        self.assertEqual(entry['request']['method'], 'POST')
    
    def test_add_observation_create(self):
        """Test adding observation creation to bundle"""
        observation = FHIRObservation(
            status='final',
            code={'coding': [{'code': 'vital-signs'}]},
            subject={'reference': 'Patient/123'}
        )
        
        self.builder.add_observation_create(observation)
        bundle = self.builder.get_bundle()
        
        self.assertEqual(len(bundle['entry']), 1)
        entry = bundle['entry'][0]
        self.assertEqual(entry['resource']['resourceType'], 'Observation')
        self.assertEqual(entry['request']['method'], 'POST')


class TestFHIRValidator(unittest.TestCase):
    
    def setUp(self):
        self.validator = FHIRValidator()
    
    def test_validate_valid_patient(self):
        """Test validation of valid patient resource"""
        patient = {
            'resourceType': 'Patient',
            'identifier': [{'value': '12345'}],
            'name': [{'family': 'Doe', 'given': ['John']}]
        }
        
        errors = self.validator.validate_resource(patient)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_invalid_patient(self):
        """Test validation of invalid patient resource"""
        patient = {
            'resourceType': 'Patient',
            'identifier': [{}],  # Missing value
            'name': [{}]  # Missing family and given
        }
        
        errors = self.validator.validate_resource(patient)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('identifier missing value' in error for error in errors))
        self.assertTrue(any('name must have family or given' in error for error in errors))
    
    def test_validate_valid_observation(self):
        """Test validation of valid observation resource"""
        observation = {
            'resourceType': 'Observation',
            'status': 'final',
            'code': {'coding': [{'code': 'vital-signs'}]},
            'subject': {'reference': 'Patient/123'}
        }
        
        errors = self.validator.validate_resource(observation)
        
        self.assertEqual(len(errors), 0)
    
    def test_validate_invalid_observation(self):
        """Test validation of invalid observation resource"""
        observation = {
            'resourceType': 'Observation',
            'status': 'invalid_status',  # Invalid status
            'code': {'coding': [{'code': 'vital-signs'}]},
            'subject': 'not_a_reference'  # Should be object
        }
        
        errors = self.validator.validate_resource(observation)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any('Invalid observation status' in error for error in errors))
        self.assertTrue(any('subject must be a reference object' in error for error in errors))
    
    def test_validate_missing_resource_type(self):
        """Test validation when resourceType is missing"""
        resource = {'id': '123'}
        
        errors = self.validator.validate_resource(resource)
        
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0], 'Missing required field: resourceType')


if __name__ == '__main__':
    unittest.main()