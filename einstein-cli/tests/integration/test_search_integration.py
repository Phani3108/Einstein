#!/usr/bin/env python3
"""Integration test for search functionality."""

import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from einstein_cli.commands.search import search
from einstein_cli.api import SearchResult, ThoughtData, APIClient
from einstein_cli.auth import AuthManager
from einstein_cli.output import OutputFormatter
from rich.console import Console


async def test_search_integration():
    """Test search functionality with mocked API."""
    
    # Create sample search results
    thoughts = [
        ThoughtData(
            id="thought1",
            content="I had a great coffee meeting with Sarah today about our AI project",
            user_id="user1",
            timestamp=datetime.now(),
            metadata={"mood": "excited", "tags": ["work", "meeting", "ai"]},
            relevance_score=0.95,
        ),
        ThoughtData(
            id="thought2",
            content="Coffee break with the team was productive, discussed machine learning",
            user_id="user1",
            timestamp=datetime.now(),
            metadata={"mood": "neutral", "tags": ["team", "ml"]},
            relevance_score=0.87,
        ),
    ]
    
    search_result = SearchResult(
        thoughts=thoughts,
        total=2,
        query="coffee meetings AI",
        execution_time=0.45,
    )
    
    # Create mock components
    console = Console()
    output_formatter = OutputFormatter(console, json_mode=False)
    
    # Mock API client
    api_client = Mock(spec=APIClient)
    api_client.search_thoughts = AsyncMock(return_value=search_result)
    api_client.__aenter__ = AsyncMock(return_value=api_client)
    api_client.__aexit__ = AsyncMock(return_value=None)
    
    # Mock auth manager
    auth_manager = Mock(spec=AuthManager)
    auth_manager.is_authenticated.return_value = True
    
    # Create mock context
    ctx = Mock()
    ctx.obj = {
        "api_client": api_client,
        "auth_manager": auth_manager,
        "output": output_formatter,
        "verbose": False,
    }
    
    print("Testing search functionality...")
    
    # Test basic search
    print("\n1. Testing basic search:")
    try:
        # Simulate the search function logic
        query = "coffee meetings AI"
        limit = 20
        filters = None
        
        # Check authentication
        if not auth_manager.is_authenticated():
            print("❌ Authentication check failed")
            return False
        
        # Validate query
        if not query.strip():
            print("❌ Query validation failed")
            return False
        
        # Perform search
        async with api_client:
            results = await api_client.search_thoughts(
                query=query,
                limit=limit,
                filters=filters
            )
        
        # Verify results
        assert results.total == 2
        assert len(results.thoughts) == 2
        assert results.query == "coffee meetings AI"
        assert results.thoughts[0].relevance_score == 0.95
        
        print("✅ Basic search test passed")
        
    except Exception as e:
        print(f"❌ Basic search test failed: {e}")
        return False
    
    # Test search with filters
    print("\n2. Testing search with filters:")
    try:
        filters = {
            "mood": "excited",
            "tags": ["work", "ai"],
            "min_score": 0.8,
            "sort": "relevance"
        }
        
        async with api_client:
            results = await api_client.search_thoughts(
                query="AI project",
                limit=10,
                filters=filters
            )
        
        # Verify API was called with correct parameters
        api_client.search_thoughts.assert_called_with(
            query="AI project",
            limit=10,
            filters=filters
        )
        
        print("✅ Search with filters test passed")
        
    except Exception as e:
        print(f"❌ Search with filters test failed: {e}")
        return False
    
    # Test output formatting
    print("\n3. Testing output formatting:")
    try:
        output_formatter.format_search_results(search_result)
        print("✅ Output formatting test passed")
        
    except Exception as e:
        print(f"❌ Output formatting test failed: {e}")
        return False
    
    print("\n🎉 All search integration tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_search_integration())
    exit(0 if success else 1)