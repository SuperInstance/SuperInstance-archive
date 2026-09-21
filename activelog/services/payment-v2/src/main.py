from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import os
from pathlib import Path

from .database import engine, Base, get_db
from .credits.routes import router as credits_router
from .affiliates.routes import router as affiliates_router
from .billing.routes import router as billing_router
from .groups.routes import router as groups_router
from .autopurchase.routes import router as autopurchase_router
from .currency.routes import router as currency_router
from .tax.routes import router as tax_router
from .invoicing.routes import router as invoicing_router
from .subscriptions.routes import router as subscriptions_router
from .escrow.routes import router as escrow_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="ActiveLog Payment System v2",
    description="Enhanced payment system with compute credits, affiliate management, bulk billing, and more",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080", "http://localhost:8325"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include routers
app.include_router(credits_router, prefix="/api/credits", tags=["credits"])
app.include_router(affiliates_router, prefix="/api/affiliates", tags=["affiliates"])
app.include_router(billing_router, prefix="/api/billing", tags=["billing"])
app.include_router(groups_router, prefix="/api/groups", tags=["credit-pooling"])
app.include_router(autopurchase_router, prefix="/api/autopurchase", tags=["auto-purchase"])
app.include_router(currency_router, prefix="/api/currency", tags=["currency"])
app.include_router(tax_router, prefix="/api/tax", tags=["tax"])
app.include_router(invoicing_router, prefix="/api/invoicing", tags=["invoicing"])
app.include_router(subscriptions_router, prefix="/api/subscriptions", tags=["subscriptions"])
app.include_router(escrow_router, prefix="/api/escrow", tags=["escrow"])

@app.get("/")
async def root():
    return {
        "message": "ActiveLog Payment System v2",
        "version": "2.0.0",
        "status": "running",
        "port": 8325,
        "features": [
            "Compute Credit Economics",
            "Affiliate Commission Structure", 
            "Bulk Organization Billing",
            "Credit Pooling for Groups",
            "Automatic Credit Purchasing",
            "International Currency Support",
            "Tax Calculation per Region",
            "Invoice Generation",
            "Subscription with Credits",
            "Marketplace Escrow"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-v2", "port": 8325}

@app.get("/api/overview")
async def system_overview():
    """Get system overview and capabilities"""
    return {
        "compute_credits": {
            "description": "Advanced credit economics with usage-based pricing",
            "endpoints": [
                "GET /api/credits/balance/{user_id}",
                "POST /api/credits/consume",
                "POST /api/credits/purchase",
                "GET /api/credits/analytics"
            ],
            "features": [
                "Multi-tier pricing (CPU, GPU, Storage, Bandwidth)",
                "Credit reservation for long-running jobs",
                "Auto-recharge capabilities",
                "Usage analytics and forecasting"
            ]
        },
        "affiliate_system": {
            "description": "5-tier affiliate program with progressive bonuses",
            "endpoints": [
                "POST /api/affiliates/program",
                "POST /api/affiliates/referral", 
                "GET /api/affiliates/stats/{affiliate_id}",
                "GET /api/affiliates/leaderboard"
            ],
            "tiers": ["Bronze", "Silver", "Gold", "Platinum", "Diamond"],
            "commission_rates": ["10%", "12%", "15%", "20%", "25%"]
        },
        "bulk_billing": {
            "description": "Enterprise-grade organization billing with volume discounts",
            "endpoints": [
                "POST /api/billing/organization/setup",
                "POST /api/billing/process",
                "GET /api/billing/usage-breakdown/{org_id}",
                "GET /api/billing/forecasts/{org_id}"
            ],
            "features": [
                "Volume-based discounts (up to 20%)",
                "Usage forecasting",
                "Flexible credit distribution",
                "Automated invoice generation"
            ]
        },
        "credit_pooling": {
            "description": "Shared credit pools for teams and organizations",
            "features": ["Team credit sharing", "Budget allocation", "Usage tracking"]
        },
        "international_support": {
            "description": "Multi-currency support with real-time exchange rates",
            "supported_currencies": ["USD", "EUR", "GBP", "JPY", "CAD", "AUD"],
            "features": ["Real-time exchange rates", "Currency hedging", "Regional pricing"]
        },
        "tax_engine": {
            "description": "Automated tax calculation for global compliance",
            "features": ["VAT/GST calculation", "Regional tax rates", "Tax reporting"]
        },
        "invoicing": {
            "description": "Professional invoice generation with PDF export",
            "features": ["Automated billing", "Multiple templates", "Payment tracking"]
        },
        "subscriptions": {
            "description": "Subscription billing integrated with credit systems",
            "features": ["Flexible billing cycles", "Credit allocation", "Usage overages"]
        },
        "marketplace_escrow": {
            "description": "Secure escrow system for marketplace transactions",
            "features": ["Dispute resolution", "Automated releases", "Multi-party transactions"]
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8325,
        reload=True,
        access_log=True
    )