"""
Working Memory System

Provides short-term memory buffer with capacity limits and temporal decay.
Inspired by human working memory with 7±2 item capacity, extended to 20 items
for AI agents with 30-minute decay function.
"""

import time
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import deque
import logging

logger = logging.getLogger(__name__)

@dataclass
class WorkingMemoryItem:
    """Individual item in working memory"""
    content: Any
    item_type: str  # 'observation', 'action', 'thought', 'emotion'
    timestamp: float = field(default_factory=time.time)
    importance: float = 1.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    context_tags: List[str] = field(default_factory=list)

    def mark_accessed(self):
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = time.time()

    def get_age(self) -> float:
        """Get age in seconds"""
        return time.time() - self.timestamp

    def get_time_since_access(self) -> float:
        """Get time since last access"""
        return time.time() - self.last_accessed

class WorkingMemory:
    """
    Working memory system with 20-item capacity and 30-minute decay.
    Implements priority-based eviction and temporal decay of importance.
    """

    def __init__(self, max_capacity: int = 20, decay_time: float = 1800.0):
        """
        Initialize working memory

        Args:
            max_capacity: Maximum number of items (default: 20)
            decay_time: Time in seconds for importance decay (default: 30 minutes)
        """
        self.max_capacity = max_capacity
        self.decay_time = decay_time
        self.items: deque[WorkingMemoryItem] = deque(maxlen=max_capacity)
        self.lock = threading.RLock()
        self.decay_thread = None
        self.running = True

        # Statistics
        self.total_added = 0
        self.total_evicted = 0
        self.total_expired = 0

        # Start decay maintenance thread
        self._start_decay_thread()

    def add_item(self, content: Any, item_type: str = 'observation',
                 importance: float = 1.0, context_tags: List[str] = None) -> bool:
        """
        Add item to working memory

        Args:
            content: The content to store
            item_type: Type of item ('observation', 'action', 'thought', 'emotion')
            importance: Initial importance score (0-1)
            context_tags: List of context tags for retrieval

        Returns:
            True if item was added, False if memory is full
        """
        with self.lock:
            item = WorkingMemoryItem(
                content=content,
                item_type=item_type,
                importance=importance,
                context_tags=context_tags or []
            )

            # Check if we need to make space
            if len(self.items) >= self.max_capacity:
                if not self._evict_item():
                    logger.warning("Working memory full and unable to evict low-priority items")
                    return False

            self.items.append(item)
            self.total_added += 1

            logger.debug(f"Added {item_type} item to working memory (capacity: {len(self.items)}/{self.max_capacity})")
            return True

    def get_items(self, item_type: str = None, context_tag: str = None,
                  limit: int = None) -> List[WorkingMemoryItem]:
        """
        Retrieve items from working memory

        Args:
            item_type: Filter by item type
            context_tag: Filter by context tag
            limit: Maximum number of items to return

        Returns:
            List of working memory items
        """
        with self.lock:
            items = list(self.items)

            # Apply filters
            if item_type:
                items = [item for item in items if item.item_type == item_type]

            if context_tag:
                items = [item for item in items if context_tag in item.context_tags]

            # Sort by importance (descending)
            items.sort(key=lambda x: x.importance, reverse=True)

            # Mark accessed and update importance
            for item in items:
                item.mark_accessed()

            # Apply limit
            if limit:
                items = items[:limit]

            return items

    def get_recent_items(self, time_seconds: float = 300.0) -> List[WorkingMemoryItem]:
        """
        Get items from recent time window

        Args:
            time_seconds: Time window in seconds (default: 5 minutes)

        Returns:
            List of recent items
        """
        with self.lock:
            current_time = time.time()
            cutoff_time = current_time - time_seconds

            recent_items = [
                item for item in self.items
                if item.timestamp >= cutoff_time
            ]

            # Mark accessed
            for item in recent_items:
                item.mark_accessed()

            return recent_items

    def search(self, query: str, limit: int = 5) -> List[WorkingMemoryItem]:
        """
        Search working memory by content

        Args:
            query: Search query string
            limit: Maximum results

        Returns:
            List of matching items
        """
        with self.lock:
            query_lower = query.lower()
            matching_items = []

            for item in self.items:
                content_str = str(item.content).lower()
                if query_lower in content_str:
                    matching_items.append(item)

            # Sort by importance
            matching_items.sort(key=lambda x: x.importance, reverse=True)

            # Mark accessed and limit
            results = matching_items[:limit]
            for item in results:
                item.mark_accessed()

            return results

    def clear(self) -> int:
        """
        Clear all items from working memory

        Returns:
            Number of items cleared
        """
        with self.lock:
            count = len(self.items)
            self.items.clear()
            return count

    def get_capacity_usage(self) -> Dict[str, float]:
        """
        Get current capacity usage statistics

        Returns:
            Dictionary with usage metrics
        """
        with self.lock:
            current_usage = len(self.items)
            usage_ratio = current_usage / self.max_capacity

            # Calculate average importance
            if self.items:
                avg_importance = sum(item.importance for item in self.items) / len(self.items)
            else:
                avg_importance = 0.0

            return {
                "current_items": current_usage,
                "max_capacity": self.max_capacity,
                "usage_ratio": usage_ratio,
                "available_slots": self.max_capacity - current_usage,
                "average_importance": avg_importance
            }

    def _evict_item(self) -> bool:
        """
        Evict lowest priority item to make space

        Returns:
            True if item was evicted
        """
        if not self.items:
            return False

        # Find item with lowest priority (importance × recency)
        current_time = time.time()
        min_priority = float('inf')
        min_index = -1

        for i, item in enumerate(self.items):
            # Calculate priority: importance × recency_factor × access_frequency
            recency_factor = 1.0 / (1.0 + (current_time - item.last_accessed) / 60.0)  # Decay over minutes
            access_factor = 1.0 + (item.access_count * 0.1)  # Boost for frequently accessed items
            priority = item.importance * recency_factor * access_factor

            if priority < min_priority:
                min_priority = priority
                min_index = i

        if min_index >= 0:
            # Remove the lowest priority item
            evicted_item = self.items[min_index]
            del self.items[min_index]
            self.total_evicted += 1

            logger.debug(f"Evicted {evicted_item.item_type} item (priority: {min_priority:.3f})")
            return True

        return False

    def _apply_decay(self):
        """Apply temporal decay to item importance"""
        with self.lock:
            current_time = time.time()
            items_to_remove = []

            for item in self.items:
                age = current_time - item.timestamp

                # Apply exponential decay: importance = initial * e^(-age/decay_time)
                decay_factor = max(0.1, 1.0 - (age / self.decay_time))
                item.importance *= decay_factor

                # Remove items with very low importance
                if item.importance < 0.01:
                    items_to_remove.append(item)

            # Remove expired items
            for item in items_to_remove:
                try:
                    self.items.remove(item)
                    self.total_expired += 1
                except ValueError:
                    pass  # Item already removed

    def _decay_maintenance_loop(self):
        """Background thread for decay maintenance"""
        while self.running:
            try:
                self._apply_decay()
                time.sleep(60)  # Run every minute
            except Exception as e:
                logger.error(f"Error in decay maintenance: {e}")

    def _start_decay_thread(self):
        """Start the background decay maintenance thread"""
        self.decay_thread = threading.Thread(
            target=self._decay_maintenance_loop,
            daemon=True,
            name="WorkingMemoryDecay"
        )
        self.decay_thread.start()

    def shutdown(self):
        """Shutdown the working memory system"""
        self.running = False
        if self.decay_thread and self.decay_thread.is_alive():
            self.decay_thread.join(timeout=5.0)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about working memory

        Returns:
            Statistics dictionary
        """
        with self.lock:
            # Item type distribution
            type_counts = {}
            for item in self.items:
                type_counts[item.item_type] = type_counts.get(item.item_type, 0) + 1

            return {
                "current_items": len(self.items),
                "max_capacity": self.max_capacity,
                "total_added": self.total_added,
                "total_evicted": self.total_evicted,
                "total_expired": self.total_expired,
                "type_distribution": type_counts,
                "average_importance": sum(item.importance for item in self.items) / len(self.items) if self.items else 0.0,
                "oldest_item_age": max(item.get_age() for item in self.items) if self.items else 0.0,
                "newest_item_age": min(item.get_age() for item in self.items) if self.items else 0.0
            }

    def __len__(self) -> int:
        """Return current number of items"""
        return len(self.items)

    def __contains__(self, content: Any) -> bool:
        """Check if content exists in working memory"""
        with self.lock:
            return any(item.content == content for item in self.items)

    def __repr__(self) -> str:
        """String representation"""
        return f"WorkingMemory({len(self.items)}/{self.max_capacity} items)"