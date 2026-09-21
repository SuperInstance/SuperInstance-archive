"""
Payment Integration System
Handles payment processing, billing, and financial transactions
"""

import asyncio
import json
import logging
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import redis
import aiohttp

class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    STRIPE = "stripe"
    CRYPTO = "crypto"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

@dataclass
class PaymentMethodInfo:
    """Payment method information"""
    method_id: str
    user_id: str
    method_type: PaymentMethod
    
    # Card/Bank details (encrypted)
    encrypted_details: Dict[str, str] = field(default_factory=dict)
    
    # Display information
    display_name: str = ""
    last_four: str = ""
    expiry_month: Optional[int] = None
    expiry_year: Optional[int] = None
    
    # Status
    is_default: bool = False
    is_valid: bool = True
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class PaymentTransaction:
    """Payment transaction record"""
    transaction_id: str
    user_id: str
    amount: Decimal
    currency: str
    
    # Transaction details
    description: str
    payment_method_id: str
    status: PaymentStatus
    
    # Billing reference
    session_id: Optional[str] = None
    bill_id: Optional[str] = None
    
    # Processing details
    processor: str = "internal"
    processor_transaction_id: Optional[str] = None
    processor_response: Dict[str, Any] = field(default_factory=dict)
    
    # Fees and taxes
    processing_fee: Decimal = Decimal("0.00")
    tax_amount: Decimal = Decimal("0.00")
    net_amount: Decimal = Decimal("0.00")
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)

