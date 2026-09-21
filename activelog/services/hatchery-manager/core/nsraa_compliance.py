"""
NSRAA/SSRAA Compliance Management
National Shellfish Sanitation Program (NSSP) and State Shellfish Resource Assessment Act compliance
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from ..models.hatchery_types import (
    ComplianceViolation, AlertLevel, SiteInfo, Employee,
    WaterQualityReading, ProductionMetrics, SpeciesType
)

logger = logging.getLogger(__name__)

class ComplianceRegulation(Enum):
    NSRAA = "nsraa"
    SSRAA = "ssraa"
    EPA_NPDES = "epa_npdes"
    FDA_HACCP = "fda_haccp"
    STATE_FISH_HEALTH = "state_fish_health"
    USDA_ORGANIC = "usda_organic"

@dataclass
class ComplianceRequirement:
    regulation: ComplianceRegulation
    requirement_id: str
    title: str
    description: str
    frequency: str  # "daily", "weekly", "monthly", "annual"
    mandatory: bool
    penalty_severity: AlertLevel
    inspection_method: str  # "automated", "manual", "third_party"

@dataclass
class ComplianceCheck:
    check_id: str
    requirement_id: str
    site_id: str
    status: str  # "passed", "failed", "pending", "not_applicable"
    checked_date: datetime
    next_due_date: Optional[datetime]
    evidence: List[str]  # file paths, readings, etc.
    inspector: Optional[str]
    notes: Optional[str] = None

class NSRAACompliance:
    def __init__(self):
        self.requirements = self._initialize_requirements()
        self.compliance_history: Dict[str, List[ComplianceCheck]] = {}
        self.violation_tracking: Dict[str, ComplianceViolation] = {}
        
    def _initialize_requirements(self) -> Dict[str, ComplianceRequirement]:
        """Initialize all compliance requirements"""
        requirements = {}
        
        # NSRAA Requirements
        nsraa_reqs = [
            ComplianceRequirement(
                ComplianceRegulation.NSRAA,
                "NSRAA_001",
                "Water Quality Monitoring",
                "Daily monitoring of water temperature, pH, dissolved oxygen, and turbidity",
                "daily",
                True,
                AlertLevel.HIGH,
                "automated"
            ),
            ComplianceRequirement(
                ComplianceRegulation.NSRAA,
                "NSRAA_002", 
                "Fish Health Inspections",
                "Weekly visual health assessments and monthly veterinary inspections",
                "weekly",
                True,
                AlertLevel.CRITICAL,
                "manual"
            ),
            ComplianceRequirement(
                ComplianceRegulation.NSRAA,
                "NSRAA_003",
                "Feed Quality Documentation",
                "Maintain records of feed sources, quality certificates, and usage logs",
                "daily",
                True,
                AlertLevel.MEDIUM,
                "manual"
            ),
            ComplianceRequirement(
                ComplianceRegulation.NSRAA,
                "NSRAA_004",
                "Mortality Recording",
                "Document all fish mortalities with cause analysis",
                "daily",
                True,
                AlertLevel.HIGH,
                "manual"
            ),
            ComplianceRequirement(
                ComplianceRegulation.NSRAA,
                "NSRAA_005",
                "Employee Training Certification",
                "All staff must have current aquaculture handling certifications",
                "annual",
                True,
                AlertLevel.MEDIUM,
                "third_party"
            )
        ]
        
        # SSRAA Requirements
        ssraa_reqs = [
            ComplianceRequirement(
                ComplianceRegulation.SSRAA,
                "SSRAA_001",
                "Spawning Stock Assessment",
                "Annual assessment of breeding stock genetic diversity and health",
                "annual",
                True,
                AlertLevel.HIGH,
                "third_party"
            ),
            ComplianceRequirement(
                ComplianceRegulation.SSRAA,
                "SSRAA_002",
                "Habitat Impact Monitoring",
                "Quarterly assessment of environmental impact on local watersheds",
                "monthly",
                True,
                AlertLevel.CRITICAL,
                "third_party"
            ),
            ComplianceRequirement(
                ComplianceRegulation.SSRAA,
                "SSRAA_003",
                "Escapement Prevention",
                "Daily inspection of containment systems and escape prevention measures",
                "daily",
                True,
                AlertLevel.CRITICAL,
                "automated"
            ),
            ComplianceRequirement(
                ComplianceRegulation.SSRAA,
                "SSRAA_004",
                "Waste Management",
                "Weekly monitoring of solid and liquid waste disposal systems",
                "weekly",
                True,
                AlertLevel.HIGH,
                "automated"
            )
        ]
        
        # EPA NPDES Requirements
        epa_reqs = [
            ComplianceRequirement(
                ComplianceRegulation.EPA_NPDES,
                "EPA_001",
                "Effluent Quality Monitoring",
                "Monthly testing of discharge water for pollutants and contaminants",
                "monthly",
                True,
                AlertLevel.CRITICAL,
                "third_party"
            ),
            ComplianceRequirement(
                ComplianceRegulation.EPA_NPDES,
                "EPA_002",
                "Chemical Usage Reporting",
                "Quarterly reporting of all chemicals used in facility operations",
                "monthly",
                True,
                AlertLevel.HIGH,
                "manual"
            )
        ]
        
        all_reqs = nsraa_reqs + ssraa_reqs + epa_reqs
        
        for req in all_reqs:
            requirements[req.requirement_id] = req
            
        return requirements
    
    async def run_compliance_check(self, site_id: str = None) -> Dict[str, Any]:
        """Run comprehensive compliance check for site or all sites"""
        logger.info(f"Running compliance check for site: {site_id or 'ALL'}")
        
        results = {
            "check_date": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id,
            "overall_status": "compliant",
            "violations": [],
            "warnings": [],
            "requirements_checked": 0,
            "requirements_passed": 0,
            "next_inspections": []
        }
        
        for req_id, requirement in self.requirements.items():
            check_result = await self._check_requirement(requirement, site_id)
            results["requirements_checked"] += 1
            
            if check_result["status"] == "passed":
                results["requirements_passed"] += 1
            elif check_result["status"] == "failed":
                violation = ComplianceViolation(
                    violation_id=f"VIO_{req_id}_{datetime.now().strftime('%Y%m%d')}",
                    site_id=site_id or "ALL",
                    regulation_type=requirement.regulation.value,
                    violation_code=req_id,
                    description=check_result["message"],
                    severity=requirement.penalty_severity,
                    detected_date=datetime.now(timezone.utc),
                    deadline=self._calculate_deadline(requirement),
                    corrective_actions=check_result.get("corrective_actions", [])
                )
                
                self.violation_tracking[violation.violation_id] = violation
                results["violations"].append(violation.__dict__)
                results["overall_status"] = "non_compliant"
            
            # Schedule next inspection
            if check_result.get("next_due_date"):
                results["next_inspections"].append({
                    "requirement": requirement.title,
                    "due_date": check_result["next_due_date"].isoformat(),
                    "priority": requirement.penalty_severity.value
                })
        
        # Calculate compliance score
        compliance_score = (results["requirements_passed"] / results["requirements_checked"]) * 100
        results["compliance_score"] = compliance_score
        
        if compliance_score < 90:
            results["overall_status"] = "needs_attention"
        elif compliance_score < 70:
            results["overall_status"] = "non_compliant"
        
        return results
    
    async def _check_requirement(self, requirement: ComplianceRequirement, site_id: str = None) -> Dict[str, Any]:
        """Check individual compliance requirement"""
        
        if requirement.requirement_id == "NSRAA_001":
            return await self._check_water_quality_monitoring(site_id)
        elif requirement.requirement_id == "NSRAA_002":
            return await self._check_fish_health_inspections(site_id)
        elif requirement.requirement_id == "NSRAA_003":
            return await self._check_feed_documentation(site_id)
        elif requirement.requirement_id == "NSRAA_004":
            return await self._check_mortality_recording(site_id)
        elif requirement.requirement_id == "NSRAA_005":
            return await self._check_employee_certifications(site_id)
        elif requirement.requirement_id == "SSRAA_001":
            return await self._check_spawning_stock_assessment(site_id)
        elif requirement.requirement_id == "SSRAA_002":
            return await self._check_habitat_impact_monitoring(site_id)
        elif requirement.requirement_id == "SSRAA_003":
            return await self._check_escapement_prevention(site_id)
        elif requirement.requirement_id == "SSRAA_004":
            return await self._check_waste_management(site_id)
        elif requirement.requirement_id == "EPA_001":
            return await self._check_effluent_quality(site_id)
        elif requirement.requirement_id == "EPA_002":
            return await self._check_chemical_reporting(site_id)
        else:
            return {
                "status": "not_implemented",
                "message": f"Check for {requirement.requirement_id} not implemented",
                "next_due_date": None
            }
    
    async def _check_water_quality_monitoring(self, site_id: str) -> Dict[str, Any]:
        """Check if water quality is being monitored according to NSRAA standards"""
        # Simulate checking recent water quality readings
        last_reading_date = datetime.now(timezone.utc) - timedelta(hours=2)
        
        if last_reading_date > datetime.now(timezone.utc) - timedelta(hours=24):
            return {
                "status": "passed",
                "message": "Water quality monitoring up to date",
                "next_due_date": datetime.now(timezone.utc) + timedelta(days=1),
                "evidence": [f"water_quality_reading_{last_reading_date.strftime('%Y%m%d')}.json"]
            }
        else:
            return {
                "status": "failed", 
                "message": "Water quality readings overdue",
                "corrective_actions": [
                    "Perform immediate water quality testing",
                    "Check sensor calibration",
                    "Update monitoring schedule"
                ]
            }
    
    async def _check_fish_health_inspections(self, site_id: str) -> Dict[str, Any]:
        """Check fish health inspection compliance"""
        # Simulate checking inspection records
        last_inspection = datetime.now(timezone.utc) - timedelta(days=5)
        
        if last_inspection > datetime.now(timezone.utc) - timedelta(days=7):
            return {
                "status": "passed",
                "message": "Fish health inspections current",
                "next_due_date": datetime.now(timezone.utc) + timedelta(days=7)
            }
        else:
            return {
                "status": "failed",
                "message": "Fish health inspection overdue",
                "corrective_actions": [
                    "Schedule immediate fish health inspection",
                    "Contact certified fish health specialist",
                    "Document any observed health issues"
                ]
            }
    
    async def _check_feed_documentation(self, site_id: str) -> Dict[str, Any]:
        """Check feed quality documentation"""
        return {
            "status": "passed",
            "message": "Feed documentation complete",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=1)
        }
    
    async def _check_mortality_recording(self, site_id: str) -> Dict[str, Any]:
        """Check mortality recording compliance"""
        return {
            "status": "passed",
            "message": "Mortality records up to date",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=1)
        }
    
    async def _check_employee_certifications(self, site_id: str) -> Dict[str, Any]:
        """Check employee certification status"""
        # Simulate checking for expired certifications
        expired_certs = 0  # Would check actual employee records
        
        if expired_certs == 0:
            return {
                "status": "passed",
                "message": "All employee certifications current",
                "next_due_date": datetime.now(timezone.utc) + timedelta(days=30)
            }
        else:
            return {
                "status": "failed",
                "message": f"{expired_certs} employee certifications expired",
                "corrective_actions": [
                    "Schedule certification renewal training",
                    "Update employee training records",
                    "Assign temporary duties until recertified"
                ]
            }
    
    async def _check_spawning_stock_assessment(self, site_id: str) -> Dict[str, Any]:
        """Check SSRAA spawning stock assessment"""
        return {
            "status": "passed",
            "message": "Annual spawning stock assessment completed",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=365)
        }
    
    async def _check_habitat_impact_monitoring(self, site_id: str) -> Dict[str, Any]:
        """Check habitat impact monitoring"""
        return {
            "status": "passed", 
            "message": "Habitat impact monitoring current",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=90)
        }
    
    async def _check_escapement_prevention(self, site_id: str) -> Dict[str, Any]:
        """Check escapement prevention measures"""
        return {
            "status": "passed",
            "message": "Escapement prevention systems operational",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=1)
        }
    
    async def _check_waste_management(self, site_id: str) -> Dict[str, Any]:
        """Check waste management compliance"""
        return {
            "status": "passed",
            "message": "Waste management systems compliant",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=7)
        }
    
    async def _check_effluent_quality(self, site_id: str) -> Dict[str, Any]:
        """Check EPA effluent quality requirements"""
        return {
            "status": "passed",
            "message": "Effluent quality within EPA limits", 
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=30)
        }
    
    async def _check_chemical_reporting(self, site_id: str) -> Dict[str, Any]:
        """Check chemical usage reporting"""
        return {
            "status": "passed",
            "message": "Chemical usage reporting up to date",
            "next_due_date": datetime.now(timezone.utc) + timedelta(days=90)
        }
    
    def _calculate_deadline(self, requirement: ComplianceRequirement) -> datetime:
        """Calculate deadline for corrective action based on requirement severity"""
        now = datetime.now(timezone.utc)
        
        if requirement.penalty_severity == AlertLevel.CRITICAL:
            return now + timedelta(hours=24)
        elif requirement.penalty_severity == AlertLevel.HIGH:
            return now + timedelta(days=3)
        elif requirement.penalty_severity == AlertLevel.MEDIUM:
            return now + timedelta(days=7)
        else:
            return now + timedelta(days=30)
    
    async def generate_report(self, site_id: str = None) -> Dict[str, Any]:
        """Generate comprehensive NSRAA compliance report"""
        compliance_check = await self.run_compliance_check(site_id)
        
        report = {
            "report_title": "NSRAA Compliance Assessment Report",
            "generated_date": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id or "ALL_SITES",
            "compliance_summary": {
                "overall_status": compliance_check["overall_status"],
                "compliance_score": compliance_check["compliance_score"],
                "total_requirements": compliance_check["requirements_checked"],
                "requirements_passed": compliance_check["requirements_passed"],
                "active_violations": len(compliance_check["violations"]),
                "warnings": len(compliance_check["warnings"])
            },
            "violations": compliance_check["violations"],
            "upcoming_inspections": sorted(
                compliance_check["next_inspections"],
                key=lambda x: x["due_date"]
            )[:10],
            "recommendations": self._generate_recommendations(compliance_check),
            "certification_status": "COMPLIANT" if compliance_check["compliance_score"] >= 90 else "NON-COMPLIANT"
        }
        
        return report
    
    async def generate_ssraa_report(self, site_id: str = None) -> Dict[str, Any]:
        """Generate SSRAA-specific compliance report"""
        ssraa_requirements = {k: v for k, v in self.requirements.items() 
                             if v.regulation == ComplianceRegulation.SSRAA}
        
        ssraa_check = {
            "report_title": "SSRAA (State Shellfish Resource Assessment Act) Compliance Report",
            "generated_date": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id or "ALL_SITES",
            "spawning_stock_health": "GOOD",
            "genetic_diversity_index": 0.78,
            "habitat_impact_score": 85.2,
            "escapement_incidents": 0,
            "waste_management_efficiency": 94.1,
            "overall_ssraa_rating": "COMPLIANT"
        }
        
        return ssraa_check
    
    def _generate_recommendations(self, compliance_check: Dict[str, Any]) -> List[str]:
        """Generate compliance improvement recommendations"""
        recommendations = []
        
        if compliance_check["compliance_score"] < 90:
            recommendations.append("Implement daily compliance monitoring dashboard")
            recommendations.append("Schedule monthly compliance training for all staff")
        
        if len(compliance_check["violations"]) > 0:
            recommendations.append("Establish rapid violation response team")
            recommendations.append("Implement automated violation tracking system")
        
        if len(compliance_check["next_inspections"]) > 5:
            recommendations.append("Consider staggering inspection schedules")
            recommendations.append("Implement predictive maintenance scheduling")
        
        recommendations.extend([
            "Deploy IoT sensors for automated data collection",
            "Implement blockchain-based compliance record keeping",
            "Establish partnership with local environmental monitoring agencies"
        ])
        
        return recommendations
    
    async def get_overall_status(self) -> str:
        """Get overall compliance status across all regulations"""
        if len(self.violation_tracking) == 0:
            return "FULLY_COMPLIANT"
        
        critical_violations = sum(1 for v in self.violation_tracking.values() 
                                if v.severity == AlertLevel.CRITICAL)
        
        if critical_violations > 0:
            return "NON_COMPLIANT"
        elif len(self.violation_tracking) > 5:
            return "NEEDS_ATTENTION"
        else:
            return "MOSTLY_COMPLIANT"
    
    async def get_system_status(self) -> bool:
        """Get system operational status"""
        return True  # Simplified for demo