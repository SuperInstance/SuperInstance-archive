"""
Payment Gateway Integrations for ActiveLedger
Supports PayPal, Google Pay, Venmo, Zelle, and Stripe
"""

import asyncio
import httpx
import json
import base64
from decimal import Decimal
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
import logging
from sqlalchemy.orm import Session

from ...models.database import Transaction, User, TransactionType, TransactionStatus, PaymentMethod
from ...config.settings import settings
from ..credits.cc_system import ComputeCreditSystem

logger = logging.getLogger(__name__)

class PaymentGatewayError(Exception):
    """Base exception for payment gateway errors"""
    pass

class PaymentGateway(ABC):
    """Abstract base class for payment gateways"""
    
    @abstractmethod
    async def create_payment(
        self, 
        amount: Decimal, 
        currency: str, 
        user_id: str, 
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a payment request"""
        pass
    
    @abstractmethod
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture/complete a payment"""
        pass
    
    @abstractmethod
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund a payment"""
        pass
    
    @abstractmethod
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get payment status"""
        pass

class PayPalGateway(PaymentGateway):
    """PayPal payment gateway implementation"""
    
    def __init__(self):
        self.client_id = settings.payments.paypal_client_id
        self.client_secret = settings.payments.paypal_client_secret
        self.environment = settings.payments.paypal_environment
        self.base_url = (
            "https://api.paypal.com" if self.environment == "live" 
            else "https://api.sandbox.paypal.com"
        )
        self.access_token = None
        self.token_expires_at = None
    
    async def _get_access_token(self) -> str:
        """Get PayPal access token"""
        
        if (self.access_token and self.token_expires_at and 
            datetime.utcnow() < self.token_expires_at):
            return self.access_token
        
        auth_string = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Authorization": f"Basic {auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = "grant_type=client_credentials"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code != 200:
                raise PaymentGatewayError(f"PayPal auth failed: {response.text}")
            
            token_data = response.json()
            self.access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
            
            return self.access_token
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create PayPal payment order"""
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "PayPal-Request-Id": f"activelog-{user_id}-{int(datetime.utcnow().timestamp())}"
        }
        
        # Calculate fees
        fee_rate = settings.payments.paypal_fee_rate
        fee_fixed = settings.payments.paypal_fee_fixed
        gross_amount = amount + (amount * fee_rate) + fee_fixed
        
        payment_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "reference_id": f"activelog-{user_id}",
                "description": description,
                "amount": {
                    "currency_code": currency,
                    "value": str(gross_amount.quantize(Decimal("0.01")))
                },
                "custom_id": user_id,
                "invoice_id": f"AL-{user_id}-{int(datetime.utcnow().timestamp())}"
            }],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "payment_method_preference": "IMMEDIATE_PAYMENT_REQUIRED",
                        "brand_name": "ActiveLog",
                        "locale": "en-US",
                        "landing_page": "LOGIN",
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                        "return_url": "https://activelog.com/payment/success",
                        "cancel_url": "https://activelog.com/payment/cancel"
                    }
                }
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                headers=headers,
                json=payment_data,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise PaymentGatewayError(f"PayPal order creation failed: {response.text}")
            
            order_data = response.json()
            
            return {
                "payment_id": order_data["id"],
                "status": order_data["status"],
                "approval_url": next(
                    link["href"] for link in order_data.get("links", [])
                    if link["rel"] == "approve"
                ),
                "gateway": "paypal",
                "gross_amount": gross_amount,
                "fee_amount": gross_amount - amount,
                "net_amount": amount,
                "currency": currency
            }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture PayPal payment"""
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders/{payment_id}/capture",
                headers=headers,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise PaymentGatewayError(f"PayPal capture failed: {response.text}")
            
            capture_data = response.json()
            
            return {
                "payment_id": payment_id,
                "capture_id": capture_data["purchase_units"][0]["payments"]["captures"][0]["id"],
                "status": capture_data["status"],
                "amount": capture_data["purchase_units"][0]["payments"]["captures"][0]["amount"]["value"],
                "currency": capture_data["purchase_units"][0]["payments"]["captures"][0]["amount"]["currency_code"]
            }
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund PayPal payment"""
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        refund_data = {}
        if amount:
            refund_data["amount"] = {
                "value": str(amount.quantize(Decimal("0.01"))),
                "currency_code": "USD"  # Default to USD, should be dynamic
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/payments/captures/{payment_id}/refund",
                headers=headers,
                json=refund_data,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise PaymentGatewayError(f"PayPal refund failed: {response.text}")
            
            return response.json()
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get PayPal payment status"""
        
        token = await self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v2/checkout/orders/{payment_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise PaymentGatewayError(f"PayPal status check failed: {response.text}")
            
            return response.json()

class StripeGateway(PaymentGateway):
    """Stripe payment gateway for credit cards and additional methods"""
    
    def __init__(self):
        self.secret_key = settings.payments.stripe_secret_key
        self.publishable_key = settings.payments.stripe_publishable_key
        self.base_url = "https://api.stripe.com"
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create Stripe PaymentIntent"""
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Calculate fees
        fee_rate = settings.payments.stripe_fee_rate
        fee_fixed = settings.payments.stripe_fee_fixed
        gross_amount = amount + (amount * fee_rate) + fee_fixed
        
        # Convert to cents for Stripe
        amount_cents = int(gross_amount * 100)
        
        data = {
            "amount": amount_cents,
            "currency": currency.lower(),
            "description": description,
            "metadata[user_id]": user_id,
            "metadata[net_amount]": str(amount),
            "automatic_payment_methods[enabled]": "true"
        }
        
        if metadata:
            for key, value in metadata.items():
                data[f"metadata[{key}]"] = str(value)
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/payment_intents",
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise PaymentGatewayError(f"Stripe payment creation failed: {response.text}")
            
            intent_data = response.json()
            
            return {
                "payment_id": intent_data["id"],
                "client_secret": intent_data["client_secret"],
                "status": intent_data["status"],
                "gateway": "stripe",
                "gross_amount": gross_amount,
                "fee_amount": gross_amount - amount,
                "net_amount": amount,
                "currency": currency
            }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture Stripe payment (auto-captured by default)"""
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/payment_intents/{payment_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise PaymentGatewayError(f"Stripe payment check failed: {response.text}")
            
            return response.json()
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund Stripe payment"""
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {"payment_intent": payment_id}
        if amount:
            data["amount"] = int(amount * 100)  # Convert to cents
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/refunds",
                headers=headers,
                data=data,
                timeout=30
            )
            
            if response.status_code not in [200, 201]:
                raise PaymentGatewayError(f"Stripe refund failed: {response.text}")
            
            return response.json()
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get Stripe payment status"""
        
        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/v1/payment_intents/{payment_id}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise PaymentGatewayError(f"Stripe status check failed: {response.text}")
            
            return response.json()

class GooglePayGateway(PaymentGateway):
    """Google Pay integration (via Stripe or PayPal)"""
    
    def __init__(self):
        self.merchant_id = settings.payments.google_pay_merchant_id
        self.gateway_id = settings.payments.google_pay_gateway_id
        # Use Stripe as the underlying processor
        self.stripe_gateway = StripeGateway()
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create Google Pay payment (delegated to Stripe)"""
        
        # Add Google Pay metadata
        google_pay_metadata = {"payment_method": "google_pay"}
        if metadata:
            google_pay_metadata.update(metadata)
        
        result = await self.stripe_gateway.create_payment(
            amount, currency, user_id, description, google_pay_metadata
        )
        
        result["gateway"] = "google_pay"
        return result
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture Google Pay payment"""
        return await self.stripe_gateway.capture_payment(payment_id)
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund Google Pay payment"""
        return await self.stripe_gateway.refund_payment(payment_id, amount)
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get Google Pay payment status"""
        return await self.stripe_gateway.get_payment_status(payment_id)

class VenmoGateway(PaymentGateway):
    """Venmo integration (via PayPal)"""
    
    def __init__(self):
        # Venmo is owned by PayPal and can be processed through PayPal
        self.paypal_gateway = PayPalGateway()
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create Venmo payment (delegated to PayPal)"""
        
        # Add Venmo metadata
        venmo_metadata = {"payment_method": "venmo"}
        if metadata:
            venmo_metadata.update(metadata)
        
        result = await self.paypal_gateway.create_payment(
            amount, currency, user_id, description, venmo_metadata
        )
        
        result["gateway"] = "venmo"
        return result
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture Venmo payment"""
        return await self.paypal_gateway.capture_payment(payment_id)
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund Venmo payment"""
        return await self.paypal_gateway.refund_payment(payment_id, amount)
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get Venmo payment status"""
        return await self.paypal_gateway.get_payment_status(payment_id)

class ZelleGateway(PaymentGateway):
    """Zelle integration (bank-to-bank transfers)"""
    
    def __init__(self):
        # Zelle typically requires bank partnership
        # This is a placeholder implementation
        pass
    
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        user_id: str,
        description: str,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create Zelle payment request"""
        
        # In practice, this would integrate with bank APIs
        # For now, return a mock response
        return {
            "payment_id": f"zelle_{user_id}_{int(datetime.utcnow().timestamp())}",
            "status": "pending_bank_transfer",
            "gateway": "zelle",
            "gross_amount": amount,
            "fee_amount": Decimal("0"),  # Zelle typically has no fees
            "net_amount": amount,
            "currency": currency,
            "instructions": {
                "recipient_email": "payments@activelog.com",
                "recipient_phone": "+1-555-ACTIVELOG",
                "reference": f"AL-{user_id}"
            }
        }
    
    async def capture_payment(self, payment_id: str) -> Dict[str, Any]:
        """Capture Zelle payment (manual verification required)"""
        
        return {
            "payment_id": payment_id,
            "status": "manual_verification_required",
            "message": "Zelle payments require manual bank verification"
        }
    
    async def refund_payment(self, payment_id: str, amount: Optional[Decimal] = None) -> Dict[str, Any]:
        """Refund Zelle payment (manual process)"""
        
        return {
            "payment_id": payment_id,
            "status": "manual_refund_required",
            "message": "Zelle refunds require manual bank transfer"
        }
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Get Zelle payment status"""
        
        return {
            "payment_id": payment_id,
            "status": "pending_verification",
            "message": "Check bank records for confirmation"
        }

class PaymentManager:
    """Central payment management system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.cc_system = ComputeCreditSystem(db)
        
        # Initialize gateways
        self.gateways = {
            PaymentMethod.PAYPAL: PayPalGateway(),
            PaymentMethod.STRIPE: StripeGateway(),
            PaymentMethod.GOOGLE_PAY: GooglePayGateway(),
            PaymentMethod.VENMO: VenmoGateway(),
            PaymentMethod.ZELLE: ZelleGateway()
        }
    
    async def create_cc_purchase(
        self,
        user_id: str,
        amount_usd: Decimal,
        payment_method: PaymentMethod,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Create a CC purchase transaction"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Calculate CC amount
        cc_amount = await self.cc_system.convert_to_cc(amount_usd, "USD", user_id)
        
        # Get appropriate gateway
        gateway = self.gateways.get(payment_method)
        if not gateway:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        
        # Create payment with gateway
        payment_result = await gateway.create_payment(
            amount_usd,
            "USD",
            user_id,
            f"Purchase {cc_amount} CC credits",
            metadata
        )
        
        # Create transaction record
        transaction = Transaction(
            user_id=user_id,
            type=TransactionType.PAYMENT,
            status=TransactionStatus.PENDING,
            amount_cc=cc_amount,
            payment_method=payment_method,
            external_transaction_id=payment_result["payment_id"],
            description=f"CC purchase via {payment_method.value}",
            metadata={
                "payment_gateway_response": payment_result,
                "usd_amount": str(amount_usd),
                "cc_amount": str(cc_amount),
                **(metadata or {})
            }
        )
        
        self.db.add(transaction)
        self.db.commit()
        
        return {
            "transaction_id": transaction.id,
            "cc_amount": cc_amount,
            "usd_amount": amount_usd,
            "payment_method": payment_method.value,
            "payment_details": payment_result
        }
    
    async def complete_payment(self, transaction_id: str) -> Dict[str, Any]:
        """Complete a payment and add CC credits"""
        
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if transaction.status != TransactionStatus.PENDING:
            raise ValueError(f"Transaction {transaction_id} is not pending")
        
        # Get gateway and capture payment
        gateway = self.gateways.get(transaction.payment_method)
        if not gateway:
            raise ValueError(f"Gateway not found for {transaction.payment_method}")
        
        try:
            # Capture payment with gateway
            capture_result = await gateway.capture_payment(transaction.external_transaction_id)
            
            # Add CC credits to user account
            await self.cc_system.add_credits(
                transaction.user_id,
                transaction.amount_cc,
                TransactionType.CREDIT,
                f"CC purchase completed - {transaction.payment_method.value}",
                transaction.external_transaction_id,
                {"original_transaction_id": transaction_id}
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.COMPLETED
            transaction.processed_at = datetime.utcnow()
            transaction.metadata["capture_result"] = capture_result
            
            self.db.commit()
            
            logger.info(f"Completed payment {transaction_id} for user {transaction.user_id}")
            
            return {
                "transaction_id": transaction_id,
                "status": "completed",
                "cc_credits_added": transaction.amount_cc,
                "capture_result": capture_result
            }
            
        except Exception as e:
            # Mark transaction as failed
            transaction.status = TransactionStatus.FAILED
            transaction.metadata["error"] = str(e)
            self.db.commit()
            
            logger.error(f"Failed to complete payment {transaction_id}: {str(e)}")
            raise
    
    async def refund_payment(
        self,
        transaction_id: str,
        reason: str = "User requested refund"
    ) -> Dict[str, Any]:
        """Refund a completed payment"""
        
        transaction = self.db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not transaction:
            raise ValueError(f"Transaction {transaction_id} not found")
        
        if transaction.status != TransactionStatus.COMPLETED:
            raise ValueError(f"Transaction {transaction_id} is not completed")
        
        # Check if user has sufficient CC balance for refund
        user_balance = await self.cc_system.get_user_balance(transaction.user_id)
        if user_balance < transaction.amount_cc:
            raise ValueError("Insufficient CC balance for refund")
        
        # Get gateway and process refund
        gateway = self.gateways.get(transaction.payment_method)
        if not gateway:
            raise ValueError(f"Gateway not found for {transaction.payment_method}")
        
        try:
            # Process refund with gateway
            refund_result = await gateway.refund_payment(transaction.external_transaction_id)
            
            # Deduct CC credits from user account
            await self.cc_system.deduct_credits(
                transaction.user_id,
                transaction.amount_cc,
                TransactionType.REFUND,
                f"Refund: {reason}",
                metadata={"original_transaction_id": transaction_id}
            )
            
            # Update transaction status
            transaction.status = TransactionStatus.REFUNDED
            transaction.metadata["refund_result"] = refund_result
            transaction.metadata["refund_reason"] = reason
            
            self.db.commit()
            
            logger.info(f"Refunded payment {transaction_id} for user {transaction.user_id}")
            
            return {
                "transaction_id": transaction_id,
                "status": "refunded",
                "cc_credits_deducted": transaction.amount_cc,
                "refund_result": refund_result
            }
            
        except Exception as e:
            logger.error(f"Failed to refund payment {transaction_id}: {str(e)}")
            raise
    
    async def get_payment_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available payment methods for user"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        methods = [
            {
                "method": "paypal",
                "name": "PayPal",
                "description": "Pay with your PayPal account",
                "fee_rate": float(settings.payments.paypal_fee_rate),
                "fee_fixed": float(settings.payments.paypal_fee_fixed),
                "supported_currencies": ["USD", "EUR", "GBP", "CAD"]
            },
            {
                "method": "stripe",
                "name": "Credit/Debit Card",
                "description": "Pay with credit or debit card",
                "fee_rate": float(settings.payments.stripe_fee_rate),
                "fee_fixed": float(settings.payments.stripe_fee_fixed),
                "supported_currencies": ["USD", "EUR", "GBP", "CAD"]
            },
            {
                "method": "google_pay",
                "name": "Google Pay",
                "description": "Pay with Google Pay",
                "fee_rate": float(settings.payments.stripe_fee_rate),
                "fee_fixed": float(settings.payments.stripe_fee_fixed),
                "supported_currencies": ["USD", "EUR", "GBP", "CAD"]
            },
            {
                "method": "venmo",
                "name": "Venmo",
                "description": "Pay with Venmo",
                "fee_rate": float(settings.payments.paypal_fee_rate),
                "fee_fixed": float(settings.payments.paypal_fee_fixed),
                "supported_currencies": ["USD"]
            },
            {
                "method": "zelle",
                "name": "Zelle",
                "description": "Bank-to-bank transfer via Zelle",
                "fee_rate": 0.0,
                "fee_fixed": 0.0,
                "supported_currencies": ["USD"],
                "processing_time": "1-3 business days"
            }
        ]
        
        return methods