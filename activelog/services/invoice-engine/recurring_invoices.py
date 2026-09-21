#!/usr/bin/env python3
"""
Recurring Invoices System
Automated recurring invoice generation with flexible scheduling
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
from dateutil.relativedelta import relativedelta
import calendar

logger = logging.getLogger(__name__)

class RecurringFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"

class RecurringInvoiceSystem:
    """Comprehensive recurring invoice automation system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/invoice-engine/data/invoice_engine.db"
        self.precision = Decimal('0.01')
    
    async def initialize(self):
        """Initialize recurring invoice system"""
        try:
            await self._setup_recurring_tables()
            logger.info("Recurring invoice system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize recurring invoice system: {e}")
            raise
    
    async def _setup_recurring_tables(self):
        """Setup recurring invoice tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Recurring invoice schedules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_schedules (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                template_id TEXT,
                frequency TEXT NOT NULL,
                interval_value INTEGER DEFAULT 1,
                start_date DATE NOT NULL,
                end_date DATE,
                max_occurrences INTEGER,
                current_occurrences INTEGER DEFAULT 0,
                next_invoice_date DATE,
                is_active BOOLEAN DEFAULT TRUE,
                is_paused BOOLEAN DEFAULT FALSE,
                auto_send BOOLEAN DEFAULT TRUE,
                items TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT
            )
        ''')
        
        # Generated recurring invoices tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_invoice_history (
                id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL,
                invoice_id TEXT,
                generation_date DATE NOT NULL,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                amount DECIMAL NOT NULL,
                status TEXT DEFAULT 'generated',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (schedule_id) REFERENCES recurring_schedules (id)
            )
        ''')
        
        # Recurring revenue forecasts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recurring_forecasts (
                id TEXT PRIMARY KEY,
                schedule_id TEXT NOT NULL,
                forecast_date DATE NOT NULL,
                projected_amount DECIMAL NOT NULL,
                confidence_level TEXT DEFAULT 'medium',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule_id) REFERENCES recurring_schedules (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def create_recurring_invoice(self, schedule_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create recurring invoice schedule"""
        try:
            schedule_id = f"REC_{uuid.uuid4().hex[:8].upper()}"
            
            # Validate frequency
            frequency = schedule_data['frequency'].lower()
            if frequency not in [f.value for f in RecurringFrequency]:
                return {
                    'success': False,
                    'error': f"Invalid frequency: {frequency}"
                }
            
            # Calculate next invoice date
            start_date = datetime.strptime(schedule_data['start_date'], '%Y-%m-%d').date()
            next_date = self._calculate_next_date(start_date, frequency, 
                                                schedule_data.get('interval_value', 1))
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO recurring_schedules (
                    id, customer_id, template_id, frequency, interval_value,
                    start_date, end_date, max_occurrences, next_invoice_date,
                    auto_send, items, metadata, data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                schedule_id, schedule_data['customer_id'], 
                schedule_data.get('template_id'), frequency,
                schedule_data.get('interval_value', 1), schedule_data['start_date'],
                schedule_data.get('end_date'), schedule_data.get('max_occurrences'),
                next_date.isoformat(), schedule_data.get('auto_send', True),
                json.dumps(schedule_data['items']), 
                json.dumps(schedule_data.get('metadata', {})),
                json.dumps(schedule_data)
            ))
            
            # Generate forecast
            await self._generate_forecast(cursor, schedule_id, schedule_data)
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'schedule_id': schedule_id,
                'next_invoice_date': next_date.isoformat(),
                'frequency': frequency
            }
            
        except Exception as e:
            logger.error(f"Error creating recurring invoice: {e}")
            return {
                'success': False,
                'error': f"Recurring invoice creation error: {str(e)}"
            }
    
    def _calculate_next_date(self, current_date: date, frequency: str, interval: int = 1) -> date:
        """Calculate next invoice date based on frequency"""
        if frequency == RecurringFrequency.DAILY.value:
            return current_date + timedelta(days=interval)
        elif frequency == RecurringFrequency.WEEKLY.value:
            return current_date + timedelta(weeks=interval)
        elif frequency == RecurringFrequency.MONTHLY.value:
            return current_date + relativedelta(months=interval)
        elif frequency == RecurringFrequency.QUARTERLY.value:
            return current_date + relativedelta(months=3 * interval)
        elif frequency == RecurringFrequency.YEARLY.value:
            return current_date + relativedelta(years=interval)
        else:
            return current_date + relativedelta(months=1)  # Default monthly
    
    async def process_recurring_invoices(self) -> Dict[str, Any]:
        """Process all due recurring invoices"""
        try:
            today = date.today()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get due schedules
            cursor.execute('''
                SELECT id, customer_id, template_id, frequency, interval_value,
                       next_invoice_date, items, auto_send, current_occurrences,
                       max_occurrences, end_date
                FROM recurring_schedules
                WHERE is_active = TRUE AND is_paused = FALSE 
                  AND next_invoice_date <= ?
            ''', (today.isoformat(),))
            
            processed_count = 0
            error_count = 0
            results = []
            
            for row in cursor.fetchall():
                try:
                    schedule_id = row[0]
                    customer_id = row[1]
                    template_id = row[2]
                    frequency = row[3]
                    interval_value = row[4]
                    next_date = datetime.strptime(row[5], '%Y-%m-%d').date()
                    items = json.loads(row[6])
                    auto_send = row[7]
                    current_occurrences = row[8]
                    max_occurrences = row[9]
                    end_date = row[10]
                    
                    # Check if we should continue
                    if end_date and today > datetime.strptime(end_date, '%Y-%m-%d').date():
                        await self._deactivate_schedule(cursor, schedule_id, 'end_date_reached')
                        continue
                        
                    if max_occurrences and current_occurrences >= max_occurrences:
                        await self._deactivate_schedule(cursor, schedule_id, 'max_occurrences_reached')
                        continue
                    
                    # Generate invoice
                    invoice_result = await self._generate_recurring_invoice(
                        cursor, schedule_id, customer_id, template_id, items, 
                        next_date, frequency, auto_send
                    )
                    
                    if invoice_result['success']:
                        # Update schedule
                        new_next_date = self._calculate_next_date(next_date, frequency, interval_value)
                        new_occurrences = current_occurrences + 1
                        
                        cursor.execute('''
                            UPDATE recurring_schedules 
                            SET next_invoice_date = ?, current_occurrences = ?, 
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        ''', (new_next_date.isoformat(), new_occurrences, schedule_id))
                        
                        processed_count += 1
                        
                        results.append({
                            'schedule_id': schedule_id,
                            'invoice_id': invoice_result.get('invoice_id'),
                            'status': 'success',
                            'next_date': new_next_date.isoformat()
                        })
                    else:
                        error_count += 1
                        results.append({
                            'schedule_id': schedule_id,
                            'status': 'error',
                            'error': invoice_result.get('error')
                        })
                        
                        # Log error in history
                        cursor.execute('''
                            INSERT INTO recurring_invoice_history (
                                id, schedule_id, generation_date, period_start,
                                period_end, amount, status, error_message
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            f"RECHIST_{uuid.uuid4().hex[:8].upper()}",
                            schedule_id, today.isoformat(), next_date.isoformat(),
                            next_date.isoformat(), 0, 'error', invoice_result.get('error')
                        ))
                        
                except Exception as e:
                    logger.error(f"Error processing recurring invoice {row[0]}: {e}")
                    error_count += 1
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'processed_count': processed_count,
                'error_count': error_count,
                'results': results,
                'process_date': today.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing recurring invoices: {e}")
            return {
                'success': False,
                'error': f"Processing error: {str(e)}"
            }
    
    async def _generate_recurring_invoice(
        self, cursor, schedule_id: str, customer_id: str, template_id: str,
        items: List[Dict], invoice_date: date, frequency: str, auto_send: bool
    ) -> Dict[str, Any]:
        """Generate individual recurring invoice"""
        try:
            from invoice_templates import template_system
            
            # Calculate period dates
            period_start = invoice_date
            if frequency == RecurringFrequency.MONTHLY.value:
                period_end = period_start + relativedelta(months=1) - timedelta(days=1)
            elif frequency == RecurringFrequency.QUARTERLY.value:
                period_end = period_start + relativedelta(months=3) - timedelta(days=1)
            elif frequency == RecurringFrequency.YEARLY.value:
                period_end = period_start + relativedelta(years=1) - timedelta(days=1)
            else:
                period_end = period_start
            
            # Generate invoice using template system
            invoice_data = {
                'customer_id': customer_id,
                'template_id': template_id,
                'items': items,
                'invoice_date': invoice_date.isoformat(),
                'due_date': (invoice_date + timedelta(days=30)).isoformat(),
                'metadata': {
                    'recurring_schedule_id': schedule_id,
                    'period_start': period_start.isoformat(),
                    'period_end': period_end.isoformat(),
                    'is_recurring': True
                }
            }
            
            invoice_result = await template_system.generate_invoice(invoice_data)
            
            if invoice_result['success']:
                invoice_id = invoice_result['invoice_id']
                
                # Calculate total amount
                total_amount = sum(Decimal(str(item.get('total', 0))) for item in items)
                
                # Record in history
                cursor.execute('''
                    INSERT INTO recurring_invoice_history (
                        id, schedule_id, invoice_id, generation_date,
                        period_start, period_end, amount, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    f"RECHIST_{uuid.uuid4().hex[:8].upper()}",
                    schedule_id, invoice_id, date.today().isoformat(),
                    period_start.isoformat(), period_end.isoformat(),
                    float(total_amount), 'generated'
                ))
                
                return {
                    'success': True,
                    'invoice_id': invoice_id,
                    'amount': total_amount
                }
            else:
                return invoice_result
                
        except Exception as e:
            logger.error(f"Error generating recurring invoice: {e}")
            return {
                'success': False,
                'error': f"Invoice generation error: {str(e)}"
            }
    
    async def _deactivate_schedule(self, cursor, schedule_id: str, reason: str):
        """Deactivate recurring schedule"""
        cursor.execute('''
            UPDATE recurring_schedules 
            SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP,
                metadata = json_set(COALESCE(metadata, '{}'), '$.deactivation_reason', ?)
            WHERE id = ?
        ''', (reason, schedule_id))
    
    async def _generate_forecast(self, cursor, schedule_id: str, schedule_data: Dict[str, Any]):
        """Generate revenue forecast for recurring schedule"""
        try:
            frequency = schedule_data['frequency']
            items = schedule_data['items']
            start_date = datetime.strptime(schedule_data['start_date'], '%Y-%m-%d').date()
            end_date = schedule_data.get('end_date')
            max_occurrences = schedule_data.get('max_occurrences')
            interval = schedule_data.get('interval_value', 1)
            
            # Calculate total amount per invoice
            total_amount = sum(Decimal(str(item.get('total', 0))) for item in items)
            
            # Generate forecast for next 12 months
            current_date = start_date
            forecast_end = date.today() + relativedelta(months=12)
            occurrence_count = 0
            
            while current_date <= forecast_end:
                # Check constraints
                if end_date and current_date > datetime.strptime(end_date, '%Y-%m-%d').date():
                    break
                if max_occurrences and occurrence_count >= max_occurrences:
                    break
                
                # Determine confidence level
                days_out = (current_date - date.today()).days
                if days_out <= 30:
                    confidence = 'high'
                elif days_out <= 90:
                    confidence = 'medium'
                else:
                    confidence = 'low'
                
                cursor.execute('''
                    INSERT INTO recurring_forecasts (
                        id, schedule_id, forecast_date, projected_amount, confidence_level
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    f"FORECAST_{uuid.uuid4().hex[:8].upper()}",
                    schedule_id, current_date.isoformat(),
                    float(total_amount), confidence
                ))
                
                current_date = self._calculate_next_date(current_date, frequency, interval)
                occurrence_count += 1
                
        except Exception as e:
            logger.error(f"Error generating forecast: {e}")
    
    async def pause_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Pause recurring schedule"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE recurring_schedules 
                SET is_paused = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (schedule_id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    'success': False,
                    'error': 'Schedule not found'
                }
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': 'Schedule paused successfully'
            }
            
        except Exception as e:
            logger.error(f"Error pausing schedule: {e}")
            return {
                'success': False,
                'error': f"Pause error: {str(e)}"
            }
    
    async def resume_schedule(self, schedule_id: str) -> Dict[str, Any]:
        """Resume paused recurring schedule"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE recurring_schedules 
                SET is_paused = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (schedule_id,))
            
            if cursor.rowcount == 0:
                conn.close()
                return {
                    'success': False,
                    'error': 'Schedule not found'
                }
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'message': 'Schedule resumed successfully'
            }
            
        except Exception as e:
            logger.error(f"Error resuming schedule: {e}")
            return {
                'success': False,
                'error': f"Resume error: {str(e)}"
            }
    
    async def list_recurring_invoices(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """List recurring invoice schedules"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            base_query = '''
                SELECT rs.id, rs.customer_id, rs.frequency, rs.interval_value,
                       rs.start_date, rs.end_date, rs.next_invoice_date,
                       rs.current_occurrences, rs.max_occurrences,
                       rs.is_active, rs.is_paused, rs.auto_send, rs.items
                FROM recurring_schedules rs
                WHERE 1=1
            '''
            
            params = []
            
            if filters:
                if filters.get('customer_id'):
                    base_query += " AND rs.customer_id = ?"
                    params.append(filters['customer_id'])
                
                if filters.get('is_active') is not None:
                    base_query += " AND rs.is_active = ?"
                    params.append(filters['is_active'])
                
                if filters.get('frequency'):
                    base_query += " AND rs.frequency = ?"
                    params.append(filters['frequency'])
            
            base_query += " ORDER BY rs.created_at DESC"
            
            cursor.execute(base_query, params)
            
            schedules = []
            for row in cursor.fetchall():
                items = json.loads(row[12])
                total_amount = sum(Decimal(str(item.get('total', 0))) for item in items)
                
                schedules.append({
                    'id': row[0],
                    'customer_id': row[1],
                    'frequency': row[2],
                    'interval_value': row[3],
                    'start_date': row[4],
                    'end_date': row[5],
                    'next_invoice_date': row[6],
                    'current_occurrences': row[7],
                    'max_occurrences': row[8],
                    'is_active': bool(row[9]),
                    'is_paused': bool(row[10]),
                    'auto_send': bool(row[11]),
                    'total_amount': total_amount,
                    'items_count': len(items)
                })
            
            conn.close()
            
            return {
                'success': True,
                'schedules': schedules,
                'count': len(schedules)
            }
            
        except Exception as e:
            logger.error(f"Error listing recurring invoices: {e}")
            return {
                'success': False,
                'error': f"List error: {str(e)}"
            }
    
    async def get_recurring_revenue_forecast(self, months: int = 12) -> Dict[str, Any]:
        """Get recurring revenue forecast"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            forecast_end = date.today() + relativedelta(months=months)
            
            cursor.execute('''
                SELECT 
                    strftime('%Y-%m', rf.forecast_date) as month,
                    SUM(rf.projected_amount) as total_amount,
                    COUNT(*) as invoice_count,
                    rf.confidence_level
                FROM recurring_forecasts rf
                JOIN recurring_schedules rs ON rf.schedule_id = rs.id
                WHERE rf.forecast_date BETWEEN ? AND ?
                  AND rs.is_active = TRUE
                GROUP BY strftime('%Y-%m', rf.forecast_date), rf.confidence_level
                ORDER BY month, rf.confidence_level
            ''', (date.today().isoformat(), forecast_end.isoformat()))
            
            monthly_forecasts = {}
            for row in cursor.fetchall():
                month = row[0]
                amount = Decimal(str(row[1]))
                count = row[2]
                confidence = row[3]
                
                if month not in monthly_forecasts:
                    monthly_forecasts[month] = {
                        'total_amount': Decimal('0'),
                        'invoice_count': 0,
                        'confidence_breakdown': {}
                    }
                
                monthly_forecasts[month]['total_amount'] += amount
                monthly_forecasts[month]['invoice_count'] += count
                monthly_forecasts[month]['confidence_breakdown'][confidence] = {
                    'amount': amount,
                    'count': count
                }
            
            conn.close()
            
            return {
                'success': True,
                'forecast_period_months': months,
                'monthly_forecasts': monthly_forecasts,
                'total_projected': sum(f['total_amount'] for f in monthly_forecasts.values())
            }
            
        except Exception as e:
            logger.error(f"Error getting revenue forecast: {e}")
            return {
                'success': False,
                'error': f"Forecast error: {str(e)}"
            }

# Global instance
recurring_system = RecurringInvoiceSystem()