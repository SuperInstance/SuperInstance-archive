from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Numeric, Enum
from sqlalchemy.dialects.postgresql import UUID, JSON, ARRAY
import uuid
from datetime import datetime, timedelta
import os
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/activelog_payment_v2")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Enums
class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class CreditTransactionType(enum.Enum):
    PURCHASE = "purchase"
    USAGE = "usage"
    REFUND = "refund"
    TRANSFER = "transfer"
    BONUS = "bonus"
    AFFILIATE_COMMISSION = "affiliate_commission"
    AUTO_PURCHASE = "auto_purchase"

class InvoiceStatus(enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"

class EscrowStatus(enum.Enum):
    PENDING = "pending"
    FUNDED = "funded"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"

# Core Models
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    billing_email = Column(String, nullable=False)
    tax_id = Column(String)
    address = Column(JSON)  # street, city, state, country, postal_code
    billing_tier = Column(String, default="standard")  # standard, enterprise
    auto_billing_enabled = Column(Boolean, default=False)
    credit_limit = Column(Numeric(15, 2), default=0)
    payment_terms = Column(Integer, default=30)  # days
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    affiliate_code = Column(String, unique=True)
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class ComputeCredit(Base):
    __tablename__ = "compute_credits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    balance = Column(Numeric(15, 4), default=0)
    reserved_balance = Column(Numeric(15, 4), default=0)  # for running jobs
    auto_recharge_enabled = Column(Boolean, default=False)
    auto_recharge_threshold = Column(Numeric(15, 4))
    auto_recharge_amount = Column(Numeric(15, 4))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class CreditTransaction(Base):
    __tablename__ = "credit_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    transaction_type = Column(Enum(CreditTransactionType), nullable=False)
    amount = Column(Numeric(15, 4), nullable=False)
    balance_before = Column(Numeric(15, 4), nullable=False)
    balance_after = Column(Numeric(15, 4), nullable=False)
    description = Column(String)
    metadata = Column(JSON)
    reference_id = Column(String)  # job_id, invoice_id, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

class CreditPricing(Base):
    __tablename__ = "credit_pricing"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    resource_type = Column(String, nullable=False)  # cpu, gpu, storage, bandwidth
    tier = Column(String, default="standard")  # standard, premium, enterprise
    credits_per_unit = Column(Numeric(10, 6), nullable=False)
    unit_name = Column(String, nullable=False)  # hour, GB, request
    region = Column(String, default="global")
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Affiliate System
class AffiliateProgram(Base):
    __tablename__ = "affiliate_programs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    commission_rate = Column(Numeric(5, 4), default=0.1)  # 10%
    tier_level = Column(Integer, default=1)
    lifetime_earnings = Column(Numeric(15, 2), default=0)
    status = Column(String, default="active")  # active, suspended, terminated
    payout_threshold = Column(Numeric(10, 2), default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

class AffiliateCommission(Base):
    __tablename__ = "affiliate_commissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    affiliate_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    transaction_id = Column(UUID(as_uuid=True))
    commission_amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 4), nullable=False)
    original_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="pending")  # pending, paid, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)

# Group Credit Pooling
class CreditPool(Base):
    __tablename__ = "credit_pools"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    total_balance = Column(Numeric(15, 4), default=0)
    allocated_balance = Column(Numeric(15, 4), default=0)
    available_balance = Column(Numeric(15, 4), default=0)
    auto_allocate = Column(Boolean, default=False)
    allocation_rules = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CreditPoolAllocation(Base):
    __tablename__ = "credit_pool_allocations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pool_id = Column(UUID(as_uuid=True), ForeignKey("credit_pools.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    allocated_amount = Column(Numeric(15, 4), nullable=False)
    used_amount = Column(Numeric(15, 4), default=0)
    allocation_date = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime)

# Currency and Tax
class CurrencyRate(Base):
    __tablename__ = "currency_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    from_currency = Column(String(3), nullable=False)
    to_currency = Column(String(3), nullable=False)
    rate = Column(Numeric(20, 10), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TaxRate(Base):
    __tablename__ = "tax_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String, nullable=False)  # US-CA, GB, etc.
    tax_type = Column(String, nullable=False)  # VAT, GST, sales_tax
    rate = Column(Numeric(5, 4), nullable=False)  # 0.2 for 20%
    description = Column(String)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime)

# Invoicing
class Invoice(Base):
    __tablename__ = "invoices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_number = Column(String, unique=True, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    subtotal = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), default=0)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), default="USD")
    due_date = Column(DateTime)
    issued_date = Column(DateTime, default=datetime.utcnow)
    paid_date = Column(DateTime)
    items = Column(JSON)  # invoice line items
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

# Subscriptions
class Subscription(Base):
    __tablename__ = "subscriptions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"))
    plan_name = Column(String, nullable=False)
    credits_per_cycle = Column(Numeric(15, 4), nullable=False)
    cycle_amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    billing_cycle = Column(String, default="monthly")  # monthly, quarterly, annually
    status = Column(String, default="active")  # active, cancelled, suspended
    next_billing_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# Marketplace Escrow
class EscrowTransaction(Base):
    __tablename__ = "escrow_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(15, 4), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(Enum(EscrowStatus), default=EscrowStatus.PENDING)
    marketplace_item_id = Column(String)
    release_conditions = Column(JSON)
    dispute_reason = Column(Text)
    released_at = Column(DateTime)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

# Payment Processing
class PaymentMethod(Base):
    __tablename__ = "payment_methods"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String, nullable=False)  # stripe, paypal
    provider_id = Column(String, nullable=False)  # external payment method ID
    type = Column(String, nullable=False)  # card, bank_account, digital_wallet
    is_default = Column(Boolean, default=False)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)