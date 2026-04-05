"""Tests for authentication management."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch

from einstein_cli.auth import AuthManager


@pytest.fixture
def auth_manager():
    """Create a test auth manager with temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield AuthManager(Path(temp_dir))


class TestAuthManager:
    """Test cases for AuthManager class."""

    def test_initialization(self):
        """Test AuthManager initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            auth_manager = AuthManager(config_dir)
            
            assert auth_manager.config_dir == config_dir
            assert auth_manager.token_file == config_dir / "token.json"
            assert auth_manager._token_data is None

    def test_initialization_creates_directory(self):
        """Test that initialization creates config directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "nonexistent" / "einstein"
            auth_manager = AuthManager(config_dir)
            
            assert config_dir.exists()
            assert config_dir.is_dir()

    def test_save_token_without_expiration(self, auth_manager):
        """Test saving token without expiration time."""
        auth_manager.save_token("test-token")
        
        assert auth_manager.token_file.exists()
        assert auth_manager._token_data is not None
        assert auth_manager._token_data["token"] == "test-token"
        assert "created_at" in auth_manager._token_data
        assert "expires_at" not in auth_manager._token_data

    def test_save_token_with_expiration(self, auth_manager):
        """Test saving token with expiration time."""
        auth_manager.save_token("test-token", expires_in=3600)
        
        assert auth_manager.token_file.exists()
        assert auth_manager._token_data is not None
        assert auth_manager._token_data["token"] == "test-token"
        assert "expires_at" in auth_manager._token_data

    def test_save_token_file_permissions(self, auth_manager):
        """Test that token file has correct permissions (owner read/write only)."""
        auth_manager.save_token("test-token")
        
        # Check file permissions (0o600 = owner read/write only)
        file_mode = auth_manager.token_file.stat().st_mode & 0o777
        assert file_mode == 0o600

    def test_load_token_success(self, auth_manager):
        """Test loading valid token."""
        auth_manager.save_token("test-token")
        
        loaded_token = auth_manager.load_token()
        assert loaded_token == "test-token"

    def test_load_token_nonexistent_file(self, auth_manager):
        """Test loading token when file doesn't exist."""
        loaded_token = auth_manager.load_token()
        assert loaded_token is None

    def test_load_token_corrupted_file(self, auth_manager):
        """Test loading token from corrupted file."""
        # Create corrupted token file
        with open(auth_manager.token_file, "w") as f:
            f.write("invalid json content")
        
        loaded_token = auth_manager.load_token()
        assert loaded_token is None
        assert not auth_manager.token_file.exists()  # Should be cleared

    def test_load_token_expired(self, auth_manager):
        """Test loading expired token."""
        # Create expired token
        expired_time = datetime.now() - timedelta(hours=1)
        token_data = {
            "token": "expired-token",
            "created_at": datetime.now().isoformat(),
            "expires_at": expired_time.isoformat()
        }
        
        with open(auth_manager.token_file, "w") as f:
            json.dump(token_data, f)
        
        loaded_token = auth_manager.load_token()
        assert loaded_token is None
        assert not auth_manager.token_file.exists()  # Should be cleared

    def test_load_token_valid_with_expiration(self, auth_manager):
        """Test loading valid token with future expiration."""
        # Create token that expires in 1 hour
        future_time = datetime.now() + timedelta(hours=1)
        token_data = {
            "token": "valid-token",
            "created_at": datetime.now().isoformat(),
            "expires_at": future_time.isoformat()
        }
        
        with open(auth_manager.token_file, "w") as f:
            json.dump(token_data, f)
        
        loaded_token = auth_manager.load_token()
        assert loaded_token == "valid-token"

    def test_clear_token(self, auth_manager):
        """Test clearing stored token."""
        auth_manager.save_token("test-token")
        assert auth_manager.token_file.exists()
        
        auth_manager.clear_token()
        assert not auth_manager.token_file.exists()
        assert auth_manager._token_data is None

    def test_clear_token_nonexistent_file(self, auth_manager):
        """Test clearing token when file doesn't exist."""
        # Should not raise an error
        auth_manager.clear_token()
        assert auth_manager._token_data is None

    def test_is_authenticated_true(self, auth_manager):
        """Test is_authenticated returns True for valid token."""
        auth_manager.save_token("test-token")
        assert auth_manager.is_authenticated() is True

    def test_is_authenticated_false_no_token(self, auth_manager):
        """Test is_authenticated returns False when no token."""
        assert auth_manager.is_authenticated() is False

    def test_is_authenticated_false_expired_token(self, auth_manager):
        """Test is_authenticated returns False for expired token."""
        # Create expired token
        expired_time = datetime.now() - timedelta(hours=1)
        token_data = {
            "token": "expired-token",
            "created_at": datetime.now().isoformat(),
            "expires_at": expired_time.isoformat()
        }
        
        with open(auth_manager.token_file, "w") as f:
            json.dump(token_data, f)
        
        assert auth_manager.is_authenticated() is False

    def test_get_auth_headers_authenticated(self, auth_manager):
        """Test getting auth headers when authenticated."""
        auth_manager.save_token("test-token")
        
        headers = auth_manager.get_auth_headers()
        assert headers == {"Authorization": "Bearer test-token"}

    def test_get_auth_headers_not_authenticated(self, auth_manager):
        """Test getting auth headers when not authenticated."""
        headers = auth_manager.get_auth_headers()
        assert headers == {}

    def test_is_token_expired_no_expiration(self, auth_manager):
        """Test token expiration check when no expiration is set."""
        auth_manager.save_token("test-token")
        assert auth_manager._is_token_expired() is False

    def test_is_token_expired_valid_token(self, auth_manager):
        """Test token expiration check for valid token."""
        auth_manager.save_token("test-token", expires_in=3600)
        assert auth_manager._is_token_expired() is False

    def test_is_token_expired_expired_token(self, auth_manager):
        """Test token expiration check for expired token."""
        # Manually set expired token data
        expired_time = datetime.now() - timedelta(hours=1)
        auth_manager._token_data = {
            "token": "expired-token",
            "expires_at": expired_time.isoformat()
        }
        assert auth_manager._is_token_expired() is True

    def test_is_token_expired_malformed_date(self, auth_manager):
        """Test token expiration check with malformed expiration date."""
        auth_manager._token_data = {
            "token": "test-token",
            "expires_at": "invalid-date-format"
        }
        assert auth_manager._is_token_expired() is True

    def test_is_token_expired_no_token_data(self, auth_manager):
        """Test token expiration check when no token data."""
        assert auth_manager._is_token_expired() is False

    def test_get_token_info_authenticated(self, auth_manager):
        """Test getting token info when authenticated."""
        auth_manager.save_token("test-token", expires_in=3600)
        
        info = auth_manager.get_token_info()
        assert info is not None
        assert info["authenticated"] is True
        assert "created_at" in info
        assert "expires_at" in info
        assert "expires_in_seconds" in info
        assert info["expires_in_seconds"] > 0

    def test_get_token_info_not_authenticated(self, auth_manager):
        """Test getting token info when not authenticated."""
        info = auth_manager.get_token_info()
        assert info is None

    def test_get_token_info_no_expiration(self, auth_manager):
        """Test getting token info for token without expiration."""
        auth_manager.save_token("test-token")
        
        info = auth_manager.get_token_info()
        assert info is not None
        assert info["authenticated"] is True
        assert "created_at" in info
        assert "expires_at" not in info
        assert "expires_in_seconds" not in info

    def test_get_token_info_malformed_expiration(self, auth_manager):
        """Test getting token info with malformed expiration date."""
        # Manually create token data with malformed expiration
        token_data = {
            "token": "test-token",
            "created_at": datetime.now().isoformat(),
            "expires_at": "invalid-date"
        }
        
        with open(auth_manager.token_file, "w") as f:
            json.dump(token_data, f)
        
        # With malformed expiration date, the token is considered expired and cleared
        info = auth_manager.get_token_info()
        assert info is None

    def test_token_persistence_across_instances(self):
        """Test that token persists across different AuthManager instances."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            
            # Create first instance and save token
            auth1 = AuthManager(config_dir)
            auth1.save_token("persistent-token")
            
            # Create second instance and verify token is loaded
            auth2 = AuthManager(config_dir)
            assert auth2.load_token() == "persistent-token"
            assert auth2.is_authenticated() is True

    def test_concurrent_token_operations(self, auth_manager):
        """Test concurrent token save and load operations."""
        # This test ensures thread safety isn't broken by basic operations
        auth_manager.save_token("token1")
        assert auth_manager.load_token() == "token1"
        
        auth_manager.save_token("token2")
        assert auth_manager.load_token() == "token2"
        
        auth_manager.clear_token()
        assert auth_manager.load_token() is None