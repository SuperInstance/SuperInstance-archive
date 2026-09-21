"""
ActiveLog Workflows Service

Comprehensive workflow automation service with:
- IFTTT-style triggers and actions
- Zapier-compatible webhook system
- Custom workflow designer API
- Scheduled workflows (cron-style)
- Conditional logic and branching
- Integration with external services
- Workflow templates marketplace
"""

import asyncio
import logging
import logging.config
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from core.config import settings, LOGGING_CONFIG
from core.database import init_db, close_db
from workflow.workflow_engine import WorkflowEngine
from scheduler.scheduler import WorkflowScheduler
from webhooks.webhook_manager import WebhookManager
from integrations.integration_manager import IntegrationManager
from templates.template_manager import TemplateManager
from api.routes import router as api_router
from middleware.auth import AuthMiddleware
from middleware.rate_limit import RateLimitMiddleware

# Setup logging
logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Global managers
workflow_engine = None
workflow_scheduler = None
webhook_manager = None
integration_manager = None
template_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global workflow_engine, workflow_scheduler, webhook_manager, integration_manager, template_manager
    
    # Startup
    logger.info("Starting ActiveLog Workflows Service...")
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Initialize database
    await init_db()
    
    # Initialize managers
    workflow_engine = WorkflowEngine()
    workflow_scheduler = WorkflowScheduler()
    webhook_manager = WebhookManager()
    integration_manager = IntegrationManager()
    template_manager = TemplateManager()
    
    # Initialize all components
    await workflow_engine.initialize()
    await workflow_scheduler.initialize()
    await webhook_manager.initialize()
    await integration_manager.initialize()
    await template_manager.initialize()
    
    # Set global references for API routes
    import api.routes as api_routes_module
    api_routes_module.workflow_engine = workflow_engine
    api_routes_module.workflow_scheduler = workflow_scheduler
    api_routes_module.webhook_manager = webhook_manager
    api_routes_module.integration_manager = integration_manager
    api_routes_module.template_manager = template_manager
    
    # Start background services
    asyncio.create_task(workflow_scheduler.start())
    asyncio.create_task(webhook_manager.start_cleanup_task())
    
    logger.info(f"Workflows Service started on port {settings.PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Workflows Service...")
    
    if workflow_scheduler:
        await workflow_scheduler.stop()
    if workflow_engine:
        await workflow_engine.cleanup()
    if webhook_manager:
        await webhook_manager.cleanup()
    if integration_manager:
        await integration_manager.cleanup()
    if template_manager:
        await template_manager.cleanup()
    
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="ActiveLog Workflows Service",
    description="Comprehensive workflow automation service with IFTTT-style triggers and actions",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

# Static files (for workflow designer UI)
if Path("static").exists():
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Include API routes
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "ActiveLog Workflows Service",
        "version": "1.0.0",
        "description": "Comprehensive workflow automation service",
        "features": [
            "IFTTT-style triggers and actions",
            "Zapier-compatible webhooks",
            "Custom workflow designer",
            "Scheduled workflows",
            "Conditional logic and branching",
            "External service integrations",
            "Template marketplace"
        ],
        "docs_url": "/docs",
        "health_url": "/health"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Basic health checks
        health_status = {
            "status": "healthy",
            "timestamp": asyncio.get_event_loop().time(),
            "version": "1.0.0",
            "components": {}
        }
        
        # Check database
        try:
            from core.database import db_manager
            await db_manager.database.execute("SELECT 1")
            health_status["components"]["database"] = "healthy"
        except Exception as e:
            health_status["components"]["database"] = f"unhealthy: {str(e)}"
            health_status["status"] = "degraded"
        
        # Check workflow engine
        if workflow_engine:
            health_status["components"]["workflow_engine"] = "healthy"
            health_status["components"]["active_executions"] = len(workflow_engine.active_executions)
        else:
            health_status["components"]["workflow_engine"] = "not initialized"
        
        # Check scheduler
        if workflow_scheduler:
            health_status["components"]["scheduler"] = "healthy" if workflow_scheduler.is_running else "stopped"
        else:
            health_status["components"]["scheduler"] = "not initialized"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": asyncio.get_event_loop().time()
        }

@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics endpoint"""
    try:
        metrics_data = {
            "workflows_total": 0,
            "executions_total": 0,
            "active_executions": 0,
            "webhooks_total": 0,
            "integrations_total": 0,
            "templates_total": 0
        }
        
        if workflow_engine:
            metrics_data.update(await workflow_engine.get_metrics())
        
        if workflow_scheduler:
            metrics_data.update(workflow_scheduler.get_metrics())
        
        if webhook_manager:
            metrics_data.update(webhook_manager.get_metrics())
        
        if integration_manager:
            metrics_data.update(integration_manager.get_metrics())
        
        if template_manager:
            metrics_data.update(template_manager.get_metrics())
        
        return metrics_data
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )

# Webhook endpoint for external services (like Zapier)
@app.post("/webhook/{endpoint_id}")
async def webhook_handler(endpoint_id: str, request: Request):
    """Handle incoming webhook requests"""
    try:
        if not webhook_manager:
            raise HTTPException(status_code=503, detail="Webhook manager not initialized")
        
        # Get request data
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            data = await request.json()
        elif "application/x-www-form-urlencoded" in content_type:
            form_data = await request.form()
            data = dict(form_data)
        else:
            data = await request.body()
        
        # Process webhook
        result = await webhook_manager.process_webhook(
            endpoint_id=endpoint_id,
            data=data,
            headers=dict(request.headers),
            method=request.method
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Webhook processing failed for {endpoint_id}: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

# Template marketplace endpoints
@app.get("/marketplace/featured")
async def featured_templates():
    """Get featured workflow templates"""
    try:
        if not template_manager:
            raise HTTPException(status_code=503, detail="Template manager not initialized")
        
        templates = await template_manager.get_featured_templates()
        return {"featured_templates": templates}
        
    except Exception as e:
        logger.error(f"Failed to get featured templates: {e}")
        raise HTTPException(status_code=500, detail="Failed to get featured templates")

# Development endpoints (only in debug mode)
if settings.DEBUG:
    @app.post("/dev/reset-db")
    async def reset_database():
        """Reset database (development only)"""
        try:
            from core.database import db_manager
            await db_manager.drop_tables()
            await db_manager.create_tables()
            return {"message": "Database reset successfully"}
        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            raise HTTPException(status_code=500, detail="Database reset failed")
    
    @app.get("/dev/test-workflow")
    async def test_workflow():
        """Create a test workflow (development only)"""
        try:
            test_workflow_data = {
                "name": "Test Workflow",
                "description": "A simple test workflow",
                "owner_id": "test-user-id",
                "trigger_config": {
                    "type": "webhook",
                    "config": {}
                },
                "actions": [
                    {
                        "type": "http_request",
                        "name": "Test HTTP Request",
                        "config": {
                            "url": "https://httpbin.org/post",
                            "method": "POST",
                            "data": {"message": "Hello from test workflow"}
                        }
                    }
                ]
            }
            
            from core.database import db_manager
            workflow_id = await db_manager.create_workflow(test_workflow_data)
            
            return {
                "message": "Test workflow created",
                "workflow_id": workflow_id,
                "webhook_url": f"/webhook/{workflow_id}"
            }
            
        except Exception as e:
            logger.error(f"Test workflow creation failed: {e}")
            raise HTTPException(status_code=500, detail="Test workflow creation failed")

def main():
    """Main entry point"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=1,  # Use 1 worker for proper lifespan management
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )

if __name__ == "__main__":
    main()