#!/usr/bin/env python3
"""Test that the dependency injection container works with our vector services."""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath("."))


def test_container_configuration():
    """Test that the container properly configures our services."""
    print("Testing Container Configuration...")

    # Set environment variables
    os.environ["OPENAI_API_KEY"] = "test-openai-key"
    os.environ["PINECONE_API_KEY"] = "test-pinecone-key"
    os.environ["PINECONE_ENVIRONMENT"] = "test-env"

    # Mock external dependencies
    with patch("src.infrastructure.services.embedding_service.AsyncOpenAI"), patch(
        "src.infrastructure.services.vector_store_service.pinecone.init"
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
        return_value=["semantic-engine"],
    ), patch(
        "src.infrastructure.services.vector_store_service.pinecone.Index"
    ):
        from src.container import container

        # Test that services can be created
        embedding_service = container.embedding_service()
        vector_store_service = container.vector_store_service()

        # Verify service types
        from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
        from src.infrastructure.services.vector_store_service import PineconeVectorStore

        assert isinstance(
            embedding_service, OpenAIEmbeddingService
        ), f"Expected OpenAIEmbeddingService, got {type(embedding_service)}"
        assert isinstance(
            vector_store_service, PineconeVectorStore
        ), f"Expected PineconeVectorStore, got {type(vector_store_service)}"

        # Verify configuration
        assert (
            embedding_service.api_key == "test-openai-key"
        ), f"Expected 'test-openai-key', got {embedding_service.api_key}"
        assert (
            vector_store_service.api_key == "test-pinecone-key"
        ), f"Expected 'test-pinecone-key', got {vector_store_service.api_key}"
        assert (
            vector_store_service.environment == "test-env"
        ), f"Expected 'test-env', got {vector_store_service.environment}"

        print("✓ Container configuration tests passed")


def test_service_interfaces():
    """Test that our services implement the correct interfaces."""
    print("Testing Service Interfaces...")

    from src.domain.services.embedding_service import EmbeddingService
    from src.domain.services.vector_store_service import VectorStoreService
    from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
    from src.infrastructure.services.vector_store_service import PineconeVectorStore

    # Test that implementations inherit from interfaces
    assert issubclass(
        OpenAIEmbeddingService, EmbeddingService
    ), "OpenAIEmbeddingService should inherit from EmbeddingService"
    assert issubclass(
        PineconeVectorStore, VectorStoreService
    ), "PineconeVectorStore should inherit from VectorStoreService"

    # Test that interfaces have the expected methods
    embedding_methods = ["generate_embedding", "generate_embeddings"]
    vector_store_methods = ["store_vector", "search", "delete_vectors"]

    for method in embedding_methods:
        assert hasattr(
            EmbeddingService, method
        ), f"EmbeddingService should have {method} method"
        assert hasattr(
            OpenAIEmbeddingService, method
        ), f"OpenAIEmbeddingService should have {method} method"

    for method in vector_store_methods:
        assert hasattr(
            VectorStoreService, method
        ), f"VectorStoreService should have {method} method"
        assert hasattr(
            PineconeVectorStore, method
        ), f"PineconeVectorStore should have {method} method"

    print("✓ Service interface tests passed")


def main():
    """Run all container integration tests."""
    print("Testing Container Integration")
    print("=" * 50)

    try:
        test_container_configuration()
        test_service_interfaces()

        print("\n" + "=" * 50)
        print("🎉 ALL CONTAINER TESTS PASSED!")
        print("✓ Dependency injection working correctly")
        print("✓ Services properly configured")
        print("✓ Interface compliance verified")
        print("=" * 50)
        return True

    except Exception as e:
        print(f"\n❌ CONTAINER TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
