"""Integration management API routes.

Endpoints for connecting/disconnecting third-party providers,
handling OAuth callbacks, and triggering manual syncs.
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.connectors.oauth import build_authorize_url, exchange_code
from src.infrastructure.connectors.registry import ConnectorRegistry
from src.domain.entities.user import User


# ---- Request/Response Models ----

class ConnectRequest(BaseModel):
    provider: str
    redirect_uri: str


class ConnectResponse(BaseModel):
    authorize_url: str


class IntegrationOut(BaseModel):
    provider: str
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime


class SyncResponse(BaseModel):
    provider: str
    events_fetched: int


# ---- Router Factory ----

def create_integrations_router(
    context_repo: ContextEventRepository,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/integrations", tags=["integrations"])

    # ---- List connected integrations ----

    @router.get("", response_model=List[IntegrationOut])
    async def list_integrations(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List user's connected integrations."""
        rows = await context_repo.get_integration_credentials(user.id)
        return [
            IntegrationOut(
                provider=r["provider"],
                is_active=r["is_active"],
                last_sync_at=r.get("last_sync_at"),
                created_at=r["created_at"],
            )
            for r in rows
        ]

    # ---- Start OAuth connect flow ----

    @router.post("/connect", response_model=ConnectResponse)
    async def connect_provider(
        req: ConnectRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Initiate OAuth2 flow for a provider. Returns the authorization URL."""
        # Scopes per provider (sensible defaults)
        default_scopes: Dict[str, List[str]] = {
            "gmail": ["https://www.googleapis.com/auth/gmail.readonly"],
            "slack": ["channels:history", "channels:read", "users:read"],
            "jira": ["read:jira-work", "read:jira-user"],
            "zoom": ["meeting:read"],
            "github": ["repo", "read:user"],
            "linear": ["read"],
        }

        scopes = default_scopes.get(req.provider, [])
        client_id = os.getenv(f"{req.provider.upper()}_CLIENT_ID", "")
        if not client_id:
            raise HTTPException(400, f"Provider {req.provider} is not configured")

        url = build_authorize_url(
            provider=req.provider,
            client_id=client_id,
            redirect_uri=req.redirect_uri,
            scopes=scopes,
            state=str(user.id),
        )
        return ConnectResponse(authorize_url=url)

    # ---- OAuth callback ----

    @router.get("/callback/{provider}")
    async def oauth_callback(
        provider: str,
        code: str = Query(...),
        state: str = Query(""),
    ):
        """Handle OAuth2 callback — exchange code for tokens and store credentials."""
        client_id = os.getenv(f"{provider.upper()}_CLIENT_ID", "")
        client_secret = os.getenv(f"{provider.upper()}_CLIENT_SECRET", "")
        redirect_uri = os.getenv(f"{provider.upper()}_REDIRECT_URI", "")

        if not client_id or not client_secret:
            raise HTTPException(400, f"Provider {provider} is not configured")

        try:
            tokens = await exchange_code(
                provider=provider,
                code=code,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
            )
        except Exception as exc:
            raise HTTPException(502, f"Token exchange failed: {exc}")

        # state carries user_id
        try:
            user_id = uuid.UUID(state)
        except ValueError:
            raise HTTPException(400, "Invalid state parameter")

        token_expiry = None
        if tokens.get("expires_in"):
            token_expiry = datetime.now() + timedelta(seconds=tokens["expires_in"])

        await context_repo.upsert_integration_credential(
            user_id=user_id,
            provider=provider,
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            token_expiry=token_expiry,
        )

        return {"status": "connected", "provider": provider}

    # ---- Disconnect (soft delete) ----

    @router.delete("/{provider}")
    async def disconnect_provider(
        provider: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Soft-delete an integration (set is_active=false)."""
        await context_repo.deactivate_integration(user.id, provider)
        return {"status": "disconnected", "provider": provider}

    # ---- Manual sync ----

    @router.post("/{provider}/sync", response_model=SyncResponse)
    async def trigger_sync(
        provider: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Trigger a manual sync for a provider."""
        connector = ConnectorRegistry.get(provider)
        if not connector:
            raise HTTPException(404, f"No connector registered for: {provider}")

        creds = await context_repo.get_integration_credential(user.id, provider)
        if not creds or not creds.get("is_active"):
            raise HTTPException(400, f"No active integration for: {provider}")

        since = creds.get("last_sync_at") or datetime(2020, 1, 1)
        events = await connector.fetch_events(
            user_id=user.id,
            since=since,
            credentials=creds,
        )

        # Ingest fetched events
        if events:
            from src.domain.entities.context_event import ContextEvent

            domain_events = []
            for ev in events:
                domain_events.append(
                    ContextEvent(
                        id=uuid.uuid4(),
                        user_id=user.id,
                        source=ev.source,
                        source_id=ev.source_id,
                        event_type=ev.event_type,
                        content=ev.content,
                        structured_data=ev.structured_data,
                        timestamp=ev.timestamp,
                        extracted_entities=ev.extracted_entities,
                        extracted_people=ev.extracted_people,
                        tier0_at=ev.tier0_at,
                    )
                )
            await context_repo.ingest_batch(domain_events)

        # Update last_sync_at
        await context_repo.update_sync_cursor(
            user.id, provider, cursor=None, last_sync_at=datetime.now()
        )

        return SyncResponse(provider=provider, events_fetched=len(events))

    return router
