"""Timeline repository interface for the Personal Semantic Engine."""

from abc import ABC, abstractmethod
from typing import List

from src.domain.entities.timeline import (
    TimelineEntry,
    TimelineGroup,
    TimelineQuery,
    TimelineResponse,
    TimelineSummary,
)


class TimelineRepository(ABC):
    """Abstract repository for timeline operations."""

    @abstractmethod
    async def get_timeline(self, query: TimelineQuery) -> TimelineResponse:
        """Get timeline entries based on query parameters.

        Args:
            query: Timeline query with filters and pagination

        Returns:
            Timeline response with entries and metadata

        Raises:
            TimelineError: If timeline retrieval fails
        """
        pass

    @abstractmethod
    async def get_timeline_summary(self, user_id: str) -> TimelineSummary:
        """Get summary statistics for user's timeline.

        Args:
            user_id: The user ID to get summary for

        Returns:
            Timeline summary with statistics

        Raises:
            TimelineError: If summary generation fails
        """
        pass

    @abstractmethod
    async def group_timeline_entries(
        self, entries: List[TimelineEntry], group_type: str = "temporal"
    ) -> List[TimelineGroup]:
        """Group timeline entries by specified criteria.

        Args:
            entries: List of timeline entries to group
            group_type: Type of grouping ("temporal", "entity", "location")

        Returns:
            List of timeline groups

        Raises:
            TimelineError: If grouping fails
        """
        pass

    @abstractmethod
    async def find_related_entries(
        self, entry_id: str, user_id: str, limit: int = 10
    ) -> List[TimelineEntry]:
        """Find entries related to a specific timeline entry.

        Args:
            entry_id: ID of the entry to find relations for
            user_id: User ID to scope the search
            limit: Maximum number of related entries to return

        Returns:
            List of related timeline entries

        Raises:
            TimelineError: If relation finding fails
        """
        pass