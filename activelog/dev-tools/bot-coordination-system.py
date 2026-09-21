#!/usr/bin/env python3
"""
SuperInstance Bot Coordination System
====================================

Advanced coordination system for SuperInstance bots to work together
effectively, preventing conflicts and maximizing development velocity.

🤖 Bot Types Supported:
- Component Architect Bot
- Assembly Specialist Bot  
- AI Integration Bot
- Experience Design Bot
- Infrastructure Bot

🎯 Coordination Features:
- Real-time task assignment with conflict prevention
- Bot specialization matching
- Progress tracking and synchronization
- Resource locking for file-level coordination
- Automatic workload balancing
- Performance metrics and optimization
"""

import json
import time
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from collections import defaultdict
from pathlib import Path
import asyncio
import threading
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class BotProfile:
    """Bot profile with specializations and capabilities"""
    bot_id: str
    bot_type: str  # component_architect, assembly_specialist, ai_integration, experience_design, infrastructure
    specializations: List[str]
    current_task: Optional[str]
    status: str  # idle, working, blocked, offline
    last_activity: str
    performance_metrics: Dict[str, float]
    workload_capacity: int
    current_workload: int

@dataclass
class Task:
    """Task definition with coordination metadata"""
    task_id: str
    title: str
    description: str
    task_type: str  # component_extraction, template_creation, integration, testing, documentation
    priority: int  # 1-10, higher is more urgent
    estimated_duration: int  # minutes
    required_specializations: List[str]
    dependencies: List[str]  # task_ids that must be completed first
    file_resources: List[str]  # files this task will modify
    assigned_bot: Optional[str]
    status: str  # pending, assigned, in_progress, completed, blocked
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    progress_percentage: int

@dataclass
class ResourceLock:
    """File resource lock to prevent conflicts"""
    resource_path: str
    locked_by: str
    lock_type: str  # read, write, exclusive
    locked_at: str
    expires_at: str

