import uuid
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from decimal import Decimal
from ..core.config import settings
import logging
import hashlib
import re

logger = logging.getLogger(__name__)

class KYCStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_ADDITIONAL_INFO = "requires_additional_info"
    EXPIRED = "expired"

class DocumentType(Enum):
    DRIVERS_LICENSE = "drivers_license"
    PASSPORT = "passport"
    STATE_ID = "state_id"
    SSN_CARD = "ssn_card"
    UTILITY_BILL = "utility_bill"
    BANK_STATEMENT = "bank_statement"
    TAX_RETURN = "tax_return"
    ARTICLES_OF_INCORPORATION = "articles_of_incorporation"
    EIN_LETTER = "ein_letter"

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    PROHIBITED = "prohibited"

class AMLReportType(Enum):
    SAR = "sar"  # Suspicious Activity Report
    CTR = "ctr"  # Currency Transaction Report
    BSA = "bsa"  # Bank Secrecy Act

@dataclass
class KYCDocument:
    document_id: str
    customer_id: str
    document_type: DocumentType
    document_number: str
    issued_date: datetime
    expiry_date: Optional[datetime]
    issuing_authority: str
    verification_status: str
    uploaded_at: datetime
    verified_at: Optional[datetime]
    file_hash: str

@dataclass
class CustomerProfile:
    customer_id: str
    kyc_status: KYCStatus
    risk_level: RiskLevel
    first_name: str
    last_name: str
    date_of_birth: datetime
    ssn_encrypted: str
    address: Dict
    phone: str
    email: str
    occupation: str
    income_range: str
    source_of_funds: str
    politically_exposed_person: bool
    sanctions_screening_date: Optional[datetime]
    sanctions_status: str
    documents: List[KYCDocument]
    created_at: datetime
    last_updated: datetime
    next_review_date: datetime

@dataclass
class SuspiciousActivity:
    activity_id: str
    customer_id: str
    account_id: str
    activity_type: str
    description: str
    amount: Optional[Decimal]
    transaction_pattern: str
    risk_score: float
    detected_at: datetime
    status: str
    investigator_notes: str
    sar_filed: bool
    sar_number: Optional[str]

