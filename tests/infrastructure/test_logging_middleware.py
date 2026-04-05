"""Tests for logging middleware."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, Response

from src.infrastructure.middleware.logging_middleware import LoggingMiddleware


class TestLoggingMiddleware:
    """Test LoggingMiddleware class."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock(spec=Request)
        request.method = "GET"
        request.url.path = "/api/test"
        request.query_params = {}
        request.headers = {"user-agent": "test-agent"}
        request.client.host = "127.0.0.1"
        request.state = Mock()
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create a mock response object."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.headers = {}
        return response
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        app = Mock()
        return LoggingMiddleware(app)
    
    @pytest.mark.asyncio
    @patch('src.infrastructure.middleware.logging_middleware.logger')
    async def test_successful_request_logging(self, mock_logger, middleware, mock_request, mock_response):
        """Test logging of successful request."""
        # Mock call_next to return successful response
        call_next = AsyncMock(return_value=mock_response)
        
        response = await middleware.dispatch(mock_request, call_next)
        
        # Verify request ID was set
        assert hasattr(mock_request.state, 'request_id')
        assert mock_request.state.request_id is not None
        
        # Verify response headers include request ID
        assert "X-Request-ID" in mock_response.headers
        assert mock_response.headers["X-Request-ID"] == mock_request.state.request_id
        
        # Verify logging calls
        assert mock_logger.info.call_count == 2  # Start and completion
        
        # Check start log
        start_call = mock_logger.info.call_args_list[0]
        assert "Request started" in start_call[0][0]
        start_extra = start_call[1]["extra"]
        assert start_extra["method"] == "GET"
        assert start_extra["path"] == "/api/test"
        assert start_extra["request_id"] == mock_request.state.request_id
        
        # Check completion log
        completion_call = mock_logger.info.call_args_list[1]
        assert "Request completed" in completion_call[0][0]
        completion_extra = completion_call[1]["extra"]
        assert completion_extra["status_code"] == 200
        assert "duration_seconds" in completion_extra
    
    @pytest.mark.asyncio
    @patch('src.infrastructure.middleware.logging_middleware.logger')
    async def test_failed_request_logging(self, mock_logger, middleware, mock_request):
        """Test logging of failed request."""
        # Mock call_next to raise exception
        test_exception = ValueError("Test error")
        call_next = AsyncMock(side_effect=test_exception)
        
        with pytest.raises(ValueError):
            await middleware.dispatch(mock_request, call_next)
        
        # Verify error logging
        mock_logger.error.assert_called_once()
        error_call = mock_logger.error.call_args
        assert "Request failed" in error_call[0][0]
        error_extra = error_call[1]["extra"]
        assert error_extra["exception"] == "Test error"
        assert error_extra["exception_type"] == "ValueError"
        assert "duration_seconds" in error_extra
    
    @pytest.mark.asyncio
    @patch('src.infrastructure.middleware.logging_middleware.logger')
    async def test_user_context_logging(self, mock_logger, middleware, mock_request, mock_response):
        """Test logging with user context."""
        # Add user to request state
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_request.state.user = mock_user
        
        call_next = AsyncMock(return_value=mock_response)
        
        await middleware.dispatch(mock_request, call_next)
        
        # Check that user_id is included in logs
        start_call = mock_logger.info.call_args_list[0]
        start_extra = start_call[1]["extra"]
        assert start_extra["user_id"] == "user-123"
        
        completion_call = mock_logger.info.call_args_list[1]
        completion_extra = completion_call[1]["extra"]
        assert completion_extra["user_id"] == "user-123"
    
    def test_get_client_ip_from_forwarded_header(self, middleware, mock_request):
        """Test extracting client IP from X-Forwarded-For header."""
        mock_request.headers = {"x-forwarded-for": "192.168.1.1, 10.0.0.1"}
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.1"
    
    def test_get_client_ip_from_real_ip_header(self, middleware, mock_request):
        """Test extracting client IP from X-Real-IP header."""
        mock_request.headers = {"x-real-ip": "192.168.1.2"}
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.2"
    
    def test_get_client_ip_from_client_object(self, middleware, mock_request):
        """Test extracting client IP from request.client."""
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.3"
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "192.168.1.3"
    
    def test_get_client_ip_unknown(self, middleware, mock_request):
        """Test handling unknown client IP."""
        mock_request.headers = {}
        mock_request.client = None
        
        ip = middleware._get_client_ip(mock_request)
        assert ip == "unknown"