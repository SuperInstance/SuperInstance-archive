# src/communication/message_bus.py

import asyncio
from typing import Dict, Any, Callable, List
from collections import defaultdict
from datetime import datetime


class MessageBus:
    """Central message bus for bot communication"""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.bot_queues: Dict[str, asyncio.Queue] = {}
        self.messages: List[Dict[str, Any]] = []

    def subscribe(self, event_type: str, callback: Callable):
        """Subscribe to event type"""
        self.subscribers[event_type].append(callback)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        """Publish event to subscribers"""
        self.messages.append({
            'type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })

        for callback in self.subscribers[event_type]:
            try:
                await callback(data)
            except Exception as e:
                print(f"Error in subscriber: {e}")

    def register_bot(self, bot_id: str):
        """Register a bot's task queue"""
        self.bot_queues[bot_id] = asyncio.Queue()

    async def assign_task(self, bot_id: str, task: Dict[str, Any]):
        """Assign task to specific bot"""
        if bot_id not in self.bot_queues:
            self.register_bot(bot_id)

        await self.bot_queues[bot_id].put(task)
        await self.publish('task_assigned', {
            'bot_id': bot_id,
            'task_id': task['task_id']
        })

    async def get_task_for_bot(self, bot_id: str) -> Dict[str, Any]:
        """Get next task for bot"""
        if bot_id not in self.bot_queues:
            self.register_bot(bot_id)

        try:
            task = await asyncio.wait_for(
                self.bot_queues[bot_id].get(),
                timeout=0.5
            )
            return task
        except asyncio.TimeoutError:
            return None

    async def send_alert(self, alert: Dict[str, Any]):
        """Send system alert"""
        await self.publish('alert', alert)
