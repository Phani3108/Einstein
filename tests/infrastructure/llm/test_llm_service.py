"""Unit tests for the LLM service."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.exceptions import EntityExtractionError
from src.infrastructure.llm.config import LLMConfigLoader
from src.infrastructure.llm.llm_service import LLMService


@pytest.fixture
def mock_config_loader():
    """Create a mock config loader."""
    mock = MagicMock(spec=LLMConfigLoader)
    mock.get_default_model.return_value = "gpt-4"
    mock.get_model_config.return_value = {
        "max_tokens": 4096,
        "default_temperature": 0.0,
    }
    return mock


@pytest.fixture
def llm_service(mock_config_loader):
    """Create an LLM service with a mock config loader."""
    return LLMService(config_loader=mock_config_loader)


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_text(mock_completion, llm_service):
    """Test generating text from the LLM."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Generated text"
    mock_completion.return_value = mock_response

    # Act
    result = await llm_service.generate("Test prompt")

    # Assert
    assert result == "Generated text"
    mock_completion.assert_called_once_with(
        model="gpt-4",
        messages=[{"role": "user", "content": "Test prompt"}],
        temperature=0.0,
        max_tokens=4096,
        response_format=None,
    )


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_with_system_prompt(mock_completion, llm_service):
    """Test generating text with a system prompt."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Generated text"
    mock_completion.return_value = mock_response

    # Act
    result = await llm_service.generate(
        "Test prompt", system_prompt="System instructions"
    )

    # Assert
    assert result == "Generated text"
    mock_completion.assert_called_once_with(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "System instructions"},
            {"role": "user", "content": "Test prompt"},
        ],
        temperature=0.0,
        max_tokens=4096,
        response_format=None,
    )


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_json(mock_completion, llm_service):
    """Test generating JSON from the LLM."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"key": "value"}'
    mock_completion.return_value = mock_response

    # Act
    result = await llm_service.generate("Test prompt", json_mode=True)

    # Assert
    assert result == {"key": "value"}
    mock_completion.assert_called_once_with(
        model="gpt-4",
        messages=[{"role": "user", "content": "Test prompt"}],
        temperature=0.0,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_json_with_schema(mock_completion, llm_service):
    """Test generating JSON with a schema."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = '{"key": "value"}'
    mock_completion.return_value = mock_response

    schema = {"type": "object", "properties": {"key": {"type": "string"}}}

    # Act
    result = await llm_service.generate(
        "Test prompt", json_mode=True, json_schema=schema
    )

    # Assert
    assert result == {"key": "value"}
    mock_completion.assert_called_once_with(
        model="gpt-4",
        messages=[{"role": "user", "content": "Test prompt"}],
        temperature=0.0,
        max_tokens=4096,
        response_format={"type": "json_object", "schema": schema},
    )


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_json_invalid_response(mock_completion, llm_service):
    """Test handling invalid JSON response."""
    # Arrange
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Invalid JSON"
    mock_completion.return_value = mock_response

    # Act & Assert
    with pytest.raises(EntityExtractionError):
        await llm_service.generate("Test prompt", json_mode=True)


@pytest.mark.asyncio
@patch("src.infrastructure.llm.llm_service.completion")
async def test_generate_api_error(mock_completion, llm_service):
    """Test handling API errors."""
    # Arrange
    mock_completion.side_effect = Exception("API error")

    # Act & Assert
    with pytest.raises(EntityExtractionError):
        await llm_service.generate("Test prompt")
