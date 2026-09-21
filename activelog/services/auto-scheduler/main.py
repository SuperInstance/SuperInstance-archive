#!/usr/bin/env python3
"""
Auto-Scheduler Service
A comprehensive automation system for intelligent scheduling, backup management, and progress reporting.
"""

import asyncio
import signal
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import uvicorn
import logging

# Import our components
from src.utils.config import ConfigManager
from src.utils.logging_setup import setup_logging
from src.scheduler.scheduler import AutoScheduler
from src.scheduler.bot_manager import TaskPriority
from src.database.schema import DatabaseManager

# Initialize configuration
config_manager = ConfigManager()
config = config_manager.to_dict()

# Setup logging
setup_logging(config)
logger = logging.getLogger('auto_scheduler')

# Initialize FastAPI app
app = FastAPI(
    title="Auto-Scheduler Service",
    description="Intelligent scheduling, backup management, and progress reporting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.get('security', {}).get('allowed_hosts', ['*']),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
scheduler: Optional[AutoScheduler] = None
database_manager: Optional[DatabaseManager] = None

# Pydantic models for API
class TaskRequest(BaseModel):
    name: str
    priority: int = 3
    estimated_duration: float = 1.0
    deadline: Optional[str] = None
    dependencies: List[str] = []
    resource_requirements: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

class BotRequest(BaseModel):
    id: str
    name: str
    daily_limit_hours: float = 5.0
    capabilities: List[str] = []

class BackupRequest(BaseModel):
    backup_type: str
    metadata: Optional[Dict[str, Any]] = None

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize the auto-scheduler service"""
    global scheduler, database_manager
    
    logger.info("Starting Auto-Scheduler Service")
    
    try:
        # Apply environment overrides
        config_manager.apply_environment_overrides()
        updated_config = config_manager.to_dict()
        
        # Initialize database
        database_manager = DatabaseManager(updated_config)
        await database_manager.initialize()
        
        # Initialize scheduler
        scheduler = AutoScheduler(updated_config)
        await scheduler.start()
        
        logger.info("Auto-Scheduler Service started successfully")
        
    except Exception as e:
        logger.error(f"Failed to start Auto-Scheduler Service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on service shutdown"""
    global scheduler
    
    logger.info("Shutting down Auto-Scheduler Service")
    
    if scheduler:
        try:
            await scheduler.stop()
            logger.info("Auto-Scheduler Service stopped successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

# Signal handlers for graceful shutdown
def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    asyncio.create_task(shutdown_event())

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Helper functions
def get_scheduler() -> AutoScheduler:
    """Get the global scheduler instance"""
    if scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return scheduler

def get_config_manager() -> ConfigManager:
    """Get the global config manager instance"""
    return config_manager

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_system_status()
        
        return {
            "status": "healthy",
            "service": "auto-scheduler",
            "version": "1.0.0",
            "scheduler_running": status.get('scheduler', {}).get('running', False),
            "timestamp": status.get('timestamp')
        }
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "error": str(e)}
        )

