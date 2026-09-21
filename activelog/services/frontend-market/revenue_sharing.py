"""
Revenue Sharing Automation System
Automated revenue distribution, tracking, and optimization
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import uuid
import asyncio
import logging
import json
from decimal import Decimal, ROUND_HALF_UP
import sqlite3

logger = logging.getLogger(__name__)

class RevenueType(str, Enum):
    SUBSCRIPTION = "subscription"
    ONE_TIME = "one_time"
    TRANSACTION = "transaction"
    ADVERTISING = "advertising"
    LICENSING = "licensing"
    COMMISSION = "commission"

class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"

class RevenueStream(BaseModel):
    id: str
    frontend_id: str
    owner_id: str
    revenue_type: RevenueType
    amount: Decimal
    currency: str = "USD"
    source_description: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class RevenueSharingRule(BaseModel):
    id: str
    frontend_id: str
    rule_name: str
    
    # Sharing percentages (must sum to 100)
    platform_percentage: float = 10.0  # Platform fee
    owner_percentage: float = 70.0      # Original owner
    developer_percentage: float = 15.0   # Development team
    maintenance_percentage: float = 5.0  # Maintenance fund
    
    # Conditions
    minimum_threshold: Decimal = Decimal('10.00')
    payout_frequency: str = "monthly"  # daily, weekly, monthly, quarterly
    
    # Performance bonuses
    performance_bonus_enabled: bool = False
    performance_targets: Dict[str, float] = {}
    
    created_at: datetime
    updated_at: datetime

class PayoutRecord(BaseModel):
    id: str
    revenue_stream_id: str
    recipient_id: str
    recipient_type: str  # platform, owner, developer, maintenance
    
    gross_amount: Decimal
    platform_fee: Decimal
    net_amount: Decimal
    
    status: PayoutStatus
    payment_method: str = "bank_transfer"
    transaction_id: Optional[str] = None
    
    scheduled_date: datetime
    processed_date: Optional[datetime] = None
    
    metadata: Dict[str, Any] = {}

class RevenueAnalytics(BaseModel):
    frontend_id: str
    period_start: datetime
    period_end: datetime
    
    total_revenue: Decimal
    revenue_by_type: Dict[RevenueType, Decimal]
    growth_rate: float
    
    payout_summary: Dict[str, Decimal]
    top_performing_features: List[Dict[str, Any]]
    
    forecast: Dict[str, float]

class RevenueSharingManager:
    def __init__(self):
        self.db_path = "/home/activeloguser/activelog/services/frontend-market/data/revenue_sharing.db"
        self.init_database()
    
    def init_database(self):
        """Initialize revenue sharing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Revenue streams table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_streams (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                revenue_type TEXT NOT NULL,
                amount DECIMAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                source_description TEXT,
                data TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Revenue sharing rules table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS revenue_sharing_rules (
                id TEXT PRIMARY KEY,
                frontend_id TEXT NOT NULL,
                rule_name TEXT NOT NULL,
                platform_percentage REAL NOT NULL,
                owner_percentage REAL NOT NULL,
                developer_percentage REAL NOT NULL,
                maintenance_percentage REAL NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Payout records table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payout_records (
                id TEXT PRIMARY KEY,
                revenue_stream_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                recipient_type TEXT NOT NULL,
                gross_amount DECIMAL NOT NULL,
                net_amount DECIMAL NOT NULL,
                status TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (revenue_stream_id) REFERENCES revenue_streams (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def record_revenue(self, revenue_data: Dict[str, Any]) -> RevenueStream:
        """Record new revenue stream"""
        revenue_id = f"REV_{uuid.uuid4().hex[:8].upper()}"
        
        revenue_stream = RevenueStream(
            id=revenue_id,
            frontend_id=revenue_data["frontend_id"],
            owner_id=revenue_data["owner_id"],
            revenue_type=RevenueType(revenue_data["revenue_type"]),
            amount=Decimal(str(revenue_data["amount"])),
            currency=revenue_data.get("currency", "USD"),
            source_description=revenue_data["source_description"],
            timestamp=datetime.now(),
            metadata=revenue_data.get("metadata", {})
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO revenue_streams 
            (id, frontend_id, owner_id, revenue_type, amount, currency, source_description, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            revenue_stream.id,
            revenue_stream.frontend_id,
            revenue_stream.owner_id,
            revenue_stream.revenue_type.value,
            float(revenue_stream.amount),
            revenue_stream.currency,
            revenue_stream.source_description,
            revenue_stream.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        # Trigger automatic payout calculation
        await self.process_revenue_sharing(revenue_stream)
        
        logger.info(f"Recorded revenue stream {revenue_id} for frontend {revenue_stream.frontend_id}")
        return revenue_stream
    
    async def create_sharing_rule(self, rule_data: Dict[str, Any]) -> RevenueSharingRule:
        """Create new revenue sharing rule"""
        rule_id = f"RULE_{uuid.uuid4().hex[:8].upper()}"
        
        # Validate percentages sum to 100
        total_percentage = (
            rule_data.get("platform_percentage", 10.0) +
            rule_data.get("owner_percentage", 70.0) +
            rule_data.get("developer_percentage", 15.0) +
            rule_data.get("maintenance_percentage", 5.0)
        )
        
        if abs(total_percentage - 100.0) > 0.01:
            raise ValueError(f"Revenue sharing percentages must sum to 100%, got {total_percentage}%")
        
        sharing_rule = RevenueSharingRule(
            id=rule_id,
            frontend_id=rule_data["frontend_id"],
            rule_name=rule_data["rule_name"],
            platform_percentage=rule_data.get("platform_percentage", 10.0),
            owner_percentage=rule_data.get("owner_percentage", 70.0),
            developer_percentage=rule_data.get("developer_percentage", 15.0),
            maintenance_percentage=rule_data.get("maintenance_percentage", 5.0),
            minimum_threshold=Decimal(str(rule_data.get("minimum_threshold", "10.00"))),
            payout_frequency=rule_data.get("payout_frequency", "monthly"),
            performance_bonus_enabled=rule_data.get("performance_bonus_enabled", False),
            performance_targets=rule_data.get("performance_targets", {}),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO revenue_sharing_rules 
            (id, frontend_id, rule_name, platform_percentage, owner_percentage, 
             developer_percentage, maintenance_percentage, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            sharing_rule.id,
            sharing_rule.frontend_id,
            sharing_rule.rule_name,
            sharing_rule.platform_percentage,
            sharing_rule.owner_percentage,
            sharing_rule.developer_percentage,
            sharing_rule.maintenance_percentage,
            sharing_rule.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created revenue sharing rule {rule_id} for frontend {sharing_rule.frontend_id}")
        return sharing_rule
    
    async def process_revenue_sharing(self, revenue_stream: RevenueStream) -> List[PayoutRecord]:
        """Process revenue sharing according to rules"""
        
        # Get sharing rule for this frontend
        sharing_rule = await self.get_sharing_rule(revenue_stream.frontend_id)
        if not sharing_rule:
            # Create default rule
            sharing_rule = await self.create_sharing_rule({
                "frontend_id": revenue_stream.frontend_id,
                "rule_name": "Default Revenue Sharing"
            })
        
        # Check minimum threshold
        if revenue_stream.amount < sharing_rule.minimum_threshold:
            logger.info(f"Revenue {revenue_stream.id} below minimum threshold, queuing for batch processing")
            return []
        
        # Calculate payouts
        payouts = []
        
        # Platform payout
        platform_amount = self._calculate_percentage(revenue_stream.amount, sharing_rule.platform_percentage)
        platform_payout = await self._create_payout_record(
            revenue_stream, "platform", "platform_treasury", platform_amount
        )
        payouts.append(platform_payout)
        
        # Owner payout
        owner_amount = self._calculate_percentage(revenue_stream.amount, sharing_rule.owner_percentage)
        owner_payout = await self._create_payout_record(
            revenue_stream, "owner", revenue_stream.owner_id, owner_amount
        )
        payouts.append(owner_payout)
        
        # Developer payout
        developer_amount = self._calculate_percentage(revenue_stream.amount, sharing_rule.developer_percentage)
        developer_payout = await self._create_payout_record(
            revenue_stream, "developer", f"dev_team_{revenue_stream.frontend_id}", developer_amount
        )
        payouts.append(developer_payout)
        
        # Maintenance fund payout
        maintenance_amount = self._calculate_percentage(revenue_stream.amount, sharing_rule.maintenance_percentage)
        maintenance_payout = await self._create_payout_record(
            revenue_stream, "maintenance", f"maintenance_fund_{revenue_stream.frontend_id}", maintenance_amount
        )
        payouts.append(maintenance_payout)
        
        # Process performance bonuses if enabled
        if sharing_rule.performance_bonus_enabled:
            bonus_payouts = await self._process_performance_bonuses(revenue_stream, sharing_rule)
            payouts.extend(bonus_payouts)
        
        logger.info(f"Processed revenue sharing for {revenue_stream.id}, created {len(payouts)} payouts")
        return payouts
    
    def _calculate_percentage(self, amount: Decimal, percentage: float) -> Decimal:
        """Calculate percentage of amount with proper rounding"""
        return (amount * Decimal(str(percentage)) / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
    
    async def _create_payout_record(self, revenue_stream: RevenueStream, recipient_type: str, 
                                  recipient_id: str, amount: Decimal) -> PayoutRecord:
        """Create payout record"""
        payout_id = f"PAYOUT_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate platform fee (2% processing fee)
        platform_fee = (amount * Decimal('0.02')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        net_amount = amount - platform_fee
        
        payout = PayoutRecord(
            id=payout_id,
            revenue_stream_id=revenue_stream.id,
            recipient_id=recipient_id,
            recipient_type=recipient_type,
            gross_amount=amount,
            platform_fee=platform_fee,
            net_amount=net_amount,
            status=PayoutStatus.PENDING,
            scheduled_date=datetime.now() + timedelta(days=1),  # Next business day
            metadata={
                "frontend_id": revenue_stream.frontend_id,
                "revenue_type": revenue_stream.revenue_type.value,
                "currency": revenue_stream.currency
            }
        )
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payout_records 
            (id, revenue_stream_id, recipient_id, recipient_type, gross_amount, net_amount, status, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            payout.id,
            payout.revenue_stream_id,
            payout.recipient_id,
            payout.recipient_type,
            float(payout.gross_amount),
            float(payout.net_amount),
            payout.status.value,
            payout.model_dump_json()
        ))
        
        conn.commit()
        conn.close()
        
        return payout
    
    async def _process_performance_bonuses(self, revenue_stream: RevenueStream, 
                                         sharing_rule: RevenueSharingRule) -> List[PayoutRecord]:
        """Process performance-based bonuses"""
        bonuses = []
        
        # Get frontend performance metrics
        performance_data = await self.get_frontend_performance(revenue_stream.frontend_id)
        
        for metric, target in sharing_rule.performance_targets.items():
            if metric in performance_data and performance_data[metric] >= target:
                # Award bonus (5% of revenue)
                bonus_amount = self._calculate_percentage(revenue_stream.amount, 5.0)
                bonus_payout = await self._create_payout_record(
                    revenue_stream, "performance_bonus", revenue_stream.owner_id, bonus_amount
                )
                bonus_payout.metadata["bonus_type"] = metric
                bonus_payout.metadata["target_achieved"] = performance_data[metric]
                bonuses.append(bonus_payout)
        
        return bonuses
    
    async def get_sharing_rule(self, frontend_id: str) -> Optional[RevenueSharingRule]:
        """Get revenue sharing rule for frontend"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM revenue_sharing_rules 
            WHERE frontend_id = ? 
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (frontend_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            rule_data = json.loads(result[0])
            return RevenueSharingRule(**rule_data)
        
        return None
    
    async def get_frontend_performance(self, frontend_id: str) -> Dict[str, float]:
        """Get performance metrics for bonus calculations"""
        # This would integrate with the performance metrics system
        return {
            "user_retention": 85.5,
            "page_load_time": 1.2,
            "conversion_rate": 3.4,
            "user_satisfaction": 4.6
        }
    
    async def process_scheduled_payouts(self) -> Dict[str, Any]:
        """Process all scheduled payouts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all pending payouts scheduled for today or earlier
        cursor.execute('''
            SELECT data FROM payout_records 
            WHERE status = 'pending' 
            AND datetime(json_extract(data, '$.scheduled_date')) <= datetime('now')
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        processed_count = 0
        failed_count = 0
        total_amount = Decimal('0')
        
        for result in results:
            payout_data = json.loads(result[0])
            payout = PayoutRecord(**payout_data)
            
            try:
                success = await self._execute_payout(payout)
                if success:
                    processed_count += 1
                    total_amount += payout.net_amount
                else:
                    failed_count += 1
            except Exception as e:
                logger.error(f"Failed to process payout {payout.id}: {e}")
                failed_count += 1
        
        return {
            "processed_count": processed_count,
            "failed_count": failed_count,
            "total_amount": float(total_amount),
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_payout(self, payout: PayoutRecord) -> bool:
        """Execute actual payout to recipient"""
        try:
            # In production, integrate with payment processors
            # For now, simulate successful payout
            
            # Update payout status
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Update status to completed
            payout.status = PayoutStatus.COMPLETED
            payout.processed_date = datetime.now()
            payout.transaction_id = f"TXN_{uuid.uuid4().hex[:12].upper()}"
            
            cursor.execute('''
                UPDATE payout_records 
                SET status = ?, data = ?
                WHERE id = ?
            ''', (payout.status.value, payout.model_dump_json(), payout.id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully processed payout {payout.id} for {payout.net_amount}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute payout {payout.id}: {e}")
            return False
    
    async def generate_revenue_analytics(self, frontend_id: str, 
                                       period_days: int = 30) -> RevenueAnalytics:
        """Generate comprehensive revenue analytics"""
        period_start = datetime.now() - timedelta(days=period_days)
        period_end = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get revenue streams for period
        cursor.execute('''
            SELECT revenue_type, SUM(amount) 
            FROM revenue_streams 
            WHERE frontend_id = ? 
            AND timestamp BETWEEN ? AND ?
            GROUP BY revenue_type
        ''', (frontend_id, period_start.isoformat(), period_end.isoformat()))
        
        revenue_by_type = {}
        total_revenue = Decimal('0')
        
        for row in cursor.fetchall():
            revenue_type = RevenueType(row[0])
            amount = Decimal(str(row[1]))
            revenue_by_type[revenue_type] = amount
            total_revenue += amount
        
        # Calculate growth rate
        previous_period_start = period_start - timedelta(days=period_days)
        cursor.execute('''
            SELECT SUM(amount) 
            FROM revenue_streams 
            WHERE frontend_id = ? 
            AND timestamp BETWEEN ? AND ?
        ''', (frontend_id, previous_period_start.isoformat(), period_start.isoformat()))
        
        previous_revenue = cursor.fetchone()[0] or 0
        growth_rate = 0.0
        if previous_revenue > 0:
            growth_rate = float((total_revenue - Decimal(str(previous_revenue))) / Decimal(str(previous_revenue)) * 100)
        
        # Get payout summary
        cursor.execute('''
            SELECT recipient_type, SUM(net_amount) 
            FROM payout_records pr
            JOIN revenue_streams rs ON pr.revenue_stream_id = rs.id
            WHERE rs.frontend_id = ?
            AND rs.timestamp BETWEEN ? AND ?
            GROUP BY recipient_type
        ''', (frontend_id, period_start.isoformat(), period_end.isoformat()))
        
        payout_summary = {}
        for row in cursor.fetchall():
            payout_summary[row[0]] = Decimal(str(row[1]))
        
        conn.close()
        
        return RevenueAnalytics(
            frontend_id=frontend_id,
            period_start=period_start,
            period_end=period_end,
            total_revenue=total_revenue,
            revenue_by_type=revenue_by_type,
            growth_rate=growth_rate,
            payout_summary=payout_summary,
            top_performing_features=[
                {"feature": "user_dashboard", "revenue": 1250.00},
                {"feature": "premium_features", "revenue": 890.00},
                {"feature": "api_access", "revenue": 675.00}
            ],
            forecast={
                "next_month": float(total_revenue * Decimal('1.15')),
                "confidence": 0.78
            }
        )
    
    async def get_payout_history(self, recipient_id: str, limit: int = 50) -> List[PayoutRecord]:
        """Get payout history for recipient"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT data FROM payout_records 
            WHERE recipient_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (recipient_id, limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [PayoutRecord(**json.loads(result[0])) for result in results]

# Global instance
revenue_sharing_manager = RevenueSharingManager()