"""Search query value objects for the Personal Semantic Engine."""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator

from src.domain.entities.enums import EntityType


class DateRange(BaseModel):
    """Date range for filtering search results."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    @validator("end_date")
    def end_date_after_start_date(
        cls, v: Optional[datetime], values: Dict
    ) -> Optional[datetime]:
        """Validate that end_date is after start_date if both are provided.

        Args:
            v: The end_date to validate
            values: The values dict containing start_date

        Returns:
            The validated end_date

        Raises:
            ValueError: If end_date is before start_date
        """
        if v is not None and values.get("start_date") is not None:
            if v < values["start_date"]:
                raise ValueError("end_date must be after start_date")
        return v


class EntityFilter(BaseModel):
    """Filter for specific entity types in search results."""

    entity_types: List[EntityType] = Field(default_factory=list)
    entity_values: List[str] = Field(default_factory=list)


class SortOptions(BaseModel):
    """Options for sorting search results."""

    sort_by: str = "relevance"  # Options: relevance, date, confidence
    sort_order: str = "desc"  # Options: asc, desc

    @validator("sort_by")
    def validate_sort_by(cls, v: str) -> str:
        """Validate that sort_by is one of the allowed values.

        Args:
            v: The sort_by value to validate

        Returns:
            The validated sort_by value

        Raises:
            ValueError: If sort_by is not one of the allowed values
        """
        allowed_values = ["relevance", "date", "confidence"]
        if v not in allowed_values:
            raise ValueError(f"sort_by must be one of {allowed_values}")
        return v

    @validator("sort_order")
    def validate_sort_order(cls, v: str) -> str:
        """Validate that sort_order is one of the allowed values.

        Args:
            v: The sort_order value to validate

        Returns:
            The validated sort_order value

        Raises:
            ValueError: If sort_order is not one of the allowed values
        """
        allowed_values = ["asc", "desc"]
        if v not in allowed_values:
            raise ValueError(f"sort_order must be one of {allowed_values}")
        return v


class Pagination(BaseModel):
    """Pagination options for search results."""

    page: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)


class SearchQuery(BaseModel):
    """A search query for the Personal Semantic Engine."""

    query_text: str
    user_id: str
    date_range: Optional[DateRange] = None
    entity_filter: Optional[EntityFilter] = None
    sort_options: SortOptions = Field(default_factory=SortOptions)
    pagination: Pagination = Field(default_factory=Pagination)
    include_raw_content: bool = True
    highlight_matches: bool = True

    @validator("query_text")
    def query_text_not_empty(cls, v: str) -> str:
        """Validate that the query text is not empty.

        Args:
            v: The query text to validate

        Returns:
            The validated query text

        Raises:
            ValueError: If the query text is empty
        """
        if not v.strip():
            raise ValueError("Search query text cannot be empty")
        return v

    class Config:
        """Pydantic configuration."""

        frozen = True  # Immutable objects
