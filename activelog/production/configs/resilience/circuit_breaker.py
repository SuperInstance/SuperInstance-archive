"""
Circuit Breaker and Retry Logic for ActiveLog Production

Implements resilience patterns including:
- Circuit breaker with multiple states
- Exponential backoff retry
- Bulkhead isolation
- Timeout handling
- Fallback mechanisms
"""

import time
import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, Dict, List, Union, Awaitable
from functools import wraps
import json
import random
import math

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open" # Testing if service recovered

class RetryStrategy(Enum):
    """Retry strategies"""
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff" 
    LINEAR_BACKOFF = "linear_backoff"
    JITTER = "jitter"

@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5          # Failures before opening circuit
    recovery_timeout: int = 60          # Seconds before trying half-open
    success_threshold: int = 3          # Successes needed to close circuit
    timeout: float = 30.0              # Request timeout seconds
    expected_exception: tuple = (Exception,)  # Exceptions that count as failures
    excluded_exceptions: tuple = ()     # Exceptions that don't count as failures

@dataclass 
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0            # Base delay in seconds
    max_delay: float = 60.0            # Maximum delay in seconds
    backoff_multiplier: float = 2.0    # Multiplier for exponential backoff
    jitter: bool = True                # Add randomness to delays
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()

class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open"""
    pass

class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts are exceeded"""
    pass

class CircuitBreakerMetrics:
    """Metrics collection for circuit breaker"""
    
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rejected_requests = 0
        self.state_changes = 0
        self.last_failure_time = None
        self.last_success_time = None
        self.response_times = []
        self.lock = threading.RLock()
    
    def record_success(self, response_time: float = None):
        """Record successful request"""
        with self.lock:
            self.total_requests += 1
            self.successful_requests += 1
            self.last_success_time = time.time()
            if response_time is not None:
                self.response_times.append(response_time)
                # Keep only last 100 response times
                if len(self.response_times) > 100:
                    self.response_times = self.response_times[-100:]
    
    def record_failure(self, response_time: float = None):
        """Record failed request"""
        with self.lock:
            self.total_requests += 1
            self.failed_requests += 1
            self.last_failure_time = time.time()
            if response_time is not None:
                self.response_times.append(response_time)
                if len(self.response_times) > 100:
                    self.response_times = self.response_times[-100:]
    
    def record_rejection(self):
        """Record rejected request (circuit open)"""
        with self.lock:
            self.rejected_requests += 1
    
    def record_state_change(self):
        """Record circuit state change"""
        with self.lock:
            self.state_changes += 1
    
    def get_failure_rate(self) -> float:
        """Get current failure rate"""
        with self.lock:
            if self.total_requests == 0:
                return 0.0
            return self.failed_requests / self.total_requests
    
    def get_average_response_time(self) -> float:
        """Get average response time"""
        with self.lock:
            if not self.response_times:
                return 0.0
            return sum(self.response_times) / len(self.response_times)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        with self.lock:
            return {
                "total_requests": self.total_requests,
                "successful_requests": self.successful_requests,
                "failed_requests": self.failed_requests,
                "rejected_requests": self.rejected_requests,
                "state_changes": self.state_changes,
                "failure_rate": self.get_failure_rate(),
                "average_response_time": self.get_average_response_time(),
                "last_failure_time": self.last_failure_time,
                "last_success_time": self.last_success_time,
            }

