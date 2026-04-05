"""Script to run the vector storage tests directly."""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from src.domain.entities.enums import EntityType
from src.domain.exceptions import EmbeddingError, VectorStoreError
from src.domain.services.vector_store_service import (
    VectorSearchResult as BaseVectorSearchResult,
)
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.infrastructure.services.vector_store_service import (
    PineconeVectorStore,
    VectorSearchResult,
)


class TestEmbeddingService(unittest.TestCase):
    """Test the OpenAI embedding service."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_client = AsyncMock()
        self.mock_client.embeddings.create = AsyncMock()

        patcher = patch(
            "src.infrastructure.services.embedding_service.AsyncOpenAI",
            return_value=self.mock_client,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.service = OpenAIEmbeddingService(api_key="test_key")
        self.service.client = self.mock_client

    def test_init(self):
        """Test initialization with API key."""
        service = OpenAIEmbeddingService(api_key="test_key")
        self.assertEqual(service.api_key, "test_key")
        self.assertEqual(service.model, "text-embedding-ada-002")
        self.assertEqual(service.batch_size, 100)

    async def test_generate_embedding(self):
        """Test generating a single embedding."""
        # Arrange
        text = "This is a test text"
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
        self.mock_client.embeddings.create.return_value = mock_response

        # Act
        result = await self.service.generate_embedding(text)

        # Assert
        self.assertEqual(result, [0.1, 0.2, 0.3])
        self.mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-ada-002",
            input=text,
        )

    async def test_generate_embedding_empty_text(self):
        """Test generating an embedding with empty text."""
        # Act & Assert
        with self.assertRaises(EmbeddingError):
            await self.service.generate_embedding("")


class TestVectorStoreService(unittest.TestCase):
    """Test the Pinecone vector store service."""

    def setUp(self):
        """Set up the test environment."""
        self.mock_index = MagicMock()
        self.mock_index.upsert = MagicMock()
        self.mock_index.query = MagicMock()
        self.mock_index.delete = MagicMock()

        # Mock pinecone module functions
        self.pinecone_init_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.init"
        )
        self.pinecone_list_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
            return_value=["semantic-engine"],
        )
        self.pinecone_index_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.Index",
            return_value=self.mock_index,
        )

        self.pinecone_init_patcher.start()
        self.pinecone_list_patcher.start()
        self.pinecone_index_patcher.start()

        self.addCleanup(self.pinecone_init_patcher.stop)
        self.addCleanup(self.pinecone_list_patcher.stop)
        self.addCleanup(self.pinecone_index_patcher.stop)

        self.store = PineconeVectorStore(
            api_key="test_key",
            environment="test-env",
            index_name="semantic-engine",
            namespace="test-namespace",
        )
        self.store.index = self.mock_index

    def test_init(self):
        """Test initialization with API key and environment."""
        store = PineconeVectorStore(api_key="test_key", environment="test-env")
        self.assertEqual(store.api_key, "test_key")
        self.assertEqual(store.environment, "test-env")
        self.assertEqual(store.index_name, "semantic-engine")
        self.assertEqual(store.namespace, "default")

    async def test_store_vector(self):
        """Test storing a vector in the vector store."""
        # Arrange
        vector_id = "test-id"
        vector = [0.1, 0.2, 0.3, 0.4]
        metadata = {"entity_type": "PERSON", "user_id": "test-user"}

        # Act
        await self.store.store_vector(vector_id, vector, metadata)

        # Assert
        self.mock_index.upsert.assert_called_once_with(
            vectors=[{"id": vector_id, "values": vector, "metadata": metadata}],
            namespace="test-namespace",
        )

    async def test_search(self):
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

        self.mock_index.query.return_value = mock_response

        # Act
        results = await self.store.search(query_vector, top_k=2)

        # Assert
        self.assertEqual(len(results), 2)
        self.assertIsInstance(results[0], VectorSearchResult)
        self.assertEqual(results[0].id, "id1")
        self.assertEqual(results[0].score, 0.95)
        self.assertEqual(
            results[0].metadata, {"entity_type": "PERSON", "value": "John Doe"}
        )

        self.assertEqual(results[1].id, "id2")
        self.assertEqual(results[1].score, 0.85)

        self.mock_index.query.assert_called_once_with(
            vector=query_vector,
            top_k=2,
            namespace="test-namespace",
            filter=None,
            include_metadata=True,
        )


class TestIntegration(unittest.TestCase):
    """Test the integration between embedding service and vector store."""

    def setUp(self):
        """Set up the test environment."""
        # Set up embedding service
        self.mock_openai_client = AsyncMock()
        self.mock_openai_client.embeddings.create = AsyncMock()

        openai_patcher = patch(
            "src.infrastructure.services.embedding_service.AsyncOpenAI",
            return_value=self.mock_openai_client,
        )
        openai_patcher.start()
        self.addCleanup(openai_patcher.stop)

        self.embedding_service = OpenAIEmbeddingService(api_key="test_key")
        self.embedding_service.client = self.mock_openai_client

        # Set up vector store
        self.mock_index = MagicMock()
        self.mock_index.upsert = MagicMock()
        self.mock_index.query = MagicMock()

        # Mock pinecone module functions
        self.pinecone_init_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.init"
        )
        self.pinecone_list_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.list_indexes",
            return_value=["semantic-engine"],
        )
        self.pinecone_index_patcher = patch(
            "src.infrastructure.services.vector_store_service.pinecone.Index",
            return_value=self.mock_index,
        )

        self.pinecone_init_patcher.start()
        self.pinecone_list_patcher.start()
        self.pinecone_index_patcher.start()

        self.addCleanup(self.pinecone_init_patcher.stop)
        self.addCleanup(self.pinecone_list_patcher.stop)
        self.addCleanup(self.pinecone_index_patcher.stop)

        self.vector_store = PineconeVectorStore(
            api_key="test_key",
            environment="test-env",
            index_name="semantic-engine",
            namespace="test-namespace",
        )
        self.vector_store.index = self.mock_index

    async def test_index_and_search_thought(self):
        """Test the full flow of embedding generation and vector storage/search."""
        # Arrange
        thought_id = "test-thought-id"
        user_id = "test-user-id"
        content = "I met John at the coffee shop yesterday."

        # Mock embedding generation
        mock_embedding = [0.1, 0.2, 0.3, 0.4]
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        self.mock_openai_client.embeddings.create.return_value = mock_response

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
        self.mock_index.query.return_value = mock_search_response

        # Act - Generate embedding
        embedding = await self.embedding_service.generate_embedding(content)

        # Act - Store vector
        metadata = {
            "entity_type": "PERSON",
            "entity_value": "John",
            "user_id": user_id,
            "thought_id": thought_id,
        }
        await self.vector_store.store_vector(thought_id, embedding, metadata)

        # Act - Search for similar vectors
        search_embedding = await self.embedding_service.generate_embedding(
            "Who did I meet yesterday?"
        )
        search_results = await self.vector_store.search(
            query_vector=search_embedding, top_k=5, entity_type=EntityType.PERSON
        )

        # Assert
        self.assertEqual(embedding, mock_embedding)

        # Verify vector was stored correctly
        self.mock_index.upsert.assert_called_once()
        upsert_call = self.mock_index.upsert.call_args
        self.assertEqual(upsert_call[1]["vectors"][0]["id"], thought_id)
        self.assertEqual(upsert_call[1]["vectors"][0]["values"], mock_embedding)
        self.assertEqual(upsert_call[1]["vectors"][0]["metadata"], metadata)

        # Verify search was performed correctly
        self.assertEqual(len(search_results), 1)
        self.assertEqual(search_results[0].id, thought_id)
        self.assertEqual(search_results[0].score, 0.95)
        self.assertEqual(search_results[0].metadata["entity_value"], "John")


def run_tests():
    """Run the tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingService))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorStoreService))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)


if __name__ == "__main__":
    # Run async tests
    for test_class in [TestEmbeddingService, TestVectorStoreService, TestIntegration]:
        for method_name in dir(test_class):
            if method_name.startswith("test_") and method_name != "test_init":
                method = getattr(test_class, method_name)
                if asyncio.iscoroutinefunction(method):
                    setattr(
                        test_class,
                        method_name,
                        lambda self, method=method: asyncio.run(method(self)),
                    )

    run_tests()
