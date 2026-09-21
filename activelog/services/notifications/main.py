"""
ActiveLog Notification Service
Handles email, in-app, webhook, and SMS notifications
"""

import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from core.config import settings
from core.logging import logger
from core.database import DatabaseManager
from services.email_service import EmailService
from services.webhook_service import WebhookService
from services.template_service import TemplateService
from services.preference_service import PreferenceService
from services.digest_service import DigestService
from services.sms_service import SMSService
from services.websocket_service import InAppNotificationService

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Notification Service",
    description="Comprehensive notification system for emails, webhooks, in-app, and SMS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from api.routes import router
from api.websocket import websocket_router

app.include_router(router, prefix="/api/v1")
app.include_router(websocket_router)

# Global services
db_manager = None
email_service = None
webhook_service = None
template_service = None
preference_service = None
digest_service = None
sms_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager, email_service, webhook_service, template_service
    global preference_service, digest_service, sms_service
    
    logger.info("Starting ActiveLog Notification Service")
    
    # Initialize database
    db_manager = DatabaseManager()
    await db_manager.initialize()
    
    # Initialize core services
    template_service = TemplateService(db_manager)
    preference_service = PreferenceService(db_manager)
    
    # Initialize notification services
    email_service = EmailService(db_manager, template_service)
    webhook_service = WebhookService(db_manager)
    sms_service = SMSService(db_manager, template_service)
    digest_service = DigestService(db_manager, email_service, template_service)
    
    # Load default templates
    await template_service.load_default_templates()
    
    # Start background tasks
    asyncio.create_task(digest_service.start_digest_scheduler())
    asyncio.create_task(webhook_service.start_retry_processor())
    
    logger.info(f"Notification Service started on port {settings.PORT}")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global digest_service, webhook_service, db_manager
    
    logger.info("Shutting down ActiveLog Notification Service")
    
    if digest_service:
        await digest_service.stop_digest_scheduler()
    
    if webhook_service:
        await webhook_service.stop_retry_processor()
    
    if db_manager:
        await db_manager.close()

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "ActiveLog Notification Service",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "Email notifications (SMTP/SendGrid/AWS SES)",
            "In-app notifications via WebSocket",
            "Webhook integrations",
            "SMS notifications (Twilio ready)",
            "Template management",
            "User preferences",
            "Digest emails",
            "Sync conflict alerts"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_healthy = await db_manager.health_check() if db_manager else False
        
        # Check services
        services_status = {
            "database": db_healthy,
            "email_service": email_service.is_configured() if email_service else False,
            "webhook_service": webhook_service is not None,
            "template_service": template_service is not None,
            "preference_service": preference_service is not None,
            "digest_service": digest_service.is_running() if digest_service else False,
            "sms_service": sms_service.is_configured() if sms_service else False
        }
        
        all_healthy = services_status["database"] and services_status["template_service"]
        
        return {
            "status": "healthy" if all_healthy else "degraded",
            "services": services_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/stats")
async def get_service_stats():
    """Get service statistics"""
    try:
        stats = {}
        
        if email_service:
            stats["email"] = await email_service.get_stats()
        
        if webhook_service:
            stats["webhook"] = await webhook_service.get_stats()
        
        if digest_service:
            stats["digest"] = await digest_service.get_stats()
        
        if sms_service:
            stats["sms"] = await sms_service.get_stats()
        
        if template_service:
            stats["templates"] = await template_service.get_stats()
        
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dependency injection
def get_db_manager() -> DatabaseManager:
    """Get database manager instance"""
    if not db_manager:
        raise HTTPException(status_code=503, detail="Database manager not initialized")
    return db_manager

def get_email_service() -> EmailService:
    """Get email service instance"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Email service not initialized")
    return email_service

def get_webhook_service() -> WebhookService:
    """Get webhook service instance"""
    if not webhook_service:
        raise HTTPException(status_code=503, detail="Webhook service not initialized")
    return webhook_service

def get_template_service() -> TemplateService:
    """Get template service instance"""
    if not template_service:
        raise HTTPException(status_code=503, detail="Template service not initialized")
    return template_service

def get_preference_service() -> PreferenceService:
    """Get preference service instance"""
    if not preference_service:
        raise HTTPException(status_code=503, detail="Preference service not initialized")
    return preference_service

def get_digest_service() -> DigestService:
    """Get digest service instance"""
    if not digest_service:
        raise HTTPException(status_code=503, detail="Digest service not initialized")
    return digest_service

def get_sms_service() -> SMSService:
    """Get SMS service instance"""
    if not sms_service:
        raise HTTPException(status_code=503, detail="SMS service not initialized")
    return sms_service

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )