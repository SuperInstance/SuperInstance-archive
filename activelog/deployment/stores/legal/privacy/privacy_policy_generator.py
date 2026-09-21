#!/usr/bin/env python3
"""
Privacy Policy Generator for ActiveLog Applications
Generates comprehensive, legally compliant privacy policies for each app vertical
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

class DataType(Enum):
    PERSONAL_INFO = "personal_info"
    FINANCIAL_DATA = "financial_data"
    AI_INPUTS = "ai_inputs"
    USAGE_DATA = "usage_data"
    DEVICE_INFO = "device_info"
    LOCATION_DATA = "location_data"

@dataclass
class DataCollection:
    data_type: DataType
    purpose: str
    legal_basis: str
    retention_period: str
    shared_with: List[str]
    user_control: str

@dataclass
class AppConfig:
    name: str
    app_type: AppType
    bundle_id: str
    data_collections: List[DataCollection]
    features: List[str]
    third_party_services: List[str]
    age_restriction: int

class PrivacyPolicyGenerator:
    """Generates comprehensive privacy policies for ActiveLog applications"""
    
    def __init__(self):
        self.company_name = "ActiveLog Technologies"
        self.company_address = "123 Innovation Drive, San Francisco, CA 94105"
        self.contact_email = "privacy@activelog.com"
        self.effective_date = datetime.now().strftime("%B %d, %Y")
        self.output_dir = "/home/activeloguser/activelog/deployment/stores/legal/privacy"
        
        # Load app configurations
        self.apps = self._load_app_configurations()
    
    def _load_app_configurations(self) -> Dict[str, AppConfig]:
        """Load app-specific privacy configurations"""
        return {
            "activelog": AppConfig(
                name="ActiveLog",
                app_type=AppType.PRODUCTIVITY,
                bundle_id="com.activelog.app",
                data_collections=[
                    DataCollection(
                        data_type=DataType.PERSONAL_INFO,
                        purpose="Account creation and user authentication",
                        legal_basis="Contract performance and legitimate interests",
                        retention_period="Account lifetime + 3 years",
                        shared_with=["Authentication providers", "Analytics services"],
                        user_control="Edit in account settings, delete account"
                    ),
                    DataCollection(
                        data_type=DataType.USAGE_DATA,
                        purpose="App improvement and analytics",
                        legal_basis="Legitimate interests",
                        retention_period="2 years",
                        shared_with=["Analytics providers", "Crash reporting services"],
                        user_control="Opt-out in settings"
                    ),
                    DataCollection(
                        data_type=DataType.DEVICE_INFO,
                        purpose="Technical support and debugging",
                        legal_basis="Legitimate interests",
                        retention_period="1 year",
                        shared_with=["Technical support providers"],
                        user_control="Cannot be disabled"
                    ),
                    DataCollection(
                        data_type=DataType.LOCATION_DATA,
                        purpose="Location-based logging features",
                        legal_basis="Consent",
                        retention_period="User-controlled deletion",
                        shared_with=["None (stored locally)"],
                        user_control="Enable/disable in permissions, delete logs"
                    )
                ],
                features=[
                    "Activity logging", "Time tracking", "Photo attachments",
                    "Voice memos", "Team collaboration", "Data export",
                    "Calendar integration", "Notifications"
                ],
                third_party_services=[
                    "Google Analytics", "Firebase Crashlytics", "Auth0",
                    "SendGrid", "AWS S3", "Stripe"
                ],
                age_restriction=13
            ),
            
            "activelog-ai": AppConfig(
                name="ActiveLog AI",
                app_type=AppType.AI_TOOLS,
                bundle_id="com.activelog.ai",
                data_collections=[
                    DataCollection(
                        data_type=DataType.PERSONAL_INFO,
                        purpose="Account management and billing",
                        legal_basis="Contract performance",
                        retention_period="Account lifetime + 7 years",
                        shared_with=["Payment processors", "Identity verification"],
                        user_control="Edit profile, delete account after data retention"
                    ),
                    DataCollection(
                        data_type=DataType.AI_INPUTS,
                        purpose="AI model processing and generation",
                        legal_basis="Contract performance and consent",
                        retention_period="30 days (cache), user-controlled (permanent)",
                        shared_with=["AI service providers (OpenAI, Anthropic, etc.)"],
                        user_control="Delete individual inputs, disable data sharing"
                    ),
                    DataCollection(
                        data_type=DataType.USAGE_DATA,
                        purpose="Service optimization and cost calculation",
                        legal_basis="Legitimate interests",
                        retention_period="2 years",
                        shared_with=["Analytics providers", "Performance monitoring"],
                        user_control="Opt-out in privacy settings"
                    ),
                    DataCollection(
                        data_type=DataType.DEVICE_INFO,
                        purpose="Local vs cloud compute optimization",
                        legal_basis="Legitimate interests",
                        retention_period="6 months",
                        shared_with=["None"],
                        user_control="Limited control (required for optimization)"
                    )
                ],
                features=[
                    "AI image generation", "Text generation", "Voice synthesis",
                    "Model training", "Batch processing", "Cost optimization",
                    "Result caching", "API integrations"
                ],
                third_party_services=[
                    "OpenAI", "Anthropic", "Stability AI", "ElevenLabs",
                    "Google Cloud", "AWS", "Firebase", "Stripe"
                ],
                age_restriction=16
            ),
            
            "activeledger": AppConfig(
                name="ActiveLedger",
                app_type=AppType.FINANCIAL,
                bundle_id="com.activelog.ledger",
                data_collections=[
                    DataCollection(
                        data_type=DataType.PERSONAL_INFO,
                        purpose="Identity verification and KYC compliance",
                        legal_basis="Legal obligation and contract performance",
                        retention_period="7 years after account closure",
                        shared_with=["Identity verification providers", "Regulatory authorities"],
                        user_control="Limited (required for compliance)"
                    ),
                    DataCollection(
                        data_type=DataType.FINANCIAL_DATA,
                        purpose="Transaction processing and financial services",
                        legal_basis="Contract performance and legal obligation",
                        retention_period="7 years (regulatory requirement)",
                        shared_with=["Payment processors", "Banking partners", "Auditors"],
                        user_control="View and export (deletion restricted by law)"
                    ),
                    DataCollection(
                        data_type=DataType.USAGE_DATA,
                        purpose="Fraud detection and service improvement",
                        legal_basis="Legitimate interests",
                        retention_period="3 years",
                        shared_with=["Fraud detection services", "Analytics providers"],
                        user_control="Limited opt-out (fraud detection required)"
                    ),
                    DataCollection(
                        data_type=DataType.LOCATION_DATA,
                        purpose="Fraud detection and compliance",
                        legal_basis="Legitimate interests and legal obligation",
                        retention_period="2 years",
                        shared_with=["Fraud detection services", "Compliance systems"],
                        user_control="Cannot disable (security requirement)"
                    )
                ],
                features=[
                    "Payment processing", "Multi-currency exchange", "Subscription billing",
                    "Marketplace transactions", "Financial analytics", "Compliance reporting",
                    "Fraud detection", "API access"
                ],
                third_party_services=[
                    "Stripe", "PayPal", "Plaid", "Jumio", "Chainalysis",
                    "AWS", "Firebase", "SendGrid", "Mixpanel"
                ],
                age_restriction=18
            )
        }
    
    def generate_all_policies(self):
        """Generate privacy policies for all applications"""
        for app_id, config in self.apps.items():
            policy_content = self._generate_policy(config)
            self._save_policy(app_id, policy_content)
            print(f"Generated privacy policy for {config.name}")
        
        # Generate master privacy policy
        master_policy = self._generate_master_policy()
        self._save_policy("master", master_policy)
        print("Generated master privacy policy")
    
    def _generate_policy(self, config: AppConfig) -> str:
        """Generate privacy policy for a specific app"""
        sections = [
            self._generate_header(config),
            self._generate_overview(config),
            self._generate_data_collection_section(config),
            self._generate_data_use_section(config),
            self._generate_data_sharing_section(config),
            self._generate_data_retention_section(config),
            self._generate_user_rights_section(config),
            self._generate_security_section(config),
            self._generate_cookies_section(config),
            self._generate_children_section(config),
            self._generate_international_section(config),
            self._generate_changes_section(config),
            self._generate_contact_section(config)
        ]
        
        return "\n\n".join(sections)
    
    def _generate_header(self, config: AppConfig) -> str:
        """Generate policy header"""
        return f"""# Privacy Policy for {config.name}

