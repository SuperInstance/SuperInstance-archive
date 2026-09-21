#!/usr/bin/env python3
"""
Browser Compatibility Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive cross-browser compatibility testing,
including feature detection, rendering differences, performance variations,
and browser-specific functionality validation.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import logging
from pathlib import Path
import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
import subprocess
import os

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.firefox.service import Service as FirefoxService
    from selenium.webdriver.edge.service import Service as EdgeService
    from selenium.webdriver.safari.service import Service as SafariService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.firefox.options import Options as FirefoxOptions
    from selenium.webdriver.edge.options import Options as EdgeOptions
    from selenium.webdriver.safari.options import Options as SafariOptions
    from selenium.common.exceptions import WebDriverException, TimeoutException
    from webdriver_manager.chrome import ChromeDriverManager
    from webdriver_manager.firefox import GeckoDriverManager
    from webdriver_manager.microsoft import EdgeChromiumDriverManager
except ImportError:
    print("Selenium and webdriver-manager required: pip install selenium webdriver-manager")

class BrowserType(Enum):
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"
    SAFARI = "safari"
    OPERA = "opera"
    IE = "ie"

class CompatibilityIssueType(Enum):
    RENDERING_DIFFERENCE = "rendering_difference"
    FEATURE_UNSUPPORTED = "feature_unsupported"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    JAVASCRIPT_ERROR = "javascript_error"
    CSS_INCOMPATIBILITY = "css_incompatibility"
    API_MISSING = "api_missing"
    FONT_RENDERING = "font_rendering"
    LAYOUT_BROKEN = "layout_broken"

class BrowserFeature(Enum):
    ES6_MODULES = "es6_modules"
    WEBGL = "webgl"
    WEBSOCKETS = "websockets"
    LOCAL_STORAGE = "local_storage"
    SESSION_STORAGE = "session_storage"
    GEOLOCATION = "geolocation"
    WEBRTC = "webrtc"
    SERVICE_WORKERS = "service_workers"
    WEB_WORKERS = "web_workers"
    INDEXED_DB = "indexed_db"
    WEB_AUDIO = "web_audio"
    CANVAS = "canvas"
    SVG = "svg"
    FLEXBOX = "flexbox"
    GRID = "grid"
    MEDIA_QUERIES = "media_queries"

class TestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class BrowserVersion:
    major: int
    minor: int
    patch: int
    build: Optional[str] = None

    def __str__(self):
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version += f".{self.build}"
        return version

@dataclass
class BrowserInfo:
    type: BrowserType
    version: BrowserVersion
    user_agent: str
    viewport_size: Tuple[int, int]
    platform: str
    capabilities: Dict[str, Any] = field(default_factory=dict)

@dataclass
class CompatibilityIssue:
    id: str
    type: CompatibilityIssueType
    severity: TestSeverity
    browser: BrowserType
    description: str
    element_selector: Optional[str] = None
    screenshot_path: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    workaround: Optional[str] = None
    affected_urls: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PerformanceMetrics:
    page_load_time: float
    dom_ready_time: float
    first_contentful_paint: float
    largest_contentful_paint: float
    cumulative_layout_shift: float
    first_input_delay: float
    memory_usage: Optional[float] = None

@dataclass
class CompatibilityTestResult:
    browser: BrowserType
    test_name: str
    status: str
    issues: List[CompatibilityIssue] = field(default_factory=list)
    performance: Optional[PerformanceMetrics] = None
    screenshots: Dict[str, str] = field(default_factory=dict)
    feature_support: Dict[BrowserFeature, bool] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class CrossBrowserTestSuite:
    name: str
    urls: List[str]
    browsers: List[BrowserType]
    test_scenarios: List[str]
    viewport_sizes: List[Tuple[int, int]] = field(default_factory=lambda: [(1920, 1080), (1366, 768), (768, 1024)])
    features_to_test: List[BrowserFeature] = field(default_factory=list)
    performance_thresholds: Dict[str, float] = field(default_factory=dict)

class BrowserDriverManager:
    def __init__(self):
        self.drivers = {}
        self.capabilities = {}
        self.setup_drivers()

    def setup_drivers(self):
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            
            firefox_options = FirefoxOptions()
            firefox_options.add_argument("--headless")
            
            edge_options = EdgeOptions()
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            
            self.capabilities = {
                BrowserType.CHROME: {
                    "service": ChromeService(ChromeDriverManager().install()),
                    "options": chrome_options
                },
                BrowserType.FIREFOX: {
                    "service": FirefoxService(GeckoDriverManager().install()),
                    "options": firefox_options
                },
                BrowserType.EDGE: {
                    "service": EdgeService(EdgeChromiumDriverManager().install()),
                    "options": edge_options
                }
            }
        except Exception as e:
            logging.error(f"Error setting up browser drivers: {e}")

    def get_driver(self, browser_type: BrowserType, headless: bool = False) -> Optional[webdriver.Remote]:
        try:
            if browser_type == BrowserType.CHROME:
                options = self.capabilities[BrowserType.CHROME]["options"]
                if headless:
                    options.add_argument("--headless")
                return webdriver.Chrome(
                    service=self.capabilities[BrowserType.CHROME]["service"],
                    options=options
                )
            elif browser_type == BrowserType.FIREFOX:
                options = self.capabilities[BrowserType.FIREFOX]["options"]
                if headless:
                    options.add_argument("--headless")
                return webdriver.Firefox(
                    service=self.capabilities[BrowserType.FIREFOX]["service"],
                    options=options
                )
            elif browser_type == BrowserType.EDGE:
                options = self.capabilities[BrowserType.EDGE]["options"]
                if headless:
                    options.add_argument("--headless")
                return webdriver.Edge(
                    service=self.capabilities[BrowserType.EDGE]["service"],
                    options=options
                )
        except Exception as e:
            logging.error(f"Failed to create {browser_type.value} driver: {e}")
            return None

    def quit_all_drivers(self):
        for driver in self.drivers.values():
            try:
                driver.quit()
            except Exception as e:
                logging.error(f"Error quitting driver: {e}")
        self.drivers.clear()

class FeatureDetector:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def detect_features(self) -> Dict[BrowserFeature, bool]:
        features = {}
        
        feature_tests = {
            BrowserFeature.ES6_MODULES: "return 'import' in window",
            BrowserFeature.WEBGL: "return !!window.WebGLRenderingContext",
            BrowserFeature.WEBSOCKETS: "return 'WebSocket' in window",
            BrowserFeature.LOCAL_STORAGE: "return typeof(Storage) !== 'undefined'",
            BrowserFeature.SESSION_STORAGE: "return 'sessionStorage' in window",
            BrowserFeature.GEOLOCATION: "return 'geolocation' in navigator",
            BrowserFeature.WEBRTC: "return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)",
            BrowserFeature.SERVICE_WORKERS: "return 'serviceWorker' in navigator",
            BrowserFeature.WEB_WORKERS: "return typeof(Worker) !== 'undefined'",
            BrowserFeature.INDEXED_DB: "return 'indexedDB' in window",
            BrowserFeature.WEB_AUDIO: "return !!(window.AudioContext || window.webkitAudioContext)",
            BrowserFeature.CANVAS: "return !!document.createElement('canvas').getContext",
            BrowserFeature.SVG: "return !!(document.createElementNS && document.createElementNS('http://www.w3.org/2000/svg', 'svg').createSVGRect)",
            BrowserFeature.FLEXBOX: "return CSS.supports('display', 'flex')",
            BrowserFeature.GRID: "return CSS.supports('display', 'grid')",
            BrowserFeature.MEDIA_QUERIES: "return 'matchMedia' in window"
        }
        
        for feature, test_script in feature_tests.items():
            try:
                result = self.driver.execute_script(test_script)
                features[feature] = bool(result)
            except Exception as e:
                logging.warning(f"Feature detection failed for {feature}: {e}")
                features[feature] = False
        
        return features

class PerformanceAnalyzer:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def collect_performance_metrics(self) -> PerformanceMetrics:
        try:
            navigation_timing = self.driver.execute_script("""
                var timing = window.performance.timing;
                var navigation = window.performance.getEntriesByType('navigation')[0];
                return {
                    navigationStart: timing.navigationStart,
                    domContentLoaded: timing.domContentLoadedEventEnd,
                    loadComplete: timing.loadEventEnd,
                    firstContentfulPaint: navigation ? navigation.loadEventEnd : null,
                    largestContentfulPaint: null,
                    cumulativeLayoutShift: null,
                    firstInputDelay: null
                };
            """)
            
            memory_info = self.driver.execute_script("""
                return window.performance.memory ? {
                    usedJSHeapSize: window.performance.memory.usedJSHeapSize,
                    totalJSHeapSize: window.performance.memory.totalJSHeapSize
                } : null;
            """)
            
            page_load_time = (navigation_timing['loadComplete'] - navigation_timing['navigationStart']) / 1000
            dom_ready_time = (navigation_timing['domContentLoaded'] - navigation_timing['navigationStart']) / 1000
            
            memory_usage = None
            if memory_info:
                memory_usage = memory_info['usedJSHeapSize'] / (1024 * 1024)  # Convert to MB
            
            return PerformanceMetrics(
                page_load_time=page_load_time,
                dom_ready_time=dom_ready_time,
                first_contentful_paint=navigation_timing.get('firstContentfulPaint', 0) / 1000,
                largest_contentful_paint=0.0,  # Would need additional measurement
                cumulative_layout_shift=0.0,   # Would need additional measurement
                first_input_delay=0.0,         # Would need additional measurement
                memory_usage=memory_usage
            )
        except Exception as e:
            logging.error(f"Performance metrics collection failed: {e}")
            return PerformanceMetrics(0, 0, 0, 0, 0, 0)

class VisualRegressionTester:
    def __init__(self, screenshots_dir: str):
        self.screenshots_dir = Path(screenshots_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)

    def take_screenshot(self, driver: webdriver.Remote, name: str, browser: BrowserType) -> str:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{name}_{browser.value}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            driver.save_screenshot(str(filepath))
            return str(filepath)
        except Exception as e:
            logging.error(f"Screenshot capture failed: {e}")
            return ""

    def compare_screenshots(self, baseline_path: str, current_path: str) -> Tuple[bool, float]:
        try:
            with open(baseline_path, 'rb') as f:
                baseline_hash = hashlib.md5(f.read()).hexdigest()
            
            with open(current_path, 'rb') as f:
                current_hash = hashlib.md5(f.read()).hexdigest()
            
            if baseline_hash == current_hash:
                return True, 0.0
            else:
                return False, 1.0  # Simplified difference calculation
        except Exception as e:
            logging.error(f"Screenshot comparison failed: {e}")
            return False, 1.0

class BrowserCompatibilityEngine:
    def __init__(self, screenshots_dir: str = "screenshots", results_dir: str = "results"):
        self.driver_manager = BrowserDriverManager()
        self.visual_tester = VisualRegressionTester(screenshots_dir)
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def run_compatibility_test_suite(self, test_suite: CrossBrowserTestSuite) -> Dict[BrowserType, List[CompatibilityTestResult]]:
        results = {}
        
        for browser in test_suite.browsers:
            browser_results = []
            driver = self.driver_manager.get_driver(browser, headless=True)
            
            if not driver:
                logging.error(f"Failed to initialize {browser.value} driver")
                continue
            
            try:
                for url in test_suite.urls:
                    for viewport in test_suite.viewport_sizes:
                        result = await self.run_single_test(
                            driver, browser, url, viewport, test_suite
                        )
                        browser_results.append(result)
                
                results[browser] = browser_results
            finally:
                driver.quit()
        
        return results

    async def run_single_test(
        self, 
        driver: webdriver.Remote, 
        browser: BrowserType, 
        url: str, 
        viewport: Tuple[int, int],
        test_suite: CrossBrowserTestSuite
    ) -> CompatibilityTestResult:
        start_time = time.time()
        issues = []
        screenshots = {}
        
        try:
            driver.set_window_size(viewport[0], viewport[1])
            driver.get(url)
            
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            feature_detector = FeatureDetector(driver)
            feature_support = feature_detector.detect_features()
            
            performance_analyzer = PerformanceAnalyzer(driver)
            performance_metrics = performance_analyzer.collect_performance_metrics()
            
            screenshot_name = f"{url.replace('://', '_').replace('/', '_')}_{viewport[0]}x{viewport[1]}"
            screenshot_path = self.visual_tester.take_screenshot(driver, screenshot_name, browser)
            screenshots[screenshot_name] = screenshot_path
            
            console_logs = driver.get_log('browser')
            for log in console_logs:
                if log['level'] in ['SEVERE', 'ERROR']:
                    issue = CompatibilityIssue(
                        id=f"{browser.value}_{len(issues)}",
                        type=CompatibilityIssueType.JAVASCRIPT_ERROR,
                        severity=TestSeverity.HIGH if log['level'] == 'SEVERE' else TestSeverity.MEDIUM,
                        browser=browser,
                        description=f"Console error: {log['message']}",
                        affected_urls=[url]
                    )
                    issues.append(issue)
            
            for feature in test_suite.features_to_test:
                if not feature_support.get(feature, False):
                    issue = CompatibilityIssue(
                        id=f"{browser.value}_{feature.value}_unsupported",
                        type=CompatibilityIssueType.FEATURE_UNSUPPORTED,
                        severity=TestSeverity.HIGH,
                        browser=browser,
                        description=f"Feature {feature.value} is not supported",
                        affected_urls=[url]
                    )
                    issues.append(issue)
            
            for threshold_name, threshold_value in test_suite.performance_thresholds.items():
                if hasattr(performance_metrics, threshold_name):
                    actual_value = getattr(performance_metrics, threshold_name)
                    if actual_value and actual_value > threshold_value:
                        issue = CompatibilityIssue(
                            id=f"{browser.value}_{threshold_name}_slow",
                            type=CompatibilityIssueType.PERFORMANCE_DEGRADATION,
                            severity=TestSeverity.MEDIUM,
                            browser=browser,
                            description=f"{threshold_name} ({actual_value:.2f}s) exceeds threshold ({threshold_value}s)",
                            affected_urls=[url]
                        )
                        issues.append(issue)
            
        except TimeoutException:
            issue = CompatibilityIssue(
                id=f"{browser.value}_timeout",
                type=CompatibilityIssueType.PERFORMANCE_DEGRADATION,
                severity=TestSeverity.HIGH,
                browser=browser,
                description="Page load timeout",
                affected_urls=[url]
            )
            issues.append(issue)
        except Exception as e:
            issue = CompatibilityIssue(
                id=f"{browser.value}_error",
                type=CompatibilityIssueType.JAVASCRIPT_ERROR,
                severity=TestSeverity.CRITICAL,
                browser=browser,
                description=f"Test execution error: {str(e)}",
                affected_urls=[url]
            )
            issues.append(issue)
        
        execution_time = time.time() - start_time
        
        return CompatibilityTestResult(
            browser=browser,
            test_name=f"{url}_{viewport[0]}x{viewport[1]}",
            status="completed",
            issues=issues,
            performance=performance_metrics,
            screenshots=screenshots,
            feature_support=feature_support,
            execution_time=execution_time
        )

    def generate_compatibility_report(self, results: Dict[BrowserType, List[CompatibilityTestResult]], output_path: str):
        report = {
            "test_summary": {
                "total_browsers": len(results),
                "total_tests": sum(len(browser_results) for browser_results in results.values()),
                "total_issues": sum(
                    len(result.issues) 
                    for browser_results in results.values() 
                    for result in browser_results
                ),
                "timestamp": datetime.now().isoformat()
            },
            "browser_results": {},
            "compatibility_matrix": {},
            "issue_summary": {}
        }
        
        issue_counts = {}
        
        for browser, browser_results in results.items():
            browser_summary = {
                "total_tests": len(browser_results),
                "passed_tests": len([r for r in browser_results if not r.issues]),
                "failed_tests": len([r for r in browser_results if r.issues]),
                "total_issues": sum(len(r.issues) for r in browser_results),
                "avg_performance": {
                    "page_load_time": sum(
                        r.performance.page_load_time for r in browser_results if r.performance
                    ) / len(browser_results) if browser_results else 0,
                    "memory_usage": sum(
                        r.performance.memory_usage for r in browser_results 
                        if r.performance and r.performance.memory_usage
                    ) / len([
                        r for r in browser_results 
                        if r.performance and r.performance.memory_usage
                    ]) if any(r.performance and r.performance.memory_usage for r in browser_results) else 0
                },
                "feature_support": {},
                "test_results": []
            }
            
            all_features = set()
            for result in browser_results:
                all_features.update(result.feature_support.keys())
            
            for feature in all_features:
                supported_count = sum(
                    1 for result in browser_results 
                    if result.feature_support.get(feature, False)
                )
                browser_summary["feature_support"][feature.value] = {
                    "supported": supported_count,
                    "total": len(browser_results),
                    "percentage": (supported_count / len(browser_results)) * 100
                }
            
            for result in browser_results:
                test_data = {
                    "test_name": result.test_name,
                    "status": result.status,
                    "execution_time": result.execution_time,
                    "issues_count": len(result.issues),
                    "performance": result.performance.__dict__ if result.performance else None,
                    "screenshots": result.screenshots,
                    "issues": [
                        {
                            "id": issue.id,
                            "type": issue.type.value,
                            "severity": issue.severity.value,
                            "description": issue.description,
                            "element_selector": issue.element_selector,
                            "workaround": issue.workaround
                        } for issue in result.issues
                    ]
                }
                browser_summary["test_results"].append(test_data)
                
                for issue in result.issues:
                    issue_key = f"{issue.type.value}_{issue.severity.value}"
                    issue_counts[issue_key] = issue_counts.get(issue_key, 0) + 1
            
            report["browser_results"][browser.value] = browser_summary
        
        report["issue_summary"] = issue_counts
        
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
            <title>Browser Compatibility Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .browser-section {{ margin-bottom: 30px; }}
                .browser-header {{ background: #007bff; color: white; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
                .test-grid {{ display: grid; gap: 10px; }}
                .test-item {{ background: #f8f9fa; padding: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.failed {{ border-left-color: #dc3545; }}
                .issue-list {{ margin-top: 10px; }}
                .issue {{ background: #fff3cd; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #ffc107; }}
                .issue.critical {{ background: #f8d7da; border-left-color: #dc3545; }}
                .issue.high {{ background: #f8d7da; border-left-color: #fd7e14; }}
                .performance-metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin: 10px 0; }}
                .metric {{ background: white; padding: 8px; border-radius: 4px; text-align: center; }}
                .feature-support {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; margin: 10px 0; }}
                .feature {{ background: white; padding: 8px; border-radius: 4px; }}
                .support-bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; }}
                .support-fill {{ height: 100%; background: #28a745; transition: width 0.3s ease; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Browser Compatibility Test Report</h1>
                    <p>Generated on {report_data['test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Browsers</h3>
                        <div class="value">{report_data['test_summary']['total_browsers']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['test_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Issues</h3>
                        <div class="value">{report_data['test_summary']['total_issues']}</div>
                    </div>
                </div>
        """
        
        for browser_name, browser_data in report_data['browser_results'].items():
            html_content += f"""
                <div class="browser-section">
                    <div class="browser-header">
                        <h2>{browser_name.upper()}</h2>
                        <p>Tests: {browser_data['total_tests']} | Passed: {browser_data['passed_tests']} | Failed: {browser_data['failed_tests']}</p>
                    </div>
                    
                    <h3>Performance Metrics</h3>
                    <div class="performance-metrics">
                        <div class="metric">
                            <strong>Avg Page Load</strong><br>
                            {browser_data['avg_performance']['page_load_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Avg Memory Usage</strong><br>
                            {browser_data['avg_performance']['memory_usage']:.2f} MB
                        </div>
                    </div>
                    
                    <h3>Feature Support</h3>
                    <div class="feature-support">
            """
            
            for feature_name, feature_data in browser_data['feature_support'].items():
                percentage = feature_data['percentage']
                html_content += f"""
                        <div class="feature">
                            <strong>{feature_name.replace('_', ' ').title()}</strong>
                            <div class="support-bar">
                                <div class="support-fill" style="width: {percentage}%;"></div>
                            </div>
                            <small>{feature_data['supported']}/{feature_data['total']} ({percentage:.1f}%)</small>
                        </div>
                """
            
            html_content += """
                    </div>
                    
                    <h3>Test Results</h3>
                    <div class="test-grid">
            """
            
            for test in browser_data['test_results']:
                status_class = 'failed' if test['issues_count'] > 0 else ''
                html_content += f"""
                        <div class="test-item {status_class}">
                            <h4>{test['test_name']}</h4>
                            <p>Status: {test['status']} | Execution Time: {test['execution_time']:.2f}s | Issues: {test['issues_count']}</p>
                """
                
                if test['issues']:
                    html_content += '<div class="issue-list">'
                    for issue in test['issues']:
                        issue_class = issue['severity']
                        html_content += f"""
                                <div class="issue {issue_class}">
                                    <strong>[{issue['severity'].upper()}] {issue['type'].replace('_', ' ').title()}</strong><br>
                                    {issue['description']}
                                </div>
                        """
                    html_content += '</div>'
                
                html_content += '</div>'
            
            html_content += '</div></div>'
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

    async def run_cross_browser_validation(
        self, 
        urls: List[str], 
        browsers: List[BrowserType] = None,
        features: List[BrowserFeature] = None
    ) -> Dict[str, Any]:
        if not browsers:
            browsers = [BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.EDGE]
        
        if not features:
            features = list(BrowserFeature)
        
        test_suite = CrossBrowserTestSuite(
            name="Cross-Browser Validation",
            urls=urls,
            browsers=browsers,
            test_scenarios=["basic_load", "feature_detection", "performance_check"],
            features_to_test=features,
            performance_thresholds={
                "page_load_time": 5.0,
                "dom_ready_time": 3.0,
                "memory_usage": 100.0  # MB
            }
        )
        
        results = await self.run_compatibility_test_suite(test_suite)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"browser_compatibility_report_{timestamp}.json"
        
        self.generate_compatibility_report(results, str(report_path))
        
        return {
            "results": results,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html'),
            "summary": {
                "browsers_tested": len(browsers),
                "urls_tested": len(urls),
                "total_issues": sum(
                    len(result.issues) 
                    for browser_results in results.values() 
                    for result in browser_results
                )
            }
        }

async def main():
    engine = BrowserCompatibilityEngine()
    
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html"
    ]
    
    browsers_to_test = [
        BrowserType.CHROME,
        BrowserType.FIREFOX,
        BrowserType.EDGE
    ]
    
    features_to_test = [
        BrowserFeature.WEBSOCKETS,
        BrowserFeature.LOCAL_STORAGE,
        BrowserFeature.WEBGL,
        BrowserFeature.SERVICE_WORKERS
    ]
    
    print("Running cross-browser compatibility tests...")
    results = await engine.run_cross_browser_validation(
        urls=test_urls,
        browsers=browsers_to_test,
        features=features_to_test
    )
    
    print(f"Tests completed!")
    print(f"Browsers tested: {results['summary']['browsers_tested']}")
    print(f"URLs tested: {results['summary']['urls_tested']}")
    print(f"Total issues found: {results['summary']['total_issues']}")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())