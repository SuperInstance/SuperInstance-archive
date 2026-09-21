"""
Marketplace v2 - Visual Product Browser
Advanced visual product browsing with filtering, search, and interactive displays
"""

import asyncio
import sqlite3
import json
import random
import time
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import threading
import logging
from pathlib import Path
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProductCategory(Enum):
    MARINE_EQUIPMENT = "marine_equipment"
    FISHING_GEAR = "fishing_gear"
    NAVIGATION_SYSTEMS = "navigation_systems"
    SAFETY_EQUIPMENT = "safety_equipment"
    ENGINE_PARTS = "engine_parts"
    ELECTRONICS = "electronics"
    TOOLS = "tools"
    BOAT_ACCESSORIES = "boat_accessories"
    MAINTENANCE_SUPPLIES = "maintenance_supplies"
    CLOTHING_GEAR = "clothing_gear"

class ProductCondition(Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    FAIR = "fair"
    FOR_PARTS = "for_parts"
    REFURBISHED = "refurbished"

class ProductStatus(Enum):
    ACTIVE = "active"
    SOLD = "sold"
    RESERVED = "reserved"
    DRAFT = "draft"
    DISCONTINUED = "discontinued"

class ViewType(Enum):
    GRID = "grid"
    LIST = "list"
    GALLERY = "gallery"
    DETAILED = "detailed"
    COMPARISON = "comparison"

class SortOption(Enum):
    RELEVANCE = "relevance"
    PRICE_LOW_HIGH = "price_asc"
    PRICE_HIGH_LOW = "price_desc"
    DATE_NEWEST = "date_desc"
    DATE_OLDEST = "date_asc"
    POPULARITY = "popularity"
    RATING = "rating"
    DISTANCE = "distance"

@dataclass
class ProductImage:
    image_id: str
    product_id: str
    url: str
    alt_text: str
    is_primary: bool
    display_order: int
    tags: List[str]
    
@dataclass
class ProductSpecification:
    spec_id: str
    name: str
    value: str
    unit: Optional[str]
    category: str
    display_order: int

@dataclass
class ProductReview:
    review_id: str
    product_id: str
    user_id: str
    rating: int  # 1-5 stars
    title: str
    content: str
    verified_purchase: bool
    helpful_votes: int
    total_votes: int
    created_at: datetime
    
@dataclass
class ProductVariant:
    variant_id: str
    product_id: str
    name: str
    sku: str
    price: float
    stock_quantity: int
    attributes: Dict[str, str]  # color, size, model, etc.
    
@dataclass
class Product:
    product_id: str
    title: str
    description: str
    short_description: str
    category: ProductCategory
    subcategory: str
    brand: str
    model: str
    sku: str
    price: float
    original_price: Optional[float]
    currency: str
    condition: ProductCondition
    status: ProductStatus
    stock_quantity: int
    minimum_order: int
    vendor_id: str
    vendor_name: str
    location: Tuple[float, float]  # lat, lon
    location_name: str
    images: List[ProductImage]
    specifications: List[ProductSpecification]
    variants: List[ProductVariant]
    reviews: List[ProductReview]
    tags: List[str]
    weight: Optional[float]
    dimensions: Optional[Dict[str, float]]  # length, width, height
    shipping_info: Dict[str, Any]
    warranty_info: Optional[str]
    return_policy: Optional[str]
    created_at: datetime
    updated_at: datetime
    view_count: int
    save_count: int  # wishlist saves
    average_rating: float
    total_reviews: int
    popularity_score: float

@dataclass
class SearchFilter:
    categories: List[ProductCategory]
    price_range: Tuple[float, float]
    condition: List[ProductCondition]
    location_radius: Optional[Tuple[float, float, float]]  # lat, lon, radius_km
    brands: List[str]
    tags: List[str]
    in_stock_only: bool
    with_reviews_only: bool
    min_rating: Optional[float]
    
@dataclass
class SearchResult:
    products: List[Product]
    total_count: int
    facets: Dict[str, Dict[str, int]]  # category -> {value -> count}
    suggested_filters: List[str]
    search_time: float
    page: int
    per_page: int

class VisualProductBrowser:
    def __init__(self, db_path: str = "marketplace_v2_browser.db"):
        self.db_path = db_path
        self.products: Dict[str, Product] = {}
        self.search_cache: Dict[str, SearchResult] = {}
        
        # Initialize database
        self._init_database()
        
        # Load sample products
        self._load_sample_products()
        
        # Start background analytics
        self.analytics_thread = threading.Thread(target=self._run_analytics, daemon=True)
        self.analytics_thread.start()
    
    def _init_database(self):
        """Initialize SQLite database for product browser"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                short_description TEXT,
                category TEXT,
                subcategory TEXT,
                brand TEXT,
                model TEXT,
                sku TEXT UNIQUE,
                price REAL,
                original_price REAL,
                currency TEXT DEFAULT 'USD',
                condition TEXT,
                status TEXT,
                stock_quantity INTEGER,
                minimum_order INTEGER DEFAULT 1,
                vendor_id TEXT,
                vendor_name TEXT,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                tags TEXT,
                weight REAL,
                dimensions TEXT,
                shipping_info TEXT,
                warranty_info TEXT,
                return_policy TEXT,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                view_count INTEGER DEFAULT 0,
                save_count INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0,
                total_reviews INTEGER DEFAULT 0,
                popularity_score REAL DEFAULT 0
            )
        ''')
        
        # Product images table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_images (
                image_id TEXT PRIMARY KEY,
                product_id TEXT,
                url TEXT,
                alt_text TEXT,
                is_primary BOOLEAN,
                display_order INTEGER,
                tags TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Product specifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_specifications (
                spec_id TEXT PRIMARY KEY,
                product_id TEXT,
                name TEXT,
                value TEXT,
                unit TEXT,
                category TEXT,
                display_order INTEGER,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Product reviews table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_reviews (
                review_id TEXT PRIMARY KEY,
                product_id TEXT,
                user_id TEXT,
                rating INTEGER,
                title TEXT,
                content TEXT,
                verified_purchase BOOLEAN,
                helpful_votes INTEGER DEFAULT 0,
                total_votes INTEGER DEFAULT 0,
                created_at TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Product variants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_variants (
                variant_id TEXT PRIMARY KEY,
                product_id TEXT,
                name TEXT,
                sku TEXT,
                price REAL,
                stock_quantity INTEGER,
                attributes TEXT,
                FOREIGN KEY (product_id) REFERENCES products (product_id)
            )
        ''')
        
        # Search analytics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_analytics (
                search_id TEXT PRIMARY KEY,
                query TEXT,
                filters TEXT,
                results_count INTEGER,
                search_time REAL,
                user_id TEXT,
                timestamp TIMESTAMP,
                clicked_products TEXT
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_price ON products(price)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_location ON products(latitude, longitude)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_status ON products(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_reviews_product ON product_reviews(product_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_variants_product ON product_variants(product_id)')
        
        conn.commit()
        conn.close()
    
    def _load_sample_products(self):
        """Load sample products for demonstration"""
        sample_products = [
            {
                "title": "Furuno GP33 GPS Navigator",
                "category": ProductCategory.NAVIGATION_SYSTEMS,
                "subcategory": "GPS Systems",
                "brand": "Furuno",
                "model": "GP33",
                "price": 899.99,
                "original_price": 1199.99,
                "condition": ProductCondition.NEW,
                "description": "Professional marine GPS navigator with 4.3-inch color LCD display, WAAS receiver, and comprehensive navigation features.",
                "specifications": [
                    ("Display", "4.3-inch Color LCD", "inches", "Display"),
                    ("Receiver", "50-channel WAAS", "channels", "Navigation"),
                    ("Accuracy", "< 3 meters", "meters", "Performance"),
                    ("Update Rate", "1 Hz", "Hz", "Performance"),
                    ("Power", "12V DC", "V", "Electrical")
                ]
            },
            {
                "title": "Shimano Tiagra 30A Fishing Reel",
                "category": ProductCategory.FISHING_GEAR,
                "subcategory": "Reels",
                "brand": "Shimano",
                "model": "Tiagra 30A",
                "price": 749.99,
                "condition": ProductCondition.NEW,
                "description": "Heavy-duty offshore fishing reel with advanced drag system, perfect for big game fishing.",
                "specifications": [
                    ("Line Capacity", "600yds/30lb", "yards", "Capacity"),
                    ("Gear Ratio", "3.9:1", "ratio", "Performance"),
                    ("Weight", "34.9 oz", "oz", "Physical"),
                    ("Max Drag", "25 lbs", "lbs", "Performance"),
                    ("Bearings", "3+1", "count", "Construction")
                ]
            },
            {
                "title": "Raymarine Axiom 9 Chartplotter",
                "category": ProductCategory.ELECTRONICS,
                "subcategory": "Chartplotters",
                "brand": "Raymarine",
                "model": "Axiom 9",
                "price": 1599.99,
                "condition": ProductCondition.NEW,
                "description": "9-inch multifunction display with built-in GPS, sonar compatibility, and RealVision 3D imaging.",
                "specifications": [
                    ("Screen Size", "9 inches", "inches", "Display"),
                    ("Resolution", "1280x800", "pixels", "Display"),
                    ("GPS", "Built-in 10Hz", "Hz", "Navigation"),
                    ("Sonar", "CHIRP Compatible", "type", "Sonar"),
                    ("Networking", "WiFi, Bluetooth", "type", "Connectivity")
                ]
            },
            {
                "title": "Mercury 150HP FourStroke Outboard",
                "category": ProductCategory.ENGINE_PARTS,
                "subcategory": "Outboard Motors",
                "brand": "Mercury",
                "model": "150HP FourStroke",
                "price": 12999.99,
                "condition": ProductCondition.NEW,
                "description": "Advanced 4-stroke outboard motor with SmartCraft technology, fuel-efficient and environmentally friendly.",
                "specifications": [
                    ("Power", "150 HP", "HP", "Performance"),
                    ("Displacement", "2.1L", "L", "Engine"),
                    ("Cylinders", "4", "count", "Engine"),
                    ("Weight", "430 lbs", "lbs", "Physical"),
                    ("Fuel System", "EFI", "type", "Fuel")
                ]
            },
            {
                "title": "EPIRB Cat II Emergency Beacon",
                "category": ProductCategory.SAFETY_EQUIPMENT,
                "subcategory": "Emergency Equipment",
                "brand": "ACR",
                "model": "ResQLink 400",
                "price": 299.99,
                "condition": ProductCondition.NEW,
                "description": "Compact personal locator beacon with GPS for emergency rescue situations.",
                "specifications": [
                    ("Frequency", "406 MHz", "MHz", "Communication"),
                    ("Battery Life", "5+ years", "years", "Power"),
                    ("GPS Accuracy", "< 5 meters", "meters", "Performance"),
                    ("Operating Temp", "-20 to +55°C", "°C", "Environment"),
                    ("Waterproof", "10m depth", "meters", "Protection")
                ]
            },
            {
                "title": "Grundens Neptune Commercial Rain Jacket",
                "category": ProductCategory.CLOTHING_GEAR,
                "subcategory": "Rain Gear",
                "brand": "Grundens",
                "model": "Neptune",
                "price": 189.99,
                "condition": ProductCondition.NEW,
                "description": "Heavy-duty commercial fishing rain jacket with reinforced shoulders and fully taped seams.",
                "specifications": [
                    ("Material", "PVC", "type", "Construction"),
                    ("Waterproof Rating", "100%", "percent", "Protection"),
                    ("Seam Sealing", "Fully Taped", "type", "Construction"),
                    ("Hood", "Adjustable", "type", "Features"),
                    ("Pockets", "2 Chest", "count", "Features")
                ]
            }
        ]
        
        for i, product_data in enumerate(sample_products):
            product_id = f"prod_{i+1:03d}"
            
            # Create images
            images = [
                ProductImage(
                    image_id=f"img_{product_id}_1",
                    product_id=product_id,
                    url=f"/images/{product_id}_main.jpg",
                    alt_text=product_data["title"],
                    is_primary=True,
                    display_order=1,
                    tags=["main", "product"]
                ),
                ProductImage(
                    image_id=f"img_{product_id}_2",
                    product_id=product_id,
                    url=f"/images/{product_id}_detail.jpg",
                    alt_text=f"{product_data['title']} - Detail View",
                    is_primary=False,
                    display_order=2,
                    tags=["detail", "closeup"]
                )
            ]
            
            # Create specifications
            specifications = [
                ProductSpecification(
                    spec_id=f"spec_{product_id}_{j}",
                    name=spec[0],
                    value=spec[1],
                    unit=spec[2] if len(spec) > 2 else None,
                    category=spec[3] if len(spec) > 3 else "General",
                    display_order=j
                )
                for j, spec in enumerate(product_data.get("specifications", []))
            ]
            
            # Create sample reviews
            reviews = [
                ProductReview(
                    review_id=f"review_{product_id}_1",
                    product_id=product_id,
                    user_id=f"user_{random.randint(1000, 9999)}",
                    rating=random.randint(4, 5),
                    title="Great product!",
                    content="Excellent quality and performs as expected. Highly recommended for professional use.",
                    verified_purchase=True,
                    helpful_votes=random.randint(5, 20),
                    total_votes=random.randint(10, 30),
                    created_at=datetime.now() - timedelta(days=random.randint(1, 90))
                )
            ]
            
            # Create variants if applicable
            variants = []
            if product_data["category"] == ProductCategory.CLOTHING_GEAR:
                variants = [
                    ProductVariant(
                        variant_id=f"var_{product_id}_S",
                        product_id=product_id,
                        name="Small",
                        sku=f"{product_id}_S",
                        price=product_data["price"],
                        stock_quantity=random.randint(5, 20),
                        attributes={"size": "S"}
                    ),
                    ProductVariant(
                        variant_id=f"var_{product_id}_M",
                        product_id=product_id,
                        name="Medium",
                        sku=f"{product_id}_M",
                        price=product_data["price"],
                        stock_quantity=random.randint(5, 20),
                        attributes={"size": "M"}
                    )
                ]
            
            # Create product
            product = Product(
                product_id=product_id,
                title=product_data["title"],
                description=product_data["description"],
                short_description=product_data["description"][:100] + "...",
                category=product_data["category"],
                subcategory=product_data["subcategory"],
                brand=product_data["brand"],
                model=product_data["model"],
                sku=f"SKU_{product_id}",
                price=product_data["price"],
                original_price=product_data.get("original_price"),
                currency="USD",
                condition=product_data["condition"],
                status=ProductStatus.ACTIVE,
                stock_quantity=random.randint(10, 100),
                minimum_order=1,
                vendor_id=f"vendor_{random.randint(100, 999)}",
                vendor_name=f"{product_data['brand']} Marine Supply",
                location=(random.uniform(40.0, 45.0), random.uniform(-75.0, -70.0)),
                location_name=f"{random.choice(['Seattle', 'Portland', 'Boston', 'Miami'])}, WA",
                images=images,
                specifications=specifications,
                variants=variants,
                reviews=reviews,
                tags=[product_data["category"].value, product_data["brand"].lower(), "marine"],
                weight=random.uniform(1.0, 50.0),
                dimensions={"length": random.uniform(10, 50), "width": random.uniform(5, 30), "height": random.uniform(3, 20)},
                shipping_info={"free_shipping": product_data["price"] > 500, "estimated_days": random.randint(3, 7)},
                warranty_info="1 year manufacturer warranty",
                return_policy="30-day return policy",
                created_at=datetime.now() - timedelta(days=random.randint(1, 365)),
                updated_at=datetime.now() - timedelta(days=random.randint(0, 30)),
                view_count=random.randint(100, 2000),
                save_count=random.randint(10, 200),
                average_rating=random.uniform(4.0, 5.0),
                total_reviews=len(reviews),
                popularity_score=random.uniform(0.5, 1.0)
            )
            
            self.products[product_id] = product
        
        # Save to database
        self._save_products_to_db()
    
    def _save_products_to_db(self):
        """Save products to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for product in self.products.values():
            # Insert product
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (product_id, title, description, short_description, category, subcategory,
                 brand, model, sku, price, original_price, currency, condition, status,
                 stock_quantity, minimum_order, vendor_id, vendor_name, latitude, longitude,
                 location_name, tags, weight, dimensions, shipping_info, warranty_info,
                 return_policy, created_at, updated_at, view_count, save_count,
                 average_rating, total_reviews, popularity_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product.product_id, product.title, product.description, product.short_description,
                product.category.value, product.subcategory, product.brand, product.model,
                product.sku, product.price, product.original_price, product.currency,
                product.condition.value, product.status.value, product.stock_quantity,
                product.minimum_order, product.vendor_id, product.vendor_name,
                product.location[0], product.location[1], product.location_name,
                json.dumps(product.tags), product.weight, json.dumps(product.dimensions),
                json.dumps(product.shipping_info), product.warranty_info, product.return_policy,
                product.created_at, product.updated_at, product.view_count, product.save_count,
                product.average_rating, product.total_reviews, product.popularity_score
            ))
            
            # Insert images
            for image in product.images:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_images 
                    (image_id, product_id, url, alt_text, is_primary, display_order, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    image.image_id, image.product_id, image.url, image.alt_text,
                    image.is_primary, image.display_order, json.dumps(image.tags)
                ))
            
            # Insert specifications
            for spec in product.specifications:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_specifications 
                    (spec_id, product_id, name, value, unit, category, display_order)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    spec.spec_id, spec.product_id, spec.name, spec.value,
                    spec.unit, spec.category, spec.display_order
                ))
            
            # Insert reviews
            for review in product.reviews:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_reviews 
                    (review_id, product_id, user_id, rating, title, content,
                     verified_purchase, helpful_votes, total_votes, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    review.review_id, review.product_id, review.user_id, review.rating,
                    review.title, review.content, review.verified_purchase,
                    review.helpful_votes, review.total_votes, review.created_at
                ))
            
            # Insert variants
            for variant in product.variants:
                cursor.execute('''
                    INSERT OR REPLACE INTO product_variants 
                    (variant_id, product_id, name, sku, price, stock_quantity, attributes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    variant.variant_id, variant.product_id, variant.name, variant.sku,
                    variant.price, variant.stock_quantity, json.dumps(variant.attributes)
                ))
        
        conn.commit()
        conn.close()
    
    async def search_products(self, query: str = "", filters: Optional[SearchFilter] = None,
                            sort_by: SortOption = SortOption.RELEVANCE, page: int = 1,
                            per_page: int = 20) -> SearchResult:
        """Search products with advanced filtering and sorting"""
        start_time = time.time()
        
        # Create cache key
        cache_key = f"{query}_{hash(str(filters))}_{sort_by.value}_{page}_{per_page}"
        if cache_key in self.search_cache:
            return self.search_cache[cache_key]
        
        # Start with all products
        matching_products = list(self.products.values())
        
        # Apply text search
        if query:
            query_lower = query.lower()
            matching_products = [
                p for p in matching_products
                if (query_lower in p.title.lower() or
                    query_lower in p.description.lower() or
                    query_lower in p.brand.lower() or
                    query_lower in p.model.lower() or
                    any(query_lower in tag.lower() for tag in p.tags))
            ]
        
        # Apply filters
        if filters:
            if filters.categories:
                matching_products = [p for p in matching_products if p.category in filters.categories]
            
            if filters.price_range:
                min_price, max_price = filters.price_range
                matching_products = [p for p in matching_products if min_price <= p.price <= max_price]
            
            if filters.condition:
                matching_products = [p for p in matching_products if p.condition in filters.condition]
            
            if filters.location_radius:
                lat, lon, radius_km = filters.location_radius
                matching_products = [
                    p for p in matching_products
                    if self._calculate_distance(lat, lon, p.location[0], p.location[1]) <= radius_km
                ]
            
            if filters.brands:
                matching_products = [p for p in matching_products if p.brand in filters.brands]
            
            if filters.tags:
                matching_products = [
                    p for p in matching_products
                    if any(tag in p.tags for tag in filters.tags)
                ]
            
            if filters.in_stock_only:
                matching_products = [p for p in matching_products if p.stock_quantity > 0]
            
            if filters.with_reviews_only:
                matching_products = [p for p in matching_products if p.total_reviews > 0]
            
            if filters.min_rating:
                matching_products = [p for p in matching_products if p.average_rating >= filters.min_rating]
        
        # Sort products
        matching_products = self._sort_products(matching_products, sort_by)
        
        # Calculate facets
        facets = self._calculate_facets(matching_products)
        
        # Paginate
        total_count = len(matching_products)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_products = matching_products[start_idx:end_idx]
        
        # Generate suggested filters
        suggested_filters = self._generate_suggested_filters(matching_products, filters)
        
        search_time = time.time() - start_time
        
        result = SearchResult(
            products=paginated_products,
            total_count=total_count,
            facets=facets,
            suggested_filters=suggested_filters,
            search_time=search_time,
            page=page,
            per_page=per_page
        )
        
        # Cache result
        self.search_cache[cache_key] = result
        
        # Log search analytics
        await self._log_search_analytics(query, filters, result)
        
        return result
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers"""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c
    
    def _sort_products(self, products: List[Product], sort_by: SortOption) -> List[Product]:
        """Sort products based on sort option"""
        if sort_by == SortOption.PRICE_LOW_HIGH:
            return sorted(products, key=lambda p: p.price)
        elif sort_by == SortOption.PRICE_HIGH_LOW:
            return sorted(products, key=lambda p: p.price, reverse=True)
        elif sort_by == SortOption.DATE_NEWEST:
            return sorted(products, key=lambda p: p.created_at, reverse=True)
        elif sort_by == SortOption.DATE_OLDEST:
            return sorted(products, key=lambda p: p.created_at)
        elif sort_by == SortOption.POPULARITY:
            return sorted(products, key=lambda p: p.popularity_score, reverse=True)
        elif sort_by == SortOption.RATING:
            return sorted(products, key=lambda p: p.average_rating, reverse=True)
        else:  # RELEVANCE or default
            return sorted(products, key=lambda p: (p.popularity_score * 0.6 + p.average_rating * 0.4), reverse=True)
    
    def _calculate_facets(self, products: List[Product]) -> Dict[str, Dict[str, int]]:
        """Calculate facet counts for filtering"""
        facets = {}
        
        # Category facets
        category_counts = {}
        for product in products:
            cat = product.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        facets["categories"] = category_counts
        
        # Brand facets
        brand_counts = {}
        for product in products:
            brand = product.brand
            brand_counts[brand] = brand_counts.get(brand, 0) + 1
        facets["brands"] = brand_counts
        
        # Condition facets
        condition_counts = {}
        for product in products:
            cond = product.condition.value
            condition_counts[cond] = condition_counts.get(cond, 0) + 1
        facets["conditions"] = condition_counts
        
        # Price ranges
        price_ranges = {
            "$0-$100": 0, "$100-$500": 0, "$500-$1000": 0,
            "$1000-$5000": 0, "$5000+": 0
        }
        for product in products:
            price = product.price
            if price < 100:
                price_ranges["$0-$100"] += 1
            elif price < 500:
                price_ranges["$100-$500"] += 1
            elif price < 1000:
                price_ranges["$500-$1000"] += 1
            elif price < 5000:
                price_ranges["$1000-$5000"] += 1
            else:
                price_ranges["$5000+"] += 1
        facets["price_ranges"] = price_ranges
        
        return facets
    
    def _generate_suggested_filters(self, products: List[Product], current_filters: Optional[SearchFilter]) -> List[str]:
        """Generate suggested filters based on search results"""
        suggestions = []
        
        if len(products) > 50:
            # Suggest narrowing by popular brands
            brand_counts = {}
            for product in products:
                brand_counts[product.brand] = brand_counts.get(product.brand, 0) + 1
            
            top_brands = sorted(brand_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            for brand, count in top_brands:
                suggestions.append(f"Filter by {brand} ({count} items)")
        
        if not current_filters or not current_filters.price_range:
            # Suggest price range if not already filtered
            prices = [p.price for p in products]
            if prices:
                avg_price = sum(prices) / len(prices)
                if avg_price > 500:
                    suggestions.append("Filter by price: Under $500")
                else:
                    suggestions.append("Filter by price: Over $1000")
        
        return suggestions
    
    async def _log_search_analytics(self, query: str, filters: Optional[SearchFilter], result: SearchResult):
        """Log search analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        search_id = f"search_{int(time.time())}_{random.randint(1000, 9999)}"
        
        cursor.execute('''
            INSERT INTO search_analytics 
            (search_id, query, filters, results_count, search_time, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            search_id,
            query,
            json.dumps(asdict(filters)) if filters else None,
            result.total_count,
            result.search_time,
            datetime.now()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_product_details(self, product_id: str) -> Optional[Product]:
        """Get detailed product information"""
        if product_id in self.products:
            product = self.products[product_id]
            
            # Increment view count
            product.view_count += 1
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE products SET view_count = ? WHERE product_id = ?', 
                         (product.view_count, product_id))
            conn.commit()
            conn.close()
            
            return product
        return None
    
    async def add_to_wishlist(self, product_id: str, user_id: str) -> bool:
        """Add product to user's wishlist"""
        if product_id in self.products:
            product = self.products[product_id]
            product.save_count += 1
            
            # Update in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE products SET save_count = ? WHERE product_id = ?', 
                         (product.save_count, product_id))
            conn.commit()
            conn.close()
            
            logger.info(f"Product {product_id} added to wishlist by user {user_id}")
            return True
        return False
    
    def get_trending_products(self, limit: int = 10) -> List[Product]:
        """Get trending products based on recent activity"""
        # Calculate trending score based on recent views and saves
        trending_products = []
        for product in self.products.values():
            # Simple trending algorithm
            trending_score = (product.view_count * 0.7 + product.save_count * 0.3) / max(1, (datetime.now() - product.created_at).days)
            trending_products.append((product, trending_score))
        
        # Sort by trending score and return top products
        trending_products.sort(key=lambda x: x[1], reverse=True)
        return [product for product, score in trending_products[:limit]]
    
    def get_featured_products(self, category: Optional[ProductCategory] = None, limit: int = 6) -> List[Product]:
        """Get featured products for display"""
        products = list(self.products.values())
        
        if category:
            products = [p for p in products if p.category == category]
        
        # Select products with high ratings and good stock
        featured = [
            p for p in products
            if p.average_rating >= 4.0 and p.stock_quantity > 0 and p.status == ProductStatus.ACTIVE
        ]
        
        # Sort by combination of rating and popularity
        featured.sort(key=lambda p: (p.average_rating * 0.6 + p.popularity_score * 0.4), reverse=True)
        
        return featured[:limit]
    
    def get_categories_overview(self) -> Dict[str, Dict[str, Any]]:
        """Get overview of all product categories"""
        categories = {}
        
        for category in ProductCategory:
            category_products = [p for p in self.products.values() if p.category == category]
            
            if category_products:
                avg_price = sum(p.price for p in category_products) / len(category_products)
                total_products = len(category_products)
                avg_rating = sum(p.average_rating for p in category_products) / len(category_products)
                
                categories[category.value] = {
                    "name": category.value.replace("_", " ").title(),
                    "total_products": total_products,
                    "average_price": avg_price,
                    "average_rating": avg_rating,
                    "featured_product": max(category_products, key=lambda p: p.popularity_score)
                }
        
        return categories
    
    def get_search_suggestions(self, partial_query: str) -> List[str]:
        """Get search suggestions based on partial query"""
        suggestions = set()
        query_lower = partial_query.lower()
        
        for product in self.products.values():
            # Add matching product titles
            if query_lower in product.title.lower():
                suggestions.add(product.title)
            
            # Add matching brands
            if query_lower in product.brand.lower():
                suggestions.add(product.brand)
            
            # Add matching models
            if query_lower in product.model.lower():
                suggestions.add(f"{product.brand} {product.model}")
            
            # Add matching tags
            for tag in product.tags:
                if query_lower in tag.lower():
                    suggestions.add(tag.replace("_", " ").title())
        
        return sorted(list(suggestions))[:10]  # Return top 10 suggestions
    
    def _run_analytics(self):
        """Background analytics processing"""
        while True:
            try:
                self._update_popularity_scores()
                time.sleep(3600)  # Update every hour
            except Exception as e:
                logger.error(f"Analytics error: {e}")
    
    def _update_popularity_scores(self):
        """Update product popularity scores based on views, saves, and reviews"""
        for product in self.products.values():
            # Calculate popularity based on normalized metrics
            view_score = min(1.0, product.view_count / 1000.0)  # Normalize to 1000 views
            save_score = min(1.0, product.save_count / 100.0)   # Normalize to 100 saves
            rating_score = product.average_rating / 5.0          # Normalize to 5 stars
            review_score = min(1.0, product.total_reviews / 50.0) # Normalize to 50 reviews
            
            # Weighted combination
            product.popularity_score = (
                view_score * 0.3 +
                save_score * 0.3 +
                rating_score * 0.2 +
                review_score * 0.2
            )
        
        logger.info("Updated popularity scores for all products")
    
    def get_browser_analytics(self) -> Dict[str, Any]:
        """Get browser analytics and statistics"""
        total_products = len(self.products)
        active_products = len([p for p in self.products.values() if p.status == ProductStatus.ACTIVE])
        
        # Category distribution
        category_dist = {}
        for product in self.products.values():
            cat = product.category.value
            category_dist[cat] = category_dist.get(cat, 0) + 1
        
        # Price statistics
        prices = [p.price for p in self.products.values()]
        price_stats = {
            "min_price": min(prices) if prices else 0,
            "max_price": max(prices) if prices else 0,
            "avg_price": sum(prices) / len(prices) if prices else 0,
            "median_price": sorted(prices)[len(prices)//2] if prices else 0
        }
        
        # Top products
        top_viewed = sorted(self.products.values(), key=lambda p: p.view_count, reverse=True)[:5]
        top_saved = sorted(self.products.values(), key=lambda p: p.save_count, reverse=True)[:5]
        
        return {
            "total_products": total_products,
            "active_products": active_products,
            "category_distribution": category_dist,
            "price_statistics": price_stats,
            "top_viewed_products": [{"id": p.product_id, "title": p.title, "views": p.view_count} for p in top_viewed],
            "top_saved_products": [{"id": p.product_id, "title": p.title, "saves": p.save_count} for p in top_saved],
            "cache_size": len(self.search_cache)
        }

# Example usage and testing
async def main():
    browser = VisualProductBrowser()
    
    print("=== Marketplace v2 - Visual Product Browser ===")
    
    # Search products
    print("\n=== Product Search ===")
    search_result = await browser.search_products(
        query="GPS",
        sort_by=SortOption.PRICE_LOW_HIGH
    )
    print(f"Found {search_result.total_count} products in {search_result.search_time:.3f}s")
    for product in search_result.products[:3]:
        print(f"- {product.title} - ${product.price}")
    
    # Get product details
    if search_result.products:
        product_id = search_result.products[0].product_id
        product_details = await browser.get_product_details(product_id)
        print(f"\n=== Product Details: {product_details.title} ===")
        print(f"Brand: {product_details.brand}")
        print(f"Price: ${product_details.price}")
        print(f"Rating: {product_details.average_rating:.1f}/5")
        print(f"Stock: {product_details.stock_quantity}")
    
    # Get trending products
    trending = browser.get_trending_products(limit=3)
    print(f"\n=== Trending Products ({len(trending)}) ===")
    for product in trending:
        print(f"- {product.title} (Views: {product.view_count}, Saves: {product.save_count})")
    
    # Get categories overview
    categories = browser.get_categories_overview()
    print(f"\n=== Categories Overview ({len(categories)}) ===")
    for cat_name, cat_data in categories.items():
        print(f"- {cat_data['name']}: {cat_data['total_products']} products, avg ${cat_data['average_price']:.2f}")
    
    # Analytics
    analytics = browser.get_browser_analytics()
    print(f"\n=== Analytics ===")
    print(f"Total Products: {analytics['total_products']}")
    print(f"Active Products: {analytics['active_products']}")
    print(f"Price Range: ${analytics['price_statistics']['min_price']:.2f} - ${analytics['price_statistics']['max_price']:.2f}")

if __name__ == "__main__":
    asyncio.run(main())