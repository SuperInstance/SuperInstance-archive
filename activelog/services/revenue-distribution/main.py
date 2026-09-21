#!/usr/bin/env python3
"""
Revenue Distribution Platform
Comprehensive revenue management, distribution, and financial operations system
Port: 8334

Features:
- Tiered fee system (1% first $100k/year, 0.1% after)
- Automatic payment splitting
- Tax reporting preparation
- Multi-currency support
- Escrow for transactions
- Dispute resolution system
- Automated invoicing
- Revenue forecasting
- Profit sharing calculations
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
import json
import asyncio
import logging
import os
import uuid
from datetime import datetime, timedelta
import sqlite3
import aiofiles
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum

# Import all the subsystem modules
from fee_system import fee_calculator
from payment_splitting import payment_splitter
from tax_reporting import tax_reporter
from currency_system import currency_manager
from escrow_system import escrow_manager
from dispute_resolution import dispute_resolver
from invoicing_system import invoice_generator
from revenue_forecasting import revenue_forecaster
from profit_sharing import profit_share_calculator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Revenue Distribution Platform",
    description="Comprehensive revenue management, distribution, and financial operations system",
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

# Revenue Distribution Data Models
class FeeStructure(str, Enum):
    TIERED = "tiered"
    FLAT = "flat"
    PERCENTAGE = "percentage"
    CUSTOM = "custom"

class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DISPUTED = "disputed"
    REFUNDED = "refunded"

class RevenueTransaction(BaseModel):
    id: str
    payer_id: str
    recipient_id: str
    
    # Transaction details
    gross_amount: Decimal
    currency: str = "USD"
    description: str = ""
    
    # Fee calculation
    platform_fee: Decimal = Decimal('0')
    net_amount: Decimal = Decimal('0')
    fee_rate: Decimal = Decimal('0')
    
    # Status and timing
    status: TransactionStatus = TransactionStatus.PENDING
    created_at: datetime
    processed_at: Optional[datetime] = None
    
    # Metadata
    reference_id: Optional[str] = None
    payment_method: str = "bank_transfer"
    tax_applicable: bool = True
    
    # Geographic and regulatory
    payer_country: str = "US"
    recipient_country: str = "US"
    tax_jurisdiction: str = "US"

# Database initialization
def init_database():
    """Initialize SQLite database for persistent storage"""
    os.makedirs("/home/activeloguser/activelog/services/revenue-distribution/data", exist_ok=True)
    conn = sqlite3.connect("/home/activeloguser/activelog/services/revenue-distribution/data/revenue_distribution.db")
    cursor = conn.cursor()
    
    # Transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS revenue_transactions (
            id TEXT PRIMARY KEY,
            payer_id TEXT NOT NULL,
            recipient_id TEXT NOT NULL,
            gross_amount DECIMAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            platform_fee DECIMAL NOT NULL,
            net_amount DECIMAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Fee calculations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_calculations (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            year INTEGER NOT NULL,
            total_revenue DECIMAL NOT NULL,
            fees_paid DECIMAL NOT NULL,
            fee_tier TEXT NOT NULL,
            calculation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Payment splits table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_splits (
            id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            recipient_id TEXT NOT NULL,
            split_amount DECIMAL NOT NULL,
            split_percentage DECIMAL NOT NULL,
            status TEXT DEFAULT 'pending',
            data TEXT NOT NULL,
            FOREIGN KEY (transaction_id) REFERENCES revenue_transactions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Utility functions
def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Simple authentication - in production, use proper JWT validation"""
    # For demo purposes, return a mock user ID
    return "user_123"

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"TXN_{uuid.uuid4().hex[:8].upper()}"

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info("Revenue Distribution Platform started on port 8334")

# API Routes

