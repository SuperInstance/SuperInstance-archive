#!/usr/bin/env python3
"""
Payment Flow Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive payment processing testing including
credit card transactions, subscription billing, refunds, fraud detection,
and PCI compliance validation.
"""

import asyncio
import json
import time
import random
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import logging
from pathlib import Path
import hashlib
import hmac
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor
import re

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.common.exceptions import WebDriverException, TimeoutException, NoSuchElementException
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Selenium and webdriver-manager required: pip install selenium webdriver-manager")

class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"
    BANK_TRANSFER = "bank_transfer"
    CRYPTOCURRENCY = "cryptocurrency"
    GIFT_CARD = "gift_card"

class PaymentProvider(Enum):
    STRIPE = "stripe"
    PAYPAL = "paypal"
    SQUARE = "square"
    BRAINTREE = "braintree"
    AUTHORIZE_NET = "authorize_net"
    ADYEN = "adyen"
    MOCK = "mock"

class TransactionType(Enum):
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"
    REFUND = "refund"
    PARTIAL_REFUND = "partial_refund"
    AUTHORIZATION = "authorization"
    CAPTURE = "capture"
    VOID = "void"
    RECURRING = "recurring"

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DECLINED = "declined"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"

class ErrorType(Enum):
    CARD_DECLINED = "card_declined"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    EXPIRED_CARD = "expired_card"
    INVALID_CVV = "invalid_cvv"
    FRAUD_DETECTED = "fraud_detected"
    PROCESSING_ERROR = "processing_error"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"

class TestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class PaymentCard:
    number: str
    expiry_month: str
    expiry_year: str
    cvv: str
    cardholder_name: str
    card_type: str = "visa"
    billing_address: Optional[Dict[str, str]] = None
    
    def get_masked_number(self) -> str:
        return f"****-****-****-{self.number[-4:]}"

@dataclass
class PaymentDetails:
    amount: Decimal
    currency: str
    description: str
    payment_method: PaymentMethod
    payment_card: Optional[PaymentCard] = None
    billing_address: Optional[Dict[str, str]] = None
    shipping_address: Optional[Dict[str, str]] = None
    customer_info: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PaymentResult:
    transaction_id: str
    status: PaymentStatus
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    provider_response: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PaymentTestCase:
    id: str
    name: str
    description: str
    payment_details: PaymentDetails
    expected_status: PaymentStatus
    expected_error_type: Optional[ErrorType] = None
    test_scenario: str = ""
    severity: TestSeverity = TestSeverity.MEDIUM
    timeout: int = 30

@dataclass
class PaymentFlowResult:
    test_case_id: str
    test_name: str
    status: str
    payment_result: Optional[PaymentResult] = None
    ui_validation_errors: List[str] = field(default_factory=list)
    security_issues: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    screenshots: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    error_details: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class PaymentFormValidator:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def validate_payment_form(self, form_selector: str = "form") -> Dict[str, List[str]]:
        validation_results = {
            "missing_fields": [],
            "insecure_fields": [],
            "validation_errors": [],
            "accessibility_issues": []
        }
        
        try:
            form_element = self.driver.find_element(By.CSS_SELECTOR, form_selector)
            
            required_fields = [
                ("card_number", "input[name*='card'], input[id*='card'], input[placeholder*='card']"),
                ("expiry", "input[name*='exp'], input[id*='exp'], input[placeholder*='exp']"),
                ("cvv", "input[name*='cvv'], input[id*='cvv'], input[name*='cvc'], input[placeholder*='cvv']"),
                ("name", "input[name*='name'], input[id*='name'], input[placeholder*='name']")
            ]
            
            for field_name, selector in required_fields:
                try:
                    field = form_element.find_element(By.CSS_SELECTOR, selector)
                    
                    if not field.get_attribute("required") and field_name in ["card_number", "expiry", "cvv"]:
                        validation_results["validation_errors"].append(f"{field_name} field should be required")
                    
                    if field_name == "card_number" and field.get_attribute("type") != "password":
                        validation_results["insecure_fields"].append(f"{field_name} field should have type='password' or be tokenized")
                    
                    if not field.get_attribute("autocomplete"):
                        validation_results["accessibility_issues"].append(f"{field_name} field missing autocomplete attribute")
                    
                except NoSuchElementException:
                    validation_results["missing_fields"].append(field_name)
            
            ssl_check = self.driver.execute_script("return location.protocol === 'https:';")
            if not ssl_check:
                validation_results["insecure_fields"].append("Payment form not served over HTTPS")
            
        except NoSuchElementException:
            validation_results["validation_errors"].append("Payment form not found")
        except Exception as e:
            validation_results["validation_errors"].append(f"Form validation error: {str(e)}")
        
        return validation_results

    def check_pci_compliance(self) -> List[str]:
        compliance_issues = []
        
        try:
            card_fields = self.driver.find_elements(By.CSS_SELECTOR, 
                "input[name*='card'], input[id*='card'], input[placeholder*='card']")
            
            for field in card_fields:
                autocomplete = field.get_attribute("autocomplete")
                if autocomplete and "cc-" not in autocomplete:
                    compliance_issues.append("Card number field should use autocomplete='cc-number'")
                
                if field.get_attribute("type") not in ["password", "tel"]:
                    compliance_issues.append("Card number field should not store plaintext")
            
            iframe_count = len(self.driver.find_elements(By.TAG_NAME, "iframe"))
            if iframe_count == 0:
                compliance_issues.append("No secure payment iframe detected - potential PCI DSS violation")
            
        except Exception as e:
            compliance_issues.append(f"PCI compliance check failed: {str(e)}")
        
        return compliance_issues

