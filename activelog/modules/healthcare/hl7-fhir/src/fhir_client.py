"""
HL7 FHIR Data Integration Module
Provides integration with FHIR-compliant healthcare systems.
"""
import json
import datetime
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from urllib.parse import urljoin, urlencode
import uuid


class FHIRResourceType(Enum):
    """FHIR Resource Types"""
    PATIENT = "Patient"
    OBSERVATION = "Observation"
    CONDITION = "Condition"
    MEDICATION_REQUEST = "MedicationRequest"
    DIAGNOSTIC_REPORT = "DiagnosticReport"
    ENCOUNTER = "Encounter"
    PRACTITIONER = "Practitioner"
    ORGANIZATION = "Organization"
    ALLERGY_INTOLERANCE = "AllergyIntolerance"
    IMMUNIZATION = "Immunization"


class FHIRVersion(Enum):
    """Supported FHIR Versions"""
    R4 = "4.0.1"
    R5 = "5.0.0"


@dataclass
class FHIRPatient:
    """FHIR Patient resource structure"""
    id: Optional[str] = None
    identifier: Optional[List[Dict]] = None
    active: bool = True
    name: Optional[List[Dict]] = None
    telecom: Optional[List[Dict]] = None
    gender: Optional[str] = None
    birthDate: Optional[str] = None
    address: Optional[List[Dict]] = None
    maritalStatus: Optional[Dict] = None
    contact: Optional[List[Dict]] = None
    generalPractitioner: Optional[List[Dict]] = None
    managingOrganization: Optional[Dict] = None


@dataclass
class FHIRObservation:
    """FHIR Observation resource structure"""
    id: Optional[str] = None
    status: str = "final"
    category: Optional[List[Dict]] = None
    code: Optional[Dict] = None
    subject: Optional[Dict] = None
    encounter: Optional[Dict] = None
    effectiveDateTime: Optional[str] = None
    issued: Optional[str] = None
    performer: Optional[List[Dict]] = None
    valueQuantity: Optional[Dict] = None
    valueString: Optional[str] = None
    valueBoolean: Optional[bool] = None
    interpretation: Optional[List[Dict]] = None
    note: Optional[List[Dict]] = None
    component: Optional[List[Dict]] = None


