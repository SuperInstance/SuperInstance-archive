"""
DICOM Image Support Module
Handles DICOM medical imaging files with HIPAA compliance.
"""
import os
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import hashlib
import json

try:
    import pydicom
    from pydicom import Dataset
    from pydicom.errors import InvalidDicomError
except ImportError:
    pydicom = None
    Dataset = None
    InvalidDicomError = Exception

try:
    import numpy as np
    from PIL import Image
except ImportError:
    np = None
    Image = None


@dataclass
class DICOMMetadata:
    """DICOM file metadata structure"""
    patient_id: str
    study_instance_uid: str
    series_instance_uid: str
    sop_instance_uid: str
    modality: str
    study_date: str
    patient_name: Optional[str] = None
    patient_birth_date: Optional[str] = None
    institution_name: Optional[str] = None
    study_description: Optional[str] = None


class DICOMSecurity:
    """Security utilities for DICOM files"""
    
    @staticmethod
    def anonymize_dicom_tags(dataset: Dataset, keep_uids: bool = True) -> Dataset:
        """Remove or replace PHI from DICOM tags"""
        if not dataset:
            return dataset
        
        # Standard anonymization mapping
        anonymization_map = {
            'PatientName': 'ANONYMOUS',
            'PatientID': lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:16],
            'PatientBirthDate': '',
            'PatientSex': '',
            'PatientAge': '',
            'PatientWeight': '',
            'PatientAddress': '',
            'InstitutionName': 'ANONYMIZED',
            'InstitutionAddress': '',
            'ReferringPhysicianName': 'ANONYMIZED',
            'PerformingPhysicianName': 'ANONYMIZED',
            'OperatorName': 'ANONYMIZED',
            'StudyDescription': 'ANONYMIZED_STUDY',
            'SeriesDescription': 'ANONYMIZED_SERIES',
        }
        
        # Apply anonymization
        for tag, replacement in anonymization_map.items():
            if tag in dataset:
                if callable(replacement):
                    dataset[tag].value = replacement(dataset[tag].value)
                else:
                    dataset[tag].value = replacement
        
        # Keep study/series/instance UIDs if requested (for tracking)
        if not keep_uids:
            uid_tags = ['StudyInstanceUID', 'SeriesInstanceUID', 'SOPInstanceUID']
            for tag in uid_tags:
                if tag in dataset:
                    dataset[tag].value = pydicom.uid.generate_uid()
        
        return dataset
    
    @staticmethod
    def validate_dicom_integrity(file_path: str) -> Tuple[bool, str]:
        """Validate DICOM file integrity and structure"""
        try:
            dataset = pydicom.dcmread(file_path, stop_before_pixels=True)
            
            # Check required tags
            required_tags = ['SOPInstanceUID', 'StudyInstanceUID', 'SeriesInstanceUID']
            for tag in required_tags:
                if tag not in dataset:
                    return False, f"Missing required tag: {tag}"
            
            return True, "Valid DICOM file"
            
        except InvalidDicomError as e:
            return False, f"Invalid DICOM format: {str(e)}"
        except Exception as e:
            return False, f"Error reading DICOM: {str(e)}"


