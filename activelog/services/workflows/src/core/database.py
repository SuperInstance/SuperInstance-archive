"""
Database models and management for workflow service
"""

import uuid
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Any, Optional, Union

import databases
from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, JSON, 
    ForeignKey, Table, Index, UniqueConstraint, CheckConstraint,
    create_engine, MetaData
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from .config import settings

# Database setup
database = databases.Database(settings.DATABASE_URL)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG
)
metadata = MetaData()
Base = declarative_base(metadata=metadata)

# Enums
class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"

class ExecutionStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"

class TriggerType(Enum):
    WEBHOOK = "webhook"
    SCHEDULE = "schedule"
    EVENT = "event"
    MANUAL = "manual"

class ActionType(Enum):
    HTTP_REQUEST = "http_request"
    EMAIL = "email"
    SLACK = "slack"
    DATABASE = "database"
    FILE_OPERATION = "file_operation"
    WEBHOOK = "webhook"
    CONDITION = "condition"
    DELAY = "delay"
    CUSTOM = "custom"

class IntegrationStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING_AUTH = "pending_auth"

# Association table for workflow tags
workflow_tags = Table(
    'workflow_tags',
    metadata,
    Column('workflow_id', UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='CASCADE')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE')),
    Index('idx_workflow_tags_workflow', 'workflow_id'),
    Index('idx_workflow_tags_tag', 'tag_id')
)

# Models
class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Settings
    settings = Column(JSONB, default=dict)
    quotas = Column(JSONB, default=lambda: {
        "max_workflows": 100,
        "max_executions_per_hour": 1000,
        "max_webhook_endpoints": 50
    })
    
    # Relationships
    workflows = relationship("Workflow", back_populates="owner", cascade="all, delete-orphan")
    integrations = relationship("Integration", back_populates="user", cascade="all, delete-orphan")

class Workflow(Base):
    """Workflow model"""
    __tablename__ = 'workflows'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Workflow configuration
    status = Column(String(20), default=WorkflowStatus.DRAFT.value, index=True)
    version = Column(Integer, default=1)
    trigger_config = Column(JSONB, nullable=False)
    actions = Column(JSONB, nullable=False)  # List of actions/steps
    
    # Execution settings
    timeout_seconds = Column(Integer, default=300)
    max_retries = Column(Integer, default=3)
    retry_delay_seconds = Column(Integer, default=60)
    
    # Scheduling (for scheduled triggers)
    schedule_config = Column(JSONB)  # Cron expression, timezone, etc.
    next_run_at = Column(DateTime, index=True)
    
    # Statistics
    total_executions = Column(Integer, default=0)
    successful_executions = Column(Integer, default=0)
    failed_executions = Column(Integer, default=0)
    last_execution_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Template information
    is_template = Column(Boolean, default=False)
    template_category = Column(String(100))
    template_rating = Column(Integer, default=0)
    
    # Relationships
    owner = relationship("User", back_populates="workflows")
    executions = relationship("WorkflowExecution", back_populates="workflow", cascade="all, delete-orphan")
    webhooks = relationship("WebhookEndpoint", back_populates="workflow", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=workflow_tags, back_populates="workflows")
    
    # Indexes
    __table_args__ = (
        Index('idx_workflows_owner_status', 'owner_id', 'status'),
        Index('idx_workflows_next_run', 'next_run_at'),
        Index('idx_workflows_template', 'is_template', 'template_category'),
    )

class WorkflowExecution(Base):
    """Workflow execution instance"""
    __tablename__ = 'workflow_executions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    
    # Execution details
    status = Column(String(20), default=ExecutionStatus.PENDING.value, index=True)
    trigger_data = Column(JSONB)  # Data that triggered the workflow
    context = Column(JSONB, default=dict)  # Execution context and variables
    
    # Timing
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)  # Execution duration in milliseconds
    
    # Results
    result = Column(JSONB)  # Final result data
    error_message = Column(Text)
    error_details = Column(JSONB)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    retry_count = Column(Integer, default=0)
    parent_execution_id = Column(UUID(as_uuid=True), ForeignKey('workflow_executions.id'))
    
    # Relationships
    workflow = relationship("Workflow", back_populates="executions")
    steps = relationship("ExecutionStep", back_populates="execution", cascade="all, delete-orphan")
    parent_execution = relationship("WorkflowExecution", remote_side=[id])
    
    # Indexes
    __table_args__ = (
        Index('idx_executions_workflow_created', 'workflow_id', 'created_at'),
        Index('idx_executions_status_created', 'status', 'created_at'),
    )

