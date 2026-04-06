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
    container.config.from_dict(
        {
            "db": {
                "connection_string": os.getenv(
                    "DATABASE_URL",
                    "postgresql+asyncpg://nyn@localhost:5432/einstein",
                ),
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
app = create_app()
