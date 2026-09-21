"""
CRM Configuration Management
Centralized configuration for all CRM components
"""

import os
from typing import Dict, Any


class CRMConfig:
    """CRM system configuration manager"""
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment and defaults"""
        return {
            # Database Configuration
            'database': {
                'type': os.environ.get('CRM_DB_TYPE', 'sqlite'),
                'host': os.environ.get('CRM_DB_HOST', 'localhost'),
                'port': int(os.environ.get('CRM_DB_PORT', 5432)),
                'name': os.environ.get('CRM_DB_NAME', 'crm_sales'),
                'username': os.environ.get('CRM_DB_USER', 'crm_user'),
                'password': os.environ.get('CRM_DB_PASSWORD', 'crm_password'),
                'file': os.environ.get('CRM_DB_FILE', 'data/crm_sales.db')
            },
            
            # Contact Management
            'contact_management': {
                'duplicate_detection_enabled': True,
                'auto_merge_duplicates': False,
                'data_enrichment_enabled': True,
                'activity_tracking_enabled': True,
                'contact_scoring_enabled': True,
                'max_contacts_per_company': 1000
            },
            
            # Lead Scoring
            'lead_scoring': {
                'enabled': True,
                'auto_scoring_enabled': True,
                'score_range': {'min': 0, 'max': 100},
                'hot_lead_threshold': 80,
                'warm_lead_threshold': 60,
                'cold_lead_threshold': 40,
                'scoring_frequency_hours': 24,
                'decay_enabled': True,
                'decay_rate_days': 30
            },
            
            # Opportunity Management
            'opportunities': {
                'default_probability': 50.0,
                'auto_stage_progression': False,
                'weighted_pipeline_enabled': True,
                'opportunity_aging_days': 90,
                'auto_close_stale_opportunities': True,
                'require_close_reason': True
            },
            
            # Pipeline Configuration
            'pipeline': {
                'default_stages': [
                    {'name': 'Lead', 'probability': 10, 'order': 1},
                    {'name': 'Qualified', 'probability': 25, 'order': 2},
                    {'name': 'Proposal', 'probability': 50, 'order': 3},
                    {'name': 'Negotiation', 'probability': 75, 'order': 4},
                    {'name': 'Closed Won', 'probability': 100, 'order': 5},
                    {'name': 'Closed Lost', 'probability': 0, 'order': 6}
                ],
                'velocity_calculation_days': 30,
                'conversion_tracking_enabled': True,
                'stage_aging_alerts': True
            },
            
            # Email Campaigns
            'email_campaigns': {
                'smtp_server': os.environ.get('SMTP_SERVER', 'localhost'),
                'smtp_port': int(os.environ.get('SMTP_PORT', 587)),
                'smtp_username': os.environ.get('SMTP_USERNAME', ''),
                'smtp_password': os.environ.get('SMTP_PASSWORD', ''),
                'from_email': os.environ.get('FROM_EMAIL', 'noreply@crm.com'),
                'from_name': os.environ.get('FROM_NAME', 'CRM System'),
                'max_recipients_per_batch': 100,
                'send_rate_per_hour': 1000,
                'bounce_handling_enabled': True,
                'unsubscribe_handling_enabled': True,
                'tracking_enabled': True
            },
            
            # Call Logging
            'call_logging': {
                'voip_integration_enabled': False,
                'recording_enabled': False,
                'transcription_enabled': False,
                'auto_activity_creation': True,
                'sentiment_analysis_enabled': False,
                'call_disposition_required': True,
                'follow_up_task_creation': True
            },
            
            # Task Automation
            'task_automation': {
                'enabled': True,
                'workflow_engine_enabled': True,
                'max_workflows_per_trigger': 5,
                'task_queue_enabled': True,
                'scheduled_tasks_enabled': True,
                'email_notifications_enabled': True,
                'webhook_notifications_enabled': True,
                'ai_task_suggestions': False
            },
            
            # Territory Management
            'territory_management': {
                'enabled': True,
                'geographic_territories': True,
                'account_based_territories': True,
                'territory_overlap_allowed': False,
                'auto_assignment_enabled': True,
                'territory_balancing_enabled': True,
                'performance_tracking_enabled': True
            },
            
            # Commission Tracking
            'commission_tracking': {
                'enabled': True,
                'default_commission_rate': 0.05,  # 5%
                'tiered_commissions_enabled': True,
                'team_commissions_enabled': True,
                'clawback_enabled': True,
                'clawback_period_days': 90,
                'payment_schedule': 'monthly',  # monthly, quarterly
                'currency': 'USD'
            },
            
            # Sales Forecasting
            'sales_forecasting': {
                'enabled': True,
                'forecasting_models': ['linear', 'seasonal', 'ml'],
                'default_model': 'linear',
                'forecast_periods': [30, 60, 90, 180, 365],  # days
                'confidence_intervals': [80, 90, 95],
                'historical_data_months': 24,
                'seasonal_adjustment': True,
                'ai_forecasting_enabled': False
            },
            
            # Customer Segmentation
            'customer_segmentation': {
                'enabled': True,
                'auto_segmentation_enabled': True,
                'rfm_analysis_enabled': True,  # Recency, Frequency, Monetary
                'behavioral_segmentation': True,
                'demographic_segmentation': True,
                'predictive_segmentation': False,
                'segment_refresh_frequency_days': 7,
                'min_segment_size': 10
            },
            
            # Retention Analytics
            'retention_analytics': {
                'enabled': True,
                'cohort_analysis_enabled': True,
                'churn_prediction_enabled': True,
                'churn_model_threshold': 0.7,
                'retention_campaign_triggers': True,
                'customer_health_scoring': True,
                'intervention_recommendations': True,
                'analysis_frequency_days': 7
            },
            
            # Integration Settings
            'integrations': {
                'salesforce_enabled': False,
                'hubspot_enabled': False,
                'mailchimp_enabled': False,
                'zapier_enabled': False,
                'slack_enabled': False,
                'teams_enabled': False,
                'zoom_enabled': False,
                'calendly_enabled': False
            },
            
            # Security Settings
            'security': {
                'encryption_enabled': True,
                'audit_logging_enabled': True,
                'role_based_access': True,
                'field_level_security': True,
                'data_masking_enabled': True,
                'session_timeout_minutes': 60,
                'password_complexity_required': True
            },
            
            # Performance Settings
            'performance': {
                'caching_enabled': True,
                'cache_ttl_seconds': 3600,
                'bulk_operations_enabled': True,
                'async_processing_enabled': True,
                'rate_limiting_enabled': True,
                'max_requests_per_minute': 1000,
                'query_optimization_enabled': True
            },
            
            # Notification Settings
            'notifications': {
                'email_notifications_enabled': True,
                'sms_notifications_enabled': False,
                'push_notifications_enabled': True,
                'slack_notifications_enabled': False,
                'webhook_notifications_enabled': True,
                'notification_frequency_limit': 10  # per hour per user
            },
            
            # Mobile Settings
            'mobile': {
                'mobile_app_enabled': True,
                'offline_mode_enabled': True,
                'sync_frequency_minutes': 15,
                'mobile_notifications_enabled': True,
                'location_tracking_enabled': False
            },
            
            # Analytics and Reporting
            'analytics': {
                'google_analytics_enabled': False,
                'custom_dashboards_enabled': True,
                'scheduled_reports_enabled': True,
                'data_export_enabled': True,
                'real_time_analytics_enabled': True,
                'historical_data_retention_months': 36
            }
        }
        
    def get(self, key: str, default=None):
        """Get configuration value by key"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value):
        """Set configuration value"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values"""
        for key, value in updates.items():
            self.set(key, value)
            
    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        return self.get('database', {})
        
    def get_smtp_config(self) -> Dict[str, Any]:
        """Get SMTP configuration for email campaigns"""
        return self.get('email_campaigns', {})
        
    def is_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.get(f'{feature}.enabled', False)
        
    def get_integration_config(self, integration_name: str) -> Dict[str, Any]:
        """Get integration configuration"""
        return self.get(f'integrations.{integration_name}', {})
        
    def export_config(self) -> Dict[str, Any]:
        """Export configuration (excluding sensitive data)"""
        config_copy = self.config.copy()
        
        # Remove sensitive information
        sensitive_keys = ['password', 'secret', 'key', 'token']
        
        def remove_sensitive(obj):
            if isinstance(obj, dict):
                return {
                    k: remove_sensitive(v) if not any(s in k.lower() for s in sensitive_keys) else '***'
                    for k, v in obj.items()
                }
            return obj
            
        return remove_sensitive(config_copy)