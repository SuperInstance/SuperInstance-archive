#!/usr/bin/env python3
"""
Advanced Security and Compliance Monitoring

Comprehensive security scanning, vulnerability detection, compliance checking,
and quantum-safe cryptography for platform builders.
"""

import asyncio
import threading
import subprocess
import os
import json
import time
import logging
import hashlib
import re
from typing import Dict, List, Any, Optional, Union, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import secrets
import base64

logger = logging.getLogger(__name__)


class SecurityLevel(Enum):
    """Security assessment levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ComplianceStandard(Enum):
    """Compliance standards"""
    ISO_27001 = "iso_27001"
    SOC2 = "soc2"
    GDPR = "gdpr"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    NIST = "nist"
    CIS = "cis"
    OWASP = "owasp"
    FDA_510K = "fda_510k"
    AUTOMOTIVE_SPICE = "automotive_spice"
    IEC_62304 = "iec_62304"  # Medical device software
    DO_178C = "do_178c"      # Aerospace software


class VulnerabilityType(Enum):
    """Vulnerability types"""
    CODE_INJECTION = "code_injection"
    XSS = "cross_site_scripting"
    SQL_INJECTION = "sql_injection"
    BUFFER_OVERFLOW = "buffer_overflow"
    USE_AFTER_FREE = "use_after_free"
    NULL_POINTER = "null_pointer_dereference"
    RACE_CONDITION = "race_condition"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CRYPTOGRAPHIC_WEAKNESS = "cryptographic_weakness"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    HARDCODED_SECRETS = "hardcoded_secrets"
    DEPENDENCY_VULNERABILITY = "dependency_vulnerability"
    CONFIGURATION_ERROR = "configuration_error"


@dataclass
class SecurityFinding:
    """Security finding information"""
    id: str
    type: VulnerabilityType
    severity: SecurityLevel
    title: str
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None
    cwe_id: Optional[str] = None  # Common Weakness Enumeration
    cve_id: Optional[str] = None  # Common Vulnerabilities and Exposures
    remediation: Optional[str] = None
    false_positive: bool = False
    suppressed: bool = False
    created_at: float = field(default_factory=time.time)
    
    @property
    def risk_score(self) -> int:
        """Calculate risk score based on severity"""
        scores = {
            SecurityLevel.CRITICAL: 10,
            SecurityLevel.HIGH: 8,
            SecurityLevel.MEDIUM: 5,
            SecurityLevel.LOW: 3,
            SecurityLevel.INFO: 1
        }
        return scores.get(self.severity, 0)


@dataclass
class ComplianceResult:
    """Compliance check result"""
    standard: ComplianceStandard
    requirement_id: str
    title: str
    status: str  # "pass", "fail", "warning", "not_applicable"
    description: str
    evidence: List[str] = field(default_factory=list)
    remediation_steps: List[str] = field(default_factory=list)
    automated_fix_available: bool = False
    last_checked: float = field(default_factory=time.time)


@dataclass
class CryptographicAnalysis:
    """Cryptographic security analysis"""
    algorithm: str
    key_size: int
    quantum_safe: bool
    deprecation_status: str
    recommendations: List[str] = field(default_factory=list)
    post_quantum_alternatives: List[str] = field(default_factory=list)


class StaticAnalyzer:
    """Advanced static code analysis"""
    
    def __init__(self):
        self.vulnerability_patterns = self._load_vulnerability_patterns()
        self.secret_patterns = self._load_secret_patterns()
        
    def _load_vulnerability_patterns(self) -> Dict[VulnerabilityType, List[Dict[str, Any]]]:
        """Load vulnerability detection patterns"""
        return {
            VulnerabilityType.BUFFER_OVERFLOW: [
                {"pattern": r"strcpy\s*\(", "description": "Unsafe strcpy usage"},
                {"pattern": r"sprintf\s*\(", "description": "Unsafe sprintf usage"},
                {"pattern": r"gets\s*\(", "description": "Unsafe gets usage"}
            ],
            VulnerabilityType.SQL_INJECTION: [
                {"pattern": r"SELECT.*\+.*['\"]", "description": "Potential SQL injection"},
                {"pattern": r"INSERT.*\+.*['\"]", "description": "Potential SQL injection"},
                {"pattern": r"UPDATE.*\+.*['\"]", "description": "Potential SQL injection"}
            ],
            VulnerabilityType.CODE_INJECTION: [
                {"pattern": r"eval\s*\(", "description": "Dangerous eval usage"},
                {"pattern": r"exec\s*\(", "description": "Dangerous exec usage"},
                {"pattern": r"system\s*\(.*\+", "description": "Command injection risk"}
            ],
            VulnerabilityType.CRYPTOGRAPHIC_WEAKNESS: [
                {"pattern": r"MD5|md5", "description": "Weak hash algorithm MD5"},
                {"pattern": r"SHA1|sha1", "description": "Weak hash algorithm SHA1"},
                {"pattern": r"DES|des", "description": "Weak encryption algorithm DES"},
                {"pattern": r"RC4|rc4", "description": "Weak encryption algorithm RC4"}
            ],
            VulnerabilityType.HARDCODED_SECRETS: [
                {"pattern": r"password\s*=\s*['\"][^'\"]{8,}", "description": "Hardcoded password"},
                {"pattern": r"api[_-]?key\s*=\s*['\"][^'\"]{16,}", "description": "Hardcoded API key"},
                {"pattern": r"secret\s*=\s*['\"][^'\"]{16,}", "description": "Hardcoded secret"}
            ]
        }
    
    def _load_secret_patterns(self) -> List[Dict[str, Any]]:
        """Load secret detection patterns"""
        return [
            {"name": "AWS Access Key", "pattern": r"AKIA[0-9A-Z]{16}"},
            {"name": "AWS Secret Key", "pattern": r"[0-9a-zA-Z/+]{40}"},
            {"name": "GitHub Token", "pattern": r"ghp_[0-9a-zA-Z]{36}"},
            {"name": "Slack Token", "pattern": r"xox[baprs]-[0-9a-zA-Z\-]{10,48}"},
            {"name": "JWT Token", "pattern": r"eyJ[0-9a-zA-Z_-]*\.eyJ[0-9a-zA-Z_-]*\.[0-9a-zA-Z_-]*"},
            {"name": "Private Key", "pattern": r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"},
            {"name": "Database URL", "pattern": r"(postgresql|mysql|mongodb)://[^/\s]+"},
            {"name": "Generic Secret", "pattern": r"['\"][0-9a-f]{32,}['\"]"}
        ]
    
    async def analyze_code(self, source_path: str) -> List[SecurityFinding]:
        """Perform static code analysis"""
        findings = []
        
        if not os.path.exists(source_path):
            return findings
        
        for root, dirs, files in os.walk(source_path):
            for file in files:
                if self._should_analyze_file(file):
                    file_path = os.path.join(root, file)
                    file_findings = await self._analyze_file(file_path)
                    findings.extend(file_findings)
        
        return findings
    
    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed"""
        analyzable_extensions = {
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',
            '.py', '.java', '.js', '.ts', '.php', '.rb',
            '.go', '.rs', '.cs', '.swift', '.kt', '.scala',
            '.sql', '.xml', '.json', '.yaml', '.yml'
        }
        
        _, ext = os.path.splitext(filename)
        return ext.lower() in analyzable_extensions
    
    async def _analyze_file(self, file_path: str) -> List[SecurityFinding]:
        """Analyze individual file for security issues"""
        findings = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Check for vulnerability patterns
            for vuln_type, patterns in self.vulnerability_patterns.items():
                for pattern_info in patterns:
                    pattern = pattern_info["pattern"]
                    description = pattern_info["description"]
                    
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            finding = SecurityFinding(
                                id=f"vuln_{int(time.time())}_{line_num}",
                                type=vuln_type,
                                severity=self._calculate_severity(vuln_type),
                                title=description,
                                description=f"Potential security issue detected: {description}",
                                file_path=file_path,
                                line_number=line_num,
                                code_snippet=line.strip(),
                                remediation=self._get_remediation_advice(vuln_type)
                            )
                            findings.append(finding)
            
            # Check for hardcoded secrets
            secret_findings = await self._detect_secrets(file_path, content, lines)
            findings.extend(secret_findings)
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
        
        return findings
    
    async def _detect_secrets(self, file_path: str, content: str, lines: List[str]) -> List[SecurityFinding]:
        """Detect hardcoded secrets in code"""
        findings = []
        
        for secret_pattern in self.secret_patterns:
            name = secret_pattern["name"]
            pattern = secret_pattern["pattern"]
            
            for line_num, line in enumerate(lines, 1):
                matches = re.finditer(pattern, line)
                for match in matches:
                    # Skip if it looks like a comment or documentation
                    if any(marker in line for marker in ['#', '//', '/*', '<!--', '"""', "'''"]):
                        continue
                    
                    finding = SecurityFinding(
                        id=f"secret_{int(time.time())}_{line_num}",
                        type=VulnerabilityType.HARDCODED_SECRETS,
                        severity=SecurityLevel.HIGH,
                        title=f"Hardcoded {name} detected",
                        description=f"Potential {name} found in source code",
                        file_path=file_path,
                        line_number=line_num,
                        code_snippet=line.strip(),
                        remediation="Move secrets to environment variables or secure configuration"
                    )
                    findings.append(finding)
        
        return findings
    
    def _calculate_severity(self, vuln_type: VulnerabilityType) -> SecurityLevel:
        """Calculate severity based on vulnerability type"""
        severity_map = {
            VulnerabilityType.BUFFER_OVERFLOW: SecurityLevel.CRITICAL,
            VulnerabilityType.CODE_INJECTION: SecurityLevel.CRITICAL,
            VulnerabilityType.SQL_INJECTION: SecurityLevel.CRITICAL,
            VulnerabilityType.PRIVILEGE_ESCALATION: SecurityLevel.CRITICAL,
            VulnerabilityType.USE_AFTER_FREE: SecurityLevel.HIGH,
            VulnerabilityType.RACE_CONDITION: SecurityLevel.HIGH,
            VulnerabilityType.CRYPTOGRAPHIC_WEAKNESS: SecurityLevel.HIGH,
            VulnerabilityType.HARDCODED_SECRETS: SecurityLevel.HIGH,
            VulnerabilityType.XSS: SecurityLevel.MEDIUM,
            VulnerabilityType.NULL_POINTER: SecurityLevel.MEDIUM,
            VulnerabilityType.CONFIGURATION_ERROR: SecurityLevel.MEDIUM,
            VulnerabilityType.DEPENDENCY_VULNERABILITY: SecurityLevel.MEDIUM,
            VulnerabilityType.INSECURE_DESERIALIZATION: SecurityLevel.LOW
        }
        
        return severity_map.get(vuln_type, SecurityLevel.INFO)
    
    def _get_remediation_advice(self, vuln_type: VulnerabilityType) -> str:
        """Get remediation advice for vulnerability type"""
        advice_map = {
            VulnerabilityType.BUFFER_OVERFLOW: "Use safe string functions like strncpy, snprintf, or memory-safe languages",
            VulnerabilityType.SQL_INJECTION: "Use parameterized queries or prepared statements",
            VulnerabilityType.CODE_INJECTION: "Avoid dynamic code execution, validate and sanitize inputs",
            VulnerabilityType.CRYPTOGRAPHIC_WEAKNESS: "Use modern cryptographic algorithms (AES-256, SHA-256+)",
            VulnerabilityType.HARDCODED_SECRETS: "Store secrets in environment variables or secure key management systems",
            VulnerabilityType.XSS: "Encode output and validate input data",
            VulnerabilityType.PRIVILEGE_ESCALATION: "Implement proper access controls and principle of least privilege"
        }
        
        return advice_map.get(vuln_type, "Review code for security best practices")


