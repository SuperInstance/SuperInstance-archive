from typing import Dict, List, Optional, Tuple, Callable, Any
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
from pydantic import BaseModel

from .models import MarketSymbol, Order, Trade, OrderSide, OrderType

class StrategyType(str, Enum):
    DOLLAR_COST_AVERAGING = "dollar_cost_averaging"
    REBALANCING = "rebalancing"
    YIELD_FARMING = "yield_farming"
    MOMENTUM_TRADING = "momentum_trading"
    MEAN_REVERSION = "mean_reversion"
    LIQUIDITY_PROVISION = "liquidity_provision"

class StrategyStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskType(str, Enum):
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    CODE_REVIEW = "code_review"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    TRANSLATION = "translation"

class TaskStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    VERIFIED = "verified"
    REJECTED = "rejected"

class AutoInvestmentStrategy(BaseModel):
    strategy_id: str = None
    user_id: str
    strategy_type: StrategyType
    name: str
    description: str
    parameters: Dict[str, Any]
    target_symbols: List[MarketSymbol]
    allocation_percentages: Dict[str, Decimal]  # symbol -> percentage
    monthly_investment: Decimal
    min_investment_amount: Decimal = Decimal('10')
    max_investment_amount: Decimal = Decimal('1000')
    risk_tolerance: str = "medium"  # low, medium, high
    status: StrategyStatus = StrategyStatus.ACTIVE
    total_invested: Decimal = Decimal('0')
    current_value: Decimal = Decimal('0')
    total_return: Decimal = Decimal('0')
    last_execution: Optional[datetime] = None
    next_execution: Optional[datetime] = None
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.strategy_id:
            self.strategy_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class YieldFarmingPool(BaseModel):
    pool_id: str = None
    name: str
    description: str
    base_symbol: MarketSymbol
    quote_symbol: MarketSymbol
    apy_rate: Decimal  # Annual percentage yield
    minimum_stake: Decimal
    lock_period_days: int = 0  # 0 for flexible staking
    total_staked: Decimal = Decimal('0')
    rewards_distributed: Decimal = Decimal('0')
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.pool_id:
            self.pool_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class StakingPosition(BaseModel):
    position_id: str = None
    user_id: str
    pool_id: str
    amount_staked: Decimal
    rewards_earned: Decimal = Decimal('0')
    stake_date: datetime = None
    unlock_date: Optional[datetime] = None
    is_active: bool = True
    auto_compound: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.position_id:
            self.position_id = str(uuid.uuid4())
        if not self.stake_date:
            self.stake_date = datetime.now()

class ReferralProgram(BaseModel):
    program_id: str = None
    referrer_id: str
    referral_code: str = None
    referrals_made: int = 0
    total_commission_earned: Decimal = Decimal('0')
    commission_rate: Decimal = Decimal('0.05')  # 5% commission
    tier_level: int = 1
    tier_benefits: Dict[str, Any] = {}
    is_active: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.program_id:
            self.program_id = str(uuid.uuid4())
        if not self.referral_code:
            self.referral_code = f"REF-{self.referrer_id[:8]}-{uuid.uuid4().hex[:6].upper()}"
        if not self.created_at:
            self.created_at = datetime.now()