class CircuitBreaker:
    """Circuit breaker implementation"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.next_attempt_time = None
        self.lock = threading.RLock()
        self.metrics = CircuitBreakerMetrics()
        
        logger.info(f"Circuit breaker '{name}' initialized: {config}")
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset to half-open"""
        if self.state != CircuitState.OPEN:
            return False
        
        if self.next_attempt_time is None:
            return True
            
        return time.time() >= self.next_attempt_time
    
    def _on_success(self, response_time: float = None):
        """Handle successful request"""
        with self.lock:
            self.failure_count = 0
            self.metrics.record_success(response_time)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._change_state(CircuitState.CLOSED)
                    self.success_count = 0
                    logger.info(f"Circuit breaker '{self.name}' closed after successful recovery")
    
    def _on_failure(self, exception: Exception, response_time: float = None):
        """Handle failed request"""
        with self.lock:
            self.success_count = 0
            self.failure_count += 1
            self.last_failure_time = time.time()
            self.metrics.record_failure(response_time)
            
            if self._should_trip_circuit():
                self._change_state(CircuitState.OPEN)
                self.next_attempt_time = time.time() + self.config.recovery_timeout
                logger.warning(f"Circuit breaker '{self.name}' opened due to {self.failure_count} failures")
    
    def _should_trip_circuit(self) -> bool:
        """Check if circuit should be tripped"""
        return (self.state == CircuitState.CLOSED and 
                self.failure_count >= self.config.failure_threshold)
    
    def _change_state(self, new_state: CircuitState):
        """Change circuit state"""
        if self.state != new_state:
            old_state = self.state
            self.state = new_state
            self.metrics.record_state_change()
            logger.info(f"Circuit breaker '{self.name}' state changed: {old_state.value} -> {new_state.value}")
    
    def _is_exception_ignored(self, exception: Exception) -> bool:
        """Check if exception should be ignored"""
        return isinstance(exception, self.config.excluded_exceptions)
    
    def _is_exception_counted(self, exception: Exception) -> bool:
        """Check if exception should count towards failures"""
        return (isinstance(exception, self.config.expected_exception) and 
                not self._is_exception_ignored(exception))
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        with self.lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if not self._should_attempt_reset():
                    self.metrics.record_rejection()
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
                else:
                    # Try half-open
                    self._change_state(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker '{self.name}' attempting recovery (HALF_OPEN)")
        
        start_time = time.time()
        try:
            # Execute function with timeout
            result = self._execute_with_timeout(func, *args, **kwargs)
            response_time = time.time() - start_time
            self._on_success(response_time)
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            if self._is_exception_counted(e):
                self._on_failure(e, response_time)
            else:
                # Exception doesn't count towards failure, but still record success
                self._on_success(response_time)
                
            raise
    
    def _execute_with_timeout(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with timeout"""
        if asyncio.iscoroutinefunction(func):
            return asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
        
        # For sync functions, we can't easily implement timeout without threading
        # In production, consider using a thread pool or async executor
        return func(*args, **kwargs)
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        with self.lock:
            # Check if circuit is open
            if self.state == CircuitState.OPEN:
                if not self._should_attempt_reset():
                    self.metrics.record_rejection()
                    raise CircuitBreakerError(f"Circuit breaker '{self.name}' is OPEN")
                else:
                    # Try half-open
                    self._change_state(CircuitState.HALF_OPEN)
                    logger.info(f"Circuit breaker '{self.name}' attempting recovery (HALF_OPEN)")
        
        start_time = time.time()
        try:
            # Execute async function with timeout
            result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.config.timeout)
            response_time = time.time() - start_time
            self._on_success(response_time)
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            
            if self._is_exception_counted(e):
                self._on_failure(e, response_time)
            else:
                self._on_success(response_time)
                
            raise
    
    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        return self.state
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        metrics = self.metrics.to_dict()
        metrics.update({
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "next_attempt_time": self.next_attempt_time,
        })
        return metrics
    
    def reset(self):
        """Manually reset circuit breaker"""
        with self.lock:
            self._change_state(CircuitState.CLOSED)
            self.failure_count = 0
            self.success_count = 0
            self.next_attempt_time = None
            logger.info(f"Circuit breaker '{self.name}' manually reset")

class RetryPolicy:
    """Retry policy implementation"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt"""
        if self.config.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.config.base_delay
            
        elif self.config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = min(
                self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1)),
                self.config.max_delay
            )
            
        elif self.config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = min(
                self.config.base_delay * attempt,
                self.config.max_delay
            )
            
        elif self.config.strategy == RetryStrategy.JITTER:
            base_delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
            jitter = random.uniform(0, 1) * base_delay * 0.1  # 10% jitter
            delay = min(base_delay + jitter, self.config.max_delay)
            
        else:
            delay = self.config.base_delay
        
        # Add jitter if enabled
        if self.config.jitter and self.config.strategy != RetryStrategy.JITTER:
            jitter = random.uniform(-0.1, 0.1) * delay
            delay = max(0, delay + jitter)
        
        return delay
    
    def _is_retryable_exception(self, exception: Exception) -> bool:
        """Check if exception is retryable"""
        if isinstance(exception, self.config.non_retryable_exceptions):
            return False
        return isinstance(exception, self.config.retryable_exceptions)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Function succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self._is_retryable_exception(e):
                    logger.info(f"Non-retryable exception: {type(e).__name__}: {e}")
                    raise
                
                if attempt == self.config.max_attempts:
                    logger.error(f"Max retry attempts ({self.config.max_attempts}) exceeded")
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt} failed: {type(e).__name__}: {e}. "
                             f"Retrying in {delay:.2f}s")
                
                time.sleep(delay)
        
        # All retries failed
        raise MaxRetriesExceededError(
            f"Failed after {self.config.max_attempts} attempts. Last error: {last_exception}"
        ) from last_exception
    
    async def aexecute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                result = await func(*args, **kwargs)
                if attempt > 1:
                    logger.info(f"Async function succeeded on attempt {attempt}")
                return result
                
            except Exception as e:
                last_exception = e
                
                if not self._is_retryable_exception(e):
                    logger.info(f"Non-retryable exception: {type(e).__name__}: {e}")
                    raise
                
                if attempt == self.config.max_attempts:
                    logger.error(f"Max retry attempts ({self.config.max_attempts}) exceeded")
                    break
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt} failed: {type(e).__name__}: {e}. "
                             f"Retrying in {delay:.2f}s")
                
                await asyncio.sleep(delay)
        
        # All retries failed
        raise MaxRetriesExceededError(
            f"Failed after {self.config.max_attempts} attempts. Last error: {last_exception}"
        ) from last_exception

