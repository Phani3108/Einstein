"""Tests for configuration management."""

import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch
from pydantic import ValidationError

from einstein_cli.config import ConfigManager, CLIConfig


def test_config_manager_initialization():
    """Test ConfigManager initialization with default values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        assert config_manager.config_path == config_path
        assert isinstance(config_manager.config, CLIConfig)
        assert config_manager.config.api.url == "http://localhost:8001"


def test_config_get_set():
    """Test getting and setting configuration values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        # Test setting and getting a value
        config_manager.set("api.url", "http://example.com:8080")
        assert config_manager.get("api.url") == "http://example.com:8080"

        # Test getting non-existent key with default
        assert config_manager.get("nonexistent.key", "default") == "default"


def test_config_persistence():
    """Test that configuration persists across instances."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"

        # Create first instance and set a value
        config1 = ConfigManager(str(config_path))
        config1.set("api.url", "http://persistent.com")

        # Create second instance and verify value persists
        config2 = ConfigManager(str(config_path))
        assert config2.get("api.url") == "http://persistent.com"


def test_config_reset():
    """Test configuration reset functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        # Change a value
        config_manager.set("api.url", "http://changed.com")
        assert config_manager.get("api.url") == "http://changed.com"

        # Reset and verify default is restored
        config_manager.reset()
        assert config_manager.get("api.url") == "http://localhost:8001"


def test_config_show():
    """Test showing all configuration values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        all_config = config_manager.show()
        assert isinstance(all_config, dict)
        assert "api" in all_config
        assert "auth" in all_config
        assert "output" in all_config
        assert "cache" in all_config


def test_platform_specific_config_paths():
    """Test platform-specific configuration paths."""
    config_manager = ConfigManager()

    # Test that we get a valid path
    config_path = config_manager.get_config_path()
    assert isinstance(config_path, Path)
    assert config_path.name == "config.toml"
    assert "einstein" in str(config_path)


@patch("sys.platform", "win32")
def test_windows_config_path():
    """Test Windows-specific configuration path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch.dict("os.environ", {"APPDATA": temp_dir}):
            config_manager = ConfigManager()
            config_path = config_manager.get_config_path()
            assert config_path.name == "config.toml"
            assert "einstein" in str(config_path)
            assert temp_dir in str(config_path)


@patch("sys.platform", "darwin")
def test_macos_config_path():
    """Test macOS-specific configuration path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(temp_dir)
            config_manager = ConfigManager()
            config_path = config_manager.get_config_path()
            assert config_path.name == "config.toml"
            assert "einstein" in str(config_path)
            assert "Library/Application Support" in str(config_path)


@patch("sys.platform", "linux")
def test_linux_config_path():
    """Test Linux-specific configuration path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = Path(temp_dir)
            config_manager = ConfigManager()
            config_path = config_manager.get_config_path()
            assert config_path.name == "config.toml"
            assert "einstein" in str(config_path)
            assert ".config" in str(config_path)


def test_config_validation_error():
    """Test handling of invalid configuration values."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        # Test setting invalid value
        with pytest.raises(ValueError):
            config_manager.set("api.timeout", "not_a_number")

        # Test setting empty key
        with pytest.raises(ValueError):
            config_manager.set("", "value")

        # Test setting key with empty parts
        with pytest.raises(ValueError):
            config_manager.set("api..url", "value")


def test_config_nested_key_error():
    """Test error when trying to set nested key on non-dict value."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        # First set a string value
        config_manager.set("api.url", "http://example.com")

        # Try to set a nested key on the string value
        with pytest.raises(ValueError, match="is not a configuration section"):
            config_manager.set("api.url.port", "8080")


def test_config_file_corruption_handling():
    """Test handling of corrupted configuration files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"

        # Create a corrupted TOML file
        with open(config_path, "w") as f:
            f.write("invalid toml content [[[")

        # Should handle corruption gracefully and create default config
        config_manager = ConfigManager(str(config_path))
        assert config_manager.get("api.url") == "http://localhost:8001"


def test_config_path_method():
    """Test getting configuration file path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "test_config.toml"
        config_manager = ConfigManager(str(config_path))

        assert config_manager.get_config_path() == config_path
