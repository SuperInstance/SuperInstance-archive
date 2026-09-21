"""
Tests for E-Discovery Export Formats
"""
import unittest
import datetime
import tempfile
import os
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from ..src.export_formats import (
    EDiscoveryExporter, EDRMXMLGenerator, ConcordanceGenerator, CSVGenerator, RelativityGenerator,
    DocumentMetadata, ProductionSet, ExportFormat, DocumentType, PrivilegeLevel, ProductionStatus
)


class TestDocumentMetadata(unittest.TestCase):
    
    def test_document_metadata_creation(self):
        """Test creating document metadata"""
        doc_metadata = DocumentMetadata(
            document_id="DOC-001",
            control_number="CTRL-001",
            title="Test Document",
            author="John Doe",
            date_created=datetime.datetime(2024, 1, 15, 10, 30),
            file_name="test.pdf",
            file_size=102400,
            document_type=DocumentType.DOCUMENT,
            privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
            production_status=ProductionStatus.PRODUCED
        )
        
        self.assertEqual(doc_metadata.document_id, "DOC-001")
        self.assertEqual(doc_metadata.control_number, "CTRL-001")
        self.assertEqual(doc_metadata.title, "Test Document")
        self.assertEqual(doc_metadata.author, "John Doe")
        self.assertEqual(doc_metadata.file_size, 102400)
        self.assertEqual(doc_metadata.document_type, DocumentType.DOCUMENT)
        self.assertEqual(doc_metadata.privilege_level, PrivilegeLevel.NOT_PRIVILEGED)


class TestProductionSet(unittest.TestCase):
    
    def setUp(self):
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Contract Agreement",
                author="Alice Smith",
                date_created=datetime.datetime(2024, 1, 15),
                document_type=DocumentType.DOCUMENT,
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED
            ),
            DocumentMetadata(
                document_id="DOC-002",
                control_number="CTRL-002",
                title="Email Communication",
                author="Bob Jones",
                recipients=["alice@company.com"],
                subject="Project Update",
                date_created=datetime.datetime(2024, 1, 16),
                document_type=DocumentType.EMAIL,
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED
            )
        ]
    
    def test_production_set_creation(self):
        """Test creating production set"""
        production_set = ProductionSet(
            production_id="PROD-001",
            production_name="First Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.EDRM_XML
        )
        
        self.assertEqual(production_set.production_id, "PROD-001")
        self.assertEqual(production_set.case_number, "CASE-2024-001")
        self.assertEqual(len(production_set.documents), 2)
        self.assertEqual(production_set.format, ExportFormat.EDRM_XML)


