import asyncio
import time
import threading
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque, defaultdict
import statistics
import random


class CircuitState(Enum):
    CLOSED = "closed"          # Normal operation
    OPEN = "open"             # Circuit is open, failing fast
    HALF_OPEN = "half_open"   # Testing if service has recovered


class FailureType(Enum):
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    SERVICE_ERROR = "service_error"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 10          # Number of failures to trigger open state
    recovery_timeout: int = 60           # Seconds before trying half-open
    request_timeout: int = 30            # Request timeout in seconds
    success_threshold: int = 5           # Successful requests needed in half-open to close
    rolling_window_size: int = 100       # Size of rolling window for failure tracking
    minimum_requests: int = 20           # Minimum requests before circuit can open
    failure_rate_threshold: float = 0.5 # Failure rate threshold (0.0-1.0)
    slow_request_threshold: float = 5.0  # Slow request threshold in seconds
    slow_request_rate_threshold: float = 0.5  # Slow request rate threshold
    max_concurrent_requests: int = 100   # Max concurrent requests in half-open


@dataclass
class RequestResult:
    success: bool
    response_time: float
    failure_type: Optional[FailureType] = None
    error_message: str = ""
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class CircuitBreakerMetrics:
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rejected_requests: int = 0
    total_response_time: float = 0.0
    slow_requests: int = 0
    state_transitions: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    failure_types: Dict[str, int] = None
    
    def __post_init__(self):
        if self.failure_types is None:
            self.failure_types = defaultdict(int)
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    @property
    def average_response_time(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests
    
    @property
    def slow_request_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.slow_requests / self.total_requests


class CircuitBreakerException(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """Circuit breaker implementation with advanced failure detection"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        
        # Rolling window for tracking requests
        self.request_history = deque(maxlen=self.config.rolling_window_size)
        self.recent_requests = deque(maxlen=self.config.minimum_requests)
        
        # State management
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
        self.next_attempt_time = datetime.now()
        
        # Concurrency control
        self.concurrent_requests = 0
        self.concurrent_lock = threading.RLock()
        
        # Callbacks
        self.state_change_callbacks = []
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
    def add_state_change_callback(self, callback: Callable[[str, CircuitState, CircuitState], None]):
        """Add callback for state changes"""
        self.state_change_callbacks.append(callback)
    
    def _notify_state_change(self, old_state: CircuitState, new_state: CircuitState):
        """Notify state change callbacks"""
        for callback in self.state_change_callbacks:
            try:
                callback(self.name, old_state, new_state)
            except Exception as e:
                self.logger.error(f"Error in state change callback: {e}")
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if not self._can_execute():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerException(f"Circuit breaker {self.name} is OPEN")
        
        with self.concurrent_lock:
            self.concurrent_requests += 1
        
        try:
            start_time = time.time()
            result = func(*args, **kwargs)
            response_time = time.time() - start_time
            
            # Record successful request
            request_result = RequestResult(
                success=True,
                response_time=response_time
            )
            self._record_request(request_result)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Classify the failure
            failure_type = self._classify_failure(e)
            
            # Record failed request
            request_result = RequestResult(
                success=False,
                response_time=response_time,
                failure_type=failure_type,
                error_message=str(e)
            )
            self._record_request(request_result)
            
            raise
            
        finally:
            with self.concurrent_lock:
                self.concurrent_requests -= 1
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if not self._can_execute():
            self.metrics.rejected_requests += 1
            raise CircuitBreakerException(f"Circuit breaker {self.name} is OPEN")
        
        with self.concurrent_lock:
            self.concurrent_requests += 1
        
        try:
            start_time = time.time()
            
            # Add timeout to the async call
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.config.request_timeout
            )
            
            response_time = time.time() - start_time
            
            # Record successful request
            request_result = RequestResult(
                success=True,
                response_time=response_time
            )
            self._record_request(request_result)
            
            return result
            
        except asyncio.TimeoutError as e:
            response_time = time.time() - start_time
            
            # Record timeout failure
            request_result = RequestResult(
                success=False,
                response_time=response_time,
                failure_type=FailureType.TIMEOUT,
                error_message="Request timeout"
            )
            self._record_request(request_result)
            
            raise
            
        except Exception as e:
            response_time = time.time() - start_time
            
            # Classify the failure
            failure_type = self._classify_failure(e)
            
            # Record failed request
            request_result = RequestResult(
                success=False,
                response_time=response_time,
                failure_type=failure_type,
                error_message=str(e)
            )
            self._record_request(request_result)
            
            raise
            
        finally:
            with self.concurrent_lock:
                self.concurrent_requests -= 1
    
    def _can_execute(self) -> bool:
        """Check if request can be executed based on circuit state"""
        current_time = datetime.now()
        
        if self.state == CircuitState.CLOSED:
            return True
            
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if current_time >= self.next_attempt_time:
                self._transition_to_half_open()
                return True
            return False
            
        elif self.state == CircuitState.HALF_OPEN:
            # Limit concurrent requests in half-open state
            with self.concurrent_lock:
                if self.concurrent_requests >= self.config.max_concurrent_requests:
                    return False
            return True
        
        return False
    
    def _record_request(self, result: RequestResult):
        """Record request result and update circuit state"""
        # Update metrics
        self.metrics.total_requests += 1
        
        if result.success:
            self.metrics.successful_requests += 1
            self.metrics.total_response_time += result.response_time
            self.metrics.last_success_time = result.timestamp
            
            # Check if request was slow
            if result.response_time >= self.config.slow_request_threshold:
                self.metrics.slow_requests += 1
            
            self._record_success()
        else:
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = result.timestamp
            self.metrics.failure_types[result.failure_type.value] += 1
            self._record_failure()
        
        # Add to rolling window
        self.request_history.append(result)
        self.recent_requests.append(result)
        
        # Update circuit state
        self._update_circuit_state()
    
    def _record_success(self):
        """Record successful request"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.failure_count = 0  # Reset failure count on success
            
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def _record_failure(self):
        """Record failed request"""
        if self.state == CircuitState.CLOSED:
            self.failure_count += 1
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately goes to open
            self._transition_to_open()
    
    def _update_circuit_state(self):
        """Update circuit state based on recent metrics"""
        if self.state != CircuitState.CLOSED:
            return
        
        # Need minimum requests before considering opening
        if len(self.recent_requests) < self.config.minimum_requests:
            return
        
        # Calculate failure metrics from recent requests
        recent_failures = sum(1 for r in self.recent_requests if not r.success)
        recent_total = len(self.recent_requests)
        
        failure_rate = recent_failures / recent_total if recent_total > 0 else 0
        
        # Calculate slow request rate
        slow_requests = sum(1 for r in self.recent_requests 
                          if r.success and r.response_time >= self.config.slow_request_threshold)
        slow_request_rate = slow_requests / recent_total if recent_total > 0 else 0
        
        # Check if circuit should open
        should_open = False
        
        # Check failure count threshold
        if self.failure_count >= self.config.failure_threshold:
            should_open = True
            self.logger.warning(f"Opening circuit {self.name}: failure count {self.failure_count}")
        
        # Check failure rate threshold
        elif failure_rate >= self.config.failure_rate_threshold:
            should_open = True
            self.logger.warning(f"Opening circuit {self.name}: failure rate {failure_rate:.2%}")
        
        # Check slow request rate
        elif slow_request_rate >= self.config.slow_request_rate_threshold:
            should_open = True
            self.logger.warning(f"Opening circuit {self.name}: slow request rate {slow_request_rate:.2%}")
        
        if should_open:
            self._transition_to_open()
    
    def _transition_to_closed(self):
        """Transition circuit to CLOSED state"""
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = datetime.now()
        self.metrics.state_transitions += 1
        
        self.logger.info(f"Circuit {self.name} transitioned to CLOSED")
        self._notify_state_change(old_state, self.state)
    
    def _transition_to_open(self):
        """Transition circuit to OPEN state"""
        old_state = self.state
        self.state = CircuitState.OPEN
        self.last_state_change = datetime.now()
        self.next_attempt_time = datetime.now() + timedelta(seconds=self.config.recovery_timeout)
        self.metrics.state_transitions += 1
        
        self.logger.warning(f"Circuit {self.name} transitioned to OPEN")
        self._notify_state_change(old_state, self.state)
    
    def _transition_to_half_open(self):
        """Transition circuit to HALF_OPEN state"""
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0
        self.failure_count = 0
        self.last_state_change = datetime.now()
        self.metrics.state_transitions += 1
        
        self.logger.info(f"Circuit {self.name} transitioned to HALF_OPEN")
        self._notify_state_change(old_state, self.state)
    
    def _classify_failure(self, exception: Exception) -> FailureType:
        """Classify the type of failure"""
        exception_type = type(exception).__name__
        exception_msg = str(exception).lower()
        
        if isinstance(exception, asyncio.TimeoutError) or 'timeout' in exception_msg:
            return FailureType.TIMEOUT
        elif 'connection' in exception_msg:
            return FailureType.CONNECTION_ERROR
        elif hasattr(exception, 'status_code') or 'http' in exception_msg:
            return FailureType.HTTP_ERROR
        elif 'rate limit' in exception_msg or 'too many requests' in exception_msg:
            return FailureType.RATE_LIMIT
        elif 'service' in exception_msg or 'server' in exception_msg:
            return FailureType.SERVICE_ERROR
        else:
            return FailureType.UNKNOWN
    
    def force_open(self):
        """Manually force circuit to OPEN state"""
        self._transition_to_open()
    
    def force_close(self):
        """Manually force circuit to CLOSED state"""
        self._transition_to_closed()
    
    def force_half_open(self):
        """Manually force circuit to HALF_OPEN state"""
        self._transition_to_half_open()
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = CircuitBreakerMetrics()
        self.request_history.clear()
        self.recent_requests.clear()
        self.failure_count = 0
        self.success_count = 0
    
    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "concurrent_requests": self.concurrent_requests,
            "last_state_change": self.last_state_change.isoformat(),
            "next_attempt_time": self.next_attempt_time.isoformat() if self.state == CircuitState.OPEN else None,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "rejected_requests": self.metrics.rejected_requests,
                "success_rate": self.metrics.success_rate,
                "failure_rate": self.metrics.failure_rate,
                "average_response_time": self.metrics.average_response_time,
                "slow_requests": self.metrics.slow_requests,
                "slow_request_rate": self.metrics.slow_request_rate,
                "state_transitions": self.metrics.state_transitions,
                "last_failure_time": self.metrics.last_failure_time.isoformat() if self.metrics.last_failure_time else None,
                "last_success_time": self.metrics.last_success_time.isoformat() if self.metrics.last_success_time else None,
                "failure_types": dict(self.metrics.failure_types)
            },
            "config": asdict(self.config)
        }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
        self.logger = logging.getLogger(__name__)
    
    def get_or_create(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.circuit_breakers:
            circuit_config = config or self.default_config
            self.circuit_breakers[name] = CircuitBreaker(name, circuit_config)
            self.logger.info(f"Created circuit breaker: {name}")
        
        return self.circuit_breakers[name]
    
    def remove(self, name: str) -> bool:
        """Remove a circuit breaker"""
        if name in self.circuit_breakers:
            del self.circuit_breakers[name]
            self.logger.info(f"Removed circuit breaker: {name}")
            return True
        return False
    
    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all circuit breakers"""
        return {name: cb.get_status() for name, cb in self.circuit_breakers.items()}
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset_metrics()
        self.logger.info("Reset all circuit breakers")
    
    def force_open_all(self):
        """Force all circuit breakers to OPEN state"""
        for cb in self.circuit_breakers.values():
            cb.force_open()
        self.logger.warning("Forced all circuit breakers to OPEN")
    
    def force_close_all(self):
        """Force all circuit breakers to CLOSED state"""
        for cb in self.circuit_breakers.values():
            cb.force_close()
        self.logger.info("Forced all circuit breakers to CLOSED")


class CircuitBreakerMiddleware:
    """Middleware for automatic circuit breaker integration"""
    
    def __init__(self, registry: CircuitBreakerRegistry):
        self.registry = registry
        self.logger = logging.getLogger(__name__)
    
    def wrap_function(self, func: Callable, service_name: str, 
                     config: CircuitBreakerConfig = None) -> Callable:
        """Wrap a function with circuit breaker protection"""
        circuit_breaker = self.registry.get_or_create(service_name, config)
        
        def wrapped_func(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)
        
        return wrapped_func
    
    def wrap_async_function(self, func: Callable, service_name: str,
                          config: CircuitBreakerConfig = None) -> Callable:
        """Wrap an async function with circuit breaker protection"""
        circuit_breaker = self.registry.get_or_create(service_name, config)
        
        async def wrapped_func(*args, **kwargs):
            return await circuit_breaker.call_async(func, *args, **kwargs)
        
        return wrapped_func


# Decorators for easy integration
def circuit_breaker(service_name: str, config: CircuitBreakerConfig = None, 
                   registry: CircuitBreakerRegistry = None):
    """Decorator for circuit breaker protection"""
    if registry is None:
        registry = CircuitBreakerRegistry()
    
    def decorator(func: Callable) -> Callable:
        circuit_breaker_instance = registry.get_or_create(service_name, config)
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await circuit_breaker_instance.call_async(func, *args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return circuit_breaker_instance.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


# Usage examples
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Create circuit breaker registry
    registry = CircuitBreakerRegistry()
    
    # Configure circuit breaker for external API
    api_config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30,
        request_timeout=10,
        success_threshold=3,
        failure_rate_threshold=0.3
    )
    
    # Example: Protect external API call
    @circuit_breaker("external-api", config=api_config, registry=registry)
    def call_external_api(data):
        # Simulate API call
        if random.random() < 0.7:  # 70% success rate
            time.sleep(0.1)  # Simulate network delay
            return {"status": "success", "data": data}
        else:
            raise Exception("API Error: Service unavailable")
    
    # Example: Protect async database call
    @circuit_breaker("database", registry=registry)
    async def query_database(query):
        # Simulate database query
        await asyncio.sleep(0.05)  # Simulate query time
        if random.random() < 0.9:  # 90% success rate
            return f"Result for: {query}"
        else:
            raise Exception("Database Error: Connection failed")
    
    # Test circuit breaker
    async def test_circuit_breakers():
        # Test sync function
        for i in range(20):
            try:
                result = call_external_api(f"request_{i}")
                print(f"API call {i}: {result['status']}")
            except CircuitBreakerException as e:
                print(f"API call {i}: Circuit breaker OPEN")
            except Exception as e:
                print(f"API call {i}: Failed - {e}")
            
            time.sleep(0.1)
        
        # Test async function
        for i in range(10):
            try:
                result = await query_database(f"SELECT * FROM table_{i}")
                print(f"DB query {i}: Success")
            except CircuitBreakerException as e:
                print(f"DB query {i}: Circuit breaker OPEN")
            except Exception as e:
                print(f"DB query {i}: Failed - {e}")
            
            await asyncio.sleep(0.1)
        
        # Show circuit breaker status
        status = registry.get_all_status()
        for name, cb_status in status.items():
            print(f"\nCircuit Breaker: {name}")
            print(f"  State: {cb_status['state']}")
            print(f"  Success Rate: {cb_status['metrics']['success_rate']:.2%}")
            print(f"  Total Requests: {cb_status['metrics']['total_requests']}")
            print(f"  Rejected Requests: {cb_status['metrics']['rejected_requests']}")
    
    # Run test
    asyncio.run(test_circuit_breakers())