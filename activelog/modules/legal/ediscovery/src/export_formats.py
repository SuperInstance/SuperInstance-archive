"""
E-Discovery Export Formats
Comprehensive export system for legal discovery documents in standard formats.
"""
import datetime
import json
import logging
import os
import uuid
import zipfile
import csv
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import base64
import hashlib


class ExportFormat(Enum):
    """Supported e-discovery export formats"""
    NATIVE = "native"
    TIFF_PDF = "tiff_pdf" 
    PST = "pst"
    EML = "eml"
    CSV = "csv"
    XML = "xml"
    JSON = "json"
    CONCORDANCE = "concordance"
    SUMMATION = "summation"
    RELATIVITY = "relativity"
    EDRM_XML = "edrm_xml"
    MBOX = "mbox"
    PDF_PORTFOLIO = "pdf_portfolio"


class DocumentType(Enum):
    """Types of documents for e-discovery"""
    EMAIL = "email"
    DOCUMENT = "document"
    SPREADSHEET = "spreadsheet"
    PRESENTATION = "presentation"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DATABASE = "database"
    WEB_PAGE = "web_page"
    INSTANT_MESSAGE = "instant_message"
    SOCIAL_MEDIA = "social_media"
    CAD_DRAWING = "cad_drawing"
    OTHER = "other"


class PrivilegeLevel(Enum):
    """Document privilege levels"""
    NOT_PRIVILEGED = "not_privileged"
    ATTORNEY_CLIENT = "attorney_client"
    WORK_PRODUCT = "work_product"
    PRIVILEGED = "privileged"
    CONFIDENTIAL = "confidential"
    HIGHLY_CONFIDENTIAL = "highly_confidential"


class ProductionStatus(Enum):
    """Document production status"""
    PRODUCED = "produced"
    WITHHELD = "withheld"
    REDACTED = "redacted"
    CLAWED_BACK = "clawed_back"
    PENDING_REVIEW = "pending_review"


@dataclass
class DocumentMetadata:
    """Metadata for e-discovery document"""
    document_id: str
    control_number: str
    title: str
    author: Optional[str] = None
    recipients: Optional[List[str]] = None
    cc_recipients: Optional[List[str]] = None
    bcc_recipients: Optional[List[str]] = None
    subject: Optional[str] = None
    date_created: Optional[datetime.datetime] = None
    date_modified: Optional[datetime.datetime] = None
    date_sent: Optional[datetime.datetime] = None
    date_received: Optional[datetime.datetime] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    file_extension: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    hash_md5: Optional[str] = None
    hash_sha256: Optional[str] = None
    document_type: Optional[DocumentType] = None
    privilege_level: Optional[PrivilegeLevel] = None
    production_status: Optional[ProductionStatus] = None
    custodian: Optional[str] = None
    source_location: Optional[str] = None
    extracted_text: Optional[str] = None
    page_count: Optional[int] = None
    attachment_count: Optional[int] = None
    has_attachments: bool = False
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None
    conversation_id: Optional[str] = None
    thread_id: Optional[str] = None
    tags: Optional[List[str]] = None
    custom_fields: Optional[Dict[str, Any]] = None


@dataclass
class ProductionSet:
    """E-discovery production set"""
    production_id: str
    production_name: str
    production_date: datetime.datetime
    requesting_party: str
    producing_party: str
    case_number: str
    documents: List[DocumentMetadata]
    format: ExportFormat
    description: Optional[str] = None
    privilege_log: Optional[List[DocumentMetadata]] = None
    confidentiality_designation: Optional[str] = None
    total_documents: Optional[int] = None
    total_pages: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


