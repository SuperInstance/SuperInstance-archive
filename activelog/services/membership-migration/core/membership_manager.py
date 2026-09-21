#!/usr/bin/env python3
"""
Core membership management functionality for ActiveLog Migration Service
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class MembershipTier(Enum):
    """Membership tier levels"""
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class MembershipStatus(Enum):
    """Membership status states"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    PENDING = "pending"


@dataclass
class MembershipInfo:
    """Membership information data structure"""
    user_id: str
    tier: MembershipTier
    status: MembershipStatus
    start_date: datetime
    end_date: Optional[datetime]
    auto_renew: bool
    payment_method: str
    subscription_id: str
    features: List[str]
    usage_limits: Dict[str, Any]
    billing_cycle: str
    last_payment_date: Optional[datetime]
    next_payment_date: Optional[datetime]
    grace_period_end: Optional[datetime]
    created_at: datetime
    updated_at: datetime


@dataclass
class MigrationStats:
    """Migration statistics data structure"""
    total_migrations: int
    successful_migrations: int
    failed_migrations: int
    pending_migrations: int
    avg_migration_time_minutes: float
    most_common_source_app: str
    most_common_target_app: str
    total_credits_migrated: float
    total_data_migrated_gb: float
    migration_success_rate: float


class MembershipManager:
    """Core membership management system"""
    
    def __init__(self, config):
        self.config = config
        self.membership_cache = {}
        self.migration_metrics = {
            'total_migrations': 0,
            'successful_migrations': 0,
            'failed_migrations': 0,
            'pending_migrations': 0,
            'migration_times': [],
            'source_apps': {},
            'target_apps': {},
            'credits_migrated': 0.0,
            'data_migrated_gb': 0.0
        }
        logger.info("MembershipManager initialized")
    
    def get_membership_info(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive membership information for a user"""
        try:
            # Check cache first
            if user_id in self.membership_cache:
                cached_info = self.membership_cache[user_id]
                if datetime.utcnow() - cached_info['cached_at'] < timedelta(minutes=5):
                    return cached_info['data']
            
            # Fetch from database (simulated)
            membership_info = self._fetch_membership_from_db(user_id)
            
            # Get subscription details
            subscription_details = self._get_subscription_details(user_id)
            
            # Get usage information
            usage_info = self._get_usage_information(user_id)
            
            # Get billing information
            billing_info = self._get_billing_information(user_id)
            
            # Get active features
            active_features = self._get_active_features(user_id)
            
            # Compile comprehensive membership info
            comprehensive_info = {
                'user_id': user_id,
                'membership': membership_info,
                'subscription': subscription_details,
                'usage': usage_info,
                'billing': billing_info,
                'features': active_features,
                'migration_history': self._get_migration_history(user_id),
                'compute_credits': self._get_compute_credits_summary(user_id),
                'family_plan': self._get_family_plan_info(user_id),
                'discounts': self._get_active_discounts(user_id),
                'last_updated': datetime.utcnow().isoformat()
            }
            
            # Cache the result
            self.membership_cache[user_id] = {
                'data': comprehensive_info,
                'cached_at': datetime.utcnow()
            }
            
            return comprehensive_info
            
        except Exception as e:
            logger.error(f"Failed to get membership info for {user_id}: {e}")
            raise
    
    def _fetch_membership_from_db(self, user_id: str) -> Dict[str, Any]:
        """Fetch membership information from database"""
        # Simulated database fetch
        return {
            'tier': 'pro',
            'status': 'active',
            'start_date': (datetime.utcnow() - timedelta(days=90)).isoformat(),
            'end_date': (datetime.utcnow() + timedelta(days=275)).isoformat(),
            'auto_renew': True,
            'subscription_id': f'sub_{user_id}_pro_001',
            'billing_cycle': 'annual',
            'created_at': (datetime.utcnow() - timedelta(days=90)).isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def _get_subscription_details(self, user_id: str) -> Dict[str, Any]:
        """Get subscription details"""
        return {
            'subscription_id': f'sub_{user_id}_pro_001',
            'plan_name': 'ActiveLog Pro Annual',
            'price': 99.00,
            'currency': 'USD',
            'billing_interval': 'year',
            'trial_end': None,
            'cancel_at_period_end': False,
            'discount_applied': False,
            'payment_method': 'card',
            'last_payment_amount': 99.00,
            'next_payment_amount': 99.00,
            'payment_status': 'paid'
        }
    
    def _get_usage_information(self, user_id: str) -> Dict[str, Any]:
        """Get usage information"""
        return {
            'current_period_start': (datetime.utcnow() - timedelta(days=30)).isoformat(),
            'current_period_end': datetime.utcnow().isoformat(),
            'api_calls_used': 8450,
            'api_calls_limit': 50000,
            'storage_used_gb': 12.5,
            'storage_limit_gb': 100.0,
            'bandwidth_used_gb': 45.2,
            'bandwidth_limit_gb': 500.0,
            'compute_credits_used': 125.50,
            'compute_credits_limit': 1000.0,
            'active_projects': 8,
            'active_projects_limit': 25
        }
    
    def _get_billing_information(self, user_id: str) -> Dict[str, Any]:
        """Get billing information"""
        return {
            'payment_method': {
                'type': 'card',
                'last4': '4242',
                'brand': 'visa',
                'exp_month': 12,
                'exp_year': 2025
            },
            'billing_address': {
                'line1': '123 Main St',
                'city': 'San Francisco',
                'state': 'CA',
                'postal_code': '94105',
                'country': 'US'
            },
            'invoice_history': [
                {
                    'invoice_id': f'inv_{user_id}_001',
                    'date': (datetime.utcnow() - timedelta(days=30)).isoformat(),
                    'amount': 99.00,
                    'status': 'paid'
                }
            ],
            'upcoming_invoice': {
                'amount': 99.00,
                'date': (datetime.utcnow() + timedelta(days=335)).isoformat()
            }
        }
    
    def _get_active_features(self, user_id: str) -> List[str]:
        """Get active features for user"""
        return [
            'advanced_analytics',
            'priority_support',
            'api_access',
            'custom_integrations',
            'team_collaboration',
            'data_export',
            'webhook_support',
            'sso_integration'
        ]
    
    def _get_migration_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get migration history for user"""
        return [
            {
                'migration_id': f'mig_{user_id}_001',
                'source_app': 'activelog-legacy',
                'target_app': 'activelog-pro',
                'date': (datetime.utcnow() - timedelta(days=45)).isoformat(),
                'status': 'completed',
                'data_migrated_gb': 2.5,
                'credits_preserved': 50.0,
                'duration_minutes': 15
            }
        ]
    
    def _get_compute_credits_summary(self, user_id: str) -> Dict[str, Any]:
        """Get compute credits summary"""
        return {
            'total_balance': 874.50,
            'available_balance': 748.25,
            'reserved_balance': 126.25,
            'last_purchase_date': (datetime.utcnow() - timedelta(days=10)).isoformat(),
            'last_purchase_amount': 100.0,
            'usage_trend_30d': 'stable',
            'estimated_days_remaining': 45,
            'auto_top_up_enabled': True,
            'auto_top_up_threshold': 100.0,
            'auto_top_up_amount': 200.0
        }
    
    def _get_family_plan_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get family plan information if applicable"""
        # Return None if not part of family plan, otherwise return plan details
        return None
    
    def _get_active_discounts(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active discounts"""
        return []
    
    def record_migration_start(self, user_id: str, source_app: str, target_app: str, migration_id: str):
        """Record the start of a migration"""
        try:
            self.migration_metrics['total_migrations'] += 1
            self.migration_metrics['pending_migrations'] += 1
            
            # Track source and target apps
            self.migration_metrics['source_apps'][source_app] = \
                self.migration_metrics['source_apps'].get(source_app, 0) + 1
            self.migration_metrics['target_apps'][target_app] = \
                self.migration_metrics['target_apps'].get(target_app, 0) + 1
            
            logger.info(f"Migration started: {migration_id} from {source_app} to {target_app}")
            
        except Exception as e:
            logger.error(f"Failed to record migration start: {e}")
    
    def record_migration_completion(self, migration_id: str, success: bool, 
                                  duration_minutes: float, credits_migrated: float = 0.0,
                                  data_migrated_gb: float = 0.0):
        """Record the completion of a migration"""
        try:
            self.migration_metrics['pending_migrations'] -= 1
            
            if success:
                self.migration_metrics['successful_migrations'] += 1
                self.migration_metrics['credits_migrated'] += credits_migrated
                self.migration_metrics['data_migrated_gb'] += data_migrated_gb
            else:
                self.migration_metrics['failed_migrations'] += 1
            
            self.migration_metrics['migration_times'].append(duration_minutes)
            
            logger.info(f"Migration completed: {migration_id}, Success: {success}")
            
        except Exception as e:
            logger.error(f"Failed to record migration completion: {e}")
    
    def get_migration_analytics(self, time_range: str = '30d') -> Dict[str, Any]:
        """Get migration analytics and statistics"""
        try:
            # Calculate success rate
            total_completed = (self.migration_metrics['successful_migrations'] + 
                             self.migration_metrics['failed_migrations'])
            success_rate = (self.migration_metrics['successful_migrations'] / total_completed * 100 
                          if total_completed > 0 else 0)
            
            # Calculate average migration time
            avg_time = (sum(self.migration_metrics['migration_times']) / 
                       len(self.migration_metrics['migration_times'])
                       if self.migration_metrics['migration_times'] else 0)
            
            # Find most common source and target apps
            most_common_source = max(self.migration_metrics['source_apps'], 
                                   key=self.migration_metrics['source_apps'].get, 
                                   default='None')
            most_common_target = max(self.migration_metrics['target_apps'], 
                                   key=self.migration_metrics['target_apps'].get, 
                                   default='None')
            
            return {
                'time_range': time_range,
                'total_migrations': self.migration_metrics['total_migrations'],
                'successful_migrations': self.migration_metrics['successful_migrations'],
                'failed_migrations': self.migration_metrics['failed_migrations'],
                'pending_migrations': self.migration_metrics['pending_migrations'],
                'success_rate_percentage': round(success_rate, 2),
                'average_migration_time_minutes': round(avg_time, 2),
                'most_common_source_app': most_common_source,
                'most_common_target_app': most_common_target,
                'total_credits_migrated': self.migration_metrics['credits_migrated'],
                'total_data_migrated_gb': self.migration_metrics['data_migrated_gb'],
                'app_migration_patterns': {
                    'source_apps': dict(self.migration_metrics['source_apps']),
                    'target_apps': dict(self.migration_metrics['target_apps'])
                },
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to generate migration analytics: {e}")
            return {'error': str(e)}
    
    def get_dashboard_metrics(self) -> Dict[str, Any]:
        """Get dashboard metrics and status information"""
        try:
            # Get current system status
            system_status = self._get_system_status()
            
            # Get recent activity
            recent_activity = self._get_recent_activity()
            
            # Get resource utilization
            resource_utilization = self._get_resource_utilization()
            
            return {
                'system_status': system_status,
                'migration_overview': {
                    'total_migrations_today': self._get_migrations_today(),
                    'active_migrations': self.migration_metrics['pending_migrations'],
                    'success_rate_24h': self._calculate_success_rate_24h(),
                    'average_migration_time': self._get_avg_migration_time()
                },
                'resource_utilization': resource_utilization,
                'recent_activity': recent_activity,
                'alerts': self._get_active_alerts(),
                'performance_metrics': self._get_performance_metrics(),
                'generated_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {'error': str(e)}
    
    def _get_system_status(self) -> Dict[str, Any]:
        """Get system status information"""
        return {
            'overall_status': 'healthy',
            'services': {
                'membership_manager': 'online',
                'cross_frontend_transfer': 'online',
                'compute_credits': 'online',
                'data_migration': 'online',
                'billing_consolidator': 'online'
            },
            'uptime_hours': 168.5,
            'last_restart': (datetime.utcnow() - timedelta(hours=168)).isoformat()
        }
    
    def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent activity logs"""
        return [
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                'activity': 'Migration completed',
                'user_id': 'user_12345',
                'details': 'Migrated from StudyLog to BusinessLog'
            },
            {
                'timestamp': (datetime.utcnow() - timedelta(minutes=12)).isoformat(),
                'activity': 'Credits preserved',
                'user_id': 'user_67890',
                'details': '150.0 credits preserved during transfer'
            }
        ]
    
    def _get_resource_utilization(self) -> Dict[str, Any]:
        """Get resource utilization metrics"""
        return {
            'cpu_usage_percent': 45.2,
            'memory_usage_percent': 62.8,
            'disk_usage_percent': 34.1,
            'network_io_mbps': 12.5,
            'active_connections': 47
        }
    
    def _get_migrations_today(self) -> int:
        """Get number of migrations today"""
        return 23
    
    def _calculate_success_rate_24h(self) -> float:
        """Calculate success rate in last 24 hours"""
        return 98.5
    
    def _get_avg_migration_time(self) -> float:
        """Get average migration time"""
        return 12.3
    
    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get active system alerts"""
        return []
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        return {
            'response_time_ms': 125,
            'throughput_requests_per_second': 45.2,
            'error_rate_percent': 0.1,
            'cache_hit_rate_percent': 87.3
        }