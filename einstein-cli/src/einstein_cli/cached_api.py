"""Cached API client with offline support."""

import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime

from einstein_cli.api import (
    APIClient, 
    ThoughtData, 
    SearchResult, 
    UserStats,
    NetworkError,
    APIError
)
from einstein_cli.cache import LocalCache, PendingOperation
from einstein_cli.config import ConfigManager


class CachedAPIClient:
    """API client wrapper with local caching and offline support."""
    
    def __init__(
        self, 
        api_client: APIClient, 
        cache: LocalCache, 
        config: ConfigManager
    ):
        """Initialize cached API client.
        
        Args:
            api_client: Underlying API client
            cache: Local cache instance
            config: Configuration manager
        """
        self.api_client = api_client
        self.cache = cache
        self.config = config
        
        # Check if offline mode was previously set
        offline_mode_str = self.cache.get_sync_metadata("offline_mode")
        self._offline_mode = offline_mode_str == "true" if offline_mode_str else False
    
    @property
    def is_offline(self) -> bool:
        """Check if client is in offline mode."""
        return self._offline_mode
    
    def set_offline_mode(self, offline: bool) -> None:
        """Set offline mode.
        
        Args:
            offline: True to enable offline mode, False to disable
        """
        self._offline_mode = offline
        # Persist offline mode setting
        self.cache.set_sync_metadata("offline_mode", "true" if offline else "false")
    
    async def _try_online_operation(self, operation_func, *args, **kwargs):
        """Try to perform an online operation, falling back to offline mode.
        
        Args:
            operation_func: Function to call for online operation
            *args: Arguments to pass to operation function
            **kwargs: Keyword arguments to pass to operation function
            
        Returns:
            Result of operation or raises exception
        """
        if self._offline_mode:
            raise NetworkError("Client is in offline mode")
        
        try:
            return await operation_func(*args, **kwargs)
        except NetworkError:
            # Automatically switch to offline mode on network errors
            self._offline_mode = True
            raise
    
    async def create_thought(
        self, 
        content: str, 
        metadata: Optional[Dict] = None,
        user_id: Optional[str] = None
    ) -> ThoughtData:
        """Create a new thought with offline support.
        
        Args:
            content: Thought content
            metadata: Optional metadata dictionary
            user_id: User ID (for offline mode)
            
        Returns:
            Created thought data
        """
        if self._offline_mode or not self.config.get("cache.enabled", True):
            # Create thought locally
            thought_id = str(uuid.uuid4())
            thought = ThoughtData(
                id=thought_id,
                content=content,
                user_id=user_id or "offline_user",  # Default for offline mode
                timestamp=datetime.now(),
                metadata=metadata
            )
            
            # Cache the thought as dirty (needs sync)
            self.cache.cache_thought(thought, is_dirty=True)
            
            # Add pending operation
            operation = PendingOperation(
                id=thought_id,
                operation="create",
                thought_data=thought.model_dump(mode='json'),  # Use JSON-serializable format
                timestamp=datetime.now()
            )
            self.cache.add_pending_operation(operation)
            
            return thought
        
        try:
            # Try online creation
            thought = await self._try_online_operation(
                self.api_client.create_thought,
                content,
                metadata
            )
            
            # Cache the created thought
            self.cache.cache_thought(thought, is_dirty=False)
            
            return thought
            
        except NetworkError:
            # Fall back to offline creation
            return await self.create_thought(content, metadata, user_id)
    
    async def search_thoughts(
        self, 
        query: str, 
        limit: int = 20, 
        filters: Optional[Dict] = None
    ) -> SearchResult:
        """Search thoughts with caching support.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional search filters
            
        Returns:
            Search results
        """
        # Check cache first if enabled
        if self.config.get("cache.enabled", True):
            cached_result = self.cache.get_cached_search_result(query, filters)
            if cached_result and not self._offline_mode:
                # Return cached result but still try to refresh in background
                return cached_result
            elif cached_result and self._offline_mode:
                # In offline mode, always return cached result if available
                return cached_result
        
        if self._offline_mode:
            # Perform local search
            thoughts = self.cache.search_cached_thoughts(query, limit)
            
            return SearchResult(
                thoughts=thoughts,
                total=len(thoughts),
                query=query,
                execution_time=0.0,
                filters_applied=filters
            )
        
        try:
            # Try online search
            result = await self._try_online_operation(
                self.api_client.search_thoughts,
                query,
                limit,
                filters
            )
            
            # Cache the search result
            if self.config.get("cache.enabled", True):
                self.cache.cache_search_result(query, filters, result)
            
            return result
            
        except NetworkError:
            # Fall back to cached search
            thoughts = self.cache.search_cached_thoughts(query, limit)
            
            return SearchResult(
                thoughts=thoughts,
                total=len(thoughts),
                query=query,
                execution_time=0.0,
                filters_applied=filters
            )
    
    async def get_thoughts(
        self, 
        limit: int = 20, 
        offset: int = 0, 
        filters: Optional[Dict] = None
    ) -> List[ThoughtData]:
        """Get list of thoughts with caching support.
        
        Args:
            limit: Maximum number of thoughts to return
            offset: Number of thoughts to skip
            filters: Optional filters
            
        Returns:
            List of thoughts
        """
        if self._offline_mode:
            # Return cached thoughts
            return self.cache.get_cached_thoughts(limit, offset)
        
        try:
            # Try online fetch
            thoughts = await self._try_online_operation(
                self.api_client.get_thoughts,
                limit,
                offset,
                filters
            )
            
            # Cache the thoughts
            if self.config.get("cache.enabled", True):
                for thought in thoughts:
                    self.cache.cache_thought(thought, is_dirty=False)
            
            return thoughts
            
        except NetworkError:
            # Fall back to cached thoughts
            return self.cache.get_cached_thoughts(limit, offset)
    
    async def get_thought_by_id(self, thought_id: str) -> ThoughtData:
        """Get a specific thought by ID with caching support.
        
        Args:
            thought_id: Unique thought identifier
            
        Returns:
            Thought data
            
        Raises:
            APIError: If thought not found in cache or server
        """
        # Check cache first
        if self.config.get("cache.enabled", True):
            cached_thought = self.cache.get_cached_thought_by_id(thought_id)
            if cached_thought:
                if self._offline_mode:
                    return cached_thought
                # In online mode, return cached but try to refresh
        
        if self._offline_mode:
            if cached_thought:
                return cached_thought
            else:
                raise APIError(f"Thought {thought_id} not found in cache")
        
        try:
            # Try online fetch
            thought = await self._try_online_operation(
                self.api_client.get_thought_by_id,
                thought_id
            )
            
            # Cache the thought
            if self.config.get("cache.enabled", True):
                self.cache.cache_thought(thought, is_dirty=False)
            
            return thought
            
        except NetworkError:
            if cached_thought:
                return cached_thought
            else:
                raise APIError(f"Thought {thought_id} not available offline")
    
    async def delete_thought(self, thought_id: str) -> bool:
        """Delete a thought by ID with offline support.
        
        Args:
            thought_id: Unique thought identifier
            
        Returns:
            True if deletion was successful
        """
        if self._offline_mode:
            # Add pending delete operation
            operation = PendingOperation(
                id=thought_id,
                operation="delete",
                timestamp=datetime.now()
            )
            self.cache.add_pending_operation(operation)
            
            # Mark as deleted locally (remove from cache)
            with self.cache._init_db():
                pass  # We'll implement soft delete if needed
            
            return True
        
        try:
            # Try online deletion
            result = await self._try_online_operation(
                self.api_client.delete_thought,
                thought_id
            )
            
            # Remove from cache
            if self.config.get("cache.enabled", True):
                # Remove from cache database
                import sqlite3
                with sqlite3.connect(self.cache.db_path) as conn:
                    conn.execute("DELETE FROM thoughts WHERE id = ?", (thought_id,))
                    conn.commit()
            
            return result
            
        except NetworkError:
            # Fall back to offline deletion
            return await self.delete_thought(thought_id)
    
    async def get_user_stats(self) -> UserStats:
        """Get user statistics.
        
        Note: This requires online connectivity as stats are computed server-side.
        
        Returns:
            User statistics data
            
        Raises:
            NetworkError: If offline or network unavailable
        """
        if self._offline_mode:
            raise NetworkError("User statistics require online connectivity")
        
        return await self._try_online_operation(self.api_client.get_user_stats)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API server health.
        
        Returns:
            Health status information
            
        Raises:
            NetworkError: If offline or network unavailable
        """
        if self._offline_mode:
            raise NetworkError("Health check requires online connectivity")
        
        return await self._try_online_operation(self.api_client.health_check)
    
    async def authenticate(self, email: str, password: str) -> str:
        """Authenticate user.
        
        Note: Authentication requires online connectivity.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Access token string
            
        Raises:
            NetworkError: If offline or network unavailable
        """
        if self._offline_mode:
            raise NetworkError("Authentication requires online connectivity")
        
        return await self._try_online_operation(
            self.api_client.authenticate,
            email,
            password
        )
    
    async def refresh_token(self) -> str:
        """Refresh authentication token.
        
        Note: Token refresh requires online connectivity.
        
        Returns:
            New access token string
            
        Raises:
            NetworkError: If offline or network unavailable
        """
        if self._offline_mode:
            raise NetworkError("Token refresh requires online connectivity")
        
        return await self._try_online_operation(self.api_client.refresh_token)
    
    async def logout(self) -> bool:
        """Logout user.
        
        Returns:
            True if logout was successful
        """
        if self._offline_mode:
            # Just clear local token
            self.api_client.auth_manager.clear_token()
            return True
        
        try:
            return await self._try_online_operation(self.api_client.logout)
        except NetworkError:
            # Clear local token even if server logout fails
            self.api_client.auth_manager.clear_token()
            return True
    
    async def sync(self, progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Sync local cache with server.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with sync results
            
        Raises:
            NetworkError: If offline or network unavailable
        """
        if self._offline_mode:
            raise NetworkError("Sync requires online connectivity")
        
        # Temporarily disable offline mode for sync
        original_offline = self._offline_mode
        self._offline_mode = False
        
        try:
            result = await self.cache.sync_with_server(self.api_client, progress_callback)
            return result
        finally:
            self._offline_mode = original_offline
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        stats = self.cache.get_cache_stats()
        stats["offline_mode"] = self._offline_mode
        return stats
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        self.cache.clear_cache()
    
    async def get_thought(self, thought_id: str) -> Optional[ThoughtData]:
        """Get a thought by ID (alias for get_thought_by_id).
        
        Args:
            thought_id: Unique thought identifier
            
        Returns:
            Thought data or None if not found
        """
        try:
            return await self.get_thought_by_id(thought_id)
        except APIError:
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get basic statistics including cache stats.
        
        Returns:
            Dictionary with statistics
        """
        cache_stats = self.get_cache_stats()
        
        # Add some basic computed stats
        cached_thoughts = self.cache.get_cached_thoughts(limit=1000)  # Get all for counting
        
        stats = {
            "total_thoughts": len(cached_thoughts),
            "cached_thoughts": cache_stats.get("cached_thoughts", 0),
            "pending_sync": cache_stats.get("pending_operations", 0),
            "offline_mode": self._offline_mode,
            "cache_enabled": self.config.get("cache.enabled", True),
        }
        
        # Try to get server stats if online
        if not self._offline_mode:
            try:
                server_stats = await self.get_user_stats()
                stats["server_thoughts"] = server_stats.total_thoughts
                stats["server_entities"] = server_stats.total_entities
            except (NetworkError, APIError):
                pass  # Ignore errors, just use cache stats
        
        return stats