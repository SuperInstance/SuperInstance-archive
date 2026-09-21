#!/usr/bin/env python3
"""
ActiveLog Business Metrics Exporter for Prometheus

Collects and exports business metrics to Prometheus including:
- User registrations and activity
- Revenue and subscription metrics
- Feature usage statistics
- API usage patterns
- Custom business KPIs
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import asyncpg
from aiohttp import web
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, CollectorRegistry, 
    generate_latest, CONTENT_TYPE_LATEST
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BusinessMetricsCollector:
    """Collects business metrics from ActiveLog database"""
    
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.db_pool = None
        
        # Create custom registry
        self.registry = CollectorRegistry()
        
        # User Metrics
        self.user_registrations = Counter(
            'activelog_user_registrations_total',
            'Total number of user registrations',
            ['source', 'plan_type'],
            registry=self.registry
        )
        
        self.active_users = Gauge(
            'activelog_active_users',
            'Number of active users',
            ['period'],
            registry=self.registry
        )
        
        self.user_retention = Gauge(
            'activelog_user_retention_rate',
            'User retention rate',
            ['period'],
            registry=self.registry
        )
        
        # Revenue Metrics
        self.revenue = Counter(
            'activelog_revenue_total',
            'Total revenue in cents',
            ['plan_type', 'payment_method'],
            registry=self.registry
        )
        
        self.monthly_recurring_revenue = Gauge(
            'activelog_mrr_total',
            'Monthly Recurring Revenue in cents',
            registry=self.registry
        )
        
        self.average_revenue_per_user = Gauge(
            'activelog_arpu',
            'Average Revenue Per User in cents',
            ['period'],
            registry=self.registry
        )
        
        self.churn_rate = Gauge(
            'activelog_churn_rate',
            'Customer churn rate',
            ['period'],
            registry=self.registry
        )
        
        # Subscription Metrics
        self.active_subscriptions = Gauge(
            'activelog_active_subscriptions',
            'Number of active subscriptions',
            ['plan_type'],
            registry=self.registry
        )
        
        self.subscription_upgrades = Counter(
            'activelog_subscription_upgrades_total',
            'Total subscription upgrades',
            ['from_plan', 'to_plan'],
            registry=self.registry
        )
        
        self.subscription_cancellations = Counter(
            'activelog_subscription_cancellations_total',
            'Total subscription cancellations',
            ['plan_type', 'reason'],
            registry=self.registry
        )
        
        # Feature Usage Metrics
        self.feature_usage = Counter(
            'activelog_feature_usage_total',
            'Feature usage count',
            ['feature', 'user_plan'],
            registry=self.registry
        )
        
        self.api_usage = Counter(
            'activelog_api_calls_total',
            'API calls made by users',
            ['endpoint', 'method', 'plan_type'],
            registry=self.registry
        )
        
        self.storage_usage = Histogram(
            'activelog_storage_usage_bytes',
            'Storage usage per user in bytes',
            ['plan_type'],
            registry=self.registry
        )
        
        # Business KPIs
        self.trial_conversion_rate = Gauge(
            'activelog_trial_conversion_rate',
            'Trial to paid conversion rate',
            registry=self.registry
        )
        
        self.customer_acquisition_cost = Gauge(
            'activelog_customer_acquisition_cost',
            'Customer acquisition cost in cents',
            ['channel'],
            registry=self.registry
        )
        
        self.lifetime_value = Gauge(
            'activelog_customer_lifetime_value',
            'Customer lifetime value in cents',
            ['cohort'],
            registry=self.registry
        )
        
        # Support Metrics
        self.support_tickets = Counter(
            'activelog_support_tickets_total',
            'Total support tickets',
            ['priority', 'category'],
            registry=self.registry
        )
        
        self.support_resolution_time = Histogram(
            'activelog_support_resolution_time_hours',
            'Support ticket resolution time in hours',
            ['priority'],
            registry=self.registry
        )
    
    async def initialize(self):
        """Initialize database connection"""
        try:
            self.db_pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def collect_metrics(self):
        """Collect all business metrics"""
        if not self.db_pool:
            logger.warning("Database pool not initialized")
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Collect user metrics
                await self._collect_user_metrics(conn)
                
                # Collect revenue metrics
                await self._collect_revenue_metrics(conn)
                
                # Collect subscription metrics
                await self._collect_subscription_metrics(conn)
                
                # Collect feature usage metrics
                await self._collect_feature_usage_metrics(conn)
                
                # Collect business KPIs
                await self._collect_business_kpis(conn)
                
                # Collect support metrics
                await self._collect_support_metrics(conn)
                
                logger.info("Business metrics collected successfully")
                
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    async def _collect_user_metrics(self, conn):
        """Collect user-related metrics"""
        # Active users (last 7 days, 30 days)
        for period_days, label in [(7, '7d'), (30, '30d')]:
            query = """
                SELECT COUNT(DISTINCT user_id) 
                FROM user_activity 
                WHERE last_active_at > NOW() - INTERVAL '%s days'
            """ % period_days
            
            count = await conn.fetchval(query)
            self.active_users.labels(period=label).set(count or 0)
        
        # User registrations by source and plan
        query = """
            SELECT registration_source, initial_plan, COUNT(*) 
            FROM users 
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY registration_source, initial_plan
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.user_registrations.labels(
                source=row['registration_source'] or 'unknown',
                plan_type=row['initial_plan'] or 'free'
            ).inc(row['count'])
        
        # User retention rates
        for period_days, label in [(7, '7d'), (30, '30d')]:
            query = """
                WITH registered_users AS (
                    SELECT user_id, created_at
                    FROM users 
                    WHERE created_at <= NOW() - INTERVAL '%s days'
                      AND created_at > NOW() - INTERVAL '%s days'
                ),
                active_users AS (
                    SELECT DISTINCT user_id
                    FROM user_activity
                    WHERE last_active_at > NOW() - INTERVAL '1 day'
                )
                SELECT 
                    COUNT(DISTINCT r.user_id) as registered,
                    COUNT(DISTINCT a.user_id) as retained
                FROM registered_users r
                LEFT JOIN active_users a ON r.user_id = a.user_id
            """ % (period_days, period_days + 1)
            
            row = await conn.fetchrow(query)
            if row['registered'] > 0:
                retention_rate = row['retained'] / row['registered']
                self.user_retention.labels(period=label).set(retention_rate)
    
    async def _collect_revenue_metrics(self, conn):
        """Collect revenue-related metrics"""
        # Revenue by plan and payment method (last hour)
        query = """
            SELECT plan_type, payment_method, SUM(amount_cents)
            FROM payments 
            WHERE created_at > NOW() - INTERVAL '1 hour'
              AND status = 'completed'
            GROUP BY plan_type, payment_method
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.revenue.labels(
                plan_type=row['plan_type'],
                payment_method=row['payment_method']
            ).inc(row['sum'] or 0)
        
        # Monthly Recurring Revenue
        query = """
            SELECT SUM(monthly_amount_cents) as mrr
            FROM subscriptions 
            WHERE status = 'active'
        """
        
        mrr = await conn.fetchval(query)
        self.monthly_recurring_revenue.set(mrr or 0)
        
        # Average Revenue Per User
        for period_days, label in [(30, '30d'), (90, '90d')]:
            query = """
                WITH period_revenue AS (
                    SELECT SUM(amount_cents) as total_revenue
                    FROM payments 
                    WHERE created_at > NOW() - INTERVAL '%s days'
                      AND status = 'completed'
                ),
                period_users AS (
                    SELECT COUNT(DISTINCT user_id) as total_users
                    FROM user_activity
                    WHERE last_active_at > NOW() - INTERVAL '%s days'
                )
                SELECT 
                    COALESCE(pr.total_revenue, 0) / GREATEST(pu.total_users, 1) as arpu
                FROM period_revenue pr, period_users pu
            """ % (period_days, period_days)
            
            arpu = await conn.fetchval(query)
            self.average_revenue_per_user.labels(period=label).set(arpu or 0)
        
        # Churn rate
        for period_days, label in [(30, '30d'), (90, '90d')]:
            query = """
                WITH period_start_users AS (
                    SELECT COUNT(DISTINCT user_id) as start_users
                    FROM subscriptions
                    WHERE created_at <= NOW() - INTERVAL '%s days'
                      AND status = 'active'
                ),
                churned_users AS (
                    SELECT COUNT(DISTINCT user_id) as churned
                    FROM subscriptions
                    WHERE cancelled_at > NOW() - INTERVAL '%s days'
                      AND cancelled_at <= NOW()
                )
                SELECT 
                    COALESCE(cu.churned, 0)::float / GREATEST(psu.start_users, 1) as churn_rate
                FROM period_start_users psu, churned_users cu
            """ % (period_days, period_days)
            
            churn_rate = await conn.fetchval(query)
            self.churn_rate.labels(period=label).set(churn_rate or 0)
    
    async def _collect_subscription_metrics(self, conn):
        """Collect subscription-related metrics"""
        # Active subscriptions by plan type
        query = """
            SELECT plan_type, COUNT(*) 
            FROM subscriptions 
            WHERE status = 'active'
            GROUP BY plan_type
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.active_subscriptions.labels(
                plan_type=row['plan_type']
            ).set(row['count'])
        
        # Subscription upgrades (last hour)
        query = """
            SELECT from_plan, to_plan, COUNT(*)
            FROM subscription_changes
            WHERE created_at > NOW() - INTERVAL '1 hour'
              AND change_type = 'upgrade'
            GROUP BY from_plan, to_plan
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.subscription_upgrades.labels(
                from_plan=row['from_plan'],
                to_plan=row['to_plan']
            ).inc(row['count'])
        
        # Subscription cancellations (last hour)
        query = """
            SELECT plan_type, cancellation_reason, COUNT(*)
            FROM subscriptions
            WHERE cancelled_at > NOW() - INTERVAL '1 hour'
            GROUP BY plan_type, cancellation_reason
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.subscription_cancellations.labels(
                plan_type=row['plan_type'],
                reason=row['cancellation_reason'] or 'unknown'
            ).inc(row['count'])
    
    async def _collect_feature_usage_metrics(self, conn):
        """Collect feature usage metrics"""
        # Feature usage (last hour)
        query = """
            SELECT f.feature_name, u.current_plan, COUNT(*)
            FROM feature_usage f
            JOIN users u ON f.user_id = u.user_id
            WHERE f.created_at > NOW() - INTERVAL '1 hour'
            GROUP BY f.feature_name, u.current_plan
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.feature_usage.labels(
                feature=row['feature_name'],
                user_plan=row['current_plan']
            ).inc(row['count'])
        
        # API usage (last hour)
        query = """
            SELECT a.endpoint, a.method, u.current_plan, COUNT(*)
            FROM api_logs a
            JOIN users u ON a.user_id = u.user_id
            WHERE a.created_at > NOW() - INTERVAL '1 hour'
            GROUP BY a.endpoint, a.method, u.current_plan
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.api_usage.labels(
                endpoint=row['endpoint'],
                method=row['method'],
                plan_type=row['current_plan']
            ).inc(row['count'])
        
        # Storage usage distribution
        query = """
            SELECT u.current_plan, s.storage_bytes
            FROM storage_usage s
            JOIN users u ON s.user_id = u.user_id
            WHERE s.updated_at > NOW() - INTERVAL '1 hour'
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.storage_usage.labels(
                plan_type=row['current_plan']
            ).observe(row['storage_bytes'] or 0)
    
    async def _collect_business_kpis(self, conn):
        """Collect business KPIs"""
        # Trial conversion rate
        query = """
            WITH trial_users AS (
                SELECT COUNT(*) as total_trials
                FROM users 
                WHERE initial_plan = 'trial'
                  AND created_at > NOW() - INTERVAL '30 days'
            ),
            converted_users AS (
                SELECT COUNT(*) as total_converted
                FROM subscriptions s
                JOIN users u ON s.user_id = u.user_id
                WHERE u.initial_plan = 'trial'
                  AND s.plan_type != 'trial'
                  AND s.created_at > u.created_at
                  AND u.created_at > NOW() - INTERVAL '30 days'
            )
            SELECT 
                COALESCE(cu.total_converted, 0)::float / GREATEST(tu.total_trials, 1) as conversion_rate
            FROM trial_users tu, converted_users cu
        """
        
        conversion_rate = await conn.fetchval(query)
        self.trial_conversion_rate.set(conversion_rate or 0)
        
        # Customer Acquisition Cost by channel
        query = """
            SELECT 
                acquisition_channel,
                COALESCE(SUM(marketing_spend_cents), 0) / GREATEST(COUNT(*), 1) as cac
            FROM users u
            LEFT JOIN marketing_spend m ON m.channel = u.acquisition_channel
            WHERE u.created_at > NOW() - INTERVAL '30 days'
              AND m.date >= NOW() - INTERVAL '30 days'
            GROUP BY acquisition_channel
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.customer_acquisition_cost.labels(
                channel=row['acquisition_channel'] or 'unknown'
            ).set(row['cac'] or 0)
    
    async def _collect_support_metrics(self, conn):
        """Collect support metrics"""
        # Support tickets (last hour)
        query = """
            SELECT priority, category, COUNT(*)
            FROM support_tickets
            WHERE created_at > NOW() - INTERVAL '1 hour'
            GROUP BY priority, category
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.support_tickets.labels(
                priority=row['priority'],
                category=row['category']
            ).inc(row['count'])
        
        # Support resolution times
        query = """
            SELECT 
                priority,
                EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600 as hours
            FROM support_tickets
            WHERE resolved_at IS NOT NULL
              AND resolved_at > NOW() - INTERVAL '24 hours'
        """
        
        rows = await conn.fetch(query)
        for row in rows:
            self.support_resolution_time.labels(
                priority=row['priority']
            ).observe(row['hours'] or 0)
    
    def get_metrics(self):
        """Get metrics in Prometheus format"""
        return generate_latest(self.registry)

class BusinessMetricsServer:
    """HTTP server for exposing business metrics"""
    
    def __init__(self, collector: BusinessMetricsCollector, port: int = 8090):
        self.collector = collector
        self.port = port
        self.app = web.Application()
        self._setup_routes()
        
        # Background task for collecting metrics
        self.collection_task = None
        self.running = False
    
    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/metrics', self._metrics_handler)
        self.app.router.add_get('/health', self._health_handler)
    
    async def _metrics_handler(self, request):
        """Handle metrics endpoint"""
        try:
            metrics = self.collector.get_metrics()
            return web.Response(
                body=metrics,
                content_type=CONTENT_TYPE_LATEST
            )
        except Exception as e:
            logger.error(f"Error generating metrics: {e}")
            return web.Response(
                text="Internal server error",
                status=500
            )
    
    async def _health_handler(self, request):
        """Handle health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })
    
    async def _collection_loop(self):
        """Background metrics collection loop"""
        while self.running:
            try:
                await self.collector.collect_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in collection loop: {e}")
                await asyncio.sleep(30)
    
    async def start(self):
        """Start the metrics server"""
        await self.collector.initialize()
        
        # Start background collection
        self.running = True
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        # Start web server
        runner = web.AppRunner(self.app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        
        logger.info(f"Business metrics server started on port {self.port}")
    
    async def stop(self):
        """Stop the metrics server"""
        self.running = False
        
        if self.collection_task:
            self.collection_task.cancel()
        
        if self.collector.db_pool:
            await self.collector.db_pool.close()

async def main():
    """Main entry point"""
    # Configuration
    db_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:password@localhost/activelog')
    port = int(os.environ.get('PORT', '8090'))
    
    # Create collector and server
    collector = BusinessMetricsCollector(db_url)
    server = BusinessMetricsServer(collector, port)
    
    try:
        await server.start()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await server.stop()

if __name__ == "__main__":
    asyncio.run(main())