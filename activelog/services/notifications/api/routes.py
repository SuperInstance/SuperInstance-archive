"""
API Routes for Notification Service
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, validator

from core.config import settings
from main import (
    get_db_manager, get_email_service, get_webhook_service, get_template_service,
    get_preference_service, get_digest_service, get_sms_service
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response models
class NotificationRequest(BaseModel):
    user_id: str
    notification_type: str
    title: str
    message: str
    tenant_id: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    priority: int = 2
    channels: Optional[List[str]] = None
    template_id: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None

class EmailNotificationRequest(BaseModel):
    user_id: str
    to_email: str
    subject: str
    body: str
    tenant_id: Optional[str] = None
    template_id: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None

class SMSNotificationRequest(BaseModel):
    user_id: str
    to_phone: str
    message: str
    tenant_id: Optional[str] = None
    template_id: Optional[str] = None
    template_vars: Optional[Dict[str, Any]] = None

class WebhookRequest(BaseModel):
    user_id: str
    webhook_url: str
    payload: Dict[str, Any]
    tenant_id: Optional[str] = None
    notification_type: str = "generic"
    headers: Optional[Dict[str, str]] = None
    secret_key: Optional[str] = None

class WebhookEndpointRequest(BaseModel):
    name: str
    url: str
    notification_types: Optional[List[str]] = None
    secret_key: Optional[str] = None

class TemplateRequest(BaseModel):
    template_id: str
    name: str
    type: str
    subject_template: Optional[str] = None
    body_template: str
    sms_template: Optional[str] = None
    description: Optional[str] = None
    variables: Optional[Dict[str, str]] = None

class PreferenceUpdateRequest(BaseModel):
    notification_type: str
    email_enabled: Optional[bool] = None
    inapp_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    digest_frequency: Optional[str] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = None

# Core notification endpoints
@router.post("/notifications/send")
async def send_notification(
    request: NotificationRequest,
    background_tasks: BackgroundTasks
):
    """Send a notification through appropriate channels"""
    try:
        from api.websocket import send_notification_to_user
        
        # Send in-app notification
        notification_id = await send_notification_to_user(
            user_id=request.user_id,
            notification_type=request.notification_type,
            title=request.title,
            message=request.message,
            data=request.data,
            priority=request.priority,
            tenant_id=request.tenant_id
        )
        
        # Send to other channels based on preferences or explicit channels
        if request.channels:
            enabled_channels = request.channels
        else:
            # Get user preferences
            preference_service = get_preference_service()
            enabled_channels = await preference_service.get_notification_channels(
                request.user_id, request.notification_type
            )
        
        # Send email if enabled
        if "email" in enabled_channels:
            email_service = get_email_service()
            # Would need to get user email from user service
            # For now, placeholder implementation
            pass
        
        # Send SMS if enabled
        if "sms" in enabled_channels:
            sms_service = get_sms_service()
            # Would need to get user phone from user service
            # For now, placeholder implementation
            pass
        
        # Send webhook if enabled
        if "webhook" in enabled_channels:
            webhook_service = get_webhook_service()
            background_tasks.add_task(
                webhook_service.send_webhooks_to_user_endpoints,
                user_id=request.user_id,
                notification_type=request.notification_type,
                payload={
                    "event": request.notification_type,
                    "title": request.title,
                    "message": request.message,
                    "data": request.data or {},
                    "timestamp": datetime.now().isoformat()
                },
                tenant_id=request.tenant_id
            )
        
        return {
            "success": True,
            "notification_id": notification_id,
            "channels_used": enabled_channels
        }
        
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/email")
async def send_email_notification(
    request: EmailNotificationRequest,
    email_service = Depends(get_email_service)
):
    """Send email notification"""
    try:
        success = await email_service.send_notification(
            user_id=request.user_id,
            to_email=request.to_email,
            subject=request.subject,
            body=request.body,
            tenant_id=request.tenant_id,
            template_id=request.template_id,
            template_vars=request.template_vars,
            from_email=request.from_email,
            from_name=request.from_name
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/sms")
async def send_sms_notification(
    request: SMSNotificationRequest,
    sms_service = Depends(get_sms_service)
):
    """Send SMS notification"""
    try:
        success = await sms_service.send_notification(
            user_id=request.user_id,
            to_phone=request.to_phone,
            message=request.message,
            tenant_id=request.tenant_id,
            template_id=request.template_id,
            template_vars=request.template_vars
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/webhook")
async def send_webhook_notification(
    request: WebhookRequest,
    webhook_service = Depends(get_webhook_service)
):
    """Send webhook notification"""
    try:
        success = await webhook_service.send_webhook(
            user_id=request.user_id,
            webhook_url=request.webhook_url,
            payload=request.payload,
            tenant_id=request.tenant_id,
            notification_type=request.notification_type,
            headers=request.headers,
            secret_key=request.secret_key
        )
        
        return {"success": success}
        
    except Exception as e:
        logger.error(f"Error sending webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Template management endpoints
@router.post("/templates")
async def create_template(
    request: TemplateRequest,
    tenant_id: Optional[str] = None,
    template_service = Depends(get_template_service)
):
    """Create a new notification template"""
    try:
        success = await template_service.create_template(
            template_id=request.template_id,
            name=request.name,
            template_type=request.type,
            subject_template=request.subject_template,
            body_template=request.body_template,
            sms_template=request.sms_template,
            description=request.description,
            variables=request.variables,
            tenant_id=tenant_id
        )
        
        if success:
            return {"message": "Template created successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to create template")
            
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates")
async def list_templates(
    tenant_id: Optional[str] = None,
    template_type: Optional[str] = None,
    include_system: bool = True,
    template_service = Depends(get_template_service)
):
    """List notification templates"""
    try:
        templates = await template_service.list_templates(
            tenant_id=tenant_id,
            template_type=template_type,
            include_system=include_system
        )
        
        return {"templates": templates}
        
    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    tenant_id: Optional[str] = None,
    template_service = Depends(get_template_service)
):
    """Get a specific template"""
    try:
        template = await template_service.get_template(template_id, tenant_id)
        
        if template:
            return template
        else:
            raise HTTPException(status_code=404, detail="Template not found")
            
    except Exception as e:
        logger.error(f"Error getting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    updates: Dict[str, Any] = Body(...),
    tenant_id: Optional[str] = None,
    template_service = Depends(get_template_service)
):
    """Update a template"""
    try:
        success = await template_service.update_template(
            template_id=template_id,
            tenant_id=tenant_id,
            **updates
        )
        
        if success:
            return {"message": "Template updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update template")
            
    except Exception as e:
        logger.error(f"Error updating template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    tenant_id: Optional[str] = None,
    template_service = Depends(get_template_service)
):
    """Delete a template"""
    try:
        success = await template_service.delete_template(template_id, tenant_id)
        
        if success:
            return {"message": "Template deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete template")
            
    except Exception as e:
        logger.error(f"Error deleting template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/templates/{template_id}/render")
async def render_template(
    template_id: str,
    variables: Dict[str, Any] = Body(...),
    output_type: str = "email",
    tenant_id: Optional[str] = None,
    template_service = Depends(get_template_service)
):
    """Render a template with variables"""
    try:
        result = await template_service.render_template(
            template_id=template_id,
            variables=variables,
            output_type=output_type,
            tenant_id=tenant_id
        )
        
        if result:
            return result
        else:
            raise HTTPException(status_code=400, detail="Failed to render template")
            
    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# User preferences endpoints
@router.get("/preferences/{user_id}")
async def get_user_preferences(
    user_id: str,
    notification_type: Optional[str] = None,
    preference_service = Depends(get_preference_service)
):
    """Get user notification preferences"""
    try:
        preferences = await preference_service.get_user_preferences(
            user_id=user_id,
            notification_type=notification_type
        )
        
        return {"preferences": preferences}
        
    except Exception as e:
        logger.error(f"Error getting preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/preferences/{user_id}")
async def update_user_preferences(
    user_id: str,
    request: PreferenceUpdateRequest,
    tenant_id: Optional[str] = None,
    preference_service = Depends(get_preference_service)
):
    """Update user notification preferences"""
    try:
        # Convert time strings to time objects if provided
        quiet_hours_start = None
        quiet_hours_end = None
        
        if request.quiet_hours_start:
            hour, minute = map(int, request.quiet_hours_start.split(":"))
            quiet_hours_start = f"{hour:02d}:{minute:02d}"
        
        if request.quiet_hours_end:
            hour, minute = map(int, request.quiet_hours_end.split(":"))
            quiet_hours_end = f"{hour:02d}:{minute:02d}"
        
        success = await preference_service.update_user_preferences(
            user_id=user_id,
            notification_type=request.notification_type,
            email_enabled=request.email_enabled,
            inapp_enabled=request.inapp_enabled,
            sms_enabled=request.sms_enabled,
            webhook_enabled=request.webhook_enabled,
            digest_frequency=request.digest_frequency,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            timezone=request.timezone,
            tenant_id=tenant_id
        )
        
        if success:
            return {"message": "Preferences updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update preferences")
            
    except Exception as e:
        logger.error(f"Error updating preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/preferences/{user_id}/bulk")
async def update_bulk_preferences(
    user_id: str,
    preferences: Dict[str, Dict[str, Any]] = Body(...),
    tenant_id: Optional[str] = None,
    preference_service = Depends(get_preference_service)
):
    """Update multiple notification preferences at once"""
    try:
        success = await preference_service.update_bulk_preferences(
            user_id=user_id,
            preferences=preferences,
            tenant_id=tenant_id
        )
        
        if success:
            return {"message": "Preferences updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update preferences")
            
    except Exception as e:
        logger.error(f"Error updating bulk preferences: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Webhook endpoints management
@router.post("/webhooks/endpoints")
async def create_webhook_endpoint(
    user_id: str,
    request: WebhookEndpointRequest,
    tenant_id: Optional[str] = None,
    webhook_service = Depends(get_webhook_service)
):
    """Register a webhook endpoint"""
    try:
        endpoint_id = await webhook_service.register_webhook_endpoint(
            user_id=user_id,
            name=request.name,
            url=request.url,
            tenant_id=tenant_id,
            notification_types=request.notification_types,
            secret_key=request.secret_key
        )
        
        return {"endpoint_id": endpoint_id, "message": "Webhook endpoint created successfully"}
        
    except Exception as e:
        logger.error(f"Error creating webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhooks/endpoints/{user_id}")
async def get_user_webhooks(
    user_id: str,
    webhook_service = Depends(get_webhook_service)
):
    """Get user's webhook endpoints"""
    try:
        endpoints = await webhook_service.get_user_webhooks(user_id)
        return {"endpoints": endpoints}
        
    except Exception as e:
        logger.error(f"Error getting webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/webhooks/endpoints/{endpoint_id}")
