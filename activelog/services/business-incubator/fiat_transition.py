"""
Fiat Currency Transition System
Manages the transition from CCC-only operations to fiat currency systems
"""

from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel
from datetime import datetime, timedelta
from enum import Enum
import uuid
import json

class TransitionStage(str, Enum):
    CCC_ONLY = "ccc_only"
    HYBRID_TESTING = "hybrid_testing"
    PARTIAL_FIAT = "partial_fiat"
    FULL_INTEGRATION = "full_integration"
    FIAT_PRIMARY = "fiat_primary"

class CurrencyMode(str, Enum):
    CCC_DOMINANT = "ccc_dominant"
    BALANCED = "balanced"
    FIAT_DOMINANT = "fiat_dominant"

class TransitionRequirement(BaseModel):
    """Requirement for transitioning to fiat currency"""
    id: str
    name: str
    description: str
    category: str  # legal, financial, technical, operational
    
    # Requirement details
    is_mandatory: bool = True
    completion_criteria: List[str]
    estimated_effort_hours: int = 0
    dependencies: List[str] = []
    
    # Status tracking
    is_completed: bool = False
    completed_at: Optional[datetime] = None
    completion_notes: str = ""

class FiatAccount(BaseModel):
    """Fiat currency account for business"""
    id: str
    business_id: str
    account_type: str  # checking, savings, merchant
    bank_name: str
    account_number: str  # Encrypted in production
    routing_number: str
    currency: str
    
    # Account status
    is_active: bool = True
    is_verified: bool = False
    verification_date: Optional[datetime] = None
    
    # Balances
    current_balance: float = 0.0
    available_balance: float = 0.0
    pending_balance: float = 0.0
    
    # Limits and fees
    daily_limit: Optional[float] = None
    monthly_fee: float = 0.0
    transaction_fee: float = 0.0
    
    created_at: datetime

class CurrencyExchangeRule(BaseModel):
    """Rules for automatic currency exchange"""
    id: str
    business_id: str
    name: str
    description: str
    
    # Exchange parameters
    from_currency: str
    to_currency: str
    trigger_condition: str  # balance_threshold, schedule, manual
    trigger_value: Optional[float] = None
    
    # Exchange limits
    min_exchange_amount: float = 0.0
    max_exchange_amount: Optional[float] = None
    exchange_percentage: float = 100.0  # % of available amount
    
    # Timing
    schedule_cron: Optional[str] = None
    is_active: bool = True
    
    # History
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    
    created_at: datetime

class TransitionPlan(BaseModel):
    """Comprehensive transition plan for business"""
    id: str
    business_id: str
    current_stage: TransitionStage
    target_stage: TransitionStage
    
    # Timeline
    start_date: datetime
    target_completion_date: datetime
    actual_completion_date: Optional[datetime] = None
    
    # Progress tracking
    completion_percentage: float = 0.0
    requirements_completed: int = 0
    requirements_total: int = 0
    
    # Configuration
    transition_speed: str = "gradual"  # gradual, accelerated, immediate
    risk_tolerance: str = "conservative"  # conservative, moderate, aggressive
    business_continuity_priority: bool = True
    
    # Status
    is_active: bool = True
    is_paused: bool = False
    pause_reason: str = ""
    
    created_at: datetime
    updated_at: datetime

