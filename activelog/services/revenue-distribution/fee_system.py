"""
Tiered Fee System
1% fee on first $100k/year, 0.1% fee after $100k
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP

logger = logging.getLogger(__name__)

class FeeTier(str, Enum):
    TIER_1 = "tier_1"  # First $100k - 1%
    TIER_2 = "tier_2"  # After $100k - 0.1%

class FeeCalculationResult(BaseModel):
    user_id: str
    year: int
    transaction_amount: Decimal
    
    # Fee calculation details
    tier_1_amount: Decimal = Decimal('0')  # Amount in first $100k
    tier_2_amount: Decimal = Decimal('0')  # Amount above $100k
    
    tier_1_fee: Decimal = Decimal('0')     # Fee on first $100k (1%)
    tier_2_fee: Decimal = Decimal('0')     # Fee above $100k (0.1%)
    
    total_fee: Decimal = Decimal('0')      # Combined fees
    net_amount: Decimal = Decimal('0')     # Amount after fees
    fee_rate: Decimal = Decimal('0')       # Effective fee rate
    
    # User's annual totals
    previous_revenue_this_year: Decimal = Decimal('0')
    new_total_revenue_this_year: Decimal = Decimal('0')
    total_fees_this_year: Decimal = Decimal('0')
    
    calculation_timestamp: datetime

class AnnualFeeSummary(BaseModel):
    user_id: str
    year: int
    
    # Revenue breakdown
    total_revenue: Decimal
    tier_1_revenue: Decimal  # Revenue subject to 1% fee
    tier_2_revenue: Decimal  # Revenue subject to 0.1% fee
    
    # Fee breakdown
    total_fees_paid: Decimal
    tier_1_fees: Decimal     # Fees at 1% rate
    tier_2_fees: Decimal     # Fees at 0.1% rate
    
    # Effective rates
    overall_fee_rate: Decimal
    
    # Transaction summary
    transaction_count: int
    
    # Generated timestamp
    generated_at: datetime

class FeeCalculator:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/revenue-distribution/data/revenue_distribution.db"
        
        # Fee structure
        self.TIER_1_THRESHOLD = Decimal('100000.00')  # $100k
        self.TIER_1_RATE = Decimal('0.01')            # 1%
        self.TIER_2_RATE = Decimal('0.001')           # 0.1%
    
    async def calculate_fees(self, user_id: str, amount: Decimal, year: int) -> Dict[str, Any]:
        """Calculate fees for a transaction based on user's annual revenue"""
        
        # Get user's current year revenue
        current_year_revenue = await self._get_user_annual_revenue(user_id, year)
        
        # Calculate how much of this transaction falls into each tier
        tier_1_amount = Decimal('0')
        tier_2_amount = Decimal('0')
        
        remaining_tier_1_capacity = max(Decimal('0'), self.TIER_1_THRESHOLD - current_year_revenue)
        
        if remaining_tier_1_capacity > 0:
            # Some or all of this transaction is in tier 1 (1% fee)
            tier_1_amount = min(amount, remaining_tier_1_capacity)
            tier_2_amount = amount - tier_1_amount
        else:
            # All of this transaction is in tier 2 (0.1% fee)
            tier_2_amount = amount
        
        # Calculate fees for each tier
        tier_1_fee = tier_1_amount * self.TIER_1_RATE
        tier_2_fee = tier_2_amount * self.TIER_2_RATE
        total_fee = tier_1_fee + tier_2_fee
        
        # Calculate net amount and effective rate
        net_amount = amount - total_fee
        fee_rate = total_fee / amount if amount > 0 else Decimal('0')
        
        # Create result
        result = FeeCalculationResult(
            user_id=user_id,
            year=year,
            transaction_amount=amount,
            tier_1_amount=tier_1_amount,
            tier_2_amount=tier_2_amount,
            tier_1_fee=tier_1_fee,
            tier_2_fee=tier_2_fee,
            total_fee=total_fee,
            net_amount=net_amount,
            fee_rate=fee_rate,
            previous_revenue_this_year=current_year_revenue,
            new_total_revenue_this_year=current_year_revenue + amount,
            total_fees_this_year=await self._get_user_annual_fees(user_id, year) + total_fee,
            calculation_timestamp=datetime.now()
        )
        
        # Store the calculation
        await self._store_fee_calculation(result)
        
        return {
            "user_id": user_id,
            "transaction_amount": float(amount),
            "fee_amount": float(total_fee),
            "net_amount": float(net_amount),
            "fee_rate": float(fee_rate),
            "tier_breakdown": {
                "tier_1": {
                    "amount": float(tier_1_amount),
                    "fee": float(tier_1_fee),
                    "rate": float(self.TIER_1_RATE)
                },
                "tier_2": {
                    "amount": float(tier_2_amount), 
                    "fee": float(tier_2_fee),
                    "rate": float(self.TIER_2_RATE)
                }
            },
            "annual_summary": {
                "previous_revenue": float(current_year_revenue),
                "new_total_revenue": float(current_year_revenue + amount),
                "total_fees_this_year": float(result.total_fees_this_year)
            }
        }
    
    async def get_annual_fee_summary(self, user_id: str, year: int) -> Dict[str, Any]:
        """Get comprehensive annual fee summary for user"""
        
        total_revenue = await self._get_user_annual_revenue(user_id, year)
        total_fees = await self._get_user_annual_fees(user_id, year)
        transaction_count = await self._get_user_transaction_count(user_id, year)
        
        # Calculate tier breakdown
        tier_1_revenue = min(total_revenue, self.TIER_1_THRESHOLD)
        tier_2_revenue = max(Decimal('0'), total_revenue - self.TIER_1_THRESHOLD)
        
        tier_1_fees = tier_1_revenue * self.TIER_1_RATE
        tier_2_fees = tier_2_revenue * self.TIER_2_RATE
        
        overall_fee_rate = total_fees / total_revenue if total_revenue > 0 else Decimal('0')
        
        summary = AnnualFeeSummary(
            user_id=user_id,
            year=year,
            total_revenue=total_revenue,
            tier_1_revenue=tier_1_revenue,
            tier_2_revenue=tier_2_revenue,
            total_fees_paid=total_fees,
            tier_1_fees=tier_1_fees,
            tier_2_fees=tier_2_fees,
            overall_fee_rate=overall_fee_rate,
            transaction_count=transaction_count,
            generated_at=datetime.now()
        )
        
        return {
            "user_id": user_id,
            "year": year,
            "revenue": {
                "total": float(total_revenue),
                "tier_1": float(tier_1_revenue),
                "tier_2": float(tier_2_revenue)
            },
            "fees": {
                "total": float(total_fees),
                "tier_1": float(tier_1_fees),
                "tier_2": float(tier_2_fees)
            },
            "rates": {
                "tier_1_rate": float(self.TIER_1_RATE),
                "tier_2_rate": float(self.TIER_2_RATE),
                "effective_rate": float(overall_fee_rate)
            },
            "transactions": {
                "count": transaction_count,
                "avg_transaction_size": float(total_revenue / transaction_count) if transaction_count > 0 else 0.0
            },
            "tier_thresholds": {
                "tier_1_limit": float(self.TIER_1_THRESHOLD),
                "remaining_tier_1_capacity": float(max(Decimal('0'), self.TIER_1_THRESHOLD - total_revenue))
            },
            "generated_at": summary.generated_at.isoformat()
        }
    
    async def get_fee_projection(self, user_id: str, year: int, 
                               projected_additional_revenue: Decimal) -> Dict[str, Any]:
        """Project fees for additional revenue"""
        
        current_revenue = await self._get_user_annual_revenue(user_id, year)
        
        # Calculate fees for the projected additional amount
        fee_result = await self.calculate_fees(user_id, projected_additional_revenue, year)
        
        return {
            "user_id": user_id,
            "current_revenue": float(current_revenue),
            "projected_additional_revenue": float(projected_additional_revenue),
            "projected_total_revenue": float(current_revenue + projected_additional_revenue),
            "projected_additional_fees": float(fee_result["fee_amount"]),
            "projected_total_fees": float(fee_result["annual_summary"]["total_fees_this_year"]),
            "effective_rate_on_additional": float(fee_result["fee_rate"]),
            "tier_breakdown": fee_result["tier_breakdown"]
        }
    
    async def _get_user_annual_revenue(self, user_id: str, year: int) -> Decimal:
        """Get user's total revenue for the year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COALESCE(SUM(gross_amount), 0)
            FROM revenue_transactions
            WHERE (recipient_id = ? OR payer_id = ?)
            AND strftime('%Y', created_at) = ?
            AND status != 'failed'
        ''', (user_id, user_id, str(year)))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return Decimal(str(result))
    
    async def _get_user_annual_fees(self, user_id: str, year: int) -> Decimal:
        """Get user's total fees paid for the year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COALESCE(SUM(platform_fee), 0)
            FROM revenue_transactions
            WHERE recipient_id = ?
            AND strftime('%Y', created_at) = ?
            AND status != 'failed'
        ''', (user_id, str(year)))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return Decimal(str(result))
    
    async def _get_user_transaction_count(self, user_id: str, year: int) -> int:
        """Get user's transaction count for the year"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*)
            FROM revenue_transactions
            WHERE (recipient_id = ? OR payer_id = ?)
            AND strftime('%Y', created_at) = ?
            AND status != 'failed'
        ''', (user_id, user_id, str(year)))
        
        result = cursor.fetchone()[0]
        conn.close()
        
        return result
    
    async def _store_fee_calculation(self, result: FeeCalculationResult):
        """Store fee calculation in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fee_calculations 
            (id, user_id, year, total_revenue, fees_paid, fee_tier, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            f"FEE_{uuid.uuid4().hex[:8].upper()}",
            result.user_id,
            result.year,
            float(result.new_total_revenue_this_year),
            float(result.total_fee),
            "mixed" if result.tier_1_amount > 0 and result.tier_2_amount > 0 else (
                "tier_1" if result.tier_1_amount > 0 else "tier_2"
            ),
            result.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
    
    async def get_fee_analytics(self, year: int = None) -> Dict[str, Any]:
        """Get platform-wide fee analytics"""
        
        if year is None:
            year = datetime.now().year
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total platform fees
        cursor.execute('''
            SELECT 
                COALESCE(SUM(platform_fee), 0) as total_fees,
                COALESCE(SUM(gross_amount), 0) as total_revenue,
                COUNT(*) as transaction_count
            FROM revenue_transactions
            WHERE strftime('%Y', created_at) = ?
            AND status != 'failed'
        ''', (str(year),))
        
        totals = cursor.fetchone()
        
        # Fee tier distribution
        cursor.execute('''
            SELECT 
                fee_tier,
                COUNT(*) as calculation_count,
                SUM(fees_paid) as total_fees
            FROM fee_calculations
            WHERE year = ?
            GROUP BY fee_tier
        ''', (year,))
        
        tier_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        total_fees = Decimal(str(totals[0]))
        total_revenue = Decimal(str(totals[1]))
        transaction_count = totals[2]
        
        effective_rate = total_fees / total_revenue if total_revenue > 0 else Decimal('0')
        
        return {
            "year": year,
            "platform_totals": {
                "total_fees_collected": float(total_fees),
                "total_revenue_processed": float(total_revenue),
                "transaction_count": transaction_count,
                "effective_fee_rate": float(effective_rate)
            },
            "tier_distribution": {
                tier: {
                    "calculation_count": count,
                    "total_fees": float(fees)
                }
                for tier, (count, fees) in tier_distribution.items()
            },
            "fee_structure": {
                "tier_1": {
                    "threshold": float(self.TIER_1_THRESHOLD),
                    "rate": float(self.TIER_1_RATE)
                },
                "tier_2": {
                    "threshold_above": float(self.TIER_1_THRESHOLD),
                    "rate": float(self.TIER_2_RATE)
                }
            }
        }

# Global instance
fee_calculator = FeeCalculator()