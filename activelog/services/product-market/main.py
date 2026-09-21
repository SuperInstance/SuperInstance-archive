#!/usr/bin/env python3
"""
Product Marketplace - Custom hardware designs and Activelog-ready devices
"""

import asyncio
import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import List, Dict, Any, Optional
import json
import os
from datetime import datetime, timedelta
import uuid
import hashlib
from pathlib import Path
import aiofiles
import aiohttp
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
try:
    import boto3
except ImportError:
    boto3 = None

try:
    from PIL import Image
except ImportError:
    Image = None

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    import stripe
except ImportError:
    stripe = None

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
except ImportError:
    sendgrid = None
    Mail = None

# Initialize FastAPI app
app = FastAPI(
    title="Activelog Product Marketplace",
    description="Custom hardware designs and Activelog-ready devices marketplace",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./product_marketplace.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Product Categories
PRODUCT_CATEGORIES = {
    "hardware_designs": "Custom Hardware Designs",
    "activelog_devices": "Activelog-Ready Devices", 
    "solar_cameras": "Solar Camera Systems",
    "fish_counters": "Fish Counter Solutions",
    "sensor_packages": "Sensor Packages",
    "diy_kits": "DIY Assembly Kits",
    "installation_services": "Installation & Assembly Services",
    "community_designs": "Community Contributed Designs"
}

class Product(Base):
    __tablename__ = "products"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    technical_specs = Column(JSON)
    price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    creator_id = Column(String(100), nullable=False)
    creator_name = Column(String(255), nullable=False)
    images = Column(JSON, default=list)
    design_files = Column(JSON, default=list)
    documentation = Column(JSON, default=list)
    tags = Column(JSON, default=list)
    popularity_score = Column(Float, default=0.0)
    viral_score = Column(Float, default=0.0)
    sales_count = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    patent_protected = Column(Boolean, default=False)
    patent_number = Column(String(100))
    license_type = Column(String(50), default="MIT")
    revenue_sharing_enabled = Column(Boolean, default=False)
    revenue_sharing_percent = Column(Float, default=10.0)
    activelog_compatible = Column(Boolean, default=True)
    difficulty_level = Column(String(20), default="intermediate")
    assembly_time_hours = Column(Integer, default=2)
    tools_required = Column(JSON, default=list)
    materials_included = Column(JSON, default=list)
    status = Column(String(20), default="active")
    featured = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Designer(Base):
    __tablename__ = "designers"
    
    id = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    bio = Column(Text)
    avatar_url = Column(String(500))
    location = Column(String(255))
    specialties = Column(JSON, default=list)
    verified = Column(Boolean, default=False)
    reputation_score = Column(Float, default=0.0)
    total_sales = Column(Float, default=0.0)
    total_earnings = Column(Float, default=0.0)
    patent_holder = Column(Boolean, default=False)
    patents = Column(JSON, default=list)
    social_links = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_number = Column(String(20), unique=True, nullable=False)
    customer_id = Column(String(100), nullable=False)
    customer_email = Column(String(255), nullable=False)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    order_type = Column(String(50))  # digital, physical, service
    shipping_address = Column(JSON)
    assembly_service = Column(Boolean, default=False)
    installation_service = Column(Boolean, default=False)
    status = Column(String(20), default="pending")
    payment_status = Column(String(20), default="pending")
    payment_intent_id = Column(String(100))
    tracking_number = Column(String(100))
    fulfillment_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    customer_id = Column(String(100), nullable=False)
    customer_name = Column(String(255), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    title = Column(String(255))
    review_text = Column(Text)
    images = Column(JSON, default=list)
    verified_purchase = Column(Boolean, default=False)
    helpful_votes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Patent(Base):
    __tablename__ = "patents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    patent_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    inventor_id = Column(String(100), nullable=False)
    inventor_name = Column(String(255), nullable=False)
    filing_date = Column(DateTime, nullable=False)
    grant_date = Column(DateTime)
    expiry_date = Column(DateTime)
    patent_office = Column(String(50), default="USPTO")
    status = Column(String(20), default="filed")
    claims = Column(JSON, default=list)
    drawings = Column(JSON, default=list)
    related_products = Column(JSON, default=list)
    licensing_available = Column(Boolean, default=False)
    license_fee_percent = Column(Float, default=5.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class ViralMetric(Base):
    __tablename__ = "viral_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    metric_type = Column(String(50), nullable=False)  # view, share, like, build, review
    count = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)
    source = Column(String(100))  # social_media, website, community
    event_metadata = Column(JSON, default=dict)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Services
class MarketplaceService:
    def __init__(self):
        self.tfidf_vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        self.s3_client = boto3.client('s3') if boto3 and os.getenv('AWS_ACCESS_KEY_ID') else None
        self.stripe_key = os.getenv('STRIPE_SECRET_KEY')
        if self.stripe_key and stripe:
            stripe.api_key = self.stripe_key
            
    async def create_product(self, product_data: dict, creator_id: str, db: Session):
        """Create a new product listing"""
        product = Product(
            name=product_data['name'],
            category=product_data['category'],
            description=product_data['description'],
            technical_specs=product_data.get('technical_specs', {}),
            price=product_data['price'],
            currency=product_data.get('currency', 'USD'),
            creator_id=creator_id,
            creator_name=product_data['creator_name'],
            images=product_data.get('images', []),
            design_files=product_data.get('design_files', []),
            documentation=product_data.get('documentation', []),
            tags=product_data.get('tags', []),
            patent_protected=product_data.get('patent_protected', False),
            patent_number=product_data.get('patent_number'),
            license_type=product_data.get('license_type', 'MIT'),
            revenue_sharing_enabled=product_data.get('revenue_sharing_enabled', False),
            revenue_sharing_percent=product_data.get('revenue_sharing_percent', 10.0),
            difficulty_level=product_data.get('difficulty_level', 'intermediate'),
            assembly_time_hours=product_data.get('assembly_time_hours', 2),
            tools_required=product_data.get('tools_required', []),
            materials_included=product_data.get('materials_included', [])
        )
        
        db.add(product)
        db.commit()
        db.refresh(product)
        
        # Track viral metrics
        await self.track_viral_metric(str(product.id), 'creation', 1, db)
        
        return product
    
    async def search_products(self, query: str, filters: dict, db: Session):
        """Advanced product search with ML-based recommendations"""
        products_query = db.query(Product).filter(Product.status == 'active')
        
        # Apply filters
        if filters.get('category'):
            products_query = products_query.filter(Product.category == filters['category'])
        
        if filters.get('price_min'):
            products_query = products_query.filter(Product.price >= filters['price_min'])
            
        if filters.get('price_max'):
            products_query = products_query.filter(Product.price <= filters['price_max'])
        
        if filters.get('activelog_compatible'):
            products_query = products_query.filter(Product.activelog_compatible == True)
            
        if filters.get('difficulty_level'):
            products_query = products_query.filter(Product.difficulty_level == filters['difficulty_level'])
        
        products = products_query.all()
        
        # If search query provided, use TF-IDF similarity
        if query:
            product_texts = [f"{p.name} {p.description} {' '.join(p.tags)}" for p in products]
            
            if product_texts:
                try:
                    tfidf_matrix = self.tfidf_vectorizer.fit_transform(product_texts + [query])
                    query_vector = tfidf_matrix[-1]
                    product_vectors = tfidf_matrix[:-1]
                    
                    similarities = cosine_similarity(query_vector, product_vectors).flatten()
                    
                    # Sort by similarity
                    sorted_indices = similarities.argsort()[::-1]
                    products = [products[i] for i in sorted_indices if similarities[i] > 0.1]
                except:
                    pass  # Fallback to original order
        
        # Sort by popularity and viral score
        products.sort(key=lambda p: (p.viral_score, p.popularity_score, p.sales_count), reverse=True)
        
        return products
    
    async def calculate_viral_score(self, product_id: str, db: Session):
        """Calculate viral score based on various engagement metrics"""
        metrics = db.query(ViralMetric).filter(ViralMetric.product_id == product_id).all()
        
        # Weight different metrics differently
        weights = {
            'view': 1.0,
            'share': 5.0,
            'like': 2.0,
            'build': 10.0,
            'review': 8.0,
            'purchase': 15.0,
            'patent_citation': 20.0
        }
        
        viral_score = 0.0
        total_count = 0
        
        for metric in metrics:
            weight = weights.get(metric.metric_type, 1.0)
            viral_score += metric.count * weight
            total_count += metric.count
        
        # Time decay factor (recent activity weighs more)
        recent_metrics = [m for m in metrics if (datetime.utcnow() - m.date).days <= 30]
        recent_boost = len(recent_metrics) * 0.1
        
        # Normalize by time since creation
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            days_since_creation = (datetime.utcnow() - product.created_at).days + 1
            viral_score = viral_score / np.sqrt(days_since_creation) + recent_boost
            
            # Update product viral score
            product.viral_score = viral_score
            db.commit()
        
        return viral_score
    
    async def track_viral_metric(self, product_id: str, metric_type: str, count: int, db: Session, source: str = None, metadata: dict = None):
        """Track viral metrics for products"""
        metric = ViralMetric(
            product_id=product_id,
            metric_type=metric_type,
            count=count,
            source=source,
            event_metadata=metadata or {}
        )
        
        db.add(metric)
        db.commit()
        
        # Recalculate viral score
        await self.calculate_viral_score(product_id, db)
    
    async def create_order(self, order_data: dict, db: Session):
        """Create a new order"""
        order_number = f"ALM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        
        order = Order(
            order_number=order_number,
            customer_id=order_data['customer_id'],
            customer_email=order_data['customer_email'],
            product_id=order_data['product_id'],
            product_name=order_data['product_name'],
            quantity=order_data.get('quantity', 1),
            unit_price=order_data['unit_price'],
            total_amount=order_data['total_amount'],
            currency=order_data.get('currency', 'USD'),
            order_type=order_data.get('order_type', 'digital'),
            shipping_address=order_data.get('shipping_address'),
            assembly_service=order_data.get('assembly_service', False),
            installation_service=order_data.get('installation_service', False)
        )
        
        db.add(order)
        db.commit()
        db.refresh(order)
        
        # Track purchase metric
        await self.track_viral_metric(str(order.product_id), 'purchase', order.quantity, db)
        
        return order
    
    async def process_revenue_sharing(self, order: Order, db: Session):
        """Process revenue sharing for creators and patent holders"""
        product = db.query(Product).filter(Product.id == order.product_id).first()
        if not product:
            return
        
        creator_earnings = order.total_amount
        
        # Deduct platform fee (e.g., 5%)
        platform_fee = order.total_amount * 0.05
        creator_earnings -= platform_fee
        
        # Handle patent royalties
        if product.patent_protected and product.patent_number:
            patent = db.query(Patent).filter(Patent.patent_number == product.patent_number).first()
            if patent and patent.licensing_available:
                royalty_fee = order.total_amount * (patent.license_fee_percent / 100)
                creator_earnings -= royalty_fee
                
                # Update patent holder earnings
                patent_holder = db.query(Designer).filter(Designer.id == patent.inventor_id).first()
                if patent_holder:
                    patent_holder.total_earnings += royalty_fee
        
        # Handle revenue sharing with collaborators
        if product.revenue_sharing_enabled and product.revenue_sharing_percent > 0:
            sharing_amount = creator_earnings * (product.revenue_sharing_percent / 100)
            creator_earnings -= sharing_amount
            
            # This would be distributed to collaborators/community contributors
            # Implementation would depend on specific sharing rules
        
        # Update creator earnings
        creator = db.query(Designer).filter(Designer.id == product.creator_id).first()
        if creator:
            creator.total_sales += order.total_amount
            creator.total_earnings += creator_earnings
            
        db.commit()

marketplace_service = MarketplaceService()

# API Routes

@app.get("/")
async def root():
    return {"message": "Activelog Product Marketplace API", "version": "1.0.0"}

@app.get("/categories")
async def get_categories():
    """Get all product categories"""
    return {"categories": PRODUCT_CATEGORIES}

@app.get("/products")
async def list_products(
    category: Optional[str] = None,
    search: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    difficulty: Optional[str] = None,
    activelog_compatible: Optional[bool] = None,
    featured: Optional[bool] = None,
    sort_by: Optional[str] = "viral_score",
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """List products with filtering and search"""
    try:
        filters = {}
        if category:
            filters['category'] = category
        if price_min is not None:
            filters['price_min'] = price_min
        if price_max is not None:
            filters['price_max'] = price_max
        if difficulty:
            filters['difficulty_level'] = difficulty
        if activelog_compatible is not None:
            filters['activelog_compatible'] = activelog_compatible
        
        products = await marketplace_service.search_products(search or "", filters, db)
        
        if featured:
            products = [p for p in products if p.featured]
        
        # Pagination
        start = (page - 1) * limit
        end = start + limit
        paginated_products = products[start:end]
        
        return {
            "products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "description": p.description,
                    "price": p.price,
                    "currency": p.currency,
                    "creator_name": p.creator_name,
                    "images": p.images,
                    "tags": p.tags,
                    "rating": p.rating,
                    "review_count": p.review_count,
                    "sales_count": p.sales_count,
                    "viral_score": p.viral_score,
                    "popularity_score": p.popularity_score,
                    "patent_protected": p.patent_protected,
                    "activelog_compatible": p.activelog_compatible,
                    "difficulty_level": p.difficulty_level,
                    "assembly_time_hours": p.assembly_time_hours,
                    "featured": p.featured,
                    "created_at": p.created_at.isoformat()
                } for p in paginated_products
            ],
            "total": len(products),
            "page": page,
            "pages": (len(products) + limit - 1) // limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products/{product_id}")
async def get_product(product_id: str, db: Session = Depends(get_db)):
    """Get detailed product information"""
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Track view
        await marketplace_service.track_viral_metric(product_id, 'view', 1, db)
        
        # Get reviews
        reviews = db.query(Review).filter(Review.product_id == product_id).order_by(Review.created_at.desc()).limit(10).all()
        
        # Get creator info
        creator = db.query(Designer).filter(Designer.id == product.creator_id).first()
        
        return {
            "id": str(product.id),
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "technical_specs": product.technical_specs,
            "price": product.price,
            "currency": product.currency,
            "creator": {
                "id": creator.id if creator else None,
                "name": creator.name if creator else product.creator_name,
                "reputation_score": creator.reputation_score if creator else 0,
                "verified": creator.verified if creator else False,
                "specialties": creator.specialties if creator else []
            },
            "images": product.images,
            "design_files": product.design_files,
            "documentation": product.documentation,
            "tags": product.tags,
            "rating": product.rating,
            "review_count": product.review_count,
            "sales_count": product.sales_count,
            "viral_score": product.viral_score,
            "popularity_score": product.popularity_score,
            "patent_protected": product.patent_protected,
            "patent_number": product.patent_number,
            "license_type": product.license_type,
            "revenue_sharing_enabled": product.revenue_sharing_enabled,
            "revenue_sharing_percent": product.revenue_sharing_percent,
            "activelog_compatible": product.activelog_compatible,
            "difficulty_level": product.difficulty_level,
            "assembly_time_hours": product.assembly_time_hours,
            "tools_required": product.tools_required,
            "materials_included": product.materials_included,
            "reviews": [
                {
                    "id": str(r.id),
                    "customer_name": r.customer_name,
                    "rating": r.rating,
                    "title": r.title,
                    "review_text": r.review_text,
                    "verified_purchase": r.verified_purchase,
                    "helpful_votes": r.helpful_votes,
                    "created_at": r.created_at.isoformat()
                } for r in reviews
            ],
            "created_at": product.created_at.isoformat(),
            "updated_at": product.updated_at.isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products")
async def create_product(
    product_data: dict,
    creator_id: str = "demo_creator",
    db: Session = Depends(get_db)
):
    """Create a new product listing"""
    try:
        # Validate category
        if product_data.get('category') not in PRODUCT_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")
        
        product = await marketplace_service.create_product(product_data, creator_id, db)
        
        return {
            "id": str(product.id),
            "message": "Product created successfully",
            "product": {
                "id": str(product.id),
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "creator_name": product.creator_name,
                "created_at": product.created_at.isoformat()
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/featured-products")
async def get_featured_products(db: Session = Depends(get_db)):
    """Get featured products across all categories"""
    try:
        products = db.query(Product).filter(
            Product.status == 'active',
            Product.featured == True
        ).order_by(Product.viral_score.desc()).limit(12).all()
        
        return {
            "featured_products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "description": p.description[:200] + "..." if len(p.description) > 200 else p.description,
                    "price": p.price,
                    "creator_name": p.creator_name,
                    "images": p.images[:1],  # First image only
                    "rating": p.rating,
                    "sales_count": p.sales_count,
                    "viral_score": p.viral_score,
                    "patent_protected": p.patent_protected,
                    "activelog_compatible": p.activelog_compatible,
                    "difficulty_level": p.difficulty_level
                } for p in products
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/viral-products")
async def get_viral_products(days: int = 30, limit: int = 20, db: Session = Depends(get_db)):
    """Get trending/viral products"""
    try:
        # Get products with high viral scores in the specified time period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        products = db.query(Product).filter(
            Product.status == 'active',
            Product.updated_at >= cutoff_date
        ).order_by(Product.viral_score.desc()).limit(limit).all()
        
        # Get viral metrics for each product
        viral_data = []
        for product in products:
            metrics = db.query(ViralMetric).filter(
                ViralMetric.product_id == product.id,
                ViralMetric.date >= cutoff_date
            ).all()
            
            total_engagement = sum(m.count for m in metrics)
            
            viral_data.append({
                "id": str(product.id),
                "name": product.name,
                "category": product.category,
                "price": product.price,
                "creator_name": product.creator_name,
                "images": product.images[:1],
                "viral_score": product.viral_score,
                "total_engagement": total_engagement,
                "engagement_breakdown": {
                    metric.metric_type: sum(m.count for m in metrics if m.metric_type == metric.metric_type)
                    for metric in metrics
                },
                "trending_factor": product.viral_score / max(1, (datetime.utcnow() - product.created_at).days)
            })
        
        return {
            "viral_products": viral_data,
            "period_days": days,
            "total_products": len(viral_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/orders")
async def create_order(
    order_data: dict,
    db: Session = Depends(get_db)
):
    """Create a new order"""
    try:
        # Validate product exists
        product = db.query(Product).filter(Product.id == order_data['product_id']).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Calculate total amount
        unit_price = product.price
        quantity = order_data.get('quantity', 1)
        total_amount = unit_price * quantity
        
        # Add assembly service cost if requested
        if order_data.get('assembly_service', False):
            assembly_cost = unit_price * 0.2  # 20% of product price
            total_amount += assembly_cost
        
        # Add installation service cost if requested
        if order_data.get('installation_service', False):
            installation_cost = unit_price * 0.3  # 30% of product price
            total_amount += installation_cost
        
        order_data.update({
            'product_name': product.name,
            'unit_price': unit_price,
            'total_amount': total_amount
        })
        
        order = await marketplace_service.create_order(order_data, db)
        
        # Process revenue sharing
        await marketplace_service.process_revenue_sharing(order, db)
        
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "total_amount": order.total_amount,
            "currency": order.currency,
            "status": order.status,
            "message": "Order created successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/designers/{designer_id}")
async def get_designer(designer_id: str, db: Session = Depends(get_db)):
    """Get designer profile and their products"""
    try:
        designer = db.query(Designer).filter(Designer.id == designer_id).first()
        if not designer:
            raise HTTPException(status_code=404, detail="Designer not found")
        
        # Get designer's products
        products = db.query(Product).filter(
            Product.creator_id == designer_id,
            Product.status == 'active'
        ).order_by(Product.viral_score.desc()).all()
        
        # Get patents
        patents = db.query(Patent).filter(Patent.inventor_id == designer_id).all()
        
        return {
            "designer": {
                "id": designer.id,
                "name": designer.name,
                "bio": designer.bio,
                "avatar_url": designer.avatar_url,
                "location": designer.location,
                "specialties": designer.specialties,
                "verified": designer.verified,
                "reputation_score": designer.reputation_score,
                "total_sales": designer.total_sales,
                "patent_holder": designer.patent_holder,
                "social_links": designer.social_links,
                "created_at": designer.created_at.isoformat()
            },
            "products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "price": p.price,
                    "rating": p.rating,
                    "sales_count": p.sales_count,
                    "viral_score": p.viral_score,
                    "created_at": p.created_at.isoformat()
                } for p in products
            ],
            "patents": [
                {
                    "id": str(p.id),
                    "patent_number": p.patent_number,
                    "title": p.title,
                    "status": p.status,
                    "filing_date": p.filing_date.isoformat() if p.filing_date else None,
                    "licensing_available": p.licensing_available
                } for p in patents
            ],
            "stats": {
                "total_products": len(products),
                "total_patents": len(patents),
                "avg_product_rating": sum(p.rating for p in products) / len(products) if products else 0
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/viral-trends")
async def get_viral_trends(
    days: int = 30,
    category: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get viral trends analytics"""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Base query
        metrics_query = db.query(ViralMetric).filter(ViralMetric.date >= cutoff_date)
        
        if category:
            # Join with products to filter by category
            metrics_query = metrics_query.join(Product).filter(Product.category == category)
        
        metrics = metrics_query.all()
        
        # Group by date and metric type
        daily_metrics = {}
        metric_totals = {}
        
        for metric in metrics:
            date_key = metric.date.strftime('%Y-%m-%d')
            if date_key not in daily_metrics:
                daily_metrics[date_key] = {}
            
            metric_type = metric.metric_type
            if metric_type not in daily_metrics[date_key]:
                daily_metrics[date_key][metric_type] = 0
            
            daily_metrics[date_key][metric_type] += metric.count
            
            if metric_type not in metric_totals:
                metric_totals[metric_type] = 0
            metric_totals[metric_type] += metric.count
        
        # Get top viral products
        top_viral_products = db.query(Product).filter(
            Product.status == 'active',
            Product.updated_at >= cutoff_date
        ).order_by(Product.viral_score.desc()).limit(10).all()
        
        return {
            "period_days": days,
            "category": category,
            "daily_trends": daily_metrics,
            "metric_totals": metric_totals,
            "top_viral_products": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "category": p.category,
                    "viral_score": p.viral_score,
                    "creator_name": p.creator_name
                } for p in top_viral_products
            ],
            "total_engagement": sum(metric_totals.values())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/products/{product_id}/viral-action")
async def track_viral_action(
    product_id: str,
    action_data: dict,
    db: Session = Depends(get_db)
):
    """Track viral actions (share, like, build, etc.)"""
    try:
        # Validate product exists
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        action_type = action_data.get('action_type')
        count = action_data.get('count', 1)
        source = action_data.get('source')
        metadata = action_data.get('metadata', {})
        
        valid_actions = ['view', 'share', 'like', 'build', 'review', 'purchase', 'download']
        if action_type not in valid_actions:
            raise HTTPException(status_code=400, detail=f"Invalid action type. Must be one of: {valid_actions}")
        
        # Track the viral metric
        await marketplace_service.track_viral_metric(
            product_id, action_type, count, db, source, metadata
        )
        
        return {
            "message": "Viral action tracked successfully",
            "product_id": product_id,
            "action_type": action_type,
            "count": count,
            "new_viral_score": product.viral_score
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8380))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)