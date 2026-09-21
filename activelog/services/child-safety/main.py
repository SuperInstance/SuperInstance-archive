"""
Child Safety System - Main Service

This module provides the main FastAPI service that coordinates all child safety
components including content filtering, interaction monitoring, bullying prevention,
screen time management, health monitoring, emergency contacts, and COPPA compliance.
"""

import asyncio
import asyncpg
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
import logging
import os
import json

# Import our safety components
from content_filtering.age_appropriate_filter import AgeAppropriateFilter, ContentItem
from monitoring.privacy_respecting_monitor import PrivacyRespectingMonitor, InteractionEvent
from bullying_prevention.anti_bullying_system import AntiBullyingSystem, BullyingIncident
from screen_time.screen_time_manager import ScreenTimeManager, ActivityType, ScreenTimeLimits
from health.health_monitor import HealthMonitor, HealthMetricType, HealthAlertLevel
from emergency.emergency_contacts import EmergencyContactSystem, EmergencyType, EmergencyLevel, ContactType
from compliance.coppa_compliance import COPPAComplianceSystem, DataCategory, ConsentType

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security
security = HTTPBearer()

# Pydantic models for API requests
class UserRegistrationRequest(BaseModel):
    user_id: str
    age: int
    birth_date: date
    parental_email: str
    parent_name: Optional[str] = None

class ContentFilterRequest(BaseModel):
    content: str
    content_type: str = "text"
    source_url: Optional[str] = None

class InteractionMonitorRequest(BaseModel):
    user_id: str
    interaction_type: str
    content: Optional[str] = None
    participant_ids: List[str] = []
    metadata: Dict[str, Any] = {}

class ScreenTimeSessionRequest(BaseModel):
    user_id: str
    activity_type: str
    app_category: str
    educational_value: float = 0.0

class EmergencyContactRequest(BaseModel):
    user_id: str
    contact_type: str
    name: str
    relationship: str
    email: str
    phone_primary: Optional[str] = None
    phone_secondary: Optional[str] = None
    preferred_method: str = "email"
    can_authorize: bool = False

class EmergencyAlertRequest(BaseModel):
    user_id: str
    emergency_type: str
    emergency_level: str
    description: str
    context_data: Dict[str, Any] = {}

class ConsentRequest(BaseModel):
    user_id: str
    consent_type: str
    data_categories: List[str]
    parent_name: str
    parent_email: str

