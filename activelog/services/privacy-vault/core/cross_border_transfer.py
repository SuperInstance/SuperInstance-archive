import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass
import hashlib
import uuid

logger = logging.getLogger(__name__)

class TransferMechanism(Enum):
    ADEQUACY_DECISION = "adequacy_decision"
    STANDARD_CONTRACTUAL_CLAUSES = "standard_contractual_clauses"
    BINDING_CORPORATE_RULES = "binding_corporate_rules"
    CERTIFICATION = "certification"
    CODES_OF_CONDUCT = "codes_of_conduct"
    DEROGATIONS = "derogations"
    APPROVED_TRANSFER_SCHEME = "approved_transfer_scheme"

class TransferStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    UNDER_REVIEW = "under_review"
    EXPIRED = "expired"

class AdequacyStatus(Enum):
    ADEQUATE = "adequate"
    PARTIALLY_ADEQUATE = "partially_adequate"
    NOT_ADEQUATE = "not_adequate"
    UNDER_ASSESSMENT = "under_assessment"
    SUSPENDED = "suspended"

class TransferRiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class DerogationType(Enum):
    EXPLICIT_CONSENT = "explicit_consent"
    CONTRACT_PERFORMANCE = "contract_performance"
    PUBLIC_INTEREST = "public_interest"
    LEGAL_CLAIMS = "legal_claims"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_REGISTER = "public_register"
    COMPELLING_LEGITIMATE_INTERESTS = "compelling_legitimate_interests"

@dataclass
class CountryAdequacy:
    country_code: str
    country_name: str
    adequacy_status: AdequacyStatus
    adequacy_decision_date: Optional[datetime]
    adequacy_expiry_date: Optional[datetime]
    partial_adequacy_sectors: List[str]
    restrictions: List[str]
    monitoring_authority: Optional[str]
    last_assessment_date: datetime
    next_review_date: Optional[datetime]
    risk_factors: List[str]
    safeguard_requirements: List[str]

@dataclass
class TransferAssessment:
    assessment_id: str
    transfer_id: str
    origin_country: str
    destination_country: str
    data_categories: List[str]
    data_volume: int
    transfer_frequency: str
    processing_purpose: str
    data_subjects: List[str]
    risk_level: TransferRiskLevel
    risk_factors: List[str]
    mitigation_measures: List[str]
    safeguards_required: List[str]
    legal_basis_required: List[TransferMechanism]
    assessor: str
    assessment_date: datetime
    review_date: datetime
    approval_required: bool
    authority_consultation: bool

@dataclass
class TransferRecord:
    transfer_id: str
    data_exporter: str
    data_importer: str
    origin_country: str
    destination_country: str
    transfer_mechanism: TransferMechanism
    transfer_date: datetime
    data_categories: List[str]
    data_subjects_count: int
    processing_purpose: str
    retention_period: str
    safeguards_applied: List[str]
    legal_basis: str
    contract_reference: Optional[str]
    approval_reference: Optional[str]
    status: TransferStatus
    expiry_date: Optional[datetime]
    monitoring_required: bool
    last_review_date: Optional[datetime]
    next_review_date: Optional[datetime]
    compliance_checks: List[str]
    breach_incidents: List[str]

@dataclass
class StandardContractualClauses:
    scc_id: str
    scc_version: str
    effective_date: datetime
    expiry_date: Optional[datetime]
    applicable_scenarios: List[str]
    controller_to_controller: bool
    controller_to_processor: bool
    processor_to_processor: bool
    additional_safeguards: List[str]
    docking_clause: bool
    modules_used: List[str]

@dataclass
class TransferImpactAssessment:
    tia_id: str
    transfer_id: str
    destination_country: str
    government_access_laws: Dict[str, Any]
    surveillance_programs: List[str]
    legal_remedies: List[str]
    independence_adequacy: str
    enforcement_record: str
    additional_safeguards: List[str]
    residual_risks: List[str]
    risk_mitigation: List[str]
    conclusion: str
    assessor: str
    assessment_date: datetime
    review_required: bool

