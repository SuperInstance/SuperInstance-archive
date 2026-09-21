import asyncio
import asyncpg
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import json
import uuid


class TransactionType(Enum):
    EARN = "earn"
    SPEND = "spend"
    GIFT = "gift"
    BONUS = "bonus"
    PENALTY = "penalty"
    ALLOWANCE = "allowance"


class EarnReason(Enum):
    PROJECT_COMPLETED = "project_completed"
    LESSON_FINISHED = "lesson_finished"
    ACHIEVEMENT_UNLOCKED = "achievement_unlocked"
    DAILY_GOAL_MET = "daily_goal_met"
    HELPING_OTHERS = "helping_others"
    CREATIVE_WORK = "creative_work"
    PROBLEM_SOLVING = "problem_solving"
    CONSISTENT_LEARNING = "consistent_learning"
    BONUS_CHALLENGE = "bonus_challenge"


class SpendCategory(Enum):
    CUSTOMIZATION = "customization"
    TOOLS_UPGRADES = "tools_upgrades"
    PROJECT_RESOURCES = "project_resources"
    AVATAR_ITEMS = "avatar_items"
    SPECIAL_FEATURES = "special_features"
    GIFTS_FOR_FRIENDS = "gifts_for_friends"
    POWER_UPS = "power_ups"


@dataclass
class Currency:
    name: str
    symbol: str
    description: str
    age_min: int
    age_max: int
    exchange_rate: float = 1.0  # Rate to base currency


@dataclass
class VirtualItem:
    item_id: str
    name: str
    description: str
    category: SpendCategory
    price: int
    age_min: int
    age_max: int
    is_available: bool
    preview_image: Optional[str] = None
    unlock_requirements: Optional[Dict] = None


@dataclass
class Transaction:
    transaction_id: str
    user_id: str
    amount: int
    currency_type: str
    transaction_type: TransactionType
    category: str
    description: str
    metadata: Dict
    created_at: datetime
    parent_approved: bool = True


