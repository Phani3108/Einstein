"""FastAPI application for the Personal Semantic Engine."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
import os

import os
from pathlib import Path
from dotenv import load_dotenv

from src.container import container
from src.api.routes.thoughts import create_thoughts_router
from src.api.routes.search import create_search_router
from src.api.routes.timeline import create_timeline_router
from src.api.routes.admin import router as admin_router
from src.api.routes.context import create_context_router
from src.api.routes.insights import create_insights_router
from src.api.routes.reflection import create_reflection_router
from src.api.routes.distillation import create_distillation_router
from src.api.routes.ai_tools import create_ai_tools_router
from src.api.routes.vault import create_vault_router
from src.api.routes.integrations import create_integrations_router
from src.api.routes.actions import create_actions_router
from src.api.routes.intelligence import create_intelligence_router
from src.infrastructure.connectors.webhook_router import router as webhook_router
from src.api.error_handlers import (
    domain_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from src.api.documentation import get_security_schemes, get_common_parameters
from src.domain.exceptions import DomainError
from src.infrastructure.middleware.logging_middleware import LoggingMiddleware
from src.infrastructure.middleware.versioning_middleware import VersioningMiddleware
from src.infrastructure.logging import setup_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: Configured FastAPI application
    """
    # Load environment configuration
    env_path = Path(".") / ".env"
    load_dotenv(dotenv_path=env_path)
    
    # Configure container
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://nyn@localhost:5432/einstein",
    )
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
    # asyncpg doesn't understand sslmode — strip it and let
    # connection.py handle SSL via connect_args instead
    from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
    _parsed = urlparse(db_url)
    _qs = parse_qs(_parsed.query)
    _qs.pop("sslmode", None)
    db_url = urlunparse(_parsed._replace(query=urlencode(_qs, doseq=True)))
    container.config.from_dict(
        {
            "db": {
                "connection_string": db_url,
            },
            "api": {
                "host": os.getenv("API_HOST", "0.0.0.0"),
                "port": int(os.getenv("API_PORT", "8000")),
            },
            "security": {
                "secret_key": os.getenv("SECRET_KEY", "insecure-secret-key"),
                "algorithm": os.getenv("ALGORITHM", "HS256"),
                "access_token_expire_minutes": int(
                    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
                ),
            },
            "openai": {
                "api_key": os.getenv("OPENAI_API_KEY", ""),
                "model": os.getenv("OPENAI_MODEL", "gpt-4"),
            },
            "pinecone": {
                "api_key": os.getenv("PINECONE_API_KEY", ""),
                "environment": os.getenv("PINECONE_ENVIRONMENT", ""),
                "index_name": os.getenv("PINECONE_INDEX", "einstein"),
            },
        }
    )
    
    # Set up logging
    setup_logging(
        level="INFO",
        format_type="json",
        enable_console=True,
        enable_file=False,
    )
    
    app = FastAPI(
        title="Personal Semantic Engine (Einstein)",
        description="""
        ## Overview
        
        The Personal Semantic Engine (Einstein) is a comprehensive API-based web service that enables users to create a unified, searchable repository of their personal data. The system ingests plain English thoughts and connects to various structured APIs to build a semantic understanding of the user's life.

        ## Key Features

        - **Natural Language Processing**: Extract entities (people, places, dates, activities, emotions) from plain text
        - **Semantic Search**: Find relevant information using natural language queries with hybrid search
        - **Timeline Visualization**: View personal data chronologically with entity relationships
        - **Metadata Enrichment**: Capture contextual information like location and weather
        - **Admin Management**: System administration and user management capabilities

        ## Authentication

        All endpoints require JWT authentication except for the health check endpoint. Include the JWT token in the Authorization header:

        ```
        Authorization: Bearer <your-jwt-token>
        ```

        ## API Versioning

        This API uses URL path versioning. The current version is `v1` and all endpoints are prefixed with `/api/v1/`.

        ## Rate Limiting

        API requests are rate-limited to ensure fair usage and system stability. Rate limits are applied per user and endpoint.

        ## Error Handling

        The API uses standard HTTP status codes and returns consistent error responses in JSON format with detailed error messages.
        """,
        version="0.1.0",
        contact={
            "name": "Personal Semantic Engine Team",
            "email": "support@einstein.example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "https://api.einstein.example.com",
                "description": "Production server"
            }
        ],
        openapi_tags=[
            {
                "name": "thoughts",
                "description": "Operations for managing personal thoughts and their semantic analysis",
            },
            {
                "name": "search",
                "description": "Semantic search operations across personal data with filtering and ranking",
            },
            {
                "name": "timeline",
                "description": "Chronological visualization of personal data with entity relationships",
            },
            {
                "name": "admin",
                "description": "Administrative operations for user and system management",
            },
            {
                "name": "context",
                "description": "Context aggregation — ingest events from mobile, query timeline, manage people & projects",
            },
            {
                "name": "insights",
                "description": "AI-powered insights — briefings, prep packs, suggestions, patterns",
            },
            {
                "name": "reflection",
                "description": "Reflection & review — relationship strength, weekly/monthly reviews, person dossiers",
            },
            {
                "name": "distillation",
                "description": "Distillation — summarize verbose events into concise distilled summaries",
            },
            {
                "name": "tools",
                "description": "Contextual AI tools — summarize, connect, prepare, extract, ask",
            },
            {
                "name": "vault",
                "description": "Vault operations — notes, versions, bookmarks, tags, graph, config, decisions, templates",
            },
            {
                "name": "actions",
                "description": "Outbound actions — preview, execute, and track actions like calendar blocks, email drafts, tickets",
            },
            {
                "name": "integrations",
                "description": "Integration management — connect/disconnect providers, OAuth callbacks, manual sync",
            },
            {
                "name": "intelligence",
                "description": "Intelligence layer — pre-meeting briefings, weekly reports, follow-up detection, relationship health",
            },
            {
                "name": "webhooks",
                "description": "Inbound webhook receiver for third-party provider events",
            },
            {
                "name": "predictions",
                "description": "Time-series forecasting for knowledge graph evolution, activity patterns, entity emergence, and relationship dynamics",
            },
        ],
        openapi_url="/api/v1/openapi.json",
        docs_url=None,  # We'll create a custom docs endpoint
        redoc_url="/api/v1/redoc",
    )

    # Add middleware
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(VersioningMiddleware)

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Update for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add exception handlers
    app.add_exception_handler(DomainError, domain_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Dependency injection
    app.container = container

    # Include routers
    thoughts_router = create_thoughts_router(
        create_thought_usecase=container.create_thought_usecase(),
        get_thoughts_usecase=container.get_thoughts_usecase(),
        get_thought_by_id_usecase=container.get_thought_by_id_usecase(),
        update_thought_usecase=container.update_thought_usecase(),
        delete_thought_usecase=container.delete_thought_usecase(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(thoughts_router)

    search_router = create_search_router(
        search_thoughts_usecase=container.search_thoughts_usecase(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(search_router)

    timeline_router = create_timeline_router(
        get_timeline_usecase=container.get_timeline_usecase(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(timeline_router)

    # Include admin router
    app.include_router(admin_router)

    # Context aggregation engine routes (Phase 0)
    context_router = create_context_router(
        context_repo=container.context_event_repository(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(context_router)

    insights_router = create_insights_router(
        context_repo=container.context_event_repository(),
        llm_service=container.llm_service(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(insights_router)

    # Reflection & review routes (Phase 3)
    reflection_router = create_reflection_router(
        context_repo=container.context_event_repository(),
        llm_service=container.llm_service(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(reflection_router)

    # Distillation routes (Phase 4C)
    distillation_router = create_distillation_router(
        context_repo=container.context_event_repository(),
        llm_service=container.llm_service(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(distillation_router)

    # Contextual AI tools routes (Phase 4D)
    ai_tools_router = create_ai_tools_router(
        context_repo=container.context_event_repository(),
        llm_service=container.llm_service(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(ai_tools_router)

    # Vault routes (Phase 4A — desktop cloud migration)
    vault_router = create_vault_router(
        vault_repo=container.vault_repository(),
        context_repo=container.context_event_repository(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(vault_router)

    # Integration connector routes (Phase 1A)
    integrations_router = create_integrations_router(
        context_repo=container.context_event_repository(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(integrations_router)

    # Action routes (Phase 3)
    actions_router = create_actions_router(
        context_repo=container.context_event_repository(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(actions_router)

    # Intelligence layer routes (Phase 5A)
    intelligence_router = create_intelligence_router(
        context_repo=container.context_event_repository(),
        auth_middleware=container.auth_middleware(),
    )
    app.include_router(intelligence_router)

    # Webhook ingestion routes (Phase 1A)
    app.include_router(webhook_router)

    # ── Dev seed endpoint ────────────────────────────────────────
    @app.post("/api/v1/dev/seed", tags=["dev"])
    async def seed_mock_data():
        """Trigger mock-data seeding (idempotent)."""
        try:
            from scripts.seed_mock_data import seed
            await seed()
            return {"status": "ok", "message": "Mock data seeded successfully"}
        except Exception as exc:
            import traceback
            return {"status": "error", "message": str(exc), "traceback": traceback.format_exc()}

    # Prediction routes — lazy import so optional
    # dependencies never crash the app on startup
    try:
        from src.api.routes.predictions import create_predictions_router

        use_mock_predictions = os.getenv("USE_MOCK_FORECASTS", "true").lower() == "true"
        predictions_router = create_predictions_router(
            database=container.db(),
            auth_middleware=container.auth_middleware(),
            use_mock=use_mock_predictions,
        )
        app.include_router(predictions_router)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "Prediction routes disabled: %s", exc
        )

    # ── Dev-user guarantee ────────────────────────────────────────
    # Ensures the dev user row exists in the "users" table before any
    # route handler can INSERT rows that reference user_id via FK.
    _dev_user_ready = {"done": False}

    @app.middleware("http")
    async def ensure_dev_user_middleware(request, call_next):
        if not _dev_user_ready["done"]:
            try:
                from uuid import UUID as _UUID
                from sqlalchemy import text as _text

                _id = _UUID("60bd95e0-1d86-49a0-99c4-1b72773ba450")
                engine = container.db()._engine
                async with engine.begin() as conn:
                    row = await conn.execute(
                        _text("SELECT id FROM users WHERE id = :uid"),
                        {"uid": _id},
                    )
                    if not row.first():
                        await conn.execute(
                            _text(
                                "INSERT INTO users "
                                "(id, email, hashed_password, is_active, is_admin, created_at, updated_at) "
                                "VALUES (:uid, :email, :pw, true, true, now(), now()) "
                                "ON CONFLICT (id) DO NOTHING"
                            ),
                            {
                                "uid": _id,
                                "email": "dev-60bd95e0@einstein.local",
                                "pw": "!dev-auto-provisioned",
                            },
                        )
                _dev_user_ready["done"] = True
            except Exception:
                pass
        return await call_next(request)

    # Customize OpenAPI schema
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        from fastapi.openapi.utils import get_openapi
        
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            servers=app.servers,
            tags=app.openapi_tags,
        )
        
        # Add security schemes
        openapi_schema["components"]["securitySchemes"] = get_security_schemes()
        
        # Add common parameters
        if "parameters" not in openapi_schema["components"]:
            openapi_schema["components"]["parameters"] = {}
        openapi_schema["components"]["parameters"].update(get_common_parameters())
        
        # Add global security requirement
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi

    # Add custom documentation endpoint
    @app.get("/api/v1/docs", response_class=HTMLResponse, include_in_schema=False)
    async def custom_swagger_ui_html():
        """Serve custom Swagger UI documentation."""
        docs_path = os.path.join(os.path.dirname(__file__), "templates", "docs.html")
        try:
            with open(docs_path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            # Fallback to default Swagger UI
            from fastapi.openapi.docs import get_swagger_ui_html
            return get_swagger_ui_html(
                openapi_url="/api/v1/openapi.json",
                title="Personal Semantic Engine API",
            )

    # Add API information endpoint
    @app.get("/api/v1/info", include_in_schema=False)
    async def api_info():
        """Get API information and metadata."""
        from src.api.versioning import VersionInfo, APIVersion
        
        version_info = VersionInfo.get_version_info(APIVersion.V1)
        return {
            "api_name": "Personal Semantic Engine (Einstein)",
            "description": "A unified, searchable repository of personal data with semantic understanding",
            "version": version_info.get("version", "1.0.0"),
            "status": version_info.get("status", "stable"),
            "release_date": version_info.get("release_date"),
            "features": version_info.get("features", []),
            "documentation": {
                "interactive_docs": "/api/v1/docs",
                "redoc": "/api/v1/redoc",
                "openapi_spec": "/api/v1/openapi.json"
            },
            "endpoints": {
                "thoughts": "/api/v1/thoughts",
                "search": "/api/v1/search", 
                "timeline": "/api/v1/timeline",
                "admin": "/api/v1/admin"
            },
            "authentication": {
                "type": "JWT Bearer Token",
                "header": "Authorization: Bearer <token>"
            }
        }

    return app


# Create app instance for uvicorn
try:
    app = create_app()
except Exception as _startup_exc:
    import logging as _log
    _log.getLogger(__name__).error("create_app() failed: %s", _startup_exc, exc_info=True)

    _fallback = FastAPI(title="Einstein — startup error")

    @_fallback.get("/{path:path}")
    async def _diag(path: str = ""):
        return {"error": "app_startup_failed", "message": str(_startup_exc)}

    app = _fallback
