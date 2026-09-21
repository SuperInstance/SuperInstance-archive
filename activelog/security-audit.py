#!/usr/bin/env python3
"""
ActiveLog Security Audit Script
Comprehensive security assessment for the ActiveLog system
"""

import os
import json
import subprocess
import hashlib
import re
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import argparse

class SecurityAuditor:
    def __init__(self, base_path: str = "/home/activeloguser/activelog"):
        self.base_path = Path(base_path)
        self.results = {
            "audit_timestamp": datetime.utcnow().isoformat(),
            "base_path": str(base_path),
            "findings": [],
            "scores": {},
            "recommendations": []
        }
    
    def add_finding(self, category: str, severity: str, title: str, description: str, file_path: str = None, line_number: int = None):
        """Add a security finding"""
        finding = {
            "category": category,
            "severity": severity.upper(),
            "title": title,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if file_path:
            finding["file_path"] = str(file_path)
        if line_number:
            finding["line_number"] = line_number
            
        self.results["findings"].append(finding)
    
    def audit_file_permissions(self):
        """Audit file permissions for security issues"""
        print("🔍 Auditing file permissions...")
        
        sensitive_files = [
            ".env", ".env.local", ".env.production",
            "config.json", "secrets.json", "keys/*",
            "*.key", "*.pem", "*.crt"
        ]
        
        findings_count = 0
        
        for pattern in sensitive_files:
            for file_path in self.base_path.rglob(pattern):
                if file_path.is_file():
                    stat = file_path.stat()
                    mode = oct(stat.st_mode)[-3:]
                    
                    # Check for world-readable sensitive files
                    if mode[2] in ['4', '5', '6', '7']:
                        self.add_finding(
                            "file_permissions",
                            "medium",
                            f"World-readable sensitive file",
                            f"File {file_path} has world-readable permissions ({mode}). Sensitive files should not be readable by others.",
                            file_path
                        )
                        findings_count += 1
                    
                    # Check for world-writable files
                    if mode[2] in ['2', '3', '6', '7']:
                        self.add_finding(
                            "file_permissions",
                            "high",
                            f"World-writable sensitive file",
                            f"File {file_path} has world-writable permissions ({mode}). This is a serious security risk.",
                            file_path
                        )
                        findings_count += 1
        
        print(f"   Found {findings_count} file permission issues")
    
    def audit_hardcoded_secrets(self):
        """Look for hardcoded secrets in source code"""
        print("🔍 Scanning for hardcoded secrets...")
        
        secret_patterns = [
            (r'password\s*=\s*["\']([^"\']{8,})["\']', "Hardcoded password"),
            (r'api_key\s*=\s*["\']([^"\']{20,})["\']', "Hardcoded API key"),
            (r'secret\s*=\s*["\']([^"\']{16,})["\']', "Hardcoded secret"),
            (r'token\s*=\s*["\']([^"\']{20,})["\']', "Hardcoded token"),
            (r'DATABASE_URL\s*=\s*["\']([^"\']+)["\']', "Database URL with credentials"),
            (r'REDIS_URL\s*=\s*["\']([^"\']+://[^"\']+)["\']', "Redis URL with credentials"),
            (r'(sk-[a-zA-Z0-9]{48})', "OpenAI API key pattern"),
            (r'(ghp_[a-zA-Z0-9]{36})', "GitHub personal access token"),
            (r'(AKIA[0-9A-Z]{16})', "AWS access key"),
        ]
        
        findings_count = 0
        
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in secret_patterns:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            # Skip obvious test/example values
                            value = match.group(1) if match.groups() else match.group(0)
                            if any(test_val in value.lower() for test_val in ['test', 'example', 'demo', 'placeholder', 'your-', 'change-in-production']):
                                continue
                            
                            self.add_finding(
                                "hardcoded_secrets",
                                "high",
                                description,
                                f"Potential hardcoded secret found: {value[:20]}{'...' if len(value) > 20 else ''}",
                                file_path,
                                line_num
                            )
                            findings_count += 1
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} potential hardcoded secrets")
    
    def audit_sql_injection(self):
        """Look for potential SQL injection vulnerabilities"""
        print("🔍 Checking for SQL injection vulnerabilities...")
        
        sql_patterns = [
            (r'execute\(.*%.*\)', "String formatting in SQL execute"),
            (r'execute\(.*\+.*\)', "String concatenation in SQL execute"),
            (r'execute\(.*f["\'].*\{.*\}.*["\'].*\)', "f-string in SQL execute"),
            (r'query.*%.*', "String formatting in SQL query"),
            (r'SELECT.*\+.*', "String concatenation in SELECT"),
            (r'INSERT.*\+.*', "String concatenation in INSERT"),
            (r'UPDATE.*\+.*', "String concatenation in UPDATE"),
            (r'DELETE.*\+.*', "String concatenation in DELETE"),
        ]
        
        findings_count = 0
        
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, description in sql_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            self.add_finding(
                                "sql_injection",
                                "high",
                                "Potential SQL injection",
                                f"{description}: {line.strip()[:100]}",
                                file_path,
                                line_num
                            )
                            findings_count += 1
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} potential SQL injection issues")
    
    def audit_authentication(self):
        """Audit authentication mechanisms"""
        print("🔍 Auditing authentication systems...")
        
        findings_count = 0
        
        # Check for JWT secret strength
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # Check for weak JWT secrets
                jwt_patterns = [
                    r'JWT_SECRET_KEY\s*=\s*["\']([^"\']{1,16})["\']',
                    r'jwt.*secret\s*=\s*["\']([^"\']{1,16})["\']',
                    r'SECRET_KEY\s*=\s*["\']([^"\']{1,16})["\']'
                ]
                
                lines = content.split('\n')
                for line_num, line in enumerate(lines, 1):
                    for pattern in jwt_patterns:
                        match = re.search(pattern, line, re.IGNORECASE)
                        if match:
                            secret = match.group(1)
                            if len(secret) < 32:
                                self.add_finding(
                                    "authentication",
                                    "high",
                                    "Weak JWT secret",
                                    f"JWT secret is only {len(secret)} characters. Should be at least 32 characters for security.",
                                    file_path,
                                    line_num
                                )
                                findings_count += 1
                
                # Check for missing authentication decorators
                if 'FastAPI' in content or 'app = FastAPI' in content:
                    if '@app.post' in content or '@app.get' in content:
                        if 'Depends(' not in content and 'Security(' not in content:
                            self.add_finding(
                                "authentication",
                                "medium",
                                "Missing authentication",
                                "FastAPI app found without authentication dependencies. Consider adding authentication to sensitive endpoints.",
                                file_path
                            )
                            findings_count += 1
                            
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} authentication issues")
    
    def audit_cors_configuration(self):
        """Audit CORS configuration for security issues"""
        print("🔍 Auditing CORS configuration...")
        
        findings_count = 0
        
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    
                    # Check for permissive CORS
                    if 'allow_origins=["*"]' in line or "allow_origins=['*']" in line:
                        self.add_finding(
                            "cors",
                            "medium",
                            "Permissive CORS configuration",
                            "CORS is configured to allow all origins (*). This should be restricted to specific domains in production.",
                            file_path,
                            line_num
                        )
                        findings_count += 1
                    
                    if 'allow_credentials=True' in line and ('allow_origins=["*"]' in content or "allow_origins=['*']" in content):
                        self.add_finding(
                            "cors",
                            "high",
                            "Dangerous CORS configuration",
                            "CORS allows credentials with wildcard origins. This is a security vulnerability.",
                            file_path,
                            line_num
                        )
                        findings_count += 1
                        
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} CORS issues")
    
    def audit_database_security(self):
        """Audit database configurations and connections"""
        print("🔍 Auditing database security...")
        
        findings_count = 0
        
        # Check for database files with weak permissions
        for db_path in self.base_path.rglob("*.db"):
            if db_path.is_file():
                stat = db_path.stat()
                mode = oct(stat.st_mode)[-3:]
                
                if mode[1] in ['4', '5', '6', '7'] or mode[2] in ['4', '5', '6', '7']:
                    self.add_finding(
                        "database_security",
                        "high",
                        "Database file with weak permissions",
                        f"Database file {db_path} has permissions {mode}. Database files should be readable only by the application user.",
                        db_path
                    )
                    findings_count += 1
                
                # Check for default/weak database passwords in SQLite files
                try:
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()
                    
                    # Check for users table with default passwords
                    try:
                        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                        if cursor.fetchone():
                            cursor.execute("SELECT username, password FROM users LIMIT 5")
                            users = cursor.fetchall()
                            for username, password in users:
                                if password and len(password) < 8:
                                    self.add_finding(
                                        "database_security",
                                        "high",
                                        "Weak password in database",
                                        f"User '{username}' has a weak password (length < 8 characters)",
                                        db_path
                                    )
                                    findings_count += 1
                    except:
                        pass
                    
                    conn.close()
                except:
                    pass
        
        print(f"   Found {findings_count} database security issues")
    
    def audit_logging_security(self):
        """Audit logging for security issues"""
        print("🔍 Auditing logging security...")
        
        findings_count = 0
        
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Check for logging sensitive information
                    if 'log' in line.lower() and any(sensitive in line.lower() for sensitive in ['password', 'token', 'key', 'secret']):
                        if 'logger.info' in line or 'print(' in line or 'logging.info' in line:
                            self.add_finding(
                                "logging",
                                "medium",
                                "Potential sensitive data logging",
                                f"Line may be logging sensitive information: {line.strip()[:100]}",
                                file_path,
                                line_num
                            )
                            findings_count += 1
                            
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} logging security issues")
    
    def audit_dependency_security(self):
        """Audit dependencies for known vulnerabilities"""
        print("🔍 Auditing dependency security...")
        
        findings_count = 0
        
        # Check requirements.txt files
        for req_file in self.base_path.rglob("requirements.txt"):
            try:
                content = req_file.read_text()
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Check for unpinned versions
                    if '==' not in line and '>=' not in line and line:
                        self.add_finding(
                            "dependencies",
                            "low",
                            "Unpinned dependency version",
                            f"Dependency '{line}' should be pinned to a specific version for security and reproducibility",
                            req_file,
                            line_num
                        )
                        findings_count += 1
                        
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} dependency issues")
    
    def audit_network_security(self):
        """Audit network-related security configurations"""
        print("🔍 Auditing network security...")
        
        findings_count = 0
        
        for file_path in self.base_path.rglob("*.py"):
            if ".git" in str(file_path) or "__pycache__" in str(file_path):
                continue
                
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    # Check for services binding to all interfaces
                    if 'host="0.0.0.0"' in line or "host='0.0.0.0'" in line:
                        if 'uvicorn.run' in line or 'app.run' in line:
                            self.add_finding(
                                "network_security",
                                "medium",
                                "Service binding to all interfaces",
                                "Service is configured to bind to all network interfaces (0.0.0.0). Consider binding to localhost (127.0.0.1) if external access is not needed.",
                                file_path,
                                line_num
                            )
                            findings_count += 1
                    
                    # Check for HTTP URLs in production
                    http_pattern = r'http://(?!localhost|127\.0\.0\.1)'
                    if re.search(http_pattern, line):
                        self.add_finding(
                            "network_security",
                            "medium",
                            "HTTP URL in configuration",
                            f"HTTP URL found (should use HTTPS in production): {line.strip()[:100]}",
                            file_path,
                            line_num
                        )
                        findings_count += 1
                        
            except Exception as e:
                continue
        
        print(f"   Found {findings_count} network security issues")
    
    def calculate_security_score(self) -> Dict[str, Any]:
        """Calculate overall security score"""
        findings_by_severity = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        findings_by_category = {}
        
        for finding in self.results["findings"]:
            severity = finding["severity"]
            category = finding["category"]
            
            findings_by_severity[severity] += 1
            findings_by_category[category] = findings_by_category.get(category, 0) + 1
        
        # Calculate score (100 - deductions)
        score = 100
        score -= findings_by_severity["HIGH"] * 10     # -10 points per high severity issue
        score -= findings_by_severity["MEDIUM"] * 5   # -5 points per medium severity issue
        score -= findings_by_severity["LOW"] * 1      # -1 point per low severity issue
        
        score = max(0, score)  # Don't go below 0
        
        # Determine rating
        if score >= 90:
            rating = "EXCELLENT"
        elif score >= 80:
            rating = "GOOD"
        elif score >= 70:
            rating = "FAIR"
        elif score >= 60:
            rating = "POOR"
        else:
            rating = "CRITICAL"
        
        return {
            "overall_score": score,
            "rating": rating,
            "findings_by_severity": findings_by_severity,
            "findings_by_category": findings_by_category,
            "total_findings": sum(findings_by_severity.values())
        }
    
    def generate_recommendations(self):
        """Generate security recommendations based on findings"""
        recommendations = []
        
        # Category-specific recommendations
        categories = set(finding["category"] for finding in self.results["findings"])
        
        if "hardcoded_secrets" in categories:
            recommendations.append({
                "priority": "HIGH",
                "category": "Secret Management",
                "recommendation": "Implement proper secret management using environment variables or a secrets management system like HashiCorp Vault, AWS Secrets Manager, or Azure Key Vault."
            })
        
        if "authentication" in categories:
            recommendations.append({
                "priority": "HIGH", 
                "category": "Authentication",
                "recommendation": "Strengthen authentication by using longer JWT secrets (32+ characters), implementing proper password policies, and adding multi-factor authentication for admin accounts."
            })
        
        if "sql_injection" in categories:
            recommendations.append({
                "priority": "HIGH",
                "category": "Data Security",
                "recommendation": "Use parameterized queries or ORM methods to prevent SQL injection. Never use string concatenation or formatting for SQL queries."
            })
        
        if "cors" in categories:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Network Security", 
                "recommendation": "Configure CORS to allow only specific origins in production. Never use wildcard (*) origins with credentials enabled."
            })
        
        if "file_permissions" in categories:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "System Security",
                "recommendation": "Set appropriate file permissions (600 for sensitive files, 644 for regular files). Ensure sensitive files are not world-readable."
            })
        
        if "database_security" in categories:
            recommendations.append({
                "priority": "MEDIUM",
                "category": "Database Security",
                "recommendation": "Secure database files with proper permissions (600). Implement strong password policies and consider database encryption at rest."
            })
        
        # General recommendations
        recommendations.extend([
            {
                "priority": "MEDIUM",
                "category": "General Security",
                "recommendation": "Implement regular security audits and automated vulnerability scanning as part of your CI/CD pipeline."
            },
            {
                "priority": "LOW",
                "category": "Monitoring",
                "recommendation": "Set up security monitoring and alerting for suspicious activities, failed authentication attempts, and unauthorized access attempts."
            },
            {
                "priority": "LOW",
                "category": "Updates",
                "recommendation": "Keep all dependencies up to date and subscribe to security advisories for your technology stack."
            }
        ])
        
        return recommendations
    
    def run_audit(self) -> Dict[str, Any]:
        """Run complete security audit"""
        print("🔒 Starting ActiveLog Security Audit...")
        print(f"   Base path: {self.base_path}")
        print()
        
        # Run all audit checks
        self.audit_file_permissions()
        self.audit_hardcoded_secrets()
        self.audit_sql_injection()
        self.audit_authentication()
        self.audit_cors_configuration()
        self.audit_database_security()
        self.audit_logging_security()
        self.audit_dependency_security()
        self.audit_network_security()
        
        # Calculate scores and recommendations
        self.results["scores"] = self.calculate_security_score()
        self.results["recommendations"] = self.generate_recommendations()
        
        print()
        print("✅ Security audit completed!")
        
        return self.results

