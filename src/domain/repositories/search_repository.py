"""Search repository interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.search_query import SearchQuery
from src.domain.entities.search_result import SearchResponse
from src.domain.entities.thought import Thought
from src.domain.entities.semantic_entry import SemanticEntry


class SearchRepository(ABC):
    """Interface for search operations."""

    @abstractmethod
    async def index_thought(self, thought: Thought, entities: List[SemanticEntry]) -> None:
        """Index a thought and its semantic entries for search.

        Args:
            thought: The thought to index
            entities: The semantic entries associated with the thought

        Raises:
            SearchIndexError: If indexing fails
        """
        pass

    @abstractmethod
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Perform a search based on the given query.

        Args:
            query: The search query containing search parameters

        Returns:
            A search response containing results and metadata

        Raises:
            SearchError: If search fails
        """
        pass

    @abstractmethod
    async def remove_from_index(self, thought_id: str) -> None:
        """Remove a thought from the search index.

        Args:
            thought_id: The ID of the thought to remove

        Raises:
            SearchIndexError: If removal fails
        """
        pass

    @abstractmethod
    async def get_suggestions(self, query_text: str, user_id: str, limit: int = 5) -> List[str]:
        """Get search suggestions based on partial query text.

        Args:
            query_text: The partial query text
            user_id: The user ID to scope suggestions to
            limit: Maximum number of suggestions to return

        Returns:
            A list of suggested search terms

        Raises:
            SearchError: If suggestion generation fails
        """
        pass