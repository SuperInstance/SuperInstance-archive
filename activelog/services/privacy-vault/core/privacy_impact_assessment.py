import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass
import hashlib
import uuid

logger = logging.getLogger(__name__)

class PIARiskLevel(Enum):
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class PIAStatus(Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_REVISION = "requires_revision"
    EXPIRED = "expired"

class ProcessingLawfulness(Enum):
    CONSENT = "consent"
    CONTRACT = "contract"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_TASK = "public_task"
    LEGITIMATE_INTERESTS = "legitimate_interests"

class DataCategory(Enum):
    PERSONAL_DATA = "personal_data"
    SENSITIVE_DATA = "sensitive_data"
    SPECIAL_CATEGORY = "special_category"
    CRIMINAL_DATA = "criminal_data"
    BIOMETRIC_DATA = "biometric_data"
    HEALTH_DATA = "health_data"
    FINANCIAL_DATA = "financial_data"

@dataclass
class PIAAssessment:
    pia_id: str
    project_name: str
    data_controller: str
    data_processor: Optional[str]
    processing_purpose: str
    lawful_basis: ProcessingLawfulness
    data_categories: List[DataCategory]
    data_subjects: List[str]
    processing_operations: List[str]
    data_sources: List[str]
    data_recipients: List[str]
    retention_period: str
    international_transfers: bool
    transfer_safeguards: Optional[str]
    risk_level: PIARiskLevel
    mitigation_measures: List[str]
    residual_risks: List[str]
    status: PIAStatus
    assessor: str
    reviewer: Optional[str]
    created_date: datetime
    review_date: Optional[datetime]
    approval_date: Optional[datetime]
    expiry_date: Optional[datetime]
    version: str
    comments: List[str]
    technical_measures: List[str]
    organizational_measures: List[str]
    dpia_required: bool
    consultation_required: bool
    authority_consultation_date: Optional[datetime]

@dataclass
class RiskAssessment:
    risk_id: str
    risk_description: str
    likelihood: PIARiskLevel
    impact: PIARiskLevel
    overall_risk: PIARiskLevel
    affected_rights: List[str]
    risk_sources: List[str]
    existing_controls: List[str]
    mitigation_measures: List[str]
    residual_likelihood: PIARiskLevel
    residual_impact: PIARiskLevel
    residual_risk: PIARiskLevel
    risk_owner: str
    review_date: datetime

@dataclass
class PIATemplate:
    template_id: str
    template_name: str
    description: str
    applicable_scenarios: List[str]
    required_sections: List[str]
    risk_criteria: Dict[str, Any]
    compliance_requirements: List[str]
    review_frequency: int  # days
    created_date: datetime
    updated_date: datetime

class PrivacyImpactAssessmentManager:
    def __init__(self):
        self.assessments: Dict[str, PIAAssessment] = {}
        self.risk_assessments: Dict[str, List[RiskAssessment]] = {}
        self.templates: Dict[str, PIATemplate] = {}
        self.risk_matrix = self._initialize_risk_matrix()
        self.dpia_thresholds = self._initialize_dpia_thresholds()
        logger.info("Privacy Impact Assessment Manager initialized")

    async def initialize(self):
        await self._create_default_templates()
        await self._load_regulatory_requirements()
        logger.info("PIA Manager initialization completed")

    def _initialize_risk_matrix(self) -> Dict[str, Dict[str, PIARiskLevel]]:
        return {
            "minimal": {
                "minimal": PIARiskLevel.MINIMAL,
                "low": PIARiskLevel.MINIMAL,
                "medium": PIARiskLevel.LOW,
                "high": PIARiskLevel.MEDIUM,
                "very_high": PIARiskLevel.HIGH
            },
            "low": {
                "minimal": PIARiskLevel.MINIMAL,
                "low": PIARiskLevel.LOW,
                "medium": PIARiskLevel.MEDIUM,
                "high": PIARiskLevel.HIGH,
                "very_high": PIARiskLevel.VERY_HIGH
            },
            "medium": {
                "minimal": PIARiskLevel.LOW,
                "low": PIARiskLevel.MEDIUM,
                "medium": PIARiskLevel.MEDIUM,
                "high": PIARiskLevel.HIGH,
                "very_high": PIARiskLevel.VERY_HIGH
            },
            "high": {
                "minimal": PIARiskLevel.MEDIUM,
                "low": PIARiskLevel.HIGH,
                "medium": PIARiskLevel.HIGH,
                "high": PIARiskLevel.VERY_HIGH,
                "very_high": PIARiskLevel.VERY_HIGH
            },
            "very_high": {
                "minimal": PIARiskLevel.HIGH,
                "low": PIARiskLevel.VERY_HIGH,
                "medium": PIARiskLevel.VERY_HIGH,
                "high": PIARiskLevel.VERY_HIGH,
                "very_high": PIARiskLevel.VERY_HIGH
            }
        }

    def _initialize_dpia_thresholds(self) -> Dict[str, Any]:
        return {
            "automatic_triggers": [
                "systematic_monitoring",
                "large_scale_processing",
                "special_category_data",
                "vulnerable_individuals",
                "innovative_technology",
                "automated_decision_making",
                "biometric_identification",
                "genetic_data_processing",
                "location_tracking",
                "behavioral_profiling"
            ],
            "high_risk_combinations": [
                ["sensitive_data", "international_transfers"],
                ["automated_decisions", "significant_effects"],
                ["large_scale", "special_category"],
                ["vulnerable_subjects", "profiling"]
            ]
        }

    async def _create_default_templates(self):
        templates = [
            PIATemplate(
                template_id="gdpr_standard",
                template_name="GDPR Standard PIA Template",
                description="Standard template for GDPR compliance",
                applicable_scenarios=["eu_processing", "personal_data", "gdpr_scope"],
                required_sections=[
                    "data_description", "processing_purpose", "lawful_basis",
                    "necessity_proportionality", "risk_assessment", "mitigation_measures"
                ],
                risk_criteria={"requires_dpia": True, "consultation_threshold": "high"},
                compliance_requirements=["GDPR Article 35", "ICO Guidelines"],
                review_frequency=365,
                created_date=datetime.now(),
                updated_date=datetime.now()
            ),
            PIATemplate(
                template_id="ccpa_standard",
                template_name="CCPA Privacy Assessment Template",
                description="Template for California Consumer Privacy Act compliance",
                applicable_scenarios=["california_residents", "consumer_data", "ccpa_scope"],
                required_sections=[
                    "consumer_rights", "data_categories", "business_purposes",
                    "third_party_sharing", "security_measures"
                ],
                risk_criteria={"sale_disclosure": True, "sensitive_data_check": True},
                compliance_requirements=["CCPA Section 1798.100", "CPRA Requirements"],
                review_frequency=180,
                created_date=datetime.now(),
                updated_date=datetime.now()
            ),
            PIATemplate(
                template_id="hipaa_healthcare",
                template_name="HIPAA Healthcare PIA Template",
                description="Template for healthcare data processing under HIPAA",
                applicable_scenarios=["healthcare_data", "phi_processing", "hipaa_scope"],
                required_sections=[
                    "phi_categories", "minimum_necessary", "safeguards",
                    "breach_procedures", "business_associates"
                ],
                risk_criteria={"phi_involved": True, "breach_risk": "high"},
                compliance_requirements=["HIPAA Privacy Rule", "HIPAA Security Rule"],
                review_frequency=180,
                created_date=datetime.now(),
                updated_date=datetime.now()
            )
        ]
        
        for template in templates:
            self.templates[template.template_id] = template
            logger.info(f"Created PIA template: {template.template_name}")

    async def _load_regulatory_requirements(self):
        self.regulatory_requirements = {
            "gdpr": {
                "dpia_required_scenarios": [
                    "systematic_extensive_evaluation",
                    "large_scale_special_category",
                    "systematic_public_monitoring"
                ],
                "consultation_required": ["high_residual_risk"],
                "review_period": 730  # 2 years
            },
            "ccpa": {
                "assessment_triggers": ["sensitive_personal_information", "sale_of_data"],
                "consumer_notice_required": True,
                "review_period": 365
            },
            "hipaa": {
                "assessment_required": ["phi_processing", "new_technology"],
                "minimum_necessary_check": True,
                "review_period": 180
            }
        }
        logger.info("Loaded regulatory requirements for PIA")

    async def create_pia_assessment(
        self,
        project_name: str,
        data_controller: str,
        processing_purpose: str,
        lawful_basis: ProcessingLawfulness,
        data_categories: List[DataCategory],
        data_subjects: List[str],
        processing_operations: List[str],
        assessor: str,
        template_id: Optional[str] = None
    ) -> str:
        pia_id = f"pia_{uuid.uuid4().hex[:8]}"
        
        # Check if DPIA is required
        dpia_required = await self._assess_dpia_requirement(
            data_categories, processing_operations, data_subjects
        )
        
        # Calculate initial risk level
        initial_risk = await self._calculate_initial_risk(
            data_categories, processing_operations, data_subjects
        )
        
        assessment = PIAAssessment(
            pia_id=pia_id,
            project_name=project_name,
            data_controller=data_controller,
            data_processor=None,
            processing_purpose=processing_purpose,
            lawful_basis=lawful_basis,
            data_categories=data_categories,
            data_subjects=data_subjects,
            processing_operations=processing_operations,
            data_sources=[],
            data_recipients=[],
            retention_period="",
            international_transfers=False,
            transfer_safeguards=None,
            risk_level=initial_risk,
            mitigation_measures=[],
            residual_risks=[],
            status=PIAStatus.DRAFT,
            assessor=assessor,
            reviewer=None,
            created_date=datetime.now(),
            review_date=None,
            approval_date=None,
            expiry_date=None,
            version="1.0",
            comments=[],
            technical_measures=[],
            organizational_measures=[],
            dpia_required=dpia_required,
            consultation_required=False,
            authority_consultation_date=None
        )
        
        self.assessments[pia_id] = assessment
        logger.info(f"Created PIA assessment: {pia_id} for project: {project_name}")
        
        return pia_id

    async def _assess_dpia_requirement(
        self,
        data_categories: List[DataCategory],
        processing_operations: List[str],
        data_subjects: List[str]
    ) -> bool:
        triggers = []
        
        # Check for special category data
        if any(cat in [DataCategory.SENSITIVE_DATA, DataCategory.SPECIAL_CATEGORY,
                      DataCategory.BIOMETRIC_DATA, DataCategory.HEALTH_DATA]
               for cat in data_categories):
            triggers.append("special_category_data")
        
        # Check for systematic monitoring
        if any(op in ["profiling", "tracking", "monitoring", "surveillance"]
               for op in processing_operations):
            triggers.append("systematic_monitoring")
        
        # Check for vulnerable individuals
        if any(subj in ["children", "elderly", "patients", "employees"]
               for subj in data_subjects):
            triggers.append("vulnerable_individuals")
        
        # Check for large scale (simplified check)
        if len(data_subjects) > 100 or "large_scale" in processing_operations:
            triggers.append("large_scale_processing")
        
        # Check for innovative technology
        if any(op in ["ai", "machine_learning", "automated_decision", "biometric"]
               for op in processing_operations):
            triggers.append("innovative_technology")
        
        # DPIA required if any automatic trigger is present
        return len(triggers) > 0

    async def _calculate_initial_risk(
        self,
        data_categories: List[DataCategory],
        processing_operations: List[str],
        data_subjects: List[str]
    ) -> PIARiskLevel:
        risk_factors = 0
        
        # Data sensitivity scoring
        high_risk_categories = [
            DataCategory.SENSITIVE_DATA, DataCategory.SPECIAL_CATEGORY,
            DataCategory.BIOMETRIC_DATA, DataCategory.HEALTH_DATA,
            DataCategory.FINANCIAL_DATA, DataCategory.CRIMINAL_DATA
        ]
        
        if any(cat in high_risk_categories for cat in data_categories):
            risk_factors += 3
        elif DataCategory.PERSONAL_DATA in data_categories:
            risk_factors += 1
        
        # Processing operations scoring
        high_risk_operations = [
            "profiling", "automated_decision", "tracking", "monitoring",
            "ai_processing", "biometric_identification", "behavioral_analysis"
        ]
        
        for operation in processing_operations:
            if operation in high_risk_operations:
                risk_factors += 2
            elif operation in ["collection", "storage", "analysis"]:
                risk_factors += 1
        
        # Data subjects scoring
        vulnerable_subjects = ["children", "elderly", "patients", "disabled"]
        if any(subj in vulnerable_subjects for subj in data_subjects):
            risk_factors += 2
        
        # Convert to risk level
        if risk_factors >= 8:
            return PIARiskLevel.VERY_HIGH
        elif risk_factors >= 6:
            return PIARiskLevel.HIGH
        elif risk_factors >= 4:
            return PIARiskLevel.MEDIUM
        elif risk_factors >= 2:
            return PIARiskLevel.LOW
        else:
            return PIARiskLevel.MINIMAL

    async def conduct_risk_assessment(
        self,
        pia_id: str,
        risks: List[Dict[str, Any]]
    ) -> List[str]:
        if pia_id not in self.assessments:
            raise ValueError(f"PIA assessment {pia_id} not found")
        
        risk_ids = []
        risk_assessments = []
        
        for risk_data in risks:
            risk_id = f"risk_{uuid.uuid4().hex[:8]}"
            
            # Calculate overall risk using risk matrix
            likelihood = PIARiskLevel(risk_data.get("likelihood", "medium"))
            impact = PIARiskLevel(risk_data.get("impact", "medium"))
            overall_risk = self.risk_matrix[likelihood.value][impact.value]
            
            # Apply mitigation measures
            mitigation_measures = risk_data.get("mitigation_measures", [])
            residual_likelihood, residual_impact = await self._calculate_residual_risk(
                likelihood, impact, mitigation_measures
            )
            residual_risk = self.risk_matrix[residual_likelihood.value][residual_impact.value]
            
            risk_assessment = RiskAssessment(
                risk_id=risk_id,
                risk_description=risk_data.get("description", ""),
                likelihood=likelihood,
                impact=impact,
                overall_risk=overall_risk,
                affected_rights=risk_data.get("affected_rights", []),
                risk_sources=risk_data.get("risk_sources", []),
                existing_controls=risk_data.get("existing_controls", []),
                mitigation_measures=mitigation_measures,
                residual_likelihood=residual_likelihood,
                residual_impact=residual_impact,
                residual_risk=residual_risk,
                risk_owner=risk_data.get("risk_owner", ""),
                review_date=datetime.now() + timedelta(days=90)
            )
            
            risk_assessments.append(risk_assessment)
            risk_ids.append(risk_id)
        
        self.risk_assessments[pia_id] = risk_assessments
        
        # Update PIA with highest residual risk
        highest_risk = max([r.residual_risk for r in risk_assessments],
                          default=PIARiskLevel.MINIMAL)
        self.assessments[pia_id].risk_level = highest_risk
        
        # Determine if consultation is required
        if highest_risk in [PIARiskLevel.HIGH, PIARiskLevel.VERY_HIGH]:
            self.assessments[pia_id].consultation_required = True
        
        logger.info(f"Conducted risk assessment for PIA {pia_id}: {len(risks)} risks assessed")
        return risk_ids

    async def _calculate_residual_risk(
        self,
        likelihood: PIARiskLevel,
        impact: PIARiskLevel,
        mitigation_measures: List[str]
    ) -> tuple[PIARiskLevel, PIARiskLevel]:
        # Simple mitigation effectiveness calculation
        effectiveness_map = {
            "encryption": 2, "access_controls": 2, "anonymization": 3,
            "pseudonymization": 2, "data_minimization": 1, "regular_audits": 1,
            "staff_training": 1, "incident_procedures": 1, "backup_systems": 1
        }
        
        total_effectiveness = sum(
            effectiveness_map.get(measure, 0) for measure in mitigation_measures
        )
        
        # Reduce likelihood and impact based on mitigation effectiveness
        risk_levels = [PIARiskLevel.MINIMAL, PIARiskLevel.LOW, PIARiskLevel.MEDIUM, 
                      PIARiskLevel.HIGH, PIARiskLevel.VERY_HIGH]
        
        likelihood_idx = risk_levels.index(likelihood)
        impact_idx = risk_levels.index(impact)
        
        # Apply mitigation reduction (max 2 levels down)
        likelihood_reduction = min(total_effectiveness // 3, 2)
        impact_reduction = min(total_effectiveness // 4, 2)
        
        residual_likelihood_idx = max(0, likelihood_idx - likelihood_reduction)
        residual_impact_idx = max(0, impact_idx - impact_reduction)
        
        return risk_levels[residual_likelihood_idx], risk_levels[residual_impact_idx]

    async def submit_for_review(self, pia_id: str, reviewer: str) -> bool:
        if pia_id not in self.assessments:
            raise ValueError(f"PIA assessment {pia_id} not found")
        
        assessment = self.assessments[pia_id]
        
        if assessment.status != PIAStatus.DRAFT:
            raise ValueError(f"PIA {pia_id} is not in draft status")
        
        # Validate completeness
        validation_results = await self._validate_assessment_completeness(assessment)
        if not validation_results["complete"]:
            missing_sections = validation_results["missing_sections"]
            raise ValueError(f"PIA incomplete. Missing: {', '.join(missing_sections)}")
        
        assessment.status = PIAStatus.IN_REVIEW
        assessment.reviewer = reviewer
        assessment.review_date = datetime.now()
        
        logger.info(f"Submitted PIA {pia_id} for review by {reviewer}")
        return True

    async def _validate_assessment_completeness(self, assessment: PIAAssessment) -> Dict[str, Any]:
        missing_sections = []
        
        required_fields = {
            "processing_purpose": assessment.processing_purpose,
            "lawful_basis": assessment.lawful_basis,
            "data_categories": assessment.data_categories,
            "data_subjects": assessment.data_subjects,
            "processing_operations": assessment.processing_operations,
            "retention_period": assessment.retention_period
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value or (isinstance(field_value, list) and len(field_value) == 0):
                missing_sections.append(field_name)
        
        # Check if risk assessment is conducted
        if assessment.pia_id not in self.risk_assessments:
            missing_sections.append("risk_assessment")
        
        # Check if mitigation measures are provided for high-risk assessments
        if assessment.risk_level in [PIARiskLevel.HIGH, PIARiskLevel.VERY_HIGH]:
            if not assessment.mitigation_measures:
                missing_sections.append("mitigation_measures")
        
        return {
            "complete": len(missing_sections) == 0,
            "missing_sections": missing_sections,
            "completeness_score": max(0, 100 - (len(missing_sections) * 15))
        }

    async def approve_assessment(self, pia_id: str, approver: str, comments: str = "") -> bool:
        if pia_id not in self.assessments:
            raise ValueError(f"PIA assessment {pia_id} not found")
        
        assessment = self.assessments[pia_id]
        
        if assessment.status != PIAStatus.IN_REVIEW:
            raise ValueError(f"PIA {pia_id} is not under review")
        
        assessment.status = PIAStatus.APPROVED
        assessment.approval_date = datetime.now()
        
        # Set expiry date based on template or default (1 year)
        template = self.templates.get("gdpr_standard")  # Default template
        review_frequency = template.review_frequency if template else 365
        assessment.expiry_date = datetime.now() + timedelta(days=review_frequency)
        
        if comments:
            assessment.comments.append(f"Approved by {approver}: {comments}")
        
        logger.info(f"Approved PIA {pia_id} by {approver}")
        return True

    async def get_assessment(self, pia_id: str) -> Optional[PIAAssessment]:
        return self.assessments.get(pia_id)

    async def list_assessments(
        self,
        status: Optional[PIAStatus] = None,
        risk_level: Optional[PIARiskLevel] = None,
        expired_only: bool = False
    ) -> List[PIAAssessment]:
        assessments = list(self.assessments.values())
        
        if status:
            assessments = [a for a in assessments if a.status == status]
        
        if risk_level:
            assessments = [a for a in assessments if a.risk_level == risk_level]
        
        if expired_only:
            now = datetime.now()
            assessments = [a for a in assessments 
                          if a.expiry_date and a.expiry_date < now]
        
        return sorted(assessments, key=lambda a: a.created_date, reverse=True)

    async def generate_pia_report(self, pia_id: str) -> Dict[str, Any]:
        if pia_id not in self.assessments:
            raise ValueError(f"PIA assessment {pia_id} not found")
        
        assessment = self.assessments[pia_id]
        risks = self.risk_assessments.get(pia_id, [])
        
        report = {
            "assessment_summary": {
                "pia_id": assessment.pia_id,
                "project_name": assessment.project_name,
                "status": assessment.status.value,
                "risk_level": assessment.risk_level.value,
                "dpia_required": assessment.dpia_required,
                "consultation_required": assessment.consultation_required,
                "created_date": assessment.created_date.isoformat(),
                "assessor": assessment.assessor,
                "reviewer": assessment.reviewer
            },
            "processing_details": {
                "data_controller": assessment.data_controller,
                "processing_purpose": assessment.processing_purpose,
                "lawful_basis": assessment.lawful_basis.value,
                "data_categories": [cat.value for cat in assessment.data_categories],
                "data_subjects": assessment.data_subjects,
                "processing_operations": assessment.processing_operations,
                "retention_period": assessment.retention_period
            },
            "risk_analysis": {
                "total_risks": len(risks),
                "risk_breakdown": self._get_risk_breakdown(risks),
                "highest_residual_risk": assessment.risk_level.value,
                "mitigation_measures": assessment.mitigation_measures
            },
            "compliance_status": {
                "gdpr_compliant": self._check_gdpr_compliance(assessment),
                "ccpa_compliant": self._check_ccpa_compliance(assessment),
                "completeness_score": (await self._validate_assessment_completeness(assessment))["completeness_score"]
            },
            "recommendations": await self._generate_recommendations(assessment, risks)
        }
        
        return report

    def _get_risk_breakdown(self, risks: List[RiskAssessment]) -> Dict[str, int]:
        breakdown = {level.value: 0 for level in PIARiskLevel}
        for risk in risks:
            breakdown[risk.residual_risk.value] += 1
        return breakdown

    def _check_gdpr_compliance(self, assessment: PIAAssessment) -> bool:
        checks = []
        
        # DPIA requirement check
        if assessment.dpia_required:
            checks.append(assessment.status in [PIAStatus.APPROVED, PIAStatus.IN_REVIEW])
        
        # Lawful basis check
        checks.append(assessment.lawful_basis is not None)
        
        # High-risk consultation check
        if assessment.risk_level in [PIARiskLevel.HIGH, PIARiskLevel.VERY_HIGH]:
            checks.append(assessment.consultation_required)
        
        return all(checks)

    def _check_ccpa_compliance(self, assessment: PIAAssessment) -> bool:
        # Simplified CCPA compliance check
        return (
            bool(assessment.processing_purpose) and
            bool(assessment.data_categories) and
            bool(assessment.retention_period)
        )

    async def _generate_recommendations(
        self,
        assessment: PIAAssessment,
        risks: List[RiskAssessment]
    ) -> List[str]:
        recommendations = []
        
        # Risk-based recommendations
        high_risks = [r for r in risks if r.residual_risk in [PIARiskLevel.HIGH, PIARiskLevel.VERY_HIGH]]
        if high_risks:
            recommendations.append("Consider additional mitigation measures for high-risk areas")
            recommendations.append("Implement regular monitoring and review procedures")
        
        # Data category recommendations
        if DataCategory.SPECIAL_CATEGORY in assessment.data_categories:
            recommendations.append("Ensure explicit consent or valid legal basis for special category data")
            recommendations.append("Implement enhanced security measures for sensitive data")
        
        # Processing operation recommendations
        if "automated_decision" in assessment.processing_operations:
            recommendations.append("Provide meaningful information about automated decision-making")
            recommendations.append("Implement human review processes for automated decisions")
        
        # International transfer recommendations
        if assessment.international_transfers:
            recommendations.append("Verify adequacy decisions or implement appropriate safeguards")
            recommendations.append("Document transfer impact assessments where required")
        
        # Retention recommendations
        if not assessment.retention_period:
            recommendations.append("Define clear data retention periods based on processing purposes")
        
        return recommendations

    async def schedule_pia_reviews(self) -> List[str]:
        now = datetime.now()
        due_for_review = []
        
        for pia_id, assessment in self.assessments.items():
            if assessment.status == PIAStatus.APPROVED and assessment.expiry_date:
                days_until_expiry = (assessment.expiry_date - now).days
                
                # Schedule review 30 days before expiry
                if 0 <= days_until_expiry <= 30:
                    due_for_review.append(pia_id)
                    logger.info(f"PIA {pia_id} due for review in {days_until_expiry} days")
        
        return due_for_review

    async def export_assessment_data(self, format: str = "json") -> Dict[str, Any]:
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_assessments": len(self.assessments),
            "assessments": {},
            "risk_assessments": {},
            "templates": {}
        }
        
        # Export assessments
        for pia_id, assessment in self.assessments.items():
            export_data["assessments"][pia_id] = {
                "pia_id": assessment.pia_id,
                "project_name": assessment.project_name,
                "status": assessment.status.value,
                "risk_level": assessment.risk_level.value,
                "created_date": assessment.created_date.isoformat(),
                "dpia_required": assessment.dpia_required
            }
        
        # Export risk assessments
        for pia_id, risks in self.risk_assessments.items():
            export_data["risk_assessments"][pia_id] = [
                {
                    "risk_id": r.risk_id,
                    "description": r.risk_description,
                    "overall_risk": r.overall_risk.value,
                    "residual_risk": r.residual_risk.value
                }
                for r in risks
            ]
        
        # Export templates
        for template_id, template in self.templates.items():
            export_data["templates"][template_id] = {
                "template_name": template.template_name,
                "description": template.description,
                "applicable_scenarios": template.applicable_scenarios
            }
        
        logger.info(f"Exported PIA data: {len(self.assessments)} assessments")
        return export_data