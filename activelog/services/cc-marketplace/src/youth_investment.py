from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum
import uuid
from pydantic import BaseModel

from .models import MarketSymbol, Order, Trade

class AccountType(str, Enum):
    MINOR_SUPERVISED = "minor_supervised"  # Under 18 with parent supervision
    YOUNG_ADULT = "young_adult"           # 18+ with educational features
    EDUCATIONAL = "educational"           # School/classroom accounts

class InvestmentGoalType(str, Enum):
    COLLEGE_FUND = "college_fund"
    FIRST_CAR = "first_car"
    EMERGENCY_FUND = "emergency_fund"
    VACATION = "vacation"
    CUSTOM = "custom"

class GameLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class AchievementType(str, Enum):
    FIRST_TRADE = "first_trade"
    CONSISTENT_SAVER = "consistent_saver"
    GOAL_ACHIEVED = "goal_achieved"
    RISK_MANAGER = "risk_manager"
    DIVERSIFIED_PORTFOLIO = "diversified_portfolio"
    LONG_TERM_HOLDER = "long_term_holder"
    COMPOUND_INTEREST_MASTER = "compound_interest_master"

class YouthAccount(BaseModel):
    account_id: str = None
    youth_name: str
    birth_date: date
    parent_guardian_id: Optional[str] = None  # Required for minors
    account_type: AccountType
    supervision_level: str = "high"  # high, medium, low
    monthly_investment_limit: Decimal = Decimal('100')
    total_investment_limit: Decimal = Decimal('2000')
    real_money_enabled: bool = False
    virtual_balance: Decimal = Decimal('10000')  # Starting virtual money
    real_balance: Decimal = Decimal('0')
    educational_progress: Dict[str, bool] = {}
    game_level: GameLevel = GameLevel.BEGINNER
    achievement_points: int = 0
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.account_id:
            self.account_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()
        
        # Set account type based on age
        age = (datetime.now().date() - self.birth_date).days // 365
        if age < 18:
            self.account_type = AccountType.MINOR_SUPERVISED
        else:
            self.account_type = AccountType.YOUNG_ADULT

class ParentGuardian(BaseModel):
    guardian_id: str = None
    name: str
    email: str
    phone: str
    notification_preferences: Dict[str, bool] = {
        'trade_notifications': True,
        'achievement_alerts': True,
        'monthly_reports': True,
        'risk_alerts': True
    }
    supervised_accounts: List[str] = []  # List of youth account IDs
    approval_required_threshold: Decimal = Decimal('50')  # Trades above this need approval
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.guardian_id:
            self.guardian_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class InvestmentGoal(BaseModel):
    goal_id: str = None
    account_id: str
    goal_type: InvestmentGoalType
    title: str
    description: str
    target_amount: Decimal
    current_amount: Decimal = Decimal('0')
    target_date: date
    monthly_contribution: Decimal = Decimal('0')
    symbols_allocated: Dict[str, Decimal] = {}  # symbol -> percentage allocation
    is_achieved: bool = False
    created_at: datetime = None
    achieved_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.goal_id:
            self.goal_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class MockTradingGame(BaseModel):
    game_id: str = None
    account_id: str
    game_name: str
    description: str
    starting_balance: Decimal = Decimal('10000')
    current_balance: Decimal = Decimal('10000')
    portfolio_value: Decimal = Decimal('10000')
    total_return: Decimal = Decimal('0')
    trades_made: int = 0
    duration_days: int = 30
    start_date: datetime = None
    end_date: Optional[datetime] = None
    is_active: bool = True
    leaderboard_eligible: bool = True
    game_level: GameLevel = GameLevel.BEGINNER
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.game_id:
            self.game_id = str(uuid.uuid4())
        if not self.start_date:
            self.start_date = datetime.now()
        if not self.end_date:
            self.end_date = self.start_date + timedelta(days=self.duration_days)

