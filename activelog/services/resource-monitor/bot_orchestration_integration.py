#!/usr/bin/env python3
"""
Bot Orchestration Integration
Integrates resource monitoring with existing bot orchestration systems
"""

import asyncio
import json
import logging
import aiohttp
import redis.asyncio as redis
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os

from adaptive_bot_throttler import AdaptiveBotThrottler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotOrchestrationIntegrator:
    """Integrates resource monitoring with bot orchestration systems"""
    
    def __init__(self, throttler: AdaptiveBotThrottler):
        self.throttler = throttler
        self.redis_client: Optional[redis.Redis] = None
        self.orchestrator_endpoints = {
            "bot-orchestrator": "http://localhost:8450",
            "bot-scaling-system": "http://localhost:8461",
            "hierarchical-task-system": "http://localhost:8471"
        }
        
        # Integration state
        self.integration_active = False
        self.last_sync = None
        
    async def initialize(self):
        """Initialize integration with orchestration systems"""
        logger.info("🔗 Initializing bot orchestration integration")
        
        # Connect to Redis for pub/sub
        try:
            self.redis_client = redis.from_url("redis://localhost:6379")
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis for orchestration coordination")
            
            # Subscribe to bot events
            asyncio.create_task(self._subscribe_to_bot_events())
            
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to Redis: {e}")
            self.redis_client = None
        
        # Register with orchestration systems
        await self._register_with_orchestrators()
        
        # Start integration loop
        asyncio.create_task(self._integration_loop())
        
        self.integration_active = True
        logger.info("✅ Bot orchestration integration active")
    
    async def _register_with_orchestrators(self):
        """Register this service with bot orchestrators"""
        
        registration_data = {
            "service_name": "resource-monitor",
            "endpoint": "http://localhost:8473",
            "capabilities": [
                "resource_monitoring",
                "bot_throttling", 
                "system_health",
                "performance_optimization"
            ],
            "priority": 8,  # High priority for resource management
            "resource_usage": "low"
        }
        
        for service_name, endpoint in self.orchestrator_endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{endpoint}/services/register",
                        json=registration_data,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"✅ Registered with {service_name}")
                        else:
                            logger.warning(f"⚠️ Failed to register with {service_name}: {response.status}")
            except Exception as e:
                logger.debug(f"Could not register with {service_name}: {e}")
    
    async def _subscribe_to_bot_events(self):
        """Subscribe to bot lifecycle events via Redis"""
        
        if not self.redis_client:
            return
        
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("bot:events", "bot:scaling", "bot:health")
        
        logger.info("👂 Subscribed to bot orchestration events")
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    event_data = json.loads(message["data"])
                    await self._handle_bot_event(event_data)
                except Exception as e:
                    logger.error(f"Error handling bot event: {e}")
    
    async def _handle_bot_event(self, event_data: Dict):
        """Handle incoming bot lifecycle events"""
        
        event_type = event_data.get("type")
        bot_id = event_data.get("bot_id")
        
        logger.debug(f"📨 Received bot event: {event_type} for {bot_id}")
        
        if event_type == "bot_started":
            # A new bot has started, update registry
            await self._handle_bot_started(event_data)
            
        elif event_type == "bot_stopped":
            # Bot has stopped, update registry
            await self._handle_bot_stopped(event_data)
            
        elif event_type == "scaling_request":
            # Orchestrator wants to scale bots
            await self._handle_scaling_request(event_data)
            
        elif event_type == "resource_request":
            # Bot requesting resource information
            await self._handle_resource_request(event_data)
    
    async def _handle_bot_started(self, event_data: Dict):
        """Handle bot started event"""
        
        bot_id = event_data["bot_id"]
        service_name = event_data.get("service_name", "unknown")
        port = event_data.get("port", 0)
        priority = event_data.get("priority", 5)
        resource_usage = event_data.get("resource_usage", "medium")
        
        # Update bot registry
        if bot_id in self.throttler.bot_registry.bots:
            await self.throttler.bot_registry.update_bot_status(bot_id, "active", datetime.now())
            logger.info(f"🟢 Updated bot status: {service_name} active")
        else:
            # Register new bot
            from adaptive_bot_throttler import BotInstance
            bot = BotInstance(
                bot_id=bot_id,
                service_name=service_name,
                port=port,
                priority=priority,
                resource_usage=resource_usage,
                current_status='active',
                last_activity=datetime.now(),
                tasks_completed=0
            )
            await self.throttler.bot_registry.register_bot(bot)
        
        # Check if we need to throttle due to new bot
        await self._evaluate_throttling_after_change()
    
    async def _handle_bot_stopped(self, event_data: Dict):
        """Handle bot stopped event"""
        
        bot_id = event_data["bot_id"]
        service_name = event_data.get("service_name", "unknown")
        
        # Update bot registry
        await self.throttler.bot_registry.update_bot_status(bot_id, "stopped", datetime.now())
        
        # Remove from throttled sets
        self.throttler.paused_bots.discard(bot_id)
        self.throttler.stopped_bots.discard(bot_id)
        
        logger.info(f"🔴 Bot stopped: {service_name}")
    
    async def _handle_scaling_request(self, event_data: Dict):
        """Handle scaling request from orchestrator"""
        
        requested_count = event_data.get("target_bot_count", 3)
        requester = event_data.get("requester", "unknown")
        
        logger.info(f"📈 Scaling request from {requester}: target {requested_count} bots")
        
        # Check current system resources
        recommendation = self.throttler.resource_monitor.analyze_throttle_requirements(requested_count)
        
        # Send response with resource-based recommendation
        response = {
            "approved_bot_count": recommendation.recommended_bot_count,
            "throttle_level": recommendation.throttle_level,
            "reason": recommendation.reason,
            "estimated_safe_count": min(requested_count, recommendation.recommended_bot_count)
        }
        
        if self.redis_client:
            await self.redis_client.publish(
                "resource:scaling_response",
                json.dumps(response)
            )
        
        logger.info(f"📊 Scaling response: approved {response['approved_bot_count']}/{requested_count} bots")
    
    async def _handle_resource_request(self, event_data: Dict):
        """Handle resource information request"""
        
        requester = event_data.get("requester", "unknown")
        request_type = event_data.get("request_type", "summary")
        
        if request_type == "summary":
            resource_data = self.throttler.resource_monitor.get_resource_summary()
        elif request_type == "throttle_status":
            resource_data = self.throttler.get_throttle_status()
        else:
            resource_data = {"error": "Unknown request type"}
        
        # Send response
        if self.redis_client:
            await self.redis_client.publish(
                f"resource:response:{requester}",
                json.dumps(resource_data, default=str)
            )
    
    async def _evaluate_throttling_after_change(self):
        """Evaluate throttling needs after bot count change"""
        
        # Small delay to let system stabilize
        await asyncio.sleep(2)
        
        # Force a throttling evaluation
        current_active = self.throttler.bot_registry.get_active_bot_count()
        recommendation = self.throttler.resource_monitor.analyze_throttle_requirements(current_active)
        
        if recommendation.throttle_level != "none":
            logger.info(f"🚦 Resource pressure detected after bot change: {recommendation.throttle_level}")
            await self.throttler._apply_throttling(recommendation)
    
    async def _integration_loop(self):
        """Main integration loop for ongoing coordination"""
        
        while True:
            try:
                await self._sync_with_orchestrators()
                await self._publish_resource_status()
                await asyncio.sleep(30)  # Sync every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in integration loop: {e}")
                await asyncio.sleep(30)
    
    async def _sync_with_orchestrators(self):
        """Sync state with orchestration systems"""
        
        # Get current throttle status
        throttle_status = self.throttler.get_throttle_status()
        
        # Send status updates to orchestrators
        for service_name, endpoint in self.orchestrator_endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{endpoint}/resource_status",
                        json={
                            "timestamp": datetime.now().isoformat(),
                            "throttle_level": throttle_status["current_throttle_level"],
                            "active_bots": throttle_status["active_bots"],
                            "recommended_max_bots": self._get_recommended_max_bots(),
                            "resource_summary": throttle_status["resource_summary"]
                        },
                        timeout=aiohttp.ClientTimeout(total=3)
                    ) as response:
                        if response.status == 200:
                            logger.debug(f"✅ Synced with {service_name}")
            except Exception as e:
                logger.debug(f"Could not sync with {service_name}: {e}")
        
        self.last_sync = datetime.now()
    
    async def _publish_resource_status(self):
        """Publish current resource status to Redis"""
        
        if not self.redis_client:
            return
        
        status_data = {
            "timestamp": datetime.now().isoformat(),
            "throttle_level": self.throttler.current_throttle_level,
            "active_bots": self.throttler.bot_registry.get_active_bot_count(),
            "resource_summary": self.throttler.resource_monitor.get_resource_summary(),
            "recommended_max_bots": self._get_recommended_max_bots()
        }
        
        await self.redis_client.publish(
            "resource:status",
            json.dumps(status_data, default=str)
        )
    
    def _get_recommended_max_bots(self) -> int:
        """Get recommended maximum bot count based on current resources"""
        
        # Conservative recommendation based on current system state
        current_recommendation = self.throttler.resource_monitor.analyze_throttle_requirements(5)
        
        if current_recommendation.throttle_level == "none":
            return 5  # System can handle full load
        elif current_recommendation.throttle_level == "warning":
            return 3  # Moderate load
        elif current_recommendation.throttle_level == "critical":
            return 2  # High load
        else:  # emergency
            return 1  # Critical load
    
    async def notify_orchestrators_of_throttle_change(self, old_level: str, new_level: str, reason: str):
        """Notify orchestrators of throttle level changes"""
        
        notification = {
            "type": "throttle_change",
            "timestamp": datetime.now().isoformat(),
            "old_level": old_level,
            "new_level": new_level,
            "reason": reason,
            "recommended_action": "adjust_bot_count" if new_level != "none" else "normal_operation"
        }
        
        # Send to Redis if available
        if self.redis_client:
            await self.redis_client.publish("resource:throttle_change", json.dumps(notification))
        
        # Send HTTP notifications to orchestrators
        for service_name, endpoint in self.orchestrator_endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{endpoint}/notifications/throttle_change",
                        json=notification,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.info(f"📢 Notified {service_name} of throttle change")
            except Exception as e:
                logger.debug(f"Could not notify {service_name}: {e}")
    
    async def request_bot_pause_from_orchestrator(self, bot_count: int) -> bool:
        """Request orchestrator to pause specific number of bots"""
        
        request = {
            "type": "pause_request",
            "timestamp": datetime.now().isoformat(),
            "requested_pause_count": bot_count,
            "reason": "resource_pressure",
            "priority_guidance": "pause_lowest_priority_first"
        }
        
        # Try each orchestrator until one responds
        for service_name, endpoint in self.orchestrator_endpoints.items():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{endpoint}/bots/pause_request",
                        json=request,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            paused_count = result.get("paused_count", 0)
                            logger.info(f"✅ {service_name} paused {paused_count} bots")
                            return paused_count >= bot_count
            except Exception as e:
                logger.debug(f"Could not request pause from {service_name}: {e}")
        
        return False
    
    def get_integration_status(self) -> Dict:
        """Get current integration status"""
        
        return {
            "integration_active": self.integration_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "redis_connected": self.redis_client is not None,
            "orchestrator_endpoints": list(self.orchestrator_endpoints.keys()),
            "registered_services": len([ep for ep in self.orchestrator_endpoints.values()]),
            "sync_interval": "30 seconds"
        }

