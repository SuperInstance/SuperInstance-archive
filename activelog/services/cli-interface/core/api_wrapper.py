#!/usr/bin/env python3
"""
API Wrapper - Provides unified REST API interface with authentication and retry logic
Handles service discovery, authentication, rate limiting, and error recovery
"""

import asyncio
import aiohttp
import requests
import json
import time
import logging
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
import backoff
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ServiceEndpoint:
    """Service endpoint configuration"""
    name: str
    base_url: str
    port: int
    health_endpoint: str = "/health"
    api_prefix: str = "/api"
    timeout: int = 30
    max_retries: int = 3


@dataclass
class APIRequest:
    """API request configuration"""
    service: str
    endpoint: str
    method: str = "GET"
    payload: Optional[Dict[str, Any]] = None
    headers: Optional[Dict[str, str]] = None
    timeout: Optional[int] = None
    retries: Optional[int] = None


@dataclass
class APIResponse:
    """API response wrapper"""
    success: bool
    status_code: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    response_time_ms: int = 0
    service: Optional[str] = None
    endpoint: Optional[str] = None


class APIWrapper:
    """Unified API wrapper with service discovery and intelligent routing"""
    
    def __init__(self, config):
        self.config = config
        self.session = requests.Session()
        self.async_session = None
        
        # Service registry
        self.services = self._initialize_service_registry()
        
        # Authentication tokens
        self.auth_tokens = {}
        self.token_refresh_callbacks = {}
        
        # Circuit breaker state
        self.circuit_breakers = {}
        
        # Request statistics
        self.request_stats = {}
        
        # Configure session
        self._configure_session()
        
        logger.info("API Wrapper initialized with service discovery")

    def _initialize_service_registry(self) -> Dict[str, ServiceEndpoint]:
        """Initialize service registry with known endpoints"""
        return {
            "auth": ServiceEndpoint(
                name="auth",
                base_url="http://localhost",
                port=8301,
                health_endpoint="/health",
                api_prefix="/api/v1"
            ),
            "file-manager": ServiceEndpoint(
                name="file-manager",
                base_url="http://localhost",
                port=8302,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "search": ServiceEndpoint(
                name="search",
                base_url="http://localhost",
                port=8303,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "data-manager": ServiceEndpoint(
                name="data-manager",
                base_url="http://localhost",
                port=8304,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "ai-orchestrator": ServiceEndpoint(
                name="ai-orchestrator",
                base_url="http://localhost",
                port=8305,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "sync-engine": ServiceEndpoint(
                name="sync-engine",
                base_url="http://localhost",
                port=8306,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "metadata": ServiceEndpoint(
                name="metadata",
                base_url="http://localhost",
                port=8307,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "graphql": ServiceEndpoint(
                name="graphql",
                base_url="http://localhost",
                port=8308,
                health_endpoint="/health",
                api_prefix="/graphql"
            ),
            "batch-import": ServiceEndpoint(
                name="batch-import",
                base_url="http://localhost",
                port=8309,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "file-watcher": ServiceEndpoint(
                name="file-watcher",
                base_url="http://localhost",
                port=8310,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "api-gateway": ServiceEndpoint(
                name="api-gateway",
                base_url="http://localhost",
                port=8311,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "membership-migration": ServiceEndpoint(
                name="membership-migration",
                base_url="http://localhost",
                port=8336,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "economy-sim": ServiceEndpoint(
                name="economy-sim",
                base_url="http://localhost",
                port=8340,
                health_endpoint="/health",
                api_prefix="/api"
            ),
            "cli-interface": ServiceEndpoint(
                name="cli-interface",
                base_url="http://localhost",
                port=8342,
                health_endpoint="/health",
                api_prefix="/api"
            )
        }

    def _configure_session(self):
        """Configure HTTP session with defaults"""
        self.session.headers.update({
            'User-Agent': 'ActiveLog-API-Wrapper/1.0.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        
        # Configure retries
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def make_request(self, service: str, endpoint: str, method: str = "GET", 
                    payload: Optional[Dict[str, Any]] = None, 
                    headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Make HTTP request to service with retry logic and error handling"""
        try:
            request = APIRequest(
                service=service,
                endpoint=endpoint,
                method=method,
                payload=payload,
                headers=headers
            )
            
            return self._execute_request(request)
            
        except Exception as e:
            logger.error(f"Request failed for {service}{endpoint}: {e}")
            return APIResponse(
                success=False,
                status_code=0,
                error=str(e),
                service=service,
                endpoint=endpoint
            )

    def _execute_request(self, request: APIRequest) -> APIResponse:
        """Execute HTTP request with timing and error handling"""
        start_time = time.time()
        
        try:
            # Get service endpoint
            service_endpoint = self.services.get(request.service)
            if not service_endpoint:
                return APIResponse(
                    success=False,
                    status_code=404,
                    error=f"Service '{request.service}' not found in registry",
                    service=request.service,
                    endpoint=request.endpoint
                )
            
            # Check circuit breaker
            if self._is_circuit_open(request.service):
                return APIResponse(
                    success=False,
                    status_code=503,
                    error="Circuit breaker open - service temporarily unavailable",
                    service=request.service,
                    endpoint=request.endpoint
                )
            
            # Build URL
            base_url = f"{service_endpoint.base_url}:{service_endpoint.port}"
            full_url = urljoin(base_url + service_endpoint.api_prefix, request.endpoint.lstrip('/'))
            
            # Prepare headers
            req_headers = self.session.headers.copy()
            if request.headers:
                req_headers.update(request.headers)
            
            # Add authentication if available
            auth_token = self.auth_tokens.get(request.service)
            if auth_token:
                req_headers['Authorization'] = f"Bearer {auth_token}"
            
            # Make request
            response = self._make_http_request(
                method=request.method,
                url=full_url,
                headers=req_headers,
                json=request.payload,
                timeout=request.timeout or service_endpoint.timeout
            )
            
            # Calculate response time
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Update statistics
            self._update_request_stats(request.service, response.status_code, response_time_ms)
            
            # Handle response
            if response.status_code < 400:
                # Success - reset circuit breaker
                self._reset_circuit_breaker(request.service)
                
                try:
                    data = response.json() if response.text else None
                except ValueError:
                    data = {"raw_response": response.text}
                
                return APIResponse(
                    success=True,
                    status_code=response.status_code,
                    data=data,
                    response_time_ms=response_time_ms,
                    service=request.service,
                    endpoint=request.endpoint
                )
            else:
                # Error - update circuit breaker
                self._record_failure(request.service)
                
                error_msg = self._extract_error_message(response)
                return APIResponse(
                    success=False,
                    status_code=response.status_code,
                    error=error_msg,
                    response_time_ms=response_time_ms,
                    service=request.service,
                    endpoint=request.endpoint
                )
                
        except requests.exceptions.Timeout:
            self._record_failure(request.service)
            return APIResponse(
                success=False,
                status_code=408,
                error="Request timeout",
                response_time_ms=int((time.time() - start_time) * 1000),
                service=request.service,
                endpoint=request.endpoint
            )
        except requests.exceptions.ConnectionError:
            self._record_failure(request.service)
            return APIResponse(
                success=False,
                status_code=503,
                error="Service unavailable - connection failed",
                response_time_ms=int((time.time() - start_time) * 1000),
                service=request.service,
                endpoint=request.endpoint
            )
        except Exception as e:
            self._record_failure(request.service)
            return APIResponse(
                success=False,
                status_code=500,
                error=f"Unexpected error: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                service=request.service,
                endpoint=request.endpoint
            )

    @backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
    def _make_http_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with exponential backoff"""
        return self.session.request(method, url, **kwargs)

    async def make_async_request(self, service: str, endpoint: str, method: str = "GET",
                                payload: Optional[Dict[str, Any]] = None,
                                headers: Optional[Dict[str, str]] = None) -> APIResponse:
        """Make asynchronous HTTP request"""
        try:
            if not self.async_session:
                self.async_session = aiohttp.ClientSession()
            
            request = APIRequest(
                service=service,
                endpoint=endpoint,
                method=method,
                payload=payload,
                headers=headers
            )
            
            return await self._execute_async_request(request)
            
        except Exception as e:
            logger.error(f"Async request failed for {service}{endpoint}: {e}")
            return APIResponse(
                success=False,
                status_code=0,
                error=str(e),
                service=service,
                endpoint=endpoint
            )

    async def _execute_async_request(self, request: APIRequest) -> APIResponse:
        """Execute asynchronous HTTP request"""
        start_time = time.time()
        
        try:
            # Get service endpoint
            service_endpoint = self.services.get(request.service)
            if not service_endpoint:
                return APIResponse(
                    success=False,
                    status_code=404,
                    error=f"Service '{request.service}' not found in registry",
                    service=request.service,
                    endpoint=request.endpoint
                )
            
            # Check circuit breaker
            if self._is_circuit_open(request.service):
                return APIResponse(
                    success=False,
                    status_code=503,
                    error="Circuit breaker open",
                    service=request.service,
                    endpoint=request.endpoint
                )
            
            # Build URL
            base_url = f"{service_endpoint.base_url}:{service_endpoint.port}"
            full_url = urljoin(base_url + service_endpoint.api_prefix, request.endpoint.lstrip('/'))
            
            # Prepare headers
            req_headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
            if request.headers:
                req_headers.update(request.headers)
            
            # Add authentication
            auth_token = self.auth_tokens.get(request.service)
            if auth_token:
                req_headers['Authorization'] = f"Bearer {auth_token}"
            
            # Make async request
            async with self.async_session.request(
                method=request.method,
                url=full_url,
                headers=req_headers,
                json=request.payload,
                timeout=aiohttp.ClientTimeout(total=request.timeout or service_endpoint.timeout)
            ) as response:
                
                response_time_ms = int((time.time() - start_time) * 1000)
                self._update_request_stats(request.service, response.status, response_time_ms)
                
                if response.status < 400:
                    self._reset_circuit_breaker(request.service)
                    
                    try:
                        data = await response.json()
                    except:
                        data = {"raw_response": await response.text()}
                    
                    return APIResponse(
                        success=True,
                        status_code=response.status,
                        data=data,
                        response_time_ms=response_time_ms,
                        service=request.service,
                        endpoint=request.endpoint
                    )
                else:
                    self._record_failure(request.service)
                    
                    try:
                        error_data = await response.json()
                        error_msg = error_data.get('error', f'HTTP {response.status}')
                    except:
                        error_msg = f'HTTP {response.status}: {await response.text()}'
                    
                    return APIResponse(
                        success=False,
                        status_code=response.status,
                        error=error_msg,
                        response_time_ms=response_time_ms,
                        service=request.service,
                        endpoint=request.endpoint
                    )
                    
        except asyncio.TimeoutError:
            self._record_failure(request.service)
            return APIResponse(
                success=False,
                status_code=408,
                error="Async request timeout",
                response_time_ms=int((time.time() - start_time) * 1000),
                service=request.service,
                endpoint=request.endpoint
            )
        except Exception as e:
            self._record_failure(request.service)
            return APIResponse(
                success=False,
                status_code=500,
                error=f"Async request error: {str(e)}",
                response_time_ms=int((time.time() - start_time) * 1000),
                service=request.service,
                endpoint=request.endpoint
            )

    def health_check(self, service: str) -> APIResponse:
        """Check service health"""
        service_endpoint = self.services.get(service)
        if not service_endpoint:
            return APIResponse(
                success=False,
                status_code=404,
                error=f"Service '{service}' not found",
                service=service,
                endpoint="/health"
            )
        
        return self.make_request(service, service_endpoint.health_endpoint)

    def health_check_all(self) -> Dict[str, APIResponse]:
        """Check health of all registered services"""
        results = {}
        for service_name in self.services:
            results[service_name] = self.health_check(service_name)
        return results

    def set_auth_token(self, service: str, token: str, refresh_callback: Optional[Callable] = None):
        """Set authentication token for service"""
        self.auth_tokens[service] = token
        if refresh_callback:
            self.token_refresh_callbacks[service] = refresh_callback
        logger.info(f"Authentication token set for service: {service}")

    def refresh_auth_token(self, service: str) -> bool:
        """Refresh authentication token for service"""
        callback = self.token_refresh_callbacks.get(service)
        if callback:
            try:
                new_token = callback()
                if new_token:
                    self.auth_tokens[service] = new_token
                    return True
            except Exception as e:
                logger.error(f"Failed to refresh token for {service}: {e}")
        return False

    def register_service(self, service: ServiceEndpoint):
        """Register new service endpoint"""
        self.services[service.name] = service
        logger.info(f"Registered service: {service.name} at {service.base_url}:{service.port}")

    def discover_services(self) -> List[str]:
        """Discover available services by health checking"""
        available = []
        for service_name in self.services:
            response = self.health_check(service_name)
            if response.success:
                available.append(service_name)
        return available

    def get_service_info(self, service: str) -> Optional[Dict[str, Any]]:
        """Get service information"""
        endpoint = self.services.get(service)
        if endpoint:
            return {
                'name': endpoint.name,
                'base_url': endpoint.base_url,
                'port': endpoint.port,
                'health_endpoint': endpoint.health_endpoint,
                'api_prefix': endpoint.api_prefix,
                'timeout': endpoint.timeout
            }
        return None

    def get_request_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get request statistics for all services"""
        return self.request_stats.copy()

    def _is_circuit_open(self, service: str) -> bool:
        """Check if circuit breaker is open for service"""
        breaker = self.circuit_breakers.get(service, {})
        if breaker.get('open', False):
            # Check if enough time has passed to try again
            last_failure = breaker.get('last_failure', 0)
            cooldown_period = breaker.get('cooldown', 60)  # 60 seconds default
            if time.time() - last_failure > cooldown_period:
                self._reset_circuit_breaker(service)
                return False
            return True
        return False

    def _record_failure(self, service: str):
        """Record failure for circuit breaker"""
        if service not in self.circuit_breakers:
            self.circuit_breakers[service] = {
                'failures': 0,
                'threshold': 5,
                'cooldown': 60,
                'open': False
            }
        
        breaker = self.circuit_breakers[service]
        breaker['failures'] += 1
        breaker['last_failure'] = time.time()
        
        if breaker['failures'] >= breaker['threshold']:
            breaker['open'] = True
            logger.warning(f"Circuit breaker opened for service: {service}")

    def _reset_circuit_breaker(self, service: str):
        """Reset circuit breaker after successful request"""
        if service in self.circuit_breakers:
            self.circuit_breakers[service] = {
                'failures': 0,
                'threshold': 5,
                'cooldown': 60,
                'open': False
            }

    def _update_request_stats(self, service: str, status_code: int, response_time_ms: int):
        """Update request statistics"""
        if service not in self.request_stats:
            self.request_stats[service] = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'avg_response_time_ms': 0,
                'response_times': [],
                'status_codes': {}
            }
        
        stats = self.request_stats[service]
        stats['total_requests'] += 1
        
        if status_code < 400:
            stats['successful_requests'] += 1
        else:
            stats['failed_requests'] += 1
        
        # Update response time tracking
        stats['response_times'].append(response_time_ms)
        if len(stats['response_times']) > 100:  # Keep only last 100
            stats['response_times'] = stats['response_times'][-100:]
        
        stats['avg_response_time_ms'] = sum(stats['response_times']) / len(stats['response_times'])
        
        # Update status code tracking
        status_str = str(status_code)
        stats['status_codes'][status_str] = stats['status_codes'].get(status_str, 0) + 1

    def _extract_error_message(self, response: requests.Response) -> str:
        """Extract error message from response"""
        try:
            error_data = response.json()
            return error_data.get('error', error_data.get('message', f'HTTP {response.status_code}'))
        except:
            return f'HTTP {response.status_code}: {response.text[:200]}'

    async def close(self):
        """Close async session"""
        if self.async_session:
            await self.async_session.close()
            self.async_session = None

    def __del__(self):
        """Cleanup on deletion"""
        if self.async_session and not self.async_session.closed:
            try:
                loop = asyncio.get_event_loop()
                loop.create_task(self.async_session.close())
            except:
                pass