#!/usr/bin/env python3
"""
ActiveLog Plugin Marketplace API
"""

import asyncio
import hashlib
import json
import os
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse
import sqlalchemy as sa
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from pydantic import BaseModel
from passlib.context import CryptContext
import jwt


# Database Models
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255))
    is_verified = Column(Boolean, default=False)
    plan_type = Column(String(20), default="free")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    plugins = relationship("Plugin", back_populates="author")
    installations = relationship("PluginInstallation", back_populates="user")


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    plan_type = Column(String(20), default="free")
    created_at = Column(DateTime, default=datetime.utcnow)


class Plugin(Base):
    __tablename__ = "plugins"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255))
    description = Column(Text)
    version = Column(String(20), nullable=False)
    category = Column(String(50))
    tags = Column(Text)  # JSON array
    
    # Author
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    author = relationship("User", back_populates="plugins")
    
    # Metadata
    runtime_type = Column(String(20))
    main_file = Column(String(255))
    manifest_data = Column(Text)  # JSON
    
    # Marketplace info
    is_published = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    price = Column(Float, default=0.0)
    currency = Column(String(3), default="USD")
    
    # Stats
    downloads = Column(Integer, default=0)
    rating_average = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)
    
    # Files
    package_url = Column(String(500))
    icon_url = Column(String(500))
    screenshots = Column(Text)  # JSON array
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    versions = relationship("PluginVersion", back_populates="plugin")
    installations = relationship("PluginInstallation", back_populates="plugin")
    reviews = relationship("PluginReview", back_populates="plugin")


class PluginVersion(Base):
    __tablename__ = "plugin_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"))
    plugin = relationship("Plugin", back_populates="versions")
    
    version = Column(String(20), nullable=False)
    changelog = Column(Text)
    package_url = Column(String(500))
    package_size = Column(Integer)
    package_hash = Column(String(64))
    
    is_stable = Column(Boolean, default=True)
    is_deprecated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class PluginInstallation(Base):
    __tablename__ = "plugin_installations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"))
    plugin = relationship("Plugin", back_populates="installations")
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    user = relationship("User", back_populates="installations")
    
    version = Column(String(20))
    installed_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    is_active = Column(Boolean, default=True)


class PluginReview(Base):
    __tablename__ = "plugin_reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    plugin_id = Column(UUID(as_uuid=True), ForeignKey("plugins.id"))
    plugin = relationship("Plugin", back_populates="reviews")
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    rating = Column(Integer)  # 1-5 stars
    title = Column(String(255))
    comment = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Pydantic Models
