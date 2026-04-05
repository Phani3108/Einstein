"""API models for search-related endpoints."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import DateRange, EntityFilter, SearchQuery, SortOptions, Pagination
from src.domain.entities.search_result import SearchMatch, SearchResult, SearchScore
from src.domain.entities.search_result import SearchResponse as DomainSearchResponse
from src.domain.entities.semantic_entry import SemanticEntry
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


class EntityFilterRequest(BaseModel):
    """Request model for entity filtering."""

    entity_types: List[EntityType] = Field(default_factory=list)
    entity_values: List[str] = Field(default_factory=list)

    def to_domain(self) -> EntityFilter:
        """Convert to domain EntityFilter."""
        return EntityFilter(
            entity_types=self.entity_types,
            entity_values=self.entity_values,
        )


class SortOptionsRequest(BaseModel):
    """Request model for sort options."""

    sort_by: str = "relevance"
    sort_order: str = "desc"

    @validator("sort_by")
    def validate_sort_by(cls, v: str) -> str:
        """Validate that sort_by is one of the allowed values."""
        allowed_values = ["relevance", "date", "confidence"]
        if v not in allowed_values:
            raise ValueError(f"sort_by must be one of {allowed_values}")
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v: str) -> str:
        """Validate that sort_order is one of the allowed values."""
        allowed_values = ["asc", "desc"]
        if v not in allowed_values:
            raise ValueError(f"sort_order must be one of {allowed_values}")
        return v

    def to_domain(self) -> SortOptions:
        """Convert to domain SortOptions."""
        return SortOptions(
            sort_by=self.sort_by,
            sort_order=self.sort_order,
        )


class PaginationRequest(BaseModel):
    """Request model for pagination."""

    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)

    def to_domain(self) -> Pagination:
        """Convert to domain Pagination."""
        return Pagination(
            page=self.page,
            page_size=self.page_size,
        )


class SearchRequest(BaseModel):
    """Request model for search operations."""

    query_text: str = Field(..., min_length=1, description="The search query text")
    date_range: Optional[DateRangeRequest] = None
    entity_filter: Optional[EntityFilterRequest] = None
    sort_options: Optional[SortOptionsRequest] = None
    pagination: Optional[PaginationRequest] = None
    include_raw_content: bool = True
    highlight_matches: bool = True

    @validator("query_text")
    def query_text_not_empty(cls, v: str) -> str:
        """Validate that the query text is not empty."""
        if not v.strip():
            raise ValueError("Search query text cannot be empty")
        return v


class SearchSuggestionsRequest(BaseModel):
    """Request model for search suggestions."""

    query_text: str = Field(..., min_length=1, description="The partial query text")
    limit: int = Field(5, ge=1, le=20, description="Maximum number of suggestions")

    @validator("query_text")
    def query_text_not_empty(cls, v: str) -> str:
        """Validate that the query text is not empty."""
        if not v.strip():
            raise ValueError("Query text cannot be empty")
        return v


class EntityListRequest(BaseModel):
    """Request model for entity listing."""

    entity_types: Optional[List[EntityType]] = None
    limit: int = Field(100, ge=1, le=1000)
    skip: int = Field(0, ge=0)


class SearchMatchResponse(BaseModel):
    """Response model for search matches."""

    field: str
    text: str
    start_position: int
    end_position: int
    highlight: str

    @classmethod
    def from_domain(cls, match: SearchMatch) -> "SearchMatchResponse":
        """Create from domain SearchMatch."""
        return cls(
            field=match.field,
            text=match.text,
            start_position=match.start_position,
            end_position=match.end_position,
            highlight=match.highlight,
        )


class SearchScoreResponse(BaseModel):
    """Response model for search scores."""

    semantic_similarity: float = Field(ge=0.0, le=1.0)
    keyword_match: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    final_score: float = Field(ge=0.0, le=1.0)

    @classmethod
    def from_domain(cls, score: SearchScore) -> "SearchScoreResponse":
        """Create from domain SearchScore."""
        return cls(
            semantic_similarity=score.semantic_similarity,
            keyword_match=score.keyword_match,
            recency_score=score.recency_score,
            confidence_score=score.confidence_score,
            final_score=score.final_score,
        )


class SearchResultResponse(BaseModel):
    """Response model for individual search results."""

    thought: ThoughtResponse
    matching_entities: List[SemanticEntryResponse] = Field(default_factory=list)
    matches: List[SearchMatchResponse] = Field(default_factory=list)
    score: SearchScoreResponse
    rank: int

    @classmethod
    def from_domain(cls, result: SearchResult) -> "SearchResultResponse":
        """Create from domain SearchResult."""
        return cls(
            thought=ThoughtResponse.from_domain(result.thought),
            matching_entities=[
                SemanticEntryResponse.from_domain(entity)
                for entity in result.matching_entities
            ],
            matches=[
                SearchMatchResponse.from_domain(match)
                for match in result.matches
            ],
            score=SearchScoreResponse.from_domain(result.score),
            rank=result.rank,
        )


class SearchResponse(BaseModel):
    """Response model for search operations."""

    results: List[SearchResultResponse] = Field(default_factory=list)
    total_count: int
    page: int
    page_size: int
    query_text: str
    search_time_ms: int
    suggestions: List[str] = Field(default_factory=list)

    @classmethod
    def from_domain(cls, response: DomainSearchResponse) -> "SearchResponse":
        """Create from domain SearchResponse."""
        return cls(
            results=[
                SearchResultResponse.from_domain(result)
                for result in response.results
            ],
            total_count=response.total_count,
            page=response.page,
            page_size=response.page_size,
            query_text=response.query_text,
            search_time_ms=response.search_time_ms,
            suggestions=response.suggestions,
        )


class SearchSuggestionsResponse(BaseModel):
    """Response model for search suggestions."""

    suggestions: List[str]
    query_text: str
    limit: int

    @classmethod
    def create(cls, suggestions: List[str], query_text: str, limit: int) -> "SearchSuggestionsResponse":
        """Create search suggestions response."""
        return cls(
            suggestions=suggestions,
            query_text=query_text,
            limit=limit,
        )


class EntitySummary(BaseModel):
    """Summary information for an entity."""

    entity_type: str
    entity_value: str
    count: int
    latest_occurrence: datetime
    confidence_avg: float


class EntityListResponse(BaseModel):
    """Response model for entity listing."""

    entities: List[EntitySummary]
    total_count: int
    entity_types_filter: Optional[List[str]] = None
    skip: int
    limit: int

    @classmethod
    def create(
        cls,
        entities: List[EntitySummary],
        total_count: int,
        entity_types_filter: Optional[List[EntityType]] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> "EntityListResponse":
        """Create entity list response."""
        return cls(
            entities=entities,
            total_count=total_count,
            entity_types_filter=[et.value for et in entity_types_filter] if entity_types_filter else None,
            skip=skip,
            limit=limit,
        )