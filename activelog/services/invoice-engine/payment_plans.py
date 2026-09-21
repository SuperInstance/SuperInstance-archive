#!/usr/bin/env python3
"""
Payment Plans System
Flexible payment plan creation and installment management
"""

import json
import sqlite3
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class PlanStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"
    CANCELLED = "cancelled"

class InstallmentStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    PARTIAL = "partial"

class PaymentPlanSystem:
    """Payment plan management system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize payment plan system"""
        try:
            await self._setup_plan_tables()
            logger.info("Payment plan system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize payment plan system: {e}")
            raise
    
    async def _setup_plan_tables(self):
        """Setup payment plan tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_plans (
                id TEXT PRIMARY KEY,
                plan_name TEXT NOT NULL,
                invoice_id TEXT NOT NULL,
                customer_id TEXT NOT NULL,
                total_amount DECIMAL NOT NULL,
                down_payment DECIMAL DEFAULT 0,
                remaining_amount DECIMAL NOT NULL,
                number_of_installments INTEGER NOT NULL,
                installment_amount DECIMAL NOT NULL,
                frequency TEXT NOT NULL,
                start_date DATE NOT NULL,
                status TEXT DEFAULT 'active',
                auto_charge BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plan_installments (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                installment_number INTEGER NOT NULL,
                due_date DATE NOT NULL,
                amount DECIMAL NOT NULL,
                paid_amount DECIMAL DEFAULT 0,
                remaining_amount DECIMAL NOT NULL,
                status TEXT DEFAULT 'pending',
                paid_date DATE,
                late_fee DECIMAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES payment_plans (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plan_payments (
                id TEXT PRIMARY KEY,
                plan_id TEXT NOT NULL,
                installment_id TEXT NOT NULL,
                payment_amount DECIMAL NOT NULL,
                payment_date DATE NOT NULL,
                payment_method TEXT,
                transaction_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plan_id) REFERENCES payment_plans (id),
                FOREIGN KEY (installment_id) REFERENCES plan_installments (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_payment_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create payment plan"""
        try:
            plan_id = f"PLAN_{uuid.uuid4().hex[:8].upper()}"
            
            total_amount = Decimal(str(plan_data['total_amount']))
            down_payment = Decimal(str(plan_data.get('down_payment', 0)))
            remaining_amount = total_amount - down_payment
            number_of_installments = int(plan_data['number_of_installments'])
            
            # Calculate installment amount
            installment_amount = (remaining_amount / number_of_installments).quantize(
                self.precision, rounding=ROUND_HALF_UP
            )
            
            # Adjust last installment to handle rounding
            total_installments = installment_amount * (number_of_installments - 1)
            last_installment = remaining_amount - total_installments
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create payment plan
            cursor.execute('''
                INSERT INTO payment_plans (
                    id, plan_name, invoice_id, customer_id, total_amount,
                    down_payment, remaining_amount, number_of_installments,
                    installment_amount, frequency, start_date, auto_charge, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                plan_id, plan_data.get('plan_name', f'Plan for {plan_data["invoice_id"]}'),
                plan_data['invoice_id'], plan_data['customer_id'],
                float(total_amount), float(down_payment), float(remaining_amount),
                number_of_installments, float(installment_amount),
                plan_data.get('frequency', 'monthly'), 
                plan_data.get('start_date', date.today().isoformat()),
                plan_data.get('auto_charge', False), json.dumps(plan_data)
            ))
            
            # Generate installments
            start_date = datetime.strptime(plan_data.get('start_date', date.today().isoformat()), '%Y-%m-%d').date()
            frequency = plan_data.get('frequency', 'monthly')
            
            for i in range(number_of_installments):
                installment_id = f"INST_{uuid.uuid4().hex[:8].upper()}"
                due_date = self._calculate_due_date(start_date, i, frequency)
                
                # Use calculated installment amount for all except last
                amount = installment_amount if i < number_of_installments - 1 else last_installment
                
                cursor.execute('''
                    INSERT INTO plan_installments (
                        id, plan_id, installment_number, due_date, amount, remaining_amount
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (installment_id, plan_id, i + 1, due_date.isoformat(), 
                      float(amount), float(amount)))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'plan_id': plan_id,
                'total_amount': total_amount,
                'down_payment': down_payment,
                'installment_amount': installment_amount,
                'number_of_installments': number_of_installments
            }
            
        except Exception as e:
            logger.error(f"Error creating payment plan: {e}")
            return {
                'success': False,
                'error': f"Payment plan creation error: {str(e)}"
            }
    
    def _calculate_due_date(self, start_date: date, installment_index: int, frequency: str) -> date:
        """Calculate due date for installment"""
        if frequency == 'weekly':
            return start_date + timedelta(weeks=installment_index + 1)
        elif frequency == 'bi-weekly':
            return start_date + timedelta(weeks=(installment_index + 1) * 2)
        elif frequency == 'monthly':
            months = installment_index + 1
            year = start_date.year + (start_date.month + months - 1) // 12
            month = (start_date.month + months - 1) % 12 + 1
            day = min(start_date.day, [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1])
            return date(year, month, day)
        elif frequency == 'quarterly':
            return start_date + timedelta(days=(installment_index + 1) * 90)
        else:  # default to monthly
            return start_date + timedelta(days=(installment_index + 1) * 30)
    
    async def process_installment_payment(self, installment_id: str, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process payment for installment"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get installment details
            cursor.execute('''
                SELECT plan_id, amount, paid_amount, remaining_amount, status
                FROM plan_installments WHERE id = ?
            ''', (installment_id,))
            
            installment_row = cursor.fetchone()
            if not installment_row:
                conn.close()
                return {'success': False, 'error': 'Installment not found'}
            
            plan_id, amount, paid_amount, remaining_amount, status = installment_row
            payment_amount = Decimal(str(payment_data['payment_amount']))
            
            if payment_amount > Decimal(str(remaining_amount)):
                conn.close()
                return {'success': False, 'error': 'Payment amount exceeds remaining balance'}
            
            # Record payment
            payment_id = f"PAY_{uuid.uuid4().hex[:8].upper()}"
            cursor.execute('''
                INSERT INTO plan_payments (
                    id, plan_id, installment_id, payment_amount, payment_date,
                    payment_method, transaction_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_id, plan_id, installment_id, float(payment_amount),
                payment_data.get('payment_date', date.today().isoformat()),
                payment_data.get('payment_method'), payment_data.get('transaction_id')
            ))
            
            # Update installment
            new_paid = Decimal(str(paid_amount)) + payment_amount
            new_remaining = Decimal(str(amount)) - new_paid
            new_status = 'paid' if new_remaining <= Decimal('0.01') else 'partial'
            
            cursor.execute('''
                UPDATE plan_installments 
                SET paid_amount = ?, remaining_amount = ?, status = ?,
                    paid_date = CASE WHEN ? = 'paid' THEN ? ELSE paid_date END
                WHERE id = ?
            ''', (
                float(new_paid), float(new_remaining), new_status,
                new_status, date.today().isoformat() if new_status == 'paid' else None,
                installment_id
            ))
            
            # Check if plan is complete
            cursor.execute('''
                SELECT COUNT(*) FROM plan_installments
                WHERE plan_id = ? AND status != 'paid'
            ''', (plan_id,))
            
            remaining_installments = cursor.fetchone()[0]
            if remaining_installments == 0:
                cursor.execute('''
                    UPDATE payment_plans SET status = 'completed' WHERE id = ?
                ''', (plan_id,))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'payment_id': payment_id,
                'installment_id': installment_id,
                'payment_amount': payment_amount,
                'remaining_amount': new_remaining,
                'installment_status': new_status
            }
            
        except Exception as e:
            logger.error(f"Error processing installment payment: {e}")
            return {'success': False, 'error': f"Payment processing error: {str(e)}"}
    
    async def get_payment_plan(self, plan_id: str) -> Dict[str, Any]:
        """Get payment plan details"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get plan details
            cursor.execute('''
                SELECT plan_name, invoice_id, customer_id, total_amount,
                       down_payment, remaining_amount, number_of_installments,
                       installment_amount, frequency, start_date, status
                FROM payment_plans WHERE id = ?
            ''', (plan_id,))
            
            plan_row = cursor.fetchone()
            if not plan_row:
                conn.close()
                return {'success': False, 'error': 'Payment plan not found'}
            
            # Get installments
            cursor.execute('''
                SELECT id, installment_number, due_date, amount, paid_amount,
                       remaining_amount, status, paid_date, late_fee
                FROM plan_installments WHERE plan_id = ?
                ORDER BY installment_number
            ''', (plan_id,))
            
            installments = []
            for row in cursor.fetchall():
                installments.append({
                    'id': row[0], 'installment_number': row[1], 'due_date': row[2],
                    'amount': Decimal(str(row[3])), 'paid_amount': Decimal(str(row[4])),
                    'remaining_amount': Decimal(str(row[5])), 'status': row[6],
                    'paid_date': row[7], 'late_fee': Decimal(str(row[8]))
                })
            
            conn.close()
            
            return {
                'success': True,
                'plan_id': plan_id,
                'plan_name': plan_row[0],
                'invoice_id': plan_row[1],
                'customer_id': plan_row[2],
                'total_amount': Decimal(str(plan_row[3])),
                'down_payment': Decimal(str(plan_row[4])),
                'remaining_amount': Decimal(str(plan_row[5])),
                'number_of_installments': plan_row[6],
                'installment_amount': Decimal(str(plan_row[7])),
                'frequency': plan_row[8],
                'start_date': plan_row[9],
                'status': plan_row[10],
                'installments': installments
            }
            
        except Exception as e:
            logger.error(f"Error getting payment plan: {e}")
            return {'success': False, 'error': f"Plan retrieval error: {str(e)}"}
    
    async def list_overdue_installments(self, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """List overdue installments"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT pi.id, pi.plan_id, pp.customer_id, pp.plan_name,
                       pi.installment_number, pi.due_date, pi.remaining_amount,
                       pi.late_fee
                FROM plan_installments pi
                JOIN payment_plans pp ON pi.plan_id = pp.id
                WHERE pi.status IN ('pending', 'partial') AND pi.due_date < ?
            '''
            
            params = [date.today().isoformat()]
            
            if customer_id:
                base_query += " AND pp.customer_id = ?"
                params.append(customer_id)
            
            base_query += " ORDER BY pi.due_date ASC"
            cursor.execute(base_query, params)
            
            overdue_installments = []
            for row in cursor.fetchall():
                days_overdue = (date.today() - datetime.strptime(row[5], '%Y-%m-%d').date()).days
                
                overdue_installments.append({
                    'installment_id': row[0],
                    'plan_id': row[1],
                    'customer_id': row[2],
                    'plan_name': row[3],
                    'installment_number': row[4],
                    'due_date': row[5],
                    'remaining_amount': Decimal(str(row[6])),
                    'late_fee': Decimal(str(row[7])),
                    'days_overdue': days_overdue
                })
            
            conn.close()
            
            return {
                'success': True,
                'overdue_installments': overdue_installments,
                'count': len(overdue_installments)
            }
            
        except Exception as e:
            logger.error(f"Error listing overdue installments: {e}")
            return {'success': False, 'error': f"Overdue list error: {str(e)}"}

# Global instance
payment_plan_system = PaymentPlanSystem()