class ExecutionStep(Base):
    """Individual step execution within a workflow"""
    __tablename__ = 'execution_steps'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False)
    
    # Step details
    step_name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)  # action_type
    step_config = Column(JSONB)
    sequence_number = Column(Integer, nullable=False)
    
    # Execution details
    status = Column(String(20), default=ExecutionStatus.PENDING.value)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    
    # Results
    input_data = Column(JSONB)
    output_data = Column(JSONB)
    error_message = Column(Text)
    
    # Relationships
    execution = relationship("WorkflowExecution", back_populates="steps")
    
    # Indexes
    __table_args__ = (
        Index('idx_steps_execution_sequence', 'execution_id', 'sequence_number'),
    )

class WebhookEndpoint(Base):
    """Webhook endpoint for triggering workflows"""
    __tablename__ = 'webhook_endpoints'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    
    # Endpoint details
    endpoint_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255))
    description = Column(Text)
    
    # Security
    secret_token = Column(String(255))  # For webhook signature verification
    allowed_origins = Column(JSONB)  # List of allowed origins
    
    # Configuration
    is_active = Column(Boolean, default=True)
    request_method = Column(String(10), default="POST")
    content_type = Column(String(100), default="application/json")
    
    # Statistics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    last_request_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    workflow = relationship("Workflow", back_populates="webhooks")

class Integration(Base):
    """External service integrations"""
    __tablename__ = 'integrations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Integration details
    service_name = Column(String(100), nullable=False, index=True)
    integration_name = Column(String(255), nullable=False)
    status = Column(String(20), default=IntegrationStatus.ACTIVE.value, index=True)
    
    # Credentials and configuration
    config = Column(JSONB, nullable=False)  # Encrypted configuration
    auth_data = Column(JSONB)  # OAuth tokens, API keys, etc.
    
    # Usage statistics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime)
    
    # Rate limiting
    rate_limit_config = Column(JSONB, default=lambda: {
        "requests_per_minute": 60,
        "requests_per_hour": 1000
    })
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)  # For OAuth tokens
    
    # Relationships
    user = relationship("User", back_populates="integrations")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'service_name', 'integration_name', name='uq_user_service_integration'),
        Index('idx_integrations_user_service', 'user_id', 'service_name'),
    )

class Template(Base):
    """Workflow templates for marketplace"""
    __tablename__ = 'templates'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template details
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    
    # Template data
    trigger_config = Column(JSONB, nullable=False)
    actions = Column(JSONB, nullable=False)
    required_integrations = Column(JSONB, default=list)
    
    # Marketplace data
    author_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    is_public = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    price = Column(Integer, default=0)  # Price in cents, 0 = free
    
    # Statistics
    install_count = Column(Integer, default=0)
    rating_average = Column(Integer, default=0)  # 1-5 scale * 100 for precision
    rating_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    version = Column(String(20), default="1.0.0")
    
    # Content
    readme = Column(Text)
    changelog = Column(Text)
    screenshots = Column(JSONB, default=list)
    
    # Relationships
    author = relationship("User")
    tags = relationship("Tag", secondary="template_tags", back_populates="templates")
    
    # Indexes
    __table_args__ = (
        Index('idx_templates_category_public', 'category', 'is_public'),
        Index('idx_templates_rating', 'rating_average', 'rating_count'),
    )

class Tag(Base):
    """Tags for workflows and templates"""
    __tablename__ = 'tags'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text)
    color = Column(String(7))  # Hex color code
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    workflows = relationship("Workflow", secondary=workflow_tags, back_populates="tags")
    templates = relationship("Template", secondary="template_tags", back_populates="tags")

# Template tags association
template_tags = Table(
    'template_tags',
    metadata,
    Column('template_id', UUID(as_uuid=True), ForeignKey('templates.id', ondelete='CASCADE')),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tags.id', ondelete='CASCADE')),
)

class ScheduledExecution(Base):
    """Scheduled workflow executions"""
    __tablename__ = 'scheduled_executions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflows.id', ondelete='CASCADE'), nullable=False)
    
    # Schedule details
    scheduled_at = Column(DateTime, nullable=False, index=True)
    cron_expression = Column(String(100))
    timezone = Column(String(50), default="UTC")
    
    # Execution details
    status = Column(String(20), default=ExecutionStatus.PENDING.value)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('workflow_executions.id'))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    
    # Relationships
    workflow = relationship("Workflow")
    execution = relationship("WorkflowExecution")
    
    # Indexes
    __table_args__ = (
        Index('idx_scheduled_executions_time_status', 'scheduled_at', 'status'),
    )

