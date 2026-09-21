#!/usr/bin/env python3
"""
Contract Lifecycle Management System
Comprehensive contract management from award to closeout
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

class ContractStatus(Enum):
    AWARDED = "awarded"
    IN_NEGOTIATION = "in_negotiation"
    SIGNED = "signed"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    CLOSED_OUT = "closed_out"

class ModificationType(Enum):
    ADMINISTRATIVE = "administrative"
    CHANGE_ORDER = "change_order"
    FUNDING_INCREASE = "funding_increase"
    SCOPE_CHANGE = "scope_change"
    PERIOD_EXTENSION = "period_extension"
    TERMINATION = "termination"

class MilestoneStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    AT_RISK = "at_risk"

class InvoiceStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    OVERDUE = "overdue"
    DISPUTED = "disputed"

class ContractLifecycleSystem:
    def __init__(self):
        self.db_path = "data/contract_lifecycle.db"
        self.workflow_templates = {}
        self.notification_rules = {}

    async def initialize(self):
        """Initialize contract lifecycle management system"""
        try:
            await self._create_database_schema()
            await self._setup_workflow_templates()
            await self._setup_notification_rules()
            logger.info("Contract Lifecycle Management System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Contract Lifecycle Management System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for contract lifecycle management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Contracts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                id TEXT PRIMARY KEY,
                contract_number TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                agency TEXT NOT NULL,
                contracting_officer TEXT,
                program_manager TEXT,
                contract_type TEXT NOT NULL,
                award_date TEXT NOT NULL,
                effective_date TEXT,
                expiration_date TEXT,
                base_period_start TEXT,
                base_period_end TEXT,
                option_periods TEXT,
                total_contract_value REAL NOT NULL,
                funded_amount REAL DEFAULT 0.0,
                obligated_amount REAL DEFAULT 0.0,
                invoiced_amount REAL DEFAULT 0.0,
                paid_amount REAL DEFAULT 0.0,
                remaining_funds REAL,
                status TEXT NOT NULL,
                performance_start_date TEXT,
                place_of_performance TEXT,
                naics_code TEXT,
                small_business_type TEXT,
                security_requirements TEXT,
                deliverables_summary TEXT,
                key_personnel TEXT,
                subcontractor_plan TEXT,
                closeout_requirements TEXT,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Contract modifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contract_modifications (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                modification_number TEXT NOT NULL,
                modification_type TEXT NOT NULL,
                description TEXT NOT NULL,
                justification TEXT,
                value_change REAL DEFAULT 0.0,
                period_change_days INTEGER DEFAULT 0,
                scope_change_description TEXT,
                effective_date TEXT NOT NULL,
                contracting_officer TEXT,
                status TEXT NOT NULL,
                supporting_documents TEXT,
                approval_workflow TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        # Contract milestones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contract_milestones (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                milestone_name TEXT NOT NULL,
                description TEXT,
                due_date TEXT NOT NULL,
                completed_date TEXT,
                status TEXT NOT NULL,
                deliverables TEXT,
                acceptance_criteria TEXT,
                responsible_party TEXT,
                dependencies TEXT,
                risk_factors TEXT,
                completion_percentage REAL DEFAULT 0.0,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        # Invoices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                billing_period_start TEXT,
                billing_period_end TEXT,
                invoice_amount REAL NOT NULL,
                labor_amount REAL DEFAULT 0.0,
                material_amount REAL DEFAULT 0.0,
                travel_amount REAL DEFAULT 0.0,
                other_costs REAL DEFAULT 0.0,
                status TEXT NOT NULL,
                submitted_date TEXT,
                approved_date TEXT,
                payment_terms TEXT,
                due_date TEXT,
                supporting_documentation TEXT,
                government_review_notes TEXT,
                rejection_reason TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        # Payments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                invoice_id TEXT NOT NULL,
                payment_amount REAL NOT NULL,
                payment_date TEXT,
                payment_method TEXT,
                reference_number TEXT,
                status TEXT NOT NULL,
                processing_time_days INTEGER,
                interest_penalty REAL DEFAULT 0.0,
                discount_taken REAL DEFAULT 0.0,
                net_payment_amount REAL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id),
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        """)
        
        # Performance metrics table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                reporting_period TEXT NOT NULL,
                cost_performance_index REAL,
                schedule_performance_index REAL,
                budget_at_completion REAL,
                estimate_at_completion REAL,
                estimate_to_complete REAL,
                variance_at_completion REAL,
                percent_complete REAL,
                critical_path_delay_days INTEGER DEFAULT 0,
                quality_score REAL DEFAULT 100.0,
                customer_satisfaction REAL DEFAULT 100.0,
                risk_score REAL DEFAULT 0.0,
                issues_count INTEGER DEFAULT 0,
                corrective_actions TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        # Closeout activities table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS closeout_activities (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                activity_name TEXT NOT NULL,
                description TEXT,
                responsible_party TEXT,
                due_date TEXT,
                completed_date TEXT,
                status TEXT NOT NULL,
                deliverables TEXT,
                completion_notes TEXT,
                required_approvals TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (contract_id) REFERENCES contracts (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_workflow_templates(self):
        """Setup contract workflow templates"""
        self.workflow_templates = {
            "contract_award": [
                {"step": "award_notification", "description": "Receive award notification"},
                {"step": "team_assignment", "description": "Assign project team"},
                {"step": "kickoff_meeting", "description": "Schedule kickoff meeting"},
                {"step": "contract_review", "description": "Review contract terms"},
                {"step": "compliance_setup", "description": "Setup compliance tracking"},
                {"step": "performance_baseline", "description": "Establish performance baseline"}
            ],
            "contract_execution": [
                {"step": "work_authorization", "description": "Issue work authorization"},
                {"step": "resource_allocation", "description": "Allocate resources"},
                {"step": "progress_tracking", "description": "Track progress against milestones"},
                {"step": "quality_assurance", "description": "Implement QA processes"},
                {"step": "risk_monitoring", "description": "Monitor and mitigate risks"}
            ],
            "contract_closeout": [
                {"step": "final_deliverables", "description": "Submit final deliverables"},
                {"step": "final_invoice", "description": "Submit final invoice"},
                {"step": "government_acceptance", "description": "Obtain government acceptance"},
                {"step": "property_disposal", "description": "Dispose of government property"},
                {"step": "final_reporting", "description": "Submit final reports"},
                {"step": "lessons_learned", "description": "Document lessons learned"},
                {"step": "archive_records", "description": "Archive contract records"}
            ]
        }

    async def _setup_notification_rules(self):
        """Setup notification rules"""
        self.notification_rules = {
            "milestone_due": {"days_before": 7, "enabled": True},
            "invoice_due": {"days_before": 5, "enabled": True},
            "contract_expiration": {"days_before": 30, "enabled": True},
            "funding_threshold": {"percentage": 80, "enabled": True},
            "performance_issues": {"threshold": 0.9, "enabled": True}
        }

    async def create_contract(self, contract_data: Dict[str, Any], 
                             award_details: Dict[str, Any]) -> Dict[str, Any]:
        """Create new contract from award"""
        try:
            contract_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Extract contract information
            contract_number = award_details.get("contract_number")
            if not contract_number:
                contract_number = f"CTR-{datetime.now().strftime('%Y%m%d')}-{contract_id[:8]}"
            
            # Calculate key dates
            award_date = award_details.get("award_date", now)
            performance_start = award_details.get("performance_start_date")
            base_period_months = contract_data.get("base_period_months", 12)
            
            if performance_start:
                start_date = datetime.fromisoformat(performance_start)
                base_period_end = (start_date + timedelta(days=base_period_months * 30)).isoformat()
            else:
                start_date = datetime.fromisoformat(award_date)
                performance_start = start_date.isoformat()
                base_period_end = (start_date + timedelta(days=base_period_months * 30)).isoformat()
            
            # Store contract
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO contracts (
                    id, contract_number, title, agency, contracting_officer,
                    contract_type, award_date, effective_date, base_period_start,
                    base_period_end, total_contract_value, status, performance_start_date,
                    place_of_performance, naics_code, deliverables_summary,
                    audit_trail, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                contract_id, contract_number, contract_data.get("title"),
                contract_data.get("agency"), award_details.get("contracting_officer"),
                contract_data.get("contract_type"), award_date, award_date,
                performance_start, base_period_end,
                contract_data.get("total_value", 0), ContractStatus.AWARDED.value,
                performance_start, contract_data.get("place_of_performance"),
                contract_data.get("naics_code"), contract_data.get("deliverables_summary"),
                json.dumps([{"action": "contract_created", "date": now}]),
                now, now
            ))
            
            # Create initial milestones
            await self._create_initial_milestones(contract_id, contract_data)
            
            # Initialize performance tracking
            await self._initialize_performance_tracking(contract_id)
            
            # Setup closeout activities
            await self._setup_closeout_activities(contract_id)
            
            conn.commit()
            conn.close()
            
            result = {
                "contract_id": contract_id,
                "contract_number": contract_number,
                "status": ContractStatus.AWARDED.value,
                "award_date": award_date,
                "performance_start_date": performance_start,
                "base_period_end": base_period_end,
                "total_value": contract_data.get("total_value", 0),
                "next_actions": [
                    "Schedule contract kickoff meeting",
                    "Assign project team members", 
                    "Review contract terms and conditions",
                    "Setup project management systems",
                    "Begin work authorization process"
                ]
            }
            
            logger.info(f"Contract created: {contract_number} (${contract_data.get('total_value', 0):,.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Error creating contract: {e}")
            return {"error": str(e)}

    async def _create_initial_milestones(self, contract_id: str, contract_data: Dict[str, Any]):
        """Create initial contract milestones"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Default milestones for all contracts
        default_milestones = [
            {
                "name": "Contract Kickoff",
                "description": "Initial project kickoff meeting",
                "days_from_start": 7
            },
            {
                "name": "30-Day Status Review",
                "description": "First monthly status review",
                "days_from_start": 30
            },
            {
                "name": "Mid-Point Review",
                "description": "Mid-contract performance review",
                "days_from_start": 180
            },
            {
                "name": "Final Deliverables",
                "description": "Submit all final deliverables",
                "days_from_start": 350
            }
        ]
        
        performance_start = contract_data.get("performance_start_date", datetime.now().isoformat())
        start_date = datetime.fromisoformat(performance_start)
        
        for milestone in default_milestones:
            milestone_id = str(uuid.uuid4())
            due_date = (start_date + timedelta(days=milestone["days_from_start"])).isoformat()
            
            cursor.execute("""
                INSERT INTO contract_milestones (
                    id, contract_id, milestone_name, description, due_date,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                milestone_id, contract_id, milestone["name"],
                milestone["description"], due_date, MilestoneStatus.NOT_STARTED.value,
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()

    async def _initialize_performance_tracking(self, contract_id: str):
        """Initialize performance tracking for contract"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        metric_id = str(uuid.uuid4())
        current_period = datetime.now().strftime("%Y-%m")
        
        cursor.execute("""
            INSERT INTO performance_metrics (
                id, contract_id, reporting_period, cost_performance_index,
                schedule_performance_index, percent_complete, quality_score,
                customer_satisfaction, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            metric_id, contract_id, current_period, 1.0, 1.0, 0.0, 100.0, 100.0,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()

    async def _setup_closeout_activities(self, contract_id: str):
        """Setup contract closeout activities"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        closeout_activities = self.workflow_templates["contract_closeout"]
        
        for activity in closeout_activities:
            activity_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO closeout_activities (
                    id, contract_id, activity_name, description,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                activity_id, contract_id, activity["step"],
                activity["description"], "not_started",
                datetime.now().isoformat(), datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()

    async def get_status(self, contract_id: str) -> Dict[str, Any]:
        """Get comprehensive contract status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get contract details
            cursor.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
            contract = cursor.fetchone()
            
            if not contract:
                return {"error": "Contract not found"}
            
            # Get milestone status
            cursor.execute("""
                SELECT status, COUNT(*) as count 
                FROM contract_milestones 
                WHERE contract_id = ? 
                GROUP BY status
            """, (contract_id,))
            
            milestone_summary = {}
            for row in cursor.fetchall():
                milestone_summary[row[0]] = row[1]
            
            # Get financial status
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(invoice_amount), 0) as total_invoiced,
                    COUNT(*) as invoice_count
                FROM invoices 
                WHERE contract_id = ?
            """, (contract_id,))
            
            financial = cursor.fetchone()
            total_invoiced = financial[0] if financial else 0
            invoice_count = financial[1] if financial else 0
            
            # Get recent performance metrics
            cursor.execute("""
                SELECT * FROM performance_metrics 
                WHERE contract_id = ? 
                ORDER BY created_at DESC 
                LIMIT 1
            """, (contract_id,))
            
            performance = cursor.fetchone()
            
            conn.close()
            
            # Calculate key metrics
            total_value = contract[8] or 0
            funded_amount = contract[9] or 0
            utilization_rate = (total_invoiced / funded_amount * 100) if funded_amount > 0 else 0
            
            # Determine health status
            health_status = await self._calculate_contract_health(contract, performance, milestone_summary)
            
            return {
                "contract_id": contract_id,
                "contract_number": contract[1],
                "title": contract[2],
                "agency": contract[3],
                "status": contract[18],
                "award_date": contract[5],
                "expiration_date": contract[7],
                "financial_summary": {
                    "total_value": total_value,
                    "funded_amount": funded_amount,
                    "invoiced_amount": total_invoiced,
                    "paid_amount": contract[12] or 0,
                    "remaining_funds": funded_amount - total_invoiced,
                    "utilization_rate": round(utilization_rate, 2)
                },
                "milestone_summary": milestone_summary,
                "performance_summary": {
                    "cost_performance_index": performance[3] if performance else 1.0,
                    "schedule_performance_index": performance[4] if performance else 1.0,
                    "percent_complete": performance[7] if performance else 0.0,
                    "quality_score": performance[10] if performance else 100.0
                } if performance else {},
                "health_status": health_status,
                "invoice_count": invoice_count,
                "days_remaining": self._calculate_days_remaining(contract[7]) if contract[7] else None,
                "critical_actions": await self._identify_critical_actions(contract_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting contract status: {e}")
            return {"error": str(e)}

    async def _calculate_contract_health(self, contract: tuple, 
                                       performance: tuple, 
                                       milestone_summary: Dict[str, int]) -> str:
        """Calculate overall contract health status"""
        health_score = 100
        
        # Performance metrics impact
        if performance:
            cpi = performance[3] or 1.0
            spi = performance[4] or 1.0
            quality_score = performance[10] or 100.0
            
            if cpi < 0.9:
                health_score -= 20
            if spi < 0.9:
                health_score -= 20
            if quality_score < 90:
                health_score -= 10
        
        # Milestone status impact
        total_milestones = sum(milestone_summary.values())
        delayed_milestones = milestone_summary.get("delayed", 0)
        
        if total_milestones > 0:
            delay_rate = delayed_milestones / total_milestones
            if delay_rate > 0.2:
                health_score -= 15
        
        # Financial utilization impact
        funded_amount = contract[9] or 0
        invoiced_amount = contract[11] or 0
        
        if funded_amount > 0:
            utilization = invoiced_amount / funded_amount
            if utilization > 0.95:
                health_score -= 10  # Potential funding issues
        
        # Determine health status
        if health_score >= 90:
            return "EXCELLENT"
        elif health_score >= 75:
            return "GOOD"
        elif health_score >= 60:
            return "FAIR"
        elif health_score >= 40:
            return "POOR"
        else:
            return "CRITICAL"

    def _calculate_days_remaining(self, expiration_date: str) -> int:
        """Calculate days remaining until contract expiration"""
        try:
            expiry = datetime.fromisoformat(expiration_date)
            return (expiry - datetime.now()).days
        except:
            return 0

    async def _identify_critical_actions(self, contract_id: str) -> List[str]:
        """Identify critical actions needed for contract"""
        actions = []
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check for overdue milestones
        cursor.execute("""
            SELECT COUNT(*) FROM contract_milestones 
            WHERE contract_id = ? AND due_date < ? AND status != 'completed'
        """, (contract_id, datetime.now().isoformat()))
        
        overdue_count = cursor.fetchone()[0]
        if overdue_count > 0:
            actions.append(f"Address {overdue_count} overdue milestone(s)")
        
        # Check for pending invoices
        cursor.execute("""
            SELECT COUNT(*) FROM invoices 
            WHERE contract_id = ? AND status = 'draft'
        """, (contract_id,))
        
        draft_invoices = cursor.fetchone()[0]
        if draft_invoices > 0:
            actions.append(f"Submit {draft_invoices} pending invoice(s)")
        
        # Check contract expiration
        cursor.execute("SELECT expiration_date FROM contracts WHERE id = ?", (contract_id,))
        expiration = cursor.fetchone()
        if expiration and expiration[0]:
            days_remaining = self._calculate_days_remaining(expiration[0])
            if days_remaining < 90:
                actions.append("Plan contract renewal or closeout")
        
        conn.close()
        
        if not actions:
            actions.append("No critical actions required")
        
        return actions

    async def submit_modification(self, contract_id: str, 
                                 modification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit contract modification"""
        try:
            modification_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Generate modification number
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM contract_modifications 
                WHERE contract_id = ?
            """, (contract_id,))
            
            mod_count = cursor.fetchone()[0] + 1
            modification_number = f"P00{mod_count:03d}"
            
            # Store modification
            cursor.execute("""
                INSERT INTO contract_modifications (
                    id, contract_id, modification_number, modification_type,
                    description, justification, value_change, effective_date,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                modification_id, contract_id, modification_number,
                modification_data.get("type", ModificationType.ADMINISTRATIVE.value),
                modification_data.get("description"),
                modification_data.get("justification"),
                modification_data.get("value_change", 0),
                modification_data.get("effective_date", now),
                "submitted", now
            ))
            
            # Update contract if modification affects value or dates
            value_change = modification_data.get("value_change", 0)
            if value_change != 0:
                cursor.execute("""
                    UPDATE contracts 
                    SET total_contract_value = total_contract_value + ?,
                        updated_at = ?
                    WHERE id = ?
                """, (value_change, now, contract_id))
            
            conn.commit()
            conn.close()
            
            result = {
                "modification_id": modification_id,
                "modification_number": modification_number,
                "contract_id": contract_id,
                "type": modification_data.get("type"),
                "value_change": value_change,
                "status": "submitted",
                "next_steps": [
                    "Government review and processing",
                    "Contracting Officer approval required",
                    "Bilateral signature if required",
                    "Update internal systems upon approval"
                ]
            }
            
            logger.info(f"Contract modification submitted: {modification_number}")
            return result
            
        except Exception as e:
            logger.error(f"Error submitting modification: {e}")
            return {"error": str(e)}

    async def generate_invoice(self, contract_id: str, 
                              billing_period: Dict[str, str],
                              cost_details: Dict[str, Any]) -> Dict[str, Any]:
        """Generate contract invoice"""
        try:
            invoice_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Generate invoice number
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT contract_number FROM contracts WHERE id = ?", (contract_id,))
            contract_number = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM invoices WHERE contract_id = ?
            """, (contract_id,))
            
            invoice_count = cursor.fetchone()[0] + 1
            invoice_number = f"{contract_number}-INV-{invoice_count:04d}"
            
            # Calculate invoice amounts
            labor_amount = Decimal(str(cost_details.get("labor_costs", 0)))
            material_amount = Decimal(str(cost_details.get("material_costs", 0)))
            travel_amount = Decimal(str(cost_details.get("travel_costs", 0)))
            other_costs = Decimal(str(cost_details.get("other_costs", 0)))
            
            total_amount = labor_amount + material_amount + travel_amount + other_costs
            
            # Calculate due date (typically 30 days)
            invoice_date = datetime.now()
            due_date = (invoice_date + timedelta(days=30)).isoformat()
            
            # Store invoice
            cursor.execute("""
                INSERT INTO invoices (
                    id, contract_id, invoice_number, invoice_date,
                    billing_period_start, billing_period_end, invoice_amount,
                    labor_amount, material_amount, travel_amount, other_costs,
                    status, due_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id, contract_id, invoice_number, now,
                billing_period.get("start_date"), billing_period.get("end_date"),
                float(total_amount), float(labor_amount), float(material_amount),
                float(travel_amount), float(other_costs), InvoiceStatus.DRAFT.value,
                due_date, now, now
            ))
            
            conn.commit()
            conn.close()
            
            result = {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "contract_id": contract_id,
                "invoice_date": now,
                "due_date": due_date,
                "billing_period": billing_period,
                "cost_breakdown": {
                    "labor_costs": float(labor_amount),
                    "material_costs": float(material_amount),
                    "travel_costs": float(travel_amount),
                    "other_costs": float(other_costs),
                    "total_amount": float(total_amount)
                },
                "status": InvoiceStatus.DRAFT.value,
                "next_steps": [
                    "Review invoice for accuracy",
                    "Attach supporting documentation",
                    "Submit to government for processing",
                    "Track payment status"
                ]
            }
            
            logger.info(f"Invoice generated: {invoice_number} - ${total_amount}")
            return result
            
        except Exception as e:
            logger.error(f"Error generating invoice: {e}")
            return {"error": str(e)}

    async def track_payment(self, invoice_id: str) -> Dict[str, Any]:
        """Track payment status for invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get invoice details
            cursor.execute("""
                SELECT i.*, c.contract_number 
                FROM invoices i 
                JOIN contracts c ON i.contract_id = c.id 
                WHERE i.id = ?
            """, (invoice_id,))
            
            invoice = cursor.fetchone()
            if not invoice:
                return {"error": "Invoice not found"}
            
            # Get payment details
            cursor.execute("""
                SELECT * FROM payments WHERE invoice_id = ?
                ORDER BY created_at DESC
            """, (invoice_id,))
            
            payments = []
            total_paid = Decimal('0')
            
            for payment in cursor.fetchall():
                payment_amount = Decimal(str(payment[3]))
                total_paid += payment_amount
                
                payments.append({
                    "payment_id": payment[0],
                    "payment_amount": float(payment_amount),
                    "payment_date": payment[4],
                    "status": payment[6],
                    "reference_number": payment[7]
                })
            
            conn.close()
            
            invoice_amount = Decimal(str(invoice[6]))
            balance_due = invoice_amount - total_paid
            
            # Calculate payment timeline
            invoice_date = datetime.fromisoformat(invoice[3])
            due_date = datetime.fromisoformat(invoice[12])
            days_outstanding = (datetime.now() - invoice_date).days
            days_overdue = max(0, (datetime.now() - due_date).days)
            
            return {
                "invoice_id": invoice_id,
                "invoice_number": invoice[2],
                "contract_number": invoice[17],
                "invoice_amount": float(invoice_amount),
                "total_paid": float(total_paid),
                "balance_due": float(balance_due),
                "payment_status": self._determine_payment_status(invoice, total_paid, invoice_amount),
                "days_outstanding": days_outstanding,
                "days_overdue": days_overdue,
                "payment_history": payments,
                "estimated_payment_date": self._estimate_payment_date(invoice, days_outstanding)
            }
            
        except Exception as e:
            logger.error(f"Error tracking payment: {e}")
            return {"error": str(e)}

    def _determine_payment_status(self, invoice: tuple, total_paid: Decimal, invoice_amount: Decimal) -> str:
        """Determine current payment status"""
        if total_paid >= invoice_amount:
            return PaymentStatus.PAID.value
        elif total_paid > 0:
            return "PARTIAL_PAYMENT"
        elif invoice[10] == InvoiceStatus.APPROVED.value:
            return PaymentStatus.PROCESSING.value
        elif invoice[10] == InvoiceStatus.SUBMITTED.value:
            return PaymentStatus.PENDING.value
        else:
            return PaymentStatus.PENDING.value

    def _estimate_payment_date(self, invoice: tuple, days_outstanding: int) -> str:
        """Estimate payment date based on historical data"""
        # Typical government payment timeframes
        if invoice[10] == InvoiceStatus.APPROVED.value:
            # Approved invoices typically paid within 10 business days
            estimated_days = 10
        elif invoice[10] == InvoiceStatus.SUBMITTED.value:
            # Submitted invoices take 15-30 days for approval + payment
            estimated_days = 25
        else:
            # Draft invoices need to be submitted first
            estimated_days = 35
        
        estimated_date = datetime.now() + timedelta(days=estimated_days)
        return estimated_date.isoformat()

    async def update_milestones(self, contract_id: str, 
                              milestone_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Update contract milestones"""
        try:
            updated_count = 0
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for update in milestone_updates:
                milestone_id = update.get("milestone_id")
                new_status = update.get("status")
                completion_date = update.get("completion_date")
                notes = update.get("notes")
                
                update_fields = ["updated_at = ?"]
                update_values = [datetime.now().isoformat()]
                
                if new_status:
                    update_fields.append("status = ?")
                    update_values.append(new_status)
                
                if completion_date:
                    update_fields.append("completed_date = ?")
                    update_values.append(completion_date)
                
                if notes:
                    update_fields.append("notes = ?")
                    update_values.append(notes)
                
                update_values.append(milestone_id)
                
                cursor.execute(f"""
                    UPDATE contract_milestones 
                    SET {', '.join(update_fields)}
                    WHERE id = ?
                """, update_values)
                
                updated_count += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return {
                "contract_id": contract_id,
                "milestones_updated": updated_count,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"Error updating milestones: {e}")
            return {"error": str(e)}

    async def initiate_closeout(self, contract_id: str) -> Dict[str, Any]:
        """Initiate contract closeout process"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update contract status
            cursor.execute("""
                UPDATE contracts 
                SET status = ?, updated_at = ?
                WHERE id = ?
            """, (ContractStatus.COMPLETED.value, datetime.now().isoformat(), contract_id))
            
            # Get closeout activities
            cursor.execute("""
                SELECT id, activity_name, status 
                FROM closeout_activities 
                WHERE contract_id = ?
                ORDER BY created_at
            """, (contract_id,))
            
            activities = []
            for row in cursor.fetchall():
                activities.append({
                    "activity_id": row[0],
                    "name": row[1],
                    "status": row[2]
                })
            
            conn.commit()
            conn.close()
            
            return {
                "contract_id": contract_id,
                "closeout_status": "initiated",
                "closeout_activities": activities,
                "next_steps": [
                    "Complete all outstanding deliverables",
                    "Submit final invoice",
                    "Dispose of government property",
                    "Submit final reports",
                    "Archive contract records"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error initiating closeout: {e}")
            return {"error": str(e)}

# Global instance
contract_system = ContractLifecycleSystem()