"""
Security Headers Audit Tool for ActiveLog
Analyzes HTTP security headers and provides recommendations for improving security posture.
"""

import requests
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
import json
from pathlib import Path
import time


class HeaderStatus(Enum):
    """Status of security header implementation."""
    MISSING = "missing"
    PRESENT = "present"
    MISCONFIGURED = "misconfigured"
    OPTIMAL = "optimal"


@dataclass
class HeaderResult:
    """Result of security header analysis."""
    name: str
    status: HeaderStatus
    value: Optional[str]
    score: int  # 0-100
    issues: List[str]
    recommendations: List[str]
    references: List[str]


class SecurityHeadersAuditor:
    """Audits security headers for web applications."""
    
    def __init__(self):
        # Define security headers and their optimal configurations
        self.security_headers = {
            'strict-transport-security': {
                'name': 'Strict-Transport-Security',
                'description': 'HSTS prevents downgrade attacks and cookie hijacking',
                'optimal_patterns': [
                    r'max-age=(\d+)',  # Should be at least 31536000 (1 year)
                    r'includeSubDomains',
                    r'preload'
                ],
                'min_max_age': 31536000,  # 1 year
                'score_weight': 15
            },
            'content-security-policy': {
                'name': 'Content-Security-Policy',
                'description': 'CSP prevents XSS and data injection attacks',
                'dangerous_values': [
                    r"'unsafe-inline'",
                    r"'unsafe-eval'",
                    r'\*',  # wildcard
                    r'data:',
                    r'javascript:'
                ],
                'recommended_directives': [
                    'default-src', 'script-src', 'style-src', 'img-src',
                    'connect-src', 'font-src', 'object-src', 'media-src',
                    'frame-src', 'frame-ancestors'
                ],
                'score_weight': 20
            },
            'x-frame-options': {
                'name': 'X-Frame-Options',
                'description': 'Prevents clickjacking attacks',
                'optimal_values': ['DENY', 'SAMEORIGIN'],
                'deprecated_note': 'Consider using CSP frame-ancestors instead',
                'score_weight': 10
            },
            'x-content-type-options': {
                'name': 'X-Content-Type-Options',
                'description': 'Prevents MIME-type sniffing',
                'optimal_values': ['nosniff'],
                'score_weight': 10
            },
            'x-xss-protection': {
                'name': 'X-XSS-Protection',
                'description': 'Legacy XSS protection (deprecated)',
                'optimal_values': ['1; mode=block', '0'],
                'deprecated_note': 'Consider using CSP instead',
                'score_weight': 5
            },
            'referrer-policy': {
                'name': 'Referrer-Policy',
                'description': 'Controls referrer information sent with requests',
                'recommended_values': [
                    'strict-origin-when-cross-origin',
                    'strict-origin',
                    'no-referrer'
                ],
                'score_weight': 8
            },
            'permissions-policy': {
                'name': 'Permissions-Policy',
                'description': 'Controls browser features and APIs',
                'recommended_features': [
                    'geolocation', 'microphone', 'camera', 'payment',
                    'usb', 'magnetometer', 'gyroscope', 'accelerometer'
                ],
                'score_weight': 12
            },
            'cross-origin-embedder-policy': {
                'name': 'Cross-Origin-Embedder-Policy',
                'description': 'Enables cross-origin isolation',
                'recommended_values': ['require-corp'],
                'score_weight': 8
            },
            'cross-origin-opener-policy': {
                'name': 'Cross-Origin-Opener-Policy',
                'description': 'Isolates browsing context',
                'recommended_values': ['same-origin', 'same-origin-allow-popups'],
                'score_weight': 8
            },
            'cross-origin-resource-policy': {
                'name': 'Cross-Origin-Resource-Policy',
                'description': 'Protects against cross-origin attacks',
                'recommended_values': ['same-origin', 'same-site', 'cross-origin'],
                'score_weight': 8
            }
        }
        
        # Additional security checks
        self.security_checks = {
            'server_disclosure': {
                'headers': ['server', 'x-powered-by', 'x-aspnet-version'],
                'description': 'Server software disclosure',
                'score_impact': -5
            },
            'cache_control': {
                'headers': ['cache-control', 'pragma', 'expires'],
                'description': 'Cache control for sensitive pages',
                'score_impact': 3
            }
        }
    
    def audit_url(self, url: str, follow_redirects: bool = True, 
                 custom_headers: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Audit security headers for a given URL.
        
        Args:
            url: The URL to audit
            follow_redirects: Whether to follow redirects
            custom_headers: Additional headers to send with request
            
        Returns:
            Audit results dictionary
        """
        result = {
            'url': url,
            'timestamp': time.time(),
            'headers_analyzed': {},
            'security_score': 0,
            'max_possible_score': 100,
            'grade': 'F',
            'critical_issues': [],
            'recommendations': [],
            'response_info': {}
        }
        
        try:
            # Make HTTP request
            headers = custom_headers or {}
            headers.update({
                'User-Agent': 'ActiveLog Security Headers Auditor 1.0'
            })
            
            response = requests.get(
                url, 
                headers=headers,
                allow_redirects=follow_redirects,
                timeout=10,
                verify=True
            )
            
            # Store response information
            result['response_info'] = {
                'status_code': response.status_code,
                'final_url': response.url,
                'response_time_ms': int(response.elapsed.total_seconds() * 1000),
                'content_type': response.headers.get('content-type', ''),
                'content_length': len(response.content),
                'redirect_chain': [r.url for r in response.history] if response.history else []
            }
            
            # Analyze headers
            self._analyze_security_headers(response.headers, result)
            
            # Calculate overall grade
            result['grade'] = self._calculate_grade(result['security_score'])
            
        except requests.exceptions.SSLError as e:
            result['error'] = f"SSL/TLS error: {str(e)}"
            result['critical_issues'].append("SSL/TLS configuration issues detected")
        except requests.exceptions.ConnectionError as e:
            result['error'] = f"Connection error: {str(e)}"
        except requests.exceptions.Timeout as e:
            result['error'] = f"Request timeout: {str(e)}"
        except Exception as e:
            result['error'] = f"Unexpected error: {str(e)}"
        
        return result
    
    def _analyze_security_headers(self, headers: Dict[str, str], result: Dict[str, Any]):
        """Analyze security headers and calculate scores."""
        total_score = 0
        max_score = 0
        
        # Convert headers to lowercase for case-insensitive lookup
        headers_lower = {k.lower(): v for k, v in headers.items()}
        
        # Analyze each security header
        for header_key, header_config in self.security_headers.items():
            header_result = self._analyze_header(
                header_key, 
                headers_lower.get(header_key),
                header_config
            )
            
            result['headers_analyzed'][header_key] = {
                'name': header_result.name,
                'status': header_result.status.value,
                'value': header_result.value,
                'score': header_result.score,
                'issues': header_result.issues,
                'recommendations': header_result.recommendations,
                'references': header_result.references
            }
            
            total_score += header_result.score
            max_score += header_config['score_weight']
            
            # Collect critical issues
            if header_result.status in [HeaderStatus.MISSING, HeaderStatus.MISCONFIGURED]:
                if header_config['score_weight'] >= 15:  # Critical headers
                    result['critical_issues'].extend(header_result.issues)
            
            # Collect recommendations
            result['recommendations'].extend(header_result.recommendations)
        
        # Additional security checks
        self._perform_additional_checks(headers_lower, result)
        
        # Calculate final score (0-100)
        result['security_score'] = int((total_score / max_score) * 100) if max_score > 0 else 0
        result['max_possible_score'] = max_score
    
    def _analyze_header(self, header_key: str, header_value: Optional[str], 
                       config: Dict[str, Any]) -> HeaderResult:
        """Analyze a specific security header."""
        result = HeaderResult(
            name=config['name'],
            status=HeaderStatus.MISSING,
            value=header_value,
            score=0,
            issues=[],
            recommendations=[],
            references=[]
        )
        
        if header_value is None:
            result.status = HeaderStatus.MISSING
            result.issues.append(f"{config['name']} header is missing")
            result.recommendations.append(f"Add {config['name']} header")
            return result
        
        result.status = HeaderStatus.PRESENT
        
        # Header-specific analysis
        if header_key == 'strict-transport-security':
            result = self._analyze_hsts(header_value, config, result)
        elif header_key == 'content-security-policy':
            result = self._analyze_csp(header_value, config, result)
        elif header_key == 'x-frame-options':
            result = self._analyze_frame_options(header_value, config, result)
        elif header_key == 'x-content-type-options':
            result = self._analyze_content_type_options(header_value, config, result)
        elif header_key == 'x-xss-protection':
            result = self._analyze_xss_protection(header_value, config, result)
        elif header_key == 'referrer-policy':
            result = self._analyze_referrer_policy(header_value, config, result)
        elif header_key == 'permissions-policy':
            result = self._analyze_permissions_policy(header_value, config, result)
        else:
            # Generic analysis for COOP, COEP, CORP
            result = self._analyze_generic_header(header_value, config, result)
        
        return result
    
    def _analyze_hsts(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze Strict-Transport-Security header."""
        value_lower = value.lower()
        
        # Check max-age
        max_age_match = re.search(r'max-age=(\d+)', value_lower)
        if not max_age_match:
            result.issues.append("HSTS missing max-age directive")
            result.score = 0
            return result
        
        max_age = int(max_age_match.group(1))
        min_age = config['min_max_age']
        
        if max_age < min_age:
            result.issues.append(f"HSTS max-age ({max_age}) is too short (minimum: {min_age})")
            result.score = config['score_weight'] // 3
        else:
            result.score = config['score_weight'] // 2
        
        # Check includeSubDomains
        if 'includesubdomains' in value_lower:
            result.score += config['score_weight'] // 4
        else:
            result.recommendations.append("Add 'includeSubDomains' to HSTS")
        
        # Check preload
        if 'preload' in value_lower:
            result.score += config['score_weight'] // 4
            result.status = HeaderStatus.OPTIMAL
        else:
            result.recommendations.append("Consider adding 'preload' to HSTS")
        
        return result
    
    def _analyze_csp(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze Content-Security-Policy header."""
        value_lower = value.lower()
        
        # Check for dangerous values
        dangerous_found = []
        for pattern in config['dangerous_values']:
            if re.search(pattern, value_lower):
                dangerous_found.append(pattern)
        
        if dangerous_found:
            result.issues.extend([f"Dangerous CSP directive: {d}" for d in dangerous_found])
            result.score = config['score_weight'] // 4
        else:
            result.score = config['score_weight'] // 2
        
        # Check for recommended directives
        present_directives = []
        for directive in config['recommended_directives']:
            if directive in value_lower:
                present_directives.append(directive)
        
        directive_score = (len(present_directives) / len(config['recommended_directives'])) * (config['score_weight'] // 2)
        result.score += int(directive_score)
        
        if len(present_directives) >= len(config['recommended_directives']) * 0.8:
            result.status = HeaderStatus.OPTIMAL
        elif dangerous_found:
            result.status = HeaderStatus.MISCONFIGURED
        
        # Specific recommendations
        if 'default-src' not in value_lower:
            result.recommendations.append("Add 'default-src' directive to CSP")
        if "'unsafe-inline'" in value_lower:
            result.recommendations.append("Remove 'unsafe-inline' from CSP")
        if "'unsafe-eval'" in value_lower:
            result.recommendations.append("Remove 'unsafe-eval' from CSP")
        
        return result
    
    def _analyze_frame_options(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze X-Frame-Options header."""
        value_upper = value.upper()
        
        if value_upper in config['optimal_values']:
            result.score = config['score_weight']
            result.status = HeaderStatus.OPTIMAL
        else:
            result.issues.append(f"Suboptimal X-Frame-Options value: {value}")
            result.score = config['score_weight'] // 2
        
        result.recommendations.append("Consider using CSP frame-ancestors directive instead")
        
        return result
    
    def _analyze_content_type_options(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze X-Content-Type-Options header."""
        if value.lower() in [v.lower() for v in config['optimal_values']]:
            result.score = config['score_weight']
            result.status = HeaderStatus.OPTIMAL
        else:
            result.issues.append(f"Invalid X-Content-Type-Options value: {value}")
            result.score = 0
        
        return result
    
    def _analyze_xss_protection(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze X-XSS-Protection header."""
        if value in config['optimal_values']:
            result.score = config['score_weight']
            result.status = HeaderStatus.OPTIMAL
        else:
            result.score = config['score_weight'] // 2
        
        result.recommendations.append("X-XSS-Protection is deprecated, use CSP instead")
        
        return result
    
    def _analyze_referrer_policy(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze Referrer-Policy header."""
        if value in config['recommended_values']:
            result.score = config['score_weight']
            result.status = HeaderStatus.OPTIMAL
        else:
            result.score = config['score_weight'] // 2
            result.recommendations.append("Use a more restrictive Referrer-Policy")
        
        return result
    
    def _analyze_permissions_policy(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze Permissions-Policy header."""
        # Count controlled features
        controlled_features = 0
        for feature in config['recommended_features']:
            if feature in value.lower():
                controlled_features += 1
        
        if controlled_features >= len(config['recommended_features']) // 2:
            result.score = config['score_weight']
            result.status = HeaderStatus.OPTIMAL
        else:
            result.score = config['score_weight'] // 2
            result.recommendations.append("Control more browser features with Permissions-Policy")
        
        return result
    
    def _analyze_generic_header(self, value: str, config: Dict[str, Any], result: HeaderResult) -> HeaderResult:
        """Analyze generic security headers."""
        if 'recommended_values' in config:
            if value in config['recommended_values']:
                result.score = config['score_weight']
                result.status = HeaderStatus.OPTIMAL
            else:
                result.score = config['score_weight'] // 2
        else:
            result.score = config['score_weight'] // 2
        
        return result
    
    def _perform_additional_checks(self, headers: Dict[str, str], result: Dict[str, Any]):
        """Perform additional security checks."""
        
        # Check for server information disclosure
        disclosure_headers = ['server', 'x-powered-by', 'x-aspnet-version', 'x-generator']
        disclosed_info = []
        
        for header in disclosure_headers:
            if header in headers:
                disclosed_info.append(f"{header}: {headers[header]}")
        
        if disclosed_info:
            result['critical_issues'].append("Server information disclosure detected")
            result['recommendations'].append("Remove or obfuscate server information headers")
            result['headers_analyzed']['information_disclosure'] = {
                'name': 'Information Disclosure',
                'status': 'present',
                'value': '; '.join(disclosed_info),
                'issues': ['Server information disclosed'],
                'score': -5
            }
            result['security_score'] -= 5
    
    def _calculate_grade(self, score: int) -> str:
        """Calculate letter grade based on score."""
        if score >= 90:
            return 'A+'
        elif score >= 85:
            return 'A'
        elif score >= 80:
            return 'A-'
        elif score >= 75:
            return 'B+'
        elif score >= 70:
            return 'B'
        elif score >= 65:
            return 'B-'
        elif score >= 60:
            return 'C+'
        elif score >= 55:
            return 'C'
        elif score >= 50:
            return 'C-'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
    
    def audit_multiple_urls(self, urls: List[str]) -> Dict[str, Any]:
        """Audit multiple URLs and generate comparative report."""
        results = {}
        
        for url in urls:
            print(f"Auditing {url}...")
            results[url] = self.audit_url(url)
        
        # Generate summary
        summary = {
            'total_urls': len(urls),
            'average_score': sum(r['security_score'] for r in results.values()) / len(results),
            'grade_distribution': {},
            'common_issues': [],
            'best_practices': []
        }
        
        # Analyze grade distribution
        grades = [r['grade'] for r in results.values()]
        for grade in set(grades):
            summary['grade_distribution'][grade] = grades.count(grade)
        
        # Find common issues
        all_issues = []
        for result in results.values():
            all_issues.extend(result['critical_issues'])
        
        from collections import Counter
        issue_counter = Counter(all_issues)
        summary['common_issues'] = [
            {'issue': issue, 'count': count}
            for issue, count in issue_counter.most_common(10)
        ]
        
        return {
            'summary': summary,
            'individual_results': results
        }
    
    def generate_report(self, audit_result: Dict[str, Any], output_format: str = 'text') -> str:
        """Generate human-readable audit report."""
        
        if output_format == 'json':
            return json.dumps(audit_result, indent=2)
        
        # Text report
        report_lines = [
            "=" * 80,
            "SECURITY HEADERS AUDIT REPORT",
            "=" * 80,
            f"URL: {audit_result['url']}",
            f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(audit_result['timestamp']))}",
            "",
            f"OVERALL SECURITY SCORE: {audit_result['security_score']}/100 (Grade: {audit_result['grade']})",
            ""
        ]
        
        # Response information
        if 'response_info' in audit_result:
            info = audit_result['response_info']
            report_lines.extend([
                "RESPONSE INFORMATION:",
                f"  Status Code: {info.get('status_code', 'N/A')}",
                f"  Final URL: {info.get('final_url', 'N/A')}",
                f"  Response Time: {info.get('response_time_ms', 'N/A')}ms",
                f"  Content Type: {info.get('content_type', 'N/A')}",
                ""
            ])
        
        # Critical issues
        if audit_result['critical_issues']:
            report_lines.extend([
                "🚨 CRITICAL ISSUES:",
                ""
            ])
            for issue in audit_result['critical_issues']:
                report_lines.append(f"  ❌ {issue}")
            report_lines.append("")
        
        # Header analysis
        report_lines.extend([
            "SECURITY HEADERS ANALYSIS:",
            ""
        ])
        
        for header_key, header_info in audit_result['headers_analyzed'].items():
            status_emoji = {
                'optimal': '✅',
                'present': '⚠️',
                'missing': '❌',
                'misconfigured': '🔧'
            }.get(header_info['status'], '❓')
            
            report_lines.extend([
                f"{status_emoji} {header_info['name']} ({header_info['score']} points)",
                f"   Status: {header_info['status'].upper()}",
                f"   Value: {header_info['value'] or 'Not present'}",
            ])
            
            if header_info['issues']:
                for issue in header_info['issues']:
                    report_lines.append(f"   Issue: {issue}")
            
            if header_info['recommendations']:
                for rec in header_info['recommendations']:
                    report_lines.append(f"   💡 {rec}")
            
            report_lines.append("")
        
        # Recommendations
        if audit_result['recommendations']:
            unique_recommendations = list(set(audit_result['recommendations']))
            report_lines.extend([
                "🔧 RECOMMENDATIONS:",
                ""
            ])
            for i, rec in enumerate(unique_recommendations[:10], 1):
                report_lines.append(f"  {i}. {rec}")
            report_lines.append("")
        
        # Error information
        if 'error' in audit_result:
            report_lines.extend([
                "❌ ERROR:",
                f"  {audit_result['error']}",
                ""
            ])
        
        report_lines.extend([
            "NEXT STEPS:",
            "1. Address critical security issues immediately",
            "2. Implement missing security headers",
            "3. Review and strengthen existing headers",
            "4. Test changes in staging environment",
            "5. Monitor headers regularly with automated tools",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


def audit_activelog_services():
    """Audit ActiveLog services for security headers."""
    
    # ActiveLog service URLs to audit
    urls_to_audit = [
        'https://localhost',
        'http://localhost:8000',  # API Gateway
        'http://localhost:3000',  # Frontend
        'http://localhost:8001',  # Auth Service
        'http://localhost:8002',  # Metadata Service
        'http://localhost:8003',  # File Service
    ]
    
    auditor = SecurityHeadersAuditor()
    
    print("🔍 Starting Security Headers Audit for ActiveLog...")
    print(f"Auditing {len(urls_to_audit)} services...")
    
    # Audit all URLs
    audit_results = auditor.audit_multiple_urls(urls_to_audit)
    
    # Generate individual reports
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    for url, result in audit_results['individual_results'].items():
        if 'error' not in result:
            # Generate text report
            report = auditor.generate_report(result)
            
            # Save report
            url_safe = urllib.parse.quote(url, safe='')
            report_file = reports_dir / f"security_headers_{url_safe}.txt"
            
            with open(report_file, 'w') as f:
                f.write(report)
            
            print(f"✅ {url}: Grade {result['grade']} ({result['security_score']}/100)")
        else:
            print(f"❌ {url}: {result['error']}")
    
    # Generate summary report
    summary_report = generate_summary_report(audit_results)
    summary_file = reports_dir / "security_headers_summary.txt"
    
    with open(summary_file, 'w') as f:
        f.write(summary_report)
    
    print(f"\n📊 Summary Report saved to: {summary_file}")
    print(summary_report)
    
    return audit_results


def generate_summary_report(audit_results: Dict[str, Any]) -> str:
    """Generate summary report for multiple URL audits."""
    
    summary = audit_results['summary']
    
    report_lines = [
        "=" * 80,
        "ACTIVELOG SECURITY HEADERS SUMMARY REPORT",
        "=" * 80,
        f"Total Services Audited: {summary['total_urls']}",
        f"Average Security Score: {summary['average_score']:.1f}/100",
        "",
        "GRADE DISTRIBUTION:",
    ]
    
    for grade, count in sorted(summary['grade_distribution'].items()):
        report_lines.append(f"  {grade}: {count} service(s)")
    
    report_lines.extend([
        "",
        "MOST COMMON ISSUES:",
    ])
    
    for issue_info in summary['common_issues']:
        report_lines.append(f"  {issue_info['issue']} ({issue_info['count']} services)")
    
    report_lines.extend([
        "",
        "RECOMMENDATIONS FOR ACTIVELOG:",
        "1. Implement comprehensive security headers in Nginx reverse proxy",
        "2. Add Content Security Policy to prevent XSS attacks",
        "3. Enable HSTS with includeSubDomains and preload",
        "4. Configure Permissions-Policy to control browser features",
        "5. Remove server information disclosure headers",
        "6. Implement security headers middleware in all services",
        "7. Regular automated security headers monitoring",
        "",
        "IMPLEMENTATION PRIORITY:",
        "🔴 High: HSTS, CSP, X-Frame-Options",
        "🟡 Medium: X-Content-Type-Options, Referrer-Policy",
        "🟢 Low: Permissions-Policy, COOP/COEP/CORP",
        "",
        "=" * 80
    ])
    
    return "\n".join(report_lines)


def main():
    """Main function to run security headers audit."""
    print("🛡️ ActiveLog Security Headers Audit Tool")
    print("========================================")
    
    # Example: Audit a single URL
    auditor = SecurityHeadersAuditor()
    
    # Test with a public site first
    print("\n🧪 Testing with example.com...")
    test_result = auditor.audit_url('https://example.com')
    test_report = auditor.generate_report(test_result)
    
    print(f"Example.com Grade: {test_result['grade']} ({test_result['security_score']}/100)")
    
    # Save test report
    reports_dir = Path(__file__).parent.parent / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    with open(reports_dir / "security_headers_example.txt", 'w') as f:
        f.write(test_report)
    
    print(f"\n📄 Test report saved to: {reports_dir}/security_headers_example.txt")
    
    # Audit ActiveLog services (will fail if not running)
    print("\n🔍 Attempting to audit ActiveLog services...")
    try:
        activelog_results = audit_activelog_services()
        print("✅ ActiveLog audit completed!")
    except Exception as e:
        print(f"❌ ActiveLog audit failed (services may not be running): {e}")
        print("To audit ActiveLog services, ensure they are running and accessible.")
    
    print("\n✅ Security Headers Audit completed!")


if __name__ == "__main__":
    main()