"""API client for communicating with Einstein server."""

import httpx
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from datetime import datetime

from einstein_cli.auth import AuthManager


class APIError(Exception):
    """Base exception for API-related errors."""

    pass


class NetworkError(APIError):
    """Raised when network communication fails."""

    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    pass


class ValidationError(APIError):
    """Raised when request validation fails."""

    pass


class ServerError(APIError):
    """Raised when server returns an error."""

    pass


class ThoughtData(BaseModel):
    """Data model for thought information."""

    id: str
    content: str
    user_id: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None
    relevance_score: Optional[float] = None  # For search results


class SearchResult(BaseModel):
    """Data model for search results."""

    thoughts: List[ThoughtData]
    total: int
    query: str
    execution_time: float
    filters_applied: Optional[Dict[str, Any]] = None


class UserStats(BaseModel):
    """Data model for user statistics."""

    total_thoughts: int
    thoughts_this_week: int
    most_common_tags: List[str]
    mood_distribution: Dict[str, int]


class APIClient:
    """HTTP client for Einstein API communication."""

    def __init__(self, base_url: str, auth_manager: AuthManager):
        """Initialize API client.

        Args:
            base_url: Base URL of the Einstein API server
            auth_manager: Authentication manager for token handling
        """
        self.base_url = base_url.rstrip("/")
        self.auth_manager = auth_manager
        self.timeout = 30.0

        # Create HTTP client with default headers
        self.client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "einstein-cli/0.1.0",
            },
        )

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    def _get_headers(self) -> Dict[str, str]:
        """Get headers including authentication if available."""
        headers = {}
        auth_headers = self.auth_manager.get_auth_headers()
        headers.update(auth_headers)
        return headers

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request body data
            params: Query parameters

        Returns:
            Response data as dictionary

        Raises:
            NetworkError: For connection issues
            AuthenticationError: For auth failures
            ValidationError: For validation errors
            ServerError: For server errors
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()

        try:
            response = await self.client.request(
                method=method, url=url, json=data, params=params, headers=headers
            )

            # Handle different response status codes
            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Please login again.")
            elif response.status_code == 422:
                error_detail = response.json().get("detail", "Validation error")
                raise ValidationError(f"Invalid request: {error_detail}")
            elif response.status_code >= 500:
                raise ServerError(f"Server error: {response.status_code}")
            elif response.status_code >= 400:
                error_detail = response.json().get("detail", "Request failed")
                raise APIError(f"API error: {error_detail}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise NetworkError(f"Could not connect to server: {e}")
        except httpx.TimeoutException:
            raise NetworkError("Request timed out")
        except httpx.HTTPStatusError as e:
            raise ServerError(f"HTTP error: {e.response.status_code}")

    async def authenticate(self, email: str, password: str) -> str:
        """Authenticate user and return access token.

        Args:
            email: User email address
            password: User password

        Returns:
            Access token string

        Raises:
            AuthenticationError: If credentials are invalid
        """
        data = {
            "username": email,  # FastAPI OAuth2 uses 'username' field
            "password": password,
        }

        try:
            # Use form data for OAuth2 token endpoint
            response = await self.client.post(
                f"{self.base_url}/auth/token",
                data=data,  # Form data, not JSON
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 401:
                raise AuthenticationError("Invalid email or password")

            response.raise_for_status()
            token_data = response.json()

            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in")

            # Save token using auth manager
            self.auth_manager.save_token(access_token, expires_in)

            return access_token

        except httpx.ConnectError as e:
            raise NetworkError(f"Could not connect to server: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise AuthenticationError("Invalid email or password")
            raise ServerError(f"Authentication failed: {e.response.status_code}")

    async def refresh_token(self) -> str:
        """Refresh the current authentication token.

        Returns:
            New access token string

        Raises:
            AuthenticationError: If token refresh fails
            NetworkError: If network communication fails
        """
        current_token = self.auth_manager.load_token()
        if not current_token:
            raise AuthenticationError("No token available to refresh")

        try:
            response = await self.client.post(
                f"{self.base_url}/auth/refresh",
                headers={"Authorization": f"Bearer {current_token}"},
            )

            if response.status_code == 401:
                # Clear invalid token and raise error
                self.auth_manager.clear_token()
                raise AuthenticationError("Token refresh failed. Please login again.")

            response.raise_for_status()
            token_data = response.json()

            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in")

            # Save new token
            self.auth_manager.save_token(access_token, expires_in)

            return access_token

        except httpx.ConnectError as e:
            raise NetworkError(f"Could not connect to server: {e}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.auth_manager.clear_token()
                raise AuthenticationError("Token refresh failed. Please login again.")
            raise ServerError(f"Token refresh failed: {e.response.status_code}")

    async def logout(self) -> bool:
        """Logout user and clear stored token.

        Returns:
            True if logout was successful
        """
        token = self.auth_manager.load_token()
        if token:
            try:
                # Attempt to invalidate token on server
                await self.client.post(
                    f"{self.base_url}/auth/logout",
                    headers={"Authorization": f"Bearer {token}"},
                )
            except (httpx.HTTPError, httpx.ConnectError):
                # If server logout fails, still clear local token
                pass

        # Always clear local token
        self.auth_manager.clear_token()
        return True

    async def create_thought(
        self, content: str, metadata: Optional[Dict] = None
    ) -> ThoughtData:
        """Create a new thought.

        Args:
            content: Thought content
            metadata: Optional metadata dictionary

        Returns:
            Created thought data
        """
        data = {"content": content}
        if metadata:
            data["metadata"] = metadata

        response = await self._make_request("POST", "/api/v1/thoughts", data=data)
        return ThoughtData(**response)

    async def search_thoughts(
        self, query: str, limit: int = 20, filters: Optional[Dict] = None
    ) -> SearchResult:
        """Search thoughts using semantic search.

        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional search filters (mood, tags, since, until, min_score, sort)

        Returns:
            Search results
        """
        params = {"q": query, "limit": limit}
        
        if filters:
            # Handle different filter types appropriately
            for key, value in filters.items():
                if key == "tags" and isinstance(value, list):
                    # Convert tag list to comma-separated string for API
                    params["tags"] = ",".join(value)
                elif key in ["since", "until"]:
                    # Date filters - pass as ISO strings
                    params[key] = value
                elif key == "min_score":
                    # Numeric filter
                    params["min_score"] = value
                elif key == "sort":
                    # Sort parameter
                    params["sort"] = value
                else:
                    # Other filters (mood, etc.)
                    params[key] = value

        response = await self._make_request("GET", "/api/v1/search", params=params)
        return SearchResult(**response)

    async def get_thoughts(
        self, limit: int = 20, offset: int = 0, filters: Optional[Dict] = None
    ) -> List[ThoughtData]:
        """Get list of thoughts.

        Args:
            limit: Maximum number of thoughts to return
            offset: Number of thoughts to skip
            filters: Optional filters

        Returns:
            List of thoughts
        """
        params = {"limit": limit, "offset": offset}
        if filters:
            params.update(filters)

        response = await self._make_request("GET", "/api/v1/thoughts", params=params)
        return [ThoughtData(**thought) for thought in response["thoughts"]]

    async def get_thought_by_id(self, thought_id: str) -> ThoughtData:
        """Get a specific thought by ID.

        Args:
            thought_id: Unique thought identifier

        Returns:
            Thought data
        """
        response = await self._make_request("GET", f"/api/v1/thoughts/{thought_id}")
        return ThoughtData(**response)

    async def delete_thought(self, thought_id: str) -> bool:
        """Delete a thought by ID.

        Args:
            thought_id: Unique thought identifier

        Returns:
            True if deletion was successful
        """
        await self._make_request("DELETE", f"/api/v1/thoughts/{thought_id}")
        return True

    async def get_user_stats(self) -> UserStats:
        """Get user statistics and analytics.

        Returns:
            User statistics data
        """
        response = await self._make_request("GET", "/api/v1/admin/stats")
        return UserStats(**response)

    async def health_check(self) -> Dict[str, Any]:
        """Check API server health.

        Returns:
            Health status information
        """
        return await self._make_request("GET", "/health")
