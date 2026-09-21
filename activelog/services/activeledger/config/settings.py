"""
ActiveLedger Configuration Settings
"""

import os
from typing import Optional, List
from pydantic import BaseSettings, Field
from decimal import Decimal

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = Field(default="postgresql://activelog_admin:password@localhost:5432/activeledger")
    echo: bool = Field(default=False)
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=30)
    
    class Config:
        env_prefix = "DATABASE_"

class RedisSettings(BaseSettings):
    """Redis configuration"""
    url: str = Field(default="redis://localhost:6379/2")
    max_connections: int = Field(default=100)
    
    class Config:
        env_prefix = "REDIS_"

class ComputeCreditSettings(BaseSettings):
    """Compute Credit (CC) system configuration"""
    base_currency: str = Field(default="USD")
    cc_to_usd_rate: Decimal = Field(default=Decimal("0.01"))  # 1 CC = $0.01 USD
    minimum_balance: Decimal = Field(default=Decimal("1.00"))
    maximum_balance: Decimal = Field(default=Decimal("10000.00"))
    free_tier_credits: Decimal = Field(default=Decimal("500"))  # 500 CC free credits
    affiliate_commission_rate: Decimal = Field(default=Decimal("0.10"))  # 10% commission
    
    class Config:
        env_prefix = "CC_"

class PaymentGatewaySettings(BaseSettings):
    """Payment gateway configuration"""
    # PayPal
    paypal_client_id: str = Field(default="")
    paypal_client_secret: str = Field(default="")
    paypal_environment: str = Field(default="sandbox")  # sandbox or live
    
    # Stripe (for additional card processing)
    stripe_secret_key: str = Field(default="")
    stripe_publishable_key: str = Field(default="")
    
    # Google Pay
    google_pay_merchant_id: str = Field(default="")
    google_pay_gateway_id: str = Field(default="")
    
    # Processing fees (passed to users via cost-plus pricing)
    paypal_fee_rate: Decimal = Field(default=Decimal("0.029"))  # 2.9%
    paypal_fee_fixed: Decimal = Field(default=Decimal("0.30"))  # $0.30
    stripe_fee_rate: Decimal = Field(default=Decimal("0.029"))  # 2.9%
    stripe_fee_fixed: Decimal = Field(default=Decimal("0.30"))  # $0.30
    
    class Config:
        env_prefix = "PAYMENT_"

class SubscriptionSettings(BaseSettings):
    """Subscription tier configuration"""
    free_tier_storage_gb: int = Field(default=5)
    free_tier_compute_hours: int = Field(default=10)
    free_tier_ad_revenue_share: Decimal = Field(default=Decimal("0.90"))  # 90% to user
    
    paid_tier_storage_gb: int = Field(default=15)
    paid_tier_compute_hours: int = Field(default=100)
    paid_tier_monthly_cost_usd: Decimal = Field(default=Decimal("9.99"))
    
    pro_tier_storage_gb: int = Field(default=100)
    pro_tier_compute_hours: int = Field(default=500)
    pro_tier_monthly_cost_usd: Decimal = Field(default=Decimal("29.99"))
    
    enterprise_tier_storage_gb: int = Field(default=1000)
    enterprise_tier_compute_hours: int = Field(default=2000)
    enterprise_tier_monthly_cost_usd: Decimal = Field(default=Decimal("99.99"))
    
    class Config:
        env_prefix = "SUBSCRIPTION_"

