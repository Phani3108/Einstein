"""Tests for HybridSearchService."""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.domain.entities.enums import EntityType
from src.domain.entities.search_query import DateRange, EntityFilter, SortOptions
from src.domain.entities.search_result import SearchScore
from src.domain.exceptions import SearchQueryError
from src.infrastructure.services.search_service import HybridSearchService


class TestHybridSearchService:
    """Test cases for HybridSearchService."""

    @pytest.fixture
    def search_service(self):
        """Create a HybridSearchService instance."""
        return HybridSearchService()

    @pytest.mark.asyncio
    async def test_parse_query_basic(self, search_service):
        """Test basic query parsing."""
        # Arrange
        query_text = "test query"
        user_id = str(uuid4())

        # Act
        result = await search_service.parse_query(query_text, user_id)

        # Assert
        assert result.query_text == "test query"
        assert result.user_id == user_id
        assert result.date_range is not None
        assert result.entity_filter is not None
        assert result.sort_options is not None
        assert result.pagination is not None
        assert result.include_raw_content is True
        assert result.highlight_matches is True

    @pytest.mark.asyncio
    async def test_parse_query_with_entity_filter(self, search_service):
        """Test query parsing with entity type filters."""
        # Arrange
        query_text = "type:person john type:location paris"
        user_id = str(uuid4())

        # Act
        result = await search_service.parse_query(query_text, user_id)

        # Assert
        assert result.query_text == "john paris"
        assert EntityType.PERSON in result.entity_filter.entity_types
        assert EntityType.LOCATION in result.entity_filter.entity_types

    @pytest.mark.asyncio
    async def test_parse_query_with_date_filters(self, search_service):
        """Test query parsing with date range filters."""
        # Arrange
        query_text = "after:2024-01-01 before:2024-12-31 test query"
        user_id = str(uuid4())

        # Act
        result = await search_service.parse_query(query_text, user_id)

        # Assert
        assert result.query_text == "test query"
        assert result.date_range.start_date == datetime(2024, 1, 1)
        assert result.date_range.end_date == datetime(2024, 12, 31)

    @pytest.mark.asyncio
    async def test_parse_query_with_relative_dates(self, search_service):
        """Test query parsing with relative date filters."""
        # Arrange
        query_text = "last week test query"
        user_id = str(uuid4())

        # Act
        result = await search_service.parse_query(query_text, user_id)

        # Assert
        assert result.query_text == "test query"
        assert result.date_range.start_date is not None
        # Should be approximately one week ago
        expected_date = datetime.now() - timedelta(weeks=1)
        assert abs((result.date_range.start_date - expected_date).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_parse_query_with_sort_options(self, search_service):
        """Test query parsing with sort options."""
        # Arrange
        query_text = "sort:date order:asc test query"
        user_id = str(uuid4())

        # Act
        result = await search_service.parse_query(query_text, user_id)

        # Assert
        assert result.query_text == "test query"
        assert result.sort_options.sort_by == "date"
        assert result.sort_options.sort_order == "asc"

    @pytest.mark.asyncio
    async def test_parse_query_empty_text_error(self, search_service):
        """Test query parsing with empty text."""
        # Arrange
        query_text = ""
        user_id = str(uuid4())

        # Act & Assert
        with pytest.raises(SearchQueryError, match="Query text cannot be empty"):
            await search_service.parse_query(query_text, user_id)

    @pytest.mark.asyncio
    async def test_parse_query_only_filters_error(self, search_service):
        """Test query parsing with only filters (no actual query text)."""
        # Arrange
        query_text = "type:person sort:date"
        user_id = str(uuid4())

        # Act & Assert
        with pytest.raises(SearchQueryError, match="Query text cannot be empty after parsing filters"):
            await search_service.parse_query(query_text, user_id)

    @pytest.mark.asyncio
    async def test_calculate_score_basic(self, search_service):
        """Test basic score calculation."""
        # Arrange
        semantic_similarity = 0.8
        keyword_match = 0.7
        recency_score = 0.6
        confidence_score = 0.9

        # Act
        result = await search_service.calculate_score(
            semantic_similarity, keyword_match, recency_score, confidence_score
        )

        # Assert
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

    @pytest.mark.asyncio
    async def test_calculate_score_clamps_values(self, search_service):
        """Test that score calculation clamps values to valid range."""
        # Arrange
        semantic_similarity = 1.5  # Above 1.0
        keyword_match = -0.1  # Below 0.0
        recency_score = 0.5
        confidence_score = 0.5

        # Act
        result = await search_service.calculate_score(
            semantic_similarity, keyword_match, recency_score, confidence_score
        )

        # Assert
        assert result.semantic_similarity == 1.0  # Clamped to 1.0
        assert result.keyword_match == 0.0  # Clamped to 0.0
        assert result.recency_score == 0.5
        assert result.confidence_score == 0.5

    @pytest.mark.asyncio
    async def test_rank_results_empty_list(self, search_service):
        """Test ranking with empty results list."""
        # Arrange
        results = []

        # Act
        ranked_results = await search_service.rank_results(results)

        # Assert
        assert ranked_results == []

    @pytest.mark.asyncio
    async def test_rank_results_single_result(self, search_service):
        """Test ranking with single result."""
        # Arrange
        from src.domain.entities.search_result import SearchResult, SearchScore
        from src.domain.entities.thought import Thought, ThoughtMetadata
        from uuid import uuid4

        thought = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Test thought",
            metadata=ThoughtMetadata(),
        )
        
        score = SearchScore(
            semantic_similarity=0.8,
            keyword_match=0.7,
            recency_score=0.6,
            confidence_score=0.9,
            final_score=0.75,
        )
        
        result = SearchResult(
            thought=thought,
            score=score,
            rank=0,  # Initial rank
        )
        
        results = [result]

        # Act
        ranked_results = await search_service.rank_results(results)

        # Assert
        assert len(ranked_results) == 1
        assert ranked_results[0].rank == 1
        assert ranked_results[0].score.final_score == 0.75

    @pytest.mark.asyncio
    async def test_rank_results_multiple_results_sorted_by_score(self, search_service):
        """Test ranking with multiple results sorted by final score."""
        # Arrange
        from src.domain.entities.search_result import SearchResult, SearchScore
        from src.domain.entities.thought import Thought, ThoughtMetadata
        from uuid import uuid4

        # Create thoughts with different scores
        thought1 = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Low score thought",
            metadata=ThoughtMetadata(),
        )
        
        thought2 = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="High score thought",
            metadata=ThoughtMetadata(),
        )
        
        thought3 = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Medium score thought",
            metadata=ThoughtMetadata(),
        )
        
        # Create results with different scores (intentionally out of order)
        result1 = SearchResult(
            thought=thought1,
            score=SearchScore(
                semantic_similarity=0.3,
                keyword_match=0.2,
                recency_score=0.1,
                confidence_score=0.4,
                final_score=0.25,  # Lowest score
            ),
            rank=0,
        )
        
        result2 = SearchResult(
            thought=thought2,
            score=SearchScore(
                semantic_similarity=0.9,
                keyword_match=0.8,
                recency_score=0.9,
                confidence_score=0.95,
                final_score=0.89,  # Highest score
            ),
            rank=0,
        )
        
        result3 = SearchResult(
            thought=thought3,
            score=SearchScore(
                semantic_similarity=0.6,
                keyword_match=0.5,
                recency_score=0.4,
                confidence_score=0.7,
                final_score=0.55,  # Medium score
            ),
            rank=0,
        )
        
        results = [result1, result2, result3]  # Intentionally out of order

        # Act
        ranked_results = await search_service.rank_results(results)

        # Assert
        assert len(ranked_results) == 3
        
        # Should be sorted by final_score descending
        assert ranked_results[0].thought.content == "High score thought"
        assert ranked_results[0].rank == 1
        assert ranked_results[0].score.final_score == 0.89
        
        assert ranked_results[1].thought.content == "Medium score thought"
        assert ranked_results[1].rank == 2
        assert ranked_results[1].score.final_score == 0.55
        
        assert ranked_results[2].thought.content == "Low score thought"
        assert ranked_results[2].rank == 3
        assert ranked_results[2].score.final_score == 0.25

    @pytest.mark.asyncio
    async def test_rank_results_preserves_other_fields(self, search_service):
        """Test that ranking preserves all other fields in search results."""
        # Arrange
        from src.domain.entities.search_result import SearchResult, SearchScore, SearchMatch
        from src.domain.entities.thought import Thought, ThoughtMetadata
        from src.domain.entities.semantic_entry import SemanticEntry
        from src.domain.entities.enums import EntityType
        from uuid import uuid4

        thought = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Test thought with entities",
            metadata=ThoughtMetadata(),
        )
        
        semantic_entry = SemanticEntry(
            id=uuid4(),
            thought_id=thought.id,
            entity_type=EntityType.PERSON,
            entity_value="John",
            confidence=0.9,
            context="Test context",
        )
        
        search_match = SearchMatch(
            field="content",
            text="test",
            start_position=0,
            end_position=4,
            highlight="<mark>test</mark>",
        )
        
        result = SearchResult(
            thought=thought,
            matching_entities=[semantic_entry],
            matches=[search_match],
            score=SearchScore(
                semantic_similarity=0.8,
                keyword_match=0.7,
                recency_score=0.6,
                confidence_score=0.9,
                final_score=0.75,
            ),
            rank=0,
        )
        
        results = [result]

        # Act
        ranked_results = await search_service.rank_results(results)

        # Assert
        assert len(ranked_results) == 1
        ranked_result = ranked_results[0]
        
        # Check that all fields are preserved
        assert ranked_result.thought == thought
        assert len(ranked_result.matching_entities) == 1
        assert ranked_result.matching_entities[0] == semantic_entry
        assert len(ranked_result.matches) == 1
        assert ranked_result.matches[0] == search_match
        assert ranked_result.score.final_score == 0.75
        assert ranked_result.rank == 1  # Updated rank

    def test_parse_entity_filters(self, search_service):
        """Test entity filter parsing."""
        # Arrange
        query_text = "type:person john type:location paris type:invalid"

        # Act
        entity_filter = search_service._parse_entity_filters(query_text)

        # Assert
        assert EntityType.PERSON in entity_filter.entity_types
        assert EntityType.LOCATION in entity_filter.entity_types
        assert len(entity_filter.entity_types) == 2  # Invalid type ignored

    def test_remove_filter_syntax(self, search_service):
        """Test removal of filter syntax from query."""
        # Arrange
        query_text = "type:person john type:location paris"

        # Act
        cleaned_query = search_service._remove_filter_syntax(query_text)

        # Assert
        assert cleaned_query == "john paris"

    def test_parse_date_filters(self, search_service):
        """Test date filter parsing."""
        # Arrange
        query_text = "after:2024-01-01 before:2024-12-31"

        # Act
        date_range = search_service._parse_date_filters(query_text)

        # Assert
        assert date_range.start_date == datetime(2024, 1, 1)
        assert date_range.end_date == datetime(2024, 12, 31)

    def test_remove_date_syntax(self, search_service):
        """Test removal of date syntax from query."""
        # Arrange
        query_text = "after:2024-01-01 before:2024-12-31 test query"

        # Act
        cleaned_query = search_service._remove_date_syntax(query_text)

        # Assert
        assert cleaned_query == "test query"

    def test_parse_sort_options(self, search_service):
        """Test sort options parsing."""
        # Arrange
        query_text = "sort:date order:asc"

        # Act
        sort_options = search_service._parse_sort_options(query_text)

        # Assert
        assert sort_options.sort_by == "date"
        assert sort_options.sort_order == "asc"

    def test_remove_sort_syntax(self, search_service):
        """Test removal of sort syntax from query."""
        # Arrange
        query_text = "sort:date order:asc test query"

        # Act
        cleaned_query = search_service._remove_sort_syntax(query_text)

        # Assert
        assert cleaned_query == "test query"