"""Integration tests for admin API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
from datetime import datetime

from src.api.app import create_app
from src.domain.entities.user import User
from src.domain.exceptions import UserAlreadyExistsError
from src.container import container


@pytest.fixture
def app():
    """Create test FastAPI app."""
    return create_app()


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_admin_user():
    """Create a mock admin user."""
    return User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed_password",
        is_admin=True,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_regular_user():
    """Create a mock regular user."""
    return User(
        id=uuid4(),
        email="user@example.com",
        hashed_password="hashed_password",
        is_admin=False,
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@pytest.fixture
def mock_auth_middleware():
    """Mock authentication middleware."""
    mock = Mock()
    mock.require_admin = AsyncMock()
    return mock


class TestAdminUsersEndpoints:
    """Test admin user management endpoints."""

    def test_get_users_success(self, client, mock_admin_user, mock_auth_middleware):
        """Test successful retrieval of users list."""
        # Mock dependencies
        mock_get_users_usecase = AsyncMock()
        mock_users = [
            User(
                id=uuid4(),
                email="user1@example.com",
                hashed_password="hash1",
                is_admin=False,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            User(
                id=uuid4(),
                email="user2@example.com",
                hashed_password="hash2",
                is_admin=True,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
        ]
        mock_get_users_usecase.execute.return_value = mock_users
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        # Override container dependencies
        with container.auth_middleware.override(mock_auth_middleware):
            with container.get_users_usecase.override(mock_get_users_usecase):
                response = client.get("/api/v1/admin/users?skip=0&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert len(data["users"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 10
        assert data["total"] == 2

        # Verify use case was called with correct parameters
        mock_get_users_usecase.execute.assert_called_once_with(skip=0, limit=10)

    def test_get_users_unauthorized(self, client, mock_auth_middleware):
        """Test get users without admin privileges."""
        from fastapi import HTTPException, status

        mock_auth_middleware.require_admin.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

        with container.auth_middleware.override(mock_auth_middleware):
            response = client.get("/api/v1/admin/users")

        assert response.status_code == 403

    def test_get_users_with_pagination(self, client, mock_admin_user, mock_auth_middleware):
        """Test get users with custom pagination parameters."""
        mock_get_users_usecase = AsyncMock()
        mock_get_users_usecase.execute.return_value = []
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        with container.auth_middleware.override(mock_auth_middleware):
            with container.get_users_usecase.override(mock_get_users_usecase):
                response = client.get("/api/v1/admin/users?skip=20&limit=50")

        assert response.status_code == 200
        mock_get_users_usecase.execute.assert_called_once_with(skip=20, limit=50)

    def test_create_user_success(self, client, mock_admin_user, mock_auth_middleware):
        """Test successful user creation."""
        mock_create_user_usecase = AsyncMock()
        new_user = User(
            id=uuid4(),
            email="newuser@example.com",
            hashed_password="hashed_password",
            is_admin=False,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_create_user_usecase.execute.return_value = new_user
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        user_data = {
            "email": "newuser@example.com",
            "password": "secure_password123",
            "is_admin": False,
            "is_active": True,
        }

        with container.auth_middleware.override(mock_auth_middleware):
            with container.create_user_usecase.override(mock_create_user_usecase):
                response = client.post("/api/v1/admin/users", json=user_data)

        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["user"]["is_admin"] is False
        assert data["message"] == "User created successfully"

        # Verify use case was called with correct parameters
        mock_create_user_usecase.execute.assert_called_once_with(
            email="newuser@example.com",
            password="secure_password123",
            is_admin=False,
            is_active=True,
        )

    def test_create_user_already_exists(self, client, mock_admin_user, mock_auth_middleware):
        """Test creating a user that already exists."""
        mock_create_user_usecase = AsyncMock()
        mock_create_user_usecase.execute.side_effect = UserAlreadyExistsError(
            "newuser@example.com"
        )
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        user_data = {
            "email": "newuser@example.com",
            "password": "secure_password123",
            "is_admin": False,
            "is_active": True,
        }

        with container.auth_middleware.override(mock_auth_middleware):
            with container.create_user_usecase.override(mock_create_user_usecase):
                response = client.post("/api/v1/admin/users", json=user_data)

        assert response.status_code == 409
        data = response.json()
        assert "User with email newuser@example.com already exists" in data["detail"]

    def test_create_user_invalid_email(self, client, mock_admin_user, mock_auth_middleware):
        """Test creating a user with invalid email."""
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        user_data = {
            "email": "invalid-email",
            "password": "secure_password123",
            "is_admin": False,
            "is_active": True,
        }

        with container.auth_middleware.override(mock_auth_middleware):
            response = client.post("/api/v1/admin/users", json=user_data)

        assert response.status_code == 422  # Validation error

    def test_create_user_unauthorized(self, client, mock_auth_middleware):
        """Test creating a user without admin privileges."""
        from fastapi import HTTPException, status

        mock_auth_middleware.require_admin.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

        user_data = {
            "email": "newuser@example.com",
            "password": "secure_password123",
            "is_admin": False,
            "is_active": True,
        }

        with container.auth_middleware.override(mock_auth_middleware):
            response = client.post("/api/v1/admin/users", json=user_data)

        assert response.status_code == 403


class TestAdminHealthEndpoint:
    """Test admin health check endpoint."""

    def test_get_system_health_success(self, client, mock_admin_user, mock_auth_middleware):
        """Test successful health check."""
        mock_health_usecase = AsyncMock()
        health_data = {
            "timestamp": "2024-01-15T10:30:00",
            "status": "healthy",
            "services": {
                "database": {
                    "status": "healthy",
                    "message": "Database connection successful",
                }
            },
            "statistics": {
                "users_accessible": True,
                "thoughts_accessible": True,
            },
        }
        mock_health_usecase.execute.return_value = health_data
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        with container.auth_middleware.override(mock_auth_middleware):
            with container.get_system_health_usecase.override(mock_health_usecase):
                response = client.get("/api/v1/admin/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "services" in data
        assert "statistics" in data
        assert data["services"]["database"]["status"] == "healthy"

    def test_get_system_health_degraded(self, client, mock_admin_user, mock_auth_middleware):
        """Test health check with degraded status."""
        mock_health_usecase = AsyncMock()
        health_data = {
            "timestamp": "2024-01-15T10:30:00",
            "status": "degraded",
            "services": {
                "database": {
                    "status": "unhealthy",
                    "message": "Database connection failed",
                }
            },
            "statistics": {
                "error": "Failed to retrieve statistics",
            },
        }
        mock_health_usecase.execute.return_value = health_data
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        with container.auth_middleware.override(mock_auth_middleware):
            with container.get_system_health_usecase.override(mock_health_usecase):
                response = client.get("/api/v1/admin/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "degraded"
        assert data["services"]["database"]["status"] == "unhealthy"

    def test_get_system_health_unauthorized(self, client, mock_auth_middleware):
        """Test health check without admin privileges."""
        from fastapi import HTTPException, status

        mock_auth_middleware.require_admin.side_effect = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )

        with container.auth_middleware.override(mock_auth_middleware):
            response = client.get("/api/v1/admin/health")

        assert response.status_code == 403

    def test_get_system_health_exception_handling(
        self, client, mock_admin_user, mock_auth_middleware
    ):
        """Test health check with exception in use case."""
        mock_health_usecase = AsyncMock()
        mock_health_usecase.execute.side_effect = Exception("Health check failed")
        mock_auth_middleware.require_admin.return_value = mock_admin_user

        with container.auth_middleware.override(mock_auth_middleware):
            with container.get_system_health_usecase.override(mock_health_usecase):
                response = client.get("/api/v1/admin/health")

        assert response.status_code == 200  # Health endpoint should always return 200
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "health_check" in data["services"]
        assert data["services"]["health_check"]["status"] == "failed"


class TestAdminEndpointsIntegration:
    """Integration tests for admin endpoints."""

    def test_admin_endpoints_require_authentication(self, client):
        """Test that all admin endpoints require authentication."""
        endpoints = [
            ("GET", "/api/v1/admin/users"),
            ("POST", "/api/v1/admin/users"),
            ("GET", "/api/v1/admin/health"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(
                    endpoint,
                    json={
                        "email": "test@example.com",
                        "password": "password123",
                        "is_admin": False,
                        "is_active": True,
                    },
                )

            # Should return 401 or 403 (depending on middleware implementation)
            assert response.status_code in [401, 403]

    def test_admin_endpoints_openapi_documentation(self, client):
        """Test that admin endpoints are properly documented in OpenAPI."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        openapi_spec = response.json()
        paths = openapi_spec["paths"]

        # Check that admin endpoints are documented
        assert "/api/v1/admin/users" in paths
        assert "/api/v1/admin/health" in paths

        # Check that endpoints have proper tags
        users_endpoint = paths["/api/v1/admin/users"]["get"]
        assert "admin" in users_endpoint["tags"]

        health_endpoint = paths["/api/v1/admin/health"]["get"]
        assert "admin" in health_endpoint["tags"]