#!/usr/bin/env python3
"""
Spending Tracker with Visual Budgets for MakersLog Kids
Kid-friendly spending visualization and budget management
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncpg
import uuid
from decimal import Decimal, ROUND_HALF_UP

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SpendingCategory(Enum):
    EDUCATIONAL = "educational"
    GAMES = "games"
    TOOLS = "tools"
    ENTERTAINMENT = "entertainment"
    BOOKS = "books"
    SOFTWARE = "software"
    SUBSCRIPTIONS = "subscriptions"
    OTHER = "other"

class BudgetPeriod(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

class TransactionStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    COMPLETED = "completed"
    REFUNDED = "refunded"

@dataclass
class SpendingTransaction:
    """Individual spending transaction"""
    transaction_id: str
    child_id: str
    parent_id: str
    amount: Decimal
    category: SpendingCategory
    description: str
    vendor: Optional[str]
    status: TransactionStatus
    requested_at: datetime
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_notes: Optional[str] = None

@dataclass
class BudgetAllowance:
    """Budget allowance configuration"""
    child_id: str
    category: SpendingCategory
    period: BudgetPeriod
    amount: Decimal
    rollover_enabled: bool = False
    notification_threshold: float = 0.8  # Notify when 80% spent

@dataclass
class SpendingSummary:
    """Spending summary for visualization"""
    period: str
    total_budget: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    percentage_used: float
    transactions_count: int
    category_breakdown: Dict[str, Decimal]

@dataclass
class VisualBudgetData:
    """Data for visual budget display"""
    child_name: str
    age: int
    period_type: BudgetPeriod
    current_period: str
    budgets: List[Dict[str, Any]]
    spending_history: List[Dict[str, Any]]
    achievements: List[str]
    suggestions: List[str]

class SpendingTracker:
    """Main spending tracker service"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        
        # Category colors for visualization
        self.category_colors = {
            SpendingCategory.EDUCATIONAL: "#4CAF50",  # Green
            SpendingCategory.GAMES: "#2196F3",        # Blue
            SpendingCategory.TOOLS: "#FF9800",        # Orange
            SpendingCategory.ENTERTAINMENT: "#9C27B0", # Purple
            SpendingCategory.BOOKS: "#795548",         # Brown
            SpendingCategory.SOFTWARE: "#607D8B",      # Blue Gray
            SpendingCategory.SUBSCRIPTIONS: "#F44336", # Red
            SpendingCategory.OTHER: "#9E9E9E"          # Gray
        }
        
        # Age-appropriate spending tips
        self.spending_tips_by_age = {
            (3, 5): [
                "Ask your parent before buying anything!",
                "Count your coins and dollars!",
                "Books are always a good choice!",
                "Save money for something special!"
            ],
            (6, 8): [
                "Compare prices before buying!",
                "Educational items help you learn!",
                "Save some money for next week!",
                "Think about if you really need it!",
                "Ask yourself: Will I use this often?"
            ],
            (9, 11): [
                "Keep track of your spending!",
                "Educational purchases are investments!",
                "Consider free alternatives first!",
                "Save for bigger, better items!",
                "Read reviews before purchasing!",
                "Think about long-term value!"
            ],
            (12, 14): [
                "Budget for different categories!",
                "Research before making purchases!",
                "Consider subscription costs over time!",
                "Look for student discounts!",
                "Save for emergency expenses!",
                "Track your spending patterns!"
            ],
            (15, 17): [
                "Create a monthly budget plan!",
                "Consider opportunity costs!",
                "Build an emergency fund!",
                "Research investment options!",
                "Track ROI on educational purchases!",
                "Plan for future major expenses!"
            ]
        }
    
    async def create_spending_transaction(self, child_id: str, amount: float, 
                                        category: str, description: str,
                                        vendor: str = None) -> Tuple[str, bool]:
        """Create a new spending transaction"""
        try:
            transaction_id = str(uuid.uuid4())
            amount_decimal = Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Get child profile for parent ID and limits
            async with self.db_pool.acquire() as conn:
                child_profile = await conn.fetchrow('''
                    SELECT parent_id, purchase_limits FROM child_profiles 
                    WHERE child_id = $1 AND is_active = TRUE
                ''', child_id)
                
                if not child_profile:
                    raise ValueError("Child profile not found")
                
                purchase_limits = json.loads(child_profile['purchase_limits'])
                
                # Check if amount requires approval
                requires_approval = (
                    amount_decimal > Decimal(str(purchase_limits['requires_approval_above'])) or
                    amount_decimal > Decimal(str(purchase_limits['single_purchase_limit']))
                )
                
                # Check category restrictions
                if category in purchase_limits.get('blocked_categories', []):
                    raise ValueError(f"Category '{category}' is blocked")
                
                allowed_categories = purchase_limits.get('allowed_categories', [])
                if allowed_categories and category not in allowed_categories:
                    raise ValueError(f"Category '{category}' is not allowed")
                
                # Check spending limits
                spending_check = await self._check_spending_limits(child_id, amount_decimal, category)
                if not spending_check[0]:
                    raise ValueError(spending_check[1])
                
                # Determine initial status
                status = TransactionStatus.PENDING if requires_approval else TransactionStatus.APPROVED
                
                # Create transaction
                await conn.execute('''
                    INSERT INTO spending_transactions 
                    (transaction_id, child_id, parent_id, amount, category, description, 
                     vendor, status, requested_at, approved_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                ''',
                transaction_id, child_id, child_profile['parent_id'],
                amount_decimal, category, description, vendor,
                status.value, datetime.now(),
                datetime.now() if status == TransactionStatus.APPROVED else None
                )
                
                # Log the transaction attempt
                await self._log_spending_activity(child_id, 'transaction_created', {
                    'transaction_id': transaction_id,
                    'amount': float(amount_decimal),
                    'category': category,
                    'requires_approval': requires_approval
                })
                
                # Check if notification is needed
                if not requires_approval:
                    await self._check_spending_notifications(child_id, category)
                
                return transaction_id, requires_approval
                
        except Exception as e:
            logger.error(f"Failed to create spending transaction: {e}")
            raise
    
    async def _check_spending_limits(self, child_id: str, amount: Decimal, 
                                   category: str) -> Tuple[bool, str]:
        """Check if spending is within limits"""
        try:
            # Get current spending for different periods
            now = datetime.now()
            today = now.date()
            week_start = today - timedelta(days=today.weekday())
            month_start = today.replace(day=1)
            
            async with self.db_pool.acquire() as conn:
                # Get child's purchase limits
                limits_row = await conn.fetchrow('''
                    SELECT purchase_limits FROM child_profiles WHERE child_id = $1
                ''', child_id)
                
                if not limits_row:
                    return False, "Child profile not found"
                
                limits = json.loads(limits_row['purchase_limits'])
                
                # Get spending for different periods
                daily_spent = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0) FROM spending_transactions
                    WHERE child_id = $1 AND DATE(requested_at) = $2 
                    AND status IN ('approved', 'completed')
                ''', child_id, today) or Decimal('0')
                
                weekly_spent = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0) FROM spending_transactions
                    WHERE child_id = $1 AND DATE(requested_at) >= $2 
                    AND status IN ('approved', 'completed')
                ''', child_id, week_start) or Decimal('0')
                
                monthly_spent = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0) FROM spending_transactions
                    WHERE child_id = $1 AND DATE(requested_at) >= $2 
                    AND status IN ('approved', 'completed')
                ''', child_id, month_start) or Decimal('0')
                
                # Check limits
                if daily_spent + amount > Decimal(str(limits['daily_limit'])):
                    return False, f"Daily limit of ${limits['daily_limit']:.2f} would be exceeded"
                
                if weekly_spent + amount > Decimal(str(limits['weekly_limit'])):
                    return False, f"Weekly limit of ${limits['weekly_limit']:.2f} would be exceeded"
                
                if monthly_spent + amount > Decimal(str(limits['monthly_limit'])):
                    return False, f"Monthly limit of ${limits['monthly_limit']:.2f} would be exceeded"
                
                return True, "Within limits"
                
        except Exception as e:
            logger.error(f"Failed to check spending limits: {e}")
            return False, "Error checking limits"
    
    async def approve_transaction(self, transaction_id: str, parent_id: str, 
                                notes: str = None) -> bool:
        """Approve a spending transaction"""
        try:
            async with self.db_pool.acquire() as conn:
                # Verify transaction belongs to this parent
                transaction = await conn.fetchrow('''
                    SELECT * FROM spending_transactions 
                    WHERE transaction_id = $1 AND parent_id = $2
                ''', transaction_id, parent_id)
                
                if not transaction:
                    return False
                
                # Update transaction status
                await conn.execute('''
                    UPDATE spending_transactions 
                    SET status = $1, approved_at = $2, parent_notes = $3
                    WHERE transaction_id = $4
                ''', TransactionStatus.APPROVED.value, datetime.now(), notes, transaction_id)
                
                # Log approval
                await self._log_spending_activity(transaction['child_id'], 'transaction_approved', {
                    'transaction_id': transaction_id,
                    'amount': float(transaction['amount']),
                    'parent_notes': notes
                })
                
                # Check spending notifications
                await self._check_spending_notifications(transaction['child_id'], transaction['category'])
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to approve transaction: {e}")
            return False
    
    async def deny_transaction(self, transaction_id: str, parent_id: str, 
                             reason: str = None) -> bool:
        """Deny a spending transaction"""
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute('''
                    UPDATE spending_transactions 
                    SET status = $1, parent_notes = $2
                    WHERE transaction_id = $3 AND parent_id = $4
                ''', TransactionStatus.DENIED.value, reason, transaction_id, parent_id)
                
                if result == 'UPDATE 0':
                    return False
                
                # Get transaction details for logging
                transaction = await conn.fetchrow('''
                    SELECT child_id, amount FROM spending_transactions 
                    WHERE transaction_id = $1
                ''', transaction_id)
                
                # Log denial
                await self._log_spending_activity(transaction['child_id'], 'transaction_denied', {
                    'transaction_id': transaction_id,
                    'amount': float(transaction['amount']),
                    'reason': reason
                })
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to deny transaction: {e}")
            return False
    
    async def get_spending_summary(self, child_id: str, period: BudgetPeriod) -> SpendingSummary:
        """Get spending summary for a child and period"""
        try:
            now = datetime.now()
            
            # Calculate period dates
            if period == BudgetPeriod.DAILY:
                start_date = now.date()
                period_name = start_date.strftime("%Y-%m-%d")
            elif period == BudgetPeriod.WEEKLY:
                start_date = now.date() - timedelta(days=now.weekday())
                end_date = start_date + timedelta(days=6)
                period_name = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            else:  # MONTHLY
                start_date = now.date().replace(day=1)
                period_name = start_date.strftime("%Y-%m")
            
            async with self.db_pool.acquire() as conn:
                # Get budget limits
                limits_row = await conn.fetchrow('''
                    SELECT purchase_limits FROM child_profiles WHERE child_id = $1
                ''', child_id)
                
                if not limits_row:
                    raise ValueError("Child profile not found")
                
                limits = json.loads(limits_row['purchase_limits'])
                
                # Get total budget for period
                if period == BudgetPeriod.DAILY:
                    total_budget = Decimal(str(limits['daily_limit']))
                elif period == BudgetPeriod.WEEKLY:
                    total_budget = Decimal(str(limits['weekly_limit']))
                else:
                    total_budget = Decimal(str(limits['monthly_limit']))
                
                # Get spending data
                if period == BudgetPeriod.DAILY:
                    spending_data = await conn.fetch('''
                        SELECT category, SUM(amount) as spent, COUNT(*) as count
                        FROM spending_transactions 
                        WHERE child_id = $1 AND DATE(requested_at) = $2 
                        AND status IN ('approved', 'completed')
                        GROUP BY category
                    ''', child_id, start_date)
                elif period == BudgetPeriod.WEEKLY:
                    spending_data = await conn.fetch('''
                        SELECT category, SUM(amount) as spent, COUNT(*) as count
                        FROM spending_transactions 
                        WHERE child_id = $1 AND DATE(requested_at) >= $2 
                        AND status IN ('approved', 'completed')
                        GROUP BY category
                    ''', child_id, start_date)
                else:  # MONTHLY
                    spending_data = await conn.fetch('''
                        SELECT category, SUM(amount) as spent, COUNT(*) as count
                        FROM spending_transactions 
                        WHERE child_id = $1 AND DATE(requested_at) >= $2 
                        AND status IN ('approved', 'completed')
                        GROUP BY category
                    ''', child_id, start_date)
                
                # Calculate totals
                spent_amount = sum(Decimal(str(row['spent'])) for row in spending_data)
                remaining_amount = total_budget - spent_amount
                percentage_used = float(spent_amount / total_budget * 100) if total_budget > 0 else 0
                transactions_count = sum(row['count'] for row in spending_data)
                
                # Build category breakdown
                category_breakdown = {
                    row['category']: Decimal(str(row['spent']))
                    for row in spending_data
                }
                
                return SpendingSummary(
                    period=period_name,
                    total_budget=total_budget,
                    spent_amount=spent_amount,
                    remaining_amount=remaining_amount,
                    percentage_used=percentage_used,
                    transactions_count=transactions_count,
                    category_breakdown=category_breakdown
                )
                
        except Exception as e:
            logger.error(f"Failed to get spending summary: {e}")
            raise
    
    async def get_visual_budget_data(self, child_id: str) -> VisualBudgetData:
        """Get data for visual budget display"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get child info
                child_info = await conn.fetchrow('''
                    SELECT name, age FROM child_profiles WHERE child_id = $1
                ''', child_id)
                
                if not child_info:
                    raise ValueError("Child profile not found")
                
                # Get spending summaries for all periods
                daily_summary = await self.get_spending_summary(child_id, BudgetPeriod.DAILY)
                weekly_summary = await self.get_spending_summary(child_id, BudgetPeriod.WEEKLY)
                monthly_summary = await self.get_spending_summary(child_id, BudgetPeriod.MONTHLY)
                
                # Prepare budget data for visualization
                budgets = [
                    {
                        'period': 'Daily',
                        'period_name': daily_summary.period,
                        'total_budget': float(daily_summary.total_budget),
                        'spent_amount': float(daily_summary.spent_amount),
                        'remaining_amount': float(daily_summary.remaining_amount),
                        'percentage_used': daily_summary.percentage_used,
                        'status': self._get_budget_status(daily_summary.percentage_used),
                        'color': self._get_budget_color(daily_summary.percentage_used),
                        'categories': [
                            {
                                'name': category,
                                'amount': float(amount),
                                'color': self.category_colors.get(SpendingCategory(category), '#9E9E9E')
                            }
                            for category, amount in daily_summary.category_breakdown.items()
                        ]
                    },
                    {
                        'period': 'Weekly',
                        'period_name': weekly_summary.period,
                        'total_budget': float(weekly_summary.total_budget),
                        'spent_amount': float(weekly_summary.spent_amount),
                        'remaining_amount': float(weekly_summary.remaining_amount),
                        'percentage_used': weekly_summary.percentage_used,
                        'status': self._get_budget_status(weekly_summary.percentage_used),
                        'color': self._get_budget_color(weekly_summary.percentage_used),
                        'categories': [
                            {
                                'name': category,
                                'amount': float(amount),
                                'color': self.category_colors.get(SpendingCategory(category), '#9E9E9E')
                            }
                            for category, amount in weekly_summary.category_breakdown.items()
                        ]
                    },
                    {
                        'period': 'Monthly',
                        'period_name': monthly_summary.period,
                        'total_budget': float(monthly_summary.total_budget),
                        'spent_amount': float(monthly_summary.spent_amount),
                        'remaining_amount': float(monthly_summary.remaining_amount),
                        'percentage_used': monthly_summary.percentage_used,
                        'status': self._get_budget_status(monthly_summary.percentage_used),
                        'color': self._get_budget_color(monthly_summary.percentage_used),
                        'categories': [
                            {
                                'name': category,
                                'amount': float(amount),
                                'color': self.category_colors.get(SpendingCategory(category), '#9E9E9E')
                            }
                            for category, amount in monthly_summary.category_breakdown.items()
                        ]
                    }
                ]
                
                # Get recent spending history
                spending_history = await self._get_spending_history(child_id, days=30)
                
                # Get achievements
                achievements = await self._get_spending_achievements(child_id)
                
                # Get age-appropriate suggestions
                suggestions = self._get_spending_suggestions(child_info['age'], budgets)
                
                return VisualBudgetData(
                    child_name=child_info['name'],
                    age=child_info['age'],
                    period_type=BudgetPeriod.MONTHLY,  # Default display
                    current_period=monthly_summary.period,
                    budgets=budgets,
                    spending_history=spending_history,
                    achievements=achievements,
                    suggestions=suggestions
                )
                
        except Exception as e:
            logger.error(f"Failed to get visual budget data: {e}")
            raise
    
    def _get_budget_status(self, percentage_used: float) -> str:
        """Get budget status based on usage percentage"""
        if percentage_used <= 50:
            return "Great!"
        elif percentage_used <= 75:
            return "Good"
        elif percentage_used <= 90:
            return "Careful"
        elif percentage_used <= 100:
            return "Almost out"
        else:
            return "Over budget"
    
    def _get_budget_color(self, percentage_used: float) -> str:
        """Get color for budget visualization"""
        if percentage_used <= 50:
            return "#4CAF50"  # Green
        elif percentage_used <= 75:
            return "#FFC107"  # Yellow
        elif percentage_used <= 90:
            return "#FF9800"  # Orange
        else:
            return "#F44336"  # Red
    
    async def _get_spending_history(self, child_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get spending history for visualization"""
        since_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            transactions = await conn.fetch('''
                SELECT DATE(requested_at) as date, 
                       SUM(amount) as daily_total,
                       COUNT(*) as transaction_count
                FROM spending_transactions 
                WHERE child_id = $1 AND requested_at >= $2 
                AND status IN ('approved', 'completed')
                GROUP BY DATE(requested_at)
                ORDER BY DATE(requested_at)
            ''', child_id, since_date)
            
            return [
                {
                    'date': row['date'].isoformat(),
                    'amount': float(row['daily_total']),
                    'transactions': row['transaction_count']
                }
                for row in transactions
            ]
    
    async def _get_spending_achievements(self, child_id: str) -> List[str]:
        """Get spending-related achievements"""
        achievements = []
        
        try:
            async with self.db_pool.acquire() as conn:
                # Check various achievement criteria
                
                # Stayed under budget for a week
                week_start = datetime.now().date() - timedelta(days=7)
                weekly_spending = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0) FROM spending_transactions
                    WHERE child_id = $1 AND DATE(requested_at) >= $2 
                    AND status IN ('approved', 'completed')
                ''', child_id, week_start) or Decimal('0')
                
                limits_row = await conn.fetchrow('''
                    SELECT purchase_limits FROM child_profiles WHERE child_id = $1
                ''', child_id)
                
                if limits_row:
                    limits = json.loads(limits_row['purchase_limits'])
                    weekly_limit = Decimal(str(limits['weekly_limit']))
                    
                    if weekly_spending <= weekly_limit * Decimal('0.8'):
                        achievements.append("🎯 Budget Master - Stayed under 80% of weekly budget!")
                    
                    if weekly_spending <= weekly_limit * Decimal('0.5'):
                        achievements.append("💰 Super Saver - Used less than half your budget!")
                
                # Educational spending achievement
                edu_spending = await conn.fetchval('''
                    SELECT COALESCE(SUM(amount), 0) FROM spending_transactions
                    WHERE child_id = $1 AND category = 'educational'
                    AND DATE(requested_at) >= $2 
                    AND status IN ('approved', 'completed')
                ''', child_id, week_start) or Decimal('0')
                
                if edu_spending > Decimal('0'):
                    achievements.append("📚 Smart Spender - Invested in education!")
                
                # Consecutive days without spending
                no_spending_days = await self._get_consecutive_no_spending_days(child_id)
                if no_spending_days >= 3:
                    achievements.append(f"🏆 {no_spending_days} Day Streak - No spending!")
                
        except Exception as e:
            logger.error(f"Failed to get spending achievements: {e}")
        
        return achievements
    
    async def _get_consecutive_no_spending_days(self, child_id: str) -> int:
        """Get consecutive days without spending"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get recent spending dates
                recent_dates = await conn.fetch('''
                    SELECT DISTINCT DATE(requested_at) as spend_date
                    FROM spending_transactions 
                    WHERE child_id = $1 
                    AND status IN ('approved', 'completed')
                    AND requested_at >= $2
                    ORDER BY spend_date DESC
                ''', child_id, datetime.now() - timedelta(days=30))
                
                if not recent_dates:
                    return 30  # No spending in 30 days
                
                spend_dates = [row['spend_date'] for row in recent_dates]
                today = datetime.now().date()
                
                # Count consecutive days without spending from today backwards
                consecutive_days = 0
                check_date = today
                
                while consecutive_days < 30:  # Max check 30 days
                    if check_date in spend_dates:
                        break
                    consecutive_days += 1
                    check_date -= timedelta(days=1)
                
                return consecutive_days
                
        except Exception as e:
            logger.error(f"Failed to get consecutive no spending days: {e}")
            return 0
    
    def _get_spending_suggestions(self, age: int, budgets: List[Dict[str, Any]]) -> List[str]:
        """Get age-appropriate spending suggestions"""
        suggestions = []
        
        # Get age-appropriate tips
        for age_range, tips in self.spending_tips_by_age.items():
            if age_range[0] <= age <= age_range[1]:
                suggestions.extend(tips[:2])  # Add first 2 tips
                break
        
        # Add budget-specific suggestions
        monthly_budget = next((b for b in budgets if b['period'] == 'Monthly'), None)
        if monthly_budget:
            if monthly_budget['percentage_used'] > 80:
                suggestions.append("You've used most of your budget. Try to save for next month!")
            elif monthly_budget['percentage_used'] < 20:
                suggestions.append("Great job saving! Consider investing in something educational!")
        
        return suggestions[:5]  # Return max 5 suggestions
    
    async def _check_spending_notifications(self, child_id: str, category: str):
        """Check if spending notifications should be sent"""
        try:
            # Get spending summary to check thresholds
            weekly_summary = await self.get_spending_summary(child_id, BudgetPeriod.WEEKLY)
            monthly_summary = await self.get_spending_summary(child_id, BudgetPeriod.MONTHLY)
            
            # Check if approaching limits
            if weekly_summary.percentage_used >= 80:
                await self._send_spending_notification(child_id, 'weekly_limit_warning', {
                    'percentage_used': weekly_summary.percentage_used,
                    'remaining_amount': float(weekly_summary.remaining_amount)
                })
            
            if monthly_summary.percentage_used >= 80:
                await self._send_spending_notification(child_id, 'monthly_limit_warning', {
                    'percentage_used': monthly_summary.percentage_used,
                    'remaining_amount': float(monthly_summary.remaining_amount)
                })
                
        except Exception as e:
            logger.error(f"Failed to check spending notifications: {e}")
    
    async def _send_spending_notification(self, child_id: str, notification_type: str, data: Dict[str, Any]):
        """Send spending notification"""
        # This would integrate with the notification service
        logger.info(f"Spending notification for child {child_id}: {notification_type} - {data}")
    
    async def _log_spending_activity(self, child_id: str, activity_type: str, activity_data: Dict[str, Any]):
        """Log spending activity"""
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute('''
                    INSERT INTO activity_logs 
                    (child_id, activity_type, activity_data, created_at)
                    VALUES ($1, $2, $3, $4)
                ''', child_id, f"spending_{activity_type}", json.dumps(activity_data), datetime.now())
                
        except Exception as e:
            logger.error(f"Failed to log spending activity: {e}")
    
    async def get_pending_transactions(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get pending transactions for parent approval"""
        async with self.db_pool.acquire() as conn:
            transactions = await conn.fetch('''
                SELECT st.*, cp.name as child_name
                FROM spending_transactions st
                JOIN child_profiles cp ON st.child_id = cp.child_id
                WHERE st.parent_id = $1 AND st.status = 'pending'
                ORDER BY st.requested_at DESC
            ''', parent_id)
            
            return [dict(transaction) for transaction in transactions]
    
    async def get_transaction_history(self, child_id: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get transaction history for a child"""
        since_date = datetime.now() - timedelta(days=days)
        
        async with self.db_pool.acquire() as conn:
            transactions = await conn.fetch('''
                SELECT * FROM spending_transactions 
                WHERE child_id = $1 AND requested_at >= $2
                ORDER BY requested_at DESC
            ''', child_id, since_date)
            
            return [dict(transaction) for transaction in transactions]

def main():
    """Example usage"""
    async def test_spending_tracker():
        print("Spending tracker example")
        
        # This would be initialized with actual database connection
        # spending_tracker = SpendingTracker(db_pool)
        
        # Example usage:
        # transaction_id, needs_approval = await spending_tracker.create_spending_transaction(
        #     "child123", 15.99, "educational", "Math learning app", "App Store"
        # )
        
        # visual_data = await spending_tracker.get_visual_budget_data("child123")
        # print(f"Budget status: {visual_data.budgets[0]['status']}")
        
    asyncio.run(test_spending_tracker())

if __name__ == '__main__':
    main()