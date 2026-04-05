"""Tests for the SearchQuery domain entity."""

from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import (
    DateRange,
    EntityFilter,
    Pagination,
    SearchQuery,
    SortOptions,
)


def test_date_range_creation():
    """Test that a date range can be created with valid data."""
    # Arrange
    start_date = datetime.now() - timedelta(days=7)
    end_date = datetime.now()

    # Act
    date_range = DateRange(
        start_date=start_date,
        end_date=end_date,
    )

    # Assert
    assert date_range.start_date == start_date
    assert date_range.end_date == end_date


def test_date_range_validation():
    """Test that a date range validates end_date is after start_date."""
    # Arrange
    start_date = datetime.now()
    end_date = datetime.now() - timedelta(days=7)  # End date before start date

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        DateRange(
            start_date=start_date,
            end_date=end_date,
        )

    assert "end_date must be after start_date" in str(exc_info.value)


def test_entity_filter_creation():
    """Test that an entity filter can be created with valid data."""
    # Arrange
    entity_types = [EntityType.PERSON, EntityType.LOCATION]
    entity_values = ["John Doe", "San Francisco"]

    # Act
    entity_filter = EntityFilter(
        entity_types=entity_types,
        entity_values=entity_values,
    )

    # Assert
    assert entity_filter.entity_types == entity_types
    assert entity_filter.entity_values == entity_values


def test_sort_options_creation():
    """Test that sort options can be created with valid data."""
    # Arrange & Act
    sort_options = SortOptions(
        sort_by="date",
        sort_order="asc",
    )

    # Assert
    assert sort_options.sort_by == "date"
    assert sort_options.sort_order == "asc"


def test_sort_options_default_values():
    """Test that sort options have correct default values."""
    # Arrange & Act
    sort_options = SortOptions()

    # Assert
    assert sort_options.sort_by == "relevance"
    assert sort_options.sort_order == "desc"


def test_sort_options_validation():
    """Test that sort options validate sort_by and sort_order."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        SortOptions(sort_by="invalid")

    assert "sort_by must be one of" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        SortOptions(sort_order="invalid")

    assert "sort_order must be one of" in str(exc_info.value)


def test_pagination_creation():
    """Test that pagination can be created with valid data."""
    # Arrange & Act
    pagination = Pagination(
        page=2,
        page_size=20,
    )

    # Assert
    assert pagination.page == 2
    assert pagination.page_size == 20


def test_pagination_default_values():
    """Test that pagination has correct default values."""
    # Arrange & Act
    pagination = Pagination()

    # Assert
    assert pagination.page == 1
    assert pagination.page_size == 10


def test_pagination_validation():
    """Test that pagination validates page and page_size."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        Pagination(page=0)

    assert "page" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Pagination(page_size=0)

    assert "page_size" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        Pagination(page_size=101)

    assert "page_size" in str(exc_info.value)


def test_search_query_creation():
    """Test that a search query can be created with valid data."""
    # Arrange
    query_text = "test query"
    user_id = "user123"
    date_range = DateRange(
        start_date=datetime.now() - timedelta(days=7),
        end_date=datetime.now(),
    )
    entity_filter = EntityFilter(
        entity_types=[EntityType.PERSON],
        entity_values=["John Doe"],
    )
    sort_options = SortOptions(
        sort_by="date",
        sort_order="asc",
    )
    pagination = Pagination(
        page=2,
        page_size=20,
    )

    # Act
    search_query = SearchQuery(
        query_text=query_text,
        user_id=user_id,
        date_range=date_range,
        entity_filter=entity_filter,
        sort_options=sort_options,
        pagination=pagination,
        include_raw_content=False,
        highlight_matches=False,
    )

    # Assert
    assert search_query.query_text == query_text
    assert search_query.user_id == user_id
    assert search_query.date_range == date_range
    assert search_query.entity_filter == entity_filter
    assert search_query.sort_options == sort_options
    assert search_query.pagination == pagination
    assert search_query.include_raw_content is False
    assert search_query.highlight_matches is False


def test_search_query_default_values():
    """Test that a search query has correct default values."""
    # Arrange & Act
    search_query = SearchQuery(
        query_text="test query",
        user_id="user123",
    )

    # Assert
    assert search_query.date_range is None
    assert search_query.entity_filter is None
    assert isinstance(search_query.sort_options, SortOptions)
    assert isinstance(search_query.pagination, Pagination)
    assert search_query.include_raw_content is True
    assert search_query.highlight_matches is True


def test_search_query_empty_query_text():
    """Test that a search query cannot be created with empty query text."""
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        SearchQuery(
            query_text="",
            user_id="user123",
        )

    assert "Search query text cannot be empty" in str(exc_info.value)
