"""
Core file watcher implementation using watchdog
"""
import os
import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
from dataclasses import dataclass, field
import time

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.events import (
    FileCreatedEvent, FileDeletedEvent, FileModifiedEvent, 
    DirCreatedEvent, DirDeletedEvent, DirModifiedEvent,
    FileMovedEvent, DirMovedEvent
)

from ignore_patterns import SmartIgnoreManager
from models import FileEventType, EventStatus
from config import WatcherConfig

logger = logging.getLogger(__name__)

@dataclass
class PendingEvent:
    """Represents an event waiting for debouncing"""
    file_path: str
    event_type: str
    first_seen: datetime
    last_seen: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    count: int = 1

    def should_process(self, debounce_seconds: float) -> bool:
        """Check if event should be processed based on debounce timer"""
        return (datetime.utcnow() - self.last_seen).total_seconds() >= debounce_seconds

    def update(self, metadata: Optional[Dict[str, Any]] = None):
        """Update the event with new occurrence"""
        self.last_seen = datetime.utcnow()
        self.count += 1
        if metadata:
            self.metadata.update(metadata)

class FileWatcherHandler(FileSystemEventHandler):
    """Handles file system events from watchdog"""
    
    def __init__(self, watcher: 'FileWatcher'):
        super().__init__()
        self.watcher = watcher
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def on_any_event(self, event: FileSystemEvent):
        """Handle any file system event"""
        try:
            # Skip directory events for now (we track files)
            if event.is_directory and not isinstance(event, (DirCreatedEvent, DirDeletedEvent)):
                return
            
            # Map watchdog events to our event types
            event_type = self._map_event_type(event)
            if not event_type:
                return
            
            # Get file path
            file_path = event.src_path
            old_path = getattr(event, 'dest_path', None)
            
            # Check if we should ignore this file
            if self.watcher.ignore_manager.should_ignore_path(file_path)['ignore']:
                self.logger.debug(f"Ignoring file: {file_path}")
                return
            
            # Create event metadata
            metadata = self._extract_metadata(event, file_path)
            
            # Queue the event for processing
            asyncio.create_task(
                self.watcher.queue_event(event_type, file_path, old_path, metadata)
            )
            
        except Exception as e:
            self.logger.error(f"Error handling file event: {e}", exc_info=True)
    
    def _map_event_type(self, event: FileSystemEvent) -> Optional[str]:
        """Map watchdog event to our event type"""
        if isinstance(event, (FileCreatedEvent, DirCreatedEvent)):
            return FileEventType.CREATED
        elif isinstance(event, (FileDeletedEvent, DirDeletedEvent)):
            return FileEventType.DELETED
        elif isinstance(event, (FileModifiedEvent, DirModifiedEvent)):
            return FileEventType.MODIFIED
        elif isinstance(event, (FileMovedEvent, DirMovedEvent)):
            return FileEventType.MOVED
        else:
            return None
    
    def _extract_metadata(self, event: FileSystemEvent, file_path: str) -> Dict[str, Any]:
        """Extract metadata from file and event"""
        metadata = {
            'event_time': datetime.utcnow().isoformat(),
            'is_directory': event.is_directory
        }
        
        try:
            # Only get file stats for existing files
            if os.path.exists(file_path) and not event.is_directory:
                stat = os.stat(file_path)
                metadata.update({
                    'file_size': stat.st_size,
                    'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    'permissions': oct(stat.st_mode)[-3:],
                })
                
                # Calculate file hash for small files
                if stat.st_size < 10 * 1024 * 1024:  # 10MB limit
                    metadata['file_hash'] = self._calculate_file_hash(file_path)
        
        except (OSError, IOError) as e:
            self.logger.warning(f"Could not get metadata for {file_path}: {e}")
        
        return metadata
    
    def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA-256 hash of file"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            self.logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return None

