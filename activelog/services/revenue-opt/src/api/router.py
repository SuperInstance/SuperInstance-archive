from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional
from pydantic import BaseModel

router = APIRouter()

# Request/Response models
class RevenueRecord(BaseModel):
    amount: float
    source: str = "general"

class TargetUpdate(BaseModel):
    monthly: Optional[float] = None
    quarterly: Optional[float] = None
    yearly: Optional[float] = None

class ABTestConfig(BaseModel):
    test_name: str
    control_price: float
    variant_price: float
    target_metric: str = "conversion_rate"
    duration_days: int = 30
    traffic_split: float = 0.5

class ReferralProgramConfig(BaseModel):
    name: str
    referrer_reward_type: str = "cash"
    referrer_reward_amount: float = 5.0
    referee_reward_type: str = "discount"
    referee_reward_amount: float = 5.0
    minimum_referee_spend: float = 0.0
    expiry_days: int = 90
    max_referrals_per_user: int = 10
    is_active: bool = True

# Revenue Monitoring Endpoints
@router.post("/revenue/record")
async def record_revenue(revenue: RevenueRecord):
    """Record a revenue transaction"""
    from main import services
    return await services["revenue_monitor"].record_revenue(revenue.amount, revenue.source)

@router.get("/revenue/targets")
async def get_targets():
    """Get current revenue target status"""
    from main import services
    return await services["revenue_monitor"].get_target_status()

@router.put("/revenue/targets")
async def update_targets(targets: TargetUpdate):
    """Update revenue targets"""
    from main import services
    target_dict = targets.dict(exclude_unset=True)
    return await services["revenue_monitor"].set_revenue_targets(target_dict)

@router.get("/revenue/analytics")
async def get_analytics(period_days: int = 30):
    """Get revenue analytics"""
    from main import services
    return await services["revenue_monitor"].get_revenue_analytics(period_days)

@router.get("/revenue/forecast")
async def get_forecast(forecast_days: int = 30):
    """Get revenue forecast"""
    from main import services
    return await services["revenue_monitor"].generate_revenue_forecast(forecast_days)

@router.get("/revenue/alerts")
async def get_alerts():
    """Get active revenue alerts"""
    from main import services
    alerts = await services["revenue_monitor"].get_active_alerts()
    return {"alerts": [alert.__dict__ for alert in alerts]}

# Churn Prediction Endpoints
@router.get("/churn/predict/{customer_id}")
async def predict_churn(customer_id: str):
    """Predict churn probability for a customer"""
    from main import services
    probability = await services["churn_predictor"].predict_churn_probability(customer_id)
    return {"customer_id": customer_id, "churn_probability": probability}

@router.get("/churn/at-risk")
async def get_at_risk_customers(threshold: float = 0.7):
    """Get customers at risk of churning"""
    from main import services
    return await services["churn_predictor"].identify_at_risk_customers(threshold)

@router.post("/churn/retention-campaign/{customer_id}")
async def execute_retention_campaign(customer_id: str, campaign_type: str):
    """Execute retention campaign for a customer"""
    from main import services
    return await services["churn_predictor"].execute_retention_campaign(customer_id, campaign_type)

# Upsell Detection Endpoints
@router.get("/upsell/opportunities")
async def get_upsell_opportunities(customer_id: Optional[str] = None):
    """Get upsell opportunities"""
    from main import services
    return await services["upsell_detector"].identify_upsell_opportunities(customer_id)

@router.post("/upsell/campaign/{customer_id}")
async def execute_upsell_campaign(customer_id: str, campaign_type: str):
    """Execute upsell campaign for a customer"""
    from main import services
    return await services["upsell_detector"].execute_upsell_campaign(customer_id, campaign_type)

@router.post("/upsell/conversion/{customer_id}")
async def track_upsell_conversion(customer_id: str, from_plan: str, to_plan: str):
    """Track successful upsell conversion"""
    from main import services
    return await services["upsell_detector"].track_upsell_conversion(customer_id, from_plan, to_plan)

