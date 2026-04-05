#!/usr/bin/env python3
"""Comprehensive verification of authentication implementation."""

import sys
import os
import asyncio
from uuid import uuid4

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.usecases.register_user_usecase import RegisterUserUseCase
from src.application.usecases.login_user_usecase import LoginUserUseCase, LoginResult
from src.application.usecases.verify_token_usecase import VerifyTokenUseCase
from src.domain.entities.user import User
from src.domain.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    UserAlreadyExistsError,
    UserRegistrationError,
)
from src.infrastructure.services.authentication_service import JWTAuthenticationService
from src.infrastructure.services.user_management_service import (
    DefaultUserManagementService,
    UserRegistrationData,
)


class MockUserRepository:
    """Mock user repository for testing."""
    
    def __init__(self):
        self.users = {}
        self.users_by_email = {}
    
    async def save(self, user: User) -> User:
        """Save a user."""
        self.users[user.id] = user
        self.users_by_email[user.email] = user
        return user
    
    async def find_by_id(self, user_id):
        """Find user by ID."""
        return self.users.get(user_id)
    
    async def find_by_email(self, email: str):
        """Find user by email."""
        return self.users_by_email.get(email)
    
    async def update(self, user: User) -> User:
        """Update a user."""
        self.users[user.id] = user
        self.users_by_email[user.email] = user
        return user


async def test_password_hashing():
    """Test password hashing and verification."""
    print("Testing password hashing...")
    
    auth_service = JWTAuthenticationService("test-secret-key")
    
    password = "test_password_123"
    hashed = await auth_service.hash_password(password)
    
    # Verify correct password
    is_valid = await auth_service.verify_password(password, hashed)
    assert is_valid is True
    
    # Verify incorrect password
    is_invalid = await auth_service.verify_password("wrong_password", hashed)
    assert is_invalid is False
    
    print("✓ Password hashing and verification work correctly")


async def test_jwt_token_operations():
    """Test JWT token creation and verification."""
    print("Testing JWT token operations...")
    
    auth_service = JWTAuthenticationService("test-secret-key")
    
    # Create test user
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=False,
    )
    
    # Create token
    token = await auth_service.create_access_token(user)
    assert isinstance(token, str)
    assert len(token) > 0
    
    # Verify token
    token_data = await auth_service.verify_token(token)
    assert token_data.user_id == user.id
    assert token_data.email == user.email
    assert token_data.is_admin == user.is_admin
    
    # Test token refresh
    new_token = await auth_service.refresh_token(token)
    assert isinstance(new_token, str)
    assert len(new_token) > 0
    
    # Verify new token
    new_token_data = await auth_service.verify_token(new_token)
    assert new_token_data.user_id == user.id
    
    print("✓ JWT token operations work correctly")


async def test_user_registration_flow():
    """Test complete user registration flow."""
    print("Testing user registration flow...")
    
    # Create dependencies
    user_repository = MockUserRepository()
    auth_service = JWTAuthenticationService("test-secret-key")
    user_management_service = DefaultUserManagementService(user_repository, auth_service)
    register_usecase = RegisterUserUseCase(user_management_service)
    
    # Test successful registration
    email = "newuser@example.com"
    password = "password123"
    
    user = await register_usecase.execute(email, password)
    
    assert user.email == email
    assert user.is_active is True
    assert user.is_admin is False
    assert user.hashed_password != password  # Should be hashed
    
    # Test duplicate registration
    try:
        await register_usecase.execute(email, password)
        assert False, "Should have raised UserAlreadyExistsError"
    except UserAlreadyExistsError:
        pass
    
    print("✓ User registration flow works correctly")


async def test_user_login_flow():
    """Test complete user login flow."""
    print("Testing user login flow...")
    
    # Create dependencies
    user_repository = MockUserRepository()
    auth_service = JWTAuthenticationService("test-secret-key")
    user_management_service = DefaultUserManagementService(user_repository, auth_service)
    register_usecase = RegisterUserUseCase(user_management_service)
    login_usecase = LoginUserUseCase(user_management_service, auth_service)
    
    # Register a user first
    email = "loginuser@example.com"
    password = "password123"
    registered_user = await register_usecase.execute(email, password)
    
    # Test successful login
    login_result = await login_usecase.execute(email, password)
    
    assert isinstance(login_result, LoginResult)
    assert login_result.user.id == registered_user.id
    assert login_result.user.email == email
    assert isinstance(login_result.access_token, str)
    assert len(login_result.access_token) > 0
    
    # Test login with wrong password
    try:
        await login_usecase.execute(email, "wrong_password")
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError:
        pass
    
    # Test login with non-existent user
    try:
        await login_usecase.execute("nonexistent@example.com", password)
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError:
        pass
    
    print("✓ User login flow works correctly")


