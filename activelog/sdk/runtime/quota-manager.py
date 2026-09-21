#!/usr/bin/env python3
"""
ActiveLog Plugin Quota Manager - Manage resource quotas and limits
"""

import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class PluginQuota:
    plugin_id: str
    user_id: str
    organization_id: str
    plan_type: str  # free, pro, enterprise
    
    # Compute quotas
    cpu_hours_daily: float = 1.0
    cpu_hours_monthly: float = 24.0
    
    # Memory quotas (MB)
    memory_limit_mb: int = 256
    memory_hours_daily: float = 8.0  # MB-hours
    memory_hours_monthly: float = 192.0
    
    # Storage quotas (MB)
    storage_limit_mb: int = 100
    storage_daily_mb: int = 1000
    storage_monthly_mb: int = 10000
    
    # Network quotas (MB)
    network_limit_mbps: float = 1.0
    network_daily_mb: int = 100
    network_monthly_mb: int = 2000
    
    # Execution quotas
    max_concurrent_executions: int = 2
    max_daily_executions: int = 100
    max_monthly_executions: int = 2000
    execution_timeout_seconds: int = 60
    
    # API quotas
    api_calls_per_minute: int = 60
    api_calls_daily: int = 5000
    api_calls_monthly: int = 100000
    
    # Special permissions
    network_enabled: bool = False
    database_access: bool = False
    filesystem_write: bool = False
    
    # Quota period
    created_at: float = 0.0
    updated_at: float = 0.0
    reset_daily_at: float = 0.0
    reset_monthly_at: float = 0.0


@dataclass
class ResourceUsage:
    plugin_id: str
    user_id: str
    period: str  # daily, monthly
    period_start: float
    
    # Actual usage
    cpu_hours_used: float = 0.0
    memory_hours_used: float = 0.0
    storage_mb_used: int = 0
    network_mb_used: int = 0
    executions_used: int = 0
    api_calls_used: int = 0
    
    # Peak usage
    peak_memory_mb: int = 0
    peak_network_mbps: float = 0.0
    peak_concurrent_executions: int = 0
    
    last_updated: float = 0.0