class TestEDRMXMLGenerator(unittest.TestCase):
    
    def setUp(self):
        self.generator = EDRMXMLGenerator()
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Test Document",
                author="John Doe",
                date_created=datetime.datetime(2024, 1, 15),
                document_type=DocumentType.DOCUMENT,
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED
            )
        ]
        
        self.production_set = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.EDRM_XML
        )
    
    def test_generate_edrm_xml(self):
        """Test EDRM XML generation"""
        xml_content = self.generator.generate_edrm_xml(self.production_set)
        
        self.assertIsInstance(xml_content, str)
        self.assertIn('<?xml version=', xml_content)
        self.assertIn('EDRM', xml_content)
        self.assertIn('Production', xml_content)
        self.assertIn('PROD-001', xml_content)
        self.assertIn('CASE-2024-001', xml_content)
        
        # Parse XML to verify structure
        root = ET.fromstring(xml_content)
        self.assertEqual(root.tag, 'EDRM')
        
        # Check production element
        production = root.find('Production')
        self.assertIsNotNone(production)
        self.assertEqual(production.get('ProductionID'), 'PROD-001')
        
        # Check documents
        documents = production.find('Documents')
        self.assertIsNotNone(documents)
        
        document_elements = documents.findall('Document')
        self.assertEqual(len(document_elements), 1)
        
        doc_elem = document_elements[0]
        self.assertEqual(doc_elem.get('DocumentID'), 'DOC-001')
        self.assertEqual(doc_elem.get('ControlNumber'), 'CTRL-001')
    
    def test_create_document_element(self):
        """Test document element creation"""
        doc = self.sample_docs[0]
        doc_elem = self.generator._create_document_element(doc)
        
        self.assertEqual(doc_elem.tag, 'Document')
        self.assertEqual(doc_elem.get('DocumentID'), 'DOC-001')
        
        # Check child elements
        title_elem = doc_elem.find('Title')
        self.assertIsNotNone(title_elem)
        self.assertEqual(title_elem.text, 'Test Document')
        
        author_elem = doc_elem.find('Author')
        self.assertIsNotNone(author_elem)
        self.assertEqual(author_elem.text, 'John Doe')
    
    def test_email_document_element(self):
        """Test email-specific document element creation"""
        email_doc = DocumentMetadata(
            document_id="EMAIL-001",
            control_number="CTRL-002",
            title="Email Subject",
            author="sender@company.com",
            recipients=["recipient@company.com"],
            subject="Important Message",
            date_sent=datetime.datetime(2024, 1, 15, 14, 30),
            date_received=datetime.datetime(2024, 1, 15, 14, 31),
            document_type=DocumentType.EMAIL
        )
        
        doc_elem = self.generator._create_document_element(email_doc)
        
        # Check email-specific elements
        recipients_elem = doc_elem.find('Recipients')
        self.assertIsNotNone(recipients_elem)
        self.assertEqual(recipients_elem.text, 'recipient@company.com')
        
        sent_elem = doc_elem.find('DateSent')
        self.assertIsNotNone(sent_elem)
        
        received_elem = doc_elem.find('DateReceived')
        self.assertIsNotNone(received_elem)


class TestConcordanceGenerator(unittest.TestCase):
    
    def setUp(self):
        self.generator = ConcordanceGenerator()
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Test Document",
                author="John Doe",
                date_created=datetime.datetime(2024, 1, 15, 10, 30),
                file_name="test.pdf",
                file_size=102400,
                custodian="John Smith",
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED
            )
        ]
        
        self.production_set = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.CONCORDANCE
        )
    
    def test_generate_concordance_dat(self):
        """Test Concordance DAT file generation"""
        dat_content = self.generator.generate_concordance_dat(self.production_set)
        
        self.assertIsInstance(dat_content, str)
        self.assertIn('DOC-001', dat_content)
        self.assertIn('CTRL-001', dat_content)
        self.assertIn('Test Document', dat_content)
        self.assertIn('John Doe', dat_content)
        
        # Check for Concordance delimiters
        self.assertIn(chr(254), dat_content)  # Quote character
        
        # Verify field count (should have specific number of fields)
        lines = dat_content.split('\n')
        self.assertEqual(len(lines), 1)  # One document = one line
        
        fields = lines[0].split(chr(20))  # ASCII 20 delimiter
        self.assertGreater(len(fields), 10)  # Should have multiple fields


