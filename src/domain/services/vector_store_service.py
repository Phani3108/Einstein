"""Vector store service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

from src.domain.entities.enums import EntityType


class VectorSearchResult:
    """Result of a vector search operation."""

    id: str
    score: float
    metadata: Dict[str, str]


class VectorStoreService(ABC):
    """Interface for vector storage and retrieval."""

    @abstractmethod
    async def store_vector(
        self, id: str, vector: List[float], metadata: Dict[str, str]
    ) -> None:
        """Store a vector in the vector database.

        Args:
            id: Unique identifier for the vector
            vector: The vector to store
            metadata: Additional metadata to store with the vector

        Raises:
            VectorStoreError: If storage fails
        """
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        entity_type: Optional[EntityType] = None,
        user_id: Optional[UUID] = None,
    ) -> List[VectorSearchResult]:
        """Search for similar vectors.

        Args:
            query_vector: The vector to search for
            top_k: Maximum number of results to return
            entity_type: Optional filter by entity type
            user_id: Optional filter by user ID

        Returns:
            A list of search results ordered by similarity

        Raises:
            VectorStoreError: If search fails
        """
        pass

    @abstractmethod
    async def delete_vectors(self, ids: List[str]) -> None:
        """Delete vectors from the vector database.

        Args:
            ids: List of vector IDs to delete

        Raises:
            VectorStoreError: If deletion fails
        """
        pass
