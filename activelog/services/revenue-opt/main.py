from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from src.api import router
from src.core.config import settings
from src.core.revenue_monitor import RevenueMonitor
from src.services.churn_predictor import ChurnPredictor
from src.services.upsell_detector import UpsellDetector
from src.services.ab_testing import ABTestingService
from src.services.ltv_calculator import LTVCalculator
from src.services.acquisition_tracker import AcquisitionTracker
from src.services.referral_optimizer import ReferralOptimizer
from src.services.funnel_analyzer import FunnelAnalyzer
from src.services.payment_recovery import PaymentRecoveryService
from src.services.subscription_optimizer import SubscriptionOptimizer

# Global service instances
services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize all revenue optimization services
    services["revenue_monitor"] = RevenueMonitor(monthly_target=settings.MONTHLY_TARGET)
    services["churn_predictor"] = ChurnPredictor()
    services["upsell_detector"] = UpsellDetector()
    services["ab_testing"] = ABTestingService()
    services["ltv_calculator"] = LTVCalculator()
    services["acquisition_tracker"] = AcquisitionTracker()
    services["referral_optimizer"] = ReferralOptimizer()
    services["funnel_analyzer"] = FunnelAnalyzer()
    services["payment_recovery"] = PaymentRecoveryService()
    services["subscription_optimizer"] = SubscriptionOptimizer()
    
    # Start background monitoring
    await services["revenue_monitor"].start_monitoring()
    
    yield
    
    # Cleanup
    await services["revenue_monitor"].stop_monitoring()

app = FastAPI(
    title="Revenue Optimizer Service",
    description="Advanced revenue optimization with churn prediction, upselling, and analytics",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router.router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Revenue Optimizer Service", "status": "active"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            name: "running" for name in services.keys()
        },
        "monthly_target": settings.MONTHLY_TARGET
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8347)