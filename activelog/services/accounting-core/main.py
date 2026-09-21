#!/usr/bin/env python3
"""
Accounting Core Platform
Comprehensive double-entry bookkeeping and financial reporting system
Port: 8349

Features:
- Double-entry bookkeeping engine
- Chart of accounts management
- Journal entry system
- General ledger
- Accounts receivable/payable
- Bank reconciliation
- Financial statement generator (P&L, Balance Sheet, Cash Flow)
- Multi-currency support
- Audit trail system
- Tax preparation interface
- Depreciation schedules
- Budget vs actual reporting
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
import hashlib

# Import all the subsystem modules
from bookkeeping_engine import double_entry_system
from chart_of_accounts import coa_manager
from journal_entries import journal_system
from general_ledger import ledger_system
from accounts_receivable import ar_system
from accounts_payable import ap_system
from bank_reconciliation import reconciliation_system
from financial_statements import statement_generator
from multi_currency import currency_system
from audit_trail import audit_system
from tax_preparation import tax_interface
from depreciation import depreciation_system
from budget_reporting import budget_system

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Accounting Core Platform",
    description="Comprehensive double-entry bookkeeping and financial reporting system",
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

# Accounting Data Models
class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"

class AccountSubType(str, Enum):
    # Assets
    CURRENT_ASSET = "current_asset"
    FIXED_ASSET = "fixed_asset"
    OTHER_ASSET = "other_asset"
    
    # Liabilities
    CURRENT_LIABILITY = "current_liability"
    LONG_TERM_LIABILITY = "long_term_liability"
    
    # Equity
    PAID_IN_CAPITAL = "paid_in_capital"
    RETAINED_EARNINGS = "retained_earnings"
    OWNERS_EQUITY = "owners_equity"
    
    # Revenue
    OPERATING_REVENUE = "operating_revenue"
    NON_OPERATING_REVENUE = "non_operating_revenue"
    
    # Expenses
    OPERATING_EXPENSE = "operating_expense"
    NON_OPERATING_EXPENSE = "non_operating_expense"

class JournalEntryStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    POSTED = "posted"
    REVERSED = "reversed"

class Account(BaseModel):
    id: str
    account_code: str
    account_name: str
    account_type: AccountType
    account_subtype: AccountSubType
    
    # Account properties
    is_active: bool = True
    requires_detail: bool = False  # Requires sub-account detail
    cash_flow_type: Optional[str] = None  # operating, investing, financing
    
    # Balances
    current_balance: Decimal = Decimal('0')
    debit_balance: Decimal = Decimal('0')
    credit_balance: Decimal = Decimal('0')
    
    # Parent account for sub-accounts
    parent_account_id: Optional[str] = None
    
    # Currency and multi-entity
    default_currency: str = "USD"
    entity_id: Optional[str] = None
    
    # Metadata
    description: str = ""
    tax_code: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

class JournalEntry(BaseModel):
    id: str
    entry_number: str
    
    # Entry details
    transaction_date: date
    description: str
    reference: Optional[str] = None
    
    # Journal lines (debits and credits)
    lines: List[Dict[str, Any]] = []
    
    # Totals
    total_debits: Decimal = Decimal('0')
    total_credits: Decimal = Decimal('0')
    
    # Status and approval
    status: JournalEntryStatus = JournalEntryStatus.DRAFT
    created_by: str
    approved_by: Optional[str] = None
    posted_by: Optional[str] = None
    
    # Metadata
    source_document: Optional[str] = None
    batch_id: Optional[str] = None
    entity_id: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

class BankTransaction(BaseModel):
    id: str
    bank_account_id: str
    
    # Transaction details
    transaction_date: date
    description: str
    amount: Decimal
    transaction_type: str  # debit, credit
    
    # Bank statement info
    statement_date: Optional[date] = None
    check_number: Optional[str] = None
    reference_number: Optional[str] = None
    
    # Reconciliation
    is_reconciled: bool = False
    reconciled_date: Optional[date] = None
    journal_entry_id: Optional[str] = None
    
    # Metadata
    imported_from: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime

class FinancialPeriod(BaseModel):
    id: str
    period_name: str
    start_date: date
    end_date: date
    
    # Period status
    is_closed: bool = False
    closed_by: Optional[str] = None
    closed_date: Optional[datetime] = None
    
    # Period type
    period_type: str = "month"  # month, quarter, year
    
    created_at: datetime

# Database initialization
def init_database():
    """Initialize SQLite database for persistent storage"""
    os.makedirs("/home/activeloguser/activelog/services/accounting-core/data", exist_ok=True)
    conn = sqlite3.connect("/home/activeloguser/activelog/services/accounting-core/data/accounting_core.db")
    cursor = conn.cursor()
    
    # Chart of accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chart_of_accounts (
            id TEXT PRIMARY KEY,
            account_code TEXT UNIQUE NOT NULL,
            account_name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            account_subtype TEXT NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            requires_detail BOOLEAN DEFAULT FALSE,
            cash_flow_type TEXT,
            current_balance DECIMAL DEFAULT 0,
            debit_balance DECIMAL DEFAULT 0,
            credit_balance DECIMAL DEFAULT 0,
            parent_account_id TEXT,
            default_currency TEXT DEFAULT 'USD',
            entity_id TEXT,
            description TEXT,
            tax_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (parent_account_id) REFERENCES chart_of_accounts (id)
        )
    ''')
    
    # Journal entries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entries (
            id TEXT PRIMARY KEY,
            entry_number TEXT UNIQUE NOT NULL,
            transaction_date DATE NOT NULL,
            description TEXT NOT NULL,
            reference TEXT,
            total_debits DECIMAL DEFAULT 0,
            total_credits DECIMAL DEFAULT 0,
            status TEXT DEFAULT 'draft',
            created_by TEXT NOT NULL,
            approved_by TEXT,
            posted_by TEXT,
            source_document TEXT,
            batch_id TEXT,
            entity_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Journal entry lines table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS journal_entry_lines (
            id TEXT PRIMARY KEY,
            journal_entry_id TEXT NOT NULL,
            account_id TEXT NOT NULL,
            line_number INTEGER NOT NULL,
            description TEXT,
            debit_amount DECIMAL DEFAULT 0,
            credit_amount DECIMAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            exchange_rate DECIMAL DEFAULT 1.0,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id),
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id)
        )
    ''')
    
    # General ledger table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS general_ledger (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            journal_entry_id TEXT NOT NULL,
            journal_line_id TEXT NOT NULL,
            transaction_date DATE NOT NULL,
            description TEXT NOT NULL,
            debit_amount DECIMAL DEFAULT 0,
            credit_amount DECIMAL DEFAULT 0,
            running_balance DECIMAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            exchange_rate DECIMAL DEFAULT 1.0,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT,
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id),
            FOREIGN KEY (journal_line_id) REFERENCES journal_entry_lines (id)
        )
    ''')
    
    # Bank accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id TEXT PRIMARY KEY,
            account_id TEXT NOT NULL,
            bank_name TEXT NOT NULL,
            account_number TEXT NOT NULL,
            account_type TEXT NOT NULL,
            routing_number TEXT,
            current_balance DECIMAL DEFAULT 0,
            last_reconciled_date DATE,
            last_reconciled_balance DECIMAL DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id)
        )
    ''')
    
    # Bank transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bank_transactions (
            id TEXT PRIMARY KEY,
            bank_account_id TEXT NOT NULL,
            transaction_date DATE NOT NULL,
            description TEXT NOT NULL,
            amount DECIMAL NOT NULL,
            transaction_type TEXT NOT NULL,
            statement_date DATE,
            check_number TEXT,
            reference_number TEXT,
            is_reconciled BOOLEAN DEFAULT FALSE,
            reconciled_date DATE,
            journal_entry_id TEXT,
            imported_from TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (bank_account_id) REFERENCES bank_accounts (id),
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
        )
    ''')
    
    # Accounts receivable table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts_receivable (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            invoice_date DATE NOT NULL,
            due_date DATE NOT NULL,
            total_amount DECIMAL NOT NULL,
            amount_paid DECIMAL DEFAULT 0,
            amount_due DECIMAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'outstanding',
            journal_entry_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
        )
    ''')
    
    # Accounts payable table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts_payable (
            id TEXT PRIMARY KEY,
            vendor_id TEXT NOT NULL,
            bill_number TEXT NOT NULL,
            bill_date DATE NOT NULL,
            due_date DATE NOT NULL,
            total_amount DECIMAL NOT NULL,
            amount_paid DECIMAL DEFAULT 0,
            amount_due DECIMAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'outstanding',
            journal_entry_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (journal_entry_id) REFERENCES journal_entries (id)
        )
    ''')
    
    # Financial periods table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS financial_periods (
            id TEXT PRIMARY KEY,
            period_name TEXT NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            is_closed BOOLEAN DEFAULT FALSE,
            closed_by TEXT,
            closed_date TIMESTAMP,
            period_type TEXT DEFAULT 'month',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL
        )
    ''')
    
    # Budgets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id TEXT PRIMARY KEY,
            budget_name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            period_id TEXT NOT NULL,
            budgeted_amount DECIMAL NOT NULL,
            actual_amount DECIMAL DEFAULT 0,
            variance_amount DECIMAL DEFAULT 0,
            variance_percentage DECIMAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id),
            FOREIGN KEY (period_id) REFERENCES financial_periods (id)
        )
    ''')
    
    # Fixed assets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fixed_assets (
            id TEXT PRIMARY KEY,
            asset_name TEXT NOT NULL,
            account_id TEXT NOT NULL,
            asset_category TEXT NOT NULL,
            purchase_date DATE NOT NULL,
            purchase_cost DECIMAL NOT NULL,
            accumulated_depreciation DECIMAL DEFAULT 0,
            current_book_value DECIMAL NOT NULL,
            salvage_value DECIMAL DEFAULT 0,
            useful_life_years INTEGER NOT NULL,
            depreciation_method TEXT DEFAULT 'straight_line',
            is_active BOOLEAN DEFAULT TRUE,
            disposal_date DATE,
            disposal_proceeds DECIMAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data TEXT NOT NULL,
            FOREIGN KEY (account_id) REFERENCES chart_of_accounts (id)
        )
    ''')
    
    # Audit trail table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_trail (
            id TEXT PRIMARY KEY,
            table_name TEXT NOT NULL,
            record_id TEXT NOT NULL,
            action TEXT NOT NULL,
            old_values TEXT,
            new_values TEXT,
            user_id TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            user_agent TEXT,
            data TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Utility functions
def authenticate_accountant(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Accountant authentication"""
    return "accountant_123"

