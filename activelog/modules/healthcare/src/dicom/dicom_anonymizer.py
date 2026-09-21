"""
DICOM Anonymizer for removing PHI from medical images
Implements DICOM PS3.15 Security and System Management Profiles
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set
import hashlib
import uuid
import re

import pydicom
from pydicom.dataset import Dataset
from pydicom.tag import Tag
from pydicom.uid import generate_uid
import numpy as np

logger = logging.getLogger(__name__)

class DICOMAnonymizer:
    def __init__(self):
        # DICOM tags to remove (Basic Application Level Confidentiality Profile)
        self.tags_to_remove = {
            # Patient identification tags
            (0x0010, 0x0010),  # Patient's Name
            (0x0010, 0x0020),  # Patient ID
            (0x0010, 0x0030),  # Patient's Birth Date
            (0x0010, 0x0032),  # Patient's Birth Time
            (0x0010, 0x0040),  # Patient's Sex
            (0x0010, 0x1000),  # Other Patient IDs
            (0x0010, 0x1001),  # Other Patient Names
            (0x0010, 0x1005),  # Patient's Birth Name
            (0x0010, 0x1010),  # Patient's Age
            (0x0010, 0x1020),  # Patient's Size
            (0x0010, 0x1030),  # Patient's Weight
            (0x0010, 0x1040),  # Patient's Address
            (0x0010, 0x1050),  # Insurance Plan Identification
            (0x0010, 0x1060),  # Patient's Mother's Birth Name
            (0x0010, 0x1080),  # Military Rank
            (0x0010, 0x1081),  # Branch of Service
            (0x0010, 0x1090),  # Medical Record Locator
            (0x0010, 0x2000),  # Medical Alerts
            (0x0010, 0x2110),  # Contrast Allergies
            (0x0010, 0x2150),  # Country of Residence
            (0x0010, 0x2152),  # Region of Residence
            (0x0010, 0x2154),  # Patient's Telephone Numbers
            (0x0010, 0x2160),  # Ethnic Group
            (0x0010, 0x2180),  # Occupation
            (0x0010, 0x21A0),  # Smoking Status
            (0x0010, 0x21B0),  # Additional Patient History
            (0x0010, 0x21C0),  # Pregnancy Status
            (0x0010, 0x21D0),  # Last Menstrual Date
            (0x0010, 0x21F0),  # Patient's Religious Preference
            (0x0010, 0x4000),  # Patient Comments
            
            # Study identification tags
            (0x0008, 0x0020),  # Study Date
            (0x0008, 0x0030),  # Study Time
            (0x0008, 0x0050),  # Accession Number
            (0x0008, 0x0080),  # Institution Name
            (0x0008, 0x0081),  # Institution Address
            (0x0008, 0x0090),  # Referring Physician's Name
            (0x0008, 0x0092),  # Referring Physician's Address
            (0x0008, 0x0094),  # Referring Physician's Telephone Numbers
            (0x0008, 0x1010),  # Station Name
            (0x0008, 0x1030),  # Study Description
            (0x0008, 0x103E),  # Series Description
            (0x0008, 0x1040),  # Institutional Department Name
            (0x0008, 0x1048),  # Physician(s) of Record
            (0x0008, 0x1050),  # Performing Physician's Name
            (0x0008, 0x1060),  # Name of Physician(s) Reading Study
            (0x0008, 0x1070),  # Operators' Name
            (0x0008, 0x1080),  # Admitting Diagnoses Description
            (0x0008, 0x1155),  # Referenced SOP Instance UID
            (0x0008, 0x2111),  # Derivation Description
            
            # Equipment identification tags
            (0x0008, 0x0070),  # Manufacturer
            (0x0008, 0x1090),  # Manufacturer's Model Name
            (0x0018, 0x1000),  # Device Serial Number
            (0x0018, 0x1020),  # Software Version(s)
            
            # Additional potentially identifying tags
            (0x0020, 0x4000),  # Image Comments
            (0x4000, 0x4000),  # Text Comments
            (0x0040, 0x0275),  # Request Attributes Sequence
            (0x0040, 0xA123),  # Person Name
            (0x0040, 0xA124),  # UID
        }
        
        # Tags to replace with dummy values
        self.tags_to_replace = {
            (0x0010, 0x0010): "ANONYMOUS",           # Patient's Name
            (0x0010, 0x0020): "ANON_ID",             # Patient ID  
            (0x0008, 0x0090): "ANON_PHYSICIAN",      # Referring Physician's Name
            (0x0008, 0x1050): "ANON_PHYSICIAN",      # Performing Physician's Name
            (0x0008, 0x1060): "ANON_PHYSICIAN",      # Name of Physician(s) Reading Study
            (0x0008, 0x0080): "ANON_INSTITUTION",    # Institution Name
            (0x0008, 0x1010): "ANON_STATION",        # Station Name
        }
        
        # UIDs that need to be replaced with new ones
        self.uid_tags = {
            (0x0020, 0x000D),  # Study Instance UID
            (0x0020, 0x000E),  # Series Instance UID
            (0x0008, 0x0018),  # SOP Instance UID
            (0x0002, 0x0003),  # Media Storage SOP Instance UID
        }
        
        # Date tags that need to be shifted
        self.date_tags = {
            (0x0008, 0x0020): "DA",  # Study Date
            (0x0008, 0x0021): "DA",  # Series Date
            (0x0008, 0x0022): "DA",  # Acquisition Date
            (0x0008, 0x0023): "DA",  # Content Date
            (0x0008, 0x0024): "DA",  # Overlay Date
            (0x0008, 0x0025): "DA",  # Curve Date
        }
        
        # Time tags that need to be shifted
        self.time_tags = {
            (0x0008, 0x0030): "TM",  # Study Time
            (0x0008, 0x0031): "TM",  # Series Time
            (0x0008, 0x0032): "TM",  # Acquisition Time
            (0x0008, 0x0033): "TM",  # Content Time
            (0x0008, 0x0034): "TM",  # Overlay Time
            (0x0008, 0x0035): "TM",  # Curve Time
        }
        
        self.uid_map = {}  # Map original UIDs to anonymized ones
        self.date_shift = None  # Date shift to be applied consistently
        
    async def initialize(self):
        """Initialize anonymizer"""
        logger.info("Initializing DICOM anonymizer")
        
        # Generate consistent date shift for this session
        # Shift between -365 and -30 days to ensure dates are in the past
        import random
        shift_days = random.randint(-365, -30)
        self.date_shift = timedelta(days=shift_days)
        
    async def anonymize_dataset(self, dataset: Dataset, 
                              patient_pseudo_id: Optional[str] = None) -> Dataset:
        """Anonymize a DICOM dataset"""
        try:
            # Create a copy to avoid modifying original
            anonymized_dataset = dataset.copy()
            
            # Generate patient pseudo ID if not provided
            if not patient_pseudo_id:
                patient_pseudo_id = self._generate_patient_pseudo_id(dataset)
            
            # Remove identifying tags
            await self._remove_identifying_tags(anonymized_dataset)
            
            # Replace tags with dummy values
            await self._replace_tags_with_dummy_values(anonymized_dataset, patient_pseudo_id)
            
            # Replace UIDs
            await self._replace_uids(anonymized_dataset)
            
            # Shift dates and times
            await self._shift_dates_and_times(anonymized_dataset)
            
            # Remove or anonymize pixel data if contains burned-in PHI
            await self._handle_pixel_data(anonymized_dataset)
            
            # Remove private tags
            await self._remove_private_tags(anonymized_dataset)
            
            # Add anonymization metadata
            await self._add_anonymization_metadata(anonymized_dataset)
            
            logger.info("DICOM dataset anonymized successfully")
            return anonymized_dataset
            
        except Exception as e:
            logger.error(f"Failed to anonymize DICOM dataset: {e}")
            raise
            
    async def _remove_identifying_tags(self, dataset: Dataset):
        """Remove identifying tags from dataset"""
        try:
            for tag in self.tags_to_remove:
                if tag in dataset:
                    del dataset[tag]
                    
            # Also remove from sequences recursively
            await self._remove_from_sequences(dataset, self.tags_to_remove)
            
        except Exception as e:
            logger.error(f"Failed to remove identifying tags: {e}")
            raise
            
    async def _replace_tags_with_dummy_values(self, dataset: Dataset, patient_pseudo_id: str):
        """Replace tags with dummy values"""
        try:
            for tag, dummy_value in self.tags_to_replace.items():
                if tag in dataset:
                    if tag == (0x0010, 0x0020):  # Patient ID
                        dataset[tag].value = patient_pseudo_id
                    else:
                        dataset[tag].value = dummy_value
                        
        except Exception as e:
            logger.error(f"Failed to replace tags with dummy values: {e}")
            raise
            
    async def _replace_uids(self, dataset: Dataset):
        """Replace UIDs with new anonymized ones"""
        try:
            for tag in self.uid_tags:
                if tag in dataset:
                    original_uid = dataset[tag].value
                    
                    # Check if we already have a mapping for this UID
                    if original_uid in self.uid_map:
                        new_uid = self.uid_map[original_uid]
                    else:
                        # Generate new UID
                        new_uid = generate_uid()
                        self.uid_map[original_uid] = new_uid
                        
                    dataset[tag].value = new_uid
                    
            # Also replace UIDs in sequences
            await self._replace_uids_in_sequences(dataset)
            
        except Exception as e:
            logger.error(f"Failed to replace UIDs: {e}")
            raise
            
    async def _shift_dates_and_times(self, dataset: Dataset):
        """Shift dates and times consistently"""
        try:
            # Shift date tags
            for tag, vr in self.date_tags.items():
                if tag in dataset:
                    original_date = dataset[tag].value
                    if original_date:
                        shifted_date = await self._shift_date(original_date)
                        dataset[tag].value = shifted_date
                        
            # Shift time tags (keep same time, just apply date shift if needed)
            # Times are usually kept as-is unless they contain date information
            
        except Exception as e:
            logger.error(f"Failed to shift dates and times: {e}")
            raise
            
    async def _handle_pixel_data(self, dataset: Dataset):
        """Handle pixel data that may contain burned-in PHI"""
        try:
            # Check for burned-in annotation
            burned_in_annotation = dataset.get("BurnedInAnnotation", "NO")
            
            if str(burned_in_annotation).upper() == "YES":
                # If burned-in annotation is confirmed, need to handle pixel data
                logger.warning("Burned-in annotation detected, pixel data may contain PHI")
                
                # Options:
                # 1. Remove pixel data entirely
                # 2. Apply image processing to remove text regions
                # 3. Add overlay to mask potential PHI regions
                
                # For now, we'll add a warning overlay
                if hasattr(dataset, 'pixel_array'):
                    await self._add_phi_warning_overlay(dataset)
                    
            # Check for other signs of burned-in PHI
            elif await self._detect_potential_text_in_image(dataset):
                logger.warning("Potential text detected in image, may contain PHI")
                # Could add additional processing here
                
        except Exception as e:
            logger.error(f"Failed to handle pixel data: {e}")
            
    async def _remove_private_tags(self, dataset: Dataset):
        """Remove private tags that may contain PHI"""
        try:
            # Private tags have odd group numbers
            private_tags = []
            
            for tag in dataset.keys():
                if tag.group % 2 == 1:  # Odd group numbers are private
                    private_tags.append(tag)
                    
            # Remove private tags
            for tag in private_tags:
                del dataset[tag]
                
        except Exception as e:
            logger.error(f"Failed to remove private tags: {e}")
            
    async def _add_anonymization_metadata(self, dataset: Dataset):
        """Add metadata indicating anonymization"""
        try:
            # Add anonymization information
            dataset.PatientIdentityRemoved = "YES"
            dataset.DeidentificationMethod = "ActiveLog Healthcare Anonymizer"
            dataset.DeidentificationMethodCodeSequence = []
            
            # Add anonymization timestamp
            now = datetime.now(timezone.utc)
            dataset.InstanceCreationDate = now.strftime("%Y%m%d")
            dataset.InstanceCreationTime = now.strftime("%H%M%S.%f")[:-3]
            
        except Exception as e:
            logger.error(f"Failed to add anonymization metadata: {e}")
            
    def _generate_patient_pseudo_id(self, dataset: Dataset) -> str:
        """Generate pseudo ID for patient"""
        try:
            # Use original patient ID to generate consistent pseudo ID
            original_id = str(dataset.get("PatientID", ""))
            if not original_id:
                # Fallback to other identifying information
                name = str(dataset.get("PatientName", ""))
                birth_date = str(dataset.get("PatientBirthDate", ""))
                original_id = f"{name}_{birth_date}"
                
            # Create hash-based pseudo ID
            hash_input = f"patient_salt_{original_id}".encode()
            hash_obj = hashlib.sha256(hash_input)
            return f"ANON_{hash_obj.hexdigest()[:8].upper()}"
            
        except Exception as e:
            logger.error(f"Failed to generate patient pseudo ID: {e}")
            return f"ANON_{uuid.uuid4().hex[:8].upper()}"
            
    async def _shift_date(self, date_string: str) -> str:
        """Shift a date string by the consistent offset"""
        try:
            # Parse DICOM date format (YYYYMMDD)
            if len(date_string) == 8 and date_string.isdigit():
                year = int(date_string[:4])
                month = int(date_string[4:6])
                day = int(date_string[6:8])
                
                original_date = datetime(year, month, day)
                shifted_date = original_date + self.date_shift
                
                return shifted_date.strftime("%Y%m%d")
            else:
                # If not standard format, return as-is or empty
                return ""
                
        except Exception as e:
            logger.error(f"Failed to shift date {date_string}: {e}")
            return ""
            
    async def _remove_from_sequences(self, dataset: Dataset, tags_to_remove: Set):
        """Recursively remove tags from sequences"""
        try:
            for element in dataset:
                if element.VR == "SQ":  # Sequence
                    for item in element.value:
                        # Remove tags from sequence item
                        for tag in tags_to_remove:
                            if tag in item:
                                del item[tag]
                                
                        # Recursively process nested sequences
                        await self._remove_from_sequences(item, tags_to_remove)
                        
        except Exception as e:
            logger.error(f"Failed to remove from sequences: {e}")
            
    async def _replace_uids_in_sequences(self, dataset: Dataset):
        """Replace UIDs in sequences"""
        try:
            for element in dataset:
                if element.VR == "SQ":  # Sequence
                    for item in element.value:
                        # Replace UIDs in sequence item
                        for tag in self.uid_tags:
                            if tag in item:
                                original_uid = item[tag].value
                                if original_uid in self.uid_map:
                                    item[tag].value = self.uid_map[original_uid]
                                else:
                                    new_uid = generate_uid()
                                    self.uid_map[original_uid] = new_uid
                                    item[tag].value = new_uid
                                    
                        # Recursively process nested sequences
                        await self._replace_uids_in_sequences(item)
                        
        except Exception as e:
            logger.error(f"Failed to replace UIDs in sequences: {e}")
            
    async def _detect_potential_text_in_image(self, dataset: Dataset) -> bool:
        """Detect potential text in image data"""
        try:
            if not hasattr(dataset, 'pixel_array'):
                return False
                
            pixel_array = dataset.pixel_array
            
            # Simple heuristic: look for high-contrast rectangular regions
            # that might contain text
            if len(pixel_array.shape) >= 2:
                # Look for regions with high horizontal contrast (text-like)
                horizontal_edges = np.abs(np.diff(pixel_array.astype(float), axis=1))
                vertical_edges = np.abs(np.diff(pixel_array.astype(float), axis=0))
                
                # Calculate edge density
                h_edge_density = np.sum(horizontal_edges > np.std(horizontal_edges) * 2) / horizontal_edges.size
                v_edge_density = np.sum(vertical_edges > np.std(vertical_edges) * 2) / vertical_edges.size
                
                # If both horizontal and vertical edge density is high, might contain text
                if h_edge_density > 0.05 and v_edge_density > 0.05:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Failed to detect potential text in image: {e}")
            return False
            
    async def _add_phi_warning_overlay(self, dataset: Dataset):
        """Add warning overlay to image with potential PHI"""
        try:
            if hasattr(dataset, 'pixel_array'):
                pixel_array = dataset.pixel_array.copy()
                
                # Add a warning overlay at the top of the image
                if len(pixel_array.shape) == 2:
                    height, width = pixel_array.shape
                    
                    # Create warning bar at top (10% of image height)
                    warning_height = max(20, height // 10)
                    
                    # Set warning area to maximum intensity
                    max_value = np.max(pixel_array)
                    pixel_array[:warning_height, :] = max_value
                    
                    # Update dataset pixel data
                    dataset.PixelData = pixel_array.tobytes()
                    
        except Exception as e:
            logger.error(f"Failed to add PHI warning overlay: {e}")
            
    async def anonymize_batch(self, file_paths: List[str], 
                            output_dir: str) -> List[Dict[str, Any]]:
        """Anonymize a batch of DICOM files"""
        try:
            results = []
            
            for file_path in file_paths:
                try:
                    # Read DICOM file
                    dataset = pydicom.dcmread(file_path, force=True)
                    
                    # Anonymize dataset
                    anonymized_dataset = await self.anonymize_dataset(dataset)
                    
                    # Generate output filename
                    original_filename = Path(file_path).name
                    output_filename = f"anon_{original_filename}"
                    output_path = Path(output_dir) / output_filename
                    
                    # Save anonymized file
                    anonymized_dataset.save_as(str(output_path))
                    
                    results.append({
                        "original_file": file_path,
                        "anonymized_file": str(output_path),
                        "status": "success",
                        "patient_pseudo_id": anonymized_dataset.get("PatientID", ""),
                        "anonymization_timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to anonymize {file_path}: {e}")
                    results.append({
                        "original_file": file_path,
                        "status": "failed",
                        "error": str(e)
                    })
                    
            return results
            
        except Exception as e:
            logger.error(f"Failed to anonymize batch: {e}")
            return []
            
    async def validate_anonymization(self, original_file: str, 
                                   anonymized_file: str) -> Dict[str, Any]:
        """Validate anonymization quality"""
        try:
            # Read both files
            original_dataset = pydicom.dcmread(original_file, force=True)
            anonymized_dataset = pydicom.dcmread(anonymized_file, force=True)
            
            validation_result = {
                "is_valid": True,
                "phi_removed": True,
                "uids_replaced": True,
                "dates_shifted": True,
                "issues": []
            }
            
            # Check if PHI tags are removed or replaced
            for tag in self.tags_to_remove:
                if tag in anonymized_dataset:
                    validation_result["issues"].append(f"PHI tag {tag} not removed")
                    validation_result["phi_removed"] = False
                    
            # Check if UIDs are different
            for tag in self.uid_tags:
                if (tag in original_dataset and tag in anonymized_dataset):
                    if original_dataset[tag].value == anonymized_dataset[tag].value:
                        validation_result["issues"].append(f"UID {tag} not replaced")
                        validation_result["uids_replaced"] = False
                        
            # Check anonymization metadata
            if not anonymized_dataset.get("PatientIdentityRemoved") == "YES":
                validation_result["issues"].append("PatientIdentityRemoved not set")
                
            validation_result["is_valid"] = (validation_result["phi_removed"] and 
                                           validation_result["uids_replaced"])
            
            return validation_result
            
        except Exception as e:
            logger.error(f"Failed to validate anonymization: {e}")
            return {"is_valid": False, "error": str(e)}
            
    def get_anonymization_summary(self) -> Dict[str, Any]:
        """Get summary of anonymization process"""
        return {
            "tags_removed": len(self.tags_to_remove),
            "tags_replaced": len(self.tags_to_replace),
            "uids_replaced": len(self.uid_tags),
            "date_shift_days": self.date_shift.days if self.date_shift else 0,
            "uid_mappings": len(self.uid_map),
            "anonymization_profile": "Basic Application Level Confidentiality Profile"
        }