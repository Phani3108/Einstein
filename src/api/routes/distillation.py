"""Distillation API routes.

Summarize verbose events into concise distilled summaries,
with auto-distillation for old long-form content.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, update, and_, desc, func

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.llm.llm_service import LLMService
from src.infrastructure.database.models import ContextEventModel
from src.domain.entities.user import User


# ---- Request / Response Models ----

class DistillRequest(BaseModel):
    event_id: Optional[str] = None
    content: Optional[str] = None


class DistillResponse(BaseModel):
    original_length: int
    distilled_length: int
    summary: str
    key_points: List[str] = []


class AutoDistillResponse(BaseModel):
    distilled_count: int
    skipped: int


class DistillationStatusResponse(BaseModel):
    total_events: int
    distilled: int
    eligible: int


# ---- LLM Prompts ----

DISTILL_SYSTEM = """You are Einstein, a context intelligence assistant.
Distill the following content into a concise 2-3 sentence summary and extract key points.
Return ONLY valid JSON:
{
  "summary": "Concise 2-3 sentence summary",
  "key_points": ["Key point 1", "Key point 2", "Key point 3"]
}"""


# ---- Router Factory ----

def create_distillation_router(
    context_repo: ContextEventRepository,
    llm_service: LLMService,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/distillation", tags=["distillation"])

    async def _distill_content(text: str) -> Dict[str, Any]:
        """Run distillation via LLM and return parsed result."""
        raw = await llm_service.generate(text, system_prompt=DISTILL_SYSTEM)
        return json.loads(raw)

    async def _get_event(user_id: UUID, event_id: str) -> ContextEventModel:
        """Fetch a single event model by id, scoped to user."""
        async with context_repo._database.session() as session:
            stmt = select(ContextEventModel).where(
                and_(
                    ContextEventModel.id == UUID(event_id),
                    ContextEventModel.user_id == user_id,
                )
            )
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if not model:
                raise HTTPException(status_code=404, detail="Event not found")
            return model

    async def _store_distilled(event_id: UUID, summary: str, key_points: List[str]) -> None:
        """Persist distilled summary into event's structured_data."""
        async with context_repo._database.session() as session:
            stmt = select(ContextEventModel).where(ContextEventModel.id == event_id)
            result = await session.execute(stmt)
            model = result.scalar_one_or_none()
            if model:
                sd = dict(model.structured_data or {})
                sd["distilled_summary"] = {
                    "summary": summary,
                    "key_points": key_points,
                    "distilled_at": datetime.now().isoformat(),
                }
                stmt_upd = (
                    update(ContextEventModel)
                    .where(ContextEventModel.id == event_id)
                    .values(structured_data=sd)
                )
                await session.execute(stmt_upd)
                await session.commit()

    # ---- Endpoints ----

    @router.post("/distill", response_model=DistillResponse)
    async def distill_event(
        req: DistillRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Distill a long event/note into a concise summary."""
        if not req.event_id and not req.content:
            raise HTTPException(status_code=400, detail="Provide event_id or content")

        text = req.content or ""
        event_id_uuid: Optional[UUID] = None

        if req.event_id:
            model = await _get_event(user.id, req.event_id)
            text = model.content or ""
            event_id_uuid = model.id

        if not text.strip():
            raise HTTPException(status_code=400, detail="No content to distill")

        original_length = len(text)

        try:
            data = await _distill_content(text)
            summary = data.get("summary", "")
            key_points = data.get("key_points", [])
        except Exception:
            # Graceful fallback: simple truncation
            summary = text[:300].rsplit(" ", 1)[0] + "..."
            key_points = []

        distilled_length = len(summary)

        # Persist if we have an event
        if event_id_uuid:
            await _store_distilled(event_id_uuid, summary, key_points)

        return DistillResponse(
            original_length=original_length,
            distilled_length=distilled_length,
            summary=summary,
            key_points=key_points,
        )

    @router.post("/auto", response_model=AutoDistillResponse)
    async def auto_distill(
        min_words: int = Query(default=500),
        min_days: int = Query(default=7),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Trigger auto-distillation of old verbose events that haven't been distilled yet."""
        cutoff = datetime.now() - timedelta(days=min_days)
        distilled_count = 0
        skipped = 0

        async with context_repo._database.session() as session:
            # Fetch candidates: older than cutoff, with content
            stmt = (
                select(ContextEventModel)
                .where(
                    and_(
                        ContextEventModel.user_id == user.id,
                        ContextEventModel.timestamp <= cutoff,
                        ContextEventModel.content.isnot(None),
                    )
                )
                .order_by(ContextEventModel.timestamp)
                .limit(100)  # scan pool
            )
            result = await session.execute(stmt)
            candidates = result.scalars().all()

        # Filter: word count >= min_words and not already distilled
        eligible = []
        for evt in candidates:
            content = evt.content or ""
            word_count = len(content.split())
            sd = evt.structured_data or {}
            already_distilled = "distilled_summary" in sd
            if word_count >= min_words and not already_distilled:
                eligible.append(evt)
            else:
                skipped += 1

        # Distill up to 10
        for evt in eligible[:10]:
            try:
                data = await _distill_content(evt.content)
                summary = data.get("summary", "")
                key_points = data.get("key_points", [])
                await _store_distilled(evt.id, summary, key_points)
                distilled_count += 1
            except Exception:
                skipped += 1

        skipped += max(0, len(eligible) - 10)

        return AutoDistillResponse(
            distilled_count=distilled_count,
            skipped=skipped,
        )

    @router.get("/status", response_model=DistillationStatusResponse)
    async def distillation_status(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get distillation status: total events, distilled count, eligible count."""
        async with context_repo._database.session() as session:
            # Total events
            total_stmt = select(func.count()).select_from(ContextEventModel).where(
                ContextEventModel.user_id == user.id
            )
            total = (await session.execute(total_stmt)).scalar() or 0

            # Distilled: events where structured_data contains 'distilled_summary'
            distilled_stmt = (
                select(func.count())
                .select_from(ContextEventModel)
                .where(
                    and_(
                        ContextEventModel.user_id == user.id,
                        ContextEventModel.structured_data["distilled_summary"].isnot(None),
                    )
                )
            )
            try:
                distilled = (await session.execute(distilled_stmt)).scalar() or 0
            except Exception:
                # Fallback if JSONB operator fails
                distilled = 0

            # Eligible: events with content, older than 7 days, not distilled
            cutoff = datetime.now() - timedelta(days=7)
            all_stmt = (
                select(ContextEventModel)
                .where(
                    and_(
                        ContextEventModel.user_id == user.id,
                        ContextEventModel.timestamp <= cutoff,
                        ContextEventModel.content.isnot(None),
                    )
                )
            )
            result = await session.execute(all_stmt)
            eligible = 0
            for evt in result.scalars().all():
                content = evt.content or ""
                sd = evt.structured_data or {}
                if len(content.split()) >= 500 and "distilled_summary" not in sd:
                    eligible += 1

        return DistillationStatusResponse(
            total_events=total,
            distilled=distilled,
            eligible=eligible,
        )

    return router