class EducationalModule(BaseModel):
    module_id: str = None
    title: str
    description: str
    content: str
    learning_objectives: List[str]
    quiz_questions: List[Dict[str, Any]] = []
    required_for_level: GameLevel
    completion_points: int = 100
    estimated_minutes: int = 30
    prerequisites: List[str] = []  # Other module IDs required first
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.module_id:
            self.module_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class Achievement(BaseModel):
    achievement_id: str = None
    account_id: str
    achievement_type: AchievementType
    title: str
    description: str
    points_awarded: int
    unlocked_at: datetime = None
    requirements_met: Dict[str, bool] = {}
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.achievement_id:
            self.achievement_id = str(uuid.uuid4())
        if not self.unlocked_at:
            self.unlocked_at = datetime.now()

class YouthInvestmentSystem:
    def __init__(self):
        self.youth_accounts: Dict[str, YouthAccount] = {}
        self.parent_guardians: Dict[str, ParentGuardian] = {}
        self.investment_goals: Dict[str, List[InvestmentGoal]] = {}  # account_id -> goals
        self.mock_trading_games: Dict[str, MockTradingGame] = {}
        self.educational_modules: Dict[str, EducationalModule] = {}
        self.achievements: Dict[str, List[Achievement]] = {}  # account_id -> achievements
        self.pending_approvals: Dict[str, Order] = {}  # order_id -> Order awaiting approval
        
        # Initialize educational content
        self._initialize_educational_modules()
        
        # Achievement definitions
        self.achievement_definitions = {
            AchievementType.FIRST_TRADE: {
                'title': 'First Steps',
                'description': 'Completed your first trade!',
                'points': 50,
                'requirements': {'trades_made': 1}
            },
            AchievementType.CONSISTENT_SAVER: {
                'title': 'Consistent Saver',
                'description': 'Made regular contributions for 3 months',
                'points': 200,
                'requirements': {'consistent_months': 3}
            },
            AchievementType.GOAL_ACHIEVED: {
                'title': 'Goal Crusher',
                'description': 'Achieved your first investment goal!',
                'points': 300,
                'requirements': {'goals_achieved': 1}
            },
            AchievementType.DIVERSIFIED_PORTFOLIO: {
                'title': 'Smart Diversifier',
                'description': 'Built a diversified portfolio across 3+ symbols',
                'points': 150,
                'requirements': {'symbols_owned': 3}
            }
        }
    
    def _initialize_educational_modules(self):
        """Initialize educational content modules"""
        modules = [
            {
                'title': 'Introduction to Investing',
                'description': 'Learn the basics of investing and building wealth',
                'content': '''
                Welcome to investing! Investing means putting your money to work to grow over time.
                
                Key concepts:
                - Stocks represent ownership in companies
                - Diversification spreads risk across different investments
                - Time is your biggest advantage when investing
                - Compound interest is the eighth wonder of the world
                
                Remember: All investments carry risk, but not investing is also risky!
                ''',
                'learning_objectives': [
                    'Understand what investing means',
                    'Learn about different types of investments',
                    'Understand risk and return',
                    'Learn about compound interest'
                ],
                'quiz_questions': [
                    {
                        'question': 'What is compound interest?',
                        'options': [
                            'Interest earned only on the principal amount',
                            'Interest earned on both principal and previously earned interest',
                            'A type of bank account',
                            'A complex math formula'
                        ],
                        'correct_answer': 1
                    }
                ],
                'required_for_level': GameLevel.BEGINNER,
                'completion_points': 100,
                'estimated_minutes': 20
            },
            {
                'title': 'Risk and Diversification',
                'description': 'Learn how to manage investment risk through diversification',
                'content': '''
                Risk is the possibility of losing money on an investment. But risk and return go hand in hand.
                
                Types of risk:
                - Market risk: Overall market declines
                - Company risk: Individual company problems
                - Inflation risk: Your money loses buying power
                
                Diversification helps by:
                - Spreading investments across different companies
                - Investing in different industries
                - Not putting all eggs in one basket
                
                The goal is to maximize return while minimizing risk.
                ''',
                'learning_objectives': [
                    'Understand different types of investment risk',
                    'Learn how diversification reduces risk',
                    'Understand the risk-return relationship',
                    'Learn to build a balanced portfolio'
                ],
                'required_for_level': GameLevel.INTERMEDIATE,
                'completion_points': 150,
                'estimated_minutes': 25,
                'prerequisites': ['Introduction to Investing']
            },
            {
                'title': 'Compound Interest Magic',
                'description': 'Discover the power of compound interest and long-term investing',
                'content': '''
                Compound interest is when you earn interest on your interest. It's incredibly powerful!
                
                The Rule of 72:
                - Divide 72 by your annual return rate
                - Result = years for your money to double
                - Example: 8% return → 72÷8 = 9 years to double
                
                Starting early matters:
                - $100/month from age 20-30 (10 years) = $190,000 at age 65
                - $100/month from age 30-65 (35 years) = $177,000 at age 65
                - Starting 10 years earlier beats 25 extra years!
                
                Time is your superpower in investing.
                ''',
                'learning_objectives': [
                    'Understand compound interest calculations',
                    'Learn the Rule of 72',
                    'Understand the importance of starting early',
                    'Calculate compound growth scenarios'
                ],
                'required_for_level': GameLevel.INTERMEDIATE,
                'completion_points': 200,
                'estimated_minutes': 30
            }
        ]
        
        for module_data in modules:
            module = EducationalModule(**module_data)
            self.educational_modules[module.module_id] = module
    
    def create_youth_account(self, youth_data: Dict, parent_data: Optional[Dict] = None) -> YouthAccount:
        """Create a new youth investment account"""
        account = YouthAccount(**youth_data)
        
        # If minor, create or link parent/guardian account
        if account.account_type == AccountType.MINOR_SUPERVISED and parent_data:
            if account.parent_guardian_id:
                # Link to existing guardian
                guardian = self.parent_guardians[account.parent_guardian_id]
                guardian.supervised_accounts.append(account.account_id)
            else:
                # Create new guardian
                guardian = ParentGuardian(**parent_data)
                guardian.supervised_accounts.append(account.account_id)
                account.parent_guardian_id = guardian.guardian_id
                self.parent_guardians[guardian.guardian_id] = guardian
        
        self.youth_accounts[account.account_id] = account
        self.investment_goals[account.account_id] = []
        self.achievements[account.account_id] = []
        
        return account
    
    def create_investment_goal(self, account_id: str, goal_data: Dict) -> InvestmentGoal:
        """Create a new investment goal"""
        if account_id not in self.youth_accounts:
            raise ValueError("Account not found")
        
        goal = InvestmentGoal(account_id=account_id, **goal_data)
        
        if account_id not in self.investment_goals:
            self.investment_goals[account_id] = []
        
        self.investment_goals[account_id].append(goal)
        return goal
    
    def calculate_goal_progress(self, goal_id: str) -> Dict:
        """Calculate progress toward an investment goal"""
        goal = None
        for goals_list in self.investment_goals.values():
            goal = next((g for g in goals_list if g.goal_id == goal_id), None)
            if goal:
                break
        
        if not goal:
            return {'error': 'Goal not found'}
        
        progress_percentage = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        days_remaining = (goal.target_date - datetime.now().date()).days
        months_remaining = max(days_remaining // 30, 1)
        
        # Calculate required monthly contribution to reach goal
        remaining_amount = goal.target_amount - goal.current_amount
        required_monthly = remaining_amount / months_remaining if months_remaining > 0 else remaining_amount
        
        # Compound interest projection
        monthly_rate = Decimal('0.08') / 12  # Assume 8% annual return
        if goal.monthly_contribution > 0 and months_remaining > 0:
            projected_amount = self._calculate_future_value(
                goal.current_amount, 
                goal.monthly_contribution, 
                monthly_rate, 
                months_remaining
            )
        else:
            projected_amount = goal.current_amount
        
        return {
            'goal_id': goal_id,
            'progress_percentage': float(progress_percentage),
            'current_amount': float(goal.current_amount),
            'target_amount': float(goal.target_amount),
            'days_remaining': days_remaining,
            'months_remaining': months_remaining,
            'required_monthly_contribution': float(required_monthly),
            'current_monthly_contribution': float(goal.monthly_contribution),
            'projected_final_amount': float(projected_amount),
            'on_track': projected_amount >= goal.target_amount,
            'shortfall': float(max(goal.target_amount - projected_amount, 0))
        }
    
    def _calculate_future_value(self, present_value: Decimal, monthly_payment: Decimal, 
                              monthly_rate: Decimal, months: int) -> Decimal:
        """Calculate future value with compound interest and monthly contributions"""
        if monthly_rate == 0:
            return present_value + (monthly_payment * months)
        
        # Future value of present amount
        fv_present = present_value * ((1 + monthly_rate) ** months)
        
        # Future value of monthly payments (annuity)
        fv_payments = monthly_payment * (((1 + monthly_rate) ** months - 1) / monthly_rate)
        
        return fv_present + fv_payments
    
    def create_mock_trading_game(self, account_id: str, game_data: Dict) -> MockTradingGame:
        """Create a new mock trading game"""
        if account_id not in self.youth_accounts:
            raise ValueError("Account not found")
        
        game = MockTradingGame(account_id=account_id, **game_data)
        self.mock_trading_games[game.game_id] = game
        return game
    
    def execute_mock_trade(self, game_id: str, symbol: MarketSymbol, side: str, 
                          quantity: Decimal, price: Decimal) -> Dict:
        """Execute a trade in mock trading game"""
        game = self.mock_trading_games.get(game_id)
        if not game or not game.is_active:
            return {'error': 'Game not found or inactive'}
        
        if datetime.now() > game.end_date:
            game.is_active = False
            return {'error': 'Game has ended'}
        
        total_cost = quantity * price
        
        if side.lower() == 'buy':
            if total_cost > game.current_balance:
                return {'error': 'Insufficient virtual funds'}
            
            game.current_balance -= total_cost
        else:  # sell
            # In real implementation, would check holdings
            game.current_balance += total_cost
        
        game.trades_made += 1
        
        # Check for achievements
        self._check_achievements(game.account_id, {'trades_made': game.trades_made})
        
        return {
            'success': True,
            'game_id': game_id,
            'remaining_balance': float(game.current_balance),
            'trades_made': game.trades_made
        }
    
    def submit_real_trade_for_approval(self, account_id: str, order_data: Dict) -> Dict:
        """Submit a real money trade for parent approval if required"""
        account = self.youth_accounts.get(account_id)
        if not account:
            return {'error': 'Account not found'}
        
        if not account.real_money_enabled:
            return {'error': 'Real money trading not enabled'}
        
        order = Order(**order_data)
        trade_value = order.quantity * (order.price or Decimal('100'))  # Estimate for market orders
        
        # Check limits
        if trade_value > account.monthly_investment_limit:
            return {'error': f'Trade exceeds monthly limit of ${account.monthly_investment_limit}'}
        
        # Check if parent approval required
        guardian = self.parent_guardians.get(account.parent_guardian_id) if account.parent_guardian_id else None
        needs_approval = (
            guardian and 
            trade_value > guardian.approval_required_threshold and 
            account.supervision_level in ['high', 'medium']
        )
        
        if needs_approval:
            self.pending_approvals[order.order_id] = order
            # In real implementation, would send notification to parent
            return {
                'order_id': order.order_id,
                'status': 'pending_approval',
                'requires_parent_approval': True,
                'trade_value': float(trade_value)
            }
        else:
            # Execute immediately
            return {
                'order_id': order.order_id,
                'status': 'submitted',
                'requires_parent_approval': False
            }
    
    def approve_trade(self, guardian_id: str, order_id: str, approved: bool) -> Dict:
        """Parent/guardian approves or rejects a trade"""
        guardian = self.parent_guardians.get(guardian_id)
        if not guardian:
            return {'error': 'Guardian not found'}
        
        order = self.pending_approvals.get(order_id)
        if not order:
            return {'error': 'Order not found or already processed'}
        
        if approved:
            # In real implementation, would submit to matching engine
            del self.pending_approvals[order_id]
            return {'status': 'approved', 'order_id': order_id}
        else:
            del self.pending_approvals[order_id]
            return {'status': 'rejected', 'order_id': order_id}
    
    def complete_educational_module(self, account_id: str, module_id: str, 
                                   quiz_answers: List[int]) -> Dict:
        """Complete an educational module and quiz"""
        account = self.youth_accounts.get(account_id)
        module = self.educational_modules.get(module_id)
        
        if not account or not module:
            return {'error': 'Account or module not found'}
        
        # Grade quiz
        correct_answers = 0
        total_questions = len(module.quiz_questions)
        
        for i, answer in enumerate(quiz_answers):
            if i < len(module.quiz_questions):
                if answer == module.quiz_questions[i]['correct_answer']:
                    correct_answers += 1
        
        passing_score = 0.7  # 70% to pass
        passed = (correct_answers / total_questions) >= passing_score if total_questions > 0 else True
        
        if passed:
            account.educational_progress[module_id] = True
            account.achievement_points += module.completion_points
            
            # Check for level advancement
            self._check_level_advancement(account)
            
            return {
                'passed': True,
                'score': correct_answers / total_questions if total_questions > 0 else 1.0,
                'points_earned': module.completion_points,
                'total_points': account.achievement_points
            }
        else:
            return {
                'passed': False,
                'score': correct_answers / total_questions,
                'required_score': passing_score,
                'can_retake': True
            }
    
    def _check_level_advancement(self, account: YouthAccount):
        """Check if account qualifies for next level"""
        completed_modules = sum(1 for completed in account.educational_progress.values() if completed)
        
        level_requirements = {
            GameLevel.BEGINNER: 0,
            GameLevel.INTERMEDIATE: 2,
            GameLevel.ADVANCED: 5,
            GameLevel.EXPERT: 8
        }
        
        for level, required_modules in level_requirements.items():
            if completed_modules >= required_modules and account.game_level != level:
                account.game_level = level
                # Award level achievement
                self._award_achievement(account.account_id, {
                    'achievement_type': f'level_{level.value}',
                    'title': f'{level.value.title()} Investor',
                    'description': f'Advanced to {level.value} level!',
                    'points_awarded': 500
                })
    
    def _check_achievements(self, account_id: str, metrics: Dict):
        """Check and award achievements based on account activity"""
        account = self.youth_accounts[account_id]
        
        for achievement_type, definition in self.achievement_definitions.items():
            # Check if already earned
            existing_achievements = self.achievements.get(account_id, [])
            if any(a.achievement_type == achievement_type for a in existing_achievements):
                continue
            
            # Check requirements
            requirements_met = True
            for requirement, threshold in definition['requirements'].items():
                if metrics.get(requirement, 0) < threshold:
                    requirements_met = False
                    break
            
            if requirements_met:
                self._award_achievement(account_id, {
                    'achievement_type': achievement_type,
                    'title': definition['title'],
                    'description': definition['description'],
                    'points_awarded': definition['points']
                })
    
    def _award_achievement(self, account_id: str, achievement_data: Dict):
        """Award an achievement to an account"""
        account = self.youth_accounts[account_id]
        
        achievement = Achievement(
            account_id=account_id,
            **achievement_data
        )
        
        if account_id not in self.achievements:
            self.achievements[account_id] = []
        
        self.achievements[account_id].append(achievement)
        account.achievement_points += achievement.points_awarded
    
    def get_compound_interest_calculator(self, principal: Decimal, monthly_contribution: Decimal,
                                       annual_rate: Decimal, years: int) -> Dict:
        """Calculate compound interest scenarios for education"""
        monthly_rate = annual_rate / 12
        months = years * 12
        
        # Calculate with and without contributions
        future_value_principal = principal * ((1 + annual_rate) ** years)
        
        future_value_with_contributions = self._calculate_future_value(
            principal, monthly_contribution, monthly_rate, months
        )
        
        # Calculate year-by-year breakdown
        yearly_breakdown = []
        current_principal = principal
        
        for year in range(1, years + 1):
            # Add monthly contributions for the year
            yearly_contributions = monthly_contribution * 12
            current_principal += yearly_contributions
            
            # Apply compound interest
            current_principal *= (1 + annual_rate)
            
            yearly_breakdown.append({
                'year': year,
                'balance': float(current_principal),
                'contributions_this_year': float(yearly_contributions),
                'interest_earned': float(current_principal - principal - (yearly_contributions * year))
            })
        
        return {
            'inputs': {
                'principal': float(principal),
                'monthly_contribution': float(monthly_contribution),
                'annual_rate': float(annual_rate * 100),  # Convert to percentage
                'years': years
            },
            'results': {
                'final_balance': float(future_value_with_contributions),
                'total_contributions': float(principal + (monthly_contribution * months)),
                'total_interest_earned': float(future_value_with_contributions - principal - (monthly_contribution * months)),
                'principal_only_result': float(future_value_principal)
            },
            'yearly_breakdown': yearly_breakdown
        }
    
    def get_youth_dashboard(self, account_id: str) -> Dict:
        """Get comprehensive dashboard for youth account"""
        account = self.youth_accounts.get(account_id)
        if not account:
            return {'error': 'Account not found'}
        
        # Get goals
        goals = self.investment_goals.get(account_id, [])
        
        # Get achievements
        achievements = self.achievements.get(account_id, [])
        
        # Get active games
        active_games = [g for g in self.mock_trading_games.values() 
                       if g.account_id == account_id and g.is_active]
        
        # Calculate age
        age = (datetime.now().date() - account.birth_date).days // 365
        
        return {
            'account_info': {
                'account_id': account_id,
                'name': account.youth_name,
                'age': age,
                'account_type': account.account_type.value,
                'game_level': account.game_level.value,
                'achievement_points': account.achievement_points,
                'real_money_enabled': account.real_money_enabled
            },
            'balances': {
                'virtual_balance': float(account.virtual_balance),
                'real_balance': float(account.real_balance),
                'monthly_limit': float(account.monthly_investment_limit),
                'total_limit': float(account.total_investment_limit)
            },
            'goals': [
                {
                    'goal_id': g.goal_id,
                    'title': g.title,
                    'target_amount': float(g.target_amount),
                    'current_amount': float(g.current_amount),
                    'progress_percentage': float(g.current_amount / g.target_amount * 100) if g.target_amount > 0 else 0,
                    'target_date': g.target_date.isoformat(),
                    'is_achieved': g.is_achieved
                } for g in goals
            ],
            'recent_achievements': [
                {
                    'title': a.title,
                    'description': a.description,
                    'points_awarded': a.points_awarded,
                    'unlocked_at': a.unlocked_at.isoformat()
                } for a in sorted(achievements, key=lambda x: x.unlocked_at, reverse=True)[:5]
            ],
            'active_games': [
                {
                    'game_id': g.game_id,
                    'name': g.game_name,
                    'current_balance': float(g.current_balance),
                    'total_return': float(g.total_return),
                    'trades_made': g.trades_made,
                    'end_date': g.end_date.isoformat() if g.end_date else None
                } for g in active_games
            ],
            'educational_progress': {
                'completed_modules': sum(1 for completed in account.educational_progress.values() if completed),
                'total_modules': len(self.educational_modules),
                'current_level': account.game_level.value
            }
        }
    
    def get_parent_dashboard(self, guardian_id: str) -> Dict:
        """Get parent/guardian dashboard"""
        guardian = self.parent_guardians.get(guardian_id)
        if not guardian:
            return {'error': 'Guardian account not found'}
        
        supervised_accounts = [
            self.youth_accounts[acc_id] for acc_id in guardian.supervised_accounts
            if acc_id in self.youth_accounts
        ]
        
        # Get pending approvals
        pending_orders = [
            order for order in self.pending_approvals.values()
            if any(order.user_id == acc.account_id for acc in supervised_accounts)
        ]
        
        return {
            'guardian_info': {
                'name': guardian.name,
                'supervised_accounts_count': len(supervised_accounts),
                'notification_preferences': guardian.notification_preferences
            },
            'supervised_accounts': [
                {
                    'account_id': acc.account_id,
                    'youth_name': acc.youth_name,
                    'age': (datetime.now().date() - acc.birth_date).days // 365,
                    'real_balance': float(acc.real_balance),
                    'virtual_balance': float(acc.virtual_balance),
                    'achievement_points': acc.achievement_points,
                    'game_level': acc.game_level.value
                } for acc in supervised_accounts
            ],
            'pending_approvals': [
                {
                    'order_id': order.order_id,
                    'user_id': order.user_id,
                    'symbol': order.symbol.value,
                    'side': order.side.value,
                    'quantity': float(order.quantity),
                    'estimated_value': float(order.quantity * (order.price or Decimal('100'))),
                    'created_at': order.created_at.isoformat() if order.created_at else None
                } for order in pending_orders
            ]
        }