def generate_account_id() -> str:
    """Generate unique account ID"""
    return f"ACC_{uuid.uuid4().hex[:8].upper()}"

def generate_journal_entry_number() -> str:
    """Generate unique journal entry number"""
    return f"JE{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"

def generate_transaction_id() -> str:
    """Generate unique transaction ID"""
    return f"TXN_{uuid.uuid4().hex[:8].upper()}"

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()
    
    # Initialize accounting systems
    await double_entry_system.initialize()
    await coa_manager.initialize()
    await journal_system.initialize()
    await currency_system.initialize()
    await audit_system.initialize()
    await depreciation_system.initialize()
    
    logger.info("Accounting Core Platform started on port 8349")

# API Routes

@app.get("/")
async def root():
    return {
        "service": "Accounting Core Platform",
        "version": "1.0.0",
        "port": 8349,
        "features": [
            "Double-entry bookkeeping engine",
            "Chart of accounts management",
            "Journal entry system",
            "General ledger",
            "Accounts receivable/payable",
            "Bank reconciliation",
            "Financial statement generator",
            "Multi-currency support",
            "Audit trail system",
            "Tax preparation interface",
            "Depreciation schedules",
            "Budget vs actual reporting"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Chart of Accounts Routes
@app.post("/api/accounts/create")
async def create_account(
    account_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Create a new account"""
    
    account_id = generate_account_id()
    
    account = Account(
        id=account_id,
        account_code=account_data["account_code"],
        account_name=account_data["account_name"],
        account_type=AccountType(account_data["account_type"]),
        account_subtype=AccountSubType(account_data["account_subtype"]),
        is_active=account_data.get("is_active", True),
        requires_detail=account_data.get("requires_detail", False),
        cash_flow_type=account_data.get("cash_flow_type"),
        parent_account_id=account_data.get("parent_account_id"),
        default_currency=account_data.get("default_currency", "USD"),
        entity_id=account_data.get("entity_id"),
        description=account_data.get("description", ""),
        tax_code=account_data.get("tax_code"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create account in chart of accounts
    await coa_manager.create_account(account)
    
    return {
        "account_id": account_id,
        "account_code": account.account_code,
        "account_name": account.account_name,
        "account_type": account.account_type.value,
        "status": "created"
    }

@app.get("/api/accounts")
async def get_chart_of_accounts(
    account_type: str = None,
    is_active: bool = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get chart of accounts"""
    
    return await coa_manager.get_chart_of_accounts(account_type, is_active)

@app.get("/api/accounts/{account_id}")
async def get_account(
    account_id: str,
    current_user: str = Depends(authenticate_accountant)
):
    """Get account details"""
    
    return await coa_manager.get_account_details(account_id)

@app.put("/api/accounts/{account_id}")
async def update_account(
    account_id: str,
    update_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Update account"""
    
    return await coa_manager.update_account(account_id, update_data)

# Journal Entry Routes
@app.post("/api/journal-entries/create")
async def create_journal_entry(
    entry_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Create journal entry"""
    
    entry_id = generate_transaction_id()
    entry_number = generate_journal_entry_number()
    
    # Validate double-entry principles
    validation = await double_entry_system.validate_entry(entry_data["lines"])
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["errors"])
    
    journal_entry = JournalEntry(
        id=entry_id,
        entry_number=entry_number,
        transaction_date=datetime.strptime(entry_data["transaction_date"], "%Y-%m-%d").date(),
        description=entry_data["description"],
        reference=entry_data.get("reference"),
        lines=entry_data["lines"],
        total_debits=Decimal(str(validation["total_debits"])),
        total_credits=Decimal(str(validation["total_credits"])),
        created_by=current_user,
        source_document=entry_data.get("source_document"),
        batch_id=entry_data.get("batch_id"),
        entity_id=entry_data.get("entity_id"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    # Create journal entry
    result = await journal_system.create_entry(journal_entry)
    
    return result

@app.get("/api/journal-entries")
async def get_journal_entries(
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get journal entries"""
    
    return await journal_system.get_entries(start_date, end_date, status)

@app.get("/api/journal-entries/{entry_id}")
async def get_journal_entry(
    entry_id: str,
    current_user: str = Depends(authenticate_accountant)
):
    """Get journal entry details"""
    
    return await journal_system.get_entry_details(entry_id)

@app.post("/api/journal-entries/{entry_id}/post")
async def post_journal_entry(
    entry_id: str,
    current_user: str = Depends(authenticate_accountant)
):
    """Post journal entry to general ledger"""
    
    result = await journal_system.post_entry(entry_id, current_user)
    
    # Update general ledger
    await ledger_system.post_journal_entry(entry_id)
    
    return result

# General Ledger Routes
@app.get("/api/general-ledger/{account_id}")
async def get_account_ledger(
    account_id: str,
    start_date: str = None,
    end_date: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get account ledger"""
    
    return await ledger_system.get_account_ledger(account_id, start_date, end_date)

@app.get("/api/general-ledger/trial-balance")
async def get_trial_balance(
    as_of_date: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Generate trial balance"""
    
    trial_balance = await ledger_system.generate_trial_balance(as_of_date)
    return trial_balance

# Accounts Receivable Routes
@app.post("/api/accounts-receivable/invoice")
async def create_invoice(
    invoice_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Create customer invoice"""
    
    invoice = await ar_system.create_invoice(invoice_data)
    return invoice

@app.get("/api/accounts-receivable")
async def get_accounts_receivable(
    customer_id: str = None,
    status: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get accounts receivable"""
    
    return await ar_system.get_receivables(customer_id, status)

@app.post("/api/accounts-receivable/{invoice_id}/payment")
async def record_customer_payment(
    invoice_id: str,
    payment_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Record customer payment"""
    
    payment = await ar_system.record_payment(invoice_id, payment_data)
    return payment

# Accounts Payable Routes
@app.post("/api/accounts-payable/bill")
async def create_bill(
    bill_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Create vendor bill"""
    
    bill = await ap_system.create_bill(bill_data)
    return bill

@app.get("/api/accounts-payable")
async def get_accounts_payable(
    vendor_id: str = None,
    status: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get accounts payable"""
    
    return await ap_system.get_payables(vendor_id, status)

@app.post("/api/accounts-payable/{bill_id}/payment")
async def record_vendor_payment(
    bill_id: str,
    payment_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Record vendor payment"""
    
    payment = await ap_system.record_payment(bill_id, payment_data)
    return payment

# Bank Reconciliation Routes
@app.post("/api/bank-reconciliation/import-statement")
async def import_bank_statement(
    bank_account_id: str,
    statement_file: UploadFile = File(...),
    current_user: str = Depends(authenticate_accountant)
):
    """Import bank statement"""
    
    result = await reconciliation_system.import_statement(bank_account_id, statement_file)
    return result

@app.get("/api/bank-reconciliation/{bank_account_id}")
async def get_reconciliation_data(
    bank_account_id: str,
    statement_date: str,
    current_user: str = Depends(authenticate_accountant)
):
    """Get bank reconciliation data"""
    
    return await reconciliation_system.get_reconciliation_data(bank_account_id, statement_date)

@app.post("/api/bank-reconciliation/{bank_account_id}/reconcile")
async def reconcile_transactions(
    bank_account_id: str,
    reconciliation_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Reconcile bank transactions"""
    
    result = await reconciliation_system.reconcile_transactions(bank_account_id, reconciliation_data)
    return result

# Financial Statements Routes
@app.get("/api/financial-statements/income-statement")
async def generate_income_statement(
    start_date: str,
    end_date: str,
    entity_id: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Generate income statement"""
    
    statement = await statement_generator.generate_income_statement(start_date, end_date, entity_id)
    return statement

@app.get("/api/financial-statements/balance-sheet")
async def generate_balance_sheet(
    as_of_date: str,
    entity_id: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Generate balance sheet"""
    
    statement = await statement_generator.generate_balance_sheet(as_of_date, entity_id)
    return statement

@app.get("/api/financial-statements/cash-flow")
async def generate_cash_flow_statement(
    start_date: str,
    end_date: str,
    entity_id: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Generate cash flow statement"""
    
    statement = await statement_generator.generate_cash_flow_statement(start_date, end_date, entity_id)
    return statement

# Multi-Currency Routes
@app.get("/api/currency/rates")
async def get_exchange_rates(
    date: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get exchange rates"""
    
    rates = await currency_system.get_exchange_rates(date)
    return rates

@app.post("/api/currency/conversion")
async def convert_currency(
    conversion_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Convert currency amount"""
    
    result = await currency_system.convert_amount(
        conversion_data["amount"],
        conversion_data["from_currency"],
        conversion_data["to_currency"],
        conversion_data.get("date")
    )
    return result

# Tax Preparation Routes
@app.get("/api/tax-preparation/{entity_id}")
async def get_tax_preparation_data(
    entity_id: str,
    tax_year: int,
    current_user: str = Depends(authenticate_accountant)
):
    """Get tax preparation data"""
    
    tax_data = await tax_interface.get_tax_data(entity_id, tax_year)
    return tax_data

@app.post("/api/tax-preparation/export")
async def export_tax_data(
    export_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Export tax data"""
    
    result = await tax_interface.export_tax_data(export_data)
    return result

# Depreciation Routes
@app.get("/api/depreciation/schedule/{asset_id}")
async def get_depreciation_schedule(
    asset_id: str,
    current_user: str = Depends(authenticate_accountant)
):
    """Get asset depreciation schedule"""
    
    schedule = await depreciation_system.get_depreciation_schedule(asset_id)
    return schedule

@app.post("/api/depreciation/calculate")
async def calculate_monthly_depreciation(
    period_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Calculate and record monthly depreciation"""
    
    result = await depreciation_system.calculate_monthly_depreciation(period_data)
    return result

# Budget vs Actual Routes
@app.post("/api/budgets/create")
async def create_budget(
    budget_data: dict,
    current_user: str = Depends(authenticate_accountant)
):
    """Create budget"""
    
    budget = await budget_system.create_budget(budget_data)
    return budget

@app.get("/api/budgets/vs-actual")
async def get_budget_vs_actual(
    period_id: str,
    account_type: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get budget vs actual report"""
    
    report = await budget_system.generate_budget_vs_actual_report(period_id, account_type)
    return report

@app.get("/api/budgets/variance-analysis")
async def get_variance_analysis(
    period_id: str,
    threshold: float = 0.1,
    current_user: str = Depends(authenticate_accountant)
):
    """Get variance analysis"""
    
    analysis = await budget_system.generate_variance_analysis(period_id, threshold)
    return analysis

# Audit Trail Routes
@app.get("/api/audit-trail/{record_id}")
async def get_audit_trail(
    record_id: str,
    table_name: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get audit trail for record"""
    
    trail = await audit_system.get_audit_trail(record_id, table_name)
    return trail

@app.get("/api/audit-trail/activity-log")
async def get_activity_log(
    start_date: str = None,
    end_date: str = None,
    user_id: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get activity log"""
    
    log = await audit_system.get_activity_log(start_date, end_date, user_id)
    return log

# Reporting Routes
@app.get("/api/reports/aging")
async def get_aging_report(
    report_type: str,  # receivables, payables
    as_of_date: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Generate aging report"""
    
    if report_type == "receivables":
        report = await ar_system.generate_aging_report(as_of_date)
    elif report_type == "payables":
        report = await ap_system.generate_aging_report(as_of_date)
    else:
        raise HTTPException(status_code=400, detail="Invalid report type")
    
    return report

@app.get("/api/reports/financial-summary")
async def get_financial_summary(
    period_start: str,
    period_end: str,
    entity_id: str = None,
    current_user: str = Depends(authenticate_accountant)
):
    """Get comprehensive financial summary"""
    
    # Generate all major financial statements
    income_statement = await statement_generator.generate_income_statement(period_start, period_end, entity_id)
    balance_sheet = await statement_generator.generate_balance_sheet(period_end, entity_id)
    cash_flow = await statement_generator.generate_cash_flow_statement(period_start, period_end, entity_id)
    
    summary = {
        "period": {
            "start_date": period_start,
            "end_date": period_end
        },
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow_statement": cash_flow,
        "key_ratios": await statement_generator.calculate_financial_ratios(period_end, entity_id),
        "generated_at": datetime.now().isoformat()
    }
    
    return summary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8349)