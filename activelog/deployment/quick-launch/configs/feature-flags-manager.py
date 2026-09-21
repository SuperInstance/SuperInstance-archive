#!/usr/bin/env python3

"""
Feature Flags Manager for ActiveLog
Manages feature flags for different environments with real-time updates
"""

import json
import redis
import argparse
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class FeatureFlagType(Enum):
    BOOLEAN = "boolean"
    STRING = "string"
    NUMBER = "number"
    JSON = "json"
    PERCENTAGE = "percentage"

@dataclass
class FeatureFlag:
    key: str
    name: str
    description: str
    type: FeatureFlagType
    enabled: bool
    value: Any = None
    percentage: int = 0  # For percentage rollout
    environments: List[str] = None
    user_segments: List[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    created_at: str = None
    updated_at: str = None

class FeatureFlagsManager:
    def __init__(self, environment: str = "beta", redis_url: str = "redis://localhost:6379/1"):
        self.environment = environment
        self.redis_client = redis.from_url(redis_url)
        self.logger = logging.getLogger(__name__)
        self.cache_prefix = f"feature_flags:{environment}"
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def load_config(self, config_file: str) -> Dict[str, FeatureFlag]:
        """Load feature flags from configuration file"""
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            flags = {}
            for flag_data in config_data.get('flags', []):
                flag = FeatureFlag(
                    key=flag_data['key'],
                    name=flag_data['name'],
                    description=flag_data['description'],
                    type=FeatureFlagType(flag_data['type']),
                    enabled=flag_data['enabled'],
                    value=flag_data.get('value'),
                    percentage=flag_data.get('percentage', 0),
                    environments=flag_data.get('environments', []),
                    user_segments=flag_data.get('user_segments', []),
                    start_date=flag_data.get('start_date'),
                    end_date=flag_data.get('end_date'),
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat()
                )
                flags[flag.key] = flag
            
            self.logger.info(f"Loaded {len(flags)} feature flags from {config_file}")
            return flags
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            return {}

    def deploy_flags(self, flags: Dict[str, FeatureFlag]):
        """Deploy feature flags to Redis"""
        try:
            pipeline = self.redis_client.pipeline()
            
            for flag_key, flag in flags.items():
                # Only deploy flags for current environment
                if flag.environments and self.environment not in flag.environments:
                    continue
                
                cache_key = f"{self.cache_prefix}:{flag_key}"
                flag_data = asdict(flag)
                
                # Convert enum to string
                flag_data['type'] = flag.type.value
                
                pipeline.set(cache_key, json.dumps(flag_data))
                pipeline.expire(cache_key, 86400)  # 24 hour expiry
            
            # Store metadata
            metadata = {
                "environment": self.environment,
                "deployed_at": datetime.now().isoformat(),
                "flags_count": len(flags)
            }
            pipeline.set(f"{self.cache_prefix}:metadata", json.dumps(metadata))
            
            pipeline.execute()
            self.logger.info(f"Deployed {len(flags)} feature flags to Redis")
            
        except Exception as e:
            self.logger.error(f"Failed to deploy flags: {e}")
            raise

    def get_flag(self, flag_key: str, user_id: str = None) -> Dict[str, Any]:
        """Get feature flag value for specific user"""
        try:
            cache_key = f"{self.cache_prefix}:{flag_key}"
            flag_data = self.redis_client.get(cache_key)
            
            if not flag_data:
                return {"enabled": False, "value": None}
            
            flag = json.loads(flag_data)
            
            # Check if flag is enabled
            if not flag['enabled']:
                return {"enabled": False, "value": flag.get('value')}
            
            # Check date constraints
            now = datetime.now()
            if flag.get('start_date') and now < datetime.fromisoformat(flag['start_date']):
                return {"enabled": False, "value": flag.get('value')}
            
            if flag.get('end_date') and now > datetime.fromisoformat(flag['end_date']):
                return {"enabled": False, "value": flag.get('value')}
            
            # Handle percentage rollout
            if flag.get('percentage', 0) > 0 and user_id:
                user_hash = hash(f"{flag_key}:{user_id}") % 100
                if user_hash >= flag['percentage']:
                    return {"enabled": False, "value": flag.get('value')}
            
            return {
                "enabled": True,
                "value": flag.get('value'),
                "type": flag['type'],
                "percentage": flag.get('percentage', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get flag {flag_key}: {e}")
            return {"enabled": False, "value": None}

    def update_flag(self, flag_key: str, updates: Dict[str, Any]):
        """Update specific feature flag"""
        try:
            cache_key = f"{self.cache_prefix}:{flag_key}"
            flag_data = self.redis_client.get(cache_key)
            
            if not flag_data:
                self.logger.error(f"Flag {flag_key} not found")
                return False
            
            flag = json.loads(flag_data)
            flag.update(updates)
            flag['updated_at'] = datetime.now().isoformat()
            
            self.redis_client.set(cache_key, json.dumps(flag))
            self.logger.info(f"Updated flag {flag_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update flag {flag_key}: {e}")
            return False

    def list_flags(self) -> List[Dict[str, Any]]:
        """List all feature flags for current environment"""
        try:
            pattern = f"{self.cache_prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            flags = []
            for key in keys:
                if key.decode().endswith(':metadata'):
                    continue
                
                flag_data = self.redis_client.get(key)
                if flag_data:
                    flag = json.loads(flag_data)
                    flags.append(flag)
            
            return flags
            
        except Exception as e:
            self.logger.error(f"Failed to list flags: {e}")
            return []

    def delete_flag(self, flag_key: str) -> bool:
        """Delete feature flag"""
        try:
            cache_key = f"{self.cache_prefix}:{flag_key}"
            deleted = self.redis_client.delete(cache_key)
            
            if deleted:
                self.logger.info(f"Deleted flag {flag_key}")
                return True
            else:
                self.logger.warning(f"Flag {flag_key} not found")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to delete flag {flag_key}: {e}")
            return False

    def health_check(self) -> Dict[str, Any]:
        """Check system health"""
        try:
            # Test Redis connection
            self.redis_client.ping()
            
            # Get metadata
            metadata_key = f"{self.cache_prefix}:metadata"
            metadata = self.redis_client.get(metadata_key)
            
            if metadata:
                metadata = json.loads(metadata)
            else:
                metadata = {"environment": self.environment}
            
            # Count active flags
            active_flags = len(self.list_flags())
            
            return {
                "status": "healthy",
                "environment": self.environment,
                "active_flags": active_flags,
                "redis_connected": True,
                **metadata
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "environment": self.environment
            }

def main():
    parser = argparse.ArgumentParser(description='Feature Flags Manager')
    parser.add_argument('--environment', default='beta', help='Environment (beta/prod)')
    parser.add_argument('--redis-url', default='redis://localhost:6379/1', help='Redis URL')
    parser.add_argument('--config', help='Config file path')
    parser.add_argument('--action', choices=['deploy', 'list', 'get', 'update', 'delete', 'health'], 
                       default='deploy', help='Action to perform')
    parser.add_argument('--flag-key', help='Flag key for get/update/delete operations')
    parser.add_argument('--updates', help='JSON string of updates for update operation')
    parser.add_argument('--user-id', help='User ID for flag evaluation')
    
    args = parser.parse_args()
    
    manager = FeatureFlagsManager(args.environment, args.redis_url)
    
    if args.action == 'deploy':
        if not args.config:
            print("Config file required for deploy action")
            sys.exit(1)
        
        flags = manager.load_config(args.config)
        manager.deploy_flags(flags)
        print(f"Deployed {len(flags)} flags to {args.environment}")
    
    elif args.action == 'list':
        flags = manager.list_flags()
        print(json.dumps(flags, indent=2))
    
    elif args.action == 'get':
        if not args.flag_key:
            print("Flag key required for get action")
            sys.exit(1)
        
        result = manager.get_flag(args.flag_key, args.user_id)
        print(json.dumps(result, indent=2))
    
    elif args.action == 'update':
        if not args.flag_key or not args.updates:
            print("Flag key and updates required for update action")
            sys.exit(1)
        
        updates = json.loads(args.updates)
        success = manager.update_flag(args.flag_key, updates)
        print("Success" if success else "Failed")
    
    elif args.action == 'delete':
        if not args.flag_key:
            print("Flag key required for delete action")
            sys.exit(1)
        
        success = manager.delete_flag(args.flag_key)
        print("Deleted" if success else "Failed")
    
    elif args.action == 'health':
        health = manager.health_check()
        print(json.dumps(health, indent=2))

if __name__ == '__main__':
    main()