"""
Trigger system for IFTTT-style workflow automation

Supports various trigger types:
- Webhook triggers
- Schedule triggers  
- Event triggers
- Manual triggers
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

from core.database import TriggerType

logger = logging.getLogger(__name__)

class TriggerResult:
    """Result of trigger evaluation"""
    
    def __init__(self, triggered: bool, data: Dict[str, Any] = None, metadata: Dict[str, Any] = None):
        self.triggered = triggered
        self.data = data or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()

class BaseTrigger(ABC):
    """Base class for all triggers"""
    
    def __init__(self, trigger_type: str):
        self.trigger_type = trigger_type
        self.is_active = False
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize the trigger with configuration"""
        pass
    
    @abstractmethod
    async def check(self, context: Dict[str, Any] = None) -> TriggerResult:
        """Check if trigger conditions are met"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """Clean up trigger resources"""
        pass
    
    def get_info(self) -> Dict[str, Any]:
        """Get trigger information"""
        return {
            "type": self.trigger_type,
            "is_active": self.is_active
        }

class WebhookTrigger(BaseTrigger):
    """Webhook-based trigger"""
    
    def __init__(self):
        super().__init__(TriggerType.WEBHOOK.value)
        self.endpoint_id: Optional[str] = None
        self.secret_token: Optional[str] = None
        self.allowed_methods: List[str] = ["POST"]
        self.content_types: List[str] = ["application/json"]
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize webhook trigger"""
        try:
            self.endpoint_id = config.get("endpoint_id")
            self.secret_token = config.get("secret_token")
            self.allowed_methods = config.get("allowed_methods", ["POST"])
            self.content_types = config.get("content_types", ["application/json"])
            
            self.is_active = True
            logger.info(f"Webhook trigger initialized with endpoint: {self.endpoint_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize webhook trigger: {e}")
            return False
    
    async def check(self, context: Dict[str, Any] = None) -> TriggerResult:
        """Check webhook trigger (called by webhook handler)"""
        if not context:
            return TriggerResult(False)
        
        # Validate request method
        method = context.get("method", "POST")
        if method not in self.allowed_methods:
            return TriggerResult(False, metadata={"error": f"Method {method} not allowed"})
        
        # Validate content type
        content_type = context.get("content_type", "")
        if not any(ct in content_type for ct in self.content_types):
            return TriggerResult(False, metadata={"error": f"Content type {content_type} not allowed"})
        
        # Verify secret token if configured
        if self.secret_token:
            provided_token = context.get("headers", {}).get("x-webhook-token")
            if provided_token != self.secret_token:
                return TriggerResult(False, metadata={"error": "Invalid webhook token"})
        
        # Extract webhook data
        webhook_data = context.get("data", {})
        
        return TriggerResult(
            triggered=True,
            data={
                "webhook_data": webhook_data,
                "headers": context.get("headers", {}),
                "method": method,
                "endpoint_id": self.endpoint_id
            },
            metadata={
                "trigger_type": "webhook",
                "endpoint_id": self.endpoint_id
            }
        )
    
    async def cleanup(self):
        """Clean up webhook trigger"""
        self.is_active = False

class ScheduleTrigger(BaseTrigger):
    """Schedule-based trigger using cron expressions"""
    
    def __init__(self):
        super().__init__(TriggerType.SCHEDULE.value)
        self.cron_expression: Optional[str] = None
        self.timezone: str = "UTC"
        self.next_run: Optional[datetime] = None
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize schedule trigger"""
        try:
            self.cron_expression = config.get("cron_expression")
            self.timezone = config.get("timezone", "UTC")
            
            if not self.cron_expression:
                raise ValueError("cron_expression is required for schedule trigger")
            
            # Calculate next run time
            self._calculate_next_run()
            
            self.is_active = True
            logger.info(f"Schedule trigger initialized with cron: {self.cron_expression}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize schedule trigger: {e}")
            return False
    
    async def check(self, context: Dict[str, Any] = None) -> TriggerResult:
        """Check if schedule trigger should fire"""
        if not self.is_active or not self.next_run:
            return TriggerResult(False)
        
        current_time = datetime.utcnow()
        
        if current_time >= self.next_run:
            # Trigger should fire
            self._calculate_next_run()  # Calculate next run time
            
            return TriggerResult(
                triggered=True,
                data={
                    "scheduled_time": self.next_run.isoformat(),
                    "actual_time": current_time.isoformat(),
                    "cron_expression": self.cron_expression
                },
                metadata={
                    "trigger_type": "schedule",
                    "cron_expression": self.cron_expression
                }
            )
        
        return TriggerResult(False)
    
    def _calculate_next_run(self):
        """Calculate next run time based on cron expression"""
        try:
            from croniter import croniter
            
            cron = croniter(self.cron_expression, datetime.utcnow())
            self.next_run = cron.get_next(datetime)
            
        except ImportError:
            logger.error("croniter package not available for schedule triggers")
            self.next_run = None
        except Exception as e:
            logger.error(f"Failed to calculate next run time: {e}")
            self.next_run = None
    
    async def cleanup(self):
        """Clean up schedule trigger"""
        self.is_active = False

class EventTrigger(BaseTrigger):
    """Event-based trigger for system events"""
    
    def __init__(self):
        super().__init__(TriggerType.EVENT.value)
        self.event_types: List[str] = []
        self.event_filters: Dict[str, Any] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize event trigger"""
        try:
            self.event_types = config.get("event_types", [])
            self.event_filters = config.get("filters", {})
            
            if not self.event_types:
                raise ValueError("event_types is required for event trigger")
            
            self.is_active = True
            logger.info(f"Event trigger initialized for events: {self.event_types}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize event trigger: {e}")
            return False
    
    async def check(self, context: Dict[str, Any] = None) -> TriggerResult:
        """Check if event trigger should fire"""
        if not self.is_active:
            return TriggerResult(False)
        
        # Check for events in queue
        try:
            event_data = self.event_queue.get_nowait()
            
            # Apply filters if configured
            if self._matches_filters(event_data):
                return TriggerResult(
                    triggered=True,
                    data=event_data,
                    metadata={
                        "trigger_type": "event",
                        "event_types": self.event_types
                    }
                )
            
        except asyncio.QueueEmpty:
            pass
        
        return TriggerResult(False)
    
    def _matches_filters(self, event_data: Dict[str, Any]) -> bool:
        """Check if event matches configured filters"""
        if not self.event_filters:
            return True
        
        for field, expected_value in self.event_filters.items():
            if field not in event_data or event_data[field] != expected_value:
                return False
        
        return True
    
    async def emit_event(self, event_data: Dict[str, Any]):
        """Emit an event to this trigger"""
        if self.is_active and event_data.get("type") in self.event_types:
            await self.event_queue.put(event_data)
    
    async def cleanup(self):
        """Clean up event trigger"""
        self.is_active = False
        
        # Clear event queue
        while not self.event_queue.empty():
            try:
                self.event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

