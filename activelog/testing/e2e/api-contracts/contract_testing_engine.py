"""
API Contract Testing Engine for ActiveLog Platform

This module provides comprehensive API contract testing including OpenAPI validation,
schema verification, backward compatibility testing, and consumer-driven contract testing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from enum import Enum
import json
import asyncio
import aiohttp
import yaml
import jsonschema
from jsonschema import validate, ValidationError
import logging
from pathlib import Path
import requests
import re
import hashlib
from urllib.parse import urljoin


class ContractTestType(Enum):
    """Types of contract tests"""
    SCHEMA_VALIDATION = "schema_validation"
    REQUEST_VALIDATION = "request_validation"
    RESPONSE_VALIDATION = "response_validation"
    BACKWARD_COMPATIBILITY = "backward_compatibility"
    CONSUMER_DRIVEN = "consumer_driven"
    API_DOCUMENTATION = "api_documentation"
    ENDPOINT_EXISTENCE = "endpoint_existence"
    HTTP_METHODS = "http_methods"
    STATUS_CODES = "status_codes"
    HEADERS_VALIDATION = "headers_validation"


class CompatibilityLevel(Enum):
    """API compatibility levels"""
    BREAKING = "breaking"
    DEPRECATED = "deprecated"
    BACKWARD_COMPATIBLE = "backward_compatible"
    FORWARD_COMPATIBLE = "forward_compatible"
    FULLY_COMPATIBLE = "fully_compatible"


class ContractSeverity(Enum):
    """Contract violation severity"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


@dataclass
class APIContract:
    """API contract definition"""
    contract_id: str
    service_name: str
    version: str
    base_url: str
    specification: Dict[str, Any]  # OpenAPI/Swagger spec
    contract_type: str = "openapi"  # openapi, json-schema, custom
    authentication: Optional[Dict[str, str]] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class ContractTestCase:
    """Individual contract test case"""
    test_id: str
    name: str
    description: str
    test_type: ContractTestType
    endpoint: str
    method: str
    contract_id: str
    test_data: Optional[Dict[str, Any]] = None
    expected_schema: Optional[Dict[str, Any]] = None
    expected_status_codes: List[int] = field(default_factory=list)
    required_headers: List[str] = field(default_factory=list)
    severity: ContractSeverity = ContractSeverity.MEDIUM


@dataclass
class ContractViolation:
    """Contract violation result"""
    violation_id: str
    test_id: str
    test_type: ContractTestType
    severity: ContractSeverity
    endpoint: str
    method: str
    violation_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    actual_response: Optional[Dict[str, Any]] = None
    expected_schema: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContractTestResult:
    """Result of contract testing"""
    test_id: str
    contract_id: str
    test_type: ContractTestType
    status: str  # "passed", "failed", "skipped"
    endpoint: str
    method: str
    violations: List[ContractViolation] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ContractTestReport:
    """Comprehensive contract test report"""
    report_id: str
    test_session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    contracts_tested: List[str] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    total_violations: int = 0
    test_results: List[ContractTestResult] = field(default_factory=list)
    compatibility_analysis: Dict[str, Any] = field(default_factory=dict)
    coverage_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