class EDRMXMLGenerator:
    """Generate EDRM XML format for e-discovery"""
    
    def __init__(self):
        self.namespace = "http://www.edrm.net/schema/edrm-2-0"
    
    def generate_edrm_xml(self, production_set: ProductionSet) -> str:
        """Generate EDRM XML for production set"""
        # Create root element
        root = ET.Element("EDRM", attrib={
            "xmlns": self.namespace,
            "Version": "2.0"
        })
        
        # Add production information
        production_elem = ET.SubElement(root, "Production")
        production_elem.set("ProductionID", production_set.production_id)
        production_elem.set("ProductionName", production_set.production_name)
        production_elem.set("ProductionDate", production_set.production_date.isoformat())
        
        # Add case information
        case_elem = ET.SubElement(production_elem, "Case")
        case_elem.set("CaseNumber", production_set.case_number)
        case_elem.set("RequestingParty", production_set.requesting_party)
        case_elem.set("ProducingParty", production_set.producing_party)
        
        # Add documents
        documents_elem = ET.SubElement(production_elem, "Documents")
        
        for doc in production_set.documents:
            doc_elem = self._create_document_element(doc)
            documents_elem.append(doc_elem)
        
        # Add privilege log if present
        if production_set.privilege_log:
            privilege_elem = ET.SubElement(production_elem, "PrivilegeLog")
            for doc in production_set.privilege_log:
                priv_doc_elem = self._create_document_element(doc)
                privilege_elem.append(priv_doc_elem)
        
        # Convert to string
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _create_document_element(self, doc: DocumentMetadata) -> ET.Element:
        """Create XML element for document"""
        doc_elem = ET.Element("Document")
        doc_elem.set("DocumentID", doc.document_id)
        doc_elem.set("ControlNumber", doc.control_number)
        
        # Add metadata fields
        if doc.title:
            title_elem = ET.SubElement(doc_elem, "Title")
            title_elem.text = doc.title
        
        if doc.author:
            author_elem = ET.SubElement(doc_elem, "Author")
            author_elem.text = doc.author
        
        if doc.subject:
            subject_elem = ET.SubElement(doc_elem, "Subject")
            subject_elem.text = doc.subject
        
        if doc.date_created:
            created_elem = ET.SubElement(doc_elem, "DateCreated")
            created_elem.text = doc.date_created.isoformat()
        
        if doc.date_modified:
            modified_elem = ET.SubElement(doc_elem, "DateModified")
            modified_elem.text = doc.date_modified.isoformat()
        
        if doc.file_name:
            filename_elem = ET.SubElement(doc_elem, "FileName")
            filename_elem.text = doc.file_name
        
        if doc.file_size:
            size_elem = ET.SubElement(doc_elem, "FileSize")
            size_elem.text = str(doc.file_size)
        
        if doc.hash_md5:
            hash_elem = ET.SubElement(doc_elem, "HashMD5")
            hash_elem.text = doc.hash_md5
        
        if doc.custodian:
            custodian_elem = ET.SubElement(doc_elem, "Custodian")
            custodian_elem.text = doc.custodian
        
        if doc.privilege_level:
            privilege_elem = ET.SubElement(doc_elem, "PrivilegeLevel")
            privilege_elem.text = doc.privilege_level.value
        
        if doc.production_status:
            status_elem = ET.SubElement(doc_elem, "ProductionStatus")
            status_elem.text = doc.production_status.value
        
        # Add email-specific fields
        if doc.document_type == DocumentType.EMAIL:
            if doc.recipients:
                recipients_elem = ET.SubElement(doc_elem, "Recipients")
                recipients_elem.text = "; ".join(doc.recipients)
            
            if doc.date_sent:
                sent_elem = ET.SubElement(doc_elem, "DateSent")
                sent_elem.text = doc.date_sent.isoformat()
            
            if doc.date_received:
                received_elem = ET.SubElement(doc_elem, "DateReceived")
                received_elem.text = doc.date_received.isoformat()
        
        return doc_elem


