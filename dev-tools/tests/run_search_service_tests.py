#!/usr/bin/env python3
"""Direct test runner for search service tests."""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import DateRange, EntityFilter, SortOptions
from src.domain.entities.search_result import SearchScore
from src.domain.exceptions import SearchQueryError
from src.infrastructure.services.search_service import HybridSearchService


async def test_parse_query_basic():
    """Test basic query parsing."""
    search_service = HybridSearchService()
    query_text = "test query"
    user_id = str(uuid4())

    result = await search_service.parse_query(query_text, user_id)

    assert result.query_text == "test query"
    assert result.user_id == user_id
    assert result.date_range is not None
    assert result.entity_filter is not None
    assert result.sort_options is not None
    assert result.pagination is not None
    assert result.include_raw_content is True
    assert result.highlight_matches is True
    print("✓ test_parse_query_basic passed")


async def test_parse_query_with_entity_filter():
    """Test query parsing with entity type filters."""
    search_service = HybridSearchService()
    query_text = "type:person john type:location paris"
    user_id = str(uuid4())

    result = await search_service.parse_query(query_text, user_id)

    assert result.query_text == "john paris"
    assert EntityType.PERSON in result.entity_filter.entity_types
    assert EntityType.LOCATION in result.entity_filter.entity_types
    print("✓ test_parse_query_with_entity_filter passed")


async def test_parse_query_with_date_filters():
    """Test query parsing with date range filters."""
    search_service = HybridSearchService()
    query_text = "after:2024-01-01 before:2024-12-31 test query"
    user_id = str(uuid4())

    result = await search_service.parse_query(query_text, user_id)

    assert result.query_text == "test query"
    assert result.date_range.start_date == datetime(2024, 1, 1)
    assert result.date_range.end_date == datetime(2024, 12, 31)
    print("✓ test_parse_query_with_date_filters passed")


async def test_calculate_score_basic():
    """Test basic score calculation."""
    search_service = HybridSearchService()
    semantic_similarity = 0.8
    keyword_match = 0.7
    recency_score = 0.6
    confidence_score = 0.9

    result = await search_service.calculate_score(
        semantic_similarity, keyword_match, recency_score, confidence_score
    )

    assert result.semantic_similarity == 0.8
    assert result.keyword_match == 0.7
    assert result.recency_score == 0.6
    assert result.confidence_score == 0.9
    
    # Calculate expected final score
    expected_final = (
        0.8 * 0.4 +  # semantic weight
        0.7 * 0.3 +  # keyword weight
        0.6 * 0.2 +  # recency weight
        0.9 * 0.1    # confidence weight
    )
    assert abs(result.final_score - expected_final) < 0.001
    print("✓ test_calculate_score_basic passed")


async def test_parse_query_empty_text_error():
    """Test query parsing with empty text."""
    search_service = HybridSearchService()
    query_text = ""
    user_id = str(uuid4())

    try:
        await search_service.parse_query(query_text, user_id)
        assert False, "Should have raised SearchQueryError"
    except SearchQueryError as e:
        assert "Query text cannot be empty" in str(e)
        print("✓ test_parse_query_empty_text_error passed")


def test_parse_entity_filters():
    """Test entity filter parsing."""
    search_service = HybridSearchService()
    query_text = "type:person john type:location paris type:invalid"

    entity_filter = search_service._parse_entity_filters(query_text)

    assert EntityType.PERSON in entity_filter.entity_types
    assert EntityType.LOCATION in entity_filter.entity_types
    assert len(entity_filter.entity_types) == 2  # Invalid type ignored
    print("✓ test_parse_entity_filters passed")


def test_remove_filter_syntax():
    """Test removal of filter syntax from query."""
    search_service = HybridSearchService()
    query_text = "type:person john type:location paris"

    cleaned_query = search_service._remove_filter_syntax(query_text)

    assert cleaned_query == "john paris"
    print("✓ test_remove_filter_syntax passed")


async def main():
    """Run all tests."""
    print("Running search service tests...")
    
    # Run async tests
    await test_parse_query_basic()
    await test_parse_query_with_entity_filter()
    await test_parse_query_with_date_filters()
    await test_calculate_score_basic()
    await test_parse_query_empty_text_error()
    
    # Run sync tests
    test_parse_entity_filters()
    test_remove_filter_syntax()
    
    print("\n✅ All search service tests passed!")


if __name__ == "__main__":
    asyncio.run(main())