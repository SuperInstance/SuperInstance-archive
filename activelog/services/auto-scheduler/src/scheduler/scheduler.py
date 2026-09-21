import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .bot_manager import BotManager, Task, TaskPriority, TaskStatus
from ..backup.backup_manager import BackupManager
from ..reporting.progress_tracker import ProgressTracker

logger = logging.getLogger(__name__)

class AutoScheduler:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.bot_manager = BotManager(config.get('bot_manager', {}))
        self.backup_manager = BackupManager(config.get('backup', {}))
        self.progress_tracker = ProgressTracker(config.get('reporting', {}))
        
        self.is_running = False
        self.scheduler_task = None
        self.backup_task = None
        
        # Scheduling intervals
        self.task_check_interval = config.get('task_check_interval', 30)  # seconds
        self.backup_check_interval = config.get('backup_check_interval', 300)  # 5 minutes
        self.report_interval = config.get('report_interval', 60)  # 1 minute
        
        # Setup default maintenance windows
        self._setup_default_maintenance()
        
        # Register for progress tracking
        self.progress_tracker.register_component('scheduler', self)
        self.progress_tracker.register_component('bot_manager', self.bot_manager)
        self.progress_tracker.register_component('backup_manager', self.backup_manager)
    
    def _setup_default_maintenance(self):
        """Setup default maintenance windows"""
        # Sunday 2-4 AM for weekly maintenance
        self.bot_manager.add_maintenance_window(6, "02:00", "04:00", "Weekly System Maintenance")
        
        # Daily 1-2 AM for backup verification
        for day in range(7):
            self.bot_manager.add_maintenance_window(day, "01:00", "02:00", "Backup Verification")
    
    async def start(self):
        """Start the auto-scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        self.is_running = True
        logger.info("Starting auto-scheduler")
        
        # Start all background tasks
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        self.backup_task = asyncio.create_task(self._backup_loop())
        self.reporting_task = asyncio.create_task(self._reporting_loop())
        
        # Schedule initial system tasks
        await self._schedule_system_tasks()
        
        logger.info("Auto-scheduler started successfully")
    
    async def stop(self):
        """Stop the auto-scheduler"""
        if not self.is_running:
            return
        
        self.is_running = False
        logger.info("Stopping auto-scheduler")
        
        # Cancel background tasks
        if self.scheduler_task:
            self.scheduler_task.cancel()
        if self.backup_task:
            self.backup_task.cancel()
        if self.reporting_task:
            self.reporting_task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(
            self.scheduler_task, 
            self.backup_task, 
            self.reporting_task,
            return_exceptions=True
        )
        
        logger.info("Auto-scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduling loop"""
        while self.is_running:
            try:
                await self._process_task_queue()
                await asyncio.sleep(self.task_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(self.task_check_interval)
    
    async def _backup_loop(self):
        """Backup management loop"""
        while self.is_running:
            try:
                await self._check_backup_schedule()
                await asyncio.sleep(self.backup_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in backup loop: {e}")
                await asyncio.sleep(self.backup_check_interval)
    
    async def _reporting_loop(self):
        """Progress reporting loop"""
        while self.is_running:
            try:
                await self._generate_progress_update()
                await asyncio.sleep(self.report_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in reporting loop: {e}")
                await asyncio.sleep(self.report_interval)
    
    async def _process_task_queue(self):
        """Process pending tasks in the queue"""
        # Check for completed tasks first
        completed_tasks = []
        for task_id, task in self.bot_manager.running_tasks.items():
            # Simulate task completion for demo
            if self._should_complete_task(task):
                completed_tasks.append((task_id, True))
        
        for task_id, success in completed_tasks:
            self.bot_manager.complete_task(task_id, success)
        
        # Process new tasks
        max_assignments = 10  # Prevent infinite loops
        assignments = 0
        
        while assignments < max_assignments:
            task = self.bot_manager.get_next_task()
            if not task:
                break
            
            bot_id = self.bot_manager.assign_task_to_bot(task.id)
            if bot_id:
                assignments += 1
                logger.info(f"Assigned task {task.id} to bot {bot_id}")
                
                # Start the task execution
                asyncio.create_task(self._execute_task(task.id))
            else:
                # No available bot, check if we need to throttle
                if task.status == TaskStatus.THROTTLED:
                    logger.info(f"Task {task.id} throttled due to bot limits")
                break
    
    def _should_complete_task(self, task: Task) -> bool:
        """Determine if a running task should be completed"""
        if not task.started_at:
            return False
        
        # Simple completion logic based on estimated duration
        elapsed = (datetime.now() - task.started_at).total_seconds() / 3600
        return elapsed >= task.estimated_duration
    
    async def _execute_task(self, task_id: str):
        """Execute a specific task (placeholder for actual execution)"""
        task = self.bot_manager.running_tasks.get(task_id)
        if not task:
            return
        
        try:
            logger.info(f"Starting execution of task {task_id}")
            
            # Simulate task execution
            await asyncio.sleep(task.estimated_duration * 3600)  # Convert to seconds
            
            # Mark as completed
            self.bot_manager.complete_task(task_id, success=True)
            
        except Exception as e:
            logger.error(f"Task {task_id} failed: {e}")
            self.bot_manager.complete_task(task_id, success=False)
    
    async def _check_backup_schedule(self):
        """Check if any backups need to be scheduled or executed"""
        current_time = datetime.now()
        
        # Check for due backups
        due_backups = await self.backup_manager.get_due_backups(current_time)
        
        for backup_type, backup_config in due_backups.items():
            # Create a backup task
            task_id = f"backup_{backup_type}_{current_time.strftime('%Y%m%d_%H%M%S')}"
            
            task = Task(
                id=task_id,
                name=f"Backup: {backup_type}",
                priority=TaskPriority.HIGH,
                estimated_duration=backup_config.get('estimated_duration', 0.5),
                resource_requirements={'capabilities': ['backup']},
                metadata={'backup_type': backup_type, 'config': backup_config}
            )
            
            self.bot_manager.add_task(task)
            logger.info(f"Scheduled backup task: {task_id}")
    
    async def _generate_progress_update(self):
        """Generate and log progress updates"""
        try:
            # Get system status
            status = self.bot_manager.get_status_summary()
            
            # Update progress tracker
            await self.progress_tracker.update_progress(status)
            
            # Log minute-by-minute update
            self._log_progress_update(status)
            
        except Exception as e:
            logger.error(f"Error generating progress update: {e}")
    
    def _log_progress_update(self, status: Dict[str, Any]):
        """Log current progress status"""
        bot_status = status['bots']
        task_status = status['tasks']
        
        logger.info(
            f"Status: {bot_status['active']}/{bot_status['total']} bots active, "
            f"{task_status['running']} running, {task_status['queued']} queued, "
            f"multiplier: {status['time_multiplier']:.1f}x"
        )
    
    async def _schedule_system_tasks(self):
        """Schedule initial system maintenance tasks"""
        system_tasks = [
            {
                'id': 'daily_cleanup',
                'name': 'Daily System Cleanup',
                'priority': TaskPriority.LOW,
                'duration': 0.5,
                'capabilities': ['maintenance'],
                'schedule': 'daily'
            },
            {
                'id': 'health_check',
                'name': 'System Health Check',
                'priority': TaskPriority.NORMAL,
                'duration': 0.25,
                'capabilities': ['maintenance'],
                'schedule': 'hourly'
            },
            {
                'id': 'performance_analysis',
                'name': 'Performance Analysis',
                'priority': TaskPriority.NORMAL,
                'duration': 1.0,
                'capabilities': ['analytics'],
                'schedule': 'daily'
            }
        ]
        
        for task_config in system_tasks:
            task = Task(
                id=f"system_{task_config['id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                name=task_config['name'],
                priority=task_config['priority'],
                estimated_duration=task_config['duration'],
                resource_requirements={'capabilities': task_config['capabilities']},
                metadata={'system_task': True, 'schedule': task_config['schedule']}
            )
            
            self.bot_manager.add_task(task)
    
    # Public API methods
    async def schedule_task(self, task_data: Dict[str, Any]) -> str:
        """Schedule a new task"""
        task = Task(
            id=task_data.get('id', f"task_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"),
            name=task_data['name'],
            priority=TaskPriority(task_data.get('priority', 3)),
            estimated_duration=task_data.get('estimated_duration', 1.0),
            deadline=datetime.fromisoformat(task_data['deadline']) if task_data.get('deadline') else None,
            dependencies=task_data.get('dependencies', []),
            resource_requirements=task_data.get('resource_requirements', {}),
            metadata=task_data.get('metadata', {})
        )
        
        success = self.bot_manager.add_task(task)
        if success:
            logger.info(f"Scheduled task: {task.id}")
            return task.id
        else:
            raise ValueError(f"Failed to schedule task: {task.id}")
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task"""
        # Remove from queue if pending
        if task_id in self.bot_manager.task_queue:
            self.bot_manager.task_queue.remove(task_id)
            del self.bot_manager.tasks[task_id]
            logger.info(f"Cancelled pending task: {task_id}")
            return True
        
        # Stop running task
        if task_id in self.bot_manager.running_tasks:
            self.bot_manager.complete_task(task_id, success=False)
            logger.info(f"Cancelled running task: {task_id}")
            return True
        
        return False
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        if task_id in self.bot_manager.tasks:
            task = self.bot_manager.tasks[task_id]
            return {
                'id': task.id,
                'name': task.name,
                'status': task.status.value,
                'priority': task.priority.value,
                'bot_id': task.bot_id,
                'created_at': task.created_at.isoformat(),
                'started_at': task.started_at.isoformat() if task.started_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'estimated_duration': task.estimated_duration,
                'metadata': task.metadata
            }
        return None
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            'scheduler': {
                'running': self.is_running,
                'uptime': (datetime.now() - self.start_time).total_seconds() if hasattr(self, 'start_time') else 0
            },
            **self.bot_manager.get_status_summary(),
            'backup': await self.backup_manager.get_status(),
            'reporting': await self.progress_tracker.get_status()
        }
    
    async def add_bot(self, bot_config: Dict[str, Any]) -> bool:
        """Add a new bot to the system"""
        from .bot_manager import Bot
        
        bot = Bot(
            id=bot_config['id'],
            name=bot_config['name'],
            daily_limit_hours=bot_config.get('daily_limit_hours', 5.0),
            capabilities=bot_config.get('capabilities', [])
        )
        
        self.bot_manager.bots[bot.id] = bot
        logger.info(f"Added new bot: {bot.id}")
        return True
    
    async def remove_bot(self, bot_id: str) -> bool:
        """Remove a bot from the system"""
        if bot_id in self.bot_manager.bots:
            bot = self.bot_manager.bots[bot_id]
            if bot.current_task:
                # Cancel current task
                await self.cancel_task(bot.current_task)
            
            del self.bot_manager.bots[bot_id]
            logger.info(f"Removed bot: {bot_id}")
            return True
        
        return False