class ComputeRentalSettings(BaseSettings):
    """Compute rental pricing configuration"""
    # EC2 instance types and daily rates (in CC)
    ec2_t3_micro_daily_cc: Decimal = Field(default=Decimal("50"))    # ~$0.50/day
    ec2_t3_small_daily_cc: Decimal = Field(default=Decimal("100"))   # ~$1.00/day
    ec2_t3_medium_daily_cc: Decimal = Field(default=Decimal("200"))  # ~$2.00/day
    ec2_t3_large_daily_cc: Decimal = Field(default=Decimal("400"))   # ~$4.00/day
    ec2_m5_large_daily_cc: Decimal = Field(default=Decimal("500"))   # ~$5.00/day
    ec2_c5_large_daily_cc: Decimal = Field(default=Decimal("450"))   # ~$4.50/day
    
    # Monthly discounts
    monthly_discount_rate: Decimal = Field(default=Decimal("0.20"))  # 20% discount for monthly
    
    # Minimum rental period (hours)
    minimum_rental_hours: int = Field(default=1)
    
    class Config:
        env_prefix = "COMPUTE_"

class MarketplaceSettings(BaseSettings):
    """Marketplace configuration"""
    transaction_fee_rate: Decimal = Field(default=Decimal("0.05"))  # 5% marketplace fee
    minimum_listing_price_cc: Decimal = Field(default=Decimal("10"))  # 10 CC minimum
    maximum_listing_price_cc: Decimal = Field(default=Decimal("100000"))  # 100,000 CC max
    
    # Escrow settings
    escrow_timeout_days: int = Field(default=7)
    dispute_resolution_days: int = Field(default=14)
    
    # Reputation system
    min_rating: int = Field(default=1)
    max_rating: int = Field(default=5)
    reputation_weight_transactions: Decimal = Field(default=Decimal("0.7"))
    reputation_weight_reviews: Decimal = Field(default=Decimal("0.3"))
    
    class Config:
        env_prefix = "MARKETPLACE_"

class AdRevenueSettings(BaseSettings):
    """Ad revenue configuration"""
    user_share_percentage: float = Field(default=90.0)  # Users get 90% of ad revenue
    platform_share_percentage: float = Field(default=10.0)  # Platform keeps 10%
    min_payout_threshold_cc: Decimal = Field(default=Decimal("0.01"))  # Minimum 0.01 CC to payout
    supported_ad_networks: List[str] = Field(default=["google_adsense", "media_net", "infolinks"])
    max_ads_per_page: int = Field(default=3)
    enable_ad_blocking_detection: bool = Field(default=True)
    
    # Revenue per impression/click (in CC)
    revenue_per_impression_cc: Decimal = Field(default=Decimal("0.001"))  # 0.001 CC per impression
    revenue_per_click_cc: Decimal = Field(default=Decimal("0.01"))  # 0.01 CC per click
    
    class Config:
        env_prefix = "AD_"

class CurrencyExchangeSettings(BaseSettings):
    """Currency exchange configuration"""
    supported_currencies: List[str] = Field(default=["USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY", "INR"])
    exchange_rate_api_key: str = Field(default="")
    exchange_rate_cache_ttl: int = Field(default=3600)  # 1 hour cache
    exchange_fee_rate: Decimal = Field(default=Decimal("0.01"))  # 1% exchange fee
    
    class Config:
        env_prefix = "EXCHANGE_"

class SecuritySettings(BaseSettings):
    """Security configuration"""
    secret_key: str = Field(default="your-secret-key-change-this")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    password_hash_algorithm: str = Field(default="bcrypt")
    
    # Rate limiting
    api_rate_limit_per_minute: int = Field(default=60)
    payment_rate_limit_per_hour: int = Field(default=10)
    
    class Config:
        env_prefix = "SECURITY_"

class MonitoringSettings(BaseSettings):
    """Monitoring and analytics configuration"""
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=8001)
    log_level: str = Field(default="INFO")
    
    # Financial monitoring thresholds
    low_balance_threshold_cc: Decimal = Field(default=Decimal("50"))
    high_transaction_threshold_cc: Decimal = Field(default=Decimal("1000"))
    
    class Config:
        env_prefix = "MONITORING_"

