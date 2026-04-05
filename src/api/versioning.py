"""API versioning strategy and utilities."""

from typing import Dict, Any
from enum import Enum


class APIVersion(str, Enum):
    """Supported API versions."""
    
    V1 = "v1"
    # Future versions can be added here
    # V2 = "v2"


class VersionInfo:
    """API version information and metadata."""
    
    CURRENT_VERSION = APIVersion.V1
    SUPPORTED_VERSIONS = [APIVersion.V1]
    
    VERSION_METADATA = {
        APIVersion.V1: {
            "version": "1.0.0",
            "release_date": "2024-01-15",
            "status": "stable",
            "description": "Initial release with core functionality",
            "features": [
                "Thought management with entity extraction",
                "Semantic search with hybrid ranking",
                "Timeline visualization with relationships",
                "Admin user management",
                "JWT authentication",
                "OpenAPI documentation"
            ],
            "breaking_changes": [],
            "deprecations": [],
            "migration_guide": None
        }
    }
    
    @classmethod
    def get_version_info(cls, version: APIVersion) -> Dict[str, Any]:
        """Get detailed information about a specific API version.
        
        Args:
            version: The API version to get information for
            
        Returns:
            Dictionary containing version metadata
        """
        return cls.VERSION_METADATA.get(version, {})
    
    @classmethod
    def is_supported(cls, version: APIVersion) -> bool:
        """Check if an API version is supported.
        
        Args:
            version: The API version to check
            
        Returns:
            True if the version is supported, False otherwise
        """
        return version in cls.SUPPORTED_VERSIONS
    
    @classmethod
    def get_latest_version(cls) -> APIVersion:
        """Get the latest supported API version.
        
        Returns:
            The latest API version
        """
        return cls.CURRENT_VERSION


def get_api_version_header() -> Dict[str, str]:
    """Get API version headers for responses.
    
    Returns:
        Dictionary of headers to include in API responses
    """
    return {
        "X-API-Version": VersionInfo.CURRENT_VERSION.value,
        "X-API-Supported-Versions": ",".join([v.value for v in VersionInfo.SUPPORTED_VERSIONS])
    }


def validate_api_version(version: str) -> bool:
    """Validate if a requested API version is supported.
    
    Args:
        version: The API version string to validate
        
    Returns:
        True if valid and supported, False otherwise
    """
    try:
        api_version = APIVersion(version)
        return VersionInfo.is_supported(api_version)
    except ValueError:
        return False


class APIVersioningStrategy:
    """API versioning strategy implementation."""
    
    STRATEGY = "url_path"  # URL path versioning (e.g., /api/v1/)
    
    # Alternative strategies for future consideration:
    # STRATEGY = "header"     # Version in Accept header
    # STRATEGY = "query"      # Version in query parameter
    # STRATEGY = "subdomain"  # Version in subdomain (v1.api.example.com)
    
    @classmethod
    def get_version_from_path(cls, path: str) -> str:
        """Extract API version from URL path.
        
        Args:
            path: The URL path to extract version from
            
        Returns:
            The extracted version string, or empty string if not found
        """
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "api":
            version_part = parts[1]
            if version_part.startswith("v") and version_part[1:].isdigit():
                return version_part
        return ""
    
    @classmethod
    def build_versioned_path(cls, version: APIVersion, endpoint: str) -> str:
        """Build a versioned API path.
        
        Args:
            version: The API version
            endpoint: The endpoint path (without version)
            
        Returns:
            The complete versioned path
        """
        endpoint = endpoint.lstrip("/")
        return f"/api/{version.value}/{endpoint}"


# Version-specific feature flags
FEATURE_FLAGS = {
    APIVersion.V1: {
        "entity_extraction": True,
        "semantic_search": True,
        "timeline_visualization": True,
        "admin_management": True,
        "rate_limiting": True,
        "openapi_docs": True,
        "jwt_auth": True,
        "metadata_enrichment": True,
        "vector_search": True,
        "relationship_mapping": True,
    }
}


def is_feature_enabled(version: APIVersion, feature: str) -> bool:
    """Check if a feature is enabled for a specific API version.
    
    Args:
        version: The API version to check
        feature: The feature name to check
        
    Returns:
        True if the feature is enabled, False otherwise
    """
    version_features = FEATURE_FLAGS.get(version, {})
    return version_features.get(feature, False)


# Deprecation warnings and migration information
DEPRECATION_WARNINGS = {
    # Example for future use:
    # APIVersion.V1: {
    #     "endpoints": {
    #         "/api/v1/old-endpoint": {
    #             "deprecated_in": "v1.1",
    #             "removed_in": "v2.0",
    #             "replacement": "/api/v2/new-endpoint",
    #             "migration_guide": "https://docs.example.com/migration/v1-to-v2"
    #         }
    #     }
    # }
}


def get_deprecation_warning(version: APIVersion, endpoint: str) -> Dict[str, Any]:
    """Get deprecation warning for an endpoint if applicable.
    
    Args:
        version: The API version
        endpoint: The endpoint path
        
    Returns:
        Deprecation warning information, or empty dict if not deprecated
    """
    version_deprecations = DEPRECATION_WARNINGS.get(version, {})
    endpoint_deprecations = version_deprecations.get("endpoints", {})
    return endpoint_deprecations.get(endpoint, {})


# Content negotiation for different response formats
SUPPORTED_MEDIA_TYPES = {
    APIVersion.V1: [
        "application/json",
        "application/vnd.api+json",  # JSON:API format
        # Future formats:
        # "application/xml",
        # "text/csv",
        # "application/yaml"
    ]
}


def get_supported_media_types(version: APIVersion) -> list:
    """Get supported media types for an API version.
    
    Args:
        version: The API version
        
    Returns:
        List of supported media type strings
    """
    return SUPPORTED_MEDIA_TYPES.get(version, ["application/json"])


# API documentation metadata
API_DOCUMENTATION = {
    APIVersion.V1: {
        "openapi_url": "/api/v1/openapi.json",
        "docs_url": "/api/v1/docs",
        "redoc_url": "/api/v1/redoc",
        "postman_collection": "/api/v1/postman.json",
        "changelog_url": "/api/v1/changelog",
        "migration_guide": None  # No migration needed for initial version
    }
}


def get_documentation_urls(version: APIVersion) -> Dict[str, str]:
    """Get documentation URLs for an API version.
    
    Args:
        version: The API version
        
    Returns:
        Dictionary of documentation URLs
    """
    return API_DOCUMENTATION.get(version, {})