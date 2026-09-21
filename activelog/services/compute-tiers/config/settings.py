#!/usr/bin/env python3
"""
Configuration settings for ActiveLog Compute Tiers Service
"""

import os
from typing import Dict, Any


class ComputeTiersConfig:
    """Configuration management for compute tiers service"""
    
    def __init__(self):
        self.aws_region = os.getenv('AWS_DEFAULT_REGION', 'us-west-2')
        self.service_port = int(os.getenv('COMPUTE_TIERS_PORT', 8331))
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Service configuration
        self.service_config = {
            'name': 'ActiveLog Compute Tiers',
            'version': '1.0.0',
            'description': 'Intelligent compute resource management with automatic right-sizing, GPU scheduling, and hybrid cloud orchestration',
            'port': self.service_port,
            'host': '0.0.0.0',
            'debug': self.environment == 'development'
        }
        
        # AWS configuration
        self.aws_config = {
            'region': self.aws_region,
            'availability_zones': [
                f'{self.aws_region}a',
                f'{self.aws_region}b',
                f'{self.aws_region}c'
            ],
            'default_vpc': os.getenv('AWS_DEFAULT_VPC'),
            'default_subnets': os.getenv('AWS_DEFAULT_SUBNETS', '').split(',') if os.getenv('AWS_DEFAULT_SUBNETS') else []
        }
        
        # Recommendation engine configuration
        self.recommendation_config = {
            'default_workload_type': 'balanced',
            'performance_weight': 0.4,
            'cost_weight': 0.3,
            'reliability_weight': 0.3,
            'cache_ttl_minutes': 15,
            'max_recommendations': 10
        }
        
        # Right-sizing configuration
        self.rightsizing_config = {
            'analysis_period_days': 7,
            'confidence_threshold': 0.7,
            'min_utilization_threshold': 0.1,
            'max_utilization_threshold': 0.85,
            'cost_savings_threshold': 5.0  # Minimum 5% savings to recommend
        }
        
        # GPU scheduling configuration
        self.gpu_config = {
            'max_concurrent_jobs': 50,
            'default_timeout_minutes': 480,  # 8 hours
            'queue_check_interval_seconds': 30,
            'resource_reservation_minutes': 15
        }
        
        # Batch optimization configuration
        self.batch_config = {
            'max_job_queue_size': 1000,
            'optimization_interval_minutes': 10,
            'default_retry_attempts': 3,
            'spot_instance_preferred': True
        }
        
        # Priority routing configuration
        self.routing_config = {
            'default_strategy': 'balanced',
            'tier_utilization_threshold': 80,
            'failover_enabled': True,
            'health_check_interval_seconds': 60
        }
        
        # Cost-performance optimizer configuration
        self.cost_performance_config = {
            'optimization_targets': ['cost', 'performance', 'balanced', 'efficiency'],
            'analysis_window_hours': 24,
            'confidence_threshold': 0.6,
            'cost_variance_threshold': 10.0  # 10% cost difference threshold
        }
        
        # SLA scheduler configuration
        self.sla_config = {
            'sla_levels': ['platinum', 'gold', 'silver', 'bronze', 'basic'],
            'default_sla_level': 'silver',
            'uptime_check_interval_seconds': 30,
            'failover_timeout_seconds': 300
        }
        
        # Hybrid orchestrator configuration
        self.hybrid_config = {
            'local_resource_discovery': True,
            'cloud_providers': ['aws', 'azure', 'gcp'],
            'default_orchestration_strategy': 'balanced',
            'heartbeat_interval_seconds': 60,
            'resource_sync_interval_minutes': 5
        }
        
        # Edge manager configuration
        self.edge_config = {
            'supported_device_types': ['raspberry_pi', 'jetson_nano', 'aws_wavelength', 'azure_edge'],
            'max_latency_threshold_ms': 100,
            'edge_tiers': ['ultra_edge', 'regional_edge', 'metro_edge', 'micro_edge'],
            'health_check_interval_seconds': 30
        }
        
        # Green energy optimizer configuration
        self.green_config = {
            'carbon_intensity_threshold': 300,  # gCO2/kWh
            'renewable_percentage_target': 70,
            'green_preferences': ['maximum_green', 'prefer_green', 'balanced'],
            'forecast_horizon_hours': 24,
            'optimization_interval_minutes': 30
        }
        
        # Logging configuration
        self.logging_config = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': f'/home/activeloguser/activelog/logs/compute-tiers.log',
            'max_file_size_mb': 100,
            'backup_count': 5
        }
        
        # Monitoring configuration
        self.monitoring_config = {
            'metrics_enabled': True,
            'metrics_interval_seconds': 60,
            'health_check_enabled': True,
            'performance_tracking': True,
            'alerts_enabled': self.environment == 'production'
        }
        
        # Security configuration
        self.security_config = {
            'api_key_required': self.environment == 'production',
            'rate_limiting_enabled': True,
            'max_requests_per_minute': 100,
            'cors_enabled': True,
            'allowed_origins': ['http://localhost:3000', 'https://activelog.com']
        }

    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section"""
        return getattr(self, f'{section}_config', {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration sections"""
        return {
            'service': self.service_config,
            'aws': self.aws_config,
            'recommendation': self.recommendation_config,
            'rightsizing': self.rightsizing_config,
            'gpu': self.gpu_config,
            'batch': self.batch_config,
            'routing': self.routing_config,
            'cost_performance': self.cost_performance_config,
            'sla': self.sla_config,
            'hybrid': self.hybrid_config,
            'edge': self.edge_config,
            'green': self.green_config,
            'logging': self.logging_config,
            'monitoring': self.monitoring_config,
            'security': self.security_config
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'