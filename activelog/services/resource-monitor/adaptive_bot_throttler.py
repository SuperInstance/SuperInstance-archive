#!/usr/bin/env python3
"""
Adaptive Bot Throttler
Automatically adjusts bot activity based on system resource usage
"""

import asyncio
import json
import logging
import aiohttp
import redis.asyncio as redis
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import os
from pathlib import Path

from system_resource_monitor import SystemResourceMonitor, ThrottleConfig, ThrottleRecommendation

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BotInstance:
    """Represents a bot instance"""
    bot_id: str
    service_name: str
    port: int
    priority: int  # 1-10, higher = more important
    resource_usage: str  # 'low', 'medium', 'high'
    current_status: str  # 'active', 'paused', 'stopped'
    last_activity: datetime
    tasks_completed: int

@dataclass
class ThrottleAction:
    """Action taken by throttler"""
    timestamp: datetime
    action_type: str  # 'pause', 'resume', 'stop', 'limit_tasks'
    bot_id: str
    reason: str
    resource_trigger: str
    previous_status: str
    new_status: str

class BotRegistry:
    """Manages registry of bot instances"""
    
    def __init__(self):
        self.bots: Dict[str, BotInstance] = {}
        self.redis_client: Optional[redis.Redis] = None
        
    async def initialize(self):
        """Initialize bot registry"""
        try:
            self.redis_client = redis.from_url("redis://localhost:6379")
            await self.redis_client.ping()
            logger.info("✅ Connected to Redis for bot coordination")
        except Exception as e:
            logger.warning(f"⚠️ Could not connect to Redis: {e}. Using in-memory registry.")
            self.redis_client = None
        
        # Load known bot instances
        await self._discover_bot_instances()
    
    async def _discover_bot_instances(self):
        """Discover running bot instances"""
        
        # Known bot services and their typical configurations
        known_services = [
            {"name": "bot-orchestrator", "port": 8450, "priority": 9, "usage": "medium"},
            {"name": "garbage-collector-bot", "port": 8470, "priority": 3, "usage": "low"},
            {"name": "hierarchical-task-system", "port": 8471, "priority": 7, "usage": "medium"},
            {"name": "smart-task-system", "port": 8463, "priority": 8, "usage": "medium"},
            {"name": "bot-scaling-system", "port": 8461, "priority": 6, "usage": "low"},
            {"name": "learning-engine", "port": 8472, "priority": 5, "usage": "low"},
        ]
        
        for service in known_services:
            bot_id = f"{service['name']}-001"
            
            # Check if service is running
            is_running = await self._check_service_health(service['port'])
            
            bot = BotInstance(
                bot_id=bot_id,
                service_name=service['name'],
                port=service['port'],
                priority=service['priority'],
                resource_usage=service['usage'],
                current_status='active' if is_running else 'stopped',
                last_activity=datetime.now(),
                tasks_completed=0
            )
            
            self.bots[bot_id] = bot
            
            if is_running:
                logger.info(f"🤖 Discovered active bot: {service['name']} on port {service['port']}")
    
    async def _check_service_health(self, port: int) -> bool:
        """Check if a service is running on specified port"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{port}/health", timeout=aiohttp.ClientTimeout(total=2)) as response:
                    return response.status == 200
        except:
            return False
    
    async def register_bot(self, bot: BotInstance):
        """Register a new bot instance"""
        self.bots[bot.bot_id] = bot
        
        if self.redis_client:
            await self.redis_client.hset(
                "bot_registry", 
                bot.bot_id, 
                json.dumps(asdict(bot), default=str)
            )
        
        logger.info(f"📝 Registered bot: {bot.bot_id} ({bot.service_name})")
    
    async def update_bot_status(self, bot_id: str, status: str, last_activity: datetime = None):
        """Update bot status"""
        if bot_id in self.bots:
            self.bots[bot_id].current_status = status
            self.bots[bot_id].last_activity = last_activity or datetime.now()
            
            if self.redis_client:
                await self.redis_client.hset(
                    "bot_registry",
                    bot_id,
                    json.dumps(asdict(self.bots[bot_id]), default=str)
                )
    
    def get_bots_by_priority(self, exclude_stopped: bool = True) -> List[BotInstance]:
        """Get bots sorted by priority (highest first)"""
        bots = list(self.bots.values())
        
        if exclude_stopped:
            bots = [b for b in bots if b.current_status != 'stopped']
        
        return sorted(bots, key=lambda b: b.priority, reverse=True)
    
    def get_active_bot_count(self) -> int:
        """Get count of currently active bots"""
        return len([b for b in self.bots.values() if b.current_status == 'active'])
    
    def get_bots_by_resource_usage(self, usage_level: str) -> List[BotInstance]:
        """Get bots by resource usage level"""
        return [b for b in self.bots.values() if b.resource_usage == usage_level]

class AdaptiveBotThrottler:
    """Main throttler that adjusts bot activity based on system resources"""
    
    def __init__(self, config: ThrottleConfig = None):
        self.config = config or ThrottleConfig()
        self.resource_monitor = SystemResourceMonitor(self.config)
        self.bot_registry = BotRegistry()
        self.throttle_history: List[ThrottleAction] = []
        self.last_throttle_check = datetime.now()
        self.throttle_cooldown = 30  # seconds between throttle actions
        
        # Throttling state
        self.current_throttle_level = "none"
        self.paused_bots: Set[str] = set()
        self.stopped_bots: Set[str] = set()
        
        # Performance tracking
        self.throttle_effectiveness = {}
        
    async def initialize(self):
        """Initialize the throttler"""
        logger.info("🚀 Initializing Adaptive Bot Throttler")
        
        await self.bot_registry.initialize()
        
        # Start resource monitoring in background
        asyncio.create_task(self.resource_monitor.start_monitoring(5))
        
        # Start throttling loop
        asyncio.create_task(self._throttling_loop())
        
        logger.info("✅ Adaptive Bot Throttler initialized")
    
    async def _throttling_loop(self):
        """Main throttling decision loop"""
        while True:
            try:
                await self._evaluate_and_throttle()
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in throttling loop: {e}")
                await asyncio.sleep(10)
    
    async def _evaluate_and_throttle(self):
        """Evaluate system state and apply throttling if needed"""
        
        # Get current bot count and system recommendation
        current_active_bots = self.bot_registry.get_active_bot_count()
        recommendation = self.resource_monitor.analyze_throttle_requirements(current_active_bots)
        
        # Check if we need to take action
        if recommendation.throttle_level != self.current_throttle_level:
            
            # Enforce throttle cooldown to prevent flapping
            time_since_last = (datetime.now() - self.last_throttle_check).total_seconds()
            if time_since_last < self.throttle_cooldown and self.current_throttle_level != "none":
                return
            
            logger.info(f"🚦 Throttle level changed: {self.current_throttle_level} → {recommendation.throttle_level}")
            logger.info(f"📊 {recommendation.metrics_summary}")
            
            await self._apply_throttling(recommendation)
            self.current_throttle_level = recommendation.throttle_level
            self.last_throttle_check = datetime.now()
    
    async def _apply_throttling(self, recommendation: ThrottleRecommendation):
        """Apply the recommended throttling actions"""
        
        current_active = self.bot_registry.get_active_bot_count()
        target_bots = recommendation.recommended_bot_count
        
        logger.info(f"🎯 Applying throttling: {current_active} → {target_bots} active bots")
        
        if recommendation.throttle_level == "none":
            # Resume all paused bots
            await self._resume_bots()
            
        elif recommendation.throttle_level == "warning":
            # Pause low-priority, high-resource bots first
            await self._selective_pause(target_bots, "warning")
            
        elif recommendation.throttle_level == "critical":
            # Pause more bots, keep only essential ones
            await self._selective_pause(target_bots, "critical")
            
        elif recommendation.throttle_level == "emergency":
            # Stop all non-essential bots
            await self._emergency_stop()
        
        # Log the action
        await self._log_throttle_action(recommendation)
    
    async def _selective_pause(self, target_count: int, level: str):
        """Selectively pause bots based on priority and resource usage"""
        
        active_bots = [b for b in self.bot_registry.bots.values() if b.current_status == 'active']
        active_count = len(active_bots)
        
        if active_count <= target_count:
            return  # Already at or below target
        
        # Sort by priority (lowest first) and resource usage (highest first)
        bots_to_consider = sorted(active_bots, key=lambda b: (b.priority, -(['low', 'medium', 'high'].index(b.resource_usage))))
        
        bots_to_pause = active_count - target_count
        
        for i in range(min(bots_to_pause, len(bots_to_consider))):
            bot = bots_to_consider[i]
            
            # Skip critical bots in warning level
            if level == "warning" and bot.priority >= 8:
                continue
            
            await self._pause_bot(bot.bot_id, f"Resource throttling: {level}")
    
    async def _pause_bot(self, bot_id: str, reason: str):
        """Pause a specific bot"""
        
        if bot_id not in self.bot_registry.bots:
            return
        
        bot = self.bot_registry.bots[bot_id]
        
        # Attempt to pause via API
        success = await self._send_bot_command(bot.port, "pause")
        
        if success:
            await self.bot_registry.update_bot_status(bot_id, 'paused')
            self.paused_bots.add(bot_id)
            logger.info(f"⏸️ Paused bot {bot.service_name} ({reason})")
        else:
            logger.warning(f"⚠️ Failed to pause bot {bot.service_name}")
    
    async def _resume_bot(self, bot_id: str):
        """Resume a paused bot"""
        
        if bot_id not in self.bot_registry.bots:
            return
        
        bot = self.bot_registry.bots[bot_id]
        
        # Attempt to resume via API
        success = await self._send_bot_command(bot.port, "resume")
        
        if success:
            await self.bot_registry.update_bot_status(bot_id, 'active')
            self.paused_bots.discard(bot_id)
            logger.info(f"▶️ Resumed bot {bot.service_name}")
        else:
            logger.warning(f"⚠️ Failed to resume bot {bot.service_name}")
    
    async def _resume_bots(self):
        """Resume all paused bots"""
        
        for bot_id in list(self.paused_bots):
            await self._resume_bot(bot_id)
    
    async def _emergency_stop(self):
        """Emergency stop of all non-critical bots"""
        
        active_bots = [b for b in self.bot_registry.bots.values() if b.current_status == 'active']
        
        for bot in active_bots:
            if bot.priority < 9:  # Keep only critical bots (priority 9-10)
                await self._stop_bot(bot.bot_id, "Emergency resource protection")
    
    async def _stop_bot(self, bot_id: str, reason: str):
        """Stop a bot completely"""
        
        if bot_id not in self.bot_registry.bots:
            return
        
        bot = self.bot_registry.bots[bot_id]
        
        # Attempt to stop via API
        success = await self._send_bot_command(bot.port, "stop")
        
        if success:
            await self.bot_registry.update_bot_status(bot_id, 'stopped')
            self.stopped_bots.add(bot_id)
            logger.warning(f"⏹️ Stopped bot {bot.service_name} ({reason})")
        else:
            logger.error(f"❌ Failed to stop bot {bot.service_name}")
    
    async def _send_bot_command(self, port: int, command: str) -> bool:
        """Send command to bot service"""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"http://localhost:{port}/control",
                    json={"action": command},
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.debug(f"Bot command failed: {e}")
            return False
    
    async def _log_throttle_action(self, recommendation: ThrottleRecommendation):
        """Log throttling action for analysis"""
        
        action = ThrottleAction(
            timestamp=datetime.now(),
            action_type=recommendation.throttle_level,
            bot_id="system",
            reason=recommendation.reason,
            resource_trigger=recommendation.metrics_summary,
            previous_status=self.current_throttle_level,
            new_status=recommendation.throttle_level
        )
        
        self.throttle_history.append(action)
        
        # Keep only recent history
        cutoff = datetime.now() - timedelta(hours=24)
        self.throttle_history = [a for a in self.throttle_history if a.timestamp >= cutoff]
    
    def get_throttle_status(self) -> Dict:
        """Get current throttling status"""
        
        active_bots = self.bot_registry.get_active_bot_count()
        resource_summary = self.resource_monitor.get_resource_summary()
        
        return {
            "current_throttle_level": self.current_throttle_level,
            "active_bots": active_bots,
            "paused_bots": len(self.paused_bots),
            "stopped_bots": len(self.stopped_bots),
            "resource_summary": resource_summary,
            "last_throttle_check": self.last_throttle_check.isoformat(),
            "bot_status": {
                bot_id: {
                    "service": bot.service_name,
                    "status": bot.current_status,
                    "priority": bot.priority,
                    "resource_usage": bot.resource_usage
                }
                for bot_id, bot in self.bot_registry.bots.items()
            }
        }
    
    def get_throttle_history(self, hours: int = 24) -> List[Dict]:
        """Get throttling history"""
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_actions = [a for a in self.throttle_history if a.timestamp >= cutoff]
        
        return [
            {
                "timestamp": a.timestamp.isoformat(),
                "action_type": a.action_type,
                "reason": a.reason,
                "resource_trigger": a.resource_trigger,
                "status_change": f"{a.previous_status} → {a.new_status}"
            }
            for a in recent_actions
        ]
    
    async def manual_override(self, bot_id: str, action: str) -> bool:
        """Manual override for bot control"""
        
        if bot_id not in self.bot_registry.bots:
            return False
        
        if action == "pause":
            await self._pause_bot(bot_id, "Manual override")
            return True
        elif action == "resume":
            await self._resume_bot(bot_id)
            return True
        elif action == "stop":
            await self._stop_bot(bot_id, "Manual override")
            return True
        
        return False
    
    def get_performance_metrics(self) -> Dict:
        """Get throttler performance metrics"""
        
        if not self.throttle_history:
            return {"message": "No throttle history available"}
        
        # Count throttle events by type
        event_counts = {}
        for action in self.throttle_history:
            event_counts[action.action_type] = event_counts.get(action.action_type, 0) + 1
        
        # Calculate effectiveness (placeholder - would need more sophisticated metrics)
        total_events = len(self.throttle_history)
        
        return {
            "total_throttle_events": total_events,
            "event_breakdown": event_counts,
            "average_active_bots": sum(1 for b in self.bot_registry.bots.values() if b.current_status == 'active'),
            "uptime_percentage": 95.0,  # Placeholder
            "resource_savings_estimated": "15-30%"  # Placeholder
        }

# Test the throttler
async def main():
    """Test the adaptive bot throttler"""
    
    # Custom config for testing
    config = ThrottleConfig(
        cpu_warning_threshold=60.0,
        cpu_critical_threshold=80.0,
        memory_warning_threshold=70.0,
        memory_critical_threshold=85.0,
        warning_bot_limit=2,
        critical_bot_limit=1,
        emergency_bot_limit=0
    )
    
    throttler = AdaptiveBotThrottler(config)
    await throttler.initialize()
    
    print("🤖 Adaptive Bot Throttler Test")
    print("==============================")
    
    # Wait for initialization
    await asyncio.sleep(5)
    
    # Get status
    status = throttler.get_throttle_status()
    print(f"\n📊 Throttle Status:")
    print(json.dumps(status, indent=2, default=str))
    
    # Simulate running for a bit
    print("\n🔄 Running throttler for 30 seconds...")
    await asyncio.sleep(30)
    
    # Get final status
    final_status = throttler.get_throttle_status()
    history = throttler.get_throttle_history(1)
    
    print(f"\n📈 Final Status:")
    print(json.dumps(final_status, indent=2, default=str))
    
    if history:
        print(f"\n📜 Throttle History:")
        print(json.dumps(history, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())