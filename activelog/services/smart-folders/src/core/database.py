"""
Database models and connection management for Smart Folders Service
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json
import uuid

import asyncpg
from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, 
    Text, JSON, Boolean, Float, ForeignKey, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from databases import Database

from .config import settings

# Database connection
database = Database(settings.database.url)
Base = declarative_base()

class FolderType(str, Enum):
    """Smart folder types"""
    SMART = "smart"
    VIRTUAL = "virtual"
    TEMPLATE = "template"
    AI = "ai"
    SHARED = "shared"
    INHERITED = "inherited"

class RuleOperator(str, Enum):
    """Rule operators"""
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    BETWEEN = "between"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"

class PermissionLevel(str, Enum):
    """Permission levels"""
    READ = "read"
    WRITE = "write"
    SHARE = "share"
    MANAGE = "manage"
    ADMIN = "admin"

class SmartFolder(Base):
    """Smart folder definitions"""
    __tablename__ = "smart_folders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Ownership and organization
    user_id = Column(String, nullable=False, index=True)
    parent_folder_id = Column(String, ForeignKey("smart_folders.id"))
    path = Column(String, nullable=False)  # Virtual path
    
    # Folder configuration
    folder_type = Column(SQLEnum(FolderType), nullable=False, default=FolderType.SMART)
    is_virtual = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    
    # Rules and conditions
    rules = Column(JSON, default=list)  # List of rule definitions
    rule_logic = Column(String, default="AND")  # AND/OR logic for combining rules
    
    # AI and suggestions
    ai_generated = Column(Boolean, default=False)
    ai_confidence = Column(Float)
    ai_model_used = Column(String)
    
    # Template information
    template_id = Column(String)
    template_applied_at = Column(DateTime)
    
    # Inheritance
    inherit_from_parent = Column(Boolean, default=True)
    inheritance_rules = Column(JSON, default=dict)
    
    # Performance and caching
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_evaluated = Column(DateTime)
    item_count = Column(Integer, default=0)
    cache_ttl = Column(Integer, default=300)  # seconds
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    children = relationship("SmartFolder", backref="parent", remote_side=[id])
    items = relationship("SmartFolderItem", back_populates="folder", cascade="all, delete-orphan")
    permissions = relationship("FolderPermission", back_populates="folder", cascade="all, delete-orphan")

class SmartFolderItem(Base):
    """Items contained in smart folders (virtual references)"""
    __tablename__ = "smart_folder_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String, ForeignKey("smart_folders.id"), nullable=False)
    
    # File reference (doesn't move actual files)
    file_id = Column(String, nullable=False)  # Reference to actual file
    file_path = Column(String, nullable=False)  # Original file path
    
    # Item metadata
    file_name = Column(String, nullable=False)
    file_size = Column(Integer)
    file_type = Column(String)
    mime_type = Column(String)
    
    # Rule matching info
    matched_rules = Column(JSON, default=list)  # Which rules matched this item
    match_score = Column(Float, default=1.0)  # Confidence score for match
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow)
    last_verified = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    folder = relationship("SmartFolder", back_populates="items")

class FolderRule(Base):
    """Individual rules for smart folders"""
    __tablename__ = "folder_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String, ForeignKey("smart_folders.id"), nullable=False)
    
    # Rule definition
    name = Column(String, nullable=False)
    description = Column(Text)
    condition_field = Column(String, nullable=False)  # What to check (file_name, size, etc.)
    operator = Column(SQLEnum(RuleOperator), nullable=False)
    value = Column(Text)  # Value to compare against (JSON for complex values)
    
    # Rule behavior
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority rules evaluated first
    
    # Performance tracking
    match_count = Column(Integer, default=0)
    last_matched = Column(DateTime)
    execution_time_ms = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FolderTemplate(Base):
    """Folder templates for common use cases"""
    __tablename__ = "folder_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Template metadata
    category = Column(String, nullable=False)  # work, personal, creative, etc.
    tags = Column(ARRAY(String), default=list)
    
    # Template definition
    structure = Column(JSON, nullable=False)  # Hierarchical folder structure
    default_rules = Column(JSON, default=list)  # Default rules for folders
    
    # Usage and ratings
    usage_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    
    # Ownership
    created_by = Column(String)  # User who created template (null for system templates)
    is_public = Column(Boolean, default=False)
    is_system = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class FolderPermission(Base):
    """Folder sharing permissions"""
    __tablename__ = "folder_permissions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String, ForeignKey("smart_folders.id"), nullable=False)
    
    # Permission details
    user_id = Column(String)  # Specific user (null for group/public permissions)
    group_id = Column(String)  # Group permission
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False)
    
    # Permission behavior
    is_inherited = Column(Boolean, default=False)  # Inherited from parent folder
    expires_at = Column(DateTime)  # Optional expiration
    
    # Granted by
    granted_by = Column(String, nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    folder = relationship("SmartFolder", back_populates="permissions")

class FolderActivity(Base):
    """Activity log for folder operations"""
    __tablename__ = "folder_activity"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    folder_id = Column(String, ForeignKey("smart_folders.id"), nullable=False)
    
    # Activity details
    user_id = Column(String, nullable=False)
    activity_type = Column(String, nullable=False)  # created, updated, shared, etc.
    description = Column(Text)
    
    # Activity metadata
    metadata = Column(JSON, default=dict)
    ip_address = Column(String)
    user_agent = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class AIFolderSuggestion(Base):
    """AI-generated folder suggestions"""
    __tablename__ = "ai_folder_suggestions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    
    # Suggestion details
    suggested_structure = Column(JSON, nullable=False)
    confidence_score = Column(Float, nullable=False)
    reasoning = Column(Text)
    
    # AI model information
    model_used = Column(String, nullable=False)
    model_version = Column(String)
    
    # User interaction
    status = Column(String, default="pending")  # pending, accepted, rejected, modified
    user_feedback = Column(Text)
    applied_at = Column(DateTime)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

# Database operations
class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.database = database
    
    async def create_smart_folder(self, user_id: str, name: str, folder_type: FolderType,
                                 parent_id: Optional[str] = None, **kwargs) -> str:
        """Create a new smart folder"""
        
        folder_id = str(uuid.uuid4())
        
        # Generate path
        if parent_id:
            parent = await self.get_smart_folder(parent_id)
            if parent:
                path = f"{parent['path']}/{name}"
            else:
                path = f"/{name}"
        else:
            path = f"/{name}"
        
        query = """
        INSERT INTO smart_folders (
            id, name, user_id, parent_folder_id, path, folder_type, 
            description, rules, ai_generated, template_id
        ) VALUES (
            :id, :name, :user_id, :parent_id, :path, :folder_type,
            :description, :rules, :ai_generated, :template_id
        )
        """
        
        await self.database.execute(
            query,
            values={
                "id": folder_id,
                "name": name,
                "user_id": user_id,
                "parent_id": parent_id,
                "path": path,
                "folder_type": folder_type,
                "description": kwargs.get("description", ""),
                "rules": json.dumps(kwargs.get("rules", [])),
                "ai_generated": kwargs.get("ai_generated", False),
                "template_id": kwargs.get("template_id")
            }
        )
        
        return folder_id
    
    async def get_smart_folder(self, folder_id: str) -> Optional[Dict[str, Any]]:
        """Get smart folder by ID"""
        
        query = "SELECT * FROM smart_folders WHERE id = :id"
        row = await self.database.fetch_one(query, values={"id": folder_id})
        
        if row:
            result = dict(row)
            # Parse JSON fields
            result['rules'] = json.loads(result['rules']) if result['rules'] else []
            result['inheritance_rules'] = json.loads(result['inheritance_rules']) if result['inheritance_rules'] else {}
            return result
        
        return None
    
    async def get_user_folders(self, user_id: str, folder_type: Optional[FolderType] = None) -> List[Dict[str, Any]]:
        """Get user's smart folders"""
        
        base_query = "SELECT * FROM smart_folders WHERE user_id = :user_id"
        values = {"user_id": user_id}
        
        if folder_type:
            base_query += " AND folder_type = :folder_type"
            values["folder_type"] = folder_type
        
        query = base_query + " ORDER BY created_at DESC"
        
        rows = await self.database.fetch_all(query, values=values)
        
        results = []
        for row in rows:
            result = dict(row)
            result['rules'] = json.loads(result['rules']) if result['rules'] else []
            result['inheritance_rules'] = json.loads(result['inheritance_rules']) if result['inheritance_rules'] else {}
            results.append(result)
        
        return results
    
    async def update_smart_folder(self, folder_id: str, updates: Dict[str, Any]) -> bool:
        """Update smart folder"""
        
        if not updates:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = {"id": folder_id, "updated_at": datetime.utcnow()}
        
        for key, value in updates.items():
            if key in ["rules", "inheritance_rules"] and isinstance(value, (dict, list)):
                value = json.dumps(value)
            set_clauses.append(f"{key} = :{key}")
            values[key] = value
        
        query = f"""
        UPDATE smart_folders 
        SET {', '.join(set_clauses)}, updated_at = :updated_at
        WHERE id = :id
        """
        
        result = await self.database.execute(query, values=values)
        return result > 0
    
    async def delete_smart_folder(self, folder_id: str) -> bool:
        """Delete smart folder and its items"""
        
        # Delete folder items first
        await self.database.execute(
            "DELETE FROM smart_folder_items WHERE folder_id = :folder_id",
            values={"folder_id": folder_id}
        )
        
        # Delete folder rules
        await self.database.execute(
            "DELETE FROM folder_rules WHERE folder_id = :folder_id",
            values={"folder_id": folder_id}
        )
        
        # Delete permissions
        await self.database.execute(
            "DELETE FROM folder_permissions WHERE folder_id = :folder_id",
            values={"folder_id": folder_id}
        )
        
        # Delete the folder
        result = await self.database.execute(
            "DELETE FROM smart_folders WHERE id = :id",
            values={"id": folder_id}
        )
        
        return result > 0
    
    async def add_folder_items(self, folder_id: str, items: List[Dict[str, Any]]) -> bool:
        """Add items to smart folder"""
        
        query = """
        INSERT INTO smart_folder_items (
            id, folder_id, file_id, file_path, file_name, 
            file_size, file_type, mime_type, matched_rules, match_score
        ) VALUES (
            :id, :folder_id, :file_id, :file_path, :file_name,
            :file_size, :file_type, :mime_type, :matched_rules, :match_score
        )
        """
        
        values_list = []
        for item in items:
            values_list.append({
                "id": str(uuid.uuid4()),
                "folder_id": folder_id,
                "file_id": item["file_id"],
                "file_path": item["file_path"],
                "file_name": item["file_name"],
                "file_size": item.get("file_size", 0),
                "file_type": item.get("file_type", ""),
                "mime_type": item.get("mime_type", ""),
                "matched_rules": json.dumps(item.get("matched_rules", [])),
                "match_score": item.get("match_score", 1.0)
            })
        
        await self.database.execute_many(query, values_list)
        
        # Update folder item count
        await self.database.execute(
            "UPDATE smart_folders SET item_count = (SELECT COUNT(*) FROM smart_folder_items WHERE folder_id = :folder_id) WHERE id = :folder_id",
            values={"folder_id": folder_id}
        )
        
        return True
    
    async def get_folder_items(self, folder_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get items in smart folder"""
        
        query = """
        SELECT * FROM smart_folder_items 
        WHERE folder_id = :folder_id 
        ORDER BY added_at DESC 
        LIMIT :limit OFFSET :offset
        """
        
        rows = await self.database.fetch_all(
            query, 
            values={"folder_id": folder_id, "limit": limit, "offset": offset}
        )
        
        results = []
        for row in rows:
            result = dict(row)
            result['matched_rules'] = json.loads(result['matched_rules']) if result['matched_rules'] else []
            results.append(result)
        
        return results
    
    async def create_folder_template(self, name: str, category: str, 
                                   structure: Dict[str, Any], **kwargs) -> str:
        """Create folder template"""
        
        template_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO folder_templates (
            id, name, category, description, structure, default_rules,
            tags, created_by, is_public, is_system
        ) VALUES (
            :id, :name, :category, :description, :structure, :default_rules,
            :tags, :created_by, :is_public, :is_system
        )
        """
        
        await self.database.execute(
            query,
            values={
                "id": template_id,
                "name": name,
                "category": category,
                "description": kwargs.get("description", ""),
                "structure": json.dumps(structure),
                "default_rules": json.dumps(kwargs.get("default_rules", [])),
                "tags": kwargs.get("tags", []),
                "created_by": kwargs.get("created_by"),
                "is_public": kwargs.get("is_public", False),
                "is_system": kwargs.get("is_system", False)
            }
        )
        
        return template_id
    
    async def get_folder_templates(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get folder templates"""
        
        base_query = "SELECT * FROM folder_templates WHERE is_public = true OR is_system = true"
        values = {}
        
        if category:
            base_query += " AND category = :category"
            values["category"] = category
        
        query = base_query + " ORDER BY usage_count DESC, rating DESC"
        
        rows = await self.database.fetch_all(query, values=values)
        
        results = []
        for row in rows:
            result = dict(row)
            result['structure'] = json.loads(result['structure']) if result['structure'] else {}
            result['default_rules'] = json.loads(result['default_rules']) if result['default_rules'] else []
            results.append(result)
        
        return results
    
    async def create_ai_suggestion(self, user_id: str, suggestion: Dict[str, Any], 
                                  model_used: str, confidence: float) -> str:
        """Create AI folder suggestion"""
        
        suggestion_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO ai_folder_suggestions (
            id, user_id, suggested_structure, confidence_score,
            reasoning, model_used, expires_at
        ) VALUES (
            :id, :user_id, :suggested_structure, :confidence_score,
            :reasoning, :model_used, :expires_at
        )
        """
        
        expires_at = datetime.utcnow() + timedelta(days=7)  # Suggestions expire in 7 days
        
        await self.database.execute(
            query,
            values={
                "id": suggestion_id,
                "user_id": user_id,
                "suggested_structure": json.dumps(suggestion["structure"]),
                "confidence_score": confidence,
                "reasoning": suggestion.get("reasoning", ""),
                "model_used": model_used,
                "expires_at": expires_at
            }
        )
        
        return suggestion_id

# Global database manager
db_manager = DatabaseManager()

async def init_db():
    """Initialize database connection"""
    await database.connect()
    
    # Create tables if they don't exist
    engine = create_engine(settings.database.url)
    Base.metadata.create_all(engine)

async def get_db():
    """Database dependency"""
    return db_manager