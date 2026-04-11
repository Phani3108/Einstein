"""Inbound webhook router — receives events from third-party providers."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Request, HTTPException, Depends

from src.infrastructure.connectors.registry import ConnectorRegistry
from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.domain.entities.context_event import ContextEvent


def create_webhook_router(
    context_repo: ContextEventRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

    @router.post("/{provider}")
    async def receive_webhook(provider: str, request: Request):
        connector = ConnectorRegistry.get(provider)
        if not connector:
            raise HTTPException(404, f"Unknown provider: {provider}")

        body = await request.body()
        headers = dict(request.headers)
        payload = await request.json()

        events = await connector.handle_webhook(payload, headers)

        if events:
            domain_events = []
            for ev in events:
                domain_events.append(
                    ContextEvent(
                        id=uuid.uuid4(),
                        user_id=ev.user_id if hasattr(ev, "user_id") else uuid.UUID("60bd95e0-1d86-49a0-99c4-1b72773ba450"),
                        source=ev.source if hasattr(ev, "source") else provider,
                        source_id=getattr(ev, "source_id", None),
                        event_type=ev.event_type if hasattr(ev, "event_type") else "webhook",
                        content=ev.content if hasattr(ev, "content") else str(payload)[:1000],
                        structured_data=ev.structured_data if hasattr(ev, "structured_data") else {},
                        timestamp=ev.timestamp if hasattr(ev, "timestamp") else datetime.utcnow(),
                        extracted_entities=getattr(ev, "extracted_entities", None),
                        extracted_people=getattr(ev, "extracted_people", []),
                        tier0_at=datetime.utcnow(),
                    )
                )
            inserted = await context_repo.ingest_batch(domain_events)
            return {"received": len(events), "ingested": inserted, "provider": provider}

        return {"received": 0, "ingested": 0, "provider": provider}

    return router
