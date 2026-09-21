#!/usr/bin/env python3

import asyncio
import aiohttp
import json
import time
import uuid
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import logging
from decimal import Decimal
import hashlib
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PaymentStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    CRYPTOCURRENCY = "cryptocurrency"
    ACTIVELOG_CREDITS = "activelog_credits"
    STRIPE = "stripe"
    PAYPAL = "paypal"

class TestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    TIMEOUT = "timeout"

@dataclass
class PaymentTransaction:
    id: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    merchant_id: str
    customer_id: str
    description: str
    status: PaymentStatus = PaymentStatus.PENDING
    created_at: datetime = None
    completed_at: datetime = None
    error_message: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}

@dataclass
class PaymentFlowTest:
    name: str
    description: str
    flow_type: str
    amount: Decimal
    currency: str
    payment_method: PaymentMethod
    expected_result: TestResult
    timeout_seconds: float = 30.0
    prerequisites: List[str] = None
    
    def __post_init__(self):
        if self.prerequisites is None:
            self.prerequisites = []

@dataclass
class PaymentTestResult:
    test_name: str
    transaction_id: str
    result: TestResult
    execution_time: float
    amount_processed: Decimal
    currency: str
    status_transitions: List[Tuple[PaymentStatus, datetime]]
    error_details: str = ""
    performance_metrics: Dict[str, Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.performance_metrics is None:
            self.performance_metrics = {}

@dataclass
class PaymentFlowReport:
    total_tests: int
    passed: int
    failed: int
    errors: int
    timeouts: int
    total_amount_tested: Decimal
    currencies_tested: List[str]
    payment_methods_tested: List[PaymentMethod]
    average_processing_time: float
    test_results: List[PaymentTestResult]
    critical_failures: List[PaymentTestResult]
    timestamp: datetime
    test_duration: float

class PaymentFlowTester:
    def __init__(self, audit_db_path: str = "audit_payment_flows.db"):
        self.audit_db_path = audit_db_path
        self.test_results: List[PaymentTestResult] = []
        self.active_transactions: Dict[str, PaymentTransaction] = {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.init_audit_database()
        self.setup_test_scenarios()

    def init_audit_database(self):
        """Initialize audit database for payment flow testing"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_flow_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            total_tests INTEGER NOT NULL,
            passed INTEGER NOT NULL,
            failed INTEGER NOT NULL,
            errors INTEGER NOT NULL,
            timeouts INTEGER NOT NULL,
            total_amount_tested REAL NOT NULL,
            currencies_tested TEXT NOT NULL,
            payment_methods_tested TEXT NOT NULL,
            average_processing_time REAL NOT NULL,
            test_duration REAL NOT NULL,
            timestamp DATETIME NOT NULL
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER,
            test_name TEXT NOT NULL,
            transaction_id TEXT NOT NULL,
            result TEXT NOT NULL,
            execution_time REAL NOT NULL,
            amount_processed REAL NOT NULL,
            currency TEXT NOT NULL,
            status_transitions TEXT,
            error_details TEXT,
            performance_metrics TEXT,
            timestamp DATETIME NOT NULL,
            FOREIGN KEY (report_id) REFERENCES payment_flow_reports (id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_transactions (
            id TEXT PRIMARY KEY,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            payment_method TEXT NOT NULL,
            merchant_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            completed_at DATETIME,
            error_message TEXT,
            metadata TEXT
        )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_test_results_timestamp ON payment_test_results(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_payment_transactions_status ON payment_transactions(status)')
        
        conn.commit()
        conn.close()

    def setup_test_scenarios(self):
        """Setup comprehensive payment flow test scenarios"""
        self.test_scenarios = [
            # Basic payment flows
            PaymentFlowTest(
                name="basic_credit_card_payment",
                description="Basic credit card payment processing",
                flow_type="standard_payment",
                amount=Decimal("29.99"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                expected_result=TestResult.PASS,
                timeout_seconds=15.0
            ),
            
            PaymentFlowTest(
                name="activelog_credits_payment",
                description="Payment using ActiveLog internal credits",
                flow_type="credits_payment",
                amount=Decimal("100.00"),
                currency="ALC",  # ActiveLog Credits
                payment_method=PaymentMethod.ACTIVELOG_CREDITS,
                expected_result=TestResult.PASS,
                timeout_seconds=5.0
            ),
            
            PaymentFlowTest(
                name="large_amount_payment",
                description="High value payment processing",
                flow_type="high_value_payment",
                amount=Decimal("5000.00"),
                currency="USD",
                payment_method=PaymentMethod.BANK_TRANSFER,
                expected_result=TestResult.PASS,
                timeout_seconds=60.0
            ),
            
            PaymentFlowTest(
                name="subscription_payment",
                description="Recurring subscription payment",
                flow_type="subscription",
                amount=Decimal("49.99"),
                currency="USD",
                payment_method=PaymentMethod.STRIPE,
                expected_result=TestResult.PASS,
                timeout_seconds=20.0,
                prerequisites=["stripe_integration_active"]
            ),
            
            PaymentFlowTest(
                name="marketplace_transaction",
                description="Marketplace seller payout flow",
                flow_type="marketplace_payout",
                amount=Decimal("250.00"),
                currency="USD",
                payment_method=PaymentMethod.PAYPAL,
                expected_result=TestResult.PASS,
                timeout_seconds=30.0
            ),
            
            PaymentFlowTest(
                name="cryptocurrency_payment",
                description="Cryptocurrency payment processing",
                flow_type="crypto_payment",
                amount=Decimal("0.001"),
                currency="BTC",
                payment_method=PaymentMethod.CRYPTOCURRENCY,
                expected_result=TestResult.PASS,
                timeout_seconds=45.0
            ),
            
            PaymentFlowTest(
                name="refund_processing",
                description="Payment refund flow",
                flow_type="refund",
                amount=Decimal("75.50"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                expected_result=TestResult.PASS,
                timeout_seconds=25.0,
                prerequisites=["original_payment_exists"]
            ),
            
            PaymentFlowTest(
                name="failed_payment_handling",
                description="Handling of intentionally failed payments",
                flow_type="failure_test",
                amount=Decimal("0.01"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                expected_result=TestResult.FAIL,
                timeout_seconds=10.0
            ),
            
            PaymentFlowTest(
                name="partial_payment",
                description="Partial payment processing",
                flow_type="partial_payment",
                amount=Decimal("150.00"),
                currency="USD",
                payment_method=PaymentMethod.CREDIT_CARD,
                expected_result=TestResult.PASS,
                timeout_seconds=20.0
            ),
            
            PaymentFlowTest(
                name="multi_currency_conversion",
                description="Multi-currency payment with conversion",
                flow_type="currency_conversion",
                amount=Decimal("100.00"),
                currency="EUR",
                payment_method=PaymentMethod.CREDIT_CARD,
                expected_result=TestResult.PASS,
                timeout_seconds=25.0
            )
        ]

    async def simulate_payment_gateway(self, transaction: PaymentTransaction) -> PaymentTestResult:
        """Simulate payment gateway processing"""
        start_time = time.time()
        status_transitions = [(transaction.status, datetime.now())]
        
        try:
            # Simulate payment processing delays
            if transaction.payment_method == PaymentMethod.CRYPTOCURRENCY:
                await asyncio.sleep(2.0)  # Crypto takes longer
            elif transaction.payment_method == PaymentMethod.BANK_TRANSFER:
                await asyncio.sleep(3.0)  # Bank transfers are slow
            else:
                await asyncio.sleep(0.5)  # Standard processing
            
            # Update status to processing
            transaction.status = PaymentStatus.PROCESSING
            status_transitions.append((transaction.status, datetime.now()))
            
            # Simulate additional processing time
            await asyncio.sleep(random.uniform(0.5, 2.0))
            
            # Determine outcome based on test conditions
            if "failure_test" in transaction.description.lower():
                transaction.status = PaymentStatus.FAILED
                transaction.error_message = "Simulated payment failure for testing"
                result = TestResult.FAIL
            elif transaction.amount > Decimal("10000"):
                transaction.status = PaymentStatus.FAILED
                transaction.error_message = "Amount exceeds processing limits"
                result = TestResult.FAIL
            elif transaction.currency not in ["USD", "EUR", "GBP", "ALC", "BTC"]:
                transaction.status = PaymentStatus.FAILED
                transaction.error_message = f"Unsupported currency: {transaction.currency}"
                result = TestResult.FAIL
            else:
                transaction.status = PaymentStatus.COMPLETED
                transaction.completed_at = datetime.now()
                result = TestResult.PASS
            
            status_transitions.append((transaction.status, datetime.now()))
            execution_time = time.time() - start_time
            
            # Calculate performance metrics
            performance_metrics = {
                "processing_latency": execution_time,
                "gateway_response_time": execution_time * 0.7,
                "validation_time": execution_time * 0.2,
                "settlement_time": execution_time * 0.1,
                "throughput_tps": 1 / execution_time if execution_time > 0 else 0
            }
            
            return PaymentTestResult(
                test_name=f"payment_{transaction.id[:8]}",
                transaction_id=transaction.id,
                result=result,
                execution_time=execution_time,
                amount_processed=transaction.amount,
                currency=transaction.currency,
                status_transitions=status_transitions,
                error_details=transaction.error_message,
                performance_metrics=performance_metrics
            )
            
        except asyncio.TimeoutError:
            transaction.status = PaymentStatus.FAILED
            transaction.error_message = "Payment processing timeout"
            status_transitions.append((transaction.status, datetime.now()))
            
            return PaymentTestResult(
                test_name=f"payment_{transaction.id[:8]}",
                transaction_id=transaction.id,
                result=TestResult.TIMEOUT,
                execution_time=time.time() - start_time,
                amount_processed=Decimal("0"),
                currency=transaction.currency,
                status_transitions=status_transitions,
                error_details="Payment processing timeout"
            )
            
        except Exception as e:
            transaction.status = PaymentStatus.FAILED
            transaction.error_message = f"Processing error: {str(e)}"
            status_transitions.append((transaction.status, datetime.now()))
            
            return PaymentTestResult(
                test_name=f"payment_{transaction.id[:8]}",
                transaction_id=transaction.id,
                result=TestResult.ERROR,
                execution_time=time.time() - start_time,
                amount_processed=Decimal("0"),
                currency=transaction.currency,
                status_transitions=status_transitions,
                error_details=str(e)
            )

    async def run_payment_flow_test(self, test: PaymentFlowTest) -> PaymentTestResult:
        """Execute a single payment flow test"""
        # Create transaction
        transaction = PaymentTransaction(
            id=str(uuid.uuid4()),
            amount=test.amount,
            currency=test.currency,
            payment_method=test.payment_method,
            merchant_id="test_merchant_001",
            customer_id="test_customer_001",
            description=test.description
        )
        
        self.active_transactions[transaction.id] = transaction
        
        try:
            # Run the payment simulation with timeout
            result = await asyncio.wait_for(
                self.simulate_payment_gateway(transaction),
                timeout=test.timeout_seconds
            )
            
            result.test_name = test.name
            
            # Save transaction to database
            self.save_transaction(transaction)
            
            return result
            
        except asyncio.TimeoutError:
            return PaymentTestResult(
                test_name=test.name,
                transaction_id=transaction.id,
                result=TestResult.TIMEOUT,
                execution_time=test.timeout_seconds,
                amount_processed=Decimal("0"),
                currency=test.currency,
                status_transitions=[(PaymentStatus.PENDING, datetime.now())],
                error_details="Test timeout exceeded"
            )
        finally:
            # Clean up
            if transaction.id in self.active_transactions:
                del self.active_transactions[transaction.id]

    async def run_all_payment_tests(self) -> PaymentFlowReport:
        """Run all payment flow tests"""
        start_time = time.time()
        self.test_results = []
        
        print(f"💳 Starting Payment Flow Testing...")
        print(f"🧪 Running {len(self.test_scenarios)} test scenarios...")
        
        # Run tests with controlled parallelism
        semaphore = asyncio.Semaphore(3)  # Limit concurrent payment tests
        
        async def run_test_with_semaphore(test):
            async with semaphore:
                print(f"  💸 Testing: {test.name}")
                return await self.run_payment_flow_test(test)
        
        tasks = [run_test_with_semaphore(test) for test in self.test_scenarios]
        self.test_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        for i, result in enumerate(self.test_results):
            if isinstance(result, Exception):
                self.test_results[i] = PaymentTestResult(
                    test_name=self.test_scenarios[i].name,
                    transaction_id="error",
                    result=TestResult.ERROR,
                    execution_time=0.0,
                    amount_processed=Decimal("0"),
                    currency="USD",
                    status_transitions=[],
                    error_details=str(result)
                )
        
        # Generate report
        test_duration = time.time() - start_time
        
        passed = sum(1 for r in self.test_results if r.result == TestResult.PASS)
        failed = sum(1 for r in self.test_results if r.result == TestResult.FAIL)
        errors = sum(1 for r in self.test_results if r.result == TestResult.ERROR)
        timeouts = sum(1 for r in self.test_results if r.result == TestResult.TIMEOUT)
        
        total_amount = sum(r.amount_processed for r in self.test_results)
        currencies = list(set(r.currency for r in self.test_results))
        payment_methods = list(set(test.payment_method for test in self.test_scenarios))
        
        avg_processing_time = sum(r.execution_time for r in self.test_results) / len(self.test_results)
        
        critical_failures = [r for r in self.test_results if r.result in [TestResult.ERROR, TestResult.TIMEOUT]]
        
        report = PaymentFlowReport(
            total_tests=len(self.test_scenarios),
            passed=passed,
            failed=failed,
            errors=errors,
            timeouts=timeouts,
            total_amount_tested=total_amount,
            currencies_tested=currencies,
            payment_methods_tested=payment_methods,
            average_processing_time=avg_processing_time,
            test_results=self.test_results,
            critical_failures=critical_failures,
            timestamp=datetime.now(),
            test_duration=test_duration
        )
        
        # Save report
        self.save_report(report)
        
        return report

    def save_transaction(self, transaction: PaymentTransaction):
        """Save transaction to database"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
            INSERT INTO payment_transactions 
            (id, amount, currency, payment_method, merchant_id, customer_id, 
             description, status, created_at, completed_at, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transaction.id, float(transaction.amount), transaction.currency,
                transaction.payment_method.value, transaction.merchant_id,
                transaction.customer_id, transaction.description, transaction.status.value,
                transaction.created_at, transaction.completed_at,
                transaction.error_message, json.dumps(transaction.metadata)
            ))
            
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to save transaction: {e}")
            conn.rollback()
        finally:
            conn.close()

    def save_report(self, report: PaymentFlowReport):
        """Save payment flow report to database"""
        conn = sqlite3.connect(self.audit_db_path)
        cursor = conn.cursor()
        
        try:
            # Save report summary
            cursor.execute('''
            INSERT INTO payment_flow_reports 
            (total_tests, passed, failed, errors, timeouts, total_amount_tested,
             currencies_tested, payment_methods_tested, average_processing_time,
             test_duration, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                report.total_tests, report.passed, report.failed, report.errors,
                report.timeouts, float(report.total_amount_tested),
                json.dumps(report.currencies_tested),
                json.dumps([method.value for method in report.payment_methods_tested]),
                report.average_processing_time, report.test_duration, report.timestamp
            ))
            
            report_id = cursor.lastrowid
            
            # Save individual test results
            for result in report.test_results:
                cursor.execute('''
                INSERT INTO payment_test_results 
                (report_id, test_name, transaction_id, result, execution_time,
                 amount_processed, currency, status_transitions, error_details,
                 performance_metrics, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    report_id, result.test_name, result.transaction_id,
                    result.result.value, result.execution_time,
                    float(result.amount_processed), result.currency,
                    json.dumps([(status.value, ts.isoformat()) for status, ts in result.status_transitions]),
                    result.error_details, json.dumps(result.performance_metrics),
                    result.timestamp
                ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to save payment flow report: {e}")
            conn.rollback()
        finally:
            conn.close()

    def generate_html_report(self, report: PaymentFlowReport) -> str:
        """Generate HTML payment flow report"""
        # Result colors
        result_colors = {
            TestResult.PASS: "#28a745",
            TestResult.FAIL: "#ffc107",
            TestResult.ERROR: "#dc3545",
            TestResult.TIMEOUT: "#6f42c1"
        }
        
        # Generate test results table
        results_html = ""
        for result in sorted(report.test_results, key=lambda x: (x.result.value, x.test_name)):
            result_color = result_colors.get(result.result, "#6c757d")
            
            # Format status transitions
            transitions = " → ".join([status.value for status, _ in result.status_transitions])
            
            results_html += f"""
            <tr style="border-bottom: 1px solid #dee2e6;">
                <td style="padding: 8px; font-family: monospace; font-size: 0.9em;">{result.test_name}</td>
                <td style="padding: 8px; font-family: monospace; font-size: 0.8em;">{result.transaction_id[:8]}...</td>
                <td style="padding: 8px; color: {result_color}; font-weight: bold;">{result.result.value.upper()}</td>
                <td style="padding: 8px; text-align: right;">${result.amount_processed}</td>
                <td style="padding: 8px; text-align: center;">{result.currency}</td>
                <td style="padding: 8px; text-align: right;">{result.execution_time:.3f}s</td>
                <td style="padding: 8px; font-size: 0.8em;">{transitions}</td>
                <td style="padding: 8px; color: #dc3545; font-size: 0.9em;">{result.error_details}</td>
            </tr>
            """
        
        # Calculate success rate
        success_rate = (report.passed / report.total_tests) * 100 if report.total_tests > 0 else 0
        
        html_report = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment Flow Testing Report</title>
            <meta charset="utf-8">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; background: #f8f9fa; }}
                .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #343a40; margin-bottom: 30px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #343a40; color: white; padding: 12px 8px; text-align: left; }}
                .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .card {{ padding: 20px; border-radius: 8px; text-align: center; color: white; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
                .metric {{ background: #e9ecef; padding: 15px; border-radius: 5px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💳 Payment Flow Testing Report</h1>
                <p><strong>Generated:</strong> {report.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Test Duration:</strong> {report.test_duration:.2f} seconds</p>
                <p><strong>Total Amount Tested:</strong> ${report.total_amount_tested}</p>
                
                <div class="summary-cards">
                    <div class="card" style="background: #28a745;">
                        <h3 style="margin: 0; font-size: 2em;">{report.passed}</h3>
                        <p style="margin: 5px 0 0 0;">Passed</p>
                    </div>
                    <div class="card" style="background: #ffc107; color: #212529;">
                        <h3 style="margin: 0; font-size: 2em;">{report.failed}</h3>
                        <p style="margin: 5px 0 0 0;">Failed</p>
                    </div>
                    <div class="card" style="background: #dc3545;">
                        <h3 style="margin: 0; font-size: 2em;">{report.errors}</h3>
                        <p style="margin: 5px 0 0 0;">Errors</p>
                    </div>
                    <div class="card" style="background: #6f42c1;">
                        <h3 style="margin: 0; font-size: 2em;">{report.timeouts}</h3>
                        <p style="margin: 5px 0 0 0;">Timeouts</p>
                    </div>
                    <div class="card" style="background: #17a2b8;">
                        <h3 style="margin: 0; font-size: 2em;">{success_rate:.1f}%</h3>
                        <p style="margin: 5px 0 0 0;">Success Rate</p>
                    </div>
                    <div class="card" style="background: #20c997;">
                        <h3 style="margin: 0; font-size: 2em;">{report.average_processing_time:.2f}s</h3>
                        <p style="margin: 5px 0 0 0;">Avg Processing Time</p>
                    </div>
                </div>
                
                <h2>📊 Test Results</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Test Name</th>
                            <th>Transaction ID</th>
                            <th>Result</th>
                            <th>Amount</th>
                            <th>Currency</th>
                            <th>Execution Time</th>
                            <th>Status Flow</th>
                            <th>Error Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {results_html}
                    </tbody>
                </table>
                
                <div class="metrics">
                    <div class="metric">
                        <strong>{len(report.currencies_tested)}</strong><br>
                        Currencies Tested
                    </div>
                    <div class="metric">
                        <strong>{len(report.payment_methods_tested)}</strong><br>
                        Payment Methods
                    </div>
                    <div class="metric">
                        <strong>{len(report.critical_failures)}</strong><br>
                        Critical Failures
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_report

async def main():
    """Main function to run payment flow testing"""
    tester = PaymentFlowTester()
    
    # Run all payment tests
    report = await tester.run_all_payment_tests()
    
    # Print summary
    print(f"\n📊 Payment Flow Test Summary:")
    print(f"💳 Total Tests: {report.total_tests}")
    print(f"✅ Passed: {report.passed}")
    print(f"⚠️ Failed: {report.failed}")
    print(f"🔥 Errors: {report.errors}")
    print(f"⏰ Timeouts: {report.timeouts}")
    print(f"💰 Total Amount Tested: ${report.total_amount_tested}")
    print(f"🌍 Currencies: {', '.join(report.currencies_tested)}")
    print(f"⚡ Average Processing Time: {report.average_processing_time:.3f} seconds")
    print(f"🕒 Test Duration: {report.test_duration:.2f} seconds")
    
    # Show critical failures
    if report.critical_failures:
        print(f"\n🚨 Critical Failures:")
        for failure in report.critical_failures:
            print(f"  {failure.test_name}: {failure.error_details}")
    
    # Generate HTML report
    html_report = tester.generate_html_report(report)
    report_path = f"payment_flow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    
    with open(report_path, 'w') as f:
        f.write(html_report)
    
    print(f"\n📄 HTML report saved: {report_path}")
    return report

if __name__ == "__main__":
    asyncio.run(main())