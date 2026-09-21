"""
Business Registration Automation
Automated business registration and compliance management system
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json
import asyncio

class BusinessType(str, Enum):
    SOLE_PROPRIETORSHIP = "sole_proprietorship"
    PARTNERSHIP = "partnership"
    LLC = "llc"
    CORPORATION = "corporation"
    NON_PROFIT = "non_profit"
    COOPERATIVE = "cooperative"

class RegistrationStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISSOLVED = "dissolved"

class LicenseType(str, Enum):
    BUSINESS_LICENSE = "business_license"
    SALES_TAX = "sales_tax"
    EMPLOYER_ID = "employer_id"
    WORKERS_COMP = "workers_comp"
    PROFESSIONAL = "professional"
    INDUSTRY_SPECIFIC = "industry_specific"
    IMPORT_EXPORT = "import_export"
    HEALTH_PERMIT = "health_permit"

class JurisdictionLevel(str, Enum):
    FEDERAL = "federal"
    STATE = "state"
    COUNTY = "county"
    CITY = "city"

class RegistrationRequirement(BaseModel):
    """Registration requirement for a business type"""
    id: str
    name: str
    description: str
    jurisdiction: JurisdictionLevel
    business_types: List[BusinessType]
    
    # Requirement details
    is_mandatory: bool = True
    estimated_cost: float = 0.0
    estimated_days: int = 7
    renewal_required: bool = False
    renewal_frequency_days: Optional[int] = None
    
    # Prerequisites
    prerequisites: List[str] = []
    
    # Forms and documents
    required_forms: List[str] = []
    required_documents: List[str] = []
    
    # Online filing
    supports_online_filing: bool = False
    filing_url: Optional[str] = None
    api_available: bool = False

class BusinessRegistration(BaseModel):
    """Business registration record"""
    id: str
    business_id: str
    business_name: str
    business_type: BusinessType
    
    # Business details
    owner_name: str
    owner_ssn: Optional[str] = None  # Encrypted in production
    business_address: Dict[str, str]
    mailing_address: Optional[Dict[str, str]] = None
    phone: str
    email: str
    website: Optional[str] = None
    
    # Industry classification
    naics_code: str
    industry_description: str
    
    # Registration status
    status: RegistrationStatus = RegistrationStatus.DRAFT
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    
    # Required licenses and permits
    required_licenses: List[str] = []
    obtained_licenses: List[str] = []
    pending_licenses: List[str] = []
    
    # Registration numbers
    ein: Optional[str] = None  # Employer Identification Number
    state_id: Optional[str] = None
    city_license: Optional[str] = None
    
    # Compliance
    compliance_score: float = 0.0
    last_compliance_check: Optional[datetime] = None
    
    created_at: datetime
    updated_at: datetime

class LicenseApplication(BaseModel):
    """License application record"""
    id: str
    registration_id: str
    license_type: LicenseType
    jurisdiction: JurisdictionLevel
    
    # Application details
    application_number: Optional[str] = None
    submitted_at: Optional[datetime] = None
    status: str = "draft"
    
    # Requirements
    required_documents: List[str] = []
    submitted_documents: List[str] = []
    missing_documents: List[str] = []
    
    # Fees
    application_fee: float = 0.0
    renewal_fee: float = 0.0
    paid: bool = False
    payment_date: Optional[datetime] = None
    
    # Timeline
    estimated_approval_days: int = 30
    actual_approval_days: Optional[int] = None
    expires_at: Optional[datetime] = None
    
    # Follow-up
    follow_up_required: bool = False
    follow_up_date: Optional[datetime] = None
    notes: str = ""

class RegistrationAutomation:
    """Automated business registration system"""
    
    def __init__(self):
        self.registrations: Dict[str, BusinessRegistration] = {}
        self.license_applications: Dict[str, LicenseApplication] = {}
        self.requirements: Dict[str, RegistrationRequirement] = {}
        self.jurisdiction_data = self._load_jurisdiction_data()
        
        # Load default requirements
        self._load_default_requirements()
    
    def _load_jurisdiction_data(self) -> Dict[str, Dict]:
        """Load jurisdiction-specific data"""
        return {
            "federal": {
                "name": "Federal",
                "processing_time_days": 30,
                "online_filing": True,
                "api_available": False
            },
            "state": {
                "name": "State",
                "processing_time_days": 14,
                "online_filing": True,
                "api_available": True
            },
            "county": {
                "name": "County",
                "processing_time_days": 7,
                "online_filing": False,
                "api_available": False
            },
            "city": {
                "name": "City",
                "processing_time_days": 5,
                "online_filing": True,
                "api_available": False
            }
        }
    
    def _load_default_requirements(self):
        """Load default registration requirements"""
        
        default_requirements = [
            # Federal requirements
            {
                "name": "Federal EIN",
                "description": "Employer Identification Number from IRS",
                "jurisdiction": JurisdictionLevel.FEDERAL,
                "business_types": [BusinessType.LLC, BusinessType.CORPORATION, BusinessType.PARTNERSHIP],
                "is_mandatory": True,
                "estimated_cost": 0.0,
                "estimated_days": 2,
                "supports_online_filing": True,
                "filing_url": "https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online",
                "required_forms": ["SS-4"],
                "required_documents": ["Articles of Incorporation", "Operating Agreement"]
            },
            
            # State requirements
            {
                "name": "State Business Registration",
                "description": "Register business entity with state",
                "jurisdiction": JurisdictionLevel.STATE,
                "business_types": [BusinessType.LLC, BusinessType.CORPORATION],
                "is_mandatory": True,
                "estimated_cost": 150.0,
                "estimated_days": 7,
                "supports_online_filing": True,
                "required_forms": ["Articles of Incorporation", "Certificate of Formation"],
                "required_documents": ["Registered Agent Information", "Operating Agreement"]
            },
            
            {
                "name": "State Sales Tax Permit",
                "description": "Permission to collect and remit sales tax",
                "jurisdiction": JurisdictionLevel.STATE,
                "business_types": [bt for bt in BusinessType],
                "is_mandatory": False,
                "estimated_cost": 0.0,
                "estimated_days": 5,
                "supports_online_filing": True,
                "required_documents": ["Business Registration", "EIN"]
            },
            
            # Local requirements
            {
                "name": "City Business License",
                "description": "General business license from city",
                "jurisdiction": JurisdictionLevel.CITY,
                "business_types": [bt for bt in BusinessType],
                "is_mandatory": True,
                "estimated_cost": 75.0,
                "estimated_days": 3,
                "renewal_required": True,
                "renewal_frequency_days": 365,
                "supports_online_filing": True,
                "required_documents": ["State Registration", "Zoning Approval"]
            },
            
            {
                "name": "County Business Permit",
                "description": "County-level business permit",
                "jurisdiction": JurisdictionLevel.COUNTY,
                "business_types": [bt for bt in BusinessType],
                "is_mandatory": False,
                "estimated_cost": 50.0,
                "estimated_days": 5,
                "supports_online_filing": False,
                "required_documents": ["City License", "Zoning Certificate"]
            }
        ]
        
        for req_data in default_requirements:
            req_id = str(uuid.uuid4())
            requirement = RegistrationRequirement(
                id=req_id,
                **req_data
            )
            self.requirements[req_id] = requirement
    
    def start_registration(self, business_id: str, business_name: str, 
                          business_type: BusinessType, owner_name: str,
                          business_address: Dict[str, str], phone: str, email: str,
                          naics_code: str, industry_description: str) -> str:
        """Start business registration process"""
        
        registration_id = str(uuid.uuid4())
        
        registration = BusinessRegistration(
            id=registration_id,
            business_id=business_id,
            business_name=business_name,
            business_type=business_type,
            owner_name=owner_name,
            business_address=business_address,
            phone=phone,
            email=email,
            naics_code=naics_code,
            industry_description=industry_description,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Determine required licenses
        registration.required_licenses = self._get_required_licenses(business_type, naics_code)
        
        self.registrations[registration_id] = registration
        return registration_id
    
    def _get_required_licenses(self, business_type: BusinessType, naics_code: str) -> List[str]:
        """Determine required licenses based on business type and industry"""
        
        required_licenses = []
        
        # Basic requirements for all businesses
        required_licenses.append("City Business License")
        
        # Business type specific requirements
        if business_type in [BusinessType.LLC, BusinessType.CORPORATION]:
            required_licenses.append("State Business Registration")
            required_licenses.append("Federal EIN")
        
        # Industry specific requirements (simplified)
        if naics_code.startswith("44") or naics_code.startswith("45"):  # Retail
            required_licenses.append("State Sales Tax Permit")
        
        if naics_code.startswith("72"):  # Food service
            required_licenses.append("Health Permit")
        
        if naics_code.startswith("62"):  # Healthcare
            required_licenses.append("Professional License")
        
        return required_licenses
    
    def get_registration_checklist(self, registration_id: str) -> Dict[str, Any]:
        """Get complete registration checklist"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            raise ValueError("Registration not found")
        
        checklist_items = []
        total_estimated_cost = 0.0
        total_estimated_days = 0
        
        # Find applicable requirements
        applicable_requirements = []
        for requirement in self.requirements.values():
            if (registration.business_type in requirement.business_types or
                not requirement.business_types):  # Empty list means applies to all
                
                # Check if license name matches required licenses
                if any(license_name in requirement.name for license_name in registration.required_licenses):
                    applicable_requirements.append(requirement)
        
        # Sort by processing order (federal, state, county, city)
        jurisdiction_order = [JurisdictionLevel.FEDERAL, JurisdictionLevel.STATE, 
                            JurisdictionLevel.COUNTY, JurisdictionLevel.CITY]
        applicable_requirements.sort(key=lambda r: jurisdiction_order.index(r.jurisdiction))
        
        for requirement in applicable_requirements:
            item = {
                "id": requirement.id,
                "name": requirement.name,
                "description": requirement.description,
                "jurisdiction": requirement.jurisdiction.value,
                "is_mandatory": requirement.is_mandatory,
                "estimated_cost": requirement.estimated_cost,
                "estimated_days": requirement.estimated_days,
                "status": self._get_requirement_status(registration_id, requirement.name),
                "required_forms": requirement.required_forms,
                "required_documents": requirement.required_documents,
                "supports_online_filing": requirement.supports_online_filing,
                "filing_url": requirement.filing_url,
                "prerequisites": requirement.prerequisites,
                "renewal_required": requirement.renewal_required
            }
            
            checklist_items.append(item)
            total_estimated_cost += requirement.estimated_cost
            total_estimated_days = max(total_estimated_days, requirement.estimated_days)
        
        return {
            "registration_id": registration_id,
            "business_name": registration.business_name,
            "business_type": registration.business_type.value,
            "status": registration.status.value,
            "checklist_items": checklist_items,
            "total_estimated_cost": total_estimated_cost,
            "total_estimated_days": total_estimated_days,
            "completion_percentage": self._calculate_completion_percentage(registration_id),
            "next_steps": self._get_next_steps(registration_id)
        }
    
    def _get_requirement_status(self, registration_id: str, requirement_name: str) -> str:
        """Get status of specific requirement"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            return "unknown"
        
        if requirement_name in registration.obtained_licenses:
            return "completed"
        elif requirement_name in registration.pending_licenses:
            return "pending"
        else:
            return "not_started"
    
    def _calculate_completion_percentage(self, registration_id: str) -> float:
        """Calculate registration completion percentage"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            return 0.0
        
        total_licenses = len(registration.required_licenses)
        if total_licenses == 0:
            return 100.0
        
        completed_licenses = len(registration.obtained_licenses)
        return (completed_licenses / total_licenses) * 100.0
    
    def _get_next_steps(self, registration_id: str) -> List[str]:
        """Get recommended next steps"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            return []
        
        next_steps = []
        
        # Find incomplete requirements
        for req_name in registration.required_licenses:
            if (req_name not in registration.obtained_licenses and 
                req_name not in registration.pending_licenses):
                
                # Find the requirement details
                requirement = next(
                    (r for r in self.requirements.values() if req_name in r.name),
                    None
                )
                
                if requirement:
                    if requirement.supports_online_filing:
                        next_steps.append(f"File {req_name} online")
                    else:
                        next_steps.append(f"Visit office for {req_name}")
                    
                    # Only show first few next steps to avoid overwhelming
                    if len(next_steps) >= 3:
                        break
        
        return next_steps
    
    def submit_license_application(self, registration_id: str, license_type: str,
                                 documents: List[str] = None) -> str:
        """Submit license application"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            raise ValueError("Registration not found")
        
        # Find requirement details
        requirement = next(
            (r for r in self.requirements.values() if license_type in r.name),
            None
        )
        
        if not requirement:
            raise ValueError(f"Unknown license type: {license_type}")
        
        application_id = str(uuid.uuid4())
        
        application = LicenseApplication(
            id=application_id,
            registration_id=registration_id,
            license_type=LicenseType.BUSINESS_LICENSE,  # Simplified
            jurisdiction=requirement.jurisdiction,
            application_fee=requirement.estimated_cost,
            estimated_approval_days=requirement.estimated_days,
            required_documents=requirement.required_documents,
            submitted_documents=documents or [],
            submitted_at=datetime.now()
        )
        
        # Calculate missing documents
        application.missing_documents = list(
            set(application.required_documents) - set(application.submitted_documents)
        )
        
        # Set status based on document completeness
        if not application.missing_documents:
            application.status = "submitted"
            # Add to pending licenses
            if license_type not in registration.pending_licenses:
                registration.pending_licenses.append(license_type)
        else:
            application.status = "incomplete"
        
        self.license_applications[application_id] = application
        registration.updated_at = datetime.now()
        
        return application_id
    
    async def process_applications(self):
        """Process pending license applications (simulated)"""
        
        for application in self.license_applications.values():
            if application.status == "submitted":
                # Simulate processing time
                days_since_submission = (datetime.now() - application.submitted_at).days
                
                if days_since_submission >= application.estimated_approval_days:
                    # Approve application (simplified logic)
                    application.status = "approved"
                    application.actual_approval_days = days_since_submission
                    
                    # Update registration
                    registration = self.registrations.get(application.registration_id)
                    if registration:
                        license_name = self._get_license_name_from_application(application)
                        if license_name in registration.pending_licenses:
                            registration.pending_licenses.remove(license_name)
                        if license_name not in registration.obtained_licenses:
                            registration.obtained_licenses.append(license_name)
                        
                        # Update registration status
                        completion_pct = self._calculate_completion_percentage(registration.id)
                        if completion_pct >= 100:
                            registration.status = RegistrationStatus.ACTIVE
                            registration.approved_at = datetime.now()
                        
                        registration.updated_at = datetime.now()
    
    def _get_license_name_from_application(self, application: LicenseApplication) -> str:
        """Get license name from application"""
        # Simplified mapping
        return application.license_type.value.replace("_", " ").title()
    
    def check_renewal_requirements(self, registration_id: str) -> List[Dict[str, Any]]:
        """Check for licenses that need renewal"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            raise ValueError("Registration not found")
        
        renewals_needed = []
        
        for license_name in registration.obtained_licenses:
            requirement = next(
                (r for r in self.requirements.values() if license_name in r.name),
                None
            )
            
            if requirement and requirement.renewal_required:
                # Calculate renewal date (simplified)
                renewal_due = datetime.now() + timedelta(days=requirement.renewal_frequency_days or 365)
                
                renewals_needed.append({
                    "license_name": license_name,
                    "renewal_due": renewal_due.isoformat(),
                    "estimated_cost": requirement.estimated_cost,
                    "supports_online_filing": requirement.supports_online_filing,
                    "filing_url": requirement.filing_url
                })
        
        return renewals_needed
    
    def generate_compliance_report(self, registration_id: str) -> Dict[str, Any]:
        """Generate compliance report for business"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            raise ValueError("Registration not found")
        
        # Get all applications for this registration
        applications = [
            app for app in self.license_applications.values()
            if app.registration_id == registration_id
        ]
        
        # Calculate compliance metrics
        total_required = len(registration.required_licenses)
        completed = len(registration.obtained_licenses)
        pending = len(registration.pending_licenses)
        compliance_score = (completed / total_required * 100) if total_required > 0 else 100
        
        # Application statistics
        app_stats = {
            "total_applications": len(applications),
            "approved": len([a for a in applications if a.status == "approved"]),
            "pending": len([a for a in applications if a.status == "submitted"]),
            "incomplete": len([a for a in applications if a.status == "incomplete"])
        }
        
        # Cost analysis
        total_fees = sum(app.application_fee for app in applications)
        paid_fees = sum(app.application_fee for app in applications if app.paid)
        outstanding_fees = total_fees - paid_fees
        
        # Timeline analysis
        avg_processing_time = None
        approved_apps = [a for a in applications if a.actual_approval_days is not None]
        if approved_apps:
            avg_processing_time = sum(a.actual_approval_days for a in approved_apps) / len(approved_apps)
        
        return {
            "registration_id": registration_id,
            "business_name": registration.business_name,
            "registration_status": registration.status.value,
            "compliance_score": compliance_score,
            "licenses": {
                "required": total_required,
                "obtained": completed,
                "pending": pending,
                "missing": total_required - completed - pending
            },
            "applications": app_stats,
            "financial": {
                "total_fees": total_fees,
                "paid_fees": paid_fees,
                "outstanding_fees": outstanding_fees
            },
            "timeline": {
                "average_processing_days": avg_processing_time,
                "registration_age_days": (datetime.now() - registration.created_at).days
            },
            "renewals": len(self.check_renewal_requirements(registration_id)),
            "last_updated": registration.updated_at.isoformat()
        }
    
    def get_registration_timeline(self, registration_id: str) -> List[Dict[str, Any]]:
        """Get registration timeline/history"""
        
        registration = self.registrations.get(registration_id)
        if not registration:
            raise ValueError("Registration not found")
        
        timeline = []
        
        # Registration created
        timeline.append({
            "date": registration.created_at.isoformat(),
            "event": "Registration Started",
            "description": f"Business registration initiated for {registration.business_name}",
            "status": "completed"
        })
        
        # Application events
        applications = [
            app for app in self.license_applications.values()
            if app.registration_id == registration_id
        ]
        
        for app in applications:
            if app.submitted_at:
                timeline.append({
                    "date": app.submitted_at.isoformat(),
                    "event": f"{app.license_type.value} Application Submitted",
                    "description": f"Application submitted for {app.license_type.value}",
                    "status": "completed"
                })
            
            if app.status == "approved":
                approval_date = app.submitted_at + timedelta(days=app.actual_approval_days or 0)
                timeline.append({
                    "date": approval_date.isoformat(),
                    "event": f"{app.license_type.value} Approved",
                    "description": f"{app.license_type.value} application approved",
                    "status": "completed"
                })
        
        # Registration status changes
        if registration.approved_at:
            timeline.append({
                "date": registration.approved_at.isoformat(),
                "event": "Registration Completed",
                "description": "Business registration process completed",
                "status": "completed"
            })
        
        # Sort by date
        timeline.sort(key=lambda x: x["date"])
        
        return timeline
    
    def estimate_registration_timeline(self, business_type: BusinessType, 
                                     naics_code: str) -> Dict[str, Any]:
        """Estimate registration timeline for new business"""
        
        # Get required licenses for this business type
        required_licenses = self._get_required_licenses(business_type, naics_code)
        
        timeline_items = []
        total_cost = 0.0
        total_days = 0
        
        for license_name in required_licenses:
            requirement = next(
                (r for r in self.requirements.values() if license_name in r.name),
                None
            )
            
            if requirement:
                timeline_items.append({
                    "step": license_name,
                    "description": requirement.description,
                    "estimated_days": requirement.estimated_days,
                    "estimated_cost": requirement.estimated_cost,
                    "jurisdiction": requirement.jurisdiction.value,
                    "supports_online_filing": requirement.supports_online_filing,
                    "prerequisites": requirement.prerequisites
                })
                
                total_cost += requirement.estimated_cost
                total_days = max(total_days, requirement.estimated_days)
        
        return {
            "business_type": business_type.value,
            "naics_code": naics_code,
            "total_estimated_cost": total_cost,
            "total_estimated_days": total_days,
            "required_steps": len(timeline_items),
            "timeline": timeline_items,
            "recommendations": [
                "Gather all required documents before starting",
                "Consider hiring a registered agent for state filings",
                "Apply for EIN early as it's needed for other applications",
                "Check local zoning requirements before applying"
            ]
        }