class SuperInstanceBotCoordinator:
    """Central coordination system for SuperInstance bots"""
    
    def __init__(self, coordination_file: str = "/home/activeloguser/activelog/bot-coordination.json"):
        self.coordination_file = coordination_file
        self.micro_updates_file = "/home/activeloguser/activelog/micro_updates.log"
        
        # In-memory state
        self.bots: Dict[str, BotProfile] = {}
        self.tasks: Dict[str, Task] = {}
        self.resource_locks: Dict[str, ResourceLock] = {}
        self.task_history: List[Dict[str, Any]] = []
        
        # Coordination metrics
        self.metrics = {
            "total_tasks_completed": 0,
            "average_task_completion_time": 0,
            "bot_collaboration_efficiency": 0,
            "conflict_prevention_saves": 0,
            "resource_lock_violations_prevented": 0
        }
        
        # Load existing state
        self._load_state()
        
        # Start background coordination thread
        self._start_coordination_thread()

    def _load_state(self):
        """Load coordination state from file"""
        try:
            if os.path.exists(self.coordination_file):
                with open(self.coordination_file, 'r') as f:
                    data = json.load(f)
                    
                # Load bots
                for bot_data in data.get('bots', []):
                    bot = BotProfile(**bot_data)
                    self.bots[bot.bot_id] = bot
                
                # Load tasks
                for task_data in data.get('tasks', []):
                    task = Task(**task_data)
                    self.tasks[task.task_id] = task
                
                # Load resource locks (expire old ones)
                current_time = datetime.now().isoformat()
                for lock_data in data.get('resource_locks', []):
                    lock = ResourceLock(**lock_data)
                    if lock.expires_at > current_time:
                        self.resource_locks[lock.resource_path] = lock
                
                self.metrics = data.get('metrics', self.metrics)
                logger.info(f"Loaded coordination state: {len(self.bots)} bots, {len(self.tasks)} tasks")
        except Exception as e:
            logger.warning(f"Could not load coordination state: {e}")

    def _save_state(self):
        """Save coordination state to file"""
        try:
            data = {
                'bots': [asdict(bot) for bot in self.bots.values()],
                'tasks': [asdict(task) for task in self.tasks.values()],
                'resource_locks': [asdict(lock) for lock in self.resource_locks.values()],
                'metrics': self.metrics,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.coordination_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save coordination state: {e}")

    def register_bot(self, bot_id: str, bot_type: str, specializations: List[str], 
                    workload_capacity: int = 3) -> bool:
        """Register a bot with the coordination system"""
        try:
            bot = BotProfile(
                bot_id=bot_id,
                bot_type=bot_type,
                specializations=specializations,
                current_task=None,
                status="idle",
                last_activity=datetime.now().isoformat(),
                performance_metrics={"avg_completion_time": 0, "success_rate": 1.0, "efficiency_score": 1.0},
                workload_capacity=workload_capacity,
                current_workload=0
            )
            
            self.bots[bot_id] = bot
            self._save_state()
            
            logger.info(f"Registered bot {bot_id} ({bot_type}) with specializations: {specializations}")
            self._log_micro_update(f"Bot {bot_id} registered - Type: {bot_type}, Specializations: {specializations}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register bot {bot_id}: {e}")
            return False

    def create_task(self, title: str, description: str, task_type: str, priority: int,
                   estimated_duration: int, required_specializations: List[str],
                   dependencies: List[str] = None, file_resources: List[str] = None) -> str:
        """Create a new task for bot assignment"""
        try:
            task_id = f"task_{int(time.time())}_{hashlib.md5(title.encode()).hexdigest()[:8]}"
            
            task = Task(
                task_id=task_id,
                title=title,
                description=description,
                task_type=task_type,
                priority=priority,
                estimated_duration=estimated_duration,
                required_specializations=required_specializations or [],
                dependencies=dependencies or [],
                file_resources=file_resources or [],
                assigned_bot=None,
                status="pending",
                created_at=datetime.now().isoformat(),
                started_at=None,
                completed_at=None,
                progress_percentage=0
            )
            
            self.tasks[task_id] = task
            self._save_state()
            
            logger.info(f"Created task {task_id}: {title}")
            self._log_micro_update(f"Task created: {title} (ID: {task_id}) - Priority: {priority}, Type: {task_type}")
            
            # Try to assign immediately
            self._try_assign_task(task_id)
            
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to create task: {e}")
            return ""

    def _try_assign_task(self, task_id: str) -> bool:
        """Try to assign a task to the best available bot"""
        try:
            task = self.tasks.get(task_id)
            if not task or task.assigned_bot:
                return False
            
            # Check if dependencies are met
            for dep_id in task.dependencies:
                dep_task = self.tasks.get(dep_id)
                if not dep_task or dep_task.status != "completed":
                    logger.info(f"Task {task_id} waiting for dependency {dep_id}")
                    return False
            
            # Check resource availability
            for resource in task.file_resources:
                if resource in self.resource_locks:
                    lock = self.resource_locks[resource]
                    if lock.expires_at > datetime.now().isoformat():
                        logger.info(f"Task {task_id} waiting for resource lock on {resource}")
                        return False
            
            # Find best bot for this task
            best_bot = self._find_best_bot_for_task(task)
            if not best_bot:
                logger.info(f"No available bot found for task {task_id}")
                return False
            
            # Assign task to bot
            task.assigned_bot = best_bot.bot_id
            task.status = "assigned"
            task.started_at = datetime.now().isoformat()
            
            best_bot.current_task = task_id
            best_bot.status = "working"
            best_bot.current_workload += 1
            best_bot.last_activity = datetime.now().isoformat()
            
            # Lock resources
            for resource in task.file_resources:
                self._lock_resource(resource, best_bot.bot_id, "write", task.estimated_duration)
            
            self._save_state()
            
            logger.info(f"Assigned task {task_id} to bot {best_bot.bot_id}")
            self._log_micro_update(f"Task assigned: {task.title} → {best_bot.bot_id} ({best_bot.bot_type})")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to assign task {task_id}: {e}")
            return False

    def _find_best_bot_for_task(self, task: Task) -> Optional[BotProfile]:
        """Find the best available bot for a specific task"""
        available_bots = []
        
        for bot in self.bots.values():
            # Check availability
            if bot.status != "idle" or bot.current_workload >= bot.workload_capacity:
                continue
            
            # Check specialization match
            specialization_score = 0
            for req_spec in task.required_specializations:
                if req_spec in bot.specializations:
                    specialization_score += 1
            
            if specialization_score == 0 and task.required_specializations:
                continue  # No matching specializations
            
            # Calculate bot score
            efficiency = bot.performance_metrics.get("efficiency_score", 1.0)
            success_rate = bot.performance_metrics.get("success_rate", 1.0)
            workload_factor = 1.0 - (bot.current_workload / bot.workload_capacity)
            
            score = (specialization_score * 2 + efficiency + success_rate) * workload_factor
            
            available_bots.append((bot, score))
        
        if not available_bots:
            return None
        
        # Return bot with highest score
        available_bots.sort(key=lambda x: x[1], reverse=True)
        return available_bots[0][0]

    def _lock_resource(self, resource_path: str, bot_id: str, lock_type: str, duration_minutes: int):
        """Lock a resource to prevent conflicts"""
        expires_at = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
        
        lock = ResourceLock(
            resource_path=resource_path,
            locked_by=bot_id,
            lock_type=lock_type,
            locked_at=datetime.now().isoformat(),
            expires_at=expires_at
        )
        
        self.resource_locks[resource_path] = lock
        logger.info(f"Locked resource {resource_path} for bot {bot_id} ({lock_type}) until {expires_at}")

    def update_task_progress(self, task_id: str, progress_percentage: int, bot_id: str) -> bool:
        """Update task progress"""
        try:
            task = self.tasks.get(task_id)
            if not task or task.assigned_bot != bot_id:
                return False
            
            task.progress_percentage = progress_percentage
            
            if progress_percentage >= 100:
                task.status = "completed"
                task.completed_at = datetime.now().isoformat()
                
                # Update bot status
                bot = self.bots.get(bot_id)
                if bot:
                    bot.current_task = None
                    bot.status = "idle"
                    bot.current_workload = max(0, bot.current_workload - 1)
                    bot.last_activity = datetime.now().isoformat()
                    
                    # Update performance metrics
                    completion_time = (datetime.fromisoformat(task.completed_at) - 
                                     datetime.fromisoformat(task.started_at)).total_seconds() / 60
                    self._update_bot_performance(bot, completion_time, task.estimated_duration)
                
                # Release resource locks
                resources_to_release = []
                for resource, lock in self.resource_locks.items():
                    if lock.locked_by == bot_id:
                        resources_to_release.append(resource)
                
                for resource in resources_to_release:
                    del self.resource_locks[resource]
                    logger.info(f"Released resource lock on {resource}")
                
                self.metrics["total_tasks_completed"] += 1
                
                logger.info(f"Task {task_id} completed by bot {bot_id}")
                self._log_micro_update(f"Task completed: {task.title} by {bot_id} - Progress: 100%")
                
                # Try to assign new tasks
                self._process_pending_tasks()
            
            else:
                task.status = "in_progress"
                logger.info(f"Task {task_id} progress updated: {progress_percentage}%")
            
            self._save_state()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            return False

    def _update_bot_performance(self, bot: BotProfile, actual_time: float, estimated_time: int):
        """Update bot performance metrics"""
        # Update average completion time
        current_avg = bot.performance_metrics.get("avg_completion_time", estimated_time)
        bot.performance_metrics["avg_completion_time"] = (current_avg + actual_time) / 2
        
        # Update efficiency score (actual vs estimated)
        efficiency = min(2.0, estimated_time / max(actual_time, 1))
        current_efficiency = bot.performance_metrics.get("efficiency_score", 1.0)
        bot.performance_metrics["efficiency_score"] = (current_efficiency * 0.8 + efficiency * 0.2)
        
        # Update success rate (assuming completion = success)
        current_success = bot.performance_metrics.get("success_rate", 1.0)
        bot.performance_metrics["success_rate"] = min(1.0, current_success * 0.9 + 0.1)

    def _process_pending_tasks(self):
        """Process all pending tasks for assignment"""
        pending_tasks = [task for task in self.tasks.values() if task.status == "pending"]
        pending_tasks.sort(key=lambda t: t.priority, reverse=True)
        
        for task in pending_tasks:
            self._try_assign_task(task.task_id)

    def _start_coordination_thread(self):
        """Start background coordination thread"""
        def coordination_loop():
            while True:
                try:
                    # Clean expired resource locks
                    current_time = datetime.now().isoformat()
                    expired_locks = []
                    for resource, lock in self.resource_locks.items():
                        if lock.expires_at <= current_time:
                            expired_locks.append(resource)
                    
                    for resource in expired_locks:
                        del self.resource_locks[resource]
                        logger.info(f"Expired resource lock released: {resource}")
                    
                    # Process pending tasks
                    self._process_pending_tasks()
                    
                    # Update coordination efficiency metrics
                    self._update_coordination_metrics()
                    
                    # Save state periodically
                    self._save_state()
                    
                except Exception as e:
                    logger.error(f"Coordination loop error: {e}")
                
                time.sleep(30)  # Run every 30 seconds
        
        thread = threading.Thread(target=coordination_loop, daemon=True)
        thread.start()
        logger.info("Bot coordination thread started")

    def _update_coordination_metrics(self):
        """Update coordination system metrics"""
        try:
            # Calculate collaboration efficiency
            active_bots = len([bot for bot in self.bots.values() if bot.status == "working"])
            total_bots = len(self.bots)
            
            if total_bots > 0:
                utilization = active_bots / total_bots
                self.metrics["bot_collaboration_efficiency"] = utilization
            
            # Calculate average task completion time
            completed_tasks = [task for task in self.tasks.values() if task.status == "completed" and task.completed_at]
            
            if completed_tasks:
                total_time = 0
                for task in completed_tasks:
                    start_time = datetime.fromisoformat(task.started_at)
                    end_time = datetime.fromisoformat(task.completed_at)
                    total_time += (end_time - start_time).total_seconds() / 60
                
                self.metrics["average_task_completion_time"] = total_time / len(completed_tasks)
        
        except Exception as e:
            logger.error(f"Failed to update coordination metrics: {e}")

    def _log_micro_update(self, message: str):
        """Log coordination update to micro_updates.log"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.micro_updates_file, 'a') as f:
                f.write(f"{timestamp} - BOT_COORDINATION - {message}\n")
        except Exception as e:
            logger.error(f"Failed to log micro update: {e}")

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "coordination_metrics": self.metrics,
            "bot_status": {
                "total_bots": len(self.bots),
                "active_bots": len([bot for bot in self.bots.values() if bot.status == "working"]),
                "idle_bots": len([bot for bot in self.bots.values() if bot.status == "idle"]),
                "bot_details": [asdict(bot) for bot in self.bots.values()]
            },
            "task_status": {
                "total_tasks": len(self.tasks),
                "pending_tasks": len([task for task in self.tasks.values() if task.status == "pending"]),
                "in_progress_tasks": len([task for task in self.tasks.values() if task.status in ["assigned", "in_progress"]]),
                "completed_tasks": len([task for task in self.tasks.values() if task.status == "completed"]),
                "task_details": [asdict(task) for task in self.tasks.values()]
            },
            "resource_locks": {
                "active_locks": len(self.resource_locks),
                "lock_details": [asdict(lock) for lock in self.resource_locks.values()]
            },
            "system_health": {
                "conflicts_prevented": self.metrics.get("resource_lock_violations_prevented", 0),
                "collaboration_efficiency": self.metrics.get("bot_collaboration_efficiency", 0),
                "average_task_time": self.metrics.get("average_task_completion_time", 0)
            }
        }

    def prevent_bot_conflict(self, bot_id: str, intended_files: List[str]) -> Tuple[bool, List[str]]:
        """Check if bot can safely work on files without conflicts"""
        conflicts = []
        
        for file_path in intended_files:
            if file_path in self.resource_locks:
                lock = self.resource_locks[file_path]
                if lock.locked_by != bot_id and lock.expires_at > datetime.now().isoformat():
                    conflicts.append(f"{file_path} locked by {lock.locked_by} until {lock.expires_at}")
        
        if conflicts:
            self.metrics["resource_lock_violations_prevented"] += 1
            self._log_micro_update(f"Conflict prevented for bot {bot_id} - Files: {intended_files}")
        
        return len(conflicts) == 0, conflicts

# CLI Interface for bot coordination
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="SuperInstance Bot Coordination System")
    parser.add_argument("--status", action="store_true", help="Show system status")
    parser.add_argument("--register-bot", nargs=3, metavar=("BOT_ID", "BOT_TYPE", "SPECIALIZATIONS"), 
                       help="Register a new bot")
    parser.add_argument("--create-task", nargs=6, metavar=("TITLE", "DESCRIPTION", "TYPE", "PRIORITY", "DURATION", "SPECIALIZATIONS"),
                       help="Create a new task")
    parser.add_argument("--update-progress", nargs=3, metavar=("TASK_ID", "PROGRESS", "BOT_ID"),
                       help="Update task progress")
    
    args = parser.parse_args()
    
    coordinator = SuperInstanceBotCoordinator()
    
    if args.status:
        status = coordinator.get_system_status()
        print(json.dumps(status, indent=2))
    
    elif args.register_bot:
        bot_id, bot_type, specializations = args.register_bot
        spec_list = specializations.split(",")
        success = coordinator.register_bot(bot_id, bot_type, spec_list)
        print(f"Bot registration {'successful' if success else 'failed'}")
    
    elif args.create_task:
        title, description, task_type, priority, duration, specializations = args.create_task
        spec_list = specializations.split(",")
        task_id = coordinator.create_task(title, description, task_type, int(priority), int(duration), spec_list)
        print(f"Created task: {task_id}")
    
    elif args.update_progress:
        task_id, progress, bot_id = args.update_progress
        success = coordinator.update_task_progress(task_id, int(progress), bot_id)
        print(f"Progress update {'successful' if success else 'failed'}")
    
    else:
        print("🤖 SuperInstance Bot Coordination System")
        print("=====================================")
        print("Use --help to see available commands")
        status = coordinator.get_system_status()
        print(f"Active Bots: {status['bot_status']['active_bots']}")
        print(f"Pending Tasks: {status['task_status']['pending_tasks']}")
        print(f"Collaboration Efficiency: {status['system_health']['collaboration_efficiency']:.2%}")

if __name__ == "__main__":
    main()