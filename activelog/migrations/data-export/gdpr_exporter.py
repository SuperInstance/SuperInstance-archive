"""
GDPR-Compliant Data Export Utilities for ActiveLog
Comprehensive user data export system for privacy compliance (GDPR, CCPA, etc.)
"""

import os
import json
import asyncio
import aiofiles
import zipfile
import tempfile
import hashlib
import csv
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncGenerator, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging
from enum import Enum
import shutil
import xml.etree.ElementTree as ET
from jinja2 import Template
import sqlite3
import pandas as pd


class ExportFormat(Enum):
    """Supported export formats."""
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    PDF = "pdf"
    HTML = "html"
    COMPLETE = "complete"  # All formats


class DataCategory(Enum):
    """GDPR data categories."""
    IDENTITY = "identity"
    CONTACT = "contact"
    PERSONAL = "personal"
    USAGE = "usage"
    PREFERENCES = "preferences"
    FILES = "files"
    METADATA = "metadata"
    LOGS = "logs"
    COMMUNICATIONS = "communications"
    FINANCIAL = "financial"


@dataclass
class ExportRequest:
    """User data export request."""
    user_id: str
    request_id: str
    requested_by: str
    request_date: datetime
    export_formats: List[ExportFormat]
    data_categories: List[DataCategory]
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    include_deleted: bool = False
    anonymize_others: bool = True
    status: str = 'pending'
    completion_date: Optional[datetime] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


@dataclass
class ExportedDataset:
    """Represents an exported dataset."""
    category: DataCategory
    format: ExportFormat
    file_path: str
    record_count: int
    size_bytes: int
    checksum: str
    schema_version: str
    export_date: datetime