# Task management endpoints
@app.post("/tasks")
async def create_task(task: TaskRequest):
    """Create a new task"""
    try:
        scheduler_instance = get_scheduler()
        
        task_data = {
            'name': task.name,
            'priority': task.priority,
            'estimated_duration': task.estimated_duration,
            'deadline': task.deadline,
            'dependencies': task.dependencies,
            'resource_requirements': task.resource_requirements,
            'metadata': task.metadata
        }
        
        task_id = await scheduler_instance.schedule_task(task_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Task '{task.name}' scheduled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_task_status(task_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending or running task"""
    try:
        scheduler_instance = get_scheduler()
        success = await scheduler_instance.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        return {
            "success": True,
            "message": f"Task {task_id} cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks")
async def list_tasks():
    """List all tasks with their current status"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_system_status()
        
        return {
            "tasks": status.get('tasks', {}),
            "task_details": {
                "queued": status.get('bot_manager', {}).get('task_queue', []),
                "running": list(status.get('bot_manager', {}).get('running_tasks', {}).keys()),
                "completed": list(status.get('bot_manager', {}).get('completed_tasks', {}).keys()),
                "failed": list(status.get('bot_manager', {}).get('failed_tasks', {}).keys())
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Bot management endpoints
@app.post("/bots")
async def add_bot(bot: BotRequest):
    """Add a new bot to the system"""
    try:
        scheduler_instance = get_scheduler()
        
        bot_config = {
            'id': bot.id,
            'name': bot.name,
            'daily_limit_hours': bot.daily_limit_hours,
            'capabilities': bot.capabilities
        }
        
        success = await scheduler_instance.add_bot(bot_config)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add bot")
        
        return {
            "success": True,
            "message": f"Bot '{bot.name}' added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/bots/{bot_id}")
async def remove_bot(bot_id: str):
    """Remove a bot from the system"""
    try:
        scheduler_instance = get_scheduler()
        success = await scheduler_instance.remove_bot(bot_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Bot not found")
        
        return {
            "success": True,
            "message": f"Bot {bot_id} removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bot: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bots")
async def list_bots():
    """List all bots and their current status"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_system_status()
        
        return {
            "bots": status.get('bots', {}),
            "timestamp": status.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Error listing bots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Backup management endpoints
@app.post("/backups")
async def create_backup(backup: BackupRequest):
    """Create a new backup"""
    try:
        scheduler_instance = get_scheduler()
        
        # Create a backup task
        task_data = {
            'name': f'Manual Backup: {backup.backup_type}',
            'priority': 2,  # High priority
            'estimated_duration': 2.0,
            'resource_requirements': {'capabilities': ['backup']},
            'metadata': {
                'backup_type': backup.backup_type,
                'manual': True,
                **(backup.metadata or {})
            }
        }
        
        task_id = await scheduler_instance.schedule_task(task_data)
        
        return {
            "success": True,
            "task_id": task_id,
            "message": f"Backup task scheduled: {backup.backup_type}"
        }
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backups/status")
async def get_backup_status():
    """Get backup system status"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_system_status()
        
        return {
            "backup": status.get('backup', {}),
            "timestamp": status.get('timestamp')
        }
        
    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Reporting endpoints
@app.get("/reports/progress")
async def get_progress_report():
    """Get current progress report"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get minute update from progress tracker
        minute_update = await scheduler_instance.progress_tracker.generate_minute_update()
        
        return {
            "type": "progress_report",
            "data": minute_update
        }
        
    except Exception as e:
        logger.error(f"Error generating progress report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/hourly")
async def get_hourly_summary():
    """Get hourly summary report"""
    try:
        scheduler_instance = get_scheduler()
        
        # Generate hourly summary
        summary = await scheduler_instance.progress_tracker.generate_hourly_summary()
        
        return {
            "type": "hourly_summary",
            "data": summary
        }
        
    except Exception as e:
        logger.error(f"Error generating hourly summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/daily")
async def get_daily_report():
    """Get daily report"""
    try:
        scheduler_instance = get_scheduler()
        
        # Generate daily report
        report = await scheduler_instance.progress_tracker.generate_daily_report()
        
        return {
            "type": "daily_report",
            "data": report
        }
        
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/recommendations")
async def get_recommendations():
    """Get intelligent recommendations"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get recommendations from progress tracker
        recommendations = await scheduler_instance.progress_tracker.get_recommendations()
        
        # Get backup recommendations
        backup_recommendations = await scheduler_instance.backup_manager.get_backup_recommendations()
        
        return {
            "recommendations": recommendations + backup_recommendations,
            "timestamp": scheduler_instance.progress_tracker.progress_tracker.datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System status and configuration endpoints
@app.get("/status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        scheduler_instance = get_scheduler()
        status = await scheduler_instance.get_system_status()
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting system status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_configuration():
    """Get current configuration"""
    try:
        config_mgr = get_config_manager()
        return {
            "config": config_mgr.to_dict(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/reload")
async def reload_configuration():
    """Reload configuration from file"""
    try:
        config_mgr = get_config_manager()
        config_mgr.reload()
        
        return {
            "success": True,
            "message": "Configuration reloaded successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/config")
async def update_configuration(updates: Dict[str, Any]):
    """Update configuration dynamically"""
    try:
        config_mgr = get_config_manager()
        result = config_mgr.update_config_dynamically(updates)
        
        if result['success']:
            return {
                "success": True,
                "message": "Configuration updated successfully",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Configuration update failed'))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/backup")
async def backup_configuration():
    """Create a configuration backup"""
    try:
        config_mgr = get_config_manager()
        backup_path = config_mgr.create_backup()
        
        return {
            "success": True,
            "backup_path": backup_path,
            "message": "Configuration backup created successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error backing up configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/history")
async def get_configuration_history():
    """Get configuration backup history"""
    try:
        config_mgr = get_config_manager()
        history = config_mgr.get_config_history()
        
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting configuration history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/config/restore/{backup_name}")
async def restore_configuration(backup_name: str):
    """Restore configuration from backup"""
    try:
        config_mgr = get_config_manager()
        
        # Find backup by name
        history = config_mgr.get_config_history()
        backup_path = None
        
        for backup in history:
            if backup['name'] == backup_name:
                backup_path = backup['path']
                break
        
        if not backup_path:
            raise HTTPException(status_code=404, detail=f"Backup '{backup_name}' not found")
        
        success = config_mgr.restore_from_backup(backup_path)
        
        if success:
            return {
                "success": True,
                "message": f"Configuration restored from {backup_name}",
                "restored_from": backup_path,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Configuration restore failed")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/integrations")
async def get_service_integrations():
    """Get service integration configuration"""
    try:
        config_mgr = get_config_manager()
        integrations = config_mgr.get_service_integrations()
        
        return {
            "success": True,
            "integrations": integrations,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting service integrations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/health")
async def get_configuration_health():
    """Get configuration health status"""
    try:
        config_mgr = get_config_manager()
        health_status = config_mgr.validate_service_health()
        
        return {
            "success": True,
            "health": health_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting configuration health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Maintenance endpoints
@app.post("/maintenance/cleanup")
async def run_cleanup():
    """Run system cleanup tasks"""
    try:
        scheduler_instance = get_scheduler()
        
        # Schedule cleanup tasks
        cleanup_tasks = [
            {
                'name': 'Database Cleanup',
                'priority': 3,
                'estimated_duration': 0.5,
                'resource_requirements': {'capabilities': ['maintenance']},
                'metadata': {'cleanup_type': 'database'}
            },
            {
                'name': 'Log Cleanup',
                'priority': 3,
                'estimated_duration': 0.25,
                'resource_requirements': {'capabilities': ['maintenance']},
                'metadata': {'cleanup_type': 'logs'}
            },
            {
                'name': 'Progress Data Cleanup',
                'priority': 3,
                'estimated_duration': 0.25,
                'resource_requirements': {'capabilities': ['maintenance']},
                'metadata': {'cleanup_type': 'progress'}
            }
        ]
        
        scheduled_tasks = []
        for task_data in cleanup_tasks:
            task_id = await scheduler_instance.schedule_task(task_data)
            scheduled_tasks.append(task_id)
        
        return {
            "success": True,
            "scheduled_tasks": scheduled_tasks,
            "message": "Cleanup tasks scheduled successfully"
        }
        
    except Exception as e:
        logger.error(f"Error running cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database management endpoints
@app.get("/database/stats")
async def get_database_stats():
    """Get database statistics and health information"""
    try:
        if database_manager is None:
            raise HTTPException(status_code=503, detail="Database manager not initialized")
        
        stats = await database_manager.get_database_stats()
        return {
            "success": True,
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/database/optimize")
async def optimize_database():
    """Run database optimization"""
    try:
        if database_manager is None:
            raise HTTPException(status_code=503, detail="Database manager not initialized")
        
        await database_manager.optimize_database()
        
        return {
            "success": True,
            "message": "Database optimization completed",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/database/backup")
async def backup_database():
    """Create a database backup"""
    try:
        if database_manager is None:
            raise HTTPException(status_code=503, detail="Database manager not initialized")
        
        backup_path = await database_manager.backup_database()
        
        return {
            "success": True,
            "backup_path": backup_path,
            "message": "Database backup created successfully",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error backing up database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/database/cleanup/{retention_days}")
async def cleanup_database(retention_days: int = 90):
    """Clean up old database records"""
    try:
        if database_manager is None:
            raise HTTPException(status_code=503, detail="Database manager not initialized")
        
        if retention_days < 1 or retention_days > 365:
            raise HTTPException(status_code=400, detail="Retention days must be between 1 and 365")
        
        deleted_count = await database_manager.cleanup_old_data(retention_days)
        
        return {
            "success": True,
            "deleted_records": deleted_count,
            "retention_days": retention_days,
            "message": f"Cleaned up {deleted_count} old records",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error cleaning up database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Advanced analytics endpoints
@app.get("/analytics/dashboard")
async def get_analytics_dashboard():
    """Get comprehensive analytics dashboard data"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get system status
        system_status = await scheduler_instance.get_system_status()
        
        # Get latest progress report
        progress_report = await scheduler_instance.progress_tracker.generate_minute_update()
        
        # Get recommendations
        recommendations = await scheduler_instance.progress_tracker.get_recommendations()
        
        # Get backup recommendations
        backup_recommendations = await scheduler_instance.backup_manager.get_backup_recommendations()
        
        # Combine all analytics
        dashboard = {
            "timestamp": datetime.now().isoformat(),
            "system_status": system_status,
            "real_time_metrics": progress_report.get('real_time_metrics', {}),
            "component_health": progress_report.get('component_health', {}),
            "alerts": progress_report.get('alerts', []),
            "trends": progress_report.get('trends', {}),
            "performance": progress_report.get('performance', {}),
            "cost": progress_report.get('cost', {}),
            "recommendations": {
                "system": recommendations,
                "backup": backup_recommendations
            }
        }
        
        return dashboard
        
    except Exception as e:
        logger.error(f"Error generating analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/performance/trends")
async def get_performance_trends():
    """Get performance trends over time"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get performance history
        performance_history = list(scheduler_instance.progress_tracker.performance_history)
        cost_history = list(scheduler_instance.progress_tracker.cost_history)
        
        # Format for visualization
        trends = {
            "timestamp": datetime.now().isoformat(),
            "performance_timeline": [
                {
                    "timestamp": entry[0].isoformat(),
                    "metrics": entry[1].__dict__
                }
                for entry in performance_history[-50:]  # Last 50 entries
            ],
            "cost_timeline": [
                {
                    "timestamp": entry[0].isoformat(),
                    "metrics": entry[1].__dict__
                }
                for entry in cost_history[-50:]  # Last 50 entries
            ]
        }
        
        return trends
        
    except Exception as e:
        logger.error(f"Error getting performance trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/efficiency")
async def get_efficiency_analysis():
    """Get detailed efficiency analysis"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get bot manager status
        bot_status = scheduler_instance.bot_manager.get_status_summary()
        
        # Calculate efficiency metrics
        efficiency_analysis = {
            "timestamp": datetime.now().isoformat(),
            "overall_efficiency": 0,
            "bot_efficiency": {},
            "task_efficiency": {},
            "time_optimization": {},
            "cost_efficiency": {}
        }
        
        # Bot efficiency analysis
        total_efficiency = 0
        active_bots = 0
        
        for bot_detail in bot_status.get('bots', {}).get('details', []):
            bot_id = bot_detail['id']
            performance = bot_detail['performance']
            used_hours = bot_detail['used_hours']
            available_hours = bot_detail['available_hours']
            
            total_hours = used_hours + available_hours
            utilization = used_hours / total_hours if total_hours > 0 else 0
            
            efficiency_analysis['bot_efficiency'][bot_id] = {
                "performance_score": performance,
                "utilization": utilization,
                "efficiency_rating": performance * utilization,
                "hours_used": used_hours,
                "hours_available": available_hours
            }
            
            total_efficiency += performance * utilization
            active_bots += 1
        
        efficiency_analysis['overall_efficiency'] = total_efficiency / active_bots if active_bots > 0 else 0
        
        # Time optimization analysis
        current_multiplier = bot_status.get('time_multiplier', 1.0)
        efficiency_analysis['time_optimization'] = {
            "current_multiplier": current_multiplier,
            "night_acceleration_active": current_multiplier > 1.0,
            "optimal_scheduling": current_multiplier >= 1.5
        }
        
        # Task efficiency
        tasks = bot_status.get('tasks', {})
        total_tasks = sum(tasks.values())
        
        efficiency_analysis['task_efficiency'] = {
            "queue_efficiency": 1 - (tasks.get('queued', 0) / max(total_tasks, 1)),
            "success_rate": tasks.get('completed', 0) / max(tasks.get('completed', 0) + tasks.get('failed', 0), 1),
            "throughput": tasks.get('running', 0) / max(bot_status.get('bots', {}).get('active', 1), 1)
        }
        
        return efficiency_analysis
        
    except Exception as e:
        logger.error(f"Error getting efficiency analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System monitoring endpoints
@app.get("/monitoring/alerts")
async def get_system_alerts():
    """Get current system alerts"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get real-time alerts from progress tracker
        progress_update = await scheduler_instance.progress_tracker.generate_minute_update()
        alerts = progress_update.get('alerts', [])
        
        # Get component health
        component_health = progress_update.get('component_health', {})
        
        # Add component health alerts
        for component, health in component_health.items():
            if health['status'] in ['warning', 'critical', 'error']:
                alerts.append({
                    'level': health['status'],
                    'component': component,
                    'message': health['message'],
                    'timestamp': health['last_check']
                })
        
        return {
            "timestamp": datetime.now().isoformat(),
            "alerts": alerts,
            "alert_counts": {
                "critical": len([a for a in alerts if a['level'] == 'critical']),
                "warning": len([a for a in alerts if a['level'] == 'warning']),
                "info": len([a for a in alerts if a['level'] == 'info']),
                "error": len([a for a in alerts if a['level'] == 'error'])
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting system alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitoring/health")
async def get_system_health():
    """Get comprehensive system health check"""
    try:
        scheduler_instance = get_scheduler()
        
        # Get component health
        progress_update = await scheduler_instance.progress_tracker.generate_minute_update()
        component_health = progress_update.get('component_health', {})
        
        # Overall health calculation
        health_scores = []
        for component, health in component_health.items():
            if health['status'] == 'healthy':
                health_scores.append(1.0)
            elif health['status'] == 'warning':
                health_scores.append(0.7)
            elif health['status'] == 'critical':
                health_scores.append(0.3)
            else:  # error
                health_scores.append(0.1)
        
        overall_health = sum(health_scores) / len(health_scores) if health_scores else 0
        
        # Health status
        if overall_health >= 0.9:
            health_status = "excellent"
        elif overall_health >= 0.7:
            health_status = "good"
        elif overall_health >= 0.5:
            health_status = "fair"
        elif overall_health >= 0.3:
            health_status = "poor"
        else:
            health_status = "critical"
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_health": overall_health,
            "health_status": health_status,
            "component_health": component_health,
            "system_metrics": progress_update.get('real_time_metrics', {}),
            "uptime": (datetime.now() - scheduler_instance.start_time).total_seconds() if hasattr(scheduler_instance, 'start_time') else 0
        }
        
    except Exception as e:
        logger.error(f"Error getting system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the service
    service_config = config.get('service', {})
    
    uvicorn.run(
        "main:app",
        host=service_config.get('host', '0.0.0.0'),
        port=service_config.get('port', 8500),
        reload=service_config.get('debug', False),
        log_level=config.get('logging', {}).get('level', 'info').lower()
    )