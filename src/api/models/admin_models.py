"""API models for admin endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr

from src.domain.entities.user import User


class UserResponse(BaseModel):
    """Response model for user data."""

    id: UUID
    email: EmailStr
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        """Create a UserResponse from a domain User entity.

        Args:
            user: The domain user entity

        Returns:
            UserResponse instance
        """
        return cls(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
        )


class UsersListResponse(BaseModel):
    """Response model for paginated users list."""

    users: List[UserResponse]
    total: int
    skip: int
    limit: int

    @classmethod
    def from_domain_list(
        cls, users: List[User], total: int, skip: int, limit: int
    ) -> "UsersListResponse":
        """Create a UsersListResponse from a list of domain User entities.

        Args:
            users: List of domain user entities
            total: Total number of users (for pagination)
            skip: Number of users skipped
            limit: Maximum number of users returned

        Returns:
            UsersListResponse instance
        """
        return cls(
            users=[UserResponse.from_domain(user) for user in users],
            total=total,
            skip=skip,
            limit=limit,
        )


class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    email: EmailStr
    password: str
    is_admin: bool = False
    is_active: bool = True

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "secure_password123",
                "is_admin": False,
                "is_active": True,
            }
        }


class CreateUserResponse(BaseModel):
    """Response model for user creation."""

    user: UserResponse
    message: str = "User created successfully"

    @classmethod
    def from_domain(cls, user: User) -> "CreateUserResponse":
        """Create a CreateUserResponse from a domain User entity.

        Args:
            user: The domain user entity

        Returns:
            CreateUserResponse instance
        """
        return cls(user=UserResponse.from_domain(user))


class HealthCheckResponse(BaseModel):
    """Response model for system health check."""

    timestamp: str
    status: str  # "healthy", "degraded", "unhealthy"
    services: Dict[str, Dict[str, Any]]
    statistics: Dict[str, Any]

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "example": {
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
        }


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    detail: Optional[str] = None
    timestamp: str = datetime.now().isoformat()

    class Config:
        """Pydantic configuration."""

        schema_extra = {
            "example": {
                "error": "User already exists",
                "detail": "A user with this email address already exists",
                "timestamp": "2024-01-15T10:30:00",
            }
        }