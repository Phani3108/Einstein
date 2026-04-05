"""Semantic entry repository interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry


class SemanticEntryRepository(ABC):
    """Interface for semantic entry data access."""

    @abstractmethod
    async def save(self, semantic_entry: SemanticEntry) -> SemanticEntry:
        """Save a semantic entry to the repository.

        Args:
            semantic_entry: The semantic entry to save

        Returns:
            The saved semantic entry with any generated fields populated
        """
        pass

    @abstractmethod
    async def save_many(
        self, semantic_entries: List[SemanticEntry]
    ) -> List[SemanticEntry]:
        """Save multiple semantic entries to the repository.

        Args:
            semantic_entries: The semantic entries to save

        Returns:
            The saved semantic entries with any generated fields populated
        """
        pass

    @abstractmethod
    async def find_by_id(self, entry_id: UUID) -> Optional[SemanticEntry]:
        """Find a semantic entry by its ID.

        Args:
            entry_id: The ID of the semantic entry to find

        Returns:
            The semantic entry if found, None otherwise
        """
        pass

    @abstractmethod
    async def find_by_thought(self, thought_id: UUID) -> List[SemanticEntry]:
        """Find semantic entries by thought ID.

        Args:
            thought_id: The ID of the thought whose semantic entries to find

        Returns:
            A list of semantic entries belonging to the thought
        """
        pass

    @abstractmethod
    async def find_by_entity_type(
        self, entity_type: EntityType, skip: int = 0, limit: int = 100
    ) -> List[SemanticEntry]:
        """Find semantic entries by entity type.

        Args:
            entity_type: The type of entity to find
            skip: Number of entries to skip for pagination
            limit: Maximum number of entries to return

        Returns:
            A list of semantic entries of the specified type
        """
        pass

    @abstractmethod
    async def find_by_entity_value(
        self, entity_value: str, skip: int = 0, limit: int = 100
    ) -> List[SemanticEntry]:
        """Find semantic entries by entity value.

        Args:
            entity_value: The value of the entity to find
            skip: Number of entries to skip for pagination
            limit: Maximum number of entries to return

        Returns:
            A list of semantic entries with the specified value
        """
        pass

    @abstractmethod
    async def delete_by_thought(self, thought_id: UUID) -> None:
        """Delete all semantic entries for a thought.

        Args:
            thought_id: The ID of the thought whose semantic entries to delete
        """
        pass