class DICOMProcessor:
    """Main DICOM processing class"""
    
    def __init__(self, temp_dir: str = "/tmp/dicom_processing"):
        if not pydicom:
            raise ImportError("pydicom library is required for DICOM processing")
        
        self.temp_dir = temp_dir
        os.makedirs(temp_dir, exist_ok=True)
        self.processing_log = []
    
    def load_dicom_file(self, file_path: str) -> Optional[Dataset]:
        """Load and validate DICOM file"""
        try:
            # Validate file integrity first
            is_valid, message = DICOMSecurity.validate_dicom_integrity(file_path)
            if not is_valid:
                logging.error(f"DICOM validation failed: {message}")
                return None
            
            dataset = pydicom.dcmread(file_path)
            
            # Log access for audit
            self.processing_log.append({
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'action': 'load_dicom',
                'file_path': file_path,
                'patient_id': getattr(dataset, 'PatientID', 'Unknown'),
                'study_uid': getattr(dataset, 'StudyInstanceUID', 'Unknown')
            })
            
            return dataset
            
        except Exception as e:
            logging.error(f"Error loading DICOM file {file_path}: {str(e)}")
            return None
    
    def extract_metadata(self, dataset: Dataset) -> DICOMMetadata:
        """Extract metadata from DICOM dataset"""
        return DICOMMetadata(
            patient_id=getattr(dataset, 'PatientID', ''),
            study_instance_uid=getattr(dataset, 'StudyInstanceUID', ''),
            series_instance_uid=getattr(dataset, 'SeriesInstanceUID', ''),
            sop_instance_uid=getattr(dataset, 'SOPInstanceUID', ''),
            modality=getattr(dataset, 'Modality', ''),
            study_date=getattr(dataset, 'StudyDate', ''),
            patient_name=str(getattr(dataset, 'PatientName', '')),
            patient_birth_date=getattr(dataset, 'PatientBirthDate', ''),
            institution_name=getattr(dataset, 'InstitutionName', ''),
            study_description=getattr(dataset, 'StudyDescription', '')
        )
    
    def convert_to_image(self, dataset: Dataset, output_format: str = 'PNG') -> Optional[bytes]:
        """Convert DICOM to standard image format"""
        if not np or not Image:
            raise ImportError("numpy and PIL are required for image conversion")
        
        try:
            # Extract pixel data
            if 'PixelData' not in dataset:
                return None
            
            # Apply window/level for proper display
            pixel_array = dataset.pixel_array
            
            # Handle different bit depths
            if dataset.BitsAllocated == 16:
                # Apply window/level if available
                if hasattr(dataset, 'WindowCenter') and hasattr(dataset, 'WindowWidth'):
                    center = float(dataset.WindowCenter)
                    width = float(dataset.WindowWidth)
                    
                    # Apply windowing
                    img_min = center - width // 2
                    img_max = center + width // 2
                    pixel_array = np.clip(pixel_array, img_min, img_max)
                
                # Normalize to 8-bit
                pixel_array = ((pixel_array - pixel_array.min()) * 255.0 / 
                              (pixel_array.max() - pixel_array.min())).astype(np.uint8)
            
            # Create PIL image
            if len(pixel_array.shape) == 2:  # Grayscale
                image = Image.fromarray(pixel_array, mode='L')
            else:  # RGB
                image = Image.fromarray(pixel_array, mode='RGB')
            
            # Convert to bytes
            from io import BytesIO
            output = BytesIO()
            image.save(output, format=output_format)
            return output.getvalue()
            
        except Exception as e:
            logging.error(f"Error converting DICOM to image: {str(e)}")
            return None
    
    def anonymize_dicom(self, input_path: str, output_path: str, keep_uids: bool = True) -> bool:
        """Anonymize DICOM file by removing PHI"""
        try:
            dataset = self.load_dicom_file(input_path)
            if not dataset:
                return False
            
            # Anonymize
            anonymized_dataset = DICOMSecurity.anonymize_dicom_tags(dataset, keep_uids)
            
            # Save anonymized version
            anonymized_dataset.save_as(output_path)
            
            # Log the anonymization
            self.processing_log.append({
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'action': 'anonymize_dicom',
                'input_path': input_path,
                'output_path': output_path,
                'original_patient_id': getattr(dataset, 'PatientID', 'Unknown'),
                'anonymized_patient_id': getattr(anonymized_dataset, 'PatientID', 'Unknown')
            })
            
            return True
            
        except Exception as e:
            logging.error(f"Error anonymizing DICOM file: {str(e)}")
            return False
    
    def batch_process_dicom_directory(self, input_dir: str, output_dir: str, 
                                    anonymize: bool = True) -> Dict[str, Any]:
        """Process all DICOM files in a directory"""
        os.makedirs(output_dir, exist_ok=True)
        results = {
            'processed': 0,
            'failed': 0,
            'errors': [],
            'metadata': []
        }
        
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(('.dcm', '.dicom')):
                    input_path = os.path.join(root, file)
                    output_path = os.path.join(output_dir, f"processed_{file}")
                    
                    try:
                        if anonymize:
                            success = self.anonymize_dicom(input_path, output_path)
                        else:
                            # Just copy with validation
                            dataset = self.load_dicom_file(input_path)
                            if dataset:
                                dataset.save_as(output_path)
                                success = True
                            else:
                                success = False
                        
                        if success:
                            results['processed'] += 1
                            # Extract metadata for processed file
                            dataset = self.load_dicom_file(output_path)
                            if dataset:
                                metadata = self.extract_metadata(dataset)
                                results['metadata'].append(metadata.__dict__)
                        else:
                            results['failed'] += 1
                            results['errors'].append(f"Failed to process {input_path}")
                            
                    except Exception as e:
                        results['failed'] += 1
                        results['errors'].append(f"Error processing {input_path}: {str(e)}")
        
        return results
    
    def search_dicom_by_criteria(self, directory: str, criteria: Dict[str, str]) -> List[str]:
        """Search DICOM files by metadata criteria"""
        matching_files = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(('.dcm', '.dicom')):
                    file_path = os.path.join(root, file)
                    
                    try:
                        dataset = pydicom.dcmread(file_path, stop_before_pixels=True)
                        metadata = self.extract_metadata(dataset)
                        
                        # Check if file matches all criteria
                        matches = True
                        for key, value in criteria.items():
                            if hasattr(metadata, key):
                                if str(getattr(metadata, key)).lower() != str(value).lower():
                                    matches = False
                                    break
                            else:
                                matches = False
                                break
                        
                        if matches:
                            matching_files.append(file_path)
                            
                    except Exception as e:
                        logging.warning(f"Error reading DICOM file {file_path}: {str(e)}")
        
        return matching_files
    
    def generate_processing_report(self) -> Dict[str, Any]:
        """Generate report of all processing activities"""
        return {
            'total_operations': len(self.processing_log),
            'operations_by_type': {},
            'recent_operations': self.processing_log[-10:],  # Last 10 operations
            'generated_at': datetime.datetime.utcnow().isoformat()
        }


