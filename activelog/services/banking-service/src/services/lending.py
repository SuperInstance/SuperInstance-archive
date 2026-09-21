import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class LoanType(Enum):
    PERSONAL = "personal"
    BUSINESS = "business"
    MORTGAGE = "mortgage"
    AUTO = "auto"
    STUDENT = "student"
    CREDIT_LINE = "credit_line"

class LoanStatus(Enum):
    APPLICATION = "application"
    UNDERWRITING = "underwriting"
    APPROVED = "approved"
    FUNDED = "funded"
    CURRENT = "current"
    DELINQUENT = "delinquent"
    DEFAULT = "default"
    PAID_OFF = "paid_off"
    CHARGED_OFF = "charged_off"

class PaymentStatus(Enum):
    CURRENT = "current"
    LATE_1_30 = "late_1_30"
    LATE_31_60 = "late_31_60"
    LATE_61_90 = "late_61_90"
    LATE_90_PLUS = "late_90_plus"

@dataclass
class LoanApplication:
    application_id: str
    customer_id: str
    loan_type: LoanType
    requested_amount: Decimal
    purpose: str
    employment_info: Dict
    income: Decimal
    debt_to_income: float
    credit_score: int
    collateral_info: Optional[Dict]
    applied_at: datetime
    status: LoanStatus

@dataclass
class Loan:
    loan_id: str
    customer_id: str
    loan_type: LoanType
    principal_amount: Decimal
    current_balance: Decimal
    interest_rate: Decimal
    term_months: int
    monthly_payment: Decimal
    payment_due_date: int  # Day of month
    origination_date: datetime
    maturity_date: datetime
    status: LoanStatus
    payment_status: PaymentStatus
    payments_made: int
    last_payment_date: Optional[datetime]
    next_payment_date: datetime

@dataclass
class LoanPayment:
    payment_id: str
    loan_id: str
    customer_id: str
    payment_date: datetime
    scheduled_date: datetime
    amount: Decimal
    principal_portion: Decimal
    interest_portion: Decimal
    fees: Decimal
    remaining_balance: Decimal
    payment_method: str
    late_fee: Decimal = Decimal('0.00')

