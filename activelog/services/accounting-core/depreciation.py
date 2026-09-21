#!/usr/bin/env python3
"""
Depreciation Schedules System
Fixed asset tracking, multiple depreciation methods, and automated calculations
"""

import json
import sqlite3
import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)

class DepreciationMethod(str, Enum):
    STRAIGHT_LINE = "straight_line"
    DOUBLE_DECLINING = "double_declining"
    UNITS_OF_PRODUCTION = "units_of_production"
    SUM_OF_YEARS = "sum_of_years"
    MACRS = "macrs"

class DepreciationSystem:
    """Comprehensive fixed asset depreciation system"""
    
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db"
        self.precision = Decimal('0.01')
        
        # MACRS depreciation tables (simplified)
        self.macrs_tables = {
            3: [0.3333, 0.4445, 0.1481, 0.0741],  # 3-year
            5: [0.2000, 0.3200, 0.1920, 0.1152, 0.1152, 0.0576],  # 5-year
            7: [0.1429, 0.2449, 0.1749, 0.1249, 0.0893, 0.0892, 0.0893, 0.0446]  # 7-year
        }
    
    async def initialize(self):
        """Initialize depreciation system"""
        try:
            await self._setup_depreciation_tables()
            logger.info("Depreciation system initialized")
        except Exception as e:
            logger.error(f"Failed to initialize depreciation system: {e}")
            raise
    
    async def _setup_depreciation_tables(self):
        """Setup depreciation-related tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Depreciation schedules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS depreciation_schedules (
                id TEXT PRIMARY KEY,
                asset_id TEXT NOT NULL,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL,
                depreciation_amount DECIMAL NOT NULL,
                accumulated_depreciation DECIMAL NOT NULL,
                book_value DECIMAL NOT NULL,
                journal_entry_id TEXT,
                is_posted BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (asset_id) REFERENCES fixed_assets (id),
                FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def calculate_monthly_depreciation(self, period_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate and record monthly depreciation"""
        try:
            calculation_date = period_data.get('calculation_date', date.today().isoformat())
            calc_date = datetime.strptime(calculation_date, '%Y-%m-%d').date()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get active assets
            cursor.execute('''
                SELECT 
                    id, asset_name, purchase_date, purchase_cost, accumulated_depreciation,
                    current_book_value, salvage_value, useful_life_years, depreciation_method
                FROM fixed_assets
                WHERE is_active = TRUE AND current_book_value > salvage_value
            ''')
            
            depreciation_entries = []
            total_depreciation = Decimal('0')
            
            for row in cursor.fetchall():
                asset_id, asset_name = row[:2]
                purchase_date = datetime.strptime(row[2], '%Y-%m-%d').date()
                purchase_cost = Decimal(str(row[3]))
                accumulated_depreciation = Decimal(str(row[4]))
                current_book_value = Decimal(str(row[5]))
                salvage_value = Decimal(str(row[6]))
                useful_life_years = row[7]
                depreciation_method = row[8]
                
                # Check if depreciation needed for this month
                if current_book_value <= salvage_value:
                    continue
                
                # Calculate monthly depreciation
                monthly_depreciation = self._calculate_depreciation_amount(
                    asset_id, purchase_cost, accumulated_depreciation, 
                    salvage_value, useful_life_years, depreciation_method,
                    purchase_date, calc_date
                )
                
                if monthly_depreciation > Decimal('0'):
                    # Ensure we don't depreciate below salvage value
                    if current_book_value - monthly_depreciation < salvage_value:
                        monthly_depreciation = current_book_value - salvage_value
                    
                    # Record depreciation schedule entry
                    schedule_id = f"DEP_{uuid.uuid4().hex[:8].upper()}"
                    new_accumulated = accumulated_depreciation + monthly_depreciation
                    new_book_value = purchase_cost - new_accumulated
                    
                    cursor.execute('''
                        INSERT INTO depreciation_schedules (
                            id, asset_id, year, month, depreciation_amount,
                            accumulated_depreciation, book_value, data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        schedule_id, asset_id, calc_date.year, calc_date.month,
                        float(monthly_depreciation), float(new_accumulated),
                        float(new_book_value), json.dumps({
                            'asset_name': asset_name,
                            'calculation_date': calculation_date,
                            'method': depreciation_method
                        })
                    ))
                    
                    # Update asset
                    cursor.execute('''
                        UPDATE fixed_assets 
                        SET accumulated_depreciation = ?, current_book_value = ?, updated_at = ?
                        WHERE id = ?
                    ''', (
                        float(new_accumulated), float(new_book_value),
                        datetime.now().isoformat(), asset_id
                    ))
                    
                    depreciation_entries.append({
                        'asset_id': asset_id,
                        'asset_name': asset_name,
                        'monthly_depreciation': monthly_depreciation,
                        'accumulated_depreciation': new_accumulated,
                        'book_value': new_book_value
                    })
                    
                    total_depreciation += monthly_depreciation
            
            # Create journal entry for total depreciation
            journal_entry_id = None
            if total_depreciation > Decimal('0'):
                journal_entry_id = await self._create_depreciation_journal_entry(
                    cursor, total_depreciation, calculation_date, 'DEPRECIATION_SYSTEM'
                )
                
                if journal_entry_id:
                    # Update schedule entries with journal entry reference
                    cursor.execute(
                        "UPDATE depreciation_schedules SET journal_entry_id = ?, is_posted = TRUE WHERE created_at >= ?",
                        (journal_entry_id, datetime.now().replace(hour=0, minute=0, second=0).isoformat())
                    )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'calculation_date': calculation_date,
                'depreciation_entries': depreciation_entries,
                'total_depreciation': total_depreciation,
                'journal_entry_id': journal_entry_id,
                'assets_processed': len(depreciation_entries)
            }
            
        except Exception as e:
            logger.error(f"Error calculating depreciation: {e}")
            return {
                'success': False,
                'error': f"Depreciation calculation error: {str(e)}"
            }
    
    def _calculate_depreciation_amount(
        self, asset_id: str, purchase_cost: Decimal, accumulated_depreciation: Decimal,
        salvage_value: Decimal, useful_life_years: int, method: str,
        purchase_date: date, calculation_date: date
    ) -> Decimal:
        """Calculate depreciation amount based on method"""
        
        depreciable_cost = purchase_cost - salvage_value
        current_book_value = purchase_cost - accumulated_depreciation
        
        # Calculate months in service
        months_in_service = (calculation_date.year - purchase_date.year) * 12 + (calculation_date.month - purchase_date.month)
        total_months = useful_life_years * 12
        
        if months_in_service >= total_months:
            return Decimal('0')  # Fully depreciated
        
        if method == DepreciationMethod.STRAIGHT_LINE.value:
            # Monthly straight-line depreciation
            monthly_depreciation = depreciable_cost / Decimal(str(total_months))
            return monthly_depreciation.quantize(self.precision, rounding=ROUND_HALF_UP)
        
        elif method == DepreciationMethod.DOUBLE_DECLINING.value:
            # Double declining balance
            annual_rate = Decimal('2') / Decimal(str(useful_life_years))
            monthly_rate = annual_rate / Decimal('12')
            monthly_depreciation = current_book_value * monthly_rate
            
            # Don't go below salvage value
            if current_book_value - monthly_depreciation < salvage_value:
                monthly_depreciation = current_book_value - salvage_value
            
            return monthly_depreciation.quantize(self.precision, rounding=ROUND_HALF_UP)
        
        elif method == DepreciationMethod.SUM_OF_YEARS.value:
            # Sum of years digits (simplified monthly)
            sum_of_years = sum(range(1, useful_life_years + 1))
            current_year = min(months_in_service // 12 + 1, useful_life_years)
            remaining_years = useful_life_years - current_year + 1
            
            annual_depreciation = depreciable_cost * Decimal(str(remaining_years)) / Decimal(str(sum_of_years))
            monthly_depreciation = annual_depreciation / Decimal('12')
            
            return monthly_depreciation.quantize(self.precision, rounding=ROUND_HALF_UP)
        
        else:
            # Default to straight-line
            monthly_depreciation = depreciable_cost / Decimal(str(total_months))
            return monthly_depreciation.quantize(self.precision, rounding=ROUND_HALF_UP)
    
    async def _create_depreciation_journal_entry(
        self, cursor, total_depreciation: Decimal, calculation_date: str, created_by: str
    ) -> Optional[str]:
        """Create journal entry for depreciation"""
        try:
            from journal_entries import journal_system
            
            # Get depreciation expense account (assuming code 6500)
            cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '6500' AND is_active = TRUE")
            expense_account_row = cursor.fetchone()
            if not expense_account_row:
                return None
            expense_account_id = expense_account_row[0]
            
            # Get accumulated depreciation account (assuming code 1600)
            cursor.execute("SELECT id FROM chart_of_accounts WHERE account_code = '1600' AND is_active = TRUE")
            accum_account_row = cursor.fetchone()
            if not accum_account_row:
                return None
            accum_account_id = accum_account_row[0]
            
            journal_entry_data = {
                'id': f"JE_{uuid.uuid4().hex[:8].upper()}",
                'transaction_date': calculation_date,
                'description': f"Monthly Depreciation - {calculation_date}",
                'reference': 'MONTHLY_DEPRECIATION',
                'lines': [
                    {
                        'account_id': expense_account_id,
                        'description': 'Monthly Depreciation Expense',
                        'debit_amount': float(total_depreciation),
                        'credit_amount': 0
                    },
                    {
                        'account_id': accum_account_id,
                        'description': 'Accumulated Depreciation',
                        'debit_amount': 0,
                        'credit_amount': float(total_depreciation)
                    }
                ],
                'created_by': created_by
            }
            
            result = await journal_system.create_entry(journal_entry_data)
            if result['success']:
                # Auto-approve and post
                await journal_system.approve_entry(result['journal_entry_id'], created_by)
                await journal_system.post_entry(result['journal_entry_id'], created_by)
                return result['journal_entry_id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating depreciation journal entry: {e}")
            return None
    
    async def get_depreciation_schedule(self, asset_id: str) -> Dict[str, Any]:
        """Get depreciation schedule for asset"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get asset details
            cursor.execute('''
                SELECT 
                    asset_name, purchase_date, purchase_cost, accumulated_depreciation,
                    current_book_value, salvage_value, useful_life_years, depreciation_method
                FROM fixed_assets WHERE id = ?
            ''', (asset_id,))
            
            asset_row = cursor.fetchone()
            if not asset_row:
                return {'success': False, 'error': 'Asset not found'}
            
            asset_info = {
                'asset_name': asset_row[0],
                'purchase_date': asset_row[1],
                'purchase_cost': Decimal(str(asset_row[2])),
                'accumulated_depreciation': Decimal(str(asset_row[3])),
                'current_book_value': Decimal(str(asset_row[4])),
                'salvage_value': Decimal(str(asset_row[5])),
                'useful_life_years': asset_row[6],
                'depreciation_method': asset_row[7]
            }
            
            # Get depreciation history
            cursor.execute('''
                SELECT 
                    year, month, depreciation_amount, accumulated_depreciation, 
                    book_value, is_posted, journal_entry_id
                FROM depreciation_schedules
                WHERE asset_id = ?
                ORDER BY year, month
            ''', (asset_id,))
            
            schedule_entries = []
            for row in cursor.fetchall():
                schedule_entries.append({
                    'year': row[0],
                    'month': row[1],
                    'period': f"{row[0]}-{row[1]:02d}",
                    'depreciation_amount': Decimal(str(row[2])),
                    'accumulated_depreciation': Decimal(str(row[3])),
                    'book_value': Decimal(str(row[4])),
                    'is_posted': bool(row[5]),
                    'journal_entry_id': row[6]
                })
            
            conn.close()
            
            return {
                'success': True,
                'asset_id': asset_id,
                'asset_info': asset_info,
                'schedule_entries': schedule_entries,
                'total_entries': len(schedule_entries)
            }
            
        except Exception as e:
            logger.error(f"Error getting depreciation schedule: {e}")
            return {
                'success': False,
                'error': f"Depreciation schedule error: {str(e)}"
            }

# Global instance
depreciation_system = DepreciationSystem()