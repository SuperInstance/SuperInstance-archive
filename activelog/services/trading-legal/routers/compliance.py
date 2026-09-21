from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sqlite3
import uuid
import json
import hashlib

router = APIRouter()

# Pydantic models
class LegalDocument(BaseModel):
    document_id: str
    title: str
    content: str
    version: str
    mandatory: bool
    effective_date: datetime
    last_updated: datetime

class ComplianceCheck(BaseModel):
    user_id: str
    compliance_status: str
    missing_documents: List[str]
    age_verified: bool
    parental_consent_required: bool
    recommendations: List[str]

class DataPrivacySettings(BaseModel):
    user_id: str
    marketing_consent: bool = False
    analytics_consent: bool = True
    third_party_sharing: bool = False
    data_retention_period: int = 365  # days
    
class AuditEvent(BaseModel):
    event_id: str
    user_id: str
    event_type: str
    event_details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str]
    compliance_impact: str

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect('trading_legal.db')

@router.get("/legal-documents")
async def get_legal_documents(required_only: bool = False):
    """Get all legal documents that users must accept"""
    
    documents = [
        {
            "document_id": "paper_trading_disclaimer",
            "title": "PAPER TRADING SIMULATION DISCLAIMER",
            "content": """
            IMPORTANT LEGAL NOTICE - PAPER TRADING SIMULATION ONLY
            
            This platform provides SIMULATED trading for educational purposes ONLY. No real money, securities, 
            or financial instruments are involved in any transactions conducted on this platform.
            
            KEY POINTS:
            • All trades are SIMULATED and do not involve real money
            • No actual securities are bought or sold
            • Market data may be delayed or simulated
            • Performance results are HYPOTHETICAL
            • Past performance does NOT guarantee future results
            
            EDUCATIONAL PURPOSE ONLY:
            This platform is designed solely for educational and training purposes. It is intended to help 
            users learn about trading concepts, strategies, and market mechanics in a risk-free environment.
            
            NO WARRANTY:
            The platform is provided "as is" without warranties of any kind. We do not guarantee the 
            accuracy, completeness, or timeliness of any information or simulation results.
            
            By using this platform, you acknowledge that you understand this is a simulation and does 
            not constitute real trading or investment activity.
            """,
            "version": "2.1",
            "mandatory": True,
            "effective_date": datetime.now(),
            "category": "trading_disclaimer"
        },
        {
            "document_id": "no_financial_advice",
            "title": "NOT FINANCIAL OR INVESTMENT ADVICE",
            "content": """
            IMPORTANT: THIS IS NOT FINANCIAL ADVICE
            
            Nothing on this platform constitutes financial, investment, trading, or other advice.
            
            EDUCATIONAL CONTENT ONLY:
            • All content is for educational and informational purposes only
            • No recommendations are made regarding specific investments
            • No guidance is provided on whether to buy, sell, or hold any security
            • Users must make their own investment decisions
            
            CONSULT PROFESSIONALS:
            Before making any real investment decisions, you should:
            • Consult with qualified financial advisors
            • Seek advice from licensed investment professionals
            • Consider your individual financial situation
            • Understand your risk tolerance
            
            LIABILITY DISCLAIMER:
            We are not responsible for any investment decisions made based on information 
            learned through this educational platform.
            """,
            "version": "2.0",
            "mandatory": True,
            "effective_date": datetime.now(),
            "category": "financial_advice_disclaimer"
        },
        {
            "document_id": "age_requirements",
            "title": "AGE REQUIREMENTS AND RESTRICTIONS",
            "content": """
            AGE VERIFICATION AND PARENTAL CONSENT REQUIREMENTS
            
            COPPA COMPLIANCE:
            For users under 13 years of age:
            • Verifiable parental consent is REQUIRED
            • Parent must create account on child's behalf
            • Parent must supervise all platform use
            • Additional restrictions may apply
            
            MINOR RESTRICTIONS (Ages 13-17):
            • Parental supervision recommended
            • Educational use only - no real trading preparation
            • Limited access to advanced features
            • Progress reports sent to parent/guardian
            
            ADULT USERS (18+):
            • Full platform access
            • Can pursue broker transition tools (21+ recommended)
            • Responsible for own compliance with local laws
            
            INTERNATIONAL USERS:
            Users outside the United States must comply with local laws regarding:
            • Age requirements for financial education
            • Data privacy regulations
            • Educational content restrictions
            """,
            "version": "1.5",
            "mandatory": True,
            "effective_date": datetime.now(),
            "category": "age_compliance"
        },
        {
            "document_id": "data_privacy_notice", 
            "title": "DATA PRIVACY AND PROTECTION NOTICE",
            "content": """
            DATA COLLECTION AND PRIVACY NOTICE
            
            MINIMAL DATA COLLECTION:
            We collect only the minimum data necessary for educational purposes:
            • Account creation information (email, username)
            • Age verification data (date of birth)
            • Educational progress and performance
            • Paper trading simulation data (NOT real financial data)
            
            NO REAL FINANCIAL DATA:
            • No real bank account information
            • No real brokerage account details
            • No actual trading positions or balances
            • All financial data is simulated
            
            DATA USE:
            Your data is used only for:
            • Providing educational services
            • Tracking learning progress
            • Generating educational reports
            • Platform improvement and security
            
            DATA SHARING:
            We do NOT share your data with:
            • Financial institutions
            • Marketing companies
            • Data brokers
            
            Limited sharing only for:
            • Legal compliance requirements
            • Safety and security purposes
            • With explicit consent
            
            PARENTAL RIGHTS:
            Parents of users under 18 can:
            • Request deletion of child's data
            • Access child's educational records
            • Modify privacy settings
            • Withdraw consent at any time
            """,
            "version": "1.3",
            "mandatory": False,
            "effective_date": datetime.now(),
            "category": "privacy"
        },
        {
            "document_id": "international_compliance",
            "title": "INTERNATIONAL LAW COMPLIANCE",
            "content": """
            INTERNATIONAL TRADING LAW COMPLIANCE
            
            JURISDICTION RESTRICTIONS:
            This educational platform is not available in jurisdictions where:
            • Financial education platforms are prohibited
            • Age restrictions prevent access
            • Data privacy laws conflict with our practices
            
            CURRENTLY RESTRICTED REGIONS:
            • Countries under international sanctions
            • Regions where financial simulation is regulated as actual trading
            • Jurisdictions requiring specific financial education licensing
            
            USER RESPONSIBILITIES:
            International users must:
            • Comply with local laws regarding financial education
            • Verify that platform use is permitted in their jurisdiction
            • Understand that this is US-based educational content
            • Not use platform if prohibited by local law
            
            GDPR COMPLIANCE (EU Users):
            • Right to data portability
            • Right to be forgotten
            • Data processing consent
            • Privacy by design implementation
            
            DISCLAIMER:
            We are not responsible for users accessing the platform in violation 
            of their local laws and regulations.
            """,
            "version": "1.2",
            "mandatory": True,
            "effective_date": datetime.now(),
            "category": "international"
        }
    ]
    
    if required_only:
        documents = [doc for doc in documents if doc["mandatory"]]
    
    return {"legal_documents": documents}