class PaymentIntegrationSystem:
    """
    Payment processing system with multiple provider support
    """
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.logger = logging.getLogger(__name__)
        
        # Payment methods and transactions
        self.payment_methods: Dict[str, PaymentMethodInfo] = {}
        self.transactions: Dict[str, PaymentTransaction] = {}
        
        # Provider configurations
        self.payment_providers = {
            "stripe": {
                "api_key": "",  # Configure externally
                "webhook_secret": "",
                "enabled": True
            },
            "paypal": {
                "client_id": "",
                "client_secret": "",
                "enabled": False
            }
        }
        
        # Encryption key for sensitive data
        self.encryption_key = "change_this_key_in_production"  # Use proper key management
        
        # Processing fees (percentages)
        self.processing_fees = {
            PaymentMethod.CREDIT_CARD: Decimal("0.029"),  # 2.9%
            PaymentMethod.DEBIT_CARD: Decimal("0.025"),   # 2.5%
            PaymentMethod.BANK_TRANSFER: Decimal("0.008"), # 0.8%
            PaymentMethod.PAYPAL: Decimal("0.034"),       # 3.4%
            PaymentMethod.STRIPE: Decimal("0.029"),       # 2.9%
            PaymentMethod.CRYPTO: Decimal("0.015")        # 1.5%
        }
        
        # Performance metrics
        self.metrics = {
            "transactions_processed": 0,
            "successful_payments": 0,
            "failed_payments": 0,
            "total_volume": Decimal("0.00"),
            "total_fees": Decimal("0.00")
        }

    async def add_payment_method(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add payment method for user"""
        try:
            user_id = payment_data["user_id"]
            method_type = PaymentMethod(payment_data["method_type"])
            
            # Generate method ID
            method_id = f"pm_{user_id}_{method_type.value}_{int(datetime.now().timestamp())}"
            
            # Encrypt sensitive details
            sensitive_details = payment_data.get("payment_details", {})
            encrypted_details = await self._encrypt_payment_details(sensitive_details)
            
            # Create payment method
            payment_method = PaymentMethodInfo(
                method_id=method_id,
                user_id=user_id,
                method_type=method_type,
                encrypted_details=encrypted_details,
                display_name=payment_data.get("display_name", f"{method_type.value.title()} Payment"),
                last_four=sensitive_details.get("card_number", "")[-4:] if "card_number" in sensitive_details else "",
                expiry_month=sensitive_details.get("expiry_month"),
                expiry_year=sensitive_details.get("expiry_year"),
                is_default=payment_data.get("is_default", False)
            )
            
            # Store payment method
            self.payment_methods[method_id] = payment_method
            
            # Store in Redis
            if self.redis_client:
                await self._store_payment_method_in_redis(payment_method)
            
            # Set as default if requested or if first method
            if payment_method.is_default or not await self._user_has_payment_methods(user_id):
                await self._set_default_payment_method(user_id, method_id)
            
            self.logger.info(f"Added payment method {method_id} for user {user_id}")
            
            return {
                "method_id": method_id,
                "status": "added",
                "display_name": payment_method.display_name,
                "last_four": payment_method.last_four,
                "is_default": payment_method.is_default
            }
            
        except Exception as e:
            self.logger.error(f"Failed to add payment method: {e}")
            return {"error": str(e)}

    async def process_payment(self, payment_request: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for bill"""
        try:
            # Create transaction record
            transaction = await self._create_transaction(payment_request)
            
            # Validate payment method
            payment_method = self.payment_methods.get(transaction.payment_method_id)
            if not payment_method or not payment_method.is_valid:
                transaction.status = PaymentStatus.FAILED
                await self._update_transaction(transaction)
                return {"transaction_id": transaction.transaction_id, "status": "failed", "error": "Invalid payment method"}
            
            # Calculate fees and taxes
            await self._calculate_fees_and_taxes(transaction)
            
            # Process payment based on method type
            result = await self._process_payment_by_method(transaction, payment_method)
            
            # Update transaction status
            transaction.status = PaymentStatus.COMPLETED if result["success"] else PaymentStatus.FAILED
            transaction.processed_at = datetime.now(timezone.utc)
            
            if result["success"]:
                transaction.processor_transaction_id = result.get("transaction_id")
                transaction.completed_at = datetime.now(timezone.utc)
                
                # Update metrics
                self.metrics["successful_payments"] += 1
                self.metrics["total_volume"] += transaction.amount
                self.metrics["total_fees"] += transaction.processing_fee
            else:
                self.metrics["failed_payments"] += 1
                transaction.processor_response = result.get("error_details", {})
            
            self.metrics["transactions_processed"] += 1
            
            # Store updated transaction
            await self._update_transaction(transaction)
            
            return {
                "transaction_id": transaction.transaction_id,
                "status": transaction.status.value,
                "amount": float(transaction.amount),
                "processing_fee": float(transaction.processing_fee),
                "net_amount": float(transaction.net_amount),
                "processor_transaction_id": transaction.processor_transaction_id,
                "processed_at": transaction.processed_at.isoformat() if transaction.processed_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Payment processing failed: {e}")
            return {"error": str(e)}

    async def get_payment_methods(self, user_id: str) -> Dict[str, Any]:
        """Get user's payment methods"""
        try:
            user_methods = [
                method for method in self.payment_methods.values()
                if method.user_id == user_id and method.is_valid
            ]
            
            # Load from Redis if not in memory
            if not user_methods and self.redis_client:
                user_methods = await self._load_user_payment_methods_from_redis(user_id)
            
            return {
                "user_id": user_id,
                "payment_methods": [
                    {
                        "method_id": method.method_id,
                        "method_type": method.method_type.value,
                        "display_name": method.display_name,
                        "last_four": method.last_four,
                        "expiry_month": method.expiry_month,
                        "expiry_year": method.expiry_year,
                        "is_default": method.is_default,
                        "created_at": method.created_at.isoformat()
                    }
                    for method in user_methods
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get payment methods: {e}")
            return {"error": str(e)}

    async def get_transaction_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get user's transaction history"""
        try:
            user_transactions = [
                transaction for transaction in self.transactions.values()
                if transaction.user_id == user_id
            ]
            
            # Sort by creation time (newest first)
            user_transactions.sort(key=lambda t: t.created_at, reverse=True)
            
            # Limit results
            user_transactions = user_transactions[:limit]
            
            return {
                "user_id": user_id,
                "transactions": [
                    {
                        "transaction_id": tx.transaction_id,
                        "amount": float(tx.amount),
                        "currency": tx.currency,
                        "description": tx.description,
                        "status": tx.status.value,
                        "payment_method_id": tx.payment_method_id,
                        "processing_fee": float(tx.processing_fee),
                        "created_at": tx.created_at.isoformat(),
                        "completed_at": tx.completed_at.isoformat() if tx.completed_at else None,
                        "session_id": tx.session_id,
                        "bill_id": tx.bill_id
                    }
                    for tx in user_transactions
                ]
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get transaction history: {e}")
            return {"error": str(e)}

    async def refund_payment(self, transaction_id: str, refund_amount: Optional[float] = None) -> Dict[str, Any]:
        """Process payment refund"""
        try:
            transaction = self.transactions.get(transaction_id)
            if not transaction:
                return {"error": "Transaction not found"}
            
            if transaction.status != PaymentStatus.COMPLETED:
                return {"error": "Only completed transactions can be refunded"}
            
            refund_amount_decimal = Decimal(str(refund_amount)) if refund_amount else transaction.amount
            
            if refund_amount_decimal > transaction.amount:
                return {"error": "Refund amount cannot exceed original transaction amount"}
            
            # Create refund transaction
            refund_transaction = PaymentTransaction(
                transaction_id=f"refund_{transaction_id}_{int(datetime.now().timestamp())}",
                user_id=transaction.user_id,
                amount=-refund_amount_decimal,  # Negative amount for refund
                currency=transaction.currency,
                description=f"Refund for {transaction.description}",
                payment_method_id=transaction.payment_method_id,
                status=PaymentStatus.PROCESSING,
                session_id=transaction.session_id,
                bill_id=transaction.bill_id,
                processor=transaction.processor,
                net_amount=-refund_amount_decimal
            )
            
            # Process refund
            refund_result = await self._process_refund(transaction, refund_transaction)
            
            if refund_result["success"]:
                refund_transaction.status = PaymentStatus.COMPLETED
                refund_transaction.completed_at = datetime.now(timezone.utc)
                
                # Update original transaction
                transaction.status = PaymentStatus.REFUNDED
                await self._update_transaction(transaction)
            else:
                refund_transaction.status = PaymentStatus.FAILED
                refund_transaction.processor_response = refund_result.get("error_details", {})
            
            # Store refund transaction
            self.transactions[refund_transaction.transaction_id] = refund_transaction
            await self._update_transaction(refund_transaction)
            
            return {
                "refund_transaction_id": refund_transaction.transaction_id,
                "status": refund_transaction.status.value,
                "refund_amount": float(refund_amount_decimal),
                "processed_at": refund_transaction.processed_at.isoformat() if refund_transaction.processed_at else None
            }
            
        except Exception as e:
            self.logger.error(f"Refund processing failed: {e}")
            return {"error": str(e)}

    async def _create_transaction(self, payment_request: Dict[str, Any]) -> PaymentTransaction:
        """Create payment transaction record"""
        user_id = payment_request["user_id"]
        amount = Decimal(str(payment_request["amount"]))
        
        transaction_id = f"txn_{user_id}_{int(datetime.now().timestamp())}"
        
        return PaymentTransaction(
            transaction_id=transaction_id,
            user_id=user_id,
            amount=amount,
            currency=payment_request.get("currency", "USD"),
            description=payment_request.get("description", "ActiveLog Service Payment"),
            payment_method_id=payment_request["payment_method_id"],
            status=PaymentStatus.PENDING,
            session_id=payment_request.get("session_id"),
            bill_id=payment_request.get("bill_id"),
            processor=payment_request.get("processor", "internal"),
            metadata=payment_request.get("metadata", {})
        )

    async def _calculate_fees_and_taxes(self, transaction: PaymentTransaction):
        """Calculate processing fees and taxes"""
        try:
            payment_method = self.payment_methods[transaction.payment_method_id]
            
            # Calculate processing fee
            fee_rate = self.processing_fees.get(payment_method.method_type, Decimal("0.029"))
            transaction.processing_fee = (transaction.amount * fee_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Calculate tax (simplified - would integrate with tax service)
            tax_rate = Decimal("0.00")  # No tax for now
            transaction.tax_amount = (transaction.amount * tax_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # Calculate net amount
            transaction.net_amount = transaction.amount - transaction.processing_fee - transaction.tax_amount
            
        except Exception as e:
            self.logger.error(f"Fee calculation failed: {e}")
            transaction.processing_fee = Decimal("0.00")
            transaction.tax_amount = Decimal("0.00")
            transaction.net_amount = transaction.amount

    async def _process_payment_by_method(
        self,
        transaction: PaymentTransaction,
        payment_method: PaymentMethodInfo
    ) -> Dict[str, Any]:
        """Process payment based on method type"""
        try:
            if payment_method.method_type == PaymentMethod.STRIPE:
                return await self._process_stripe_payment(transaction, payment_method)
            elif payment_method.method_type == PaymentMethod.PAYPAL:
                return await self._process_paypal_payment(transaction, payment_method)
            elif payment_method.method_type in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
                return await self._process_card_payment(transaction, payment_method)
            else:
                # Simulate other payment methods
                return await self._simulate_payment_processing(transaction, payment_method)
            
        except Exception as e:
            self.logger.error(f"Payment processing by method failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_stripe_payment(
        self,
        transaction: PaymentTransaction,
        payment_method: PaymentMethodInfo
    ) -> Dict[str, Any]:
        """Process Stripe payment"""
        try:
            stripe_config = self.payment_providers["stripe"]
            if not stripe_config["enabled"] or not stripe_config["api_key"]:
                return {"success": False, "error": "Stripe not configured"}
            
            # Simulate Stripe API call
            self.logger.info(f"Processing Stripe payment for ${transaction.amount}")
            
            # In production, this would make actual Stripe API calls
            payment_result = {
                "success": True,
                "transaction_id": f"stripe_{int(datetime.now().timestamp())}",
                "status": "succeeded"
            }
            
            return payment_result
            
        except Exception as e:
            self.logger.error(f"Stripe payment failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_paypal_payment(
        self,
        transaction: PaymentTransaction,
        payment_method: PaymentMethodInfo
    ) -> Dict[str, Any]:
        """Process PayPal payment"""
        try:
            paypal_config = self.payment_providers["paypal"]
            if not paypal_config["enabled"]:
                return {"success": False, "error": "PayPal not configured"}
            
            # Simulate PayPal payment
            self.logger.info(f"Processing PayPal payment for ${transaction.amount}")
            
            return {
                "success": True,
                "transaction_id": f"paypal_{int(datetime.now().timestamp())}",
                "status": "completed"
            }
            
        except Exception as e:
            self.logger.error(f"PayPal payment failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_card_payment(
        self,
        transaction: PaymentTransaction,
        payment_method: PaymentMethodInfo
    ) -> Dict[str, Any]:
        """Process credit/debit card payment"""
        try:
            # Decrypt card details
            card_details = await self._decrypt_payment_details(payment_method.encrypted_details)
            
            # Validate card
            if not self._validate_card_details(card_details):
                return {"success": False, "error": "Invalid card details"}
            
            # Simulate card processing
            self.logger.info(f"Processing card payment for ${transaction.amount}")
            
            # Simulate success/failure based on amount (for testing)
            if transaction.amount < Decimal("10000"):  # Under $10,000 always succeeds
                return {
                    "success": True,
                    "transaction_id": f"card_{int(datetime.now().timestamp())}",
                    "authorization_code": f"AUTH{int(datetime.now().timestamp())}"
                }
            else:
                return {"success": False, "error": "Amount exceeds card limit"}
            
        except Exception as e:
            self.logger.error(f"Card payment failed: {e}")
            return {"success": False, "error": str(e)}

    async def _simulate_payment_processing(
        self,
        transaction: PaymentTransaction,
        payment_method: PaymentMethodInfo
    ) -> Dict[str, Any]:
        """Simulate payment processing for testing"""
        try:
            # Simulate processing delay
            await asyncio.sleep(1)
            
            # Simulate success rate (95% success)
            import random
            success = random.random() < 0.95
            
            if success:
                return {
                    "success": True,
                    "transaction_id": f"sim_{int(datetime.now().timestamp())}",
                    "status": "completed"
                }
            else:
                return {
                    "success": False,
                    "error": "Simulated payment failure",
                    "error_code": "DECLINED"
                }
            
        except Exception as e:
            self.logger.error(f"Simulated payment failed: {e}")
            return {"success": False, "error": str(e)}

    async def _process_refund(
        self,
        original_transaction: PaymentTransaction,
        refund_transaction: PaymentTransaction
    ) -> Dict[str, Any]:
        """Process refund"""
        try:
            # Simulate refund processing
            self.logger.info(f"Processing refund of ${abs(refund_transaction.amount)} for transaction {original_transaction.transaction_id}")
            
            # In production, this would call the appropriate payment provider's refund API
            return {
                "success": True,
                "refund_id": f"refund_{int(datetime.now().timestamp())}",
                "status": "completed"
            }
            
        except Exception as e:
            self.logger.error(f"Refund processing failed: {e}")
            return {"success": False, "error": str(e)}

    def _validate_card_details(self, card_details: Dict[str, str]) -> bool:
        """Validate card details"""
        try:
            # Basic validation
            card_number = card_details.get("card_number", "")
            if len(card_number) < 13 or len(card_number) > 19:
                return False
            
            expiry_month = card_details.get("expiry_month")
            expiry_year = card_details.get("expiry_year")
            
            if not expiry_month or not expiry_year:
                return False
            
            # Check expiry date
            current_date = datetime.now()
            if (expiry_year < current_date.year or 
                (expiry_year == current_date.year and expiry_month < current_date.month)):
                return False
            
            return True
            
        except Exception:
            return False

    async def _encrypt_payment_details(self, details: Dict[str, Any]) -> Dict[str, str]:
        """Encrypt sensitive payment details"""
        try:
            encrypted_details = {}
            
            for key, value in details.items():
                if isinstance(value, (str, int)):
                    # Simple encryption (use proper encryption in production)
                    encrypted_value = self._simple_encrypt(str(value))
                    encrypted_details[key] = encrypted_value
            
            return encrypted_details
            
        except Exception as e:
            self.logger.error(f"Encryption failed: {e}")
            return {}

    async def _decrypt_payment_details(self, encrypted_details: Dict[str, str]) -> Dict[str, str]:
        """Decrypt payment details"""
        try:
            decrypted_details = {}
            
            for key, encrypted_value in encrypted_details.items():
                decrypted_value = self._simple_decrypt(encrypted_value)
                decrypted_details[key] = decrypted_value
            
            return decrypted_details
            
        except Exception as e:
            self.logger.error(f"Decryption failed: {e}")
            return {}

    def _simple_encrypt(self, data: str) -> str:
        """Simple encryption (use proper encryption in production)"""
        try:
            import base64
            # This is not secure - use proper encryption
            encoded = base64.b64encode(data.encode()).decode()
            return encoded
        except Exception:
            return data

    def _simple_decrypt(self, encrypted_data: str) -> str:
        """Simple decryption (use proper decryption in production)"""
        try:
            import base64
            # This is not secure - use proper decryption
            decoded = base64.b64decode(encrypted_data.encode()).decode()
            return decoded
        except Exception:
            return encrypted_data

    async def _user_has_payment_methods(self, user_id: str) -> bool:
        """Check if user has any payment methods"""
        return any(
            method.user_id == user_id and method.is_valid
            for method in self.payment_methods.values()
        )

    async def _set_default_payment_method(self, user_id: str, method_id: str):
        """Set default payment method for user"""
        try:
            # Unset current default
            for method in self.payment_methods.values():
                if method.user_id == user_id and method.is_default:
                    method.is_default = False
                    await self._update_payment_method_in_redis(method)
            
            # Set new default
            if method_id in self.payment_methods:
                self.payment_methods[method_id].is_default = True
                await self._update_payment_method_in_redis(self.payment_methods[method_id])
            
        except Exception as e:
            self.logger.error(f"Failed to set default payment method: {e}")

    async def _store_payment_method_in_redis(self, payment_method: PaymentMethodInfo):
        """Store payment method in Redis"""
        try:
            if not self.redis_client:
                return
            
            method_key = f"payment_method:{payment_method.method_id}"
            
            method_data = {
                "method_id": payment_method.method_id,
                "user_id": payment_method.user_id,
                "method_type": payment_method.method_type.value,
                "encrypted_details": json.dumps(payment_method.encrypted_details),
                "display_name": payment_method.display_name,
                "last_four": payment_method.last_four,
                "expiry_month": str(payment_method.expiry_month) if payment_method.expiry_month else "",
                "expiry_year": str(payment_method.expiry_year) if payment_method.expiry_year else "",
                "is_default": str(payment_method.is_default),
                "is_valid": str(payment_method.is_valid),
                "created_at": payment_method.created_at.isoformat()
            }
            
            await self.redis_client.hset(method_key, mapping=method_data)
            await self.redis_client.expire(method_key, 2592000)  # 30 days
            
            # Add to user's payment methods set
            user_methods_key = f"user_payment_methods:{payment_method.user_id}"
            await self.redis_client.sadd(user_methods_key, payment_method.method_id)
            await self.redis_client.expire(user_methods_key, 2592000)
            
        except Exception as e:
            self.logger.error(f"Failed to store payment method in Redis: {e}")

    async def _update_payment_method_in_redis(self, payment_method: PaymentMethodInfo):
        """Update payment method in Redis"""
        await self._store_payment_method_in_redis(payment_method)

    async def _load_user_payment_methods_from_redis(self, user_id: str) -> List[PaymentMethodInfo]:
        """Load user's payment methods from Redis"""
        try:
            if not self.redis_client:
                return []
            
            user_methods_key = f"user_payment_methods:{user_id}"
            method_ids = await self.redis_client.smembers(user_methods_key)
            
            methods = []
            for method_id in method_ids:
                method_key = f"payment_method:{method_id}"
                method_data = await self.redis_client.hgetall(method_key)
                
                if method_data:
                    method = PaymentMethodInfo(
                        method_id=method_data["method_id"],
                        user_id=method_data["user_id"],
                        method_type=PaymentMethod(method_data["method_type"]),
                        encrypted_details=json.loads(method_data.get("encrypted_details", "{}")),
                        display_name=method_data["display_name"],
                        last_four=method_data["last_four"],
                        expiry_month=int(method_data["expiry_month"]) if method_data.get("expiry_month") else None,
                        expiry_year=int(method_data["expiry_year"]) if method_data.get("expiry_year") else None,
                        is_default=method_data.get("is_default", "False") == "True",
                        is_valid=method_data.get("is_valid", "True") == "True",
                        created_at=datetime.fromisoformat(method_data["created_at"])
                    )
                    
                    methods.append(method)
                    self.payment_methods[method_id] = method
            
            return methods
            
        except Exception as e:
            self.logger.error(f"Failed to load payment methods from Redis: {e}")
            return []

    async def _update_transaction(self, transaction: PaymentTransaction):
        """Update transaction in storage"""
        try:
            self.transactions[transaction.transaction_id] = transaction
            
            if self.redis_client:
                await self._store_transaction_in_redis(transaction)
            
        except Exception as e:
            self.logger.error(f"Failed to update transaction: {e}")

    async def _store_transaction_in_redis(self, transaction: PaymentTransaction):
        """Store transaction in Redis"""
        try:
            if not self.redis_client:
                return
            
            transaction_key = f"payment_transaction:{transaction.transaction_id}"
            
            transaction_data = {
                "transaction_id": transaction.transaction_id,
                "user_id": transaction.user_id,
                "amount": str(transaction.amount),
                "currency": transaction.currency,
                "description": transaction.description,
                "payment_method_id": transaction.payment_method_id,
                "status": transaction.status.value,
                "session_id": transaction.session_id or "",
                "bill_id": transaction.bill_id or "",
                "processor": transaction.processor,
                "processor_transaction_id": transaction.processor_transaction_id or "",
                "processing_fee": str(transaction.processing_fee),
                "tax_amount": str(transaction.tax_amount),
                "net_amount": str(transaction.net_amount),
                "created_at": transaction.created_at.isoformat(),
                "processed_at": transaction.processed_at.isoformat() if transaction.processed_at else "",
                "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else "",
                "metadata": json.dumps(transaction.metadata)
            }
            
            await self.redis_client.hset(transaction_key, mapping=transaction_data)
            await self.redis_client.expire(transaction_key, 7776000)  # 90 days
            
            # Add to user's transaction list
            user_transactions_key = f"user_transactions:{transaction.user_id}"
            await self.redis_client.zadd(
                user_transactions_key,
                {transaction.transaction_id: transaction.created_at.timestamp()}
            )
            await self.redis_client.expire(user_transactions_key, 7776000)
            
        except Exception as e:
            self.logger.error(f"Failed to store transaction in Redis: {e}")

    async def get_payment_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get payment statistics"""
        try:
            if user_id:
                # User-specific stats
                user_transactions = [
                    tx for tx in self.transactions.values()
                    if tx.user_id == user_id
                ]
                
                total_amount = sum(float(tx.amount) for tx in user_transactions if tx.status == PaymentStatus.COMPLETED)
                total_fees = sum(float(tx.processing_fee) for tx in user_transactions if tx.status == PaymentStatus.COMPLETED)
                
                return {
                    "user_id": user_id,
                    "total_transactions": len(user_transactions),
                    "successful_transactions": sum(1 for tx in user_transactions if tx.status == PaymentStatus.COMPLETED),
                    "failed_transactions": sum(1 for tx in user_transactions if tx.status == PaymentStatus.FAILED),
                    "total_amount": total_amount,
                    "total_fees": total_fees,
                    "average_transaction": total_amount / len(user_transactions) if user_transactions else 0
                }
            else:
                # System-wide stats
                return {
                    "system_stats": {
                        "total_transactions": self.metrics["transactions_processed"],
                        "successful_payments": self.metrics["successful_payments"],
                        "failed_payments": self.metrics["failed_payments"],
                        "total_volume": float(self.metrics["total_volume"]),
                        "total_fees": float(self.metrics["total_fees"]),
                        "success_rate": (
                            self.metrics["successful_payments"] / self.metrics["transactions_processed"]
                            if self.metrics["transactions_processed"] > 0 else 0
                        ) * 100
                    },
                    "provider_stats": {
                        provider: config["enabled"]
                        for provider, config in self.payment_providers.items()
                    }
                }
            
        except Exception as e:
            self.logger.error(f"Failed to get payment stats: {e}")
            return {"error": str(e)}

    async def get_status(self) -> Dict[str, Any]:
        """Get payment system status"""
        return {
            "payment_methods": len(self.payment_methods),
            "active_transactions": len([tx for tx in self.transactions.values() if tx.status in [PaymentStatus.PENDING, PaymentStatus.PROCESSING]]),
            "completed_transactions": len([tx for tx in self.transactions.values() if tx.status == PaymentStatus.COMPLETED]),
            "failed_transactions": len([tx for tx in self.transactions.values() if tx.status == PaymentStatus.FAILED]),
            "metrics": {
                "transactions_processed": self.metrics["transactions_processed"],
                "successful_payments": self.metrics["successful_payments"],
                "failed_payments": self.metrics["failed_payments"],
                "total_volume": float(self.metrics["total_volume"]),
                "total_fees": float(self.metrics["total_fees"])
            },
            "providers": {
                provider: config["enabled"]
                for provider, config in self.payment_providers.items()
            },
            "redis_connected": self.redis_client is not None
        }

    async def shutdown(self):
        """Shutdown payment system"""
        try:
            self.logger.info("Shutting down payment integration system...")
            
            # Store final transaction states
            for transaction in self.transactions.values():
                if self.redis_client:
                    await self._store_transaction_in_redis(transaction)
            
            self.logger.info("Payment integration system shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during payment system shutdown: {e}")