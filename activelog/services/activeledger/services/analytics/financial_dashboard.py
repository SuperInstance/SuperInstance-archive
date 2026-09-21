"""
Financial Dashboard Service
Provides real-time financial analytics, cost tracking, and credit monitoring
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func, text
import json

from ...models.database import (
    User, Transaction, ComputeInstance, MarketplaceTransaction, 
    AdRevenue, EnterpriseAccount, Subscription, TransactionType, 
    TransactionStatus, SubscriptionTier
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem
from ..exchange.currency_converter import CurrencyConverter

logger = logging.getLogger(__name__)

class FinancialDashboard:
    """Real-time financial dashboard and analytics service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.currency_converter = CurrencyConverter()
    
    async def get_user_financial_overview(self, user_id: str) -> Dict:
        """Get comprehensive financial overview for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get current balance and summary
        balance_summary = await self.cc_system.get_balance_summary(user_id)
        
        # Get spending analysis
        spending_analysis = await self._get_spending_analysis(user_id)
        
        # Get earnings analysis
        earnings_analysis = await self._get_earnings_analysis(user_id)
        
        # Get subscription info
        subscription_info = await self._get_subscription_info(user_id)
        
        # Get cost projections
        cost_projections = await self._get_cost_projections(user_id)
        
        # Get recent activity
        recent_activity = await self._get_recent_activity(user_id)
        
        return {
            "user_id": user_id,
            "snapshot_time": datetime.utcnow().isoformat(),
            "balance_summary": balance_summary,
            "spending_analysis": spending_analysis,
            "earnings_analysis": earnings_analysis,
            "subscription_info": subscription_info,
            "cost_projections": cost_projections,
            "recent_activity": recent_activity,
            "currency_preferences": {
                "preferred_currency": user.preferred_currency,
                "auto_conversion_enabled": hasattr(user, 'auto_conversion_rule') and user.auto_conversion_rule.auto_convert_enabled if user.auto_conversion_rule else False
            }
        }
    
    async def _get_spending_analysis(self, user_id: str) -> Dict:
        """Analyze user spending patterns"""
        
        # Get spending data for last 30, 90, and 365 days
        periods = {
            "last_30_days": 30,
            "last_90_days": 90,
            "last_365_days": 365
        }
        
        spending_by_period = {}
        
        for period_name, days in periods.items():
            start_date = datetime.utcnow() - timedelta(days=days)
            
            spending_data = (
                self.db.query(
                    Transaction.type,
                    func.sum(func.abs(Transaction.amount_cc)).label("total_amount"),
                    func.count(Transaction.id).label("transaction_count")
                )
                .filter(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.type.in_([
                            TransactionType.DEBIT,
                            TransactionType.PAYMENT,
                            TransactionType.ESCROW,
                            TransactionType.SUBSCRIPTION
                        ]),
                        Transaction.status == TransactionStatus.COMPLETED,
                        Transaction.created_at >= start_date
                    )
                )
                .group_by(Transaction.type)
                .all()
            )
            
            total_spent = sum(data.total_amount for data in spending_data)
            
            spending_by_period[period_name] = {
                "total_spent_cc": float(total_spent),
                "average_daily_cc": float(total_spent / days) if days > 0 else 0,
                "transaction_count": sum(data.transaction_count for data in spending_data),
                "breakdown_by_type": {
                    data.type.value: {
                        "amount_cc": float(data.total_amount),
                        "transaction_count": data.transaction_count,
                        "percentage": float((data.total_amount / total_spent * 100)) if total_spent > 0 else 0
                    }
                    for data in spending_data
                }
            }
        
        # Get top spending categories
        top_categories = await self._get_top_spending_categories(user_id)
        
        # Calculate spending trends
        spending_trend = await self._calculate_spending_trend(user_id)
        
        return {
            "periods": spending_by_period,
            "top_categories": top_categories,
            "spending_trend": spending_trend
        }
    
    async def _get_earnings_analysis(self, user_id: str) -> Dict:
        """Analyze user earnings from various sources"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Get ad revenue earnings (if free tier)
        ad_earnings = {}
        if user.subscription_tier == SubscriptionTier.FREE:
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            ad_revenue_data = (
                self.db.query(
                    func.sum(AdRevenue.user_share_cc).label("total_earnings"),
                    func.sum(AdRevenue.impressions).label("total_impressions"),
                    func.sum(AdRevenue.clicks).label("total_clicks")
                )
                .filter(
                    and_(
                        AdRevenue.user_id == user_id,
                        AdRevenue.date >= thirty_days_ago.date()
                    )
                )
                .first()
            )
            
            ad_earnings = {
                "total_earnings_cc": float(ad_revenue_data.total_earnings or 0),
                "total_impressions": int(ad_revenue_data.total_impressions or 0),
                "total_clicks": int(ad_revenue_data.total_clicks or 0),
                "average_daily_cc": float((ad_revenue_data.total_earnings or 0) / 30)
            }
        
        # Get affiliate earnings
        affiliate_earnings = (
            self.db.query(
                func.sum(Transaction.amount_cc).label("total_earnings")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.AFFILIATE_COMMISSION,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Get marketplace earnings
        marketplace_earnings = (
            self.db.query(
                func.sum(Transaction.amount_cc).label("total_earnings")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type == TransactionType.MARKETPLACE_SALE,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Get refunds and credits
        credits_refunds = (
            self.db.query(
                func.sum(Transaction.amount_cc).label("total_amount")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([TransactionType.REFUND, TransactionType.CREDIT]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= datetime.utcnow() - timedelta(days=30)
                )
            )
            .scalar() or Decimal("0")
        )
        
        total_earnings = (
            (ad_earnings.get("total_earnings_cc", 0) if ad_earnings else 0) +
            float(affiliate_earnings) +
            float(marketplace_earnings) +
            float(credits_refunds)
        )
        
        return {
            "last_30_days": {
                "total_earnings_cc": total_earnings,
                "ad_revenue": ad_earnings,
                "affiliate_earnings_cc": float(affiliate_earnings),
                "marketplace_earnings_cc": float(marketplace_earnings),
                "credits_refunds_cc": float(credits_refunds)
            },
            "projected_monthly": {
                "total_cc": total_earnings,  # Already 30-day data
                "ad_revenue_cc": ad_earnings.get("total_earnings_cc", 0) if ad_earnings else 0,
                "affiliate_cc": float(affiliate_earnings),
                "marketplace_cc": float(marketplace_earnings)
            }
        }
    
    async def _get_subscription_info(self, user_id: str) -> Dict:
        """Get subscription information and costs"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        
        # Get current subscription
        current_subscription = (
            self.db.query(Subscription)
            .filter(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == "active"
                )
            )
            .first()
        )
        
        subscription_costs = {}
        if current_subscription:
            # Calculate subscription costs
            days_in_current_cycle = (current_subscription.billing_cycle_end - current_subscription.billing_cycle_start).days
            days_used = (datetime.utcnow() - current_subscription.billing_cycle_start).days
            
            subscription_costs = {
                "current_tier": current_subscription.tier.value,
                "monthly_cost_cc": float(current_subscription.monthly_cost_cc),
                "current_cycle": {
                    "start": current_subscription.billing_cycle_start.isoformat(),
                    "end": current_subscription.billing_cycle_end.isoformat(),
                    "days_total": days_in_current_cycle,
                    "days_used": min(days_used, days_in_current_cycle),
                    "days_remaining": max(0, days_in_current_cycle - days_used),
                    "cost_used_cc": float(
                        current_subscription.monthly_cost_cc * 
                        min(days_used, days_in_current_cycle) / days_in_current_cycle
                    )
                },
                "next_billing": current_subscription.next_billing_date.isoformat() if current_subscription.next_billing_date else None
            }
        else:
            subscription_costs = {
                "current_tier": user.subscription_tier.value if user.subscription_tier else "free",
                "monthly_cost_cc": 0,
                "current_cycle": None,
                "next_billing": None
            }
        
        return subscription_costs
    
    async def _get_cost_projections(self, user_id: str) -> Dict:
        """Calculate cost projections based on usage patterns"""
        
        # Get usage data for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Average daily spending
        avg_daily_spending = (
            self.db.query(
                func.avg(
                    func.abs(Transaction.amount_cc)
                ).label("avg_daily")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([
                        TransactionType.DEBIT,
                        TransactionType.PAYMENT,
                        TransactionType.SUBSCRIPTION
                    ]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Project future costs
        projections = {
            "next_7_days": float(avg_daily_spending * 7),
            "next_30_days": float(avg_daily_spending * 30),
            "next_90_days": float(avg_daily_spending * 90),
            "next_365_days": float(avg_daily_spending * 365)
        }
        
        # Add subscription costs if applicable
        subscription = await self._get_subscription_info(user_id)
        if subscription.get("monthly_cost_cc", 0) > 0:
            monthly_sub_cost = subscription["monthly_cost_cc"]
            projections["next_30_days"] += monthly_sub_cost
            projections["next_90_days"] += monthly_sub_cost * 3
            projections["next_365_days"] += monthly_sub_cost * 12
        
        return {
            "projections_cc": projections,
            "based_on_avg_daily_cc": float(avg_daily_spending),
            "confidence_level": "medium" if avg_daily_spending > 0 else "low"
        }
    
    async def _get_recent_activity(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get recent financial activity"""
        
        recent_transactions = (
            self.db.query(Transaction)
            .filter(Transaction.user_id == user_id)
            .order_by(desc(Transaction.created_at))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "transaction_id": tx.id,
                "type": tx.type.value,
                "amount_cc": float(tx.amount_cc),
                "description": tx.description,
                "status": tx.status.value,
                "created_at": tx.created_at.isoformat(),
                "metadata": tx.metadata or {}
            }
            for tx in recent_transactions
        ]
    
    async def _get_top_spending_categories(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get top spending categories for the user"""
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Group by transaction type for basic categorization
        category_spending = (
            self.db.query(
                Transaction.type,
                func.sum(func.abs(Transaction.amount_cc)).label("total_spent"),
                func.count(Transaction.id).label("transaction_count")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([
                        TransactionType.DEBIT,
                        TransactionType.PAYMENT,
                        TransactionType.SUBSCRIPTION,
                        TransactionType.ESCROW
                    ]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .group_by(Transaction.type)
            .order_by(desc("total_spent"))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "category": category.type.value,
                "amount_cc": float(category.total_spent),
                "transaction_count": category.transaction_count,
                "average_per_transaction_cc": float(category.total_spent / category.transaction_count)
            }
            for category in category_spending
        ]
    
    async def _calculate_spending_trend(self, user_id: str) -> Dict:
        """Calculate spending trend over time"""
        
        # Compare last 30 days vs previous 30 days
        now = datetime.utcnow()
        last_30_days = now - timedelta(days=30)
        previous_30_days = now - timedelta(days=60)
        
        current_period_spending = (
            self.db.query(
                func.sum(func.abs(Transaction.amount_cc)).label("total")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([TransactionType.DEBIT, TransactionType.PAYMENT]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= last_30_days
                )
            )
            .scalar() or Decimal("0")
        )
        
        previous_period_spending = (
            self.db.query(
                func.sum(func.abs(Transaction.amount_cc)).label("total")
            )
            .filter(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type.in_([TransactionType.DEBIT, TransactionType.PAYMENT]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= previous_30_days,
                    Transaction.created_at < last_30_days
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Calculate trend
        if previous_period_spending > 0:
            change_percentage = float(
                (current_period_spending - previous_period_spending) / previous_period_spending * 100
            )
        else:
            change_percentage = 100.0 if current_period_spending > 0 else 0.0
        
        trend = "increasing" if change_percentage > 5 else "decreasing" if change_percentage < -5 else "stable"
        
        return {
            "current_period_cc": float(current_period_spending),
            "previous_period_cc": float(previous_period_spending),
            "change_percentage": change_percentage,
            "trend": trend
        }
    
    async def get_platform_financial_analytics(self, admin_id: str) -> Dict:
        """Get platform-wide financial analytics for administrators"""
        
        # Verify admin access (implement your admin verification logic)
        # For now, we'll proceed with the analytics
        
        # Get overall platform metrics
        platform_metrics = await self._get_platform_metrics()
        
        # Get revenue breakdown
        revenue_breakdown = await self._get_revenue_breakdown()
        
        # Get user tier distribution
        user_distribution = await self._get_user_tier_distribution()
        
        # Get transaction volume trends
        volume_trends = await self._get_transaction_volume_trends()
        
        # Get top users by spending
        top_spenders = await self._get_top_spenders()
        
        return {
            "snapshot_time": datetime.utcnow().isoformat(),
            "platform_metrics": platform_metrics,
            "revenue_breakdown": revenue_breakdown,
            "user_distribution": user_distribution,
            "volume_trends": volume_trends,
            "top_spenders": top_spenders
        }
    
    async def _get_platform_metrics(self) -> Dict:
        """Get overall platform financial metrics"""
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Total platform balance
        total_cc_in_circulation = (
            self.db.query(func.sum(User.cc_balance))
            .filter(User.cc_balance > 0)
            .scalar() or Decimal("0")
        )
        
        # Total transactions last 30 days
        recent_transaction_volume = (
            self.db.query(
                func.count(Transaction.id).label("count"),
                func.sum(func.abs(Transaction.amount_cc)).label("volume")
            )
            .filter(
                and_(
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .first()
        )
        
        # Active users (users with transactions in last 30 days)
        active_users = (
            self.db.query(func.count(func.distinct(Transaction.user_id)))
            .filter(Transaction.created_at >= thirty_days_ago)
            .scalar() or 0
        )
        
        return {
            "total_cc_in_circulation": float(total_cc_in_circulation),
            "total_users": self.db.query(func.count(User.id)).scalar() or 0,
            "active_users_30d": active_users,
            "transaction_volume_30d": {
                "count": recent_transaction_volume.count or 0,
                "volume_cc": float(recent_transaction_volume.volume or 0)
            }
        }
    
    async def _get_revenue_breakdown(self) -> Dict:
        """Get platform revenue breakdown by source"""
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        # Subscription revenue
        subscription_revenue = (
            self.db.query(
                func.sum(func.abs(Transaction.amount_cc)).label("total")
            )
            .filter(
                and_(
                    Transaction.type == TransactionType.SUBSCRIPTION,
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Marketplace platform fees
        marketplace_fees = (
            self.db.query(
                func.sum(MarketplaceTransaction.platform_fee_cc).label("total")
            )
            .filter(
                and_(
                    MarketplaceTransaction.status == "completed",
                    MarketplaceTransaction.created_at >= thirty_days_ago
                )
            )
            .scalar() or Decimal("0")
        )
        
        # Ad revenue platform share (10%)
        ad_platform_revenue = (
            self.db.query(
                func.sum(AdRevenue.platform_share_cc).label("total")
            )
            .filter(AdRevenue.date >= thirty_days_ago.date())
            .scalar() or Decimal("0")
        )
        
        # Currency conversion fees
        conversion_fees = (
            self.db.query(
                func.sum(Transaction.amount_cc).label("total")
            )
            .filter(
                and_(
                    Transaction.type == TransactionType.CURRENCY_CONVERSION,
                    Transaction.description.like("%fee%"),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .scalar() or Decimal("0")
        )
        
        total_revenue = subscription_revenue + marketplace_fees + ad_platform_revenue + conversion_fees
        
        return {
            "total_revenue_30d_cc": float(total_revenue),
            "breakdown": {
                "subscriptions_cc": float(subscription_revenue),
                "marketplace_fees_cc": float(marketplace_fees),
                "ad_revenue_share_cc": float(ad_platform_revenue),
                "conversion_fees_cc": float(conversion_fees)
            },
            "percentage_breakdown": {
                "subscriptions": float(subscription_revenue / total_revenue * 100) if total_revenue > 0 else 0,
                "marketplace_fees": float(marketplace_fees / total_revenue * 100) if total_revenue > 0 else 0,
                "ad_revenue_share": float(ad_platform_revenue / total_revenue * 100) if total_revenue > 0 else 0,
                "conversion_fees": float(conversion_fees / total_revenue * 100) if total_revenue > 0 else 0
            }
        }
    
    async def _get_user_tier_distribution(self) -> Dict:
        """Get distribution of users by subscription tier"""
        
        tier_distribution = (
            self.db.query(
                User.subscription_tier,
                func.count(User.id).label("count")
            )
            .group_by(User.subscription_tier)
            .all()
        )
        
        total_users = sum(tier.count for tier in tier_distribution)
        
        return {
            "total_users": total_users,
            "distribution": {
                tier.subscription_tier.value if tier.subscription_tier else "free": {
                    "count": tier.count,
                    "percentage": float(tier.count / total_users * 100) if total_users > 0 else 0
                }
                for tier in tier_distribution
            }
        }
    
    async def _get_transaction_volume_trends(self) -> Dict:
        """Get transaction volume trends over time"""
        
        # Get daily transaction volumes for last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        daily_volumes = (
            self.db.query(
                func.date(Transaction.created_at).label("date"),
                func.count(Transaction.id).label("count"),
                func.sum(func.abs(Transaction.amount_cc)).label("volume")
            )
            .filter(
                and_(
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .group_by(func.date(Transaction.created_at))
            .order_by(func.date(Transaction.created_at))
            .all()
        )
        
        return {
            "period_days": 30,
            "daily_data": [
                {
                    "date": day.date.isoformat(),
                    "transaction_count": day.count,
                    "volume_cc": float(day.volume or 0)
                }
                for day in daily_volumes
            ]
        }
    
    async def _get_top_spenders(self, limit: int = 10) -> List[Dict]:
        """Get top spending users (anonymized)"""
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        
        top_spenders = (
            self.db.query(
                Transaction.user_id,
                func.sum(func.abs(Transaction.amount_cc)).label("total_spent")
            )
            .filter(
                and_(
                    Transaction.type.in_([TransactionType.DEBIT, TransactionType.PAYMENT]),
                    Transaction.status == TransactionStatus.COMPLETED,
                    Transaction.created_at >= thirty_days_ago
                )
            )
            .group_by(Transaction.user_id)
            .order_by(desc("total_spent"))
            .limit(limit)
            .all()
        )
        
        return [
            {
                "user_id_hash": f"user_{hash(spender.user_id) % 100000:05d}",  # Anonymized
                "total_spent_cc": float(spender.total_spent),
                "rank": idx + 1
            }
            for idx, spender in enumerate(top_spenders)
        ]
    
    async def get_real_time_metrics(self, user_id: Optional[str] = None) -> Dict:
        """Get real-time financial metrics"""
        
        current_time = datetime.utcnow()
        
        if user_id:
            # User-specific real-time metrics
            current_balance = await self.cc_system.get_user_balance(user_id)
            
            # Recent transactions (last 24 hours)
            yesterday = current_time - timedelta(days=1)
            recent_activity = (
                self.db.query(
                    func.count(Transaction.id).label("count"),
                    func.sum(func.abs(Transaction.amount_cc)).label("volume")
                )
                .filter(
                    and_(
                        Transaction.user_id == user_id,
                        Transaction.created_at >= yesterday,
                        Transaction.status == TransactionStatus.COMPLETED
                    )
                )
                .first()
            )
            
            return {
                "user_id": user_id,
                "timestamp": current_time.isoformat(),
                "current_balance_cc": float(current_balance),
                "last_24h": {
                    "transaction_count": recent_activity.count or 0,
                    "volume_cc": float(recent_activity.volume or 0)
                }
            }
        
        else:
            # Platform-wide real-time metrics
            total_platform_balance = (
                self.db.query(func.sum(User.cc_balance))
                .scalar() or Decimal("0")
            )
            
            # Active users in last hour
            last_hour = current_time - timedelta(hours=1)
            active_last_hour = (
                self.db.query(func.count(func.distinct(Transaction.user_id)))
                .filter(Transaction.created_at >= last_hour)
                .scalar() or 0
            )
            
            return {
                "platform": "activeledger",
                "timestamp": current_time.isoformat(),
                "total_cc_circulation": float(total_platform_balance),
                "active_users_last_hour": active_last_hour
            }