class ConcordanceGenerator:
    """Generate Concordance DAT file format"""
    
    def __init__(self):
        self.delimiter = chr(20)  # ASCII 20 (Concordance delimiter)
        self.quote_char = chr(254)  # ASCII 254 (Concordance quote)
    
    def generate_concordance_dat(self, production_set: ProductionSet) -> str:
        """Generate Concordance DAT file content"""
        output_lines = []
        
        # Define field mappings
        field_mappings = [
            ("DOCID", "document_id"),
            ("BEGDOC", "control_number"),
            ("ENDDOC", "control_number"),
            ("TITLE", "title"),
            ("AUTHOR", "author"),
            ("SUBJECT", "subject"),
            ("DATECREATED", "date_created"),
            ("DATEMODIFIED", "date_modified"),
            ("FILENAME", "file_name"),
            ("FILESIZE", "file_size"),
            ("CUSTODIAN", "custodian"),
            ("PRIVILEGE", "privilege_level"),
            ("PRODUCTION", "production_status")
        ]
        
        for doc in production_set.documents:
            fields = []
            
            for field_name, attr_name in field_mappings:
                value = getattr(doc, attr_name, "")
                
                if value is None:
                    value = ""
                elif isinstance(value, datetime.datetime):
                    value = value.strftime("%m/%d/%Y %H:%M:%S")
                elif isinstance(value, (PrivilegeLevel, ProductionStatus, DocumentType)):
                    value = value.value
                else:
                    value = str(value)
                
                # Escape delimiters and quotes
                value = value.replace(self.delimiter, " ")
                value = value.replace(self.quote_char, "'")
                
                fields.append(f"{self.quote_char}{value}{self.quote_char}")
            
            output_lines.append(self.delimiter.join(fields))
        
        return "\n".join(output_lines)


class CSVGenerator:
    """Generate CSV format for e-discovery"""
    
    def generate_csv(self, production_set: ProductionSet) -> str:
        """Generate CSV content for production set"""
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Define headers
        headers = [
            "Document ID", "Control Number", "Title", "Author", "Subject",
            "Date Created", "Date Modified", "File Name", "File Size",
            "Custodian", "Privilege Level", "Production Status", "Document Type",
            "Hash MD5", "Page Count", "Has Attachments", "Tags"
        ]
        
        writer.writerow(headers)
        
        # Write document data
        for doc in production_set.documents:
            row = [
                doc.document_id,
                doc.control_number,
                doc.title or "",
                doc.author or "",
                doc.subject or "",
                doc.date_created.isoformat() if doc.date_created else "",
                doc.date_modified.isoformat() if doc.date_modified else "",
                doc.file_name or "",
                doc.file_size or "",
                doc.custodian or "",
                doc.privilege_level.value if doc.privilege_level else "",
                doc.production_status.value if doc.production_status else "",
                doc.document_type.value if doc.document_type else "",
                doc.hash_md5 or "",
                doc.page_count or "",
                doc.has_attachments,
                "; ".join(doc.tags) if doc.tags else ""
            ]
            writer.writerow(row)
        
        return output.getvalue()


class RelativityGenerator:
    """Generate Relativity load file format"""
    
    def generate_relativity_load_file(self, production_set: ProductionSet) -> Dict[str, str]:
        """Generate Relativity load files"""
        # Generate control file (.ctl)
        control_file = self._generate_control_file(production_set)
        
        # Generate data file (.dat)
        data_file = self._generate_data_file(production_set)
        
        # Generate opticon file (.opt) for images
        opticon_file = self._generate_opticon_file(production_set)
        
        return {
            "control_file": control_file,
            "data_file": data_file,
            "opticon_file": opticon_file
        }
    
    def _generate_control_file(self, production_set: ProductionSet) -> str:
        """Generate Relativity control file"""
        lines = [
            f"# Relativity Control File",
            f"# Production: {production_set.production_name}",
            f"# Date: {production_set.production_date.isoformat()}",
            f"",
            f"DOCUMENT_ID,1",
            f"CONTROL_NUMBER,2", 
            f"TITLE,3",
            f"AUTHOR,4",
            f"SUBJECT,5",
            f"DATE_CREATED,6",
            f"DATE_MODIFIED,7",
            f"FILE_NAME,8",
            f"FILE_SIZE,9",
            f"CUSTODIAN,10",
            f"PRIVILEGE_LEVEL,11",
            f"PRODUCTION_STATUS,12"
        ]
        
        return "\n".join(lines)
    
    def _generate_data_file(self, production_set: ProductionSet) -> str:
        """Generate Relativity data file"""
        lines = []
        
        for doc in production_set.documents:
            fields = [
                doc.document_id,
                doc.control_number,
                doc.title or "",
                doc.author or "",
                doc.subject or "",
                doc.date_created.isoformat() if doc.date_created else "",
                doc.date_modified.isoformat() if doc.date_modified else "",
                doc.file_name or "",
                str(doc.file_size) if doc.file_size else "",
                doc.custodian or "",
                doc.privilege_level.value if doc.privilege_level else "",
                doc.production_status.value if doc.production_status else ""
            ]
            
            # Escape and quote fields
            escaped_fields = []
            for field in fields:
                field = str(field).replace('"', '""')  # Escape quotes
                escaped_fields.append(f'"{field}"')
            
            lines.append(",".join(escaped_fields))
        
        return "\n".join(lines)
    
    def _generate_opticon_file(self, production_set: ProductionSet) -> str:
        """Generate Opticon file for image production"""
        lines = []
        
        for doc in production_set.documents:
            if doc.document_type in [DocumentType.IMAGE, DocumentType.DOCUMENT]:
                # Simulate image file paths
                page_count = doc.page_count or 1
                
                for page_num in range(1, page_count + 1):
                    image_path = f"IMAGES\\{doc.control_number}_{page_num:04d}.tif"
                    text_path = f"TEXT\\{doc.control_number}_{page_num:04d}.txt"
                    
                    line = f"{doc.control_number},{page_num},{image_path},{text_path},Y"
                    lines.append(line)
        
        return "\n".join(lines)