class FiatTransitionManager:
    """Manages transition from CCC to fiat currency operations"""
    
    def __init__(self):
        self.transition_plans: Dict[str, TransitionPlan] = {}
        self.fiat_accounts: Dict[str, FiatAccount] = {}
        self.exchange_rules: Dict[str, CurrencyExchangeRule] = {}
        self.requirements_templates = self._load_requirements_templates()
        self.transition_requirements: Dict[str, List[TransitionRequirement]] = {}
        
    def _load_requirements_templates(self) -> Dict[str, List[Dict]]:
        """Load transition requirements templates"""
        return {
            TransitionStage.HYBRID_TESTING.value: [
                {
                    "name": "Banking Relationship Setup",
                    "description": "Establish business banking relationships",
                    "category": "financial",
                    "is_mandatory": True,
                    "completion_criteria": ["Business checking account opened", "Account verification completed"],
                    "estimated_effort_hours": 8
                },
                {
                    "name": "Accounting System Integration",
                    "description": "Integrate fiat accounting with existing CCC system",
                    "category": "technical",
                    "is_mandatory": True,
                    "completion_criteria": ["Accounting software configured", "Chart of accounts updated"],
                    "estimated_effort_hours": 16
                },
                {
                    "name": "Tax Registration",
                    "description": "Register for applicable tax obligations",
                    "category": "legal",
                    "is_mandatory": True,
                    "completion_criteria": ["Tax ID numbers obtained", "Tax reporting schedule established"],
                    "estimated_effort_hours": 12
                }
            ],
            
            TransitionStage.PARTIAL_FIAT.value: [
                {
                    "name": "Payment Processing Setup",
                    "description": "Implement fiat payment processing capabilities",
                    "category": "technical",
                    "is_mandatory": True,
                    "completion_criteria": ["Payment processor account setup", "PCI compliance achieved"],
                    "estimated_effort_hours": 24
                },
                {
                    "name": "Currency Exchange Automation",
                    "description": "Set up automated currency exchange rules",
                    "category": "operational",
                    "is_mandatory": False,
                    "completion_criteria": ["Exchange rules configured", "Risk limits established"],
                    "estimated_effort_hours": 8
                },
                {
                    "name": "Financial Controls Implementation",
                    "description": "Implement dual-currency financial controls",
                    "category": "operational",
                    "is_mandatory": True,
                    "completion_criteria": ["Approval workflows established", "Reconciliation procedures documented"],
                    "estimated_effort_hours": 20
                }
            ],
            
            TransitionStage.FULL_INTEGRATION.value: [
                {
                    "name": "Customer Communication",
                    "description": "Communicate currency options to customers",
                    "category": "operational",
                    "is_mandatory": True,
                    "completion_criteria": ["Customer notifications sent", "Support materials prepared"],
                    "estimated_effort_hours": 12
                },
                {
                    "name": "Vendor Integration",
                    "description": "Integrate fiat payments with vendor relationships",
                    "category": "operational",
                    "is_mandatory": True,
                    "completion_criteria": ["Vendor payment systems updated", "Contract amendments completed"],
                    "estimated_effort_hours": 16
                },
                {
                    "name": "Risk Management Framework",
                    "description": "Implement comprehensive currency risk management",
                    "category": "financial",
                    "is_mandatory": True,
                    "completion_criteria": ["Risk policies documented", "Monitoring systems active"],
                    "estimated_effort_hours": 32
                }
            ]
        }
    
    def create_transition_plan(self, business_id: str, current_stage: TransitionStage,
                             target_stage: TransitionStage, target_date: datetime,
                             transition_speed: str = "gradual") -> str:
        """Create transition plan for business"""
        
        plan_id = str(uuid.uuid4())
        
        # Calculate requirements
        all_requirements = []
        stage_order = [
            TransitionStage.CCC_ONLY,
            TransitionStage.HYBRID_TESTING,
            TransitionStage.PARTIAL_FIAT,
            TransitionStage.FULL_INTEGRATION,
            TransitionStage.FIAT_PRIMARY
        ]
        
        current_index = stage_order.index(current_stage)
        target_index = stage_order.index(target_stage)
        
        # Generate requirements for each stage in the transition path
        for i in range(current_index + 1, target_index + 1):
            stage = stage_order[i]
            stage_requirements = self.requirements_templates.get(stage.value, [])
            
            for req_template in stage_requirements:
                req_id = str(uuid.uuid4())
                requirement = TransitionRequirement(
                    id=req_id,
                    **req_template
                )
                all_requirements.append(requirement)
        
        plan = TransitionPlan(
            id=plan_id,
            business_id=business_id,
            current_stage=current_stage,
            target_stage=target_stage,
            start_date=datetime.now(),
            target_completion_date=target_date,
            transition_speed=transition_speed,
            requirements_total=len(all_requirements),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.transition_plans[plan_id] = plan
        self.transition_requirements[plan_id] = all_requirements
        
        return plan_id
    
    def get_transition_status(self, plan_id: str) -> Dict[str, Any]:
        """Get current transition status"""
        
        plan = self.transition_plans.get(plan_id)
        if not plan:
            raise ValueError("Transition plan not found")
        
        requirements = self.transition_requirements.get(plan_id, [])
        
        # Calculate progress
        completed_requirements = [r for r in requirements if r.is_completed]
        plan.completion_percentage = (len(completed_requirements) / len(requirements) * 100) if requirements else 100
        plan.requirements_completed = len(completed_requirements)
        
        # Categorize requirements
        requirements_by_category = {}
        for req in requirements:
            if req.category not in requirements_by_category:
                requirements_by_category[req.category] = {"total": 0, "completed": 0}
            
            requirements_by_category[req.category]["total"] += 1
            if req.is_completed:
                requirements_by_category[req.category]["completed"] += 1
        
        # Calculate timeline metrics
        days_since_start = (datetime.now() - plan.start_date).days
        days_until_target = (plan.target_completion_date - datetime.now()).days
        
        return {
            "plan_id": plan_id,
            "current_stage": plan.current_stage.value,
            "target_stage": plan.target_stage.value,
            "completion_percentage": plan.completion_percentage,
            "requirements_completed": plan.requirements_completed,
            "requirements_total": plan.requirements_total,
            "requirements_by_category": requirements_by_category,
            "timeline": {
                "start_date": plan.start_date.isoformat(),
                "target_completion_date": plan.target_completion_date.isoformat(),
                "days_since_start": days_since_start,
                "days_until_target": days_until_target,
                "is_on_track": self._is_on_track(plan)
            },
            "next_requirements": self._get_next_requirements(plan_id),
            "blockers": self._get_blockers(plan_id),
            "recommendations": self._get_recommendations(plan_id)
        }
    
    def _is_on_track(self, plan: TransitionPlan) -> bool:
        """Check if transition is on track"""
        
        total_days = (plan.target_completion_date - plan.start_date).days
        days_elapsed = (datetime.now() - plan.start_date).days
        
        expected_progress = (days_elapsed / total_days * 100) if total_days > 0 else 0
        
        # Allow 10% buffer
        return plan.completion_percentage >= (expected_progress - 10)
    
    def _get_next_requirements(self, plan_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get next requirements to work on"""
        
        requirements = self.transition_requirements.get(plan_id, [])
        
        # Find incomplete requirements with no incomplete dependencies
        next_requirements = []
        
        for req in requirements:
            if req.is_completed:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_name in req.dependencies:
                dep_req = next((r for r in requirements if r.name == dep_name), None)
                if dep_req and not dep_req.is_completed:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                next_requirements.append({
                    "id": req.id,
                    "name": req.name,
                    "description": req.description,
                    "category": req.category,
                    "estimated_effort_hours": req.estimated_effort_hours,
                    "completion_criteria": req.completion_criteria,
                    "is_mandatory": req.is_mandatory
                })
        
        return next_requirements[:limit]
    
    def _get_blockers(self, plan_id: str) -> List[str]:
        """Get current blockers"""
        
        plan = self.transition_plans.get(plan_id)
        requirements = self.transition_requirements.get(plan_id, [])
        
        blockers = []
        
        if plan.is_paused:
            blockers.append(f"Plan is paused: {plan.pause_reason}")
        
        # Check for overdue requirements
        if not self._is_on_track(plan):
            blockers.append("Transition is behind schedule")
        
        # Check for high-priority incomplete requirements
        critical_incomplete = [
            r for r in requirements
            if not r.is_completed and r.is_mandatory and r.category == "legal"
        ]
        
        if critical_incomplete:
            blockers.append(f"{len(critical_incomplete)} critical legal requirements pending")
        
        return blockers
    
    def _get_recommendations(self, plan_id: str) -> List[str]:
        """Get recommendations for transition"""
        
        plan = self.transition_plans.get(plan_id)
        requirements = self.transition_requirements.get(plan_id, [])
        
        recommendations = []
        
        # Progress-based recommendations
        if plan.completion_percentage < 25:
            recommendations.append("Focus on foundational requirements first (banking, legal)")
        elif plan.completion_percentage < 50:
            recommendations.append("Begin technical integration and system setup")
        elif plan.completion_percentage < 75:
            recommendations.append("Test dual-currency operations with small transactions")
        else:
            recommendations.append("Prepare for full transition and customer communication")
        
        # Speed-based recommendations
        if not self._is_on_track(plan):
            if plan.transition_speed == "gradual":
                recommendations.append("Consider accelerating transition speed")
            recommendations.append("Identify and address bottlenecks in critical path")
        
        # Category-based recommendations
        technical_reqs = [r for r in requirements if r.category == "technical" and not r.is_completed]
        if len(technical_reqs) > 3:
            recommendations.append("Consider hiring technical consultant for faster implementation")
        
        return recommendations
    
    def complete_requirement(self, plan_id: str, requirement_id: str, 
                           completion_notes: str = "") -> bool:
        """Mark requirement as completed"""
        
        requirements = self.transition_requirements.get(plan_id, [])
        requirement = next((r for r in requirements if r.id == requirement_id), None)
        
        if not requirement:
            raise ValueError("Requirement not found")
        
        requirement.is_completed = True
        requirement.completed_at = datetime.now()
        requirement.completion_notes = completion_notes
        
        # Update plan
        plan = self.transition_plans.get(plan_id)
        if plan:
            plan.updated_at = datetime.now()
            
            # Check if plan is complete
            completed_requirements = [r for r in requirements if r.is_completed]
            if len(completed_requirements) == len(requirements):
                plan.actual_completion_date = datetime.now()
                plan.completion_percentage = 100.0
        
        return True
    
    def create_fiat_account(self, business_id: str, account_type: str, bank_name: str,
                          account_number: str, routing_number: str, currency: str) -> str:
        """Create fiat currency account"""
        
        account_id = str(uuid.uuid4())
        
        account = FiatAccount(
            id=account_id,
            business_id=business_id,
            account_type=account_type,
            bank_name=bank_name,
            account_number=account_number,  # Should be encrypted in production
            routing_number=routing_number,
            currency=currency,
            created_at=datetime.now()
        )
        
        self.fiat_accounts[account_id] = account
        return account_id
    
    def create_exchange_rule(self, business_id: str, name: str, from_currency: str,
                           to_currency: str, trigger_condition: str,
                           trigger_value: Optional[float] = None) -> str:
        """Create automated currency exchange rule"""
        
        rule_id = str(uuid.uuid4())
        
        rule = CurrencyExchangeRule(
            id=rule_id,
            business_id=business_id,
            name=name,
            description=f"Auto-exchange {from_currency} to {to_currency}",
            from_currency=from_currency,
            to_currency=to_currency,
            trigger_condition=trigger_condition,
            trigger_value=trigger_value,
            created_at=datetime.now()
        )
        
        self.exchange_rules[rule_id] = rule
        return rule_id
    
    def simulate_currency_mix(self, business_id: str, ccc_percentage: float,
                            fiat_percentage: float, scenario_days: int = 30) -> Dict[str, Any]:
        """Simulate business operations with different currency mix"""
        
        # Mock historical transaction data for simulation
        daily_revenue = 1000.0  # Base daily revenue
        daily_expenses = 600.0  # Base daily expenses
        
        simulation_results = {
            "scenario_days": scenario_days,
            "currency_mix": {
                "ccc_percentage": ccc_percentage,
                "fiat_percentage": fiat_percentage
            },
            "projected_metrics": {},
            "risk_analysis": {},
            "recommendations": []
        }
        
        # Calculate projected metrics
        total_revenue = daily_revenue * scenario_days
        total_expenses = daily_expenses * scenario_days
        
        ccc_revenue = total_revenue * (ccc_percentage / 100)
        fiat_revenue = total_revenue * (fiat_percentage / 100)
        
        ccc_expenses = total_expenses * (ccc_percentage / 100)
        fiat_expenses = total_expenses * (fiat_percentage / 100)
        
        simulation_results["projected_metrics"] = {
            "total_revenue": total_revenue,
            "ccc_revenue": ccc_revenue,
            "fiat_revenue": fiat_revenue,
            "total_expenses": total_expenses,
            "ccc_expenses": ccc_expenses,
            "fiat_expenses": fiat_expenses,
            "net_profit": total_revenue - total_expenses
        }
        
        # Risk analysis
        exchange_risk = abs(50 - fiat_percentage) / 50 * 0.3  # Higher risk as we move away from 50/50
        operational_complexity = (ccc_percentage > 0 and fiat_percentage > 0) * 0.2  # Mixed operations
        regulatory_risk = fiat_percentage / 100 * 0.1  # Higher fiat = more regulation
        
        total_risk_score = exchange_risk + operational_complexity + regulatory_risk
        
        simulation_results["risk_analysis"] = {
            "exchange_risk": exchange_risk,
            "operational_complexity": operational_complexity,
            "regulatory_risk": regulatory_risk,
            "total_risk_score": total_risk_score,
            "risk_level": "low" if total_risk_score < 0.3 else "medium" if total_risk_score < 0.6 else "high"
        }
        
        # Recommendations
        recommendations = []
        
        if fiat_percentage < 25:
            recommendations.append("Consider gradual fiat adoption for market expansion")
        elif fiat_percentage > 75:
            recommendations.append("Maintain some CCC operations for community benefits")
        
        if total_risk_score > 0.5:
            recommendations.append("Implement additional risk management controls")
        
        if ccc_percentage > 0 and fiat_percentage > 0:
            recommendations.append("Set up automated currency exchange rules")
        
        simulation_results["recommendations"] = recommendations
        
        return simulation_results
    
    def get_transition_roadmap(self, business_id: str, target_stage: TransitionStage) -> Dict[str, Any]:
        """Get comprehensive transition roadmap"""
        
        # Find existing plan or create template
        existing_plan = next(
            (plan for plan in self.transition_plans.values() if plan.business_id == business_id),
            None
        )
        
        current_stage = existing_plan.current_stage if existing_plan else TransitionStage.CCC_ONLY
        
        stage_order = [
            TransitionStage.CCC_ONLY,
            TransitionStage.HYBRID_TESTING,
            TransitionStage.PARTIAL_FIAT,
            TransitionStage.FULL_INTEGRATION,
            TransitionStage.FIAT_PRIMARY
        ]
        
        current_index = stage_order.index(current_stage)
        target_index = stage_order.index(target_stage)
        
        roadmap_stages = []
        
        for i in range(current_index, target_index + 1):
            stage = stage_order[i]
            stage_requirements = self.requirements_templates.get(stage.value, [])
            
            estimated_duration = sum(req.get("estimated_effort_hours", 0) for req in stage_requirements) // 8
            
            stage_info = {
                "stage": stage.value,
                "name": stage.value.replace("_", " ").title(),
                "is_current": stage == current_stage,
                "requirements_count": len(stage_requirements),
                "estimated_duration_days": max(estimated_duration, 7),
                "key_milestones": self._get_stage_milestones(stage),
                "success_criteria": self._get_stage_success_criteria(stage)
            }
            
            roadmap_stages.append(stage_info)
        
        total_duration = sum(stage["estimated_duration_days"] for stage in roadmap_stages)
        
        return {
            "business_id": business_id,
            "current_stage": current_stage.value,
            "target_stage": target_stage.value,
            "total_estimated_duration_days": total_duration,
            "stages": roadmap_stages,
            "critical_success_factors": [
                "Maintain business continuity during transition",
                "Ensure regulatory compliance at each stage",
                "Test thoroughly before full implementation",
                "Communicate clearly with all stakeholders"
            ],
            "potential_risks": [
                "Cash flow disruption during transition",
                "Regulatory compliance gaps",
                "Technical integration challenges",
                "Customer confusion or resistance"
            ]
        }
    
    def _get_stage_milestones(self, stage: TransitionStage) -> List[str]:
        """Get key milestones for transition stage"""
        
        milestones = {
            TransitionStage.HYBRID_TESTING: [
                "First fiat account opened",
                "Dual-currency accounting system operational",
                "Tax registrations completed"
            ],
            TransitionStage.PARTIAL_FIAT: [
                "Payment processing system live",
                "First fiat customer transaction",
                "Currency exchange rules active"
            ],
            TransitionStage.FULL_INTEGRATION: [
                "All customers notified of currency options",
                "Vendor payments integrated",
                "Risk management framework implemented"
            ],
            TransitionStage.FIAT_PRIMARY: [
                "Majority of transactions in fiat",
                "CCC operations maintained for strategic purposes",
                "Full regulatory compliance achieved"
            ]
        }
        
        return milestones.get(stage, [])
    
    def _get_stage_success_criteria(self, stage: TransitionStage) -> List[str]:
        """Get success criteria for transition stage"""
        
        criteria = {
            TransitionStage.HYBRID_TESTING: [
                "Can process both CCC and fiat transactions",
                "Accounting reconciliation working correctly",
                "No compliance issues identified"
            ],
            TransitionStage.PARTIAL_FIAT: [
                "50% of new transactions in fiat",
                "Payment processing success rate > 99%",
                "Currency exchange slippage < 1%"
            ],
            TransitionStage.FULL_INTEGRATION: [
                "All major business processes support both currencies",
                "Customer satisfaction maintained",
                "Operational efficiency not degraded"
            ],
            TransitionStage.FIAT_PRIMARY: [
                "Business can operate independently of CCC",
                "Regulatory audit passed",
                "Profitability maintained or improved"
            ]
        }
        
        return criteria.get(stage, [])