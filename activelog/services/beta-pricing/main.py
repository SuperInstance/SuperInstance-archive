#!/usr/bin/env python3
"""
Beta Pricing Platform
Comprehensive beta pricing strategies and optimization system
Port: 8338

Features:
- Free beta tier with limits
- Discounted early adopter pricing
- CCC rewards for bug reports
- Referral bonuses for beta users
- Usage tracking for pricing validation
- A/B testing different price points
- Survey system for price sensitivity
- Competitor pricing analysis
- Value perception testing
- Conversion rate optimization
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import json
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta, date
import sqlite3
import aiofiles
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
import random
import hashlib

# Import all the subsystem modules
from beta_tier_manager import beta_tier_manager
from early_adopter_pricing import early_adopter_pricing
from ccc_rewards import ccc_rewards_system
from referral_system import referral_bonus_system
from usage_tracker import usage_tracking_system
from ab_testing import ab_testing_system
from survey_system import pricing_survey_system
from competitor_analysis import competitor_analyzer
from value_perception import value_perception_tester
from conversion_optimizer import conversion_rate_optimizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Beta Pricing Platform",
    description="Comprehensive beta pricing strategies and optimization system",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8088"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# Beta Pricing Data Models
class BetaTier(str, Enum):
    FREE = "free"
    EARLY_ADOPTER = "early_adopter"
    BETA_PLUS = "beta_plus"
    PREMIUM_BETA = "premium_beta"

class PricingStrategy(str, Enum):
    FREEMIUM = "freemium"
    DISCOUNT_BASED = "discount_based"
    VALUE_BASED = "value_based"
    PENETRATION = "penetration"
    SKIMMING = "skimming"

class RewardType(str, Enum):
    CCC_TOKENS = "ccc_tokens"
    ACCOUNT_CREDITS = "account_credits"
    TIER_UPGRADE = "tier_upgrade"
    EXCLUSIVE_ACCESS = "exclusive_access"

class BetaUser(BaseModel):
    id: str
    email: str
    name: str
    tier: BetaTier
    signup_date: datetime
    
    # Usage tracking
    total_api_calls: int = 0
    monthly_api_calls: int = 0
    features_used: List[str] = []
    
    # Pricing experiment
    experiment_group: str = "control"
    price_point: Decimal = Decimal('0')
    has_converted: bool = False
    conversion_date: Optional[datetime] = None
    
    # Rewards and referrals
    ccc_balance: Decimal = Decimal('0')
    referral_code: str
    referred_by: Optional[str] = None
    referrals_made: int = 0
    
    # Survey participation
    survey_responses: List[str] = []
    price_sensitivity_score: Optional[float] = None
    
    created_at: datetime
    updated_at: datetime

class PricingTier(BaseModel):
    id: str
    name: str
    tier: BetaTier
    base_price: Decimal
    beta_price: Decimal
    discount_percentage: Decimal
    
    # Limits
    api_calls_limit: int
    features_included: List[str]
    storage_limit_gb: int
    support_level: str
    
    # Benefits
    ccc_earning_rate: Decimal  # CCC per dollar spent
    referral_bonus: Decimal
    early_access: bool
    
    valid_until: datetime
    created_at: datetime

class UsageEvent(BaseModel):
    id: str
    user_id: str
    event_type: str  # api_call, feature_use, login, etc.
    feature_name: Optional[str] = None
    
    # Metrics
    duration_ms: Optional[int] = None
    api_endpoint: Optional[str] = None
    success: bool = True
    
    # Context
    session_id: str
    ip_address: str
    user_agent: str
    
    timestamp: datetime

# Database initialization
def init_database():
    """Initialize SQLite database for persistent storage"""
    os.makedirs("/home/activeloguser/activelog/services/beta-pricing/data", exist_ok=True)
    conn = sqlite3.connect("/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db")
    cursor = conn.cursor()
    
    # Beta users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS beta_users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            tier TEXT DEFAULT 'free',
            signup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_api_calls INTEGER DEFAULT 0,
            monthly_api_calls INTEGER DEFAULT 0,
            experiment_group TEXT DEFAULT 'control',
            price_point DECIMAL DEFAULT 0,
            has_converted BOOLEAN DEFAULT FALSE,
            ccc_balance DECIMAL DEFAULT 0,
            referral_code TEXT UNIQUE NOT NULL,
            referred_by TEXT,
            referrals_made INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Pricing tiers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pricing_tiers (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tier TEXT NOT NULL,
            base_price DECIMAL NOT NULL,
            beta_price DECIMAL NOT NULL,
            discount_percentage DECIMAL NOT NULL,
            api_calls_limit INTEGER NOT NULL,
            storage_limit_gb INTEGER NOT NULL,
            support_level TEXT NOT NULL,
            ccc_earning_rate DECIMAL DEFAULT 0,
            referral_bonus DECIMAL DEFAULT 0,
            early_access BOOLEAN DEFAULT FALSE,
            valid_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Usage events table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_events (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            feature_name TEXT,
            duration_ms INTEGER,
            api_endpoint TEXT,
            success BOOLEAN DEFAULT TRUE,
            session_id TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES beta_users (id)
        )
    ''')
    
    # AB testing experiments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ab_experiments (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'active',
            control_group TEXT NOT NULL,
            test_groups TEXT NOT NULL, -- JSON array
            start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            end_date TIMESTAMP,
            conversion_metric TEXT DEFAULT 'signup_to_paid',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Survey responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS survey_responses (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            survey_type TEXT NOT NULL,
            questions_responses TEXT NOT NULL, -- JSON
            price_sensitivity_score DECIMAL,
            willingness_to_pay DECIMAL,
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES beta_users (id)
        )
    ''')
    
    # Competitor pricing data table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_pricing (
            id TEXT PRIMARY KEY,
            competitor_name TEXT NOT NULL,
            product_name TEXT NOT NULL,
            pricing_tier TEXT NOT NULL,
            price DECIMAL NOT NULL,
            features TEXT NOT NULL, -- JSON array
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# Utility functions
def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Simple authentication - in production, use proper JWT validation"""
    return "user_123"

