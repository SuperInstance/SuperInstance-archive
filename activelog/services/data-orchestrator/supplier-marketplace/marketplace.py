#!/usr/bin/env python3
"""
Supplier Marketplace System
Comprehensive platform for supplier discovery, management, and procurement
"""

import os
import json
import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import sqlite3
import threading
from datetime import datetime, timedelta
import requests
import hashlib
import uuid
from decimal import Decimal
import re


class SupplierCategory(Enum):
    MANUFACTURING = "manufacturing"
    MATERIALS = "materials"
    ELECTRONICS = "electronics"
    MECHANICAL = "mechanical"
    SOFTWARE = "software"
    LOGISTICS = "logistics"
    TESTING = "testing"
    CONSULTING = "consulting"


class PaymentTerms(Enum):
    NET_30 = "net_30"
    NET_60 = "net_60"
    COD = "cod"
    PREPAID = "prepaid"
    CREDIT_CARD = "credit_card"


class SupplierStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING_VERIFICATION = "pending_verification"
    SUSPENDED = "suspended"
    BLACKLISTED = "blacklisted"


@dataclass
class Location:
    country: str
    state: str
    city: str
    zip_code: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None


@dataclass
class Contact:
    name: str
    email: str
    phone: str
    role: str
    is_primary: bool = False


@dataclass
class Certification:
    name: str
    issuer: str
    issue_date: datetime
    expiry_date: Optional[datetime]
    certificate_number: str
    verified: bool = False


@dataclass
class Product:
    id: str
    name: str
    description: str
    category: str
    specifications: Dict[str, Any]
    unit_price: Decimal
    minimum_order_quantity: int
    lead_time_days: int
    availability: str
    images: List[str] = None
    certifications: List[str] = None


@dataclass
class Supplier:
    id: str
    name: str
    description: str
    categories: List[SupplierCategory]
    location: Location
    contacts: List[Contact]
    website: Optional[str]
    established_year: int
    employee_count: Optional[int]
    annual_revenue: Optional[Decimal]
    certifications: List[Certification]
    payment_terms: List[PaymentTerms]
    shipping_options: List[str]
    minimum_order_value: Optional[Decimal]
    rating: float
    review_count: int
    verified: bool
    status: SupplierStatus
    created_at: datetime
    updated_at: datetime
    products: List[Product] = None


@dataclass
class Review:
    id: str
    supplier_id: str
    reviewer_name: str
    rating: int
    title: str
    content: str
    verified_purchase: bool
    created_at: datetime
    helpful_votes: int = 0


@dataclass
class RFQRequest:
    id: str
    requester_id: str
    title: str
    description: str
    category: str
    specifications: Dict[str, Any]
    quantity: int
    target_price: Optional[Decimal]
    delivery_deadline: datetime
    location: Location
    created_at: datetime
    status: str
    responses: List[Dict] = None


