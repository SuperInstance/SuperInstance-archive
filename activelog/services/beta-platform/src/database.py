from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/activelog_beta")

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

# Base models
class User(Base):
    __tablename__ = "beta_users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_beta_tester = Column(Boolean, default=True)
    beta_tier = Column(String, default="basic")  # basic, premium, enterprise
    reward_points = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class Feedback(Base):
    __tablename__ = "feedback"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    category = Column(String)  # ui, performance, feature, general
    rating = Column(Integer)  # 1-5 stars
    title = Column(String, nullable=False)
    description = Column(Text)
    metadata = Column(JSON)  # browser, device, etc.
    status = Column(String, default="open")  # open, reviewed, implemented, closed
    priority = Column(String, default="medium")  # low, medium, high, critical
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class BugReport(Base):
    __tablename__ = "bug_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    steps_to_reproduce = Column(Text)
    expected_behavior = Column(Text)
    actual_behavior = Column(Text)
    severity = Column(String, default="medium")  # low, medium, high, critical
    status = Column(String, default="open")  # open, investigating, fixed, closed
    screenshot_paths = Column(JSON)  # array of screenshot file paths
    browser_info = Column(JSON)
    device_info = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class FeatureRequest(Base):
    __tablename__ = "feature_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String)
    priority = Column(String, default="medium")
    status = Column(String, default="proposed")  # proposed, approved, in_progress, completed, rejected
    votes = Column(Integer, default=0)
    implementation_effort = Column(String)  # small, medium, large
    business_value = Column(String)  # low, medium, high
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class FeatureVote(Base):
    __tablename__ = "feature_votes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    feature_request_id = Column(UUID(as_uuid=True), ForeignKey("feature_requests.id"))
    vote_type = Column(String)  # upvote, downvote
    created_at = Column(DateTime, default=datetime.utcnow)

class RewardTransaction(Base):
    __tablename__ = "reward_transactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    action_type = Column(String)  # feedback, bug_report, feature_request, testing_session
    points_earned = Column(Integer)
    description = Column(String)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

class RolloutStage(Base):
    __tablename__ = "rollout_stages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    feature_flags = Column(JSON)  # feature flags for this stage
    user_percentage = Column(Float, default=0.0)  # percentage of users in this stage
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class UserRolloutAssignment(Base):
    __tablename__ = "user_rollout_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    stage_id = Column(UUID(as_uuid=True), ForeignKey("rollout_stages.id"))
    assigned_at = Column(DateTime, default=datetime.utcnow)
    
class RolloutMetrics(Base):
    __tablename__ = "rollout_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stage_id = Column(UUID(as_uuid=True), ForeignKey("rollout_stages.id"))
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float)
    metadata = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class CrashReport(Base):
    __tablename__ = "crash_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    error_type = Column(String)
    error_message = Column(Text)
    stack_trace = Column(Text)
    browser_info = Column(JSON)
    device_info = Column(JSON)
    url = Column(String)
    user_agent = Column(String)
    session_id = Column(String)
    severity = Column(String, default="medium")  # low, medium, high, critical
    status = Column(String, default="open")  # open, investigating, fixed, closed
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    metric_type = Column(String)  # page_load, api_response, memory_usage, etc.
    metric_value = Column(Float)
    url = Column(String)
    browser_info = Column(JSON)
    device_info = Column(JSON)
    session_id = Column(String)
    metadata = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.utcnow)

class UsageEvent(Base):
    __tablename__ = "usage_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    event_type = Column(String)  # page_view, button_click, feature_usage, etc.
    event_data = Column(JSON)
    url = Column(String)
    session_id = Column(String)
    browser_info = Column(JSON)
    device_info = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ABTest(Base):
    __tablename__ = "ab_tests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(Text)
    hypothesis = Column(Text)
    variants = Column(JSON)  # [{"name": "control", "config": {...}}, ...]
    traffic_allocation = Column(JSON)  # {"control": 0.5, "variant_a": 0.5}
    target_users = Column(JSON)  # user targeting criteria
    success_metrics = Column(JSON)  # metrics to track
    status = Column(String, default="draft")  # draft, running, paused, completed
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ABTestAssignment(Base):
    __tablename__ = "ab_test_assignments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"))
    variant = Column(String)
    assigned_at = Column(DateTime, default=datetime.utcnow)

class ABTestResult(Base):
    __tablename__ = "ab_test_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("ab_tests.id"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("beta_users.id"))
    variant = Column(String)
    metric_name = Column(String)
    metric_value = Column(Float)
    metadata = Column(JSON)
    recorded_at = Column(DateTime, default=datetime.utcnow)