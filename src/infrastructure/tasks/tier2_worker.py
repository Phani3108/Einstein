"""Tier 2 worker: LLM enrichment for context events.

Runs every ~5 minutes. Picks up events where tier2_at is NULL (and tier1_at is set),
sends to LLM for topic extraction, action item detection, and commitment extraction.
"""

import json
import logging
from typing import Optional
from uuid import UUID

from src.infrastructure.database.connection import Database
from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

ENRICHMENT_SYSTEM = """You are Einstein, a personal context intelligence engine.
Analyze this context event and extract structured information.

Return ONLY valid JSON:
{
  "topics": ["topic1", "topic2"],
  "action_items": [
    {"task": "description", "assignee": "person or null", "deadline": "date or null", "priority": "high|medium|low"}
  ],
  "commitments": [
    {"description": "what was committed", "person": "who it was committed to or null", "due_date": "when or null"}
  ],
  "sentiment": "positive|neutral|negative",
  "category": "work|personal|health|finance|social|learning|other",
  "key_entities": ["entity1", "entity2"]
}

If there are no action items or commitments, return empty arrays.
Focus on extracting actionable intelligence, not just summarizing."""


async def process_tier2(
    database: Database,
    llm_service: LLMService,
    user_id: UUID,
    batch_size: int = 10,
) -> int:
    """Run LLM enrichment on events that have embeddings but no Tier 2 processing.

    Args:
        database: Database connection
        llm_service: LLM service for enrichment
        user_id: User to process events for
        batch_size: Number of events per run

    Returns:
        Number of events processed
    """
    repo = ContextEventRepository(database)
    events = await repo.get_unprocessed(user_id=user_id, tier=2, limit=batch_size)

    if not events:
        return 0

    processed = 0
    for event in events:
        # Skip events with no meaningful content
        if not event.content or len(event.content.strip()) < 10:
            # Mark as processed with empty enrichment
            await repo.update_tier2(
                event.id,
                enriched_data={},
                topics=[],
                action_items=None,
            )
            processed += 1
            continue

        try:
            prompt = f"""Source: {event.source} ({event.event_type})
Timestamp: {event.timestamp.isoformat()}
Content: {event.content[:2000]}
People mentioned: {', '.join(event.extracted_people) if event.extracted_people else 'none'}"""

            raw = await llm_service.generate(prompt, system_prompt=ENRICHMENT_SYSTEM)
            data = json.loads(raw)

            topics = data.get("topics", [])
            action_items = data.get("action_items", None) or None
            enriched_data = {
                k: v
                for k, v in data.items()
                if k not in ("topics", "action_items")
            }

            await repo.update_tier2(event.id, enriched_data, topics, action_items)

            # Extract commitments if any
            commitments = data.get("commitments", [])
            if commitments:
                await _store_commitments(repo, database, user_id, event.id, commitments)

            processed += 1
            logger.debug(
                "Tier 2 processed event %s: %d topics, %d action items",
                event.id,
                len(topics),
                len(action_items) if action_items else 0,
            )
        except Exception as e:
            logger.error("Tier 2 failed for event %s: %s", event.id, e)

    logger.info("Tier 2: processed %d/%d events for user %s", processed, len(events), user_id)
    return processed


async def _store_commitments(
    repo: ContextEventRepository,
    database: Database,
    user_id: UUID,
    event_id: UUID,
    commitments: list[dict],
) -> None:
    """Store extracted commitments in the DB."""
    import uuid as uuid_mod
    from datetime import datetime
    from src.domain.entities.context_event import Commitment
    from src.infrastructure.database.models import CommitmentModel

    async with database.session() as session:
        for c in commitments:
            model = CommitmentModel(
                id=uuid_mod.uuid4(),
                user_id=user_id,
                event_id=event_id,
                description=c.get("description", ""),
                due_date=_parse_date(c.get("due_date")),
                status="open",
            )
            session.add(model)
        await session.commit()


def _parse_date(date_str: Optional[str]):
    """Best-effort date parsing."""
    if not date_str:
        return None
    from datetime import datetime
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


async def tier2_task(ctx: dict) -> int:
    """arq task entry point for Tier 2 processing."""
    database = ctx["database"]
    llm_service = ctx["llm_service"]
    from src.infrastructure.tasks.tier1_worker import _get_active_user_ids

    user_ids = await _get_active_user_ids(database)
    total = 0
    for uid in user_ids:
        total += await process_tier2(database, llm_service, uid)
    return total