class ResilientService:
    """Service wrapper combining circuit breaker and retry logic"""
    
    def __init__(self, name: str, circuit_config: CircuitBreakerConfig = None, 
                 retry_config: RetryConfig = None, fallback: Callable = None):
        self.name = name
        self.circuit_breaker = CircuitBreaker(name, circuit_config or CircuitBreakerConfig())
        self.retry_policy = RetryPolicy(retry_config or RetryConfig())
        self.fallback = fallback
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with resilience patterns"""
        try:
            return self.retry_policy.execute(
                lambda: self.circuit_breaker.call(func, *args, **kwargs)
            )
        except (CircuitBreakerError, MaxRetriesExceededError) as e:
            logger.error(f"Resilient service '{self.name}' failed: {e}")
            
            if self.fallback:
                logger.info(f"Executing fallback for service '{self.name}'")
                try:
                    return self.fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback failed for service '{self.name}': {fallback_error}")
                    raise e from fallback_error
            
            raise
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with resilience patterns"""
        try:
            return await self.retry_policy.aexecute(
                lambda: self.circuit_breaker.acall(func, *args, **kwargs)
            )
        except (CircuitBreakerError, MaxRetriesExceededError) as e:
            logger.error(f"Resilient async service '{self.name}' failed: {e}")
            
            if self.fallback:
                logger.info(f"Executing fallback for service '{self.name}'")
                try:
                    if asyncio.iscoroutinefunction(self.fallback):
                        return await self.fallback(*args, **kwargs)
                    else:
                        return self.fallback(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"Fallback failed for service '{self.name}': {fallback_error}")
                    raise e from fallback_error
            
            raise
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        return {
            "service_name": self.name,
            "circuit_breaker": self.circuit_breaker.get_metrics(),
            "retry_config": {
                "max_attempts": self.retry_policy.config.max_attempts,
                "strategy": self.retry_policy.config.strategy.value,
                "base_delay": self.retry_policy.config.base_delay,
                "max_delay": self.retry_policy.config.max_delay,
            }
        }

