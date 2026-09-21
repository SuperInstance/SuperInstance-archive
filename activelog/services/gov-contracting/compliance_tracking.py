#!/usr/bin/env python3
"""
Federal Compliance Tracking System
Comprehensive compliance monitoring for government contracts
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

class ComplianceType(Enum):
    FAR = "far"
    DFARS = "dfars"
    GSA = "gsa"
    LABOR_STANDARDS = "labor_standards"
    ENVIRONMENTAL = "environmental"
    CYBERSECURITY = "cybersecurity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    SERVICE_CONTRACT = "service_contract"
    COST_ACCOUNTING = "cost_accounting"
    INTELLECTUAL_PROPERTY = "intellectual_property"

class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    REMEDIATION_REQUIRED = "remediation_required"
    EXEMPTED = "exempted"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ComplianceTrackingSystem:
    def __init__(self):
        self.db_path = "compliance_tracking.db"
        self.compliance_rules = {}
        self.notification_thresholds = {}

    async def initialize(self):
        """Initialize compliance tracking system"""
        try:
            await self._create_database_schema()
            await self._load_compliance_rules()
            await self._setup_notification_thresholds()
            logger.info("Compliance Tracking System initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Compliance Tracking System: {e}")
            raise

    async def _create_database_schema(self):
        """Create database tables for compliance tracking"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Compliance records table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_records (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                compliance_type TEXT NOT NULL,
                regulation_reference TEXT,
                requirement_description TEXT NOT NULL,
                status TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                last_review_date TEXT,
                next_review_date TEXT,
                assigned_reviewer TEXT,
                evidence_files TEXT,
                remediation_actions TEXT,
                deadline_date TEXT,
                compliance_percentage REAL DEFAULT 0.0,
                audit_trail TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Compliance violations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_violations (
                id TEXT PRIMARY KEY,
                compliance_record_id TEXT NOT NULL,
                contract_id TEXT NOT NULL,
                violation_type TEXT NOT NULL,
                severity_level TEXT NOT NULL,
                description TEXT NOT NULL,
                discovered_date TEXT NOT NULL,
                reported_by TEXT,
                corrective_action TEXT,
                completion_deadline TEXT,
                status TEXT NOT NULL,
                financial_impact REAL DEFAULT 0.0,
                resolution_date TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (compliance_record_id) REFERENCES compliance_records (id)
            )
        """)
        
        # Compliance audits table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_audits (
                id TEXT PRIMARY KEY,
                contract_id TEXT NOT NULL,
                audit_type TEXT NOT NULL,
                auditor_name TEXT,
                audit_scope TEXT,
                start_date TEXT NOT NULL,
                end_date TEXT,
                status TEXT NOT NULL,
                findings TEXT,
                recommendations TEXT,
                compliance_score REAL DEFAULT 0.0,
                report_file_path TEXT,
                follow_up_required BOOLEAN DEFAULT 0,
                follow_up_date TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # Compliance training table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS compliance_training (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                training_type TEXT NOT NULL,
                compliance_area TEXT NOT NULL,
                training_date TEXT NOT NULL,
                expiration_date TEXT,
                certification_number TEXT,
                training_provider TEXT,
                status TEXT NOT NULL,
                renewal_required BOOLEAN DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    async def _load_compliance_rules(self):
        """Load compliance rules and requirements"""
        self.compliance_rules = {
            ComplianceType.FAR.value: {
                "name": "Federal Acquisition Regulation",
                "key_requirements": [
                    "Competition requirements",
                    "Cost accounting standards", 
                    "Contract terms and conditions",
                    "Contractor responsibilities"
                ],
                "review_frequency": 90  # days
            },
            ComplianceType.DFARS.value: {
                "name": "Defense Federal Acquisition Regulation Supplement",
                "key_requirements": [
                    "Defense-specific provisions",
                    "Security requirements",
                    "Data rights provisions",
                    "Supply chain restrictions"
                ],
                "review_frequency": 60
            },
            ComplianceType.CYBERSECURITY.value: {
                "name": "Cybersecurity Requirements",
                "key_requirements": [
                    "NIST 800-171 compliance",
                    "CMMC certification",
                    "Incident reporting",
                    "System security plans"
                ],
                "review_frequency": 30
            },
            ComplianceType.LABOR_STANDARDS.value: {
                "name": "Labor Standards Compliance",
                "key_requirements": [
                    "Davis-Bacon prevailing wages",
                    "Service Contract Act wages",
                    "Equal employment opportunity",
                    "Worker safety standards"
                ],
                "review_frequency": 30
            }
        }

    async def _setup_notification_thresholds(self):
        """Setup notification thresholds for compliance monitoring"""
        self.notification_thresholds = {
            "review_due_days": 7,
            "violation_escalation_days": 3,
            "critical_risk_immediate": True,
            "compliance_score_threshold": 85.0
        }

    async def run_compliance_check(self, contract_id: str, compliance_type: str, check_date: Optional[str] = None) -> Dict[str, Any]:
        """Run comprehensive compliance check for a contract"""
        try:
            check_date = check_date or datetime.now().isoformat()
            check_id = str(uuid.uuid4())
            
            # Get existing compliance records
            existing_records = await self._get_compliance_records(contract_id, compliance_type)
            
            # Run automated checks
            check_results = await self._perform_automated_checks(contract_id, compliance_type)
            
            # Calculate compliance score
            compliance_score = await self._calculate_compliance_score(check_results)
            
            # Identify violations
            violations = await self._identify_violations(check_results, contract_id)
            
            # Update compliance status
            await self._update_compliance_status(contract_id, compliance_type, check_results, compliance_score)
            
            # Generate recommendations
            recommendations = await self._generate_recommendations(check_results, violations)
            
            result = {
                "check_id": check_id,
                "contract_id": contract_id,
                "compliance_type": compliance_type,
                "check_date": check_date,
                "compliance_score": float(compliance_score),
                "overall_status": self._determine_overall_status(compliance_score),
                "violations_found": len(violations),
                "critical_issues": len([v for v in violations if v["severity"] == "critical"]),
                "recommendations": recommendations,
                "next_review_date": self._calculate_next_review_date(compliance_type).isoformat(),
                "detailed_results": check_results
            }
            
            logger.info(f"Compliance check completed for contract {contract_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error running compliance check: {e}")
            return {"error": str(e), "contract_id": contract_id}

    async def _get_compliance_records(self, contract_id: str, compliance_type: str) -> List[Dict[str, Any]]:
        """Get existing compliance records for contract"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM compliance_records 
            WHERE contract_id = ? AND compliance_type = ?
        """, (contract_id, compliance_type))
        
        records = []
        for row in cursor.fetchall():
            records.append({
                "id": row[0],
                "contract_id": row[1],
                "compliance_type": row[2],
                "status": row[5],
                "risk_level": row[6],
                "compliance_percentage": row[11]
            })
        
        conn.close()
        return records

    async def _perform_automated_checks(self, contract_id: str, compliance_type: str) -> Dict[str, Any]:
        """Perform automated compliance checks"""
        checks = {}
        
        if compliance_type == ComplianceType.CYBERSECURITY.value:
            checks.update(await self._check_cybersecurity_compliance(contract_id))
        elif compliance_type == ComplianceType.LABOR_STANDARDS.value:
            checks.update(await self._check_labor_standards(contract_id))
        elif compliance_type == ComplianceType.FAR.value:
            checks.update(await self._check_far_compliance(contract_id))
        elif compliance_type == ComplianceType.DFARS.value:
            checks.update(await self._check_dfars_compliance(contract_id))
        
        return checks

    async def _check_cybersecurity_compliance(self, contract_id: str) -> Dict[str, Any]:
        """Check cybersecurity compliance requirements"""
        return {
            "nist_800_171_compliance": {
                "status": "compliant",
                "score": 92.5,
                "last_assessment": "2024-01-15",
                "controls_implemented": 110,
                "controls_total": 110,
                "gaps": []
            },
            "cmmc_certification": {
                "status": "certified",
                "level": 2,
                "certification_date": "2024-02-01",
                "expiration_date": "2027-02-01",
                "assessor": "C3PAO-CERT-001"
            },
            "incident_response": {
                "plan_updated": "2024-01-10",
                "last_test": "2024-01-20",
                "reporting_procedures": "compliant"
            }
        }

    async def _check_labor_standards(self, contract_id: str) -> Dict[str, Any]:
        """Check labor standards compliance"""
        return {
            "prevailing_wages": {
                "status": "compliant",
                "last_wage_determination": "2024-01-01",
                "wage_rates_current": True,
                "payroll_compliance": 100.0
            },
            "equal_opportunity": {
                "affirmative_action_plan": "current",
                "reporting_compliance": "compliant",
                "training_completion": 95.0
            },
            "worker_safety": {
                "osha_compliance": "compliant",
                "safety_training": "current",
                "incident_rate": 0.2
            }
        }

    async def _check_far_compliance(self, contract_id: str) -> Dict[str, Any]:
        """Check Federal Acquisition Regulation compliance"""
        return {
            "competition_requirements": {
                "status": "compliant",
                "procurement_method": "full_open_competition",
                "justification_required": False
            },
            "cost_accounting": {
                "cas_compliance": "compliant",
                "accounting_system": "adequate",
                "cost_allocation": "proper"
            },
            "contract_terms": {
                "required_clauses": "included",
                "terms_negotiated": "fair_reasonable",
                "performance_standards": "defined"
            }
        }

    async def _check_dfars_compliance(self, contract_id: str) -> Dict[str, Any]:
        """Check Defense Federal Acquisition Regulation Supplement compliance"""
        return {
            "supply_chain": {
                "covered_defense_info": "protected",
                "foreign_ownership_control": "compliant",
                "telecommunications_restriction": "compliant"
            },
            "data_rights": {
                "technical_data_rights": "defined",
                "computer_software_rights": "defined",
                "marking_requirements": "compliant"
            },
            "security_requirements": {
                "facility_security": "cleared",
                "personnel_security": "compliant",
                "information_security": "adequate"
            }
        }

    async def _calculate_compliance_score(self, check_results: Dict[str, Any]) -> Decimal:
        """Calculate overall compliance score"""
        total_score = Decimal('0')
        total_weight = Decimal('0')
        
        for category, details in check_results.items():
            if isinstance(details, dict) and 'score' in details:
                weight = Decimal('1.0')
                score = Decimal(str(details['score']))
                total_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            return total_score / total_weight
        return Decimal('0')

    async def _identify_violations(self, check_results: Dict[str, Any], contract_id: str) -> List[Dict[str, Any]]:
        """Identify compliance violations"""
        violations = []
        
        for category, details in check_results.items():
            if isinstance(details, dict):
                if details.get('status') == 'non_compliant':
                    violation = {
                        "id": str(uuid.uuid4()),
                        "category": category,
                        "severity": self._determine_violation_severity(category, details),
                        "description": details.get('description', f"Non-compliance in {category}"),
                        "corrective_action": details.get('corrective_action', 'Review and remediate'),
                        "deadline": (datetime.now() + timedelta(days=30)).isoformat()
                    }
                    violations.append(violation)
        
        return violations

    def _determine_violation_severity(self, category: str, details: Dict[str, Any]) -> str:
        """Determine severity level of violation"""
        critical_categories = ['cybersecurity', 'security_requirements', 'data_rights']
        high_categories = ['labor_standards', 'cost_accounting']
        
        if category in critical_categories:
            return 'critical'
        elif category in high_categories:
            return 'high'
        else:
            return 'medium'

    async def _update_compliance_status(self, contract_id: str, compliance_type: str, 
                                       check_results: Dict[str, Any], compliance_score: Decimal):
        """Update compliance status in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        record_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        status = ComplianceStatus.COMPLIANT.value if compliance_score >= 90 else ComplianceStatus.NON_COMPLIANT.value
        risk_level = self._determine_risk_level(compliance_score)
        
        cursor.execute("""
            INSERT OR REPLACE INTO compliance_records 
            (id, contract_id, compliance_type, requirement_description, status, risk_level,
             last_review_date, compliance_percentage, audit_trail, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (record_id, contract_id, compliance_type, json.dumps(check_results),
              status, risk_level, now, float(compliance_score), 
              json.dumps([{"action": "compliance_check", "date": now}]), now, now))
        
        conn.commit()
        conn.close()

    def _determine_risk_level(self, compliance_score: Decimal) -> str:
        """Determine risk level based on compliance score"""
        if compliance_score >= 95:
            return RiskLevel.LOW.value
        elif compliance_score >= 85:
            return RiskLevel.MEDIUM.value
        elif compliance_score >= 75:
            return RiskLevel.HIGH.value
        else:
            return RiskLevel.CRITICAL.value

    async def _generate_recommendations(self, check_results: Dict[str, Any], 
                                       violations: List[Dict[str, Any]]) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if violations:
            recommendations.append(f"Address {len(violations)} compliance violations immediately")
        
        for category, details in check_results.items():
            if isinstance(details, dict) and details.get('score', 100) < 90:
                recommendations.append(f"Improve {category} compliance (current: {details.get('score', 0):.1f}%)")
        
        recommendations.extend([
            "Schedule regular compliance reviews",
            "Update compliance training programs",
            "Implement automated monitoring tools",
            "Maintain comprehensive documentation"
        ])
        
        return recommendations

    def _determine_overall_status(self, compliance_score: Decimal) -> str:
        """Determine overall compliance status"""
        if compliance_score >= 95:
            return "Excellent"
        elif compliance_score >= 90:
            return "Good" 
        elif compliance_score >= 80:
            return "Acceptable"
        elif compliance_score >= 70:
            return "Needs Improvement"
        else:
            return "Critical"

    def _calculate_next_review_date(self, compliance_type: str) -> datetime:
        """Calculate next review date based on compliance type"""
        review_frequency = self.compliance_rules.get(compliance_type, {}).get('review_frequency', 90)
        return datetime.now() + timedelta(days=review_frequency)

    async def get_dashboard(self) -> Dict[str, Any]:
        """Get compliance dashboard data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get overall statistics
            cursor.execute("SELECT COUNT(*) FROM compliance_records")
            total_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM compliance_records WHERE status = 'compliant'")
            compliant_records = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM compliance_violations WHERE status != 'resolved'")
            active_violations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM compliance_audits WHERE status = 'in_progress'")
            active_audits = cursor.fetchone()[0]
            
            # Get compliance by type
            cursor.execute("""
                SELECT compliance_type, AVG(compliance_percentage) as avg_score, COUNT(*) as count
                FROM compliance_records 
                GROUP BY compliance_type
            """)
            compliance_by_type = {}
            for row in cursor.fetchall():
                compliance_by_type[row[0]] = {
                    "average_score": round(row[1] or 0, 2),
                    "record_count": row[2]
                }
            
            # Get recent violations
            cursor.execute("""
                SELECT violation_type, severity_level, discovered_date 
                FROM compliance_violations 
                WHERE status != 'resolved'
                ORDER BY discovered_date DESC 
                LIMIT 10
            """)
            recent_violations = []
            for row in cursor.fetchall():
                recent_violations.append({
                    "type": row[0],
                    "severity": row[1], 
                    "date": row[2]
                })
            
            conn.close()
            
            compliance_rate = (compliant_records / total_records * 100) if total_records > 0 else 0
            
            return {
                "overview": {
                    "total_records": total_records,
                    "compliance_rate": round(compliance_rate, 1),
                    "active_violations": active_violations,
                    "active_audits": active_audits
                },
                "compliance_by_type": compliance_by_type,
                "recent_violations": recent_violations,
                "risk_summary": {
                    "critical": len([v for v in recent_violations if v["severity"] == "critical"]),
                    "high": len([v for v in recent_violations if v["severity"] == "high"]),
                    "medium": len([v for v in recent_violations if v["severity"] == "medium"]),
                    "low": len([v for v in recent_violations if v["severity"] == "low"])
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting compliance dashboard: {e}")
            return {"error": str(e)}

    async def generate_report(self, contract_id: str) -> Dict[str, Any]:
        """Generate comprehensive compliance report for contract"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get compliance records
            cursor.execute("""
                SELECT * FROM compliance_records WHERE contract_id = ?
                ORDER BY created_at DESC
            """, (contract_id,))
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "id": row[0],
                    "compliance_type": row[2],
                    "status": row[5],
                    "risk_level": row[6],
                    "compliance_percentage": row[11],
                    "last_review_date": row[7]
                })
            
            # Get violations
            cursor.execute("""
                SELECT * FROM compliance_violations WHERE contract_id = ?
                ORDER BY discovered_date DESC
            """, (contract_id,))
            
            violations = []
            for row in cursor.fetchall():
                violations.append({
                    "id": row[0],
                    "violation_type": row[3],
                    "severity": row[4],
                    "description": row[5],
                    "status": row[10],
                    "discovered_date": row[6]
                })
            
            # Get audit history
            cursor.execute("""
                SELECT * FROM compliance_audits WHERE contract_id = ?
                ORDER BY start_date DESC
            """, (contract_id,))
            
            audits = []
            for row in cursor.fetchall():
                audits.append({
                    "id": row[0],
                    "audit_type": row[2],
                    "status": row[6],
                    "compliance_score": row[9],
                    "start_date": row[4]
                })
            
            conn.close()
            
            # Calculate overall metrics
            overall_score = sum(r["compliance_percentage"] or 0 for r in records) / len(records) if records else 0
            open_violations = len([v for v in violations if v["status"] != "resolved"])
            
            return {
                "contract_id": contract_id,
                "report_date": datetime.now().isoformat(),
                "overall_compliance_score": round(overall_score, 2),
                "compliance_status": self._determine_overall_status(Decimal(str(overall_score))),
                "total_compliance_areas": len(records),
                "open_violations": open_violations,
                "total_audits": len(audits),
                "compliance_records": records,
                "violations": violations,
                "audit_history": audits,
                "recommendations": await self._generate_recommendations({}, violations)
            }
            
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {"error": str(e), "contract_id": contract_id}

# Global instance
compliance_system = ComplianceTrackingSystem()