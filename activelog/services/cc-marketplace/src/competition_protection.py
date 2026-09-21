from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import uuid
from pydantic import BaseModel

from .models import MarketSymbol

class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DefenseStrategy(str, Enum):
    BROAD_OWNERSHIP = "broad_ownership"
    COMMUNITY_LOYALTY = "community_loyalty"
    TECHNICAL_MOATS = "technical_moats"
    ECONOMIC_INCENTIVES = "economic_incentives"
    GOVERNANCE_PROTECTION = "governance_protection"

class CompetitiveThreat(str, Enum):
    HOSTILE_TAKEOVER = "hostile_takeover"
    TALENT_POACHING = "talent_poaching"
    FEATURE_COPYING = "feature_copying"
    PRICE_COMPETITION = "price_competition"
    REGULATORY_CAPTURE = "regulatory_capture"
    NETWORK_FRAGMENTATION = "network_fragmentation"

class OwnershipIncentive(BaseModel):
    incentive_id: str = None
    name: str
    description: str
    target_audience: str  # new_users, long_term_holders, contributors, etc.
    incentive_type: str   # ownership_grants, purchase_discounts, staking_rewards
    symbol: MarketSymbol
    base_amount: Decimal
    multipliers: Dict[str, Decimal] = {}  # conditions -> multiplier
    eligibility_criteria: List[str]
    duration_months: int
    max_participants: Optional[int] = None
    current_participants: int = 0
    budget_allocated: Decimal
    budget_used: Decimal = Decimal('0')
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.incentive_id:
            self.incentive_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class LoyaltyProgram(BaseModel):
    program_id: str = None
    name: str
    description: str
    tier_structure: Dict[str, Dict[str, Any]]  # tier_name -> benefits
    point_earning_rules: List[Dict[str, Any]]
    point_redemption_options: List[Dict[str, Any]]
    special_events: List[Dict[str, Any]] = []
    total_participants: int = 0
    points_distributed: Decimal = Decimal('0')
    rewards_claimed: Decimal = Decimal('0')
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.program_id:
            self.program_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class HoldingBonus(BaseModel):
    bonus_id: str = None
    holder_id: str
    symbol: MarketSymbol
    shares_held: Decimal
    holding_start_date: date
    minimum_holding_period_months: int
    bonus_rate_annual: Decimal  # Additional percentage bonus per year
    accumulated_bonus: Decimal = Decimal('0')
    last_bonus_calculation: date = None
    is_active: bool = True
    early_withdrawal_penalty: Decimal = Decimal('0.05')  # 5% penalty
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.bonus_id:
            self.bonus_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
        if not self.last_bonus_calculation:
            self.last_bonus_calculation = date.today()