class ChildSafetyService:
    def __init__(self):
        self.app = FastAPI(
            title="Child Safety System",
            description="Comprehensive child safety and protection system",
            version="1.0.0"
        )
        self.db_pool = None
        
        # Initialize components (will be set up after database connection)
        self.content_filter = None
        self.interaction_monitor = None
        self.bullying_system = None
        self.screen_time_manager = None
        self.health_monitor = None
        self.emergency_system = None
        self.coppa_compliance = None
        
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        """Setup FastAPI middleware"""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = datetime.now()
            response = await call_next(request)
            process_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
            return response

    def setup_routes(self):
        """Setup FastAPI routes"""
        
        # Health check
        @self.app.get("/health")
        async def health_check():
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        
        # User management
        @self.app.post("/users/register")
        async def register_user(request: UserRegistrationRequest):
            """Register a new user with child safety protections"""
            try:
                # Register with COPPA compliance
                child_user = await self.coppa_compliance.register_child_user(
                    user_id=request.user_id,
                    birth_date=request.birth_date,
                    parental_email=request.parental_email
                )
                
                # Set up screen time limits
                screen_limits = await self.screen_time_manager.set_user_limits(
                    user_id=request.user_id,
                    age=request.age
                )
                
                # Start health monitoring
                await self.health_monitor.start_monitoring(request.user_id, request.age)
                
                return {
                    "user_id": request.user_id,
                    "coppa_compliance": {
                        "consent_required": child_user.consent_required,
                        "consent_status": child_user.consent_status.value,
                        "account_restricted": child_user.account_restricted
                    },
                    "screen_time_limits": {
                        "weekday_minutes": screen_limits.weekday_minutes,
                        "weekend_minutes": screen_limits.weekend_minutes
                    },
                    "health_monitoring": "active",
                    "message": "User registered successfully with child safety protections"
                }
                
            except Exception as e:
                logger.error(f"User registration failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Content filtering
        @self.app.post("/content/filter")
        async def filter_content(request: ContentFilterRequest):
            """Filter content for age-appropriateness and safety"""
            try:
                content_item = ContentItem(
                    content_id=f"content_{int(datetime.now().timestamp())}",
                    content=request.content,
                    content_type=request.content_type,
                    source_url=request.source_url,
                    metadata={}
                )
                
                analysis = await self.content_filter.analyze_content(content_item, age=13)
                
                return {
                    "content_id": content_item.content_id,
                    "safety_level": analysis.safety_level.value,
                    "age_rating": analysis.age_rating,
                    "educational_value": analysis.educational_value,
                    "blocked": analysis.blocked,
                    "reasons": analysis.reasons,
                    "filtered_content": analysis.filtered_content
                }
                
            except Exception as e:
                logger.error(f"Content filtering failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Interaction monitoring
        @self.app.post("/interactions/monitor")
        async def monitor_interaction(request: InteractionMonitorRequest):
            """Monitor user interaction for safety concerns"""
            try:
                interaction_event = InteractionEvent(
                    event_id=f"event_{int(datetime.now().timestamp())}",
                    user_id=request.user_id,
                    interaction_type=request.interaction_type,
                    timestamp=datetime.now(),
                    content_hash=None,
                    participant_ids=request.participant_ids,
                    risk_indicators=[],
                    metadata=request.metadata
                )
                
                risk_assessment = await self.interaction_monitor.analyze_interaction(
                    interaction_event, request.content
                )
                
                return {
                    "event_id": interaction_event.event_id,
                    "risk_level": risk_assessment.risk_level.value,
                    "risk_score": risk_assessment.risk_score,
                    "risk_factors": risk_assessment.risk_factors,
                    "intervention_recommended": risk_assessment.requires_intervention,
                    "alerts_triggered": risk_assessment.alerts_triggered
                }
                
            except Exception as e:
                logger.error(f"Interaction monitoring failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Screen time management
        @self.app.post("/screentime/start")
        async def start_screen_session(request: ScreenTimeSessionRequest):
            """Start a new screen time session"""
            try:
                activity_type = ActivityType(request.activity_type)
                
                session_id = await self.screen_time_manager.start_session(
                    user_id=request.user_id,
                    activity_type=activity_type,
                    app_category=request.app_category,
                    educational_value=request.educational_value
                )
                
                if not session_id:
                    return {
                        "allowed": False,
                        "message": "Screen time session cannot be started. Check daily limits or restricted periods."
                    }
                
                return {
                    "session_id": session_id,
                    "allowed": True,
                    "activity_type": request.activity_type,
                    "message": "Screen time session started successfully"
                }
                
            except Exception as e:
                logger.error(f"Screen time session start failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/screentime/end/{session_id}")
        async def end_screen_session(session_id: str):
            """End a screen time session"""
            try:
                session = await self.screen_time_manager.end_session(session_id)
                
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                return {
                    "session_id": session_id,
                    "total_minutes": session.total_minutes,
                    "activity_type": session.activity_type.value,
                    "educational_value": session.educational_value,
                    "breaks_taken": len(session.breaks_taken),
                    "message": "Screen time session ended successfully"
                }
                
            except Exception as e:
                logger.error(f"Screen time session end failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Health monitoring
        @self.app.get("/health/dashboard/{user_id}")
        async def get_health_dashboard(user_id: str):
            """Get health monitoring dashboard for a user"""
            try:
                dashboard = await self.health_monitor.get_health_dashboard(user_id)
                return dashboard
                
            except Exception as e:
                logger.error(f"Health dashboard retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Emergency contacts
        @self.app.post("/emergency/contacts")
        async def add_emergency_contact(request: EmergencyContactRequest):
            """Add an emergency contact for a user"""
            try:
                contact_type = ContactType(request.contact_type)
                
                contact_id = await self.emergency_system.add_emergency_contact(
                    user_id=request.user_id,
                    contact_type=contact_type,
                    name=request.name,
                    relationship=request.relationship,
                    email=request.email,
                    phone_primary=request.phone_primary,
                    phone_secondary=request.phone_secondary,
                    can_authorize=request.can_authorize
                )
                
                return {
                    "contact_id": contact_id,
                    "user_id": request.user_id,
                    "contact_type": request.contact_type,
                    "verification_required": True,
                    "message": "Emergency contact added. Verification email sent."
                }
                
            except Exception as e:
                logger.error(f"Emergency contact addition failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/emergency/alert")
        async def trigger_emergency_alert(request: EmergencyAlertRequest):
            """Trigger an emergency alert"""
            try:
                emergency_type = EmergencyType(request.emergency_type)
                emergency_level = EmergencyLevel(request.emergency_level)
                
                alert_id = await self.emergency_system.trigger_emergency_alert(
                    user_id=request.user_id,
                    emergency_type=emergency_type,
                    emergency_level=emergency_level,
                    description=request.description,
                    context_data=request.context_data,
                    auto_generated=False
                )
                
                return {
                    "alert_id": alert_id,
                    "emergency_type": request.emergency_type,
                    "emergency_level": request.emergency_level,
                    "message": "Emergency alert triggered and contacts notified"
                }
                
            except Exception as e:
                logger.error(f"Emergency alert failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # COPPA compliance
        @self.app.post("/coppa/consent")
        async def request_parental_consent(request: ConsentRequest):
            """Request parental consent for data collection"""
            try:
                consent_type = ConsentType(request.consent_type)
                data_categories = [DataCategory(cat) for cat in request.data_categories]
                
                consent_id = await self.coppa_compliance.request_parental_consent(
                    user_id=request.user_id,
                    consent_type=consent_type,
                    data_categories=data_categories,
                    parent_name=request.parent_name,
                    parent_email=request.parent_email,
                    ip_address="127.0.0.1",  # Would get from request
                    user_agent="API Client"
                )
                
                return {
                    "consent_id": consent_id,
                    "user_id": request.user_id,
                    "consent_type": request.consent_type,
                    "data_categories": request.data_categories,
                    "message": "Parental consent request sent. Verification required."
                }
                
            except Exception as e:
                logger.error(f"Parental consent request failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/coppa/compliance/{user_id}")
        async def get_compliance_status(user_id: str):
            """Get COPPA compliance status for a user"""
            try:
                dashboard = await self.coppa_compliance.get_compliance_dashboard(user_id)
                return dashboard
                
            except Exception as e:
                logger.error(f"Compliance status retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Comprehensive safety dashboard
        @self.app.get("/safety/dashboard/{user_id}")
        async def get_safety_dashboard(user_id: str):
            """Get comprehensive safety dashboard for a user"""
            try:
                # Gather data from all safety components
                health_dashboard = await self.health_monitor.get_health_dashboard(user_id)
                emergency_dashboard = await self.emergency_system.get_emergency_dashboard(user_id)
                compliance_dashboard = await self.coppa_compliance.get_compliance_dashboard(user_id)
                screen_time_report = await self.screen_time_manager.get_usage_report(user_id, days=7)
                
                # Create comprehensive dashboard
                safety_dashboard = {
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    "overall_safety_score": self._calculate_overall_safety_score(
                        health_dashboard, emergency_dashboard, compliance_dashboard, screen_time_report
                    ),
                    "health_monitoring": {
                        "status": health_dashboard["health_status"],
                        "score": health_dashboard["overall_health_score"],
                        "alerts": len(health_dashboard["recent_alerts"])
                    },
                    "emergency_contacts": {
                        "status": emergency_dashboard["system_status"]["status"],
                        "coverage": emergency_dashboard["system_status"]["coverage"],
                        "verified_contacts": emergency_dashboard["emergency_contacts"]["verified"]
                    },
                    "coppa_compliance": {
                        "status": compliance_dashboard["compliance_summary"]["status"],
                        "score": compliance_dashboard["compliance_summary"]["overall_score"],
                        "alerts": len(compliance_dashboard["alerts"])
                    },
                    "screen_time": {
                        "daily_average": screen_time_report["summary"]["average_daily_usage"],
                        "educational_percentage": screen_time_report["summary"]["educational_percentage"],
                        "health_score": screen_time_report["summary"]["health_score"]
                    },
                    "recommendations": self._generate_safety_recommendations(
                        health_dashboard, emergency_dashboard, compliance_dashboard, screen_time_report
                    )
                }
                
                return safety_dashboard
                
            except Exception as e:
                logger.error(f"Safety dashboard retrieval failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # System administration
        @self.app.post("/admin/audit")
        async def run_compliance_audit():
            """Run comprehensive compliance audit"""
            try:
                audit_id = await self.coppa_compliance.run_compliance_audit()
                
                return {
                    "audit_id": audit_id,
                    "message": "Compliance audit completed successfully"
                }
                
            except Exception as e:
                logger.error(f"Compliance audit failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/admin/data-retention")
        async def run_data_retention_review():
            """Run data retention review and cleanup"""
            try:
                await self.coppa_compliance.schedule_data_retention_review()
                await self.screen_time_manager.cleanup_old_data()
                
                return {
                    "message": "Data retention review completed successfully"
                }
                
            except Exception as e:
                logger.error(f"Data retention review failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _calculate_overall_safety_score(self, health_data: Dict, emergency_data: Dict,
                                      compliance_data: Dict, screen_time_data: Dict) -> float:
        """Calculate overall safety score from component scores"""
        
        health_score = health_data.get("overall_health_score", 0)
        compliance_score = compliance_data.get("compliance_summary", {}).get("overall_score", 0)
        screen_time_score = screen_time_data.get("summary", {}).get("health_score", 0)
        
        # Emergency system score based on coverage
        emergency_coverage = emergency_data.get("system_status", {}).get("coverage", "None")
        emergency_score = {"Full": 100, "Partial": 75, "None": 0}.get(emergency_coverage, 0)
        
        # Weighted average
        overall_score = (
            health_score * 0.3 +
            compliance_score * 0.25 +
            screen_time_score * 0.25 +
            emergency_score * 0.2
        )
        
        return round(overall_score, 1)

    def _generate_safety_recommendations(self, health_data: Dict, emergency_data: Dict,
                                       compliance_data: Dict, screen_time_data: Dict) -> List[str]:
        """Generate safety recommendations based on all component data"""
        
        recommendations = []
        
        # Health recommendations
        if health_data.get("overall_health_score", 0) < 70:
            recommendations.extend(health_data.get("recommendations", []))
        
        # Emergency contact recommendations
        emergency_recs = emergency_data.get("system_status", {}).get("recommendations", [])
        recommendations.extend(emergency_recs)
        
        # Compliance recommendations
        if compliance_data.get("alerts"):
            recommendations.append("Address COPPA compliance alerts")
        
        # Screen time recommendations
        if screen_time_data.get("summary", {}).get("health_score", 0) < 70:
            recommendations.append("Review screen time usage patterns and increase breaks")
        
        # Remove duplicates and limit to top 5
        unique_recommendations = list(dict.fromkeys(recommendations))
        return unique_recommendations[:5]

    async def initialize_database(self):
        """Initialize database connection and components"""
        try:
            # Create database connection pool
            self.db_pool = await asyncpg.create_pool(
                host=os.getenv("DB_HOST", "localhost"),
                port=os.getenv("DB_PORT", "5432"),
                database=os.getenv("DB_NAME", "child_safety"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "password"),
                min_size=5,
                max_size=20
            )
            
            # Initialize all safety components
            self.content_filter = AgeAppropriateFilter(self.db_pool)
            self.interaction_monitor = PrivacyRespectingMonitor(self.db_pool)
            self.bullying_system = AntiBullyingSystem(self.db_pool)
            self.screen_time_manager = ScreenTimeManager(self.db_pool)
            self.health_monitor = HealthMonitor(self.db_pool)
            self.emergency_system = EmergencyContactSystem(self.db_pool)
            self.coppa_compliance = COPPAComplianceSystem(self.db_pool)
            
            # Initialize database tables
            await self.content_filter.initialize_database()
            await self.interaction_monitor.initialize_database()
            await self.bullying_system.initialize_database()
            await self.screen_time_manager.initialize_database()
            await self.health_monitor.initialize_database()
            await self.emergency_system.initialize_database()
            await self.coppa_compliance.initialize_database()
            
            logger.info("Child Safety System initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    async def startup(self):
        """Application startup event"""
        await self.initialize_database()
        
        # Start background tasks
        asyncio.create_task(self._periodic_data_cleanup())
        asyncio.create_task(self._periodic_compliance_audit())
        
        logger.info("Child Safety System started on port 8213")

    async def _periodic_data_cleanup(self):
        """Periodic data retention cleanup task"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.coppa_compliance.schedule_data_retention_review()
                await self.screen_time_manager.cleanup_old_data()
                logger.info("Periodic data cleanup completed")
            except Exception as e:
                logger.error(f"Periodic data cleanup failed: {e}")

    async def _periodic_compliance_audit(self):
        """Periodic compliance audit task"""
        while True:
            try:
                await asyncio.sleep(86400)  # Run daily
                await self.coppa_compliance.run_compliance_audit()
                logger.info("Periodic compliance audit completed")
            except Exception as e:
                logger.error(f"Periodic compliance audit failed: {e}")

# Create the service instance
child_safety_service = ChildSafetyService()
app = child_safety_service.app

# Setup startup and shutdown events
@app.on_event("startup")
async def startup_event():
    await child_safety_service.startup()

@app.on_event("shutdown")
async def shutdown_event():
    if child_safety_service.db_pool:
        await child_safety_service.db_pool.close()
    logger.info("Child Safety System shutdown complete")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8213,
        log_level="info",
        reload=False  # Set to True for development
    )