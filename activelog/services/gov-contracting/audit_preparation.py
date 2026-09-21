#!/usr/bin/env python3
"""
Audit Preparation System
Comprehensive audit planning, preparation, and response management
"""

import asyncio
import logging
import sqlite3
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class AuditType(Enum):
    DCAA = "dcaa"                    # Defense Contract Audit Agency
    INCURRED_COST = "incurred_cost"  # Incurred Cost Audit
    CAS = "cas"                      # Cost Accounting Standards
    ACCOUNTING_SYSTEM = "accounting_system"
    PRICING = "pricing"              # Price Proposal Audit
    COMPLIANCE = "compliance"        # Compliance Audit
    FORWARD_PRICING = "forward_pricing"
    LABOR_FLOOR_CHECK = "labor_floor_check"
    POSTAWARD = "postaward"          # Post-Award Audit

class AuditStatus(Enum):
    SCHEDULED = "scheduled"
    IN_PREPARATION = "in_preparation"
    IN_PROGRESS = "in_progress"
    DRAFT_REPORT = "draft_report"
    FINAL_REPORT = "final_report"
    CLOSED = "closed"
    APPEALED = "appealed"

class FindingType(Enum):
    QUESTIONED_COST = "questioned_cost"
    ACCOUNTING_DEFICIENCY = "accounting_deficiency"
    CAS_NONCOMPLIANCE = "cas_noncompliance"
    INTERNAL_CONTROL = "internal_control"
    INADEQUATE_SUPPORT = "inadequate_support"
    UNALLOWABLE_COST = "unallowable_cost"
    MISCLASSIFICATION = "misclassification"

class FindingSeverity(Enum):
    CRITICAL = "critical"
    SIGNIFICANT = "significant"
    MINOR = "minor"
    OBSERVATION = "observation"

