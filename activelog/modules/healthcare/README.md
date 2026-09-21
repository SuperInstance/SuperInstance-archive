# Healthcare Modules

A comprehensive suite of healthcare-focused modules designed for secure, HIPAA-compliant medical data processing and integration.

## Overview

This healthcare module collection provides essential components for building secure healthcare applications with full compliance frameworks, medical data processing capabilities, and integration with standard healthcare protocols.

## Modules

### 1. HIPAA Compliance Framework (`hipaa/`)

**Purpose**: Ensures HIPAA compliance for healthcare applications through comprehensive privacy and security controls.

**Key Features**:
- PHI (Protected Health Information) encryption and de-identification
- Access control with minimum necessary principle
- Breach detection and notification management
- Business Associate Agreement (BAA) compliance
- Data retention policy enforcement
- Audit logging for compliance reporting

**Main Classes**:
- `HIPAACompliance`: Core compliance framework
- `DataRetentionManager`: Manages data retention policies
- `BusinessAssociateAgreement`: BAA compliance management

**Example Usage**:
```python
from modules.healthcare.hipaa.src.compliance import HIPAACompliance

compliance = HIPAACompliance()

# Encrypt PHI
encrypted_ssn = compliance.encrypt_phi("123-45-6789")

# Validate access
access_decision = compliance.validate_access(
    user_role="doctor", 
    requested_fields=["name", "diagnosis"], 
    purpose=AccessLevel.TREATMENT
)

# De-identify data
de_identified = compliance.de_identify_data({
    "name": "John Doe",
    "ssn": "123-45-6789",
    "diagnosis": "Diabetes"
})
```

### 2. DICOM Image Support (`dicom/`)

**Purpose**: Handles DICOM medical imaging files with security and anonymization features.

**Key Features**:
- DICOM file loading, validation, and processing
- Image anonymization and PHI removal
- Metadata extraction and indexing
- Image format conversion (DICOM to PNG/JPEG)
- Batch processing capabilities
- Secure storage with patient directory organization

**Main Classes**:
- `DICOMProcessor`: Main processing engine
- `DICOMSecurity`: Security and anonymization utilities
- `DICOMStorage`: Secure storage management

**Example Usage**:
```python
from modules.healthcare.dicom.src.dicom_handler import DICOMProcessor

processor = DICOMProcessor()

# Load and process DICOM file
dataset = processor.load_dicom_file("patient_scan.dcm")
metadata = processor.extract_metadata(dataset)

# Anonymize DICOM
processor.anonymize_dicom("input.dcm", "anonymized.dcm")

# Convert to standard image format
image_bytes = processor.convert_to_image(dataset, "PNG")
```

### 3. HL7/FHIR Data Integration (`hl7-fhir/`)

**Purpose**: Provides integration with FHIR-compliant healthcare systems and HL7 v2 message processing.

**Key Features**:
- FHIR R4/R5 client implementation
- Patient, Observation, and Condition resource management
- HL7 v2 message parsing and conversion
- FHIR bundle operations for batch processing
- Resource validation against FHIR specifications
- Bidirectional HL7 ↔ FHIR conversion

**Main Classes**:
- `FHIRClient`: FHIR server communication
- `HL7MessageParser`: HL7 v2 message processing
- `FHIRToHL7Converter`: Format conversion utilities
- `FHIRValidator`: Resource validation

**Example Usage**:
```python
from modules.healthcare.hl7_fhir.src.fhir_client import FHIRClient, FHIRPatient

client = FHIRClient("https://fhir-server.example.com")

# Create patient
patient = FHIRPatient(
    name=[{"family": "Doe", "given": ["John"]}],
    gender="male",
    birthDate="1990-01-01"
)
patient_id = client.create_patient(patient)

# Search patients
results = client.search_patients({"name": "John Doe"})
```

### 4. Patient Consent Management (`consent/`)

**Purpose**: Comprehensive consent management system for healthcare data access and sharing.

**Key Features**:
- Granular consent tracking with multiple provision types
- Purpose-based access control (treatment, payment, operations, research)
- Special category data protection (mental health, substance abuse)
- Consent templates for common scenarios
- Consent withdrawal and expiration handling
- Audit trail for all consent actions

**Main Classes**:
- `ConsentManager`: Core consent management
- `ConsentValidator`: Consent record validation
- `ConsentTemplateManager`: Pre-defined consent templates

