"""Authentication management for Einstein CLI."""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timedelta


class AuthManager:
    """Manages authentication tokens and user sessions."""

    def __init__(self, config_dir: Path):
        """Initialize authentication manager.

        Args:
            config_dir: Directory to store authentication data
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.token_file = self.config_dir / "token.json"
        self._token_data: Optional[Dict] = None

    def save_token(self, token: str, expires_in: Optional[int] = None) -> None:
        """Save authentication token to secure storage.

        Args:
            token: JWT authentication token
            expires_in: Token expiration time in seconds (optional)
        """
        token_data = {"token": token, "created_at": datetime.now().isoformat()}

        if expires_in:
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            token_data["expires_at"] = expires_at.isoformat()

        # Save to file with restricted permissions
        with open(self.token_file, "w") as f:
            json.dump(token_data, f)

        # Set file permissions to be readable only by owner
        self.token_file.chmod(0o600)
        self._token_data = token_data

    def load_token(self) -> Optional[str]:
        """Load authentication token from storage.

        Returns:
            Authentication token if valid, None otherwise
        """
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file, "r") as f:
                self._token_data = json.load(f)

            # Check if token has expired
            if self._is_token_expired():
                self.clear_token()
                return None

            return self._token_data.get("token")

        except (json.JSONDecodeError, KeyError, ValueError):
            # If token file is corrupted, clear it
            self.clear_token()
            return None

    def clear_token(self) -> None:
        """Clear stored authentication token."""
        if self.token_file.exists():
            self.token_file.unlink()
        self._token_data = None

    def is_authenticated(self) -> bool:
        """Check if user is currently authenticated.

        Returns:
            True if authenticated with valid token, False otherwise
        """
        token = self.load_token()
        return token is not None

    def get_auth_headers(self) -> Dict[str, str]:
        """Get HTTP headers for authenticated requests.

        Returns:
            Dictionary with Authorization header if authenticated, empty dict otherwise
        """
        token = self.load_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def _is_token_expired(self) -> bool:
        """Check if the current token has expired.

        Returns:
            True if token is expired, False otherwise
        """
        if not self._token_data or "expires_at" not in self._token_data:
            # If no expiration info, assume token is still valid
            return False

        try:
            expires_at = datetime.fromisoformat(self._token_data["expires_at"])
            return datetime.now() >= expires_at
        except ValueError:
            # If expiration date is malformed, consider token expired
            return True

    def get_token_info(self) -> Optional[Dict]:
        """Get information about the current token.

        Returns:
            Dictionary with token information or None if not authenticated
        """
        if not self.is_authenticated():
            return None

        info = {
            "authenticated": True,
            "created_at": self._token_data.get("created_at"),
        }

        if "expires_at" in self._token_data:
            info["expires_at"] = self._token_data["expires_at"]
            try:
                expires_at = datetime.fromisoformat(self._token_data["expires_at"])
                time_left = expires_at - datetime.now()
                info["expires_in_seconds"] = int(time_left.total_seconds())
            except ValueError:
                pass

        return info
