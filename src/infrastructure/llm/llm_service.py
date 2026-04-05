"""LLM service implementation using LiteLLM."""

import json
import os
from typing import Any, Dict, List, Optional, Union

import litellm
from litellm import completion

from src.domain.exceptions import EntityExtractionError
from src.infrastructure.llm.config import LLMConfigLoader


class LLMService:
    """Service for interacting with LLMs through LiteLLM."""

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        temperature: float = None,
        max_tokens: int = None,
        config_loader: Optional[LLMConfigLoader] = None,
    ):
        """Initialize the LLM service.

        Args:
            model: The LLM model to use (defaults to config or env var LLM_MODEL)
            api_key: The API key for the LLM provider (defaults to env var based on model)
            temperature: The temperature for generation (defaults to model config)
            max_tokens: The maximum number of tokens to generate (defaults to model config)
            config_loader: Optional config loader instance
        """
        # Load configuration
        self._config_loader = config_loader or LLMConfigLoader()

        # Set model from args, env, or config
        self.model = model or self._config_loader.get_default_model()

        # Get model-specific configuration
        model_config = self._config_loader.get_model_config(self.model)

        # Set parameters with priority: args > env > config > default
        self.temperature = (
            temperature
            if temperature is not None
            else float(
                os.getenv(
                    "LLM_TEMPERATURE", model_config.get("default_temperature", 0.0)
                )
            )
        )
        self.max_tokens = (
            max_tokens
            if max_tokens is not None
            else int(os.getenv("LLM_MAX_TOKENS", model_config.get("max_tokens", 1024)))
        )
        
        # Ensure max_tokens doesn't exceed safe limits for the model
        if self.max_tokens > 4000:  # Leave room for input tokens
            self.max_tokens = 1024

        # Set API key if provided, otherwise LiteLLM will use environment variables
        if api_key:
            if "openai" in self.model or "gpt" in self.model:
                os.environ["OPENAI_API_KEY"] = api_key
            elif "claude" in self.model:
                os.environ["ANTHROPIC_API_KEY"] = api_key
            elif "deepseek" in self.model:
                os.environ["DEEPSEEK_API_KEY"] = api_key

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        json_mode: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Dict[str, Any]]:
        """Generate text from the LLM.

        Args:
            prompt: The user prompt to send to the LLM
            system_prompt: Optional system prompt for context
            json_mode: Whether to request JSON output
            json_schema: Optional JSON schema for structured output

        Returns:
            The generated text or parsed JSON object

        Raises:
            EntityExtractionError: If the LLM call fails or JSON parsing fails
        """
        messages = []

        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        # Add user prompt
        messages.append({"role": "user", "content": prompt})

        try:
            # Configure response format for JSON if requested
            response_format = None
            if json_mode:
                response_format = {"type": "json_object"}
                if json_schema:
                    # Some models support json_schema, but not all
                    # We'll include it for those that do
                    response_format["schema"] = json_schema

            # Make the API call
            call_params = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
            
            # Only add response_format for models that support it
            if json_mode and response_format:
                # Check if model supports structured output
                if "gpt-4o" in self.model or "gpt-3.5-turbo" in self.model:
                    call_params["response_format"] = response_format
                else:
                    # For older models, add JSON instruction to the system message
                    if messages and messages[0]["role"] == "system":
                        messages[0]["content"] += "\n\nPlease respond with valid JSON only."
                    else:
                        messages.insert(0, {"role": "system", "content": "Please respond with valid JSON only."})
            
            response = await completion(**call_params)

            # Extract the content from the response
            content = response.choices[0].message.content

            # Parse JSON if requested
            if json_mode:
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    raise EntityExtractionError(
                        f"Failed to parse JSON from LLM response: {str(e)}"
                    )

            return content

        except Exception as e:
            raise EntityExtractionError(f"LLM API call failed: {str(e)}")
