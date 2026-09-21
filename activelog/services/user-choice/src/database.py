from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, Numeric, Enum, JSON, Index
from sqlalchemy.dialects.postgresql import UUID, ARRAY
import uuid
from datetime import datetime, timedelta
import os
import enum

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/activelog_user_choice")

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
class ChoiceType(enum.Enum):
    FRONTEND_SELECTION = "frontend_selection"
    COMPUTE_ALLOCATION = "compute_allocation"
    LOCAL_VS_CLOUD = "local_vs_cloud"
    SPEED_VS_COST = "speed_vs_cost"
    BATTERY_VS_PERFORMANCE = "battery_vs_performance"
    PRIVACY_VS_CONVENIENCE = "privacy_vs_convenience"
    FEATURE_VS_PRICE = "feature_vs_price"

class ComputeType(enum.Enum):
    LOCAL = "local"
    CLOUD = "cloud"
    EDGE = "edge"
    HYBRID = "hybrid"

class OptimizationTarget(enum.Enum):
    SPEED = "speed"
    COST = "cost"
    BATTERY = "battery"
    PERFORMANCE = "performance"
    PRIVACY = "privacy"
    CONVENIENCE = "convenience"
    BALANCED = "balanced"

class DeviceType(enum.Enum):
    MOBILE = "mobile"
    TABLET = "tablet"
    LAPTOP = "laptop"
    DESKTOP = "desktop"
    SERVER = "server"
    IOT = "iot"

class RewardType(enum.Enum):
    LOYALTY_POINTS = "loyalty_points"
    REFERRAL_BONUS = "referral_bonus"
    EARLY_ADOPTER = "early_adopter"
    ACHIEVEMENT = "achievement"
    USAGE_MILESTONE = "usage_milestone"

class FrontendCategory(enum.Enum):
    PRODUCTIVITY = "productivity"
    ENTERTAINMENT = "entertainment"
    GAMING = "gaming"
    EDUCATION = "education"
    BUSINESS = "business"
    DEVELOPMENT = "development"
    CREATIVE = "creative"

# Core Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    preferences = Column(JSON, default={})  # User preference settings
    choice_history = Column(JSON, default={})  # Historical choices
    optimization_profile = Column(JSON, default={})  # Learned optimization preferences
    device_profiles = Column(JSON, default={})  # Device-specific profiles
    is_early_adopter = Column(Boolean, default=False)
    loyalty_tier = Column(String, default="bronze")  # bronze, silver, gold, platinum
    total_referrals = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class FrontendStatement(Base):
    __tablename__ = "frontend_statements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    frontend_name = Column(String, nullable=False)
    frontend_category = Column(Enum(FrontendCategory), nullable=False)
    statement_text = Column(Text, nullable=False)  # User's statement about their choice
    reasoning = Column(Text)  # Why they chose this frontend
    satisfaction_score = Column(Integer)  # 1-10 satisfaction rating
    usage_frequency = Column(String, default="daily")  # daily, weekly, monthly, rarely
    primary_use_case = Column(String)
    alternative_considered = Column(String)  # What else they considered
    would_recommend = Column(Boolean, default=True)
    statement_date = Column(DateTime, default=datetime.utcnow)
    is_public = Column(Boolean, default=False)  # Can be shared as testimonial
    metadata = Column(JSON, default={})
    
    __table_args__ = (Index('idx_frontend_user', 'user_id'),)

class ComputeAllowance(Base):
    __tablename__ = "compute_allowances"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    monthly_allowance = Column(Numeric(10, 2), nullable=False)  # Monthly compute budget
    current_usage = Column(Numeric(10, 2), default=0)  # Current month usage
    optimization_target = Column(Enum(OptimizationTarget), default=OptimizationTarget.BALANCED)
    auto_optimization_enabled = Column(Boolean, default=True)
    preferred_compute_type = Column(Enum(ComputeType), default=ComputeType.CLOUD)
    cost_sensitivity = Column(Numeric(3, 2), default=0.5)  # 0-1 scale
    performance_priority = Column(Numeric(3, 2), default=0.5)  # 0-1 scale
    allowance_period_start = Column(DateTime, nullable=False)
    allowance_period_end = Column(DateTime, nullable=False)
    overage_protection = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserChoice(Base):
    __tablename__ = "user_choices"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    choice_type = Column(Enum(ChoiceType), nullable=False)
    choice_context = Column(JSON, nullable=False)  # Context of the choice
    options_considered = Column(JSON, nullable=False)  # Available options
    selected_option = Column(JSON, nullable=False)  # Chosen option
    decision_factors = Column(JSON, default={})  # Factors that influenced decision
    confidence_level = Column(Numeric(3, 2), default=0.5)  # 0-1 confidence
    outcome_satisfaction = Column(Integer)  # 1-10 satisfaction with outcome
    time_to_decide_seconds = Column(Integer)  # How long they took to decide
    device_context = Column(JSON, default={})  # Device info during choice
    location_context = Column(String)  # Geographic or network location
    choice_date = Column(DateTime, default=datetime.utcnow)
    is_automated = Column(Boolean, default=False)  # Was choice automated
    metadata = Column(JSON, default={})
    
    __table_args__ = (
        Index('idx_choice_user_type', 'user_id', 'choice_type'),
        Index('idx_choice_date', 'choice_date'),
    )

