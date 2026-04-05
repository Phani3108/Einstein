"""Tests for retry mechanisms."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock

from src.infrastructure.retry import (
    RetryConfig,
    CircuitBreaker,
    retry,
    async_retry,
    llm_retry,
    vector_store_retry,
    embedding_retry,
)
from src.domain.exceptions import (
    VectorStoreError,
    EmbeddingError,
    EntityExtractionError,
)


class TestRetryConfig:
    """Test RetryConfig class."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
        assert ConnectionError in config.retryable_exceptions
        assert VectorStoreError in config.retryable_exceptions
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=1.5,
            jitter=False,
            retryable_exceptions=[ValueError],
        )
        
        assert config.max_attempts == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 1.5
        assert config.jitter is False
        assert config.retryable_exceptions == [ValueError]
    
    def test_calculate_delay(self):
        """Test delay calculation."""
        config = RetryConfig(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=10.0,
            jitter=False,
        )
        
        assert config.calculate_delay(0) == 1.0
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(2) == 4.0
        assert config.calculate_delay(3) == 8.0
        assert config.calculate_delay(4) == 10.0  # Capped at max_delay
    
    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            base_delay=2.0,
            exponential_base=2.0,
            jitter=True,
        )
        
        delay = config.calculate_delay(1)
        # With jitter, delay should be between 2.0 and 4.0
        assert 2.0 <= delay <= 4.0
    
    def test_should_retry(self):
        """Test retry decision logic."""
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=[ValueError, ConnectionError],
        )
        
        # Should retry for retryable exceptions within max attempts
        assert config.should_retry(ValueError("test"), 0) is True
        assert config.should_retry(ConnectionError("test"), 1) is True
        
        # Should not retry for non-retryable exceptions
        assert config.should_retry(TypeError("test"), 0) is False
        
        # Should not retry when max attempts reached
        assert config.should_retry(ValueError("test"), 2) is False


class TestCircuitBreaker:
    """Test CircuitBreaker class."""
    
    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Should allow calls in closed state
        result = breaker.call(lambda: "success")
        assert result == "success"
        assert breaker.state == "CLOSED"
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after threshold failures."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)
        
        # First failure
        with pytest.raises(ValueError):
            breaker.call(lambda: exec('raise ValueError("test")'))
        assert breaker.state == "CLOSED"
        assert breaker.failure_count == 1
        
        # Second failure - should open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: exec('raise ValueError("test")'))
        assert breaker.state == "OPEN"
        assert breaker.failure_count == 2
    
    def test_circuit_breaker_blocks_calls_when_open(self):
        """Test circuit breaker blocks calls when open."""
        breaker = CircuitBreaker(failure_threshold=1, expected_exception=ValueError)
        
        # Trigger failure to open circuit
        with pytest.raises(ValueError):
            breaker.call(lambda: exec('raise ValueError("test")'))
        
        # Should block subsequent calls
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            breaker.call(lambda: "success")
    
    @pytest.mark.asyncio
    async def test_async_circuit_breaker(self):
        """Test async circuit breaker functionality."""
        breaker = CircuitBreaker(failure_threshold=2, expected_exception=ValueError)
        
        # Should allow successful async calls
        result = await breaker.acall(AsyncMock(return_value="success"))
        assert result == "success"
        
        # Should handle async failures
        async_mock = AsyncMock(side_effect=ValueError("test"))
        with pytest.raises(ValueError):
            await breaker.acall(async_mock)


class TestRetryDecorator:
    """Test retry decorator."""
    
    def test_retry_success_on_first_attempt(self):
        """Test successful function call on first attempt."""
        mock_func = Mock(return_value="success")
        
        @retry(RetryConfig(max_attempts=3))
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test successful function call after failures."""
        mock_func = Mock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        
        @retry(RetryConfig(
            max_attempts=3,
            base_delay=0.01,  # Fast retry for testing
            retryable_exceptions=[ValueError],
        ))
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_retry_exhausts_attempts(self):
        """Test retry exhausts all attempts and fails."""
        mock_func = Mock(side_effect=ValueError("persistent failure"))
        
        @retry(RetryConfig(
            max_attempts=2,
            base_delay=0.01,
            retryable_exceptions=[ValueError],
        ))
        def test_func():
            return mock_func()
        
        with pytest.raises(ValueError, match="persistent failure"):
            test_func()
        assert mock_func.call_count == 2
    
    def test_retry_non_retryable_exception(self):
        """Test retry doesn't retry non-retryable exceptions."""
        mock_func = Mock(side_effect=TypeError("not retryable"))
        
        @retry(RetryConfig(
            max_attempts=3,
            retryable_exceptions=[ValueError],
        ))
        def test_func():
            return mock_func()
        
        with pytest.raises(TypeError, match="not retryable"):
            test_func()
        assert mock_func.call_count == 1


class TestAsyncRetryDecorator:
    """Test async retry decorator."""
    
    @pytest.mark.asyncio
    async def test_async_retry_success_on_first_attempt(self):
        """Test successful async function call on first attempt."""
        mock_func = AsyncMock(return_value="success")
        
        @async_retry(RetryConfig(max_attempts=3))
        async def test_func():
            return await mock_func()
        
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """Test successful async function call after failures."""
        mock_func = AsyncMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        
        @async_retry(RetryConfig(
            max_attempts=3,
            base_delay=0.01,
            retryable_exceptions=[ValueError],
        ))
        async def test_func():
            return await mock_func()
        
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_exhausts_attempts(self):
        """Test async retry exhausts all attempts and fails."""
        mock_func = AsyncMock(side_effect=ValueError("persistent failure"))
        
        @async_retry(RetryConfig(
            max_attempts=2,
            base_delay=0.01,
            retryable_exceptions=[ValueError],
        ))
        async def test_func():
            return await mock_func()
        
        with pytest.raises(ValueError, match="persistent failure"):
            await test_func()
        assert mock_func.call_count == 2


class TestPreconfiguredRetryDecorators:
    """Test preconfigured retry decorators."""
    
    @pytest.mark.asyncio
    async def test_llm_retry_decorator(self):
        """Test LLM retry decorator configuration."""
        mock_func = AsyncMock(side_effect=[EntityExtractionError("fail"), "success"])
        
        @llm_retry
        async def test_func():
            return await mock_func()
        
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_vector_store_retry_decorator(self):
        """Test vector store retry decorator configuration."""
        mock_func = AsyncMock(side_effect=[VectorStoreError("fail"), "success"])
        
        @vector_store_retry
        async def test_func():
            return await mock_func()
        
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_embedding_retry_decorator(self):
        """Test embedding retry decorator configuration."""
        mock_func = AsyncMock(side_effect=[EmbeddingError("fail"), "success"])
        
        @embedding_retry
        async def test_func():
            return await mock_func()
        
        result = await test_func()
        assert result == "success"
        assert mock_func.call_count == 2