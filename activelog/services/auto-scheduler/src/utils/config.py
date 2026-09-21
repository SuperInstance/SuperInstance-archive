import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConfigManager:
    """Configuration management for the auto-scheduler service"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self.config = self._load_config()
        self._validate_config()
    
    def _find_config_file(self) -> str:
        """Find configuration file in standard locations"""
        possible_paths = [
            os.environ.get('AUTO_SCHEDULER_CONFIG'),
            '/home/activeloguser/activelog/services/auto-scheduler/config/config.yaml',
            '/home/activeloguser/activelog/services/auto-scheduler/config/config.json',
            '/home/activeloguser/activelog/services/auto-scheduler/config.yaml',
            '/home/activeloguser/activelog/services/auto-scheduler/config.json'
        ]
        
        for path in possible_paths:
            if path and Path(path).exists():
                return path
        
        # Return default path (will be created with defaults)
        return '/home/activeloguser/activelog/services/auto-scheduler/config/config.yaml'
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create defaults"""
        config_path = Path(self.config_path)
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    if config_path.suffix.lower() == '.yaml' or config_path.suffix.lower() == '.yml':
                        return yaml.safe_load(f)
                    else:
                        return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {e}")
                return self._get_default_config()
        else:
            logger.info(f"Config file not found at {config_path}, using defaults")
            config = self._get_default_config()
            self._save_default_config(config_path, config)
            return config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'service': {
                'name': 'auto-scheduler',
                'version': '1.0.0',
                'port': 8500,
                'host': '0.0.0.0',
                'debug': False
            },
            
            'scheduler': {
                'task_check_interval': 30,
                'backup_check_interval': 300,
                'report_interval': 60,
                'max_concurrent_tasks': 10
            },
            
            'bot_manager': {
                'night_start_hour': 22,
                'night_end_hour': 6,
                'night_acceleration_hour': 3,
                'night_multiplier': 2.0,
                'throttle_threshold': 0.5,
                'default_daily_limit': 5.0
            },
            
            'backup': {
                'enabled': True,
                'backup_path': '/home/activeloguser/activelog/backups',
                'source_path': '/home/activeloguser/activelog',
                'compression': True,
                'verification': True,
                'cloud_sync': False,
                'retention': {
                    'incremental': {'days': 7},
                    'stability': {'weeks': 4},
                    'milestone': {'months': 12},
                    'archive': {'years': 3},
                    'permanent': {'years': 50}
                }
            },
            
            'reporting': {
                'db_path': '/home/activeloguser/activelog/services/auto-scheduler/data/progress.db',
                'report_retention_days': 90,
                'cost_per_bot_hour': 0.50,
                'enable_minute_updates': True,
                'enable_hourly_summaries': True,
                'enable_daily_reports': True
            },
            
            'logging': {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': '/home/activeloguser/activelog/services/auto-scheduler/logs/auto-scheduler.log',
                'max_bytes': 10485760,  # 10MB
                'backup_count': 5
            },
            
            'security': {
                'api_key_required': False,
                'allowed_hosts': ['localhost', '127.0.0.1'],
                'max_request_size': 1048576  # 1MB
            },
            
            'database': {
                'url': 'sqlite:///home/activeloguser/activelog/services/auto-scheduler/data/auto_scheduler.db',
                'pool_size': 5,
                'max_overflow': 10
            }
        }
    
    def _save_default_config(self, config_path: Path, config: Dict[str, Any]):
        """Save default configuration to file"""
        try:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config, f, indent=2)
            
            logger.info(f"Created default config at {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving default config: {e}")
    
    def _validate_config(self):
        """Validate configuration values"""
        required_sections = ['service', 'scheduler', 'bot_manager', 'backup', 'reporting']
        
        for section in required_sections:
            if section not in self.config:
                logger.error(f"Missing required config section: {section}")
                raise ValueError(f"Missing required config section: {section}")
        
        # Validate service config
        service = self.config['service']
        if 'port' not in service or not isinstance(service['port'], int):
            raise ValueError("Service port must be an integer")
        
        if service['port'] < 1 or service['port'] > 65535:
            raise ValueError("Service port must be between 1 and 65535")
        
        # Validate bot manager config
        bot_config = self.config['bot_manager']
        if bot_config['night_start_hour'] < 0 or bot_config['night_start_hour'] > 23:
            raise ValueError("night_start_hour must be between 0 and 23")
        
        if bot_config['night_end_hour'] < 0 or bot_config['night_end_hour'] > 23:
            raise ValueError("night_end_hour must be between 0 and 23")
        
        if bot_config['night_multiplier'] <= 0:
            raise ValueError("night_multiplier must be positive")
        
        # Validate paths
        backup_config = self.config['backup']
        backup_path = Path(backup_config['backup_path'])
        source_path = Path(backup_config['source_path'])
        
        if not source_path.exists():
            logger.warning(f"Source path does not exist: {source_path}")
        
        # Create backup path if it doesn't exist
        try:
            backup_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Cannot create backup path {backup_path}: {e}")
        
        logger.info("Configuration validation completed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'service.port')"""
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value using dot notation"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self):
        """Save current configuration to file"""
        try:
            config_path = Path(self.config_path)
            
            with open(config_path, 'w') as f:
                if config_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self.config, f, indent=2)
            
            logger.info(f"Configuration saved to {config_path}")
            
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            raise
    
    def reload(self):
        """Reload configuration from file"""
        self.config = self._load_config()
        self._validate_config()
        logger.info("Configuration reloaded")
    
    def get_environment_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables"""
        overrides = {}
        prefix = 'AUTO_SCHEDULER_'
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace('_', '.')
                
                # Try to parse as JSON first, then as string
                try:
                    parsed_value = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed_value = value
                
                overrides[config_key] = parsed_value
        
        return overrides
    
    def apply_environment_overrides(self):
        """Apply environment variable overrides to configuration"""
        overrides = self.get_environment_overrides()
        
        for key, value in overrides.items():
            self.set(key, value)
            logger.info(f"Applied environment override: {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """Get entire configuration section"""
        return self.config.get(section, {})
    
    def to_dict(self) -> Dict[str, Any]:
        """Get full configuration as dictionary"""
        return self.config.copy()
    
    def create_backup(self) -> str:
        """Create a backup of the current configuration"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            config_path = Path(self.config_path)
            backup_path = config_path.parent / f"{config_path.stem}_backup_{timestamp}{config_path.suffix}"
            
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(backup_path, 'w') as f:
                if backup_path.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(self.config, f, default_flow_style=False, indent=2)
                else:
                    json.dump(self.config, f, indent=2)
            
            logger.info(f"Configuration backup created: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Error creating configuration backup: {e}")
            raise
    
    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore configuration from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create current config backup before restore
            current_backup = self.create_backup()
            logger.info(f"Created safety backup: {current_backup}")
            
            # Load backup configuration
            with open(backup_file, 'r') as f:
                if backup_file.suffix.lower() in ['.yaml', '.yml']:
                    backup_config = yaml.safe_load(f)
                else:
                    backup_config = json.load(f)
            
            # Validate backup config
            old_config = self.config
            self.config = backup_config
            
            try:
                self._validate_config()
                self.save()  # Save restored config
                logger.info(f"Configuration restored from {backup_path}")
                return True
                
            except Exception as e:
                # Restore failed, revert to old config
                self.config = old_config
                logger.error(f"Backup validation failed, reverted: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error restoring configuration: {e}")
            return False
    
    def get_config_history(self) -> List[Dict[str, Any]]:
        """Get list of available configuration backups"""
        try:
            config_path = Path(self.config_path)
            backup_pattern = f"{config_path.stem}_backup_*{config_path.suffix}"
            backup_files = list(config_path.parent.glob(backup_pattern))
            
            history = []
            for backup_file in sorted(backup_files, key=lambda x: x.stat().st_mtime, reverse=True):
                stat = backup_file.stat()
                history.append({
                    'path': str(backup_file),
                    'name': backup_file.name,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'size_bytes': stat.st_size
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Error getting config history: {e}")
            return []
    
    def update_config_dynamically(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration dynamically with validation"""
        try:
            # Create backup before changes
            backup_path = self.create_backup()
            
            # Apply updates
            old_values = {}
            for key, value in updates.items():
                old_values[key] = self.get(key)
                self.set(key, value)
            
            # Validate new configuration
            try:
                self._validate_config()
                self.save()
                
                logger.info(f"Configuration updated successfully")
                return {
                    'success': True,
                    'backup_created': backup_path,
                    'updated_keys': list(updates.keys()),
                    'old_values': old_values
                }
                
            except Exception as e:
                # Validation failed, revert changes
                for key, old_value in old_values.items():
                    if old_value is not None:
                        self.set(key, old_value)
                    else:
                        # Remove the key if it didn't exist before
                        try:
                            keys = key.split('.')
                            config = self.config
                            for k in keys[:-1]:
                                config = config[k]
                            del config[keys[-1]]
                        except (KeyError, TypeError):
                            pass
                
                logger.error(f"Configuration validation failed, reverted: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'reverted': True
                }
                
        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_service_integrations(self) -> Dict[str, Any]:
        """Get configuration for service integrations"""
        integrations = {
            'database': {
                'enabled': True,
                'connection_string': self.get('database.url'),
                'health_check_interval': 300  # 5 minutes
            },
            'monitoring': {
                'enabled': True,
                'metrics_endpoint': f"http://{self.get('service.host')}:{self.get('service.port')}/monitoring/health",
                'alerts_enabled': True
            },
            'backup': {
                'enabled': self.get('backup.enabled', True),
                'cloud_sync': self.get('backup.cloud_sync', False),
                'verification': self.get('backup.verification', True)
            },
            'reporting': {
                'enabled': True,
                'minute_updates': self.get('reporting.enable_minute_updates', True),
                'hourly_summaries': self.get('reporting.enable_hourly_summaries', True),
                'daily_reports': self.get('reporting.enable_daily_reports', True)
            }
        }
        
        return integrations
    
    def validate_service_health(self) -> Dict[str, Any]:
        """Validate service health configuration"""
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_health': 'healthy',
            'checks': []
        }
        
        try:
            # Check service configuration
            service_config = self.get_section('service')
            if service_config.get('port', 0) < 1024 and os.getuid() != 0:
                health_status['checks'].append({
                    'component': 'service',
                    'status': 'warning',
                    'message': 'Service port < 1024 may require root privileges'
                })
            else:
                health_status['checks'].append({
                    'component': 'service',
                    'status': 'healthy',
                    'message': 'Service configuration valid'
                })
            
            # Check database configuration
            db_path = Path(self.get('database.url', '').replace('sqlite:///', ''))
            if db_path.parent.exists() and not os.access(db_path.parent, os.W_OK):
                health_status['checks'].append({
                    'component': 'database',
                    'status': 'critical',
                    'message': 'Database directory is not writable'
                })
                health_status['overall_health'] = 'critical'
            else:
                health_status['checks'].append({
                    'component': 'database',
                    'status': 'healthy',
                    'message': 'Database configuration valid'
                })
            
            # Check backup configuration
            backup_path = Path(self.get('backup.backup_path'))
            source_path = Path(self.get('backup.source_path'))
            
            if not source_path.exists():
                health_status['checks'].append({
                    'component': 'backup',
                    'status': 'warning',
                    'message': f'Source path does not exist: {source_path}'
                })
                if health_status['overall_health'] == 'healthy':
                    health_status['overall_health'] = 'warning'
            else:
                health_status['checks'].append({
                    'component': 'backup',
                    'status': 'healthy',
                    'message': 'Backup configuration valid'
                })
            
            # Check logging configuration
            log_path = Path(self.get('logging.file'))
            if not log_path.parent.exists():
                try:
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    health_status['checks'].append({
                        'component': 'logging',
                        'status': 'healthy',
                        'message': 'Logging directory created'
                    })
                except Exception as e:
                    health_status['checks'].append({
                        'component': 'logging',
                        'status': 'warning',
                        'message': f'Cannot create log directory: {e}'
                    })
                    if health_status['overall_health'] == 'healthy':
                        health_status['overall_health'] = 'warning'
            else:
                health_status['checks'].append({
                    'component': 'logging',
                    'status': 'healthy',
                    'message': 'Logging configuration valid'
                })
            
        except Exception as e:
            health_status['overall_health'] = 'error'
            health_status['checks'].append({
                'component': 'configuration',
                'status': 'error',
                'message': f'Configuration validation error: {e}'
            })
        
        return health_status