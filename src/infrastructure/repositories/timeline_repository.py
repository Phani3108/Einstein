"""Timeline repository implementation for the Personal Semantic Engine."""

from datetime import datetime, timedelta
from typing import Dict, List
from uuid import UUID, uuid4

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.timeline import (
    EntityConnection,
    TimelineEntry,
    TimelineGroup,
    TimelineQuery,
    TimelineResponse,
    TimelineSummary,
    DateRange,
)
from src.domain.entities.thought import Thought
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.exceptions import TimelineError, TimelineGroupingError
from src.domain.repositories.timeline_repository import TimelineRepository
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    SemanticEntry as SemanticEntryModel,
    Thought as ThoughtModel,
)


class PostgreSQLTimelineRepository(TimelineRepository):
    """PostgreSQL implementation of timeline repository."""

    def __init__(self, database: Database):
        """Initialize the repository with database connection.

        Args:
            database: Database connection manager
        """
        self._database = database

    async def get_timeline(self, query: TimelineQuery) -> TimelineResponse:
        """Get timeline entries based on query parameters.

        Args:
            query: Timeline query with filters and pagination

        Returns:
            Timeline response with entries and metadata

        Raises:
            TimelineError: If timeline retrieval fails
        """
        try:
            async with self._database.session() as session:
                # Build base query
                base_query = (
                    select(ThoughtModel)
                    .where(ThoughtModel.user_id == UUID(query.user_id))
                )

                # Apply date range filter
                if query.filters and query.filters.date_range:
                    if query.filters.date_range.start_date:
                        base_query = base_query.where(
                            ThoughtModel.timestamp >= query.filters.date_range.start_date
                        )
                    if query.filters.date_range.end_date:
                        base_query = base_query.where(
                            ThoughtModel.timestamp <= query.filters.date_range.end_date
                        )

                # Apply entity type filter
                if query.filters and query.filters.entity_types:
                    entity_subquery = (
                        select(SemanticEntryModel.thought_id)
                        .where(
                            SemanticEntryModel.entity_type.in_(
                                [et.value for et in query.filters.entity_types]
                            )
                        )
                    )
                    base_query = base_query.where(
                        ThoughtModel.id.in_(entity_subquery)
                    )

                # Apply tags filter
                if query.filters and query.filters.tags:
                    # Filter by tags in metadata
                    for tag in query.filters.tags:
                        base_query = base_query.where(
                            ThoughtModel.metadata.op("@>")({
                                "tags": [tag]
                            })
                        )

                # Apply sorting
                if query.sort_order == "desc":
                    base_query = base_query.order_by(desc(ThoughtModel.timestamp))
                else:
                    base_query = base_query.order_by(ThoughtModel.timestamp)

                # Get total count
                count_query = select(func.count()).select_from(base_query.subquery())
                count_result = await session.execute(count_query)
                total_count = count_result.scalar()

                # Apply pagination
                if query.pagination:
                    offset = (query.pagination.page - 1) * query.pagination.page_size
                    base_query = base_query.offset(offset).limit(query.pagination.page_size)

                # Execute query
                result = await session.execute(base_query)
                thought_models = result.scalars().all()

                # Convert to timeline entries
                timeline_entries = []
                for thought_model in thought_models:
                    # Get semantic entries for this thought
                    entities_query = select(SemanticEntryModel).where(
                        SemanticEntryModel.thought_id == thought_model.id
                    )
                    entities_result = await session.execute(entities_query)
                    entity_models = entities_result.scalars().all()

                    # Convert to domain objects
                    thought = thought_model.to_domain()
                    entities = [entity_model.to_domain() for entity_model in entity_models]

                    # Create entity connections
                    connections = [
                        EntityConnection(
                            entity_id=entity.id,
                            entity_type=entity.entity_type,
                            entity_value=entity.entity_value,
                            confidence=entity.confidence,
                        )
                        for entity in entities
                    ]

                    # Create timeline entry
                    timeline_entry = TimelineEntry(
                        id=thought.id,
                        thought=thought,
                        timestamp=thought.timestamp,
                        entities=entities,
                        connections=connections,
                        grouped_with=[],
                        data_source="thought",
                    )
                    timeline_entries.append(timeline_entry)

                # Calculate pagination metadata
                page = query.pagination.page if query.pagination else 1
                page_size = query.pagination.page_size if query.pagination else len(timeline_entries)
                has_next = (page * page_size) < total_count
                has_previous = page > 1

                return TimelineResponse(
                    entries=timeline_entries,
                    groups=[],  # Groups will be populated if requested
                    total_count=total_count,
                    page=page,
                    page_size=page_size,
                    has_next=has_next,
                    has_previous=has_previous,
                )

        except Exception as e:
            raise TimelineError(f"Timeline retrieval failed: {str(e)}")

    async def get_timeline_summary(self, user_id: str) -> TimelineSummary:
        """Get summary statistics for user's timeline.

        Args:
            user_id: The user ID to get summary for

        Returns:
            Timeline summary with statistics

        Raises:
            TimelineError: If summary generation fails
        """
        try:
            async with self._database.session() as session:
                # Get total entries count
                total_query = select(func.count(ThoughtModel.id)).where(
                    ThoughtModel.user_id == UUID(user_id)
                )
                total_result = await session.execute(total_query)
                total_entries = total_result.scalar()

                # Get date range
                date_range_query = select(
                    func.min(ThoughtModel.timestamp),
                    func.max(ThoughtModel.timestamp)
                ).where(ThoughtModel.user_id == UUID(user_id))
                date_result = await session.execute(date_range_query)
                min_date, max_date = date_result.first()

                # Get entity counts by type
                entity_counts_query = (
                    select(
                        SemanticEntryModel.entity_type,
                        func.count(SemanticEntryModel.id)
                    )
                    .join(ThoughtModel, SemanticEntryModel.thought_id == ThoughtModel.id)
                    .where(ThoughtModel.user_id == UUID(user_id))
                    .group_by(SemanticEntryModel.entity_type)
                )
                entity_counts_result = await session.execute(entity_counts_query)
                entity_counts = {
                    entity_type: count
                    for entity_type, count in entity_counts_result.fetchall()
                }

                # Get most active periods (by day)
                active_periods_query = (
                    select(
                        func.date(ThoughtModel.timestamp).label("date"),
                        func.count(ThoughtModel.id).label("count")
                    )
                    .where(ThoughtModel.user_id == UUID(user_id))
                    .group_by(func.date(ThoughtModel.timestamp))
                    .order_by(func.count(ThoughtModel.id).desc())
                    .limit(5)
                )
                active_periods_result = await session.execute(active_periods_query)
                most_active_periods = [
                    {"date": str(date), "count": str(count)}
                    for date, count in active_periods_result.fetchall()
                ]

                # Get top entities by frequency
                top_entities_query = (
                    select(
                        SemanticEntryModel.entity_value,
                        SemanticEntryModel.entity_type,
                        func.count(SemanticEntryModel.id).label("count")
                    )
                    .join(ThoughtModel, SemanticEntryModel.thought_id == ThoughtModel.id)
                    .where(ThoughtModel.user_id == UUID(user_id))
                    .group_by(SemanticEntryModel.entity_value, SemanticEntryModel.entity_type)
                    .order_by(func.count(SemanticEntryModel.id).desc())
                    .limit(10)
                )
                top_entities_result = await session.execute(top_entities_query)
                top_entities = [
                    {
                        "entity_value": entity_value,
                        "entity_type": entity_type,
                        "count": str(count)
                    }
                    for entity_value, entity_type, count in top_entities_result.fetchall()
                ]

                return TimelineSummary(
                    total_entries=total_entries,
                    date_range=DateRange(
                        start_date=min_date,
                        end_date=max_date
                    ),
                    entity_counts=entity_counts,
                    most_active_periods=most_active_periods,
                    top_entities=top_entities,
                )

        except Exception as e:
            raise TimelineError(f"Timeline summary generation failed: {str(e)}")

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
            TimelineGroupingError: If grouping fails
        """
        try:
            if group_type == "temporal":
                return await self._group_by_temporal(entries)
            elif group_type == "entity":
                return await self._group_by_entity(entries)
            elif group_type == "location":
                return await self._group_by_location(entries)
            else:
                raise TimelineGroupingError(f"Unsupported group type: {group_type}")

        except Exception as e:
            raise TimelineGroupingError(f"Timeline grouping failed: {str(e)}")

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
        try:
            async with self._database.session() as session:
                # Get the target entry
                target_query = select(ThoughtModel).where(
                    and_(
                        ThoughtModel.id == UUID(entry_id),
                        ThoughtModel.user_id == UUID(user_id)
                    )
                )
                target_result = await session.execute(target_query)
                target_thought = target_result.scalar_one_or_none()

                if not target_thought:
                    return []

                # Get entities from target entry
                target_entities_query = select(SemanticEntryModel).where(
                    SemanticEntryModel.thought_id == UUID(entry_id)
                )
                target_entities_result = await session.execute(target_entities_query)
                target_entities = target_entities_result.scalars().all()

                if not target_entities:
                    return []

                # Find thoughts with similar entities
                entity_values = [entity.entity_value for entity in target_entities]
                entity_types = [entity.entity_type for entity in target_entities]

                related_query = (
                    select(ThoughtModel)
                    .join(SemanticEntryModel, SemanticEntryModel.thought_id == ThoughtModel.id)
                    .where(
                        and_(
                            ThoughtModel.user_id == UUID(user_id),
                            ThoughtModel.id != UUID(entry_id),
                            or_(
                                SemanticEntryModel.entity_value.in_(entity_values),
                                SemanticEntryModel.entity_type.in_(entity_types)
                            )
                        )
                    )
                    .distinct()
                    .order_by(desc(ThoughtModel.timestamp))
                    .limit(limit)
                )

                related_result = await session.execute(related_query)
                related_thoughts = related_result.scalars().all()

                # Convert to timeline entries
                related_entries = []
                for thought_model in related_thoughts:
                    # Get entities for this thought
                    entities_query = select(SemanticEntryModel).where(
                        SemanticEntryModel.thought_id == thought_model.id
                    )
                    entities_result = await session.execute(entities_query)
                    entity_models = entities_result.scalars().all()

                    # Convert to domain objects
                    thought = thought_model.to_domain()
                    entities = [entity_model.to_domain() for entity_model in entity_models]

                    # Create entity connections
                    connections = [
                        EntityConnection(
                            entity_id=entity.id,
                            entity_type=entity.entity_type,
                            entity_value=entity.entity_value,
                            confidence=entity.confidence,
                        )
                        for entity in entities
                    ]

                    # Create timeline entry
                    timeline_entry = TimelineEntry(
                        id=thought.id,
                        thought=thought,
                        timestamp=thought.timestamp,
                        entities=entities,
                        connections=connections,
                        grouped_with=[],
                        data_source="thought",
                    )
                    related_entries.append(timeline_entry)

                return related_entries

        except Exception as e:
            raise TimelineError(f"Related entries search failed: {str(e)}")

    async def _group_by_temporal(self, entries: List[TimelineEntry]) -> List[TimelineGroup]:
        """Group entries by temporal proximity (same day)."""
        groups = {}
        
        for entry in entries:
            date_key = entry.timestamp.date()
            
            if date_key not in groups:
                groups[date_key] = []
            groups[date_key].append(entry)
        
        timeline_groups = []
        for date_key, group_entries in groups.items():
            if len(group_entries) > 1:  # Only create groups with multiple entries
                # Find common entities
                all_entities = []
                for entry in group_entries:
                    all_entities.extend(entry.connections)
                
                # Count entity occurrences
                entity_counts = {}
                for entity in all_entities:
                    key = f"{entity.entity_type.value}:{entity.entity_value}"
                    entity_counts[key] = entity_counts.get(key, 0) + 1
                
                # Find common entities (appearing in multiple entries)
                common_entities = [
                    entity for entity in all_entities
                    if entity_counts[f"{entity.entity_type.value}:{entity.entity_value}"] > 1
                ]
                
                # Remove duplicates
                seen = set()
                unique_common_entities = []
                for entity in common_entities:
                    key = f"{entity.entity_type.value}:{entity.entity_value}"
                    if key not in seen:
                        seen.add(key)
                        unique_common_entities.append(entity)
                
                timeline_group = TimelineGroup(
                    id=uuid4(),
                    entries=group_entries,
                    primary_timestamp=min(entry.timestamp for entry in group_entries),
                    group_type="temporal",
                    common_entities=unique_common_entities,
                    summary=f"Activities on {date_key}",
                )
                timeline_groups.append(timeline_group)
        
        return timeline_groups

    async def _group_by_entity(self, entries: List[TimelineEntry]) -> List[TimelineGroup]:
        """Group entries by shared entities."""
        # This is a simplified implementation
        # In a full implementation, you'd use more sophisticated entity matching
        return []

    async def _group_by_location(self, entries: List[TimelineEntry]) -> List[TimelineGroup]:
        """Group entries by location."""
        # This is a simplified implementation
        # In a full implementation, you'd group by location metadata
        return []