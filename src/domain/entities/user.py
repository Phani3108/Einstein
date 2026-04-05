"""User domain entity for the Personal Semantic Engine."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator


class User(BaseModel):
    """A user of the Personal Semantic Engine."""

    id: UUID
    email: EmailStr
    hashed_password: str
    is_active: bool = True
    is_admin: bool = False
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_login: Optional[datetime] = None

    @validator("email")
    def email_not_empty(cls, v: str) -> str:
        """Validate that the email is not empty.

        Args:
            v: The email to validate

        Returns:
            The validated email

        Raises:
            ValueError: If the email is empty
        """
        if not v.strip():
            raise ValueError("Email cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects
