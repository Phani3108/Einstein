"""Integration tests for vector storage infrastructure.

These tests verify that the embedding service and vector store service
work together correctly for semantic search functionality.
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.enums import EntityType
from src.domain.services.vector_store_service import VectorSearchResult
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.infrastructure.services.vector_store_service import PineconeVectorStore


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock = AsyncMock()
    mock.embeddings.create = AsyncMock()
    return mock


@pytest.fixture
def mock_pinecone_index():
    """Create a mock Pinecone index."""
    mock = MagicMock()
    mock.upsert = MagicMock()
    mock.query = MagicMock()
    mock.delete = MagicMock()
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


@pytest.fixture
def vector_store(mock_pinecone_index):
    """Create a vector store with mocked Pinecone functions."""
    with patch("src.infrastructure.services.vector_store_service.pinecone.init"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index",
        return_value=mock_pinecone_index,
    ):
        store = PineconeVectorStore(
            api_key="test_key",
            environment="test-env",
            index_name="semantic-engine",
            namespace="test-namespace",
        )
        store.index = mock_pinecone_index
        return store


@pytest.mark.asyncio
async def test_index_and_search_thought(embedding_service, vector_store):
    """Test the full flow of embedding generation and vector storage/search."""
    # Arrange
    thought_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    content = "I met John at the coffee shop yesterday."

    # Mock embedding generation
    mock_embedding = [0.1, 0.2, 0.3, 0.4]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=mock_embedding)]
    embedding_service.client.embeddings.create.return_value = mock_response

    # Mock vector search results
    mock_match = MagicMock()
    mock_match.id = thought_id
    mock_match.score = 0.95
    mock_match.metadata = {
        "entity_type": "PERSON",
        "entity_value": "John",
        "user_id": user_id,
    }

    mock_search_response = MagicMock()
    mock_search_response.matches = [mock_match]
    vector_store.index.query.return_value = mock_search_response

    # Act - Generate embedding
    embedding = await embedding_service.generate_embedding(content)

    # Act - Store vector
    metadata = {
        "entity_type": "PERSON",
        "entity_value": "John",
        "user_id": user_id,
        "thought_id": thought_id,
    }
    await vector_store.store_vector(thought_id, embedding, metadata)

    # Act - Search for similar vectors
    search_embedding = await embedding_service.generate_embedding(
        "Who did I meet yesterday?"
    )
    search_results = await vector_store.search(
        query_vector=search_embedding,
        top_k=5,
        entity_type=EntityType.PERSON,
        user_id=uuid.UUID(user_id),
    )

    # Assert
    assert embedding == mock_embedding

    # Verify vector was stored correctly
    vector_store.index.upsert.assert_called_once()
    upsert_call = vector_store.index.upsert.call_args
    assert upsert_call[1]["vectors"][0]["id"] == thought_id
    assert upsert_call[1]["vectors"][0]["values"] == mock_embedding
    assert upsert_call[1]["vectors"][0]["metadata"] == metadata

    # Verify search was performed correctly
    assert len(search_results) == 1
    assert search_results[0].id == thought_id
    assert search_results[0].score == 0.95
    assert search_results[0].metadata["entity_value"] == "John"

    # Verify search filters were applied
    vector_store.index.query.assert_called_once()
    query_call = vector_store.index.query.call_args
    assert query_call[1]["filter"] == {"entity_type": "PERSON", "user_id": user_id}


@pytest.mark.asyncio
async def test_batch_indexing_and_search(embedding_service, vector_store):
    """Test batch indexing of multiple texts and searching."""
    # Arrange
    user_id = str(uuid.uuid4())
    texts = [
        "I visited Paris last summer.",
        "The conference in New York was great.",
        "I enjoyed the concert at the Opera House.",
    ]

    # Mock batch embedding generation
    mock_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]]
    mock_data = [
        MagicMock(embedding=mock_embeddings[0], index=0),
        MagicMock(embedding=mock_embeddings[1], index=1),
        MagicMock(embedding=mock_embeddings[2], index=2),
    ]
    mock_response = MagicMock()
    mock_response.data = mock_data
    embedding_service.client.embeddings.create.return_value = mock_response

    # Mock search response
    mock_match = MagicMock()
    mock_match.id = "location-1"
    mock_match.score = 0.92
    mock_match.metadata = {
        "entity_type": "LOCATION",
        "entity_value": "Paris",
        "user_id": user_id,
    }

    mock_search_response = MagicMock()
    mock_search_response.matches = [mock_match]
    vector_store.index.query.return_value = mock_search_response

    # Act - Generate embeddings
    embeddings = await embedding_service.generate_embeddings(texts)

    # Act - Store vectors
    for i, embedding in enumerate(embeddings):
        entity_id = f"location-{i}"
        metadata = {
            "entity_type": "LOCATION",
            "entity_value": f"Location {i}",
            "user_id": user_id,
        }
        await vector_store.store_vector(entity_id, embedding, metadata)

    # Act - Search for similar vectors
    search_embedding = await embedding_service.generate_embedding(
        "Where did I go in Europe?"
    )
    search_results = await vector_store.search(
        query_vector=search_embedding, top_k=5, entity_type=EntityType.LOCATION
    )

    # Assert
    assert len(embeddings) == 3
    assert embeddings[0] == mock_embeddings[0]
    assert embeddings[1] == mock_embeddings[1]
    assert embeddings[2] == mock_embeddings[2]

    # Verify vectors were stored correctly
    assert vector_store.index.upsert.call_count == 3

    # Verify search was performed correctly
    assert len(search_results) == 1
    assert search_results[0].id == "location-1"
    assert search_results[0].score == 0.92
    assert search_results[0].metadata["entity_value"] == "Paris"
