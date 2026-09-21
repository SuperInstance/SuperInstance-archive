#!/usr/bin/env python3
"""
Lightweight Bot Communication Protocol System
============================================

Ultra-lightweight communication system for bot interpreters that enables:
- Minimal overhead status sharing between bots
- Pattern synchronization across interpreter instances
- Cascading optimization notifications
- Smart context sharing for improved coordination

Key Design Principles:
- <1% CPU overhead per bot
- <10MB memory footprint total
- Async pub/sub messaging
- Automatic cleanup of stale connections
- Privacy-preserving pattern sharing (hashes only)
"""

import asyncio
import json
import time
import weakref
from typing import Dict, List, Set, Optional, Any, Callable, Union
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from enum import Enum
import logging
import hashlib
import pickle
import uuid
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class MessageType(Enum):
    """Types of lightweight messages between bots"""
    STATUS_UPDATE = "status_update"
    PATTERN_SYNC = "pattern_sync"
    OPTIMIZATION_HINT = "optimization_hint"
    CONTEXT_SHARE = "context_share"
    DEPENDENCY_NOTIFICATION = "dependency_notification"
    PERFORMANCE_METRIC = "performance_metric"

class MessagePriority(Enum):
    """Message priorities for lightweight processing"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4
    BACKGROUND = 5

@dataclass
class LightweightMessage:
    """Ultra-lightweight message structure"""
    msg_id: str
    msg_type: MessageType
    sender: str
    recipients: List[str]  # Empty list = broadcast
    priority: MessagePriority
    timestamp: float
    data: Dict[str, Any]
    ttl_seconds: int = 300  # 5 minute default TTL

@dataclass  
class BotStatus:
    """Lightweight bot status"""
    bot_id: str
    load_factor: float  # 0.0 to 1.0
    processing_queue_size: int
    avg_response_time_ms: float
    error_rate: float
    last_activity: float
    patterns_learned: int
    optimization_score: float

@dataclass
class PatternHint:
    """Privacy-preserving pattern hint"""
    pattern_hash: str  # Hash of actual pattern
    pattern_type: str
    success_rate: float
    usage_count: int
    applies_to_contexts: List[str]  # Hashed context types

class LightweightBotRegistry:
    """Ultra-lightweight registry for bot communication"""
    
    def __init__(self, max_bots: int = 1000):
        self.max_bots = max_bots
        self.bots: Dict[str, BotStatus] = {}
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.subscribers: Dict[MessageType, Set[str]] = defaultdict(set)
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
        
        # Performance tracking
        self.message_count = 0
        self.bytes_transferred = 0
        self.avg_message_size = 0.0
        
    def register_bot(self, bot_id: str, initial_status: Optional[BotStatus] = None) -> bool:
        """Register a bot with ultra-minimal overhead"""
        if len(self.bots) >= self.max_bots:
            logger.warning(f"Registry full, cannot register {bot_id}")
            return False
        
        if not initial_status:
            initial_status = BotStatus(
                bot_id=bot_id,
                load_factor=0.0,
                processing_queue_size=0,
                avg_response_time_ms=0.0,
                error_rate=0.0,
                last_activity=time.time(),
                patterns_learned=0,
                optimization_score=0.0
            )
        
        self.bots[bot_id] = initial_status
        return True
    
    def unregister_bot(self, bot_id: str) -> bool:
        """Unregister bot and cleanup resources"""
        if bot_id in self.bots:
            del self.bots[bot_id]
            
            # Cleanup message queue
            if bot_id in self.message_queues:
                del self.message_queues[bot_id]
            
            # Remove from subscribers
            for subscribers in self.subscribers.values():
                subscribers.discard(bot_id)
            
            return True
        return False
    
    def update_bot_status(self, bot_id: str, status: BotStatus) -> bool:
        """Update bot status with minimal processing"""
        if bot_id not in self.bots:
            return False
        
        self.bots[bot_id] = status
        self._maybe_cleanup()
        return True
    
    def subscribe_to_messages(self, bot_id: str, message_types: List[MessageType]) -> bool:
        """Subscribe bot to specific message types"""
        if bot_id not in self.bots:
            return False
        
        for msg_type in message_types:
            self.subscribers[msg_type].add(bot_id)
        
        return True
    
    def _maybe_cleanup(self):
        """Periodic cleanup with minimal overhead"""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        # Remove stale bots (inactive for >30 minutes)
        stale_threshold = current_time - 1800  # 30 minutes
        stale_bots = [
            bot_id for bot_id, status in self.bots.items()
            if status.last_activity < stale_threshold
        ]
        
        for bot_id in stale_bots:
            self.unregister_bot(bot_id)
        
        self.last_cleanup = current_time
        
        if stale_bots:
            logger.info(f"🧹 Cleaned up {len(stale_bots)} stale bot registrations")

class MessageProcessor:
    """Lightweight message processor with minimal CPU overhead"""
    
    def __init__(self, bot_id: str, registry: LightweightBotRegistry):
        self.bot_id = bot_id
        self.registry = registry
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.processing_enabled = True
        
        # Performance monitoring
        self.messages_processed = 0
        self.processing_time_total = 0.0
        self.last_performance_log = time.time()
    
    def register_handler(self, msg_type: MessageType, handler: Callable):
        """Register lightweight message handler"""
        self.message_handlers[msg_type] = handler
        
        # Auto-subscribe to this message type
        self.registry.subscribe_to_messages(self.bot_id, [msg_type])
    
    async def process_pending_messages(self, max_messages: int = 10) -> int:
        """Process pending messages with CPU limit"""
        if not self.processing_enabled:
            return 0
        
        processed = 0
        start_time = time.time()
        
        queue = self.registry.message_queues[self.bot_id]
        
        while queue and processed < max_messages:
            try:
                message = queue.popleft()
                
                # Check TTL
                if time.time() - message.timestamp > message.ttl_seconds:
                    continue  # Skip expired message
                
                # Process by priority (higher priority = lower number)
                if message.msg_type in self.message_handlers:
                    handler = self.message_handlers[message.msg_type]
                    
                    # Run handler with timeout for lightweight processing
                    try:
                        await asyncio.wait_for(handler(message), timeout=0.1)  # 100ms max per message
                    except asyncio.TimeoutError:
                        logger.warning(f"Handler timeout for {message.msg_type} from {message.sender}")
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing message: {e}")
        
        # Update performance metrics
        processing_time = time.time() - start_time
        self.processing_time_total += processing_time
        self.messages_processed += processed
        
        return processed
    
    def get_performance_stats(self) -> Dict[str, float]:
        """Get lightweight performance statistics"""
        if self.messages_processed == 0:
            return {'avg_processing_time_ms': 0.0, 'messages_per_second': 0.0}
        
        avg_time = (self.processing_time_total / self.messages_processed) * 1000
        current_time = time.time()
        elapsed = current_time - self.last_performance_log
        mps = self.messages_processed / elapsed if elapsed > 0 else 0.0
        
        return {
            'avg_processing_time_ms': avg_time,
            'messages_per_second': mps,
            'total_processed': self.messages_processed
        }

class LightweightCommunicator:
    """Main communication interface for bots"""
    
    def __init__(self, bot_id: str, registry: LightweightBotRegistry):
        self.bot_id = bot_id
        self.registry = registry
        self.processor = MessageProcessor(bot_id, registry)
        
        # Register this bot
        self.registry.register_bot(bot_id)
        
        # Setup default handlers
        self._setup_default_handlers()
        
        # Background processing
        self.background_task: Optional[asyncio.Task] = None
        self.processing_active = False
    
    def _setup_default_handlers(self):
        """Setup default lightweight message handlers"""
        
        async def handle_status_update(message: LightweightMessage):
            """Handle bot status updates"""
            # Minimal processing - just log significant status changes
            sender_status = BotStatus(**message.data)
            if sender_status.error_rate > 0.1:  # >10% error rate
                logger.warning(f"High error rate from {message.sender}: {sender_status.error_rate:.2%}")
        
        async def handle_pattern_sync(message: LightweightMessage):
            """Handle pattern synchronization hints"""
            pattern_hint = PatternHint(**message.data)
            if pattern_hint.success_rate > 0.9:  # Only sync highly successful patterns
                # Store hint for potential use (implementation depends on bot type)
                logger.debug(f"High-success pattern hint from {message.sender}: {pattern_hint.pattern_hash[:8]}")
        
        async def handle_optimization_hint(message: LightweightMessage):
            """Handle optimization hints from other bots"""
            optimization_data = message.data
            if optimization_data.get('confidence', 0) > 0.8:
                logger.info(f"Optimization hint from {message.sender}: {optimization_data.get('suggestion', 'unknown')}")
        
        # Register handlers
        self.processor.register_handler(MessageType.STATUS_UPDATE, handle_status_update)
        self.processor.register_handler(MessageType.PATTERN_SYNC, handle_pattern_sync)
        self.processor.register_handler(MessageType.OPTIMIZATION_HINT, handle_optimization_hint)
    
    async def start_background_processing(self):
        """Start lightweight background message processing"""
        if self.background_task and not self.background_task.done():
            return  # Already running
        
        self.processing_active = True
        self.background_task = asyncio.create_task(self._background_message_loop())
        logger.debug(f"Started background processing for {self.bot_id}")
    
    async def stop_background_processing(self):
        """Stop background processing"""
        self.processing_active = False
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        logger.debug(f"Stopped background processing for {self.bot_id}")
    
    async def _background_message_loop(self):
        """Ultra-lightweight background message processing loop"""
        while self.processing_active:
            try:
                # Process messages with minimal CPU impact
                processed = await self.processor.process_pending_messages(max_messages=5)
                
                # Adaptive sleep - more sleep if no messages
                if processed == 0:
                    await asyncio.sleep(1.0)  # 1 second if no messages
                else:
                    await asyncio.sleep(0.1)  # 100ms if processing messages
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background processing for {self.bot_id}: {e}")
                await asyncio.sleep(5.0)  # Back off on error
    
    def send_message(self, msg_type: MessageType, data: Dict[str, Any], 
                    recipients: Optional[List[str]] = None, 
                    priority: MessagePriority = MessagePriority.NORMAL,
                    ttl_seconds: int = 300) -> str:
        """Send lightweight message to other bots"""
        
        message = LightweightMessage(
            msg_id=str(uuid.uuid4())[:8],  # Short ID for efficiency
            msg_type=msg_type,
            sender=self.bot_id,
            recipients=recipients or [],  # Empty = broadcast
            priority=priority,
            timestamp=time.time(),
            data=data,
            ttl_seconds=ttl_seconds
        )
        
        # Determine actual recipients
        if recipients:
            actual_recipients = [r for r in recipients if r in self.registry.bots]
        else:
            # Broadcast to subscribers of this message type
            actual_recipients = list(self.registry.subscribers.get(msg_type, set()))
        
        # Queue message for recipients
        message_data = asdict(message)
        message_size = len(json.dumps(message_data).encode())
        
        for recipient in actual_recipients:
            if recipient != self.bot_id:  # Don't send to self
                self.registry.message_queues[recipient].append(message)
        
        # Update registry statistics
        self.registry.message_count += 1
        self.registry.bytes_transferred += message_size * len(actual_recipients)
        self.registry.avg_message_size = self.registry.bytes_transferred / self.registry.message_count
        
        return message.msg_id
    
    def broadcast_status_update(self, status: BotStatus):
        """Broadcast status update with minimal overhead"""
        # Only broadcast if significant change
        current_status = self.registry.bots.get(self.bot_id)
        if current_status and self._status_change_significant(current_status, status):
            self.send_message(
                MessageType.STATUS_UPDATE,
                asdict(status),
                priority=MessagePriority.LOW  # Status updates are low priority
            )
        
        # Always update local registry
        self.registry.update_bot_status(self.bot_id, status)
    
    def _status_change_significant(self, old: BotStatus, new: BotStatus) -> bool:
        """Determine if status change is significant enough to broadcast"""
        # Check for significant changes to avoid spam
        return (
            abs(old.load_factor - new.load_factor) > 0.1 or  # 10% load change
            abs(old.error_rate - new.error_rate) > 0.05 or   # 5% error rate change
            abs(old.optimization_score - new.optimization_score) > 0.1  # 10% optimization change
        )
    
    def share_pattern_hint(self, pattern_hash: str, pattern_type: str, 
                          success_rate: float, usage_count: int,
                          contexts: List[str]):
        """Share pattern hint with other bots"""
        
        # Only share high-quality patterns
        if success_rate < 0.8:
            return
        
        hint = PatternHint(
            pattern_hash=pattern_hash,
            pattern_type=pattern_type,
            success_rate=success_rate,
            usage_count=usage_count,
            applies_to_contexts=contexts
        )
        
        self.send_message(
            MessageType.PATTERN_SYNC,
            asdict(hint),
            priority=MessagePriority.NORMAL
        )
    
    def send_optimization_hint(self, suggestion: str, confidence: float, 
                             affected_components: List[str]):
        """Send optimization hint to relevant bots"""
        
        optimization_data = {
            'suggestion': suggestion,
            'confidence': confidence,
            'affected_components': affected_components,
            'timestamp': time.time()
        }
        
        self.send_message(
            MessageType.OPTIMIZATION_HINT,
            optimization_data,
            priority=MessagePriority.HIGH
        )
    
    def notify_dependency_change(self, dependency_type: str, change_description: str,
                               affected_bots: List[str]):
        """Notify about dependency changes"""
        
        notification_data = {
            'dependency_type': dependency_type,
            'change_description': change_description,
            'severity': 'medium'  # Can be 'low', 'medium', 'high', 'critical'
        }
        
        self.send_message(
            MessageType.DEPENDENCY_NOTIFICATION,
            notification_data,
            recipients=affected_bots,
            priority=MessagePriority.HIGH
        )
    
    def get_nearby_bots(self, max_distance: float = 0.3) -> List[str]:
        """Get bots with similar performance characteristics"""
        if self.bot_id not in self.registry.bots:
            return []
        
        my_status = self.registry.bots[self.bot_id]
        nearby_bots = []
        
        for bot_id, status in self.registry.bots.items():
            if bot_id == self.bot_id:
                continue
            
            # Calculate simple distance based on key metrics
            load_diff = abs(my_status.load_factor - status.load_factor)
            error_diff = abs(my_status.error_rate - status.error_rate)
            opt_diff = abs(my_status.optimization_score - status.optimization_score)
            
            distance = (load_diff + error_diff + opt_diff) / 3.0
            
            if distance <= max_distance:
                nearby_bots.append(bot_id)
        
        return nearby_bots
    
    def get_communication_stats(self) -> Dict[str, Any]:
        """Get communication statistics"""
        performance = self.processor.get_performance_stats()
        
        return {
            'bot_id': self.bot_id,
            'messages_in_queue': len(self.registry.message_queues[self.bot_id]),
            'processing_performance': performance,
            'background_processing_active': self.processing_active,
            'registered_handlers': len(self.processor.message_handlers),
            'nearby_bots': len(self.get_nearby_bots()),
            'registry_stats': {
                'total_bots': len(self.registry.bots),
                'total_messages_processed': self.registry.message_count,
                'avg_message_size_bytes': self.registry.avg_message_size,
                'total_bytes_transferred': self.registry.bytes_transferred
            }
        }

class CommunicationManager:
    """Manages all bot communication in the system"""
    
    def __init__(self, max_bots: int = 1000):
        self.registry = LightweightBotRegistry(max_bots)
        self.communicators: Dict[str, LightweightCommunicator] = {}
        self.system_stats = {
            'start_time': time.time(),
            'peak_concurrent_bots': 0,
            'total_messages_sent': 0
        }
        
    def create_communicator(self, bot_id: str) -> LightweightCommunicator:
        """Create communicator for a bot"""
        if bot_id in self.communicators:
            return self.communicators[bot_id]
        
        communicator = LightweightCommunicator(bot_id, self.registry)
        self.communicators[bot_id] = communicator
        
        # Update peak concurrent bots
        self.system_stats['peak_concurrent_bots'] = max(
            self.system_stats['peak_concurrent_bots'],
            len(self.communicators)
        )
        
        return communicator
    
    def remove_communicator(self, bot_id: str) -> bool:
        """Remove communicator and cleanup"""
        if bot_id not in self.communicators:
            return False
        
        communicator = self.communicators[bot_id]
        
        # Stop background processing
        asyncio.create_task(communicator.stop_background_processing())
        
        # Remove from registry
        self.registry.unregister_bot(bot_id)
        
        # Remove from communicators
        del self.communicators[bot_id]
        
        return True
    
    async def start_all_background_processing(self):
        """Start background processing for all communicators"""
        tasks = []
        for communicator in self.communicators.values():
            tasks.append(communicator.start_background_processing())
        
        if tasks:
            await asyncio.gather(*tasks)
        
        logger.info(f"Started background processing for {len(tasks)} communicators")
    
    async def stop_all_background_processing(self):
        """Stop background processing for all communicators"""
        tasks = []
        for communicator in self.communicators.values():
            tasks.append(communicator.stop_background_processing())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"Stopped background processing for {len(tasks)} communicators")
    
    def broadcast_system_message(self, message_type: MessageType, data: Dict[str, Any],
                                priority: MessagePriority = MessagePriority.NORMAL):
        """Broadcast message to all bots in system"""
        
        # Use any communicator to send broadcast
        if self.communicators:
            sender_id = list(self.communicators.keys())[0]
            communicator = self.communicators[sender_id]
            
            message_id = communicator.send_message(
                message_type, data, 
                recipients=None,  # Broadcast
                priority=priority
            )
            
            self.system_stats['total_messages_sent'] += 1
            return message_id
        
        return None
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics"""
        current_time = time.time()
        uptime = current_time - self.system_stats['start_time']
        
        # Aggregate stats from all communicators
        total_queue_size = sum(
            len(self.registry.message_queues[bot_id])
            for bot_id in self.communicators.keys()
        )
        
        # Calculate system-wide metrics
        active_bots = len([c for c in self.communicators.values() if c.processing_active])
        
        return {
            'system_uptime_seconds': uptime,
            'active_bots': len(self.communicators),
            'active_background_processors': active_bots,
            'peak_concurrent_bots': self.system_stats['peak_concurrent_bots'],
            'total_pending_messages': total_queue_size,
            'registry_stats': {
                'registered_bots': len(self.registry.bots),
                'message_types_subscribed': len(self.registry.subscribers),
                'total_messages_sent': self.registry.message_count,
                'total_bytes_transferred': self.registry.bytes_transferred,
                'avg_message_size_bytes': round(self.registry.avg_message_size, 2)
            },
            'performance': {
                'messages_per_second': self.registry.message_count / uptime if uptime > 0 else 0,
                'bytes_per_second': self.registry.bytes_transferred / uptime if uptime > 0 else 0,
                'avg_queue_size': total_queue_size / len(self.communicators) if self.communicators else 0
            }
        }

