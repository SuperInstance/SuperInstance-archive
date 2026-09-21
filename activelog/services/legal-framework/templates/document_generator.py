#!/usr/bin/env python3
"""
Document Generator for Legal Framework
Generates terms of service, privacy policies, and other legal documents
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
import re
from jinja2 import Template, Environment, FileSystemLoader

class DocumentType(Enum):
    TERMS_OF_SERVICE = "terms_of_service"
    PRIVACY_POLICY = "privacy_policy"
    COOKIE_POLICY = "cookie_policy"
    EULA = "eula"
    SERVICE_AGREEMENT = "service_agreement"
    DATA_PROCESSING_AGREEMENT = "dpa"
    ACCEPTABLE_USE_POLICY = "aup"
    REFUND_POLICY = "refund_policy"
    SLA = "sla"
    DMCA_POLICY = "dmca"

class JurisdictionType(Enum):
    US_FEDERAL = "us_federal"
    US_CALIFORNIA = "us_california"
    EU_GDPR = "eu_gdpr"
    UK = "uk"
    CANADA = "canada"
    AUSTRALIA = "australia"
    INTERNATIONAL = "international"

@dataclass
class DocumentMetadata:
    document_id: str
    document_type: DocumentType
    title: str
    version: str
    jurisdiction: JurisdictionType
    effective_date: datetime
    last_modified: datetime
    created_by: str
    company_info: Dict[str, Any]
    tags: List[str]
    status: str = "draft"

@dataclass
class GenerationRequest:
    document_type: DocumentType
    jurisdiction: JurisdictionType
    company_info: Dict[str, Any]
    service_info: Dict[str, Any]
    custom_clauses: List[Dict[str, Any]] = None
    template_variables: Dict[str, Any] = None
    format_type: str = "html"
    include_boilerplate: bool = True

class DocumentGenerator:
    """Comprehensive legal document generator"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/documents.db'
        self.templates_path = '/home/activeloguser/activelog/services/legal-framework/templates/legal_templates'
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.templates_path, exist_ok=True)
        
        self._init_database()
        self._setup_jinja_environment()
        self._create_default_templates()
    
    def _init_database(self):
        """Initialize document database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    document_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    version TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    effective_date TEXT NOT NULL,
                    last_modified TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    company_info TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    status TEXT DEFAULT 'draft',
                    tags TEXT
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS templates (
                    template_id TEXT PRIMARY KEY,
                    document_type TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    template_content TEXT NOT NULL,
                    variables TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS clauses (
                    clause_id TEXT PRIMARY KEY,
                    clause_type TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    clause_content TEXT NOT NULL,
                    is_required BOOLEAN DEFAULT 0,
                    applicable_documents TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
    
    def _setup_jinja_environment(self):
        """Setup Jinja2 template environment"""
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            autoescape=True,
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self.jinja_env.filters['format_date'] = self._format_date
        self.jinja_env.filters['format_address'] = self._format_address
        self.jinja_env.filters['capitalize_words'] = self._capitalize_words
    
    def _format_date(self, date_obj: datetime, format_str: str = "%B %d, %Y") -> str:
        """Format date for legal documents"""
        return date_obj.strftime(format_str)
    
    def _format_address(self, address: Dict[str, str]) -> str:
        """Format address for legal documents"""
        parts = [
            address.get('street'),
            address.get('city'),
            address.get('state'),
            address.get('zip'),
            address.get('country')
        ]
        return ', '.join(filter(None, parts))
    
    def _capitalize_words(self, text: str) -> str:
        """Capitalize each word"""
        return ' '.join(word.capitalize() for word in text.split())
    
    def generate_document(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate legal document based on request"""
        try:
            request = GenerationRequest(**request_data)
            
            # Get template
            template = self._get_template(request.document_type, request.jurisdiction)
            if not template:
                raise ValueError(f"No template found for {request.document_type} in {request.jurisdiction}")
            
            # Prepare template variables
            variables = self._prepare_template_variables(request)
            
            # Generate document content
            content = template.render(**variables)
            
            # Create document metadata
            document_id = f"{request.document_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            metadata = DocumentMetadata(
                document_id=document_id,
                document_type=request.document_type,
                title=self._generate_document_title(request.document_type, request.company_info),
                version="1.0",
                jurisdiction=request.jurisdiction,
                effective_date=datetime.now(),
                last_modified=datetime.now(),
                created_by="system",
                company_info=request.company_info,
                tags=self._generate_tags(request)
            )
            
            # Store document
            self._store_document(metadata, content)
            
            return {
                'success': True,
                'document_id': document_id,
                'content': content,
                'metadata': asdict(metadata),
                'download_url': f"/documents/download/{document_id}",
                'preview_url': f"/documents/preview/{document_id}"
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to generate document'
            }
    
    def generate_terms_of_service(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate terms of service document"""
        request_data = {
            'document_type': DocumentType.TERMS_OF_SERVICE,
            'jurisdiction': JurisdictionType(company_data.get('jurisdiction', 'us_federal')),
            'company_info': company_data,
            'service_info': company_data.get('service_info', {}),
            'format_type': company_data.get('format_type', 'html')
        }
        
        return self.generate_document(request_data)
    
    def generate_privacy_policy(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate privacy policy document"""
        request_data = {
            'document_type': DocumentType.PRIVACY_POLICY,
            'jurisdiction': JurisdictionType(company_data.get('jurisdiction', 'us_federal')),
            'company_info': company_data,
            'service_info': company_data.get('service_info', {}),
            'format_type': company_data.get('format_type', 'html')
        }
        
        return self.generate_document(request_data)
    
    def _get_template(self, document_type: DocumentType, jurisdiction: JurisdictionType) -> Optional[Template]:
        """Get template for document type and jurisdiction"""
        template_name = f"{document_type.value}_{jurisdiction.value}.html"
        
        try:
            return self.jinja_env.get_template(template_name)
        except:
            # Fallback to generic template
            try:
                return self.jinja_env.get_template(f"{document_type.value}_generic.html")
            except:
                return None
    
    def _prepare_template_variables(self, request: GenerationRequest) -> Dict[str, Any]:
        """Prepare variables for template rendering"""
        variables = {
            'company': request.company_info,
            'service': request.service_info,
            'effective_date': datetime.now(),
            'last_updated': datetime.now(),
            'year': datetime.now().year,
            'jurisdiction': request.jurisdiction.value,
            'document_type': request.document_type.value
        }
        
        # Add custom template variables
        if request.template_variables:
            variables.update(request.template_variables)
        
        # Add jurisdiction-specific variables
        variables.update(self._get_jurisdiction_variables(request.jurisdiction))
        
        return variables
    
    def _get_jurisdiction_variables(self, jurisdiction: JurisdictionType) -> Dict[str, Any]:
        """Get jurisdiction-specific template variables"""
        jurisdiction_vars = {
            JurisdictionType.US_FEDERAL: {
                'governing_law': 'United States federal law',
                'court_jurisdiction': 'federal courts of the United States',
                'dispute_resolution': 'binding arbitration'
            },
            JurisdictionType.US_CALIFORNIA: {
                'governing_law': 'laws of the State of California',
                'court_jurisdiction': 'state and federal courts of California',
                'dispute_resolution': 'California courts'
            },
            JurisdictionType.EU_GDPR: {
                'governing_law': 'laws of the European Union',
                'court_jurisdiction': 'competent courts of the EU',
                'data_protection': 'GDPR compliant',
                'right_to_be_forgotten': True
            },
            JurisdictionType.UK: {
                'governing_law': 'laws of England and Wales',
                'court_jurisdiction': 'courts of England and Wales',
                'data_protection': 'UK GDPR compliant'
            }
        }
        
        return jurisdiction_vars.get(jurisdiction, {})
    
    def _generate_document_title(self, document_type: DocumentType, company_info: Dict[str, Any]) -> str:
        """Generate document title"""
        company_name = company_info.get('name', 'Company')
        
        titles = {
            DocumentType.TERMS_OF_SERVICE: f"{company_name} Terms of Service",
            DocumentType.PRIVACY_POLICY: f"{company_name} Privacy Policy",
            DocumentType.COOKIE_POLICY: f"{company_name} Cookie Policy",
            DocumentType.EULA: f"{company_name} End User License Agreement",
            DocumentType.SERVICE_AGREEMENT: f"{company_name} Service Agreement",
            DocumentType.DATA_PROCESSING_AGREEMENT: f"{company_name} Data Processing Agreement",
            DocumentType.ACCEPTABLE_USE_POLICY: f"{company_name} Acceptable Use Policy",
            DocumentType.REFUND_POLICY: f"{company_name} Refund Policy",
            DocumentType.SLA: f"{company_name} Service Level Agreement",
            DocumentType.DMCA_POLICY: f"{company_name} DMCA Policy"
        }
        
        return titles.get(document_type, f"{company_name} Legal Document")
    
    def _generate_tags(self, request: GenerationRequest) -> List[str]:
        """Generate tags for document"""
        tags = [
            request.document_type.value,
            request.jurisdiction.value,
            'auto-generated'
        ]
        
        # Add service-specific tags
        if 'type' in request.service_info:
            tags.append(request.service_info['type'])
        
        return tags
    
    def _store_document(self, metadata: DocumentMetadata, content: str):
        """Store generated document"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO documents 
                (document_id, document_type, title, version, jurisdiction, 
                 effective_date, last_modified, created_by, company_info, 
                 content, metadata, status, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                metadata.document_id,
                metadata.document_type.value,
                metadata.title,
                metadata.version,
                metadata.jurisdiction.value,
                metadata.effective_date.isoformat(),
                metadata.last_modified.isoformat(),
                metadata.created_by,
                json.dumps(metadata.company_info),
                content,
                json.dumps(asdict(metadata)),
                metadata.status,
                json.dumps(metadata.tags)
            ))
    
    def list_templates(self) -> Dict[str, Any]:
        """List available document templates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT template_id, document_type, jurisdiction, 
                           created_date, last_updated, is_active
                    FROM templates 
                    WHERE is_active = 1
                    ORDER BY document_type, jurisdiction
                ''')
                
                templates = []
                for row in cursor.fetchall():
                    templates.append({
                        'template_id': row[0],
                        'document_type': row[1],
                        'jurisdiction': row[2],
                        'created_date': row[3],
                        'last_updated': row[4],
                        'is_active': bool(row[5])
                    })
                
                return {
                    'success': True,
                    'templates': templates,
                    'total_count': len(templates)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to list templates'
            }
    
    def get_document(self, document_id: str) -> Dict[str, Any]:
        """Get generated document by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM documents WHERE document_id = ?
                ''', (document_id,))
                
                row = cursor.fetchone()
                if not row:
                    return {
                        'success': False,
                        'error': 'Document not found',
                        'message': f'No document found with ID: {document_id}'
                    }
                
                return {
                    'success': True,
                    'document': {
                        'document_id': row[0],
                        'document_type': row[1],
                        'title': row[2],
                        'version': row[3],
                        'jurisdiction': row[4],
                        'effective_date': row[5],
                        'last_modified': row[6],
                        'created_by': row[7],
                        'company_info': json.loads(row[8]),
                        'content': row[9],
                        'metadata': json.loads(row[10]),
                        'status': row[11],
                        'tags': json.loads(row[12])
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to get document'
            }
    
    def list_documents(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """List generated documents with optional filters"""
        try:
            query = '''
                SELECT document_id, document_type, title, version, 
                       jurisdiction, effective_date, status, tags
                FROM documents
            '''
            params = []
            
            if filters:
                conditions = []
                if 'document_type' in filters:
                    conditions.append('document_type = ?')
                    params.append(filters['document_type'])
                if 'jurisdiction' in filters:
                    conditions.append('jurisdiction = ?')
                    params.append(filters['jurisdiction'])
                if 'status' in filters:
                    conditions.append('status = ?')
                    params.append(filters['status'])
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY last_modified DESC'
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                
                documents = []
                for row in cursor.fetchall():
                    documents.append({
                        'document_id': row[0],
                        'document_type': row[1],
                        'title': row[2],
                        'version': row[3],
                        'jurisdiction': row[4],
                        'effective_date': row[5],
                        'status': row[6],
                        'tags': json.loads(row[7])
                    })
                
                return {
                    'success': True,
                    'documents': documents,
                    'total_count': len(documents)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to list documents'
            }
    
    def _create_default_templates(self):
        """Create default document templates"""
        self._create_terms_of_service_template()
        self._create_privacy_policy_template()
    
    def _create_terms_of_service_template(self):
        """Create default terms of service template"""
        template_content = '''<!DOCTYPE html>
<html>
<head>
    <title>{{ company.name }} Terms of Service</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
        h1 { color: #333; border-bottom: 2px solid #333; }
        h2 { color: #555; margin-top: 30px; }
        .effective-date { font-style: italic; color: #666; }
        .contact-info { background: #f5f5f5; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>{{ company.name }} Terms of Service</h1>
    
    <p class="effective-date">Effective Date: {{ effective_date | format_date }}</p>
    
    <h2>1. Acceptance of Terms</h2>
    <p>By accessing and using {{ company.name }}'s services, you accept and agree to be bound by the terms and provision of this agreement.</p>
    
    <h2>2. Description of Service</h2>
    <p>{{ company.name }} provides {{ service.description | default('digital services') }} through our platform.</p>
    
    <h2>3. User Accounts</h2>
    <p>You are responsible for maintaining the confidentiality of your account and password and for restricting access to your computer.</p>
    
    <h2>4. Acceptable Use</h2>
    <p>You agree not to use the service for any unlawful purpose or to solicit others to perform unlawful acts.</p>
    
    <h2>5. Privacy Policy</h2>
    <p>Your privacy is important to us. Please review our Privacy Policy, which also governs your use of the Service.</p>
    
    <h2>6. Intellectual Property</h2>
    <p>The service and its original content, features and functionality are and will remain the exclusive property of {{ company.name }}.</p>
    
    <h2>7. Termination</h2>
    <p>We may terminate or suspend your account and bar access to the service immediately, without prior notice.</p>
    
    <h2>8. Governing Law</h2>
    <p>These Terms shall be interpreted and governed by {{ governing_law | default('applicable law') }}.</p>
    
    <h2>9. Contact Information</h2>
    <div class="contact-info">
        <p><strong>{{ company.name }}</strong></p>
        {% if company.address %}<p>{{ company.address | format_address }}</p>{% endif %}
        {% if company.email %}<p>Email: {{ company.email }}</p>{% endif %}
        {% if company.phone %}<p>Phone: {{ company.phone }}</p>{% endif %}
    </div>
    
    <p><em>Last updated: {{ last_updated | format_date }}</em></p>
</body>
</html>'''
        
        template_file = os.path.join(self.templates_path, 'terms_of_service_generic.html')
        os.makedirs(os.path.dirname(template_file), exist_ok=True)
        
        with open(template_file, 'w') as f:
            f.write(template_content)
    
    def _create_privacy_policy_template(self):
        """Create default privacy policy template"""
        template_content = '''<!DOCTYPE html>
<html>
<head>
    <title>{{ company.name }} Privacy Policy</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }
        h1 { color: #333; border-bottom: 2px solid #333; }
        h2 { color: #555; margin-top: 30px; }
        .effective-date { font-style: italic; color: #666; }
        .contact-info { background: #f5f5f5; padding: 15px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>{{ company.name }} Privacy Policy</h1>
    
    <p class="effective-date">Effective Date: {{ effective_date | format_date }}</p>
    
    <h2>1. Information We Collect</h2>
    <p>We collect information you provide directly to us, such as when you create an account or contact us for support.</p>
    
    <h2>2. How We Use Your Information</h2>
    <p>We use the information we collect to provide, maintain, and improve our services.</p>
    
    <h2>3. Information Sharing</h2>
    <p>We do not sell, trade, or otherwise transfer your personal information to third parties without your consent.</p>
    
    <h2>4. Data Security</h2>
    <p>We implement appropriate security measures to protect your personal information.</p>
    
    <h2>5. Cookies and Tracking</h2>
    <p>We use cookies and similar tracking technologies to enhance your experience on our service.</p>
    
    <h2>6. Your Rights</h2>
    <p>You have the right to access, update, or delete your personal information.</p>
    
    {% if jurisdiction == 'eu_gdpr' %}
    <h2>7. GDPR Rights</h2>
    <p>Under GDPR, you have additional rights including data portability and the right to be forgotten.</p>
    {% endif %}
    
    <h2>8. Children's Privacy</h2>
    <p>Our service is not directed to children under 13, and we do not knowingly collect personal information from children under 13.</p>
    
    <h2>9. Changes to Privacy Policy</h2>
    <p>We may update this privacy policy from time to time. We will notify you of any changes.</p>
    
    <h2>10. Contact Information</h2>
    <div class="contact-info">
        <p><strong>{{ company.name }}</strong></p>
        {% if company.address %}<p>{{ company.address | format_address }}</p>{% endif %}
        {% if company.email %}<p>Email: {{ company.email }}</p>{% endif %}
        {% if company.phone %}<p>Phone: {{ company.phone }}</p>{% endif %}
    </div>
    
    <p><em>Last updated: {{ last_updated | format_date }}</em></p>
</body>
</html>'''
        
        template_file = os.path.join(self.templates_path, 'privacy_policy_generic.html')
        os.makedirs(os.path.dirname(template_file), exist_ok=True)
        
        with open(template_file, 'w') as f:
            f.write(template_content)