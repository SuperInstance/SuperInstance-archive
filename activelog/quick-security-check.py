#!/usr/bin/env python3
"""
Quick Security Check for ActiveLog
Fast security assessment focusing on critical issues
"""

import os
import re
from pathlib import Path
from datetime import datetime

def check_secrets_in_files():
    """Quick check for obvious secrets"""
    issues = []
    secret_patterns = [
        (r'password\s*=\s*["\'](?!test|demo|placeholder|your-|change)([^"\']{8,})["\']', "Potential hardcoded password"),
        (r'api_key\s*=\s*["\'](?!test|demo|placeholder|your-|change)([^"\']{20,})["\']', "Potential API key"),
        (r'secret\s*=\s*["\'](?!test|demo|placeholder|your-|change)([^"\']{16,})["\']', "Potential secret"),
        (r'sk-[a-zA-Z0-9]{48}', "OpenAI API key pattern"),
    ]
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(errors='ignore')
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern, desc in secret_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(f"🔑 {desc} in {py_file}:{line_num}")
                        break
        except:
            continue
    
    return issues

def check_cors_issues():
    """Check for CORS security issues"""
    issues = []
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(errors='ignore')
            if 'allow_origins=["*"]' in content or "allow_origins=['*']" in content:
                issues.append(f"🌐 Permissive CORS (allow all origins) in {py_file}")
                
                if 'allow_credentials=True' in content:
                    issues.append(f"⚠️  DANGEROUS: CORS allows credentials with wildcard origins in {py_file}")
        except:
            continue
    
    return issues

def check_sql_injection():
    """Quick check for SQL injection risks"""
    issues = []
    dangerous_patterns = [
        r'execute\(.*\+.*\)',
        r'execute\(.*%.*\)',
        r'execute\(.*f["\'].*\{.*\}.*["\'].*\)',
    ]
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(errors='ignore')
            for line_num, line in enumerate(content.split('\n'), 1):
                for pattern in dangerous_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append(f"💉 Potential SQL injection in {py_file}:{line_num}")
                        break
        except:
            continue
    
    return issues

def check_file_permissions():
    """Check permissions on sensitive files"""
    issues = []
    sensitive_patterns = ["*.key", "*.pem", ".env*", "*secret*", "*password*"]
    
    for pattern in sensitive_patterns:
        for file_path in Path(".").rglob(pattern):
            if file_path.is_file():
                try:
                    mode = oct(file_path.stat().st_mode)[-3:]
                    if mode[2] in ['4', '5', '6', '7']:  # World readable
                        issues.append(f"📁 World-readable sensitive file: {file_path} ({mode})")
                    if mode[2] in ['2', '3', '6', '7']:  # World writable
                        issues.append(f"📝 World-writable sensitive file: {file_path} ({mode})")
                except:
                    continue
    
    return issues

def check_weak_jwt_secrets():
    """Check for weak JWT secrets"""
    issues = []
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(errors='ignore')
            
            # Look for JWT secret definitions
            jwt_patterns = [
                r'JWT_SECRET_KEY\s*=\s*["\']([^"\']+)["\']',
                r'SECRET_KEY\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in jwt_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for secret in matches:
                    if len(secret) < 32:
                        issues.append(f"🔐 Weak JWT secret in {py_file} (only {len(secret)} chars, should be 32+)")
        except:
            continue
    
    return issues

def check_network_binding():
    """Check for services binding to all interfaces"""
    issues = []
    
    for py_file in Path(".").rglob("*.py"):
        if "__pycache__" in str(py_file) or ".git" in str(py_file):
            continue
        
        try:
            content = py_file.read_text(errors='ignore')
            
            for line_num, line in enumerate(content.split('\n'), 1):
                if 'host="0.0.0.0"' in line and ('uvicorn.run' in line or 'app.run' in line):
                    issues.append(f"🌍 Service binding to all interfaces in {py_file}:{line_num}")
        except:
            continue
    
    return issues

def main():
    print("🔒 ActiveLog Quick Security Check")
    print("=" * 50)
    print()
    
    all_issues = []
    
    print("Checking for hardcoded secrets...")
    all_issues.extend(check_secrets_in_files())
    
    print("Checking CORS configuration...")
    all_issues.extend(check_cors_issues())
    
    print("Checking for SQL injection risks...")
    all_issues.extend(check_sql_injection())
    
    print("Checking file permissions...")
    all_issues.extend(check_file_permissions())
    
    print("Checking JWT secret strength...")
    all_issues.extend(check_weak_jwt_secrets())
    
    print("Checking network binding...")
    all_issues.extend(check_network_binding())
    
    print()
    print("🔍 SECURITY FINDINGS")
    print("=" * 50)
    
    if not all_issues:
        print("✅ No critical security issues found!")
        print("\n📊 SECURITY SCORE: 100/100 (EXCELLENT)")
    else:
        critical_issues = len([i for i in all_issues if "DANGEROUS" in i or "SQL injection" in i])
        medium_issues = len([i for i in all_issues if i not in [j for j in all_issues if "DANGEROUS" in j or "SQL injection" in j]])
        
        for issue in all_issues:
            print(issue)
        
        # Calculate score
        score = max(0, 100 - critical_issues * 20 - medium_issues * 5)
        
        if score >= 80:
            rating = "GOOD"
        elif score >= 60:
            rating = "FAIR" 
        elif score >= 40:
            rating = "POOR"
        else:
            rating = "CRITICAL"
        
        print(f"\n📊 SECURITY SCORE: {score}/100 ({rating})")
        print(f"Total Issues: {len(all_issues)} (Critical: {critical_issues}, Medium: {medium_issues})")
    
    print()
    print("💡 SECURITY RECOMMENDATIONS:")
    print("- Use environment variables for secrets instead of hardcoding")
    print("- Configure CORS to allow only specific origins in production")
    print("- Use parameterized queries to prevent SQL injection")
    print("- Set proper file permissions (600) for sensitive files")
    print("- Use strong JWT secrets (32+ characters)")
    print("- Consider binding services to localhost if external access isn't needed")
    print()
    print("For a comprehensive audit, run: python3 security-audit.py")

if __name__ == "__main__":
    main()