class KYCAMLService:
    def __init__(self):
        self.customer_profiles = {}
        self.documents = {}
        self.suspicious_activities = {}
        self.watchlists = {
            'ofac': self._load_ofac_list(),
            'pep': self._load_pep_list(),
            'sanctions': self._load_sanctions_list()
        }
        self.aml_rules = self._initialize_aml_rules()
        
    async def initiate_kyc(self, customer_data: Dict) -> Dict:
        """Initiate KYC process for a new customer"""
        try:
            customer_id = customer_data.get('customer_id', str(uuid.uuid4()))
            
            # Encrypt sensitive data
            ssn_encrypted = self._encrypt_ssn(customer_data.get('ssn', ''))
            
            profile = CustomerProfile(
                customer_id=customer_id,
                kyc_status=KYCStatus.NOT_STARTED,
                risk_level=RiskLevel.MEDIUM,  # Default to medium, will be reassessed
                first_name=customer_data.get('first_name', ''),
                last_name=customer_data.get('last_name', ''),
                date_of_birth=datetime.fromisoformat(customer_data.get('date_of_birth')),
                ssn_encrypted=ssn_encrypted,
                address=customer_data.get('address', {}),
                phone=customer_data.get('phone', ''),
                email=customer_data.get('email', ''),
                occupation=customer_data.get('occupation', ''),
                income_range=customer_data.get('income_range', ''),
                source_of_funds=customer_data.get('source_of_funds', ''),
                politically_exposed_person=False,
                sanctions_screening_date=None,
                sanctions_status='pending',
                documents=[],
                created_at=datetime.now(),
                last_updated=datetime.now(),
                next_review_date=datetime.now() + timedelta(days=365)
            )
            
            self.customer_profiles[customer_id] = profile
            
            # Start screening processes
            screening_result = await self._perform_initial_screening(customer_id)
            
            # Update status based on screening
            if screening_result['passed']:
                profile.kyc_status = KYCStatus.IN_PROGRESS
                profile.sanctions_status = 'clear'
            else:
                profile.kyc_status = KYCStatus.REJECTED
                profile.sanctions_status = 'blocked'
                profile.risk_level = RiskLevel.PROHIBITED
            
            profile.sanctions_screening_date = datetime.now()
            profile.last_updated = datetime.now()
            
            logger.info(f"KYC initiated for customer: {customer_id}")
            
            return {
                'success': True,
                'customer_id': customer_id,
                'kyc_status': profile.kyc_status.value,
                'risk_level': profile.risk_level.value,
                'sanctions_status': profile.sanctions_status,
                'required_documents': self._get_required_documents(profile),
                'screening_result': screening_result
            }
        
        except Exception as e:
            logger.error(f"Error initiating KYC: {e}")
            return {'success': False, 'error': str(e)}
    
    async def upload_document(self, customer_id: str, document_data: Dict) -> Dict:
        """Upload and verify KYC document"""
        try:
            if customer_id not in self.customer_profiles:
                return {'success': False, 'error': 'Customer not found'}
            
            profile = self.customer_profiles[customer_id]
            
            if profile.kyc_status not in [KYCStatus.IN_PROGRESS, KYCStatus.REQUIRES_ADDITIONAL_INFO]:
                return {'success': False, 'error': 'KYC not in progress'}
            
            document_id = str(uuid.uuid4())
            file_hash = hashlib.sha256(document_data.get('file_content', '').encode()).hexdigest()
            
            document = KYCDocument(
                document_id=document_id,
                customer_id=customer_id,
                document_type=DocumentType(document_data['document_type']),
                document_number=document_data.get('document_number', ''),
                issued_date=datetime.fromisoformat(document_data.get('issued_date')),
                expiry_date=datetime.fromisoformat(document_data['expiry_date']) if document_data.get('expiry_date') else None,
                issuing_authority=document_data.get('issuing_authority', ''),
                verification_status='pending',
                uploaded_at=datetime.now(),
                verified_at=None,
                file_hash=file_hash
            )
            
            self.documents[document_id] = document
            profile.documents.append(document)
            
            # Perform document verification
            verification_result = await self._verify_document(document)
            
            document.verification_status = verification_result['status']
            if verification_result['verified']:
                document.verified_at = datetime.now()
            
            # Check if all required documents are provided
            completion_check = await self._check_kyc_completion(customer_id)
            
            if completion_check['complete']:
                profile.kyc_status = KYCStatus.PENDING_REVIEW
                # Schedule review
                asyncio.create_task(self._schedule_kyc_review(customer_id))
            
            profile.last_updated = datetime.now()
            
            return {
                'success': True,
                'document_id': document_id,
                'verification_status': document.verification_status,
                'kyc_status': profile.kyc_status.value,
                'completion_status': completion_check
            }
        
        except Exception as e:
            logger.error(f"Error uploading document: {e}")
            return {'success': False, 'error': str(e)}
    
    async def perform_transaction_monitoring(self, transaction_data: Dict) -> Dict:
        """Monitor transaction for suspicious activity"""
        try:
            customer_id = transaction_data.get('customer_id')
            account_id = transaction_data.get('account_id')
            amount = Decimal(str(transaction_data.get('amount', 0)))
            transaction_type = transaction_data.get('transaction_type')
            
            alerts = []
            
            # Check against AML rules
            for rule in self.aml_rules:
                if await self._evaluate_aml_rule(rule, transaction_data):
                    alerts.append({
                        'rule_id': rule['rule_id'],
                        'rule_name': rule['name'],
                        'severity': rule['severity'],
                        'description': rule['description']
                    })
            
            # Currency Transaction Report (CTR) check
            if amount >= Decimal(str(settings.CTR_THRESHOLD)):
                await self._generate_ctr(transaction_data)
                alerts.append({
                    'rule_id': 'CTR_REQUIRED',
                    'rule_name': 'Currency Transaction Report',
                    'severity': 'high',
                    'description': f'Transaction amount ${amount} requires CTR filing'
                })
            
            # Suspicious Activity Report (SAR) check
            suspicious_score = await self._calculate_suspicion_score(transaction_data)
            
            if suspicious_score > 70:
                activity_id = await self._create_suspicious_activity(transaction_data, suspicious_score)
                alerts.append({
                    'rule_id': 'SAR_CANDIDATE',
                    'rule_name': 'Suspicious Activity Detected',
                    'severity': 'critical',
                    'description': f'Suspicious score: {suspicious_score}',
                    'activity_id': activity_id
                })
            
            return {
                'success': True,
                'monitoring_result': {
                    'alerts_triggered': len(alerts),
                    'alerts': alerts,
                    'suspicion_score': suspicious_score,
                    'action_required': len([a for a in alerts if a['severity'] in ['high', 'critical']]) > 0
                }
            }
        
        except Exception as e:
            logger.error(f"Error in transaction monitoring: {e}")
            return {'success': False, 'error': str(e)}
    
    async def get_kyc_status(self, customer_id: str) -> Dict:
        """Get KYC status and requirements"""
        try:
            if customer_id not in self.customer_profiles:
                return {'success': False, 'error': 'Customer not found'}
            
            profile = self.customer_profiles[customer_id]
            
            return {
                'success': True,
                'customer_id': customer_id,
                'kyc_status': profile.kyc_status.value,
                'risk_level': profile.risk_level.value,
                'sanctions_status': profile.sanctions_status,
                'last_screening': profile.sanctions_screening_date.isoformat() if profile.sanctions_screening_date else None,
                'next_review': profile.next_review_date.isoformat(),
                'documents_submitted': len(profile.documents),
                'documents_verified': len([d for d in profile.documents if d.verification_status == 'verified']),
                'required_documents': self._get_required_documents(profile),
                'compliance_score': await self._calculate_compliance_score(customer_id)
            }
        
        except Exception as e:
            logger.error(f"Error getting KYC status: {e}")
            return {'success': False, 'error': str(e)}
    
    async def generate_compliance_report(self, report_type: str, start_date: datetime, end_date: datetime) -> Dict:
        """Generate compliance reports"""
        try:
            if report_type == 'sar':
                return await self._generate_sar_report(start_date, end_date)
            elif report_type == 'ctr':
                return await self._generate_ctr_report(start_date, end_date)
            elif report_type == 'kyc_summary':
                return await self._generate_kyc_summary_report(start_date, end_date)
            elif report_type == 'risk_assessment':
                return await self._generate_risk_assessment_report()
            else:
                return {'success': False, 'error': 'Invalid report type'}
        
        except Exception as e:
            logger.error(f"Error generating compliance report: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _perform_initial_screening(self, customer_id: str) -> Dict:
        """Perform initial sanctions and watchlist screening"""
        profile = self.customer_profiles[customer_id]
        
        # Check OFAC sanctions list
        ofac_match = await self._check_sanctions_list(
            profile.first_name, profile.last_name, profile.address
        )
        
        # Check PEP (Politically Exposed Person) list
        pep_match = await self._check_pep_list(
            profile.first_name, profile.last_name, profile.occupation
        )
        
        if pep_match:
            profile.politically_exposed_person = True
            profile.risk_level = RiskLevel.HIGH
        
        # Additional risk factors
        risk_factors = []
        if profile.occupation.lower() in ['politician', 'government official', 'diplomat']:
            risk_factors.append('High-risk occupation')
            profile.risk_level = RiskLevel.HIGH
        
        if profile.address.get('country', '').upper() in ['IR', 'KP', 'SY']:  # High-risk countries
            risk_factors.append('High-risk country')
            profile.risk_level = RiskLevel.HIGH
        
        passed = not ofac_match and profile.risk_level != RiskLevel.PROHIBITED
        
        return {
            'passed': passed,
            'ofac_match': ofac_match,
            'pep_match': pep_match,
            'risk_factors': risk_factors,
            'final_risk_level': profile.risk_level.value
        }
    
    async def _verify_document(self, document: KYCDocument) -> Dict:
        """Verify uploaded document"""
        # Mock document verification - in production would use OCR and validation services
        
        # Basic validation
        if document.expiry_date and document.expiry_date < datetime.now():
            return {'verified': False, 'status': 'expired', 'reason': 'Document has expired'}
        
        # Document number validation
        if document.document_type == DocumentType.SSN_CARD:
            if not self._validate_ssn_format(document.document_number):
                return {'verified': False, 'status': 'invalid', 'reason': 'Invalid SSN format'}
        
        # Simulate verification success (90% success rate)
        import random
        if random.random() > 0.1:
            return {'verified': True, 'status': 'verified', 'reason': 'Document verified successfully'}
        else:
            return {'verified': False, 'status': 'rejected', 'reason': 'Document could not be verified'}
    
    def _get_required_documents(self, profile: CustomerProfile) -> List[str]:
        """Get list of required documents based on customer profile"""
        required = ['drivers_license', 'utility_bill']
        
        if profile.risk_level == RiskLevel.HIGH:
            required.extend(['tax_return', 'bank_statement'])
        
        if profile.politically_exposed_person:
            required.append('source_of_funds_declaration')
        
        # Remove already submitted documents
        submitted_types = [doc.document_type.value for doc in profile.documents]
        return [doc for doc in required if doc not in submitted_types]
    
    async def _check_kyc_completion(self, customer_id: str) -> Dict:
        """Check if KYC is complete"""
        profile = self.customer_profiles[customer_id]
        required_docs = self._get_required_documents(profile)
        verified_docs = [doc for doc in profile.documents if doc.verification_status == 'verified']
        
        return {
            'complete': len(required_docs) == 0 and len(verified_docs) >= 2,
            'required_documents': required_docs,
            'verified_documents': len(verified_docs),
            'completion_percentage': min(100, (len(verified_docs) / max(len(required_docs) + len(verified_docs), 1)) * 100)
        }
    
    async def _schedule_kyc_review(self, customer_id: str):
        """Schedule KYC review"""
        try:
            # Simulate review delay
            await asyncio.sleep(10)  # In production, this would be hours/days
            
            profile = self.customer_profiles[customer_id]
            
            # Automated review logic
            verified_docs = [doc for doc in profile.documents if doc.verification_status == 'verified']
            
            if len(verified_docs) >= 2 and profile.sanctions_status == 'clear':
                profile.kyc_status = KYCStatus.APPROVED
                profile.next_review_date = datetime.now() + timedelta(days=365)
                logger.info(f"KYC approved for customer: {customer_id}")
            else:
                profile.kyc_status = KYCStatus.REQUIRES_ADDITIONAL_INFO
                logger.warning(f"KYC requires additional info for customer: {customer_id}")
            
            profile.last_updated = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in KYC review for customer {customer_id}: {e}")
    
    def _initialize_aml_rules(self) -> List[Dict]:
        """Initialize AML monitoring rules"""
        return [
            {
                'rule_id': 'LARGE_CASH_DEPOSIT',
                'name': 'Large Cash Deposit',
                'description': 'Cash deposit over $10,000',
                'severity': 'high',
                'condition': lambda tx: tx.get('transaction_type') == 'deposit' and 
                            tx.get('payment_method') == 'cash' and 
                            float(tx.get('amount', 0)) > 10000
            },
            {
                'rule_id': 'RAPID_MOVEMENT',
                'name': 'Rapid Fund Movement',
                'description': 'Multiple large transactions in short period',
                'severity': 'medium',
                'condition': lambda tx: self._check_rapid_movement(tx)
            },
            {
                'rule_id': 'STRUCTURING',
                'name': 'Potential Structuring',
                'description': 'Multiple transactions just under reporting threshold',
                'severity': 'high',
                'condition': lambda tx: self._check_structuring_pattern(tx)
            },
            {
                'rule_id': 'UNUSUAL_LOCATION',
                'name': 'Unusual Location',
                'description': 'Transaction from unusual geographic location',
                'severity': 'low',
                'condition': lambda tx: self._check_unusual_location(tx)
            }
        ]
    
    async def _evaluate_aml_rule(self, rule: Dict, transaction_data: Dict) -> bool:
        """Evaluate AML rule against transaction"""
        try:
            return rule['condition'](transaction_data)
        except Exception as e:
            logger.error(f"Error evaluating AML rule {rule['rule_id']}: {e}")
            return False
    
    def _check_rapid_movement(self, transaction_data: Dict) -> bool:
        """Check for rapid fund movement pattern"""
        # Mock implementation - would check transaction history
        return False
    
    def _check_structuring_pattern(self, transaction_data: Dict) -> bool:
        """Check for potential structuring pattern"""
        amount = float(transaction_data.get('amount', 0))
        return 9000 <= amount <= 9999  # Just under $10k threshold
    
    def _check_unusual_location(self, transaction_data: Dict) -> bool:
        """Check for transactions from unusual locations"""
        # Mock implementation - would check against customer's typical locations
        return False
    
    async def _calculate_suspicion_score(self, transaction_data: Dict) -> float:
        """Calculate suspicion score for transaction"""
        score = 0.0
        
        amount = float(transaction_data.get('amount', 0))
        
        # Amount-based scoring
        if amount > 50000:
            score += 30
        elif amount > 25000:
            score += 20
        elif amount > 10000:
            score += 10
        
        # Cash transactions
        if transaction_data.get('payment_method') == 'cash':
            score += 15
        
        # Time-based patterns (mock)
        hour = datetime.now().hour
        if hour < 6 or hour > 22:  # Late night/early morning
            score += 10
        
        return min(100, score)
    
    async def _create_suspicious_activity(self, transaction_data: Dict, suspicion_score: float) -> str:
        """Create suspicious activity record"""
        activity_id = str(uuid.uuid4())
        
        activity = SuspiciousActivity(
            activity_id=activity_id,
            customer_id=transaction_data.get('customer_id'),
            account_id=transaction_data.get('account_id'),
            activity_type='transaction',
            description=f"Suspicious transaction detected with score {suspicion_score}",
            amount=Decimal(str(transaction_data.get('amount', 0))),
            transaction_pattern='high_risk',
            risk_score=suspicion_score,
            detected_at=datetime.now(),
            status='pending_investigation',
            investigator_notes='',
            sar_filed=False,
            sar_number=None
        )
        
        self.suspicious_activities[activity_id] = activity
        
        # Auto-file SAR for very high scores
        if suspicion_score > 85:
            await self._auto_file_sar(activity_id)
        
        logger.warning(f"Suspicious activity created: {activity_id} with score {suspicion_score}")
        return activity_id
    
    async def _auto_file_sar(self, activity_id: str):
        """Automatically file SAR for high-risk activities"""
        activity = self.suspicious_activities[activity_id]
        
        sar_number = f"SAR{datetime.now().strftime('%Y%m%d')}{len(self.suspicious_activities):04d}"
        activity.sar_filed = True
        activity.sar_number = sar_number
        activity.status = 'sar_filed'
        
        logger.critical(f"SAR automatically filed: {sar_number} for activity: {activity_id}")
    
    async def _generate_ctr(self, transaction_data: Dict):
        """Generate Currency Transaction Report"""
        ctr_number = f"CTR{datetime.now().strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"
        
        ctr_data = {
            'ctr_number': ctr_number,
            'customer_id': transaction_data.get('customer_id'),
            'transaction_amount': transaction_data.get('amount'),
            'transaction_date': datetime.now().isoformat(),
            'filing_date': datetime.now().isoformat(),
            'status': 'filed'
        }
        
        logger.info(f"CTR filed: {ctr_number} for amount ${transaction_data.get('amount')}")
        return ctr_data
    
    def _load_ofac_list(self) -> List[Dict]:
        """Load OFAC sanctions list (mock)"""
        return [
            {'name': 'BLOCKED PERSON', 'type': 'individual'},
            {'name': 'SANCTIONED ENTITY', 'type': 'entity'}
        ]
    
    def _load_pep_list(self) -> List[Dict]:
        """Load Politically Exposed Persons list (mock)"""
        return [
            {'name': 'POLITICAL FIGURE', 'position': 'Government Official'}
        ]
    
    def _load_sanctions_list(self) -> List[Dict]:
        """Load additional sanctions lists (mock)"""
        return []
    
    async def _check_sanctions_list(self, first_name: str, last_name: str, address: Dict) -> bool:
        """Check against sanctions lists"""
        full_name = f"{first_name} {last_name}".upper()
        
        for entry in self.watchlists['ofac']:
            if entry['name'] in full_name or full_name in entry['name']:
                return True
        
        return False
    
    async def _check_pep_list(self, first_name: str, last_name: str, occupation: str) -> bool:
        """Check against PEP list"""
        full_name = f"{first_name} {last_name}".upper()
        
        for entry in self.watchlists['pep']:
            if entry['name'] in full_name or full_name in entry['name']:
                return True
        
        # Check occupation-based PEP indicators
        high_risk_occupations = ['politician', 'government official', 'diplomat', 'military officer']
        return any(occ in occupation.lower() for occ in high_risk_occupations)
    
    def _encrypt_ssn(self, ssn: str) -> str:
        """Encrypt SSN (mock encryption)"""
        if not ssn:
            return ""
        return hashlib.sha256((ssn + settings.ENCRYPTION_KEY).encode()).hexdigest()
    
    def _validate_ssn_format(self, ssn: str) -> bool:
        """Validate SSN format"""
        pattern = r'^\d{3}-?\d{2}-?\d{4}$'
        return bool(re.match(pattern, ssn))
    
    async def _calculate_compliance_score(self, customer_id: str) -> float:
        """Calculate compliance score for customer"""
        profile = self.customer_profiles[customer_id]
        score = 0.0
        
        # KYC status scoring
        kyc_scores = {
            KYCStatus.APPROVED: 40,
            KYCStatus.PENDING_REVIEW: 25,
            KYCStatus.IN_PROGRESS: 15,
            KYCStatus.NOT_STARTED: 0,
            KYCStatus.REJECTED: 0
        }
        score += kyc_scores.get(profile.kyc_status, 0)
        
        # Document verification scoring
        verified_docs = [doc for doc in profile.documents if doc.verification_status == 'verified']
        score += min(30, len(verified_docs) * 10)
        
        # Risk level scoring
        risk_scores = {
            RiskLevel.LOW: 20,
            RiskLevel.MEDIUM: 15,
            RiskLevel.HIGH: 10,
            RiskLevel.PROHIBITED: 0
        }
        score += risk_scores.get(profile.risk_level, 0)
        
        # Sanctions screening scoring
        if profile.sanctions_status == 'clear':
            score += 10
        
        return min(100, score)
    
    async def _generate_sar_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate SAR summary report"""
        sars_filed = [
            activity for activity in self.suspicious_activities.values()
            if activity.sar_filed and start_date <= activity.detected_at <= end_date
        ]
        
        return {
            'success': True,
            'report_type': 'SAR Summary',
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_sars': len(sars_filed),
            'total_amount': float(sum(activity.amount or Decimal('0') for activity in sars_filed)),
            'sars': [
                {
                    'sar_number': activity.sar_number,
                    'customer_id': activity.customer_id,
                    'amount': float(activity.amount) if activity.amount else 0,
                    'activity_type': activity.activity_type,
                    'risk_score': activity.risk_score,
                    'detected_at': activity.detected_at.isoformat()
                }
                for activity in sars_filed
            ]
        }
    
    async def _generate_ctr_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate CTR summary report"""
        # Mock CTR data
        return {
            'success': True,
            'report_type': 'CTR Summary',
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_ctrs': 0,
            'total_amount': 0.0,
            'ctrs': []
        }
    
    async def _generate_kyc_summary_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """Generate KYC summary report"""
        relevant_profiles = [
            profile for profile in self.customer_profiles.values()
            if start_date <= profile.created_at <= end_date
        ]
        
        status_counts = {}
        risk_counts = {}
        
        for profile in relevant_profiles:
            status = profile.kyc_status.value
            risk = profile.risk_level.value
            
            status_counts[status] = status_counts.get(status, 0) + 1
            risk_counts[risk] = risk_counts.get(risk, 0) + 1
        
        return {
            'success': True,
            'report_type': 'KYC Summary',
            'period': f"{start_date.date()} to {end_date.date()}",
            'total_customers': len(relevant_profiles),
            'status_breakdown': status_counts,
            'risk_breakdown': risk_counts,
            'approval_rate': (status_counts.get('approved', 0) / max(len(relevant_profiles), 1)) * 100
        }
    
    async def _generate_risk_assessment_report(self) -> Dict:
        """Generate overall risk assessment report"""
        total_customers = len(self.customer_profiles)
        high_risk_customers = len([p for p in self.customer_profiles.values() if p.risk_level == RiskLevel.HIGH])
        pending_kyc = len([p for p in self.customer_profiles.values() if p.kyc_status in [KYCStatus.IN_PROGRESS, KYCStatus.PENDING_REVIEW]])
        
        return {
            'success': True,
            'report_type': 'Risk Assessment',
            'generated_at': datetime.now().isoformat(),
            'total_customers': total_customers,
            'high_risk_customers': high_risk_customers,
            'high_risk_percentage': (high_risk_customers / max(total_customers, 1)) * 100,
            'pending_kyc': pending_kyc,
            'active_investigations': len([a for a in self.suspicious_activities.values() if a.status == 'pending_investigation']),
            'sars_filed_ytd': len([a for a in self.suspicious_activities.values() if a.sar_filed]),
            'recommendations': self._generate_risk_recommendations()
        }
    
    def _generate_risk_recommendations(self) -> List[str]:
        """Generate risk management recommendations"""
        recommendations = []
        
        high_risk_count = len([p for p in self.customer_profiles.values() if p.risk_level == RiskLevel.HIGH])
        
        if high_risk_count > len(self.customer_profiles) * 0.1:
            recommendations.append("High risk customer percentage exceeds 10% - review risk assessment criteria")
        
        pending_investigations = len([a for a in self.suspicious_activities.values() if a.status == 'pending_investigation'])
        if pending_investigations > 5:
            recommendations.append("Multiple pending investigations - consider additional compliance staff")
        
        if not recommendations:
            recommendations.append("Compliance posture is within acceptable parameters")
        
        return recommendations