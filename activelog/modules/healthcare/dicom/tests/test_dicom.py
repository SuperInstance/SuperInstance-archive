"""
Tests for DICOM image support module
"""
import unittest
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from ..src.dicom_handler import DICOMProcessor, DICOMSecurity, DICOMStorage, DICOMMetadata


class TestDICOMSecurity(unittest.TestCase):
    
    def setUp(self):
        # Mock pydicom Dataset
        self.mock_dataset = Mock()
        self.mock_dataset.PatientName = Mock()
        self.mock_dataset.PatientName.value = "John Doe"
        self.mock_dataset.PatientID = Mock()
        self.mock_dataset.PatientID.value = "12345"
        self.mock_dataset.StudyInstanceUID = Mock()
        self.mock_dataset.StudyInstanceUID.value = "1.2.3.4.5"
    
    def test_anonymize_dicom_tags(self):
        """Test DICOM tag anonymization"""
        # Create mock dataset with PHI
        mock_dataset = {
            'PatientName': Mock(value='John Doe'),
            'PatientID': Mock(value='12345'),
            'PatientBirthDate': Mock(value='19800101'),
            'StudyInstanceUID': Mock(value='1.2.3.4.5')
        }
        
        # Mock the dataset to behave like a dictionary
        dataset_mock = Mock()
        dataset_mock.__contains__ = lambda self, key: key in mock_dataset
        dataset_mock.__getitem__ = lambda self, key: mock_dataset[key]
        
        anonymized = DICOMSecurity.anonymize_dicom_tags(dataset_mock, keep_uids=True)
        
        # Verify anonymization occurred
        self.assertEqual(mock_dataset['PatientName'].value, 'ANONYMOUS')
        self.assertEqual(mock_dataset['PatientBirthDate'].value, '')
        # UID should be kept
        self.assertEqual(mock_dataset['StudyInstanceUID'].value, '1.2.3.4.5')


class TestDICOMProcessor(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('os.makedirs')
    def test_processor_initialization(self, mock_makedirs):
        """Test DICOM processor initialization"""
        with patch('healthcare.dicom.src.dicom_handler.pydicom', Mock()):
            processor = DICOMProcessor(self.temp_dir)
            self.assertEqual(processor.temp_dir, self.temp_dir)
            mock_makedirs.assert_called_once()
    
    def test_processor_without_pydicom(self):
        """Test processor fails gracefully without pydicom"""
        with patch('healthcare.dicom.src.dicom_handler.pydicom', None):
            with self.assertRaises(ImportError):
                DICOMProcessor(self.temp_dir)
    
    @patch('healthcare.dicom.src.dicom_handler.pydicom')
    def test_load_dicom_file_success(self, mock_pydicom):
        """Test successful DICOM file loading"""
        # Mock successful file read
        mock_dataset = Mock()
        mock_dataset.PatientID = '12345'
        mock_dataset.StudyInstanceUID = '1.2.3.4.5'
        mock_pydicom.dcmread.return_value = mock_dataset
        
        # Mock validation
        with patch.object(DICOMSecurity, 'validate_dicom_integrity', return_value=(True, "Valid")):
            processor = DICOMProcessor(self.temp_dir)
            result = processor.load_dicom_file('/fake/path.dcm')
            
            self.assertIsNotNone(result)
            self.assertEqual(len(processor.processing_log), 1)
    
    @patch('healthcare.dicom.src.dicom_handler.pydicom')
    def test_extract_metadata(self, mock_pydicom):
        """Test metadata extraction from DICOM dataset"""
        mock_dataset = Mock()
        mock_dataset.PatientID = '12345'
        mock_dataset.StudyInstanceUID = '1.2.3.4.5'
        mock_dataset.SeriesInstanceUID = '1.2.3.4.5.6'
        mock_dataset.SOPInstanceUID = '1.2.3.4.5.6.7'
        mock_dataset.Modality = 'CT'
        mock_dataset.StudyDate = '20240101'
        
        processor = DICOMProcessor(self.temp_dir)
        metadata = processor.extract_metadata(mock_dataset)
        
        self.assertIsInstance(metadata, DICOMMetadata)
        self.assertEqual(metadata.patient_id, '12345')
        self.assertEqual(metadata.modality, 'CT')
    
    @patch('healthcare.dicom.src.dicom_handler.pydicom')
    def test_search_dicom_by_criteria(self, mock_pydicom):
        """Test searching DICOM files by criteria"""
        # Create test file structure
        test_dir = os.path.join(self.temp_dir, 'test_dicoms')
        os.makedirs(test_dir)
        test_file = os.path.join(test_dir, 'test.dcm')
        
        # Create empty file
        with open(test_file, 'w') as f:
            f.write('')
        
        # Mock dataset
        mock_dataset = Mock()
        mock_dataset.PatientID = '12345'
        mock_dataset.Modality = 'CT'
        mock_pydicom.dcmread.return_value = mock_dataset
        
        processor = DICOMProcessor(self.temp_dir)
        
        # Mock extract_metadata
        with patch.object(processor, 'extract_metadata') as mock_extract:
            mock_metadata = Mock()
            mock_metadata.patient_id = '12345'
            mock_metadata.modality = 'CT'
            mock_extract.return_value = mock_metadata
            
            results = processor.search_dicom_by_criteria(test_dir, {'patient_id': '12345'})
            self.assertEqual(len(results), 1)


class TestDICOMStorage(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.storage = DICOMStorage(self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_storage_initialization(self):
        """Test storage initialization creates directories"""
        self.assertTrue(os.path.exists(self.temp_dir))
        self.assertEqual(self.storage.storage_root, self.temp_dir)
    
    @patch('os.chmod')
    def test_store_dicom_secure(self, mock_chmod):
        """Test secure DICOM storage"""
        mock_dataset = Mock()
        mock_dataset.SOPInstanceUID = '1.2.3.4.5.6.7'
        mock_dataset.save_as = Mock()
        
        result_path = self.storage.store_dicom_secure(
            mock_dataset, 'patient123', 'study456'
        )
        
        self.assertTrue(result_path.startswith(self.temp_dir))
        mock_dataset.save_as.assert_called_once()
        mock_chmod.assert_called_once_with(result_path, 0o600)
    
    def test_create_storage_index(self):
        """Test storage index creation"""
        # Create test directory structure
        patient_dir = os.path.join(self.temp_dir, 'patient123')
        study_dir = os.path.join(patient_dir, 'study456')
        os.makedirs(study_dir)
        
        # Create test DICOM file
        test_file = os.path.join(study_dir, 'test.dcm')
        with open(test_file, 'w') as f:
            f.write('')
        
        index = self.storage.create_storage_index()
        
        self.assertIn('patient123', index)
        self.assertEqual(len(index['patient123']['studies']), 1)
        self.assertEqual(index['patient123']['total_files'], 1)


if __name__ == '__main__':
    unittest.main()