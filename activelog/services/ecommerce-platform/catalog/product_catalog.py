"""
Product Catalog Management
Handles product creation, management, and catalog operations
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class ProductStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ProductType(Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"
    SERVICE = "service"
    SUBSCRIPTION = "subscription"


@dataclass
class Product:
    product_id: str
    name: str
    description: str
    category_id: str
    price: float
    compare_price: Optional[float]
    cost_price: Optional[float]
    sku: str
    barcode: Optional[str]
    product_type: ProductType
    status: ProductStatus
    images: List[str]
    tags: List[str]
    meta_title: Optional[str]
    meta_description: Optional[str]
    weight: Optional[float]
    dimensions: Optional[Dict[str, float]]
    created_at: datetime
    updated_at: datetime


class ProductCatalogManager:
    """Manages product catalog operations"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.product_cache = {}
        
    def create_product(self, product_data: Dict[str, Any]) -> str:
        """Create new product"""
        try:
            product_id = f"prod_{datetime.now().timestamp()}"
            
            # Validate required fields
            required_fields = ['name', 'description', 'category_id', 'price', 'sku']
            for field in required_fields:
                if field not in product_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create product record
            product = {
                'product_id': product_id,
                'name': product_data['name'],
                'description': product_data['description'],
                'category_id': product_data['category_id'],
                'price': float(product_data['price']),
                'compare_price': product_data.get('compare_price'),
                'cost_price': product_data.get('cost_price'),
                'sku': product_data['sku'],
                'barcode': product_data.get('barcode'),
                'product_type': product_data.get('product_type', 'physical'),
                'status': product_data.get('status', 'draft'),
                'images': product_data.get('images', []),
                'tags': product_data.get('tags', []),
                'meta_title': product_data.get('meta_title'),
                'meta_description': product_data.get('meta_description'),
                'weight': product_data.get('weight'),
                'dimensions': product_data.get('dimensions', {}),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save to database
            self.db.save_product(product)
            
            # Create initial inventory record
            self.create_initial_inventory(product_id, product_data.get('initial_quantity', 0))
            
            # Generate SEO-friendly URL
            self.generate_product_url(product_id, product_data['name'])
            
            return product_id
            
        except Exception as e:
            raise Exception(f"Error creating product: {e}")
            
    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get product by ID"""
        try:
            # Check cache first
            if product_id in self.product_cache:
                return self.product_cache[product_id]
                
            # Get from database
            product = self.db.get_product(product_id)
            if product:
                # Add calculated fields
                product = self.enrich_product_data(product)
                self.product_cache[product_id] = product
                
            return product
            
        except Exception as e:
            raise Exception(f"Error getting product: {e}")
            
    def update_product(self, product_id: str, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update product"""
        try:
            # Get existing product
            existing_product = self.db.get_product(product_id)
            if not existing_product:
                raise ValueError("Product not found")
                
            # Update fields
            updated_product = existing_product.copy()
            updated_product.update(product_data)
            updated_product['updated_at'] = datetime.now().isoformat()
            
            # Save to database
            self.db.update_product(product_id, updated_product)
            
            # Clear cache
            if product_id in self.product_cache:
                del self.product_cache[product_id]
                
            return updated_product
            
        except Exception as e:
            raise Exception(f"Error updating product: {e}")
            
    def delete_product(self, product_id: str) -> bool:
        """Delete product (soft delete)"""
        try:
            # Update status to archived instead of hard delete
            result = self.update_product(product_id, {
                'status': 'archived',
                'archived_at': datetime.now().isoformat()
            })
            
            return bool(result)
            
        except Exception as e:
            raise Exception(f"Error deleting product: {e}")
            
    def list_products(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List products with pagination and filtering"""
        try:
            if filters is None:
                filters = {}
                
            # Get products from database
            products = self.db.list_products(filters, page, limit)
            
            # Enrich product data
            enriched_products = []
            for product in products:
                enriched_product = self.enrich_product_data(product)
                enriched_products.append(enriched_product)
                
            # Get total count for pagination
            total_count = self.db.get_product_count(filters)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'products': enriched_products,
                'pagination': {
                    'page': page,
                    'limit': limit,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
                'filters_applied': filters
            }
            
        except Exception as e:
            raise Exception(f"Error listing products: {e}")
            
    def search_products(self, query: str, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Search products by name, description, tags"""
        try:
            if not query:
                return []
                
            # Perform database search
            products = self.db.search_products(query, filters)
            
            # Enrich and sort by relevance
            enriched_products = []
            for product in products:
                enriched_product = self.enrich_product_data(product)
                enriched_product['relevance_score'] = self.calculate_relevance_score(product, query)
                enriched_products.append(enriched_product)
                
            # Sort by relevance score
            enriched_products.sort(key=lambda x: x['relevance_score'], reverse=True)
            
            return enriched_products
            
        except Exception as e:
            raise Exception(f"Error searching products: {e}")
            
    def get_categories(self) -> List[Dict[str, Any]]:
        """Get all product categories"""
        try:
            categories = self.db.get_categories()
            
            # Add product count for each category
            for category in categories:
                category['product_count'] = self.db.get_category_product_count(category['category_id'])
                
            return categories
            
        except Exception as e:
            raise Exception(f"Error getting categories: {e}")
            
    def create_category(self, category_data: Dict[str, Any]) -> str:
        """Create new product category"""
        try:
            category_id = f"cat_{datetime.now().timestamp()}"
            
            category = {
                'category_id': category_id,
                'name': category_data['name'],
                'description': category_data.get('description', ''),
                'parent_id': category_data.get('parent_id'),
                'image': category_data.get('image'),
                'meta_title': category_data.get('meta_title'),
                'meta_description': category_data.get('meta_description'),
                'sort_order': category_data.get('sort_order', 0),
                'status': category_data.get('status', 'active'),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.db.save_category(category)
            return category_id
            
        except Exception as e:
            raise Exception(f"Error creating category: {e}")
            
    def get_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """Get product variants (size, color, etc.)"""
        try:
            variants = self.db.get_product_variants(product_id)
            
            # Enrich variant data
            for variant in variants:
                variant['inventory'] = self.get_variant_inventory(variant['variant_id'])
                variant['images'] = self.get_variant_images(variant['variant_id'])
                
            return variants
            
        except Exception as e:
            raise Exception(f"Error getting product variants: {e}")
            
    def create_product_variant(self, product_id: str, variant_data: Dict[str, Any]) -> str:
        """Create product variant"""
        try:
            variant_id = f"var_{datetime.now().timestamp()}"
            
            variant = {
                'variant_id': variant_id,
                'product_id': product_id,
                'title': variant_data['title'],
                'price': float(variant_data.get('price', 0)),
                'compare_price': variant_data.get('compare_price'),
                'cost_price': variant_data.get('cost_price'),
                'sku': variant_data.get('sku', f"{product_id}-{variant_id}"),
                'barcode': variant_data.get('barcode'),
                'weight': variant_data.get('weight'),
                'dimensions': variant_data.get('dimensions', {}),
                'option1': variant_data.get('option1'),  # e.g., Size
                'option2': variant_data.get('option2'),  # e.g., Color
                'option3': variant_data.get('option3'),  # e.g., Material
                'image': variant_data.get('image'),
                'position': variant_data.get('position', 1),
                'inventory_quantity': variant_data.get('inventory_quantity', 0),
                'inventory_policy': variant_data.get('inventory_policy', 'deny'),
                'fulfillment_service': variant_data.get('fulfillment_service', 'manual'),
                'requires_shipping': variant_data.get('requires_shipping', True),
                'taxable': variant_data.get('taxable', True),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.db.save_product_variant(variant)
            return variant_id
            
        except Exception as e:
            raise Exception(f"Error creating product variant: {e}")
            
    def get_product_reviews_summary(self, product_id: str) -> Dict[str, Any]:
        """Get product reviews summary"""
        try:
            reviews_data = self.db.get_product_reviews_summary(product_id)
            
            return {
                'average_rating': reviews_data.get('average_rating', 0),
                'total_reviews': reviews_data.get('total_reviews', 0),
                'rating_distribution': reviews_data.get('rating_distribution', {}),
                'recent_reviews': reviews_data.get('recent_reviews', [])
            }
            
        except Exception as e:
            return {
                'average_rating': 0,
                'total_reviews': 0,
                'rating_distribution': {},
                'recent_reviews': []
            }
            
    def get_related_products(self, product_id: str, limit: int = 6) -> List[Dict[str, Any]]:
        """Get related products based on category and tags"""
        try:
            product = self.get_product(product_id)
            if not product:
                return []
                
            # Find products in same category with similar tags
            related_products = self.db.get_related_products(
                product['category_id'],
                product.get('tags', []),
                product_id,
                limit
            )
            
            # Enrich product data
            enriched_related = []
            for related in related_products:
                enriched_product = self.enrich_product_data(related)
                enriched_related.append(enriched_product)
                
            return enriched_related
            
        except Exception as e:
            raise Exception(f"Error getting related products: {e}")
            
    def enrich_product_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich product data with calculated fields"""
        try:
            # Add inventory information
            product['inventory'] = self.get_product_inventory_summary(product['product_id'])
            
            # Add reviews summary
            product['reviews_summary'] = self.get_product_reviews_summary(product['product_id'])
            
            # Add discount information
            if product.get('compare_price') and product['price'] < product['compare_price']:
                discount_amount = product['compare_price'] - product['price']
                discount_percentage = (discount_amount / product['compare_price']) * 100
                product['discount'] = {
                    'amount': discount_amount,
                    'percentage': round(discount_percentage, 2)
                }
            
            # Add URL
            product['url'] = self.generate_product_url(product['product_id'], product['name'])
            
            # Add image URLs
            if product.get('images'):
                product['featured_image'] = product['images'][0] if product['images'] else None
                product['image_urls'] = [self.get_image_url(image) for image in product['images']]
            
            return product
            
        except Exception as e:
            # Return product as-is if enrichment fails
            return product
            
    def get_product_inventory_summary(self, product_id: str) -> Dict[str, Any]:
        """Get product inventory summary"""
        try:
            return {
                'total_quantity': 100,
                'available_quantity': 95,
                'reserved_quantity': 5,
                'low_stock_threshold': 10,
                'is_low_stock': False,
                'is_in_stock': True
            }
        except Exception:
            return {
                'total_quantity': 0,
                'available_quantity': 0,
                'reserved_quantity': 0,
                'low_stock_threshold': 0,
                'is_low_stock': True,
                'is_in_stock': False
            }
            
    def calculate_relevance_score(self, product: Dict[str, Any], query: str) -> float:
        """Calculate search relevance score"""
        try:
            score = 0
            query_lower = query.lower()
            
            # Name match (highest weight)
            if query_lower in product['name'].lower():
                score += 10
                if product['name'].lower().startswith(query_lower):
                    score += 5
                    
            # Description match
            if query_lower in product['description'].lower():
                score += 5
                
            # Tags match
            for tag in product.get('tags', []):
                if query_lower in tag.lower():
                    score += 3
                    
            # SKU match
            if query_lower in product.get('sku', '').lower():
                score += 8
                
            return score
            
        except Exception:
            return 0
            
    def generate_product_url(self, product_id: str, product_name: str) -> str:
        """Generate SEO-friendly product URL"""
        try:
            # Create slug from product name
            slug = product_name.lower().replace(' ', '-').replace('/', '-')
            slug = ''.join(c for c in slug if c.isalnum() or c == '-')
            return f"/products/{slug}-{product_id}"
        except Exception:
            return f"/products/{product_id}"
            
    def get_image_url(self, image_path: str) -> str:
        """Get full image URL"""
        try:
            base_url = self.config.get('cdn_base_url', 'https://cdn.activelog.com')
            return f"{base_url}/images/{image_path}"
        except Exception:
            return image_path
            
    def create_initial_inventory(self, product_id: str, quantity: int = 0):
        """Create initial inventory record for product"""
        try:
            inventory_data = {
                'product_id': product_id,
                'quantity': quantity,
                'reserved_quantity': 0,
                'location': 'default',
                'updated_at': datetime.now().isoformat()
            }
            self.db.save_inventory(inventory_data)
        except Exception as e:
            # Log error but don't fail product creation
            print(f"Warning: Could not create initial inventory: {e}")
            
    def get_variant_inventory(self, variant_id: str) -> Dict[str, Any]:
        """Get variant inventory information"""
        try:
            return {
                'quantity': 50,
                'reserved': 2,
                'available': 48
            }
        except Exception:
            return {'quantity': 0, 'reserved': 0, 'available': 0}
            
    def get_variant_images(self, variant_id: str) -> List[str]:
        """Get variant-specific images"""
        try:
            return []  # Would fetch from database
        except Exception:
            return []
            
    def get_product_count(self) -> int:
        """Get total product count"""
        try:
            return self.db.get_product_count()
        except Exception:
            return 0