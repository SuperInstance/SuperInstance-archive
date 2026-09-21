"""
GDPR-compliant Data Export with comprehensive user data collection
"""

import os
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional, Set
import hashlib
import csv

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.colors import black, blue, gray
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
import pandas as pd

from ..core.config import settings
from ..utils.file_utils import get_file_metadata, get_files_by_filters
from ..utils.metadata_extractor import MetadataExtractor

logger = logging.getLogger(__name__)

class GDPRExporter:
    """GDPR-compliant data export with comprehensive user data collection"""
    
    def __init__(self):
        self.metadata_extractor = MetadataExtractor()
        self.styles = None
        self.gdpr_categories = self._define_gdpr_categories()
        
    async def initialize(self):
        """Initialize GDPR exporter"""
        self.styles = self._create_styles()
        logger.info("GDPR exporter initialized")
    
    def _define_gdpr_categories(self) -> Dict[str, Dict[str, Any]]:
        """Define GDPR data categories and their handling"""
        
        return {
            "personal_files": {
                "name": "Personal Files and Documents",
                "description": "User-uploaded files, documents, and media",
                "legal_basis": "Contract performance",
                "retention_period": "Account lifetime + 30 days",
                "anonymizable": False
            },
            "account_data": {
                "name": "Account Information", 
                "description": "User profile, settings, and account details",
                "legal_basis": "Contract performance",
                "retention_period": "Account lifetime + 7 years",
                "anonymizable": True
            },
            "usage_data": {
                "name": "Usage and Analytics Data",
                "description": "Application usage, feature interaction, performance metrics",
                "legal_basis": "Legitimate interest",
                "retention_period": "2 years from collection",
                "anonymizable": True
            },
            "system_logs": {
                "name": "System and Security Logs",
                "description": "Authentication logs, error logs, security events",
                "legal_basis": "Legitimate interest / Legal obligation",
                "retention_period": "1 year from generation",
                "anonymizable": True
            },
            "communication_data": {
                "name": "Communications and Support",
                "description": "Support tickets, notifications, email communications",
                "legal_basis": "Contract performance",
                "retention_period": "3 years from last contact",
                "anonymizable": False
            },
            "technical_data": {
                "name": "Technical and Device Data",
                "description": "IP addresses, device info, browser data, cookies",
                "legal_basis": "Legitimate interest",
                "retention_period": "1 year from collection",
                "anonymizable": True
            },
            "sharing_data": {
                "name": "Shared Content and Collaborations",
                "description": "Shared files, collaboration data, permissions",
                "legal_basis": "Contract performance",
                "retention_period": "Account lifetime + 30 days",
                "anonymizable": False
            }
        }
    
    def _create_styles(self):
        """Create PDF styles for GDPR export"""
        
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='GDPRTitle',
            parent=styles['Title'],
            fontSize=20,
            spaceAfter=20,
            textColor=black,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='CategoryHeader',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=12,
            textColor=blue,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='SubSection',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=8,
            textColor=black,
            fontName='Helvetica-Bold'
        ))
        
        styles.add(ParagraphStyle(
            name='LegalText',
            parent=styles['Normal'],
            fontSize=10,
            textColor=gray,
            fontName='Helvetica-Oblique'
        ))
        
        return styles
    
    def export(self, job_id: str, config: Dict[str, Any],
              filters: Dict[str, Any], output_dir: str,
              progress_callback: Callable) -> Dict[str, Any]:
        """
        Generate GDPR-compliant data export
        
        Args:
            job_id: Export job identifier
            config: GDPR export configuration
            filters: Data selection filters (user_id is primary filter)
            output_dir: Output directory path
            progress_callback: Progress reporting callback
            
        Returns:
            Export result with GDPR package path and metadata
        """
        
        try:
            progress_callback(0, 100, "Initializing GDPR export")
            
            # Get GDPR configuration
            gdpr_config = self._get_gdpr_config(config)
            user_id = filters.get("user_id")
            
            if not user_id:
                return {"success": False, "error": "User ID required for GDPR export"}
            
            # Create GDPR export directory
            gdpr_dir = os.path.join(output_dir, "gdpr_export")
            os.makedirs(gdpr_dir, exist_ok=True)
            
            progress_callback(10, 100, "Collecting user data")
            
            # Collect all user data
            user_data = self._collect_user_data(user_id, gdpr_config, progress_callback)
            
            progress_callback(40, 100, "Generating data exports")
            
            # Generate data exports
            export_results = self._generate_data_exports(
                user_data, gdpr_dir, gdpr_config, progress_callback
            )
            
            progress_callback(70, 100, "Creating GDPR documentation")
            
            # Generate GDPR documentation
            self._generate_gdpr_documentation(
                user_data, gdpr_dir, gdpr_config, progress_callback
            )
            
            progress_callback(85, 100, "Creating export package")
            
            # Create final archive
            archive_path = os.path.join(output_dir, f"gdpr_export_{job_id}.zip")
            self._create_gdpr_archive(gdpr_dir, archive_path)
            
            progress_callback(100, 100, "GDPR export completed")
            
            return {
                "success": True,
                "output_path": archive_path,
                "filename": f"gdpr_export_{job_id}.zip",
                "file_size": os.path.getsize(archive_path),
                "categories_exported": list(user_data.keys()),
                "data_summary": export_results
            }
            
        except Exception as e:
            logger.error(f"GDPR export failed for job {job_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_gdpr_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get GDPR export configuration with defaults"""
        
        return {
            "include_deleted": config.get("include_deleted", settings.security.gdpr_include_logs),
            "include_system_logs": config.get("include_system_logs", settings.security.gdpr_include_logs),
            "anonymize_ip_addresses": config.get("anonymize_ip_addresses", settings.security.gdpr_anonymize_ips),
            "export_format": config.get("export_format", "multiple"),  # json, csv, pdf, multiple
            "include_metadata": config.get("include_metadata", True),
            "include_legal_info": config.get("include_legal_info", True),
            "data_categories": config.get("data_categories", list(self.gdpr_categories.keys())),
            "time_range_days": config.get("time_range_days", None),  # None = all time
            "compression_level": config.get("compression_level", 9),
            "create_manifest": config.get("create_manifest", True),
            "hash_verification": config.get("hash_verification", True)
        }
    
    def _collect_user_data(self, user_id: str, config: Dict[str, Any],
                          progress_callback: Callable) -> Dict[str, Any]:
        """Collect comprehensive user data across all categories"""
        
        user_data = {}
        total_categories = len(config["data_categories"])
        
        for i, category in enumerate(config["data_categories"]):
            progress = 10 + (i / total_categories * 30)
            progress_callback(progress, 100, f"Collecting {category} data")
            
            try:
                if category == "personal_files":
                    user_data[category] = self._collect_personal_files(user_id, config)
                elif category == "account_data":
                    user_data[category] = self._collect_account_data(user_id, config)
                elif category == "usage_data":
                    user_data[category] = self._collect_usage_data(user_id, config)
                elif category == "system_logs":
                    user_data[category] = self._collect_system_logs(user_id, config)
                elif category == "communication_data":
                    user_data[category] = self._collect_communication_data(user_id, config)
                elif category == "technical_data":
                    user_data[category] = self._collect_technical_data(user_id, config)
                elif category == "sharing_data":
                    user_data[category] = self._collect_sharing_data(user_id, config)
                else:
                    logger.warning(f"Unknown GDPR category: {category}")
                    
            except Exception as e:
                logger.error(f"Failed to collect {category} data: {e}")
                user_data[category] = {"error": str(e), "items": []}
        
        return user_data
    
    def _collect_personal_files(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect user's personal files and documents"""
        
        # In a real implementation, this would query the database for user files
        # For this example, we'll simulate the data structure
        
        files_data = {
            "category": "personal_files",
            "collected_at": datetime.utcnow().isoformat(),
            "total_files": 0,
            "total_size_bytes": 0,
            "items": []
        }
        
        try:
            # Simulate file collection (replace with actual database queries)
            # Example query: SELECT * FROM files WHERE user_id = user_id AND deleted = false
            
            # For demo, get files from filters if provided
            mock_files = [
                {
                    "file_id": "file_001",
                    "filename": "document1.pdf",
                    "path": "/user/documents/document1.pdf",
                    "size": 1024000,
                    "created_at": "2024-01-15T10:30:00Z",
                    "modified_at": "2024-01-15T10:30:00Z",
                    "file_type": "application/pdf",
                    "checksum": "abc123def456",
                    "tags": ["work", "important"],
                    "shared_with": []
                },
                {
                    "file_id": "file_002", 
                    "filename": "photo1.jpg",
                    "path": "/user/photos/photo1.jpg",
                    "size": 2048000,
                    "created_at": "2024-02-01T14:20:00Z",
                    "modified_at": "2024-02-01T14:20:00Z",
                    "file_type": "image/jpeg",
                    "checksum": "def456ghi789",
                    "tags": ["family", "vacation"],
                    "shared_with": ["user_456"]
                }
            ]
            
            files_data["items"] = mock_files
            files_data["total_files"] = len(mock_files)
            files_data["total_size_bytes"] = sum(f["size"] for f in mock_files)
            
        except Exception as e:
            logger.error(f"Failed to collect personal files: {e}")
            files_data["error"] = str(e)
        
        return files_data
    
    def _collect_account_data(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect user account information"""
        
        account_data = {
            "category": "account_data",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        try:
            # Mock account data (replace with actual database queries)
            mock_account = {
                "user_id": user_id,
                "email": "user@example.com",
                "username": "example_user",
                "display_name": "Example User",
                "created_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-03-15T09:30:00Z",
                "account_status": "active",
                "email_verified": True,
                "two_factor_enabled": True,
                "preferences": {
                    "language": "en",
                    "timezone": "UTC",
                    "notifications_enabled": True,
                    "theme": "light"
                },
                "subscription": {
                    "plan": "premium",
                    "started_at": "2024-01-15T00:00:00Z",
                    "expires_at": "2025-01-15T00:00:00Z"
                }
            }
            
            account_data["items"].append(mock_account)
            
        except Exception as e:
            logger.error(f"Failed to collect account data: {e}")
            account_data["error"] = str(e)
        
        return account_data
    
    def _collect_usage_data(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect usage analytics and interaction data"""
        
        usage_data = {
            "category": "usage_data",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        try:
            # Mock usage data
            mock_usage = [
                {
                    "session_id": "session_001",
                    "started_at": "2024-03-15T09:00:00Z",
                    "ended_at": "2024-03-15T10:30:00Z",
                    "duration_minutes": 90,
                    "pages_visited": ["/dashboard", "/files", "/settings"],
                    "actions_performed": ["file_upload", "file_share", "settings_update"],
                    "device_info": "anonymized",
                    "ip_address": "192.168.1.xxx" if config["anonymize_ip_addresses"] else "192.168.1.100"
                },
                {
                    "session_id": "session_002",
                    "started_at": "2024-03-14T14:00:00Z", 
                    "ended_at": "2024-03-14T15:00:00Z",
                    "duration_minutes": 60,
                    "pages_visited": ["/dashboard", "/files"],
                    "actions_performed": ["file_download", "file_view"],
                    "device_info": "anonymized",
                    "ip_address": "192.168.1.xxx" if config["anonymize_ip_addresses"] else "192.168.1.101"
                }
            ]
            
            usage_data["items"] = mock_usage
            
        except Exception as e:
            logger.error(f"Failed to collect usage data: {e}")
            usage_data["error"] = str(e)
        
        return usage_data
    
    def _collect_system_logs(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect system and security logs"""
        
        logs_data = {
            "category": "system_logs",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        if not config["include_system_logs"]:
            logs_data["note"] = "System logs excluded by configuration"
            return logs_data
        
        try:
            # Mock system logs
            mock_logs = [
                {
                    "timestamp": "2024-03-15T09:00:00Z",
                    "level": "INFO",
                    "event_type": "login_success",
                    "message": "User login successful",
                    "ip_address": "192.168.1.xxx" if config["anonymize_ip_addresses"] else "192.168.1.100",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "session_id": "session_001"
                },
                {
                    "timestamp": "2024-03-15T09:05:00Z",
                    "level": "INFO", 
                    "event_type": "file_upload",
                    "message": "File uploaded successfully",
                    "file_id": "file_001",
                    "file_size": 1024000
                },
                {
                    "timestamp": "2024-03-14T08:30:00Z",
                    "level": "WARN",
                    "event_type": "login_failed",
                    "message": "Login attempt failed - invalid password",
                    "ip_address": "192.168.1.xxx" if config["anonymize_ip_addresses"] else "192.168.1.102",
                    "attempts": 1
                }
            ]
            
            logs_data["items"] = mock_logs
            
        except Exception as e:
            logger.error(f"Failed to collect system logs: {e}")
            logs_data["error"] = str(e)
        
        return logs_data
    
    def _collect_communication_data(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect communication and support data"""
        
        comm_data = {
            "category": "communication_data",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        try:
            # Mock communication data
            mock_communications = [
                {
                    "type": "support_ticket",
                    "ticket_id": "TICKET_001",
                    "created_at": "2024-02-15T10:00:00Z",
                    "status": "resolved",
                    "subject": "Unable to upload large files",
                    "messages": [
                        {
                            "timestamp": "2024-02-15T10:00:00Z",
                            "from": "user",
                            "message": "I'm having trouble uploading files larger than 100MB"
                        },
                        {
                            "timestamp": "2024-02-15T11:30:00Z",
                            "from": "support",
                            "message": "We've increased your upload limit. Please try again."
                        }
                    ]
                },
                {
                    "type": "email_notification",
                    "sent_at": "2024-03-01T12:00:00Z",
                    "subject": "Your monthly storage report",
                    "delivered": True
                }
            ]
            
            comm_data["items"] = mock_communications
            
        except Exception as e:
            logger.error(f"Failed to collect communication data: {e}")
            comm_data["error"] = str(e)
        
        return comm_data
    
    def _collect_technical_data(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect technical and device data"""
        
        tech_data = {
            "category": "technical_data",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        try:
            # Mock technical data
            mock_tech_data = [
                {
                    "device_fingerprint": "device_001",
                    "browser": "Chrome 122.0",
                    "os": "Windows 10",
                    "screen_resolution": "1920x1080",
                    "timezone": "America/New_York",
                    "language": "en-US",
                    "cookies": [
                        {
                            "name": "session_token",
                            "value": "[encrypted]",
                            "expires": "2024-03-16T00:00:00Z",
                            "purpose": "Authentication"
                        },
                        {
                            "name": "preferences",
                            "value": "[encrypted]", 
                            "expires": "2025-03-15T00:00:00Z",
                            "purpose": "User preferences"
                        }
                    ]
                }
            ]
            
            tech_data["items"] = mock_tech_data
            
        except Exception as e:
            logger.error(f"Failed to collect technical data: {e}")
            tech_data["error"] = str(e)
        
        return tech_data
    
    def _collect_sharing_data(self, user_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Collect shared content and collaboration data"""
        
        sharing_data = {
            "category": "sharing_data",
            "collected_at": datetime.utcnow().isoformat(),
            "items": []
        }
        
        try:
            # Mock sharing data
            mock_sharing = [
                {
                    "shared_file_id": "file_002",
                    "shared_with": [
                        {
                            "user_id": "user_456",
                            "email": "friend@example.com",
                            "permission": "view",
                            "shared_at": "2024-02-01T15:00:00Z"
                        }
                    ],
                    "share_links": [
                        {
                            "link_id": "link_001",
                            "url": "https://app.example.com/share/abc123",
                            "created_at": "2024-02-01T15:00:00Z",
                            "expires_at": "2024-03-01T15:00:00Z",
                            "permission": "view",
                            "password_protected": True
                        }
                    ]
                }
            ]
            
            sharing_data["items"] = mock_sharing
            
        except Exception as e:
            logger.error(f"Failed to collect sharing data: {e}")
            sharing_data["error"] = str(e)
        
        return sharing_data
    
    def _generate_data_exports(self, user_data: Dict[str, Any], 
                             gdpr_dir: str, config: Dict[str, Any],
                             progress_callback: Callable) -> Dict[str, Any]:
        """Generate data export files in various formats"""
        
        export_results = {}
        total_categories = len(user_data)
        
        # Create data directory
        data_dir = os.path.join(gdpr_dir, "data")
        os.makedirs(data_dir, exist_ok=True)
        
        for i, (category, data) in enumerate(user_data.items()):
            progress = 40 + (i / total_categories * 30)
            progress_callback(progress, 100, f"Exporting {category}")
            
            category_results = {}
            
            try:
                # JSON export
                if config["export_format"] in ["json", "multiple"]:
                    json_path = os.path.join(data_dir, f"{category}.json")
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2, default=str)
                    category_results["json"] = json_path
                
                # CSV export (for structured data)
                if config["export_format"] in ["csv", "multiple"] and data.get("items"):
                    csv_path = os.path.join(data_dir, f"{category}.csv")
                    self._export_to_csv(data["items"], csv_path)
                    category_results["csv"] = csv_path
                
                # Calculate data stats
                item_count = len(data.get("items", []))
                data_size = len(json.dumps(data, default=str))
                
                category_results["stats"] = {
                    "item_count": item_count,
                    "data_size_bytes": data_size
                }
                
                export_results[category] = category_results
                
            except Exception as e:
                logger.error(f"Failed to export {category}: {e}")
                export_results[category] = {"error": str(e)}
        
        return export_results
    
    def _export_to_csv(self, items: List[Dict[str, Any]], csv_path: str):
        """Export data items to CSV format"""
        
        if not items:
            return
        
        try:
            # Flatten nested dictionaries for CSV
            flattened_items = []
            
            for item in items:
                flat_item = self._flatten_dict(item)
                flattened_items.append(flat_item)
            
            # Create DataFrame and export
            df = pd.DataFrame(flattened_items)
            df.to_csv(csv_path, index=False, encoding='utf-8')
            
        except Exception as e:
            logger.error(f"Failed to create CSV export: {e}")
    
    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '_') -> Dict[str, Any]:
        """Flatten nested dictionary for CSV export"""
        
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            elif isinstance(v, list):
                # Convert lists to comma-separated strings
                items.append((new_key, ', '.join(str(x) for x in v)))
            else:
                items.append((new_key, v))
        
        return dict(items)
    
    def _generate_gdpr_documentation(self, user_data: Dict[str, Any],
                                   gdpr_dir: str, config: Dict[str, Any],
                                   progress_callback: Callable):
        """Generate GDPR documentation and legal information"""
        
        # Create documentation directory
        docs_dir = os.path.join(gdpr_dir, "documentation")
        os.makedirs(docs_dir, exist_ok=True)
        
        # Generate main GDPR report (PDF)
        progress_callback(75, 100, "Generating GDPR report")
        self._generate_gdpr_report(user_data, docs_dir, config)
        
        # Generate data processing record
        progress_callback(80, 100, "Creating processing record")
        self._generate_processing_record(user_data, docs_dir, config)
        
        # Generate manifest
        if config["create_manifest"]:
            progress_callback(82, 100, "Creating export manifest")
            self._generate_export_manifest(user_data, gdpr_dir, config)
    
    def _generate_gdpr_report(self, user_data: Dict[str, Any], 
                            docs_dir: str, config: Dict[str, Any]):
        """Generate comprehensive GDPR report in PDF format"""
        
        try:
            report_path = os.path.join(docs_dir, "gdpr_report.pdf")
            
            doc = SimpleDocTemplate(
                report_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=18
            )
            
            story = []
            
            # Title page
            story.append(Paragraph("GDPR Data Export Report", self.styles['GDPRTitle']))
            story.append(Spacer(1, 30))
            
            # Export information
            export_info = [
                f"Export Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                f"Total Categories: {len(user_data)}",
                f"Export Format: {config['export_format']}",
                f"Includes Deleted Data: {'Yes' if config['include_deleted'] else 'No'}",
                f"Includes System Logs: {'Yes' if config['include_system_logs'] else 'No'}"
            ]
            
            for info in export_info:
                story.append(Paragraph(info, self.styles['Normal']))
            
            story.append(PageBreak())
            
            # Data categories
            story.append(Paragraph("Data Categories and Legal Basis", self.styles['CategoryHeader']))
            story.append(Spacer(1, 20))
            
            for category, data in user_data.items():
                if category in self.gdpr_categories:
                    cat_info = self.gdpr_categories[category]
                    
                    story.append(Paragraph(cat_info["name"], self.styles['SubSection']))
                    
                    # Category details
                    details = [
                        f"<b>Description:</b> {cat_info['description']}",
                        f"<b>Legal Basis:</b> {cat_info['legal_basis']}",
                        f"<b>Retention Period:</b> {cat_info['retention_period']}",
                        f"<b>Can be Anonymized:</b> {'Yes' if cat_info['anonymizable'] else 'No'}",
                        f"<b>Items in Export:</b> {len(data.get('items', []))}"
                    ]
                    
                    for detail in details:
                        story.append(Paragraph(detail, self.styles['Normal']))
                    
                    story.append(Spacer(1, 15))
            
            # Rights information
            story.append(PageBreak())
            story.append(Paragraph("Your Rights Under GDPR", self.styles['CategoryHeader']))
            story.append(Spacer(1, 20))
            
            rights_text = [
                "<b>Right to Access:</b> This export fulfills your right to access your personal data.",
                "<b>Right to Rectification:</b> You can request corrections to inaccurate data through our support system.",
                "<b>Right to Erasure:</b> You can request deletion of your personal data, subject to legal obligations.",
                "<b>Right to Portability:</b> This export provides your data in machine-readable formats.",
                "<b>Right to Object:</b> You can object to processing based on legitimate interests.",
                "<b>Right to Restrict Processing:</b> You can request restriction of processing in certain circumstances."
            ]
            
            for right in rights_text:
                story.append(Paragraph(right, self.styles['Normal']))
                story.append(Spacer(1, 10))
            
            # Build PDF
            doc.build(story)
            
        except Exception as e:
            logger.error(f"Failed to generate GDPR report: {e}")
    
    def _generate_processing_record(self, user_data: Dict[str, Any],
                                  docs_dir: str, config: Dict[str, Any]):
        """Generate data processing record"""
        
        try:
            record_path = os.path.join(docs_dir, "processing_record.json")
            
            processing_record = {
                "record_created": datetime.utcnow().isoformat(),
                "controller": {
                    "name": "ActiveLog",
                    "contact": "privacy@activelog.com",
                    "dpo_contact": "dpo@activelog.com"
                },
                "processing_activities": []
            }
            
            for category, data in user_data.items():
                if category in self.gdpr_categories:
                    cat_info = self.gdpr_categories[category]
                    
                    activity = {
                        "category": category,
                        "name": cat_info["name"],
                        "description": cat_info["description"],
                        "legal_basis": cat_info["legal_basis"],
                        "data_subjects": ["registered_users"],
                        "recipients": ["internal_systems"],
                        "retention_period": cat_info["retention_period"],
                        "data_items": len(data.get("items", [])),
                        "anonymizable": cat_info["anonymizable"],
                        "security_measures": [
                            "encryption_at_rest",
                            "encryption_in_transit", 
                            "access_controls",
                            "audit_logging"
                        ]
                    }
                    
                    processing_record["processing_activities"].append(activity)
            
            with open(record_path, 'w', encoding='utf-8') as f:
                json.dump(processing_record, f, indent=2, default=str)
                
        except Exception as e:
            logger.error(f"Failed to generate processing record: {e}")
    
    def _generate_export_manifest(self, user_data: Dict[str, Any],
                                gdpr_dir: str, config: Dict[str, Any]):
        """Generate export manifest with file hashes"""
        
        try:
            manifest_path = os.path.join(gdpr_dir, "MANIFEST.json")
            
            manifest = {
                "export_created": datetime.utcnow().isoformat(),
                "export_type": "gdpr_data_export",
                "export_version": "1.0",
                "total_categories": len(user_data),
                "configuration": {
                    "include_deleted": config["include_deleted"],
                    "include_system_logs": config["include_system_logs"],
                    "anonymize_ips": config["anonymize_ip_addresses"],
                    "export_format": config["export_format"]
                },
                "files": []
            }
            
            # Add file hashes if requested
            if config["hash_verification"]:
                for root, dirs, files in os.walk(gdpr_dir):
                    for file in files:
                        if file == "MANIFEST.json":
                            continue
                            
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, gdpr_dir)
                        
                        # Calculate file hash
                        file_hash = self._calculate_file_hash(file_path)
                        file_size = os.path.getsize(file_path)
                        
                        manifest["files"].append({
                            "path": relative_path,
                            "size": file_size,
                            "sha256": file_hash
                        })
            
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to generate manifest: {e}")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of file"""
        
        try:
            hash_sha256 = hashlib.sha256()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate hash for {file_path}: {e}")
            return ""
    
    def _create_gdpr_archive(self, gdpr_dir: str, archive_path: str):
        """Create final GDPR export archive"""
        
        import zipfile
        
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, 
                               compresslevel=9) as zipf:
                for root, dirs, files in os.walk(gdpr_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_path = os.path.relpath(file_path, gdpr_dir)
                        zipf.write(file_path, arc_path)
                        
        except Exception as e:
            logger.error(f"Failed to create GDPR archive: {e}")
            raise