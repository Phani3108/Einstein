#!/usr/bin/env python3
"""Test the ranking functionality."""

import sys
import os
import asyncio
from uuid import uuid4

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.domain.entities.search_result import SearchResult, SearchScore
from src.domain.entities.thought import Thought, ThoughtMetadata
from src.infrastructure.services.search_service import HybridSearchService


async def test_rank_results_functionality():
    """Test the actual ranking functionality."""
    search_service = HybridSearchService()
    
    # Create test thoughts
    thought1 = Thought(
        id=uuid4(),
        user_id=uuid4(),
        content="First thought",
        metadata=ThoughtMetadata(),
    )
    
    thought2 = Thought(
        id=uuid4(),
        user_id=uuid4(),
        content="Second thought",
        metadata=ThoughtMetadata(),
    )
    
    thought3 = Thought(
        id=uuid4(),
        user_id=uuid4(),
        content="Third thought",
        metadata=ThoughtMetadata(),
    )
    
    # Create search results with different scores (unsorted)
    result1 = SearchResult(
        thought=thought1,
        score=SearchScore(
            semantic_similarity=0.5,
            keyword_match=0.6,
            recency_score=0.7,
            confidence_score=0.8,
            final_score=0.6,  # Middle score
        ),
        rank=0,
    )
    
    result2 = SearchResult(
        thought=thought2,
        score=SearchScore(
            semantic_similarity=0.9,
            keyword_match=0.8,
            recency_score=0.7,
            confidence_score=0.9,
            final_score=0.85,  # Highest score
        ),
        rank=0,
    )
    
    result3 = SearchResult(
        thought=thought3,
        score=SearchScore(
            semantic_similarity=0.3,
            keyword_match=0.4,
            recency_score=0.5,
            confidence_score=0.6,
            final_score=0.4,  # Lowest score
        ),
        rank=0,
    )
    
    # Test ranking
    unsorted_results = [result1, result2, result3]  # Mixed order
    ranked_results = await search_service.rank_results(unsorted_results)
    
    # Verify ranking order (highest score first)
    assert len(ranked_results) == 3
    assert ranked_results[0].score.final_score == 0.85  # result2
    assert ranked_results[1].score.final_score == 0.6   # result1
    assert ranked_results[2].score.final_score == 0.4   # result3
    
    # Verify rank positions
    assert ranked_results[0].rank == 1
    assert ranked_results[1].rank == 2
    assert ranked_results[2].rank == 3
    
    # Verify thoughts are in correct order
    assert ranked_results[0].thought.content == "Second thought"
    assert ranked_results[1].thought.content == "First thought"
    assert ranked_results[2].thought.content == "Third thought"
    
    print("✓ Ranking functionality works correctly")
    print(f"  Rank 1: {ranked_results[0].thought.content} (score: {ranked_results[0].score.final_score})")
    print(f"  Rank 2: {ranked_results[1].thought.content} (score: {ranked_results[1].score.final_score})")
    print(f"  Rank 3: {ranked_results[2].thought.content} (score: {ranked_results[2].score.final_score})")


async def test_rank_empty_results():
    """Test ranking with empty results."""
    search_service = HybridSearchService()
    
    empty_results = []
    ranked_results = await search_service.rank_results(empty_results)
    
    assert len(ranked_results) == 0
    print("✓ Empty results ranking works correctly")


async def main():
    """Run all ranking functionality tests."""
    print("Running ranking functionality tests...")
    
    await test_rank_results_functionality()
    await test_rank_empty_results()
    
    print("\n✅ All ranking functionality tests passed!")


if __name__ == "__main__":
    asyncio.run(main())