# A/B Testing Endpoints
@router.post("/ab-test/create")
async def create_ab_test(test_config: ABTestConfig):
    """Create a new A/B test"""
    from main import services
    return await services["ab_testing"].create_pricing_test(
        test_config.test_name,
        test_config.control_price,
        test_config.variant_price,
        test_config.target_metric,
        test_config.duration_days,
        test_config.traffic_split
    )

@router.post("/ab-test/{test_id}/start")
async def start_ab_test(test_id: str):
    """Start an A/B test"""
    from main import services
    return await services["ab_testing"].start_test(test_id)

@router.get("/ab-test/{test_id}/assign/{user_id}")
async def assign_test_variant(test_id: str, user_id: str):
    """Assign user to test variant"""
    from main import services
    return await services["ab_testing"].assign_variant(test_id, user_id)

@router.post("/ab-test/{test_id}/impression")
async def record_impression(test_id: str, variant: str, user_id: str):
    """Record test impression"""
    from main import services
    return await services["ab_testing"].record_impression(test_id, variant, user_id)

@router.post("/ab-test/{test_id}/conversion")
async def record_conversion(test_id: str, variant: str, user_id: str, revenue: float = 0.0):
    """Record test conversion"""
    from main import services
    return await services["ab_testing"].record_conversion(test_id, variant, user_id, revenue)

@router.get("/ab-test/{test_id}/results")
async def get_test_results(test_id: str):
    """Get A/B test results"""
    from main import services
    return await services["ab_testing"].get_test_results(test_id)

@router.post("/ab-test/{test_id}/stop")
async def stop_ab_test(test_id: str, reason: str = "Manual stop"):
    """Stop A/B test"""
    from main import services
    return await services["ab_testing"].stop_test(test_id, reason)

# LTV Calculation Endpoints
@router.get("/ltv/{customer_id}")
async def calculate_ltv(customer_id: str, method: str = "predictive"):
    """Calculate customer lifetime value"""
    from main import services
    return await services["ltv_calculator"].calculate_customer_ltv(customer_id, method)

@router.get("/ltv/cohort/{cohort_id}")
async def calculate_cohort_ltv(cohort_id: str):
    """Calculate LTV for customer cohort"""
    from main import services
    return await services["ltv_calculator"].calculate_cohort_ltv(cohort_id)

@router.get("/ltv/high-value")
async def get_high_value_customers(threshold_percentile: int = 80):
    """Get high-value customers"""
    from main import services
    return await services["ltv_calculator"].identify_high_value_customers(threshold_percentile)

@router.get("/ltv/{customer_id}/recommendations")
async def get_ltv_recommendations(customer_id: str):
    """Get LTV optimization recommendations"""
    from main import services
    return await services["ltv_calculator"].generate_ltv_optimization_recommendations(customer_id)

# Acquisition Tracking Endpoints
@router.post("/acquisition/track")
async def track_acquisition_event(
    customer_id: str, 
    channel: str, 
    campaign: str, 
    cost: float, 
    event_type: str = "impression"
):
    """Track acquisition event"""
    from main import services
    return await services["acquisition_tracker"].track_acquisition_event(
        customer_id, channel, campaign, cost, event_type
    )

@router.get("/acquisition/cac/{channel}")
async def calculate_channel_cac(channel: str, time_period_days: int = 30):
    """Calculate Customer Acquisition Cost for channel"""
    from main import services
    return await services["acquisition_tracker"].calculate_channel_cac(channel, time_period_days)

@router.get("/acquisition/attribution/{customer_id}")
async def analyze_attribution(customer_id: str, model: str = "linear", conversion_value: Optional[float] = None):
    """Analyze customer acquisition attribution"""
    from main import services
    return await services["acquisition_tracker"].analyze_attribution(customer_id, model, conversion_value)

@router.get("/acquisition/optimize")
async def optimize_channel_mix():
    """Optimize marketing channel mix"""
    from main import services
    return await services["acquisition_tracker"].optimize_channel_mix()

# Referral Program Endpoints
@router.post("/referral/program")
async def create_referral_program(program_config: ReferralProgramConfig):
    """Create referral program"""
    from main import services
    return await services["referral_optimizer"].create_referral_program(program_config.dict())