class PaymentProvider_Mock:
    def __init__(self):
        self.success_rate = 0.85
        self.processing_delay = (0.5, 3.0)
        
        self.test_cards = {
            "4111111111111111": {"status": "success", "type": "visa"},
            "4000000000000002": {"status": "declined", "type": "visa"},
            "4000000000000069": {"status": "expired", "type": "visa"},
            "4000000000000127": {"status": "insufficient_funds", "type": "visa"},
            "4000000000000119": {"status": "fraud", "type": "visa"},
            "5555555555554444": {"status": "success", "type": "mastercard"},
            "2223003122003222": {"status": "success", "type": "mastercard"},
            "378282246310005": {"status": "success", "type": "amex"}
        }

    async def process_payment(self, payment_details: PaymentDetails) -> PaymentResult:
        start_time = time.time()
        
        await asyncio.sleep(random.uniform(*self.processing_delay))
        
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"
        
        if payment_details.payment_card:
            card_number = payment_details.payment_card.number.replace(" ", "")
            card_config = self.test_cards.get(card_number, {"status": "success"})
            
            if card_config["status"] == "success":
                status = PaymentStatus.COMPLETED
                error_code = None
                error_message = None
            elif card_config["status"] == "declined":
                status = PaymentStatus.DECLINED
                error_code = "card_declined"
                error_message = "Your card was declined"
            elif card_config["status"] == "expired":
                status = PaymentStatus.FAILED
                error_code = "expired_card"
                error_message = "Your card has expired"
            elif card_config["status"] == "insufficient_funds":
                status = PaymentStatus.FAILED
                error_code = "insufficient_funds"
                error_message = "Insufficient funds"
            elif card_config["status"] == "fraud":
                status = PaymentStatus.FAILED
                error_code = "fraud_detected"
                error_message = "Transaction flagged as potentially fraudulent"
            else:
                status = PaymentStatus.FAILED
                error_code = "processing_error"
                error_message = "Unable to process payment"
        else:
            if random.random() < self.success_rate:
                status = PaymentStatus.COMPLETED
                error_code = None
                error_message = None
            else:
                status = PaymentStatus.FAILED
                error_code = "processing_error"
                error_message = "Payment processing failed"
        
        processing_time = time.time() - start_time
        
        return PaymentResult(
            transaction_id=transaction_id,
            status=status,
            amount=payment_details.amount,
            currency=payment_details.currency,
            payment_method=payment_details.payment_method,
            error_code=error_code,
            error_message=error_message,
            processing_time=processing_time,
            provider_response={
                "provider": "mock",
                "transaction_id": transaction_id,
                "processing_time": processing_time
            }
        )

