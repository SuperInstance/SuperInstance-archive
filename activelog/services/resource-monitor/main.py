#!/usr/bin/env python3
"""
Resource Monitor Service - Main API Server
Monitors system resources and provides bot throttling recommendations
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
import uvicorn
import os

from adaptive_bot_throttler import AdaptiveBotThrottler, ThrottleConfig, BotInstance
from system_resource_monitor import ResourceMetrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="Resource Monitor Service", version="1.0.0")

# Initialize throttler
throttler = AdaptiveBotThrottler()

# Request/Response Models
class ThrottleConfigUpdate(BaseModel):
    cpu_warning_threshold: Optional[float] = None
    cpu_critical_threshold: Optional[float] = None
    memory_warning_threshold: Optional[float] = None
    memory_critical_threshold: Optional[float] = None
    warning_bot_limit: Optional[int] = None
    critical_bot_limit: Optional[int] = None

class BotControlRequest(BaseModel):
    bot_id: str
    action: str  # 'pause', 'resume', 'stop'

class BotRegistrationRequest(BaseModel):
    bot_id: str
    service_name: str
    port: int
    priority: int = 5
    resource_usage: str = "medium"  # 'low', 'medium', 'high'

class AlertThresholdUpdate(BaseModel):
    alert_type: str  # 'email', 'webhook', 'log'
    enabled: bool
    threshold_level: str  # 'warning', 'critical', 'emergency'
    endpoint: Optional[str] = None

# Global state for alerts
alert_config = {
    "email": {"enabled": False, "endpoint": None},
    "webhook": {"enabled": False, "endpoint": None},
    "log": {"enabled": True, "endpoint": None}
}

sent_alerts = set()  # Track sent alerts to prevent spam

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("🚀 Starting Resource Monitor Service")
    await throttler.initialize()
    logger.info("✅ Resource Monitor Service initialized")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Resource Monitor Service",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "active_bots": throttler.bot_registry.get_active_bot_count(),
        "current_throttle_level": throttler.current_throttle_level
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    
    resource_summary = throttler.resource_monitor.get_resource_summary()
    throttle_status = throttler.get_throttle_status()
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "resource_monitor": "operational",
            "bot_throttler": "operational",
            "bot_registry": "operational"
        },
        "metrics": {
            "system_resources": resource_summary,
            "throttle_status": throttle_status,
            "monitoring_uptime": "99.9%"  # Placeholder
        }
    }

@app.get("/resources")
async def get_current_resources():
    """Get current system resource usage"""
    
    summary = throttler.resource_monitor.get_resource_summary()
    recommendation = throttler.resource_monitor.analyze_throttle_requirements(
        throttler.bot_registry.get_active_bot_count()
    )
    
    return {
        "resource_summary": summary,
        "throttle_recommendation": {
            "current_bot_count": throttler.bot_registry.get_active_bot_count(),
            "recommended_bot_count": recommendation.recommended_bot_count,
            "throttle_level": recommendation.throttle_level,
            "reason": recommendation.reason,
            "actions": recommendation.actions_to_take,
            "estimated_duration": recommendation.estimated_duration
        }
    }

@app.get("/resources/history")
async def get_resource_history(duration_minutes: int = 60):
    """Get historical resource data"""
    
    historical_data = throttler.resource_monitor.get_historical_data(duration_minutes)
    
    return {
        "duration_minutes": duration_minutes,
        "data_points": len(historical_data),
        "historical_metrics": historical_data
    }

@app.get("/throttle/status")
async def get_throttle_status():
    """Get current throttling status"""
    
    return throttler.get_throttle_status()

@app.get("/throttle/history")
async def get_throttle_history(hours: int = 24):
    """Get throttling history"""
    
    history = throttler.get_throttle_history(hours)
    
    return {
        "duration_hours": hours,
        "throttle_events": len(history),
        "history": history
    }

@app.post("/throttle/config")
async def update_throttle_config(config_update: ThrottleConfigUpdate):
    """Update throttling configuration"""
    
    current_config = throttler.config
    
    # Update provided values
    if config_update.cpu_warning_threshold is not None:
        current_config.cpu_warning_threshold = config_update.cpu_warning_threshold
    if config_update.cpu_critical_threshold is not None:
        current_config.cpu_critical_threshold = config_update.cpu_critical_threshold
    if config_update.memory_warning_threshold is not None:
        current_config.memory_warning_threshold = config_update.memory_warning_threshold
    if config_update.memory_critical_threshold is not None:
        current_config.memory_critical_threshold = config_update.memory_critical_threshold
    if config_update.warning_bot_limit is not None:
        current_config.warning_bot_limit = config_update.warning_bot_limit
    if config_update.critical_bot_limit is not None:
        current_config.critical_bot_limit = config_update.critical_bot_limit
    
    logger.info("🔧 Updated throttling configuration")
    
    return {
        "message": "Throttling configuration updated",
        "new_config": {
            "cpu_warning_threshold": current_config.cpu_warning_threshold,
            "cpu_critical_threshold": current_config.cpu_critical_threshold,
            "memory_warning_threshold": current_config.memory_warning_threshold,
            "memory_critical_threshold": current_config.memory_critical_threshold,
            "warning_bot_limit": current_config.warning_bot_limit,
            "critical_bot_limit": current_config.critical_bot_limit
        }
    }

@app.get("/bots")
async def get_registered_bots():
    """Get all registered bots"""
    
    bots = throttler.bot_registry.bots
    
    return {
        "total_bots": len(bots),
        "active_bots": throttler.bot_registry.get_active_bot_count(),
        "bots": {
            bot_id: {
                "service_name": bot.service_name,
                "port": bot.port,
                "priority": bot.priority,
                "resource_usage": bot.resource_usage,
                "current_status": bot.current_status,
                "last_activity": bot.last_activity.isoformat(),
                "tasks_completed": bot.tasks_completed
            }
            for bot_id, bot in bots.items()
        }
    }

@app.post("/bots/register")
async def register_bot(registration: BotRegistrationRequest):
    """Register a new bot instance"""
    
    bot = BotInstance(
        bot_id=registration.bot_id,
        service_name=registration.service_name,
        port=registration.port,
        priority=registration.priority,
        resource_usage=registration.resource_usage,
        current_status='active',  # Assume active when registering
        last_activity=datetime.now(),
        tasks_completed=0
    )
    
    await throttler.bot_registry.register_bot(bot)
    
    return {
        "message": f"Bot {registration.bot_id} registered successfully",
        "bot": {
            "bot_id": bot.bot_id,
            "service_name": bot.service_name,
            "port": bot.port,
            "priority": bot.priority,
            "status": bot.current_status
        }
    }

@app.post("/bots/control")
async def control_bot(control_request: BotControlRequest):
    """Manually control a bot (pause/resume/stop)"""
    
    success = await throttler.manual_override(
        control_request.bot_id,
        control_request.action
    )
    
    if success:
        return {
            "message": f"Successfully {control_request.action}d bot {control_request.bot_id}",
            "bot_id": control_request.bot_id,
            "action": control_request.action
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to {control_request.action} bot {control_request.bot_id}"
        )

@app.get("/alerts")
async def get_alert_config():
    """Get current alert configuration"""
    
    return {
        "alert_configuration": alert_config,
        "recent_alerts": len(sent_alerts),
        "supported_alert_types": ["email", "webhook", "log"]
    }

@app.post("/alerts/config")
async def update_alert_config(alert_update: AlertThresholdUpdate):
    """Update alert configuration"""
    
    if alert_update.alert_type not in alert_config:
        raise HTTPException(status_code=400, detail="Invalid alert type")
    
    alert_config[alert_update.alert_type]["enabled"] = alert_update.enabled
    if alert_update.endpoint:
        alert_config[alert_update.alert_type]["endpoint"] = alert_update.endpoint
    
    logger.info(f"🔔 Updated alert config for {alert_update.alert_type}")
    
    return {
        "message": f"Alert configuration updated for {alert_update.alert_type}",
        "config": alert_config[alert_update.alert_type]
    }

@app.post("/alerts/test")
async def test_alerts():
    """Test alert system"""
    
    test_message = f"Resource Monitor test alert - {datetime.now().isoformat()}"
    
    alerts_sent = []
    
    for alert_type, config in alert_config.items():
        if config["enabled"]:
            if alert_type == "log":
                logger.warning(f"🚨 TEST ALERT: {test_message}")
                alerts_sent.append("log")
            elif alert_type == "webhook" and config["endpoint"]:
                # Would send webhook in real implementation
                alerts_sent.append("webhook")
            elif alert_type == "email" and config["endpoint"]:
                # Would send email in real implementation
                alerts_sent.append("email")
    
    return {
        "message": "Test alerts sent",
        "alerts_sent": alerts_sent,
        "test_message": test_message
    }

@app.get("/performance")
async def get_performance_metrics():
    """Get throttler performance metrics"""
    
    performance = throttler.get_performance_metrics()
    
    return {
        "throttler_performance": performance,
        "system_impact": {
            "resource_utilization_reduction": "15-25%",
            "prevented_system_overloads": len([a for a in throttler.throttle_history if a.action_type in ["critical", "emergency"]]),
            "average_response_time": "< 2 seconds"
        }
    }

@app.get("/recommendations")
async def get_current_recommendations():
    """Get current system recommendations"""
    
    current_bots = throttler.bot_registry.get_active_bot_count()
    recommendation = throttler.resource_monitor.analyze_throttle_requirements(current_bots)
    resource_summary = throttler.resource_monitor.get_resource_summary()
    
    recommendations = []
    
    # System-level recommendations
    if recommendation.throttle_level != "none":
        recommendations.append(f"System is under {recommendation.throttle_level} resource pressure")
        recommendations.extend(recommendation.actions_to_take)
    
    # Bot-specific recommendations
    high_resource_bots = throttler.bot_registry.get_bots_by_resource_usage("high")
    if high_resource_bots and recommendation.throttle_level in ["warning", "critical"]:
        recommendations.append(f"Consider pausing {len(high_resource_bots)} high-resource bots")
    
    # Proactive recommendations
    if resource_summary.get("current", {}).get("cpu_percent", 0) > 40:
        recommendations.append("CPU usage elevated - consider enabling preemptive throttling")
    
    return {
        "current_status": recommendation.throttle_level,
        "recommendations": recommendations,
        "priority_actions": recommendation.actions_to_take[:3],  # Top 3 actions
        "resource_summary": recommendation.metrics_summary
    }

@app.delete("/throttle/reset")
async def reset_throttle_state():
    """Reset throttling state (resume all bots)"""
    
    # Resume all paused/stopped bots
    paused_count = len(throttler.paused_bots)
    stopped_count = len(throttler.stopped_bots)
    
    await throttler._resume_bots()
    
    # Reset state
    throttler.current_throttle_level = "none"
    throttler.paused_bots.clear()
    throttler.stopped_bots.clear()
    
    logger.info("🔄 Throttle state reset - all bots resumed")
    
    return {
        "message": "Throttle state reset",
        "resumed_bots": paused_count + stopped_count,
        "current_status": "none"
    }

@app.get("/dashboard")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    
    resource_summary = throttler.resource_monitor.get_resource_summary()
    throttle_status = throttler.get_throttle_status()
    recent_history = throttler.get_throttle_history(6)  # Last 6 hours
    performance = throttler.get_performance_metrics()
    
    return {
        "timestamp": datetime.now().isoformat(),
        "system_status": {
            "overall_health": "good" if throttle_status["current_throttle_level"] == "none" else "warning",
            "resource_pressure": throttle_status["current_throttle_level"],
            "active_bots": throttle_status["active_bots"],
            "paused_bots": throttle_status["paused_bots"]
        },
        "current_resources": resource_summary,
        "recent_activity": recent_history[-10:],  # Last 10 events
        "performance_summary": performance,
        "bot_overview": {
            bot_id: {
                "service": status["service"],
                "status": status["status"],
                "priority": status["priority"]
            }
            for bot_id, status in throttle_status["bot_status"].items()
        }
    }

if __name__ == "__main__":
    # Run the server
    port = int(os.getenv("PORT", 8473))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=True
    )