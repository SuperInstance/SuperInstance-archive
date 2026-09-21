"""
Payment Processing
Handles payment processing, authorization, capture, and refunds
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import hashlib
import secrets


class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    STRIPE = "stripe"
    SQUARE = "square"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"


class PaymentStatus(Enum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"


@dataclass
class PaymentTransaction:
    transaction_id: str
    order_id: str
    payment_method: PaymentMethod
    amount: float
    currency: str
    status: PaymentStatus
    gateway: str
    gateway_transaction_id: Optional[str]
    created_at: datetime
    processed_at: Optional[datetime]


class PaymentProcessor:
    """Manages payment processing operations"""
    
    def __init__(self, config, db):
        self.config = config
        self.db = db
        self.enabled_gateways = self.initialize_payment_gateways()
        
    def initialize_payment_gateways(self) -> Dict[str, Any]:
        """Initialize available payment gateways"""
        return {
            'stripe': {
                'name': 'Stripe',
                'enabled': self.config.get('stripe_enabled', True),
                'public_key': self.config.get('stripe_public_key'),
                'secret_key': self.config.get('stripe_secret_key'),
                'supported_methods': ['credit_card', 'debit_card', 'apple_pay', 'google_pay']
            },
            'paypal': {
                'name': 'PayPal',
                'enabled': self.config.get('paypal_enabled', True),
                'client_id': self.config.get('paypal_client_id'),
                'client_secret': self.config.get('paypal_client_secret'),
                'supported_methods': ['paypal']
            },
            'square': {
                'name': 'Square',
                'enabled': self.config.get('square_enabled', False),
                'application_id': self.config.get('square_app_id'),
                'access_token': self.config.get('square_access_token'),
                'supported_methods': ['credit_card', 'debit_card']
            }
        }
        
    def process_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment transaction"""
        try:
            # Validate payment data
            required_fields = ['order_id', 'amount', 'currency', 'payment_method']
            for field in required_fields:
                if field not in payment_data:
                    raise ValueError(f"Missing required field: {field}")
                    
            order_id = payment_data['order_id']
            amount = float(payment_data['amount'])
            currency = payment_data.get('currency', 'USD')
            payment_method = payment_data['payment_method']
            
            # Validate amount
            if amount <= 0:
                raise ValueError("Payment amount must be greater than 0")
                
            # Get order information
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            if order['status'] != 'pending':
                raise ValueError("Order is not in a payable state")
                
            # Validate payment amount matches order total
            if abs(amount - order['totals']['total']) > 0.01:
                raise ValueError("Payment amount does not match order total")
                
            # Create payment transaction
            transaction_id = f"txn_{datetime.now().timestamp()}"
            transaction = {
                'transaction_id': transaction_id,
                'order_id': order_id,
                'customer_id': order.get('customer_id'),
                'payment_method': payment_method['method_type'],
                'amount': amount,
                'currency': currency,
                'status': 'pending',
                'gateway': self.select_payment_gateway(payment_method),
                'gateway_transaction_id': None,
                'payment_details': payment_method,
                'created_at': datetime.now().isoformat(),
                'processed_at': None
            }
            
            # Save transaction
            self.db.save_payment_transaction(transaction)
            
            # Process payment through gateway
            gateway_result = self.process_through_gateway(transaction, payment_method)
            
            # Update transaction with gateway result
            transaction['status'] = gateway_result['status']
            transaction['gateway_transaction_id'] = gateway_result.get('gateway_transaction_id')
            transaction['processed_at'] = datetime.now().isoformat()
            transaction['gateway_response'] = gateway_result.get('response_data')
            
            self.db.update_payment_transaction(transaction_id, transaction)
            
            # Update order status based on payment result
            if gateway_result['status'] == 'captured':
                self.update_order_status(order_id, 'paid')
                result_message = "Payment processed successfully"
            elif gateway_result['status'] == 'authorized':
                self.update_order_status(order_id, 'authorized')
                result_message = "Payment authorized successfully"
            else:
                self.update_order_status(order_id, 'payment_failed')
                result_message = "Payment failed"
                
            return {
                'status': 'success' if gateway_result['status'] in ['captured', 'authorized'] else 'failed',
                'message': result_message,
                'transaction_id': transaction_id,
                'payment_status': gateway_result['status'],
                'amount': amount,
                'currency': currency,
                'gateway': transaction['gateway'],
                'gateway_transaction_id': gateway_result.get('gateway_transaction_id')
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Payment processing failed: {e}",
                'error_code': 'PAYMENT_ERROR'
            }
            
    def process_through_gateway(self, transaction: Dict[str, Any], payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment through selected gateway"""
        gateway = transaction['gateway']
        
        if gateway == 'stripe':
            return self.process_stripe_payment(transaction, payment_method)
        elif gateway == 'paypal':
            return self.process_paypal_payment(transaction, payment_method)
        elif gateway == 'square':
            return self.process_square_payment(transaction, payment_method)
        else:
            return self.process_mock_payment(transaction, payment_method)
            
    def process_stripe_payment(self, transaction: Dict[str, Any], payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment through Stripe"""
        try:
            # Simulate Stripe payment processing
            gateway_transaction_id = f"stripe_txn_{datetime.now().timestamp()}"
            
            # Simulate success/failure based on test card numbers
            card_number = payment_method.get('card_number', '')
            if card_number.endswith('0002'):  # Simulate declined card
                return {
                    'status': 'failed',
                    'gateway_transaction_id': gateway_transaction_id,
                    'response_data': {'error': 'card_declined', 'decline_code': 'generic_decline'},
                    'error_message': 'Your card was declined'
                }
            elif card_number.endswith('0004'):  # Simulate auth-only
                return {
                    'status': 'authorized',
                    'gateway_transaction_id': gateway_transaction_id,
                    'response_data': {'status': 'requires_capture', 'payment_intent_id': gateway_transaction_id}
                }
            else:  # Simulate successful payment
                return {
                    'status': 'captured',
                    'gateway_transaction_id': gateway_transaction_id,
                    'response_data': {'status': 'succeeded', 'payment_intent_id': gateway_transaction_id}
                }
                
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': f"Stripe processing error: {e}",
                'response_data': {'error': str(e)}
            }
            
    def process_paypal_payment(self, transaction: Dict[str, Any], payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment through PayPal"""
        try:
            # Simulate PayPal payment processing
            gateway_transaction_id = f"paypal_txn_{datetime.now().timestamp()}"
            
            return {
                'status': 'captured',
                'gateway_transaction_id': gateway_transaction_id,
                'response_data': {
                    'status': 'COMPLETED',
                    'payer_email': payment_method.get('payer_email', 'test@paypal.com'),
                    'transaction_id': gateway_transaction_id
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': f"PayPal processing error: {e}",
                'response_data': {'error': str(e)}
            }
            
    def process_square_payment(self, transaction: Dict[str, Any], payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment through Square"""
        try:
            # Simulate Square payment processing
            gateway_transaction_id = f"square_txn_{datetime.now().timestamp()}"
            
            return {
                'status': 'captured',
                'gateway_transaction_id': gateway_transaction_id,
                'response_data': {
                    'status': 'COMPLETED',
                    'payment_id': gateway_transaction_id,
                    'receipt_number': f"SQ{gateway_transaction_id[-8:].upper()}"
                }
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error_message': f"Square processing error: {e}",
                'response_data': {'error': str(e)}
            }
            
    def process_mock_payment(self, transaction: Dict[str, Any], payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment through mock gateway (for testing)"""
        gateway_transaction_id = f"mock_txn_{datetime.now().timestamp()}"
        
        return {
            'status': 'captured',
            'gateway_transaction_id': gateway_transaction_id,
            'response_data': {'status': 'success', 'mock': True}
        }
        
    def capture_authorized_payment(self, transaction_id: str, capture_amount: Optional[float] = None) -> Dict[str, Any]:
        """Capture previously authorized payment"""
        try:
            # Get transaction
            transaction = self.db.get_payment_transaction(transaction_id)
            if not transaction:
                raise ValueError("Transaction not found")
                
            if transaction['status'] != 'authorized':
                raise ValueError("Transaction is not in authorized state")
                
            # Determine capture amount
            if capture_amount is None:
                capture_amount = transaction['amount']
            elif capture_amount > transaction['amount']:
                raise ValueError("Capture amount cannot exceed authorized amount")
                
            # Process capture through gateway
            gateway_result = self.capture_through_gateway(transaction, capture_amount)
            
            if gateway_result['status'] == 'captured':
                # Update transaction
                transaction['status'] = 'captured'
                transaction['captured_amount'] = capture_amount
                transaction['captured_at'] = datetime.now().isoformat()
                self.db.update_payment_transaction(transaction_id, transaction)
                
                # Update order status
                self.update_order_status(transaction['order_id'], 'paid')
                
                return {
                    'status': 'success',
                    'message': 'Payment captured successfully',
                    'transaction_id': transaction_id,
                    'captured_amount': capture_amount
                }
            else:
                return {
                    'status': 'failed',
                    'message': 'Payment capture failed',
                    'error': gateway_result.get('error_message')
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error capturing payment: {e}"
            }
            
    def refund_payment(self, payment_id: str, refund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment refund"""
        try:
            # Get original transaction
            transaction = self.db.get_payment_transaction(payment_id)
            if not transaction:
                raise ValueError("Transaction not found")
                
            if transaction['status'] not in ['captured']:
                raise ValueError("Transaction cannot be refunded")
                
            # Determine refund amount
            refund_amount = refund_data.get('amount')
            if refund_amount is None:
                refund_amount = transaction['amount']
            elif refund_amount <= 0 or refund_amount > transaction['amount']:
                raise ValueError("Invalid refund amount")
                
            # Check for existing refunds
            existing_refunds = self.db.get_transaction_refunds(payment_id)
            total_refunded = sum(refund['amount'] for refund in existing_refunds)
            
            if total_refunded + refund_amount > transaction['amount']:
                raise ValueError("Total refund amount would exceed original transaction amount")
                
            # Create refund transaction
            refund_id = f"refund_{datetime.now().timestamp()}"
            refund_transaction = {
                'refund_id': refund_id,
                'original_transaction_id': payment_id,
                'order_id': transaction['order_id'],
                'amount': refund_amount,
                'currency': transaction['currency'],
                'reason': refund_data.get('reason', 'customer_request'),
                'status': 'pending',
                'gateway': transaction['gateway'],
                'created_at': datetime.now().isoformat()
            }
            
            # Process refund through gateway
            gateway_result = self.process_refund_through_gateway(transaction, refund_transaction)
            
            # Update refund transaction
            refund_transaction['status'] = gateway_result['status']
            refund_transaction['gateway_refund_id'] = gateway_result.get('gateway_refund_id')
            refund_transaction['processed_at'] = datetime.now().isoformat()
            
            # Save refund transaction
            self.db.save_refund_transaction(refund_transaction)
            
            # Update original transaction status
            total_refunded_after = total_refunded + refund_amount
            if total_refunded_after >= transaction['amount']:
                new_status = 'refunded'
            else:
                new_status = 'partially_refunded'
                
            transaction['status'] = new_status
            transaction['refunded_amount'] = total_refunded_after
            self.db.update_payment_transaction(payment_id, transaction)
            
            return {
                'status': 'success',
                'message': 'Refund processed successfully',
                'refund_id': refund_id,
                'refund_amount': refund_amount,
                'gateway_refund_id': gateway_result.get('gateway_refund_id')
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error processing refund: {e}"
            }
            
    def process_refund_through_gateway(self, transaction: Dict[str, Any], refund: Dict[str, Any]) -> Dict[str, Any]:
        """Process refund through payment gateway"""
        gateway = transaction['gateway']
        
        # Simulate gateway refund processing
        gateway_refund_id = f"{gateway}_refund_{datetime.now().timestamp()}"
        
        return {
            'status': 'refunded',
            'gateway_refund_id': gateway_refund_id,
            'response_data': {'status': 'succeeded', 'refund_id': gateway_refund_id}
        }
        
    def capture_through_gateway(self, transaction: Dict[str, Any], capture_amount: float) -> Dict[str, Any]:
        """Capture authorized payment through gateway"""
        gateway = transaction['gateway']
        
        # Simulate gateway capture processing
        return {
            'status': 'captured',
            'captured_amount': capture_amount,
            'response_data': {'status': 'captured', 'amount': capture_amount}
        }
        
    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment transaction status"""
        try:
            transaction = self.db.get_payment_transaction(payment_id)
            if not transaction:
                return {
                    'status': 'error',
                    'message': 'Transaction not found'
                }
                
            # Get refund information if applicable
            refunds = self.db.get_transaction_refunds(payment_id)
            total_refunded = sum(refund['amount'] for refund in refunds)
            
            return {
                'status': 'success',
                'transaction_id': payment_id,
                'payment_status': transaction['status'],
                'amount': transaction['amount'],
                'currency': transaction['currency'],
                'payment_method': transaction['payment_method'],
                'gateway': transaction['gateway'],
                'gateway_transaction_id': transaction.get('gateway_transaction_id'),
                'created_at': transaction['created_at'],
                'processed_at': transaction.get('processed_at'),
                'refunds': {
                    'total_refunded': total_refunded,
                    'refund_count': len(refunds),
                    'refunds': refunds
                }
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error getting payment status: {e}"
            }
            
    def select_payment_gateway(self, payment_method: Dict[str, Any]) -> str:
        """Select appropriate payment gateway based on payment method"""
        method_type = payment_method.get('method_type', 'credit_card')
        
        # Priority order for gateway selection
        for gateway, config in self.enabled_gateways.items():
            if config['enabled'] and method_type in config['supported_methods']:
                return gateway
                
        # Default fallback
        return 'stripe'
        
    def get_available_payment_methods(self, order_id: str) -> Dict[str, Any]:
        """Get available payment methods for order"""
        try:
            order = self.db.get_order(order_id)
            if not order:
                raise ValueError("Order not found")
                
            available_methods = []
            
            # Credit/Debit Cards
            if self.is_gateway_available('stripe') or self.is_gateway_available('square'):
                available_methods.append({
                    'method_type': 'credit_card',
                    'name': 'Credit/Debit Card',
                    'description': 'Pay with Visa, MasterCard, American Express',
                    'icon': 'credit-card',
                    'fees': self.get_payment_method_fees('credit_card', order['totals']['total'])
                })
                
            # PayPal
            if self.is_gateway_available('paypal'):
                available_methods.append({
                    'method_type': 'paypal',
                    'name': 'PayPal',
                    'description': 'Pay with your PayPal account',
                    'icon': 'paypal',
                    'fees': self.get_payment_method_fees('paypal', order['totals']['total'])
                })
                
            # Apple Pay (if supported)
            if self.is_mobile_device_payment_supported():
                available_methods.append({
                    'method_type': 'apple_pay',
                    'name': 'Apple Pay',
                    'description': 'Pay with Touch ID or Face ID',
                    'icon': 'apple-pay',
                    'fees': self.get_payment_method_fees('apple_pay', order['totals']['total'])
                })
                
            # Google Pay (if supported)
            if self.is_mobile_device_payment_supported():
                available_methods.append({
                    'method_type': 'google_pay',
                    'name': 'Google Pay',
                    'description': 'Pay with your Google account',
                    'icon': 'google-pay',
                    'fees': self.get_payment_method_fees('google_pay', order['totals']['total'])
                })
                
            return {
                'status': 'success',
                'available_methods': available_methods,
                'recommended_method': available_methods[0] if available_methods else None
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f"Error getting payment methods: {e}"
            }
            
    def is_gateway_available(self, gateway: str) -> bool:
        """Check if payment gateway is available and configured"""
        gateway_config = self.enabled_gateways.get(gateway, {})
        return gateway_config.get('enabled', False)
        
    def is_mobile_device_payment_supported(self) -> bool:
        """Check if mobile device payments are supported"""
        return True  # Would check user agent and gateway support
        
    def get_payment_method_fees(self, method_type: str, amount: float) -> Dict[str, Any]:
        """Get payment method processing fees"""
        fee_structures = {
            'credit_card': {'percentage': 2.9, 'fixed': 0.30},
            'paypal': {'percentage': 3.49, 'fixed': 0.00},
            'apple_pay': {'percentage': 2.9, 'fixed': 0.30},
            'google_pay': {'percentage': 2.9, 'fixed': 0.30}
        }
        
        fee_structure = fee_structures.get(method_type, {'percentage': 0, 'fixed': 0})
        fee_amount = (amount * fee_structure['percentage'] / 100) + fee_structure['fixed']
        
        return {
            'fee_amount': round(fee_amount, 2),
            'fee_percentage': fee_structure['percentage'],
            'fixed_fee': fee_structure['fixed'],
            'description': f"{fee_structure['percentage']}% + ${fee_structure['fixed']}"
        }
        
    def update_order_status(self, order_id: str, status: str):
        """Update order status after payment processing"""
        try:
            order_update = {
                'status': status,
                'updated_at': datetime.now().isoformat()
            }
            
            if status == 'paid':
                order_update['paid_at'] = datetime.now().isoformat()
                
            self.db.update_order_status(order_id, order_update)
        except Exception as e:
            print(f"Warning: Could not update order status: {e}")