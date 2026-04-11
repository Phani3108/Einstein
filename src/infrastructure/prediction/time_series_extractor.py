"""Time series extraction from Einstein database.

Extracts time series data from thoughts, context events, connections,
and profiles for forecasting purposes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Sequence
from uuid import UUID
import logging

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    Thought,
    SemanticEntry,
    ContextEventModel,
    ConnectionModel,
    PersonProfileModel,
    ProjectModel,
    Relationship,
)

logger = logging.getLogger(__name__)


@dataclass
class TimeSeriesData:
    """Container for extracted time series data."""

    name: str
    values: list[float]
    timestamps: list[datetime]
    granularity: str
    metadata: dict

    @property
    def length(self) -> int:
        """Number of data points in the series."""
        return len(self.values)

    def to_list(self) -> list[float]:
        """Get raw values for forecasting."""
        return self.values

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "values": self.values,
            "timestamps": [ts.isoformat() for ts in self.timestamps],
            "granularity": self.granularity,
            "metadata": self.metadata,
            "length": self.length,
        }


class TimeSeriesExtractor(ABC):
    """Base class for time series extractors."""

    def __init__(self, session: AsyncSession):
        """Initialize extractor with database session.

        Args:
            session: SQLAlchemy async session.
        """
        self._session = session

    @abstractmethod
    async def extract(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        **kwargs,
    ) -> TimeSeriesData:
        """Extract time series data for a user.

        Args:
            user_id: User identifier.
            start_date: Start of time range (defaults to 90 days ago).
            end_date: End of time range (defaults to now).

        Returns:
            TimeSeriesData with extracted values.
        """
        pass

    def _get_date_range(
        self,
        start_date: Optional[datetime],
        end_date: Optional[datetime],
        default_days: int = 90,
    ) -> tuple[datetime, datetime]:
        """Get date range with defaults."""
        end = end_date or datetime.utcnow()
        start = start_date or (end - timedelta(days=default_days))
        return start, end

    def _generate_date_buckets(
        self,
        start: datetime,
        end: datetime,
        granularity: str = "day",
    ) -> list[datetime]:
        """Generate date buckets for aggregation."""
        buckets = []
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)

        if granularity == "hour":
            delta = timedelta(hours=1)
            current = start.replace(minute=0, second=0, microsecond=0)
        elif granularity == "week":
            delta = timedelta(weeks=1)
            current = current - timedelta(days=current.weekday())
        else:
            delta = timedelta(days=1)

        while current <= end:
            buckets.append(current)
            current += delta

        return buckets


class ActivityExtractor(TimeSeriesExtractor):
    """Extract activity time series from thoughts and context events."""

    async def extract(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
        include_thoughts: bool = True,
        include_events: bool = True,
    ) -> TimeSeriesData:
        """Extract activity counts over time.

        Args:
            user_id: User identifier.
            start_date: Start of time range.
            end_date: End of time range.
            granularity: Time bucket size ("hour", "day", "week").
            include_thoughts: Include thought counts.
            include_events: Include context event counts.

        Returns:
            TimeSeriesData with activity counts per bucket.
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        thought_counts = {}
        event_counts = {}

        if include_thoughts:
            thought_counts = await self._get_thought_counts(
                user_id, start, end, granularity
            )

        if include_events:
            event_counts = await self._get_event_counts(
                user_id, start, end, granularity
            )

        values = []
        for bucket in buckets:
            count = thought_counts.get(bucket, 0) + event_counts.get(bucket, 0)
            values.append(float(count))

        return TimeSeriesData(
            name="activity",
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "include_thoughts": include_thoughts,
                "include_events": include_events,
                "total_count": sum(values),
            },
        )

    async def _get_thought_counts(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
        granularity: str,
    ) -> dict[datetime, int]:
        """Get thought counts per time bucket."""
        if granularity == "hour":
            trunc_func = func.date_trunc("hour", Thought.timestamp)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", Thought.timestamp)
        else:
            trunc_func = func.date_trunc("day", Thought.timestamp)

        stmt = (
            select(trunc_func.label("bucket"), func.count().label("count"))
            .where(
                and_(
                    Thought.user_id == user_id,
                    Thought.timestamp >= start,
                    Thought.timestamp <= end,
                )
            )
            .group_by(trunc_func)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        return {row.bucket: row.count for row in rows}

    async def _get_event_counts(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
        granularity: str,
    ) -> dict[datetime, int]:
        """Get context event counts per time bucket."""
        if granularity == "hour":
            trunc_func = func.date_trunc("hour", ContextEventModel.timestamp)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", ContextEventModel.timestamp)
        else:
            trunc_func = func.date_trunc("day", ContextEventModel.timestamp)

        stmt = (
            select(trunc_func.label("bucket"), func.count().label("count"))
            .where(
                and_(
                    ContextEventModel.user_id == user_id,
                    ContextEventModel.timestamp >= start,
                    ContextEventModel.timestamp <= end,
                )
            )
            .group_by(trunc_func)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        return {row.bucket: row.count for row in rows}

    async def extract_by_source(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> dict[str, TimeSeriesData]:
        """Extract activity counts broken down by event source.

        Returns separate time series for each event source (notification,
        phone, calendar, email, manual_note, thought).
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        if granularity == "hour":
            trunc_func = func.date_trunc("hour", ContextEventModel.timestamp)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", ContextEventModel.timestamp)
        else:
            trunc_func = func.date_trunc("day", ContextEventModel.timestamp)

        stmt = (
            select(
                trunc_func.label("bucket"),
                ContextEventModel.source,
                func.count().label("count"),
            )
            .where(
                and_(
                    ContextEventModel.user_id == user_id,
                    ContextEventModel.timestamp >= start,
                    ContextEventModel.timestamp <= end,
                )
            )
            .group_by(trunc_func, ContextEventModel.source)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        source_counts: dict[str, dict[datetime, int]] = {}
        for row in rows:
            if row.source not in source_counts:
                source_counts[row.source] = {}
            source_counts[row.source][row.bucket] = row.count

        thought_counts = await self._get_thought_counts(user_id, start, end, granularity)
        source_counts["thought"] = thought_counts

        series_dict = {}
        for source, counts in source_counts.items():
            values = [float(counts.get(bucket, 0)) for bucket in buckets]
            series_dict[source] = TimeSeriesData(
                name=f"activity_{source}",
                values=values,
                timestamps=buckets,
                granularity=granularity,
                metadata={
                    "user_id": str(user_id),
                    "source": source,
                    "total_count": sum(values),
                },
            )

        return series_dict


class EntityMentionExtractor(TimeSeriesExtractor):
    """Extract entity mention frequency time series."""

    async def extract(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        granularity: str = "day",
    ) -> TimeSeriesData:
        """Extract entity mention counts over time.

        Args:
            user_id: User identifier.
            start_date: Start of time range.
            end_date: End of time range.
            entity_type: Filter by entity type (person, organization, etc.).
            entity_value: Filter by specific entity value.
            granularity: Time bucket size.

        Returns:
            TimeSeriesData with mention counts per bucket.
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        if granularity == "hour":
            trunc_func = func.date_trunc("hour", SemanticEntry.extracted_at)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", SemanticEntry.extracted_at)
        else:
            trunc_func = func.date_trunc("day", SemanticEntry.extracted_at)

        conditions = [
            Thought.user_id == user_id,
            SemanticEntry.extracted_at >= start,
            SemanticEntry.extracted_at <= end,
        ]

        if entity_type:
            conditions.append(SemanticEntry.entity_type == entity_type)
        if entity_value:
            conditions.append(SemanticEntry.entity_value == entity_value)

        stmt = (
            select(trunc_func.label("bucket"), func.count().label("count"))
            .select_from(SemanticEntry)
            .join(Thought, Thought.id == SemanticEntry.thought_id)
            .where(and_(*conditions))
            .group_by(trunc_func)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        counts = {row.bucket: row.count for row in rows}
        values = [float(counts.get(bucket, 0)) for bucket in buckets]

        name = "entity_mentions"
        if entity_type:
            name = f"entity_mentions_{entity_type}"
        if entity_value:
            name = f"entity_{entity_value}"

        return TimeSeriesData(
            name=name,
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "entity_type": entity_type,
                "entity_value": entity_value,
                "total_mentions": sum(values),
            },
        )

    async def extract_top_entities(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        entity_type: Optional[str] = None,
        top_n: int = 10,
        granularity: str = "day",
    ) -> dict[str, TimeSeriesData]:
        """Extract time series for top N most mentioned entities.

        Returns separate time series for each top entity.
        """
        start, end = self._get_date_range(start_date, end_date)

        conditions = [
            Thought.user_id == user_id,
            SemanticEntry.extracted_at >= start,
            SemanticEntry.extracted_at <= end,
        ]
        if entity_type:
            conditions.append(SemanticEntry.entity_type == entity_type)

        top_stmt = (
            select(
                SemanticEntry.entity_type,
                SemanticEntry.entity_value,
                func.count().label("total"),
            )
            .select_from(SemanticEntry)
            .join(Thought, Thought.id == SemanticEntry.thought_id)
            .where(and_(*conditions))
            .group_by(SemanticEntry.entity_type, SemanticEntry.entity_value)
            .order_by(func.count().desc())
            .limit(top_n)
        )

        result = await self._session.execute(top_stmt)
        top_entities = result.fetchall()

        series_dict = {}
        for entity in top_entities:
            series = await self.extract(
                user_id=user_id,
                start_date=start,
                end_date=end,
                entity_type=entity.entity_type,
                entity_value=entity.entity_value,
                granularity=granularity,
            )
            key = f"{entity.entity_type}:{entity.entity_value}"
            series_dict[key] = series

        return series_dict


class ConnectionRateExtractor(TimeSeriesExtractor):
    """Extract connection formation rate time series."""

    async def extract(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        connection_type: Optional[str] = None,
        granularity: str = "day",
    ) -> TimeSeriesData:
        """Extract connection formation rate over time.

        Args:
            user_id: User identifier.
            start_date: Start of time range.
            end_date: End of time range.
            connection_type: Filter by connection type.
            granularity: Time bucket size.

        Returns:
            TimeSeriesData with new connections per bucket.
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        if granularity == "hour":
            trunc_func = func.date_trunc("hour", ConnectionModel.discovered_at)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", ConnectionModel.discovered_at)
        else:
            trunc_func = func.date_trunc("day", ConnectionModel.discovered_at)

        conditions = [
            ConnectionModel.user_id == user_id,
            ConnectionModel.discovered_at >= start,
            ConnectionModel.discovered_at <= end,
        ]

        if connection_type:
            conditions.append(ConnectionModel.connection_type == connection_type)

        stmt = (
            select(trunc_func.label("bucket"), func.count().label("count"))
            .where(and_(*conditions))
            .group_by(trunc_func)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        counts = {row.bucket: row.count for row in rows}
        values = [float(counts.get(bucket, 0)) for bucket in buckets]

        return TimeSeriesData(
            name="connection_rate",
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "connection_type": connection_type,
                "total_connections": sum(values),
            },
        )

    async def extract_entity_relationships(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> TimeSeriesData:
        """Extract semantic entity relationship formation rate."""
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        if granularity == "hour":
            trunc_func = func.date_trunc("hour", Relationship.created_at)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", Relationship.created_at)
        else:
            trunc_func = func.date_trunc("day", Relationship.created_at)

        stmt = (
            select(trunc_func.label("bucket"), func.count().label("count"))
            .select_from(Relationship)
            .join(SemanticEntry, SemanticEntry.id == Relationship.source_entity_id)
            .join(Thought, Thought.id == SemanticEntry.thought_id)
            .where(
                and_(
                    Thought.user_id == user_id,
                    Relationship.created_at >= start,
                    Relationship.created_at <= end,
                )
            )
            .group_by(trunc_func)
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        counts = {row.bucket: row.count for row in rows}
        values = [float(counts.get(bucket, 0)) for bucket in buckets]

        return TimeSeriesData(
            name="entity_relationship_rate",
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "total_relationships": sum(values),
            },
        )


class ProfileMetricsExtractor(TimeSeriesExtractor):
    """Extract person and project engagement metrics time series."""

    async def extract(
        self,
        user_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> TimeSeriesData:
        """Extract overall profile activity (people interactions).

        Args:
            user_id: User identifier.
            start_date: Start of time range.
            end_date: End of time range.
            granularity: Time bucket size.

        Returns:
            TimeSeriesData with people interaction counts per bucket.
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        if granularity == "hour":
            trunc_func = func.date_trunc("hour", ContextEventModel.timestamp)
        elif granularity == "week":
            trunc_func = func.date_trunc("week", ContextEventModel.timestamp)
        else:
            trunc_func = func.date_trunc("day", ContextEventModel.timestamp)

        stmt = (
            select(
                trunc_func.label("bucket"),
                func.count(func.distinct(func.unnest(ContextEventModel.extracted_people))).label("count"),
            )
            .where(
                and_(
                    ContextEventModel.user_id == user_id,
                    ContextEventModel.timestamp >= start,
                    ContextEventModel.timestamp <= end,
                    ContextEventModel.extracted_people != None,
                )
            )
            .group_by(trunc_func)
        )

        try:
            result = await self._session.execute(stmt)
            rows = result.fetchall()
            counts = {row.bucket: row.count for row in rows}
        except Exception as e:
            logger.warning(f"Complex query failed, falling back: {e}")
            counts = await self._get_people_interaction_counts_fallback(
                user_id, start, end, buckets, granularity
            )

        values = [float(counts.get(bucket, 0)) for bucket in buckets]

        return TimeSeriesData(
            name="people_interactions",
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "total_interactions": sum(values),
            },
        )

    async def _get_people_interaction_counts_fallback(
        self,
        user_id: UUID,
        start: datetime,
        end: datetime,
        buckets: list[datetime],
        granularity: str,
    ) -> dict[datetime, int]:
        """Fallback method for counting people interactions."""
        stmt = select(
            ContextEventModel.timestamp,
            ContextEventModel.extracted_people,
        ).where(
            and_(
                ContextEventModel.user_id == user_id,
                ContextEventModel.timestamp >= start,
                ContextEventModel.timestamp <= end,
            )
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        counts: dict[datetime, int] = {}
        for row in rows:
            if not row.extracted_people:
                continue

            if granularity == "hour":
                bucket = row.timestamp.replace(minute=0, second=0, microsecond=0)
            elif granularity == "week":
                bucket = row.timestamp - timedelta(days=row.timestamp.weekday())
                bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                bucket = row.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

            if bucket not in counts:
                counts[bucket] = 0
            counts[bucket] += len(row.extracted_people)

        return counts

    async def extract_person_activity(
        self,
        user_id: UUID,
        person_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        granularity: str = "day",
    ) -> TimeSeriesData:
        """Extract activity time series for a specific person.

        Args:
            user_id: User identifier.
            person_name: Name of the person to track.
            start_date: Start of time range.
            end_date: End of time range.
            granularity: Time bucket size.

        Returns:
            TimeSeriesData with interaction counts for the person.
        """
        start, end = self._get_date_range(start_date, end_date)
        buckets = self._generate_date_buckets(start, end, granularity)

        stmt = select(
            ContextEventModel.timestamp,
            ContextEventModel.extracted_people,
        ).where(
            and_(
                ContextEventModel.user_id == user_id,
                ContextEventModel.timestamp >= start,
                ContextEventModel.timestamp <= end,
            )
        )

        result = await self._session.execute(stmt)
        rows = result.fetchall()

        counts: dict[datetime, int] = {}
        person_lower = person_name.lower()

        for row in rows:
            if not row.extracted_people:
                continue

            matching = [
                p for p in row.extracted_people if person_lower in p.lower()
            ]
            if not matching:
                continue

            if granularity == "hour":
                bucket = row.timestamp.replace(minute=0, second=0, microsecond=0)
            elif granularity == "week":
                bucket = row.timestamp - timedelta(days=row.timestamp.weekday())
                bucket = bucket.replace(hour=0, minute=0, second=0, microsecond=0)
            else:
                bucket = row.timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

            if bucket not in counts:
                counts[bucket] = 0
            counts[bucket] += len(matching)

        values = [float(counts.get(bucket, 0)) for bucket in buckets]

        return TimeSeriesData(
            name=f"person_activity_{person_name}",
            values=values,
            timestamps=buckets,
            granularity=granularity,
            metadata={
                "user_id": str(user_id),
                "person_name": person_name,
                "total_interactions": sum(values),
            },
        )

    async def get_dormancy_at_risk(
        self,
        user_id: UUID,
        dormancy_threshold_days: int = 14,
    ) -> list[dict]:
        """Get people and projects at risk of becoming dormant.

        Args:
            user_id: User identifier.
            dormancy_threshold_days: Days threshold for dormancy risk.

        Returns:
            List of entities at risk with their metrics.
        """
        at_risk = []

        people_stmt = select(PersonProfileModel).where(
            and_(
                PersonProfileModel.user_id == user_id,
                PersonProfileModel.dormancy_days >= dormancy_threshold_days // 2,
            )
        )
        people_result = await self._session.execute(people_stmt)
        people = people_result.scalars().all()

        for person in people:
            at_risk.append({
                "type": "person",
                "id": str(person.id),
                "name": person.name,
                "dormancy_days": person.dormancy_days,
                "freshness_score": person.freshness_score,
                "last_seen": person.last_seen.isoformat() if person.last_seen else None,
                "days_until_dormant": max(0, dormancy_threshold_days - person.dormancy_days),
                "risk_level": "critical" if person.dormancy_days >= dormancy_threshold_days else "high" if person.dormancy_days >= dormancy_threshold_days * 3 // 4 else "medium",
            })

        projects_stmt = select(ProjectModel).where(
            and_(
                ProjectModel.user_id == user_id,
                ProjectModel.dormancy_days >= dormancy_threshold_days // 2,
                ProjectModel.status == "active",
            )
        )
        projects_result = await self._session.execute(projects_stmt)
        projects = projects_result.scalars().all()

        for project in projects:
            at_risk.append({
                "type": "project",
                "id": str(project.id),
                "name": project.title,
                "dormancy_days": project.dormancy_days,
                "last_activity_at": (
                    project.last_activity_at.isoformat()
                    if project.last_activity_at
                    else None
                ),
                "days_until_dormant": max(0, dormancy_threshold_days - project.dormancy_days),
                "risk_level": "critical" if project.dormancy_days >= dormancy_threshold_days else "high" if project.dormancy_days >= dormancy_threshold_days * 3 // 4 else "medium",
            })

        at_risk.sort(key=lambda x: x["days_until_dormant"])
        return at_risk
