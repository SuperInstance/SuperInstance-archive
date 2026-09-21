"""Logging utilities"""

import logging
import sys
from pathlib import Path

def setup_logging(level=logging.INFO):
    """Setup logging configuration"""
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(logs_dir / "smart_folders.log")
        ]
    )
    
    # Set specific logger levels
    logging.getLogger("databases").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)