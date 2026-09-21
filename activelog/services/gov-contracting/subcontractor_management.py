#!/usr/bin/env python3
"""
Subcontractor Management System
Comprehensive subcontractor registration, evaluation, and management
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

class SubcontractorStatus(Enum):
    PROSPECTIVE = "prospective"
    QUALIFIED = "qualified"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    BLACKLISTED = "blacklisted"

class SmallBusinessType(Enum):
    SMALL_BUSINESS = "small_business"
    SMALL_DISADVANTAGED = "small_disadvantaged"
    WOMAN_OWNED = "woman_owned"
    VETERAN_OWNED = "veteran_owned"
    SERVICE_DISABLED_VETERAN = "service_disabled_veteran"
    HUBZONE = "hubzone"
    HISTORICALLY_BLACK = "historically_black"
    NATIVE_AMERICAN = "native_american"
    NONE = "none"

class PerformanceRating(Enum):
    OUTSTANDING = "outstanding"
    SATISFACTORY = "satisfactory"
    MARGINAL = "marginal"
    UNSATISFACTORY = "unsatisfactory"
    NOT_RATED = "not_rated"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class SubcontractorManagementSystem:
    def __init__(self):
        self.db_path = "data/subcontractor_management.db"
        self.evaluation_criteria = {}
        self.risk_factors = {}

    async def initialize(self):
        """Initialize subcontractor management system"""
        try:
            await self._create_database_schema()
            await self._setup_evaluation_criteria()
            await self._setup_risk_factors()
            logger.info("Subcontractor Management System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Subcontractor Management System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for subcontractor management"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Subcontractors table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcontractors (
                id TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                duns_number TEXT UNIQUE,
                cage_code TEXT,
                sam_registration_status TEXT,
                sam_expiration_date TEXT,
                primary_naics TEXT,
                secondary_naics TEXT,
                small_business_type TEXT,
                business_structure TEXT,
                address_line1 TEXT,
                address_line2 TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                country TEXT DEFAULT 'USA',
                phone_number TEXT,
                email_address TEXT,
                website TEXT,
                primary_contact_name TEXT,
                primary_contact_title TEXT,
                primary_contact_phone TEXT,
                primary_contact_email TEXT,
                bonding_capacity REAL DEFAULT 0.0,
                insurance_general_liability REAL DEFAULT 0.0,
                insurance_professional_liability REAL DEFAULT 0.0,
                insurance_cyber_liability REAL DEFAULT 0.0,
                annual_revenue REAL DEFAULT 0.0,
                employee_count INTEGER DEFAULT 0,
                years_in_business INTEGER DEFAULT 0,
                security_clearance_facility TEXT,
                security_clearance_personnel TEXT,
                certifications TEXT,
                core_capabilities TEXT,
                past_performance_rating TEXT DEFAULT 'not_rated',
                overall_risk_rating TEXT DEFAULT 'medium',
                status TEXT NOT NULL DEFAULT 'prospective',
                registration_date TEXT NOT NULL,
                last_updated TEXT NOT NULL,
                audit_trail TEXT
            )
        """)
        
        # Subcontract agreements table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcontract_agreements (
                id TEXT PRIMARY KEY,
                prime_contract_id TEXT NOT NULL,
                subcontractor_id TEXT NOT NULL,
                subcontract_number TEXT NOT NULL,
                work_description TEXT NOT NULL,
                subcontract_value REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                performance_location TEXT,
                payment_terms TEXT,
                deliverables TEXT,
                key_personnel TEXT,
                status TEXT NOT NULL DEFAULT 'draft',
                signed_date TEXT,
                effective_date TEXT,
                modification_history TEXT,
                closeout_date TEXT,
                final_payment_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id)
            )
        """)
        
        # Performance evaluations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performance_evaluations (
                id TEXT PRIMARY KEY,
                subcontractor_id TEXT NOT NULL,
                subcontract_id TEXT,
                evaluation_period_start TEXT NOT NULL,
                evaluation_period_end TEXT NOT NULL,
                evaluator_name TEXT NOT NULL,
                evaluator_title TEXT,
                technical_performance_score REAL DEFAULT 0.0,
                schedule_performance_score REAL DEFAULT 0.0,
                cost_performance_score REAL DEFAULT 0.0,
                quality_score REAL DEFAULT 0.0,
                management_score REAL DEFAULT 0.0,
                overall_score REAL DEFAULT 0.0,
                overall_rating TEXT NOT NULL,
                strengths TEXT,
                weaknesses TEXT,
                recommendations TEXT,
                corrective_actions_required TEXT,
                follow_up_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id)
            )
        """)
        
        # Capacity assessments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS capacity_assessments (
                id TEXT PRIMARY KEY,
                subcontractor_id TEXT NOT NULL,
                assessment_date TEXT NOT NULL,
                assessor_name TEXT NOT NULL,
                technical_capacity_score REAL DEFAULT 0.0,
                financial_capacity_score REAL DEFAULT 0.0,
                management_capacity_score REAL DEFAULT 0.0,
                past_performance_score REAL DEFAULT 0.0,
                bonding_capacity REAL DEFAULT 0.0,
                current_workload_percentage REAL DEFAULT 0.0,
                available_capacity_percentage REAL DEFAULT 100.0,
                maximum_contract_value REAL DEFAULT 0.0,
                geographic_coverage TEXT,
                specialized_capabilities TEXT,
                capacity_limitations TEXT,
                recommendations TEXT,
                overall_capacity_rating TEXT,
                valid_until TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id)
            )
        """)
        
        # Payment tracking table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subcontractor_payments (
                id TEXT PRIMARY KEY,
                subcontractor_id TEXT NOT NULL,
                subcontract_id TEXT NOT NULL,
                invoice_number TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                invoice_amount REAL NOT NULL,
                payment_due_date TEXT NOT NULL,
                payment_date TEXT,
                payment_amount REAL,
                payment_method TEXT,
                payment_reference TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                late_fees REAL DEFAULT 0.0,
                discount_taken REAL DEFAULT 0.0,
                withholding_amount REAL DEFAULT 0.0,
                net_payment REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id),
                FOREIGN KEY (subcontract_id) REFERENCES subcontract_agreements (id)
            )
        """)
        
        # Risk assessments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS risk_assessments (
                id TEXT PRIMARY KEY,
                subcontractor_id TEXT NOT NULL,
                assessment_date TEXT NOT NULL,
                assessor_name TEXT NOT NULL,
                financial_risk_score REAL DEFAULT 0.0,
                performance_risk_score REAL DEFAULT 0.0,
                operational_risk_score REAL DEFAULT 0.0,
                compliance_risk_score REAL DEFAULT 0.0,
                security_risk_score REAL DEFAULT 0.0,
                overall_risk_score REAL DEFAULT 0.0,
                risk_level TEXT NOT NULL,
                identified_risks TEXT,
                mitigation_strategies TEXT,
                monitoring_plan TEXT,
                review_date TEXT,
                risk_appetite TEXT,
                recommendations TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id)
            )
        """)
        
        # Compliance monitoring table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_monitoring (
                id TEXT PRIMARY KEY,
                subcontractor_id TEXT NOT NULL,
                compliance_area TEXT NOT NULL,
                requirement_description TEXT NOT NULL,
                compliance_status TEXT NOT NULL,
                last_review_date TEXT,
                next_review_date TEXT,
                evidence_documents TEXT,
                compliance_score REAL DEFAULT 0.0,
                violations_count INTEGER DEFAULT 0,
                corrective_actions TEXT,
                responsible_party TEXT,
                deadline_date TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (subcontractor_id) REFERENCES subcontractors (id)
            )
        """)
        
        conn.commit()
        conn.close()

    async def _setup_evaluation_criteria(self):
        """Setup performance evaluation criteria"""
        self.evaluation_criteria = {
            "technical_performance": {
                "weight": 0.25,
                "factors": [
                    "Quality of deliverables",
                    "Technical expertise demonstrated",
                    "Innovation and problem-solving",
                    "Adherence to technical specifications"
                ]
            },
            "schedule_performance": {
                "weight": 0.25,
                "factors": [
                    "On-time delivery",
                    "Milestone adherence",
                    "Schedule recovery capabilities",
                    "Proactive communication on delays"
                ]
            },
            "cost_performance": {
                "weight": 0.20,
                "factors": [
                    "Budget adherence",
                    "Change order management",
                    "Cost transparency",
                    "Value engineering contributions"
                ]
            },
            "quality": {
                "weight": 0.15,
                "factors": [
                    "Defect rates",
                    "Rework requirements",
                    "Quality control processes",
                    "Customer satisfaction"
                ]
            },
            "management": {
                "weight": 0.15,
                "factors": [
                    "Project management effectiveness",
                    "Communication quality",
                    "Team coordination",
                    "Issue resolution"
                ]
            }
        }

    async def _setup_risk_factors(self):
        """Setup risk assessment factors"""
        self.risk_factors = {
            "financial": [
                "Credit rating",
                "Financial stability",
                "Cash flow adequacy",
                "Bonding capacity"
            ],
            "performance": [
                "Past performance history",
                "Current workload",
                "Resource availability",
                "Technical capability"
            ],
            "operational": [
                "Management stability",
                "Key personnel retention",
                "Geographic location",
                "Supply chain risks"
            ],
            "compliance": [
                "Regulatory compliance history",
                "Security clearance status",
                "Certification maintenance",
                "Audit findings"
            ],
            "security": [
                "Facility clearance",
                "Personnel clearance",
                "Information security practices",
                "Cybersecurity maturity"
            ]
        }

    async def register_subcontractor(self, subcontractor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Register new subcontractor"""
        try:
            subcontractor_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Validate required fields
            required_fields = ["company_name", "duns_number", "primary_naics"]
            missing_fields = [field for field in required_fields if not subcontractor_data.get(field)]
            
            if missing_fields:
                return {
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }
            
            # Check for duplicate DUNS number
            existing = await self._check_existing_subcontractor(subcontractor_data["duns_number"])
            if existing:
                return {
                    "error": f"Subcontractor with DUNS {subcontractor_data['duns_number']} already exists"
                }
            
            # Store subcontractor
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO subcontractors (
                    id, company_name, duns_number, cage_code, sam_registration_status,
                    sam_expiration_date, primary_naics, secondary_naics, small_business_type,
                    business_structure, address_line1, city, state, zip_code,
                    phone_number, email_address, website, primary_contact_name,
                    primary_contact_title, primary_contact_phone, primary_contact_email,
                    bonding_capacity, annual_revenue, employee_count, years_in_business,
                    security_clearance_facility, certifications, core_capabilities,
                    registration_date, last_updated, audit_trail
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subcontractor_id, subcontractor_data["company_name"],
                subcontractor_data["duns_number"], subcontractor_data.get("cage_code"),
                subcontractor_data.get("sam_registration_status", "active"),
                subcontractor_data.get("sam_expiration_date"),
                subcontractor_data["primary_naics"], subcontractor_data.get("secondary_naics"),
                subcontractor_data.get("small_business_type", SmallBusinessType.NONE.value),
                subcontractor_data.get("business_structure"),
                subcontractor_data.get("address_line1"), subcontractor_data.get("city"),
                subcontractor_data.get("state"), subcontractor_data.get("zip_code"),
                subcontractor_data.get("phone_number"), subcontractor_data.get("email_address"),
                subcontractor_data.get("website"), subcontractor_data.get("primary_contact_name"),
                subcontractor_data.get("primary_contact_title"),
                subcontractor_data.get("primary_contact_phone"),
                subcontractor_data.get("primary_contact_email"),
                subcontractor_data.get("bonding_capacity", 0),
                subcontractor_data.get("annual_revenue", 0),
                subcontractor_data.get("employee_count", 0),
                subcontractor_data.get("years_in_business", 0),
                subcontractor_data.get("security_clearance_facility"),
                json.dumps(subcontractor_data.get("certifications", [])),
                json.dumps(subcontractor_data.get("core_capabilities", [])),
                now, now, json.dumps([{"action": "registered", "date": now}])
            ))
            
            # Perform initial capacity assessment
            capacity_assessment = await self._perform_initial_capacity_assessment(
                subcontractor_id, subcontractor_data
            )
            
            # Perform initial risk assessment
            risk_assessment = await self._perform_initial_risk_assessment(
                subcontractor_id, subcontractor_data
            )
            
            conn.commit()
            conn.close()
            
            result = {
                "subcontractor_id": subcontractor_id,
                "company_name": subcontractor_data["company_name"],
                "duns_number": subcontractor_data["duns_number"],
                "status": SubcontractorStatus.PROSPECTIVE.value,
                "registration_date": now,
                "initial_assessments": {
                    "capacity_rating": capacity_assessment.get("overall_capacity_rating"),
                    "risk_level": risk_assessment.get("risk_level")
                },
                "next_steps": [
                    "Complete detailed capability assessment",
                    "Verify insurance and bonding requirements",
                    "Review past performance references",
                    "Conduct security clearance verification"
                ]
            }
            
            logger.info(f"Subcontractor registered: {subcontractor_data['company_name']} ({subcontractor_data['duns_number']})")
            return result
            
        except Exception as e:
            logger.error(f"Error registering subcontractor: {e}")
            return {"error": str(e)}

    async def _check_existing_subcontractor(self, duns_number: str) -> bool:
        """Check if subcontractor already exists"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM subcontractors WHERE duns_number = ?", (duns_number,))
        result = cursor.fetchone()
        
        conn.close()
        return result is not None

    async def _perform_initial_capacity_assessment(self, subcontractor_id: str, 
                                                 subcontractor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform initial capacity assessment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        assessment_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Calculate capacity scores based on available data
        financial_score = min(100, (subcontractor_data.get("annual_revenue", 0) / 1000000) * 20)
        management_score = min(100, subcontractor_data.get("years_in_business", 0) * 5)
        bonding_score = min(100, (subcontractor_data.get("bonding_capacity", 0) / 1000000) * 25)
        
        technical_score = 75  # Default score, to be updated with detailed assessment
        overall_score = (financial_score + management_score + bonding_score + technical_score) / 4
        
        # Determine capacity rating
        if overall_score >= 85:
            capacity_rating = "excellent"
        elif overall_score >= 70:
            capacity_rating = "good"
        elif overall_score >= 55:
            capacity_rating = "adequate"
        else:
            capacity_rating = "limited"
        
        # Store assessment
        cursor.execute("""
            INSERT INTO capacity_assessments (
                id, subcontractor_id, assessment_date, assessor_name,
                technical_capacity_score, financial_capacity_score,
                management_capacity_score, bonding_capacity, overall_capacity_rating,
                valid_until, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assessment_id, subcontractor_id, now, "System",
            technical_score, financial_score, management_score,
            subcontractor_data.get("bonding_capacity", 0), capacity_rating,
            (datetime.now() + timedelta(days=365)).isoformat(), now
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "assessment_id": assessment_id,
            "overall_capacity_rating": capacity_rating,
            "financial_capacity_score": financial_score,
            "management_capacity_score": management_score,
            "bonding_capacity": subcontractor_data.get("bonding_capacity", 0)
        }

    async def _perform_initial_risk_assessment(self, subcontractor_id: str,
                                             subcontractor_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform initial risk assessment"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        assessment_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Calculate risk scores based on available data
        financial_risk = 100 - min(100, (subcontractor_data.get("annual_revenue", 0) / 1000000) * 20)
        performance_risk = 50  # Default moderate risk
        operational_risk = max(0, 100 - (subcontractor_data.get("years_in_business", 0) * 5))
        compliance_risk = 25  # Low default risk
        security_risk = 50 if subcontractor_data.get("security_clearance_facility") else 75
        
        overall_risk = (financial_risk + performance_risk + operational_risk + 
                       compliance_risk + security_risk) / 5
        
        # Determine risk level
        if overall_risk >= 75:
            risk_level = RiskLevel.CRITICAL.value
        elif overall_risk >= 60:
            risk_level = RiskLevel.HIGH.value
        elif overall_risk >= 40:
            risk_level = RiskLevel.MEDIUM.value
        else:
            risk_level = RiskLevel.LOW.value
        
        # Store assessment
        cursor.execute("""
            INSERT INTO risk_assessments (
                id, subcontractor_id, assessment_date, assessor_name,
                financial_risk_score, performance_risk_score, operational_risk_score,
                compliance_risk_score, security_risk_score, overall_risk_score,
                risk_level, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            assessment_id, subcontractor_id, now, "System",
            financial_risk, performance_risk, operational_risk,
            compliance_risk, security_risk, overall_risk,
            risk_level, now
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "assessment_id": assessment_id,
            "risk_level": risk_level,
            "overall_risk_score": overall_risk,
            "key_risks": self._identify_key_risks(financial_risk, performance_risk, 
                                                 operational_risk, compliance_risk, security_risk)
        }

    def _identify_key_risks(self, financial: float, performance: float, 
                          operational: float, compliance: float, security: float) -> List[str]:
        """Identify key risk areas"""
        risks = []
        
        if financial > 70:
            risks.append("Financial stability concerns")
        if performance > 70:
            risks.append("Performance history risks")
        if operational > 70:
            risks.append("Operational capability risks")
        if compliance > 70:
            risks.append("Compliance and regulatory risks")
        if security > 70:
            risks.append("Security clearance risks")
        
        return risks

    async def evaluate_performance(self, subcontractor_id: str, 
                                 evaluation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate subcontractor performance"""
        try:
            evaluation_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Calculate weighted overall score
            criteria = self.evaluation_criteria
            
            technical_score = evaluation_data.get("technical_performance_score", 0)
            schedule_score = evaluation_data.get("schedule_performance_score", 0)
            cost_score = evaluation_data.get("cost_performance_score", 0)
            quality_score = evaluation_data.get("quality_score", 0)
            management_score = evaluation_data.get("management_score", 0)
            
            overall_score = (
                technical_score * criteria["technical_performance"]["weight"] +
                schedule_score * criteria["schedule_performance"]["weight"] +
                cost_score * criteria["cost_performance"]["weight"] +
                quality_score * criteria["quality"]["weight"] +
                management_score * criteria["management"]["weight"]
            )
            
            # Determine overall rating
            if overall_score >= 90:
                overall_rating = PerformanceRating.OUTSTANDING.value
            elif overall_score >= 75:
                overall_rating = PerformanceRating.SATISFACTORY.value
            elif overall_score >= 60:
                overall_rating = PerformanceRating.MARGINAL.value
            else:
                overall_rating = PerformanceRating.UNSATISFACTORY.value
            
            # Store evaluation
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO performance_evaluations (
                    id, subcontractor_id, subcontract_id, evaluation_period_start,
                    evaluation_period_end, evaluator_name, evaluator_title,
                    technical_performance_score, schedule_performance_score,
                    cost_performance_score, quality_score, management_score,
                    overall_score, overall_rating, strengths, weaknesses,
                    recommendations, corrective_actions_required, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evaluation_id, subcontractor_id, evaluation_data.get("subcontract_id"),
                evaluation_data.get("evaluation_period_start"),
                evaluation_data.get("evaluation_period_end"),
                evaluation_data.get("evaluator_name"),
                evaluation_data.get("evaluator_title"),
                technical_score, schedule_score, cost_score, quality_score, management_score,
                overall_score, overall_rating,
                evaluation_data.get("strengths", ""),
                evaluation_data.get("weaknesses", ""),
                evaluation_data.get("recommendations", ""),
                evaluation_data.get("corrective_actions_required", ""), now
            ))
            
            # Update subcontractor's overall performance rating
            cursor.execute("""
                UPDATE subcontractors 
                SET past_performance_rating = ?, last_updated = ?
                WHERE id = ?
            """, (overall_rating, now, subcontractor_id))
            
            conn.commit()
            conn.close()
            
            result = {
                "evaluation_id": evaluation_id,
                "subcontractor_id": subcontractor_id,
                "overall_score": round(overall_score, 2),
                "overall_rating": overall_rating,
                "score_breakdown": {
                    "technical_performance": technical_score,
                    "schedule_performance": schedule_score,
                    "cost_performance": cost_score,
                    "quality": quality_score,
                    "management": management_score
                },
                "evaluation_summary": {
                    "strengths": evaluation_data.get("strengths", ""),
                    "weaknesses": evaluation_data.get("weaknesses", ""),
                    "recommendations": evaluation_data.get("recommendations", "")
                },
                "impact_on_future_work": self._determine_impact_on_future_work(overall_rating)
            }
            
            logger.info(f"Performance evaluation completed: {overall_rating} ({overall_score:.1f})")
            return result
            
        except Exception as e:
            logger.error(f"Error evaluating performance: {e}")
            return {"error": str(e)}

    def _determine_impact_on_future_work(self, rating: str) -> List[str]:
        """Determine impact of performance rating on future work"""
        impacts = {
            PerformanceRating.OUTSTANDING.value: [
                "Preferred vendor status for future opportunities",
                "Eligible for increased subcontract values",
                "Reduced oversight and monitoring requirements",
                "Priority consideration for new contracts"
            ],
            PerformanceRating.SATISFACTORY.value: [
                "Continues to meet requirements for future work",
                "Standard monitoring and oversight maintained",
                "Eligible for contract renewals"
            ],
            PerformanceRating.MARGINAL.value: [
                "Increased oversight and monitoring required",
                "Performance improvement plan needed",
                "Limited eligibility for new contracts",
                "Regular progress reviews required"
            ],
            PerformanceRating.UNSATISFACTORY.value: [
                "Immediate corrective action required",
                "Suspension from future work consideration",
                "Potential contract termination",
                "Formal performance improvement plan mandatory"
            ]
        }
        
        return impacts.get(rating, ["Standard evaluation process applies"])

    async def get_performance_metrics(self, subcontractor_id: str) -> Dict[str, Any]:
        """Get comprehensive performance metrics for subcontractor"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get subcontractor basic info
            cursor.execute("SELECT company_name, past_performance_rating FROM subcontractors WHERE id = ?", 
                         (subcontractor_id,))
            subcontractor = cursor.fetchone()
            
            if not subcontractor:
                return {"error": "Subcontractor not found"}
            
            # Get all performance evaluations
            cursor.execute("""
                SELECT evaluation_period_start, evaluation_period_end, overall_score, 
                       overall_rating, technical_performance_score, schedule_performance_score,
                       cost_performance_score, quality_score, management_score
                FROM performance_evaluations 
                WHERE subcontractor_id = ?
                ORDER BY evaluation_period_start DESC
            """, (subcontractor_id,))
            
            evaluations = []
            total_score = 0
            evaluation_count = 0
            
            for row in cursor.fetchall():
                evaluation = {
                    "period_start": row[0],
                    "period_end": row[1],
                    "overall_score": row[2],
                    "overall_rating": row[3],
                    "technical_score": row[4],
                    "schedule_score": row[5],
                    "cost_score": row[6],
                    "quality_score": row[7],
                    "management_score": row[8]
                }
                evaluations.append(evaluation)
                total_score += row[2]
                evaluation_count += 1
            
            # Calculate averages
            average_score = total_score / evaluation_count if evaluation_count > 0 else 0
            
            # Get recent capacity assessment
            cursor.execute("""
                SELECT overall_capacity_rating, available_capacity_percentage,
                       maximum_contract_value
                FROM capacity_assessments 
                WHERE subcontractor_id = ?
                ORDER BY assessment_date DESC
                LIMIT 1
            """, (subcontractor_id,))
            
            capacity = cursor.fetchone()
            
            # Get current risk assessment
            cursor.execute("""
                SELECT risk_level, overall_risk_score
                FROM risk_assessments 
                WHERE subcontractor_id = ?
                ORDER BY assessment_date DESC
                LIMIT 1
            """, (subcontractor_id,))
            
            risk = cursor.fetchone()
            
            conn.close()
            
            return {
                "subcontractor_id": subcontractor_id,
                "company_name": subcontractor[0],
                "current_rating": subcontractor[1],
                "performance_history": {
                    "evaluation_count": evaluation_count,
                    "average_score": round(average_score, 2),
                    "recent_evaluations": evaluations[:5]  # Last 5 evaluations
                },
                "capacity_status": {
                    "capacity_rating": capacity[0] if capacity else "not_assessed",
                    "available_capacity": capacity[1] if capacity else 0,
                    "maximum_contract_value": capacity[2] if capacity else 0
                } if capacity else {},
                "risk_profile": {
                    "risk_level": risk[0] if risk else "medium",
                    "risk_score": risk[1] if risk else 50
                } if risk else {},
                "performance_trends": self._calculate_performance_trends(evaluations),
                "recommendations": self._generate_performance_recommendations(
                    average_score, evaluations
                )
            }
            
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {"error": str(e)}

    def _calculate_performance_trends(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        if len(evaluations) < 2:
            return {"trend": "insufficient_data", "direction": "stable"}
        
        recent_scores = [e["overall_score"] for e in evaluations[:3]]
        older_scores = [e["overall_score"] for e in evaluations[-3:]]
        
        recent_avg = sum(recent_scores) / len(recent_scores)
        older_avg = sum(older_scores) / len(older_scores)
        
        difference = recent_avg - older_avg
        
        if difference > 5:
            direction = "improving"
        elif difference < -5:
            direction = "declining"
        else:
            direction = "stable"
        
        return {
            "trend": f"{abs(difference):.1f}_point_change",
            "direction": direction,
            "recent_average": round(recent_avg, 2),
            "historical_average": round(older_avg, 2)
        }

    def _generate_performance_recommendations(self, average_score: float,
                                            evaluations: List[Dict[str, Any]]) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []
        
        if average_score < 70:
            recommendations.append("Consider performance improvement plan")
            recommendations.append("Increase monitoring and oversight")
        elif average_score < 85:
            recommendations.append("Focus on identified improvement areas")
            recommendations.append("Regular performance check-ins")
        else:
            recommendations.append("Continue current performance level")
            recommendations.append("Consider for additional opportunities")
        
        # Analyze specific weak areas from recent evaluations
        if evaluations:
            recent_eval = evaluations[0]
            if recent_eval["technical_score"] < 75:
                recommendations.append("Address technical capability gaps")
            if recent_eval["schedule_score"] < 75:
                recommendations.append("Improve schedule management practices")
            if recent_eval["quality_score"] < 75:
                recommendations.append("Enhance quality control processes")
        
        return recommendations

    async def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment to subcontractor"""
        try:
            payment_id = str(uuid.uuid4())
            now = datetime.now().isoformat()
            
            # Calculate payment amounts
            invoice_amount = Decimal(str(payment_data.get("invoice_amount", 0)))
            withholding = Decimal(str(payment_data.get("withholding_amount", 0)))
            discount = Decimal(str(payment_data.get("discount_taken", 0)))
            net_payment = invoice_amount - withholding - discount
            
            # Store payment
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO subcontractor_payments (
                    id, subcontractor_id, subcontract_id, invoice_number,
                    invoice_date, invoice_amount, payment_due_date,
                    payment_date, payment_amount, payment_method,
                    payment_reference, status, withholding_amount,
                    discount_taken, net_payment, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment_id, payment_data["subcontractor_id"],
                payment_data["subcontract_id"], payment_data["invoice_number"],
                payment_data["invoice_date"], float(invoice_amount),
                payment_data["payment_due_date"], now, float(net_payment),
                payment_data.get("payment_method", "ACH"),
                payment_data.get("payment_reference"),
                "processed", float(withholding), float(discount),
                float(net_payment), now, now
            ))
            
            conn.commit()
            conn.close()
            
            return {
                "payment_id": payment_id,
                "subcontractor_id": payment_data["subcontractor_id"],
                "invoice_number": payment_data["invoice_number"],
                "payment_amount": float(net_payment),
                "payment_date": now,
                "status": "processed",
                "payment_breakdown": {
                    "invoice_amount": float(invoice_amount),
                    "withholding_amount": float(withholding),
                    "discount_taken": float(discount),
                    "net_payment": float(net_payment)
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return {"error": str(e)}

    async def monitor_compliance(self, subcontractor_id: str) -> Dict[str, Any]:
        """Monitor subcontractor compliance across multiple areas"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get all compliance areas
            cursor.execute("""
                SELECT compliance_area, compliance_status, compliance_score,
                       violations_count, last_review_date, next_review_date
                FROM compliance_monitoring 
                WHERE subcontractor_id = ?
                ORDER BY compliance_area
            """, (subcontractor_id,))
            
            compliance_areas = []
            total_score = 0
            area_count = 0
            total_violations = 0
            
            for row in cursor.fetchall():
                area = {
                    "area": row[0],
                    "status": row[1],
                    "score": row[2],
                    "violations": row[3],
                    "last_review": row[4],
                    "next_review": row[5]
                }
                compliance_areas.append(area)
                total_score += row[2] or 0
                area_count += 1
                total_violations += row[3] or 0
            
            overall_score = total_score / area_count if area_count > 0 else 100
            
            # Determine overall compliance status
            if overall_score >= 95 and total_violations == 0:
                overall_status = "excellent"
            elif overall_score >= 85 and total_violations <= 2:
                overall_status = "good"
            elif overall_score >= 75 and total_violations <= 5:
                overall_status = "acceptable"
            else:
                overall_status = "needs_improvement"
            
            conn.close()
            
            return {
                "subcontractor_id": subcontractor_id,
                "overall_compliance_status": overall_status,
                "overall_compliance_score": round(overall_score, 2),
                "total_violations": total_violations,
                "compliance_areas": compliance_areas,
                "recommendations": self._generate_compliance_recommendations(
                    overall_status, compliance_areas
                ),
                "next_actions": self._identify_compliance_actions(compliance_areas)
            }
            
        except Exception as e:
            logger.error(f"Error monitoring compliance: {e}")
            return {"error": str(e)}

    def _generate_compliance_recommendations(self, overall_status: str,
                                           compliance_areas: List[Dict[str, Any]]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if overall_status == "needs_improvement":
            recommendations.append("Immediate compliance review and corrective action required")
            recommendations.append("Increase monitoring frequency")
        
        # Check specific areas needing attention
        for area in compliance_areas:
            if area["score"] < 80:
                recommendations.append(f"Address compliance gaps in {area['area']}")
            if area["violations"] > 0:
                recommendations.append(f"Resolve {area['violations']} violations in {area['area']}")
        
        if not recommendations:
            recommendations.append("Maintain current compliance standards")
            recommendations.append("Continue regular monitoring schedule")
        
        return recommendations

    def _identify_compliance_actions(self, compliance_areas: List[Dict[str, Any]]) -> List[str]:
        """Identify required compliance actions"""
        actions = []
        now = datetime.now()
        
        for area in compliance_areas:
            if area["next_review"]:
                try:
                    review_date = datetime.fromisoformat(area["next_review"])
                    days_until_review = (review_date - now).days
                    
                    if days_until_review <= 7:
                        actions.append(f"Schedule compliance review for {area['area']}")
                except:
                    pass
            
            if area["violations"] > 0:
                actions.append(f"Address {area['violations']} violations in {area['area']}")
        
        if not actions:
            actions.append("No immediate compliance actions required")
        
        return actions

# Global instance
subcontractor_system = SubcontractorManagementSystem()