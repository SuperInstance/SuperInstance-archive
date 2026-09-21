"""
CCC Rewards System
Manage CCC token rewards for bug reports and beta participation
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import sqlite3
import json
import uuid
from enum import Enum

logger = logging.getLogger(__name__)

class RewardTrigger(str, Enum):
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    SURVEY_COMPLETION = "survey_completion"
    REFERRAL_SIGNUP = "referral_signup"
    BETA_SIGNUP = "beta_signup"
    DAILY_LOGIN = "daily_login"
    TIER_UPGRADE = "tier_upgrade"
    FEEDBACK_SUBMISSION = "feedback_submission"

class BugSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class CCCRewardsSystem:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db"
        
        # CCC reward amounts by trigger and severity
        self.reward_amounts = {
            RewardTrigger.BUG_REPORT: {
                BugSeverity.LOW: Decimal('5'),
                BugSeverity.MEDIUM: Decimal('15'),
                BugSeverity.HIGH: Decimal('50'),
                BugSeverity.CRITICAL: Decimal('200')
            },
            RewardTrigger.FEATURE_REQUEST: Decimal('10'),
            RewardTrigger.SURVEY_COMPLETION: Decimal('25'),
            RewardTrigger.REFERRAL_SIGNUP: Decimal('50'),
            RewardTrigger.BETA_SIGNUP: Decimal('100'),
            RewardTrigger.DAILY_LOGIN: Decimal('1'),
            RewardTrigger.TIER_UPGRADE: Decimal('25'),
            RewardTrigger.FEEDBACK_SUBMISSION: Decimal('10')
        }
        
        # Bonus multipliers for special conditions
        self.bonus_multipliers = {
            "first_bug_report": Decimal('2.0'),
            "multiple_bugs_day": Decimal('1.5'),
            "critical_bug_verified": Decimal('3.0'),
            "beta_champion": Decimal('2.5')  # For users with high activity
        }
    
    async def process_bug_report(self, user_id: str, severity: str, description: str, 
                               steps_to_reproduce: List[str] = None) -> Dict[str, Any]:
        """Process bug report and award CCC tokens"""
        
        bug_id = f"BUG_{uuid.uuid4().hex[:8].upper()}"
        severity_enum = BugSeverity(severity.lower())
        
        # Calculate base reward
        base_reward = self.reward_amounts[RewardTrigger.BUG_REPORT][severity_enum]
        
        # Check for bonus multipliers
        bonus_info = await self._calculate_bug_report_bonuses(user_id, severity_enum)
        final_reward = base_reward * bonus_info["multiplier"]
        
        # Store bug report
        bug_report = {
            "bug_id": bug_id,
            "user_id": user_id,
            "severity": severity,
            "description": description,
            "steps_to_reproduce": steps_to_reproduce or [],
            "status": "submitted",
            "reward_amount": float(final_reward),
            "submitted_at": datetime.now(),
            "verified": False
        }
        
        await self._store_bug_report(bug_report)
        
        # Award CCC tokens
        await self._award_ccc_tokens(
            user_id, 
            final_reward, 
            RewardTrigger.BUG_REPORT,
            f"Bug report: {bug_id}"
        )
        
        return {
            "bug_id": bug_id,
            "severity": severity,
            "base_reward": float(base_reward),
            "bonus_multiplier": float(bonus_info["multiplier"]),
            "bonuses_applied": bonus_info["bonuses"],
            "final_reward": float(final_reward),
            "total_ccc_balance": await self.get_user_balance(user_id)
        }
    
    async def _calculate_bug_report_bonuses(self, user_id: str, severity: BugSeverity) -> Dict[str, Any]:
        """Calculate bonus multipliers for bug report"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if this is user's first bug report
        cursor.execute('''
            SELECT COUNT(*) FROM ccc_rewards 
            WHERE user_id = ? AND trigger_type = ?
        ''', (user_id, RewardTrigger.BUG_REPORT.value))
        
        bug_report_count = cursor.fetchone()[0]
        
        # Check bug reports today
        today = datetime.now().date()
        cursor.execute('''
            SELECT COUNT(*) FROM ccc_rewards 
            WHERE user_id = ? AND trigger_type = ? 
            AND DATE(awarded_at) = ?
        ''', (user_id, RewardTrigger.BUG_REPORT.value, today.isoformat()))
        
        bugs_today = cursor.fetchone()[0]
        
        conn.close()
        
        multiplier = Decimal('1.0')
        bonuses = []
        
        # First bug report bonus
        if bug_report_count == 0:
            multiplier *= self.bonus_multipliers["first_bug_report"]
            bonuses.append("First Bug Report (2x)")
        
        # Multiple bugs in one day bonus
        if bugs_today > 0:
            multiplier *= self.bonus_multipliers["multiple_bugs_day"]
            bonuses.append("Multiple Reports Today (1.5x)")
        
        # Critical bug bonus
        if severity == BugSeverity.CRITICAL:
            multiplier *= self.bonus_multipliers["critical_bug_verified"]
            bonuses.append("Critical Bug (3x)")
        
        return {
            "multiplier": multiplier,
            "bonuses": bonuses
        }
    
    async def _store_bug_report(self, bug_report: Dict[str, Any]) -> None:
        """Store bug report in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create bug reports table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bug_reports (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT DEFAULT 'submitted',
                reward_amount DECIMAL NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified BOOLEAN DEFAULT FALSE,
                data TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO bug_reports 
            (id, user_id, severity, description, status, reward_amount, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            bug_report["bug_id"],
            bug_report["user_id"],
            bug_report["severity"],
            bug_report["description"],
            bug_report["status"],
            bug_report["reward_amount"],
            json.dumps(bug_report)
        ))
        
        conn.commit()
        conn.close()
    
    async def _award_ccc_tokens(self, user_id: str, amount: Decimal, 
                              trigger: RewardTrigger, description: str) -> None:
        """Award CCC tokens to user"""
        
        reward_id = f"REWARD_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create rewards table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ccc_rewards (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                trigger_type TEXT NOT NULL,
                description TEXT NOT NULL,
                awarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                redeemed BOOLEAN DEFAULT FALSE,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        # Record reward
        cursor.execute('''
            INSERT INTO ccc_rewards 
            (id, user_id, amount, trigger_type, description, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            reward_id, user_id, float(amount), trigger.value, description,
            json.dumps({"reward_id": reward_id, "trigger": trigger.value})
        ))
        
        # Update user balance
        cursor.execute('''
            UPDATE beta_users 
            SET ccc_balance = ccc_balance + ?, updated_at = ?
            WHERE id = ?
        ''', (float(amount), datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Awarded {amount} CCC to user {user_id} for {trigger.value}")
    
    async def grant_signup_bonus(self, user_id: str) -> Dict[str, Any]:
        """Grant signup bonus to new beta user"""
        
        bonus_amount = self.reward_amounts[RewardTrigger.BETA_SIGNUP]
        
        await self._award_ccc_tokens(
            user_id,
            bonus_amount,
            RewardTrigger.BETA_SIGNUP,
            "Welcome to beta! Thank you for joining."
        )
        
        return {
            "user_id": user_id,
            "bonus_type": "signup",
            "amount": float(bonus_amount),
            "message": "Welcome bonus awarded!"
        }
    
    async def get_signup_bonus_amount(self) -> Decimal:
        """Get signup bonus amount"""
        return self.reward_amounts[RewardTrigger.BETA_SIGNUP]
    
    async def grant_survey_completion_reward(self, user_id: str, survey_id: str = None) -> Dict[str, Any]:
        """Grant reward for completing survey"""
        
        reward_amount = self.reward_amounts[RewardTrigger.SURVEY_COMPLETION]
        
        await self._award_ccc_tokens(
            user_id,
            reward_amount,
            RewardTrigger.SURVEY_COMPLETION,
            f"Survey completion reward - {survey_id or 'General Survey'}"
        )
        
        return {
            "user_id": user_id,
            "reward_type": "survey_completion",
            "amount": float(reward_amount),
            "survey_id": survey_id
        }
    
    async def grant_referral_reward(self, user_id: str, referred_user_id: str) -> Dict[str, Any]:
        """Grant reward for successful referral"""
        
        reward_amount = self.reward_amounts[RewardTrigger.REFERRAL_SIGNUP]
        
        await self._award_ccc_tokens(
            user_id,
            reward_amount,
            RewardTrigger.REFERRAL_SIGNUP,
            f"Referral reward - User {referred_user_id} joined"
        )
        
        return {
            "user_id": user_id,
            "reward_type": "referral",
            "amount": float(reward_amount),
            "referred_user": referred_user_id
        }
    
    async def get_user_balance(self, user_id: str) -> float:
        """Get user's current CCC balance"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT ccc_balance FROM beta_users WHERE id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        return float(result[0]) if result else 0.0
    
    async def get_user_reward_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get user's CCC reward history"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, amount, trigger_type, description, awarded_at, redeemed
            FROM ccc_rewards 
            WHERE user_id = ?
            ORDER BY awarded_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rewards = []
        total_earned = Decimal('0')
        
        for row in cursor.fetchall():
            reward_id, amount, trigger, desc, awarded_at, redeemed = row
            reward_amount = Decimal(str(amount))
            
            rewards.append({
                "reward_id": reward_id,
                "amount": float(reward_amount),
                "trigger": trigger,
                "description": desc,
                "awarded_at": awarded_at,
                "redeemed": bool(redeemed)
            })
            
            total_earned += reward_amount
        
        conn.close()
        
        current_balance = await self.get_user_balance(user_id)
        
        return {
            "user_id": user_id,
            "current_balance": current_balance,
            "total_earned": float(total_earned),
            "reward_count": len(rewards),
            "rewards": rewards
        }
    
    async def redeem_rewards(self, user_id: str, reward_type: str, amount: float) -> Dict[str, Any]:
        """Redeem CCC rewards for benefits"""
        
        current_balance = await self.get_user_balance(user_id)
        
        if current_balance < amount:
            return {
                "success": False,
                "error": "Insufficient CCC balance",
                "current_balance": current_balance,
                "requested_amount": amount
            }
        
        # Process redemption based on type
        redemption_benefits = await self._process_redemption(user_id, reward_type, amount)
        
        # Deduct CCC from balance
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE beta_users 
            SET ccc_balance = ccc_balance - ?, updated_at = ?
            WHERE id = ?
        ''', (amount, datetime.now().isoformat(), user_id))
        
        conn.commit()
        conn.close()
        
        # Record redemption
        await self._record_redemption(user_id, reward_type, amount, redemption_benefits)
        
        return {
            "success": True,
            "user_id": user_id,
            "redemption_type": reward_type,
            "amount_redeemed": amount,
            "benefits": redemption_benefits,
            "new_balance": current_balance - amount
        }
    
    async def _process_redemption(self, user_id: str, reward_type: str, amount: float) -> Dict[str, Any]:
        """Process CCC redemption for specific benefit type"""
        
        redemption_rates = {
            "account_credits": 0.01,  # 1 CCC = $0.01 credit
            "tier_upgrade_discount": 0.02,  # 1 CCC = $0.02 off upgrade
            "api_calls_boost": 10,  # 1 CCC = 10 extra API calls
            "storage_boost": 0.1  # 1 CCC = 0.1 GB extra storage
        }
        
        rate = redemption_rates.get(reward_type, 0.01)
        
        if reward_type == "account_credits":
            credit_value = amount * rate
            return {
                "type": "account_credits",
                "credit_amount": credit_value,
                "description": f"${credit_value:.2f} account credit"
            }
        
        elif reward_type == "tier_upgrade_discount":
            discount_value = amount * rate
            return {
                "type": "tier_upgrade_discount",
                "discount_amount": discount_value,
                "description": f"${discount_value:.2f} off next tier upgrade"
            }
        
        elif reward_type == "api_calls_boost":
            extra_calls = int(amount * rate)
            # Would actually add to user's API limit here
            return {
                "type": "api_calls_boost",
                "extra_calls": extra_calls,
                "description": f"{extra_calls} additional API calls this month"
            }
        
        elif reward_type == "storage_boost":
            extra_storage = amount * rate
            return {
                "type": "storage_boost",
                "extra_storage_gb": extra_storage,
                "description": f"{extra_storage:.1f} GB additional storage"
            }
        
        return {"type": "unknown", "description": "Redemption processed"}
    
    async def _record_redemption(self, user_id: str, reward_type: str, 
                               amount: float, benefits: Dict[str, Any]) -> None:
        """Record CCC redemption in database"""
        
        redemption_id = f"REDEMPTION_{uuid.uuid4().hex[:8].upper()}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create redemptions table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ccc_redemptions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                redemption_type TEXT NOT NULL,
                amount_redeemed DECIMAL NOT NULL,
                benefits_received TEXT NOT NULL,
                redeemed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY (user_id) REFERENCES beta_users (id)
            )
        ''')
        
        cursor.execute('''
            INSERT INTO ccc_redemptions 
            (id, user_id, redemption_type, amount_redeemed, benefits_received, data)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            redemption_id, user_id, reward_type, amount,
            json.dumps(benefits), json.dumps({
                "redemption_id": redemption_id,
                "processed_at": datetime.now().isoformat()
            })
        ))
        
        conn.commit()
        conn.close()
    
    async def get_platform_ccc_stats(self) -> Dict[str, Any]:
        """Get platform-wide CCC statistics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total CCC distributed
        cursor.execute('SELECT SUM(amount) FROM ccc_rewards')
        total_distributed = cursor.fetchone()[0] or 0
        
        # Total CCC redeemed
        cursor.execute('SELECT SUM(amount_redeemed) FROM ccc_redemptions')
        total_redeemed = cursor.fetchone()[0] or 0
        
        # Rewards by trigger type
        cursor.execute('''
            SELECT trigger_type, COUNT(*) as count, SUM(amount) as total
            FROM ccc_rewards
            GROUP BY trigger_type
        ''')
        
        rewards_by_trigger = {}
        for row in cursor.fetchall():
            trigger, count, total = row
            rewards_by_trigger[trigger] = {
                "count": count,
                "total_amount": total or 0
            }
        
        # Top earners
        cursor.execute('''
            SELECT user_id, ccc_balance
            FROM beta_users
            ORDER BY ccc_balance DESC
            LIMIT 10
        ''')
        
        top_earners = []
        for row in cursor.fetchall():
            user_id, balance = row
            top_earners.append({
                "user_id": user_id,
                "balance": balance or 0
            })
        
        conn.close()
        
        return {
            "total_ccc_distributed": total_distributed,
            "total_ccc_redeemed": total_redeemed,
            "active_ccc_in_circulation": total_distributed - total_redeemed,
            "rewards_by_trigger": rewards_by_trigger,
            "top_earners": top_earners,
            "generated_at": datetime.now().isoformat()
        }

# Global instance
ccc_rewards_system = CCCRewardsSystem()