class OptimizationRecommendation(Base):
    __tablename__ = "optimization_recommendations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    recommendation_type = Column(String, nullable=False)
    current_configuration = Column(JSON, nullable=False)
    recommended_configuration = Column(JSON, nullable=False)
    expected_benefits = Column(JSON, nullable=False)  # Cost savings, performance gains, etc.
    confidence_score = Column(Numeric(3, 2), nullable=False)  # ML model confidence
    implementation_difficulty = Column(String, default="easy")  # easy, medium, hard
    estimated_impact = Column(JSON, default={})  # Projected impact metrics
    recommendation_reason = Column(Text)
    valid_until = Column(DateTime)
    was_accepted = Column(Boolean)
    acceptance_date = Column(DateTime)
    actual_outcome = Column(JSON)  # Actual results if implemented
    created_at = Column(DateTime, default=datetime.utcnow)

class DeviceProfile(Base):
    __tablename__ = "device_profiles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    device_identifier = Column(String, nullable=False)
    device_type = Column(Enum(DeviceType), nullable=False)
    device_name = Column(String)  # User-friendly name
    specifications = Column(JSON, default={})  # Hardware specs
    performance_profile = Column(JSON, default={})  # Benchmarks and capabilities
    battery_profile = Column(JSON, default={})  # Battery capacity and usage patterns
    network_profile = Column(JSON, default={})  # Network capabilities and preferences
    usage_patterns = Column(JSON, default={})  # When and how device is used
    optimization_preferences = Column(JSON, default={})  # Device-specific preferences
    last_seen = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_device_user', 'user_id'),)

class DecisionEngine(Base):
    __tablename__ = "decision_engines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    engine_name = Column(String, nullable=False)
    decision_criteria = Column(JSON, nullable=False)  # Weighted criteria for decisions
    learning_data = Column(JSON, default={})  # ML model data
    success_metrics = Column(JSON, default={})  # Track decision success
    adaptation_rate = Column(Numeric(3, 2), default=0.1)  # How quickly it learns
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

class FeatureComparison(Base):
    __tablename__ = "feature_comparisons"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    comparison_name = Column(String, nullable=False)
    options_compared = Column(JSON, nullable=False)  # List of options with features/prices
    feature_weights = Column(JSON, nullable=False)  # User's feature importance weights
    price_sensitivity = Column(Numeric(3, 2), default=0.5)  # How price-sensitive user is
    selected_option = Column(JSON)  # Final choice
    comparison_result = Column(JSON, default={})  # Detailed analysis results
    satisfaction_rating = Column(Integer)  # Post-decision satisfaction
    would_compare_again = Column(Boolean, default=True)
    comparison_date = Column(DateTime, default=datetime.utcnow)
    metadata = Column(JSON, default={})

class RewardTransaction(Base):
    __tablename__ = "reward_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reward_type = Column(Enum(RewardType), nullable=False)
    points_earned = Column(Integer, nullable=False)
    points_spent = Column(Integer, default=0)
    activity_description = Column(Text)
    trigger_event = Column(String)  # What triggered this reward
    multiplier_applied = Column(Numeric(3, 2), default=1.0)  # Any bonus multipliers
    referral_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))  # If referral-based
    expiration_date = Column(DateTime)  # When points expire
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (Index('idx_reward_user', 'user_id'),)

