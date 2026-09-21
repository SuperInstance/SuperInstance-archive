"""
Ad Revenue Tracking and Distribution System
Tracks ad performance and distributes 90% of revenue to free tier users
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.database import (
    User, AdRevenue, Transaction, SubscriptionTier, TransactionType, TransactionStatus
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class AdRevenueManager:
    """Manages ad revenue tracking and distribution for free tier users"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        self.user_revenue_share = settings.ad_revenue.user_share_percentage
        self.platform_revenue_share = settings.ad_revenue.platform_share_percentage
        self.min_payout_threshold_cc = settings.ad_revenue.min_payout_threshold_cc
        
    async def record_ad_impression(
        self,
        user_id: str,
        ad_network: str,
        ad_unit_id: str,
        revenue_usd: Decimal = Decimal("0")
    ) -> AdRevenue:
        """Record an ad impression for a user"""
        
        # Verify user is on free tier
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.subscription_tier != SubscriptionTier.FREE:
            raise ValueError("Ad revenue only applies to free tier users")
        
        # Get or create today's ad revenue record
        today = datetime.utcnow().date()
        ad_revenue = (
            self.db.query(AdRevenue)
            .filter(
                and_(
                    AdRevenue.user_id == user_id,
                    AdRevenue.ad_network == ad_network,
                    AdRevenue.ad_unit_id == ad_unit_id,
                    func.date(AdRevenue.date) == today
                )
            )
            .first()
        )
        
        if not ad_revenue:
            ad_revenue = AdRevenue(
                user_id=user_id,
                ad_network=ad_network,
                ad_unit_id=ad_unit_id,
                date=datetime.utcnow()
            )
            self.db.add(ad_revenue)
        
        # Update impression count and revenue
        ad_revenue.impressions += 1
        if revenue_usd > 0:
            ad_revenue.revenue_usd += revenue_usd
            
            # Convert to CC
            revenue_cc = await self.cc_system.convert_to_cc(revenue_usd, "USD")
            ad_revenue.revenue_cc += revenue_cc
            
            # Calculate user and platform shares
            user_share = revenue_cc * (self.user_revenue_share / 100)
            platform_share = revenue_cc * (self.platform_revenue_share / 100)
            
            ad_revenue.user_share_cc += user_share
            ad_revenue.platform_share_cc += platform_share
        
        self.db.commit()
        
        logger.info(f"Recorded ad impression for user {user_id}: {ad_network}/{ad_unit_id}")
        return ad_revenue
    
    async def record_ad_click(
        self,
        user_id: str,
        ad_network: str,
        ad_unit_id: str,
        revenue_usd: Decimal
    ) -> AdRevenue:
        """Record an ad click for a user"""
        
        # Verify user is on free tier
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.subscription_tier != SubscriptionTier.FREE:
            raise ValueError("Ad revenue only applies to free tier users")
        
        # Get or create today's ad revenue record
        today = datetime.utcnow().date()
        ad_revenue = (
            self.db.query(AdRevenue)
            .filter(
                and_(
                    AdRevenue.user_id == user_id,
                    AdRevenue.ad_network == ad_network,
                    AdRevenue.ad_unit_id == ad_unit_id,
                    func.date(AdRevenue.date) == today
                )
            )
            .first()
        )
        
        if not ad_revenue:
            ad_revenue = AdRevenue(
                user_id=user_id,
                ad_network=ad_network,
                ad_unit_id=ad_unit_id,
                date=datetime.utcnow()
            )
            self.db.add(ad_revenue)
        
        # Update click count and revenue
        ad_revenue.clicks += 1
        ad_revenue.revenue_usd += revenue_usd
        
        # Convert to CC
        revenue_cc = await self.cc_system.convert_to_cc(revenue_usd, "USD")
        ad_revenue.revenue_cc += revenue_cc
        
        # Calculate user and platform shares
        user_share = revenue_cc * (self.user_revenue_share / 100)
        platform_share = revenue_cc * (self.platform_revenue_share / 100)
        
        ad_revenue.user_share_cc += user_share
        ad_revenue.platform_share_cc += platform_share
        
        self.db.commit()
        
        logger.info(f"Recorded ad click for user {user_id}: {ad_network}/{ad_unit_id} - {revenue_usd} USD")
        return ad_revenue
    
    async def process_daily_payouts(self, date: Optional[datetime] = None) -> Dict[str, int]:
        """Process daily ad revenue payouts to users"""
        
        if not date:
            date = datetime.utcnow().date()
        
        # Get all ad revenue for the date that hasn't been paid out yet
        ad_revenues = (
            self.db.query(AdRevenue)
            .filter(
                and_(
                    func.date(AdRevenue.date) == date,
                    AdRevenue.user_share_cc >= self.min_payout_threshold_cc
                )
            )
            .all()
        )
        
        results = {"processed": 0, "failed": 0, "total_cc_distributed": Decimal("0")}
        
        for ad_revenue in ad_revenues:
            try:
                # Check if user still exists and is on free tier
                user = self.db.query(User).filter(User.id == ad_revenue.user_id).first()
                if not user or user.subscription_tier != SubscriptionTier.FREE:
                    continue
                
                # Award CC credits to user
                await self.cc_system.add_credits(
                    ad_revenue.user_id,
                    ad_revenue.user_share_cc,
                    TransactionType.AD_REVENUE,
                    f"Daily ad revenue payout for {date}",
                    metadata={
                        "ad_network": ad_revenue.ad_network,
                        "ad_unit_id": ad_revenue.ad_unit_id,
                        "impressions": ad_revenue.impressions,
                        "clicks": ad_revenue.clicks,
                        "revenue_usd": str(ad_revenue.revenue_usd),
                        "user_share_percentage": self.user_revenue_share,
                        "payout_date": date.isoformat()
                    }
                )
                
                results["processed"] += 1
                results["total_cc_distributed"] += ad_revenue.user_share_cc
                
                logger.info(
                    f"Paid out {ad_revenue.user_share_cc} CC to user {ad_revenue.user_id} "
                    f"for ad revenue on {date}"
                )
                
            except Exception as e:
                logger.error(f"Failed to process payout for user {ad_revenue.user_id}: {str(e)}")
                results["failed"] += 1
        
        logger.info(f"Daily ad revenue payout completed for {date}: {results}")
        return results
    
    async def get_user_ad_stats(
        self,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get ad revenue statistics for a user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        query = self.db.query(AdRevenue).filter(
            and_(
                AdRevenue.user_id == user_id,
                AdRevenue.date >= start_date,
                AdRevenue.date <= end_date
            )
        )
        
        ad_revenues = query.all()
        
        # Aggregate statistics
        total_impressions = sum(ar.impressions for ar in ad_revenues)
        total_clicks = sum(ar.clicks for ar in ad_revenues)
        total_revenue_usd = sum(ar.revenue_usd for ar in ad_revenues)
        total_revenue_cc = sum(ar.revenue_cc for ar in ad_revenues)
        total_user_share_cc = sum(ar.user_share_cc for ar in ad_revenues)
        
        # Calculate CTR (Click Through Rate)
        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Calculate average revenue per impression (RPM)
        rpm_usd = (total_revenue_usd / total_impressions * 1000) if total_impressions > 0 else 0
        
        # Get daily breakdown
        daily_stats = []
        for ar in ad_revenues:
            daily_stats.append({
                "date": ar.date.date().isoformat(),
                "ad_network": ar.ad_network,
                "impressions": ar.impressions,
                "clicks": ar.clicks,
                "revenue_usd": float(ar.revenue_usd),
                "user_share_cc": float(ar.user_share_cc),
                "ctr": (ar.clicks / ar.impressions * 100) if ar.impressions > 0 else 0
            })
        
        return {
            "user_id": user_id,
            "period": {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat()
            },
            "totals": {
                "impressions": total_impressions,
                "clicks": total_clicks,
                "revenue_usd": float(total_revenue_usd),
                "revenue_cc": float(total_revenue_cc),
                "user_share_cc": float(total_user_share_cc),
                "ctr_percentage": float(ctr),
                "rpm_usd": float(rpm_usd)
            },
            "daily_breakdown": daily_stats,
            "revenue_sharing": {
                "user_share_percentage": self.user_revenue_share,
                "platform_share_percentage": self.platform_revenue_share,
                "min_payout_threshold_cc": float(self.min_payout_threshold_cc)
            }
        }
    
    async def get_platform_ad_analytics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """Get platform-wide ad revenue analytics"""
        
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Aggregate platform statistics
        platform_stats = (
            self.db.query(
                func.sum(AdRevenue.impressions).label("total_impressions"),
                func.sum(AdRevenue.clicks).label("total_clicks"),
                func.sum(AdRevenue.revenue_usd).label("total_revenue_usd"),
                func.sum(AdRevenue.revenue_cc).label("total_revenue_cc"),
                func.sum(AdRevenue.user_share_cc).label("total_user_share_cc"),
                func.sum(AdRevenue.platform_share_cc).label("total_platform_share_cc"),
                func.count(func.distinct(AdRevenue.user_id)).label("active_users")
            )
            .filter(
                and_(
                    AdRevenue.date >= start_date,
                    AdRevenue.date <= end_date
                )
            )
            .first()
        )
        
        # Get network breakdown
        network_stats = (
            self.db.query(
                AdRevenue.ad_network,
                func.sum(AdRevenue.impressions).label("impressions"),
                func.sum(AdRevenue.clicks).label("clicks"),
                func.sum(AdRevenue.revenue_usd).label("revenue_usd"),
                func.sum(AdRevenue.user_share_cc).label("user_share_cc")
            )
            .filter(
                and_(
                    AdRevenue.date >= start_date,
                    AdRevenue.date <= end_date
                )
            )
            .group_by(AdRevenue.ad_network)
            .all()
        )
        
        # Calculate overall CTR
        total_impressions = platform_stats.total_impressions or 0
        total_clicks = platform_stats.total_clicks or 0
        overall_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        
        # Calculate RPM
        total_revenue_usd = platform_stats.total_revenue_usd or Decimal("0")
        rpm_usd = (total_revenue_usd / total_impressions * 1000) if total_impressions > 0 else 0
        
        return {
            "period": {
                "start_date": start_date.date().isoformat(),
                "end_date": end_date.date().isoformat()
            },
            "platform_totals": {
                "impressions": total_impressions,
                "clicks": total_clicks,
                "revenue_usd": float(total_revenue_usd),
                "revenue_cc": float(platform_stats.total_revenue_cc or 0),
                "user_share_cc": float(platform_stats.total_user_share_cc or 0),
                "platform_share_cc": float(platform_stats.total_platform_share_cc or 0),
                "active_users": platform_stats.active_users or 0,
                "ctr_percentage": float(overall_ctr),
                "rpm_usd": float(rpm_usd)
            },
            "network_breakdown": [
                {
                    "ad_network": network.ad_network,
                    "impressions": network.impressions,
                    "clicks": network.clicks,
                    "revenue_usd": float(network.revenue_usd),
                    "user_share_cc": float(network.user_share_cc),
                    "ctr_percentage": (network.clicks / network.impressions * 100) if network.impressions > 0 else 0
                }
                for network in network_stats
            ]
        }
    
    async def simulate_ad_revenue(
        self,
        user_id: str,
        impressions: int,
        click_rate: float = 0.02,
        rpm_usd: float = 2.50
    ) -> Dict:
        """Simulate ad revenue for testing and projections"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if user.subscription_tier != SubscriptionTier.FREE:
            raise ValueError("Ad revenue simulation only applies to free tier users")
        
        # Calculate clicks and revenue
        clicks = int(impressions * click_rate)
        revenue_usd = Decimal(str(impressions * rpm_usd / 1000))
        
        # Convert to CC
        revenue_cc = await self.cc_system.convert_to_cc(revenue_usd, "USD")
        
        # Calculate user share
        user_share_cc = revenue_cc * (self.user_revenue_share / 100)
        platform_share_cc = revenue_cc * (self.platform_revenue_share / 100)
        
        return {
            "simulation_parameters": {
                "impressions": impressions,
                "click_rate_percentage": click_rate * 100,
                "rpm_usd": rpm_usd
            },
            "projected_results": {
                "clicks": clicks,
                "revenue_usd": float(revenue_usd),
                "revenue_cc": float(revenue_cc),
                "user_share_cc": float(user_share_cc),
                "platform_share_cc": float(platform_share_cc)
            },
            "monthly_projection": {
                "impressions": impressions * 30,
                "clicks": clicks * 30,
                "revenue_usd": float(revenue_usd * 30),
                "user_earnings_cc": float(user_share_cc * 30)
            }
        }