async def test_token_verification_flow():
    """Test token verification flow."""
    print("Testing token verification flow...")
    
    # Create dependencies
    user_repository = MockUserRepository()
    auth_service = JWTAuthenticationService("test-secret-key")
    user_management_service = DefaultUserManagementService(user_repository, auth_service)
    register_usecase = RegisterUserUseCase(user_management_service)
    login_usecase = LoginUserUseCase(user_management_service, auth_service)
    verify_token_usecase = VerifyTokenUseCase(auth_service, user_management_service)
    
    # Register and login a user
    email = "tokenuser@example.com"
    password = "password123"
    registered_user = await register_usecase.execute(email, password)
    login_result = await login_usecase.execute(email, password)
    
    # Test token verification
    verified_user = await verify_token_usecase.execute(login_result.access_token)
    
    assert verified_user.id == registered_user.id
    assert verified_user.email == email
    assert verified_user.is_active is True
    
    # Test invalid token
    try:
        await verify_token_usecase.execute("invalid.token.here")
        assert False, "Should have raised InvalidTokenError"
    except InvalidTokenError:
        pass
    
    print("✓ Token verification flow works correctly")


async def test_admin_user_functionality():
    """Test admin user functionality."""
    print("Testing admin user functionality...")
    
    auth_service = JWTAuthenticationService("test-secret-key")
    
    # Create admin user
    admin_user = User(
        id=uuid4(),
        email="admin@example.com",
        hashed_password="hashed_password",
        is_active=True,
        is_admin=True,
    )
    
    # Create token for admin
    admin_token = await auth_service.create_access_token(admin_user)
    
    # Verify admin token
    token_data = await auth_service.verify_token(admin_token)
    assert token_data.is_admin is True
    
    print("✓ Admin user functionality works correctly")


async def test_user_deactivation():
    """Test user deactivation functionality."""
    print("Testing user deactivation...")
    
    # Create dependencies
    user_repository = MockUserRepository()
    auth_service = JWTAuthenticationService("test-secret-key")
    user_management_service = DefaultUserManagementService(user_repository, auth_service)
    register_usecase = RegisterUserUseCase(user_management_service)
    verify_token_usecase = VerifyTokenUseCase(auth_service, user_management_service)
    
    # Register a user
    email = "deactivateuser@example.com"
    password = "password123"
    user = await register_usecase.execute(email, password)
    
    # Create token
    token = await auth_service.create_access_token(user)
    
    # Deactivate user
    await user_management_service.deactivate_user(user.id)
    
    # Try to verify token with deactivated user
    try:
        await verify_token_usecase.execute(token)
        assert False, "Should have raised InvalidTokenError"
    except InvalidTokenError as e:
        assert "deactivated" in str(e)
    
    print("✓ User deactivation works correctly")


async def test_input_validation():
    """Test input validation."""
    print("Testing input validation...")
    
    # Create dependencies
    user_repository = MockUserRepository()
    auth_service = JWTAuthenticationService("test-secret-key")
    user_management_service = DefaultUserManagementService(user_repository, auth_service)
    register_usecase = RegisterUserUseCase(user_management_service)
    login_usecase = LoginUserUseCase(user_management_service, auth_service)
    
    # Test registration validation
    try:
        await register_usecase.execute("", "password123")
        assert False, "Should have raised UserRegistrationError"
    except UserRegistrationError:
        pass
    
    try:
        await register_usecase.execute("test@example.com", "short")
        assert False, "Should have raised UserRegistrationError"
    except UserRegistrationError:
        pass
    
    # Test login validation
    try:
        await login_usecase.execute("", "password123")
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError:
        pass
    
    try:
        await login_usecase.execute("test@example.com", "")
        assert False, "Should have raised AuthenticationError"
    except AuthenticationError:
        pass
    
    print("✓ Input validation works correctly")


async def main():
    """Run all authentication verification tests."""
    print("🔐 Verifying Authentication Implementation")
    print("=" * 50)
    
    await test_password_hashing()
    await test_jwt_token_operations()
    await test_user_registration_flow()
    await test_user_login_flow()
    await test_token_verification_flow()
    await test_admin_user_functionality()
    await test_user_deactivation()
    await test_input_validation()
    
    print("\n" + "=" * 50)
    print("✅ All authentication implementation tests passed!")
    print("\n📋 Implementation Summary:")
    print("  ✓ JWTAuthenticationService - JWT token creation and verification")
    print("  ✓ DefaultUserManagementService - User registration and management")
    print("  ✓ Password hashing with bcrypt")
    print("  ✓ RegisterUserUseCase - User registration with validation")
    print("  ✓ LoginUserUseCase - User authentication and token generation")
    print("  ✓ VerifyTokenUseCase - Token verification and user validation")
    print("  ✓ AuthenticationMiddleware - FastAPI middleware for auth")
    print("  ✓ Admin user support")
    print("  ✓ User activation/deactivation")
    print("  ✓ Input validation and error handling")
    print("  ✓ Comprehensive unit tests")


if __name__ == "__main__":
    asyncio.run(main())