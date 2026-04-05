#!/usr/bin/env python3
"""
Full integration test for the Personal Semantic Engine.

This script tests the complete flow:
1. Database connection
2. OpenAI API integration
3. Pinecone vector store
4. Thought creation with entity extraction
5. Semantic search functionality
"""

import asyncio
import sys
import traceback
from datetime import datetime
from uuid import uuid4

from src.container import container
from src.domain.entities.thought import Thought, ThoughtMetadata


async def test_database_connection():
    """Test PostgreSQL database connection."""
    print("🔍 Testing database connection...")
    try:
        db = container.db()
        # Test connection by getting a session
        from sqlalchemy import text
        async with db.session() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


async def test_openai_integration():
    """Test OpenAI API integration."""
    print("🔍 Testing OpenAI integration...")
    try:
        embedding_service = container.embedding_service()
        
        # Test embedding generation
        test_text = "This is a test sentence for embedding generation."
        embedding = await embedding_service.generate_embedding(test_text)
        
        assert isinstance(embedding, list)
        assert len(embedding) == 1536  # OpenAI ada-002 embedding size
        assert all(isinstance(x, float) for x in embedding)
        
        print(f"✅ OpenAI integration successful (embedding dimension: {len(embedding)})")
        return True
    except Exception as e:
        print(f"❌ OpenAI integration failed: {e}")
        traceback.print_exc()
        return False


async def test_pinecone_integration():
    """Test Pinecone vector store integration."""
    print("🔍 Testing Pinecone integration...")
    try:
        vector_store = container.vector_store_service()
        
        # Test storing a vector
        test_vector = [0.1] * 1536  # Mock 1536-dimensional vector
        test_id = f"test-{uuid4()}"
        test_metadata = {"test": "true", "timestamp": str(datetime.now())}
        
        await vector_store.store_vector(test_id, test_vector, test_metadata)
        print("✅ Pinecone vector storage successful")
        
        # Test searching vectors
        search_results = await vector_store.search(test_vector, top_k=5)
        print(f"✅ Pinecone vector search successful (found {len(search_results)} results)")
        
        return True
    except Exception as e:
        print(f"❌ Pinecone integration failed: {e}")
        traceback.print_exc()
        return False


async def test_entity_extraction():
    """Test LLM-based entity extraction."""
    print("🔍 Testing entity extraction...")
    try:
        entity_service = container.entity_extraction_service()
        
        test_content = "I had lunch with Sarah at Central Park yesterday. We discussed the new project proposal and I'm feeling optimistic about it."
        
        from uuid import uuid4
        test_thought_id = str(uuid4())
        entities = await entity_service.extract_entities(test_content, test_thought_id)
        
        assert isinstance(entities, list)
        print(f"✅ Entity extraction successful (found {len(entities)} entities)")
        
        for entity in entities[:3]:  # Show first 3 entities
            print(f"   - {entity.entity_type.value}: {entity.entity_value} (confidence: {entity.confidence:.2f})")
        
        return True
    except Exception as e:
        print(f"❌ Entity extraction failed: {e}")
        traceback.print_exc()
        return False


async def test_thought_creation():
    """Test complete thought creation workflow."""
    print("🔍 Testing thought creation workflow...")
    try:
        create_usecase = container.create_thought_usecase()
        
        # Use the test user we created earlier
        test_user_id = "d4d7784a-1662-43da-9663-44c3d8ae1e83"  # From create_test_user.py output
        
        # Create thought with metadata
        test_content = "Had an amazing coffee meeting with John at Starbucks downtown. We brainstormed ideas for the AI project and I'm excited about the potential collaboration."
        
        metadata = ThoughtMetadata(
            mood="excited",
            tags=["work", "meeting", "AI", "collaboration"],
            custom={"location_type": "coffee_shop", "meeting_type": "brainstorming"}
        )
        
        thought = await create_usecase.execute(
            user_id=test_user_id,
            content=test_content,
            metadata=metadata
        )
        
        assert thought.id is not None
        assert thought.content == test_content
        assert len(thought.semantic_entries) > 0
        
        print(f"✅ Thought creation successful (ID: {thought.id})")
        print(f"   - Content: {thought.content[:50]}...")
        print(f"   - Entities extracted: {len(thought.semantic_entries)}")
        print(f"   - Metadata: {len(thought.metadata.tags)} tags, mood: {thought.metadata.mood}")
        
        return True, thought
    except Exception as e:
        print(f"❌ Thought creation failed: {e}")
        traceback.print_exc()
        return False, None


