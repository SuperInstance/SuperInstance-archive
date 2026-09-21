"""
Database Manager for Cloud Infrastructure System
Handles all database operations with SQLite backend and async support
"""

import asyncio
import logging
import sqlite3
import aiosqlite
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
import json
from pathlib import Path

from core.models import (
    User, EC2Instance, BillingRecord, ScalingEvent, GameNightEvent,
    APIKey, UserIsolationInfo, DATABASE_SCHEMA, current_timestamp,
    InstanceState, UserTier, InstanceType, BillingStatus, EventType,
    Organization, Department, Project, OrganizationMember, ApprovalRequest,
    OrganizationTier, OrganizationRole, ApprovalStatus
)

class DatabaseManager:
    """Centralized database management for all cloud infrastructure data"""
    
    def __init__(self, db_path: str = "cloud_infrastructure.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.initialized = False
        
    async def initialize(self):
        """Initialize database with schema"""
        if self.initialized:
            return
            
        try:
            # Ensure database directory exists
            db_dir = Path(self.db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Create database and schema
            async with aiosqlite.connect(self.db_path) as db:
                await db.executescript(DATABASE_SCHEMA)
                await db.commit()
                
            self.initialized = True
            self.logger.info(f"Database initialized at {self.db_path}")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    # User management
    async def create_user(self, user: User) -> bool:
        """Create a new user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO users 
                    (user_id, email, tier, created_at, vpc_id, encryption_key_id, 
                     billing_status, monthly_budget, current_spend)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user.user_id, user.email, user.tier.value, user.created_at,
                    user.vpc_id, user.encryption_key_id, user.billing_status.value,
                    user.monthly_budget, user.current_spend
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT user_id, email, tier, created_at, vpc_id, encryption_key_id,
                           billing_status, monthly_budget, current_spend
                    FROM users WHERE user_id = ?
                """, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return User(
                            user_id=row[0],
                            email=row[1],
                            tier=UserTier(row[2]),
                            created_at=datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3],
                            vpc_id=row[4],
                            encryption_key_id=row[5],
                            billing_status=BillingStatus(row[6]),
                            monthly_budget=row[7],
                            current_spend=row[8]
                        )
                    return None
        except Exception as e:
            self.logger.error(f"Error getting user: {e}")
            return None
    
    async def update_user(self, user: User) -> bool:
        """Update user information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE users SET 
                        email = ?, tier = ?, vpc_id = ?, encryption_key_id = ?,
                        billing_status = ?, monthly_budget = ?, current_spend = ?
                    WHERE user_id = ?
                """, (
                    user.email, user.tier.value, user.vpc_id, user.encryption_key_id,
                    user.billing_status.value, user.monthly_budget, user.current_spend,
                    user.user_id
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating user: {e}")
            return False
    
    async def count_total_users(self) -> int:
        """Count total users"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"Error counting users: {e}")
            return 0
    
    async def get_active_users_with_instances(self) -> List[User]:
        """Get users that have running instances"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT DISTINCT u.user_id, u.email, u.tier, u.created_at, 
                           u.vpc_id, u.encryption_key_id, u.billing_status, 
                           u.monthly_budget, u.current_spend
                    FROM users u
                    JOIN ec2_instances i ON u.user_id = i.user_id
                    WHERE i.state IN ('running', 'pending')
                """) as cursor:
                    users = []
                    async for row in cursor:
                        user = User(
                            user_id=row[0],
                            email=row[1],
                            tier=UserTier(row[2]),
                            created_at=datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3],
                            vpc_id=row[4],
                            encryption_key_id=row[5],
                            billing_status=BillingStatus(row[6]),
                            monthly_budget=row[7],
                            current_spend=row[8]
                        )
                        users.append(user)
                    return users
        except Exception as e:
            self.logger.error(f"Error getting active users: {e}")
            return []
    
    # Instance management
    async def create_instance(self, instance: EC2Instance) -> bool:
        """Create a new instance record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO ec2_instances
                    (instance_id, user_id, instance_type, state, created_at,
                     public_ip, private_ip, vpc_id, subnet_id, security_groups,
                     tags, last_billed_at, total_runtime_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    instance.instance_id, instance.user_id, instance.instance_type.value,
                    instance.state.value, instance.created_at, instance.public_ip,
                    instance.private_ip, instance.vpc_id, instance.subnet_id,
                    json.dumps(instance.security_groups), json.dumps(instance.tags),
                    instance.last_billed_at, instance.total_runtime_minutes
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating instance: {e}")
            return False
    
    async def get_instance(self, instance_id: str) -> Optional[EC2Instance]:
        """Get instance by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT instance_id, user_id, instance_type, state, created_at,
                           public_ip, private_ip, vpc_id, subnet_id, security_groups,
                           tags, last_billed_at, total_runtime_minutes
                    FROM ec2_instances WHERE instance_id = ?
                """, (instance_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return EC2Instance(
                            instance_id=row[0],
                            user_id=row[1],
                            instance_type=InstanceType(row[2]),
                            state=InstanceState(row[3]),
                            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            public_ip=row[5],
                            private_ip=row[6],
                            vpc_id=row[7],
                            subnet_id=row[8],
                            security_groups=json.loads(row[9]) if row[9] else [],
                            tags=json.loads(row[10]) if row[10] else {},
                            last_billed_at=datetime.fromisoformat(row[11]) if row[11] else None,
                            total_runtime_minutes=row[12]
                        )
                    return None
        except Exception as e:
            self.logger.error(f"Error getting instance: {e}")
            return None
    
    async def update_instance(self, instance: EC2Instance) -> bool:
        """Update instance information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE ec2_instances SET
                        state = ?, public_ip = ?, private_ip = ?, 
                        security_groups = ?, tags = ?, last_billed_at = ?,
                        total_runtime_minutes = ?
                    WHERE instance_id = ?
                """, (
                    instance.state.value, instance.public_ip, instance.private_ip,
                    json.dumps(instance.security_groups), json.dumps(instance.tags),
                    instance.last_billed_at, instance.total_runtime_minutes,
                    instance.instance_id
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating instance: {e}")
            return False
    
    async def get_user_instances(self, user_id: str) -> List[EC2Instance]:
        """Get all instances for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT instance_id, user_id, instance_type, state, created_at,
                           public_ip, private_ip, vpc_id, subnet_id, security_groups,
                           tags, last_billed_at, total_runtime_minutes
                    FROM ec2_instances WHERE user_id = ?
                    ORDER BY created_at DESC
                """, (user_id,)) as cursor:
                    instances = []
                    async for row in cursor:
                        instance = EC2Instance(
                            instance_id=row[0],
                            user_id=row[1],
                            instance_type=InstanceType(row[2]),
                            state=InstanceState(row[3]),
                            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            public_ip=row[5],
                            private_ip=row[6],
                            vpc_id=row[7],
                            subnet_id=row[8],
                            security_groups=json.loads(row[9]) if row[9] else [],
                            tags=json.loads(row[10]) if row[10] else {},
                            last_billed_at=datetime.fromisoformat(row[11]) if row[11] else None,
                            total_runtime_minutes=row[12]
                        )
                        instances.append(instance)
                    return instances
        except Exception as e:
            self.logger.error(f"Error getting user instances: {e}")
            return []
    
    async def get_instances_by_state(self, state: str) -> List[EC2Instance]:
        """Get instances by state"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT instance_id, user_id, instance_type, state, created_at,
                           public_ip, private_ip, vpc_id, subnet_id, security_groups,
                           tags, last_billed_at, total_runtime_minutes
                    FROM ec2_instances WHERE state = ?
                """, (state,)) as cursor:
                    instances = []
                    async for row in cursor:
                        instance = EC2Instance(
                            instance_id=row[0],
                            user_id=row[1],
                            instance_type=InstanceType(row[2]),
                            state=InstanceState(row[3]),
                            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            public_ip=row[5],
                            private_ip=row[6],
                            vpc_id=row[7],
                            subnet_id=row[8],
                            security_groups=json.loads(row[9]) if row[9] else [],
                            tags=json.loads(row[10]) if row[10] else {},
                            last_billed_at=datetime.fromisoformat(row[11]) if row[11] else None,
                            total_runtime_minutes=row[12]
                        )
                        instances.append(instance)
                    return instances
        except Exception as e:
            self.logger.error(f"Error getting instances by state: {e}")
            return []
    
    async def count_user_instances(self, user_id: str) -> int:
        """Count instances for a user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT COUNT(*) FROM ec2_instances 
                    WHERE user_id = ? AND state NOT IN ('terminated')
                """, (user_id,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"Error counting user instances: {e}")
            return 0
    
    async def count_all_instances(self) -> int:
        """Count all instances"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("SELECT COUNT(*) FROM ec2_instances") as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"Error counting all instances: {e}")
            return 0
    
    async def count_instances_by_state(self, state: InstanceState) -> int:
        """Count instances by state"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT COUNT(*) FROM ec2_instances WHERE state = ?
                """, (state.value,)) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else 0
        except Exception as e:
            self.logger.error(f"Error counting instances by state: {e}")
            return 0
    
    # Billing management
    async def create_billing_record(self, record: BillingRecord) -> bool:
        """Create a new billing record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO billing_records
                    (record_id, user_id, instance_id, instance_type, start_time,
                     end_time, duration_minutes, cost_per_minute, total_cost, billing_tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.record_id, record.user_id, record.instance_id,
                    record.instance_type.value, record.start_time, record.end_time,
                    record.duration_minutes, record.cost_per_minute, record.total_cost,
                    json.dumps(record.billing_tags)
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating billing record: {e}")
            return False
    
    async def get_billing_records(self, user_id: str, start_date: datetime = None,
                                end_date: datetime = None, instance_id: str = None) -> List[BillingRecord]:
        """Get billing records for a user"""
        try:
            query = """
                SELECT record_id, user_id, instance_id, instance_type, start_time,
                       end_time, duration_minutes, cost_per_minute, total_cost, billing_tags
                FROM billing_records WHERE user_id = ?
            """
            params = [user_id]
            
            if start_date:
                query += " AND start_time >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND end_time <= ?"
                params.append(end_date)
                
            if instance_id:
                query += " AND instance_id = ?"
                params.append(instance_id)
            
            query += " ORDER BY start_time DESC"
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(query, params) as cursor:
                    records = []
                    async for row in cursor:
                        record = BillingRecord(
                            record_id=row[0],
                            user_id=row[1],
                            instance_id=row[2],
                            instance_type=InstanceType(row[3]),
                            start_time=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            end_time=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                            duration_minutes=row[6],
                            cost_per_minute=row[7],
                            total_cost=row[8],
                            billing_tags=json.loads(row[9]) if row[9] else {}
                        )
                        records.append(record)
                    return records
        except Exception as e:
            self.logger.error(f"Error getting billing records: {e}")
            return []
    
    async def get_all_billing_records(self, start_date: datetime, end_date: datetime) -> List[BillingRecord]:
        """Get all billing records in date range"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT record_id, user_id, instance_id, instance_type, start_time,
                           end_time, duration_minutes, cost_per_minute, total_cost, billing_tags
                    FROM billing_records 
                    WHERE start_time >= ? AND end_time <= ?
                    ORDER BY start_time DESC
                """, (start_date, end_date)) as cursor:
                    records = []
                    async for row in cursor:
                        record = BillingRecord(
                            record_id=row[0],
                            user_id=row[1],
                            instance_id=row[2],
                            instance_type=InstanceType(row[3]),
                            start_time=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            end_time=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                            duration_minutes=row[6],
                            cost_per_minute=row[7],
                            total_cost=row[8],
                            billing_tags=json.loads(row[9]) if row[9] else {}
                        )
                        records.append(record)
                    return records
        except Exception as e:
            self.logger.error(f"Error getting all billing records: {e}")
            return []
    
    # Additional helper methods would continue here...
    # For brevity, I'll add a few key ones
    
    async def create_scaling_event(self, event: ScalingEvent) -> bool:
        """Create a scaling event record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO scaling_events
                    (event_id, user_id, event_type, trigger_metric, trigger_value,
                     scaling_action, instances_before, instances_after, timestamp,
                     success, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.user_id, event.event_type.value,
                    event.trigger_metric, event.trigger_value, event.scaling_action,
                    event.instances_before, event.instances_after, event.timestamp,
                    event.success, event.error_message
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating scaling event: {e}")
            return False
    
    async def get_recent_scaling_events(self, user_id: str, hours: int = 24) -> List[ScalingEvent]:
        """Get recent scaling events for a user"""
        try:
            cutoff_time = current_timestamp() - datetime.timedelta(hours=hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT event_id, user_id, event_type, trigger_metric, trigger_value,
                           scaling_action, instances_before, instances_after, timestamp,
                           success, error_message
                    FROM scaling_events 
                    WHERE user_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                """, (user_id, cutoff_time)) as cursor:
                    events = []
                    async for row in cursor:
                        event = ScalingEvent(
                            event_id=row[0],
                            user_id=row[1],
                            event_type=EventType(row[2]),
                            trigger_metric=row[3],
                            trigger_value=row[4],
                            scaling_action=row[5],
                            instances_before=row[6],
                            instances_after=row[7],
                            timestamp=datetime.fromisoformat(row[8]) if isinstance(row[8], str) else row[8],
                            success=bool(row[9]),
                            error_message=row[10]
                        )
                        events.append(event)
                    return events
        except Exception as e:
            self.logger.error(f"Error getting scaling events: {e}")
            return []
    
    async def create_game_night_event(self, event: GameNightEvent) -> bool:
        """Create a game night event"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO game_night_events
                    (event_id, user_id, name, start_time, duration_hours,
                     expected_players, scale_multiplier, pre_scale_instances, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.event_id, event.user_id, event.name, event.start_time,
                    event.duration_hours, event.expected_players, event.scale_multiplier,
                    event.pre_scale_instances, event.active
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating game night event: {e}")
            return False
    
    async def get_active_game_night_events(self, user_id: str) -> List[GameNightEvent]:
        """Get active game night events for user"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT event_id, user_id, name, start_time, duration_hours,
                           expected_players, scale_multiplier, pre_scale_instances, active
                    FROM game_night_events
                    WHERE user_id = ? AND active = 1
                    ORDER BY start_time ASC
                """, (user_id,)) as cursor:
                    events = []
                    async for row in cursor:
                        event = GameNightEvent(
                            event_id=row[0],
                            user_id=row[1],
                            name=row[2],
                            start_time=datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3],
                            duration_hours=row[4],
                            expected_players=row[5],
                            scale_multiplier=row[6],
                            pre_scale_instances=row[7],
                            active=bool(row[8])
                        )
                        events.append(event)
                    return events
        except Exception as e:
            self.logger.error(f"Error getting active game night events: {e}")
            return []
    
    async def update_game_night_event(self, event: GameNightEvent) -> bool:
        """Update game night event"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE game_night_events SET
                        name = ?, start_time = ?, duration_hours = ?,
                        expected_players = ?, scale_multiplier = ?,
                        pre_scale_instances = ?, active = ?
                    WHERE event_id = ?
                """, (
                    event.name, event.start_time, event.duration_hours,
                    event.expected_players, event.scale_multiplier,
                    event.pre_scale_instances, event.active, event.event_id
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating game night event: {e}")
            return False
    
    # Placeholder methods for isolation and API key management
    # (Would implement these based on the models)
    
    async def save_user_isolation_info(self, isolation_info: UserIsolationInfo) -> bool:
        """Save user isolation configuration"""
        # Implementation would save to a separate table
        return True
    
    async def get_user_isolation_info(self, user_id: str) -> Optional[UserIsolationInfo]:
        """Get user isolation configuration"""
        # Implementation would retrieve from isolation table
        return None
    
    async def create_api_key(self, api_key: APIKey) -> bool:
        """Create API key record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO api_keys
                    (key_id, user_id, key_hash, name, permissions, created_at,
                     expires_at, last_used_at, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    api_key.key_id, api_key.user_id, api_key.key_hash,
                    api_key.name, json.dumps(api_key.permissions),
                    api_key.created_at, api_key.expires_at,
                    api_key.last_used_at, api_key.active
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating API key: {e}")
            return False
    
    async def get_api_key_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT key_id, user_id, key_hash, name, permissions, created_at,
                           expires_at, last_used_at, active
                    FROM api_keys WHERE key_hash = ?
                """, (key_hash,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return APIKey(
                            key_id=row[0],
                            user_id=row[1],
                            key_hash=row[2],
                            name=row[3],
                            permissions=json.loads(row[4]),
                            created_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                            expires_at=datetime.fromisoformat(row[6]) if row[6] else None,
                            last_used_at=datetime.fromisoformat(row[7]) if row[7] else None,
                            active=bool(row[8])
                        )
                    return None
        except Exception as e:
            self.logger.error(f"Error getting API key by hash: {e}")
            return None
    
    async def update_api_key(self, api_key: APIKey) -> bool:
        """Update API key"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE api_keys SET
                        last_used_at = ?, active = ?
                    WHERE key_id = ?
                """, (api_key.last_used_at, api_key.active, api_key.key_id))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating API key: {e}")
            return False
    
    # Utility methods
    async def store_usage_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Store usage metrics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO system_metrics (timestamp, metric_name, metric_value, tags)
                    VALUES (?, ?, ?, ?)
                """, (
                    metrics['timestamp'], 'usage_metrics', 0,
                    json.dumps(metrics)
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error storing usage metrics: {e}")
            return False
    
    async def get_latest_usage_metrics(self, instance_id: str) -> Optional[Dict[str, Any]]:
        """Get latest usage metrics for instance"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT tags FROM system_metrics 
                    WHERE metric_name = 'usage_metrics' 
                    AND json_extract(tags, '$.instance_id') = ?
                    ORDER BY timestamp DESC LIMIT 1
                """, (instance_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return json.loads(row[0])
                    return None
        except Exception as e:
            self.logger.error(f"Error getting latest usage metrics: {e}")
            return None
    
    async def cleanup_old_data(self, retention_days: int = 90):
        """Cleanup old data beyond retention period"""
        try:
            cutoff_date = current_timestamp() - datetime.timedelta(days=retention_days)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Clean old billing records
                await db.execute("""
                    DELETE FROM billing_records WHERE start_time < ?
                """, (cutoff_date,))
                
                # Clean old system metrics
                await db.execute("""
                    DELETE FROM system_metrics WHERE timestamp < ?
                """, (cutoff_date,))
                
                # Clean old scaling events
                await db.execute("""
                    DELETE FROM scaling_events WHERE timestamp < ?
                """, (cutoff_date,))
                
                await db.commit()
                
            self.logger.info(f"Cleaned up data older than {retention_days} days")
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
    
    # Enterprise Organization Management Methods
    async def create_organization(self, organization: Organization) -> bool:
        """Create a new organization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO organizations 
                    (org_id, name, tier, owner_user_id, created_at, sso_enabled,
                     audit_logging, compliance_mode, billing_account_id, cost_center, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    organization.org_id, organization.name, organization.tier.value,
                    organization.owner_user_id, organization.created_at, organization.sso_enabled,
                    organization.audit_logging, organization.compliance_mode,
                    organization.billing_account_id, organization.cost_center,
                    json.dumps(organization.tags)
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating organization: {e}")
            return False

    async def get_organization(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT org_id, name, tier, owner_user_id, created_at, sso_enabled,
                           audit_logging, compliance_mode, billing_account_id, cost_center, tags
                    FROM organizations WHERE org_id = ?
                """, (org_id,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        return Organization(
                            org_id=row[0],
                            name=row[1],
                            tier=OrganizationTier(row[2]),
                            owner_user_id=row[3],
                            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            sso_enabled=bool(row[5]),
                            audit_logging=bool(row[6]),
                            compliance_mode=row[7],
                            billing_account_id=row[8],
                            cost_center=row[9],
                            tags=json.loads(row[10]) if row[10] else {}
                        )
                    return None
        except Exception as e:
            self.logger.error(f"Error getting organization: {e}")
            return None

    async def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get all organizations where user is a member"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT DISTINCT o.org_id, o.name, o.tier, o.owner_user_id, o.created_at, 
                           o.sso_enabled, o.audit_logging, o.compliance_mode, 
                           o.billing_account_id, o.cost_center, o.tags
                    FROM organizations o
                    LEFT JOIN organization_members om ON o.org_id = om.org_id
                    WHERE o.owner_user_id = ? OR (om.user_id = ? AND om.active = 1)
                """, (user_id, user_id)) as cursor:
                    orgs = []
                    async for row in cursor:
                        org = Organization(
                            org_id=row[0],
                            name=row[1],
                            tier=OrganizationTier(row[2]),
                            owner_user_id=row[3],
                            created_at=datetime.fromisoformat(row[4]) if isinstance(row[4], str) else row[4],
                            sso_enabled=bool(row[5]),
                            audit_logging=bool(row[6]),
                            compliance_mode=row[7],
                            billing_account_id=row[8],
                            cost_center=row[9],
                            tags=json.loads(row[10]) if row[10] else {}
                        )
                        orgs.append(org)
                    return orgs
        except Exception as e:
            self.logger.error(f"Error getting user organizations: {e}")
            return []

    async def create_department(self, department: Department) -> bool:
        """Create a new department"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO departments
                    (dept_id, org_id, name, manager_user_id, budget_limit, 
                     cost_center, created_at, active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    department.dept_id, department.org_id, department.name,
                    department.manager_user_id, department.budget_limit,
                    department.cost_center, department.created_at, department.active
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating department: {e}")
            return False

    async def get_organization_departments(self, org_id: str) -> List[Department]:
        """Get all departments in an organization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT dept_id, org_id, name, manager_user_id, budget_limit,
                           cost_center, created_at, active
                    FROM departments WHERE org_id = ? AND active = 1
                    ORDER BY name
                """, (org_id,)) as cursor:
                    departments = []
                    async for row in cursor:
                        dept = Department(
                            dept_id=row[0],
                            org_id=row[1],
                            name=row[2],
                            manager_user_id=row[3],
                            budget_limit=row[4],
                            cost_center=row[5],
                            created_at=datetime.fromisoformat(row[6]) if isinstance(row[6], str) else row[6],
                            active=bool(row[7])
                        )
                        departments.append(dept)
                    return departments
        except Exception as e:
            self.logger.error(f"Error getting organization departments: {e}")
            return []

    async def create_project(self, project: Project) -> bool:
        """Create a new project"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO projects
                    (project_id, dept_id, name, description, owner_user_id, 
                     budget_limit, cost_center, created_at, archived, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project.project_id, project.dept_id, project.name, project.description,
                    project.owner_user_id, project.budget_limit, project.cost_center,
                    project.created_at, project.archived, json.dumps(project.tags)
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating project: {e}")
            return False

    async def get_department_projects(self, dept_id: str) -> List[Project]:
        """Get all projects in a department"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT project_id, dept_id, name, description, owner_user_id,
                           budget_limit, cost_center, created_at, archived, tags
                    FROM projects WHERE dept_id = ? AND archived = 0
                    ORDER BY name
                """, (dept_id,)) as cursor:
                    projects = []
                    async for row in cursor:
                        project = Project(
                            project_id=row[0],
                            dept_id=row[1],
                            name=row[2],
                            description=row[3],
                            owner_user_id=row[4],
                            budget_limit=row[5],
                            cost_center=row[6],
                            created_at=datetime.fromisoformat(row[7]) if isinstance(row[7], str) else row[7],
                            archived=bool(row[8]),
                            tags=json.loads(row[9]) if row[9] else {}
                        )
                        projects.append(project)
                    return projects
        except Exception as e:
            self.logger.error(f"Error getting department projects: {e}")
            return []

    async def add_organization_member(self, member: OrganizationMember) -> bool:
        """Add a member to an organization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO organization_members
                    (member_id, org_id, user_id, role, dept_id, joined_at, active, permissions)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    member.member_id, member.org_id, member.user_id, member.role.value,
                    member.dept_id, member.joined_at, member.active, json.dumps(member.permissions)
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error adding organization member: {e}")
            return False

    async def get_organization_members(self, org_id: str) -> List[OrganizationMember]:
        """Get all members of an organization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT member_id, org_id, user_id, role, dept_id, joined_at, active, permissions
                    FROM organization_members WHERE org_id = ? AND active = 1
                """, (org_id,)) as cursor:
                    members = []
                    async for row in cursor:
                        member = OrganizationMember(
                            member_id=row[0],
                            org_id=row[1],
                            user_id=row[2],
                            role=OrganizationRole(row[3]),
                            dept_id=row[4],
                            joined_at=datetime.fromisoformat(row[5]) if isinstance(row[5], str) else row[5],
                            active=bool(row[6]),
                            permissions=json.loads(row[7]) if row[7] else []
                        )
                        members.append(member)
                    return members
        except Exception as e:
            self.logger.error(f"Error getting organization members: {e}")
            return []

    async def create_approval_request(self, request: ApprovalRequest) -> bool:
        """Create an approval request"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO approval_requests
                    (request_id, org_id, requester_user_id, approver_user_id, resource_type,
                     resource_config, justification, status, estimated_cost, created_at,
                     reviewed_at, comments)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request.request_id, request.org_id, request.requester_user_id,
                    request.approver_user_id, request.resource_type, json.dumps(request.resource_config),
                    request.justification, request.status.value, request.estimated_cost,
                    request.created_at, request.reviewed_at, request.comments
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error creating approval request: {e}")
            return False

    async def get_pending_approval_requests(self, org_id: str) -> List[ApprovalRequest]:
        """Get pending approval requests for an organization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT request_id, org_id, requester_user_id, approver_user_id, resource_type,
                           resource_config, justification, status, estimated_cost, created_at,
                           reviewed_at, comments
                    FROM approval_requests 
                    WHERE org_id = ? AND status = 'pending'
                    ORDER BY created_at ASC
                """, (org_id,)) as cursor:
                    requests = []
                    async for row in cursor:
                        request = ApprovalRequest(
                            request_id=row[0],
                            org_id=row[1],
                            requester_user_id=row[2],
                            approver_user_id=row[3],
                            resource_type=row[4],
                            resource_config=json.loads(row[5]),
                            justification=row[6],
                            status=ApprovalStatus(row[7]),
                            estimated_cost=row[8],
                            created_at=datetime.fromisoformat(row[9]) if isinstance(row[9], str) else row[9],
                            reviewed_at=datetime.fromisoformat(row[10]) if row[10] else None,
                            comments=row[11]
                        )
                        requests.append(request)
                    return requests
        except Exception as e:
            self.logger.error(f"Error getting pending approval requests: {e}")
            return []

    async def update_approval_request(self, request: ApprovalRequest) -> bool:
        """Update an approval request"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE approval_requests SET
                        approver_user_id = ?, status = ?, reviewed_at = ?, comments = ?
                    WHERE request_id = ?
                """, (
                    request.approver_user_id, request.status.value, request.reviewed_at,
                    request.comments, request.request_id
                ))
                await db.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error updating approval request: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Database health check"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Test basic connectivity
                await db.execute("SELECT 1")
                
                # Get database size
                db_path = Path(self.db_path)
                db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0
                
                # Count records in main tables
                async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                    user_count = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM ec2_instances") as cursor:
                    instance_count = (await cursor.fetchone())[0]
                
                async with db.execute("SELECT COUNT(*) FROM billing_records") as cursor:
                    billing_count = (await cursor.fetchone())[0]
                
                # Count enterprise tables if they exist
                try:
                    async with db.execute("SELECT COUNT(*) FROM organizations") as cursor:
                        org_count = (await cursor.fetchone())[0]
                except:
                    org_count = 0
                
                return {
                    'service': 'database_manager',
                    'healthy': True,
                    'database_size_mb': round(db_size_mb, 2),
                    'user_count': user_count,
                    'instance_count': instance_count,
                    'billing_records': billing_count,
                    'organization_count': org_count,
                    'timestamp': current_timestamp().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return {
                'service': 'database_manager',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }