"""DICOM image viewing and processing functionality"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any, BinaryIO
from pathlib import Path
import tempfile
import numpy as np
from PIL import Image, ImageEnhance
import pydicom
from pydicom.dataset import Dataset
from pydicom.uid import generate_uid

from ..core.config import get_healthcare_settings
from ..compliance.hipaa_manager import HIPAAManager
from ..compliance.encryption_manager import EncryptionManager


class DICOMViewer:
    """Secure DICOM image viewing with PHI protection"""
    
    def __init__(self):
        self.settings = get_healthcare_settings()
        self.hipaa_manager = HIPAAManager()
        self.encryption_manager = EncryptionManager()
        
    async def get_viewable_image(
        self, 
        storage_id: str, 
        user_id: str,
        window_center: Optional[int] = None,
        window_width: Optional[int] = None,
        size: Tuple[int, int] = (512, 512)
    ) -> Optional[bytes]:
        """
        Get DICOM image as viewable format with windowing
        
        Args:
            storage_id: Encrypted DICOM storage identifier
            user_id: User requesting the image
            window_center: DICOM window center value
            window_width: DICOM window width value  
            size: Output image size (width, height)
            
        Returns:
            PNG image bytes or None if access denied
        """
        try:
            # Validate access
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="dicom_image",
                resource_id=storage_id,
                action="view",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Load encrypted DICOM file
            dicom_path = self._get_storage_path(storage_id)
            if not dicom_path.exists():
                return None
                
            # Decrypt and load DICOM
            with tempfile.NamedTemporaryFile() as temp_file:
                await self._decrypt_dicom_file(dicom_path, temp_file.name)
                dataset = pydicom.dcmread(temp_file.name)
                
            # Convert to viewable image
            image_bytes = await self._dataset_to_image(
                dataset, window_center, window_width, size
            )
            
            # Log access
            await self._log_image_access(storage_id, user_id)
            
            return image_bytes
            
        except Exception as e:
            await self._log_access_error(storage_id, user_id, str(e))
            return None
            
    async def get_image_metadata(
        self, 
        storage_id: str, 
        user_id: str,
        include_phi: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Get DICOM image metadata
        
        Args:
            storage_id: Encrypted DICOM storage identifier
            user_id: User requesting metadata
            include_phi: Whether to include PHI fields (requires elevated access)
            
        Returns:
            Metadata dictionary or None if access denied
        """
        try:
            # Validate access level
            access_purpose = "treatment" if include_phi else "quality_assurance"
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="dicom_metadata",
                resource_id=storage_id,
                action="view",
                purpose=access_purpose
            )
            
            if not access_valid:
                return None
                
            # Load and decrypt DICOM
            dicom_path = self._get_storage_path(storage_id)
            if not dicom_path.exists():
                return None
                
            with tempfile.NamedTemporaryFile() as temp_file:
                await self._decrypt_dicom_file(dicom_path, temp_file.name)
                dataset = pydicom.dcmread(temp_file.name)
                
            # Extract metadata
            metadata = await self._extract_metadata(dataset, include_phi)
            
            # Log access
            await self._log_metadata_access(storage_id, user_id, include_phi)
            
            return metadata
            
        except Exception as e:
            await self._log_access_error(storage_id, user_id, str(e))
            return None
            
    async def get_image_series(
        self,
        series_uid: str,
        user_id: str,
        start_slice: int = 0,
        num_slices: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get multiple images from a DICOM series
        
        Args:
            series_uid: DICOM Series Instance UID
            user_id: User requesting the series
            start_slice: Starting slice number
            num_slices: Number of slices to return
            
        Returns:
            List of image data dictionaries
        """
        try:
            # Find all images in series
            series_images = await self._find_series_images(series_uid)
            
            if not series_images:
                return []
                
            # Validate access to series
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="dicom_series",
                resource_id=series_uid,
                action="view",
                purpose="treatment"
            )
            
            if not access_valid:
                return []
                
            # Get requested slice range
            end_slice = min(start_slice + num_slices, len(series_images))
            requested_images = series_images[start_slice:end_slice]
            
            # Process each image
            results = []
            for image_info in requested_images:
                storage_id = image_info["storage_id"]
                
                # Get viewable image
                image_bytes = await self.get_viewable_image(
                    storage_id, user_id, size=(256, 256)  # Smaller for series view
                )
                
                if image_bytes:
                    results.append({
                        "storage_id": storage_id,
                        "slice_number": image_info["slice_number"],
                        "image_data": image_bytes,
                        "instance_uid": image_info["instance_uid"]
                    })
                    
            return results
            
        except Exception as e:
            await self._log_access_error(series_uid, user_id, str(e))
            return []
            
    async def create_mpr_view(
        self,
        series_uid: str,
        user_id: str,
        plane: str = "sagittal",  # sagittal, coronal, axial
        slice_position: float = 0.5
    ) -> Optional[bytes]:
        """
        Create Multi-Planar Reconstruction (MPR) view
        
        Args:
            series_uid: DICOM Series Instance UID
            user_id: User requesting the MPR
            plane: Reconstruction plane
            slice_position: Position along the plane (0.0-1.0)
            
        Returns:
            PNG image bytes or None
        """
        try:
            # Validate access
            access_valid = await self.hipaa_manager.validate_access_request(
                user_id=user_id,
                resource_type="dicom_series",
                resource_id=series_uid,
                action="reconstruct",
                purpose="treatment"
            )
            
            if not access_valid:
                return None
                
            # Load entire series
            volume_data = await self._load_series_volume(series_uid)
            if volume_data is None:
                return None
                
            # Create MPR slice
            mpr_slice = self._create_mpr_slice(volume_data, plane, slice_position)
            
            # Convert to viewable image
            image_bytes = self._array_to_png(mpr_slice)
            
            # Log MPR creation
            await self._log_mpr_access(series_uid, user_id, plane)
            
            return image_bytes
            
        except Exception as e:
            await self._log_access_error(series_uid, user_id, str(e))
            return None
            
    def _get_storage_path(self, storage_id: str) -> Path:
        """Get the file system path for a storage ID"""
        storage_dir = Path(self.settings.DICOM_STORAGE_PATH)
        return storage_dir / f"{storage_id}.dcm"
        
    async def _decrypt_dicom_file(self, encrypted_path: Path, output_path: str):
        """Decrypt DICOM file to temporary location"""
        with open(encrypted_path, "rb") as encrypted_file:
            encrypted_data = encrypted_file.read()
            
        decrypted_data = await self.encryption_manager.decrypt_data(
            encrypted_data, "maximum_security"
        )
        
        with open(output_path, "wb") as decrypted_file:
            decrypted_file.write(decrypted_data)
            
    async def _dataset_to_image(
        self,
        dataset: Dataset,
        window_center: Optional[int],
        window_width: Optional[int],
        size: Tuple[int, int]
    ) -> bytes:
        """Convert DICOM dataset to PNG image with windowing"""
        
        # Get pixel array
        pixel_array = dataset.pixel_array
        
        # Handle different photometric interpretations
        if hasattr(dataset, 'PhotometricInterpretation'):
            if dataset.PhotometricInterpretation == 'MONOCHROME1':
                # Invert for MONOCHROME1
                pixel_array = np.amax(pixel_array) - pixel_array
                
        # Apply windowing
        if window_center is not None and window_width is not None:
            img_min = window_center - window_width // 2
            img_max = window_center + window_width // 2
            pixel_array = np.clip(pixel_array, img_min, img_max)
        else:
            # Auto-window
            img_min = np.percentile(pixel_array, 1)
            img_max = np.percentile(pixel_array, 99)
            pixel_array = np.clip(pixel_array, img_min, img_max)
            
        # Normalize to 0-255
        pixel_array = ((pixel_array - img_min) / (img_max - img_min) * 255).astype(np.uint8)
        
        # Convert to PIL Image
        if len(pixel_array.shape) == 3:
            # Multi-frame, take first frame
            pil_image = Image.fromarray(pixel_array[0])
        else:
            pil_image = Image.fromarray(pixel_array)
            
        # Resize if needed
        if pil_image.size != size:
            pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
            
        # Convert to PNG bytes
        import io
        png_buffer = io.BytesIO()
        pil_image.save(png_buffer, format='PNG')
        return png_buffer.getvalue()
        
    async def _extract_metadata(
        self, 
        dataset: Dataset, 
        include_phi: bool
    ) -> Dict[str, Any]:
        """Extract DICOM metadata with PHI filtering"""
        
        # Safe tags (no PHI)
        safe_tags = [
            'StudyDate', 'SeriesDate', 'AcquisitionDate',
            'StudyTime', 'SeriesTime', 'AcquisitionTime',
            'Modality', 'Manufacturer', 'ManufacturerModelName',
            'SoftwareVersions', 'StudyDescription', 'SeriesDescription',
            'ProtocolName', 'BodyPartExamined', 'SliceThickness',
            'PixelSpacing', 'ImageOrientationPatient', 'ImagePositionPatient',
            'Rows', 'Columns', 'BitsAllocated', 'BitsStored',
            'PixelRepresentation', 'WindowCenter', 'WindowWidth',
            'RescaleIntercept', 'RescaleSlope'
        ]
        
        # PHI tags (require elevated access)
        phi_tags = [
            'PatientName', 'PatientID', 'PatientBirthDate',
            'PatientSex', 'PatientAge', 'PatientWeight',
            'PatientAddress', 'StudyInstanceUID', 'SeriesInstanceUID',
            'SOPInstanceUID', 'AccessionNumber', 'StudyID'
        ]
        
        metadata = {}
        
        # Always include safe metadata
        for tag in safe_tags:
            if hasattr(dataset, tag):
                value = getattr(dataset, tag)
                if value is not None:
                    metadata[tag] = str(value)
                    
        # Include PHI only if authorized
        if include_phi:
            for tag in phi_tags:
                if hasattr(dataset, tag):
                    value = getattr(dataset, tag)
                    if value is not None:
                        metadata[tag] = str(value)
                        
        return metadata
        
    async def _find_series_images(self, series_uid: str) -> List[Dict[str, Any]]:
        """Find all images belonging to a DICOM series"""
        # This would query the database for images in the series
        # Placeholder implementation
        return []
        
    async def _load_series_volume(self, series_uid: str) -> Optional[np.ndarray]:
        """Load entire DICOM series as 3D volume"""
        series_images = await self._find_series_images(series_uid)
        
        if not series_images:
            return None
            
        # Load and stack all slices
        slices = []
        for image_info in sorted(series_images, key=lambda x: x["slice_number"]):
            storage_id = image_info["storage_id"]
            dicom_path = self._get_storage_path(storage_id)
            
            with tempfile.NamedTemporaryFile() as temp_file:
                await self._decrypt_dicom_file(dicom_path, temp_file.name)
                dataset = pydicom.dcmread(temp_file.name)
                slices.append(dataset.pixel_array)
                
        return np.stack(slices, axis=0)
        
    def _create_mpr_slice(
        self, 
        volume: np.ndarray, 
        plane: str, 
        position: float
    ) -> np.ndarray:
        """Create MPR slice from 3D volume"""
        
        if plane == "sagittal":
            # YZ plane
            slice_idx = int(position * volume.shape[2])
            return volume[:, :, slice_idx]
        elif plane == "coronal":
            # XZ plane  
            slice_idx = int(position * volume.shape[1])
            return volume[:, slice_idx, :]
        else:  # axial
            # XY plane
            slice_idx = int(position * volume.shape[0])
            return volume[slice_idx, :, :]
            
    def _array_to_png(self, array: np.ndarray) -> bytes:
        """Convert numpy array to PNG bytes"""
        # Normalize to 0-255
        array = ((array - np.min(array)) / (np.max(array) - np.min(array)) * 255).astype(np.uint8)
        
        pil_image = Image.fromarray(array)
        
        import io
        png_buffer = io.BytesIO()
        pil_image.save(png_buffer, format='PNG')
        return png_buffer.getvalue()
        
    async def _log_image_access(self, storage_id: str, user_id: str):
        """Log DICOM image access"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action="view_dicom_image",
            resource_type="dicom_image",
            resource_id=storage_id,
            purpose="treatment"
        )
        
    async def _log_metadata_access(self, storage_id: str, user_id: str, include_phi: bool):
        """Log DICOM metadata access"""
        action = "view_dicom_metadata_phi" if include_phi else "view_dicom_metadata"
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action=action,
            resource_type="dicom_metadata", 
            resource_id=storage_id,
            purpose="treatment"
        )
        
    async def _log_mpr_access(self, series_uid: str, user_id: str, plane: str):
        """Log MPR reconstruction access"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action=f"create_mpr_{plane}",
            resource_type="dicom_series",
            resource_id=series_uid,
            purpose="treatment"
        )
        
    async def _log_access_error(self, resource_id: str, user_id: str, error: str):
        """Log access error"""
        await self.hipaa_manager.log_phi_access(
            user_id=user_id,
            action="access_error",
            resource_type="dicom",
            resource_id=resource_id,
            purpose="error_logging",
            additional_data={"error": error}
        )