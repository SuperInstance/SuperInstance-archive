"""
DICOM Manager for medical image handling with HIPAA compliance
Supports DICOM file operations, metadata extraction, and secure storage
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4
import json

import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid
import numpy as np
from PIL import Image
import SimpleITK as sitk

from ..core.config import settings
from ..compliance.hipaa_manager import HIPAAManager, PHIClassification
from ..compliance.encryption_manager import EncryptionManager

logger = logging.getLogger(__name__)
security_logger = logging.getLogger("security")

class DICOMManager:
    def __init__(self):
        self.hipaa_manager = HIPAAManager()
        self.encryption_manager = EncryptionManager()
        self.storage_path = Path(settings.DICOM_STORAGE_PATH)
        self.temp_path = self.storage_path / "temp"
        self.anonymized_path = self.storage_path / "anonymized"
        
        # DICOM tag mappings for PHI classification
        self.phi_tags = {
            # Patient identification tags
            (0x0010, 0x0010): "patient_name",           # Patient's Name
            (0x0010, 0x0020): "patient_id",             # Patient ID
            (0x0010, 0x0030): "patient_birth_date",     # Patient's Birth Date
            (0x0010, 0x0040): "patient_sex",            # Patient's Sex
            (0x0010, 0x1000): "other_patient_ids",      # Other Patient IDs
            (0x0010, 0x1001): "other_patient_names",    # Other Patient Names
            (0x0010, 0x1010): "patient_age",            # Patient's Age
            (0x0010, 0x1030): "patient_weight",         # Patient's Weight
            (0x0010, 0x1040): "patient_address",        # Patient's Address
            (0x0010, 0x2154): "patient_telephone",      # Patient's Telephone Numbers
            
            # Study identification tags
            (0x0020, 0x000D): "study_instance_uid",     # Study Instance UID
            (0x0020, 0x0010): "study_id",               # Study ID
            (0x0008, 0x0020): "study_date",             # Study Date
            (0x0008, 0x0030): "study_time",             # Study Time
            (0x0008, 0x1030): "study_description",      # Study Description
            (0x0008, 0x0050): "accession_number",       # Accession Number
            
            # Series identification tags
            (0x0020, 0x000E): "series_instance_uid",    # Series Instance UID
            (0x0020, 0x0011): "series_number",          # Series Number
            (0x0008, 0x103E): "series_description",     # Series Description
            (0x0018, 0x0015): "body_part_examined",     # Body Part Examined
            
            # Equipment identification tags
            (0x0008, 0x0070): "manufacturer",           # Manufacturer
            (0x0008, 0x1090): "model_name",             # Manufacturer's Model Name
            (0x0018, 0x1000): "device_serial_number",   # Device Serial Number
            (0x0008, 0x1010): "station_name",           # Station Name
            
            # Institution tags
            (0x0008, 0x0080): "institution_name",       # Institution Name
            (0x0008, 0x0081): "institution_address",    # Institution Address
            (0x0008, 0x1040): "institution_department", # Institutional Department Name
            
            # Physician tags
            (0x0008, 0x0090): "referring_physician",    # Referring Physician's Name
            (0x0008, 0x1050): "performing_physician",   # Performing Physician's Name
            (0x0008, 0x1060): "reading_physician",      # Name of Physician(s) Reading Study
        }
        
    async def initialize(self):
        """Initialize DICOM manager"""
        logger.info("Initializing DICOM manager")
        
        # Create storage directories
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        self.anonymized_path.mkdir(parents=True, exist_ok=True)
        
        await self.hipaa_manager.initialize()
        await self.encryption_manager.initialize()
        
        logger.info("DICOM manager initialized")
        
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up DICOM manager")
        
        await self.hipaa_manager.cleanup()
        await self.encryption_manager.cleanup()
        
        # Cleanup temporary files
        await self._cleanup_temp_files()
        
    async def store_dicom_file(self, file_path: str, patient_id: str, 
                             user_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Store DICOM file with HIPAA compliance"""
        try:
            # Validate file
            validation_result = await self.validate_dicom_file(file_path)
            if not validation_result["is_valid"]:
                raise ValueError(f"Invalid DICOM file: {validation_result['error']}")
            
            # Read DICOM dataset
            dataset = pydicom.dcmread(file_path, force=True)
            
            # Extract metadata with PHI classification
            extracted_metadata = await self._extract_metadata(dataset)
            
            # Generate unique storage ID
            storage_id = str(uuid4())
            
            # Create storage structure
            storage_info = {
                "storage_id": storage_id,
                "original_filename": Path(file_path).name,
                "patient_id": patient_id,
                "modality": str(dataset.get("Modality", "UNKNOWN")),
                "study_date": str(dataset.get("StudyDate", "")),
                "series_description": str(dataset.get("SeriesDescription", "")),
                "stored_by": user_id,
                "storage_timestamp": datetime.now(timezone.utc).isoformat(),
                "file_size": os.path.getsize(file_path),
                "metadata": extracted_metadata,
                "phi_present": True,
                "encryption_applied": True
            }
            
            # Store original encrypted file
            encrypted_file_path = await self._store_encrypted_dicom(file_path, storage_id)
            storage_info["encrypted_file_path"] = str(encrypted_file_path)
            
            # Create anonymized version if enabled
            if settings.DICOM_ANONYMIZATION_ENABLED:
                anonymized_file_path = await self._create_anonymized_version(dataset, storage_id)
                storage_info["anonymized_file_path"] = str(anonymized_file_path)
            
            # Generate thumbnails for viewing
            thumbnail_paths = await self._generate_thumbnails(dataset, storage_id)
            storage_info["thumbnail_paths"] = thumbnail_paths
            
            # Store metadata
            metadata_file = self.storage_path / f"{storage_id}_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(storage_info, f, indent=2)
            
            # Log storage activity
            security_logger.info(
                f"DICOM file stored: storage_id={storage_id}, "
                f"patient_id={patient_id}, user_id={user_id}, "
                f"modality={storage_info['modality']}"
            )
            
            return storage_info
            
        except Exception as e:
            logger.error(f"Failed to store DICOM file: {e}")
            raise
            
    async def retrieve_dicom_file(self, storage_id: str, user_id: str, 
                                anonymized: bool = False) -> Dict[str, Any]:
        """Retrieve DICOM file with access control"""
        try:
            # Load metadata
            metadata_file = self.storage_path / f"{storage_id}_metadata.json"
            if not metadata_file.exists():
                raise FileNotFoundError(f"DICOM file not found: {storage_id}")
                
            with open(metadata_file, 'r') as f:
                storage_info = json.load(f)
            
            # Check access permissions
            access_check = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="medical_image",
                resource_id=storage_id,
                action="read",
                purpose="treatment",  # This would come from request context
                patient_id=storage_info["patient_id"]
            )
            
            if not access_check["allowed"]:
                raise PermissionError(f"Access denied: {access_check['reason']}")
            
            # Determine which version to return
            if anonymized and "anonymized_file_path" in storage_info:
                file_path = storage_info["anonymized_file_path"]
                is_encrypted = False  # Anonymized files are typically not encrypted
            else:
                file_path = storage_info["encrypted_file_path"]
                is_encrypted = True
                
            # Decrypt file if necessary
            if is_encrypted:
                temp_file = self.temp_path / f"{storage_id}_{user_id}_temp.dcm"
                await self.encryption_manager.decrypt_file(file_path, str(temp_file))
                file_path = str(temp_file)
            
            result = {
                "storage_id": storage_id,
                "file_path": file_path,
                "metadata": storage_info,
                "is_anonymized": anonymized,
                "access_granted_to": user_id,
                "access_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Log access
            security_logger.info(
                f"DICOM file accessed: storage_id={storage_id}, "
                f"user_id={user_id}, anonymized={anonymized}"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to retrieve DICOM file: {e}")
            raise
            
    async def validate_dicom_file(self, file_path: str) -> Dict[str, Any]:
        """Validate DICOM file format and compliance"""
        try:
            validation_result = {
                "is_valid": False,
                "file_path": file_path,
                "file_size": 0,
                "modality": "",
                "error": "",
                "warnings": []
            }
            
            # Check file exists and size
            if not os.path.exists(file_path):
                validation_result["error"] = "File does not exist"
                return validation_result
                
            file_size = os.path.getsize(file_path)
            validation_result["file_size"] = file_size
            
            # Check file size limits
            if file_size > settings.DICOM_MAX_FILE_SIZE:
                validation_result["error"] = f"File size exceeds limit ({settings.DICOM_MAX_FILE_SIZE} bytes)"
                return validation_result
                
            # Try to read as DICOM
            try:
                dataset = pydicom.dcmread(file_path, force=True)
            except Exception as e:
                validation_result["error"] = f"Invalid DICOM format: {str(e)}"
                return validation_result
                
            # Check required tags
            required_tags = [
                "SOPInstanceUID", "StudyInstanceUID", "SeriesInstanceUID", "Modality"
            ]
            
            for tag in required_tags:
                if not hasattr(dataset, tag) or not getattr(dataset, tag):
                    validation_result["warnings"].append(f"Missing or empty required tag: {tag}")
                    
            # Check modality
            modality = str(dataset.get("Modality", ""))
            validation_result["modality"] = modality
            
            if modality not in settings.DICOM_ALLOWED_MODALITIES:
                validation_result["warnings"].append(f"Modality '{modality}' not in allowed list")
                
            # Check for PHI in image data (basic check)
            if await self._check_burned_in_annotation(dataset):
                validation_result["warnings"].append("Potential burned-in PHI detected in image data")
                
            validation_result["is_valid"] = True
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate DICOM file: {e}")
            validation_result["error"] = f"Validation error: {str(e)}"
            return validation_result
            
    async def _extract_metadata(self, dataset: Dataset) -> Dict[str, Any]:
        """Extract metadata from DICOM dataset with PHI classification"""
        try:
            metadata = {}
            
            # Extract standard DICOM tags
            for tag, field_name in self.phi_tags.items():
                try:
                    if tag in dataset:
                        value = dataset[tag].value
                        if isinstance(value, bytes):
                            value = value.decode('utf-8', errors='ignore')
                        metadata[field_name] = str(value) if value else ""
                except Exception as e:
                    logger.warning(f"Failed to extract tag {tag}: {e}")
                    metadata[field_name] = ""
                    
            # Extract image-specific metadata
            metadata.update({
                "rows": int(dataset.get("Rows", 0)),
                "columns": int(dataset.get("Columns", 0)),
                "bits_allocated": int(dataset.get("BitsAllocated", 0)),
                "bits_stored": int(dataset.get("BitsStored", 0)),
                "photometric_interpretation": str(dataset.get("PhotometricInterpretation", "")),
                "pixel_spacing": list(dataset.get("PixelSpacing", [])) if "PixelSpacing" in dataset else [],
                "slice_thickness": float(dataset.get("SliceThickness", 0)) if "SliceThickness" in dataset else 0,
                "window_center": dataset.get("WindowCenter", 0),
                "window_width": dataset.get("WindowWidth", 0)
            })
            
            # Classify PHI data
            phi_classification = await self.hipaa_manager.classify_phi_data(metadata)
            metadata["_phi_classification"] = {k: v.value for k, v in phi_classification.items()}
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
            return {}
            
    async def _store_encrypted_dicom(self, source_file: str, storage_id: str) -> Path:
        """Store DICOM file with encryption"""
        try:
            encrypted_dir = self.storage_path / "encrypted" / storage_id[:2] / storage_id[2:4]
            encrypted_dir.mkdir(parents=True, exist_ok=True)
            
            encrypted_file_path = encrypted_dir / f"{storage_id}.dcm.enc"
            
            # Encrypt and store file
            await self.encryption_manager.encrypt_file(
                file_path=source_file,
                output_path=str(encrypted_file_path)
            )
            
            return encrypted_file_path
            
        except Exception as e:
            logger.error(f"Failed to store encrypted DICOM: {e}")
            raise
            
    async def _create_anonymized_version(self, dataset: Dataset, storage_id: str) -> Path:
        """Create anonymized version of DICOM file"""
        try:
            from .dicom_anonymizer import DICOMAnonymizer
            
            anonymizer = DICOMAnonymizer()
            await anonymizer.initialize()
            
            # Create anonymized dataset
            anonymized_dataset = await anonymizer.anonymize_dataset(dataset)
            
            # Save anonymized file
            anonymized_dir = self.anonymized_path / storage_id[:2] / storage_id[2:4]
            anonymized_dir.mkdir(parents=True, exist_ok=True)
            
            anonymized_file_path = anonymized_dir / f"{storage_id}_anon.dcm"
            anonymized_dataset.save_as(str(anonymized_file_path))
            
            return anonymized_file_path
            
        except Exception as e:
            logger.error(f"Failed to create anonymized version: {e}")
            raise
            
    async def _generate_thumbnails(self, dataset: Dataset, storage_id: str) -> Dict[str, str]:
        """Generate thumbnails for DICOM image"""
        try:
            thumbnail_paths = {}
            
            # Check if dataset has pixel data
            if not hasattr(dataset, 'pixel_array'):
                return thumbnail_paths
                
            try:
                pixel_array = dataset.pixel_array
            except Exception as e:
                logger.warning(f"Cannot access pixel array: {e}")
                return thumbnail_paths
                
            # Create thumbnails directory
            thumb_dir = self.storage_path / "thumbnails" / storage_id[:2] / storage_id[2:4]
            thumb_dir.mkdir(parents=True, exist_ok=True)
            
            # Normalize pixel array to 8-bit
            if pixel_array.dtype != np.uint8:
                # Apply window/level if available
                if hasattr(dataset, 'WindowCenter') and hasattr(dataset, 'WindowWidth'):
                    window_center = float(dataset.WindowCenter)
                    window_width = float(dataset.WindowWidth)
                    
                    img_min = window_center - window_width / 2
                    img_max = window_center + window_width / 2
                    
                    pixel_array = np.clip(pixel_array, img_min, img_max)
                    pixel_array = ((pixel_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                else:
                    # Auto-scale to full range
                    pixel_array = ((pixel_array - pixel_array.min()) / 
                                 (pixel_array.max() - pixel_array.min()) * 255).astype(np.uint8)
            
            # Handle different image dimensions
            if len(pixel_array.shape) == 3:
                # Multi-frame image - use middle frame
                frame_index = pixel_array.shape[0] // 2
                image_data = pixel_array[frame_index]
            else:
                image_data = pixel_array
                
            # Create different sized thumbnails
            thumbnail_sizes = [(64, 64), (128, 128), (256, 256)]
            
            for width, height in thumbnail_sizes:
                # Convert to PIL Image
                pil_image = Image.fromarray(image_data)
                
                # Resize maintaining aspect ratio
                pil_image.thumbnail((width, height), Image.Resampling.LANCZOS)
                
                # Save thumbnail
                thumb_filename = f"{storage_id}_thumb_{width}x{height}.png"
                thumb_path = thumb_dir / thumb_filename
                pil_image.save(str(thumb_path), "PNG")
                
                thumbnail_paths[f"{width}x{height}"] = str(thumb_path)
                
            return thumbnail_paths
            
        except Exception as e:
            logger.error(f"Failed to generate thumbnails: {e}")
            return {}
            
    async def _check_burned_in_annotation(self, dataset: Dataset) -> bool:
        """Basic check for burned-in PHI in image data"""
        try:
            # This is a simple heuristic check
            # In practice, would use more sophisticated image analysis
            
            burned_in_annotation = dataset.get("BurnedInAnnotation", "NO")
            if str(burned_in_annotation).upper() == "YES":
                return True
                
            # Check for text in image using basic heuristics
            if hasattr(dataset, 'pixel_array'):
                try:
                    pixel_array = dataset.pixel_array
                    
                    # Look for high-contrast regions that might contain text
                    if len(pixel_array.shape) >= 2:
                        # Simple edge detection to find potential text regions
                        # This would need more sophisticated analysis in production
                        edges = np.abs(np.diff(pixel_array.astype(float), axis=1))
                        high_contrast_ratio = np.sum(edges > np.std(edges) * 2) / edges.size
                        
                        # If high contrast ratio exceeds threshold, might contain text
                        if high_contrast_ratio > 0.1:  # 10% threshold
                            return True
                            
                except Exception as e:
                    logger.warning(f"Cannot analyze pixel data for burned-in annotation: {e}")
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to check burned-in annotation: {e}")
            return False
            
    async def search_dicom_files(self, search_criteria: Dict[str, Any], 
                               user_id: str) -> List[Dict[str, Any]]:
        """Search DICOM files based on criteria"""
        try:
            results = []
            
            # Get all metadata files
            metadata_files = list(self.storage_path.glob("*_metadata.json"))
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r') as f:
                        storage_info = json.load(f)
                        
                    # Check access permissions
                    access_check = await self.hipaa_manager.validate_access_request(
                        user_id=user_id,
                        resource_type="medical_image",
                        resource_id=storage_info["storage_id"],
                        action="read",
                        purpose="treatment",
                        patient_id=storage_info["patient_id"]
                    )
                    
                    if not access_check["allowed"]:
                        continue
                        
                    # Apply search criteria
                    if await self._matches_search_criteria(storage_info, search_criteria):
                        # Apply minimum necessary standard
                        filtered_info = await self.hipaa_manager.apply_minimum_necessary(
                            data=storage_info,
                            user_role="physician",  # This would come from user context
                            access_purpose="treatment"
                        )
                        results.append(filtered_info)
                        
                except Exception as e:
                    logger.warning(f"Failed to process metadata file {metadata_file}: {e}")
                    continue
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to search DICOM files: {e}")
            return []
            
    async def _matches_search_criteria(self, storage_info: Dict[str, Any], 
                                     criteria: Dict[str, Any]) -> bool:
        """Check if storage info matches search criteria"""
        try:
            for key, value in criteria.items():
                if key == "patient_id":
                    if storage_info.get("patient_id") != value:
                        return False
                elif key == "modality":
                    if storage_info.get("modality") != value:
                        return False
                elif key == "study_date_range":
                    study_date = storage_info.get("study_date", "")
                    if not (value["start"] <= study_date <= value["end"]):
                        return False
                elif key == "series_description":
                    if value.lower() not in storage_info.get("series_description", "").lower():
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"Failed to match search criteria: {e}")
            return False
            
    async def _cleanup_temp_files(self):
        """Cleanup temporary files older than configured hours"""
        try:
            cutoff_time = datetime.now(timezone.utc).timestamp() - (settings.TEMP_FILE_CLEANUP_HOURS * 3600)
            
            for temp_file in self.temp_path.glob("*"):
                try:
                    if temp_file.stat().st_mtime < cutoff_time:
                        temp_file.unlink()
                        logger.debug(f"Cleaned up temp file: {temp_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to cleanup temp files: {e}")
            
    async def get_dicom_statistics(self) -> Dict[str, Any]:
        """Get DICOM storage statistics"""
        try:
            stats = {
                "total_files": 0,
                "total_size_bytes": 0,
                "modalities": {},
                "anonymized_files": 0,
                "encrypted_files": 0
            }
            
            # Count metadata files
            metadata_files = list(self.storage_path.glob("*_metadata.json"))
            stats["total_files"] = len(metadata_files)
            
            for metadata_file in metadata_files:
                try:
                    with open(metadata_file, 'r') as f:
                        storage_info = json.load(f)
                        
                    # Add to size
                    stats["total_size_bytes"] += storage_info.get("file_size", 0)
                    
                    # Count modalities
                    modality = storage_info.get("modality", "UNKNOWN")
                    stats["modalities"][modality] = stats["modalities"].get(modality, 0) + 1
                    
                    # Count special versions
                    if storage_info.get("anonymized_file_path"):
                        stats["anonymized_files"] += 1
                    if storage_info.get("encrypted_file_path"):
                        stats["encrypted_files"] += 1
                        
                except Exception as e:
                    logger.warning(f"Failed to process metadata file {metadata_file}: {e}")
                    
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get DICOM statistics: {e}")
            return {}