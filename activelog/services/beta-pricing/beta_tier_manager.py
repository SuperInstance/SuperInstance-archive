"""
Beta Tier Management System
Manage free beta tiers with limits and usage tracking
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TierLimits:
    api_calls_per_month: int
    storage_gb: int
    features: List[str]
    concurrent_sessions: int
    support_level: str

class BetaTierManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        
        # Default tier configurations
        self.tier_configs = {
            "free": TierLimits(
                api_calls_per_month=1000,
                storage_gb=1,
                features=["basic_search", "file_upload", "basic_analytics"],
                concurrent_sessions=1,
                support_level="community"
            ),
            "early_adopter": TierLimits(
                api_calls_per_month=5000,
                storage_gb=10,
                features=["basic_search", "file_upload", "basic_analytics", "advanced_search", "batch_processing"],
                concurrent_sessions=3,
                support_level="email"
            ),
            "beta_plus": TierLimits(
                api_calls_per_month=15000,
                storage_gb=50,
                features=["all_features"],
                concurrent_sessions=5,
                support_level="priority_email"
            ),
            "premium_beta": TierLimits(
                api_calls_per_month=-1,  # Unlimited
                storage_gb=500,
                features=["all_features", "white_label", "api_access"],
                concurrent_sessions=10,
                support_level="phone_support"
            )
        }
    
    async def create_default_tiers(self) -> Dict[str, Any]:
        """Create default pricing tiers"""
        
        tiers_created = []
        
        for tier_name, limits in self.tier_configs.items():
            tier_data = {
                "id": f"TIER_{tier_name.upper()}",
                "name": tier_name.replace('_', ' ').title(),
                "tier": tier_name,
                "base_price": self._get_base_price(tier_name),
                "beta_price": self._get_beta_price(tier_name),
                "discount_percentage": self._get_discount_percentage(tier_name),
                "api_calls_limit": limits.api_calls_per_month,
                "storage_limit_gb": limits.storage_gb,
                "support_level": limits.support_level,
                "features_included": limits.features,
                "ccc_earning_rate": self._get_ccc_earning_rate(tier_name),
                "referral_bonus": self._get_referral_bonus(tier_name),
                "early_access": tier_name in ["beta_plus", "premium_beta"],
                "valid_until": datetime.now() + timedelta(days=365),  # 1 year beta period
                "created_at": datetime.now()
            }
            
            await self._store_tier(tier_data)
            tiers_created.append(tier_data)
        
        return {
            "tiers_created": len(tiers_created),
            "tiers": tiers_created
        }
    
    def _get_base_price(self, tier: str) -> Decimal:
        """Get base price for tier (what it would cost after beta)"""
        prices = {
            "free": Decimal('0'),
            "early_adopter": Decimal('29'),
            "beta_plus": Decimal('99'),
            "premium_beta": Decimal('299')
        }
        return prices.get(tier, Decimal('0'))
    
    def _get_beta_price(self, tier: str) -> Decimal:
        """Get discounted beta price"""
        base = self._get_base_price(tier)
        if tier == "free":
            return Decimal('0')
        elif tier == "early_adopter":
            return base * Decimal('0.5')  # 50% off
        elif tier == "beta_plus":
            return base * Decimal('0.3')  # 70% off
        elif tier == "premium_beta":
            return base * Decimal('0.2')  # 80% off
        return base
    
    def _get_discount_percentage(self, tier: str) -> Decimal:
        """Get discount percentage for tier"""
        base = self._get_base_price(tier)
        beta = self._get_beta_price(tier)
        if base == 0:
            return Decimal('0')
        return ((base - beta) / base * 100).quantize(Decimal('0.01'))
    
    def _get_ccc_earning_rate(self, tier: str) -> Decimal:
        """Get CCC earning rate per dollar spent"""
        rates = {
            "free": Decimal('0.1'),  # 0.1 CCC per interaction
            "early_adopter": Decimal('0.05'),  # 5% back in CCC
            "beta_plus": Decimal('0.10'),  # 10% back in CCC
            "premium_beta": Decimal('0.15')  # 15% back in CCC
        }
        return rates.get(tier, Decimal('0'))
    
    def _get_referral_bonus(self, tier: str) -> Decimal:
        """Get referral bonus amount"""
        bonuses = {
            "free": Decimal('5'),  # $5 credit
            "early_adopter": Decimal('10'),  # $10 credit
            "beta_plus": Decimal('25'),  # $25 credit
            "premium_beta": Decimal('50')  # $50 credit
        }
        return bonuses.get(tier, Decimal('0'))
    
    async def _store_tier(self, tier_data: Dict[str, Any]) -> None:
        """Store tier configuration in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO pricing_tiers 
            (id, name, tier, base_price, beta_price, discount_percentage,
             api_calls_limit, storage_limit_gb, support_level, ccc_earning_rate,
             referral_bonus, early_access, valid_until, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            tier_data["id"], tier_data["name"], tier_data["tier"],
            float(tier_data["base_price"]), float(tier_data["beta_price"]),
            float(tier_data["discount_percentage"]), tier_data["api_calls_limit"],
            tier_data["storage_limit_gb"], tier_data["support_level"],
            float(tier_data["ccc_earning_rate"]), float(tier_data["referral_bonus"]),
            tier_data["early_access"], tier_data["valid_until"].isoformat(),
            json.dumps(tier_data, default=str)
        ))
        
        conn.commit()
        conn.close()
    
    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with tier limits and usage"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user data
        cursor.execute('''
            SELECT tier, total_api_calls, monthly_api_calls, ccc_balance, 
                   referrals_made, created_at, data
            FROM beta_users 
            WHERE id = ?
        ''', (user_id,))
        
        user_result = cursor.fetchone()
        if not user_result:
            conn.close()
            raise ValueError(f"User {user_id} not found")
        
        tier, total_api_calls, monthly_api_calls, ccc_balance, referrals_made, created_at, user_data = user_result
        
        # Get tier limits
        cursor.execute('''
            SELECT api_calls_limit, storage_limit_gb, support_level, data
            FROM pricing_tiers 
            WHERE tier = ?
        ''', (tier,))
        
        tier_result = cursor.fetchone()
        conn.close()
        
        if tier_result:
            api_limit, storage_limit, support_level, tier_data = tier_result
            tier_info = json.loads(tier_data)
        else:
            # Default limits if tier not found
            api_limit = 1000
            storage_limit = 1
            support_level = "community"
            tier_info = {}
        
        # Calculate usage percentages
        api_usage_percent = (monthly_api_calls / api_limit * 100) if api_limit > 0 else 0
        
        return {
            "user_id": user_id,
            "tier": tier,
            "tier_info": tier_info,
            "usage": {
                "api_calls": {
                    "monthly": monthly_api_calls,
                    "total": total_api_calls,
                    "limit": api_limit,
                    "usage_percent": min(100, api_usage_percent),
                    "remaining": max(0, api_limit - monthly_api_calls) if api_limit > 0 else "unlimited"
                },
                "storage": {
                    "limit_gb": storage_limit,
                    "used_gb": 0,  # Would calculate actual usage
                    "usage_percent": 0
                }
            },
            "rewards": {
                "ccc_balance": float(ccc_balance),
                "referrals_made": referrals_made
            },
            "support_level": support_level,
            "member_since": created_at
        }
    
    async def check_usage_limits(self, user_id: str) -> Dict[str, Any]:
        """Check if user has exceeded usage limits"""
        
        profile = await self.get_user_profile(user_id)
        
        limits_status = {
            "user_id": user_id,
            "tier": profile["tier"],
            "limits_exceeded": [],
            "warnings": [],
            "status": "ok"
        }
        
        # Check API limit
        api_usage = profile["usage"]["api_calls"]
        if api_usage["limit"] > 0:  # Not unlimited
            if api_usage["monthly"] >= api_usage["limit"]:
                limits_status["limits_exceeded"].append("api_calls")
                limits_status["status"] = "limit_exceeded"
            elif api_usage["usage_percent"] > 80:
                limits_status["warnings"].append({
                    "type": "api_calls",
                    "message": f"API usage at {api_usage['usage_percent']:.1f}%"
                })
        
        # Check storage limit
        storage_usage = profile["usage"]["storage"]
        if storage_usage["usage_percent"] > 90:
            limits_status["warnings"].append({
                "type": "storage",
                "message": f"Storage usage at {storage_usage['usage_percent']:.1f}%"
            })
        elif storage_usage["usage_percent"] >= 100:
            limits_status["limits_exceeded"].append("storage")
            limits_status["status"] = "limit_exceeded"
        
        return limits_status
    
    async def increment_usage(self, user_id: str, usage_type: str, amount: int = 1) -> Dict[str, Any]:
        """Increment user usage counters"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if usage_type == "api_calls":
            cursor.execute('''
                UPDATE beta_users 
                SET total_api_calls = total_api_calls + ?,
                    monthly_api_calls = monthly_api_calls + ?,
                    updated_at = ?
                WHERE id = ?
            ''', (amount, amount, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        # Check if limits exceeded after increment
        limits_status = await self.check_usage_limits(user_id)
        
        return {
            "user_id": user_id,
            "usage_type": usage_type,
            "amount_added": amount,
            "limits_status": limits_status
        }
    
    async def reset_monthly_usage(self, user_id: str = None) -> Dict[str, Any]:
        """Reset monthly usage counters (run monthly)"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id:
            cursor.execute('''
                UPDATE beta_users 
                SET monthly_api_calls = 0, updated_at = ?
                WHERE id = ?
            ''', (datetime.now().isoformat(), user_id))
            affected = cursor.rowcount
        else:
            cursor.execute('''
                UPDATE beta_users 
                SET monthly_api_calls = 0, updated_at = ?
            ''', (datetime.now().isoformat(),))
            affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return {
            "reset_type": "monthly_usage",
            "users_affected": affected,
            "reset_at": datetime.now().isoformat()
        }
    
    async def get_tier_metrics(self) -> Dict[str, Any]:
        """Get metrics across all tiers"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # User distribution by tier
        cursor.execute('''
            SELECT tier, COUNT(*) as user_count,
                   AVG(monthly_api_calls) as avg_monthly_calls,
                   AVG(ccc_balance) as avg_ccc_balance,
                   SUM(referrals_made) as total_referrals
            FROM beta_users
            GROUP BY tier
        ''')
        
        tier_stats = {}
        for row in cursor.fetchall():
            tier, count, avg_calls, avg_ccc, referrals = row
            tier_stats[tier] = {
                "user_count": count,
                "avg_monthly_calls": avg_calls or 0,
                "avg_ccc_balance": avg_ccc or 0,
                "total_referrals": referrals or 0
            }
        
        # Overall stats
        cursor.execute('''
            SELECT COUNT(*) as total_users,
                   SUM(total_api_calls) as total_api_calls,
                   AVG(ccc_balance) as platform_avg_ccc
            FROM beta_users
        ''')
        
        overall = cursor.fetchone()
        conn.close()
        
        return {
            "tier_breakdown": tier_stats,
            "platform_totals": {
                "total_users": overall[0],
                "total_api_calls": overall[1] or 0,
                "avg_ccc_balance": overall[2] or 0
            },
            "generated_at": datetime.now().isoformat()
        }
    
    async def upgrade_user_tier(self, user_id: str, new_tier: str) -> Dict[str, Any]:
        """Upgrade user to a higher tier"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current tier
        cursor.execute('SELECT tier FROM beta_users WHERE id = ?', (user_id,))
        current_result = cursor.fetchone()
        
        if not current_result:
            conn.close()
            raise ValueError(f"User {user_id} not found")
        
        current_tier = current_result[0]
        
        # Update tier
        cursor.execute('''
            UPDATE beta_users 
            SET tier = ?, updated_at = ?
            WHERE id = ?
        ''', (new_tier, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        # Get new tier info
        new_profile = await self.get_user_profile(user_id)
        
        return {
            "user_id": user_id,
            "previous_tier": current_tier,
            "new_tier": new_tier,
            "upgraded_at": datetime.now().isoformat(),
            "new_limits": new_profile["usage"]
        }

# Global instance
beta_tier_manager = BetaTierManager()