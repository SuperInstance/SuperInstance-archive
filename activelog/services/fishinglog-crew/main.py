"""
FishingLog Crew Management Service
Comprehensive crew management system for fishing vessels

Port: 8375
Features:
- Crew invitation and management
- Role-based permissions
- Shared navigation views
- Fish count tracking
- Watch alarms and attention monitoring
- Escalating alarm systems
- Captain override controls
- Task management
- Shift scheduling
- Crew share calculator
- Safety drill tracking
"""

import asyncio
import logging
import os
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uuid

# Import all modules
from crew.crew_management import CrewManager, CrewRole, InvitationStatus
from roles.permissions import PermissionManager, Permission, PermissionScope, AccessLevel
from navigation.shared_navigation import SharedNavigationManager, DisplayMode, NavigationDataType
from alarms.watch_alarms import WatchAlarmManager, AlarmType, AlarmLevel, OverrideReason
from tasks.task_management import TaskManager, TaskCategory, TaskPriority, TaskStatus
from scheduling.shift_scheduling import ShiftScheduler, ShiftType, ShiftStatus
from shares.share_calculator import ShareCalculator, ShareType, DeductionType, BonusType
from safety.drill_tracking import DrillTracker, DrillType, DrillStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="FishingLog Crew Management Service",
    description="Comprehensive crew management system for fishing vessels",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
crew_manager: Optional[CrewManager] = None
permission_manager: Optional[PermissionManager] = None
navigation_manager: Optional[SharedNavigationManager] = None
alarm_manager: Optional[WatchAlarmManager] = None
task_manager: Optional[TaskManager] = None
shift_scheduler: Optional[ShiftScheduler] = None
share_calculator: Optional[ShareCalculator] = None
drill_tracker: Optional[DrillTracker] = None

# WebSocket connections
websocket_connections: Dict[str, WebSocket] = {}


# Pydantic models
class CrewInvitationRequest(BaseModel):
    vessel_id: str
    email: str
    role: str
    message: Optional[str] = None


class AcceptInvitationRequest(BaseModel):
    invitation_token: str
    name: str
    phone: str
    certifications: List[str] = []


class TaskCreateRequest(BaseModel):
    title: str
    description: str
    category: str
    priority: str
    vessel_id: str
    trip_id: Optional[str] = None
    due_date: Optional[str] = None
    assigned_to: Optional[str] = None


class ShiftCreateRequest(BaseModel):
    vessel_id: str
    shift_type: str
    scheduled_start: str
    duration_hours: float
    required_role: str
    trip_id: Optional[str] = None


class ShareCalculationRequest(BaseModel):
    trip_id: str
    scheme_id: str
    crew_assignments: List[Dict[str, Any]]
    trip_expenses: Optional[Dict[str, float]] = None


class DrillScheduleRequest(BaseModel):
    vessel_id: str
    drill_type: str
    scheduled_date: str
    scenario_description: str
    objectives: List[str]
    trip_id: Optional[str] = None


class NavigationUpdateRequest(BaseModel):
    data_type: str
    data: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """Initialize all managers on startup"""
    global crew_manager, permission_manager, navigation_manager, alarm_manager
    global task_manager, shift_scheduler, share_calculator, drill_tracker
    
    logger.info("Starting FishingLog Crew Management Service")
    
    # Initialize managers
    permission_manager = PermissionManager()
    crew_manager = CrewManager(permission_manager)
    navigation_manager = SharedNavigationManager(crew_manager, permission_manager)
    alarm_manager = WatchAlarmManager(crew_manager, permission_manager)
    task_manager = TaskManager(crew_manager, permission_manager)
    shift_scheduler = ShiftScheduler(crew_manager, permission_manager)
    share_calculator = ShareCalculator(crew_manager, permission_manager)
    drill_tracker = DrillTracker(crew_manager, permission_manager)
    
    logger.info("All managers initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down FishingLog Crew Management Service")


# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "fishinglog-crew",
        "port": 8375,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# WebSocket connection management
@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    await websocket.accept()
    websocket_connections[connection_id] = websocket
    
    # Register with all managers for real-time updates
    navigation_manager.register_websocket(connection_id, websocket)
    alarm_manager.register_websocket(connection_id, websocket)
    task_manager.register_websocket(connection_id, websocket)
    shift_scheduler.register_websocket(connection_id, websocket)
    drill_tracker.register_websocket(connection_id, websocket)
    
    logger.info(f"WebSocket connection {connection_id} established")
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection {connection_id} disconnected")
    finally:
        # Cleanup
        if connection_id in websocket_connections:
            del websocket_connections[connection_id]
        
        # Unregister from managers
        navigation_manager.unregister_websocket(connection_id)
        alarm_manager.unregister_websocket(connection_id)
        task_manager.unregister_websocket(connection_id)
        shift_scheduler.unregister_websocket(connection_id)
        drill_tracker.unregister_websocket(connection_id)


