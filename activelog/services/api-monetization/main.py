"""
API Monetization Service
Main FastAPI application for comprehensive API monetization and management
"""

import asyncio
import logging
import uvicorn
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

# Import monetization managers
from core.usage_metering import UsageMeteringManager
from core.api_key_management import APIKeyManager
from core.rate_limiting import RateLimitingManager
from core.developer_portal import DeveloperPortalManager
from core.api_marketplace import APIMarketplaceManager
from core.revenue_sharing import RevenueSharingManager
from core.usage_analytics import UsageAnalyticsManager

# Import data models
from models.monetization_models import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/api-monetization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="API Monetization Service",
    description="Comprehensive API monetization and developer ecosystem platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global managers
usage_manager = None
key_manager = None
rate_limiter = None
portal_manager = None
marketplace_manager = None
revenue_manager = None
analytics_manager = None

@app.on_event("startup")
async def startup_event():
    """Initialize all monetization managers on startup"""
    global usage_manager, key_manager, rate_limiter, portal_manager
    global marketplace_manager, revenue_manager, analytics_manager
    
    logger.info("Starting API Monetization Service initialization...")
    
    try:
        # Initialize managers
        usage_manager = UsageMeteringManager()
        key_manager = APIKeyManager()
        rate_limiter = RateLimitingManager()
        portal_manager = DeveloperPortalManager()
        marketplace_manager = APIMarketplaceManager()
        revenue_manager = RevenueSharingManager()
        analytics_manager = UsageAnalyticsManager()
        
        # Initialize all managers
        await usage_manager.initialize()
        await key_manager.initialize()
        await rate_limiter.initialize()
        await portal_manager.initialize()
        await marketplace_manager.initialize()
        await revenue_manager.initialize()
        await analytics_manager.initialize()
        
        # Start background monitoring tasks
        asyncio.create_task(usage_monitoring_loop())
        asyncio.create_task(billing_processing_loop())
        asyncio.create_task(analytics_aggregation_loop())
        asyncio.create_task(rate_limit_cleanup_loop())
        asyncio.create_task(revenue_calculation_loop())
        
        logger.info("API Monetization Service initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize API Monetization Service: {e}")
        raise

# Usage Metering Endpoints
@app.post("/usage/track", response_model=Dict[str, Any])
async def track_api_usage(request: UsageTrackingRequest):
    """Track API usage for billing"""
    try:
        usage_id = await usage_manager.track_usage(
            api_key=request.api_key,
            endpoint=request.endpoint,
            method=request.method,
            request_size=request.request_size,
            response_size=request.response_size,
            duration_ms=request.duration_ms,
            status_code=request.status_code,
            metadata=request.metadata
        )
        return {"status": "success", "usage_id": usage_id}
    except Exception as e:
        logger.error(f"Failed to track usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/{api_key}/current")
async def get_current_usage(api_key: str):
    """Get current usage for API key"""
    try:
        usage_data = await usage_manager.get_current_usage(api_key)
        return usage_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/usage/{api_key}/history")