async def update_webhook_endpoint(
    endpoint_id: int,
    user_id: str,
    updates: Dict[str, Any] = Body(...),
    webhook_service = Depends(get_webhook_service)
):
    """Update webhook endpoint"""
    try:
        success = await webhook_service.update_webhook_endpoint(
            endpoint_id=endpoint_id,
            user_id=user_id,
            **updates
        )
        
        if success:
            return {"message": "Webhook endpoint updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update webhook endpoint")
            
    except Exception as e:
        logger.error(f"Error updating webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/webhooks/endpoints/{endpoint_id}")
async def delete_webhook_endpoint(
    endpoint_id: int,
    user_id: str,
    webhook_service = Depends(get_webhook_service)
):
    """Delete webhook endpoint"""
    try:
        success = await webhook_service.delete_webhook_endpoint(endpoint_id, user_id)
        
        if success:
            return {"message": "Webhook endpoint deleted successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete webhook endpoint")
            
    except Exception as e:
        logger.error(f"Error deleting webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhooks/endpoints/{endpoint_id}/test")
async def test_webhook_endpoint(
    endpoint_id: int,
    user_id: str,
    webhook_service = Depends(get_webhook_service)
):
    """Test a webhook endpoint"""
    try:
        result = await webhook_service.test_webhook_endpoint(endpoint_id, user_id)
        return result
        
    except Exception as e:
        logger.error(f"Error testing webhook endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Digest management endpoints
@router.post("/digest/send/{user_id}")
async def send_immediate_digest(
    user_id: str,
    digest_type: str = "daily",
    tenant_id: Optional[str] = None,
    digest_service = Depends(get_digest_service)
):
    """Send immediate digest to user"""
    try:
        success = await digest_service.send_immediate_digest(
            user_id=user_id,
            digest_type=digest_type,
            tenant_id=tenant_id
        )
        
        if success:
            return {"message": "Digest sent successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to send digest")
            
    except Exception as e:
        logger.error(f"Error sending digest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/digest/queue")
async def get_digest_queue_status(digest_service = Depends(get_digest_service)):
    """Get digest queue status"""
    try:
        status = await digest_service.get_digest_queue_status()
        return {"queue_status": status}
        
    except Exception as e:
        logger.error(f"Error getting digest queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# SMS specific endpoints
@router.post("/sms/validate-phone")
async def validate_phone_number(
    phone: str = Body(..., embed=True),
    sms_service = Depends(get_sms_service)
):
    """Validate phone number format"""
    try:
        result = await sms_service.validate_phone_number(phone)
        return result
        
    except Exception as e:
        logger.error(f"Error validating phone: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sms/history/{user_id}")
async def get_sms_history(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    sms_service = Depends(get_sms_service)
):
    """Get SMS history for user"""
    try:
        history = await sms_service.get_sms_history(user_id, limit)
        return {"history": history}
        
    except Exception as e:
        logger.error(f"Error getting SMS history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sms/account-info")
async def get_sms_account_info(sms_service = Depends(get_sms_service)):
    """Get SMS account information"""
    try:
        info = await sms_service.get_account_info()
        
        if info:
            return info
        else:
            raise HTTPException(status_code=503, detail="SMS service not configured")
            
    except Exception as e:
        logger.error(f"Error getting SMS account info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Status and monitoring endpoints
@router.get("/notifications/{notification_id}/status")
async def get_notification_status(
    notification_id: str,
    service_type: str = Query(..., regex="^(email|sms|webhook)$"),
    email_service = Depends(get_email_service),
    sms_service = Depends(get_sms_service),
    webhook_service = Depends(get_webhook_service)
):
    """Get notification status"""
    try:
        if service_type == "email":
            status = await email_service.get_email_status(notification_id)
        elif service_type == "sms":
            status = await sms_service.get_delivery_status(notification_id)
        elif service_type == "webhook":
            status = await webhook_service.get_webhook_status(notification_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid service type")
        
        if status:
            return status
        else:
            raise HTTPException(status_code=404, detail="Notification not found")
            
    except Exception as e:
        logger.error(f"Error getting notification status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/retry/failed")
async def retry_failed_notifications(
    service_type: str = Query(..., regex="^(email|sms|webhook)$"),
    background_tasks: BackgroundTasks,
    email_service = Depends(get_email_service),
    sms_service = Depends(get_sms_service),
    webhook_service = Depends(get_webhook_service)
):
    """Retry failed notifications"""
    try:
        if service_type == "email":
            task = background_tasks.add_task(email_service.retry_failed_emails)
        elif service_type == "sms":
            task = background_tasks.add_task(sms_service.retry_failed_sms)
        elif service_type == "webhook":
            # Webhook retries are handled by background processor
            return {"message": "Webhook retries are handled automatically"}
        
        return {"message": f"Retry task started for {service_type} notifications"}
        
    except Exception as e:
        logger.error(f"Error starting retry: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system/configuration")
async def get_system_configuration():
    """Get current system configuration"""
    return {
        "service_name": settings.SERVICE_NAME,
        "port": settings.PORT,
        "email_provider": settings.EMAIL_PROVIDER,
        "email_configured": settings.email_configured,
        "sms_configured": settings.sms_configured,
        "digest_enabled": settings.DIGEST_ENABLED,
        "notification_types": settings.NOTIFICATION_TYPES,
        "priority_levels": settings.PRIORITY_LEVELS,
        "supported_channels": ["email", "inapp", "sms", "webhook"]
    }