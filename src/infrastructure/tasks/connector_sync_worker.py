"""Connector sync worker — polls active integrations for new events.

Runs every 5 minutes alongside existing Tier 1/2 workers.
Iterates all active integration_credentials, calls each connector's fetch_events(),
and feeds results into the context event repository.
"""

import logging
import uuid
from datetime import datetime, timedelta

from src.infrastructure.database.connection import Database
from src.infrastructure.connectors.registry import ConnectorRegistry

logger = logging.getLogger(__name__)


async def sync_integrations(database: Database):
    """Poll all active integrations for new events."""
    async with database.session() as session:
        # Get all active integration credentials
        from sqlalchemy import text
        result = await session.execute(
            text("""
                SELECT id, user_id, provider, access_token, refresh_token,
                       token_expiry, metadata, last_sync_at, sync_cursor
                FROM integration_credentials
                WHERE is_active = true
            """)
        )
        credentials_rows = result.fetchall()

    if not credentials_rows:
        return

    total_events = 0

    for row in credentials_rows:
        provider = row.provider
        user_id = row.user_id

        connector = ConnectorRegistry.get(provider)
        if not connector:
            logger.warning(f"No connector registered for provider: {provider}")
            continue

        since = row.last_sync_at or (datetime.utcnow() - timedelta(days=7))

        try:
            creds = {
                "access_token": row.access_token,
                "refresh_token": row.refresh_token,
                "metadata": row.metadata or {},
            }

            events = await connector.fetch_events(user_id, since, creds)

            if events:
                # Convert to domain events and ingest
                from src.domain.entities.context_event import ContextEvent
                domain_events = []
                for e in events:
                    domain_events.append(ContextEvent(
                        id=uuid.uuid4(),
                        user_id=user_id,
                        source=e.source,
                        source_id=e.source_id,
                        event_type=e.event_type,
                        content=e.content,
                        structured_data=e.structured_data,
                        timestamp=e.timestamp,
                        extracted_people=e.extracted_people,
                        extracted_entities=e.extracted_entities,
                        tier0_at=e.tier0_at,
                    ))

                from src.infrastructure.repositories.context_event_repository import ContextEventRepository
                repo = ContextEventRepository(database)
                inserted = await repo.ingest_batch(domain_events)
                total_events += inserted

                # Update last_sync_at
                async with database.session() as session:
                    from sqlalchemy import text
                    await session.execute(
                        text("UPDATE integration_credentials SET last_sync_at = :now, updated_at = :now WHERE id = :id"),
                        {"now": datetime.utcnow(), "id": row.id},
                    )
                    await session.commit()

                logger.info(f"Synced {inserted} events from {provider} for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to sync {provider} for user {user_id}: {e}")
            continue

    if total_events > 0:
        logger.info(f"Connector sync complete: {total_events} total events ingested")
