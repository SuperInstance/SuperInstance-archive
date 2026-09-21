#!/usr/bin/env python3
"""
Partnership Manager for Legal Framework
Handles partnership agreements, joint ventures, strategic alliances, and business relationships
"""

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
import json
from pathlib import Path
import uuid

class PartnershipType(Enum):
    STRATEGIC_ALLIANCE = "strategic_alliance"
    JOINT_VENTURE = "joint_venture"
    TECHNOLOGY_PARTNERSHIP = "technology_partnership"
    DISTRIBUTION_PARTNERSHIP = "distribution_partnership"
    MARKETING_PARTNERSHIP = "marketing_partnership"
    RESELLER_AGREEMENT = "reseller_agreement"
    OEM_AGREEMENT = "oem_agreement"
    LICENSING_PARTNERSHIP = "licensing_partnership"
    INTEGRATION_PARTNERSHIP = "integration_partnership"
    CHANNEL_PARTNERSHIP = "channel_partnership"

class PartnershipStatus(Enum):
    DRAFT = "draft"
    NEGOTIATION = "negotiation"
    REVIEW = "review"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"

class TerminationType(Enum):
    MUTUAL_AGREEMENT = "mutual_agreement"
    BREACH = "breach"
    CONVENIENCE = "convenience"
    EXPIRATION = "expiration"
    NON_PERFORMANCE = "non_performance"

@dataclass
class Partner:
    partner_id: str
    company_name: str
    legal_entity_type: str
    jurisdiction: str
    contact_person: str
    contact_email: str
    contact_phone: str
    address: Dict[str, str]
    business_registration: str
    tax_id: str
    financial_info: Dict[str, Any]
    references: List[str]
    compliance_status: str
    created_date: datetime

@dataclass
class PartnershipAgreement:
    agreement_id: str
    partnership_type: PartnershipType
    primary_partner_id: str
    secondary_partner_id: str
    title: str
    description: str
    objectives: List[str]
    scope_of_work: str
    start_date: datetime
    end_date: Optional[datetime]
    status: PartnershipStatus
    terms_conditions: Dict[str, Any]
    financial_terms: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    termination_clauses: Dict[str, Any]
    created_date: datetime
    last_modified: datetime

@dataclass
class PartnershipPerformance:
    performance_id: str
    agreement_id: str
    evaluation_period: str
    metrics: Dict[str, Any]
    goals_met: List[str]
    goals_missed: List[str]
    issues: List[str]
    recommendations: List[str]
    overall_rating: float
    evaluation_date: datetime

