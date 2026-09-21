from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Numeric, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from datetime import datetime, timedelta
import os
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/activelog_pricing")

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
class PricingTier(enum.Enum):
    GARAGE = "garage"
    COMMUNITY = "community"
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"

class ComputeLocation(enum.Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    EDGE = "edge"
    MOBILE = "mobile"

class ResourceType(enum.Enum):
    CPU = "cpu"
    GPU = "gpu"
    MEMORY = "memory"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    LLM_INFERENCE = "llm_inference"

# Core Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    membership_tier = Column(Enum(PricingTier), default=PricingTier.STANDARD)
    join_date = Column(DateTime, default=datetime.utcnow)
    is_frontend_owner = Column(Boolean, default=False)
    frontend_id = Column(String)  # Which frontend they own
    location = Column(String)  # Geographic location for pricing
    created_at = Column(DateTime, default=datetime.utcnow)

class PricingConfig(Base):
    __tablename__ = "pricing_configs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_name = Column(String, nullable=False, unique=True)
    base_cost = Column(Numeric(10, 4), nullable=False)
    markup_amount = Column(Numeric(10, 4), default=2.0)  # $2 default markup
    inflation_rate = Column(Numeric(5, 4), default=0.03)  # 3% default
    tier = Column(Enum(PricingTier), default=PricingTier.STANDARD)
    resource_type = Column(Enum(ResourceType), nullable=False)
    effective_from = Column(DateTime, default=datetime.utcnow)
    effective_to = Column(DateTime)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ComputeCost(Base):
    __tablename__ = "compute_costs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    location = Column(Enum(ComputeLocation), nullable=False)
    units_consumed = Column(Numeric(15, 6), nullable=False)
    base_cost = Column(Numeric(10, 4), nullable=False)
    final_cost = Column(Numeric(10, 4), nullable=False)
    pricing_tier = Column(Enum(PricingTier), nullable=False)
    is_off_peak = Column(Boolean, default=False)
    peak_multiplier = Column(Numeric(4, 2), default=1.0)
    session_id = Column(String)
    metadata = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class InflationAdjustment(Base):
    __tablename__ = "inflation_adjustments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    adjustment_date = Column(DateTime, default=datetime.utcnow)
    inflation_rate = Column(Numeric(5, 4), nullable=False)
    adjustment_factor = Column(Numeric(5, 4), nullable=False)
    affected_tiers = Column(ARRAY(String))
    reason = Column(String)
    metadata = Column(JSON)

class PeakPricingSchedule(Base):
    __tablename__ = "peak_pricing_schedules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    timezone = Column(String, default="UTC")
    peak_start_hour = Column(Integer, nullable=False)  # 0-23
    peak_end_hour = Column(Integer, nullable=False)    # 0-23
    peak_days = Column(ARRAY(Integer))  # 0-6 (Monday=0)
    peak_multiplier = Column(Numeric(4, 2), default=1.5)  # 1.5x during peak
    off_peak_multiplier = Column(Numeric(4, 2), default=0.8)  # 0.8x during off-peak
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ServerFarmTier(Base):
    __tablename__ = "server_farm_tiers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier_name = Column(String, nullable=False)
    tier_level = Column(Integer, nullable=False)  # 1=Garage, 2=Community, etc.
    cpu_cost_per_hour = Column(Numeric(8, 4), nullable=False)
    gpu_cost_per_hour = Column(Numeric(8, 4), nullable=False)
    memory_cost_per_gb_hour = Column(Numeric(6, 4), nullable=False)
    storage_cost_per_gb_month = Column(Numeric(6, 4), nullable=False)
    bandwidth_cost_per_gb = Column(Numeric(6, 4), nullable=False)
    availability_sla = Column(Numeric(5, 2))  # 99.9% etc.
    geographic_regions = Column(ARRAY(String))
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RevenueShare(Base):
    __tablename__ = "revenue_shares"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    frontend_id = Column(String, nullable=False)
    transaction_id = Column(String)
    total_amount = Column(Numeric(10, 4), nullable=False)
    frontend_share = Column(Numeric(10, 4), default=1.0)  # $1 to frontend
    activelog_share = Column(Numeric(10, 4), default=1.0)  # $1 to ActiveLog
    revenue_date = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class MembershipPricing(Base):
    __tablename__ = "membership_pricing"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier = Column(Enum(PricingTier), nullable=False)
    base_monthly_price = Column(Numeric(8, 2), nullable=False)
    current_monthly_price = Column(Numeric(8, 2), nullable=False)
    user_count = Column(Integer, default=0)
    discount_factor = Column(Numeric(5, 4), default=1.0)
    min_price = Column(Numeric(8, 2), nullable=False)  # Floor price
    max_discount = Column(Numeric(4, 2), default=0.5)  # Max 50% discount
    effective_from = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class ComputeComparison(Base):
    __tablename__ = "compute_comparisons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    local_cost = Column(Numeric(10, 4), nullable=False)
    cloud_cost = Column(Numeric(10, 4), nullable=False)
    local_specs = Column(JSON)  # Hardware specifications
    cloud_specs = Column(JSON)  # Cloud instance specifications
    performance_ratio = Column(Numeric(4, 2))  # Performance comparison
    recommendation = Column(String)  # local, cloud, hybrid
    comparison_date = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON)

