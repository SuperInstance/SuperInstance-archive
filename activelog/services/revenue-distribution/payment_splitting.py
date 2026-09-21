"""
Automatic Payment Splitting System
Distribute payments automatically based on predefined rules and percentages
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

class SplitType(str, Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    REMAINDER = "remainder"

class SplitStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class PaymentSplit(BaseModel):
    id: str
    transaction_id: str
    recipient_id: str
    
    # Split configuration
    split_type: SplitType
    split_value: Decimal  # Percentage (0-100) or fixed amount
    calculated_amount: Decimal = Decimal('0')
    
    # Processing details
    status: SplitStatus = SplitStatus.PENDING
    processed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    
    # Metadata
    description: str = ""
    reference_id: Optional[str] = None
    priority: int = 1  # Higher numbers processed first
    
    created_at: datetime

class SplitRule(BaseModel):
    id: str
    rule_name: str
    
    # Conditions
    applicable_to: str = "all"  # user_id, transaction_type, or "all"
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    
    # Split definitions
    splits: List[Dict[str, Any]] = []  # Array of split configurations
    
    # Rule metadata
    active: bool = True
    created_by: str
    created_at: datetime
    updated_at: datetime

class PaymentSplitter:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/revenue-distribution/data/revenue_distribution.db"
        self.init_split_database()
    
    def init_split_database(self):
        """Initialize payment splitting database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Split rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS split_rules (
                id TEXT PRIMARY KEY,
                rule_name TEXT NOT NULL,
                applicable_to TEXT NOT NULL,
                min_amount DECIMAL,
                max_amount DECIMAL,
                active BOOLEAN DEFAULT TRUE,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        # Individual splits tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_splits (
                id TEXT PRIMARY KEY,
                transaction_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                split_type TEXT NOT NULL,
                split_value DECIMAL NOT NULL,
                calculated_amount DECIMAL NOT NULL,
                status TEXT DEFAULT 'pending',
                processed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def process_payment_splits(self, transaction_id: str, custom_splits: List[Dict[str, Any]] = None):
        """Process payment splits for a transaction"""
        
        # Get transaction details
        transaction = await self._get_transaction(transaction_id)
        if not transaction:
            logger.error(f"Transaction {transaction_id} not found")
            return
        
        # Determine splits to apply
        if custom_splits:
            splits = await self._create_custom_splits(transaction_id, custom_splits, transaction["net_amount"])
        else:
            splits = await self._apply_default_split_rules(transaction_id, transaction)
        
        # Process each split
        for split in splits:
            try:
                await self._execute_split(split)
                logger.info(f"Processed split {split.id} for {split.calculated_amount}")
            except Exception as e:
                logger.error(f"Failed to process split {split.id}: {e}")
                split.status = SplitStatus.FAILED
                split.failure_reason = str(e)
                await self._update_split(split)
    
    async def _create_custom_splits(self, transaction_id: str, custom_splits: List[Dict[str, Any]], 
                                  net_amount: Decimal) -> List[PaymentSplit]:
        """Create payment splits from custom configuration"""
        
        splits = []
        total_allocated = Decimal('0')
        
        # Sort by priority (higher first)
        sorted_splits = sorted(custom_splits, key=lambda x: x.get('priority', 1), reverse=True)
        
        for split_config in sorted_splits:
            split_id = f"SPLIT_{uuid.uuid4().hex[:8].upper()}"
            
            split_type = SplitType(split_config["type"])
            split_value = Decimal(str(split_config["value"]))
            
            # Calculate amount based on type
            if split_type == SplitType.PERCENTAGE:
                calculated_amount = (net_amount * split_value / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            elif split_type == SplitType.FIXED_AMOUNT:
                calculated_amount = split_value
            elif split_type == SplitType.REMAINDER:
                calculated_amount = net_amount - total_allocated
            else:
                calculated_amount = Decimal('0')
            
            # Ensure we don't exceed available amount
            calculated_amount = min(calculated_amount, net_amount - total_allocated)
            
            split = PaymentSplit(
                id=split_id,
                transaction_id=transaction_id,
                recipient_id=split_config["recipient_id"],
                split_type=split_type,
                split_value=split_value,
                calculated_amount=calculated_amount,
                description=split_config.get("description", ""),
                reference_id=split_config.get("reference_id"),
                priority=split_config.get("priority", 1),
                created_at=datetime.now()
            )
            
            splits.append(split)
            total_allocated += calculated_amount
            
            # Store split
            await self._store_split(split)
        
        return splits
    
    async def _apply_default_split_rules(self, transaction_id: str, transaction: Dict[str, Any]) -> List[PaymentSplit]:
        """Apply default split rules for a transaction"""
        
        # Get applicable split rules
        rules = await self._get_applicable_split_rules(transaction)
        
        splits = []
        for rule in rules:
            rule_splits = await self._create_splits_from_rule(transaction_id, transaction, rule)
            splits.extend(rule_splits)
        
        return splits
    
    async def _get_applicable_split_rules(self, transaction: Dict[str, Any]) -> List[SplitRule]:
        """Get split rules applicable to a transaction"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM split_rules
            WHERE active = TRUE
            AND (applicable_to = 'all' OR applicable_to = ?)
            AND (min_amount IS NULL OR min_amount <= ?)
            AND (max_amount IS NULL OR max_amount >= ?)
        ''', (
            transaction["recipient_id"], 
            transaction["net_amount"], 
            transaction["net_amount"]
        ))
        
        results = cursor.fetchall()
        conn.close()
        
        rules = []
        for result in results:
            rule_data = json.loads(result[0])
            rule = SplitRule(**rule_data)
            rules.append(rule)
        
        return rules
    
    async def _create_splits_from_rule(self, transaction_id: str, transaction: Dict[str, Any], 
                                     rule: SplitRule) -> List[PaymentSplit]:
        """Create payment splits from a split rule"""
        
        splits = []
        net_amount = Decimal(str(transaction["net_amount"]))
        
        for split_config in rule.splits:
            split_id = f"SPLIT_{uuid.uuid4().hex[:8].upper()}"
            
            split_type = SplitType(split_config["type"])
            split_value = Decimal(str(split_config["value"]))
            
            # Calculate amount
            if split_type == SplitType.PERCENTAGE:
                calculated_amount = (net_amount * split_value / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                )
            elif split_type == SplitType.FIXED_AMOUNT:
                calculated_amount = split_value
            else:
                calculated_amount = Decimal('0')
            
            split = PaymentSplit(
                id=split_id,
                transaction_id=transaction_id,
                recipient_id=split_config["recipient_id"],
                split_type=split_type,
                split_value=split_value,
                calculated_amount=calculated_amount,
                description=f"Rule: {rule.rule_name}",
                priority=split_config.get("priority", 1),
                created_at=datetime.now()
            )
            
            splits.append(split)
            await self._store_split(split)
        
        return splits
    
    async def _execute_split(self, split: PaymentSplit):
        """Execute a payment split"""
        
        # Update status to processing
        split.status = SplitStatus.PROCESSING
        await self._update_split(split)
        
        # In production, this would integrate with payment processors
        # For demo, we simulate successful split execution
        await asyncio.sleep(0.1)  # Simulate processing time
        
        # Mark as completed
        split.status = SplitStatus.COMPLETED
        split.processed_at = datetime.now()
        await self._update_split(split)
        
        # Create accounting entry (simplified)
        await self._create_split_accounting_entry(split)
    
    async def _create_split_accounting_entry(self, split: PaymentSplit):
        """Create accounting entry for the split"""
        
        # This would integrate with accounting systems
        logger.info(f"Accounting entry: Split {split.calculated_amount} to {split.recipient_id}")
    
    async def create_split_rule(self, rule_data: Dict[str, Any]) -> SplitRule:
        """Create a new payment split rule"""
        
        rule_id = f"RULE_{uuid.uuid4().hex[:8].upper()}"
        
        rule = SplitRule(
            id=rule_id,
            rule_name=rule_data["rule_name"],
            applicable_to=rule_data.get("applicable_to", "all"),
            min_amount=Decimal(str(rule_data["min_amount"])) if rule_data.get("min_amount") else None,
            max_amount=Decimal(str(rule_data["max_amount"])) if rule_data.get("max_amount") else None,
            splits=rule_data["splits"],
            created_by=rule_data["created_by"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store rule
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO split_rules 
            (id, rule_name, applicable_to, min_amount, max_amount, created_by, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            rule.id, rule.rule_name, rule.applicable_to,
            float(rule.min_amount) if rule.min_amount else None,
            float(rule.max_amount) if rule.max_amount else None,
            rule.created_by, rule.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created split rule {rule_id}: {rule.rule_name}")
        return rule
    
    async def get_transaction_splits(self, transaction_id: str) -> List[PaymentSplit]:
        """Get all splits for a transaction"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM payment_splits
            WHERE transaction_id = ?
            ORDER BY priority DESC, created_at ASC
        ''', (transaction_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        splits = []
        for result in results:
            split_data = json.loads(result[0])
            split = PaymentSplit(**split_data)
            splits.append(split)
        
        return splits
    
    async def get_recipient_splits(self, recipient_id: str, limit: int = 50) -> List[PaymentSplit]:
        """Get splits for a specific recipient"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM payment_splits
            WHERE recipient_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        ''', (recipient_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        splits = []
        for result in results:
            split_data = json.loads(result[0])
            split = PaymentSplit(**split_data)
            splits.append(split)
        
        return splits
    
    async def get_split_analytics(self, period_days: int = 30) -> Dict[str, Any]:
        """Get payment splitting analytics"""
        
        period_start = datetime.now() - timedelta(days=period_days)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total splits processed
        cursor.execute('''
            SELECT 
                COUNT(*) as split_count,
                SUM(calculated_amount) as total_amount,
                AVG(calculated_amount) as avg_amount
            FROM payment_splits
            WHERE created_at >= ?
        ''', (period_start.isoformat(),))
        
        totals = cursor.fetchone()
        
        # Status breakdown
        cursor.execute('''
            SELECT status, COUNT(*), SUM(calculated_amount)
            FROM payment_splits
            WHERE created_at >= ?
            GROUP BY status
        ''', (period_start.isoformat(),))
        
        status_breakdown = {}
        for row in cursor.fetchall():
            status_breakdown[row[0]] = {
                "count": row[1],
                "total_amount": float(row[2]) if row[2] else 0.0
            }
        
        # Top recipients
        cursor.execute('''
            SELECT recipient_id, COUNT(*), SUM(calculated_amount)
            FROM payment_splits
            WHERE created_at >= ?
            GROUP BY recipient_id
            ORDER BY SUM(calculated_amount) DESC
            LIMIT 10
        ''', (period_start.isoformat(),))
        
        top_recipients = []
        for row in cursor.fetchall():
            top_recipients.append({
                "recipient_id": row[0],
                "split_count": row[1],
                "total_received": float(row[2])
            })
        
        conn.close()
        
        return {
            "period_days": period_days,
            "period_start": period_start.isoformat(),
            "totals": {
                "split_count": totals[0],
                "total_amount": float(totals[1]) if totals[1] else 0.0,
                "average_amount": float(totals[2]) if totals[2] else 0.0
            },
            "status_breakdown": status_breakdown,
            "top_recipients": top_recipients,
            "success_rate": (
                status_breakdown.get("completed", {}).get("count", 0) / totals[0] * 100
                if totals[0] > 0 else 0.0
            )
        }
    
    async def _get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction details"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM revenue_transactions
            WHERE id = ?
        ''', (transaction_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return json.loads(result[0])
        return None
    
    async def _store_split(self, split: PaymentSplit):
        """Store payment split in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_splits 
            (id, transaction_id, recipient_id, split_type, split_value, calculated_amount, data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            split.id, split.transaction_id, split.recipient_id,
            split.split_type.value, float(split.split_value),
            float(split.calculated_amount), split.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
    
    async def _update_split(self, split: PaymentSplit):
        """Update payment split in database"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE payment_splits 
            SET status = ?, processed_at = ?, data = ?
            WHERE id = ?
        ''', (
            split.status.value,
            split.processed_at.isoformat() if split.processed_at else None,
            split.model_dump_json(),
            split.id
        ))
        
        conn.commit()
        conn.close()

# Global instance
payment_splitter = PaymentSplitter()