# Crew Management Endpoints
@app.post("/crew/invite")
async def invite_crew_member(request: CrewInvitationRequest):
    """Invite a new crew member"""
    try:
        role = CrewRole(request.role)
        invitation_id = await crew_manager.invite_crew_member(
            vessel_id=request.vessel_id,
            inviter_id="system",  # In real implementation, get from auth
            email=request.email,
            proposed_role=role,
            message=request.message
        )
        
        if invitation_id:
            return {"success": True, "invitation_id": invitation_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create invitation")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")
    except Exception as e:
        logger.error(f"Failed to invite crew member: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/crew/accept-invitation")
async def accept_invitation(request: AcceptInvitationRequest):
    """Accept crew invitation"""
    try:
        member_id = await crew_manager.accept_invitation(
            invitation_token=request.invitation_token,
            user_details={
                "name": request.name,
                "phone": request.phone,
                "certifications": request.certifications
            }
        )
        
        if member_id:
            return {"success": True, "member_id": member_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to accept invitation")
            
    except Exception as e:
        logger.error(f"Failed to accept invitation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/crew/vessel/{vessel_id}")
async def get_vessel_crew(vessel_id: str):
    """Get all crew members for a vessel"""
    try:
        crew = await crew_manager.get_vessel_crew(vessel_id)
        return {"crew": crew}
    except Exception as e:
        logger.error(f"Failed to get vessel crew: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Navigation Endpoints
@app.post("/navigation/register-station")
async def register_navigation_station(member_id: str, role: str, display_mode: str):
    """Register navigation station"""
    try:
        crew_role = CrewRole(role)
        display = DisplayMode(display_mode)
        
        success = await navigation_manager.register_station(
            member_id=member_id,
            role=crew_role,
            display_mode=display
        )
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to register navigation station: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/navigation/update")
async def update_navigation_data(request: NavigationUpdateRequest, source_station: str):
    """Update navigation data"""
    try:
        data_type = NavigationDataType(request.data_type)
        
        await navigation_manager.update_navigation_data(
            data_type=data_type,
            data=request.data,
            source_station=source_station
        )
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to update navigation data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/navigation/fish-count")
async def add_fish_count(trip_id: str, species: str, count: int, weight: Optional[float] = None):
    """Add fish count"""
    try:
        success = await navigation_manager.add_fish_count(
            trip_id=trip_id,
            species=species,
            count=count,
            weight=weight
        )
        
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to add fish count: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Alarm Management Endpoints
@app.post("/alarms/start-watch")
async def start_watch(crew_member_id: str, vessel_id: str, duration: Optional[int] = None):
    """Start a watch session"""
    try:
        watch_id = await alarm_manager.start_watch(
            crew_member_id=crew_member_id,
            vessel_id=vessel_id,
            scheduled_duration=duration
        )
        
        if watch_id:
            return {"success": True, "watch_id": watch_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to start watch")
            
    except Exception as e:
        logger.error(f"Failed to start watch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/alarms/end-watch/{watch_id}")
async def end_watch(watch_id: str, ended_by: str):
    """End a watch session"""
    try:
        success = await alarm_manager.end_watch(watch_id, ended_by)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to end watch: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/alarms/respond/{alarm_id}")
async def respond_to_alarm(alarm_id: str, responder_id: str, message: Optional[str] = None):
    """Respond to an alarm"""
    try:
        success = await alarm_manager.respond_to_alarm(alarm_id, responder_id, message)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to respond to alarm: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/alarms/override/{alarm_id}")
async def override_alarm(alarm_id: str, override_by: str, reason: str, notes: Optional[str] = None):
    """Override an alarm (captain only)"""
    try:
        override_reason = OverrideReason(reason)
        success = await alarm_manager.override_alarm(alarm_id, override_by, override_reason, notes)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to override alarm: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Task Management Endpoints
@app.post("/tasks")
async def create_task(request: TaskCreateRequest):
    """Create a new task"""
    try:
        category = TaskCategory(request.category)
        priority = TaskPriority(request.priority)
        
        due_date = None
        if request.due_date:
            due_date = datetime.fromisoformat(request.due_date.replace('Z', '+00:00'))
        
        task_id = await task_manager.create_task(
            title=request.title,
            description=request.description,
            category=category,
            priority=priority,
            vessel_id=request.vessel_id,
            created_by="system",
            trip_id=request.trip_id,
            due_date=due_date,
            assigned_to=request.assigned_to
        )
        
        if task_id:
            return {"success": True, "task_id": task_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create task")
            
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/tasks/user/{user_id}")
async def get_user_tasks(user_id: str, status: Optional[str] = None):
    """Get tasks for a user"""
    try:
        status_filter = None
        if status:
            status_filter = [TaskStatus(status)]
        
        tasks = task_manager.get_tasks_for_user(user_id, status_filter)
        return {"tasks": tasks}
    except Exception as e:
        logger.error(f"Failed to get user tasks: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/tasks/{task_id}/start")
async def start_task(task_id: str, user_id: str):
    """Start working on a task"""
    try:
        success = await task_manager.start_task(task_id, user_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to start task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/tasks/{task_id}/complete")
async def complete_task(task_id: str, user_id: str, notes: Optional[str] = None):
    """Complete a task"""
    try:
        success = await task_manager.complete_task(task_id, user_id, notes)
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to complete task: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Shift Scheduling Endpoints
@app.post("/shifts")
async def create_shift(request: ShiftCreateRequest):
    """Create a new shift"""
    try:
        shift_type = ShiftType(request.shift_type)
        required_role = CrewRole(request.required_role)
        scheduled_start = datetime.fromisoformat(request.scheduled_start.replace('Z', '+00:00'))
        
        shift_id = await shift_scheduler.create_shift(
            vessel_id=request.vessel_id,
            shift_type=shift_type,
            scheduled_start=scheduled_start,
            duration_hours=request.duration_hours,
            required_role=required_role,
            created_by="system",
            trip_id=request.trip_id
        )
        
        if shift_id:
            return {"success": True, "shift_id": shift_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to create shift")
            
    except Exception as e:
        logger.error(f"Failed to create shift: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/shifts/vessel/{vessel_id}")
async def get_vessel_schedule(vessel_id: str):
    """Get schedule for vessel"""
    try:
        schedule = shift_scheduler.get_schedule_for_vessel(vessel_id)
        return {"schedule": schedule}
    except Exception as e:
        logger.error(f"Failed to get vessel schedule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Share Calculator Endpoints
@app.post("/shares/calculate")
async def calculate_crew_shares(request: ShareCalculationRequest):
    """Calculate crew shares for a trip"""
    try:
        trip_expenses = None
        if request.trip_expenses:
            trip_expenses = {
                DeductionType(k): float(v) for k, v in request.trip_expenses.items()
            }
        
        allocation_ids = await share_calculator.calculate_crew_shares(
            trip_id=request.trip_id,
            scheme_id=request.scheme_id,
            crew_assignments=request.crew_assignments,
            calculated_by="system",
            trip_expenses=trip_expenses
        )
        
        return {"success": True, "allocation_ids": allocation_ids}
    except Exception as e:
        logger.error(f"Failed to calculate shares: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/shares/trip/{trip_id}")
async def get_trip_share_summary(trip_id: str):
    """Get share summary for a trip"""
    try:
        summary = share_calculator.get_trip_share_summary(trip_id)
        return summary
    except Exception as e:
        logger.error(f"Failed to get trip share summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Safety Drill Endpoints
@app.post("/drills")
async def schedule_drill(request: DrillScheduleRequest):
    """Schedule a safety drill"""
    try:
        drill_type = DrillType(request.drill_type)
        scheduled_date = datetime.fromisoformat(request.scheduled_date.replace('Z', '+00:00'))
        
        drill_id = await drill_tracker.schedule_drill(
            vessel_id=request.vessel_id,
            drill_type=drill_type,
            scheduled_date=scheduled_date,
            drill_master_id="system",
            scenario_description=request.scenario_description,
            objectives=request.objectives,
            created_by="system",
            trip_id=request.trip_id
        )
        
        if drill_id:
            return {"success": True, "drill_id": drill_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to schedule drill")
            
    except Exception as e:
        logger.error(f"Failed to schedule drill: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/drills/vessel/{vessel_id}")
async def get_vessel_drills(vessel_id: str):
    """Get drills for vessel"""
    try:
        drills = drill_tracker.get_vessel_drills(vessel_id)
        return {"drills": drills}
    except Exception as e:
        logger.error(f"Failed to get vessel drills: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/drills/compliance/{vessel_id}")
async def get_drill_compliance(vessel_id: str):
    """Get drill compliance status"""
    try:
        compliance = drill_tracker.get_drill_compliance_status(vessel_id)
        return compliance
    except Exception as e:
        logger.error(f"Failed to get drill compliance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Statistics and Reporting
@app.get("/stats/vessel/{vessel_id}")
async def get_vessel_statistics(vessel_id: str):
    """Get comprehensive statistics for vessel"""
    try:
        stats = {
            "tasks": task_manager.get_task_statistics(vessel_id),
            "shifts": shift_scheduler.get_shift_statistics(vessel_id),
            "drills": drill_tracker.get_drill_statistics(vessel_id),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        return stats
    except Exception as e:
        logger.error(f"Failed to get vessel statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8375))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )