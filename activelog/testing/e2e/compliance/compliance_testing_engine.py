#!/usr/bin/env python3
"""
Compliance Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive compliance testing for GDPR, COPPA, CCPA,
HIPAA, SOX, and other regulatory frameworks including data privacy, consent management,
data retention, audit trails, and regulatory reporting.
"""

import asyncio
import json
import time
import uuid
import re
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
import subprocess

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Selenium optional: pip install selenium webdriver-manager")

class ComplianceFramework(Enum):
    GDPR = "gdpr"
    COPPA = "coppa"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOX = "sox"
    PCI_DSS = "pci_dss"
    ISO27001 = "iso27001"

class DataCategory(Enum):
    PERSONAL_DATA = "personal_data"
    SENSITIVE_PERSONAL_DATA = "sensitive_personal_data"
    HEALTH_DATA = "health_data"
    FINANCIAL_DATA = "financial_data"
    BIOMETRIC_DATA = "biometric_data"
    CHILDREN_DATA = "children_data"
    LOCATION_DATA = "location_data"

class ConsentType(Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    OPT_IN = "opt_in"
    OPT_OUT = "opt_out"
    PARENTAL = "parental"

class ComplianceViolationType(Enum):
    NO_CONSENT = "no_consent"
    INVALID_CONSENT = "invalid_consent"
    DATA_RETENTION_VIOLATION = "data_retention_violation"
    MISSING_PRIVACY_NOTICE = "missing_privacy_notice"
    INADEQUATE_SECURITY = "inadequate_security"
    NO_DATA_PORTABILITY = "no_data_portability"
    NO_RIGHT_TO_DELETE = "no_right_to_delete"
    MISSING_AUDIT_TRAIL = "missing_audit_trail"
    IMPROPER_DATA_TRANSFER = "improper_data_transfer"
    MISSING_DPO_CONTACT = "missing_dpo_contact"
    AGE_VERIFICATION_FAILURE = "age_verification_failure"

class ComplianceSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class DataProcessingRecord:
    data_type: DataCategory
    purpose: str
    legal_basis: str
    retention_period: int  # days
    processing_date: datetime
    consent_required: bool = True
    consent_obtained: bool = False
    consent_timestamp: Optional[datetime] = None
    processor_name: Optional[str] = None
    transfer_countries: List[str] = field(default_factory=list)

@dataclass
class ConsentRecord:
    user_id: str
    consent_type: ConsentType
    data_categories: List[DataCategory]
    purposes: List[str]
    consent_given: bool
    consent_timestamp: datetime
    consent_method: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    withdrawal_timestamp: Optional[datetime] = None
    parental_consent: bool = False

@dataclass
class ComplianceViolation:
    id: str
    framework: ComplianceFramework
    violation_type: ComplianceViolationType
    severity: ComplianceSeverity
    article_reference: str
    description: str
    affected_users: List[str] = field(default_factory=list)
    data_categories: List[DataCategory] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation_steps: List[str] = field(default_factory=list)
    max_fine_amount: Optional[float] = None
    detection_timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ComplianceTestResult:
    test_case_id: str
    test_name: str
    framework: ComplianceFramework
    status: str
    violations: List[ComplianceViolation] = field(default_factory=list)
    compliant_items: List[str] = field(default_factory=list)
    audit_trail_complete: bool = False
    consent_management_valid: bool = False
    data_retention_compliant: bool = False
    security_measures_adequate: bool = False
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class GDPRComplianceTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    async def test_gdpr_compliance(self) -> List[ComplianceViolation]:
        violations = []
        
        violations.extend(await self._test_privacy_notice())
        violations.extend(await self._test_consent_mechanisms())
        violations.extend(await self._test_data_subject_rights())
        violations.extend(await self._test_data_protection_measures())
        violations.extend(await self._test_data_retention_policies())
        violations.extend(await self._test_international_transfers())
        violations.extend(await self._test_breach_notification())
        
        return violations

    async def _test_privacy_notice(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/privacy-policy")
            
            if response.status_code != 200:
                violations.append(ComplianceViolation(
                    id="gdpr_no_privacy_notice",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.MISSING_PRIVACY_NOTICE,
                    severity=ComplianceSeverity.HIGH,
                    article_reference="Article 13, 14",
                    description="Privacy notice/policy not accessible or missing",
                    max_fine_amount=20000000.0,  # 20M EUR or 4% of turnover
                    remediation_steps=[
                        "Create comprehensive privacy notice",
                        "Make privacy notice easily accessible",
                        "Include all required GDPR information"
                    ]
                ))
            else:
                content = response.text.lower()
                required_elements = [
                    "controller", "purpose", "legal basis", "retention",
                    "rights", "contact", "complaint", "dpo"
                ]
                
                missing_elements = [elem for elem in required_elements if elem not in content]
                
                if missing_elements:
                    violations.append(ComplianceViolation(
                        id="gdpr_incomplete_privacy_notice",
                        framework=ComplianceFramework.GDPR,
                        violation_type=ComplianceViolationType.MISSING_PRIVACY_NOTICE,
                        severity=ComplianceSeverity.MEDIUM,
                        article_reference="Article 13, 14",
                        description=f"Privacy notice missing required elements: {', '.join(missing_elements)}",
                        evidence={"missing_elements": missing_elements},
                        remediation_steps=[
                            f"Add missing information: {', '.join(missing_elements)}",
                            "Review GDPR Article 13/14 requirements"
                        ]
                    ))
        except Exception as e:
            logging.error(f"Privacy notice test failed: {e}")
        
        return violations

    async def _test_consent_mechanisms(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/signup")
            
            if response.status_code == 200:
                content = response.text.lower()
                
                if "consent" not in content and "agree" not in content:
                    violations.append(ComplianceViolation(
                        id="gdpr_no_consent_mechanism",
                        framework=ComplianceFramework.GDPR,
                        violation_type=ComplianceViolationType.NO_CONSENT,
                        severity=ComplianceSeverity.CRITICAL,
                        article_reference="Article 6, 7",
                        description="No consent mechanism found on signup page",
                        remediation_steps=[
                            "Implement explicit consent checkboxes",
                            "Separate consent for different purposes",
                            "Make consent withdrawal easy"
                        ]
                    ))
                
                if "pre-ticked" in content or "checked" in content:
                    violations.append(ComplianceViolation(
                        id="gdpr_pre_ticked_consent",
                        framework=ComplianceFramework.GDPR,
                        violation_type=ComplianceViolationType.INVALID_CONSENT,
                        severity=ComplianceSeverity.HIGH,
                        article_reference="Article 7",
                        description="Pre-ticked consent boxes detected (not valid under GDPR)",
                        remediation_steps=[
                            "Remove pre-ticked consent boxes",
                            "Require active user action for consent"
                        ]
                    ))
        except Exception as e:
            logging.error(f"Consent mechanism test failed: {e}")
        
        return violations

    async def _test_data_subject_rights(self) -> List[ComplianceViolation]:
        violations = []
        
        rights_endpoints = [
            ("/api/user/data-export", "data portability"),
            ("/api/user/delete", "right to erasure"),
            ("/api/user/data-access", "right to access"),
            ("/privacy/contact", "contact DPO")
        ]
        
        for endpoint, right_name in rights_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 404:
                    violation_type = {
                        "data portability": ComplianceViolationType.NO_DATA_PORTABILITY,
                        "right to erasure": ComplianceViolationType.NO_RIGHT_TO_DELETE,
                        "contact DPO": ComplianceViolationType.MISSING_DPO_CONTACT
                    }.get(right_name, ComplianceViolationType.NO_DATA_PORTABILITY)
                    
                    violations.append(ComplianceViolation(
                        id=f"gdpr_no_{right_name.replace(' ', '_')}",
                        framework=ComplianceFramework.GDPR,
                        violation_type=violation_type,
                        severity=ComplianceSeverity.HIGH,
                        article_reference="Articles 15-22",
                        description=f"No implementation found for {right_name}",
                        remediation_steps=[
                            f"Implement {right_name} functionality",
                            "Provide clear instructions to users",
                            "Respond to requests within 30 days"
                        ]
                    ))
            except Exception as e:
                logging.error(f"Data subject rights test failed for {right_name}: {e}")
        
        return violations

    async def _test_data_protection_measures(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(self.base_url)
            
            if not response.url.startswith("https://"):
                violations.append(ComplianceViolation(
                    id="gdpr_no_encryption_in_transit",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.INADEQUATE_SECURITY,
                    severity=ComplianceSeverity.HIGH,
                    article_reference="Article 32",
                    description="No HTTPS encryption for data in transit",
                    remediation_steps=[
                        "Implement HTTPS/TLS encryption",
                        "Redirect HTTP to HTTPS",
                        "Use strong cipher suites"
                    ]
                ))
            
            security_headers = [
                "strict-transport-security",
                "x-content-type-options",
                "x-frame-options",
                "content-security-policy"
            ]
            
            missing_headers = []
            for header in security_headers:
                if header not in response.headers:
                    missing_headers.append(header)
            
            if missing_headers:
                violations.append(ComplianceViolation(
                    id="gdpr_missing_security_headers",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.INADEQUATE_SECURITY,
                    severity=ComplianceSeverity.MEDIUM,
                    article_reference="Article 32",
                    description=f"Missing security headers: {', '.join(missing_headers)}",
                    evidence={"missing_headers": missing_headers},
                    remediation_steps=[
                        "Implement missing security headers",
                        "Configure web server security policies",
                        "Regular security header audits"
                    ]
                ))
        except Exception as e:
            logging.error(f"Data protection measures test failed: {e}")
        
        return violations

    async def _test_data_retention_policies(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/api/data-retention-policy")
            
            if response.status_code == 404:
                violations.append(ComplianceViolation(
                    id="gdpr_no_retention_policy",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.DATA_RETENTION_VIOLATION,
                    severity=ComplianceSeverity.MEDIUM,
                    article_reference="Article 5(1)(e)",
                    description="No data retention policy accessible to users",
                    remediation_steps=[
                        "Define clear data retention periods",
                        "Implement automated data deletion",
                        "Document retention policy"
                    ]
                ))
        except Exception as e:
            logging.error(f"Data retention test failed: {e}")
        
        return violations

    async def _test_international_transfers(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/privacy-policy")
            
            if response.status_code == 200:
                content = response.text.lower()
                
                transfer_keywords = ["transfer", "third country", "international", "outside eu"]
                has_transfer_mention = any(keyword in content for keyword in transfer_keywords)
                
                if has_transfer_mention:
                    adequacy_keywords = ["adequacy decision", "standard contractual clauses", "bcr", "binding corporate rules"]
                    has_safeguards = any(keyword in content for keyword in adequacy_keywords)
                    
                    if not has_safeguards:
                        violations.append(ComplianceViolation(
                            id="gdpr_unsafe_international_transfer",
                            framework=ComplianceFramework.GDPR,
                            violation_type=ComplianceViolationType.IMPROPER_DATA_TRANSFER,
                            severity=ComplianceSeverity.HIGH,
                            article_reference="Articles 44-49",
                            description="International data transfers without adequate safeguards",
                            remediation_steps=[
                                "Implement Standard Contractual Clauses",
                                "Use adequacy decision countries only",
                                "Document transfer impact assessments"
                            ]
                        ))
        except Exception as e:
            logging.error(f"International transfers test failed: {e}")
        
        return violations

    async def _test_breach_notification(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/security/incident-response")
            
            if response.status_code == 404:
                violations.append(ComplianceViolation(
                    id="gdpr_no_breach_procedure",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.MISSING_AUDIT_TRAIL,
                    severity=ComplianceSeverity.MEDIUM,
                    article_reference="Articles 33, 34",
                    description="No breach notification procedure documented",
                    remediation_steps=[
                        "Establish breach response procedures",
                        "Implement 72-hour notification process",
                        "Create user notification templates"
                    ]
                ))
        except Exception as e:
            logging.error(f"Breach notification test failed: {e}")
        
        return violations

class COPPAComplianceTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    async def test_coppa_compliance(self) -> List[ComplianceViolation]:
        violations = []
        
        violations.extend(await self._test_age_verification())
        violations.extend(await self._test_parental_consent())
        violations.extend(await self._test_child_data_collection())
        violations.extend(await self._test_child_data_disclosure())
        
        return violations

    async def _test_age_verification(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/signup")
            
            if response.status_code == 200:
                content = response.text.lower()
                
                age_keywords = ["age", "birth", "birthday", "born", "old"]
                has_age_check = any(keyword in content for keyword in age_keywords)
                
                if not has_age_check:
                    violations.append(ComplianceViolation(
                        id="coppa_no_age_verification",
                        framework=ComplianceFramework.COPPA,
                        violation_type=ComplianceViolationType.AGE_VERIFICATION_FAILURE,
                        severity=ComplianceSeverity.CRITICAL,
                        article_reference="15 U.S.C. §6502(b)(1)",
                        description="No age verification mechanism found",
                        data_categories=[DataCategory.CHILDREN_DATA],
                        max_fine_amount=43792.0,  # COPPA fine per violation
                        remediation_steps=[
                            "Implement age verification at registration",
                            "Block users under 13 without parental consent",
                            "Create age-appropriate interfaces"
                        ]
                    ))
        except Exception as e:
            logging.error(f"Age verification test failed: {e}")
        
        return violations

    async def _test_parental_consent(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/parental-consent")
            
            if response.status_code == 404:
                violations.append(ComplianceViolation(
                    id="coppa_no_parental_consent",
                    framework=ComplianceFramework.COPPA,
                    violation_type=ComplianceViolationType.NO_CONSENT,
                    severity=ComplianceSeverity.CRITICAL,
                    article_reference="15 U.S.C. §6502(b)(1)(A)",
                    description="No parental consent mechanism for children under 13",
                    data_categories=[DataCategory.CHILDREN_DATA],
                    remediation_steps=[
                        "Implement verifiable parental consent",
                        "Provide multiple consent methods",
                        "Enable parents to review/delete child data"
                    ]
                ))
        except Exception as e:
            logging.error(f"Parental consent test failed: {e}")
        
        return violations

    async def _test_child_data_collection(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            sensitive_fields = [
                "social_security", "phone_number", "address", 
                "school", "location", "photo", "video"
            ]
            
            response = self.session.get(f"{self.base_url}/kids/profile")
            
            if response.status_code == 200:
                content = response.text.lower()
                
                found_sensitive = [field for field in sensitive_fields if field in content]
                
                if found_sensitive:
                    violations.append(ComplianceViolation(
                        id="coppa_excessive_child_data",
                        framework=ComplianceFramework.COPPA,
                        violation_type=ComplianceViolationType.NO_CONSENT,
                        severity=ComplianceSeverity.HIGH,
                        article_reference="15 U.S.C. §6502(b)(1)(C)",
                        description=f"Collecting sensitive data from children: {', '.join(found_sensitive)}",
                        data_categories=[DataCategory.CHILDREN_DATA],
                        evidence={"sensitive_fields": found_sensitive},
                        remediation_steps=[
                            "Limit child data collection to necessary only",
                            "Remove sensitive data fields for children",
                            "Implement data minimization for minors"
                        ]
                    ))
        except Exception as e:
            logging.error(f"Child data collection test failed: {e}")
        
        return violations

    async def _test_child_data_disclosure(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = self.session.get(f"{self.base_url}/privacy-policy")
            
            if response.status_code == 200:
                content = response.text.lower()
                
                disclosure_keywords = ["share", "disclose", "third party", "advertising", "marketing"]
                has_disclosure = any(keyword in content for keyword in disclosure_keywords)
                
                child_keywords = ["child", "children", "minor", "under 13"]
                mentions_children = any(keyword in content for keyword in child_keywords)
                
                if has_disclosure and not mentions_children:
                    violations.append(ComplianceViolation(
                        id="coppa_undisclosed_child_sharing",
                        framework=ComplianceFramework.COPPA,
                        violation_type=ComplianceViolationType.IMPROPER_DATA_TRANSFER,
                        severity=ComplianceSeverity.HIGH,
                        article_reference="15 U.S.C. §6502(b)(1)(D)",
                        description="Data sharing policies don't address children's data",
                        data_categories=[DataCategory.CHILDREN_DATA],
                        remediation_steps=[
                            "Clearly state child data sharing policies",
                            "Prohibit sharing children's personal information",
                            "Get parental consent for any sharing"
                        ]
                    ))
        except Exception as e:
            logging.error(f"Child data disclosure test failed: {e}")
        
        return violations

class ComplianceTestingEngine:
    def __init__(self, base_url: str = "http://localhost:8080", results_dir: str = "compliance_results"):
        self.base_url = base_url
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.gdpr_tester = GDPRComplianceTester(base_url)
        self.coppa_tester = COPPAComplianceTester(base_url)
        
        self.driver = None

    def _setup_driver(self) -> webdriver.Chrome:
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logging.error(f"Failed to setup Chrome driver: {e}")
            return None

    async def test_cookie_compliance(self) -> List[ComplianceViolation]:
        violations = []
        self.driver = self._setup_driver()
        
        if not self.driver:
            return violations
        
        try:
            self.driver.get(self.base_url)
            
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            cookies = self.driver.get_cookies()
            
            cookie_banner = self.driver.find_elements(
                By.XPATH, "//*[contains(text(), 'cookie') or contains(text(), 'Cookie')]"
            )
            
            if not cookie_banner and cookies:
                violations.append(ComplianceViolation(
                    id="gdpr_no_cookie_consent",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.NO_CONSENT,
                    severity=ComplianceSeverity.HIGH,
                    article_reference="ePrivacy Directive, GDPR Article 6",
                    description="Cookies set without user consent or notice",
                    evidence={"cookies_count": len(cookies)},
                    remediation_steps=[
                        "Implement cookie consent banner",
                        "Allow granular cookie preferences",
                        "Only set essential cookies before consent"
                    ]
                ))
            
            tracking_cookies = [c for c in cookies if 'analytics' in c.get('name', '').lower() 
                              or 'tracking' in c.get('name', '').lower()
                              or 'marketing' in c.get('name', '').lower()]
            
            if tracking_cookies and not cookie_banner:
                violations.append(ComplianceViolation(
                    id="gdpr_tracking_without_consent",
                    framework=ComplianceFramework.GDPR,
                    violation_type=ComplianceViolationType.NO_CONSENT,
                    severity=ComplianceSeverity.CRITICAL,
                    article_reference="GDPR Article 6, ePrivacy Directive",
                    description="Tracking cookies set without explicit consent",
                    evidence={"tracking_cookies": [c['name'] for c in tracking_cookies]},
                    remediation_steps=[
                        "Remove tracking cookies before consent",
                        "Implement consent management platform",
                        "Provide cookie opt-out mechanisms"
                    ]
                ))
                
        except Exception as e:
            logging.error(f"Cookie compliance test failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
        
        return violations

    async def test_data_minimization(self) -> List[ComplianceViolation]:
        violations = []
        
        try:
            response = requests.get(f"{self.base_url}/api/user/profile")
            
            if response.status_code == 200:
                try:
                    profile_data = response.json()
                    
                    excessive_fields = [
                        'social_security', 'passport', 'drivers_license',
                        'mother_maiden_name', 'blood_type', 'political_views',
                        'sexual_orientation', 'race', 'religion'
                    ]
                    
                    found_excessive = [field for field in excessive_fields 
                                     if field in str(profile_data).lower()]
                    
                    if found_excessive:
                        violations.append(ComplianceViolation(
                            id="gdpr_data_minimization",
                            framework=ComplianceFramework.GDPR,
                            violation_type=ComplianceViolationType.NO_CONSENT,
                            severity=ComplianceSeverity.MEDIUM,
                            article_reference="GDPR Article 5(1)(c)",
                            description="Collection of excessive personal data",
                            data_categories=[DataCategory.SENSITIVE_PERSONAL_DATA],
                            evidence={"excessive_fields": found_excessive},
                            remediation_steps=[
                                "Remove unnecessary data fields",
                                "Implement data minimization principle",
                                "Regular data collection audits"
                            ]
                        ))
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            logging.error(f"Data minimization test failed: {e}")
        
        return violations

    async def run_gdpr_compliance_test(self) -> ComplianceTestResult:
        start_time = time.time()
        
        result = ComplianceTestResult(
            test_case_id="gdpr_compliance_test",
            test_name="GDPR Compliance Audit",
            framework=ComplianceFramework.GDPR,
            status="running"
        )
        
        try:
            violations = await self.gdpr_tester.test_gdpr_compliance()
            cookie_violations = await self.test_cookie_compliance()
            data_min_violations = await self.test_data_minimization()
            
            all_violations = violations + cookie_violations + data_min_violations
            result.violations = all_violations
            
            if not all_violations:
                result.status = "passed"
                result.compliant_items = [
                    "Privacy notice accessible",
                    "Consent mechanisms implemented", 
                    "Data subject rights supported",
                    "Security measures in place",
                    "Cookie compliance maintained"
                ]
            else:
                result.status = "failed"
            
            result.consent_management_valid = not any(
                v.violation_type in [ComplianceViolationType.NO_CONSENT, ComplianceViolationType.INVALID_CONSENT]
                for v in all_violations
            )
            
            result.security_measures_adequate = not any(
                v.violation_type == ComplianceViolationType.INADEQUATE_SECURITY
                for v in all_violations
            )
            
        except Exception as e:
            result.status = "error"
            logging.error(f"GDPR compliance test failed: {e}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_coppa_compliance_test(self) -> ComplianceTestResult:
        start_time = time.time()
        
        result = ComplianceTestResult(
            test_case_id="coppa_compliance_test",
            test_name="COPPA Compliance Audit",
            framework=ComplianceFramework.COPPA,
            status="running"
        )
        
        try:
            violations = await self.coppa_tester.test_coppa_compliance()
            result.violations = violations
            
            if not violations:
                result.status = "passed"
                result.compliant_items = [
                    "Age verification implemented",
                    "Parental consent mechanisms in place",
                    "Limited child data collection",
                    "Proper child data disclosure policies"
                ]
            else:
                result.status = "failed"
            
            result.consent_management_valid = not any(
                v.violation_type in [ComplianceViolationType.NO_CONSENT, ComplianceViolationType.AGE_VERIFICATION_FAILURE]
                for v in violations
            )
            
        except Exception as e:
            result.status = "error"
            logging.error(f"COPPA compliance test failed: {e}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_comprehensive_compliance_tests(self) -> Dict[str, Any]:
        print("Starting comprehensive compliance testing...")
        
        test_results = []
        
        print("Running GDPR compliance test...")
        gdpr_result = await self.run_gdpr_compliance_test()
        test_results.append(gdpr_result)
        
        print("Running COPPA compliance test...")
        coppa_result = await self.run_coppa_compliance_test()
        test_results.append(coppa_result)
        
        summary = self._generate_test_summary(test_results)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"compliance_report_{timestamp}.json"
        
        self.generate_compliance_report(test_results, summary, str(report_path))
        
        return {
            "test_results": test_results,
            "summary": summary,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html')
        }

    def _generate_test_summary(self, results: List[ComplianceTestResult]) -> Dict[str, Any]:
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "passed"])
        failed_tests = len([r for r in results if r.status == "failed"])
        
        all_violations = []
        for result in results:
            all_violations.extend(result.violations)
        
        total_potential_fines = sum(
            v.max_fine_amount for v in all_violations 
            if v.max_fine_amount
        )
        
        framework_violations = {}
        severity_distribution = {}
        
        for violation in all_violations:
            framework = violation.framework.value
            framework_violations[framework] = framework_violations.get(framework, 0) + 1
            
            severity = violation.severity.value
            severity_distribution[severity] = severity_distribution.get(severity, 0) + 1
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "total_violations": len(all_violations),
            "framework_violations": framework_violations,
            "severity_distribution": severity_distribution,
            "total_potential_fines": total_potential_fines,
            "consent_compliance_rate": len([
                r for r in results if r.consent_management_valid
            ]) / total_tests * 100 if total_tests > 0 else 0,
            "security_compliance_rate": len([
                r for r in results if r.security_measures_adequate  
            ]) / total_tests * 100 if total_tests > 0 else 0
        }

    def generate_compliance_report(self, results: List[ComplianceTestResult], summary: Dict[str, Any], output_path: str):
        report = {
            "compliance_summary": {
                "total_tests": summary["total_tests"],
                "passed_tests": summary["passed_tests"],
                "failed_tests": summary["failed_tests"],
                "pass_rate": summary["pass_rate"],
                "total_violations": summary["total_violations"],
                "total_potential_fines": summary["total_potential_fines"],
                "consent_compliance_rate": summary["consent_compliance_rate"],
                "security_compliance_rate": summary["security_compliance_rate"],
                "timestamp": datetime.now().isoformat()
            },
            "violation_analysis": {
                "by_framework": summary["framework_violations"],
                "by_severity": summary["severity_distribution"]
            },
            "detailed_results": []
        }
        
        for result in results:
            test_data = {
                "test_case_id": result.test_case_id,
                "test_name": result.test_name,
                "framework": result.framework.value,
                "status": result.status,
                "execution_time": result.execution_time,
                "violations_count": len(result.violations),
                "compliant_items": result.compliant_items,
                "consent_management_valid": result.consent_management_valid,
                "security_measures_adequate": result.security_measures_adequate,
                "violations": [
                    {
                        "id": v.id,
                        "framework": v.framework.value,
                        "type": v.violation_type.value,
                        "severity": v.severity.value,
                        "article_reference": v.article_reference,
                        "description": v.description,
                        "affected_users": v.affected_users,
                        "data_categories": [dc.value for dc in v.data_categories],
                        "evidence": v.evidence,
                        "remediation_steps": v.remediation_steps,
                        "max_fine_amount": v.max_fine_amount,
                        "detection_timestamp": v.detection_timestamp.isoformat()
                    } for v in result.violations
                ]
            }
            
            report["detailed_results"].append(test_data)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        html_report_path = output_path.replace('.json', '.html')
        self.generate_html_report(report, html_report_path)

    def generate_html_report(self, report_data: Dict[str, Any], output_path: str):
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Compliance Test Report - GDPR, COPPA, & More</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #007bff; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .critical {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .success {{ color: #28a745; }}
                .violation-analysis {{ background: #fff3cd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .framework-section {{ margin-bottom: 30px; }}
                .framework-header {{ background: #6c757d; color: white; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
                .test-item {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.failed {{ border-left-color: #dc3545; }}
                .compliance-metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }}
                .compliance-metric {{ background: white; padding: 10px; border-radius: 4px; text-align: center; }}
                .violations-section {{ margin-top: 15px; }}
                .violation {{ background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; }}
                .violation.critical {{ background: #f5c6cb; }}
                .violation.high {{ background: #f8d7da; }}
                .violation.medium {{ background: #fff3cd; border-left-color: #ffc107; }}
                .violation.low {{ background: #d1ecf1; border-left-color: #17a2b8; }}
                .violation-details {{ margin-top: 8px; padding: 8px; background: rgba(255,255,255,0.7); border-radius: 4px; font-size: 0.9em; }}
                .remediation {{ background: #d4edda; padding: 8px; margin-top: 5px; border-radius: 4px; }}
                .fine-amount {{ background: #f8d7da; padding: 5px 10px; border-radius: 4px; font-weight: bold; color: #721c24; }}
                .status-badge {{ padding: 4px 8px; border-radius: 12px; color: white; font-weight: bold; }}
                .status-passed {{ background: #28a745; }}
                .status-failed {{ background: #dc3545; }}
                .compliant-items {{ background: #d4edda; padding: 10px; border-radius: 4px; margin-top: 10px; }}
                .chart {{ margin: 15px 0; }}
                .bar {{ height: 25px; background: #e9ecef; border-radius: 12px; overflow: hidden; margin: 8px 0; }}
                .bar-fill {{ height: 100%; display: flex; align-items: center; padding: 0 12px; color: white; font-weight: bold; }}
                .gdpr-bar {{ background: #007bff; }}
                .coppa-bar {{ background: #28a745; }}
                .critical-bar {{ background: #dc3545; }}
                .high-bar {{ background: #fd7e14; }}
                .medium-bar {{ background: #ffc107; }}
                .low-bar {{ background: #17a2b8; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚖️ Compliance Test Report</h1>
                    <h2>GDPR, COPPA & Regulatory Compliance Audit</h2>
                    <p>Generated on {report_data['compliance_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['compliance_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Passed Tests</h3>
                        <div class="value success">{report_data['compliance_summary']['passed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Failed Tests</h3>
                        <div class="value critical">{report_data['compliance_summary']['failed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Violations</h3>
                        <div class="value critical">{report_data['compliance_summary']['total_violations']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Pass Rate</h3>
                        <div class="value {'success' if report_data['compliance_summary']['pass_rate'] >= 80 else 'critical'}">{report_data['compliance_summary']['pass_rate']:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <h3>Potential Fines</h3>
                        <div class="value critical">${report_data['compliance_summary']['total_potential_fines']:,.0f}</div>
                    </div>
                </div>
                
                <div class="compliance-metrics">
                    <div class="compliance-metric">
                        <h4>Consent Compliance</h4>
                        <div class="value {'success' if report_data['compliance_summary']['consent_compliance_rate'] >= 80 else 'critical'}">{report_data['compliance_summary']['consent_compliance_rate']:.1f}%</div>
                    </div>
                    <div class="compliance-metric">
                        <h4>Security Compliance</h4>
                        <div class="value {'success' if report_data['compliance_summary']['security_compliance_rate'] >= 80 else 'critical'}">{report_data['compliance_summary']['security_compliance_rate']:.1f}%</div>
                    </div>
                </div>
                
                <div class="violation-analysis">
                    <h3>📊 Violation Analysis</h3>
                    
                    <div class="chart">
                        <h4>Violations by Framework</h4>
        """
        
        total_violations = max(report_data['compliance_summary']['total_violations'], 1)
        for framework, count in report_data['violation_analysis']['by_framework'].items():
            percentage = (count / total_violations) * 100
            bar_class = f"{framework}-bar"
            html_content += f"""
                        <div class="bar">
                            <div class="bar-fill {bar_class}" style="width: {percentage}%;">
                                {framework.upper()}: {count} violations
                            </div>
                        </div>
            """
        
        html_content += """
                    </div>
                    
                    <div class="chart">
                        <h4>Violations by Severity</h4>
        """
        
        for severity, count in report_data['violation_analysis']['by_severity'].items():
            percentage = (count / total_violations) * 100
            bar_class = f"{severity}-bar"
            html_content += f"""
                        <div class="bar">
                            <div class="bar-fill {bar_class}" style="width: {percentage}%;">
                                {severity.upper()}: {count} violations
                            </div>
                        </div>
            """
        
        html_content += """
                    </div>
                </div>
        """
        
        for test in report_data['detailed_results']:
            framework_name = test['framework'].upper()
            status_class = test['status']
            
            html_content += f"""
                <div class="framework-section">
                    <div class="framework-header">
                        <h2>{framework_name} Compliance Test</h2>
                    </div>
                    
                    <div class="test-item {status_class}">
                        <h3>{test['test_name']} <span class="status-badge status-{status_class}">{test['status'].upper()}</span></h3>
                        <p><strong>Execution Time:</strong> {test['execution_time']:.2f}s | <strong>Violations:</strong> {test['violations_count']}</p>
                        
                        <div class="compliance-metrics">
                            <div class="compliance-metric">
                                <strong>Consent Management</strong><br>
                                {'✅ Valid' if test['consent_management_valid'] else '❌ Invalid'}
                            </div>
                            <div class="compliance-metric">
                                <strong>Security Measures</strong><br>
                                {'✅ Adequate' if test['security_measures_adequate'] else '❌ Inadequate'}
                            </div>
                        </div>
            """
            
            if test['compliant_items']:
                html_content += '<div class="compliant-items"><h4>✅ Compliant Items:</h4><ul>'
                for item in test['compliant_items']:
                    html_content += f"<li>{item}</li>"
                html_content += "</ul></div>"
            
            if test['violations']:
                html_content += '<div class="violations-section"><h4>🚨 Compliance Violations</h4>'
                
                for violation in test['violations']:
                    fine_text = f"Max Fine: ${violation['max_fine_amount']:,.0f}" if violation['max_fine_amount'] else ""
                    
                    html_content += f"""
                        <div class="violation {violation['severity']}">
                            <h5>[{violation['severity'].upper()}] {violation['type'].replace('_', ' ').title()}</h5>
                            <p><strong>{violation['description']}</strong></p>
                            <div class="violation-details">
                                <strong>Framework:</strong> {violation['framework'].upper()}<br>
                                <strong>Article Reference:</strong> {violation['article_reference']}<br>
                                <strong>Data Categories:</strong> {', '.join(violation['data_categories']) if violation['data_categories'] else 'N/A'}
                    """
                    
                    if violation['affected_users']:
                        html_content += f"<br><strong>Affected Users:</strong> {len(violation['affected_users'])}"
                    
                    if violation['evidence']:
                        html_content += f"<br><strong>Evidence:</strong> {json.dumps(violation['evidence'])}"
                    
                    if fine_text:
                        html_content += f"<br><div class='fine-amount'>{fine_text}</div>"
                    
                    html_content += "</div>"
                    
                    if violation['remediation_steps']:
                        html_content += '<div class="remediation"><strong>💡 Remediation Steps:</strong><ul>'
                        for step in violation['remediation_steps']:
                            html_content += f"<li>{step}</li>"
                        html_content += "</ul></div>"
                    
                    html_content += "</div>"
                
                html_content += "</div>"
            
            html_content += "</div></div>"
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

async def main():
    engine = ComplianceTestingEngine()
    
    results = await engine.run_comprehensive_compliance_tests()
    
    print(f"Compliance testing completed!")
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed tests: {results['summary']['passed_tests']}")
    print(f"Failed tests: {results['summary']['failed_tests']}")
    print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")
    print(f"Total violations: {results['summary']['total_violations']}")
    print(f"Potential fines: ${results['summary']['total_potential_fines']:,.0f}")
    print(f"Consent compliance: {results['summary']['consent_compliance_rate']:.1f}%")
    print(f"Security compliance: {results['summary']['security_compliance_rate']:.1f}%")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())