class SupplierDatabase:
    def __init__(self, db_path: str = "suppliers.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS suppliers (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                categories TEXT,
                location TEXT,
                contacts TEXT,
                website TEXT,
                established_year INTEGER,
                employee_count INTEGER,
                annual_revenue REAL,
                certifications TEXT,
                payment_terms TEXT,
                shipping_options TEXT,
                minimum_order_value REAL,
                rating REAL DEFAULT 0.0,
                review_count INTEGER DEFAULT 0,
                verified BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'pending_verification',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                supplier_id TEXT,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                specifications TEXT,
                unit_price REAL,
                minimum_order_quantity INTEGER,
                lead_time_days INTEGER,
                availability TEXT,
                images TEXT,
                certifications TEXT,
                created_at TEXT,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id TEXT PRIMARY KEY,
                supplier_id TEXT,
                reviewer_name TEXT,
                rating INTEGER,
                title TEXT,
                content TEXT,
                verified_purchase BOOLEAN,
                created_at TEXT,
                helpful_votes INTEGER DEFAULT 0,
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rfq_requests (
                id TEXT PRIMARY KEY,
                requester_id TEXT,
                title TEXT,
                description TEXT,
                category TEXT,
                specifications TEXT,
                quantity INTEGER,
                target_price REAL,
                delivery_deadline TEXT,
                location TEXT,
                created_at TEXT,
                status TEXT DEFAULT 'open',
                responses TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS supplier_metrics (
                supplier_id TEXT,
                metric_date TEXT,
                orders_fulfilled INTEGER DEFAULT 0,
                avg_delivery_time REAL DEFAULT 0.0,
                quality_score REAL DEFAULT 0.0,
                response_time_hours REAL DEFAULT 0.0,
                PRIMARY KEY (supplier_id, metric_date),
                FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_category ON suppliers(categories)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_location ON suppliers(location)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_suppliers_rating ON suppliers(rating)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_products_price ON products(unit_price)")
        
        conn.commit()
        conn.close()
    
    def add_supplier(self, supplier: Supplier) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO suppliers 
            (id, name, description, categories, location, contacts, website, established_year,
             employee_count, annual_revenue, certifications, payment_terms, shipping_options,
             minimum_order_value, rating, review_count, verified, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            supplier.id, supplier.name, supplier.description,
            json.dumps([cat.value for cat in supplier.categories]),
            json.dumps(asdict(supplier.location)),
            json.dumps([asdict(contact) for contact in supplier.contacts]),
            supplier.website, supplier.established_year, supplier.employee_count,
            float(supplier.annual_revenue) if supplier.annual_revenue else None,
            json.dumps([asdict(cert) for cert in supplier.certifications]),
            json.dumps([term.value for term in supplier.payment_terms]),
            json.dumps(supplier.shipping_options),
            float(supplier.minimum_order_value) if supplier.minimum_order_value else None,
            supplier.rating, supplier.review_count, supplier.verified,
            supplier.status.value, supplier.created_at.isoformat(), supplier.updated_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        return supplier.id
    
    def add_product(self, product: Product, supplier_id: str) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO products
            (id, supplier_id, name, description, category, specifications, unit_price,
             minimum_order_quantity, lead_time_days, availability, images, certifications, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.id, supplier_id, product.name, product.description,
            product.category, json.dumps(product.specifications),
            float(product.unit_price), product.minimum_order_quantity,
            product.lead_time_days, product.availability,
            json.dumps(product.images or []),
            json.dumps(product.certifications or []),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        return product.id
    
    def search_suppliers(self, query: str = "", category: SupplierCategory = None,
                        location: str = "", min_rating: float = 0.0,
                        verified_only: bool = False, max_results: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM suppliers WHERE status = 'active'"
        params = []
        
        if query:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if category:
            sql += " AND categories LIKE ?"
            params.append(f"%{category.value}%")
        
        if location:
            sql += " AND location LIKE ?"
            params.append(f"%{location}%")
        
        if min_rating > 0:
            sql += " AND rating >= ?"
            params.append(min_rating)
        
        if verified_only:
            sql += " AND verified = 1"
        
        sql += " ORDER BY rating DESC, review_count DESC LIMIT ?"
        params.append(max_results)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def search_products(self, query: str = "", category: str = "",
                       max_price: Decimal = None, min_availability: int = 0,
                       max_lead_time: int = None, max_results: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = """
            SELECT p.*, s.name as supplier_name, s.rating as supplier_rating
            FROM products p 
            JOIN suppliers s ON p.supplier_id = s.id 
            WHERE s.status = 'active'
        """
        params = []
        
        if query:
            sql += " AND (p.name LIKE ? OR p.description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        
        if category:
            sql += " AND p.category LIKE ?"
            params.append(f"%{category}%")
        
        if max_price:
            sql += " AND p.unit_price <= ?"
            params.append(float(max_price))
        
        if max_lead_time:
            sql += " AND p.lead_time_days <= ?"
            params.append(max_lead_time)
        
        sql += " ORDER BY s.rating DESC, p.unit_price ASC LIMIT ?"
        params.append(max_results)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in rows]
    
    def get_supplier(self, supplier_id: str) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            columns = [desc[0] for desc in cursor.description]
            return dict(zip(columns, row))
        return None
    
    def add_review(self, review: Review) -> str:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO reviews 
            (id, supplier_id, reviewer_name, rating, title, content, 
             verified_purchase, created_at, helpful_votes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            review.id, review.supplier_id, review.reviewer_name, review.rating,
            review.title, review.content, review.verified_purchase,
            review.created_at.isoformat(), review.helpful_votes
        ))
        
        # Update supplier rating
        cursor.execute("""
            SELECT AVG(rating), COUNT(rating) FROM reviews WHERE supplier_id = ?
        """, (review.supplier_id,))
        avg_rating, review_count = cursor.fetchone()
        
        cursor.execute("""
            UPDATE suppliers SET rating = ?, review_count = ? WHERE id = ?
        """, (avg_rating or 0.0, review_count or 0, review.supplier_id))
        
        conn.commit()
        conn.close()
        return review.id


class SupplierVerification:
    def __init__(self):
        self.verification_criteria = {
            'business_license': {'required': True, 'weight': 0.3},
            'tax_registration': {'required': True, 'weight': 0.2},
            'quality_certifications': {'required': False, 'weight': 0.2},
            'financial_stability': {'required': False, 'weight': 0.15},
            'reference_check': {'required': False, 'weight': 0.15}
        }
    
    def verify_supplier(self, supplier: Supplier, documents: Dict[str, str]) -> Dict[str, Any]:
        """Verify supplier credentials and documentation"""
        verification_result = {
            'supplier_id': supplier.id,
            'verified': False,
            'score': 0.0,
            'checks': {},
            'recommendations': [],
            'verified_at': datetime.now().isoformat()
        }
        
        total_score = 0.0
        max_score = 0.0
        
        for criterion, config in self.verification_criteria.items():
            max_score += config['weight']
            check_result = self._check_criterion(criterion, supplier, documents)
            verification_result['checks'][criterion] = check_result
            
            if check_result['passed']:
                total_score += config['weight']
            elif config['required']:
                verification_result['recommendations'].append(
                    f"Required: {criterion.replace('_', ' ').title()}"
                )
        
        verification_result['score'] = total_score / max_score if max_score > 0 else 0.0
        verification_result['verified'] = verification_result['score'] >= 0.7  # 70% threshold
        
        return verification_result
    
    def _check_criterion(self, criterion: str, supplier: Supplier, documents: Dict[str, str]) -> Dict[str, Any]:
        """Check individual verification criterion"""
        check_result = {
            'criterion': criterion,
            'passed': False,
            'details': '',
            'checked_at': datetime.now().isoformat()
        }
        
        if criterion == 'business_license':
            if 'business_license' in documents:
                # In real implementation, would validate the document
                check_result['passed'] = len(documents['business_license']) > 0
                check_result['details'] = 'Business license provided'
            
        elif criterion == 'tax_registration':
            if 'tax_registration' in documents:
                check_result['passed'] = len(documents['tax_registration']) > 0
                check_result['details'] = 'Tax registration provided'
        
        elif criterion == 'quality_certifications':
            cert_count = len(supplier.certifications)
            check_result['passed'] = cert_count > 0
            check_result['details'] = f'{cert_count} certifications provided'
        
        elif criterion == 'financial_stability':
            # Check revenue and years in business
            years_operating = datetime.now().year - supplier.established_year
            has_revenue = supplier.annual_revenue and supplier.annual_revenue > 0
            check_result['passed'] = years_operating >= 2 and has_revenue
            check_result['details'] = f'{years_operating} years in business'
        
        elif criterion == 'reference_check':
            # Check if supplier has reviews or references
            check_result['passed'] = supplier.review_count > 0
            check_result['details'] = f'{supplier.review_count} reviews available'
        
        return check_result


class RFQSystem:
    def __init__(self, database: SupplierDatabase):
        self.database = database
    
    def create_rfq(self, rfq_request: RFQRequest) -> str:
        """Create a new RFQ request"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO rfq_requests
            (id, requester_id, title, description, category, specifications,
             quantity, target_price, delivery_deadline, location, created_at, status, responses)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rfq_request.id, rfq_request.requester_id, rfq_request.title,
            rfq_request.description, rfq_request.category,
            json.dumps(rfq_request.specifications), rfq_request.quantity,
            float(rfq_request.target_price) if rfq_request.target_price else None,
            rfq_request.delivery_deadline.isoformat(),
            json.dumps(asdict(rfq_request.location)),
            rfq_request.created_at.isoformat(), rfq_request.status,
            json.dumps(rfq_request.responses or [])
        ))
        
        conn.commit()
        conn.close()
        return rfq_request.id
    
    def find_matching_suppliers(self, rfq_request: RFQRequest) -> List[Dict]:
        """Find suppliers that match RFQ requirements"""
        # Search for suppliers in the same category
        matching_suppliers = self.database.search_suppliers(
            query=rfq_request.category,
            category=None,
            verified_only=True,
            max_results=20
        )
        
        # Score suppliers based on RFQ fit
        scored_suppliers = []
        for supplier_data in matching_suppliers:
            score = self._calculate_rfq_match_score(rfq_request, supplier_data)
            if score > 0.3:  # Minimum threshold
                supplier_data['match_score'] = score
                scored_suppliers.append(supplier_data)
        
        # Sort by match score
        scored_suppliers.sort(key=lambda x: x['match_score'], reverse=True)
        return scored_suppliers
    
    def _calculate_rfq_match_score(self, rfq_request: RFQRequest, supplier_data: Dict) -> float:
        """Calculate how well a supplier matches an RFQ request"""
        score = 0.0
        max_score = 1.0
        
        # Category match (30% weight)
        categories = json.loads(supplier_data.get('categories', '[]'))
        if rfq_request.category.lower() in [cat.lower() for cat in categories]:
            score += 0.3
        
        # Rating (25% weight)
        rating = supplier_data.get('rating', 0.0)
        score += (rating / 5.0) * 0.25
        
        # Verification status (20% weight)
        if supplier_data.get('verified'):
            score += 0.2
        
        # Location proximity (15% weight) - simplified
        supplier_location = json.loads(supplier_data.get('location', '{}'))
        if supplier_location.get('country') == rfq_request.location.country:
            score += 0.15
            if supplier_location.get('state') == rfq_request.location.state:
                score += 0.05
        
        # Review count (10% weight)
        review_count = supplier_data.get('review_count', 0)
        score += min(review_count / 100.0, 1.0) * 0.1
        
        return min(score, max_score)


class SupplierAnalytics:
    def __init__(self, database: SupplierDatabase):
        self.database = database
    
    def generate_supplier_report(self, supplier_id: str) -> Dict[str, Any]:
        """Generate comprehensive supplier performance report"""
        supplier_data = self.database.get_supplier(supplier_id)
        if not supplier_data:
            return {}
        
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        # Get reviews
        cursor.execute("""
            SELECT rating, created_at FROM reviews 
            WHERE supplier_id = ? 
            ORDER BY created_at DESC
        """, (supplier_id,))
        reviews = cursor.fetchall()
        
        # Get products
        cursor.execute("""
            SELECT COUNT(*), AVG(unit_price), AVG(lead_time_days)
            FROM products WHERE supplier_id = ?
        """, (supplier_id,))
        product_stats = cursor.fetchone()
        
        # Get metrics
        cursor.execute("""
            SELECT * FROM supplier_metrics 
            WHERE supplier_id = ? 
            ORDER BY metric_date DESC LIMIT 12
        """, (supplier_id,))
        metrics = cursor.fetchall()
        
        conn.close()
        
        # Calculate performance indicators
        performance_report = {
            'supplier_info': supplier_data,
            'performance_metrics': {
                'overall_rating': supplier_data.get('rating', 0.0),
                'total_reviews': len(reviews),
                'product_count': product_stats[0] if product_stats else 0,
                'avg_product_price': product_stats[1] if product_stats else 0.0,
                'avg_lead_time': product_stats[2] if product_stats else 0,
            },
            'rating_trend': self._calculate_rating_trend(reviews),
            'strengths': [],
            'areas_for_improvement': [],
            'generated_at': datetime.now().isoformat()
        }
        
        # Identify strengths and improvements
        rating = supplier_data.get('rating', 0.0)
        if rating >= 4.5:
            performance_report['strengths'].append('Excellent customer satisfaction')
        if rating >= 4.0:
            performance_report['strengths'].append('High quality products/services')
        
        if supplier_data.get('verified'):
            performance_report['strengths'].append('Verified supplier status')
        
        if len(reviews) < 5:
            performance_report['areas_for_improvement'].append('Increase customer review count')
        
        if rating < 3.5:
            performance_report['areas_for_improvement'].append('Improve customer satisfaction')
        
        return performance_report
    
    def _calculate_rating_trend(self, reviews: List[Tuple]) -> Dict[str, Any]:
        """Calculate rating trend over time"""
        if len(reviews) < 2:
            return {'trend': 'insufficient_data', 'change': 0.0}
        
        # Get recent ratings (last 30 days) vs older ratings
        cutoff_date = datetime.now() - timedelta(days=30)
        
        recent_ratings = []
        older_ratings = []
        
        for rating, created_at_str in reviews:
            created_at = datetime.fromisoformat(created_at_str)
            if created_at >= cutoff_date:
                recent_ratings.append(rating)
            else:
                older_ratings.append(rating)
        
        if not recent_ratings or not older_ratings:
            return {'trend': 'insufficient_data', 'change': 0.0}
        
        recent_avg = sum(recent_ratings) / len(recent_ratings)
        older_avg = sum(older_ratings) / len(older_ratings)
        change = recent_avg - older_avg
        
        trend = 'stable'
        if change > 0.5:
            trend = 'improving'
        elif change < -0.5:
            trend = 'declining'
        
        return {
            'trend': trend,
            'change': change,
            'recent_average': recent_avg,
            'historical_average': older_avg
        }
    
    def generate_market_insights(self, category: str = None) -> Dict[str, Any]:
        """Generate market insights for suppliers in a category"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        sql = "SELECT * FROM suppliers WHERE status = 'active'"
        params = []
        
        if category:
            sql += " AND categories LIKE ?"
            params.append(f"%{category}%")
        
        cursor.execute(sql, params)
        suppliers = cursor.fetchall()
        
        if not suppliers:
            return {'error': 'No suppliers found for analysis'}
        
        # Calculate market metrics
        ratings = [s[15] for s in suppliers if s[15] is not None]  # rating column
        review_counts = [s[16] for s in suppliers if s[16] is not None]  # review_count column
        
        insights = {
            'total_suppliers': len(suppliers),
            'verified_suppliers': sum(1 for s in suppliers if s[17]),  # verified column
            'average_rating': sum(ratings) / len(ratings) if ratings else 0.0,
            'median_rating': sorted(ratings)[len(ratings)//2] if ratings else 0.0,
            'top_rated_threshold': sorted(ratings)[-int(len(ratings)*0.1)] if len(ratings) >= 10 else max(ratings) if ratings else 0.0,
            'average_reviews': sum(review_counts) / len(review_counts) if review_counts else 0,
            'generated_at': datetime.now().isoformat()
        }
        
        conn.close()
        return insights


class SupplierMarketplace:
    def __init__(self, data_dir: str = "marketplace_data"):
        self.data_dir = data_dir
        self.database = SupplierDatabase()
        self.verification = SupplierVerification()
        self.rfq_system = RFQSystem(self.database)
        self.analytics = SupplierAnalytics(self.database)
        
        # Callbacks
        self.on_supplier_registered: Optional[Callable] = None
        self.on_rfq_created: Optional[Callable] = None
        self.on_review_added: Optional[Callable] = None
        
        # Ensure directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        logging.info("Supplier Marketplace initialized")
    
    async def register_supplier(self, supplier_data: Dict[str, Any], 
                              verification_docs: Dict[str, str] = None) -> str:
        """Register a new supplier in the marketplace"""
        try:
            # Create supplier object
            supplier = Supplier(
                id=str(uuid.uuid4()),
                name=supplier_data['name'],
                description=supplier_data.get('description', ''),
                categories=[SupplierCategory(cat) for cat in supplier_data.get('categories', [])],
                location=Location(**supplier_data['location']),
                contacts=[Contact(**contact) for contact in supplier_data.get('contacts', [])],
                website=supplier_data.get('website'),
                established_year=supplier_data.get('established_year', datetime.now().year),
                employee_count=supplier_data.get('employee_count'),
                annual_revenue=Decimal(str(supplier_data['annual_revenue'])) if supplier_data.get('annual_revenue') else None,
                certifications=[
                    Certification(
                        name=cert['name'],
                        issuer=cert['issuer'],
                        issue_date=datetime.fromisoformat(cert['issue_date']),
                        expiry_date=datetime.fromisoformat(cert['expiry_date']) if cert.get('expiry_date') else None,
                        certificate_number=cert['certificate_number']
                    ) for cert in supplier_data.get('certifications', [])
                ],
                payment_terms=[PaymentTerms(term) for term in supplier_data.get('payment_terms', [])],
                shipping_options=supplier_data.get('shipping_options', []),
                minimum_order_value=Decimal(str(supplier_data['minimum_order_value'])) if supplier_data.get('minimum_order_value') else None,
                rating=0.0,
                review_count=0,
                verified=False,
                status=SupplierStatus.PENDING_VERIFICATION,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Add to database
            supplier_id = self.database.add_supplier(supplier)
            
            # Verify supplier if documents provided
            if verification_docs:
                verification_result = self.verification.verify_supplier(supplier, verification_docs)
                if verification_result['verified']:
                    supplier.status = SupplierStatus.ACTIVE
                    supplier.verified = True
                    self.database.add_supplier(supplier)  # Update
            
            # Add products if provided
            if 'products' in supplier_data:
                for product_data in supplier_data['products']:
                    product = Product(
                        id=str(uuid.uuid4()),
                        name=product_data['name'],
                        description=product_data.get('description', ''),
                        category=product_data['category'],
                        specifications=product_data.get('specifications', {}),
                        unit_price=Decimal(str(product_data['unit_price'])),
                        minimum_order_quantity=product_data.get('minimum_order_quantity', 1),
                        lead_time_days=product_data.get('lead_time_days', 7),
                        availability=product_data.get('availability', 'in_stock'),
                        images=product_data.get('images', []),
                        certifications=product_data.get('certifications', [])
                    )
                    self.database.add_product(product, supplier_id)
            
            # Trigger callback
            if self.on_supplier_registered:
                self.on_supplier_registered(supplier)
            
            logging.info(f"Supplier registered: {supplier.name} ({supplier_id})")
            return supplier_id
            
        except Exception as e:
            logging.error(f"Error registering supplier: {e}")
            raise
    
    def search_suppliers(self, **filters) -> List[Dict]:
        """Search for suppliers with various filters"""
        return self.database.search_suppliers(**filters)
    
    def search_products(self, **filters) -> List[Dict]:
        """Search for products with various filters"""
        return self.database.search_products(**filters)
    
    def get_supplier_details(self, supplier_id: str) -> Optional[Dict]:
        """Get detailed supplier information"""
        supplier_data = self.database.get_supplier(supplier_id)
        if not supplier_data:
            return None
        
        # Get products
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM products WHERE supplier_id = ?", (supplier_id,))
        products = cursor.fetchall()
        
        cursor.execute("SELECT * FROM reviews WHERE supplier_id = ? ORDER BY created_at DESC", (supplier_id,))
        reviews = cursor.fetchall()
        
        conn.close()
        
        # Add products and reviews to supplier data
        supplier_data['products'] = [dict(zip([col[0] for col in cursor.description], product)) for product in products]
        supplier_data['reviews'] = [dict(zip([col[0] for col in cursor.description], review)) for review in reviews]
        
        return supplier_data
    
    async def create_rfq(self, rfq_data: Dict[str, Any]) -> str:
        """Create a new RFQ request"""
        rfq_request = RFQRequest(
            id=str(uuid.uuid4()),
            requester_id=rfq_data['requester_id'],
            title=rfq_data['title'],
            description=rfq_data['description'],
            category=rfq_data['category'],
            specifications=rfq_data.get('specifications', {}),
            quantity=rfq_data['quantity'],
            target_price=Decimal(str(rfq_data['target_price'])) if rfq_data.get('target_price') else None,
            delivery_deadline=datetime.fromisoformat(rfq_data['delivery_deadline']),
            location=Location(**rfq_data['location']),
            created_at=datetime.now(),
            status='open'
        )
        
        rfq_id = self.rfq_system.create_rfq(rfq_request)
        
        # Find matching suppliers
        matching_suppliers = self.rfq_system.find_matching_suppliers(rfq_request)
        
        # Notify matching suppliers (placeholder)
        await self._notify_suppliers_of_rfq(matching_suppliers, rfq_request)
        
        if self.on_rfq_created:
            self.on_rfq_created(rfq_request)
        
        return rfq_id
    
    async def _notify_suppliers_of_rfq(self, suppliers: List[Dict], rfq_request: RFQRequest):
        """Notify suppliers about relevant RFQ requests"""
        # In real implementation, this would send emails or push notifications
        logging.info(f"Notifying {len(suppliers)} suppliers about RFQ: {rfq_request.title}")
    
    def add_review(self, supplier_id: str, review_data: Dict[str, Any]) -> str:
        """Add a review for a supplier"""
        review = Review(
            id=str(uuid.uuid4()),
            supplier_id=supplier_id,
            reviewer_name=review_data['reviewer_name'],
            rating=review_data['rating'],
            title=review_data['title'],
            content=review_data['content'],
            verified_purchase=review_data.get('verified_purchase', False),
            created_at=datetime.now(),
            helpful_votes=0
        )
        
        review_id = self.database.add_review(review)
        
        if self.on_review_added:
            self.on_review_added(review)
        
        return review_id
    
    def get_supplier_recommendations(self, user_id: str, category: str = None) -> List[Dict]:
        """Get personalized supplier recommendations"""
        # Simplified recommendation logic
        filters = {'verified_only': True, 'min_rating': 4.0}
        if category:
            filters['category'] = SupplierCategory(category)
        
        recommendations = self.search_suppliers(**filters)
        
        # Sort by rating and review count
        recommendations.sort(key=lambda x: (x['rating'], x['review_count']), reverse=True)
        
        return recommendations[:10]
    
    def generate_analytics_report(self, supplier_id: str = None, category: str = None) -> Dict[str, Any]:
        """Generate analytics report"""
        if supplier_id:
            return self.analytics.generate_supplier_report(supplier_id)
        else:
            return self.analytics.generate_market_insights(category)
    
    def get_marketplace_stats(self) -> Dict[str, Any]:
        """Get overall marketplace statistics"""
        conn = sqlite3.connect(self.database.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM suppliers WHERE status = 'active'")
        active_suppliers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM suppliers WHERE verified = 1")
        verified_suppliers = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM products")
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM rfq_requests WHERE status = 'open'")
        open_rfqs = cursor.fetchone()[0]
        
        cursor.execute("SELECT AVG(rating) FROM suppliers WHERE rating > 0")
        avg_rating = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        return {
            'active_suppliers': active_suppliers,
            'verified_suppliers': verified_suppliers,
            'total_products': total_products,
            'open_rfqs': open_rfqs,
            'average_supplier_rating': avg_rating,
            'generated_at': datetime.now().isoformat()
        }


# Demo function
async def demo_supplier_marketplace():
    """Demonstrate Supplier Marketplace functionality"""
    print("=== Supplier Marketplace Demo ===")
    
    marketplace = SupplierMarketplace()
    
    # Set up callbacks
    marketplace.on_supplier_registered = lambda supplier: print(f"Supplier registered: {supplier.name}")
    marketplace.on_rfq_created = lambda rfq: print(f"RFQ created: {rfq.title}")
    
    # Register a sample supplier
    sample_supplier = {
        'name': 'TechParts Manufacturing',
        'description': 'Leading manufacturer of electronic components',
        'categories': ['electronics', 'manufacturing'],
        'location': {
            'country': 'USA',
            'state': 'California',
            'city': 'San Jose',
            'zip_code': '95110',
            'address': '123 Tech Street'
        },
        'contacts': [{
            'name': 'John Smith',
            'email': 'john@techparts.com',
            'phone': '+1-555-0123',
            'role': 'Sales Manager',
            'is_primary': True
        }],
        'website': 'https://techparts.com',
        'established_year': 2010,
        'employee_count': 150,
        'annual_revenue': 5000000,
        'payment_terms': ['net_30', 'credit_card'],
        'shipping_options': ['ground', 'express', 'international'],
        'products': [{
            'name': 'High-Performance PCB',
            'description': 'Multi-layer printed circuit board',
            'category': 'electronics',
            'specifications': {'layers': 6, 'thickness': '1.6mm'},
            'unit_price': 25.99,
            'minimum_order_quantity': 100,
            'lead_time_days': 14,
            'availability': 'in_stock'
        }]
    }
    
    supplier_id = await marketplace.register_supplier(sample_supplier)
    
    # Search suppliers
    suppliers = marketplace.search_suppliers(category=SupplierCategory.ELECTRONICS)
    print(f"Found {len(suppliers)} electronics suppliers")
    
    # Create RFQ
    rfq_data = {
        'requester_id': 'user123',
        'title': 'Need PCBs for IoT Project',
        'description': 'Looking for high-quality PCBs for our new IoT device',
        'category': 'electronics',
        'quantity': 1000,
        'target_price': 20.00,
        'delivery_deadline': (datetime.now() + timedelta(days=30)).isoformat(),
        'location': {
            'country': 'USA',
            'state': 'California',
            'city': 'San Francisco',
            'zip_code': '94105',
            'address': '456 Startup Ave'
        }
    }
    
    rfq_id = await marketplace.create_rfq(rfq_data)
    
    # Get marketplace stats
    stats = marketplace.get_marketplace_stats()
    print(f"Marketplace stats: {stats}")
    
    print("Supplier Marketplace demo completed")


if __name__ == "__main__":
    asyncio.run(demo_supplier_marketplace())