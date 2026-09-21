#!/usr/bin/env python3
"""
Advanced Payroll Automation Engine for ActiveLog
Handles comprehensive payroll processing, tax calculations, and compliance
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import asyncpg
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import yaml
from enum import Enum
import uuid
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
import boto3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PayrollFrequency(Enum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    SEMIMONTHLY = "semimonthly"
    MONTHLY = "monthly"

class PayrollStatus(Enum):
    DRAFT = "draft"
    PROCESSING = "processing"
    APPROVED = "approved"
    PAID = "paid"
    CANCELLED = "cancelled"

class EmployeeStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"

class PayType(Enum):
    SALARY = "salary"
    HOURLY = "hourly"
    CONTRACTOR = "contractor"

@dataclass
class TaxBracket:
    """Tax bracket definition"""
    min_income: Decimal
    max_income: Optional[Decimal]
    rate: Decimal
    base_tax: Decimal = Decimal('0')

@dataclass
class PayrollItem:
    """Individual payroll item (earning or deduction)"""
    code: str
    name: str
    amount: Decimal
    is_taxable: bool = True
    is_pre_tax: bool = False
    is_employer_contribution: bool = False
    category: str = "earning"  # earning, deduction, tax

@dataclass
class Employee:
    """Employee information for payroll"""
    id: int
    employee_number: str
    first_name: str
    last_name: str
    email: str
    ssn: str
    hire_date: date
    status: EmployeeStatus
    pay_type: PayType
    pay_rate: Decimal
    pay_frequency: PayrollFrequency
    
    # Tax information
    federal_allowances: int
    state_allowances: int
    filing_status: str  # single, married_filing_jointly, married_filing_separately, head_of_household
    additional_federal_withholding: Decimal = Decimal('0')
    additional_state_withholding: Decimal = Decimal('0')
    
    # Benefits and deductions
    health_insurance: Decimal = Decimal('0')
    dental_insurance: Decimal = Decimal('0')
    vision_insurance: Decimal = Decimal('0')
    retirement_401k: Decimal = Decimal('0')  # percentage
    retirement_401k_amount: Decimal = Decimal('0')  # fixed amount
    
    # Address information
    address_line1: str = ""
    address_line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    
    # Bank information for direct deposit
    bank_account_number: str = ""
    bank_routing_number: str = ""
    account_type: str = "checking"  # checking, savings

@dataclass
class Timesheet:
    """Employee timesheet for a pay period"""
    employee_id: int
    pay_period_start: date
    pay_period_end: date
    regular_hours: Decimal
    overtime_hours: Decimal = Decimal('0')
    double_time_hours: Decimal = Decimal('0')
    vacation_hours: Decimal = Decimal('0')
    sick_hours: Decimal = Decimal('0')
    holiday_hours: Decimal = Decimal('0')
    approved: bool = False
    approved_by: Optional[int] = None
    approved_at: Optional[datetime] = None

@dataclass
class PayrollCalculation:
    """Complete payroll calculation for an employee"""
    employee: Employee
    pay_period_start: date
    pay_period_end: date
    
    # Earnings
    regular_pay: Decimal = Decimal('0')
    overtime_pay: Decimal = Decimal('0')
    double_time_pay: Decimal = Decimal('0')
    vacation_pay: Decimal = Decimal('0')
    sick_pay: Decimal = Decimal('0')
    holiday_pay: Decimal = Decimal('0')
    bonus: Decimal = Decimal('0')
    commission: Decimal = Decimal('0')
    
    # Pre-tax deductions
    health_insurance: Decimal = Decimal('0')
    dental_insurance: Decimal = Decimal('0')
    vision_insurance: Decimal = Decimal('0')
    retirement_401k: Decimal = Decimal('0')
    flexible_spending: Decimal = Decimal('0')
    
    # Tax calculations
    federal_income_tax: Decimal = Decimal('0')
    state_income_tax: Decimal = Decimal('0')
    social_security_tax: Decimal = Decimal('0')
    medicare_tax: Decimal = Decimal('0')
    unemployment_tax: Decimal = Decimal('0')
    disability_tax: Decimal = Decimal('0')
    
    # Post-tax deductions
    union_dues: Decimal = Decimal('0')
    garnishments: Decimal = Decimal('0')
    loan_repayments: Decimal = Decimal('0')
    
    # Employer contributions
    employer_social_security: Decimal = Decimal('0')
    employer_medicare: Decimal = Decimal('0')
    employer_unemployment: Decimal = Decimal('0')
    employer_401k_match: Decimal = Decimal('0')
    
    def __post_init__(self):
        self.calculate_totals()
    
    @property
    def gross_pay(self) -> Decimal:
        """Total gross pay before deductions"""
        return (self.regular_pay + self.overtime_pay + self.double_time_pay +
                self.vacation_pay + self.sick_pay + self.holiday_pay +
                self.bonus + self.commission)
    
    @property
    def total_pre_tax_deductions(self) -> Decimal:
        """Total pre-tax deductions"""
        return (self.health_insurance + self.dental_insurance + self.vision_insurance +
                self.retirement_401k + self.flexible_spending)
    
    @property
    def taxable_income(self) -> Decimal:
        """Income subject to taxes (gross - pre-tax deductions)"""
        return self.gross_pay - self.total_pre_tax_deductions
    
    @property
    def total_taxes(self) -> Decimal:
        """Total tax withholdings"""
        return (self.federal_income_tax + self.state_income_tax +
                self.social_security_tax + self.medicare_tax +
                self.unemployment_tax + self.disability_tax)
    
    @property
    def total_post_tax_deductions(self) -> Decimal:
        """Total post-tax deductions"""
        return self.union_dues + self.garnishments + self.loan_repayments
    
    @property
    def net_pay(self) -> Decimal:
        """Final net pay amount"""
        return self.gross_pay - self.total_pre_tax_deductions - self.total_taxes - self.total_post_tax_deductions
    
    @property
    def total_employer_costs(self) -> Decimal:
        """Total employer costs"""
        return (self.gross_pay + self.employer_social_security + self.employer_medicare +
                self.employer_unemployment + self.employer_401k_match)
    
    def calculate_totals(self):
        """Calculate and round all monetary amounts to 2 decimal places"""
        for field_name in ['regular_pay', 'overtime_pay', 'double_time_pay', 'vacation_pay',
                          'sick_pay', 'holiday_pay', 'bonus', 'commission',
                          'health_insurance', 'dental_insurance', 'vision_insurance',
                          'retirement_401k', 'flexible_spending', 'federal_income_tax',
                          'state_income_tax', 'social_security_tax', 'medicare_tax',
                          'unemployment_tax', 'disability_tax', 'union_dues', 'garnishments',
                          'loan_repayments', 'employer_social_security', 'employer_medicare',
                          'employer_unemployment', 'employer_401k_match']:
            current_value = getattr(self, field_name)
            setattr(self, field_name, current_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

class TaxCalculator:
    """Handles tax calculations for payroll"""
    
    def __init__(self, tax_tables_config: Dict[str, Any]):
        self.tax_tables = tax_tables_config
        self.load_tax_tables()
    
    def load_tax_tables(self):
        """Load current year tax tables"""
        current_year = datetime.now().year
        
        # Federal tax brackets for 2024 (simplified)
        self.federal_brackets = {
            'single': [
                TaxBracket(Decimal('0'), Decimal('11000'), Decimal('0.10')),
                TaxBracket(Decimal('11000'), Decimal('44725'), Decimal('0.12'), Decimal('1100')),
                TaxBracket(Decimal('44725'), Decimal('95375'), Decimal('0.22'), Decimal('5147')),
                TaxBracket(Decimal('95375'), Decimal('182050'), Decimal('0.24'), Decimal('16290')),
                TaxBracket(Decimal('182050'), Decimal('231250'), Decimal('0.32'), Decimal('37104')),
                TaxBracket(Decimal('231250'), Decimal('578125'), Decimal('0.35'), Decimal('52832')),
                TaxBracket(Decimal('578125'), None, Decimal('0.37'), Decimal('174238.25'))
            ],
            'married_filing_jointly': [
                TaxBracket(Decimal('0'), Decimal('22000'), Decimal('0.10')),
                TaxBracket(Decimal('22000'), Decimal('89450'), Decimal('0.12'), Decimal('2200')),
                TaxBracket(Decimal('89450'), Decimal('190750'), Decimal('0.22'), Decimal('10294')),
                TaxBracket(Decimal('190750'), Decimal('364200'), Decimal('0.24'), Decimal('32580')),
                TaxBracket(Decimal('364200'), Decimal('462500'), Decimal('0.32'), Decimal('74208')),
                TaxBracket(Decimal('462500'), Decimal('693750'), Decimal('0.35'), Decimal('105664')),
                TaxBracket(Decimal('693750'), None, Decimal('0.37'), Decimal('186601.50'))
            ]
        }
        
        # Social Security and Medicare rates (2024)
        self.social_security_rate = Decimal('0.062')
        self.social_security_wage_base = Decimal('160200')
        self.medicare_rate = Decimal('0.0145')
        self.additional_medicare_rate = Decimal('0.009')  # on income over $200,000
        self.additional_medicare_threshold = Decimal('200000')
        
        # State tax rates (simplified - would need full state tables)
        self.state_tax_rates = {
            'CA': Decimal('0.08'),  # California simplified rate
            'TX': Decimal('0.00'),  # Texas has no state income tax
            'NY': Decimal('0.06'),  # New York simplified rate
            'FL': Decimal('0.00'),  # Florida has no state income tax
        }
    
    def calculate_federal_tax(self, annual_income: Decimal, filing_status: str, 
                            allowances: int, pay_periods: int) -> Decimal:
        """Calculate federal income tax withholding"""
        # Adjust for allowances (simplified)
        allowance_amount = Decimal('4300') * allowances  # 2024 allowance amount
        taxable_income = max(Decimal('0'), annual_income - allowance_amount)
        
        # Calculate annual tax using brackets
        annual_tax = self._calculate_tax_from_brackets(
            taxable_income, 
            self.federal_brackets.get(filing_status, self.federal_brackets['single'])
        )
        
        # Return per-pay-period amount
        return annual_tax / pay_periods
    
    def calculate_state_tax(self, annual_income: Decimal, state: str, 
                          allowances: int, pay_periods: int) -> Decimal:
        """Calculate state income tax withholding"""
        state_rate = self.state_tax_rates.get(state, Decimal('0'))
        
        if state_rate == Decimal('0'):
            return Decimal('0')
        
        # Simplified state tax calculation
        allowance_amount = Decimal('2000') * allowances  # Simplified state allowance
        taxable_income = max(Decimal('0'), annual_income - allowance_amount)
        annual_tax = taxable_income * state_rate
        
        return annual_tax / pay_periods
    
    def calculate_social_security_tax(self, gross_pay: Decimal, ytd_wages: Decimal) -> Decimal:
        """Calculate Social Security tax"""
        # Check if YTD wages exceed wage base
        if ytd_wages >= self.social_security_wage_base:
            return Decimal('0')
        
        # Calculate taxable amount for this pay period
        remaining_wages = self.social_security_wage_base - ytd_wages
        taxable_wages = min(gross_pay, remaining_wages)
        
        return taxable_wages * self.social_security_rate
    
    def calculate_medicare_tax(self, gross_pay: Decimal, ytd_wages: Decimal) -> Decimal:
        """Calculate Medicare tax including additional Medicare tax"""
        # Regular Medicare tax (no wage base limit)
        medicare_tax = gross_pay * self.medicare_rate
        
        # Additional Medicare tax for high earners
        if ytd_wages + gross_pay > self.additional_medicare_threshold:
            additional_taxable = min(
                gross_pay, 
                (ytd_wages + gross_pay) - self.additional_medicare_threshold
            )
            medicare_tax += additional_taxable * self.additional_medicare_rate
        
        return medicare_tax
    
    def _calculate_tax_from_brackets(self, income: Decimal, brackets: List[TaxBracket]) -> Decimal:
        """Calculate tax using progressive brackets"""
        tax = Decimal('0')
        
        for bracket in brackets:
            if income <= bracket.min_income:
                break
            
            # Determine taxable amount in this bracket
            bracket_min = bracket.min_income
            bracket_max = bracket.max_income or income
            
            taxable_in_bracket = min(income, bracket_max) - bracket_min
            
            if taxable_in_bracket > 0:
                tax += bracket.base_tax + (taxable_in_bracket * bracket.rate)
            
            if bracket.max_income and income <= bracket.max_income:
                break
        
        return tax

class PayrollEngine:
    """Main payroll processing engine"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.db_pool = None
        self.tax_calculator = TaxCalculator(self.config.get('tax_tables', {}))
        self.scheduler = AsyncIOScheduler()
        
        # Initialize third-party integrations
        if self.config.get('bank_integration', {}).get('enabled'):
            self.bank_client = self._initialize_bank_client()
        
        if self.config.get('tax_service', {}).get('enabled'):
            self.tax_service_client = self._initialize_tax_service()
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize the payroll engine"""
        await self.connect_database()
        await self.create_tables()
        await self.setup_scheduler()
        
        self.scheduler.start()
        logger.info("Payroll engine initialized")
    
    async def shutdown(self):
        """Shutdown the payroll engine"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("Payroll engine shutdown")
    
    async def connect_database(self):
        """Connect to PostgreSQL database"""
        db_config = self.config['database']
        self.db_pool = await asyncpg.create_pool(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database'],
            min_size=2,
            max_size=10
        )
    
    async def create_tables(self):
        """Create database tables for payroll"""
        async with self.db_pool.acquire() as conn:
            # Employees table (extends basic employee info for payroll)
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payroll_employees (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL UNIQUE,
                    employee_number VARCHAR(20) NOT NULL UNIQUE,
                    ssn VARCHAR(11) NOT NULL,
                    pay_type VARCHAR(20) NOT NULL,
                    pay_rate DECIMAL(10,2) NOT NULL,
                    pay_frequency VARCHAR(20) NOT NULL,
                    federal_allowances INTEGER DEFAULT 0,
                    state_allowances INTEGER DEFAULT 0,
                    filing_status VARCHAR(30) NOT NULL,
                    additional_federal_withholding DECIMAL(10,2) DEFAULT 0,
                    additional_state_withholding DECIMAL(10,2) DEFAULT 0,
                    health_insurance DECIMAL(10,2) DEFAULT 0,
                    dental_insurance DECIMAL(10,2) DEFAULT 0,
                    vision_insurance DECIMAL(10,2) DEFAULT 0,
                    retirement_401k DECIMAL(5,2) DEFAULT 0,
                    retirement_401k_amount DECIMAL(10,2) DEFAULT 0,
                    bank_account_number VARCHAR(20),
                    bank_routing_number VARCHAR(9),
                    account_type VARCHAR(10) DEFAULT 'checking',
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Timesheets table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS timesheets (
                    id SERIAL PRIMARY KEY,
                    employee_id INTEGER NOT NULL,
                    pay_period_start DATE NOT NULL,
                    pay_period_end DATE NOT NULL,
                    regular_hours DECIMAL(5,2) DEFAULT 0,
                    overtime_hours DECIMAL(5,2) DEFAULT 0,
                    double_time_hours DECIMAL(5,2) DEFAULT 0,
                    vacation_hours DECIMAL(5,2) DEFAULT 0,
                    sick_hours DECIMAL(5,2) DEFAULT 0,
                    holiday_hours DECIMAL(5,2) DEFAULT 0,
                    approved BOOLEAN DEFAULT FALSE,
                    approved_by INTEGER,
                    approved_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(employee_id, pay_period_start, pay_period_end)
                )
            ''')
            
            # Payroll runs table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payroll_runs (
                    id SERIAL PRIMARY KEY,
                    run_name VARCHAR(255) NOT NULL,
                    pay_period_start DATE NOT NULL,
                    pay_period_end DATE NOT NULL,
                    pay_date DATE NOT NULL,
                    status VARCHAR(20) DEFAULT 'draft',
                    total_gross_pay DECIMAL(12,2) DEFAULT 0,
                    total_net_pay DECIMAL(12,2) DEFAULT 0,
                    total_taxes DECIMAL(12,2) DEFAULT 0,
                    total_employer_costs DECIMAL(12,2) DEFAULT 0,
                    processed_by INTEGER,
                    processed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Payroll calculations table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payroll_calculations (
                    id SERIAL PRIMARY KEY,
                    payroll_run_id INTEGER NOT NULL REFERENCES payroll_runs(id),
                    employee_id INTEGER NOT NULL,
                    
                    -- Earnings
                    regular_pay DECIMAL(10,2) DEFAULT 0,
                    overtime_pay DECIMAL(10,2) DEFAULT 0,
                    double_time_pay DECIMAL(10,2) DEFAULT 0,
                    vacation_pay DECIMAL(10,2) DEFAULT 0,
                    sick_pay DECIMAL(10,2) DEFAULT 0,
                    holiday_pay DECIMAL(10,2) DEFAULT 0,
                    bonus DECIMAL(10,2) DEFAULT 0,
                    commission DECIMAL(10,2) DEFAULT 0,
                    
                    -- Pre-tax deductions
                    health_insurance DECIMAL(10,2) DEFAULT 0,
                    dental_insurance DECIMAL(10,2) DEFAULT 0,
                    vision_insurance DECIMAL(10,2) DEFAULT 0,
                    retirement_401k DECIMAL(10,2) DEFAULT 0,
                    flexible_spending DECIMAL(10,2) DEFAULT 0,
                    
                    -- Tax withholdings
                    federal_income_tax DECIMAL(10,2) DEFAULT 0,
                    state_income_tax DECIMAL(10,2) DEFAULT 0,
                    social_security_tax DECIMAL(10,2) DEFAULT 0,
                    medicare_tax DECIMAL(10,2) DEFAULT 0,
                    unemployment_tax DECIMAL(10,2) DEFAULT 0,
                    disability_tax DECIMAL(10,2) DEFAULT 0,
                    
                    -- Post-tax deductions
                    union_dues DECIMAL(10,2) DEFAULT 0,
                    garnishments DECIMAL(10,2) DEFAULT 0,
                    loan_repayments DECIMAL(10,2) DEFAULT 0,
                    
                    -- Employer contributions
                    employer_social_security DECIMAL(10,2) DEFAULT 0,
                    employer_medicare DECIMAL(10,2) DEFAULT 0,
                    employer_unemployment DECIMAL(10,2) DEFAULT 0,
                    employer_401k_match DECIMAL(10,2) DEFAULT 0,
                    
                    -- Totals
                    gross_pay DECIMAL(10,2) DEFAULT 0,
                    net_pay DECIMAL(10,2) DEFAULT 0,
                    total_taxes DECIMAL(10,2) DEFAULT 0,
                    total_employer_costs DECIMAL(10,2) DEFAULT 0,
                    
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Direct deposit transactions
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS direct_deposit_transactions (
                    id SERIAL PRIMARY KEY,
                    payroll_calculation_id INTEGER NOT NULL REFERENCES payroll_calculations(id),
                    employee_id INTEGER NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    bank_account_number VARCHAR(20),
                    bank_routing_number VARCHAR(9),
                    transaction_id VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'pending',
                    processed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Tax filings table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS payroll_tax_filings (
                    id SERIAL PRIMARY KEY,
                    filing_period_start DATE NOT NULL,
                    filing_period_end DATE NOT NULL,
                    tax_type VARCHAR(50) NOT NULL, -- 'federal_941', 'state_unemployment', etc.
                    filing_status VARCHAR(20) DEFAULT 'draft',
                    total_wages DECIMAL(12,2) DEFAULT 0,
                    total_tax_withheld DECIMAL(12,2) DEFAULT 0,
                    employer_tax DECIMAL(12,2) DEFAULT 0,
                    filing_data JSONB,
                    filed_at TIMESTAMP WITH TIME ZONE,
                    due_date DATE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
    
    async def setup_scheduler(self):
        """Setup scheduled payroll jobs"""
        # Weekly payroll processing (Fridays at 10 AM)
        self.scheduler.add_job(
            self.auto_process_weekly_payroll,
            CronTrigger(day_of_week=4, hour=10, minute=0),  # Friday
            id='weekly_payroll',
            name='Weekly Payroll Processing',
            replace_existing=True
        )
        
        # Bi-weekly payroll processing (every other Friday at 10 AM)
        self.scheduler.add_job(
            self.auto_process_biweekly_payroll,
            CronTrigger(day_of_week=4, hour=10, minute=0, week=2),  # Every 2 weeks on Friday
            id='biweekly_payroll',
            name='Bi-weekly Payroll Processing',
            replace_existing=True
        )
        
        # Monthly payroll processing (last business day at 10 AM)
        self.scheduler.add_job(
            self.auto_process_monthly_payroll,
            CronTrigger(day=-1, hour=10, minute=0),  # Last day of month
            id='monthly_payroll',
            name='Monthly Payroll Processing',
            replace_existing=True
        )
        
        # Tax filing reminders
        self.scheduler.add_job(
            self.check_tax_filing_deadlines,
            CronTrigger(hour=9, minute=0),  # Daily at 9 AM
            id='tax_filing_reminders',
            name='Tax Filing Deadline Reminders',
            replace_existing=True
        )
    
    # Employee Management
    async def create_payroll_employee(self, employee_data: Dict[str, Any]) -> int:
        """Create or update payroll employee record"""
        async with self.db_pool.acquire() as conn:
            employee_id = await conn.fetchval('''
                INSERT INTO payroll_employees 
                (employee_id, employee_number, ssn, pay_type, pay_rate, pay_frequency,
                 federal_allowances, state_allowances, filing_status,
                 additional_federal_withholding, additional_state_withholding,
                 health_insurance, dental_insurance, vision_insurance,
                 retirement_401k, retirement_401k_amount,
                 bank_account_number, bank_routing_number, account_type)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
                ON CONFLICT (employee_id) DO UPDATE SET
                    pay_rate = EXCLUDED.pay_rate,
                    pay_frequency = EXCLUDED.pay_frequency,
                    federal_allowances = EXCLUDED.federal_allowances,
                    state_allowances = EXCLUDED.state_allowances,
                    filing_status = EXCLUDED.filing_status,
                    updated_at = NOW()
                RETURNING id
            ''',
            employee_data['employee_id'], employee_data['employee_number'],
            employee_data['ssn'], employee_data['pay_type'],
            employee_data['pay_rate'], employee_data['pay_frequency'],
            employee_data.get('federal_allowances', 0),
            employee_data.get('state_allowances', 0),
            employee_data['filing_status'],
            employee_data.get('additional_federal_withholding', 0),
            employee_data.get('additional_state_withholding', 0),
            employee_data.get('health_insurance', 0),
            employee_data.get('dental_insurance', 0),
            employee_data.get('vision_insurance', 0),
            employee_data.get('retirement_401k', 0),
            employee_data.get('retirement_401k_amount', 0),
            employee_data.get('bank_account_number'),
            employee_data.get('bank_routing_number'),
            employee_data.get('account_type', 'checking')
            )
            
            return employee_id
    
    async def submit_timesheet(self, timesheet_data: Dict[str, Any]) -> int:
        """Submit employee timesheet"""
        async with self.db_pool.acquire() as conn:
            timesheet_id = await conn.fetchval('''
                INSERT INTO timesheets 
                (employee_id, pay_period_start, pay_period_end,
                 regular_hours, overtime_hours, double_time_hours,
                 vacation_hours, sick_hours, holiday_hours)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (employee_id, pay_period_start, pay_period_end) DO UPDATE SET
                    regular_hours = EXCLUDED.regular_hours,
                    overtime_hours = EXCLUDED.overtime_hours,
                    double_time_hours = EXCLUDED.double_time_hours,
                    vacation_hours = EXCLUDED.vacation_hours,
                    sick_hours = EXCLUDED.sick_hours,
                    holiday_hours = EXCLUDED.holiday_hours,
                    updated_at = NOW()
                RETURNING id
            ''',
            timesheet_data['employee_id'],
            timesheet_data['pay_period_start'],
            timesheet_data['pay_period_end'],
            timesheet_data.get('regular_hours', 0),
            timesheet_data.get('overtime_hours', 0),
            timesheet_data.get('double_time_hours', 0),
            timesheet_data.get('vacation_hours', 0),
            timesheet_data.get('sick_hours', 0),
            timesheet_data.get('holiday_hours', 0)
            )
            
            return timesheet_id
    
    async def approve_timesheet(self, timesheet_id: int, approved_by: int) -> bool:
        """Approve employee timesheet"""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute('''
                UPDATE timesheets 
                SET approved = TRUE, approved_by = $1, approved_at = NOW()
                WHERE id = $2
            ''', approved_by, timesheet_id)
            
            return result != 'UPDATE 0'
    
    # Payroll Processing
    async def create_payroll_run(self, run_data: Dict[str, Any]) -> int:
        """Create a new payroll run"""
        async with self.db_pool.acquire() as conn:
            payroll_run_id = await conn.fetchval('''
                INSERT INTO payroll_runs 
                (run_name, pay_period_start, pay_period_end, pay_date, processed_by)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            ''',
            run_data['run_name'],
            run_data['pay_period_start'],
            run_data['pay_period_end'],
            run_data['pay_date'],
            run_data.get('processed_by')
            )
            
            return payroll_run_id
    
    async def calculate_payroll(self, payroll_run_id: int) -> Dict[str, Any]:
        """Calculate payroll for all employees in a payroll run"""
        logger.info(f"Starting payroll calculation for run {payroll_run_id}")
        
        async with self.db_pool.acquire() as conn:
            # Get payroll run details
            payroll_run = await conn.fetchrow('''
                SELECT * FROM payroll_runs WHERE id = $1
            ''', payroll_run_id)
            
            if not payroll_run:
                raise ValueError(f"Payroll run {payroll_run_id} not found")
            
            # Get active employees
            employees = await conn.fetch('''
                SELECT pe.*, e.first_name, e.last_name, e.email, e.hire_date, e.state
                FROM payroll_employees pe
                JOIN employees e ON pe.employee_id = e.id
                WHERE e.status = 'active'
            ''')
            
            calculations = []
            total_gross_pay = Decimal('0')
            total_net_pay = Decimal('0')
            total_taxes = Decimal('0')
            total_employer_costs = Decimal('0')
            
            for employee_row in employees:
                try:
                    # Create Employee object
                    employee = Employee(
                        id=employee_row['employee_id'],
                        employee_number=employee_row['employee_number'],
                        first_name=employee_row['first_name'],
                        last_name=employee_row['last_name'],
                        email=employee_row['email'],
                        ssn=employee_row['ssn'],
                        hire_date=employee_row['hire_date'],
                        status=EmployeeStatus.ACTIVE,
                        pay_type=PayType(employee_row['pay_type']),
                        pay_rate=employee_row['pay_rate'],
                        pay_frequency=PayrollFrequency(employee_row['pay_frequency']),
                        federal_allowances=employee_row['federal_allowances'],
                        state_allowances=employee_row['state_allowances'],
                        filing_status=employee_row['filing_status'],
                        additional_federal_withholding=employee_row['additional_federal_withholding'],
                        additional_state_withholding=employee_row['additional_state_withholding'],
                        health_insurance=employee_row['health_insurance'],
                        dental_insurance=employee_row['dental_insurance'],
                        vision_insurance=employee_row['vision_insurance'],
                        retirement_401k=employee_row['retirement_401k'],
                        retirement_401k_amount=employee_row['retirement_401k_amount'],
                        state=employee_row['state']
                    )
                    
                    # Calculate payroll for this employee
                    calculation = await self._calculate_employee_payroll(
                        employee, 
                        payroll_run['pay_period_start'],
                        payroll_run['pay_period_end']
                    )
                    
                    # Store calculation in database
                    await self._store_payroll_calculation(payroll_run_id, calculation)
                    
                    calculations.append(calculation)
                    total_gross_pay += calculation.gross_pay
                    total_net_pay += calculation.net_pay
                    total_taxes += calculation.total_taxes
                    total_employer_costs += calculation.total_employer_costs
                    
                except Exception as e:
                    logger.error(f"Failed to calculate payroll for employee {employee_row['employee_id']}: {e}")
            
            # Update payroll run totals
            await conn.execute('''
                UPDATE payroll_runs 
                SET total_gross_pay = $1, total_net_pay = $2, 
                    total_taxes = $3, total_employer_costs = $4,
                    status = 'processing'
                WHERE id = $5
            ''', total_gross_pay, total_net_pay, total_taxes, total_employer_costs, payroll_run_id)
            
            logger.info(f"Payroll calculation completed for {len(calculations)} employees")
            
            return {
                'payroll_run_id': payroll_run_id,
                'employee_count': len(calculations),
                'total_gross_pay': float(total_gross_pay),
                'total_net_pay': float(total_net_pay),
                'total_taxes': float(total_taxes),
                'total_employer_costs': float(total_employer_costs)
            }
    
    async def _calculate_employee_payroll(self, employee: Employee, 
                                        pay_period_start: date, 
                                        pay_period_end: date) -> PayrollCalculation:
        """Calculate payroll for a single employee"""
        calculation = PayrollCalculation(
            employee=employee,
            pay_period_start=pay_period_start,
            pay_period_end=pay_period_end
        )
        
        # Get timesheet data
        timesheet = await self._get_employee_timesheet(
            employee.id, pay_period_start, pay_period_end
        )
        
        # Calculate earnings
        await self._calculate_earnings(calculation, timesheet)
        
        # Calculate pre-tax deductions
        await self._calculate_pre_tax_deductions(calculation)
        
        # Calculate taxes
        await self._calculate_taxes(calculation)
        
        # Calculate post-tax deductions
        await self._calculate_post_tax_deductions(calculation)
        
        # Calculate employer contributions
        await self._calculate_employer_contributions(calculation)
        
        return calculation
    
    async def _get_employee_timesheet(self, employee_id: int, 
                                    pay_period_start: date, 
                                    pay_period_end: date) -> Optional[Timesheet]:
        """Get approved timesheet for employee and pay period"""
        async with self.db_pool.acquire() as conn:
            timesheet_row = await conn.fetchrow('''
                SELECT * FROM timesheets 
                WHERE employee_id = $1 
                AND pay_period_start = $2 
                AND pay_period_end = $3
                AND approved = TRUE
            ''', employee_id, pay_period_start, pay_period_end)
            
            if not timesheet_row:
                return None
            
            return Timesheet(
                employee_id=timesheet_row['employee_id'],
                pay_period_start=timesheet_row['pay_period_start'],
                pay_period_end=timesheet_row['pay_period_end'],
                regular_hours=timesheet_row['regular_hours'],
                overtime_hours=timesheet_row['overtime_hours'],
                double_time_hours=timesheet_row['double_time_hours'],
                vacation_hours=timesheet_row['vacation_hours'],
                sick_hours=timesheet_row['sick_hours'],
                holiday_hours=timesheet_row['holiday_hours'],
                approved=timesheet_row['approved'],
                approved_by=timesheet_row['approved_by'],
                approved_at=timesheet_row['approved_at']
            )
    
    async def _calculate_earnings(self, calculation: PayrollCalculation, 
                                timesheet: Optional[Timesheet]):
        """Calculate employee earnings"""
        employee = calculation.employee
        
        if employee.pay_type == PayType.SALARY:
            # Salary calculation
            pay_periods_per_year = self._get_pay_periods_per_year(employee.pay_frequency)
            calculation.regular_pay = employee.pay_rate / pay_periods_per_year
            
        elif employee.pay_type == PayType.HOURLY and timesheet:
            # Hourly calculation
            regular_rate = employee.pay_rate
            overtime_rate = regular_rate * Decimal('1.5')
            double_time_rate = regular_rate * Decimal('2.0')
            
            calculation.regular_pay = timesheet.regular_hours * regular_rate
            calculation.overtime_pay = timesheet.overtime_hours * overtime_rate
            calculation.double_time_pay = timesheet.double_time_hours * double_time_rate
            calculation.vacation_pay = timesheet.vacation_hours * regular_rate
            calculation.sick_pay = timesheet.sick_hours * regular_rate
            calculation.holiday_pay = timesheet.holiday_hours * regular_rate
    
    async def _calculate_pre_tax_deductions(self, calculation: PayrollCalculation):
        """Calculate pre-tax deductions"""
        employee = calculation.employee
        
        # Insurance deductions
        calculation.health_insurance = employee.health_insurance
        calculation.dental_insurance = employee.dental_insurance
        calculation.vision_insurance = employee.vision_insurance
        
        # 401k contribution
        if employee.retirement_401k > 0:
            calculation.retirement_401k = calculation.gross_pay * (employee.retirement_401k / Decimal('100'))
        else:
            calculation.retirement_401k = employee.retirement_401k_amount
    
    async def _calculate_taxes(self, calculation: PayrollCalculation):
        """Calculate tax withholdings"""
        employee = calculation.employee
        
        # Get YTD wages for tax calculations
        ytd_wages = await self._get_ytd_wages(employee.id, calculation.pay_period_end)
        
        # Estimate annual income for tax calculations
        pay_periods_per_year = self._get_pay_periods_per_year(employee.pay_frequency)
        annual_income = calculation.taxable_income * pay_periods_per_year
        
        # Federal income tax
        calculation.federal_income_tax = self.tax_calculator.calculate_federal_tax(
            annual_income, employee.filing_status, employee.federal_allowances, pay_periods_per_year
        ) + employee.additional_federal_withholding
        
        # State income tax
        calculation.state_income_tax = self.tax_calculator.calculate_state_tax(
            annual_income, employee.state, employee.state_allowances, pay_periods_per_year
        ) + employee.additional_state_withholding
        
        # Social Security tax
        calculation.social_security_tax = self.tax_calculator.calculate_social_security_tax(
            calculation.taxable_income, ytd_wages
        )
        
        # Medicare tax
        calculation.medicare_tax = self.tax_calculator.calculate_medicare_tax(
            calculation.taxable_income, ytd_wages
        )
    
    async def _calculate_post_tax_deductions(self, calculation: PayrollCalculation):
        """Calculate post-tax deductions"""
        # These would be configurable per employee
        # For now, using placeholder values
        calculation.union_dues = Decimal('0')
        calculation.garnishments = Decimal('0')
        calculation.loan_repayments = Decimal('0')
    
    async def _calculate_employer_contributions(self, calculation: PayrollCalculation):
        """Calculate employer contributions and taxes"""
        # Employer Social Security (matches employee contribution)
        calculation.employer_social_security = calculation.social_security_tax
        
        # Employer Medicare (matches employee contribution)
        calculation.employer_medicare = calculation.medicare_tax
        
        # Unemployment tax (simplified - would vary by state)
        calculation.employer_unemployment = calculation.taxable_income * Decimal('0.006')
        
        # 401k match (simplified - would be configurable)
        if calculation.retirement_401k > 0:
            match_rate = Decimal('0.50')  # 50% match up to 3%
            max_match = calculation.gross_pay * Decimal('0.03')
            calculation.employer_401k_match = min(
                calculation.retirement_401k * match_rate,
                max_match
            )
    
    def _get_pay_periods_per_year(self, frequency: PayrollFrequency) -> Decimal:
        """Get number of pay periods per year"""
        if frequency == PayrollFrequency.WEEKLY:
            return Decimal('52')
        elif frequency == PayrollFrequency.BIWEEKLY:
            return Decimal('26')
        elif frequency == PayrollFrequency.SEMIMONTHLY:
            return Decimal('24')
        elif frequency == PayrollFrequency.MONTHLY:
            return Decimal('12')
        else:
            return Decimal('26')  # Default to biweekly
    
    async def _get_ytd_wages(self, employee_id: int, as_of_date: date) -> Decimal:
        """Get year-to-date wages for an employee"""
        year_start = date(as_of_date.year, 1, 1)
        
        async with self.db_pool.acquire() as conn:
            result = await conn.fetchval('''
                SELECT COALESCE(SUM(pc.gross_pay), 0)
                FROM payroll_calculations pc
                JOIN payroll_runs pr ON pc.payroll_run_id = pr.id
                WHERE pc.employee_id = $1
                AND pr.pay_period_end >= $2
                AND pr.pay_period_end < $3
                AND pr.status = 'paid'
            ''', employee_id, year_start, as_of_date)
            
            return result or Decimal('0')
    
    async def _store_payroll_calculation(self, payroll_run_id: int, 
                                       calculation: PayrollCalculation):
        """Store payroll calculation in database"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO payroll_calculations 
                (payroll_run_id, employee_id,
                 regular_pay, overtime_pay, double_time_pay, vacation_pay, sick_pay, holiday_pay,
                 bonus, commission, health_insurance, dental_insurance, vision_insurance,
                 retirement_401k, flexible_spending, federal_income_tax, state_income_tax,
                 social_security_tax, medicare_tax, unemployment_tax, disability_tax,
                 union_dues, garnishments, loan_repayments,
                 employer_social_security, employer_medicare, employer_unemployment, employer_401k_match,
                 gross_pay, net_pay, total_taxes, total_employer_costs)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32)
            ''',
            payroll_run_id, calculation.employee.id,
            calculation.regular_pay, calculation.overtime_pay, calculation.double_time_pay,
            calculation.vacation_pay, calculation.sick_pay, calculation.holiday_pay,
            calculation.bonus, calculation.commission, calculation.health_insurance,
            calculation.dental_insurance, calculation.vision_insurance,
            calculation.retirement_401k, calculation.flexible_spending,
            calculation.federal_income_tax, calculation.state_income_tax,
            calculation.social_security_tax, calculation.medicare_tax,
            calculation.unemployment_tax, calculation.disability_tax,
            calculation.union_dues, calculation.garnishments, calculation.loan_repayments,
            calculation.employer_social_security, calculation.employer_medicare,
            calculation.employer_unemployment, calculation.employer_401k_match,
            calculation.gross_pay, calculation.net_pay, calculation.total_taxes,
            calculation.total_employer_costs
            )
    
    # Direct Deposit Processing
    async def process_direct_deposits(self, payroll_run_id: int) -> Dict[str, Any]:
        """Process direct deposit transactions"""
        logger.info(f"Processing direct deposits for payroll run {payroll_run_id}")
        
        results = {
            'total_amount': Decimal('0'),
            'successful_deposits': 0,
            'failed_deposits': 0,
            'transactions': []
        }
        
        async with self.db_pool.acquire() as conn:
            # Get payroll calculations with bank info
            calculations = await conn.fetch('''
                SELECT pc.*, pe.bank_account_number, pe.bank_routing_number, pe.account_type,
                       e.first_name, e.last_name, e.email
                FROM payroll_calculations pc
                JOIN payroll_employees pe ON pc.employee_id = pe.employee_id
                JOIN employees e ON pc.employee_id = e.id
                WHERE pc.payroll_run_id = $1
                AND pe.bank_account_number IS NOT NULL
                AND pe.bank_routing_number IS NOT NULL
            ''', payroll_run_id)
            
            for calc in calculations:
                try:
                    # Create direct deposit transaction
                    transaction_id = await self._create_direct_deposit_transaction(calc)
                    
                    # Process with bank (mock implementation)
                    success = await self._process_bank_transaction(
                        calc['bank_routing_number'],
                        calc['bank_account_number'],
                        float(calc['net_pay']),
                        f"{calc['first_name']} {calc['last_name']}"
                    )
                    
                    if success:
                        results['successful_deposits'] += 1
                        results['total_amount'] += calc['net_pay']
                        
                        # Update transaction status
                        await conn.execute('''
                            UPDATE direct_deposit_transactions 
                            SET status = 'processed', processed_at = NOW()
                            WHERE id = $1
                        ''', transaction_id)
                    else:
                        results['failed_deposits'] += 1
                        
                        await conn.execute('''
                            UPDATE direct_deposit_transactions 
                            SET status = 'failed'
                            WHERE id = $1
                        ''', transaction_id)
                    
                    results['transactions'].append({
                        'employee_name': f"{calc['first_name']} {calc['last_name']}",
                        'amount': float(calc['net_pay']),
                        'status': 'processed' if success else 'failed'
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to process direct deposit for employee {calc['employee_id']}: {e}")
                    results['failed_deposits'] += 1
        
        logger.info(f"Direct deposit processing completed: {results['successful_deposits']} successful, {results['failed_deposits']} failed")
        
        return results
    
    async def _create_direct_deposit_transaction(self, calculation: Dict[str, Any]) -> int:
        """Create direct deposit transaction record"""
        async with self.db_pool.acquire() as conn:
            transaction_id = await conn.fetchval('''
                INSERT INTO direct_deposit_transactions 
                (payroll_calculation_id, employee_id, amount, 
                 bank_account_number, bank_routing_number)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            ''',
            calculation['id'], calculation['employee_id'], calculation['net_pay'],
            calculation['bank_account_number'], calculation['bank_routing_number']
            )
            
            return transaction_id
    
    async def _process_bank_transaction(self, routing_number: str, account_number: str,
                                      amount: float, employee_name: str) -> bool:
        """Process bank transaction (mock implementation)"""
        # This would integrate with actual banking API
        logger.info(f"Processing bank transfer: ${amount:.2f} to {employee_name}")
        
        # Mock success/failure (in real implementation, this would call bank API)
        import random
        return random.random() > 0.05  # 95% success rate
    
    # Automated Payroll Processing
    async def auto_process_weekly_payroll(self):
        """Automatically process weekly payroll"""
        logger.info("Starting automatic weekly payroll processing")
        # Implementation would check for employees with weekly pay frequency
        # and create/process payroll runs
    
    async def auto_process_biweekly_payroll(self):
        """Automatically process bi-weekly payroll"""
        logger.info("Starting automatic bi-weekly payroll processing")
        # Implementation would check for employees with bi-weekly pay frequency
    
    async def auto_process_monthly_payroll(self):
        """Automatically process monthly payroll"""
        logger.info("Starting automatic monthly payroll processing")
        # Implementation would check for employees with monthly pay frequency
    
    async def check_tax_filing_deadlines(self):
        """Check for upcoming tax filing deadlines"""
        logger.info("Checking tax filing deadlines")
        # Implementation would check for upcoming quarterly/annual filings
    
    # Reporting
    async def generate_payroll_report(self, payroll_run_id: int) -> Dict[str, Any]:
        """Generate comprehensive payroll report"""
        async with self.db_pool.acquire() as conn:
            # Get payroll run summary
            run_summary = await conn.fetchrow('''
                SELECT * FROM payroll_runs WHERE id = $1
            ''', payroll_run_id)
            
            # Get detailed calculations
            calculations = await conn.fetch('''
                SELECT pc.*, e.first_name, e.last_name, pe.employee_number
                FROM payroll_calculations pc
                JOIN employees e ON pc.employee_id = e.id
                JOIN payroll_employees pe ON pc.employee_id = pe.employee_id
                WHERE pc.payroll_run_id = $1
                ORDER BY e.last_name, e.first_name
            ''', payroll_run_id)
            
            return {
                'run_summary': dict(run_summary),
                'employee_calculations': [dict(calc) for calc in calculations],
                'total_employees': len(calculations)
            }
    
    # Third-party Integrations
    def _initialize_bank_client(self):
        """Initialize bank API client"""
        # This would initialize actual bank API client
        logger.info("Initializing bank API client")
        return None
    
    def _initialize_tax_service(self):
        """Initialize tax service API client"""
        # This would initialize tax service API client (like ADP, etc.)
        logger.info("Initializing tax service API client")
        return None

def main():
    """Example usage"""
    async def run_payroll_example():
        config_path = "payroll_config.yml"
        payroll_engine = PayrollEngine(config_path)
        
        try:
            await payroll_engine.initialize()
            
            # Create sample payroll run
            run_data = {
                'run_name': 'Weekly Payroll - Week Ending 2024-01-15',
                'pay_period_start': date(2024, 1, 8),
                'pay_period_end': date(2024, 1, 14),
                'pay_date': date(2024, 1, 19),
                'processed_by': 1
            }
            
            payroll_run_id = await payroll_engine.create_payroll_run(run_data)
            print(f"Created payroll run: {payroll_run_id}")
            
            # Calculate payroll
            results = await payroll_engine.calculate_payroll(payroll_run_id)
            print(f"Payroll calculated: {results}")
            
        finally:
            await payroll_engine.shutdown()
    
    asyncio.run(run_payroll_example())

if __name__ == '__main__':
    main()