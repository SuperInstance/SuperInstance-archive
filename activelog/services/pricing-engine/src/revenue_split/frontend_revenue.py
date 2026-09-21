from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from ..database import (
    RevenueShare, User, ComputeCost, PricingTier,
    ComputeLocation, ResourceType
)

logger = logging.getLogger(__name__)

class FrontendRevenueManager:
    """Manage frontend owner revenue split ($1 to frontend, $1 to ActiveLog)"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.frontend_split = Decimal('1.0')    # $1 to frontend owner
        self.activelog_split = Decimal('1.0')   # $1 to ActiveLog
        self.minimum_transaction = Decimal('2.0')  # Minimum $2 transaction for split
    
    async def process_revenue_split(
        self,
        user_id: uuid.UUID,
        frontend_id: str,
        transaction_amount: Decimal,
        transaction_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process revenue split for a frontend transaction"""
        
        try:
            # Validate minimum transaction amount
            if transaction_amount < self.minimum_transaction:
                return {
                    "processed": False,
                    "reason": f"Transaction amount ${transaction_amount} below minimum ${self.minimum_transaction}",
                    "transaction_id": transaction_id
                }
            
            # Get frontend owner information
            frontend_owner = await self._get_frontend_owner(frontend_id)
            if not frontend_owner:
                return {
                    "processed": False,
                    "reason": f"Frontend owner not found for frontend_id: {frontend_id}",
                    "transaction_id": transaction_id
                }
            
            # Calculate split amounts
            split_calculation = await self._calculate_split_amounts(
                transaction_amount, frontend_id, user_id
            )
            
            # Create revenue share record
            revenue_share = RevenueShare(
                user_id=user_id,
                frontend_id=frontend_id,
                transaction_id=transaction_id or str(uuid.uuid4()),
                total_amount=transaction_amount,
                frontend_share=split_calculation['frontend_amount'],
                activelog_share=split_calculation['activelog_amount'],
                metadata={
                    "frontend_owner_id": str(frontend_owner.id),
                    "split_method": split_calculation['method'],
                    "bonus_applied": split_calculation.get('bonus_applied', False),
                    "user_tier": frontend_owner.membership_tier.value,
                    **(metadata or {})
                }
            )
            
            self.db.add(revenue_share)
            await self.db.commit()
            await self.db.refresh(revenue_share)
            
            # Update frontend owner statistics
            await self._update_frontend_owner_stats(frontend_owner.id, split_calculation['frontend_amount'])
            
            # Process payouts if threshold reached
            payout_status = await self._check_payout_threshold(frontend_owner.id, frontend_id)
            
            return {
                "processed": True,
                "revenue_share_id": str(revenue_share.id),
                "split_breakdown": {
                    "total_amount": float(transaction_amount),
                    "frontend_share": float(split_calculation['frontend_amount']),
                    "activelog_share": float(split_calculation['activelog_amount']),
                    "frontend_owner_id": str(frontend_owner.id),
                    "split_percentage": {
                        "frontend": float((split_calculation['frontend_amount'] / transaction_amount) * 100),
                        "activelog": float((split_calculation['activelog_amount'] / transaction_amount) * 100)
                    }
                },
                "payout_status": payout_status,
                "processing_timestamp": revenue_share.revenue_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process revenue split: {e}")
            raise
    
    async def get_frontend_revenue_summary(
        self,
        frontend_id: str,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get revenue summary for a specific frontend"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get all revenue shares for this frontend
            result = await self.db.execute(
                select(RevenueShare).where(
                    and_(
                        RevenueShare.frontend_id == frontend_id,
                        RevenueShare.revenue_date >= start_date
                    )
                ).order_by(RevenueShare.revenue_date.desc())
            )
            revenue_records = result.scalars().all()
            
            if not revenue_records:
                return {
                    "frontend_id": frontend_id,
                    "period_days": period_days,
                    "message": "No revenue data found for this period"
                }
            
            # Calculate totals
            total_transactions = len(revenue_records)
            total_revenue = sum(record.total_amount for record in revenue_records)
            total_frontend_share = sum(record.frontend_share for record in revenue_records)
            total_activelog_share = sum(record.activelog_share for record in revenue_records)
            
            # Daily revenue breakdown
            daily_revenue = {}
            for record in revenue_records:
                day = record.revenue_date.date().isoformat()
                if day not in daily_revenue:
                    daily_revenue[day] = {
                        "total": Decimal('0'),
                        "frontend_share": Decimal('0'),
                        "transactions": 0
                    }
                daily_revenue[day]['total'] += record.total_amount
                daily_revenue[day]['frontend_share'] += record.frontend_share
                daily_revenue[day]['transactions'] += 1
            
            # Top users by revenue
            user_revenue = {}
            for record in revenue_records:
                user_id_str = str(record.user_id)
                if user_id_str not in user_revenue:
                    user_revenue[user_id_str] = Decimal('0')
                user_revenue[user_id_str] += record.total_amount
            
            top_users = sorted(user_revenue.items(), key=lambda x: x[1], reverse=True)[:10]
            
            # Growth metrics
            if period_days >= 14:
                first_half = revenue_records[len(revenue_records)//2:]
                second_half = revenue_records[:len(revenue_records)//2]
                
                first_half_avg = sum(r.total_amount for r in first_half) / len(first_half) if first_half else 0
                second_half_avg = sum(r.total_amount for r in second_half) / len(second_half) if second_half else 0
                
                growth_rate = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
            else:
                growth_rate = 0
            
            # Convert decimals for JSON serialization
            daily_revenue_serializable = {}
            for day, data in daily_revenue.items():
                daily_revenue_serializable[day] = {
                    "total": float(data['total']),
                    "frontend_share": float(data['frontend_share']),
                    "transactions": data['transactions']
                }
            
            return {
                "frontend_id": frontend_id,
                "period_days": period_days,
                "revenue_summary": {
                    "total_transactions": total_transactions,
                    "total_revenue": float(total_revenue),
                    "frontend_owner_earnings": float(total_frontend_share),
                    "activelog_earnings": float(total_activelog_share),
                    "average_transaction_value": float(total_revenue / total_transactions) if total_transactions > 0 else 0,
                    "average_daily_revenue": float(total_revenue / period_days),
                    "growth_rate_percentage": float(growth_rate)
                },
                "daily_breakdown": daily_revenue_serializable,
                "top_revenue_users": [
                    {"user_id": user_id, "revenue": float(revenue)} 
                    for user_id, revenue in top_users
                ],
                "performance_metrics": await self._calculate_frontend_performance_metrics(
                    frontend_id, revenue_records
                ),
                "payout_status": await self._get_payout_status(frontend_id),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get frontend revenue summary: {e}")
            raise
    
    async def get_frontend_owner_dashboard(
        self,
        owner_user_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive dashboard for frontend owner"""
        
        try:
            # Get all frontends owned by this user
            result = await self.db.execute(
                select(User).where(User.id == owner_user_id)
            )
            owner = result.scalar_one_or_none()
            
            if not owner or not owner.is_frontend_owner:
                return {
                    "error": "User is not a frontend owner",
                    "user_id": str(owner_user_id)
                }
            
            # Get revenue data for all owned frontends
            owned_frontends = await self._get_owned_frontends(owner_user_id)
            
            dashboard_data = {
                "owner_id": str(owner_user_id),
                "owner_email": owner.email,
                "owner_tier": owner.membership_tier.value,
                "total_frontends": len(owned_frontends),
                "period_days": period_days,
                "aggregate_metrics": {},
                "frontend_performance": [],
                "earnings_forecast": {},
                "optimization_recommendations": []
            }
            
            # Aggregate metrics across all frontends
            total_earnings = Decimal('0')
            total_transactions = 0
            total_users_served = set()
            
            for frontend_id in owned_frontends:
                frontend_summary = await self.get_frontend_revenue_summary(frontend_id, period_days)
                
                if 'revenue_summary' in frontend_summary:
                    summary = frontend_summary['revenue_summary']
                    total_earnings += Decimal(str(summary['frontend_owner_earnings']))
                    total_transactions += summary['total_transactions']
                    
                    # Track unique users
                    for user_data in frontend_summary.get('top_revenue_users', []):
                        total_users_served.add(user_data['user_id'])
                    
                    dashboard_data['frontend_performance'].append({
                        "frontend_id": frontend_id,
                        "revenue": summary['frontend_owner_earnings'],
                        "transactions": summary['total_transactions'],
                        "growth_rate": summary['growth_rate_percentage'],
                        "avg_transaction_value": summary['average_transaction_value']
                    })
            
            # Calculate aggregate metrics
            dashboard_data['aggregate_metrics'] = {
                "total_earnings": float(total_earnings),
                "total_transactions": total_transactions,
                "unique_users_served": len(total_users_served),
                "average_earnings_per_frontend": float(total_earnings / len(owned_frontends)) if owned_frontends else 0,
                "estimated_monthly_earnings": float(total_earnings * (30 / period_days)) if period_days != 30 else float(total_earnings),
                "estimated_annual_earnings": float(total_earnings * (365 / period_days))
            }
            
            # Generate earnings forecast
            dashboard_data['earnings_forecast'] = await self._generate_earnings_forecast(
                owner_user_id, total_earnings, period_days
            )
            
            # Generate optimization recommendations
            dashboard_data['optimization_recommendations'] = await self._generate_optimization_recommendations(
                owner_user_id, dashboard_data['frontend_performance']
            )
            
            # Payout information
            dashboard_data['payout_info'] = await self._get_owner_payout_info(owner_user_id)
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Failed to get frontend owner dashboard: {e}")
            raise
    
    async def process_bulk_revenue_splits(
        self,
        transactions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Process multiple revenue splits in bulk"""
        
        try:
            processed_count = 0
            failed_count = 0
            total_frontend_revenue = Decimal('0')
            total_activelog_revenue = Decimal('0')
            processing_results = []
            
            for transaction in transactions:
                try:
                    result = await self.process_revenue_split(
                        user_id=uuid.UUID(transaction['user_id']),
                        frontend_id=transaction['frontend_id'],
                        transaction_amount=Decimal(str(transaction['amount'])),
                        transaction_id=transaction.get('transaction_id'),
                        metadata=transaction.get('metadata')
                    )
                    
                    if result['processed']:
                        processed_count += 1
                        total_frontend_revenue += Decimal(str(result['split_breakdown']['frontend_share']))
                        total_activelog_revenue += Decimal(str(result['split_breakdown']['activelog_share']))
                    else:
                        failed_count += 1
                    
                    processing_results.append({
                        "transaction_id": transaction.get('transaction_id'),
                        "processed": result['processed'],
                        "reason": result.get('reason')
                    })
                    
                except Exception as e:
                    failed_count += 1
                    processing_results.append({
                        "transaction_id": transaction.get('transaction_id'),
                        "processed": False,
                        "reason": f"Processing error: {str(e)}"
                    })
            
            return {
                "bulk_processing_complete": True,
                "summary": {
                    "total_transactions": len(transactions),
                    "processed_successfully": processed_count,
                    "failed_processing": failed_count,
                    "success_rate": (processed_count / len(transactions)) * 100 if transactions else 0,
                    "total_frontend_revenue": float(total_frontend_revenue),
                    "total_activelog_revenue": float(total_activelog_revenue)
                },
                "detailed_results": processing_results,
                "processing_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process bulk revenue splits: {e}")
            raise
    
    async def _get_frontend_owner(self, frontend_id: str) -> Optional[User]:
        """Get the owner of a frontend"""
        
        result = await self.db.execute(
            select(User).where(
                and_(
                    User.is_frontend_owner == True,
                    User.frontend_id == frontend_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _calculate_split_amounts(
        self,
        transaction_amount: Decimal,
        frontend_id: str,
        user_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Calculate split amounts with potential bonuses"""
        
        frontend_amount = self.frontend_split
        activelog_amount = self.activelog_split
        method = "standard_split"
        bonus_applied = False
        
        # Check for volume bonuses
        monthly_volume = await self._get_frontend_monthly_volume(frontend_id)
        
        if monthly_volume > Decimal('10000'):  # $10,000+ monthly volume
            # 10% bonus to frontend owner
            frontend_amount = self.frontend_split * Decimal('1.1')
            activelog_amount = transaction_amount - frontend_amount
            method = "volume_bonus_split"
            bonus_applied = True
        elif monthly_volume > Decimal('5000'):  # $5,000+ monthly volume
            # 5% bonus to frontend owner
            frontend_amount = self.frontend_split * Decimal('1.05')
            activelog_amount = transaction_amount - frontend_amount
            method = "small_volume_bonus_split"
            bonus_applied = True
        
        # Ensure we don't exceed transaction amount
        if frontend_amount + activelog_amount > transaction_amount:
            # Pro-rate if bonuses would exceed transaction
            total_split = frontend_amount + activelog_amount
            frontend_amount = (frontend_amount / total_split) * transaction_amount
            activelog_amount = transaction_amount - frontend_amount
        
        return {
            "frontend_amount": frontend_amount,
            "activelog_amount": activelog_amount,
            "method": method,
            "bonus_applied": bonus_applied,
            "monthly_volume": float(monthly_volume)
        }
    
    async def _update_frontend_owner_stats(
        self,
        owner_id: uuid.UUID,
        earnings_amount: Decimal
    ) -> None:
        """Update frontend owner statistics (simplified)"""
        
        # In production, this would update detailed statistics tables
        logger.info(f"Updated stats for frontend owner {owner_id}: +${earnings_amount}")
    
    async def _check_payout_threshold(
        self,
        owner_id: uuid.UUID,
        frontend_id: str
    ) -> Dict[str, Any]:
        """Check if payout threshold has been reached"""
        
        # Get unpaid earnings
        result = await self.db.execute(
            select(func.sum(RevenueShare.frontend_share)).where(
                and_(
                    RevenueShare.frontend_id == frontend_id,
                    RevenueShare.metadata['payout_processed'].is_(None)  # Unpaid
                )
            )
        )
        unpaid_amount = result.scalar() or Decimal('0')
        
        payout_threshold = Decimal('100.0')  # $100 minimum payout
        
        return {
            "unpaid_earnings": float(unpaid_amount),
            "payout_threshold": float(payout_threshold),
            "threshold_reached": unpaid_amount >= payout_threshold,
            "next_payout_eligible": unpaid_amount >= payout_threshold
        }
    
    async def _get_frontend_monthly_volume(self, frontend_id: str) -> Decimal:
        """Get monthly transaction volume for a frontend"""
        
        start_date = datetime.utcnow() - timedelta(days=30)
        
        result = await self.db.execute(
            select(func.sum(RevenueShare.total_amount)).where(
                and_(
                    RevenueShare.frontend_id == frontend_id,
                    RevenueShare.revenue_date >= start_date
                )
            )
        )
        return result.scalar() or Decimal('0')
    
    async def _calculate_frontend_performance_metrics(
        self,
        frontend_id: str,
        revenue_records: List[RevenueShare]
    ) -> Dict[str, Any]:
        """Calculate performance metrics for a frontend"""
        
        if not revenue_records:
            return {"data_insufficient": True}
        
        # Calculate metrics
        avg_transaction = sum(r.total_amount for r in revenue_records) / len(revenue_records)
        total_users = len(set(str(r.user_id) for r in revenue_records))
        
        # Revenue per user
        revenue_per_user = sum(r.total_amount for r in revenue_records) / total_users if total_users > 0 else 0
        
        # Transaction frequency
        days_span = (revenue_records[0].revenue_date - revenue_records[-1].revenue_date).days or 1
        transactions_per_day = len(revenue_records) / days_span
        
        return {
            "average_transaction_value": float(avg_transaction),
            "total_unique_users": total_users,
            "revenue_per_user": float(revenue_per_user),
            "transactions_per_day": float(transactions_per_day),
            "user_retention_indicator": total_users / len(revenue_records) if revenue_records else 0
        }
    
    async def _get_payout_status(self, frontend_id: str) -> Dict[str, Any]:
        """Get current payout status for frontend"""
        
        # Get unpaid earnings
        result = await self.db.execute(
            select(func.sum(RevenueShare.frontend_share)).where(
                and_(
                    RevenueShare.frontend_id == frontend_id,
                    or_(
                        RevenueShare.metadata['payout_processed'].is_(None),
                        RevenueShare.metadata['payout_processed'] == False
                    )
                )
            )
        )
        pending_payout = result.scalar() or Decimal('0')
        
        return {
            "pending_payout": float(pending_payout),
            "next_payout_date": (datetime.utcnow() + timedelta(days=7)).isoformat(),  # Weekly payouts
            "payout_method": "bank_transfer",  # Default method
            "minimum_payout": 100.0
        }
    
    async def _get_owned_frontends(self, owner_id: uuid.UUID) -> List[str]:
        """Get list of frontends owned by user"""
        
        result = await self.db.execute(
            select(User.frontend_id).where(User.id == owner_id)
        )
        frontend_id = result.scalar_one_or_none()
        
        # In a more complex system, a user might own multiple frontends
        return [frontend_id] if frontend_id else []
    
    async def _generate_earnings_forecast(
        self,
        owner_id: uuid.UUID,
        current_earnings: Decimal,
        period_days: int
    ) -> Dict[str, Any]:
        """Generate earnings forecast"""
        
        daily_avg = current_earnings / period_days if period_days > 0 else Decimal('0')
        
        return {
            "next_month": float(daily_avg * 30),
            "next_quarter": float(daily_avg * 90),
            "next_year": float(daily_avg * 365),
            "confidence": "medium",  # Would be based on historical variance
            "growth_assumptions": "Current trend continues"
        }
    
    async def _generate_optimization_recommendations(
        self,
        owner_id: uuid.UUID,
        frontend_performance: List[Dict]
    ) -> List[str]:
        """Generate optimization recommendations"""
        
        recommendations = []
        
        if frontend_performance:
            avg_growth = sum(fp.get('growth_rate', 0) for fp in frontend_performance) / len(frontend_performance)
            
            if avg_growth < 0:
                recommendations.append("Focus on user retention strategies to improve revenue growth")
            elif avg_growth > 20:
                recommendations.append("Consider expanding to additional frontend applications")
            
            avg_transaction = sum(fp.get('avg_transaction_value', 0) for fp in frontend_performance) / len(frontend_performance)
            if avg_transaction < 5:
                recommendations.append("Explore premium features to increase average transaction value")
        
        recommendations.extend([
            "Enable volume bonuses by reaching $5,000+ monthly revenue",
            "Optimize user onboarding to increase conversion rates",
            "Consider implementing referral programs for user acquisition"
        ])
        
        return recommendations
    
    async def _get_owner_payout_info(self, owner_id: uuid.UUID) -> Dict[str, Any]:
        """Get payout information for owner"""
        
        return {
            "payout_schedule": "weekly",
            "minimum_payout": 100.0,
            "payout_method": "bank_transfer",
            "tax_reporting": "1099 issued annually",
            "next_payout_date": (datetime.utcnow() + timedelta(days=7)).isoformat()
        }