# Global communication manager
communication_manager = CommunicationManager()

# Easy integration functions
def create_bot_communicator(bot_id: str) -> LightweightCommunicator:
    """Create lightweight communicator for a bot"""
    return communication_manager.create_communicator(bot_id)

def remove_bot_communicator(bot_id: str) -> bool:
    """Remove bot communicator"""
    return communication_manager.remove_communicator(bot_id)

async def start_communication_system():
    """Start the lightweight communication system"""
    await communication_manager.start_all_background_processing()
    logger.info("🔗 Lightweight bot communication system started")

async def stop_communication_system():
    """Stop the lightweight communication system"""
    await communication_manager.stop_all_background_processing()
    logger.info("🔗 Lightweight bot communication system stopped")

def get_communication_system_stats() -> Dict[str, Any]:
    """Get communication system statistics"""
    return communication_manager.get_system_statistics()

def broadcast_system_optimization_hint(suggestion: str, confidence: float):
    """Broadcast optimization hint to all bots"""
    data = {
        'suggestion': suggestion,
        'confidence': confidence,
        'system_wide': True,
        'timestamp': time.time()
    }
    
    return communication_manager.broadcast_system_message(
        MessageType.OPTIMIZATION_HINT,
        data,
        MessagePriority.HIGH
    )

