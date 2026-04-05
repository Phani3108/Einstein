"""Unit tests for the Pinecone vector store service."""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.entities.enums import EntityType
from src.domain.exceptions import VectorStoreError
from src.domain.services.vector_store_service import VectorSearchResult
from src.infrastructure.services.vector_store_service import PineconeVectorStore


@pytest.fixture
def mock_pinecone_index():
    """Create a mock Pinecone index."""
    mock = MagicMock()
    mock.upsert = MagicMock()
    mock.query = MagicMock()
    mock.delete = MagicMock()
    return mock


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
async def test_store_vector(vector_store, mock_pinecone_index):
    """Test storing a vector in the vector store."""
    # Arrange
    vector_id = str(uuid.uuid4())
    vector = [0.1, 0.2, 0.3, 0.4]
    metadata = {"entity_type": "PERSON", "user_id": str(uuid.uuid4())}

    # Act
    await vector_store.store_vector(vector_id, vector, metadata)

    # Assert
    vector_store.index.upsert.assert_called_once_with(
        vectors=[{"id": vector_id, "values": vector, "metadata": metadata}],
        namespace="test-namespace",
    )


@pytest.mark.asyncio
async def test_store_vector_error(vector_store, mock_pinecone_index):
    """Test handling errors when storing vectors."""
    # Arrange
    vector_id = str(uuid.uuid4())
    vector = [0.1, 0.2, 0.3, 0.4]
    metadata = {"entity_type": "PERSON", "user_id": str(uuid.uuid4())}
    vector_store.index.upsert.side_effect = Exception("Storage error")

    # Act & Assert
    with pytest.raises(VectorStoreError, match="Failed to store vector: Storage error"):
        await vector_store.store_vector(vector_id, vector, metadata)


@pytest.mark.asyncio
async def test_search(vector_store, mock_pinecone_index):
    """Test searching for similar vectors."""
    # Arrange
    query_vector = [0.1, 0.2, 0.3, 0.4]

    # Mock search results
    mock_match1 = MagicMock()
    mock_match1.id = "id1"
    mock_match1.score = 0.95
    mock_match1.metadata = {"entity_type": "PERSON", "value": "John Doe"}

    mock_match2 = MagicMock()
    mock_match2.id = "id2"
    mock_match2.score = 0.85
    mock_match2.metadata = {"entity_type": "ORGANIZATION", "value": "Acme Corp"}

    mock_response = MagicMock()
    mock_response.matches = [mock_match1, mock_match2]

    vector_store.index.query.return_value = mock_response

    # Act
    results = await vector_store.search(query_vector, top_k=2)

    # Assert
    assert len(results) == 2
    assert isinstance(results[0], VectorSearchResult)
    assert results[0].id == "id1"
    assert results[0].score == 0.95
    assert results[0].metadata == {"entity_type": "PERSON", "value": "John Doe"}

    assert results[1].id == "id2"
    assert results[1].score == 0.85

    vector_store.index.query.assert_called_once_with(
        vector=query_vector,
        top_k=2,
        namespace="test-namespace",
        filter=None,
        include_metadata=True,
    )


@pytest.mark.asyncio
async def test_search_with_filters(vector_store, mock_pinecone_index):
    """Test searching with entity type and user ID filters."""
    # Arrange
    query_vector = [0.1, 0.2, 0.3, 0.4]
    entity_type = EntityType.PERSON
    user_id = uuid.uuid4()

    mock_response = MagicMock()
    mock_response.matches = []
    vector_store.index.query.return_value = mock_response

    # Act
    await vector_store.search(
        query_vector=query_vector, top_k=5, entity_type=entity_type, user_id=user_id
    )

    # Assert
    vector_store.index.query.assert_called_once_with(
        vector=query_vector,
        top_k=5,
        namespace="test-namespace",
        filter={"entity_type": "PERSON", "user_id": str(user_id)},
        include_metadata=True,
    )


@pytest.mark.asyncio
async def test_search_error(vector_store, mock_pinecone_index):
    """Test handling errors during search."""
    # Arrange
    query_vector = [0.1, 0.2, 0.3, 0.4]
    vector_store.index.query.side_effect = Exception("Search error")

    # Act & Assert
    with pytest.raises(
        VectorStoreError, match="Failed to search vectors: Search error"
    ):
        await vector_store.search(query_vector)


@pytest.mark.asyncio
async def test_delete_vectors(vector_store, mock_pinecone_index):
    """Test deleting vectors from the vector store."""
    # Arrange
    vector_ids = ["id1", "id2", "id3"]

    # Act
    await vector_store.delete_vectors(vector_ids)

    # Assert
    vector_store.index.delete.assert_called_once_with(
        ids=vector_ids, namespace="test-namespace"
    )


@pytest.mark.asyncio
async def test_delete_vectors_error(vector_store, mock_pinecone_index):
    """Test handling errors when deleting vectors."""
    # Arrange
    vector_ids = ["id1", "id2", "id3"]
    vector_store.index.delete.side_effect = Exception("Deletion error")

    # Act & Assert
    with pytest.raises(
        VectorStoreError, match="Failed to delete vectors: Deletion error"
    ):
        await vector_store.delete_vectors(vector_ids)


def test_ensure_index_exists_index_exists():
    """Test ensuring index exists when it already exists."""
    # Act
    with patch("src.infrastructure.services.vector_store_service.pinecone.init"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ) as mock_list, patch(
        "src.infrastructure.services.vector_store_service.pinecone.create_index"
    ) as mock_create, patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index"
    ):
        store = PineconeVectorStore(api_key="test_key", environment="test-env")

    # Assert
    mock_create.assert_not_called()


def test_ensure_index_exists_create_index():
    """Test ensuring index exists when it doesn't exist."""
    # Act
    with patch("src.infrastructure.services.vector_store_service.pinecone.init"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["other-index"],
    ) as mock_list, patch(
        "src.infrastructure.services.vector_store_service.pinecone.create_index"
    ) as mock_create, patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index"
    ):
        store = PineconeVectorStore(api_key="test_key", environment="test-env")

    # Assert
    mock_create.assert_called_once_with(
        name="semantic-engine", dimension=1536, metric="cosine"
    )


def test_ensure_index_exists_error():
    """Test handling errors when ensuring index exists."""
    # Act & Assert
    with pytest.raises(
        VectorStoreError, match="Failed to ensure index exists: API error"
    ):
        with patch(
            "src.infrastructure.services.vector_store_service.pinecone.init"
        ), patch(
            "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
            side_effect=Exception("API error"),
        ), patch(
            "src.infrastructure.services.vector_store_service.pinecone.Index"
        ):
            PineconeVectorStore(api_key="test_key", environment="test-env")
