#!/usr/bin/env python3
"""
GDPR Compliance Manager for Legal Framework
Handles GDPR compliance assessment, data requests, consent management, and audit trails
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
import hashlib
import uuid

class DataProcessingPurpose(Enum):
    LEGITIMATE_INTEREST = "legitimate_interest"
    CONTRACT_PERFORMANCE = "contract_performance"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    CONSENT = "consent"

class DataCategory(Enum):
    PERSONAL_IDENTIFIERS = "personal_identifiers"
    CONTACT_INFORMATION = "contact_information"
    FINANCIAL_DATA = "financial_data"
    TECHNICAL_DATA = "technical_data"
    BEHAVIORAL_DATA = "behavioral_data"
    BIOMETRIC_DATA = "biometric_data"
    HEALTH_DATA = "health_data"
    SPECIAL_CATEGORIES = "special_categories"

class ConsentStatus(Enum):
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    PENDING = "pending"
    EXPIRED = "expired"

class DataRequestType(Enum):
    ACCESS = "access"
    RECTIFICATION = "rectification"
    ERASURE = "erasure"
    RESTRICTION = "restriction"
    PORTABILITY = "portability"
    OBJECTION = "objection"

class RequestStatus(Enum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    PARTIALLY_COMPLETED = "partially_completed"

@dataclass
class ConsentRecord:
    consent_id: str
    subject_id: str
    purpose: DataProcessingPurpose
    data_categories: List[DataCategory]
    consent_date: datetime
    status: ConsentStatus
    consent_text: str
    withdrawal_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    metadata: Dict[str, Any] = None

@dataclass
class DataRequest:
    request_id: str
    subject_id: str
    request_type: DataRequestType
    submitted_date: datetime
    status: RequestStatus
    description: str
    response_due_date: datetime
    completed_date: Optional[datetime] = None
    response_data: Optional[str] = None
    rejection_reason: Optional[str] = None

@dataclass
class ComplianceAssessment:
    assessment_id: str
    conducted_date: datetime
    data_processing_activities: List[Dict[str, Any]]
    legal_bases: List[DataProcessingPurpose]
    data_categories: List[DataCategory]
    compliance_score: float
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    next_review_date: datetime

class GDPRComplianceManager:
    """Comprehensive GDPR compliance management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/gdpr.db'
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize GDPR compliance database"""
        with sqlite3.connect(self.db_path) as conn:
            # Consent management table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS consent_records (
                    consent_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    data_categories TEXT NOT NULL,
                    consent_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    consent_text TEXT NOT NULL,
                    withdrawal_date TEXT,
                    expiry_date TEXT,
                    metadata TEXT,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Data requests table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS data_requests (
                    request_id TEXT PRIMARY KEY,
                    subject_id TEXT NOT NULL,
                    request_type TEXT NOT NULL,
                    submitted_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    description TEXT NOT NULL,
                    response_due_date TEXT NOT NULL,
                    completed_date TEXT,
                    response_data TEXT,
                    rejection_reason TEXT,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Compliance assessments table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS compliance_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    conducted_date TEXT NOT NULL,
                    data_processing_activities TEXT NOT NULL,
                    legal_bases TEXT NOT NULL,
                    data_categories TEXT NOT NULL,
                    compliance_score REAL NOT NULL,
                    findings TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    next_review_date TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
            
            # Audit trail table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS audit_trail (
                    audit_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    performed_by TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT
                )
            ''')
            
            # Data processing activities table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS data_processing_activities (
                    activity_id TEXT PRIMARY KEY,
                    activity_name TEXT NOT NULL,
                    purpose TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    data_categories TEXT NOT NULL,
                    data_subjects TEXT NOT NULL,
                    recipients TEXT NOT NULL,
                    retention_period TEXT NOT NULL,
                    security_measures TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
    
    def assess_compliance(self, assessment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct comprehensive GDPR compliance assessment"""
        try:
            assessment_id = str(uuid.uuid4())
            
            # Analyze data processing activities
            activities = assessment_data.get('data_processing_activities', [])
            legal_bases = self._analyze_legal_bases(activities)
            data_categories = self._analyze_data_categories(activities)
            
            # Calculate compliance score
            compliance_score = self._calculate_compliance_score(activities, assessment_data)
            
            # Generate findings and recommendations
            findings = self._generate_findings(activities, compliance_score)
            recommendations = self._generate_recommendations(findings)
            
            # Create assessment record
            assessment = ComplianceAssessment(
                assessment_id=assessment_id,
                conducted_date=datetime.now(),
                data_processing_activities=activities,
                legal_bases=legal_bases,
                data_categories=data_categories,
                compliance_score=compliance_score,
                findings=findings,
                recommendations=recommendations,
                next_review_date=datetime.now() + timedelta(days=365)
            )
            
            # Store assessment
            self._store_assessment(assessment)
            
            # Log audit trail
            self._log_audit('compliance_assessment', assessment_id, 'created', 'system')
            
            return {
                'success': True,
                'assessment_id': assessment_id,
                'compliance_score': compliance_score,
                'findings': findings,
                'recommendations': recommendations,
                'next_review_date': assessment.next_review_date.isoformat(),
                'summary': self._generate_assessment_summary(assessment)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to conduct compliance assessment'
            }
    
    def handle_data_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GDPR data subject request"""
        try:
            request_id = str(uuid.uuid4())
            request_type = DataRequestType(request_data['request_type'])
            
            # Calculate response due date (30 days for most requests)
            response_due_date = datetime.now() + timedelta(days=30)
            
            # Create data request
            data_request = DataRequest(
                request_id=request_id,
                subject_id=request_data['subject_id'],
                request_type=request_type,
                submitted_date=datetime.now(),
                status=RequestStatus.RECEIVED,
                description=request_data.get('description', ''),
                response_due_date=response_due_date
            )
            
            # Store request
            self._store_data_request(data_request)
            
            # Process request based on type
            if request_type == DataRequestType.ACCESS:
                result = self._process_access_request(data_request)
            elif request_type == DataRequestType.ERASURE:
                result = self._process_erasure_request(data_request)
            elif request_type == DataRequestType.PORTABILITY:
                result = self._process_portability_request(data_request)
            elif request_type == DataRequestType.RECTIFICATION:
                result = self._process_rectification_request(data_request)
            else:
                result = self._process_generic_request(data_request)
            
            # Log audit trail
            self._log_audit('data_request', request_id, 'submitted', request_data.get('submitted_by', 'unknown'))
            
            return {
                'success': True,
                'request_id': request_id,
                'status': data_request.status.value,
                'response_due_date': response_due_date.isoformat(),
                'processing_result': result,
                'next_steps': self._get_request_next_steps(request_type)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to handle data request'
            }
    
    def manage_consent(self, consent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Manage GDPR consent records"""
        try:
            action = consent_data.get('action', 'record')
            
            if action == 'record':
                return self._record_consent(consent_data)
            elif action == 'withdraw':
                return self._withdraw_consent(consent_data)
            elif action == 'renew':
                return self._renew_consent(consent_data)
            elif action == 'query':
                return self._query_consent(consent_data)
            else:
                return {
                    'success': False,
                    'error': 'Invalid action',
                    'message': f'Unknown consent action: {action}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to manage consent'
            }
    
    def _record_consent(self, consent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record new consent"""
        consent_id = str(uuid.uuid4())
        
        # Parse data categories
        data_categories = [DataCategory(cat) for cat in consent_data.get('data_categories', [])]
        
        # Set expiry date if provided
        expiry_date = None
        if 'expiry_months' in consent_data:
            expiry_date = datetime.now() + timedelta(days=30 * consent_data['expiry_months'])
        
        consent = ConsentRecord(
            consent_id=consent_id,
            subject_id=consent_data['subject_id'],
            purpose=DataProcessingPurpose(consent_data['purpose']),
            data_categories=data_categories,
            consent_date=datetime.now(),
            status=ConsentStatus.GIVEN,
            consent_text=consent_data['consent_text'],
            expiry_date=expiry_date,
            metadata=consent_data.get('metadata', {})
        )
        
        self._store_consent(consent)
        self._log_audit('consent', consent_id, 'recorded', consent_data.get('recorded_by', 'system'))
        
        return {
            'success': True,
            'consent_id': consent_id,
            'status': consent.status.value,
            'expiry_date': expiry_date.isoformat() if expiry_date else None
        }
    
    def _withdraw_consent(self, consent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Withdraw consent"""
        consent_id = consent_data.get('consent_id')
        subject_id = consent_data.get('subject_id')
        
        if not consent_id and not subject_id:
            return {
                'success': False,
                'error': 'Either consent_id or subject_id required'
            }
        
        # Update consent status
        with sqlite3.connect(self.db_path) as conn:
            if consent_id:
                conn.execute('''
                    UPDATE consent_records 
                    SET status = ?, withdrawal_date = ?, last_updated = ?
                    WHERE consent_id = ?
                ''', (ConsentStatus.WITHDRAWN.value, datetime.now().isoformat(), 
                      datetime.now().isoformat(), consent_id))
            else:
                conn.execute('''
                    UPDATE consent_records 
                    SET status = ?, withdrawal_date = ?, last_updated = ?
                    WHERE subject_id = ? AND status = ?
                ''', (ConsentStatus.WITHDRAWN.value, datetime.now().isoformat(),
                      datetime.now().isoformat(), subject_id, ConsentStatus.GIVEN.value))
            
            affected_rows = conn.total_changes
        
        self._log_audit('consent', consent_id or subject_id, 'withdrawn', 
                       consent_data.get('withdrawn_by', 'subject'))
        
        return {
            'success': True,
            'affected_consents': affected_rows,
            'withdrawal_date': datetime.now().isoformat()
        }
    
    def _process_access_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process data access request"""
        # Collect all data for the subject
        subject_data = self._collect_subject_data(request.subject_id)
        
        # Update request status
        self._update_request_status(request.request_id, RequestStatus.COMPLETED, 
                                   json.dumps(subject_data))
        
        return {
            'data_collected': len(subject_data),
            'data_sources': list(subject_data.keys()) if subject_data else [],
            'delivery_method': 'secure_download'
        }
    
    def _process_erasure_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process right to be forgotten request"""
        # Mark data for deletion (implement actual deletion based on retention policies)
        deletion_plan = self._create_deletion_plan(request.subject_id)
        
        # Update request status
        self._update_request_status(request.request_id, RequestStatus.IN_PROGRESS,
                                   json.dumps(deletion_plan))
        
        return {
            'deletion_plan': deletion_plan,
            'estimated_completion': (datetime.now() + timedelta(days=7)).isoformat()
        }
    
    def _process_portability_request(self, request: DataRequest) -> Dict[str, Any]:
        """Process data portability request"""
        # Export data in machine-readable format
        portable_data = self._export_portable_data(request.subject_id)
        
        self._update_request_status(request.request_id, RequestStatus.COMPLETED,
                                   json.dumps({'export_size': len(str(portable_data))}))
        
        return {
            'export_format': 'JSON',
            'export_size': len(str(portable_data)),
            'download_expires': (datetime.now() + timedelta(days=30)).isoformat()
        }
    
    def _calculate_compliance_score(self, activities: List[Dict[str, Any]], 
                                   assessment_data: Dict[str, Any]) -> float:
        """Calculate GDPR compliance score"""
        total_score = 0
        max_score = 0
        
        # Check each compliance area
        compliance_areas = {
            'legal_basis': 20,
            'data_minimization': 15,
            'consent_management': 15,
            'data_security': 15,
            'breach_procedures': 10,
            'privacy_by_design': 10,
            'data_subject_rights': 15
        }
        
        for area, weight in compliance_areas.items():
            area_score = self._assess_compliance_area(area, activities, assessment_data)
            total_score += area_score * weight
            max_score += 100 * weight
        
        return round((total_score / max_score) * 100, 2) if max_score > 0 else 0.0
    
    def _assess_compliance_area(self, area: str, activities: List[Dict[str, Any]], 
                               assessment_data: Dict[str, Any]) -> float:
        """Assess specific compliance area"""
        if area == 'legal_basis':
            return self._assess_legal_basis(activities)
        elif area == 'consent_management':
            return self._assess_consent_management(assessment_data)
        elif area == 'data_security':
            return self._assess_data_security(assessment_data)
        elif area == 'data_minimization':
            return self._assess_data_minimization(activities)
        else:
            return 70.0  # Default score for other areas
    
    def _assess_legal_basis(self, activities: List[Dict[str, Any]]) -> float:
        """Assess legal basis compliance"""
        if not activities:
            return 0.0
        
        valid_basis_count = sum(1 for activity in activities 
                               if activity.get('legal_basis') in [basis.value for basis in DataProcessingPurpose])
        
        return (valid_basis_count / len(activities)) * 100
    
    def _assess_consent_management(self, assessment_data: Dict[str, Any]) -> float:
        """Assess consent management practices"""
        consent_features = assessment_data.get('consent_features', {})
        
        score = 0
        if consent_features.get('granular_consent'): score += 25
        if consent_features.get('easy_withdrawal'): score += 25
        if consent_features.get('consent_records'): score += 25
        if consent_features.get('consent_renewal'): score += 25
        
        return score
    
    def _store_assessment(self, assessment: ComplianceAssessment):
        """Store compliance assessment"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO compliance_assessments
                (assessment_id, conducted_date, data_processing_activities, 
                 legal_bases, data_categories, compliance_score, findings, 
                 recommendations, next_review_date, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                assessment.assessment_id,
                assessment.conducted_date.isoformat(),
                json.dumps(assessment.data_processing_activities),
                json.dumps([basis.value for basis in assessment.legal_bases]),
                json.dumps([cat.value for cat in assessment.data_categories]),
                assessment.compliance_score,
                json.dumps(assessment.findings),
                json.dumps(assessment.recommendations),
                assessment.next_review_date.isoformat(),
                datetime.now().isoformat()
            ))
    
    def _store_data_request(self, request: DataRequest):
        """Store data request"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO data_requests
                (request_id, subject_id, request_type, submitted_date, status,
                 description, response_due_date, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.request_id,
                request.subject_id,
                request.request_type.value,
                request.submitted_date.isoformat(),
                request.status.value,
                request.description,
                request.response_due_date.isoformat(),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    def _store_consent(self, consent: ConsentRecord):
        """Store consent record"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO consent_records
                (consent_id, subject_id, purpose, data_categories, consent_date,
                 status, consent_text, expiry_date, metadata, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                consent.consent_id,
                consent.subject_id,
                consent.purpose.value,
                json.dumps([cat.value for cat in consent.data_categories]),
                consent.consent_date.isoformat(),
                consent.status.value,
                consent.consent_text,
                consent.expiry_date.isoformat() if consent.expiry_date else None,
                json.dumps(consent.metadata) if consent.metadata else None,
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
    
    def _log_audit(self, entity_type: str, entity_id: str, action: str, 
                   performed_by: str, details: Dict[str, Any] = None):
        """Log audit trail entry"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO audit_trail
                (audit_id, entity_type, entity_id, action, performed_by, 
                 timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                entity_type,
                entity_id,
                action,
                performed_by,
                datetime.now().isoformat(),
                json.dumps(details) if details else None
            ))
    
    def _analyze_legal_bases(self, activities: List[Dict[str, Any]]) -> List[DataProcessingPurpose]:
        """Analyze legal bases from activities"""
        bases = set()
        for activity in activities:
            legal_basis = activity.get('legal_basis')
            if legal_basis:
                try:
                    bases.add(DataProcessingPurpose(legal_basis))
                except ValueError:
                    pass
        return list(bases)
    
    def _analyze_data_categories(self, activities: List[Dict[str, Any]]) -> List[DataCategory]:
        """Analyze data categories from activities"""
        categories = set()
        for activity in activities:
            data_cats = activity.get('data_categories', [])
            for cat in data_cats:
                try:
                    categories.add(DataCategory(cat))
                except ValueError:
                    pass
        return list(categories)
    
    def _generate_findings(self, activities: List[Dict[str, Any]], score: float) -> List[Dict[str, Any]]:
        """Generate compliance findings"""
        findings = []
        
        if score < 50:
            findings.append({
                'severity': 'high',
                'area': 'overall_compliance',
                'finding': 'Overall compliance score is below acceptable threshold',
                'risk_level': 'high'
            })
        
        # Check for missing legal bases
        activities_without_basis = [a for a in activities if not a.get('legal_basis')]
        if activities_without_basis:
            findings.append({
                'severity': 'high',
                'area': 'legal_basis',
                'finding': f'{len(activities_without_basis)} activities lack proper legal basis',
                'risk_level': 'high'
            })
        
        return findings
    
    def _generate_recommendations(self, findings: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on findings"""
        recommendations = []
        
        for finding in findings:
            if finding['area'] == 'legal_basis':
                recommendations.append("Establish clear legal basis for all data processing activities")
            elif finding['area'] == 'overall_compliance':
                recommendations.append("Conduct comprehensive GDPR compliance review and remediation")
        
        if not recommendations:
            recommendations.append("Maintain current compliance practices and conduct regular reviews")
        
        return recommendations
    
    def _generate_assessment_summary(self, assessment: ComplianceAssessment) -> Dict[str, Any]:
        """Generate assessment summary"""
        return {
            'overall_rating': 'compliant' if assessment.compliance_score >= 80 else 
                             'partially_compliant' if assessment.compliance_score >= 60 else 'non_compliant',
            'key_strengths': ['Well-documented processes', 'Clear legal bases'] if assessment.compliance_score >= 70 else [],
            'priority_actions': assessment.recommendations[:3],
            'next_steps': [
                'Schedule regular compliance reviews',
                'Implement recommended improvements',
                'Train staff on GDPR requirements'
            ]
        }