"""Unit tests for the LLM-based entity extraction service."""

import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import ThoughtMetadata
from src.domain.exceptions import EntityExtractionError
from src.infrastructure.llm.entity_extraction_service import LLMEntityExtractionService
from src.infrastructure.llm.llm_service import LLMService


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    mock = AsyncMock(spec=LLMService)
    return mock


@pytest.fixture
def entity_extraction_service(mock_llm_service, tmp_path):
    """Create an entity extraction service with a mock LLM service and temp prompts directory."""
    # Create temporary prompts directory
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()

    # Create system prompt file
    system_prompt_file = prompts_dir / "entity_extraction_system.txt"
    system_prompt_file.write_text("System prompt")

    # Create extraction prompt file
    extraction_prompt_file = prompts_dir / "entity_extraction.txt"
    extraction_prompt_file.write_text(
        "Extract entities from: {CONTENT}\nMetadata: {METADATA}"
    )

    # Create schema file
    schema_file = prompts_dir / "entity_extraction_schema.json"
    schema_file.write_text(
        '{"type": "object", "properties": {"entities": {"type": "array"}}}'
    )

    return LLMEntityExtractionService(mock_llm_service, str(prompts_dir))


@pytest.mark.asyncio
async def test_extract_entities(mock_llm_service, entity_extraction_service):
    """Test extracting entities from text."""
    # Arrange
    thought_id = uuid.uuid4()
    content = "John met Sarah in New York yesterday."

    # Mock LLM response
    mock_llm_service.generate.return_value = {
        "entities": [
            {
                "id": "1",
                "type": "PERSON",
                "value": "John",
                "confidence": 0.95,
                "context": "John met Sarah",
                "relationships": [
                    {"target_id": "2", "type": "met_with", "strength": 0.9}
                ],
            },
            {
                "id": "2",
                "type": "PERSON",
                "value": "Sarah",
                "confidence": 0.95,
                "context": "John met Sarah",
                "relationships": [],
            },
            {
                "id": "3",
                "type": "LOCATION",
                "value": "New York",
                "confidence": 0.98,
                "context": "in New York",
                "relationships": [],
            },
            {
                "id": "4",
                "type": "DATE",
                "value": "yesterday",
                "confidence": 0.9,
                "context": "New York yesterday",
                "relationships": [],
            },
        ]
    }

    # Act
    result = await entity_extraction_service.extract_entities(content, thought_id)

    # Assert
    assert len(result) == 4
    assert all(isinstance(entry, SemanticEntry) for entry in result)
    assert all(entry.thought_id == thought_id for entry in result)

    # Check entity types
    entity_types = [entry.entity_type for entry in result]
    assert EntityType.PERSON in entity_types
    assert EntityType.LOCATION in entity_types
    assert EntityType.DATE in entity_types

    # Check entity values
    entity_values = [entry.entity_value for entry in result]
    assert "John" in entity_values
    assert "Sarah" in entity_values
    assert "New York" in entity_values
    assert "yesterday" in entity_values

    # Check relationships
    john_entry = next(entry for entry in result if entry.entity_value == "John")
    assert len(john_entry.relationships) == 1

    # Verify LLM service was called correctly
    mock_llm_service.generate.assert_called_once()
    call_args = mock_llm_service.generate.call_args
    assert call_args[1]["system_prompt"] == "System prompt"
    assert "{CONTENT}" not in call_args[1]["prompt"]
    assert content in call_args[1]["prompt"]
    assert call_args[1]["json_mode"] is True


@pytest.mark.asyncio
async def test_extract_entities_with_metadata(
    mock_llm_service, entity_extraction_service
):
    """Test extracting entities with metadata."""
    # Arrange
    thought_id = uuid.uuid4()
    content = "I felt happy during my vacation."
    metadata = ThoughtMetadata(mood="happy", tags=["vacation", "personal"])

    # Mock LLM response
    mock_llm_service.generate.return_value = {
        "entities": [
            {
                "id": "1",
                "type": "EMOTION",
                "value": "happy",
                "confidence": 0.95,
                "context": "felt happy",
            }
        ]
    }

    # Act
    result = await entity_extraction_service.extract_entities(
        content, thought_id, metadata
    )

    # Assert
    assert len(result) == 1
    assert result[0].entity_type == EntityType.EMOTION
    assert result[0].entity_value == "happy"

    # Verify metadata was included in prompt
    call_args = mock_llm_service.generate.call_args
    assert "mood" in call_args[1]["prompt"]
    assert "happy" in call_args[1]["prompt"]
    assert "vacation" in call_args[1]["prompt"]


@pytest.mark.asyncio
async def test_extract_entities_llm_error(mock_llm_service, entity_extraction_service):
    """Test handling LLM errors during extraction."""
    # Arrange
    thought_id = uuid.uuid4()
    content = "Test content"
    mock_llm_service.generate.side_effect = EntityExtractionError("LLM error")

    # Act & Assert
    with pytest.raises(EntityExtractionError):
        await entity_extraction_service.extract_entities(content, thought_id)


@pytest.mark.asyncio
async def test_extract_entities_invalid_response(
    mock_llm_service, entity_extraction_service
):
    """Test handling invalid LLM responses."""
    # Arrange
    thought_id = uuid.uuid4()
    content = "Test content"
    mock_llm_service.generate.return_value = {"invalid": "response"}

    # Act
    result = await entity_extraction_service.extract_entities(content, thought_id)

    # Assert
    assert len(result) == 0


@pytest.mark.asyncio
async def test_extract_entities_invalid_entity_type(
    mock_llm_service, entity_extraction_service
):
    """Test handling invalid entity types in LLM responses."""
    # Arrange
    thought_id = uuid.uuid4()
    content = "Test content"
    mock_llm_service.generate.return_value = {
        "entities": [
            {"id": "1", "type": "INVALID_TYPE", "value": "Test value"},
            {"id": "2", "type": "PERSON", "value": "John"},
        ]
    }

    # Act
    result = await entity_extraction_service.extract_entities(content, thought_id)

    # Assert
    assert len(result) == 1
    assert result[0].entity_type == EntityType.PERSON
    assert result[0].entity_value == "John"