class CrossBorderTransferManager:
    def __init__(self):
        self.adequacy_decisions: Dict[str, CountryAdequacy] = {}
        self.transfer_records: Dict[str, TransferRecord] = {}
        self.transfer_assessments: Dict[str, TransferAssessment] = {}
        self.impact_assessments: Dict[str, TransferImpactAssessment] = {}
        self.scc_templates: Dict[str, StandardContractualClauses] = {}
        self.derogation_tracker: Dict[str, List[Dict]] = {}
        logger.info("Cross-Border Transfer Manager initialized")

    async def initialize(self):
        await self._load_adequacy_decisions()
        await self._load_scc_templates()
        await self._initialize_country_risk_profiles()
        logger.info("Cross-Border Transfer Manager initialization completed")

    async def _load_adequacy_decisions(self):
        # European Commission adequacy decisions (as of 2024)
        adequacy_data = [
            {
                "country_code": "GB",
                "country_name": "United Kingdom",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2021, 6, 28),
                "expiry_date": datetime(2025, 6, 27),  # Subject to review
                "restrictions": ["government_access_concerns"],
                "monitoring_authority": "ICO"
            },
            {
                "country_code": "CH",
                "country_name": "Switzerland",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2000, 7, 26),
                "expiry_date": None,
                "restrictions": [],
                "monitoring_authority": "FDPIC"
            },
            {
                "country_code": "IL",
                "country_name": "Israel",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2011, 1, 31),
                "expiry_date": None,
                "restrictions": [],
                "monitoring_authority": "ILITA"
            },
            {
                "country_code": "NZ",
                "country_name": "New Zealand",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2013, 4, 19),
                "expiry_date": None,
                "restrictions": [],
                "monitoring_authority": "OPC"
            },
            {
                "country_code": "UY",
                "country_name": "Uruguay",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2012, 8, 21),
                "expiry_date": None,
                "restrictions": [],
                "monitoring_authority": "URCDP"
            },
            {
                "country_code": "KR",
                "country_name": "South Korea",
                "status": AdequacyStatus.ADEQUATE,
                "decision_date": datetime(2021, 12, 17),
                "expiry_date": datetime(2025, 12, 16),
                "restrictions": [],
                "monitoring_authority": "PIPC"
            },
            {
                "country_code": "US",
                "country_name": "United States",
                "status": AdequacyStatus.NOT_ADEQUATE,
                "decision_date": None,
                "expiry_date": None,
                "restrictions": ["government_surveillance", "fisa_702", "executive_order_12333"],
                "monitoring_authority": None
            },
            {
                "country_code": "CN",
                "country_name": "China",
                "status": AdequacyStatus.NOT_ADEQUATE,
                "decision_date": None,
                "expiry_date": None,
                "restrictions": ["cybersecurity_law", "data_localization", "government_access"],
                "monitoring_authority": "CAC"
            },
            {
                "country_code": "RU",
                "country_name": "Russia",
                "status": AdequacyStatus.NOT_ADEQUATE,
                "decision_date": None,
                "expiry_date": None,
                "restrictions": ["data_localization_law", "government_surveillance"],
                "monitoring_authority": "Roskomnadzor"
            },
            {
                "country_code": "IN",
                "country_name": "India",
                "status": AdequacyStatus.UNDER_ASSESSMENT,
                "decision_date": None,
                "expiry_date": None,
                "restrictions": ["proposed_data_localization"],
                "monitoring_authority": "Proposed_DPA"
            }
        ]
        
        for data in adequacy_data:
            country = CountryAdequacy(
                country_code=data["country_code"],
                country_name=data["country_name"],
                adequacy_status=data["status"],
                adequacy_decision_date=data.get("decision_date"),
                adequacy_expiry_date=data.get("expiry_date"),
                partial_adequacy_sectors=[],
                restrictions=data.get("restrictions", []),
                monitoring_authority=data.get("monitoring_authority"),
                last_assessment_date=datetime.now() - timedelta(days=30),
                next_review_date=data.get("expiry_date"),
                risk_factors=data.get("restrictions", []),
                safeguard_requirements=self._get_safeguard_requirements(data["status"])
            )
            
            self.adequacy_decisions[data["country_code"]] = country
        
        logger.info(f"Loaded {len(self.adequacy_decisions)} adequacy decisions")

    def _get_safeguard_requirements(self, status: AdequacyStatus) -> List[str]:
        if status == AdequacyStatus.ADEQUATE:
            return ["standard_monitoring", "breach_notification"]
        elif status == AdequacyStatus.NOT_ADEQUATE:
            return [
                "transfer_impact_assessment", "additional_safeguards",
                "encryption_in_transit", "encryption_at_rest",
                "data_minimization", "access_controls", "audit_logging"
            ]
        else:
            return ["enhanced_monitoring", "legal_review"]

    async def _load_scc_templates(self):
        # EU Standard Contractual Clauses (2021 version)
        scc_2021 = StandardContractualClauses(
            scc_id="eu_scc_2021",
            scc_version="2021/914",
            effective_date=datetime(2021, 6, 27),
            expiry_date=None,
            applicable_scenarios=["third_country_transfers"],
            controller_to_controller=True,
            controller_to_processor=True,
            processor_to_processor=True,
            additional_safeguards=[
                "encryption", "pseudonymization", "access_controls",
                "audit_logging", "data_minimization"
            ],
            docking_clause=True,
            modules_used=["module_1", "module_2", "module_3"]
        )
        
        self.scc_templates["eu_scc_2021"] = scc_2021
        logger.info("Loaded SCC templates")

    async def _initialize_country_risk_profiles(self):
        self.country_risk_profiles = {
            "US": {
                "surveillance_laws": ["FISA_702", "Executive_Order_12333", "PATRIOT_Act"],
                "government_access": "HIGH",
                "legal_remedies": ["judicial_review", "congressional_oversight"],
                "enforcement_independence": "MEDIUM"
            },
            "CN": {
                "surveillance_laws": ["Cybersecurity_Law", "National_Intelligence_Law"],
                "government_access": "VERY_HIGH",
                "legal_remedies": ["limited"],
                "enforcement_independence": "LOW"
            },
            "RU": {
                "surveillance_laws": ["Data_Localization_Law", "SORM"],
                "government_access": "VERY_HIGH",
                "legal_remedies": ["limited"],
                "enforcement_independence": "LOW"
            }
        }
        logger.info("Initialized country risk profiles")

    async def assess_transfer_requirements(
        self,
        origin_country: str,
        destination_country: str,
        data_categories: List[str],
        processing_purpose: str,
        data_volume: int
    ) -> TransferAssessment:
        assessment_id = f"ta_{uuid.uuid4().hex[:8]}"
        
        # Check adequacy status
        adequacy_info = self.adequacy_decisions.get(destination_country)
        
        # Assess risk level
        risk_level = await self._assess_transfer_risk(
            destination_country, data_categories, data_volume
        )
        
        # Determine required safeguards
        safeguards_required = await self._determine_required_safeguards(
            destination_country, data_categories, risk_level
        )
        
        # Determine legal basis options
        legal_basis_options = await self._determine_legal_basis_options(
            destination_country, adequacy_info, risk_level
        )
        
        # Identify risk factors
        risk_factors = await self._identify_risk_factors(
            destination_country, data_categories, processing_purpose
        )
        
        assessment = TransferAssessment(
            assessment_id=assessment_id,
            transfer_id="",  # Will be set when transfer is created
            origin_country=origin_country,
            destination_country=destination_country,
            data_categories=data_categories,
            data_volume=data_volume,
            transfer_frequency="",  # To be specified
            processing_purpose=processing_purpose,
            data_subjects=[],  # To be specified
            risk_level=risk_level,
            risk_factors=risk_factors,
            mitigation_measures=[],
            safeguards_required=safeguards_required,
            legal_basis_required=legal_basis_options,
            assessor="system",
            assessment_date=datetime.now(),
            review_date=datetime.now() + timedelta(days=365),
            approval_required=risk_level in [TransferRiskLevel.HIGH, TransferRiskLevel.VERY_HIGH],
            authority_consultation=risk_level == TransferRiskLevel.VERY_HIGH
        )
        
        self.transfer_assessments[assessment_id] = assessment
        logger.info(f"Created transfer assessment {assessment_id} for {origin_country} -> {destination_country}")
        
        return assessment

    async def _assess_transfer_risk(
        self,
        destination_country: str,
        data_categories: List[str],
        data_volume: int
    ) -> TransferRiskLevel:
        risk_score = 0
        
        # Country risk factor
        adequacy_info = self.adequacy_decisions.get(destination_country)
        if adequacy_info:
            if adequacy_info.adequacy_status == AdequacyStatus.NOT_ADEQUATE:
                risk_score += 3
            elif adequacy_info.adequacy_status == AdequacyStatus.UNDER_ASSESSMENT:
                risk_score += 2
            elif adequacy_info.adequacy_status == AdequacyStatus.PARTIALLY_ADEQUATE:
                risk_score += 1
        else:
            risk_score += 4  # Unknown country = highest risk
        
        # Data sensitivity factor
        sensitive_categories = [
            "special_category", "biometric", "health", "financial",
            "criminal", "children", "genetic"
        ]
        
        for category in data_categories:
            if category in sensitive_categories:
                risk_score += 2
            else:
                risk_score += 1
        
        # Volume factor
        if data_volume > 1000000:
            risk_score += 2
        elif data_volume > 100000:
            risk_score += 1
        
        # Convert to risk level
        if risk_score >= 8:
            return TransferRiskLevel.VERY_HIGH
        elif risk_score >= 6:
            return TransferRiskLevel.HIGH
        elif risk_score >= 4:
            return TransferRiskLevel.MEDIUM
        else:
            return TransferRiskLevel.LOW

    async def _determine_required_safeguards(
        self,
        destination_country: str,
        data_categories: List[str],
        risk_level: TransferRiskLevel
    ) -> List[str]:
        safeguards = []
        
        # Base safeguards for all transfers
        safeguards.extend([
            "data_minimization", "purpose_limitation", "storage_limitation"
        ])
        
        # Risk-based safeguards
        if risk_level in [TransferRiskLevel.MEDIUM, TransferRiskLevel.HIGH, TransferRiskLevel.VERY_HIGH]:
            safeguards.extend([
                "encryption_in_transit", "encryption_at_rest",
                "access_controls", "audit_logging"
            ])
        
        if risk_level in [TransferRiskLevel.HIGH, TransferRiskLevel.VERY_HIGH]:
            safeguards.extend([
                "pseudonymization", "data_anonymization",
                "secure_deletion", "incident_response"
            ])
        
        if risk_level == TransferRiskLevel.VERY_HIGH:
            safeguards.extend([
                "end_to_end_encryption", "zero_knowledge_architecture",
                "homomorphic_encryption", "trusted_execution_environment"
            ])
        
        # Country-specific safeguards
        country_risk = self.country_risk_profiles.get(destination_country, {})
        if country_risk.get("government_access") in ["HIGH", "VERY_HIGH"]:
            safeguards.extend([
                "government_access_notification", "legal_challenge_procedures",
                "data_subject_notification"
            ])
        
        return list(set(safeguards))  # Remove duplicates

    async def _determine_legal_basis_options(
        self,
        destination_country: str,
        adequacy_info: Optional[CountryAdequacy],
        risk_level: TransferRiskLevel
    ) -> List[TransferMechanism]:
        options = []
        
        # Adequacy decision
        if adequacy_info and adequacy_info.adequacy_status == AdequacyStatus.ADEQUATE:
            options.append(TransferMechanism.ADEQUACY_DECISION)
        
        # Standard Contractual Clauses (always available)
        options.append(TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES)
        
        # Other mechanisms based on risk and context
        if risk_level in [TransferRiskLevel.LOW, TransferRiskLevel.MEDIUM]:
            options.extend([
                TransferMechanism.CERTIFICATION,
                TransferMechanism.CODES_OF_CONDUCT
            ])
        
        # Binding Corporate Rules (for intra-group transfers)
        options.append(TransferMechanism.BINDING_CORPORATE_RULES)
        
        # Derogations (last resort)
        options.append(TransferMechanism.DEROGATIONS)
        
        return options

    async def _identify_risk_factors(
        self,
        destination_country: str,
        data_categories: List[str],
        processing_purpose: str
    ) -> List[str]:
        risk_factors = []
        
        # Country-specific risks
        adequacy_info = self.adequacy_decisions.get(destination_country)
        if adequacy_info:
            risk_factors.extend(adequacy_info.risk_factors)
        
        # Data category risks
        if "special_category" in data_categories:
            risk_factors.append("special_category_data_processing")
        
        if "children" in data_categories:
            risk_factors.append("child_data_processing")
        
        if "biometric" in data_categories:
            risk_factors.append("biometric_data_processing")
        
        # Processing purpose risks
        high_risk_purposes = [
            "profiling", "automated_decision_making", "surveillance",
            "marketing", "behavioral_analysis"
        ]
        
        if any(purpose in processing_purpose.lower() for purpose in high_risk_purposes):
            risk_factors.append("high_risk_processing_purpose")
        
        return risk_factors

    async def create_transfer_record(
        self,
        data_exporter: str,
        data_importer: str,
        origin_country: str,
        destination_country: str,
        transfer_mechanism: TransferMechanism,
        assessment_id: Optional[str] = None
    ) -> str:
        transfer_id = f"tr_{uuid.uuid4().hex[:8]}"
        
        # Get assessment if provided
        assessment = None
        if assessment_id:
            assessment = self.transfer_assessments.get(assessment_id)
        
        transfer_record = TransferRecord(
            transfer_id=transfer_id,
            data_exporter=data_exporter,
            data_importer=data_importer,
            origin_country=origin_country,
            destination_country=destination_country,
            transfer_mechanism=transfer_mechanism,
            transfer_date=datetime.now(),
            data_categories=assessment.data_categories if assessment else [],
            data_subjects_count=assessment.data_volume if assessment else 0,
            processing_purpose=assessment.processing_purpose if assessment else "",
            retention_period="",  # To be specified
            safeguards_applied=assessment.safeguards_required if assessment else [],
            legal_basis="",  # To be specified
            contract_reference=None,
            approval_reference=None,
            status=TransferStatus.PENDING,
            expiry_date=None,
            monitoring_required=True,
            last_review_date=None,
            next_review_date=datetime.now() + timedelta(days=365),
            compliance_checks=[],
            breach_incidents=[]
        )
        
        # Update assessment with transfer ID
        if assessment:
            assessment.transfer_id = transfer_id
        
        self.transfer_records[transfer_id] = transfer_record
        logger.info(f"Created transfer record {transfer_id}: {origin_country} -> {destination_country}")
        
        return transfer_id

    async def conduct_transfer_impact_assessment(
        self,
        transfer_id: str,
        assessor: str
    ) -> str:
        if transfer_id not in self.transfer_records:
            raise ValueError(f"Transfer record {transfer_id} not found")
        
        transfer = self.transfer_records[transfer_id]
        tia_id = f"tia_{uuid.uuid4().hex[:8]}"
        
        # Analyze destination country laws
        country_profile = self.country_risk_profiles.get(
            transfer.destination_country, {}
        )
        
        # Assess government access laws
        government_access_laws = {
            "surveillance_framework": country_profile.get("surveillance_laws", []),
            "access_procedures": self._analyze_access_procedures(transfer.destination_country),
            "scope_limitations": self._analyze_scope_limitations(transfer.destination_country),
            "oversight_mechanisms": self._analyze_oversight_mechanisms(transfer.destination_country)
        }
        
        # Determine additional safeguards needed
        additional_safeguards = await self._determine_additional_safeguards(
            transfer, country_profile
        )
        
        # Assess residual risks
        residual_risks = await self._assess_residual_risks(
            transfer, additional_safeguards
        )
        
        # Generate conclusion
        conclusion = await self._generate_tia_conclusion(
            transfer, residual_risks, additional_safeguards
        )
        
        tia = TransferImpactAssessment(
            tia_id=tia_id,
            transfer_id=transfer_id,
            destination_country=transfer.destination_country,
            government_access_laws=government_access_laws,
            surveillance_programs=country_profile.get("surveillance_laws", []),
            legal_remedies=country_profile.get("legal_remedies", []),
            independence_adequacy=country_profile.get("enforcement_independence", "UNKNOWN"),
            enforcement_record="",  # To be researched
            additional_safeguards=additional_safeguards,
            residual_risks=residual_risks,
            risk_mitigation=additional_safeguards,
            conclusion=conclusion,
            assessor=assessor,
            assessment_date=datetime.now(),
            review_required=True
        )
        
        self.impact_assessments[tia_id] = tia
        
        # Update transfer record
        transfer.compliance_checks.append(f"TIA conducted: {tia_id}")
        
        logger.info(f"Conducted Transfer Impact Assessment {tia_id} for transfer {transfer_id}")
        return tia_id

    def _analyze_access_procedures(self, country_code: str) -> List[str]:
        procedures_map = {
            "US": ["FISA_warrant", "national_security_letter", "administrative_subpoena"],
            "CN": ["government_directive", "regulatory_order"],
            "RU": ["government_request", "regulatory_enforcement"],
            "GB": ["judicial_warrant", "national_security_notice"]
        }
        return procedures_map.get(country_code, ["unknown_procedures"])

    def _analyze_scope_limitations(self, country_code: str) -> List[str]:
        limitations_map = {
            "US": ["necessity_requirement", "proportionality_principle"],
            "CN": ["national_security_scope", "broad_interpretation"],
            "RU": ["national_security_scope", "law_enforcement_scope"],
            "GB": ["necessity_requirement", "judicial_oversight"]
        }
        return limitations_map.get(country_code, ["unknown_limitations"])

    def _analyze_oversight_mechanisms(self, country_code: str) -> List[str]:
        oversight_map = {
            "US": ["FISC_oversight", "congressional_oversight", "inspector_general"],
            "CN": ["limited_oversight"],
            "RU": ["limited_oversight"],
            "GB": ["judicial_oversight", "ICO_oversight", "tribunal_review"]
        }
        return oversight_map.get(country_code, ["unknown_oversight"])

    async def _determine_additional_safeguards(
        self,
        transfer: TransferRecord,
        country_profile: Dict[str, Any]
    ) -> List[str]:
        safeguards = []
        
        # High government access risk
        if country_profile.get("government_access") in ["HIGH", "VERY_HIGH"]:
            safeguards.extend([
                "client_side_encryption", "key_management_in_origin",
                "government_access_notification", "data_minimization_enhanced"
            ])
        
        # Limited legal remedies
        if "limited" in country_profile.get("legal_remedies", []):
            safeguards.extend([
                "data_subject_notification_procedures",
                "legal_challenge_support", "alternative_remedy_procedures"
            ])
        
        # Weak enforcement independence
        if country_profile.get("enforcement_independence") in ["LOW", "MEDIUM"]:
            safeguards.extend([
                "enhanced_monitoring", "regular_compliance_audits",
                "third_party_assessments"
            ])
        
        return list(set(safeguards))

    async def _assess_residual_risks(
        self,
        transfer: TransferRecord,
        additional_safeguards: List[str]
    ) -> List[str]:
        risks = []
        
        # Government access risks
        if transfer.destination_country in ["US", "CN", "RU"]:
            if "client_side_encryption" not in additional_safeguards:
                risks.append("potential_government_access_to_data")
            else:
                risks.append("metadata_exposure_risk")
        
        # Enforcement risks
        if "enhanced_monitoring" not in additional_safeguards:
            risks.append("limited_recourse_for_violations")
        
        # Technical risks
        if not any("encryption" in s for s in additional_safeguards):
            risks.append("data_interception_during_transfer")
        
        return risks

    async def _generate_tia_conclusion(
        self,
        transfer: TransferRecord,
        residual_risks: List[str],
        additional_safeguards: List[str]
    ) -> str:
        if not residual_risks:
            return "Transfer can proceed with implemented safeguards. Residual risks are minimal."
        
        if len(residual_risks) <= 2 and len(additional_safeguards) >= 3:
            return "Transfer can proceed with enhanced safeguards. Residual risks are acceptable."
        
        if len(residual_risks) > 2:
            return "Transfer presents significant risks. Additional safeguards required or transfer should be reconsidered."
        
        return "Transfer requires careful consideration and ongoing monitoring."

    async def approve_transfer(self, transfer_id: str, approver: str) -> bool:
        if transfer_id not in self.transfer_records:
            raise ValueError(f"Transfer record {transfer_id} not found")
        
        transfer = self.transfer_records[transfer_id]
        transfer.status = TransferStatus.APPROVED
        transfer.approval_reference = f"APP_{uuid.uuid4().hex[:8]}"
        
        logger.info(f"Approved transfer {transfer_id} by {approver}")
        return True

    async def monitor_transfers(self) -> Dict[str, Any]:
        monitoring_results = {
            "total_transfers": len(self.transfer_records),
            "active_transfers": 0,
            "expired_transfers": 0,
            "compliance_issues": [],
            "review_required": []
        }
        
        now = datetime.now()
        
        for transfer_id, transfer in self.transfer_records.items():
            if transfer.status == TransferStatus.APPROVED:
                monitoring_results["active_transfers"] += 1
            
            # Check for expired transfers
            if transfer.expiry_date and transfer.expiry_date < now:
                monitoring_results["expired_transfers"] += 1
                transfer.status = TransferStatus.EXPIRED
            
            # Check for reviews due
            if transfer.next_review_date and transfer.next_review_date < now:
                monitoring_results["review_required"].append(transfer_id)
            
            # Check adequacy status changes
            adequacy_info = self.adequacy_decisions.get(transfer.destination_country)
            if adequacy_info and adequacy_info.adequacy_status == AdequacyStatus.SUSPENDED:
                monitoring_results["compliance_issues"].append({
                    "transfer_id": transfer_id,
                    "issue": "adequacy_decision_suspended",
                    "country": transfer.destination_country
                })
        
        logger.info(f"Transfer monitoring completed: {monitoring_results['active_transfers']} active transfers")
        return monitoring_results

    async def get_transfer_compliance_report(self, transfer_id: str) -> Dict[str, Any]:
        if transfer_id not in self.transfer_records:
            raise ValueError(f"Transfer record {transfer_id} not found")
        
        transfer = self.transfer_records[transfer_id]
        
        # Get associated assessments
        tia_records = [tia for tia in self.impact_assessments.values() 
                      if tia.transfer_id == transfer_id]
        
        report = {
            "transfer_summary": {
                "transfer_id": transfer.transfer_id,
                "status": transfer.status.value,
                "origin": transfer.origin_country,
                "destination": transfer.destination_country,
                "mechanism": transfer.transfer_mechanism.value,
                "transfer_date": transfer.transfer_date.isoformat()
            },
            "adequacy_status": self._get_current_adequacy_status(transfer.destination_country),
            "safeguards_compliance": self._check_safeguards_compliance(transfer),
            "impact_assessments": len(tia_records),
            "compliance_score": self._calculate_compliance_score(transfer, tia_records),
            "recommendations": self._generate_compliance_recommendations(transfer, tia_records)
        }
        
        return report

    def _get_current_adequacy_status(self, country_code: str) -> Dict[str, Any]:
        adequacy_info = self.adequacy_decisions.get(country_code)
        if not adequacy_info:
            return {"status": "unknown", "requires_safeguards": True}
        
        return {
            "status": adequacy_info.adequacy_status.value,
            "decision_date": adequacy_info.adequacy_decision_date.isoformat() if adequacy_info.adequacy_decision_date else None,
            "expiry_date": adequacy_info.adequacy_expiry_date.isoformat() if adequacy_info.adequacy_expiry_date else None,
            "restrictions": adequacy_info.restrictions,
            "requires_safeguards": adequacy_info.adequacy_status != AdequacyStatus.ADEQUATE
        }

    def _check_safeguards_compliance(self, transfer: TransferRecord) -> Dict[str, Any]:
        required_safeguards = [
            "encryption_in_transit", "encryption_at_rest", "access_controls"
        ]
        
        implemented = []
        missing = []
        
        for safeguard in required_safeguards:
            if safeguard in transfer.safeguards_applied:
                implemented.append(safeguard)
            else:
                missing.append(safeguard)
        
        return {
            "implemented_safeguards": implemented,
            "missing_safeguards": missing,
            "compliance_percentage": (len(implemented) / len(required_safeguards)) * 100
        }

    def _calculate_compliance_score(
        self,
        transfer: TransferRecord,
        tia_records: List[TransferImpactAssessment]
    ) -> int:
        score = 0
        
        # Legal basis score (30 points)
        if transfer.transfer_mechanism in [
            TransferMechanism.ADEQUACY_DECISION,
            TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES,
            TransferMechanism.BINDING_CORPORATE_RULES
        ]:
            score += 30
        elif transfer.transfer_mechanism == TransferMechanism.DEROGATIONS:
            score += 15
        
        # Safeguards score (40 points)
        safeguards_compliance = self._check_safeguards_compliance(transfer)
        score += int(safeguards_compliance["compliance_percentage"] * 0.4)
        
        # Impact assessment score (20 points)
        if tia_records:
            score += 20
        
        # Documentation score (10 points)
        if transfer.contract_reference:
            score += 5
        if transfer.approval_reference:
            score += 5
        
        return min(score, 100)

    def _generate_compliance_recommendations(
        self,
        transfer: TransferRecord,
        tia_records: List[TransferImpactAssessment]
    ) -> List[str]:
        recommendations = []
        
        # Missing TIA
        if not tia_records and transfer.destination_country in ["US", "CN", "RU"]:
            recommendations.append("Conduct Transfer Impact Assessment for high-risk destination")
        
        # Missing safeguards
        safeguards_check = self._check_safeguards_compliance(transfer)
        if safeguards_check["missing_safeguards"]:
            recommendations.append(f"Implement missing safeguards: {', '.join(safeguards_check['missing_safeguards'])}")
        
        # Expired adequacy
        adequacy_status = self._get_current_adequacy_status(transfer.destination_country)
        if adequacy_status.get("expiry_date"):
            expiry_date = datetime.fromisoformat(adequacy_status["expiry_date"])
            if expiry_date < datetime.now() + timedelta(days=90):
                recommendations.append("Monitor adequacy decision renewal - expiring soon")
        
        return recommendations

    async def export_transfer_data(self, format: str = "json") -> Dict[str, Any]:
        export_data = {
            "export_date": datetime.now().isoformat(),
            "total_transfers": len(self.transfer_records),
            "adequacy_decisions": {},
            "transfer_records": {},
            "impact_assessments": {}
        }
        
        # Export adequacy decisions
        for country_code, adequacy in self.adequacy_decisions.items():
            export_data["adequacy_decisions"][country_code] = {
                "country_name": adequacy.country_name,
                "adequacy_status": adequacy.adequacy_status.value,
                "decision_date": adequacy.adequacy_decision_date.isoformat() if adequacy.adequacy_decision_date else None,
                "restrictions": adequacy.restrictions
            }
        
        # Export transfer records
        for transfer_id, transfer in self.transfer_records.items():
            export_data["transfer_records"][transfer_id] = {
                "origin": transfer.origin_country,
                "destination": transfer.destination_country,
                "mechanism": transfer.transfer_mechanism.value,
                "status": transfer.status.value,
                "transfer_date": transfer.transfer_date.isoformat()
            }
        
        # Export impact assessments
        for tia_id, tia in self.impact_assessments.items():
            export_data["impact_assessments"][tia_id] = {
                "transfer_id": tia.transfer_id,
                "destination_country": tia.destination_country,
                "conclusion": tia.conclusion,
                "assessment_date": tia.assessment_date.isoformat()
            }
        
        logger.info(f"Exported cross-border transfer data: {len(self.transfer_records)} transfers")
        return export_data