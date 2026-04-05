"""Search thoughts use case for the Personal Semantic Engine."""

import time
from typing import List
from uuid import UUID

from src.domain.entities.search_query import SearchQuery
from src.domain.entities.search_result import SearchResponse
from src.domain.exceptions import SearchError, SearchQueryError
from src.domain.repositories.search_repository import SearchRepository
from src.domain.services.search_service import SearchService


class SearchThoughtsUseCase:
    """Use case for searching thoughts with hybrid search strategy."""

    def __init__(
        self,
        search_repository: SearchRepository,
        search_service: SearchService,
    ):
        """Initialize the use case with required dependencies.

        Args:
            search_repository: Repository for search operations
            search_service: Service for search-related operations
        """
        self._search_repository = search_repository
        self._search_service = search_service

    async def execute(self, query_text: str, user_id: UUID) -> SearchResponse:
        """Execute a search for thoughts using hybrid search strategy.

        Args:
            query_text: The search query text
            user_id: The ID of the user performing the search

        Returns:
            A search response containing ranked results and metadata

        Raises:
            SearchQueryError: If query parsing fails
            SearchError: If search execution fails
        """
        start_time = time.time()

        try:
            # Parse and validate the search query
            search_query = await self._search_service.parse_query(
                query_text=query_text, user_id=str(user_id)
            )

            # Perform the search
            search_response = await self._search_repository.search(search_query)

            # Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Update response with search time
            final_response = SearchResponse(
                results=search_response.results,
                total_count=search_response.total_count,
                page=search_response.page,
                page_size=search_response.page_size,
                query_text=search_response.query_text,
                search_time_ms=search_time_ms,
                suggestions=search_response.suggestions,
            )

            return final_response

        except SearchQueryError:
            # Re-raise query errors as-is
            raise
        except Exception as e:
            raise SearchError(f"Search execution failed: {str(e)}")

    async def execute_with_query(self, search_query: SearchQuery) -> SearchResponse:
        """Execute a search with a pre-built search query.

        Args:
            search_query: The complete search query object

        Returns:
            A search response containing ranked results and metadata

        Raises:
            SearchError: If search execution fails
        """
        start_time = time.time()

        try:
            # Perform the search
            search_response = await self._search_repository.search(search_query)

            # Calculate search time
            search_time_ms = int((time.time() - start_time) * 1000)

            # Update response with search time
            final_response = SearchResponse(
                results=search_response.results,
                total_count=search_response.total_count,
                page=search_response.page,
                page_size=search_response.page_size,
                query_text=search_response.query_text,
                search_time_ms=search_time_ms,
                suggestions=search_response.suggestions,
            )

            return final_response

        except Exception as e:
            raise SearchError(f"Search execution failed: {str(e)}")

    async def get_suggestions(
        self, query_text: str, user_id: UUID, limit: int = 5
    ) -> List[str]:
        """Get search suggestions for partial query text.

        Args:
            query_text: The partial query text
            user_id: The ID of the user requesting suggestions
            limit: Maximum number of suggestions to return

        Returns:
            A list of suggested search terms

        Raises:
            SearchError: If suggestion generation fails
        """
        try:
            suggestions = await self._search_repository.get_suggestions(
                query_text=query_text, user_id=str(user_id), limit=limit
            )
            return suggestions

        except Exception as e:
            raise SearchError(f"Suggestion generation failed: {str(e)}")