if __name__ == "__main__":
    # Test the lightweight communication system
    async def test_communication_system():
        print("🧪 Testing Lightweight Bot Communication System")
        print("=" * 50)
        
        # Create test communicators
        bot1 = create_bot_communicator("test_bot_1")
        bot2 = create_bot_communicator("test_bot_2")
        bot3 = create_bot_communicator("test_bot_3")
        
        # Start background processing
        await start_communication_system()
        
        # Test status updates
        status1 = BotStatus(
            bot_id="test_bot_1",
            load_factor=0.3,
            processing_queue_size=5,
            avg_response_time_ms=150.0,
            error_rate=0.02,
            last_activity=time.time(),
            patterns_learned=25,
            optimization_score=0.8
        )
        
        bot1.broadcast_status_update(status1)
        
        # Test pattern sharing
        bot1.share_pattern_hint(
            pattern_hash="abc12345",
            pattern_type="command_translation",
            success_rate=0.95,
            usage_count=100,
            contexts=["linux_system", "file_operations"]
        )
        
        # Test optimization hint
        bot2.send_optimization_hint(
            suggestion="Consider consolidating file operations",
            confidence=0.85,
            affected_components=["file_handler", "disk_manager"]
        )
        
        # Wait for message processing
        await asyncio.sleep(2)
        
        # Get statistics
        print("\n📊 Communication Statistics:")
        system_stats = get_communication_system_stats()
        for key, value in system_stats.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
        
        # Test individual communicator stats
        print(f"\n🤖 Bot 1 Communication Stats:")
        bot1_stats = bot1.get_communication_stats()
        for key, value in bot1_stats.items():
            if isinstance(value, dict):
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")
        
        # Test nearby bots
        nearby = bot1.get_nearby_bots()
        print(f"\n🔍 Nearby bots to bot1: {nearby}")
        
        # Cleanup
        await stop_communication_system()
        
        print("\n✅ Lightweight communication system test completed!")
    
    asyncio.run(test_communication_system())