# Integration with existing throttler
class EnhancedAdaptiveBotThrottler(AdaptiveBotThrottler):
    """Enhanced throttler with orchestration integration"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.integration = BotOrchestrationIntegrator(self)
    
    async def initialize(self):
        """Initialize with orchestration integration"""
        await super().initialize()
        await self.integration.initialize()
    
    async def _apply_throttling(self, recommendation):
        """Enhanced throttling with orchestrator coordination"""
        
        old_level = self.current_throttle_level
        
        # Try to coordinate with orchestrators first
        if recommendation.throttle_level in ["warning", "critical"]:
            current_active = self.bot_registry.get_active_bot_count()
            pause_count = current_active - recommendation.recommended_bot_count
            
            if pause_count > 0:
                # Request orchestrator to handle pausing
                success = await self.integration.request_bot_pause_from_orchestrator(pause_count)
                if success:
                    logger.info(f"✅ Orchestrator handled bot pausing ({pause_count} bots)")
                    self.current_throttle_level = recommendation.throttle_level
                    await self.integration.notify_orchestrators_of_throttle_change(
                        old_level, recommendation.throttle_level, recommendation.reason
                    )
                    return
        
        # Fall back to direct throttling
        await super()._apply_throttling(recommendation)
        
        # Notify orchestrators of change
        if old_level != self.current_throttle_level:
            await self.integration.notify_orchestrators_of_throttle_change(
                old_level, self.current_throttle_level, recommendation.reason
            )

# Test the integration
async def main():
    """Test orchestration integration"""
    
    from system_resource_monitor import ThrottleConfig
    
    config = ThrottleConfig(
        cpu_warning_threshold=60.0,
        memory_warning_threshold=70.0
    )
    
    # Use enhanced throttler with integration
    throttler = EnhancedAdaptiveBotThrottler(config)
    await throttler.initialize()
    
    print("🔗 Bot Orchestration Integration Test")
    print("=====================================")
    
    # Run for a bit to see integration in action
    await asyncio.sleep(60)
    
    # Get integration status
    integration_status = throttler.integration.get_integration_status()
    print(f"\n📊 Integration Status:")
    print(json.dumps(integration_status, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())