def generate_user_id() -> str:
    """Generate unique user ID"""
    return f"BETA_{uuid.uuid4().hex[:8].upper()}"

def generate_referral_code() -> str:
    """Generate unique referral code"""
    return f"REF{uuid.uuid4().hex[:6].upper()}"

def hash_ip_address(ip: str) -> str:
    """Hash IP address for privacy"""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    
    # Initialize default pricing tiers
    await beta_tier_manager.create_default_tiers()
    
    # Start background tasks
    asyncio.create_task(usage_tracking_system.start_analytics_processing())
    asyncio.create_task(competitor_analyzer.start_competitor_monitoring())
    
    logger.info("Beta Pricing Platform started on port 8338")

# API Routes

@app.get("/")
async def root():
    return {
        "service": "Beta Pricing Platform",
        "version": "1.0.0",
        "port": 8338,
        "features": [
            "Free beta tier with limits",
            "Discounted early adopter pricing",
            "CCC rewards for bug reports",
            "Referral bonuses for beta users",
            "Usage tracking for pricing validation",
            "A/B testing different price points",
            "Survey system for price sensitivity",
            "Competitor pricing analysis",
            "Value perception testing",
            "Conversion rate optimization"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Beta User Management Routes
@app.post("/api/users/signup")
async def signup_beta_user(
    user_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Sign up a new beta user"""
    
    user_id = generate_user_id()
    referral_code = generate_referral_code()
    
    # Assign to A/B testing group
    experiment_group = await ab_testing_system.assign_user_to_experiment(
        user_id, "pricing_experiment_v1"
    )
    
    # Get pricing tier for experiment group
    tier_info = await early_adopter_pricing.get_tier_for_experiment(experiment_group)
    
    user = BetaUser(
        id=user_id,
        email=user_data["email"],
        name=user_data["name"],
        tier=BetaTier(tier_info["tier"]),
        signup_date=datetime.now(),
        experiment_group=experiment_group,
        price_point=Decimal(str(tier_info["price"])),
        referral_code=referral_code,
        referred_by=user_data.get("referral_code"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Store user
    conn = sqlite3.connect("/home/activeloguser/activelog/services/beta-pricing/data/beta_pricing.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO beta_users 
        (id, email, name, tier, experiment_group, price_point, referral_code, referred_by, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.id, user.email, user.name, user.tier.value,
        user.experiment_group, float(user.price_point),
        user.referral_code, user.referred_by, user.model_dump_json()
    ))
    
    conn.commit()
    conn.close()
    
    # Process referral bonus if applicable
    if user.referred_by:
        await referral_bonus_system.process_referral(user.referred_by, user_id)
    
    # Send welcome rewards
    await ccc_rewards_system.grant_signup_bonus(user_id)
    
    return {
        "user_id": user_id,
        "tier": user.tier.value,
        "referral_code": user.referral_code,
        "experiment_group": user.experiment_group,
        "welcome_bonus": await ccc_rewards_system.get_signup_bonus_amount()
    }

@app.get("/api/users/{user_id}")
async def get_user_profile(
    user_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get beta user profile and stats"""
    
    return await beta_tier_manager.get_user_profile(user_id)

@app.post("/api/users/{user_id}/upgrade")
async def upgrade_user_tier(
    user_id: str,
    upgrade_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Upgrade user to paid tier"""
    
    upgrade_result = await early_adopter_pricing.process_tier_upgrade(
        user_id, upgrade_data["target_tier"], upgrade_data.get("payment_method")
    )
    
    # Track conversion
    await conversion_rate_optimizer.track_conversion(user_id, "tier_upgrade")
    
    return upgrade_result

# Usage Tracking Routes
@app.post("/api/usage/track")
async def track_usage_event(
    usage_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Track usage event for pricing analytics"""
    
    event = UsageEvent(
        id=f"EVENT_{uuid.uuid4().hex[:8].upper()}",
        user_id=usage_data["user_id"],
        event_type=usage_data["event_type"],
        feature_name=usage_data.get("feature_name"),
        duration_ms=usage_data.get("duration_ms"),
        api_endpoint=usage_data.get("api_endpoint"),
        success=usage_data.get("success", True),
        session_id=usage_data["session_id"],
        ip_address=hash_ip_address(usage_data.get("ip_address", "")),
        user_agent=usage_data.get("user_agent", ""),
        timestamp=datetime.now()
    )
    
    await usage_tracking_system.record_usage_event(event)
    
    # Check tier limits
    tier_status = await beta_tier_manager.check_usage_limits(usage_data["user_id"])
    
    return {
        "event_id": event.id,
        "recorded": True,
        "tier_status": tier_status
    }

@app.get("/api/usage/analytics/{user_id}")
async def get_usage_analytics(
    user_id: str,
    period: str = "month",
    current_user: str = Depends(authenticate_user)
):
    """Get usage analytics for user"""
    
    analytics = await usage_tracking_system.get_user_analytics(user_id, period)
    return analytics

# A/B Testing Routes
@app.post("/api/experiments/create")
async def create_pricing_experiment(
    experiment_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Create A/B testing experiment for pricing"""
    
    experiment = await ab_testing_system.create_experiment(
        experiment_data["name"],
        experiment_data["description"],
        experiment_data["test_groups"],
        experiment_data.get("conversion_metric", "signup_to_paid")
    )
    
    return experiment

@app.get("/api/experiments/{experiment_id}/results")
async def get_experiment_results(
    experiment_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get A/B testing experiment results"""
    
    results = await ab_testing_system.get_experiment_results(experiment_id)
    return results

@app.post("/api/experiments/{experiment_id}/assign")
async def assign_user_to_experiment(
    experiment_id: str,
    assignment_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Assign user to experiment group"""
    
    assignment = await ab_testing_system.assign_user_to_experiment(
        assignment_data["user_id"], experiment_id
    )
    
    return {"user_id": assignment_data["user_id"], "group": assignment}

# Survey System Routes
@app.post("/api/surveys/create")
async def create_pricing_survey(
    survey_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Create pricing sensitivity survey"""
    
    survey = await pricing_survey_system.create_survey(
        survey_data["title"],
        survey_data["questions"],
        survey_data.get("target_users", [])
    )
    
    return survey

@app.post("/api/surveys/{survey_id}/respond")
async def submit_survey_response(
    survey_id: str,
    response_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Submit survey response"""
    
    response = await pricing_survey_system.submit_response(
        survey_id,
        response_data["user_id"],
        response_data["responses"]
    )
    
    # Grant CCC reward for survey completion
    await ccc_rewards_system.grant_survey_completion_reward(response_data["user_id"])
    
    return response

@app.get("/api/surveys/insights")
async def get_pricing_insights(
    current_user: str = Depends(authenticate_user)
):
    """Get pricing insights from surveys"""
    
    insights = await pricing_survey_system.generate_pricing_insights()
    return insights

# CCC Rewards Routes
@app.post("/api/rewards/bug-report")
async def report_bug_for_reward(
    bug_report: dict,
    current_user: str = Depends(authenticate_user)
):
    """Submit bug report and earn CCC rewards"""
    
    reward = await ccc_rewards_system.process_bug_report(
        bug_report["user_id"],
        bug_report["severity"],
        bug_report["description"],
        bug_report.get("steps_to_reproduce", [])
    )
    
    return reward

@app.get("/api/rewards/{user_id}/balance")
async def get_ccc_balance(
    user_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get user's CCC reward balance"""
    
    balance = await ccc_rewards_system.get_user_balance(user_id)
    return balance

@app.post("/api/rewards/{user_id}/redeem")
async def redeem_ccc_rewards(
    user_id: str,
    redemption_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Redeem CCC rewards"""
    
    redemption = await ccc_rewards_system.redeem_rewards(
        user_id,
        redemption_data["reward_type"],
        redemption_data["amount"]
    )
    
    return redemption

# Referral System Routes
@app.get("/api/referrals/{user_id}/stats")
async def get_referral_stats(
    user_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get referral statistics"""
    
    stats = await referral_bonus_system.get_referral_stats(user_id)
    return stats

@app.post("/api/referrals/validate")
async def validate_referral_code(
    validation_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Validate referral code"""
    
    validation = await referral_bonus_system.validate_referral_code(
        validation_data["referral_code"]
    )
    
    return validation

# Competitor Analysis Routes
@app.get("/api/competitors/pricing")
async def get_competitor_pricing(
    category: str = None,
    current_user: str = Depends(authenticate_user)
):
    """Get competitor pricing analysis"""
    
    analysis = await competitor_analyzer.get_pricing_analysis(category)
    return analysis

@app.post("/api/competitors/add")
async def add_competitor_data(
    competitor_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Add competitor pricing data"""
    
    result = await competitor_analyzer.add_competitor_data(
        competitor_data["name"],
        competitor_data["product"],
        competitor_data["tiers"]
    )
    
    return result

# Value Perception Routes
@app.post("/api/value-perception/test")
async def run_value_perception_test(
    test_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Run value perception test"""
    
    test = await value_perception_tester.run_test(
        test_data["user_id"],
        test_data["feature_set"],
        test_data["price_points"]
    )
    
    return test

@app.get("/api/value-perception/results/{test_id}")
async def get_value_perception_results(
    test_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get value perception test results"""
    
    results = await value_perception_tester.get_test_results(test_id)
    return results

# Conversion Optimization Routes
@app.get("/api/conversion/analytics")
async def get_conversion_analytics(
    period: str = "month",
    segment: str = None,
    current_user: str = Depends(authenticate_user)
):
    """Get conversion rate analytics"""
    
    analytics = await conversion_rate_optimizer.get_conversion_analytics(period, segment)
    return analytics

@app.post("/api/conversion/optimize")
async def optimize_conversion_funnel(
    optimization_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Optimize conversion funnel"""
    
    optimization = await conversion_rate_optimizer.optimize_funnel(
        optimization_data["funnel_step"],
        optimization_data["target_metric"]
    )
    
    return optimization

# Analytics and Dashboard Routes
@app.get("/api/analytics/dashboard")
async def get_pricing_dashboard(
    period: str = "month",
    current_user: str = Depends(authenticate_user)
):
    """Get comprehensive pricing analytics dashboard"""
    
    # Aggregate data from all systems
    user_metrics = await beta_tier_manager.get_tier_metrics()
    usage_metrics = await usage_tracking_system.get_platform_usage(period)
    experiment_results = await ab_testing_system.get_active_experiments_summary()
    conversion_metrics = await conversion_rate_optimizer.get_conversion_summary()
    competitor_insights = await competitor_analyzer.get_market_position()
    
    dashboard = {
        "period": period,
        "user_metrics": user_metrics,
        "usage_metrics": usage_metrics,
        "experiments": experiment_results,
        "conversions": conversion_metrics,
        "market_position": competitor_insights,
        "generated_at": datetime.now().isoformat()
    }
    
    return dashboard

@app.get("/api/analytics/pricing-recommendations")
async def get_pricing_recommendations(
    current_user: str = Depends(authenticate_user)
):
    """Get AI-powered pricing recommendations"""
    
    recommendations = await early_adopter_pricing.generate_pricing_recommendations()
    return recommendations

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8338)