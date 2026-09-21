"""
Configuration management for file watcher
"""
import os
from typing import List, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class WatcherConfig:
    """File watcher configuration"""
    
    # Watching configuration
    watch_directories: List[str]
    watch_recursive: bool = True
    watch_hidden_files: bool = False
    
    # Pattern filtering
    include_patterns: List[str] = None
    exclude_patterns: List[str] = None
    ignore_file: str = ".activelog-ignore"
    
    # Batch processing
    batch_size: int = 100
    batch_timeout: float = 5.0
    debounce_delay: float = 1.0
    max_batch_wait: float = 30.0
    
    # Performance settings
    max_events_per_second: int = 1000
    memory_limit_mb: int = 512
    max_queue_size: int = 10000
    
    # External services
    sync_engine_url: str = "http://localhost:8004"
    sync_api_key: Optional[str] = None
    enable_sync_queue: bool = True
    
    # NATS configuration
    nats_url: str = "nats://localhost:4222"
    nats_subject: str = "file.events"
    nats_queue_group: str = "file-watchers"
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 4
    redis_password: Optional[str] = None
    
    # Database configuration
    database_url: str = "postgresql+asyncpg://watcher_user:watcher_password@localhost/activelog_watcher"
    
    # Monitoring
    enable_metrics: bool = True
    metrics_interval: float = 60.0
    health_check_interval: float = 30.0
    
    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_rotation_size: str = "10MB"
    log_retention_days: int = 7
    
    @classmethod
    def from_env(cls) -> 'WatcherConfig':
        """Load configuration from environment variables"""
        
        # Parse watch directories
        watch_dirs_str = os.getenv('WATCH_DIRECTORIES', '/tmp/activelog-test')
        watch_directories = [d.strip() for d in watch_dirs_str.split(',') if d.strip()]
        
        # Parse include/exclude patterns
        include_patterns = None
        include_str = os.getenv('INCLUDE_PATTERNS')
        if include_str:
            include_patterns = [p.strip() for p in include_str.split(',') if p.strip()]
        
        exclude_patterns = None
        exclude_str = os.getenv('EXCLUDE_PATTERNS')
        if exclude_str:
            exclude_patterns = [p.strip() for p in exclude_str.split(',') if p.strip()]
        
        return cls(
            # Watching configuration
            watch_directories=watch_directories,
            watch_recursive=os.getenv('WATCH_RECURSIVE', 'true').lower() == 'true',
            watch_hidden_files=os.getenv('WATCH_HIDDEN_FILES', 'false').lower() == 'true',
            
            # Pattern filtering
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            ignore_file=os.getenv('IGNORE_FILE', '.activelog-ignore'),
            
            # Batch processing
            batch_size=int(os.getenv('BATCH_SIZE', '100')),
            batch_timeout=float(os.getenv('BATCH_TIMEOUT', '5')),
            debounce_delay=float(os.getenv('DEBOUNCE_DELAY', '1')),
            max_batch_wait=float(os.getenv('MAX_BATCH_WAIT', '30')),
            
            # Performance settings
            max_events_per_second=int(os.getenv('MAX_EVENTS_PER_SECOND', '1000')),
            memory_limit_mb=int(os.getenv('MEMORY_LIMIT_MB', '512')),
            max_queue_size=int(os.getenv('MAX_QUEUE_SIZE', '10000')),
            
            # External services
            sync_engine_url=os.getenv('SYNC_ENGINE_URL', 'http://localhost:8004'),
            sync_api_key=os.getenv('SYNC_API_KEY'),
            enable_sync_queue=os.getenv('ENABLE_SYNC_QUEUE', 'true').lower() == 'true',
            
            # NATS configuration
            nats_url=os.getenv('NATS_URL', 'nats://localhost:4222'),
            nats_subject=os.getenv('NATS_SUBJECT', 'file.events'),
            nats_queue_group=os.getenv('NATS_QUEUE_GROUP', 'file-watchers'),
            
            # Redis configuration
            redis_host=os.getenv('REDIS_HOST', 'localhost'),
            redis_port=int(os.getenv('REDIS_PORT', '6379')),
            redis_db=int(os.getenv('REDIS_DB', '4')),
            redis_password=os.getenv('REDIS_PASSWORD'),
            
            # Database configuration
            database_url=os.getenv('DATABASE_URL', 
                'postgresql+asyncpg://watcher_user:watcher_password@localhost/activelog_watcher'),
            
            # Monitoring
            enable_metrics=os.getenv('ENABLE_METRICS', 'true').lower() == 'true',
            metrics_interval=float(os.getenv('METRICS_INTERVAL', '60')),
            health_check_interval=float(os.getenv('HEALTH_CHECK_INTERVAL', '30')),
            
            # Logging
            log_level=os.getenv('LOG_LEVEL', 'INFO'),
            log_file=os.getenv('LOG_FILE'),
            log_rotation_size=os.getenv('LOG_ROTATION_SIZE', '10MB'),
            log_retention_days=int(os.getenv('LOG_RETENTION_DAYS', '7'))
        )
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        # Validate watch directories
        if not self.watch_directories:
            errors.append("At least one watch directory must be specified")
        else:
            for directory in self.watch_directories:
                if not os.path.exists(directory):
                    errors.append(f"Watch directory does not exist: {directory}")
                elif not os.path.isdir(directory):
                    errors.append(f"Watch path is not a directory: {directory}")
        
        # Validate batch settings
        if self.batch_size <= 0:
            errors.append("Batch size must be positive")
        
        if self.batch_timeout <= 0:
            errors.append("Batch timeout must be positive")
        
        if self.debounce_delay < 0:
            errors.append("Debounce delay cannot be negative")
        
        # Validate performance settings
        if self.max_events_per_second <= 0:
            errors.append("Max events per second must be positive")
        
        if self.memory_limit_mb <= 0:
            errors.append("Memory limit must be positive")
        
        if self.max_queue_size <= 0:
            errors.append("Max queue size must be positive")
        
        # Validate intervals
        if self.metrics_interval <= 0:
            errors.append("Metrics interval must be positive")
        
        if self.health_check_interval <= 0:
            errors.append("Health check interval must be positive")
        
        return errors
    
    def create_directories(self) -> List[str]:
        """Create missing directories and return list of created directories"""
        created = []
        
        for directory in self.watch_directories:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory, exist_ok=True)
                    created.append(directory)
                except OSError as e:
                    # Log error but don't fail
                    pass
        
        return created
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        else:
            return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    def get_nats_config(self) -> dict:
        """Get NATS connection configuration"""
        return {
            "servers": [self.nats_url],
            "name": "file-watcher",
            "verbose": False,
            "pedantic": False,
            "max_reconnect_attempts": -1,
            "reconnect_time_wait": 2,
        }
    
    def __str__(self) -> str:
        """String representation of config (hiding sensitive data)"""
        safe_config = {
            'watch_directories': self.watch_directories,
            'watch_recursive': self.watch_recursive,
            'batch_size': self.batch_size,
            'batch_timeout': self.batch_timeout,
            'debounce_delay': self.debounce_delay,
            'sync_engine_url': self.sync_engine_url,
            'nats_url': self.nats_url,
            'nats_subject': self.nats_subject,
            'enable_metrics': self.enable_metrics,
            'log_level': self.log_level
        }
        return f"WatcherConfig({safe_config})"