async def get_usage_history(
    api_key: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    granularity: str = "daily"
):
    """Get usage history for API key"""
    try:
        history = await usage_manager.get_usage_history(
            api_key, start_date, end_date, granularity
        )
        return history
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/billing/generate")
async def generate_bill(request: BillingRequest, background_tasks: BackgroundTasks):
    """Generate bill for customer"""
    try:
        background_tasks.add_task(usage_manager.generate_bill, request.customer_id, request.billing_period)
        return {"status": "bill_generation_started", "customer_id": request.customer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/billing/{customer_id}/invoices")
async def get_customer_invoices(customer_id: str):
    """Get customer invoices"""
    try:
        invoices = await usage_manager.get_customer_invoices(customer_id)
        return invoices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Key Management Endpoints
@app.post("/keys/create", response_model=Dict[str, Any])
async def create_api_key(request: APIKeyRequest):
    """Create new API key"""
    try:
        key_data = await key_manager.create_api_key(
            developer_id=request.developer_id,
            key_name=request.key_name,
            tier_id=request.tier_id,
            permissions=request.permissions,
            metadata=request.metadata
        )
        return {"status": "success", "key_data": key_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keys/{api_key}/validate")
async def validate_api_key(api_key: str):
    """Validate API key"""
    try:
        validation_result = await key_manager.validate_key(api_key)
        return validation_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/keys/{api_key}/rotate")
async def rotate_api_key(api_key: str):
    """Rotate API key"""
    try:
        new_key = await key_manager.rotate_key(api_key)
        return {"status": "success", "new_key": new_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/keys/{api_key}")
async def revoke_api_key(api_key: str):
    """Revoke API key"""
    try:
        success = await key_manager.revoke_key(api_key)
        return {"status": "success" if success else "failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keys/developer/{developer_id}")
async def get_developer_keys(developer_id: str):
    """Get all keys for developer"""
    try:
        keys = await key_manager.get_developer_keys(developer_id)
        return keys
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Rate Limiting Endpoints
@app.post("/rate-limit/check")
async def check_rate_limit(request: RateLimitCheckRequest):
    """Check if request is within rate limits"""
    try:
        result = await rate_limiter.check_rate_limit(
            api_key=request.api_key,
            endpoint=request.endpoint,
            client_ip=request.client_ip
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/rate-limit/tiers", response_model=Dict[str, Any])
async def create_rate_limit_tier(request: RateLimitTierRequest):
    """Create rate limiting tier"""
    try:
        tier_id = await rate_limiter.create_tier(
            tier_name=request.tier_name,
            limits=request.limits,
            tier_config=request.tier_config
        )
        return {"status": "success", "tier_id": tier_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rate-limit/tiers")
async def get_rate_limit_tiers():
    """Get all rate limiting tiers"""
    try:
        tiers = await rate_limiter.get_all_tiers()
        return tiers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/rate-limit/{api_key}/status")
async def get_rate_limit_status(api_key: str):
    """Get current rate limit status for API key"""
    try:
        status_data = await rate_limiter.get_key_status(api_key)
        return status_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Developer Portal Endpoints
@app.get("/portal", response_class=HTMLResponse)
async def developer_portal_home(request: Request):
    """Developer portal home page"""
    try:
        portal_data = await portal_manager.get_portal_data()
        return templates.TemplateResponse("portal_home.html", {
            "request": request,
            "portal_data": portal_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portal/developers/register", response_model=Dict[str, Any])
async def register_developer(request: DeveloperRegistrationRequest):
    """Register new developer"""
    try:
        developer_id = await portal_manager.register_developer(
            email=request.email,
            company_name=request.company_name,
            developer_info=request.developer_info
        )
        return {"status": "success", "developer_id": developer_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portal/developers/{developer_id}/dashboard", response_class=HTMLResponse)
async def developer_dashboard(request: Request, developer_id: str):
    """Developer dashboard"""
    try:
        dashboard_data = await portal_manager.get_developer_dashboard(developer_id)
        return templates.TemplateResponse("developer_dashboard.html", {
            "request": request,
            "dashboard_data": dashboard_data,
            "developer_id": developer_id
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portal/documentation/{api_id}")
async def get_api_documentation(api_id: str):
    """Get API documentation"""
    try:
        docs = await portal_manager.get_api_documentation(api_id)
        return docs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portal/support/tickets", response_model=Dict[str, Any])
async def create_support_ticket(request: SupportTicketRequest):
    """Create support ticket"""
    try:
        ticket_id = await portal_manager.create_support_ticket(
            developer_id=request.developer_id,
            subject=request.subject,
            description=request.description,
            priority=request.priority
        )
        return {"status": "success", "ticket_id": ticket_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# API Marketplace Endpoints
@app.get("/marketplace", response_class=HTMLResponse)
async def api_marketplace(request: Request):
    """API marketplace homepage"""
    try:
        marketplace_data = await marketplace_manager.get_marketplace_data()
        return templates.TemplateResponse("marketplace.html", {
            "request": request,
            "marketplace_data": marketplace_data
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/marketplace/apis/publish", response_model=Dict[str, Any])
async def publish_api(request: APIPublishRequest):
    """Publish API to marketplace"""
    try:
        api_id = await marketplace_manager.publish_api(
            provider_id=request.provider_id,
            api_info=request.api_info,
            pricing_model=request.pricing_model,
            documentation=request.documentation
        )
        return {"status": "success", "api_id": api_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/marketplace/apis")
async def browse_apis(
    category: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    """Browse marketplace APIs"""
    try:
        apis = await marketplace_manager.browse_apis(
            category=category,
            search_query=search,
            page=page,
            limit=limit
        )
        return apis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/marketplace/apis/{api_id}")
async def get_api_details(api_id: str):
    """Get detailed API information"""
    try:
        api_details = await marketplace_manager.get_api_details(api_id)
        return api_details
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/marketplace/apis/{api_id}/subscribe")
async def subscribe_to_api(api_id: str, request: APISubscriptionRequest):
    """Subscribe to marketplace API"""
    try:
        subscription_id = await marketplace_manager.subscribe_to_api(
            api_id=api_id,
            developer_id=request.developer_id,
            tier_id=request.tier_id
        )
        return {"status": "success", "subscription_id": subscription_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/marketplace/apis/{api_id}/reviews")
async def get_api_reviews(api_id: str):
    """Get API reviews and ratings"""
    try:
        reviews = await marketplace_manager.get_api_reviews(api_id)
        return reviews
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/marketplace/apis/{api_id}/reviews")
async def submit_api_review(api_id: str, request: APIReviewRequest):
    """Submit API review"""
    try:
        review_id = await marketplace_manager.submit_review(
            api_id=api_id,
            developer_id=request.developer_id,
            rating=request.rating,
            review_text=request.review_text
        )
        return {"status": "success", "review_id": review_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Revenue Sharing Endpoints
@app.post("/revenue/configure")
async def configure_revenue_sharing(request: RevenueSharingRequest):
    """Configure revenue sharing for API"""
    try:
        config_id = await revenue_manager.configure_revenue_sharing(
            api_id=request.api_id,
            sharing_model=request.sharing_model,
            participants=request.participants
        )
        return {"status": "success", "config_id": config_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/revenue/{api_id}/report")
async def get_revenue_report(
    api_id: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get revenue report for API"""
    try:
        report = await revenue_manager.get_revenue_report(
            api_id, start_date, end_date
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/revenue/distribute")
async def distribute_revenue(request: RevenueDistributionRequest, background_tasks: BackgroundTasks):
    """Distribute revenue to participants"""
    try:
        background_tasks.add_task(
            revenue_manager.distribute_revenue,
            request.api_id,
            request.period
        )
        return {"status": "revenue_distribution_started", "api_id": request.api_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/revenue/provider/{provider_id}/earnings")
async def get_provider_earnings(provider_id: str):
    """Get earnings for API provider"""
    try:
        earnings = await revenue_manager.get_provider_earnings(provider_id)
        return earnings
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Usage Analytics Endpoints
@app.get("/analytics/overview")
async def get_analytics_overview():
    """Get analytics overview"""
    try:
        overview = await analytics_manager.get_analytics_overview()
        return overview
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/{api_key}/metrics")
async def get_api_key_metrics(
    api_key: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metrics: Optional[List[str]] = None
):
    """Get metrics for specific API key"""
    try:
        data = await analytics_manager.get_api_key_metrics(
            api_key, start_date, end_date, metrics or []
        )
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/apis/{api_id}/performance")
async def get_api_performance_metrics(api_id: str):
    """Get API performance metrics"""
    try:
        metrics = await analytics_manager.get_api_performance_metrics(api_id)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/developers/{developer_id}/insights")
async def get_developer_insights(developer_id: str):
    """Get developer usage insights"""
    try:
        insights = await analytics_manager.get_developer_insights(developer_id)
        return insights
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/revenue/trends")
async def get_revenue_trends(
    period: str = "monthly",
    api_id: Optional[str] = None
):
    """Get revenue trends analysis"""
    try:
        trends = await analytics_manager.get_revenue_trends(period, api_id)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analytics/reports/custom")
async def generate_custom_report(request: CustomReportRequest):
    """Generate custom analytics report"""
    try:
        report_id = await analytics_manager.generate_custom_report(
            report_config=request.report_config,
            filters=request.filters,
            metrics=request.metrics
        )
        return {"status": "success", "report_id": report_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Admin Dashboard Endpoints
@app.get("/admin/dashboard")
async def admin_dashboard():
    """Admin dashboard overview"""
    try:
        dashboard_data = {
            "usage_summary": await usage_manager.get_usage_summary(),
            "key_statistics": await key_manager.get_key_statistics(),
            "rate_limit_stats": await rate_limiter.get_rate_limit_statistics(),
            "marketplace_stats": await marketplace_manager.get_marketplace_statistics(),
            "revenue_summary": await revenue_manager.get_revenue_summary(),
            "analytics_overview": await analytics_manager.get_analytics_overview()
        }
        return dashboard_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/health")
async def system_health_check():
    """System health check"""
    try:
        health_data = {
            "usage_metering": await usage_manager.health_check(),
            "key_management": await key_manager.health_check(),
            "rate_limiting": await rate_limiter.health_check(),
            "developer_portal": await portal_manager.health_check(),
            "marketplace": await marketplace_manager.health_check(),
            "revenue_sharing": await revenue_manager.health_check(),
            "analytics": await analytics_manager.health_check(),
            "system_status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        return health_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Webhook Endpoints
@app.post("/webhooks/payment")
async def handle_payment_webhook(request: PaymentWebhookRequest):
    """Handle payment provider webhooks"""
    try:
        await usage_manager.process_payment_webhook(request.webhook_data)
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Payment webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhooks/usage")
async def handle_usage_webhook(request: UsageWebhookRequest):
    """Handle external usage webhooks"""
    try:
        await usage_manager.process_usage_webhook(request.usage_data)
        return {"status": "processed"}
    except Exception as e:
        logger.error(f"Usage webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Background monitoring tasks
async def usage_monitoring_loop():
    """Background task to monitor API usage"""
    while True:
        try:
            await usage_manager.monitor_usage()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logger.error(f"Usage monitoring error: {e}")
            await asyncio.sleep(60)

async def billing_processing_loop():
    """Background task to process billing"""
    while True:
        try:
            await usage_manager.process_billing()
            await asyncio.sleep(3600)  # Process every hour
        except Exception as e:
            logger.error(f"Billing processing error: {e}")
            await asyncio.sleep(3600)

async def analytics_aggregation_loop():
    """Background task to aggregate analytics"""
    while True:
        try:
            await analytics_manager.aggregate_analytics()
            await asyncio.sleep(300)  # Aggregate every 5 minutes
        except Exception as e:
            logger.error(f"Analytics aggregation error: {e}")
            await asyncio.sleep(300)

async def rate_limit_cleanup_loop():
    """Background task to cleanup rate limit data"""
    while True:
        try:
            await rate_limiter.cleanup_expired_limits()
            await asyncio.sleep(1800)  # Cleanup every 30 minutes
        except Exception as e:
            logger.error(f"Rate limit cleanup error: {e}")
            await asyncio.sleep(1800)

async def revenue_calculation_loop():
    """Background task to calculate revenue"""
    while True:
        try:
            await revenue_manager.calculate_revenue()
            await asyncio.sleep(86400)  # Calculate daily
        except Exception as e:
            logger.error(f"Revenue calculation error: {e}")
            await asyncio.sleep(86400)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "service": "api-monetization"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8111)