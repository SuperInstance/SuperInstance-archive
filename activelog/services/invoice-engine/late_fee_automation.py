#!/usr/bin/env python3
"""
Late Fee Automation System
Automatic late fee calculation and application for overdue invoices
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

class LateFeeType(str, Enum):
    FIXED = "fixed"
    PERCENTAGE = "percentage"
    TIERED = "tiered"
    COMPOUND = "compound"

class LateFeeAutomationSystem:
    """Automated late fee calculation and application system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
        
        # Default late fee configurations
        self.default_configs = {
            'grace_period_days': 3,
            'fee_type': LateFeeType.PERCENTAGE.value,
            'fee_amount': Decimal('1.5'),  # 1.5% per month
            'max_fee_percentage': Decimal('25'),  # Maximum 25% of original amount
            'compound_frequency': 'monthly'
        }
    
    async def initialize(self):
        """Initialize late fee system"""
        try:
            await self._setup_late_fee_tables()
            logger.info("Late fee automation system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize late fee system: {e}")
            raise
    
    async def _setup_late_fee_tables(self):
        """Setup late fee related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Late fee configurations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS late_fee_configs (
                id TEXT PRIMARY KEY,
                customer_id TEXT,
                fee_type TEXT NOT NULL,
                fee_amount DECIMAL NOT NULL,
                grace_period_days INTEGER DEFAULT 0,
                max_fee_percentage DECIMAL,
                compound_frequency TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Applied late fees table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS late_fees (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                fee_config_id TEXT,
                application_date DATE NOT NULL,
                days_overdue INTEGER NOT NULL,
                original_amount DECIMAL NOT NULL,
                fee_amount DECIMAL NOT NULL,
                fee_type TEXT NOT NULL,
                calculation_details TEXT,
                is_reversed BOOLEAN DEFAULT FALSE,
                reversed_date DATE,
                reversed_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Late fee history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS late_fee_history (
                id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                action_type TEXT NOT NULL,
                fee_amount DECIMAL NOT NULL,
                action_date DATE NOT NULL,
                action_by TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def apply_late_fees(self) -> Dict[str, Any]:
        """Apply late fees to all eligible overdue invoices"""
        try:
            today = date.today()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get overdue invoices eligible for late fees
            cursor.execute('''
                SELECT i.id, i.invoice_number, i.customer_id, i.due_date,
                       i.total_amount, i.paid_amount, i.status
                FROM invoices i
                WHERE i.status IN ('sent', 'overdue')
                  AND i.due_date < ?
                  AND (i.total_amount - COALESCE(i.paid_amount, 0)) > 0.01
            ''', (today.isoformat(),))
            
            overdue_invoices = cursor.fetchall()
            applied_fees = []
            
            for invoice_row in overdue_invoices:
                invoice_id = invoice_row[0]
                invoice_number = invoice_row[1]
                customer_id = invoice_row[2]
                due_date = datetime.strptime(invoice_row[3], '%Y-%m-%d').date()
                total_amount = Decimal(str(invoice_row[4]))
                paid_amount = Decimal(str(invoice_row[5] or 0))
                
                days_overdue = (today - due_date).days
                outstanding_amount = total_amount - paid_amount
                
                # Get late fee configuration for customer
                fee_config = await self._get_fee_config(cursor, customer_id)
                
                # Check grace period
                if days_overdue <= fee_config['grace_period_days']:
                    continue
                
                # Check if late fee already applied recently
                if await self._is_fee_recently_applied(cursor, invoice_id, today):
                    continue
                
                # Calculate late fee
                fee_result = await self._calculate_late_fee(
                    cursor, invoice_id, outstanding_amount, days_overdue, fee_config
                )
                
                if fee_result['fee_amount'] > 0:
                    # Apply late fee
                    late_fee_id = await self._apply_late_fee(
                        cursor, invoice_id, fee_result, fee_config, days_overdue
                    )
                    
                    if late_fee_id:
                        applied_fees.append({
                            'invoice_id': invoice_id,
                            'invoice_number': invoice_number,
                            'late_fee_id': late_fee_id,
                            'fee_amount': fee_result['fee_amount'],
                            'days_overdue': days_overdue,
                            'outstanding_amount': outstanding_amount
                        })
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'fees_applied': len(applied_fees),
                'late_fees': applied_fees,
                'application_date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error applying late fees: {e}")
            return {
                'success': False,
                'error': f"Late fee application error: {str(e)}"
            }
    
    async def _get_fee_config(self, cursor, customer_id: str) -> Dict[str, Any]:
        """Get late fee configuration for customer"""
        cursor.execute('''
            SELECT fee_type, fee_amount, grace_period_days, max_fee_percentage,
                   compound_frequency, data
            FROM late_fee_configs
            WHERE customer_id = ? AND is_active = TRUE
            ORDER BY created_at DESC
            LIMIT 1
        ''', (customer_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                'fee_type': row[0],
                'fee_amount': Decimal(str(row[1])),
                'grace_period_days': row[2] or 0,
                'max_fee_percentage': Decimal(str(row[3] or 25)),
                'compound_frequency': row[4] or 'monthly',
                'data': json.loads(row[5] or '{}')
            }
        else:
            # Use default configuration
            return self.default_configs.copy()
    
    async def _is_fee_recently_applied(self, cursor, invoice_id: str, today: date) -> bool:
        """Check if late fee was applied recently"""
        cursor.execute('''
            SELECT id FROM late_fees
            WHERE invoice_id = ? AND application_date >= ?
              AND is_reversed = FALSE
        ''', (invoice_id, (today - timedelta(days=30)).isoformat()))
        
        return cursor.fetchone() is not None
    
    async def _calculate_late_fee(
        self, cursor, invoice_id: str, outstanding_amount: Decimal,
        days_overdue: int, fee_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate late fee amount"""
        try:
            fee_type = fee_config['fee_type']
            fee_amount = fee_config['fee_amount']
            max_fee_percentage = fee_config['max_fee_percentage']
            
            calculated_fee = Decimal('0')
            calculation_details = {}
            
            if fee_type == LateFeeType.FIXED.value:
                # Fixed amount fee
                calculated_fee = fee_amount
                calculation_details = {
                    'type': 'fixed',
                    'fixed_amount': float(fee_amount)
                }
                
            elif fee_type == LateFeeType.PERCENTAGE.value:
                # Percentage of outstanding amount
                calculated_fee = (outstanding_amount * fee_amount / Decimal('100')).quantize(
                    self.precision, rounding=ROUND_HALF_UP
                )
                calculation_details = {
                    'type': 'percentage',
                    'percentage': float(fee_amount),
                    'base_amount': float(outstanding_amount)
                }
                
            elif fee_type == LateFeeType.TIERED.value:
                # Tiered fee based on days overdue
                calculated_fee = self._calculate_tiered_fee(days_overdue, outstanding_amount, fee_config)
                calculation_details = {
                    'type': 'tiered',
                    'days_overdue': days_overdue,
                    'base_amount': float(outstanding_amount)
                }
                
            elif fee_type == LateFeeType.COMPOUND.value:
                # Compound fee over time
                calculated_fee = self._calculate_compound_fee(
                    cursor, invoice_id, outstanding_amount, days_overdue, fee_config
                )
                calculation_details = {
                    'type': 'compound',
                    'days_overdue': days_overdue,
                    'base_amount': float(outstanding_amount),
                    'frequency': fee_config['compound_frequency']
                }
            
            # Apply maximum fee limit
            max_fee = outstanding_amount * max_fee_percentage / Decimal('100')
            if calculated_fee > max_fee:
                calculated_fee = max_fee
                calculation_details['capped_at_max'] = True
                calculation_details['max_fee_percentage'] = float(max_fee_percentage)
            
            return {
                'fee_amount': calculated_fee,
                'calculation_details': calculation_details
            }
            
        except Exception as e:
            logger.error(f"Error calculating late fee: {e}")
            return {
                'fee_amount': Decimal('0'),
                'calculation_details': {'error': str(e)}
            }
    
    def _calculate_tiered_fee(self, days_overdue: int, outstanding_amount: Decimal, fee_config: Dict[str, Any]) -> Decimal:
        """Calculate tiered late fee"""
        # Default tiered structure
        tiers = [
            {'days': 30, 'percentage': Decimal('1.0')},   # 1% for 1-30 days
            {'days': 60, 'percentage': Decimal('2.0')},   # 2% for 31-60 days
            {'days': 90, 'percentage': Decimal('3.0')},   # 3% for 61-90 days
            {'days': float('inf'), 'percentage': Decimal('5.0')}  # 5% for 90+ days
        ]
        
        for tier in tiers:
            if days_overdue <= tier['days']:
                return (outstanding_amount * tier['percentage'] / Decimal('100')).quantize(
                    self.precision, rounding=ROUND_HALF_UP
                )
        
        return Decimal('0')
    
    def _calculate_compound_fee(
        self, cursor, invoice_id: str, outstanding_amount: Decimal,
        days_overdue: int, fee_config: Dict[str, Any]
    ) -> Decimal:
        """Calculate compound late fee"""
        frequency = fee_config['compound_frequency']
        monthly_rate = fee_config['fee_amount'] / Decimal('100')  # Convert percentage to decimal
        
        if frequency == 'daily':
            daily_rate = monthly_rate / Decimal('30')
            periods = days_overdue
            rate_per_period = daily_rate
        elif frequency == 'weekly':
            weekly_rate = monthly_rate / Decimal('4')
            periods = days_overdue // 7
            rate_per_period = weekly_rate
        else:  # monthly (default)
            periods = days_overdue // 30
            rate_per_period = monthly_rate
        
        if periods <= 0:
            return Decimal('0')
        
        # Simple compound interest calculation: A = P(1 + r)^n - P
        compound_amount = outstanding_amount * ((Decimal('1') + rate_per_period) ** periods)
        fee_amount = compound_amount - outstanding_amount
        
        return fee_amount.quantize(self.precision, rounding=ROUND_HALF_UP)
    
    async def _apply_late_fee(
        self, cursor, invoice_id: str, fee_result: Dict[str, Any],
        fee_config: Dict[str, Any], days_overdue: int
    ) -> Optional[str]:
        """Apply calculated late fee to invoice"""
        try:
            late_fee_id = f"FEE_{uuid.uuid4().hex[:8].upper()}"
            fee_amount = fee_result['fee_amount']
            
            # Get original invoice amount
            cursor.execute('SELECT total_amount FROM invoices WHERE id = ?', (invoice_id,))
            invoice_row = cursor.fetchone()
            if not invoice_row:
                return None
            
            original_amount = Decimal(str(invoice_row[0]))
            
            # Insert late fee record
            cursor.execute('''
                INSERT INTO late_fees (
                    id, invoice_id, application_date, days_overdue,
                    original_amount, fee_amount, fee_type, calculation_details, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                late_fee_id, invoice_id, date.today().isoformat(), days_overdue,
                float(original_amount), float(fee_amount), fee_config['fee_type'],
                json.dumps(fee_result['calculation_details']),
                json.dumps({
                    'config_used': fee_config,
                    'application_timestamp': datetime.now().isoformat()
                })
            ))
            
            # Update invoice total (add late fee to outstanding amount)
            cursor.execute('''
                UPDATE invoices 
                SET total_amount = total_amount + ?, 
                    status = 'overdue',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (float(fee_amount), invoice_id))
            
            # Record in history
            cursor.execute('''
                INSERT INTO late_fee_history (
                    id, invoice_id, action_type, fee_amount, action_date, details
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                f"HIST_{uuid.uuid4().hex[:8].upper()}",
                invoice_id, 'applied', float(fee_amount), date.today().isoformat(),
                f"Late fee applied: {fee_config['fee_type']} - {days_overdue} days overdue"
            ))
            
            return late_fee_id
            
        except Exception as e:
            logger.error(f"Error applying late fee: {e}")
            return None
    
    async def reverse_late_fee(self, late_fee_id: str, reason: str, reversed_by: str = 'USER') -> Dict[str, Any]:
        """Reverse a previously applied late fee"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get late fee details
            cursor.execute('''
                SELECT invoice_id, fee_amount, is_reversed
                FROM late_fees WHERE id = ?
            ''', (late_fee_id,))
            
            fee_row = cursor.fetchone()
            if not fee_row:
                conn.close()
                return {
                    'success': False,
                    'error': 'Late fee not found'
                }
            
            invoice_id, fee_amount, is_reversed = fee_row
            
            if is_reversed:
                conn.close()
                return {
                    'success': False,
                    'error': 'Late fee already reversed'
                }
            
            # Mark fee as reversed
            cursor.execute('''
                UPDATE late_fees 
                SET is_reversed = TRUE, reversed_date = ?, reversed_reason = ?
                WHERE id = ?
            ''', (date.today().isoformat(), reason, late_fee_id))
            
            # Reduce invoice total
            cursor.execute('''
                UPDATE invoices 
                SET total_amount = total_amount - ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (fee_amount, invoice_id))
            
            # Record in history
            cursor.execute('''
                INSERT INTO late_fee_history (
                    id, invoice_id, action_type, fee_amount, action_date,
                    action_by, details
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f"HIST_{uuid.uuid4().hex[:8].upper()}",
                invoice_id, 'reversed', fee_amount, date.today().isoformat(),
                reversed_by, f"Late fee reversed: {reason}"
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'late_fee_id': late_fee_id,
                'invoice_id': invoice_id,
                'reversed_amount': Decimal(str(fee_amount)),
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"Error reversing late fee: {e}")
            return {
                'success': False,
                'error': f"Reversal error: {str(e)}"
            }
    
    async def configure_customer_fees(self, customer_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure late fee settings for specific customer"""
        try:
            config_id = f"CFG_{uuid.uuid4().hex[:8].upper()}"
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Deactivate existing configurations
            cursor.execute('''
                UPDATE late_fee_configs 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            ''', (customer_id,))
            
            # Insert new configuration
            cursor.execute('''
                INSERT INTO late_fee_configs (
                    id, customer_id, fee_type, fee_amount, grace_period_days,
                    max_fee_percentage, compound_frequency, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                config_id, customer_id, config_data['fee_type'],
                float(Decimal(str(config_data['fee_amount']))),
                config_data.get('grace_period_days', 0),
                float(Decimal(str(config_data.get('max_fee_percentage', 25)))),
                config_data.get('compound_frequency', 'monthly'),
                json.dumps(config_data)
            ))
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'config_id': config_id,
                'customer_id': customer_id,
                'fee_type': config_data['fee_type']
            }
            
        except Exception as e:
            logger.error(f"Error configuring customer fees: {e}")
            return {
                'success': False,
                'error': f"Configuration error: {str(e)}"
            }
    
    async def list_late_fees(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List applied late fees with filtering"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT lf.id, lf.invoice_id, lf.application_date, lf.days_overdue,
                       lf.original_amount, lf.fee_amount, lf.fee_type,
                       lf.is_reversed, lf.reversed_date, lf.reversed_reason
                FROM late_fees lf
                WHERE 1=1
            '''
            
            params = []
            
            if filters:
                if filters.get('invoice_id'):
                    base_query += " AND lf.invoice_id = ?"
                    params.append(filters['invoice_id'])
                
                if filters.get('is_reversed') is not None:
                    base_query += " AND lf.is_reversed = ?"
                    params.append(filters['is_reversed'])
                
                if filters.get('date_from'):
                    base_query += " AND lf.application_date >= ?"
                    params.append(filters['date_from'])
                
                if filters.get('date_to'):
                    base_query += " AND lf.application_date <= ?"
                    params.append(filters['date_to'])
            
            base_query += " ORDER BY lf.application_date DESC"
            
            cursor.execute(base_query, params)
            
            late_fees = []
            for row in cursor.fetchall():
                late_fees.append({
                    'id': row[0],
                    'invoice_id': row[1],
                    'application_date': row[2],
                    'days_overdue': row[3],
                    'original_amount': Decimal(str(row[4])),
                    'fee_amount': Decimal(str(row[5])),
                    'fee_type': row[6],
                    'is_reversed': bool(row[7]),
                    'reversed_date': row[8],
                    'reversed_reason': row[9]
                })
            
            conn.close()
            
            return {
                'success': True,
                'late_fees': late_fees,
                'count': len(late_fees)
            }
            
        except Exception as e:
            logger.error(f"Error listing late fees: {e}")
            return {
                'success': False,
                'error': f"List error: {str(e)}"
            }

# Global instance
late_fee_system = LateFeeAutomationSystem()