**Example Usage**:
```python
from modules.healthcare.consent.src.consent_manager import ConsentManager

manager = ConsentManager()

# Create consent
consent_data = {
    'status': 'active',
    'scope': 'general',
    'category': ['treatment', 'payment'],
    'provisions': [{
        'type': 'permit',
        'purpose': ['treatment'],
        'data_categories': ['demographics', 'clinical_notes'],
        'actors': []
    }]
}

consent_id = manager.create_consent('patient123', consent_data)

# Check access permission
permission = manager.check_access_permission(
    'patient123', 'doctor1', ConsentType.TREATMENT, 
    [DataCategory.CLINICAL_NOTES]
)
```

### 5. Audit Trails for Compliance (`audit/`)

**Purpose**: Comprehensive audit logging system for HIPAA compliance and security monitoring.

**Key Features**:
- Detailed audit event logging with encryption
- Compliance-specific event types (PHI access, disclosures)
- Automated retention policy management
- Security incident tracking and reporting
- User activity analysis and anomaly detection
- Compliance report generation

**Main Classes**:
- `AuditTrail`: Main audit system
- `AuditStorage`: Persistent audit log storage
- `AuditAnalyzer`: Pattern analysis and anomaly detection

**Example Usage**:
```python
from modules.healthcare.audit.src.audit_trail import AuditTrail, AuditUser, AuditableResource

audit = AuditTrail()

# Log data access
user = AuditUser(user_id="doctor1", user_type="provider")
resource = AuditableResource(
    resource_type="Patient", 
    resource_id="123", 
    patient_id="patient123"
)

audit.log_data_access(user, resource, ip_address="192.168.1.100")

# Generate compliance report
report = audit.generate_compliance_report(
    start_date=datetime.datetime(2024, 1, 1),
    end_date=datetime.datetime(2024, 12, 31)
)
```

### 6. Medical Device Integration APIs (`device-api/`)

**Purpose**: Secure integration framework for medical devices and IoT sensors with real-time monitoring.

**Key Features**:
- Multi-protocol support (HL7, MQTT, custom protocols)
- Real-time device monitoring and data collection
- Medical alarm detection and management
- Device status tracking and health monitoring
- Data validation and normalization
- Batch device management capabilities

**Main Classes**:
- `DeviceManager`: Central device management
- `HL7DeviceProtocol`: HL7-based device communication
- `MQTTDeviceProtocol`: MQTT/IoT device integration
- `DeviceDataProcessor`: Data validation and processing

**Example Usage**:
```python
from modules.healthcare.device_api.src.device_integration import DeviceManager, DeviceInfo, DeviceType

manager = DeviceManager()

# Register device
device = DeviceInfo(
    device_id="monitor_001",
    device_type=DeviceType.VITAL_SIGNS_MONITOR,
    manufacturer="MedTech",
    model="VM-2000",
    serial_number="SN123456",
    firmware_version="1.2.3"
)

manager.register_device(device, 'hl7')

# Connect and monitor
await manager.connect_device("monitor_001", 'hl7')
manager.start_monitoring()

# Get device readings
readings = manager.get_device_readings("monitor_001")
```

### 7. Clinical Notes NLP Processing (`nlp/`)

**Purpose**: Natural language processing for clinical documentation and medical text analysis.

**Key Features**:
- Medical entity extraction (medications, conditions, procedures)
- Clinical concept normalization to standard vocabularies
- Sentiment and uncertainty analysis for clinical text
- Medication regimen extraction and tracking
- Clinical trend identification across multiple notes
- Batch processing for large document sets

**Main Classes**:
- `ClinicalNLPProcessor`: Main NLP processing pipeline
- `ClinicalEntityExtractor`: Medical entity extraction
- `ClinicalSentimentAnalyzer`: Sentiment and uncertainty analysis
- `MedicalTerminologyMatcher`: Terminology normalization

**Example Usage**:
```python
from modules.healthcare.nlp.src.clinical_nlp import ClinicalNLPProcessor, NoteType

processor = ClinicalNLPProcessor()

# Process clinical note
text = """
Patient presents with diabetes and hypertension. 
Currently taking metformin 500mg twice daily.
Patient reports feeling much better overall.
"""

result = processor.process_clinical_note(text, NoteType.PROGRESS_NOTE, "patient123")

# Extract medications
medications = processor.extract_medication_regimen([result])

# Generate summary
summary = processor.generate_summary_report([result])
```