class VirtualCurrencySystem:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.currencies = self._initialize_currencies()
        self.earning_rates = self._initialize_earning_rates()
        self.spending_limits = self._initialize_spending_limits()
        
    async def initialize_tables(self):
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_balances (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    currency_type VARCHAR(20) NOT NULL,
                    balance INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    last_allowance TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, currency_type)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS currency_transactions (
                    id SERIAL PRIMARY KEY,
                    transaction_id VARCHAR(50) UNIQUE NOT NULL,
                    user_id VARCHAR(50) NOT NULL,
                    amount INTEGER NOT NULL,
                    currency_type VARCHAR(20) NOT NULL,
                    transaction_type VARCHAR(20) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    parent_approved BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS virtual_store_items (
                    id SERIAL PRIMARY KEY,
                    item_id VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    category VARCHAR(50) NOT NULL,
                    price INTEGER NOT NULL,
                    currency_type VARCHAR(20) DEFAULT 'coins',
                    age_min INTEGER NOT NULL,
                    age_max INTEGER NOT NULL,
                    is_available BOOLEAN DEFAULT TRUE,
                    preview_image TEXT,
                    unlock_requirements JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_purchases (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    item_id VARCHAR(50) NOT NULL,
                    transaction_id VARCHAR(50) NOT NULL,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_id)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS earning_multipliers (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(50) NOT NULL,
                    multiplier_type VARCHAR(50) NOT NULL,
                    multiplier_value FLOAT NOT NULL,
                    expires_at TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def _initialize_currencies(self) -> Dict[str, Currency]:
        """Initialize different types of virtual currencies by age group"""
        return {
            "stars": Currency(
                name="Learning Stars",
                symbol="⭐",
                description="Earn stars for completing lessons and projects",
                age_min=5,
                age_max=10,
                exchange_rate=1.0
            ),
            "coins": Currency(
                name="Maker Coins", 
                symbol="🪙",
                description="The main currency for buying tools and customizations",
                age_min=8,
                age_max=16,
                exchange_rate=1.0
            ),
            "gems": Currency(
                name="Achievement Gems",
                symbol="💎", 
                description="Rare gems earned through special achievements",
                age_min=10,
                age_max=18,
                exchange_rate=5.0
            ),
            "tickets": Currency(
                name="Fun Tickets",
                symbol="🎫",
                description="Special tickets for games and activities",
                age_min=5,
                age_max=12,
                exchange_rate=0.5
            )
        }

    def _initialize_earning_rates(self) -> Dict:
        """Initialize how much currency users earn for different activities"""
        return {
            EarnReason.PROJECT_COMPLETED: {
                "base_amount": 10,
                "age_multipliers": {
                    (5, 8): 1.2,    # Extra encouragement for young kids
                    (9, 12): 1.0,   # Standard rate
                    (13, 18): 0.8   # Slightly less as projects get more complex
                }
            },
            EarnReason.LESSON_FINISHED: {
                "base_amount": 5,
                "age_multipliers": {
                    (5, 8): 1.5,
                    (9, 12): 1.0,
                    (13, 18): 0.7
                }
            },
            EarnReason.ACHIEVEMENT_UNLOCKED: {
                "base_amount": 15,
                "age_multipliers": {
                    (5, 8): 1.3,
                    (9, 12): 1.0,
                    (13, 18): 0.9
                }
            },
            EarnReason.DAILY_GOAL_MET: {
                "base_amount": 8,
                "age_multipliers": {
                    (5, 8): 1.4,
                    (9, 12): 1.0,
                    (13, 18): 0.8
                }
            },
            EarnReason.HELPING_OTHERS: {
                "base_amount": 12,
                "age_multipliers": {
                    (5, 8): 1.2,
                    (9, 12): 1.0,
                    (13, 18): 1.0
                }
            }
        }

    def _initialize_spending_limits(self) -> Dict:
        """Initialize daily/weekly spending limits by age"""
        return {
            (5, 8): {"daily": 20, "weekly": 100},
            (9, 12): {"daily": 30, "weekly": 150}, 
            (13, 16): {"daily": 50, "weekly": 250},
            (17, 18): {"daily": 75, "weekly": 400}
        }

    async def get_user_balance(self, user_id: str, currency_type: str = "coins") -> Dict:
        """Get user's current balance and earning statistics"""
        async with self.db_pool.acquire() as conn:
            balance_data = await conn.fetchrow("""
                SELECT * FROM user_balances
                WHERE user_id = $1 AND currency_type = $2
            """, user_id, currency_type)
            
            if not balance_data:
                # Create initial balance
                await conn.execute("""
                    INSERT INTO user_balances (user_id, currency_type, balance)
                    VALUES ($1, $2, 0)
                """, user_id, currency_type)
                balance_data = {"balance": 0, "total_earned": 0, "total_spent": 0}
            
            # Get recent transactions
            recent_transactions = await conn.fetch("""
                SELECT * FROM currency_transactions
                WHERE user_id = $1 AND currency_type = $2
                ORDER BY created_at DESC
                LIMIT 10
            """, user_id, currency_type)
        
        currency_info = self.currencies.get(currency_type, self.currencies["coins"])
        
        return {
            "balance": balance_data["balance"],
            "currency": {
                "type": currency_type,
                "name": currency_info.name,
                "symbol": currency_info.symbol,
                "description": currency_info.description
            },
            "statistics": {
                "total_earned": balance_data["total_earned"],
                "total_spent": balance_data["total_spent"],
                "net_earnings": balance_data["total_earned"] - balance_data["total_spent"]
            },
            "recent_transactions": [
                {
                    "amount": tx["amount"],
                    "type": tx["transaction_type"],
                    "description": tx["description"],
                    "date": tx["created_at"].isoformat()
                } for tx in recent_transactions
            ],
            "earning_potential": await self.get_daily_earning_potential(user_id)
        }

    async def award_currency(self, user_id: str, reason: EarnReason, 
                           metadata: Dict = None, currency_type: str = "coins") -> Dict:
        """Award currency to user for completing activities"""
        user_age = await self.get_user_age(user_id)
        
        # Check if earning is valid
        can_earn, limitation_reason = await self.can_earn_currency(user_id, reason)
        if not can_earn:
            return {
                "success": False,
                "reason": limitation_reason,
                "suggested_action": "Try again later or complete different activities"
            }
        
        # Calculate amount to award
        amount = self.calculate_earning_amount(reason, user_age, metadata or {})
        
        # Apply any active multipliers
        final_amount = await self.apply_earning_multipliers(user_id, amount)
        
        # Create transaction
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=user_id,
            amount=final_amount,
            currency_type=currency_type,
            transaction_type=TransactionType.EARN,
            category=reason.value,
            description=self.get_earning_description(reason, final_amount),
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        # Process transaction
        success = await self.process_transaction(transaction)
        
        if success:
            # Check for bonus opportunities
            bonus_info = await self.check_bonus_opportunities(user_id, reason)
            
            return {
                "success": True,
                "amount_earned": final_amount,
                "currency_type": currency_type,
                "new_balance": await self.get_balance_amount(user_id, currency_type),
                "description": transaction.description,
                "bonus_opportunities": bonus_info,
                "achievement_progress": await self.get_achievement_progress(user_id),
                "celebration_message": self.generate_celebration_message(reason, final_amount)
            }
        else:
            return {
                "success": False,
                "reason": "Failed to process transaction",
                "suggested_action": "Please try again"
            }

    async def spend_currency(self, user_id: str, item_id: str, 
                           currency_type: str = "coins") -> Dict:
        """Process currency spending for virtual items"""
        user_age = await self.get_user_age(user_id)
        
        # Get item details
        item = await self.get_store_item(item_id)
        if not item:
            return {"success": False, "reason": "Item not found"}
        
        # Check age appropriateness
        if not (item["age_min"] <= user_age <= item["age_max"]):
            return {
                "success": False, 
                "reason": "This item is not available for your age group",
                "alternative_items": await self.get_age_appropriate_alternatives(user_id, item["category"])
            }
        
        # Check if user already owns item
        if await self.user_owns_item(user_id, item_id):
            return {"success": False, "reason": "You already own this item"}
        
        # Check balance
        current_balance = await self.get_balance_amount(user_id, currency_type)
        if current_balance < item["price"]:
            return {
                "success": False,
                "reason": f"Insufficient balance. You need {item['price'] - current_balance} more {currency_type}",
                "earning_suggestions": await self.get_earning_suggestions(user_id),
                "current_balance": current_balance,
                "required_amount": item["price"]
            }
        
        # Check spending limits
        can_spend, limit_reason = await self.check_spending_limits(user_id, item["price"], user_age)
        if not can_spend:
            return {
                "success": False,
                "reason": limit_reason,
                "spending_summary": await self.get_spending_summary(user_id)
            }
        
        # Check parent approval if needed
        needs_approval = await self.needs_parent_approval(user_id, item["price"], item["category"])
        if needs_approval:
            return await self.request_parent_approval_for_purchase(user_id, item_id, item["price"])
        
        # Process purchase
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=user_id,
            amount=-item["price"],  # Negative for spending
            currency_type=currency_type,
            transaction_type=TransactionType.SPEND,
            category=item["category"],
            description=f"Purchased {item['name']}",
            metadata={"item_id": item_id, "item_name": item["name"]},
            created_at=datetime.now()
        )
        
        success = await self.process_transaction(transaction)
        
        if success:
            # Record the purchase
            await self.record_purchase(user_id, item_id, transaction.transaction_id)
            
            return {
                "success": True,
                "item_purchased": item["name"],
                "amount_spent": item["price"],
                "new_balance": await self.get_balance_amount(user_id, currency_type),
                "item_details": item,
                "congratulations_message": f"🎉 You now own {item['name']}!",
                "related_items": await self.get_related_items(item["category"], user_age)
            }
        else:
            return {
                "success": False,
                "reason": "Failed to process purchase",
                "suggested_action": "Please try again or contact support"
            }

    async def process_daily_allowance(self, user_id: str) -> Dict:
        """Give user their daily allowance if eligible"""
        user_age = await self.get_user_age(user_id)
        
        # Check if allowance already given today
        async with self.db_pool.acquire() as conn:
            last_allowance = await conn.fetchval("""
                SELECT last_allowance FROM user_balances
                WHERE user_id = $1 AND currency_type = 'coins'
            """, user_id)
            
            if last_allowance and last_allowance.date() == datetime.now().date():
                return {
                    "success": False,
                    "reason": "Daily allowance already received",
                    "next_allowance": "Tomorrow",
                    "current_balance": await self.get_balance_amount(user_id, "coins")
                }
        
        # Calculate allowance amount based on age and recent activity
        base_allowance = self.get_base_allowance(user_age)
        activity_bonus = await self.calculate_activity_bonus(user_id)
        total_allowance = base_allowance + activity_bonus
        
        # Create allowance transaction
        transaction = Transaction(
            transaction_id=str(uuid.uuid4()),
            user_id=user_id,
            amount=total_allowance,
            currency_type="coins",
            transaction_type=TransactionType.ALLOWANCE,
            category="daily_allowance",
            description=f"Daily allowance (base: {base_allowance}, bonus: {activity_bonus})",
            metadata={"base_amount": base_allowance, "activity_bonus": activity_bonus},
            created_at=datetime.now()
        )
        
        success = await self.process_transaction(transaction)
        
        if success:
            # Update last allowance timestamp
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE user_balances 
                    SET last_allowance = CURRENT_TIMESTAMP
                    WHERE user_id = $1 AND currency_type = 'coins'
                """, user_id)
            
            return {
                "success": True,
                "allowance_received": total_allowance,
                "base_amount": base_allowance,
                "activity_bonus": activity_bonus,
                "new_balance": await self.get_balance_amount(user_id, "coins"),
                "bonus_explanation": await self.explain_activity_bonus(user_id, activity_bonus),
                "spending_suggestions": await self.get_spending_suggestions(user_id)
            }
        else:
            return {
                "success": False,
                "reason": "Failed to process daily allowance"
            }

    def calculate_earning_amount(self, reason: EarnReason, user_age: int, metadata: Dict) -> int:
        """Calculate how much currency to award based on reason and age"""
        earning_config = self.earning_rates.get(reason, {"base_amount": 5, "age_multipliers": {}})
        base_amount = earning_config["base_amount"]
        
        # Apply age multiplier
        age_multiplier = 1.0
        for (age_min, age_max), multiplier in earning_config["age_multipliers"].items():
            if age_min <= user_age <= age_max:
                age_multiplier = multiplier
                break
        
        # Apply difficulty/effort multiplier from metadata
        difficulty_multiplier = metadata.get("difficulty_multiplier", 1.0)
        time_bonus = metadata.get("time_bonus", 0)
        
        final_amount = int(base_amount * age_multiplier * difficulty_multiplier) + time_bonus
        return max(final_amount, 1)  # Ensure at least 1 currency unit

    async def apply_earning_multipliers(self, user_id: str, amount: int) -> int:
        """Apply any active earning multipliers"""
        async with self.db_pool.acquire() as conn:
            multipliers = await conn.fetch("""
                SELECT multiplier_value FROM earning_multipliers
                WHERE user_id = $1 AND is_active = TRUE 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            """, user_id)
        
        total_multiplier = 1.0
        for multiplier in multipliers:
            total_multiplier *= multiplier["multiplier_value"]
        
        return int(amount * total_multiplier)

    async def process_transaction(self, transaction: Transaction) -> bool:
        """Process a currency transaction"""
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                try:
                    # Insert transaction record
                    await conn.execute("""
                        INSERT INTO currency_transactions (
                            transaction_id, user_id, amount, currency_type,
                            transaction_type, category, description, metadata, parent_approved
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """, 
                        transaction.transaction_id, transaction.user_id, transaction.amount,
                        transaction.currency_type, transaction.transaction_type.value,
                        transaction.category, transaction.description, 
                        json.dumps(transaction.metadata), transaction.parent_approved
                    )
                    
                    # Update user balance
                    if transaction.amount > 0:
                        # Earning
                        await conn.execute("""
                            UPDATE user_balances 
                            SET balance = balance + $1, total_earned = total_earned + $1
                            WHERE user_id = $2 AND currency_type = $3
                        """, transaction.amount, transaction.user_id, transaction.currency_type)
                    else:
                        # Spending
                        await conn.execute("""
                            UPDATE user_balances 
                            SET balance = balance + $1, total_spent = total_spent + $2
                            WHERE user_id = $3 AND currency_type = $4
                        """, transaction.amount, abs(transaction.amount), 
                           transaction.user_id, transaction.currency_type)
                    
                    return True
                    
                except Exception as e:
                    print(f"Transaction failed: {e}")
                    return False

    async def get_virtual_store(self, user_id: str, category: str = None) -> Dict:
        """Get virtual store items available to user"""
        user_age = await self.get_user_age(user_id)
        user_balance = await self.get_balance_amount(user_id, "coins")
        
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT * FROM virtual_store_items
                WHERE is_available = TRUE AND age_min <= $1 AND age_max >= $1
            """
            params = [user_age]
            
            if category:
                query += " AND category = $2"
                params.append(category)
            
            query += " ORDER BY price ASC"
            
            items = await conn.fetch(query, *params)
            
            # Get user's owned items
            owned_items = await conn.fetch("""
                SELECT item_id FROM user_purchases WHERE user_id = $1
            """, user_id)
            owned_set = {item["item_id"] for item in owned_items}
        
        # Format items for display
        store_items = []
        for item in items:
            item_data = {
                "item_id": item["item_id"],
                "name": item["name"],
                "description": item["description"],
                "category": item["category"],
                "price": item["price"],
                "currency_type": item["currency_type"],
                "preview_image": item["preview_image"],
                "owned": item["item_id"] in owned_set,
                "can_afford": user_balance >= item["price"],
                "unlock_requirements": json.loads(item["unlock_requirements"]) if item["unlock_requirements"] else None
            }
            store_items.append(item_data)
        
        # Group items by category
        categories = {}
        for item in store_items:
            cat = item["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        return {
            "user_balance": user_balance,
            "currency_type": "coins",
            "items_by_category": categories,
            "featured_items": store_items[:6],  # First 6 items as featured
            "affordable_items": [item for item in store_items if item["can_afford"] and not item["owned"]],
            "wishlist_suggestions": [item for item in store_items if not item["can_afford"] and not item["owned"]][:5]
        }

    async def get_earning_suggestions(self, user_id: str) -> List[Dict]:
        """Get personalized suggestions for earning more currency"""
        user_age = await self.get_user_age(user_id)
        
        suggestions = [
            {
                "activity": "Complete a coding project",
                "potential_earning": "10-25 coins",
                "time_estimate": "30-60 minutes",
                "difficulty": "Medium",
                "description": "Build something creative and learn new skills"
            },
            {
                "activity": "Finish daily learning goals",
                "potential_earning": "8-12 coins", 
                "time_estimate": "15-30 minutes",
                "difficulty": "Easy",
                "description": "Complete your daily lessons and challenges"
            },
            {
                "activity": "Help another user",
                "potential_earning": "12-18 coins",
                "time_estimate": "20-40 minutes", 
                "difficulty": "Medium",
                "description": "Share knowledge and help others learn"
            }
        ]
        
        if user_age >= 10:
            suggestions.append({
                "activity": "Solve bonus challenges",
                "potential_earning": "15-30 coins",
                "time_estimate": "45-90 minutes",
                "difficulty": "Hard",
                "description": "Take on advanced challenges for bigger rewards"
            })
        
        return suggestions

    def get_earning_description(self, reason: EarnReason, amount: int) -> str:
        """Generate user-friendly description of earning"""
        descriptions = {
            EarnReason.PROJECT_COMPLETED: f"🎉 Great job completing your project! (+{amount} coins)",
            EarnReason.LESSON_FINISHED: f"📚 Awesome! You finished a lesson! (+{amount} coins)",
            EarnReason.ACHIEVEMENT_UNLOCKED: f"🏆 Achievement unlocked! Well done! (+{amount} coins)",
            EarnReason.DAILY_GOAL_MET: f"⭐ Daily goal completed! Keep it up! (+{amount} coins)",
            EarnReason.HELPING_OTHERS: f"🤝 Thank you for helping others! (+{amount} coins)",
            EarnReason.CREATIVE_WORK: f"🎨 Your creativity is amazing! (+{amount} coins)",
            EarnReason.PROBLEM_SOLVING: f"🧩 Excellent problem solving! (+{amount} coins)"
        }
        
        return descriptions.get(reason, f"Great work! (+{amount} coins)")

    def generate_celebration_message(self, reason: EarnReason, amount: int) -> str:
        """Generate encouraging celebration message"""
        messages = {
            EarnReason.PROJECT_COMPLETED: [
                "Your project is fantastic! 🌟",
                "What an amazing creation! 🚀",
                "You should be proud of this work! ✨"
            ],
            EarnReason.ACHIEVEMENT_UNLOCKED: [
                "You're on fire! 🔥",
                "Achievement master! 🏆",
                "Keep collecting those achievements! ⭐"
            ],
            EarnReason.HELPING_OTHERS: [
                "You're such a helpful friend! 🤗",
                "Kindness like yours makes the world better! 💙",
                "Thanks for being an awesome community member! 🌟"
            ]
        }
        
        import random
        message_options = messages.get(reason, ["Great job!", "Keep up the good work!", "You're doing amazing!"])
        return random.choice(message_options)

    async def get_user_age(self, user_id: str) -> int:
        """Get user age from profile"""
        # This would integrate with user profile system
        # For now, return default age
        return 10

    async def get_balance_amount(self, user_id: str, currency_type: str) -> int:
        """Get just the balance amount"""
        async with self.db_pool.acquire() as conn:
            balance = await conn.fetchval("""
                SELECT balance FROM user_balances
                WHERE user_id = $1 AND currency_type = $2
            """, user_id, currency_type)
            return balance if balance is not None else 0

    async def can_earn_currency(self, user_id: str, reason: EarnReason) -> Tuple[bool, str]:
        """Check if user can earn currency for this reason"""
        # Check for rate limiting (e.g., can't complete same lesson multiple times per day)
        if reason in [EarnReason.LESSON_FINISHED, EarnReason.DAILY_GOAL_MET]:
            async with self.db_pool.acquire() as conn:
                today_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM currency_transactions
                    WHERE user_id = $1 AND category = $2 
                    AND created_at >= CURRENT_DATE
                """, user_id, reason.value)
                
                if reason == EarnReason.DAILY_GOAL_MET and today_count >= 1:
                    return False, "Daily goal reward already claimed today"
        
        return True, "Can earn currency"

    def get_base_allowance(self, user_age: int) -> int:
        """Calculate base daily allowance by age"""
        if user_age < 8:
            return 15
        elif user_age < 12:
            return 12
        elif user_age < 16:
            return 10
        else:
            return 8

    async def calculate_activity_bonus(self, user_id: str) -> int:
        """Calculate bonus allowance based on recent activity"""
        async with self.db_pool.acquire() as conn:
            # Count activities from yesterday
            yesterday = datetime.now() - timedelta(days=1)
            activity_count = await conn.fetchval("""
                SELECT COUNT(*) FROM currency_transactions
                WHERE user_id = $1 AND transaction_type = 'earn' 
                AND created_at >= $2
            """, user_id, yesterday)
        
        # Bonus for being active
        if activity_count >= 5:
            return 8
        elif activity_count >= 3:
            return 5
        elif activity_count >= 1:
            return 2
        else:
            return 0

    async def check_spending_limits(self, user_id: str, amount: int, user_age: int) -> Tuple[bool, str]:
        """Check if spending is within daily/weekly limits"""
        # Get age-appropriate limits
        limits = None
        for (age_min, age_max), limit_config in self.spending_limits.items():
            if age_min <= user_age <= age_max:
                limits = limit_config
                break
        
        if not limits:
            return True, "No limits apply"
        
        # Check daily spending
        async with self.db_pool.acquire() as conn:
            today_spent = await conn.fetchval("""
                SELECT COALESCE(SUM(ABS(amount)), 0) FROM currency_transactions
                WHERE user_id = $1 AND transaction_type = 'spend'
                AND created_at >= CURRENT_DATE
            """, user_id)
            
            if today_spent + amount > limits["daily"]:
                return False, f"Daily spending limit of {limits['daily']} coins would be exceeded"
            
            # Check weekly spending
            week_start = datetime.now() - timedelta(days=7)
            week_spent = await conn.fetchval("""
                SELECT COALESCE(SUM(ABS(amount)), 0) FROM currency_transactions
                WHERE user_id = $1 AND transaction_type = 'spend'
                AND created_at >= $2
            """, user_id, week_start)
            
            if week_spent + amount > limits["weekly"]:
                return False, f"Weekly spending limit of {limits['weekly']} coins would be exceeded"
        
        return True, "Within spending limits"

    async def needs_parent_approval(self, user_id: str, amount: int, category: str) -> bool:
        """Check if purchase needs parent approval"""
        user_age = await self.get_user_age(user_id)
        
        # Young kids need approval for larger purchases
        if user_age < 10 and amount >= 50:
            return True
        
        # Certain categories always need approval
        approval_categories = [SpendCategory.SPECIAL_FEATURES.value, SpendCategory.POWER_UPS.value]
        if category in approval_categories:
            return True
        
        return False

    async def get_store_item(self, item_id: str) -> Optional[Dict]:
        """Get specific store item details"""
        async with self.db_pool.acquire() as conn:
            item = await conn.fetchrow("""
                SELECT * FROM virtual_store_items WHERE item_id = $1
            """, item_id)
            
            return dict(item) if item else None

    async def user_owns_item(self, user_id: str, item_id: str) -> bool:
        """Check if user already owns an item"""
        async with self.db_pool.acquire() as conn:
            exists = await conn.fetchval("""
                SELECT EXISTS(SELECT 1 FROM user_purchases 
                WHERE user_id = $1 AND item_id = $2)
            """, user_id, item_id)
            
            return exists

    async def record_purchase(self, user_id: str, item_id: str, transaction_id: str):
        """Record item purchase"""
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_purchases (user_id, item_id, transaction_id)
                VALUES ($1, $2, $3)
            """, user_id, item_id, transaction_id)

    async def get_daily_earning_potential(self, user_id: str) -> Dict:
        """Calculate how much user could potentially earn today"""
        user_age = await self.get_user_age(user_id)
        
        return {
            "project_completion": "10-25 coins",
            "lesson_completion": "5-15 coins per lesson", 
            "daily_goal": "8-12 coins",
            "helping_others": "12-18 coins",
            "daily_allowance": f"{self.get_base_allowance(user_age)}+ coins",
            "total_potential": "50-100+ coins per day with active participation"
        }

    async def check_bonus_opportunities(self, user_id: str, recent_reason: EarnReason) -> List[Dict]:
        """Check for bonus earning opportunities"""
        opportunities = []
        
        # Streak bonuses
        if recent_reason == EarnReason.DAILY_GOAL_MET:
            streak = await self.calculate_daily_streak(user_id)
            if streak >= 7:
                opportunities.append({
                    "type": "streak_bonus",
                    "description": f"🔥 {streak} day streak! Keep it up for bonus rewards!",
                    "potential_bonus": "20 coins at 10 days"
                })
        
        # Completion bonuses
        if recent_reason == EarnReason.PROJECT_COMPLETED:
            project_count = await self.count_projects_this_week(user_id)
            if project_count >= 3:
                opportunities.append({
                    "type": "productivity_bonus",
                    "description": "🚀 3+ projects this week! You're on a roll!",
                    "potential_bonus": "15 coins bonus"
                })
        
        return opportunities

    async def calculate_daily_streak(self, user_id: str) -> int:
        """Calculate consecutive days user has met daily goal"""
        # This would check for consecutive days of daily_goal_met transactions
        return 5  # Mock value

    async def count_projects_this_week(self, user_id: str) -> int:
        """Count projects completed this week"""
        week_start = datetime.now() - timedelta(days=7)
        
        async with self.db_pool.acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM currency_transactions
                WHERE user_id = $1 AND category = $2 AND created_at >= $3
            """, user_id, EarnReason.PROJECT_COMPLETED.value, week_start)
            
            return count or 0

    async def get_achievement_progress(self, user_id: str) -> Dict:
        """Get progress towards earning-related achievements"""
        total_earned = await self.get_total_earned(user_id)
        
        return {
            "coin_collector": {
                "progress": min(total_earned, 1000),
                "target": 1000,
                "description": "Earn 1000 total coins",
                "reward": "25 bonus coins + special badge"
            },
            "daily_champion": {
                "progress": await self.calculate_daily_streak(user_id),
                "target": 10,
                "description": "Meet daily goals for 10 days in a row",
                "reward": "50 bonus coins + streak multiplier"
            }
        }

    async def get_total_earned(self, user_id: str) -> int:
        """Get user's total lifetime earnings"""
        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval("""
                SELECT COALESCE(total_earned, 0) FROM user_balances
                WHERE user_id = $1 AND currency_type = 'coins'
            """, user_id)
            
            return total or 0