class EventBatcher:
    """Batches events for efficient processing"""
    
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_events: List[Dict[str, Any]] = []
        self.last_batch_time = time.time()
        self.batch_callbacks: List[callable] = []
    
    def add_callback(self, callback: callable):
        """Add callback to be called when batch is ready"""
        self.batch_callbacks.append(callback)
    
    async def add_event(self, event_data: Dict[str, Any]):
        """Add event to batch"""
        self.pending_events.append(event_data)
        
        # Check if we should process the batch
        if self._should_process_batch():
            await self._process_batch()
    
    def _should_process_batch(self) -> bool:
        """Check if batch should be processed"""
        return (
            len(self.pending_events) >= self.batch_size or
            time.time() - self.last_batch_time >= self.batch_timeout
        )
    
    async def _process_batch(self):
        """Process current batch"""
        if not self.pending_events:
            return
        
        batch = self.pending_events.copy()
        self.pending_events.clear()
        self.last_batch_time = time.time()
        
        # Call all batch callbacks
        for callback in self.batch_callbacks:
            try:
                await callback(batch)
            except Exception as e:
                logger.error(f"Error in batch callback: {e}")
    
    async def flush(self):
        """Force process current batch"""
        if self.pending_events:
            await self._process_batch()

class FileWatcher:
    """Main file watcher class"""
    
    def __init__(self, config: WatcherConfig):
        self.config = config
        self.ignore_manager = SmartIgnoreManager()
        self.observer = Observer()
        self.handler = FileWatcherHandler(self)
        
        # Event processing
        self.pending_events: Dict[str, PendingEvent] = {}
        self.event_batcher = EventBatcher(
            batch_size=config.batch_size,
            batch_timeout=config.batch_timeout
        )
        
        # Statistics
        self.stats = {
            'events_processed': 0,
            'events_ignored': 0,
            'events_debounced': 0,
            'batches_processed': 0,
            'start_time': datetime.utcnow()
        }
        
        # Background tasks
        self._tasks: Set[asyncio.Task] = set()
        self._running = False
        
        logger.info(f"FileWatcher initialized with config: {config}")
    
    async def start(self):
        """Start the file watcher"""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Starting file watcher...")
        
        try:
            # Load ignore patterns for each watched directory
            for directory in self.config.watch_directories:
                if os.path.exists(directory):
                    self.ignore_manager.pattern_matcher.load_directory_ignore_files(directory)
                    self.logger.info(f"Loaded ignore patterns for {directory}")
            
            # Add global ignore patterns from config
            if self.config.exclude_patterns:
                self.ignore_manager.pattern_matcher.add_global_patterns(
                    self.config.exclude_patterns
                )
            
            # Set up event batcher
            self.event_batcher.add_callback(self._process_event_batch)
            
            # Start watching directories
            for directory in self.config.watch_directories:
                if os.path.exists(directory):
                    self.observer.schedule(
                        self.handler, 
                        directory, 
                        recursive=self.config.watch_recursive
                    )
                    self.logger.info(f"Watching directory: {directory}")
                else:
                    self.logger.warning(f"Directory does not exist: {directory}")
            
            # Start the observer
            self.observer.start()
            self._running = True
            
            # Start background tasks
            self._tasks.add(asyncio.create_task(self._debounce_processor()))
            self._tasks.add(asyncio.create_task(self._metrics_collector()))
            
            self.logger.info("File watcher started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start file watcher: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the file watcher"""
        self.logger.info("Stopping file watcher...")
        self._running = False
        
        # Stop observer
        self.observer.stop()
        self.observer.join()
        
        # Cancel background tasks
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Process any remaining events
        await self.event_batcher.flush()
        
        self.logger.info("File watcher stopped")
    
    async def queue_event(self, event_type: str, file_path: str, 
                         old_path: Optional[str] = None, 
                         metadata: Optional[Dict[str, Any]] = None):
        """Queue a file event for processing"""
        
        # Create event key for debouncing
        event_key = f"{file_path}:{event_type}"
        
        current_time = datetime.utcnow()
        
        if event_key in self.pending_events:
            # Update existing pending event
            self.pending_events[event_key].update(metadata)
            self.stats['events_debounced'] += 1
        else:
            # Create new pending event
            self.pending_events[event_key] = PendingEvent(
                file_path=file_path,
                event_type=event_type,
                first_seen=current_time,
                last_seen=current_time,
                metadata=metadata or {}
            )
        
        # Add old_path for move events
        if old_path:
            self.pending_events[event_key].metadata['old_path'] = old_path
    
    async def _debounce_processor(self):
        """Process debounced events"""
        while self._running:
            try:
                current_time = datetime.utcnow()
                ready_events = []
                
                # Find events ready for processing
                for event_key, pending_event in list(self.pending_events.items()):
                    if pending_event.should_process(self.config.debounce_delay):
                        ready_events.append(pending_event)
                        del self.pending_events[event_key]
                
                # Process ready events
                for event in ready_events:
                    await self._process_event(event)
                
                # Sleep before next check
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in debounce processor: {e}")
    
    async def _process_event(self, event: PendingEvent):
        """Process a single debounced event"""
        try:
            event_data = {
                'event_type': event.event_type,
                'file_path': event.file_path,
                'old_path': event.metadata.get('old_path'),
                'metadata': event.metadata,
                'detected_at': event.first_seen.isoformat(),
                'debounce_count': event.count
            }
            
            # Add to batch
            await self.event_batcher.add_event(event_data)
            self.stats['events_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing event {event.file_path}: {e}")
    
    async def _process_event_batch(self, events: List[Dict[str, Any]]):
        """Process a batch of events"""
        try:
            self.logger.info(f"Processing batch of {len(events)} events")
            
            # Here you would typically:
            # 1. Store events in database
            # 2. Send to sync engine via NATS
            # 3. Update metrics
            
            # For now, we'll just log and update stats
            self.stats['batches_processed'] += 1
            
            # TODO: Implement actual batch processing
            # - Store in database
            # - Queue for sync engine
            # - Update file checksums
            
        except Exception as e:
            logger.error(f"Error processing event batch: {e}")
    
    async def _metrics_collector(self):
        """Collect and report metrics"""
        while self._running:
            try:
                # Calculate uptime
                uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
                
                # Calculate rates
                events_per_second = self.stats['events_processed'] / max(uptime, 1)
                
                metrics = {
                    'uptime_seconds': uptime,
                    'events_processed': self.stats['events_processed'],
                    'events_ignored': self.stats['events_ignored'],
                    'events_debounced': self.stats['events_debounced'],
                    'batches_processed': self.stats['batches_processed'],
                    'events_per_second': events_per_second,
                    'pending_events': len(self.pending_events),
                    'watched_directories': len(self.config.watch_directories)
                }
                
                self.logger.debug(f"Metrics: {metrics}")
                
                # TODO: Store metrics in database or send to monitoring system
                
                await asyncio.sleep(self.config.metrics_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics"""
        uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'events_per_second': self.stats['events_processed'] / max(uptime, 1),
            'pending_events': len(self.pending_events),
            'watched_directories': len(self.config.watch_directories),
            'is_running': self._running
        }
    
    async def add_watch_directory(self, directory: str):
        """Add a new directory to watch"""
        if directory not in self.config.watch_directories:
            if os.path.exists(directory):
                self.config.watch_directories.append(directory)
                
                # Load ignore patterns
                self.ignore_manager.pattern_matcher.load_directory_ignore_files(directory)
                
                # Start watching if observer is running
                if self._running:
                    self.observer.schedule(
                        self.handler,
                        directory,
                        recursive=self.config.watch_recursive
                    )
                
                self.logger.info(f"Added watch directory: {directory}")
            else:
                raise ValueError(f"Directory does not exist: {directory}")
    
    async def remove_watch_directory(self, directory: str):
        """Remove a directory from watching"""
        if directory in self.config.watch_directories:
            self.config.watch_directories.remove(directory)
            
            # TODO: Remove observer watch (requires tracking watch handles)
            
            self.logger.info(f"Removed watch directory: {directory}")
    
    async def force_scan(self, directory: Optional[str] = None):
        """Force a full scan of directory"""
        directories = [directory] if directory else self.config.watch_directories
        
        for dir_path in directories:
            if os.path.exists(dir_path):
                self.logger.info(f"Starting forced scan of {dir_path}")
                
                # Walk directory and create events for all files
                for root, dirs, files in os.walk(dir_path):
                    for file_name in files:
                        file_path = os.path.join(root, file_name)
                        
                        # Check if file should be ignored
                        if not self.ignore_manager.should_ignore_path(file_path)['ignore']:
                            metadata = self.handler._extract_metadata(None, file_path)
                            await self.queue_event(
                                FileEventType.CREATED, 
                                file_path, 
                                metadata=metadata
                            )
                
                self.logger.info(f"Completed forced scan of {dir_path}")