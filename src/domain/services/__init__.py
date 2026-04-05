"""Domain service interfaces for the Personal Semantic Engine.

This package contains abstract base classes that define the service interfaces
for domain operations. These interfaces are implemented by the infrastructure layer.
"""

from .authentication_service import AuthenticationService, TokenData
from .embedding_service import EmbeddingService
from .entity_extraction_service import EntityExtractionService
from .search_service import SearchService
from .user_management_service import UserManagementService, UserRegistrationData
from .vector_store_service import VectorSearchResult, VectorStoreService

__all__ = [
    "AuthenticationService",
    "EmbeddingService",
    "EntityExtractionService",
    "SearchService",
    "TokenData",
    "UserManagementService",
    "UserRegistrationData",
    "VectorSearchResult",
    "VectorStoreService",
]