class DependencyScanner:
    """Dependency vulnerability scanner"""
    
    def __init__(self):
        self.vulnerability_db = {}  # Would load from CVE database
    
    async def scan_dependencies(self, project_path: str) -> List[SecurityFinding]:
        """Scan project dependencies for vulnerabilities"""
        findings = []
        
        # Scan different dependency files
        dependency_files = [
            ("requirements.txt", self._scan_python_deps),
            ("package.json", self._scan_node_deps),
            ("Cargo.toml", self._scan_rust_deps),
            ("go.mod", self._scan_go_deps),
            ("pom.xml", self._scan_java_deps),
            ("Gemfile", self._scan_ruby_deps)
        ]
        
        for dep_file, scanner_func in dependency_files:
            dep_path = os.path.join(project_path, dep_file)
            if os.path.exists(dep_path):
                dep_findings = await scanner_func(dep_path)
                findings.extend(dep_findings)
        
        return findings
    
    async def _scan_python_deps(self, requirements_path: str) -> List[SecurityFinding]:
        """Scan Python dependencies"""
        findings = []
        
        try:
            # Use safety to check for known vulnerabilities
            cmd = ["safety", "check", "-r", requirements_path, "--json"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                data = json.loads(stdout.decode())
                for vuln in data:
                    finding = SecurityFinding(
                        id=f"dep_vuln_{vuln.get('id', 'unknown')}",
                        type=VulnerabilityType.DEPENDENCY_VULNERABILITY,
                        severity=SecurityLevel.HIGH,
                        title=f"Vulnerable dependency: {vuln.get('package')}",
                        description=vuln.get('advisory', 'No description available'),
                        cve_id=vuln.get('cve'),
                        remediation=f"Update {vuln.get('package')} to version {vuln.get('safe_version', 'latest')}"
                    )
                    findings.append(finding)
                    
        except FileNotFoundError:
            logger.info("Safety tool not found, skipping Python dependency scan")
        except Exception as e:
            logger.error(f"Error scanning Python dependencies: {e}")
        
        return findings
    
    async def _scan_node_deps(self, package_path: str) -> List[SecurityFinding]:
        """Scan Node.js dependencies"""
        findings = []
        
        try:
            # Use npm audit
            project_dir = os.path.dirname(package_path)
            cmd = ["npm", "audit", "--json"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                data = json.loads(stdout.decode())
                vulnerabilities = data.get("vulnerabilities", {})
                
                for package, vuln_data in vulnerabilities.items():
                    severity = vuln_data.get("severity", "unknown")
                    security_level = self._map_npm_severity(severity)
                    
                    finding = SecurityFinding(
                        id=f"npm_vuln_{package}_{int(time.time())}",
                        type=VulnerabilityType.DEPENDENCY_VULNERABILITY,
                        severity=security_level,
                        title=f"Vulnerable Node.js dependency: {package}",
                        description=vuln_data.get("title", "No description available"),
                        remediation=f"Update {package} to a secure version"
                    )
                    findings.append(finding)
                    
        except FileNotFoundError:
            logger.info("npm not found, skipping Node.js dependency scan")
        except Exception as e:
            logger.error(f"Error scanning Node.js dependencies: {e}")
        
        return findings
    
    def _map_npm_severity(self, npm_severity: str) -> SecurityLevel:
        """Map npm severity to SecurityLevel"""
        mapping = {
            "critical": SecurityLevel.CRITICAL,
            "high": SecurityLevel.HIGH,
            "moderate": SecurityLevel.MEDIUM,
            "low": SecurityLevel.LOW,
            "info": SecurityLevel.INFO
        }
        return mapping.get(npm_severity.lower(), SecurityLevel.MEDIUM)
    
    async def _scan_rust_deps(self, cargo_path: str) -> List[SecurityFinding]:
        """Scan Rust dependencies"""
        findings = []
        
        try:
            project_dir = os.path.dirname(cargo_path)
            cmd = ["cargo", "audit", "--json"]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=project_dir
            )
            stdout, stderr = await process.communicate()
            
            if stdout:
                data = json.loads(stdout.decode())
                vulnerabilities = data.get("vulnerabilities", {})
                
                for vuln_id, vuln_data in vulnerabilities.items():
                    finding = SecurityFinding(
                        id=f"rust_vuln_{vuln_id}",
                        type=VulnerabilityType.DEPENDENCY_VULNERABILITY,
                        severity=SecurityLevel.HIGH,
                        title=f"Vulnerable Rust dependency: {vuln_data.get('package', 'unknown')}",
                        description=vuln_data.get("title", "No description available"),
                        remediation="Update to a secure version of the dependency"
                    )
                    findings.append(finding)
                    
        except FileNotFoundError:
            logger.info("cargo-audit not found, skipping Rust dependency scan")
        except Exception as e:
            logger.error(f"Error scanning Rust dependencies: {e}")
        
        return findings
    
    async def _scan_go_deps(self, go_mod_path: str) -> List[SecurityFinding]:
        """Scan Go dependencies"""
        # Placeholder - would use govulncheck or similar
        return []
    
    async def _scan_java_deps(self, pom_path: str) -> List[SecurityFinding]:
        """Scan Java dependencies"""
        # Placeholder - would use OWASP dependency check
        return []
    
    async def _scan_ruby_deps(self, gemfile_path: str) -> List[SecurityFinding]:
        """Scan Ruby dependencies"""
        # Placeholder - would use bundler-audit
        return []


class ComplianceChecker:
    """Compliance standards checker"""
    
    def __init__(self):
        self.compliance_rules = self._load_compliance_rules()
    
    def _load_compliance_rules(self) -> Dict[ComplianceStandard, List[Dict[str, Any]]]:
        """Load compliance rules and checks"""
        return {
            ComplianceStandard.ISO_27001: [
                {
                    "id": "A.14.2.1",
                    "title": "Secure development policy",
                    "description": "Information security policy for system development",
                    "check": "policy_documented"
                },
                {
                    "id": "A.14.2.5",
                    "title": "Secure system engineering principles",
                    "description": "Secure coding practices implementation",
                    "check": "secure_coding_practices"
                }
            ],
            ComplianceStandard.OWASP: [
                {
                    "id": "ASVS-1.1.1",
                    "title": "Security Architecture",
                    "description": "Application security architecture documentation",
                    "check": "security_architecture"
                },
                {
                    "id": "ASVS-2.1.1",
                    "title": "Password Security",
                    "description": "Strong password requirements",
                    "check": "password_policy"
                }
            ],
            ComplianceStandard.PCI_DSS: [
                {
                    "id": "REQ-6.5.1",
                    "title": "Injection flaws",
                    "description": "Protection against injection attacks",
                    "check": "injection_protection"
                },
                {
                    "id": "REQ-6.5.3",
                    "title": "Insecure cryptographic storage",
                    "description": "Secure cryptographic storage",
                    "check": "cryptographic_storage"
                }
            ],
            ComplianceStandard.HIPAA: [
                {
                    "id": "164.312(a)(1)",
                    "title": "Access control",
                    "description": "Unique user identification and access controls",
                    "check": "access_control"
                },
                {
                    "id": "164.312(e)(1)",
                    "title": "Transmission security",
                    "description": "End-to-end encryption for data transmission",
                    "check": "transmission_encryption"
                }
            ]
        }
    
    async def check_compliance(self, project_path: str, standards: List[ComplianceStandard]) -> List[ComplianceResult]:
        """Check compliance against specified standards"""
        results = []
        
        for standard in standards:
            rules = self.compliance_rules.get(standard, [])
            
            for rule in rules:
                result = await self._check_rule(project_path, standard, rule)
                results.append(result)
        
        return results
    
    async def _check_rule(self, project_path: str, standard: ComplianceStandard, 
                         rule: Dict[str, Any]) -> ComplianceResult:
        """Check individual compliance rule"""
        check_type = rule["check"]
        
        # Perform specific check based on rule type
        if check_type == "secure_coding_practices":
            status = await self._check_secure_coding(project_path)
        elif check_type == "injection_protection":
            status = await self._check_injection_protection(project_path)
        elif check_type == "cryptographic_storage":
            status = await self._check_cryptographic_storage(project_path)
        elif check_type == "access_control":
            status = await self._check_access_control(project_path)
        else:
            status = "not_applicable"
        
        return ComplianceResult(
            standard=standard,
            requirement_id=rule["id"],
            title=rule["title"],
            status=status,
            description=rule["description"],
            remediation_steps=self._get_remediation_steps(check_type, status)
        )
    
    async def _check_secure_coding(self, project_path: str) -> str:
        """Check for secure coding practices"""
        # Look for security-related files and configurations
        security_files = [
            ".security.yml",
            "SECURITY.md",
            ".bandit",
            ".semgrep.yml"
        ]
        
        for sec_file in security_files:
            if os.path.exists(os.path.join(project_path, sec_file)):
                return "pass"
        
        return "fail"
    
    async def _check_injection_protection(self, project_path: str) -> str:
        """Check for injection attack protection"""
        # This would analyze code for proper input validation
        # For now, return a placeholder
        return "warning"
    
    async def _check_cryptographic_storage(self, project_path: str) -> str:
        """Check cryptographic storage practices"""
        # This would analyze encryption usage
        return "warning"
    
    async def _check_access_control(self, project_path: str) -> str:
        """Check access control implementation"""
        # This would check for authentication/authorization code
        return "warning"
    
    def _get_remediation_steps(self, check_type: str, status: str) -> List[str]:
        """Get remediation steps for failed checks"""
        if status == "pass":
            return []
        
        remediation_map = {
            "secure_coding_practices": [
                "Create a SECURITY.md file documenting security practices",
                "Implement automated security scanning in CI/CD",
                "Establish secure code review processes"
            ],
            "injection_protection": [
                "Implement input validation and sanitization",
                "Use parameterized queries for database access",
                "Enable Content Security Policy (CSP) headers"
            ],
            "cryptographic_storage": [
                "Use strong encryption algorithms (AES-256)",
                "Implement proper key management",
                "Encrypt sensitive data at rest and in transit"
            ],
            "access_control": [
                "Implement multi-factor authentication",
                "Use role-based access control (RBAC)",
                "Log and monitor access attempts"
            ]
        }
        
        return remediation_map.get(check_type, ["Review implementation for compliance requirements"])


class CryptographyAnalyzer:
    """Quantum-safe cryptography analyzer"""
    
    def __init__(self):
        self.deprecated_algorithms = {
            "MD5": {"deprecated": True, "reason": "Cryptographically broken"},
            "SHA1": {"deprecated": True, "reason": "Collision vulnerabilities"},
            "DES": {"deprecated": True, "reason": "Key size too small"},
            "3DES": {"deprecated": True, "reason": "Vulnerable to Sweet32 attack"},
            "RC4": {"deprecated": True, "reason": "Biased keystream"},
            "RSA-1024": {"deprecated": True, "reason": "Key size insufficient"}
        }
        
        self.quantum_safe_algorithms = {
            "CRYSTALS-Kyber": "Post-quantum key encapsulation",
            "CRYSTALS-Dilithium": "Post-quantum digital signatures",
            "FALCON": "Post-quantum digital signatures",
            "SPHINCS+": "Post-quantum digital signatures",
            "NTRU": "Post-quantum encryption",
            "SABER": "Post-quantum key exchange"
        }
    
    async def analyze_cryptography(self, project_path: str) -> List[CryptographicAnalysis]:
        """Analyze cryptographic implementations"""
        analyses = []
        
        crypto_patterns = [
            {"algorithm": "AES", "pattern": r"AES[_-]?(128|192|256)", "quantum_safe": False},
            {"algorithm": "RSA", "pattern": r"RSA[_-]?(\d+)", "quantum_safe": False},
            {"algorithm": "ECDSA", "pattern": r"ECDSA", "quantum_safe": False},
            {"algorithm": "SHA-256", "pattern": r"SHA[_-]?256", "quantum_safe": True},
            {"algorithm": "SHA-3", "pattern": r"SHA[_-]?3", "quantum_safe": True},
            {"algorithm": "ChaCha20", "pattern": r"ChaCha20", "quantum_safe": False},
            {"algorithm": "Kyber", "pattern": r"Kyber", "quantum_safe": True},
            {"algorithm": "Dilithium", "pattern": r"Dilithium", "quantum_safe": True}
        ]
        
        for root, dirs, files in os.walk(project_path):
            for file in files:
                if file.endswith(('.py', '.java', '.cpp', '.c', '.js', '.ts')):
                    file_path = os.path.join(root, file)
                    file_analyses = await self._analyze_crypto_in_file(file_path, crypto_patterns)
                    analyses.extend(file_analyses)
        
        return analyses
    
    async def _analyze_crypto_in_file(self, file_path: str, patterns: List[Dict[str, Any]]) -> List[CryptographicAnalysis]:
        """Analyze cryptographic usage in a single file"""
        analyses = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for pattern_info in patterns:
                algorithm = pattern_info["algorithm"]
                pattern = pattern_info["pattern"]
                quantum_safe = pattern_info["quantum_safe"]
                
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    key_size = 0
                    if match.groups():
                        try:
                            key_size = int(match.group(1))
                        except (ValueError, IndexError):
                            pass
                    
                    analysis = CryptographicAnalysis(
                        algorithm=algorithm,
                        key_size=key_size,
                        quantum_safe=quantum_safe,
                        deprecation_status=self._get_deprecation_status(algorithm, key_size),
                        recommendations=self._get_crypto_recommendations(algorithm, key_size, quantum_safe),
                        post_quantum_alternatives=self._get_post_quantum_alternatives(algorithm)
                    )
                    analyses.append(analysis)
                    
        except Exception as e:
            logger.error(f"Error analyzing cryptography in {file_path}: {e}")
        
        return analyses
    
    def _get_deprecation_status(self, algorithm: str, key_size: int) -> str:
        """Get deprecation status of cryptographic algorithm"""
        algo_key = f"{algorithm}-{key_size}" if key_size > 0 else algorithm
        
        if algo_key in self.deprecated_algorithms:
            return "deprecated"
        elif algorithm == "RSA" and key_size < 2048:
            return "deprecated"
        elif algorithm == "ECDSA" and key_size < 256:
            return "deprecated"
        else:
            return "active"
    
    def _get_crypto_recommendations(self, algorithm: str, key_size: int, quantum_safe: bool) -> List[str]:
        """Get recommendations for cryptographic usage"""
        recommendations = []
        
        if not quantum_safe:
            recommendations.append("Consider migration to quantum-safe alternatives")
        
        if algorithm == "AES" and key_size < 256:
            recommendations.append("Use AES-256 for better security")
        
        if algorithm == "RSA" and key_size < 4096:
            recommendations.append("Use RSA-4096 or higher for future-proofing")
        
        if algorithm in ["MD5", "SHA1"]:
            recommendations.append("Migrate to SHA-256 or SHA-3")
        
        return recommendations
    
    def _get_post_quantum_alternatives(self, algorithm: str) -> List[str]:
        """Get post-quantum alternatives for algorithm"""
        alternatives_map = {
            "RSA": ["CRYSTALS-Dilithium", "FALCON", "SPHINCS+"],
            "ECDSA": ["CRYSTALS-Dilithium", "FALCON"],
            "DH": ["CRYSTALS-Kyber", "NTRU", "SABER"],
            "ECDH": ["CRYSTALS-Kyber", "NTRU"]
        }
        
        return alternatives_map.get(algorithm, [])


class SecurityComplianceManager:
    """Main security and compliance management system"""
    
    def __init__(self):
        self.static_analyzer = StaticAnalyzer()
        self.dependency_scanner = DependencyScanner()
        self.compliance_checker = ComplianceChecker()
        self.crypto_analyzer = CryptographyAnalyzer()
        
        self.security_reports: Dict[str, Dict[str, Any]] = {}
        self.compliance_callbacks: List[Callable] = []
        
        self._running = False
        self._lock = threading.Lock()
    
    async def start(self):
        """Start security and compliance monitoring"""
        self._running = True
        logger.info("Security and compliance monitoring started")
    
    async def stop(self):
        """Stop security and compliance monitoring"""
        self._running = False
        logger.info("Security and compliance monitoring stopped")
    
    async def perform_security_scan(self, build_id: str, project_path: str, 
                                  compliance_standards: List[ComplianceStandard] = None) -> str:
        """Perform comprehensive security scan"""
        scan_id = f"scan_{build_id}_{int(time.time())}"
        
        try:
            # Perform static analysis
            static_findings = await self.static_analyzer.analyze_code(project_path)
            
            # Scan dependencies
            dependency_findings = await self.dependency_scanner.scan_dependencies(project_path)
            
            # Check compliance
            compliance_results = []
            if compliance_standards:
                compliance_results = await self.compliance_checker.check_compliance(
                    project_path, compliance_standards
                )
            
            # Analyze cryptography
            crypto_analyses = await self.crypto_analyzer.analyze_cryptography(project_path)
            
            # Generate security report
            report = {
                "scan_id": scan_id,
                "build_id": build_id,
                "project_path": project_path,
                "scan_time": time.time(),
                "static_findings": [asdict(f) for f in static_findings],
                "dependency_findings": [asdict(f) for f in dependency_findings],
                "compliance_results": [asdict(r) for r in compliance_results],
                "crypto_analyses": [asdict(a) for a in crypto_analyses],
                "summary": self._generate_security_summary(
                    static_findings, dependency_findings, compliance_results, crypto_analyses
                )
            }
            
            with self._lock:
                self.security_reports[scan_id] = report
            
            # Notify callbacks
            for callback in self.compliance_callbacks:
                try:
                    await callback({
                        "event": "security_scan_completed",
                        "scan_id": scan_id,
                        "build_id": build_id,
                        "summary": report["summary"]
                    })
                except Exception as e:
                    logger.error(f"Security callback error: {e}")
            
            logger.info(f"Security scan completed: {scan_id}")
            return scan_id
            
        except Exception as e:
            logger.error(f"Security scan failed: {e}")
            raise
    
    def _generate_security_summary(self, static_findings: List[SecurityFinding],
                                 dependency_findings: List[SecurityFinding],
                                 compliance_results: List[ComplianceResult],
                                 crypto_analyses: List[CryptographicAnalysis]) -> Dict[str, Any]:
        """Generate security scan summary"""
        all_findings = static_findings + dependency_findings
        
        # Count findings by severity
        severity_counts = {level.value: 0 for level in SecurityLevel}
        for finding in all_findings:
            severity_counts[finding.severity.value] += 1
        
        # Calculate risk score
        total_risk = sum(finding.risk_score for finding in all_findings)
        
        # Compliance summary
        compliance_summary = {
            "total_checks": len(compliance_results),
            "passed": len([r for r in compliance_results if r.status == "pass"]),
            "failed": len([r for r in compliance_results if r.status == "fail"]),
            "warnings": len([r for r in compliance_results if r.status == "warning"])
        }
        
        # Crypto summary
        crypto_summary = {
            "total_algorithms": len(crypto_analyses),
            "quantum_safe": len([a for a in crypto_analyses if a.quantum_safe]),
            "deprecated": len([a for a in crypto_analyses if a.deprecation_status == "deprecated"])
        }
        
        return {
            "total_findings": len(all_findings),
            "severity_breakdown": severity_counts,
            "total_risk_score": total_risk,
            "risk_level": self._calculate_risk_level(total_risk, len(all_findings)),
            "compliance_summary": compliance_summary,
            "cryptography_summary": crypto_summary,
            "recommendations": self._generate_top_recommendations(all_findings, compliance_results)
        }
    
    def _calculate_risk_level(self, total_risk: int, finding_count: int) -> str:
        """Calculate overall risk level"""
        if finding_count == 0:
            return "low"
        
        avg_risk = total_risk / finding_count
        
        if avg_risk >= 8:
            return "critical"
        elif avg_risk >= 6:
            return "high"
        elif avg_risk >= 4:
            return "medium"
        else:
            return "low"
    
    def _generate_top_recommendations(self, findings: List[SecurityFinding],
                                    compliance_results: List[ComplianceResult]) -> List[str]:
        """Generate top security recommendations"""
        recommendations = []
        
        # Top vulnerability types
        vuln_types = {}
        for finding in findings:
            vuln_types[finding.type] = vuln_types.get(finding.type, 0) + 1
        
        # Sort by frequency
        top_vulns = sorted(vuln_types.items(), key=lambda x: x[1], reverse=True)[:3]
        
        for vuln_type, count in top_vulns:
            if vuln_type == VulnerabilityType.HARDCODED_SECRETS:
                recommendations.append("Implement secure secrets management")
            elif vuln_type == VulnerabilityType.CRYPTOGRAPHIC_WEAKNESS:
                recommendations.append("Upgrade to modern cryptographic algorithms")
            elif vuln_type == VulnerabilityType.DEPENDENCY_VULNERABILITY:
                recommendations.append("Update vulnerable dependencies")
        
        # Failed compliance checks
        failed_compliance = [r for r in compliance_results if r.status == "fail"]
        if failed_compliance:
            recommendations.append("Address critical compliance failures")
        
        return recommendations[:5]  # Top 5 recommendations
    
    async def get_security_report(self, scan_id: str) -> Optional[Dict[str, Any]]:
        """Get security scan report"""
        with self._lock:
            return self.security_reports.get(scan_id)
    
    async def get_build_security_status(self, build_id: str) -> Optional[Dict[str, Any]]:
        """Get security status for a build"""
        with self._lock:
            for report in self.security_reports.values():
                if report["build_id"] == build_id:
                    return {
                        "scan_id": report["scan_id"],
                        "risk_level": report["summary"]["risk_level"],
                        "total_findings": report["summary"]["total_findings"],
                        "compliance_passed": report["summary"]["compliance_summary"]["passed"],
                        "quantum_safe_crypto": report["summary"]["cryptography_summary"]["quantum_safe"]
                    }
        
        return None
    
    def add_compliance_callback(self, callback: Callable):
        """Add compliance callback"""
        self.compliance_callbacks.append(callback)
    
    def is_healthy(self) -> bool:
        """Check if security system is healthy"""
        return self._running
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get security statistics"""
        with self._lock:
            total_scans = len(self.security_reports)
            
            if total_scans == 0:
                return {"total_scans": 0}
            
            # Aggregate statistics
            total_findings = sum(report["summary"]["total_findings"] for report in self.security_reports.values())
            high_risk_scans = len([r for r in self.security_reports.values() 
                                 if r["summary"]["risk_level"] in ["high", "critical"]])
            
            return {
                "total_scans": total_scans,
                "total_findings": total_findings,
                "average_findings_per_scan": total_findings / total_scans,
                "high_risk_scans": high_risk_scans,
                "risk_percentage": (high_risk_scans / total_scans) * 100
            }


# Global security and compliance manager
security_compliance_manager = SecurityComplianceManager()