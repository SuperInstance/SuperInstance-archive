from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging
import uuid
from typing import Dict, Any, List, Optional
from decimal import Decimal
from pydantic import BaseModel, Field
from datetime import datetime

# Import our modules
from .database import get_db, engine, Base
from .cost_calculator.engine import CostPlusCalculator
from .inflation.automation import InflationAutomation
from .tracking.cost_tracker import ComputeCostTracker
from .peak_pricing.scheduler import PeakPricingScheduler
from .server_tiers.garage_farm_manager import GarageFarmManager
from .revenue_split.frontend_revenue import FrontendRevenueManager
from .database import (
    ResourceType, ComputeLocation, PricingTier
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting ActiveLog Pricing Engine...")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down ActiveLog Pricing Engine...")
    await engine.dispose()

app = FastAPI(
    title="ActiveLog Pricing Engine",
    description="Advanced pricing system with cost-plus methodology, inflation adjustments, and revenue management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for API
class PriceCalculationRequest(BaseModel):
    resource_type: str
    units: float
    user_id: Optional[str] = None
    location: str = "cloud"
    tier: Optional[str] = None
    include_peak_pricing: bool = True

class BulkPricingRequest(BaseModel):
    resource_requests: List[Dict[str, Any]]
    user_id: Optional[str] = None
    apply_bulk_discount: bool = True

class InflationAdjustmentRequest(BaseModel):
    emergency_rate: float
    reason: str
    affected_tiers: Optional[List[str]] = None

class RevenueShareRequest(BaseModel):
    user_id: str
    frontend_id: str
    transaction_amount: float
    transaction_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class PeakScheduleRequest(BaseModel):
    name: str
    timezone_name: str = "UTC"
    peak_start_hour: int = 9
    peak_end_hour: int = 17
    peak_days: Optional[List[int]] = None
    peak_multiplier: Optional[float] = None
    off_peak_multiplier: Optional[float] = None

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ActiveLog Pricing Engine",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/overview")
async def get_system_overview():
    """Get comprehensive overview of pricing engine capabilities"""
    return {
        "service": "ActiveLog Pricing Engine",
        "port": 8326,
        "capabilities": {
            "cost_plus_pricing": "2-dollar markup with inflation adjustments",
            "inflation_automation": "Monthly and emergency adjustments",
            "cost_tracking": "Per-user compute cost analysis",
            "peak_pricing": "Off-peak discounts and demand-based pricing",
            "garage_server_tiers": "5-tier garage infrastructure pricing",
            "revenue_split": "$1 to frontend, $1 to ActiveLog",
            "membership_scaling": "Price reduction as user base grows",
            "local_vs_cloud": "Cost comparison and optimization",
            "mobile_optimization": "Battery life vs cost analysis",
            "llm_savings": "Pass-through savings for efficient models",
            "allowance_tracking": "Membership allowance management",
            "cost_forecasting": "Predictive cost analysis"
        },
        "integration_points": {
            "payment_v2": "port 8325 - Credit processing and billing",
            "activeledger": "port 8122 - Financial ledger integration",
            "api_gateway": "port 8001 - Request routing and auth"
        }
    }