async def test_semantic_search():
    """Test semantic search functionality."""
    print("🔍 Testing semantic search...")
    try:
        search_usecase = container.search_thoughts_usecase()
        
        # Search for thoughts related to meetings
        search_query = "coffee meetings and collaboration"
        
        # Note: This might return empty results if no thoughts exist yet
        from src.domain.entities.search_query import SearchQuery
        search_query_obj = SearchQuery(
            query_text=search_query,
            user_id="d4d7784a-1662-43da-9663-44c3d8ae1e83"
        )
        results = await search_usecase.execute_with_query(search_query_obj)
        
        print(f"✅ Semantic search successful (found {len(results)} results)")
        
        return True
    except Exception as e:
        print(f"❌ Semantic search failed: {e}")
        traceback.print_exc()
        return False


async def run_full_integration_test():
    """Run all integration tests."""
    print("🚀 Starting Full Integration Test for Personal Semantic Engine")
    print("=" * 70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("OpenAI Integration", test_openai_integration),
        ("Pinecone Integration", test_pinecone_integration),
        ("Entity Extraction", test_entity_extraction),
        ("Thought Creation", test_thought_creation),
        ("Semantic Search", test_semantic_search),
    ]
    
    results = []
    thought_created = None
    
    for test_name, test_func in tests:
        try:
            if test_name == "Thought Creation":
                success, thought_created = await test_func()
                results.append(success)
            else:
                success = await test_func()
                results.append(success)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 70)
    print(f"📊 Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests passed! The system is ready for full testing.")
        print("\n✅ What's working:")
        print("   • PostgreSQL database connection")
        print("   • OpenAI API integration (embeddings + LLM)")
        print("   • Pinecone vector store (storage + search)")
        print("   • Entity extraction from natural language")
        print("   • Complete thought processing pipeline")
        print("   • Semantic search functionality")
        print("\n🚀 You can now:")
        print("   • Start the API server: poetry run python src/main.py")
        print("   • Test endpoints via Swagger UI: http://localhost:8001/api/v1/docs")
        print("   • Create thoughts with real entity extraction")
        print("   • Perform semantic searches across your data")
        
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please check the configuration.")
        print("\n🔧 Common issues:")
        print("   • Check your .env file has correct API keys")
        print("   • Ensure Pinecone index is created with 1536 dimensions")
        print("   • Verify PostgreSQL is running and accessible")
        print("   • Check OpenAI API key has sufficient credits")
        
        return False


if __name__ == "__main__":
    # Load environment configuration
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # Configure container
    container.config.from_dict({
        "db": {
            "connection_string": os.getenv("DATABASE_URL"),
        },
        "security": {
            "secret_key": os.getenv("SECRET_KEY", "dev-secret-key"),
            "algorithm": os.getenv("ALGORITHM", "HS256"),
            "access_token_expire_minutes": int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
        },
        "openai": {
            "api_key": os.getenv("OPENAI_API_KEY"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        },
        "pinecone": {
            "api_key": os.getenv("PINECONE_API_KEY"),
            "host": os.getenv("PINECONE_HOST"),
            "environment": os.getenv("PINECONE_ENVIRONMENT"),
            "index_name": os.getenv("PINECONE_INDEX", "faraday"),
        },
    })
    
    success = asyncio.run(run_full_integration_test())
    sys.exit(0 if success else 1)