# Database manager
class DatabaseManager:
    """Database management operations"""
    
    def __init__(self):
        self.database = database
    
    async def connect(self):
        """Connect to database"""
        await self.database.connect()
    
    async def disconnect(self):
        """Disconnect from database"""
        await self.database.disconnect()
    
    async def create_tables(self):
        """Create all tables"""
        metadata.create_all(engine)
    
    async def drop_tables(self):
        """Drop all tables (use with caution!)"""
        metadata.drop_all(engine)
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> str:
        """Create a new user"""
        query = """
        INSERT INTO users (id, username, email, hashed_password, full_name, settings, quotas)
        VALUES (:id, :username, :email, :hashed_password, :full_name, :settings, :quotas)
        RETURNING id
        """
        user_id = str(uuid.uuid4())
        values = {
            "id": user_id,
            "username": user_data["username"],
            "email": user_data["email"],
            "hashed_password": user_data["hashed_password"],
            "full_name": user_data.get("full_name"),
            "settings": json.dumps(user_data.get("settings", {})),
            "quotas": json.dumps(user_data.get("quotas", {
                "max_workflows": 100,
                "max_executions_per_hour": 1000,
                "max_webhook_endpoints": 50
            }))
        }
        await self.database.execute(query, values)
        return user_id
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = :user_id"
        return await self.database.fetch_one(query, {"user_id": user_id})
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        query = "SELECT * FROM users WHERE username = :username"
        return await self.database.fetch_one(query, {"username": username})
    
    # Workflow operations
    async def create_workflow(self, workflow_data: Dict[str, Any]) -> str:
        """Create a new workflow"""
        query = """
        INSERT INTO workflows (id, name, description, owner_id, status, trigger_config, actions, 
                             timeout_seconds, max_retries, retry_delay_seconds, schedule_config)
        VALUES (:id, :name, :description, :owner_id, :status, :trigger_config, :actions,
                :timeout_seconds, :max_retries, :retry_delay_seconds, :schedule_config)
        RETURNING id
        """
        workflow_id = str(uuid.uuid4())
        values = {
            "id": workflow_id,
            "name": workflow_data["name"],
            "description": workflow_data.get("description"),
            "owner_id": workflow_data["owner_id"],
            "status": workflow_data.get("status", WorkflowStatus.DRAFT.value),
            "trigger_config": json.dumps(workflow_data["trigger_config"]),
            "actions": json.dumps(workflow_data["actions"]),
            "timeout_seconds": workflow_data.get("timeout_seconds", 300),
            "max_retries": workflow_data.get("max_retries", 3),
            "retry_delay_seconds": workflow_data.get("retry_delay_seconds", 60),
            "schedule_config": json.dumps(workflow_data.get("schedule_config")) if workflow_data.get("schedule_config") else None
        }
        await self.database.execute(query, values)
        return workflow_id
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get workflow by ID"""
        query = "SELECT * FROM workflows WHERE id = :workflow_id"
        return await self.database.fetch_one(query, {"workflow_id": workflow_id})
    
    async def list_user_workflows(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List workflows for a user"""
        query = """
        SELECT * FROM workflows 
        WHERE owner_id = :user_id 
        ORDER BY updated_at DESC 
        LIMIT :limit OFFSET :offset
        """
        rows = await self.database.fetch_all(query, {
            "user_id": user_id,
            "limit": limit,
            "offset": offset
        })
        return [dict(row) for row in rows]
    
    # Execution operations
    async def create_execution(self, execution_data: Dict[str, Any]) -> str:
        """Create a new workflow execution"""
        query = """
        INSERT INTO workflow_executions (id, workflow_id, status, trigger_data, context)
        VALUES (:id, :workflow_id, :status, :trigger_data, :context)
        RETURNING id
        """
        execution_id = str(uuid.uuid4())
        values = {
            "id": execution_id,
            "workflow_id": execution_data["workflow_id"],
            "status": execution_data.get("status", ExecutionStatus.PENDING.value),
            "trigger_data": json.dumps(execution_data.get("trigger_data", {})),
            "context": json.dumps(execution_data.get("context", {}))
        }
        await self.database.execute(query, values)
        return execution_id
    
    async def update_execution(self, execution_id: str, updates: Dict[str, Any]) -> bool:
        """Update workflow execution"""
        set_clauses = []
        values = {"execution_id": execution_id}
        
        for field, value in updates.items():
            if field in ["status", "started_at", "completed_at", "duration_ms", "error_message"]:
                set_clauses.append(f"{field} = :{field}")
                values[field] = value
            elif field in ["result", "error_details", "context"]:
                set_clauses.append(f"{field} = :{field}")
                values[field] = json.dumps(value) if value is not None else None
        
        if not set_clauses:
            return False
        
        query = f"UPDATE workflow_executions SET {', '.join(set_clauses)} WHERE id = :execution_id"
        result = await self.database.execute(query, values)
        return result > 0
    
    async def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get execution by ID"""
        query = "SELECT * FROM workflow_executions WHERE id = :execution_id"
        return await self.database.fetch_one(query, {"execution_id": execution_id})

# Initialize database manager
db_manager = DatabaseManager()

# Database initialization
async def init_db():
    """Initialize database connection and tables"""
    await db_manager.connect()
    await db_manager.create_tables()

async def close_db():
    """Close database connection"""
    await db_manager.disconnect()