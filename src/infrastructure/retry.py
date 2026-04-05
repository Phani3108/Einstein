"""Retry mechanisms for external API calls and operations."""

import asyncio
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, List, Optional, Type, TypeVar, Union

from src.domain.exceptions import (
    EmbeddingError,
    EntityExtractionError,
    VectorStoreError,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """Initialize retry configuration.
        
        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: List of exceptions that should trigger retries
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [
            ConnectionError,
            TimeoutError,
            OSError,
            # Add domain-specific exceptions that should be retried
            VectorStoreError,
            EmbeddingError,
            EntityExtractionError,
        ]
    
    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            float: Delay in seconds
        """
        # Exponential backoff
        delay = self.base_delay * (self.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.max_delay)
        
        # Add jitter to avoid thundering herd
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if an exception should trigger a retry.
        
        Args:
            exception: Exception that occurred
            attempt: Current attempt number (0-based)
            
        Returns:
            bool: True if should retry, False otherwise
        """
        if attempt >= self.max_attempts - 1:
            return False
        
        return any(
            isinstance(exception, exc_type) 
            for exc_type in self.retryable_exceptions
        )


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception,
    ):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time to wait before attempting recovery
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Call function with circuit breaker protection.
        
        Args:
            func: Function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            T: Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def acall(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Async version of call method.
        
        Args:
            func: Async function to call
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            T: Function result
            
        Raises:
            Exception: If circuit is open or function fails
        """
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt reset.
        
        Returns:
            bool: True if should attempt reset
        """
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


def retry(config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic to functions.
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorator function
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(e, attempt):
                        logger.error(
                            f"Function {func.__name__} failed on attempt {attempt + 1}, not retrying",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": config.max_attempts,
                                "exception": str(e),
                                "exception_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        raise e
                    
                    delay = config.calculate_delay(attempt)
                    logger.warning(
                        f"Function {func.__name__} failed on attempt {attempt + 1}, retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": config.max_attempts,
                            "delay_seconds": delay,
                            "exception": str(e),
                            "exception_type": type(e).__name__,
                        },
                    )
                    
                    time.sleep(delay)
            
            # If we get here, all attempts failed
            logger.error(
                f"Function {func.__name__} failed after {config.max_attempts} attempts",
                extra={
                    "function": func.__name__,
                    "max_attempts": config.max_attempts,
                    "final_exception": str(last_exception),
                    "final_exception_type": type(last_exception).__name__,
                },
                exc_info=True,
            )
            raise last_exception
        
        return wrapper
    return decorator


def async_retry(config: Optional[RetryConfig] = None):
    """Decorator for adding retry logic to async functions.
    
    Args:
        config: Retry configuration
        
    Returns:
        Decorator function
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not config.should_retry(e, attempt):
                        logger.error(
                            f"Async function {func.__name__} failed on attempt {attempt + 1}, not retrying",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_attempts": config.max_attempts,
                                "exception": str(e),
                                "exception_type": type(e).__name__,
                            },
                            exc_info=True,
                        )
                        raise e
                    
                    delay = config.calculate_delay(attempt)
                    logger.warning(
                        f"Async function {func.__name__} failed on attempt {attempt + 1}, retrying in {delay:.2f}s",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "max_attempts": config.max_attempts,
                            "delay_seconds": delay,
                            "exception": str(e),
                            "exception_type": type(e).__name__,
                        },
                    )
                    
                    await asyncio.sleep(delay)
            
            # If we get here, all attempts failed
            logger.error(
                f"Async function {func.__name__} failed after {config.max_attempts} attempts",
                extra={
                    "function": func.__name__,
                    "max_attempts": config.max_attempts,
                    "final_exception": str(last_exception),
                    "final_exception_type": type(last_exception).__name__,
                },
                exc_info=True,
            )
            raise last_exception
        
        return wrapper
    return decorator


# Pre-configured retry decorators for common use cases
llm_retry = async_retry(RetryConfig(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    retryable_exceptions=[
        ConnectionError,
        TimeoutError,
        EntityExtractionError,
    ]
))

vector_store_retry = async_retry(RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=15.0,
    retryable_exceptions=[
        ConnectionError,
        TimeoutError,
        VectorStoreError,
    ]
))

embedding_retry = async_retry(RetryConfig(
    max_attempts=3,
    base_delay=1.5,
    max_delay=20.0,
    retryable_exceptions=[
        ConnectionError,
        TimeoutError,
        EmbeddingError,
    ]
))