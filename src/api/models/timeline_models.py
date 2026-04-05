"""API models for timeline-related endpoints."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.entities.enums import EntityType
from src.domain.entities.timeline import (
    DateRange,
    EntityConnection,
    TimelineEntry,
    TimelineFilter,
    TimelineGroup,
    TimelineResponse,
    TimelineSummary,
)
from src.api.models.thought_models import ThoughtResponse, SemanticEntryResponse


class DateRangeRequest(BaseModel):
    """Request model for date range filtering."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator("end_date")
    def end_date_after_start_date(
        cls, v: Optional[datetime], values: Dict
    ) -> Optional[datetime]:
        """Validate that end_date is after start_date if both are provided."""
        if v is not None and values.get("start_date") is not None:
            if v < values["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v

    def to_domain(self) -> DateRange:
        """Convert to domain DateRange."""
        return DateRange(
            start_date=self.start_date,
            end_date=self.end_date,
        )


class TimelineFilterRequest(BaseModel):
    """Request model for timeline filtering."""

    entity_types: List[EntityType] = Field(default_factory=list)
    date_range: Optional[DateRangeRequest] = None
    data_sources: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    def to_domain(self) -> TimelineFilter:
        """Convert to domain TimelineFilter."""
        return TimelineFilter(
            entity_types=self.entity_types,
            date_range=self.date_range.to_domain() if self.date_range else None,
            data_sources=self.data_sources,
            tags=self.tags,
        )


class EntityConnectionResponse(BaseModel):
    """Response model for entity connections."""

    entity_id: UUID
    entity_type: str
    entity_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    relationship_type: Optional[str] = None

    @classmethod
    def from_domain(cls, connection: EntityConnection) -> "EntityConnectionResponse":
        """Create from domain EntityConnection."""
        return cls(
            entity_id=connection.entity_id,
            entity_type=connection.entity_type.value,
            entity_value=connection.entity_value,
            confidence=connection.confidence,
            relationship_type=connection.relationship_type,
        )


class TimelineEntryResponse(BaseModel):
    """Response model for timeline entries."""

    id: UUID
    thought: ThoughtResponse
    timestamp: datetime
    entities: List[SemanticEntryResponse] = Field(default_factory=list)
    connections: List[EntityConnectionResponse] = Field(default_factory=list)
    grouped_with: List[UUID] = Field(default_factory=list)
    data_source: str = "thought"

    @classmethod
    def from_domain(cls, entry: TimelineEntry) -> "TimelineEntryResponse":
        """Create from domain TimelineEntry."""
        return cls(
            id=entry.id,
            thought=ThoughtResponse.from_domain(entry.thought),
            timestamp=entry.timestamp,
            entities=[
                SemanticEntryResponse.from_domain(entity)
                for entity in entry.entities
            ],
            connections=[
                EntityConnectionResponse.from_domain(connection)
                for connection in entry.connections
            ],
            grouped_with=entry.grouped_with,
            data_source=entry.data_source,
        )


class TimelineGroupResponse(BaseModel):
    """Response model for timeline groups."""

    id: UUID
    entries: List[TimelineEntryResponse]
    primary_timestamp: datetime
    group_type: str
    common_entities: List[EntityConnectionResponse] = Field(default_factory=list)
    summary: Optional[str] = None

    @classmethod
    def from_domain(cls, group: TimelineGroup) -> "TimelineGroupResponse":
        """Create from domain TimelineGroup."""
        return cls(
            id=group.id,
            entries=[
                TimelineEntryResponse.from_domain(entry)
                for entry in group.entries
            ],
            primary_timestamp=group.primary_timestamp,
            group_type=group.group_type,
            common_entities=[
                EntityConnectionResponse.from_domain(entity)
                for entity in group.common_entities
            ],
            summary=group.summary,
        )


class TimelineSummaryResponse(BaseModel):
    """Response model for timeline summary."""

    total_entries: int
    date_range: DateRangeRequest
    entity_counts: Dict[str, int] = Field(default_factory=dict)
    most_active_periods: List[Dict[str, str]] = Field(default_factory=list)
    top_entities: List[Dict[str, str]] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, summary: TimelineSummary) -> "TimelineSummaryResponse":
        """Create from domain TimelineSummary."""
        return cls(
            total_entries=summary.total_entries,
            date_range=DateRangeRequest(
                start_date=summary.date_range.start_date,
                end_date=summary.date_range.end_date,
            ),
            entity_counts=summary.entity_counts,
            most_active_periods=summary.most_active_periods,
            top_entities=summary.top_entities,
        )


class TimelineResponse(BaseModel):
    """Response model for timeline queries."""

    entries: List[TimelineEntryResponse] = Field(default_factory=list)
    groups: List[TimelineGroupResponse] = Field(default_factory=list)
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    summary: Optional[TimelineSummaryResponse] = None

    @classmethod
    def from_domain(cls, response: TimelineResponse) -> "TimelineResponse":
        """Create from domain TimelineResponse."""
        return cls(
            entries=[
                TimelineEntryResponse.from_domain(entry)
                for entry in response.entries
            ],
            groups=[
                TimelineGroupResponse.from_domain(group)
                for group in response.groups
            ],
            total_count=response.total_count,
            page=response.page,
            page_size=response.page_size,
            has_next=response.has_next,
            has_previous=response.has_previous,
            summary=TimelineSummaryResponse.from_domain(response.summary) if response.summary else None,
        )


class TimelineRequest(BaseModel):
    """Request model for timeline queries."""

    filters: Optional[TimelineFilterRequest] = None
    page: int = Field(1, ge=1, description="Page number")
    page_size: int = Field(20, ge=1, le=100, description="Items per page")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort order")
    include_groups: bool = Field(False, description="Include grouped entries")
    include_summary: bool = Field(False, description="Include timeline summary")


class RelatedEntriesRequest(BaseModel):
    """Request model for related entries."""

    entry_id: str = Field(..., description="ID of the entry to find relations for")
    limit: int = Field(10, ge=1, le=50, description="Maximum number of related entries")


class RelatedEntriesResponse(BaseModel):
    """Response model for related entries."""

    entry_id: str
    related_entries: List[TimelineEntryResponse]
    total_count: int