class AuditPreparationSystem:
    def __init__(self):
        self.db_path = "data/audit_preparation.db"
        self.audit_checklists = {}
        self.documentation_requirements = {}

    async def initialize(self):
        """Initialize audit preparation system"""
        try:
            await self._create_database_schema()
            await self._setup_audit_checklists()
            await self._setup_documentation_requirements()
            logger.info("Audit Preparation System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Audit Preparation System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for audit preparation"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Audit schedules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_schedules (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                audit_type TEXT NOT NULL,
                audit_agency TEXT NOT NULL,
                auditor_name TEXT,
                auditor_contact TEXT,
                notification_date TEXT,
                entrance_conference_date TEXT,
                fieldwork_start_date TEXT,
                fieldwork_end_date TEXT,
                exit_conference_date TEXT,
                draft_report_date TEXT,
                final_report_date TEXT,
                audit_period_start TEXT NOT NULL,
                audit_period_end TEXT NOT NULL,
                scope_description TEXT,
                audit_objectives TEXT,
                status TEXT NOT NULL,
                preparation_lead TEXT,
                audit_team_members TEXT,
                client_contact TEXT,
                special_instructions TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Document collection table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_collection (
                id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                document_category TEXT NOT NULL,
                document_name TEXT NOT NULL,
                document_description TEXT,
                document_path TEXT,
                document_type TEXT,
                collection_date TEXT,
                collected_by TEXT,
                version TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                review_required BOOLEAN DEFAULT 0,
                reviewed_by TEXT,
                review_date TEXT,
                review_notes TEXT,
                retention_period TEXT,
                confidentiality_level TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (audit_id) REFERENCES audit_schedules (id)
            )
        """)
        
        # Audit checklist table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_checklists (
                id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                checklist_category TEXT NOT NULL,
                checklist_item TEXT NOT NULL,
                item_description TEXT,
                responsible_party TEXT,
                due_date TEXT,
                completion_date TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                completion_percentage REAL DEFAULT 0.0,
                notes TEXT,
                supporting_documents TEXT,
                dependencies TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audit_id) REFERENCES audit_schedules (id)
            )
        """)
        
        # Audit findings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_findings (
                id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                finding_number TEXT,
                finding_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                questioned_amount REAL DEFAULT 0.0,
                audit_period TEXT,
                contract_reference TEXT,
                regulation_citation TEXT,
                auditor_position TEXT,
                contractor_position TEXT,
                supporting_evidence TEXT,
                potential_impact TEXT,
                management_response TEXT,
                corrective_action_plan TEXT,
                target_completion_date TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (audit_id) REFERENCES audit_schedules (id)
            )
        """)
        
        # Corrective action plans table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS corrective_action_plans (
                id TEXT PRIMARY KEY,
                finding_id TEXT NOT NULL,
                action_description TEXT NOT NULL,
                responsible_party TEXT NOT NULL,
                target_completion_date TEXT NOT NULL,
                actual_completion_date TEXT,
                status TEXT NOT NULL DEFAULT 'planned',
                progress_percentage REAL DEFAULT 0.0,
                cost_impact REAL DEFAULT 0.0,
                resource_requirements TEXT,
                success_criteria TEXT,
                verification_method TEXT,
                progress_updates TEXT,
                barriers_issues TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (finding_id) REFERENCES audit_findings (id)
            )
        """)
        
        # Evidence repository table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence_repository (
                id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                finding_id TEXT,
                evidence_type TEXT NOT NULL,
                evidence_title TEXT NOT NULL,
                evidence_description TEXT,
                evidence_source TEXT,
                collection_date TEXT NOT NULL,
                collected_by TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,
                hash_value TEXT,
                chain_of_custody TEXT,
                relevance_score INTEGER DEFAULT 5,
                authentication_status TEXT,
                analysis_notes TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (audit_id) REFERENCES audit_schedules (id)
            )
        """)
        
        # Audit communications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_communications (
                id TEXT PRIMARY KEY,
                audit_id TEXT NOT NULL,
                communication_date TEXT NOT NULL,
                communication_type TEXT NOT NULL,
                participants TEXT,
                subject TEXT,
                summary TEXT,
                action_items TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_date TEXT,
                attachments TEXT,
                created_by TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (audit_id) REFERENCES audit_schedules (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_audit_checklists(self):
        """Setup audit preparation checklists by type"""
        self.audit_checklists = {
            AuditType.DCAA.value: [
                {
                    "category": "preparation",
                    "items": [
                        "Review audit notification letter",
                        "Assemble internal audit response team",
                        "Schedule entrance conference",
                        "Prepare executive briefing materials",
                        "Review prior audit findings and status"
                    ]
                },
                {
                    "category": "documentation",
                    "items": [
                        "Collect accounting system documentation",
                        "Gather cost accounting policies",
                        "Compile indirect rate calculations",
                        "Prepare contract files",
                        "Organize supporting cost documentation"
                    ]
                },
                {
                    "category": "personnel",
                    "items": [
                        "Brief key personnel on audit process",
                        "Assign document custodians",
                        "Prepare subject matter experts",
                        "Schedule personnel availability",
                        "Review confidentiality requirements"
                    ]
                }
            ],
            AuditType.INCURRED_COST.value: [
                {
                    "category": "cost_data",
                    "items": [
                        "Prepare final indirect cost rate proposals",
                        "Compile supporting cost schedules",
                        "Organize direct cost documentation",
                        "Prepare cost transfer documentation",
                        "Review unallowable cost schedules"
                    ]
                },
                {
                    "category": "accounting_records", 
                    "items": [
                        "Prepare general ledger details",
                        "Compile trial balances",
                        "Organize journal entries",
                        "Prepare bank reconciliations",
                        "Review account analyses"
                    ]
                }
            ],
            AuditType.CAS.value: [
                {
                    "category": "cas_compliance",
                    "items": [
                        "Review CAS disclosure statement",
                        "Prepare cost accounting practice documentation",
                        "Compile cost allocation methodologies",
                        "Review consistency of practices",
                        "Prepare impact analysis of changes"
                    ]
                }
            ]
        }

    async def _setup_documentation_requirements(self):
        """Setup documentation requirements by audit type"""
        self.documentation_requirements = {
            AuditType.DCAA.value: {
                "accounting_system": [
                    "Chart of accounts",
                    "Accounting policies and procedures",
                    "System access controls",
                    "Backup and recovery procedures"
                ],
                "cost_data": [
                    "Labor distribution records",
                    "Payroll registers",
                    "Indirect cost pools",
                    "Cost allocation bases"
                ],
                "contracts": [
                    "Contract documents",
                    "Modifications",
                    "Correspondence files",
                    "Progress reports"
                ]
            },
            AuditType.INCURRED_COST.value: {
                "financial_statements": [
                    "Annual financial statements", 
                    "CPA audit reports",
                    "Management letters",
                    "Footnote disclosures"
                ],
                "cost_proposals": [
                    "Final indirect cost rate proposals",
                    "Supporting schedules",
                    "Rate calculations",
                    "Unallowable cost schedules"
                ]
            }
        }

    async def prepare_audit(self, contract_id: str, audit_type: str) -> Dict[str, Any]:
        """Prepare for upcoming audit"""
        try:
            audit_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Create audit schedule entry
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get current year for audit period
            current_year = datetime.now().year
            audit_period_start = f"{current_year-1}-01-01"
            audit_period_end = f"{current_year-1}-12-31"
            
            cursor.execute("""
                INSERT INTO audit_schedules (
                    id, contract_id, audit_type, audit_agency, audit_period_start,
                    audit_period_end, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                audit_id, contract_id, audit_type, "DCAA",
                audit_period_start, audit_period_end,
                AuditStatus.IN_PREPARATION.value, now, now
            ))
            
            # Generate preparation checklist
            checklist_items = await self._generate_preparation_checklist(audit_id, audit_type)
            
            # Initialize document collection plan
            document_plan = await self._create_document_collection_plan(audit_id, audit_type)
            
            # Setup audit team
            audit_team = await self._setup_audit_response_team(audit_id)
            
            conn.commit()
            conn.close()
            
            result = {
                "audit_id": audit_id,
                "contract_id": contract_id,
                "audit_type": audit_type,
                "preparation_status": "initiated",
                "audit_period": {
                    "start": audit_period_start,
                    "end": audit_period_end
                },
                "preparation_checklist": checklist_items,
                "document_collection_plan": document_plan,
                "audit_response_team": audit_team,
                "estimated_timeline": {
                    "preparation_weeks": 3,
                    "document_collection_weeks": 2,
                    "fieldwork_weeks": 4,
                    "response_weeks": 2
                },
                "immediate_actions": [
                    "Notify key personnel of audit",
                    "Begin document collection process", 
                    "Schedule preparation meetings",
                    "Review prior audit findings"
                ]
            }
            
            logger.info(f"Audit preparation initiated: {audit_type} for contract {contract_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error preparing audit: {e}")
            return {"error": str(e)}

    async def _generate_preparation_checklist(self, audit_id: str, audit_type: str) -> List[Dict[str, Any]]:
        """Generate detailed preparation checklist"""
        checklist_items = []
        
        if audit_type in self.audit_checklists:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for category in self.audit_checklists[audit_type]:
                for item in category["items"]:
                    checklist_id = str(uuid.uuid4())
                    due_date = (datetime.now() + timedelta(days=14)).isoformat()
                    
                    cursor.execute("""
                        INSERT INTO audit_checklists (
                            id, audit_id, checklist_category, checklist_item,
                            due_date, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        checklist_id, audit_id, category["category"], item,
                        due_date, datetime.now().isoformat(), datetime.now().isoformat()
                    ))
                    
                    checklist_items.append({
                        "id": checklist_id,
                        "category": category["category"],
                        "item": item,
                        "due_date": due_date,
                        "status": "pending",
                        "priority": "medium"
                    })
            
            conn.commit()
            conn.close()
        
        return checklist_items

    async def _create_document_collection_plan(self, audit_id: str, audit_type: str) -> Dict[str, Any]:
        """Create comprehensive document collection plan"""
        document_plan = {
            "categories": [],
            "total_documents": 0,
            "estimated_collection_time": "2-3 weeks"
        }
        
        if audit_type in self.documentation_requirements:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            requirements = self.documentation_requirements[audit_type]
            
            for category, documents in requirements.items():
                category_info = {
                    "category": category,
                    "documents": []
                }
                
                for doc in documents:
                    doc_id = str(uuid.uuid4())
                    
                    cursor.execute("""
                        INSERT INTO document_collection (
                            id, audit_id, document_category, document_name,
                            created_at
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (
                        doc_id, audit_id, category, doc,
                        datetime.now().isoformat()
                    ))
                    
                    category_info["documents"].append({
                        "id": doc_id,
                        "name": doc,
                        "status": "pending",
                        "priority": "high" if category == "contracts" else "medium"
                    })
                
                document_plan["categories"].append(category_info)
                document_plan["total_documents"] += len(documents)
            
            conn.commit()
            conn.close()
        
        return document_plan

    async def _setup_audit_response_team(self, audit_id: str) -> Dict[str, Any]:
        """Setup audit response team structure"""
        return {
            "team_lead": "To be assigned",
            "accounting_lead": "To be assigned",
            "contracts_lead": "To be assigned",
            "technical_lead": "To be assigned",
            "supporting_members": [
                "Cost accounting specialist",
                "Contract administrator",
                "IT systems administrator",
                "Records management specialist"
            ],
            "external_support": {
                "legal_counsel": "Available if needed",
                "audit_consultants": "Available if needed"
            },
            "communication_protocol": [
                "Daily team standup meetings",
                "Weekly progress reports",
                "Immediate escalation for issues"
            ]
        }

    async def get_checklist(self, audit_id: str) -> Dict[str, Any]:
        """Get comprehensive audit preparation checklist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get audit details
            cursor.execute("""
                SELECT audit_type, status, contract_id, audit_period_start, audit_period_end
                FROM audit_schedules WHERE id = ?
            """, (audit_id,))
            
            audit = cursor.fetchone()
            if not audit:
                return {"error": "Audit not found"}
            
            # Get checklist items
            cursor.execute("""
                SELECT id, checklist_category, checklist_item, responsible_party,
                       due_date, completion_date, status, priority, completion_percentage,
                       notes
                FROM audit_checklists 
                WHERE audit_id = ?
                ORDER BY checklist_category, checklist_item
            """, (audit_id,))
            
            checklist_items = []
            categories = {}
            
            for row in cursor.fetchall():
                item = {
                    "id": row[0],
                    "category": row[1],
                    "item": row[2],
                    "responsible_party": row[3],
                    "due_date": row[4],
                    "completion_date": row[5],
                    "status": row[6],
                    "priority": row[7],
                    "completion_percentage": row[8],
                    "notes": row[9]
                }
                checklist_items.append(item)
                
                # Group by category
                if row[1] not in categories:
                    categories[row[1]] = []
                categories[row[1]].append(item)
            
            # Calculate overall progress
            total_items = len(checklist_items)
            completed_items = len([item for item in checklist_items if item["status"] == "completed"])
            overall_progress = (completed_items / total_items * 100) if total_items > 0 else 0
            
            # Get document collection status
            cursor.execute("""
                SELECT document_category, COUNT(*) as total,
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM document_collection 
                WHERE audit_id = ?
                GROUP BY document_category
            """, (audit_id,))
            
            document_status = {}
            for row in cursor.fetchall():
                document_status[row[0]] = {
                    "total": row[1],
                    "completed": row[2],
                    "percentage": (row[2] / row[1] * 100) if row[1] > 0 else 0
                }
            
            conn.close()
            
            return {
                "audit_id": audit_id,
                "audit_type": audit[0],
                "audit_status": audit[1],
                "contract_id": audit[2],
                "audit_period": {
                    "start": audit[3],
                    "end": audit[4]
                },
                "overall_progress": round(overall_progress, 2),
                "checklist_summary": {
                    "total_items": total_items,
                    "completed_items": completed_items,
                    "in_progress_items": len([item for item in checklist_items if item["status"] == "in_progress"]),
                    "overdue_items": self._count_overdue_items(checklist_items)
                },
                "checklist_by_category": categories,
                "document_collection_status": document_status,
                "critical_actions": self._identify_critical_actions(checklist_items),
                "upcoming_deadlines": self._get_upcoming_deadlines(checklist_items)
            }
            
        except Exception as e:
            logger.error(f"Error getting audit checklist: {e}")
            return {"error": str(e)}

    def _count_overdue_items(self, checklist_items: List[Dict[str, Any]]) -> int:
        """Count overdue checklist items"""
        now = datetime.now()
        overdue_count = 0
        
        for item in checklist_items:
            if item["due_date"] and item["status"] != "completed":
                try:
                    due_date = datetime.fromisoformat(item["due_date"])
                    if due_date < now:
                        overdue_count += 1
                except:
                    pass
        
        return overdue_count

    def _identify_critical_actions(self, checklist_items: List[Dict[str, Any]]) -> List[str]:
        """Identify critical actions that need immediate attention"""
        critical_actions = []
        now = datetime.now()
        
        for item in checklist_items:
            if item["priority"] == "high" and item["status"] == "pending":
                critical_actions.append(f"Complete: {item['item']}")
            
            if item["due_date"]:
                try:
                    due_date = datetime.fromisoformat(item["due_date"])
                    days_until_due = (due_date - now).days
                    
                    if days_until_due <= 3 and item["status"] != "completed":
                        critical_actions.append(f"URGENT: {item['item']} due in {days_until_due} days")
                except:
                    pass
        
        return critical_actions[:10]  # Return top 10 critical actions

    def _get_upcoming_deadlines(self, checklist_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get upcoming deadlines in next 7 days"""
        deadlines = []
        now = datetime.now()
        
        for item in checklist_items:
            if item["due_date"] and item["status"] != "completed":
                try:
                    due_date = datetime.fromisoformat(item["due_date"])
                    days_until_due = (due_date - now).days
                    
                    if 0 <= days_until_due <= 7:
                        deadlines.append({
                            "item": item["item"],
                            "due_date": item["due_date"],
                            "days_until_due": days_until_due,
                            "priority": item["priority"],
                            "responsible_party": item["responsible_party"]
                        })
                except:
                    pass
        
        return sorted(deadlines, key=lambda x: x["days_until_due"])

    async def submit_evidence(self, audit_id: str, evidence_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit evidence for audit"""
        try:
            evidence_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO evidence_repository (
                    id, audit_id, finding_id, evidence_type, evidence_title,
                    evidence_description, evidence_source, collection_date,
                    collected_by, file_path, relevance_score, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence_id, audit_id, evidence_data.get("finding_id"),
                evidence_data["evidence_type"], evidence_data["evidence_title"],
                evidence_data.get("evidence_description"),
                evidence_data.get("evidence_source"),
                evidence_data.get("collection_date", now),
                evidence_data["collected_by"],
                evidence_data.get("file_path"),
                evidence_data.get("relevance_score", 5), now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "evidence_id": evidence_id,
                "audit_id": audit_id,
                "evidence_type": evidence_data["evidence_type"],
                "evidence_title": evidence_data["evidence_title"],
                "collection_date": evidence_data.get("collection_date", now),
                "status": "submitted",
                "next_steps": [
                    "Catalog and organize evidence",
                    "Review for completeness",
                    "Prepare evidence index",
                    "Ensure chain of custody"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error submitting evidence: {e}")
            return {"error": str(e)}

    async def track_findings(self, audit_id: str) -> Dict[str, Any]:
        """Track audit findings and responses"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all findings for audit
            cursor.execute("""
                SELECT id, finding_number, finding_type, severity, title,
                       questioned_amount, status, created_at
                FROM audit_findings 
                WHERE audit_id = ?
                ORDER BY severity DESC, created_at ASC
            """, (audit_id,))
            
            findings = []
            total_questioned_costs = Decimal('0')
            severity_counts = {}
            
            for row in cursor.fetchall():
                finding = {
                    "finding_id": row[0],
                    "finding_number": row[1],
                    "finding_type": row[2],
                    "severity": row[3],
                    "title": row[4],
                    "questioned_amount": row[5] or 0,
                    "status": row[6],
                    "created_date": row[7]
                }
                findings.append(finding)
                
                total_questioned_costs += Decimal(str(finding["questioned_amount"]))
                severity_counts[finding["severity"]] = severity_counts.get(finding["severity"], 0) + 1
            
            # Get corrective action plans
            cursor.execute("""
                SELECT f.id, c.action_description, c.responsible_party,
                       c.target_completion_date, c.status, c.progress_percentage
                FROM audit_findings f
                JOIN corrective_action_plans c ON f.id = c.finding_id
                WHERE f.audit_id = ?
            """, (audit_id,))
            
            action_plans = []
            for row in cursor.fetchall():
                action_plans.append({
                    "finding_id": row[0],
                    "action_description": row[1],
                    "responsible_party": row[2],
                    "target_completion_date": row[3],
                    "status": row[4],
                    "progress_percentage": row[5] or 0
                })
            
            conn.close()
            
            return {
                "audit_id": audit_id,
                "findings_summary": {
                    "total_findings": len(findings),
                    "total_questioned_costs": float(total_questioned_costs),
                    "severity_breakdown": severity_counts,
                    "open_findings": len([f for f in findings if f["status"] == "open"]),
                    "closed_findings": len([f for f in findings if f["status"] == "closed"])
                },
                "findings_detail": findings,
                "corrective_action_plans": action_plans,
                "response_status": self._assess_response_status(findings, action_plans),
                "recommendations": [
                    "Prioritize critical and significant findings",
                    "Develop comprehensive corrective action plans",
                    "Establish regular progress monitoring",
                    "Engage with auditors on disputed findings"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error tracking findings: {e}")
            return {"error": str(e)}

    def _assess_response_status(self, findings: List[Dict[str, Any]], 
                              action_plans: List[Dict[str, Any]]) -> str:
        """Assess overall response status"""
        if not findings:
            return "no_findings"
        
        open_findings = [f for f in findings if f["status"] == "open"]
        critical_findings = [f for f in findings if f["severity"] == "critical"]
        
        if critical_findings and len(open_findings) > len(findings) * 0.5:
            return "needs_immediate_attention"
        elif open_findings:
            return "response_in_progress"
        else:
            return "response_complete"

    async def generate_response_template(self, finding_id: str) -> Dict[str, Any]:
        """Generate response template for audit finding"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT finding_type, severity, title, description, 
                       questioned_amount, regulation_citation
                FROM audit_findings WHERE id = ?
            """, (finding_id,))
            
            finding = cursor.fetchone()
            if not finding:
                return {"error": "Finding not found"}
            
            conn.close()
            
            # Generate response template based on finding type and severity
            template = {
                "finding_id": finding_id,
                "response_sections": [
                    {
                        "section": "understanding_of_finding",
                        "description": "Contractor's understanding of the auditor's position",
                        "template": f"We understand the auditor's position regarding {finding[2].lower()}..."
                    },
                    {
                        "section": "contractor_position", 
                        "description": "Contractor's position and disagreement (if any)",
                        "template": "The contractor's position is..."
                    },
                    {
                        "section": "corrective_action",
                        "description": "Corrective actions taken or planned",
                        "template": "To address this finding, we have implemented/will implement the following corrective actions..."
                    },
                    {
                        "section": "supporting_documentation",
                        "description": "References to supporting documentation",
                        "template": "Please refer to the following supporting documentation..."
                    }
                ],
                "response_guidelines": [
                    "Be specific and factual in all responses",
                    "Provide supporting documentation for all claims",
                    "Address each element of the finding",
                    "Propose realistic corrective action timelines",
                    "Maintain professional tone throughout"
                ],
                "estimated_questioned_costs": finding[4] or 0,
                "regulatory_citations": finding[5] or "Various FAR/CAS provisions",
                "recommended_timeline": self._get_recommended_response_timeline(finding[1])
            }
            
            return template
            
        except Exception as e:
            logger.error(f"Error generating response template: {e}")
            return {"error": str(e)}

    def _get_recommended_response_timeline(self, severity: str) -> str:
        """Get recommended response timeline based on severity"""
        timelines = {
            FindingSeverity.CRITICAL.value: "7-10 business days",
            FindingSeverity.SIGNIFICANT.value: "14-21 business days", 
            FindingSeverity.MINOR.value: "21-30 business days",
            FindingSeverity.OBSERVATION.value: "30-45 business days"
        }
        return timelines.get(severity, "21-30 business days")

    async def create_corrective_action_plan(self, finding_id: str, 
                                          action_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create corrective action plan for finding"""
        try:
            action_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO corrective_action_plans (
                    id, finding_id, action_description, responsible_party,
                    target_completion_date, cost_impact, resource_requirements,
                    success_criteria, verification_method, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                action_id, finding_id, action_data["action_description"],
                action_data["responsible_party"], action_data["target_completion_date"],
                action_data.get("cost_impact", 0),
                action_data.get("resource_requirements"),
                action_data.get("success_criteria"),
                action_data.get("verification_method"), now, now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "action_id": action_id,
                "finding_id": finding_id,
                "action_description": action_data["action_description"],
                "responsible_party": action_data["responsible_party"],
                "target_completion_date": action_data["target_completion_date"],
                "status": "planned",
                "monitoring_plan": [
                    "Weekly progress reviews",
                    "Milestone tracking",
                    "Resource allocation monitoring",
                    "Success criteria validation"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating corrective action plan: {e}")
            return {"error": str(e)}

# Global instance
audit_system = AuditPreparationSystem()