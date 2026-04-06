"""Tier 1 worker: Generate embeddings for unprocessed context events.

Runs every ~60 seconds. Picks up events where tier1_at is NULL,
generates embeddings via OpenAI, stores them in the DB.
"""

import logging
from typing import Optional
from uuid import UUID

from src.infrastructure.database.connection import Database
from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService

logger = logging.getLogger(__name__)


async def process_tier1(
    database: Database,
    embedding_service: OpenAIEmbeddingService,
    user_id: UUID,
    batch_size: int = 20,
) -> int:
    """Generate embeddings for unprocessed events.

    Args:
        database: Database connection
        embedding_service: OpenAI embedding service
        user_id: User to process events for
        batch_size: Number of events to process per run

    Returns:
        Number of events processed
    """
    repo = ContextEventRepository(database)
    events = await repo.get_unprocessed(user_id=user_id, tier=1, limit=batch_size)

    if not events:
        return 0

    processed = 0
    for event in events:
        try:
            # Build text for embedding from content + metadata
            text_parts = []
            if event.content:
                text_parts.append(event.content)
            if event.extracted_people:
                text_parts.append(f"People: {', '.join(event.extracted_people)}")
            if event.topics:
                text_parts.append(f"Topics: {', '.join(event.topics)}")

            text = " | ".join(text_parts) if text_parts else f"{event.source} {event.event_type}"

            embedding = await embedding_service.generate_embedding(text)
            await repo.update_tier1(event.id, embedding)
            processed += 1

            logger.debug(
                "Tier 1 processed event %s (%s/%s)",
                event.id,
                event.source,
                event.event_type,
            )
        except Exception as e:
            logger.error("Tier 1 failed for event %s: %s", event.id, e)

    logger.info("Tier 1: processed %d/%d events for user %s", processed, len(events), user_id)
    return processed


async def tier1_task(ctx: dict) -> int:
    """arq task entry point for Tier 1 processing."""
    database = ctx["database"]
    embedding_service = ctx["embedding_service"]
    user_ids = await _get_active_user_ids(database)

    total = 0
    for uid in user_ids:
        total += await process_tier1(database, embedding_service, uid)
    return total


async def _get_active_user_ids(database: Database) -> list[UUID]:
    """Get all user IDs that have context events."""
    from sqlalchemy import select, distinct
    from src.infrastructure.database.models import ContextEventModel

    async with database.session() as session:
        stmt = select(distinct(ContextEventModel.user_id))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]
