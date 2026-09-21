import asyncio
import random
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Union, Type
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict
import functools
import inspect


class RetryStrategy(Enum):
    FIXED_DELAY = "fixed_delay"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIBONACCI_BACKOFF = "fibonacci_backoff"
    CUSTOM = "custom"


class RetryCondition(Enum):
    ALL_EXCEPTIONS = "all_exceptions"
    SPECIFIC_EXCEPTIONS = "specific_exceptions"
    STATUS_CODES = "status_codes"
    CUSTOM_PREDICATE = "custom_predicate"


@dataclass
class RetryConfig:
    max_attempts: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    multiplier: float = 2.0  # for exponential backoff
    jitter: bool = True  # add randomization
    condition: RetryCondition = RetryCondition.ALL_EXCEPTIONS
    retryable_exceptions: List[Type[Exception]] = None
    retryable_status_codes: List[int] = None
    custom_predicate: Optional[Callable[[Exception], bool]] = None
    timeout: Optional[float] = None  # total timeout for all attempts
    
    def __post_init__(self):
        if self.retryable_exceptions is None:
            self.retryable_exceptions = [Exception]
        if self.retryable_status_codes is None:
            self.retryable_status_codes = [500, 502, 503, 504, 408, 429]


@dataclass
class RetryAttempt:
    attempt_number: int
    delay: float
    exception: Optional[Exception]
    start_time: datetime
    end_time: Optional[datetime]
    success: bool
    
    @property
    def duration(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


@dataclass
class RetryResult:
    success: bool
    attempts: List[RetryAttempt]
    final_result: Any = None
    final_exception: Optional[Exception] = None
    total_duration: float = 0.0
    
    @property
    def attempt_count(self) -> int:
        return len(self.attempts)


class RetryDelayCalculator:
    """Calculate retry delays based on different strategies"""
    
    @staticmethod
    def calculate_delay(attempt: int, config: RetryConfig) -> float:
        """Calculate delay for the given attempt"""
        if config.strategy == RetryStrategy.FIXED_DELAY:
            delay = config.base_delay
            
        elif config.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = config.base_delay * (config.multiplier ** (attempt - 1))
            
        elif config.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = config.base_delay * attempt
            
        elif config.strategy == RetryStrategy.FIBONACCI_BACKOFF:
            delay = config.base_delay * RetryDelayCalculator._fibonacci(attempt)
            
        else:
            delay = config.base_delay
        
        # Apply max delay limit
        delay = min(delay, config.max_delay)
        
        # Add jitter if enabled
        if config.jitter:
            # Add up to 10% jitter
            jitter_amount = delay * 0.1 * random.random()
            delay += jitter_amount
        
        return delay
    
    @staticmethod
    def _fibonacci(n: int) -> int:
        """Calculate fibonacci number for backoff"""
        if n <= 1:
            return n
        elif n == 2:
            return 1
        else:
            a, b = 1, 1
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b


class RetryPredicate:
    """Determine if an exception should trigger a retry"""
    
    @staticmethod
    def should_retry(exception: Exception, config: RetryConfig) -> bool:
        """Check if exception should trigger a retry"""
        if config.condition == RetryCondition.ALL_EXCEPTIONS:
            return True
            
        elif config.condition == RetryCondition.SPECIFIC_EXCEPTIONS:
            return any(isinstance(exception, exc_type) for exc_type in config.retryable_exceptions)
            
        elif config.condition == RetryCondition.STATUS_CODES:
            # Check if exception has a status_code attribute
            if hasattr(exception, 'status_code'):
                return exception.status_code in config.retryable_status_codes
            elif hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
                return exception.response.status_code in config.retryable_status_codes
            else:
                return False
                
        elif config.condition == RetryCondition.CUSTOM_PREDICATE:
            if config.custom_predicate:
                return config.custom_predicate(exception)
            else:
                return False
        
        return False


class RetryExecutor:
    """Core retry execution logic"""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def execute(self, func: Callable, *args, **kwargs) -> RetryResult:
        """Execute function with retry logic"""
        attempts = []
        start_time = datetime.now()
        timeout_time = None
        
        if self.config.timeout:
            timeout_time = start_time + timedelta(seconds=self.config.timeout)
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = datetime.now()
            
            # Check timeout
            if timeout_time and attempt_start >= timeout_time:
                self.logger.warning(f"Retry timeout reached after {attempt_num - 1} attempts")
                break
            
            try:
                result = func(*args, **kwargs)
                
                # Success
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    exception=None,
                    start_time=attempt_start,
                    end_time=datetime.now(),
                    success=True
                )
                attempts.append(attempt)
                
                total_duration = (datetime.now() - start_time).total_seconds()
                
                return RetryResult(
                    success=True,
                    attempts=attempts,
                    final_result=result,
                    total_duration=total_duration
                )
                
            except Exception as e:
                attempt_end = datetime.now()
                
                # Check if we should retry
                should_retry = RetryPredicate.should_retry(e, self.config)
                is_last_attempt = (attempt_num >= self.config.max_attempts)
                
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    exception=e,
                    start_time=attempt_start,
                    end_time=attempt_end,
                    success=False
                )
                attempts.append(attempt)
                
                if not should_retry or is_last_attempt:
                    # No more retries
                    self.logger.error(f"Final failure after {attempt_num} attempts: {e}")
                    total_duration = (datetime.now() - start_time).total_seconds()
                    
                    return RetryResult(
                        success=False,
                        attempts=attempts,
                        final_exception=e,
                        total_duration=total_duration
                    )
                
                # Calculate delay for next attempt
                delay = RetryDelayCalculator.calculate_delay(attempt_num, self.config)
                attempt.delay = delay
                
                # Check if delay would exceed timeout
                if timeout_time:
                    delay_end = datetime.now() + timedelta(seconds=delay)
                    if delay_end >= timeout_time:
                        self.logger.warning(f"Delay would exceed timeout, stopping retries")
                        break
                
                self.logger.info(f"Attempt {attempt_num} failed: {e}. Retrying in {delay:.2f}s")
                time.sleep(delay)
        
        # If we get here, we've exhausted retries or hit timeout
        total_duration = (datetime.now() - start_time).total_seconds()
        final_exception = attempts[-1].exception if attempts else Exception("No attempts made")
        
        return RetryResult(
            success=False,
            attempts=attempts,
            final_exception=final_exception,
            total_duration=total_duration
        )
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> RetryResult:
        """Execute async function with retry logic"""
        attempts = []
        start_time = datetime.now()
        timeout_time = None
        
        if self.config.timeout:
            timeout_time = start_time + timedelta(seconds=self.config.timeout)
        
        for attempt_num in range(1, self.config.max_attempts + 1):
            attempt_start = datetime.now()
            
            # Check timeout
            if timeout_time and attempt_start >= timeout_time:
                self.logger.warning(f"Retry timeout reached after {attempt_num - 1} attempts")
                break
            
            try:
                result = await func(*args, **kwargs)
                
                # Success
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    exception=None,
                    start_time=attempt_start,
                    end_time=datetime.now(),
                    success=True
                )
                attempts.append(attempt)
                
                total_duration = (datetime.now() - start_time).total_seconds()
                
                return RetryResult(
                    success=True,
                    attempts=attempts,
                    final_result=result,
                    total_duration=total_duration
                )
                
            except Exception as e:
                attempt_end = datetime.now()
                
                # Check if we should retry
                should_retry = RetryPredicate.should_retry(e, self.config)
                is_last_attempt = (attempt_num >= self.config.max_attempts)
                
                attempt = RetryAttempt(
                    attempt_number=attempt_num,
                    delay=0.0,
                    exception=e,
                    start_time=attempt_start,
                    end_time=attempt_end,
                    success=False
                )
                attempts.append(attempt)
                
                if not should_retry or is_last_attempt:
                    # No more retries
                    self.logger.error(f"Final failure after {attempt_num} attempts: {e}")
                    total_duration = (datetime.now() - start_time).total_seconds()
                    
                    return RetryResult(
                        success=False,
                        attempts=attempts,
                        final_exception=e,
                        total_duration=total_duration
                    )
                
                # Calculate delay for next attempt
                delay = RetryDelayCalculator.calculate_delay(attempt_num, self.config)
                attempt.delay = delay
                
                # Check if delay would exceed timeout
                if timeout_time:
                    delay_end = datetime.now() + timedelta(seconds=delay)
                    if delay_end >= timeout_time:
                        self.logger.warning(f"Delay would exceed timeout, stopping retries")
                        break
                
                self.logger.info(f"Attempt {attempt_num} failed: {e}. Retrying in {delay:.2f}s")
                await asyncio.sleep(delay)
        
        # If we get here, we've exhausted retries or hit timeout
        total_duration = (datetime.now() - start_time).total_seconds()
        final_exception = attempts[-1].exception if attempts else Exception("No attempts made")
        
        return RetryResult(
            success=False,
            attempts=attempts,
            final_exception=final_exception,
            total_duration=total_duration
        )


