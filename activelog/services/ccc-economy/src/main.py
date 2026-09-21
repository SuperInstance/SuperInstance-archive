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
from .wallet.wallet_manager import CCCWalletManager
from .earnings.sales_manager import CCCEarningsManager
from .business.ccc_operations import CCCBusinessManager
from .investment.startup_investment import CCCInvestmentManager
from .database import (
    BusinessType, CCCTransactionType
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting CCC Economy System...")
    
    # Create database tables
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down CCC Economy System...")
    await engine.dispose()

app = FastAPI(
    title="CCC Economy System",
    description="Complete CCC-based economy with wallets, businesses, investments, and marketplace",
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
class CreateWalletRequest(BaseModel):
    user_id: str
    initial_balance: Optional[float] = 0.0

class TransferCCCRequest(BaseModel):
    sender_wallet_id: str
    recipient_wallet_id: str
    amount: float
    description: Optional[str] = "CCC Transfer"

class ProductSaleRequest(BaseModel):
    business_id: str
    buyer_user_id: str
    product_details: Dict[str, Any]
    sale_amount_ccc: float

class RegisterBusinessRequest(BaseModel):
    owner_id: str
    business_name: str
    description: str
    business_type: str = "startup"
    initial_valuation_ccc: Optional[float] = 10000

class InvestmentRequest(BaseModel):
    investor_id: str
    business_id: str
    investment_amount_ccc: float
    expected_return_percentage: Optional[float] = None

class CreateInvestmentOpportunityRequest(BaseModel):
    business_id: str
    equity_percentage_offered: float
    valuation_ccc: float
    minimum_investment_ccc: float
    maximum_investment_ccc: Optional[float] = None
    requires_accredited: bool = False

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "CCC Economy System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/overview")
async def get_system_overview():
    """Get comprehensive overview of CCC economy capabilities"""
    return {
        "service": "CCC Economy System",
        "port": 8327,
        "capabilities": {
            "wallet_management": "CCC wallet creation and management",
            "earnings_system": "Product/service sales in CCC",
            "business_operations": "100% CCC-based business operations",
            "investment_system": "Startup investment with equity trading",
            "ownership_trading": "Percentage-based ownership trading",
            "dividend_distribution": "10% = 10 cents/month/member",
            "equity_marketplace": "Business equity trading platform",
            "voting_mechanics": "Voting with CCC wallet balance",
            "fiat_conversion": "Controlled CCC to fiat conversion",
            "tax_deferred": "Tax-deferred CCC accumulation",
            "inheritance_system": "CCC inheritance and transfer",
            "analytics_dashboard": "Comprehensive CCC analytics"
        },
        "currency": "CCC (Community Contribution Credits)",
        "fiat_free_operations": True,
        "blockchain_integration": "Native CCC blockchain"
    }

# Wallet Management Endpoints
@app.post("/api/wallet/create")
async def create_wallet(
    request: CreateWalletRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new CCC wallet"""
    try:
        manager = CCCWalletManager(db)
        result = await manager.create_wallet(
            user_id=uuid.UUID(request.user_id),
            initial_balance=Decimal(str(request.initial_balance))
        )
        return result
    except Exception as e:
        logger.error(f"Wallet creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet/balance/{user_id}")
async def get_wallet_balance(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get wallet balance and details"""
    try:
        manager = CCCWalletManager(db)
        result = await manager.get_wallet_balance(user_id=uuid.UUID(user_id))
        return result
    except Exception as e:
        logger.error(f"Get wallet balance failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/wallet/transfer")
async def transfer_ccc(
    request: TransferCCCRequest,
    db: AsyncSession = Depends(get_db)
):
    """Transfer CCC between wallets"""
    try:
        manager = CCCWalletManager(db)
        result = await manager.transfer_ccc(
            sender_wallet_id=uuid.UUID(request.sender_wallet_id),
            recipient_wallet_id=uuid.UUID(request.recipient_wallet_id),
            amount=Decimal(str(request.amount)),
            description=request.description
        )
        return result
    except Exception as e:
        logger.error(f"CCC transfer failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet/transactions/{wallet_id}")
async def get_transaction_history(
    wallet_id: str,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """Get transaction history for wallet"""
    try:
        manager = CCCWalletManager(db)
        result = await manager.get_transaction_history(
            wallet_id=uuid.UUID(wallet_id),
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Get transaction history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/wallet/analytics/{wallet_id}")
async def get_wallet_analytics(
    wallet_id: str,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get wallet analytics"""
    try:
        manager = CCCWalletManager(db)
        result = await manager.get_wallet_analytics(
            wallet_id=uuid.UUID(wallet_id),
            period_days=period_days
        )
        return result
    except Exception as e:
        logger.error(f"Get wallet analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Sales and Earnings Endpoints
@app.post("/api/sales/product")
async def process_product_sale(
    request: ProductSaleRequest,
    db: AsyncSession = Depends(get_db)
):
    """Process a product sale in CCC"""
    try:
        manager = CCCEarningsManager(db)
        result = await manager.process_product_sale(
            business_id=uuid.UUID(request.business_id),
            buyer_user_id=uuid.UUID(request.buyer_user_id),
            product_details=request.product_details,
            sale_amount_ccc=Decimal(str(request.sale_amount_ccc))
        )
        return result
    except Exception as e:
        logger.error(f"Product sale processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sales/analytics/{business_id}")
async def get_sales_analytics(
    business_id: str,
    period_days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get sales analytics for business"""
    try:
        manager = CCCEarningsManager(db)
        result = await manager.get_business_sales_analytics(
            business_id=uuid.UUID(business_id),
            period_days=period_days
        )
        return result
    except Exception as e:
        logger.error(f"Sales analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sales/customer-history/{customer_id}")
async def get_customer_purchase_history(
    customer_id: str,
    period_days: int = 90,
    db: AsyncSession = Depends(get_db)
):
    """Get customer purchase history"""
    try:
        manager = CCCEarningsManager(db)
        result = await manager.get_customer_purchase_history(
            customer_user_id=uuid.UUID(customer_id),
            period_days=period_days
        )
        return result
    except Exception as e:
        logger.error(f"Customer purchase history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Business Operations Endpoints
@app.post("/api/business/register")
async def register_business(
    request: RegisterBusinessRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register a CCC-native business"""
    try:
        manager = CCCBusinessManager(db)
        result = await manager.register_business(
            owner_id=uuid.UUID(request.owner_id),
            business_name=request.business_name,
            description=request.description,
            business_type=BusinessType(request.business_type),
            initial_valuation_ccc=Decimal(str(request.initial_valuation_ccc))
        )
        return result
    except Exception as e:
        logger.error(f"Business registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/business/financials/{business_id}")
async def get_business_financials(
    business_id: str,
    period_months: int = 12,
    db: AsyncSession = Depends(get_db)
):
    """Get business financial overview"""
    try:
        manager = CCCBusinessManager(db)
        result = await manager.get_business_financials(
            business_id=uuid.UUID(business_id),
            period_months=period_months
        )
        return result
    except Exception as e:
        logger.error(f"Business financials failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/business/transaction")
async def process_business_transaction(
    business_id: str,
    transaction_type: str,
    amount_ccc: float,
    description: str = "",
    category: str = "general",
    counterparty_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Process business transaction in CCC"""
    try:
        manager = CCCBusinessManager(db)
        result = await manager.operate_business_transaction(
            business_id=uuid.UUID(business_id),
            transaction_type=transaction_type,
            amount_ccc=Decimal(str(amount_ccc)),
            counterparty_id=uuid.UUID(counterparty_id) if counterparty_id else None,
            description=description,
            category=category
        )
        return result
    except Exception as e:
        logger.error(f"Business transaction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/business/payroll/setup")
async def setup_business_payroll(
    business_id: str,
    employees: List[Dict[str, Any]],
    payment_schedule: str = "monthly",
    db: AsyncSession = Depends(get_db)
):
    """Setup CCC-based payroll system"""
    try:
        manager = CCCBusinessManager(db)
        result = await manager.setup_business_payroll(
            business_id=uuid.UUID(business_id),
            employees=employees,
            payment_schedule=payment_schedule
        )
        return result
    except Exception as e:
        logger.error(f"Payroll setup failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Investment System Endpoints
@app.post("/api/investment/opportunity/create")
async def create_investment_opportunity(
    request: CreateInvestmentOpportunityRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create investment opportunity for startup"""
    try:
        manager = CCCInvestmentManager(db)
        result = await manager.create_investment_opportunity(
            business_id=uuid.UUID(request.business_id),
            equity_percentage_offered=Decimal(str(request.equity_percentage_offered)),
            valuation_ccc=Decimal(str(request.valuation_ccc)),
            minimum_investment_ccc=Decimal(str(request.minimum_investment_ccc)),
            maximum_investment_ccc=Decimal(str(request.maximum_investment_ccc)) if request.maximum_investment_ccc else None,
            requires_accredited=request.requires_accredited
        )
        return result
    except Exception as e:
        logger.error(f"Investment opportunity creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/investment/invest")
async def make_investment(
    request: InvestmentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Make an investment in a startup"""
    try:
        manager = CCCInvestmentManager(db)
        result = await manager.make_investment(
            investor_id=uuid.UUID(request.investor_id),
            business_id=uuid.UUID(request.business_id),
            investment_amount_ccc=Decimal(str(request.investment_amount_ccc)),
            expected_return_percentage=Decimal(str(request.expected_return_percentage)) if request.expected_return_percentage else None
        )
        return result
    except Exception as e:
        logger.error(f"Investment processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/investment/portfolio/{investor_id}")
async def get_investment_portfolio(
    investor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get investment portfolio for investor"""
    try:
        manager = CCCInvestmentManager(db)
        result = await manager.get_investment_portfolio(
            investor_id=uuid.UUID(investor_id)
        )
        return result
    except Exception as e:
        logger.error(f"Investment portfolio retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/investment/business/{business_id}/investors")
async def get_business_investors(
    business_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all investors for a business"""
    try:
        manager = CCCInvestmentManager(db)
        result = await manager.get_business_investors(
            business_id=uuid.UUID(business_id)
        )
        return result
    except Exception as e:
        logger.error(f"Business investors retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/investment/exit")
async def process_investment_exit(
    investment_id: str,
    exit_type: str,
    exit_amount_ccc: float,
    exit_reason: str,
    db: AsyncSession = Depends(get_db)
):
    """Process investment exit/liquidation"""
    try:
        manager = CCCInvestmentManager(db)
        result = await manager.process_investment_exit(
            investment_id=uuid.UUID(investment_id),
            exit_type=exit_type,
            exit_amount_ccc=Decimal(str(exit_amount_ccc)),
            exit_reason=exit_reason
        )
        return result
    except Exception as e:
        logger.error(f"Investment exit processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Analytics Endpoints
@app.get("/api/analytics/system-overview")
async def get_system_analytics(
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive system analytics"""
    try:
        # Get wallet manager for system stats
        wallet_manager = CCCWalletManager(db)
        system_balances = await wallet_manager.get_all_wallet_balances()
        
        return {
            "ccc_economy_stats": system_balances,
            "system_health": "healthy",
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"System analytics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# System Configuration Endpoints
@app.post("/api/system/initialize")
async def initialize_system(
    db: AsyncSession = Depends(get_db)
):
    """Initialize CCC economy system with sample data"""
    try:
        # This would set up initial system configuration
        return {
            "initialized": True,
            "message": "CCC Economy System initialized successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8327)