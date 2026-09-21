"""
CoCapn (Co-Captain) Service
Maritime navigation and crew coordination service
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
import aiohttp
import logging
from enum import Enum
import math
import json
import uuid

logger = logging.getLogger(__name__)

class NavigationStatus(str, Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"
    EMERGENCY = "emergency"
    ANCHORED = "anchored"

class WeatherCondition(str, Enum):
    CALM = "calm"
    MODERATE = "moderate"
    ROUGH = "rough"
    SEVERE = "severe"
    STORM = "storm"

class CrewRole(str, Enum):
    CAPTAIN = "captain"
    FIRST_MATE = "first_mate"
    NAVIGATOR = "navigator"
    ENGINEER = "engineer"
    DECKHAND = "deckhand"
    COOK = "cook"
    RADIO_OPERATOR = "radio_operator"

# Request/Response Models
class NavigationPlan(BaseModel):
    vessel_id: str
    departure_port: str
    destination_port: str
    waypoints: List[Dict[str, float]] = Field(default_factory=list)
    estimated_duration: float  # hours
    fuel_required: float  # liters
    crew_requirements: List[CrewRole]
    weather_window: Dict[str, Any]
    emergency_ports: List[str] = Field(default_factory=list)

class CrewAssignment(BaseModel):
    crew_member_id: str
    name: str
    role: CrewRole
    certification_level: int = Field(ge=1, le=5)
    experience_years: int = Field(ge=0)
    availability: Dict[str, bool]
    emergency_contact: str

class VesselPosition(BaseModel):
    vessel_id: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float = Field(ge=0, lt=360)
    speed_knots: float = Field(ge=0)
    timestamp: datetime

class WeatherUpdate(BaseModel):
    location: Dict[str, float]  # lat, lon
    condition: WeatherCondition
    wind_speed_knots: float
    wave_height_meters: float
    visibility_km: float
    temperature_celsius: float
    pressure_hpa: float
    forecast_hours: int = 24

class CoCapnService:
    """Co-Captain service for maritime navigation and crew coordination"""
    
    def __init__(self):
        self.navigation_plans = {}
        self.active_voyages = {}
        self.crew_assignments = {}
        self.weather_data = {}
        self.vessel_positions = {}
        self.communication_log = {}
        
    async def create_navigation_plan(self, plan: NavigationPlan) -> str:
        """Create a comprehensive navigation plan"""
        plan_id = str(uuid.uuid4())
        
        # Calculate route details
        route_details = await self._calculate_route(
            plan.departure_port,
            plan.destination_port,
            plan.waypoints
        )
        
        # Assess weather conditions
        weather_assessment = await self._assess_weather_conditions(route_details)
        
        # Validate crew requirements
        crew_validation = await self._validate_crew_requirements(plan.crew_requirements)
        
        navigation_plan = {
            "plan_id": plan_id,
            "vessel_id": plan.vessel_id,
            "route_details": route_details,
            "weather_assessment": weather_assessment,
            "crew_validation": crew_validation,
            "fuel_calculation": await self._calculate_fuel_requirements(route_details),
            "safety_checkpoints": await self._identify_safety_checkpoints(route_details),
            "communication_schedule": await self._create_communication_schedule(plan.estimated_duration),
            "emergency_procedures": await self._prepare_emergency_procedures(plan.emergency_ports),
            "created_at": datetime.utcnow(),
            "status": NavigationStatus.PLANNING
        }
        
        self.navigation_plans[plan_id] = navigation_plan
        
        # Notify marine-advanced service
        await self._notify_marine_advanced("navigation_plan_created", {
            "plan_id": plan_id,
            "vessel_id": plan.vessel_id,
            "route_summary": route_details["summary"]
        })
        
        return plan_id
    
    async def assign_crew(self, plan_id: str, crew_assignments: List[CrewAssignment]) -> Dict[str, Any]:
        """Assign crew members to a navigation plan"""
        if plan_id not in self.navigation_plans:
            raise ValueError(f"Navigation plan {plan_id} not found")
        
        # Validate crew qualifications
        assignment_results = []
        for assignment in crew_assignments:
            qualification_check = await self._check_crew_qualifications(assignment)
            
            assignment_result = {
                "crew_member_id": assignment.crew_member_id,
                "role": assignment.role,
                "qualified": qualification_check["qualified"],
                "certification_valid": qualification_check["certification_valid"],
                "experience_adequate": qualification_check["experience_adequate"],
                "assigned": False
            }
            
            if qualification_check["qualified"]:
                self.crew_assignments[f"{plan_id}_{assignment.crew_member_id}"] = {
                    "plan_id": plan_id,
                    "assignment": assignment.dict(),
                    "assigned_at": datetime.utcnow(),
                    "duties": await self._define_crew_duties(assignment.role),
                    "watch_schedule": await self._create_watch_schedule(assignment.role)
                }
                assignment_result["assigned"] = True
            
            assignment_results.append(assignment_result)
        
        # Update navigation plan with crew info
        self.navigation_plans[plan_id]["crew_assignments"] = assignment_results
        
        return {
            "plan_id": plan_id,
            "assignments": assignment_results,
            "total_assigned": len([r for r in assignment_results if r["assigned"]]),
            "crew_complete": await self._verify_crew_completeness(plan_id)
        }
    
    async def start_voyage(self, plan_id: str) -> Dict[str, Any]:
        """Start an active voyage based on navigation plan"""
        if plan_id not in self.navigation_plans:
            raise ValueError(f"Navigation plan {plan_id} not found")
        
        plan = self.navigation_plans[plan_id]
        
        # Pre-departure checks
        departure_checks = await self._perform_departure_checks(plan_id)
        
        if not departure_checks["all_clear"]:
            return {
                "voyage_started": False,
                "issues": departure_checks["issues"],
                "recommendations": departure_checks["recommendations"]
            }
        
        voyage_id = str(uuid.uuid4())
        
        active_voyage = {
            "voyage_id": voyage_id,
            "plan_id": plan_id,
            "vessel_id": plan["vessel_id"],
            "started_at": datetime.utcnow(),
            "status": NavigationStatus.ACTIVE,
            "current_position": None,
            "next_waypoint": plan["route_details"]["waypoints"][0] if plan["route_details"]["waypoints"] else None,
            "progress": 0.0,
            "communication_log": [],
            "crew_status": "active",
            "weather_updates": [],
            "incidents": []
        }
        
        self.active_voyages[voyage_id] = active_voyage
        self.navigation_plans[plan_id]["status"] = NavigationStatus.ACTIVE
        
        # Start monitoring systems
        await self._start_voyage_monitoring(voyage_id)
        
        return {
            "voyage_started": True,
            "voyage_id": voyage_id,
            "estimated_arrival": datetime.utcnow() + timedelta(hours=plan["route_details"]["estimated_hours"]),
            "next_checkpoint": active_voyage["next_waypoint"],
            "crew_briefed": True
        }
    
    async def update_position(self, position: VesselPosition) -> Dict[str, Any]:
        """Update vessel position and calculate progress"""
        self.vessel_positions[position.vessel_id] = position.dict()
        
        # Find active voyage for this vessel
        active_voyage = None
        for voyage in self.active_voyages.values():
            if voyage["vessel_id"] == position.vessel_id and voyage["status"] == NavigationStatus.ACTIVE:
                active_voyage = voyage
                break
        
        if not active_voyage:
            return {"status": "no_active_voyage"}
        
        # Calculate progress
        progress_update = await self._calculate_voyage_progress(active_voyage["voyage_id"], position)
        
        # Update voyage data
        active_voyage["current_position"] = position.dict()
        active_voyage["progress"] = progress_update["progress_percent"]
        active_voyage["next_waypoint"] = progress_update["next_waypoint"]
        
        # Check for course corrections
        course_check = await self._check_course_deviation(active_voyage["voyage_id"], position)
        
        # Weather check
        weather_advisory = await self._check_weather_conditions(position.latitude, position.longitude)
        
        return {
            "vessel_id": position.vessel_id,
            "progress": progress_update["progress_percent"],
            "next_waypoint": progress_update["next_waypoint"],
            "course_status": course_check["status"],
            "weather_advisory": weather_advisory,
            "estimated_arrival": progress_update["estimated_arrival"]
        }
    
    async def handle_emergency(self, vessel_id: str, emergency_type: str, details: Dict[str, Any]) -> Dict[str, Any]:
        """Handle maritime emergency situations"""
        emergency_id = str(uuid.uuid4())
        
        # Find active voyage
        active_voyage = None
        for voyage in self.active_voyages.values():
            if voyage["vessel_id"] == vessel_id and voyage["status"] == NavigationStatus.ACTIVE:
                active_voyage = voyage
                break
        
        if active_voyage:
            active_voyage["status"] = NavigationStatus.EMERGENCY
        
        emergency_response = {
            "emergency_id": emergency_id,
            "vessel_id": vessel_id,
            "emergency_type": emergency_type,
            "details": details,
            "timestamp": datetime.utcnow(),
            "response_actions": [],
            "nearest_assistance": None,
            "evacuation_plan": None
        }
        
        # Determine emergency response
        if emergency_type == "medical":
            emergency_response["response_actions"] = await self._handle_medical_emergency(vessel_id, details)
        elif emergency_type == "mechanical":
            emergency_response["response_actions"] = await self._handle_mechanical_emergency(vessel_id, details)
        elif emergency_type == "weather":
            emergency_response["response_actions"] = await self._handle_weather_emergency(vessel_id, details)
        elif emergency_type == "collision":
            emergency_response["response_actions"] = await self._handle_collision_emergency(vessel_id, details)
        else:
            emergency_response["response_actions"] = await self._handle_general_emergency(vessel_id, details)
        
        # Find nearest assistance
        if vessel_id in self.vessel_positions:
            position = self.vessel_positions[vessel_id]
            emergency_response["nearest_assistance"] = await self._find_nearest_assistance(
                position["latitude"], 
                position["longitude"]
            )
        
        # Notify authorities and marine services
        await self._notify_emergency_services(emergency_response)
        await self._notify_marine_advanced("emergency_declared", emergency_response)
        
        return emergency_response
    
    async def coordinate_crew_communication(self, vessel_id: str, message_type: str, content: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate crew communications and watch changes"""
        communication_id = str(uuid.uuid4())
        
        communication_entry = {
            "communication_id": communication_id,
            "vessel_id": vessel_id,
            "message_type": message_type,
            "content": content,
            "timestamp": datetime.utcnow(),
            "acknowledged_by": []
        }
        
        if vessel_id not in self.communication_log:
            self.communication_log[vessel_id] = []
        
        self.communication_log[vessel_id].append(communication_entry)
        
        # Handle specific communication types
        if message_type == "watch_change":
            await self._process_watch_change(vessel_id, content)
        elif message_type == "weather_update":
            await self._process_weather_communication(vessel_id, content)
        elif message_type == "navigation_update":
            await self._process_navigation_communication(vessel_id, content)
        elif message_type == "crew_report":
            await self._process_crew_report(vessel_id, content)
        
        return {
            "communication_id": communication_id,
            "broadcast": True,
            "requires_acknowledgment": content.get("requires_ack", False),
            "priority": content.get("priority", "normal")
        }
    
    # Helper methods
    
    async def _calculate_route(self, departure: str, destination: str, waypoints: List[Dict[str, float]]) -> Dict[str, Any]:
        """Calculate route details including distance and time"""
        # Simplified route calculation
        total_distance = 0.0
        route_segments = []
        
        # Add departure to waypoints to destination
        all_points = [{"name": departure, "lat": 0, "lon": 0}]  # Would get from port database
        all_points.extend([{"name": f"Waypoint {i}", **wp} for i, wp in enumerate(waypoints)])
        all_points.append({"name": destination, "lat": 0, "lon": 0})  # Would get from port database
        
        for i in range(len(all_points) - 1):
            segment_distance = await self._calculate_distance(all_points[i], all_points[i + 1])
            total_distance += segment_distance
            route_segments.append({
                "from": all_points[i]["name"],
                "to": all_points[i + 1]["name"],
                "distance_nm": segment_distance,
                "bearing": await self._calculate_bearing(all_points[i], all_points[i + 1])
            })
        
        return {
            "total_distance_nm": total_distance,
            "estimated_hours": total_distance / 10,  # Assuming 10 knot average speed
            "segments": route_segments,
            "waypoints": waypoints,
            "summary": f"{departure} to {destination} via {len(waypoints)} waypoints"
        }
    
    async def _calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """Calculate distance between two points in nautical miles"""
        # Simplified haversine formula
        lat1, lon1 = math.radians(point1.get("lat", 0)), math.radians(point1.get("lon", 0))
        lat2, lon2 = math.radians(point2.get("lat", 0)), math.radians(point2.get("lon", 0))
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Convert to nautical miles (Earth radius in nautical miles: 3440.065)
        return c * 3440.065
    
    async def _calculate_bearing(self, point1: Dict, point2: Dict) -> float:
        """Calculate bearing between two points"""
        lat1, lon1 = math.radians(point1.get("lat", 0)), math.radians(point1.get("lon", 0))
        lat2, lon2 = math.radians(point2.get("lat", 0)), math.radians(point2.get("lon", 0))
        
        dlon = lon2 - lon1
        
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        bearing = math.atan2(y, x)
        return (math.degrees(bearing) + 360) % 360
    
    async def _assess_weather_conditions(self, route_details: Dict[str, Any]) -> Dict[str, Any]:
        """Assess weather conditions for the planned route"""
        return {
            "overall_conditions": WeatherCondition.MODERATE,
            "weather_windows": [
                {"start": datetime.utcnow(), "duration_hours": 12, "condition": WeatherCondition.CALM},
                {"start": datetime.utcnow() + timedelta(hours=12), "duration_hours": 6, "condition": WeatherCondition.MODERATE}
            ],
            "alerts": [],
            "recommendations": ["Monitor weather updates every 4 hours", "Have contingency plan for rough weather"]
        }
    
    async def _validate_crew_requirements(self, crew_requirements: List[CrewRole]) -> Dict[str, Any]:
        """Validate crew requirements for the voyage"""
        required_roles = set(crew_requirements)
        essential_roles = {CrewRole.CAPTAIN, CrewRole.NAVIGATOR, CrewRole.ENGINEER}
        
        return {
            "has_essential_crew": essential_roles.issubset(required_roles),
            "total_required": len(crew_requirements),
            "missing_essential": list(essential_roles - required_roles),
            "recommended_additions": ["radio_operator"] if len(crew_requirements) > 5 else []
        }
    
    async def _calculate_fuel_requirements(self, route_details: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate fuel requirements for the voyage"""
        distance_nm = route_details["total_distance_nm"]
        base_consumption = distance_nm * 15  # 15 liters per nautical mile (example)
        
        return {
            "base_fuel_liters": base_consumption,
            "reserve_fuel_liters": base_consumption * 0.2,  # 20% reserve
            "total_required_liters": base_consumption * 1.2,
            "fuel_stops_recommended": distance_nm > 500
        }
    
    async def _identify_safety_checkpoints(self, route_details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify safety checkpoints along the route"""
        checkpoints = []
        
        for i, segment in enumerate(route_details["segments"]):
            if i % 2 == 0:  # Every other segment
                checkpoints.append({
                    "checkpoint_id": f"CP_{i+1}",
                    "location": segment["to"],
                    "distance_from_start": sum(s["distance_nm"] for s in route_details["segments"][:i+1]),
                    "safety_checks": ["Position report", "Fuel check", "Crew status", "Weather update"],
                    "emergency_procedures": "Standard emergency protocols"
                })
        
        return checkpoints
    
    async def _create_communication_schedule(self, estimated_duration: float) -> List[Dict[str, Any]]:
        """Create communication schedule for the voyage"""
        schedule = []
        intervals = max(1, int(estimated_duration / 4))  # Every 4 hours or minimum 1
        
        for i in range(0, int(estimated_duration), intervals):
            schedule.append({
                "time_offset_hours": i,
                "type": "position_report",
                "content": "Position, status, and weather report",
                "recipients": ["harbor_master", "company_dispatch"]
            })
        
        return schedule
    
    async def _prepare_emergency_procedures(self, emergency_ports: List[str]) -> Dict[str, Any]:
        """Prepare emergency procedures and port information"""
        return {
            "emergency_contacts": [
                {"role": "Coast Guard", "frequency": "Channel 16", "phone": "Emergency services"},
                {"role": "Company Dispatch", "frequency": "Company channel", "phone": "+1-555-0199"}
            ],
            "emergency_ports": [{"name": port, "distance_estimate": "TBD", "facilities": "Full service"} for port in emergency_ports],
            "procedures": {
                "medical_emergency": "Contact Coast Guard, assess patient, prepare for evacuation",
                "mechanical_failure": "Assess damage, contact dispatch, proceed to nearest safe port",
                "severe_weather": "Seek shelter, reduce speed, maintain communication"
            }
        }
    
    async def _notify_marine_advanced(self, event_type: str, data: Dict[str, Any]):
        """Notify marine-advanced service of events"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "http://localhost:8025/api/cocapn/notifications",
                    json={"event_type": event_type, "data": data}
                )
        except Exception as e:
            logger.error(f"Failed to notify marine-advanced: {e}")
    
    async def _check_crew_qualifications(self, assignment: CrewAssignment) -> Dict[str, Any]:
        """Check crew member qualifications"""
        # Simplified qualification check
        required_cert_level = {
            CrewRole.CAPTAIN: 5,
            CrewRole.NAVIGATOR: 4,
            CrewRole.ENGINEER: 3,
            CrewRole.FIRST_MATE: 3
        }.get(assignment.role, 2)
        
        required_experience = {
            CrewRole.CAPTAIN: 10,
            CrewRole.NAVIGATOR: 5,
            CrewRole.ENGINEER: 3,
            CrewRole.FIRST_MATE: 5
        }.get(assignment.role, 1)
        
        return {
            "qualified": assignment.certification_level >= required_cert_level and assignment.experience_years >= required_experience,
            "certification_valid": assignment.certification_level >= required_cert_level,
            "experience_adequate": assignment.experience_years >= required_experience,
            "required_cert_level": required_cert_level,
            "required_experience": required_experience
        }
    
    async def _define_crew_duties(self, role: CrewRole) -> List[str]:
        """Define duties for crew role"""
        duties_map = {
            CrewRole.CAPTAIN: ["Overall vessel command", "Navigation oversight", "Crew management", "Emergency decisions"],
            CrewRole.NAVIGATOR: ["Chart plotting", "Position fixing", "Course corrections", "Weather monitoring"],
            CrewRole.ENGINEER: ["Engine maintenance", "Mechanical systems", "Fuel management", "Safety systems"],
            CrewRole.FIRST_MATE: ["Watch supervision", "Cargo operations", "Safety inspections", "Crew coordination"],
            CrewRole.DECKHAND: ["Deck maintenance", "Line handling", "Equipment operation", "General assistance"],
            CrewRole.COOK: ["Meal preparation", "Galley maintenance", "Provision management", "Crew nutrition"],
            CrewRole.RADIO_OPERATOR: ["Communications", "Weather reports", "Position reports", "Emergency coordination"]
        }
        return duties_map.get(role, ["General duties"])
    
    async def _create_watch_schedule(self, role: CrewRole) -> Dict[str, Any]:
        """Create watch schedule for crew member"""
        if role in [CrewRole.CAPTAIN, CrewRole.NAVIGATOR, CrewRole.FIRST_MATE]:
            return {
                "watch_pattern": "4_on_8_off",
                "watches": [
                    {"start": "00:00", "end": "04:00", "type": "navigation_watch"},
                    {"start": "08:00", "end": "12:00", "type": "navigation_watch"},
                    {"start": "16:00", "end": "20:00", "type": "navigation_watch"}
                ]
            }
        else:
            return {
                "watch_pattern": "day_shift",
                "watches": [
                    {"start": "06:00", "end": "18:00", "type": "duty_watch"}
                ]
            }
    
    async def _perform_departure_checks(self, plan_id: str) -> Dict[str, Any]:
        """Perform pre-departure safety and readiness checks"""
        checks = {
            "crew_aboard": True,  # Would check actual crew status
            "fuel_sufficient": True,  # Would check fuel levels
            "weather_acceptable": True,  # Would check weather conditions
            "equipment_operational": True,  # Would check equipment status
            "permits_valid": True,  # Would check documentation
            "communication_tested": True  # Would test radio equipment
        }
        
        all_clear = all(checks.values())
        issues = [check for check, status in checks.items() if not status]
        
        return {
            "all_clear": all_clear,
            "checks": checks,
            "issues": issues,
            "recommendations": ["Address all issues before departure"] if issues else ["Cleared for departure"]
        }
    
    async def _start_voyage_monitoring(self, voyage_id: str):
        """Start automated monitoring systems for the voyage"""
        # This would start background tasks for monitoring
        logger.info(f"Started monitoring for voyage {voyage_id}")
    
    async def _calculate_voyage_progress(self, voyage_id: str, position: VesselPosition) -> Dict[str, Any]:
        """Calculate voyage progress based on current position"""
        # Simplified progress calculation
        return {
            "progress_percent": 25.0,  # Would calculate based on actual route
            "next_waypoint": {"lat": 40.0, "lon": -74.0, "name": "Next checkpoint"},
            "estimated_arrival": datetime.utcnow() + timedelta(hours=6),
            "distance_remaining_nm": 150.0
        }
    
    async def _check_course_deviation(self, voyage_id: str, position: VesselPosition) -> Dict[str, Any]:
        """Check for course deviation"""
        return {
            "status": "on_course",
            "deviation_degrees": 2.0,
            "correction_required": False,
            "recommended_heading": position.heading
        }
    
    async def _check_weather_conditions(self, lat: float, lon: float) -> Dict[str, Any]:
        """Check current weather conditions at position"""
        return {
            "condition": WeatherCondition.MODERATE,
            "wind_speed_knots": 12.0,
            "wave_height_meters": 2.0,
            "visibility_km": 10.0,
            "advisory": "Monitor for changing conditions"
        }
    
    async def _handle_medical_emergency(self, vessel_id: str, details: Dict[str, Any]) -> List[str]:
        """Handle medical emergency"""
        return [
            "Contact Coast Guard medical services",
            "Administer first aid if qualified",
            "Prepare for possible evacuation",
            "Document patient condition",
            "Maintain course to nearest medical facility"
        ]
    
    async def _handle_mechanical_emergency(self, vessel_id: str, details: Dict[str, Any]) -> List[str]:
        """Handle mechanical emergency"""
        return [
            "Assess mechanical problem severity",
            "Attempt repairs if safe to do so",
            "Contact company dispatch",
            "Determine nearest repair facility",
            "Request towing assistance if needed"
        ]
    
    async def _handle_weather_emergency(self, vessel_id: str, details: Dict[str, Any]) -> List[str]:
        """Handle weather emergency"""
        return [
            "Reduce speed and seek shelter",
            "Secure all loose equipment",
            "Monitor weather updates continuously",
            "Prepare for possible course change",
            "Ensure crew safety protocols active"
        ]
    
    async def _handle_collision_emergency(self, vessel_id: str, details: Dict[str, Any]) -> List[str]:
        """Handle collision emergency"""
        return [
            "Assess vessel damage immediately",
            "Check for injuries to crew",
            "Contact Coast Guard and authorities",
            "Document incident thoroughly",
            "Prepare damage control measures"
        ]
    
    async def _handle_general_emergency(self, vessel_id: str, details: Dict[str, Any]) -> List[str]:
        """Handle general emergency"""
        return [
            "Assess situation severity",
            "Ensure crew safety first",
            "Contact appropriate authorities",
            "Follow established emergency procedures",
            "Maintain detailed incident log"
        ]
    
    async def _find_nearest_assistance(self, lat: float, lon: float) -> Dict[str, Any]:
        """Find nearest assistance for emergency"""
        return {
            "coast_guard_station": {
                "name": "Coastal Station Alpha",
                "distance_nm": 45.0,
                "estimated_response_time": "2 hours",
                "capabilities": ["Search and rescue", "Medical evacuation"]
            },
            "nearest_vessel": {
                "vessel_name": "Helper One",
                "distance_nm": 12.0,
                "vessel_type": "Commercial fishing",
                "estimated_arrival": "45 minutes"
            }
        }
    
    async def _notify_emergency_services(self, emergency_response: Dict[str, Any]):
        """Notify emergency services of situation"""
        logger.info(f"Emergency services notified for {emergency_response['emergency_id']}")
    
    async def _process_watch_change(self, vessel_id: str, content: Dict[str, Any]):
        """Process watch change communication"""
        logger.info(f"Watch change processed for vessel {vessel_id}")
    
    async def _process_weather_communication(self, vessel_id: str, content: Dict[str, Any]):
        """Process weather update communication"""
        logger.info(f"Weather update processed for vessel {vessel_id}")
    
    async def _process_navigation_communication(self, vessel_id: str, content: Dict[str, Any]):
        """Process navigation communication"""
        logger.info(f"Navigation update processed for vessel {vessel_id}")
    
    async def _process_crew_report(self, vessel_id: str, content: Dict[str, Any]):
        """Process crew report communication"""
        logger.info(f"Crew report processed for vessel {vessel_id}")
    
    async def _verify_crew_completeness(self, plan_id: str) -> bool:
        """Verify if crew assignment is complete"""
        # Would check if all required roles are filled
        return True

# FastAPI App
app = FastAPI(
    title="CoCapn Maritime Navigation Service",
    description="Co-Captain service for maritime navigation and crew coordination",
    version="1.0.0"
)

service = CoCapnService()

# Health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "cocapn",
        "timestamp": datetime.utcnow().isoformat(),
        "active_voyages": len(service.active_voyages),
        "navigation_plans": len(service.navigation_plans)
    }

# Navigation endpoints
@app.post("/navigation/plan")
async def create_navigation_plan(plan: NavigationPlan):
    plan_id = await service.create_navigation_plan(plan)
    return {"success": True, "plan_id": plan_id}

@app.post("/navigation/crew/{plan_id}")
async def assign_crew(plan_id: str, crew_assignments: List[CrewAssignment]):
    result = await service.assign_crew(plan_id, crew_assignments)
    return {"success": True, **result}

@app.post("/voyage/start/{plan_id}")
async def start_voyage(plan_id: str):
    result = await service.start_voyage(plan_id)
    return {"success": result["voyage_started"], **result}

@app.post("/voyage/position")
async def update_position(position: VesselPosition):
    result = await service.update_position(position)
    return {"success": True, **result}

@app.post("/emergency/{vessel_id}")
async def handle_emergency(vessel_id: str, emergency_type: str, details: Dict[str, Any]):
    result = await service.handle_emergency(vessel_id, emergency_type, details)
    return {"success": True, **result}

@app.post("/communication/{vessel_id}")
async def coordinate_communication(vessel_id: str, message_type: str, content: Dict[str, Any]):
    result = await service.coordinate_crew_communication(vessel_id, message_type, content)
    return {"success": True, **result}

# Status endpoints
@app.get("/navigation/plans")
async def get_navigation_plans():
    return {"plans": list(service.navigation_plans.keys())}

@app.get("/voyage/active")
async def get_active_voyages():
    return {"voyages": list(service.active_voyages.keys())}

@app.get("/crew/assignments/{plan_id}")
async def get_crew_assignments(plan_id: str):
    assignments = {k: v for k, v in service.crew_assignments.items() if v["plan_id"] == plan_id}
    return {"assignments": assignments}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8026)