def main():
    parser = argparse.ArgumentParser(description="ActiveLog Security Audit Tool")
    parser.add_argument("--path", default="/home/activeloguser/activelog", help="Path to ActiveLog installation")
    parser.add_argument("--output", help="Output file for results (JSON format)")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    auditor = SecurityAuditor(args.path)
    results = auditor.run_audit()
    
    # Print summary
    scores = results["scores"]
    print(f"\n📊 SECURITY AUDIT SUMMARY")
    print(f"{'='*50}")
    print(f"Overall Score: {scores['overall_score']}/100 ({scores['rating']})")
    print(f"Total Issues: {scores['total_findings']}")
    print(f"  • High Severity: {scores['findings_by_severity']['HIGH']}")
    print(f"  • Medium Severity: {scores['findings_by_severity']['MEDIUM']}")
    print(f"  • Low Severity: {scores['findings_by_severity']['LOW']}")
    print()
    
    if args.verbose or scores["total_findings"] > 0:
        print(f"🔍 DETAILED FINDINGS")
        print(f"{'='*50}")
        for finding in results["findings"]:
            print(f"[{finding['severity']}] {finding['title']}")
            print(f"  Category: {finding['category']}")
            print(f"  Description: {finding['description']}")
            if finding.get('file_path'):
                print(f"  File: {finding['file_path']}")
                if finding.get('line_number'):
                    print(f"  Line: {finding['line_number']}")
            print()
    
    print(f"💡 RECOMMENDATIONS")
    print(f"{'='*50}")
    for rec in results["recommendations"]:
        print(f"[{rec['priority']}] {rec['category']}")
        print(f"  {rec['recommendation']}")
        print()
    
    # Save results if output file specified
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"💾 Results saved to: {args.output}")

if __name__ == "__main__":
    main()