# Global registry for resilient services
_service_registry: Dict[str, ResilientService] = {}

def register_resilient_service(name: str, circuit_config: CircuitBreakerConfig = None,
                             retry_config: RetryConfig = None, fallback: Callable = None):
    """Register a resilient service"""
    global _service_registry
    _service_registry[name] = ResilientService(name, circuit_config, retry_config, fallback)
    return _service_registry[name]

def get_resilient_service(name: str) -> Optional[ResilientService]:
    """Get registered resilient service"""
    return _service_registry.get(name)

def get_all_service_metrics() -> Dict[str, Any]:
    """Get metrics for all registered services"""
    return {name: service.get_metrics() for name, service in _service_registry.items()}

# Decorators for easy integration
def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator for circuit breaker protection"""
    def decorator(func: Callable):
        cb = CircuitBreaker(f"{func.__module__}.{func.__name__}" if name is None else name,
                           config or CircuitBreakerConfig())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return cb.call(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await cb.acall(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator

def retry(config: RetryConfig = None):
    """Decorator for retry logic"""
    def decorator(func: Callable):
        retry_policy = RetryPolicy(config or RetryConfig())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return retry_policy.execute(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_policy.aexecute(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator

def resilient(name: str, circuit_config: CircuitBreakerConfig = None,
             retry_config: RetryConfig = None, fallback: Callable = None):
    """Decorator combining circuit breaker and retry logic"""
    def decorator(func: Callable):
        service = ResilientService(
            name or f"{func.__module__}.{func.__name__}",
            circuit_config, retry_config, fallback
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return service.call(func, *args, **kwargs)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await service.acall(func, *args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    return decorator

# Bulkhead pattern implementation
class Bulkhead:
    """Bulkhead isolation pattern"""
    
    def __init__(self, name: str, max_concurrent_requests: int = 10):
        self.name = name
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.sync_semaphore = threading.Semaphore(max_concurrent_requests)
        self.active_requests = 0
        self.rejected_requests = 0
        self.completed_requests = 0
        self.lock = threading.RLock()
    
    async def aexecute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with bulkhead isolation"""
        try:
            async with self.semaphore:
                with self.lock:
                    self.active_requests += 1
                
                try:
                    result = await func(*args, **kwargs)
                    with self.lock:
                        self.completed_requests += 1
                    return result
                finally:
                    with self.lock:
                        self.active_requests -= 1
                        
        except asyncio.TimeoutError:
            with self.lock:
                self.rejected_requests += 1
            raise
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with bulkhead isolation"""
        if not self.sync_semaphore.acquire(blocking=False):
            with self.lock:
                self.rejected_requests += 1
            raise Exception(f"Bulkhead '{self.name}' capacity exceeded")
        
        try:
            with self.lock:
                self.active_requests += 1
            
            result = func(*args, **kwargs)
            with self.lock:
                self.completed_requests += 1
            return result
            
        finally:
            with self.lock:
                self.active_requests -= 1
            self.sync_semaphore.release()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get bulkhead metrics"""
        with self.lock:
            return {
                "name": self.name,
                "active_requests": self.active_requests,
                "rejected_requests": self.rejected_requests,
                "completed_requests": self.completed_requests,
                "available_capacity": self.semaphore._value if hasattr(self.semaphore, '_value') else 0
            }

# Example configurations for different services
DATABASE_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30,
    success_threshold=2,
    timeout=10.0,
    expected_exception=(Exception,),
    excluded_exceptions=(KeyboardInterrupt,)
)

API_CIRCUIT_CONFIG = CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout=60,
    success_threshold=3,
    timeout=30.0
)

DATABASE_RETRY_CONFIG = RetryConfig(
    max_attempts=3,
    strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
    base_delay=0.5,
    max_delay=10.0,
    backoff_multiplier=2.0
)

API_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    strategy=RetryStrategy.FIXED_DELAY,
    base_delay=1.0,
    max_delay=5.0
)