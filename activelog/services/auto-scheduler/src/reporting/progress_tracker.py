import asyncio
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict, deque
import statistics
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProgressEntry:
    timestamp: datetime
    component: str
    metric: str
    value: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceMetrics:
    avg_task_completion_time: float
    task_success_rate: float
    bot_efficiency_score: float
    system_utilization: float
    backup_success_rate: float
    storage_growth_rate: float

@dataclass
class CostMetrics:
    total_bot_hours: float
    cost_per_hour: float
    total_cost: float
    cost_by_task_type: Dict[str, float]
    efficiency_savings: float

class ProgressTracker:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.db_path = Path(config.get('db_path', '/home/activeloguser/activelog/services/auto-scheduler/data/progress.db'))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory caches for performance
        self.recent_entries = deque(maxlen=1000)
        self.minute_cache = {}
        self.hourly_cache = {}
        self.daily_cache = {}
        
        # Component registry
        self.registered_components = {}
        self.component_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        # Reporting configuration
        self.report_retention_days = config.get('report_retention_days', 90)
        self.cost_per_bot_hour = config.get('cost_per_bot_hour', 0.50)
        
        # Analytics state
        self.performance_history = deque(maxlen=100)
        self.cost_history = deque(maxlen=100)
        
        # Initialize database
        asyncio.create_task(self._init_database())
    
    async def _init_database(self):
        """Initialize SQLite database for progress tracking"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Progress entries table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS progress_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    component TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    value TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    avg_task_completion_time REAL,
                    task_success_rate REAL,
                    bot_efficiency_score REAL,
                    system_utilization REAL,
                    backup_success_rate REAL,
                    storage_growth_rate REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Cost tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cost_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_bot_hours REAL,
                    cost_per_hour REAL,
                    total_cost REAL,
                    cost_by_task_type TEXT,
                    efficiency_savings REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_timestamp ON progress_entries(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_component ON progress_entries(component)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_reports_type ON reports(report_type)')
            
            conn.commit()
            conn.close()
            
            logger.info("Progress tracking database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def register_component(self, name: str, component: Any):
        """Register a component for progress tracking"""
        self.registered_components[name] = component
        logger.info(f"Registered component: {name}")
    
    def add_callback(self, component: str, callback: Callable):
        """Add a callback for component updates"""
        self.component_callbacks[component].append(callback)
    
    async def record_entry(self, component: str, metric: str, value: Any, 
                          metadata: Optional[Dict[str, Any]] = None):
        """Record a progress entry"""
        entry = ProgressEntry(
            timestamp=datetime.now(),
            component=component,
            metric=metric,
            value=value,
            metadata=metadata or {}
        )
        
        # Add to recent entries cache
        self.recent_entries.append(entry)
        
        # Store in database
        await self._store_entry(entry)
        
        # Trigger callbacks
        for callback in self.component_callbacks.get(component, []):
            try:
                await callback(entry)
            except Exception as e:
                logger.error(f"Error in callback for {component}: {e}")
    
    async def _store_entry(self, entry: ProgressEntry):
        """Store entry in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO progress_entries 
                (timestamp, component, metric, value, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                entry.timestamp.isoformat(),
                entry.component,
                entry.metric,
                json.dumps(entry.value) if not isinstance(entry.value, (str, int, float)) else str(entry.value),
                json.dumps(entry.metadata)
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing progress entry: {e}")
    
    async def update_progress(self, status: Dict[str, Any]):
        """Update progress with comprehensive status"""
        timestamp = datetime.now()
        
        # Record bot status
        if 'bots' in status:
            bot_data = status['bots']
            await self.record_entry('bots', 'total_count', bot_data['total'])
            await self.record_entry('bots', 'active_count', bot_data['active'])
            await self.record_entry('bots', 'busy_count', bot_data['busy'])
            
            # Record individual bot metrics
            for bot in bot_data.get('details', []):
                await self.record_entry('bot', 'used_hours', bot['used_hours'], 
                                       {'bot_id': bot['id'], 'bot_name': bot['name']})
                await self.record_entry('bot', 'available_hours', bot['available_hours'],
                                       {'bot_id': bot['id'], 'bot_name': bot['name']})
                await self.record_entry('bot', 'performance', bot['performance'],
                                       {'bot_id': bot['id'], 'bot_name': bot['name']})
        
        # Record task status
        if 'tasks' in status:
            task_data = status['tasks']
            await self.record_entry('tasks', 'queued', task_data['queued'])
            await self.record_entry('tasks', 'running', task_data['running'])
            await self.record_entry('tasks', 'completed', task_data['completed'])
            await self.record_entry('tasks', 'failed', task_data['failed'])
            await self.record_entry('tasks', 'throttled', task_data['throttled'])
        
        # Record system metrics
        await self.record_entry('system', 'time_multiplier', status.get('time_multiplier', 1.0))
        await self.record_entry('system', 'in_maintenance', status.get('in_maintenance', False))
        
        # Update analytics
        await self._update_analytics(status, timestamp)
    
    async def _update_analytics(self, status: Dict[str, Any], timestamp: datetime):
        """Update performance and cost analytics"""
        try:
            # Calculate performance metrics
            perf_metrics = await self._calculate_performance_metrics(status)
            self.performance_history.append((timestamp, perf_metrics))
            
            # Calculate cost metrics
            cost_metrics = await self._calculate_cost_metrics(status)
            self.cost_history.append((timestamp, cost_metrics))
            
            # Store in database
            await self._store_performance_metrics(timestamp, perf_metrics)
            await self._store_cost_metrics(timestamp, cost_metrics)
            
        except Exception as e:
            logger.error(f"Error updating analytics: {e}")
    
    async def _calculate_performance_metrics(self, status: Dict[str, Any]) -> PerformanceMetrics:
        """Calculate current performance metrics"""
        try:
            # Get recent task completion data
            recent_tasks = await self._get_recent_entries('tasks', hours=24)
            
            # Average task completion time
            completion_times = []
            for entry in recent_tasks:
                if entry.metric == 'completion_time':
                    completion_times.append(float(entry.value))
            
            avg_completion_time = statistics.mean(completion_times) if completion_times else 0.0
            
            # Task success rate
            completed = sum(1 for e in recent_tasks if e.metric == 'completed' and float(e.value) > 0)
            failed = sum(1 for e in recent_tasks if e.metric == 'failed' and float(e.value) > 0)
            total_tasks = completed + failed
            success_rate = (completed / total_tasks) if total_tasks > 0 else 1.0
            
            # Bot efficiency score (average of all bot performance scores)
            bot_performances = []
            if 'bots' in status and 'details' in status['bots']:
                for bot in status['bots']['details']:
                    bot_performances.append(bot.get('performance', 1.0))
            
            avg_bot_efficiency = statistics.mean(bot_performances) if bot_performances else 1.0
            
            # System utilization (busy bots / total active bots)
            total_bots = status.get('bots', {}).get('active', 1)
            busy_bots = status.get('bots', {}).get('busy', 0)
            utilization = busy_bots / total_bots if total_bots > 0 else 0.0
            
            # Backup success rate
            backup_entries = await self._get_recent_entries('backup', hours=168)  # 1 week
            backup_completed = sum(1 for e in backup_entries if e.metric == 'completed')
            backup_failed = sum(1 for e in backup_entries if e.metric == 'failed')
            backup_total = backup_completed + backup_failed
            backup_success_rate = (backup_completed / backup_total) if backup_total > 0 else 1.0
            
            # Storage growth rate (placeholder)
            storage_growth_rate = 0.05  # 5% per month default
            
            return PerformanceMetrics(
                avg_task_completion_time=avg_completion_time,
                task_success_rate=success_rate,
                bot_efficiency_score=avg_bot_efficiency,
                system_utilization=utilization,
                backup_success_rate=backup_success_rate,
                storage_growth_rate=storage_growth_rate
            )
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return PerformanceMetrics(0, 0, 0, 0, 0, 0)
    
    async def _calculate_cost_metrics(self, status: Dict[str, Any]) -> CostMetrics:
        """Calculate current cost metrics"""
        try:
            # Total bot hours used today
            total_bot_hours = 0.0
            cost_by_task_type = defaultdict(float)
            
            if 'bots' in status and 'details' in status['bots']:
                for bot in status['bots']['details']:
                    used_hours = bot.get('used_hours', 0.0)
                    total_bot_hours += used_hours
            
            # Calculate costs
            total_cost = total_bot_hours * self.cost_per_bot_hour
            
            # Efficiency savings (based on time multiplier and bot performance)
            time_multiplier = status.get('time_multiplier', 1.0)
            avg_performance = statistics.mean([
                bot.get('performance', 1.0) 
                for bot in status.get('bots', {}).get('details', [])
            ]) if status.get('bots', {}).get('details') else 1.0
            
            # Savings from night acceleration and good performance
            base_cost = total_bot_hours * self.cost_per_bot_hour
            efficiency_factor = (time_multiplier * avg_performance)
            efficiency_savings = base_cost * (efficiency_factor - 1.0) / efficiency_factor
            
            return CostMetrics(
                total_bot_hours=total_bot_hours,
                cost_per_hour=self.cost_per_bot_hour,
                total_cost=total_cost,
                cost_by_task_type=dict(cost_by_task_type),
                efficiency_savings=max(0, efficiency_savings)
            )
            
        except Exception as e:
            logger.error(f"Error calculating cost metrics: {e}")
            return CostMetrics(0, 0, 0, {}, 0)
    
    async def _store_performance_metrics(self, timestamp: datetime, metrics: PerformanceMetrics):
        """Store performance metrics in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO performance_metrics 
                (timestamp, avg_task_completion_time, task_success_rate, 
                 bot_efficiency_score, system_utilization, backup_success_rate, 
                 storage_growth_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                metrics.avg_task_completion_time,
                metrics.task_success_rate,
                metrics.bot_efficiency_score,
                metrics.system_utilization,
                metrics.backup_success_rate,
                metrics.storage_growth_rate
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing performance metrics: {e}")
    
    async def _store_cost_metrics(self, timestamp: datetime, metrics: CostMetrics):
        """Store cost metrics in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO cost_metrics 
                (timestamp, total_bot_hours, cost_per_hour, total_cost, 
                 cost_by_task_type, efficiency_savings)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                timestamp.isoformat(),
                metrics.total_bot_hours,
                metrics.cost_per_hour,
                metrics.total_cost,
                json.dumps(metrics.cost_by_task_type),
                metrics.efficiency_savings
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing cost metrics: {e}")
    
    async def _get_recent_entries(self, component: str, hours: int = 1) -> List[ProgressEntry]:
        """Get recent entries for a component"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT timestamp, component, metric, value, metadata
                FROM progress_entries
                WHERE component = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            ''', (component, cutoff_time.isoformat()))
            
            rows = cursor.fetchall()
            conn.close()
            
            entries = []
            for row in rows:
                try:
                    value = json.loads(row[3])
                except (json.JSONDecodeError, TypeError):
                    value = row[3]
                
                try:
                    metadata = json.loads(row[4]) if row[4] else {}
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
                
                entries.append(ProgressEntry(
                    timestamp=datetime.fromisoformat(row[0]),
                    component=row[1],
                    metric=row[2],
                    value=value,
                    metadata=metadata
                ))
            
            return entries
            
        except Exception as e:
            logger.error(f"Error getting recent entries: {e}")
            return []
    
    async def generate_minute_update(self) -> Dict[str, Any]:
        """Generate comprehensive minute-by-minute progress update with real-time monitoring"""
        timestamp = datetime.now()
        
        # Get latest status from each component
        latest_status = {}
        component_health = {}
        
        for name, component in self.registered_components.items():
            try:
                if hasattr(component, 'get_status_summary'):
                    status = await component.get_status_summary()
                    latest_status[name] = status
                elif hasattr(component, 'get_status'):
                    status = await component.get_status()
                    latest_status[name] = status
                else:
                    status = {'active': True}
                    latest_status[name] = status
                
                # Assess component health
                component_health[name] = self._assess_component_health(name, status)
                
            except Exception as e:
                logger.error(f"Error getting status from {name}: {e}")
                component_health[name] = {
                    'status': 'error',
                    'message': str(e),
                    'last_successful_update': None
                }
        
        # Get real-time metrics
        real_time_metrics = await self._get_real_time_metrics()
        
        # Create enriched minute update
        update = {
            'timestamp': timestamp.isoformat(),
            'type': 'minute_update',
            'status': latest_status,
            'component_health': component_health,
            'real_time_metrics': real_time_metrics,
            'performance': self.performance_history[-1][1].__dict__ if self.performance_history else {},
            'cost': self.cost_history[-1][1].__dict__ if self.cost_history else {},
            'alerts': await self._check_for_alerts(),
            'trends': await self._calculate_minute_trends()
        }
        
        # Cache and return
        self.minute_cache[timestamp.minute] = update
        
        # Log critical updates
        if any(h['status'] == 'critical' for h in component_health.values()):
            logger.warning(f"Critical component health detected at {timestamp}")
        
        return update
    
    def _assess_component_health(self, name: str, status: Dict[str, Any]) -> Dict[str, Any]:
        """Assess the health status of a component"""
        health = {
            'status': 'healthy',
            'message': 'Component operating normally',
            'last_check': datetime.now().isoformat()
        }
        
        try:
            if name == 'bot_manager':
                total_bots = status.get('bots', {}).get('total', 0)
                active_bots = status.get('bots', {}).get('active', 0)
                
                if total_bots == 0:
                    health['status'] = 'critical'
                    health['message'] = 'No bots available'
                elif active_bots / total_bots < 0.5:
                    health['status'] = 'warning'
                    health['message'] = f'Only {active_bots}/{total_bots} bots active'
                
            elif name == 'backup_manager':
                running_backups = status.get('running_backups', 0)
                if running_backups > 3:
                    health['status'] = 'warning'
                    health['message'] = f'{running_backups} backups running simultaneously'
                
                # Check for failed backups
                by_status = status.get('by_status', {})
                failed_count = by_status.get('failed', 0)
                total_count = status.get('total_backups', 1)
                
                if failed_count / total_count > 0.1:  # More than 10% failure rate
                    health['status'] = 'critical'
                    health['message'] = f'High backup failure rate: {failed_count}/{total_count}'
            
            elif name == 'scheduler':
                if not status.get('scheduler', {}).get('running', False):
                    health['status'] = 'critical'
                    health['message'] = 'Scheduler not running'
        
        except Exception as e:
            health['status'] = 'error'
            health['message'] = f'Health check error: {e}'
        
        return health
    
    async def _get_real_time_metrics(self) -> Dict[str, Any]:
        """Get real-time performance metrics"""
        current_time = datetime.now()
        
        # Get recent entries for real-time calculation
        recent_entries = list(self.recent_entries)
        
        metrics = {
            'timestamp': current_time.isoformat(),
            'entries_per_minute': len([e for e in recent_entries if (current_time - e.timestamp).seconds < 60]),
            'active_components': len(self.registered_components),
            'cache_hit_ratio': self._calculate_cache_hit_ratio(),
            'memory_usage_mb': self._estimate_memory_usage(),
            'database_size_mb': self._get_database_size_mb()
        }
        
        # Calculate throughput metrics
        recent_tasks = [e for e in recent_entries if e.component == 'tasks' and (current_time - e.timestamp).seconds < 300]  # Last 5 minutes
        completed_tasks = len([e for e in recent_tasks if e.metric == 'completed'])
        
        metrics['task_throughput_per_minute'] = completed_tasks / 5.0 if recent_tasks else 0
        
        return metrics
    
    def _calculate_cache_hit_ratio(self) -> float:
        """Calculate cache hit ratio (placeholder)"""
        # In a real implementation, this would track cache hits vs misses
        return 0.85  # 85% hit ratio
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        # Rough estimation based on cached data
        base_size = 10  # Base service memory
        cache_size = (len(self.minute_cache) * 0.1 + 
                     len(self.hourly_cache) * 0.5 + 
                     len(self.daily_cache) * 2.0)
        history_size = (len(self.performance_history) * 0.01 + 
                       len(self.cost_history) * 0.01)
        
        return base_size + cache_size + history_size
    
    def _get_database_size_mb(self) -> float:
        """Get database file size in MB"""
        try:
            if self.db_path.exists():
                size_bytes = self.db_path.stat().st_size
                return size_bytes / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    async def _check_for_alerts(self) -> List[Dict[str, Any]]:
        """Check for system alerts based on current metrics"""
        alerts = []
        
        if self.performance_history:
            latest_perf = self.performance_history[-1][1]
            
            # Critical alerts
            if latest_perf.task_success_rate < 0.8:
                alerts.append({
                    'level': 'critical',
                    'component': 'tasks',
                    'message': f'Task success rate critically low: {latest_perf.task_success_rate:.1%}',
                    'timestamp': datetime.now().isoformat()
                })
            
            if latest_perf.system_utilization > 0.95:
                alerts.append({
                    'level': 'warning',
                    'component': 'system',
                    'message': f'System utilization very high: {latest_perf.system_utilization:.1%}',
                    'timestamp': datetime.now().isoformat()
                })
            
            if latest_perf.backup_success_rate < 0.9:
                alerts.append({
                    'level': 'warning',
                    'component': 'backup',
                    'message': f'Backup success rate low: {latest_perf.backup_success_rate:.1%}',
                    'timestamp': datetime.now().isoformat()
                })
        
        # Check database size
        db_size = self._get_database_size_mb()
        if db_size > 100:  # 100MB threshold
            alerts.append({
                'level': 'info',
                'component': 'storage',
                'message': f'Database size large: {db_size:.1f}MB',
                'timestamp': datetime.now().isoformat()
            })
        
        return alerts
    
    async def _calculate_minute_trends(self) -> Dict[str, Any]:
        """Calculate minute-to-minute trends"""
        trends = {}
        
        if len(self.performance_history) >= 2:
            current = self.performance_history[-1][1]
            previous = self.performance_history[-2][1]
            
            trends['performance'] = {
                'task_success_rate_trend': current.task_success_rate - previous.task_success_rate,
                'efficiency_trend': current.bot_efficiency_score - previous.bot_efficiency_score,
                'utilization_trend': current.system_utilization - previous.system_utilization
            }
        
        if len(self.cost_history) >= 2:
            current_cost = self.cost_history[-1][1]
            previous_cost = self.cost_history[-2][1]
            
            trends['cost'] = {
                'total_cost_trend': current_cost.total_cost - previous_cost.total_cost,
                'efficiency_savings_trend': current_cost.efficiency_savings - previous_cost.efficiency_savings,
                'hourly_rate_trend': current_cost.total_bot_hours - previous_cost.total_bot_hours
            }
        
        return trends
    
    async def generate_hourly_summary(self) -> Dict[str, Any]:
        """Generate hourly summary report"""
        timestamp = datetime.now()
        hour_start = timestamp.replace(minute=0, second=0, microsecond=0)
        
        # Get hourly aggregated data
        hourly_entries = await self._get_recent_entries('', hours=1)  # All components
        
        # Aggregate by component and metric
        aggregates = defaultdict(lambda: defaultdict(list))
        for entry in hourly_entries:
            if isinstance(entry.value, (int, float)):
                aggregates[entry.component][entry.metric].append(entry.value)
        
        # Calculate statistics
        summary = {
            'timestamp': timestamp.isoformat(),
            'period': 'hourly',
            'period_start': hour_start.isoformat(),
            'components': {}
        }
        
        for component, metrics in aggregates.items():
            summary['components'][component] = {}
            for metric, values in metrics.items():
                if values:
                    summary['components'][component][metric] = {
                        'count': len(values),
                        'min': min(values),
                        'max': max(values),
                        'avg': statistics.mean(values),
                        'sum': sum(values)
                    }
        
        # Add performance trends
        if len(self.performance_history) > 1:
            recent_perf = self.performance_history[-1][1]
            prev_perf = self.performance_history[-2][1]
            
            summary['performance_trends'] = {
                'task_success_rate_change': recent_perf.task_success_rate - prev_perf.task_success_rate,
                'efficiency_change': recent_perf.bot_efficiency_score - prev_perf.bot_efficiency_score,
                'utilization_change': recent_perf.system_utilization - prev_perf.system_utilization
            }
        
        self.hourly_cache[timestamp.hour] = summary
        return summary
    
    async def generate_daily_report(self) -> Dict[str, Any]:
        """Generate comprehensive daily report"""
        timestamp = datetime.now()
        day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Get daily performance metrics
        daily_entries = await self._get_recent_entries('', hours=24)
        
        # Calculate daily statistics
        tasks_completed = sum(1 for e in daily_entries if e.component == 'tasks' and e.metric == 'completed')
        tasks_failed = sum(1 for e in daily_entries if e.component == 'tasks' and e.metric == 'failed')
        
        bot_hours_used = sum(
            float(e.value) for e in daily_entries 
            if e.component == 'bot' and e.metric == 'used_hours'
        )
        
        # Get latest performance and cost metrics
        latest_performance = self.performance_history[-1][1] if self.performance_history else None
        latest_cost = self.cost_history[-1][1] if self.cost_history else None
        
        report = {
            'timestamp': timestamp.isoformat(),
            'report_date': day_start.date().isoformat(),
            'type': 'daily_report',
            
            # Task summary
            'task_summary': {
                'completed': tasks_completed,
                'failed': tasks_failed,
                'success_rate': tasks_completed / (tasks_completed + tasks_failed) if (tasks_completed + tasks_failed) > 0 else 0,
                'total_processed': tasks_completed + tasks_failed
            },
            
            # Resource utilization
            'resource_utilization': {
                'total_bot_hours': bot_hours_used,
                'avg_utilization': latest_performance.system_utilization if latest_performance else 0,
                'efficiency_score': latest_performance.bot_efficiency_score if latest_performance else 0
            },
            
            # Cost analysis
            'cost_analysis': {
                'total_cost': latest_cost.total_cost if latest_cost else 0,
                'cost_per_task': (latest_cost.total_cost / (tasks_completed + tasks_failed)) if latest_cost and (tasks_completed + tasks_failed) > 0 else 0,
                'efficiency_savings': latest_cost.efficiency_savings if latest_cost else 0
            },
            
            # System health
            'system_health': {
                'backup_success_rate': latest_performance.backup_success_rate if latest_performance else 0,
                'avg_task_completion_time': latest_performance.avg_task_completion_time if latest_performance else 0,
                'storage_growth': latest_performance.storage_growth_rate if latest_performance else 0
            }
        }
        
        # Store report
        await self._store_report('daily', timestamp, report)
        
        self.daily_cache[timestamp.day] = report
        return report
    
    async def _store_report(self, report_type: str, timestamp: datetime, content: Dict[str, Any]):
        """Store generated report in database"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO reports (report_type, timestamp, content)
                VALUES (?, ?, ?)
            ''', (report_type, timestamp.isoformat(), json.dumps(content)))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error storing report: {e}")
    
    async def get_recommendations(self) -> List[Dict[str, Any]]:
        """Generate intelligent recommendations based on analytics"""
        recommendations = []
        
        if not self.performance_history:
            return recommendations
        
        latest_perf = self.performance_history[-1][1]
        latest_cost = self.cost_history[-1][1] if self.cost_history else None
        
        # Performance recommendations
        if latest_perf.task_success_rate < 0.9:
            recommendations.append({
                'type': 'performance',
                'priority': 'high',
                'title': 'Low Task Success Rate',
                'description': f'Task success rate is {latest_perf.task_success_rate:.1%}, below optimal 90%',
                'action': 'Review failed tasks and adjust bot configurations'
            })
        
        if latest_perf.system_utilization < 0.3:
            recommendations.append({
                'type': 'efficiency',
                'priority': 'medium',
                'title': 'Low System Utilization',
                'description': f'System utilization is {latest_perf.system_utilization:.1%}, consider more tasks',
                'action': 'Schedule additional tasks or reduce bot count'
            })
        
        if latest_perf.bot_efficiency_score < 0.8:
            recommendations.append({
                'type': 'performance',
                'priority': 'medium',
                'title': 'Bot Performance Below Average',
                'description': f'Average bot efficiency is {latest_perf.bot_efficiency_score:.2f}',
                'action': 'Review bot performance and retrain underperforming bots'
            })
        
        # Cost recommendations
        if latest_cost and latest_cost.total_cost > 50.0:  # $50 daily threshold
            recommendations.append({
                'type': 'cost',
                'priority': 'medium',
                'title': 'High Daily Costs',
                'description': f'Daily cost is ${latest_cost.total_cost:.2f}',
                'action': 'Optimize task scheduling or reduce bot hours'
            })
        
        # Backup recommendations
        if latest_perf.backup_success_rate < 0.95:
            recommendations.append({
                'type': 'reliability',
                'priority': 'high',
                'title': 'Backup Success Rate Low',
                'description': f'Backup success rate is {latest_perf.backup_success_rate:.1%}',
                'action': 'Investigate backup failures and fix issues'
            })
        
        return recommendations
    
    async def get_status(self) -> Dict[str, Any]:
        """Get progress tracker status"""
        return {
            'timestamp': datetime.now().isoformat(),
            'registered_components': list(self.registered_components.keys()),
            'recent_entries_count': len(self.recent_entries),
            'performance_history_count': len(self.performance_history),
            'cost_history_count': len(self.cost_history),
            'cache_sizes': {
                'minute': len(self.minute_cache),
                'hourly': len(self.hourly_cache),
                'daily': len(self.daily_cache)
            },
            'latest_performance': self.performance_history[-1][1].__dict__ if self.performance_history else None,
            'latest_cost': self.cost_history[-1][1].__dict__ if self.cost_history else None,
            'recommendations_count': len(await self.get_recommendations())
        }
    
    async def cleanup_old_data(self):
        """Cleanup old progress data based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.report_retention_days)
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Clean up old progress entries
            cursor.execute('''
                DELETE FROM progress_entries 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            # Clean up old reports
            cursor.execute('''
                DELETE FROM reports 
                WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            logger.info(f"Cleaned up {deleted_count} old progress records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old data: {e}")