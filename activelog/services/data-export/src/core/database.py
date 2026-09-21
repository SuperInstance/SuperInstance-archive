"""
Database models and connection management for Data Export Service
"""

import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import json

import asyncpg
from sqlalchemy import (
    create_engine, Column, String, Integer, DateTime, 
    Text, JSON, Boolean, Float, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from databases import Database
import uuid

from .config import settings

# Database connection
database = Database(settings.database.url)
Base = declarative_base()

class ExportStatus(str, Enum):
    """Export job status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ExportType(str, Enum):
    """Export format types"""
    PDF = "pdf"
    ZIP = "zip"
    TAR_GZ = "tar.gz"
    WEBSITE = "website"
    PHOTOBOOK = "photobook" 
    GDPR = "gdpr"
    EXCEL = "excel"
    JSON = "json"
    CSV = "csv"

class ExportJob(Base):
    """Export job tracking"""
    __tablename__ = "export_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    export_type = Column(String, nullable=False)
    status = Column(String, default=ExportStatus.PENDING, index=True)
    
    # Export configuration
    config = Column(JSON, nullable=False)
    filters = Column(JSON)  # File filters, date ranges, etc.
    
    # Progress tracking
    total_items = Column(Integer, default=0)
    processed_items = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    current_operation = Column(String)
    
    # File information
    output_filename = Column(String)
    output_path = Column(String)
    file_size = Column(Integer)  # bytes
    
    # Metadata
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Cloud upload info
    cloud_provider = Column(String)
    cloud_path = Column(String)
    cloud_share_url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExportItem(Base):
    """Individual items in an export"""
    __tablename__ = "export_items"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    export_job_id = Column(String, ForeignKey("export_jobs.id"), nullable=False)
    
    # Source file information
    source_path = Column(String, nullable=False)
    source_type = Column(String)  # file, folder, metadata
    file_size = Column(Integer)
    
    # Processing status
    status = Column(String, default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Output information
    output_path = Column(String)
    included = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)

class UserExportPreferences(Base):
    """User export preferences and settings"""
    __tablename__ = "user_export_preferences"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, unique=True, index=True)
    
    # Default settings
    default_export_format = Column(String, default="zip")
    include_metadata = Column(Boolean, default=True)
    compress_images = Column(Boolean, default=True)
    
    # PDF preferences
    pdf_quality = Column(String, default="high")
    pdf_include_thumbnails = Column(Boolean, default=True)
    
    # Archive preferences
    compression_level = Column(Integer, default=6)
    
    # Cloud preferences
    preferred_cloud_provider = Column(String)
    auto_upload_to_cloud = Column(Boolean, default=False)
    
    # GDPR settings
    gdpr_include_deleted = Column(Boolean, default=True)
    gdpr_include_system_logs = Column(Boolean, default=False)
    
    # Notification preferences
    email_on_completion = Column(Boolean, default=True)
    webhook_url = Column(String)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ExportTemplate(Base):
    """Reusable export templates"""
    __tablename__ = "export_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    export_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    filters = Column(JSON)
    
    is_public = Column(Boolean, default=False)
    usage_count = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Database operations
class DatabaseManager:
    """Database operations manager"""
    
    def __init__(self):
        self.database = database
    
    async def create_export_job(self, user_id: str, export_type: str, 
                               config: Dict[str, Any], filters: Optional[Dict[str, Any]] = None) -> str:
        """Create a new export job"""
        
        job_id = str(uuid.uuid4())
        
        query = """
        INSERT INTO export_jobs (id, user_id, export_type, config, filters, status)
        VALUES (:id, :user_id, :export_type, :config, :filters, :status)
        """
        
        await self.database.execute(
            query, 
            values={
                "id": job_id,
                "user_id": user_id,
                "export_type": export_type,
                "config": json.dumps(config),
                "filters": json.dumps(filters) if filters else None,
                "status": ExportStatus.PENDING
            }
        )
        
        return job_id
    
    async def get_export_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get export job by ID"""
        
        query = "SELECT * FROM export_jobs WHERE id = :id"
        row = await self.database.fetch_one(query, values={"id": job_id})
        
        if row:
            result = dict(row)
            # Parse JSON fields
            result['config'] = json.loads(result['config']) if result['config'] else {}
            result['filters'] = json.loads(result['filters']) if result['filters'] else {}
            return result
        
        return None
    
    async def update_export_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update export job"""
        
        if not updates:
            return False
        
        # Build dynamic update query
        set_clauses = []
        values = {"id": job_id, "updated_at": datetime.utcnow()}
        
        for key, value in updates.items():
            if key in ["config", "filters"] and isinstance(value, dict):
                value = json.dumps(value)
            set_clauses.append(f"{key} = :{key}")
            values[key] = value
        
        query = f"""
        UPDATE export_jobs 
        SET {', '.join(set_clauses)}, updated_at = :updated_at
        WHERE id = :id
        """
        
        result = await self.database.execute(query, values=values)
        return result > 0
    
    async def get_user_export_jobs(self, user_id: str, limit: int = 50, 
                                  status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user's export jobs"""
        
        base_query = "SELECT * FROM export_jobs WHERE user_id = :user_id"
        values = {"user_id": user_id, "limit": limit}
        
        if status:
            base_query += " AND status = :status"
            values["status"] = status
        
        query = base_query + " ORDER BY created_at DESC LIMIT :limit"
        
        rows = await self.database.fetch_all(query, values=values)
        
        results = []
        for row in rows:
            result = dict(row)
            result['config'] = json.loads(result['config']) if result['config'] else {}
            result['filters'] = json.loads(result['filters']) if result['filters'] else {}
            results.append(result)
        
        return results
    
    async def create_export_items(self, job_id: str, items: List[Dict[str, Any]]) -> bool:
        """Bulk create export items"""
        
        query = """
        INSERT INTO export_items (id, export_job_id, source_path, source_type, file_size)
        VALUES (:id, :export_job_id, :source_path, :source_type, :file_size)
        """
        
        values_list = []
        for item in items:
            values_list.append({
                "id": str(uuid.uuid4()),
                "export_job_id": job_id,
                "source_path": item.get("source_path"),
                "source_type": item.get("source_type", "file"),
                "file_size": item.get("file_size", 0)
            })
        
        await self.database.execute_many(query, values_list)
        return True
    
    async def get_export_items(self, job_id: str) -> List[Dict[str, Any]]:
        """Get items for export job"""
        
        query = "SELECT * FROM export_items WHERE export_job_id = :job_id ORDER BY created_at"
        rows = await self.database.fetch_all(query, values={"job_id": job_id})
        
        return [dict(row) for row in rows]
    
    async def update_export_item_status(self, item_id: str, status: str, 
                                       error_message: Optional[str] = None) -> bool:
        """Update export item status"""
        
        updates = {
            "status": status,
            "processed_at": datetime.utcnow()
        }
        
        if error_message:
            updates["error_message"] = error_message
        
        set_clauses = []
        values = {"id": item_id}
        
        for key, value in updates.items():
            set_clauses.append(f"{key} = :{key}")
            values[key] = value
        
        query = f"UPDATE export_items SET {', '.join(set_clauses)} WHERE id = :id"
        
        result = await self.database.execute(query, values=values)
        return result > 0
    
    async def get_user_preferences(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user export preferences"""
        
        query = "SELECT * FROM user_export_preferences WHERE user_id = :user_id"
        row = await self.database.fetch_one(query, values={"user_id": user_id})
        
        return dict(row) if row else None
    
    async def save_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Save or update user preferences"""
        
        # Check if preferences exist
        existing = await self.get_user_preferences(user_id)
        
        if existing:
            # Update existing
            set_clauses = []
            values = {"user_id": user_id, "updated_at": datetime.utcnow()}
            
            for key, value in preferences.items():
                if hasattr(UserExportPreferences, key):
                    set_clauses.append(f"{key} = :{key}")
                    values[key] = value
            
            if set_clauses:
                query = f"""
                UPDATE user_export_preferences 
                SET {', '.join(set_clauses)}, updated_at = :updated_at
                WHERE user_id = :user_id
                """
                await self.database.execute(query, values=values)
        else:
            # Create new
            values = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                **preferences
            }
            
            columns = list(values.keys())
            placeholders = [f":{col}" for col in columns]
            
            query = f"""
            INSERT INTO user_export_preferences ({', '.join(columns)})
            VALUES ({', '.join(placeholders)})
            """
            
            await self.database.execute(query, values=values)
        
        return True
    
    async def cleanup_expired_jobs(self) -> int:
        """Clean up expired export jobs"""
        
        query = """
        DELETE FROM export_jobs 
        WHERE expires_at < :now 
        OR (status = :completed AND completed_at < :cleanup_date)
        """
        
        cleanup_date = datetime.utcnow() - timedelta(days=settings.security.data_retention_days)
        
        result = await self.database.execute(
            query, 
            values={
                "now": datetime.utcnow(),
                "completed": ExportStatus.COMPLETED,
                "cleanup_date": cleanup_date
            }
        )
        
        return result

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