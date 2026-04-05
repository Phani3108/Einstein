"""Embedding service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingService(ABC):
    """Interface for generating vector embeddings from text."""

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate a vector embedding for the given text.

        Args:
            text: The text to generate an embedding for

        Returns:
            A vector embedding representing the text

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    @abstractmethod
    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate vector embeddings for multiple texts.

        Args:
            texts: The texts to generate embeddings for

        Returns:
            A list of vector embeddings representing the texts

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass
