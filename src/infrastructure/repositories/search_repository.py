"""Search repository implementation for the Personal Semantic Engine."""

import re
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.search_query import SearchQuery
from src.domain.entities.search_result import (
    SearchMatch,
    SearchResponse,
    SearchResult,
    SearchScore,
)
from src.domain.entities.semantic_entry import SemanticEntry
from src.domain.entities.thought import Thought
from src.domain.exceptions import SearchError, SearchIndexError
from src.domain.repositories.search_repository import SearchRepository
from src.domain.services.embedding_service import EmbeddingService
from src.domain.services.search_service import SearchService
from src.domain.services.vector_store_service import VectorStoreService
from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    SemanticEntry as SemanticEntryModel,
    Thought as ThoughtModel,
)


class HybridSearchRepository(SearchRepository):
    """Hybrid search repository combining database and vector search."""

    def __init__(
        self,
        database: Database,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        search_service: SearchService,
    ):
        """Initialize the search repository.

        Args:
            database: Database connection manager
            vector_store: Vector store service for semantic search
            embedding_service: Service for generating embeddings
            search_service: Service for search operations
        """
        self._database = database
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._search_service = search_service

    async def index_thought(self, thought: Thought, entities: List[SemanticEntry]) -> None:
        """Index a thought and its semantic entries for search.

        Args:
            thought: The thought to index
            entities: The semantic entries associated with the thought

        Raises:
            SearchIndexError: If indexing fails
        """
        try:
            # Generate embedding for the thought content
            content_embedding = await self._embedding_service.generate_embedding(
                thought.content
            )

            # Store thought embedding in vector store
            await self._vector_store.store(
                id=f"thought_{thought.id}",
                vector=content_embedding,
                metadata={
                    "type": "thought",
                    "thought_id": str(thought.id),
                    "user_id": str(thought.user_id),
                    "timestamp": thought.timestamp.isoformat(),
                    "content_preview": thought.content[:200],
                },
            )

            # Index each semantic entry
            for entity in entities:
                if entity.embedding:
                    await self._vector_store.store(
                        id=f"entity_{entity.id}",
                        vector=entity.embedding,
                        metadata={
                            "type": "entity",
                            "entity_id": str(entity.id),
                            "thought_id": str(entity.thought_id),
                            "user_id": str(thought.user_id),
                            "entity_type": entity.entity_type.value,
                            "entity_value": entity.entity_value,
                            "confidence": str(entity.confidence),
                            "timestamp": thought.timestamp.isoformat(),
                        },
                    )

        except Exception as e:
            raise SearchIndexError(f"Failed to index thought: {str(e)}")

    async def search(self, query: SearchQuery) -> SearchResponse:
        """Perform a search based on the given query.

        Args:
            query: The search query containing search parameters

        Returns:
            A search response containing results and metadata

        Raises:
            SearchError: If search fails
        """
        try:
            # Generate embedding for the query
            query_embedding = await self._embedding_service.generate_embedding(
                query.query_text
            )

            # Perform vector search
            vector_results = await self._vector_store.search(
                query_vector=query_embedding,
                top_k=query.pagination.page_size * 2,  # Get more for filtering
                user_id=query.user_id,
                entity_type=query.entity_filter.entity_types[0] if query.entity_filter and query.entity_filter.entity_types else None,
            )

            # Get thought IDs from vector results
            thought_ids = []
            vector_scores = {}
            
            for result in vector_results:
                if result.metadata.get("type") == "thought":
                    thought_id = result.metadata["thought_id"]
                    thought_ids.append(thought_id)
                    vector_scores[thought_id] = result.score
                elif result.metadata.get("type") == "entity":
                    thought_id = result.metadata["thought_id"]
                    if thought_id not in thought_ids:
                        thought_ids.append(thought_id)
                    # Use higher score if multiple entities match
                    vector_scores[thought_id] = max(
                        vector_scores.get(thought_id, 0), result.score
                    )

            if not thought_ids:
                return SearchResponse(
                    results=[],
                    total_count=0,
                    page=query.pagination.page,
                    page_size=query.pagination.page_size,
                    query_text=query.query_text,
                    search_time_ms=0,
                    suggestions=[],
                )

            # Fetch thoughts from database with additional filtering
            async with self._database.session() as session:
                # Build database query
                db_query = (
                    select(ThoughtModel)
                    .where(ThoughtModel.id.in_([UUID(tid) for tid in thought_ids]))
                    .where(ThoughtModel.user_id == UUID(query.user_id))
                )

                # Apply date range filter
                if query.date_range:
                    if query.date_range.start_date:
                        db_query = db_query.where(
                            ThoughtModel.timestamp >= query.date_range.start_date
                        )
                    if query.date_range.end_date:
                        db_query = db_query.where(
                            ThoughtModel.timestamp <= query.date_range.end_date
                        )

                # Apply keyword search if needed
                if query.query_text:
                    db_query = db_query.where(
                        ThoughtModel.content.ilike(f"%{query.query_text}%")
                    )

                # Execute query
                result = await session.execute(db_query)
                thought_models = result.scalars().all()

                # Convert to domain objects and create search results
                search_results = []
                for thought_model in thought_models:
                    thought = thought_model.to_domain()
                    
                    # Calculate scores
                    semantic_score = vector_scores.get(str(thought.id), 0.0)
                    keyword_score = self._calculate_keyword_score(
                        query.query_text, thought.content
                    )
                    recency_score = self._calculate_recency_score(thought.timestamp)
                    confidence_score = self._calculate_confidence_score(thought)

                    # Use search service to calculate final score
                    score = await self._search_service.calculate_score(
                        semantic_similarity=semantic_score,
                        keyword_match=keyword_score,
                        recency_score=recency_score,
                        confidence_score=confidence_score,
                    )

                    # Generate matches for highlighting
                    matches = self._generate_matches(query.query_text, thought.content)

                    # Get matching entities
                    matching_entities = [
                        entity for entity in thought.semantic_entries
                        if self._entity_matches_query(entity, query)
                    ]

                    search_result = SearchResult(
                        thought=thought,
                        matching_entities=matching_entities,
                        matches=matches,
                        score=score,
                        rank=0,  # Will be set during ranking
                    )
                    search_results.append(search_result)

                # Rank results
                ranked_results = await self._search_service.rank_results(search_results)

                # Apply pagination
                start_idx = (query.pagination.page - 1) * query.pagination.page_size
                end_idx = start_idx + query.pagination.page_size
                paginated_results = ranked_results[start_idx:end_idx]

                return SearchResponse(
                    results=paginated_results,
                    total_count=len(ranked_results),
                    page=query.pagination.page,
                    page_size=query.pagination.page_size,
                    query_text=query.query_text,
                    search_time_ms=0,  # Will be calculated by use case
                    suggestions=[],
                )

        except Exception as e:
            raise SearchError(f"Search failed: {str(e)}")

    async def remove_from_index(self, thought_id: str) -> None:
        """Remove a thought from the search index.

        Args:
            thought_id: The ID of the thought to remove

        Raises:
            SearchIndexError: If removal fails
        """
        try:
            # Remove thought vector
            await self._vector_store.delete(f"thought_{thought_id}")

            # Remove associated entity vectors
            # Note: In a real implementation, you'd want to query for entity IDs first
            # For now, we'll assume the vector store can handle missing IDs gracefully

        except Exception as e:
            raise SearchIndexError(f"Failed to remove from index: {str(e)}")

    async def get_suggestions(
        self, query_text: str, user_id: str, limit: int = 5
    ) -> List[str]:
        """Get search suggestions based on partial query text.

        Args:
            query_text: The partial query text
            user_id: The user ID to scope suggestions to
            limit: Maximum number of suggestions to return

        Returns:
            A list of suggested search terms

        Raises:
            SearchError: If suggestion generation fails
        """
        try:
            suggestions = []
            
            async with self._database.session() as session:
                # Get entity values that start with the query text
                entity_query = (
                    select(SemanticEntryModel.entity_value)
                    .join(ThoughtModel, SemanticEntryModel.thought_id == ThoughtModel.id)
                    .where(ThoughtModel.user_id == UUID(user_id))
                    .where(SemanticEntryModel.entity_value.ilike(f"{query_text}%"))
                    .group_by(SemanticEntryModel.entity_value)
                    .order_by(func.count(SemanticEntryModel.entity_value).desc())
                    .limit(limit)
                )
                
                result = await session.execute(entity_query)
                entity_suggestions = [row[0] for row in result.fetchall()]
                suggestions.extend(entity_suggestions)

                # If we need more suggestions, get common words from thought content
                if len(suggestions) < limit:
                    remaining = limit - len(suggestions)
                    
                    # Simple word extraction from content
                    content_query = (
                        select(ThoughtModel.content)
                        .where(ThoughtModel.user_id == UUID(user_id))
                        .where(ThoughtModel.content.ilike(f"%{query_text}%"))
                        .limit(50)  # Limit to avoid processing too much text
                    )
                    
                    result = await session.execute(content_query)
                    contents = [row[0] for row in result.fetchall()]
                    
                    # Extract words that start with query_text
                    word_suggestions = set()
                    for content in contents:
                        words = re.findall(r'\b\w+', content.lower())
                        for word in words:
                            if word.startswith(query_text.lower()) and len(word) > len(query_text):
                                word_suggestions.add(word)
                                if len(word_suggestions) >= remaining:
                                    break
                        if len(word_suggestions) >= remaining:
                            break
                    
                    suggestions.extend(list(word_suggestions)[:remaining])

            return suggestions[:limit]

        except Exception as e:
            raise SearchError(f"Failed to generate suggestions: {str(e)}")

    def _calculate_keyword_score(self, query: str, content: str) -> float:
        """Calculate keyword matching score."""
        if not query or not content:
            return 0.0
        
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        if not query_words:
            return 0.0
        
        matches = query_words.intersection(content_words)
        return len(matches) / len(query_words)

    def _calculate_recency_score(self, timestamp: datetime) -> float:
        """Calculate recency-based score."""
        now = datetime.now()
        age_days = (now - timestamp).days
        
        # Score decreases exponentially with age
        # Recent thoughts (< 7 days) get high scores
        if age_days <= 7:
            return 1.0
        elif age_days <= 30:
            return 0.8
        elif age_days <= 90:
            return 0.6
        elif age_days <= 365:
            return 0.4
        else:
            return 0.2

    def _calculate_confidence_score(self, thought: Thought) -> float:
        """Calculate average confidence score from entities."""
        if not thought.semantic_entries:
            return 0.5  # Default score for thoughts without entities
        
        total_confidence = sum(entity.confidence for entity in thought.semantic_entries)
        return total_confidence / len(thought.semantic_entries)

    def _generate_matches(self, query: str, content: str) -> List[SearchMatch]:
        """Generate search matches for highlighting."""
        matches = []
        if not query or not content:
            return matches
        
        query_words = query.lower().split()
        content_lower = content.lower()
        
        for word in query_words:
            start = 0
            while True:
                pos = content_lower.find(word, start)
                if pos == -1:
                    break
                
                # Create highlighted version
                highlight = (
                    content[:pos] +
                    f"<mark>{content[pos:pos+len(word)]}</mark>" +
                    content[pos+len(word):]
                )
                
                match = SearchMatch(
                    field="content",
                    text=word,
                    start_position=pos,
                    end_position=pos + len(word),
                    highlight=highlight,
                )
                matches.append(match)
                start = pos + 1
        
        return matches

    def _entity_matches_query(self, entity: SemanticEntry, query: SearchQuery) -> bool:
        """Check if an entity matches the search query."""
        # Check entity type filter
        if query.entity_filter and query.entity_filter.entity_types:
            if entity.entity_type not in query.entity_filter.entity_types:
                return False
        
        # Check entity value filter
        if query.entity_filter and query.entity_filter.entity_values:
            if entity.entity_value not in query.entity_filter.entity_values:
                return False
        
        # Check if entity value contains query text
        if query.query_text.lower() in entity.entity_value.lower():
            return True
        
        return False