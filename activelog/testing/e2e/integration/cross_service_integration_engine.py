"""
Cross-Service Integration Testing Engine for ActiveLog Platform

This module provides comprehensive integration testing across all microservices
with service mesh communication, contract validation, and end-to-end workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from enum import Enum
import json
import asyncio
import aiohttp
import websockets
import logging
from pathlib import Path
import yaml
import subprocess
import time
import random
import hashlib
import uuid


class ServiceType(Enum):
    """Types of services in the platform"""
    WEB_API = "web_api"
    MICROSERVICE = "microservice"
    DATABASE = "database"
    MESSAGE_QUEUE = "message_queue"
    CACHE = "cache"
    EXTERNAL_API = "external_api"
    WEBSOCKET_SERVICE = "websocket_service"
    FILE_STORAGE = "file_storage"
    NOTIFICATION_SERVICE = "notification_service"


class IntegrationTestType(Enum):
    """Types of integration tests"""
    SERVICE_TO_SERVICE = "service_to_service"
    END_TO_END_WORKFLOW = "end_to_end_workflow"
    CONTRACT_VALIDATION = "contract_validation"
    DATA_FLOW = "data_flow"
    EVENT_DRIVEN = "event_driven"
    BATCH_PROCESSING = "batch_processing"
    REAL_TIME_SYNC = "real_time_sync"
    CIRCUIT_BREAKER = "circuit_breaker"
    LOAD_BALANCING = "load_balancing"
    SERVICE_DISCOVERY = "service_discovery"


class TestResult(Enum):
    """Test result statuses"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class ServiceEndpoint:
    """Service endpoint definition"""
    service_id: str
    name: str
    service_type: ServiceType
    base_url: str
    health_check_path: str = "/health"
    authentication: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    retry_count: int = 3
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class IntegrationTestCase:
    """Integration test case definition"""
    test_id: str
    name: str
    description: str
    test_type: IntegrationTestType
    services_involved: List[str]
    test_steps: List[Dict[str, Any]]
    expected_results: Dict[str, Any]
    prerequisites: List[str] = field(default_factory=list)
    cleanup_steps: List[Dict[str, Any]] = field(default_factory=list)
    timeout: float = 60.0
    tags: List[str] = field(default_factory=list)


@dataclass
class IntegrationTestResult:
    """Result of an integration test"""
    test_id: str
    test_name: str
    test_type: IntegrationTestType
    result: TestResult
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    error_message: Optional[str] = None
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    service_interactions: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    logs: List[str] = field(default_factory=list)


