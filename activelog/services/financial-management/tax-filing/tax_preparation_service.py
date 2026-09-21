#!/usr/bin/env python3
"""
Advanced Tax Filing Preparation Service for ActiveLog
Handles tax form generation, compliance, and filing automation
"""

import asyncio
import json
import logging
import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Tuple
import asyncpg
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import yaml
from enum import Enum
import uuid
import requests
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
import boto3
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TaxFormType(Enum):
    FORM_941 = "941"  # Quarterly Federal Tax Return
    FORM_940 = "940"  # Federal Unemployment Tax
    FORM_W2 = "W-2"   # Employee Wage Statement
    FORM_W3 = "W-3"   # Transmittal of Wage and Tax Statements
    FORM_1099 = "1099"  # Miscellaneous Income
    FORM_1120 = "1120"  # Corporate Income Tax
    STATE_QUARTERLY = "state_quarterly"
    STATE_ANNUAL = "state_annual"

class FilingStatus(Enum):
    DRAFT = "draft"
    READY = "ready"
    FILED = "filed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    AMENDED = "amended"

class TaxPeriod(Enum):
    QUARTERLY = "quarterly"
    MONTHLY = "monthly"
    ANNUAL = "annual"
    SEMIANNUAL = "semiannual"

@dataclass
class TaxForm:
    """Base tax form structure"""
    form_type: TaxFormType
    tax_year: int
    filing_period: str  # "Q1 2024", "2024", etc.
    due_date: date
    status: FilingStatus
    form_data: Dict[str, Any]
    filing_method: str = "electronic"  # electronic, paper
    created_at: Optional[datetime] = None
    filed_at: Optional[datetime] = None
    confirmation_number: Optional[str] = None

@dataclass
class Form941Data:
    """Form 941 Quarterly Federal Tax Return data"""
    ein: str
    business_name: str
    address: Dict[str, str]
    quarter: int
    year: int
    
    # Employee counts
    number_of_employees: int
    
    # Wages and compensation
    total_wages: Decimal
    federal_income_tax_withheld: Decimal
    taxable_social_security_wages: Decimal
    taxable_medicare_wages: Decimal
    
    # Tax calculations
    social_security_tax: Decimal
    medicare_tax: Decimal
    total_taxes: Decimal
    total_deposits: Decimal
    
    # Adjustments
    current_quarter_adjustments: Decimal = Decimal('0')
    prior_quarter_adjustments: Decimal = Decimal('0')
    
    # Balance due or overpayment
    balance_due: Decimal = Decimal('0')
    overpayment: Decimal = Decimal('0')

@dataclass
class FormW2Data:
    """Form W-2 Wage and Tax Statement data"""
    employer_ein: str
    employer_name: str
    employer_address: Dict[str, str]
    
    employee_ssn: str
    employee_name: str
    employee_address: Dict[str, str]
    
    # Box amounts
    wages_tips_compensation: Decimal  # Box 1
    federal_income_tax_withheld: Decimal  # Box 2
    social_security_wages: Decimal  # Box 3
    social_security_tax_withheld: Decimal  # Box 4
    medicare_wages: Decimal  # Box 5
    medicare_tax_withheld: Decimal  # Box 6
    social_security_tips: Decimal = Decimal('0')  # Box 7
    allocated_tips: Decimal = Decimal('0')  # Box 8
    dependent_care_benefits: Decimal = Decimal('0')  # Box 10
    nonqualified_plans: Decimal = Decimal('0')  # Box 11
    
    # State and local taxes
    state_wages: Dict[str, Decimal] = None
    state_tax: Dict[str, Decimal] = None
    local_wages: Dict[str, Decimal] = None
    local_tax: Dict[str, Decimal] = None
    
    # Other information
    retirement_plan: bool = False  # Box 13
    third_party_sick_pay: bool = False  # Box 13

