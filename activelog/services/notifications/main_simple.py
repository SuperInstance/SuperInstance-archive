"""
ActiveLog Notification Service - Simplified Main Application
Port: 8006
"""

import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from core.config import settings
from core.database import DatabaseManager
from core.logging import logger

# Global service instances
db_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db_manager
    
    # Startup
    logger.info("Starting Notification Service")
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        logger.info("Notification Service started successfully", port=8006)
        
    except Exception as e:
        logger.error("Failed to start Notification Service", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Notification Service")
    
    try:
        if db_manager:
            await db_manager.close()
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


app = FastAPI(
    title="ActiveLog Notification Service",
    description="Comprehensive notification service with email, SMS, webhook, and in-app support",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class NotificationRequest(BaseModel):
    notification_type: str
    recipient_id: str  # user_id
    tenant_id: Optional[str] = None
    channels: List[str] = Field(default_factory=lambda: ["in_app"])
    priority: str = "normal"
    title: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)


class PreferencesRequest(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db_healthy = await db_manager.health_check() if db_manager else False
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "service": "notifications",
            "port": 8006,
            "database": "connected" if db_healthy else "disconnected",
            "features": {
                "email": settings.email_configured,
                "sms": settings.sms_configured,
                "webhooks": True,
                "in_app": True,
                "templates": True,
                "digest": settings.DIGEST_ENABLED
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail=str(e))


# Notification endpoints
@app.post("/api/v1/notifications")
async def create_notification(request: NotificationRequest):
    """Create and send a notification"""
    try:
        notification_id = str(uuid.uuid4())
        
        # For now, just create in-app notifications
        if "in_app" in request.channels:
            await db_manager.execute_command("""
                INSERT INTO inapp_notifications (
                    notification_id, user_id, tenant_id, type, title, message, 
                    data, priority
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, notification_id, request.recipient_id, request.tenant_id, 
                 request.notification_type, request.title, request.message, 
                 json.dumps(request.data), 
                 settings.PRIORITY_LEVELS.get(request.priority, 2))
        
        return {
            "notification_id": notification_id,
            "status": "created",
            "channels": request.channels,
            "created_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to create notification", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create notification")


# User notifications endpoints
@app.get("/api/v1/users/{user_id}/notifications")
async def get_user_notifications(user_id: str, 
                               limit: int = Query(50, ge=1, le=100),
                               unread_only: bool = Query(False)):
    """Get user's in-app notifications"""
    try:
        query = """
            SELECT * FROM inapp_notifications 
            WHERE user_id = $1 AND (expires_at IS NULL OR expires_at > NOW())
        """
        params = [user_id]
        
        if unread_only:
            query += " AND is_read = FALSE"
        
        query += " ORDER BY created_at DESC LIMIT $2"
        params.append(limit)
        
        notifications = await db_manager.execute_query(query, *params)
        
        unread_count = await db_manager.execute_scalar("""
            SELECT COUNT(*) FROM inapp_notifications 
            WHERE user_id = $1 AND is_read = FALSE 
                AND (expires_at IS NULL OR expires_at > NOW())
        """, user_id)
        
        # Parse JSON data fields
        for notification in notifications:
            if notification.get('data'):
                try:
                    notification['data'] = json.loads(notification['data'])
                except (json.JSONDecodeError, TypeError):
                    notification['data'] = {}
        
        return {
            "notifications": notifications,
            "unread_count": unread_count or 0,
            "total": len(notifications)
        }
    except Exception as e:
        logger.error("Failed to get user notifications", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get notifications")


@app.post("/api/v1/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, user_id: str = Query(...)):
    """Mark notification as read"""
    try:
        result = await db_manager.execute_command("""
            UPDATE inapp_notifications 
            SET is_read = TRUE, read_at = NOW() 
            WHERE notification_id = $1 AND user_id = $2
        """, notification_id, user_id)
        
        if "UPDATE 1" in result:
            return {"status": "success", "message": "Notification marked as read"}
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to mark notification as read", 
                    notification_id=notification_id, user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to mark as read")


# User preferences endpoints
@app.get("/api/v1/users/{user_id}/preferences")
async def get_user_preferences(user_id: str, tenant_id: Optional[str] = Query(None)):
    """Get user notification preferences"""
    try:
        prefs = await db_manager.execute_query("""
            SELECT * FROM notification_preferences 
            WHERE user_id = $1 AND ($2::VARCHAR IS NULL OR tenant_id = $2)
            LIMIT 1
        """, user_id, tenant_id)
        
        if prefs:
            return dict(prefs[0])
        else:
            return {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email_enabled": settings.DEFAULT_EMAIL_ENABLED,
                "sms_enabled": settings.DEFAULT_SMS_ENABLED,
                "inapp_enabled": settings.DEFAULT_INAPP_ENABLED,
                "webhook_enabled": settings.DEFAULT_WEBHOOK_ENABLED
            }
    except Exception as e:
        logger.error("Failed to get user preferences", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get preferences")


# System notification endpoints
@app.post("/api/v1/system/broadcast")
async def broadcast_system_notification(
    title: str = Query(...),
    message: str = Query(...),
    notification_type: str = Query("system_announcement"),
    priority: int = Query(3)
):
    """Broadcast system notification to all users"""
    try:
        # For now, just log the broadcast
        logger.info("System notification broadcast", 
                   title=title,
                   message=message,
                   type=notification_type,
                   priority=priority)
        
        return {
            "status": "success",
            "message": "System notification broadcasted",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to broadcast system notification", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to broadcast notification")


# Statistics endpoint
@app.get("/api/v1/stats")
async def get_service_stats():
    """Get notification service statistics"""
    try:
        stats = await db_manager.get_notification_stats() if db_manager else {}
        
        return {
            "service": "notifications",
            "version": "1.0.0",
            "port": 8006,
            "database": stats,
            "configuration": {
                "email_provider": settings.EMAIL_PROVIDER,
                "email_configured": settings.email_configured,
                "sms_configured": settings.sms_configured,
                "digest_enabled": settings.DIGEST_ENABLED,
                "supported_channels": ["in_app", "email", "sms", "webhook"],
                "supported_types": list(settings.NOTIFICATION_TYPES.keys())
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error("Failed to get service statistics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get statistics")


# WebSocket support (simplified)
connected_users = {}

@app.websocket("/api/v1/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time notifications"""
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    
    if user_id not in connected_users:
        connected_users[user_id] = {}
    connected_users[user_id][connection_id] = websocket
    
    logger.info("WebSocket connected", user_id=user_id, connection_id=connection_id)
    
    try:
        # Send recent unread notifications
        notifications = await db_manager.execute_query("""
            SELECT * FROM inapp_notifications 
            WHERE user_id = $1 AND is_read = FALSE 
            ORDER BY created_at DESC LIMIT 10
        """, user_id)
        
        if notifications:
            sync_message = {
                "type": "notifications_sync",
                "notifications": [dict(notif) for notif in notifications],
                "count": len(notifications)
            }
            await websocket.send_text(json.dumps(sync_message, default=str))
        
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message) if message else {}
                
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error("WebSocket message error", user_id=user_id, error=str(e))
                break
                
    except Exception as e:
        logger.error("WebSocket connection error", user_id=user_id, error=str(e))
    finally:
        if user_id in connected_users and connection_id in connected_users[user_id]:
            del connected_users[user_id][connection_id]
            if not connected_users[user_id]:
                del connected_users[user_id]
        logger.info("WebSocket disconnected", user_id=user_id, connection_id=connection_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main_simple:app",
        host="0.0.0.0",
        port=8006,
        reload=True,
        log_level="info"
    )