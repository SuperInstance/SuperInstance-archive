#!/usr/bin/env python3
"""
Choice Economics Service - Main Application
Runs on port 8335 as requested
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
from typing import Dict, Any, List, Optional

from src.database import get_session, init_database
from src.frontend.statement_manager import FrontendStatementManager
from src.compute.allowance_optimizer import ComputeAllowanceOptimizer
from src.decision.cloud_decision_engine import CloudDecisionEngine
from src.optimization.speed_cost_optimizer import SpeedCostOptimizer
from src.optimization.battery_performance_chooser import BatteryPerformanceChooser
from src.privacy.privacy_convenience_options import PrivacyConvenienceOptions
from src.comparison.feature_price_comparison import FeatureVsPriceComparison
from src.rewards.loyalty_rewards_system import LoyaltyRewardsSystem
from src.rewards.referral_bonuses_system import ReferralBonusesSystem
from src.rewards.early_adopter_benefits import EarlyAdopterBenefits


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_database()
    yield


app = FastAPI(
    title="Choice Economics Service",
    description="Comprehensive choice economics system for user decisions and trade-offs",
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


@app.get("/")
async def root():
    return {
        "service": "Choice Economics",
        "version": "1.0.0",
        "port": 8335,
        "features": [
            "Frontend selection as statement",
            "Compute allowance optimization",
            "Local vs cloud decision engine",
            "Speed vs cost optimizer",
            "Battery vs performance chooser",
            "Privacy vs convenience options",
            "Feature vs price comparison",
            "Loyalty rewards system",
            "Referral bonuses",
            "Early adopter benefits"
        ]
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "choice-economics", "port": 8335}


# Frontend Statement Endpoints
@app.post("/frontend/statements")
async def create_frontend_statement(
    user_id: str,
    frontend_name: str,
    statement_text: str,
    satisfaction_score: int,
    session=Depends(get_session)
):
    manager = FrontendStatementManager(session)
    statement = await manager.create_frontend_statement(
        uuid.UUID(user_id), frontend_name, statement_text, satisfaction_score
    )
    return {"id": str(statement.id), "message": "Statement created successfully"}


@app.get("/frontend/recommendations/{user_id}")
async def get_frontend_recommendations(
    user_id: str,
    limit: int = 5,
    session=Depends(get_session)
):
    manager = FrontendStatementManager(session)
    recommendations = await manager.get_frontend_recommendations(uuid.UUID(user_id), limit)
    return {"recommendations": recommendations}


# Compute Allowance Endpoints
@app.post("/compute/optimize")
async def optimize_compute_allowance(
    user_id: str,
    budget_limit: float,
    priority_tasks: List[str],
    session=Depends(get_session)
):
    optimizer = ComputeAllowanceOptimizer(session)
    optimization = await optimizer.optimize_allowance_usage(
        uuid.UUID(user_id), budget_limit, priority_tasks
    )
    return optimization


@app.get("/compute/usage/{user_id}")
async def get_compute_usage(
    user_id: str,
    period_days: int = 30,
    session=Depends(get_session)
):
    optimizer = ComputeAllowanceOptimizer(session)
    usage = await optimizer.get_usage_analytics(uuid.UUID(user_id), period_days)
    return usage


# Cloud Decision Endpoints
@app.post("/decision/cloud")
async def make_cloud_decision(
    user_id: str,
    task_requirements: Dict[str, Any],
    session=Depends(get_session)
):
    engine = CloudDecisionEngine(session)
    decision = await engine.make_decision(uuid.UUID(user_id), task_requirements)
    return decision


# Speed vs Cost Optimization Endpoints
@app.post("/optimization/speed-cost")
async def optimize_speed_cost(
    user_id: str,
    task_requirements: Dict[str, Any],
    session=Depends(get_session)
):
    optimizer = SpeedCostOptimizer(session)
    optimization = await optimizer.optimize_speed_vs_cost(uuid.UUID(user_id), task_requirements)
    return optimization


# Battery Performance Endpoints
@app.post("/optimization/battery-performance")
async def choose_battery_performance(
    user_id: str,
    device_info: Dict[str, Any],
    usage_context: Dict[str, Any],
    session=Depends(get_session)
):
    chooser = BatteryPerformanceChooser(session)
    choice = await chooser.choose_battery_vs_performance(uuid.UUID(user_id), device_info, usage_context)
    return choice


# Privacy Convenience Endpoints
@app.post("/privacy/evaluate")
async def evaluate_privacy_convenience(
    user_id: str,
    data_request: Dict[str, Any],
    session=Depends(get_session)
):
    options = PrivacyConvenienceOptions(session)
    evaluation = await options.evaluate_privacy_vs_convenience(uuid.UUID(user_id), data_request)
    return evaluation


# Feature Price Comparison Endpoints
@app.post("/comparison/services")
async def compare_services(
    user_id: str,
    services: List[Dict[str, Any]],
    session=Depends(get_session)
):
    comparison = FeatureVsPriceComparison(session)
    result = await comparison.compare_services(uuid.UUID(user_id), services)
    return result


# Loyalty Rewards Endpoints
@app.post("/rewards/loyalty/earn")
async def earn_loyalty_points(
    user_id: str,
    action: str,
    points: int,
    session=Depends(get_session)
):
    system = LoyaltyRewardsSystem(session)
    result = await system.award_points(uuid.UUID(user_id), action, points)
    return result


@app.get("/rewards/loyalty/balance/{user_id}")
async def get_loyalty_balance(
    user_id: str,
    session=Depends(get_session)
):
    system = LoyaltyRewardsSystem(session)
    balance = await system.get_user_balance(uuid.UUID(user_id))
    return {"balance": balance}


@app.post("/rewards/loyalty/redeem")
async def redeem_loyalty_reward(
    user_id: str,
    reward_id: str,
    session=Depends(get_session)
):
    system = LoyaltyRewardsSystem(session)
    result = await system.redeem_reward(uuid.UUID(user_id), uuid.UUID(reward_id))
    return result


# Referral Bonuses Endpoints
@app.post("/rewards/referrals/create")
async def create_referral_link(
    user_id: str,
    campaign: str = "default",
    session=Depends(get_session)
):
    system = ReferralBonusesSystem(session)
    link = await system.create_referral_link(uuid.UUID(user_id), campaign)
    return {"referral_code": link.referral_code, "link": f"/signup?ref={link.referral_code}"}


@app.post("/rewards/referrals/signup")
async def process_referral_signup(
    referral_code: str,
    new_user_id: str,
    session=Depends(get_session)
):
    system = ReferralBonusesSystem(session)
    result = await system.process_referral_signup(referral_code, uuid.UUID(new_user_id))
    return result


# Early Adopter Benefits Endpoints
@app.get("/rewards/early-adopter/status/{user_id}")
async def get_early_adopter_status(
    user_id: str,
    session=Depends(get_session)
):
    benefits = EarlyAdopterBenefits(session)
    status = await benefits.assess_early_adopter_status(uuid.UUID(user_id))
    return status


@app.post("/rewards/early-adopter/claim")
async def claim_early_adopter_benefit(
    user_id: str,
    benefit_type: str,
    session=Depends(get_session)
):
    benefits = EarlyAdopterBenefits(session)
    result = await benefits.claim_early_adopter_benefit(uuid.UUID(user_id), benefit_type)
    return result


@app.post("/rewards/early-adopter/beta/enroll")
async def enroll_in_beta_program(
    user_id: str,
    program_name: str,
    session=Depends(get_session)
):
    benefits = EarlyAdopterBenefits(session)
    result = await benefits.enroll_in_beta_program(uuid.UUID(user_id), program_name)
    return result


# Analytics Endpoints
@app.get("/analytics/user/{user_id}")
async def get_user_analytics(
    user_id: str,
    period_days: int = 30,
    session=Depends(get_session)
):
    """Get comprehensive user analytics across all systems"""
    user_uuid = uuid.UUID(user_id)
    
    # Gather analytics from all systems
    compute_optimizer = ComputeAllowanceOptimizer(session)
    loyalty_system = LoyaltyRewardsSystem(session)
    early_adopter = EarlyAdopterBenefits(session)
    
    analytics = {
        "user_id": user_id,
        "period_days": period_days,
        "compute_usage": await compute_optimizer.get_usage_analytics(user_uuid, period_days),
        "loyalty_status": await loyalty_system.get_user_tier_info(user_uuid),
        "early_adopter_status": await early_adopter.get_early_adopter_analytics(user_uuid, period_days)
    }
    
    return analytics


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8335,
        reload=True,
        log_level="info"
    )