class TaskBounty(BaseModel):
    bounty_id: str = None
    title: str
    description: str
    task_type: TaskType
    difficulty_level: str = "medium"  # easy, medium, hard, expert
    reward_amount: Decimal
    reward_symbol: MarketSymbol
    requirements: List[str]
    deadline: Optional[datetime] = None
    status: TaskStatus = TaskStatus.OPEN
    assigned_to: Optional[str] = None
    submitted_by: str
    completed_by: Optional[str] = None
    verification_required: bool = True
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.bounty_id:
            self.bounty_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class ContentCreationReward(BaseModel):
    reward_id: str = None
    creator_id: str
    content_type: str  # blog_post, video, tutorial, review
    content_title: str
    content_url: str
    quality_score: Decimal = Decimal('0')  # 0-10 rating
    engagement_metrics: Dict[str, int] = {}  # views, likes, shares, etc.
    reward_amount: Decimal = Decimal('0')
    reward_symbol: MarketSymbol
    status: str = "pending"  # pending, approved, rejected
    created_at: datetime = None
    approved_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.reward_id:
            self.reward_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class YieldOptimizationSystem:
    def __init__(self, matching_engine, portfolio_manager, amm):
        self.matching_engine = matching_engine
        self.portfolio_manager = portfolio_manager
        self.amm = amm
        
        self.investment_strategies: Dict[str, AutoInvestmentStrategy] = {}
        self.yield_farming_pools: Dict[str, YieldFarmingPool] = {}
        self.staking_positions: Dict[str, List[StakingPosition]] = {}  # user_id -> positions
        self.referral_programs: Dict[str, ReferralProgram] = {}
        self.task_bounties: Dict[str, TaskBounty] = {}
        self.content_rewards: Dict[str, List[ContentCreationReward]] = {}  # creator_id -> rewards
        
        # Initialize default yield farming pools
        self._initialize_yield_pools()
        
        # Start background strategy execution
        self._start_strategy_executor()
    
    def _initialize_yield_pools(self):
        """Initialize default yield farming pools"""
        pools = [
            {
                'name': 'ActiveLog Staking Pool',
                'description': 'Stake ALOG tokens for steady rewards',
                'base_symbol': MarketSymbol.ACTIVELOG_CC,
                'quote_symbol': MarketSymbol.ACTIVELOG_CC,
                'apy_rate': Decimal('0.12'),  # 12% APY
                'minimum_stake': Decimal('100'),
                'lock_period_days': 0
            },
            {
                'name': 'DMLog LP Pool',
                'description': 'Provide liquidity for DMLOG/CC pair',
                'base_symbol': MarketSymbol.DMLOG_CC,
                'quote_symbol': MarketSymbol.ACTIVELOG_CC,
                'apy_rate': Decimal('0.18'),  # 18% APY
                'minimum_stake': Decimal('50'),
                'lock_period_days': 30
            },
            {
                'name': 'StudyLog Education Fund',
                'description': 'Long-term staking with educational benefits',
                'base_symbol': MarketSymbol.STUDYLOG_CC,
                'quote_symbol': MarketSymbol.ACTIVELOG_CC,
                'apy_rate': Decimal('0.15'),  # 15% APY
                'minimum_stake': Decimal('200'),
                'lock_period_days': 90
            }
        ]
        
        for pool_data in pools:
            pool = YieldFarmingPool(**pool_data)
            self.yield_farming_pools[pool.pool_id] = pool
    
    def create_investment_strategy(self, user_id: str, strategy_data: Dict) -> AutoInvestmentStrategy:
        """Create a new auto-investment strategy"""
        strategy = AutoInvestmentStrategy(user_id=user_id, **strategy_data)
        
        # Set next execution time
        if strategy.strategy_type == StrategyType.DOLLAR_COST_AVERAGING:
            strategy.next_execution = datetime.now() + timedelta(days=30)  # Monthly
        elif strategy.strategy_type == StrategyType.REBALANCING:
            strategy.next_execution = datetime.now() + timedelta(days=90)  # Quarterly
        
        self.investment_strategies[strategy.strategy_id] = strategy
        return strategy
    
    def execute_dollar_cost_averaging(self, strategy: AutoInvestmentStrategy) -> Dict:
        """Execute dollar cost averaging strategy"""
        try:
            total_amount = strategy.monthly_investment
            results = []
            
            for symbol_str, percentage in strategy.allocation_percentages.items():
                try:
                    symbol = MarketSymbol(symbol_str)
                    amount_to_invest = total_amount * percentage / 100
                    
                    if amount_to_invest >= strategy.min_investment_amount:
                        # Create market buy order
                        order = Order(
                            user_id=strategy.user_id,
                            symbol=symbol,
                            side=OrderSide.BUY,
                            order_type=OrderType.MARKET,
                            quantity=amount_to_invest  # Will be converted to shares based on price
                        )
                        
                        # Submit order (in real implementation)
                        # trades = await self.matching_engine.submit_order(order)
                        
                        results.append({
                            'symbol': symbol.value,
                            'amount_invested': float(amount_to_invest),
                            'status': 'success'
                        })
                        
                        strategy.total_invested += amount_to_invest
                
                except Exception as e:
                    results.append({
                        'symbol': symbol_str,
                        'error': str(e),
                        'status': 'failed'
                    })
            
            strategy.last_execution = datetime.now()
            strategy.next_execution = datetime.now() + timedelta(days=30)
            
            return {
                'strategy_id': strategy.strategy_id,
                'execution_date': strategy.last_execution.isoformat(),
                'total_invested': float(strategy.monthly_investment),
                'results': results
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def execute_rebalancing_strategy(self, strategy: AutoInvestmentStrategy) -> Dict:
        """Execute portfolio rebalancing strategy"""
        try:
            # Get current portfolio positions
            positions = self.portfolio_manager.get_positions(strategy.user_id)
            
            if not positions:
                return {'error': 'No positions to rebalance'}
            
            # Calculate current allocation
            total_value = sum(pos.market_value for pos in positions)
            current_allocation = {
                pos.symbol.value: pos.market_value / total_value 
                for pos in positions
            }
            
            rebalancing_trades = []
            
            for symbol_str, target_percentage in strategy.allocation_percentages.items():
                current_percentage = current_allocation.get(symbol_str, 0)
                target_decimal = target_percentage / 100
                
                deviation = abs(target_decimal - current_percentage)
                
                # Rebalance if deviation > 5%
                if deviation > 0.05:
                    target_value = total_value * target_decimal
                    current_value = current_allocation.get(symbol_str, 0) * total_value
                    
                    if target_value > current_value:
                        # Need to buy more
                        amount_to_buy = target_value - current_value
                        rebalancing_trades.append({
                            'symbol': symbol_str,
                            'action': 'buy',
                            'amount': float(amount_to_buy),
                            'reason': f'Under-allocated by {deviation:.1%}'
                        })
                    else:
                        # Need to sell some
                        amount_to_sell = current_value - target_value
                        rebalancing_trades.append({
                            'symbol': symbol_str,
                            'action': 'sell',
                            'amount': float(amount_to_sell),
                            'reason': f'Over-allocated by {deviation:.1%}'
                        })
            
            strategy.last_execution = datetime.now()
            strategy.next_execution = datetime.now() + timedelta(days=90)
            
            return {
                'strategy_id': strategy.strategy_id,
                'execution_date': strategy.last_execution.isoformat(),
                'rebalancing_trades': rebalancing_trades,
                'current_allocation': {k: f"{v:.1%}" for k, v in current_allocation.items()}
            }
        
        except Exception as e:
            return {'error': str(e)}
    
    def stake_in_yield_pool(self, user_id: str, pool_id: str, amount: Decimal) -> Dict:
        """Stake tokens in a yield farming pool"""
        pool = self.yield_farming_pools.get(pool_id)
        if not pool or not pool.is_active:
            return {'error': 'Pool not found or inactive'}
        
        if amount < pool.minimum_stake:
            return {'error': f'Minimum stake is {pool.minimum_stake}'}
        
        # Create staking position
        position = StakingPosition(
            user_id=user_id,
            pool_id=pool_id,
            amount_staked=amount
        )
        
        # Set unlock date if locked staking
        if pool.lock_period_days > 0:
            position.unlock_date = datetime.now() + timedelta(days=pool.lock_period_days)
        
        # Add to user's positions
        if user_id not in self.staking_positions:
            self.staking_positions[user_id] = []
        
        self.staking_positions[user_id].append(position)
        
        # Update pool totals
        pool.total_staked += amount
        
        return {
            'position_id': position.position_id,
            'pool_name': pool.name,
            'amount_staked': float(amount),
            'apy_rate': float(pool.apy_rate * 100),  # Convert to percentage
            'unlock_date': position.unlock_date.isoformat() if position.unlock_date else None,
            'daily_reward_estimate': float(amount * pool.apy_rate / 365)
        }
    
    def calculate_staking_rewards(self, position_id: str) -> Dict:
        """Calculate rewards for a staking position"""
        position = None
        pool = None
        
        # Find position
        for positions_list in self.staking_positions.values():
            position = next((p for p in positions_list if p.position_id == position_id), None)
            if position:
                pool = self.yield_farming_pools[position.pool_id]
                break
        
        if not position or not pool:
            return {'error': 'Position not found'}
        
        # Calculate rewards based on time staked
        days_staked = (datetime.now() - position.stake_date).days
        if days_staked == 0:
            days_staked = 1  # Minimum 1 day for partial day calculation
        
        daily_rate = pool.apy_rate / 365
        total_rewards = position.amount_staked * daily_rate * days_staked
        
        # Subtract already claimed rewards
        pending_rewards = total_rewards - position.rewards_earned
        
        return {
            'position_id': position_id,
            'amount_staked': float(position.amount_staked),
            'days_staked': days_staked,
            'total_rewards': float(total_rewards),
            'rewards_earned': float(position.rewards_earned),
            'pending_rewards': float(pending_rewards),
            'apy_rate': float(pool.apy_rate * 100),
            'can_withdraw': not position.unlock_date or datetime.now() >= position.unlock_date
        }
    
    def claim_staking_rewards(self, user_id: str, position_id: str) -> Dict:
        """Claim pending staking rewards"""
        user_positions = self.staking_positions.get(user_id, [])
        position = next((p for p in user_positions if p.position_id == position_id), None)
        
        if not position:
            return {'error': 'Position not found'}
        
        reward_info = self.calculate_staking_rewards(position_id)
        if 'error' in reward_info:
            return reward_info
        
        pending_rewards = Decimal(str(reward_info['pending_rewards']))
        
        if pending_rewards <= 0:
            return {'error': 'No rewards to claim'}
        
        # Update position
        position.rewards_earned += pending_rewards
        
        # Auto-compound if enabled
        if position.auto_compound:
            position.amount_staked += pending_rewards
            
            return {
                'rewards_claimed': float(pending_rewards),
                'auto_compounded': True,
                'new_stake_amount': float(position.amount_staked)
            }
        else:
            # In real implementation, would credit user's balance
            return {
                'rewards_claimed': float(pending_rewards),
                'auto_compounded': False
            }
    
    def create_referral_program(self, referrer_id: str) -> ReferralProgram:
        """Create a referral program for a user"""
        program = ReferralProgram(referrer_id=referrer_id)
        
        # Set tier benefits
        program.tier_benefits = {
            'tier_1': {'commission_rate': 0.05, 'bonus_rewards': 0},
            'tier_2': {'commission_rate': 0.07, 'bonus_rewards': 100},  # 10+ referrals
            'tier_3': {'commission_rate': 0.10, 'bonus_rewards': 500}   # 50+ referrals
        }
        
        self.referral_programs[program.program_id] = program
        return program
    
    def process_referral_signup(self, referral_code: str, new_user_id: str) -> Dict:
        """Process a new user signup with referral code"""
        # Find referral program
        program = None
        for prog in self.referral_programs.values():
            if prog.referral_code == referral_code and prog.is_active:
                program = prog
                break
        
        if not program:
            return {'error': 'Invalid referral code'}
        
        # Update referral stats
        program.referrals_made += 1
        
        # Check for tier advancement
        if program.referrals_made >= 50:
            program.tier_level = 3
        elif program.referrals_made >= 10:
            program.tier_level = 2
        
        # Calculate signup bonus
        tier_benefits = program.tier_benefits[f'tier_{program.tier_level}']
        signup_bonus = Decimal(str(tier_benefits['bonus_rewards']))
        
        return {
            'referrer_id': program.referrer_id,
            'new_user_id': new_user_id,
            'signup_bonus': float(signup_bonus),
            'referrer_tier': program.tier_level,
            'total_referrals': program.referrals_made
        }
    
    def create_task_bounty(self, submitted_by: str, bounty_data: Dict) -> TaskBounty:
        """Create a new task bounty"""
        bounty = TaskBounty(submitted_by=submitted_by, **bounty_data)
        
        # Set reward based on difficulty
        difficulty_multipliers = {
            'easy': Decimal('0.5'),
            'medium': Decimal('1.0'),
            'hard': Decimal('2.0'),
            'expert': Decimal('5.0')
        }
        
        base_reward = Decimal('50')  # Base reward amount
        multiplier = difficulty_multipliers.get(bounty.difficulty_level, Decimal('1.0'))
        bounty.reward_amount = base_reward * multiplier
        
        self.task_bounties[bounty.bounty_id] = bounty
        return bounty
    
    def submit_bounty_completion(self, bounty_id: str, completed_by: str, 
                                submission_data: Dict) -> Dict:
        """Submit completion for a task bounty"""
        bounty = self.task_bounties.get(bounty_id)
        if not bounty:
            return {'error': 'Bounty not found'}
        
        if bounty.status != TaskStatus.OPEN:
            return {'error': 'Bounty not available'}
        
        bounty.status = TaskStatus.IN_PROGRESS
        bounty.assigned_to = completed_by
        bounty.completed_by = completed_by
        bounty.completed_at = datetime.now()
        
        if bounty.verification_required:
            bounty.status = TaskStatus.COMPLETED
            return {
                'bounty_id': bounty_id,
                'status': 'submitted_for_review',
                'reward_pending': float(bounty.reward_amount)
            }
        else:
            bounty.status = TaskStatus.VERIFIED
            return self._award_bounty_reward(bounty)
    
    def verify_bounty_completion(self, bounty_id: str, verified: bool, 
                               reviewer_notes: str = "") -> Dict:
        """Verify a completed bounty"""
        bounty = self.task_bounties.get(bounty_id)
        if not bounty or bounty.status != TaskStatus.COMPLETED:
            return {'error': 'Bounty not found or not ready for verification'}
        
        if verified:
            bounty.status = TaskStatus.VERIFIED
            return self._award_bounty_reward(bounty)
        else:
            bounty.status = TaskStatus.REJECTED
            return {
                'bounty_id': bounty_id,
                'status': 'rejected',
                'notes': reviewer_notes
            }
    
    def _award_bounty_reward(self, bounty: TaskBounty) -> Dict:
        """Award reward for completed bounty"""
        # In real implementation, would credit user's account
        return {
            'bounty_id': bounty.bounty_id,
            'completed_by': bounty.completed_by,
            'reward_amount': float(bounty.reward_amount),
            'reward_symbol': bounty.reward_symbol.value,
            'status': 'reward_awarded'
        }
    
    def submit_content_for_reward(self, creator_id: str, content_data: Dict) -> ContentCreationReward:
        """Submit content for reward consideration"""
        reward = ContentCreationReward(creator_id=creator_id, **content_data)
        
        if creator_id not in self.content_rewards:
            self.content_rewards[creator_id] = []
        
        self.content_rewards[creator_id].append(reward)
        return reward
    
    def approve_content_reward(self, reward_id: str, quality_score: Decimal) -> Dict:
        """Approve content reward based on quality"""
        reward = None
        for rewards_list in self.content_rewards.values():
            reward = next((r for r in rewards_list if r.reward_id == reward_id), None)
            if reward:
                break
        
        if not reward:
            return {'error': 'Content reward not found'}
        
        reward.quality_score = quality_score
        reward.status = "approved"
        reward.approved_at = datetime.now()
        
        # Calculate reward based on quality score
        base_reward = Decimal('25')
        quality_multiplier = quality_score / 10  # 0-10 scale
        reward.reward_amount = base_reward * quality_multiplier
        
        return {
            'reward_id': reward_id,
            'quality_score': float(quality_score),
            'reward_amount': float(reward.reward_amount),
            'status': 'approved'
        }
    
    def get_yield_opportunities(self, user_id: str, risk_tolerance: str = "medium") -> List[Dict]:
        """Get available yield opportunities for a user"""
        opportunities = []
        
        # Staking pools
        for pool in self.yield_farming_pools.values():
            if pool.is_active:
                risk_level = self._assess_pool_risk(pool)
                
                if self._matches_risk_tolerance(risk_level, risk_tolerance):
                    opportunities.append({
                        'type': 'staking',
                        'pool_id': pool.pool_id,
                        'name': pool.name,
                        'description': pool.description,
                        'apy': float(pool.apy_rate * 100),
                        'minimum_stake': float(pool.minimum_stake),
                        'lock_period_days': pool.lock_period_days,
                        'risk_level': risk_level,
                        'total_staked': float(pool.total_staked)
                    })
        
        # Active strategies
        user_strategies = [s for s in self.investment_strategies.values() 
                          if s.user_id == user_id and s.status == StrategyStatus.ACTIVE]
        
        for strategy in user_strategies:
            opportunities.append({
                'type': 'auto_strategy',
                'strategy_id': strategy.strategy_id,
                'name': strategy.name,
                'description': strategy.description,
                'expected_return': self._calculate_strategy_expected_return(strategy),
                'next_execution': strategy.next_execution.isoformat() if strategy.next_execution else None,
                'total_invested': float(strategy.total_invested),
                'risk_level': strategy.risk_tolerance
            })
        
        # Task bounties
        active_bounties = [b for b in self.task_bounties.values() 
                          if b.status == TaskStatus.OPEN]
        
        for bounty in active_bounties[:5]:  # Show top 5 bounties
            opportunities.append({
                'type': 'task_bounty',
                'bounty_id': bounty.bounty_id,
                'title': bounty.title,
                'description': bounty.description,
                'reward_amount': float(bounty.reward_amount),
                'difficulty': bounty.difficulty_level,
                'deadline': bounty.deadline.isoformat() if bounty.deadline else None
            })
        
        return sorted(opportunities, key=lambda x: x.get('apy', x.get('expected_return', 0)), reverse=True)
    
    def _assess_pool_risk(self, pool: YieldFarmingPool) -> str:
        """Assess risk level of a staking pool"""
        if pool.lock_period_days == 0:
            return "low"  # Flexible staking is lower risk
        elif pool.lock_period_days <= 30:
            return "medium"
        else:
            return "high"  # Long lock periods are higher risk
    
    def _matches_risk_tolerance(self, risk_level: str, tolerance: str) -> bool:
        """Check if risk level matches user tolerance"""
        risk_scores = {"low": 1, "medium": 2, "high": 3}
        tolerance_scores = {"low": 1, "medium": 2, "high": 3}
        
        return risk_scores[risk_level] <= tolerance_scores[tolerance]
    
    def _calculate_strategy_expected_return(self, strategy: AutoInvestmentStrategy) -> float:
        """Calculate expected return for a strategy"""
        # Simplified calculation - in reality would be much more complex
        base_returns = {
            StrategyType.DOLLAR_COST_AVERAGING: 8.0,  # 8% expected annual return
            StrategyType.REBALANCING: 9.0,
            StrategyType.YIELD_FARMING: 15.0,
            StrategyType.MOMENTUM_TRADING: 12.0,
            StrategyType.MEAN_REVERSION: 10.0
        }
        
        return base_returns.get(strategy.strategy_type, 7.0)
    
    def _start_strategy_executor(self):
        """Start background task to execute strategies"""
        async def execute_strategies():
            while True:
                try:
                    now = datetime.now()
                    
                    for strategy in self.investment_strategies.values():
                        if (strategy.status == StrategyStatus.ACTIVE and 
                            strategy.next_execution and 
                            now >= strategy.next_execution):
                            
                            if strategy.strategy_type == StrategyType.DOLLAR_COST_AVERAGING:
                                result = self.execute_dollar_cost_averaging(strategy)
                            elif strategy.strategy_type == StrategyType.REBALANCING:
                                result = self.execute_rebalancing_strategy(strategy)
                            
                            # Log execution result (in real implementation)
                            print(f"Executed strategy {strategy.strategy_id}: {result}")
                    
                    # Check every hour
                    await asyncio.sleep(3600)
                
                except Exception as e:
                    print(f"Strategy execution error: {e}")
                    await asyncio.sleep(3600)
        
        # Start background task (in real implementation would use proper async task management)
        # asyncio.create_task(execute_strategies())
    
    def get_user_yield_summary(self, user_id: str) -> Dict:
        """Get comprehensive yield summary for user"""
        # Get user strategies
        user_strategies = [s for s in self.investment_strategies.values() if s.user_id == user_id]
        
        # Get staking positions
        user_positions = self.staking_positions.get(user_id, [])
        
        # Get referral program
        user_referral = next((p for p in self.referral_programs.values() 
                            if p.referrer_id == user_id), None)
        
        # Calculate totals
        total_staked = sum(pos.amount_staked for pos in user_positions)
        total_rewards_earned = sum(pos.rewards_earned for pos in user_positions)
        total_strategy_invested = sum(s.total_invested for s in user_strategies)
        
        return {
            'user_id': user_id,
            'active_strategies': len([s for s in user_strategies if s.status == StrategyStatus.ACTIVE]),
            'total_strategy_invested': float(total_strategy_invested),
            'staking_positions': len(user_positions),
            'total_staked': float(total_staked),
            'total_rewards_earned': float(total_rewards_earned),
            'referral_program': {
                'active': user_referral is not None,
                'referrals_made': user_referral.referrals_made if user_referral else 0,
                'commission_earned': float(user_referral.total_commission_earned) if user_referral else 0,
                'referral_code': user_referral.referral_code if user_referral else None
            },
            'available_opportunities': len(self.get_yield_opportunities(user_id))
        }