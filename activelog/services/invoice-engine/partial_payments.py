#!/usr/bin/env python3
"""
Partial Payment Tracking System
Advanced payment tracking with partial payments, overpayments, and credit management
"""

import json
import sqlite3
import asyncio
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentMethod(str, Enum):
    CASH = "cash"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    ACH = "ach"
    PAYPAL = "paypal"
    CRYPTO = "crypto"

class PartialPaymentTrackingSystem:
    """Comprehensive partial payment and credit management system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize payment tracking system"""
        try:
            await self._setup_payment_tables()
            logger.info("Partial payment tracking system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize payment tracking system: {e}")
            raise
    
    async def _setup_payment_tables(self):
        """Setup payment tracking tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                payment_number TEXT UNIQUE NOT NULL,
                invoice_id TEXT,
                customer_id TEXT NOT NULL,
                payment_date DATE NOT NULL,
                amount DECIMAL NOT NULL,
                payment_method TEXT NOT NULL,
                status TEXT DEFAULT 'processed',
                reference_number TEXT,
                notes TEXT,
                allocated_amount DECIMAL DEFAULT 0,
                unallocated_amount DECIMAL DEFAULT 0,
                is_overpayment BOOLEAN DEFAULT FALSE,
                processor_fee DECIMAL DEFAULT 0,
                net_amount DECIMAL NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Payment allocations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_allocations (
                id TEXT PRIMARY KEY,
                payment_id TEXT NOT NULL,
                invoice_id TEXT NOT NULL,
                allocated_amount DECIMAL NOT NULL,
                allocation_date DATE NOT NULL,
                allocation_type TEXT DEFAULT 'manual',
                created_by TEXT DEFAULT 'SYSTEM',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (payment_id) REFERENCES payments (id),
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        ''')
        
        # Customer credits table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customer_credits (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                credit_amount DECIMAL NOT NULL,
                used_amount DECIMAL DEFAULT 0,
                remaining_amount DECIMAL NOT NULL,
                source_type TEXT NOT NULL,
                source_id TEXT,
                expiry_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Payment plans table (for installments)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_plans (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                total_amount DECIMAL NOT NULL,
                paid_amount DECIMAL DEFAULT 0,
                remaining_amount DECIMAL NOT NULL,
                installment_amount DECIMAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                next_payment_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (invoice_id) REFERENCES invoices (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def record_payment(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Record a new payment"""
        try:
            payment_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
            payment_number = await self._generate_payment_number()
            
            amount = Decimal(str(payment_data['amount']))
            processor_fee = Decimal(str(payment_data.get('processor_fee', 0)))
            net_amount = amount - processor_fee
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO payments (
                    id, payment_number, invoice_id, customer_id, payment_date,
                    amount, payment_method, reference_number, notes,
                    unallocated_amount, processor_fee, net_amount, metadata, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_id, payment_number, payment_data.get('invoice_id'),
                payment_data['customer_id'], payment_data.get('payment_date', date.today().isoformat()),
                float(amount), payment_data['payment_method'],
                payment_data.get('reference_number'), payment_data.get('notes'),
                float(net_amount), float(processor_fee), float(net_amount),
                json.dumps(payment_data.get('metadata', {})), json.dumps(payment_data)
            ))
            
            # If specific invoice provided, attempt automatic allocation
            allocation_result = None
            if payment_data.get('invoice_id'):
                allocation_result = await self._auto_allocate_payment(
                    cursor, payment_id, payment_data['invoice_id'], net_amount
                )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'payment_number': payment_number,
                'amount': amount,
                'net_amount': net_amount,
                'allocation_result': allocation_result
            }
            
        except Exception as e:
            logger.error(f"Error recording payment: {e}")
            return {
                'success': False,
                'error': f"Payment recording error: {str(e)}"
            }
    
    async def _generate_payment_number(self) -> str:
        """Generate unique payment number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM payments")
        count = cursor.fetchone()[0] + 1
        
        conn.close()
        
        return f"PAY-{date.today().strftime('%Y%m')}-{count:05d}"
    
    async def _auto_allocate_payment(self, cursor, payment_id: str, invoice_id: str, amount: Decimal) -> Dict[str, Any]:
        """Automatically allocate payment to specified invoice"""
        try:
            # Get invoice details
            cursor.execute('''
                SELECT total_amount, paid_amount FROM invoices WHERE id = ?
            ''', (invoice_id,))
            
            invoice_row = cursor.fetchone()
            if not invoice_row:
                return {
                    'success': False,
                    'error': 'Invoice not found'
                }
            
            total_amount = Decimal(str(invoice_row[0]))
            paid_amount = Decimal(str(invoice_row[1] or 0))
            outstanding_amount = total_amount - paid_amount
            
            # Calculate allocation amount
            if amount >= outstanding_amount:
                # Full payment or overpayment
                allocated_amount = outstanding_amount
                is_overpayment = amount > outstanding_amount
                overpayment_amount = amount - outstanding_amount if is_overpayment else Decimal('0')
            else:
                # Partial payment
                allocated_amount = amount
                is_overpayment = False
                overpayment_amount = Decimal('0')
            
            # Create allocation record
            allocation_id = f"ALLOC_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO payment_allocations (
                    id, payment_id, invoice_id, allocated_amount, allocation_date
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                allocation_id, payment_id, invoice_id, float(allocated_amount),
                date.today().isoformat()
            ))
            
            # Update payment record
            unallocated = amount - allocated_amount
            cursor.execute('''
                UPDATE payments 
                SET allocated_amount = ?, unallocated_amount = ?, is_overpayment = ?
                WHERE id = ?
            ''', (float(allocated_amount), float(unallocated), is_overpayment, payment_id))
            
            # Update invoice
            new_paid_amount = paid_amount + allocated_amount
            new_status = 'paid' if new_paid_amount >= total_amount else 'partially_paid'
            
            cursor.execute('''
                UPDATE invoices 
                SET paid_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (float(new_paid_amount), new_status, invoice_id))
            
            # Handle overpayment by creating customer credit
            if overpayment_amount > 0:
                await self._create_customer_credit(
                    cursor, payment_id, overpayment_amount, 'overpayment'
                )
            
            return {
                'success': True,
                'allocation_id': allocation_id,
                'allocated_amount': allocated_amount,
                'is_overpayment': is_overpayment,
                'overpayment_amount': overpayment_amount,
                'invoice_status': new_status
            }
            
        except Exception as e:
            logger.error(f"Error auto-allocating payment: {e}")
            return {
                'success': False,
                'error': f"Allocation error: {str(e)}"
            }
    
    async def _create_customer_credit(self, cursor, source_id: str, amount: Decimal, source_type: str):
        """Create customer credit for overpayment or refund"""
        # Get customer_id from source
        if source_type == 'overpayment':
            cursor.execute('SELECT customer_id FROM payments WHERE id = ?', (source_id,))
        else:
            cursor.execute('SELECT customer_id FROM invoices WHERE id = ?', (source_id,))
        
        customer_row = cursor.fetchone()
        if not customer_row:
            return
        
        customer_id = customer_row[0]
        credit_id = f"CREDIT_{uuid.uuid4().hex[:8].upper()}"
        
        cursor.execute('''
            INSERT INTO customer_credits (
                id, customer_id, credit_amount, remaining_amount,
                source_type, source_id, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            credit_id, customer_id, float(amount), float(amount),
            source_type, source_id, json.dumps({
                'created_from': source_type,
                'original_amount': float(amount),
                'creation_date': date.today().isoformat()
            })
        ))
    
    async def allocate_payment(self, payment_id: str, allocations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Manually allocate payment to multiple invoices"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get payment details
            cursor.execute('''
                SELECT amount, allocated_amount, customer_id 
                FROM payments WHERE id = ?
            ''', (payment_id,))
            
            payment_row = cursor.fetchone()
            if not payment_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Payment not found'
                }
            
            payment_amount = Decimal(str(payment_row[0]))
            current_allocated = Decimal(str(payment_row[1]))
            customer_id = payment_row[2]
            
            # Calculate total allocation requested
            total_requested = sum(Decimal(str(alloc['amount'])) for alloc in allocations)
            available_amount = payment_amount - current_allocated
            
            if total_requested > available_amount:
                conn.close()
                return {
                    'success': False,
                    'error': f'Insufficient unallocated amount. Available: {available_amount}, Requested: {total_requested}'
                }
            
            allocation_results = []
            total_allocated = Decimal('0')
            
            for allocation in allocations:
                invoice_id = allocation['invoice_id']
                alloc_amount = Decimal(str(allocation['amount']))
                
                # Validate invoice belongs to same customer
                cursor.execute('SELECT customer_id, total_amount, paid_amount FROM invoices WHERE id = ?', (invoice_id,))
                invoice_row = cursor.fetchone()
                
                if not invoice_row:
                    continue
                
                if invoice_row[0] != customer_id:
                    continue
                
                invoice_total = Decimal(str(invoice_row[1]))
                invoice_paid = Decimal(str(invoice_row[2] or 0))
                invoice_outstanding = invoice_total - invoice_paid
                
                # Don't allocate more than outstanding
                final_allocation = min(alloc_amount, invoice_outstanding)
                
                if final_allocation > 0:
                    # Create allocation record
                    allocation_id = f"ALLOC_{uuid.uuid4().hex[:8].upper()}"
                    cursor.execute('''
                        INSERT INTO payment_allocations (
                            id, payment_id, invoice_id, allocated_amount,
                            allocation_date, allocation_type, created_by
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        allocation_id, payment_id, invoice_id, float(final_allocation),
                        date.today().isoformat(), 'manual', allocation.get('created_by', 'USER')
                    ))
                    
                    # Update invoice
                    new_paid = invoice_paid + final_allocation
                    new_status = 'paid' if new_paid >= invoice_total else 'partially_paid'
                    
                    cursor.execute('''
                        UPDATE invoices 
                        SET paid_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (float(new_paid), new_status, invoice_id))
                    
                    allocation_results.append({
                        'invoice_id': invoice_id,
                        'allocated_amount': final_allocation,
                        'new_invoice_status': new_status
                    })
                    
                    total_allocated += final_allocation
            
            # Update payment record
            new_allocated = current_allocated + total_allocated
            new_unallocated = payment_amount - new_allocated
            
            cursor.execute('''
                UPDATE payments 
                SET allocated_amount = ?, unallocated_amount = ?
                WHERE id = ?
            ''', (float(new_allocated), float(new_unallocated), payment_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'total_allocated': total_allocated,
                'remaining_unallocated': new_unallocated,
                'allocations': allocation_results
            }
            
        except Exception as e:
            logger.error(f"Error allocating payment: {e}")
            return {
                'success': False,
                'error': f"Allocation error: {str(e)}"
            }
    
    async def apply_customer_credit(self, customer_id: str, invoice_id: str, amount: Decimal) -> Dict[str, Any]:
        """Apply customer credit to an invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get available credits
            cursor.execute('''
                SELECT id, remaining_amount FROM customer_credits
                WHERE customer_id = ? AND is_active = TRUE AND remaining_amount > 0
                ORDER BY created_at ASC
            ''', (customer_id,))
            
            credits = cursor.fetchall()
            if not credits:
                conn.close()
                return {
                    'success': False,
                    'error': 'No available credits'
                }
            
            # Get invoice details
            cursor.execute('''
                SELECT total_amount, paid_amount FROM invoices WHERE id = ? AND customer_id = ?
            ''', (invoice_id, customer_id))
            
            invoice_row = cursor.fetchone()
            if not invoice_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Invoice not found'
                }
            
            total_amount = Decimal(str(invoice_row[0]))
            paid_amount = Decimal(str(invoice_row[1] or 0))
            outstanding = total_amount - paid_amount
            
            # Apply credits up to requested amount and outstanding balance
            amount_to_apply = min(amount, outstanding)
            applied_credits = []
            remaining_to_apply = amount_to_apply
            
            for credit_id, credit_remaining in credits:
                if remaining_to_apply <= 0:
                    break
                
                credit_amount = Decimal(str(credit_remaining))
                amount_from_credit = min(remaining_to_apply, credit_amount)
                
                # Update credit
                new_remaining = credit_amount - amount_from_credit
                cursor.execute('''
                    UPDATE customer_credits 
                    SET used_amount = used_amount + ?, remaining_amount = ?,
                        is_active = CASE WHEN ? <= 0.01 THEN FALSE ELSE TRUE END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (float(amount_from_credit), float(new_remaining), float(new_remaining), credit_id))
                
                applied_credits.append({
                    'credit_id': credit_id,
                    'amount_applied': amount_from_credit
                })
                
                remaining_to_apply -= amount_from_credit
            
            # Update invoice
            new_paid_amount = paid_amount + amount_to_apply
            new_status = 'paid' if new_paid_amount >= total_amount else 'partially_paid'
            
            cursor.execute('''
                UPDATE invoices 
                SET paid_amount = ?, status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (float(new_paid_amount), new_status, invoice_id))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'invoice_id': invoice_id,
                'amount_applied': amount_to_apply,
                'applied_credits': applied_credits,
                'new_invoice_status': new_status
            }
            
        except Exception as e:
            logger.error(f"Error applying customer credit: {e}")
            return {
                'success': False,
                'error': f"Credit application error: {str(e)}"
            }
    
    async def get_invoice_payments(self, invoice_id: str) -> Dict[str, Any]:
        """Get all payments allocated to an invoice"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.id, p.payment_number, p.payment_date, p.amount,
                       p.payment_method, pa.allocated_amount, p.reference_number
                FROM payments p
                JOIN payment_allocations pa ON p.id = pa.payment_id
                WHERE pa.invoice_id = ?
                ORDER BY p.payment_date DESC
            ''', (invoice_id,))
            
            payments = []
            total_paid = Decimal('0')
            
            for row in cursor.fetchall():
                allocated_amount = Decimal(str(row[5]))
                payments.append({
                    'payment_id': row[0],
                    'payment_number': row[1],
                    'payment_date': row[2],
                    'payment_amount': Decimal(str(row[3])),
                    'payment_method': row[4],
                    'allocated_amount': allocated_amount,
                    'reference_number': row[6]
                })
                total_paid += allocated_amount
            
            conn.close()
            
            return {
                'success': True,
                'invoice_id': invoice_id,
                'payments': payments,
                'total_paid': total_paid,
                'payment_count': len(payments)
            }
            
        except Exception as e:
            logger.error(f"Error getting invoice payments: {e}")
            return {
                'success': False,
                'error': f"Payment retrieval error: {str(e)}"
            }
    
    async def get_aging_report(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate accounts receivable aging report"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            today = date.today()
            base_query = '''
                SELECT i.id, i.invoice_number, i.customer_id, i.invoice_date,
                       i.due_date, i.total_amount, i.paid_amount, i.status
                FROM invoices i
                WHERE i.status IN ('sent', 'overdue', 'partially_paid')
                  AND (i.total_amount - COALESCE(i.paid_amount, 0)) > 0.01
            '''
            
            params = []
            if customer_id:
                base_query += " AND i.customer_id = ?"
                params.append(customer_id)
            
            cursor.execute(base_query, params)
            
            aging_buckets = {
                'current': [],      # Not yet due
                '1-30_days': [],    # 1-30 days overdue
                '31-60_days': [],   # 31-60 days overdue
                '61-90_days': [],   # 61-90 days overdue
                '90+_days': []      # 90+ days overdue
            }
            
            totals = {
                'current': Decimal('0'),
                '1-30_days': Decimal('0'),
                '31-60_days': Decimal('0'),
                '61-90_days': Decimal('0'),
                '90+_days': Decimal('0')
            }
            
            for row in cursor.fetchall():
                invoice_id = row[0]
                invoice_number = row[1]
                customer_id = row[2]
                invoice_date = row[3]
                due_date = datetime.strptime(row[4], '%Y-%m-%d').date()
                total_amount = Decimal(str(row[5]))
                paid_amount = Decimal(str(row[6] or 0))
                status = row[7]
                
                outstanding = total_amount - paid_amount
                days_overdue = (today - due_date).days
                
                invoice_data = {
                    'invoice_id': invoice_id,
                    'invoice_number': invoice_number,
                    'customer_id': customer_id,
                    'invoice_date': invoice_date,
                    'due_date': due_date.isoformat(),
                    'total_amount': total_amount,
                    'paid_amount': paid_amount,
                    'outstanding_amount': outstanding,
                    'days_overdue': days_overdue,
                    'status': status
                }
                
                # Categorize by age
                if days_overdue <= 0:
                    bucket = 'current'
                elif days_overdue <= 30:
                    bucket = '1-30_days'
                elif days_overdue <= 60:
                    bucket = '31-60_days'
                elif days_overdue <= 90:
                    bucket = '61-90_days'
                else:
                    bucket = '90+_days'
                
                aging_buckets[bucket].append(invoice_data)
                totals[bucket] += outstanding
            
            total_outstanding = sum(totals.values())
            
            conn.close()
            
            return {
                'success': True,
                'aging_report': aging_buckets,
                'totals': totals,
                'total_outstanding': total_outstanding,
                'report_date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating aging report: {e}")
            return {
                'success': False,
                'error': f"Aging report error: {str(e)}"
            }

# Global instance
payment_tracking_system = PartialPaymentTrackingSystem()