class FHIRClient:
    """FHIR-compliant client for healthcare data integration"""
    
    def __init__(self, base_url: str, version: FHIRVersion = FHIRVersion.R4, 
                 auth_token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.version = version
        self.auth_token = auth_token
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            'Accept': f'application/fhir+json; fhirVersion={version.value}',
            'Content-Type': 'application/fhir+json'
        })
        
        if auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {auth_token}'
            })
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                     params: Optional[Dict] = None) -> requests.Response:
        """Make HTTP request to FHIR server"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                timeout=30
            )
            
            # Log the request for audit
            logging.info(f"FHIR {method} request to {url}, status: {response.status_code}")
            
            return response
            
        except requests.exceptions.RequestException as e:
            logging.error(f"FHIR request failed: {str(e)}")
            raise
    
    def get_capability_statement(self) -> Optional[Dict]:
        """Get FHIR server capability statement"""
        response = self._make_request('GET', 'metadata')
        if response.status_code == 200:
            return response.json()
        return None
    
    def search_patients(self, search_params: Dict[str, str]) -> List[Dict]:
        """Search for patients using FHIR search parameters"""
        response = self._make_request('GET', 'Patient', params=search_params)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('resourceType') == 'Bundle':
                return [entry['resource'] for entry in bundle.get('entry', [])]
        
        return []
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """Get specific patient by ID"""
        response = self._make_request('GET', f'Patient/{patient_id}')
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def create_patient(self, patient: FHIRPatient) -> Optional[str]:
        """Create new patient resource"""
        patient_data = {
            'resourceType': 'Patient',
            **{k: v for k, v in asdict(patient).items() if v is not None}
        }
        
        response = self._make_request('POST', 'Patient', data=patient_data)
        
        if response.status_code == 201:
            created_patient = response.json()
            return created_patient.get('id')
        
        return None
    
    def update_patient(self, patient_id: str, patient: FHIRPatient) -> bool:
        """Update existing patient resource"""
        patient_data = {
            'resourceType': 'Patient',
            'id': patient_id,
            **{k: v for k, v in asdict(patient).items() if v is not None}
        }
        
        response = self._make_request('PUT', f'Patient/{patient_id}', data=patient_data)
        return response.status_code == 200
    
    def delete_patient(self, patient_id: str) -> bool:
        """Delete patient resource"""
        response = self._make_request('DELETE', f'Patient/{patient_id}')
        return response.status_code == 204
    
    def get_patient_observations(self, patient_id: str, 
                               observation_code: Optional[str] = None) -> List[Dict]:
        """Get observations for a patient"""
        params = {'subject': f'Patient/{patient_id}'}
        if observation_code:
            params['code'] = observation_code
        
        response = self._make_request('GET', 'Observation', params=params)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('resourceType') == 'Bundle':
                return [entry['resource'] for entry in bundle.get('entry', [])]
        
        return []
    
    def create_observation(self, observation: FHIRObservation) -> Optional[str]:
        """Create new observation resource"""
        observation_data = {
            'resourceType': 'Observation',
            **{k: v for k, v in asdict(observation).items() if v is not None}
        }
        
        response = self._make_request('POST', 'Observation', data=observation_data)
        
        if response.status_code == 201:
            created_obs = response.json()
            return created_obs.get('id')
        
        return None
    
    def search_by_resource_type(self, resource_type: FHIRResourceType, 
                               search_params: Dict[str, str]) -> List[Dict]:
        """Generic search by resource type"""
        response = self._make_request('GET', resource_type.value, params=search_params)
        
        if response.status_code == 200:
            bundle = response.json()
            if bundle.get('resourceType') == 'Bundle':
                return [entry['resource'] for entry in bundle.get('entry', [])]
        
        return []
    
    def batch_operation(self, bundle: Dict) -> Optional[Dict]:
        """Execute FHIR batch operation"""
        response = self._make_request('POST', '', data=bundle)
        
        if response.status_code == 200:
            return response.json()
        
        return None


class HL7MessageParser:
    """Parser for HL7 v2 messages"""
    
    def __init__(self):
        self.field_separator = '|'
        self.component_separator = '^'
        self.repetition_separator = '~'
        self.escape_character = '\\'
        self.subcomponent_separator = '&'
    
    def parse_message(self, hl7_message: str) -> Dict[str, Any]:
        """Parse HL7 v2 message into structured format"""
        lines = hl7_message.strip().split('\n')
        parsed = {
            'message_header': None,
            'segments': [],
            'message_type': None
        }
        
        for line in lines:
            if line.startswith('MSH'):
                parsed['message_header'] = self._parse_msh_segment(line)
                parsed['message_type'] = self._extract_message_type(line)
            else:
                segment = self._parse_segment(line)
                if segment:
                    parsed['segments'].append(segment)
        
        return parsed
    
    def _parse_msh_segment(self, msh_line: str) -> Dict[str, Any]:
        """Parse MSH (Message Header) segment"""
        fields = msh_line.split(self.field_separator)
        
        return {
            'segment_type': 'MSH',
            'field_separator': fields[1] if len(fields) > 1 else '',
            'encoding_characters': fields[2] if len(fields) > 2 else '',
            'sending_application': fields[3] if len(fields) > 3 else '',
            'sending_facility': fields[4] if len(fields) > 4 else '',
            'receiving_application': fields[5] if len(fields) > 5 else '',
            'receiving_facility': fields[6] if len(fields) > 6 else '',
            'timestamp': fields[7] if len(fields) > 7 else '',
            'message_type': fields[9] if len(fields) > 9 else '',
            'message_control_id': fields[10] if len(fields) > 10 else '',
            'processing_id': fields[11] if len(fields) > 11 else '',
            'version_id': fields[12] if len(fields) > 12 else ''
        }
    
    def _parse_segment(self, segment_line: str) -> Optional[Dict[str, Any]]:
        """Parse generic HL7 segment"""
        if len(segment_line) < 3:
            return None
        
        segment_type = segment_line[:3]
        fields = segment_line.split(self.field_separator)
        
        return {
            'segment_type': segment_type,
            'fields': fields[1:] if len(fields) > 1 else []
        }
    
    def _extract_message_type(self, msh_line: str) -> Optional[str]:
        """Extract message type from MSH segment"""
        fields = msh_line.split(self.field_separator)
        if len(fields) > 9:
            message_type_field = fields[9]
            # Message type is typically in format: ADT^A01^ADT_A01
            return message_type_field.split(self.component_separator)[0]
        return None


class FHIRToHL7Converter:
    """Convert between FHIR and HL7 v2 formats"""
    
    def __init__(self):
        self.hl7_parser = HL7MessageParser()
    
    def fhir_patient_to_hl7_pid(self, fhir_patient: Dict) -> str:
        """Convert FHIR Patient to HL7 PID segment"""
        pid_fields = ['PID']  # Segment ID
        
        # PID-1: Set ID
        pid_fields.append('1')
        
        # PID-2: Patient ID (External ID)
        pid_fields.append('')
        
        # PID-3: Patient Identifier List
        identifiers = fhir_patient.get('identifier', [])
        if identifiers:
            # Use first identifier
            identifier = identifiers[0]
            pid_fields.append(identifier.get('value', ''))
        else:
            pid_fields.append('')
        
        # PID-4: Alternate Patient ID
        pid_fields.append('')
        
        # PID-5: Patient Name
        names = fhir_patient.get('name', [])
        if names:
            name = names[0]
            family = name.get('family', '')
            given = ' '.join(name.get('given', []))
            pid_fields.append(f"{family}^{given}")
        else:
            pid_fields.append('')
        
        # PID-6: Mother's Maiden Name
        pid_fields.append('')
        
        # PID-7: Date/Time of Birth
        birth_date = fhir_patient.get('birthDate', '')
        if birth_date:
            # Convert FHIR date format to HL7 format
            pid_fields.append(birth_date.replace('-', ''))
        else:
            pid_fields.append('')
        
        # PID-8: Administrative Sex
        gender_map = {'male': 'M', 'female': 'F', 'other': 'O', 'unknown': 'U'}
        gender = fhir_patient.get('gender', '')
        pid_fields.append(gender_map.get(gender, ''))
        
        return '|'.join(pid_fields)
    
    def hl7_pid_to_fhir_patient(self, pid_segment: str) -> Dict:
        """Convert HL7 PID segment to FHIR Patient"""
        fields = pid_segment.split('|')
        
        patient = {
            'resourceType': 'Patient',
            'id': str(uuid.uuid4())
        }
        
        # Patient identifier
        if len(fields) > 3 and fields[3]:
            patient['identifier'] = [{
                'use': 'usual',
                'value': fields[3]
            }]
        
        # Patient name
        if len(fields) > 5 and fields[5]:
            name_parts = fields[5].split('^')
            patient['name'] = [{
                'use': 'official',
                'family': name_parts[0] if len(name_parts) > 0 else '',
                'given': name_parts[1].split(' ') if len(name_parts) > 1 else []
            }]
        
        # Birth date
        if len(fields) > 7 and fields[7]:
            birth_date = fields[7]
            # Convert HL7 date format (YYYYMMDD) to FHIR format (YYYY-MM-DD)
            if len(birth_date) == 8:
                formatted_date = f"{birth_date[:4]}-{birth_date[4:6]}-{birth_date[6:8]}"
                patient['birthDate'] = formatted_date
        
        # Gender
        if len(fields) > 8 and fields[8]:
            gender_map = {'M': 'male', 'F': 'female', 'O': 'other', 'U': 'unknown'}
            patient['gender'] = gender_map.get(fields[8], 'unknown')
        
        return patient


class FHIRBundleBuilder:
    """Build FHIR Bundle resources for batch operations"""
    
    def __init__(self, bundle_type: str = 'batch'):
        self.bundle = {
            'resourceType': 'Bundle',
            'id': str(uuid.uuid4()),
            'type': bundle_type,
            'entry': []
        }
    
    def add_resource(self, resource: Dict, request_method: str = 'POST',
                    request_url: Optional[str] = None):
        """Add resource to bundle"""
        entry = {
            'resource': resource,
            'request': {
                'method': request_method,
                'url': request_url or resource['resourceType']
            }
        }
        
        self.bundle['entry'].append(entry)
    
    def add_patient_create(self, patient: FHIRPatient):
        """Add patient creation to bundle"""
        patient_resource = {
            'resourceType': 'Patient',
            **{k: v for k, v in asdict(patient).items() if v is not None}
        }
        self.add_resource(patient_resource, 'POST', 'Patient')
    
    def add_observation_create(self, observation: FHIRObservation):
        """Add observation creation to bundle"""
        observation_resource = {
            'resourceType': 'Observation',
            **{k: v for k, v in asdict(observation).items() if v is not None}
        }
        self.add_resource(observation_resource, 'POST', 'Observation')
    
    def get_bundle(self) -> Dict:
        """Get the completed bundle"""
        return self.bundle


class FHIRValidator:
    """Validate FHIR resources against specifications"""
    
    def __init__(self):
        self.required_fields = {
            'Patient': ['resourceType'],
            'Observation': ['resourceType', 'status', 'code', 'subject']
        }
    
    def validate_resource(self, resource: Dict) -> List[str]:
        """Validate FHIR resource and return list of errors"""
        errors = []
        
        resource_type = resource.get('resourceType')
        if not resource_type:
            errors.append('Missing required field: resourceType')
            return errors
        
        if resource_type in self.required_fields:
            for field in self.required_fields[resource_type]:
                if field not in resource or resource[field] is None:
                    errors.append(f'Missing required field: {field}')
        
        # Validate specific resource types
        if resource_type == 'Patient':
            errors.extend(self._validate_patient(resource))
        elif resource_type == 'Observation':
            errors.extend(self._validate_observation(resource))
        
        return errors
    
    def _validate_patient(self, patient: Dict) -> List[str]:
        """Validate Patient resource"""
        errors = []
        
        # Check identifier format
        identifiers = patient.get('identifier', [])
        for identifier in identifiers:
            if 'value' not in identifier:
                errors.append('Patient identifier missing value')
        
        # Check name format
        names = patient.get('name', [])
        for name in names:
            if 'family' not in name and 'given' not in name:
                errors.append('Patient name must have family or given name')
        
        return errors
    
    def _validate_observation(self, observation: Dict) -> List[str]:
        """Validate Observation resource"""
        errors = []
        
        # Check status values
        valid_statuses = ['registered', 'preliminary', 'final', 'amended', 'corrected', 'cancelled', 'entered-in-error', 'unknown']
        status = observation.get('status')
        if status not in valid_statuses:
            errors.append(f'Invalid observation status: {status}')
        
        # Check subject reference
        subject = observation.get('subject')
        if subject and not isinstance(subject, dict):
            errors.append('Observation subject must be a reference object')
        
        return errors