class QuotaManager:
    """Manage plugin resource quotas and usage tracking"""
    
    def __init__(self, db_path: str = "quota.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
        
        # In-memory cache for active quotas
        self.quota_cache = {}
        self.usage_cache = {}
        
        # Plan configurations
        self.plan_configs = {
            'free': {
                'cpu_hours_daily': 1.0,
                'cpu_hours_monthly': 24.0,
                'memory_limit_mb': 256,
                'memory_hours_daily': 4.0,
                'memory_hours_monthly': 96.0,
                'storage_limit_mb': 100,
                'storage_daily_mb': 500,
                'storage_monthly_mb': 5000,
                'network_daily_mb': 50,
                'network_monthly_mb': 1000,
                'max_concurrent_executions': 1,
                'max_daily_executions': 50,
                'max_monthly_executions': 1000,
                'api_calls_per_minute': 30,
                'api_calls_daily': 2500,
                'api_calls_monthly': 50000,
                'network_enabled': False,
                'database_access': False,
                'filesystem_write': False,
            },
            'pro': {
                'cpu_hours_daily': 8.0,
                'cpu_hours_monthly': 200.0,
                'memory_limit_mb': 512,
                'memory_hours_daily': 32.0,
                'memory_hours_monthly': 800.0,
                'storage_limit_mb': 500,
                'storage_daily_mb': 5000,
                'storage_monthly_mb': 100000,
                'network_daily_mb': 500,
                'network_monthly_mb': 10000,
                'max_concurrent_executions': 5,
                'max_daily_executions': 500,
                'max_monthly_executions': 10000,
                'api_calls_per_minute': 120,
                'api_calls_daily': 10000,
                'api_calls_monthly': 500000,
                'network_enabled': True,
                'database_access': True,
                'filesystem_write': True,
            },
            'enterprise': {
                'cpu_hours_daily': 50.0,
                'cpu_hours_monthly': 1000.0,
                'memory_limit_mb': 2048,
                'memory_hours_daily': 200.0,
                'memory_hours_monthly': 5000.0,
                'storage_limit_mb': 5000,
                'storage_daily_mb': 50000,
                'storage_monthly_mb': 1000000,
                'network_daily_mb': 5000,
                'network_monthly_mb': 100000,
                'max_concurrent_executions': 20,
                'max_daily_executions': 2000,
                'max_monthly_executions': 50000,
                'api_calls_per_minute': 600,
                'api_calls_daily': 50000,
                'api_calls_monthly': 2000000,
                'network_enabled': True,
                'database_access': True,
                'filesystem_write': True,
            }
        }
    
    def _init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create quotas table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS quotas (
                plugin_id TEXT,
                user_id TEXT,
                organization_id TEXT,
                plan_type TEXT,
                quota_data TEXT,
                created_at REAL,
                updated_at REAL,
                PRIMARY KEY (plugin_id, user_id)
            )
        """)
        
        # Create usage table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage (
                plugin_id TEXT,
                user_id TEXT,
                period TEXT,
                period_start REAL,
                usage_data TEXT,
                last_updated REAL,
                PRIMARY KEY (plugin_id, user_id, period, period_start)
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quotas_user ON quotas (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_quotas_org ON quotas (organization_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_usage_period ON usage (period, period_start)")
        
        conn.commit()
        conn.close()
    
    async def create_plugin_quota(
        self, 
        plugin_id: str, 
        user_id: str, 
        organization_id: str, 
        plan_type: str = 'free'
    ) -> PluginQuota:
        """Create quota for a plugin"""
        
        if plan_type not in self.plan_configs:
            raise ValueError(f"Unknown plan type: {plan_type}")
        
        # Create quota with plan defaults
        now = time.time()
        quota_data = self.plan_configs[plan_type].copy()
        quota_data.update({
            'plugin_id': plugin_id,
            'user_id': user_id,
            'organization_id': organization_id,
            'plan_type': plan_type,
            'created_at': now,
            'updated_at': now,
            'reset_daily_at': self._get_next_daily_reset(),
            'reset_monthly_at': self._get_next_monthly_reset()
        })
        
        quota = PluginQuota(**quota_data)
        
        # Store in database
        await self._save_quota(quota)
        
        # Cache the quota
        self.quota_cache[(plugin_id, user_id)] = quota
        
        return quota
    
    async def get_plugin_quota(self, plugin_id: str, user_id: str) -> Optional[PluginQuota]:
        """Get quota for a plugin"""
        
        # Check cache first
        cache_key = (plugin_id, user_id)
        if cache_key in self.quota_cache:
            return self.quota_cache[cache_key]
        
        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT quota_data FROM quotas WHERE plugin_id = ? AND user_id = ?",
            (plugin_id, user_id)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            quota_data = json.loads(result[0])
            quota = PluginQuota(**quota_data)
            self.quota_cache[cache_key] = quota
            return quota
        
        return None
    
    async def update_plugin_quota(
        self, 
        plugin_id: str, 
        user_id: str, 
        **updates
    ) -> Optional[PluginQuota]:
        """Update plugin quota"""
        
        quota = await self.get_plugin_quota(plugin_id, user_id)
        if not quota:
            return None
        
        # Update fields
        for field, value in updates.items():
            if hasattr(quota, field):
                setattr(quota, field, value)
        
        quota.updated_at = time.time()
        
        # Save updated quota
        await self._save_quota(quota)
        
        # Update cache
        self.quota_cache[(plugin_id, user_id)] = quota
        
        return quota
    
    async def check_quota_limit(
        self, 
        plugin_id: str, 
        user_id: str, 
        resource_type: str, 
        requested_amount: float = 1.0
    ) -> Dict[str, Any]:
        """Check if resource usage would exceed quota"""
        
        quota = await self.get_plugin_quota(plugin_id, user_id)
        if not quota:
            return {'allowed': False, 'reason': 'No quota found'}
        
        # Get current usage
        daily_usage = await self.get_resource_usage(plugin_id, user_id, 'daily')
        monthly_usage = await self.get_resource_usage(plugin_id, user_id, 'monthly')
        
        # Check specific resource limits
        checks = []
        
        if resource_type == 'cpu':
            checks.extend([
                {
                    'limit': quota.cpu_hours_daily,
                    'used': daily_usage.cpu_hours_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.cpu_hours_monthly,
                    'used': monthly_usage.cpu_hours_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        elif resource_type == 'memory':
            checks.extend([
                {
                    'limit': quota.memory_hours_daily,
                    'used': daily_usage.memory_hours_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.memory_hours_monthly,
                    'used': monthly_usage.memory_hours_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        elif resource_type == 'storage':
            checks.extend([
                {
                    'limit': quota.storage_daily_mb,
                    'used': daily_usage.storage_mb_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.storage_monthly_mb,
                    'used': monthly_usage.storage_mb_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        elif resource_type == 'network':
            checks.extend([
                {
                    'limit': quota.network_daily_mb,
                    'used': daily_usage.network_mb_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.network_monthly_mb,
                    'used': monthly_usage.network_mb_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        elif resource_type == 'execution':
            checks.extend([
                {
                    'limit': quota.max_daily_executions,
                    'used': daily_usage.executions_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.max_monthly_executions,
                    'used': monthly_usage.executions_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        elif resource_type == 'api_calls':
            checks.extend([
                {
                    'limit': quota.api_calls_daily,
                    'used': daily_usage.api_calls_used,
                    'requested': requested_amount,
                    'period': 'daily'
                },
                {
                    'limit': quota.api_calls_monthly,
                    'used': monthly_usage.api_calls_used,
                    'requested': requested_amount,
                    'period': 'monthly'
                }
            ])
        
        # Check all limits
        for check in checks:
            if check['used'] + check['requested'] > check['limit']:
                return {
                    'allowed': False,
                    'reason': f"{resource_type} {check['period']} limit exceeded",
                    'limit': check['limit'],
                    'used': check['used'],
                    'requested': check['requested'],
                    'available': max(0, check['limit'] - check['used'])
                }
        
        return {'allowed': True}
    
    async def record_resource_usage(
        self,
        plugin_id: str,
        user_id: str,
        usage_data: Dict[str, float]
    ):
        """Record resource usage"""
        
        # Update both daily and monthly usage
        for period in ['daily', 'monthly']:
            usage = await self.get_resource_usage(plugin_id, user_id, period)
            
            # Update usage values
            if 'cpu_hours' in usage_data:
                usage.cpu_hours_used += usage_data['cpu_hours']
            if 'memory_hours' in usage_data:
                usage.memory_hours_used += usage_data['memory_hours']
                usage.peak_memory_mb = max(usage.peak_memory_mb, usage_data.get('peak_memory_mb', 0))
            if 'storage_mb' in usage_data:
                usage.storage_mb_used += usage_data['storage_mb']
            if 'network_mb' in usage_data:
                usage.network_mb_used += usage_data['network_mb']
                usage.peak_network_mbps = max(usage.peak_network_mbps, usage_data.get('peak_network_mbps', 0))
            if 'executions' in usage_data:
                usage.executions_used += usage_data['executions']
                usage.peak_concurrent_executions = max(usage.peak_concurrent_executions, usage_data.get('concurrent_executions', 0))
            if 'api_calls' in usage_data:
                usage.api_calls_used += usage_data['api_calls']
            
            usage.last_updated = time.time()
            
            # Save usage
            await self._save_usage(usage)
    
    async def get_resource_usage(
        self, 
        plugin_id: str, 
        user_id: str, 
        period: str
    ) -> ResourceUsage:
        """Get current resource usage for period"""
        
        period_start = self._get_period_start(period)
        cache_key = (plugin_id, user_id, period, period_start)
        
        # Check cache
        if cache_key in self.usage_cache:
            return self.usage_cache[cache_key]
        
        # Load from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT usage_data FROM usage WHERE plugin_id = ? AND user_id = ? AND period = ? AND period_start = ?",
            (plugin_id, user_id, period, period_start)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            usage_data = json.loads(result[0])
            usage = ResourceUsage(**usage_data)
        else:
            # Create new usage record
            usage = ResourceUsage(
                plugin_id=plugin_id,
                user_id=user_id,
                period=period,
                period_start=period_start,
                last_updated=time.time()
            )
            await self._save_usage(usage)
        
        self.usage_cache[cache_key] = usage
        return usage
    
    async def reset_quotas(self):
        """Reset quotas at period boundaries"""
        now = time.time()
        
        # Check for daily resets
        expired_daily = []
        for key, quota in self.quota_cache.items():
            if now >= quota.reset_daily_at:
                expired_daily.append(key)
        
        # Reset daily usage
        for key in expired_daily:
            plugin_id, user_id = key
            quota = self.quota_cache[key]
            quota.reset_daily_at = self._get_next_daily_reset()
            await self._save_quota(quota)
            
            # Clear daily usage from cache
            daily_keys = [k for k in self.usage_cache.keys() if k[0] == plugin_id and k[1] == user_id and k[2] == 'daily']
            for daily_key in daily_keys:
                del self.usage_cache[daily_key]
        
        # Similar logic for monthly resets
        expired_monthly = []
        for key, quota in self.quota_cache.items():
            if now >= quota.reset_monthly_at:
                expired_monthly.append(key)
        
        for key in expired_monthly:
            plugin_id, user_id = key
            quota = self.quota_cache[key]
            quota.reset_monthly_at = self._get_next_monthly_reset()
            await self._save_quota(quota)
            
            # Clear monthly usage from cache
            monthly_keys = [k for k in self.usage_cache.keys() if k[0] == plugin_id and k[1] == user_id and k[2] == 'monthly']
            for monthly_key in monthly_keys:
                del self.usage_cache[monthly_key]
    
    async def get_quota_summary(self, plugin_id: str, user_id: str) -> Dict[str, Any]:
        """Get quota and usage summary"""
        quota = await self.get_plugin_quota(plugin_id, user_id)
        if not quota:
            return None
        
        daily_usage = await self.get_resource_usage(plugin_id, user_id, 'daily')
        monthly_usage = await self.get_resource_usage(plugin_id, user_id, 'monthly')
        
        return {
            'plugin_id': plugin_id,
            'user_id': user_id,
            'plan_type': quota.plan_type,
            'quotas': {
                'cpu_hours_daily': quota.cpu_hours_daily,
                'cpu_hours_monthly': quota.cpu_hours_monthly,
                'memory_limit_mb': quota.memory_limit_mb,
                'memory_hours_daily': quota.memory_hours_daily,
                'memory_hours_monthly': quota.memory_hours_monthly,
                'storage_limit_mb': quota.storage_limit_mb,
                'network_daily_mb': quota.network_daily_mb,
                'network_monthly_mb': quota.network_monthly_mb,
                'max_daily_executions': quota.max_daily_executions,
                'max_monthly_executions': quota.max_monthly_executions,
                'api_calls_daily': quota.api_calls_daily,
                'api_calls_monthly': quota.api_calls_monthly,
            },
            'usage': {
                'daily': {
                    'cpu_hours': daily_usage.cpu_hours_used,
                    'memory_hours': daily_usage.memory_hours_used,
                    'storage_mb': daily_usage.storage_mb_used,
                    'network_mb': daily_usage.network_mb_used,
                    'executions': daily_usage.executions_used,
                    'api_calls': daily_usage.api_calls_used,
                },
                'monthly': {
                    'cpu_hours': monthly_usage.cpu_hours_used,
                    'memory_hours': monthly_usage.memory_hours_used,
                    'storage_mb': monthly_usage.storage_mb_used,
                    'network_mb': monthly_usage.network_mb_used,
                    'executions': monthly_usage.executions_used,
                    'api_calls': monthly_usage.api_calls_used,
                }
            },
            'utilization': {
                'cpu_daily_percent': (daily_usage.cpu_hours_used / quota.cpu_hours_daily) * 100,
                'cpu_monthly_percent': (monthly_usage.cpu_hours_used / quota.cpu_hours_monthly) * 100,
                'memory_daily_percent': (daily_usage.memory_hours_used / quota.memory_hours_daily) * 100,
                'memory_monthly_percent': (monthly_usage.memory_hours_used / quota.memory_hours_monthly) * 100,
                'executions_daily_percent': (daily_usage.executions_used / quota.max_daily_executions) * 100,
                'executions_monthly_percent': (monthly_usage.executions_used / quota.max_monthly_executions) * 100,
            }
        }
    
    # Helper methods
    
    async def _save_quota(self, quota: PluginQuota):
        """Save quota to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        quota_data = json.dumps(asdict(quota))
        
        cursor.execute("""
            INSERT OR REPLACE INTO quotas 
            (plugin_id, user_id, organization_id, plan_type, quota_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            quota.plugin_id,
            quota.user_id,
            quota.organization_id,
            quota.plan_type,
            quota_data,
            quota.created_at,
            quota.updated_at
        ))
        
        conn.commit()
        conn.close()
    
    async def _save_usage(self, usage: ResourceUsage):
        """Save usage to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        usage_data = json.dumps(asdict(usage))
        
        cursor.execute("""
            INSERT OR REPLACE INTO usage 
            (plugin_id, user_id, period, period_start, usage_data, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            usage.plugin_id,
            usage.user_id,
            usage.period,
            usage.period_start,
            usage_data,
            usage.last_updated
        ))
        
        conn.commit()
        conn.close()
    
    def _get_period_start(self, period: str) -> float:
        """Get start time for current period"""
        now = datetime.utcnow()
        
        if period == 'daily':
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'monthly':
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise ValueError(f"Unknown period: {period}")
        
        return start.timestamp()
    
    def _get_next_daily_reset(self) -> float:
        """Get next daily reset time"""
        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        return tomorrow.timestamp()
    
    def _get_next_monthly_reset(self) -> float:
        """Get next monthly reset time"""
        now = datetime.utcnow()
        if now.month == 12:
            next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return next_month.timestamp()


# Global quota manager instance
quota_manager = QuotaManager()


async def main():
    """Test the quota manager"""
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: quota-manager.py <plugin_id> <user_id> <action>")
        print("Actions: create, check, record, summary")
        sys.exit(1)
    
    plugin_id = sys.argv[1]
    user_id = sys.argv[2]
    action = sys.argv[3]
    
    manager = QuotaManager("test_quota.db")
    
    if action == 'create':
        quota = await manager.create_plugin_quota(plugin_id, user_id, "org-123", "pro")
        print(f"Created quota: {quota}")
    
    elif action == 'check':
        result = await manager.check_quota_limit(plugin_id, user_id, 'cpu', 0.5)
        print(f"Quota check: {result}")
    
    elif action == 'record':
        await manager.record_resource_usage(plugin_id, user_id, {
            'cpu_hours': 0.1,
            'memory_hours': 0.5,
            'executions': 1
        })
        print("Usage recorded")
    
    elif action == 'summary':
        summary = await manager.get_quota_summary(plugin_id, user_id)
        print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    asyncio.run(main())