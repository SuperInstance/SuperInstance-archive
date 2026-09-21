#!/usr/bin/env python3
"""
Multi-Tenant Isolation Testing Engine for ActiveLog E2E Testing Suite.

This module provides comprehensive multi-tenant application testing including
data isolation, resource isolation, security boundaries, performance isolation,
tenant onboarding/offboarding, and cross-tenant vulnerability testing.
"""

import asyncio
import json
import time
import uuid
import random
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Union, Set
from enum import Enum
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import requests
import subprocess

try:
    import psycopg2
    import pymongo
    import redis
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service as ChromeService
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Optional dependencies: pip install psycopg2 pymongo redis selenium webdriver-manager")

class TenantIsolationType(Enum):
    DATA_ISOLATION = "data_isolation"
    RESOURCE_ISOLATION = "resource_isolation"
    SECURITY_ISOLATION = "security_isolation"
    NETWORK_ISOLATION = "network_isolation"
    PERFORMANCE_ISOLATION = "performance_isolation"
    UI_ISOLATION = "ui_isolation"

class IsolationLevel(Enum):
    STRICT = "strict"
    MODERATE = "moderate"
    BASIC = "basic"

class TenantType(Enum):
    ENTERPRISE = "enterprise"
    STANDARD = "standard"
    BASIC = "basic"
    TRIAL = "trial"

class ViolationType(Enum):
    DATA_LEAK = "data_leak"
    RESOURCE_BREACH = "resource_breach"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    CROSS_TENANT_VISIBILITY = "cross_tenant_visibility"
    PERFORMANCE_INTERFERENCE = "performance_interference"
    CONFIG_BLEED = "config_bleed"

class TestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class TenantConfiguration:
    tenant_id: str
    tenant_name: str
    tenant_type: TenantType
    isolation_level: IsolationLevel
    resource_limits: Dict[str, Any]
    data_schema: Optional[str] = None
    custom_domain: Optional[str] = None
    feature_flags: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IsolationViolation:
    id: str
    violation_type: ViolationType
    severity: TestSeverity
    source_tenant: str
    target_tenant: str
    description: str
    evidence: Optional[Dict[str, Any]] = None
    detection_time: datetime = field(default_factory=datetime.now)
    remediation_required: bool = True

@dataclass
class TenantTestData:
    tenant_config: TenantConfiguration
    test_users: List[Dict[str, Any]]
    test_data_records: List[Dict[str, Any]]
    api_credentials: Dict[str, str]
    database_connection: Optional[Dict[str, Any]] = None

@dataclass
class MultiTenantTestResult:
    test_case_id: str
    test_name: str
    isolation_type: TenantIsolationType
    status: str
    tenants_tested: List[str]
    violations: List[IsolationViolation] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    security_findings: List[str] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

