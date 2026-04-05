"""Tests for API client functionality."""

import pytest
import httpx
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime
from pathlib import Path
import tempfile

from einstein_cli.api import (
    APIClient,
    APIError,
    NetworkError,
    AuthenticationError,
    ValidationError,
    ServerError,
    ThoughtData,
    SearchResult,
    UserStats,
)
from einstein_cli.auth import AuthManager


@pytest.fixture
def auth_manager():
    """Create a test auth manager."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield AuthManager(Path(temp_dir))


@pytest.fixture
def api_client(auth_manager):
    """Create a test API client."""
    return APIClient("http://localhost:8001", auth_manager)


class TestAPIClient:
    """Test cases for APIClient class."""

    def test_initialization(self, auth_manager):
        """Test API client initialization."""
        client = APIClient("http://localhost:8001/", auth_manager)
        
        assert client.base_url == "http://localhost:8001"
        assert client.auth_manager == auth_manager
        assert client.timeout == 30.0
        assert isinstance(client.client, httpx.AsyncClient)

    def test_get_headers_without_auth(self, api_client):
        """Test getting headers when not authenticated."""
        headers = api_client._get_headers()
        assert headers == {}

    def test_get_headers_with_auth(self, api_client):
        """Test getting headers when authenticated."""
        api_client.auth_manager.save_token("test-token")
        headers = api_client._get_headers()
        assert headers == {"Authorization": "Bearer test-token"}

    @pytest.mark.asyncio
    async def test_context_manager(self, auth_manager):
        """Test API client as async context manager."""
        async with APIClient("http://localhost:8001", auth_manager) as client:
            assert isinstance(client, APIClient)
        # Client should be closed after context exit

    @pytest.mark.asyncio
    async def test_make_request_success(self, api_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True}
        mock_response.raise_for_status.return_value = None

        with patch.object(api_client.client, 'request', return_value=mock_response) as mock_request:
            result = await api_client._make_request("GET", "/test")
            
            assert result == {"success": True}
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_make_request_authentication_error(self, api_client):
        """Test API request with authentication error."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"detail": "Unauthorized"}

        with patch.object(api_client.client, 'request', return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Authentication failed"):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_validation_error(self, api_client):
        """Test API request with validation error."""
        mock_response = Mock()
        mock_response.status_code = 422
        mock_response.json.return_value = {"detail": "Validation failed"}

        with patch.object(api_client.client, 'request', return_value=mock_response):
            with pytest.raises(ValidationError, match="Invalid request"):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_server_error(self, api_client):
        """Test API request with server error."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"detail": "Internal server error"}

        with patch.object(api_client.client, 'request', return_value=mock_response):
            with pytest.raises(ServerError, match="Server error"):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_network_error(self, api_client):
        """Test API request with network error."""
        with patch.object(api_client.client, 'request', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(NetworkError, match="Could not connect to server"):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_make_request_timeout_error(self, api_client):
        """Test API request with timeout error."""
        with patch.object(api_client.client, 'request', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(NetworkError, match="Request timed out"):
                await api_client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_authenticate_success(self, api_client):
        """Test successful authentication."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test-token",
            "expires_in": 3600
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(api_client.client, 'post', return_value=mock_response):
            token = await api_client.authenticate("test@example.com", "password")
            
            assert token == "test-token"
            assert api_client.auth_manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_authenticate_invalid_credentials(self, api_client):
        """Test authentication with invalid credentials."""
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(api_client.client, 'post', return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Invalid email or password"):
                await api_client.authenticate("test@example.com", "wrong-password")

    @pytest.mark.asyncio
    async def test_authenticate_network_error(self, api_client):
        """Test authentication with network error."""
        with patch.object(api_client.client, 'post', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(NetworkError, match="Could not connect to server"):
                await api_client.authenticate("test@example.com", "password")

    @pytest.mark.asyncio
    async def test_refresh_token_success(self, api_client):
        """Test successful token refresh."""
        # First set up an existing token
        api_client.auth_manager.save_token("old-token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token",
            "expires_in": 3600
        }
        mock_response.raise_for_status.return_value = None

        with patch.object(api_client.client, 'post', return_value=mock_response):
            new_token = await api_client.refresh_token()
            
            assert new_token == "new-token"
            assert api_client.auth_manager.load_token() == "new-token"

    @pytest.mark.asyncio
    async def test_refresh_token_no_existing_token(self, api_client):
        """Test token refresh when no token exists."""
        with pytest.raises(AuthenticationError, match="No token available to refresh"):
            await api_client.refresh_token()

    @pytest.mark.asyncio
    async def test_refresh_token_invalid_token(self, api_client):
        """Test token refresh with invalid token."""
        api_client.auth_manager.save_token("invalid-token")
        
        mock_response = Mock()
        mock_response.status_code = 401

        with patch.object(api_client.client, 'post', return_value=mock_response):
            with pytest.raises(AuthenticationError, match="Token refresh failed"):
                await api_client.refresh_token()
            
            # Token should be cleared
            assert not api_client.auth_manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_refresh_token_network_error(self, api_client):
        """Test token refresh with network error."""
        api_client.auth_manager.save_token("test-token")
        
        with patch.object(api_client.client, 'post', side_effect=httpx.ConnectError("Connection failed")):
            with pytest.raises(NetworkError, match="Could not connect to server"):
                await api_client.refresh_token()

    @pytest.mark.asyncio
    async def test_logout_success(self, api_client):
        """Test successful logout."""
        api_client.auth_manager.save_token("test-token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None

        with patch.object(api_client.client, 'post', return_value=mock_response):
            result = await api_client.logout()
            
            assert result is True
            assert not api_client.auth_manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_logout_no_token(self, api_client):
        """Test logout when no token exists."""
        result = await api_client.logout()
        assert result is True

    @pytest.mark.asyncio
    async def test_logout_server_error(self, api_client):
        """Test logout when server logout fails but local token is still cleared."""
        api_client.auth_manager.save_token("test-token")
        
        with patch.object(api_client.client, 'post', side_effect=httpx.ConnectError("Connection failed")):
            result = await api_client.logout()
            
            assert result is True
            assert not api_client.auth_manager.is_authenticated()

    @pytest.mark.asyncio
    async def test_create_thought(self, api_client):
        """Test creating a thought."""
        thought_data = {
            "id": "test-id",
            "content": "Test thought",
            "user_id": "user-123",
            "timestamp": "2024-01-01T12:00:00",
            "metadata": {"mood": "happy"}
        }

        with patch.object(api_client, '_make_request', return_value=thought_data) as mock_request:
            result = await api_client.create_thought("Test thought", {"mood": "happy"})
            
            assert isinstance(result, ThoughtData)
            assert result.content == "Test thought"
            assert result.metadata == {"mood": "happy"}
            
            mock_request.assert_called_once_with(
                "POST", 
                "/api/v1/thoughts", 
                data={"content": "Test thought", "metadata": {"mood": "happy"}}
            )

    @pytest.mark.asyncio
    async def test_create_thought_without_metadata(self, api_client):
        """Test creating a thought without metadata."""
        thought_data = {
            "id": "test-id",
            "content": "Test thought",
            "user_id": "user-123",
            "timestamp": "2024-01-01T12:00:00"
        }

        with patch.object(api_client, '_make_request', return_value=thought_data) as mock_request:
            result = await api_client.create_thought("Test thought")
            
            assert isinstance(result, ThoughtData)
            assert result.content == "Test thought"
            
            mock_request.assert_called_once_with(
                "POST", 
                "/api/v1/thoughts", 
                data={"content": "Test thought"}
            )

    @pytest.mark.asyncio
    async def test_search_thoughts(self, api_client):
        """Test searching thoughts."""
        search_data = {
            "thoughts": [
                {
                    "id": "test-id",
                    "content": "Test thought",
                    "user_id": "user-123",
                    "timestamp": "2024-01-01T12:00:00"
                }
            ],
            "total": 1,
            "query": "test",
            "execution_time": 0.1
        }

        with patch.object(api_client, '_make_request', return_value=search_data) as mock_request:
            result = await api_client.search_thoughts("test", limit=10, filters={"mood": "happy"})
            
            assert isinstance(result, SearchResult)
            assert result.query == "test"
            assert result.total == 1
            assert len(result.thoughts) == 1
            
            mock_request.assert_called_once_with(
                "GET", 
                "/api/v1/search", 
                params={"q": "test", "limit": 10, "mood": "happy"}
            )

    @pytest.mark.asyncio
    async def test_get_thoughts(self, api_client):
        """Test getting list of thoughts."""
        thoughts_data = {
            "thoughts": [
                {
                    "id": "test-id-1",
                    "content": "Test thought 1",
                    "user_id": "user-123",
                    "timestamp": "2024-01-01T12:00:00"
                },
                {
                    "id": "test-id-2",
                    "content": "Test thought 2",
                    "user_id": "user-123",
                    "timestamp": "2024-01-01T13:00:00"
                }
            ]
        }

        with patch.object(api_client, '_make_request', return_value=thoughts_data) as mock_request:
            result = await api_client.get_thoughts(limit=10, offset=0)
            
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(thought, ThoughtData) for thought in result)
            
            mock_request.assert_called_once_with(
                "GET", 
                "/api/v1/thoughts", 
                params={"limit": 10, "offset": 0}
            )

    @pytest.mark.asyncio
    async def test_get_thought_by_id(self, api_client):
        """Test getting a specific thought by ID."""
        thought_data = {
            "id": "test-id",
            "content": "Test thought",
            "user_id": "user-123",
            "timestamp": "2024-01-01T12:00:00"
        }

        with patch.object(api_client, '_make_request', return_value=thought_data) as mock_request:
            result = await api_client.get_thought_by_id("test-id")
            
            assert isinstance(result, ThoughtData)
            assert result.id == "test-id"
            assert result.content == "Test thought"
            
            mock_request.assert_called_once_with("GET", "/api/v1/thoughts/test-id")

    @pytest.mark.asyncio
    async def test_delete_thought(self, api_client):
        """Test deleting a thought."""
        with patch.object(api_client, '_make_request', return_value={}) as mock_request:
            result = await api_client.delete_thought("test-id")
            
            assert result is True
            mock_request.assert_called_once_with("DELETE", "/api/v1/thoughts/test-id")

    @pytest.mark.asyncio
    async def test_get_user_stats(self, api_client):
        """Test getting user statistics."""
        stats_data = {
            "total_thoughts": 100,
            "thoughts_this_week": 10,
            "most_common_tags": ["work", "personal"],
            "mood_distribution": {"happy": 50, "neutral": 30, "sad": 20}
        }

        with patch.object(api_client, '_make_request', return_value=stats_data) as mock_request:
            result = await api_client.get_user_stats()
            
            assert isinstance(result, UserStats)
            assert result.total_thoughts == 100
            assert result.thoughts_this_week == 10
            
            mock_request.assert_called_once_with("GET", "/api/v1/admin/stats")

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """Test health check endpoint."""
        health_data = {"status": "healthy", "timestamp": "2024-01-01T12:00:00"}

        with patch.object(api_client, '_make_request', return_value=health_data) as mock_request:
            result = await api_client.health_check()
            
            assert result == health_data
            mock_request.assert_called_once_with("GET", "/health")


class TestDataModels:
    """Test cases for API data models."""

    def test_thought_data_model(self):
        """Test ThoughtData model validation."""
        data = {
            "id": "test-id",
            "content": "Test content",
            "user_id": "user-123",
            "timestamp": datetime.now(),
            "metadata": {"mood": "happy"}
        }
        
        thought = ThoughtData(**data)
        assert thought.id == "test-id"
        assert thought.content == "Test content"
        assert thought.metadata == {"mood": "happy"}

    def test_thought_data_model_without_metadata(self):
        """Test ThoughtData model without metadata."""
        data = {
            "id": "test-id",
            "content": "Test content",
            "user_id": "user-123",
            "timestamp": datetime.now()
        }
        
        thought = ThoughtData(**data)
        assert thought.metadata is None

    def test_search_result_model(self):
        """Test SearchResult model validation."""
        data = {
            "thoughts": [
                {
                    "id": "test-id",
                    "content": "Test content",
                    "user_id": "user-123",
                    "timestamp": datetime.now()
                }
            ],
            "total": 1,
            "query": "test query",
            "execution_time": 0.1
        }
        
        result = SearchResult(**data)
        assert len(result.thoughts) == 1
        assert result.total == 1
        assert result.query == "test query"

    def test_user_stats_model(self):
        """Test UserStats model validation."""
        data = {
            "total_thoughts": 100,
            "thoughts_this_week": 10,
            "most_common_tags": ["work", "personal"],
            "mood_distribution": {"happy": 50, "neutral": 30}
        }
        
        stats = UserStats(**data)
        assert stats.total_thoughts == 100
        assert stats.thoughts_this_week == 10
        assert "work" in stats.most_common_tags