class LendingService:
    def __init__(self):
        self.applications = {}
        self.loans = {}
        self.payments = {}
        self.payment_processor_active = False
        
    async def start_payment_processing(self):
        """Start payment processing service"""
        self.payment_processor_active = True
        asyncio.create_task(self._payment_processing_loop())
        logger.info("Loan payment processing started")
    
    async def stop_payment_processing(self):
        """Stop payment processing"""
        self.payment_processor_active = False
        logger.info("Loan payment processing stopped")
    
    async def submit_application(self, application_data: Dict) -> Dict:
        """Submit loan application"""
        try:
            application_id = str(uuid.uuid4())
            
            application = LoanApplication(
                application_id=application_id,
                customer_id=application_data['customer_id'],
                loan_type=LoanType(application_data['loan_type']),
                requested_amount=Decimal(str(application_data['requested_amount'])),
                purpose=application_data.get('purpose', ''),
                employment_info=application_data.get('employment_info', {}),
                income=Decimal(str(application_data['annual_income'])),
                debt_to_income=float(application_data.get('debt_to_income', 0)),
                credit_score=int(application_data.get('credit_score', 650)),
                collateral_info=application_data.get('collateral_info'),
                applied_at=datetime.now(),
                status=LoanStatus.APPLICATION
            )
            
            self.applications[application_id] = application
            
            # Trigger automated underwriting
            await self._automated_underwriting(application_id)
            
            return {
                'success': True,
                'application_id': application_id,
                'status': self.applications[application_id].status.value,
                'submitted_at': application.applied_at.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error submitting loan application: {e}")
            return {'success': False, 'error': str(e)}
    
    async def originate_loan(self, loan_data: Dict) -> Dict:
        """Originate approved loan"""
        try:
            loan_id = str(uuid.uuid4())
            principal = Decimal(str(loan_data['principal_amount']))
            rate = Decimal(str(loan_data['interest_rate']))
            term = int(loan_data['term_months'])
            
            # Calculate monthly payment using amortization formula
            monthly_rate = rate / Decimal('12') / Decimal('100')
            if monthly_rate > 0:
                payment = principal * (monthly_rate * (1 + monthly_rate) ** term) / ((1 + monthly_rate) ** term - 1)
            else:
                payment = principal / term
            
            payment = payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            origination_date = datetime.now()
            maturity_date = origination_date + timedelta(days=term * 30)
            next_payment_date = origination_date + timedelta(days=30)
            
            loan = Loan(
                loan_id=loan_id,
                customer_id=loan_data['customer_id'],
                loan_type=LoanType(loan_data['loan_type']),
                principal_amount=principal,
                current_balance=principal,
                interest_rate=rate,
                term_months=term,
                monthly_payment=payment,
                payment_due_date=int(loan_data.get('payment_due_date', 15)),
                origination_date=origination_date,
                maturity_date=maturity_date,
                status=LoanStatus.FUNDED,
                payment_status=PaymentStatus.CURRENT,
                payments_made=0,
                last_payment_date=None,
                next_payment_date=next_payment_date
            )
            
            self.loans[loan_id] = loan
            
            return {
                'success': True,
                'loan_id': loan_id,
                'principal_amount': float(principal),
                'monthly_payment': float(payment),
                'next_payment_date': next_payment_date.isoformat(),
                'maturity_date': maturity_date.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error originating loan: {e}")
            return {'success': False, 'error': str(e)}
    
    async def process_payment(self, payment_data: Dict) -> Dict:
        """Process loan payment"""
        try:
            loan_id = payment_data['loan_id']
            if loan_id not in self.loans:
                return {'success': False, 'error': 'Loan not found'}
            
            loan = self.loans[loan_id]
            payment_amount = Decimal(str(payment_data['amount']))
            payment_date = datetime.now()
            
            # Calculate interest and principal portions
            monthly_rate = loan.interest_rate / Decimal('12') / Decimal('100')
            interest_portion = (loan.current_balance * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            principal_portion = payment_amount - interest_portion
            
            # Apply payment to balance
            loan.current_balance = max(Decimal('0'), loan.current_balance - principal_portion)
            loan.payments_made += 1
            loan.last_payment_date = payment_date
            loan.next_payment_date = payment_date + timedelta(days=30)
            
            # Update payment status
            if loan.current_balance <= Decimal('0.01'):
                loan.status = LoanStatus.PAID_OFF
                loan.payment_status = PaymentStatus.CURRENT
            else:
                days_late = (payment_date - loan.next_payment_date).days
                if days_late <= 0:
                    loan.payment_status = PaymentStatus.CURRENT
                elif days_late <= 30:
                    loan.payment_status = PaymentStatus.LATE_1_30
                elif days_late <= 60:
                    loan.payment_status = PaymentStatus.LATE_31_60
                elif days_late <= 90:
                    loan.payment_status = PaymentStatus.LATE_61_90
                else:
                    loan.payment_status = PaymentStatus.LATE_90_PLUS
            
            # Create payment record
            payment_id = str(uuid.uuid4())
            payment_record = LoanPayment(
                payment_id=payment_id,
                loan_id=loan_id,
                customer_id=loan.customer_id,
                payment_date=payment_date,
                scheduled_date=loan.next_payment_date,
                amount=payment_amount,
                principal_portion=principal_portion,
                interest_portion=interest_portion,
                fees=Decimal('0.00'),
                remaining_balance=loan.current_balance,
                payment_method=payment_data.get('payment_method', 'ach')
            )
            
            self.payments[payment_id] = payment_record
            
            return {
                'success': True,
                'payment_id': payment_id,
                'principal_portion': float(principal_portion),
                'interest_portion': float(interest_portion),
                'remaining_balance': float(loan.current_balance),
                'loan_status': loan.status.value,
                'payment_status': loan.payment_status.value
            }
        
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_loan_details(self, loan_id: str) -> Dict:
        """Get loan details"""
        try:
            if loan_id not in self.loans:
                return {'success': False, 'error': 'Loan not found'}
            
            loan = self.loans[loan_id]
            
            # Get payment history
            loan_payments = [
                {
                    'payment_id': p.payment_id,
                    'payment_date': p.payment_date.isoformat(),
                    'amount': float(p.amount),
                    'principal': float(p.principal_portion),
                    'interest': float(p.interest_portion),
                    'balance_after': float(p.remaining_balance)
                }
                for p in self.payments.values()
                if p.loan_id == loan_id
            ]
            
            return {
                'success': True,
                'loan_id': loan_id,
                'customer_id': loan.customer_id,
                'loan_type': loan.loan_type.value,
                'principal_amount': float(loan.principal_amount),
                'current_balance': float(loan.current_balance),
                'interest_rate': float(loan.interest_rate),
                'monthly_payment': float(loan.monthly_payment),
                'term_months': loan.term_months,
                'payments_made': loan.payments_made,
                'status': loan.status.value,
                'payment_status': loan.payment_status.value,
                'next_payment_date': loan.next_payment_date.isoformat(),
                'payment_history': loan_payments
            }
        
        except Exception as e:
            logger.error(f"Error getting loan details: {e}")
            return {'success': False, 'error': str(e)}
    
    async def calculate_amortization_schedule(self, loan_data: Dict) -> Dict:
        """Calculate loan amortization schedule"""
        try:
            principal = Decimal(str(loan_data['principal']))
            rate = Decimal(str(loan_data['interest_rate']))
            term = int(loan_data['term_months'])
            
            monthly_rate = rate / Decimal('12') / Decimal('100')
            
            if monthly_rate > 0:
                payment = principal * (monthly_rate * (1 + monthly_rate) ** term) / ((1 + monthly_rate) ** term - 1)
            else:
                payment = principal / term
            
            payment = payment.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            schedule = []
            remaining_balance = principal
            
            for month in range(1, term + 1):
                interest_payment = (remaining_balance * monthly_rate).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                principal_payment = payment - interest_payment
                
                if remaining_balance < principal_payment:
                    principal_payment = remaining_balance
                    payment = principal_payment + interest_payment
                
                remaining_balance -= principal_payment
                
                schedule.append({
                    'payment_number': month,
                    'payment_amount': float(payment),
                    'principal_payment': float(principal_payment),
                    'interest_payment': float(interest_payment),
                    'remaining_balance': float(remaining_balance)
                })
                
                if remaining_balance <= Decimal('0.01'):
                    break
            
            return {
                'success': True,
                'monthly_payment': float(payment),
                'total_payments': float(payment * len(schedule)),
                'total_interest': float(payment * len(schedule) - principal),
                'schedule': schedule
            }
        
        except Exception as e:
            logger.error(f"Error calculating amortization: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _automated_underwriting(self, application_id: str):
        """Automated underwriting process"""
        try:
            application = self.applications[application_id]
            
            # Simple underwriting rules
            approval_score = 0
            
            # Credit score weight (40%)
            if application.credit_score >= 750:
                approval_score += 40
            elif application.credit_score >= 700:
                approval_score += 30
            elif application.credit_score >= 650:
                approval_score += 20
            elif application.credit_score >= 600:
                approval_score += 10
            
            # Debt-to-income weight (30%)
            if application.debt_to_income <= 0.2:
                approval_score += 30
            elif application.debt_to_income <= 0.3:
                approval_score += 25
            elif application.debt_to_income <= 0.4:
                approval_score += 15
            elif application.debt_to_income <= 0.5:
                approval_score += 5
            
            # Income stability weight (20%)
            if application.income >= Decimal('100000'):
                approval_score += 20
            elif application.income >= Decimal('75000'):
                approval_score += 15
            elif application.income >= Decimal('50000'):
                approval_score += 10
            elif application.income >= Decimal('35000'):
                approval_score += 5
            
            # Loan amount vs income weight (10%)
            loan_to_income = float(application.requested_amount / application.income)
            if loan_to_income <= 2:
                approval_score += 10
            elif loan_to_income <= 4:
                approval_score += 5
            
            # Decision
            if approval_score >= 70:
                application.status = LoanStatus.APPROVED
            else:
                application.status = LoanStatus.UNDERWRITING
            
            logger.info(f"Application {application_id} underwriting score: {approval_score}, status: {application.status.value}")
            
        except Exception as e:
            logger.error(f"Error in automated underwriting: {e}")
    
    async def _payment_processing_loop(self):
        """Background payment processing"""
        while self.payment_processor_active:
            try:
                await self._process_scheduled_payments()
                await self._check_delinquencies()
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error in payment processing loop: {e}")
                await asyncio.sleep(3600)
    
    async def _process_scheduled_payments(self):
        """Process scheduled payments"""
        today = datetime.now().date()
        
        for loan in self.loans.values():
            if (loan.status == LoanStatus.CURRENT and 
                loan.next_payment_date.date() <= today):
                # In production, this would trigger payment collection
                logger.info(f"Payment due for loan {loan.loan_id}")
    
    async def _check_delinquencies(self):
        """Check for delinquent loans"""
        today = datetime.now()
        
        for loan in self.loans.values():
            if loan.status == LoanStatus.CURRENT:
                days_past_due = (today - loan.next_payment_date).days
                
                if days_past_due > 90:
                    loan.status = LoanStatus.DEFAULT
                elif days_past_due > 30:
                    loan.status = LoanStatus.DELINQUENT