#!/usr/bin/env python3
"""
Basic integration test for the Personal Semantic Engine.

This script tests the core components:
1. Database connection
2. OpenAI API integration
3. Pinecone vector store
"""

import asyncio
import sys
import traceback
from datetime import datetime
from uuid import uuid4

from src.container import container


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
        search_results = await vector_store.search(
            query_vector=test_vector, 
            top_k=5
        )
        print(f"✅ Pinecone vector search successful (found {len(search_results)} results)")
        
        return True
    except Exception as e:
        print(f"❌ Pinecone integration failed: {e}")
        traceback.print_exc()
        return False


async def run_basic_integration_test():
    """Run basic integration tests."""
    print("🚀 Starting Basic Integration Test for Personal Semantic Engine")
    print("=" * 70)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("OpenAI Integration", test_openai_integration),
        ("Pinecone Integration", test_pinecone_integration),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
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
    print(f"📊 Basic Integration Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All basic integration tests passed! Core services are working.")
        print("\n✅ What's working:")
        print("   • PostgreSQL database connection")
        print("   • OpenAI API integration (embeddings)")
        print("   • Pinecone vector store (storage + search)")
        print("\n🚀 You can now:")
        print("   • Start the API server: poetry run python src/main.py")
        print("   • Test endpoints via Swagger UI: http://localhost:8001/api/v1/docs")
        
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
    
    success = asyncio.run(run_basic_integration_test())
    sys.exit(0 if success else 1)