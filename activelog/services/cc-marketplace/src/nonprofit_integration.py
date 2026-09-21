from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum
import uuid
from pydantic import BaseModel

from .models import MarketSymbol

class NonProfitType(str, Enum):
    LIBRARY = "library"
    FOUNDATION = "foundation"
    EDUCATIONAL = "educational"
    PUBLIC_GOOD = "public_good"
    CHARITY = "charity"
    RESEARCH = "research"

class GrantStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    FUNDED = "funded"
    COMPLETED = "completed"

class ImpactCategory(str, Enum):
    EDUCATION = "education"
    RESEARCH = "research"
    COMMUNITY = "community"
    ENVIRONMENT = "environment"
    HEALTH = "health"
    TECHNOLOGY = "technology"
    ACCESSIBILITY = "accessibility"

class NonProfitAccount(BaseModel):
    account_id: str = None
    organization_name: str
    tax_id: str  # EIN or other tax-exempt identifier
    nonprofit_type: NonProfitType
    verification_status: str = "pending"  # pending, verified, rejected
    special_rate_eligible: bool = False
    cc_stream_rate: Decimal = Decimal('0')  # CC per day from shares
    total_donated: Decimal = Decimal('0')
    total_received: Decimal = Decimal('0')
    created_at: datetime = None
    verified_at: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.account_id:
            self.account_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class DonationProgram(BaseModel):
    program_id: str = None
    name: str
    description: str
    target_symbols: List[MarketSymbol]
    matching_ratio: Decimal = Decimal('1.0')  # 1:1 matching by default
    max_matching_amount: Decimal = Decimal('10000')
    current_matched: Decimal = Decimal('0')
    start_date: datetime
    end_date: datetime
    is_active: bool = True
    tax_deductible: bool = True
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.program_id:
            self.program_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class Donation(BaseModel):
    donation_id: str = None
    donor_id: str
    recipient_account_id: str
    program_id: Optional[str] = None
    amount: Decimal
    symbol: MarketSymbol
    matched_amount: Decimal = Decimal('0')
    total_amount: Decimal = None  # amount + matched_amount
    tax_deductible: bool = True
    tax_receipt_number: str = None
    donation_date: datetime = None
    purpose: Optional[str] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.donation_id:
            self.donation_id = str(uuid.uuid4())
        if not self.donation_date:
            self.donation_date = datetime.now()
        if not self.tax_receipt_number:
            self.tax_receipt_number = f"TR-{datetime.now().strftime('%Y%m%d')}-{self.donation_id[:8]}"
        if not self.total_amount:
            self.total_amount = self.amount + self.matched_amount

class GrantApplication(BaseModel):
    application_id: str = None
    applicant_account_id: str
    title: str
    description: str
    requested_amount: Decimal
    symbol: MarketSymbol
    project_duration_months: int
    impact_category: ImpactCategory
    expected_outcomes: List[str]
    budget_breakdown: Dict[str, Decimal]
    timeline_milestones: List[Dict[str, str]]
    status: GrantStatus = GrantStatus.DRAFT
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    funded_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None
    funding_conditions: List[str] = []
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.application_id:
            self.application_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class ImpactReport(BaseModel):
    report_id: str = None
    account_id: str
    reporting_period_start: datetime
    reporting_period_end: datetime
    metrics: Dict[str, Any]  # Flexible metrics structure
    outcomes_achieved: List[str]
    beneficiaries_count: int
    funds_utilized: Decimal
    remaining_funds: Decimal
    next_period_goals: List[str]
    supporting_documents: List[str] = []  # URLs or file references
    created_at: datetime = None
    
    def __init__(self, **data):
        super().__init__(**data)
        if not self.report_id:
            self.report_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now()