class PaymentUIAutomator:
    def __init__(self, driver: webdriver.Remote):
        self.driver = driver

    def fill_payment_form(self, payment_details: PaymentDetails, form_selectors: Dict[str, str] = None) -> bool:
        try:
            if not form_selectors:
                form_selectors = {
                    "card_number": "input[name*='card'], input[id*='card'], #card-number",
                    "expiry_month": "select[name*='month'], #exp-month",
                    "expiry_year": "select[name*='year'], #exp-year",
                    "cvv": "input[name*='cvv'], input[name*='cvc'], #cvv",
                    "cardholder_name": "input[name*='name'], #cardholder-name",
                    "amount": "input[name*='amount'], #amount"
                }
            
            if payment_details.payment_card:
                card_number_field = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, form_selectors["card_number"]))
                )
                card_number_field.clear()
                card_number_field.send_keys(payment_details.payment_card.number)
                
                try:
                    expiry_month_select = Select(self.driver.find_element(By.CSS_SELECTOR, form_selectors["expiry_month"]))
                    expiry_month_select.select_by_value(payment_details.payment_card.expiry_month)
                    
                    expiry_year_select = Select(self.driver.find_element(By.CSS_SELECTOR, form_selectors["expiry_year"]))
                    expiry_year_select.select_by_value(payment_details.payment_card.expiry_year)
                except NoSuchElementException:
                    expiry_field = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='MM/YY'], input[placeholder*='expiry']")
                    expiry_field.clear()
                    expiry_field.send_keys(f"{payment_details.payment_card.expiry_month}/{payment_details.payment_card.expiry_year}")
                
                cvv_field = self.driver.find_element(By.CSS_SELECTOR, form_selectors["cvv"])
                cvv_field.clear()
                cvv_field.send_keys(payment_details.payment_card.cvv)
                
                name_field = self.driver.find_element(By.CSS_SELECTOR, form_selectors["cardholder_name"])
                name_field.clear()
                name_field.send_keys(payment_details.payment_card.cardholder_name)
            
            try:
                amount_field = self.driver.find_element(By.CSS_SELECTOR, form_selectors["amount"])
                amount_field.clear()
                amount_field.send_keys(str(payment_details.amount))
            except NoSuchElementException:
                pass  # Amount might be pre-filled
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to fill payment form: {e}")
            return False

    def submit_payment_form(self, submit_selector: str = "button[type='submit'], input[type='submit'], .pay-button") -> bool:
        try:
            submit_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, submit_selector))
            )
            submit_button.click()
            return True
        except Exception as e:
            logging.error(f"Failed to submit payment form: {e}")
            return False

    def wait_for_payment_result(self, success_selector: str = ".success, .payment-complete", 
                              error_selector: str = ".error, .payment-failed", 
                              timeout: int = 30) -> Tuple[bool, str]:
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.find_elements(By.CSS_SELECTOR, success_selector) or 
                         d.find_elements(By.CSS_SELECTOR, error_selector)
            )
            
            if self.driver.find_elements(By.CSS_SELECTOR, success_selector):
                return True, "Payment completed successfully"
            elif self.driver.find_elements(By.CSS_SELECTOR, error_selector):
                error_element = self.driver.find_element(By.CSS_SELECTOR, error_selector)
                return False, error_element.text
            
        except TimeoutException:
            return False, "Payment processing timeout"
        except Exception as e:
            return False, f"Payment result check failed: {str(e)}"
        
        return False, "Unknown payment result"

