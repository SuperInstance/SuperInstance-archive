from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import uuid
from pydantic import BaseModel

from .models import MarketSymbol

class TransitionPhase(str, Enum):
    PLANNING = "planning"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    COMPLETION = "completion"

class VestingScheduleType(str, Enum):
    LINEAR = "linear"
    CLIFF = "cliff"
    ACCELERATED = "accelerated"
    PERFORMANCE_BASED = "performance_based"

class GovernanceModel(str, Enum):
    FOUNDER_CONTROLLED = "founder_controlled"
    BOARD_GOVERNED = "board_governed"
    COMMUNITY_GOVERNED = "community_governed"
    DAO_GOVERNED = "dao_governed"
    HYBRID = "hybrid"

class DecentralizationLevel(str, Enum):
    CENTRALIZED = "centralized"
    SEMI_DECENTRALIZED = "semi_decentralized"
    DECENTRALIZED = "decentralized"
    FULLY_AUTONOMOUS = "fully_autonomous"

class ExitPlan(BaseModel):
    plan_id: str = None
    name: str
    description: str
    target_completion_date: date
    current_phase: TransitionPhase = TransitionPhase.PLANNING
    phases_completed: List[str] = []
    total_founder_shares: Decimal
    total_employee_shares: Decimal = Decimal('0')
    total_community_shares: Decimal = Decimal('0')
    governance_transition_timeline: Dict[str, date]
    decentralization_milestones: List[Dict[str, Any]] = []
    legal_structure_changes: List[Dict[str, Any]] = []
    token_migration_plan: Optional[Dict[str, Any]] = None
    legacy_preservation_plan: Dict[str, Any] = {}
    created_at: datetime = None
    updated_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.plan_id:
            self.plan_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
        self.updated_at = datetime.now()

