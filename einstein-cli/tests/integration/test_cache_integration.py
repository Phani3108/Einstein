#!/usr/bin/env python3
"""Integration test for local caching and offline support."""

import asyncio
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, 'src')

from einstein_cli.cache import LocalCache, PendingOperation
from einstein_cli.api import ThoughtData, SearchResult
from einstein_cli.cached_api import CachedAPIClient
from einstein_cli.config import ConfigManager


class MockAPIClient:
    """Mock API client for testing."""
    
    def __init__(self):
        self.thoughts = {}
        self.call_count = 0
        self.should_fail = False
    
    async def create_thought(self, content: str, metadata=None):
        self.call_count += 1
        if self.should_fail:
            from einstein_cli.api import NetworkError
            raise NetworkError("Mock network error")
        
        thought_id = f"mock-{len(self.thoughts) + 1}"
        thought = ThoughtData(
            id=thought_id,
            content=content,
            user_id="test-user",
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.thoughts[thought_id] = thought
        return thought
    
    async def get_thoughts(self, limit=20, offset=0, filters=None):
        self.call_count += 1
        if self.should_fail:
            from einstein_cli.api import NetworkError
            raise NetworkError("Mock network error")
        
        thoughts = list(self.thoughts.values())
        return thoughts[offset:offset + limit]
    
    async def search_thoughts(self, query: str, limit=20, filters=None):
        self.call_count += 1
        if self.should_fail:
            from einstein_cli.api import NetworkError
            raise NetworkError("Mock network error")
        
        # Simple mock search - return thoughts containing query
        matching_thoughts = [
            thought for thought in self.thoughts.values()
            if query.lower() in thought.content.lower()
        ]
        
        return SearchResult(
            thoughts=matching_thoughts[:limit],
            total=len(matching_thoughts),
            query=query,
            execution_time=0.1
        )
    
    async def get_thought_by_id(self, thought_id: str):
        self.call_count += 1
        if self.should_fail:
            from einstein_cli.api import NetworkError
            raise NetworkError("Mock network error")
        
        if thought_id not in self.thoughts:
            from einstein_cli.api import APIError
            raise APIError(f"Thought {thought_id} not found")
        
        return self.thoughts[thought_id]
    
    async def delete_thought(self, thought_id: str):
        self.call_count += 1
        if self.should_fail:
            from einstein_cli.api import NetworkError
            raise NetworkError("Mock network error")
        
        if thought_id in self.thoughts:
            del self.thoughts[thought_id]
        return True


async def test_cache_basic_operations():
    """Test basic cache operations."""
    print("🧪 Testing basic cache operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        cache = LocalCache(cache_dir)
        
        # Test caching a thought
        thought = ThoughtData(
            id="test-1",
            content="Test thought content",
            user_id="test-user",
            timestamp=datetime.now(),
            metadata={"mood": "happy", "tags": ["test"]}
        )
        
        cache.cache_thought(thought)
        
        # Test retrieving cached thought
        cached_thought = cache.get_cached_thought_by_id("test-1")
        assert cached_thought is not None
        assert cached_thought.content == "Test thought content"
        assert cached_thought.metadata["mood"] == "happy"
        
        # Test listing cached thoughts
        thoughts = cache.get_cached_thoughts(limit=10)
        assert len(thoughts) == 1
        assert thoughts[0].id == "test-1"
        
        # Test search cache
        search_result = SearchResult(
            thoughts=[thought],
            total=1,
            query="test",
            execution_time=0.1
        )
        
        cache.cache_search_result("test", None, search_result)
        cached_search = cache.get_cached_search_result("test", None)
        assert cached_search is not None
        assert len(cached_search.thoughts) == 1
        
        print("✅ Basic cache operations working")


async def test_offline_mode():
    """Test offline mode functionality."""
    print("🧪 Testing offline mode...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create mock config
        config = ConfigManager(str(config_dir / "config.toml"))
        
        # Create cache and mock API client
        cache = LocalCache(cache_dir)
        mock_api = MockAPIClient()
        cached_api = CachedAPIClient(mock_api, cache, config)
        
        # Test online creation
        thought1 = await cached_api.create_thought("Online thought")
        assert thought1.id.startswith("mock-")
        assert mock_api.call_count == 1
        
        # Switch to offline mode
        cached_api.set_offline_mode(True)
        
        # Test offline creation
        thought2 = await cached_api.create_thought("Offline thought")
        assert thought2.content == "Offline thought"
        # Should not call API in offline mode
        assert mock_api.call_count == 1
        
        # Check pending operations
        pending_ops = cache.get_pending_operations()
        assert len(pending_ops) == 1
        assert pending_ops[0].operation == "create"
        
        # Test offline search
        search_result = await cached_api.search_thoughts("thought")
        assert len(search_result.thoughts) >= 1  # Should find cached thoughts
        
        print("✅ Offline mode working")


async def test_sync_operations():
    """Test sync functionality."""
    print("🧪 Testing sync operations...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create mock config
        config = ConfigManager(str(config_dir / "config.toml"))
        
        # Create cache and mock API client
        cache = LocalCache(cache_dir)
        mock_api = MockAPIClient()
        cached_api = CachedAPIClient(mock_api, cache, config)
        
        # Create some offline thoughts
        cached_api.set_offline_mode(True)
        
        await cached_api.create_thought("Offline thought 1")
        await cached_api.create_thought("Offline thought 2")
        
        # Check pending operations
        pending_ops = cache.get_pending_operations()
        assert len(pending_ops) == 2
        
        # Switch back online and sync
        cached_api.set_offline_mode(False)
        
        sync_results = await cached_api.sync()
        
        # Check sync results
        assert sync_results["operations_processed"] == 2
        assert sync_results["operations_failed"] == 0
        
        # Check that API was called
        assert mock_api.call_count == 2
        
        # Check that pending operations are cleared
        pending_ops = cache.get_pending_operations()
        assert len(pending_ops) == 0
        
        print("✅ Sync operations working")


async def test_network_failure_handling():
    """Test handling of network failures."""
    print("🧪 Testing network failure handling...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create mock config
        config = ConfigManager(str(config_dir / "config.toml"))
        
        # Create cache and mock API client
        cache = LocalCache(cache_dir)
        mock_api = MockAPIClient()
        cached_api = CachedAPIClient(mock_api, cache, config)
        
        # Create a thought online first
        thought = await cached_api.create_thought("Online thought")
        assert mock_api.call_count == 1
        
        # Simulate network failure
        mock_api.should_fail = True
        
        # Try to create another thought - should automatically switch to offline
        thought2 = await cached_api.create_thought("Offline thought due to network error")
        
        # Should be in offline mode now
        assert cached_api.is_offline
        
        # Should have pending operation
        pending_ops = cache.get_pending_operations()
        assert len(pending_ops) == 1
        
        # Try to search - should use cache
        search_result = await cached_api.search_thoughts("thought")
        assert len(search_result.thoughts) >= 1
        
        print("✅ Network failure handling working")


async def test_cache_stats():
    """Test cache statistics."""
    print("🧪 Testing cache statistics...")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        cache_dir = Path(temp_dir) / "cache"
        config_dir = Path(temp_dir) / "config"
        config_dir.mkdir()
        
        # Create mock config
        config = ConfigManager(str(config_dir / "config.toml"))
        
        # Create cache and mock API client
        cache = LocalCache(cache_dir)
        mock_api = MockAPIClient()
        cached_api = CachedAPIClient(mock_api, cache, config)
        
        # Create some thoughts
        await cached_api.create_thought("Thought 1")
        await cached_api.create_thought("Thought 2")
        
        # Create offline thought
        cached_api.set_offline_mode(True)
        await cached_api.create_thought("Offline thought")
        
        # Get stats
        stats = cached_api.get_cache_stats()
        
        assert stats["cached_thoughts"] >= 2
        assert stats["pending_operations"] == 1
        assert stats["offline_mode"] == True
        assert "cache_size_mb" in stats
        
        print("✅ Cache statistics working")


async def main():
    """Run all cache integration tests."""
    print("🚀 Starting cache integration tests...\n")
    
    try:
        await test_cache_basic_operations()
        await test_offline_mode()
        await test_sync_operations()
        await test_network_failure_handling()
        await test_cache_stats()
        
        print("\n🎉 All cache integration tests passed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))