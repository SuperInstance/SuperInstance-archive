"""
ActiveLog Integration Hub - Centralized Configuration Management
Dynamic configuration system for all 70+ services with hot-reloading,
environment-specific configs, and secure secret management
"""

import asyncio
import json
import yaml
import os
import hashlib
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime, timedelta
import aiofiles
import aiohttp
from cryptography.fernet import Fernet
import base64
from service_discovery import ServiceDiscovery
import fnmatch

class ConfigFormat(Enum):
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    INI = "ini"
    ENV = "env"

class ConfigScope(Enum):
    GLOBAL = "global"
    SERVICE = "service"
    ENVIRONMENT = "environment"
    INSTANCE = "instance"

class ConfigSource(Enum):
    FILE = "file"
    DATABASE = "database"
    CONSUL = "consul"
    ETCD = "etcd"
    ENVIRONMENT = "environment"
    VAULT = "vault"
    REMOTE_HTTP = "remote_http"

@dataclass
class ConfigValue:
    key: str
    value: Any
    data_type: str
    encrypted: bool = False
    source: str = "file"
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 1
    description: str = ""
    validation_rules: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

@dataclass
class ConfigSchema:
    key: str
    data_type: str
    required: bool = False
    default_value: Any = None
    validation_rules: List[str] = field(default_factory=list)
    description: str = ""
    sensitive: bool = False
    environment_specific: bool = False

@dataclass
class ServiceConfig:
    service_name: str
    environment: str
    config_values: Dict[str, ConfigValue] = field(default_factory=dict)
    config_hash: str = ""
    last_updated: datetime = field(default_factory=datetime.now)
    version: int = 1
    watchers: Set[str] = field(default_factory=set)

class ConfigWatcher:
    """Watches for configuration changes"""
    def __init__(self, service_name: str, callback: Callable[[Dict[str, Any]], None]):
        self.service_name = service_name
        self.callback = callback
        self.active = True
        self.last_hash = ""
    
    async def notify(self, config_data: Dict[str, Any], config_hash: str):
        """Notify of configuration change"""
        if self.active and config_hash != self.last_hash:
            self.last_hash = config_hash
            try:
                if asyncio.iscoroutinefunction(self.callback):
                    await self.callback(config_data)
                else:
                    self.callback(config_data)
            except Exception as e:
                logging.error(f"Config watcher callback failed for {self.service_name}: {e}")

class SecretManager:
    """Manages encrypted secrets"""
    def __init__(self, encryption_key: Optional[str] = None):
        if encryption_key:
            self.cipher = Fernet(encryption_key.encode())
        else:
            # Generate or load encryption key
            key_file = Path("/home/activeloguser/activelog/.config_encryption_key")
            if key_file.exists():
                with open(key_file, 'rb') as f:
                    key = f.read()
            else:
                key = Fernet.generate_key()
                key_file.parent.mkdir(exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                os.chmod(key_file, 0o600)  # Restrict permissions
            
            self.cipher = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        """Encrypt a value"""
        return base64.b64encode(self.cipher.encrypt(value.encode())).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt a value"""
        return self.cipher.decrypt(base64.b64decode(encrypted_value)).decode()
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value is encrypted"""
        try:
            base64.b64decode(value)
            self.cipher.decrypt(base64.b64decode(value))
            return True
        except:
            return False

class ConfigValidator:
    """Validates configuration values"""
    
    @staticmethod
    def validate_value(value: Any, rules: List[str]) -> List[str]:
        """Validate value against rules"""
        errors = []
        
        for rule in rules:
            if rule.startswith("type:"):
                expected_type = rule.split(":", 1)[1]
                if not ConfigValidator._check_type(value, expected_type):
                    errors.append(f"Expected type {expected_type}, got {type(value).__name__}")
            
            elif rule.startswith("range:"):
                range_spec = rule.split(":", 1)[1]
                if not ConfigValidator._check_range(value, range_spec):
                    errors.append(f"Value {value} not in range {range_spec}")
            
            elif rule.startswith("regex:"):
                import re
                pattern = rule.split(":", 1)[1]
                if isinstance(value, str) and not re.match(pattern, value):
                    errors.append(f"Value '{value}' does not match pattern {pattern}")
            
            elif rule.startswith("enum:"):
                allowed_values = rule.split(":", 1)[1].split(",")
                if str(value) not in allowed_values:
                    errors.append(f"Value '{value}' not in allowed values: {allowed_values}")
            
            elif rule == "required" and value is None:
                errors.append("Required value is missing")
        
        return errors
    
    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict
        }
        
        expected = type_map.get(expected_type)
        if expected:
            return isinstance(value, expected)
        
        return True
    
    @staticmethod
    def _check_range(value: Any, range_spec: str) -> bool:
        """Check if numeric value is in range"""
        try:
            if "-" in range_spec:
                min_val, max_val = range_spec.split("-", 1)
                return float(min_val) <= float(value) <= float(max_val)
        except:
            pass
        
        return True

