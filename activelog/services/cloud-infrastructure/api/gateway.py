"""
Secure API Gateway for Cloud Infrastructure
Provides secure API-only interconnection layer with authentication, rate limiting, and monitoring
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from dataclasses import asdict
import json
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, WebSocket, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from core.models import (
    User, CreateInstanceRequest, InstanceResponse, GameNightEventRequest,
    BillingUsageRequest, BillingUsageResponse, ScalingConfigRequest,
    SystemMetrics, current_timestamp, generate_id
)

from isolation.access_control import AccessControlManager, Permission
from billing.usage_analytics import (
    UsageAnalytics, AnalyticsPeriod, CostDimension, 
    ResourceUtilization, CostAttribution, UsagePattern, ComparativeAnalysis
)
from billing.report_generator import (
    ReportGenerator, ReportRequest, ReportType, ReportFormat
)
from billing.user_friendly_dashboard import UserFriendlyFinanceDashboard
from billing.cost_calculator import CostCalculator, UsagePattern
from billing.payment_processor import PaymentProcessor, PaymentStatus, InvoiceStatus, PaymentMethodType
from billing.forecasting import UsageForecaster, ForecastModel, BudgetAlertLevel

# Import service managers (these would be injected in a real implementation)
class ServiceRegistry:
    """Registry for all cloud infrastructure services"""
    
    def __init__(self):
        self.ec2_provisioner = None
        self.billing_engine = None
        self.auto_scaler = None
        self.tenant_manager = None
        self.access_control = None
        self.usage_tracker = None
        self.database_manager = None
        self.usage_analytics = None
        self.report_generator = None
        self.user_friendly_dashboard = None
        self.cost_calculator = None
        self.payment_processor = None
        self.usage_forecaster = None
        self.organization_manager = None
    
    def register_services(self, **services):
        """Register services with the registry"""
        for name, service in services.items():
            setattr(self, name, service)

# Global service registry
service_registry = ServiceRegistry()

class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self):
        self.buckets = {}
        self.cleanup_task = None
    
    def is_allowed(self, identifier: str, max_requests: int = 100, 
                  time_window: int = 60) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under rate limit"""
        current_time = time.time()
        
        if identifier not in self.buckets:
            self.buckets[identifier] = {
                'tokens': max_requests,
                'last_refill': current_time,
                'max_tokens': max_requests,
                'refill_rate': max_requests / time_window
            }
        
        bucket = self.buckets[identifier]
        
        # Refill tokens based on time passed
        time_passed = current_time - bucket['last_refill']
        tokens_to_add = time_passed * bucket['refill_rate']
        bucket['tokens'] = min(bucket['max_tokens'], bucket['tokens'] + tokens_to_add)
        bucket['last_refill'] = current_time
        
        # Check if request is allowed
        if bucket['tokens'] >= 1:
            bucket['tokens'] -= 1
            return True, {
                'allowed': True,
                'remaining_tokens': int(bucket['tokens']),
                'reset_time': current_time + (bucket['max_tokens'] - bucket['tokens']) / bucket['refill_rate']
            }
        else:
            return False, {
                'allowed': False,
                'remaining_tokens': 0,
                'reset_time': current_time + (1 - bucket['tokens']) / bucket['refill_rate']
            }
    
    async def cleanup_old_buckets(self):
        """Cleanup old rate limit buckets"""
        while True:
            current_time = time.time()
            expired_keys = []
            
            for identifier, bucket in self.buckets.items():
                if current_time - bucket['last_refill'] > 3600:  # 1 hour
                    expired_keys.append(identifier)
            
            for key in expired_keys:
                del self.buckets[key]
            
            await asyncio.sleep(300)  # Cleanup every 5 minutes

# Global rate limiter
rate_limiter = RateLimiter()

# Request/Response models
class AuthenticationRequest(BaseModel):
    """API key authentication request"""
    api_key: str = Field(..., description="API key for authentication")

class AuthenticationResponse(BaseModel):
    """Authentication response"""
    user_id: str
    permissions: List[str]
    expires_at: str

class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str
    message: str
    timestamp: str
    request_id: str

class HealthCheckResponse(BaseModel):
    """Health check response"""
    service: str
    healthy: bool
    version: str
    timestamp: str
    components: Dict[str, Any]

# Authentication dependency
security = HTTPBearer(auto_error=False)

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Dict[str, Any]:
    """Get current authenticated user"""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Validate API key
    auth_info = await service_registry.access_control.validate_api_key(credentials.credentials)
    if not auth_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Add request context
    auth_info['ip_address'] = request.client.host
    auth_info['user_agent'] = request.headers.get('User-Agent')
    
    return auth_info

async def require_permission(permission: Permission):
    """Dependency factory for permission requirements"""
    async def check_permission(
        request: Request,
        user: Dict[str, Any] = Depends(get_current_user)
    ):
        user_id = user['user_id']
        has_permission, reason = await service_registry.access_control.check_permission(
            user_id, permission, context={
                'ip_address': user.get('ip_address'),
                'user_agent': user.get('user_agent')
            }
        )
        
        if not has_permission:
            raise HTTPException(status_code=403, detail=f"Permission denied: {reason}")
        
        return user
    
    return check_permission

async def rate_limit_check(request: Request, user: Dict[str, Any] = Depends(get_current_user)):
    """Rate limiting middleware"""
    user_id = user['user_id']
    
    # Get rate limit for user (could be tier-based)
    user_obj = await service_registry.database_manager.get_user(user_id)
    if user_obj and user_obj.tier.value == 'enterprise':
        max_requests = 1000
    elif user_obj and user_obj.tier.value == 'premium':
        max_requests = 500
    else:
        max_requests = 100
    
    allowed, info = rate_limiter.is_allowed(user_id, max_requests)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(info['reset_time']))
            }
        )
    
    # Add rate limit headers to response (would be done in middleware)
    return user

# Create FastAPI app with lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logging.info("Starting Cloud Infrastructure API Gateway")
    
    # Start rate limiter cleanup
    rate_limiter.cleanup_task = asyncio.create_task(rate_limiter.cleanup_old_buckets())
    
    yield
    
    # Shutdown
    logging.info("Shutting down Cloud Infrastructure API Gateway")
    if rate_limiter.cleanup_task:
        rate_limiter.cleanup_task.cancel()

app = FastAPI(
    title="Cloud Infrastructure API",
    description="Secure API gateway for cloud infrastructure management",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.detail,
            "timestamp": current_timestamp().isoformat(),
            "request_id": generate_id("req")
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logging.exception("Unhandled exception in API gateway")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An internal error occurred",
            "timestamp": current_timestamp().isoformat(),
            "request_id": generate_id("req")
        }
    )

# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """System health check"""
    try:
        components = {}
        overall_healthy = True
        
        # Check each service component
        if service_registry.ec2_provisioner:
            components['ec2_provisioner'] = await service_registry.ec2_provisioner.health_check()
            if not components['ec2_provisioner'].get('healthy', False):
                overall_healthy = False
        
        if service_registry.billing_engine:
            components['billing_engine'] = await service_registry.billing_engine.health_check()
            if not components['billing_engine'].get('healthy', False):
                overall_healthy = False
        
        if service_registry.auto_scaler:
            components['auto_scaler'] = await service_registry.auto_scaler.health_check()
            if not components['auto_scaler'].get('healthy', False):
                overall_healthy = False
        
        if service_registry.access_control:
            components['access_control'] = await service_registry.access_control.health_check()
            if not components['access_control'].get('healthy', False):
                overall_healthy = False
        
        return HealthCheckResponse(
            service="cloud_infrastructure_api",
            healthy=overall_healthy,
            version="1.0.0",
            timestamp=current_timestamp().isoformat(),
            components=components
        )
        
    except Exception as e:
        return HealthCheckResponse(
            service="cloud_infrastructure_api",
            healthy=False,
            version="1.0.0",
            timestamp=current_timestamp().isoformat(),
            components={"error": str(e)}
        )

# Authentication endpoints
@app.post("/auth/validate", response_model=AuthenticationResponse)
async def validate_api_key(request: AuthenticationRequest):
    """Validate API key and return user information"""
    auth_info = await service_registry.access_control.validate_api_key(request.api_key)
    
    if not auth_info:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return AuthenticationResponse(
        user_id=auth_info['user_id'],
        permissions=[perm.value for perm in auth_info['permissions']],
        expires_at=current_timestamp().isoformat()  # Would use actual expiry
    )

# Instance management endpoints
@app.post("/api/v1/instances", response_model=InstanceResponse)
async def create_instance(
    request: CreateInstanceRequest,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_permission(Permission.INSTANCE_CREATE))
):
    """Create a new EC2 instance"""
    # Override user_id from authentication
    request.user_id = user['user_id']
    
    # Additional permission checks for instance type
    has_permission, reason = await service_registry.access_control.check_permission(
        user['user_id'], Permission.INSTANCE_CREATE,
        context={'instance_type': request.instance_type.value}
    )
    
    if not has_permission:
        raise HTTPException(status_code=403, detail=reason)
    
    try:
        instance_response = await service_registry.ec2_provisioner.provision_instance(request)
        return instance_response
    except Exception as e:
        logging.error(f"Error creating instance: {e}")
        raise HTTPException(status_code=500, detail=f"Instance creation failed: {e}")

@app.get("/api/v1/instances", response_model=List[InstanceResponse])
async def list_instances(
    user: Dict[str, Any] = Depends(require_permission(Permission.INSTANCE_READ))
):
    """List user's instances"""
    try:
        instances = await service_registry.ec2_provisioner.get_user_instances(user['user_id'])
        return instances
    except Exception as e:
        logging.error(f"Error listing instances: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list instances: {e}")

