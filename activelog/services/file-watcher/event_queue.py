"""
Event queue management for file watcher
Handles queuing events to sync engine and NATS
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

import nats
from nats.aio.client import Client as NATS
from nats.js.api import StreamConfig, ConsumerConfig, RetentionPolicy, DiscardPolicy
import redis.asyncio as redis
import aiofiles

from config import WatcherConfig

logger = logging.getLogger(__name__)

class EventQueue:
    """Manages queuing of file events"""
    
    def __init__(self, config: WatcherConfig):
        self.config = config
        self.nats_client: Optional[NATS] = None
        self.redis_client: Optional[redis.Redis] = None
        self.jetstream = None
        
        # Local queue for when external systems are unavailable
        self.local_queue: List[Dict[str, Any]] = []
        self.max_local_queue_size = 1000
        
        # Connection status
        self.nats_connected = False
        self.redis_connected = False
        
    async def initialize(self):
        """Initialize connections to NATS and Redis"""
        logger.info("Initializing event queue...")
        
        # Initialize NATS
        await self._init_nats()
        
        # Initialize Redis
        await self._init_redis()
        
        logger.info(f"Event queue initialized (NATS: {self.nats_connected}, Redis: {self.redis_connected})")
    
    async def _init_nats(self):
        """Initialize NATS connection and JetStream"""
        try:
            self.nats_client = NATS()
            await self.nats_client.connect(**self.config.get_nats_config())
            
            # Initialize JetStream
            self.jetstream = self.nats_client.jetstream()
            
            # Create or update stream for file events
            try:
                await self.jetstream.add_stream(StreamConfig(
                    name="FILE_EVENTS",
                    subjects=[self.config.nats_subject],
                    retention=RetentionPolicy.WORK_QUEUE,
                    discard=DiscardPolicy.OLD,
                    max_msgs=100000,
                    max_age=86400,  # 24 hours
                    max_bytes=1024*1024*1024,  # 1GB
                    duplicate_window=60,  # 1 minute
                ))
            except Exception as e:
                # Stream might already exist
                logger.debug(f"Stream creation info: {e}")
            
            self.nats_connected = True
            logger.info("NATS connection established")
            
        except Exception as e:
            logger.warning(f"Failed to connect to NATS: {e}")
            self.nats_connected = False
    
    async def _init_redis(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.from_url(
                self.config.get_redis_url(),
                encoding='utf-8',
                decode_responses=True
            )
            
            # Test connection
            await self.redis_client.ping()
            self.redis_connected = True
            logger.info("Redis connection established")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.redis_connected = False
    
    async def queue_event(self, event_data: Dict[str, Any]) -> bool:
        """Queue a file event for processing"""
        try:
            # Add event metadata
            event_data['queued_at'] = datetime.utcnow().isoformat()
            event_data['event_id'] = str(uuid.uuid4())
            
            # Try to send to NATS first
            if await self._send_to_nats(event_data):
                return True
            
            # Fallback to Redis
            if await self._send_to_redis(event_data):
                return True
            
            # Last resort: local queue
            await self._add_to_local_queue(event_data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue event: {e}")
            return False
    
    async def queue_batch(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Queue a batch of events"""
        batch_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        batch_data = {
            'batch_id': batch_id,
            'timestamp': timestamp,
            'event_count': len(events),
            'events': events
        }
        
        success_count = 0
        failed_events = []
        
        if self.config.enable_sync_queue:
            # Try to send as batch to NATS
            if await self._send_batch_to_nats(batch_data):
                success_count = len(events)
            else:
                # Send individual events as fallback
                for event in events:
                    if await self.queue_event(event):
                        success_count += 1
                    else:
                        failed_events.append(event)
        
        return {
            'batch_id': batch_id,
            'success_count': success_count,
            'failed_count': len(failed_events),
            'failed_events': failed_events
        }
    
    async def _send_to_nats(self, event_data: Dict[str, Any]) -> bool:
        """Send event to NATS JetStream"""
        if not self.nats_connected or not self.jetstream:
            return False
        
        try:
            message_data = json.dumps(event_data).encode()
            
            ack = await self.jetstream.publish(
                self.config.nats_subject,
                message_data,
                headers={'event_type': event_data.get('event_type', 'unknown')}
            )
            
            logger.debug(f"Event sent to NATS: {ack.seq}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send to NATS: {e}")
            return False
    
    async def _send_batch_to_nats(self, batch_data: Dict[str, Any]) -> bool:
        """Send batch to NATS JetStream"""
        if not self.nats_connected or not self.jetstream:
            return False
        
        try:
            message_data = json.dumps(batch_data).encode()
            
            ack = await self.jetstream.publish(
                f"{self.config.nats_subject}.batch",
                message_data,
                headers={'batch_id': batch_data['batch_id']}
            )
            
            logger.debug(f"Batch sent to NATS: {ack.seq}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send batch to NATS: {e}")
            return False
    
    async def _send_to_redis(self, event_data: Dict[str, Any]) -> bool:
        """Send event to Redis queue"""
        if not self.redis_connected or not self.redis_client:
            return False
        
        try:
            queue_key = f"file_events:{self.config.nats_queue_group}"
            
            await self.redis_client.lpush(
                queue_key,
                json.dumps(event_data)
            )
            
            # Trim queue to prevent memory issues
            await self.redis_client.ltrim(queue_key, 0, 10000)
            
            logger.debug("Event sent to Redis queue")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to send to Redis: {e}")
            return False
    
    async def _add_to_local_queue(self, event_data: Dict[str, Any]):
        """Add event to local queue as last resort"""
        if len(self.local_queue) >= self.max_local_queue_size:
            # Remove oldest events to make room
            self.local_queue = self.local_queue[-self.max_local_queue_size//2:]
        
        self.local_queue.append(event_data)
        logger.debug(f"Event added to local queue (size: {len(self.local_queue)})")
    
    async def flush_local_queue(self) -> int:
        """Flush local queue to external systems"""
        if not self.local_queue:
            return 0
        
        flushed_count = 0
        remaining_events = []
        
        for event in self.local_queue:
            if await self._send_to_nats(event) or await self._send_to_redis(event):
                flushed_count += 1
            else:
                remaining_events.append(event)
        
        self.local_queue = remaining_events
        
        if flushed_count > 0:
            logger.info(f"Flushed {flushed_count} events from local queue")
        
        return flushed_count
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        stats = {
            'nats_connected': self.nats_connected,
            'redis_connected': self.redis_connected,
            'local_queue_size': len(self.local_queue),
            'max_local_queue_size': self.max_local_queue_size
        }
        
        # Get Redis queue size if connected
        if self.redis_connected and self.redis_client:
            try:
                queue_key = f"file_events:{self.config.nats_queue_group}"
                redis_queue_size = await self.redis_client.llen(queue_key)
                stats['redis_queue_size'] = redis_queue_size
            except Exception as e:
                logger.warning(f"Failed to get Redis queue size: {e}")
                stats['redis_queue_size'] = -1
        
        return stats
    
    async def reconnect(self):
        """Attempt to reconnect to external systems"""
        logger.info("Attempting to reconnect to external systems...")
        
        # Try NATS reconnection
        if not self.nats_connected:
            await self._init_nats()
        
        # Try Redis reconnection
        if not self.redis_connected:
            await self._init_redis()
        
        # Flush local queue if we have connections
        if self.nats_connected or self.redis_connected:
            await self.flush_local_queue()
    
    async def close(self):
        """Close all connections"""
        logger.info("Closing event queue connections...")
        
        # Flush local queue before closing
        await self.flush_local_queue()
        
        # Close NATS
        if self.nats_client:
            await self.nats_client.close()
            self.nats_connected = False
        
        # Close Redis
        if self.redis_client:
            await self.redis_client.close()
            self.redis_connected = False
        
        logger.info("Event queue connections closed")

class SyncEngineClient:
    """Client for communicating with sync engine"""
    
    def __init__(self, config: WatcherConfig):
        self.config = config
        self.base_url = config.sync_engine_url.rstrip('/')
        self.api_key = config.sync_api_key
        
    async def notify_file_change(self, event_data: Dict[str, Any]) -> bool:
        """Notify sync engine of file change"""
        try:
            import aiohttp
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Bearer {self.api_key}"
            
            # Map our event data to sync engine format
            sync_data = {
                'file_path': event_data['file_path'],
                'event_type': event_data['event_type'],
                'metadata': event_data.get('metadata', {}),
                'detected_at': event_data.get('detected_at'),
                'source': 'file-watcher'
            }
            
            if 'old_path' in event_data:
                sync_data['old_path'] = event_data['old_path']
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/events",
                    json=sync_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status < 300:
                        logger.debug(f"Notified sync engine of event: {event_data['file_path']}")
                        return True
                    else:
                        logger.warning(f"Sync engine returned {response.status}")
                        return False
        
        except Exception as e:
            logger.warning(f"Failed to notify sync engine: {e}")
            return False
    
    async def notify_batch(self, events: List[Dict[str, Any]]) -> bool:
        """Notify sync engine of batch of events"""
        try:
            import aiohttp
            
            headers = {}
            if self.api_key:
                headers['Authorization'] = f"Bearer {self.api_key}"
            
            sync_data = {
                'events': [
                    {
                        'file_path': event['file_path'],
                        'event_type': event['event_type'],
                        'metadata': event.get('metadata', {}),
                        'detected_at': event.get('detected_at'),
                        'source': 'file-watcher'
                    }
                    for event in events
                ],
                'batch_timestamp': datetime.utcnow().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/v1/events/batch",
                    json=sync_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status < 300:
                        logger.info(f"Notified sync engine of batch: {len(events)} events")
                        return True
                    else:
                        logger.warning(f"Sync engine batch returned {response.status}")
                        return False
        
        except Exception as e:
            logger.warning(f"Failed to notify sync engine of batch: {e}")
            return False