**Effective Date:** {self.effective_date}  
**Last Updated:** {self.effective_date}

{self.company_name} ("we," "our," or "us") respects your privacy and is committed to protecting your personal information. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use the {config.name} mobile application (the "App") and related services (collectively, the "Services").

**Bundle Identifier:** {config.bundle_id}

Please read this Privacy Policy carefully. By using our Services, you agree to the collection and use of information in accordance with this policy."""
    
    def _generate_overview(self, config: AppConfig) -> str:
        """Generate overview section"""
        app_type_descriptions = {
            AppType.PRODUCTIVITY: "productivity and activity tracking",
            AppType.AI_TOOLS: "artificial intelligence and content generation",
            AppType.FINANCIAL: "financial services and transaction processing"
        }
        
        description = app_type_descriptions.get(config.app_type, "general")
        
        return f"""## 1. Overview

{config.name} is a {description} application that provides the following key features:

{self._format_list(config.features)}

This Privacy Policy applies to all users of {config.name} and covers our practices regarding personal data collection, processing, and protection."""
    
    def _generate_data_collection_section(self, config: AppConfig) -> str:
        """Generate data collection section"""
        sections = [
            "## 2. Information We Collect",
            "",
            "We collect information you provide directly to us, information we obtain automatically when you use our Services, and information from third-party sources."
        ]
        
        for collection in config.data_collections:
            data_type_names = {
                DataType.PERSONAL_INFO: "Personal Information",
                DataType.FINANCIAL_DATA: "Financial Information",
                DataType.AI_INPUTS: "AI Input Data",
                DataType.USAGE_DATA: "Usage and Analytics Data",
                DataType.DEVICE_INFO: "Device Information",
                DataType.LOCATION_DATA: "Location Information"
            }
            
            type_name = data_type_names.get(collection.data_type, str(collection.data_type))
            
            sections.extend([
                f"### {type_name}",
                f"**Purpose:** {collection.purpose}",
                f"**Legal Basis:** {collection.legal_basis}",
                f"**Your Control:** {collection.user_control}",
                ""
            ])
        
        # Add specific details based on app type
        if config.app_type == AppType.AI_TOOLS:
            sections.extend([
                "### AI-Specific Data Collection",
                "When you use our AI features, we may collect:",
                "- Text prompts and instructions",
                "- Images uploaded for processing",
                "- Voice recordings for synthesis",
                "- Generated outputs and results",
                "- Model preferences and settings",
                "",
                "**Important:** Your AI inputs may be processed by third-party AI providers (OpenAI, Anthropic, etc.) according to their privacy policies."
            ])
        
        elif config.app_type == AppType.FINANCIAL:
            sections.extend([
                "### Financial Data Collection",
                "For regulatory compliance and service provision, we collect:",
                "- Identity verification documents",
                "- Banking and payment information",
                "- Transaction history and patterns",
                "- Credit and financial standing information",
                "- Tax identification numbers",
                "",
                "**Regulatory Note:** Some financial data collection is required by law and cannot be opted out of."
            ])
        
        return "\n".join(sections)
    
    def _generate_data_use_section(self, config: AppConfig) -> str:
        """Generate data use section"""
        sections = [
            "## 3. How We Use Your Information",
            "",
            "We use the information we collect for the following purposes:"
        ]
        
        general_uses = [
            "Provide, maintain, and improve our Services",
            "Process transactions and send related information",
            "Send technical notices and support messages",
            "Respond to comments, questions, and customer service requests",
            "Monitor and analyze trends and usage",
            "Detect, investigate, and prevent fraudulent transactions",
            "Comply with legal obligations"
        ]
        
        if config.app_type == AppType.AI_TOOLS:
            general_uses.extend([
                "Process AI requests and generate content",
                "Optimize model selection and performance",
                "Cache results for improved efficiency",
                "Train and improve AI models (with consent)"
            ])
        
        elif config.app_type == AppType.FINANCIAL:
            general_uses.extend([
                "Verify identity and prevent money laundering",
                "Process payments and currency exchanges",
                "Calculate fees and maintain accurate records",
                "Generate financial reports and statements",
                "Comply with financial regulations"
            ])
        
        sections.append(self._format_list(general_uses))
        
        return "\n".join(sections)
    
    def _generate_data_sharing_section(self, config: AppConfig) -> str:
        """Generate data sharing section"""
        sections = [
            "## 4. Information Sharing and Disclosure",
            "",
            "We may share your information in the following circumstances:"
        ]
        
        sharing_scenarios = [
            "**Service Providers:** We work with third-party service providers who perform services on our behalf",
            "**Legal Requirements:** When required by law or to protect our rights and safety",
            "**Business Transfers:** In connection with mergers, acquisitions, or asset sales",
            "**Consent:** When you have given us explicit consent to share your information"
        ]
        
        if config.app_type == AppType.AI_TOOLS:
            sharing_scenarios.insert(0, "**AI Providers:** Your prompts and inputs are shared with AI service providers for processing")
        
        elif config.app_type == AppType.FINANCIAL:
            sharing_scenarios.insert(0, "**Financial Partners:** Banking partners, payment processors, and regulatory authorities as required")
        
        sections.extend(sharing_scenarios)
        
        # Add third-party services list
        sections.extend([
            "",
            "### Third-Party Services",
            f"We work with the following types of service providers:",
            self._format_list(config.third_party_services)
        ])
        
        return "\n".join(sections)
    
    def _generate_data_retention_section(self, config: AppConfig) -> str:
        """Generate data retention section"""
        sections = [
            "## 5. Data Retention",
            "",
            "We retain your information for different periods depending on the type of data and purpose:"
        ]
        
        retention_info = []
        for collection in config.data_collections:
            data_type_names = {
                DataType.PERSONAL_INFO: "Personal Information",
                DataType.FINANCIAL_DATA: "Financial Data",
                DataType.AI_INPUTS: "AI Input Data",
                DataType.USAGE_DATA: "Usage Data",
                DataType.DEVICE_INFO: "Device Information",
                DataType.LOCATION_DATA: "Location Data"
            }
            
            type_name = data_type_names.get(collection.data_type, str(collection.data_type))
            retention_info.append(f"**{type_name}:** {collection.retention_period}")
        
        sections.extend(retention_info)
        
        if config.app_type == AppType.FINANCIAL:
            sections.extend([
                "",
                "**Regulatory Note:** Financial institutions are required by law to retain certain records for specified periods (typically 7 years). This may limit our ability to delete some information upon request."
            ])
        
        return "\n".join(sections)
    
    def _generate_user_rights_section(self, config: AppConfig) -> str:
        """Generate user rights section"""
        sections = [
            "## 6. Your Rights and Choices",
            "",
            "Depending on your location, you may have the following rights regarding your personal information:"
        ]
        
        rights = [
            "**Access:** Request access to your personal information",
            "**Correction:** Request correction of inaccurate information",
            "**Deletion:** Request deletion of your information (subject to legal requirements)",
            "**Portability:** Request a copy of your information in a portable format",
            "**Restriction:** Request restriction of processing",
            "**Objection:** Object to processing based on legitimate interests"
        ]
        
        sections.extend(rights)
        
        # Add controls table
        sections.extend([
            "",
            "### Your Control Over Your Information",
            ""
        ])
        
        # Create table of user controls
        control_table = ["| Data Type | Your Control |", "| --- | --- |"]
        for collection in config.data_collections:
            data_type_names = {
                DataType.PERSONAL_INFO: "Personal Info",
                DataType.FINANCIAL_DATA: "Financial Data",
                DataType.AI_INPUTS: "AI Inputs",
                DataType.USAGE_DATA: "Usage Data",
                DataType.DEVICE_INFO: "Device Info",
                DataType.LOCATION_DATA: "Location Data"
            }
            
            type_name = data_type_names.get(collection.data_type, str(collection.data_type))
            control_table.append(f"| {type_name} | {collection.user_control} |")
        
        sections.extend(control_table)
        
        return "\n".join(sections)
    
    def _generate_security_section(self, config: AppConfig) -> str:
        """Generate security section"""
        sections = [
            "## 7. Data Security",
            "",
            "We implement appropriate technical and organizational measures to protect your personal information against unauthorized access, alteration, disclosure, or destruction."
        ]
        
        security_measures = [
            "**Encryption:** Data is encrypted in transit and at rest",
            "**Access Controls:** Strict access controls and authentication requirements",
            "**Regular Audits:** Security assessments and vulnerability testing",
            "**Employee Training:** Regular privacy and security training for our team",
            "**Incident Response:** Procedures for detecting and responding to security incidents"
        ]
        
        if config.app_type == AppType.FINANCIAL:
            security_measures.extend([
                "**Financial Security:** PCI DSS compliance and SOX controls",
                "**Fraud Detection:** Advanced fraud monitoring and prevention systems",
                "**Regulatory Compliance:** SOC 2 Type II certification"
            ])
        
        elif config.app_type == AppType.AI_TOOLS:
            security_measures.extend([
                "**Local Processing:** Option to process sensitive data locally",
                "**Data Minimization:** Only necessary data is sent to AI providers",
                "**Secure APIs:** All third-party AI integrations use secure connections"
            ])
        
        sections.extend(security_measures)
        
        sections.extend([
            "",
            "While we strive to protect your personal information, no method of transmission over the internet or electronic storage is 100% secure. We cannot guarantee absolute security."
        ])
        
        return "\n".join(sections)
    
    def _generate_cookies_section(self, config: AppConfig) -> str:
        """Generate cookies and tracking section"""
        return """## 8. Cookies and Tracking Technologies

