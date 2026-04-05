"""Tests for SearchThoughtsUseCase."""

import pytest
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.application.usecases.search_thoughts_usecase import SearchThoughtsUseCase
from src.domain.entities.search_query import SearchQuery, Pagination
from src.domain.entities.search_result import SearchResponse, SearchResult, SearchScore
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.domain.exceptions import SearchError, SearchQueryError
from src.domain.repositories.search_repository import SearchRepository
from src.domain.services.search_service import SearchService


class TestSearchThoughtsUseCase:
    """Test cases for SearchThoughtsUseCase."""

    @pytest.fixture
    def mock_search_repository(self):
        """Create a mock search repository."""
        return Mock(spec=SearchRepository)

    @pytest.fixture
    def mock_search_service(self):
        """Create a mock search service."""
        return Mock(spec=SearchService)

    @pytest.fixture
    def search_usecase(self, mock_search_repository, mock_search_service):
        """Create a SearchThoughtsUseCase instance with mocked dependencies."""
        return SearchThoughtsUseCase(
            search_repository=mock_search_repository,
            search_service=mock_search_service,
        )

    @pytest.fixture
    def sample_search_query(self):
        """Create a sample search query."""
        return SearchQuery(
            query_text="test query",
            user_id=str(uuid4()),
            pagination=Pagination(page=1, page_size=10),
        )

    @pytest.fixture
    def sample_search_response(self):
        """Create a sample search response."""
        thought = Thought(
            id=uuid4(),
            user_id=uuid4(),
            content="Test thought content",
            metadata=ThoughtMetadata(),
        )
        
        search_result = SearchResult(
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
            results=[search_result],
            total_count=1,
            page=1,
            page_size=10,
            query_text="test query",
            search_time_ms=0,  # Will be updated by use case
        )

    @pytest.mark.asyncio
    async def test_execute_successful_search(
        self,
        search_usecase,
        mock_search_repository,
        mock_search_service,
        sample_search_query,
        sample_search_response,
    ):
        """Test successful search execution."""
        # Arrange
        user_id = uuid4()
        query_text = "test query"
        
        mock_search_service.parse_query = AsyncMock(return_value=sample_search_query)
        mock_search_repository.search = AsyncMock(return_value=sample_search_response)

        # Act
        result = await search_usecase.execute(query_text, user_id)

        # Assert
        assert result is not None
        assert result.query_text == "test query"
        assert result.total_count == 1
        assert len(result.results) == 1
        assert result.search_time_ms >= 0  # Should be updated with actual time
        
        mock_search_service.parse_query.assert_called_once_with(
            query_text=query_text, user_id=str(user_id)
        )
        mock_search_repository.search.assert_called_once_with(sample_search_query)

    @pytest.mark.asyncio
    async def test_execute_with_query_successful_search(
        self,
        search_usecase,
        mock_search_repository,
        sample_search_query,
        sample_search_response,
    ):
        """Test successful search execution with pre-built query."""
        # Arrange
        mock_search_repository.search = AsyncMock(return_value=sample_search_response)

        # Act
        result = await search_usecase.execute_with_query(sample_search_query)

        # Assert
        assert result is not None
        assert result.query_text == "test query"
        assert result.total_count == 1
        assert len(result.results) == 1
        assert result.search_time_ms >= 0  # Should be updated with actual time
        
        mock_search_repository.search.assert_called_once_with(sample_search_query)

    @pytest.mark.asyncio
    async def test_execute_query_parsing_error(
        self,
        search_usecase,
        mock_search_service,
    ):
        """Test search execution with query parsing error."""
        # Arrange
        user_id = uuid4()
        query_text = ""
        
        mock_search_service.parse_query = AsyncMock(
            side_effect=SearchQueryError("Query text cannot be empty")
        )

        # Act & Assert
        with pytest.raises(SearchQueryError, match="Query text cannot be empty"):
            await search_usecase.execute(query_text, user_id)

    @pytest.mark.asyncio
    async def test_execute_search_repository_error(
        self,
        search_usecase,
        mock_search_repository,
        mock_search_service,
        sample_search_query,
    ):
        """Test search execution with repository error."""
        # Arrange
        user_id = uuid4()
        query_text = "test query"
        
        mock_search_service.parse_query = AsyncMock(return_value=sample_search_query)
        mock_search_repository.search = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Act & Assert
        with pytest.raises(SearchError, match="Search execution failed"):
            await search_usecase.execute(query_text, user_id)

    @pytest.mark.asyncio
    async def test_get_suggestions_successful(
        self,
        search_usecase,
        mock_search_repository,
    ):
        """Test successful suggestion generation."""
        # Arrange
        user_id = uuid4()
        query_text = "test"
        expected_suggestions = ["test query", "test content", "test idea"]
        
        mock_search_repository.get_suggestions = AsyncMock(
            return_value=expected_suggestions
        )

        # Act
        result = await search_usecase.get_suggestions(query_text, user_id)

        # Assert
        assert result == expected_suggestions
        mock_search_repository.get_suggestions.assert_called_once_with(
            query_text=query_text, user_id=str(user_id), limit=5
        )

    @pytest.mark.asyncio
    async def test_get_suggestions_with_custom_limit(
        self,
        search_usecase,
        mock_search_repository,
    ):
        """Test suggestion generation with custom limit."""
        # Arrange
        user_id = uuid4()
        query_text = "test"
        limit = 10
        expected_suggestions = ["suggestion1", "suggestion2"]
        
        mock_search_repository.get_suggestions = AsyncMock(
            return_value=expected_suggestions
        )

        # Act
        result = await search_usecase.get_suggestions(query_text, user_id, limit)

        # Assert
        assert result == expected_suggestions
        mock_search_repository.get_suggestions.assert_called_once_with(
            query_text=query_text, user_id=str(user_id), limit=limit
        )

    @pytest.mark.asyncio
    async def test_get_suggestions_repository_error(
        self,
        search_usecase,
        mock_search_repository,
    ):
        """Test suggestion generation with repository error."""
        # Arrange
        user_id = uuid4()
        query_text = "test"
        
        mock_search_repository.get_suggestions = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        # Act & Assert
        with pytest.raises(SearchError, match="Suggestion generation failed"):
            await search_usecase.get_suggestions(query_text, user_id)