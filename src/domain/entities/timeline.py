"""Timeline domain entities for the Personal Semantic Engine."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.entities.enums import EntityType
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought


class DateRange(BaseModel):
    """Date range for timeline filtering."""

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

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineFilter(BaseModel):
    """Filters for timeline queries."""

    entity_types: List[EntityType] = Field(default_factory=list)
    date_range: Optional[DateRange] = None
    data_sources: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        frozen = True


class Pagination(BaseModel):
    """Pagination parameters for timeline queries."""

    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineQuery(BaseModel):
    """Query parameters for timeline requests."""

    user_id: str
    filters: Optional[TimelineFilter] = None
    pagination: Optional[Pagination] = None
    sort_order: str = Field("desc", pattern="^(asc|desc)$")

    @validator("user_id")
    def user_id_not_empty(cls, v: str) -> str:
        """Validate that user_id is not empty."""
        if not v.strip():
            raise ValueError("User ID cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        frozen = True


class EntityConnection(BaseModel):
    """Connection between entities in timeline."""

    entity_id: UUID
    entity_type: EntityType
    entity_value: str
    confidence: float = Field(ge=0.0, le=1.0)
    relationship_type: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineEntry(BaseModel):
    """A single entry in the timeline."""

    id: UUID
    thought: Thought
    timestamp: datetime
    entities: List[SemanticEntry] = Field(default_factory=list)
    connections: List[EntityConnection] = Field(default_factory=list)
    grouped_with: List[UUID] = Field(default_factory=list)  # IDs of related entries
    data_source: str = "thought"  # For future external API integrations

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineGroup(BaseModel):
    """A group of related timeline entries."""

    id: UUID
    entries: List[TimelineEntry]
    primary_timestamp: datetime
    group_type: str  # "temporal", "entity", "location", etc.
    common_entities: List[EntityConnection] = Field(default_factory=list)
    summary: Optional[str] = None

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineSummary(BaseModel):
    """Summary statistics for a timeline."""

    total_entries: int
    date_range: DateRange
    entity_counts: Dict[str, int] = Field(default_factory=dict)  # entity_type -> count
    most_active_periods: List[Dict[str, str]] = Field(default_factory=list)
    top_entities: List[Dict[str, str]] = Field(default_factory=list)

    class Config:
        """Pydantic configuration."""

        frozen = True


class TimelineResponse(BaseModel):
    """Response for timeline queries."""

    entries: List[TimelineEntry] = Field(default_factory=list)
    groups: List[TimelineGroup] = Field(default_factory=list)
    total_count: int
    page: int
    page_size: int
    has_next: bool
    has_previous: bool
    summary: Optional[TimelineSummary] = None

    class Config:
        """Pydantic configuration."""

        frozen = True