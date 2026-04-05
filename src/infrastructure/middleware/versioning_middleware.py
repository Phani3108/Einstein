"""API versioning middleware for adding version headers to responses."""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.versioning import get_api_version_header, get_deprecation_warning, APIVersioningStrategy, APIVersion


class VersioningMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API versioning concerns."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add versioning headers to response.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            HTTP response with versioning headers added
        """
        # Extract version from URL path
        version_str = APIVersioningStrategy.get_version_from_path(str(request.url.path))
        
        # Process the request
        response = await call_next(request)
        
        # Add version headers to response
        version_headers = get_api_version_header()
        for header_name, header_value in version_headers.items():
            response.headers[header_name] = header_value
        
        # Add deprecation warnings if applicable
        if version_str:
            try:
                api_version = APIVersion(version_str)
                deprecation_info = get_deprecation_warning(api_version, str(request.url.path))
                
                if deprecation_info:
                    # Add deprecation headers
                    response.headers["X-API-Deprecated"] = "true"
                    if "deprecated_in" in deprecation_info:
                        response.headers["X-API-Deprecated-In"] = deprecation_info["deprecated_in"]
                    if "removed_in" in deprecation_info:
                        response.headers["X-API-Removed-In"] = deprecation_info["removed_in"]
                    if "replacement" in deprecation_info:
                        response.headers["X-API-Replacement"] = deprecation_info["replacement"]
                    if "migration_guide" in deprecation_info:
                        response.headers["X-API-Migration-Guide"] = deprecation_info["migration_guide"]
                        
            except ValueError:
                # Invalid version format, skip deprecation checks
                pass
        
        return response