class PluginCreate(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: str
    version: str
    category: str
    tags: List[str] = []
    runtime_type: str
    price: float = 0.0
    currency: str = "USD"


class PluginUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    price: Optional[float] = None
    is_published: Optional[bool] = None


class PluginResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    version: str
    category: str
    tags: List[str]
    author_name: str
    runtime_type: str
    price: float
    currency: str
    downloads: int
    rating_average: float
    rating_count: int
    is_featured: bool
    is_verified: bool
    icon_url: Optional[str]
    created_at: datetime
    updated_at: datetime


class PluginSearchResponse(BaseModel):
    total: int
    plugins: List[PluginResponse]
    facets: Dict[str, Any]


class ReviewCreate(BaseModel):
    rating: int
    title: str
    comment: Optional[str] = None


class ReviewResponse(BaseModel):
    id: str
    rating: int
    title: str
    comment: Optional[str]
    user_name: str
    created_at: datetime


# FastAPI Application
app = FastAPI(
    title="ActiveLog Plugin Marketplace API",
    description="API for managing plugins in the ActiveLog marketplace",
    version="1.0.0"
)

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///marketplace.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

# File storage
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(exist_ok=True)


# Dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def decode_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return user


# Plugin Management Endpoints

@app.post("/plugins", response_model=PluginResponse)
async def create_plugin(
    plugin_data: PluginCreate,
    manifest_file: UploadFile = File(...),
    package_file: UploadFile = File(...),
    icon_file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new plugin"""
    
    # Check if plugin name already exists
    existing = db.query(Plugin).filter(Plugin.name == plugin_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Plugin name already exists")
    
    # Validate and parse manifest
    manifest_content = await manifest_file.read()
    try:
        manifest = json.loads(manifest_content.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid manifest JSON")
    
    # Validate package
    package_content = await package_file.read()
    if not package_content:
        raise HTTPException(status_code=400, detail="Empty package file")
    
    # Calculate package hash
    package_hash = hashlib.sha256(package_content).hexdigest()
    
    # Save files
    plugin_id = str(uuid.uuid4())
    plugin_dir = UPLOAD_DIR / plugin_id
    plugin_dir.mkdir(exist_ok=True)
    
    # Save package
    package_path = plugin_dir / f"{plugin_data.name}-{plugin_data.version}.zip"
    with open(package_path, "wb") as f:
        f.write(package_content)
    
    # Save icon if provided
    icon_url = None
    if icon_file:
        icon_content = await icon_file.read()
        icon_path = plugin_dir / f"icon.{icon_file.filename.split('.')[-1]}"
        with open(icon_path, "wb") as f:
            f.write(icon_content)
        icon_url = f"/files/{plugin_id}/icon.{icon_file.filename.split('.')[-1]}"
    
    # Create plugin record
    plugin = Plugin(
        id=plugin_id,
        name=plugin_data.name,
        display_name=plugin_data.display_name or plugin_data.name,
        description=plugin_data.description,
        version=plugin_data.version,
        category=plugin_data.category,
        tags=json.dumps(plugin_data.tags),
        author_id=current_user.id,
        runtime_type=plugin_data.runtime_type,
        main_file=manifest.get("main", ""),
        manifest_data=json.dumps(manifest),
        price=plugin_data.price,
        currency=plugin_data.currency,
        package_url=f"/files/{plugin_id}/{package_path.name}",
        icon_url=icon_url
    )
    
    db.add(plugin)
    
    # Create version record
    version = PluginVersion(
        plugin_id=plugin_id,
        version=plugin_data.version,
        package_url=plugin.package_url,
        package_size=len(package_content),
        package_hash=package_hash
    )
    
    db.add(version)
    db.commit()
    db.refresh(plugin)
    
    return _plugin_to_response(plugin, current_user.username)


@app.get("/plugins", response_model=PluginSearchResponse)
async def search_plugins(
    q: Optional[str] = Query(None, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    author: Optional[str] = Query(None, description="Filter by author"),
    featured: Optional[bool] = Query(None, description="Filter featured plugins"),
    verified: Optional[bool] = Query(None, description="Filter verified plugins"),
    min_rating: Optional[float] = Query(None, description="Minimum rating"),
    sort: str = Query("downloads", description="Sort by: downloads, rating, created, updated"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """Search and filter plugins"""
    
    query = db.query(Plugin).filter(Plugin.is_published == True)
    
    # Apply filters
    if q:
        query = query.filter(
            sa.or_(
                Plugin.name.contains(q),
                Plugin.display_name.contains(q),
                Plugin.description.contains(q)
            )
        )
    
    if category:
        query = query.filter(Plugin.category == category)
    
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        for tag in tag_list:
            query = query.filter(Plugin.tags.contains(f'"{tag}"'))
    
    if author:
        query = query.join(User).filter(User.username == author)
    
    if featured is not None:
        query = query.filter(Plugin.is_featured == featured)
    
    if verified is not None:
        query = query.filter(Plugin.is_verified == verified)
    
    if min_rating:
        query = query.filter(Plugin.rating_average >= min_rating)
    
    # Apply sorting
    if sort == "downloads":
        query = query.order_by(Plugin.downloads.desc())
    elif sort == "rating":
        query = query.order_by(Plugin.rating_average.desc())
    elif sort == "created":
        query = query.order_by(Plugin.created_at.desc())
    elif sort == "updated":
        query = query.order_by(Plugin.updated_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    plugins = query.offset(offset).limit(limit).all()
    
    # Convert to response format
    plugin_responses = []
    for plugin in plugins:
        author = db.query(User).filter(User.id == plugin.author_id).first()
        plugin_responses.append(_plugin_to_response(plugin, author.username if author else "Unknown"))
    
    # Generate facets
    facets = _generate_facets(db)
    
    return PluginSearchResponse(
        total=total,
        plugins=plugin_responses,
        facets=facets
    )


@app.get("/plugins/{plugin_id}", response_model=PluginResponse)
async def get_plugin(plugin_id: str, db: Session = Depends(get_db)):
    """Get plugin details"""
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    author = db.query(User).filter(User.id == plugin.author_id).first()
    return _plugin_to_response(plugin, author.username if author else "Unknown")


@app.put("/plugins/{plugin_id}", response_model=PluginResponse)
async def update_plugin(
    plugin_id: str,
    plugin_data: PluginUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update plugin details"""
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    if plugin.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this plugin")
    
    # Update fields
    for field, value in plugin_data.dict(exclude_unset=True).items():
        if field == "tags":
            value = json.dumps(value)
        setattr(plugin, field, value)
    
    plugin.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(plugin)
    
    return _plugin_to_response(plugin, current_user.username)


@app.delete("/plugins/{plugin_id}")
async def delete_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a plugin"""
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    if plugin.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this plugin")
    
    # Clean up files
    plugin_dir = UPLOAD_DIR / plugin_id
    if plugin_dir.exists():
        import shutil
        shutil.rmtree(plugin_dir)
    
    # Delete from database
    db.delete(plugin)
    db.commit()
    
    return {"message": "Plugin deleted successfully"}


# Plugin Installation

@app.post("/plugins/{plugin_id}/install")
async def install_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Install a plugin for the current user"""
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin or not plugin.is_published:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Check if already installed
    existing = db.query(PluginInstallation).filter(
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.user_id == current_user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Plugin already installed")
    
    # Create installation record
    installation = PluginInstallation(
        plugin_id=plugin_id,
        user_id=current_user.id,
        version=plugin.version
    )
    
    db.add(installation)
    
    # Update download count
    plugin.downloads += 1
    
    db.commit()
    
    return {"message": "Plugin installed successfully", "installation_id": str(installation.id)}


@app.delete("/plugins/{plugin_id}/install")
async def uninstall_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uninstall a plugin"""
    
    installation = db.query(PluginInstallation).filter(
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.user_id == current_user.id
    ).first()
    
    if not installation:
        raise HTTPException(status_code=404, detail="Plugin not installed")
    
    db.delete(installation)
    db.commit()
    
    return {"message": "Plugin uninstalled successfully"}


@app.get("/plugins/{plugin_id}/download")
async def download_plugin(
    plugin_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download plugin package"""
    
    # Check if user has installed the plugin
    installation = db.query(PluginInstallation).filter(
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.user_id == current_user.id
    ).first()
    
    if not installation:
        raise HTTPException(status_code=403, detail="Plugin not installed")
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Get package file path
    package_path = UPLOAD_DIR / plugin_id / f"{plugin.name}-{plugin.version}.zip"
    
    if not package_path.exists():
        raise HTTPException(status_code=404, detail="Package file not found")
    
    return FileResponse(
        path=package_path,
        filename=package_path.name,
        media_type="application/zip"
    )


# Reviews

@app.post("/plugins/{plugin_id}/reviews", response_model=ReviewResponse)
async def create_review(
    plugin_id: str,
    review_data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a review for a plugin"""
    
    plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="Plugin not found")
    
    # Check if user has installed the plugin
    installation = db.query(PluginInstallation).filter(
        PluginInstallation.plugin_id == plugin_id,
        PluginInstallation.user_id == current_user.id
    ).first()
    
    if not installation:
        raise HTTPException(status_code=400, detail="Must install plugin before reviewing")
    
    # Check if user already reviewed
    existing_review = db.query(PluginReview).filter(
        PluginReview.plugin_id == plugin_id,
        PluginReview.user_id == current_user.id
    ).first()
    
    if existing_review:
        raise HTTPException(status_code=400, detail="Already reviewed this plugin")
    
    # Create review
    review = PluginReview(
        plugin_id=plugin_id,
        user_id=current_user.id,
        rating=review_data.rating,
        title=review_data.title,
        comment=review_data.comment
    )
    
    db.add(review)
    
    # Update plugin rating
    _update_plugin_rating(db, plugin_id)
    
    db.commit()
    db.refresh(review)
    
    return ReviewResponse(
        id=str(review.id),
        rating=review.rating,
        title=review.title,
        comment=review.comment,
        user_name=current_user.username,
        created_at=review.created_at
    )


@app.get("/plugins/{plugin_id}/reviews")
async def get_reviews(
    plugin_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get reviews for a plugin"""
    
    query = db.query(PluginReview).filter(PluginReview.plugin_id == plugin_id)
    
    total = query.count()
    offset = (page - 1) * limit
    reviews = query.offset(offset).limit(limit).all()
    
    review_responses = []
    for review in reviews:
        user = db.query(User).filter(User.id == review.user_id).first()
        review_responses.append(ReviewResponse(
            id=str(review.id),
            rating=review.rating,
            title=review.title,
            comment=review.comment,
            user_name=user.username if user else "Unknown",
            created_at=review.created_at
        ))
    
    return {
        "total": total,
        "reviews": review_responses
    }


# Helper Functions

def _plugin_to_response(plugin: Plugin, author_name: str) -> PluginResponse:
    """Convert Plugin model to response format"""
    return PluginResponse(
        id=str(plugin.id),
        name=plugin.name,
        display_name=plugin.display_name,
        description=plugin.description,
        version=plugin.version,
        category=plugin.category,
        tags=json.loads(plugin.tags) if plugin.tags else [],
        author_name=author_name,
        runtime_type=plugin.runtime_type,
        price=plugin.price,
        currency=plugin.currency,
        downloads=plugin.downloads,
        rating_average=plugin.rating_average,
        rating_count=plugin.rating_count,
        is_featured=plugin.is_featured,
        is_verified=plugin.is_verified,
        icon_url=plugin.icon_url,
        created_at=plugin.created_at,
        updated_at=plugin.updated_at
    )


def _generate_facets(db: Session) -> Dict[str, Any]:
    """Generate search facets"""
    
    # Get categories
    categories = db.query(Plugin.category, sa.func.count(Plugin.id)).filter(
        Plugin.is_published == True
    ).group_by(Plugin.category).all()
    
    # Get runtime types
    runtimes = db.query(Plugin.runtime_type, sa.func.count(Plugin.id)).filter(
        Plugin.is_published == True
    ).group_by(Plugin.runtime_type).all()
    
    return {
        "categories": [{"name": cat[0], "count": cat[1]} for cat in categories],
        "runtimes": [{"name": rt[0], "count": rt[1]} for rt in runtimes],
        "price_ranges": [
            {"name": "Free", "min": 0, "max": 0},
            {"name": "$1-10", "min": 1, "max": 10},
            {"name": "$10+", "min": 10, "max": None}
        ]
    }


def _update_plugin_rating(db: Session, plugin_id: str):
    """Update plugin rating based on reviews"""
    
    reviews = db.query(PluginReview).filter(PluginReview.plugin_id == plugin_id).all()
    
    if reviews:
        total_rating = sum(review.rating for review in reviews)
        avg_rating = total_rating / len(reviews)
        
        plugin = db.query(Plugin).filter(Plugin.id == plugin_id).first()
        plugin.rating_average = round(avg_rating, 2)
        plugin.rating_count = len(reviews)


# File serving
@app.get("/files/{plugin_id}/{filename}")
async def serve_file(plugin_id: str, filename: str):
    """Serve plugin files"""
    file_path = UPLOAD_DIR / plugin_id / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=file_path, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)