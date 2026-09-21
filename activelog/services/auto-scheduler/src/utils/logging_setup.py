import logging
import logging.handlers
from pathlib import Path
from typing import Dict, Any

def setup_logging(config: Dict[str, Any]):
    """Setup logging configuration for the auto-scheduler service"""
    
    # Get logging configuration
    log_config = config.get('logging', {})
    log_level = log_config.get('level', 'INFO')
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', '/home/activeloguser/activelog/services/auto-scheduler/logs/auto-scheduler.log')
    max_bytes = log_config.get('max_bytes', 10485760)  # 10MB
    backup_count = log_config.get('backup_count', 5)
    
    # Create logs directory
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Set up specific logger levels for different components
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    # Auto-scheduler specific loggers
    logging.getLogger('auto_scheduler').setLevel(getattr(logging, log_level.upper()))
    logging.getLogger('scheduler').setLevel(getattr(logging, log_level.upper()))
    logging.getLogger('bot_manager').setLevel(getattr(logging, log_level.upper()))
    logging.getLogger('backup_manager').setLevel(getattr(logging, log_level.upper()))
    logging.getLogger('progress_tracker').setLevel(getattr(logging, log_level.upper()))
    
    logging.info(f"Logging setup completed - Level: {log_level}, File: {log_file}")