"""
ActiveLog Education AI Suite - Certificate and Credential Management

Advanced blockchain-backed digital certificate system with verifiable credentials,
skill badging, achievement tracking, and professional certification pathways.
"""

import asyncio
import json
import uuid
import hashlib
import base64
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import sqlite3
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont
import io
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import jwt

class CredentialType(Enum):
    COURSE_COMPLETION = "course_completion"
    SKILL_BADGE = "skill_badge"
    ACHIEVEMENT = "achievement"
    CERTIFICATION = "certification"
    MICRO_CREDENTIAL = "micro_credential"
    COMPETENCY_BADGE = "competency_badge"
    PARTICIPATION = "participation"
    EXCELLENCE_AWARD = "excellence_award"

class CredentialLevel(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"  
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"

class VerificationStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REVOKED = "revoked"
    EXPIRED = "expired"

class IssuingAuthority(Enum):
    ACTIVELOG_AI = "activelog_ai"
    EDUCATIONAL_INSTITUTION = "educational_institution"
    PROFESSIONAL_BODY = "professional_body"
    INDUSTRY_PARTNER = "industry_partner"
    PEER_VERIFIED = "peer_verified"

@dataclass
class SkillEvidence:
    evidence_id: str
    evidence_type: str  # assignment, project, test, portfolio
    title: str
    description: str
    artifacts: List[str]  # URLs or file paths
    assessment_score: Optional[float]
    peer_reviews: List[Dict[str, Any]] = field(default_factory=list)
    mentor_feedback: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class DigitalCredential:
    credential_id: str
    credential_type: CredentialType
    title: str
    description: str
    recipient_id: str
    recipient_name: str
    recipient_email: str
    issuer_id: str
    issuer_name: str
    issuing_authority: IssuingAuthority
    skill_areas: List[str]
    competency_level: CredentialLevel
    learning_outcomes: List[str]
    evidence: List[SkillEvidence]
    issue_date: datetime
    expiry_date: Optional[datetime]
    verification_status: VerificationStatus
    verification_url: str
    blockchain_hash: Optional[str] = None
    digital_signature: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CertificateTemplate:
    template_id: str
    name: str
    credential_type: CredentialType
    design_layout: str
    color_scheme: Dict[str, str]
    fonts: Dict[str, str]
    logo_url: str
    signature_fields: List[Dict[str, str]]
    custom_fields: List[str]
    background_image: Optional[str] = None

@dataclass
class DigitalBadge:
    badge_id: str
    name: str
    description: str
    image_url: str
    criteria: Dict[str, Any]
    skill_tags: List[str]
    difficulty_level: CredentialLevel
    estimated_hours: int
    prerequisites: List[str] = field(default_factory=list)
    stackable_with: List[str] = field(default_factory=list)  # Other badges that combine
    industry_recognition: List[str] = field(default_factory=list)

@dataclass
class LearnerPortfolio:
    portfolio_id: str
    learner_id: str
    learner_name: str
    credentials: List[DigitalCredential]
    badges: List[DigitalBadge]
    skill_progression: Dict[str, Any]
    achievement_timeline: List[Dict[str, Any]]
    public_profile_url: str
    privacy_settings: Dict[str, bool]
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

@dataclass
class VerificationRequest:
    request_id: str
    credential_id: str
    verifier_id: str
    verifier_organization: str
    requested_at: datetime
    verification_purpose: str
    status: str = "pending"
    verified_at: Optional[datetime] = None
    verification_result: Optional[Dict[str, Any]] = None

class CertificateManager:
    """Advanced certificate and credential management system"""
    
    def __init__(self, database_path: str = "/home/activeloguser/activelog/data/credentials.db"):
        self.db_path = database_path
        self.credentials: Dict[str, DigitalCredential] = {}
        self.templates: Dict[str, CertificateTemplate] = {}
        self.badges: Dict[str, DigitalBadge] = {}
        self.portfolios: Dict[str, LearnerPortfolio] = {}
        self.verification_requests: Dict[str, VerificationRequest] = {}
        
        # Cryptographic keys for signing
        self.private_key = None
        self.public_key = None
        
        # Initialize system
        asyncio.create_task(self.initialize())
    
    async def initialize(self):
        """Initialize the certificate management system"""
        await self.setup_database()
        await self.setup_cryptographic_keys()
        await self.load_certificate_templates()
        await self.load_skill_badges()
        print("Certificate Manager initialized")
    
    async def setup_database(self):
        """Setup SQLite database for credential data"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Digital credentials table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digital_credentials (
                credential_id TEXT PRIMARY KEY,
                credential_data JSON NOT NULL,
                recipient_id TEXT NOT NULL,
                issuer_id TEXT NOT NULL,
                issue_date TIMESTAMP NOT NULL,
                expiry_date TIMESTAMP,
                verification_status TEXT NOT NULL,
                blockchain_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Certificate templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS certificate_templates (
                template_id TEXT PRIMARY KEY,
                template_data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Digital badges table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS digital_badges (
                badge_id TEXT PRIMARY KEY,
                badge_data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Learner portfolios table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS learner_portfolios (
                portfolio_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL UNIQUE,
                portfolio_data JSON NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verification requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_requests (
                request_id TEXT PRIMARY KEY,
                credential_id TEXT NOT NULL,
                verifier_id TEXT NOT NULL,
                request_data JSON NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credential_id) REFERENCES digital_credentials (credential_id)
            )
        ''')
        
        # Skill evidence table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_evidence (
                evidence_id TEXT PRIMARY KEY,
                credential_id TEXT NOT NULL,
                evidence_data JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (credential_id) REFERENCES digital_credentials (credential_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    async def setup_cryptographic_keys(self):
        """Setup cryptographic keys for certificate signing"""
        key_path = Path("/home/activeloguser/activelog/data/credential_keys")
        key_path.mkdir(parents=True, exist_ok=True)
        
        private_key_path = key_path / "private_key.pem"
        public_key_path = key_path / "public_key.pem"
        
        if private_key_path.exists() and public_key_path.exists():
            # Load existing keys
            with open(private_key_path, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )
            
            with open(public_key_path, 'rb') as f:
                self.public_key = serialization.load_pem_public_key(f.read())
        else:
            # Generate new keys
            self.private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            self.public_key = self.private_key.public_key()
            
            # Save keys
            with open(private_key_path, 'wb') as f:
                f.write(self.private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            with open(public_key_path, 'wb') as f:
                f.write(self.public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            # Restrict permissions
            private_key_path.chmod(0o600)
    
    async def load_certificate_templates(self):
        """Load predefined certificate templates"""
        # Course completion certificate template
        course_completion_template = CertificateTemplate(
            template_id="course_completion_standard",
            name="Standard Course Completion Certificate",
            credential_type=CredentialType.COURSE_COMPLETION,
            design_layout="formal",
            color_scheme={
                "primary": "#1f4788",
                "secondary": "#f4f4f4", 
                "accent": "#d4af37",
                "text": "#2c3e50"
            },
            fonts={
                "title": "Georgia",
                "body": "Arial",
                "signature": "Brush Script MT"
            },
            logo_url="/assets/logos/activelog_education.png",
            signature_fields=[
                {"name": "instructor", "title": "Lead Instructor"},
                {"name": "director", "title": "Education Director"}
            ],
            custom_fields=["course_duration", "grade_achieved", "skills_mastered"]
        )
        
        # Skill badge template
        skill_badge_template = CertificateTemplate(
            template_id="skill_badge_modern",
            name="Modern Skill Badge",
            credential_type=CredentialType.SKILL_BADGE,
            design_layout="badge",
            color_scheme={
                "primary": "#e74c3c",
                "secondary": "#ecf0f1",
                "accent": "#f39c12",
                "text": "#2c3e50"
            },
            fonts={
                "title": "Montserrat",
                "body": "Open Sans",
                "signature": "Dancing Script"
            },
            logo_url="/assets/logos/skill_badge.png",
            signature_fields=[
                {"name": "assessor", "title": "Skill Assessor"}
            ],
            custom_fields=["competency_level", "assessment_date", "valid_until"]
        )
        
        # Professional certification template
        certification_template = CertificateTemplate(
            template_id="professional_certification",
            name="Professional Certification",
            credential_type=CredentialType.CERTIFICATION,
            design_layout="formal_certification",
            color_scheme={
                "primary": "#27ae60",
                "secondary": "#ffffff",
                "accent": "#f1c40f",
                "text": "#2c3e50"
            },
            fonts={
                "title": "Times New Roman",
                "body": "Calibri",
                "signature": "Lucida Handwriting"
            },
            logo_url="/assets/logos/professional_cert.png",
            signature_fields=[
                {"name": "board_chair", "title": "Board Chairperson"},
                {"name": "certifying_body", "title": "Certifying Authority"}
            ],
            custom_fields=["certification_number", "renewal_date", "cpe_requirements"]
        )
        
        self.templates = {
            course_completion_template.template_id: course_completion_template,
            skill_badge_template.template_id: skill_badge_template,
            certification_template.template_id: certification_template
        }
    
    async def load_skill_badges(self):
        """Load predefined skill badges"""
        # Programming badges
        python_badge = DigitalBadge(
            badge_id="python_programming_basic",
            name="Python Programming Foundation",
            description="Demonstrates proficiency in Python programming fundamentals",
            image_url="/assets/badges/python_basic.png",
            criteria={
                "requirements": [
                    "Complete 10+ Python exercises",
                    "Build 2+ Python projects",
                    "Pass Python fundamentals assessment (80%+)"
                ],
                "assessment_type": "practical_coding",
                "minimum_score": 0.8
            },
            skill_tags=["python", "programming", "software_development", "coding"],
            difficulty_level=CredentialLevel.BEGINNER,
            estimated_hours=40,
            stackable_with=["web_development_badge", "data_analysis_badge"]
        )
        
        # Data analysis badge
        data_analysis_badge = DigitalBadge(
            badge_id="data_analysis_intermediate",
            name="Data Analysis Specialist",
            description="Skilled in data analysis, visualization, and statistical interpretation",
            image_url="/assets/badges/data_analysis.png",
            criteria={
                "requirements": [
                    "Analyze 5+ real datasets",
                    "Create compelling data visualizations",
                    "Present data-driven insights",
                    "Master statistical concepts"
                ],
                "assessment_type": "portfolio_review",
                "minimum_score": 0.85
            },
            skill_tags=["data_analysis", "statistics", "visualization", "python", "excel"],
            difficulty_level=CredentialLevel.INTERMEDIATE,
            estimated_hours=60,
            prerequisites=["python_programming_basic"],
            industry_recognition=["tech_companies", "consulting_firms", "research_organizations"]
        )
        
        # Mathematics mastery badge
        math_mastery_badge = DigitalBadge(
            badge_id="mathematics_advanced",
            name="Advanced Mathematics Mastery",
            description="Deep understanding of advanced mathematical concepts and applications",
            image_url="/assets/badges/mathematics.png",
            criteria={
                "requirements": [
                    "Master calculus concepts",
                    "Solve complex mathematical problems",
                    "Apply mathematics to real-world scenarios",
                    "Demonstrate mathematical reasoning"
                ],
                "assessment_type": "comprehensive_exam",
                "minimum_score": 0.90
            },
            skill_tags=["mathematics", "calculus", "algebra", "problem_solving"],
            difficulty_level=CredentialLevel.ADVANCED,
            estimated_hours=120,
            industry_recognition=["engineering_firms", "financial_institutions", "research_centers"]
        )
        
        self.badges = {
            python_badge.badge_id: python_badge,
            data_analysis_badge.badge_id: data_analysis_badge,
            math_mastery_badge.badge_id: math_mastery_badge
        }
    
    async def issue_credential(self, recipient_id: str, recipient_name: str, recipient_email: str,
                              credential_type: CredentialType, title: str, description: str,
                              skill_areas: List[str], competency_level: CredentialLevel,
                              learning_outcomes: List[str], evidence: List[SkillEvidence],
                              issuer_id: str, issuer_name: str,
                              expiry_date: Optional[datetime] = None) -> DigitalCredential:
        """Issue a new digital credential"""
        
        credential_id = str(uuid.uuid4())
        issue_date = datetime.now()
        
        # Generate verification URL
        verification_url = f"https://credentials.activelog.ai/verify/{credential_id}"
        
        # Create credential
        credential = DigitalCredential(
            credential_id=credential_id,
            credential_type=credential_type,
            title=title,
            description=description,
            recipient_id=recipient_id,
            recipient_name=recipient_name,
            recipient_email=recipient_email,
            issuer_id=issuer_id,
            issuer_name=issuer_name,
            issuing_authority=IssuingAuthority.ACTIVELOG_AI,
            skill_areas=skill_areas,
            competency_level=competency_level,
            learning_outcomes=learning_outcomes,
            evidence=evidence,
            issue_date=issue_date,
            expiry_date=expiry_date,
            verification_status=VerificationStatus.VERIFIED,
            verification_url=verification_url
        )
        
        # Generate digital signature
        credential_data = json.dumps(asdict(credential), default=str, sort_keys=True)
        signature = self.sign_credential(credential_data)
        credential.digital_signature = signature
        
        # Generate blockchain hash (simulate)
        blockchain_hash = self.generate_blockchain_hash(credential)
        credential.blockchain_hash = blockchain_hash
        
        # Store credential
        self.credentials[credential_id] = credential
        await self.save_credential_to_database(credential)
        
        # Update learner portfolio
        await self.update_learner_portfolio(recipient_id, credential)
        
        # Generate certificate image
        certificate_image = await self.generate_certificate_image(credential)
        
        return credential
    
    def sign_credential(self, credential_data: str) -> str:
        """Digitally sign credential data"""
        signature = self.private_key.sign(
            credential_data.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        return base64.b64encode(signature).decode('utf-8')
    
    def verify_credential_signature(self, credential_data: str, signature: str) -> bool:
        """Verify credential digital signature"""
        try:
            signature_bytes = base64.b64decode(signature.encode('utf-8'))
            self.public_key.verify(
                signature_bytes,
                credential_data.encode('utf-8'),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False
    
    def generate_blockchain_hash(self, credential: DigitalCredential) -> str:
        """Generate blockchain hash for credential immutability"""
        # Simulate blockchain hash generation
        credential_string = f"{credential.credential_id}{credential.recipient_id}{credential.issue_date}"
        hash_object = hashlib.sha256(credential_string.encode())
        return hash_object.hexdigest()
    
    async def generate_certificate_image(self, credential: DigitalCredential) -> str:
        """Generate visual certificate image"""
        # Create certificate image
        width, height = 1200, 900
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # Load fonts (would use actual font files in production)
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Georgia.ttf", 48)
            body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
            small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 16)
        except:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # Draw certificate border
        border_color = "#1f4788"
        draw.rectangle([(50, 50), (width-50, height-50)], outline=border_color, width=5)
        draw.rectangle([(70, 70), (width-70, height-70)], outline=border_color, width=2)
        
        # Certificate title
        title_text = "CERTIFICATE OF COMPLETION"
        title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 150), title_text, fill=border_color, font=title_font)
        
        # Recipient name
        name_text = f"Awarded to: {credential.recipient_name}"
        name_bbox = draw.textbbox((0, 0), name_text, font=body_font)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((width - name_width) // 2, 250), name_text, fill="#2c3e50", font=body_font)
        
        # Course/skill title
        course_text = credential.title
        course_bbox = draw.textbbox((0, 0), course_text, font=body_font)
        course_width = course_bbox[2] - course_bbox[0]
        draw.text(((width - course_width) // 2, 320), course_text, fill="#2c3e50", font=body_font)
        
        # Skills mastered
        if credential.skill_areas:
            skills_text = f"Skills: {', '.join(credential.skill_areas)}"
            skills_bbox = draw.textbbox((0, 0), skills_text, font=small_font)
            skills_width = skills_bbox[2] - skills_bbox[0]
            draw.text(((width - skills_width) // 2, 380), skills_text, fill="#666666", font=small_font)
        
        # Issue date
        date_text = f"Issued on: {credential.issue_date.strftime('%B %d, %Y')}"
        date_bbox = draw.textbbox((0, 0), date_text, font=small_font)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(((width - date_width) // 2, 450), date_text, fill="#666666", font=small_font)
        
        # QR code for verification
        qr_data = credential.verification_url
        qr = qrcode.QRCode(version=1, box_size=3, border=1)
        qr.add_data(qr_data)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Paste QR code
        img.paste(qr_img, (width - 200, height - 200))
        
        # Add verification text
        verify_text = "Scan to verify"
        draw.text((width - 180, height - 70), verify_text, fill="#666666", font=small_font)
        
        # Save image
        cert_dir = Path("/home/activeloguser/activelog/data/certificates")
        cert_dir.mkdir(parents=True, exist_ok=True)
        cert_path = cert_dir / f"{credential.credential_id}.png"
        img.save(cert_path)
        
        return str(cert_path)
    
    async def award_badge(self, learner_id: str, badge_id: str, 
                         evidence: List[SkillEvidence]) -> DigitalCredential:
        """Award a skill badge to a learner"""
        if badge_id not in self.badges:
            raise ValueError(f"Badge {badge_id} not found")
        
        badge = self.badges[badge_id]
        
        # Create credential for badge
        credential = await self.issue_credential(
            recipient_id=learner_id,
            recipient_name="Learner",  # Would get from user profile
            recipient_email="learner@example.com",  # Would get from user profile
            credential_type=CredentialType.SKILL_BADGE,
            title=badge.name,
            description=badge.description,
            skill_areas=badge.skill_tags,
            competency_level=badge.difficulty_level,
            learning_outcomes=[f"Mastered {badge.name} requirements"],
            evidence=evidence,
            issuer_id="activelog_ai",
            issuer_name="ActiveLog AI Education"
        )
        
        return credential
    
    async def create_learner_portfolio(self, learner_id: str, learner_name: str) -> LearnerPortfolio:
        """Create a new learner portfolio"""
        portfolio_id = str(uuid.uuid4())
        public_profile_url = f"https://portfolios.activelog.ai/{learner_id}"
        
        portfolio = LearnerPortfolio(
            portfolio_id=portfolio_id,
            learner_id=learner_id,
            learner_name=learner_name,
            credentials=[],
            badges=[],
            skill_progression={},
            achievement_timeline=[],
            public_profile_url=public_profile_url,
            privacy_settings={
                "public_profile": True,
                "show_credentials": True,
                "show_progress": True,
                "contact_info": False
            }
        )
        
        self.portfolios[learner_id] = portfolio
        await self.save_portfolio_to_database(portfolio)
        
        return portfolio
    
    async def update_learner_portfolio(self, learner_id: str, credential: DigitalCredential):
        """Update learner portfolio with new credential"""
        if learner_id not in self.portfolios:
            await self.create_learner_portfolio(learner_id, credential.recipient_name)
        
        portfolio = self.portfolios[learner_id]
        portfolio.credentials.append(credential)
        
        # Update skill progression
        for skill_area in credential.skill_areas:
            if skill_area not in portfolio.skill_progression:
                portfolio.skill_progression[skill_area] = {
                    "level": credential.competency_level.value,
                    "credentials_earned": 1,
                    "last_updated": datetime.now().isoformat()
                }
            else:
                portfolio.skill_progression[skill_area]["credentials_earned"] += 1
                portfolio.skill_progression[skill_area]["last_updated"] = datetime.now().isoformat()
        
        # Add to achievement timeline
        portfolio.achievement_timeline.append({
            "date": credential.issue_date.isoformat(),
            "type": credential.credential_type.value,
            "title": credential.title,
            "description": f"Earned {credential.credential_type.value}: {credential.title}"
        })
        
        portfolio.last_updated = datetime.now()
        await self.save_portfolio_to_database(portfolio)
    
    async def verify_credential(self, credential_id: str) -> Dict[str, Any]:
        """Verify the authenticity of a credential"""
        if credential_id not in self.credentials:
            return {"valid": False, "error": "Credential not found"}
        
        credential = self.credentials[credential_id]
        
        # Check expiry
        if credential.expiry_date and datetime.now() > credential.expiry_date:
            return {"valid": False, "error": "Credential has expired"}
        
        # Check revocation status
        if credential.verification_status == VerificationStatus.REVOKED:
            return {"valid": False, "error": "Credential has been revoked"}
        
        # Verify digital signature
        credential_data = json.dumps(asdict(credential), default=str, sort_keys=True)
        signature_valid = self.verify_credential_signature(credential_data, credential.digital_signature)
        
        if not signature_valid:
            return {"valid": False, "error": "Invalid digital signature"}
        
        # Return verification result
        return {
            "valid": True,
            "credential": {
                "id": credential.credential_id,
                "type": credential.credential_type.value,
                "title": credential.title,
                "recipient": credential.recipient_name,
                "issuer": credential.issuer_name,
                "issue_date": credential.issue_date.isoformat(),
                "expiry_date": credential.expiry_date.isoformat() if credential.expiry_date else None,
                "skill_areas": credential.skill_areas,
                "competency_level": credential.competency_level.value,
                "blockchain_hash": credential.blockchain_hash
            }
        }
    
    async def request_verification(self, credential_id: str, verifier_id: str, 
                                 verifier_organization: str, purpose: str) -> VerificationRequest:
        """Request credential verification from third party"""
        request_id = str(uuid.uuid4())
        
        verification_request = VerificationRequest(
            request_id=request_id,
            credential_id=credential_id,
            verifier_id=verifier_id,
            verifier_organization=verifier_organization,
            requested_at=datetime.now(),
            verification_purpose=purpose
        )
        
        self.verification_requests[request_id] = verification_request
        await self.save_verification_request_to_database(verification_request)
        
        return verification_request
    
    async def get_learner_portfolio(self, learner_id: str) -> Optional[LearnerPortfolio]:
        """Get learner's credential portfolio"""
        return self.portfolios.get(learner_id)
    
    async def get_skill_pathway_recommendations(self, learner_id: str) -> Dict[str, Any]:
        """Get recommended skill pathways for learner"""
        portfolio = self.portfolios.get(learner_id)
        if not portfolio:
            return {"error": "Portfolio not found"}
        
        # Analyze current skills
        current_skills = set()
        for credential in portfolio.credentials:
            current_skills.update(credential.skill_areas)
        
        # Find stackable badges
        recommended_badges = []
        for badge in self.badges.values():
            # Check if prerequisites are met
            prerequisites_met = all(
                any(skill in current_skills for skill in badge.prerequisites) or not badge.prerequisites
                for _ in [True]  # Simplified check
            )
            
            # Check if badge would stack with current skills
            if prerequisites_met and badge.badge_id not in [c.title for c in portfolio.credentials]:
                recommended_badges.append({
                    "badge_id": badge.badge_id,
                    "name": badge.name,
                    "description": badge.description,
                    "estimated_hours": badge.estimated_hours,
                    "difficulty_level": badge.difficulty_level.value,
                    "skill_tags": badge.skill_tags,
                    "industry_recognition": badge.industry_recognition
                })
        
        return {
            "current_skills": list(current_skills),
            "recommended_badges": recommended_badges[:5],  # Top 5 recommendations
            "skill_gaps": await self.identify_skill_gaps(current_skills),
            "career_pathways": await self.suggest_career_pathways(current_skills)
        }
    
    async def identify_skill_gaps(self, current_skills: set) -> List[str]:
        """Identify skill gaps for career advancement"""
        # Common skill combinations for different career paths
        career_skill_sets = {
            "data_scientist": {"python", "statistics", "machine_learning", "data_visualization", "sql"},
            "web_developer": {"html", "css", "javascript", "react", "node_js", "databases"},
            "software_engineer": {"programming", "algorithms", "system_design", "testing", "version_control"},
            "digital_marketer": {"analytics", "content_creation", "seo", "social_media", "email_marketing"}
        }
        
        skill_gaps = []
        for career, required_skills in career_skill_sets.items():
            missing_skills = required_skills - current_skills
            if len(missing_skills) <= 3:  # Close to completing this career path
                skill_gaps.extend(list(missing_skills))
        
        return list(set(skill_gaps))
    
    async def suggest_career_pathways(self, current_skills: set) -> List[Dict[str, Any]]:
        """Suggest career pathways based on current skills"""
        pathways = [
            {
                "career": "Data Analyst",
                "match_percentage": len(current_skills.intersection({"python", "statistics", "data_analysis"})) / 3 * 100,
                "next_steps": ["Advanced Statistics Badge", "Data Visualization Certificate"],
                "estimated_time": "3-6 months"
            },
            {
                "career": "Software Developer",
                "match_percentage": len(current_skills.intersection({"programming", "python", "javascript"})) / 3 * 100,
                "next_steps": ["Web Development Certificate", "Algorithm Design Badge"],
                "estimated_time": "6-12 months"
            }
        ]
        
        # Sort by match percentage
        pathways.sort(key=lambda x: x["match_percentage"], reverse=True)
        return pathways[:3]  # Top 3 pathways
    
    async def generate_credential_report(self, issuer_id: str) -> Dict[str, Any]:
        """Generate credential issuance report for an issuer"""
        issued_credentials = [c for c in self.credentials.values() if c.issuer_id == issuer_id]
        
        if not issued_credentials:
            return {"message": "No credentials found for this issuer"}
        
        # Calculate statistics
        total_issued = len(issued_credentials)
        by_type = {}
        by_level = {}
        by_month = {}
        
        for credential in issued_credentials:
            # By type
            cred_type = credential.credential_type.value
            by_type[cred_type] = by_type.get(cred_type, 0) + 1
            
            # By level
            level = credential.competency_level.value
            by_level[level] = by_level.get(level, 0) + 1
            
            # By month
            month_key = credential.issue_date.strftime("%Y-%m")
            by_month[month_key] = by_month.get(month_key, 0) + 1
        
        return {
            "issuer_id": issuer_id,
            "total_credentials_issued": total_issued,
            "credentials_by_type": by_type,
            "credentials_by_level": by_level,
            "issuance_by_month": by_month,
            "verification_requests": len([vr for vr in self.verification_requests.values() 
                                        if vr.credential_id in [c.credential_id for c in issued_credentials]]),
            "average_skill_areas_per_credential": sum(len(c.skill_areas) for c in issued_credentials) / total_issued
        }
    
    # Database operations
    async def save_credential_to_database(self, credential: DigitalCredential):
        """Save credential to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO digital_credentials 
            (credential_id, credential_data, recipient_id, issuer_id, issue_date, 
             expiry_date, verification_status, blockchain_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            credential.credential_id,
            json.dumps(asdict(credential), default=str),
            credential.recipient_id,
            credential.issuer_id,
            credential.issue_date.isoformat(),
            credential.expiry_date.isoformat() if credential.expiry_date else None,
            credential.verification_status.value,
            credential.blockchain_hash
        ))
        
        conn.commit()
        conn.close()
    
    async def save_portfolio_to_database(self, portfolio: LearnerPortfolio):
        """Save learner portfolio to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO learner_portfolios 
            (portfolio_id, learner_id, portfolio_data, last_updated)
            VALUES (?, ?, ?, ?)
        ''', (
            portfolio.portfolio_id,
            portfolio.learner_id,
            json.dumps(asdict(portfolio), default=str),
            portfolio.last_updated.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    async def save_verification_request_to_database(self, request: VerificationRequest):
        """Save verification request to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO verification_requests 
            (request_id, credential_id, verifier_id, request_data, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            request.request_id,
            request.credential_id,
            request.verifier_id,
            json.dumps(asdict(request), default=str),
            request.status
        ))
        
        conn.commit()
        conn.close()

# Example usage
async def main():
    manager = CertificateManager()
    
    # Create skill evidence
    evidence = [
        SkillEvidence(
            evidence_id=str(uuid.uuid4()),
            evidence_type="project",
            title="Python Data Analysis Project",
            description="Analyzed sales data using pandas and matplotlib",
            artifacts=["project_report.pdf", "code_repository_url"],
            assessment_score=0.92
        )
    ]
    
    # Issue a credential
    credential = await manager.issue_credential(
        recipient_id="learner_123",
        recipient_name="John Student",
        recipient_email="john@example.com",
        credential_type=CredentialType.COURSE_COMPLETION,
        title="Python Programming Fundamentals",
        description="Comprehensive Python programming course completion",
        skill_areas=["python", "programming", "data_analysis"],
        competency_level=CredentialLevel.INTERMEDIATE,
        learning_outcomes=["Python syntax mastery", "Data manipulation skills", "Problem-solving abilities"],
        evidence=evidence,
        issuer_id="activelog_ai",
        issuer_name="ActiveLog AI Education"
    )
    
    print(f"Issued credential: {credential.credential_id}")
    
    # Verify credential
    verification = await manager.verify_credential(credential.credential_id)
    print(f"Verification result: {verification}")
    
    # Award a badge
    badge_credential = await manager.award_badge("learner_123", "python_programming_basic", evidence)
    print(f"Awarded badge: {badge_credential.title}")
    
    # Get learner portfolio
    portfolio = await manager.get_learner_portfolio("learner_123")
    if portfolio:
        print(f"Portfolio has {len(portfolio.credentials)} credentials")
    
    # Get skill pathway recommendations
    recommendations = await manager.get_skill_pathway_recommendations("learner_123")
    print(f"Recommendations: {recommendations}")

if __name__ == "__main__":
    asyncio.run(main())