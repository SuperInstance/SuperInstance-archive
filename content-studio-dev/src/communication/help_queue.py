# src/communication/help_queue.py

import asyncio
from typing import Dict, Any, List
from datetime import datetime


class HelpQueue:
    """Queue for bot help requests"""

    def __init__(self):
        self.queue: List[Dict[str, Any]] = []
        self.lock = asyncio.Lock()
        self.resolved: List[Dict[str, Any]] = []

    async def add(self, help_request: Dict[str, Any]):
        """Add help request to queue"""
        async with self.lock:
            help_request['queued_at'] = datetime.now().isoformat()
            help_request['status'] = 'pending'
            self.queue.append(help_request)

    async def get(self) -> Dict[str, Any]:
        """Get next help request"""
        async with self.lock:
            if self.queue:
                request = self.queue.pop(0)
                request['status'] = 'processing'
                return request
        return None

    def is_empty(self) -> bool:
        """Check if queue is empty"""
        return len(self.queue) == 0

    async def resolve(self, request_id: str, resolution: Dict[str, Any]):
        """Mark help request as resolved"""
        async with self.lock:
            for req in self.queue:
                if req['task_id'] == request_id:
                    req['status'] = 'resolved'
                    req['resolution'] = resolution
                    req['resolved_at'] = datetime.now().isoformat()
                    self.resolved.append(req)
                    self.queue.remove(req)
                    break