class DatabaseIsolationTester:
    def __init__(self, db_configs: Dict[str, Dict[str, Any]]):
        self.db_configs = db_configs
        self.connections = {}

    async def test_data_isolation(self, tenant_configs: List[TenantConfiguration]) -> List[IsolationViolation]:
        violations = []
        
        try:
            await self._setup_tenant_data(tenant_configs)
            
            for i, tenant_a in enumerate(tenant_configs):
                for tenant_b in tenant_configs[i+1:]:
                    violation = await self._test_cross_tenant_data_access(tenant_a, tenant_b)
                    if violation:
                        violations.append(violation)
                        
                    violation = await self._test_data_visibility(tenant_a, tenant_b)
                    if violation:
                        violations.append(violation)
            
            for tenant in tenant_configs:
                violation = await self._test_sql_injection_isolation(tenant)
                if violation:
                    violations.append(violation)
                    
        except Exception as e:
            logging.error(f"Database isolation test failed: {e}")
            
        return violations

    async def _setup_tenant_data(self, tenant_configs: List[TenantConfiguration]):
        for tenant in tenant_configs:
            try:
                conn_config = self.db_configs.get('postgresql', {})
                conn = psycopg2.connect(**conn_config)
                cursor = conn.cursor()
                
                table_name = f"tenant_{tenant.tenant_id}_data"
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {table_name} (
                        id SERIAL PRIMARY KEY,
                        tenant_id VARCHAR(255) NOT NULL,
                        sensitive_data TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                for i in range(10):
                    cursor.execute(f"""
                        INSERT INTO {table_name} (tenant_id, sensitive_data)
                        VALUES (%s, %s)
                    """, (tenant.tenant_id, f"Sensitive data for {tenant.tenant_id} - {i}"))
                
                conn.commit()
                cursor.close()
                conn.close()
                
            except Exception as e:
                logging.warning(f"Failed to setup data for tenant {tenant.tenant_id}: {e}")

    async def _test_cross_tenant_data_access(self, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            conn_config = self.db_configs.get('postgresql', {})
            conn = psycopg2.connect(**conn_config)
            cursor = conn.cursor()
            
            table_a = f"tenant_{tenant_a.tenant_id}_data"
            table_b = f"tenant_{tenant_b.tenant_id}_data"
            
            cursor.execute(f"""
                SELECT COUNT(*) FROM {table_a} 
                WHERE tenant_id != %s
            """, (tenant_a.tenant_id,))
            
            cross_tenant_records = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            if cross_tenant_records > 0:
                return IsolationViolation(
                    id=f"data_leak_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                    violation_type=ViolationType.DATA_LEAK,
                    severity=TestSeverity.CRITICAL,
                    source_tenant=tenant_a.tenant_id,
                    target_tenant=tenant_b.tenant_id,
                    description=f"Found {cross_tenant_records} cross-tenant records in {tenant_a.tenant_id} data",
                    evidence={"cross_tenant_records": cross_tenant_records}
                )
        except Exception as e:
            logging.error(f"Cross-tenant data access test failed: {e}")
            
        return None

    async def _test_data_visibility(self, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            conn_config = self.db_configs.get('postgresql', {})
            conn = psycopg2.connect(**conn_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_name LIKE %s AND table_name NOT LIKE %s
            """, (f"tenant_{tenant_a.tenant_id}%", f"tenant_{tenant_b.tenant_id}%"))
            
            visible_tables = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if visible_tables:
                return IsolationViolation(
                    id=f"table_visibility_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                    violation_type=ViolationType.CROSS_TENANT_VISIBILITY,
                    severity=TestSeverity.HIGH,
                    source_tenant=tenant_a.tenant_id,
                    target_tenant=tenant_b.tenant_id,
                    description=f"Tenant {tenant_b.tenant_id} can see tables belonging to {tenant_a.tenant_id}",
                    evidence={"visible_tables": [t[0] for t in visible_tables]}
                )
        except Exception as e:
            logging.error(f"Data visibility test failed: {e}")
            
        return None

    async def _test_sql_injection_isolation(self, tenant: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            conn_config = self.db_configs.get('postgresql', {})
            conn = psycopg2.connect(**conn_config)
            cursor = conn.cursor()
            
            malicious_query = f"'; SELECT * FROM pg_tables; --"
            table_name = f"tenant_{tenant.tenant_id}_data"
            
            try:
                cursor.execute(f"""
                    SELECT * FROM {table_name} 
                    WHERE sensitive_data LIKE %s
                """, (malicious_query,))
                
                results = cursor.fetchall()
                
            except psycopg2.Error:
                pass
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logging.error(f"SQL injection isolation test failed: {e}")
            
        return None

class APIIsolationTester:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    async def test_api_isolation(self, tenant_configs: List[TenantConfiguration]) -> List[IsolationViolation]:
        violations = []
        
        for i, tenant_a in enumerate(tenant_configs):
            for tenant_b in tenant_configs[i+1:]:
                violation = await self._test_cross_tenant_api_access(tenant_a, tenant_b)
                if violation:
                    violations.append(violation)
                    
                violation = await self._test_authorization_bypass(tenant_a, tenant_b)
                if violation:
                    violations.append(violation)
        
        return violations

    async def _test_cross_tenant_api_access(self, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            headers_a = {'X-Tenant-ID': tenant_a.tenant_id, 'Authorization': 'Bearer token_a'}
            headers_b = {'X-Tenant-ID': tenant_b.tenant_id, 'Authorization': 'Bearer token_b'}
            
            response = self.session.get(
                f"{self.base_url}/api/tenants/{tenant_a.tenant_id}/data",
                headers=headers_b
            )
            
            if response.status_code == 200:
                return IsolationViolation(
                    id=f"api_access_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                    violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                    severity=TestSeverity.CRITICAL,
                    source_tenant=tenant_a.tenant_id,
                    target_tenant=tenant_b.tenant_id,
                    description=f"Tenant {tenant_b.tenant_id} can access {tenant_a.tenant_id} data via API",
                    evidence={"response_code": response.status_code, "response_size": len(response.content)}
                )
        except Exception as e:
            logging.error(f"API cross-tenant access test failed: {e}")
            
        return None

    async def _test_authorization_bypass(self, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            headers = {'Authorization': f'Bearer {tenant_b.tenant_id}_token'}
            
            response = self.session.post(
                f"{self.base_url}/api/tenants/{tenant_a.tenant_id}/admin/users",
                headers=headers,
                json={"username": "malicious_user", "role": "admin"}
            )
            
            if response.status_code in [200, 201]:
                return IsolationViolation(
                    id=f"auth_bypass_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                    violation_type=ViolationType.UNAUTHORIZED_ACCESS,
                    severity=TestSeverity.CRITICAL,
                    source_tenant=tenant_a.tenant_id,
                    target_tenant=tenant_b.tenant_id,
                    description=f"Authorization bypass: {tenant_b.tenant_id} can create users in {tenant_a.tenant_id}",
                    evidence={"response_code": response.status_code}
                )
        except Exception as e:
            logging.error(f"Authorization bypass test failed: {e}")
            
        return None

class UIIsolationTester:
    def __init__(self):
        self.driver = None

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

    async def test_ui_isolation(self, base_url: str, tenant_configs: List[TenantConfiguration]) -> List[IsolationViolation]:
        violations = []
        self.driver = self._setup_driver()
        
        if not self.driver:
            return violations
        
        try:
            for i, tenant_a in enumerate(tenant_configs):
                for tenant_b in tenant_configs[i+1:]:
                    violation = await self._test_cross_tenant_ui_data(base_url, tenant_a, tenant_b)
                    if violation:
                        violations.append(violation)
                        
                    violation = await self._test_tenant_branding_isolation(base_url, tenant_a, tenant_b)
                    if violation:
                        violations.append(violation)
        finally:
            if self.driver:
                self.driver.quit()
        
        return violations

    async def _test_cross_tenant_ui_data(self, base_url: str, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            self.driver.get(f"{base_url}?tenant={tenant_a.tenant_id}")
            
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            
            tenant_b_data_elements = self.driver.find_elements(
                By.XPATH, f"//*[contains(text(), '{tenant_b.tenant_id}') or contains(text(), '{tenant_b.tenant_name}')]"
            )
            
            if tenant_b_data_elements:
                return IsolationViolation(
                    id=f"ui_data_leak_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                    violation_type=ViolationType.CROSS_TENANT_VISIBILITY,
                    severity=TestSeverity.HIGH,
                    source_tenant=tenant_a.tenant_id,
                    target_tenant=tenant_b.tenant_id,
                    description=f"Tenant {tenant_b.tenant_id} data visible in {tenant_a.tenant_id} UI",
                    evidence={"elements_found": len(tenant_b_data_elements)}
                )
        except Exception as e:
            logging.error(f"UI cross-tenant data test failed: {e}")
            
        return None

    async def _test_tenant_branding_isolation(self, base_url: str, tenant_a: TenantConfiguration, tenant_b: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            self.driver.get(f"{base_url}?tenant={tenant_a.tenant_id}")
            
            branding_elements = self.driver.find_elements(By.CSS_SELECTOR, ".logo, .brand, .tenant-name")
            
            for element in branding_elements:
                if tenant_b.tenant_name.lower() in element.text.lower():
                    return IsolationViolation(
                        id=f"branding_bleed_{tenant_a.tenant_id}_{tenant_b.tenant_id}",
                        violation_type=ViolationType.CONFIG_BLEED,
                        severity=TestSeverity.MEDIUM,
                        source_tenant=tenant_a.tenant_id,
                        target_tenant=tenant_b.tenant_id,
                        description=f"Tenant {tenant_b.tenant_id} branding appears in {tenant_a.tenant_id} interface",
                        evidence={"element_text": element.text}
                    )
        except Exception as e:
            logging.error(f"Branding isolation test failed: {e}")
            
        return None

class PerformanceIsolationTester:
    def __init__(self):
        self.load_generators = {}

    async def test_performance_isolation(self, base_url: str, tenant_configs: List[TenantConfiguration]) -> List[IsolationViolation]:
        violations = []
        
        for tenant in tenant_configs:
            violation = await self._test_resource_exhaustion_isolation(base_url, tenant, tenant_configs)
            if violation:
                violations.append(violation)
                
            violation = await self._test_rate_limiting_isolation(base_url, tenant)
            if violation:
                violations.append(violation)
        
        return violations

    async def _test_resource_exhaustion_isolation(self, base_url: str, target_tenant: TenantConfiguration, all_tenants: List[TenantConfiguration]) -> Optional[IsolationViolation]:
        try:
            other_tenants = [t for t in all_tenants if t.tenant_id != target_tenant.tenant_id]
            
            baseline_response_times = []
            for _ in range(10):
                start_time = time.time()
                response = requests.get(f"{base_url}/api/health", headers={'X-Tenant-ID': target_tenant.tenant_id})
                response_time = time.time() - start_time
                baseline_response_times.append(response_time)
            
            baseline_avg = sum(baseline_response_times) / len(baseline_response_times)
            
            load_tasks = []
            for other_tenant in other_tenants[:2]:  # Test with 2 other tenants
                task = asyncio.create_task(self._generate_load(base_url, other_tenant))
                load_tasks.append(task)
            
            await asyncio.sleep(2)  # Let load build up
            
            stressed_response_times = []
            for _ in range(10):
                start_time = time.time()
                response = requests.get(f"{base_url}/api/health", headers={'X-Tenant-ID': target_tenant.tenant_id})
                response_time = time.time() - start_time
                stressed_response_times.append(response_time)
            
            for task in load_tasks:
                task.cancel()
            
            stressed_avg = sum(stressed_response_times) / len(stressed_response_times)
            degradation_factor = stressed_avg / baseline_avg
            
            if degradation_factor > 3.0:  # 3x slower under load
                return IsolationViolation(
                    id=f"performance_interference_{target_tenant.tenant_id}",
                    violation_type=ViolationType.PERFORMANCE_INTERFERENCE,
                    severity=TestSeverity.HIGH,
                    source_tenant="multiple",
                    target_tenant=target_tenant.tenant_id,
                    description=f"Performance degradation: {degradation_factor:.2f}x slower under multi-tenant load",
                    evidence={
                        "baseline_avg_ms": baseline_avg * 1000,
                        "stressed_avg_ms": stressed_avg * 1000,
                        "degradation_factor": degradation_factor
                    }
                )
        except Exception as e:
            logging.error(f"Performance isolation test failed: {e}")
            
        return None

    async def _generate_load(self, base_url: str, tenant: TenantConfiguration):
        try:
            while True:
                requests.get(
                    f"{base_url}/api/data",
                    headers={'X-Tenant-ID': tenant.tenant_id},
                    timeout=1
                )
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    async def _test_rate_limiting_isolation(self, base_url: str, tenant: TenantConfiguration) -> Optional[IsolationViolation]:
        try:
            requests_made = 0
            successful_requests = 0
            
            for _ in range(100):
                response = requests.get(
                    f"{base_url}/api/data",
                    headers={'X-Tenant-ID': tenant.tenant_id}
                )
                requests_made += 1
                
                if response.status_code == 200:
                    successful_requests += 1
                elif response.status_code == 429:  # Rate limited
                    break
            
            if successful_requests > 90:  # Should be rate limited before 90 requests
                return IsolationViolation(
                    id=f"rate_limit_bypass_{tenant.tenant_id}",
                    violation_type=ViolationType.RESOURCE_BREACH,
                    severity=TestSeverity.MEDIUM,
                    source_tenant=tenant.tenant_id,
                    target_tenant=tenant.tenant_id,
                    description=f"Rate limiting not enforced properly for tenant {tenant.tenant_id}",
                    evidence={
                        "requests_made": requests_made,
                        "successful_requests": successful_requests
                    }
                )
        except Exception as e:
            logging.error(f"Rate limiting test failed: {e}")
            
        return None

class MultiTenantTestingEngine:
    def __init__(self, base_url: str = "http://localhost:8080", results_dir: str = "multi_tenant_results"):
        self.base_url = base_url
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_configs = {
            'postgresql': {
                'host': 'localhost',
                'port': 5432,
                'database': 'test_multi_tenant',
                'user': 'test_user',
                'password': 'test_password'
            }
        }
        
        self.db_tester = DatabaseIsolationTester(self.db_configs)
        self.api_tester = APIIsolationTester(self.base_url)
        self.ui_tester = UIIsolationTester()
        self.perf_tester = PerformanceIsolationTester()
        
        self.test_tenants = self._create_test_tenants()

    def _create_test_tenants(self) -> List[TenantConfiguration]:
        return [
            TenantConfiguration(
                tenant_id="tenant_alpha",
                tenant_name="Alpha Corporation",
                tenant_type=TenantType.ENTERPRISE,
                isolation_level=IsolationLevel.STRICT,
                resource_limits={"cpu": 8, "memory": "16GB", "storage": "100GB"},
                custom_domain="alpha.example.com",
                feature_flags={"premium_features": True, "analytics": True}
            ),
            TenantConfiguration(
                tenant_id="tenant_beta", 
                tenant_name="Beta Industries",
                tenant_type=TenantType.STANDARD,
                isolation_level=IsolationLevel.MODERATE,
                resource_limits={"cpu": 4, "memory": "8GB", "storage": "50GB"},
                feature_flags={"premium_features": False, "analytics": True}
            ),
            TenantConfiguration(
                tenant_id="tenant_gamma",
                tenant_name="Gamma Solutions", 
                tenant_type=TenantType.BASIC,
                isolation_level=IsolationLevel.BASIC,
                resource_limits={"cpu": 2, "memory": "4GB", "storage": "25GB"},
                feature_flags={"premium_features": False, "analytics": False}
            ),
            TenantConfiguration(
                tenant_id="tenant_delta",
                tenant_name="Delta Enterprises",
                tenant_type=TenantType.TRIAL,
                isolation_level=IsolationLevel.BASIC,
                resource_limits={"cpu": 1, "memory": "2GB", "storage": "10GB"},
                feature_flags={"premium_features": False, "analytics": False}
            )
        ]

    async def run_data_isolation_tests(self) -> MultiTenantTestResult:
        start_time = time.time()
        
        result = MultiTenantTestResult(
            test_case_id="data_isolation_test",
            test_name="Database Data Isolation Test",
            isolation_type=TenantIsolationType.DATA_ISOLATION,
            status="running",
            tenants_tested=[t.tenant_id for t in self.test_tenants]
        )
        
        try:
            violations = await self.db_tester.test_data_isolation(self.test_tenants)
            result.violations = violations
            
            if not violations:
                result.status = "passed"
            else:
                result.status = "failed"
                
        except Exception as e:
            result.status = "error"
            result.security_findings.append(f"Test execution failed: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_api_isolation_tests(self) -> MultiTenantTestResult:
        start_time = time.time()
        
        result = MultiTenantTestResult(
            test_case_id="api_isolation_test", 
            test_name="API Security Isolation Test",
            isolation_type=TenantIsolationType.SECURITY_ISOLATION,
            status="running",
            tenants_tested=[t.tenant_id for t in self.test_tenants]
        )
        
        try:
            violations = await self.api_tester.test_api_isolation(self.test_tenants)
            result.violations = violations
            
            if not violations:
                result.status = "passed"
            else:
                result.status = "failed"
                
        except Exception as e:
            result.status = "error"
            result.security_findings.append(f"API test execution failed: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_ui_isolation_tests(self) -> MultiTenantTestResult:
        start_time = time.time()
        
        result = MultiTenantTestResult(
            test_case_id="ui_isolation_test",
            test_name="User Interface Isolation Test",
            isolation_type=TenantIsolationType.UI_ISOLATION,
            status="running",
            tenants_tested=[t.tenant_id for t in self.test_tenants]
        )
        
        try:
            violations = await self.ui_tester.test_ui_isolation(self.base_url, self.test_tenants)
            result.violations = violations
            
            if not violations:
                result.status = "passed"
            else:
                result.status = "failed"
                
        except Exception as e:
            result.status = "error"
            result.security_findings.append(f"UI test execution failed: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_performance_isolation_tests(self) -> MultiTenantTestResult:
        start_time = time.time()
        
        result = MultiTenantTestResult(
            test_case_id="performance_isolation_test",
            test_name="Performance Isolation Test", 
            isolation_type=TenantIsolationType.PERFORMANCE_ISOLATION,
            status="running",
            tenants_tested=[t.tenant_id for t in self.test_tenants]
        )
        
        try:
            violations = await self.perf_tester.test_performance_isolation(self.base_url, self.test_tenants)
            result.violations = violations
            
            if not violations:
                result.status = "passed"
            else:
                result.status = "failed"
                
        except Exception as e:
            result.status = "error"
            result.security_findings.append(f"Performance test execution failed: {str(e)}")
        
        result.execution_time = time.time() - start_time
        return result

    async def run_comprehensive_multi_tenant_tests(self) -> Dict[str, Any]:
        print("Starting comprehensive multi-tenant isolation testing...")
        
        test_results = []
        
        print("Running data isolation tests...")
        data_result = await self.run_data_isolation_tests()
        test_results.append(data_result)
        
        print("Running API isolation tests...")
        api_result = await self.run_api_isolation_tests()
        test_results.append(api_result)
        
        print("Running UI isolation tests...")
        ui_result = await self.run_ui_isolation_tests()
        test_results.append(ui_result)
        
        print("Running performance isolation tests...")
        perf_result = await self.run_performance_isolation_tests()
        test_results.append(perf_result)
        
        summary = self._generate_test_summary(test_results)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.results_dir / f"multi_tenant_report_{timestamp}.json"
        
        self.generate_multi_tenant_report(test_results, summary, str(report_path))
        
        return {
            "test_results": test_results,
            "summary": summary,
            "report_path": str(report_path),
            "html_report_path": str(report_path).replace('.json', '.html')
        }

    def _generate_test_summary(self, results: List[MultiTenantTestResult]) -> Dict[str, Any]:
        total_tests = len(results)
        passed_tests = len([r for r in results if r.status == "passed"])
        failed_tests = len([r for r in results if r.status == "failed"])
        error_tests = len([r for r in results if r.status == "error"])
        
        all_violations = []
        for result in results:
            all_violations.extend(result.violations)
        
        violation_counts = {}
        severity_counts = {}
        
        for violation in all_violations:
            violation_type = violation.violation_type.value
            violation_counts[violation_type] = violation_counts.get(violation_type, 0) + 1
            
            severity = violation.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        return {
            "total_tests": total_tests,
            "passed_tests": passed_tests, 
            "failed_tests": failed_tests,
            "error_tests": error_tests,
            "pass_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "total_violations": len(all_violations),
            "violation_types": violation_counts,
            "severity_distribution": severity_counts,
            "tenants_tested": len(self.test_tenants),
            "isolation_types_tested": len(set(r.isolation_type for r in results)),
            "average_execution_time": sum(r.execution_time for r in results) / total_tests if total_tests > 0 else 0
        }

    def generate_multi_tenant_report(self, results: List[MultiTenantTestResult], summary: Dict[str, Any], output_path: str):
        report = {
            "test_summary": {
                "total_tests": summary["total_tests"],
                "passed_tests": summary["passed_tests"],
                "failed_tests": summary["failed_tests"],
                "error_tests": summary["error_tests"],
                "pass_rate": summary["pass_rate"],
                "total_violations": summary["total_violations"],
                "tenants_tested": summary["tenants_tested"],
                "timestamp": datetime.now().isoformat()
            },
            "violation_analysis": {
                "violation_types": summary["violation_types"],
                "severity_distribution": summary["severity_distribution"]
            },
            "tenant_configurations": [
                {
                    "tenant_id": t.tenant_id,
                    "tenant_name": t.tenant_name,
                    "tenant_type": t.tenant_type.value,
                    "isolation_level": t.isolation_level.value,
                    "resource_limits": t.resource_limits,
                    "feature_flags": t.feature_flags
                } for t in self.test_tenants
            ],
            "detailed_results": []
        }
        
        for result in results:
            test_data = {
                "test_case_id": result.test_case_id,
                "test_name": result.test_name,
                "isolation_type": result.isolation_type.value,
                "status": result.status,
                "execution_time": result.execution_time,
                "tenants_tested": result.tenants_tested,
                "violations_count": len(result.violations),
                "security_findings": result.security_findings,
                "performance_metrics": result.performance_metrics,
                "violations": [
                    {
                        "id": v.id,
                        "type": v.violation_type.value,
                        "severity": v.severity.value,
                        "source_tenant": v.source_tenant,
                        "target_tenant": v.target_tenant,
                        "description": v.description,
                        "evidence": v.evidence,
                        "detection_time": v.detection_time.isoformat(),
                        "remediation_required": v.remediation_required
                    } for v in result.violations
                ]
            }
            
            report["detailed_results"].append(test_data)
        
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
            <title>Multi-Tenant Isolation Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .header {{ text-align: center; margin-bottom: 30px; padding: 20px; background: #6f42c1; color: white; border-radius: 6px; }}
                .summary {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
                .summary-card {{ background: #f8f9fa; padding: 15px; border-radius: 6px; text-align: center; }}
                .summary-card h3 {{ margin: 0; color: #333; }}
                .summary-card .value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .critical {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
                .success {{ color: #28a745; }}
                .violation-analysis {{ background: #fff3cd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .tenant-config {{ background: #e8f4fd; padding: 20px; border-radius: 6px; margin-bottom: 30px; }}
                .tenant-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
                .tenant-card {{ background: white; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff; }}
                .test-results {{ margin-bottom: 30px; }}
                .test-item {{ background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 4px; border-left: 4px solid #28a745; }}
                .test-item.failed {{ border-left-color: #dc3545; }}
                .test-item.error {{ border-left-color: #ffc107; }}
                .violations-section {{ margin-top: 15px; }}
                .violation {{ background: #f8d7da; padding: 10px; margin: 5px 0; border-radius: 4px; border-left: 3px solid #dc3545; }}
                .violation.critical {{ background: #f5c6cb; }}
                .violation.high {{ background: #f8d7da; }}
                .violation.medium {{ background: #fff3cd; border-left-color: #ffc107; }}
                .violation.low {{ background: #d1ecf1; border-left-color: #17a2b8; }}
                .violation-details {{ margin-top: 8px; padding: 8px; background: rgba(255,255,255,0.7); border-radius: 4px; font-size: 0.9em; }}
                .status-badge {{ padding: 4px 8px; border-radius: 12px; color: white; font-weight: bold; }}
                .status-passed {{ background: #28a745; }}
                .status-failed {{ background: #dc3545; }}
                .status-error {{ background: #ffc107; color: #212529; }}
                .chart {{ margin: 15px 0; }}
                .bar {{ height: 20px; background: #e9ecef; border-radius: 10px; overflow: hidden; margin: 5px 0; }}
                .bar-fill {{ height: 100%; background: #007bff; display: flex; align-items: center; padding: 0 10px; color: white; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏢 Multi-Tenant Isolation Test Report</h1>
                    <p>Comprehensive Tenant Isolation & Security Testing</p>
                    <p>Generated on {report_data['test_summary']['timestamp']}</p>
                </div>
                
                <div class="summary">
                    <div class="summary-card">
                        <h3>Total Tests</h3>
                        <div class="value">{report_data['test_summary']['total_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Passed Tests</h3>
                        <div class="value success">{report_data['test_summary']['passed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Failed Tests</h3>
                        <div class="value critical">{report_data['test_summary']['failed_tests']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Total Violations</h3>
                        <div class="value critical">{report_data['test_summary']['total_violations']}</div>
                    </div>
                    <div class="summary-card">
                        <h3>Pass Rate</h3>
                        <div class="value {'success' if report_data['test_summary']['pass_rate'] >= 80 else 'critical'}">{report_data['test_summary']['pass_rate']:.1f}%</div>
                    </div>
                    <div class="summary-card">
                        <h3>Tenants Tested</h3>
                        <div class="value">{report_data['test_summary']['tenants_tested']}</div>
                    </div>
                </div>
                
                <div class="violation-analysis">
                    <h3>🚨 Violation Analysis</h3>
                    <div class="chart">
                        <h4>Violations by Type</h4>
        """
        
        for violation_type, count in report_data['violation_analysis']['violation_types'].items():
            percentage = (count / max(report_data['test_summary']['total_violations'], 1)) * 100
            html_content += f"""
                        <div class="bar">
                            <div class="bar-fill" style="width: {percentage}%;">
                                {violation_type.replace('_', ' ').title()}: {count}
                            </div>
                        </div>
            """
        
        html_content += """
                    </div>
                    <div class="chart">
                        <h4>Violations by Severity</h4>
        """
        
        for severity, count in report_data['violation_analysis']['severity_distribution'].items():
            percentage = (count / max(report_data['test_summary']['total_violations'], 1)) * 100
            html_content += f"""
                        <div class="bar">
                            <div class="bar-fill {severity}" style="width: {percentage}%;">
                                {severity.upper()}: {count}
                            </div>
                        </div>
            """
        
        html_content += """
                    </div>
                </div>
                
                <div class="tenant-config">
                    <h3>🏗️ Tenant Configurations Tested</h3>
                    <div class="tenant-grid">
        """
        
        for tenant in report_data['tenant_configurations']:
            html_content += f"""
                        <div class="tenant-card">
                            <h4>{tenant['tenant_name']} ({tenant['tenant_id']})</h4>
                            <p><strong>Type:</strong> {tenant['tenant_type'].upper()}</p>
                            <p><strong>Isolation Level:</strong> {tenant['isolation_level'].upper()}</p>
                            <p><strong>Resources:</strong> CPU: {tenant['resource_limits'].get('cpu', 'N/A')}, 
                               Memory: {tenant['resource_limits'].get('memory', 'N/A')}, 
                               Storage: {tenant['resource_limits'].get('storage', 'N/A')}</p>
                            <p><strong>Features:</strong> {', '.join([f"{k}: {'✅' if v else '❌'}" for k, v in tenant['feature_flags'].items()])}</p>
                        </div>
            """
        
        html_content += """
                    </div>
                </div>
                
                <div class="test-results">
                    <h3>📊 Detailed Test Results</h3>
        """
        
        for test in report_data['detailed_results']:
            status_class = test['status']
            html_content += f"""
                    <div class="test-item {status_class}">
                        <h4>{test['test_name']} ({test['test_case_id']}) 
                            <span class="status-badge status-{status_class}">{test['status'].upper()}</span>
                        </h4>
                        <p><strong>Isolation Type:</strong> {test['isolation_type'].replace('_', ' ').title()} | 
                           <strong>Execution Time:</strong> {test['execution_time']:.2f}s | 
                           <strong>Violations:</strong> {test['violations_count']}</p>
                        <p><strong>Tenants Tested:</strong> {', '.join(test['tenants_tested'])}</p>
            """
            
            if test['security_findings']:
                html_content += "<p><strong>Security Findings:</strong></p><ul>"
                for finding in test['security_findings']:
                    html_content += f"<li>{finding}</li>"
                html_content += "</ul>"
            
            if test['violations']:
                html_content += '<div class="violations-section"><h5>🛡️ Isolation Violations</h5>'
                
                for violation in test['violations']:
                    html_content += f"""
                        <div class="violation {violation['severity']}">
                            <strong>[{violation['severity'].upper()}] {violation['type'].replace('_', ' ').title()}</strong>
                            <p>{violation['description']}</p>
                            <div class="violation-details">
                                <strong>Source Tenant:</strong> {violation['source_tenant']}<br>
                                <strong>Target Tenant:</strong> {violation['target_tenant']}<br>
                                <strong>Detection Time:</strong> {violation['detection_time']}<br>
                                <strong>Remediation Required:</strong> {'✅ Yes' if violation['remediation_required'] else '❌ No'}
                    """
                    
                    if violation['evidence']:
                        html_content += f"<br><strong>Evidence:</strong> {json.dumps(violation['evidence'], indent=2)}"
                    
                    html_content += "</div></div>"
                
                html_content += "</div>"
            
            html_content += "</div>"
        
        html_content += """
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)

async def main():
    engine = MultiTenantTestingEngine()
    
    results = await engine.run_comprehensive_multi_tenant_tests()
    
    print(f"Multi-tenant isolation testing completed!")
    print(f"Total tests: {results['summary']['total_tests']}")
    print(f"Passed tests: {results['summary']['passed_tests']}")
    print(f"Failed tests: {results['summary']['failed_tests']}")
    print(f"Pass rate: {results['summary']['pass_rate']:.1f}%")
    print(f"Total violations: {results['summary']['total_violations']}")
    print(f"Tenants tested: {results['summary']['tenants_tested']}")
    print(f"Report saved to: {results['report_path']}")
    print(f"HTML report saved to: {results['html_report_path']}")

if __name__ == "__main__":
    asyncio.run(main())