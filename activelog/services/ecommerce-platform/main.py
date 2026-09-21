#!/usr/bin/env python3
"""
ActiveLog E-commerce Platform
Main service file for comprehensive e-commerce functionality
Port: 8355
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from decimal import Decimal

from flask import Flask, jsonify, request
from flask_cors import CORS

# E-commerce components
from catalog.product_catalog import ProductCatalogManager
from cart.shopping_cart import ShoppingCartManager
from checkout.checkout_system import CheckoutSystem
from payments.payment_processor import PaymentProcessor
from shipping.shipping_calculator import ShippingCalculator
from tax.tax_calculator import TaxCalculator
from inventory.inventory_sync import InventoryManager
from orders.order_manager import OrderManager
from customers.customer_accounts import CustomerAccountManager
from wishlist.wishlist_system import WishlistManager
from reviews.reviews_ratings import ReviewsRatingsManager
from affiliates.affiliate_tracking import AffiliateTracker

from config.ecommerce_config import EcommerceConfig
from database.ecommerce_db import EcommerceDatabase


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class EcommercePlatformInfo:
    name: str
    version: str
    status: str
    total_products: int
    active_orders: int
    registered_customers: int
    revenue_today: float


class EcommercePlatformService:
    """Main e-commerce platform service orchestrating all components"""
    
    def __init__(self):
        self.config = EcommerceConfig()
        self.db = EcommerceDatabase()
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize e-commerce components
        self.product_catalog = ProductCatalogManager(self.config, self.db)
        self.shopping_cart = ShoppingCartManager(self.config, self.db)
        self.checkout = CheckoutSystem(self.config, self.db)
        self.payments = PaymentProcessor(self.config, self.db)
        self.shipping = ShippingCalculator(self.config, self.db)
        self.tax = TaxCalculator(self.config, self.db)
        self.inventory = InventoryManager(self.config, self.db)
        self.orders = OrderManager(self.config, self.db)
        self.customers = CustomerAccountManager(self.config, self.db)
        self.wishlist = WishlistManager(self.config, self.db)
        self.reviews = ReviewsRatingsManager(self.config, self.db)
        self.affiliates = AffiliateTracker(self.config, self.db)
        
        self.setup_routes()
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('ecommerce-platform')
        
    def setup_routes(self):
        """Setup all API routes"""
        
        # Health check
        @self.app.route('/health', methods=['GET'])
        def health():
            platform_info = self.get_platform_info()
            return jsonify({
                'status': 'healthy',
                'service': 'ecommerce-platform',
                'port': 8355,
                'timestamp': datetime.now().isoformat(),
                'platform_info': asdict(platform_info)
            })
            
        # ======== PRODUCT CATALOG ROUTES ========
        @self.app.route('/catalog/products', methods=['GET'])
        def list_products():
            """List all products with pagination and filtering"""
            try:
                category = request.args.get('category')
                search = request.args.get('search')
                min_price = request.args.get('min_price', type=float)
                max_price = request.args.get('max_price', type=float)
                page = request.args.get('page', 1, type=int)
                limit = request.args.get('limit', 20, type=int)
                
                filters = {}
                if category:
                    filters['category'] = category
                if search:
                    filters['search'] = search
                if min_price is not None:
                    filters['min_price'] = min_price
                if max_price is not None:
                    filters['max_price'] = max_price
                    
                result = self.product_catalog.list_products(filters, page, limit)
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/catalog/products/<product_id>', methods=['GET'])
        def get_product(product_id):
            """Get product details"""
            try:
                product = self.product_catalog.get_product(product_id)
                if not product:
                    return jsonify({'error': 'Product not found'}), 404
                return jsonify(product)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/catalog/products', methods=['POST'])
        def create_product():
            """Create new product"""
            try:
                product_data = request.json
                product_id = self.product_catalog.create_product(product_data)
                return jsonify({
                    'message': 'Product created successfully',
                    'product_id': product_id
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/catalog/categories', methods=['GET'])
        def list_categories():
            """List product categories"""
            try:
                categories = self.product_catalog.get_categories()
                return jsonify({
                    'categories': categories,
                    'count': len(categories)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== SHOPPING CART ROUTES ========
        @self.app.route('/cart/<session_id>', methods=['GET'])
        def get_cart(session_id):
            """Get shopping cart contents"""
            try:
                cart = self.shopping_cart.get_cart(session_id)
                return jsonify(cart)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/cart/<session_id>/add', methods=['POST'])
        def add_to_cart(session_id):
            """Add item to shopping cart"""
            try:
                item_data = request.json
                result = self.shopping_cart.add_item(session_id, item_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/cart/<session_id>/update', methods=['PUT'])
        def update_cart_item(session_id):
            """Update cart item quantity"""
            try:
                update_data = request.json
                result = self.shopping_cart.update_item(session_id, update_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/cart/<session_id>/remove/<item_id>', methods=['DELETE'])
        def remove_from_cart(session_id, item_id):
            """Remove item from cart"""
            try:
                result = self.shopping_cart.remove_item(session_id, item_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/cart/<session_id>/clear', methods=['DELETE'])
        def clear_cart(session_id):
            """Clear entire cart"""
            try:
                result = self.shopping_cart.clear_cart(session_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== CHECKOUT ROUTES ========
        @self.app.route('/checkout/initialize', methods=['POST'])
        def initialize_checkout():
            """Initialize checkout process"""
            try:
                checkout_data = request.json
                result = self.checkout.initialize_checkout(checkout_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/checkout/calculate', methods=['POST'])
        def calculate_totals():
            """Calculate order totals including tax and shipping"""
            try:
                calculation_data = request.json
                result = self.checkout.calculate_totals(calculation_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/checkout/complete', methods=['POST'])
        def complete_checkout():
            """Complete checkout process"""
            try:
                order_data = request.json
                result = self.checkout.complete_checkout(order_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== PAYMENT ROUTES ========
        @self.app.route('/payments/process', methods=['POST'])
        def process_payment():
            """Process payment"""
            try:
                payment_data = request.json
                result = self.payments.process_payment(payment_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/payments/<payment_id>/status', methods=['GET'])
        def get_payment_status(payment_id):
            """Get payment status"""
            try:
                status = self.payments.get_payment_status(payment_id)
                return jsonify(status)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/payments/<payment_id>/refund', methods=['POST'])
        def refund_payment(payment_id):
            """Process payment refund"""
            try:
                refund_data = request.json
                result = self.payments.refund_payment(payment_id, refund_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== SHIPPING ROUTES ========
        @self.app.route('/shipping/calculate', methods=['POST'])
        def calculate_shipping():
            """Calculate shipping costs"""
            try:
                shipping_data = request.json
                result = self.shipping.calculate_shipping(shipping_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/shipping/methods', methods=['GET'])
        def get_shipping_methods():
            """Get available shipping methods"""
            try:
                methods = self.shipping.get_shipping_methods()
                return jsonify({
                    'shipping_methods': methods,
                    'count': len(methods)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== TAX ROUTES ========
        @self.app.route('/tax/calculate', methods=['POST'])
        def calculate_tax():
            """Calculate tax for order"""
            try:
                tax_data = request.json
                result = self.tax.calculate_tax(tax_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/tax/rates', methods=['GET'])
        def get_tax_rates():
            """Get tax rates by location"""
            try:
                location = request.args.get('location')
                rates = self.tax.get_tax_rates(location)
                return jsonify(rates)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== INVENTORY ROUTES ========
        @self.app.route('/inventory/<product_id>', methods=['GET'])
        def get_inventory(product_id):
            """Get inventory levels for product"""
            try:
                inventory = self.inventory.get_inventory(product_id)
                return jsonify(inventory)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/inventory/<product_id>/update', methods=['PUT'])
        def update_inventory(product_id):
            """Update inventory levels"""
            try:
                inventory_data = request.json
                result = self.inventory.update_inventory(product_id, inventory_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/inventory/sync', methods=['POST'])
        def sync_inventory():
            """Sync inventory across channels"""
            try:
                sync_data = request.json
                result = self.inventory.sync_inventory(sync_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== ORDER ROUTES ========
        @self.app.route('/orders', methods=['GET'])
        def list_orders():
            """List orders with filtering"""
            try:
                status = request.args.get('status')
                customer_id = request.args.get('customer_id')
                date_from = request.args.get('date_from')
                date_to = request.args.get('date_to')
                page = request.args.get('page', 1, type=int)
                limit = request.args.get('limit', 20, type=int)
                
                filters = {}
                if status:
                    filters['status'] = status
                if customer_id:
                    filters['customer_id'] = customer_id
                if date_from:
                    filters['date_from'] = date_from
                if date_to:
                    filters['date_to'] = date_to
                    
                result = self.orders.list_orders(filters, page, limit)
                return jsonify(result)
                
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/orders/<order_id>', methods=['GET'])
        def get_order(order_id):
            """Get order details"""
            try:
                order = self.orders.get_order(order_id)
                if not order:
                    return jsonify({'error': 'Order not found'}), 404
                return jsonify(order)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/orders/<order_id>/status', methods=['PUT'])
        def update_order_status(order_id):
            """Update order status"""
            try:
                status_data = request.json
                result = self.orders.update_order_status(order_id, status_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== CUSTOMER ROUTES ========
        @self.app.route('/customers/register', methods=['POST'])
        def register_customer():
            """Register new customer"""
            try:
                customer_data = request.json
                result = self.customers.register_customer(customer_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/customers/login', methods=['POST'])
        def customer_login():
            """Customer login"""
            try:
                login_data = request.json
                result = self.customers.authenticate_customer(login_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/customers/<customer_id>', methods=['GET'])
        def get_customer(customer_id):
            """Get customer profile"""
            try:
                customer = self.customers.get_customer(customer_id)
                if not customer:
                    return jsonify({'error': 'Customer not found'}), 404
                return jsonify(customer)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/customers/<customer_id>/addresses', methods=['GET'])
        def get_customer_addresses(customer_id):
            """Get customer addresses"""
            try:
                addresses = self.customers.get_customer_addresses(customer_id)
                return jsonify({
                    'addresses': addresses,
                    'count': len(addresses)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/customers/<customer_id>/addresses', methods=['POST'])
        def add_customer_address(customer_id):
            """Add customer address"""
            try:
                address_data = request.json
                result = self.customers.add_customer_address(customer_id, address_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== WISHLIST ROUTES ========
        @self.app.route('/wishlist/<customer_id>', methods=['GET'])
        def get_wishlist(customer_id):
            """Get customer wishlist"""
            try:
                wishlist = self.wishlist.get_wishlist(customer_id)
                return jsonify(wishlist)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/wishlist/<customer_id>/add', methods=['POST'])
        def add_to_wishlist(customer_id):
            """Add item to wishlist"""
            try:
                item_data = request.json
                result = self.wishlist.add_to_wishlist(customer_id, item_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/wishlist/<customer_id>/remove/<product_id>', methods=['DELETE'])
        def remove_from_wishlist(customer_id, product_id):
            """Remove item from wishlist"""
            try:
                result = self.wishlist.remove_from_wishlist(customer_id, product_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== REVIEWS ROUTES ========
        @self.app.route('/reviews/product/<product_id>', methods=['GET'])
        def get_product_reviews(product_id):
            """Get reviews for product"""
            try:
                page = request.args.get('page', 1, type=int)
                limit = request.args.get('limit', 10, type=int)
                
                reviews = self.reviews.get_product_reviews(product_id, page, limit)
                return jsonify(reviews)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/reviews', methods=['POST'])
        def create_review():
            """Create product review"""
            try:
                review_data = request.json
                result = self.reviews.create_review(review_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/reviews/<review_id>/helpful', methods=['POST'])
        def mark_review_helpful(review_id):
            """Mark review as helpful"""
            try:
                result = self.reviews.mark_helpful(review_id)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== AFFILIATE ROUTES ========
        @self.app.route('/affiliates/register', methods=['POST'])
        def register_affiliate():
            """Register new affiliate"""
            try:
                affiliate_data = request.json
                result = self.affiliates.register_affiliate(affiliate_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/affiliates/<affiliate_id>/links', methods=['GET'])
        def get_affiliate_links(affiliate_id):
            """Get affiliate tracking links"""
            try:
                links = self.affiliates.get_affiliate_links(affiliate_id)
                return jsonify(links)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/affiliates/<affiliate_id>/stats', methods=['GET'])
        def get_affiliate_stats(affiliate_id):
            """Get affiliate statistics"""
            try:
                stats = self.affiliates.get_affiliate_stats(affiliate_id)
                return jsonify(stats)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/affiliates/track', methods=['POST'])
        def track_affiliate_click():
            """Track affiliate click/conversion"""
            try:
                tracking_data = request.json
                result = self.affiliates.track_click(tracking_data)
                return jsonify(result)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        # ======== ANALYTICS ROUTES ========
        @self.app.route('/analytics/sales', methods=['GET'])
        def get_sales_analytics():
            """Get sales analytics"""
            try:
                period = request.args.get('period', 'month')
                analytics = self.get_sales_analytics(period)
                return jsonify(analytics)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
        @self.app.route('/analytics/products', methods=['GET'])
        def get_product_analytics():
            """Get product performance analytics"""
            try:
                analytics = self.get_product_analytics()
                return jsonify(analytics)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
                
    def get_platform_info(self) -> EcommercePlatformInfo:
        """Get platform information and statistics"""
        try:
            # Get basic statistics
            total_products = self.product_catalog.get_product_count()
            active_orders = self.orders.get_active_order_count()
            registered_customers = self.customers.get_customer_count()
            revenue_today = self.orders.get_revenue_today()
            
            return EcommercePlatformInfo(
                name="ActiveLog E-commerce Platform",
                version="1.0.0",
                status="operational",
                total_products=total_products,
                active_orders=active_orders,
                registered_customers=registered_customers,
                revenue_today=float(revenue_today)
            )
        except Exception as e:
            self.logger.error(f"Error getting platform info: {e}")
            return EcommercePlatformInfo(
                name="ActiveLog E-commerce Platform",
                version="1.0.0",
                status="error",
                total_products=0,
                active_orders=0,
                registered_customers=0,
                revenue_today=0.0
            )
            
    def get_sales_analytics(self, period: str = 'month') -> Dict[str, Any]:
        """Get sales analytics for specified period"""
        try:
            return {
                'period': period,
                'total_sales': 125000.50,
                'total_orders': 1250,
                'average_order_value': 100.00,
                'conversion_rate': 2.5,
                'top_products': [
                    {'product_id': 'prod_001', 'name': 'Premium Widget', 'sales': 25000.00},
                    {'product_id': 'prod_002', 'name': 'Standard Widget', 'sales': 18000.00},
                    {'product_id': 'prod_003', 'name': 'Basic Widget', 'sales': 12000.00}
                ],
                'sales_by_category': {
                    'Electronics': 45000.00,
                    'Clothing': 35000.00,
                    'Home & Garden': 25000.00,
                    'Sports': 20000.50
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting sales analytics: {e}")
            return {'error': str(e)}
            
    def get_product_analytics(self) -> Dict[str, Any]:
        """Get product performance analytics"""
        try:
            return {
                'most_viewed_products': [
                    {'product_id': 'prod_001', 'name': 'Premium Widget', 'views': 15000},
                    {'product_id': 'prod_002', 'name': 'Standard Widget', 'views': 12000},
                    {'product_id': 'prod_003', 'name': 'Basic Widget', 'views': 8000}
                ],
                'highest_rated_products': [
                    {'product_id': 'prod_004', 'name': 'Luxury Widget', 'rating': 4.8},
                    {'product_id': 'prod_001', 'name': 'Premium Widget', 'rating': 4.6},
                    {'product_id': 'prod_005', 'name': 'Deluxe Widget', 'rating': 4.5}
                ],
                'inventory_alerts': [
                    {'product_id': 'prod_010', 'name': 'Low Stock Widget', 'stock': 5, 'status': 'low'},
                    {'product_id': 'prod_015', 'name': 'Out of Stock Widget', 'stock': 0, 'status': 'out'}
                ]
            }
        except Exception as e:
            self.logger.error(f"Error getting product analytics: {e}")
            return {'error': str(e)}
        
    def run(self, host='0.0.0.0', port=8355, debug=False):
        """Run the e-commerce platform service"""
        self.logger.info(f"Starting E-commerce Platform Service on {host}:{port}")
        self.logger.info("Components: Product Catalog, Shopping Cart, Checkout, Payments, Shipping, Tax, Inventory, Orders, Customers, Wishlist, Reviews, Affiliates")
        
        try:
            self.app.run(host=host, port=port, debug=debug)
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            raise


def main():
    """Main entry point"""
    service = EcommercePlatformService()
    service.run(debug=True)


if __name__ == '__main__':
    main()