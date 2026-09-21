#!/usr/bin/env python3
"""
Small Business Certifications Management System
Comprehensive small business certification tracking and management
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

class CertificationType(Enum):
    SMALL_BUSINESS = "small_business"
    SMALL_DISADVANTAGED = "small_disadvantaged_business"
    WOMAN_OWNED = "woman_owned_small_business"
    VETERAN_OWNED = "veteran_owned_small_business"
    SERVICE_DISABLED_VETERAN = "service_disabled_veteran_owned"
    HUBZONE = "hubzone_small_business"
    HISTORICALLY_BLACK = "historically_black_college_university"
    NATIVE_AMERICAN = "native_american_owned"
    ECONOMICALLY_DISADVANTAGED = "economically_disadvantaged_wosb"
    SMALL_BUSINESS_INNOVATION = "small_business_innovation_research"

class CertificationStatus(Enum):
    ACTIVE = "active"
    PENDING = "pending"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    DENIED = "denied"
    UNDER_REVIEW = "under_review"

class ApplicationStatus(Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    ADDITIONAL_INFO_REQUIRED = "additional_info_required"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"

class SetAsideType(Enum):
    SMALL_BUSINESS = "small_business_set_aside"
    SDB = "small_disadvantaged_business"
    WOSB = "women_owned_small_business"
    EDWOSB = "economically_disadvantaged_wosb"
    VOSB = "veteran_owned_small_business"
    SDVOSB = "service_disabled_veteran_owned"
    HUBZONE = "hubzone_set_aside"
    HBCU = "historically_black_college_university"

class SmallBusinessCertificationSystem:
    def __init__(self):
        self.db_path = "data/small_business_certs.db"
        self.certification_requirements = {}
        self.set_aside_preferences = {}

    async def initialize(self):
        """Initialize small business certification system"""
        try:
            await self._create_database_schema()
            await self._setup_certification_requirements()
            await self._setup_set_aside_preferences()
            logger.info("Small Business Certification System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Small Business Certification System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for small business certifications"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Certifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certifications (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                duns_number TEXT,
                cage_code TEXT,
                certification_type TEXT NOT NULL,
                certification_number TEXT,
                certifying_agency TEXT NOT NULL,
                application_date TEXT,
                certification_date TEXT,
                expiration_date TEXT,
                status TEXT NOT NULL,
                annual_receipts REAL,
                employee_count INTEGER,
                naics_code TEXT,
                primary_industry TEXT,
                ownership_percentage REAL,
                control_percentage REAL,
                eligibility_documentation TEXT,
                supporting_documents TEXT,
                renewal_required BOOLEAN DEFAULT 1,
                next_renewal_date TEXT,
                compliance_requirements TEXT,
                benefits_claimed TEXT,
                set_aside_eligibility TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Certification applications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS certification_applications (
                id TEXT PRIMARY KEY,
                certification_id TEXT,
                application_type TEXT NOT NULL,
                certification_type TEXT NOT NULL,
                applicant_name TEXT NOT NULL,
                business_name TEXT NOT NULL,
                application_date TEXT NOT NULL,
                submission_date TEXT,
                review_start_date TEXT,
                decision_date TEXT,
                status TEXT NOT NULL,
                reviewer_name TEXT,
                reviewer_agency TEXT,
                documentation_submitted TEXT,
                additional_info_requests TEXT,
                decision_rationale TEXT,
                appeal_deadline TEXT,
                appeal_submitted BOOLEAN DEFAULT 0,
                processing_time_days INTEGER,
                fees_paid REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Annual certifications table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS annual_certifications (
                id TEXT PRIMARY KEY,
                certification_id TEXT NOT NULL,
                reporting_year INTEGER NOT NULL,
                annual_receipts REAL NOT NULL,
                employee_count INTEGER NOT NULL,
                naics_codes TEXT,
                ownership_changes TEXT,
                control_changes TEXT,
                size_standard_met BOOLEAN DEFAULT 1,
                eligibility_maintained BOOLEAN DEFAULT 1,
                compliance_issues TEXT,
                corrective_actions TEXT,
                certification_date TEXT NOT NULL,
                expiration_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (certification_id) REFERENCES certifications (id)
            )
        """)
        
        # Set-aside tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS set_aside_tracking (
                id TEXT PRIMARY KEY,
                certification_id TEXT NOT NULL,
                contract_number TEXT NOT NULL,
                solicitation_number TEXT,
                set_aside_type TEXT NOT NULL,
                contract_value REAL NOT NULL,
                award_date TEXT,
                performance_period_start TEXT,
                performance_period_end TEXT,
                prime_or_sub TEXT DEFAULT 'prime',
                subcontract_percentage REAL,
                performance_goals_met BOOLEAN DEFAULT 1,
                benefits_realized REAL DEFAULT 0.0,
                reporting_requirements TEXT,
                compliance_status TEXT DEFAULT 'compliant',
                created_at TEXT NOT NULL,
                FOREIGN KEY (certification_id) REFERENCES certifications (id)
            )
        """)
        
        # Compliance monitoring table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_monitoring (
                id TEXT PRIMARY KEY,
                certification_id TEXT NOT NULL,
                monitoring_date TEXT NOT NULL,
                compliance_area TEXT NOT NULL,
                requirement_description TEXT NOT NULL,
                compliance_status TEXT NOT NULL,
                evidence_reviewed TEXT,
                findings TEXT,
                corrective_actions_required TEXT,
                corrective_actions_taken TEXT,
                completion_date TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_date TEXT,
                monitor_name TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (certification_id) REFERENCES certifications (id)
            )
        """)
        
        # Renewal tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS renewal_tracking (
                id TEXT PRIMARY KEY,
                certification_id TEXT NOT NULL,
                renewal_type TEXT NOT NULL,
                current_expiration_date TEXT NOT NULL,
                renewal_due_date TEXT NOT NULL,
                renewal_submitted_date TEXT,
                renewal_approved_date TEXT,
                new_expiration_date TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                documentation_submitted TEXT,
                review_process_status TEXT,
                reviewer_feedback TEXT,
                additional_requirements TEXT,
                fees_required REAL DEFAULT 0.0,
                fees_paid REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (certification_id) REFERENCES certifications (id)
            )
        """)
        
        # Benefits tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS benefits_tracking (
                id TEXT PRIMARY KEY,
                certification_id TEXT NOT NULL,
                benefit_type TEXT NOT NULL,
                program_name TEXT,
                benefit_description TEXT NOT NULL,
                eligibility_start_date TEXT,
                eligibility_end_date TEXT,
                benefit_value REAL DEFAULT 0.0,
                utilization_count INTEGER DEFAULT 0,
                last_utilized_date TEXT,
                terms_conditions TEXT,
                reporting_requirements TEXT,
                compliance_obligations TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (certification_id) REFERENCES certifications (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_certification_requirements(self):
        """Setup certification requirements and criteria"""
        self.certification_requirements = {
            CertificationType.SMALL_BUSINESS.value: {
                "size_standards": "Varies by NAICS code",
                "ownership_requirement": "51% owned by US citizens or permanent residents",
                "control_requirement": "Day-to-day control by qualifying individuals",
                "independence_requirement": "Independently owned and operated",
                "documentation": ["Tax returns", "Financial statements", "Organizational documents"],
                "renewal_period": 365,  # days
                "certifying_agency": "SBA"
            },
            CertificationType.SMALL_DISADVANTAGED.value: {
                "size_standards": "Must meet small business size standards",
                "ownership_requirement": "51% owned by socially and economically disadvantaged individuals",
                "personal_net_worth": "$750,000 excluding primary residence and business equity",
                "documentation": ["Personal financial statement", "Tax returns", "Birth certificates"],
                "renewal_period": 1095,  # 3 years
                "certifying_agency": "SBA"
            },
            CertificationType.WOMAN_OWNED.value: {
                "size_standards": "Must meet small business size standards",
                "ownership_requirement": "51% owned by one or more women",
                "control_requirement": "Day-to-day control by qualifying women",
                "documentation": ["Birth certificates", "Organizational documents", "Financial records"],
                "renewal_period": 365,
                "certifying_agency": "SBA or Third-party certifier"
            },
            CertificationType.VETERAN_OWNED.value: {
                "size_standards": "Must meet small business size standards", 
                "ownership_requirement": "51% owned by one or more veterans",
                "control_requirement": "Day-to-day control by qualifying veterans",
                "documentation": ["DD-214", "Organizational documents", "Financial records"],
                "renewal_period": 365,
                "certifying_agency": "VA or SBA"
            },
            CertificationType.SERVICE_DISABLED_VETERAN.value: {
                "size_standards": "Must meet small business size standards",
                "ownership_requirement": "51% owned by service-disabled veterans",
                "control_requirement": "Day-to-day control by service-disabled veterans",
                "disability_requirement": "Service-connected disability rating",
                "documentation": ["VA disability letter", "DD-214", "Medical records"],
                "renewal_period": 365,
                "certifying_agency": "VA"
            },
            CertificationType.HUBZONE.value: {
                "size_standards": "Must meet small business size standards",
                "location_requirement": "Principal office in HUBZone area",
                "employee_requirement": "35% of employees reside in HUBZone",
                "ownership_requirement": "51% owned by US citizens",
                "documentation": ["Employee residence verification", "Lease agreements", "Payroll records"],
                "renewal_period": 1095,  # 3 years
                "certifying_agency": "SBA"
            }
        }

    async def _setup_set_aside_preferences(self):
        """Setup set-aside preferences and benefits"""
        self.set_aside_preferences = {
            SetAsideType.SMALL_BUSINESS.value: {
                "preference_percentage": 0,
                "sole_source_threshold": 4000000,  # For manufacturing
                "competitive_threshold": 7000000,
                "subcontracting_credit": True,
                "mentor_protege_eligible": True
            },
            SetAsideType.SDB.value: {
                "preference_percentage": 10,  # Price evaluation adjustment
                "sole_source_threshold": 4000000,
                "competitive_threshold": 7000000,
                "subcontracting_credit": True,
                "joint_venture_eligible": True
            },
            SetAsideType.WOSB.value: {
                "preference_percentage": 0,
                "sole_source_threshold": 4000000,
                "competitive_threshold": 7000000,
                "industry_focus": ["NAICS codes under-represented by women"],
                "subcontracting_credit": True
            },
            SetAsideType.HUBZONE.value: {
                "preference_percentage": 10,
                "sole_source_threshold": 7000000,
                "competitive_threshold": 7000000,
                "price_evaluation_preference": True,
                "subcontracting_credit": True
            }
        }

    async def apply_certification(self, certification_type: str, 
                                 application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply for small business certification"""
        try:
            application_id = str(uuid.uuid4())
            certification_id = str(uuid.uuid4()) if application_data.get("new_certification") else application_data.get("certification_id")
            now = datetime.now().isoformat()
            
            # Validate application data
            required_fields = ["applicant_name", "business_name", "duns_number"]
            missing_fields = [field for field in required_fields if not application_data.get(field)]
            
            if missing_fields:
                return {"error": f"Missing required fields: {', '.join(missing_fields)}"}
            
            # Check eligibility prerequisites
            eligibility_check = await self._check_eligibility(certification_type, application_data)
            if not eligibility_check["eligible"]:
                return {
                    "error": "Eligibility requirements not met",
                    "issues": eligibility_check["issues"]
                }
            
            # Store application
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO certification_applications (
                    id, certification_id, application_type, certification_type,
                    applicant_name, business_name, application_date, status,
                    documentation_submitted, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                application_id, certification_id, "new_application", certification_type,
                application_data["applicant_name"], application_data["business_name"],
                now, ApplicationStatus.DRAFT.value,
                json.dumps(application_data.get("documentation", [])), now, now
            ))
            
            # Create certification record if new
            if application_data.get("new_certification"):
                cursor.execute("""
                    INSERT INTO certifications (
                        id, company_name, duns_number, cage_code, certification_type,
                        certifying_agency, annual_receipts, employee_count,
                        naics_code, status, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    certification_id, application_data["business_name"],
                    application_data["duns_number"], application_data.get("cage_code"),
                    certification_type, self.certification_requirements[certification_type]["certifying_agency"],
                    application_data.get("annual_receipts", 0),
                    application_data.get("employee_count", 0),
                    application_data.get("naics_code"),
                    CertificationStatus.PENDING.value, now, now
                ))
            
            # Generate application checklist
            checklist = await self._generate_application_checklist(certification_type)
            
            # Calculate estimated processing time
            processing_estimate = await self._estimate_processing_time(certification_type)
            
            conn.commit()
            conn.close()
            
            result = {
                "application_id": application_id,
                "certification_id": certification_id,
                "certification_type": certification_type,
                "application_status": ApplicationStatus.DRAFT.value,
                "application_date": now,
                "eligibility_check": eligibility_check,
                "required_documentation": checklist["documentation"],
                "application_checklist": checklist["checklist"],
                "estimated_processing_time": processing_estimate,
                "next_steps": [
                    "Complete all required documentation",
                    "Submit application to certifying agency",
                    "Respond to any additional information requests",
                    "Monitor application status regularly"
                ]
            }
            
            logger.info(f"Certification application created: {certification_type} for {application_data['business_name']}")
            return result
            
        except Exception as e:
            logger.error(f"Error applying for certification: {e}")
            return {"error": str(e)}

    async def _check_eligibility(self, certification_type: str, 
                                application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check eligibility for certification type"""
        eligibility_issues = []
        
        if certification_type not in self.certification_requirements:
            return {"eligible": False, "issues": ["Unknown certification type"]}
        
        requirements = self.certification_requirements[certification_type]
        
        # Check size standards (simplified check)
        annual_receipts = application_data.get("annual_receipts", 0)
        employee_count = application_data.get("employee_count", 0)
        
        # Basic size standard check (would need NAICS-specific rules in production)
        if annual_receipts > 50000000:  # $50M threshold for many service industries
            eligibility_issues.append("Annual receipts may exceed size standards")
        
        if employee_count > 500:  # 500 employee threshold for many industries
            eligibility_issues.append("Employee count may exceed size standards")
        
        # Check ownership requirements (basic validation)
        ownership_percentage = application_data.get("ownership_percentage", 0)
        if ownership_percentage < 51:
            eligibility_issues.append("Must have at least 51% qualifying ownership")
        
        # Certification-specific checks
        if certification_type == CertificationType.HUBZONE.value:
            hubzone_location = application_data.get("hubzone_location", False)
            if not hubzone_location:
                eligibility_issues.append("Business must be located in qualified HUBZone area")
        
        if certification_type == CertificationType.SERVICE_DISABLED_VETERAN.value:
            disability_rating = application_data.get("disability_rating", 0)
            if disability_rating < 10:
                eligibility_issues.append("Must have service-connected disability rating")
        
        return {
            "eligible": len(eligibility_issues) == 0,
            "issues": eligibility_issues,
            "recommendations": self._generate_eligibility_recommendations(eligibility_issues)
        }

    def _generate_eligibility_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations to address eligibility issues"""
        recommendations = []
        
        for issue in issues:
            if "size standards" in issue.lower():
                recommendations.append("Review NAICS code size standards and consider business restructuring")
            elif "ownership" in issue.lower():
                recommendations.append("Review ownership structure and consider ownership transfers")
            elif "hubzone" in issue.lower():
                recommendations.append("Verify HUBZone area qualification or consider office relocation")
            elif "disability" in issue.lower():
                recommendations.append("Obtain updated VA disability rating documentation")
        
        if not recommendations:
            recommendations.append("Continue with application process - all basic requirements appear to be met")
        
        return recommendations

    async def _generate_application_checklist(self, certification_type: str) -> Dict[str, Any]:
        """Generate application checklist for certification type"""
        if certification_type not in self.certification_requirements:
            return {"documentation": [], "checklist": []}
        
        requirements = self.certification_requirements[certification_type]
        
        checklist_items = [
            {
                "item": "Complete application form",
                "required": True,
                "status": "pending",
                "description": "Submit completed certification application"
            },
            {
                "item": "Business registration documents",
                "required": True,
                "status": "pending",
                "description": "Articles of incorporation, bylaws, operating agreements"
            },
            {
                "item": "Financial documentation",
                "required": True,
                "status": "pending", 
                "description": "Tax returns, financial statements, banking records"
            },
            {
                "item": "Ownership documentation",
                "required": True,
                "status": "pending",
                "description": "Stock certificates, membership certificates, ownership agreements"
            }
        ]
        
        # Add certification-specific requirements
        if certification_type == CertificationType.WOMAN_OWNED.value:
            checklist_items.append({
                "item": "Birth certificates of female owners",
                "required": True,
                "status": "pending",
                "description": "Birth certificates proving gender of qualifying owners"
            })
        
        if certification_type == CertificationType.VETERAN_OWNED.value:
            checklist_items.append({
                "item": "Military service records (DD-214)",
                "required": True,
                "status": "pending",
                "description": "Discharge papers proving veteran status"
            })
        
        if certification_type == CertificationType.HUBZONE.value:
            checklist_items.extend([
                {
                    "item": "Employee residence verification",
                    "required": True,
                    "status": "pending",
                    "description": "Documentation proving 35% of employees live in HUBZone"
                },
                {
                    "item": "Principal office location proof",
                    "required": True,
                    "status": "pending",
                    "description": "Lease agreement or property deed for HUBZone location"
                }
            ])
        
        return {
            "documentation": requirements.get("documentation", []),
            "checklist": checklist_items,
            "estimated_completion_time": "2-4 weeks"
        }

    async def _estimate_processing_time(self, certification_type: str) -> Dict[str, Any]:
        """Estimate processing time for certification"""
        processing_times = {
            CertificationType.SMALL_BUSINESS.value: {"days": 30, "description": "30 days from complete application"},
            CertificationType.SMALL_DISADVANTAGED.value: {"days": 90, "description": "90 days for initial review"},
            CertificationType.WOMAN_OWNED.value: {"days": 45, "description": "45 days for third-party certification"},
            CertificationType.VETERAN_OWNED.value: {"days": 30, "description": "30 days from complete application"},
            CertificationType.SERVICE_DISABLED_VETERAN.value: {"days": 45, "description": "45 days including VA verification"},
            CertificationType.HUBZONE.value: {"days": 60, "description": "60 days including location verification"}
        }
        
        return processing_times.get(certification_type, {"days": 45, "description": "45 days typical processing time"})

    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive certification status"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get certification summary
            cursor.execute("""
                SELECT certification_type, status, COUNT(*) as count
                FROM certifications
                GROUP BY certification_type, status
            """)
            
            certification_summary = {}
            for row in cursor.fetchall():
                cert_type = row[0]
                status = row[1]
                count = row[2]
                
                if cert_type not in certification_summary:
                    certification_summary[cert_type] = {}
                certification_summary[cert_type][status] = count
            
            # Get expiring certifications
            thirty_days_ahead = (datetime.now() + timedelta(days=30)).isoformat()
            ninety_days_ahead = (datetime.now() + timedelta(days=90)).isoformat()
            
            cursor.execute("""
                SELECT COUNT(*) FROM certifications 
                WHERE expiration_date BETWEEN ? AND ?
                AND status = 'active'
            """, (datetime.now().isoformat(), thirty_days_ahead))
            expiring_30_days = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM certifications 
                WHERE expiration_date BETWEEN ? AND ?
                AND status = 'active'
            """, (datetime.now().isoformat(), ninety_days_ahead))
            expiring_90_days = cursor.fetchone()[0]
            
            # Get recent applications
            cursor.execute("""
                SELECT certification_type, status, COUNT(*) as count
                FROM certification_applications
                WHERE application_date >= date('now', '-30 days')
                GROUP BY certification_type, status
            """)
            
            recent_applications = {}
            for row in cursor.fetchall():
                cert_type = row[0]
                status = row[1]
                count = row[2]
                
                if cert_type not in recent_applications:
                    recent_applications[cert_type] = {}
                recent_applications[cert_type][status] = count
            
            # Get set-aside utilization
            cursor.execute("""
                SELECT set_aside_type, SUM(contract_value) as total_value, COUNT(*) as count
                FROM set_aside_tracking
                WHERE award_date >= date('now', '-1 year')
                GROUP BY set_aside_type
            """, )
            
            set_aside_utilization = {}
            for row in cursor.fetchall():
                set_aside_utilization[row[0]] = {
                    "total_value": row[1] or 0,
                    "contract_count": row[2]
                }
            
            conn.close()
            
            return {
                "status_date": datetime.now().isoformat(),
                "certification_summary": certification_summary,
                "expiring_certifications": {
                    "within_30_days": expiring_30_days,
                    "within_90_days": expiring_90_days,
                    "urgency_level": "critical" if expiring_30_days > 0 else "medium" if expiring_90_days > 0 else "low"
                },
                "recent_applications": recent_applications,
                "set_aside_utilization": set_aside_utilization,
                "action_items": await self._generate_action_items(expiring_30_days, expiring_90_days),
                "recommendations": [
                    "Monitor certification expiration dates closely",
                    "Begin renewal process 90 days before expiration",
                    "Maintain compliance with all certification requirements",
                    "Maximize utilization of set-aside opportunities"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error getting certification status: {e}")
            return {"error": str(e)}

    async def _generate_action_items(self, expiring_30: int, expiring_90: int) -> List[str]:
        """Generate action items based on certification status"""
        action_items = []
        
        if expiring_30 > 0:
            action_items.append(f"URGENT: {expiring_30} certification(s) expiring within 30 days")
        
        if expiring_90 > 0:
            action_items.append(f"Begin renewal process for {expiring_90} certification(s) expiring within 90 days")
        
        action_items.extend([
            "Review annual certification requirements",
            "Update business size standards compliance",
            "Maintain accurate ownership documentation",
            "Monitor set-aside opportunity pipeline"
        ])
        
        return action_items

    async def renew_certification(self, cert_id: str, renewal_data: Dict[str, Any]) -> Dict[str, Any]:
        """Renew existing certification"""
        try:
            renewal_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Get current certification
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT certification_type, expiration_date, status 
                FROM certifications WHERE id = ?
            """, (cert_id,))
            
            certification = cursor.fetchone()
            if not certification:
                return {"error": "Certification not found"}
            
            certification_type = certification[0]
            current_expiration = certification[1]
            
            # Check if renewal is needed
            if current_expiration:
                expiry_date = datetime.fromisoformat(current_expiration)
                days_until_expiry = (expiry_date - datetime.now()).days
                
                if days_until_expiry > 90:
                    return {
                        "warning": f"Certification not due for renewal for {days_until_expiry} days",
                        "early_renewal_allowed": True
                    }
            
            # Calculate new expiration date
            renewal_period = self.certification_requirements[certification_type]["renewal_period"]
            new_expiration = (datetime.now() + timedelta(days=renewal_period)).isoformat()
            
            # Create renewal record
            cursor.execute("""
                INSERT INTO renewal_tracking (
                    id, certification_id, renewal_type, current_expiration_date,
                    renewal_due_date, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                renewal_id, cert_id, "standard_renewal", current_expiration,
                new_expiration, "pending", now, now
            ))
            
            # Generate renewal checklist
            renewal_checklist = await self._generate_renewal_checklist(certification_type)
            
            # Update certification status
            cursor.execute("""
                UPDATE certifications 
                SET status = 'under_review', updated_at = ?
                WHERE id = ?
            """, (now, cert_id))
            
            conn.commit()
            conn.close()
            
            result = {
                "renewal_id": renewal_id,
                "certification_id": cert_id,
                "certification_type": certification_type,
                "renewal_status": "initiated",
                "current_expiration": current_expiration,
                "proposed_new_expiration": new_expiration,
                "renewal_checklist": renewal_checklist,
                "required_documentation": await self._get_renewal_documentation(certification_type),
                "estimated_processing_time": "30-45 days",
                "next_steps": [
                    "Submit updated financial documentation",
                    "Confirm continued eligibility",
                    "Submit renewal application",
                    "Pay required renewal fees"
                ]
            }
            
            logger.info(f"Certification renewal initiated: {renewal_id} for {certification_type}")
            return result
            
        except Exception as e:
            logger.error(f"Error renewing certification: {e}")
            return {"error": str(e)}

    async def _generate_renewal_checklist(self, certification_type: str) -> List[Dict[str, Any]]:
        """Generate renewal checklist"""
        base_checklist = [
            {
                "item": "Current financial statements",
                "required": True,
                "description": "Most recent tax returns and financial statements"
            },
            {
                "item": "Updated organizational documents",
                "required": True,
                "description": "Current bylaws, operating agreements, etc."
            },
            {
                "item": "Size standards compliance verification",
                "required": True,
                "description": "Confirmation business still meets size requirements"
            },
            {
                "item": "Ownership verification",
                "required": True,
                "description": "Current ownership structure documentation"
            }
        ]
        
        # Add certification-specific renewal requirements
        if certification_type == CertificationType.HUBZONE.value:
            base_checklist.extend([
                {
                    "item": "Employee residence verification",
                    "required": True,
                    "description": "Updated proof that 35% of employees live in HUBZone"
                },
                {
                    "item": "Principal office location confirmation",
                    "required": True,
                    "description": "Confirmation business maintains HUBZone location"
                }
            ])
        
        if certification_type == CertificationType.SMALL_DISADVANTAGED.value:
            base_checklist.append({
                "item": "Updated personal financial statements",
                "required": True,
                "description": "Current personal financial information for qualifying owners"
            })
        
        return base_checklist

    async def _get_renewal_documentation(self, certification_type: str) -> List[str]:
        """Get required documentation for renewal"""
        if certification_type not in self.certification_requirements:
            return []
        
        base_docs = [
            "Renewal application form",
            "Current tax returns (3 years)",
            "Current financial statements",
            "Updated organizational documents"
        ]
        
        specific_docs = self.certification_requirements[certification_type].get("documentation", [])
        return base_docs + specific_docs

    async def track_set_aside_utilization(self, cert_id: str, 
                                        contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Track set-aside contract utilization"""
        try:
            tracking_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO set_aside_tracking (
                    id, certification_id, contract_number, solicitation_number,
                    set_aside_type, contract_value, award_date,
                    performance_period_start, performance_period_end,
                    prime_or_sub, subcontract_percentage, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tracking_id, cert_id, contract_data["contract_number"],
                contract_data.get("solicitation_number"),
                contract_data["set_aside_type"], contract_data["contract_value"],
                contract_data.get("award_date", now),
                contract_data.get("performance_period_start"),
                contract_data.get("performance_period_end"),
                contract_data.get("prime_or_sub", "prime"),
                contract_data.get("subcontract_percentage", 0), now
            ))
            
            conn.commit()
            conn.close()
            
            # Calculate benefits realized
            benefits = await self._calculate_set_aside_benefits(contract_data)
            
            return {
                "tracking_id": tracking_id,
                "certification_id": cert_id,
                "contract_number": contract_data["contract_number"],
                "set_aside_type": contract_data["set_aside_type"],
                "contract_value": contract_data["contract_value"],
                "estimated_benefits": benefits,
                "reporting_requirements": await self._get_set_aside_reporting_requirements(
                    contract_data["set_aside_type"]
                )
            }
            
        except Exception as e:
            logger.error(f"Error tracking set-aside utilization: {e}")
            return {"error": str(e)}

    async def _calculate_set_aside_benefits(self, contract_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate benefits from set-aside contract"""
        contract_value = contract_data["contract_value"]
        set_aside_type = contract_data["set_aside_type"]
        
        benefits = {
            "direct_contract_value": contract_value,
            "competitive_advantage": "Set-aside competition only",
            "subcontracting_credit": False,
            "mentor_protege_eligible": False
        }
        
        if set_aside_type in self.set_aside_preferences:
            preferences = self.set_aside_preferences[set_aside_type]
            benefits["subcontracting_credit"] = preferences.get("subcontracting_credit", False)
            benefits["mentor_protege_eligible"] = preferences.get("mentor_protege_eligible", False)
            
            if preferences.get("preference_percentage", 0) > 0:
                benefits["price_evaluation_benefit"] = f"{preferences['preference_percentage']}% price adjustment"
        
        return benefits

    async def _get_set_aside_reporting_requirements(self, set_aside_type: str) -> List[str]:
        """Get reporting requirements for set-aside type"""
        base_requirements = [
            "Quarterly progress reports",
            "Annual small business certification",
            "Subcontracting plan compliance (if applicable)"
        ]
        
        specific_requirements = {
            SetAsideType.SDB.value: ["SDB utilization reporting", "Mentor-protégé program reporting"],
            SetAsideType.HUBZONE.value: ["HUBZone employee residency reporting", "Principal office location confirmation"],
            SetAsideType.WOSB.value: ["Women-owned business status confirmation"],
            SetAsideType.SDVOSB.value: ["Service-disabled veteran status confirmation"]
        }
        
        return base_requirements + specific_requirements.get(set_aside_type, [])

    async def generate_compliance_report(self, cert_id: str) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get certification details
            cursor.execute("""
                SELECT certification_type, status, certification_date, expiration_date,
                       company_name, annual_receipts, employee_count
                FROM certifications WHERE id = ?
            """, (cert_id,))
            
            cert = cursor.fetchone()
            if not cert:
                return {"error": "Certification not found"}
            
            # Get compliance monitoring records
            cursor.execute("""
                SELECT compliance_area, compliance_status, monitoring_date,
                       findings, corrective_actions_taken
                FROM compliance_monitoring 
                WHERE certification_id = ?
                ORDER BY monitoring_date DESC
            """, (cert_id,))
            
            compliance_records = []
            for row in cursor.fetchall():
                compliance_records.append({
                    "area": row[0],
                    "status": row[1],
                    "date": row[2],
                    "findings": row[3],
                    "corrective_actions": row[4]
                })
            
            # Get set-aside utilization
            cursor.execute("""
                SELECT set_aside_type, COUNT(*) as count, SUM(contract_value) as total_value
                FROM set_aside_tracking 
                WHERE certification_id = ?
                GROUP BY set_aside_type
            """, (cert_id,))
            
            utilization_data = []
            for row in cursor.fetchall():
                utilization_data.append({
                    "set_aside_type": row[0],
                    "contract_count": row[1],
                    "total_value": row[2] or 0
                })
            
            conn.close()
            
            # Calculate compliance score
            compliance_score = await self._calculate_compliance_score(compliance_records)
            
            return {
                "certification_id": cert_id,
                "company_name": cert[4],
                "certification_type": cert[0],
                "certification_status": cert[1],
                "certification_date": cert[2],
                "expiration_date": cert[3],
                "compliance_score": compliance_score,
                "size_standards_compliance": {
                    "annual_receipts": cert[5],
                    "employee_count": cert[6],
                    "status": "compliant"  # Would calculate based on NAICS standards
                },
                "compliance_monitoring": compliance_records,
                "set_aside_utilization": utilization_data,
                "recommendations": await self._generate_compliance_recommendations(
                    compliance_records, compliance_score
                )
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {"error": str(e)}

    async def _calculate_compliance_score(self, compliance_records: List[Dict[str, Any]]) -> float:
        """Calculate overall compliance score"""
        if not compliance_records:
            return 85.0  # Default score
        
        status_scores = {
            "compliant": 100,
            "mostly_compliant": 85,
            "partially_compliant": 70,
            "non_compliant": 40
        }
        
        total_score = 0
        for record in compliance_records:
            score = status_scores.get(record["status"], 70)
            total_score += score
        
        return round(total_score / len(compliance_records), 1)

    async def _generate_compliance_recommendations(self, compliance_records: List[Dict[str, Any]], 
                                                 compliance_score: float) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if compliance_score < 80:
            recommendations.append("Immediate attention required to address compliance issues")
        
        non_compliant_areas = [r["area"] for r in compliance_records if r["status"] == "non_compliant"]
        if non_compliant_areas:
            recommendations.append(f"Address non-compliance in: {', '.join(non_compliant_areas)}")
        
        recommendations.extend([
            "Maintain current size standards compliance",
            "Continue regular compliance monitoring",
            "Update documentation as business changes occur",
            "Prepare for certification renewal in advance"
        ])
        
        return recommendations

# Global instance
certification_system = SmallBusinessCertificationSystem()