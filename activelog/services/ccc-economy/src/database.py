from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Numeric, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from datetime import datetime, timedelta
import os
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/activelog_ccc_economy")

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
class CCCTransactionType(enum.Enum):
    EARN = "earn"                    # Earning CCC from sales
    SPEND = "spend"                  # Spending CCC for purchases
    INVEST = "invest"                # Investing CCC in startups
    DIVIDEND = "dividend"            # Receiving dividends
    TRADE = "trade"                  # Trading ownership percentages
    TRANSFER = "transfer"            # Transferring CCC to another wallet
    CONVERT_TO_FIAT = "convert_to_fiat"  # Converting CCC to fiat
    CONVERT_FROM_FIAT = "convert_from_fiat"  # Converting fiat to CCC
    INHERITANCE = "inheritance"      # Inheritance transfer
    VOTE = "vote"                   # Voting with CCC
    TAX_DEFERRED = "tax_deferred"   # Tax-deferred accumulation

class BusinessType(enum.Enum):
    STARTUP = "startup"
    ESTABLISHED = "established"
    COOPERATIVE = "cooperative"
    NON_PROFIT = "non_profit"

class InvestmentStatus(enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    PENDING = "pending"

class VoteType(enum.Enum):
    BUSINESS_DECISION = "business_decision"
    EQUITY_TRADE = "equity_trade"
    DIVIDEND_RATE = "dividend_rate"
    GOVERNANCE = "governance"

class ConversionStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

# Core Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    tax_id = Column(String)  # For tax purposes
    country = Column(String, default="US")
    is_business_owner = Column(Boolean, default=False)
    is_accredited_investor = Column(Boolean, default=False)
    kyc_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class CCCWallet(Base):
    __tablename__ = "ccc_wallets"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    balance = Column(Numeric(20, 8), default=0, nullable=False)  # CCC balance
    locked_balance = Column(Numeric(20, 8), default=0)  # Locked for investments/trades
    tax_deferred_balance = Column(Numeric(20, 8), default=0)  # Tax-deferred CCC
    total_earned = Column(Numeric(20, 8), default=0)  # Lifetime earnings
    total_invested = Column(Numeric(20, 8), default=0)  # Total invested
    wallet_address = Column(String, unique=True, nullable=False)  # Blockchain address
    private_key_hash = Column(String)  # Encrypted private key
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_wallet_user', 'user_id'),)

class CCCTransaction(Base):
    __tablename__ = "ccc_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("ccc_wallets.id"), nullable=False)
    transaction_type = Column(Enum(CCCTransactionType), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    counterparty_wallet_id = Column(UUID(as_uuid=True), ForeignKey("ccc_wallets.id"))
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"))
    investment_id = Column(UUID(as_uuid=True), ForeignKey("ccc_investments.id"))
    description = Column(Text)
    metadata = Column(JSON)
    blockchain_tx_hash = Column(String)  # Blockchain transaction hash
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_transaction_wallet', 'wallet_id'),
        Index('idx_transaction_type', 'transaction_type'),
        Index('idx_transaction_created', 'created_at'),
    )

class Business(Base):
    __tablename__ = "businesses"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    business_type = Column(Enum(BusinessType), default=BusinessType.STARTUP)
    total_equity = Column(Numeric(5, 2), default=100.00)  # Total equity percentage
    valuation_ccc = Column(Numeric(20, 8), default=0)  # Current valuation in CCC
    monthly_revenue_ccc = Column(Numeric(20, 8), default=0)  # Monthly revenue
    dividend_rate = Column(Numeric(5, 4), default=0.1)  # 10% dividend rate
    is_public = Column(Boolean, default=False)  # Available for public investment
    requires_accredited_investors = Column(Boolean, default=False)
    legal_structure = Column(String)  # LLC, Corp, etc.
    incorporation_date = Column(DateTime)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CCCInvestment(Base):
    __tablename__ = "ccc_investments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investor_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    investment_amount_ccc = Column(Numeric(20, 8), nullable=False)
    equity_percentage = Column(Numeric(5, 4), nullable=False)  # Percentage owned
    investment_date = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(InvestmentStatus), default=InvestmentStatus.ACTIVE)
    expected_return_percentage = Column(Numeric(5, 2))
    lock_period_months = Column(Integer, default=12)  # Lock period for investment
    unlock_date = Column(DateTime)
    is_dividend_eligible = Column(Boolean, default=True)
    metadata = Column(JSON)
    
    __table_args__ = (
        Index('idx_investment_investor', 'investor_id'),
        Index('idx_investment_business', 'business_id'),
    )