class ManualTrigger(BaseTrigger):
    """Manual trigger for user-initiated workflows"""
    
    def __init__(self):
        super().__init__(TriggerType.MANUAL.value)
        self.trigger_requested = False
        self.trigger_data: Dict[str, Any] = {}
        
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize manual trigger"""
        try:
            # Manual triggers don't need much configuration
            self.is_active = True
            logger.info("Manual trigger initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize manual trigger: {e}")
            return False
    
    async def check(self, context: Dict[str, Any] = None) -> TriggerResult:
        """Check if manual trigger was activated"""
        if not self.is_active:
            return TriggerResult(False)
        
        if self.trigger_requested:
            # Reset trigger state
            self.trigger_requested = False
            trigger_data = self.trigger_data.copy()
            self.trigger_data = {}
            
            return TriggerResult(
                triggered=True,
                data=trigger_data,
                metadata={
                    "trigger_type": "manual"
                }
            )
        
        return TriggerResult(False)
    
    async def activate(self, data: Dict[str, Any] = None):
        """Manually activate the trigger"""
        if self.is_active:
            self.trigger_requested = True
            self.trigger_data = data or {}
    
    async def cleanup(self):
        """Clean up manual trigger"""
        self.is_active = False
        self.trigger_requested = False
        self.trigger_data = {}

class TriggerRegistry:
    """Registry for managing all trigger types"""
    
    def __init__(self):
        self.triggers: Dict[str, type] = {}
        self.active_triggers: Dict[str, BaseTrigger] = {}
        
    async def initialize(self):
        """Initialize trigger registry with built-in triggers"""
        
        # Register built-in triggers
        self.register_trigger("webhook", WebhookTrigger)
        self.register_trigger("schedule", ScheduleTrigger)
        self.register_trigger("event", EventTrigger)
        self.register_trigger("manual", ManualTrigger)
        
        logger.info(f"Trigger registry initialized with {len(self.triggers)} trigger types")
    
    def register_trigger(self, trigger_type: str, trigger_class: type):
        """Register a new trigger type"""
        if not issubclass(trigger_class, BaseTrigger):
            raise ValueError(f"Trigger class must inherit from BaseTrigger")
        
        self.triggers[trigger_type] = trigger_class
        logger.debug(f"Registered trigger type: {trigger_type}")
    
    async def create_trigger(self, trigger_type: str, config: Dict[str, Any]) -> Optional[BaseTrigger]:
        """Create and initialize a trigger instance"""
        
        if trigger_type not in self.triggers:
            logger.error(f"Unknown trigger type: {trigger_type}")
            return None
        
        try:
            trigger_class = self.triggers[trigger_type]
            trigger = trigger_class()
            
            if await trigger.initialize(config):
                trigger_id = f"{trigger_type}_{len(self.active_triggers)}"
                self.active_triggers[trigger_id] = trigger
                return trigger
            else:
                logger.error(f"Failed to initialize trigger: {trigger_type}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating trigger {trigger_type}: {e}")
            return None
    
    def get_trigger(self, trigger_id: str) -> Optional[BaseTrigger]:
        """Get an active trigger by ID"""
        return self.active_triggers.get(trigger_id)
    
    async def remove_trigger(self, trigger_id: str) -> bool:
        """Remove and cleanup a trigger"""
        
        if trigger_id in self.active_triggers:
            trigger = self.active_triggers[trigger_id]
            await trigger.cleanup()
            del self.active_triggers[trigger_id]
            return True
        
        return False
    
    async def check_all_triggers(self, context: Dict[str, Any] = None) -> List[TriggerResult]:
        """Check all active triggers"""
        
        results = []
        for trigger_id, trigger in self.active_triggers.items():
            try:
                result = await trigger.check(context)
                if result.triggered:
                    result.metadata["trigger_id"] = trigger_id
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Error checking trigger {trigger_id}: {e}")
        
        return results
    
    def get_trigger_types(self) -> List[str]:
        """Get list of available trigger types"""
        return list(self.triggers.keys())
    
    def get_active_triggers(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active triggers"""
        return {
            trigger_id: trigger.get_info()
            for trigger_id, trigger in self.active_triggers.items()
        }
    
    async def cleanup(self):
        """Clean up all triggers"""
        
        for trigger_id, trigger in list(self.active_triggers.items()):
            await trigger.cleanup()
        
        self.active_triggers.clear()
        logger.info("All triggers cleaned up")