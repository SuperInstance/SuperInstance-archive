"""
Referral Bonus System
Manage referral bonuses and tracking for beta users
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
import hashlib

logger = logging.getLogger(__name__)

class ReferralBonusSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        
        # Referral bonus structure
        self.bonus_structure = {
            "signup_bonus": {
                "referrer": Decimal('50'),  # CCC tokens
                "referee": Decimal('25')    # CCC tokens
            },
            "tier_upgrade_bonus": {
                "referrer_percentage": Decimal('20'),  # % of upgrade price
                "min_bonus": Decimal('5'),
                "max_bonus": Decimal('100')
            },
            "milestone_bonuses": {
                5: Decimal('100'),   # 5 referrals
                10: Decimal('250'),  # 10 referrals
                25: Decimal('500'),  # 25 referrals
                50: Decimal('1000'), # 50 referrals
                100: Decimal('2500') # 100 referrals
            }
        }
        
        # Referral tiers with increasing benefits
        self.referral_tiers = {
            "bronze": {"min_referrals": 1, "bonus_multiplier": Decimal('1.0')},
            "silver": {"min_referrals": 5, "bonus_multiplier": Decimal('1.2')},
            "gold": {"min_referrals": 15, "bonus_multiplier": Decimal('1.5')},
            "platinum": {"min_referrals": 30, "bonus_multiplier": Decimal('1.8')},
            "diamond": {"min_referrals": 50, "bonus_multiplier": Decimal('2.0')}
        }
    
    async def process_referral(self, referral_code: str, new_user_id: str) -> Dict[str, Any]:
        """Process referral when new user signs up"""
        
        # Find referrer by code
        referrer_info = await self.get_referrer_by_code(referral_code)
        if not referrer_info:
            return {
                "success": False,
                "error": "Invalid referral code"
            }
        
        referrer_id = referrer_info["user_id"]
        
        # Check for self-referral
        if referrer_id == new_user_id:
            return {
                "success": False,
                "error": "Cannot refer yourself"
            }
        
        # Check if user already referred by someone else
        existing_referrer = await self._get_user_referrer(new_user_id)
        if existing_referrer:
            return {
                "success": False,
                "error": "User already has a referrer"
            }
        
        # Process bonuses
        referrer_bonus = await self._award_referral_bonus(referrer_id, new_user_id, "signup")
        referee_bonus = await self._award_referee_bonus(new_user_id, referrer_id)
        
        # Update referral counts
        await self._increment_referral_count(referrer_id)
        
        # Check milestone bonuses
        milestone_bonus = await self._check_milestone_bonus(referrer_id)
        
        # Record referral relationship
        await self._record_referral(referrer_id, new_user_id, referral_code)
        
        return {
            "success": True,
            "referrer_id": referrer_id,
            "referee_id": new_user_id,
            "referrer_bonus": referrer_bonus,
            "referee_bonus": referee_bonus,
            "milestone_bonus": milestone_bonus,
            "processed_at": datetime.now().isoformat()
        }
    
    async def get_referrer_by_code(self, referral_code: str) -> Optional[Dict[str, Any]]:
        """Get referrer information by referral code"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, email, tier, referrals_made
            FROM beta_users 
            WHERE referral_code = ?
        ''', (referral_code,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        user_id, name, email, tier, referrals = result
        
        return {
            "user_id": user_id,
            "name": name,
            "email": email,
            "tier": tier,
            "referrals_made": referrals
        }
    
    async def _get_user_referrer(self, user_id: str) -> Optional[str]:
        """Check if user already has a referrer"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT referred_by FROM beta_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result and result[0] else None
    
    async def _award_referral_bonus(self, referrer_id: str, referee_id: str, 
                                  bonus_type: str) -> Dict[str, Any]:
        """Award bonus to referrer"""
        
        if bonus_type == "signup":
            base_bonus = self.bonus_structure["signup_bonus"]["referrer"]
        else:
            base_bonus = Decimal('0')
        
        # Get referrer tier for bonus multiplier
        referrer_tier = await self._get_user_referral_tier(referrer_id)
        multiplier = self.referral_tiers[referrer_tier]["bonus_multiplier"]
        
        final_bonus = base_bonus * multiplier
        
        # Award bonus (integrate with CCC rewards system)
        from ccc_rewards import ccc_rewards_system
        await ccc_rewards_system.grant_referral_reward(referrer_id, referee_id)
        
        return {
            "base_bonus": float(base_bonus),
            "multiplier": float(multiplier),
            "tier": referrer_tier,
            "final_bonus": float(final_bonus),
            "bonus_type": bonus_type
        }
    
    async def _award_referee_bonus(self, referee_id: str, referrer_id: str) -> Dict[str, Any]:
        """Award welcome bonus to referee"""
        
        bonus_amount = self.bonus_structure["signup_bonus"]["referee"]
        
        # Award bonus
        from ccc_rewards import ccc_rewards_system
        await ccc_rewards_system._award_ccc_tokens(
            referee_id,
            bonus_amount,
            ccc_rewards_system.RewardTrigger.REFERRAL_SIGNUP,
            f"Referral welcome bonus from {referrer_id}"
        )
        
        return {
            "amount": float(bonus_amount),
            "type": "welcome_bonus"
        }
    
    async def _increment_referral_count(self, referrer_id: str) -> None:
        """Increment referrer's referral count"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE beta_users 
            SET referrals_made = referrals_made + 1, updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), referrer_id))
        
        conn.commit()
        conn.close()
    
    async def _check_milestone_bonus(self, referrer_id: str) -> Optional[Dict[str, Any]]:
        """Check if referrer reached a milestone for bonus"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT referrals_made FROM beta_users WHERE id = ?', (referrer_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        referral_count = result[0]
        
        # Check if current count is a milestone
        if referral_count in self.bonus_structure["milestone_bonuses"]:
            milestone_bonus = self.bonus_structure["milestone_bonuses"][referral_count]
            
            # Award milestone bonus
            from ccc_rewards import ccc_rewards_system
            await ccc_rewards_system._award_ccc_tokens(
                referrer_id,
                milestone_bonus,
                ccc_rewards_system.RewardTrigger.REFERRAL_SIGNUP,
                f"Milestone bonus: {referral_count} referrals"
            )
            
            return {
                "milestone": referral_count,
                "bonus_amount": float(milestone_bonus),
                "message": f"Congratulations on {referral_count} referrals!"
            }
        
        return None
    
    async def _record_referral(self, referrer_id: str, referee_id: str, referral_code: str) -> None:
        """Record referral relationship in database"""
        
        referral_id = f"REF_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create referrals table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_id TEXT NOT NULL,
                referee_id TEXT NOT NULL,
                referral_code TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (referrer_id) REFERENCES beta_users (id),
                FOREIGN KEY (referee_id) REFERENCES beta_users (id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO referrals 
            (id, referrer_id, referee_id, referral_code, data)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            referral_id, referrer_id, referee_id, referral_code,
            json.dumps({
                "referral_id": referral_id,
                "processed_at": datetime.now().isoformat()
            })
        ))
        
        conn.commit()
        conn.close()
    
    async def _get_user_referral_tier(self, user_id: str) -> str:
        """Get user's referral tier based on referral count"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT referrals_made FROM beta_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        referral_count = result[0] if result else 0
        
        # Determine tier
        for tier in reversed(list(self.referral_tiers.keys())):
            if referral_count >= self.referral_tiers[tier]["min_referrals"]:
                return tier
        
        return "bronze"
    
    async def get_referral_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive referral statistics for user"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get user referral info
        cursor.execute('''
            SELECT referrals_made, referral_code, ccc_balance
            FROM beta_users 
            WHERE id = ?
        ''', (user_id,))
        
        user_result = cursor.fetchone()
        if not user_result:
            return {"error": "User not found"}
        
        referrals_made, referral_code, ccc_balance = user_result
        
        # Get referred users
        cursor.execute('''
            SELECT r.referee_id, u.name, u.email, u.tier, u.signup_date, r.created_at
            FROM referrals r
            JOIN beta_users u ON r.referee_id = u.id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        ''', (user_id,))
        
        referred_users = []
        for row in cursor.fetchall():
            referee_id, name, email, tier, signup_date, referral_date = row
            referred_users.append({
                "user_id": referee_id,
                "name": name,
                "email": email,
                "tier": tier,
                "signup_date": signup_date,
                "referral_date": referral_date
            })
        
        # Calculate total bonuses earned from referrals
        cursor.execute('''
            SELECT SUM(amount) 
            FROM ccc_rewards 
            WHERE user_id = ? AND trigger_type = ?
        ''', (user_id, "referral_signup"))
        
        total_bonuses = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # Get current tier
        current_tier = await self._get_user_referral_tier(user_id)
        tier_info = self.referral_tiers[current_tier]
        
        # Next milestone
        next_milestone = None
        next_milestone_bonus = None
        for milestone, bonus in self.bonus_structure["milestone_bonuses"].items():
            if milestone > referrals_made:
                next_milestone = milestone
                next_milestone_bonus = float(bonus)
                break
        
        return {
            "user_id": user_id,
            "referral_code": referral_code,
            "referrals_made": referrals_made,
            "current_tier": current_tier,
            "tier_multiplier": float(tier_info["bonus_multiplier"]),
            "total_bonuses_earned": total_bonuses,
            "current_ccc_balance": ccc_balance,
            "referred_users": referred_users,
            "next_milestone": {
                "referrals_needed": next_milestone,
                "bonus_amount": next_milestone_bonus,
                "progress": referrals_made
            } if next_milestone else None,
            "sharing_links": await self._generate_sharing_links(referral_code)
        }
    
    async def _generate_sharing_links(self, referral_code: str) -> Dict[str, str]:
        """Generate sharing links for different platforms"""
        
        base_url = "https://activelog.com/signup"
        referral_url = f"{base_url}?ref={referral_code}"
        
        # Social media sharing URLs
        twitter_text = "Check out ActiveLog - amazing productivity platform! Join with my referral link:"
        facebook_text = "I'm loving ActiveLog for productivity tracking. Join me!"
        
        return {
            "direct_link": referral_url,
            "twitter": f"https://twitter.com/intent/tweet?text={twitter_text}&url={referral_url}",
            "facebook": f"https://www.facebook.com/sharer/sharer.php?u={referral_url}",
            "linkedin": f"https://www.linkedin.com/sharing/share-offsite/?url={referral_url}",
            "email_subject": "Join ActiveLog with my referral",
            "email_body": f"Hi! I've been using ActiveLog and think you'd love it too. Join with my referral link: {referral_url}"
        }
    
    async def validate_referral_code(self, referral_code: str) -> Dict[str, Any]:
        """Validate if referral code exists and is active"""
        
        referrer_info = await self.get_referrer_by_code(referral_code)
        
        if not referrer_info:
            return {
                "valid": False,
                "error": "Referral code not found"
            }
        
        # Additional validation rules
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if referrer account is active
        cursor.execute('''
            SELECT tier, signup_date 
            FROM beta_users 
            WHERE id = ?
        ''', (referrer_info["user_id"],))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return {
                "valid": False,
                "error": "Referrer account not found"
            }
        
        tier, signup_date = result
        account_age = (datetime.now() - datetime.fromisoformat(signup_date)).days
        
        # Referrer must be active for at least 7 days
        if account_age < 7:
            return {
                "valid": False,
                "error": "Referrer account too new"
            }
        
        return {
            "valid": True,
            "referrer_name": referrer_info["name"],
            "referrer_tier": tier,
            "bonus_info": {
                "signup_bonus": float(self.bonus_structure["signup_bonus"]["referee"]),
                "currency": "CCC tokens"
            }
        }
    
    async def get_platform_referral_stats(self) -> Dict[str, Any]:
        """Get platform-wide referral statistics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total referrals
        cursor.execute('SELECT COUNT(*) FROM referrals')
        total_referrals = cursor.fetchone()[0]
        
        # Users with referrals
        cursor.execute('SELECT COUNT(*) FROM beta_users WHERE referrals_made > 0')
        active_referrers = cursor.fetchone()[0]
        
        # Top referrers
        cursor.execute('''
            SELECT id, name, referrals_made
            FROM beta_users
            WHERE referrals_made > 0
            ORDER BY referrals_made DESC
            LIMIT 10
        ''')
        
        top_referrers = []
        for row in cursor.fetchall():
            user_id, name, referrals = row
            tier = await self._get_user_referral_tier(user_id)
            top_referrers.append({
                "user_id": user_id,
                "name": name,
                "referrals": referrals,
                "tier": tier
            })
        
        # Referral conversion rate
        cursor.execute('SELECT COUNT(*) FROM beta_users')
        total_users = cursor.fetchone()[0]
        conversion_rate = (total_referrals / total_users * 100) if total_users > 0 else 0
        
        conn.close()
        
        return {
            "total_referrals": total_referrals,
            "active_referrers": active_referrers,
            "referral_conversion_rate": conversion_rate,
            "average_referrals_per_user": total_referrals / total_users if total_users > 0 else 0,
            "top_referrers": top_referrers,
            "generated_at": datetime.now().isoformat()
        }

# Global instance
referral_bonus_system = ReferralBonusSystem()