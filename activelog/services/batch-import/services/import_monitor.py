"""
Import Monitor Service - Watches import folder for new files
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from dataclasses import dataclass, field
from datetime import datetime

from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class FileEvent:
    """Represents a file system event"""
    path: Path
    event_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    size: Optional[int] = None
    is_stable: bool = False

class ImportFileHandler(FileSystemEventHandler):
    """Handles file system events in the import directory"""
    
    def __init__(self, monitor):
        self.monitor = monitor
        super().__init__()
    
    def on_created(self, event: FileSystemEvent):
        """Handle file creation events"""
        if not event.is_directory:
            self.monitor.add_file_event(event.src_path, "created")
    
    def on_moved(self, event: FileSystemEvent):
        """Handle file move events"""
        if not event.is_directory:
            self.monitor.add_file_event(event.dest_path, "moved")
    
    def on_modified(self, event: FileSystemEvent):
        """Handle file modification events"""
        if not event.is_directory:
            self.monitor.add_file_event(event.src_path, "modified")

class ImportMonitor:
    """Monitors import directory for new files and triggers batch processing"""
    
    def __init__(self, import_path: str, batch_processor, check_interval: int = 30):
        self.import_path = Path(import_path)
        self.batch_processor = batch_processor
        self.check_interval = check_interval
        
        # File tracking
        self.pending_files: Dict[str, FileEvent] = {}
        self.stable_files: Set[str] = set()
        self.processed_files: Set[str] = set()
        
        # Monitoring state
        self.is_monitoring = False
        self.observer: Optional[Observer] = None
        self.monitor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            "files_detected": 0,
            "files_processed": 0,
            "files_failed": 0,
            "batches_created": 0,
            "start_time": None,
            "last_scan": None
        }
        
        logger.info(f"Import monitor initialized for path: {self.import_path}")
    
    async def start_monitoring(self):
        """Start monitoring the import directory"""
        if self.is_monitoring:
            logger.warning("Monitor is already running")
            return
        
        try:
            # Ensure import directory exists
            self.import_path.mkdir(parents=True, exist_ok=True)
            
            # Start file system watcher
            self.observer = Observer()
            handler = ImportFileHandler(self)
            self.observer.schedule(handler, str(self.import_path), recursive=True)
            self.observer.start()
            
            # Start periodic processing
            self.monitor_task = asyncio.create_task(self._monitor_loop())
            
            self.is_monitoring = True
            self.stats["start_time"] = datetime.now()
            
            logger.info(f"Started monitoring {self.import_path}")
            
            # Perform initial scan
            await self._scan_existing_files()
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}")
            await self.stop_monitoring()
            raise
    
    async def stop_monitoring(self):
        """Stop monitoring the import directory"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        
        # Stop file system watcher
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        # Stop monitoring task
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.monitor_task = None
        
        logger.info("Stopped monitoring import directory")
    
    def add_file_event(self, file_path: str, event_type: str):
        """Add a file event for processing"""
        try:
            path = Path(file_path)
            
            # Skip hidden files and directories
            if path.name.startswith('.'):
                return
            
            # Skip files that are not in supported formats
            if path.suffix.lower() not in settings.all_supported_formats:
                logger.debug(f"Skipping unsupported file format: {path}")
                return
            
            # Check if file exists and get size
            if not path.exists():
                return
            
            try:
                file_size = path.stat().st_size
            except OSError:
                # File might be in use or deleted
                return
            
            # Create or update file event
            file_key = str(path)
            if file_key in self.pending_files:
                # Update existing event
                self.pending_files[file_key].event_type = event_type
                self.pending_files[file_key].timestamp = datetime.now()
                self.pending_files[file_key].size = file_size
                self.pending_files[file_key].is_stable = False
            else:
                # Create new event
                self.pending_files[file_key] = FileEvent(
                    path=path,
                    event_type=event_type,
                    size=file_size
                )
                self.stats["files_detected"] += 1
            
            logger.debug(f"Added file event: {event_type} - {path}")
            
        except Exception as e:
            logger.error(f"Error adding file event for {file_path}: {e}")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.is_monitoring:
            try:
                await asyncio.sleep(self.check_interval)
                
                if not self.is_monitoring:
                    break
                
                await self._process_pending_files()
                self.stats["last_scan"] = datetime.now()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
                await asyncio.sleep(5)  # Brief pause before retrying
    
    async def _scan_existing_files(self):
        """Scan for existing files in the import directory"""
        try:
            logger.info("Scanning for existing files in import directory")
            
            existing_files = []
            for file_path in self.import_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    if file_path.suffix.lower() in settings.all_supported_formats:
                        existing_files.append(file_path)
            
            logger.info(f"Found {len(existing_files)} existing files")
            
            # Add existing files as events
            for file_path in existing_files:
                self.add_file_event(str(file_path), "existing")
            
            # Process them immediately
            await self._process_pending_files()
            
        except Exception as e:
            logger.error(f"Error scanning existing files: {e}")
    
    async def _process_pending_files(self):
        """Process pending files and create batches"""
        if not self.pending_files:
            return
        
        try:
            # Check which files are stable (not being written to)
            stable_files = await self._check_file_stability()
            
            if not stable_files:
                logger.debug("No stable files ready for processing")
                return
            
            # Create batches of stable files
            batches = self._create_batches(stable_files)
            
            for batch in batches:
                try:
                    # Submit batch for processing
                    await self.batch_processor.process_batch(batch)
                    self.stats["batches_created"] += 1
                    
                    # Mark files as processed
                    for file_path in batch:
                        self.processed_files.add(file_path)
                        if file_path in self.pending_files:
                            del self.pending_files[file_path]
                    
                    logger.info(f"Submitted batch of {len(batch)} files for processing")
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    # Files will remain in pending_files for retry
            
        except Exception as e:
            logger.error(f"Error processing pending files: {e}")
    
    async def _check_file_stability(self) -> List[str]:
        """Check which files are stable (not being written to)"""
        stable_files = []
        current_time = datetime.now()
        
        for file_path, file_event in list(self.pending_files.items()):
            try:
                path = Path(file_path)
                
                # Check if file still exists
                if not path.exists():
                    del self.pending_files[file_path]
                    continue
                
                # Check if file size has changed
                try:
                    current_size = path.stat().st_size
                    
                    # Skip empty files
                    if current_size == 0:
                        continue
                    
                    # Skip files that are too large
                    if current_size > settings.MAX_FILE_SIZE:
                        logger.warning(f"File too large, skipping: {path} ({current_size} bytes)")
                        del self.pending_files[file_path]
                        continue
                    
                    # Check if size has changed since last check
                    if file_event.size is None or current_size != file_event.size:
                        file_event.size = current_size
                        file_event.timestamp = current_time
                        file_event.is_stable = False
                        continue
                    
                    # Check if file has been stable for enough time
                    time_since_change = (current_time - file_event.timestamp).total_seconds()
                    if time_since_change >= 5:  # 5 seconds of stability
                        file_event.is_stable = True
                        stable_files.append(file_path)
                    
                except OSError as e:
                    # File might be locked or in use
                    logger.debug(f"Cannot access file {path}: {e}")
                    continue
                
            except Exception as e:
                logger.error(f"Error checking file stability for {file_path}: {e}")
        
        return stable_files
    
    def _create_batches(self, stable_files: List[str]) -> List[List[str]]:
        """Create batches from stable files"""
        batches = []
        current_batch = []
        
        for file_path in stable_files:
            current_batch.append(file_path)
            
            if len(current_batch) >= settings.BATCH_SIZE:
                batches.append(current_batch)
                current_batch = []
        
        # Add remaining files as a batch
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def is_running(self) -> bool:
        """Check if monitor is running"""
        return self.is_monitoring
    
    def get_stats(self) -> Dict:
        """Get monitoring statistics"""
        stats = self.stats.copy()
        stats.update({
            "pending_files": len(self.pending_files),
            "stable_files": len(self.stable_files),
            "processed_files": len(self.processed_files),
            "is_monitoring": self.is_monitoring,
            "import_path": str(self.import_path)
        })
        
        if stats["start_time"]:
            uptime = (datetime.now() - stats["start_time"]).total_seconds()
            stats["uptime_seconds"] = uptime
        
        return stats
    
    def get_pending_files(self) -> List[Dict]:
        """Get list of pending files with details"""
        pending = []
        for file_path, file_event in self.pending_files.items():
            pending.append({
                "path": file_path,
                "event_type": file_event.event_type,
                "timestamp": file_event.timestamp.isoformat(),
                "size": file_event.size,
                "is_stable": file_event.is_stable
            })
        return pending