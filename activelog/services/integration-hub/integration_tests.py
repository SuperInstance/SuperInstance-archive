"""
ActiveLog Integration Hub - Automated Integration Tests
Comprehensive integration testing between all related services
"""

import asyncio
import aiohttp
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import logging
import uuid
from service_discovery import ServiceDiscovery, ServiceInfo
from health_monitor import HealthMonitor

class TestType(Enum):
    API_CONNECTIVITY = "api_connectivity"
    DATA_FLOW = "data_flow"
    DEPENDENCY_CHAIN = "dependency_chain"
    LOAD_TEST = "load_test"
    SECURITY_TEST = "security_test"
    CONTRACT_TEST = "contract_test"
    END_TO_END = "end_to_end"

class TestStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RUNNING = "running"
    ERROR = "error"

@dataclass
class TestStep:
    name: str
    action: str
    expected_result: Any
    actual_result: Any = None
    status: TestStatus = TestStatus.RUNNING
    duration_ms: float = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IntegrationTest:
    test_id: str
    name: str
    description: str
    test_type: TestType
    services_involved: List[str]
    steps: List[TestStep]
    status: TestStatus = TestStatus.RUNNING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: float = 0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.test_id:
            self.test_id = str(uuid.uuid4())
        if not self.start_time:
            self.start_time = datetime.now()

@dataclass
class TestSuite:
    suite_id: str
    name: str
    description: str
    tests: List[IntegrationTest]
    parallel_execution: bool = True
    timeout_seconds: int = 300
    retry_count: int = 1
    
    def __post_init__(self):
        if not self.suite_id:
            self.suite_id = str(uuid.uuid4())