@router.post("/verify-compliance")
async def verify_user_compliance(user_id: str, check_type: str = "full"):
    """Verify user compliance with all legal requirements"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check legal document acceptances
    cursor.execute('''
        SELECT document_type, document_version, accepted_at
        FROM legal_acceptances
        WHERE user_id = ? AND is_valid = 1
    ''', (user_id,))
    accepted_docs = cursor.fetchall()
    
    # Check age verification
    cursor.execute('''
        SELECT verification_status, date_of_birth, parent_consent
        FROM age_verifications
        WHERE user_id = ?
        ORDER BY verified_at DESC
        LIMIT 1
    ''', (user_id,))
    age_verification = cursor.fetchone()
    
    conn.close()
    
    # Required documents
    required_documents = [
        "paper_trading_disclaimer",
        "no_financial_advice", 
        "age_requirements",
        "international_compliance"
    ]
    
    # Check compliance
    accepted_doc_types = [doc[0] for doc in accepted_docs]
    missing_documents = [doc for doc in required_documents if doc not in accepted_doc_types]
    
    # Age compliance check
    age_verified = age_verification is not None
    parental_consent_required = False
    
    if age_verification:
        verification_status = age_verification[0]
        if verification_status in ["requires_parent_consent", "pending_parent_verification"]:
            parental_consent_required = True
    
    # Determine overall compliance status
    if missing_documents or (parental_consent_required and not age_verification[2]):
        compliance_status = "non_compliant"
    elif age_verification and age_verification[0] in ["pending_parent_verification"]:
        compliance_status = "pending_verification"
    else:
        compliance_status = "compliant"
    
    # Generate recommendations
    recommendations = []
    if missing_documents:
        recommendations.append(f"Accept required legal documents: {', '.join(missing_documents)}")
    if not age_verified:
        recommendations.append("Complete age verification process")
    if parental_consent_required:
        recommendations.append("Obtain parental consent for account use")
    
    return ComplianceCheck(
        user_id=user_id,
        compliance_status=compliance_status,
        missing_documents=missing_documents,
        age_verified=age_verified,
        parental_consent_required=parental_consent_required,
        recommendations=recommendations
    )

@router.post("/record-audit-event")
async def record_audit_event(
    user_id: str,
    event_type: str,
    event_details: Dict[str, Any],
    request: Request
):
    """Record compliance audit event"""
    
    event_id = str(uuid.uuid4())
    client_ip = request.client.host
    
    # Determine compliance impact
    high_impact_events = ["document_declined", "age_verification_failed", "unauthorized_access"]
    compliance_impact = "high" if event_type in high_impact_events else "medium"
    
    # Store audit event (in real implementation, this might go to a dedicated audit system)
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create audit events table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_details TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ip_address TEXT,
            compliance_impact TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT INTO audit_events
        (event_id, user_id, event_type, event_details, ip_address, compliance_impact)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (event_id, user_id, event_type, json.dumps(event_details), client_ip, compliance_impact))
    
    conn.commit()
    conn.close()
    
    return {
        "event_id": event_id,
        "message": "Audit event recorded",
        "compliance_impact": compliance_impact
    }

@router.get("/privacy-settings/{user_id}")
async def get_privacy_settings(user_id: str):
    """Get user privacy settings"""
    
    # Default privacy settings (GDPR compliant)
    default_settings = {
        "marketing_consent": False,
        "analytics_consent": True,  # Necessary for service
        "third_party_sharing": False,
        "data_retention_period": 365,
        "cookie_preferences": {
            "necessary": True,  # Cannot be disabled
            "analytics": False,
            "marketing": False
        },
        "communication_preferences": {
            "educational_updates": True,
            "platform_announcements": True,
            "marketing_emails": False,
            "progress_reports": True
        }
    }
    
    return {
        "user_id": user_id,
        "privacy_settings": default_settings,
        "last_updated": datetime.now(),
        "gdpr_compliant": True
    }

@router.post("/update-privacy-settings")
async def update_privacy_settings(settings: DataPrivacySettings):
    """Update user privacy settings"""
    
    # Validate settings (some settings like necessary cookies cannot be disabled)
    if not settings.analytics_consent:
        raise HTTPException(
            status_code=400,
            detail="Analytics consent is required for basic platform functionality"
        )
    
    # Store settings (simplified - in production this would be in dedicated privacy db)
    return {
        "message": "Privacy settings updated successfully",
        "settings": settings,
        "effective_date": datetime.now()
    }

@router.get("/coppa-compliance-check/{user_id}")
async def coppa_compliance_check(user_id: str):
    """Check COPPA compliance for user"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get age verification
    cursor.execute('''
        SELECT date_of_birth, parent_consent, parent_email, verification_status
        FROM age_verifications
        WHERE user_id = ?
        ORDER BY verified_at DESC
        LIMIT 1
    ''', (user_id,))
    
    verification = cursor.fetchone()
    conn.close()
    
    if not verification:
        return {
            "user_id": user_id,
            "coppa_status": "verification_required",
            "compliant": False,
            "message": "Age verification required"
        }
    
    birth_date, parent_consent, parent_email, status = verification
    
    # Calculate age
    birth_date_obj = datetime.strptime(birth_date, "%Y-%m-%d")
    age = datetime.now().year - birth_date_obj.year
    
    # COPPA compliance check
    if age < 13:
        coppa_compliant = parent_consent and parent_email and status == "pending_parent_verification"
        coppa_status = "requires_parent_consent" if not coppa_compliant else "parent_consent_obtained"
    else:
        coppa_compliant = True
        coppa_status = "not_applicable"
    
    return {
        "user_id": user_id,
        "user_age": age,
        "coppa_status": coppa_status,
        "compliant": coppa_compliant,
        "parent_consent_required": age < 13,
        "restrictions": {
            "limited_data_collection": age < 13,
            "parental_oversight_required": age < 18,
            "educational_only": age < 21
        }
    }

