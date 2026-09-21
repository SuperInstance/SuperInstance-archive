from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import json

from ..database import (
    CCCWallet, CCCTransaction, Business, BusinessRevenue,
    CCCTransactionType, User
)
from ..wallet.wallet_manager import CCCWalletManager

logger = logging.getLogger(__name__)

class CCCEarningsManager:
    """Manage CCC earnings through product and service sales"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.wallet_manager = CCCWalletManager(db)
        self.platform_fee_rate = Decimal('0.025')  # 2.5% platform fee
        self.min_transaction_amount = Decimal('0.01')  # Minimum 0.01 CCC
        
    async def process_product_sale(
        self,
        business_id: uuid.UUID,
        buyer_user_id: uuid.UUID,
        product_details: Dict[str, Any],
        sale_amount_ccc: Decimal,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a product sale and distribute CCC earnings"""
        
        try:
            if sale_amount_ccc < self.min_transaction_amount:
                return {
                    "success": False,
                    "error": f"Sale amount must be at least {self.min_transaction_amount} CCC"
                }
            
            # Get business and owner information
            business_info = await self._get_business_info(business_id)
            if not business_info["found"]:
                return {"success": False, "error": "Business not found"}
            
            business = business_info["business"]
            owner_wallet = business_info["owner_wallet"]
            
            # Get buyer wallet
            buyer_wallet_result = await self.wallet_manager.get_wallet_balance(user_id=buyer_user_id)
            if "error" in buyer_wallet_result:
                return {"success": False, "error": "Buyer wallet not found"}
            
            buyer_wallet_id = uuid.UUID(buyer_wallet_result["wallet_id"])
            
            # Check buyer has sufficient balance
            if buyer_wallet_result["available_balance"] < float(sale_amount_ccc):
                return {
                    "success": False,
                    "error": "Buyer has insufficient CCC balance",
                    "available_balance": buyer_wallet_result["available_balance"],
                    "required_amount": float(sale_amount_ccc)
                }
            
            # Calculate fee distribution
            platform_fee = sale_amount_ccc * self.platform_fee_rate
            seller_earnings = sale_amount_ccc - platform_fee
            
            # Process buyer payment (spend CCC)
            buyer_spend_result = await self.wallet_manager.spend_ccc(
                wallet_id=buyer_wallet_id,
                amount=sale_amount_ccc,
                purpose=f"Purchase: {product_details.get('name', 'Product')}",
                business_id=business_id,
                metadata={
                    "product_details": product_details,
                    "sale_transaction": True,
                    "platform_fee": float(platform_fee),
                    **(metadata or {})
                }
            )
            
            if not buyer_spend_result["success"]:
                return {
                    "success": False,
                    "error": "Failed to process buyer payment",
                    "details": buyer_spend_result
                }
            
            # Process seller earnings (add CCC)
            seller_earnings_result = await self.wallet_manager.add_ccc_earnings(
                wallet_id=uuid.UUID(owner_wallet["wallet_id"]),
                amount=seller_earnings,
                source=f"Product Sale: {product_details.get('name', 'Product')}",
                business_id=business_id,
                metadata={
                    "buyer_user_id": str(buyer_user_id),
                    "product_details": product_details,
                    "gross_sale_amount": float(sale_amount_ccc),
                    "platform_fee": float(platform_fee),
                    "net_earnings": float(seller_earnings),
                    **(metadata or {})
                }
            )
            
            if not seller_earnings_result["success"]:
                # Rollback buyer transaction if seller earning fails
                await self._rollback_transaction(buyer_spend_result["transaction_id"])
                return {
                    "success": False,
                    "error": "Failed to process seller earnings",
                    "details": seller_earnings_result
                }
            
            # Record business revenue
            await self._record_business_revenue(
                business_id=business_id,
                revenue_amount=seller_earnings,
                revenue_source="product_sale",
                transaction_details={
                    "product": product_details,
                    "buyer_id": str(buyer_user_id),
                    "gross_amount": float(sale_amount_ccc),
                    "platform_fee": float(platform_fee)
                }
            )
            
            # Update business monthly revenue
            await self._update_business_monthly_revenue(business_id, seller_earnings)
            
            return {
                "success": True,
                "sale_id": str(uuid.uuid4()),  # Generate sale ID
                "gross_sale_amount_ccc": float(sale_amount_ccc),
                "platform_fee_ccc": float(platform_fee),
                "seller_earnings_ccc": float(seller_earnings),
                "buyer_transaction_id": buyer_spend_result["transaction_id"],
                "seller_transaction_id": seller_earnings_result["transaction_id"],
                "product_details": product_details,
                "sale_timestamp": datetime.utcnow().isoformat(),
                "fee_breakdown": {
                    "platform_fee_rate": float(self.platform_fee_rate),
                    "platform_fee_amount": float(platform_fee),
                    "seller_net_rate": float(1 - self.platform_fee_rate)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to process product sale: {e}")
            raise
    
    async def process_service_sale(
        self,
        business_id: uuid.UUID,
        buyer_user_id: uuid.UUID,
        service_details: Dict[str, Any],
        service_amount_ccc: Decimal,
        is_subscription: bool = False,
        subscription_period_months: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a service sale and distribute CCC earnings"""
        
        try:
            # Similar to product sale but with service-specific handling
            if service_amount_ccc < self.min_transaction_amount:
                return {
                    "success": False,
                    "error": f"Service amount must be at least {self.min_transaction_amount} CCC"
                }
            
            # Get business info
            business_info = await self._get_business_info(business_id)
            if not business_info["found"]:
                return {"success": False, "error": "Business not found"}
            
            business = business_info["business"]
            owner_wallet = business_info["owner_wallet"]
            
            # Calculate earnings (different fee structure for services)
            service_platform_fee_rate = Decimal('0.02')  # 2% for services
            platform_fee = service_amount_ccc * service_platform_fee_rate
            seller_earnings = service_amount_ccc - platform_fee
            
            # Process payment and earnings similar to product sale
            buyer_wallet_result = await self.wallet_manager.get_wallet_balance(user_id=buyer_user_id)
            if "error" in buyer_wallet_result:
                return {"success": False, "error": "Buyer wallet not found"}
            
            buyer_wallet_id = uuid.UUID(buyer_wallet_result["wallet_id"])
            
            # Check balance
            if buyer_wallet_result["available_balance"] < float(service_amount_ccc):
                return {
                    "success": False,
                    "error": "Buyer has insufficient CCC balance",
                    "available_balance": buyer_wallet_result["available_balance"]
                }
            
            # Process transactions
            buyer_spend_result = await self.wallet_manager.spend_ccc(
                wallet_id=buyer_wallet_id,
                amount=service_amount_ccc,
                purpose=f"Service: {service_details.get('name', 'Service')}",
                business_id=business_id,
                metadata={
                    "service_details": service_details,
                    "is_subscription": is_subscription,
                    "subscription_period_months": subscription_period_months,
                    "service_transaction": True,
                    **(metadata or {})
                }
            )
            
            if not buyer_spend_result["success"]:
                return {"success": False, "error": "Failed to process buyer payment"}
            
            seller_earnings_result = await self.wallet_manager.add_ccc_earnings(
                wallet_id=uuid.UUID(owner_wallet["wallet_id"]),
                amount=seller_earnings,
                source=f"Service: {service_details.get('name', 'Service')}",
                business_id=business_id,
                metadata={
                    "buyer_user_id": str(buyer_user_id),
                    "service_details": service_details,
                    "is_subscription": is_subscription,
                    "net_earnings": float(seller_earnings)
                }
            )
            
            if not seller_earnings_result["success"]:
                await self._rollback_transaction(buyer_spend_result["transaction_id"])
                return {"success": False, "error": "Failed to process seller earnings"}
            
            # Record business revenue
            await self._record_business_revenue(
                business_id=business_id,
                revenue_amount=seller_earnings,
                revenue_source="service_sale",
                transaction_details={
                    "service": service_details,
                    "buyer_id": str(buyer_user_id),
                    "is_subscription": is_subscription,
                    "subscription_period": subscription_period_months
                }
            )
            
            # Update business stats
            await self._update_business_monthly_revenue(business_id, seller_earnings)
            
            # Schedule recurring billing if subscription
            recurring_billing_id = None
            if is_subscription and subscription_period_months:
                recurring_billing_id = await self._setup_recurring_billing(
                    business_id=business_id,
                    buyer_user_id=buyer_user_id,
                    service_details=service_details,
                    monthly_amount=service_amount_ccc / subscription_period_months,
                    period_months=subscription_period_months
                )
            
            return {
                "success": True,
                "service_sale_id": str(uuid.uuid4()),
                "gross_amount_ccc": float(service_amount_ccc),
                "platform_fee_ccc": float(platform_fee),
                "seller_earnings_ccc": float(seller_earnings),
                "buyer_transaction_id": buyer_spend_result["transaction_id"],
                "seller_transaction_id": seller_earnings_result["transaction_id"],
                "service_details": service_details,
                "is_subscription": is_subscription,
                "recurring_billing_id": str(recurring_billing_id) if recurring_billing_id else None,
                "sale_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process service sale: {e}")
            raise
    
    async def get_business_sales_analytics(
        self,
        business_id: uuid.UUID,
        period_days: int = 30
    ) -> Dict[str, Any]:
        """Get comprehensive sales analytics for a business"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get business info
            business_info = await self._get_business_info(business_id)
            if not business_info["found"]:
                return {"error": "Business not found"}
            
            # Get all earnings transactions for this business
            result = await self.db.execute(
                select(CCCTransaction).where(
                    and_(
                        CCCTransaction.business_id == business_id,
                        CCCTransaction.transaction_type == CCCTransactionType.EARN,
                        CCCTransaction.created_at >= start_date
                    )
                ).order_by(CCCTransaction.created_at.desc())
            )
            earnings_transactions = result.scalars().all()
            
            if not earnings_transactions:
                return {
                    "business_id": str(business_id),
                    "period_days": period_days,
                    "message": "No sales data found for this period"
                }
            
            # Calculate analytics
            total_gross_revenue = Decimal('0')
            total_net_earnings = Decimal('0')
            total_platform_fees = Decimal('0')
            product_sales = 0
            service_sales = 0
            subscription_sales = 0
            unique_customers = set()
            
            daily_sales = {}
            top_products = {}
            top_services = {}
            
            for tx in earnings_transactions:
                # Add to totals
                net_earnings = tx.amount
                total_net_earnings += net_earnings
                
                # Extract metadata
                metadata = tx.metadata or {}
                gross_amount = Decimal(str(metadata.get('gross_sale_amount', net_earnings)))
                platform_fee = Decimal(str(metadata.get('platform_fee', 0)))
                
                total_gross_revenue += gross_amount
                total_platform_fees += platform_fee
                
                # Track customer
                buyer_id = metadata.get('buyer_user_id')
                if buyer_id:
                    unique_customers.add(buyer_id)
                
                # Categorize transaction
                if 'product_details' in metadata:
                    product_sales += 1
                    product_name = metadata['product_details'].get('name', 'Unknown Product')
                    if product_name not in top_products:
                        top_products[product_name] = {"sales": 0, "revenue": Decimal('0')}
                    top_products[product_name]["sales"] += 1
                    top_products[product_name]["revenue"] += gross_amount
                elif 'service_details' in metadata:
                    if metadata.get('is_subscription'):
                        subscription_sales += 1
                    else:
                        service_sales += 1
                    service_name = metadata['service_details'].get('name', 'Unknown Service')
                    if service_name not in top_services:
                        top_services[service_name] = {"sales": 0, "revenue": Decimal('0')}
                    top_services[service_name]["sales"] += 1
                    top_services[service_name]["revenue"] += gross_amount
                
                # Daily breakdown
                day = tx.created_at.date().isoformat()
                if day not in daily_sales:
                    daily_sales[day] = {"transactions": 0, "revenue": Decimal('0')}
                daily_sales[day]["transactions"] += 1
                daily_sales[day]["revenue"] += gross_amount
            
            # Sort top products and services
            top_products_sorted = sorted(
                top_products.items(),
                key=lambda x: x[1]["revenue"],
                reverse=True
            )[:10]
            
            top_services_sorted = sorted(
                top_services.items(),
                key=lambda x: x[1]["revenue"],
                reverse=True
            )[:10]
            
            # Convert to serializable format
            top_products_serialized = [
                {
                    "product_name": name,
                    "sales_count": data["sales"],
                    "total_revenue": float(data["revenue"])
                }
                for name, data in top_products_sorted
            ]
            
            top_services_serialized = [
                {
                    "service_name": name,
                    "sales_count": data["sales"],
                    "total_revenue": float(data["revenue"])
                }
                for name, data in top_services_sorted
            ]
            
            daily_sales_serialized = {
                day: {
                    "transactions": data["transactions"],
                    "revenue": float(data["revenue"])
                }
                for day, data in daily_sales.items()
            }
            
            return {
                "business_id": str(business_id),
                "business_name": business_info["business"].name,
                "period_days": period_days,
                "summary": {
                    "total_transactions": len(earnings_transactions),
                    "total_gross_revenue_ccc": float(total_gross_revenue),
                    "total_net_earnings_ccc": float(total_net_earnings),
                    "total_platform_fees_ccc": float(total_platform_fees),
                    "unique_customers": len(unique_customers),
                    "average_transaction_value": float(total_gross_revenue / len(earnings_transactions)),
                    "average_daily_revenue": float(total_gross_revenue / period_days)
                },
                "sales_breakdown": {
                    "product_sales": product_sales,
                    "service_sales": service_sales,
                    "subscription_sales": subscription_sales
                },
                "top_products": top_products_serialized,
                "top_services": top_services_serialized,
                "daily_sales": daily_sales_serialized,
                "growth_metrics": await self._calculate_growth_metrics(business_id, period_days),
                "analysis_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get business sales analytics: {e}")
            raise
    
    async def get_customer_purchase_history(
        self,
        customer_user_id: uuid.UUID,
        period_days: int = 90
    ) -> Dict[str, Any]:
        """Get purchase history for a customer"""
        
        try:
            start_date = datetime.utcnow() - timedelta(days=period_days)
            
            # Get customer's spending transactions
            customer_wallet = await self.wallet_manager.get_wallet_balance(user_id=customer_user_id)
            if "error" in customer_wallet:
                return {"error": "Customer wallet not found"}
            
            result = await self.db.execute(
                select(CCCTransaction).where(
                    and_(
                        CCCTransaction.wallet_id == uuid.UUID(customer_wallet["wallet_id"]),
                        CCCTransaction.transaction_type == CCCTransactionType.SPEND,
                        CCCTransaction.created_at >= start_date,
                        CCCTransaction.business_id.isnot(None)  # Only business purchases
                    )
                ).order_by(CCCTransaction.created_at.desc())
            )
            purchases = result.scalars().all()
            
            if not purchases:
                return {
                    "customer_id": str(customer_user_id),
                    "period_days": period_days,
                    "message": "No purchase history found"
                }
            
            # Analyze purchases
            total_spent = sum(abs(tx.amount) for tx in purchases)
            businesses_purchased_from = set(str(tx.business_id) for tx in purchases if tx.business_id)
            
            purchase_history = []
            for tx in purchases:
                metadata = tx.metadata or {}
                purchase_history.append({
                    "transaction_id": str(tx.id),
                    "amount_ccc": float(abs(tx.amount)),
                    "business_id": str(tx.business_id) if tx.business_id else None,
                    "purchase_type": "product" if "product_details" in metadata else "service",
                    "item_details": metadata.get("product_details") or metadata.get("service_details", {}),
                    "purchase_date": tx.created_at.isoformat(),
                    "description": tx.description
                })
            
            return {
                "customer_id": str(customer_user_id),
                "period_days": period_days,
                "summary": {
                    "total_purchases": len(purchases),
                    "total_spent_ccc": float(total_spent),
                    "unique_businesses": len(businesses_purchased_from),
                    "average_purchase_value": float(total_spent / len(purchases)),
                    "purchase_frequency": len(purchases) / (period_days / 30)  # Purchases per month
                },
                "purchase_history": purchase_history,
                "spending_pattern": await self._analyze_spending_pattern(purchases)
            }
            
        except Exception as e:
            logger.error(f"Failed to get customer purchase history: {e}")
            raise
    
    async def process_refund(
        self,
        original_transaction_id: uuid.UUID,
        refund_amount_ccc: Decimal,
        refund_reason: str,
        business_id: uuid.UUID,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a refund for a previous sale"""
        
        try:
            # Get original transaction
            result = await self.db.execute(
                select(CCCTransaction).where(CCCTransaction.id == original_transaction_id)
            )
            original_tx = result.scalar_one_or_none()
            
            if not original_tx:
                return {"success": False, "error": "Original transaction not found"}
            
            if original_tx.transaction_type != CCCTransactionType.SPEND:
                return {"success": False, "error": "Can only refund purchase transactions"}
            
            # Get business and customer wallets
            business_info = await self._get_business_info(business_id)
            if not business_info["found"]:
                return {"success": False, "error": "Business not found"}
            
            customer_wallet_id = original_tx.wallet_id
            business_wallet_id = uuid.UUID(business_info["owner_wallet"]["wallet_id"])
            
            # Check business has sufficient balance for refund
            business_balance = await self.wallet_manager.get_wallet_balance(wallet_id=business_wallet_id)
            if business_balance["available_balance"] < float(refund_amount_ccc):
                return {
                    "success": False,
                    "error": "Business has insufficient balance for refund",
                    "available_balance": business_balance["available_balance"]
                }
            
            # Process refund - deduct from business, add to customer
            business_refund_result = await self.wallet_manager.spend_ccc(
                wallet_id=business_wallet_id,
                amount=refund_amount_ccc,
                purpose=f"Refund: {refund_reason}",
                metadata={
                    "refund_transaction": True,
                    "original_transaction_id": str(original_transaction_id),
                    "refund_reason": refund_reason,
                    **(metadata or {})
                }
            )
            
            if not business_refund_result["success"]:
                return {"success": False, "error": "Failed to process business refund deduction"}
            
            customer_refund_result = await self.wallet_manager.add_ccc_earnings(
                wallet_id=customer_wallet_id,
                amount=refund_amount_ccc,
                source=f"Refund from business",
                business_id=business_id,
                metadata={
                    "refund_received": True,
                    "original_transaction_id": str(original_transaction_id),
                    "refund_reason": refund_reason
                }
            )
            
            if not customer_refund_result["success"]:
                # Rollback business transaction
                await self._rollback_transaction(business_refund_result["transaction_id"])
                return {"success": False, "error": "Failed to process customer refund"}
            
            return {
                "success": True,
                "refund_id": str(uuid.uuid4()),
                "refund_amount_ccc": float(refund_amount_ccc),
                "original_transaction_id": str(original_transaction_id),
                "business_transaction_id": business_refund_result["transaction_id"],
                "customer_transaction_id": customer_refund_result["transaction_id"],
                "refund_reason": refund_reason,
                "refund_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process refund: {e}")
            raise
    
    async def _get_business_info(self, business_id: uuid.UUID) -> Dict[str, Any]:
        """Get business and owner wallet information"""
        
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            return {"found": False}
        
        # Get owner wallet
        owner_wallet = await self.wallet_manager.get_wallet_balance(user_id=business.owner_id)
        if "error" in owner_wallet:
            return {"found": False, "error": "Owner wallet not found"}
        
        return {
            "found": True,
            "business": business,
            "owner_wallet": owner_wallet
        }
    
    async def _record_business_revenue(
        self,
        business_id: uuid.UUID,
        revenue_amount: Decimal,
        revenue_source: str,
        transaction_details: Dict
    ) -> None:
        """Record business revenue for analytics"""
        
        # Get current month period
        now = datetime.utcnow()
        period_start = datetime(now.year, now.month, 1)
        
        if now.month == 12:
            period_end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
        
        # Check if revenue record exists for this period
        result = await self.db.execute(
            select(BusinessRevenue).where(
                and_(
                    BusinessRevenue.business_id == business_id,
                    BusinessRevenue.revenue_period_start == period_start
                )
            )
        )
        existing_revenue = result.scalar_one_or_none()
        
        if existing_revenue:
            # Update existing record
            existing_revenue.total_revenue_ccc += revenue_amount
            existing_revenue.net_profit_ccc += revenue_amount  # Simplified
            
            # Update revenue sources
            sources = existing_revenue.revenue_sources or {}
            if revenue_source not in sources:
                sources[revenue_source] = {"count": 0, "amount": 0}
            sources[revenue_source]["count"] += 1
            sources[revenue_source]["amount"] += float(revenue_amount)
            existing_revenue.revenue_sources = sources
        else:
            # Create new record
            revenue_record = BusinessRevenue(
                business_id=business_id,
                revenue_period_start=period_start,
                revenue_period_end=period_end,
                total_revenue_ccc=revenue_amount,
                net_profit_ccc=revenue_amount,  # Simplified
                revenue_sources={
                    revenue_source: {
                        "count": 1,
                        "amount": float(revenue_amount)
                    }
                }
            )
            self.db.add(revenue_record)
        
        await self.db.commit()
    
    async def _update_business_monthly_revenue(
        self,
        business_id: uuid.UUID,
        revenue_amount: Decimal
    ) -> None:
        """Update business monthly revenue field"""
        
        result = await self.db.execute(
            select(Business).where(Business.id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if business:
            business.monthly_revenue_ccc += revenue_amount
            await self.db.commit()
    
    async def _setup_recurring_billing(
        self,
        business_id: uuid.UUID,
        buyer_user_id: uuid.UUID,
        service_details: Dict,
        monthly_amount: Decimal,
        period_months: int
    ) -> uuid.UUID:
        """Setup recurring billing for subscription services"""
        
        # In production, this would create proper recurring billing records
        # For now, just return a placeholder ID
        return uuid.uuid4()
    
    async def _rollback_transaction(self, transaction_id: str) -> None:
        """Rollback a transaction (simplified implementation)"""
        
        # In production, this would properly reverse the transaction
        logger.warning(f"Transaction rollback requested for {transaction_id}")
    
    async def _calculate_growth_metrics(
        self,
        business_id: uuid.UUID,
        period_days: int
    ) -> Dict[str, Any]:
        """Calculate growth metrics for business"""
        
        # Compare current period with previous period
        current_start = datetime.utcnow() - timedelta(days=period_days)
        previous_start = current_start - timedelta(days=period_days)
        
        # Get current period revenue
        result = await self.db.execute(
            select(func.sum(CCCTransaction.amount)).where(
                and_(
                    CCCTransaction.business_id == business_id,
                    CCCTransaction.transaction_type == CCCTransactionType.EARN,
                    CCCTransaction.created_at >= current_start
                )
            )
        )
        current_revenue = result.scalar() or Decimal('0')
        
        # Get previous period revenue
        result = await self.db.execute(
            select(func.sum(CCCTransaction.amount)).where(
                and_(
                    CCCTransaction.business_id == business_id,
                    CCCTransaction.transaction_type == CCCTransactionType.EARN,
                    CCCTransaction.created_at >= previous_start,
                    CCCTransaction.created_at < current_start
                )
            )
        )
        previous_revenue = result.scalar() or Decimal('0')
        
        # Calculate growth rate
        if previous_revenue > 0:
            growth_rate = ((current_revenue - previous_revenue) / previous_revenue) * 100
        else:
            growth_rate = 100 if current_revenue > 0 else 0
        
        return {
            "current_period_revenue": float(current_revenue),
            "previous_period_revenue": float(previous_revenue),
            "growth_rate_percentage": float(growth_rate),
            "growth_trend": "increasing" if growth_rate > 5 else "decreasing" if growth_rate < -5 else "stable"
        }
    
    async def _analyze_spending_pattern(
        self,
        purchases: List[CCCTransaction]
    ) -> Dict[str, Any]:
        """Analyze customer spending patterns"""
        
        if not purchases:
            return {"pattern": "no_data"}
        
        # Analyze purchase frequency
        dates = [tx.created_at.date() for tx in purchases]
        unique_dates = len(set(dates))
        total_days = (max(dates) - min(dates)).days + 1
        
        frequency_score = unique_dates / total_days if total_days > 0 else 0
        
        # Analyze spending consistency
        amounts = [abs(tx.amount) for tx in purchases]
        avg_amount = sum(amounts) / len(amounts)
        variance = sum((amount - avg_amount) ** 2 for amount in amounts) / len(amounts)
        consistency_score = 1 / (1 + variance)  # Higher score = more consistent
        
        return {
            "frequency_score": frequency_score,
            "consistency_score": float(consistency_score),
            "average_purchase": float(avg_amount),
            "purchase_pattern": "regular" if frequency_score > 0.3 else "sporadic"
        }