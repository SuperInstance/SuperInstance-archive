"""
Database manager for notification service
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncpg
from asyncpg.pool import Pool

from .config import settings
from .logging import logger

class DatabaseManager:
    """Manages database connections and notification data"""
    
    def __init__(self):
        self.pool: Optional[Pool] = None
        
    async def initialize(self):
        """Initialize database connection and create tables"""
        try:
            # Create connection pool
            self.pool = await asyncpg.create_pool(
                settings.DATABASE_URL,
                min_size=5,
                max_size=20,
                max_inactive_connection_lifetime=300
            )
            
            logger.info("Database connection pool created")
            
            # Create tables
            await self._create_tables()
            
            logger.info("Database initialization completed")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def _create_tables(self):
        """Create all required tables"""
        async with self.pool.acquire() as conn:
            # Notification templates table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_templates (
                    id SERIAL PRIMARY KEY,
                    template_id VARCHAR(255) UNIQUE NOT NULL,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    type VARCHAR(100) NOT NULL,
                    subject_template TEXT,
                    body_template TEXT NOT NULL,
                    sms_template TEXT,
                    variables JSONB DEFAULT '{}',
                    is_system BOOLEAN DEFAULT FALSE,
                    tenant_id VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    is_active BOOLEAN DEFAULT TRUE
                )
            """)
            
            # User notification preferences table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS notification_preferences (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    notification_type VARCHAR(100) NOT NULL,
                    email_enabled BOOLEAN DEFAULT TRUE,
                    inapp_enabled BOOLEAN DEFAULT TRUE,
                    sms_enabled BOOLEAN DEFAULT FALSE,
                    webhook_enabled BOOLEAN DEFAULT FALSE,
                    digest_frequency VARCHAR(50) DEFAULT 'daily',
                    quiet_hours_start TIME,
                    quiet_hours_end TIME,
                    timezone VARCHAR(100) DEFAULT 'UTC',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(user_id, notification_type)
                )
            """)
            
            # In-app notifications table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS inapp_notifications (
                    id BIGSERIAL PRIMARY KEY,
                    notification_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    type VARCHAR(100) NOT NULL,
                    title VARCHAR(500) NOT NULL,
                    message TEXT NOT NULL,
                    data JSONB DEFAULT '{}',
                    priority INTEGER DEFAULT 2,
                    is_read BOOLEAN DEFAULT FALSE,
                    read_at TIMESTAMP WITH TIME ZONE,
                    expires_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Email notifications log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS email_notifications (
                    id BIGSERIAL PRIMARY KEY,
                    notification_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    to_email VARCHAR(255) NOT NULL,
                    from_email VARCHAR(255) NOT NULL,
                    subject VARCHAR(500) NOT NULL,
                    body TEXT NOT NULL,
                    template_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'pending',
                    provider VARCHAR(50),
                    provider_message_id VARCHAR(255),
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # SMS notifications log table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sms_notifications (
                    id BIGSERIAL PRIMARY KEY,
                    notification_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    to_phone VARCHAR(50) NOT NULL,
                    message TEXT NOT NULL,
                    template_id VARCHAR(255),
                    status VARCHAR(50) DEFAULT 'pending',
                    provider VARCHAR(50),
                    provider_message_id VARCHAR(255),
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Webhook notifications table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_notifications (
                    id BIGSERIAL PRIMARY KEY,
                    notification_id VARCHAR(255) UNIQUE NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    webhook_url TEXT NOT NULL,
                    payload JSONB NOT NULL,
                    headers JSONB DEFAULT '{}',
                    status VARCHAR(50) DEFAULT 'pending',
                    response_status INTEGER,
                    response_body TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Digest queue table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS digest_queue (
                    id BIGSERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    digest_type VARCHAR(100) NOT NULL,
                    notifications JSONB NOT NULL,
                    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
                    status VARCHAR(50) DEFAULT 'pending',
                    sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Webhook endpoints table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS webhook_endpoints (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR(255) NOT NULL,
                    tenant_id VARCHAR(255),
                    name VARCHAR(255) NOT NULL,
                    url TEXT NOT NULL,
                    secret_key VARCHAR(255),
                    notification_types TEXT[] DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Create indexes for better performance
            await self._create_indexes(conn)
            
            logger.info("Database tables created successfully")
    
    async def _create_indexes(self, conn):
        """Create database indexes for optimal performance"""
        indexes = [
            # Notification templates indexes
            "CREATE INDEX IF NOT EXISTS idx_templates_type ON notification_templates(type)",
            "CREATE INDEX IF NOT EXISTS idx_templates_tenant ON notification_templates(tenant_id)",
            
            # User preferences indexes
            "CREATE INDEX IF NOT EXISTS idx_preferences_user ON notification_preferences(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_preferences_user_type ON notification_preferences(user_id, notification_type)",
            
            # In-app notifications indexes
            "CREATE INDEX IF NOT EXISTS idx_inapp_user ON inapp_notifications(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_inapp_unread ON inapp_notifications(user_id, is_read, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_inapp_expires ON inapp_notifications(expires_at)",
            
            # Email notifications indexes
            "CREATE INDEX IF NOT EXISTS idx_email_user ON email_notifications(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_email_status ON email_notifications(status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_email_retry ON email_notifications(status, retry_count)",
            
            # SMS notifications indexes
            "CREATE INDEX IF NOT EXISTS idx_sms_user ON sms_notifications(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_sms_status ON sms_notifications(status, created_at DESC)",
            
            # Webhook notifications indexes
            "CREATE INDEX IF NOT EXISTS idx_webhook_user ON webhook_notifications(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_webhook_status ON webhook_notifications(status, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_webhook_retry ON webhook_notifications(status, retry_count)",
            
            # Digest queue indexes
            "CREATE INDEX IF NOT EXISTS idx_digest_user ON digest_queue(user_id, digest_type)",
            "CREATE INDEX IF NOT EXISTS idx_digest_scheduled ON digest_queue(scheduled_for, status)",
            
            # Webhook endpoints indexes
            "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON webhook_endpoints(user_id, is_active)",
        ]
        
        for index_sql in indexes:
            try:
                await conn.execute(index_sql)
            except Exception as e:
                logger.warning(f"Could not create index: {e}")
    
    async def execute_query(self, query: str, *args) -> List[Dict]:
        """Execute a query and return results as dictionaries"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]
    
    async def execute_scalar(self, query: str, *args) -> Any:
        """Execute a query and return a single value"""
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)
    
    async def execute_command(self, query: str, *args) -> str:
        """Execute a command (INSERT, UPDATE, DELETE)"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def execute_many(self, query: str, data: List[tuple]) -> None:
        """Execute a query with multiple parameter sets"""
        async with self.pool.acquire() as conn:
            await conn.executemany(query, data)
    
    async def health_check(self) -> bool:
        """Check database health"""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def cleanup_old_notifications(self, days_to_keep: int = 30):
        """Clean up old notification records"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            # Clean up old in-app notifications
            result = await self.execute_command(
                "DELETE FROM inapp_notifications WHERE created_at < $1 AND is_read = TRUE",
                cutoff_date
            )
            logger.info(f"Cleaned up old in-app notifications: {result}")
            
            # Clean up old email logs
            result = await self.execute_command(
                "DELETE FROM email_notifications WHERE created_at < $1 AND status IN ('sent', 'failed')",
                cutoff_date
            )
            logger.info(f"Cleaned up old email notifications: {result}")
            
            # Clean up old SMS logs
            result = await self.execute_command(
                "DELETE FROM sms_notifications WHERE created_at < $1 AND status IN ('sent', 'failed')",
                cutoff_date
            )
            logger.info(f"Cleaned up old SMS notifications: {result}")
            
            # Clean up old webhook logs
            result = await self.execute_command(
                "DELETE FROM webhook_notifications WHERE created_at < $1 AND status IN ('sent', 'failed')",
                cutoff_date
            )
            logger.info(f"Cleaned up old webhook notifications: {result}")
            
            # Clean up expired notifications
            result = await self.execute_command(
                "DELETE FROM inapp_notifications WHERE expires_at < NOW()"
            )
            logger.info(f"Cleaned up expired notifications: {result}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old notifications: {e}")
    
    async def get_notification_stats(self) -> Dict:
        """Get notification statistics"""
        try:
            stats = {}
            
            # Get counts by table
            tables = [
                'notification_templates',
                'notification_preferences', 
                'inapp_notifications',
                'email_notifications',
                'sms_notifications',
                'webhook_notifications',
                'digest_queue',
                'webhook_endpoints'
            ]
            
            for table in tables:
                count = await self.execute_scalar(f"SELECT COUNT(*) FROM {table}")
                stats[table] = count
            
            # Get status breakdown for recent notifications (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            
            # Email status breakdown
            email_stats = await self.execute_query("""
                SELECT status, COUNT(*) as count
                FROM email_notifications 
                WHERE created_at >= $1
                GROUP BY status
            """, cutoff)
            stats["email_status_24h"] = {row["status"]: row["count"] for row in email_stats}
            
            # SMS status breakdown
            sms_stats = await self.execute_query("""
                SELECT status, COUNT(*) as count
                FROM sms_notifications 
                WHERE created_at >= $1
                GROUP BY status
            """, cutoff)
            stats["sms_status_24h"] = {row["status"]: row["count"] for row in sms_stats}
            
            # Webhook status breakdown
            webhook_stats = await self.execute_query("""
                SELECT status, COUNT(*) as count
                FROM webhook_notifications 
                WHERE created_at >= $1
                GROUP BY status
            """, cutoff)
            stats["webhook_status_24h"] = {row["status"]: row["count"] for row in webhook_stats}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {}
    
    async def close(self):
        """Close database connections"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connections closed")