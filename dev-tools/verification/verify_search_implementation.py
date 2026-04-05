#!/usr/bin/env python3
"""Comprehensive verification of search implementation."""

import sys
import os
import asyncio
from uuid import uuid4

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.application.usecases.search_thoughts_usecase import SearchThoughtsUseCase
from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import SearchQuery, Pagination
from src.domain.entities.search_result import SearchResponse, SearchResult, SearchScore
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import SearchError, SearchQueryError
from src.infrastructure.services.search_service import HybridSearchService


class MockSearchRepository:
    """Mock search repository for testing."""
    
    async def search(self, query: SearchQuery) -> SearchResponse:
        """Mock search implementation."""
        # Create a mock thought
        thought = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content=f"Mock result for query: {query.query_text}",
            metadata=ThoughtMetadata(),
        )
        
        # Create a mock search result
        result = SearchResult(
            thought=thought,
            score=SearchScore(
                semantic_similarity=0.8,
                keyword_match=0.7,
                recency_score=0.6,
                confidence_score=0.9,
                final_score=0.75,
            ),
            rank=1,
        )
        
        return SearchResponse(
            results=[result],
            total_count=1,
            page=query.pagination.page,
            page_size=query.pagination.page_size,
            query_text=query.query_text,
            search_time_ms=0,  # Will be updated by use case
        )
    
    async def get_suggestions(self, query_text: str, user_id: str, limit: int = 5) -> list[str]:
        """Mock suggestions implementation."""
        return [f"{query_text} suggestion 1", f"{query_text} suggestion 2"]


async def test_complete_search_flow():
    """Test the complete search flow from use case to service."""
    print("Testing complete search flow...")
    
    # Create dependencies
    search_repository = MockSearchRepository()
    search_service = HybridSearchService()
    search_usecase = SearchThoughtsUseCase(search_repository, search_service)
    
    # Test basic search
    user_id = uuid4()
    query_text = "test search query"
    
    result = await search_usecase.execute(query_text, user_id)
    
    # Verify result structure
    assert isinstance(result, SearchResponse)
    assert result.query_text == query_text
    assert result.total_count == 1
    assert len(result.results) == 1
    assert result.search_time_ms >= 0
    
    # Verify search result
    search_result = result.results[0]
    assert isinstance(search_result, SearchResult)
    assert isinstance(search_result.thought, Thought)
    assert isinstance(search_result.score, SearchScore)
    assert search_result.rank == 1
    
    print("✓ Basic search flow works")


async def test_search_with_filters():
    """Test search with various filters."""
    print("Testing search with filters...")
    
    search_service = HybridSearchService()
    
    # Test entity type filters
    query_with_filters = "type:person john type:location paris"
    user_id = str(uuid4())
    
    parsed_query = await search_service.parse_query(query_with_filters, user_id)
    
    assert parsed_query.query_text == "john paris"
    assert EntityType.PERSON in parsed_query.entity_filter.entity_types
    assert EntityType.LOCATION in parsed_query.entity_filter.entity_types
    
    print("✓ Entity type filters work")
    
    # Test date filters
    query_with_dates = "after:2024-01-01 before:2024-12-31 search term"
    parsed_date_query = await search_service.parse_query(query_with_dates, user_id)
    
    assert parsed_date_query.query_text == "search term"
    assert parsed_date_query.date_range.start_date is not None
    assert parsed_date_query.date_range.end_date is not None
    
    print("✓ Date filters work")
    
    # Test sort options
    query_with_sort = "sort:date order:asc search term"
    parsed_sort_query = await search_service.parse_query(query_with_sort, user_id)
    
    assert parsed_sort_query.query_text == "search term"
    assert parsed_sort_query.sort_options.sort_by == "date"
    assert parsed_sort_query.sort_options.sort_order == "asc"
    
    print("✓ Sort options work")


async def test_search_scoring():
    """Test search scoring algorithm."""
    print("Testing search scoring...")
    
    search_service = HybridSearchService()
    
    # Test different score combinations
    test_cases = [
        (1.0, 0.0, 0.0, 0.0, 0.4),  # Pure semantic
        (0.0, 1.0, 0.0, 0.0, 0.3),  # Pure keyword
        (0.0, 0.0, 1.0, 0.0, 0.2),  # Pure recency
        (0.0, 0.0, 0.0, 1.0, 0.1),  # Pure confidence
        (0.8, 0.7, 0.6, 0.9, 0.74), # Mixed scores (0.8*0.4 + 0.7*0.3 + 0.6*0.2 + 0.9*0.1 = 0.74)
    ]
    
    for semantic, keyword, recency, confidence, expected in test_cases:
        score = await search_service.calculate_score(semantic, keyword, recency, confidence)
        assert abs(score.final_score - expected) < 0.001, f"Expected {expected}, got {score.final_score}"
    
    print("✓ Scoring algorithm works correctly")


async def test_error_handling():
    """Test error handling in search functionality."""
    print("Testing error handling...")
    
    search_service = HybridSearchService()
    
    # Test empty query error
    try:
        await search_service.parse_query("", str(uuid4()))
        assert False, "Should have raised SearchQueryError"
    except SearchQueryError as e:
        assert "Query text cannot be empty" in str(e)
    
    print("✓ Empty query error handling works")
    
    # Test query with only filters error
    try:
        await search_service.parse_query("type:person sort:date", str(uuid4()))
        assert False, "Should have raised SearchQueryError"
    except SearchQueryError as e:
        assert "Query text cannot be empty after parsing filters" in str(e)
    
    print("✓ Filters-only query error handling works")


async def test_suggestions():
    """Test search suggestions functionality."""
    print("Testing suggestions...")
    
    search_repository = MockSearchRepository()
    search_service = HybridSearchService()
    search_usecase = SearchThoughtsUseCase(search_repository, search_service)
    
    user_id = uuid4()
    query_text = "test"
    
    suggestions = await search_usecase.get_suggestions(query_text, user_id)
    
    assert isinstance(suggestions, list)
    assert len(suggestions) == 2
    assert "test suggestion 1" in suggestions
    assert "test suggestion 2" in suggestions
    
    print("✓ Suggestions functionality works")


async def main():
    """Run all verification tests."""
    print("🔍 Verifying Search Implementation")
    print("=" * 50)
    
    await test_complete_search_flow()
    await test_search_with_filters()
    await test_search_scoring()
    await test_error_handling()
    await test_suggestions()
    
    print("\n" + "=" * 50)
    print("✅ All search implementation tests passed!")
    print("\n📋 Implementation Summary:")
    print("  ✓ SearchThoughtsUseCase - Hybrid search orchestration")
    print("  ✓ HybridSearchService - Query parsing and scoring")
    print("  ✓ Search query parsing with filters (entity types, dates, sort)")
    print("  ✓ Hybrid scoring algorithm (semantic + keyword + recency + confidence)")
    print("  ✓ Search result ranking")
    print("  ✓ Error handling and validation")
    print("  ✓ Search suggestions")
    print("  ✓ Domain entities (SearchQuery, SearchResult, SearchResponse)")
    print("  ✓ Repository and service interfaces")
    print("  ✓ Comprehensive unit tests")


if __name__ == "__main__":
    asyncio.run(main())