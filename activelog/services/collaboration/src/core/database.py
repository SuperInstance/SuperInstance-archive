"""
Database models and connection management for collaboration service
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from enum import Enum

import databases
from sqlalchemy import (
    create_engine, MetaData, Table, Column, String, Integer, DateTime, 
    Boolean, Text, ForeignKey, JSON, Float, Index, UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.sql import func
import uuid

from .config import settings

logger = logging.getLogger(__name__)

# Database connection
database = databases.Database(settings.DATABASE_URL)
metadata = MetaData()

# Enums for database
class WorkspaceRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin" 
    MEMBER = "member"
    VIEWER = "viewer"

class DocumentPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    COMMENT = "comment"
    ADMIN = "admin"

class AnnotationType(str, Enum):
    HIGHLIGHT = "highlight"
    NOTE = "note"
    DRAWING = "drawing"
    STAMP = "stamp"

class ActivityType(str, Enum):
    DOCUMENT_CREATED = "document_created"
    DOCUMENT_UPDATED = "document_updated"
    DOCUMENT_DELETED = "document_deleted"
    ANNOTATION_ADDED = "annotation_added"
    ANNOTATION_UPDATED = "annotation_updated"
    ANNOTATION_DELETED = "annotation_deleted"
    COMMENT_ADDED = "comment_added"
    COMMENT_UPDATED = "comment_updated"
    COMMENT_DELETED = "comment_deleted"
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    VERSION_CREATED = "version_created"

# Core tables
workspaces = Table(
    "workspaces",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("name", String(255), nullable=False),
    Column("description", Text),
    Column("owner_id", String(255), nullable=False, index=True),
    Column("settings", JSON, default={}),
    Column("is_active", Boolean, default=True),
    Column("last_activity_at", DateTime(timezone=True), default=func.now()),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("updated_at", DateTime(timezone=True), default=func.now(), onupdate=func.now()),
    Index("idx_workspaces_owner", "owner_id"),
    Index("idx_workspaces_activity", "last_activity_at"),
)

workspace_members = Table(
    "workspace_members",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String(255), nullable=False),
    Column("role", String(50), nullable=False, default=WorkspaceRole.MEMBER),
    Column("invited_by", String(255)),
    Column("invited_at", DateTime(timezone=True), default=func.now()),
    Column("joined_at", DateTime(timezone=True)),
    Column("is_active", Boolean, default=True),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("updated_at", DateTime(timezone=True), default=func.now(), onupdate=func.now()),
    UniqueConstraint("workspace_id", "user_id", name="unique_workspace_user"),
    Index("idx_workspace_members_user", "user_id"),
    Index("idx_workspace_members_workspace", "workspace_id"),
    CheckConstraint("role IN ('owner', 'admin', 'member', 'viewer')", name="valid_role"),
)

documents = Table(
    "documents",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("file_path", String(1000), nullable=False),
    Column("file_type", String(50), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("mime_type", String(100)),
    Column("checksum", String(64)),
    Column("owner_id", String(255), nullable=False),
    Column("current_version_id", UUID(as_uuid=True)),
    Column("is_locked", Boolean, default=False),
    Column("locked_by", String(255)),
    Column("locked_at", DateTime(timezone=True)),
    Column("metadata", JSON, default={}),
    Column("tags", ARRAY(String), default=[]),
    Column("last_accessed_at", DateTime(timezone=True), default=func.now()),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("updated_at", DateTime(timezone=True), default=func.now(), onupdate=func.now()),
    Index("idx_documents_workspace", "workspace_id"),
    Index("idx_documents_owner", "owner_id"),
    Index("idx_documents_type", "file_type"),
    Index("idx_documents_tags", "tags", postgresql_using="gin"),
)

document_versions = Table(
    "document_versions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("version_number", Integer, nullable=False),
    Column("file_path", String(1000), nullable=False),
    Column("file_size", Integer, nullable=False),
    Column("checksum", String(64), nullable=False),
    Column("created_by", String(255), nullable=False),
    Column("change_summary", Text),
    Column("metadata", JSON, default={}),
    Column("is_auto_version", Boolean, default=False),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    UniqueConstraint("document_id", "version_number", name="unique_document_version"),
    Index("idx_document_versions_document", "document_id"),
    Index("idx_document_versions_created", "created_at"),
)

annotations = Table(
    "annotations",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("version_id", UUID(as_uuid=True), ForeignKey("document_versions.id")),
    Column("created_by", String(255), nullable=False),
    Column("annotation_type", String(50), nullable=False),
    Column("content", Text),
    Column("position_data", JSON, nullable=False),  # Page, coordinates, selection range
    Column("style_data", JSON, default={}),  # Color, size, font, etc.
    Column("metadata", JSON, default={}),
    Column("is_private", Boolean, default=False),
    Column("is_resolved", Boolean, default=False),
    Column("resolved_by", String(255)),
    Column("resolved_at", DateTime(timezone=True)),
    Column("thread_id", UUID(as_uuid=True)),  # For grouped annotations
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("updated_at", DateTime(timezone=True), default=func.now(), onupdate=func.now()),
    Index("idx_annotations_document", "document_id"),
    Index("idx_annotations_creator", "created_by"),
    Index("idx_annotations_type", "annotation_type"),
    Index("idx_annotations_thread", "thread_id"),
    CheckConstraint("annotation_type IN ('highlight', 'note', 'drawing', 'stamp')", name="valid_annotation_type"),
)

comments = Table(
    "comments",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("annotation_id", UUID(as_uuid=True), ForeignKey("annotations.id", ondelete="CASCADE")),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("parent_comment_id", UUID(as_uuid=True), ForeignKey("comments.id", ondelete="CASCADE")),
    Column("created_by", String(255), nullable=False),
    Column("content", Text, nullable=False),
    Column("mentions", ARRAY(String), default=[]),  # @user mentions
    Column("is_edited", Boolean, default=False),
    Column("edited_at", DateTime(timezone=True)),
    Column("is_deleted", Boolean, default=False),
    Column("deleted_at", DateTime(timezone=True)),
    Column("metadata", JSON, default={}),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("updated_at", DateTime(timezone=True), default=func.now(), onupdate=func.now()),
    Index("idx_comments_annotation", "annotation_id"),
    Index("idx_comments_document", "document_id"),
    Index("idx_comments_creator", "created_by"),
    Index("idx_comments_parent", "parent_comment_id"),
    Index("idx_comments_mentions", "mentions", postgresql_using="gin"),
)

activity_feed = Table(
    "activity_feed",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")),
    Column("actor_id", String(255), nullable=False),
    Column("activity_type", String(100), nullable=False),
    Column("target_id", UUID(as_uuid=True)),  # ID of affected resource
    Column("target_type", String(50)),  # Type of affected resource
    Column("details", JSON, default={}),
    Column("metadata", JSON, default={}),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Index("idx_activity_workspace", "workspace_id"),
    Index("idx_activity_document", "document_id"),
    Index("idx_activity_actor", "actor_id"),
    Index("idx_activity_type", "activity_type"),
    Index("idx_activity_created", "created_at"),
)

notifications = Table(
    "notifications",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("recipient_id", String(255), nullable=False),
    Column("workspace_id", UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE")),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE")),
    Column("activity_id", UUID(as_uuid=True), ForeignKey("activity_feed.id", ondelete="CASCADE")),
    Column("notification_type", String(100), nullable=False),
    Column("title", String(255), nullable=False),
    Column("message", Text, nullable=False),
    Column("is_read", Boolean, default=False),
    Column("read_at", DateTime(timezone=True)),
    Column("metadata", JSON, default={}),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Index("idx_notifications_recipient", "recipient_id"),
    Index("idx_notifications_workspace", "workspace_id"),
    Index("idx_notifications_read", "is_read"),
    Index("idx_notifications_created", "created_at"),
)

document_permissions = Table(
    "document_permissions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", String(255), nullable=False),
    Column("permission", String(50), nullable=False),
    Column("granted_by", String(255), nullable=False),
    Column("granted_at", DateTime(timezone=True), default=func.now()),
    Column("expires_at", DateTime(timezone=True)),
    Column("is_active", Boolean, default=True),
    Column("metadata", JSON, default={}),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    UniqueConstraint("document_id", "user_id", name="unique_document_user_permission"),
    Index("idx_document_permissions_document", "document_id"),
    Index("idx_document_permissions_user", "user_id"),
    Index("idx_document_permissions_permission", "permission"),
    CheckConstraint("permission IN ('read', 'write', 'comment', 'admin')", name="valid_permission"),
)

guest_access_tokens = Table(
    "guest_access_tokens",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("token", String(255), nullable=False, unique=True),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("permissions", ARRAY(String), nullable=False),  # ['read', 'comment']
    Column("created_by", String(255), nullable=False),
    Column("guest_email", String(255)),
    Column("guest_name", String(255)),
    Column("max_uses", Integer, default=1),
    Column("current_uses", Integer, default=0),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("is_active", Boolean, default=True),
    Column("metadata", JSON, default={}),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Column("last_used_at", DateTime(timezone=True)),
    Index("idx_guest_tokens_token", "token"),
    Index("idx_guest_tokens_document", "document_id"),
    Index("idx_guest_tokens_expires", "expires_at"),
    Index("idx_guest_tokens_active", "is_active"),
)

guest_sessions = Table(
    "guest_sessions",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("token_id", UUID(as_uuid=True), ForeignKey("guest_access_tokens.id", ondelete="CASCADE"), nullable=False),
    Column("session_id", String(255), nullable=False, unique=True),
    Column("document_id", UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
    Column("guest_ip", String(45)),  # IPv6 support
    Column("guest_user_agent", Text),
    Column("is_active", Boolean, default=True),
    Column("last_activity_at", DateTime(timezone=True), default=func.now()),
    Column("created_at", DateTime(timezone=True), default=func.now()),
    Index("idx_guest_sessions_token", "token_id"),
    Index("idx_guest_sessions_session", "session_id"),
    Index("idx_guest_sessions_document", "document_id"),
    Index("idx_guest_sessions_active", "is_active"),
)

# Database manager class
class DatabaseManager:
    def __init__(self):
        self.database = database
        self.engine = create_engine(settings.DATABASE_URL, echo=settings.DEBUG)
        
    async def connect(self):
        """Connect to database"""
        try:
            await self.database.connect()
            logger.info("Connected to collaboration database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
            
    async def disconnect(self):
        """Disconnect from database"""
        try:
            await self.database.disconnect()
            logger.info("Disconnected from collaboration database")
        except Exception as e:
            logger.error(f"Failed to disconnect from database: {e}")
            
    async def create_tables(self):
        """Create all tables"""
        try:
            metadata.create_all(self.engine)
            logger.info("Created collaboration database tables")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
            
    async def drop_tables(self):
        """Drop all tables (development only)"""
        try:
            metadata.drop_all(self.engine)
            logger.info("Dropped collaboration database tables")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    # Workspace operations
    async def create_workspace(self, workspace_data: Dict[str, Any]) -> str:
        """Create a new workspace"""
        try:
            workspace_id = uuid.uuid4()
            query = workspaces.insert().values(
                id=workspace_id,
                **workspace_data
            )
            await self.database.execute(query)
            
            # Add owner as workspace member
            member_query = workspace_members.insert().values(
                workspace_id=workspace_id,
                user_id=workspace_data["owner_id"],
                role=WorkspaceRole.OWNER,
                joined_at=func.now()
            )
            await self.database.execute(member_query)
            
            logger.info(f"Created workspace {workspace_id}")
            return str(workspace_id)
            
        except Exception as e:
            logger.error(f"Failed to create workspace: {e}")
            raise
    
    async def get_workspace(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Get workspace by ID"""
        try:
            query = workspaces.select().where(workspaces.c.id == workspace_id)
            result = await self.database.fetch_one(query)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Failed to get workspace {workspace_id}: {e}")
            raise
    
    # Document operations
    async def create_document(self, document_data: Dict[str, Any]) -> str:
        """Create a new document"""
        try:
            document_id = uuid.uuid4()
            
            # Create initial version
            version_id = uuid.uuid4()
            version_query = document_versions.insert().values(
                id=version_id,
                document_id=document_id,
                version_number=1,
                file_path=document_data["file_path"],
                file_size=document_data["file_size"],
                checksum=document_data["checksum"],
                created_by=document_data["owner_id"],
                change_summary="Initial version"
            )
            await self.database.execute(version_query)
            
            # Create document
            query = documents.insert().values(
                id=document_id,
                current_version_id=version_id,
                **document_data
            )
            await self.database.execute(query)
            
            logger.info(f"Created document {document_id}")
            return str(document_id)
            
        except Exception as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    # Annotation operations
    async def create_annotation(self, annotation_data: Dict[str, Any]) -> str:
        """Create a new annotation"""
        try:
            annotation_id = uuid.uuid4()
            query = annotations.insert().values(
                id=annotation_id,
                **annotation_data
            )
            await self.database.execute(query)
            
            logger.info(f"Created annotation {annotation_id}")
            return str(annotation_id)
            
        except Exception as e:
            logger.error(f"Failed to create annotation: {e}")
            raise
    
    # Activity feed operations
    async def log_activity(self, activity_data: Dict[str, Any]) -> str:
        """Log activity to feed"""
        try:
            activity_id = uuid.uuid4()
            query = activity_feed.insert().values(
                id=activity_id,
                **activity_data
            )
            await self.database.execute(query)
            
            return str(activity_id)
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            raise
    
    async def get_activity_feed(self, workspace_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get activity feed for workspace"""
        try:
            query = (activity_feed.select()
                    .where(activity_feed.c.workspace_id == workspace_id)
                    .order_by(activity_feed.c.created_at.desc())
                    .limit(limit)
                    .offset(offset))
            
            results = await self.database.fetch_all(query)
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get activity feed: {e}")
            raise
    
    # Guest access operations
    async def create_guest_token(self, token_data: Dict[str, Any]) -> str:
        """Create guest access token"""
        try:
            token_id = uuid.uuid4()
            query = guest_access_tokens.insert().values(
                id=token_id,
                **token_data
            )
            await self.database.execute(query)
            
            logger.info(f"Created guest token {token_id}")
            return str(token_id)
            
        except Exception as e:
            logger.error(f"Failed to create guest token: {e}")
            raise
    
    async def validate_guest_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate guest access token"""
        try:
            query = (guest_access_tokens.select()
                    .where(guest_access_tokens.c.token == token)
                    .where(guest_access_tokens.c.is_active == True)
                    .where(guest_access_tokens.c.expires_at > func.now()))
            
            result = await self.database.fetch_one(query)
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to validate guest token: {e}")
            raise

# Create global database manager instance
db_manager = DatabaseManager()

async def init_db():
    """Initialize database connection and create tables"""
    await db_manager.connect()
    await db_manager.create_tables()

async def close_db():
    """Close database connection"""
    await db_manager.disconnect()