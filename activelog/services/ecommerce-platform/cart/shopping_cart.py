"""
Shopping Cart Management
Handles shopping cart operations and session management
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CartItem:
    item_id: str
    product_id: str
    variant_id: Optional[str]
    quantity: int
    price: float
    title: str
    image: Optional[str]
    sku: str
    properties: Dict[str, str]
    added_at: datetime


@dataclass
class ShoppingCart:
    session_id: str
    items: List[CartItem]
    subtotal: float
    total_quantity: int
    currency: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class ShoppingCartManager:
    """Manages shopping cart operations"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.cart_expiry_hours = config.get('cart_expiry_hours', 24)
        self.max_quantity_per_item = config.get('max_quantity_per_item', 99)
        self.cart_cache = {}
        
    def get_cart(self, session_id: str) -> Dict[str, Any]:
        """Get shopping cart for session"""
        try:
            # Check cache first
            if session_id in self.cart_cache:
                cart = self.cart_cache[session_id]
                if cart['expires_at'] > datetime.now():
                    return self.format_cart_response(cart)
                else:
                    # Cart expired, remove from cache
                    del self.cart_cache[session_id]
            
            # Get from database
            cart_data = self.db.get_cart(session_id)
            
            if not cart_data:
                # Create new empty cart
                cart_data = self.create_empty_cart(session_id)
            else:
                # Check if cart has expired
                expires_at = datetime.fromisoformat(cart_data['expires_at'])
                if expires_at <= datetime.now():
                    # Cart expired, create new empty cart
                    cart_data = self.create_empty_cart(session_id)
                else:
                    # Refresh cart data and extend expiry
                    cart_data = self.refresh_cart_data(cart_data)
            
            # Cache the cart
            self.cart_cache[session_id] = cart_data
            
            return self.format_cart_response(cart_data)
            
        except Exception as e:
            raise Exception(f"Error getting cart: {e}")
            
    def add_item(self, session_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add item to shopping cart"""
        try:
            # Validate item data
            required_fields = ['product_id', 'quantity']
            for field in required_fields:
                if field not in item_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            product_id = item_data['product_id']
            variant_id = item_data.get('variant_id')
            quantity = int(item_data['quantity'])
            properties = item_data.get('properties', {})
            
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0")
            if quantity > self.max_quantity_per_item:
                raise ValueError(f"Quantity cannot exceed {self.max_quantity_per_item}")
            
            # Get product information
            product_info = self.get_product_info(product_id, variant_id)
            if not product_info:
                raise ValueError("Product not found or not available")
                
            # Check inventory availability
            if not self.check_inventory_availability(product_id, variant_id, quantity):
                raise ValueError("Insufficient inventory")
                
            # Get current cart
            cart = self.get_cart_data(session_id)
            
            # Check if item already exists in cart
            existing_item = self.find_existing_item(cart['items'], product_id, variant_id, properties)
            
            if existing_item:
                # Update quantity of existing item
                new_quantity = existing_item['quantity'] + quantity
                if new_quantity > self.max_quantity_per_item:
                    raise ValueError(f"Total quantity would exceed {self.max_quantity_per_item}")
                    
                # Check inventory for new total quantity
                if not self.check_inventory_availability(product_id, variant_id, new_quantity):
                    raise ValueError("Insufficient inventory for total quantity")
                    
                existing_item['quantity'] = new_quantity
                existing_item['updated_at'] = datetime.now().isoformat()
                
                result_message = f"Updated quantity to {new_quantity}"
                
            else:
                # Add new item to cart
                item_id = f"item_{datetime.now().timestamp()}"
                
                new_item = {
                    'item_id': item_id,
                    'product_id': product_id,
                    'variant_id': variant_id,
                    'quantity': quantity,
                    'price': product_info['price'],
                    'title': product_info['title'],
                    'image': product_info.get('image'),
                    'sku': product_info.get('sku', ''),
                    'properties': properties,
                    'added_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                cart['items'].append(new_item)
                result_message = f"Added {quantity} item(s) to cart"
            
            # Recalculate cart totals
            cart = self.calculate_cart_totals(cart)
            cart['updated_at'] = datetime.now().isoformat()
            cart['expires_at'] = (datetime.now() + timedelta(hours=self.cart_expiry_hours)).isoformat()
            
            # Save cart
            self.save_cart(cart)
            
            return {
                'status': 'success',
                'message': result_message,
                'cart': self.format_cart_response(cart),
                'item_added': {
                    'product_id': product_id,
                    'variant_id': variant_id,
                    'quantity': quantity,
                    'title': product_info['title']
                }
            }
            
        except Exception as e:
            raise Exception(f"Error adding item to cart: {e}")
            
    def update_item(self, session_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update cart item quantity"""
        try:
            item_id = update_data.get('item_id')
            new_quantity = int(update_data.get('quantity', 0))
            
            if not item_id:
                raise ValueError("Item ID is required")
            if new_quantity < 0:
                raise ValueError("Quantity cannot be negative")
            if new_quantity > self.max_quantity_per_item:
                raise ValueError(f"Quantity cannot exceed {self.max_quantity_per_item}")
                
            # Get current cart
            cart = self.get_cart_data(session_id)
            
            # Find item to update
            item_to_update = None
            for item in cart['items']:
                if item['item_id'] == item_id:
                    item_to_update = item
                    break
                    
            if not item_to_update:
                raise ValueError("Item not found in cart")
                
            if new_quantity == 0:
                # Remove item from cart
                cart['items'] = [item for item in cart['items'] if item['item_id'] != item_id]
                result_message = f"Removed {item_to_update['title']} from cart"
            else:
                # Check inventory availability
                if not self.check_inventory_availability(
                    item_to_update['product_id'], 
                    item_to_update.get('variant_id'), 
                    new_quantity
                ):
                    raise ValueError("Insufficient inventory")
                    
                # Update quantity
                old_quantity = item_to_update['quantity']
                item_to_update['quantity'] = new_quantity
                item_to_update['updated_at'] = datetime.now().isoformat()
                
                result_message = f"Updated quantity from {old_quantity} to {new_quantity}"
            
            # Recalculate cart totals
            cart = self.calculate_cart_totals(cart)
            cart['updated_at'] = datetime.now().isoformat()
            cart['expires_at'] = (datetime.now() + timedelta(hours=self.cart_expiry_hours)).isoformat()
            
            # Save cart
            self.save_cart(cart)
            
            return {
                'status': 'success',
                'message': result_message,
                'cart': self.format_cart_response(cart)
            }
            
        except Exception as e:
            raise Exception(f"Error updating cart item: {e}")
            
    def remove_item(self, session_id: str, item_id: str) -> Dict[str, Any]:
        """Remove item from cart"""
        try:
            return self.update_item(session_id, {'item_id': item_id, 'quantity': 0})
            
        except Exception as e:
            raise Exception(f"Error removing item from cart: {e}")
            
    def clear_cart(self, session_id: str) -> Dict[str, Any]:
        """Clear entire cart"""
        try:
            # Create new empty cart
            cart = self.create_empty_cart(session_id)
            
            # Save cart
            self.save_cart(cart)
            
            # Remove from cache
            if session_id in self.cart_cache:
                del self.cart_cache[session_id]
                
            return {
                'status': 'success',
                'message': 'Cart cleared successfully',
                'cart': self.format_cart_response(cart)
            }
            
        except Exception as e:
            raise Exception(f"Error clearing cart: {e}")
            
    def apply_discount_code(self, session_id: str, discount_code: str) -> Dict[str, Any]:
        """Apply discount code to cart"""
        try:
            # Get current cart
            cart = self.get_cart_data(session_id)
            
            # Validate discount code
            discount = self.validate_discount_code(discount_code, cart)
            if not discount:
                raise ValueError("Invalid or expired discount code")
                
            # Apply discount
            cart['discount'] = discount
            cart = self.calculate_cart_totals(cart)
            cart['updated_at'] = datetime.now().isoformat()
            
            # Save cart
            self.save_cart(cart)
            
            return {
                'status': 'success',
                'message': f'Discount code "{discount_code}" applied',
                'discount': discount,
                'cart': self.format_cart_response(cart)
            }
            
        except Exception as e:
            raise Exception(f"Error applying discount code: {e}")
            
    def remove_discount_code(self, session_id: str) -> Dict[str, Any]:
        """Remove discount code from cart"""
        try:
            # Get current cart
            cart = self.get_cart_data(session_id)
            
            if 'discount' in cart:
                del cart['discount']
                cart = self.calculate_cart_totals(cart)
                cart['updated_at'] = datetime.now().isoformat()
                
                # Save cart
                self.save_cart(cart)
                
                return {
                    'status': 'success',
                    'message': 'Discount code removed',
                    'cart': self.format_cart_response(cart)
                }
            else:
                return {
                    'status': 'info',
                    'message': 'No discount code to remove',
                    'cart': self.format_cart_response(cart)
                }
                
        except Exception as e:
            raise Exception(f"Error removing discount code: {e}")
            
    def get_cart_data(self, session_id: str) -> Dict[str, Any]:
        """Get raw cart data (internal use)"""
        if session_id in self.cart_cache:
            return self.cart_cache[session_id]
        
        cart_data = self.db.get_cart(session_id)
        if not cart_data:
            cart_data = self.create_empty_cart(session_id)
            
        return cart_data
        
    def create_empty_cart(self, session_id: str) -> Dict[str, Any]:
        """Create empty cart"""
        now = datetime.now()
        expires_at = now + timedelta(hours=self.cart_expiry_hours)
        
        return {
            'session_id': session_id,
            'items': [],
            'subtotal': 0.0,
            'total_quantity': 0,
            'currency': self.config.get('default_currency', 'USD'),
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
    def calculate_cart_totals(self, cart: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate cart totals"""
        subtotal = 0.0
        total_quantity = 0
        
        for item in cart['items']:
            item_total = item['price'] * item['quantity']
            subtotal += item_total
            total_quantity += item['quantity']
            
        cart['subtotal'] = subtotal
        cart['total_quantity'] = total_quantity
        
        # Apply discount if present
        if 'discount' in cart:
            discount = cart['discount']
            if discount['type'] == 'percentage':
                discount_amount = (subtotal * discount['value']) / 100
            else:  # fixed amount
                discount_amount = min(discount['value'], subtotal)
                
            cart['discount_amount'] = discount_amount
            cart['total'] = max(0, subtotal - discount_amount)
        else:
            cart['discount_amount'] = 0.0
            cart['total'] = subtotal
            
        return cart
        
    def refresh_cart_data(self, cart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refresh cart data with latest product info and prices"""
        try:
            updated_items = []
            items_updated = False
            
            for item in cart_data['items']:
                # Get latest product info
                product_info = self.get_product_info(item['product_id'], item.get('variant_id'))
                
                if product_info:
                    # Update price if changed
                    if item['price'] != product_info['price']:
                        item['price'] = product_info['price']
                        items_updated = True
                        
                    # Update title if changed
                    if item['title'] != product_info['title']:
                        item['title'] = product_info['title']
                        items_updated = True
                        
                    # Check if still in stock
                    if self.check_inventory_availability(item['product_id'], item.get('variant_id'), item['quantity']):
                        updated_items.append(item)
                    else:
                        # Item out of stock, mark for user notification
                        item['out_of_stock'] = True
                        updated_items.append(item)
                        items_updated = True
                else:
                    # Product no longer available, don't include in cart
                    items_updated = True
                    
            if items_updated:
                cart_data['items'] = updated_items
                cart_data = self.calculate_cart_totals(cart_data)
                cart_data['updated_at'] = datetime.now().isoformat()
                
            # Extend expiry time
            cart_data['expires_at'] = (datetime.now() + timedelta(hours=self.cart_expiry_hours)).isoformat()
            
            return cart_data
            
        except Exception as e:
            # Return cart as-is if refresh fails
            return cart_data
            
    def find_existing_item(self, items: List[Dict], product_id: str, variant_id: Optional[str], properties: Dict) -> Optional[Dict]:
        """Find existing item in cart with same product, variant, and properties"""
        for item in items:
            if (item['product_id'] == product_id and 
                item.get('variant_id') == variant_id and
                item.get('properties', {}) == properties):
                return item
        return None
        
    def get_product_info(self, product_id: str, variant_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get product information for cart operations"""
        try:
            # This would typically fetch from product catalog
            # Simulating product data for now
            return {
                'product_id': product_id,
                'variant_id': variant_id,
                'title': f'Product {product_id}',
                'price': 29.99,
                'image': f'/images/{product_id}.jpg',
                'sku': f'SKU-{product_id}',
                'available': True
            }
        except Exception:
            return None
            
    def check_inventory_availability(self, product_id: str, variant_id: Optional[str], quantity: int) -> bool:
        """Check if product/variant has sufficient inventory"""
        try:
            # This would typically check actual inventory
            # Simulating inventory check for now
            return quantity <= 100  # Assume max 100 available
        except Exception:
            return False
            
    def validate_discount_code(self, discount_code: str, cart: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate discount code"""
        try:
            # This would typically validate against discount database
            # Simulating discount validation for now
            valid_codes = {
                'SAVE10': {'type': 'percentage', 'value': 10, 'min_amount': 50},
                'WELCOME': {'type': 'fixed', 'value': 5, 'min_amount': 25}
            }
            
            if discount_code in valid_codes:
                discount = valid_codes[discount_code]
                if cart['subtotal'] >= discount['min_amount']:
                    return {
                        'code': discount_code,
                        'type': discount['type'],
                        'value': discount['value'],
                        'min_amount': discount['min_amount']
                    }
            return None
        except Exception:
            return None
            
    def save_cart(self, cart: Dict[str, Any]):
        """Save cart to database and cache"""
        try:
            self.db.save_cart(cart)
            self.cart_cache[cart['session_id']] = cart
        except Exception as e:
            raise Exception(f"Error saving cart: {e}")
            
    def format_cart_response(self, cart: Dict[str, Any]) -> Dict[str, Any]:
        """Format cart data for API response"""
        try:
            formatted_cart = cart.copy()
            
            # Add cart summary
            formatted_cart['summary'] = {
                'item_count': len(cart['items']),
                'total_quantity': cart['total_quantity'],
                'subtotal': cart['subtotal'],
                'discount_amount': cart.get('discount_amount', 0),
                'total': cart.get('total', cart['subtotal']),
                'currency': cart['currency']
            }
            
            # Add cart warnings/notices
            warnings = []
            for item in cart['items']:
                if item.get('out_of_stock'):
                    warnings.append(f"{item['title']} is currently out of stock")
                    
            if warnings:
                formatted_cart['warnings'] = warnings
                
            # Add estimated shipping (would be calculated based on location)
            formatted_cart['estimated_shipping'] = {
                'available': True,
                'rates': [
                    {'name': 'Standard Shipping', 'price': 5.99, 'delivery_days': '3-5'},
                    {'name': 'Express Shipping', 'price': 12.99, 'delivery_days': '1-2'}
                ]
            }
            
            return formatted_cart
            
        except Exception as e:
            return cart