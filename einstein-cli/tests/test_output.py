"""Tests for output formatting functionality."""

import json
import pytest
from datetime import datetime
from unittest.mock import Mock, patch
from io import StringIO

from rich.console import Console
from einstein_cli.output import OutputFormatter, SearchHighlighter, FARADAY_THEME
from einstein_cli.api import ThoughtData, SearchResult, UserStats


class TestOutputFormatter:
    """Test cases for OutputFormatter class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.console = Console(file=StringIO(), width=80, legacy_windows=False)
        self.formatter = OutputFormatter(self.console, json_mode=False)
        self.json_formatter = OutputFormatter(self.console, json_mode=True)

        # Sample thought data
        self.sample_thought = ThoughtData(
            id="test-123",
            content="This is a test thought about machine learning and AI",
            user_id="user-456",
            timestamp=datetime(2024, 1, 15, 14, 30, 0),
            metadata={
                "mood": "excited",
                "tags": ["ai", "machine-learning", "test"]
            }
        )

        # Sample search results
        self.sample_search_result = SearchResult(
            query="machine learning",
            thoughts=[self.sample_thought],
            total=1,
            execution_time=0.25
        )

        # Sample user stats
        self.sample_stats = UserStats(
            total_thoughts=100,
            thoughts_this_week=15,
            most_common_tags=["ai", "work", "ideas", "projects", "learning"],
            mood_distribution={
                "happy": 30,
                "excited": 25,
                "neutral": 20,
                "calm": 15,
                "anxious": 10
            }
        )

    def test_formatter_initialization(self):
        """Test OutputFormatter initialization."""
        assert self.formatter.console == self.console
        assert self.formatter.json_mode is False
        assert self.json_formatter.json_mode is True

    def test_format_thought_full_display(self):
        """Test formatting a single thought with full details."""
        self.formatter.format_thought(self.sample_thought, show_full=True)
        output = self.console.file.getvalue()
        
        # Check that content is displayed
        assert "This is a test thought about machine learning and AI" in output
        assert "test-123" in output
        assert "2024-01-15 14:30" in output
        assert "excited" in output
        assert "ai, machine-learning, test" in output

    def test_format_thought_summary_display(self):
        """Test formatting a thought in summary mode."""
        self.formatter.format_thought(self.sample_thought, show_full=False)
        output = self.console.file.getvalue()
        
        # Check that summary info is displayed
        assert "This is a test thought about machine learning and AI" in output
        assert "test-123" in output

    def test_format_thought_json_mode(self):
        """Test formatting thought in JSON mode."""
        self.json_formatter.format_thought(self.sample_thought)
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert json_data["id"] == "test-123"
        assert json_data["content"] == "This is a test thought about machine learning and AI"

    def test_format_thought_list(self):
        """Test formatting a list of thoughts."""
        thoughts = [self.sample_thought]
        self.formatter.format_thought_list(thoughts, "Test Thoughts")
        output = self.console.file.getvalue()
        
        assert "Test Thoughts" in output
        assert "(1 found)" in output
        assert "This is a test thought about machine learning and AI" in output

    def test_format_thought_list_empty(self):
        """Test formatting an empty thought list."""
        self.formatter.format_thought_list([], "Empty Thoughts")
        output = self.console.file.getvalue()
        
        assert "No empty thoughts found." in output

    def test_format_thought_list_json_mode(self):
        """Test formatting thought list in JSON mode."""
        thoughts = [self.sample_thought]
        self.json_formatter.format_thought_list(thoughts, "Test Thoughts")
        output = self.console.file.getvalue()
        
        # Should be valid JSON array
        json_data = json.loads(output)
        assert isinstance(json_data, list)
        assert len(json_data) == 1
        assert json_data[0]["id"] == "test-123"

    def test_format_search_results(self):
        """Test formatting search results with highlighting."""
        self.formatter.format_search_results(self.sample_search_result)
        output = self.console.file.getvalue()
        
        assert "Search: 'machine learning'" in output
        assert "(1 results in 0.25s)" in output
        assert "This is a test thought about machine learning and AI" in output
        assert "90%" in output  # Mock relevance score (95 - (1 * 5) = 90)

    def test_format_search_results_empty(self):
        """Test formatting empty search results."""
        empty_result = SearchResult(
            query="nonexistent",
            thoughts=[],
            total=0,
            execution_time=0.1
        )
        self.formatter.format_search_results(empty_result)
        output = self.console.file.getvalue()
        
        assert "Search: 'nonexistent'" in output
        assert "No matching thoughts found." in output

    def test_format_search_results_json_mode(self):
        """Test formatting search results in JSON mode."""
        self.json_formatter.format_search_results(self.sample_search_result)
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert json_data["query"] == "machine learning"
        assert json_data["total"] == 1
        assert len(json_data["thoughts"]) == 1

    def test_format_stats(self):
        """Test formatting user statistics."""
        self.formatter.format_stats(self.sample_stats)
        output = self.console.file.getvalue()
        
        assert "Your Einstein Statistics" in output
        assert "Total Thoughts" in output
        assert "100" in output
        assert "This Week" in output
        assert "15" in output
        assert "Mood Distribution:" in output
        assert "happy" in output
        assert "30.0%" in output

    def test_format_stats_json_mode(self):
        """Test formatting stats in JSON mode."""
        self.json_formatter.format_stats(self.sample_stats)
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert json_data["total_thoughts"] == 100
        assert json_data["thoughts_this_week"] == 15

    def test_format_table(self):
        """Test formatting data as a table."""
        data = [
            {"name": "Alice", "age": 30, "city": "New York"},
            {"name": "Bob", "age": 25, "city": "San Francisco"}
        ]
        headers = ["name", "age", "city"]
        
        self.formatter.format_table(data, headers, "Test Table")
        output = self.console.file.getvalue()
        
        assert "Test Table" in output
        assert "Alice" in output
        assert "Bob" in output
        assert "30" in output
        assert "25" in output

    def test_format_table_empty(self):
        """Test formatting empty table."""
        self.formatter.format_table([], ["name", "age"], "Empty Table")
        output = self.console.file.getvalue()
        
        assert "No data to display." in output

    def test_format_table_json_mode(self):
        """Test formatting table in JSON mode."""
        data = [{"name": "Alice", "age": 30}]
        headers = ["name", "age"]
        
        self.json_formatter.format_table(data, headers, "Test Table")
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert isinstance(json_data, list)
        assert json_data[0]["name"] == "Alice"

    def test_format_error(self):
        """Test formatting error messages."""
        self.formatter.format_error("Test error message", "Network Error")
        output = self.console.file.getvalue()
        
        assert "Test error message" in output
        assert "Network Error" in output

    def test_format_error_json_mode(self):
        """Test formatting error in JSON mode."""
        self.json_formatter.format_error("Test error", "API Error")
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert json_data["error"] == "Test error"
        assert json_data["type"] == "API Error"

    def test_format_success(self):
        """Test formatting success messages."""
        self.formatter.format_success("Operation completed", "Success")
        output = self.console.file.getvalue()
        
        assert "Operation completed" in output
        assert "Success" in output

    def test_format_success_json_mode(self):
        """Test formatting success in JSON mode."""
        self.json_formatter.format_success("Done", "Complete")
        output = self.console.file.getvalue()
        
        # Should be valid JSON
        json_data = json.loads(output)
        assert json_data["success"] is True
        assert json_data["message"] == "Done"

    def test_create_progress(self):
        """Test creating progress indicator."""
        progress = self.formatter.create_progress("Testing...")
        assert progress is not None
        assert progress.console == self.console

    def test_get_mood_emoji(self):
        """Test mood emoji mapping."""
        assert self.formatter._get_mood_emoji("happy") == "😊"
        assert self.formatter._get_mood_emoji("excited") == "🤩"
        assert self.formatter._get_mood_emoji("sad") == "😢"
        assert self.formatter._get_mood_emoji("unknown") == "💭"

    def test_color_support_detection(self):
        """Test color support detection."""
        # Test with color support
        color_console = Console(color_system="standard")
        color_formatter = OutputFormatter(color_console)
        assert color_formatter.supports_color is True

        # Test without color support
        no_color_console = Console(color_system=None)
        no_color_formatter = OutputFormatter(no_color_console)
        assert no_color_formatter.supports_color is False

    def test_search_highlighter(self):
        """Test search term highlighting."""
        highlighter = SearchHighlighter(["machine", "learning"])
        assert len(highlighter.highlights) == 2
        
        # Test case insensitive matching
        highlighter_case = SearchHighlighter(["AI", "test"])
        assert len(highlighter_case.highlights) == 2

    def test_theme_application(self):
        """Test that theme is applied when colors are supported."""
        color_console = Console(color_system="standard")
        formatter = OutputFormatter(color_console)
        
        # Theme should be applied
        assert formatter.console._theme is not None

    def test_graceful_degradation_no_colors(self):
        """Test graceful degradation when colors are not supported."""
        no_color_console = Console(color_system=None, file=StringIO(), width=80)
        formatter = OutputFormatter(no_color_console)
        
        # Should still work without colors
        formatter.format_thought(self.sample_thought)
        output = no_color_console.file.getvalue()
        
        assert "This is a test thought about machine learning and AI" in output
        assert "test-123" in output

    def test_long_content_truncation(self):
        """Test that long content is properly truncated in summary view."""
        long_thought = ThoughtData(
            id="long-123",
            content="A" * 100,  # 100 character content
            user_id="user-456",
            timestamp=datetime.now(),
            metadata={}
        )
        
        self.formatter.format_thought(long_thought, show_full=False)
        output = self.console.file.getvalue()
        
        # Should be truncated with ellipsis
        assert "..." in output

    def test_extract_search_terms_method(self):
        """Test the _extract_search_terms method."""
        # This method should exist to extract terms from search queries
        # Let's check if it exists and works properly
        search_terms = self.formatter._extract_search_terms("machine learning AI")
        # The method should split the query into individual terms
        # This is used by the SearchHighlighter
        
        # If the method doesn't exist, we should implement it
        assert hasattr(self.formatter, '_extract_search_terms')


class TestSearchHighlighter:
    """Test cases for SearchHighlighter class."""

    def test_initialization(self):
        """Test SearchHighlighter initialization."""
        terms = ["machine", "learning"]
        highlighter = SearchHighlighter(terms)
        
        assert len(highlighter.highlights) == 2
        assert highlighter.base_style == "search."

    def test_empty_terms(self):
        """Test SearchHighlighter with empty terms."""
        highlighter = SearchHighlighter([])
        assert len(highlighter.highlights) == 0

    def test_whitespace_terms(self):
        """Test SearchHighlighter filters out whitespace-only terms."""
        terms = ["machine", "  ", "learning", ""]
        highlighter = SearchHighlighter(terms)
        
        # Should only have 2 valid terms
        assert len(highlighter.highlights) == 2


class TestThemeDefinition:
    """Test cases for theme definition."""

    def test_theme_exists(self):
        """Test that FARADAY_THEME is properly defined."""
        assert FARADAY_THEME is not None
        
        # Check for required theme keys
        required_keys = [
            "search.highlight",
            "thought.content",
            "thought.metadata",
            "thought.timestamp",
            "error.network",
            "error.auth",
            "success"
        ]
        
        for key in required_keys:
            assert key in FARADAY_THEME.styles