class PaymentFlowTestingEngine:
    def __init__(self, screenshots_dir: str = "payment_screenshots", results_dir: str = "payment_results"):
        self.screenshots_dir = Path(screenshots_dir)
        self.results_dir = Path(results_dir)
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.payment_provider = PaymentProvider_Mock()
        self.test_cases = self._create_test_cases()

    def _create_test_cases(self) -> List[PaymentTestCase]:
        test_cases = []
        
        test_cards = [
            PaymentCard("4111111111111111", "12", "2025", "123", "John Doe", "visa"),
            PaymentCard("4000000000000002", "12", "2025", "123", "Jane Smith", "visa"),  # Declined
            PaymentCard("4000000000000069", "12", "2020", "123", "Bob Johnson", "visa"),  # Expired
            PaymentCard("4000000000000127", "12", "2025", "123", "Alice Brown", "visa"),  # Insufficient funds
            PaymentCard("5555555555554444", "12", "2025", "123", "Charlie Wilson", "mastercard"),
        ]
        
        amounts = [Decimal("10.00"), Decimal("99.99"), Decimal("1.00"), Decimal("999.99")]
        
        for i, card in enumerate(test_cards):
            for j, amount in enumerate(amounts):
                if "000000000002" in card.number:
                    expected_status = PaymentStatus.DECLINED
                    expected_error = ErrorType.CARD_DECLINED
                    scenario = "declined_card_test"
                elif "000000000069" in card.number:
                    expected_status = PaymentStatus.FAILED
                    expected_error = ErrorType.EXPIRED_CARD
                    scenario = "expired_card_test"
                elif "000000000127" in card.number:
                    expected_status = PaymentStatus.FAILED
                    expected_error = ErrorType.INSUFFICIENT_FUNDS
                    scenario = "insufficient_funds_test"
                else:
                    expected_status = PaymentStatus.COMPLETED
                    expected_error = None
                    scenario = "successful_payment_test"
                
                test_case = PaymentTestCase(
                    id=f"test_{i}_{j}",
                    name=f"Payment test {card.card_type} ${amount}",
                    description=f"Test {scenario} with {card.card_type} card for ${amount}",
                    payment_details=PaymentDetails(
                        amount=amount,
                        currency="USD",
                        description=f"Test payment ${amount}",
                        payment_method=PaymentMethod.CREDIT_CARD,
                        payment_card=card
                    ),
                    expected_status=expected_status,
                    expected_error_type=expected_error,
                    test_scenario=scenario,
                    severity=TestSeverity.HIGH if expected_error else TestSeverity.MEDIUM
                )
                test_cases.append(test_case)
        
        subscription_test = PaymentTestCase(
            id="subscription_test",
            name="Recurring subscription payment",
            description="Test recurring monthly subscription",
            payment_details=PaymentDetails(
                amount=Decimal("29.99"),
                currency="USD", 
                description="Monthly subscription",
                payment_method=PaymentMethod.CREDIT_CARD,
                payment_card=PaymentCard("4111111111111111", "12", "2025", "123", "John Doe", "visa"),
                metadata={"subscription": True, "interval": "monthly"}
            ),
            expected_status=PaymentStatus.COMPLETED,
            test_scenario="subscription_test",
            severity=TestSeverity.CRITICAL
        )
        test_cases.append(subscription_test)
        
        return test_cases

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

    async def run_payment_flow_test(self, test_case: PaymentTestCase, payment_page_url: str) -> PaymentFlowResult:
        start_time = time.time()
        result = PaymentFlowResult(
            test_case_id=test_case.id,
            test_name=test_case.name,
            status="pending"
        )
        
        driver = self._setup_driver()
        if not driver:
            result.status = "failed"
            result.error_details = "Failed to initialize web driver"
            return result
        
        try:
            driver.get(payment_page_url)
            
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            screenshot_path = self._take_screenshot(driver, f"{test_case.id}_initial")
            result.screenshots.append(screenshot_path)
            
            form_validator = PaymentFormValidator(driver)
            validation_results = form_validator.validate_payment_form()
            
            for field_type, issues in validation_results.items():
                if issues:
                    result.ui_validation_errors.extend(issues)
            
            pci_issues = form_validator.check_pci_compliance()
            result.security_issues.extend(pci_issues)
            
            ui_automator = PaymentUIAutomator(driver)
            
            form_fill_start = time.time()
            form_filled = ui_automator.fill_payment_form(test_case.payment_details)
            form_fill_time = time.time() - form_fill_start
            result.performance_metrics["form_fill_time"] = form_fill_time
            
            if not form_filled:
                result.status = "failed"
                result.error_details = "Failed to fill payment form"
                return result
            
            screenshot_path = self._take_screenshot(driver, f"{test_case.id}_filled")
            result.screenshots.append(screenshot_path)
            
            submit_start = time.time()
            form_submitted = ui_automator.submit_payment_form()
            
            if not form_submitted:
                result.status = "failed"
                result.error_details = "Failed to submit payment form"
                return result
            
            payment_success, payment_message = ui_automator.wait_for_payment_result(timeout=test_case.timeout)
            submit_time = time.time() - submit_start
            result.performance_metrics["payment_processing_time"] = submit_time
            
            screenshot_path = self._take_screenshot(driver, f"{test_case.id}_result")
            result.screenshots.append(screenshot_path)
            
            payment_result = await self.payment_provider.process_payment(test_case.payment_details)
            result.payment_result = payment_result
            
            if payment_success and payment_result.status == PaymentStatus.COMPLETED:
                if test_case.expected_status == PaymentStatus.COMPLETED:
                    result.status = "passed"
                else:
                    result.status = "failed"
                    result.error_details = f"Expected {test_case.expected_status.value} but got {payment_result.status.value}"
            elif not payment_success:
                if test_case.expected_status in [PaymentStatus.FAILED, PaymentStatus.DECLINED]:
                    result.status = "passed"
                else:
                    result.status = "failed"
                    result.error_details = f"Payment failed unexpectedly: {payment_message}"
            else:
                result.status = "failed"
                result.error_details = f"Unexpected payment result: {payment_message}"
            
        except Exception as e:
            result.status = "failed"
            result.error_details = f"Test execution error: {str(e)}"
            screenshot_path = self._take_screenshot(driver, f"{test_case.id}_error")
            result.screenshots.append(screenshot_path)
        
        finally:
            driver.quit()
            result.execution_time = time.time() - start_time
        
        return result

    def _take_screenshot(self, driver: webdriver.Remote, name: str) -> str:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"payment_{name}_{timestamp}.png"
            filepath = self.screenshots_dir / filename
            
            driver.save_screenshot(str(filepath))
            return str(filepath)
        except Exception as e:
            logging.error(f"Screenshot capture failed: {e}")
            return ""

    async def run_payment_test_suite(self, payment_page_url: str, test_case_ids: List[str] = None) -> Dict[str, Any]:
        test_cases_to_run = self.test_cases
        if test_case_ids:
            test_cases_to_run = [tc for tc in self.test_cases if tc.id in test_case_ids]
        
        results = []
        
        for test_case in test_cases_to_run:
            print(f"Running test case: {test_case.name}")
            result = await self.run_payment_flow_test(test_case, payment_page_url)
            results.append(result)
            
            await asyncio.sleep(1)
        
        return {
            "results": results,
            "summary": self._generate_test_summary(results)
        }

    def _generate_test_summary(self, results: List[PaymentFlowResult]) -> Dict[str, Any]:
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "passed"])
        failed_tests = len([r for r in results if r.status == "failed"])
        
        avg_execution_time = sum(r.execution_time for r in results) / total_tests if total_tests > 0 else 0
        avg_form_fill_time = sum(r.performance_metrics.get("form_fill_time", 0) for r in results) / total_tests if total_tests > 0 else 0
        avg_processing_time = sum(r.performance_metrics.get("payment_processing_time", 0) for r in results) / total_tests if total_tests > 0 else 0
        
        all_ui_errors = []
        all_security_issues = []
        
        for result in results:
            all_ui_errors.extend(result.ui_validation_errors)
            all_security_issues.extend(result.security_issues)
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "pass_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "average_execution_time": avg_execution_time,
            "average_form_fill_time": avg_form_fill_time,
            "average_processing_time": avg_processing_time,
            "unique_ui_errors": list(set(all_ui_errors)),
            "unique_security_issues": list(set(all_security_issues)),
            "total_ui_errors": len(all_ui_errors),
            "total_security_issues": len(all_security_issues)
        }

    def generate_payment_report(self, test_results: Dict[str, Any], output_path: str):
        results = test_results["results"]
        summary = test_results["summary"]
        
        report = {
            "test_summary": {
                "total_tests": summary["total_tests"],
                "passed_tests": summary["passed_tests"],
                "failed_tests": summary["failed_tests"],
                "pass_rate": summary["pass_rate"],
                "timestamp": datetime.now().isoformat()
            },
            "performance_metrics": {
                "average_execution_time": summary["average_execution_time"],
                "average_form_fill_time": summary["average_form_fill_time"],
                "average_processing_time": summary["average_processing_time"]
            },
            "security_analysis": {
                "ui_validation_errors": summary["unique_ui_errors"],
                "security_issues": summary["unique_security_issues"],
                "total_issues": summary["total_ui_errors"] + summary["total_security_issues"]
            },
            "test_results": []
        }
        
        for result in results:
            test_data = {
                "test_case_id": result.test_case_id,
                "test_name": result.test_name,
                "status": result.status,
                "execution_time": result.execution_time,
                "performance_metrics": result.performance_metrics,
                "ui_validation_errors": result.ui_validation_errors,
                "security_issues": result.security_issues,
                "screenshots": result.screenshots,
                "error_details": result.error_details,
                "payment_result": {
                    "transaction_id": result.payment_result.transaction_id if result.payment_result else None,
                    "status": result.payment_result.status.value if result.payment_result else None,
                    "amount": float(result.payment_result.amount) if result.payment_result else None,
                    "currency": result.payment_result.currency if result.payment_result else None,
                    "error_code": result.payment_result.error_code if result.payment_result else None,
                    "error_message": result.payment_result.error_message if result.payment_result else None,
                    "processing_time": result.payment_result.processing_time if result.payment_result else None
                } if result.payment_result else None
            }
            report["test_results"].append(test_data)
        
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
            <title>Payment Flow Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #28a745; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .pass-rate {{ color: #28a745; }}
                .fail-rate {{ color: #dc3545; }}
                .performance-section {{ background: #e3f2fd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .security-section {{ background: #fff3e0; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .test-results {{ margin-bottom: 30px; }}
                .test-item {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.failed {{ border-left-color: #dc3545; }}
                .test-item.pending {{ border-left-color: #ffc107; }}
                .test-details {{ margin-top: 10px; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
                .detail-section {{ background: white; padding: 10px; border-radius: 4px; }}
                .payment-result {{ background: #e8f5e8; padding: 10px; border-radius: 4px; }}
                .payment-result.failed {{ background: #f8d7da; }}
                .error-list {{ list-style-type: none; padding: 0; }}
                .error-item {{ background: #f8d7da; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; }}
                .security-item {{ background: #fff3cd; padding: 8px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #ffc107; }}
                .performance-metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
                .metric {{ background: white; padding: 8px; border-radius: 4px; text-align: center; }}
                .screenshots {{ display: flex; gap: 10px; flex-wrap: wrap; }}
                .screenshot {{ width: 150px; height: 100px; object-fit: cover; border-radius: 4px; border: 1px solid #ddd; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>💳 Payment Flow Test Report</h1>
                    <p>Comprehensive E2E Payment Testing Results</p>
                    <p>Generated on {report_data['test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['test_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Passed Tests</h3>
                        <div class="value pass-rate">{report_data['test_summary']['passed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Failed Tests</h3>
                        <div class="value fail-rate">{report_data['test_summary']['failed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Pass Rate</h3>
                        <div class="value {'pass-rate' if report_data['test_summary']['pass_rate'] >= 80 else 'fail-rate'}">{report_data['test_summary']['pass_rate']:.1f}%</div>
                    </div>
                </div>
                
                <div class="performance-section">
                    <h3>⚡ Performance Metrics</h3>
                    <div class="performance-metrics">
                        <div class="metric">
                            <strong>Avg Execution Time</strong><br>
                            {report_data['performance_metrics']['average_execution_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Avg Form Fill Time</strong><br>
                            {report_data['performance_metrics']['average_form_fill_time']:.2f}s
                        </div>
                        <div class="metric">
                            <strong>Avg Processing Time</strong><br>
                            {report_data['performance_metrics']['average_processing_time']:.2f}s
                        </div>
                    </div>
                </div>
                
                <div class="security-section">
                    <h3>🔒 Security Analysis</h3>
                    <p><strong>Total Security Issues Found:</strong> {report_data['security_analysis']['total_issues']}</p>
        """
        
        if report_data['security_analysis']['ui_validation_errors']:
            html_content += "<h4>UI Validation Errors:</h4><ul class='error-list'>"
            for error in report_data['security_analysis']['ui_validation_errors']:
                html_content += f"<li class='error-item'>{error}</li>"
            html_content += "</ul>"
        
        if report_data['security_analysis']['security_issues']:
            html_content += "<h4>Security Issues:</h4><ul class='error-list'>"
            for issue in report_data['security_analysis']['security_issues']:
                html_content += f"<li class='security-item'>{issue}</li>"
            html_content += "</ul>"
        
        html_content += """
                </div>
                
                <div class="test-results">
                    <h3>📊 Detailed Test Results</h3>
        """
        
        for test in report_data['test_results']:
            status_class = test['status']
            html_content += f"""
                    <div class="test-item {status_class}">
                        <h4>{test['test_name']} ({test['test_case_id']})</h4>
                        <p><strong>Status:</strong> {test['status'].upper()} | <strong>Execution Time:</strong> {test['execution_time']:.2f}s</p>
                        
                        <div class="test-details">
                            <div class="detail-section">
                                <h5>Performance Metrics</h5>
                                <div class="performance-metrics">
            """
            
            for metric, value in test['performance_metrics'].items():
                html_content += f"""
                                    <div class="metric">
                                        <strong>{metric.replace('_', ' ').title()}</strong><br>
                                        {value:.2f}s
                                    </div>
                """
            
            html_content += "</div></div>"
            
            if test['payment_result']:
                payment_status = test['payment_result']['status']
                result_class = 'failed' if payment_status in ['failed', 'declined'] else ''
                html_content += f"""
                            <div class="detail-section">
                                <h5>Payment Result</h5>
                                <div class="payment-result {result_class}">
                                    <strong>Transaction ID:</strong> {test['payment_result']['transaction_id'] or 'N/A'}<br>
                                    <strong>Status:</strong> {payment_status or 'N/A'}<br>
                                    <strong>Amount:</strong> ${test['payment_result']['amount'] or 0:.2f} {test['payment_result']['currency'] or 'USD'}<br>
                                    <strong>Processing Time:</strong> {test['payment_result']['processing_time'] or 0:.2f}s
                """
                
                if test['payment_result']['error_code']:
                    html_content += f"<br><strong>Error:</strong> {test['payment_result']['error_code']} - {test['payment_result']['error_message']}"
                
                html_content += "</div></div>"
            
            if test['ui_validation_errors']:
                html_content += """
                            <div class="detail-section">
                                <h5>UI Validation Errors</h5>
                                <ul class="error-list">
                """
                for error in test['ui_validation_errors']:
                    html_content += f"<li class='error-item'>{error}</li>"
                html_content += "</ul></div>"
            
            if test['security_issues']:
                html_content += """
                            <div class="detail-section">
                                <h5>Security Issues</h5>
                                <ul class="error-list">
                """
                for issue in test['security_issues']:
                    html_content += f"<li class='security-item'>{issue}</li>"
                html_content += "</ul></div>"
            
            if test['error_details']:
                html_content += f"""
                            <div class="detail-section">
                                <h5>Error Details</h5>
                                <div class="error-item">{test['error_details']}</div>
                            </div>
                """
            
            html_content += "</div></div>"
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

    async def run_comprehensive_payment_test(self, payment_page_url: str) -> Dict[str, Any]:
        print("Starting comprehensive payment flow testing...")
        
        test_results = await self.run_payment_test_suite(payment_page_url)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"payment_flow_report_{timestamp}.json"
        
        self.generate_payment_report(test_results, str(report_path))
        
        return {
            "test_results": test_results,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html'),
            "summary": test_results["summary"]
        }

async def main():
    engine = PaymentFlowTestingEngine()
    
    payment_page_url = "https://example.com/payment"
    
    print("Running comprehensive payment flow tests...")
    results = await engine.run_comprehensive_payment_test(payment_page_url)
    
    print(f"Payment flow testing completed!")
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed tests: {results['summary']['passed_tests']}")
    print(f"Failed tests: {results['summary']['failed_tests']}")
    print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")
    print(f"Average execution time: {results['summary']['average_execution_time']:.2f}s")
    print(f"UI errors found: {results['summary']['total_ui_errors']}")
    print(f"Security issues found: {results['summary']['total_security_issues']}")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())