class GDPRExporter:
    """GDPR-compliant data exporter for ActiveLog users."""
    
    def __init__(self, db_config: Dict[str, Any], storage_config: Dict[str, Any]):
        self.db_config = db_config
        self.storage_config = storage_config
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Export configuration
        self.config = {
            'max_file_size': 2 * 1024 * 1024 * 1024,  # 2GB per archive
            'retention_days': 30,  # How long to keep exports
            'batch_size': 1000,
            'include_system_metadata': True,
            'anonymize_referenced_users': True,
            'encrypt_exports': True,
            'formats': {
                ExportFormat.JSON: {'extension': '.json', 'mime_type': 'application/json'},
                ExportFormat.XML: {'extension': '.xml', 'mime_type': 'application/xml'},
                ExportFormat.CSV: {'extension': '.csv', 'mime_type': 'text/csv'},
                ExportFormat.HTML: {'extension': '.html', 'mime_type': 'text/html'},
                ExportFormat.PDF: {'extension': '.pdf', 'mime_type': 'application/pdf'}
            }
        }
        
        # Data mapping configuration
        self.data_mappings = {
            DataCategory.IDENTITY: {
                'tables': ['users', 'user_profiles'],
                'fields': ['id', 'username', 'email', 'full_name', 'date_of_birth', 'profile_picture'],
                'description': 'User identity and profile information'
            },
            DataCategory.CONTACT: {
                'tables': ['user_contacts', 'addresses'],
                'fields': ['phone', 'address', 'country', 'timezone'],
                'description': 'Contact information and addresses'
            },
            DataCategory.PERSONAL: {
                'tables': ['user_preferences', 'user_settings'],
                'fields': ['language', 'theme', 'notifications', 'privacy_settings'],
                'description': 'Personal preferences and settings'
            },
            DataCategory.USAGE: {
                'tables': ['user_sessions', 'activity_logs', 'usage_analytics'],
                'fields': ['login_time', 'ip_address', 'user_agent', 'actions', 'duration'],
                'description': 'Platform usage and activity data'
            },
            DataCategory.FILES: {
                'tables': ['files', 'file_versions', 'file_shares'],
                'fields': ['filename', 'content', 'metadata', 'upload_date', 'tags'],
                'description': 'User files and associated metadata'
            },
            DataCategory.METADATA: {
                'tables': ['file_metadata', 'search_indices', 'classifications'],
                'fields': ['extracted_text', 'ai_tags', 'similarity_vectors'],
                'description': 'Automatically generated metadata and AI analysis'
            },
            DataCategory.COMMUNICATIONS: {
                'tables': ['messages', 'comments', 'notifications'],
                'fields': ['content', 'recipients', 'timestamps', 'read_status'],
                'description': 'Communications and messaging data'
            },
            DataCategory.LOGS: {
                'tables': ['audit_logs', 'error_logs', 'security_events'],
                'fields': ['timestamp', 'event_type', 'details', 'ip_address'],
                'description': 'System logs and audit trails'
            }
        }
    
    async def create_export_request(self, user_id: str, requested_by: str, 
                                  export_formats: List[str], data_categories: List[str],
                                  **kwargs) -> ExportRequest:
        """Create a new export request."""
        
        request_id = f"export_{user_id}_{int(datetime.now().timestamp())}"
        
        export_request = ExportRequest(
            user_id=user_id,
            request_id=request_id,
            requested_by=requested_by,
            request_date=datetime.now(timezone.utc),
            export_formats=[ExportFormat(f) for f in export_formats],
            data_categories=[DataCategory(c) for c in data_categories],
            date_range_start=kwargs.get('date_range_start'),
            date_range_end=kwargs.get('date_range_end'),
            include_deleted=kwargs.get('include_deleted', False),
            anonymize_others=kwargs.get('anonymize_others', True)
        )
        
        # Store request in database
        await self._store_export_request(export_request)
        
        self.logger.info(f"Created export request {request_id} for user {user_id}")
        return export_request
    
    async def process_export_request(self, request_id: str) -> str:
        """Process an export request and generate export package."""
        
        # Retrieve request
        export_request = await self._get_export_request(request_id)
        if not export_request:
            raise ValueError(f"Export request {request_id} not found")
        
        self.logger.info(f"Processing export request {request_id}")
        export_request.status = 'processing'
        await self._update_export_request(export_request)
        
        try:
            # Create temporary directory for export
            with tempfile.TemporaryDirectory() as temp_dir:
                export_dir = Path(temp_dir) / request_id
                export_dir.mkdir(parents=True, exist_ok=True)
                
                # Export data in requested formats
                exported_datasets = []
                
                for category in export_request.data_categories:
                    for format in export_request.export_formats:
                        dataset = await self._export_data_category(
                            export_request, category, format, export_dir
                        )
                        if dataset:
                            exported_datasets.append(dataset)
                
                # Generate export manifest
                await self._generate_export_manifest(export_request, exported_datasets, export_dir)
                
                # Generate human-readable report
                await self._generate_export_report(export_request, exported_datasets, export_dir)
                
                # Create archive
                archive_path = await self._create_export_archive(export_request, export_dir)
                
                # Store archive and update request
                final_path = await self._store_export_archive(archive_path, request_id)
                
                export_request.status = 'completed'
                export_request.completion_date = datetime.now(timezone.utc)
                export_request.download_url = final_path
                export_request.expires_at = datetime.now(timezone.utc).replace(
                    day=datetime.now().day + self.config['retention_days']
                )
                
                await self._update_export_request(export_request)
                
                self.logger.info(f"Export request {request_id} completed: {final_path}")
                return final_path
                
        except Exception as e:
            export_request.status = 'failed'
            await self._update_export_request(export_request)
            self.logger.error(f"Export request {request_id} failed: {e}")
            raise
    
    async def _export_data_category(self, request: ExportRequest, category: DataCategory, 
                                  format: ExportFormat, export_dir: Path) -> Optional[ExportedDataset]:
        """Export data for a specific category and format."""
        
        if category not in self.data_mappings:
            self.logger.warning(f"No mapping defined for category {category}")
            return None
        
        category_config = self.data_mappings[category]
        
        # Extract data from database
        data = await self._extract_category_data(request, category, category_config)
        
        if not data:
            self.logger.info(f"No data found for category {category}")
            return None
        
        # Generate filename
        filename = f"{category.value}_{format.value}{self.config['formats'][format]['extension']}"
        file_path = export_dir / filename
        
        # Export in requested format
        if format == ExportFormat.JSON:
            await self._export_as_json(data, file_path)
        elif format == ExportFormat.XML:
            await self._export_as_xml(data, file_path, category)
        elif format == ExportFormat.CSV:
            await self._export_as_csv(data, file_path)
        elif format == ExportFormat.HTML:
            await self._export_as_html(data, file_path, category, category_config)
        else:
            self.logger.warning(f"Unsupported export format: {format}")
            return None
        
        # Calculate file stats
        stat = os.stat(file_path)
        checksum = self._calculate_checksum(str(file_path))
        
        return ExportedDataset(
            category=category,
            format=format,
            file_path=str(file_path),
            record_count=len(data) if isinstance(data, list) else 1,
            size_bytes=stat.st_size,
            checksum=checksum,
            schema_version="1.0",
            export_date=datetime.now(timezone.utc)
        )
    
    async def _extract_category_data(self, request: ExportRequest, category: DataCategory, 
                                   config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data from database for a category."""
        
        data = []
        
        # This would connect to the actual database
        # For demo purposes, generating sample data
        
        if category == DataCategory.IDENTITY:
            data = [{
                'user_id': request.user_id,
                'username': f'user_{request.user_id}',
                'email': f'user_{request.user_id}@example.com',
                'full_name': 'John Doe',
                'registration_date': '2023-01-01T00:00:00Z',
                'last_login': '2024-12-01T10:30:00Z',
                'account_status': 'active'
            }]
        
        elif category == DataCategory.FILES:
            data = [
                {
                    'file_id': f'file_{i}',
                    'filename': f'document_{i}.pdf',
                    'upload_date': '2024-11-01T10:00:00Z',
                    'file_size': 1024 * (i + 1),
                    'mime_type': 'application/pdf',
                    'tags': ['work', 'important']
                }
                for i in range(10)
            ]
        
        elif category == DataCategory.USAGE:
            data = [
                {
                    'session_id': f'session_{i}',
                    'login_time': f'2024-12-{i:02d}T10:00:00Z',
                    'logout_time': f'2024-12-{i:02d}T12:00:00Z',
                    'ip_address': f'192.168.1.{100 + i}' if not request.anonymize_others else '[ANONYMIZED]',
                    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'actions_count': 25 + i
                }
                for i in range(1, 11)
            ]
        
        elif category == DataCategory.COMMUNICATIONS:
            data = [
                {
                    'message_id': f'msg_{i}',
                    'timestamp': f'2024-12-{i:02d}T15:30:00Z',
                    'message_type': 'comment',
                    'content': f'This is sample message content {i}',
                    'recipients': ['user_2', 'user_3'] if not request.anonymize_others else ['[ANONYMIZED]'],
                    'read_status': 'read' if i % 2 == 0 else 'unread'
                }
                for i in range(1, 6)
            ]
        
        # Apply date range filtering if specified
        if request.date_range_start or request.date_range_end:
            data = self._filter_by_date_range(data, request.date_range_start, request.date_range_end)
        
        return data
    
    def _filter_by_date_range(self, data: List[Dict[str, Any]], start_date: Optional[datetime], 
                            end_date: Optional[datetime]) -> List[Dict[str, Any]]:
        """Filter data by date range."""
        # Implementation would filter based on actual date fields
        # For demo, returning all data
        return data
    
    async def _export_as_json(self, data: List[Dict[str, Any]], file_path: Path):
        """Export data as JSON."""
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(json.dumps(data, indent=2, default=str))
    
    async def _export_as_xml(self, data: List[Dict[str, Any]], file_path: Path, category: DataCategory):
        """Export data as XML."""
        root = ET.Element('export')
        root.set('category', category.value)
        root.set('export_date', datetime.now().isoformat())
        
        for record in data:
            record_elem = ET.SubElement(root, 'record')
            for key, value in record.items():
                field_elem = ET.SubElement(record_elem, key)
                field_elem.text = str(value) if value is not None else ''
        
        tree = ET.ElementTree(root)
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
    
    async def _export_as_csv(self, data: List[Dict[str, Any]], file_path: Path):
        """Export data as CSV."""
        if not data:
            return
        
        async with aiofiles.open(file_path, 'w', newline='') as f:
            # Convert to pandas for easier CSV handling
            df = pd.DataFrame(data)
            csv_content = df.to_csv(index=False)
            await f.write(csv_content)
    
    async def _export_as_html(self, data: List[Dict[str, Any]], file_path: Path, 
                            category: DataCategory, config: Dict[str, Any]):
        """Export data as HTML."""
        
        html_template = Template('''
<!DOCTYPE html>
<html>
<head>
    <title>{{ category_name }} Export</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f0f0f0; padding: 20px; border-radius: 5px; margin-bottom: 20px; }
        .section { margin-bottom: 30px; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .metadata { color: #666; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ category_name }} Data Export</h1>
        <p class="metadata">
            Export Date: {{ export_date }}<br>
            Description: {{ description }}<br>
            Record Count: {{ record_count }}
        </p>
    </div>
    
    <div class="section">
        <h2>Data Records</h2>
        {% if records %}
        <table>
            <thead>
                <tr>
                {% for field in records[0].keys() %}
                    <th>{{ field.replace('_', ' ').title() }}</th>
                {% endfor %}
                </tr>
            </thead>
            <tbody>
            {% for record in records %}
                <tr>
                {% for value in record.values() %}
                    <td>{{ value if value is not none else '' }}</td>
                {% endfor %}
                </tr>
            {% endfor %}
            </tbody>
        </table>
        {% else %}
        <p>No data records found.</p>
        {% endif %}
    </div>
</body>
</html>
        ''')
        
        html_content = html_template.render(
            category_name=category.value.replace('_', ' ').title(),
            export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            description=config.get('description', ''),
            record_count=len(data),
            records=data
        )
        
        async with aiofiles.open(file_path, 'w') as f:
            await f.write(html_content)
    
    async def _generate_export_manifest(self, request: ExportRequest, 
                                      datasets: List[ExportedDataset], export_dir: Path):
        """Generate export manifest file."""
        
        manifest = {
            'export_info': {
                'request_id': request.request_id,
                'user_id': request.user_id,
                'export_date': datetime.now(timezone.utc).isoformat(),
                'requested_by': request.requested_by,
                'request_date': request.request_date.isoformat(),
                'gdpr_compliance': True,
                'data_controller': 'ActiveLog Platform',
                'retention_period': f"{self.config['retention_days']} days"
            },
            'export_scope': {
                'data_categories': [cat.value for cat in request.data_categories],
                'export_formats': [fmt.value for fmt in request.export_formats],
                'date_range': {
                    'start': request.date_range_start.isoformat() if request.date_range_start else None,
                    'end': request.date_range_end.isoformat() if request.date_range_end else None
                },
                'include_deleted': request.include_deleted,
                'anonymize_others': request.anonymize_others
            },
            'datasets': [asdict(dataset) for dataset in datasets],
            'data_rights_info': {
                'right_to_access': 'This export provides access to your personal data as per GDPR Article 15',
                'right_to_portability': 'Data is provided in machine-readable formats as per GDPR Article 20',
                'right_to_rectification': 'Contact support to update any incorrect information',
                'right_to_erasure': 'Contact support to request deletion of your data',
                'data_retention': f'This export will be automatically deleted after {self.config["retention_days"]} days'
            },
            'technical_info': {
                'schema_version': '1.0',
                'export_tool': 'ActiveLog GDPR Exporter v1.0',
                'checksum_algorithm': 'SHA-256',
                'total_files': len(datasets),
                'total_size_bytes': sum(ds.size_bytes for ds in datasets)
            }
        }
        
        manifest_path = export_dir / 'export_manifest.json'
        async with aiofiles.open(manifest_path, 'w') as f:
            await f.write(json.dumps(manifest, indent=2))
    
    async def _generate_export_report(self, request: ExportRequest, 
                                    datasets: List[ExportedDataset], export_dir: Path):
        """Generate human-readable export report."""
        
        report_template = Template('''
# Personal Data Export Report

**Export Request ID:** {{ request_id }}  
**User ID:** {{ user_id }}  
**Export Date:** {{ export_date }}  
**Requested By:** {{ requested_by }}

## Export Summary

This export contains your personal data from ActiveLog platform in accordance with:
- General Data Protection Regulation (GDPR) Article 15 (Right of Access)
- General Data Protection Regulation (GDPR) Article 20 (Right to Data Portability)

### Data Categories Exported

{% for category in categories %}
- **{{ category.name }}**: {{ category.description }}
{% endfor %}

### Export Files

{% for dataset in datasets %}
- **{{ dataset.category.value }}.{{ dataset.format.value }}**
  - Records: {{ dataset.record_count }}
  - Size: {{ "%.2f"|format(dataset.size_bytes / 1024 / 1024) }} MB
  - Checksum: {{ dataset.checksum[:16] }}...
{% endfor %}

### Your Data Rights

Under GDPR, you have the following rights regarding your personal data:

1. **Right to Access (Article 15)**: You can request access to your personal data (this export fulfills this right)
2. **Right to Rectification (Article 16)**: You can request correction of inaccurate data
3. **Right to Erasure (Article 17)**: You can request deletion of your data
4. **Right to Restrict Processing (Article 18)**: You can request limitation of data processing
5. **Right to Data Portability (Article 20)**: You can request your data in machine-readable format (this export fulfills this right)
6. **Right to Object (Article 21)**: You can object to certain types of data processing

To exercise any of these rights, please contact our Data Protection Officer at: privacy@activelog.com

### Technical Information

- **Export Tool**: ActiveLog GDPR Exporter v1.0
- **Data Controller**: ActiveLog Platform
- **Export Retention**: This export will be automatically deleted after {{ retention_days }} days
- **Data Anonymization**: Other users' identifiable information has been anonymized as requested

### Important Notes

1. This export contains all personal data associated with your account as of the export date
2. Some technical metadata may be included to ensure data integrity
3. File attachments and binary content are included when technically feasible
4. For questions about this export, contact: privacy@activelog.com

---
*This export was generated automatically by ActiveLog's GDPR-compliant data export system.*
        ''')
        
        # Prepare template data
        categories_info = []
        for cat in request.data_categories:
            if cat in self.data_mappings:
                categories_info.append({
                    'name': cat.value.replace('_', ' ').title(),
                    'description': self.data_mappings[cat]['description']
                })
        
        report_content = report_template.render(
            request_id=request.request_id,
            user_id=request.user_id,
            export_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            requested_by=request.requested_by,
            categories=categories_info,
            datasets=datasets,
            retention_days=self.config['retention_days']
        )
        
        report_path = export_dir / 'README.md'
        async with aiofiles.open(report_path, 'w') as f:
            await f.write(report_content)
    
    async def _create_export_archive(self, request: ExportRequest, export_dir: Path) -> str:
        """Create ZIP archive of export files."""
        
        archive_filename = f"activelog_export_{request.user_id}_{request.request_id}.zip"
        archive_path = export_dir.parent / archive_filename
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in export_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(export_dir)
                    zipf.write(file_path, arcname)
        
        return str(archive_path)
    
    async def _store_export_archive(self, archive_path: str, request_id: str) -> str:
        """Store export archive in designated location."""
        
        storage_dir = Path(self.storage_config.get('export_storage_path', '/tmp/activelog_exports'))
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        final_path = storage_dir / Path(archive_path).name
        shutil.move(archive_path, final_path)
        
        return str(final_path)
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate SHA256 checksum."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    async def _store_export_request(self, request: ExportRequest):
        """Store export request in database."""
        # In production, this would store in actual database
        requests_dir = Path('/tmp/activelog_export_requests')
        requests_dir.mkdir(exist_ok=True)
        
        request_file = requests_dir / f"{request.request_id}.json"
        async with aiofiles.open(request_file, 'w') as f:
            await f.write(json.dumps(asdict(request), indent=2, default=str))
    
    async def _get_export_request(self, request_id: str) -> Optional[ExportRequest]:
        """Retrieve export request from database."""
        request_file = Path(f'/tmp/activelog_export_requests/{request_id}.json')
        
        if not request_file.exists():
            return None
        
        async with aiofiles.open(request_file, 'r') as f:
            data = json.loads(await f.read())
        
        # Convert back to ExportRequest object
        request = ExportRequest(**data)
        # Convert string dates back to datetime objects
        request.request_date = datetime.fromisoformat(data['request_date'])
        if data.get('completion_date'):
            request.completion_date = datetime.fromisoformat(data['completion_date'])
        if data.get('expires_at'):
            request.expires_at = datetime.fromisoformat(data['expires_at'])
        
        return request
    
    async def _update_export_request(self, request: ExportRequest):
        """Update export request in database."""
        await self._store_export_request(request)
    
    async def list_user_exports(self, user_id: str) -> List[ExportRequest]:
        """List all export requests for a user."""
        requests_dir = Path('/tmp/activelog_export_requests')
        if not requests_dir.exists():
            return []
        
        user_requests = []
        for request_file in requests_dir.glob(f'export_{user_id}_*.json'):
            request = await self._get_export_request(request_file.stem)
            if request:
                user_requests.append(request)
        
        return sorted(user_requests, key=lambda x: x.request_date, reverse=True)
    
    async def cleanup_expired_exports(self):
        """Clean up expired export files."""
        storage_dir = Path(self.storage_config.get('export_storage_path', '/tmp/activelog_exports'))
        requests_dir = Path('/tmp/activelog_export_requests')
        
        if not storage_dir.exists() or not requests_dir.exists():
            return
        
        expired_count = 0
        
        for request_file in requests_dir.glob('*.json'):
            request = await self._get_export_request(request_file.stem)
            if request and request.expires_at and datetime.now(timezone.utc) > request.expires_at:
                # Delete export file
                if request.download_url and Path(request.download_url).exists():
                    os.unlink(request.download_url)
                
                # Delete request record
                os.unlink(request_file)
                expired_count += 1
        
        self.logger.info(f"Cleaned up {expired_count} expired exports")


async def demo_gdpr_export():
    """Demo GDPR export functionality."""
    print("📋 GDPR Data Export Demo")
    print("=" * 50)
    
    # Configuration
    db_config = {'host': 'localhost', 'database': 'activelog'}
    storage_config = {'export_storage_path': '/tmp/activelog_exports'}
    
    # Initialize exporter
    exporter = GDPRExporter(db_config, storage_config)
    
    # Create export request
    user_id = 'demo_user_12345'
    request = await exporter.create_export_request(
        user_id=user_id,
        requested_by=user_id,
        export_formats=['json', 'html', 'csv'],
        data_categories=['identity', 'files', 'usage', 'communications'],
        include_deleted=False,
        anonymize_others=True
    )
    
    print(f"Created export request: {request.request_id}")
    
    # Process export
    try:
        export_path = await exporter.process_export_request(request.request_id)
        print(f"Export completed: {export_path}")
        
        # List user exports
        user_exports = await exporter.list_user_exports(user_id)
        print(f"User has {len(user_exports)} total exports")
        
        # Show export contents
        if os.path.exists(export_path):
            with zipfile.ZipFile(export_path, 'r') as zf:
                print("\\nExport contents:")
                for file_info in zf.filelist:
                    print(f"  - {file_info.filename} ({file_info.file_size} bytes)")
    
    except Exception as e:
        print(f"Export failed: {e}")
    
    print("\\n✅ GDPR export demo completed!")


def main():
    """Main function for demo."""
    asyncio.run(demo_gdpr_export())


if __name__ == "__main__":
    main()