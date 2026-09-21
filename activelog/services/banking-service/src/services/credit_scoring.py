import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
import json
import logging
from ..core.config import settings

logger = logging.getLogger(__name__)

class CreditScoreModel(Enum):
    FICO = "fico"
    VANTAGE = "vantage"
    CUSTOM = "custom"

class CreditGrade(Enum):
    EXCELLENT = "excellent"  # 800+
    VERY_GOOD = "very_good"  # 740-799
    GOOD = "good"           # 670-739
    FAIR = "fair"           # 580-669
    POOR = "poor"           # 300-579

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class CreditReport:
    customer_id: str
    report_id: str
    credit_score: int
    credit_grade: CreditGrade
    risk_level: RiskLevel
    model_used: CreditScoreModel
    factors: Dict  # Contributing factors
    accounts: List[Dict]  # Credit accounts
    inquiries: List[Dict]  # Credit inquiries
    public_records: List[Dict]  # Bankruptcies, liens, etc.
    payment_history: Dict  # Payment history analysis
    credit_utilization: float
    credit_age_months: int
    credit_mix_score: int
    report_date: datetime
    bureau_data: Dict  # Data from credit bureaus

@dataclass
class CreditMonitoring:
    customer_id: str
    monitoring_id: str
    active: bool
    alert_threshold: int  # Score change threshold for alerts
    last_score: int
    last_check: datetime
    alerts: List[Dict]
    created_at: datetime

class CreditScoringService:
    def __init__(self):
        self.credit_reports = {}
        self.monitoring_accounts = {}
        self.monitoring_active = False
        
    async def start_monitoring(self):
        """Start credit monitoring service"""
        self.monitoring_active = True
        asyncio.create_task(self._monitoring_loop())
        logger.info("Credit monitoring started")
    
    async def stop_monitoring(self):
        """Stop credit monitoring"""
        self.monitoring_active = False
        logger.info("Credit monitoring stopped")
    
    async def calculate_credit_score(self, customer_data: Dict) -> Dict:
        """Calculate credit score for customer"""
        try:
            customer_id = customer_data['customer_id']
            model = CreditScoreModel(customer_data.get('model', 'custom'))
            
            # Get customer credit data
            credit_accounts = customer_data.get('credit_accounts', [])
            payment_history = customer_data.get('payment_history', {})
            credit_inquiries = customer_data.get('inquiries', [])
            public_records = customer_data.get('public_records', [])
            
            # Calculate score components
            payment_score = self._calculate_payment_history_score(payment_history)
            utilization_score = self._calculate_utilization_score(credit_accounts)
            age_score = self._calculate_credit_age_score(credit_accounts)
            mix_score = self._calculate_credit_mix_score(credit_accounts)
            inquiry_score = self._calculate_inquiry_score(credit_inquiries)
            
            # Weight the components (similar to FICO model)
            weighted_score = (
                payment_score * 0.35 +      # Payment history (35%)
                utilization_score * 0.30 +  # Credit utilization (30%)
                age_score * 0.15 +          # Length of credit history (15%)
                mix_score * 0.10 +          # Credit mix (10%)
                inquiry_score * 0.10        # New credit inquiries (10%)
            )
            
            # Convert to standard 300-850 range
            credit_score = int(300 + (weighted_score / 100) * 550)
            credit_score = min(max(credit_score, 300), 850)
            
            # Determine credit grade and risk level
            credit_grade = self._get_credit_grade(credit_score)
            risk_level = self._get_risk_level(credit_score, public_records)
            
            # Calculate additional metrics
            credit_utilization = self._calculate_overall_utilization(credit_accounts)
            credit_age_months = self._calculate_average_age_months(credit_accounts)
            
            # Create credit report
            report_id = str(uuid.uuid4())
            report = CreditReport(
                customer_id=customer_id,
                report_id=report_id,
                credit_score=credit_score,
                credit_grade=credit_grade,
                risk_level=risk_level,
                model_used=model,
                factors=self._get_score_factors(payment_score, utilization_score, age_score, mix_score, inquiry_score),
                accounts=credit_accounts,
                inquiries=credit_inquiries,
                public_records=public_records,
                payment_history=payment_history,
                credit_utilization=credit_utilization,
                credit_age_months=credit_age_months,
                credit_mix_score=mix_score,
                report_date=datetime.now(),
                bureau_data=customer_data.get('bureau_data', {})
            )
            
            self.credit_reports[report_id] = report
            
            return {
                'success': True,
                'customer_id': customer_id,
                'credit_score': credit_score,
                'credit_grade': credit_grade.value,
                'risk_level': risk_level.value,
                'report_id': report_id,
                'factors': report.factors,
                'credit_utilization': credit_utilization,
                'generated_at': report.report_date.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error calculating credit score: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_credit_report(self, report_id: str) -> Dict:
        """Get detailed credit report"""
        try:
            if report_id not in self.credit_reports:
                return {'success': False, 'error': 'Credit report not found'}
            
            report = self.credit_reports[report_id]
            
            return {
                'success': True,
                'report_id': report_id,
                'customer_id': report.customer_id,
                'credit_score': report.credit_score,
                'credit_grade': report.credit_grade.value,
                'risk_level': report.risk_level.value,
                'model_used': report.model_used.value,
                'report_date': report.report_date.isoformat(),
                'factors': report.factors,
                'credit_utilization': report.credit_utilization,
                'credit_age_months': report.credit_age_months,
                'accounts': report.accounts,
                'inquiries': report.inquiries,
                'public_records': report.public_records,
                'payment_history': report.payment_history
            }
        
        except Exception as e:
            logger.error(f"Error getting credit report: {e}")
            return {'success': False, 'error': str(e)}
    
    async def setup_credit_monitoring(self, monitoring_data: Dict) -> Dict:
        """Set up credit monitoring for customer"""
        try:
            customer_id = monitoring_data['customer_id']
            monitoring_id = str(uuid.uuid4())
            
            monitoring = CreditMonitoring(
                customer_id=customer_id,
                monitoring_id=monitoring_id,
                active=True,
                alert_threshold=monitoring_data.get('alert_threshold', 25),
                last_score=monitoring_data.get('current_score', 0),
                last_check=datetime.now(),
                alerts=[],
                created_at=datetime.now()
            )
            
            self.monitoring_accounts[monitoring_id] = monitoring
            
            return {
                'success': True,
                'monitoring_id': monitoring_id,
                'customer_id': customer_id,
                'alert_threshold': monitoring.alert_threshold,
                'created_at': monitoring.created_at.isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error setting up credit monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    async def analyze_creditworthiness(self, analysis_data: Dict) -> Dict:
        """Analyze creditworthiness for lending decision"""
        try:
            customer_id = analysis_data['customer_id']
            requested_amount = Decimal(str(analysis_data['requested_amount']))
            loan_type = analysis_data['loan_type']
            
            # Get or calculate credit score
            credit_score = analysis_data.get('credit_score')
            if not credit_score:
                score_result = await self.calculate_credit_score(analysis_data)
                if not score_result['success']:
                    return score_result
                credit_score = score_result['credit_score']
            
            # Analyze debt-to-income ratio
            monthly_income = Decimal(str(analysis_data.get('monthly_income', 0)))
            monthly_debt = Decimal(str(analysis_data.get('monthly_debt', 0)))
            proposed_payment = Decimal(str(analysis_data.get('proposed_payment', 0)))
            
            if monthly_income > 0:
                current_dti = float(monthly_debt / monthly_income)
                new_dti = float((monthly_debt + proposed_payment) / monthly_income)
            else:
                current_dti = 1.0
                new_dti = 1.0
            
            # Analyze credit utilization
            credit_accounts = analysis_data.get('credit_accounts', [])
            utilization = self._calculate_overall_utilization(credit_accounts)
            
            # Risk assessment
            risk_factors = []
            approval_probability = 1.0
            
            # Credit score impact (40% weight)
            if credit_score >= 750:
                approval_probability *= 0.95
            elif credit_score >= 700:
                approval_probability *= 0.85
                risk_factors.append("Credit score below 750")
            elif credit_score >= 650:
                approval_probability *= 0.70
                risk_factors.append("Credit score below 700")
            elif credit_score >= 600:
                approval_probability *= 0.50
                risk_factors.append("Credit score below 650")
            else:
                approval_probability *= 0.25
                risk_factors.append("Credit score below 600")
            
            # DTI impact (30% weight)
            if new_dti <= 0.28:
                approval_probability *= 0.95
            elif new_dti <= 0.36:
                approval_probability *= 0.85
                risk_factors.append("DTI ratio elevated")
            elif new_dti <= 0.43:
                approval_probability *= 0.70
                risk_factors.append("DTI ratio high")
            else:
                approval_probability *= 0.40
                risk_factors.append("DTI ratio excessive")
            
            # Utilization impact (20% weight)
            if utilization <= 0.10:
                approval_probability *= 0.98
            elif utilization <= 0.30:
                approval_probability *= 0.90
            elif utilization <= 0.50:
                approval_probability *= 0.80
                risk_factors.append("High credit utilization")
            else:
                approval_probability *= 0.60
                risk_factors.append("Very high credit utilization")
            
            # Determine recommendation
            if approval_probability >= 0.80:
                recommendation = "APPROVE"
                risk_rating = "LOW"
            elif approval_probability >= 0.60:
                recommendation = "APPROVE_WITH_CONDITIONS"
                risk_rating = "MEDIUM"
            elif approval_probability >= 0.40:
                recommendation = "MANUAL_REVIEW"
                risk_rating = "HIGH"
            else:
                recommendation = "DECLINE"
                risk_rating = "VERY_HIGH"
            
            return {
                'success': True,
                'customer_id': customer_id,
                'credit_score': credit_score,
                'approval_probability': round(approval_probability * 100, 2),
                'recommendation': recommendation,
                'risk_rating': risk_rating,
                'current_dti': round(current_dti * 100, 2),
                'new_dti': round(new_dti * 100, 2),
                'credit_utilization': round(utilization * 100, 2),
                'risk_factors': risk_factors,
                'analysis_date': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error analyzing creditworthiness: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_payment_history_score(self, payment_history: Dict) -> float:
        """Calculate payment history score (35% of FICO)"""
        if not payment_history:
            return 50.0  # Below average if no history
        
        on_time_payments = payment_history.get('on_time_payments', 0)
        total_payments = payment_history.get('total_payments', 1)
        late_payments = payment_history.get('late_payments', {})
        
        if total_payments == 0:
            return 50.0
        
        on_time_ratio = on_time_payments / total_payments
        
        # Deduct for late payments
        score = on_time_ratio * 100
        score -= late_payments.get('30_days', 0) * 2
        score -= late_payments.get('60_days', 0) * 5
        score -= late_payments.get('90_days', 0) * 10
        score -= late_payments.get('120_plus_days', 0) * 15
        
        return max(min(score, 100), 0)
    
    def _calculate_utilization_score(self, credit_accounts: List[Dict]) -> float:
        """Calculate credit utilization score (30% of FICO)"""
        if not credit_accounts:
            return 50.0
        
        total_limits = sum(Decimal(str(acc.get('credit_limit', 0))) for acc in credit_accounts)
        total_balances = sum(Decimal(str(acc.get('balance', 0))) for acc in credit_accounts)
        
        if total_limits == 0:
            return 50.0
        
        utilization = float(total_balances / total_limits)
        
        # Optimal utilization is around 1-9%
        if utilization <= 0.01:
            return 95
        elif utilization <= 0.09:
            return 100
        elif utilization <= 0.20:
            return 90 - (utilization - 0.09) * 200  # Decline rapidly
        elif utilization <= 0.30:
            return 70 - (utilization - 0.20) * 100
        elif utilization <= 0.50:
            return 60 - (utilization - 0.30) * 50
        else:
            return max(10, 50 - (utilization - 0.50) * 40)
    
    def _calculate_credit_age_score(self, credit_accounts: List[Dict]) -> float:
        """Calculate credit history age score (15% of FICO)"""
        if not credit_accounts:
            return 20.0  # Very poor if no accounts
        
        account_ages = []
        for account in credit_accounts:
            opened_date = account.get('opened_date')
            if opened_date:
                if isinstance(opened_date, str):
                    opened_date = datetime.fromisoformat(opened_date.replace('Z', '+00:00'))
                age_months = (datetime.now() - opened_date).days / 30.44
                account_ages.append(age_months)
        
        if not account_ages:
            return 20.0
        
        avg_age_months = sum(account_ages) / len(account_ages)
        oldest_account_months = max(account_ages)
        
        # Score based on average age and oldest account
        age_score = min(avg_age_months / 120 * 60, 60)  # 60 points for 10+ years avg
        oldest_score = min(oldest_account_months / 240 * 40, 40)  # 40 points for 20+ years oldest
        
        return age_score + oldest_score
    
    def _calculate_credit_mix_score(self, credit_accounts: List[Dict]) -> float:
        """Calculate credit mix score (10% of FICO)"""
        if not credit_accounts:
            return 30.0
        
        account_types = set(acc.get('account_type', '').lower() for acc in credit_accounts)
        
        # Ideal mix includes revolving and installment credit
        score = 50
        if 'credit_card' in account_types or 'revolving' in account_types:
            score += 20
        if any(t in account_types for t in ['mortgage', 'auto', 'installment']):
            score += 20
        if 'retail_card' in account_types:
            score += 5
        if len(account_types) >= 4:
            score += 5
        
        return min(score, 100)
    
    def _calculate_inquiry_score(self, inquiries: List[Dict]) -> float:
        """Calculate new credit inquiries score (10% of FICO)"""
        if not inquiries:
            return 90.0
        
        # Count hard inquiries in last 12 months
        twelve_months_ago = datetime.now() - timedelta(days=365)
        recent_inquiries = [
            inq for inq in inquiries
            if inq.get('type') == 'hard' and 
            datetime.fromisoformat(inq.get('date', '2020-01-01')) > twelve_months_ago
        ]
        
        inquiry_count = len(recent_inquiries)
        
        # Deduct points for each inquiry
        score = 100 - (inquiry_count * 15)
        return max(score, 20)
    
    def _calculate_overall_utilization(self, credit_accounts: List[Dict]) -> float:
        """Calculate overall credit utilization ratio"""
        if not credit_accounts:
            return 0.0
        
        total_limits = sum(Decimal(str(acc.get('credit_limit', 0))) for acc in credit_accounts)
        total_balances = sum(Decimal(str(acc.get('balance', 0))) for acc in credit_accounts)
        
        if total_limits == 0:
            return 0.0
        
        return float(total_balances / total_limits)
    
    def _calculate_average_age_months(self, credit_accounts: List[Dict]) -> int:
        """Calculate average account age in months"""
        if not credit_accounts:
            return 0
        
        account_ages = []
        for account in credit_accounts:
            opened_date = account.get('opened_date')
            if opened_date:
                if isinstance(opened_date, str):
                    opened_date = datetime.fromisoformat(opened_date.replace('Z', '+00:00'))
                age_months = (datetime.now() - opened_date).days / 30.44
                account_ages.append(age_months)
        
        return int(sum(account_ages) / len(account_ages)) if account_ages else 0
    
    def _get_credit_grade(self, score: int) -> CreditGrade:
        """Get credit grade from score"""
        if score >= 800:
            return CreditGrade.EXCELLENT
        elif score >= 740:
            return CreditGrade.VERY_GOOD
        elif score >= 670:
            return CreditGrade.GOOD
        elif score >= 580:
            return CreditGrade.FAIR
        else:
            return CreditGrade.POOR
    
    def _get_risk_level(self, score: int, public_records: List[Dict]) -> RiskLevel:
        """Determine risk level"""
        # Check for serious derogatory marks
        has_bankruptcy = any(rec.get('type') == 'bankruptcy' for rec in public_records)
        has_recent_derogatory = any(
            (datetime.now() - datetime.fromisoformat(rec.get('date', '2020-01-01'))).days < 1095
            for rec in public_records
        )
        
        if has_bankruptcy or has_recent_derogatory:
            return RiskLevel.VERY_HIGH
        elif score < 600:
            return RiskLevel.VERY_HIGH
        elif score < 650:
            return RiskLevel.HIGH
        elif score < 700:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _get_score_factors(self, payment: float, utilization: float, age: float, mix: float, inquiry: float) -> Dict:
        """Get factors affecting credit score"""
        return {
            'payment_history': {
                'score': round(payment, 1),
                'weight': '35%',
                'description': 'Payment history on credit accounts'
            },
            'credit_utilization': {
                'score': round(utilization, 1),
                'weight': '30%',
                'description': 'Amount owed vs available credit'
            },
            'credit_age': {
                'score': round(age, 1),
                'weight': '15%',
                'description': 'Length of credit history'
            },
            'credit_mix': {
                'score': round(mix, 1),
                'weight': '10%',
                'description': 'Types of credit accounts'
            },
            'new_credit': {
                'score': round(inquiry, 1),
                'weight': '10%',
                'description': 'Recent credit inquiries'
            }
        }
    
    async def _monitoring_loop(self):
        """Background monitoring loop"""
        while self.monitoring_active:
            try:
                await self._check_credit_changes()
                await asyncio.sleep(86400)  # Check daily
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(86400)
    
    async def _check_credit_changes(self):
        """Check for credit score changes"""
        for monitoring in self.monitoring_accounts.values():
            if monitoring.active:
                # In production, this would fetch new credit data
                logger.info(f"Monitoring credit for customer {monitoring.customer_id}")