@app.get("/")
async def root():
    return {
        "service": "Revenue Distribution Platform",
        "version": "1.0.0",
        "port": 8334,
        "features": [
            "Tiered fee system (1% first $100k/year, 0.1% after)",
            "Automatic payment splitting",
            "Tax reporting preparation", 
            "Multi-currency support",
            "Escrow for transactions",
            "Dispute resolution system",
            "Automated invoicing",
            "Revenue forecasting",
            "Profit sharing calculations"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Fee System Routes
@app.post("/api/fees/calculate")
async def calculate_fees(
    user_id: str,
    amount: float,
    year: int = None,
    current_user: str = Depends(authenticate_user)
):
    """Calculate fees based on tiered structure"""
    if year is None:
        year = datetime.now().year
    
    result = await fee_calculator.calculate_fees(user_id, Decimal(str(amount)), year)
    return result

@app.get("/api/fees/{user_id}/summary/{year}")
async def get_fee_summary(
    user_id: str,
    year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get annual fee summary for user"""
    summary = await fee_calculator.get_annual_fee_summary(user_id, year)
    return summary

# Payment Processing Routes
@app.post("/api/payments/process")
async def process_payment(
    transaction_data: dict,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(authenticate_user)
):
    """Process a revenue distribution payment"""
    
    transaction_id = generate_transaction_id()
    
    # Calculate fees
    fee_result = await fee_calculator.calculate_fees(
        transaction_data["recipient_id"], 
        Decimal(str(transaction_data["amount"])),
        datetime.now().year
    )
    
    # Create transaction record
    transaction = RevenueTransaction(
        id=transaction_id,
        payer_id=transaction_data["payer_id"],
        recipient_id=transaction_data["recipient_id"],
        gross_amount=Decimal(str(transaction_data["amount"])),
        currency=transaction_data.get("currency", "USD"),
        platform_fee=fee_result["fee_amount"],
        net_amount=fee_result["net_amount"],
        fee_rate=fee_result["fee_rate"],
        description=transaction_data.get("description", ""),
        created_at=datetime.now(),
        reference_id=transaction_data.get("reference_id"),
        payment_method=transaction_data.get("payment_method", "bank_transfer")
    )
    
    # Store transaction
    conn = sqlite3.connect("/home/activeloguser/activelog/services/revenue-distribution/data/revenue_distribution.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO revenue_transactions 
        (id, payer_id, recipient_id, gross_amount, currency, platform_fee, net_amount, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        transaction.id, transaction.payer_id, transaction.recipient_id,
        float(transaction.gross_amount), transaction.currency,
        float(transaction.platform_fee), float(transaction.net_amount),
        transaction.model_dump_json()
    ))
    
    conn.commit()
    conn.close()
    
    # Process payment splitting in background
    background_tasks.add_task(
        payment_splitter.process_payment_splits, 
        transaction_id, 
        transaction_data.get("splits", [])
    )
    
    return {
        "transaction_id": transaction_id,
        "status": "processing",
        "gross_amount": float(transaction.gross_amount),
        "platform_fee": float(transaction.platform_fee),
        "net_amount": float(transaction.net_amount),
        "fee_rate": float(transaction.fee_rate)
    }

# Tax Reporting Routes
@app.get("/api/tax/report/{user_id}/{year}")
async def generate_tax_report(
    user_id: str,
    year: int,
    current_user: str = Depends(authenticate_user)
):
    """Generate tax report for user"""
    report = await tax_reporter.generate_annual_report(user_id, year)
    return report

@app.get("/api/tax/1099/{user_id}/{year}")
async def generate_1099(
    user_id: str,
    year: int,
    current_user: str = Depends(authenticate_user)
):
    """Generate 1099 form data"""
    form_1099 = await tax_reporter.generate_1099_data(user_id, year)
    return form_1099

# Multi-Currency Routes
@app.get("/api/currency/rates")
async def get_exchange_rates(base_currency: str = "USD"):
    """Get current exchange rates"""
    rates = await currency_manager.get_exchange_rates(base_currency)
    return rates

@app.post("/api/currency/convert")
async def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
    current_user: str = Depends(authenticate_user)
):
    """Convert amount between currencies"""
    result = await currency_manager.convert_amount(
        Decimal(str(amount)), from_currency, to_currency
    )
    return result

# Escrow Routes
@app.post("/api/escrow/create")
async def create_escrow(
    escrow_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Create escrow account for transaction"""
    escrow = await escrow_manager.create_escrow_account(escrow_data)
    return escrow

@app.post("/api/escrow/{escrow_id}/release")
async def release_escrow(
    escrow_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Release funds from escrow"""
    result = await escrow_manager.release_escrow_funds(escrow_id)
    return result

# Dispute Resolution Routes
@app.post("/api/disputes/create")
async def create_dispute(
    dispute_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Create a dispute for transaction"""
    dispute = await dispute_resolver.create_dispute(dispute_data)
    return dispute

@app.get("/api/disputes/{dispute_id}")
async def get_dispute(
    dispute_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get dispute details"""
    dispute = await dispute_resolver.get_dispute(dispute_id)
    return dispute

# Invoicing Routes
@app.post("/api/invoices/generate")
async def generate_invoice(
    invoice_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Generate automated invoice"""
    invoice = await invoice_generator.create_invoice(invoice_data)
    return invoice

@app.get("/api/invoices/{user_id}")
async def get_user_invoices(
    user_id: str,
    status: str = None,
    current_user: str = Depends(authenticate_user)
):
    """Get invoices for user"""
    invoices = await invoice_generator.get_user_invoices(user_id, status)
    return invoices

# Revenue Forecasting Routes
@app.get("/api/forecast/revenue/{user_id}")
async def forecast_revenue(
    user_id: str,
    months_ahead: int = 12,
    current_user: str = Depends(authenticate_user)
):
    """Generate revenue forecast"""
    forecast = await revenue_forecaster.generate_revenue_forecast(user_id, months_ahead)
    return forecast

@app.get("/api/forecast/fees/{user_id}")
async def forecast_fees(
    user_id: str,
    months_ahead: int = 12,
    current_user: str = Depends(authenticate_user)
):
    """Generate fee forecast"""
    forecast = await revenue_forecaster.generate_fee_forecast(user_id, months_ahead)
    return forecast

# Profit Sharing Routes
@app.post("/api/profit-sharing/calculate")
async def calculate_profit_sharing(
    profit_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Calculate profit sharing distribution"""
    distribution = await profit_share_calculator.calculate_distribution(profit_data)
    return distribution

@app.get("/api/profit-sharing/{entity_id}/history")
async def get_profit_sharing_history(
    entity_id: str,
    year: int = None,
    current_user: str = Depends(authenticate_user)
):
    """Get profit sharing history"""
    if year is None:
        year = datetime.now().year
    
    history = await profit_share_calculator.get_distribution_history(entity_id, year)
    return history

# Analytics and Reporting Routes
@app.get("/api/analytics/dashboard/{user_id}")
async def get_revenue_dashboard(
    user_id: str,
    current_user: str = Depends(authenticate_user)
):
    """Get comprehensive revenue analytics dashboard"""
    
    # Get data from various systems
    fee_summary = await fee_calculator.get_annual_fee_summary(user_id, datetime.now().year)
    revenue_forecast = await revenue_forecaster.generate_revenue_forecast(user_id, 6)
    recent_transactions = await get_recent_transactions(user_id, 10)
    
    dashboard = {
        "user_id": user_id,
        "current_year_fees": fee_summary,
        "revenue_forecast": revenue_forecast,
        "recent_transactions": recent_transactions,
        "generated_at": datetime.now().isoformat()
    }
    
    return dashboard

async def get_recent_transactions(user_id: str, limit: int = 10) -> List[dict]:
    """Get recent transactions for user"""
    conn = sqlite3.connect("/home/activeloguser/activelog/services/revenue-distribution/data/revenue_distribution.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT data FROM revenue_transactions 
        WHERE recipient_id = ? OR payer_id = ?
        ORDER BY created_at DESC 
        LIMIT ?
    ''', (user_id, user_id, limit))
    
    results = cursor.fetchall()
    conn.close()
    
    transactions = []
    for result in results:
        transaction_data = json.loads(result[0])
        transactions.append(transaction_data)
    
    return transactions

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8334)