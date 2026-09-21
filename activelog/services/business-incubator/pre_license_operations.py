"""
Pre-License Business Operations
Handles business operations before official licensing and registration
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

class PreLicenseStage(str, Enum):
    CONCEPT = "concept"
    VALIDATION = "validation"
    PROTOTYPE = "prototype"
    PRE_REVENUE = "pre_revenue"
    READY_FOR_LICENSE = "ready_for_license"

class ComplianceStatus(str, Enum):
    COMPLIANT = "compliant"
    NEEDS_ATTENTION = "needs_attention"
    NON_COMPLIANT = "non_compliant"

class OperationRestriction(BaseModel):
    """Operational restrictions for pre-license businesses"""
    id: str
    type: str  # revenue_cap, customer_limit, geographic, activity
    description: str
    limit_value: Optional[float] = None
    limit_unit: str = ""
    is_active: bool = True
    expiry_date: Optional[datetime] = None

class PreLicenseActivity(BaseModel):
    """Tracked activity for pre-license business"""
    id: str
    business_id: str
    activity_type: str  # customer_contact, revenue_generation, marketing, development
    description: str
    value: Optional[float] = None
    currency: str = "CCC"
    date: datetime
    
    # Compliance tracking
    is_compliant: bool = True
    compliance_notes: str = ""
    requires_review: bool = False

class PreLicenseCompliance(BaseModel):
    """Compliance tracking for pre-license operations"""
    business_id: str
    current_stage: PreLicenseStage
    compliance_score: float  # 0-100
    status: ComplianceStatus
    
    # Metrics
    total_revenue: float = 0.0
    total_customers: int = 0
    days_operating: int = 0
    
    # Restrictions
    active_restrictions: List[OperationRestriction] = []
    
    # Compliance checks
    last_review_date: datetime
    next_review_date: datetime
    compliance_issues: List[str] = []
    
    # Transition readiness
    license_readiness_score: float = 0.0
    missing_requirements: List[str] = []

class PreLicenseManager:
    """Manages pre-license business operations"""
    
    def __init__(self):
        self.pre_license_businesses: Dict[str, PreLicenseCompliance] = {}
        self.activities: Dict[str, List[PreLicenseActivity]] = {}
        self.restrictions_templates = self._load_restriction_templates()
        
    def _load_restriction_templates(self) -> Dict[str, Dict]:
        """Load pre-license restriction templates"""
        return {
            "concept_stage": {
                "max_revenue": 1000.0,  # CCC
                "max_customers": 10,
                "allowed_activities": ["market_research", "product_development", "networking"],
                "duration_days": 90
            },
            "validation_stage": {
                "max_revenue": 5000.0,  # CCC
                "max_customers": 50,
                "allowed_activities": ["customer_interviews", "mvp_testing", "pilot_programs"],
                "duration_days": 180
            },
            "prototype_stage": {
                "max_revenue": 15000.0,  # CCC
                "max_customers": 100,
                "allowed_activities": ["beta_testing", "limited_sales", "feedback_collection"],
                "duration_days": 270
            },
            "pre_revenue_stage": {
                "max_revenue": 50000.0,  # CCC
                "max_customers": 500,
                "allowed_activities": ["soft_launch", "pre_orders", "limited_marketing"],
                "duration_days": 365
            }
        }
    
    def register_pre_license_business(self, business_id: str, owner_id: str,
                                    initial_stage: PreLicenseStage = PreLicenseStage.CONCEPT) -> str:
        """Register business for pre-license operations"""
        
        compliance_id = str(uuid.uuid4())
        
        # Get stage restrictions
        stage_template = self.restrictions_templates.get(f"{initial_stage.value}_stage", {})
        restrictions = self._create_stage_restrictions(initial_stage, stage_template)
        
        compliance = PreLicenseCompliance(
            business_id=business_id,
            current_stage=initial_stage,
            compliance_score=100.0,  # Start fully compliant
            status=ComplianceStatus.COMPLIANT,
            active_restrictions=restrictions,
            last_review_date=datetime.now(),
            next_review_date=datetime.now() + timedelta(days=30),
            license_readiness_score=self._calculate_license_readiness(initial_stage)
        )
        
        self.pre_license_businesses[business_id] = compliance
        self.activities[business_id] = []
        
        return compliance_id
    
    def _create_stage_restrictions(self, stage: PreLicenseStage, template: Dict) -> List[OperationRestriction]:
        """Create restrictions based on stage template"""
        restrictions = []
        
        if "max_revenue" in template:
            restrictions.append(OperationRestriction(
                id=str(uuid.uuid4()),
                type="revenue_cap",
                description=f"Maximum revenue limit for {stage.value} stage",
                limit_value=template["max_revenue"],
                limit_unit="CCC",
                expiry_date=datetime.now() + timedelta(days=template.get("duration_days", 90))
            ))
        
        if "max_customers" in template:
            restrictions.append(OperationRestriction(
                id=str(uuid.uuid4()),
                type="customer_limit",
                description=f"Maximum customer limit for {stage.value} stage",
                limit_value=template["max_customers"],
                limit_unit="customers",
                expiry_date=datetime.now() + timedelta(days=template.get("duration_days", 90))
            ))
        
        # Activity restrictions
        if "allowed_activities" in template:
            for activity in ["customer_contact", "revenue_generation", "marketing"]:
                if activity not in template["allowed_activities"]:
                    restrictions.append(OperationRestriction(
                        id=str(uuid.uuid4()),
                        type="activity",
                        description=f"Restricted activity: {activity}",
                        is_active=True
                    ))
        
        return restrictions
    
    def record_activity(self, business_id: str, activity_type: str, description: str,
                       value: Optional[float] = None, currency: str = "CCC") -> str:
        """Record business activity"""
        
        if business_id not in self.pre_license_businesses:
            raise ValueError("Business not registered for pre-license operations")
        
        activity_id = str(uuid.uuid4())
        
        # Check compliance
        compliance_check = self._check_activity_compliance(business_id, activity_type, value)
        
        activity = PreLicenseActivity(
            id=activity_id,
            business_id=business_id,
            activity_type=activity_type,
            description=description,
            value=value,
            currency=currency,
            date=datetime.now(),
            is_compliant=compliance_check["is_compliant"],
            compliance_notes=compliance_check.get("notes", ""),
            requires_review=compliance_check.get("requires_review", False)
        )
        
        self.activities[business_id].append(activity)
        
        # Update compliance metrics
        self._update_compliance_metrics(business_id, activity)
        
        return activity_id
    
    def _check_activity_compliance(self, business_id: str, activity_type: str, 
                                  value: Optional[float]) -> Dict[str, Any]:
        """Check if activity complies with pre-license restrictions"""
        
        compliance = self.pre_license_businesses[business_id]
        result = {"is_compliant": True, "notes": "", "requires_review": False}
        
        # Check revenue restrictions
        if activity_type == "revenue_generation" and value:
            revenue_restriction = next(
                (r for r in compliance.active_restrictions if r.type == "revenue_cap"),
                None
            )
            
            if revenue_restriction:
                current_revenue = compliance.total_revenue + value
                if current_revenue > revenue_restriction.limit_value:
                    result["is_compliant"] = False
                    result["notes"] = f"Revenue cap exceeded: {current_revenue} > {revenue_restriction.limit_value}"
                    result["requires_review"] = True
        
        # Check customer restrictions
        if activity_type == "customer_acquisition":
            customer_restriction = next(
                (r for r in compliance.active_restrictions if r.type == "customer_limit"),
                None
            )
            
            if customer_restriction:
                if compliance.total_customers >= customer_restriction.limit_value:
                    result["is_compliant"] = False
                    result["notes"] = f"Customer limit reached: {compliance.total_customers}"
                    result["requires_review"] = True
        
        # Check activity restrictions
        activity_restrictions = [r for r in compliance.active_restrictions 
                               if r.type == "activity" and activity_type in r.description.lower()]
        
        if activity_restrictions:
            result["is_compliant"] = False
            result["notes"] = f"Activity '{activity_type}' is restricted at current stage"
            result["requires_review"] = True
        
        return result
    
    def _update_compliance_metrics(self, business_id: str, activity: PreLicenseActivity):
        """Update compliance metrics after activity"""
        
        compliance = self.pre_license_businesses[business_id]
        
        # Update revenue
        if activity.activity_type == "revenue_generation" and activity.value:
            compliance.total_revenue += activity.value
        
        # Update customer count
        if activity.activity_type == "customer_acquisition":
            compliance.total_customers += 1
        
        # Update days operating
        start_date = min(a.date for a in self.activities[business_id]) if self.activities[business_id] else datetime.now()
        compliance.days_operating = (datetime.now() - start_date).days
        
        # Recalculate compliance score
        compliance.compliance_score = self._calculate_compliance_score(business_id)
        
        # Update status
        if compliance.compliance_score < 70:
            compliance.status = ComplianceStatus.NON_COMPLIANT
        elif compliance.compliance_score < 85:
            compliance.status = ComplianceStatus.NEEDS_ATTENTION
        else:
            compliance.status = ComplianceStatus.COMPLIANT
        
        # Update license readiness
        compliance.license_readiness_score = self._calculate_license_readiness(compliance.current_stage)
    
    def _calculate_compliance_score(self, business_id: str) -> float:
        """Calculate overall compliance score"""
        
        compliance = self.pre_license_businesses[business_id]
        business_activities = self.activities.get(business_id, [])
        
        score = 100.0
        
        # Deduct points for non-compliant activities
        non_compliant_activities = [a for a in business_activities if not a.is_compliant]
        score -= len(non_compliant_activities) * 10
        
        # Deduct points for exceeding restrictions
        for restriction in compliance.active_restrictions:
            if restriction.type == "revenue_cap" and compliance.total_revenue > restriction.limit_value:
                over_limit = (compliance.total_revenue - restriction.limit_value) / restriction.limit_value
                score -= min(over_limit * 50, 30)  # Max 30 point deduction
            
            if restriction.type == "customer_limit" and compliance.total_customers > restriction.limit_value:
                over_limit = (compliance.total_customers - restriction.limit_value) / restriction.limit_value
                score -= min(over_limit * 40, 25)  # Max 25 point deduction
        
        return max(score, 0.0)
    
    def _calculate_license_readiness(self, stage: PreLicenseStage) -> float:
        """Calculate readiness for business licensing"""
        
        readiness_scores = {
            PreLicenseStage.CONCEPT: 20.0,
            PreLicenseStage.VALIDATION: 40.0,
            PreLicenseStage.PROTOTYPE: 60.0,
            PreLicenseStage.PRE_REVENUE: 80.0,
            PreLicenseStage.READY_FOR_LICENSE: 95.0
        }
        
        return readiness_scores.get(stage, 0.0)
    
    def advance_stage(self, business_id: str, new_stage: PreLicenseStage) -> bool:
        """Advance business to next pre-license stage"""
        
        if business_id not in self.pre_license_businesses:
            raise ValueError("Business not registered for pre-license operations")
        
        compliance = self.pre_license_businesses[business_id]
        
        # Check if advancement is allowed
        if not self._can_advance_stage(business_id, new_stage):
            return False
        
        # Update stage
        old_stage = compliance.current_stage
        compliance.current_stage = new_stage
        
        # Update restrictions
        stage_template = self.restrictions_templates.get(f"{new_stage.value}_stage", {})
        compliance.active_restrictions = self._create_stage_restrictions(new_stage, stage_template)
        
        # Update readiness score
        compliance.license_readiness_score = self._calculate_license_readiness(new_stage)
        
        # Reset some metrics for new stage
        compliance.next_review_date = datetime.now() + timedelta(days=30)
        
        # Update missing requirements
        compliance.missing_requirements = self._get_missing_requirements(business_id, new_stage)
        
        return True
    
    def _can_advance_stage(self, business_id: str, new_stage: PreLicenseStage) -> bool:
        """Check if business can advance to new stage"""
        
        compliance = self.pre_license_businesses[business_id]
        
        # Must be compliant to advance
        if compliance.status == ComplianceStatus.NON_COMPLIANT:
            return False
        
        # Stage progression rules
        stage_order = [
            PreLicenseStage.CONCEPT,
            PreLicenseStage.VALIDATION,
            PreLicenseStage.PROTOTYPE,
            PreLicenseStage.PRE_REVENUE,
            PreLicenseStage.READY_FOR_LICENSE
        ]
        
        current_index = stage_order.index(compliance.current_stage)
        new_index = stage_order.index(new_stage)
        
        # Can only advance one stage at a time
        return new_index == current_index + 1
    
    def _get_missing_requirements(self, business_id: str, stage: PreLicenseStage) -> List[str]:
        """Get missing requirements for license readiness"""
        
        missing = []
        
        if stage == PreLicenseStage.VALIDATION:
            missing.extend([
                "Market research documentation",
                "Customer interview results",
                "Competitive analysis"
            ])
        
        elif stage == PreLicenseStage.PROTOTYPE:
            missing.extend([
                "Working prototype or MVP",
                "User testing results",
                "Technical documentation"
            ])
        
        elif stage == PreLicenseStage.PRE_REVENUE:
            missing.extend([
                "Revenue model validation",
                "Pricing strategy",
                "Early customer testimonials"
            ])
        
        elif stage == PreLicenseStage.READY_FOR_LICENSE:
            missing.extend([
                "Business plan",
                "Financial projections",
                "Legal structure documentation",
                "Compliance documentation"
            ])
        
        return missing
    
    def get_compliance_report(self, business_id: str) -> Dict[str, Any]:
        """Generate compliance report for business"""
        
        if business_id not in self.pre_license_businesses:
            raise ValueError("Business not registered for pre-license operations")
        
        compliance = self.pre_license_businesses[business_id]
        business_activities = self.activities.get(business_id, [])
        
        # Activity summary
        activity_summary = {}
        for activity in business_activities:
            activity_type = activity.activity_type
            if activity_type not in activity_summary:
                activity_summary[activity_type] = {"count": 0, "total_value": 0.0, "compliant": 0}
            
            activity_summary[activity_type]["count"] += 1
            if activity.value:
                activity_summary[activity_type]["total_value"] += activity.value
            if activity.is_compliant:
                activity_summary[activity_type]["compliant"] += 1
        
        # Restriction status
        restriction_status = []
        for restriction in compliance.active_restrictions:
            status = {
                "type": restriction.type,
                "description": restriction.description,
                "limit": restriction.limit_value,
                "unit": restriction.limit_unit,
                "is_active": restriction.is_active
            }
            
            if restriction.type == "revenue_cap":
                status["current_value"] = compliance.total_revenue
                status["utilization"] = (compliance.total_revenue / restriction.limit_value * 100) if restriction.limit_value else 0
            elif restriction.type == "customer_limit":
                status["current_value"] = compliance.total_customers
                status["utilization"] = (compliance.total_customers / restriction.limit_value * 100) if restriction.limit_value else 0
            
            restriction_status.append(status)
        
        return {
            "business_id": business_id,
            "current_stage": compliance.current_stage.value,
            "compliance_score": compliance.compliance_score,
            "status": compliance.status.value,
            "license_readiness_score": compliance.license_readiness_score,
            "days_operating": compliance.days_operating,
            "total_revenue": compliance.total_revenue,
            "total_customers": compliance.total_customers,
            "activity_summary": activity_summary,
            "restrictions": restriction_status,
            "missing_requirements": compliance.missing_requirements,
            "compliance_issues": compliance.compliance_issues,
            "next_review_date": compliance.next_review_date.isoformat(),
            "recommendations": self._get_recommendations(business_id)
        }
    
    def _get_recommendations(self, business_id: str) -> List[str]:
        """Get recommendations for business improvement"""
        
        compliance = self.pre_license_businesses[business_id]
        recommendations = []
        
        if compliance.compliance_score < 85:
            recommendations.append("Review and address compliance issues to improve score")
        
        if compliance.license_readiness_score < 70:
            recommendations.append("Focus on completing requirements for next stage advancement")
        
        # Stage-specific recommendations
        if compliance.current_stage == PreLicenseStage.CONCEPT:
            recommendations.append("Conduct thorough market research and customer interviews")
        elif compliance.current_stage == PreLicenseStage.VALIDATION:
            recommendations.append("Develop MVP and collect user feedback")
        elif compliance.current_stage == PreLicenseStage.PROTOTYPE:
            recommendations.append("Test pricing model and prepare for limited revenue generation")
        elif compliance.current_stage == PreLicenseStage.PRE_REVENUE:
            recommendations.append("Prepare business documentation for full licensing")
        
        # Revenue utilization
        revenue_restriction = next(
            (r for r in compliance.active_restrictions if r.type == "revenue_cap"),
            None
        )
        if revenue_restriction:
            utilization = (compliance.total_revenue / revenue_restriction.limit_value) * 100
            if utilization > 80:
                recommendations.append("Consider advancing to next stage - approaching revenue limit")
            elif utilization < 30:
                recommendations.append("Explore opportunities to increase revenue within current limits")
        
        return recommendations
    
    def get_stage_transition_plan(self, business_id: str) -> Dict[str, Any]:
        """Get plan for transitioning to next stage or licensing"""
        
        if business_id not in self.pre_license_businesses:
            raise ValueError("Business not registered for pre-license operations")
        
        compliance = self.pre_license_businesses[business_id]
        current_stage = compliance.current_stage
        
        # Determine next stage
        stage_order = [
            PreLicenseStage.CONCEPT,
            PreLicenseStage.VALIDATION,
            PreLicenseStage.PROTOTYPE,
            PreLicenseStage.PRE_REVENUE,
            PreLicenseStage.READY_FOR_LICENSE
        ]
        
        current_index = stage_order.index(current_stage)
        
        if current_index == len(stage_order) - 1:
            # Ready for licensing
            next_step = "business_licensing"
            next_stage = None
        else:
            next_stage = stage_order[current_index + 1]
            next_step = f"advance_to_{next_stage.value}"
        
        # Get requirements
        if next_stage:
            requirements = self._get_missing_requirements(business_id, next_stage)
            timeline_days = 30 + (current_index * 30)  # Progressive timeline
        else:
            requirements = [
                "Complete business registration",
                "Obtain required licenses",
                "Set up full accounting system",
                "Transition to fiat currency operations"
            ]
            timeline_days = 90
        
        return {
            "current_stage": current_stage.value,
            "next_step": next_step,
            "next_stage": next_stage.value if next_stage else "licensed",
            "requirements": requirements,
            "estimated_timeline_days": timeline_days,
            "readiness_score": compliance.license_readiness_score,
            "blocking_issues": compliance.compliance_issues,
            "recommended_actions": self._get_recommendations(business_id)
        }