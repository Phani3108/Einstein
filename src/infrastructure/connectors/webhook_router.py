"""Inbound webhook router — receives events from third-party providers."""

from fastapi import APIRouter, Request, HTTPException

from .registry import ConnectorRegistry

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/{provider}")
async def receive_webhook(provider: str, request: Request):
    connector = ConnectorRegistry.get(provider)
    if not connector:
        raise HTTPException(404, f"Unknown provider: {provider}")

    body = await request.body()
    headers = dict(request.headers)
    payload = await request.json()

    # Verify signature if needed
    signature = (
        headers.get("x-hub-signature-256")
        or headers.get("x-slack-signature")
        or ""
    )
    # Note: webhook secret would come from integration_credentials — simplified for now

    events = await connector.handle_webhook(payload, headers)

    # Ingest events — would use context_event_repository in production
    return {"received": len(events), "provider": provider}
