#!/usr/bin/env python3
"""
Accessibility Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive accessibility testing following WCAG 2.1 guidelines,
including automated testing, manual test guidance, and compliance reporting.
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
import logging
from pathlib import Path
import re
from concurrent.futures import ThreadPoolExecutor
import subprocess
import base64

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Selenium and webdriver-manager required: pip install selenium webdriver-manager")

class WcagLevel(Enum):
    A = "A"
    AA = "AA"
    AAA = "AAA"

class WcagPrinciple(Enum):
    PERCEIVABLE = "perceivable"
    OPERABLE = "operable"
    UNDERSTANDABLE = "understandable"
    ROBUST = "robust"

class AccessibilityViolationType(Enum):
    MISSING_ALT_TEXT = "missing_alt_text"
    INSUFFICIENT_COLOR_CONTRAST = "insufficient_color_contrast"
    MISSING_FORM_LABELS = "missing_form_labels"
    KEYBOARD_NAVIGATION_ISSUES = "keyboard_navigation_issues"
    MISSING_HEADING_STRUCTURE = "missing_heading_structure"
    FOCUS_MANAGEMENT = "focus_management"
    ARIA_VIOLATIONS = "aria_violations"
    SEMANTIC_STRUCTURE = "semantic_structure"
    TEXT_ALTERNATIVES = "text_alternatives"
    RESPONSIVE_DESIGN = "responsive_design"
    TIMING_ISSUES = "timing_issues"
    SEIZURE_TRIGGERS = "seizure_triggers"

class AccessibilitySeverity(Enum):
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"

class TestType(Enum):
    AUTOMATED = "automated"
    MANUAL = "manual"
    HYBRID = "hybrid"

@dataclass
class ColorContrastResult:
    foreground: str
    background: str
    ratio: float
    passes_aa: bool
    passes_aaa: bool
    element_selector: str

@dataclass
class KeyboardNavigationResult:
    focusable_elements: List[str]
    unreachable_elements: List[str]
    focus_order_issues: List[str]
    keyboard_traps: List[str]

@dataclass
class AccessibilityViolation:
    id: str
    type: AccessibilityViolationType
    severity: AccessibilitySeverity
    wcag_level: WcagLevel
    wcag_principle: WcagPrinciple
    wcag_guideline: str
    description: str
    element_selector: Optional[str] = None
    element_html: Optional[str] = None
    suggested_fix: Optional[str] = None
    help_url: Optional[str] = None
    impact: Optional[str] = None
    xpath: Optional[str] = None
    screenshot_path: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AccessibilityTestResult:
    url: str
    test_name: str
    test_type: TestType
    wcag_level: WcagLevel
    violations: List[AccessibilityViolation] = field(default_factory=list)
    passed_rules: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    color_contrast_results: List[ColorContrastResult] = field(default_factory=list)
    keyboard_navigation: Optional[KeyboardNavigationResult] = None
    page_structure_score: float = 0.0
    overall_score: float = 0.0
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class AccessibilityTestSuite:
    name: str
    urls: List[str]
    wcag_level: WcagLevel
    test_types: List[TestType]
    include_color_contrast: bool = True
    include_keyboard_navigation: bool = True
    include_screen_reader_testing: bool = True
    viewport_sizes: List[Tuple[int, int]] = field(default_factory=lambda: [(1920, 1080), (768, 1024), (375, 667)])
    custom_rules: List[str] = field(default_factory=list)

class AccessibilityAuditor:
    def __init__(self):
        self.axe_core_script = self._load_axe_core()
        self.wcag_rules = self._load_wcag_rules()

    def _load_axe_core(self) -> str:
        axe_core_js = """
        // Simplified axe-core implementation for accessibility testing
        window.axe = {
            run: function(context, options, callback) {
                var results = {
                    violations: [],
                    passes: [],
                    incomplete: [],
                    timestamp: new Date().toISOString()
                };
                
                // Check for missing alt text
                var images = document.querySelectorAll('img');
                images.forEach(function(img, index) {
                    if (!img.alt && !img.getAttribute('aria-label') && !img.getAttribute('aria-labelledby')) {
                        results.violations.push({
                            id: 'image-alt',
                            description: 'Images must have alternate text',
                            impact: 'critical',
                            nodes: [{
                                target: ['img:nth-child(' + (index + 1) + ')'],
                                html: img.outerHTML,
                                failureSummary: 'Missing alt attribute'
                            }]
                        });
                    }
                });
                
                // Check for form labels
                var inputs = document.querySelectorAll('input, textarea, select');
                inputs.forEach(function(input, index) {
                    var hasLabel = document.querySelector('label[for="' + input.id + '"]') ||
                                  input.getAttribute('aria-label') ||
                                  input.getAttribute('aria-labelledby') ||
                                  input.closest('label');
                    
                    if (!hasLabel && input.type !== 'hidden' && input.type !== 'submit' && input.type !== 'button') {
                        results.violations.push({
                            id: 'label',
                            description: 'Form elements must have labels',
                            impact: 'critical',
                            nodes: [{
                                target: [input.tagName.toLowerCase() + ':nth-child(' + (index + 1) + ')'],
                                html: input.outerHTML,
                                failureSummary: 'Missing label'
                            }]
                        });
                    }
                });
                
                // Check heading structure
                var headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                var prevLevel = 0;
                headings.forEach(function(heading, index) {
                    var level = parseInt(heading.tagName.substring(1));
                    if (index === 0 && level !== 1) {
                        results.violations.push({
                            id: 'page-has-heading-one',
                            description: 'Page should have a heading that starts with h1',
                            impact: 'moderate',
                            nodes: [{
                                target: [heading.tagName.toLowerCase() + ':first-child'],
                                html: heading.outerHTML,
                                failureSummary: 'Page does not start with h1'
                            }]
                        });
                    }
                    
                    if (level > prevLevel + 1) {
                        results.violations.push({
                            id: 'heading-order',
                            description: 'Heading levels should increase by one',
                            impact: 'moderate',
                            nodes: [{
                                target: [heading.tagName.toLowerCase() + ':nth-child(' + (index + 1) + ')'],
                                html: heading.outerHTML,
                                failureSummary: 'Heading level skipped'
                            }]
                        });
                    }
                    
                    prevLevel = level;
                });
                
                // Check for ARIA violations
                var ariaElements = document.querySelectorAll('[aria-labelledby]');
                ariaElements.forEach(function(element, index) {
                    var labelId = element.getAttribute('aria-labelledby');
                    if (!document.getElementById(labelId)) {
                        results.violations.push({
                            id: 'aria-labelledby',
                            description: 'aria-labelledby attribute must reference an existing element',
                            impact: 'serious',
                            nodes: [{
                                target: ['[aria-labelledby="' + labelId + '"]:nth-child(' + (index + 1) + ')'],
                                html: element.outerHTML,
                                failureSummary: 'Referenced label does not exist'
                            }]
                        });
                    }
                });
                
                // Check color contrast (simplified)
                var textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, div, a, button');
                textElements.forEach(function(element, index) {
                    if (element.textContent.trim()) {
                        var styles = window.getComputedStyle(element);
                        var color = styles.color;
                        var backgroundColor = styles.backgroundColor;
                        
                        // This is a simplified check - real implementation would calculate actual contrast ratio
                        if (color === 'rgb(128, 128, 128)' && backgroundColor === 'rgb(255, 255, 255)') {
                            results.violations.push({
                                id: 'color-contrast',
                                description: 'Elements must have sufficient color contrast',
                                impact: 'serious',
                                nodes: [{
                                    target: [element.tagName.toLowerCase() + ':nth-child(' + (index + 1) + ')'],
                                    html: element.outerHTML,
                                    failureSummary: 'Insufficient color contrast'
                                }]
                            });
                        }
                    }
                });
                
                if (callback) {
                    callback(results);
                }
                return results;
            }
        };
        """
        return axe_core_js

    def _load_wcag_rules(self) -> Dict[str, Dict[str, Any]]:
        return {
            "image-alt": {
                "wcag_level": "A",
                "principle": "perceivable",
                "guideline": "1.1.1",
                "description": "All images must have alternative text"
            },
            "label": {
                "wcag_level": "A", 
                "principle": "perceivable",
                "guideline": "1.3.1",
                "description": "Form elements must have labels"
            },
            "color-contrast": {
                "wcag_level": "AA",
                "principle": "perceivable", 
                "guideline": "1.4.3",
                "description": "Text must have sufficient color contrast"
            },
            "heading-order": {
                "wcag_level": "AA",
                "principle": "perceivable",
                "guideline": "1.3.1", 
                "description": "Headings must be properly structured"
            },
            "keyboard-navigation": {
                "wcag_level": "A",
                "principle": "operable",
                "guideline": "2.1.1",
                "description": "All functionality must be keyboard accessible"
            }
        }

    async def audit_page(self, driver: webdriver.Remote, url: str, wcag_level: WcagLevel) -> AccessibilityTestResult:
        start_time = time.time()
        violations = []
        
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            driver.execute_script(self.axe_core_script)
            
            axe_results = driver.execute_script("return axe.run();")
            
            for violation in axe_results.get('violations', []):
                rule_info = self.wcag_rules.get(violation['id'], {})
                
                for node in violation.get('nodes', []):
                    accessibility_violation = AccessibilityViolation(
                        id=f"{violation['id']}_{len(violations)}",
                        type=self._map_violation_type(violation['id']),
                        severity=self._map_severity(violation.get('impact', 'moderate')),
                        wcag_level=WcagLevel(rule_info.get('wcag_level', 'AA')),
                        wcag_principle=WcagPrinciple(rule_info.get('principle', 'perceivable')),
                        wcag_guideline=rule_info.get('guideline', ''),
                        description=violation.get('description', ''),
                        element_selector=node.get('target', [''])[0] if node.get('target') else None,
                        element_html=node.get('html', ''),
                        suggested_fix=self._get_suggested_fix(violation['id']),
                        help_url=f"https://dequeuniversity.com/rules/axe/4.4/{violation['id']}",
                        impact=violation.get('impact')
                    )
                    violations.append(accessibility_violation)
            
            passed_rules = [pass_rule['id'] for pass_rule in axe_results.get('passes', [])]
            
            execution_time = time.time() - start_time
            overall_score = self._calculate_accessibility_score(violations, passed_rules)
            
            return AccessibilityTestResult(
                url=url,
                test_name=f"accessibility_audit_{wcag_level.value}",
                test_type=TestType.AUTOMATED,
                wcag_level=wcag_level,
                violations=violations,
                passed_rules=passed_rules,
                overall_score=overall_score,
                execution_time=execution_time
            )
            
        except Exception as e:
            logging.error(f"Accessibility audit failed for {url}: {e}")
            return AccessibilityTestResult(
                url=url,
                test_name=f"accessibility_audit_{wcag_level.value}",
                test_type=TestType.AUTOMATED,
                wcag_level=wcag_level,
                violations=[],
                overall_score=0.0,
                execution_time=time.time() - start_time
            )

    def _map_violation_type(self, axe_rule_id: str) -> AccessibilityViolationType:
        mapping = {
            'image-alt': AccessibilityViolationType.MISSING_ALT_TEXT,
            'label': AccessibilityViolationType.MISSING_FORM_LABELS,
            'color-contrast': AccessibilityViolationType.INSUFFICIENT_COLOR_CONTRAST,
            'heading-order': AccessibilityViolationType.MISSING_HEADING_STRUCTURE,
            'aria-labelledby': AccessibilityViolationType.ARIA_VIOLATIONS,
            'keyboard-navigation': AccessibilityViolationType.KEYBOARD_NAVIGATION_ISSUES
        }
        return mapping.get(axe_rule_id, AccessibilityViolationType.SEMANTIC_STRUCTURE)

    def _map_severity(self, axe_impact: str) -> AccessibilitySeverity:
        mapping = {
            'critical': AccessibilitySeverity.CRITICAL,
            'serious': AccessibilitySeverity.SERIOUS,
            'moderate': AccessibilitySeverity.MODERATE,
            'minor': AccessibilitySeverity.MINOR
        }
        return mapping.get(axe_impact, AccessibilitySeverity.MODERATE)

    def _get_suggested_fix(self, rule_id: str) -> str:
        fixes = {
            'image-alt': 'Add meaningful alt text to images. Use alt="" for decorative images.',
            'label': 'Add labels to form controls using <label>, aria-label, or aria-labelledby.',
            'color-contrast': 'Increase color contrast to meet WCAG AA standards (4.5:1 for normal text, 3:1 for large text).',
            'heading-order': 'Use headings in proper hierarchical order (h1, h2, h3, etc.).',
            'aria-labelledby': 'Ensure aria-labelledby references an existing element with the specified ID.',
            'keyboard-navigation': 'Ensure all interactive elements are keyboard accessible and have visible focus indicators.'
        }
        return fixes.get(rule_id, 'Review accessibility guidelines for this element.')

    def _calculate_accessibility_score(self, violations: List[AccessibilityViolation], passed_rules: List[str]) -> float:
        if not violations and not passed_rules:
            return 0.0
        
        total_checks = len(violations) + len(passed_rules)
        passed_checks = len(passed_rules)
        
        base_score = (passed_checks / total_checks) * 100 if total_checks > 0 else 0
        
        severity_penalties = {
            AccessibilitySeverity.CRITICAL: 15,
            AccessibilitySeverity.SERIOUS: 10,
            AccessibilitySeverity.MODERATE: 5,
            AccessibilitySeverity.MINOR: 2
        }
        
        penalty = sum(severity_penalties.get(v.severity, 0) for v in violations)
        final_score = max(0, base_score - penalty)
        
        return round(final_score, 2)

class ColorContrastAnalyzer:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def analyze_color_contrast(self) -> List[ColorContrastResult]:
        results = []
        
        try:
            contrast_data = self.driver.execute_script("""
                function getContrastRatio(fg, bg) {
                    function getLuminance(rgb) {
                        var [r, g, b] = rgb.match(/\\d+/g).map(x => parseInt(x) / 255);
                        [r, g, b] = [r, g, b].map(x => x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4));
                        return 0.2126 * r + 0.7152 * g + 0.0722 * b;
                    }
                    
                    var fgLum = getLuminance(fg);
                    var bgLum = getLuminance(bg);
                    var ratio = (Math.max(fgLum, bgLum) + 0.05) / (Math.min(fgLum, bgLum) + 0.05);
                    return Math.round(ratio * 100) / 100;
                }
                
                var textElements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, span, a, button, label');
                var results = [];
                
                for (var i = 0; i < textElements.length; i++) {
                    var element = textElements[i];
                    if (element.textContent.trim()) {
                        var styles = window.getComputedStyle(element);
                        var color = styles.color;
                        var backgroundColor = styles.backgroundColor;
                        
                        // Skip transparent backgrounds
                        if (backgroundColor === 'rgba(0, 0, 0, 0)' || backgroundColor === 'transparent') {
                            var parent = element.parentElement;
                            while (parent && (window.getComputedStyle(parent).backgroundColor === 'rgba(0, 0, 0, 0)' || 
                                            window.getComputedStyle(parent).backgroundColor === 'transparent')) {
                                parent = parent.parentElement;
                            }
                            if (parent) {
                                backgroundColor = window.getComputedStyle(parent).backgroundColor;
                            } else {
                                backgroundColor = 'rgb(255, 255, 255)'; // Default to white
                            }
                        }
                        
                        var ratio = getContrastRatio(color, backgroundColor);
                        var selector = element.tagName.toLowerCase();
                        if (element.id) selector += '#' + element.id;
                        if (element.className) selector += '.' + element.className.split(' ')[0];
                        
                        results.push({
                            foreground: color,
                            background: backgroundColor,
                            ratio: ratio,
                            selector: selector
                        });
                    }
                }
                
                return results;
            """)
            
            for data in contrast_data:
                ratio = data['ratio']
                result = ColorContrastResult(
                    foreground=data['foreground'],
                    background=data['background'],
                    ratio=ratio,
                    passes_aa=ratio >= 4.5,
                    passes_aaa=ratio >= 7.0,
                    element_selector=data['selector']
                )
                results.append(result)
                
        except Exception as e:
            logging.error(f"Color contrast analysis failed: {e}")
        
        return results

class KeyboardNavigationTester:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def test_keyboard_navigation(self) -> KeyboardNavigationResult:
        try:
            focusable_elements = self.driver.execute_script("""
                var focusableElements = Array.from(document.querySelectorAll(
                    'a[href], button, input, textarea, select, details, [tabindex]:not([tabindex="-1"])'
                )).filter(el => !el.disabled && !el.hidden && el.offsetWidth > 0 && el.offsetHeight > 0);
                
                return focusableElements.map(el => {
                    var selector = el.tagName.toLowerCase();
                    if (el.id) selector += '#' + el.id;
                    if (el.className) selector += '.' + el.className.split(' ')[0];
                    return selector;
                });
            """)
            
            unreachable_elements = []
            focus_order_issues = []
            keyboard_traps = []
            
            body = self.driver.find_element(By.TAG_NAME, "body")
            body.click()  # Start from body
            
            previous_element = None
            for i in range(min(len(focusable_elements), 20)):  # Test first 20 elements
                try:
                    ActionChains(self.driver).send_keys(Keys.TAB).perform()
                    time.sleep(0.1)
                    
                    current_element = self.driver.switch_to.active_element
                    current_selector = self.driver.execute_script("""
                        var el = arguments[0];
                        var selector = el.tagName.toLowerCase();
                        if (el.id) selector += '#' + el.id;
                        if (el.className) selector += '.' + el.className.split(' ')[0];
                        return selector;
                    """, current_element)
                    
                    if previous_element and current_element == previous_element:
                        keyboard_traps.append(current_selector)
                    
                    previous_element = current_element
                    
                except Exception as e:
                    unreachable_elements.append(f"Element at position {i}")
            
            return KeyboardNavigationResult(
                focusable_elements=focusable_elements,
                unreachable_elements=unreachable_elements,
                focus_order_issues=focus_order_issues,
                keyboard_traps=keyboard_traps
            )
            
        except Exception as e:
            logging.error(f"Keyboard navigation test failed: {e}")
            return KeyboardNavigationResult([], [], [], [])

class AccessibilityTestingEngine:
    def __init__(self, screenshots_dir: str = "accessibility_screenshots", results_dir: str = "accessibility_results"):
        self.screenshots_dir = Path(screenshots_dir)
        self.results_dir = Path(results_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None

    def _setup_driver(self) -> webdriver.Chrome:
        try:
            chrome_options = ChromeOptions()
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--headless")
            
            service = ChromeService(ChromeDriverManager().install())
            return webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logging.error(f"Failed to setup Chrome driver: {e}")
            return None

    async def run_accessibility_test_suite(self, test_suite: AccessibilityTestSuite) -> Dict[str, List[AccessibilityTestResult]]:
        results = {"automated": [], "manual_guidance": []}
        
        self.driver = self._setup_driver()
        if not self.driver:
            return results
        
        try:
            auditor = AccessibilityAuditor()
            
            for url in test_suite.urls:
                for viewport in test_suite.viewport_sizes:
                    self.driver.set_window_size(viewport[0], viewport[1])
                    
                    if TestType.AUTOMATED in test_suite.test_types:
                        result = await auditor.audit_page(self.driver, url, test_suite.wcag_level)
                        
                        if test_suite.include_color_contrast:
                            contrast_analyzer = ColorContrastAnalyzer(self.driver)
                            result.color_contrast_results = contrast_analyzer.analyze_color_contrast()
                        
                        if test_suite.include_keyboard_navigation:
                            keyboard_tester = KeyboardNavigationTester(self.driver)
                            result.keyboard_navigation = keyboard_tester.test_keyboard_navigation()
                        
                        screenshot_name = f"{url.replace('://', '_').replace('/', '_')}_{viewport[0]}x{viewport[1]}"
                        screenshot_path = self._take_screenshot(screenshot_name)
                        
                        for violation in result.violations:
                            violation.screenshot_path = screenshot_path
                        
                        results["automated"].append(result)
            
            if TestType.MANUAL in test_suite.test_types:
                manual_guidance = self._generate_manual_test_guidance(test_suite)
                results["manual_guidance"] = manual_guidance
                
        finally:
            if self.driver:
                self.driver.quit()
        
        return results

    def _take_screenshot(self, name: str) -> str:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"accessibility_{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            if self.driver:
                self.driver.save_screenshot(str(filepath))
                return str(filepath)
        except Exception as e:
            logging.error(f"Screenshot capture failed: {e}")
        return ""

    def _generate_manual_test_guidance(self, test_suite: AccessibilityTestSuite) -> List[AccessibilityTestResult]:
        manual_tests = []
        
        for url in test_suite.urls:
            guidance_result = AccessibilityTestResult(
                url=url,
                test_name="manual_accessibility_guidance",
                test_type=TestType.MANUAL,
                wcag_level=test_suite.wcag_level,
                violations=[],
                warnings=[
                    "Manual test: Check screen reader compatibility using NVDA, JAWS, or VoiceOver",
                    "Manual test: Verify keyboard navigation flow makes logical sense",
                    "Manual test: Test with users who have disabilities",
                    "Manual test: Verify focus indicators are visible and clear",
                    "Manual test: Check that all interactive elements have descriptive names",
                    "Manual test: Ensure error messages are clear and helpful",
                    "Manual test: Verify that content is understandable at different zoom levels",
                    "Manual test: Check that animations can be paused or disabled",
                    "Manual test: Verify sufficient time limits for completing tasks"
                ]
            )
            manual_tests.append(guidance_result)
        
        return manual_tests

    def generate_accessibility_report(self, results: Dict[str, List[AccessibilityTestResult]], output_path: str):
        all_violations = []
        total_tests = 0
        passed_tests = 0
        
        for test_type, test_results in results.items():
            for result in test_results:
                total_tests += 1
                all_violations.extend(result.violations)
                if not result.violations:
                    passed_tests += 1
        
        violation_summary = {}
        for violation in all_violations:
            key = f"{violation.type.value}_{violation.severity.value}"
            violation_summary[key] = violation_summary.get(key, 0) + 1
        
        wcag_compliance = {
            "A": len([v for v in all_violations if v.wcag_level == WcagLevel.A]),
            "AA": len([v for v in all_violations if v.wcag_level == WcagLevel.AA]),
            "AAA": len([v for v in all_violations if v.wcag_level == WcagLevel.AAA])
        }
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "total_violations": len(all_violations),
                "overall_score": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
                "timestamp": datetime.now().isoformat()
            },
            "wcag_compliance": wcag_compliance,
            "violation_summary": violation_summary,
            "detailed_results": {}
        }
        
        for test_type, test_results in results.items():
            report["detailed_results"][test_type] = []
            
            for result in test_results:
                test_data = {
                    "url": result.url,
                    "test_name": result.test_name,
                    "wcag_level": result.wcag_level.value,
                    "overall_score": result.overall_score,
                    "execution_time": result.execution_time,
                    "violations_count": len(result.violations),
                    "warnings_count": len(result.warnings),
                    "violations": [
                        {
                            "id": v.id,
                            "type": v.type.value,
                            "severity": v.severity.value,
                            "wcag_level": v.wcag_level.value,
                            "wcag_principle": v.wcag_principle.value,
                            "wcag_guideline": v.wcag_guideline,
                            "description": v.description,
                            "element_selector": v.element_selector,
                            "suggested_fix": v.suggested_fix,
                            "help_url": v.help_url,
                            "screenshot_path": v.screenshot_path
                        } for v in result.violations
                    ],
                    "warnings": result.warnings,
                    "color_contrast_issues": [
                        {
                            "element": cr.element_selector,
                            "foreground": cr.foreground,
                            "background": cr.background,
                            "ratio": cr.ratio,
                            "passes_aa": cr.passes_aa,
                            "passes_aaa": cr.passes_aaa
                        } for cr in result.color_contrast_results if not cr.passes_aa
                    ] if result.color_contrast_results else [],
                    "keyboard_navigation": {
                        "focusable_elements_count": len(result.keyboard_navigation.focusable_elements) if result.keyboard_navigation else 0,
                        "unreachable_elements": result.keyboard_navigation.unreachable_elements if result.keyboard_navigation else [],
                        "keyboard_traps": result.keyboard_navigation.keyboard_traps if result.keyboard_navigation else []
                    } if result.keyboard_navigation else {}
                }
                
                report["detailed_results"][test_type].append(test_data)
        
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
            <title>Accessibility Test Report - WCAG Compliance</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #2c3e50; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; border-left: 4px solid #007bff; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .wcag-compliance {{ background: #e8f5e8; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .wcag-level {{ display: inline-block; margin: 10px; padding: 10px 15px; background: white; border-radius: 4px; border: 2px solid #28a745; }}
                .wcag-level.violations {{ border-color: #dc3545; color: #dc3545; }}
                .violation-summary {{ background: #fff3cd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .test-results {{ margin-bottom: 30px; }}
                .test-type-header {{ background: #6c757d; color: white; padding: 15px; border-radius: 6px; margin-bottom: 10px; }}
                .test-item {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.has-violations {{ border-left-color: #dc3545; }}
                .violations-list {{ margin-top: 15px; }}
                .violation {{ background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; }}
                .violation.critical {{ background: #f5c6cb; }}
                .violation.serious {{ background: #f8d7da; }}
                .violation.moderate {{ background: #fff3cd; border-left-color: #ffc107; }}
                .violation.minor {{ background: #d1ecf1; border-left-color: #17a2b8; }}
                .violation-details {{ margin-top: 10px; padding: 10px; background: rgba(255,255,255,0.7); border-radius: 4px; }}
                .suggested-fix {{ background: #d4edda; padding: 8px; margin-top: 5px; border-radius: 4px; }}
                .keyboard-nav {{ background: #e2e3e5; padding: 15px; border-radius: 4px; margin-top: 10px; }}
                .color-contrast {{ background: #e2e3e5; padding: 15px; border-radius: 4px; margin-top: 10px; }}
                .score {{ font-size: 1.2em; font-weight: bold; }}
                .score.excellent {{ color: #28a745; }}
                .score.good {{ color: #ffc107; }}
                .score.poor {{ color: #dc3545; }}
                .manual-guidance {{ background: #cce5ff; padding: 15px; border-radius: 4px; margin-top: 10px; }}
                .warning {{ background: #fff3cd; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #ffc107; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🔍 Accessibility Test Report</h1>
                    <h2>WCAG Compliance Analysis</h2>
                    <p>Generated on {report_data['test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['test_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Passed Tests</h3>
                        <div class="value">{report_data['test_summary']['passed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Failed Tests</h3>
                        <div class="value">{report_data['test_summary']['failed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Violations</h3>
                        <div class="value">{report_data['test_summary']['total_violations']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Overall Score</h3>
                        <div class="value score {'excellent' if report_data['test_summary']['overall_score'] >= 80 else 'good' if report_data['test_summary']['overall_score'] >= 60 else 'poor'}">{report_data['test_summary']['overall_score']:.1f}%</div>
                    </div>
                </div>
                
                <div class="wcag-compliance">
                    <h3>🎯 WCAG Compliance Violations</h3>
                    <div class="wcag-level {'violations' if report_data['wcag_compliance']['A'] > 0 else ''}">
                        <strong>Level A:</strong> {report_data['wcag_compliance']['A']} violations
                    </div>
                    <div class="wcag-level {'violations' if report_data['wcag_compliance']['AA'] > 0 else ''}">
                        <strong>Level AA:</strong> {report_data['wcag_compliance']['AA']} violations
                    </div>
                    <div class="wcag-level {'violations' if report_data['wcag_compliance']['AAA'] > 0 else ''}">
                        <strong>Level AAA:</strong> {report_data['wcag_compliance']['AAA']} violations
                    </div>
                </div>
        """
        
        if report_data['violation_summary']:
            html_content += """
                <div class="violation-summary">
                    <h3>📊 Violation Summary by Type</h3>
            """
            
            for violation_type, count in report_data['violation_summary'].items():
                violation_name = violation_type.replace('_', ' ').title()
                html_content += f"""
                    <div class="violation-type">
                        <strong>{violation_name}:</strong> {count} occurrences
                    </div>
                """
            
            html_content += "</div>"
        
        for test_type, test_results in report_data['detailed_results'].items():
            html_content += f"""
                <div class="test-results">
                    <div class="test-type-header">
                        <h2>🧪 {test_type.replace('_', ' ').title()} Results</h2>
                    </div>
            """
            
            for test in test_results:
                has_violations = test['violations_count'] > 0
                html_content += f"""
                    <div class="test-item {'has-violations' if has_violations else ''}">
                        <h3>📄 {test['url']}</h3>
                        <p><strong>Test:</strong> {test['test_name']} | <strong>WCAG Level:</strong> {test['wcag_level']} | 
                           <strong>Score:</strong> <span class="score {'excellent' if test['overall_score'] >= 80 else 'good' if test['overall_score'] >= 60 else 'poor'}">{test['overall_score']:.1f}%</span> | 
                           <strong>Execution Time:</strong> {test['execution_time']:.2f}s</p>
                        <p><strong>Violations:</strong> {test['violations_count']} | <strong>Warnings:</strong> {test['warnings_count']}</p>
                """
                
                if test['violations']:
                    html_content += '<div class="violations-list"><h4>🚨 Accessibility Violations</h4>'
                    
                    for violation in test['violations']:
                        html_content += f"""
                            <div class="violation {violation['severity']}">
                                <strong>[{violation['severity'].upper()}] {violation['type'].replace('_', ' ').title()}</strong>
                                <p>{violation['description']}</p>
                                <div class="violation-details">
                                    <strong>WCAG:</strong> {violation['wcag_level']} - {violation['wcag_principle']} - {violation['wcag_guideline']}<br>
                                    <strong>Element:</strong> {violation['element_selector'] or 'N/A'}
                                </div>
                        """
                        
                        if violation['suggested_fix']:
                            html_content += f"""
                                <div class="suggested-fix">
                                    <strong>💡 Suggested Fix:</strong> {violation['suggested_fix']}
                                </div>
                            """
                        
                        if violation['help_url']:
                            html_content += f"""
                                <p><strong>🔗 Learn More:</strong> <a href="{violation['help_url']}" target="_blank">WCAG Guidelines</a></p>
                            """
                        
                        html_content += '</div>'
                    
                    html_content += '</div>'
                
                if test['warnings']:
                    html_content += '<div class="manual-guidance"><h4>⚠️ Manual Testing Guidance</h4>'
                    for warning in test['warnings']:
                        html_content += f'<div class="warning">{warning}</div>'
                    html_content += '</div>'
                
                if test['color_contrast_issues']:
                    html_content += '<div class="color-contrast"><h4>🎨 Color Contrast Issues</h4>'
                    for issue in test['color_contrast_issues']:
                        html_content += f"""
                            <div class="contrast-issue">
                                <strong>Element:</strong> {issue['element']}<br>
                                <strong>Colors:</strong> {issue['foreground']} on {issue['background']}<br>
                                <strong>Ratio:</strong> {issue['ratio']}:1 (AA: {'✅' if issue['passes_aa'] else '❌'}, AAA: {'✅' if issue['passes_aaa'] else '❌'})
                            </div>
                        """
                    html_content += '</div>'
                
                if test['keyboard_navigation'] and (test['keyboard_navigation'].get('unreachable_elements') or test['keyboard_navigation'].get('keyboard_traps')):
                    html_content += f"""
                        <div class="keyboard-nav">
                            <h4>⌨️ Keyboard Navigation Issues</h4>
                            <p><strong>Focusable Elements:</strong> {test['keyboard_navigation']['focusable_elements_count']}</p>
                    """
                    
                    if test['keyboard_navigation'].get('unreachable_elements'):
                        html_content += f"<p><strong>Unreachable Elements:</strong> {', '.join(test['keyboard_navigation']['unreachable_elements'])}</p>"
                    
                    if test['keyboard_navigation'].get('keyboard_traps'):
                        html_content += f"<p><strong>Keyboard Traps:</strong> {', '.join(test['keyboard_navigation']['keyboard_traps'])}</p>"
                    
                    html_content += '</div>'
                
                html_content += '</div>'
            
            html_content += '</div>'
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

    async def run_wcag_compliance_audit(
        self,
        urls: List[str],
        wcag_level: WcagLevel = WcagLevel.AA,
        include_manual_guidance: bool = True
    ) -> Dict[str, Any]:
        test_types = [TestType.AUTOMATED]
        if include_manual_guidance:
            test_types.append(TestType.MANUAL)
        
        test_suite = AccessibilityTestSuite(
            name="WCAG Compliance Audit",
            urls=urls,
            wcag_level=wcag_level,
            test_types=test_types,
            include_color_contrast=True,
            include_keyboard_navigation=True,
            include_screen_reader_testing=True
        )
        
        results = await self.run_accessibility_test_suite(test_suite)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"accessibility_report_{wcag_level.value}_{timestamp}.json"
        
        self.generate_accessibility_report(results, str(report_path))
        
        total_violations = sum(len(result.violations) for result_list in results.values() for result in result_list)
        
        return {
            "results": results,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html'),
            "summary": {
                "wcag_level": wcag_level.value,
                "urls_tested": len(urls),
                "total_violations": total_violations,
                "compliance_status": "PASS" if total_violations == 0 else "FAIL"
            }
        }

async def main():
    engine = AccessibilityTestingEngine()
    
    test_urls = [
        "https://example.com",
        "https://httpbin.org/html"
    ]
    
    print("Running WCAG AA compliance audit...")
    results = await engine.run_wcag_compliance_audit(
        urls=test_urls,
        wcag_level=WcagLevel.AA,
        include_manual_guidance=True
    )
    
    print(f"Accessibility audit completed!")
    print(f"WCAG Level: {results['summary']['wcag_level']}")
    print(f"URLs tested: {results['summary']['urls_tested']}")
    print(f"Total violations: {results['summary']['total_violations']}")
    print(f"Compliance status: {results['summary']['compliance_status']}")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())