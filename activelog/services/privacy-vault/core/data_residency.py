import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from ..models.privacy_models import DataLocation, DataCategory
import logging
import json

logger = logging.getLogger(__name__)

class DataResidencyManager:
    def __init__(self):
        self.data_locations: Dict[str, DataLocation] = {}
        self.jurisdiction_rules: Dict[str, Dict] = {}
        self.compliance_policies: Dict[str, Dict] = {}
        self.monitoring_alerts: List[Dict] = []
        self.geo_restrictions: Dict[str, List[str]] = {}
        self.cloud_provider_regions: Dict[str, List[Dict]] = {}
        
        # Initialize residency framework
        asyncio.create_task(self._initialize_jurisdiction_rules())
        asyncio.create_task(self._initialize_cloud_provider_mapping())
    
    async def _initialize_jurisdiction_rules(self):
        """Initialize data residency rules for different jurisdictions"""
        self.jurisdiction_rules = {
            "EU": {
                "name": "European Union",
                "data_localization_required": True,
                "allowed_regions": [
                    "eu-west-1", "eu-west-2", "eu-west-3", "eu-central-1", 
                    "eu-north-1", "eu-south-1"
                ],
                "restricted_data_types": [
                    DataCategory.PERSONAL_DATA,
                    DataCategory.SENSITIVE_DATA,
                    DataCategory.HEALTH_DATA
                ],
                "cross_border_restrictions": {
                    "adequacy_required": True,
                    "scc_required": True,  # Standard Contractual Clauses
                    "prohibited_countries": ["CN", "RU"]
                },
                "retention_requirements": {
                    "max_retention_days": 2555,  # 7 years
                    "deletion_requirements": "secure_deletion"
                }
            },
            "US": {
                "name": "United States",
                "data_localization_required": False,
                "allowed_regions": [
                    "us-east-1", "us-east-2", "us-west-1", "us-west-2"
                ],
                "restricted_data_types": [
                    DataCategory.HEALTH_DATA,  # HIPAA
                    DataCategory.FINANCIAL_DATA  # SOX, GLBA
                ],
                "sector_specific_rules": {
                    "healthcare": {
                        "framework": "HIPAA",
                        "encryption_required": True,
                        "audit_trail_required": True
                    },
                    "financial": {
                        "framework": "SOX",
                        "data_residency_required": True
                    }
                }
            },
            "CA": {
                "name": "Canada",
                "data_localization_required": True,
                "allowed_regions": ["ca-central-1"],
                "restricted_data_types": [
                    DataCategory.PERSONAL_DATA,
                    DataCategory.HEALTH_DATA
                ],
                "cross_border_restrictions": {
                    "consent_required": True,
                    "notification_required": True
                }
            },
            "CN": {
                "name": "China",
                "data_localization_required": True,
                "allowed_regions": ["cn-north-1", "cn-northwest-1"],
                "restricted_data_types": [
                    DataCategory.PERSONAL_DATA,
                    DataCategory.SENSITIVE_DATA,
                    DataCategory.LOCATION_DATA
                ],
                "cross_border_restrictions": {
                    "security_assessment_required": True,
                    "government_approval_required": True
                }
            },
            "RU": {
                "name": "Russia",
                "data_localization_required": True,
                "allowed_regions": ["ru-central-1"],
                "restricted_data_types": [
                    DataCategory.PERSONAL_DATA
                ],
                "cross_border_restrictions": {
                    "prohibited": True
                }
            },
            "IN": {
                "name": "India",
                "data_localization_required": True,
                "allowed_regions": ["ap-south-1"],
                "restricted_data_types": [
                    DataCategory.FINANCIAL_DATA,
                    DataCategory.HEALTH_DATA
                ],
                "mirroring_required": True
            }
        }
        
        # Initialize compliance policies
        self.compliance_policies = {
            "gdpr_compliance": {
                "applicable_jurisdictions": ["EU"],
                "requirements": [
                    "data_minimization",
                    "purpose_limitation",
                    "storage_limitation",
                    "accuracy",
                    "integrity_confidentiality"
                ]
            },
            "ccpa_compliance": {
                "applicable_jurisdictions": ["US-CA"],
                "requirements": [
                    "consumer_rights",
                    "data_transparency",
                    "opt_out_rights"
                ]
            }
        }
    
    async def _initialize_cloud_provider_mapping(self):
        """Initialize mapping of cloud provider regions to jurisdictions"""
        self.cloud_provider_regions = {
            "aws": {
                "us-east-1": {"jurisdiction": "US", "location": "N. Virginia"},
                "us-west-2": {"jurisdiction": "US", "location": "Oregon"},
                "eu-west-1": {"jurisdiction": "EU", "location": "Ireland"},
                "eu-central-1": {"jurisdiction": "EU", "location": "Frankfurt"},
                "ca-central-1": {"jurisdiction": "CA", "location": "Canada Central"},
                "ap-south-1": {"jurisdiction": "IN", "location": "Mumbai"},
                "cn-north-1": {"jurisdiction": "CN", "location": "Beijing"},
                "eu-west-3": {"jurisdiction": "EU", "location": "Paris"}
            },
            "azure": {
                "eastus": {"jurisdiction": "US", "location": "East US"},
                "westeurope": {"jurisdiction": "EU", "location": "West Europe"},
                "canadacentral": {"jurisdiction": "CA", "location": "Canada Central"},
                "chinanorth": {"jurisdiction": "CN", "location": "China North"}
            },
            "gcp": {
                "us-central1": {"jurisdiction": "US", "location": "Iowa"},
                "europe-west1": {"jurisdiction": "EU", "location": "Belgium"},
                "asia-south1": {"jurisdiction": "IN", "location": "Mumbai"}
            }
        }
    
    async def register_data_location(
        self,
        data_id: str,
        location: str,
        data_type: DataCategory,
        jurisdiction: str,
        storage_requirements: Dict[str, Any]
    ) -> str:
        """Register data location for residency tracking"""
        try:
            location_id = f"loc_{data_id}_{int(datetime.utcnow().timestamp())}"
            
            # Validate jurisdiction and location compatibility
            compliance_check = await self._validate_location_compliance(
                location, data_type, jurisdiction, storage_requirements
            )
            
            if not compliance_check["compliant"]:
                raise ValueError(f"Location not compliant: {compliance_check['violations']}")
            
            # Create data location record
            data_location = DataLocation(
                location_id=location_id,
                data_id=data_id,
                geographic_location=location,
                jurisdiction=jurisdiction,
                storage_provider=storage_requirements.get("provider"),
                compliance_certifications=storage_requirements.get("certifications", []),
                created_at=datetime.utcnow(),
                last_verified=datetime.utcnow()
            )
            
            # Store location record
            self.data_locations[location_id] = data_location
            
            # Set up monitoring for this location
            await self._setup_location_monitoring(location_id)
            
            logger.info(f"Registered data location: {location_id} in {jurisdiction}")
            return location_id
            
        except Exception as e:
            logger.error(f"Data location registration failed: {e}")
            raise
    
    async def _validate_location_compliance(
        self,
        location: str,
        data_type: DataCategory,
        jurisdiction: str,
        storage_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate if location meets compliance requirements"""
        violations = []
        compliant = True
        
        # Check jurisdiction rules
        if jurisdiction in self.jurisdiction_rules:
            rules = self.jurisdiction_rules[jurisdiction]
            
            # Check data localization requirements
            if rules.get("data_localization_required", False):
                allowed_regions = rules.get("allowed_regions", [])
                region = storage_requirements.get("region", location)
                
                if region not in allowed_regions:
                    violations.append(f"Data must be stored in allowed regions: {allowed_regions}")
                    compliant = False
            
            # Check restricted data types
            restricted_types = rules.get("restricted_data_types", [])
            if data_type in restricted_types:
                # Additional checks for restricted data
                if not storage_requirements.get("encryption_enabled", False):
                    violations.append("Encryption required for restricted data types")
                    compliant = False
                
                if not storage_requirements.get("access_logging", False):
                    violations.append("Access logging required for restricted data types")
                    compliant = False
            
            # Check sector-specific rules
            sector_rules = rules.get("sector_specific_rules", {})
            data_sector = storage_requirements.get("sector")
            
            if data_sector and data_sector in sector_rules:
                sector_rule = sector_rules[data_sector]
                
                if sector_rule.get("encryption_required", False) and not storage_requirements.get("encryption_enabled", False):
                    violations.append(f"Encryption required for {data_sector} sector")
                    compliant = False
                
                if sector_rule.get("audit_trail_required", False) and not storage_requirements.get("audit_trail", False):
                    violations.append(f"Audit trail required for {data_sector} sector")
                    compliant = False
        
        # Check cloud provider region mapping
        provider = storage_requirements.get("provider")
        region = storage_requirements.get("region")
        
        if provider and region:
            provider_regions = self.cloud_provider_regions.get(provider, {})
            if region in provider_regions:
                region_jurisdiction = provider_regions[region]["jurisdiction"]
                if region_jurisdiction != jurisdiction:
                    violations.append(f"Region {region} is in {region_jurisdiction}, not {jurisdiction}")
                    compliant = False
        
        return {
            "compliant": compliant,
            "violations": violations,
            "recommendations": await self._generate_compliance_recommendations(jurisdiction, data_type)
        }
    
    async def _generate_compliance_recommendations(
        self, jurisdiction: str, data_type: DataCategory
    ) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if jurisdiction == "EU":
            recommendations.extend([
                "Ensure GDPR compliance with appropriate technical and organizational measures",
                "Implement data minimization and purpose limitation",
                "Maintain records of processing activities"
            ])
            
            if data_type in [DataCategory.HEALTH_DATA, DataCategory.BIOMETRIC_DATA]:
                recommendations.append("Consider additional safeguards for special category data")
        
        elif jurisdiction == "US":
            if data_type == DataCategory.HEALTH_DATA:
                recommendations.extend([
                    "Ensure HIPAA compliance with appropriate safeguards",
                    "Implement business associate agreements where applicable"
                ])
            
            if data_type == DataCategory.FINANCIAL_DATA:
                recommendations.extend([
                    "Consider SOX and GLBA compliance requirements",
                    "Implement financial data protection measures"
                ])
        
        elif jurisdiction == "CN":
            recommendations.extend([
                "Conduct cybersecurity review for cross-border transfers",
                "Ensure compliance with Cybersecurity Law requirements"
            ])
        
        return recommendations
    
    async def check_compliance(self, data_id: str) -> Dict[str, Any]:
        """Check data residency compliance for specific data"""
        try:
            # Find all locations for this data
            data_locations = [
                loc for loc in self.data_locations.values() 
                if loc.data_id == data_id
            ]
            
            if not data_locations:
                return {
                    "compliant": False,
                    "reason": "No location records found",
                    "recommendations": ["Register data location for compliance tracking"]
                }
            
            compliance_results = []
            overall_compliant = True
            
            for location in data_locations:
                # Check location compliance
                location_compliance = await self._check_location_compliance(location)
                compliance_results.append({
                    "location_id": location.location_id,
                    "jurisdiction": location.jurisdiction,
                    "compliant": location_compliance["compliant"],
                    "issues": location_compliance.get("issues", []),
                    "last_verified": location.last_verified
                })
                
                if not location_compliance["compliant"]:
                    overall_compliant = False
            
            # Check for jurisdiction conflicts
            jurisdictions = set(loc.jurisdiction for loc in data_locations)
            jurisdiction_conflicts = await self._check_jurisdiction_conflicts(jurisdictions)
            
            return {
                "data_id": data_id,
                "overall_compliant": overall_compliant and not jurisdiction_conflicts["has_conflicts"],
                "locations": compliance_results,
                "jurisdiction_conflicts": jurisdiction_conflicts,
                "last_checked": datetime.utcnow(),
                "recommendations": await self._generate_remediation_recommendations(compliance_results)
            }
            
        except Exception as e:
            logger.error(f"Compliance check failed for data {data_id}: {e}")
            return {
                "compliant": False,
                "error": str(e),
                "last_checked": datetime.utcnow()
            }
    
    async def _check_location_compliance(self, location: DataLocation) -> Dict[str, Any]:
        """Check compliance for a specific location"""
        issues = []
        compliant = True
        
        # Check if location is still valid
        if location.jurisdiction in self.jurisdiction_rules:
            rules = self.jurisdiction_rules[location.jurisdiction]
            
            # Check allowed regions
            if rules.get("data_localization_required", False):
                allowed_regions = rules.get("allowed_regions", [])
                # This would need actual region detection in production
                # For now, assume compliance based on registration
        
        # Check certification validity
        required_certs = await self._get_required_certifications(location.jurisdiction)
        missing_certs = set(required_certs) - set(location.compliance_certifications)
        
        if missing_certs:
            issues.append(f"Missing certifications: {', '.join(missing_certs)}")
            compliant = False
        
        # Check last verification time
        verification_threshold = datetime.utcnow() - timedelta(days=90)  # 90 days
        if location.last_verified < verification_threshold:
            issues.append("Location verification is overdue")
            # Don't mark as non-compliant, but flag for attention
        
        return {
            "compliant": compliant,
            "issues": issues
        }
    
    async def _check_jurisdiction_conflicts(self, jurisdictions: Set[str]) -> Dict[str, Any]:
        """Check for conflicts between jurisdictions"""
        conflicts = []
        has_conflicts = False
        
        # Check for conflicting requirements
        jurisdiction_list = list(jurisdictions)
        for i, jurisdiction1 in enumerate(jurisdiction_list):
            for jurisdiction2 in jurisdiction_list[i+1:]:
                conflict = await self._check_jurisdiction_pair_conflict(jurisdiction1, jurisdiction2)
                if conflict["has_conflict"]:
                    conflicts.append(conflict)
                    has_conflicts = True
        
        return {
            "has_conflicts": has_conflicts,
            "conflicts": conflicts,
            "jurisdictions_involved": list(jurisdictions)
        }
    
    async def _check_jurisdiction_pair_conflict(self, jurisdiction1: str, jurisdiction2: str) -> Dict[str, Any]:
        """Check for conflicts between two jurisdictions"""
        rules1 = self.jurisdiction_rules.get(jurisdiction1, {})
        rules2 = self.jurisdiction_rules.get(jurisdiction2, {})
        
        conflicts = []
        
        # Check cross-border restrictions
        restrictions1 = rules1.get("cross_border_restrictions", {})
        restrictions2 = rules2.get("cross_border_restrictions", {})
        
        # Check prohibited countries
        prohibited1 = restrictions1.get("prohibited_countries", [])
        prohibited2 = restrictions2.get("prohibited_countries", [])
        
        if jurisdiction2 in prohibited1:
            conflicts.append(f"{jurisdiction1} prohibits data transfer to {jurisdiction2}")
        
        if jurisdiction1 in prohibited2:
            conflicts.append(f"{jurisdiction2} prohibits data transfer from {jurisdiction1}")
        
        return {
            "has_conflict": len(conflicts) > 0,
            "jurisdiction1": jurisdiction1,
            "jurisdiction2": jurisdiction2,
            "conflicts": conflicts
        }
    
    async def _get_required_certifications(self, jurisdiction: str) -> List[str]:
        """Get required certifications for jurisdiction"""
        certification_map = {
            "EU": ["ISO27001", "SOC2_Type2"],
            "US": ["SOC2_Type2", "FedRAMP"],
            "CA": ["ISO27001", "SOC2_Type2"],
            "CN": ["GB/T 22080", "ISO27001"],
            "IN": ["ISO27001", "CERT-In_Empanelled"]
        }
        
        return certification_map.get(jurisdiction, ["ISO27001"])
    
    async def _generate_remediation_recommendations(self, compliance_results: List[Dict]) -> List[str]:
        """Generate recommendations for compliance remediation"""
        recommendations = []
        
        # Analyze compliance issues
        all_issues = []
        for result in compliance_results:
            all_issues.extend(result.get("issues", []))
        
        if not all_issues:
            return ["Maintain current compliance posture with regular reviews"]
        
        # Generate specific recommendations based on issues
        if any("certification" in issue.lower() for issue in all_issues):
            recommendations.append("Obtain missing compliance certifications")
        
        if any("verification" in issue.lower() for issue in all_issues):
            recommendations.append("Schedule location verification audits")
        
        if any("encryption" in issue.lower() for issue in all_issues):
            recommendations.append("Implement or verify encryption for data at rest and in transit")
        
        if any("audit" in issue.lower() for issue in all_issues):
            recommendations.append("Enhance audit logging and monitoring capabilities")
        
        return recommendations
    
    async def _setup_location_monitoring(self, location_id: str):
        """Set up monitoring for a data location"""
        try:
            # Schedule periodic compliance checks
            # In production, this would integrate with monitoring systems
            logger.info(f"Monitoring setup for location {location_id}")
            
        except Exception as e:
            logger.error(f"Failed to setup monitoring for {location_id}: {e}")
    
    async def monitor_compliance(self):
        """Monitor all registered locations for compliance"""
        try:
            compliance_issues = []
            
            for location_id, location in self.data_locations.items():
                compliance_result = await self._check_location_compliance(location)
                
                if not compliance_result["compliant"]:
                    compliance_issues.append({
                        "location_id": location_id,
                        "data_id": location.data_id,
                        "jurisdiction": location.jurisdiction,
                        "issues": compliance_result["issues"],
                        "detected_at": datetime.utcnow()
                    })
            
            # Generate alerts for compliance issues
            if compliance_issues:
                await self._generate_compliance_alerts(compliance_issues)
            
            logger.info(f"Compliance monitoring completed. Found {len(compliance_issues)} issues.")
            
        except Exception as e:
            logger.error(f"Compliance monitoring failed: {e}")
    
    async def _generate_compliance_alerts(self, issues: List[Dict]):
        """Generate alerts for compliance issues"""
        for issue in issues:
            alert = {
                "alert_id": f"compliance_alert_{int(datetime.utcnow().timestamp())}",
                "type": "data_residency_violation",
                "severity": "high" if "certification" in str(issue["issues"]) else "medium",
                "location_id": issue["location_id"],
                "data_id": issue["data_id"],
                "jurisdiction": issue["jurisdiction"],
                "issues": issue["issues"],
                "created_at": datetime.utcnow(),
                "status": "open"
            }
            
            self.monitoring_alerts.append(alert)
            logger.warning(f"Compliance alert generated: {alert['alert_id']}")
    
    async def get_residency_report(self, jurisdiction: Optional[str] = None) -> Dict[str, Any]:
        """Generate data residency compliance report"""
        try:
            # Filter locations by jurisdiction if specified
            locations = list(self.data_locations.values())
            if jurisdiction:
                locations = [loc for loc in locations if loc.jurisdiction == jurisdiction]
            
            # Calculate compliance statistics
            total_locations = len(locations)
            compliant_locations = 0
            compliance_issues = []
            
            for location in locations:
                compliance_result = await self._check_location_compliance(location)
                if compliance_result["compliant"]:
                    compliant_locations += 1
                else:
                    compliance_issues.extend(compliance_result["issues"])
            
            # Generate jurisdiction distribution
            jurisdiction_distribution = {}
            for location in locations:
                jurisdiction_distribution[location.jurisdiction] = \
                    jurisdiction_distribution.get(location.jurisdiction, 0) + 1
            
            return {
                "report_generated": datetime.utcnow(),
                "scope": jurisdiction or "all_jurisdictions",
                "total_data_locations": total_locations,
                "compliant_locations": compliant_locations,
                "compliance_rate": (compliant_locations / total_locations * 100) if total_locations > 0 else 0,
                "jurisdiction_distribution": jurisdiction_distribution,
                "active_alerts": len([a for a in self.monitoring_alerts if a["status"] == "open"]),
                "common_issues": list(set(compliance_issues)),
                "recommendations": await self._generate_remediation_recommendations([
                    {"issues": compliance_issues}
                ])
            }
            
        except Exception as e:
            logger.error(f"Residency report generation failed: {e}")
            return {"error": str(e)}
    
    async def relocate_data(
        self,
        data_id: str,
        new_location: str,
        new_jurisdiction: str,
        migration_plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Relocate data to new jurisdiction"""
        try:
            # Validate new location compliance
            validation_result = await self._validate_location_compliance(
                new_location,
                migration_plan.get("data_type", DataCategory.PERSONAL_DATA),
                new_jurisdiction,
                migration_plan
            )
            
            if not validation_result["compliant"]:
                raise ValueError(f"New location not compliant: {validation_result['violations']}")
            
            # Create migration record
            migration_id = f"migration_{data_id}_{int(datetime.utcnow().timestamp())}"
            
            # Register new location
            new_location_id = await self.register_data_location(
                data_id=data_id,
                location=new_location,
                data_type=migration_plan.get("data_type", DataCategory.PERSONAL_DATA),
                jurisdiction=new_jurisdiction,
                storage_requirements=migration_plan
            )
            
            # Mark old locations for decommissioning
            old_locations = [
                loc for loc in self.data_locations.values() 
                if loc.data_id == data_id and loc.location_id != new_location_id
            ]
            
            return {
                "migration_id": migration_id,
                "new_location_id": new_location_id,
                "old_locations_count": len(old_locations),
                "status": "initiated",
                "compliance_validated": True
            }
            
        except Exception as e:
            logger.error(f"Data relocation failed: {e}")
            raise