class ConfigurationManager:
    """Central configuration management system"""
    
    def __init__(self, discovery: ServiceDiscovery, config_dir: str = "/home/activeloguser/activelog/config"):
        self.discovery = discovery
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Core components
        self.secret_manager = SecretManager()
        self.validator = ConfigValidator()
        
        # Configuration storage
        self.service_configs: Dict[str, ServiceConfig] = {}
        self.global_config: Dict[str, ConfigValue] = {}
        self.config_schemas: Dict[str, ConfigSchema] = {}
        
        # Watchers and change tracking
        self.watchers: Dict[str, List[ConfigWatcher]] = {}
        self.config_hashes: Dict[str, str] = {}
        
        # Environment settings
        self.current_environment = os.getenv("ACTIVELOG_ENV", "development")
        self.environments = ["development", "staging", "production"]
        
        # Configuration sources
        self.config_sources: Dict[ConfigSource, Any] = {}
        
        # Background tasks
        self.reload_interval = 60  # seconds
        self.running = False
        
    async def initialize(self):
        """Initialize the configuration manager"""
        # Load configuration schemas
        await self.load_config_schemas()
        
        # Discover services and load their configurations
        await self.discovery.discover_all_services()
        await self.load_all_service_configs()
        
        # Setup configuration sources
        await self.setup_config_sources()
        
        # Start background tasks
        self.running = True
        asyncio.create_task(self.config_reload_task())
        asyncio.create_task(self.config_sync_task())
        
        logging.info(f"Configuration manager initialized for environment: {self.current_environment}")
        logging.info(f"Managing configs for {len(self.service_configs)} services")
    
    async def load_config_schemas(self):
        """Load configuration schemas"""
        schema_file = self.config_dir / "schemas" / "config_schemas.yaml"
        
        if schema_file.exists():
            try:
                async with aiofiles.open(schema_file, 'r') as f:
                    content = await f.read()
                    schemas_data = yaml.safe_load(content)
                    
                    for service_name, schema_config in schemas_data.items():
                        for key, schema_def in schema_config.items():
                            schema_key = f"{service_name}.{key}"
                            self.config_schemas[schema_key] = ConfigSchema(
                                key=schema_key,
                                data_type=schema_def.get('type', 'str'),
                                required=schema_def.get('required', False),
                                default_value=schema_def.get('default'),
                                validation_rules=schema_def.get('validation', []),
                                description=schema_def.get('description', ''),
                                sensitive=schema_def.get('sensitive', False),
                                environment_specific=schema_def.get('environment_specific', False)
                            )
            except Exception as e:
                logging.warning(f"Failed to load config schemas: {e}")
    
    async def load_all_service_configs(self):
        """Load configurations for all discovered services"""
        for service_name in self.discovery.services.keys():
            await self.load_service_config(service_name)
        
        # Load global configuration
        await self.load_global_config()
    
    async def load_service_config(self, service_name: str) -> ServiceConfig:
        """Load configuration for a specific service"""
        # Try different configuration file formats
        config_files = [
            self.config_dir / "services" / f"{service_name}.yaml",
            self.config_dir / "services" / f"{service_name}.yml",
            self.config_dir / "services" / f"{service_name}.json",
            self.config_dir / "environments" / self.current_environment / f"{service_name}.yaml",
            self.config_dir / "environments" / self.current_environment / f"{service_name}.json"
        ]
        
        config_values = {}
        
        # Load base configuration
        for config_file in config_files:
            if config_file.exists():
                config_data = await self.load_config_file(config_file)
                if config_data:
                    config_values.update(await self.process_config_data(config_data, service_name))
                    break
        
        # Load environment-specific overrides
        env_config_file = self.config_dir / "environments" / self.current_environment / f"{service_name}.yaml"
        if env_config_file.exists():
            env_config = await self.load_config_file(env_config_file)
            if env_config:
                env_values = await self.process_config_data(env_config, service_name)
                config_values.update(env_values)
        
        # Load environment variables
        env_values = await self.load_environment_variables(service_name)
        config_values.update(env_values)
        
        # Create service config
        service_config = ServiceConfig(
            service_name=service_name,
            environment=self.current_environment,
            config_values=config_values
        )
        
        # Calculate config hash
        service_config.config_hash = self.calculate_config_hash(config_values)
        
        # Store configuration
        self.service_configs[service_name] = service_config
        
        return service_config
    
    async def load_config_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load configuration from file"""
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
            
            if file_path.suffix in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            elif file_path.suffix == '.json':
                return json.loads(content)
            elif file_path.suffix == '.toml':
                try:
                    import toml
                    return toml.loads(content)
                except ImportError:
                    logging.warning("TOML support not available")
            
        except Exception as e:
            logging.error(f"Failed to load config file {file_path}: {e}")
        
        return None
    
    async def process_config_data(self, config_data: Dict[str, Any], service_name: str) -> Dict[str, ConfigValue]:
        """Process raw configuration data into ConfigValue objects"""
        config_values = {}
        
        def process_nested_config(data: Dict[str, Any], prefix: str = ""):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                
                if isinstance(value, dict):
                    # Recursively process nested configuration
                    process_nested_config(value, full_key)
                else:
                    # Create ConfigValue
                    config_key = f"{service_name}.{full_key}"
                    
                    # Check if value should be encrypted
                    schema = self.config_schemas.get(config_key)
                    encrypted = schema.sensitive if schema else self.is_sensitive_key(full_key)
                    
                    # Encrypt if needed and not already encrypted
                    if encrypted and isinstance(value, str) and not self.secret_manager.is_encrypted(value):
                        value = self.secret_manager.encrypt(value)
                    
                    config_values[full_key] = ConfigValue(
                        key=full_key,
                        value=value,
                        data_type=type(value).__name__,
                        encrypted=encrypted,
                        source="file",
                        description=schema.description if schema else ""
                    )
        
        process_nested_config(config_data)
        return config_values
    
    async def load_environment_variables(self, service_name: str) -> Dict[str, ConfigValue]:
        """Load configuration from environment variables"""
        config_values = {}
        prefix = f"ACTIVELOG_{service_name.upper().replace('-', '_')}_"
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace('_', '.')
                
                # Try to parse value type
                parsed_value = self.parse_env_value(value)
                
                config_values[config_key] = ConfigValue(
                    key=config_key,
                    value=parsed_value,
                    data_type=type(parsed_value).__name__,
                    source="environment"
                )
        
        return config_values
    
    def parse_env_value(self, value: str) -> Any:
        """Parse environment variable value to appropriate type"""
        # Try boolean
        if value.lower() in ['true', 'false']:
            return value.lower() == 'true'
        
        # Try integer
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Try JSON
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Return as string
        return value
    
    async def load_global_config(self):
        """Load global configuration"""
        global_config_file = self.config_dir / "global.yaml"
        
        if global_config_file.exists():
            config_data = await self.load_config_file(global_config_file)
            if config_data:
                self.global_config = await self.process_config_data(config_data, "global")
    
    def is_sensitive_key(self, key: str) -> bool:
        """Check if a configuration key contains sensitive data"""
        sensitive_patterns = [
            '*password*', '*secret*', '*key*', '*token*',
            '*credential*', '*auth*', '*api_key*', '*private*'
        ]
        
        key_lower = key.lower()
        for pattern in sensitive_patterns:
            if fnmatch.fnmatch(key_lower, pattern):
                return True
        
        return False
    
    def calculate_config_hash(self, config_values: Dict[str, ConfigValue]) -> str:
        """Calculate hash of configuration for change detection"""
        config_data = {}
        for key, config_value in config_values.items():
            # Don't include encrypted values in hash calculation
            if not config_value.encrypted:
                config_data[key] = config_value.value
        
        config_str = json.dumps(config_data, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    async def get_service_config(self, service_name: str, 
                                decrypt_secrets: bool = True) -> Dict[str, Any]:
        """Get configuration for a service"""
        if service_name not in self.service_configs:
            await self.load_service_config(service_name)
        
        service_config = self.service_configs.get(service_name)
        if not service_config:
            return {}
        
        config_dict = {}
        
        # Build nested configuration dictionary
        for key, config_value in service_config.config_values.items():
            value = config_value.value
            
            # Decrypt if needed
            if config_value.encrypted and decrypt_secrets:
                try:
                    value = self.secret_manager.decrypt(value)
                except Exception as e:
                    logging.error(f"Failed to decrypt config value {key}: {e}")
                    continue
            
            # Build nested structure
            keys = key.split('.')
            current_dict = config_dict
            
            for i, k in enumerate(keys[:-1]):
                if k not in current_dict:
                    current_dict[k] = {}
                current_dict = current_dict[k]
            
            current_dict[keys[-1]] = value
        
        # Add global configuration
        for key, config_value in self.global_config.items():
            if key not in config_dict:
                value = config_value.value
                if config_value.encrypted and decrypt_secrets:
                    try:
                        value = self.secret_manager.decrypt(value)
                    except Exception:
                        continue
                
                keys = key.split('.')
                current_dict = config_dict
                
                for i, k in enumerate(keys[:-1]):
                    if k not in current_dict:
                        current_dict[k] = {}
                    current_dict = current_dict[k]
                
                current_dict[keys[-1]] = value
        
        return config_dict
    
    async def set_config_value(self, service_name: str, key: str, value: Any,
                              encrypt: bool = False) -> bool:
        """Set a configuration value"""
        try:
            # Validate value if schema exists
            schema_key = f"{service_name}.{key}"
            schema = self.config_schemas.get(schema_key)
            
            if schema:
                validation_errors = self.validator.validate_value(value, schema.validation_rules)
                if validation_errors:
                    logging.error(f"Validation failed for {schema_key}: {validation_errors}")
                    return False
            
            # Encrypt if needed
            if encrypt and isinstance(value, str):
                value = self.secret_manager.encrypt(value)
            
            # Create or update service config
            if service_name not in self.service_configs:
                self.service_configs[service_name] = ServiceConfig(
                    service_name=service_name,
                    environment=self.current_environment
                )
            
            service_config = self.service_configs[service_name]
            
            # Update value
            service_config.config_values[key] = ConfigValue(
                key=key,
                value=value,
                data_type=type(value).__name__,
                encrypted=encrypt,
                source="api"
            )
            
            # Update metadata
            service_config.last_updated = datetime.now()
            service_config.version += 1
            service_config.config_hash = self.calculate_config_hash(service_config.config_values)
            
            # Persist configuration
            await self.persist_service_config(service_name)
            
            # Notify watchers
            await self.notify_watchers(service_name)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to set config value {service_name}.{key}: {e}")
            return False
    
    async def persist_service_config(self, service_name: str):
        """Persist service configuration to file"""
        if service_name not in self.service_configs:
            return
        
        service_config = self.service_configs[service_name]
        config_file = self.config_dir / "services" / f"{service_name}.yaml"
        config_file.parent.mkdir(exist_ok=True)
        
        # Build configuration data
        config_data = {}
        for key, config_value in service_config.config_values.items():
            if config_value.source != "environment":  # Don't persist env vars
                keys = key.split('.')
                current_dict = config_data
                
                for i, k in enumerate(keys[:-1]):
                    if k not in current_dict:
                        current_dict[k] = {}
                    current_dict = current_dict[k]
                
                current_dict[keys[-1]] = config_value.value
        
        # Write configuration file
        try:
            async with aiofiles.open(config_file, 'w') as f:
                await f.write(yaml.dump(config_data, default_flow_style=False))
        except Exception as e:
            logging.error(f"Failed to persist config for {service_name}: {e}")
    
    async def watch_config(self, service_name: str, callback: Callable[[Dict[str, Any]], None]) -> str:
        """Watch for configuration changes"""
        watcher_id = f"{service_name}_{int(time.time())}_{id(callback)}"
        
        watcher = ConfigWatcher(service_name, callback)
        
        if service_name not in self.watchers:
            self.watchers[service_name] = []
        
        self.watchers[service_name].append(watcher)
        
        # Add to service config
        if service_name in self.service_configs:
            self.service_configs[service_name].watchers.add(watcher_id)
        
        return watcher_id
    
    async def unwatch_config(self, service_name: str, watcher_id: str):
        """Stop watching configuration changes"""
        if service_name in self.watchers:
            self.watchers[service_name] = [
                w for w in self.watchers[service_name] 
                if id(w.callback) != int(watcher_id.split('_')[-1])
            ]
        
        if service_name in self.service_configs:
            self.service_configs[service_name].watchers.discard(watcher_id)
    
    async def notify_watchers(self, service_name: str):
        """Notify configuration watchers"""
        if service_name not in self.watchers:
            return
        
        config_data = await self.get_service_config(service_name)
        config_hash = self.service_configs[service_name].config_hash
        
        for watcher in self.watchers[service_name]:
            await watcher.notify(config_data, config_hash)
    
    async def reload_service_config(self, service_name: str) -> bool:
        """Reload configuration for a service"""
        try:
            old_hash = ""
            if service_name in self.service_configs:
                old_hash = self.service_configs[service_name].config_hash
            
            await self.load_service_config(service_name)
            
            new_hash = self.service_configs[service_name].config_hash
            
            if old_hash != new_hash:
                await self.notify_watchers(service_name)
                logging.info(f"Reloaded configuration for {service_name}")
                return True
            
        except Exception as e:
            logging.error(f"Failed to reload config for {service_name}: {e}")
        
        return False
    
    async def setup_config_sources(self):
        """Setup external configuration sources"""
        # File watcher (already handled)
        self.config_sources[ConfigSource.FILE] = True
        
        # Environment variables (already handled)
        self.config_sources[ConfigSource.ENVIRONMENT] = True
        
        # TODO: Add support for other sources like Consul, etcd, Vault
    
    async def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration management summary"""
        total_configs = sum(len(sc.config_values) for sc in self.service_configs.values())
        encrypted_configs = sum(
            sum(1 for cv in sc.config_values.values() if cv.encrypted)
            for sc in self.service_configs.values()
        )
        
        return {
            "environment": self.current_environment,
            "services_managed": len(self.service_configs),
            "total_config_values": total_configs,
            "encrypted_values": encrypted_configs,
            "active_watchers": sum(len(watchers) for watchers in self.watchers.values()),
            "config_sources": list(self.config_sources.keys()),
            "schemas_defined": len(self.config_schemas),
            "last_reload": max(
                (sc.last_updated for sc in self.service_configs.values()),
                default=datetime.now()
            ).isoformat()
        }
    
    async def export_configs(self, service_name: Optional[str] = None, 
                           include_secrets: bool = False) -> Dict[str, Any]:
        """Export configurations"""
        if service_name:
            if service_name not in self.service_configs:
                return {}
            
            return {
                service_name: await self.get_service_config(service_name, decrypt_secrets=include_secrets)
            }
        else:
            configs = {}
            for svc_name in self.service_configs.keys():
                configs[svc_name] = await self.get_service_config(svc_name, decrypt_secrets=include_secrets)
            
            return configs
    
    # Background tasks
    async def config_reload_task(self):
        """Background task to reload configurations periodically"""
        while self.running:
            try:
                await asyncio.sleep(self.reload_interval)
                
                # Check for file changes and reload if needed
                for service_name in self.service_configs.keys():
                    await self.reload_service_config(service_name)
                
            except Exception as e:
                logging.error(f"Config reload task error: {e}")
    
    async def config_sync_task(self):
        """Background task to sync with external sources"""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                # TODO: Sync with external configuration sources
                # like Consul, etcd, Vault, etc.
                
            except Exception as e:
                logging.error(f"Config sync task error: {e}")
    
    def stop(self):
        """Stop the configuration manager"""
        self.running = False

# Example usage and integration
async def main():
    discovery = ServiceDiscovery()
    config_manager = ConfigurationManager(discovery)
    
    await config_manager.initialize()
    
    # Example: Get configuration for a service
    user_service_config = await config_manager.get_service_config("user-service")
    print(f"User service config: {json.dumps(user_service_config, indent=2)}")
    
    # Example: Set a configuration value
    await config_manager.set_config_value("user-service", "database.host", "localhost")
    await config_manager.set_config_value("user-service", "api.secret_key", "my-secret", encrypt=True)
    
    # Example: Watch for configuration changes
    async def on_config_change(config_data):
        print(f"Configuration changed: {list(config_data.keys())}")
    
    watcher_id = await config_manager.watch_config("user-service", on_config_change)
    
    # Example: Get configuration summary
    summary = await config_manager.get_config_summary()
    print(f"Config summary: {json.dumps(summary, indent=2, default=str)}")
    
    # Wait for a while to see changes
    await asyncio.sleep(60)
    
    config_manager.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())