class AntiTakeoverProvision(BaseModel):
    provision_id: str = None
    name: str
    description: str
    provision_type: str  # poison_pill, golden_parachute, staggered_board, supermajority
    trigger_conditions: List[str]
    protection_mechanisms: List[str]
    ownership_threshold: Optional[Decimal] = None  # Threshold that triggers provision
    duration_days: Optional[int] = None
    governance_approval_required: bool = True
    community_vote_threshold: Decimal = Decimal('0.67')  # 67% supermajority
    is_active: bool = True
    activated_instances: List[Dict[str, Any]] = []
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.provision_id:
            self.provision_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class CommunityDefenseFund(BaseModel):
    fund_id: str = None
    name: str
    description: str
    total_balance: Decimal = Decimal('0')
    allocated_reserves: Dict[str, Decimal] = {}  # purpose -> amount
    funding_sources: List[Dict[str, Any]] = []
    spending_authority: List[str] = []  # Who can authorize spending
    spending_limits: Dict[str, Decimal] = {}
    emergency_access_conditions: List[str] = []
    disbursements: List[Dict[str, Any]] = []
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.fund_id:
            self.fund_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class GovernanceParticipationReward(BaseModel):
    reward_id: str = None
    participant_id: str
    participation_type: str  # voting, proposal_creation, discussion, review
    activity_date: date
    activity_details: Dict[str, Any]
    base_reward_points: int
    multiplier_applied: Decimal = Decimal('1.0')
    final_reward_amount: Decimal
    reward_symbol: MarketSymbol
    claimed: bool = False
    claimed_at: Optional[datetime] = None
    season_period: str = ""  # e.g., "2024-Q1"
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.reward_id:
            self.reward_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class CommunityMarketingCampaign(BaseModel):
    campaign_id: str = None
    name: str
    description: str
    campaign_type: str  # referral, content_creation, social_media, events
    budget_allocated: Decimal
    budget_spent: Decimal = Decimal('0')
    target_metrics: Dict[str, Any]
    current_metrics: Dict[str, Any] = {}
    rewards_structure: Dict[str, Any]
    participants: List[str] = []  # user IDs
    start_date: date
    end_date: date
    is_active: bool = True
    results_summary: Dict[str, Any] = {}
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.campaign_id:
            self.campaign_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class OpenSourceProtection(BaseModel):
    protection_id: str = None
    license_type: str  # MIT, Apache, GPL, etc.
    patent_protection: bool = False
    trademark_registrations: List[str] = []
    copyright_assignments: List[str] = []
    contributor_agreements: Dict[str, date] = {}  # contributor_id -> agreement_date
    fork_monitoring: Dict[str, Any] = {}
    defensive_publications: List[Dict[str, Any]] = []
    legal_defense_fund: Decimal = Decimal('0')
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.protection_id:
            self.protection_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class CompetitionProtectionSystem:
    def __init__(self):
        self.ownership_incentives: Dict[str, OwnershipIncentive] = {}
        self.loyalty_programs: Dict[str, LoyaltyProgram] = {}
        self.holding_bonuses: Dict[str, List[HoldingBonus]] = {}  # holder_id -> bonuses
        self.anti_takeover_provisions: Dict[str, AntiTakeoverProvision] = {}
        self.community_defense_funds: Dict[str, CommunityDefenseFund] = {}
        self.governance_rewards: Dict[str, List[GovernanceParticipationReward]] = {}  # participant_id -> rewards
        self.marketing_campaigns: Dict[str, CommunityMarketingCampaign] = {}
        self.open_source_protections: Dict[str, OpenSourceProtection] = {}
        
        # Initialize default protection mechanisms
        self._initialize_default_protections()
    
    def _initialize_default_protections(self):
        """Initialize default competition protection mechanisms"""
        
        # Create broad ownership incentive program
        ownership_incentive = OwnershipIncentive(
            name="Community Ownership Expansion",
            description="Distribute shares broadly to prevent concentration",
            target_audience="new_users",
            incentive_type="ownership_grants",
            symbol=MarketSymbol.ACTIVELOG_CC,
            base_amount=Decimal('10'),  # 10 shares per new user
            multipliers={
                "early_adopter": Decimal('2.0'),
                "referral_signup": Decimal('1.5'),
                "community_contributor": Decimal('3.0'),
                "long_term_commitment": Decimal('2.5')
            },
            eligibility_criteria=[
                "account_age_minimum_30_days",
                "completed_onboarding",
                "verified_identity",
                "community_guidelines_accepted"
            ],
            duration_months=24,
            budget_allocated=Decimal('1000000')  # 1M shares budget
        )
        self.ownership_incentives[ownership_incentive.incentive_id] = ownership_incentive
        
        # Create loyalty program
        loyalty_program = LoyaltyProgram(
            name="ActiveLog Champions",
            description="Reward long-term community members and active participants",
            tier_structure={
                "Bronze": {
                    "min_points": 0,
                    "benefits": ["5% trading fee discount", "Access to community forums"],
                    "bonus_multiplier": 1.0
                },
                "Silver": {
                    "min_points": 1000,
                    "benefits": ["10% trading fee discount", "Early access to features", "Monthly CC bonus"],
                    "bonus_multiplier": 1.2
                },
                "Gold": {
                    "min_points": 5000,
                    "benefits": ["15% trading fee discount", "Beta testing access", "Governance voting bonus"],
                    "bonus_multiplier": 1.5
                },
                "Platinum": {
                    "min_points": 15000,
                    "benefits": ["20% trading fee discount", "Direct founder access", "Share bonus program"],
                    "bonus_multiplier": 2.0
                }
            },
            point_earning_rules=[
                {"action": "daily_login", "points": 10},
                {"action": "trade_execution", "points": 50},
                {"action": "referral_signup", "points": 500},
                {"action": "content_creation", "points": 200},
                {"action": "governance_voting", "points": 100},
                {"action": "bug_report", "points": 1000},
                {"action": "community_help", "points": 150}
            ],
            point_redemption_options=[
                {"item": "Trading fee waiver", "cost": 500},
                {"item": "5 CC tokens", "cost": 1000},
                {"item": "Exclusive merchandise", "cost": 2000},
                {"item": "One-on-one consultation", "cost": 5000},
                {"item": "Governance proposal boost", "cost": 3000}
            ]
        )
        self.loyalty_programs[loyalty_program.program_id] = loyalty_program
        
        # Create anti-takeover provisions
        poison_pill = AntiTakeoverProvision(
            name="Shareholder Rights Plan",
            description="Dilutes hostile acquirer's position if ownership threshold exceeded",
            provision_type="poison_pill",
            trigger_conditions=[
                "single_entity_ownership_exceeds_15_percent",
                "coordinated_group_ownership_exceeds_20_percent",
                "hostile_intent_declared"
            ],
            protection_mechanisms=[
                "issue_rights_to_existing_shareholders",
                "dilute_acquirer_position",
                "board_approval_required_for_large_purchases",
                "mandatory_disclosure_above_5_percent"
            ],
            ownership_threshold=Decimal('0.15'),  # 15% trigger
            duration_days=365,
            community_vote_threshold=Decimal('0.75')  # 75% to activate
        )
        self.anti_takeover_provisions[poison_pill.provision_id] = poison_pill
        
        # Create community defense fund
        defense_fund = CommunityDefenseFund(
            name="ActiveLog Defense Treasury",
            description="Fund to protect community interests and respond to competitive threats",
            total_balance=Decimal('500000'),  # $500K initial funding
            allocated_reserves={
                "legal_defense": Decimal('200000'),
                "competitive_response": Decimal('150000'),
                "community_rewards": Decimal('100000'),
                "emergency_fund": Decimal('50000')
            },
            funding_sources=[
                {"source": "transaction_fees", "percentage": 0.1, "amount_contributed": Decimal('100000')},
                {"source": "community_donations", "amount_contributed": Decimal('50000')},
                {"source": "founder_contribution", "amount_contributed": Decimal('350000')}
            ],
            spending_authority=["community_vote", "emergency_board", "founder_veto"],
            spending_limits={
                "single_expenditure": Decimal('25000'),
                "monthly_limit": Decimal('50000'),
                "emergency_limit": Decimal('100000')
            },
            emergency_access_conditions=[
                "imminent_hostile_takeover",
                "critical_competitive_threat",
                "regulatory_challenge",
                "technical_security_breach"
            ]
        )
        self.community_defense_funds[defense_fund.fund_id] = defense_fund
        
        # Create open source protection
        os_protection = OpenSourceProtection(
            license_type="MIT",
            patent_protection=True,
            trademark_registrations=["ActiveLog", "CC Marketplace", "DMLog"],
            copyright_assignments=["All core contributors"],
            fork_monitoring={
                "github_monitoring": True,
                "automated_alerts": True,
                "trademark_enforcement": True
            },
            defensive_publications=[
                {
                    "title": "Distributed User Activity Logging System",
                    "publication_date": "2024-01-15",
                    "purpose": "Prevent patent trolling on core logging mechanisms"
                },
                {
                    "title": "Community-Driven Token Economics Model",
                    "publication_date": "2024-03-20",
                    "purpose": "Protect innovative tokenomics from patent claims"
                }
            ],
            legal_defense_fund=Decimal('100000')
        )
        self.open_source_protections[os_protection.protection_id] = os_protection
    
    def create_ownership_incentive(self, incentive_data: Dict) -> OwnershipIncentive:
        """Create a new broad ownership incentive program"""
        incentive = OwnershipIncentive(**incentive_data)
        self.ownership_incentives[incentive.incentive_id] = incentive
        return incentive
    
    def grant_ownership_incentive(self, user_id: str, incentive_id: str, 
                                 qualifying_conditions: List[str]) -> Dict:
        """Grant ownership incentive to qualifying user"""
        incentive = self.ownership_incentives.get(incentive_id)
        if not incentive or not incentive.is_active:
            return {'error': 'Incentive not found or inactive'}
        
        if incentive.current_participants >= (incentive.max_participants or float('inf')):
            return {'error': 'Maximum participants reached'}
        
        # Check eligibility
        for criteria in incentive.eligibility_criteria:
            if criteria not in qualifying_conditions:
                return {'error': f'Does not meet criteria: {criteria}'}
        
        # Calculate grant amount with multipliers
        base_grant = incentive.base_amount
        total_multiplier = Decimal('1.0')
        
        for condition in qualifying_conditions:
            if condition in incentive.multipliers:
                total_multiplier += incentive.multipliers[condition] - Decimal('1.0')
        
        final_grant = base_grant * total_multiplier
        
        # Check budget
        if incentive.budget_used + final_grant > incentive.budget_allocated:
            return {'error': 'Insufficient budget remaining'}
        
        # Grant the incentive
        incentive.budget_used += final_grant
        incentive.current_participants += 1
        
        return {
            'user_id': user_id,
            'incentive_id': incentive_id,
            'shares_granted': float(final_grant),
            'symbol': incentive.symbol.value,
            'multiplier_applied': float(total_multiplier),
            'conditions_met': qualifying_conditions
        }
    
    def create_long_term_holding_bonus(self, holder_id: str, symbol: MarketSymbol, 
                                     shares_held: Decimal, bonus_config: Dict) -> HoldingBonus:
        """Create long-term holding bonus for loyalty incentive"""
        bonus = HoldingBonus(
            holder_id=holder_id,
            symbol=symbol,
            shares_held=shares_held,
            holding_start_date=date.today(),
            **bonus_config
        )
        
        if holder_id not in self.holding_bonuses:
            self.holding_bonuses[holder_id] = []
        
        self.holding_bonuses[holder_id].append(bonus)
        return bonus
    
    def calculate_holding_bonus(self, bonus_id: str, as_of_date: Optional[date] = None) -> Dict:
        """Calculate accumulated holding bonus"""
        if not as_of_date:
            as_of_date = date.today()
        
        bonus = None
        for bonuses_list in self.holding_bonuses.values():
            bonus = next((b for b in bonuses_list if b.bonus_id == bonus_id), None)
            if bonus:
                break
        
        if not bonus:
            return {'error': 'Holding bonus not found'}
        
        # Calculate holding period
        holding_days = (as_of_date - bonus.holding_start_date).days
        holding_months = holding_days / 30.0
        
        # Check if minimum holding period met
        if holding_months < bonus.minimum_holding_period_months:
            return {
                'bonus_id': bonus_id,
                'holding_period_days': holding_days,
                'minimum_period_met': False,
                'accumulated_bonus': 0,
                'projected_bonus': 0,
                'days_until_eligible': int((bonus.minimum_holding_period_months * 30) - holding_days)
            }
        
        # Calculate bonus
        eligible_days = holding_days
        daily_bonus_rate = bonus.bonus_rate_annual / 365
        new_bonus = bonus.shares_held * daily_bonus_rate * (eligible_days - (bonus.last_bonus_calculation - bonus.holding_start_date).days)
        
        total_accumulated = bonus.accumulated_bonus + new_bonus
        
        return {
            'bonus_id': bonus_id,
            'holder_id': bonus.holder_id,
            'shares_held': float(bonus.shares_held),
            'holding_period_days': holding_days,
            'annual_bonus_rate': float(bonus.bonus_rate_annual * 100),  # Convert to percentage
            'accumulated_bonus': float(total_accumulated),
            'new_bonus_available': float(new_bonus),
            'minimum_period_met': True,
            'early_withdrawal_penalty': float(bonus.early_withdrawal_penalty * 100)
        }
    
    def claim_holding_bonus(self, bonus_id: str, early_withdrawal: bool = False) -> Dict:
        """Claim accumulated holding bonus"""
        bonus_info = self.calculate_holding_bonus(bonus_id)
        if 'error' in bonus_info:
            return bonus_info
        
        if not bonus_info['minimum_period_met'] and not early_withdrawal:
            return {'error': 'Minimum holding period not met'}
        
        # Find and update bonus
        bonus = None
        for bonuses_list in self.holding_bonuses.values():
            bonus = next((b for b in bonuses_list if b.bonus_id == bonus_id), None)
            if bonus:
                break
        
        if not bonus:
            return {'error': 'Bonus not found'}
        
        claimable_amount = Decimal(str(bonus_info['new_bonus_available']))
        
        if early_withdrawal:
            penalty = claimable_amount * bonus.early_withdrawal_penalty
            claimable_amount -= penalty
            
            return {
                'bonus_claimed': float(claimable_amount),
                'penalty_applied': float(penalty),
                'early_withdrawal': True,
                'remaining_shares': float(bonus.shares_held)
            }
        
        # Normal claim
        bonus.accumulated_bonus += claimable_amount
        bonus.last_bonus_calculation = date.today()
        
        return {
            'bonus_claimed': float(claimable_amount),
            'total_accumulated': float(bonus.accumulated_bonus),
            'penalty_applied': 0,
            'early_withdrawal': False
        }
    
    def create_governance_participation_reward(self, participant_id: str, 
                                             participation_data: Dict) -> GovernanceParticipationReward:
        """Reward governance participation"""
        reward = GovernanceParticipationReward(
            participant_id=participant_id,
            **participation_data
        )
        
        # Apply multipliers based on participation quality/frequency
        base_multiplier = Decimal('1.0')
        
        # Frequency multiplier
        recent_participation = len([
            r for rewards_list in self.governance_rewards.values()
            for r in rewards_list
            if r.participant_id == participant_id and 
               r.activity_date >= date.today() - timedelta(days=30)
        ])
        
        if recent_participation >= 10:
            base_multiplier *= Decimal('1.5')  # Very active participant
        elif recent_participation >= 5:
            base_multiplier *= Decimal('1.2')  # Active participant
        
        # Quality multiplier (based on activity type)
        quality_multipliers = {
            "proposal_creation": Decimal('2.0'),
            "detailed_review": Decimal('1.5'),
            "voting": Decimal('1.0'),
            "discussion": Decimal('1.2')
        }
        
        base_multiplier *= quality_multipliers.get(reward.participation_type, Decimal('1.0'))
        
        reward.multiplier_applied = base_multiplier
        reward.final_reward_amount = Decimal(str(reward.base_reward_points)) * base_multiplier
        
        if participant_id not in self.governance_rewards:
            self.governance_rewards[participant_id] = []
        
        self.governance_rewards[participant_id].append(reward)
        return reward
    
    def activate_anti_takeover_provision(self, provision_id: str, trigger_event: Dict) -> Dict:
        """Activate anti-takeover provision in response to threat"""
        provision = self.anti_takeover_provisions.get(provision_id)
        if not provision:
            return {'error': 'Provision not found'}
        
        # Check if trigger conditions are met
        trigger_met = False
        for condition in provision.trigger_conditions:
            if condition in trigger_event.get('conditions_detected', []):
                trigger_met = True
                break
        
        if not trigger_met:
            return {'error': 'Trigger conditions not met'}
        
        # Check if community vote is required and passed
        if provision.governance_approval_required:
            vote_result = trigger_event.get('community_vote_result', 0)
            if vote_result < provision.community_vote_threshold:
                return {'error': f'Community vote failed. Required: {provision.community_vote_threshold:.0%}, Got: {vote_result:.0%}'}
        
        # Activate provision
        activation_instance = {
            'activation_date': datetime.now().isoformat(),
            'trigger_event': trigger_event,
            'protection_mechanisms_activated': provision.protection_mechanisms,
            'duration_days': provision.duration_days,
            'expiry_date': (datetime.now() + timedelta(days=provision.duration_days or 365)).isoformat()
        }
        
        provision.activated_instances.append(activation_instance)
        
        return {
            'provision_activated': provision.name,
            'activation_date': activation_instance['activation_date'],
            'protection_mechanisms': provision.protection_mechanisms,
            'duration_days': provision.duration_days,
            'threat_level': trigger_event.get('threat_level', 'high')
        }
    
    def create_community_marketing_campaign(self, campaign_data: Dict) -> CommunityMarketingCampaign:
        """Create community-driven marketing campaign"""
        campaign = CommunityMarketingCampaign(**campaign_data)
        self.marketing_campaigns[campaign.campaign_id] = campaign
        return campaign
    
    def assess_competitive_threat_level(self, threat_data: Dict) -> Dict:
        """Assess competitive threat and recommend countermeasures"""
        threat_type = CompetitiveThreat(threat_data.get('threat_type'))
        threat_indicators = threat_data.get('indicators', [])
        market_conditions = threat_data.get('market_conditions', {})
        
        # Calculate threat level based on multiple factors
        threat_score = 0
        
        # Threat type severity
        threat_severities = {
            CompetitiveThreat.HOSTILE_TAKEOVER: 10,
            CompetitiveThreat.REGULATORY_CAPTURE: 8,
            CompetitiveThreat.NETWORK_FRAGMENTATION: 7,
            CompetitiveThreat.TALENT_POACHING: 5,
            CompetitiveThreat.FEATURE_COPYING: 4,
            CompetitiveThreat.PRICE_COMPETITION: 3
        }
        
        threat_score += threat_severities.get(threat_type, 5)
        
        # Market condition modifiers
        if market_conditions.get('high_volatility'):
            threat_score += 2
        if market_conditions.get('low_liquidity'):
            threat_score += 2
        if market_conditions.get('regulatory_uncertainty'):
            threat_score += 3
        
        # Indicator-based scoring
        critical_indicators = [
            'large_share_accumulation',
            'coordinated_buying',
            'hostile_public_statements',
            'regulatory_lobbying'
        ]
        
        for indicator in threat_indicators:
            if indicator in critical_indicators:
                threat_score += 3
            else:
                threat_score += 1
        
        # Determine threat level
        if threat_score >= 15:
            threat_level = ThreatLevel.CRITICAL
        elif threat_score >= 10:
            threat_level = ThreatLevel.HIGH
        elif threat_score >= 6:
            threat_level = ThreatLevel.MEDIUM
        else:
            threat_level = ThreatLevel.LOW
        
        # Recommend countermeasures
        recommended_actions = []
        
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            recommended_actions.extend([
                "Activate anti-takeover provisions",
                "Increase community engagement",
                "Accelerate decentralization timeline",
                "Mobilize community defense fund"
            ])
        
        if threat_type == CompetitiveThreat.HOSTILE_TAKEOVER:
            recommended_actions.extend([
                "Implement poison pill strategy",
                "Broad ownership distribution campaign",
                "Emergency governance vote",
                "Legal defense preparation"
            ])
        
        elif threat_type == CompetitiveThreat.TALENT_POACHING:
            recommended_actions.extend([
                "Accelerate employee equity vesting",
                "Increase retention bonuses",
                "Enhance company culture programs",
                "Competitive compensation review"
            ])
        
        return {
            'threat_type': threat_type.value,
            'threat_level': threat_level.value,
            'threat_score': threat_score,
            'assessment_date': datetime.now().isoformat(),
            'recommended_actions': recommended_actions,
            'immediate_steps': recommended_actions[:3],  # Top 3 priority actions
            'monitoring_required': threat_level in [ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        }
    
    def get_community_defense_status(self) -> Dict:
        """Get comprehensive community defense status"""
        # Aggregate data from all protection mechanisms
        total_participants = sum(
            incentive.current_participants 
            for incentive in self.ownership_incentives.values()
        )
        
        total_defense_funding = sum(
            fund.total_balance 
            for fund in self.community_defense_funds.values()
        )
        
        active_holding_bonuses = sum(
            len([b for b in bonuses if b.is_active])
            for bonuses in self.holding_bonuses.values()
        )
        
        governance_participants = len(self.governance_rewards)
        
        active_provisions = len([
            p for p in self.anti_takeover_provisions.values() 
            if p.is_active
        ])
        
        # Calculate decentralization metrics
        broad_ownership_score = min(total_participants / 1000, 1.0)  # Target: 1000 owners
        loyalty_program_score = min(
            sum(p.total_participants for p in self.loyalty_programs.values()) / 5000, 
            1.0
        )  # Target: 5000 loyal users
        governance_score = min(governance_participants / 500, 1.0)  # Target: 500 active governors
        
        overall_defense_score = (
            broad_ownership_score * 0.4 + 
            loyalty_program_score * 0.3 + 
            governance_score * 0.3
        ) * 100
        
        return {
            'overall_defense_score': round(overall_defense_score, 1),
            'metrics': {
                'broad_ownership': {
                    'participants': total_participants,
                    'score': round(broad_ownership_score * 100, 1),
                    'target': 1000
                },
                'loyalty_programs': {
                    'participants': sum(p.total_participants for p in self.loyalty_programs.values()),
                    'score': round(loyalty_program_score * 100, 1),
                    'target': 5000
                },
                'governance_participation': {
                    'participants': governance_participants,
                    'score': round(governance_score * 100, 1),
                    'target': 500
                }
            },
            'defense_mechanisms': {
                'ownership_incentives': len([i for i in self.ownership_incentives.values() if i.is_active]),
                'holding_bonuses': active_holding_bonuses,
                'anti_takeover_provisions': active_provisions,
                'defense_fund_balance': float(total_defense_funding),
                'marketing_campaigns': len([c for c in self.marketing_campaigns.values() if c.is_active])
            },
            'recommendations': self._get_defense_recommendations(overall_defense_score)
        }
    
    def _get_defense_recommendations(self, defense_score: float) -> List[str]:
        """Get recommendations to improve defense posture"""
        recommendations = []
        
        if defense_score < 30:
            recommendations.extend([
                "URGENT: Launch broad ownership distribution campaign",
                "URGENT: Activate community loyalty programs immediately",
                "URGENT: Increase community engagement and governance participation"
            ])
        elif defense_score < 60:
            recommendations.extend([
                "Expand ownership incentive programs",
                "Enhance loyalty program benefits",
                "Increase governance participation rewards"
            ])
        elif defense_score < 80:
            recommendations.extend([
                "Fine-tune existing programs",
                "Launch specialized retention initiatives",
                "Prepare advanced anti-takeover measures"
            ])
        else:
            recommendations.extend([
                "Maintain current defense posture",
                "Monitor for emerging threats",
                "Continue community engagement excellence"
            ])
        
        return recommendations