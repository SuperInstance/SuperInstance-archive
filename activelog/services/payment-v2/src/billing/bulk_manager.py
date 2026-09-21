from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

from ..database import (
    Organization, User, ComputeCredit, CreditTransaction, 
    CreditTransactionType, Invoice, InvoiceStatus
)

class BulkBillingManager:
    """Handles bulk billing for organizations and enterprise accounts"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_organization_billing_cycle(
        self,
        organization_id: uuid.UUID,
        billing_period: str = "monthly",  # monthly, quarterly, annually
        credit_limit: Decimal = Decimal('10000'),
        auto_billing_enabled: bool = True
    ) -> Dict[str, Any]:
        """Set up organization billing cycle"""
        
        # Get organization
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            raise ValueError("Organization not found")
        
        # Update organization billing settings
        organization.auto_billing_enabled = auto_billing_enabled
        organization.credit_limit = credit_limit
        organization.billing_tier = "enterprise"
        
        # Calculate next billing date
        next_billing_date = self._calculate_next_billing_date(billing_period)
        
        await self.db.commit()
        
        return {
            "success": True,
            "organization_id": str(organization_id),
            "billing_period": billing_period,
            "credit_limit": float(credit_limit),
            "auto_billing_enabled": auto_billing_enabled,
            "next_billing_date": next_billing_date.isoformat()
        }
    
    async def process_bulk_billing(
        self,
        organization_id: uuid.UUID,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Dict[str, Any]:
        """Process bulk billing for organization"""
        
        # Get organization
        org_result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        organization = org_result.scalar_one_or_none()
        
        if not organization:
            raise ValueError("Organization not found")
        
        # Get all organization users
        users_result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = users_result.scalars().all()
        
        # Aggregate usage across all users
        total_usage = await self._calculate_organization_usage(
            organization_id, billing_period_start, billing_period_end
        )
        
        # Calculate bulk discount
        bulk_discount = self._calculate_bulk_discount(total_usage["total_credits"])
        discounted_total = total_usage["total_credits"] * (1 - bulk_discount)
        
        # Generate invoice
        invoice = await self._create_bulk_invoice(
            organization, total_usage, bulk_discount, 
            billing_period_start, billing_period_end
        )
        
        return {
            "success": True,
            "invoice_id": str(invoice.id),
            "organization_id": str(organization_id),
            "billing_period": {
                "start": billing_period_start.isoformat(),
                "end": billing_period_end.isoformat()
            },
            "usage_summary": total_usage,
            "bulk_discount": float(bulk_discount),
            "total_before_discount": float(total_usage["total_credits"]),
            "total_after_discount": float(discounted_total),
            "user_count": len(users)
        }
    
    async def get_organization_usage_breakdown(
        self,
        organization_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Get detailed usage breakdown by user and resource type"""
        
        # Get organization users
        users_result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = users_result.scalars().all()
        
        user_usage = {}
        resource_totals = {}
        grand_total = Decimal('0')
        
        for user in users:
            # Get user's usage transactions
            usage_result = await self.db.execute(
                select(CreditTransaction).where(
                    and_(
                        CreditTransaction.user_id == user.id,
                        CreditTransaction.transaction_type == CreditTransactionType.USAGE,
                        CreditTransaction.created_at >= start_date,
                        CreditTransaction.created_at <= end_date
                    )
                )
            )
            
            transactions = usage_result.scalars().all()
            user_total = Decimal('0')
            user_resources = {}
            
            for tx in transactions:
                credits_used = abs(tx.amount)
                user_total += credits_used
                grand_total += credits_used
                
                if tx.metadata:
                    resource_type = tx.metadata.get('resource_type', 'unknown')
                    
                    # User resource breakdown
                    if resource_type not in user_resources:
                        user_resources[resource_type] = {
                            'credits': 0,
                            'transactions': 0,
                            'units': 0
                        }
                    
                    user_resources[resource_type]['credits'] += float(credits_used)
                    user_resources[resource_type]['transactions'] += 1
                    user_resources[resource_type]['units'] += tx.metadata.get('units', 0)
                    
                    # Organization resource totals
                    if resource_type not in resource_totals:
                        resource_totals[resource_type] = {
                            'credits': 0,
                            'transactions': 0,
                            'units': 0,
                            'users': set()
                        }
                    
                    resource_totals[resource_type]['credits'] += float(credits_used)
                    resource_totals[resource_type]['transactions'] += 1
                    resource_totals[resource_type]['units'] += tx.metadata.get('units', 0)
                    resource_totals[resource_type]['users'].add(str(user.id))
            
            user_usage[str(user.id)] = {
                'email': user.email,
                'total_credits': float(user_total),
                'resources': user_resources,
                'transaction_count': len(transactions)
            }
        
        # Convert sets to counts for JSON serialization
        for resource_type in resource_totals:
            resource_totals[resource_type]['unique_users'] = len(resource_totals[resource_type]['users'])
            del resource_totals[resource_type]['users']
        
        return {
            "organization_id": str(organization_id),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "grand_total_credits": float(grand_total),
            "total_users": len(users),
            "user_breakdown": user_usage,
            "resource_totals": resource_totals
        }
    
    async def apply_organization_credits(
        self,
        organization_id: uuid.UUID,
        credit_amount: Decimal,
        distribution_method: str = "equal"  # equal, usage_based, manual
    ) -> Dict[str, Any]:
        """Apply bulk credits to organization users"""
        
        # Get organization users
        users_result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = users_result.scalars().all()
        
        if not users:
            raise ValueError("No users found for organization")
        
        distribution_plan = await self._calculate_credit_distribution(
            users, credit_amount, distribution_method
        )
        
        applied_credits = []
        
        for user_id, amount in distribution_plan.items():
            # Get or create credit account
            from ..credits.economics import ComputeEconomics
            economics = ComputeEconomics(self.db)
            account = await economics._get_or_create_credit_account(uuid.UUID(user_id))
            
            # Create transaction
            transaction = CreditTransaction(
                user_id=uuid.UUID(user_id),
                organization_id=organization_id,
                transaction_type=CreditTransactionType.PURCHASE,
                amount=amount,
                balance_before=account.balance,
                balance_after=account.balance + amount,
                description="Organization bulk credit allocation",
                metadata={
                    "bulk_credit": True,
                    "distribution_method": distribution_method,
                    "organization_purchase": True
                }
            )
            
            self.db.add(transaction)
            
            # Update balance
            account.balance += amount
            account.updated_at = datetime.utcnow()
            
            applied_credits.append({
                "user_id": user_id,
                "amount": float(amount),
                "transaction_id": str(transaction.id)
            })
        
        await self.db.commit()
        
        return {
            "success": True,
            "organization_id": str(organization_id),
            "total_credits_applied": float(credit_amount),
            "distribution_method": distribution_method,
            "users_credited": len(applied_credits),
            "credit_details": applied_credits
        }
    
    async def get_billing_forecasts(
        self,
        organization_id: uuid.UUID,
        months_ahead: int = 3
    ) -> Dict[str, Any]:
        """Generate billing forecasts based on usage patterns"""
        
        # Get historical usage (last 3 months)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        historical_usage = await self._calculate_organization_usage(
            organization_id, start_date, end_date
        )
        
        # Calculate monthly average
        monthly_average = historical_usage["total_credits"] / 3
        
        # Generate forecasts
        forecasts = []
        current_date = end_date
        
        for month in range(months_ahead):
            forecast_start = current_date + timedelta(days=30 * month)
            forecast_end = forecast_start + timedelta(days=30)
            
            # Apply growth factor (simple linear projection)
            growth_factor = 1 + (0.05 * month)  # 5% growth per month
            projected_usage = monthly_average * Decimal(str(growth_factor))
            
            # Calculate cost with bulk discount
            bulk_discount = self._calculate_bulk_discount(projected_usage)
            projected_cost = projected_usage * (1 - bulk_discount)
            
            forecasts.append({
                "month": month + 1,
                "period_start": forecast_start.date().isoformat(),
                "period_end": forecast_end.date().isoformat(),
                "projected_credits": float(projected_usage),
                "bulk_discount": float(bulk_discount),
                "projected_cost": float(projected_cost),
                "confidence": max(0.9 - (month * 0.1), 0.5)  # Decreasing confidence
            })
        
        return {
            "organization_id": str(organization_id),
            "historical_period": {
                "start": start_date.date().isoformat(),
                "end": end_date.date().isoformat(),
                "total_credits": float(historical_usage["total_credits"])
            },
            "monthly_average": float(monthly_average),
            "forecasts": forecasts
        }
    
    async def _calculate_organization_usage(
        self,
        organization_id: uuid.UUID,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Calculate total organization usage for period"""
        
        # Get all usage transactions for organization users
        usage_result = await self.db.execute(
            select(CreditTransaction).where(
                and_(
                    CreditTransaction.organization_id == organization_id,
                    CreditTransaction.transaction_type == CreditTransactionType.USAGE,
                    CreditTransaction.created_at >= start_date,
                    CreditTransaction.created_at <= end_date
                )
            )
        )
        
        transactions = usage_result.scalars().all()
        
        total_credits = Decimal('0')
        resource_breakdown = {}
        unique_users = set()
        
        for tx in transactions:
            credits_used = abs(tx.amount)
            total_credits += credits_used
            unique_users.add(str(tx.user_id))
            
            if tx.metadata:
                resource_type = tx.metadata.get('resource_type', 'unknown')
                if resource_type not in resource_breakdown:
                    resource_breakdown[resource_type] = 0
                resource_breakdown[resource_type] += float(credits_used)
        
        return {
            "total_credits": total_credits,
            "transaction_count": len(transactions),
            "unique_users": len(unique_users),
            "resource_breakdown": resource_breakdown
        }
    
    def _calculate_bulk_discount(self, total_credits: Decimal) -> Decimal:
        """Calculate bulk discount based on usage volume"""
        
        if total_credits >= 100000:  # $1000+ usage
            return Decimal('0.20')    # 20% discount
        elif total_credits >= 50000:  # $500+ usage
            return Decimal('0.15')    # 15% discount
        elif total_credits >= 20000:  # $200+ usage
            return Decimal('0.10')    # 10% discount
        elif total_credits >= 10000:  # $100+ usage
            return Decimal('0.05')    # 5% discount
        else:
            return Decimal('0')       # No discount
    
    async def _create_bulk_invoice(
        self,
        organization: Organization,
        usage_summary: Dict[str, Any],
        bulk_discount: Decimal,
        period_start: datetime,
        period_end: datetime
    ) -> Invoice:
        """Create bulk invoice for organization"""
        
        # Generate invoice number
        invoice_number = f"ORG-{organization.id.hex[:8].upper()}-{period_start.strftime('%Y%m')}"
        
        subtotal = usage_summary["total_credits"] / 100  # Convert credits to USD
        discount_amount = subtotal * bulk_discount
        total_amount = subtotal - discount_amount
        
        # Create line items
        line_items = []
        for resource_type, credits in usage_summary["resource_breakdown"].items():
            line_items.append({
                "description": f"{resource_type.title()} Usage",
                "quantity": float(credits),
                "unit_price": 0.01,  # $0.01 per credit
                "total": float(credits) * 0.01
            })
        
        if bulk_discount > 0:
            line_items.append({
                "description": f"Bulk Discount ({float(bulk_discount)*100:.0f}%)",
                "quantity": 1,
                "unit_price": -float(discount_amount),
                "total": -float(discount_amount)
            })
        
        invoice = Invoice(
            invoice_number=invoice_number,
            organization_id=organization.id,
            status=InvoiceStatus.SENT,
            subtotal=subtotal,
            tax_amount=Decimal('0'),  # Tax calculation would be handled separately
            total_amount=total_amount,
            currency="USD",
            due_date=datetime.utcnow() + timedelta(days=organization.payment_terms),
            items=line_items,
            metadata={
                "billing_period": {
                    "start": period_start.isoformat(),
                    "end": period_end.isoformat()
                },
                "bulk_discount": float(bulk_discount),
                "usage_summary": usage_summary
            }
        )
        
        self.db.add(invoice)
        await self.db.flush()
        
        return invoice
    
    async def _calculate_credit_distribution(
        self,
        users: List[User],
        total_credits: Decimal,
        method: str
    ) -> Dict[str, Decimal]:
        """Calculate how to distribute credits among users"""
        
        if method == "equal":
            # Equal distribution
            credits_per_user = total_credits / len(users)
            return {str(user.id): credits_per_user for user in users}
        
        elif method == "usage_based":
            # Distribution based on historical usage
            # This would require more complex calculation
            # For now, implement equal distribution
            return await self._calculate_credit_distribution(users, total_credits, "equal")
        
        else:
            # Manual distribution would require additional parameters
            raise ValueError(f"Unsupported distribution method: {method}")
    
    def _calculate_next_billing_date(self, billing_period: str) -> datetime:
        """Calculate next billing date based on period"""
        
        now = datetime.utcnow()
        
        if billing_period == "monthly":
            if now.month == 12:
                return datetime(now.year + 1, 1, 1)
            else:
                return datetime(now.year, now.month + 1, 1)
        
        elif billing_period == "quarterly":
            current_quarter = (now.month - 1) // 3 + 1
            next_quarter_month = (current_quarter % 4) * 3 + 1
            next_year = now.year if current_quarter < 4 else now.year + 1
            return datetime(next_year, next_quarter_month, 1)
        
        elif billing_period == "annually":
            return datetime(now.year + 1, 1, 1)
        
        else:
            raise ValueError(f"Unsupported billing period: {billing_period}")