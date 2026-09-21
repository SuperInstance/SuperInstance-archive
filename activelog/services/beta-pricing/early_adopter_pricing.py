"""
Early Adopter Pricing System
Manage discounted pricing for early adopters and beta users
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PricingStrategy:
    strategy_id: str
    name: str
    discount_type: str  # percentage, fixed_amount, tiered
    discount_value: Decimal
    conditions: Dict[str, Any]
    valid_from: datetime
    valid_until: datetime

class EarlyAdopterPricing:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        
        # Early adopter strategies
        self.pricing_strategies = {
            "early_bird_50": {
                "name": "Early Bird 50% Off",
                "discount_type": "percentage",
                "discount_value": Decimal('50'),
                "conditions": {
                    "signup_before": "2024-12-31",
                    "minimum_commitment": "3_months"
                }
            },
            "lifetime_deal": {
                "name": "Lifetime Deal",
                "discount_type": "fixed_price",
                "discount_value": Decimal('299'),
                "conditions": {
                    "signup_before": "2024-10-31",
                    "one_time_payment": True
                }
            },
            "referral_stack": {
                "name": "Referral Discount Stack",
                "discount_type": "tiered",
                "discount_value": Decimal('10'),  # Per referral
                "conditions": {
                    "max_discount": Decimal('75'),
                    "referral_requirement": True
                }
            },
            "beta_feedback": {
                "name": "Beta Feedback Bonus",
                "discount_type": "percentage",
                "discount_value": Decimal('25'),
                "conditions": {
                    "feedback_required": True,
                    "min_usage_days": 30
                }
            }
        }
    
    async def get_tier_for_experiment(self, experiment_group: str) -> Dict[str, Any]:
        """Get pricing tier configuration for A/B testing group"""
        
        # Different pricing strategies for experiment groups
        experiment_configs = {
            "control": {
                "tier": "free",
                "price": Decimal('0'),
                "strategy": "freemium"
            },
            "discount_25": {
                "tier": "early_adopter",
                "price": Decimal('21.75'),  # 25% off $29
                "strategy": "discount_based"
            },
            "discount_50": {
                "tier": "early_adopter", 
                "price": Decimal('14.50'),  # 50% off $29
                "strategy": "discount_based"
            },
            "value_proposition": {
                "tier": "beta_plus",
                "price": Decimal('29.70'),  # 70% off $99 (better value)
                "strategy": "value_based"
            },
            "premium_trial": {
                "tier": "premium_beta",
                "price": Decimal('59.80'),  # 80% off $299
                "strategy": "penetration"
            }
        }
        
        return experiment_configs.get(experiment_group, experiment_configs["control"])
    
    async def calculate_early_adopter_discount(self, user_id: str, base_price: Decimal, 
                                             strategy: str = "early_bird_50") -> Dict[str, Any]:
        """Calculate early adopter discount for user"""
        
        # Get user info to check eligibility
        user_info = await self._get_user_info(user_id)
        
        if not user_info:
            return {
                "eligible": False,
                "reason": "User not found"
            }
        
        strategy_config = self.pricing_strategies.get(strategy)
        if not strategy_config:
            return {
                "eligible": False,
                "reason": "Invalid pricing strategy"
            }
        
        # Check eligibility conditions
        eligibility = await self._check_eligibility(user_info, strategy_config["conditions"])
        
        if not eligibility["eligible"]:
            return eligibility
        
        # Calculate discount
        discount_amount = await self._calculate_discount(
            base_price, 
            strategy_config["discount_type"],
            strategy_config["discount_value"],
            user_info
        )
        
        final_price = max(Decimal('0'), base_price - discount_amount)
        
        return {
            "eligible": True,
            "strategy": strategy,
            "strategy_name": strategy_config["name"],
            "base_price": float(base_price),
            "discount_amount": float(discount_amount),
            "final_price": float(final_price),
            "discount_percentage": float((discount_amount / base_price * 100)) if base_price > 0 else 0,
            "conditions_met": eligibility["conditions_met"],
            "expires_at": self._get_strategy_expiry(strategy)
        }
    
    async def _get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information for discount calculation"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT email, signup_date, referrals_made, total_api_calls, 
                   has_converted, tier, data
            FROM beta_users 
            WHERE id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        email, signup_date, referrals, api_calls, converted, tier, data = result
        
        return {
            "user_id": user_id,
            "email": email,
            "signup_date": datetime.fromisoformat(signup_date),
            "referrals_made": referrals,
            "total_api_calls": api_calls,
            "has_converted": converted,
            "tier": tier,
            "usage_days": (datetime.now() - datetime.fromisoformat(signup_date)).days,
            "user_data": json.loads(data)
        }
    
    async def _check_eligibility(self, user_info: Dict[str, Any], 
                               conditions: Dict[str, Any]) -> Dict[str, Any]:
        """Check if user meets eligibility conditions"""
        
        conditions_met = []
        conditions_failed = []
        
        # Check signup deadline
        if "signup_before" in conditions:
            deadline = datetime.fromisoformat(conditions["signup_before"])
            if user_info["signup_date"] <= deadline:
                conditions_met.append("signup_deadline")
            else:
                conditions_failed.append("signup_deadline")
        
        # Check minimum usage
        if "min_usage_days" in conditions:
            min_days = conditions["min_usage_days"]
            if user_info["usage_days"] >= min_days:
                conditions_met.append("usage_requirement")
            else:
                conditions_failed.append("usage_requirement")
        
        # Check referral requirement
        if conditions.get("referral_requirement"):
            if user_info["referrals_made"] > 0:
                conditions_met.append("referral_requirement")
            else:
                conditions_failed.append("referral_requirement")
        
        # Check feedback requirement
        if conditions.get("feedback_required"):
            # In a real system, check if user has provided feedback
            # For now, assume eligible if they've been active
            if user_info["total_api_calls"] > 100:
                conditions_met.append("feedback_requirement")
            else:
                conditions_failed.append("feedback_requirement")
        
        # Check if already converted
        if user_info["has_converted"] and "one_time_payment" in conditions:
            conditions_failed.append("already_converted")
        
        return {
            "eligible": len(conditions_failed) == 0,
            "conditions_met": conditions_met,
            "conditions_failed": conditions_failed,
            "reason": f"Failed conditions: {', '.join(conditions_failed)}" if conditions_failed else None
        }
    
    async def _calculate_discount(self, base_price: Decimal, discount_type: str, 
                                discount_value: Decimal, user_info: Dict[str, Any]) -> Decimal:
        """Calculate discount amount based on type and user info"""
        
        if discount_type == "percentage":
            return base_price * (discount_value / 100)
        
        elif discount_type == "fixed_amount":
            return min(discount_value, base_price)
        
        elif discount_type == "fixed_price":
            # Set final price (discount_value is the target price)
            return max(Decimal('0'), base_price - discount_value)
        
        elif discount_type == "tiered":
            # Discount based on referrals or other tiered metric
            referrals = user_info["referrals_made"]
            max_discount_pct = Decimal('75')  # Max 75% off
            discount_per_referral = discount_value  # e.g., 10% per referral
            
            total_discount_pct = min(max_discount_pct, referrals * discount_per_referral)
            return base_price * (total_discount_pct / 100)
        
        return Decimal('0')
    
    def _get_strategy_expiry(self, strategy: str) -> str:
        """Get expiry date for pricing strategy"""
        
        expiry_dates = {
            "early_bird_50": "2024-12-31T23:59:59",
            "lifetime_deal": "2024-10-31T23:59:59",
            "referral_stack": "2025-03-31T23:59:59",
            "beta_feedback": "2024-11-30T23:59:59"
        }
        
        return expiry_dates.get(strategy, "2024-12-31T23:59:59")
    
    async def process_tier_upgrade(self, user_id: str, target_tier: str, 
                                 payment_method: Optional[str] = None) -> Dict[str, Any]:
        """Process user tier upgrade with early adopter pricing"""
        
        # Get current user info
        user_info = await self._get_user_info(user_id)
        if not user_info:
            raise ValueError(f"User {user_id} not found")
        
        # Get base price for target tier
        tier_prices = {
            "early_adopter": Decimal('29'),
            "beta_plus": Decimal('99'),
            "premium_beta": Decimal('299')
        }
        
        base_price = tier_prices.get(target_tier, Decimal('29'))
        
        # Calculate best available discount
        best_discount = None
        best_strategy = None
        
        for strategy_name in self.pricing_strategies.keys():
            discount_info = await self.calculate_early_adopter_discount(
                user_id, base_price, strategy_name
            )
            
            if discount_info["eligible"]:
                if best_discount is None or discount_info["discount_amount"] > best_discount:
                    best_discount = discount_info["discount_amount"]
                    best_strategy = discount_info
        
        if best_strategy is None:
            # No discounts available, use base price
            final_price = base_price
            discount_info = {
                "strategy": "none",
                "discount_amount": 0,
                "discount_percentage": 0
            }
        else:
            final_price = Decimal(str(best_strategy["final_price"]))
            discount_info = best_strategy
        
        # Process upgrade (in real system, handle payment here)
        upgrade_id = f"UPGRADE_{uuid.uuid4().hex[:8].upper()}"
        
        # Update user tier
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE beta_users 
            SET tier = ?, has_converted = TRUE, conversion_date = ?, updated_at = ?
            WHERE id = ?
        ''', (target_tier, datetime.now().isoformat(), datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        return {
            "upgrade_id": upgrade_id,
            "user_id": user_id,
            "previous_tier": user_info["tier"],
            "new_tier": target_tier,
            "pricing": {
                "base_price": float(base_price),
                "final_price": float(final_price),
                "discount_applied": discount_info,
                "payment_method": payment_method
            },
            "upgraded_at": datetime.now().isoformat()
        }
    
    async def generate_pricing_recommendations(self) -> Dict[str, Any]:
        """Generate AI-powered pricing recommendations based on user behavior"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get conversion rates by experiment group
        cursor.execute('''
            SELECT experiment_group, 
                   COUNT(*) as total_users,
                   SUM(CASE WHEN has_converted THEN 1 ELSE 0 END) as conversions,
                   AVG(monthly_api_calls) as avg_usage,
                   AVG(referrals_made) as avg_referrals
            FROM beta_users
            GROUP BY experiment_group
        ''')
        
        experiment_data = []
        for row in cursor.fetchall():
            group, total, conversions, usage, referrals = row
            conversion_rate = (conversions / total * 100) if total > 0 else 0
            
            experiment_data.append({
                "group": group,
                "total_users": total,
                "conversions": conversions,
                "conversion_rate": conversion_rate,
                "avg_usage": usage or 0,
                "avg_referrals": referrals or 0
            })
        
        # Get overall metrics
        cursor.execute('''
            SELECT 
                AVG(CASE WHEN has_converted THEN monthly_api_calls ELSE 0 END) as avg_converted_usage,
                AVG(CASE WHEN NOT has_converted THEN monthly_api_calls ELSE 0 END) as avg_free_usage,
                COUNT(CASE WHEN tier = 'free' AND monthly_api_calls > 800 THEN 1 END) as high_usage_free_users
            FROM beta_users
        ''')
        
        metrics = cursor.fetchone()
        conn.close()
        
        # Generate recommendations
        recommendations = []
        
        # Find best performing experiment
        if experiment_data:
            best_experiment = max(experiment_data, key=lambda x: x["conversion_rate"])
            recommendations.append({
                "type": "experiment_winner",
                "recommendation": f"Scale {best_experiment['group']} strategy",
                "reason": f"Highest conversion rate at {best_experiment['conversion_rate']:.1f}%",
                "priority": "high"
            })
        
        # Usage-based recommendations
        if metrics and metrics[2] > 10:  # High usage free users
            recommendations.append({
                "type": "usage_limit",
                "recommendation": "Reduce free tier API limit to 500/month",
                "reason": f"{metrics[2]} free users exceeding 80% of limit",
                "priority": "medium"
            })
        
        # Pricing optimization
        recommendations.append({
            "type": "price_point",
            "recommendation": "Test $19/month entry tier",
            "reason": "Gap between free and $29 tiers too large",
            "priority": "medium"
        })
        
        # Referral program optimization
        avg_referrals = sum(exp["avg_referrals"] for exp in experiment_data) / len(experiment_data) if experiment_data else 0
        if avg_referrals < 0.5:
            recommendations.append({
                "type": "referral_program",
                "recommendation": "Increase referral bonus to $15",
                "reason": f"Low referral rate: {avg_referrals:.1f} per user",
                "priority": "low"
            })
        
        return {
            "experiment_performance": experiment_data,
            "key_metrics": {
                "avg_converted_usage": metrics[0] if metrics else 0,
                "avg_free_usage": metrics[1] if metrics else 0,
                "high_usage_free_users": metrics[2] if metrics else 0
            },
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat()
        }
    
    async def create_custom_pricing_strategy(self, strategy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create custom pricing strategy"""
        
        strategy_id = f"CUSTOM_{uuid.uuid4().hex[:8].upper()}"
        
        strategy = PricingStrategy(
            strategy_id=strategy_id,
            name=strategy_data["name"],
            discount_type=strategy_data["discount_type"],
            discount_value=Decimal(str(strategy_data["discount_value"])),
            conditions=strategy_data["conditions"],
            valid_from=datetime.fromisoformat(strategy_data["valid_from"]),
            valid_until=datetime.fromisoformat(strategy_data["valid_until"])
        )
        
        # Store strategy (in real system, would persist to database)
        self.pricing_strategies[strategy_id] = {
            "name": strategy.name,
            "discount_type": strategy.discount_type,
            "discount_value": strategy.discount_value,
            "conditions": strategy.conditions
        }
        
        return {
            "strategy_id": strategy_id,
            "name": strategy.name,
            "created_at": datetime.now().isoformat(),
            "valid_period": f"{strategy.valid_from.isoformat()} to {strategy.valid_until.isoformat()}"
        }

# Global instance
early_adopter_pricing = EarlyAdopterPricing()