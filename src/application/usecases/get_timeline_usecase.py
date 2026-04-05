"""Get timeline use case for the Personal Semantic Engine."""

from typing import Optional
from uuid import UUID

from src.domain.entities.timeline import (
    DateRange,
    Pagination,
    TimelineFilter,
    TimelineQuery,
    TimelineResponse,
    TimelineSummary,
)
from src.domain.exceptions import TimelineError, TimelineQueryError
from src.domain.repositories.timeline_repository import TimelineRepository


class GetTimelineUseCase:
    """Use case for retrieving user timeline data."""

    def __init__(self, timeline_repository: TimelineRepository):
        """Initialize the use case with required dependencies.

        Args:
            timeline_repository: Repository for timeline operations
        """
        self._timeline_repository = timeline_repository

    async def execute(
        self,
        user_id: UUID,
        date_range: Optional[DateRange] = None,
        entity_types: Optional[list] = None,
        data_sources: Optional[list] = None,
        tags: Optional[list] = None,
        page: int = 1,
        page_size: int = 20,
        sort_order: str = "desc",
    ) -> TimelineResponse:
        """Execute timeline retrieval with filtering and pagination.

        Args:
            user_id: The ID of the user requesting timeline
            date_range: Optional date range filter
            entity_types: Optional list of entity types to filter by
            data_sources: Optional list of data sources to filter by
            tags: Optional list of tags to filter by
            page: Page number for pagination
            page_size: Number of items per page
            sort_order: Sort order ("asc" or "desc")

        Returns:
            Timeline response with entries and metadata

        Raises:
            TimelineQueryError: If query parameters are invalid
            TimelineError: If timeline retrieval fails
        """
        try:
            # Validate input parameters
            if page < 1:
                raise TimelineQueryError("Page number must be greater than 0")
            
            if page_size < 1 or page_size > 100:
                raise TimelineQueryError("Page size must be between 1 and 100")
            
            if sort_order not in ["asc", "desc"]:
                raise TimelineQueryError("Sort order must be 'asc' or 'desc'")

            # Build timeline filter
            timeline_filter = None
            if any([date_range, entity_types, data_sources, tags]):
                timeline_filter = TimelineFilter(
                    entity_types=entity_types or [],
                    date_range=date_range,
                    data_sources=data_sources or [],
                    tags=tags or [],
                )

            # Build timeline query
            query = TimelineQuery(
                user_id=str(user_id),
                filters=timeline_filter,
                pagination=Pagination(page=page, page_size=page_size),
                sort_order=sort_order,
            )

            # Execute timeline retrieval
            timeline_response = await self._timeline_repository.get_timeline(query)

            return timeline_response

        except TimelineQueryError:
            # Re-raise query errors as-is
            raise
        except Exception as e:
            raise TimelineError(f"Timeline retrieval failed: {str(e)}")

    async def get_summary(self, user_id: UUID) -> TimelineSummary:
        """Get timeline summary statistics for a user.

        Args:
            user_id: The ID of the user to get summary for

        Returns:
            Timeline summary with statistics

        Raises:
            TimelineError: If summary generation fails
        """
        try:
            summary = await self._timeline_repository.get_timeline_summary(str(user_id))
            return summary

        except Exception as e:
            raise TimelineError(f"Timeline summary generation failed: {str(e)}")

    async def get_related_entries(
        self, entry_id: str, user_id: UUID, limit: int = 10
    ) -> list:
        """Get entries related to a specific timeline entry.

        Args:
            entry_id: ID of the entry to find relations for
            user_id: User ID to scope the search
            limit: Maximum number of related entries to return

        Returns:
            List of related timeline entries

        Raises:
            TimelineError: If relation finding fails
        """
        try:
            if limit < 1 or limit > 50:
                raise TimelineQueryError("Limit must be between 1 and 50")

            related_entries = await self._timeline_repository.find_related_entries(
                entry_id=entry_id,
                user_id=str(user_id),
                limit=limit,
            )

            return related_entries

        except TimelineQueryError:
            # Re-raise query errors as-is
            raise
        except Exception as e:
            raise TimelineError(f"Related entries retrieval failed: {str(e)}")