# Cost calculation endpoints
@app.post("/api/pricing/calculate")
async def calculate_price(
    request: PriceCalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    """Calculate price using cost-plus methodology"""
    try:
        calculator = CostPlusCalculator(db)
        
        result = await calculator.calculate_price(
            resource_type=ResourceType(request.resource_type),
            units=Decimal(str(request.units)),
            user_id=uuid.UUID(request.user_id) if request.user_id else None,
            location=ComputeLocation(request.location),
            tier=PricingTier(request.tier) if request.tier else None,
            include_peak_pricing=request.include_peak_pricing
        )
        
        return result
    except Exception as e:
        logger.error(f"Price calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/pricing/bulk-calculate")
async def calculate_bulk_pricing(
    request: BulkPricingRequest,
    db: AsyncSession = Depends(get_db)
):
    """Calculate bulk pricing with discounts"""
    try:
        calculator = CostPlusCalculator(db)
        
        result = await calculator.calculate_bulk_pricing(
            resource_requests=request.resource_requests,
            user_id=uuid.UUID(request.user_id) if request.user_id else None,
            apply_bulk_discount=request.apply_bulk_discount
        )
        
        return result
    except Exception as e:
        logger.error(f"Bulk pricing calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pricing/breakdown/{resource_type}")
async def get_pricing_breakdown(
    resource_type: str,
    units: float = 1.0,
    db: AsyncSession = Depends(get_db)
):
    """Get pricing breakdown across all tiers"""
    try:
        calculator = CostPlusCalculator(db)
        
        result = await calculator.get_pricing_breakdown_by_tier(
            resource_type=ResourceType(resource_type),
            units=Decimal(str(units))
        )
        
        return result
    except Exception as e:
        logger.error(f"Pricing breakdown failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Inflation management endpoints
@app.post("/api/inflation/monthly-update")
async def run_monthly_inflation_update(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Run monthly inflation adjustment"""
    try:
        automation = InflationAutomation(db)
        result = await automation.run_monthly_inflation_update()
        return result
    except Exception as e:
        logger.error(f"Monthly inflation update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inflation/emergency-adjustment")
async def emergency_inflation_adjustment(
    request: InflationAdjustmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Apply emergency inflation adjustment"""
    try:
        automation = InflationAutomation(db)
        
        result = await automation.emergency_inflation_adjustment(
            emergency_rate=Decimal(str(request.emergency_rate)),
            reason=request.reason,
            affected_tiers=request.affected_tiers
        )
        
        return result
    except Exception as e:
        logger.error(f"Emergency inflation adjustment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/inflation/forecast")
async def get_inflation_forecast(
    months_ahead: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """Get inflation forecast"""
    try:
        automation = InflationAutomation(db)
        result = await automation.get_inflation_forecast(months_ahead)
        return result
    except Exception as e:
        logger.error(f"Inflation forecast failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Cost tracking endpoints
@app.post("/api/tracking/record-usage")
async def record_compute_usage(
    user_id: str,
    resource_type: str,
    location: str,
    units_consumed: float,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Record compute usage and calculate costs"""
    try:
        tracker = ComputeCostTracker(db)
        
        result = await tracker.track_compute_usage(
            user_id=uuid.UUID(user_id),
            resource_type=ResourceType(resource_type),
            location=ComputeLocation(location),
            units_consumed=Decimal(str(units_consumed)),
            session_id=session_id
        )
        
        return result
    except Exception as e:
        logger.error(f"Usage tracking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tracking/user-summary/{user_id}")
async def get_user_cost_summary(
    user_id: str,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get cost summary for user"""
    try:
        tracker = ComputeCostTracker(db)
        
        result = await tracker.get_user_cost_summary(
            user_id=uuid.UUID(user_id),
            period_days=period_days
        )
        
        return result
    except Exception as e:
        logger.error(f"User cost summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tracking/trends/{user_id}")
async def get_cost_trends(
    user_id: str,
    days: int = 90,
    db: AsyncSession = Depends(get_db)
):
    """Get cost trends analysis"""
    try:
        tracker = ComputeCostTracker(db)
        
        result = await tracker.get_cost_trends(
            user_id=uuid.UUID(user_id),
            days=days
        )
        
        return result
    except Exception as e:
        logger.error(f"Cost trends analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Peak pricing endpoints
@app.get("/api/peak-pricing/current-multiplier")
async def get_current_pricing_multiplier(
    timestamp: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get current pricing multiplier"""
    try:
        scheduler = PeakPricingScheduler(db)
        
        check_time = datetime.fromisoformat(timestamp) if timestamp else datetime.utcnow()
        result = await scheduler.get_pricing_multiplier(check_time)
        
        return result
    except Exception as e:
        logger.error(f"Pricing multiplier lookup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/peak-pricing/create-schedule")
async def create_peak_schedule(
    request: PeakScheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create peak pricing schedule"""
    try:
        scheduler = PeakPricingScheduler(db)
        
        result = await scheduler.create_peak_schedule(
            name=request.name,
            timezone_name=request.timezone_name,
            peak_start_hour=request.peak_start_hour,
            peak_end_hour=request.peak_end_hour,
            peak_days=request.peak_days,
            peak_multiplier=Decimal(str(request.peak_multiplier)) if request.peak_multiplier else None,
            off_peak_multiplier=Decimal(str(request.off_peak_multiplier)) if request.off_peak_multiplier else None
        )
        
        return result
    except Exception as e:
        logger.error(f"Peak schedule creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/peak-pricing/optimize-job")
async def optimize_job_scheduling(
    job_duration_hours: int,
    max_delay_hours: int = 24,
    cost_threshold: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """Find optimal time to run a job"""
    try:
        scheduler = PeakPricingScheduler(db)
        
        result = await scheduler.optimize_job_scheduling(
            job_duration_hours=job_duration_hours,
            max_delay_hours=max_delay_hours,
            cost_threshold=Decimal(str(cost_threshold)) if cost_threshold else None
        )
        
        return result
    except Exception as e:
        logger.error(f"Job scheduling optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Garage server farm endpoints
@app.post("/api/garage-farms/initialize-tiers")
async def initialize_server_tiers(db: AsyncSession = Depends(get_db)):
    """Initialize server farm tiers"""
    try:
        manager = GarageFarmManager(db)
        result = await manager.initialize_server_farm_tiers()
        return result
    except Exception as e:
        logger.error(f"Server tier initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/garage-farms/optimal-tier/{user_id}")
async def get_optimal_tier(
    user_id: str,
    cpu_hours_per_month: int = 100,
    gpu_hours_per_month: int = 50,
    monthly_budget: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get optimal server tier recommendation"""
    try:
        manager = GarageFarmManager(db)
        
        requirements = {
            "cpu_hours_per_month": cpu_hours_per_month,
            "gpu_hours_per_month": gpu_hours_per_month
        }
        
        budget_constraints = None
        if monthly_budget:
            budget_constraints = {"monthly_max": Decimal(str(monthly_budget))}
        
        result = await manager.get_optimal_tier_for_user(
            user_id=uuid.UUID(user_id),
            resource_requirements=requirements,
            budget_constraints=budget_constraints
        )
        
        return result
    except Exception as e:
        logger.error(f"Optimal tier recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/garage-farms/vs-cloud-savings/{user_id}")
async def calculate_garage_vs_cloud_savings(
    user_id: str,
    cpu_hours_per_month: int = 100,
    gpu_hours_per_month: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Calculate garage vs cloud cost savings"""
    try:
        manager = GarageFarmManager(db)
        
        usage_scenario = {
            "cpu_hours_per_month": cpu_hours_per_month,
            "gpu_hours_per_month": gpu_hours_per_month
        }
        
        result = await manager.calculate_garage_vs_cloud_savings(
            user_id=uuid.UUID(user_id),
            usage_scenario=usage_scenario
        )
        
        return result
    except Exception as e:
        logger.error(f"Garage vs cloud savings calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Revenue split endpoints
@app.post("/api/revenue/process-split")
async def process_revenue_split(
    request: RevenueShareRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process frontend owner revenue split"""
    try:
        manager = FrontendRevenueManager(db)
        
        result = await manager.process_revenue_split(
            user_id=uuid.UUID(request.user_id),
            frontend_id=request.frontend_id,
            transaction_amount=Decimal(str(request.transaction_amount)),
            transaction_id=request.transaction_id,
            metadata=request.metadata
        )
        
        return result
    except Exception as e:
        logger.error(f"Revenue split processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/revenue/frontend-summary/{frontend_id}")
async def get_frontend_revenue_summary(
    frontend_id: str,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get revenue summary for frontend"""
    try:
        manager = FrontendRevenueManager(db)
        
        result = await manager.get_frontend_revenue_summary(
            frontend_id=frontend_id,
            period_days=period_days
        )
        
        return result
    except Exception as e:
        logger.error(f"Frontend revenue summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/revenue/owner-dashboard/{owner_id}")
async def get_frontend_owner_dashboard(
    owner_id: str,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive dashboard for frontend owner"""
    try:
        manager = FrontendRevenueManager(db)
        
        result = await manager.get_frontend_owner_dashboard(
            owner_user_id=uuid.UUID(owner_id),
            period_days=period_days
        )
        
        return result
    except Exception as e:
        logger.error(f"Frontend owner dashboard failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System configuration endpoints
@app.post("/api/config/update-pricing")
async def update_pricing_config(
    config_name: str,
    base_cost: Optional[float] = None,
    markup_amount: Optional[float] = None,
    tier: Optional[str] = None,
    resource_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update pricing configuration"""
    try:
        calculator = CostPlusCalculator(db)
        
        result = await calculator.update_pricing_config(
            config_name=config_name,
            base_cost=Decimal(str(base_cost)) if base_cost is not None else None,
            markup_amount=Decimal(str(markup_amount)) if markup_amount is not None else None,
            tier=PricingTier(tier) if tier else None,
            resource_type=ResourceType(resource_type) if resource_type else None
        )
        
        return {
            "updated": True,
            "config_id": str(result.id),
            "config_name": result.config_name,
            "base_cost": float(result.base_cost),
            "markup_amount": float(result.markup_amount)
        }
    except Exception as e:
        logger.error(f"Pricing config update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8326)