"""
Enterprise Billing Manager
Handles custom enterprise pricing, volume discounts, and specialized billing arrangements
"""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from ...models.database import (
    User, EnterpriseAccount, EnterpriseBillingPlan, Transaction, 
    EnterpriseInvoice, EnterpriseContract, EnterpriseUsage,
    TransactionType, TransactionStatus, SubscriptionTier
)
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class BillingCycle(Enum):
    """Enterprise billing cycles"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    CUSTOM = "custom"

class PaymentTerms(Enum):
    """Payment terms for enterprise accounts"""
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_45 = "net_45"
    NET_60 = "net_60"
    PREPAID = "prepaid"

class EnterpriseBillingManager:
    """Manages enterprise billing with custom pricing and terms"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        
        # Volume discount tiers (percentage off)
        self.volume_discounts = {
            1000: Decimal("0.05"),     # 5% discount for $1000+ monthly
            5000: Decimal("0.10"),     # 10% discount for $5000+ monthly  
            15000: Decimal("0.15"),    # 15% discount for $15000+ monthly
            50000: Decimal("0.20"),    # 20% discount for $50000+ monthly
            100000: Decimal("0.25")    # 25% discount for $100000+ monthly
        }
    
    async def create_enterprise_account(
        self,
        user_id: str,
        company_name: str,
        billing_contact_name: str,
        billing_contact_email: str,
        billing_address: Dict,
        tax_id: Optional[str] = None,
        payment_terms: PaymentTerms = PaymentTerms.NET_30,
        billing_cycle: BillingCycle = BillingCycle.MONTHLY
    ) -> EnterpriseAccount:
        """Create a new enterprise account"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Check if enterprise account already exists
        existing_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.user_id == user_id)
            .first()
        )
        
        if existing_account:
            raise ValueError(f"Enterprise account already exists for user {user_id}")
        
        # Create enterprise account
        enterprise_account = EnterpriseAccount(
            user_id=user_id,
            company_name=company_name,
            billing_contact_name=billing_contact_name,
            billing_contact_email=billing_contact_email,
            billing_address=billing_address,
            tax_id=tax_id,
            payment_terms=payment_terms,
            billing_cycle=billing_cycle,
            is_active=True,
            credit_limit_cc=Decimal("100000"),  # Default $1000 credit limit
            current_balance_cc=Decimal("0")
        )
        
        # Upgrade user to enterprise tier
        user.subscription_tier = SubscriptionTier.ENTERPRISE
        
        self.db.add(enterprise_account)
        self.db.commit()
        
        logger.info(f"Created enterprise account for {company_name} (user {user_id})")
        return enterprise_account
    
    async def create_custom_billing_plan(
        self,
        enterprise_account_id: str,
        plan_name: str,
        base_monthly_cc: Decimal,
        included_storage_gb: int,
        included_compute_hours: int,
        included_bandwidth_gb: int,
        included_api_calls: int,
        storage_overage_rate_cc: Optional[Decimal] = None,
        compute_overage_rate_cc: Optional[Decimal] = None,
        bandwidth_overage_rate_cc: Optional[Decimal] = None,
        api_overage_rate_cc: Optional[Decimal] = None,
        volume_discount_threshold_cc: Optional[Decimal] = None,
        custom_discount_rate: Optional[Decimal] = None
    ) -> EnterpriseBillingPlan:
        """Create custom billing plan for enterprise account"""
        
        enterprise_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.id == enterprise_account_id)
            .first()
        )
        
        if not enterprise_account:
            raise ValueError(f"Enterprise account {enterprise_account_id} not found")
        
        # Create custom billing plan
        billing_plan = EnterpriseBillingPlan(
            enterprise_account_id=enterprise_account_id,
            plan_name=plan_name,
            base_monthly_cc=base_monthly_cc,
            included_storage_gb=included_storage_gb,
            included_compute_hours=included_compute_hours,
            included_bandwidth_gb=included_bandwidth_gb,
            included_api_calls=included_api_calls,
            storage_overage_rate_cc=storage_overage_rate_cc,
            compute_overage_rate_cc=compute_overage_rate_cc,
            bandwidth_overage_rate_cc=bandwidth_overage_rate_cc,
            api_overage_rate_cc=api_overage_rate_cc,
            volume_discount_threshold_cc=volume_discount_threshold_cc,
            custom_discount_rate=custom_discount_rate,
            is_active=True
        )
        
        self.db.add(billing_plan)
        self.db.commit()
        
        logger.info(f"Created custom billing plan '{plan_name}' for enterprise account {enterprise_account_id}")
        return billing_plan
    
    async def calculate_enterprise_invoice(
        self,
        enterprise_account_id: str,
        billing_period_start: datetime,
        billing_period_end: datetime
    ) -> Dict:
        """Calculate enterprise invoice for billing period"""
        
        enterprise_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.id == enterprise_account_id)
            .first()
        )
        
        if not enterprise_account:
            raise ValueError(f"Enterprise account {enterprise_account_id} not found")
        
        # Get active billing plan
        billing_plan = (
            self.db.query(EnterpriseBillingPlan)
            .filter(
                and_(
                    EnterpriseBillingPlan.enterprise_account_id == enterprise_account_id,
                    EnterpriseBillingPlan.is_active == True
                )
            )
            .first()
        )
        
        if not billing_plan:
            raise ValueError(f"No active billing plan found for enterprise account {enterprise_account_id}")
        
        # Get usage data for billing period
        usage_data = (
            self.db.query(EnterpriseUsage)
            .filter(
                and_(
                    EnterpriseUsage.enterprise_account_id == enterprise_account_id,
                    EnterpriseUsage.usage_date >= billing_period_start.date(),
                    EnterpriseUsage.usage_date < billing_period_end.date()
                )
            )
            .all()
        )
        
        # Aggregate usage
        total_storage_gb = sum(usage.storage_gb for usage in usage_data)
        total_compute_hours = sum(usage.compute_hours for usage in usage_data)
        total_bandwidth_gb = sum(usage.bandwidth_gb for usage in usage_data)
        total_api_calls = sum(usage.api_calls for usage in usage_data)
        
        # Calculate base charges
        base_charge_cc = billing_plan.base_monthly_cc
        
        # Calculate overage charges
        storage_overage = max(0, total_storage_gb - billing_plan.included_storage_gb)
        compute_overage = max(0, total_compute_hours - billing_plan.included_compute_hours)
        bandwidth_overage = max(0, total_bandwidth_gb - billing_plan.included_bandwidth_gb)
        api_overage = max(0, total_api_calls - billing_plan.included_api_calls)
        
        storage_overage_cc = (
            storage_overage * (billing_plan.storage_overage_rate_cc or Decimal("2.30"))
        )
        compute_overage_cc = (
            compute_overage * (billing_plan.compute_overage_rate_cc or Decimal("4.16"))
        )
        bandwidth_overage_cc = (
            bandwidth_overage * (billing_plan.bandwidth_overage_rate_cc or Decimal("8.50"))
        )
        api_overage_cc = (
            (Decimal(api_overage) / 1000000) * 
            (billing_plan.api_overage_rate_cc or Decimal("350"))
        )
        
        # Calculate subtotal
        subtotal_cc = (
            base_charge_cc + 
            storage_overage_cc + 
            compute_overage_cc + 
            bandwidth_overage_cc + 
            api_overage_cc
        )
        
        # Apply volume discount
        discount_rate = Decimal("0")
        discount_cc = Decimal("0")
        
        if billing_plan.custom_discount_rate:
            discount_rate = billing_plan.custom_discount_rate
        elif billing_plan.volume_discount_threshold_cc and subtotal_cc >= billing_plan.volume_discount_threshold_cc:
            # Find applicable volume discount
            subtotal_usd = subtotal_cc * settings.compute_credits.cc_to_usd_rate
            for threshold, rate in sorted(self.volume_discounts.items(), reverse=True):
                if subtotal_usd >= threshold:
                    discount_rate = rate
                    break
        
        if discount_rate > 0:
            discount_cc = subtotal_cc * discount_rate
        
        total_cc = subtotal_cc - discount_cc
        
        return {
            "enterprise_account_id": enterprise_account_id,
            "billing_period": {
                "start": billing_period_start.date().isoformat(),
                "end": billing_period_end.date().isoformat()
            },
            "usage_summary": {
                "storage_gb": total_storage_gb,
                "compute_hours": total_compute_hours,
                "bandwidth_gb": total_bandwidth_gb,
                "api_calls": total_api_calls
            },
            "included_allowances": {
                "storage_gb": billing_plan.included_storage_gb,
                "compute_hours": billing_plan.included_compute_hours,
                "bandwidth_gb": billing_plan.included_bandwidth_gb,
                "api_calls": billing_plan.included_api_calls
            },
            "overage_usage": {
                "storage_gb": storage_overage,
                "compute_hours": compute_overage,
                "bandwidth_gb": bandwidth_overage,
                "api_calls": api_overage
            },
            "charges": {
                "base_charge_cc": float(base_charge_cc),
                "storage_overage_cc": float(storage_overage_cc),
                "compute_overage_cc": float(compute_overage_cc),
                "bandwidth_overage_cc": float(bandwidth_overage_cc),
                "api_overage_cc": float(api_overage_cc),
                "subtotal_cc": float(subtotal_cc),
                "discount_rate": float(discount_rate * 100),
                "discount_cc": float(discount_cc),
                "total_cc": float(total_cc)
            },
            "rates": {
                "storage_overage_rate_cc": float(billing_plan.storage_overage_rate_cc or Decimal("2.30")),
                "compute_overage_rate_cc": float(billing_plan.compute_overage_rate_cc or Decimal("4.16")),
                "bandwidth_overage_rate_cc": float(billing_plan.bandwidth_overage_rate_cc or Decimal("8.50")),
                "api_overage_rate_per_million_cc": float(billing_plan.api_overage_rate_cc or Decimal("350"))
            }
        }
    
    async def generate_enterprise_invoice(
        self,
        enterprise_account_id: str,
        billing_period_start: datetime,
        billing_period_end: datetime,
        invoice_notes: Optional[str] = None
    ) -> EnterpriseInvoice:
        """Generate formal enterprise invoice"""
        
        # Calculate invoice amounts
        calculation = await self.calculate_enterprise_invoice(
            enterprise_account_id, billing_period_start, billing_period_end
        )
        
        enterprise_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.id == enterprise_account_id)
            .first()
        )
        
        # Generate invoice number
        invoice_number = f"AL-{enterprise_account_id[:8].upper()}-{datetime.utcnow().strftime('%Y%m%d')}"
        
        # Calculate due date based on payment terms
        due_date = self._calculate_due_date(datetime.utcnow(), enterprise_account.payment_terms)
        
        # Create invoice record
        invoice = EnterpriseInvoice(
            enterprise_account_id=enterprise_account_id,
            invoice_number=invoice_number,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            subtotal_cc=Decimal(str(calculation["charges"]["subtotal_cc"])),
            discount_cc=Decimal(str(calculation["charges"]["discount_cc"])),
            total_cc=Decimal(str(calculation["charges"]["total_cc"])),
            usage_data=calculation,
            invoice_notes=invoice_notes,
            due_date=due_date,
            is_paid=False
        )
        
        # Update enterprise account balance
        enterprise_account.current_balance_cc += invoice.total_cc
        
        self.db.add(invoice)
        self.db.commit()
        
        logger.info(
            f"Generated enterprise invoice {invoice_number} for {enterprise_account.company_name}: "
            f"{invoice.total_cc} CC"
        )
        
        return invoice
    
    def _calculate_due_date(self, invoice_date: datetime, payment_terms: PaymentTerms) -> datetime:
        """Calculate invoice due date based on payment terms"""
        
        terms_days = {
            PaymentTerms.PREPAID: 0,
            PaymentTerms.NET_15: 15,
            PaymentTerms.NET_30: 30,
            PaymentTerms.NET_45: 45,
            PaymentTerms.NET_60: 60
        }
        
        days = terms_days.get(payment_terms, 30)
        return invoice_date + timedelta(days=days)
    
    async def process_enterprise_payment(
        self,
        invoice_id: str,
        payment_amount_cc: Decimal,
        payment_reference: Optional[str] = None
    ) -> EnterpriseInvoice:
        """Process payment for enterprise invoice"""
        
        invoice = (
            self.db.query(EnterpriseInvoice)
            .filter(EnterpriseInvoice.id == invoice_id)
            .first()
        )
        
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")
        
        if invoice.is_paid:
            raise ValueError("Invoice is already paid")
        
        enterprise_account = invoice.enterprise_account
        
        try:
            # Create payment transaction
            await self.cc_system.add_credits(
                enterprise_account.user_id,
                payment_amount_cc,
                TransactionType.ENTERPRISE_PAYMENT,
                f"Enterprise payment for invoice {invoice.invoice_number}",
                metadata={
                    "invoice_id": invoice_id,
                    "invoice_number": invoice.invoice_number,
                    "payment_reference": payment_reference,
                    "enterprise_account_id": str(enterprise_account.id)
                }
            )
            
            # Update invoice and account
            if payment_amount_cc >= invoice.total_cc:
                invoice.is_paid = True
                invoice.paid_at = datetime.utcnow()
                invoice.payment_amount_cc = payment_amount_cc
                
                # If overpayment, add to account credit
                if payment_amount_cc > invoice.total_cc:
                    overpayment = payment_amount_cc - invoice.total_cc
                    enterprise_account.account_credit_cc += overpayment
            else:
                # Partial payment
                invoice.payment_amount_cc = payment_amount_cc
            
            # Reduce account balance
            enterprise_account.current_balance_cc -= min(payment_amount_cc, invoice.total_cc)
            
            self.db.commit()
            
            logger.info(
                f"Processed enterprise payment for invoice {invoice.invoice_number}: "
                f"{payment_amount_cc} CC"
            )
            
            return invoice
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to process enterprise payment for invoice {invoice_id}: {str(e)}")
            raise
    
    async def get_enterprise_billing_summary(self, enterprise_account_id: str) -> Dict:
        """Get billing summary for enterprise account"""
        
        enterprise_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.id == enterprise_account_id)
            .first()
        )
        
        if not enterprise_account:
            raise ValueError(f"Enterprise account {enterprise_account_id} not found")
        
        # Get current billing plan
        billing_plan = (
            self.db.query(EnterpriseBillingPlan)
            .filter(
                and_(
                    EnterpriseBillingPlan.enterprise_account_id == enterprise_account_id,
                    EnterpriseBillingPlan.is_active == True
                )
            )
            .first()
        )
        
        # Get recent invoices
        recent_invoices = (
            self.db.query(EnterpriseInvoice)
            .filter(EnterpriseInvoice.enterprise_account_id == enterprise_account_id)
            .order_by(desc(EnterpriseInvoice.created_at))
            .limit(12)
            .all()
        )
        
        # Calculate payment stats
        total_paid = sum(
            invoice.payment_amount_cc or Decimal("0") 
            for invoice in recent_invoices 
            if invoice.is_paid
        )
        
        outstanding_balance = sum(
            invoice.total_cc - (invoice.payment_amount_cc or Decimal("0"))
            for invoice in recent_invoices 
            if not invoice.is_paid
        )
        
        # Get current month usage
        current_month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        current_usage = (
            self.db.query(
                func.sum(EnterpriseUsage.storage_gb).label("storage_gb"),
                func.sum(EnterpriseUsage.compute_hours).label("compute_hours"),
                func.sum(EnterpriseUsage.bandwidth_gb).label("bandwidth_gb"),
                func.sum(EnterpriseUsage.api_calls).label("api_calls")
            )
            .filter(
                and_(
                    EnterpriseUsage.enterprise_account_id == enterprise_account_id,
                    EnterpriseUsage.usage_date >= current_month_start.date()
                )
            )
            .first()
        )
        
        return {
            "account_info": {
                "company_name": enterprise_account.company_name,
                "account_id": enterprise_account_id,
                "billing_contact": enterprise_account.billing_contact_name,
                "payment_terms": enterprise_account.payment_terms.value,
                "billing_cycle": enterprise_account.billing_cycle.value,
                "is_active": enterprise_account.is_active
            },
            "current_billing_plan": {
                "plan_name": billing_plan.plan_name if billing_plan else None,
                "base_monthly_cc": float(billing_plan.base_monthly_cc) if billing_plan else 0,
                "included_allowances": {
                    "storage_gb": billing_plan.included_storage_gb if billing_plan else 0,
                    "compute_hours": billing_plan.included_compute_hours if billing_plan else 0,
                    "bandwidth_gb": billing_plan.included_bandwidth_gb if billing_plan else 0,
                    "api_calls": billing_plan.included_api_calls if billing_plan else 0
                } if billing_plan else None
            },
            "current_month_usage": {
                "storage_gb": float(current_usage.storage_gb or 0),
                "compute_hours": float(current_usage.compute_hours or 0),
                "bandwidth_gb": float(current_usage.bandwidth_gb or 0),
                "api_calls": int(current_usage.api_calls or 0)
            },
            "financial_summary": {
                "current_balance_cc": float(enterprise_account.current_balance_cc),
                "account_credit_cc": float(enterprise_account.account_credit_cc),
                "credit_limit_cc": float(enterprise_account.credit_limit_cc),
                "outstanding_balance_cc": float(outstanding_balance),
                "total_paid_12m_cc": float(total_paid)
            },
            "recent_invoices": [
                {
                    "invoice_id": invoice.id,
                    "invoice_number": invoice.invoice_number,
                    "total_cc": float(invoice.total_cc),
                    "payment_amount_cc": float(invoice.payment_amount_cc or 0),
                    "is_paid": invoice.is_paid,
                    "due_date": invoice.due_date.isoformat(),
                    "created_at": invoice.created_at.isoformat()
                }
                for invoice in recent_invoices
            ]
        }
    
    async def create_enterprise_contract(
        self,
        enterprise_account_id: str,
        contract_terms: Dict,
        effective_date: datetime,
        expiry_date: datetime,
        minimum_commitment_cc: Optional[Decimal] = None,
        committed_discount_rate: Optional[Decimal] = None
    ) -> EnterpriseContract:
        """Create enterprise contract with special terms"""
        
        enterprise_account = (
            self.db.query(EnterpriseAccount)
            .filter(EnterpriseAccount.id == enterprise_account_id)
            .first()
        )
        
        if not enterprise_account:
            raise ValueError(f"Enterprise account {enterprise_account_id} not found")
        
        contract = EnterpriseContract(
            enterprise_account_id=enterprise_account_id,
            contract_terms=contract_terms,
            effective_date=effective_date,
            expiry_date=expiry_date,
            minimum_commitment_cc=minimum_commitment_cc,
            committed_discount_rate=committed_discount_rate,
            is_active=True
        )
        
        self.db.add(contract)
        self.db.commit()
        
        logger.info(f"Created enterprise contract for {enterprise_account.company_name}")
        return contract
    
    async def record_enterprise_usage(
        self,
        enterprise_account_id: str,
        usage_date: datetime,
        storage_gb: Decimal,
        compute_hours: Decimal,
        bandwidth_gb: Decimal,
        api_calls: int
    ) -> EnterpriseUsage:
        """Record daily usage for enterprise account"""
        
        # Get or create usage record for the date
        usage_record = (
            self.db.query(EnterpriseUsage)
            .filter(
                and_(
                    EnterpriseUsage.enterprise_account_id == enterprise_account_id,
                    EnterpriseUsage.usage_date == usage_date.date()
                )
            )
            .first()
        )
        
        if not usage_record:
            usage_record = EnterpriseUsage(
                enterprise_account_id=enterprise_account_id,
                usage_date=usage_date.date()
            )
            self.db.add(usage_record)
        
        # Update usage metrics
        usage_record.storage_gb = storage_gb
        usage_record.compute_hours = compute_hours
        usage_record.bandwidth_gb = bandwidth_gb
        usage_record.api_calls = api_calls
        
        self.db.commit()
        
        logger.debug(
            f"Recorded enterprise usage for {enterprise_account_id} on {usage_date.date()}: "
            f"{storage_gb}GB storage, {compute_hours}h compute, {bandwidth_gb}GB bandwidth, {api_calls} API calls"
        )
        
        return usage_record