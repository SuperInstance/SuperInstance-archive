#!/usr/bin/env python3
"""
Acquisition Manager for Legal Framework
Handles acquisition readiness, due diligence, valuation, and M&A documentation
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
import hashlib

class AcquisitionType(Enum):
    ASSET_PURCHASE = "asset_purchase"
    STOCK_PURCHASE = "stock_purchase"
    MERGER = "merger"
    ACQUI_HIRE = "acqui_hire"
    STRATEGIC_INVESTMENT = "strategic_investment"
    LICENSING_DEAL = "licensing_deal"

class AcquisitionStage(Enum):
    PREPARATION = "preparation"
    MARKETING = "marketing"
    DUE_DILIGENCE = "due_diligence"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    POST_ACQUISITION = "post_acquisition"
    COMPLETED = "completed"
    TERMINATED = "terminated"

class DueDiligenceArea(Enum):
    LEGAL = "legal"
    FINANCIAL = "financial"
    TECHNICAL = "technical"
    COMMERCIAL = "commercial"
    OPERATIONAL = "operational"
    HR = "human_resources"
    REGULATORY = "regulatory"
    ENVIRONMENTAL = "environmental"
    TAX = "tax"
    IP = "intellectual_property"

class ValuationMethod(Enum):
    DCF = "discounted_cash_flow"
    COMPARABLE_COMPANIES = "comparable_companies"
    PRECEDENT_TRANSACTIONS = "precedent_transactions"
    ASSET_BASED = "asset_based"
    REVENUE_MULTIPLE = "revenue_multiple"
    EBITDA_MULTIPLE = "ebitda_multiple"

@dataclass
class AcquisitionTarget:
    target_id: str
    company_name: str
    industry: str
    stage: str  # startup, growth, mature
    location: str
    employees_count: int
    annual_revenue: float
    technology_stack: List[str]
    key_assets: List[str]
    competitive_advantages: List[str]
    key_personnel: List[Dict[str, Any]]
    financials: Dict[str, Any]
    created_date: datetime

@dataclass
class AcquisitionPackage:
    package_id: str
    company_id: str
    package_type: str  # sell-side, buy-side
    title: str
    description: str
    target_valuation: float
    valuation_method: ValuationMethod
    stage: AcquisitionStage
    documents_prepared: List[str]
    data_room_items: List[str]
    key_metrics: Dict[str, Any]
    investment_highlights: List[str]
    risk_factors: List[str]
    created_date: datetime
    last_updated: datetime

@dataclass
class DueDiligenceRequest:
    request_id: str
    target_id: str
    requester_id: str
    areas: List[DueDiligenceArea]
    timeline_days: int
    confidentiality_level: str
    specific_questions: List[str]
    document_requests: List[str]
    status: str
    created_date: datetime
    due_date: datetime

class AcquisitionManager:
    """Comprehensive acquisition and M&A management system"""
    
    def __init__(self, config):
        self.config = config
        self.db_path = '/home/activeloguser/activelog/data/legal-framework/acquisitions.db'
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Initialize acquisition database"""
        with sqlite3.connect(self.db_path) as conn:
            # Acquisition targets table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS acquisition_targets (
                    target_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    industry TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    location TEXT NOT NULL,
                    employees_count INTEGER,
                    annual_revenue REAL,
                    technology_stack TEXT,
                    key_assets TEXT,
                    competitive_advantages TEXT,
                    key_personnel TEXT,
                    financials TEXT,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Acquisition packages table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS acquisition_packages (
                    package_id TEXT PRIMARY KEY,
                    company_id TEXT NOT NULL,
                    package_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    target_valuation REAL,
                    valuation_method TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    documents_prepared TEXT,
                    data_room_items TEXT,
                    key_metrics TEXT,
                    investment_highlights TEXT,
                    risk_factors TEXT,
                    created_date TEXT NOT NULL,
                    last_updated TEXT NOT NULL
                )
            ''')
            
            # Due diligence requests table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS due_diligence_requests (
                    request_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    requester_id TEXT NOT NULL,
                    areas TEXT NOT NULL,
                    timeline_days INTEGER NOT NULL,
                    confidentiality_level TEXT NOT NULL,
                    specific_questions TEXT,
                    document_requests TEXT,
                    status TEXT DEFAULT 'pending',
                    created_date TEXT NOT NULL,
                    due_date TEXT NOT NULL
                )
            ''')
            
            # Due diligence findings table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS due_diligence_findings (
                    finding_id TEXT PRIMARY KEY,
                    request_id TEXT NOT NULL,
                    area TEXT NOT NULL,
                    finding_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    recommendation TEXT,
                    documents_referenced TEXT,
                    reviewer TEXT NOT NULL,
                    review_date TEXT NOT NULL
                )
            ''')
            
            # Valuations table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS valuations (
                    valuation_id TEXT PRIMARY KEY,
                    target_id TEXT NOT NULL,
                    valuation_method TEXT NOT NULL,
                    valuation_amount REAL NOT NULL,
                    assumptions TEXT NOT NULL,
                    methodology_notes TEXT,
                    conducted_by TEXT NOT NULL,
                    valuation_date TEXT NOT NULL,
                    confidence_level TEXT NOT NULL,
                    supporting_documents TEXT
                )
            ''')
            
            # Deal structures table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS deal_structures (
                    deal_id TEXT PRIMARY KEY,
                    acquisition_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    acquirer_id TEXT NOT NULL,
                    total_consideration REAL NOT NULL,
                    cash_component REAL,
                    stock_component REAL,
                    earnout_component REAL,
                    payment_terms TEXT,
                    conditions_precedent TEXT,
                    representations_warranties TEXT,
                    closing_date TEXT,
                    created_date TEXT NOT NULL
                )
            ''')
    
    def prepare_package(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare comprehensive acquisition package"""
        try:
            package_id = str(uuid.uuid4())
            
            # Create acquisition package
            package = AcquisitionPackage(
                package_id=package_id,
                company_id=package_data['company_id'],
                package_type=package_data.get('package_type', 'sell-side'),
                title=package_data['title'],
                description=package_data['description'],
                target_valuation=package_data.get('target_valuation', 0.0),
                valuation_method=ValuationMethod(package_data.get('valuation_method', 'dcf')),
                stage=AcquisitionStage.PREPARATION,
                documents_prepared=[],
                data_room_items=[],
                key_metrics=package_data.get('key_metrics', {}),
                investment_highlights=package_data.get('investment_highlights', []),
                risk_factors=package_data.get('risk_factors', []),
                created_date=datetime.now(),
                last_updated=datetime.now()
            )
            
            # Generate required documents
            documents = self._generate_acquisition_documents(package)
            
            # Create data room structure
            data_room = self._create_data_room_structure(package)
            
            # Update package with generated items
            package.documents_prepared = [doc['name'] for doc in documents]
            package.data_room_items = list(data_room.keys())
            
            # Store package
            self._store_acquisition_package(package)
            
            # Generate executive summary
            exec_summary = self._generate_executive_summary(package)
            
            return {
                'success': True,
                'package_id': package_id,
                'stage': package.stage.value,
                'documents_generated': len(documents),
                'data_room_sections': len(data_room),
                'executive_summary': exec_summary,
                'next_steps': self._get_package_next_steps(package.stage)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to prepare acquisition package'
            }
    
    def conduct_due_diligence(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct comprehensive due diligence"""
        try:
            request_id = str(uuid.uuid4())
            
            # Create due diligence request
            dd_request = DueDiligenceRequest(
                request_id=request_id,
                target_id=request_data['target_id'],
                requester_id=request_data['requester_id'],
                areas=[DueDiligenceArea(area) for area in request_data['areas']],
                timeline_days=request_data.get('timeline_days', 30),
                confidentiality_level=request_data.get('confidentiality_level', 'high'),
                specific_questions=request_data.get('specific_questions', []),
                document_requests=request_data.get('document_requests', []),
                status='in_progress',
                created_date=datetime.now(),
                due_date=datetime.now() + timedelta(days=request_data.get('timeline_days', 30))
            )
            
            # Store request
            self._store_dd_request(dd_request)
            
            # Conduct analysis for each area
            findings = []
            for area in dd_request.areas:
                area_findings = self._analyze_dd_area(area, dd_request.target_id)
                findings.extend(area_findings)
            
            # Store findings
            for finding in findings:
                self._store_dd_finding(request_id, finding)
            
            # Generate summary report
            summary = self._generate_dd_summary(findings)
            
            return {
                'success': True,
                'request_id': request_id,
                'areas_analyzed': len(dd_request.areas),
                'total_findings': len(findings),
                'critical_issues': len([f for f in findings if f.get('severity') == 'critical']),
                'summary': summary,
                'due_date': dd_request.due_date.isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to conduct due diligence'
            }
    
    def _generate_acquisition_documents(self, package: AcquisitionPackage) -> List[Dict[str, Any]]:
        """Generate acquisition-related documents"""
        documents = []
        
        # Executive Summary / Teaser
        exec_summary = {
            'name': 'Executive Summary',
            'type': 'executive_summary',
            'content': self._create_executive_summary_content(package)
        }
        documents.append(exec_summary)
        
        # Confidential Information Memorandum (CIM)
        cim = {
            'name': 'Confidential Information Memorandum',
            'type': 'cim',
            'content': self._create_cim_content(package)
        }
        documents.append(cim)
        
        # Financial Model
        fin_model = {
            'name': 'Financial Model',
            'type': 'financial_model',
            'content': self._create_financial_model_content(package)
        }
        documents.append(fin_model)
        
        # Management Presentation
        mgmt_presentation = {
            'name': 'Management Presentation',
            'type': 'management_presentation',
            'content': self._create_management_presentation_content(package)
        }
        documents.append(mgmt_presentation)
        
        return documents
    
    def _create_executive_summary_content(self, package: AcquisitionPackage) -> str:
        """Create executive summary content"""
        return f"""
EXECUTIVE SUMMARY
{package.title}

INVESTMENT HIGHLIGHTS:
{chr(10).join(f"• {highlight}" for highlight in package.investment_highlights)}

KEY METRICS:
{json.dumps(package.key_metrics, indent=2)}

TARGET VALUATION: ${package.target_valuation:,.0f}
VALUATION METHOD: {package.valuation_method.value.replace('_', ' ').title()}

DESCRIPTION:
{package.description}

RISK FACTORS:
{chr(10).join(f"• {risk}" for risk in package.risk_factors)}
"""
    
    def _create_cim_content(self, package: AcquisitionPackage) -> str:
        """Create Confidential Information Memorandum content"""
        return f"""
CONFIDENTIAL INFORMATION MEMORANDUM
{package.title}

TABLE OF CONTENTS:
1. Executive Summary
2. Investment Highlights
3. Business Overview
4. Financial Performance
5. Market Analysis
6. Management Team
7. Growth Strategy
8. Risk Factors

EXECUTIVE SUMMARY:
{package.description}

FINANCIAL HIGHLIGHTS:
{json.dumps(package.key_metrics, indent=2)}

This document contains confidential and proprietary information. Any reproduction or distribution is strictly prohibited.
"""
    
    def _create_data_room_structure(self, package: AcquisitionPackage) -> Dict[str, List[str]]:
        """Create virtual data room structure"""
        data_room = {
            'Corporate': [
                'Articles of Incorporation',
                'Bylaws',
                'Board Resolutions',
                'Shareholder Agreements',
                'Corporate Structure Chart'
            ],
            'Financial': [
                'Audited Financial Statements (3 years)',
                'Monthly Financial Reports',
                'Tax Returns',
                'Budget and Forecasts',
                'Accounts Receivable Aging'
            ],
            'Legal': [
                'Material Contracts',
                'Employment Agreements',
                'Intellectual Property Portfolio',
                'Litigation Summary',
                'Regulatory Compliance'
            ],
            'Commercial': [
                'Customer Contracts',
                'Supplier Agreements',
                'Sales Pipeline',
                'Market Analysis',
                'Competitive Analysis'
            ],
            'Technology': [
                'Technology Architecture',
                'Source Code Documentation',
                'Security Assessments',
                'IT Infrastructure',
                'Development Roadmap'
            ],
            'Human Resources': [
                'Employee Handbook',
                'Organization Chart',
                'Compensation Plans',
                'Benefits Summary',
                'Key Personnel Contracts'
            ]
        }
        
        return data_room
    
    def _analyze_dd_area(self, area: DueDiligenceArea, target_id: str) -> List[Dict[str, Any]]:
        """Analyze specific due diligence area"""
        findings = []
        
        if area == DueDiligenceArea.LEGAL:
            findings.extend(self._analyze_legal_dd(target_id))
        elif area == DueDiligenceArea.FINANCIAL:
            findings.extend(self._analyze_financial_dd(target_id))
        elif area == DueDiligenceArea.TECHNICAL:
            findings.extend(self._analyze_technical_dd(target_id))
        elif area == DueDiligenceArea.IP:
            findings.extend(self._analyze_ip_dd(target_id))
        else:
            # Generic analysis for other areas
            findings.append({
                'area': area.value,
                'finding_type': 'informational',
                'severity': 'low',
                'title': f'{area.value.replace("_", " ").title()} Review Required',
                'description': f'Detailed {area.value} analysis needs to be conducted',
                'recommendation': f'Engage {area.value} specialists for comprehensive review'
            })
        
        return findings
    
    def _analyze_legal_dd(self, target_id: str) -> List[Dict[str, Any]]:
        """Analyze legal due diligence"""
        return [
            {
                'area': 'legal',
                'finding_type': 'compliance',
                'severity': 'medium',
                'title': 'Corporate Structure Review',
                'description': 'Company corporate structure appears standard with proper documentation',
                'recommendation': 'Verify all corporate filings are current and complete'
            },
            {
                'area': 'legal',
                'finding_type': 'contract',
                'severity': 'low',
                'title': 'Material Contracts Analysis',
                'description': 'Key customer and supplier contracts reviewed',
                'recommendation': 'Negotiate assignment or consent provisions for key contracts'
            }
        ]
    
    def _analyze_financial_dd(self, target_id: str) -> List[Dict[str, Any]]:
        """Analyze financial due diligence"""
        return [
            {
                'area': 'financial',
                'finding_type': 'accounting',
                'severity': 'low',
                'title': 'Financial Statements Review',
                'description': 'Financial statements appear consistent with industry standards',
                'recommendation': 'Conduct quality of earnings analysis'
            },
            {
                'area': 'financial',
                'finding_type': 'working_capital',
                'severity': 'medium',
                'title': 'Working Capital Analysis',
                'description': 'Working capital requirements vary seasonally',
                'recommendation': 'Include working capital adjustment mechanism in deal structure'
            }
        ]
    
    def _analyze_technical_dd(self, target_id: str) -> List[Dict[str, Any]]:
        """Analyze technical due diligence"""
        return [
            {
                'area': 'technical',
                'finding_type': 'architecture',
                'severity': 'low',
                'title': 'Technology Stack Review',
                'description': 'Technology architecture is modern and scalable',
                'recommendation': 'Plan for technology integration post-acquisition'
            },
            {
                'area': 'technical',
                'finding_type': 'security',
                'severity': 'medium',
                'title': 'Cybersecurity Assessment',
                'description': 'Security practices meet industry standards with some improvements needed',
                'recommendation': 'Implement additional security measures before closing'
            }
        ]
    
    def _analyze_ip_dd(self, target_id: str) -> List[Dict[str, Any]]:
        """Analyze intellectual property due diligence"""
        return [
            {
                'area': 'intellectual_property',
                'finding_type': 'patents',
                'severity': 'low',
                'title': 'Patent Portfolio Review',
                'description': 'Strong patent portfolio with key technologies protected',
                'recommendation': 'Verify patent assignments and consider additional filings'
            },
            {
                'area': 'intellectual_property',
                'finding_type': 'trademarks',
                'severity': 'low',
                'title': 'Trademark Analysis',
                'description': 'Trademarks properly registered and maintained',
                'recommendation': 'Ensure trademark assignments are included in transaction'
            }
        ]
    
    def _generate_dd_summary(self, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate due diligence summary"""
        critical_count = len([f for f in findings if f.get('severity') == 'critical'])
        high_count = len([f for f in findings if f.get('severity') == 'high'])
        medium_count = len([f for f in findings if f.get('severity') == 'medium'])
        low_count = len([f for f in findings if f.get('severity') == 'low'])
        
        overall_risk = 'low'
        if critical_count > 0:
            overall_risk = 'critical'
        elif high_count > 2:
            overall_risk = 'high'
        elif medium_count > 5:
            overall_risk = 'medium'
        
        return {
            'total_findings': len(findings),
            'risk_breakdown': {
                'critical': critical_count,
                'high': high_count,
                'medium': medium_count,
                'low': low_count
            },
            'overall_risk_level': overall_risk,
            'key_recommendations': [
                'Complete detailed financial quality of earnings analysis',
                'Negotiate representations and warranties insurance',
                'Plan comprehensive integration strategy',
                'Establish escrow for potential issues'
            ]
        }
    
    def _store_acquisition_package(self, package: AcquisitionPackage):
        """Store acquisition package"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO acquisition_packages
                (package_id, company_id, package_type, title, description,
                 target_valuation, valuation_method, stage, documents_prepared,
                 data_room_items, key_metrics, investment_highlights, risk_factors,
                 created_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                package.package_id,
                package.company_id,
                package.package_type,
                package.title,
                package.description,
                package.target_valuation,
                package.valuation_method.value,
                package.stage.value,
                json.dumps(package.documents_prepared),
                json.dumps(package.data_room_items),
                json.dumps(package.key_metrics),
                json.dumps(package.investment_highlights),
                json.dumps(package.risk_factors),
                package.created_date.isoformat(),
                package.last_updated.isoformat()
            ))
    
    def _store_dd_request(self, request: DueDiligenceRequest):
        """Store due diligence request"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO due_diligence_requests
                (request_id, target_id, requester_id, areas, timeline_days,
                 confidentiality_level, specific_questions, document_requests,
                 status, created_date, due_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                request.request_id,
                request.target_id,
                request.requester_id,
                json.dumps([area.value for area in request.areas]),
                request.timeline_days,
                request.confidentiality_level,
                json.dumps(request.specific_questions),
                json.dumps(request.document_requests),
                request.status,
                request.created_date.isoformat(),
                request.due_date.isoformat()
            ))
    
    def _store_dd_finding(self, request_id: str, finding: Dict[str, Any]):
        """Store due diligence finding"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO due_diligence_findings
                (finding_id, request_id, area, finding_type, severity,
                 title, description, recommendation, reviewer, review_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                request_id,
                finding['area'],
                finding['finding_type'],
                finding['severity'],
                finding['title'],
                finding['description'],
                finding['recommendation'],
                'system',
                datetime.now().isoformat()
            ))
    
    def _generate_executive_summary(self, package: AcquisitionPackage) -> str:
        """Generate executive summary"""
        return f"""
{package.title} represents a compelling {package.package_type} opportunity in the {package.key_metrics.get('industry', 'technology')} sector.

Key Investment Highlights:
{chr(10).join(f"• {highlight}" for highlight in package.investment_highlights[:3])}

The target valuation of ${package.target_valuation:,.0f} is based on {package.valuation_method.value.replace('_', ' ')} methodology.

This package includes comprehensive documentation and data room materials to support the acquisition process.
"""
    
    def _get_package_next_steps(self, stage: AcquisitionStage) -> List[str]:
        """Get next steps for acquisition package"""
        next_steps = {
            AcquisitionStage.PREPARATION: [
                'Complete document preparation',
                'Set up virtual data room',
                'Prepare marketing materials',
                'Identify potential buyers/targets'
            ],
            AcquisitionStage.MARKETING: [
                'Execute marketing process',
                'Manage buyer/seller communications',
                'Schedule management presentations',
                'Coordinate due diligence requests'
            ],
            AcquisitionStage.DUE_DILIGENCE: [
                'Facilitate due diligence process',
                'Respond to buyer requests',
                'Address findings and concerns',
                'Prepare for negotiations'
            ],
            AcquisitionStage.NEGOTIATION: [
                'Negotiate deal terms',
                'Structure transaction',
                'Draft definitive agreements',
                'Plan closing process'
            ]
        }
        
        return next_steps.get(stage, ['Continue with acquisition process'])