## Security and Compliance

All modules are designed with healthcare security requirements in mind:

- **HIPAA Compliance**: Built-in PHI protection and audit logging
- **Encryption**: Sensitive data encryption at rest and in transit
- **Access Control**: Role-based access with minimum necessary principles
- **Audit Trails**: Comprehensive logging for compliance reporting
- **Data De-identification**: Tools for removing or obscuring PHI
- **Secure Storage**: Patient data organized with proper access controls

## Dependencies

Core dependencies for the healthcare modules:

```bash
# Required packages
pip install cryptography  # For encryption
pip install requests      # For FHIR/HTTP communication
pip install pydicom       # For DICOM processing
pip install pillow        # For image processing
pip install numpy         # For medical data processing

# Optional packages
pip install paho-mqtt     # For MQTT device integration
pip install asyncio       # For async device communication
```

## Testing

Each module includes comprehensive test suites:

```bash
# Run all healthcare module tests
python -m pytest modules/healthcare/

# Run specific module tests
python -m pytest modules/healthcare/hipaa/tests/
python -m pytest modules/healthcare/dicom/tests/
python -m pytest modules/healthcare/hl7-fhir/tests/
python -m pytest modules/healthcare/consent/tests/
python -m pytest modules/healthcare/audit/tests/
python -m pytest modules/healthcare/device-api/tests/
python -m pytest modules/healthcare/nlp/tests/
```

## Configuration

### Environment Variables

```bash
# HIPAA Compliance
HIPAA_ENCRYPTION_KEY=your_encryption_key_here
HIPAA_AUDIT_RETENTION_DAYS=2190  # 6 years

# FHIR Integration
FHIR_SERVER_URL=https://your-fhir-server.com
FHIR_AUTH_TOKEN=your_auth_token

# Device Integration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883

# Audit Storage
AUDIT_STORAGE_PATH=/path/to/audit/logs
AUDIT_ENCRYPTION_KEY=your_audit_encryption_key
```

## Integration Examples

### Complete Patient Data Pipeline

```python
from modules.healthcare.hipaa.src.compliance import HIPAACompliance
from modules.healthcare.consent.src.consent_manager import ConsentManager
from modules.healthcare.audit.src.audit_trail import AuditTrail
from modules.healthcare.hl7_fhir.src.fhir_client import FHIRClient

# Initialize systems
compliance = HIPAACompliance()
consent_manager = ConsentManager()
audit_trail = AuditTrail()
fhir_client = FHIRClient("https://fhir-server.com")

# Check consent before data access
user = AuditUser(user_id="doctor1", user_type="provider")
permission = consent_manager.check_access_permission(
    "patient123", "doctor1", ConsentType.TREATMENT, 
    [DataCategory.CLINICAL_NOTES]
)

if permission['permitted']:
    # Access permitted - retrieve data
    patient_data = fhir_client.get_patient("patient123")
    
    # Log the access
    audit_trail.log_data_access(user, resource, outcome=AuditOutcome.SUCCESS)
else:
    # Access denied - log the attempt
    audit_trail.log_data_access(user, resource, outcome=AuditOutcome.DENIED)
```

### Medical Device to FHIR Pipeline

```python
from modules.healthcare.device_api.src.device_integration import DeviceManager
from modules.healthcare.hl7_fhir.src.fhir_client import FHIRClient, FHIRObservation

device_manager = DeviceManager()
fhir_client = FHIRClient("https://fhir-server.com")

# Device data callback
def process_device_reading(reading):
    # Convert device reading to FHIR Observation
    observation = FHIRObservation(
        status="final",
        code={"coding": [{"code": reading.data_type.value}]},
        subject={"reference": f"Patient/{reading.patient_id}"},
        valueQuantity={
            "value": reading.value,
            "unit": reading.unit
        },
        effectiveDateTime=reading.timestamp.isoformat()
    )
    
    # Send to FHIR server
    fhir_client.create_observation(observation)

device_manager.add_data_callback(process_device_reading)
```

## Support and Documentation

For detailed API documentation and additional examples, refer to the individual module documentation within each subdirectory.

## License

This healthcare module collection is designed for educational and development purposes. Ensure proper validation and compliance review before using in production healthcare environments.