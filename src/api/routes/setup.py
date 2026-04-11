"""Setup and health-check API routes — no auth required.

Used by the Getting Started wizard to validate each service.
"""

import os
import traceback
from datetime import datetime
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/setup", tags=["setup"])


class ServiceStatus(BaseModel):
    service: str
    status: str  # connected | disconnected | not_configured
    message: str = ""


class SetupStatusResponse(BaseModel):
    services: List[ServiceStatus]
    mode: str  # local | cloud


class SetupConfigResponse(BaseModel):
    database_type: str  # sqlite | postgresql
    llm_provider: str  # ollama | openai | anthropic | deepseek | not_configured
    llm_model: str
    embedding_provider: str  # ollama | openai | mock
    redis_configured: bool
    pinecone_configured: bool
    ollama_url: str


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Check connectivity of all services. No auth required."""
    services: List[ServiceStatus] = []
    db_url = os.getenv("DATABASE_URL", "")

    # 1. Database
    try:
        from src.container import container
        db = container.db()
        async with db.engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
        services.append(ServiceStatus(service="database", status="connected", message=db_url.split("@")[-1] if "@" in db_url else "sqlite"))
    except Exception as e:
        services.append(ServiceStatus(service="database", status="disconnected", message=str(e)[:200]))

    # 2. LLM
    llm_model = os.getenv("LLM_MODEL", "")
    if llm_model.startswith("ollama/"):
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                resp.raise_for_status()
                models = [m["name"] for m in resp.json().get("models", [])]
                services.append(ServiceStatus(service="llm", status="connected", message=f"Ollama: {', '.join(models[:5])}"))
        except Exception as e:
            services.append(ServiceStatus(service="llm", status="disconnected", message=f"Ollama not reachable at {ollama_url}: {str(e)[:100]}"))
    elif llm_model:
        api_key = os.getenv("OPENAI_API_KEY", "") or os.getenv("ANTHROPIC_API_KEY", "") or os.getenv("DEEPSEEK_API_KEY", "")
        if api_key and api_key not in ("your-openai-api-key-here", "your-anthropic-api-key-here", "your-deepseek-api-key-here"):
            services.append(ServiceStatus(service="llm", status="connected", message=f"Model: {llm_model}"))
        else:
            services.append(ServiceStatus(service="llm", status="not_configured", message="No API key set"))
    else:
        services.append(ServiceStatus(service="llm", status="not_configured", message="LLM_MODEL not set"))

    # 3. Embeddings
    emb_provider = os.getenv("EMBEDDING_PROVIDER", "").lower()
    if emb_provider == "ollama":
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                resp.raise_for_status()
                services.append(ServiceStatus(service="embeddings", status="connected", message=f"Ollama embeddings ({os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')})"))
        except Exception:
            services.append(ServiceStatus(service="embeddings", status="disconnected", message="Ollama not reachable"))
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if api_key and api_key != "your-openai-api-key-here":
            services.append(ServiceStatus(service="embeddings", status="connected", message="OpenAI embeddings"))
        else:
            services.append(ServiceStatus(service="embeddings", status="not_configured", message="Using mock embeddings"))

    # 4. Redis
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(redis_url)
            await r.ping()
            await r.aclose()
            services.append(ServiceStatus(service="redis", status="connected", message="Redis available"))
        except Exception as e:
            services.append(ServiceStatus(service="redis", status="disconnected", message=str(e)[:100]))
    else:
        services.append(ServiceStatus(service="redis", status="not_configured", message="Optional — for background workers"))

    # 5. Pinecone
    pinecone_key = os.getenv("PINECONE_API_KEY", "")
    if pinecone_key and pinecone_key != "your-pinecone-api-key-here":
        services.append(ServiceStatus(service="vector_db", status="connected", message="Pinecone configured"))
    else:
        services.append(ServiceStatus(service="vector_db", status="not_configured", message="Optional — for semantic search"))

    # Determine mode
    is_local = "sqlite" in db_url or llm_model.startswith("ollama/")
    mode = "local" if is_local else "cloud"

    return SetupStatusResponse(services=services, mode=mode)


@router.get("/config", response_model=SetupConfigResponse)
async def get_setup_config():
    """Return current configuration (no secrets)."""
    db_url = os.getenv("DATABASE_URL", "")
    llm_model = os.getenv("LLM_MODEL", "")

    if "sqlite" in db_url:
        db_type = "sqlite"
    elif "postgresql" in db_url:
        db_type = "postgresql"
    else:
        db_type = "sqlite"  # default

    if llm_model.startswith("ollama/"):
        llm_provider = "ollama"
    elif "gpt" in llm_model or "openai" in llm_model:
        llm_provider = "openai"
    elif "claude" in llm_model:
        llm_provider = "anthropic"
    elif "deepseek" in llm_model:
        llm_provider = "deepseek"
    else:
        llm_provider = "not_configured"

    emb_provider = os.getenv("EMBEDDING_PROVIDER", "").lower()
    if not emb_provider:
        api_key = os.getenv("OPENAI_API_KEY", "")
        emb_provider = "openai" if (api_key and api_key != "your-openai-api-key-here") else "mock"

    return SetupConfigResponse(
        database_type=db_type,
        llm_provider=llm_provider,
        llm_model=llm_model or "not set",
        embedding_provider=emb_provider,
        redis_configured=bool(os.getenv("REDIS_URL")),
        pinecone_configured=bool(os.getenv("PINECONE_API_KEY", "").replace("your-pinecone-api-key-here", "")),
        ollama_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


@router.post("/test-llm")
async def test_llm():
    """Send a test prompt to verify LLM connectivity."""
    try:
        from src.container import container
        llm = container.llm_service()
        result = await llm.generate("Say hello in one sentence.", system_prompt="You are a helpful assistant.")
        return {"status": "ok", "response": result[:500]}
    except Exception as e:
        return {"status": "error", "message": str(e)[:500], "traceback": traceback.format_exc()[-1000:]}


@router.post("/init-db")
async def init_database():
    """Initialize database tables."""
    try:
        from src.infrastructure.database.models import Base
        from src.container import container
        db = container.db()

        if db.is_sqlite:
            from src.infrastructure.database.connection import register_sqlite_adapters
            register_sqlite_adapters()

        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        return {"status": "ok", "message": "Database tables created successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:500]}


@router.get("/ollama/models")
async def list_ollama_models():
    """List models available in the local Ollama instance."""
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{ollama_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [{"name": m["name"], "size": m.get("size", 0), "modified_at": m.get("modified_at", "")} for m in data.get("models", [])]
            return {"status": "ok", "models": models}
    except Exception as e:
        return {"status": "error", "message": f"Cannot reach Ollama at {ollama_url}: {str(e)[:200]}"}