@dataclass
class IntegrationTestReport:
    """Comprehensive integration test report"""
    report_id: str
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    test_results: List[IntegrationTestResult] = field(default_factory=list)
    service_health: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    overall_success_rate: float = 0.0
    services_tested: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ServiceDiscovery:
    """Manages service discovery and health checking"""
    
    def __init__(self):
        self.services: Dict[str, ServiceEndpoint] = {}
        self.service_health: Dict[str, Dict[str, Any]] = {}
    
    def register_service(self, service: ServiceEndpoint):
        """Register a service"""
        self.services[service.service_id] = service
        logging.info(f"Registered service: {service.service_id} at {service.base_url}")
    
    async def health_check(self, service_id: str) -> Dict[str, Any]:
        """Check health of a specific service"""
        if service_id not in self.services:
            return {"status": "unknown", "error": "Service not registered"}
        
        service = self.services[service_id]
        health_url = f"{service.base_url.rstrip('/')}{service.health_check_path}"
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=service.timeout)) as session:
                start_time = time.time()
                
                headers = {}
                if service.authentication:
                    if "api_key" in service.authentication:
                        headers["X-API-Key"] = service.authentication["api_key"]
                    elif "bearer_token" in service.authentication:
                        headers["Authorization"] = f"Bearer {service.authentication['bearer_token']}"
                
                async with session.get(health_url, headers=headers) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        
                        health_info = {
                            "status": "healthy",
                            "response_time": response_time,
                            "status_code": response.status,
                            "response_data": response_data,
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        health_info = {
                            "status": "unhealthy",
                            "response_time": response_time,
                            "status_code": response.status,
                            "error": f"HTTP {response.status}",
                            "timestamp": datetime.now().isoformat()
                        }
        
        except asyncio.TimeoutError:
            health_info = {
                "status": "timeout",
                "error": "Health check timeout",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            health_info = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        
        self.service_health[service_id] = health_info
        return health_info
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all registered services"""
        tasks = [self.health_check(service_id) for service_id in self.services.keys()]
        health_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        result = {}
        for service_id, health_result in zip(self.services.keys(), health_results):
            if isinstance(health_result, Exception):
                result[service_id] = {
                    "status": "error",
                    "error": str(health_result),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                result[service_id] = health_result
        
        return result
    
    def get_service_dependencies(self, service_id: str) -> List[str]:
        """Get dependencies for a service"""
        if service_id not in self.services:
            return []
        return self.services[service_id].dependencies
    
    def get_dependency_chain(self, service_id: str) -> List[str]:
        """Get the complete dependency chain for a service"""
        visited = set()
        chain = []
        
        def _build_chain(current_service_id: str):
            if current_service_id in visited:
                return  # Avoid circular dependencies
            
            visited.add(current_service_id)
            dependencies = self.get_service_dependencies(current_service_id)
            
            for dep in dependencies:
                _build_chain(dep)
                if dep not in chain:
                    chain.append(dep)
        
        _build_chain(service_id)
        return chain


class ServiceCommunicator:
    """Handles communication between services"""
    
    def __init__(self, service_discovery: ServiceDiscovery):
        self.service_discovery = service_discovery
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=100)
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, service_id: str, method: str, endpoint: str,
                          **kwargs) -> Dict[str, Any]:
        """Make HTTP request to a service"""
        if service_id not in self.service_discovery.services:
            raise ValueError(f"Service {service_id} not found")
        
        service = self.service_discovery.services[service_id]
        url = f"{service.base_url.rstrip('/')}{endpoint}"
        
        # Add authentication if configured
        headers = kwargs.get('headers', {})
        if service.authentication:
            if "api_key" in service.authentication:
                headers["X-API-Key"] = service.authentication["api_key"]
            elif "bearer_token" in service.authentication:
                headers["Authorization"] = f"Bearer {service.authentication['bearer_token']}"
        kwargs['headers'] = headers
        
        start_time = time.time()
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response_time = time.time() - start_time
                
                # Get response data
                if response.content_type == 'application/json':
                    response_data = await response.json()
                else:
                    response_data = await response.text()
                
                return {
                    "service_id": service_id,
                    "method": method,
                    "endpoint": endpoint,
                    "url": url,
                    "status_code": response.status,
                    "response_time": response_time,
                    "response_data": response_data,
                    "headers": dict(response.headers),
                    "success": 200 <= response.status < 300,
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            response_time = time.time() - start_time
            return {
                "service_id": service_id,
                "method": method,
                "endpoint": endpoint,
                "url": url,
                "status_code": 0,
                "response_time": response_time,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat()
            }
    
    async def test_service_communication(self, source_service: str, target_service: str,
                                       test_endpoint: str = "/ping") -> Dict[str, Any]:
        """Test communication between two services"""
        result = await self.make_request(target_service, "GET", test_endpoint)
        
        return {
            "source_service": source_service,
            "target_service": target_service,
            "communication_successful": result["success"],
            "response_time": result["response_time"],
            "status_code": result["status_code"],
            "error": result.get("error"),
            "timestamp": datetime.now().isoformat()
        }


class ContractValidator:
    """Validates API contracts between services"""
    
    def __init__(self):
        self.contracts: Dict[str, Dict[str, Any]] = {}
    
    def load_contract(self, service_id: str, contract_path: str):
        """Load API contract specification"""
        try:
            with open(contract_path, 'r') as f:
                if contract_path.endswith('.yaml') or contract_path.endswith('.yml'):
                    contract = yaml.safe_load(f)
                else:
                    contract = json.load(f)
            
            self.contracts[service_id] = contract
            logging.info(f"Loaded contract for service: {service_id}")
        
        except Exception as e:
            logging.error(f"Failed to load contract for {service_id}: {e}")
    
    async def validate_response(self, service_id: str, endpoint: str, 
                              response_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate response against contract"""
        if service_id not in self.contracts:
            return {
                "valid": False,
                "error": "No contract found for service",
                "service_id": service_id
            }
        
        contract = self.contracts[service_id]
        
        try:
            # Simplified contract validation - in practice would use JSON Schema or OpenAPI
            paths = contract.get('paths', {})
            
            for path, methods in paths.items():
                if endpoint.startswith(path):
                    # Found matching path
                    for method, spec in methods.items():
                        if 'responses' in spec:
                            # Validate response structure
                            response_schema = spec['responses'].get('200', {}).get('schema', {})
                            validation_result = self._validate_schema(response_data, response_schema)
                            
                            return {
                                "valid": validation_result["valid"],
                                "errors": validation_result.get("errors", []),
                                "service_id": service_id,
                                "endpoint": endpoint,
                                "contract_path": path
                            }
            
            return {
                "valid": False,
                "error": "Endpoint not found in contract",
                "service_id": service_id,
                "endpoint": endpoint
            }
        
        except Exception as e:
            return {
                "valid": False,
                "error": f"Contract validation error: {str(e)}",
                "service_id": service_id,
                "endpoint": endpoint
            }
    
    def _validate_schema(self, data: Any, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Validate data against schema (simplified)"""
        errors = []
        
        if not schema:
            return {"valid": True}
        
        schema_type = schema.get('type')
        
        if schema_type == 'object' and isinstance(data, dict):
            required_fields = schema.get('required', [])
            properties = schema.get('properties', {})
            
            # Check required fields
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing required field: {field}")
            
            # Validate properties
            for field, field_schema in properties.items():
                if field in data:
                    field_validation = self._validate_schema(data[field], field_schema)
                    if not field_validation["valid"]:
                        errors.extend(field_validation.get("errors", []))
        
        elif schema_type == 'array' and isinstance(data, list):
            items_schema = schema.get('items', {})
            for i, item in enumerate(data):
                item_validation = self._validate_schema(item, items_schema)
                if not item_validation["valid"]:
                    errors.extend([f"Item {i}: {error}" for error in item_validation.get("errors", [])])
        
        elif schema_type == 'string' and not isinstance(data, str):
            errors.append(f"Expected string, got {type(data).__name__}")
        
        elif schema_type == 'number' and not isinstance(data, (int, float)):
            errors.append(f"Expected number, got {type(data).__name__}")
        
        elif schema_type == 'boolean' and not isinstance(data, bool):
            errors.append(f"Expected boolean, got {type(data).__name__}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class WorkflowTester:
    """Tests end-to-end workflows across multiple services"""
    
    def __init__(self, service_discovery: ServiceDiscovery, communicator: ServiceCommunicator):
        self.service_discovery = service_discovery
        self.communicator = communicator
        self.workflow_data: Dict[str, Any] = {}
    
    async def execute_workflow(self, test_case: IntegrationTestCase) -> IntegrationTestResult:
        """Execute a complete workflow test"""
        result = IntegrationTestResult(
            test_id=test_case.test_id,
            test_name=test_case.name,
            test_type=test_case.test_type,
            result=TestResult.FAILED,
            start_time=datetime.now()
        )
        
        try:
            # Execute test steps
            for i, step in enumerate(test_case.test_steps):
                step_result = await self._execute_step(step, result)
                result.step_results.append(step_result)
                
                if not step_result.get("success", False):
                    result.error_message = step_result.get("error", "Step failed")
                    result.result = TestResult.FAILED
                    break
                
                # Brief pause between steps
                await asyncio.sleep(0.1)
            
            else:
                # All steps completed successfully
                result.result = TestResult.PASSED
            
            # Execute cleanup steps
            for cleanup_step in test_case.cleanup_steps:
                try:
                    await self._execute_step(cleanup_step, result)
                except Exception as e:
                    result.logs.append(f"Cleanup step failed: {str(e)}")
        
        except asyncio.TimeoutError:
            result.result = TestResult.TIMEOUT
            result.error_message = "Test execution timeout"
        
        except Exception as e:
            result.result = TestResult.ERROR
            result.error_message = str(e)
        
        finally:
            result.end_time = datetime.now()
            result.execution_time = (result.end_time - result.start_time).total_seconds()
        
        return result
    
    async def _execute_step(self, step: Dict[str, Any], test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute a single test step"""
        step_type = step.get("type")
        
        if step_type == "http_request":
            return await self._execute_http_request_step(step, test_result)
        elif step_type == "websocket":
            return await self._execute_websocket_step(step, test_result)
        elif step_type == "wait":
            return await self._execute_wait_step(step, test_result)
        elif step_type == "validate":
            return await self._execute_validation_step(step, test_result)
        elif step_type == "store_data":
            return await self._execute_store_data_step(step, test_result)
        elif step_type == "database_query":
            return await self._execute_database_step(step, test_result)
        else:
            return {
                "success": False,
                "error": f"Unknown step type: {step_type}",
                "step": step
            }
    
    async def _execute_http_request_step(self, step: Dict[str, Any], 
                                       test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute HTTP request step"""
        service_id = step.get("service_id")
        method = step.get("method", "GET")
        endpoint = step.get("endpoint")
        data = step.get("data", {})
        expected_status = step.get("expected_status", 200)
        
        # Replace template variables in data
        data = self._replace_template_variables(data)
        
        try:
            request_result = await self.communicator.make_request(
                service_id, method, endpoint, json=data
            )
            
            test_result.service_interactions.append(request_result)
            
            success = request_result["success"] and request_result["status_code"] == expected_status
            
            # Store response data for later steps
            if success and isinstance(request_result.get("response_data"), dict):
                self.workflow_data.update(request_result["response_data"])
            
            return {
                "success": success,
                "step": step,
                "result": request_result,
                "expected_status": expected_status,
                "actual_status": request_result["status_code"]
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    async def _execute_websocket_step(self, step: Dict[str, Any],
                                    test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute WebSocket communication step"""
        service_id = step.get("service_id")
        endpoint = step.get("endpoint")
        message = step.get("message", {})
        expected_response = step.get("expected_response")
        
        if service_id not in self.service_discovery.services:
            return {
                "success": False,
                "error": f"Service {service_id} not found",
                "step": step
            }
        
        service = self.service_discovery.services[service_id]
        ws_url = service.base_url.replace('http://', 'ws://').replace('https://', 'wss://') + endpoint
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send message
                message_data = self._replace_template_variables(message)
                await websocket.send(json.dumps(message_data))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                # Store response data
                if isinstance(response_data, dict):
                    self.workflow_data.update(response_data)
                
                # Check expected response if specified
                success = True
                if expected_response:
                    success = self._validate_response_data(response_data, expected_response)
                
                return {
                    "success": success,
                    "step": step,
                    "response": response_data,
                    "websocket_url": ws_url
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step,
                "websocket_url": ws_url
            }
    
    async def _execute_wait_step(self, step: Dict[str, Any],
                               test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute wait step"""
        duration = step.get("duration", 1.0)
        condition = step.get("condition")  # Optional condition to wait for
        
        try:
            if condition:
                # Wait for condition to be met (simplified)
                start_time = time.time()
                timeout = step.get("timeout", 30.0)
                
                while time.time() - start_time < timeout:
                    if await self._check_condition(condition):
                        return {
                            "success": True,
                            "step": step,
                            "wait_time": time.time() - start_time
                        }
                    await asyncio.sleep(0.5)
                
                return {
                    "success": False,
                    "error": "Condition timeout",
                    "step": step
                }
            else:
                # Simple time-based wait
                await asyncio.sleep(duration)
                return {
                    "success": True,
                    "step": step,
                    "wait_duration": duration
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    async def _execute_validation_step(self, step: Dict[str, Any],
                                     test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute validation step"""
        validation_type = step.get("validation_type")
        expected_data = step.get("expected_data", {})
        
        try:
            if validation_type == "data_exists":
                # Check if certain data exists in workflow_data
                for key, expected_value in expected_data.items():
                    if key not in self.workflow_data:
                        return {
                            "success": False,
                            "error": f"Key {key} not found in workflow data",
                            "step": step
                        }
                    
                    if self.workflow_data[key] != expected_value:
                        return {
                            "success": False,
                            "error": f"Value mismatch for {key}: expected {expected_value}, got {self.workflow_data[key]}",
                            "step": step
                        }
                
                return {
                    "success": True,
                    "step": step,
                    "validated_data": expected_data
                }
            
            elif validation_type == "service_health":
                # Validate that services are healthy
                services_to_check = step.get("services", [])
                for service_id in services_to_check:
                    health = await self.service_discovery.health_check(service_id)
                    if health["status"] != "healthy":
                        return {
                            "success": False,
                            "error": f"Service {service_id} is not healthy: {health.get('error', 'Unknown issue')}",
                            "step": step
                        }
                
                return {
                    "success": True,
                    "step": step,
                    "services_checked": services_to_check
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown validation type: {validation_type}",
                    "step": step
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    async def _execute_store_data_step(self, step: Dict[str, Any],
                                     test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute data storage step"""
        try:
            data_to_store = step.get("data", {})
            
            # Replace template variables and store data
            processed_data = self._replace_template_variables(data_to_store)
            self.workflow_data.update(processed_data)
            
            return {
                "success": True,
                "step": step,
                "stored_data": processed_data
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    async def _execute_database_step(self, step: Dict[str, Any],
                                   test_result: IntegrationTestResult) -> Dict[str, Any]:
        """Execute database operation step"""
        # Simplified database step - would integrate with actual database connections
        try:
            operation = step.get("operation")  # "query", "insert", "update", "delete"
            table = step.get("table")
            data = step.get("data", {})
            
            # This is a mock implementation
            # In real scenario, would execute actual database operations
            
            if operation == "query":
                # Mock query result
                mock_result = [{"id": 1, "name": "test", "created_at": datetime.now().isoformat()}]
                self.workflow_data[f"db_result_{table}"] = mock_result
                
                return {
                    "success": True,
                    "step": step,
                    "operation": operation,
                    "result_count": len(mock_result)
                }
            
            elif operation in ["insert", "update", "delete"]:
                # Mock successful operation
                return {
                    "success": True,
                    "step": step,
                    "operation": operation,
                    "affected_rows": 1
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown database operation: {operation}",
                    "step": step
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "step": step
            }
    
    def _replace_template_variables(self, data: Any) -> Any:
        """Replace template variables in data with workflow data"""
        if isinstance(data, str):
            for key, value in self.workflow_data.items():
                data = data.replace(f"{{{key}}}", str(value))
            
            # Replace special variables
            data = data.replace("{timestamp}", str(int(time.time())))
            data = data.replace("{uuid}", str(uuid.uuid4()))
            data = data.replace("{random}", str(random.randint(1000, 9999)))
            
            return data
        
        elif isinstance(data, dict):
            return {k: self._replace_template_variables(v) for k, v in data.items()}
        
        elif isinstance(data, list):
            return [self._replace_template_variables(item) for item in data]
        
        return data
    
    def _validate_response_data(self, response_data: Dict[str, Any], 
                              expected_data: Dict[str, Any]) -> bool:
        """Validate response data against expected data"""
        for key, expected_value in expected_data.items():
            if key not in response_data:
                return False
            if response_data[key] != expected_value:
                return False
        return True
    
    async def _check_condition(self, condition: Dict[str, Any]) -> bool:
        """Check if a condition is met"""
        condition_type = condition.get("type")
        
        if condition_type == "service_health":
            service_id = condition.get("service_id")
            health = await self.service_discovery.health_check(service_id)
            return health["status"] == "healthy"
        
        elif condition_type == "data_exists":
            key = condition.get("key")
            return key in self.workflow_data
        
        elif condition_type == "http_endpoint":
            # Check if HTTP endpoint returns expected response
            try:
                service_id = condition.get("service_id")
                endpoint = condition.get("endpoint")
                expected_status = condition.get("expected_status", 200)
                
                result = await self.communicator.make_request(service_id, "GET", endpoint)
                return result["status_code"] == expected_status
            except:
                return False
        
        return False


class CrossServiceIntegrationEngine:
    """Main cross-service integration testing engine"""
    
    def __init__(self):
        self.service_discovery = ServiceDiscovery()
        self.contract_validator = ContractValidator()
        self.test_cases: List[IntegrationTestCase] = []
        self.test_results: List[IntegrationTestResult] = []
    
    def register_service(self, service: ServiceEndpoint):
        """Register a service for testing"""
        self.service_discovery.register_service(service)
    
    def load_service_contract(self, service_id: str, contract_path: str):
        """Load API contract for a service"""
        self.contract_validator.load_contract(service_id, contract_path)
    
    def add_test_case(self, test_case: IntegrationTestCase):
        """Add integration test case"""
        self.test_cases.append(test_case)
    
    def create_default_test_cases(self):
        """Create default integration test cases for ActiveLog platform"""
        
        # Service-to-Service communication test
        service_comm_test = IntegrationTestCase(
            test_id="service_communication_test",
            name="Service to Service Communication",
            description="Test communication between all registered services",
            test_type=IntegrationTestType.SERVICE_TO_SERVICE,
            services_involved=list(self.service_discovery.services.keys()),
            test_steps=[
                {
                    "type": "http_request",
                    "service_id": "main_api",
                    "method": "GET",
                    "endpoint": "/health",
                    "expected_status": 200
                },
                {
                    "type": "http_request",
                    "service_id": "tutorial_service",
                    "method": "GET",
                    "endpoint": "/health",
                    "expected_status": 200
                },
                {
                    "type": "validate",
                    "validation_type": "service_health",
                    "services": ["main_api", "tutorial_service"]
                }
            ],
            expected_results={"all_services_healthy": True}
        )
        
        # End-to-End user workflow
        e2e_workflow_test = IntegrationTestCase(
            test_id="e2e_user_workflow",
            name="End-to-End User Workflow",
            description="Complete user journey from registration to tutorial completion",
            test_type=IntegrationTestType.END_TO_END_WORKFLOW,
            services_involved=["main_api", "tutorial_service", "auth_service"],
            test_steps=[
                # User registration
                {
                    "type": "http_request",
                    "service_id": "main_api",
                    "method": "POST",
                    "endpoint": "/auth/register",
                    "data": {
                        "username": "testuser_{timestamp}",
                        "email": "testuser_{timestamp}@example.com",
                        "password": "TestPassword123!"
                    },
                    "expected_status": 201
                },
                # Store user data
                {
                    "type": "store_data",
                    "data": {
                        "user_registered": True,
                        "registration_timestamp": "{timestamp}"
                    }
                },
                # User login
                {
                    "type": "http_request",
                    "service_id": "main_api",
                    "method": "POST",
                    "endpoint": "/auth/login",
                    "data": {
                        "username": "testuser_{registration_timestamp}",
                        "password": "TestPassword123!"
                    },
                    "expected_status": 200
                },
                # Start tutorial
                {
                    "type": "http_request",
                    "service_id": "tutorial_service",
                    "method": "POST",
                    "endpoint": "/tutorials/start",
                    "data": {
                        "tutorial_id": "beginner_tech",
                        "user_id": "{user_id}"
                    },
                    "expected_status": 200
                },
                # Complete tutorial step
                {
                    "type": "http_request",
                    "service_id": "tutorial_service",
                    "method": "POST",
                    "endpoint": "/tutorials/complete-step",
                    "data": {
                        "tutorial_id": "beginner_tech",
                        "step_id": "step_1",
                        "user_id": "{user_id}"
                    },
                    "expected_status": 200
                },
                # Validate completion
                {
                    "type": "validate",
                    "validation_type": "data_exists",
                    "expected_data": {
                        "user_registered": True,
                        "step_completed": True
                    }
                }
            ],
            expected_results={"workflow_completed": True},
            cleanup_steps=[
                {
                    "type": "http_request",
                    "service_id": "main_api",
                    "method": "DELETE",
                    "endpoint": "/users/{user_id}",
                    "expected_status": 200
                }
            ]
        )
        
        # Data synchronization test
        data_sync_test = IntegrationTestCase(
            test_id="data_synchronization_test",
            name="Data Synchronization Test",
            description="Test data synchronization between services",
            test_type=IntegrationTestType.REAL_TIME_SYNC,
            services_involved=["main_api", "tutorial_service", "progress_service"],
            test_steps=[
                # Create user progress in main service
                {
                    "type": "http_request",
                    "service_id": "main_api",
                    "method": "POST",
                    "endpoint": "/users/{user_id}/progress",
                    "data": {
                        "skill_completed": "basic_programming",
                        "score": 95,
                        "completion_time": "{timestamp}"
                    },
                    "expected_status": 201
                },
                # Wait for synchronization
                {
                    "type": "wait",
                    "duration": 2.0
                },
                # Verify data in tutorial service
                {
                    "type": "http_request",
                    "service_id": "tutorial_service",
                    "method": "GET",
                    "endpoint": "/users/{user_id}/progress",
                    "expected_status": 200
                },
                # Validate synchronized data
                {
                    "type": "validate",
                    "validation_type": "data_exists",
                    "expected_data": {
                        "skill_completed": "basic_programming",
                        "score": 95
                    }
                }
            ],
            expected_results={"data_synchronized": True}
        )
        
        self.add_test_case(service_comm_test)
        self.add_test_case(e2e_workflow_test)
        self.add_test_case(data_sync_test)
    
    async def run_comprehensive_tests(self) -> IntegrationTestReport:
        """Run all integration tests"""
        session_id = f"integration_test_{int(time.time())}"
        
        report = IntegrationTestReport(
            report_id=f"report_{session_id}",
            test_session_id=session_id,
            start_time=datetime.now(),
            services_tested=list(self.service_discovery.services.keys())
        )
        
        print(f"Starting comprehensive integration tests...")
        print(f"Testing {len(self.test_cases)} test cases across {len(self.service_discovery.services)} services")
        
        try:
            # First, check health of all services
            print("Checking service health...")
            service_health = await self.service_discovery.health_check_all()
            report.service_health = service_health
            
            unhealthy_services = [
                service_id for service_id, health in service_health.items()
                if health["status"] != "healthy"
            ]
            
            if unhealthy_services:
                print(f"Warning: {len(unhealthy_services)} services are unhealthy: {unhealthy_services}")
            
            # Run integration tests
            async with ServiceCommunicator(self.service_discovery) as communicator:
                workflow_tester = WorkflowTester(self.service_discovery, communicator)
                
                for test_case in self.test_cases:
                    print(f"Running test: {test_case.name}")
                    
                    # Skip tests that involve unhealthy services
                    if any(service in unhealthy_services for service in test_case.services_involved):
                        result = IntegrationTestResult(
                            test_id=test_case.test_id,
                            test_name=test_case.name,
                            test_type=test_case.test_type,
                            result=TestResult.SKIPPED,
                            start_time=datetime.now(),
                            end_time=datetime.now(),
                            error_message="Required services are unhealthy"
                        )
                        report.skipped_tests += 1
                    else:
                        result = await workflow_tester.execute_workflow(test_case)
                        
                        if result.result == TestResult.PASSED:
                            report.passed_tests += 1
                        elif result.result == TestResult.FAILED:
                            report.failed_tests += 1
                        elif result.result == TestResult.ERROR:
                            report.error_tests += 1
                        elif result.result == TestResult.SKIPPED:
                            report.skipped_tests += 1
                    
                    report.test_results.append(result)
                    report.total_tests += 1
                    
                    # Brief pause between tests
                    await asyncio.sleep(1.0)
            
            # Calculate overall success rate
            if report.total_tests > 0:
                report.overall_success_rate = (report.passed_tests / report.total_tests) * 100
            
            # Generate recommendations
            report.recommendations = self._generate_recommendations(report)
            
            report.end_time = datetime.now()
            
            print(f"Integration tests completed:")
            print(f"  Total tests: {report.total_tests}")
            print(f"  Passed: {report.passed_tests}")
            print(f"  Failed: {report.failed_tests}")
            print(f"  Skipped: {report.skipped_tests}")
            print(f"  Errors: {report.error_tests}")
            print(f"  Success rate: {report.overall_success_rate:.1f}%")
            
        except Exception as e:
            logging.error(f"Error during integration tests: {e}")
        
        return report
    
    def _generate_recommendations(self, report: IntegrationTestReport) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Service health recommendations
        unhealthy_services = [
            service_id for service_id, health in report.service_health.items()
            if health["status"] != "healthy"
        ]
        
        if unhealthy_services:
            recommendations.append(f"Fix unhealthy services: {', '.join(unhealthy_services)}")
        
        # Test failure recommendations
        if report.failed_tests > 0:
            recommendations.append(f"Investigate {report.failed_tests} failed test cases")
        
        # Performance recommendations
        slow_services = []
        for service_id, health in report.service_health.items():
            if health.get("response_time", 0) > 2.0:  # Slower than 2 seconds
                slow_services.append(service_id)
        
        if slow_services:
            recommendations.append(f"Optimize performance for slow services: {', '.join(slow_services)}")
        
        # Contract validation recommendations
        recommendations.extend([
            "Implement comprehensive API contract testing",
            "Set up continuous integration for cross-service tests",
            "Monitor service dependencies and communication patterns",
            "Implement circuit breaker patterns for resilient service communication",
            "Set up distributed tracing for better debugging"
        ])
        
        return recommendations[:10]  # Limit to top 10
    
    def generate_html_report(self, report: IntegrationTestReport) -> str:
        """Generate HTML report for integration tests"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cross-Service Integration Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background: #f4f4f4; padding: 20px; border-radius: 5px; }}
                .summary {{ display: flex; justify-content: space-around; margin: 20px 0; }}
                .metric {{ text-align: center; }}
                .metric h3 {{ margin: 0; color: #333; }}
                .metric .value {{ font-size: 2em; font-weight: bold; }}
                .passed {{ color: #4caf50; }}
                .failed {{ color: #f44336; }}
                .skipped {{ color: #ff9800; }}
                .error {{ color: #9c27b0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .service-healthy {{ background-color: #e8f5e8; }}
                .service-unhealthy {{ background-color: #ffebee; }}
                .test-passed {{ background-color: #e8f5e8; }}
                .test-failed {{ background-color: #ffebee; }}
                .test-skipped {{ background-color: #fff3e0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Cross-Service Integration Test Report</h1>
                <p><strong>Report ID:</strong> {report.report_id}</p>
                <p><strong>Test Period:</strong> {report.start_time} - {report.end_time}</p>
                <p><strong>Services Tested:</strong> {', '.join(report.services_tested)}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <h3>Total Tests</h3>
                    <div class="value">{report.total_tests}</div>
                </div>
                <div class="metric">
                    <h3>Passed</h3>
                    <div class="value passed">{report.passed_tests}</div>
                </div>
                <div class="metric">
                    <h3>Failed</h3>
                    <div class="value failed">{report.failed_tests}</div>
                </div>
                <div class="metric">
                    <h3>Success Rate</h3>
                    <div class="value">{report.overall_success_rate:.1f}%</div>
                </div>
            </div>
            
            <h2>Service Health Status</h2>
            <table>
                <thead>
                    <tr>
                        <th>Service</th>
                        <th>Status</th>
                        <th>Response Time</th>
                        <th>Last Check</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for service_id, health in report.service_health.items():
            status_class = "service-healthy" if health["status"] == "healthy" else "service-unhealthy"
            response_time = f"{health.get('response_time', 0):.3f}s" if health.get('response_time') else "N/A"
            
            html += f"""
                    <tr class="{status_class}">
                        <td>{service_id}</td>
                        <td>{health['status'].upper()}</td>
                        <td>{response_time}</td>
                        <td>{health.get('timestamp', 'N/A')}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
            
            <h2>Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Type</th>
                        <th>Result</th>
                        <th>Execution Time</th>
                        <th>Services</th>
                        <th>Error</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for result in report.test_results:
            result_class = f"test-{result.result.value}"
            services_involved = ", ".join([step.get("service_id", "N/A") for step in result.step_results if step.get("service_id")])
            
            html += f"""
                    <tr class="{result_class}">
                        <td>{result.test_name}</td>
                        <td>{result.test_type.value}</td>
                        <td>{result.result.value.upper()}</td>
                        <td>{result.execution_time:.2f}s</td>
                        <td>{services_involved}</td>
                        <td>{result.error_message or ''}</td>
                    </tr>
            """
        
        html += """
                </tbody>
            </table>
            
            <h2>Recommendations</h2>
            <ul>
        """
        
        for rec in report.recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_integration_tests():
        # Initialize integration test engine
        engine = CrossServiceIntegrationEngine()
        
        # Register services
        services = [
            ServiceEndpoint("main_api", "Main API", ServiceType.WEB_API, "http://localhost:3000"),
            ServiceEndpoint("tutorial_service", "Tutorial Service", ServiceType.MICROSERVICE, "http://localhost:8216"),
            ServiceEndpoint("auth_service", "Authentication Service", ServiceType.MICROSERVICE, "http://localhost:8001"),
            ServiceEndpoint("progress_service", "Progress Service", ServiceType.MICROSERVICE, "http://localhost:8002"),
            ServiceEndpoint("notification_service", "Notification Service", ServiceType.MICROSERVICE, "http://localhost:8003")
        ]
        
        for service in services:
            engine.register_service(service)
        
        # Create default test cases
        engine.create_default_test_cases()
        
        print("Starting cross-service integration tests...")
        
        # Run comprehensive tests
        report = await engine.run_comprehensive_tests()
        
        # Generate and save HTML report
        html_report = engine.generate_html_report(report)
        report_file = Path(f"integration_test_report_{int(time.time())}.html")
        report_file.write_text(html_report)
        
        print(f"\nIntegration Test Summary:")
        print(f"Total Tests: {report.total_tests}")
        print(f"Success Rate: {report.overall_success_rate:.1f}%")
        print(f"Services Tested: {len(report.services_tested)}")
        print(f"HTML Report saved to: {report_file}")
        
        return report
    
    # Run the integration tests
    asyncio.run(run_integration_tests())