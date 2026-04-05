"""Unit tests for the OpenAI embedding service."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.exceptions import EmbeddingError
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock = AsyncMock()
    mock.embeddings.create = AsyncMock()
    return mock


@pytest.fixture
def embedding_service(mock_openai_client):
    """Create an embedding service with a mock OpenAI client."""
    with patch(
        "src.infrastructure.services.embedding_service.AsyncOpenAI",
        return_value=mock_openai_client,
    ):
        service = OpenAIEmbeddingService(api_key="test_key")
        service.client = mock_openai_client
        return service


@pytest.mark.asyncio
async def test_generate_embedding(embedding_service, mock_openai_client):
    """Test generating a single embedding."""
    # Arrange
    text = "This is a test text"
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    mock_openai_client.embeddings.create.return_value = mock_response

    # Act
    result = await embedding_service.generate_embedding(text)

    # Assert
    assert result == [0.1, 0.2, 0.3]
    mock_openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-ada-002",
        input=text,
    )


@pytest.mark.asyncio
async def test_generate_embedding_empty_text(embedding_service):
    """Test generating an embedding with empty text."""
    # Act & Assert
    with pytest.raises(
        EmbeddingError, match="Cannot generate embedding for empty text"
    ):
        await embedding_service.generate_embedding("")


@pytest.mark.asyncio
async def test_generate_embedding_api_error(embedding_service, mock_openai_client):
    """Test handling API errors when generating embeddings."""
    # Arrange
    text = "This is a test text"
    mock_openai_client.embeddings.create.side_effect = Exception("API error")

    # Act & Assert
    with pytest.raises(EmbeddingError, match="Failed to generate embedding: API error"):
        await embedding_service.generate_embedding(text)


@pytest.mark.asyncio
async def test_generate_embeddings(embedding_service, mock_openai_client):
    """Test generating multiple embeddings."""
    # Arrange
    texts = ["Text 1", "Text 2", "Text 3"]

    mock_data = [
        MagicMock(embedding=[0.1, 0.2, 0.3], index=0),
        MagicMock(embedding=[0.4, 0.5, 0.6], index=1),
        MagicMock(embedding=[0.7, 0.8, 0.9], index=2),
    ]
    mock_response = MagicMock()
    mock_response.data = mock_data
    mock_openai_client.embeddings.create.return_value = mock_response

    # Act
    result = await embedding_service.generate_embeddings(texts)

    # Assert
    assert len(result) == 3
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.4, 0.5, 0.6]
    assert result[2] == [0.7, 0.8, 0.9]
    mock_openai_client.embeddings.create.assert_called_once_with(
        model="text-embedding-ada-002",
        input=texts,
    )


@pytest.mark.asyncio
async def test_generate_embeddings_empty_list(embedding_service, mock_openai_client):
    """Test generating embeddings with an empty list."""
    # Act
    result = await embedding_service.generate_embeddings([])

    # Assert
    assert result == []
    mock_openai_client.embeddings.create.assert_not_called()


@pytest.mark.asyncio
async def test_generate_embeddings_all_empty_texts(embedding_service):
    """Test generating embeddings with all empty texts."""
    # Act & Assert
    with pytest.raises(
        EmbeddingError, match="Cannot generate embeddings for empty texts"
    ):
        await embedding_service.generate_embeddings(["", "  ", ""])


@pytest.mark.asyncio
async def test_generate_embeddings_batch_processing(
    embedding_service, mock_openai_client
):
    """Test batch processing for generating embeddings."""
    # Arrange
    texts = [f"Text {i}" for i in range(150)]  # More than the default batch size of 100

    # Create mock responses for each batch
    batch1_data = [MagicMock(embedding=[0.1, 0.2], index=i) for i in range(100)]
    batch2_data = [MagicMock(embedding=[0.3, 0.4], index=i) for i in range(50)]

    batch1_response = MagicMock()
    batch1_response.data = batch1_data

    batch2_response = MagicMock()
    batch2_response.data = batch2_data

    mock_openai_client.embeddings.create.side_effect = [
        batch1_response,
        batch2_response,
    ]

    # Act
    result = await embedding_service.generate_embeddings(texts)

    # Assert
    assert len(result) == 150
    assert mock_openai_client.embeddings.create.call_count == 2

    # First call should have 100 texts
    first_call_args = mock_openai_client.embeddings.create.call_args_list[0]
    assert len(first_call_args[1]["input"]) == 100

    # Second call should have 50 texts
    second_call_args = mock_openai_client.embeddings.create.call_args_list[1]
    assert len(second_call_args[1]["input"]) == 50
