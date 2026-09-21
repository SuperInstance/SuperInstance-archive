import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import json
import sqlite3
from pathlib import Path
import numpy as np
from collections import defaultdict, deque
import psutil
import time

logger = logging.getLogger(__name__)

class ScalingAction(Enum):
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"

class ScalingPolicy(Enum):
    REACTIVE = "reactive"
    PREDICTIVE = "predictive"
    SCHEDULED = "scheduled"
    HYBRID = "hybrid"

@dataclass
class ScalingMetrics:
    cpu_utilization: float
    memory_utilization: float
    queue_length: int
    active_tasks: int
    avg_response_time: float
    throughput: float
    error_rate: float
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ScalingRule:
    metric: str
    threshold_up: float
    threshold_down: float
    duration: int  # seconds
    cooldown: int  # seconds
    scale_up_amount: int
    scale_down_amount: int
    enabled: bool = True
    
class ResourceMonitor:
    """Monitor system resources and performance metrics"""
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_history = deque(maxlen=1000)
        self.running = False
        self._monitor_task = None
        
        # Metrics tracking
        self.current_metrics = None
        self.last_collection = None
    
    async def start(self):
        """Start resource monitoring"""
        try:
            logger.info("Starting Resource Monitor...")
            
            self.running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            
            logger.info("Resource Monitor started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Resource Monitor: {e}")
            raise
    
    async def stop(self):
        """Stop resource monitoring"""
        logger.info("Stopping Resource Monitor...")
        
        self.running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Resource Monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                metrics = await self._collect_metrics()
                
                if metrics:
                    self.current_metrics = metrics
                    self.metrics_history.append(metrics)
                    self.last_collection = datetime.now()
                
                await asyncio.sleep(self.collection_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    async def _collect_metrics(self) -> Optional[ScalingMetrics]:
        """Collect current system metrics"""
        try:
            # System metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Placeholder for application-specific metrics
            # These would be collected from the orchestration system
            queue_length = 0
            active_tasks = 0
            avg_response_time = 0.0
            throughput = 0.0
            error_rate = 0.0
            
            return ScalingMetrics(
                cpu_utilization=cpu_percent,
                memory_utilization=memory_percent,
                queue_length=queue_length,
                active_tasks=active_tasks,
                avg_response_time=avg_response_time,
                throughput=throughput,
                error_rate=error_rate
            )
            
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return None
    
    def get_current_metrics(self) -> Optional[ScalingMetrics]:
        """Get current system metrics"""
        return self.current_metrics
    
    def get_metrics_history(self, minutes: int = 60) -> List[ScalingMetrics]:
        """Get metrics history for specified time period"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff]
    
    def get_average_metrics(self, minutes: int = 15) -> Optional[ScalingMetrics]:
        """Get average metrics over specified time period"""
        recent_metrics = self.get_metrics_history(minutes)
        
        if not recent_metrics:
            return None
        
        return ScalingMetrics(
            cpu_utilization=np.mean([m.cpu_utilization for m in recent_metrics]),
            memory_utilization=np.mean([m.memory_utilization for m in recent_metrics]),
            queue_length=int(np.mean([m.queue_length for m in recent_metrics])),
            active_tasks=int(np.mean([m.active_tasks for m in recent_metrics])),
            avg_response_time=np.mean([m.avg_response_time for m in recent_metrics]),
            throughput=np.mean([m.throughput for m in recent_metrics]),
            error_rate=np.mean([m.error_rate for m in recent_metrics])
        )

class AutoScaler:
    """Intelligent auto-scaling system"""
    
    def __init__(self, db_path: str = "/home/activeloguser/activelog/data/autoscaler.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.resource_monitor = ResourceMonitor()
        self.scaling_policy = ScalingPolicy.HYBRID
        self.running = False
        
        # Scaling configuration
        self.min_instances = 1
        self.max_instances = 10
        self.current_instances = 1
        
        # Scaling rules
        self.scaling_rules = self._default_scaling_rules()
        
        # Cooldown tracking
        self.last_scaling_action = None
        self.last_scaling_time = None
        self.scaling_history = deque(maxlen=1000)
        
        # Callbacks for scaling actions
        self.scale_up_callback: Optional[Callable[[int], Any]] = None
        self.scale_down_callback: Optional[Callable[[int], Any]] = None
        
        self._init_database()
        self._scaler_task = None
    
    def _init_database(self):
        """Initialize auto-scaler database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scaling_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    action TEXT,
                    reason TEXT,
                    instances_before INTEGER,
                    instances_after INTEGER,
                    metrics TEXT,
                    policy TEXT,
                    success BOOLEAN,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scaling_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    cpu_utilization REAL,
                    memory_utilization REAL,
                    queue_length INTEGER,
                    active_tasks INTEGER,
                    avg_response_time REAL,
                    throughput REAL,
                    error_rate REAL,
                    instances INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    
    def _default_scaling_rules(self) -> List[ScalingRule]:
        """Get default scaling rules"""
        return [
            ScalingRule(
                metric="cpu_utilization",
                threshold_up=80.0,
                threshold_down=20.0,
                duration=300,  # 5 minutes
                cooldown=600,  # 10 minutes
                scale_up_amount=1,
                scale_down_amount=1
            ),
            ScalingRule(
                metric="memory_utilization",
                threshold_up=85.0,
                threshold_down=30.0,
                duration=300,
                cooldown=600,
                scale_up_amount=1,
                scale_down_amount=1
            ),
            ScalingRule(
                metric="queue_length",
                threshold_up=20.0,
                threshold_down=5.0,
                duration=180,  # 3 minutes
                cooldown=300,  # 5 minutes
                scale_up_amount=2,
                scale_down_amount=1
            ),
            ScalingRule(
                metric="avg_response_time",
                threshold_up=5000.0,  # 5 seconds
                threshold_down=1000.0,  # 1 second
                duration=300,
                cooldown=600,
                scale_up_amount=1,
                scale_down_amount=1
            )
        ]
    
    async def start(self):
        """Start the auto-scaler"""
        try:
            logger.info("Starting Auto-Scaler...")
            
            await self.resource_monitor.start()
            
            self.running = True
            self._scaler_task = asyncio.create_task(self._scaling_loop())
            
            logger.info("Auto-Scaler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start Auto-Scaler: {e}")
            raise
    
    async def stop(self):
        """Stop the auto-scaler"""
        logger.info("Stopping Auto-Scaler...")
        
        self.running = False
        
        if self._scaler_task:
            self._scaler_task.cancel()
            try:
                await self._scaler_task
            except asyncio.CancelledError:
                pass
        
        await self.resource_monitor.stop()
        
        logger.info("Auto-Scaler stopped")
    
    async def _scaling_loop(self):
        """Main scaling decision loop"""
        while self.running:
            try:
                await self._evaluate_scaling()
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scaling loop: {e}")
                await asyncio.sleep(30)
    
    async def _evaluate_scaling(self):
        """Evaluate whether scaling action is needed"""
        try:
            current_metrics = self.resource_monitor.get_current_metrics()
            if not current_metrics:
                return
            
            # Store metrics
            await self._store_metrics(current_metrics)
            
            # Check if in cooldown period
            if self._in_cooldown():
                return
            
            # Evaluate based on policy
            if self.scaling_policy == ScalingPolicy.REACTIVE:
                action, reason = await self._reactive_scaling(current_metrics)
            elif self.scaling_policy == ScalingPolicy.PREDICTIVE:
                action, reason = await self._predictive_scaling(current_metrics)
            elif self.scaling_policy == ScalingPolicy.SCHEDULED:
                action, reason = await self._scheduled_scaling(current_metrics)
            else:  # HYBRID
                action, reason = await self._hybrid_scaling(current_metrics)
            
            if action != ScalingAction.NO_ACTION:
                await self._execute_scaling_action(action, reason, current_metrics)
                
        except Exception as e:
            logger.error(f"Error evaluating scaling: {e}")
    
    async def _reactive_scaling(self, metrics: ScalingMetrics) -> tuple[ScalingAction, str]:
        """Reactive scaling based on current metrics"""
        # Check each scaling rule
        for rule in self.scaling_rules:
            if not rule.enabled:
                continue
            
            metric_value = getattr(metrics, rule.metric, 0)
            
            # Check for scale up
            if metric_value >= rule.threshold_up:
                if await self._metric_sustained(rule.metric, rule.threshold_up, rule.duration):
                    if self.current_instances < self.max_instances:
                        return ScalingAction.SCALE_UP, f"{rule.metric} ({metric_value:.1f}) exceeded threshold ({rule.threshold_up})"
            
            # Check for scale down
            elif metric_value <= rule.threshold_down:
                if await self._metric_sustained(rule.metric, rule.threshold_down, rule.duration, below=True):
                    if self.current_instances > self.min_instances:
                        return ScalingAction.SCALE_DOWN, f"{rule.metric} ({metric_value:.1f}) below threshold ({rule.threshold_down})"
        
        return ScalingAction.NO_ACTION, "No thresholds exceeded"
    
    async def _predictive_scaling(self, metrics: ScalingMetrics) -> tuple[ScalingAction, str]:
        """Predictive scaling based on trends and patterns"""
        # Get historical data
        history = self.resource_monitor.get_metrics_history(30)  # 30 minutes
        
        if len(history) < 10:
            return await self._reactive_scaling(metrics)
        
        # Analyze trends
        cpu_trend = self._calculate_trend([m.cpu_utilization for m in history[-10:]])
        queue_trend = self._calculate_trend([m.queue_length for m in history[-10:]])
        
        # Predict future load
        predicted_cpu = metrics.cpu_utilization + (cpu_trend * 10)  # 10 minutes ahead
        predicted_queue = metrics.queue_length + (queue_trend * 10)
        
        # Make scaling decision based on predictions
        if predicted_cpu > 85 or predicted_queue > 25:
            if self.current_instances < self.max_instances:
                return ScalingAction.SCALE_UP, f"Predicted overload: CPU {predicted_cpu:.1f}%, Queue {predicted_queue:.0f}"
        
        elif predicted_cpu < 20 and predicted_queue < 3:
            if self.current_instances > self.min_instances:
                return ScalingAction.SCALE_DOWN, f"Predicted underutilization: CPU {predicted_cpu:.1f}%, Queue {predicted_queue:.0f}"
        
        return ScalingAction.NO_ACTION, "No predictive action needed"
    
    async def _scheduled_scaling(self, metrics: ScalingMetrics) -> tuple[ScalingAction, str]:
        """Scheduled scaling based on time patterns"""
        current_hour = datetime.now().hour
        
        # Example: scale up during business hours, scale down at night
        if 9 <= current_hour <= 17:  # Business hours
            if self.current_instances < 3:
                return ScalingAction.SCALE_UP, "Business hours scaling"
        else:  # Off hours
            if self.current_instances > 1:
                return ScalingAction.SCALE_DOWN, "Off hours scaling"
        
        return ScalingAction.NO_ACTION, "No scheduled action needed"
    
    async def _hybrid_scaling(self, metrics: ScalingMetrics) -> tuple[ScalingAction, str]:
        """Hybrid scaling combining reactive and predictive approaches"""
        # First check reactive scaling
        reactive_action, reactive_reason = await self._reactive_scaling(metrics)
        
        if reactive_action != ScalingAction.NO_ACTION:
            return reactive_action, f"Reactive: {reactive_reason}"
        
        # Then check predictive scaling
        predictive_action, predictive_reason = await self._predictive_scaling(metrics)
        
        if predictive_action != ScalingAction.NO_ACTION:
            return predictive_action, f"Predictive: {predictive_reason}"
        
        # Finally check scheduled scaling
        scheduled_action, scheduled_reason = await self._scheduled_scaling(metrics)
        
        if scheduled_action != ScalingAction.NO_ACTION:
            return scheduled_action, f"Scheduled: {scheduled_reason}"
        
        return ScalingAction.NO_ACTION, "No hybrid action needed"
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend (slope) from values"""
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        try:
            coeffs = np.polyfit(x, values, 1)
            return coeffs[0]  # slope
        except:
            return 0.0
    
    async def _metric_sustained(
        self, 
        metric: str, 
        threshold: float, 
        duration: int,
        below: bool = False
    ) -> bool:
        """Check if metric has been above/below threshold for duration"""
        history = self.resource_monitor.get_metrics_history(duration // 60 + 1)
        
        if len(history) < 2:
            return False
        
        cutoff_time = datetime.now() - timedelta(seconds=duration)
        sustained_count = 0
        
        for metrics in reversed(history):
            if metrics.timestamp < cutoff_time:
                break
            
            value = getattr(metrics, metric, 0)
            
            if below:
                if value <= threshold:
                    sustained_count += 1
                else:
                    break
            else:
                if value >= threshold:
                    sustained_count += 1
                else:
                    break
        
        # Need at least 3 consecutive measurements
        return sustained_count >= 3
    
    def _in_cooldown(self) -> bool:
        """Check if we're in a cooldown period"""
        if not self.last_scaling_time:
            return False
        
        # Use shortest cooldown period from active rules
        min_cooldown = min(rule.cooldown for rule in self.scaling_rules if rule.enabled)
        cooldown_end = self.last_scaling_time + timedelta(seconds=min_cooldown)
        
        return datetime.now() < cooldown_end
    
    async def _execute_scaling_action(
        self, 
        action: ScalingAction, 
        reason: str, 
        metrics: ScalingMetrics
    ):
        """Execute the scaling action"""
        try:
            old_instances = self.current_instances
            success = True
            
            if action == ScalingAction.SCALE_UP:
                new_instances = min(self.current_instances + 1, self.max_instances)
                if self.scale_up_callback:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.scale_up_callback, new_instances - self.current_instances
                    )
                self.current_instances = new_instances
                
            elif action == ScalingAction.SCALE_DOWN:
                new_instances = max(self.current_instances - 1, self.min_instances)
                if self.scale_down_callback:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self.scale_down_callback, self.current_instances - new_instances
                    )
                self.current_instances = new_instances
            
            # Record scaling event
            await self._record_scaling_event(action, reason, old_instances, self.current_instances, metrics, success)
            
            self.last_scaling_action = action
            self.last_scaling_time = datetime.now()
            
            logger.info(f"Scaling action executed: {action.value} from {old_instances} to {self.current_instances} instances. Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to execute scaling action: {e}")
            await self._record_scaling_event(action, reason, old_instances, old_instances, metrics, False)
    
    async def _store_metrics(self, metrics: ScalingMetrics):
        """Store metrics to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO scaling_metrics 
                    (timestamp, cpu_utilization, memory_utilization, queue_length,
                     active_tasks, avg_response_time, throughput, error_rate, instances)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp,
                    metrics.cpu_utilization,
                    metrics.memory_utilization,
                    metrics.queue_length,
                    metrics.active_tasks,
                    metrics.avg_response_time,
                    metrics.throughput,
                    metrics.error_rate,
                    self.current_instances
                ))
        except Exception as e:
            logger.error(f"Failed to store metrics: {e}")
    
    async def _record_scaling_event(
        self,
        action: ScalingAction,
        reason: str,
        instances_before: int,
        instances_after: int,
        metrics: ScalingMetrics,
        success: bool
    ):
        """Record scaling event to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO scaling_events 
                    (timestamp, action, reason, instances_before, instances_after,
                     metrics, policy, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    datetime.now(),
                    action.value,
                    reason,
                    instances_before,
                    instances_after,
                    json.dumps({
                        'cpu_utilization': metrics.cpu_utilization,
                        'memory_utilization': metrics.memory_utilization,
                        'queue_length': metrics.queue_length,
                        'active_tasks': metrics.active_tasks
                    }),
                    self.scaling_policy.value,
                    success
                ))
            
            # Add to in-memory history
            self.scaling_history.append({
                'timestamp': datetime.now(),
                'action': action.value,
                'reason': reason,
                'instances_before': instances_before,
                'instances_after': instances_after,
                'success': success
            })
            
        except Exception as e:
            logger.error(f"Failed to record scaling event: {e}")
    
    def set_scaling_callbacks(
        self, 
        scale_up_callback: Callable[[int], Any],
        scale_down_callback: Callable[[int], Any]
    ):
        """Set callbacks for scaling actions"""
        self.scale_up_callback = scale_up_callback
        self.scale_down_callback = scale_down_callback
    
    def set_scaling_policy(self, policy: ScalingPolicy):
        """Change scaling policy"""
        self.scaling_policy = policy
        logger.info(f"Scaling policy changed to: {policy.value}")
    
    def set_instance_limits(self, min_instances: int, max_instances: int):
        """Set instance limits"""
        self.min_instances = max(1, min_instances)
        self.max_instances = max(self.min_instances, max_instances)
        self.current_instances = max(self.min_instances, min(self.current_instances, self.max_instances))
        
        logger.info(f"Instance limits set: {self.min_instances}-{self.max_instances}, current: {self.current_instances}")
    
    def add_scaling_rule(self, rule: ScalingRule):
        """Add or update a scaling rule"""
        # Remove existing rule for same metric
        self.scaling_rules = [r for r in self.scaling_rules if r.metric != rule.metric]
        self.scaling_rules.append(rule)
        
        logger.info(f"Scaling rule added for {rule.metric}: up={rule.threshold_up}, down={rule.threshold_down}")
    
    def get_scaling_status(self) -> Dict[str, Any]:
        """Get current scaling status"""
        current_metrics = self.resource_monitor.get_current_metrics()
        
        return {
            'running': self.running,
            'current_instances': self.current_instances,
            'min_instances': self.min_instances,
            'max_instances': self.max_instances,
            'scaling_policy': self.scaling_policy.value,
            'last_scaling_action': self.last_scaling_action.value if self.last_scaling_action else None,
            'last_scaling_time': self.last_scaling_time.isoformat() if self.last_scaling_time else None,
            'in_cooldown': self._in_cooldown(),
            'current_metrics': {
                'cpu_utilization': current_metrics.cpu_utilization if current_metrics else 0,
                'memory_utilization': current_metrics.memory_utilization if current_metrics else 0,
                'queue_length': current_metrics.queue_length if current_metrics else 0,
                'active_tasks': current_metrics.active_tasks if current_metrics else 0
            } if current_metrics else None,
            'scaling_rules': [
                {
                    'metric': rule.metric,
                    'threshold_up': rule.threshold_up,
                    'threshold_down': rule.threshold_down,
                    'enabled': rule.enabled
                } for rule in self.scaling_rules
            ]
        }
    
    def get_scaling_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get scaling history for specified time period"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            event for event in self.scaling_history 
            if event['timestamp'] >= cutoff
        ]
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for specified time period"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT AVG(cpu_utilization), AVG(memory_utilization),
                           AVG(queue_length), AVG(active_tasks),
                           AVG(avg_response_time), AVG(throughput),
                           AVG(error_rate), AVG(instances)
                    FROM scaling_metrics
                    WHERE timestamp > datetime('now', '-{} hours')
                """.format(hours))
                
                row = cursor.fetchone()
                if row and any(x is not None for x in row):
                    return {
                        'avg_cpu_utilization': row[0] or 0,
                        'avg_memory_utilization': row[1] or 0,
                        'avg_queue_length': row[2] or 0,
                        'avg_active_tasks': row[3] or 0,
                        'avg_response_time': row[4] or 0,
                        'avg_throughput': row[5] or 0,
                        'avg_error_rate': row[6] or 0,
                        'avg_instances': row[7] or 1
                    }
                
        except Exception as e:
            logger.error(f"Failed to get metrics summary: {e}")
        
        return {
            'avg_cpu_utilization': 0,
            'avg_memory_utilization': 0,
            'avg_queue_length': 0,
            'avg_active_tasks': 0,
            'avg_response_time': 0,
            'avg_throughput': 0,
            'avg_error_rate': 0,
            'avg_instances': self.current_instances
        }