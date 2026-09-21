"""
Auto-Scaling System for Dynamic Workloads
Handles automatic scaling with special support for game night events
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
from enum import Enum
import json
import math

from core.models import (
    EC2Instance, User, ScalingEvent, GameNightEvent, EventType,
    InstanceType, InstanceState, CreateInstanceRequest,
    current_timestamp, generate_id
)

class ScalingAction(str, Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"

class ScalingTrigger(str, Enum):
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    NETWORK_UTILIZATION = "network_utilization"
    CUSTOM_METRIC = "custom_metric"
    SCHEDULED_EVENT = "scheduled_event"
    MANUAL = "manual"

class AutoScaler:
    """Automatic scaling system with game night support"""
    
    def __init__(self, config: Dict[str, Any], database_manager, ec2_provisioner):
        self.config = config
        self.db = database_manager
        self.provisioner = ec2_provisioner
        self.logger = logging.getLogger(__name__)
        
        # Scaling configuration
        self.scaling_config = config.get('scaling', {})
        self.game_night_config = self.scaling_config.get('game_night', {})
        
        # Scaling state
        self.scaling_active = False
        self.scaling_task = None
        self.cooldown_periods = {}  # Track cooldown per user
        self.active_scaling_operations = {}  # Track ongoing scaling
        
        # Game night events
        self.active_game_nights = {}
        self.scheduled_events = []
        
    async def start_auto_scaling(self):
        """Start the auto-scaling system"""
        if self.scaling_active:
            return
            
        self.scaling_active = True
        
        # Start main scaling loop
        self.scaling_task = asyncio.create_task(self._scaling_loop())
        
        # Start game night monitoring
        asyncio.create_task(self._game_night_monitor())
        
        # Load scheduled events
        await self._load_scheduled_events()
        
        self.logger.info("Auto-scaling system started")
    
    async def stop_auto_scaling(self):
        """Stop the auto-scaling system"""
        self.scaling_active = False
        if self.scaling_task:
            self.scaling_task.cancel()
            try:
                await self.scaling_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Auto-scaling system stopped")
    
    async def _scaling_loop(self):
        """Main scaling evaluation loop"""
        scaling_interval = self.scaling_config.get('scaling_interval_seconds', 60)
        
        while self.scaling_active:
            try:
                await self._evaluate_scaling_decisions()
                await asyncio.sleep(scaling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Scaling loop error: {e}")
                await asyncio.sleep(scaling_interval)
    
    async def _evaluate_scaling_decisions(self):
        """Evaluate scaling decisions for all users"""
        try:
            # Get all active users with running instances
            active_users = await self.db.get_active_users_with_instances()
            
            scaling_tasks = []
            for user in active_users:
                task = self._evaluate_user_scaling(user.user_id)
                scaling_tasks.append(task)
            
            if scaling_tasks:
                await asyncio.gather(*scaling_tasks, return_exceptions=True)
                
        except Exception as e:
            self.logger.error(f"Error evaluating scaling decisions: {e}")
    
    async def _evaluate_user_scaling(self, user_id: str):
        """Evaluate scaling for a specific user"""
        try:
            # Check if user is in cooldown
            if self._is_in_cooldown(user_id):
                return
            
            # Get user's instances and metrics
            user_instances = await self.db.get_user_instances(user_id)
            running_instances = [i for i in user_instances if i.state == InstanceState.RUNNING]
            
            if not running_instances:
                return
            
            # Get scaling configuration for user (or default)
            scaling_config = await self._get_user_scaling_config(user_id)
            
            # Calculate current metrics
            avg_metrics = await self._calculate_average_metrics(running_instances)
            
            # Check for game night events
            game_night_scaling = await self._check_game_night_scaling(user_id)
            
            # Determine scaling action
            scaling_decision = await self._make_scaling_decision(
                user_id, running_instances, avg_metrics, scaling_config, game_night_scaling
            )
            
            if scaling_decision['action'] != ScalingAction.NO_ACTION:
                await self._execute_scaling_action(user_id, scaling_decision)
                
        except Exception as e:
            self.logger.error(f"Error evaluating scaling for user {user_id}: {e}")
    
    def _is_in_cooldown(self, user_id: str) -> bool:
        """Check if user is in scaling cooldown period"""
        if user_id not in self.cooldown_periods:
            return False
            
        cooldown_end = self.cooldown_periods[user_id]
        return current_timestamp() < cooldown_end
    
    async def _get_user_scaling_config(self, user_id: str) -> Dict[str, Any]:
        """Get scaling configuration for user"""
        # Try to get user-specific config from database
        user_config = await self.db.get_user_scaling_config(user_id)
        
        if user_config:
            return user_config
        
        # Return default configuration
        return {
            'min_instances': self.scaling_config.get('min_instances', 1),
            'max_instances': self.scaling_config.get('max_instances', 10),
            'target_cpu_utilization': self.scaling_config.get('cpu_scale_up_threshold', 70),
            'target_memory_utilization': self.scaling_config.get('memory_scale_up_threshold', 80),
            'scale_up_cooldown': self.scaling_config.get('cooldown_period_seconds', 300),
            'scale_down_cooldown': self.scaling_config.get('cooldown_period_seconds', 300)
        }
    
    async def _calculate_average_metrics(self, instances: List[EC2Instance]) -> Dict[str, float]:
        """Calculate average metrics across instances"""
        if not instances:
            return {}
        
        total_cpu = 0.0
        total_memory = 0.0
        total_network = 0.0
        metrics_count = 0
        
        # Get metrics from usage tracker
        from billing.usage_tracker import UsageTracker
        usage_tracker = UsageTracker(self.config, self.db)
        
        for instance in instances:
            metrics = await usage_tracker.get_real_time_metrics(instance.instance_id)
            if metrics:
                total_cpu += metrics.get('cpu_utilization', 0)
                total_memory += metrics.get('memory_utilization', 0)
                total_network += metrics.get('network_out_bytes', 0) / 1000000  # Convert to MB
                metrics_count += 1
        
        if metrics_count == 0:
            return {}
        
        return {
            'avg_cpu_utilization': total_cpu / metrics_count,
            'avg_memory_utilization': total_memory / metrics_count,
            'avg_network_mb': total_network / metrics_count,
            'instance_count': len(instances)
        }
    
    async def _check_game_night_scaling(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Check if user has active game night events requiring scaling"""
        try:
            current_time = current_timestamp()
            
            # Check active game night events
            active_events = await self.db.get_active_game_night_events(user_id)
            
            for event in active_events:
                # Check if event should be starting soon (pre-scale)
                pre_scale_time = event.start_time - timedelta(
                    minutes=self.game_night_config.get('pre_scale_minutes', 30)
                )
                
                # Check if event should be ending soon (post-scale)
                post_scale_time = event.end_time + timedelta(
                    minutes=self.game_night_config.get('post_scale_minutes', 60)
                )
                
                if pre_scale_time <= current_time <= event.end_time:
                    # Scale up for the event
                    return {
                        'event_id': event.event_id,
                        'event_type': 'game_night_scale_up',
                        'scale_multiplier': event.scale_multiplier,
                        'target_instances': event.pre_scale_instances,
                        'priority': 'high'
                    }
                elif event.end_time < current_time <= post_scale_time:
                    # Scale down after the event
                    return {
                        'event_id': event.event_id,
                        'event_type': 'game_night_scale_down',
                        'scale_multiplier': 1.0,  # Return to normal
                        'target_instances': 1,  # Minimum instances
                        'priority': 'medium'
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking game night scaling for user {user_id}: {e}")
            return None
    
    async def _make_scaling_decision(self, user_id: str, instances: List[EC2Instance],
                                   metrics: Dict[str, float], scaling_config: Dict[str, Any],
                                   game_night_scaling: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Make scaling decision based on metrics and configuration"""
        current_instance_count = len(instances)
        min_instances = scaling_config['min_instances']
        max_instances = scaling_config['max_instances']
        
        # Default decision
        decision = {
            'action': ScalingAction.NO_ACTION,
            'reason': 'no_scaling_needed',
            'current_instances': current_instance_count,
            'target_instances': current_instance_count,
            'trigger': ScalingTrigger.CPU_UTILIZATION,
            'metrics': metrics
        }
        
        # Game night scaling takes priority
        if game_night_scaling:
            target_instances = game_night_scaling['target_instances']
            
            if target_instances > current_instance_count and current_instance_count < max_instances:
                decision.update({
                    'action': ScalingAction.SCALE_UP,
                    'reason': f"game_night_event_{game_night_scaling['event_type']}",
                    'target_instances': min(target_instances, max_instances),
                    'trigger': ScalingTrigger.SCHEDULED_EVENT,
                    'instances_to_add': min(target_instances - current_instance_count, max_instances - current_instance_count)
                })
            elif target_instances < current_instance_count and current_instance_count > min_instances:
                decision.update({
                    'action': ScalingAction.SCALE_DOWN,
                    'reason': f"game_night_event_{game_night_scaling['event_type']}",
                    'target_instances': max(target_instances, min_instances),
                    'trigger': ScalingTrigger.SCHEDULED_EVENT,
                    'instances_to_remove': min(current_instance_count - target_instances, current_instance_count - min_instances)
                })
            
            return decision
        
        # Regular metric-based scaling
        if not metrics:
            return decision
        
        avg_cpu = metrics.get('avg_cpu_utilization', 0)
        avg_memory = metrics.get('avg_memory_utilization', 0)
        
        target_cpu = scaling_config['target_cpu_utilization']
        target_memory = scaling_config['target_memory_utilization']
        
        # Scale up conditions
        if (avg_cpu > target_cpu or avg_memory > target_memory) and current_instance_count < max_instances:
            # Calculate how many instances to add
            cpu_ratio = avg_cpu / target_cpu if target_cpu > 0 else 1
            memory_ratio = avg_memory / target_memory if target_memory > 0 else 1
            max_ratio = max(cpu_ratio, memory_ratio)
            
            # Calculate target instances based on load
            target_instances = min(
                math.ceil(current_instance_count * max_ratio),
                max_instances
            )
            
            instances_to_add = target_instances - current_instance_count
            
            if instances_to_add > 0:
                decision.update({
                    'action': ScalingAction.SCALE_UP,
                    'reason': f'high_utilization_cpu_{avg_cpu:.1f}%_memory_{avg_memory:.1f}%',
                    'target_instances': target_instances,
                    'instances_to_add': instances_to_add,
                    'trigger': ScalingTrigger.CPU_UTILIZATION if cpu_ratio > memory_ratio else ScalingTrigger.MEMORY_UTILIZATION
                })
        
        # Scale down conditions
        elif avg_cpu < (target_cpu * 0.3) and avg_memory < (target_memory * 0.3) and current_instance_count > min_instances:
            # Conservative scale down - only if utilization is very low
            target_instances = max(
                math.ceil(current_instance_count * 0.7),  # Remove 30% of instances
                min_instances
            )
            
            instances_to_remove = current_instance_count - target_instances
            
            if instances_to_remove > 0:
                decision.update({
                    'action': ScalingAction.SCALE_DOWN,
                    'reason': f'low_utilization_cpu_{avg_cpu:.1f}%_memory_{avg_memory:.1f}%',
                    'target_instances': target_instances,
                    'instances_to_remove': instances_to_remove,
                    'trigger': ScalingTrigger.CPU_UTILIZATION
                })
        
        return decision
    
    async def _execute_scaling_action(self, user_id: str, decision: Dict[str, Any]):
        """Execute the scaling action"""
        try:
            action = decision['action']
            current_instances = decision['current_instances']
            
            if action == ScalingAction.SCALE_UP:
                await self._scale_up(user_id, decision)
            elif action == ScalingAction.SCALE_DOWN:
                await self._scale_down(user_id, decision)
            
            # Record scaling event
            scaling_event = ScalingEvent(
                event_id=generate_id("scale"),
                user_id=user_id,
                event_type=EventType.CUSTOM,  # Could be more specific
                trigger_metric=decision['trigger'].value,
                trigger_value=decision['metrics'].get('avg_cpu_utilization', 0),
                scaling_action=action.value,
                instances_before=current_instances,
                instances_after=decision['target_instances'],
                timestamp=current_timestamp(),
                success=True  # Will be updated if operation fails
            )
            
            await self.db.create_scaling_event(scaling_event)
            
            # Set cooldown period
            cooldown_seconds = decision.get('cooldown_seconds', 
                                          self.scaling_config.get('cooldown_period_seconds', 300))
            self.cooldown_periods[user_id] = current_timestamp() + timedelta(seconds=cooldown_seconds)
            
            self.logger.info(
                f"Executed {action.value} for user {user_id}: "
                f"{current_instances} -> {decision['target_instances']} instances"
            )
            
        except Exception as e:
            self.logger.error(f"Error executing scaling action for user {user_id}: {e}")
            
            # Record failed scaling event
            scaling_event = ScalingEvent(
                event_id=generate_id("scale"),
                user_id=user_id,
                event_type=EventType.CUSTOM,
                trigger_metric=decision['trigger'].value,
                trigger_value=decision['metrics'].get('avg_cpu_utilization', 0),
                scaling_action=decision['action'].value,
                instances_before=decision['current_instances'],
                instances_after=decision['current_instances'],  # No change
                timestamp=current_timestamp(),
                success=False,
                error_message=str(e)
            )
            
            await self.db.create_scaling_event(scaling_event)
    
    async def _scale_up(self, user_id: str, decision: Dict[str, Any]):
        """Scale up instances for user"""
        instances_to_add = decision['instances_to_add']
        
        # Get user info
        user = await self.db.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Get user's existing instances to determine instance type and configuration
        existing_instances = await self.db.get_user_instances(user_id)
        running_instances = [i for i in existing_instances if i.state == InstanceState.RUNNING]
        
        if running_instances:
            # Use the same instance type as existing instances
            template_instance = running_instances[0]
            instance_type = template_instance.instance_type
            # Could also copy other configuration like security groups, etc.
        else:
            # Default instance type
            instance_type = InstanceType.T3_MEDIUM
        
        # Determine if this is for game night (use game-optimized instances)
        if 'game_night' in decision.get('reason', ''):
            if instance_type == InstanceType.C5_4XLARGE:
                instance_type = InstanceType.C5_4XLARGE_GAME
            elif instance_type == InstanceType.C5_9XLARGE:
                instance_type = InstanceType.C5_9XLARGE_GAME
        
        # Launch new instances
        launch_tasks = []
        for i in range(instances_to_add):
            request = CreateInstanceRequest(
                user_id=user_id,
                instance_type=instance_type,
                image_id=self.config['aws']['default_image_id'],
                tags={
                    'AutoScaled': 'true',
                    'ScalingReason': decision['reason'],
                    'ScalingTimestamp': current_timestamp().isoformat()
                }
            )
            
            task = self.provisioner.provision_instance(request)
            launch_tasks.append(task)
        
        # Wait for all instances to launch
        results = await asyncio.gather(*launch_tasks, return_exceptions=True)
        
        successful_launches = []
        failed_launches = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_launches.append(str(result))
            else:
                successful_launches.append(result.instance_id)
        
        self.logger.info(
            f"Scale up for user {user_id}: "
            f"Launched {len(successful_launches)}/{instances_to_add} instances"
        )
        
        if failed_launches:
            self.logger.error(f"Failed to launch {len(failed_launches)} instances: {failed_launches}")
    
    async def _scale_down(self, user_id: str, decision: Dict[str, Any]):
        """Scale down instances for user"""
        instances_to_remove = decision['instances_to_remove']
        
        # Get user's running instances
        user_instances = await self.db.get_user_instances(user_id)
        running_instances = [i for i in user_instances if i.state == InstanceState.RUNNING]
        
        if len(running_instances) <= instances_to_remove:
            self.logger.warning(f"Cannot remove {instances_to_remove} instances, only {len(running_instances)} running")
            return
        
        # Select instances to terminate (oldest first, or least utilized)
        instances_to_terminate = await self._select_instances_to_terminate(
            running_instances, instances_to_remove
        )
        
        # Terminate selected instances
        termination_tasks = []
        for instance in instances_to_terminate:
            task = self.provisioner.terminate_instance(user_id, instance.instance_id)
            termination_tasks.append(task)
        
        # Wait for all terminations to complete
        results = await asyncio.gather(*termination_tasks, return_exceptions=True)
        
        successful_terminations = sum(1 for result in results if result is True)
        
        self.logger.info(
            f"Scale down for user {user_id}: "
            f"Terminated {successful_terminations}/{instances_to_remove} instances"
        )
    
    async def _select_instances_to_terminate(self, instances: List[EC2Instance], 
                                           count: int) -> List[EC2Instance]:
        """Select which instances to terminate during scale down"""
        if count >= len(instances):
            return instances
        
        # Strategy: Terminate instances with lowest utilization first
        # Get utilization for each instance
        instance_utilization = []
        
        from billing.usage_tracker import UsageTracker
        usage_tracker = UsageTracker(self.config, self.db)
        
        for instance in instances:
            metrics = await usage_tracker.get_real_time_metrics(instance.instance_id)
            if metrics:
                utilization = (metrics.get('cpu_utilization', 0) + 
                             metrics.get('memory_utilization', 0)) / 2
            else:
                utilization = 0
            
            instance_utilization.append((instance, utilization))
        
        # Sort by utilization (lowest first)
        instance_utilization.sort(key=lambda x: x[1])
        
        # Return the lowest utilized instances
        return [instance for instance, _ in instance_utilization[:count]]
    
    async def schedule_game_night(self, event: GameNightEvent) -> bool:
        """Schedule a game night event"""
        try:
            # Calculate pre-scale instances based on expected load
            base_instances = await self._calculate_base_instances(event.user_id)
            event.pre_scale_instances = max(
                int(base_instances * event.scale_multiplier),
                1
            )
            
            # Save to database
            await self.db.create_game_night_event(event)
            
            self.logger.info(
                f"Scheduled game night '{event.name}' for user {event.user_id}: "
                f"{event.start_time} - {event.end_time} "
                f"(scale to {event.pre_scale_instances} instances)"
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error scheduling game night event: {e}")
            return False
    
    async def _calculate_base_instances(self, user_id: str) -> int:
        """Calculate base instance count for user"""
        user_instances = await self.db.get_user_instances(user_id)
        running_instances = [i for i in user_instances if i.state == InstanceState.RUNNING]
        return max(len(running_instances), 1)
    
    async def _game_night_monitor(self):
        """Monitor and activate game night events"""
        while self.scaling_active:
            try:
                current_time = current_timestamp()
                
                # Check for events that should be activated
                upcoming_events = await self.db.get_upcoming_game_night_events(
                    current_time + timedelta(hours=1)  # Look ahead 1 hour
                )
                
                for event in upcoming_events:
                    if not event.active:
                        # Activate event
                        event.active = True
                        await self.db.update_game_night_event(event)
                        self.active_game_nights[event.event_id] = event
                        
                        self.logger.info(f"Activated game night event: {event.name}")
                
                # Check for events that should be deactivated
                expired_events = []
                for event_id, event in self.active_game_nights.items():
                    if current_time > event.end_time + timedelta(
                        minutes=self.game_night_config.get('post_scale_minutes', 60)
                    ):
                        expired_events.append(event_id)
                
                for event_id in expired_events:
                    event = self.active_game_nights.pop(event_id)
                    event.active = False
                    await self.db.update_game_night_event(event)
                    self.logger.info(f"Deactivated game night event: {event.name}")
                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Game night monitor error: {e}")
                await asyncio.sleep(300)
    
    async def _load_scheduled_events(self):
        """Load recurring scheduled events from configuration"""
        scheduled_events = self.game_night_config.get('scheduled_events', {})
        
        for event_name, event_config in scheduled_events.items():
            # Parse cron pattern and create future events
            # This is simplified - in production, use a proper cron parser
            self.logger.info(f"Loaded scheduled event: {event_name}")
    
    async def get_scaling_status(self, user_id: str) -> Dict[str, Any]:
        """Get scaling status for a user"""
        try:
            # Get current instances
            user_instances = await self.db.get_user_instances(user_id)
            running_instances = [i for i in user_instances if i.state == InstanceState.RUNNING]
            
            # Get scaling configuration
            scaling_config = await self._get_user_scaling_config(user_id)
            
            # Get recent scaling events
            recent_events = await self.db.get_recent_scaling_events(user_id, hours=24)
            
            # Get active game night events
            active_game_nights = await self.db.get_active_game_night_events(user_id)
            
            # Check if in cooldown
            in_cooldown = self._is_in_cooldown(user_id)
            cooldown_remaining = 0
            if in_cooldown and user_id in self.cooldown_periods:
                cooldown_remaining = int((self.cooldown_periods[user_id] - current_timestamp()).total_seconds())
            
            return {
                'user_id': user_id,
                'scaling_enabled': self.scaling_active,
                'current_instances': len(running_instances),
                'configuration': scaling_config,
                'in_cooldown': in_cooldown,
                'cooldown_remaining_seconds': cooldown_remaining,
                'active_game_nights': len(active_game_nights),
                'recent_scaling_events': [
                    {
                        'event_id': event.event_id,
                        'action': event.scaling_action,
                        'instances_before': event.instances_before,
                        'instances_after': event.instances_after,
                        'timestamp': event.timestamp.isoformat(),
                        'success': event.success
                    }
                    for event in recent_events[-5:]  # Last 5 events
                ],
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting scaling status for user {user_id}: {e}")
            return {
                'user_id': user_id,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check for auto-scaler"""
        try:
            scaling_healthy = self.scaling_active and (
                self.scaling_task and not self.scaling_task.done()
            )
            
            # Count active operations
            active_operations = len(self.active_scaling_operations)
            active_cooldowns = len(self.cooldown_periods)
            active_game_nights = len(self.active_game_nights)
            
            return {
                'service': 'auto_scaler',
                'healthy': scaling_healthy,
                'scaling_loop_active': scaling_healthy,
                'active_scaling_operations': active_operations,
                'users_in_cooldown': active_cooldowns,
                'active_game_nights': active_game_nights,
                'scaling_interval_seconds': self.scaling_config.get('scaling_interval_seconds', 60),
                'timestamp': current_timestamp().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Auto-scaler health check failed: {e}")
            return {
                'service': 'auto_scaler',
                'healthy': False,
                'error': str(e),
                'timestamp': current_timestamp().isoformat()
            }