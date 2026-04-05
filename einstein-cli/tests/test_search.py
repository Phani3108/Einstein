"""Tests for search commands."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from click.testing import CliRunner

from einstein_cli.commands.search import search, parse_date_filter
from einstein_cli.api import SearchResult, ThoughtData, APIError, AuthenticationError, NetworkError
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter


class TestParseDateFilter:
    """Test date parsing functionality."""

    def test_parse_today(self):
        """Test parsing 'today' keyword."""
        result = parse_date_filter("today")
        expected = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == expected.date()
        assert result.hour == 0

    def test_parse_yesterday(self):
        """Test parsing 'yesterday' keyword."""
        result = parse_date_filter("yesterday")
        expected = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == expected.date()
        assert result.hour == 0

    def test_parse_days_format(self):
        """Test parsing '7d' format."""
        result = parse_date_filter("7d")
        expected = (datetime.now() - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == expected.date()

    def test_parse_weeks_format(self):
        """Test parsing '2w' format."""
        result = parse_date_filter("2w")
        expected = (datetime.now() - timedelta(weeks=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        assert result.date() == expected.date()

    def test_parse_iso_date(self):
        """Test parsing ISO date format."""
        result = parse_date_filter("2024-01-15")
        expected = datetime(2024, 1, 15)
        assert result == expected

    def test_parse_invalid_date(self):
        """Test parsing invalid date format."""
        with pytest.raises(ValueError, match="Invalid date format"):
            parse_date_filter("invalid-date")


class TestSearchCommand:
    """Test search command functionality."""

    @pytest.fixture
    def sample_search_result(self):
        """Create sample search result."""
        thoughts = [
            ThoughtData(
                id="thought1",
                content="I had a great coffee meeting with Sarah today",
                user_id="user1",
                timestamp=datetime.now(),
                metadata={"mood": "excited", "tags": ["work", "meeting"]},
                relevance_score=0.95,
            ),
            ThoughtData(
                id="thought2",
                content="Coffee break with the team was productive",
                user_id="user1",
                timestamp=datetime.now() - timedelta(hours=2),
                metadata={"mood": "neutral", "tags": ["team"]},
                relevance_score=0.87,
            ),
        ]
        return SearchResult(
            thoughts=thoughts,
            total=2,
            query="coffee meetings",
            execution_time=0.45,
        )

    def test_search_command_help(self):
        """Test that search command shows help correctly."""
        runner = CliRunner()
        result = runner.invoke(search, ["--help"])
        assert result.exit_code == 0
        assert "Search thoughts using natural language queries" in result.output
        assert "--limit" in result.output
        assert "--mood" in result.output
        assert "--tags" in result.output

    def test_search_command_structure(self):
        """Test that search command has correct structure and options."""
        # Test that the command exists and has the right parameters
        assert search.name == "search"
        assert len(search.params) == 8  # query + 7 options
        
        # Check parameter names
        param_names = [param.name for param in search.params]
        expected_params = ["query", "limit", "mood", "tags", "since", "until", "min_score", "sort"]
        for param in expected_params:
            assert param in param_names