class IRSElectronicFilingService:
    """Service for IRS electronic filing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.base_url = config.get('irs_api_base_url', 'https://efile.irs.gov/api/v1')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
        self.test_mode = config.get('test_mode', True)
        
    async def authenticate(self) -> str:
        """Authenticate with IRS e-file system"""
        auth_url = f"{self.base_url}/auth/token"
        
        auth_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': 'efile_submit efile_status'
        }
        
        try:
            # Mock authentication for demo
            logger.info("Authenticating with IRS e-file system")
            return f"mock_token_{uuid.uuid4().hex[:16]}"
            
        except Exception as e:
            logger.error(f"IRS authentication failed: {e}")
            raise
    
    async def submit_form(self, form_xml: str, form_type: TaxFormType) -> Dict[str, Any]:
        """Submit tax form electronically"""
        token = await self.authenticate()
        
        submit_url = f"{self.base_url}/submit"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/xml'
        }
        
        try:
            # Mock submission for demo
            confirmation_number = f"IRS{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:8].upper()}"
            
            logger.info(f"Submitted {form_type.value} form electronically")
            
            return {
                'status': 'submitted',
                'confirmation_number': confirmation_number,
                'submission_id': f"SUB{uuid.uuid4().hex[:12].upper()}",
                'estimated_processing_time': '24-48 hours'
            }
            
        except Exception as e:
            logger.error(f"Form submission failed: {e}")
            raise
    
    async def check_status(self, submission_id: str) -> Dict[str, Any]:
        """Check filing status"""
        token = await self.authenticate()
        
        status_url = f"{self.base_url}/status/{submission_id}"
        headers = {'Authorization': f'Bearer {token}'}
        
        try:
            # Mock status check
            statuses = ['submitted', 'processing', 'accepted', 'rejected']
            import random
            status = random.choice(statuses)
            
            return {
                'submission_id': submission_id,
                'status': status,
                'last_updated': datetime.now().isoformat(),
                'messages': []
            }
            
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            raise

class TaxFormGenerator:
    """Generates tax forms in various formats"""
    
    def __init__(self, templates_dir: str):
        self.templates_dir = templates_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=False
        )
        
        # Add custom filters
        self.jinja_env.filters['currency'] = self.format_currency
        self.jinja_env.filters['date'] = self.format_date
    
    def format_currency(self, amount: Decimal) -> str:
        """Format currency amounts"""
        return f"{amount:,.2f}"
    
    def format_date(self, date_obj: date, format_str: str = "%m/%d/%Y") -> str:
        """Format dates"""
        return date_obj.strftime(format_str)
    
    def generate_form_941_xml(self, form_data: Form941Data) -> str:
        """Generate Form 941 XML for electronic filing"""
        template = self.jinja_env.get_template('form_941.xml')
        
        return template.render(
            form_data=form_data,
            generated_at=datetime.now()
        )
    
    def generate_form_941_pdf(self, form_data: Form941Data, output_path: Optional[str] = None) -> bytes:
        """Generate Form 941 PDF"""
        from io import BytesIO
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # Form header
        title = Paragraph("Form 941 - Employer's QUARTERLY Federal Tax Return", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Business information
        business_info = [
            ['Employer identification number (EIN)', form_data.ein],
            ['Name (not your trade name)', form_data.business_name],
            ['Trade name (if any)', ''],
            ['Address', f"{form_data.address.get('street', '')}\n{form_data.address.get('city', '')}, {form_data.address.get('state', '')} {form_data.address.get('zip', '')}"]
        ]
        
        business_table = Table(business_info, colWidths=[3*inch, 4*inch])
        business_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(business_table)
        story.append(Spacer(1, 20))
        
        # Quarter and year
        quarter_info = Paragraph(f"Quarter: Q{form_data.quarter} {form_data.year}", styles['Normal'])
        story.append(quarter_info)
        story.append(Spacer(1, 20))
        
        # Tax calculations table
        tax_data = [
            ['Description', 'Amount'],
            ['Number of employees who received wages', str(form_data.number_of_employees)],
            ['Wages, tips, and other compensation', f"${form_data.total_wages:,.2f}"],
            ['Federal income tax withheld from wages', f"${form_data.federal_income_tax_withheld:,.2f}"],
            ['Taxable social security wages', f"${form_data.taxable_social_security_wages:,.2f}"],
            ['Social security tax', f"${form_data.social_security_tax:,.2f}"],
            ['Taxable Medicare wages & tips', f"${form_data.taxable_medicare_wages:,.2f}"],
            ['Medicare tax', f"${form_data.medicare_tax:,.2f}"],
            ['Total taxes after adjustments', f"${form_data.total_taxes:,.2f}"],
            ['Total deposits for this quarter', f"${form_data.total_deposits:,.2f}"],
        ]
        
        if form_data.balance_due > 0:
            tax_data.append(['Balance due', f"${form_data.balance_due:,.2f}"])
        elif form_data.overpayment > 0:
            tax_data.append(['Overpayment', f"${form_data.overpayment:,.2f}"])
        
        tax_table = Table(tax_data, colWidths=[4*inch, 2*inch])
        tax_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ]))
        
        story.append(tax_table)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes
    
    def generate_form_w2_xml(self, w2_data: List[FormW2Data]) -> str:
        """Generate Form W-2 XML for electronic filing"""
        template = self.jinja_env.get_template('form_w2.xml')
        
        return template.render(
            w2_records=w2_data,
            generated_at=datetime.now()
        )
    
    def generate_form_w2_pdf(self, w2_data: FormW2Data, output_path: Optional[str] = None) -> bytes:
        """Generate individual Form W-2 PDF"""
        from io import BytesIO
        buffer = BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        styles = getSampleStyleSheet()
        story = []
        
        # W-2 Header
        title = Paragraph("Form W-2 - Wage and Tax Statement", styles['Title'])
        story.append(title)
        story.append(Spacer(1, 20))
        
        # Employer information
        employer_info = [
            ['a. Employee\'s social security number', w2_data.employee_ssn],
            ['b. Employer identification number (EIN)', w2_data.employer_ein],
            ['c. Employer\'s name, address, and ZIP code', 
             f"{w2_data.employer_name}\n{w2_data.employer_address.get('street', '')}\n{w2_data.employer_address.get('city', '')}, {w2_data.employer_address.get('state', '')} {w2_data.employer_address.get('zip', '')}"],
            ['e. Employee\'s first name and initial, last name',
             w2_data.employee_name],
            ['f. Employee\'s address and ZIP code',
             f"{w2_data.employee_address.get('street', '')}\n{w2_data.employee_address.get('city', '')}, {w2_data.employee_address.get('state', '')} {w2_data.employee_address.get('zip', '')}"]
        ]
        
        employer_table = Table(employer_info, colWidths=[2.5*inch, 4.5*inch])
        employer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        story.append(employer_table)
        story.append(Spacer(1, 20))
        
        # Wage and tax information
        wage_data = [
            ['Box', 'Description', 'Amount'],
            ['1', 'Wages, tips, other compensation', f"${w2_data.wages_tips_compensation:,.2f}"],
            ['2', 'Federal income tax withheld', f"${w2_data.federal_income_tax_withheld:,.2f}"],
            ['3', 'Social security wages', f"${w2_data.social_security_wages:,.2f}"],
            ['4', 'Social security tax withheld', f"${w2_data.social_security_tax_withheld:,.2f}"],
            ['5', 'Medicare wages and tips', f"${w2_data.medicare_wages:,.2f}"],
            ['6', 'Medicare tax withheld', f"${w2_data.medicare_tax_withheld:,.2f}"],
        ]
        
        if w2_data.social_security_tips > 0:
            wage_data.append(['7', 'Social security tips', f"${w2_data.social_security_tips:,.2f}"])
        
        if w2_data.allocated_tips > 0:
            wage_data.append(['8', 'Allocated tips', f"${w2_data.allocated_tips:,.2f}"])
        
        wage_table = Table(wage_data, colWidths=[0.5*inch, 3*inch, 2*inch])
        wage_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ALIGN', (2, 1), (2, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white]),
        ]))
        
        story.append(wage_table)
        
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        if output_path:
            with open(output_path, 'wb') as f:
                f.write(pdf_bytes)
        
        return pdf_bytes

class TaxPreparationService:
    """Main tax filing preparation service"""
    
    def __init__(self, config_path: str):
        self.config = self.load_config(config_path)
        self.db_pool = None
        self.form_generator = TaxFormGenerator(self.config['templates']['directory'])
        self.irs_service = IRSElectronicFilingService(self.config.get('irs_efile', {}))
        
        # Initialize state tax services
        self.state_services = {}
        for state_code, state_config in self.config.get('state_tax_services', {}).items():
            self.state_services[state_code] = self._initialize_state_service(state_code, state_config)
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def initialize(self):
        """Initialize the tax preparation service"""
        await self.connect_database()
        await self.create_tables()
        logger.info("Tax preparation service initialized")
    
    async def shutdown(self):
        """Shutdown the service"""
        if self.db_pool:
            await self.db_pool.close()
        logger.info("Tax preparation service shutdown")
    
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
        """Create database tables for tax filing"""
        async with self.db_pool.acquire() as conn:
            # Tax forms table
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tax_forms (
                    id SERIAL PRIMARY KEY,
                    form_id UUID UNIQUE DEFAULT gen_random_uuid(),
                    form_type VARCHAR(20) NOT NULL,
                    tax_year INTEGER NOT NULL,
                    filing_period VARCHAR(20) NOT NULL,
                    due_date DATE NOT NULL,
                    status VARCHAR(20) DEFAULT 'draft',
                    form_data JSONB NOT NULL,
                    filing_method VARCHAR(20) DEFAULT 'electronic',
                    confirmation_number VARCHAR(50),
                    filed_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Tax filing calendar
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tax_filing_calendar (
                    id SERIAL PRIMARY KEY,
                    form_type VARCHAR(20) NOT NULL,
                    filing_period VARCHAR(20) NOT NULL,
                    due_date DATE NOT NULL,
                    tax_year INTEGER NOT NULL,
                    reminder_sent BOOLEAN DEFAULT FALSE,
                    reminder_sent_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
            
            # Electronic filing log
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS efile_submissions (
                    id SERIAL PRIMARY KEY,
                    form_id UUID NOT NULL REFERENCES tax_forms(form_id),
                    submission_id VARCHAR(50),
                    status VARCHAR(20) DEFAULT 'submitted',
                    response_data JSONB,
                    error_messages TEXT[],
                    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    last_status_check TIMESTAMP WITH TIME ZONE
                )
            ''')
            
            # Tax compliance alerts
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS tax_compliance_alerts (
                    id SERIAL PRIMARY KEY,
                    alert_type VARCHAR(50) NOT NULL,
                    severity VARCHAR(20) NOT NULL,
                    title VARCHAR(255) NOT NULL,
                    description TEXT,
                    due_date DATE,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TIMESTAMP WITH TIME ZONE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            ''')
    
    # Form 941 Processing
    async def prepare_form_941(self, quarter: int, year: int) -> str:
        """Prepare Form 941 quarterly return"""
        logger.info(f"Preparing Form 941 for Q{quarter} {year}")
        
        # Gather payroll data for the quarter
        payroll_data = await self._gather_quarterly_payroll_data(quarter, year)
        
        # Calculate quarter dates
        quarter_dates = self._get_quarter_dates(quarter, year)
        
        # Get company information
        company_info = await self._get_company_information()
        
        # Create Form 941 data structure
        form_941_data = Form941Data(
            ein=company_info['ein'],
            business_name=company_info['name'],
            address=company_info['address'],
            quarter=quarter,
            year=year,
            number_of_employees=payroll_data['employee_count'],
            total_wages=payroll_data['total_wages'],
            federal_income_tax_withheld=payroll_data['federal_tax_withheld'],
            taxable_social_security_wages=payroll_data['social_security_wages'],
            taxable_medicare_wages=payroll_data['medicare_wages'],
            social_security_tax=payroll_data['social_security_tax'],
            medicare_tax=payroll_data['medicare_tax'],
            total_taxes=payroll_data['total_taxes'],
            total_deposits=payroll_data['total_deposits']
        )
        
        # Calculate balance due or overpayment
        balance = form_941_data.total_taxes - form_941_data.total_deposits
        if balance > 0:
            form_941_data.balance_due = balance
        else:
            form_941_data.overpayment = abs(balance)
        
        # Create tax form record
        form_id = await self._create_tax_form_record(
            TaxFormType.FORM_941,
            year,
            f"Q{quarter} {year}",
            quarter_dates['due_date'],
            asdict(form_941_data)
        )
        
        # Generate PDF
        pdf_bytes = self.form_generator.generate_form_941_pdf(form_941_data)
        
        # Store form file
        file_path = await self._store_form_file(form_id, 'pdf', pdf_bytes)
        
        logger.info(f"Form 941 prepared successfully: {form_id}")
        
        return form_id
    
    async def _gather_quarterly_payroll_data(self, quarter: int, year: int) -> Dict[str, Any]:
        """Gather payroll data for quarterly tax forms"""
        quarter_dates = self._get_quarter_dates(quarter, year)
        
        async with self.db_pool.acquire() as conn:
            # Get payroll summary for the quarter
            payroll_summary = await conn.fetchrow('''
                SELECT 
                    COUNT(DISTINCT pc.employee_id) as employee_count,
                    SUM(pc.gross_pay) as total_wages,
                    SUM(pc.federal_income_tax) as federal_tax_withheld,
                    SUM(pc.social_security_tax) as social_security_tax,
                    SUM(pc.medicare_tax) as medicare_tax,
                    SUM(pc.social_security_tax + pc.medicare_tax + pc.federal_income_tax) as total_taxes,
                    SUM(CASE WHEN pc.gross_pay <= 160200 THEN pc.gross_pay ELSE 160200 END) as social_security_wages,
                    SUM(pc.gross_pay) as medicare_wages
                FROM payroll_calculations pc
                JOIN payroll_runs pr ON pc.payroll_run_id = pr.id
                WHERE pr.pay_period_end >= $1 
                AND pr.pay_period_end <= $2
                AND pr.status = 'paid'
            ''', quarter_dates['start_date'], quarter_dates['end_date'])
            
            # Get total tax deposits made during the quarter
            total_deposits = await conn.fetchval('''
                SELECT COALESCE(SUM(amount), 0)
                FROM tax_deposits
                WHERE deposit_date >= $1 
                AND deposit_date <= $2
                AND tax_type IN ('federal_income', 'social_security', 'medicare')
            ''', quarter_dates['start_date'], quarter_dates['end_date']) or Decimal('0')
            
            return {
                'employee_count': payroll_summary['employee_count'] or 0,
                'total_wages': payroll_summary['total_wages'] or Decimal('0'),
                'federal_tax_withheld': payroll_summary['federal_tax_withheld'] or Decimal('0'),
                'social_security_wages': payroll_summary['social_security_wages'] or Decimal('0'),
                'medicare_wages': payroll_summary['medicare_wages'] or Decimal('0'),
                'social_security_tax': payroll_summary['social_security_tax'] or Decimal('0'),
                'medicare_tax': payroll_summary['medicare_tax'] or Decimal('0'),
                'total_taxes': payroll_summary['total_taxes'] or Decimal('0'),
                'total_deposits': total_deposits
            }
    
    def _get_quarter_dates(self, quarter: int, year: int) -> Dict[str, date]:
        """Get start, end, and due dates for a quarter"""
        quarters = {
            1: {
                'start_date': date(year, 1, 1),
                'end_date': date(year, 3, 31),
                'due_date': date(year, 4, 30)
            },
            2: {
                'start_date': date(year, 4, 1),
                'end_date': date(year, 6, 30),
                'due_date': date(year, 7, 31)
            },
            3: {
                'start_date': date(year, 7, 1),
                'end_date': date(year, 9, 30),
                'due_date': date(year, 10, 31)
            },
            4: {
                'start_date': date(year, 10, 1),
                'end_date': date(year, 12, 31),
                'due_date': date(year + 1, 1, 31)
            }
        }
        
        return quarters.get(quarter, quarters[1])
    
    # W-2 Processing
    async def prepare_w2_forms(self, tax_year: int) -> List[str]:
        """Prepare W-2 forms for all employees"""
        logger.info(f"Preparing W-2 forms for {tax_year}")
        
        # Get company information
        company_info = await self._get_company_information()
        
        # Get employee W-2 data
        employees_w2_data = await self._get_employees_w2_data(tax_year)
        
        form_ids = []
        
        for employee_data in employees_w2_data:
            # Create FormW2Data object
            w2_data = FormW2Data(
                employer_ein=company_info['ein'],
                employer_name=company_info['name'],
                employer_address=company_info['address'],
                employee_ssn=employee_data['ssn'],
                employee_name=f"{employee_data['first_name']} {employee_data['last_name']}",
                employee_address=employee_data['address'],
                wages_tips_compensation=employee_data['wages_tips_compensation'],
                federal_income_tax_withheld=employee_data['federal_income_tax_withheld'],
                social_security_wages=employee_data['social_security_wages'],
                social_security_tax_withheld=employee_data['social_security_tax_withheld'],
                medicare_wages=employee_data['medicare_wages'],
                medicare_tax_withheld=employee_data['medicare_tax_withheld'],
                retirement_plan=employee_data.get('retirement_plan', False)
            )
            
            # Create tax form record
            form_id = await self._create_tax_form_record(
                TaxFormType.FORM_W2,
                tax_year,
                str(tax_year),
                date(tax_year + 1, 1, 31),  # W-2s due January 31
                asdict(w2_data)
            )
            
            # Generate PDF
            pdf_bytes = self.form_generator.generate_form_w2_pdf(w2_data)
            
            # Store form file
            file_path = await self._store_form_file(form_id, 'pdf', pdf_bytes)
            
            form_ids.append(form_id)
        
        logger.info(f"Generated {len(form_ids)} W-2 forms for {tax_year}")
        
        return form_ids
    
    async def _get_employees_w2_data(self, tax_year: int) -> List[Dict[str, Any]]:
        """Get W-2 data for all employees for the tax year"""
        async with self.db_pool.acquire() as conn:
            employees_data = await conn.fetch('''
                SELECT 
                    e.id,
                    e.first_name,
                    e.last_name,
                    e.email,
                    pe.ssn,
                    e.address,
                    SUM(pc.gross_pay) as wages_tips_compensation,
                    SUM(pc.federal_income_tax) as federal_income_tax_withheld,
                    SUM(CASE WHEN pc.gross_pay <= 160200 THEN pc.gross_pay ELSE 160200 END) as social_security_wages,
                    SUM(pc.social_security_tax) as social_security_tax_withheld,
                    SUM(pc.gross_pay) as medicare_wages,
                    SUM(pc.medicare_tax) as medicare_tax_withheld,
                    MAX(CASE WHEN pc.retirement_401k > 0 THEN TRUE ELSE FALSE END) as retirement_plan
                FROM employees e
                JOIN payroll_employees pe ON e.id = pe.employee_id
                JOIN payroll_calculations pc ON e.id = pc.employee_id
                JOIN payroll_runs pr ON pc.payroll_run_id = pr.id
                WHERE EXTRACT(YEAR FROM pr.pay_period_end) = $1
                AND pr.status = 'paid'
                GROUP BY e.id, e.first_name, e.last_name, e.email, pe.ssn, e.address
                ORDER BY e.last_name, e.first_name
            ''', tax_year)
            
            result = []
            for employee in employees_data:
                # Parse address (assuming JSON format)
                address = json.loads(employee['address']) if employee['address'] else {}
                
                result.append({
                    'id': employee['id'],
                    'first_name': employee['first_name'],
                    'last_name': employee['last_name'],
                    'ssn': employee['ssn'],
                    'address': address,
                    'wages_tips_compensation': employee['wages_tips_compensation'] or Decimal('0'),
                    'federal_income_tax_withheld': employee['federal_income_tax_withheld'] or Decimal('0'),
                    'social_security_wages': employee['social_security_wages'] or Decimal('0'),
                    'social_security_tax_withheld': employee['social_security_tax_withheld'] or Decimal('0'),
                    'medicare_wages': employee['medicare_wages'] or Decimal('0'),
                    'medicare_tax_withheld': employee['medicare_tax_withheld'] or Decimal('0'),
                    'retirement_plan': employee['retirement_plan'] or False
                })
            
            return result
    
    # Electronic Filing
    async def submit_form_electronically(self, form_id: str) -> Dict[str, Any]:
        """Submit tax form electronically"""
        logger.info(f"Submitting form {form_id} electronically")
        
        async with self.db_pool.acquire() as conn:
            # Get form data
            form_record = await conn.fetchrow('''
                SELECT * FROM tax_forms WHERE form_id = $1
            ''', form_id)
            
            if not form_record:
                raise ValueError(f"Form {form_id} not found")
            
            form_type = TaxFormType(form_record['form_type'])
            
            # Generate XML for electronic filing
            if form_type == TaxFormType.FORM_941:
                form_data = Form941Data(**form_record['form_data'])
                xml_content = self.form_generator.generate_form_941_xml(form_data)
            elif form_type == TaxFormType.FORM_W2:
                w2_data = [FormW2Data(**form_record['form_data'])]
                xml_content = self.form_generator.generate_form_w2_xml(w2_data)
            else:
                raise ValueError(f"Electronic filing not supported for {form_type.value}")
            
            # Submit to IRS
            submission_result = await self.irs_service.submit_form(xml_content, form_type)
            
            # Update form status
            await conn.execute('''
                UPDATE tax_forms 
                SET status = 'filed', 
                    confirmation_number = $1, 
                    filed_at = NOW(),
                    updated_at = NOW()
                WHERE form_id = $2
            ''', submission_result['confirmation_number'], form_id)
            
            # Record submission
            await conn.execute('''
                INSERT INTO efile_submissions 
                (form_id, submission_id, status, response_data)
                VALUES ($1, $2, $3, $4)
            ''', form_id, submission_result['submission_id'], 
            submission_result['status'], json.dumps(submission_result))
            
            logger.info(f"Form {form_id} submitted successfully: {submission_result['confirmation_number']}")
            
            return submission_result
    
    async def check_filing_status(self, form_id: str) -> Dict[str, Any]:
        """Check electronic filing status"""
        async with self.db_pool.acquire() as conn:
            submission = await conn.fetchrow('''
                SELECT * FROM efile_submissions 
                WHERE form_id = $1
                ORDER BY submitted_at DESC
                LIMIT 1
            ''', form_id)
            
            if not submission:
                return {'status': 'not_filed'}
            
            # Check status with IRS
            status_result = await self.irs_service.check_status(submission['submission_id'])
            
            # Update local status
            if status_result['status'] != submission['status']:
                await conn.execute('''
                    UPDATE efile_submissions 
                    SET status = $1, 
                        response_data = $2,
                        last_status_check = NOW()
                    WHERE id = $3
                ''', status_result['status'], json.dumps(status_result), submission['id'])
                
                # Update form status if accepted
                if status_result['status'] == 'accepted':
                    await conn.execute('''
                        UPDATE tax_forms 
                        SET status = 'accepted', updated_at = NOW()
                        WHERE form_id = $1
                    ''', form_id)
            
            return status_result
    
    # Tax Compliance Monitoring
    async def monitor_compliance(self):
        """Monitor tax compliance and generate alerts"""
        logger.info("Monitoring tax compliance...")
        
        # Check for upcoming due dates
        upcoming_deadlines = await self._check_upcoming_deadlines()
        
        # Check for overdue filings
        overdue_filings = await self._check_overdue_filings()
        
        # Generate compliance alerts
        alerts_created = 0
        
        for deadline in upcoming_deadlines:
            await self._create_compliance_alert(
                'upcoming_deadline',
                'warning',
                f"{deadline['form_type']} Due Soon",
                f"Form {deadline['form_type']} for {deadline['filing_period']} is due on {deadline['due_date']}",
                deadline['due_date']
            )
            alerts_created += 1
        
        for overdue in overdue_filings:
            await self._create_compliance_alert(
                'overdue_filing',
                'critical',
                f"{overdue['form_type']} Overdue",
                f"Form {overdue['form_type']} for {overdue['filing_period']} was due on {overdue['due_date']}",
                overdue['due_date']
            )
            alerts_created += 1
        
        logger.info(f"Created {alerts_created} compliance alerts")
        
        return alerts_created
    
    async def _check_upcoming_deadlines(self) -> List[Dict[str, Any]]:
        """Check for tax filing deadlines in the next 30 days"""
        async with self.db_pool.acquire() as conn:
            deadlines = await conn.fetch('''
                SELECT * FROM tax_filing_calendar
                WHERE due_date BETWEEN NOW()::date AND (NOW() + INTERVAL '30 days')::date
                AND reminder_sent = FALSE
            ''')
            
            return [dict(deadline) for deadline in deadlines]
    
    async def _check_overdue_filings(self) -> List[Dict[str, Any]]:
        """Check for overdue tax filings"""
        async with self.db_pool.acquire() as conn:
            overdue = await conn.fetch('''
                SELECT tfc.* FROM tax_filing_calendar tfc
                LEFT JOIN tax_forms tf ON tfc.form_type = tf.form_type 
                    AND tfc.filing_period = tf.filing_period
                    AND tfc.tax_year = tf.tax_year
                WHERE tfc.due_date < NOW()::date
                AND (tf.id IS NULL OR tf.status NOT IN ('filed', 'accepted'))
            ''')
            
            return [dict(overdue_item) for overdue_item in overdue]
    
    async def _create_compliance_alert(self, alert_type: str, severity: str,
                                     title: str, description: str, due_date: date):
        """Create tax compliance alert"""
        async with self.db_pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO tax_compliance_alerts 
                (alert_type, severity, title, description, due_date)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT DO NOTHING
            ''', alert_type, severity, title, description, due_date)
    
    # Utility Methods
    async def _get_company_information(self) -> Dict[str, Any]:
        """Get company information for tax forms"""
        # This would normally fetch from a company settings table
        return {
            'name': 'ActiveLog Solutions Inc.',
            'ein': '12-3456789',
            'address': {
                'street': '123 Business Ave',
                'city': 'San Francisco',
                'state': 'CA',
                'zip': '94105'
            }
        }
    
    async def _create_tax_form_record(self, form_type: TaxFormType, tax_year: int,
                                    filing_period: str, due_date: date,
                                    form_data: Dict[str, Any]) -> str:
        """Create tax form database record"""
        async with self.db_pool.acquire() as conn:
            form_id = await conn.fetchval('''
                INSERT INTO tax_forms 
                (form_type, tax_year, filing_period, due_date, form_data)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING form_id
            ''', form_type.value, tax_year, filing_period, due_date, json.dumps(form_data, default=str))
            
            return str(form_id)
    
    async def _store_form_file(self, form_id: str, file_format: str, file_data: bytes) -> str:
        """Store tax form file"""
        # This would normally upload to cloud storage
        file_name = f"tax_form_{form_id}.{file_format}"
        file_path = f"/tmp/{file_name}"
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        logger.info(f"Stored tax form file: {file_path}")
        
        return file_path
    
    def _initialize_state_service(self, state_code: str, config: Dict[str, Any]):
        """Initialize state tax service"""
        logger.info(f"Initializing {state_code} tax service")
        return None  # Placeholder for state-specific implementations
    
    async def get_tax_calendar(self, year: int) -> List[Dict[str, Any]]:
        """Get tax filing calendar for the year"""
        async with self.db_pool.acquire() as conn:
            calendar_items = await conn.fetch('''
                SELECT * FROM tax_filing_calendar 
                WHERE tax_year = $1 
                ORDER BY due_date
            ''', year)
            
            return [dict(item) for item in calendar_items]
    
    async def generate_tax_summary_report(self, year: int) -> Dict[str, Any]:
        """Generate comprehensive tax summary report"""
        async with self.db_pool.acquire() as conn:
            # Get filed forms summary
            forms_summary = await conn.fetch('''
                SELECT 
                    form_type,
                    COUNT(*) as forms_filed,
                    COUNT(*) FILTER (WHERE status = 'accepted') as forms_accepted,
                    COUNT(*) FILTER (WHERE status = 'rejected') as forms_rejected
                FROM tax_forms 
                WHERE tax_year = $1
                GROUP BY form_type
            ''', year)
            
            # Get compliance status
            compliance_summary = await conn.fetchrow('''
                SELECT 
                    COUNT(*) as total_alerts,
                    COUNT(*) FILTER (WHERE severity = 'critical') as critical_alerts,
                    COUNT(*) FILTER (WHERE resolved = true) as resolved_alerts
                FROM tax_compliance_alerts
                WHERE EXTRACT(YEAR FROM created_at) = $1
            ''', year)
            
            return {
                'year': year,
                'forms_summary': [dict(form) for form in forms_summary],
                'compliance_summary': dict(compliance_summary),
                'generated_at': datetime.now().isoformat()
            }

def main():
    """Example usage"""
    async def run_tax_preparation():
        config_path = "tax_config.yml"
        tax_service = TaxPreparationService(config_path)
        
        try:
            await tax_service.initialize()
            
            # Prepare Form 941 for Q1 2024
            form_941_id = await tax_service.prepare_form_941(1, 2024)
            print(f"Form 941 prepared: {form_941_id}")
            
            # Prepare W-2 forms for 2024
            w2_form_ids = await tax_service.prepare_w2_forms(2024)
            print(f"W-2 forms prepared: {len(w2_form_ids)} forms")
            
            # Monitor compliance
            alerts_created = await tax_service.monitor_compliance()
            print(f"Compliance monitoring created {alerts_created} alerts")
            
            # Generate tax summary report
            report = await tax_service.generate_tax_summary_report(2024)
            print(f"Tax summary report: {report}")
            
        finally:
            await tax_service.shutdown()
    
    asyncio.run(run_tax_preparation())

if __name__ == '__main__':
    main()