class PartnershipManager:
    """Comprehensive partnership management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/partnerships.db'
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize partnership database"""
        with sqlite3.connect(self.db_path) as conn:
            # Partners table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS partners (
                    partner_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    legal_entity_type TEXT NOT NULL,
                    jurisdiction TEXT NOT NULL,
                    contact_person TEXT NOT NULL,
                    contact_email TEXT NOT NULL,
                    contact_phone TEXT,
                    address TEXT NOT NULL,
                    business_registration TEXT NOT NULL,
                    tax_id TEXT,
                    financial_info TEXT,
                    partner_references TEXT,
                    compliance_status TEXT DEFAULT 'pending',
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Partnership agreements table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS partnership_agreements (
                    agreement_id TEXT PRIMARY KEY,
                    partnership_type TEXT NOT NULL,
                    primary_partner_id TEXT NOT NULL,
                    secondary_partner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    objectives TEXT NOT NULL,
                    scope_of_work TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT,
                    status TEXT NOT NULL,
                    terms_conditions TEXT NOT NULL,
                    financial_terms TEXT NOT NULL,
                    performance_metrics TEXT NOT NULL,
                    termination_clauses TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    last_modified TEXT NOT NULL
                )
            ''')
            
            # Partnership performance table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS partnership_performance (
                    performance_id TEXT PRIMARY KEY,
                    agreement_id TEXT NOT NULL,
                    evaluation_period TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    goals_met TEXT NOT NULL,
                    goals_missed TEXT NOT NULL,
                    issues TEXT NOT NULL,
                    recommendations TEXT NOT NULL,
                    overall_rating REAL NOT NULL,
                    evaluation_date TEXT NOT NULL,
                    created_date TEXT NOT NULL
                )
            ''')
            
            # Partnership communications table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS partnership_communications (
                    communication_id TEXT PRIMARY KEY,
                    agreement_id TEXT NOT NULL,
                    communication_type TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sender TEXT NOT NULL,
                    recipient TEXT NOT NULL,
                    sent_date TEXT NOT NULL,
                    response_required BOOLEAN DEFAULT 0,
                    response_due_date TEXT,
                    status TEXT DEFAULT 'sent'
                )
            ''')
            
            # Legal documents table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS partnership_documents (
                    document_id TEXT PRIMARY KEY,
                    agreement_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    document_name TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    version TEXT NOT NULL,
                    created_date TEXT NOT NULL,
                    expires_date TEXT,
                    is_signed BOOLEAN DEFAULT 0,
                    signature_data TEXT
                )
            ''')
    
    def create_partnership(self, partnership_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new partnership agreement"""
        try:
            agreement_id = str(uuid.uuid4())
            
            # Validate partner information
            primary_partner = self._get_or_create_partner(partnership_data['primary_partner'])
            secondary_partner = self._get_or_create_partner(partnership_data['secondary_partner'])
            
            # Create partnership agreement
            agreement = PartnershipAgreement(
                agreement_id=agreement_id,
                partnership_type=PartnershipType(partnership_data['partnership_type']),
                primary_partner_id=primary_partner['partner_id'],
                secondary_partner_id=secondary_partner['partner_id'],
                title=partnership_data['title'],
                description=partnership_data['description'],
                objectives=partnership_data.get('objectives', []),
                scope_of_work=partnership_data['scope_of_work'],
                start_date=datetime.fromisoformat(partnership_data['start_date']),
                end_date=datetime.fromisoformat(partnership_data['end_date']) if partnership_data.get('end_date') else None,
                status=PartnershipStatus.DRAFT,
                terms_conditions=partnership_data.get('terms_conditions', {}),
                financial_terms=partnership_data.get('financial_terms', {}),
                performance_metrics=partnership_data.get('performance_metrics', {}),
                termination_clauses=partnership_data.get('termination_clauses', {}),
                created_date=datetime.now(),
                last_modified=datetime.now()
            )
            
            # Store agreement
            self._store_partnership_agreement(agreement)
            
            # Generate partnership documentation
            documents = self._generate_partnership_documents(agreement)
            
            return {
                'success': True,
                'agreement_id': agreement_id,
                'status': agreement.status.value,
                'partners': {
                    'primary': primary_partner['company_name'],
                    'secondary': secondary_partner['company_name']
                },
                'documents_generated': len(documents),
                'next_steps': self._get_partnership_next_steps(agreement.status)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create partnership'
            }
    
    def _get_or_create_partner(self, partner_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get existing partner or create new one"""
        # Check if partner already exists
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT partner_id, company_name FROM partners 
                WHERE company_name = ? AND business_registration = ?
            ''', (partner_data['company_name'], partner_data.get('business_registration', '')))
            
            existing_partner = cursor.fetchone()
            if existing_partner:
                return {
                    'partner_id': existing_partner[0],
                    'company_name': existing_partner[1],
                    'is_new': False
                }
        
        # Create new partner
        partner_id = str(uuid.uuid4())
        partner = Partner(
            partner_id=partner_id,
            company_name=partner_data['company_name'],
            legal_entity_type=partner_data.get('legal_entity_type', 'corporation'),
            jurisdiction=partner_data.get('jurisdiction', 'us'),
            contact_person=partner_data['contact_person'],
            contact_email=partner_data['contact_email'],
            contact_phone=partner_data.get('contact_phone'),
            address=partner_data.get('address', {}),
            business_registration=partner_data.get('business_registration', ''),
            tax_id=partner_data.get('tax_id'),
            financial_info=partner_data.get('financial_info', {}),
            references=partner_data.get('references', []),
            compliance_status='pending',
            created_date=datetime.now()
        )
        
        self._store_partner(partner)
        
        return {
            'partner_id': partner_id,
            'company_name': partner.company_name,
            'is_new': True
        }
    
    def _store_partner(self, partner: Partner):
        """Store partner information"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO partners
                (partner_id, company_name, legal_entity_type, jurisdiction,
                 contact_person, contact_email, contact_phone, address,
                 business_registration, tax_id, financial_info, partner_references,
                 compliance_status, created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                partner.partner_id,
                partner.company_name,
                partner.legal_entity_type,
                partner.jurisdiction,
                partner.contact_person,
                partner.contact_email,
                partner.contact_phone,
                json.dumps(partner.address),
                partner.business_registration,
                partner.tax_id,
                json.dumps(partner.financial_info),
                json.dumps(partner.references),
                partner.compliance_status,
                partner.created_date.isoformat(),
                datetime.now().isoformat()
            ))
    
    def _store_partnership_agreement(self, agreement: PartnershipAgreement):
        """Store partnership agreement"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO partnership_agreements
                (agreement_id, partnership_type, primary_partner_id, secondary_partner_id,
                 title, description, objectives, scope_of_work, start_date, end_date,
                 status, terms_conditions, financial_terms, performance_metrics,
                 termination_clauses, created_date, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                agreement.agreement_id,
                agreement.partnership_type.value,
                agreement.primary_partner_id,
                agreement.secondary_partner_id,
                agreement.title,
                agreement.description,
                json.dumps(agreement.objectives),
                agreement.scope_of_work,
                agreement.start_date.isoformat(),
                agreement.end_date.isoformat() if agreement.end_date else None,
                agreement.status.value,
                json.dumps(agreement.terms_conditions),
                json.dumps(agreement.financial_terms),
                json.dumps(agreement.performance_metrics),
                json.dumps(agreement.termination_clauses),
                agreement.created_date.isoformat(),
                agreement.last_modified.isoformat()
            ))
    
    def _generate_partnership_documents(self, agreement: PartnershipAgreement) -> List[Dict[str, Any]]:
        """Generate partnership legal documents"""
        documents = []
        
        # Generate master agreement
        master_agreement = self._generate_master_agreement(agreement)
        documents.append(master_agreement)
        
        # Generate specific partnership type documents
        if agreement.partnership_type == PartnershipType.JOINT_VENTURE:
            jv_agreement = self._generate_joint_venture_agreement(agreement)
            documents.append(jv_agreement)
        elif agreement.partnership_type == PartnershipType.RESELLER_AGREEMENT:
            reseller_agreement = self._generate_reseller_agreement(agreement)
            documents.append(reseller_agreement)
        
        # Generate NDAs
        nda = self._generate_mutual_nda(agreement)
        documents.append(nda)
        
        # Store document references
        for doc in documents:
            self._store_document_reference(agreement.agreement_id, doc)
        
        return documents
    
    def _generate_master_agreement(self, agreement: PartnershipAgreement) -> Dict[str, Any]:
        """Generate master partnership agreement"""
        template = f"""
MASTER PARTNERSHIP AGREEMENT

{agreement.title}

This Master Partnership Agreement ("Agreement") is entered into on {agreement.start_date.strftime('%B %d, %Y')}.

PARTIES:
- Primary Partner: {agreement.primary_partner_id}
- Secondary Partner: {agreement.secondary_partner_id}

1. PURPOSE AND OBJECTIVES
{chr(10).join(f"   - {obj}" for obj in agreement.objectives)}

2. SCOPE OF WORK
{agreement.scope_of_work}

3. TERM
This Agreement shall commence on {agreement.start_date.strftime('%B %d, %Y')} and shall continue until {agreement.end_date.strftime('%B %d, %Y') if agreement.end_date else 'terminated in accordance with the terms herein'}.

4. FINANCIAL TERMS
{json.dumps(agreement.financial_terms, indent=2)}

5. PERFORMANCE METRICS
{json.dumps(agreement.performance_metrics, indent=2)}

6. TERMINATION
{json.dumps(agreement.termination_clauses, indent=2)}

7. GOVERNING LAW
This Agreement shall be governed by and construed in accordance with applicable law.
"""
        
        return {
            'document_type': 'master_agreement',
            'document_name': f'Master Partnership Agreement - {agreement.title}',
            'content': template,
            'version': '1.0'
        }
    
    def _generate_joint_venture_agreement(self, agreement: PartnershipAgreement) -> Dict[str, Any]:
        """Generate joint venture specific agreement"""
        template = f"""
JOINT VENTURE AGREEMENT

{agreement.title}

1. JOINT VENTURE FORMATION
The parties agree to form a joint venture for the purpose of {agreement.description}.

2. CAPITAL CONTRIBUTIONS
Each party shall contribute resources as defined in the financial terms.

3. MANAGEMENT STRUCTURE
The joint venture shall be managed according to the governance structure defined herein.

4. PROFIT AND LOSS SHARING
Profits and losses shall be shared according to the agreed percentages.

5. INTELLECTUAL PROPERTY
All intellectual property created during the joint venture shall be handled according to the IP provisions.
"""
        
        return {
            'document_type': 'joint_venture_agreement',
            'document_name': f'Joint Venture Agreement - {agreement.title}',
            'content': template,
            'version': '1.0'
        }
    
    def _generate_reseller_agreement(self, agreement: PartnershipAgreement) -> Dict[str, Any]:
        """Generate reseller agreement"""
        template = f"""
RESELLER AGREEMENT

{agreement.title}

1. APPOINTMENT
The Company hereby appoints the Reseller as a non-exclusive reseller of the Products.

2. RESELLER OBLIGATIONS
The Reseller agrees to:
- Market and sell the Products in the designated territory
- Provide customer support as specified
- Maintain adequate inventory levels

3. PRICING AND PAYMENT TERMS
{json.dumps(agreement.financial_terms.get('pricing', {}), indent=2)}

4. TERRITORY
The Reseller is authorized to sell in the designated territory only.

5. MARKETING SUPPORT
The Company will provide marketing materials and support as specified.
"""
        
        return {
            'document_type': 'reseller_agreement',
            'document_name': f'Reseller Agreement - {agreement.title}',
            'content': template,
            'version': '1.0'
        }
    
    def _generate_mutual_nda(self, agreement: PartnershipAgreement) -> Dict[str, Any]:
        """Generate mutual non-disclosure agreement"""
        template = f"""
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into in connection with the partnership: {agreement.title}.

1. DEFINITION OF CONFIDENTIAL INFORMATION
Confidential Information means any and all non-public information disclosed by either party.

2. OBLIGATIONS
Each party agrees to:
- Hold confidential information in strict confidence
- Not disclose to third parties
- Use only for the purpose of evaluating the partnership

3. EXCEPTIONS
Confidential information does not include information that:
- Is publicly known
- Was known prior to disclosure
- Is independently developed

4. TERM
This Agreement shall remain in effect for 5 years from the date of execution.
"""
        
        return {
            'document_type': 'mutual_nda',
            'document_name': f'Mutual NDA - {agreement.title}',
            'content': template,
            'version': '1.0'
        }
    
    def _store_document_reference(self, agreement_id: str, document: Dict[str, Any]):
        """Store document reference"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO partnership_documents
                (document_id, agreement_id, document_type, document_name,
                 file_path, version, created_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                agreement_id,
                document['document_type'],
                document['document_name'],
                f"/documents/{agreement_id}/{document['document_type']}.txt",
                document['version'],
                datetime.now().isoformat()
            ))
    
    def list_partnerships(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """List partnership agreements with optional filters"""
        try:
            query = '''
                SELECT pa.*, p1.company_name as primary_partner_name, 
                       p2.company_name as secondary_partner_name
                FROM partnership_agreements pa
                JOIN partners p1 ON pa.primary_partner_id = p1.partner_id
                JOIN partners p2 ON pa.secondary_partner_id = p2.partner_id
            '''
            params = []
            
            if filters:
                conditions = []
                if 'partnership_type' in filters:
                    conditions.append('pa.partnership_type = ?')
                    params.append(filters['partnership_type'])
                if 'status' in filters:
                    conditions.append('pa.status = ?')
                    params.append(filters['status'])
                if 'partner_name' in filters:
                    conditions.append('(p1.company_name LIKE ? OR p2.company_name LIKE ?)')
                    params.extend([f"%{filters['partner_name']}%", f"%{filters['partner_name']}%"])
                
                if conditions:
                    query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY pa.created_date DESC'
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                
                partnerships = []
                for row in cursor.fetchall():
                    partnerships.append({
                        'agreement_id': row[0],
                        'partnership_type': row[1],
                        'title': row[4],
                        'status': row[10],
                        'start_date': row[8],
                        'end_date': row[9],
                        'primary_partner': row[-2],
                        'secondary_partner': row[-1],
                        'created_date': row[-4]
                    })
                
                return {
                    'success': True,
                    'partnerships': partnerships,
                    'total_count': len(partnerships)
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to list partnerships'
            }
    
    def _get_partnership_next_steps(self, status: PartnershipStatus) -> List[str]:
        """Get next steps for partnership based on status"""
        next_steps = {
            PartnershipStatus.DRAFT: [
                'Review partnership terms',
                'Conduct due diligence on partners',
                'Generate legal documentation',
                'Schedule negotiation meetings'
            ],
            PartnershipStatus.NEGOTIATION: [
                'Finalize terms and conditions',
                'Review financial arrangements',
                'Address legal concerns',
                'Prepare for legal review'
            ],
            PartnershipStatus.REVIEW: [
                'Complete legal review',
                'Obtain necessary approvals',
                'Schedule signing ceremony',
                'Prepare implementation plan'
            ],
            PartnershipStatus.APPROVED: [
                'Execute partnership agreement',
                'Begin implementation',
                'Set up communication channels',
                'Establish performance monitoring'
            ]
        }
        
        return next_steps.get(status, ['Continue partnership operations'])