"""Integration tests for error handling and logging."""

import json
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from src.api.app import create_app
from src.domain.exceptions import ThoughtNotFoundError, EntityExtractionError


class TestErrorHandlingIntegration:
    """Test error handling integration with the API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def mock_container(self):
        """Mock the dependency injection container."""
        with patch('src.api.app.container') as mock_container:
            yield mock_container
    
    def test_domain_exception_handling(self, client, mock_container):
        """Test that domain exceptions are properly handled."""
        # Mock the use case to raise a domain exception
        mock_usecase = Mock()
        mock_usecase.execute.side_effect = ThoughtNotFoundError("test-id")
        mock_container.get_thought_by_id_usecase.return_value = mock_usecase
        
        # Mock auth middleware to allow request
        mock_auth = Mock()
        mock_auth.return_value = None
        mock_container.auth_middleware.return_value = mock_auth
        
        # Make request that should trigger the exception
        response = client.get("/api/v1/thoughts/test-id")
        
        # Verify error response format
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert error_data["error"]["code"] == "NOT_FOUND"
        assert "test-id" in error_data["error"]["message"]
        assert "timestamp" in error_data["error"]
        assert "request_id" in error_data["error"]
        assert error_data["error"]["status_code"] == 404
    
    def test_validation_error_handling(self, client, mock_container):
        """Test that validation errors are properly handled."""
        # Mock auth middleware
        mock_auth = Mock()
        mock_auth.return_value = None
        mock_container.auth_middleware.return_value = mock_auth
        
        # Make request with invalid data
        response = client.post(
            "/api/v1/thoughts",
            json={"invalid_field": "value"}  # Missing required 'content' field
        )
        
        # Verify validation error response
        assert response.status_code == 422
        error_data = response.json()
        
        assert "error" in error_data
        assert error_data["error"]["code"] == "VALIDATION_ERROR"
        assert error_data["error"]["message"] == "Request validation failed"
        assert "details" in error_data["error"]
        assert isinstance(error_data["error"]["details"], list)
    
    def test_http_exception_handling(self, client):
        """Test that HTTP exceptions are properly handled."""
        # Make request to non-existent endpoint
        response = client.get("/api/v1/nonexistent")
        
        # Verify HTTP error response
        assert response.status_code == 404
        error_data = response.json()
        
        assert "error" in error_data
        assert error_data["error"]["code"] == "NOT_FOUND"
        assert "timestamp" in error_data["error"]
        assert "request_id" in error_data["error"]
    
    @patch('src.infrastructure.logging.setup_logging')
    def test_logging_setup_on_app_creation(self, mock_setup_logging):
        """Test that logging is set up when app is created."""
        create_app()
        
        mock_setup_logging.assert_called_once_with(
            level="INFO",
            format_type="json",
            enable_console=True,
            enable_file=False,
        )
    
    def test_request_id_in_response_headers(self, client):
        """Test that request ID is included in response headers."""
        response = client.get("/api/v1/nonexistent")
        
        assert "X-Request-ID" in response.headers
        assert response.headers["X-Request-ID"] is not None
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.options("/api/v1/thoughts")
        
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers
    
    def test_service_unavailable_error_handling(self, client, mock_container):
        """Test handling of service unavailable errors."""
        # Mock the use case to raise a service error
        mock_usecase = Mock()
        mock_usecase.execute.side_effect = EntityExtractionError("Service unavailable")
        mock_container.create_thought_usecase.return_value = mock_usecase
        
        # Mock auth middleware
        mock_auth = Mock()
        mock_auth.return_value = None
        mock_container.auth_middleware.return_value = mock_auth
        
        # Make request that should trigger the exception
        response = client.post(
            "/api/v1/thoughts",
            json={"content": "Test thought"}
        )
        
        # Verify service error response
        assert response.status_code == 422
        error_data = response.json()
        
        assert error_data["error"]["code"] == "UNPROCESSABLE_ENTITY"
        assert "Service unavailable" in error_data["error"]["message"]
    
    def test_error_response_consistency(self, client):
        """Test that all error responses follow the same format."""
        # Test different types of errors
        responses = [
            client.get("/api/v1/nonexistent"),  # 404
            client.post("/api/v1/thoughts", json={}),  # 422 validation
        ]
        
        for response in responses:
            error_data = response.json()
            
            # Verify consistent error structure
            assert "error" in error_data
            error = error_data["error"]
            
            # Required fields
            assert "code" in error
            assert "message" in error
            assert "timestamp" in error
            assert "request_id" in error
            assert "status_code" in error
            
            # Verify timestamp format (ISO format)
            assert "T" in error["timestamp"]
            assert error["timestamp"].endswith("Z") or "+" in error["timestamp"]
            
            # Verify status code matches HTTP status
            assert error["status_code"] == response.status_code