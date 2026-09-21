"""
Order Management System
Handles order processing, fulfillment, tracking, and lifecycle management
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    RETURNED = "returned"


class FulfillmentStatus(Enum):
    UNFULFILLED = "unfulfilled"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class PaymentStatus(Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    VOIDED = "voided"


@dataclass
class OrderItem:
    product_id: str
    variant_id: Optional[str]
    sku: str
    title: str
    quantity: int
    price: float
    total: float
    tax_amount: float
    discount_amount: float


@dataclass
class ShippingAddress:
    first_name: str
    last_name: str
    company: Optional[str]
    address1: str
    address2: Optional[str]
    city: str
    state: str
    zip: str
    country: str
    phone: Optional[str]


class OrderManager:
    """Manages order lifecycle and fulfillment"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        
        # Order processing settings
        self.auto_confirm_orders = config.get('auto_confirm_orders', True)
        self.auto_capture_payment = config.get('auto_capture_payment', True)
        self.send_order_emails = config.get('send_order_emails', True)
        
        # Fulfillment settings
        self.auto_fulfill_digital = config.get('auto_fulfill_digital', True)
        self.require_signature = config.get('require_signature', False)
        
        # Integration settings
        self.shipstation_config = config.get('shipstation', {})
        self.fulfillment_services = config.get('fulfillment_services', {})
        
    def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new order from checkout"""
        try:
            # Generate order ID and number
            order_id = f"order_{datetime.now().timestamp()}"
            order_number = self.generate_order_number()
            
            # Extract order details
            customer_id = order_data.get('customer_id')
            checkout_session_id = order_data.get('checkout_session_id')
            
            # Create order record
            order = {
                'order_id': order_id,
                'order_number': order_number,
                'customer_id': customer_id,
                'checkout_session_id': checkout_session_id,
                'status': OrderStatus.PENDING.value,
                'payment_status': PaymentStatus.PENDING.value,
                'fulfillment_status': FulfillmentStatus.UNFULFILLED.value,
                'currency': order_data.get('currency', 'USD'),
                'subtotal': order_data['totals']['subtotal'],
                'tax_total': order_data['totals']['tax'],
                'shipping_total': order_data['totals']['shipping'],
                'discount_total': order_data['totals'].get('discount', 0),
                'total': order_data['totals']['total'],
                'items': order_data['items'],
                'shipping_address': order_data['shipping_address'],
                'billing_address': order_data['billing_address'],
                'shipping_method': order_data['shipping_method'],
                'payment_method': order_data['payment_method'],
                'notes': order_data.get('notes', ''),
                'source': order_data.get('source', 'web'),
                'tags': order_data.get('tags', []),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Save order
            success = self.db.save_order(order)
            if not success:
                raise Exception("Failed to save order")
                
            # Auto-confirm if enabled
            if self.auto_confirm_orders:
                self.confirm_order(order_id)
                
            # Send order confirmation email
            if self.send_order_emails:
                self.send_order_confirmation_email(order_id)
                
            return {
                'success': True,
                'order_id': order_id,
                'order_number': order_number,
                'status': OrderStatus.PENDING.value,
                'total': order['total'],
                'message': 'Order created successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error creating order: {e}")
            
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID"""
        try:
            order = self.db.get_order(order_id)
            if not order:
                return None
                
            # Enrich order data
            order = self.enrich_order_data(order)
            return order
            
        except Exception as e:
            raise Exception(f"Error getting order: {e}")
            
    def update_order_status(self, order_id: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update order status"""
        try:
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            new_status = OrderStatus(status_data['status'])
            current_status = OrderStatus(order['status'])
            
            # Validate status transition
            if not self.is_valid_status_transition(current_status, new_status):
                raise ValueError(f"Invalid status transition from {current_status.value} to {new_status.value}")
                
            # Update order
            updates = {
                'status': new_status.value,
                'updated_at': datetime.now().isoformat()
            }
            
            # Handle specific status changes
            if new_status == OrderStatus.CANCELLED:
                updates['cancelled_at'] = datetime.now().isoformat()
                updates['cancellation_reason'] = status_data.get('reason', 'Customer request')
                # Release inventory
                self.release_order_inventory(order_id)
                
            elif new_status == OrderStatus.CONFIRMED:
                updates['confirmed_at'] = datetime.now().isoformat()
                # Reserve inventory
                self.reserve_order_inventory(order_id)
                
            elif new_status == OrderStatus.SHIPPED:
                updates['shipped_at'] = datetime.now().isoformat()
                updates['tracking_number'] = status_data.get('tracking_number')
                updates['carrier'] = status_data.get('carrier')
                
            elif new_status == OrderStatus.DELIVERED:
                updates['delivered_at'] = datetime.now().isoformat()
                
            # Save updates
            success = self.db.update_order(order_id, updates)
            if not success:
                raise Exception("Failed to update order status")
                
            # Send status update email
            if self.send_order_emails:
                self.send_status_update_email(order_id, new_status)
                
            # Create order event
            self.create_order_event(order_id, 'status_change', {
                'from_status': current_status.value,
                'to_status': new_status.value,
                'reason': status_data.get('reason'),
                'notes': status_data.get('notes')
            })
            
            return {
                'success': True,
                'order_id': order_id,
                'old_status': current_status.value,
                'new_status': new_status.value,
                'message': f'Order status updated to {new_status.value}'
            }
            
        except Exception as e:
            raise Exception(f"Error updating order status: {e}")
            
    def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for order"""
        try:
            order_id = payment_data['order_id']
            payment_method = payment_data['payment_method']
            amount = payment_data.get('amount')
            
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            # Process payment (integration with payment processor)
            payment_result = self.process_order_payment(order, payment_method, amount)
            
            if payment_result['success']:
                # Update order payment status
                payment_status = PaymentStatus.PAID if payment_result['captured'] else PaymentStatus.AUTHORIZED
                
                updates = {
                    'payment_status': payment_status.value,
                    'payment_gateway_id': payment_result['transaction_id'],
                    'paid_at': datetime.now().isoformat() if payment_result['captured'] else None,
                    'updated_at': datetime.now().isoformat()
                }
                
                self.db.update_order(order_id, updates)
                
                # Create payment record
                payment_record = {
                    'payment_id': payment_result['transaction_id'],
                    'order_id': order_id,
                    'amount': payment_result['amount'],
                    'currency': order['currency'],
                    'payment_method': payment_method['method_type'],
                    'status': payment_status.value,
                    'gateway': payment_result['gateway'],
                    'gateway_transaction_id': payment_result['gateway_transaction_id'],
                    'created_at': datetime.now().isoformat()
                }
                
                self.db.save_payment(payment_record)
                
                # Auto-capture if enabled and not already captured
                if self.auto_capture_payment and not payment_result['captured']:
                    self.capture_payment(order_id, payment_result['amount'])
                    
                return {
                    'success': True,
                    'order_id': order_id,
                    'payment_id': payment_result['transaction_id'],
                    'amount': payment_result['amount'],
                    'status': payment_status.value,
                    'message': 'Payment processed successfully'
                }
            else:
                raise Exception(f"Payment processing failed: {payment_result.get('error', 'Unknown error')}")
                
        except Exception as e:
            raise Exception(f"Error processing payment: {e}")
            
    def capture_payment(self, order_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
        """Capture authorized payment"""
        try:
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            if order['payment_status'] != PaymentStatus.AUTHORIZED.value:
                raise ValueError("Order payment is not authorized")
                
            # Capture payment
            capture_amount = amount or order['total']
            
            # This would integrate with payment processor
            capture_result = {
                'success': True,
                'amount': capture_amount,
                'transaction_id': f"capture_{datetime.now().timestamp()}"
            }
            
            if capture_result['success']:
                # Update order
                updates = {
                    'payment_status': PaymentStatus.PAID.value,
                    'paid_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                self.db.update_order(order_id, updates)
                
                return {
                    'success': True,
                    'order_id': order_id,
                    'captured_amount': capture_amount,
                    'message': 'Payment captured successfully'
                }
            else:
                raise Exception("Payment capture failed")
                
        except Exception as e:
            raise Exception(f"Error capturing payment: {e}")
            
    def fulfill_order(self, fulfillment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fulfill order (create shipment)"""
        try:
            order_id = fulfillment_data['order_id']
            items_to_fulfill = fulfillment_data.get('items', [])  # If partial fulfillment
            shipping_carrier = fulfillment_data.get('carrier', 'manual')
            tracking_number = fulfillment_data.get('tracking_number')
            notify_customer = fulfillment_data.get('notify_customer', True)
            
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            # Create fulfillment record
            fulfillment_id = f"fulfill_{datetime.now().timestamp()}"
            
            # Determine items to fulfill
            if not items_to_fulfill:
                # Fulfill all items
                items_to_fulfill = order['items']
                
            fulfillment = {
                'fulfillment_id': fulfillment_id,
                'order_id': order_id,
                'status': 'fulfilled',
                'tracking_number': tracking_number,
                'tracking_company': shipping_carrier,
                'tracking_url': self.generate_tracking_url(shipping_carrier, tracking_number),
                'items': items_to_fulfill,
                'shipped_at': datetime.now().isoformat(),
                'notify_customer': notify_customer,
                'created_at': datetime.now().isoformat()
            }
            
            # Save fulfillment
            self.db.save_fulfillment(fulfillment)
            
            # Update order fulfillment status
            fulfillment_status = self.calculate_order_fulfillment_status(order_id)
            
            updates = {
                'fulfillment_status': fulfillment_status.value,
                'updated_at': datetime.now().isoformat()
            }
            
            # If fully fulfilled, update status to shipped
            if fulfillment_status == FulfillmentStatus.FULFILLED:
                updates['status'] = OrderStatus.SHIPPED.value
                updates['shipped_at'] = datetime.now().isoformat()
                
            self.db.update_order(order_id, updates)
            
            # Reduce inventory
            self.reduce_fulfilled_inventory(items_to_fulfill)
            
            # Send shipping notification
            if notify_customer and self.send_order_emails:
                self.send_shipping_notification(order_id, fulfillment_id)
                
            # Create order event
            self.create_order_event(order_id, 'order_fulfilled', {
                'fulfillment_id': fulfillment_id,
                'tracking_number': tracking_number,
                'carrier': shipping_carrier,
                'items_count': len(items_to_fulfill)
            })
            
            return {
                'success': True,
                'fulfillment_id': fulfillment_id,
                'order_id': order_id,
                'tracking_number': tracking_number,
                'fulfillment_status': fulfillment_status.value,
                'message': 'Order fulfilled successfully'
            }
            
        except Exception as e:
            raise Exception(f"Error fulfilling order: {e}")
            
    def refund_order(self, refund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process order refund"""
        try:
            order_id = refund_data['order_id']
            refund_amount = refund_data.get('amount')
            reason = refund_data.get('reason', 'Customer request')
            restock_items = refund_data.get('restock_items', True)
            
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            if order['payment_status'] not in [PaymentStatus.PAID.value, PaymentStatus.PARTIALLY_REFUNDED.value]:
                raise ValueError("Order cannot be refunded")
                
            # Calculate refund amount
            if not refund_amount:
                refund_amount = order['total']
                
            # Process refund with payment gateway
            refund_result = self.process_refund_payment(order, refund_amount)
            
            if refund_result['success']:
                # Create refund record
                refund_id = f"refund_{datetime.now().timestamp()}"
                refund_record = {
                    'refund_id': refund_id,
                    'order_id': order_id,
                    'amount': refund_amount,
                    'reason': reason,
                    'restock_items': restock_items,
                    'gateway_refund_id': refund_result['refund_id'],
                    'status': 'completed',
                    'created_at': datetime.now().isoformat()
                }
                
                self.db.save_refund(refund_record)
                
                # Update order payment status
                total_refunded = self.calculate_total_refunded(order_id) + refund_amount
                
                if total_refunded >= order['total']:
                    payment_status = PaymentStatus.REFUNDED
                    order_status = OrderStatus.REFUNDED
                else:
                    payment_status = PaymentStatus.PARTIALLY_REFUNDED
                    order_status = OrderStatus(order['status'])  # Keep current status
                    
                updates = {
                    'payment_status': payment_status.value,
                    'status': order_status.value,
                    'refunded_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                self.db.update_order(order_id, updates)
                
                # Restock inventory if requested
                if restock_items:
                    self.restock_order_items(order_id, refund_amount / order['total'])
                    
                # Send refund confirmation
                if self.send_order_emails:
                    self.send_refund_notification(order_id, refund_id)
                    
                return {
                    'success': True,
                    'refund_id': refund_id,
                    'order_id': order_id,
                    'refund_amount': refund_amount,
                    'payment_status': payment_status.value,
                    'message': 'Refund processed successfully'
                }
            else:
                raise Exception(f"Refund processing failed: {refund_result.get('error')}")
                
        except Exception as e:
            raise Exception(f"Error processing refund: {e}")
            
    def list_orders(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 50) -> Dict[str, Any]:
        """List orders with filtering and pagination"""
        try:
            if filters is None:
                filters = {}
                
            orders = self.db.list_orders(filters, page, limit)
            
            # Enrich order data
            enriched_orders = []
            for order in orders:
                enriched_order = self.enrich_order_data(order)
                enriched_orders.append(enriched_order)
                
            # Get total count
            total_count = self.db.get_order_count(filters)
            total_pages = (total_count + limit - 1) // limit
            
            return {
                'orders': enriched_orders,
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
            raise Exception(f"Error listing orders: {e}")
            
    def get_order_analytics(self, analytics_params: Dict[str, Any]) -> Dict[str, Any]:
        """Get order analytics and metrics"""
        try:
            start_date = analytics_params.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
            end_date = analytics_params.get('end_date', datetime.now().strftime('%Y-%m-%d'))
            
            analytics = self.db.get_order_analytics(start_date, end_date)
            
            return {
                'period': {
                    'start_date': start_date,
                    'end_date': end_date
                },
                'total_orders': analytics.get('total_orders', 0),
                'total_revenue': analytics.get('total_revenue', 0),
                'average_order_value': analytics.get('average_order_value', 0),
                'orders_by_status': analytics.get('orders_by_status', {}),
                'top_products': analytics.get('top_products', []),
                'revenue_by_day': analytics.get('revenue_by_day', []),
                'customer_metrics': {
                    'new_customers': analytics.get('new_customers', 0),
                    'returning_customers': analytics.get('returning_customers', 0),
                    'customer_retention_rate': analytics.get('customer_retention_rate', 0)
                }
            }
            
        except Exception as e:
            raise Exception(f"Error getting order analytics: {e}")
            
    def enrich_order_data(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich order data with additional information"""
        try:
            # Add customer information
            if order.get('customer_id'):
                customer = self.db.get_customer(order['customer_id'])
                if customer:
                    order['customer'] = {
                        'id': customer['customer_id'],
                        'email': customer.get('email'),
                        'first_name': customer.get('first_name'),
                        'last_name': customer.get('last_name')
                    }
                    
            # Add fulfillment information
            fulfillments = self.db.get_order_fulfillments(order['order_id'])
            order['fulfillments'] = fulfillments
            
            # Add payment information
            payments = self.db.get_order_payments(order['order_id'])
            order['payments'] = payments
            
            # Add refund information
            refunds = self.db.get_order_refunds(order['order_id'])
            order['refunds'] = refunds
            
            # Calculate derived values
            order['total_paid'] = sum(p['amount'] for p in payments if p['status'] == 'paid')
            order['total_refunded'] = sum(r['amount'] for r in refunds if r['status'] == 'completed')
            order['net_payment'] = order['total_paid'] - order['total_refunded']
            
            return order
            
        except Exception as e:
            return order
            
    def generate_order_number(self) -> str:
        """Generate human-readable order number"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d')
            sequence = self.db.get_next_order_sequence()
            return f"ORD-{timestamp}-{sequence:04d}"
        except Exception:
            return f"ORD-{datetime.now().timestamp()}"
            
    def is_valid_status_transition(self, current: OrderStatus, new: OrderStatus) -> bool:
        """Check if status transition is valid"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED, OrderStatus.RETURNED],
            OrderStatus.DELIVERED: [OrderStatus.RETURNED],
            OrderStatus.CANCELLED: [],
            OrderStatus.REFUNDED: [],
            OrderStatus.RETURNED: [OrderStatus.REFUNDED]
        }
        
        return new in valid_transitions.get(current, [])
        
    def confirm_order(self, order_id: str) -> bool:
        """Confirm order (auto-processing)"""
        try:
            return self.update_order_status(order_id, {'status': 'confirmed'})['success']
        except Exception:
            return False
            
    def reserve_order_inventory(self, order_id: str) -> bool:
        """Reserve inventory for order items"""
        try:
            # This would integrate with inventory system
            return True
        except Exception:
            return False
            
    def release_order_inventory(self, order_id: str) -> bool:
        """Release reserved inventory"""
        try:
            # This would integrate with inventory system
            return True
        except Exception:
            return False
            
    def reduce_fulfilled_inventory(self, items: List[Dict[str, Any]]) -> bool:
        """Reduce inventory for fulfilled items"""
        try:
            # This would integrate with inventory system
            return True
        except Exception:
            return False
            
    def restock_order_items(self, order_id: str, percentage: float = 1.0) -> bool:
        """Restock order items (for refunds)"""
        try:
            # This would integrate with inventory system
            return True
        except Exception:
            return False
            
    def calculate_order_fulfillment_status(self, order_id: str) -> FulfillmentStatus:
        """Calculate order fulfillment status"""
        try:
            fulfillments = self.db.get_order_fulfillments(order_id)
            order = self.db.get_order(order_id)
            
            if not fulfillments:
                return FulfillmentStatus.UNFULFILLED
                
            # Check if all items are fulfilled
            total_ordered = sum(item['quantity'] for item in order['items'])
            total_fulfilled = sum(
                sum(item['quantity'] for item in f['items'])
                for f in fulfillments
            )
            
            if total_fulfilled >= total_ordered:
                return FulfillmentStatus.FULFILLED
            elif total_fulfilled > 0:
                return FulfillmentStatus.PARTIALLY_FULFILLED
            else:
                return FulfillmentStatus.UNFULFILLED
                
        except Exception:
            return FulfillmentStatus.UNFULFILLED
            
    def calculate_total_refunded(self, order_id: str) -> float:
        """Calculate total amount refunded for order"""
        try:
            refunds = self.db.get_order_refunds(order_id)
            return sum(r['amount'] for r in refunds if r['status'] == 'completed')
        except Exception:
            return 0.0
            
    def process_order_payment(self, order: Dict[str, Any], payment_method: Dict[str, Any], amount: Optional[float]) -> Dict[str, Any]:
        """Process payment for order"""
        # This would integrate with payment processor
        return {
            'success': True,
            'transaction_id': f"pay_{datetime.now().timestamp()}",
            'amount': amount or order['total'],
            'captured': True,
            'gateway': 'stripe',
            'gateway_transaction_id': f"ch_{datetime.now().timestamp()}"
        }
        
    def process_refund_payment(self, order: Dict[str, Any], amount: float) -> Dict[str, Any]:
        """Process refund with payment gateway"""
        # This would integrate with payment processor
        return {
            'success': True,
            'refund_id': f"refund_{datetime.now().timestamp()}",
            'amount': amount
        }
        
    def generate_tracking_url(self, carrier: str, tracking_number: str) -> Optional[str]:
        """Generate tracking URL for carrier"""
        try:
            carrier_urls = {
                'ups': f"https://www.ups.com/track?tracknum={tracking_number}",
                'fedex': f"https://www.fedex.com/track/?trackingnumber={tracking_number}",
                'usps': f"https://tools.usps.com/go/TrackConfirmAction?qtc_tLabels1={tracking_number}",
                'dhl': f"https://www.dhl.com/track?tracking-id={tracking_number}"
            }
            
            return carrier_urls.get(carrier.lower())
        except Exception:
            return None
            
    def create_order_event(self, order_id: str, event_type: str, event_data: Dict[str, Any]):
        """Create order event for audit trail"""
        try:
            event = {
                'order_id': order_id,
                'event_type': event_type,
                'event_data': json.dumps(event_data),
                'created_at': datetime.now().isoformat()
            }
            self.db.save_order_event(event)
        except Exception as e:
            print(f"Error creating order event: {e}")
            
    def send_order_confirmation_email(self, order_id: str):
        """Send order confirmation email"""
        # This would integrate with email service
        print(f"Order confirmation email sent for order {order_id}")
        
    def send_status_update_email(self, order_id: str, status: OrderStatus):
        """Send order status update email"""
        # This would integrate with email service
        print(f"Status update email sent for order {order_id}: {status.value}")
        
    def send_shipping_notification(self, order_id: str, fulfillment_id: str):
        """Send shipping notification email"""
        # This would integrate with email service
        print(f"Shipping notification sent for order {order_id}, fulfillment {fulfillment_id}")
        
    def send_refund_notification(self, order_id: str, refund_id: str):
        """Send refund confirmation email"""
        # This would integrate with email service
        print(f"Refund notification sent for order {order_id}, refund {refund_id}")