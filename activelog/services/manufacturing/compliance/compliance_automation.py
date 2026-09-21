#!/usr/bin/env python3
"""
ActiveLog Manufacturing Suite - Compliance Documentation Automation

Automated system for generating, managing, and tracking compliance documentation
across multiple regulatory frameworks and quality standards.
"""

import asyncio
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
from pathlib import Path
import aiohttp
import xml.etree.ElementTree as ET
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import jinja2
from docx import Document
from docx.shared import Inches
import warnings
warnings.filterwarnings('ignore')


class ComplianceStandard(Enum):
    ISO_9001 = "iso_9001"
    ISO_14001 = "iso_14001"
    ISO_45001 = "iso_45001"
    FDA_CFR_21 = "fda_cfr_21"
    CE_MARKING = "ce_marking"
    FCC_PART_15 = "fcc_part_15"
    ROHS = "rohs"
    REACH = "reach"
    UL_LISTED = "ul_listed"
    IEC_61508 = "iec_61508"
    ITAR = "itar"
    GDPR = "gdpr"


class DocumentType(Enum):
    CERTIFICATE = "certificate"
    TEST_REPORT = "test_report"
    AUDIT_REPORT = "audit_report"
    DECLARATION = "declaration"
    MANUAL = "manual"
    SOP = "sop"  # Standard Operating Procedure
    RISK_ASSESSMENT = "risk_assessment"
    CALIBRATION_RECORD = "calibration_record"
    TRAINING_RECORD = "training_record"
    CHANGE_CONTROL = "change_control"


class DocumentStatus(Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    ACTIVE = "active"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"


class ReviewType(Enum):
    TECHNICAL = "technical"
    REGULATORY = "regulatory"
    QUALITY = "quality"
    LEGAL = "legal"
    MANAGEMENT = "management"


@dataclass
class ComplianceRequirement:
    requirement_id: str
    standard: ComplianceStandard
    section: str
    title: str
    description: str
    mandatory: bool
    applicable_products: List[str]
    required_documents: List[DocumentType]
    frequency_months: Optional[int]  # How often to update
    responsible_department: str
    implementation_deadline: Optional[datetime]


@dataclass
class ComplianceDocument:
    document_id: str
    title: str
    document_type: DocumentType
    standard: ComplianceStandard
    version: str
    status: DocumentStatus
    created_date: datetime
    approved_date: Optional[datetime]
    expiry_date: Optional[datetime]
    file_path: str
    template_id: Optional[str]
    author: str
    approver: Optional[str]
    product_scope: List[str]
    requirements_covered: List[str]
    metadata: Dict[str, Any]


@dataclass
class ReviewProcess:
    review_id: str
    document_id: str
    review_type: ReviewType
    reviewer: str
    assigned_date: datetime
    due_date: datetime
    completed_date: Optional[datetime]
    status: str  # pending, in_progress, completed, rejected
    comments: str
    recommendations: List[str]


@dataclass
class AuditFinding:
    finding_id: str
    audit_id: str
    standard: ComplianceStandard
    finding_type: str  # non_conformity, observation, opportunity
    severity: str  # critical, major, minor
    description: str
    root_cause: str
    corrective_action: str
    responsible_person: str
    due_date: datetime
    status: str  # open, in_progress, closed, verified


@dataclass
class ComplianceMetrics:
    metrics_date: datetime
    total_requirements: int
    compliant_requirements: int
    compliance_percentage: float
    overdue_documents: int
    pending_reviews: int
    open_findings: int
    average_closure_time_days: float
    certification_status: Dict[ComplianceStandard, str]


class DocumentTemplateEngine:
    """Engine for managing and generating document templates"""
    
    def __init__(self, templates_path: str):
        self.templates_path = Path(templates_path)
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_path)),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialize default document templates"""
        self.templates_path.mkdir(parents=True, exist_ok=True)
        
        # Create default templates
        self._create_iso_9001_templates()
        self._create_test_report_templates()
        self._create_sop_templates()
        self._create_certificate_templates()
    
    def _create_iso_9001_templates(self):
        """Create ISO 9001 document templates"""
        # Quality Manual template
        quality_manual_template = """
# Quality Manual
## Document Control
- Document ID: {{ document_id }}
- Version: {{ version }}
- Effective Date: {{ effective_date }}
- Next Review: {{ next_review_date }}

## 1. Scope
This Quality Manual describes the Quality Management System of {{ company_name }} in accordance with ISO 9001:2015.

### 1.1 Organization and Context
{{ organization_context }}

### 1.2 Interested Parties
{{ interested_parties }}

## 2. Quality Policy
{{ quality_policy }}

## 3. Quality Objectives
{% for objective in quality_objectives %}
- {{ objective }}
{% endfor %}

## 4. Process Documentation
{% for process in processes %}
### 4.{{ loop.index }} {{ process.name }}
- Purpose: {{ process.purpose }}
- Inputs: {{ process.inputs | join(', ') }}
- Outputs: {{ process.outputs | join(', ') }}
- Controls: {{ process.controls | join(', ') }}
- Resources: {{ process.resources | join(', ') }}
{% endfor %}