class NonProfitIntegrationSystem:
    def __init__(self):
        self.nonprofit_accounts: Dict[str, NonProfitAccount] = {}
        self.donation_programs: Dict[str, DonationProgram] = {}
        self.donations: List[Donation] = []
        self.grant_applications: Dict[str, GrantApplication] = {}
        self.impact_reports: Dict[str, List[ImpactReport]] = {}  # account_id -> reports
        
        # Special rates for different organization types
        self.special_rates = {
            NonProfitType.LIBRARY: Decimal('0.75'),      # 25% discount
            NonProfitType.EDUCATIONAL: Decimal('0.60'),  # 40% discount
            NonProfitType.PUBLIC_GOOD: Decimal('0.50'),  # 50% discount
            NonProfitType.RESEARCH: Decimal('0.70'),     # 30% discount
            NonProfitType.FOUNDATION: Decimal('0.85'),   # 15% discount
            NonProfitType.CHARITY: Decimal('0.55'),      # 45% discount
        }
        
        # Initialize default donation programs
        self._initialize_default_programs()
    
    def _initialize_default_programs(self):
        """Initialize default donation matching programs"""
        # Education support program
        education_program = DonationProgram(
            name="Education Support Initiative",
            description="Matching donations for educational institutions and libraries",
            target_symbols=[MarketSymbol.ACTIVELOG_CC, MarketSymbol.STUDYLOG_CC],
            matching_ratio=Decimal('2.0'),  # 2:1 matching
            max_matching_amount=Decimal('50000'),
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=365),
        )
        self.donation_programs[education_program.program_id] = education_program
        
        # Public good program
        public_good_program = DonationProgram(
            name="Public Good Innovation Fund",
            description="Supporting projects that benefit the broader community",
            target_symbols=list(MarketSymbol),
            matching_ratio=Decimal('1.5'),  # 1.5:1 matching
            max_matching_amount=Decimal('25000'),
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=365),
        )
        self.donation_programs[public_good_program.program_id] = public_good_program
    
    def register_nonprofit(self, organization_data: Dict) -> NonProfitAccount:
        """Register a new non-profit organization"""
        account = NonProfitAccount(**organization_data)
        
        # Determine special rate eligibility
        if account.nonprofit_type in self.special_rates:
            account.special_rate_eligible = True
        
        self.nonprofit_accounts[account.account_id] = account
        return account
    
    def verify_nonprofit_status(self, account_id: str, verification_data: Dict) -> bool:
        """Verify non-profit tax-exempt status"""
        account = self.nonprofit_accounts.get(account_id)
        if not account:
            return False
        
        # In real implementation, this would integrate with tax authority APIs
        # For now, simulate verification process
        if verification_data.get('tax_id_verified') and verification_data.get('documents_valid'):
            account.verification_status = "verified"
            account.verified_at = datetime.now()
            return True
        else:
            account.verification_status = "rejected"
            return False
    
    def get_special_rate(self, account_id: str) -> Optional[Decimal]:
        """Get special pricing rate for non-profit"""
        account = self.nonprofit_accounts.get(account_id)
        if not account or not account.special_rate_eligible or account.verification_status != "verified":
            return None
        
        return self.special_rates.get(account.nonprofit_type)
    
    def calculate_share_dividend_stream(self, account_id: str, shares_owned: Decimal, 
                                      symbol: MarketSymbol, annual_yield: Decimal) -> Dict:
        """Calculate steady CC stream from shares for libraries/institutions"""
        account = self.nonprofit_accounts.get(account_id)
        if not account:
            return {'error': 'Account not found'}
        
        # Calculate dividend stream
        annual_dividend = shares_owned * annual_yield
        daily_dividend = annual_dividend / Decimal('365')
        monthly_dividend = annual_dividend / Decimal('12')
        
        # Apply any special modifiers for non-profits
        if account.nonprofit_type == NonProfitType.LIBRARY:
            # Libraries get enhanced dividend stream
            daily_dividend *= Decimal('1.2')
            monthly_dividend *= Decimal('1.2')
            annual_dividend *= Decimal('1.2')
        
        account.cc_stream_rate = daily_dividend
        
        return {
            'account_id': account_id,
            'shares_owned': float(shares_owned),
            'annual_dividend': float(annual_dividend),
            'monthly_dividend': float(monthly_dividend),
            'daily_dividend': float(daily_dividend),
            'enhanced_rate': account.nonprofit_type == NonProfitType.LIBRARY
        }
    
    def process_donation(self, donor_id: str, recipient_account_id: str, 
                        amount: Decimal, symbol: MarketSymbol, 
                        program_id: Optional[str] = None) -> Donation:
        """Process a donation with matching funds if applicable"""
        recipient_account = self.nonprofit_accounts.get(recipient_account_id)
        if not recipient_account:
            raise ValueError("Recipient account not found")
        
        donation = Donation(
            donor_id=donor_id,
            recipient_account_id=recipient_account_id,
            amount=amount,
            symbol=symbol,
            program_id=program_id
        )
        
        # Apply matching funds if program exists
        if program_id:
            program = self.donation_programs.get(program_id)
            if program and program.is_active and symbol in program.target_symbols:
                # Check if matching funds available
                potential_match = amount * program.matching_ratio
                available_match = program.max_matching_amount - program.current_matched
                
                actual_match = min(potential_match, available_match)
                if actual_match > 0:
                    donation.matched_amount = actual_match
                    donation.total_amount = amount + actual_match
                    program.current_matched += actual_match
        
        # Update recipient totals
        recipient_account.total_received += donation.total_amount
        
        self.donations.append(donation)
        return donation
    
    def create_grant_application(self, applicant_account_id: str, 
                               application_data: Dict) -> GrantApplication:
        """Create a new grant application"""
        if applicant_account_id not in self.nonprofit_accounts:
            raise ValueError("Applicant account not found")
        
        application = GrantApplication(
            applicant_account_id=applicant_account_id,
            **application_data
        )
        
        self.grant_applications[application.application_id] = application
        return application
    
    def submit_grant_application(self, application_id: str) -> bool:
        """Submit grant application for review"""
        application = self.grant_applications.get(application_id)
        if not application:
            return False
        
        if application.status != GrantStatus.DRAFT:
            return False
        
        application.status = GrantStatus.SUBMITTED
        application.submitted_at = datetime.now()
        return True
    
    def review_grant_application(self, application_id: str, decision: str, 
                               reviewer_notes: str = "", conditions: List[str] = []) -> bool:
        """Review a grant application"""
        application = self.grant_applications.get(application_id)
        if not application or application.status != GrantStatus.SUBMITTED:
            return False
        
        application.status = GrantStatus.UNDER_REVIEW
        application.reviewed_at = datetime.now()
        application.reviewer_notes = reviewer_notes
        
        if decision.lower() == 'approve':
            application.status = GrantStatus.APPROVED
            application.approved_at = datetime.now()
            application.funding_conditions = conditions
        elif decision.lower() == 'reject':
            application.status = GrantStatus.REJECTED
        
        return True
    
    def fund_grant(self, application_id: str) -> Dict:
        """Fund an approved grant application"""
        application = self.grant_applications.get(application_id)
        if not application or application.status != GrantStatus.APPROVED:
            return {'error': 'Grant not approved for funding'}
        
        # In real implementation, this would trigger actual fund transfer
        application.status = GrantStatus.FUNDED
        application.funded_at = datetime.now()
        
        # Update recipient account
        recipient_account = self.nonprofit_accounts[application.applicant_account_id]
        recipient_account.total_received += application.requested_amount
        
        return {
            'success': True,
            'application_id': application_id,
            'amount_funded': float(application.requested_amount),
            'symbol': application.symbol.value,
            'funded_at': application.funded_at.isoformat()
        }
    
    def submit_impact_report(self, account_id: str, report_data: Dict) -> ImpactReport:
        """Submit an impact report"""
        if account_id not in self.nonprofit_accounts:
            raise ValueError("Account not found")
        
        report = ImpactReport(
            account_id=account_id,
            **report_data
        )
        
        if account_id not in self.impact_reports:
            self.impact_reports[account_id] = []
        
        self.impact_reports[account_id].append(report)
        return report
    
    def get_donation_tax_receipt(self, donation_id: str) -> Dict:
        """Generate tax receipt for donation"""
        donation = next((d for d in self.donations if d.donation_id == donation_id), None)
        if not donation or not donation.tax_deductible:
            return {'error': 'Donation not found or not tax deductible'}
        
        recipient = self.nonprofit_accounts[donation.recipient_account_id]
        
        return {
            'receipt_number': donation.tax_receipt_number,
            'donor_id': donation.donor_id,
            'recipient_organization': recipient.organization_name,
            'recipient_tax_id': recipient.tax_id,
            'donation_amount': float(donation.amount),
            'matched_amount': float(donation.matched_amount),
            'total_deductible': float(donation.amount),  # Only original donation is deductible
            'donation_date': donation.donation_date.isoformat(),
            'symbol': donation.symbol.value,
            'purpose': donation.purpose
        }
    
    def get_nonprofit_dashboard(self, account_id: str) -> Dict:
        """Get comprehensive dashboard for non-profit account"""
        account = self.nonprofit_accounts.get(account_id)
        if not account:
            return {'error': 'Account not found'}
        
        # Get donations received
        donations_received = [d for d in self.donations if d.recipient_account_id == account_id]
        
        # Get grants
        grants = [g for g in self.grant_applications.values() if g.applicant_account_id == account_id]
        
        # Get impact reports
        reports = self.impact_reports.get(account_id, [])
        
        # Calculate metrics
        total_donations = sum(d.total_amount for d in donations_received)
        active_grants = len([g for g in grants if g.status in [GrantStatus.APPROVED, GrantStatus.FUNDED]])
        
        return {
            'account_info': {
                'organization_name': account.organization_name,
                'nonprofit_type': account.nonprofit_type.value,
                'verification_status': account.verification_status,
                'special_rate_eligible': account.special_rate_eligible,
                'cc_stream_rate': float(account.cc_stream_rate)
            },
            'financial_summary': {
                'total_received': float(account.total_received),
                'total_donations': float(total_donations),
                'active_grants': active_grants,
                'impact_reports': len(reports)
            },
            'recent_donations': [
                {
                    'donation_id': d.donation_id,
                    'amount': float(d.amount),
                    'matched_amount': float(d.matched_amount),
                    'total_amount': float(d.total_amount),
                    'date': d.donation_date.isoformat(),
                    'symbol': d.symbol.value
                } for d in sorted(donations_received, key=lambda x: x.donation_date, reverse=True)[:10]
            ],
            'grant_status': [
                {
                    'application_id': g.application_id,
                    'title': g.title,
                    'requested_amount': float(g.requested_amount),
                    'status': g.status.value,
                    'submitted_at': g.submitted_at.isoformat() if g.submitted_at else None
                } for g in grants
            ]
        }
    
    def get_public_good_projects(self) -> List[Dict]:
        """Get highlighted public good projects"""
        public_good_accounts = [
            acc for acc in self.nonprofit_accounts.values() 
            if acc.nonprofit_type == NonProfitType.PUBLIC_GOOD and acc.verification_status == "verified"
        ]
        
        projects = []
        for account in public_good_accounts:
            # Get recent impact reports
            reports = self.impact_reports.get(account.account_id, [])
            latest_report = max(reports, key=lambda x: x.created_at) if reports else None
            
            # Get active grants
            active_grants = [
                g for g in self.grant_applications.values() 
                if g.applicant_account_id == account.account_id and g.status == GrantStatus.FUNDED
            ]
            
            projects.append({
                'account_id': account.account_id,
                'organization_name': account.organization_name,
                'total_received': float(account.total_received),
                'active_grants_count': len(active_grants),
                'latest_impact_report': {
                    'beneficiaries_count': latest_report.beneficiaries_count,
                    'outcomes_achieved': latest_report.outcomes_achieved[:3]  # Top 3 outcomes
                } if latest_report else None,
                'donation_url': f"/donate/{account.account_id}"
            })
        
        return sorted(projects, key=lambda x: x['total_received'], reverse=True)
    
    def get_matching_program_info(self, program_id: str) -> Dict:
        """Get information about a donation matching program"""
        program = self.donation_programs.get(program_id)
        if not program:
            return {'error': 'Program not found'}
        
        return {
            'program_id': program.program_id,
            'name': program.name,
            'description': program.description,
            'matching_ratio': float(program.matching_ratio),
            'max_matching_amount': float(program.max_matching_amount),
            'current_matched': float(program.current_matched),
            'remaining_match_funds': float(program.max_matching_amount - program.current_matched),
            'target_symbols': [s.value for s in program.target_symbols],
            'is_active': program.is_active,
            'start_date': program.start_date.isoformat(),
            'end_date': program.end_date.isoformat(),
            'tax_deductible': program.tax_deductible
        }