@router.get("/jurisdiction-check")
async def check_jurisdiction_compliance(
    country_code: str,
    region: Optional[str] = None
):
    """Check if platform is compliant in user's jurisdiction"""
    
    # Restricted jurisdictions (mock data)
    restricted_countries = {
        "CN": {"reason": "Great Firewall restrictions", "severity": "blocked"},
        "IR": {"reason": "International sanctions", "severity": "blocked"},
        "KP": {"reason": "International sanctions", "severity": "blocked"},
        "SY": {"reason": "International sanctions", "severity": "blocked"}
    }
    
    # Countries with special requirements
    special_requirements = {
        "GB": ["GDPR compliance", "FCA educational content rules"],
        "DE": ["GDPR compliance", "BaFin educational restrictions"],
        "FR": ["GDPR compliance", "AMF investor protection rules"],
        "CA": ["PIPEDA compliance", "Provincial securities regulations"],
        "AU": ["Privacy Act compliance", "ASIC investor education rules"],
        "JP": ["Personal Information Protection Act", "FSA educational guidelines"]
    }
    
    if country_code in restricted_countries:
        restriction = restricted_countries[country_code]
        return {
            "country_code": country_code,
            "access_permitted": False,
            "restriction_reason": restriction["reason"],
            "severity": restriction["severity"],
            "alternative_access": None
        }
    
    requirements = special_requirements.get(country_code, ["Standard compliance"])
    
    return {
        "country_code": country_code,
        "access_permitted": True,
        "special_requirements": requirements,
        "compliance_status": "compliant",
        "local_disclaimers_required": country_code in special_requirements,
        "data_processing_notes": "GDPR compliant" if country_code in ["GB", "DE", "FR"] else "Standard privacy protection"
    }

