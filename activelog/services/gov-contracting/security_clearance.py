#!/usr/bin/env python3
"""
Security Clearance Tracking System
Comprehensive security clearance management and tracking
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

class ClearanceLevel(Enum):
    PUBLIC_TRUST = "public_trust"
    SECRET = "secret"
    TOP_SECRET = "top_secret"
    TOP_SECRET_SCI = "top_secret_sci"
    Q_CLEARANCE = "q_clearance"
    L_CLEARANCE = "l_clearance"
    CONFIDENTIAL = "confidential"

class ClearanceStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    PENDING = "pending"
    IN_PROCESS = "in_process"
    DENIED = "denied"
    EXPIRED = "expired"

class InvestigationType(Enum):
    NACLC = "naclc"  # National Agency Check with Law and Credit
    MBI = "mbi"      # Moderate Background Investigation
    BI = "bi"        # Background Investigation
    SSBI = "ssbi"    # Single Scope Background Investigation
    SSBI_PR = "ssbi_pr"  # SSBI Periodic Reinvestigation
    T3 = "t3"        # Tier 3 Investigation
    T5 = "t5"        # Tier 5 Investigation

class FacilityClearanceLevel(Enum):
    CONFIDENTIAL = "confidential"
    SECRET = "secret"
    TOP_SECRET = "top_secret"

class SecurityClearanceSystem:
    def __init__(self):
        self.db_path = "data/security_clearance.db"
        self.clearance_requirements = {}
        self.investigation_timelines = {}

    async def initialize(self):
        """Initialize security clearance tracking system"""
        try:
            await self._create_database_schema()
            await self._setup_clearance_requirements()
            await self._setup_investigation_timelines()
            logger.info("Security Clearance System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Security Clearance System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for security clearance tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Personnel clearances table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personnel_clearances (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                middle_initial TEXT,
                ssn_last4 TEXT,
                date_of_birth TEXT,
                citizenship TEXT DEFAULT 'US',
                clearance_level TEXT NOT NULL,
                clearance_status TEXT NOT NULL,
                sponsor_agency TEXT,
                investigation_type TEXT,
                investigation_opened_date TEXT,
                investigation_closed_date TEXT,
                adjudication_date TEXT,
                effective_date TEXT,
                expiration_date TEXT,
                next_review_date TEXT,
                security_officer TEXT,
                sponsoring_organization TEXT,
                position_sensitivity TEXT,
                polygraph_required BOOLEAN DEFAULT 0,
                polygraph_date TEXT,
                polygraph_type TEXT,
                special_access_programs TEXT,
                compartments TEXT,
                caveats TEXT,
                reciprocity_accepted BOOLEAN DEFAULT 1,
                interim_clearance BOOLEAN DEFAULT 0,
                debriefing_required BOOLEAN DEFAULT 0,
                debriefing_date TEXT,
                notes TEXT,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Facility security clearances table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facility_clearances (
                id TEXT PRIMARY KEY,
                facility_name TEXT NOT NULL,
                facility_address TEXT,
                facility_code TEXT UNIQUE,
                clearance_level TEXT NOT NULL,
                status TEXT NOT NULL,
                sponsoring_agency TEXT NOT NULL,
                cognizant_security_office TEXT,
                facility_security_officer TEXT,
                effective_date TEXT NOT NULL,
                expiration_date TEXT,
                next_inspection_date TEXT,
                last_inspection_date TEXT,
                inspection_results TEXT,
                security_violations_count INTEGER DEFAULT 0,
                corrective_actions TEXT,
                special_security_measures TEXT,
                emergency_contacts TEXT,
                backup_fso TEXT,
                safeguarding_capabilities TEXT,
                it_security_plan TEXT,
                physical_security_plan TEXT,
                personnel_security_plan TEXT,
                industrial_security_plan TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Clearance renewals table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clearance_renewals (
                id TEXT PRIMARY KEY,
                clearance_id TEXT NOT NULL,
                renewal_type TEXT NOT NULL,
                initiation_date TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                investigation_type TEXT,
                submitted_forms TEXT,
                references_contacted INTEGER DEFAULT 0,
                interviews_completed INTEGER DEFAULT 0,
                adjudication_status TEXT,
                approval_date TEXT,
                denial_reason TEXT,
                appeals_process TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (clearance_id) REFERENCES personnel_clearances (id)
            )
        """)
        
        # Security incidents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_incidents (
                id TEXT PRIMARY KEY,
                incident_type TEXT NOT NULL,
                incident_date TEXT NOT NULL,
                reported_date TEXT NOT NULL,
                reported_by TEXT NOT NULL,
                employee_id TEXT,
                facility_id TEXT,
                incident_description TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                classification_level_involved TEXT,
                immediate_actions_taken TEXT,
                investigation_required BOOLEAN DEFAULT 0,
                investigation_status TEXT,
                investigation_findings TEXT,
                corrective_actions TEXT,
                disciplinary_actions TEXT,
                security_manager_review TEXT,
                closure_date TEXT,
                lessons_learned TEXT,
                reporting_requirements TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Access control table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_control (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                facility_id TEXT,
                access_level TEXT NOT NULL,
                areas_authorized TEXT,
                systems_authorized TEXT,
                special_access_programs TEXT,
                effective_date TEXT NOT NULL,
                expiration_date TEXT,
                authorization_basis TEXT,
                authorizing_official TEXT,
                access_conditions TEXT,
                monitoring_requirements TEXT,
                review_frequency TEXT,
                last_review_date TEXT,
                next_review_date TEXT,
                access_violations INTEGER DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Security training table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS security_training (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                training_type TEXT NOT NULL,
                training_title TEXT NOT NULL,
                training_date TEXT NOT NULL,
                completion_date TEXT,
                expiration_date TEXT,
                training_provider TEXT,
                certification_number TEXT,
                training_hours REAL DEFAULT 0.0,
                passing_score REAL,
                actual_score REAL,
                status TEXT NOT NULL,
                refresher_required BOOLEAN DEFAULT 0,
                next_training_due TEXT,
                training_materials TEXT,
                instructor_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES personnel_clearances (employee_id)
            )
        """)
        
        # Continuous evaluation table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS continuous_evaluation (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                clearance_id TEXT NOT NULL,
                evaluation_date TEXT NOT NULL,
                evaluation_type TEXT NOT NULL,
                data_sources_checked TEXT,
                issues_identified TEXT,
                risk_indicators TEXT,
                mitigation_actions TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_date TEXT,
                evaluation_result TEXT,
                evaluator_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (clearance_id) REFERENCES personnel_clearances (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_clearance_requirements(self):
        """Setup clearance level requirements and timelines"""
        self.clearance_requirements = {
            ClearanceLevel.PUBLIC_TRUST.value: {
                "investigation_type": InvestigationType.NACLC.value,
                "validity_period": 15,  # years
                "reinvestigation_period": 15,
                "polygraph_required": False,
                "citizenship_required": "US",
                "minimum_age": 18
            },
            ClearanceLevel.SECRET.value: {
                "investigation_type": InvestigationType.MBI.value,
                "validity_period": 10,
                "reinvestigation_period": 10,
                "polygraph_required": False,
                "citizenship_required": "US",
                "minimum_age": 18
            },
            ClearanceLevel.TOP_SECRET.value: {
                "investigation_type": InvestigationType.SSBI.value,
                "validity_period": 5,
                "reinvestigation_period": 5,
                "polygraph_required": False,
                "citizenship_required": "US",
                "minimum_age": 18
            },
            ClearanceLevel.TOP_SECRET_SCI.value: {
                "investigation_type": InvestigationType.SSBI.value,
                "validity_period": 5,
                "reinvestigation_period": 5,
                "polygraph_required": True,
                "citizenship_required": "US",
                "minimum_age": 18
            }
        }

    async def _setup_investigation_timelines(self):
        """Setup typical investigation processing timelines"""
        self.investigation_timelines = {
            InvestigationType.NACLC.value: {"typical_days": 45, "maximum_days": 90},
            InvestigationType.MBI.value: {"typical_days": 120, "maximum_days": 180},
            InvestigationType.BI.value: {"typical_days": 180, "maximum_days": 270},
            InvestigationType.SSBI.value: {"typical_days": 300, "maximum_days": 540},
            InvestigationType.T3.value: {"typical_days": 90, "maximum_days": 150},
            InvestigationType.T5.value: {"typical_days": 240, "maximum_days": 400}
        }

    async def track_clearance(self, employee_id: str, clearance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track security clearance for employee"""
        try:
            clearance_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Validate clearance data
            required_fields = ["first_name", "last_name", "clearance_level", "sponsor_agency"]
            missing_fields = [field for field in required_fields if not clearance_data.get(field)]
            
            if missing_fields:
                return {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            
            # Calculate expiration date based on clearance level
            clearance_level = clearance_data["clearance_level"]
            if clearance_level in self.clearance_requirements:
                validity_period = self.clearance_requirements[clearance_level]["validity_period"]
                effective_date = datetime.fromisoformat(clearance_data.get("effective_date", now))
                expiration_date = (effective_date + timedelta(days=validity_period * 365)).isoformat()
            else:
                expiration_date = None
            
            # Store clearance record
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO personnel_clearances (
                    id, employee_id, first_name, last_name, middle_initial,
                    ssn_last4, date_of_birth, citizenship, clearance_level,
                    clearance_status, sponsor_agency, investigation_type,
                    investigation_opened_date, adjudication_date, effective_date,
                    expiration_date, security_officer, sponsoring_organization,
                    position_sensitivity, polygraph_required, special_access_programs,
                    compartments, interim_clearance, audit_trail, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                clearance_id, employee_id, clearance_data["first_name"],
                clearance_data["last_name"], clearance_data.get("middle_initial"),
                clearance_data.get("ssn_last4"), clearance_data.get("date_of_birth"),
                clearance_data.get("citizenship", "US"), clearance_level,
                clearance_data.get("clearance_status", ClearanceStatus.ACTIVE.value),
                clearance_data["sponsor_agency"],
                clearance_data.get("investigation_type"),
                clearance_data.get("investigation_opened_date"),
                clearance_data.get("adjudication_date"),
                clearance_data.get("effective_date", now), expiration_date,
                clearance_data.get("security_officer"),
                clearance_data.get("sponsoring_organization"),
                clearance_data.get("position_sensitivity"),
                clearance_data.get("polygraph_required", False),
                json.dumps(clearance_data.get("special_access_programs", [])),
                json.dumps(clearance_data.get("compartments", [])),
                clearance_data.get("interim_clearance", False),
                json.dumps([{"action": "clearance_added", "date": now}]),
                now, now
            ))
            
            # Setup access control if specified
            if clearance_data.get("facility_access"):
                await self._setup_access_control(employee_id, clearance_data["facility_access"])
            
            conn.commit()
            conn.close()
            
            # Calculate renewal timeline
            renewal_timeline = await self._calculate_renewal_timeline(clearance_level, expiration_date)
            
            result = {
                "clearance_id": clearance_id,
                "employee_id": employee_id,
                "clearance_level": clearance_level,
                "status": clearance_data.get("clearance_status", ClearanceStatus.ACTIVE.value),
                "effective_date": clearance_data.get("effective_date", now),
                "expiration_date": expiration_date,
                "renewal_timeline": renewal_timeline,
                "next_actions": [
                    "Setup security briefing schedule",
                    "Configure access control systems",
                    "Schedule security training",
                    "Setup continuous monitoring"
                ]
            }
            
            logger.info(f"Security clearance tracked: {clearance_level} for {clearance_data['first_name']} {clearance_data['last_name']}")
            return result
            
        except Exception as e:
            logger.error(f"Error tracking clearance: {e}")
            return {"error": str(e)}

    async def _setup_access_control(self, employee_id: str, facility_access: Dict[str, Any]):
        """Setup access control for employee"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        access_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO access_control (
                id, employee_id, facility_id, access_level, areas_authorized,
                systems_authorized, effective_date, authorization_basis,
                authorizing_official, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            access_id, employee_id, facility_access.get("facility_id"),
            facility_access.get("access_level"), 
            json.dumps(facility_access.get("areas_authorized", [])),
            json.dumps(facility_access.get("systems_authorized", [])),
            now, facility_access.get("authorization_basis"),
            facility_access.get("authorizing_official"), now, now
        ))
        
        conn.commit()
        conn.close()

    async def _calculate_renewal_timeline(self, clearance_level: str, expiration_date: str) -> Dict[str, Any]:
        """Calculate clearance renewal timeline"""
        if not expiration_date or clearance_level not in self.clearance_requirements:
            return {"renewal_required": False}
        
        expiry = datetime.fromisoformat(expiration_date)
        now = datetime.now()
        days_until_expiry = (expiry - now).days
        
        # Renewal should typically start 12-18 months before expiration
        renewal_start_days = min(540, days_until_expiry - 365)
        renewal_start_date = (now + timedelta(days=renewal_start_days)).isoformat()
        
        return {
            "renewal_required": True,
            "days_until_expiry": days_until_expiry,
            "renewal_start_date": renewal_start_date,
            "renewal_urgency": "critical" if days_until_expiry < 180 else "high" if days_until_expiry < 365 else "normal"
        }

    async def get_expiring_clearances(self, days_ahead: int = 90) -> Dict[str, Any]:
        """Get clearances expiring within specified timeframe"""
        try:
            cutoff_date = (datetime.now() + timedelta(days=days_ahead)).isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, employee_id, first_name, last_name, clearance_level,
                       expiration_date, security_officer, sponsoring_organization
                FROM personnel_clearances 
                WHERE expiration_date <= ? AND clearance_status = 'active'
                ORDER BY expiration_date ASC
            """, (cutoff_date,))
            
            expiring_clearances = []
            critical_count = 0
            high_priority_count = 0
            
            for row in cursor.fetchall():
                expiry_date = datetime.fromisoformat(row[5])
                days_until_expiry = (expiry_date - datetime.now()).days
                
                if days_until_expiry <= 30:
                    urgency = "critical"
                    critical_count += 1
                elif days_until_expiry <= 90:
                    urgency = "high"
                    high_priority_count += 1
                else:
                    urgency = "medium"
                
                clearance = {
                    "clearance_id": row[0],
                    "employee_id": row[1],
                    "employee_name": f"{row[2]} {row[3]}",
                    "clearance_level": row[4],
                    "expiration_date": row[5],
                    "days_until_expiry": days_until_expiry,
                    "urgency": urgency,
                    "security_officer": row[6],
                    "sponsoring_organization": row[7],
                    "recommended_actions": self._get_renewal_actions(days_until_expiry)
                }
                expiring_clearances.append(clearance)
            
            conn.close()
            
            return {
                "total_expiring": len(expiring_clearances),
                "critical_count": critical_count,
                "high_priority_count": high_priority_count,
                "timeframe_days": days_ahead,
                "expiring_clearances": expiring_clearances,
                "summary": {
                    "immediate_action_required": critical_count,
                    "renewal_process_start": high_priority_count,
                    "planning_required": len(expiring_clearances) - critical_count - high_priority_count
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting expiring clearances: {e}")
            return {"error": str(e)}

    def _get_renewal_actions(self, days_until_expiry: int) -> List[str]:
        """Get recommended actions based on time until expiry"""
        if days_until_expiry <= 30:
            return [
                "URGENT: Initiate emergency renewal process",
                "Contact security officer immediately",
                "Prepare interim clearance request",
                "Review work assignment restrictions"
            ]
        elif days_until_expiry <= 90:
            return [
                "Begin formal renewal process",
                "Submit SF-86 and supporting forms",
                "Schedule investigative interviews",
                "Notify project managers of timeline"
            ]
        elif days_until_expiry <= 180:
            return [
                "Start renewal planning process",
                "Update personnel security file",
                "Review clearance requirements",
                "Schedule pre-renewal briefing"
            ]
        else:
            return [
                "Monitor for renewal timeline",
                "Maintain security compliance",
                "Update contact information",
                "Complete required training"
            ]

    async def initiate_renewal(self, clearance_id: str, renewal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate clearance renewal process"""
        try:
            renewal_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Get clearance details
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT clearance_level, expiration_date, employee_id 
                FROM personnel_clearances WHERE id = ?
            """, (clearance_id,))
            
            clearance = cursor.fetchone()
            if not clearance:
                return {"error": "Clearance not found"}
            
            clearance_level = clearance[0]
            employee_id = clearance[2]
            
            # Determine investigation type for renewal
            if clearance_level in self.clearance_requirements:
                investigation_type = self._get_renewal_investigation_type(clearance_level)
            else:
                investigation_type = InvestigationType.MBI.value
            
            # Calculate due date based on investigation timeline
            timeline = self.investigation_timelines.get(investigation_type, {"typical_days": 180})
            due_date = (datetime.now() + timedelta(days=timeline["typical_days"])).isoformat()
            
            # Store renewal record
            cursor.execute("""
                INSERT INTO clearance_renewals (
                    id, clearance_id, renewal_type, initiation_date, due_date,
                    status, investigation_type, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                renewal_id, clearance_id, "periodic_reinvestigation", now, due_date,
                "initiated", investigation_type, now, now
            ))
            
            # Update clearance status
            cursor.execute("""
                UPDATE personnel_clearances 
                SET clearance_status = ?, updated_at = ?
                WHERE id = ?
            """, ("renewal_in_progress", now, clearance_id))
            
            conn.commit()
            conn.close()
            
            # Generate renewal checklist
            checklist = await self._generate_renewal_checklist(clearance_level, investigation_type)
            
            result = {
                "renewal_id": renewal_id,
                "clearance_id": clearance_id,
                "employee_id": employee_id,
                "renewal_type": "periodic_reinvestigation",
                "investigation_type": investigation_type,
                "initiation_date": now,
                "estimated_completion": due_date,
                "status": "initiated",
                "required_forms": self._get_required_forms(investigation_type),
                "renewal_checklist": checklist,
                "next_steps": [
                    "Complete and submit SF-86 form",
                    "Provide updated contact information",
                    "Schedule fingerprinting appointment",
                    "Notify references of potential contact"
                ]
            }
            
            logger.info(f"Clearance renewal initiated: {renewal_id} for {clearance_level}")
            return result
            
        except Exception as e:
            logger.error(f"Error initiating renewal: {e}")
            return {"error": str(e)}

    def _get_renewal_investigation_type(self, clearance_level: str) -> str:
        """Get appropriate investigation type for renewal"""
        renewal_mapping = {
            ClearanceLevel.PUBLIC_TRUST.value: InvestigationType.NACLC.value,
            ClearanceLevel.SECRET.value: InvestigationType.MBI.value,
            ClearanceLevel.TOP_SECRET.value: InvestigationType.SSBI_PR.value,
            ClearanceLevel.TOP_SECRET_SCI.value: InvestigationType.SSBI_PR.value
        }
        return renewal_mapping.get(clearance_level, InvestigationType.MBI.value)

    def _get_required_forms(self, investigation_type: str) -> List[str]:
        """Get required forms for investigation type"""
        form_mapping = {
            InvestigationType.NACLC.value: ["SF-85", "FD-258"],
            InvestigationType.MBI.value: ["SF-86", "FD-258", "SF-87"],
            InvestigationType.SSBI.value: ["SF-86", "FD-258", "SF-87", "SF-312"],
            InvestigationType.SSBI_PR.value: ["SF-86", "FD-258", "SF-87"]
        }
        return form_mapping.get(investigation_type, ["SF-86", "FD-258"])

    async def _generate_renewal_checklist(self, clearance_level: str, investigation_type: str) -> List[Dict[str, Any]]:
        """Generate comprehensive renewal checklist"""
        checklist = [
            {
                "item": "Complete SF-86 Security Clearance Application",
                "status": "pending",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "priority": "high"
            },
            {
                "item": "Submit fingerprints (FD-258)",
                "status": "pending", 
                "due_date": (datetime.now() + timedelta(days=21)).isoformat(),
                "priority": "high"
            },
            {
                "item": "Provide updated employment history",
                "status": "pending",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "priority": "medium"
            },
            {
                "item": "Update residence history for past 10 years",
                "status": "pending",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "priority": "medium"
            },
            {
                "item": "Provide updated reference contacts",
                "status": "pending",
                "due_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "priority": "medium"
            }
        ]
        
        # Add clearance-specific requirements
        if clearance_level in [ClearanceLevel.TOP_SECRET.value, ClearanceLevel.TOP_SECRET_SCI.value]:
            checklist.extend([
                {
                    "item": "Schedule polygraph examination",
                    "status": "pending",
                    "due_date": (datetime.now() + timedelta(days=45)).isoformat(),
                    "priority": "high"
                },
                {
                    "item": "Complete financial disclosure",
                    "status": "pending",
                    "due_date": (datetime.now() + timedelta(days=21)).isoformat(),
                    "priority": "medium"
                }
            ])
        
        return checklist

    async def track_facility_security(self, facility_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track facility security clearance"""
        try:
            facility_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Store facility clearance
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO facility_clearances (
                    id, facility_name, facility_address, facility_code,
                    clearance_level, status, sponsoring_agency,
                    cognizant_security_office, facility_security_officer,
                    effective_date, next_inspection_date, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                facility_id, facility_data["facility_name"],
                facility_data.get("facility_address"), facility_data.get("facility_code"),
                facility_data["clearance_level"], 
                facility_data.get("status", "active"),
                facility_data["sponsoring_agency"],
                facility_data.get("cognizant_security_office"),
                facility_data.get("facility_security_officer"),
                facility_data.get("effective_date", now),
                facility_data.get("next_inspection_date"), now, now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "facility_id": facility_id,
                "facility_name": facility_data["facility_name"],
                "clearance_level": facility_data["clearance_level"],
                "status": facility_data.get("status", "active"),
                "effective_date": facility_data.get("effective_date", now)
            }
            
        except Exception as e:
            logger.error(f"Error tracking facility security: {e}")
            return {"error": str(e)}

    async def generate_security_report(self, report_type: str = "comprehensive") -> Dict[str, Any]:
        """Generate comprehensive security report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get personnel clearance statistics
            cursor.execute("""
                SELECT clearance_level, clearance_status, COUNT(*) as count
                FROM personnel_clearances
                GROUP BY clearance_level, clearance_status
            """)
            
            clearance_stats = {}
            for row in cursor.fetchall():
                level = row[0]
                status = row[1]
                count = row[2]
                
                if level not in clearance_stats:
                    clearance_stats[level] = {}
                clearance_stats[level][status] = count
            
            # Get expiring clearances summary
            thirty_days = (datetime.now() + timedelta(days=30)).isoformat()
            ninety_days = (datetime.now() + timedelta(days=90)).isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM personnel_clearances 
                WHERE expiration_date <= ? AND clearance_status = 'active'
            """, (thirty_days,))
            expiring_30 = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM personnel_clearances 
                WHERE expiration_date <= ? AND clearance_status = 'active'
            """, (ninety_days,))
            expiring_90 = cursor.fetchone()[0]
            
            # Get security incidents summary
            cursor.execute("""
                SELECT severity_level, COUNT(*) as count
                FROM security_incidents
                WHERE incident_date >= date('now', '-1 year')
                GROUP BY severity_level
            """)
            
            incident_stats = {}
            for row in cursor.fetchall():
                incident_stats[row[0]] = row[1]
            
            # Get training compliance
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM security_training
                WHERE expiration_date >= date('now')
                GROUP BY status
            """)
            
            training_stats = {}
            for row in cursor.fetchall():
                training_stats[row[0]] = row[1]
            
            conn.close()
            
            return {
                "report_type": report_type,
                "report_date": datetime.now().isoformat(),
                "clearance_statistics": clearance_stats,
                "expiring_clearances": {
                    "within_30_days": expiring_30,
                    "within_90_days": expiring_90,
                    "urgency_level": "critical" if expiring_30 > 0 else "high" if expiring_90 > 5 else "normal"
                },
                "security_incidents": {
                    "past_year_summary": incident_stats,
                    "total_incidents": sum(incident_stats.values())
                },
                "training_compliance": training_stats,
                "recommendations": [
                    "Monitor expiring clearances closely",
                    "Ensure timely renewal processes",
                    "Maintain security training compliance",
                    "Review incident trends for patterns",
                    "Update security procedures as needed"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error generating security report: {e}")
            return {"error": str(e)}

    async def record_security_incident(self, incident_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record security incident"""
        try:
            incident_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO security_incidents (
                    id, incident_type, incident_date, reported_date, reported_by,
                    employee_id, facility_id, incident_description, severity_level,
                    classification_level_involved, immediate_actions_taken,
                    investigation_required, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                incident_id, incident_data["incident_type"],
                incident_data["incident_date"], now, incident_data["reported_by"],
                incident_data.get("employee_id"), incident_data.get("facility_id"),
                incident_data["incident_description"], incident_data["severity_level"],
                incident_data.get("classification_level_involved"),
                incident_data.get("immediate_actions_taken"),
                incident_data.get("investigation_required", False), now, now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "incident_id": incident_id,
                "incident_type": incident_data["incident_type"],
                "severity_level": incident_data["severity_level"],
                "reported_date": now,
                "next_actions": [
                    "Notify security management",
                    "Conduct preliminary assessment",
                    "Document all actions taken",
                    "Determine investigation requirements"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error recording security incident: {e}")
            return {"error": str(e)}

# Global instance
clearance_system = SecurityClearanceSystem()