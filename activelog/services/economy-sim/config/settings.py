#!/usr/bin/env python3
"""
Configuration settings for ActiveLog Economic Simulator
"""

import os
from typing import Dict, Any


class EconomySimConfig:
    """Configuration management for economic simulator"""
    
    def __init__(self):
        self.service_port = int(os.getenv('ECONOMY_SIM_PORT', 8340))
        self.environment = os.getenv('ENVIRONMENT', 'development')
        
        # Service configuration
        self.service_config = {
            'name': 'ActiveLog Economic Simulator',
            'version': '1.0.0',
            'description': 'Comprehensive economic modeling for user growth, infrastructure costs, CCC economy, pricing strategies, creator economics, and market dynamics',
            'port': self.service_port,
            'host': '0.0.0.0',
            'debug': self.environment == 'development'
        }
        
        # Simulation configuration
        self.simulation_config = {
            'max_simulation_duration_months': int(os.getenv('MAX_SIMULATION_DURATION', 60)),  # 5 years max
            'default_simulation_duration_months': 24,
            'monte_carlo_iterations': int(os.getenv('MONTE_CARLO_ITERATIONS', 1000)),
            'confidence_intervals': [0.05, 0.25, 0.5, 0.75, 0.95],  # 5th to 95th percentiles
            'simulation_step_size': 'monthly',
            'parallel_processing_enabled': os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
        }
        
        # User growth model configuration
        self.user_growth_config = {
            'max_market_size': int(os.getenv('MAX_MARKET_SIZE', 100000000)),  # 100M users max
            'min_growth_rate': float(os.getenv('MIN_GROWTH_RATE', 0.01)),     # 1% min monthly
            'max_growth_rate': float(os.getenv('MAX_GROWTH_RATE', 0.50)),     # 50% max monthly
            'churn_rate_bounds': [0.01, 0.30],  # 1% to 30% monthly churn
            'viral_coefficient_bounds': [0.0, 1.0],
            'network_effect_threshold': int(os.getenv('NETWORK_EFFECT_THRESHOLD', 10000)),
            'market_saturation_factor': float(os.getenv('MARKET_SATURATION_FACTOR', 0.8))
        }
        
        # Infrastructure cost model configuration
        self.infrastructure_config = {
            'cost_update_frequency_days': int(os.getenv('COST_UPDATE_FREQUENCY', 30)),
            'cloud_providers': ['aws', 'azure', 'gcp', 'hybrid'],
            'scaling_strategies': ['fixed_capacity', 'auto_scaling', 'predictive_scaling', 'reserved_instances', 'spot_instances', 'hybrid_scaling'],
            'cost_optimization_threshold': float(os.getenv('COST_OPTIMIZATION_THRESHOLD', 0.1)),  # 10%
            'currency': os.getenv('CURRENCY', 'USD'),
            'cost_projection_accuracy': float(os.getenv('COST_PROJECTION_ACCURACY', 0.85))  # 85% accuracy
        }
        
        # CCC economy configuration
        self.ccc_economy_config = {
            'initial_supply': int(os.getenv('CCC_INITIAL_SUPPLY', 1000000)),  # 1M credits
            'initial_price_usd': float(os.getenv('CCC_INITIAL_PRICE', 0.10)),  # $0.10 per credit
            'supply_cap': int(os.getenv('CCC_SUPPLY_CAP', 1000000000)),  # 1B credits max
            'price_volatility_cap': float(os.getenv('CCC_PRICE_VOLATILITY_CAP', 0.50)),  # 50% max volatility
            'minimum_price': float(os.getenv('CCC_MINIMUM_PRICE', 0.01)),   # $0.01 floor
            'maximum_price': float(os.getenv('CCC_MAXIMUM_PRICE', 10.00)),  # $10.00 ceiling
            'market_maker_enabled': os.getenv('CCC_MARKET_MAKER_ENABLED', 'true').lower() == 'true',
            'transaction_fee_rate': float(os.getenv('CCC_TRANSACTION_FEE', 0.02))  # 2% fee
        }
        
        # Creator economics configuration
        self.creator_config = {
            'revenue_sharing_models': ['flat_rate', 'percentage_based', 'tier_based', 'performance_based'],
            'default_revenue_share': float(os.getenv('DEFAULT_REVENUE_SHARE', 0.70)),  # 70% to creators
            'minimum_payout_threshold': float(os.getenv('MIN_PAYOUT_THRESHOLD', 50.00)),  # $50 minimum
            'creator_tier_thresholds': {
                'bronze': 1000,    # $1K revenue
                'silver': 10000,   # $10K revenue
                'gold': 100000,    # $100K revenue
                'platinum': 1000000 # $1M revenue
            },
            'performance_bonus_multiplier': float(os.getenv('PERFORMANCE_BONUS', 1.2))  # 20% bonus
        }
        
        # Pricing strategy configuration
        self.pricing_config = {
            'pricing_models': ['freemium', 'subscription', 'pay_per_use', 'tiered', 'enterprise'],
            'price_elasticity_bounds': [-3.0, -0.1],  # Demand elasticity bounds
            'competitive_pricing_factor': float(os.getenv('COMPETITIVE_PRICING_FACTOR', 0.9)),  # 10% below competition
            'premium_pricing_threshold': float(os.getenv('PREMIUM_PRICING_THRESHOLD', 1.2)),   # 20% above market
            'discount_limits': {
                'student_max': 0.50,    # 50% max student discount
                'volume_max': 0.30,     # 30% max volume discount
                'promotional_max': 0.25  # 25% max promotional discount
            }
        }
        
        # Market dynamics configuration
        self.market_dynamics_config = {
            'competitor_response_time_days': int(os.getenv('COMPETITOR_RESPONSE_TIME', 30)),
            'market_entry_barriers': ['high', 'medium', 'low'],
            'technology_disruption_probability': float(os.getenv('TECH_DISRUPTION_PROB', 0.1)),  # 10% chance
            'regulatory_change_probability': float(os.getenv('REGULATORY_CHANGE_PROB', 0.05)),   # 5% chance
            'economic_cycle_duration_months': int(os.getenv('ECONOMIC_CYCLE_DURATION', 48)),     # 4 years
            'market_volatility_factor': float(os.getenv('MARKET_VOLATILITY_FACTOR', 0.15))       # 15% volatility
        }
        
        # Network effects configuration
        self.network_effects_config = {
            'critical_mass_threshold': int(os.getenv('CRITICAL_MASS_THRESHOLD', 10000)),
            'network_value_exponent': float(os.getenv('NETWORK_VALUE_EXPONENT', 1.5)),  # Metcalfe's law variation
            'viral_spreading_rate': float(os.getenv('VIRAL_SPREADING_RATE', 0.1)),      # 10% viral rate
            'network_decay_rate': float(os.getenv('NETWORK_DECAY_RATE', 0.02)),         # 2% monthly decay
            'platform_lock_in_strength': float(os.getenv('PLATFORM_LOCK_IN', 0.3))     # 30% lock-in effect
        }
        
        # Profitability prediction configuration
        self.profitability_config = {
            'target_profit_margin': float(os.getenv('TARGET_PROFIT_MARGIN', 0.20)),     # 20% margin
            'break_even_timeframe_months': int(os.getenv('BREAK_EVEN_TIMEFRAME', 36)),  # 3 years
            'cash_flow_discount_rate': float(os.getenv('DISCOUNT_RATE', 0.12)),         # 12% discount rate
            'growth_investment_ratio': float(os.getenv('GROWTH_INVESTMENT_RATIO', 0.30)), # 30% reinvestment
            'operating_leverage_factor': float(os.getenv('OPERATING_LEVERAGE', 2.0))    # 2x operating leverage
        }
        
        # Data storage configuration
        self.data_config = {
            'simulation_data_retention_days': int(os.getenv('SIMULATION_DATA_RETENTION', 365)),
            'cache_ttl_hours': int(os.getenv('CACHE_TTL_HOURS', 24)),
            'data_export_formats': ['json', 'csv', 'excel', 'pdf'],
            'compression_enabled': os.getenv('COMPRESSION_ENABLED', 'true').lower() == 'true',
            'backup_frequency_hours': int(os.getenv('BACKUP_FREQUENCY', 24))
        }
        
        # Analytics configuration
        self.analytics_config = {
            'metrics_aggregation_intervals': ['hourly', 'daily', 'weekly', 'monthly'],
            'real_time_metrics_enabled': os.getenv('REAL_TIME_METRICS', 'true').lower() == 'true',
            'anomaly_detection_enabled': os.getenv('ANOMALY_DETECTION', 'true').lower() == 'true',
            'predictive_analytics_enabled': os.getenv('PREDICTIVE_ANALYTICS', 'true').lower() == 'true',
            'custom_metrics_limit': int(os.getenv('CUSTOM_METRICS_LIMIT', 100))
        }
        
        # Security configuration
        self.security_config = {
            'api_key_required': self.environment == 'production',
            'rate_limiting_enabled': True,
            'max_requests_per_minute': int(os.getenv('MAX_REQUESTS_PER_MINUTE', 100)),
            'simulation_complexity_limit': int(os.getenv('SIMULATION_COMPLEXITY_LIMIT', 1000)),
            'data_encryption_enabled': os.getenv('DATA_ENCRYPTION', 'true').lower() == 'true',
            'audit_logging_enabled': self.environment == 'production'
        }
        
        # Integration configuration
        self.integration_config = {
            'external_data_sources': {
                'market_data_api': os.getenv('MARKET_DATA_API_URL', ''),
                'economic_indicators_api': os.getenv('ECONOMIC_INDICATORS_API', ''),
                'cloud_pricing_apis': {
                    'aws': os.getenv('AWS_PRICING_API', ''),
                    'azure': os.getenv('AZURE_PRICING_API', ''),
                    'gcp': os.getenv('GCP_PRICING_API', '')
                }
            },
            'webhook_endpoints': {
                'simulation_complete': os.getenv('WEBHOOK_SIMULATION_COMPLETE', ''),
                'alert_notifications': os.getenv('WEBHOOK_ALERTS', '')
            },
            'export_destinations': {
                's3_bucket': os.getenv('EXPORT_S3_BUCKET', ''),
                'database_connection': os.getenv('EXPORT_DB_CONNECTION', '')
            }
        }
        
        # Logging configuration
        self.logging_config = {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file': f'/home/activeloguser/activelog/logs/economy-sim.log',
            'max_file_size_mb': int(os.getenv('LOG_MAX_FILE_SIZE_MB', 100)),
            'backup_count': int(os.getenv('LOG_BACKUP_COUNT', 5)),
            'structured_logging': os.getenv('STRUCTURED_LOGGING', 'false').lower() == 'true'
        }
        
        # Monitoring configuration
        self.monitoring_config = {
            'metrics_enabled': True,
            'metrics_port': int(os.getenv('METRICS_PORT', 9340)),
            'health_check_enabled': True,
            'performance_tracking': True,
            'alerts_enabled': self.environment == 'production',
            'prometheus_enabled': os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true',
            'grafana_dashboard_enabled': os.getenv('GRAFANA_ENABLED', 'true').lower() == 'true'
        }

    def get_config(self, section: str) -> Dict[str, Any]:
        """Get configuration for a specific section"""
        return getattr(self, f'{section}_config', {})
    
    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration sections"""
        return {
            'service': self.service_config,
            'simulation': self.simulation_config,
            'user_growth': self.user_growth_config,
            'infrastructure': self.infrastructure_config,
            'ccc_economy': self.ccc_economy_config,
            'creator': self.creator_config,
            'pricing': self.pricing_config,
            'market_dynamics': self.market_dynamics_config,
            'network_effects': self.network_effects_config,
            'profitability': self.profitability_config,
            'data': self.data_config,
            'analytics': self.analytics_config,
            'security': self.security_config,
            'integration': self.integration_config,
            'logging': self.logging_config,
            'monitoring': self.monitoring_config
        }
    
    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == 'production'
    
    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == 'development'
    
    def validate_simulation_params(self, params: Dict[str, Any]) -> bool:
        """Validate simulation parameters against configuration limits"""
        
        # Check simulation duration
        duration = params.get('simulation_duration_months', 0)
        if duration > self.simulation_config['max_simulation_duration_months']:
            return False
        
        # Check user growth parameters
        if 'user_growth_params' in params:
            growth_params = params['user_growth_params']
            
            # Check growth rate bounds
            growth_rate = growth_params.get('monthly_growth_rate', 0)
            if not (self.user_growth_config['min_growth_rate'] <= growth_rate <= self.user_growth_config['max_growth_rate']):
                return False
            
            # Check market size
            market_size = growth_params.get('target_market_size', 0)
            if market_size > self.user_growth_config['max_market_size']:
                return False
        
        # Check CCC economy parameters
        if 'ccc_economy_params' in params:
            ccc_params = params['ccc_economy_params']
            initial_conditions = ccc_params.get('initial_conditions', {})
            
            # Check initial price bounds
            initial_price = initial_conditions.get('initial_price', 0)
            if not (self.ccc_economy_config['minimum_price'] <= initial_price <= self.ccc_economy_config['maximum_price']):
                return False
            
            # Check supply bounds
            initial_supply = initial_conditions.get('initial_supply', 0)
            if initial_supply > self.ccc_economy_config['supply_cap']:
                return False
        
        return True
    
    def get_default_simulation_params(self) -> Dict[str, Any]:
        """Get default simulation parameters"""
        return {
            'simulation_duration_months': self.simulation_config['default_simulation_duration_months'],
            'user_growth_params': {
                'initial_users': 1000,
                'monthly_growth_rate': 0.15,
                'monthly_churn_rate': 0.05,
                'target_market_size': 1000000,
                'viral_coefficient': 0.1
            },
            'infrastructure_params': {
                'scaling_strategy': 'auto_scaling',
                'cloud_provider': 'aws',
                'cost_optimization_enabled': True
            },
            'ccc_economy_params': {
                'initial_conditions': {
                    'initial_supply': self.ccc_economy_config['initial_supply'],
                    'initial_price': self.ccc_economy_config['initial_price_usd']
                },
                'supply_parameters': {
                    'base_supply_rate': 1000000,
                    'supply_elasticity': 0.5
                },
                'demand_parameters': {
                    'base_demand_rate': 800000,
                    'price_elasticity': -0.8
                }
            },
            'pricing_params': {
                'pricing_model': 'freemium',
                'optimization_goals': ['revenue_maximization', 'user_acquisition']
            }
        }
    
    def get_performance_thresholds(self) -> Dict[str, Any]:
        """Get performance monitoring thresholds"""
        return {
            'simulation_timeout_minutes': 30,
            'max_memory_usage_gb': 8,
            'max_cpu_usage_percent': 80,
            'response_time_p95_ms': 5000,
            'error_rate_threshold_percent': 1.0,
            'queue_depth_threshold': 100
        }