class TestCSVGenerator(unittest.TestCase):
    
    def setUp(self):
        self.generator = CSVGenerator()
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Test Document",
                author="John Doe",
                date_created=datetime.datetime(2024, 1, 15),
                file_name="test.pdf",
                file_size=102400,
                custodian="John Smith",
                document_type=DocumentType.DOCUMENT,
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED,
                has_attachments=False,
                tags=["contract", "important"]
            ),
            DocumentMetadata(
                document_id="DOC-002",
                control_number="CTRL-002",
                title="Email Message",
                author="Jane Smith",
                date_created=datetime.datetime(2024, 1, 16),
                document_type=DocumentType.EMAIL,
                privilege_level=PrivilegeLevel.ATTORNEY_CLIENT,
                production_status=ProductionStatus.WITHHELD
            )
        ]
        
        self.production_set = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.CSV
        )
    
    def test_generate_csv(self):
        """Test CSV generation"""
        csv_content = self.generator.generate_csv(self.production_set)
        
        self.assertIsInstance(csv_content, str)
        
        # Parse CSV content
        import csv
        import io
        
        csv_reader = csv.reader(io.StringIO(csv_content))
        rows = list(csv_reader)
        
        # Check header row
        self.assertEqual(len(rows), 3)  # Header + 2 data rows
        headers = rows[0]
        self.assertIn("Document ID", headers)
        self.assertIn("Control Number", headers)
        self.assertIn("Title", headers)
        self.assertIn("Author", headers)
        
        # Check data rows
        doc1_row = rows[1]
        self.assertEqual(doc1_row[0], "DOC-001")  # Document ID
        self.assertEqual(doc1_row[1], "CTRL-001")  # Control Number
        self.assertEqual(doc1_row[2], "Test Document")  # Title
        self.assertIn("contract; important", doc1_row)  # Tags should be joined


class TestRelativityGenerator(unittest.TestCase):
    
    def setUp(self):
        self.generator = RelativityGenerator()
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Test Document",
                author="John Doe",
                date_created=datetime.datetime(2024, 1, 15),
                document_type=DocumentType.DOCUMENT,
                page_count=3
            ),
            DocumentMetadata(
                document_id="DOC-002",
                control_number="CTRL-002",
                title="Image File",
                document_type=DocumentType.IMAGE,
                page_count=1
            )
        ]
        
        self.production_set = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.RELATIVITY
        )
    
    def test_generate_relativity_load_file(self):
        """Test Relativity load file generation"""
        load_files = self.generator.generate_relativity_load_file(self.production_set)
        
        self.assertIn("control_file", load_files)
        self.assertIn("data_file", load_files)
        self.assertIn("opticon_file", load_files)
        
        # Test control file
        control_file = load_files["control_file"]
        self.assertIn("Relativity Control File", control_file)
        self.assertIn("DOCUMENT_ID,1", control_file)
        self.assertIn("CONTROL_NUMBER,2", control_file)
        
        # Test data file
        data_file = load_files["data_file"]
        self.assertIn("DOC-001", data_file)
        self.assertIn("CTRL-001", data_file)
        self.assertIn("Test Document", data_file)
        
        # Test opticon file
        opticon_file = load_files["opticon_file"]
        # Should have entries for documents with images
        lines = opticon_file.split('\n')
        self.assertGreater(len(lines), 0)
        # Should have entries for each page
        ctrl_001_lines = [line for line in lines if 'CTRL-001' in line]
        self.assertEqual(len(ctrl_001_lines), 3)  # 3 pages


