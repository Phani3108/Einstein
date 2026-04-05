#!/usr/bin/env python3
"""Test only the vector services without importing the full container."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))


def test_vector_services_directly():
    """Test vector services directly without container."""
    print("Testing Vector Services Directly...")

    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
    os.environ["PINECONE_ENVIRONMENT"] = "test-env"

    # Mock external dependencies
    with patch(
        "src.infrastructure.services.embedding_service.AsyncOpenAI"
    ) as mock_openai, patch(
        "src.infrastructure.services.vector_store_service.pinecone.init"
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index"
    ) as mock_index:
        from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
        from src.infrastructure.services.vector_store_service import PineconeVectorStore

        # Test embedding service creation
        embedding_service = OpenAIEmbeddingService(api_key="test-openai-key")
        assert embedding_service.api_key == "test-openai-key"
        assert embedding_service.model == "text-embedding-ada-002"

        # Test vector store creation
        vector_store = PineconeVectorStore(
            api_key="test-pinecone-key", environment="test-env"
        )
        assert vector_store.api_key == "test-pinecone-key"
        assert vector_store.environment == "test-env"
        assert vector_store.index_name == "semantic-engine"

        print("✓ Vector services creation tests passed")


def test_service_interfaces_directly():
    """Test service interfaces directly."""
    print("Testing Service Interfaces Directly...")

    from src.domain.services.embedding_service import EmbeddingService
    from src.domain.services.vector_store_service import VectorStoreService
    from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
    from src.infrastructure.services.vector_store_service import PineconeVectorStore

    # Test inheritance
    assert issubclass(OpenAIEmbeddingService, EmbeddingService)
    assert issubclass(PineconeVectorStore, VectorStoreService)

    # Test method existence
    embedding_methods = ["generate_embedding", "generate_embeddings"]
    vector_store_methods = ["store_vector", "search", "delete_vectors"]

    for method in embedding_methods:
        assert hasattr(OpenAIEmbeddingService, method)

    for method in vector_store_methods:
        assert hasattr(PineconeVectorStore, method)

    print("✓ Service interface tests passed")


def main():
    """Run vector service tests."""
    print("Testing Vector Services Implementation")
    print("=" * 50)

    try:
        test_vector_services_directly()
        test_service_interfaces_directly()

        print("\n" + "=" * 50)
        print("🎉 ALL VECTOR SERVICE TESTS PASSED!")
        print("✓ Services can be created with correct configuration")
        print("✓ Services implement the correct interfaces")
        print("✓ Clean architecture principles maintained")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n❌ VECTOR SERVICE TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
