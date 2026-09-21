#!/usr/bin/env python3
"""
Terms of Service Generator for ActiveLog Applications
Generates comprehensive, legally compliant terms of service for each app vertical
"""

import os
import json
import yaml
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

class AppType(Enum):
    PRODUCTIVITY = "productivity"
    AI_TOOLS = "ai_tools"
    FINANCIAL = "financial"

class LiabilityLevel(Enum):
    STANDARD = "standard"
    ENHANCED = "enhanced"
    FINANCIAL = "financial"

@dataclass
class ServiceFeature:
    name: str
    description: str
    limitations: List[str]
    user_obligations: List[str]
    restrictions: List[str]

@dataclass
class AppTermsConfig:
    name: str
    app_type: AppType
    bundle_id: str
    service_features: List[ServiceFeature]
    liability_level: LiabilityLevel
    age_requirement: int
    subscription_model: bool
    financial_services: bool
    ai_services: bool
    content_creation: bool
    data_processing: bool
    third_party_integrations: List[str]

class TermsOfServiceGenerator:
    """Generates comprehensive terms of service for ActiveLog applications"""
    
    def __init__(self):
        self.company_name = "ActiveLog Technologies"
        self.company_address = "123 Innovation Drive, San Francisco, CA 94105"
        self.contact_email = "legal@activelog.com"
        self.effective_date = datetime.now().strftime("%B %d, %Y")
        self.output_dir = "/home/activeloguser/activelog/deployment/stores/legal/terms"
        
        # Load app configurations
        self.apps = self._load_app_configurations()
    
    def _load_app_configurations(self) -> Dict[str, AppTermsConfig]:
        """Load app-specific terms configurations"""
        return {
            "activelog": AppTermsConfig(
                name="ActiveLog",
                app_type=AppType.PRODUCTIVITY,
                bundle_id="com.activelog.app",
                service_features=[
                    ServiceFeature(
                        name="Activity Logging",
                        description="Track and record daily activities, time, and productivity metrics",
                        limitations=["Storage limits based on subscription tier", "Export limitations for free users"],
                        user_obligations=["Provide accurate information", "Use for lawful purposes only"],
                        restrictions=["No sharing of inappropriate content", "No automated spam or bulk operations"]
                    ),
                    ServiceFeature(
                        name="Team Collaboration",
                        description="Share logs and collaborate with team members",
                        limitations=["Member limits based on plan", "Admin controls may restrict access"],
                        user_obligations=["Respect team privacy settings", "Follow organization policies"],
                        restrictions=["No unauthorized access to team data", "No malicious team activities"]
                    ),
                    ServiceFeature(
                        name="Data Sync",
                        description="Synchronize data across multiple devices",
                        limitations=["Sync frequency limits", "Device number restrictions"],
                        user_obligations=["Secure your devices", "Report security issues"],
                        restrictions=["No sharing credentials", "No circumventing sync limits"]
                    )
                ],
                liability_level=LiabilityLevel.STANDARD,
                age_requirement=13,
                subscription_model=True,
                financial_services=False,
                ai_services=False,
                content_creation=True,
                data_processing=True,
                third_party_integrations=["Google Calendar", "Slack", "Microsoft Teams", "Zapier"]
            ),
            
            "activelog-ai": AppTermsConfig(
                name="ActiveLog AI",
                app_type=AppType.AI_TOOLS,
                bundle_id="com.activelog.ai",
                service_features=[
                    ServiceFeature(
                        name="AI Content Generation",
                        description="Generate text, images, and other content using artificial intelligence",
                        limitations=["Usage quotas based on subscription", "Content moderation filters", "Model availability"],
                        user_obligations=["Use responsibly and ethically", "Respect intellectual property", "Follow content policies"],
                        restrictions=["No illegal content generation", "No impersonation or fraud", "No copyright infringement"]
                    ),
                    ServiceFeature(
                        name="Model Training",
                        description="Train custom AI models using your data",
                        limitations=["Compute resource limits", "Training time restrictions", "Model size limits"],
                        user_obligations=["Own rights to training data", "Comply with AI ethics", "Secure model access"],
                        restrictions=["No biased or harmful models", "No privacy-violating models", "No malicious use cases"]
                    ),
                    ServiceFeature(
                        name="API Integration",
                        description="Access AI services programmatically through APIs",
                        limitations=["Rate limiting", "Usage quotas", "API versioning"],
                        user_obligations=["Secure API keys", "Monitor usage", "Follow best practices"],
                        restrictions=["No API abuse", "No reselling access", "No circumventing limits"]
                    )
                ],
                liability_level=LiabilityLevel.ENHANCED,
                age_requirement=16,
                subscription_model=True,
                financial_services=False,
                ai_services=True,
                content_creation=True,
                data_processing=True,
                third_party_integrations=["OpenAI", "Anthropic", "Stability AI", "Google Cloud AI", "AWS Bedrock"]
            ),
            
            "activeledger": AppTermsConfig(
                name="ActiveLedger",
                app_type=AppType.FINANCIAL,
                bundle_id="com.activelog.ledger",
                service_features=[
                    ServiceFeature(
                        name="Payment Processing",
                        description="Process payments, transfers, and currency exchanges",
                        limitations=["Transaction limits", "Geographic restrictions", "Regulatory compliance requirements"],
                        user_obligations=["Provide accurate financial information", "Comply with AML/KYC", "Report suspicious activity"],
                        restrictions=["No money laundering", "No terrorist financing", "No sanctions violations"]
                    ),
                    ServiceFeature(
                        name="Multi-Currency Exchange",
                        description="Convert between multiple currencies with real-time rates",
                        limitations=["Exchange rate spreads", "Daily/monthly limits", "Supported currency pairs"],
                        user_obligations=["Understand exchange risks", "Verify transaction details", "Comply with tax obligations"],
                        restrictions=["No currency manipulation", "No illegal trading", "No market abuse"]
                    ),
                    ServiceFeature(
                        name="Subscription Billing",
                        description="Automated recurring billing and subscription management",
                        limitations=["Billing cycle restrictions", "Payment method requirements", "Cancellation policies"],
                        user_obligations=["Maintain valid payment methods", "Monitor billing statements", "Update account information"],
                        restrictions=["No fraudulent billing", "No unauthorized subscriptions", "No chargeback abuse"]
                    ),
                    ServiceFeature(
                        name="Financial Analytics",
                        description="Advanced analytics and reporting for financial data",
                        limitations=["Data retention periods", "Report generation limits", "Historical data availability"],
                        user_obligations=["Verify data accuracy", "Secure access to reports", "Comply with financial regulations"],
                        restrictions=["No data manipulation", "No unauthorized access", "No regulatory violations"]
                    )
                ],
                liability_level=LiabilityLevel.FINANCIAL,
                age_requirement=18,
                subscription_model=True,
                financial_services=True,
                ai_services=False,
                content_creation=False,
                data_processing=True,
                third_party_integrations=["Stripe", "PayPal", "Plaid", "Jumio", "Chainalysis", "Banking APIs"]
            )
        }
    
    def generate_all_terms(self):
        """Generate terms of service for all applications"""
        for app_id, config in self.apps.items():
            terms_content = self._generate_terms(config)
            self._save_terms(app_id, terms_content)
            print(f"Generated terms of service for {config.name}")
        
        # Generate master terms of service
        master_terms = self._generate_master_terms()
        self._save_terms("master", master_terms)
        print("Generated master terms of service")
    
    def _generate_terms(self, config: AppTermsConfig) -> str:
        """Generate terms of service for a specific app"""
        sections = [
            self._generate_header(config),
            self._generate_acceptance_section(config),
            self._generate_service_description_section(config),
            self._generate_user_accounts_section(config),
            self._generate_user_conduct_section(config),
            self._generate_service_features_section(config),
            self._generate_subscription_section(config) if config.subscription_model else "",
            self._generate_financial_section(config) if config.financial_services else "",
            self._generate_ai_section(config) if config.ai_services else "",
            self._generate_intellectual_property_section(config),
            self._generate_privacy_section(config),
            self._generate_third_party_section(config),
            self._generate_disclaimers_section(config),
            self._generate_limitation_of_liability_section(config),
            self._generate_indemnification_section(config),
            self._generate_termination_section(config),
            self._generate_dispute_resolution_section(config),
            self._generate_changes_section(config),
            self._generate_general_provisions_section(config),
            self._generate_contact_section(config)
        ]
        
        # Remove empty sections
        sections = [section for section in sections if section.strip()]
        
        return "\n\n".join(sections)
    
    def _generate_header(self, config: AppTermsConfig) -> str:
        """Generate terms header"""
        return f"""# Terms of Service for {config.name}

**Effective Date:** {self.effective_date}  
**Last Updated:** {self.effective_date}

Welcome to {config.name}! These Terms of Service ("Terms") govern your use of the {config.name} mobile application and related services (collectively, the "Service") operated by {self.company_name} ("we," "us," or "our").

**Bundle Identifier:** {config.bundle_id}

Please read these Terms carefully before using our Service. By accessing or using our Service, you agree to be bound by these Terms. If you disagree with any part of these Terms, then you may not access the Service.

**Age Requirement:** You must be at least {config.age_requirement} years old to use this Service."""
    
    def _generate_acceptance_section(self, config: AppTermsConfig) -> str:
        """Generate acceptance section"""
        return """## 1. Acceptance of Terms

By downloading, installing, accessing, or using our Service, you:
- Acknowledge that you have read and understood these Terms
- Agree to be bound by these Terms and our Privacy Policy
- Represent that you meet the age requirements
- Confirm you have the authority to enter into this agreement

If you are using the Service on behalf of an organization, you represent and warrant that you have the authority to bind that organization to these Terms."""
    
    def _generate_service_description_section(self, config: AppTermsConfig) -> str:
        """Generate service description section"""
        app_type_descriptions = {
            AppType.PRODUCTIVITY: f"{config.name} is a productivity application that helps users track activities, manage time, and collaborate with teams.",
            AppType.AI_TOOLS: f"{config.name} is an AI-powered platform that provides content generation, model training, and artificial intelligence services.",
            AppType.FINANCIAL: f"{config.name} is a financial services platform that provides payment processing, currency exchange, and financial management tools."
        }
        
        description = app_type_descriptions.get(config.app_type, f"{config.name} provides various digital services.")
        
        features_list = "\n".join([f"- {feature.name}: {feature.description}" for feature in config.service_features])
        
        return f"""## 2. Description of Service

{description}

### Key Features:
{features_list}

### Service Availability
- We strive to maintain 99.9% uptime but do not guarantee uninterrupted service
- Maintenance windows may temporarily affect availability
- Features may be added, modified, or removed at our discretion
- Service availability may vary by geographic location"""
    
    def _generate_user_accounts_section(self, config: AppTermsConfig) -> str:
        """Generate user accounts section"""
        sections = [
            "## 3. User Accounts",
            "",
            "### Account Creation",
            "- You must create an account to use certain features of our Service",
            "- You must provide accurate, current, and complete information",
            "- You are responsible for maintaining account security",
            "- You must notify us immediately of any unauthorized access"
        ]
        
        if config.financial_services:
            sections.extend([
                "",
                "### Enhanced Verification (Financial Services)",
                "- Identity verification is required for financial features",
                "- You must comply with Know Your Customer (KYC) requirements",
                "- Additional documentation may be requested",
                "- Account limits may apply until verification is complete"
            ])
        
        sections.extend([
            "",
            "### Account Responsibilities",
            "- One account per person (no multiple accounts)",
            "- Keep your login credentials secure and confidential",
            "- You are responsible for all activity under your account",
            "- Notify us immediately of any security breaches"
        ])
        
        return "\n".join(sections)
    
    def _generate_user_conduct_section(self, config: AppTermsConfig) -> str:
        """Generate user conduct section"""
        sections = [
            "## 4. User Conduct and Acceptable Use",
            "",
            "### Acceptable Use",
            "You agree to use our Service only for lawful purposes and in accordance with these Terms.",
            "",
            "### Prohibited Activities",
            "You may not:",
            "- Violate any applicable laws or regulations",
            "- Infringe upon the rights of others",
            "- Transmit harmful, offensive, or inappropriate content",
            "- Attempt to gain unauthorized access to our systems",
            "- Interfere with the proper functioning of the Service",
            "- Use automated systems to access the Service without permission",
            "- Reverse engineer or attempt to extract source code",
            "- Resell or redistribute the Service without authorization"
        ]
        
        if config.ai_services:
            sections.extend([
                "",
                "### AI-Specific Conduct",
                "When using AI features, you may not:",
                "- Generate illegal, harmful, or malicious content",
                "- Attempt to create biased or discriminatory models",
                "- Use AI outputs to impersonate others",
                "- Generate content that violates intellectual property rights",
                "- Create deepfakes or other deceptive content without disclosure"
            ])
        
        if config.financial_services:
            sections.extend([
                "",
                "### Financial Services Conduct",
                "For financial features, you must:",
                "- Comply with all applicable financial regulations",
                "- Provide accurate financial information",
                "- Report suspicious activities",
                "- Not engage in money laundering or terrorist financing",
                "- Comply with sanctions and export control laws"
            ])
        
        return "\n".join(sections)
    
    def _generate_service_features_section(self, config: AppTermsConfig) -> str:
        """Generate service features section"""
        sections = [
            "## 5. Service Features and Limitations",
            ""
        ]
        
        for feature in config.service_features:
            sections.extend([
                f"### {feature.name}",
                f"{feature.description}",
                "",
                "**Your Obligations:**"
            ])
            sections.extend([f"- {obligation}" for obligation in feature.user_obligations])
            
            sections.extend(["", "**Limitations:**"])
            sections.extend([f"- {limitation}" for limitation in feature.limitations])
            
            sections.extend(["", "**Restrictions:**"])
            sections.extend([f"- {restriction}" for restriction in feature.restrictions])
            sections.append("")
        
        return "\n".join(sections)
    
    def _generate_subscription_section(self, config: AppTermsConfig) -> str:
        """Generate subscription section"""
        return """## 6. Subscription and Payment Terms

### Subscription Plans
- We offer various subscription plans with different features and limits
- Current pricing is available in the app and on our website
- Prices may change with notice as described in these Terms

### Billing and Payment
- Subscriptions are billed in advance on a recurring basis
- Payment is due immediately upon subscription or renewal
- You authorize us to charge your payment method automatically
- Failed payments may result in service suspension

### Free Trials
- Free trials may be offered for new subscribers
- Trial periods automatically convert to paid subscriptions unless cancelled
- Cancellation during trial period avoids charges

### Cancellation and Refunds
- You may cancel your subscription at any time through account settings
- Cancellation stops future billing but doesn't refund current period
- No refunds for partial months or unused features
- Enterprise customers may have different refund terms

### Price Changes
- We may change subscription prices with 30 days' notice
- Existing subscribers receive notification before changes take effect
- You may cancel to avoid price increases"""
    
    def _generate_financial_section(self, config: AppTermsConfig) -> str:
        """Generate financial services section"""
        return """## 7. Financial Services Terms

### Regulatory Compliance
- Our financial services are subject to various regulations
- You must comply with all applicable financial laws
- We may be required to report certain transactions
- Services may be limited based on your jurisdiction

### Transaction Processing
- Transaction limits may apply based on verification level
- Processing times vary by transaction type and amount
- Fees are disclosed before transaction completion
- Some transactions may be delayed for security review

### Currency Exchange
- Exchange rates are provided by third-party sources
- Rates include our markup and may differ from market rates
- Large transactions may receive more favorable rates
- Historical rate data is for reference only

### Risk Disclosure
- Financial services involve inherent risks
- Currency values may fluctuate
- Past performance does not guarantee future results
- You are responsible for understanding risks before transacting

### Anti-Money Laundering (AML)
- We implement AML procedures as required by law
- Suspicious activities will be reported to authorities
- Your account may be frozen pending investigation
- We may request additional documentation for compliance

### Know Your Customer (KYC)
- Identity verification is required for financial services
- Additional documentation may be requested
- Verification status affects transaction limits
- False information may result in account termination"""
    
    def _generate_ai_section(self, config: AppTermsConfig) -> str:
        """Generate AI services section"""
        return """## 8. Artificial Intelligence Services Terms

### AI Service Provision
- We provide access to various AI models and services
- Model availability and capabilities may change
- Processing times vary based on complexity and demand
- Results are generated automatically and may require human review

### Content Generation
- AI-generated content is provided "as is" without warranties
- You are responsible for reviewing and validating outputs
- Generated content may not be accurate or appropriate
- We do not guarantee originality or non-infringement

### Data Usage for AI
- Your inputs may be used to improve AI services (with consent)
- We implement privacy protections for sensitive data
- Local processing options may be available
- Data retention periods vary by service type

### Model Training
- Custom model training requires appropriate data rights
- Training data must comply with our content policies
- Trained models remain subject to these Terms
- We may limit or terminate training services at our discretion

### Intellectual Property in AI Outputs
- You retain rights to your original inputs
- AI outputs may not be subject to copyright protection
- Generated content may inadvertently resemble existing works
- You are responsible for clearance of any third-party rights

### AI Ethics and Responsibility
- We strive to provide fair and unbiased AI services
- Report any concerning AI behavior or outputs
- Use AI services responsibly and ethically
- Consider the impact of AI-generated content on others"""
    
    def _generate_intellectual_property_section(self, config: AppTermsConfig) -> str:
        """Generate intellectual property section"""
        sections = [
            "## 9. Intellectual Property Rights",
            "",
            "### Our Rights",
            "- The Service and its original content, features, and functionality are owned by us",
            "- Our trademarks, service marks, and logos are our property",
            "- The Service is protected by copyright, trademark, and other intellectual property laws",
            "",
            "### Your Rights",
            "- You retain ownership of content you upload or create",
            "- You grant us a license to use your content to provide the Service",
            "- This license ends when you delete content or terminate your account"
        ]
        
        if config.ai_services:
            sections.extend([
                "",
                "### AI-Generated Content",
                "- You own inputs you provide to AI services",
                "- AI outputs may not be subject to copyright protection",
                "- You are responsible for determining IP status of outputs",
                "- We make no warranties regarding IP rights in AI outputs"
            ])
        
        sections.extend([
            "",
            "### License to Use Service",
            "- We grant you a limited, non-exclusive license to use the Service",
            "- This license is personal and non-transferable",
            "- You may not modify, distribute, or reverse engineer the Service",
            "",
            "### DMCA and Copyright Protection",
            "- We respect intellectual property rights",
            "- Report copyright infringement to our designated agent",
            "- We will respond to valid DMCA takedown notices",
            "- Repeat infringers may have their accounts terminated"
        ])
        
        return "\n".join(sections)
    
    def _generate_privacy_section(self, config: AppTermsConfig) -> str:
        """Generate privacy section"""
        return f"""## 10. Privacy and Data Protection

### Privacy Policy
- Our Privacy Policy describes how we collect, use, and protect your information
- The Privacy Policy is incorporated into these Terms by reference
- You consent to data processing as described in our Privacy Policy

### Data Security
- We implement appropriate security measures to protect your data
- You are responsible for maintaining the security of your account
- Report any suspected data breaches immediately

### Data Retention
- We retain your data as described in our Privacy Policy
- You may request data deletion subject to legal requirements
- Some data may be retained for legal compliance purposes

### Cross-Border Data Transfer
- Your data may be processed in countries other than your residence
- We implement appropriate safeguards for international transfers
- Data transfers comply with applicable privacy laws

For more information, please review our Privacy Policy at: https://activelog.com/{config.name.lower()}-privacy"""
    
    def _generate_third_party_section(self, config: AppTermsConfig) -> str:
        """Generate third-party section"""
        integrations_list = "\n".join([f"- {integration}" for integration in config.third_party_integrations])
        
        return f"""## 11. Third-Party Services and Integrations

### Third-Party Services
Our Service may integrate with or rely on third-party services, including:

{integrations_list}

### Third-Party Terms
- Each third-party service has its own terms and policies
- You are responsible for compliance with third-party terms
- We are not responsible for third-party service availability or performance
- Third-party integrations may change or be discontinued

### Links and References
- Our Service may contain links to third-party websites
- We do not endorse or control third-party websites
- You access third-party websites at your own risk
- Third-party privacy policies govern their data practices"""
    
    def _generate_disclaimers_section(self, config: AppTermsConfig) -> str:
        """Generate disclaimers section"""
        sections = [
            "## 12. Disclaimers",
            "",
            "### General Disclaimers",
            'THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, WHETHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO:',
            "- MERCHANTABILITY",
            "- FITNESS FOR A PARTICULAR PURPOSE",
            "- NON-INFRINGEMENT",
            "- ACCURACY OR COMPLETENESS",
            "- UNINTERRUPTED OR ERROR-FREE OPERATION"
        ]
        
        if config.ai_services:
            sections.extend([
                "",
                "### AI Service Disclaimers",
                "- AI outputs may contain errors, bias, or inappropriate content",
                "- AI services are experimental and continuously evolving",
                "- We do not guarantee accuracy of AI-generated content",
                "- AI outputs should be reviewed and validated before use"
            ])
        
        if config.financial_services:
            sections.extend([
                "",
                "### Financial Service Disclaimers",
                "- We are not providing financial, investment, or tax advice",
                "- Financial data and calculations are for informational purposes",
                "- You should consult professionals for financial decisions",
                "- Market conditions and regulations may affect service availability"
            ])
        
        return "\n".join(sections)
    
    def _generate_limitation_of_liability_section(self, config: AppTermsConfig) -> str:
        """Generate limitation of liability section"""
        base_text = """## 13. Limitation of Liability

TO THE FULLEST EXTENT PERMITTED BY LAW, IN NO EVENT SHALL WE BE LIABLE FOR:

- INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES
- LOSS OF PROFITS, DATA, USE, GOODWILL, OR OTHER INTANGIBLE LOSSES
- DAMAGES RESULTING FROM SERVICE INTERRUPTIONS OR SECURITY BREACHES
- DAMAGES CAUSED BY THIRD-PARTY SERVICES OR INTEGRATIONS

### Liability Cap
OUR TOTAL LIABILITY FOR ALL CLAIMS ARISING FROM YOUR USE OF THE SERVICE SHALL NOT EXCEED:"""
        
        if config.liability_level == LiabilityLevel.FINANCIAL:
            liability_cap = "THE GREATER OF (A) $1,000 OR (B) THE AMOUNT PAID BY YOU FOR THE SERVICE IN THE 12 MONTHS PRECEDING THE CLAIM"
        elif config.liability_level == LiabilityLevel.ENHANCED:
            liability_cap = "THE GREATER OF (A) $500 OR (B) THE AMOUNT PAID BY YOU FOR THE SERVICE IN THE 6 MONTHS PRECEDING THE CLAIM"
        else:
            liability_cap = "THE GREATER OF (A) $100 OR (B) THE AMOUNT PAID BY YOU FOR THE SERVICE IN THE 3 MONTHS PRECEDING THE CLAIM"
        
        jurisdictional_text = """
### Jurisdictional Variations
Some jurisdictions do not allow the exclusion or limitation of liability, so the above limitations may not apply to you. In such jurisdictions, our liability is limited to the fullest extent permitted by law."""
        
        return f"{base_text}\n{liability_cap}\n{jurisdictional_text}"
    
    def _generate_indemnification_section(self, config: AppTermsConfig) -> str:
        """Generate indemnification section"""
        base_indemnification = [
            "## 14. Indemnification",
            "",
            "You agree to defend, indemnify, and hold us harmless from any claims, damages, losses, costs, and expenses (including reasonable attorneys' fees) arising from or relating to:",
            "",
            "- Your use of the Service",
            "- Your violation of these Terms",
            "- Your violation of any rights of third parties",
            "- Content you submit or generate using the Service"
        ]
        
        if config.ai_services:
            base_indemnification.extend([
                "- AI outputs generated using your inputs",
                "- Use of AI-generated content in violation of third-party rights"
            ])
        
        if config.financial_services:
            base_indemnification.extend([
                "- Financial transactions conducted through the Service",
                "- Violations of financial regulations or laws",
                "- Fraudulent or illegal financial activities"
            ])
        
        base_indemnification.extend([
            "",
            "This indemnification obligation will survive termination of these Terms and your use of the Service."
        ])
        
        return "\n".join(base_indemnification)
    
    def _generate_termination_section(self, config: AppTermsConfig) -> str:
        """Generate termination section"""
        return """## 15. Termination

### Termination by You
- You may terminate your account at any time through account settings
- Termination stops future billing but doesn't refund current period
- Your data will be deleted according to our Privacy Policy

### Termination by Us
We may terminate or suspend your account immediately, without prior notice, for:
- Violation of these Terms
- Illegal or fraudulent activity
- Non-payment of fees
- Extended inactivity
- Regulatory requirements

### Effect of Termination
Upon termination:
- Your right to access the Service ceases immediately
- Outstanding payment obligations remain due
- Provisions that should survive termination will remain in effect
- We may delete your data after a reasonable retention period

### Data Export
- You may export your data before termination
- Data export may be limited after account termination
- Some data may be retained for legal compliance"""
    
    def _generate_dispute_resolution_section(self, config: AppTermsConfig) -> str:
        """Generate dispute resolution section"""
        return """## 16. Dispute Resolution

### Informal Resolution
Before filing any formal dispute, please contact us at legal@activelog.com to attempt to resolve the issue informally. We are committed to working with you to resolve disputes fairly and efficiently.

### Binding Arbitration
Any disputes arising from these Terms or your use of the Service will be resolved through binding arbitration, except for:
- Claims for injunctive relief
- Intellectual property disputes
- Small claims court matters

### Arbitration Process
- Arbitration will be conducted by the American Arbitration Association (AAA)
- Arbitration will be held in San Francisco, California, or remotely
- The arbitrator's decision is final and binding
- Class actions and jury trials are waived

### Governing Law
These Terms are governed by the laws of California, without regard to conflict of law principles. The federal and state courts of California have exclusive jurisdiction over any disputes not subject to arbitration.

### Limitation Period
Any claim must be filed within one year of the date the claim arose, or it will be permanently barred."""
    
    def _generate_changes_section(self, config: AppTermsConfig) -> str:
        """Generate changes section"""
        return f"""## 17. Changes to Terms

### Modification Rights
We reserve the right to modify these Terms at any time. When we make changes, we will:
- Post the updated Terms in the app
- Update the "Last Updated" date
- Notify users of material changes via email or app notification

### Material Changes
For significant changes that materially affect your rights or obligations, we will provide at least 30 days' notice. Your continued use of the Service after the effective date constitutes acceptance of the new Terms.

### Rejection of Changes
If you do not agree to modified Terms, you must stop using the Service and may terminate your account."""
    
    def _generate_general_provisions_section(self, config: AppTermsConfig) -> str:
        """Generate general provisions section"""
        return """## 18. General Provisions

### Entire Agreement
These Terms, together with our Privacy Policy, constitute the entire agreement between you and us regarding the Service.

### Severability
If any provision of these Terms is found to be unenforceable, the remaining provisions will remain in full force and effect.

### Waiver
No waiver of any term or condition will be deemed a further or continuing waiver of such term or any other term.

### Assignment
You may not assign your rights under these Terms without our prior written consent. We may assign our rights and obligations without restriction.

### Force Majeure
We are not liable for any failure to perform due to causes beyond our reasonable control, including natural disasters, government actions, or network failures.

### Language
These Terms are written in English. Any translations are provided for convenience only, and the English version controls in case of conflict.

### Electronic Communications
You consent to receive agreements, notices, and other communications electronically."""
    
    def _generate_contact_section(self, config: AppTermsConfig) -> str:
        """Generate contact information section"""
        return f"""## 19. Contact Information

If you have any questions about these Terms, please contact us:

**Email:** {self.contact_email}  
**Address:** {self.company_address}  
**Phone:** +1-555-TERMS (1-555-837-6769)

**Legal Notices:** For formal legal notices, please send written communication to the address above.

**Response Time:** We will respond to inquiries within 5 business days.

---

© {datetime.now().year} {self.company_name}. All rights reserved.

These Terms of Service were last updated on {self.effective_date}."""
    
    def _generate_master_terms(self) -> str:
        """Generate master terms of service covering all apps"""
        return f"""# ActiveLog Master Terms of Service

**Effective Date:** {self.effective_date}  
**Last Updated:** {self.effective_date}

These Master Terms of Service govern your use of all applications and services provided by {self.company_name} ("ActiveLog," "we," "us," or "our").

## Our Applications

We provide the following applications, each with specific terms:

### ActiveLog (Productivity App)
- **Purpose:** Activity logging and productivity tracking
- **Bundle ID:** com.activelog.app
- **Age Requirement:** 13+
- **Key Features:** Time tracking, team collaboration, data sync

### ActiveLog AI (AI Tools)
- **Purpose:** AI-powered content generation and automation
- **Bundle ID:** com.activelog.ai
- **Age Requirement:** 16+
- **Key Features:** AI content generation, model training, API access

### ActiveLedger (Financial Platform)
- **Purpose:** Financial services and transaction processing
- **Bundle ID:** com.activelog.ledger
- **Age Requirement:** 18+
- **Key Features:** Payment processing, currency exchange, financial analytics

## Universal Terms

The following terms apply to all ActiveLog applications:

### Account Requirements
- One account can access multiple applications
- Age requirements vary by application (highest requirement applies)
- Enhanced verification may be required for certain features
- Account security is your responsibility

### Acceptable Use
Across all applications, you may not:
- Violate any applicable laws or regulations
- Infringe upon the rights of others
- Transmit harmful or inappropriate content
- Attempt unauthorized access to our systems
- Use automated systems without permission

### Subscription and Billing
- Unified billing across all applications
- Subscription features vary by application
- Enterprise plans available for business use
- Standard cancellation and refund policies apply

### Privacy and Data Protection
- Unified privacy policy covers all applications
- Data sharing between applications with your consent
- Enhanced protection for financial and AI data
- User control over data usage and retention

### Support and Contact
For support with any ActiveLog application:
- **Email:** support@activelog.com
- **Legal:** legal@activelog.com
- **Privacy:** privacy@activelog.com

## Application-Specific Terms

Each application has additional terms that apply when using that specific service. Please review the individual terms for each application you use:

- ActiveLog Terms: Available in-app and at activelog.com/terms
- ActiveLog AI Terms: Available in-app and at activelog.com/ai-terms
- ActiveLedger Terms: Available in-app and at activelog.com/ledger-terms

By using any ActiveLog application, you agree to both these Master Terms and the specific terms for that application."""
    
    def _save_terms(self, app_id: str, content: str):
        """Save terms of service to file"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save as markdown
        md_path = os.path.join(self.output_dir, f"{app_id}_terms_of_service.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save as HTML for web display
        html_content = self._convert_to_html(content)
        html_path = os.path.join(self.output_dir, f"{app_id}_terms_of_service.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _convert_to_html(self, markdown_content: str) -> str:
        """Convert markdown to HTML"""
        try:
            import markdown
            html_body = markdown.markdown(markdown_content, extensions=['tables'])
        except ImportError:
            # Fallback: simple HTML conversion
            html_body = markdown_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            html_body = f"<p>{html_body}</p>"
        
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - ActiveLog</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        h2 {{ border-bottom: 2px solid #eee; padding-bottom: 10px; }}
        .legal-text {{ font-size: 14px; color: #666; }}
        .important {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; margin: 20px 0; border-radius: 5px; }}
        ul, ol {{ padding-left: 25px; }}
        .last-updated {{ color: #666; font-style: italic; margin-top: 40px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    {html_body}
    <div class="last-updated">
        <p>These terms were generated automatically on {self.effective_date}</p>
        <p>For the most current version, please check the in-app terms or visit our website.</p>
    </div>
</body>
</html>"""
        
        return html_template

def main():
    """Generate all terms of service"""
    generator = TermsOfServiceGenerator()
    generator.generate_all_terms()
    print("Terms of service generation completed!")
    print(f"Output directory: {generator.output_dir}")

if __name__ == "__main__":
    main()