class RetryManager:
    """Manage retry configurations and execution"""
    
    def __init__(self):
        self.configs: Dict[str, RetryConfig] = {}
        self.default_config = RetryConfig()
        self.metrics = RetryMetrics()
        self.logger = logging.getLogger(__name__)
    
    def register_config(self, name: str, config: RetryConfig):
        """Register a retry configuration"""
        self.configs[name] = config
        self.logger.info(f"Registered retry config: {name}")
    
    def get_config(self, name: str) -> RetryConfig:
        """Get retry configuration by name"""
        return self.configs.get(name, self.default_config)
    
    def retry(self, func: Callable, config_name: str = None, 
             config: RetryConfig = None, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        retry_config = config or self.get_config(config_name) if config_name else self.default_config
        
        executor = RetryExecutor(retry_config)
        result = executor.execute(func, *args, **kwargs)
        
        # Record metrics
        self.metrics.record_retry_result(config_name or 'default', result)
        
        if result.success:
            return result.final_result
        else:
            raise result.final_exception
    
    async def retry_async(self, func: Callable, config_name: str = None,
                         config: RetryConfig = None, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        retry_config = config or self.get_config(config_name) if config_name else self.default_config
        
        executor = RetryExecutor(retry_config)
        result = await executor.execute_async(func, *args, **kwargs)
        
        # Record metrics
        self.metrics.record_retry_result(config_name or 'default', result)
        
        if result.success:
            return result.final_result
        else:
            raise result.final_exception


class RetryMetrics:
    """Track retry statistics and metrics"""
    
    def __init__(self):
        self.stats = defaultdict(lambda: {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_attempts': 0,
            'avg_attempts': 0.0,
            'total_duration': 0.0,
            'avg_duration': 0.0
        })
        self.lock = threading.RLock()
    
    def record_retry_result(self, config_name: str, result: RetryResult):
        """Record retry result for metrics"""
        with self.lock:
            stats = self.stats[config_name]
            
            stats['total_calls'] += 1
            stats['total_attempts'] += result.attempt_count
            stats['total_duration'] += result.total_duration
            
            if result.success:
                stats['successful_calls'] += 1
            else:
                stats['failed_calls'] += 1
            
            # Update averages
            stats['avg_attempts'] = stats['total_attempts'] / stats['total_calls']
            stats['avg_duration'] = stats['total_duration'] / stats['total_calls']
    
    def get_stats(self, config_name: str = None) -> Dict[str, Any]:
        """Get retry statistics"""
        with self.lock:
            if config_name:
                return dict(self.stats.get(config_name, {}))
            else:
                return {name: dict(stats) for name, stats in self.stats.items()}
    
    def reset_stats(self, config_name: str = None):
        """Reset statistics"""
        with self.lock:
            if config_name:
                if config_name in self.stats:
                    del self.stats[config_name]
            else:
                self.stats.clear()


# Global retry manager instance
_retry_manager = RetryManager()


# Decorator functions
def retry(max_attempts: int = 3, 
          strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF,
          base_delay: float = 1.0,
          max_delay: float = 60.0,
          multiplier: float = 2.0,
          jitter: bool = True,
          retryable_exceptions: List[Type[Exception]] = None,
          retryable_status_codes: List[int] = None,
          timeout: Optional[float] = None,
          config_name: Optional[str] = None):
    """Retry decorator for functions"""
    
    def decorator(func: Callable) -> Callable:
        # Create config
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            strategy=strategy,
            base_delay=base_delay,
            max_delay=max_delay,
            multiplier=multiplier,
            jitter=jitter,
            retryable_exceptions=retryable_exceptions,
            retryable_status_codes=retryable_status_codes,
            timeout=timeout
        )
        
        # Register config if name provided
        if config_name:
            _retry_manager.register_config(config_name, retry_config)
        
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await _retry_manager.retry_async(func, config_name, retry_config, *args, **kwargs)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return _retry_manager.retry(func, config_name, retry_config, *args, **kwargs)
            return sync_wrapper
    
    return decorator


def retry_on_exception(exceptions: List[Type[Exception]], 
                      max_attempts: int = 3,
                      base_delay: float = 1.0,
                      strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF):
    """Retry decorator for specific exceptions"""
    return retry(
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        retryable_exceptions=exceptions
    )


def retry_on_status_codes(status_codes: List[int],
                         max_attempts: int = 3,
                         base_delay: float = 1.0,
                         strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF):
    """Retry decorator for specific HTTP status codes"""
    return retry(
        max_attempts=max_attempts,
        strategy=strategy,
        base_delay=base_delay,
        retryable_status_codes=status_codes
    )


# Utility functions
def get_retry_manager() -> RetryManager:
    """Get global retry manager instance"""
    return _retry_manager


def configure_default_retry(config: RetryConfig):
    """Configure default retry behavior"""
    _retry_manager.default_config = config


# Usage examples
if __name__ == "__main__":
    import aiohttp
    
    logging.basicConfig(level=logging.INFO)
    
    # Example 1: Simple retry decorator
    @retry(max_attempts=5, base_delay=0.5, strategy=RetryStrategy.EXPONENTIAL_BACKOFF)
    def unreliable_function():
        if random.random() < 0.7:  # 70% failure rate
            raise Exception("Random failure!")
        return "Success!"
    
    # Example 2: Retry on specific exceptions
    @retry_on_exception([ConnectionError, TimeoutError], max_attempts=3)
    def network_call():
        if random.random() < 0.5:
            raise ConnectionError("Network unavailable")
        return "Network response"
    
    # Example 3: Async function with retry
    @retry(max_attempts=3, timeout=30.0, config_name="http_client")
    async def http_request(url: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status >= 500:
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status
                    )
                return await response.text()
    
    # Test the functions
    async def test_retry_examples():
        # Test sync function
        try:
            result = unreliable_function()
            print(f"Sync function result: {result}")
        except Exception as e:
            print(f"Sync function failed: {e}")
        
        # Test network call
        try:
            result = network_call()
            print(f"Network call result: {result}")
        except Exception as e:
            print(f"Network call failed: {e}")
        
        # Test async HTTP request
        try:
            result = await http_request("https://httpbin.org/delay/1")
            print(f"HTTP request succeeded (length: {len(result)})")
        except Exception as e:
            print(f"HTTP request failed: {e}")
        
        # Show retry statistics
        manager = get_retry_manager()
        stats = manager.metrics.get_stats()
        print("\nRetry Statistics:")
        for config_name, config_stats in stats.items():
            print(f"  {config_name}: {config_stats}")
    
    # Run tests
    asyncio.run(test_retry_examples())