@router.post("/referral/link/{user_id}")
async def generate_referral_link(user_id: str, program_id: str):
    """Generate referral link"""
    from main import services
    return await services["referral_optimizer"].generate_referral_link(user_id, program_id)

@router.post("/referral/click/{referral_code}")
async def track_referral_click(referral_code: str):
    """Track referral click"""
    from main import services
    return await services["referral_optimizer"].track_referral_click(referral_code)

@router.post("/referral/conversion/{referral_code}")
async def process_referral_conversion(referral_code: str, referee_id: str, purchase_amount: float):
    """Process referral conversion"""
    from main import services
    return await services["referral_optimizer"].process_referral_conversion(referral_code, referee_id, purchase_amount)

@router.get("/referral/metrics/{program_id}")
async def get_program_metrics(program_id: str, time_period_days: int = 30):
    """Get referral program metrics"""
    from main import services
    return await services["referral_optimizer"].calculate_program_metrics(program_id, time_period_days)

# Conversion Funnel Endpoints
@router.post("/funnel/define")
async def define_funnel(funnel_name: str, stages: List[str], stage_configs: Dict):
    """Define custom conversion funnel"""
    from main import services
    return await services["funnel_analyzer"].define_custom_funnel(funnel_name, stages, stage_configs)

@router.post("/funnel/track/{user_id}")
async def track_user_journey(user_id: str, stage: str, metadata: Optional[Dict] = None):
    """Track user journey through funnel"""
    from main import services
    return await services["funnel_analyzer"].track_user_journey(user_id, stage, metadata)

@router.get("/funnel/analyze")
async def analyze_funnel(funnel_name: str = "default", time_period_days: int = 30, cohort_analysis: bool = True):
    """Analyze funnel performance"""
    from main import services
    return await services["funnel_analyzer"].analyze_funnel_performance(funnel_name, time_period_days, cohort_analysis)

@router.get("/funnel/dropoffs")
async def get_dropoff_points(funnel_name: str = "default"):
    """Get funnel drop-off points"""
    from main import services
    return await services["funnel_analyzer"].identify_drop_off_points(funnel_name)

# Payment Recovery Endpoints
@router.post("/payment/failure")
async def record_payment_failure(
    customer_id: str,
    amount: float,
    failure_reason: str,
    payment_method_id: str,
    subscription_id: Optional[str] = None,
    invoice_id: Optional[str] = None
):
    """Record payment failure"""
    from main import services
    return await services["payment_recovery"].record_payment_failure(
        customer_id, amount, failure_reason, payment_method_id, subscription_id, invoice_id
    )

@router.post("/payment/retry/{failure_id}")
async def retry_payment(failure_id: str):
    """Retry failed payment"""
    from main import services
    return await services["payment_recovery"].retry_failed_payment(failure_id)

@router.get("/payment/recovery/analytics")
async def get_recovery_analytics(time_period_days: int = 30):
    """Get payment recovery analytics"""
    from main import services
    return await services["payment_recovery"].get_recovery_analytics(time_period_days)

# Subscription Optimization Endpoints
@router.post("/subscription/plan")
async def create_subscription_plan(plan_config: Dict):
    """Create subscription plan"""
    from main import services
    return await services["subscription_optimizer"].create_subscription_plan(plan_config)

@router.get("/subscription/optimize/pricing/{plan_id}")
async def optimize_pricing(plan_id: str):
    """Optimize subscription pricing"""
    from main import services
    return await services["subscription_optimizer"].optimize_pricing_strategy(plan_id)

@router.get("/subscription/optimize/billing-cycles")
async def optimize_billing_cycles():
    """Optimize billing cycles"""
    from main import services
    return await services["subscription_optimizer"].optimize_billing_cycles()

@router.get("/subscription/optimize/trials")
async def optimize_trials():
    """Optimize trial periods"""
    from main import services
    return await services["subscription_optimizer"].optimize_trial_periods()

@router.get("/subscription/metrics")
async def get_subscription_metrics(time_period_days: int = 30):
    """Get subscription metrics"""
    from main import services
    return await services["subscription_optimizer"].calculate_subscription_metrics(time_period_days)