"""Dependency injection container for the Personal Semantic Engine.

This module provides a centralized container for managing dependencies and their
lifecycle throughout the application.
"""

import os

from dependency_injector import containers, providers

from src.domain.services.embedding_service import EmbeddingService
from src.domain.services.entity_extraction_service import EntityExtractionService
from src.domain.services.vector_store_service import VectorStoreService
from src.infrastructure.database.connection import Database
from src.infrastructure.llm.config import LLMConfigLoader
from src.infrastructure.llm.entity_extraction_service import LLMEntityExtractionService
from src.infrastructure.llm.llm_service import LLMService
from src.infrastructure.repositories.semantic_entry_repository import (
    PostgreSQLSemanticEntryRepository,
)
from src.infrastructure.repositories.thought_repository import (
    PostgreSQLThoughtRepository,
)
from src.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from src.infrastructure.repositories.context_event_repository import (
    ContextEventRepository,
)
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.infrastructure.services.vector_store_service import PineconeVectorStore
from src.infrastructure.services.authentication_service import JWTAuthenticationService
from src.infrastructure.services.user_management_service import DefaultUserManagementService
from src.infrastructure.services.search_service import HybridSearchService
from src.infrastructure.repositories.search_repository import HybridSearchRepository
from src.infrastructure.repositories.timeline_repository import PostgreSQLTimelineRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware

# Use cases
from src.application.usecases.create_thought_usecase import CreateThoughtUseCase
from src.application.usecases.get_thoughts_usecase import GetThoughtsUseCase
from src.application.usecases.get_thought_by_id_usecase import GetThoughtByIdUseCase
from src.application.usecases.update_thought_usecase import UpdateThoughtUseCase
from src.application.usecases.delete_thought_usecase import DeleteThoughtUseCase
from src.application.usecases.verify_token_usecase import VerifyTokenUseCase
from src.application.usecases.search_thoughts_usecase import SearchThoughtsUseCase
from src.application.usecases.get_timeline_usecase import GetTimelineUseCase
from src.application.usecases.get_users_usecase import GetUsersUseCase
from src.application.usecases.create_user_usecase import CreateUserUseCase
from src.application.usecases.get_system_health_usecase import GetSystemHealthUseCase


class Container(containers.DeclarativeContainer):
    """Application container for dependency injection."""

    config = providers.Configuration()

    # Infrastructure
    db = providers.Singleton(Database, connection_string=config.db.connection_string)

    # LLM Configuration
    llm_config_loader = providers.Singleton(LLMConfigLoader)

    llm_service = providers.Singleton(
        LLMService,
        model=os.getenv("LLM_MODEL"),
        config_loader=llm_config_loader,
    )

    # Repositories
    thought_repository = providers.Singleton(
        PostgreSQLThoughtRepository,
        database=db,
    )

    user_repository = providers.Singleton(
        PostgreSQLUserRepository,
        database=db,
    )

    semantic_entry_repository = providers.Singleton(
        PostgreSQLSemanticEntryRepository,
        database=db,
    )

    # Services
    entity_extraction_service = providers.Singleton(
        LLMEntityExtractionService,
        llm_service=llm_service,
    )

    embedding_service = providers.Singleton(
        OpenAIEmbeddingService,
        api_key=os.getenv("OPENAI_API_KEY"),
    )

    vector_store_service = providers.Singleton(
        PineconeVectorStore,
        api_key=os.getenv("PINECONE_API_KEY"),
        host=os.getenv("PINECONE_HOST"),
        environment=os.getenv("PINECONE_ENVIRONMENT"),  # Keep for backward compatibility
        index_name=os.getenv("PINECONE_INDEX", "einstein"),
    )

    # Authentication services
    authentication_service = providers.Singleton(
        JWTAuthenticationService,
        secret_key=os.getenv("JWT_SECRET_KEY", "your-secret-key"),
        algorithm="HS256",
        access_token_expire_minutes=30,
    )

    user_management_service = providers.Singleton(
        DefaultUserManagementService,
        user_repository=user_repository,
        authentication_service=authentication_service,
    )

    search_service = providers.Singleton(HybridSearchService)

    search_repository = providers.Singleton(
        HybridSearchRepository,
        database=db,
        vector_store=vector_store_service,
        embedding_service=embedding_service,
        search_service=search_service,
    )

    timeline_repository = providers.Singleton(
        PostgreSQLTimelineRepository,
        database=db,
    )

    # Use cases
    create_thought_usecase = providers.Factory(
        CreateThoughtUseCase,
        thought_repository=thought_repository,
        semantic_entry_repository=semantic_entry_repository,
        entity_extraction_service=entity_extraction_service,
    )

    get_thoughts_usecase = providers.Factory(
        GetThoughtsUseCase,
        thought_repository=thought_repository,
    )

    get_thought_by_id_usecase = providers.Factory(
        GetThoughtByIdUseCase,
        thought_repository=thought_repository,
    )

    update_thought_usecase = providers.Factory(
        UpdateThoughtUseCase,
        thought_repository=thought_repository,
        semantic_entry_repository=semantic_entry_repository,
        entity_extraction_service=entity_extraction_service,
    )

    delete_thought_usecase = providers.Factory(
        DeleteThoughtUseCase,
        thought_repository=thought_repository,
        semantic_entry_repository=semantic_entry_repository,
    )

    verify_token_usecase = providers.Factory(
        VerifyTokenUseCase,
        authentication_service=authentication_service,
        user_management_service=user_management_service,
    )

    search_thoughts_usecase = providers.Factory(
        SearchThoughtsUseCase,
        search_repository=search_repository,
        search_service=search_service,
    )

    get_timeline_usecase = providers.Factory(
        GetTimelineUseCase,
        timeline_repository=timeline_repository,
    )

    # Admin use cases
    get_users_usecase = providers.Factory(
        GetUsersUseCase,
        user_repository=user_repository,
    )

    create_user_usecase = providers.Factory(
        CreateUserUseCase,
        user_repository=user_repository,
        authentication_service=authentication_service,
    )

    get_system_health_usecase = providers.Factory(
        GetSystemHealthUseCase,
        database=db,
        user_repository=user_repository,
        thought_repository=thought_repository,
    )

    # Context aggregation engine (Phase 0)
    context_event_repository = providers.Singleton(
        ContextEventRepository,
        database=db,
    )

    # Middleware
    auth_middleware = providers.Factory(
        AuthenticationMiddleware,
        verify_token_usecase=verify_token_usecase,
    )


container = Container()
