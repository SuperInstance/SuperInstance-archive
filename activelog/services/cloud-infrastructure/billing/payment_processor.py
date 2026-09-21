#!/usr/bin/env python3
"""
Payment Processing System
Handles payments, invoice generation, and subscription management.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    """Payment status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethodType(Enum):
    """Payment method type enumeration"""
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    ACH = "ach"
    WIRE_TRANSFER = "wire_transfer"
    CRYPTO = "crypto"
    ENTERPRISE_CONTRACT = "enterprise_contract"

class InvoiceStatus(Enum):
    """Invoice status enumeration"""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

@dataclass
class PaymentMethod:
    """Payment method information"""
    method_id: str
    user_id: str
    type: PaymentMethodType
    is_default: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

@dataclass
class Payment:
    """Payment record"""
    payment_id: str
    user_id: str
    invoice_id: str
    amount: Decimal
    currency: str = "USD"
    payment_method_id: str = ""
    status: PaymentStatus = PaymentStatus.PENDING
    transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None

@dataclass
class Invoice:
    """Invoice record"""
    invoice_id: str
    user_id: str
    org_id: Optional[str] = None
    amount: Decimal = Decimal('0.00')
    tax_amount: Decimal = Decimal('0.00')
    total_amount: Decimal = Decimal('0.00')
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    billing_period_start: Optional[datetime] = None
    billing_period_end: Optional[datetime] = None
    due_date: Optional[datetime] = None
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