class VestingSchedule(BaseModel):
    schedule_id: str = None
    beneficiary_id: str
    beneficiary_type: str  # founder, employee, advisor, community
    total_shares: Decimal
    vested_shares: Decimal = Decimal('0')
    schedule_type: VestingScheduleType
    start_date: date
    cliff_duration_months: int = 12  # 1 year cliff by default
    vesting_duration_months: int = 48  # 4 year vesting by default
    vesting_frequency: str = "monthly"  # monthly, quarterly, yearly
    performance_metrics: Optional[Dict[str, Any]] = None
    acceleration_triggers: List[str] = []
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.schedule_id:
            self.schedule_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class EmployeeStockOption(BaseModel):
    option_id: str = None
    employee_id: str
    grant_date: date
    exercise_price: Decimal
    total_options: Decimal
    vested_options: Decimal = Decimal('0')
    exercised_options: Decimal = Decimal('0')
    vesting_schedule_id: str
    expiration_date: date
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.option_id:
            self.option_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class GovernanceTransition(BaseModel):
    transition_id: str = None
    plan_id: str
    from_model: GovernanceModel
    to_model: GovernanceModel
    transition_date: date
    voting_power_distribution: Dict[str, Decimal]  # stakeholder -> percentage
    decision_making_process: Dict[str, Any]
    community_participation_requirements: Dict[str, Any] = {}
    is_completed: bool = False
    completion_metrics: Dict[str, Any] = {}
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.transition_id:
            self.transition_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class DAOStructure(BaseModel):
    dao_id: str = None
    name: str
    description: str
    governance_token_symbol: MarketSymbol
    total_supply: Decimal
    voting_mechanism: str = "token_weighted"  # token_weighted, quadratic, one_person_one_vote
    proposal_threshold: Decimal = Decimal('1000')  # Tokens needed to create proposal
    quorum_requirement: Decimal = Decimal('0.04')  # 4% participation required
    voting_period_days: int = 7
    timelock_delay_hours: int = 48
    treasury_management: Dict[str, Any] = {}
    smart_contract_addresses: Dict[str, str] = {}
    multisig_signers: List[str] = []
    is_active: bool = False
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.dao_id:
            self.dao_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class TokenMigrationPlan(BaseModel):
    migration_id: str = None
    plan_id: str
    from_symbol: MarketSymbol
    to_symbol: Optional[str] = None  # New token symbol if different
    migration_ratio: Decimal = Decimal('1')  # 1:1 by default
    migration_start_date: date
    migration_end_date: date
    snapshot_dates: List[date] = []
    eligibility_criteria: Dict[str, Any] = {}
    migration_process: List[Dict[str, str]] = []
    backward_compatibility_period: int = 365  # Days to maintain old system
    user_migration_incentives: List[Dict[str, Any]] = []
    technical_specifications: Dict[str, Any] = {}
    is_active: bool = False
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.migration_id:
            self.migration_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class LegacyPreservationPlan(BaseModel):
    preservation_id: str = None
    plan_id: str
    data_archival_strategy: Dict[str, Any]
    code_repository_preservation: Dict[str, str]  # repo -> archive location
    documentation_preservation: List[Dict[str, str]]
    community_history_preservation: Dict[str, Any]
    brand_and_trademark_handling: Dict[str, str]
    user_data_migration_plan: Dict[str, Any]
    service_continuity_guarantees: List[str]
    historical_milestone_documentation: List[Dict[str, Any]]
    founder_story_preservation: Dict[str, Any] = {}
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.preservation_id:
            self.preservation_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class ExitStrategySystem:
    def __init__(self):
        self.exit_plans: Dict[str, ExitPlan] = {}
        self.vesting_schedules: Dict[str, VestingSchedule] = {}
        self.employee_stock_options: Dict[str, EmployeeStockOption] = {}
        self.governance_transitions: Dict[str, List[GovernanceTransition]] = {}  # plan_id -> transitions
        self.dao_structures: Dict[str, DAOStructure] = {}
        self.token_migration_plans: Dict[str, TokenMigrationPlan] = {}
        self.legacy_preservation_plans: Dict[str, LegacyPreservationPlan] = {}
        
        # Initialize default 5-year transition plan
        self._initialize_default_exit_plan()
    
    def _initialize_default_exit_plan(self):
        """Initialize the default 5-year ownership transition plan"""
        plan = ExitPlan(
            name="ActiveLog 5-Year Transition to Community Ownership",
            description="Comprehensive plan to transition ActiveLog from founder control to community governance over 5 years",
            target_completion_date=date.today() + timedelta(days=5*365),  # 5 years from now
            total_founder_shares=Decimal('1000000'),  # 1M founder shares
            governance_transition_timeline={
                "year_1": date.today() + timedelta(days=365),
                "year_2": date.today() + timedelta(days=2*365),
                "year_3": date.today() + timedelta(days=3*365),
                "year_4": date.today() + timedelta(days=4*365),
                "year_5": date.today() + timedelta(days=5*365)
            },
            decentralization_milestones=[
                {
                    "phase": "Year 1 - Foundation Building",
                    "target_date": date.today() + timedelta(days=365),
                    "goals": [
                        "Establish community advisory board",
                        "Begin employee equity program",
                        "Create governance framework documentation",
                        "Launch community proposal system"
                    ],
                    "decentralization_level": DecentralizationLevel.CENTRALIZED.value
                },
                {
                    "phase": "Year 2 - Community Engagement",
                    "target_date": date.today() + timedelta(days=2*365),
                    "goals": [
                        "Transfer 20% voting power to community",
                        "Establish community treasury",
                        "Launch contributor recognition program",
                        "Begin open-source governance tools"
                    ],
                    "decentralization_level": DecentralizationLevel.SEMI_DECENTRALIZED.value
                },
                {
                    "phase": "Year 3 - Operational Transition",
                    "target_date": date.today() + timedelta(days=3*365),
                    "goals": [
                        "Community controls 40% of decisions",
                        "Employee ownership reaches 25%",
                        "Implement DAO governance structure",
                        "Launch token-based voting system"
                    ],
                    "decentralization_level": DecentralizationLevel.SEMI_DECENTRALIZED.value
                },
                {
                    "phase": "Year 4 - Governance Handover",
                    "target_date": date.today() + timedelta(days=4*365),
                    "goals": [
                        "Community majority control (51%+)",
                        "Fully operational DAO",
                        "Automated governance processes",
                        "Multi-stakeholder decision making"
                    ],
                    "decentralization_level": DecentralizationLevel.DECENTRALIZED.value
                },
                {
                    "phase": "Year 5 - Full Autonomy",
                    "target_date": date.today() + timedelta(days=5*365),
                    "goals": [
                        "Community owns 70%+ of governance",
                        "Fully autonomous operations",
                        "Self-sustaining ecosystem",
                        "Founder advisory role only"
                    ],
                    "decentralization_level": DecentralizationLevel.FULLY_AUTONOMOUS.value
                }
            ],
            legacy_preservation_plan={
                "mission_continuity": "Ensure ActiveLog's mission of empowering users persists",
                "founder_recognition": "Maintain historical acknowledgment of founder contributions",
                "community_values": "Preserve core values of innovation, accessibility, and user empowerment",
                "brand_integrity": "Protect brand and ensure consistent quality standards"
            }
        )
        
        self.exit_plans[plan.plan_id] = plan
    
    def create_founder_vesting_schedule(self, plan_id: str, founder_id: str, 
                                      total_shares: Decimal) -> VestingSchedule:
        """Create vesting schedule for founder shares"""
        plan = self.exit_plans.get(plan_id)
        if not plan:
            raise ValueError("Exit plan not found")
        
        # 4-year vesting with 1-year cliff and acceleration triggers
        schedule = VestingSchedule(
            beneficiary_id=founder_id,
            beneficiary_type="founder",
            total_shares=total_shares,
            schedule_type=VestingScheduleType.LINEAR,
            start_date=date.today(),
            cliff_duration_months=12,
            vesting_duration_months=48,
            vesting_frequency="quarterly",
            acceleration_triggers=[
                "community_governance_milestone",
                "successful_dao_launch",
                "founder_departure_from_active_role"
            ]
        )
        
        self.vesting_schedules[schedule.schedule_id] = schedule
        return schedule
    
    def create_employee_stock_options(self, plan_id: str, employee_id: str, 
                                    option_data: Dict) -> EmployeeStockOption:
        """Create employee stock option grant"""
        plan = self.exit_plans.get(plan_id)
        if not plan:
            raise ValueError("Exit plan not found")
        
        # Create vesting schedule for employee
        vesting_schedule = VestingSchedule(
            beneficiary_id=employee_id,
            beneficiary_type="employee",
            total_shares=option_data['total_options'],
            schedule_type=VestingScheduleType.LINEAR,
            start_date=date.today(),
            cliff_duration_months=12,
            vesting_duration_months=36,  # 3 years for employees
            vesting_frequency="monthly"
        )
        
        self.vesting_schedules[vesting_schedule.schedule_id] = vesting_schedule
        
        # Create stock options
        options = EmployeeStockOption(
            employee_id=employee_id,
            grant_date=date.today(),
            exercise_price=option_data.get('exercise_price', Decimal('1.00')),
            total_options=option_data['total_options'],
            vesting_schedule_id=vesting_schedule.schedule_id,
            expiration_date=date.today() + timedelta(days=10*365)  # 10 years to exercise
        )
        
        self.employee_stock_options[options.option_id] = options
        return options
    
    def calculate_vested_shares(self, schedule_id: str, as_of_date: Optional[date] = None) -> Dict:
        """Calculate vested shares as of a specific date"""
        schedule = self.vesting_schedules.get(schedule_id)
        if not schedule:
            return {'error': 'Vesting schedule not found'}
        
        if not as_of_date:
            as_of_date = date.today()
        
        # Check if cliff period has been met
        cliff_date = schedule.start_date + timedelta(days=schedule.cliff_duration_months * 30)
        
        if as_of_date < cliff_date:
            return {
                'schedule_id': schedule_id,
                'vested_shares': 0,
                'vesting_percentage': 0,
                'cliff_date': cliff_date.isoformat(),
                'cliff_met': False
            }
        
        # Calculate vesting based on schedule type
        if schedule.schedule_type == VestingScheduleType.LINEAR:
            total_vesting_days = schedule.vesting_duration_months * 30
            days_vested = (as_of_date - schedule.start_date).days
            
            # Don't exceed total vesting period
            days_vested = min(days_vested, total_vesting_days)
            
            vesting_percentage = days_vested / total_vesting_days
            vested_shares = schedule.total_shares * Decimal(str(vesting_percentage))
        
        elif schedule.schedule_type == VestingScheduleType.CLIFF:
            # All or nothing at cliff date
            vesting_end_date = schedule.start_date + timedelta(days=schedule.vesting_duration_months * 30)
            if as_of_date >= vesting_end_date:
                vested_shares = schedule.total_shares
                vesting_percentage = 1.0
            else:
                vested_shares = Decimal('0')
                vesting_percentage = 0.0
        
        else:  # Other schedule types would be implemented here
            vested_shares = Decimal('0')
            vesting_percentage = 0.0
        
        return {
            'schedule_id': schedule_id,
            'vested_shares': float(vested_shares),
            'vesting_percentage': vesting_percentage,
            'total_shares': float(schedule.total_shares),
            'cliff_date': cliff_date.isoformat(),
            'cliff_met': True,
            'fully_vested_date': (schedule.start_date + timedelta(days=schedule.vesting_duration_months * 30)).isoformat()
        }
    
    def create_governance_transition(self, plan_id: str, transition_data: Dict) -> GovernanceTransition:
        """Create a governance transition milestone"""
        transition = GovernanceTransition(
            plan_id=plan_id,
            **transition_data
        )
        
        if plan_id not in self.governance_transitions:
            self.governance_transitions[plan_id] = []
        
        self.governance_transitions[plan_id].append(transition)
        return transition
    
    def design_dao_structure(self, plan_id: str, dao_data: Dict) -> DAOStructure:
        """Design DAO structure for community governance"""
        dao = DAOStructure(**dao_data)
        
        # Set up default treasury management
        dao.treasury_management = {
            "multi_sig_threshold": "3_of_5",
            "spending_limits": {
                "operational": float(Decimal('10000')),  # $10K for operations
                "development": float(Decimal('50000')),  # $50K for development
                "community": float(Decimal('25000'))     # $25K for community programs
            },
            "budget_approval_process": [
                "Community proposal",
                "Technical review",
                "Economic impact assessment",
                "Community vote",
                "Multi-sig execution"
            ]
        }
        
        # Smart contract framework
        dao.smart_contract_addresses = {
            "governance_token": "0x0000000000000000000000000000000000000000",  # Placeholder
            "voting_contract": "0x0000000000000000000000000000000000000000",
            "treasury_contract": "0x0000000000000000000000000000000000000000",
            "timelock_contract": "0x0000000000000000000000000000000000000000"
        }
        
        self.dao_structures[dao.dao_id] = dao
        return dao
    
    def create_token_migration_plan(self, plan_id: str, migration_data: Dict) -> TokenMigrationPlan:
        """Create token migration plan for decentralization"""
        migration = TokenMigrationPlan(
            plan_id=plan_id,
            **migration_data
        )
        
        # Set up default migration process
        migration.migration_process = [
            {
                "step": "1",
                "description": "Announce migration 90 days in advance",
                "duration": "90 days"
            },
            {
                "step": "2", 
                "description": "Deploy new token contracts and verify",
                "duration": "30 days"
            },
            {
                "step": "3",
                "description": "Open migration portal for users",
                "duration": "180 days"
            },
            {
                "step": "4",
                "description": "Automated migration for unclaimed tokens",
                "duration": "30 days"
            },
            {
                "step": "5",
                "description": "Legacy system maintenance period",
                "duration": "365 days"
            }
        ]
        
        # User incentives for early migration
        migration.user_migration_incentives = [
            {
                "type": "early_bird_bonus",
                "description": "5% bonus tokens for migrating in first 30 days",
                "bonus_percentage": 5
            },
            {
                "type": "gas_fee_reimbursement",
                "description": "Reimburse migration transaction fees",
                "max_reimbursement": 50
            },
            {
                "type": "governance_power",
                "description": "Enhanced voting power for early adopters",
                "multiplier": 1.2
            }
        ]
        
        self.token_migration_plans[migration.migration_id] = migration
        return migration
    
    def create_legacy_preservation_plan(self, plan_id: str, preservation_data: Dict) -> LegacyPreservationPlan:
        """Create comprehensive legacy preservation plan"""
        preservation = LegacyPreservationPlan(
            plan_id=plan_id,
            **preservation_data
        )
        
        # Default data archival strategy
        preservation.data_archival_strategy = {
            "user_data": {
                "retention_period": "indefinite",
                "backup_frequency": "daily",
                "archive_format": "encrypted_json",
                "access_controls": "user_controlled"
            },
            "transaction_history": {
                "retention_period": "indefinite",
                "blockchain_backup": True,
                "immutable_record": True
            },
            "system_logs": {
                "retention_period": "7_years",
                "compliance_requirements": ["financial_auditing", "regulatory_reporting"]
            }
        }
        
        # Code repository preservation
        preservation.code_repository_preservation = {
            "github_main": "https://github.com/activelog/main-archive",
            "ipfs_backup": "ipfs://QmActiveLogCodeArchive",
            "institutional_backup": "software_heritage_foundation",
            "license": "mit_open_source"
        }
        
        # Documentation preservation
        preservation.documentation_preservation = [
            {
                "type": "technical_documentation",
                "location": "docs.activelog.ai/archive",
                "format": "markdown_html"
            },
            {
                "type": "user_guides",
                "location": "help.activelog.ai/archive",
                "format": "interactive_tutorials"
            },
            {
                "type": "api_documentation",
                "location": "api.activelog.ai/archive",
                "format": "openapi_spec"
            }
        ]
        
        # Historical milestones
        preservation.historical_milestone_documentation = [
            {
                "milestone": "Platform Launch",
                "date": "2024-01-01",
                "description": "Initial release of ActiveLog platform",
                "significance": "Foundation of the ecosystem"
            },
            {
                "milestone": "Community Milestone",
                "date": "2024-06-01",
                "description": "Reached 10,000 active users",
                "significance": "Proof of product-market fit"
            },
            {
                "milestone": "Governance Transition Start",
                "date": date.today().isoformat(),
                "description": "Beginning of 5-year transition to community ownership",
                "significance": "Start of decentralization journey"
            }
        ]
        
        self.legacy_preservation_plans[preservation.preservation_id] = preservation
        return preservation
    
    def get_transition_roadmap(self, plan_id: str) -> Dict:
        """Get detailed transition roadmap with timeline and milestones"""
        plan = self.exit_plans.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        
        # Calculate progress
        total_phases = len(plan.decentralization_milestones)
        completed_phases = len(plan.phases_completed)
        progress_percentage = (completed_phases / total_phases * 100) if total_phases > 0 else 0
        
        # Get governance transitions
        transitions = self.governance_transitions.get(plan_id, [])
        
        # Get next milestone
        next_milestone = None
        for milestone in plan.decentralization_milestones:
            milestone_date = datetime.strptime(milestone['target_date'], '%Y-%m-%d').date() if isinstance(milestone['target_date'], str) else milestone['target_date']
            if milestone_date > date.today():
                next_milestone = milestone
                break
        
        return {
            'plan_info': {
                'plan_id': plan_id,
                'name': plan.name,
                'description': plan.description,
                'target_completion': plan.target_completion_date.isoformat(),
                'current_phase': plan.current_phase.value,
                'progress_percentage': progress_percentage
            },
            'milestones': [
                {
                    'phase': m['phase'],
                    'target_date': m['target_date'].isoformat() if isinstance(m['target_date'], date) else m['target_date'],
                    'goals': m['goals'],
                    'decentralization_level': m['decentralization_level'],
                    'is_completed': m['phase'] in plan.phases_completed,
                    'is_current': m == next_milestone
                } for m in plan.decentralization_milestones
            ],
            'governance_transitions': [
                {
                    'from_model': t.from_model.value,
                    'to_model': t.to_model.value,
                    'transition_date': t.transition_date.isoformat(),
                    'voting_power_distribution': {k: float(v) for k, v in t.voting_power_distribution.items()},
                    'is_completed': t.is_completed
                } for t in transitions
            ],
            'next_milestone': {
                'phase': next_milestone['phase'],
                'target_date': next_milestone['target_date'].isoformat() if isinstance(next_milestone['target_date'], date) else next_milestone['target_date'],
                'days_remaining': (datetime.strptime(next_milestone['target_date'], '%Y-%m-%d').date() - date.today()).days if isinstance(next_milestone['target_date'], str) else (next_milestone['target_date'] - date.today()).days,
                'goals': next_milestone['goals']
            } if next_milestone else None
        }
    
    def get_ownership_distribution_projection(self, plan_id: str, target_date: date) -> Dict:
        """Project ownership distribution at a future date"""
        plan = self.exit_plans.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        
        # Get all vesting schedules related to this plan
        plan_schedules = [s for s in self.vesting_schedules.values()]
        
        projected_distribution = {
            'founders': Decimal('0'),
            'employees': Decimal('0'),
            'community': Decimal('0'),
            'treasury': Decimal('0')
        }
        
        total_shares = plan.total_founder_shares + plan.total_employee_shares + plan.total_community_shares
        
        # Calculate vested shares for each category
        for schedule in plan_schedules:
            vesting_info = self.calculate_vested_shares(schedule.schedule_id, target_date)
            vested_amount = Decimal(str(vesting_info.get('vested_shares', 0)))
            
            if schedule.beneficiary_type == 'founder':
                projected_distribution['founders'] += vested_amount
            elif schedule.beneficiary_type == 'employee':
                projected_distribution['employees'] += vested_amount
            elif schedule.beneficiary_type == 'community':
                projected_distribution['community'] += vested_amount
        
        # Add community shares that will be distributed by target date
        years_elapsed = (target_date - date.today()).days / 365
        community_distribution_rate = 0.2  # 20% per year
        additional_community_shares = min(
            plan.total_founder_shares * Decimal(str(years_elapsed * community_distribution_rate)),
            plan.total_founder_shares
        )
        projected_distribution['community'] += additional_community_shares
        projected_distribution['founders'] -= additional_community_shares
        
        # Treasury reserve
        projected_distribution['treasury'] = total_shares * Decimal('0.1')  # 10% treasury reserve
        
        # Calculate percentages
        total_distributed = sum(projected_distribution.values())
        distribution_percentages = {
            k: float(v / total_distributed * 100) if total_distributed > 0 else 0
            for k, v in projected_distribution.items()
        }
        
        return {
            'target_date': target_date.isoformat(),
            'ownership_distribution': {
                'founders': {
                    'shares': float(projected_distribution['founders']),
                    'percentage': distribution_percentages['founders']
                },
                'employees': {
                    'shares': float(projected_distribution['employees']),
                    'percentage': distribution_percentages['employees']
                },
                'community': {
                    'shares': float(projected_distribution['community']),
                    'percentage': distribution_percentages['community']
                },
                'treasury': {
                    'shares': float(projected_distribution['treasury']),
                    'percentage': distribution_percentages['treasury']
                }
            },
            'governance_implications': {
                'community_controlled': distribution_percentages['community'] > 50,
                'founder_influence': distribution_percentages['founders'],
                'decision_making_model': 'community_majority' if distribution_percentages['community'] > 50 else 'hybrid'
            }
        }
    
    def get_exit_strategy_dashboard(self, plan_id: str) -> Dict:
        """Get comprehensive exit strategy dashboard"""
        plan = self.exit_plans.get(plan_id)
        if not plan:
            return {'error': 'Plan not found'}
        
        # Get current ownership distribution
        current_distribution = self.get_ownership_distribution_projection(plan_id, date.today())
        
        # Get 5-year projection
        future_distribution = self.get_ownership_distribution_projection(
            plan_id, 
            date.today() + timedelta(days=5*365)
        )
        
        # Get DAO info
        dao_structures = list(self.dao_structures.values())
        
        # Get migration plans
        migration_plans = [m for m in self.token_migration_plans.values() if m.plan_id == plan_id]
        
        # Get preservation plans
        preservation_plans = [p for p in self.legacy_preservation_plans.values() if p.plan_id == plan_id]
        
        return {
            'plan_overview': {
                'name': plan.name,
                'current_phase': plan.current_phase.value,
                'target_completion': plan.target_completion_date.isoformat(),
                'days_remaining': (plan.target_completion_date - date.today()).days
            },
            'current_ownership': current_distribution.get('ownership_distribution', {}),
            'projected_ownership': future_distribution.get('ownership_distribution', {}),
            'decentralization_progress': {
                'milestones_completed': len(plan.phases_completed),
                'total_milestones': len(plan.decentralization_milestones),
                'current_level': self._get_current_decentralization_level(plan)
            },
            'dao_readiness': {
                'structure_designed': len(dao_structures) > 0,
                'governance_token_ready': any(dao.governance_token_symbol for dao in dao_structures),
                'community_engagement': self._assess_community_readiness()
            },
            'migration_status': {
                'plans_created': len(migration_plans),
                'active_migrations': len([m for m in migration_plans if m.is_active])
            },
            'legacy_preservation': {
                'plans_created': len(preservation_plans),
                'data_archival_ready': any(p.data_archival_strategy for p in preservation_plans),
                'documentation_preserved': any(p.documentation_preservation for p in preservation_plans)
            }
        }
    
    def _get_current_decentralization_level(self, plan: ExitPlan) -> str:
        """Assess current decentralization level"""
        completed_phases = len(plan.phases_completed)
        total_phases = len(plan.decentralization_milestones)
        
        if completed_phases == 0:
            return DecentralizationLevel.CENTRALIZED.value
        elif completed_phases < total_phases * 0.3:
            return DecentralizationLevel.CENTRALIZED.value
        elif completed_phases < total_phases * 0.7:
            return DecentralizationLevel.SEMI_DECENTRALIZED.value
        elif completed_phases < total_phases * 0.9:
            return DecentralizationLevel.DECENTRALIZED.value
        else:
            return DecentralizationLevel.FULLY_AUTONOMOUS.value
    
    def _assess_community_readiness(self) -> Dict:
        """Assess community readiness for governance"""
        # In real implementation, would analyze community metrics
        return {
            'active_community_members': 5000,  # Placeholder
            'governance_participation_rate': 0.15,
            'proposal_success_rate': 0.73,
            'average_voting_participation': 0.08,
            'readiness_score': 0.75
        }