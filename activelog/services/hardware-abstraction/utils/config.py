"""
Configuration Management
"""

import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for hardware abstraction system"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.json"
        self.config_data = {}
        self.load_config()
    
    def load_config(self):
        """Load configuration from file or use defaults"""
        default_config = {
            "server": {
                "host": "0.0.0.0",
                "port": int(os.getenv("PORT", 8420)),
                "debug": False
            },
            "discovery": {
                "mdns_enabled": True,
                "network_scan_enabled": True,
                "scan_interval": 30,
                "protocols": ["tcp", "udp", "http"]
            },
            "communication": {
                "max_connections": 100,
                "timeout": 30,
                "retry_attempts": 3,
                "protocols": {
                    "usb": {"enabled": True, "max_devices": 10},
                    "ethernet": {"enabled": True, "max_bandwidth": "1Gbps"},
                    "wifi": {"enabled": True, "max_bandwidth": "100Mbps"},
                    "bluetooth": {"enabled": True, "max_devices": 8},
                    "serial": {"enabled": True, "baud_rate": 115200}
                }
            },
            "device_types": {
                "input_devices": {
                    "cameras": {"max_resolution": "4K", "max_fps": 60},
                    "sensors": {"sampling_rate": 1000},
                    "microphones": {"sample_rate": 48000, "bit_depth": 24}
                },
                "output_devices": {
                    "displays": {"max_resolution": "8K", "max_refresh": 120},
                    "printers": {"max_resolution": "0.1mm"},
                    "speakers": {"frequency_range": "20Hz-20kHz"}
                }
            },
            "monitoring": {
                "health_check_interval": 10,
                "performance_logging": True,
                "alert_thresholds": {
                    "cpu_usage": 80,
                    "memory_usage": 85,
                    "disk_usage": 90,
                    "temperature": 70
                }
            },
            "security": {
                "enable_encryption": True,
                "require_authentication": False,
                "allowed_ips": ["127.0.0.1", "192.168.0.0/16"]
            }
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    file_config = json.load(f)
                    self.config_data = self._merge_configs(default_config, file_config)
                logger.info(f"Loaded configuration from {self.config_file}")
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")
                self.config_data = default_config
        else:
            self.config_data = default_config
            logger.info("Using default configuration")
    
    def _merge_configs(self, default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge configuration dictionaries"""
        result = default.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value
        return result
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        keys = key.split('.')
        value = self.config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot notation key"""
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config_data, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration data"""
        return self.config_data.copy()
    
    def validate(self) -> bool:
        """Validate configuration"""
        required_keys = [
            "server.host",
            "server.port",
            "discovery.mdns_enabled",
            "communication.max_connections"
        ]
        
        for key in required_keys:
            if self.get(key) is None:
                logger.error(f"Missing required configuration key: {key}")
                return False
        
        return True