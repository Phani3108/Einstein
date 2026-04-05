"""Entity extraction service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from uuid import UUID

from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import ThoughtMetadata


class EntityExtractionService(ABC):
    """Interface for extracting semantic entities from thought content."""

    @abstractmethod
    async def extract_entities(
        self, content: str, thought_id: UUID, metadata: Optional[ThoughtMetadata] = None
    ) -> List[SemanticEntry]:
        """Extract semantic entities from thought content.

        Args:
            content: The raw thought content to analyze
            thought_id: The ID of the thought being analyzed
            metadata: Optional metadata to provide context for extraction

        Returns:
            A list of extracted semantic entries

        Raises:
            EntityExtractionError: If extraction fails
        """
        pass
