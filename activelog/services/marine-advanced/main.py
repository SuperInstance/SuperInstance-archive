"""
Marine Advanced Service
Advanced maritime operations and coordination hub
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
from enum import Enum
import json
import uuid

from marine_hub_integration import (
    marine_hub_integrator, MarineHubIntegrator,
    OperationType, MarineServiceStatus
)

logger = logging.getLogger(__name__)

class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class WeatherCondition(str, Enum):
    CALM = "calm"
    MODERATE = "moderate"
    ROUGH = "rough"
    SEVERE = "severe"
    STORM = "storm"

# Request/Response Models
class MarineOperationRequest(BaseModel):
    operation_type: OperationType
    parameters: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=0, le=5)

class WeatherAlert(BaseModel):
    alert_type: str
    severity: AlertSeverity
    affected_area: Dict[str, Any]  # Geographic bounds
    conditions: WeatherCondition
    wind_speed_knots: float
    wave_height_meters: float
    duration_hours: int
    recommendations: List[str] = Field(default_factory=list)

class VesselAlert(BaseModel):
    vessel_id: str
    alert_type: str
    severity: AlertSeverity
    message: str
    location: Optional[Dict[str, float]] = None
    requires_action: bool = True

class MarineAdvancedService:
    """Advanced maritime operations service"""
    
    def __init__(self):
        self.weather_alerts = {}
        self.vessel_alerts = {}
        self.coordination_logs = {}
        self.service_notifications = {}
        
        # Initialize marine hub integrator
        self.marine_hub = marine_hub_integrator
        
    async def initialize_service(self):
        """Initialize the marine advanced service"""
        # Start marine integration hub
        await self.marine_hub.start_integration_hub()
        logger.info("Marine Advanced Service initialized")
    
    async def shutdown_service(self):
        """Shutdown the marine advanced service"""
        await self.marine_hub.stop_integration_hub()
        logger.info("Marine Advanced Service shutdown")
    
    async def coordinate_marine_operation(self, request: MarineOperationRequest) -> Dict[str, Any]:
        """Coordinate marine operation across integrated services"""
        try:
            # Register operation with marine hub
            operation_id = await self.marine_hub.register_marine_operation(
                operation_type=request.operation_type,
                parameters=request.parameters,
                priority=request.priority
            )
            
            # Execute operation
            result = await self.marine_hub.execute_marine_operation(operation_id)
            
            # Log coordination activity
            await self._log_coordination_activity(
                "marine_operation",
                {
                    "operation_id": operation_id,
                    "operation_type": request.operation_type,
                    "result": result
                }
            )
            
            return {
                "operation_id": operation_id,
                "status": result.get("status", "unknown"),
                "result": result.get("result"),
                "service_used": result.get("service"),
                "execution_time": result.get("completed_at")
            }
            
        except Exception as e:
            logger.error(f"Failed to coordinate marine operation: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def issue_weather_alert(self, alert: WeatherAlert) -> str:
        """Issue weather alert to all marine services"""
        alert_id = str(uuid.uuid4())
        
        alert_data = {
            "alert_id": alert_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "affected_area": alert.affected_area,
            "conditions": alert.conditions,
            "wind_speed_knots": alert.wind_speed_knots,
            "wave_height_meters": alert.wave_height_meters,
            "duration_hours": alert.duration_hours,
            "recommendations": alert.recommendations,
            "issued_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=alert.duration_hours)
        }
        
        self.weather_alerts[alert_id] = alert_data
        
        # Broadcast to all marine services
        await self._broadcast_weather_alert(alert_data)
        
        # Coordinate response if severe weather
        if alert.severity in [AlertSeverity.ERROR, AlertSeverity.CRITICAL]:
            await self._coordinate_severe_weather_response(alert_data)
        
        return alert_id
    
    async def issue_vessel_alert(self, alert: VesselAlert) -> str:
        """Issue vessel-specific alert"""
        alert_id = str(uuid.uuid4())
        
        alert_data = {
            "alert_id": alert_id,
            "vessel_id": alert.vessel_id,
            "alert_type": alert.alert_type,
            "severity": alert.severity,
            "message": alert.message,
            "location": alert.location,
            "requires_action": alert.requires_action,
            "issued_at": datetime.utcnow(),
            "status": "active"
        }
        
        self.vessel_alerts[alert_id] = alert_data
        
        # Send to appropriate services
        await self._send_vessel_alert(alert_data)
        
        # Coordinate emergency response if critical
        if alert.severity == AlertSeverity.CRITICAL:
            await self._coordinate_emergency_response(alert_data)
        
        return alert_id
    
    async def get_maritime_situation_awareness(self) -> Dict[str, Any]:
        """Get comprehensive maritime situation awareness"""
        # Get service statuses
        services_status = await self.marine_hub.get_marine_services_status()
        
        # Get operations summary
        operations_summary = await self.marine_hub.get_marine_operations_summary()
        
        # Analyze current alerts
        active_weather_alerts = [
            alert for alert in self.weather_alerts.values()
            if alert["expires_at"] > datetime.utcnow()
        ]
        
        active_vessel_alerts = [
            alert for alert in self.vessel_alerts.values()
            if alert["status"] == "active"
        ]
        
        # Calculate risk assessment
        risk_assessment = await self._calculate_maritime_risk_assessment(
            active_weather_alerts,
            active_vessel_alerts,
            services_status
        )
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "services_status": services_status,
            "operations_summary": operations_summary,
            "active_alerts": {
                "weather_alerts": len(active_weather_alerts),
                "vessel_alerts": len(active_vessel_alerts),
                "critical_alerts": len([a for a in active_weather_alerts + active_vessel_alerts if a.get("severity") == AlertSeverity.CRITICAL])
            },
            "risk_assessment": risk_assessment,
            "coordination_status": await self._get_coordination_status()
        }
    
    async def handle_service_notification(self, service_name: str, notification: Dict[str, Any]) -> Dict[str, Any]:
        """Handle notifications from integrated marine services"""
        notification_id = str(uuid.uuid4())
        
        notification_record = {
            "notification_id": notification_id,
            "service_name": service_name,
            "notification": notification,
            "received_at": datetime.utcnow(),
            "processed": False
        }
        
        self.service_notifications[notification_id] = notification_record
        
        # Process notification based on type
        event_type = notification.get("event_type", "unknown")
        
        if event_type == "emergency_declared":
            await self._handle_emergency_notification(notification)
        elif event_type == "vessel_registered":
            await self._handle_vessel_registration_notification(notification)
        elif event_type == "navigation_plan_created":
            await self._handle_navigation_plan_notification(notification)
        elif event_type == "fishing_trip_completed":
            await self._handle_fishing_trip_notification(notification)
        elif event_type == "maintenance_required":
            await self._handle_maintenance_notification(notification)
        
        notification_record["processed"] = True
        
        return {
            "notification_id": notification_id,
            "processed": True,
            "response_actions": notification_record.get("response_actions", [])
        }
    
    async def coordinate_search_and_rescue(self, incident_details: Dict[str, Any]) -> str:
        """Coordinate search and rescue operation"""
        sar_operation_id = str(uuid.uuid4())
        
        # Register SAR operation
        operation_id = await self.marine_hub.register_marine_operation(
            operation_type=OperationType.EMERGENCY,
            parameters={
                "sar_operation_id": sar_operation_id,
                "incident_type": "search_and_rescue",
                "location": incident_details.get("location", {}),
                "vessel_in_distress": incident_details.get("vessel_id"),
                "persons_in_water": incident_details.get("persons_count", 0),
                "weather_conditions": incident_details.get("weather", {}),
                "available_resources": incident_details.get("resources", []),
                "urgency": "critical"
            },
            priority=0  # Highest priority
        )
        
        # Execute SAR coordination
        await self.marine_hub.execute_marine_operation(operation_id)
        
        # Log SAR operation
        await self._log_coordination_activity(
            "search_and_rescue",
            {
                "sar_operation_id": sar_operation_id,
                "operation_id": operation_id,
                "incident_details": incident_details
            }
        )
        
        return sar_operation_id
    
    async def manage_fleet_coordination(self, fleet_id: str, coordination_type: str, 
                                      parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Manage fleet-wide coordination activities"""
        coordination_id = str(uuid.uuid4())
        
        # Determine operation type
        operation_type_map = {
            "formation_change": OperationType.FLEET_COMMAND,
            "joint_operation": OperationType.LOGISTICS,
            "emergency_response": OperationType.EMERGENCY,
            "resource_sharing": OperationType.LOGISTICS
        }
        
        operation_type = operation_type_map.get(coordination_type, OperationType.FLEET_COMMAND)
        
        # Register fleet coordination operation
        operation_id = await self.marine_hub.register_marine_operation(
            operation_type=operation_type,
            parameters={
                "coordination_id": coordination_id,
                "fleet_id": fleet_id,
                "coordination_type": coordination_type,
                **parameters
            }
        )
        
        # Execute coordination
        result = await self.marine_hub.execute_marine_operation(operation_id)
        
        # Log coordination
        await self._log_coordination_activity(
            "fleet_coordination",
            {
                "coordination_id": coordination_id,
                "fleet_id": fleet_id,
                "coordination_type": coordination_type,
                "result": result
            }
        )
        
        return {
            "coordination_id": coordination_id,
            "operation_id": operation_id,
            "status": result.get("status"),
            "fleet_id": fleet_id,
            "coordination_type": coordination_type
        }
    
    # Helper methods
    
    async def _log_coordination_activity(self, activity_type: str, details: Dict[str, Any]):
        """Log coordination activity"""
        log_id = str(uuid.uuid4())
        
        log_entry = {
            "log_id": log_id,
            "activity_type": activity_type,
            "details": details,
            "timestamp": datetime.utcnow(),
            "coordinator": "marine-advanced"
        }
        
        self.coordination_logs[log_id] = log_entry
        logger.info(f"Logged coordination activity: {activity_type}")
    
    async def _broadcast_weather_alert(self, alert_data: Dict[str, Any]):
        """Broadcast weather alert to all marine services"""
        services_status = await self.marine_hub.get_marine_services_status()
        
        for service_name, service_info in services_status["services"].items():
            if service_info["service_info"]["status"] == MarineServiceStatus.HEALTHY:
                try:
                    # Send weather alert to service
                    await self.marine_hub.register_marine_operation(
                        operation_type=OperationType.EMERGENCY,
                        parameters={
                            "alert_type": "weather_alert",
                            "alert_data": alert_data
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to send weather alert to {service_name}: {e}")
    
    async def _coordinate_severe_weather_response(self, alert_data: Dict[str, Any]):
        """Coordinate response to severe weather"""
        # Register severe weather response operation
        await self.marine_hub.register_marine_operation(
            operation_type=OperationType.EMERGENCY,
            parameters={
                "emergency_type": "severe_weather",
                "alert_data": alert_data,
                "response_actions": [
                    "Notify all vessels in affected area",
                    "Recommend course alterations",
                    "Prepare emergency services",
                    "Monitor vessel positions closely"
                ]
            },
            priority=0
        )
    
    async def _send_vessel_alert(self, alert_data: Dict[str, Any]):
        """Send vessel alert to appropriate services"""
        # Determine which services need the alert
        if alert_data["alert_type"] in ["navigation", "position", "course"]:
            target_service = "cocapn"
        elif alert_data["alert_type"] in ["mechanical", "crew", "inspection"]:
            target_service = "capitaine"
        elif alert_data["alert_type"] in ["fishing", "catch", "quota"]:
            target_service = "marine-fishing"
        else:
            target_service = None  # Send to all
        
        # Send alert
        await self.marine_hub.register_marine_operation(
            operation_type=OperationType.EMERGENCY,
            parameters={
                "alert_type": "vessel_alert",
                "vessel_id": alert_data["vessel_id"],
                "alert_data": alert_data,
                "target_service": target_service
            }
        )
    
    async def _coordinate_emergency_response(self, alert_data: Dict[str, Any]):
        """Coordinate emergency response for critical vessel alert"""
        await self.marine_hub.handle_marine_emergency(
            emergency_type=alert_data["alert_type"],
            vessel_id=alert_data["vessel_id"],
            location=alert_data.get("location", {}),
            details={
                "alert_message": alert_data["message"],
                "severity": alert_data["severity"],
                "requires_action": alert_data["requires_action"]
            }
        )
    
    async def _calculate_maritime_risk_assessment(self, weather_alerts: List[Dict], 
                                                vessel_alerts: List[Dict],
                                                services_status: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall maritime risk assessment"""
        risk_factors = {
            "weather_risk": 0,
            "operational_risk": 0,
            "service_risk": 0,
            "overall_risk": 0
        }
        
        # Weather risk assessment
        critical_weather = len([a for a in weather_alerts if a["severity"] == AlertSeverity.CRITICAL])
        severe_weather = len([a for a in weather_alerts if a["severity"] == AlertSeverity.ERROR])
        risk_factors["weather_risk"] = min(100, (critical_weather * 40) + (severe_weather * 20))
        
        # Operational risk assessment
        critical_vessel = len([a for a in vessel_alerts if a["severity"] == AlertSeverity.CRITICAL])
        emergency_vessel = len([a for a in vessel_alerts if a["severity"] == AlertSeverity.ERROR])
        risk_factors["operational_risk"] = min(100, (critical_vessel * 30) + (emergency_vessel * 15))
        
        # Service risk assessment
        total_services = services_status["total_services"]
        healthy_services = services_status["healthy_services"]
        service_availability = healthy_services / total_services if total_services > 0 else 1
        risk_factors["service_risk"] = max(0, (1 - service_availability) * 100)
        
        # Overall risk (weighted average)
        risk_factors["overall_risk"] = (
            risk_factors["weather_risk"] * 0.4 +
            risk_factors["operational_risk"] * 0.4 +
            risk_factors["service_risk"] * 0.2
        )
        
        # Risk level classification
        overall_risk = risk_factors["overall_risk"]
        if overall_risk >= 80:
            risk_level = "CRITICAL"
        elif overall_risk >= 60:
            risk_level = "HIGH"
        elif overall_risk >= 40:
            risk_level = "MODERATE"
        elif overall_risk >= 20:
            risk_level = "LOW"
        else:
            risk_level = "MINIMAL"
        
        return {
            **risk_factors,
            "risk_level": risk_level,
            "assessment_time": datetime.utcnow().isoformat()
        }
    
    async def _get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status"""
        recent_logs = [
            log for log in self.coordination_logs.values()
            if log["timestamp"] > datetime.utcnow() - timedelta(hours=24)
        ]
        
        return {
            "active_coordinations": len(recent_logs),
            "last_coordination": max([log["timestamp"] for log in recent_logs]) if recent_logs else None,
            "coordination_types": list(set([log["activity_type"] for log in recent_logs])),
            "success_rate": 100.0  # Would calculate based on actual results
        }
    
    async def _handle_emergency_notification(self, notification: Dict[str, Any]):
        """Handle emergency notification from service"""
        # Escalate to SAR if needed
        if notification.get("emergency_type") in ["man_overboard", "vessel_sinking", "medical_emergency"]:
            await self.coordinate_search_and_rescue(notification)
    
    async def _handle_vessel_registration_notification(self, notification: Dict[str, Any]):
        """Handle vessel registration notification"""
        # Log new vessel registration
        await self._log_coordination_activity(
            "vessel_registration",
            {
                "vessel_id": notification.get("vessel_id"),
                "vessel_name": notification.get("vessel_name"),
                "vessel_class": notification.get("vessel_class")
            }
        )
    
    async def _handle_navigation_plan_notification(self, notification: Dict[str, Any]):
        """Handle navigation plan notification"""
        # Monitor navigation plan execution
        await self._log_coordination_activity(
            "navigation_monitoring",
            {
                "plan_id": notification.get("plan_id"),
                "vessel_id": notification.get("vessel_id"),
                "route_summary": notification.get("route_summary")
            }
        )
    
    async def _handle_fishing_trip_notification(self, notification: Dict[str, Any]):
        """Handle fishing trip notification"""
        # Log fishing activity
        await self._log_coordination_activity(
            "fishing_coordination",
            {
                "trip_id": notification.get("trip_id"),
                "vessel_id": notification.get("vessel_id"),
                "catch_summary": notification.get("catch_summary")
            }
        )
    
    async def _handle_maintenance_notification(self, notification: Dict[str, Any]):
        """Handle maintenance notification"""
        # Coordinate maintenance scheduling
        await self.marine_hub.register_marine_operation(
            operation_type=OperationType.LOGISTICS,
            parameters={
                "operation_type": "maintenance_coordination",
                "vessel_id": notification.get("vessel_id"),
                "maintenance_type": notification.get("maintenance_type"),
                "priority": notification.get("priority", "normal")
            }
        )

# FastAPI App
app = FastAPI(
    title="Marine Advanced Operations Hub",
    description="Advanced maritime operations and coordination service",
    version="1.0.0"
)

service = MarineAdvancedService()

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await service.initialize_service()

@app.on_event("shutdown")
async def shutdown_event():
    await service.shutdown_service()

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "marine-advanced",
        "timestamp": datetime.utcnow().isoformat(),
        "marine_hub_status": "integrated"
    }

# Marine operations endpoints
@app.post("/api/marine/operation")
async def coordinate_marine_operation(request: MarineOperationRequest):
    result = await service.coordinate_marine_operation(request)
    return {"success": True, **result}

@app.post("/api/alerts/weather")
async def issue_weather_alert(alert: WeatherAlert):
    alert_id = await service.issue_weather_alert(alert)
    return {"success": True, "alert_id": alert_id}

@app.post("/api/alerts/vessel")
async def issue_vessel_alert(alert: VesselAlert):
    alert_id = await service.issue_vessel_alert(alert)
    return {"success": True, "alert_id": alert_id}

@app.get("/api/situation/awareness")
async def get_maritime_situation_awareness():
    result = await service.get_maritime_situation_awareness()
    return {"success": True, **result}

@app.post("/api/{service_name}/notifications")
async def handle_service_notification(service_name: str, notification: Dict[str, Any]):
    result = await service.handle_service_notification(service_name, notification)
    return {"success": True, **result}

@app.post("/api/sar/coordinate")
async def coordinate_search_and_rescue(incident_details: Dict[str, Any]):
    sar_id = await service.coordinate_search_and_rescue(incident_details)
    return {"success": True, "sar_operation_id": sar_id}

@app.post("/api/fleet/{fleet_id}/coordinate/{coordination_type}")
async def manage_fleet_coordination(fleet_id: str, coordination_type: str, parameters: Dict[str, Any]):
    result = await service.manage_fleet_coordination(fleet_id, coordination_type, parameters)
    return {"success": True, **result}

# Status endpoints
@app.get("/api/services/status")
async def get_services_status():
    result = await service.marine_hub.get_marine_services_status()
    return {"success": True, **result}

@app.get("/api/operations/summary")
async def get_operations_summary():
    result = await service.marine_hub.get_marine_operations_summary()
    return {"success": True, **result}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8025)