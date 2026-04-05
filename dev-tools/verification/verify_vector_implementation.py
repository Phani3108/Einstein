#!/usr/bin/env python3
"""Verify that the vector storage implementation is working correctly."""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))

from src.domain.entities.enums import EntityType
from src.domain.exceptions import EmbeddingError, VectorStoreError
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.infrastructure.services.vector_store_service import PineconeVectorStore


async def test_embedding_service():
    """Test the embedding service functionality."""
    print("Testing OpenAI Embedding Service...")

    # Mock the OpenAI client
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4])]
    mock_client.embeddings.create.return_value = mock_response

    with patch(
        "src.infrastructure.services.embedding_service.AsyncOpenAI",
        return_value=mock_client,
    ):
        service = OpenAIEmbeddingService(api_key="test_key")
        service.client = mock_client

        # Test single embedding
        result = await service.generate_embedding("Test text")
        assert result == [
            0.1,
            0.2,
            0.3,
            0.4,
        ], f"Expected [0.1, 0.2, 0.3, 0.4], got {result}"

        # Test batch embeddings
        mock_data = [
            MagicMock(embedding=[0.1, 0.2], index=0),
            MagicMock(embedding=[0.3, 0.4], index=1),
        ]
        mock_response.data = mock_data

        results = await service.generate_embeddings(["Text 1", "Text 2"])
        assert len(results) == 2, f"Expected 2 results, got {len(results)}"
        assert results[0] == [0.1, 0.2], f"Expected [0.1, 0.2], got {results[0]}"
        assert results[1] == [0.3, 0.4], f"Expected [0.3, 0.4], got {results[1]}"

        # Test empty text error
        try:
            await service.generate_embedding("")
            assert False, "Should have raised EmbeddingError"
        except EmbeddingError:
            pass  # Expected

        print("✓ Embedding service tests passed")


async def test_vector_store():
    """Test the vector store functionality."""
    print("Testing Pinecone Vector Store...")

    # Mock Pinecone
    mock_index = MagicMock()
    mock_index.upsert = MagicMock()
    mock_index.query = MagicMock()
    mock_index.delete = MagicMock()

    with patch("src.infrastructure.services.vector_store_service.pinecone.init"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index",
        return_value=mock_index,
    ):
        store = PineconeVectorStore(api_key="test_key", environment="test-env")
        store.index = mock_index

        # Test storing vector
        await store.store_vector("test-id", [0.1, 0.2, 0.3], {"type": "test"})
        mock_index.upsert.assert_called_once()

        # Test searching vectors
        mock_match = MagicMock()
        mock_match.id = "test-id"
        mock_match.score = 0.95
        mock_match.metadata = {"type": "test"}

        mock_response = MagicMock()
        mock_response.matches = [mock_match]
        mock_index.query.return_value = mock_response

        results = await store.search([0.1, 0.2, 0.3], top_k=5)
        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert results[0].id == "test-id", f"Expected 'test-id', got {results[0].id}"
        assert results[0].score == 0.95, f"Expected 0.95, got {results[0].score}"

        # Test deleting vectors
        await store.delete_vectors(["test-id"])
        mock_index.delete.assert_called_once()

        print("✓ Vector store tests passed")


async def test_integration():
    """Test integration between embedding service and vector store."""
    print("Testing Integration...")

    # Mock OpenAI
    mock_openai_client = AsyncMock()
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3, 0.4])]
    mock_openai_client.embeddings.create.return_value = mock_embedding_response

    # Mock Pinecone
    mock_index = MagicMock()
    mock_index.upsert = MagicMock()
    mock_index.query = MagicMock()

    with patch(
        "src.infrastructure.services.embedding_service.AsyncOpenAI",
        return_value=mock_openai_client,
    ), patch("src.infrastructure.services.vector_store_service.pinecone.init"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index",
        return_value=mock_index,
    ):
        # Create services
        embedding_service = OpenAIEmbeddingService(api_key="test_key")
        embedding_service.client = mock_openai_client

        vector_store = PineconeVectorStore(api_key="test_key", environment="test-env")
        vector_store.index = mock_index

        # Test full workflow
        text = "I met John at the coffee shop yesterday."

        # Generate embedding
        embedding = await embedding_service.generate_embedding(text)
        assert embedding == [
            0.1,
            0.2,
            0.3,
            0.4,
        ], f"Expected [0.1, 0.2, 0.3, 0.4], got {embedding}"

        # Store vector
        metadata = {"entity_type": "PERSON", "entity_value": "John"}
        await vector_store.store_vector("thought-1", embedding, metadata)

        # Verify storage call
        mock_index.upsert.assert_called_once()
        upsert_call = mock_index.upsert.call_args
        assert upsert_call[1]["vectors"][0]["id"] == "thought-1"
        assert upsert_call[1]["vectors"][0]["values"] == embedding
        assert upsert_call[1]["vectors"][0]["metadata"] == metadata

        # Mock search response
        mock_match = MagicMock()
        mock_match.id = "thought-1"
        mock_match.score = 0.95
        mock_match.metadata = metadata

        mock_search_response = MagicMock()
        mock_search_response.matches = [mock_match]
        mock_index.query.return_value = mock_search_response

        # Search for similar vectors
        search_embedding = await embedding_service.generate_embedding("Who did I meet?")
        results = await vector_store.search(
            search_embedding, entity_type=EntityType.PERSON
        )

        assert len(results) == 1, f"Expected 1 result, got {len(results)}"
        assert (
            results[0].id == "thought-1"
        ), f"Expected 'thought-1', got {results[0].id}"
        assert (
            results[0].metadata["entity_value"] == "John"
        ), f"Expected 'John', got {results[0].metadata.get('entity_value')}"

        print("✓ Integration tests passed")


async def main():
    """Run all verification tests."""
    print("Verifying Vector Storage Implementation")
    print("=" * 50)

    try:
        await test_embedding_service()
        await test_vector_store()
        await test_integration()

        print("\n" + "=" * 50)
        print("🎉 ALL TESTS PASSED! Vector storage implementation is working correctly.")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
