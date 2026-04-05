#!/usr/bin/env python
"""Standalone test for LLM service without application context."""

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

# Add the current directory to the Python path
sys.path.insert(0, os.path.abspath("."))

# Import the LLM service
from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import ThoughtMetadata
from src.domain.exceptions import EntityExtractionError
from src.infrastructure.llm.config import LLMConfigLoader
from src.infrastructure.llm.entity_extraction_service import LLMEntityExtractionService
from src.infrastructure.llm.llm_service import LLMService


async def test_llm_service():
    """Test the LLM service."""
    # Create a mock config loader
    mock_config_loader = MagicMock(spec=LLMConfigLoader)
    mock_config_loader.get_default_model.return_value = "gpt-4"
    mock_config_loader.get_model_config.return_value = {
        "max_tokens": 4096,
        "default_temperature": 0.0,
    }

    # Create the LLM service
    llm_service = LLMService(config_loader=mock_config_loader)

    # Mock the completion function
    with patch("src.infrastructure.llm.llm_service.completion") as mock_completion:
        # Set up the mock response
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Generated text"
        mock_completion.return_value = asyncio.Future()
        mock_completion.return_value.set_result(mock_response)

        # Test generating text
        result = await llm_service.generate("Test prompt")

        # Check the result
        assert result == "Generated text"
        mock_completion.assert_called_once()

        print("✅ LLM service test passed")


async def test_entity_extraction_service():
    """Test the entity extraction service."""
    # Create a mock LLM service
    mock_llm_service = AsyncMock(spec=LLMService)

    # Create a temporary directory for prompts
    import shutil
    import tempfile
    from pathlib import Path

    temp_dir = tempfile.mkdtemp()
    try:
        # Create prompt files
        prompts_dir = Path(temp_dir) / "prompts"
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

        # Create the entity extraction service
        entity_extraction_service = LLMEntityExtractionService(
            mock_llm_service, str(prompts_dir)
        )

        # Set up the mock response
        mock_llm_service.generate.return_value = {
            "entities": [
                {
                    "id": "1",
                    "type": "PERSON",
                    "value": "John",
                    "confidence": 0.95,
                    "context": "John met Sarah",
                }
            ]
        }

        # Test extracting entities
        thought_id = uuid.uuid4()
        result = await entity_extraction_service.extract_entities(
            "John met Sarah", thought_id
        )

        # Check the result
        assert len(result) == 1
        assert result[0].entity_type == EntityType.PERSON
        assert result[0].entity_value == "John"
        assert result[0].thought_id == thought_id

        print("✅ Entity extraction service test passed")

    finally:
        # Clean up the temporary directory
        shutil.rmtree(temp_dir)


async def run_tests():
    """Run all tests."""
    await test_llm_service()
    await test_entity_extraction_service()


if __name__ == "__main__":
    asyncio.run(run_tests())
    print("All tests passed!")