@app.delete("/api/v1/instances/{instance_id}")
async def terminate_instance(
    instance_id: str,
    user: Dict[str, Any] = Depends(require_permission(Permission.INSTANCE_DELETE))
):
    """Terminate an instance"""
    try:
        # Verify user owns the instance
        has_access = await service_registry.tenant_manager.validate_user_access(
            user['user_id'], instance_id, 'instance'
        )
        
        if not has_access:
            raise HTTPException(status_code=403, detail="Access denied: Instance not owned by user")
        
        success = await service_registry.ec2_provisioner.terminate_instance(user['user_id'], instance_id)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to terminate instance")
        
        return {"message": "Instance termination initiated", "instance_id": instance_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error terminating instance: {e}")
        raise HTTPException(status_code=500, detail=f"Termination failed: {e}")

# Billing endpoints
@app.get("/api/v1/billing/usage", response_model=BillingUsageResponse)
async def get_billing_usage(
    request: BillingUsageRequest = Depends(),
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get billing usage for user"""
    # Override user_id from authentication
    request.user_id = user['user_id']
    
    try:
        usage_data = await service_registry.billing_engine.get_user_usage(
            request.user_id, request.start_date, request.end_date
        )
        
        return BillingUsageResponse(
            user_id=usage_data['user_id'],
            total_cost=usage_data['summary']['total_cost'],
            total_minutes=usage_data['summary']['total_minutes'],
            period_start=datetime.fromisoformat(usage_data['period']['start_date']),
            period_end=datetime.fromisoformat(usage_data['period']['end_date']),
            breakdown=usage_data['breakdown']
        )
        
    except Exception as e:
        logging.error(f"Error getting billing usage: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage data: {e}")

@app.get("/api/v1/billing/projection")
async def get_cost_projection(
    days: int = 30,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get cost projection for user"""
    try:
        projection = await service_registry.billing_engine.calculate_projected_cost(
            user['user_id'], days
        )
        return projection
    except Exception as e:
        logging.error(f"Error getting cost projection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get projection: {e}")

# Analytics endpoints
@app.get("/api/v1/analytics/cost-breakdown")
async def get_detailed_cost_breakdown(
    start_date: str,
    end_date: str,
    dimensions: Optional[str] = "instance_type,service",
    min_cost: float = 0.01,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get detailed cost breakdown across multiple dimensions"""
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        dimension_list = []
        if dimensions:
            for dim in dimensions.split(','):
                try:
                    dimension_list.append(CostDimension(dim.strip()))
                except ValueError:
                    pass  # Skip invalid dimensions
        
        breakdown = await service_registry.usage_analytics.get_detailed_cost_breakdown(
            user['user_id'], start_dt, end_dt, dimension_list, Decimal(str(min_cost))
        )
        
        # Convert Decimal values for JSON serialization
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj
        
        return convert_decimals(breakdown)
    except Exception as e:
        logging.error(f"Error getting cost breakdown: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cost breakdown: {e}")

@app.get("/api/v1/analytics/resource-utilization")
async def get_resource_utilization(
    start_date: str,
    end_date: str,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get resource utilization analysis"""
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        utilization_data = await service_registry.usage_analytics.analyze_resource_utilization(
            user['user_id'], start_dt, end_dt
        )
        
        # Convert to dict for JSON serialization
        return [asdict(util) for util in utilization_data]
    except Exception as e:
        logging.error(f"Error getting resource utilization: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get utilization data: {e}")

@app.get("/api/v1/analytics/usage-patterns")
async def get_usage_patterns(
    start_date: str,
    end_date: str,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get usage patterns and optimization opportunities"""
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        patterns = await service_registry.usage_analytics.detect_usage_patterns(
            user['user_id'], start_dt, end_dt
        )
        
        # Convert to dict for JSON serialization
        def convert_pattern(pattern):
            pattern_dict = asdict(pattern)
            # Convert Decimal cost_impact to float
            if isinstance(pattern_dict['cost_impact'], Decimal):
                pattern_dict['cost_impact'] = float(pattern_dict['cost_impact'])
            return pattern_dict
        
        return [convert_pattern(pattern) for pattern in patterns]
    except Exception as e:
        logging.error(f"Error getting usage patterns: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get usage patterns: {e}")

@app.get("/api/v1/analytics/comparative-analysis")
async def get_comparative_analysis(
    current_start: str,
    current_end: str,
    comparison_period: str = "previous_period",
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get comparative cost analysis between periods"""
    try:
        start_dt = datetime.fromisoformat(current_start.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(current_end.replace('Z', '+00:00'))
        
        analysis = await service_registry.usage_analytics.generate_comparative_analysis(
            user['user_id'], start_dt, end_dt, comparison_period
        )
        
        # Convert to dict and handle Decimal conversion
        analysis_dict = asdict(analysis)
        
        def convert_decimals(obj):
            if isinstance(obj, dict):
                return {k: convert_decimals(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_decimals(v) for v in obj]
            elif isinstance(obj, Decimal):
                return float(obj)
            else:
                return obj
        
        return convert_decimals(analysis_dict)
    except Exception as e:
        logging.error(f"Error getting comparative analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get comparative analysis: {e}")

@app.get("/api/v1/analytics/tag-allocation")
async def get_tag_based_allocation(
    start_date: str,
    end_date: str,
    tag_key: str,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get cost allocation based on resource tags"""
    try:
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        allocations = await service_registry.usage_analytics.get_tag_based_cost_allocation(
            user['user_id'], start_dt, end_dt, tag_key
        )
        
        # Convert CostAttribution objects to dict and handle Decimal conversion
        result = {}
        for tag_value, attribution in allocations.items():
            attr_dict = asdict(attribution)
            # Convert Decimal values
            attr_dict['total_cost'] = float(attr_dict['total_cost'])
            attr_dict['average_cost_per_resource'] = float(attr_dict['average_cost_per_resource'])
            result[tag_value] = attr_dict
        
        return result
    except Exception as e:
        logging.error(f"Error getting tag allocation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tag allocation: {e}")

@app.post("/api/v1/reports/generate")
async def generate_report(
    report_type: str,
    format: str,
    start_date: str,
    end_date: str,
    filters: Optional[Dict[str, Any]] = None,
    include_charts: bool = True,
    include_recommendations: bool = True,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Generate a comprehensive usage and cost report"""
    try:
        # Validate parameters
        try:
            report_type_enum = ReportType(report_type)
            format_enum = ReportFormat(format)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid parameter: {e}")
        
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        
        # Create report request
        report_request = ReportRequest(
            report_type=report_type_enum,
            format=format_enum,
            start_date=start_dt,
            end_date=end_dt,
            filters=filters,
            include_charts=include_charts,
            include_recommendations=include_recommendations
        )
        
        # Generate the report
        report_result = await service_registry.report_generator.generate_report(
            user['user_id'], report_request
        )
        
        return report_result
        
    except Exception as e:
        logging.error(f"Error generating report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {e}")

@app.get("/api/v1/reports/types")
async def get_available_report_types(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get list of available report types and formats"""
    return {
        'report_types': [
            {
                'value': report_type.value,
                'name': report_type.value.replace('_', ' ').title(),
                'description': _get_report_description(report_type)
            }
            for report_type in ReportType
        ],
        'formats': [
            {
                'value': format_type.value,
                'name': format_type.value.upper(),
                'description': _get_format_description(format_type)
            }
            for format_type in ReportFormat
        ]
    }

def _get_report_description(report_type: ReportType) -> str:
    """Get description for report type"""
    descriptions = {
        ReportType.COST_SUMMARY: "High-level cost overview with breakdowns by service and instance type",
        ReportType.DETAILED_BILLING: "Detailed line-item billing with per-resource costs",
        ReportType.RESOURCE_UTILIZATION: "Resource efficiency and utilization analysis",
        ReportType.COMPARATIVE_ANALYSIS: "Period-over-period cost and usage comparison",
        ReportType.OPTIMIZATION_REPORT: "Cost optimization recommendations and savings opportunities",
        ReportType.EXECUTIVE_SUMMARY: "Executive-level overview with key metrics and insights",
        ReportType.TREND_ANALYSIS: "Cost trends and forecasting analysis",
        ReportType.DEPARTMENT_BREAKDOWN: "Cost allocation by department or team"
    }
    return descriptions.get(report_type, "Custom report")

def _get_format_description(format_type: ReportFormat) -> str:
    """Get description for format type"""
    descriptions = {
        ReportFormat.JSON: "Machine-readable JSON format",
        ReportFormat.CSV: "Comma-separated values for spreadsheet import",
        ReportFormat.HTML: "Web-friendly HTML format with styling",
        ReportFormat.PDF: "Portable document format (coming soon)",
        ReportFormat.EXCEL: "Microsoft Excel format (coming soon)"
    }
    return descriptions.get(format_type, "Standard format")

# User-Friendly Finance Endpoints
@app.get("/api/v1/finance/overview")
async def get_financial_overview(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get user-friendly financial overview with clear metrics and insights"""
    try:
        overview = await service_registry.user_friendly_dashboard.get_financial_overview(
            user['user_id']
        )
        return overview
    except Exception as e:
        logging.error(f"Error getting financial overview: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load financial overview: {e}")

@app.get("/api/v1/finance/budget")
async def get_budget_management(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get user-friendly budget management interface"""
    try:
        budget_info = await service_registry.user_friendly_dashboard.get_budget_management(
            user['user_id']
        )
        return budget_info
    except Exception as e:
        logging.error(f"Error getting budget management: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load budget information: {e}")

@app.get("/api/v1/finance/optimization")
async def get_cost_optimization_guide(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get personalized cost optimization guide with actionable recommendations"""
    try:
        optimization_guide = await service_registry.user_friendly_dashboard.get_cost_optimization_guide(
            user['user_id']
        )
        return optimization_guide
    except Exception as e:
        logging.error(f"Error getting optimization guide: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load optimization guide: {e}")

@app.get("/api/v1/finance/invoice")
async def get_simple_invoice_view(
    month: Optional[str] = None,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get simple, easy-to-understand invoice view"""
    try:
        invoice = await service_registry.user_friendly_dashboard.get_simple_invoice_view(
            user['user_id'], month
        )
        return invoice
    except Exception as e:
        logging.error(f"Error getting invoice view: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load invoice: {e}")

@app.get("/api/v1/finance/spending-summary")
async def get_spending_summary(
    period: str = "month",  # month, week, day
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get a simple spending summary for the specified period"""
    try:
        from datetime import datetime, timedelta
        
        now = datetime.now()
        
        if period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = "This Month"
        elif period == "week":
            start_date = now - timedelta(days=now.weekday())
            end_date = now
            period_name = "This Week"
        elif period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = now
            period_name = "Today"
        else:
            raise HTTPException(status_code=400, detail="Invalid period. Use: month, week, or day")
        
        # Get billing records
        import aiosqlite
        async with aiosqlite.connect(service_registry.database_manager.db_path) as conn:
            query = """
                SELECT total_cost, instance_type, start_time FROM billing_records 
                WHERE user_id = ? AND start_time >= ? AND start_time <= ?
                ORDER BY start_time DESC
            """
            cursor = await conn.execute(query, (user['user_id'], start_date, end_date))
            records = await cursor.fetchall()
        
        if not records:
            return {
                'period': period_name,
                'total_cost': "$0.00",
                'resource_count': 0,
                'message': f"No spending recorded for {period_name.lower()}"
            }
        
        total_cost = sum(Decimal(str(record[0])) for record in records)
        resource_count = len(set(record[1] for record in records))
        
        # Calculate average
        if period == "month":
            days = (end_date - start_date).days + 1
            avg_label = "daily average"
            avg_amount = total_cost / days if days > 0 else Decimal('0')
        elif period == "week":
            avg_label = "daily average"
            avg_amount = total_cost / 7
        else:
            avg_label = "hourly average" 
            avg_amount = total_cost / 24
        
        return {
            'period': period_name,
            'total_cost': f"${total_cost:.2f}",
            'resource_count': resource_count,
            'average': {
                'label': avg_label,
                'amount': f"${avg_amount:.2f}"
            },
            'top_services': await _get_top_services(records),
            'trend': await _calculate_simple_trend(user['user_id'], period, start_date, end_date)
        }
        
    except Exception as e:
        logging.error(f"Error getting spending summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get spending summary: {e}")

@app.get("/api/v1/finance/alerts")
async def get_financial_alerts(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get current financial alerts and notifications"""
    try:
        # Get current spending
        now = datetime.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        import aiosqlite
        async with aiosqlite.connect(service_registry.database_manager.db_path) as conn:
            query = """
                SELECT SUM(total_cost) FROM billing_records 
                WHERE user_id = ? AND start_time >= ?
            """
            cursor = await conn.execute(query, (user['user_id'], month_start))
            result = await cursor.fetchone()
            current_spend = Decimal(str(result[0])) if result[0] else Decimal('0')
        
        # Get user budget
        user_info = await service_registry.database_manager.get_user(user['user_id'])
        monthly_budget = getattr(user_info, 'monthly_budget', None) or Decimal('1000')
        
        alerts = []
        budget_percent = float(current_spend / monthly_budget * 100)
        
        if budget_percent >= 100:
            alerts.append({
                'severity': 'critical',
                'title': 'Budget Exceeded',
                'message': f"You've spent ${current_spend:.2f}, exceeding your ${monthly_budget:.2f} monthly budget",
                'action': 'Review and optimize resources immediately',
                'icon': '🚨'
            })
        elif budget_percent >= 80:
            alerts.append({
                'severity': 'warning',
                'title': 'Budget Alert',
                'message': f"You've used {budget_percent:.0f}% of your monthly budget",
                'action': 'Monitor spending closely',
                'icon': '⚠️'
            })
        
        # Check for unusual spending
        if current_spend > monthly_budget * Decimal('0.5'):
            days_elapsed = now.day
            if days_elapsed < 15:  # High spend in first half of month
                alerts.append({
                    'severity': 'info',
                    'title': 'High Early Spending',
                    'message': f"You've spent ${current_spend:.2f} in {days_elapsed} days",
                    'action': 'Review recent resource usage',
                    'icon': '📊'
                })
        
        return {
            'alerts': alerts,
            'budget_status': {
                'current_spend': f"${current_spend:.2f}",
                'budget_limit': f"${monthly_budget:.2f}",
                'percentage_used': f"{budget_percent:.1f}%",
                'remaining': f"${max(0, monthly_budget - current_spend):.2f}"
            },
            'recommendations': [
                "Set up automatic alerts for budget thresholds",
                "Review your highest-cost resources weekly",
                "Consider reserved instances for consistent workloads"
            ]
        }
        
    except Exception as e:
        logging.error(f"Error getting financial alerts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alerts: {e}")

# Helper functions for finance endpoints
async def _get_top_services(records) -> List[Dict[str, str]]:
    """Get top services by cost"""
    service_costs = {}
    for record in records:
        service = record[1] or 'compute'  # instance_type as proxy for service
        cost = Decimal(str(record[0]))
        if service not in service_costs:
            service_costs[service] = Decimal('0')
        service_costs[service] += cost
    
    sorted_services = sorted(service_costs.items(), key=lambda x: x[1], reverse=True)[:3]
    return [
        {
            'service': service,
            'cost': f"${cost:.2f}"
        }
        for service, cost in sorted_services
    ]

async def _calculate_simple_trend(user_id: str, period: str, start_date: datetime, end_date: datetime) -> Dict[str, str]:
    """Calculate simple trend comparison"""
    # Get previous period for comparison
    period_length = end_date - start_date
    prev_start = start_date - period_length
    prev_end = start_date
    
    import aiosqlite
    async with aiosqlite.connect(service_registry.database_manager.db_path) as conn:
        query = """
            SELECT SUM(total_cost) FROM billing_records 
            WHERE user_id = ? AND start_time >= ? AND start_time < ?
        """
        cursor = await conn.execute(query, (user_id, prev_start, prev_end))
        result = await cursor.fetchone()
        prev_cost = Decimal(str(result[0])) if result[0] else Decimal('0')
    
    # Calculate current period cost
    cursor = await conn.execute(query, (user_id, start_date, end_date))
    result = await cursor.fetchone()
    current_cost = Decimal(str(result[0])) if result[0] else Decimal('0')
    
    if prev_cost == 0:
        return {
            'direction': 'stable',
            'message': 'No previous data for comparison'
        }
    
    change_percent = float((current_cost - prev_cost) / prev_cost * 100)
    
    if abs(change_percent) < 5:
        return {
            'direction': 'stable',
            'message': f'Similar to last {period} ({change_percent:+.1f}%)'
        }
    elif change_percent > 0:
        return {
            'direction': 'increasing',
            'message': f'{change_percent:.1f}% higher than last {period}'
        }
    else:
        return {
            'direction': 'decreasing', 
            'message': f'{abs(change_percent):.1f}% lower than last {period}'
        }

# Cost Calculator Endpoints
@app.get("/api/v1/calculator/estimate")
async def calculate_instance_cost(
    instance_type: str,
    usage_pattern: str = "always_on",
    custom_hours_per_week: Optional[int] = None,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Calculate cost estimate for an instance with different usage patterns"""
    try:
        # Validate usage pattern
        try:
            pattern = UsagePattern(usage_pattern)
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid usage pattern. Use: {', '.join([p.value for p in UsagePattern])}"
            )
        
        estimate = service_registry.cost_calculator.calculate_instance_cost(
            instance_type, pattern, custom_hours_per_week
        )
        
        return {
            'estimate': asdict(estimate),
            'cost_breakdown': {
                'per_hour': f"${estimate.hourly_cost:.3f}",
                'per_day': f"${estimate.daily_cost:.2f}",
                'per_week': f"${estimate.weekly_cost:.2f}",
                'per_month': f"${estimate.monthly_cost:.2f}",
                'per_year': f"${estimate.annual_cost:.2f}"
            },
            'usage_details': {
                'pattern': estimate.usage_pattern,
                'hours_per_month': estimate.hours_per_month,
                'instance_type': estimate.instance_type
            },
            'recommendations': estimate.recommendations
        }
        
    except Exception as e:
        logging.error(f"Error calculating cost estimate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate estimate: {e}")

@app.get("/api/v1/calculator/compare")
async def compare_instance_costs(
    instance_types: str,  # Comma-separated list
    usage_pattern: str = "always_on",
    custom_hours_per_week: Optional[int] = None,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Compare costs across different instance types"""
    try:
        # Parse instance types
        types_list = [t.strip() for t in instance_types.split(',')]
        if len(types_list) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 instance types allowed")
        
        # Validate usage pattern
        try:
            pattern = UsagePattern(usage_pattern)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid usage pattern. Use: {', '.join([p.value for p in UsagePattern])}"
            )
        
        comparison = service_registry.cost_calculator.compare_instance_types(
            types_list, pattern, custom_hours_per_week
        )
        
        return comparison
        
    except Exception as e:
        logging.error(f"Error comparing instance costs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to compare costs: {e}")

@app.get("/api/v1/calculator/usage-patterns")
async def show_usage_pattern_savings(
    instance_type: str,
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Show potential savings from different usage patterns"""
    try:
        savings_analysis = service_registry.cost_calculator.calculate_usage_pattern_savings(
            instance_type
        )
        return savings_analysis
        
    except Exception as e:
        logging.error(f"Error calculating usage pattern savings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate savings: {e}")

@app.post("/api/v1/calculator/project")
async def estimate_project_cost(
    project_config: Dict[str, Any],
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Estimate total project cost from configuration"""
    try:
        project_estimate = service_registry.cost_calculator.estimate_project_cost(project_config)
        return project_estimate
        
    except Exception as e:
        logging.error(f"Error estimating project cost: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to estimate project cost: {e}")

@app.get("/api/v1/calculator/pricing")
async def get_pricing_summary(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get simple pricing summary for popular instance types"""
    try:
        pricing_info = service_registry.cost_calculator.get_pricing_summary()
        return pricing_info
        
    except Exception as e:
        logging.error(f"Error getting pricing summary: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pricing: {e}")

@app.get("/api/v1/calculator/savings-recommendations")
async def get_personalized_savings(
    user: Dict[str, Any] = Depends(require_permission(Permission.BILLING_READ))
):
    """Get personalized savings recommendations based on current usage"""
    try:
        # Get user's current spending and usage patterns
        current_spend = await _get_current_monthly_spending(user['user_id'])
        instance_types = await _get_user_instance_types(user['user_id'])
        
        recommendations = service_registry.cost_calculator.get_savings_recommendations(
            current_spend, instance_types, {}
        )
        
        return {
            'current_monthly_spend': f"${current_spend:.2f}",
            'recommendations': [asdict(rec) for rec in recommendations],
            'total_potential_savings': f"${sum(rec.monthly_savings for rec in recommendations):.2f}/month",
            'implementation_priority': [
                rec for rec in recommendations 
                if rec.difficulty == "Easy"
            ][:3]
        }
        
    except Exception as e:
        logging.error(f"Error getting savings recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recommendations: {e}")

# Helper functions for cost calculator
async def _get_current_monthly_spending(user_id: str) -> Decimal:
    """Get current month spending for user"""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    import aiosqlite
    async with aiosqlite.connect(service_registry.database_manager.db_path) as conn:
        query = """
            SELECT SUM(total_cost) FROM billing_records 
            WHERE user_id = ? AND start_time >= ?
        """
        cursor = await conn.execute(query, (user_id, month_start))
        result = await cursor.fetchone()
        return Decimal(str(result[0])) if result[0] else Decimal('0')

async def _get_user_instance_types(user_id: str) -> List[str]:
    """Get instance types currently used by user"""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    import aiosqlite
    async with aiosqlite.connect(service_registry.database_manager.db_path) as conn:
        query = """
            SELECT DISTINCT instance_type FROM billing_records 
            WHERE user_id = ? AND start_time >= ?
        """
        cursor = await conn.execute(query, (user_id, month_start))
        results = await cursor.fetchall()
        return [row[0] for row in results if row[0]]

# Scaling endpoints
@app.get("/api/v1/scaling/status")
async def get_scaling_status(
    user: Dict[str, Any] = Depends(require_permission(Permission.SCALING_READ))
):
    """Get auto-scaling status for user"""
    try:
        status = await service_registry.auto_scaler.get_scaling_status(user['user_id'])
        return status
    except Exception as e:
        logging.error(f"Error getting scaling status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scaling status: {e}")

@app.post("/api/v1/scaling/config")
async def update_scaling_config(
    config: ScalingConfigRequest,
    user: Dict[str, Any] = Depends(require_permission(Permission.SCALING_CONFIG))
):
    """Update auto-scaling configuration"""
    # Override user_id from authentication
    config.user_id = user['user_id']
    
    try:
        # Save scaling configuration
        await service_registry.database_manager.save_user_scaling_config(config.dict())
        
        # Clear any cached scaling configuration
        return {"message": "Scaling configuration updated", "user_id": user['user_id']}
        
    except Exception as e:
        logging.error(f"Error updating scaling config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {e}")

@app.post("/api/v1/scaling/game-night")
async def schedule_game_night(
    event: GameNightEventRequest,
    user: Dict[str, Any] = Depends(require_permission(Permission.SCALING_CONFIG))
):
    """Schedule a game night scaling event"""
    # Override user_id from authentication
    event.user_id = user['user_id']
    
    try:
        from core.models import GameNightEvent
        
        game_night = GameNightEvent(
            event_id=generate_id("game"),
            user_id=event.user_id,
            name=event.name,
            start_time=event.start_time,
            duration_hours=event.duration_hours,
            expected_players=event.expected_players,
            scale_multiplier=event.scale_multiplier,
            pre_scale_instances=0  # Will be calculated by auto_scaler
        )
        
        success = await service_registry.auto_scaler.schedule_game_night(game_night)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to schedule game night")
        
        return {
            "message": "Game night event scheduled",
            "event_id": game_night.event_id,
            "start_time": game_night.start_time.isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error scheduling game night: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule event: {e}")

# System metrics endpoint
@app.get("/api/v1/metrics", response_model=SystemMetrics)
async def get_system_metrics(
    user: Dict[str, Any] = Depends(require_permission(Permission.ADMIN_METRICS_READ))
):
    """Get system-wide metrics (admin only)"""
    try:
        # Aggregate metrics from all services
        provisioner_metrics = await service_registry.ec2_provisioner.health_check()
        billing_metrics = await service_registry.billing_engine.get_billing_metrics()
        scaling_metrics = await service_registry.auto_scaler.health_check()
        
        # Get instance counts
        total_instances = provisioner_metrics.get('total_instances', 0)
        running_instances = provisioner_metrics.get('running_instances', 0)
        
        # Get user count
        total_users = await service_registry.database_manager.count_total_users()
        
        return SystemMetrics(
            timestamp=current_timestamp(),
            total_instances=total_instances,
            running_instances=running_instances,
            total_users=total_users,
            total_cost_current_month=billing_metrics.get('current_month_revenue', 0.0),
            average_cpu_utilization=0.0,  # Would calculate from usage tracker
            scaling_events_last_hour=0  # Would get from scaling metrics
        )
        
    except Exception as e:
        logging.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")

# ======================= Enterprise Organization Endpoints =======================

@app.post("/api/v1/enterprise/organizations")
async def create_organization(
    name: str = Field(..., description="Organization name"),
    tier: str = Field("business", description="Organization tier"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create a new organization"""
    try:
        check_permissions(current_user, [Permission.ADMIN])
        
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        from core.models import OrganizationTier
        organization = await org_manager.create_organization(
            name=name,
            owner_user_id=current_user.user_id,
            tier=OrganizationTier(tier)
        )
        
        if organization:
            return {
                "organization": organization.to_dict(),
                "message": "Organization created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create organization")
            
    except Exception as e:
        logging.error(f"Create organization error: {e}")
        raise HTTPException(status_code=500, detail=f"Create organization failed: {e}")

@app.get("/api/v1/enterprise/organizations")
async def list_user_organizations(
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Get organizations where user is a member"""
    try:
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        organizations = await org_manager.get_user_organizations(current_user.user_id)
        
        return {
            "organizations": [org.to_dict() for org in organizations],
            "count": len(organizations)
        }
        
    except Exception as e:
        logging.error(f"List organizations error: {e}")
        raise HTTPException(status_code=500, detail=f"List organizations failed: {e}")

@app.post("/api/v1/enterprise/organizations/{org_id}/departments")
async def create_department(
    org_id: str,
    name: str = Field(..., description="Department name"),
    manager_user_id: str = Field(..., description="Department manager user ID"),
    budget_limit: Optional[float] = Field(None, description="Department budget limit"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create a department in an organization"""
    try:
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        department = await org_manager.create_department(
            org_id=org_id,
            name=name,
            manager_user_id=manager_user_id,
            budget_limit=budget_limit
        )
        
        if department:
            return {
                "department": department.to_dict(),
                "message": "Department created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create department")
            
    except Exception as e:
        logging.error(f"Create department error: {e}")
        raise HTTPException(status_code=500, detail=f"Create department failed: {e}")

@app.post("/api/v1/enterprise/approval-requests")
async def create_approval_request(
    org_id: str = Field(..., description="Organization ID"),
    resource_type: str = Field(..., description="Type of resource being requested"),
    resource_config: dict = Field(..., description="Resource configuration"),
    justification: str = Field(..., description="Justification for the request"),
    estimated_cost: Optional[float] = Field(None, description="Estimated cost"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create an approval request for resource provisioning"""
    try:
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        approval_request = await org_manager.create_approval_request(
            org_id=org_id,
            requester_user_id=current_user.user_id,
            resource_type=resource_type,
            resource_config=resource_config,
            justification=justification,
            estimated_cost=estimated_cost
        )
        
        if approval_request:
            return {
                "approval_request": approval_request.to_dict(),
                "message": "Approval request created successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create approval request")
            
    except Exception as e:
        logging.error(f"Create approval request error: {e}")
        raise HTTPException(status_code=500, detail=f"Create approval request failed: {e}")

@app.get("/api/v1/enterprise/organizations/{org_id}/approval-requests")
async def list_approval_requests(
    org_id: str,
    status: Optional[str] = Field(None, description="Filter by status (pending, approved, rejected)"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """List approval requests for an organization"""
    try:
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        if status == 'pending':
            requests = await org_manager.get_pending_approval_requests(org_id)
        else:
            # Get all requests (simplified)
            requests = await org_manager.get_pending_approval_requests(org_id)
        
        return {
            "approval_requests": [req.to_dict() for req in requests],
            "count": len(requests)
        }
        
    except Exception as e:
        logging.error(f"List approval requests error: {e}")
        raise HTTPException(status_code=500, detail=f"List approval requests failed: {e}")

@app.post("/api/v1/enterprise/approval-requests/{request_id}/approve")
async def approve_request(
    request_id: str,
    comments: Optional[str] = Field(None, description="Approval comments"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Approve a resource request"""
    try:
        org_manager = service_registry.organization_manager
        if not org_manager:
            raise HTTPException(status_code=503, detail="Organization manager not available")
        
        result = await org_manager.approve_request(
            request_id=request_id,
            approver_user_id=current_user.user_id,
            comments=comments
        )
        
        if result:
            return {"message": "Request approved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to approve request")
            
    except Exception as e:
        logging.error(f"Approve request error: {e}")
        raise HTTPException(status_code=500, detail=f"Approve request failed: {e}")

# ======================= Enterprise Scaling Endpoints =======================

@app.post("/api/v1/enterprise/scaling/policies")
async def create_scaling_policy(
    org_id: str = Field(..., description="Organization ID"),
    name: str = Field(..., description="Policy name"),
    trigger_type: str = Field(..., description="Scaling trigger type"),
    threshold_value: float = Field(..., description="Trigger threshold"),
    scaling_action: str = Field(..., description="Scaling action"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create enterprise scaling policy"""
    try:
        # Initialize scaling manager
        from enterprise.scaling_features import EnterpriseScalingManager, ScalingTrigger, ScalingAction
        scaling_manager = EnterpriseScalingManager(
            service_registry.database_manager, 
            service_registry.organization_manager
        )
        
        policy = await scaling_manager.create_scaling_policy(
            org_id=org_id,
            name=name,
            trigger_type=ScalingTrigger(trigger_type),
            threshold_value=threshold_value,
            scaling_action=ScalingAction(scaling_action)
        )
        
        return {
            "policy": {
                "policy_id": policy.policy_id,
                "name": policy.name,
                "trigger_type": policy.trigger_type.value,
                "threshold_value": policy.threshold_value,
                "scaling_action": policy.scaling_action.value,
                "active": policy.active
            },
            "message": "Scaling policy created successfully"
        }
        
    except Exception as e:
        logging.error(f"Create scaling policy error: {e}")
        raise HTTPException(status_code=500, detail=f"Create scaling policy failed: {e}")

@app.get("/api/v1/enterprise/scaling/recommendations/{org_id}")
async def get_scaling_recommendations(
    org_id: str,
    resource_type: str = Field("instances", description="Resource type"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Get AI-driven scaling recommendations"""
    try:
        from enterprise.scaling_features import EnterpriseScalingManager
        scaling_manager = EnterpriseScalingManager(
            service_registry.database_manager,
            service_registry.organization_manager
        )
        
        recommendations = await scaling_manager.get_scaling_recommendations(
            org_id=org_id,
            resource_type=resource_type
        )
        
        return recommendations
        
    except Exception as e:
        logging.error(f"Get scaling recommendations error: {e}")
        raise HTTPException(status_code=500, detail=f"Get scaling recommendations failed: {e}")

@app.post("/api/v1/enterprise/scaling/resource-pools")
async def create_resource_pool(
    org_id: str = Field(..., description="Organization ID"),
    name: str = Field(..., description="Pool name"),
    resource_type: str = Field(..., description="Resource type"),
    min_capacity: int = Field(..., description="Minimum capacity"),
    max_capacity: int = Field(..., description="Maximum capacity"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Create enterprise resource pool"""
    try:
        from enterprise.scaling_features import EnterpriseScalingManager
        scaling_manager = EnterpriseScalingManager(
            service_registry.database_manager,
            service_registry.organization_manager
        )
        
        pool = await scaling_manager.create_resource_pool(
            org_id=org_id,
            name=name,
            resource_type=resource_type,
            min_capacity=min_capacity,
            max_capacity=max_capacity
        )
        
        return {
            "pool": {
                "pool_id": pool.pool_id,
                "name": pool.name,
                "resource_type": pool.resource_type,
                "min_capacity": pool.min_capacity,
                "max_capacity": pool.max_capacity,
                "target_capacity": pool.target_capacity,
                "active": pool.active
            },
            "message": "Resource pool created successfully"
        }
        
    except Exception as e:
        logging.error(f"Create resource pool error: {e}")
        raise HTTPException(status_code=500, detail=f"Create resource pool failed: {e}")

@app.get("/api/v1/enterprise/scaling/dashboard/{org_id}")
async def get_scaling_dashboard(
    org_id: str,
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Get enterprise scaling dashboard"""
    try:
        from enterprise.scaling_features import EnterpriseScalingManager
        scaling_manager = EnterpriseScalingManager(
            service_registry.database_manager,
            service_registry.organization_manager
        )
        
        dashboard = await scaling_manager.get_enterprise_scaling_dashboard(org_id)
        
        return dashboard
        
    except Exception as e:
        logging.error(f"Get scaling dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Get scaling dashboard failed: {e}")

@app.post("/api/v1/enterprise/scaling/capacity-planning")
async def generate_capacity_plan(
    org_id: str = Field(..., description="Organization ID"),
    dept_id: Optional[str] = Field(None, description="Department ID"),
    project_id: Optional[str] = Field(None, description="Project ID"),
    planning_days: int = Field(90, description="Planning horizon in days"),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Generate predictive capacity plan"""
    try:
        from enterprise.scaling_features import EnterpriseScalingManager
        scaling_manager = EnterpriseScalingManager(
            service_registry.database_manager,
            service_registry.organization_manager
        )
        
        plan = await scaling_manager.generate_capacity_plan(
            org_id=org_id,
            dept_id=dept_id,
            project_id=project_id,
            planning_days=planning_days
        )
        
        return {
            "capacity_plan": {
                "plan_id": plan.plan_id,
                "planning_period": {
                    "start_date": plan.start_date.isoformat(),
                    "end_date": plan.end_date.isoformat()
                },
                "projections": {
                    "current_capacity": plan.current_capacity,
                    "projected_capacity": plan.projected_capacity,
                    "peak_capacity_needed": plan.peak_capacity_needed
                },
                "costs": {
                    "current_monthly_cost": str(plan.current_monthly_cost),
                    "projected_monthly_cost": str(plan.projected_monthly_cost)
                },
                "recommendations": plan.recommendations,
                "risk_factors": plan.risk_factors,
                "cost_optimization_opportunities": plan.cost_optimization_opportunities
            },
            "message": "Capacity plan generated successfully"
        }
        
    except Exception as e:
        logging.error(f"Generate capacity plan error: {e}")
        raise HTTPException(status_code=500, detail=f"Generate capacity plan failed: {e}")

# Payment and Invoice Management Endpoints
@app.post("/api/v1/payments/methods")
async def add_payment_method(
    method_type: str,
    metadata: Dict[str, Any],
    current_user: AuthInfo = Depends(require_auth)
):
    """Add a payment method for the current user"""
    try:
        method_enum = PaymentMethodType(method_type)
        
        method_id = await service_registry.payment_processor.add_payment_method(
            current_user.user_id, method_enum, metadata
        )
        
        return {
            "method_id": method_id,
            "message": f"Payment method {method_type} added successfully"
        }
    except Exception as e:
        logging.error(f"Error adding payment method: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/payments/methods")
async def get_payment_methods(current_user: AuthInfo = Depends(require_auth)):
    """Get all payment methods for the current user"""
    try:
        methods = await service_registry.payment_processor.get_user_payment_methods(
            current_user.user_id
        )
        return {"payment_methods": methods}
    except Exception as e:
        logging.error(f"Error getting payment methods: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/invoices/generate")
async def generate_invoice(
    billing_period_start: Optional[str] = None,
    billing_period_end: Optional[str] = None,
    current_user: AuthInfo = Depends(require_auth)
):
    """Generate an invoice based on usage"""
    try:
        from datetime import datetime, timezone
        
        start_date = None
        end_date = None
        
        if billing_period_start:
            start_date = datetime.fromisoformat(billing_period_start.replace('Z', '+00:00'))
        if billing_period_end:
            end_date = datetime.fromisoformat(billing_period_end.replace('Z', '+00:00'))
        
        invoice_id = await service_registry.payment_processor.generate_usage_invoice(
            current_user.user_id, 
            org_id=current_user.org_id,
            billing_period_start=start_date,
            billing_period_end=end_date
        )
        
        return {
            "invoice_id": invoice_id,
            "message": "Invoice generated successfully",
            "billing_period_start": start_date.isoformat() if start_date else None,
            "billing_period_end": end_date.isoformat() if end_date else None
        }
    except Exception as e:
        logging.error(f"Error generating invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/invoices")
async def get_invoices(
    limit: int = 50,
    current_user: AuthInfo = Depends(require_auth)
):
    """Get invoices for the current user"""
    try:
        invoices = await service_registry.payment_processor.get_user_invoices(
            current_user.user_id, limit
        )
        return {"invoices": invoices}
    except Exception as e:
        logging.error(f"Error getting invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/invoices/{invoice_id}/send")
async def send_invoice(
    invoice_id: str,
    current_user: AuthInfo = Depends(require_auth)
):
    """Send an invoice to the customer"""
    try:
        success = await service_registry.payment_processor.send_invoice(invoice_id)
        if success:
            return {"message": f"Invoice {invoice_id} sent successfully"}
        else:
            raise HTTPException(status_code=404, detail="Invoice not found or cannot be sent")
    except Exception as e:
        logging.error(f"Error sending invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/payments/process")
async def process_payment(
    invoice_id: str,
    payment_method_id: str,
    current_user: AuthInfo = Depends(require_auth)
):
    """Process a payment for an invoice"""
    try:
        payment_id = await service_registry.payment_processor.process_payment(
            invoice_id, payment_method_id
        )
        
        return {
            "payment_id": payment_id,
            "message": "Payment processed successfully",
            "invoice_id": invoice_id
        }
    except Exception as e:
        logging.error(f"Error processing payment: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/payments/history")
async def get_payment_history(
    limit: int = 50,
    current_user: AuthInfo = Depends(require_auth)
):
    """Get payment history for the current user"""
    try:
        payments = await service_registry.payment_processor.get_payment_history(
            current_user.user_id, limit
        )
        return {"payments": payments}
    except Exception as e:
        logging.error(f"Error getting payment history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Usage Forecasting and Budget Planning Endpoints
@app.post("/api/v1/forecasting/generate")
async def generate_forecast(
    forecast_days: int = 30,
    model: str = "linear",
    current_user: AuthInfo = Depends(require_auth)
):
    """Generate usage forecast for a user"""
    try:
        from billing.forecasting import ForecastModel
        forecast_model = ForecastModel(model)
        
        forecast = await service_registry.usage_forecaster.generate_usage_forecast(
            current_user.user_id, forecast_days, forecast_model, current_user.org_id
        )
        
        return {
            "forecast_id": forecast.forecast_id,
            "forecast_period_days": forecast.forecast_period_days,
            "model_used": forecast.model_used.value,
            "predicted_cost": float(forecast.predicted_cost),
            "confidence_level": forecast.confidence_level,
            "predicted_usage": {k: float(v) for k, v in forecast.predicted_usage.items()},
            "factors_considered": forecast.factors_considered,
            "recommendations": forecast.recommendations
        }
    except Exception as e:
        logging.error(f"Error generating forecast: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/budgets/create")
async def create_budget(
    name: str,
    total_budget: float,
    period_months: int = 12,
    service_allocations: Optional[Dict[str, float]] = None,
    current_user: AuthInfo = Depends(require_auth)
):
    """Create a new budget plan"""
    try:
        from decimal import Decimal
        
        # Convert service allocations to Decimal
        allocations = None
        if service_allocations:
            allocations = {k: Decimal(str(v)) for k, v in service_allocations.items()}
        
        budget_plan = await service_registry.usage_forecaster.create_budget_plan(
            current_user.user_id, name, Decimal(str(total_budget)),
            period_months, current_user.org_id, allocations
        )
        
        return {
            "budget_id": budget_plan.budget_id,
            "name": budget_plan.name,
            "total_budget": float(budget_plan.total_budget),
            "monthly_budget": float(budget_plan.monthly_budget),
            "period_start": budget_plan.period_start.isoformat(),
            "period_end": budget_plan.period_end.isoformat(),
            "service_allocations": {k: float(v) for k, v in budget_plan.service_allocations.items()},
            "alert_thresholds": budget_plan.alert_thresholds
        }
    except Exception as e:
        logging.error(f"Error creating budget: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/budgets")
async def get_budgets(current_user: AuthInfo = Depends(require_auth)):
    """Get budget plans for the current user"""
    try:
        budgets = await service_registry.usage_forecaster.get_user_budget_plans(
            current_user.user_id
        )
        return {"budgets": budgets}
    except Exception as e:
        logging.error(f"Error getting budgets: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/budgets/{budget_id}/update-spend")
async def update_budget_spend(
    budget_id: str,
    current_user: AuthInfo = Depends(require_auth)
):
    """Update current spend for a budget"""
    try:
        success = await service_registry.usage_forecaster.update_budget_spend(budget_id)
        if success:
            return {"message": f"Budget {budget_id} spending updated successfully"}
        else:
            raise HTTPException(status_code=404, detail="Budget not found")
    except Exception as e:
        logging.error(f"Error updating budget spend: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/budgets/alerts")
async def get_budget_alerts(
    acknowledged: bool = False,
    current_user: AuthInfo = Depends(require_auth)
):
    """Get budget alerts for the current user"""
    try:
        alerts = await service_registry.usage_forecaster.get_budget_alerts(
            current_user.user_id, acknowledged
        )
        return {"alerts": alerts}
    except Exception as e:
        logging.error(f"Error getting budget alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/forecasting/dashboard")
async def get_forecasting_dashboard(current_user: AuthInfo = Depends(require_auth)):
    """Get comprehensive forecasting and budget dashboard"""
    try:
        dashboard = await service_registry.usage_forecaster.get_forecasting_dashboard(
            current_user.user_id
        )
        return dashboard
    except Exception as e:
        logging.error(f"Error getting forecasting dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/billing/setup-recurring")
async def setup_recurring_billing(
    plan_name: str,
    amount: float,
    billing_cycle: str = "monthly",
    current_user: AuthInfo = Depends(require_auth)
):
    """Setup recurring billing for a user"""
    try:
        from decimal import Decimal
        
        subscription_id = await service_registry.payment_processor.setup_recurring_billing(
            current_user.user_id, plan_name, Decimal(str(amount)), billing_cycle
        )
        
        return {
            "subscription_id": subscription_id,
            "plan_name": plan_name,
            "amount": amount,
            "billing_cycle": billing_cycle,
            "message": "Recurring billing setup successfully"
        }
    except Exception as e:
        logging.error(f"Error setting up recurring billing: {e}")
        raise HTTPException(status_code=400, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event streaming"""
    await websocket.accept()
    
    try:
        # Authenticate WebSocket connection
        auth_data = await websocket.receive_json()
        if 'api_key' not in auth_data:
            await websocket.send_json({"error": "Authentication required"})
            await websocket.close()
            return
        
        # Validate API key
        auth_info = await service_registry.access_control.validate_api_key(auth_data['api_key'])
        if not auth_info:
            await websocket.send_json({"error": "Invalid API key"})
            await websocket.close()
            return
        
        user_id = auth_info['user_id']
        
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "user_id": user_id,
            "timestamp": current_timestamp().isoformat()
        })
        
        # Event streaming loop
        while True:
            try:
                # Wait for messages (could be event subscriptions)
                message = await asyncio.wait_for(websocket.receive_json(), timeout=30)
                
                if message.get('type') == 'subscribe':
                    # Handle event subscription
                    event_types = message.get('events', [])
                    await websocket.send_json({
                        "type": "subscription_confirmed",
                        "events": event_types
                    })
                
                # Send periodic updates (simplified)
                await websocket.send_json({
                    "type": "status_update",
                    "timestamp": current_timestamp().isoformat(),
                    "status": "healthy"
                })
                
            except asyncio.TimeoutError:
                # Send keepalive
                await websocket.send_json({
                    "type": "keepalive",
                    "timestamp": current_timestamp().isoformat()
                })
                
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        await websocket.close()

# Service initialization endpoint (for testing)
@app.post("/internal/initialize")
async def initialize_services(services_config: Dict[str, Any]):
    """Initialize services (internal endpoint for testing)"""
    try:
        # This would normally be done during application startup
        # with dependency injection
        
        return {
            "message": "Services initialized",
            "timestamp": current_timestamp().isoformat()
        }
        
    except Exception as e:
        logging.error(f"Error initializing services: {e}")
        raise HTTPException(status_code=500, detail=f"Service initialization failed: {e}")

def create_app(config: Dict[str, Any], **services) -> FastAPI:
    """Factory function to create configured app"""
    # Register services
    service_registry.register_services(**services)
    
    # Configure app based on config
    if config.get('api', {}).get('enable_cors', True):
        cors_origins = config.get('api', {}).get('cors_origins', ['*'])
        # CORS is already configured above
    
    return app

async def start_server(config: Dict[str, Any], **services):
    """Start the API server"""
    app_instance = create_app(config, **services)
    
    host = config.get('api', {}).get('host', '0.0.0.0')
    port = config.get('api', {}).get('port', 8600)
    workers = config.get('api', {}).get('workers', 1)
    
    logging.info(f"Starting Cloud Infrastructure API Gateway on {host}:{port}")
    
    # Configure uvicorn
    uvicorn_config = uvicorn.Config(
        app=app_instance,
        host=host,
        port=port,
        workers=workers,
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(uvicorn_config)
    await server.serve()

if __name__ == "__main__":
    # For testing purposes
    import yaml
    
    # Load configuration
    with open("config/infrastructure.yaml", "r") as f:
        config = yaml.safe_load(f)
    
    # Run server
    asyncio.run(start_server(config))