class TestEDiscoveryExporter(unittest.TestCase):
    
    def setUp(self):
        self.exporter = EDiscoveryExporter()
        self.temp_dir = tempfile.mkdtemp()
        
        self.sample_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",
                title="Test Document",
                author="John Doe",
                date_created=datetime.datetime(2024, 1, 15),
                document_type=DocumentType.DOCUMENT,
                privilege_level=PrivilegeLevel.NOT_PRIVILEGED,
                production_status=ProductionStatus.PRODUCED
            )
        ]
        
        self.production_set = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=self.sample_docs,
            format=ExportFormat.EDRM_XML
        )
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_edrm_xml(self):
        """Test EDRM XML export"""
        result = self.exporter.export_production_set(
            self.production_set, ExportFormat.EDRM_XML, self.temp_dir
        )
        
        self.assertEqual(result["production_id"], "PROD-001")
        self.assertEqual(result["export_format"], "edrm_xml")
        self.assertEqual(result["document_count"], 1)
        self.assertGreater(len(result["files_created"]), 0)
        
        # Check that XML file was created
        xml_files = [f for f in result["files_created"] if f.endswith('.xml')]
        self.assertEqual(len(xml_files), 1)
        
        # Verify file exists and has content
        xml_file = Path(xml_files[0])
        self.assertTrue(xml_file.exists())
        
        with open(xml_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        self.assertIn('EDRM', xml_content)
        self.assertIn('PROD-001', xml_content)
    
    def test_export_csv(self):
        """Test CSV export"""
        result = self.exporter.export_production_set(
            self.production_set, ExportFormat.CSV, self.temp_dir
        )
        
        self.assertEqual(result["export_format"], "csv")
        
        # Check that CSV file was created
        csv_files = [f for f in result["files_created"] if f.endswith('.csv')]
        self.assertEqual(len(csv_files), 1)
        
        # Verify file content
        csv_file = Path(csv_files[0])
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_content = f.read()
        
        self.assertIn('Document ID', csv_content)  # Header
        self.assertIn('DOC-001', csv_content)  # Data
    
    def test_export_relativity(self):
        """Test Relativity export"""
        result = self.exporter.export_production_set(
            self.production_set, ExportFormat.RELATIVITY, self.temp_dir
        )
        
        self.assertEqual(result["export_format"], "relativity")
        
        # Should create multiple files for Relativity
        created_files = result["files_created"]
        
        ctl_files = [f for f in created_files if f.endswith('.ctl')]
        dat_files = [f for f in created_files if f.endswith('.dat')]
        opt_files = [f for f in created_files if f.endswith('.opt')]
        
        self.assertEqual(len(ctl_files), 1)
        self.assertEqual(len(dat_files), 1)
        self.assertEqual(len(opt_files), 1)
    
    def test_export_json(self):
        """Test JSON export"""
        result = self.exporter.export_production_set(
            self.production_set, ExportFormat.JSON, self.temp_dir
        )
        
        self.assertEqual(result["export_format"], "json")
        
        # Check that JSON file was created
        json_files = [f for f in result["files_created"] if f.endswith('.json')]
        self.assertEqual(len(json_files), 1)
        
        # Verify JSON content
        json_file = Path(json_files[0])
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        self.assertIn('production_set', json_data)
        self.assertIn('export_metadata', json_data)
        self.assertEqual(json_data['production_set']['production_id'], 'PROD-001')
    
    def test_unsupported_format(self):
        """Test error handling for unsupported format"""
        with self.assertRaises(ValueError):
            # Create a mock format that's not implemented
            self.exporter.export_production_set(
                self.production_set, ExportFormat.PST, self.temp_dir
            )
    
    def test_validate_production_set_valid(self):
        """Test production set validation - valid case"""
        validation = self.exporter.validate_production_set(self.production_set)
        
        self.assertTrue(validation["is_valid"])
        self.assertEqual(len(validation["errors"]), 0)
        self.assertEqual(validation["statistics"]["total_documents"], 1)
    
    def test_validate_production_set_invalid(self):
        """Test production set validation - invalid case"""
        # Create invalid production set
        invalid_production = ProductionSet(
            production_id="",  # Missing required field
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="",  # Missing required field
            documents=[],  # No documents
            format=ExportFormat.CSV
        )
        
        validation = self.exporter.validate_production_set(invalid_production)
        
        self.assertFalse(validation["is_valid"])
        self.assertGreater(len(validation["errors"]), 0)
        
        # Check specific errors
        errors = validation["errors"]
        self.assertTrue(any("Production ID is required" in error for error in errors))
        self.assertTrue(any("Case number is required" in error for error in errors))
        self.assertTrue(any("No documents in production set" in error for error in errors))
    
    def test_validate_production_set_duplicate_control_numbers(self):
        """Test validation with duplicate control numbers"""
        duplicate_docs = [
            DocumentMetadata(
                document_id="DOC-001",
                control_number="CTRL-001",  # Duplicate
                title="Doc 1"
            ),
            DocumentMetadata(
                document_id="DOC-002",
                control_number="CTRL-001",  # Duplicate
                title="Doc 2"
            )
        ]
        
        production_with_duplicates = ProductionSet(
            production_id="PROD-001",
            production_name="Test Production",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-001",
            documents=duplicate_docs,
            format=ExportFormat.CSV
        )
        
        validation = self.exporter.validate_production_set(production_with_duplicates)
        
        self.assertFalse(validation["is_valid"])
        self.assertTrue(any("Duplicate control numbers" in error for error in validation["errors"]))
    
    @patch('shutil.copy2')
    def test_export_native_files(self, mock_copy):
        """Test native file export"""
        # Create a test file
        test_file = Path(self.temp_dir) / "test.pdf"
        test_file.write_text("Test content")
        
        # Update document to point to test file
        self.sample_docs[0].file_path = str(test_file)
        self.sample_docs[0].file_name = "original.pdf"
        
        # Mock the copy operation
        mock_copy.return_value = None
        
        output_dir = Path(self.temp_dir) / "native_export"
        result = self.exporter._export_native_files(self.production_set, output_dir)
        
        self.assertIn("native_export", result)
        native_result = result["native_export"]
        
        self.assertEqual(native_result["files_exported"], 1)
        self.assertEqual(native_result["files_missing"], 0)
        
        # Check that metadata file was created
        metadata_file = output_dir / "native_metadata.csv"
        self.assertTrue(metadata_file.exists())
    
    def test_generate_privilege_log(self):
        """Test privilege log generation"""
        # Add privileged documents
        privileged_docs = [
            DocumentMetadata(
                document_id="PRIV-001",
                control_number="CTRL-PRIV-001",
                title="Attorney Communication",
                author="Attorney",
                subject="Legal Advice",
                date_created=datetime.datetime(2024, 1, 15),
                privilege_level=PrivilegeLevel.ATTORNEY_CLIENT
            ),
            DocumentMetadata(
                document_id="PRIV-002",
                control_number="CTRL-PRIV-002",
                title="Work Product",
                author="Legal Team",
                date_created=datetime.datetime(2024, 1, 16),
                privilege_level=PrivilegeLevel.WORK_PRODUCT
            )
        ]
        
        privileged_production = ProductionSet(
            production_id="PRIV-PROD-001",
            production_name="Privilege Log Test",
            production_date=datetime.datetime.now(),
            requesting_party="Plaintiff",
            producing_party="Defendant",
            case_number="CASE-2024-001",
            documents=privileged_docs,
            format=ExportFormat.CSV
        )
        
        privilege_log = self.exporter.generate_privilege_log(privileged_production)
        
        self.assertIsInstance(privilege_log, str)
        self.assertIn("Privilege Log", privilege_log)
        self.assertIn("CASE-2024-001", privilege_log)
        self.assertIn("CTRL-PRIV-001", privilege_log)
        self.assertIn("attorney_client", privilege_log)
        self.assertIn("work_product", privilege_log)
    
    def test_generate_privilege_log_no_privileged_docs(self):
        """Test privilege log with no privileged documents"""
        privilege_log = self.exporter.generate_privilege_log(self.production_set)
        
        self.assertEqual(privilege_log, "No privileged documents found.")
    
    def test_create_production_package(self):
        """Test creating comprehensive production package"""
        formats = [ExportFormat.CSV, ExportFormat.JSON]
        
        package_path = self.exporter.create_production_package(
            self.production_set,
            formats,
            self.temp_dir,
            include_natives=False
        )
        
        self.assertTrue(package_path.endswith('.zip'))
        self.assertTrue(Path(package_path).exists())
        
        # Verify ZIP contents
        import zipfile
        with zipfile.ZipFile(package_path, 'r') as zipf:
            file_list = zipf.namelist()
            
            # Should have manifest
            self.assertTrue(any('manifest.json' in f for f in file_list))
            
            # Should have files from each format
            self.assertTrue(any('csv/' in f for f in file_list))
            self.assertTrue(any('json/' in f for f in file_list))


if __name__ == '__main__':
    unittest.main()