"""
Batch import handler for efficiently processing large directory imports
"""
import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator
from pathlib import Path
import time

from ignore_patterns import SmartIgnoreManager
from models import FileEventType

logger = logging.getLogger(__name__)

class BatchImporter:
    """Handles efficient batch imports of large directories"""
    
    def __init__(self, ignore_manager: SmartIgnoreManager, batch_size: int = 1000):
        self.ignore_manager = ignore_manager
        self.batch_size = batch_size
        self.stats = {
            'files_scanned': 0,
            'files_ignored': 0,
            'files_processed': 0,
            'directories_scanned': 0,
            'total_size': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def scan_directory(self, directory: str, 
                           recursive: bool = True,
                           include_patterns: Optional[List[str]] = None,
                           max_file_size: Optional[int] = None) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Scan directory and yield batches of file events
        
        Args:
            directory: Directory to scan
            recursive: Whether to scan subdirectories
            include_patterns: Additional patterns to include
            max_file_size: Maximum file size to process (bytes)
        
        Yields:
            Batches of file event dictionaries
        """
        self.stats['start_time'] = datetime.utcnow()
        logger.info(f"Starting batch scan of {directory}")
        
        batch = []
        
        try:
            async for file_info in self._walk_directory(directory, recursive, max_file_size):
                # Check if file should be ignored
                ignore_result = self.ignore_manager.should_ignore_path(
                    file_info['file_path'], 
                    directory
                )
                
                if ignore_result['ignore']:
                    self.stats['files_ignored'] += 1
                    continue
                
                # Check include patterns if specified
                if include_patterns and not self._matches_patterns(file_info['file_path'], include_patterns):
                    self.stats['files_ignored'] += 1
                    continue
                
                # Add to batch
                batch.append(self._create_event_data(file_info))
                self.stats['files_processed'] += 1
                
                # Yield batch when full
                if len(batch) >= self.batch_size:
                    yield batch
                    batch = []
                    
                    # Allow other tasks to run
                    await asyncio.sleep(0)
            
            # Yield final batch if any
            if batch:
                yield batch
                
        finally:
            self.stats['end_time'] = datetime.utcnow()
            duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
            
            logger.info(f"Batch scan completed in {duration:.2f}s")
            logger.info(f"Scanned: {self.stats['files_scanned']} files, "
                       f"Processed: {self.stats['files_processed']}, "
                       f"Ignored: {self.stats['files_ignored']}")
    
    async def _walk_directory(self, directory: str, recursive: bool, 
                            max_file_size: Optional[int]) -> AsyncGenerator[Dict[str, Any], None]:
        """Walk directory and yield file information"""
        
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return
        
        if recursive:
            # Use os.walk for recursive scanning
            for root, dirs, files in os.walk(directory):
                self.stats['directories_scanned'] += 1
                
                # Filter out ignored directories
                dirs[:] = [d for d in dirs if not self._should_ignore_directory(os.path.join(root, d))]
                
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    
                    try:
                        file_info = await self._get_file_info(file_path, max_file_size)
                        if file_info:
                            self.stats['files_scanned'] += 1
                            self.stats['total_size'] += file_info.get('size', 0)
                            yield file_info
                    except Exception as e:
                        logger.warning(f"Error processing file {file_path}: {e}")
                
                # Allow other tasks to run periodically
                await asyncio.sleep(0)
        else:
            # Scan only immediate directory
            try:
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    
                    if os.path.isfile(item_path):
                        try:
                            file_info = await self._get_file_info(item_path, max_file_size)
                            if file_info:
                                self.stats['files_scanned'] += 1
                                self.stats['total_size'] += file_info.get('size', 0)
                                yield file_info
                        except Exception as e:
                            logger.warning(f"Error processing file {item_path}: {e}")
            except Exception as e:
                logger.error(f"Error listing directory {directory}: {e}")
    
    async def _get_file_info(self, file_path: str, max_file_size: Optional[int]) -> Optional[Dict[str, Any]]:
        """Get file information"""
        try:
            stat = os.stat(file_path)
            
            # Skip if file is too large
            if max_file_size and stat.st_size > max_file_size:
                logger.debug(f"Skipping large file: {file_path} ({stat.st_size} bytes)")
                return None
            
            # Get basic file info
            file_info = {
                'file_path': file_path,
                'size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime),
                'created_time': datetime.fromtimestamp(stat.st_ctime),
                'permissions': oct(stat.st_mode)[-3:],
                'is_directory': os.path.isdir(file_path)
            }
            
            # Get file extension and MIME type
            _, ext = os.path.splitext(file_path)
            file_info['extension'] = ext.lower()
            
            # Calculate hash for small files
            if stat.st_size < 1024 * 1024:  # 1MB limit for hash calculation
                file_info['hash'] = await self._calculate_file_hash(file_path)
            
            return file_info
            
        except (OSError, IOError) as e:
            logger.warning(f"Could not get info for {file_path}: {e}")
            return None
    
    async def _calculate_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate SHA-256 hash of file asynchronously"""
        try:
            import hashlib
            import aiofiles
            
            hasher = hashlib.sha256()
            
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(8192):
                    hasher.update(chunk)
            
            return hasher.hexdigest()
            
        except Exception as e:
            logger.warning(f"Could not calculate hash for {file_path}: {e}")
            return None
    
    def _should_ignore_directory(self, dir_path: str) -> bool:
        """Check if directory should be ignored"""
        # Check against ignore patterns
        return self.ignore_manager.should_ignore_path(dir_path)['ignore']
    
    def _matches_patterns(self, file_path: str, patterns: List[str]) -> bool:
        """Check if file matches any of the include patterns"""
        import fnmatch
        
        file_name = os.path.basename(file_path)
        
        for pattern in patterns:
            if fnmatch.fnmatch(file_name, pattern) or fnmatch.fnmatch(file_path, pattern):
                return True
        
        return False
    
    def _create_event_data(self, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """Create event data from file info"""
        return {
            'event_type': FileEventType.CREATED,
            'file_path': file_info['file_path'],
            'metadata': {
                'file_size': file_info['size'],
                'modified_time': file_info['modified_time'].isoformat(),
                'created_time': file_info['created_time'].isoformat(),
                'permissions': file_info['permissions'],
                'extension': file_info['extension'],
                'file_hash': file_info.get('hash'),
                'is_directory': file_info['is_directory'],
                'batch_import': True,
                'detected_at': datetime.utcnow().isoformat()
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get import statistics"""
        stats = self.stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['duration_seconds'] = duration
            stats['files_per_second'] = stats['files_scanned'] / max(duration, 1)
            stats['bytes_per_second'] = stats['total_size'] / max(duration, 1)
        
        return stats
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'files_scanned': 0,
            'files_ignored': 0,
            'files_processed': 0,
            'directories_scanned': 0,
            'total_size': 0,
            'start_time': None,
            'end_time': None
        }

class ThrottledBatchProcessor:
    """Processes batches with throttling to prevent overwhelming the system"""
    
    def __init__(self, max_batches_per_second: float = 10.0, max_events_per_second: float = 1000.0):
        self.max_batches_per_second = max_batches_per_second
        self.max_events_per_second = max_events_per_second
        
        self.batch_timestamps = []
        self.event_timestamps = []
        
        self.stats = {
            'batches_processed': 0,
            'events_processed': 0,
            'throttle_delays': 0,
            'total_delay_time': 0.0
        }
    
    async def process_batch(self, batch: List[Dict[str, Any]], 
                          processor_func: callable) -> Dict[str, Any]:
        """
        Process a batch with throttling
        
        Args:
            batch: List of events to process
            processor_func: Async function to process the batch
        
        Returns:
            Processing result
        """
        current_time = time.time()
        
        # Check if we need to throttle
        delay = self._calculate_throttle_delay(current_time, len(batch))
        
        if delay > 0:
            logger.debug(f"Throttling: waiting {delay:.2f}s")
            await asyncio.sleep(delay)
            self.stats['throttle_delays'] += 1
            self.stats['total_delay_time'] += delay
            current_time = time.time()
        
        # Record timestamps
        self.batch_timestamps.append(current_time)
        self.event_timestamps.extend([current_time] * len(batch))
        
        # Clean old timestamps (keep last minute)
        cutoff = current_time - 60
        self.batch_timestamps = [t for t in self.batch_timestamps if t > cutoff]
        self.event_timestamps = [t for t in self.event_timestamps if t > cutoff]
        
        # Process the batch
        try:
            result = await processor_func(batch)
            
            self.stats['batches_processed'] += 1
            self.stats['events_processed'] += len(batch)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            raise
    
    def _calculate_throttle_delay(self, current_time: float, batch_size: int) -> float:
        """Calculate how long to wait before processing"""
        delays = []
        
        # Check batch rate limit
        if self.max_batches_per_second > 0:
            recent_batches = [t for t in self.batch_timestamps if t > current_time - 1.0]
            if len(recent_batches) >= self.max_batches_per_second:
                batch_delay = (recent_batches[0] + 1.0) - current_time
                if batch_delay > 0:
                    delays.append(batch_delay)
        
        # Check event rate limit
        if self.max_events_per_second > 0:
            recent_events = [t for t in self.event_timestamps if t > current_time - 1.0]
            if len(recent_events) + batch_size > self.max_events_per_second:
                # Calculate when we can process this batch
                events_to_wait_for = (len(recent_events) + batch_size) - self.max_events_per_second
                if events_to_wait_for > 0 and recent_events:
                    event_delay = (recent_events[events_to_wait_for - 1] + 1.0) - current_time
                    if event_delay > 0:
                        delays.append(event_delay)
        
        return max(delays) if delays else 0.0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get throttling statistics"""
        return self.stats.copy()
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'batches_processed': 0,
            'events_processed': 0,
            'throttle_delays': 0,
            'total_delay_time': 0.0
        }