class MobileOptimization(Base):
    __tablename__ = "mobile_optimizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_model = Column(String)
    battery_capacity_mah = Column(Integer)
    current_battery_level = Column(Integer)  # 0-100
    task_complexity = Column(String)  # low, medium, high
    estimated_runtime_minutes = Column(Integer)
    estimated_battery_drain = Column(Integer)  # percentage
    cost_per_minute_local = Column(Numeric(6, 4))
    cost_per_minute_cloud = Column(Numeric(6, 4))
    recommended_location = Column(Enum(ComputeLocation))
    optimization_reason = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class LLMSavings(Base):
    __tablename__ = "llm_savings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    model_name = Column(String, nullable=False)
    standard_cost = Column(Numeric(8, 4), nullable=False)
    optimized_cost = Column(Numeric(8, 4), nullable=False)
    savings_amount = Column(Numeric(8, 4), nullable=False)
    efficiency_factor = Column(Numeric(4, 2))  # How much more efficient
    tokens_processed = Column(Integer)
    optimization_method = Column(String)  # quantization, pruning, etc.
    performance_impact = Column(Numeric(4, 2))  # Quality reduction factor
    created_at = Column(DateTime, default=datetime.utcnow)

class MembershipAllowance(Base):
    __tablename__ = "membership_allowances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tier = Column(Enum(PricingTier), nullable=False)
    monthly_allowance = Column(Numeric(8, 4), nullable=False)  # Credits or dollars
    used_allowance = Column(Numeric(8, 4), default=0)
    remaining_allowance = Column(Numeric(8, 4), nullable=False)
    billing_cycle_start = Column(DateTime, nullable=False)
    billing_cycle_end = Column(DateTime, nullable=False)
    overage_rate = Column(Numeric(6, 4), default=0.01)  # Rate for usage over allowance
    created_at = Column(DateTime, default=datetime.utcnow)

class CostForecast(Base):
    __tablename__ = "cost_forecasts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    forecast_period_days = Column(Integer, default=30)
    historical_avg_daily_cost = Column(Numeric(8, 4))
    projected_monthly_cost = Column(Numeric(10, 2))
    confidence_level = Column(Numeric(4, 2))  # 0.0-1.0
    growth_trend = Column(String)  # increasing, stable, decreasing
    seasonal_factors = Column(JSON)
    forecast_breakdown = Column(JSON)  # By resource type
    recommendations = Column(JSON)
    forecast_date = Column(DateTime, default=datetime.utcnow)