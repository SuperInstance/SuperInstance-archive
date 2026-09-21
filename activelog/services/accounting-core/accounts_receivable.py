#!/usr/bin/env python3
"""
Accounts Receivable System
Handles customer invoice management, payment tracking, aging analysis, and collection management
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    OUTSTANDING = "outstanding"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    WRITTEN_OFF = "written_off"
    CANCELLED = "cancelled"

class PaymentMethod(str, Enum):
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    ACH = "ach"
    WIRE = "wire"
    OTHER = "other"

class AccountsReceivableSystem:
    """
    Comprehensive accounts receivable management system
    """
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # Aging buckets (days)
        self.aging_buckets = [
            (0, 30, "Current"),
            (31, 60, "31-60 days"),
            (61, 90, "61-90 days"),
            (91, 120, "91-120 days"),
            (121, float('inf'), "Over 120 days")
        ]
    
    async def initialize(self):
        """Initialize the accounts receivable system"""
        try:
            await self._setup_ar_tables()
            logger.info("Accounts receivable system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize AR system: {e}")
            raise
    
    async def _setup_ar_tables(self):
        """Setup AR-specific tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Customer information table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                customer_code TEXT UNIQUE NOT NULL,
                customer_name TEXT NOT NULL,
                contact_person TEXT,
                email TEXT,
                phone TEXT,
                billing_address TEXT,
                shipping_address TEXT,
                credit_limit DECIMAL DEFAULT 0,
                payment_terms INTEGER DEFAULT 30,
                tax_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # AR aging snapshots
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ar_aging_snapshots (
                id TEXT PRIMARY KEY,
                snapshot_date DATE NOT NULL,
                total_outstanding DECIMAL NOT NULL,
                current_amount DECIMAL NOT NULL,
                days_31_60 DECIMAL NOT NULL,
                days_61_90 DECIMAL NOT NULL,
                days_91_120 DECIMAL NOT NULL,
                over_120_days DECIMAL NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                aging_data TEXT NOT NULL
            )
        ''')
        
        # AR payments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ar_payments (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                invoice_id TEXT,
                payment_date DATE NOT NULL,
                payment_amount DECIMAL NOT NULL,
                payment_method TEXT NOT NULL,
                reference_number TEXT,
                bank_deposit_id TEXT,
                journal_entry_id TEXT,
                notes TEXT,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL,
                FOREIGN KEY (customer_id) REFERENCES customers (id),
                FOREIGN KEY (invoice_id) REFERENCES accounts_receivable (id),
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create customer invoice"""
        try:
            # Generate invoice ID and number
            invoice_id = f"INV_{uuid.uuid4().hex[:8].upper()}"
            invoice_number = self._generate_invoice_number()
            
            # Calculate due date
            invoice_date = datetime.strptime(invoice_data['invoice_date'], "%Y-%m-%d").date()
            payment_terms = invoice_data.get('payment_terms', 30)
            due_date = invoice_date + timedelta(days=payment_terms)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert invoice
            cursor.execute('''
                INSERT INTO accounts_receivable (
                    id, customer_id, invoice_number, invoice_date, due_date,
                    total_amount, amount_paid, amount_due, currency, status,
                    created_at, updated_at, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                invoice_id, invoice_data['customer_id'], invoice_number,
                invoice_data['invoice_date'], due_date.isoformat(),
                float(Decimal(str(invoice_data['total_amount']))),
                0, float(Decimal(str(invoice_data['total_amount']))),
                invoice_data.get('currency', 'USD'), InvoiceStatus.OUTSTANDING.value,
                datetime.now().isoformat(), datetime.now().isoformat(),
                json.dumps({**invoice_data, 'id': invoice_id, 'invoice_number': invoice_number})
            ))
            
            # Create journal entry for invoice
            await self._create_invoice_journal_entry(cursor, invoice_id, invoice_data)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'invoice_id': invoice_id,
                'invoice_number': invoice_number,
                'total_amount': Decimal(str(invoice_data['total_amount'])),
                'due_date': due_date.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            return {
                'success': False,
                'error': f"Invoice creation error: {str(e)}"
            }
    
    def _generate_invoice_number(self) -> str:
        """Generate unique invoice number"""
        date_str = datetime.now().strftime("%Y%m%d")
        random_str = uuid.uuid4().hex[:6].upper()
        return f"INV{date_str}{random_str}"
    
    async def _create_invoice_journal_entry(self, cursor, invoice_id: str, invoice_data: Dict[str, Any]):
        """Create journal entry for invoice"""
        from journal_entries import journal_system
        
        # Get AR account ID (assuming standard account code 1100)
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '1100' AND is_active = TRUE")
        ar_account_row = cursor.fetchone()
        if not ar_account_row:
            raise Exception("Accounts Receivable account not found")
        ar_account_id = ar_account_row[0]
        
        # Get revenue account ID (assuming standard account code 4000)
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '4000' AND is_active = TRUE")
        revenue_account_row = cursor.fetchone()
        if not revenue_account_row:
            raise Exception("Sales Revenue account not found")
        revenue_account_id = revenue_account_row[0]
        
        total_amount = Decimal(str(invoice_data['total_amount']))
        
        journal_entry_data = {
            'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
            'transaction_date': invoice_data['invoice_date'],
            'description': f"Invoice {invoice_data.get('description', 'Customer Invoice')}",
            'reference': invoice_id,
            'lines': [
                {
                    'account_id': ar_account_id,
                    'description': 'Customer Invoice - Accounts Receivable',
                    'debit_amount': float(total_amount),
                    'credit_amount': 0
                },
                {
                    'account_id': revenue_account_id,
                    'description': 'Customer Invoice - Sales Revenue',
                    'debit_amount': 0,
                    'credit_amount': float(total_amount)
                }
            ],
            'created_by': 'AR_SYSTEM'
        }
        
        result = await journal_system.create_entry(journal_entry_data)
        if result['success']:
            # Auto-approve and post
            await journal_system.approve_entry(result['journal_entry_id'], 'AR_SYSTEM')
            await journal_system.post_entry(result['journal_entry_id'], 'AR_SYSTEM')
            
            # Update invoice with journal entry reference
            cursor.execute(
                "UPDATE accounts_receivable SET journal_entry_id = ? WHERE id = ?",
                (result['journal_entry_id'], invoice_id)
            )
    
    async def record_payment(self, invoice_id: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record customer payment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get invoice details
            cursor.execute(
                "SELECT customer_id, total_amount, amount_paid, amount_due FROM accounts_receivable WHERE id = ?",
                (invoice_id,)
            )
            invoice_row = cursor.fetchone()
            if not invoice_row:
                return {'success': False, 'error': f"Invoice {invoice_id} not found"}
            
            customer_id, total_amount, amount_paid, amount_due = invoice_row
            payment_amount = Decimal(str(payment_data['payment_amount']))
            
            if payment_amount > Decimal(str(amount_due)):
                return {'success': False, 'error': "Payment amount exceeds amount due"}
            
            # Record payment
            payment_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO ar_payments (
                    id, customer_id, invoice_id, payment_date, payment_amount,
                    payment_method, reference_number, notes, created_by, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_id, customer_id, invoice_id, payment_data['payment_date'],
                float(payment_amount), payment_data.get('payment_method', PaymentMethod.CASH.value),
                payment_data.get('reference_number'), payment_data.get('notes'),
                payment_data.get('created_by', 'AR_SYSTEM'), json.dumps(payment_data)
            ))
            
            # Update invoice
            new_amount_paid = Decimal(str(amount_paid)) + payment_amount
            new_amount_due = Decimal(str(total_amount)) - new_amount_paid
            
            new_status = InvoiceStatus.PAID.value if new_amount_due <= Decimal('0.01') else InvoiceStatus.PARTIAL.value
            
            cursor.execute('''
                UPDATE accounts_receivable 
                SET amount_paid = ?, amount_due = ?, status = ?, updated_at = ?
                WHERE id = ?
            ''', (
                float(new_amount_paid), float(new_amount_due), new_status,
                datetime.now().isoformat(), invoice_id
            ))
            
            # Create payment journal entry
            await self._create_payment_journal_entry(cursor, payment_id, payment_data, payment_amount)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_amount': payment_amount,
                'new_balance': new_amount_due,
                'invoice_status': new_status
            }
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return {
                'success': False,
                'error': f"Payment recording error: {str(e)}"
            }
    
    async def _create_payment_journal_entry(self, cursor, payment_id: str, payment_data: Dict[str, Any], payment_amount: Decimal):
        """Create journal entry for payment"""
        from journal_entries import journal_system
        
        # Get cash account (assuming code 1000)
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '1000' AND is_active = TRUE")
        cash_account_row = cursor.fetchone()
        if not cash_account_row:
            raise Exception("Cash account not found")
        cash_account_id = cash_account_row[0]
        
        # Get AR account
        cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '1100' AND is_active = TRUE")
        ar_account_row = cursor.fetchone()
        if not ar_account_row:
            raise Exception("Accounts Receivable account not found")
        ar_account_id = ar_account_row[0]
        
        journal_entry_data = {
            'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
            'transaction_date': payment_data['payment_date'],
            'description': f"Customer Payment - {payment_data.get('payment_method', 'Cash')}",
            'reference': payment_id,
            'lines': [
                {
                    'account_id': cash_account_id,
                    'description': 'Customer Payment Received',
                    'debit_amount': float(payment_amount),
                    'credit_amount': 0
                },
                {
                    'account_id': ar_account_id,
                    'description': 'Reduce Accounts Receivable',
                    'debit_amount': 0,
                    'credit_amount': float(payment_amount)
                }
            ],
            'created_by': 'AR_SYSTEM'
        }
        
        result = await journal_system.create_entry(journal_entry_data)
        if result['success']:
            await journal_system.approve_entry(result['journal_entry_id'], 'AR_SYSTEM')
            await journal_system.post_entry(result['journal_entry_id'], 'AR_SYSTEM')
    
    async def get_receivables(self, customer_id: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
        """Get accounts receivable"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            where_conditions = []
            params = []
            
            if customer_id:
                where_conditions.append("ar.customer_id = ?")
                params.append(customer_id)
            
            if status:
                where_conditions.append("ar.status = ?")
                params.append(status)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            cursor.execute(f'''
                SELECT 
                    ar.id, ar.invoice_number, ar.invoice_date, ar.due_date,
                    ar.total_amount, ar.amount_paid, ar.amount_due, ar.status,
                    c.customer_name, c.customer_code
                FROM accounts_receivable ar
                JOIN customers c ON ar.customer_id = c.id
                {where_clause}
                ORDER BY ar.due_date
            ''', params)
            
            receivables = []
            for row in cursor.fetchall():
                receivables.append({
                    'id': row[0],
                    'invoice_number': row[1],
                    'invoice_date': row[2],
                    'due_date': row[3],
                    'total_amount': Decimal(str(row[4])),
                    'amount_paid': Decimal(str(row[5])),
                    'amount_due': Decimal(str(row[6])),
                    'status': row[7],
                    'customer_name': row[8],
                    'customer_code': row[9],
                    'days_outstanding': (date.today() - datetime.strptime(row[2], "%Y-%m-%d").date()).days
                })
            
            conn.close()
            
            return {
                'success': True,
                'receivables': receivables,
                'total_outstanding': sum(r['amount_due'] for r in receivables)
            }
            
        except Exception as e:
            logger.error(f"Error getting receivables: {e}")
            return {
                'success': False,
                'error': f"Get receivables error: {str(e)}"
            }
    
    async def generate_aging_report(self, as_of_date: Optional[str] = None) -> Dict[str, Any]:
        """Generate aging report"""
        try:
            if as_of_date is None:
                as_of_date = date.today().isoformat()
            
            reference_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    ar.id, ar.invoice_number, ar.invoice_date, ar.due_date,
                    ar.amount_due, c.customer_name, c.customer_code
                FROM accounts_receivable ar
                JOIN customers c ON ar.customer_id = c.id
                WHERE ar.amount_due > 0.01 AND ar.status != 'paid'
            ''')
            
            aging_data = {bucket[2]: [] for bucket in self.aging_buckets}
            aging_totals = {bucket[2]: Decimal('0') for bucket in self.aging_buckets}
            
            for row in cursor.fetchall():
                invoice_id, invoice_number, invoice_date, due_date = row[:4]
                amount_due, customer_name, customer_code = row[4:]
                
                invoice_date_obj = datetime.strptime(invoice_date, "%Y-%m-%d").date()
                days_outstanding = (reference_date - invoice_date_obj).days
                
                # Find appropriate aging bucket
                bucket_name = "Over 120 days"  # default
                for min_days, max_days, name in self.aging_buckets:
                    if min_days <= days_outstanding <= max_days:
                        bucket_name = name
                        break
                
                amount_decimal = Decimal(str(amount_due))
                aging_data[bucket_name].append({
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    'invoice_date': invoice_date,
                    'due_date': due_date,
                    'customer_name': customer_name,
                    'customer_code': customer_code,
                    'amount_due': amount_decimal,
                    'days_outstanding': days_outstanding
                })
                aging_totals[bucket_name] += amount_decimal
            
            total_outstanding = sum(aging_totals.values())
            
            conn.close()
            
            return {
                'success': True,
                'as_of_date': as_of_date,
                'aging_data': aging_data,
                'aging_totals': aging_totals,
                'total_outstanding': total_outstanding,
                'aging_percentages': {
                    bucket: (amount / total_outstanding * 100) if total_outstanding > 0 else Decimal('0')
                    for bucket, amount in aging_totals.items()
                }
            }
            
        except Exception as e:
            logger.error(f"Error generating aging report: {e}")
            return {
                'success': False,
                'error': f"Aging report error: {str(e)}"
            }

# Global instance
ar_system = AccountsReceivableSystem()