class EDiscoveryExporter:
    """Main e-discovery export system"""
    
    def __init__(self):
        self.edrm_generator = EDRMXMLGenerator()
        self.concordance_generator = ConcordanceGenerator()
        self.csv_generator = CSVGenerator()
        self.relativity_generator = RelativityGenerator()
    
    def export_production_set(self, production_set: ProductionSet, 
                            export_format: ExportFormat,
                            output_path: str) -> Dict[str, Any]:
        """Export production set in specified format"""
        
        export_result = {
            "production_id": production_set.production_id,
            "export_format": export_format.value,
            "output_path": output_path,
            "exported_at": datetime.datetime.utcnow(),
            "document_count": len(production_set.documents),
            "files_created": [],
            "metadata": {}
        }
        
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if export_format == ExportFormat.EDRM_XML:
            xml_content = self.edrm_generator.generate_edrm_xml(production_set)
            xml_file = output_dir / f"{production_set.production_id}_edrm.xml"
            
            with open(xml_file, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            
            export_result["files_created"].append(str(xml_file))
        
        elif export_format == ExportFormat.CONCORDANCE:
            dat_content = self.concordance_generator.generate_concordance_dat(production_set)
            dat_file = output_dir / f"{production_set.production_id}.dat"
            
            with open(dat_file, 'w', encoding='utf-8') as f:
                f.write(dat_content)
            
            export_result["files_created"].append(str(dat_file))
        
        elif export_format == ExportFormat.CSV:
            csv_content = self.csv_generator.generate_csv(production_set)
            csv_file = output_dir / f"{production_set.production_id}.csv"
            
            with open(csv_file, 'w', encoding='utf-8', newline='') as f:
                f.write(csv_content)
            
            export_result["files_created"].append(str(csv_file))
        
        elif export_format == ExportFormat.RELATIVITY:
            rel_files = self.relativity_generator.generate_relativity_load_file(production_set)
            
            # Write control file
            ctl_file = output_dir / f"{production_set.production_id}.ctl"
            with open(ctl_file, 'w', encoding='utf-8') as f:
                f.write(rel_files["control_file"])
            export_result["files_created"].append(str(ctl_file))
            
            # Write data file
            dat_file = output_dir / f"{production_set.production_id}.dat"
            with open(dat_file, 'w', encoding='utf-8') as f:
                f.write(rel_files["data_file"])
            export_result["files_created"].append(str(dat_file))
            
            # Write opticon file
            opt_file = output_dir / f"{production_set.production_id}.opt"
            with open(opt_file, 'w', encoding='utf-8') as f:
                f.write(rel_files["opticon_file"])
            export_result["files_created"].append(str(opt_file))
        
        elif export_format == ExportFormat.JSON:
            json_data = {
                "production_set": asdict(production_set),
                "export_metadata": export_result
            }
            
            # Convert datetime objects to ISO strings for JSON serialization
            json_data = self._serialize_datetime_objects(json_data)
            
            json_file = output_dir / f"{production_set.production_id}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            export_result["files_created"].append(str(json_file))
        
        elif export_format == ExportFormat.NATIVE:
            # Export native files with metadata
            native_result = self._export_native_files(production_set, output_dir)
            export_result.update(native_result)
        
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
        
        # Generate export log
        log_file = output_dir / f"{production_set.production_id}_export_log.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"E-Discovery Export Log\n")
            f.write(f"{'=' * 40}\n")
            f.write(f"Production ID: {production_set.production_id}\n")
            f.write(f"Production Name: {production_set.production_name}\n")
            f.write(f"Export Format: {export_format.value}\n")
            f.write(f"Export Date: {export_result['exported_at'].isoformat()}\n")
            f.write(f"Document Count: {export_result['document_count']}\n")
            f.write(f"Files Created: {len(export_result['files_created'])}\n")
            f.write(f"\nFiles:\n")
            for file_path in export_result['files_created']:
                f.write(f"  - {file_path}\n")
        
        export_result["files_created"].append(str(log_file))
        
        logging.info(f"Exported production set {production_set.production_id} in {export_format.value} format")
        
        return export_result
    
    def create_production_package(self, production_set: ProductionSet,
                                export_formats: List[ExportFormat],
                                output_path: str,
                                include_natives: bool = True) -> str:
        """Create comprehensive production package with multiple formats"""
        
        package_dir = Path(output_path) / f"{production_set.production_id}_package"
        package_dir.mkdir(parents=True, exist_ok=True)
        
        export_results = []
        
        # Export in each requested format
        for export_format in export_formats:
            format_dir = package_dir / export_format.value
            result = self.export_production_set(production_set, export_format, str(format_dir))
            export_results.append(result)
        
        # Include native files if requested
        if include_natives:
            native_dir = package_dir / "native_files"
            native_result = self._export_native_files(production_set, native_dir)
            export_results.append(native_result)
        
        # Create package manifest
        manifest = {
            "production_package": {
                "production_id": production_set.production_id,
                "production_name": production_set.production_name,
                "case_number": production_set.case_number,
                "created_at": datetime.datetime.utcnow().isoformat(),
                "total_documents": len(production_set.documents),
                "formats_included": [fmt.value for fmt in export_formats],
                "includes_natives": include_natives
            },
            "exports": export_results
        }
        
        manifest_file = package_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, default=str)
        
        # Create ZIP package
        zip_file = Path(output_path) / f"{production_set.production_id}_package.zip"
        
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in package_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_dir)
                    zipf.write(file_path, arcname)
        
        logging.info(f"Created production package: {zip_file}")
        
        return str(zip_file)
    
    def validate_production_set(self, production_set: ProductionSet) -> Dict[str, Any]:
        """Validate production set for export"""
        validation_result = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "statistics": {}
        }
        
        # Check required fields
        if not production_set.production_id:
            validation_result["errors"].append("Production ID is required")
            validation_result["is_valid"] = False
        
        if not production_set.case_number:
            validation_result["errors"].append("Case number is required")
            validation_result["is_valid"] = False
        
        if not production_set.documents:
            validation_result["errors"].append("No documents in production set")
            validation_result["is_valid"] = False
        
        # Validate documents
        document_errors = 0
        privileged_count = 0
        duplicate_control_numbers = set()
        control_numbers_seen = set()
        
        for i, doc in enumerate(production_set.documents):
            doc_prefix = f"Document {i+1}"
            
            if not doc.document_id:
                validation_result["errors"].append(f"{doc_prefix}: Missing document ID")
                document_errors += 1
            
            if not doc.control_number:
                validation_result["errors"].append(f"{doc_prefix}: Missing control number")
                document_errors += 1
            elif doc.control_number in control_numbers_seen:
                duplicate_control_numbers.add(doc.control_number)
            else:
                control_numbers_seen.add(doc.control_number)
            
            if doc.privilege_level and doc.privilege_level != PrivilegeLevel.NOT_PRIVILEGED:
                privileged_count += 1
            
            if doc.file_path and not Path(doc.file_path).exists():
                validation_result["warnings"].append(f"{doc_prefix}: File not found at {doc.file_path}")
        
        if duplicate_control_numbers:
            validation_result["errors"].append(f"Duplicate control numbers: {duplicate_control_numbers}")
            validation_result["is_valid"] = False
        
        # Generate statistics
        validation_result["statistics"] = {
            "total_documents": len(production_set.documents),
            "document_errors": document_errors,
            "privileged_documents": privileged_count,
            "duplicate_control_numbers": len(duplicate_control_numbers),
            "document_types": self._count_document_types(production_set.documents)
        }
        
        if document_errors > 0:
            validation_result["is_valid"] = False
        
        return validation_result
    
    def _export_native_files(self, production_set: ProductionSet, output_dir: Path) -> Dict[str, Any]:
        """Export native files with metadata"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        native_dir = output_dir / "files"
        native_dir.mkdir(exist_ok=True)
        
        files_exported = []
        files_missing = []
        
        for doc in production_set.documents:
            if doc.file_path and Path(doc.file_path).exists():
                src_file = Path(doc.file_path)
                
                # Preserve original filename or use control number
                if doc.file_name:
                    dest_name = f"{doc.control_number}_{doc.file_name}"
                else:
                    dest_name = f"{doc.control_number}{src_file.suffix}"
                
                dest_file = native_dir / dest_name
                
                # Copy file
                import shutil
                shutil.copy2(src_file, dest_file)
                files_exported.append(str(dest_file))
            
            else:
                files_missing.append(doc.control_number)
        
        # Create metadata file
        metadata_file = output_dir / "native_metadata.csv"
        with open(metadata_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Control Number", "Document ID", "Original Path", "Exported File", "Status"])
            
            for doc in production_set.documents:
                status = "Exported" if doc.file_path and Path(doc.file_path).exists() else "Missing"
                exported_file = f"{doc.control_number}_{doc.file_name}" if doc.file_name else f"{doc.control_number}"
                
                writer.writerow([
                    doc.control_number,
                    doc.document_id,
                    doc.file_path or "",
                    exported_file if status == "Exported" else "",
                    status
                ])
        
        return {
            "native_export": {
                "files_exported": len(files_exported),
                "files_missing": len(files_missing),
                "missing_files": files_missing,
                "metadata_file": str(metadata_file)
            }
        }
    
    def _serialize_datetime_objects(self, obj: Any) -> Any:
        """Convert datetime objects to ISO strings for JSON serialization"""
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._serialize_datetime_objects(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._serialize_datetime_objects(item) for item in obj]
        elif hasattr(obj, '__dict__'):
            return {key: self._serialize_datetime_objects(value) for key, value in obj.__dict__.items()}
        else:
            return obj
    
    def _count_document_types(self, documents: List[DocumentMetadata]) -> Dict[str, int]:
        """Count documents by type"""
        type_counts = {}
        
        for doc in documents:
            doc_type = doc.document_type.value if doc.document_type else "unknown"
            type_counts[doc_type] = type_counts.get(doc_type, 0) + 1
        
        return type_counts
    
    def generate_privilege_log(self, production_set: ProductionSet) -> str:
        """Generate privilege log for withheld documents"""
        privileged_docs = [
            doc for doc in production_set.documents
            if doc.privilege_level and doc.privilege_level != PrivilegeLevel.NOT_PRIVILEGED
        ]
        
        if not privileged_docs:
            return "No privileged documents found."
        
        # Generate CSV format privilege log
        output = []
        output.append("Privilege Log")
        output.append(f"Case: {production_set.case_number}")
        output.append(f"Production: {production_set.production_name}")
        output.append(f"Date: {production_set.production_date.strftime('%m/%d/%Y')}")
        output.append("")
        
        # Headers
        output.append("Control Number,Date,Author,Recipients,Subject,Privilege Basis,Description")
        
        for doc in privileged_docs:
            row = [
                doc.control_number,
                doc.date_created.strftime('%m/%d/%Y') if doc.date_created else "",
                doc.author or "",
                "; ".join(doc.recipients) if doc.recipients else "",
                doc.subject or "",
                doc.privilege_level.value if doc.privilege_level else "",
                doc.title or ""
            ]
            
            # Escape CSV fields
            escaped_row = []
            for field in row:
                if ',' in field or '"' in field or '\n' in field:
                    escaped_row.append(f'"{field.replace('"', '""')}"')
                else:
                    escaped_row.append(field)
            
            output.append(",".join(escaped_row))
        
        return "\n".join(output)