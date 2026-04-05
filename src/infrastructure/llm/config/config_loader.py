"""Configuration loader for LLM settings."""

import json
import os
from typing import Dict, Optional


class LLMConfigLoader:
    """Loader for LLM configuration settings."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader.

        Args:
            config_path: Path to the LLM config file (defaults to llm_config.json in the same directory)
        """
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "llm_config.json")

        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load the configuration from file.

        Returns:
            The configuration as a dictionary
        """
        try:
            with open(self.config_path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Return default config if file doesn't exist or is invalid
            return {
                "providers": {
                    "openai": {
                        "models": {
                            "gpt-4": {
                                "description": "OpenAI GPT-4 model",
                                "max_tokens": 2048,
                                "default_temperature": 0.0,
                            },
                            "gpt-4o-mini": {
                                "description": "OpenAI GPT-4o Mini model",
                                "max_tokens": 2048,
                                "default_temperature": 0.0,
                            }
                        }
                    }
                },
                "default_provider": "openai",
                "default_model": "gpt-4o-mini",
            }

    def get_default_model(self) -> str:
        """Get the default model from config or environment.

        Returns:
            The default model name
        """
        return os.getenv("LLM_MODEL", self.config.get("default_model", "gpt-4o-mini"))

    def get_model_config(self, model_name: str) -> Dict:
        """Get configuration for a specific model.

        Args:
            model_name: The name of the model

        Returns:
            The model configuration
        """
        # Determine provider from model name
        provider = None
        for provider_name, provider_config in self.config.get("providers", {}).items():
            if model_name in provider_config.get("models", {}):
                provider = provider_name
                break

        if not provider:
            # Return default config if model not found
            return {"max_tokens": 2048, "default_temperature": 0.0}

        return self.config["providers"][provider]["models"][model_name]