## 5. Risk Management
{{ risk_management_approach }}

## 6. Performance Monitoring
{{ performance_monitoring }}

## Document Approval
Approved by: {{ approver_name }}
Date: {{ approval_date }}
Signature: _________________
        """
        
        with open(self.templates_path / "iso_9001_quality_manual.md", 'w') as f:
            f.write(quality_manual_template)
    
    def _create_test_report_templates(self):
        """Create test report templates"""
        test_report_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ report_title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { border-bottom: 2px solid #333; padding-bottom: 10px; }
        .section { margin: 20px 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .pass { color: green; font-weight: bold; }
        .fail { color: red; font-weight: bold; }
        .signature { margin-top: 50px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ report_title }}</h1>
        <p><strong>Report ID:</strong> {{ report_id }}</p>
        <p><strong>Date:</strong> {{ test_date }}</p>
        <p><strong>Product:</strong> {{ product_name }}</p>
        <p><strong>Standard:</strong> {{ standard }}</p>
    </div>

    <div class="section">
        <h2>Test Summary</h2>
        <p><strong>Overall Result:</strong> 
            <span class="{% if overall_result == 'PASS' %}pass{% else %}fail{% endif %}">
                {{ overall_result }}
            </span>
        </p>
        <p><strong>Tests Performed:</strong> {{ tests_performed }}</p>
        <p><strong>Tests Passed:</strong> {{ tests_passed }}</p>
        <p><strong>Test Duration:</strong> {{ test_duration }}</p>
    </div>

    <div class="section">
        <h2>Test Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Test Description</th>
                    <th>Requirement</th>
                    <th>Result</th>
                    <th>Value</th>
                    <th>Limit</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for test in test_results %}
                <tr>
                    <td>{{ test.test_id }}</td>
                    <td>{{ test.description }}</td>
                    <td>{{ test.requirement }}</td>
                    <td>{{ test.result }}</td>
                    <td>{{ test.measured_value }}</td>
                    <td>{{ test.limit_value }}</td>
                    <td class="{% if test.status == 'PASS' %}pass{% else %}fail{% endif %}">
                        {{ test.status }}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="section">
        <h2>Test Equipment</h2>
        <table>
            <thead>
                <tr>
                    <th>Equipment</th>
                    <th>Model</th>
                    <th>Serial Number</th>
                    <th>Calibration Date</th>
                    <th>Calibration Due</th>
                </tr>
            </thead>
            <tbody>
                {% for equipment in test_equipment %}
                <tr>
                    <td>{{ equipment.name }}</td>
                    <td>{{ equipment.model }}</td>
                    <td>{{ equipment.serial_number }}</td>
                    <td>{{ equipment.calibration_date }}</td>
                    <td>{{ equipment.calibration_due }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <div class="signature">
        <p><strong>Tested by:</strong> {{ tester_name }}</p>
        <p><strong>Reviewed by:</strong> {{ reviewer_name }}</p>
        <p><strong>Approved by:</strong> {{ approver_name }}</p>
        <br>
        <p>Signature: _________________ Date: {{ approval_date }}</p>
    </div>
</body>
</html>
        """
        
        with open(self.templates_path / "test_report.html", 'w') as f:
            f.write(test_report_template)
    
    def _create_sop_templates(self):
        """Create Standard Operating Procedure templates"""
        sop_template = """
# Standard Operating Procedure
## SOP: {{ sop_number }}
## Title: {{ title }}
## Version: {{ version }}
## Effective Date: {{ effective_date }}

### 1. Purpose
{{ purpose }}

### 2. Scope
{{ scope }}

### 3. Responsibilities
{% for role in responsibilities %}
- **{{ role.title }}:** {{ role.responsibility }}
{% endfor %}

### 4. Materials and Equipment
{% for item in materials_equipment %}
- {{ item.name }}: {{ item.description }}
  - Specification: {{ item.specification }}
  - Supplier: {{ item.supplier }}
{% endfor %}

### 5. Safety Considerations
{% for safety_item in safety_considerations %}
- {{ safety_item }}
{% endfor %}

### 6. Procedure
{% for step in procedure_steps %}
#### Step {{ loop.index }}: {{ step.title }}
{{ step.description }}

**Acceptance Criteria:** {{ step.acceptance_criteria }}
**Duration:** {{ step.estimated_time }}
{% if step.critical_control_point %}
**Critical Control Point:** {{ step.critical_control_point }}
{% endif %}
{% endfor %}

### 7. Quality Controls
{% for control in quality_controls %}
- **{{ control.parameter }}:** {{ control.specification }}
  - Test Method: {{ control.test_method }}
  - Frequency: {{ control.frequency }}
{% endfor %}

### 8. Documentation Requirements
{% for doc in documentation_requirements %}
- {{ doc }}
{% endfor %}

### 9. Training Requirements
{{ training_requirements }}

### 10. Change Control
Any changes to this SOP must be approved by {{ change_control_authority }} and documented according to the Change Control Procedure.

### Document History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
{% for change in document_history %}
| {{ change.version }} | {{ change.date }} | {{ change.author }} | {{ change.changes }} |
{% endfor %}

### Approval
Prepared by: {{ author_name }}
Reviewed by: {{ reviewer_name }}
Approved by: {{ approver_name }}
Date: {{ approval_date }}
        """
        
        with open(self.templates_path / "sop_template.md", 'w') as f:
            f.write(sop_template)
    
    def _create_certificate_templates(self):
        """Create certificate templates"""
        certificate_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Certificate of Compliance</title>
    <style>
        body {
            font-family: 'Times New Roman', serif;
            margin: 50px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        .certificate {
            border: 10px solid #2c3e50;
            border-radius: 20px;
            padding: 50px;
            background: white;
            text-align: center;
            box-shadow: 0 0 30px rgba(0,0,0,0.3);
        }
        .header {
            font-size: 36px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: 3px;
        }
        .subheader {
            font-size: 24px;
            color: #34495e;
            margin-bottom: 40px;
        }
        .content {
            font-size: 18px;
            line-height: 1.8;
            color: #2c3e50;
            margin: 30px 0;
        }
        .product-info {
            background: #ecf0f1;
            padding: 20px;
            margin: 30px 0;
            border-radius: 10px;
        }
        .signature-section {
            display: flex;
            justify-content: space-between;
            margin-top: 80px;
        }
        .signature {
            text-align: center;
            width: 200px;
        }
        .signature-line {
            border-top: 2px solid #2c3e50;
            margin-top: 50px;
            margin-bottom: 10px;
        }
        .seal {
            position: absolute;
            top: 100px;
            right: 100px;
            width: 100px;
            height: 100px;
            border: 3px solid #e74c3c;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(231, 76, 60, 0.1);
            font-weight: bold;
            color: #e74c3c;
            transform: rotate(-15deg);
        }
    </style>
</head>
<body>
    <div class="certificate">
        <div class="seal">CERTIFIED</div>
        
        <div class="header">Certificate of Compliance</div>
        <div class="subheader">{{ standard_name }}</div>
        
        <div class="content">
            This is to certify that the product described below has been examined and tested
            in accordance with the requirements of {{ standard_reference }} and found to comply
            with all applicable specifications.
        </div>
        
        <div class="product-info">
            <strong>Product:</strong> {{ product_name }}<br>
            <strong>Model:</strong> {{ product_model }}<br>
            <strong>Manufacturer:</strong> {{ manufacturer }}<br>
            <strong>Part Number:</strong> {{ part_number }}<br>
            <strong>Serial Number Range:</strong> {{ serial_range }}
        </div>
        
        <div class="content">
            <strong>Test Report Reference:</strong> {{ test_report_number }}<br>
            <strong>Certificate Number:</strong> {{ certificate_number }}<br>
            <strong>Issue Date:</strong> {{ issue_date }}<br>
            <strong>Expiry Date:</strong> {{ expiry_date }}
        </div>
        
        <div class="content">
            This certificate is valid only for products manufactured under the quality system
            described in the referenced test report and remains valid until the expiry date
            shown above, unless superseded or withdrawn.
        </div>
        
        <div class="signature-section">
            <div class="signature">
                <div class="signature-line"></div>
                <div>{{ technical_reviewer }}</div>
                <div>Technical Reviewer</div>
            </div>
            
            <div class="signature">
                <div class="signature-line"></div>
                <div>{{ authorized_signatory }}</div>
                <div>Authorized Signatory</div>
            </div>
        </div>
    </div>
</body>
</html>
        """
        
        with open(self.templates_path / "certificate_template.html", 'w') as f:
            f.write(certificate_template)
    
    async def generate_document(self, template_name: str, data: Dict[str, Any], 
                              output_format: str = "html") -> str:
        """Generate document from template"""
        try:
            template = self.jinja_env.get_template(template_name)
            content = template.render(**data)
            
            # Generate output file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = template_name.replace('.', '_')
            output_file = f"{base_name}_{timestamp}.{output_format}"
            output_path = self.templates_path / "generated" / output_file
            
            # Ensure output directory exists
            output_path.parent.mkdir(exist_ok=True)
            
            if output_format == "pdf" and template_name.endswith('.html'):
                # Convert HTML to PDF (simplified - in production use proper HTML to PDF library)
                pdf_content = self._html_to_pdf(content)
                with open(output_path, 'wb') as f:
                    f.write(pdf_content)
            else:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            return str(output_path)
            
        except Exception as e:
            raise Exception(f"Document generation failed: {str(e)}")
    
    def _html_to_pdf(self, html_content: str) -> bytes:
        """Convert HTML to PDF (simplified implementation)"""
        # In production, use libraries like WeasyPrint or pdfkit
        # This is a placeholder implementation
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Simple text extraction (in production, parse HTML properly)
        import re
        text_content = re.sub(r'<[^>]+>', '', html_content)
        lines = text_content.split('\n')
        
        y_position = 750
        for line in lines:
            if line.strip():
                c.drawString(50, y_position, line.strip()[:80])  # Truncate long lines
                y_position -= 20
                if y_position < 50:
                    c.showPage()
                    y_position = 750
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()


class ComplianceTracker:
    """System for tracking compliance requirements and status"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.requirements_cache = {}
        self._load_standard_requirements()
    
    def _load_standard_requirements(self):
        """Load standard compliance requirements"""
        # ISO 9001:2015 requirements
        iso_9001_requirements = [
            {
                'requirement_id': 'ISO_9001_4.1',
                'standard': ComplianceStandard.ISO_9001,
                'section': '4.1',
                'title': 'Understanding the organization and its context',
                'description': 'Determine external and internal issues relevant to purpose and strategic direction',
                'mandatory': True,
                'required_documents': [DocumentType.MANUAL],
                'frequency_months': 12
            },
            {
                'requirement_id': 'ISO_9001_4.2',
                'standard': ComplianceStandard.ISO_9001,
                'section': '4.2',
                'title': 'Understanding the needs and expectations of interested parties',
                'description': 'Determine interested parties and their requirements',
                'mandatory': True,
                'required_documents': [DocumentType.MANUAL],
                'frequency_months': 12
            },
            {
                'requirement_id': 'ISO_9001_7.1.5',
                'standard': ComplianceStandard.ISO_9001,
                'section': '7.1.5',
                'title': 'Monitoring and measuring resources',
                'description': 'Ensure measurement equipment is calibrated and verified',
                'mandatory': True,
                'required_documents': [DocumentType.CALIBRATION_RECORD, DocumentType.SOP],
                'frequency_months': 12
            },
            {
                'requirement_id': 'ISO_9001_8.5.1',
                'standard': ComplianceStandard.ISO_9001,
                'section': '8.5.1',
                'title': 'Control of production and service provision',
                'description': 'Controlled conditions for production and service provision',
                'mandatory': True,
                'required_documents': [DocumentType.SOP],
                'frequency_months': 6
            }
        ]
        
        # FDA CFR 21 Part 820 requirements
        fda_requirements = [
            {
                'requirement_id': 'FDA_820.20',
                'standard': ComplianceStandard.FDA_CFR_21,
                'section': '820.20',
                'title': 'Management responsibility',
                'description': 'Quality policy and management review requirements',
                'mandatory': True,
                'required_documents': [DocumentType.MANUAL, DocumentType.AUDIT_REPORT],
                'frequency_months': 12
            },
            {
                'requirement_id': 'FDA_820.70',
                'standard': ComplianceStandard.FDA_CFR_21,
                'section': '820.70',
                'title': 'Production and process controls',
                'description': 'Controls for production processes and procedures',
                'mandatory': True,
                'required_documents': [DocumentType.SOP, DocumentType.TEST_REPORT],
                'frequency_months': 6
            }
        ]
        
        # Store in cache
        self.requirements_cache[ComplianceStandard.ISO_9001] = iso_9001_requirements
        self.requirements_cache[ComplianceStandard.FDA_CFR_21] = fda_requirements
    
    async def get_compliance_status(self, standard: ComplianceStandard, 
                                   product_id: Optional[str] = None) -> Dict[str, Any]:
        """Get compliance status for a standard"""
        requirements = self.requirements_cache.get(standard, [])
        
        if product_id:
            # Filter requirements applicable to specific product
            requirements = [
                req for req in requirements 
                if not req.get('applicable_products') or product_id in req.get('applicable_products', [])
            ]
        
        total_requirements = len(requirements)
        compliant_count = 0
        non_compliant = []
        
        for req in requirements:
            compliance_check = await self._check_requirement_compliance(req, product_id)
            if compliance_check['compliant']:
                compliant_count += 1
            else:
                non_compliant.append({
                    'requirement_id': req['requirement_id'],
                    'title': req['title'],
                    'issues': compliance_check['issues']
                })
        
        compliance_percentage = (compliant_count / total_requirements * 100) if total_requirements > 0 else 0
        
        return {
            'standard': standard.value,
            'product_id': product_id,
            'total_requirements': total_requirements,
            'compliant_requirements': compliant_count,
            'compliance_percentage': compliance_percentage,
            'non_compliant_items': non_compliant,
            'assessment_date': datetime.now()
        }
    
    async def _check_requirement_compliance(self, requirement: Dict[str, Any], 
                                          product_id: Optional[str]) -> Dict[str, Any]:
        """Check compliance for a specific requirement"""
        issues = []
        compliant = True
        
        # Check if required documents exist
        required_docs = requirement.get('required_documents', [])
        for doc_type in required_docs:
            if not await self._document_exists(doc_type, requirement['requirement_id'], product_id):
                issues.append(f"Missing required document: {doc_type.value}")
                compliant = False
        
        # Check document currency based on frequency
        frequency_months = requirement.get('frequency_months')
        if frequency_months:
            for doc_type in required_docs:
                if not await self._document_current(doc_type, requirement['requirement_id'], 
                                                  frequency_months, product_id):
                    issues.append(f"Document {doc_type.value} needs update (frequency: {frequency_months} months)")
                    compliant = False
        
        return {
            'compliant': compliant,
            'issues': issues
        }
    
    async def _document_exists(self, doc_type: DocumentType, requirement_id: str, 
                             product_id: Optional[str]) -> bool:
        """Check if required document exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT COUNT(*) FROM compliance_documents 
            WHERE document_type = ? AND ? = ANY(requirements_covered)
            AND status IN ('approved', 'active')
        """
        params = [doc_type.value, requirement_id]
        
        if product_id:
            query += " AND ? = ANY(product_scope)"
            params.append(product_id)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0
    
    async def _document_current(self, doc_type: DocumentType, requirement_id: str,
                              frequency_months: int, product_id: Optional[str]) -> bool:
        """Check if document is current based on frequency requirements"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() - timedelta(days=frequency_months * 30)
        
        query = """
            SELECT COUNT(*) FROM compliance_documents 
            WHERE document_type = ? AND ? = ANY(requirements_covered)
            AND status IN ('approved', 'active')
            AND (approved_date > ? OR created_date > ?)
        """
        params = [doc_type.value, requirement_id, cutoff_date, cutoff_date]
        
        if product_id:
            query += " AND ? = ANY(product_scope)"
            params.append(product_id)
        
        cursor.execute(query, params)
        count = cursor.fetchone()[0]
        conn.close()
        
        return count > 0


class AuditManager:
    """System for managing compliance audits and findings"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def schedule_audit(self, standard: ComplianceStandard, audit_type: str,
                           scheduled_date: datetime, auditor: str) -> str:
        """Schedule a compliance audit"""
        audit_id = f"AUDIT_{standard.value.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audits 
            (audit_id, standard, audit_type, scheduled_date, auditor, status, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_id, standard.value, audit_type, scheduled_date, auditor, 'scheduled', datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        return audit_id
    
    async def record_finding(self, finding: AuditFinding) -> str:
        """Record an audit finding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO audit_findings 
            (finding_id, audit_id, standard, finding_type, severity, description,
             root_cause, corrective_action, responsible_person, due_date, status, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            finding.finding_id, finding.audit_id, finding.standard.value,
            finding.finding_type, finding.severity, finding.description,
            finding.root_cause, finding.corrective_action, finding.responsible_person,
            finding.due_date, finding.status, datetime.now()
        ))
        
        conn.commit()
        conn.close()
        
        return finding.finding_id
    
    async def get_open_findings(self, standard: Optional[ComplianceStandard] = None) -> List[Dict[str, Any]]:
        """Get all open audit findings"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM audit_findings 
            WHERE status IN ('open', 'in_progress')
        """
        params = []
        
        if standard:
            query += " AND standard = ?"
            params.append(standard.value)
        
        query += " ORDER BY severity DESC, due_date ASC"
        
        cursor.execute(query, params)
        findings = cursor.fetchall()
        conn.close()
        
        return [
            {
                'finding_id': row[0],
                'audit_id': row[1],
                'standard': row[2],
                'finding_type': row[3],
                'severity': row[4],
                'description': row[5],
                'root_cause': row[6],
                'corrective_action': row[7],
                'responsible_person': row[8],
                'due_date': row[9],
                'status': row[10]
            }
            for row in findings
        ]
    
    async def close_finding(self, finding_id: str, verification_notes: str, 
                          verifier: str) -> bool:
        """Close an audit finding"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE audit_findings 
            SET status = 'closed', verification_notes = ?, verifier = ?, 
                closure_date = ?
            WHERE finding_id = ?
        """, (verification_notes, verifier, datetime.now(), finding_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success


class ComplianceAutomation:
    """Main system for compliance documentation automation"""
    
    def __init__(self, db_path: str = "compliance.db", templates_path: str = "templates"):
        self.db_path = db_path
        self.templates_path = templates_path
        self.template_engine = DocumentTemplateEngine(templates_path)
        self.compliance_tracker = ComplianceTracker(db_path)
        self.audit_manager = AuditManager(db_path)
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize compliance database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compliance documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_documents (
                document_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                document_type TEXT,
                standard TEXT,
                version TEXT,
                status TEXT,
                created_date TIMESTAMP,
                approved_date TIMESTAMP,
                expiry_date TIMESTAMP,
                file_path TEXT,
                template_id TEXT,
                author TEXT,
                approver TEXT,
                product_scope TEXT,  -- JSON array
                requirements_covered TEXT,  -- JSON array
                metadata TEXT,  -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Review processes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_processes (
                review_id TEXT PRIMARY KEY,
                document_id TEXT,
                review_type TEXT,
                reviewer TEXT,
                assigned_date TIMESTAMP,
                due_date TIMESTAMP,
                completed_date TIMESTAMP,
                status TEXT,
                comments TEXT,
                recommendations TEXT,  -- JSON array
                FOREIGN KEY (document_id) REFERENCES compliance_documents (document_id)
            )
        """)
        
        # Audits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                audit_id TEXT PRIMARY KEY,
                standard TEXT,
                audit_type TEXT,
                scheduled_date TIMESTAMP,
                actual_date TIMESTAMP,
                auditor TEXT,
                status TEXT,
                scope TEXT,
                created_date TIMESTAMP
            )
        """)
        
        # Audit findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_findings (
                finding_id TEXT PRIMARY KEY,
                audit_id TEXT,
                standard TEXT,
                finding_type TEXT,
                severity TEXT,
                description TEXT,
                root_cause TEXT,
                corrective_action TEXT,
                responsible_person TEXT,
                due_date TIMESTAMP,
                status TEXT,
                verification_notes TEXT,
                verifier TEXT,
                closure_date TIMESTAMP,
                created_date TIMESTAMP,
                FOREIGN KEY (audit_id) REFERENCES audits (audit_id)
            )
        """)
        
        # Training records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_records (
                training_id TEXT PRIMARY KEY,
                employee_id TEXT,
                training_topic TEXT,
                standard TEXT,
                completion_date TIMESTAMP,
                expiry_date TIMESTAMP,
                trainer TEXT,
                score REAL,
                certificate_path TEXT
            )
        """)
        
        # Change control table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_control (
                change_id TEXT PRIMARY KEY,
                change_description TEXT,
                affected_documents TEXT,  -- JSON array
                requestor TEXT,
                approval_authority TEXT,
                implementation_date TIMESTAMP,
                status TEXT,
                impact_assessment TEXT,
                created_date TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    async def create_document(self, document: ComplianceDocument) -> str:
        """Create a new compliance document"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO compliance_documents 
            (document_id, title, document_type, standard, version, status,
             created_date, approved_date, expiry_date, file_path, template_id,
             author, approver, product_scope, requirements_covered, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            document.document_id, document.title, document.document_type.value,
            document.standard.value, document.version, document.status.value,
            document.created_date, document.approved_date, document.expiry_date,
            document.file_path, document.template_id, document.author,
            document.approver, json.dumps(document.product_scope),
            json.dumps(document.requirements_covered), json.dumps(document.metadata)
        ))
        
        conn.commit()
        conn.close()
        
        return document.document_id
    
    async def generate_compliance_document(self, template_name: str, 
                                         document_data: Dict[str, Any],
                                         standard: ComplianceStandard,
                                         document_type: DocumentType) -> str:
        """Generate a compliance document from template"""
        # Generate document file
        file_path = await self.template_engine.generate_document(
            template_name, document_data, "html"
        )
        
        # Create document record
        document_id = f"{standard.value.upper()}_{document_type.value.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        document = ComplianceDocument(
            document_id=document_id,
            title=document_data.get('title', f"{standard.value} {document_type.value}"),
            document_type=document_type,
            standard=standard,
            version="1.0",
            status=DocumentStatus.DRAFT,
            created_date=datetime.now(),
            approved_date=None,
            expiry_date=None,
            file_path=file_path,
            template_id=template_name,
            author=document_data.get('author', 'System Generated'),
            approver=None,
            product_scope=document_data.get('product_scope', []),
            requirements_covered=document_data.get('requirements_covered', []),
            metadata=document_data
        )
        
        await self.create_document(document)
        
        return document_id
    
    async def initiate_review(self, document_id: str, review_type: ReviewType,
                            reviewer: str, due_days: int = 7) -> str:
        """Initiate document review process"""
        review_id = f"REV_{document_id}_{review_type.value.upper()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        review_process = ReviewProcess(
            review_id=review_id,
            document_id=document_id,
            review_type=review_type,
            reviewer=reviewer,
            assigned_date=datetime.now(),
            due_date=datetime.now() + timedelta(days=due_days),
            completed_date=None,
            status='pending',
            comments='',
            recommendations=[]
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO review_processes 
            (review_id, document_id, review_type, reviewer, assigned_date,
             due_date, completed_date, status, comments, recommendations)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            review_process.review_id, review_process.document_id,
            review_process.review_type.value, review_process.reviewer,
            review_process.assigned_date, review_process.due_date,
            review_process.completed_date, review_process.status,
            review_process.comments, json.dumps(review_process.recommendations)
        ))
        
        conn.commit()
        conn.close()
        
        return review_id
    
    async def complete_review(self, review_id: str, comments: str,
                            recommendations: List[str], approved: bool) -> bool:
        """Complete document review"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        status = 'approved' if approved else 'rejected'
        
        cursor.execute("""
            UPDATE review_processes 
            SET completed_date = ?, status = ?, comments = ?, recommendations = ?
            WHERE review_id = ?
        """, (
            datetime.now(), status, comments, json.dumps(recommendations), review_id
        ))
        
        # If approved, update document status
        if approved:
            cursor.execute("""
                UPDATE compliance_documents 
                SET status = 'approved', approved_date = ?
                WHERE document_id = (
                    SELECT document_id FROM review_processes WHERE review_id = ?
                )
            """, (datetime.now(), review_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return success
    
    async def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive compliance dashboard"""
        dashboard_data = {
            'dashboard_date': datetime.now(),
            'standards_status': {},
            'document_summary': await self._get_document_summary(),
            'review_summary': await self._get_review_summary(),
            'audit_summary': await self._get_audit_summary(),
            'upcoming_expirations': await self._get_upcoming_expirations(),
            'compliance_metrics': await self._calculate_compliance_metrics()
        }
        
        # Get status for each standard
        for standard in ComplianceStandard:
            try:
                status = await self.compliance_tracker.get_compliance_status(standard)
                dashboard_data['standards_status'][standard.value] = status
            except Exception as e:
                dashboard_data['standards_status'][standard.value] = {
                    'error': str(e)
                }
        
        return dashboard_data
    
    async def _get_document_summary(self) -> Dict[str, Any]:
        """Get document status summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM compliance_documents
            GROUP BY status
        """)
        
        status_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT COUNT(*) FROM compliance_documents")
        total_documents = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_documents': total_documents,
            'status_breakdown': status_counts,
            'active_documents': status_counts.get('active', 0),
            'draft_documents': status_counts.get('draft', 0),
            'expired_documents': status_counts.get('expired', 0)
        }
    
    async def _get_review_summary(self) -> Dict[str, Any]:
        """Get review process summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM review_processes
            WHERE assigned_date >= date('now', '-30 days')
            GROUP BY status
        """)
        
        review_counts = dict(cursor.fetchall())
        
        # Get overdue reviews
        cursor.execute("""
            SELECT COUNT(*) FROM review_processes
            WHERE status = 'pending' AND due_date < date('now')
        """)
        
        overdue_reviews = cursor.fetchone()[0]
        conn.close()
        
        return {
            'pending_reviews': review_counts.get('pending', 0),
            'completed_reviews': review_counts.get('approved', 0) + review_counts.get('rejected', 0),
            'overdue_reviews': overdue_reviews,
            'review_breakdown': review_counts
        }
    
    async def _get_audit_summary(self) -> Dict[str, Any]:
        """Get audit summary"""
        open_findings = await self.audit_manager.get_open_findings()
        
        findings_by_severity = {}
        for finding in open_findings:
            severity = finding['severity']
            findings_by_severity[severity] = findings_by_severity.get(severity, 0) + 1
        
        return {
            'total_open_findings': len(open_findings),
            'critical_findings': findings_by_severity.get('critical', 0),
            'major_findings': findings_by_severity.get('major', 0),
            'minor_findings': findings_by_severity.get('minor', 0),
            'findings_by_severity': findings_by_severity
        }
    
    async def _get_upcoming_expirations(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get documents expiring soon"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        cursor.execute("""
            SELECT document_id, title, expiry_date, standard
            FROM compliance_documents
            WHERE expiry_date IS NOT NULL 
            AND expiry_date <= ?
            AND status = 'active'
            ORDER BY expiry_date
        """, (cutoff_date,))
        
        expirations = cursor.fetchall()
        conn.close()
        
        return [
            {
                'document_id': row[0],
                'title': row[1],
                'expiry_date': row[2],
                'standard': row[3],
                'days_until_expiry': (datetime.fromisoformat(row[2]) - datetime.now()).days
            }
            for row in expirations
        ]
    
    async def _calculate_compliance_metrics(self) -> ComplianceMetrics:
        """Calculate overall compliance metrics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total and compliant requirements (simplified calculation)
        cursor.execute("SELECT COUNT(*) FROM compliance_documents WHERE status = 'active'")
        total_active_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM compliance_documents WHERE status = 'expired'")
        overdue_docs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM review_processes WHERE status = 'pending'")
        pending_reviews = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM audit_findings WHERE status IN ('open', 'in_progress')")
        open_findings = cursor.fetchone()[0]
        
        # Average closure time for findings
        cursor.execute("""
            SELECT AVG(julianday(closure_date) - julianday(created_date)) as avg_days
            FROM audit_findings
            WHERE status = 'closed'
            AND closure_date >= date('now', '-90 days')
        """)
        
        avg_closure_result = cursor.fetchone()
        avg_closure_time = avg_closure_result[0] if avg_closure_result and avg_closure_result[0] else 0
        
        conn.close()
        
        # Calculate compliance percentage (simplified)
        total_requirements = 50  # Placeholder - should be calculated based on applicable standards
        compliant_requirements = max(0, total_requirements - overdue_docs - open_findings)
        compliance_percentage = (compliant_requirements / total_requirements * 100) if total_requirements > 0 else 0
        
        # Certification status (placeholder)
        certification_status = {}
        for standard in ComplianceStandard:
            certification_status[standard] = "valid"  # Simplified
        
        return ComplianceMetrics(
            metrics_date=datetime.now(),
            total_requirements=total_requirements,
            compliant_requirements=compliant_requirements,
            compliance_percentage=compliance_percentage,
            overdue_documents=overdue_docs,
            pending_reviews=pending_reviews,
            open_findings=open_findings,
            average_closure_time_days=avg_closure_time,
            certification_status=certification_status
        )
    
    async def add_sample_data(self):
        """Add sample data for testing"""
        # Sample compliance documents
        sample_docs = [
            {
                'template_name': 'iso_9001_quality_manual.md',
                'data': {
                    'document_id': 'QM-001',
                    'version': '2.1',
                    'effective_date': '2024-01-01',
                    'next_review_date': '2024-12-31',
                    'company_name': 'ActiveLog Manufacturing',
                    'organization_context': 'Leading provider of manufacturing solutions',
                    'interested_parties': 'Customers, suppliers, employees, regulators',
                    'quality_policy': 'Committed to delivering high-quality products',
                    'quality_objectives': [
                        'Achieve 99.5% customer satisfaction',
                        'Reduce defect rate to <0.1%',
                        'Improve on-time delivery to 98%'
                    ],
                    'processes': [
                        {
                            'name': 'Product Development',
                            'purpose': 'Design and develop new products',
                            'inputs': ['Market requirements', 'Customer feedback'],
                            'outputs': ['Product specifications', 'Design documents'],
                            'controls': ['Design reviews', 'Verification tests'],
                            'resources': ['Design engineers', 'CAD software']
                        }
                    ],
                    'risk_management_approach': 'Risk-based thinking integrated into all processes',
                    'performance_monitoring': 'Monthly KPI reviews and customer feedback analysis',
                    'approver_name': 'John Smith',
                    'approval_date': '2024-01-01',
                    'author': 'Quality Manager',
                    'requirements_covered': ['ISO_9001_4.1', 'ISO_9001_4.2']
                },
                'standard': ComplianceStandard.ISO_9001,
                'document_type': DocumentType.MANUAL
            }
        ]
        
        for doc_info in sample_docs:
            try:
                doc_id = await self.generate_compliance_document(
                    doc_info['template_name'],
                    doc_info['data'],
                    doc_info['standard'],
                    doc_info['document_type']
                )
                print(f"Generated document: {doc_id}")
                
                # Initiate review
                review_id = await self.initiate_review(
                    doc_id, ReviewType.TECHNICAL, 'Technical Reviewer', 7
                )
                print(f"Initiated review: {review_id}")
                
            except Exception as e:
                print(f"Error generating sample document: {e}")


async def main():
    """Example usage of Compliance Automation"""
    compliance_system = ComplianceAutomation()
    
    # Add sample data
    await compliance_system.add_sample_data()
    print("Added sample compliance data")
    
    # Get compliance dashboard
    dashboard = await compliance_system.get_compliance_dashboard()
    
    print(f"\n" + "="*50)
    print(f"COMPLIANCE DASHBOARD")
    print(f"="*50)
    
    print(f"\nDocument Summary:")
    doc_summary = dashboard['document_summary']
    print(f"Total Documents: {doc_summary['total_documents']}")
    print(f"Active Documents: {doc_summary['active_documents']}")
    print(f"Draft Documents: {doc_summary['draft_documents']}")
    print(f"Expired Documents: {doc_summary['expired_documents']}")
    
    print(f"\nReview Summary:")
    review_summary = dashboard['review_summary']
    print(f"Pending Reviews: {review_summary['pending_reviews']}")
    print(f"Overdue Reviews: {review_summary['overdue_reviews']}")
    print(f"Completed Reviews: {review_summary['completed_reviews']}")
    
    print(f"\nAudit Summary:")
    audit_summary = dashboard['audit_summary']
    print(f"Total Open Findings: {audit_summary['total_open_findings']}")
    print(f"Critical Findings: {audit_summary['critical_findings']}")
    print(f"Major Findings: {audit_summary['major_findings']}")
    
    print(f"\nCompliance Metrics:")
    metrics = dashboard['compliance_metrics']
    print(f"Overall Compliance: {metrics['compliance_percentage']:.1f}%")
    print(f"Overdue Documents: {metrics['overdue_documents']}")
    print(f"Open Findings: {metrics['open_findings']}")
    print(f"Average Finding Closure: {metrics['average_closure_time_days']:.1f} days")
    
    print(f"\nStandards Compliance Status:")
    for standard, status in dashboard['standards_status'].items():
        if 'error' not in status:
            print(f"{standard}: {status.get('compliance_percentage', 0):.1f}% compliant")
        else:
            print(f"{standard}: Error - {status['error']}")
    
    print(f"\nUpcoming Document Expirations:")
    for expiration in dashboard['upcoming_expirations'][:5]:
        print(f"- {expiration['title']}: {expiration['days_until_expiry']} days")


if __name__ == "__main__":
    asyncio.run(main())