@router.get("/compliance-report")
async def generate_compliance_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Generate compliance report for audit purposes"""
    
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = datetime.now().isoformat()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Document acceptance stats
    cursor.execute('''
        SELECT document_type, COUNT(*) as count
        FROM legal_acceptances
        WHERE accepted_at BETWEEN ? AND ?
        GROUP BY document_type
    ''', (start_date, end_date))
    document_stats = cursor.fetchall()
    
    # Age verification stats
    cursor.execute('''
        SELECT verification_status, COUNT(*) as count
        FROM age_verifications
        WHERE verified_at BETWEEN ? AND ?
        GROUP BY verification_status
    ''', (start_date, end_date))
    age_stats = cursor.fetchall()
    
    # Audit events
    cursor.execute('''
        SELECT event_type, compliance_impact, COUNT(*) as count
        FROM audit_events
        WHERE timestamp BETWEEN ? AND ?
        GROUP BY event_type, compliance_impact
    ''', (start_date, end_date))
    audit_stats = cursor.fetchall()
    
    conn.close()
    
    return {
        "report_period": {
            "start_date": start_date,
            "end_date": end_date
        },
        "document_acceptances": [
            {"document_type": doc_type, "acceptances": count}
            for doc_type, count in document_stats
        ],
        "age_verifications": [
            {"status": status, "count": count}
            for status, count in age_stats
        ],
        "audit_events": [
            {"event_type": event_type, "impact": impact, "count": count}
            for event_type, impact, count in audit_stats
        ],
        "compliance_score": 96.8,  # Mock score
        "recommendations": [
            "Continue monitoring parental consent completion rates",
            "Review international jurisdiction requirements quarterly",
            "Update privacy policy for emerging regulations"
        ],
        "generated_at": datetime.now()
    }