class IntegrationTestEngine:
    def __init__(self, discovery: ServiceDiscovery, health_monitor: HealthMonitor):
        self.discovery = discovery
        self.health_monitor = health_monitor
        self.test_suites: Dict[str, TestSuite] = {}
        self.test_results: Dict[str, IntegrationTest] = {}
        self.running_tests: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def initialize(self):
        """Initialize the test engine"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        # Auto-generate test suites based on discovered services
        await self.generate_test_suites()
    
    async def generate_test_suites(self):
        """Auto-generate integration test suites based on service discovery"""
        await self.discovery.discover_all_services()
        
        # Generate API connectivity tests
        api_suite = await self.generate_api_connectivity_suite()
        self.test_suites["api_connectivity"] = api_suite
        
        # Generate dependency chain tests
        dependency_suite = await self.generate_dependency_chain_suite()
        self.test_suites["dependency_chains"] = dependency_suite
        
        # Generate data flow tests
        data_flow_suite = await self.generate_data_flow_suite()
        self.test_suites["data_flows"] = data_flow_suite
        
        # Generate contract tests
        contract_suite = await self.generate_contract_test_suite()
        self.test_suites["contracts"] = contract_suite
        
        # Generate end-to-end workflow tests
        e2e_suite = await self.generate_e2e_test_suite()
        self.test_suites["end_to_end"] = e2e_suite
    
    async def generate_api_connectivity_suite(self) -> TestSuite:
        """Generate API connectivity tests for all services"""
        tests = []
        
        api_services = [s for s in self.discovery.services.values() 
                       if s.port > 0 and s.endpoints]
        
        for service in api_services:
            for endpoint in service.endpoints:
                test = IntegrationTest(
                    test_id="",
                    name=f"API Connectivity - {service.name}{endpoint.path}",
                    description=f"Test {endpoint.method} {endpoint.path} endpoint connectivity",
                    test_type=TestType.API_CONNECTIVITY,
                    services_involved=[service.name],
                    steps=[
                        TestStep(
                            name="Health Check",
                            action=f"GET http://{service.host}:{service.port}/health",
                            expected_result=200
                        ),
                        TestStep(
                            name="Endpoint Test",
                            action=f"{endpoint.method} http://{service.host}:{service.port}{endpoint.path}",
                            expected_result="valid_response"
                        )
                    ]
                )
                tests.append(test)
        
        return TestSuite(
            suite_id="",
            name="API Connectivity Tests",
            description="Test basic API connectivity for all services",
            tests=tests
        )
    
    async def generate_dependency_chain_suite(self) -> TestSuite:
        """Generate dependency chain tests"""
        tests = []
        
        # Analyze service dependencies
        dependency_chains = await self.analyze_dependency_chains()
        
        for chain in dependency_chains:
            if len(chain) > 1:
                test = IntegrationTest(
                    test_id="",
                    name=f"Dependency Chain - {' -> '.join(chain)}",
                    description=f"Test dependency chain: {' -> '.join(chain)}",
                    test_type=TestType.DEPENDENCY_CHAIN,
                    services_involved=chain,
                    steps=await self.generate_dependency_test_steps(chain)
                )
                tests.append(test)
        
        return TestSuite(
            suite_id="",
            name="Dependency Chain Tests",
            description="Test service dependency chains",
            tests=tests
        )
    
    async def generate_data_flow_suite(self) -> TestSuite:
        """Generate data flow tests between services"""
        tests = []
        
        # Common data flow patterns in ActiveLog
        data_flows = [
            {
                "name": "User Registration Flow",
                "services": ["api-gateway", "user-service", "notification-service", "database"],
                "flow": "register_user -> create_profile -> send_welcome_email -> store_data"
            },
            {
                "name": "Activity Sync Flow",
                "services": ["sync-service", "activity-processor", "data-store", "analytics"],
                "flow": "sync_activities -> process_data -> store_activities -> update_metrics"
            },
            {
                "name": "AI Processing Flow",
                "services": ["ai-gateway", "nlp-service", "ml-processor", "results-cache"],
                "flow": "receive_request -> process_text -> run_ml_models -> cache_results"
            }
        ]
        
        for flow_config in data_flows:
            # Only create test if all services exist
            existing_services = [s for s in flow_config["services"] 
                               if s in self.discovery.services]
            
            if len(existing_services) >= 2:
                test = IntegrationTest(
                    test_id="",
                    name=f"Data Flow - {flow_config['name']}",
                    description=f"Test {flow_config['flow']}",
                    test_type=TestType.DATA_FLOW,
                    services_involved=existing_services,
                    steps=await self.generate_data_flow_test_steps(existing_services, flow_config)
                )
                tests.append(test)
        
        return TestSuite(
            suite_id="",
            name="Data Flow Tests",
            description="Test data flows between services",
            tests=tests
        )
    
    async def generate_contract_test_suite(self) -> TestSuite:
        """Generate contract tests between services"""
        tests = []
        
        # Test API contracts
        for service_name, service in self.discovery.services.items():
            if service.endpoints:
                test = IntegrationTest(
                    test_id="",
                    name=f"API Contract - {service_name}",
                    description=f"Test API contract compliance for {service_name}",
                    test_type=TestType.CONTRACT_TEST,
                    services_involved=[service_name],
                    steps=await self.generate_contract_test_steps(service)
                )
                tests.append(test)
        
        return TestSuite(
            suite_id="",
            name="Contract Tests",
            description="Test API contracts and data schemas",
            tests=tests
        )
    
    async def generate_e2e_test_suite(self) -> TestSuite:
        """Generate end-to-end workflow tests"""
        tests = []
        
        # Common end-to-end scenarios
        e2e_scenarios = [
            {
                "name": "Complete User Journey",
                "description": "Full user registration to activity sync workflow",
                "services": ["api-gateway", "user-service", "sync-service", "analytics"]
            },
            {
                "name": "AI Processing Pipeline",
                "description": "Complete AI processing from input to results",
                "services": ["nlp-service", "ml-processor", "data-enrichment", "results-api"]
            },
            {
                "name": "Memory System Workflow",
                "description": "Memory preservation and retrieval workflow",
                "services": ["memory-preservation", "story-continuation", "biography-generation"]
            }
        ]
        
        for scenario in e2e_scenarios:
            # Check if required services exist
            existing_services = [s for s in scenario["services"] 
                               if s in self.discovery.services]
            
            if len(existing_services) >= 2:
                test = IntegrationTest(
                    test_id="",
                    name=f"E2E - {scenario['name']}",
                    description=scenario["description"],
                    test_type=TestType.END_TO_END,
                    services_involved=existing_services,
                    steps=await self.generate_e2e_test_steps(existing_services, scenario)
                )
                tests.append(test)
        
        return TestSuite(
            suite_id="",
            name="End-to-End Tests",
            description="Complete workflow integration tests",
            tests=tests
        )
    
    async def analyze_dependency_chains(self) -> List[List[str]]:
        """Analyze and find service dependency chains"""
        chains = []
        
        # Build dependency graph
        dependency_graph = {}
        for service_name, service in self.discovery.services.items():
            deps = []
            for dep_url in service.dependencies:
                # Try to map URL dependencies to service names
                for other_service_name in self.discovery.services.keys():
                    if other_service_name.replace("-", "").lower() in dep_url.lower():
                        deps.append(other_service_name)
            dependency_graph[service_name] = deps
        
        # Find chains using DFS
        def find_chains(current_service, visited, current_chain):
            if current_service in visited:
                return
            
            visited.add(current_service)
            current_chain.append(current_service)
            
            if len(current_chain) > 1:
                chains.append(current_chain.copy())
            
            for dependent in dependency_graph.get(current_service, []):
                find_chains(dependent, visited.copy(), current_chain.copy())
        
        for service in dependency_graph.keys():
            find_chains(service, set(), [])
        
        # Remove duplicates and sort by length
        unique_chains = []
        for chain in chains:
            if chain not in unique_chains and len(chain) <= 5:  # Limit chain length
                unique_chains.append(chain)
        
        return unique_chains
    
    async def generate_dependency_test_steps(self, chain: List[str]) -> List[TestStep]:
        """Generate test steps for dependency chain"""
        steps = []
        
        # Test each service in chain is healthy
        for service_name in chain:
            steps.append(TestStep(
                name=f"Health Check - {service_name}",
                action=f"check_health",
                expected_result="healthy",
                metadata={"service": service_name}
            ))
        
        # Test dependencies can communicate
        for i in range(len(chain) - 1):
            source = chain[i]
            target = chain[i + 1]
            steps.append(TestStep(
                name=f"Communication Test - {source} -> {target}",
                action="test_communication",
                expected_result="success",
                metadata={"source": source, "target": target}
            ))
        
        return steps
    
    async def generate_data_flow_test_steps(self, services: List[str], flow_config: Dict) -> List[TestStep]:
        """Generate test steps for data flow"""
        steps = []
        
        # Create test data
        test_data = {
            "test_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "payload": {"test": True, "message": "Integration test data"}
        }
        
        steps.append(TestStep(
            name="Prepare Test Data",
            action="prepare_data",
            expected_result="success",
            metadata={"data": test_data}
        ))
        
        # Test each step in the flow
        for i, service_name in enumerate(services):
            if i == 0:
                # First service - inject data
                steps.append(TestStep(
                    name=f"Inject Data - {service_name}",
                    action="inject_test_data",
                    expected_result="accepted",
                    metadata={"service": service_name, "data": test_data}
                ))
            else:
                # Subsequent services - verify data received
                steps.append(TestStep(
                    name=f"Verify Data Flow - {service_name}",
                    action="verify_data_received",
                    expected_result="data_found",
                    metadata={"service": service_name, "test_id": test_data["test_id"]}
                ))
        
        return steps
    
    async def generate_contract_test_steps(self, service: ServiceInfo) -> List[TestStep]:
        """Generate contract test steps for a service"""
        steps = []
        
        for endpoint in service.endpoints:
            # Test endpoint schema
            steps.append(TestStep(
                name=f"Schema Validation - {endpoint.method} {endpoint.path}",
                action="validate_schema",
                expected_result="valid_schema",
                metadata={"endpoint": endpoint}
            ))
            
            # Test response format
            steps.append(TestStep(
                name=f"Response Format - {endpoint.method} {endpoint.path}",
                action="validate_response_format",
                expected_result="valid_format",
                metadata={"endpoint": endpoint}
            ))
        
        return steps
    
    async def generate_e2e_test_steps(self, services: List[str], scenario: Dict) -> List[TestStep]:
        """Generate end-to-end test steps"""
        steps = []
        
        # Generate workflow steps based on scenario
        if "User Journey" in scenario["name"]:
            steps = [
                TestStep("User Registration", "register_user", "success"),
                TestStep("Profile Creation", "create_profile", "profile_created"),
                TestStep("Activity Sync", "sync_activities", "sync_complete"),
                TestStep("Analytics Update", "update_analytics", "analytics_updated"),
                TestStep("Verify End State", "verify_complete_state", "all_systems_updated")
            ]
        elif "AI Processing" in scenario["name"]:
            steps = [
                TestStep("Submit Text", "submit_text", "accepted"),
                TestStep("NLP Processing", "process_nlp", "nlp_complete"),
                TestStep("ML Processing", "run_ml_models", "models_complete"),
                TestStep("Results Generation", "generate_results", "results_ready"),
                TestStep("Verify Results", "verify_results", "results_valid")
            ]
        elif "Memory System" in scenario["name"]:
            steps = [
                TestStep("Create Memory", "create_memory_entry", "memory_created"),
                TestStep("Process Story", "process_story_continuation", "story_processed"),
                TestStep("Generate Biography", "generate_biography_section", "biography_updated"),
                TestStep("Verify Preservation", "verify_memory_preserved", "memory_accessible")
            ]
        
        return steps
    
    async def run_test_suite(self, suite_id: str) -> Dict[str, Any]:
        """Run a complete test suite"""
        if suite_id not in self.test_suites:
            return {"error": f"Test suite {suite_id} not found"}
        
        suite = self.test_suites[suite_id]
        results = []
        
        if suite.parallel_execution:
            # Run tests in parallel
            tasks = [self.run_integration_test(test) for test in suite.tests]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        else:
            # Run tests sequentially
            for test in suite.tests:
                result = await self.run_integration_test(test)
                results.append(result)
        
        # Compile suite results
        passed_tests = sum(1 for r in results if isinstance(r, IntegrationTest) and r.status == TestStatus.PASSED)
        failed_tests = sum(1 for r in results if isinstance(r, IntegrationTest) and r.status == TestStatus.FAILED)
        error_tests = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, IntegrationTest) and r.status == TestStatus.ERROR))
        
        return {
            "suite_id": suite_id,
            "suite_name": suite.name,
            "total_tests": len(suite.tests),
            "passed": passed_tests,
            "failed": failed_tests,
            "errors": error_tests,
            "success_rate": (passed_tests / len(suite.tests)) * 100 if suite.tests else 0,
            "results": [r if isinstance(r, dict) else self.test_to_dict(r) for r in results if not isinstance(r, Exception)]
        }
    
    async def run_integration_test(self, test: IntegrationTest) -> IntegrationTest:
        """Run a single integration test"""
        self.running_tests.add(test.test_id)
        test.start_time = datetime.now()
        
        try:
            for step in test.steps:
                await self.execute_test_step(step, test)
                
                if step.status == TestStatus.FAILED:
                    test.status = TestStatus.FAILED
                    test.error = step.error
                    break
            
            # If all steps passed
            if test.status == TestStatus.RUNNING:
                test.status = TestStatus.PASSED
                
        except Exception as e:
            test.status = TestStatus.ERROR
            test.error = str(e)
            logging.error(f"Integration test {test.test_id} failed: {e}")
        
        finally:
            test.end_time = datetime.now()
            test.duration_ms = (test.end_time - test.start_time).total_seconds() * 1000
            self.test_results[test.test_id] = test
            self.running_tests.discard(test.test_id)
        
        return test
    
    async def execute_test_step(self, step: TestStep, test: IntegrationTest):
        """Execute a single test step"""
        start_time = time.time()
        step.status = TestStatus.RUNNING
        
        try:
            if step.action == "check_health":
                step.actual_result = await self.check_service_health(step.metadata["service"])
                step.status = TestStatus.PASSED if step.actual_result == "healthy" else TestStatus.FAILED
            
            elif step.action == "test_communication":
                step.actual_result = await self.test_service_communication(
                    step.metadata["source"], 
                    step.metadata["target"]
                )
                step.status = TestStatus.PASSED if step.actual_result == "success" else TestStatus.FAILED
            
            elif step.action.startswith("GET") or step.action.startswith("POST"):
                # HTTP request
                method, url = step.action.split(" ", 1)
                step.actual_result = await self.make_http_request(method, url)
                
                if isinstance(step.expected_result, int):
                    # Expecting HTTP status code
                    step.status = TestStatus.PASSED if step.actual_result == step.expected_result else TestStatus.FAILED
                else:
                    # Other validation
                    step.status = TestStatus.PASSED if step.actual_result else TestStatus.FAILED
            
            elif step.action == "inject_test_data":
                step.actual_result = await self.inject_test_data(
                    step.metadata["service"], 
                    step.metadata["data"]
                )
                step.status = TestStatus.PASSED if step.actual_result == "accepted" else TestStatus.FAILED
            
            elif step.action == "verify_data_received":
                step.actual_result = await self.verify_data_flow(
                    step.metadata["service"], 
                    step.metadata["test_id"]
                )
                step.status = TestStatus.PASSED if step.actual_result == "data_found" else TestStatus.FAILED
            
            else:
                # Custom test actions
                step.actual_result = await self.execute_custom_action(step, test)
                step.status = TestStatus.PASSED if step.actual_result == step.expected_result else TestStatus.FAILED
                
        except Exception as e:
            step.status = TestStatus.ERROR
            step.error = str(e)
            step.actual_result = f"Error: {e}"
        
        finally:
            step.duration_ms = (time.time() - start_time) * 1000
    
    async def check_service_health(self, service_name: str) -> str:
        """Check if a service is healthy"""
        if service_name in self.discovery.services:
            service = self.discovery.services[service_name]
            if service.status.value == "healthy":
                return "healthy"
            else:
                return service.status.value
        return "not_found"
    
    async def test_service_communication(self, source_service: str, target_service: str) -> str:
        """Test communication between two services"""
        # Simulate service communication test
        source = self.discovery.services.get(source_service)
        target = self.discovery.services.get(target_service)
        
        if not source or not target:
            return "service_not_found"
        
        # If both services are healthy, assume communication works
        if source.status.value == "healthy" and target.status.value == "healthy":
            return "success"
        else:
            return "communication_failed"
    
    async def make_http_request(self, method: str, url: str) -> Any:
        """Make HTTP request and return status code or response"""
        try:
            if self.session:
                async with self.session.request(method, url) as response:
                    return response.status
        except Exception:
            return None
    
    async def inject_test_data(self, service_name: str, data: Dict) -> str:
        """Inject test data into a service"""
        # Simulate data injection - in real implementation, this would
        # send data to the service's test endpoint
        service = self.discovery.services.get(service_name)
        if service and service.port > 0:
            try:
                url = f"http://{service.host}:{service.port}/test/inject"
                if self.session:
                    async with self.session.post(url, json=data) as response:
                        if response.status == 200:
                            return "accepted"
            except:
                pass
        
        return "failed"
    
    async def verify_data_flow(self, service_name: str, test_id: str) -> str:
        """Verify that data flowed to a service"""
        # Simulate data verification
        service = self.discovery.services.get(service_name)
        if service and service.port > 0:
            try:
                url = f"http://{service.host}:{service.port}/test/verify/{test_id}"
                if self.session:
                    async with self.session.get(url) as response:
                        if response.status == 200:
                            return "data_found"
            except:
                pass
        
        return "data_not_found"
    
    async def execute_custom_action(self, step: TestStep, test: IntegrationTest) -> Any:
        """Execute custom test actions"""
        # Placeholder for custom test logic
        # In real implementation, this would contain specific test logic
        # for different types of actions
        
        return "custom_action_completed"
    
    def test_to_dict(self, test: IntegrationTest) -> Dict[str, Any]:
        """Convert test to dictionary"""
        return {
            "test_id": test.test_id,
            "name": test.name,
            "description": test.description,
            "test_type": test.test_type.value,
            "services_involved": test.services_involved,
            "status": test.status.value,
            "duration_ms": test.duration_ms,
            "error": test.error,
            "steps": [
                {
                    "name": step.name,
                    "action": step.action,
                    "expected_result": step.expected_result,
                    "actual_result": step.actual_result,
                    "status": step.status.value,
                    "duration_ms": step.duration_ms,
                    "error": step.error
                }
                for step in test.steps
            ]
        }
    
    def get_test_report(self) -> Dict[str, Any]:
        """Get comprehensive test report"""
        total_tests = len(self.test_results)
        if total_tests == 0:
            return {"message": "No tests have been run yet"}
        
        passed = sum(1 for t in self.test_results.values() if t.status == TestStatus.PASSED)
        failed = sum(1 for t in self.test_results.values() if t.status == TestStatus.FAILED)
        errors = sum(1 for t in self.test_results.values() if t.status == TestStatus.ERROR)
        
        # Group results by test type
        by_type = {}
        for test in self.test_results.values():
            test_type = test.test_type.value
            if test_type not in by_type:
                by_type[test_type] = {"passed": 0, "failed": 0, "errors": 0, "total": 0}
            
            by_type[test_type]["total"] += 1
            if test.status == TestStatus.PASSED:
                by_type[test_type]["passed"] += 1
            elif test.status == TestStatus.FAILED:
                by_type[test_type]["failed"] += 1
            elif test.status == TestStatus.ERROR:
                by_type[test_type]["errors"] += 1
        
        return {
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "success_rate": (passed / total_tests) * 100,
                "currently_running": len(self.running_tests)
            },
            "by_test_type": by_type,
            "test_suites": {
                suite_id: {
                    "name": suite.name,
                    "description": suite.description,
                    "test_count": len(suite.tests)
                }
                for suite_id, suite in self.test_suites.items()
            },
            "recent_failures": [
                self.test_to_dict(test) for test in 
                sorted(self.test_results.values(), 
                      key=lambda t: t.end_time or datetime.now(), reverse=True)
                if test.status in [TestStatus.FAILED, TestStatus.ERROR]
            ][:10]
        }

# Example usage
async def main():
    discovery = ServiceDiscovery()
    health_monitor = HealthMonitor(discovery)
    test_engine = IntegrationTestEngine(discovery, health_monitor)
    
    # Initialize
    await test_engine.initialize()
    
    print(f"Generated {len(test_engine.test_suites)} test suites")
    
    # Run API connectivity tests
    if "api_connectivity" in test_engine.test_suites:
        results = await test_engine.run_test_suite("api_connectivity")
        print(f"API Connectivity Tests: {results['passed']}/{results['total_tests']} passed")
    
    # Get full report
    report = test_engine.get_test_report()
    print(f"Overall success rate: {report['summary']['success_rate']:.1f}%")

if __name__ == "__main__":
    asyncio.run(main())