class Settings(BaseSettings):
    """Main application settings"""
    app_name: str = Field(default="ActiveLedger")
    app_version: str = Field(default="1.0.0")
    debug: bool = Field(default=False)
    
    # Component settings
    database: DatabaseSettings = DatabaseSettings()
    redis: RedisSettings = RedisSettings()
    compute_credits: ComputeCreditSettings = ComputeCreditSettings()
    payments: PaymentGatewaySettings = PaymentGatewaySettings()
    subscriptions: SubscriptionSettings = SubscriptionSettings()
    compute_rental: ComputeRentalSettings = ComputeRentalSettings()
    marketplace: MarketplaceSettings = MarketplaceSettings()
    ad_revenue: AdRevenueSettings = AdRevenueSettings()
    currency_exchange: CurrencyExchangeSettings = CurrencyExchangeSettings()
    security: SecuritySettings = SecuritySettings()
    monitoring: MonitoringSettings = MonitoringSettings()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()

# Pricing calculator constants
PRICING_COMPONENTS = {
    "storage": {
        "cost_per_gb_per_month_cc": Decimal("5"),  # 5 CC per GB per month
        "free_tier_gb": settings.subscriptions.free_tier_storage_gb
    },
    "compute": {
        "cost_per_hour_cc": Decimal("10"),  # 10 CC per compute hour
        "free_tier_hours": settings.subscriptions.free_tier_compute_hours
    },
    "bandwidth": {
        "cost_per_gb_cc": Decimal("1"),  # 1 CC per GB transfer
        "free_tier_gb": 100  # 100 GB free per month
    },
    "api_calls": {
        "cost_per_1000_calls_cc": Decimal("1"),  # 1 CC per 1000 API calls
        "free_tier_calls": 10000  # 10,000 free calls per month
    }
}

# Transparent cost-plus pricing
COST_PLUS_MARKUP = Decimal("0.15")  # 15% markup over actual costs

# Subscription tier definitions
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free Tier",
        "storage_gb": settings.subscriptions.free_tier_storage_gb,
        "compute_hours": settings.subscriptions.free_tier_compute_hours,
        "monthly_cost_cc": Decimal("0"),
        "features": ["Ad revenue sharing", "Basic support", "Community access"],
        "limits": {
            "api_calls_per_month": 10000,
            "bandwidth_gb_per_month": 100,
            "max_file_size_mb": 100
        }
    },
    "paid": {
        "name": "Paid Tier",
        "storage_gb": settings.subscriptions.paid_tier_storage_gb,
        "compute_hours": settings.subscriptions.paid_tier_compute_hours,
        "monthly_cost_cc": settings.subscriptions.paid_tier_monthly_cost_usd * 100,  # Convert to CC
        "features": ["No ads", "Priority support", "Advanced analytics"],
        "limits": {
            "api_calls_per_month": 100000,
            "bandwidth_gb_per_month": 1000,
            "max_file_size_mb": 1000
        }
    },
    "pro": {
        "name": "Pro Tier",
        "storage_gb": settings.subscriptions.pro_tier_storage_gb,
        "compute_hours": settings.subscriptions.pro_tier_compute_hours,
        "monthly_cost_cc": settings.subscriptions.pro_tier_monthly_cost_usd * 100,
        "features": ["Custom branding", "API access", "Advanced integrations"],
        "limits": {
            "api_calls_per_month": 1000000,
            "bandwidth_gb_per_month": 10000,
            "max_file_size_mb": 10000
        }
    },
    "enterprise": {
        "name": "Enterprise",
        "storage_gb": settings.subscriptions.enterprise_tier_storage_gb,
        "compute_hours": settings.subscriptions.enterprise_tier_compute_hours,
        "monthly_cost_cc": settings.subscriptions.enterprise_tier_monthly_cost_usd * 100,
        "features": ["Custom pricing", "Dedicated support", "SLA guarantees"],
        "limits": {
            "api_calls_per_month": -1,  # Unlimited
            "bandwidth_gb_per_month": -1,  # Unlimited
            "max_file_size_mb": -1  # Unlimited
        }
    }
}