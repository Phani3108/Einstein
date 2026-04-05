"""Search service implementation for the Personal Semantic Engine."""

import re
from datetime import datetime, timedelta
from typing import List

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import (
    DateRange,
    EntityFilter,
    Pagination,
    SearchQuery,
    SortOptions,
)
from src.domain.entities.search_result import SearchResponse, SearchResult, SearchScore
from src.domain.exceptions import SearchQueryError, SearchRankingError
from src.domain.services.search_service import SearchService


class HybridSearchService(SearchService):
    """Implementation of search service with hybrid search capabilities."""

    # Scoring weights for different components
    SEMANTIC_WEIGHT = 0.4
    KEYWORD_WEIGHT = 0.3
    RECENCY_WEIGHT = 0.2
    CONFIDENCE_WEIGHT = 0.1

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
        try:
            # Clean the query text
            cleaned_query = query_text.strip()
            if not cleaned_query:
                raise SearchQueryError("Query text cannot be empty")

            # Parse entity type filters from query (e.g., "type:person john")
            entity_filter = self._parse_entity_filters(cleaned_query)
            cleaned_query = self._remove_filter_syntax(cleaned_query)

            # Parse date range filters (e.g., "after:2024-01-01 before:2024-12-31")
            date_range = self._parse_date_filters(cleaned_query)
            cleaned_query = self._remove_date_syntax(cleaned_query)

            # Parse sort options (e.g., "sort:date order:asc")
            sort_options = self._parse_sort_options(cleaned_query)
            cleaned_query = self._remove_sort_syntax(cleaned_query)

            # Final cleanup
            cleaned_query = cleaned_query.strip()
            if not cleaned_query:
                raise SearchQueryError("Query text cannot be empty after parsing filters")

            return SearchQuery(
                query_text=cleaned_query,
                user_id=user_id,
                date_range=date_range,
                entity_filter=entity_filter,
                sort_options=sort_options,
                pagination=Pagination(),  # Default pagination
                include_raw_content=True,
                highlight_matches=True,
            )

        except SearchQueryError:
            raise
        except Exception as e:
            raise SearchQueryError(f"Failed to parse query: {str(e)}")

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
        # Ensure all scores are within valid range
        semantic_similarity = max(0.0, min(1.0, semantic_similarity))
        keyword_match = max(0.0, min(1.0, keyword_match))
        recency_score = max(0.0, min(1.0, recency_score))
        confidence_score = max(0.0, min(1.0, confidence_score))

        # Calculate weighted final score
        final_score = (
            semantic_similarity * self.SEMANTIC_WEIGHT
            + keyword_match * self.KEYWORD_WEIGHT
            + recency_score * self.RECENCY_WEIGHT
            + confidence_score * self.CONFIDENCE_WEIGHT
        )

        return SearchScore(
            semantic_similarity=semantic_similarity,
            keyword_match=keyword_match,
            recency_score=recency_score,
            confidence_score=confidence_score,
            final_score=final_score,
        )

    async def rank_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Rank search results based on their scores.

        Args:
            results: List of search results to rank

        Returns:
            Ranked list of search results

        Raises:
            SearchRankingError: If ranking fails
        """
        try:
            # Sort results by final score in descending order
            sorted_results = sorted(
                results, key=lambda r: r.score.final_score, reverse=True
            )

            # Update rank positions (create new objects since they're frozen)
            ranked_results = []
            for i, result in enumerate(sorted_results):
                ranked_result = SearchResult(
                    thought=result.thought,
                    matching_entities=result.matching_entities,
                    matches=result.matches,
                    score=result.score,
                    rank=i + 1,
                )
                ranked_results.append(ranked_result)

            return ranked_results

        except Exception as e:
            raise SearchRankingError(f"Failed to rank results: {str(e)}")

    def _parse_entity_filters(self, query_text: str) -> EntityFilter:
        """Parse entity type filters from query text."""
        entity_filter = EntityFilter()

        # Look for type:entity_type patterns
        type_pattern = r"type:(\w+)"
        matches = re.findall(type_pattern, query_text, re.IGNORECASE)

        for match in matches:
            try:
                entity_type = EntityType(match.lower())
                if entity_type not in entity_filter.entity_types:
                    entity_filter.entity_types.append(entity_type)
            except ValueError:
                # Invalid entity type, ignore
                pass

        return entity_filter

    def _remove_filter_syntax(self, query_text: str) -> str:
        """Remove entity filter syntax from query text."""
        cleaned = re.sub(r"type:\w+", "", query_text, flags=re.IGNORECASE)
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _parse_date_filters(self, query_text: str) -> DateRange:
        """Parse date range filters from query text."""
        date_range = DateRange()

        # Look for after:date patterns
        after_pattern = r"after:(\d{4}-\d{2}-\d{2})"
        after_match = re.search(after_pattern, query_text, re.IGNORECASE)
        if after_match:
            try:
                date_range.start_date = datetime.strptime(after_match.group(1), "%Y-%m-%d")
            except ValueError:
                pass

        # Look for before:date patterns
        before_pattern = r"before:(\d{4}-\d{2}-\d{2})"
        before_match = re.search(before_pattern, query_text, re.IGNORECASE)
        if before_match:
            try:
                date_range.end_date = datetime.strptime(before_match.group(1), "%Y-%m-%d")
            except ValueError:
                pass

        # Look for relative date patterns (e.g., "last week", "yesterday")
        if "last week" in query_text.lower():
            date_range.start_date = datetime.now() - timedelta(weeks=1)
        elif "yesterday" in query_text.lower():
            date_range.start_date = datetime.now() - timedelta(days=1)
            date_range.end_date = datetime.now()

        return date_range

    def _remove_date_syntax(self, query_text: str) -> str:
        """Remove date filter syntax from query text."""
        query_text = re.sub(r"after:\d{4}-\d{2}-\d{2}", "", query_text, flags=re.IGNORECASE)
        query_text = re.sub(r"before:\d{4}-\d{2}-\d{2}", "", query_text, flags=re.IGNORECASE)
        query_text = re.sub(r"last week", "", query_text, flags=re.IGNORECASE)
        query_text = re.sub(r"yesterday", "", query_text, flags=re.IGNORECASE)
        # Remove extra whitespace
        query_text = re.sub(r"\s+", " ", query_text).strip()
        return query_text

    def _parse_sort_options(self, query_text: str) -> SortOptions:
        """Parse sort options from query text."""
        sort_options = SortOptions()

        # Look for sort:field patterns
        sort_pattern = r"sort:(\w+)"
        sort_match = re.search(sort_pattern, query_text, re.IGNORECASE)
        if sort_match:
            sort_by = sort_match.group(1).lower()
            if sort_by in ["relevance", "date", "confidence"]:
                sort_options.sort_by = sort_by

        # Look for order:direction patterns
        order_pattern = r"order:(asc|desc)"
        order_match = re.search(order_pattern, query_text, re.IGNORECASE)
        if order_match:
            sort_options.sort_order = order_match.group(1).lower()

        return sort_options

    def _remove_sort_syntax(self, query_text: str) -> str:
        """Remove sort syntax from query text."""
        query_text = re.sub(r"sort:\w+", "", query_text, flags=re.IGNORECASE)
        query_text = re.sub(r"order:(asc|desc)", "", query_text, flags=re.IGNORECASE)
        # Remove extra whitespace
        query_text = re.sub(r"\s+", " ", query_text).strip()
        return query_text