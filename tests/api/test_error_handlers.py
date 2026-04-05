"""Tests for API error handlers."""

import pytest
from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from unittest.mock import Mock, AsyncMock

from src.api.error_handlers import (
    ErrorHandler,
    ErrorResponse,
    domain_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from src.domain.exceptions import (
    ThoughtNotFoundError,
    UserNotFoundError,
    AuthenticationError,
    EntityExtractionError,
    VectorStoreError,
    SearchError,
)


class TestErrorResponse:
    """Test ErrorResponse model."""
    
    def test_create_error_response(self):
        """Test creating an error response."""
        response = ErrorResponse.create(
            code="TEST_ERROR",
            message="Test error message",
            details={"field": "value"},
            request_id="test-123",
            status_code=400,
        )
        
        assert response.error["code"] == "TEST_ERROR"
        assert response.error["message"] == "Test error message"
        assert response.error["details"] == {"field": "value"}
        assert response.error["request_id"] == "test-123"
        assert response.error["status_code"] == 400
        assert "timestamp" in response.error
    
    def test_create_error_response_with_defaults(self):
        """Test creating an error response with default values."""
        response = ErrorResponse.create(
            code="TEST_ERROR",
            message="Test error message",
        )
        
        assert response.error["code"] == "TEST_ERROR"
        assert response.error["message"] == "Test error message"
        assert response.error["details"] is None
        assert response.error["status_code"] == 500
        assert "request_id" in response.error
        assert "timestamp" in response.error


class TestErrorHandler:
    """Test ErrorHandler class."""
    
    def test_get_status_code_for_domain_exceptions(self):
        """Test getting status codes for domain exceptions."""
        assert ErrorHandler.get_status_code(ThoughtNotFoundError("123")) == 404
        assert ErrorHandler.get_status_code(UserNotFoundError()) == 404
        assert ErrorHandler.get_status_code(AuthenticationError()) == 401
        assert ErrorHandler.get_status_code(EntityExtractionError("test")) == 422
        assert ErrorHandler.get_status_code(VectorStoreError("test")) == 503
        assert ErrorHandler.get_status_code(SearchError("test")) == 503
    
    def test_get_status_code_for_unknown_exception(self):
        """Test getting status code for unknown exception."""
        assert ErrorHandler.get_status_code(ValueError("test")) == 500
    
    def test_get_error_code_for_status_codes(self):
        """Test getting error codes for status codes."""
        assert ErrorHandler.get_error_code(400) == "BAD_REQUEST"
        assert ErrorHandler.get_error_code(401) == "UNAUTHORIZED"
        assert ErrorHandler.get_error_code(404) == "NOT_FOUND"
        assert ErrorHandler.get_error_code(422) == "UNPROCESSABLE_ENTITY"
        assert ErrorHandler.get_error_code(500) == "INTERNAL_ERROR"
        assert ErrorHandler.get_error_code(503) == "SERVICE_UNAVAILABLE"
    
    def test_get_error_code_for_unknown_status(self):
        """Test getting error code for unknown status code."""
        assert ErrorHandler.get_error_code(999) == "UNKNOWN_ERROR"
    
    def test_format_domain_exception(self):
        """Test formatting domain exceptions."""
        from uuid import uuid4
        thought_id = uuid4()
        exception = ThoughtNotFoundError(thought_id)
        
        error_response, status_code = ErrorHandler.format_domain_exception(
            exception, "test-123"
        )
        
        assert status_code == 404
        assert error_response.error["code"] == "NOT_FOUND"
        assert str(thought_id) in error_response.error["message"]
        assert error_response.error["details"]["thought_id"] == str(thought_id)
        assert error_response.error["request_id"] == "test-123"
    
    def test_format_http_exception(self):
        """Test formatting HTTP exceptions."""
        exception = HTTPException(status_code=400, detail="Bad request")
        
        error_response, status_code = ErrorHandler.format_http_exception(
            exception, "test-123"
        )
        
        assert status_code == 400
        assert error_response.error["code"] == "BAD_REQUEST"
        assert error_response.error["message"] == "Bad request"
        assert error_response.error["request_id"] == "test-123"
    
    def test_format_validation_exception(self):
        """Test formatting validation exceptions."""
        # Mock a validation error
        mock_error = Mock()
        mock_error.errors.return_value = [
            {
                "loc": ("field1",),
                "msg": "Field is required",
                "type": "value_error.missing",
            },
            {
                "loc": ("field2", "nested"),
                "msg": "Invalid value",
                "type": "value_error.invalid",
            },
        ]
        
        error_response, status_code = ErrorHandler.format_validation_exception(
            mock_error, "test-123"
        )
        
        assert status_code == 422
        assert error_response.error["code"] == "VALIDATION_ERROR"
        assert error_response.error["message"] == "Request validation failed"
        assert len(error_response.error["details"]) == 2
        assert error_response.error["details"][0]["field"] == "field1"
        assert error_response.error["details"][1]["field"] == "field2.nested"
    
    def test_format_generic_exception(self):
        """Test formatting generic exceptions."""
        exception = ValueError("Something went wrong")
        
        error_response, status_code = ErrorHandler.format_generic_exception(
            exception, "test-123"
        )
        
        assert status_code == 500
        assert error_response.error["code"] == "INTERNAL_ERROR"
        assert error_response.error["message"] == "An internal error occurred"
        assert error_response.error["details"]["exception_type"] == "ValueError"
        assert error_response.error["request_id"] == "test-123"


class TestExceptionHandlers:
    """Test exception handler functions."""
    
    @pytest.fixture
    def mock_request(self):
        """Create a mock request object."""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.state = Mock()
        request.state.request_id = "test-123"
        return request
    
    @pytest.mark.asyncio
    async def test_domain_exception_handler(self, mock_request):
        """Test domain exception handler."""
        from uuid import uuid4
        thought_id = uuid4()
        exception = ThoughtNotFoundError(thought_id)
        
        response = await domain_exception_handler(mock_request, exception)
        
        assert response.status_code == 404
        response_data = response.body.decode()
        assert "NOT_FOUND" in response_data
        assert str(thought_id) in response_data
    
    @pytest.mark.asyncio
    async def test_http_exception_handler(self, mock_request):
        """Test HTTP exception handler."""
        exception = HTTPException(status_code=400, detail="Bad request")
        
        response = await http_exception_handler(mock_request, exception)
        
        assert response.status_code == 400
        response_data = response.body.decode()
        assert "BAD_REQUEST" in response_data
        assert "Bad request" in response_data
    
    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, mock_request):
        """Test validation exception handler."""
        mock_error = Mock()
        mock_error.errors.return_value = [
            {
                "loc": ("field1",),
                "msg": "Field is required",
                "type": "value_error.missing",
            }
        ]
        
        response = await validation_exception_handler(mock_request, mock_error)
        
        assert response.status_code == 422
        response_data = response.body.decode()
        assert "VALIDATION_ERROR" in response_data
        assert "Request validation failed" in response_data
    
    @pytest.mark.asyncio
    async def test_generic_exception_handler(self, mock_request):
        """Test generic exception handler."""
        exception = ValueError("Something went wrong")
        
        response = await generic_exception_handler(mock_request, exception)
        
        assert response.status_code == 500
        response_data = response.body.decode()
        assert "INTERNAL_ERROR" in response_data
        assert "An internal error occurred" in response_data