class DICOMStorage:
    """DICOM file storage management with HIPAA compliance"""
    
    def __init__(self, storage_root: str):
        self.storage_root = storage_root
        os.makedirs(storage_root, exist_ok=True)
    
    def store_dicom_secure(self, dataset: Dataset, patient_id: str, 
                          study_uid: str) -> str:
        """Store DICOM file in organized, secure structure"""
        # Create patient directory structure
        patient_dir = os.path.join(self.storage_root, 
                                  hashlib.sha256(patient_id.encode()).hexdigest()[:16])
        study_dir = os.path.join(patient_dir, study_uid.replace('.', '_'))
        os.makedirs(study_dir, exist_ok=True)
        
        # Generate secure filename
        filename = f"{dataset.SOPInstanceUID.replace('.', '_')}.dcm"
        file_path = os.path.join(study_dir, filename)
        
        # Save file
        dataset.save_as(file_path)
        
        # Set restrictive permissions
        os.chmod(file_path, 0o600)
        
        return file_path
    
    def create_storage_index(self) -> Dict[str, Any]:
        """Create index of stored DICOM files"""
        index = {}
        
        for patient_dir in os.listdir(self.storage_root):
            patient_path = os.path.join(self.storage_root, patient_dir)
            if os.path.isdir(patient_path):
                index[patient_dir] = {
                    'studies': [],
                    'total_files': 0
                }
                
                for study_dir in os.listdir(patient_path):
                    study_path = os.path.join(patient_path, study_dir)
                    if os.path.isdir(study_path):
                        file_count = len([f for f in os.listdir(study_path) 
                                        if f.endswith('.dcm')])
                        index[patient_dir]['studies'].append({
                            'study_uid': study_dir,
                            'file_count': file_count
                        })
                        index[patient_dir]['total_files'] += file_count
        
        return index