"""
Scheduler Engine

Advanced scheduling system with 5-hour session limits, intelligent backup scheduling,
and automated development workflow management for ActiveLog.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Callable, Union
from enum import Enum
import aiosqlite
import croniter
from pathlib import Path
import subprocess
import git
import shutil
import tarfile
import gzip

logger = logging.getLogger(__name__)

class ScheduleType(Enum):
    SESSION_LIMIT = "session_limit"
    BACKUP = "backup" 
    WORKFLOW = "workflow"
    MAINTENANCE = "maintenance"
    MONITORING = "monitoring"
    CLEANUP = "cleanup"

class SchedulePriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4
    EMERGENCY = 5

class SessionStatus(Enum):
    ACTIVE = "active"
    WARNING = "warning"
    CRITICAL = "critical"
    EXPIRED = "expired"
    FORCED_STOP = "forced_stop"

@dataclass
class ScheduledTask:
    id: str
    name: str
    schedule_type: ScheduleType
    priority: SchedulePriority
    cron_expression: str
    function: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: dict = field(default_factory=dict)
    enabled: bool = True
    next_run: datetime = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    failure_count: int = 0
    max_failures: int = 3
    timeout_seconds: int = 3600
    retry_delay_seconds: int = 60

@dataclass
class SessionMetrics:
    session_id: str
    start_time: datetime
    current_duration_hours: float
    token_usage: int
    cost_cc: float
    tasks_completed: int
    status: SessionStatus
    warning_threshold_hours: float = 4.0
    critical_threshold_hours: float = 4.5
    max_duration_hours: float = 5.0

class SessionLimiter:
    """Manages 5-hour session limits and intelligent throttling"""
    
    def __init__(self, max_hours: float = 5.0):
        self.max_hours = max_hours
        self.warning_threshold = max_hours * 0.8  # 4 hours
        self.critical_threshold = max_hours * 0.9  # 4.5 hours
        self.current_session = None
        self.callbacks = {
            SessionStatus.WARNING: [],
            SessionStatus.CRITICAL: [],
            SessionStatus.EXPIRED: []
        }
    
    def start_session(self, session_id: str = None) -> SessionMetrics:
        """Start a new development session"""
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        self.current_session = SessionMetrics(
            session_id=session_id,
            start_time=datetime.now(timezone.utc),
            current_duration_hours=0.0,
            token_usage=0,
            cost_cc=0.0,
            tasks_completed=0,
            status=SessionStatus.ACTIVE,
            warning_threshold_hours=self.warning_threshold,
            critical_threshold_hours=self.critical_threshold,
            max_duration_hours=self.max_hours
        )
        
        logger.info(f"Started development session: {session_id}")
        return self.current_session
    
    def update_session(self, token_usage: int = 0, cost_cc: float = 0.0, 
                      tasks_completed: int = 0) -> SessionMetrics:
        """Update current session metrics"""
        if not self.current_session:
            self.start_session()
        
        # Update metrics
        self.current_session.token_usage += token_usage
        self.current_session.cost_cc += cost_cc
        self.current_session.tasks_completed += tasks_completed
        
        # Calculate current duration
        current_time = datetime.now(timezone.utc)
        duration = current_time - self.current_session.start_time
        self.current_session.current_duration_hours = duration.total_seconds() / 3600
        
        # Update status
        old_status = self.current_session.status
        
        if self.current_session.current_duration_hours >= self.max_hours:
            self.current_session.status = SessionStatus.EXPIRED
        elif self.current_session.current_duration_hours >= self.critical_threshold:
            self.current_session.status = SessionStatus.CRITICAL
        elif self.current_session.current_duration_hours >= self.warning_threshold:
            self.current_session.status = SessionStatus.WARNING
        else:
            self.current_session.status = SessionStatus.ACTIVE
        
        # Trigger callbacks on status change
        if old_status != self.current_session.status:
            await self._trigger_status_callbacks(self.current_session.status)
        
        return self.current_session
    
    async def _trigger_status_callbacks(self, status: SessionStatus):
        """Trigger registered callbacks for status changes"""
        for callback in self.callbacks.get(status, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self.current_session)
                else:
                    callback(self.current_session)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    def register_status_callback(self, status: SessionStatus, callback: Callable):
        """Register callback for status changes"""
        self.callbacks[status].append(callback)
    
    def get_remaining_time(self) -> timedelta:
        """Get remaining time in current session"""
        if not self.current_session:
            return timedelta(hours=self.max_hours)
        
        remaining_hours = self.max_hours - self.current_session.current_duration_hours
        return timedelta(hours=max(0, remaining_hours))
    
    def should_throttle(self) -> tuple[bool, float]:
        """Check if operations should be throttled and by how much"""
        if not self.current_session:
            return False, 1.0
        
        if self.current_session.status == SessionStatus.EXPIRED:
            return True, 0.0  # Complete stop
        elif self.current_session.status == SessionStatus.CRITICAL:
            return True, 0.1  # 90% throttle
        elif self.current_session.status == SessionStatus.WARNING:
            return True, 0.5  # 50% throttle
        
        return False, 1.0

class SchedulerEngine:
    """
    Advanced scheduler engine with session management, backup automation,
    and intelligent workflow scheduling for ActiveLog development.
    """
    
    def __init__(self):
        self.tasks = {}
        self.running = False
        self.session_limiter = SessionLimiter()
        self.db_path = "/home/activeloguser/activelog/services/auto-scheduler/scheduler.db"
        
        # Initialize default schedules
        self._initialize_default_schedules()
        
        # Start background scheduler
        asyncio.create_task(self._init_database())
        asyncio.create_task(self._scheduler_loop())
    
    def _initialize_default_schedules(self):
        """Initialize default scheduled tasks"""
        
        # 3 AM Daily Backup
        self.add_task(
            "daily_backup",
            "Daily System Backup",
            ScheduleType.BACKUP,
            SchedulePriority.HIGH,
            "0 3 * * *",  # 3 AM daily
            self._perform_daily_backup
        )
        
        # Weekly Deep Backup (Sunday 2 AM)
        self.add_task(
            "weekly_backup",
            "Weekly Deep Backup",
            ScheduleType.BACKUP,
            SchedulePriority.CRITICAL,
            "0 2 * * 0",  # Sunday 2 AM
            self._perform_weekly_backup
        )
        
        # Monthly Archive (1st of month, 1 AM)
        self.add_task(
            "monthly_archive",
            "Monthly Archive Creation",
            ScheduleType.BACKUP,
            SchedulePriority.MEDIUM,
            "0 1 1 * *",  # 1st day of month, 1 AM
            self._perform_monthly_archive
        )
        
        # Session Limit Monitor (every minute)
        self.add_task(
            "session_monitor",
            "Session Limit Monitoring",
            ScheduleType.SESSION_LIMIT,
            SchedulePriority.CRITICAL,
            "* * * * *",  # Every minute
            self._monitor_session_limits
        )
        
        # Cleanup Temp Files (every 6 hours)
        self.add_task(
            "cleanup_temp",
            "Cleanup Temporary Files",
            ScheduleType.CLEANUP,
            SchedulePriority.LOW,
            "0 */6 * * *",  # Every 6 hours
            self._cleanup_temp_files
        )
        
        # Health Check (every 5 minutes)
        self.add_task(
            "health_check",
            "System Health Check",
            ScheduleType.MONITORING,
            SchedulePriority.MEDIUM,
            "*/5 * * * *",  # Every 5 minutes
            self._perform_health_check
        )
    
    async def _init_database(self):
        """Initialize scheduler database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    cron_expression TEXT NOT NULL,
                    enabled BOOLEAN DEFAULT 1,
                    next_run TEXT NOT NULL,
                    last_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    failure_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    success BOOLEAN,
                    error_message TEXT,
                    execution_time_seconds REAL,
                    FOREIGN KEY (task_id) REFERENCES scheduled_tasks (id)
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_history (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_hours REAL,
                    token_usage INTEGER DEFAULT 0,
                    cost_cc REAL DEFAULT 0.0,
                    tasks_completed INTEGER DEFAULT 0,
                    final_status TEXT,
                    backup_created BOOLEAN DEFAULT 0
                )
            """)
            
            await db.commit()
    
    def add_task(self, task_id: str, name: str, schedule_type: ScheduleType,
                priority: SchedulePriority, cron_expression: str, 
                function: Callable, *args, **kwargs):
        """Add a scheduled task"""
        
        # Calculate next run time
        cron = croniter.croniter(cron_expression, datetime.now())
        next_run = cron.get_next(datetime)
        
        task = ScheduledTask(
            id=task_id,
            name=name,
            schedule_type=schedule_type,
            priority=priority,
            cron_expression=cron_expression,
            function=function,
            args=args,
            kwargs=kwargs,
            next_run=next_run
        )
        
        self.tasks[task_id] = task
        logger.info(f"Added scheduled task: {name} (next run: {next_run})")
    
    def remove_task(self, task_id: str):
        """Remove a scheduled task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed scheduled task: {task_id}")
    
    def enable_task(self, task_id: str, enabled: bool = True):
        """Enable or disable a scheduled task"""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = enabled
            logger.info(f"{'Enabled' if enabled else 'Disabled'} task: {task_id}")
    
    async def _scheduler_loop(self):
        """Main scheduler loop"""
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.running:
                    continue
                
                current_time = datetime.now()
                
                # Check for tasks that need to run
                for task in self.tasks.values():
                    if (task.enabled and 
                        task.next_run and 
                        current_time >= task.next_run and
                        task.failure_count < task.max_failures):
                        
                        # Execute task
                        asyncio.create_task(self._execute_task(task))
                        
                        # Schedule next run
                        cron = croniter.croniter(task.cron_expression, current_time)
                        task.next_run = cron.get_next(datetime)
                
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        execution_id = f"{task.id}_{int(time.time())}"
        start_time = datetime.now()
        
        logger.info(f"Executing scheduled task: {task.name}")
        
        try:
            # Record execution start
            await self._record_execution_start(execution_id, task.id, start_time)
            
            # Execute with timeout
            if asyncio.iscoroutinefunction(task.function):
                result = await asyncio.wait_for(
                    task.function(*task.args, **task.kwargs),
                    timeout=task.timeout_seconds
                )
            else:
                result = await asyncio.get_event_loop().run_in_executor(
                    None, task.function, *task.args, **task.kwargs
                )
            
            # Record success
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            await self._record_execution_complete(
                execution_id, end_time, True, None, execution_time
            )
            
            # Update task stats
            task.last_run = start_time
            task.run_count += 1
            task.failure_count = 0  # Reset failure count on success
            
            logger.info(f"Task '{task.name}' completed successfully in {execution_time:.2f}s")
            
        except asyncio.TimeoutError:
            error_msg = f"Task '{task.name}' timed out after {task.timeout_seconds}s"
            await self._handle_task_failure(task, execution_id, error_msg)
            
        except Exception as e:
            error_msg = f"Task '{task.name}' failed: {str(e)}"
            await self._handle_task_failure(task, execution_id, error_msg)
    
    async def _handle_task_failure(self, task: ScheduledTask, execution_id: str, error_msg: str):
        """Handle task execution failure"""
        logger.error(error_msg)
        
        # Record failure
        end_time = datetime.now()
        await self._record_execution_complete(
            execution_id, end_time, False, error_msg, 0
        )
        
        # Update failure count
        task.failure_count += 1
        
        # Schedule retry if under failure limit
        if task.failure_count < task.max_failures:
            retry_time = datetime.now() + timedelta(seconds=task.retry_delay_seconds)
            task.next_run = retry_time
            logger.info(f"Scheduled retry for '{task.name}' at {retry_time}")
        else:
            logger.error(f"Task '{task.name}' exceeded max failures ({task.max_failures}), disabling")
            task.enabled = False
    
    async def _record_execution_start(self, execution_id: str, task_id: str, start_time: datetime):
        """Record task execution start"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO task_executions (id, task_id, started_at)
                VALUES (?, ?, ?)
            """, (execution_id, task_id, start_time.isoformat()))
            await db.commit()
    
    async def _record_execution_complete(self, execution_id: str, end_time: datetime,
                                       success: bool, error_message: str, execution_time: float):
        """Record task execution completion"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE task_executions 
                SET completed_at = ?, success = ?, error_message = ?, execution_time_seconds = ?
                WHERE id = ?
            """, (end_time.isoformat(), success, error_message, execution_time, execution_id))
            await db.commit()
    
    # Scheduled Task Functions
    
    async def _perform_daily_backup(self):
        """Perform daily backup at 3 AM"""
        logger.info("Starting daily backup...")
        
        backup_dir = Path("/home/activeloguser/activelog/backups/daily")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"activelog_daily_{timestamp}.tar.gz"
        backup_path = backup_dir / backup_name
        
        # Create backup
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add("/home/activeloguser/activelog/services", arcname="services")
            tar.add("/home/activeloguser/activelog/frontend", arcname="frontend", filter=self._backup_filter)
            
            # Add databases
            for db_file in Path("/home/activeloguser/activelog/services").rglob("*.db"):
                tar.add(db_file, arcname=f"databases/{db_file.name}")
        
        # Keep only last 7 daily backups
        await self._cleanup_old_backups(backup_dir, "activelog_daily_", 7)
        
        logger.info(f"Daily backup completed: {backup_path}")
    
    async def _perform_weekly_backup(self):
        """Perform comprehensive weekly backup"""
        logger.info("Starting weekly backup...")
        
        backup_dir = Path("/home/activeloguser/activelog/backups/weekly")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"activelog_weekly_{timestamp}.tar.gz"
        backup_path = backup_dir / backup_name
        
        # Create comprehensive backup
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add("/home/activeloguser/activelog", arcname="activelog")
        
        # Keep only last 4 weekly backups
        await self._cleanup_old_backups(backup_dir, "activelog_weekly_", 4)
        
        logger.info(f"Weekly backup completed: {backup_path}")
    
    async def _perform_monthly_archive(self):
        """Create monthly archive"""
        logger.info("Starting monthly archive...")
        
        archive_dir = Path("/home/activeloguser/activelog/backups/monthly")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m")
        archive_name = f"activelog_archive_{timestamp}.tar.gz"
        archive_path = archive_dir / archive_name
        
        # Create archive with git history
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add("/home/activeloguser/activelog", arcname=f"activelog_{timestamp}")
        
        # Keep monthly archives for 12 months
        await self._cleanup_old_backups(archive_dir, "activelog_archive_", 12)
        
        logger.info(f"Monthly archive completed: {archive_path}")
    
    def _backup_filter(self, tarinfo):
        """Filter function for backups to exclude unnecessary files"""
        exclude_patterns = [
            "node_modules", "__pycache__", ".git", "*.log", "*.tmp", 
            ".DS_Store", "Thumbs.db", "*.pyc", "dist", "build"
        ]
        
        for pattern in exclude_patterns:
            if pattern in tarinfo.name:
                return None
        
        return tarinfo
    
    async def _cleanup_old_backups(self, backup_dir: Path, prefix: str, keep_count: int):
        """Clean up old backup files"""
        backup_files = sorted(backup_dir.glob(f"{prefix}*"), key=lambda x: x.stat().st_mtime, reverse=True)
        
        for backup_file in backup_files[keep_count:]:
            backup_file.unlink()
            logger.info(f"Deleted old backup: {backup_file}")
    
    async def _monitor_session_limits(self):
        """Monitor and enforce session limits"""
        if self.session_limiter.current_session:
            session = self.session_limiter.update_session()
            
            if session.status == SessionStatus.EXPIRED:
                logger.critical("SESSION EXPIRED - Initiating emergency backup and shutdown")
                await self._emergency_session_end(session)
    
    async def _emergency_session_end(self, session: SessionMetrics):
        """Handle emergency session end"""
        try:
            # Create emergency backup
            backup_dir = Path("/home/activeloguser/activelog/backups/emergency")
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"emergency_backup_{session.session_id}_{timestamp}.tar.gz"
            backup_path = backup_dir / backup_name
            
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add("/home/activeloguser/activelog/services", arcname="services")
            
            # Record session end
            await self._record_session_end(session, backup_created=True)
            
            logger.critical(f"Emergency backup created: {backup_path}")
            logger.critical("DEVELOPMENT SESSION FORCIBLY ENDED DUE TO TIME LIMIT")
            
        except Exception as e:
            logger.error(f"Emergency session end failed: {e}")
    
    async def _cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_dirs = [
            "/tmp",
            "/home/activeloguser/activelog/services/*/logs",
            "/home/activeloguser/activelog/services/*/*.log"
        ]
        
        cleaned_count = 0
        for temp_pattern in temp_dirs:
            for temp_file in Path().glob(temp_pattern):
                if temp_file.is_file() and temp_file.stat().st_mtime < time.time() - 86400:  # 1 day old
                    temp_file.unlink()
                    cleaned_count += 1
        
        logger.info(f"Cleaned up {cleaned_count} temporary files")
    
    async def _perform_health_check(self):
        """Perform system health check"""
        # Check disk space
        disk_usage = shutil.disk_usage("/home/activeloguser/activelog")
        free_gb = disk_usage.free / (1024**3)
        
        if free_gb < 5.0:  # Less than 5GB free
            logger.warning(f"Low disk space: {free_gb:.1f}GB remaining")
        
        # Check service health
        services_healthy = True
        service_ports = [8450, 8440, 8441, 8442, 8443, 8444, 8445]
        
        for port in service_ports:
            # Simple port check (would implement proper health checks in production)
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                if result != 0:
                    services_healthy = False
                    logger.warning(f"Service on port {port} appears to be down")
            except:
                pass
        
        if services_healthy:
            logger.info("System health check: All services healthy")
    
    async def _record_session_end(self, session: SessionMetrics, backup_created: bool = False):
        """Record session end in database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO session_history
                (session_id, start_time, end_time, duration_hours, token_usage,
                 cost_cc, tasks_completed, final_status, backup_created)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.start_time.isoformat(),
                datetime.now(timezone.utc).isoformat(),
                session.current_duration_hours,
                session.token_usage,
                session.cost_cc,
                session.tasks_completed,
                session.status.value,
                backup_created
            ))
            await db.commit()
    
    async def start(self):
        """Start the scheduler engine"""
        self.running = True
        
        # Start session monitoring
        self.session_limiter.start_session()
        
        logger.info("Scheduler engine started")
    
    async def stop(self):
        """Stop the scheduler engine"""
        self.running = False
        
        # Record session end if active
        if self.session_limiter.current_session:
            await self._record_session_end(self.session_limiter.current_session)
        
        logger.info("Scheduler engine stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status"""
        task_status = {}
        for task_id, task in self.tasks.items():
            task_status[task_id] = {
                "name": task.name,
                "enabled": task.enabled,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "run_count": task.run_count,
                "failure_count": task.failure_count
            }
        
        return {
            "running": self.running,
            "current_session": self.session_limiter.current_session.__dict__ if self.session_limiter.current_session else None,
            "tasks": task_status
        }

# Global instance
scheduler_engine = SchedulerEngine()