class EquityTrade(Base):
    __tablename__ = "equity_trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_investment_id = Column(UUID(as_uuid=True), ForeignKey("ccc_investments.id"), nullable=False)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    equity_percentage_traded = Column(Numeric(5, 4), nullable=False)
    price_per_percentage_ccc = Column(Numeric(20, 8), nullable=False)
    total_price_ccc = Column(Numeric(20, 8), nullable=False)
    trade_date = Column(DateTime, default=datetime.utcnow)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime)
    escrow_wallet_id = Column(UUID(as_uuid=True), ForeignKey("ccc_wallets.id"))
    metadata = Column(JSON)

class DividendDistribution(Base):
    __tablename__ = "dividend_distributions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    distribution_date = Column(DateTime, default=datetime.utcnow)
    total_amount_ccc = Column(Numeric(20, 8), nullable=False)
    revenue_period_start = Column(DateTime, nullable=False)
    revenue_period_end = Column(DateTime, nullable=False)
    dividend_rate_used = Column(Numeric(5, 4), nullable=False)
    eligible_investors_count = Column(Integer, default=0)
    is_distributed = Column(Boolean, default=False)
    metadata = Column(JSON)

class DividendPayment(Base):
    __tablename__ = "dividend_payments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    distribution_id = Column(UUID(as_uuid=True), ForeignKey("dividend_distributions.id"), nullable=False)
    investment_id = Column(UUID(as_uuid=True), ForeignKey("ccc_investments.id"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    equity_percentage = Column(Numeric(5, 4), nullable=False)
    dividend_amount_ccc = Column(Numeric(20, 8), nullable=False)
    payment_date = Column(DateTime, default=datetime.utcnow)
    is_paid = Column(Boolean, default=False)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("ccc_transactions.id"))

class BusinessVote(Base):
    __tablename__ = "business_votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    proposal_title = Column(String, nullable=False)
    proposal_description = Column(Text, nullable=False)
    vote_type = Column(Enum(VoteType), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    voting_start_date = Column(DateTime, default=datetime.utcnow)
    voting_end_date = Column(DateTime, nullable=False)
    minimum_ccc_to_vote = Column(Numeric(20, 8), default=0)
    total_ccc_voted = Column(Numeric(20, 8), default=0)
    votes_for = Column(Numeric(20, 8), default=0)
    votes_against = Column(Numeric(20, 8), default=0)
    is_passed = Column(Boolean)
    is_active = Column(Boolean, default=True)
    metadata = Column(JSON)

class VoteCast(Base):
    __tablename__ = "votes_cast"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vote_id = Column(UUID(as_uuid=True), ForeignKey("business_votes.id"), nullable=False)
    voter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ccc_amount_voted = Column(Numeric(20, 8), nullable=False)
    vote_choice = Column(Boolean, nullable=False)  # True = For, False = Against
    vote_date = Column(DateTime, default=datetime.utcnow)
    investment_id = Column(UUID(as_uuid=True), ForeignKey("ccc_investments.id"))  # Associated investment
    voting_power = Column(Numeric(5, 4))  # Calculated voting power based on equity

class CCCConversion(Base):
    __tablename__ = "ccc_conversions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    wallet_id = Column(UUID(as_uuid=True), ForeignKey("ccc_wallets.id"), nullable=False)
    conversion_type = Column(String, nullable=False)  # "ccc_to_fiat" or "fiat_to_ccc"
    ccc_amount = Column(Numeric(20, 8), nullable=False)
    fiat_amount = Column(Numeric(10, 2), nullable=False)
    fiat_currency = Column(String, default="USD")
    exchange_rate = Column(Numeric(10, 6), nullable=False)  # CCC to fiat rate
    status = Column(Enum(ConversionStatus), default=ConversionStatus.PENDING)
    approval_required = Column(Boolean, default=True)
    approved_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    approval_date = Column(DateTime)
    processing_date = Column(DateTime)
    completion_date = Column(DateTime)
    bank_account_info = Column(JSON)  # Encrypted bank details
    conversion_limits_applied = Column(JSON)  # Rate limits, daily limits, etc.
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class TaxDeferredAccount(Base):
    __tablename__ = "tax_deferred_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_type = Column(String, nullable=False)  # "401k_equivalent", "ira_equivalent", etc.
    ccc_balance = Column(Numeric(20, 8), default=0)
    annual_contribution_limit_ccc = Column(Numeric(20, 8), default=10000)  # Annual limit
    current_year_contributions = Column(Numeric(20, 8), default=0)
    total_contributions = Column(Numeric(20, 8), default=0)
    total_earnings = Column(Numeric(20, 8), default=0)
    vesting_schedule = Column(JSON)  # Vesting rules
    withdrawal_rules = Column(JSON)  # Withdrawal rules and penalties
    employer_match_rate = Column(Numeric(5, 4), default=0)  # If applicable
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class CCCInheritance(Base):
    __tablename__ = "ccc_inheritances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deceased_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    beneficiary_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    executor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    total_ccc_inherited = Column(Numeric(20, 8), nullable=False)
    equity_investments_inherited = Column(JSON)  # List of investment IDs
    inheritance_percentage = Column(Numeric(5, 4), default=100.00)  # Percentage of estate
    legal_documentation = Column(JSON)  # Will, death certificate, etc.
    probate_status = Column(String, default="pending")
    transfer_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    tax_implications = Column(JSON)  # Tax calculations
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class CCCMarketplace(Base):
    __tablename__ = "ccc_marketplace"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    equity_percentage_for_sale = Column(Numeric(5, 4), nullable=False)
    asking_price_ccc = Column(Numeric(20, 8), nullable=False)
    minimum_bid_ccc = Column(Numeric(20, 8))
    listing_type = Column(String, default="fixed_price")  # fixed_price, auction
    listing_date = Column(DateTime, default=datetime.utcnow)
    expiration_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    total_bids = Column(Integer, default=0)
    highest_bid_ccc = Column(Numeric(20, 8), default=0)
    description = Column(Text)
    due_diligence_documents = Column(JSON)  # Business documents
    metadata = Column(JSON)

class MarketplaceBid(Base):
    __tablename__ = "marketplace_bids"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("ccc_marketplace.id"), nullable=False)
    bidder_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    bid_amount_ccc = Column(Numeric(20, 8), nullable=False)
    bid_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_winning_bid = Column(Boolean, default=False)
    escrow_amount = Column(Numeric(20, 8))  # Amount held in escrow
    expiration_date = Column(DateTime)
    metadata = Column(JSON)

class BusinessRevenue(Base):
    __tablename__ = "business_revenues"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    revenue_period_start = Column(DateTime, nullable=False)
    revenue_period_end = Column(DateTime, nullable=False)
    total_revenue_ccc = Column(Numeric(20, 8), nullable=False)
    total_expenses_ccc = Column(Numeric(20, 8), default=0)
    net_profit_ccc = Column(Numeric(20, 8), nullable=False)
    dividend_amount_ccc = Column(Numeric(20, 8), default=0)
    revenue_sources = Column(JSON)  # Breakdown by source
    expense_breakdown = Column(JSON)  # Detailed expenses
    is_audited = Column(Boolean, default=False)
    auditor_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class CCCAnalytics(Base):
    __tablename__ = "ccc_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime, nullable=False)
    total_ccc_in_circulation = Column(Numeric(20, 8), default=0)
    total_ccc_locked_investments = Column(Numeric(20, 8), default=0)
    total_businesses_active = Column(Integer, default=0)
    total_active_investors = Column(Integer, default=0)
    daily_transaction_volume = Column(Numeric(20, 8), default=0)
    daily_transaction_count = Column(Integer, default=0)
    average_investment_size = Column(Numeric(20, 8), default=0)
    total_dividends_paid = Column(Numeric(20, 8), default=0)
    ccc_to_fiat_rate = Column(Numeric(10, 6), default=1.0)
    market_cap_equivalent = Column(Numeric(15, 2), default=0)
    top_businesses_by_value = Column(JSON)
    most_active_investors = Column(JSON)
    ecosystem_health_score = Column(Numeric(3, 2), default=5.0)  # 1-10 scale
    metadata = Column(JSON)
    
    __table_args__ = (Index('idx_analytics_date', 'date'),)