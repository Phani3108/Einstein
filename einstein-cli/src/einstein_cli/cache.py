"""Local caching system for offline support."""

import sqlite3
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel

from einstein_cli.api import ThoughtData, SearchResult, APIClient, NetworkError


class CacheError(Exception):
    """Base exception for cache-related errors."""
    pass


class SyncConflict(Exception):
    """Raised when sync conflicts occur."""
    
    def __init__(self, message: str, local_thought: ThoughtData, server_thought: ThoughtData):
        super().__init__(message)
        self.local_thought = local_thought
        self.server_thought = server_thought


class PendingOperation(BaseModel):
    """Represents a pending operation to sync with server."""
    
    id: str
    operation: str  # 'create', 'update', 'delete'
    thought_data: Optional[Dict[str, Any]] = None
    timestamp: datetime
    retries: int = 0


class LocalCache:
    """SQLite-based local cache for offline support."""
    
    def __init__(self, cache_dir: Path):
        """Initialize local cache.
        
        Args:
            cache_dir: Directory to store cache database
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = cache_dir / "cache.db"
        self.max_retries = 3
        
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS thoughts (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    relevance_score REAL,
                    cached_at TEXT NOT NULL,
                    is_dirty INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    query_hash TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    filters TEXT,
                    results TEXT NOT NULL,
                    cached_at TEXT NOT NULL,
                    execution_time REAL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pending_operations (
                    id TEXT PRIMARY KEY,
                    operation TEXT NOT NULL,
                    thought_data TEXT,
                    timestamp TEXT NOT NULL,
                    retries INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_user_id ON thoughts(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_thoughts_timestamp ON thoughts(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_search_cache_query ON search_cache(query)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_pending_ops_timestamp ON pending_operations(timestamp)")
            
            conn.commit()
    
    def _serialize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Optional[str]:
        """Serialize metadata dictionary to JSON string."""
        return json.dumps(metadata) if metadata else None
    
    def _deserialize_metadata(self, metadata_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Deserialize JSON string to metadata dictionary."""
        return json.loads(metadata_str) if metadata_str else None
    
    def _generate_query_hash(self, query: str, filters: Optional[Dict] = None) -> str:
        """Generate hash for search query and filters."""
        import hashlib
        
        query_data = {"query": query, "filters": filters or {}}
        query_str = json.dumps(query_data, sort_keys=True)
        return hashlib.md5(query_str.encode()).hexdigest()
    
    def cache_thought(self, thought: ThoughtData, is_dirty: bool = False) -> None:
        """Cache a thought locally.
        
        Args:
            thought: Thought data to cache
            is_dirty: Whether the thought has local changes not synced to server
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO thoughts 
                (id, content, user_id, timestamp, metadata, relevance_score, cached_at, is_dirty)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                thought.id,
                thought.content,
                thought.user_id,
                thought.timestamp.isoformat(),
                self._serialize_metadata(thought.metadata),
                thought.relevance_score,
                datetime.now().isoformat(),
                1 if is_dirty else 0
            ))
            conn.commit()
    
    def get_cached_thoughts(
        self, 
        limit: int = 20, 
        offset: int = 0,
        user_id: Optional[str] = None
    ) -> List[ThoughtData]:
        """Get cached thoughts.
        
        Args:
            limit: Maximum number of thoughts to return
            offset: Number of thoughts to skip
            user_id: Filter by user ID
            
        Returns:
            List of cached thoughts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            query = "SELECT * FROM thoughts"
            params = []
            
            if user_id:
                query += " WHERE user_id = ?"
                params.append(user_id)
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            thoughts = []
            for row in rows:
                thought = ThoughtData(
                    id=row["id"],
                    content=row["content"],
                    user_id=row["user_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                    relevance_score=row["relevance_score"]
                )
                thoughts.append(thought)
            
            return thoughts
    
    def get_cached_thought_by_id(self, thought_id: str) -> Optional[ThoughtData]:
        """Get a specific cached thought by ID.
        
        Args:
            thought_id: Unique thought identifier
            
        Returns:
            Cached thought data or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("SELECT * FROM thoughts WHERE id = ?", (thought_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            return ThoughtData(
                id=row["id"],
                content=row["content"],
                user_id=row["user_id"],
                timestamp=datetime.fromisoformat(row["timestamp"]),
                metadata=self._deserialize_metadata(row["metadata"]),
                relevance_score=row["relevance_score"]
            )
    
    def search_cached_thoughts(
        self, 
        query: str, 
        limit: int = 20,
        user_id: Optional[str] = None
    ) -> List[ThoughtData]:
        """Search through cached thoughts using simple text matching.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            user_id: Filter by user ID
            
        Returns:
            List of matching thoughts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Simple text search using SQLite FTS or LIKE
            search_query = """
                SELECT * FROM thoughts 
                WHERE content LIKE ? 
            """
            params = [f"%{query}%"]
            
            if user_id:
                search_query += " AND user_id = ?"
                params.append(user_id)
            
            search_query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(search_query, params)
            rows = cursor.fetchall()
            
            thoughts = []
            for row in rows:
                thought = ThoughtData(
                    id=row["id"],
                    content=row["content"],
                    user_id=row["user_id"],
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    metadata=self._deserialize_metadata(row["metadata"]),
                    relevance_score=None  # No semantic scoring for cached search
                )
                thoughts.append(thought)
            
            return thoughts
    
    def cache_search_result(
        self, 
        query: str, 
        filters: Optional[Dict] = None, 
        result: SearchResult = None
    ) -> None:
        """Cache search results.
        
        Args:
            query: Search query string
            filters: Search filters applied
            result: Search result to cache
        """
        if not result:
            return
            
        query_hash = self._generate_query_hash(query, filters)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO search_cache 
                (query_hash, query, filters, results, cached_at, execution_time)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                query_hash,
                query,
                json.dumps(filters) if filters else None,
                result.model_dump_json(),
                datetime.now().isoformat(),
                result.execution_time
            ))
            conn.commit()
            
            # Also cache individual thoughts from search results
            for thought in result.thoughts:
                self.cache_thought(thought, is_dirty=False)
    
    def get_cached_search_result(
        self, 
        query: str, 
        filters: Optional[Dict] = None,
        max_age_minutes: int = 30
    ) -> Optional[SearchResult]:
        """Get cached search results if available and not expired.
        
        Args:
            query: Search query string
            filters: Search filters applied
            max_age_minutes: Maximum age of cached results in minutes
            
        Returns:
            Cached search result or None if not available/expired
        """
        query_hash = self._generate_query_hash(query, filters)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM search_cache 
                WHERE query_hash = ? AND cached_at > ?
            """, (
                query_hash,
                (datetime.now() - timedelta(minutes=max_age_minutes)).isoformat()
            ))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return SearchResult.model_validate_json(row["results"])
    
    def add_pending_operation(self, operation: PendingOperation) -> None:
        """Add a pending operation to sync with server.
        
        Args:
            operation: Pending operation to add
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pending_operations 
                (id, operation, thought_data, timestamp, retries)
                VALUES (?, ?, ?, ?, ?)
            """, (
                operation.id,
                operation.operation,
                json.dumps(operation.thought_data, default=str) if operation.thought_data else None,
                operation.timestamp.isoformat(),
                operation.retries
            ))
            conn.commit()
    
    def get_pending_operations(self) -> List[PendingOperation]:
        """Get all pending operations.
        
        Returns:
            List of pending operations
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            cursor = conn.execute("""
                SELECT * FROM pending_operations 
                ORDER BY timestamp ASC
            """)
            rows = cursor.fetchall()
            
            operations = []
            for row in rows:
                operation = PendingOperation(
                    id=row["id"],
                    operation=row["operation"],
                    thought_data=json.loads(row["thought_data"]) if row["thought_data"] else None,
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    retries=row["retries"]
                )
                operations.append(operation)
            
            return operations
    
    def remove_pending_operation(self, operation_id: str) -> None:
        """Remove a pending operation.
        
        Args:
            operation_id: ID of operation to remove
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM pending_operations WHERE id = ?", (operation_id,))
            conn.commit()
    
    def increment_operation_retries(self, operation_id: str) -> None:
        """Increment retry count for a pending operation.
        
        Args:
            operation_id: ID of operation to update
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE pending_operations 
                SET retries = retries + 1 
                WHERE id = ?
            """, (operation_id,))
            conn.commit()
    
    def set_sync_metadata(self, key: str, value: str) -> None:
        """Set sync metadata value.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_metadata 
                (key, value, updated_at)
                VALUES (?, ?, ?)
            """, (key, value, datetime.now().isoformat()))
            conn.commit()
    
    def get_sync_metadata(self, key: str) -> Optional[str]:
        """Get sync metadata value.
        
        Args:
            key: Metadata key
            
        Returns:
            Metadata value or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT value FROM sync_metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def clear_cache(self) -> None:
        """Clear all cached data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM thoughts")
            conn.execute("DELETE FROM search_cache")
            conn.execute("DELETE FROM pending_operations")
            conn.execute("DELETE FROM sync_metadata")
            conn.commit()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM thoughts")
            thought_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM thoughts WHERE is_dirty = 1")
            dirty_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM search_cache")
            search_cache_count = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM pending_operations")
            pending_count = cursor.fetchone()[0]
            
            # Calculate cache size
            cache_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0
            cache_size_mb = cache_size_bytes / (1024 * 1024)
            
            return {
                "cached_thoughts": thought_count,
                "dirty_thoughts": dirty_count,
                "cached_searches": search_cache_count,
                "pending_operations": pending_count,
                "cache_size_mb": round(cache_size_mb, 2),
                "cache_path": str(self.db_path)
            }
    
    async def sync_with_server(
        self, 
        api_client: APIClient,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """Sync local cache with server.
        
        Args:
            api_client: API client for server communication
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dictionary with sync results
        """
        sync_results = {
            "operations_processed": 0,
            "operations_failed": 0,
            "conflicts_resolved": 0,
            "errors": []
        }
        
        try:
            # Get all pending operations
            pending_ops = self.get_pending_operations()
            
            if progress_callback:
                progress_callback(f"Processing {len(pending_ops)} pending operations...")
            
            for i, operation in enumerate(pending_ops):
                try:
                    if operation.retries >= self.max_retries:
                        # Skip operations that have exceeded retry limit
                        sync_results["operations_failed"] += 1
                        sync_results["errors"].append(
                            f"Operation {operation.id} exceeded retry limit"
                        )
                        continue
                    
                    # Process the operation
                    await self._process_pending_operation(api_client, operation)
                    
                    # Remove successful operation
                    self.remove_pending_operation(operation.id)
                    sync_results["operations_processed"] += 1
                    
                    if progress_callback:
                        progress_callback(f"Processed operation {i+1}/{len(pending_ops)}")
                
                except SyncConflict as e:
                    # Handle sync conflict
                    resolved = await self._resolve_sync_conflict(e)
                    if resolved:
                        self.remove_pending_operation(operation.id)
                        sync_results["conflicts_resolved"] += 1
                    else:
                        sync_results["operations_failed"] += 1
                        sync_results["errors"].append(f"Unresolved conflict: {e}")
                
                except Exception as e:
                    # Increment retry count and continue
                    self.increment_operation_retries(operation.id)
                    sync_results["operations_failed"] += 1
                    sync_results["errors"].append(f"Operation {operation.id} failed: {e}")
            
            # Update last sync timestamp
            self.set_sync_metadata("last_sync", datetime.now().isoformat())
            
            if progress_callback:
                progress_callback("Sync completed")
            
        except NetworkError as e:
            sync_results["errors"].append(f"Network error during sync: {e}")
        except Exception as e:
            sync_results["errors"].append(f"Unexpected error during sync: {e}")
        
        return sync_results
    
    async def _process_pending_operation(
        self, 
        api_client: APIClient, 
        operation: PendingOperation
    ) -> None:
        """Process a single pending operation.
        
        Args:
            api_client: API client for server communication
            operation: Pending operation to process
        """
        if operation.operation == "create":
            # Create thought on server
            thought_data = ThoughtData(**operation.thought_data)
            created_thought = await api_client.create_thought(
                thought_data.content, 
                thought_data.metadata
            )
            
            # Update local cache with server-assigned ID
            self.cache_thought(created_thought, is_dirty=False)
            
        elif operation.operation == "update":
            # For updates, we would need an update API endpoint
            # For now, we'll treat this as a potential conflict
            thought_data = ThoughtData(**operation.thought_data)
            
            try:
                server_thought = await api_client.get_thought_by_id(thought_data.id)
                
                # Check if server version is newer
                if server_thought.timestamp > thought_data.timestamp:
                    raise SyncConflict(
                        "Server has newer version",
                        thought_data,
                        server_thought
                    )
                
                # If we had an update endpoint, we would use it here
                # For now, we'll just update the cache
                self.cache_thought(thought_data, is_dirty=False)
                
            except Exception:
                # If thought doesn't exist on server, treat as create
                await api_client.create_thought(thought_data.content, thought_data.metadata)
        
        elif operation.operation == "delete":
            # Delete thought on server
            await api_client.delete_thought(operation.id)
            
            # Remove from local cache
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM thoughts WHERE id = ?", (operation.id,))
                conn.commit()
    
    async def _resolve_sync_conflict(self, conflict: SyncConflict) -> bool:
        """Resolve a sync conflict.
        
        Args:
            conflict: Sync conflict to resolve
            
        Returns:
            True if conflict was resolved, False otherwise
        """
        # For now, implement a simple "server wins" strategy
        # In a real implementation, you might want to prompt the user
        
        # Cache the server version
        self.cache_thought(conflict.server_thought, is_dirty=False)
        
        return True