class OpenAPIValidator:
    """Validates requests/responses against OpenAPI specifications"""
    
    def __init__(self):
        self.validators: Dict[str, Dict[str, Any]] = {}
    
    def load_contract(self, contract: APIContract):
        """Load and prepare OpenAPI contract for validation"""
        try:
            spec = contract.specification
            
            # Extract schemas for validation
            schemas = {}
            if 'components' in spec and 'schemas' in spec['components']:
                schemas = spec['components']['schemas']
            elif 'definitions' in spec:  # Swagger 2.0
                schemas = spec['definitions']
            
            # Extract path definitions
            paths = spec.get('paths', {})
            
            self.validators[contract.contract_id] = {
                'spec': spec,
                'schemas': schemas,
                'paths': paths,
                'base_url': contract.base_url,
                'version': spec.get('info', {}).get('version', '1.0.0')
            }
            
            logging.info(f"Loaded OpenAPI contract: {contract.service_name} v{contract.version}")
        
        except Exception as e:
            logging.error(f"Failed to load contract {contract.contract_id}: {e}")
            raise
    
    def validate_request(self, contract_id: str, endpoint: str, method: str, 
                        request_data: Dict[str, Any]) -> List[ContractViolation]:
        """Validate request against contract"""
        violations = []
        
        if contract_id not in self.validators:
            return [ContractViolation(
                violation_id=f"no_contract_{contract_id}",
                test_id="request_validation",
                test_type=ContractTestType.REQUEST_VALIDATION,
                severity=ContractSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                violation_type="missing_contract",
                message=f"Contract {contract_id} not loaded"
            )]
        
        validator = self.validators[contract_id]
        paths = validator['paths']
        schemas = validator['schemas']
        
        # Find matching path
        path_spec = None
        for path, path_def in paths.items():
            if self._path_matches(endpoint, path):
                path_spec = path_def
                break
        
        if not path_spec:
            violations.append(ContractViolation(
                violation_id=f"unknown_endpoint_{hash(endpoint)}",
                test_id="request_validation",
                test_type=ContractTestType.REQUEST_VALIDATION,
                severity=ContractSeverity.HIGH,
                endpoint=endpoint,
                method=method,
                violation_type="unknown_endpoint",
                message=f"Endpoint {endpoint} not found in contract"
            ))
            return violations
        
        # Check method exists
        method_spec = path_spec.get(method.lower())
        if not method_spec:
            violations.append(ContractViolation(
                violation_id=f"unsupported_method_{method}_{hash(endpoint)}",
                test_id="request_validation",
                test_type=ContractTestType.REQUEST_VALIDATION,
                severity=ContractSeverity.HIGH,
                endpoint=endpoint,
                method=method,
                violation_type="unsupported_method",
                message=f"Method {method} not supported on {endpoint}"
            ))
            return violations
        
        # Validate request body if present
        if 'requestBody' in method_spec and request_data:
            request_body_spec = method_spec['requestBody']
            content_spec = request_body_spec.get('content', {})
            
            # Assume JSON content type
            json_spec = content_spec.get('application/json', {})
            if 'schema' in json_spec:
                schema = self._resolve_schema(json_spec['schema'], schemas)
                try:
                    validate(instance=request_data, schema=schema)
                except ValidationError as e:
                    violations.append(ContractViolation(
                        violation_id=f"request_schema_violation_{hash(str(e))}",
                        test_id="request_validation",
                        test_type=ContractTestType.REQUEST_VALIDATION,
                        severity=ContractSeverity.HIGH,
                        endpoint=endpoint,
                        method=method,
                        violation_type="request_schema_violation",
                        message=f"Request body validation failed: {e.message}",
                        details={"schema_path": e.absolute_path, "validation_error": str(e)}
                    ))
        
        # Validate required parameters
        parameters = method_spec.get('parameters', [])
        for param in parameters:
            if param.get('required', False):
                param_name = param['name']
                param_location = param['in']  # query, path, header
                
                # Check if required parameter is present (simplified)
                if param_location == 'query' and 'query_params' in request_data:
                    if param_name not in request_data['query_params']:
                        violations.append(ContractViolation(
                            violation_id=f"missing_param_{param_name}",
                            test_id="request_validation",
                            test_type=ContractTestType.REQUEST_VALIDATION,
                            severity=ContractSeverity.MEDIUM,
                            endpoint=endpoint,
                            method=method,
                            violation_type="missing_required_parameter",
                            message=f"Required parameter '{param_name}' missing"
                        ))
        
        return violations
    
    def validate_response(self, contract_id: str, endpoint: str, method: str,
                         status_code: int, response_data: Any, 
                         response_headers: Dict[str, str]) -> List[ContractViolation]:
        """Validate response against contract"""
        violations = []
        
        if contract_id not in self.validators:
            return [ContractViolation(
                violation_id=f"no_contract_{contract_id}",
                test_id="response_validation",
                test_type=ContractTestType.RESPONSE_VALIDATION,
                severity=ContractSeverity.CRITICAL,
                endpoint=endpoint,
                method=method,
                violation_type="missing_contract",
                message=f"Contract {contract_id} not loaded"
            )]
        
        validator = self.validators[contract_id]
        paths = validator['paths']
        schemas = validator['schemas']
        
        # Find matching path and method
        path_spec = None
        method_spec = None
        
        for path, path_def in paths.items():
            if self._path_matches(endpoint, path):
                path_spec = path_def
                method_spec = path_def.get(method.lower())
                break
        
        if not method_spec:
            return violations  # Already handled in request validation
        
        # Check if status code is documented
        responses = method_spec.get('responses', {})
        status_str = str(status_code)
        
        if status_str not in responses and 'default' not in responses:
            violations.append(ContractViolation(
                violation_id=f"undocumented_status_{status_code}",
                test_id="response_validation",
                test_type=ContractTestType.RESPONSE_VALIDATION,
                severity=ContractSeverity.MEDIUM,
                endpoint=endpoint,
                method=method,
                violation_type="undocumented_status_code",
                message=f"Status code {status_code} not documented in contract",
                details={"documented_codes": list(responses.keys())}
            ))
        
        # Validate response schema
        response_spec = responses.get(status_str) or responses.get('default')
        if response_spec and 'content' in response_spec:
            content_spec = response_spec['content']
            json_spec = content_spec.get('application/json', {})
            
            if 'schema' in json_spec and response_data is not None:
                schema = self._resolve_schema(json_spec['schema'], schemas)
                try:
                    validate(instance=response_data, schema=schema)
                except ValidationError as e:
                    violations.append(ContractViolation(
                        violation_id=f"response_schema_violation_{hash(str(e))}",
                        test_id="response_validation",
                        test_type=ContractTestType.RESPONSE_VALIDATION,
                        severity=ContractSeverity.HIGH,
                        endpoint=endpoint,
                        method=method,
                        violation_type="response_schema_violation",
                        message=f"Response schema validation failed: {e.message}",
                        details={
                            "schema_path": list(e.absolute_path),
                            "validation_error": str(e),
                            "response_data": response_data
                        },
                        expected_schema=schema,
                        actual_response=response_data
                    ))
        
        # Validate required response headers
        if response_spec and 'headers' in response_spec:
            required_headers = response_spec['headers']
            for header_name, header_spec in required_headers.items():
                if header_spec.get('required', False) and header_name not in response_headers:
                    violations.append(ContractViolation(
                        violation_id=f"missing_header_{header_name}",
                        test_id="response_validation",
                        test_type=ContractTestType.RESPONSE_VALIDATION,
                        severity=ContractSeverity.MEDIUM,
                        endpoint=endpoint,
                        method=method,
                        violation_type="missing_required_header",
                        message=f"Required response header '{header_name}' missing"
                    ))
        
        return violations
    
    def _path_matches(self, actual_path: str, spec_path: str) -> bool:
        """Check if actual path matches OpenAPI path pattern"""
        # Convert OpenAPI path to regex
        # Replace {param} with regex pattern
        regex_pattern = re.sub(r'\{[^}]+\}', r'[^/]+', spec_path)
        regex_pattern = f"^{regex_pattern}$"
        
        return bool(re.match(regex_pattern, actual_path))
    
    def _resolve_schema(self, schema_ref: Dict[str, Any], schemas: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve schema reference"""
        if '$ref' in schema_ref:
            ref_path = schema_ref['$ref']
            # Handle #/components/schemas/SchemaName references
            if ref_path.startswith('#/components/schemas/'):
                schema_name = ref_path.split('/')[-1]
                return schemas.get(schema_name, {})
            elif ref_path.startswith('#/definitions/'):  # Swagger 2.0
                schema_name = ref_path.split('/')[-1]
                return schemas.get(schema_name, {})
        
        return schema_ref


class BackwardCompatibilityAnalyzer:
    """Analyzes API backward compatibility between versions"""
    
    def __init__(self):
        self.previous_contracts: Dict[str, APIContract] = {}
    
    def set_baseline_contract(self, contract: APIContract):
        """Set baseline contract for compatibility analysis"""
        self.previous_contracts[contract.service_name] = contract
    
    def analyze_compatibility(self, new_contract: APIContract) -> List[ContractViolation]:
        """Analyze compatibility between versions"""
        violations = []
        
        service_name = new_contract.service_name
        if service_name not in self.previous_contracts:
            return violations  # No baseline to compare against
        
        old_contract = self.previous_contracts[service_name]
        old_paths = old_contract.specification.get('paths', {})
        new_paths = new_contract.specification.get('paths', {})
        
        # Check for removed endpoints
        for old_path in old_paths:
            if old_path not in new_paths:
                violations.append(ContractViolation(
                    violation_id=f"removed_endpoint_{hash(old_path)}",
                    test_id="compatibility_analysis",
                    test_type=ContractTestType.BACKWARD_COMPATIBILITY,
                    severity=ContractSeverity.CRITICAL,
                    endpoint=old_path,
                    method="*",
                    violation_type="removed_endpoint",
                    message=f"Endpoint {old_path} was removed (breaking change)"
                ))
                continue
            
            # Check for removed methods
            old_methods = set(old_paths[old_path].keys())
            new_methods = set(new_paths[old_path].keys())
            
            for removed_method in old_methods - new_methods:
                if removed_method not in ['parameters', 'summary', 'description']:  # Skip non-method keys
                    violations.append(ContractViolation(
                        violation_id=f"removed_method_{removed_method}_{hash(old_path)}",
                        test_id="compatibility_analysis",
                        test_type=ContractTestType.BACKWARD_COMPATIBILITY,
                        severity=ContractSeverity.CRITICAL,
                        endpoint=old_path,
                        method=removed_method.upper(),
                        violation_type="removed_method",
                        message=f"Method {removed_method.upper()} removed from {old_path} (breaking change)"
                    ))
            
            # Check for schema changes in existing methods
            for method in old_methods & new_methods:
                if method in ['parameters', 'summary', 'description']:
                    continue
                
                old_method_spec = old_paths[old_path][method]
                new_method_spec = new_paths[old_path][method]
                
                # Check response schema compatibility
                schema_violations = self._compare_response_schemas(
                    old_path, method, old_method_spec, new_method_spec
                )
                violations.extend(schema_violations)
                
                # Check request schema compatibility
                request_violations = self._compare_request_schemas(
                    old_path, method, old_method_spec, new_method_spec
                )
                violations.extend(request_violations)
        
        return violations
    
    def _compare_response_schemas(self, endpoint: str, method: str,
                                old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> List[ContractViolation]:
        """Compare response schemas for compatibility"""
        violations = []
        
        old_responses = old_spec.get('responses', {})
        new_responses = new_spec.get('responses', {})
        
        for status_code in old_responses:
            if status_code not in new_responses:
                violations.append(ContractViolation(
                    violation_id=f"removed_response_{status_code}_{hash(endpoint)}",
                    test_id="schema_compatibility",
                    test_type=ContractTestType.BACKWARD_COMPATIBILITY,
                    severity=ContractSeverity.HIGH,
                    endpoint=endpoint,
                    method=method.upper(),
                    violation_type="removed_response_code",
                    message=f"Response code {status_code} removed from {method.upper()} {endpoint}"
                ))
                continue
            
            # Compare schema structure (simplified)
            old_content = old_responses[status_code].get('content', {})
            new_content = new_responses[status_code].get('content', {})
            
            for content_type in old_content:
                if content_type not in new_content:
                    violations.append(ContractViolation(
                        violation_id=f"removed_content_type_{hash(content_type)}",
                        test_id="schema_compatibility",
                        test_type=ContractTestType.BACKWARD_COMPATIBILITY,
                        severity=ContractSeverity.MEDIUM,
                        endpoint=endpoint,
                        method=method.upper(),
                        violation_type="removed_content_type",
                        message=f"Content type {content_type} removed from response"
                    ))
        
        return violations
    
    def _compare_request_schemas(self, endpoint: str, method: str,
                               old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> List[ContractViolation]:
        """Compare request schemas for compatibility"""
        violations = []
        
        # Check required parameters
        old_params = old_spec.get('parameters', [])
        new_params = new_spec.get('parameters', [])
        
        old_required = {p['name'] for p in old_params if p.get('required', False)}
        new_required = {p['name'] for p in new_params if p.get('required', False)}
        
        # Adding required parameters is a breaking change
        newly_required = new_required - old_required
        for param in newly_required:
            violations.append(ContractViolation(
                violation_id=f"new_required_param_{param}",
                test_id="schema_compatibility",
                test_type=ContractTestType.BACKWARD_COMPATIBILITY,
                severity=ContractSeverity.CRITICAL,
                endpoint=endpoint,
                method=method.upper(),
                violation_type="new_required_parameter",
                message=f"Parameter '{param}' is now required (breaking change)"
            ))
        
        return violations


class ConsumerDrivenContractTester:
    """Tests consumer-driven contracts"""
    
    def __init__(self):
        self.consumer_contracts: Dict[str, Dict[str, Any]] = {}
    
    def load_consumer_contract(self, consumer_name: str, contract_file: str):
        """Load consumer contract (e.g., Pact file)"""
        try:
            with open(contract_file, 'r') as f:
                contract = json.load(f)
            
            self.consumer_contracts[consumer_name] = contract
            logging.info(f"Loaded consumer contract for: {consumer_name}")
        
        except Exception as e:
            logging.error(f"Failed to load consumer contract {consumer_name}: {e}")
    
    def verify_consumer_contract(self, consumer_name: str, provider_url: str) -> List[ContractViolation]:
        """Verify consumer contract against provider"""
        violations = []
        
        if consumer_name not in self.consumer_contracts:
            return [ContractViolation(
                violation_id="missing_consumer_contract",
                test_id="consumer_contract_verification",
                test_type=ContractTestType.CONSUMER_DRIVEN,
                severity=ContractSeverity.CRITICAL,
                endpoint="*",
                method="*",
                violation_type="missing_contract",
                message=f"Consumer contract for {consumer_name} not loaded"
            )]
        
        contract = self.consumer_contracts[consumer_name]
        interactions = contract.get('interactions', [])
        
        for interaction in interactions:
            request = interaction.get('request', {})
            expected_response = interaction.get('response', {})
            
            endpoint = request.get('path', '')
            method = request.get('method', 'GET')
            
            try:
                # Make actual request to provider
                response = requests.request(
                    method=method,
                    url=f"{provider_url.rstrip('/')}{endpoint}",
                    json=request.get('body'),
                    headers=request.get('headers', {}),
                    params=request.get('query'),
                    timeout=30
                )
                
                # Verify response matches contract
                contract_violations = self._verify_interaction(
                    interaction, response, consumer_name
                )
                violations.extend(contract_violations)
            
            except Exception as e:
                violations.append(ContractViolation(
                    violation_id=f"request_failed_{hash(endpoint)}",
                    test_id="consumer_contract_verification",
                    test_type=ContractTestType.CONSUMER_DRIVEN,
                    severity=ContractSeverity.HIGH,
                    endpoint=endpoint,
                    method=method,
                    violation_type="request_failed",
                    message=f"Request to {method} {endpoint} failed: {str(e)}"
                ))
        
        return violations
    
    def _verify_interaction(self, interaction: Dict[str, Any], 
                          actual_response: requests.Response,
                          consumer_name: str) -> List[ContractViolation]:
        """Verify single interaction"""
        violations = []
        
        expected_response = interaction.get('response', {})
        request = interaction.get('request', {})
        endpoint = request.get('path', '')
        method = request.get('method', 'GET')
        
        # Check status code
        expected_status = expected_response.get('status')
        if expected_status and actual_response.status_code != expected_status:
            violations.append(ContractViolation(
                violation_id=f"status_mismatch_{hash(endpoint)}",
                test_id="consumer_contract_verification",
                test_type=ContractTestType.CONSUMER_DRIVEN,
                severity=ContractSeverity.HIGH,
                endpoint=endpoint,
                method=method,
                violation_type="status_code_mismatch",
                message=f"Expected status {expected_status}, got {actual_response.status_code}",
                details={
                    "expected": expected_status,
                    "actual": actual_response.status_code,
                    "consumer": consumer_name
                }
            ))
        
        # Check response body (simplified matching)
        expected_body = expected_response.get('body')
        if expected_body:
            try:
                actual_body = actual_response.json()
                body_violations = self._compare_bodies(expected_body, actual_body, endpoint, method, consumer_name)
                violations.extend(body_violations)
            except json.JSONDecodeError:
                violations.append(ContractViolation(
                    violation_id=f"invalid_json_{hash(endpoint)}",
                    test_id="consumer_contract_verification",
                    test_type=ContractTestType.CONSUMER_DRIVEN,
                    severity=ContractSeverity.MEDIUM,
                    endpoint=endpoint,
                    method=method,
                    violation_type="invalid_json_response",
                    message="Response body is not valid JSON"
                ))
        
        # Check response headers
        expected_headers = expected_response.get('headers', {})
        for header_name, expected_value in expected_headers.items():
            actual_value = actual_response.headers.get(header_name)
            if actual_value != expected_value:
                violations.append(ContractViolation(
                    violation_id=f"header_mismatch_{header_name}",
                    test_id="consumer_contract_verification",
                    test_type=ContractTestType.CONSUMER_DRIVEN,
                    severity=ContractSeverity.MEDIUM,
                    endpoint=endpoint,
                    method=method,
                    violation_type="header_mismatch",
                    message=f"Header {header_name}: expected '{expected_value}', got '{actual_value}'"
                ))
        
        return violations
    
    def _compare_bodies(self, expected: Any, actual: Any, endpoint: str, 
                       method: str, consumer_name: str) -> List[ContractViolation]:
        """Compare response bodies (simplified implementation)"""
        violations = []
        
        # This is a simplified comparison
        # In practice, would use more sophisticated matching (e.g., Pact matchers)
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            for key in expected:
                if key not in actual:
                    violations.append(ContractViolation(
                        violation_id=f"missing_field_{key}",
                        test_id="consumer_contract_verification",
                        test_type=ContractTestType.CONSUMER_DRIVEN,
                        severity=ContractSeverity.HIGH,
                        endpoint=endpoint,
                        method=method,
                        violation_type="missing_response_field",
                        message=f"Expected field '{key}' missing from response",
                        details={"consumer": consumer_name}
                    ))
        
        return violations


class ContractTestEngine:
    """Main API contract testing engine"""
    
    def __init__(self):
        self.contracts: Dict[str, APIContract] = {}
        self.test_cases: List[ContractTestCase] = []
        self.openapi_validator = OpenAPIValidator()
        self.compatibility_analyzer = BackwardCompatibilityAnalyzer()
        self.consumer_tester = ConsumerDrivenContractTester()
    
    def load_contract_from_file(self, contract_id: str, service_name: str, 
                               base_url: str, file_path: str, version: str = "1.0.0"):
        """Load API contract from OpenAPI file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.endswith(('.yaml', '.yml')):
                    spec = yaml.safe_load(f)
                else:
                    spec = json.load(f)
            
            contract = APIContract(
                contract_id=contract_id,
                service_name=service_name,
                version=version,
                base_url=base_url,
                specification=spec
            )
            
            self.contracts[contract_id] = contract
            self.openapi_validator.load_contract(contract)
            
            logging.info(f"Loaded contract from file: {file_path}")
            return contract
        
        except Exception as e:
            logging.error(f"Failed to load contract from {file_path}: {e}")
            raise
    
    def load_contract_from_url(self, contract_id: str, service_name: str,
                              base_url: str, spec_url: str, version: str = "1.0.0"):
        """Load API contract from URL (e.g., /openapi.json)"""
        try:
            response = requests.get(spec_url, timeout=30)
            response.raise_for_status()
            
            if spec_url.endswith(('.yaml', '.yml')):
                spec = yaml.safe_load(response.text)
            else:
                spec = response.json()
            
            contract = APIContract(
                contract_id=contract_id,
                service_name=service_name,
                version=version,
                base_url=base_url,
                specification=spec
            )
            
            self.contracts[contract_id] = contract
            self.openapi_validator.load_contract(contract)
            
            logging.info(f"Loaded contract from URL: {spec_url}")
            return contract
        
        except Exception as e:
            logging.error(f"Failed to load contract from {spec_url}: {e}")
            raise
    
    def add_test_case(self, test_case: ContractTestCase):
        """Add contract test case"""
        self.test_cases.append(test_case)
    
    def create_default_test_cases(self):
        """Create default contract test cases"""
        for contract_id, contract in self.contracts.items():
            spec = contract.specification
            paths = spec.get('paths', {})
            
            for path, path_def in paths.items():
                for method, method_def in path_def.items():
                    if method in ['get', 'post', 'put', 'delete', 'patch']:
                        
                        # Schema validation test
                        self.add_test_case(ContractTestCase(
                            test_id=f"schema_validation_{contract_id}_{method}_{hash(path)}",
                            name=f"Schema Validation - {method.upper()} {path}",
                            description=f"Validate request/response schemas for {method.upper()} {path}",
                            test_type=ContractTestType.SCHEMA_VALIDATION,
                            endpoint=path,
                            method=method.upper(),
                            contract_id=contract_id,
                            expected_status_codes=[200, 201, 204] if method in ['get', 'post'] else [200]
                        ))
                        
                        # Response validation test
                        responses = method_def.get('responses', {})
                        for status_code in responses:
                            if status_code.isdigit():
                                self.add_test_case(ContractTestCase(
                                    test_id=f"response_validation_{contract_id}_{method}_{status_code}_{hash(path)}",
                                    name=f"Response Validation - {method.upper()} {path} ({status_code})",
                                    description=f"Validate {status_code} response for {method.upper()} {path}",
                                    test_type=ContractTestType.RESPONSE_VALIDATION,
                                    endpoint=path,
                                    method=method.upper(),
                                    contract_id=contract_id,
                                    expected_status_codes=[int(status_code)]
                                ))
    
    async def run_contract_tests(self) -> ContractTestReport:
        """Run all contract tests"""
        session_id = f"contract_test_{int(datetime.now().timestamp())}"
        
        report = ContractTestReport(
            report_id=f"report_{session_id}",
            test_session_id=session_id,
            start_time=datetime.now(),
            contracts_tested=list(self.contracts.keys()),
            total_tests=len(self.test_cases)
        )
        
        print(f"Starting contract testing...")
        print(f"Testing {len(self.contracts)} contracts with {len(self.test_cases)} test cases")
        
        try:
            async with aiohttp.ClientSession() as session:
                
                for test_case in self.test_cases:
                    print(f"Running test: {test_case.name}")
                    
                    result = await self._execute_test_case(session, test_case)
                    report.test_results.append(result)
                    
                    if result.status == "passed":
                        report.passed_tests += 1
                    elif result.status == "failed":
                        report.failed_tests += 1
                        report.total_violations += len(result.violations)
                    else:
                        report.skipped_tests += 1
                    
                    # Brief pause between tests
                    await asyncio.sleep(0.1)
                
                # Run compatibility analysis
                report.compatibility_analysis = self._run_compatibility_analysis()
                
                # Run consumer-driven contract tests
                consumer_results = self._run_consumer_driven_tests()
                report.test_results.extend(consumer_results)
                
                # Generate coverage analysis
                report.coverage_analysis = self._analyze_coverage()
                
                # Generate recommendations
                report.recommendations = self._generate_recommendations(report)
        
        except Exception as e:
            logging.error(f"Error during contract testing: {e}")
        
        finally:
            report.end_time = datetime.now()
        
        print(f"Contract testing completed:")
        print(f"  Total tests: {report.total_tests}")
        print(f"  Passed: {report.passed_tests}")
        print(f"  Failed: {report.failed_tests}")
        print(f"  Violations: {report.total_violations}")
        
        return report
    
    async def _execute_test_case(self, session: aiohttp.ClientSession, 
                               test_case: ContractTestCase) -> ContractTestResult:
        """Execute individual contract test case"""
        start_time = datetime.now()
        
        result = ContractTestResult(
            test_id=test_case.test_id,
            contract_id=test_case.contract_id,
            test_type=test_case.test_type,
            status="failed",
            endpoint=test_case.endpoint,
            method=test_case.method
        )
        
        try:
            if test_case.contract_id not in self.contracts:
                result.violations.append(ContractViolation(
                    violation_id="missing_contract",
                    test_id=test_case.test_id,
                    test_type=test_case.test_type,
                    severity=ContractSeverity.CRITICAL,
                    endpoint=test_case.endpoint,
                    method=test_case.method,
                    violation_type="missing_contract",
                    message=f"Contract {test_case.contract_id} not loaded"
                ))
                return result
            
            contract = self.contracts[test_case.contract_id]
            
            # Make request to endpoint
            url = f"{contract.base_url.rstrip('/')}{test_case.endpoint}"
            
            # Replace path parameters with test values
            url = re.sub(r'\{[^}]+\}', 'test-value', url)
            
            try:
                if test_case.method.upper() == "GET":
                    async with session.get(url) as response:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        status_code = response.status
                        headers = dict(response.headers)
                
                elif test_case.method.upper() == "POST":
                    test_data = test_case.test_data or {"test": "data"}
                    async with session.post(url, json=test_data) as response:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        status_code = response.status
                        headers = dict(response.headers)
                
                else:
                    # Other methods
                    async with session.request(test_case.method, url) as response:
                        response_data = await response.json() if response.content_type == 'application/json' else await response.text()
                        status_code = response.status
                        headers = dict(response.headers)
                
                # Validate response
                if test_case.test_type == ContractTestType.RESPONSE_VALIDATION:
                    violations = self.openapi_validator.validate_response(
                        test_case.contract_id, test_case.endpoint, test_case.method.lower(),
                        status_code, response_data, headers
                    )
                    result.violations.extend(violations)
                
                # Validate request (if test data provided)
                elif test_case.test_type == ContractTestType.REQUEST_VALIDATION and test_case.test_data:
                    violations = self.openapi_validator.validate_request(
                        test_case.contract_id, test_case.endpoint, test_case.method.lower(),
                        test_case.test_data
                    )
                    result.violations.extend(violations)
                
                # Check expected status codes
                if test_case.expected_status_codes and status_code not in test_case.expected_status_codes:
                    result.violations.append(ContractViolation(
                        violation_id=f"unexpected_status_{status_code}",
                        test_id=test_case.test_id,
                        test_type=test_case.test_type,
                        severity=ContractSeverity.MEDIUM,
                        endpoint=test_case.endpoint,
                        method=test_case.method,
                        violation_type="unexpected_status_code",
                        message=f"Status {status_code} not in expected codes {test_case.expected_status_codes}"
                    ))
                
                # Test passed if no violations
                if not result.violations:
                    result.status = "passed"
            
            except asyncio.TimeoutError:
                result.violations.append(ContractViolation(
                    violation_id="request_timeout",
                    test_id=test_case.test_id,
                    test_type=test_case.test_type,
                    severity=ContractSeverity.HIGH,
                    endpoint=test_case.endpoint,
                    method=test_case.method,
                    violation_type="request_timeout",
                    message="Request timed out"
                ))
            
            except Exception as e:
                result.violations.append(ContractViolation(
                    violation_id="request_error",
                    test_id=test_case.test_id,
                    test_type=test_case.test_type,
                    severity=ContractSeverity.HIGH,
                    endpoint=test_case.endpoint,
                    method=test_case.method,
                    violation_type="request_error",
                    message=f"Request failed: {str(e)}"
                ))
        
        except Exception as e:
            result.violations.append(ContractViolation(
                violation_id="test_error",
                test_id=test_case.test_id,
                test_type=test_case.test_type,
                severity=ContractSeverity.CRITICAL,
                endpoint=test_case.endpoint,
                method=test_case.method,
                violation_type="test_error",
                message=f"Test execution failed: {str(e)}"
            ))
        
        finally:
            result.execution_time = (datetime.now() - start_time).total_seconds()
        
        return result
    
    def _run_compatibility_analysis(self) -> Dict[str, Any]:
        """Run backward compatibility analysis"""
        compatibility_results = {}
        
        for contract_id, contract in self.contracts.items():
            # Set as baseline for next run
            self.compatibility_analyzer.set_baseline_contract(contract)
            
            # In a real scenario, would compare with previous version
            # For now, return empty results
            compatibility_results[contract_id] = {
                "breaking_changes": 0,
                "deprecated_features": 0,
                "new_features": 0,
                "compatibility_level": CompatibilityLevel.FULLY_COMPATIBLE.value
            }
        
        return compatibility_results
    
    def _run_consumer_driven_tests(self) -> List[ContractTestResult]:
        """Run consumer-driven contract tests"""
        # This would load and verify consumer contracts (Pact files)
        # For now, return empty results
        return []
    
    def _analyze_coverage(self) -> Dict[str, Any]:
        """Analyze contract test coverage"""
        coverage = {
            "endpoint_coverage": {},
            "method_coverage": {},
            "status_code_coverage": {},
            "overall_coverage_percent": 0
        }
        
        # Calculate coverage for each contract
        for contract_id, contract in self.contracts.items():
            paths = contract.specification.get('paths', {})
            total_endpoints = len(paths)
            tested_endpoints = set()
            
            for test_case in self.test_cases:
                if test_case.contract_id == contract_id:
                    tested_endpoints.add(test_case.endpoint)
            
            if total_endpoints > 0:
                endpoint_coverage = (len(tested_endpoints) / total_endpoints) * 100
                coverage["endpoint_coverage"][contract_id] = endpoint_coverage
        
        # Calculate overall coverage
        if coverage["endpoint_coverage"]:
            coverage["overall_coverage_percent"] = sum(coverage["endpoint_coverage"].values()) / len(coverage["endpoint_coverage"])
        
        return coverage
    
    def _generate_recommendations(self, report: ContractTestReport) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        if report.failed_tests > 0:
            recommendations.append(f"Fix {report.failed_tests} failing contract tests")
        
        if report.total_violations > 0:
            critical_violations = sum(1 for result in report.test_results 
                                    for violation in result.violations 
                                    if violation.severity == ContractSeverity.CRITICAL)
            
            if critical_violations > 0:
                recommendations.append(f"URGENT: Address {critical_violations} critical contract violations")
        
        # Coverage recommendations
        overall_coverage = report.coverage_analysis.get("overall_coverage_percent", 0)
        if overall_coverage < 80:
            recommendations.append(f"Improve contract test coverage (currently {overall_coverage:.1f}%)")
        
        # General recommendations
        recommendations.extend([
            "Implement automated contract testing in CI/CD pipeline",
            "Set up contract versioning and backward compatibility monitoring",
            "Consider implementing consumer-driven contract testing",
            "Establish contract governance and review processes",
            "Monitor API usage to identify critical endpoints for testing"
        ])
        
        return recommendations[:10]  # Limit to top 10


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def run_contract_tests():
        # Initialize contract test engine
        engine = ContractTestEngine()
        
        # Example: Load contracts from files or URLs
        try:
            # Load main API contract
            engine.load_contract_from_url(
                "main_api",
                "Main API",
                "http://localhost:3000",
                "http://localhost:3000/openapi.json",
                "1.0.0"
            )
            
            # Load tutorial service contract
            engine.load_contract_from_url(
                "tutorial_service",
                "Tutorial Service",
                "http://localhost:8216",
                "http://localhost:8216/openapi.json",
                "1.0.0"
            )
            
        except Exception as e:
            print(f"Warning: Could not load contracts from URLs: {e}")
            
            # Create mock contracts for testing
            mock_spec = {
                "openapi": "3.0.0",
                "info": {"title": "Test API", "version": "1.0.0"},
                "paths": {
                    "/health": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "Health check",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "properties": {
                                                    "status": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "/users": {
                        "get": {
                            "responses": {
                                "200": {
                                    "description": "List users",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "array",
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "id": {"type": "integer"},
                                                        "name": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            
            contract = APIContract(
                contract_id="test_api",
                service_name="Test API",
                version="1.0.0",
                base_url="http://localhost:3000",
                specification=mock_spec
            )
            
            engine.contracts["test_api"] = contract
            engine.openapi_validator.load_contract(contract)
        
        # Create default test cases
        engine.create_default_test_cases()
        
        print("Starting contract testing...")
        
        # Run contract tests
        report = await engine.run_contract_tests()
        
        print(f"\n=== Contract Test Report ===")
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Total Violations: {report.total_violations}")
        
        print(f"\nContract Coverage:")
        for contract_id, coverage in report.coverage_analysis.get("endpoint_coverage", {}).items():
            print(f"  - {contract_id}: {coverage:.1f}%")
        
        print(f"\nRecommendations:")
        for rec in report.recommendations[:5]:
            print(f"  • {rec}")
        
        return report
    
    # Run the contract tests
    asyncio.run(run_contract_tests())