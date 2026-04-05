"""Configuration management for Einstein CLI."""

import os
import sys
import toml
from pathlib import Path
from typing import Any, Optional, Dict
from pydantic import BaseModel, ValidationError


class CLIConfig(BaseModel):
    """Configuration model for CLI settings."""

    class APIConfig(BaseModel):
        url: str = "http://localhost:8001"
        timeout: int = 30

    class AuthConfig(BaseModel):
        auto_login: bool = True
        remember_token: bool = True

    class OutputConfig(BaseModel):
        colors: bool = True
        pager: str = "auto"
        max_results: int = 20

    class CacheConfig(BaseModel):
        enabled: bool = True
        max_size_mb: int = 100
        sync_interval: int = 300

    api: APIConfig = APIConfig()
    auth: AuthConfig = AuthConfig()
    output: OutputConfig = OutputConfig()
    cache: CacheConfig = CacheConfig()


class ConfigManager:
    """Manages CLI configuration using TOML files."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_path: Optional path to config file. If None, uses default location.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Platform-specific default config location
            self.config_path = self._get_default_config_path()

        self.config_dir = self.config_path.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self._config_data = self._load_config()
        self.config = CLIConfig(**self._config_data)

    def _get_default_config_path(self) -> Path:
        """Get platform-specific default configuration path.

        Returns:
            Path to default configuration file
        """
        if sys.platform == "win32":
            # Windows: %APPDATA%/einstein/config.toml
            config_dir = Path(
                os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
            )
            return config_dir / "einstein" / "config.toml"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/einstein/config.toml
            return (
                Path.home()
                / "Library"
                / "Application Support"
                / "einstein"
                / "config.toml"
            )
        else:
            # Linux/Unix: ~/.config/einstein/config.toml (XDG Base Directory)
            xdg_config_home = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
            return Path(xdg_config_home) / "einstein" / "config.toml"

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config_data = toml.load(f)

                # Validate loaded configuration
                try:
                    CLIConfig(**config_data)
                    return config_data
                except ValidationError as e:
                    print(
                        f"Warning: Invalid configuration file, using defaults. Validation errors: {e}"
                    )
                    return self._create_default_config()

            except (toml.TomlDecodeError, OSError) as e:
                # If config is corrupted or unreadable, create new one
                print(f"Warning: Could not load config file: {e}")
                return self._create_default_config()
        else:
            # Create default config
            return self._create_default_config()

    def _create_default_config(self) -> Dict[str, Any]:
        """Create and save default configuration.

        Returns:
            Default configuration dictionary
        """
        default_config = CLIConfig()
        config_data = default_config.model_dump()
        self._save_config(config_data)
        return config_data

    def _save_config(self, config_data: Dict[str, Any]) -> None:
        """Save configuration to file.

        Args:
            config_data: Configuration dictionary to save

        Raises:
            OSError: If file cannot be written
            ValidationError: If configuration data is invalid
        """
        # Validate configuration before saving
        CLIConfig(**config_data)

        # Ensure directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Write configuration file
        with open(self.config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'api.url')
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split(".")
        value = self._config_data

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'api.url')
            value: Value to set

        Raises:
            ValueError: If key is invalid or value doesn't validate
            ValidationError: If resulting configuration is invalid
        """
        if not key or not key.strip():
            raise ValueError("Configuration key cannot be empty")

        keys = key.split(".")
        if not all(k.strip() for k in keys):
            raise ValueError("Configuration key parts cannot be empty")

        # Create a deep copy of current config
        config_data = self._deep_copy_dict(self._config_data)

        # Navigate to the parent of the target key
        current = config_data
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            elif not isinstance(current[k], dict):
                raise ValueError(
                    f"Cannot set nested key '{key}': '{k}' is not a configuration section"
                )
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Validate the new configuration
        try:
            new_config = CLIConfig(**config_data)
        except ValidationError as e:
            raise ValueError(f"Invalid configuration value for '{key}': {e}")

        # Update internal state and save
        self._config_data = config_data
        self.config = new_config
        self._save_config(config_data)

    def _deep_copy_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Create a deep copy of a dictionary.

        Args:
            d: Dictionary to copy

        Returns:
            Deep copy of the dictionary
        """
        result = {}
        for key, value in d.items():
            if isinstance(value, dict):
                result[key] = self._deep_copy_dict(value)
            else:
                result[key] = value
        return result

    def show(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config_data.copy()

    def reset(self) -> None:
        """Reset configuration to defaults."""
        default_config = CLIConfig()
        self._config_data = default_config.model_dump()
        self.config = default_config
        self._save_config(self._config_data)

    def get_config_path(self) -> Path:
        """Get the path to the configuration file.

        Returns:
            Path to the configuration file
        """
        return self.config_path
