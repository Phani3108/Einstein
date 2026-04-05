"""Search service interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.search_query import SearchQuery
from src.domain.entities.search_result import SearchResponse, SearchScore


class SearchService(ABC):
    """Interface for search-related operations."""

    @abstractmethod
    async def parse_query(self, query_text: str, user_id: str) -> SearchQuery:
        """Parse and validate a search query string.

        Args:
            query_text: The raw search query text
            user_id: The user ID making the search

        Returns:
            A validated SearchQuery object

        Raises:
            SearchQueryError: If query parsing fails
        """
        pass

    @abstractmethod
    async def calculate_score(
        self,
        semantic_similarity: float,
        keyword_match: float,
        recency_score: float,
        confidence_score: float,
    ) -> SearchScore:
        """Calculate a combined search score from individual components.

        Args:
            semantic_similarity: Semantic similarity score (0-1)
            keyword_match: Keyword matching score (0-1)
            recency_score: Recency-based score (0-1)
            confidence_score: Entity extraction confidence score (0-1)

        Returns:
            A SearchScore object with the calculated final score
        """
        pass

    @abstractmethod
    async def rank_results(self, results: List["SearchResult"]) -> List["SearchResult"]:
        """Rank search results based on their scores.

        Args:
            results: List of search results to rank

        Returns:
            Ranked list of search results

        Raises:
            SearchRankingError: If ranking fails
        """
        pass