We use cookies and similar tracking technologies to collect and use personal information about you. For further information about the types of cookies we use, why, and how you can control cookies, please see our Cookie Policy.

### Types of Cookies We Use:
- **Essential Cookies:** Required for basic app functionality
- **Analytics Cookies:** Help us understand how you use our Services
- **Preference Cookies:** Remember your settings and preferences
- **Performance Cookies:** Improve app performance and user experience

You can control cookies through your device settings, but disabling certain cookies may limit app functionality."""
    
    def _generate_children_section(self, config: AppConfig) -> str:
        """Generate children's privacy section"""
        if config.age_restriction >= 18:
            age_text = "18 years of age"
            coppa_text = "We do not knowingly collect personal information from anyone under 18."
        elif config.age_restriction >= 16:
            age_text = "16 years of age"
            coppa_text = "We do not knowingly collect personal information from children under 16 without parental consent."
        else:
            age_text = "13 years of age"
            coppa_text = "We comply with COPPA and do not knowingly collect personal information from children under 13 without verifiable parental consent."
        
        return f"""## 9. Children's Privacy

Our Services are not intended for individuals under {age_text}. {coppa_text}

If you are a parent or guardian and believe your child has provided us with personal information, please contact us immediately. We will take steps to remove such information from our systems.

**Age Verification:** Users may be required to verify their age before accessing certain features, particularly in our financial services."""
    
    def _generate_international_section(self, config: AppConfig) -> str:
        """Generate international transfers section"""
        return f"""## 10. International Data Transfers

Your information may be transferred to and processed in countries other than your country of residence. These countries may have data protection laws that are different from the laws of your country.

We ensure appropriate safeguards are in place for international transfers, including:
- **Standard Contractual Clauses:** EU-approved model contracts
- **Adequacy Decisions:** Transfers to countries with adequate protection
- **Privacy Shield:** Compliance with applicable frameworks
- **Data Processing Agreements:** Contractual protections with service providers

**For EU Users:** We comply with GDPR requirements for international transfers and ensure adequate protection for your personal data."""
    
    def _generate_changes_section(self, config: AppConfig) -> str:
        """Generate policy changes section"""
        return f"""## 11. Changes to This Privacy Policy

We may update this Privacy Policy from time to time. We will notify you of any changes by:
- Posting the new Privacy Policy in the app
- Sending you an email notification
- Displaying a prominent notice in our Services

**Material Changes:** For significant changes that affect how we use your personal information, we will provide at least 30 days' notice and may require your consent.

The "Last Updated" date at the top of this Privacy Policy indicates when it was last revised."""
    
    def _generate_contact_section(self, config: AppConfig) -> str:
        """Generate contact information section"""
        return f"""## 12. Contact Us

If you have any questions about this Privacy Policy or our privacy practices, please contact us:

**Email:** {self.contact_email}  
**Address:** {self.company_address}  
**Phone:** +1-555-PRIVACY (1-555-774-8229)

**Data Protection Officer:** For EU users, you can contact our Data Protection Officer at dpo@activelog.com

**Response Time:** We will respond to your privacy inquiries within 30 days (or as required by applicable law).

---

© {datetime.now().year} {self.company_name}. All rights reserved."""
    
    def _generate_master_policy(self) -> str:
        """Generate master privacy policy covering all apps"""
        sections = [
            f"""# ActiveLog Privacy Policy - Master Policy

**Effective Date:** {self.effective_date}  
**Last Updated:** {self.effective_date}

This master privacy policy covers all ActiveLog applications and services provided by {self.company_name}. For app-specific details, please refer to the individual privacy policies for each application.

## Our Applications

We provide the following applications, each with specific privacy considerations:

### ActiveLog (Productivity App)
- **Purpose:** Activity logging and productivity tracking
- **Bundle ID:** com.activelog.app
- **Age Restriction:** 13+
- **Key Privacy Features:** Local data storage options, team collaboration controls

### ActiveLog AI (AI Tools)
- **Purpose:** AI-powered content generation and automation
- **Bundle ID:** com.activelog.ai
- **Age Restriction:** 16+
- **Key Privacy Features:** Local AI processing, data sharing controls for AI providers

### ActiveLedger (Financial Platform)
- **Purpose:** Financial services and transaction processing
- **Bundle ID:** com.activelog.ledger
- **Age Restriction:** 18+
- **Key Privacy Features:** Enhanced security, regulatory compliance, KYC requirements

## Universal Privacy Principles

Across all our applications, we adhere to the following privacy principles:

1. **Transparency:** Clear communication about data practices
2. **User Control:** Meaningful choices about your information
3. **Data Minimization:** Collect only what's necessary
4. **Security First:** Strong protection for your data
5. **Compliance:** Adherence to applicable privacy laws

## Your Rights Across All Apps

Regardless of which ActiveLog app you use, you have the following rights:
- Access your personal information
- Correct inaccurate information
- Delete your information (subject to legal requirements)
- Port your data to another service
- Restrict processing of your information
- Object to processing based on legitimate interests

For specific details about each application, please refer to their individual privacy policies."""
        ]
        
        return "\n\n".join(sections)
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items as markdown"""
        return "\n".join([f"- {item}" for item in items])
    
    def _save_policy(self, app_id: str, content: str):
        """Save privacy policy to file"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Save as markdown
        md_path = os.path.join(self.output_dir, f"{app_id}_privacy_policy.md")
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Save as HTML for web display
        html_content = self._convert_to_html(content)
        html_path = os.path.join(self.output_dir, f"{app_id}_privacy_policy.html")
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
    <title>Privacy Policy - ActiveLog</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
               line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .last-updated {{ color: #666; font-style: italic; }}
    </style>
</head>
<body>
    {html_body}
    <div class="last-updated">
        <p>This policy was generated automatically on {self.effective_date}</p>
    </div>
</body>
</html>"""
        
        return html_template

def main():
    """Generate all privacy policies"""
    generator = PrivacyPolicyGenerator()
    generator.generate_all_policies()
    print("Privacy policy generation completed!")
    print(f"Output directory: {generator.output_dir}")

if __name__ == "__main__":
    main()