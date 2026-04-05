"""Tests for the User domain entity."""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.domain.entities.user import User


def test_user_creation():
    """Test that a user can be created with valid data."""
    # Arrange
    user_id = uuid.uuid4()
    email = "test@example.com"
    hashed_password = "hashed_password_string"
    created_at = datetime.now()
    updated_at = datetime.now()
    last_login = datetime.now()

    # Act
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        created_at=created_at,
        updated_at=updated_at,
        last_login=last_login,
    )

    # Assert
    assert user.id == user_id
    assert user.email == email
    assert user.hashed_password == hashed_password
    assert user.is_active is True
    assert user.is_admin is False
    assert user.created_at == created_at
    assert user.updated_at == updated_at
    assert user.last_login == last_login


def test_user_default_values():
    """Test that a user has correct default values."""
    # Arrange
    user_id = uuid.uuid4()
    email = "test@example.com"
    hashed_password = "hashed_password_string"

    # Act
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
    )

    # Assert
    assert user.is_active is True
    assert user.is_admin is False
    assert user.last_login is None
    assert isinstance(user.created_at, datetime)
    assert isinstance(user.updated_at, datetime)


def test_user_admin_flag():
    """Test that a user can be created as an admin."""
    # Arrange
    user_id = uuid.uuid4()
    email = "admin@example.com"
    hashed_password = "hashed_password_string"

    # Act
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        is_admin=True,
    )

    # Assert
    assert user.is_admin is True


def test_user_inactive_flag():
    """Test that a user can be created as inactive."""
    # Arrange
    user_id = uuid.uuid4()
    email = "inactive@example.com"
    hashed_password = "hashed_password_string"

    # Act
    user = User(
        id=user_id,
        email=email,
        hashed_password=hashed_password,
        is_active=False,
    )

    # Assert
    assert user.is_active is False


def test_user_invalid_email():
    """Test that a user cannot be created with an invalid email."""
    # Arrange
    user_id = uuid.uuid4()
    invalid_email = "not_an_email"
    hashed_password = "hashed_password_string"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        User(
            id=user_id,
            email=invalid_email,
            hashed_password=hashed_password,
        )

    assert "email" in str(exc_info.value)


def test_user_empty_email():
    """Test that a user cannot be created with an empty email."""
    # Arrange
    user_id = uuid.uuid4()
    empty_email = ""
    hashed_password = "hashed_password_string"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        User(
            id=user_id,
            email=empty_email,
            hashed_password=hashed_password,
        )

    assert "Email cannot be empty" in str(exc_info.value)
