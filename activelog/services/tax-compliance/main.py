#!/usr/bin/env python3
"""
Tax Compliance Platform
Comprehensive tax compliance, reporting, and documentation system
Port: 8337

Features:
- 1099 generation for creators
- CCC to USD reporting
- Business expense tracking
- Charitable donation receipts
- International tax forms
- Automated tax withholding
- Quarterly estimate calculator
- Audit trail generation
- Revenue categorization
- Expense categorization
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

# Import all the subsystem modules
from form_1099_generator import form_1099_generator
from ccc_reporting import ccc_reporter
from expense_tracking import expense_tracker
from donation_receipts import donation_receipt_generator
from international_forms import international_tax_forms
from tax_withholding import tax_withholding_calculator
from quarterly_estimates import quarterly_estimate_calculator
from audit_trails import audit_trail_generator
from revenue_categorizer import revenue_categorizer
from expense_categorizer import expense_categorizer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Tax Compliance Platform",
    description="Comprehensive tax compliance, reporting, and documentation system",
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

# Tax Compliance Data Models
class TaxFormType(str, Enum):
    FORM_1099_MISC = "1099_misc"
    FORM_1099_NEC = "1099_nec"
    FORM_W9 = "w9"
    FORM_1042_S = "1042_s"
    FORM_8966 = "8966"

class ExpenseCategory(str, Enum):
    OFFICE_SUPPLIES = "office_supplies"
    TRAVEL = "travel"
    MEALS = "meals"
    UTILITIES = "utilities"
    SOFTWARE = "software"
    PROFESSIONAL_SERVICES = "professional_services"
    MARKETING = "marketing"
    EQUIPMENT = "equipment"
    RENT = "rent"
    INSURANCE = "insurance"

class RevenueCategory(str, Enum):
    SERVICE_REVENUE = "service_revenue"
    PRODUCT_SALES = "product_sales"
    LICENSING = "licensing"
    ROYALTIES = "royalties"
    CONSULTING = "consulting"
    SUBSCRIPTION = "subscription"
    ADVERTISING = "advertising"
    COMMISSION = "commission"

class TaxEntity(BaseModel):
    id: str
    name: str
    tax_id: str  # SSN or EIN
    entity_type: str = "individual"  # individual, llc, corporation, partnership
    
    # Contact information
    address: Dict[str, str] = {}
    email: str = ""
    phone: str = ""
    
    # Tax details
    tax_year: int
    filing_status: str = "single"
    
    # International
    country: str = "US"
    is_foreign_entity: bool = False
    
    created_at: datetime
    updated_at: datetime

class TaxTransaction(BaseModel):
    id: str
    entity_id: str
    
    # Transaction details
    amount: Decimal
    currency: str = "USD"
    ccc_amount: Optional[Decimal] = None  # If paid in CCC
    transaction_date: date
    
    # Categorization
    revenue_category: Optional[RevenueCategory] = None
    expense_category: Optional[ExpenseCategory] = None
    transaction_type: str = "revenue"  # revenue, expense, donation
    
    # Tax implications
    taxable: bool = True
    deductible: bool = False
    subject_to_withholding: bool = False
    
    # Documentation
    description: str
    receipt_url: Optional[str] = None
    supporting_documents: List[str] = []
    
    # Metadata
    payer_id: Optional[str] = None
    reference_id: Optional[str] = None
    
    created_at: datetime

# Database initialization
def init_database():
    """Initialize SQLite database for persistent storage"""
    os.makedirs("/home/activeloguser/activelog/services/tax-compliance/data", exist_ok=True)
    conn = sqlite3.connect("/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db")
    cursor = conn.cursor()
    
    # Tax entities table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_entities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            tax_id TEXT NOT NULL,
            entity_type TEXT DEFAULT 'individual',
            tax_year INTEGER NOT NULL,
            country TEXT DEFAULT 'US',
            is_foreign_entity BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Tax transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_transactions (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            amount DECIMAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            ccc_amount DECIMAL,
            transaction_date DATE NOT NULL,
            revenue_category TEXT,
            expense_category TEXT,
            transaction_type TEXT DEFAULT 'revenue',
            taxable BOOLEAN DEFAULT TRUE,
            deductible BOOLEAN DEFAULT FALSE,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES tax_entities (id)
        )
    ''')
    
    # Tax forms table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_forms (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            form_type TEXT NOT NULL,
            tax_year INTEGER NOT NULL,
            form_data TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_path TEXT,
            FOREIGN KEY (entity_id) REFERENCES tax_entities (id)
        )
    ''')
    
    # Withholding records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tax_withholding (
            id TEXT PRIMARY KEY,
            entity_id TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            withholding_amount DECIMAL NOT NULL,
            withholding_rate DECIMAL NOT NULL,
            withholding_type TEXT NOT NULL,
            remitted_date DATE,
            data TEXT NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES tax_entities (id),
            FOREIGN KEY (transaction_id) REFERENCES tax_transactions (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Utility functions
def authenticate_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Simple authentication - in production, use proper JWT validation"""
    return "user_123"

def generate_entity_id() -> str:
    """Generate unique entity ID"""
    return f"ENTITY_{uuid.uuid4().hex[:8].upper()}"

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"TAXTXN_{uuid.uuid4().hex[:8].upper()}"

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    logger.info("Tax Compliance Platform started on port 8337")

# API Routes

@app.get("/")
async def root():
    return {
        "service": "Tax Compliance Platform",
        "version": "1.0.0",
        "port": 8337,
        "features": [
            "1099 generation for creators",
            "CCC to USD reporting",
            "Business expense tracking",
            "Charitable donation receipts",
            "International tax forms",
            "Automated tax withholding",
            "Quarterly estimate calculator",
            "Audit trail generation",
            "Revenue categorization",
            "Expense categorization"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Entity Management Routes
@app.post("/api/entities/create")
async def create_tax_entity(
    entity_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Create a new tax entity"""
    
    entity_id = generate_entity_id()
    
    entity = TaxEntity(
        id=entity_id,
        name=entity_data["name"],
        tax_id=entity_data["tax_id"],
        entity_type=entity_data.get("entity_type", "individual"),
        address=entity_data.get("address", {}),
        email=entity_data.get("email", ""),
        phone=entity_data.get("phone", ""),
        tax_year=entity_data.get("tax_year", datetime.now().year),
        filing_status=entity_data.get("filing_status", "single"),
        country=entity_data.get("country", "US"),
        is_foreign_entity=entity_data.get("is_foreign_entity", False),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Store entity
    conn = sqlite3.connect("/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tax_entities 
        (id, name, tax_id, entity_type, tax_year, country, is_foreign_entity, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        entity.id, entity.name, entity.tax_id, entity.entity_type,
        entity.tax_year, entity.country, entity.is_foreign_entity,
        entity.model_dump_json()
    ))
    
    conn.commit()
    conn.close()
    
    return {
        "entity_id": entity_id,
        "status": "created",
        "name": entity.name,
        "tax_year": entity.tax_year
    }

# Transaction Routes
@app.post("/api/transactions/record")
async def record_tax_transaction(
    transaction_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Record a tax-relevant transaction"""
    
    transaction_id = generate_transaction_id()
    
    # Categorize transaction automatically
    if transaction_data.get("transaction_type") == "revenue":
        category = await revenue_categorizer.categorize_revenue(
            transaction_data["description"],
            transaction_data.get("payer_id")
        )
        revenue_category = category["category"]
        expense_category = None
    else:
        category = await expense_categorizer.categorize_expense(
            transaction_data["description"],
            Decimal(str(transaction_data["amount"]))
        )
        expense_category = category["category"]
        revenue_category = None
    
    transaction = TaxTransaction(
        id=transaction_id,
        entity_id=transaction_data["entity_id"],
        amount=Decimal(str(transaction_data["amount"])),
        currency=transaction_data.get("currency", "USD"),
        ccc_amount=Decimal(str(transaction_data["ccc_amount"])) if transaction_data.get("ccc_amount") else None,
        transaction_date=datetime.strptime(transaction_data["transaction_date"], "%Y-%m-%d").date(),
        revenue_category=RevenueCategory(revenue_category) if revenue_category else None,
        expense_category=ExpenseCategory(expense_category) if expense_category else None,
        transaction_type=transaction_data.get("transaction_type", "revenue"),
        taxable=transaction_data.get("taxable", True),
        deductible=transaction_data.get("deductible", transaction_data.get("transaction_type") == "expense"),
        description=transaction_data["description"],
        receipt_url=transaction_data.get("receipt_url"),
        supporting_documents=transaction_data.get("supporting_documents", []),
        payer_id=transaction_data.get("payer_id"),
        reference_id=transaction_data.get("reference_id"),
        created_at=datetime.now()
    )
    
    # Store transaction
    conn = sqlite3.connect("/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db")
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO tax_transactions 
        (id, entity_id, amount, currency, ccc_amount, transaction_date, 
         revenue_category, expense_category, transaction_type, taxable, 
         deductible, description, data)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        transaction.id, transaction.entity_id, float(transaction.amount),
        transaction.currency, float(transaction.ccc_amount) if transaction.ccc_amount else None,
        transaction.transaction_date.isoformat(),
        transaction.revenue_category.value if transaction.revenue_category else None,
        transaction.expense_category.value if transaction.expense_category else None,
        transaction.transaction_type, transaction.taxable, transaction.deductible,
        transaction.description, transaction.model_dump_json()
    ))
    
    conn.commit()
    conn.close()
    
    # Check if withholding is required
    if transaction.subject_to_withholding and transaction.transaction_type == "revenue":
        await tax_withholding_calculator.calculate_withholding(transaction_id)
    
    return {
        "transaction_id": transaction_id,
        "status": "recorded",
        "category": revenue_category or expense_category,
        "taxable": transaction.taxable,
        "amount": float(transaction.amount)
    }

# Form Generation Routes
@app.post("/api/forms/1099/generate")
async def generate_1099_form(
    form_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Generate 1099 form for creator payments"""
    
    form_1099 = await form_1099_generator.generate_1099(
        entity_id=form_data["entity_id"],
        tax_year=form_data["tax_year"],
        form_type=form_data.get("form_type", "1099_misc")
    )
    
    return form_1099

@app.get("/api/forms/1099/{entity_id}/{tax_year}")
async def get_1099_summary(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get 1099 summary for entity and year"""
    
    summary = await form_1099_generator.get_1099_summary(entity_id, tax_year)
    return summary

# CCC Reporting Routes
@app.get("/api/ccc/report/{entity_id}/{tax_year}")
async def generate_ccc_report(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Generate CCC to USD reporting"""
    
    report = await ccc_reporter.generate_ccc_tax_report(entity_id, tax_year)
    return report

@app.post("/api/ccc/conversion")
async def record_ccc_conversion(
    conversion_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Record CCC to USD conversion for tax purposes"""
    
    result = await ccc_reporter.record_ccc_conversion(conversion_data)
    return result

# Expense Tracking Routes
@app.get("/api/expenses/{entity_id}")
async def get_business_expenses(
    entity_id: str,
    year: int = None,
    category: str = None,
    current_user: str = Depends(authenticate_user)
):
    """Get business expenses for entity"""
    
    if year is None:
        year = datetime.now().year
    
    expenses = await expense_tracker.get_business_expenses(entity_id, year, category)
    return expenses

@app.get("/api/expenses/summary/{entity_id}/{tax_year}")
async def get_expense_summary(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get expense summary by category"""
    
    summary = await expense_tracker.get_expense_summary(entity_id, tax_year)
    return summary

# Donation Receipt Routes
@app.post("/api/donations/receipt")
async def generate_donation_receipt(
    donation_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Generate charitable donation receipt"""
    
    receipt = await donation_receipt_generator.create_donation_receipt(donation_data)
    return receipt

@app.get("/api/donations/{entity_id}/{tax_year}")
async def get_donation_summary(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get donation summary for tax year"""
    
    summary = await donation_receipt_generator.get_donation_summary(entity_id, tax_year)
    return summary

# International Tax Forms Routes
@app.post("/api/international/forms/generate")
async def generate_international_form(
    form_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Generate international tax forms"""
    
    form = await international_tax_forms.generate_international_form(
        form_data["form_type"],
        form_data["entity_id"],
        form_data["tax_year"]
    )
    
    return form

# Tax Withholding Routes
@app.get("/api/withholding/{entity_id}/{tax_year}")
async def get_withholding_summary(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get tax withholding summary"""
    
    summary = await tax_withholding_calculator.get_withholding_summary(entity_id, tax_year)
    return summary

@app.post("/api/withholding/calculate")
async def calculate_withholding(
    withholding_data: dict,
    current_user: str = Depends(authenticate_user)
):
    """Calculate tax withholding for transaction"""
    
    result = await tax_withholding_calculator.calculate_withholding_amount(
        withholding_data["amount"],
        withholding_data["entity_type"],
        withholding_data.get("is_foreign", False)
    )
    
    return result

# Quarterly Estimates Routes
@app.get("/api/quarterly/estimates/{entity_id}/{tax_year}")
async def calculate_quarterly_estimates(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Calculate quarterly estimated tax payments"""
    
    estimates = await quarterly_estimate_calculator.calculate_quarterly_estimate(entity_id, 1, tax_year)
    return estimates

@app.get("/api/quarterly/calendar/{entity_id}/{tax_year}")
async def get_quarterly_calendar(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get quarterly payment calendar"""
    
    calendar = await quarterly_estimate_calculator.calculate_quarterly_estimate(entity_id, 1, tax_year)
    return calendar

# Audit Trail Routes
@app.get("/api/audit/trail/{entity_id}")
async def generate_audit_trail(
    entity_id: str,
    start_date: str = None,
    end_date: str = None,
    current_user: str = Depends(authenticate_user)
):
    """Generate audit trail for entity"""
    
    trail = await audit_trail_generator.generate_audit_trail(
        entity_id, start_date, end_date
    )
    return trail

@app.get("/api/audit/compliance/{entity_id}/{tax_year}")
async def get_compliance_report(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_user)
):
    """Get tax compliance report"""
    
    report = await audit_trail_generator.generate_compliance_report(entity_id, tax_year)
    return report

# Analytics and Dashboard Routes
@app.get("/api/analytics/dashboard/{entity_id}")
async def get_tax_dashboard(
    entity_id: str,
    tax_year: int = None,
    current_user: str = Depends(authenticate_user)
):
    """Get comprehensive tax analytics dashboard"""
    
    if tax_year is None:
        tax_year = datetime.now().year
    
    # Get data from various systems
    revenue_summary = await get_revenue_summary(entity_id, tax_year)
    expense_summary = await expense_tracker.get_expense_summary(entity_id, tax_year)
    quarterly_estimates = await quarterly_estimate_calculator.calculate_quarterly_estimate(entity_id, 1, tax_year)
    withholding_summary = await tax_withholding_calculator.get_withholding_summary(entity_id, tax_year)
    
    dashboard = {
        "entity_id": entity_id,
        "tax_year": tax_year,
        "revenue_summary": revenue_summary,
        "expense_summary": expense_summary,
        "quarterly_estimates": quarterly_estimates,
        "withholding_summary": withholding_summary,
        "compliance_status": await audit_trail_generator.check_compliance_status(entity_id, tax_year),
        "generated_at": datetime.now().isoformat()
    }
    
    return dashboard

async def get_revenue_summary(entity_id: str, tax_year: int) -> Dict[str, Any]:
    """Get revenue summary for entity and year"""
    
    conn = sqlite3.connect("/home/activeloguser/activelog/services/tax-compliance/data/tax_compliance.db")
    cursor = conn.cursor()
    
    # Total revenue by category
    cursor.execute('''
        SELECT 
            revenue_category,
            SUM(amount) as total_amount,
            COUNT(*) as transaction_count
        FROM tax_transactions
        WHERE entity_id = ?
        AND strftime('%Y', transaction_date) = ?
        AND transaction_type = 'revenue'
        AND taxable = TRUE
        GROUP BY revenue_category
    ''', (entity_id, str(tax_year)))
    
    results = cursor.fetchall()
    
    # Total revenue
    cursor.execute('''
        SELECT 
            SUM(amount) as total_revenue,
            COUNT(*) as total_transactions
        FROM tax_transactions
        WHERE entity_id = ?
        AND strftime('%Y', transaction_date) = ?
        AND transaction_type = 'revenue'
        AND taxable = TRUE
    ''', (entity_id, str(tax_year)))
    
    totals = cursor.fetchone()
    conn.close()
    
    category_breakdown = {}
    for result in results:
        category = result[0] if result[0] else "uncategorized"
        category_breakdown[category] = {
            "amount": float(result[1]),
            "transaction_count": result[2]
        }
    
    return {
        "total_revenue": float(totals[0]) if totals[0] else 0.0,
        "total_transactions": totals[1],
        "category_breakdown": category_breakdown
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8337)