class PaymentProcessor:
    """Payment processing system"""
    
    def __init__(self, database_manager, config):
        self.database_manager = database_manager
        self.config = config
        self.payment_providers = {}
        
    async def initialize(self):
        """Initialize payment processor"""
        await self._setup_payment_tables()
        await self._initialize_payment_providers()
        
    async def _setup_payment_tables(self):
        """Setup payment-related database tables"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            # Payment methods table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_methods (
                    method_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Payments table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    payment_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    invoice_id TEXT NOT NULL,
                    amount DECIMAL(10,4) NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    payment_method_id TEXT,
                    status TEXT NOT NULL,
                    transaction_id TEXT,
                    failure_reason TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    processed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (payment_method_id) REFERENCES payment_methods (method_id)
                )
            """)
            
            # Invoices table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS invoices (
                    invoice_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    org_id TEXT,
                    amount DECIMAL(10,4) NOT NULL,
                    tax_amount DECIMAL(10,4) DEFAULT 0.00,
                    total_amount DECIMAL(10,4) NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    status TEXT NOT NULL,
                    billing_period_start TEXT,
                    billing_period_end TEXT,
                    due_date TEXT,
                    line_items TEXT,
                    metadata TEXT,
                    created_at TEXT NOT NULL,
                    sent_at TEXT,
                    paid_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await conn.commit()
            
    async def _initialize_payment_providers(self):
        """Initialize payment provider integrations"""
        # Mock payment providers for demonstration
        self.payment_providers = {
            'stripe': MockStripeProvider(),
            'paypal': MockPayPalProvider(),
            'enterprise': EnterpriseContractProvider()
        }
        
    # Payment Methods
    async def add_payment_method(self, user_id: str, method_type: PaymentMethodType, 
                               metadata: Dict[str, Any]) -> str:
        """Add a payment method for a user"""
        method_id = f"pm_{uuid.uuid4().hex[:12]}"
        
        payment_method = PaymentMethod(
            method_id=method_id,
            user_id=user_id,
            type=method_type,
            metadata=metadata
        )
        
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO payment_methods 
                (method_id, user_id, type, is_default, metadata, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                method_id, user_id, method_type.value, False,
                json.dumps(metadata), payment_method.created_at.isoformat(),
                payment_method.expires_at.isoformat() if payment_method.expires_at else None
            ))
            await conn.commit()
            
        return method_id
        
    async def get_user_payment_methods(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all payment methods for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT method_id, type, is_default, metadata, created_at, expires_at
                FROM payment_methods 
                WHERE user_id = ?
                ORDER BY is_default DESC, created_at DESC
            """, (user_id,)) as cursor:
                methods = []
                async for row in cursor:
                    methods.append({
                        'method_id': row[0],
                        'type': row[1],
                        'is_default': bool(row[2]),
                        'metadata': json.loads(row[3]) if row[3] else {},
                        'created_at': row[4],
                        'expires_at': row[5]
                    })
                return methods
    
    # Invoice Management
    async def create_invoice(self, user_id: str, org_id: Optional[str] = None,
                           billing_period_start: Optional[datetime] = None,
                           billing_period_end: Optional[datetime] = None) -> str:
        """Create a new invoice"""
        invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
        
        # If no billing period specified, use current month
        if not billing_period_start:
            now = datetime.now(timezone.utc)
            billing_period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Last day of current month
            next_month = billing_period_start.replace(month=billing_period_start.month + 1) if billing_period_start.month < 12 else billing_period_start.replace(year=billing_period_start.year + 1, month=1)
            billing_period_end = next_month - timedelta(seconds=1)
        
        # Calculate due date (30 days from creation)
        due_date = datetime.now(timezone.utc) + timedelta(days=30)
        
        invoice = Invoice(
            invoice_id=invoice_id,
            user_id=user_id,
            org_id=org_id,
            billing_period_start=billing_period_start,
            billing_period_end=billing_period_end,
            due_date=due_date
        )
        
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO invoices 
                (invoice_id, user_id, org_id, amount, tax_amount, total_amount, 
                 currency, status, billing_period_start, billing_period_end, 
                 due_date, line_items, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                invoice_id, user_id, org_id, float(invoice.amount), float(invoice.tax_amount),
                float(invoice.total_amount), invoice.currency, invoice.status.value,
                billing_period_start.isoformat(), billing_period_end.isoformat(),
                due_date.isoformat(), json.dumps(invoice.line_items),
                json.dumps(invoice.metadata), invoice.created_at.isoformat()
            ))
            await conn.commit()
            
        return invoice_id
        
    async def add_invoice_line_item(self, invoice_id: str, description: str, 
                                  quantity: int, unit_price: Decimal, 
                                  service_type: str = "compute") -> bool:
        """Add a line item to an invoice"""
        line_item = {
            'description': description,
            'quantity': quantity,
            'unit_price': float(unit_price),
            'total': float(quantity * unit_price),
            'service_type': service_type,
            'added_at': datetime.now(timezone.utc).isoformat()
        }
        
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            # Get current line items
            async with conn.execute("""
                SELECT line_items, amount FROM invoices WHERE invoice_id = ?
            """, (invoice_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                    
                current_items = json.loads(row[0]) if row[0] else []
                current_amount = Decimal(str(row[1]))
                
            # Add new line item
            current_items.append(line_item)
            new_amount = current_amount + (quantity * unit_price)
            
            # Calculate tax (10% for demo)
            tax_amount = new_amount * Decimal('0.10')
            total_amount = new_amount + tax_amount
            
            # Update invoice
            await conn.execute("""
                UPDATE invoices 
                SET line_items = ?, amount = ?, tax_amount = ?, total_amount = ?
                WHERE invoice_id = ?
            """, (
                json.dumps(current_items), float(new_amount), 
                float(tax_amount), float(total_amount), invoice_id
            ))
            await conn.commit()
            
        return True
        
    async def generate_usage_invoice(self, user_id: str, org_id: Optional[str] = None,
                                   billing_period_start: Optional[datetime] = None,
                                   billing_period_end: Optional[datetime] = None) -> str:
        """Generate an invoice based on usage data"""
        invoice_id = await self.create_invoice(user_id, org_id, billing_period_start, billing_period_end)
        
        if not billing_period_start:
            now = datetime.now(timezone.utc)
            billing_period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = billing_period_start.replace(month=billing_period_start.month + 1) if billing_period_start.month < 12 else billing_period_start.replace(year=billing_period_start.year + 1, month=1)
            billing_period_end = next_month - timedelta(seconds=1)
            
        # Get usage data from database directly
        import aiosqlite
        total_compute_cost = Decimal('0')
        total_storage_cost = Decimal('0')
        total_network_cost = Decimal('0')
        
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            # Get usage from billing_records or usage_records
            async with conn.execute("""
                SELECT COALESCE(SUM(compute_cost), 0), COALESCE(SUM(storage_cost), 0), COALESCE(SUM(network_cost), 0)
                FROM usage_records 
                WHERE user_id = ? AND created_at BETWEEN ? AND ?
            """, (user_id, billing_period_start.isoformat(), billing_period_end.isoformat())) as cursor:
                row = await cursor.fetchone()
                if row:
                    total_compute_cost = Decimal(str(row[0] or 0))
                    total_storage_cost = Decimal(str(row[1] or 0))
                    total_network_cost = Decimal(str(row[2] or 0))
        
        # Add line items for different services
        if total_compute_cost > 0:
            await self.add_invoice_line_item(
                invoice_id,
                f"Compute Usage - ${total_compute_cost:.2f}",
                1,
                total_compute_cost,
                "compute"
            )
            
        if total_storage_cost > 0:
            await self.add_invoice_line_item(
                invoice_id,
                f"Storage Usage - ${total_storage_cost:.2f}",
                1,
                total_storage_cost,
                "storage"
            )
            
        if total_network_cost > 0:
            await self.add_invoice_line_item(
                invoice_id,
                f"Network Usage - ${total_network_cost:.2f}",
                1,
                total_network_cost,
                "network"
            )
            
        return invoice_id
    
    # Payment Processing
    async def process_payment(self, invoice_id: str, payment_method_id: str) -> str:
        """Process a payment for an invoice"""
        payment_id = f"pay_{uuid.uuid4().hex[:12]}"
        
        # Get invoice details
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT user_id, total_amount, currency, status 
                FROM invoices WHERE invoice_id = ?
            """, (invoice_id,)) as cursor:
                invoice_row = await cursor.fetchone()
                if not invoice_row or invoice_row[3] != InvoiceStatus.SENT.value:
                    raise ValueError("Invoice not found or not ready for payment")
                    
                user_id, amount, currency, status = invoice_row
                
            # Get payment method details
            async with conn.execute("""
                SELECT type, metadata FROM payment_methods WHERE method_id = ?
            """, (payment_method_id,)) as cursor:
                method_row = await cursor.fetchone()
                if not method_row:
                    raise ValueError("Payment method not found")
                    
                method_type, method_metadata = method_row
                
        # Create payment record
        payment = Payment(
            payment_id=payment_id,
            user_id=user_id,
            invoice_id=invoice_id,
            amount=Decimal(str(amount)),
            currency=currency,
            payment_method_id=payment_method_id,
            status=PaymentStatus.PROCESSING
        )
        
        # Store payment record
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                INSERT INTO payments 
                (payment_id, user_id, invoice_id, amount, currency, 
                 payment_method_id, status, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                payment_id, user_id, invoice_id, float(payment.amount), 
                currency, payment_method_id, payment.status.value,
                json.dumps(payment.metadata), payment.created_at.isoformat()
            ))
            await conn.commit()
        
        # Process with appropriate provider
        try:
            provider = self._get_payment_provider(method_type)
            transaction_id = await provider.process_payment(payment, json.loads(method_metadata))
            
            # Update payment as successful
            await self._update_payment_status(
                payment_id, PaymentStatus.COMPLETED, transaction_id
            )
            
            # Mark invoice as paid
            await self._mark_invoice_paid(invoice_id)
            
            logger.info(f"Payment {payment_id} processed successfully")
            return payment_id
            
        except Exception as e:
            # Update payment as failed
            await self._update_payment_status(
                payment_id, PaymentStatus.FAILED, failure_reason=str(e)
            )
            logger.error(f"Payment {payment_id} failed: {e}")
            raise
            
    async def _update_payment_status(self, payment_id: str, status: PaymentStatus, 
                                   transaction_id: Optional[str] = None,
                                   failure_reason: Optional[str] = None):
        """Update payment status"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                UPDATE payments 
                SET status = ?, transaction_id = ?, failure_reason = ?, processed_at = ?
                WHERE payment_id = ?
            """, (
                status.value, transaction_id, failure_reason,
                datetime.now(timezone.utc).isoformat(), payment_id
            ))
            await conn.commit()
            
    async def _mark_invoice_paid(self, invoice_id: str):
        """Mark an invoice as paid"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                UPDATE invoices 
                SET status = ?, paid_at = ?
                WHERE invoice_id = ?
            """, (
                InvoiceStatus.PAID.value,
                datetime.now(timezone.utc).isoformat(),
                invoice_id
            ))
            await conn.commit()
    
    def _get_payment_provider(self, method_type: str):
        """Get appropriate payment provider"""
        if method_type in ['credit_card', 'debit_card']:
            return self.payment_providers['stripe']
        elif method_type == 'ach':
            return self.payment_providers['paypal']
        elif method_type == 'enterprise_contract':
            return self.payment_providers['enterprise']
        else:
            raise ValueError(f"Unsupported payment method: {method_type}")
    
    # Invoice Management
    async def send_invoice(self, invoice_id: str) -> bool:
        """Send an invoice to the customer"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            await conn.execute("""
                UPDATE invoices 
                SET status = ?, sent_at = ?
                WHERE invoice_id = ? AND status = ?
            """, (
                InvoiceStatus.SENT.value,
                datetime.now(timezone.utc).isoformat(),
                invoice_id,
                InvoiceStatus.DRAFT.value
            ))
            await conn.commit()
            
        # In a real system, this would send email/notification
        logger.info(f"Invoice {invoice_id} sent to customer")
        return True
        
    async def get_user_invoices(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get invoices for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT invoice_id, amount, tax_amount, total_amount, currency, 
                       status, billing_period_start, billing_period_end, 
                       due_date, created_at, sent_at, paid_at
                FROM invoices 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                invoices = []
                async for row in cursor:
                    invoices.append({
                        'invoice_id': row[0],
                        'amount': float(row[1]),
                        'tax_amount': float(row[2]),
                        'total_amount': float(row[3]),
                        'currency': row[4],
                        'status': row[5],
                        'billing_period_start': row[6],
                        'billing_period_end': row[7],
                        'due_date': row[8],
                        'created_at': row[9],
                        'sent_at': row[10],
                        'paid_at': row[11]
                    })
                return invoices
    
    async def get_payment_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get payment history for a user"""
        import aiosqlite
        async with aiosqlite.connect(self.database_manager.db_path) as conn:
            async with conn.execute("""
                SELECT p.payment_id, p.invoice_id, p.amount, p.currency, 
                       p.status, p.transaction_id, p.created_at, p.processed_at,
                       pm.type as payment_method_type
                FROM payments p
                LEFT JOIN payment_methods pm ON p.payment_method_id = pm.method_id
                WHERE p.user_id = ?
                ORDER BY p.created_at DESC
                LIMIT ?
            """, (user_id, limit)) as cursor:
                payments = []
                async for row in cursor:
                    payments.append({
                        'payment_id': row[0],
                        'invoice_id': row[1],
                        'amount': float(row[2]),
                        'currency': row[3],
                        'status': row[4],
                        'transaction_id': row[5],
                        'created_at': row[6],
                        'processed_at': row[7],
                        'payment_method_type': row[8]
                    })
                return payments
    
    # Subscription Management
    async def setup_recurring_billing(self, user_id: str, plan_name: str, 
                                    amount: Decimal, billing_cycle: str = "monthly") -> str:
        """Setup recurring billing for a user"""
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        
        # Store subscription details
        subscription = {
            'subscription_id': subscription_id,
            'user_id': user_id,
            'plan_name': plan_name,
            'amount': float(amount),
            'billing_cycle': billing_cycle,
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'next_billing_date': (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        }
        
        # In a real system, this would be stored in a subscriptions table
        logger.info(f"Recurring billing setup for user {user_id}: {plan_name} - ${amount}/{billing_cycle}")
        
        return subscription_id

# Mock Payment Providers
class MockStripeProvider:
    """Mock Stripe payment provider"""
    
    async def process_payment(self, payment: Payment, method_metadata: Dict[str, Any]) -> str:
        """Process payment through Stripe"""
        # Simulate processing delay
        await asyncio.sleep(0.1)
        
        # Mock success for amounts under $10000
        if payment.amount < Decimal('10000.00'):
            return f"stripe_tx_{uuid.uuid4().hex[:16]}"
        else:
            raise Exception("Payment declined - amount too large")

class MockPayPalProvider:
    """Mock PayPal payment provider"""
    
    async def process_payment(self, payment: Payment, method_metadata: Dict[str, Any]) -> str:
        """Process payment through PayPal"""
        await asyncio.sleep(0.2)
        return f"paypal_tx_{uuid.uuid4().hex[:16]}"

class EnterpriseContractProvider:
    """Enterprise contract payment provider"""
    
    async def process_payment(self, payment: Payment, method_metadata: Dict[str, Any]) -> str:
        """Process enterprise contract payment"""
        # Enterprise contracts are always approved
        return f"enterprise_tx_{uuid.uuid4().hex[:16]}"