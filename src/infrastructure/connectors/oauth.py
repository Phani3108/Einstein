"""Shared OAuth2 helpers for connector authentication flows."""

from typing import Any, Dict, List
from urllib.parse import urlencode

import httpx

# Provider-specific OAuth2 endpoints
PROVIDER_CONFIG: Dict[str, Dict[str, str]] = {
    "gmail": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
    },
    "jira": {
        "authorize_url": "https://auth.atlassian.com/authorize",
        "token_url": "https://auth.atlassian.com/oauth/token",
    },
    "slack": {
        "authorize_url": "https://slack.com/oauth/v2/authorize",
        "token_url": "https://slack.com/api/oauth.v2.access",
    },
    "zoom": {
        "authorize_url": "https://zoom.us/oauth/authorize",
        "token_url": "https://zoom.us/oauth/token",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
    },
    "linear": {
        "authorize_url": "https://linear.app/oauth/authorize",
        "token_url": "https://api.linear.app/oauth/token",
    },
}


def build_authorize_url(
    provider: str,
    client_id: str,
    redirect_uri: str,
    scopes: List[str],
    state: str = "",
) -> str:
    """Build the OAuth2 authorization URL for a given provider."""
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown OAuth2 provider: {provider}")

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(scopes),
    }
    if state:
        params["state"] = state

    # Atlassian (Jira) uses audience param
    if provider == "jira":
        params["audience"] = "api.atlassian.com"
        params["prompt"] = "consent"

    return f"{config['authorize_url']}?{urlencode(params)}"


async def exchange_code(
    provider: str,
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> Dict[str, Any]:
    """Exchange an authorization code for access/refresh tokens."""
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown OAuth2 provider: {provider}")

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config["token_url"], data=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
    }


async def refresh_token(
    provider: str,
    refresh_tok: str,
    client_id: str,
    client_secret: str,
) -> Dict[str, Any]:
    """Refresh an expired access token."""
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        raise ValueError(f"Unknown OAuth2 provider: {provider}")

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_tok,
        "client_id": client_id,
        "client_secret": client_secret,
    }

    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            config["token_url"], data=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()

    return {
        "access_token": data.get("access_token"),
        "refresh_token": data.get("refresh_token"),
        "expires_in": data.get("expires_in"),
    }
