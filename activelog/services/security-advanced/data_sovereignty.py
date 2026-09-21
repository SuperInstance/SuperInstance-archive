"""
Data Sovereignty Enforcement System
Enforce data residency, sovereignty, and cross-border transfer compliance
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Any, Callable, Union, Tuple
from enum import Enum
import hashlib
import secrets
import asyncio
from datetime import datetime, timedelta
import json
from abc import ABC, abstractmethod
import ipaddress

class JurisdictionType(Enum):
    COUNTRY = "country"
    STATE_PROVINCE = "state_province"
    ECONOMIC_ZONE = "economic_zone"
    CUSTOM = "custom"

class DataClassification(Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PERSONAL_DATA = "personal_data"
    SENSITIVE_PERSONAL_DATA = "sensitive_personal_data"

class TransferMechanism(Enum):
    ADEQUACY_DECISION = "adequacy_decision"
    STANDARD_CONTRACTUAL_CLAUSES = "standard_contractual_clauses"
    BINDING_CORPORATE_RULES = "binding_corporate_rules"
    CERTIFICATION = "certification"
    CONSENT = "consent"
    CONTRACT_NECESSITY = "contract_necessity"
    PUBLIC_INTEREST = "public_interest"
    LEGITIMATE_INTERESTS = "legitimate_interests"

class ComplianceRegime(Enum):
    GDPR = "gdpr"  # General Data Protection Regulation (EU)
    CCPA = "ccpa"  # California Consumer Privacy Act
    LGPD = "lgpd"  # Lei Geral de Proteção de Dados (Brazil)
    PIPEDA = "pipeda"  # Personal Information Protection and Electronic Documents Act (Canada)
    DPA = "dpa"  # Data Protection Act (UK)
    PDPA_SINGAPORE = "pdpa_singapore"
    CDPA = "cdpa"  # China Data Protection Act
    CUSTOM_REGIME = "custom_regime"

class ViolationType(Enum):
    UNAUTHORIZED_TRANSFER = "unauthorized_transfer"
    RESIDENCY_VIOLATION = "residency_violation"
    INADEQUATE_SAFEGUARDS = "inadequate_safeguards"
    MISSING_CONSENT = "missing_consent"
    RETENTION_VIOLATION = "retention_violation"
    ACCESS_VIOLATION = "access_violation"

@dataclass
class GeographicLocation:
    """Geographic location for data sovereignty"""
    country_code: str  # ISO 3166-1 alpha-2
    region: Optional[str]  # State, province, or region
    city: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    jurisdiction_type: JurisdictionType
    compliance_regimes: List[ComplianceRegime]

@dataclass
class DataResidencyRule:
    """Rule defining where data must reside"""
    rule_id: str
    name: str
    data_types: List[DataClassification]
    allowed_locations: List[GeographicLocation]
    prohibited_locations: List[GeographicLocation]
    compliance_regimes: List[ComplianceRegime]
    retention_period: Optional[timedelta]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool

@dataclass
class DataAsset:
    """Data asset with sovereignty requirements"""
    asset_id: str
    name: str
    data_classification: DataClassification
    current_location: GeographicLocation
    subject_jurisdictions: List[str]  # Jurisdictions of data subjects
    applicable_regimes: List[ComplianceRegime]
    residency_rules: List[str]  # Rule IDs
    created_at: datetime
    last_accessed: Optional[datetime]
    size_bytes: int

@dataclass
class TransferRequest:
    """Request for cross-border data transfer"""
    request_id: str
    source_asset_id: str
    destination_location: GeographicLocation
    transfer_mechanism: TransferMechanism
    purpose: str
    requester: str
    requested_at: datetime
    duration: Optional[timedelta]
    safeguards: List[str]
    additional_context: Dict[str, Any]

@dataclass
class TransferApproval:
    """Approval for data transfer"""
    approval_id: str
    request_id: str
    approved_by: str
    approved_at: datetime
    conditions: List[str]
    valid_until: Optional[datetime]
    monitoring_requirements: List[str]
    approval_basis: TransferMechanism

@dataclass
class ComplianceViolation:
    """Detected compliance violation"""
    violation_id: str
    violation_type: ViolationType
    asset_id: str
    description: str
    detected_at: datetime
    severity: str  # "low", "medium", "high", "critical"
    affected_subjects: Optional[int]
    potential_fine: Optional[float]
    remediation_required: List[str]
    status: str  # "open", "investigating", "resolved", "false_positive"

@dataclass
class DataProcessor:
    """Third-party data processor information"""
    processor_id: str
    name: str
    location: GeographicLocation
    certifications: List[str]
    compliance_regimes: List[ComplianceRegime]
    data_processing_agreement: Optional[str]
    security_measures: List[str]
    last_audit: Optional[datetime]

class SovereigntyEngine(ABC):
    """Abstract base for data sovereignty enforcement"""
    
    @abstractmethod
    async def evaluate_residency_compliance(self, asset: DataAsset) -> Dict[str, Any]:
        """Evaluate if asset complies with residency rules"""
        pass
    
    @abstractmethod
    async def assess_transfer_legality(self, request: TransferRequest) -> Dict[str, Any]:
        """Assess if data transfer is legally compliant"""
        pass
    
    @abstractmethod
    async def detect_violations(self, assets: List[DataAsset]) -> List[ComplianceViolation]:
        """Detect compliance violations"""
        pass

class GDPRSovereigntyEngine(SovereigntyEngine):
    """GDPR-specific sovereignty enforcement"""
    
    def __init__(self):
        # EU/EEA countries with GDPR adequacy
        self.adequate_countries = {
            "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", 
            "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
            "PL", "PT", "RO", "SK", "SI", "ES", "SE", "IS", "LI", "NO"
        }
        
        # Countries with adequacy decisions
        self.adequacy_decision_countries = {
            "AD", "AR", "CA", "FO", "GG", "IL", "IM", "JE", "JP", "NZ", 
            "CH", "UY", "GB", "US"  # US under specific frameworks
        }
    
    async def evaluate_residency_compliance(self, asset: DataAsset) -> Dict[str, Any]:
        """Evaluate GDPR residency compliance"""
        compliance_result = {
            "compliant": True,
            "issues": [],
            "recommendations": [],
            "risk_level": "low"
        }
        
        # Check if data is in adequate jurisdiction
        current_country = asset.current_location.country_code
        
        if asset.data_classification in [DataClassification.PERSONAL_DATA, DataClassification.SENSITIVE_PERSONAL_DATA]:
            if current_country not in self.adequate_countries and current_country not in self.adequacy_decision_countries:
                compliance_result["compliant"] = False
                compliance_result["issues"].append(f"Personal data located in non-adequate country: {current_country}")
                compliance_result["risk_level"] = "high"
                compliance_result["recommendations"].append("Move data to EU/EEA or adequate country")
        
        # Check subject jurisdiction alignment
        eu_subjects = any(country in self.adequate_countries for country in asset.subject_jurisdictions)
        if eu_subjects and current_country not in self.adequate_countries and current_country not in self.adequacy_decision_countries:
            compliance_result["compliant"] = False
            compliance_result["issues"].append("EU data subjects' data stored outside adequate jurisdictions")
            compliance_result["risk_level"] = "critical"
        
        return compliance_result
    
    async def assess_transfer_legality(self, request: TransferRequest) -> Dict[str, Any]:
        """Assess GDPR transfer legality"""
        assessment = {
            "legal": True,
            "basis": None,
            "additional_safeguards_required": [],
            "conditions": [],
            "risk_assessment": "low"
        }
        
        destination_country = request.destination_location.country_code
        
        # Check if transfer is within adequate jurisdictions
        if destination_country in self.adequate_countries or destination_country in self.adequacy_decision_countries:
            assessment["basis"] = "adequacy_decision"
            return assessment
        
        # Evaluate transfer mechanism
        if request.transfer_mechanism == TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES:
            assessment["basis"] = "standard_contractual_clauses"
            assessment["additional_safeguards_required"] = [
                "encryption_in_transit",
                "encryption_at_rest",
                "access_controls",
                "audit_logging"
            ]
            assessment["conditions"] = [
                "regular_compliance_monitoring",
                "data_subject_rights_procedures",
                "breach_notification_procedures"
            ]
        elif request.transfer_mechanism == TransferMechanism.CONSENT:
            assessment["basis"] = "explicit_consent"
            assessment["conditions"] = [
                "informed_consent_obtained",
                "consent_withdrawal_mechanism",
                "limited_transfer_scope"
            ]
        else:
            assessment["legal"] = False
            assessment["risk_assessment"] = "high"
        
        return assessment
    
    async def detect_violations(self, assets: List[DataAsset]) -> List[ComplianceViolation]:
        """Detect GDPR violations"""
        violations = []
        
        for asset in assets:
            compliance = await self.evaluate_residency_compliance(asset)
            
            if not compliance["compliant"]:
                for issue in compliance["issues"]:
                    violation = ComplianceViolation(
                        violation_id=f"gdpr_viol_{secrets.token_hex(8)}",
                        violation_type=ViolationType.RESIDENCY_VIOLATION,
                        asset_id=asset.asset_id,
                        description=issue,
                        detected_at=datetime.now(),
                        severity=compliance["risk_level"],
                        affected_subjects=None,  # Would need to calculate
                        potential_fine=self._calculate_gdpr_fine(compliance["risk_level"], asset.size_bytes),
                        remediation_required=compliance["recommendations"],
                        status="open"
                    )
                    violations.append(violation)
        
        return violations
    
    def _calculate_gdpr_fine(self, risk_level: str, data_size: int) -> float:
        """Calculate potential GDPR fine"""
        # GDPR fines can be up to 4% of annual turnover or €20M, whichever is higher
        base_fine = {
            "low": 1000,
            "medium": 10000,
            "high": 50000,
            "critical": 200000
        }.get(risk_level, 1000)
        
        # Scale by data size (very simplified)
        size_multiplier = min(10, max(1, data_size / (1024 * 1024)))  # MB-based scaling
        
        return base_fine * size_multiplier

class DataSovereigntySystem:
    """Main data sovereignty enforcement system"""
    
    def __init__(self):
        self.sovereignty_engines: Dict[ComplianceRegime, SovereigntyEngine] = {
            ComplianceRegime.GDPR: GDPRSovereigntyEngine()
        }
        
        self.data_assets: Dict[str, DataAsset] = {}
        self.residency_rules: Dict[str, DataResidencyRule] = {}
        self.transfer_requests: List[TransferRequest] = []
        self.transfer_approvals: Dict[str, TransferApproval] = {}
        self.compliance_violations: List[ComplianceViolation] = []
        self.data_processors: Dict[str, DataProcessor] = {}
        
        # Geographic IP ranges for location detection
        self.ip_location_ranges: Dict[str, List[Tuple[str, str]]] = {}
    
    async def register_data_asset(
        self,
        name: str,
        data_classification: DataClassification,
        current_location: GeographicLocation,
        subject_jurisdictions: List[str],
        applicable_regimes: List[ComplianceRegime],
        size_bytes: int
    ) -> DataAsset:
        """Register a new data asset"""
        asset = DataAsset(
            asset_id=f"asset_{secrets.token_hex(8)}",
            name=name,
            data_classification=data_classification,
            current_location=current_location,
            subject_jurisdictions=subject_jurisdictions,
            applicable_regimes=applicable_regimes,
            residency_rules=[],
            created_at=datetime.now(),
            last_accessed=None,
            size_bytes=size_bytes
        )
        
        self.data_assets[asset.asset_id] = asset
        
        # Automatically apply relevant residency rules
        await self._apply_residency_rules(asset)
        
        return asset
    
    async def _apply_residency_rules(self, asset: DataAsset):
        """Apply relevant residency rules to an asset"""
        for rule in self.residency_rules.values():
            if (asset.data_classification in rule.data_types and
                any(regime in asset.applicable_regimes for regime in rule.compliance_regimes)):
                asset.residency_rules.append(rule.rule_id)
    
    async def create_residency_rule(
        self,
        name: str,
        data_types: List[DataClassification],
        allowed_locations: List[GeographicLocation],
        prohibited_locations: List[GeographicLocation],
        compliance_regimes: List[ComplianceRegime],
        retention_period: Optional[timedelta] = None
    ) -> DataResidencyRule:
        """Create a new data residency rule"""
        rule = DataResidencyRule(
            rule_id=f"rule_{secrets.token_hex(8)}",
            name=name,
            data_types=data_types,
            allowed_locations=allowed_locations,
            prohibited_locations=prohibited_locations,
            compliance_regimes=compliance_regimes,
            retention_period=retention_period,
            created_at=datetime.now(),
            expires_at=None,
            is_active=True
        )
        
        self.residency_rules[rule.rule_id] = rule
        
        # Apply to existing assets
        for asset in self.data_assets.values():
            if (asset.data_classification in data_types and
                any(regime in asset.applicable_regimes for regime in compliance_regimes)):
                asset.residency_rules.append(rule.rule_id)
        
        return rule
    
    async def request_data_transfer(
        self,
        asset_id: str,
        destination_location: GeographicLocation,
        transfer_mechanism: TransferMechanism,
        purpose: str,
        requester: str,
        duration: Optional[timedelta] = None,
        safeguards: Optional[List[str]] = None
    ) -> TransferRequest:
        """Request approval for cross-border data transfer"""
        if asset_id not in self.data_assets:
            raise ValueError(f"Asset {asset_id} not found")
        
        request = TransferRequest(
            request_id=f"req_{secrets.token_hex(8)}",
            source_asset_id=asset_id,
            destination_location=destination_location,
            transfer_mechanism=transfer_mechanism,
            purpose=purpose,
            requester=requester,
            requested_at=datetime.now(),
            duration=duration,
            safeguards=safeguards or [],
            additional_context={}
        )
        
        self.transfer_requests.append(request)
        return request
    
    async def evaluate_transfer_request(self, request_id: str) -> Dict[str, Any]:
        """Evaluate a transfer request for compliance"""
        request = next((r for r in self.transfer_requests if r.request_id == request_id), None)
        if not request:
            raise ValueError(f"Transfer request {request_id} not found")
        
        asset = self.data_assets[request.source_asset_id]
        
        evaluation_results = {}
        overall_compliant = True
        
        # Evaluate against each applicable compliance regime
        for regime in asset.applicable_regimes:
            if regime in self.sovereignty_engines:
                engine = self.sovereignty_engines[regime]
                result = await engine.assess_transfer_legality(request)
                evaluation_results[regime.value] = result
                
                if not result["legal"]:
                    overall_compliant = False
        
        return {
            "request_id": request_id,
            "overall_compliant": overall_compliant,
            "regime_evaluations": evaluation_results,
            "recommended_action": "approve" if overall_compliant else "deny",
            "required_safeguards": list(set().union(*[
                result.get("additional_safeguards_required", [])
                for result in evaluation_results.values()
            ])),
            "conditions": list(set().union(*[
                result.get("conditions", [])
                for result in evaluation_results.values()
            ]))
        }
    
    async def approve_transfer(
        self,
        request_id: str,
        approver: str,
        conditions: Optional[List[str]] = None,
        valid_duration: Optional[timedelta] = None
    ) -> TransferApproval:
        """Approve a data transfer request"""
        request = next((r for r in self.transfer_requests if r.request_id == request_id), None)
        if not request:
            raise ValueError(f"Transfer request {request_id} not found")
        
        # Evaluate first
        evaluation = await self.evaluate_transfer_request(request_id)
        if not evaluation["overall_compliant"]:
            raise ValueError("Cannot approve non-compliant transfer request")
        
        approval = TransferApproval(
            approval_id=f"app_{secrets.token_hex(8)}",
            request_id=request_id,
            approved_by=approver,
            approved_at=datetime.now(),
            conditions=conditions or evaluation["conditions"],
            valid_until=datetime.now() + valid_duration if valid_duration else None,
            monitoring_requirements=["audit_access", "monitor_compliance", "review_safeguards"],
            approval_basis=request.transfer_mechanism
        )
        
        self.transfer_approvals[approval.approval_id] = approval
        return approval
    
    async def detect_ip_location_violations(self, ip_addresses: List[str]) -> List[ComplianceViolation]:
        """Detect violations based on IP address locations"""
        violations = []
        
        for ip in ip_addresses:
            try:
                # Simple IP location detection (would use real GeoIP service)
                ip_obj = ipaddress.ip_address(ip)
                detected_country = self._detect_country_from_ip(str(ip_obj))
                
                # Check against assets that prohibit this location
                for asset in self.data_assets.values():
                    for rule_id in asset.residency_rules:
                        rule = self.residency_rules[rule_id]
                        
                        prohibited_countries = [loc.country_code for loc in rule.prohibited_locations]
                        if detected_country in prohibited_countries:
                            violation = ComplianceViolation(
                                violation_id=f"ip_viol_{secrets.token_hex(8)}",
                                violation_type=ViolationType.ACCESS_VIOLATION,
                                asset_id=asset.asset_id,
                                description=f"Access from prohibited jurisdiction {detected_country} via IP {ip}",
                                detected_at=datetime.now(),
                                severity="high",
                                affected_subjects=None,
                                potential_fine=None,
                                remediation_required=["block_access", "investigate_breach"],
                                status="open"
                            )
                            violations.append(violation)
            
            except ValueError:
                # Invalid IP address
                continue
        
        return violations
    
    def _detect_country_from_ip(self, ip: str) -> str:
        """Detect country from IP address (simplified)"""
        # This would normally use a GeoIP database
        # For demo purposes, return a mock country based on IP ranges
        if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172."):
            return "US"  # Private IP ranges treated as US
        elif ip.startswith("8.8."):
            return "US"  # Google DNS
        elif ip.startswith("1.1."):
            return "US"  # Cloudflare DNS
        else:
            return "US"  # Default fallback
    
    async def run_compliance_audit(self) -> Dict[str, Any]:
        """Run comprehensive compliance audit"""
        audit_results = {
            "audit_timestamp": datetime.now().isoformat(),
            "total_assets": len(self.data_assets),
            "violations_found": 0,
            "compliance_by_regime": {},
            "assets_at_risk": [],
            "transfer_compliance": {},
            "recommendations": []
        }
        
        all_violations = []
        
        # Audit each compliance regime
        for regime, engine in self.sovereignty_engines.items():
            regime_assets = [
                asset for asset in self.data_assets.values()
                if regime in asset.applicable_regimes
            ]
            
            regime_violations = await engine.detect_violations(regime_assets)
            all_violations.extend(regime_violations)
            
            audit_results["compliance_by_regime"][regime.value] = {
                "total_assets": len(regime_assets),
                "violations": len(regime_violations),
                "compliance_rate": (len(regime_assets) - len(regime_violations)) / len(regime_assets) if regime_assets else 1.0
            }
        
        # Update violations list
        self.compliance_violations.extend(all_violations)
        audit_results["violations_found"] = len(all_violations)
        
        # Identify high-risk assets
        for violation in all_violations:
            if violation.severity in ["high", "critical"]:
                audit_results["assets_at_risk"].append({
                    "asset_id": violation.asset_id,
                    "violation_type": violation.violation_type.value,
                    "severity": violation.severity,
                    "description": violation.description
                })
        
        # Transfer compliance
        pending_transfers = [r for r in self.transfer_requests if r.request_id not in self.transfer_approvals]
        audit_results["transfer_compliance"] = {
            "pending_requests": len(pending_transfers),
            "approved_transfers": len(self.transfer_approvals),
            "overdue_requests": len([
                r for r in pending_transfers 
                if (datetime.now() - r.requested_at).days > 7
            ])
        }
        
        # Generate recommendations
        if audit_results["violations_found"] > 0:
            audit_results["recommendations"].extend([
                "Review and remediate identified violations",
                "Implement automated compliance monitoring",
                "Update data residency rules",
                "Review transfer mechanisms and safeguards"
            ])
        
        if audit_results["transfer_compliance"]["pending_requests"] > 0:
            audit_results["recommendations"].append("Process pending transfer requests")
        
        return audit_results
    
    async def get_sovereignty_dashboard(self) -> Dict[str, Any]:
        """Get sovereignty enforcement dashboard data"""
        # Recent violations
        recent_violations = [
            v for v in self.compliance_violations
            if (datetime.now() - v.detected_at).days <= 7
        ]
        
        # Assets by classification
        classification_breakdown = {}
        for classification in DataClassification:
            count = len([a for a in self.data_assets.values() if a.data_classification == classification])
            classification_breakdown[classification.value] = count
        
        # Geographic distribution
        location_breakdown = {}
        for asset in self.data_assets.values():
            country = asset.current_location.country_code
            location_breakdown[country] = location_breakdown.get(country, 0) + 1
        
        return {
            "total_assets": len(self.data_assets),
            "total_residency_rules": len(self.residency_rules),
            "pending_transfers": len(self.transfer_requests) - len(self.transfer_approvals),
            "recent_violations": len(recent_violations),
            "critical_violations": len([v for v in recent_violations if v.severity == "critical"]),
            "classification_breakdown": classification_breakdown,
            "geographic_distribution": location_breakdown,
            "compliance_regimes_active": len(self.sovereignty_engines),
            "data_processors": len(self.data_processors),
            "last_audit": max([v.detected_at for v in self.compliance_violations]) if self.compliance_violations else None
        }

def create_data_sovereignty_system() -> DataSovereigntySystem:
    """Factory function to create data sovereignty system"""
    return DataSovereigntySystem()

# Example usage
async def example_usage():
    """Example of using data sovereignty enforcement"""
    
    # Create sovereignty system
    sovereignty_system = create_data_sovereignty_system()
    
    # Define geographic locations
    eu_location = GeographicLocation(
        country_code="DE",
        region="Bavaria",
        city="Munich",
        latitude=48.1351,
        longitude=11.5820,
        jurisdiction_type=JurisdictionType.COUNTRY,
        compliance_regimes=[ComplianceRegime.GDPR]
    )
    
    us_location = GeographicLocation(
        country_code="US",
        region="California",
        city="San Francisco",
        latitude=37.7749,
        longitude=-122.4194,
        jurisdiction_type=JurisdictionType.STATE_PROVINCE,
        compliance_regimes=[ComplianceRegime.CCPA]
    )
    
    # Create residency rule
    gdpr_rule = await sovereignty_system.create_residency_rule(
        name="GDPR Personal Data Residency",
        data_types=[DataClassification.PERSONAL_DATA, DataClassification.SENSITIVE_PERSONAL_DATA],
        allowed_locations=[eu_location],
        prohibited_locations=[],
        compliance_regimes=[ComplianceRegime.GDPR],
        retention_period=timedelta(days=2555)  # 7 years
    )
    
    print(f"Created GDPR residency rule: {gdpr_rule.rule_id}")
    
    # Register data assets
    user_data_asset = await sovereignty_system.register_data_asset(
        name="User Profile Database",
        data_classification=DataClassification.PERSONAL_DATA,
        current_location=eu_location,
        subject_jurisdictions=["DE", "FR", "IT"],
        applicable_regimes=[ComplianceRegime.GDPR],
        size_bytes=1024*1024*100  # 100 MB
    )
    
    print(f"Registered user data asset: {user_data_asset.asset_id}")
    print(f"  Current location: {user_data_asset.current_location.country_code}")
    print(f"  Classification: {user_data_asset.data_classification.value}")
    print(f"  Applied rules: {len(user_data_asset.residency_rules)}")
    
    # Request data transfer
    transfer_request = await sovereignty_system.request_data_transfer(
        asset_id=user_data_asset.asset_id,
        destination_location=us_location,
        transfer_mechanism=TransferMechanism.STANDARD_CONTRACTUAL_CLAUSES,
        purpose="analytics_processing",
        requester="data_science_team",
        duration=timedelta(days=30),
        safeguards=["encryption", "access_controls", "audit_logging"]
    )
    
    print(f"\nRequested data transfer: {transfer_request.request_id}")
    print(f"  From: {user_data_asset.current_location.country_code}")
    print(f"  To: {transfer_request.destination_location.country_code}")
    print(f"  Mechanism: {transfer_request.transfer_mechanism.value}")
    
    # Evaluate transfer request
    evaluation = await sovereignty_system.evaluate_transfer_request(transfer_request.request_id)
    
    print(f"\nTransfer evaluation:")
    print(f"  Overall compliant: {evaluation['overall_compliant']}")
    print(f"  Recommended action: {evaluation['recommended_action']}")
    print(f"  Required safeguards: {evaluation['required_safeguards']}")
    print(f"  Conditions: {evaluation['conditions']}")
    
    # Test IP location violation detection
    test_ips = ["192.168.1.100", "8.8.8.8", "1.1.1.1"]
    ip_violations = await sovereignty_system.detect_ip_location_violations(test_ips)
    
    print(f"\nIP location violations detected: {len(ip_violations)}")
    
    # Run compliance audit
    audit_results = await sovereignty_system.run_compliance_audit()
    
    print(f"\nCompliance Audit Results:")
    print(f"  Total assets: {audit_results['total_assets']}")
    print(f"  Violations found: {audit_results['violations_found']}")
    print(f"  Assets at risk: {len(audit_results['assets_at_risk'])}")
    
    for regime, stats in audit_results['compliance_by_regime'].items():
        print(f"  {regime} compliance: {stats['compliance_rate']*100:.1f}% ({stats['violations']} violations)")
    
    print(f"\nRecommendations:")
    for recommendation in audit_results['recommendations']:
        print(f"  - {recommendation}")
    
    # Get dashboard data
    dashboard = await sovereignty_system.get_sovereignty_dashboard()
    
    print(f"\nSovereignty Dashboard:")
    print(f"  Total assets: {dashboard['total_assets']}")
    print(f"  Residency rules: {dashboard['total_residency_rules']}")
    print(f"  Pending transfers: {dashboard['pending_transfers']}")
    print(f"  Recent violations: {dashboard['recent_violations']}")
    
    print(f"\nGeographic distribution:")
    for country, count in dashboard['geographic_distribution'].items():
        print(f"  {country}: {count} assets")

if __name__ == "__main__":
    asyncio.run(example_usage())