class LoyaltyTier(Base):
    __tablename__ = "loyalty_tiers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tier_name = Column(String, nullable=False, unique=True)
    tier_level = Column(Integer, nullable=False)  # 1=Bronze, 2=Silver, etc.
    points_required = Column(Integer, nullable=False)
    monthly_allowance_bonus = Column(Numeric(5, 2), default=0)  # Extra compute allowance %
    discount_percentage = Column(Numeric(5, 2), default=0)  # Price discount %
    priority_support = Column(Boolean, default=False)
    early_access_features = Column(Boolean, default=False)
    referral_bonus_multiplier = Column(Numeric(3, 2), default=1.0)
    benefits_description = Column(JSON, default={})
    tier_color = Column(String, default="#888888")  # UI color theme
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ReferralProgram(Base):
    __tablename__ = "referral_programs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    referred_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    referral_code = Column(String, nullable=False, unique=True)
    referral_source = Column(String)  # Where referral came from
    signup_bonus_points = Column(Integer, default=500)
    usage_bonus_points = Column(Integer, default=0)  # Bonus for referred user activity
    referrer_bonus_points = Column(Integer, default=0)
    milestone_bonuses = Column(JSON, default={})  # Bonuses for milestones
    is_active = Column(Boolean, default=True)
    referred_at = Column(DateTime, default=datetime.utcnow)
    activated_at = Column(DateTime)  # When referred user became active
    last_activity = Column(DateTime)
    total_value_generated = Column(Numeric(10, 2), default=0)  # Value from referred user
    metadata = Column(JSON, default={})

class EarlyAdopterBenefit(Base):
    __tablename__ = "early_adopter_benefits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    feature_name = Column(String, nullable=False)
    adoption_date = Column(DateTime, nullable=False)
    benefit_type = Column(String, nullable=False)  # discount, bonus_features, priority_access
    benefit_value = Column(JSON, nullable=False)  # Specific benefit details
    duration_months = Column(Integer)  # How long benefit lasts
    usage_count = Column(Integer, default=0)  # How many times benefit used
    max_usage = Column(Integer)  # Maximum usage limit
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime)
    metadata = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)

class ChoiceAnalytics(Base):
    __tablename__ = "choice_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(DateTime, nullable=False)
    total_users = Column(Integer, default=0)
    total_choices_made = Column(Integer, default=0)
    choice_type_breakdown = Column(JSON, default={})  # Choices by type
    optimization_success_rate = Column(Numeric(5, 2), default=0)  # % of successful optimizations
    average_satisfaction_score = Column(Numeric(3, 2), default=0)
    popular_configurations = Column(JSON, default={})  # Most common user configurations
    cost_savings_generated = Column(Numeric(15, 2), default=0)  # Total cost savings
    performance_improvements = Column(JSON, default={})  # Performance metrics
    user_engagement_metrics = Column(JSON, default={})
    referral_program_stats = Column(JSON, default={})
    loyalty_program_stats = Column(JSON, default={})
    feature_adoption_rates = Column(JSON, default={})
    metadata = Column(JSON, default={})
    
    __table_args__ = (Index('idx_analytics_date', 'date'),)

class OptimizationHistory(Base):
    __tablename__ = "optimization_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    optimization_type = Column(String, nullable=False)
    before_configuration = Column(JSON, nullable=False)
    after_configuration = Column(JSON, nullable=False)
    optimization_trigger = Column(String)  # manual, automated, scheduled
    expected_benefits = Column(JSON, nullable=False)
    actual_benefits = Column(JSON, default={})  # Measured after implementation
    implementation_date = Column(DateTime, default=datetime.utcnow)
    measurement_period_days = Column(Integer, default=7)
    success_score = Column(Numeric(3, 2))  # 0-1 success rating
    user_satisfaction = Column(Integer)  # 1-10 rating
    would_optimize_again = Column(Boolean, default=True)
    rollback_date = Column(DateTime)  # If optimization was rolled back
    metadata = Column(JSON, default={})

class PersonalizationModel(Base):
    __tablename__ = "personalization_models"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    model_type = Column(String, nullable=False)  # choice_prediction, optimization_suggestion, etc.
    model_version = Column(String, default="1.0")
    training_data_points = Column(Integer, default=0)
    model_accuracy = Column(Numeric(5, 4))  # Model accuracy score
    feature_weights = Column(JSON, default={})  # Learned feature importance
    prediction_confidence = Column(Numeric(3, 2), default=0.5)
    last_training_date = Column(DateTime)
    next_training_date = Column(DateTime)
    model_parameters = Column(JSON, default={})  # ML model parameters
    is_active = Column(Boolean, default=True)
    performance_metrics = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow)