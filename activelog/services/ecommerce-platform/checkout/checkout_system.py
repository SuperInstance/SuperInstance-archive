"""
Checkout System
Handles checkout process, order creation, and payment flow
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


class CheckoutStep(Enum):
    CART_REVIEW = "cart_review"
    SHIPPING_INFO = "shipping_info"
    BILLING_INFO = "billing_info"
    SHIPPING_METHOD = "shipping_method"
    PAYMENT_METHOD = "payment_method"
    ORDER_REVIEW = "order_review"
    PAYMENT_PROCESSING = "payment_processing"
    ORDER_CONFIRMATION = "order_confirmation"


@dataclass
class CheckoutSession:
    session_id: str
    cart_id: str
    customer_id: Optional[str]
    current_step: CheckoutStep
    shipping_address: Optional[Dict[str, str]]
    billing_address: Optional[Dict[str, str]]
    shipping_method: Optional[Dict[str, Any]]
    payment_method: Optional[Dict[str, Any]]
    order_totals: Dict[str, float]
    created_at: datetime
    expires_at: datetime


class CheckoutSystem:
    """Manages checkout process and order creation"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.checkout_timeout_minutes = config.get('checkout_timeout_minutes', 30)
        
    def initialize_checkout(self, checkout_data: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize checkout process"""
        try:
            session_id = checkout_data.get('session_id')
            cart_id = checkout_data.get('cart_id', session_id)
            customer_id = checkout_data.get('customer_id')
            
            if not session_id:
                raise ValueError("Session ID is required")
                
            # Validate cart exists and has items
            cart = self.db.get_cart(cart_id)
            if not cart or not cart.get('items'):
                raise ValueError("Cart is empty or not found")
                
            # Create checkout session
            checkout_session_id = f"checkout_{datetime.now().timestamp()}"
            checkout_session = {
                'session_id': checkout_session_id,
                'cart_id': cart_id,
                'customer_id': customer_id,
                'current_step': 'cart_review',
                'shipping_address': None,
                'billing_address': None,
                'shipping_method': None,
                'payment_method': None,
                'order_totals': self.calculate_initial_totals(cart),
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=self.checkout_timeout_minutes)).isoformat()
            }
            
            # Save checkout session
            self.db.save_checkout_session(checkout_session)
            
            return {
                'status': 'success',
                'message': 'Checkout initialized',
                'checkout_session_id': checkout_session_id,
                'current_step': 'cart_review',
                'cart': cart,
                'totals': checkout_session['order_totals']
            }
            
        except Exception as e:
            raise Exception(f"Error initializing checkout: {e}")
            
    def update_shipping_address(self, checkout_session_id: str, address_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update shipping address"""
        try:
            # Validate address data
            required_fields = ['first_name', 'last_name', 'address1', 'city', 'state', 'zip', 'country']
            for field in required_fields:
                if field not in address_data or not address_data[field]:
                    raise ValueError(f"Missing required field: {field}")
                    
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Update shipping address
            checkout['shipping_address'] = address_data
            checkout['current_step'] = 'shipping_method'
            checkout['updated_at'] = datetime.now().isoformat()
            
            # Save checkout session
            self.db.update_checkout_session(checkout_session_id, checkout)
            
            return {
                'status': 'success',
                'message': 'Shipping address updated',
                'current_step': 'shipping_method',
                'next_action': 'select_shipping_method'
            }
            
        except Exception as e:
            raise Exception(f"Error updating shipping address: {e}")
            
    def select_shipping_method(self, checkout_session_id: str, shipping_method: Dict[str, Any]) -> Dict[str, Any]:
        """Select shipping method"""
        try:
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Validate shipping method
            if not shipping_method.get('method_id'):
                raise ValueError("Shipping method ID is required")
                
            # Update checkout with shipping method
            checkout['shipping_method'] = shipping_method
            checkout['current_step'] = 'billing_info'
            checkout['updated_at'] = datetime.now().isoformat()
            
            # Recalculate totals with shipping
            checkout['order_totals'] = self.calculate_totals_with_shipping(checkout)
            
            # Save checkout session
            self.db.update_checkout_session(checkout_session_id, checkout)
            
            return {
                'status': 'success',
                'message': 'Shipping method selected',
                'current_step': 'billing_info',
                'totals': checkout['order_totals'],
                'next_action': 'enter_billing_info'
            }
            
        except Exception as e:
            raise Exception(f"Error selecting shipping method: {e}")
            
    def update_billing_address(self, checkout_session_id: str, billing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update billing address"""
        try:
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Handle "same as shipping" option
            if billing_data.get('same_as_shipping') and checkout.get('shipping_address'):
                billing_address = checkout['shipping_address'].copy()
            else:
                # Validate billing address data
                required_fields = ['first_name', 'last_name', 'address1', 'city', 'state', 'zip', 'country']
                for field in required_fields:
                    if field not in billing_data or not billing_data[field]:
                        raise ValueError(f"Missing required field: {field}")
                billing_address = billing_data
                
            # Update billing address
            checkout['billing_address'] = billing_address
            checkout['current_step'] = 'payment_method'
            checkout['updated_at'] = datetime.now().isoformat()
            
            # Recalculate totals with tax
            checkout['order_totals'] = self.calculate_totals_with_tax(checkout)
            
            # Save checkout session
            self.db.update_checkout_session(checkout_session_id, checkout)
            
            return {
                'status': 'success',
                'message': 'Billing address updated',
                'current_step': 'payment_method',
                'totals': checkout['order_totals'],
                'next_action': 'select_payment_method'
            }
            
        except Exception as e:
            raise Exception(f"Error updating billing address: {e}")
            
    def select_payment_method(self, checkout_session_id: str, payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Select payment method"""
        try:
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Validate payment method
            if not payment_method.get('method_type'):
                raise ValueError("Payment method type is required")
                
            # Update checkout with payment method
            checkout['payment_method'] = payment_method
            checkout['current_step'] = 'order_review'
            checkout['updated_at'] = datetime.now().isoformat()
            
            # Save checkout session
            self.db.update_checkout_session(checkout_session_id, checkout)
            
            return {
                'status': 'success',
                'message': 'Payment method selected',
                'current_step': 'order_review',
                'totals': checkout['order_totals'],
                'next_action': 'review_order'
            }
            
        except Exception as e:
            raise Exception(f"Error selecting payment method: {e}")
            
    def calculate_totals(self, calculation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate order totals including tax and shipping"""
        try:
            checkout_session_id = calculation_data.get('checkout_session_id')
            if not checkout_session_id:
                raise ValueError("Checkout session ID is required")
                
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Calculate comprehensive totals
            totals = self.calculate_comprehensive_totals(checkout)
            
            return {
                'status': 'success',
                'totals': totals,
                'breakdown': self.get_totals_breakdown(totals)
            }
            
        except Exception as e:
            raise Exception(f"Error calculating totals: {e}")
            
    def complete_checkout(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete checkout process and create order"""
        try:
            checkout_session_id = order_data.get('checkout_session_id')
            if not checkout_session_id:
                raise ValueError("Checkout session ID is required")
                
            # Get checkout session
            checkout = self.db.get_checkout_session(checkout_session_id)
            if not checkout:
                raise ValueError("Checkout session not found")
                
            # Validate checkout is ready for completion
            if checkout['current_step'] != 'order_review':
                raise ValueError("Checkout is not ready for completion")
                
            if not all([checkout.get('shipping_address'), checkout.get('billing_address'), 
                       checkout.get('shipping_method'), checkout.get('payment_method')]):
                raise ValueError("Missing required checkout information")
                
            # Create order
            order_id = f"order_{datetime.now().timestamp()}"
            order = {
                'order_id': order_id,
                'checkout_session_id': checkout_session_id,
                'customer_id': checkout.get('customer_id'),
                'status': 'pending',
                'items': self.prepare_order_items(checkout),
                'shipping_address': checkout['shipping_address'],
                'billing_address': checkout['billing_address'],
                'shipping_method': checkout['shipping_method'],
                'payment_method': checkout['payment_method'],
                'totals': checkout['order_totals'],
                'notes': order_data.get('notes', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save order
            self.db.save_order(order)
            
            # Update checkout session
            checkout['current_step'] = 'payment_processing'
            checkout['order_id'] = order_id
            checkout['updated_at'] = datetime.now().isoformat()
            self.db.update_checkout_session(checkout_session_id, checkout)
            
            return {
                'status': 'success',
                'message': 'Order created successfully',
                'order_id': order_id,
                'order_number': self.generate_order_number(order_id),
                'total_amount': checkout['order_totals']['total'],
                'payment_required': True,
                'next_step': 'process_payment'
            }
            
        except Exception as e:
            raise Exception(f"Error completing checkout: {e}")
            
    def calculate_initial_totals(self, cart: Dict[str, Any]) -> Dict[str, float]:
        """Calculate initial totals from cart"""
        return {
            'subtotal': cart.get('subtotal', 0),
            'discount': cart.get('discount_amount', 0),
            'shipping': 0,
            'tax': 0,
            'total': cart.get('subtotal', 0) - cart.get('discount_amount', 0)
        }
        
    def calculate_totals_with_shipping(self, checkout: Dict[str, Any]) -> Dict[str, float]:
        """Calculate totals including shipping"""
        totals = checkout['order_totals'].copy()
        
        if checkout.get('shipping_method'):
            shipping_cost = checkout['shipping_method'].get('price', 0)
            totals['shipping'] = shipping_cost
            totals['total'] = totals['subtotal'] - totals['discount'] + shipping_cost
            
        return totals
        
    def calculate_totals_with_tax(self, checkout: Dict[str, Any]) -> Dict[str, float]:
        """Calculate totals including tax"""
        totals = checkout['order_totals'].copy()
        
        if checkout.get('billing_address'):
            # Calculate tax based on billing address
            tax_amount = self.calculate_tax_amount(checkout)
            totals['tax'] = tax_amount
            totals['total'] = totals['subtotal'] - totals['discount'] + totals['shipping'] + tax_amount
            
        return totals
        
    def calculate_comprehensive_totals(self, checkout: Dict[str, Any]) -> Dict[str, float]:
        """Calculate all totals comprehensively"""
        # Get cart data
        cart = self.db.get_cart(checkout['cart_id'])
        
        subtotal = cart.get('subtotal', 0)
        discount = cart.get('discount_amount', 0)
        
        # Calculate shipping
        shipping = 0
        if checkout.get('shipping_method'):
            shipping = checkout['shipping_method'].get('price', 0)
            
        # Calculate tax
        tax = 0
        if checkout.get('billing_address'):
            tax = self.calculate_tax_amount(checkout)
            
        # Calculate handling fees
        handling = self.calculate_handling_fee(subtotal)
        
        total = subtotal - discount + shipping + tax + handling
        
        return {
            'subtotal': round(subtotal, 2),
            'discount': round(discount, 2),
            'shipping': round(shipping, 2),
            'tax': round(tax, 2),
            'handling': round(handling, 2),
            'total': round(total, 2)
        }
        
    def calculate_tax_amount(self, checkout: Dict[str, Any]) -> float:
        """Calculate tax amount based on billing address"""
        try:
            # This would integrate with tax calculation service
            billing_address = checkout.get('billing_address', {})
            state = billing_address.get('state', '')
            
            # Simplified tax calculation
            tax_rates = {
                'CA': 0.0875,  # California
                'NY': 0.08,    # New York
                'TX': 0.0625,  # Texas
                'FL': 0.06     # Florida
            }
            
            tax_rate = tax_rates.get(state, 0)
            taxable_amount = checkout['order_totals']['subtotal'] - checkout['order_totals']['discount']
            
            return taxable_amount * tax_rate
            
        except Exception:
            return 0
            
    def calculate_handling_fee(self, subtotal: float) -> float:
        """Calculate handling fee"""
        # Example: $2 handling fee for orders under $50
        if subtotal < 50:
            return 2.00
        return 0
        
    def prepare_order_items(self, checkout: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare order items from cart"""
        cart = self.db.get_cart(checkout['cart_id'])
        order_items = []
        
        for item in cart.get('items', []):
            order_item = {
                'product_id': item['product_id'],
                'variant_id': item.get('variant_id'),
                'quantity': item['quantity'],
                'price': item['price'],
                'title': item['title'],
                'sku': item.get('sku'),
                'image': item.get('image'),
                'properties': item.get('properties', {}),
                'line_total': item['price'] * item['quantity']
            }
            order_items.append(order_item)
            
        return order_items
        
    def generate_order_number(self, order_id: str) -> str:
        """Generate human-readable order number"""
        timestamp = datetime.now().strftime('%Y%m%d')
        order_suffix = order_id.split('_')[-1][:6]
        return f"AL{timestamp}{order_suffix.upper()}"
        
    def get_totals_breakdown(self, totals: Dict[str, float]) -> List[Dict[str, Any]]:
        """Get detailed totals breakdown for display"""
        breakdown = [
            {'label': 'Subtotal', 'amount': totals['subtotal'], 'type': 'subtotal'},
        ]
        
        if totals['discount'] > 0:
            breakdown.append({'label': 'Discount', 'amount': -totals['discount'], 'type': 'discount'})
            
        if totals['shipping'] > 0:
            breakdown.append({'label': 'Shipping', 'amount': totals['shipping'], 'type': 'shipping'})
            
        if totals.get('handling', 0) > 0:
            breakdown.append({'label': 'Handling', 'amount': totals['handling'], 'type': 'handling'})
            
        if totals['tax'] > 0:
            breakdown.append({'label': 'Tax', 'amount': totals['tax'], 'type': 'tax'})
            
        breakdown.append({'label': 'Total', 'amount': totals['total'], 'type': 'total'})
        
        return breakdown