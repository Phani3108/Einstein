"""Insight generation API routes.

Briefings, prep packs, suggestions, and pattern detection —
all powered by the context event graph + LLM.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.llm.llm_service import LLMService
from src.infrastructure.services.embedding_service import OpenAIEmbeddingService
from src.domain.entities.user import User

import json


# ---- Response Models ----

class BriefingResponse(BaseModel):
    summary: str = ""
    highlights: List[str] = []
    attention_needed: List[str] = []
    themes: List[str] = []


class PrepPackResponse(BaseModel):
    summary: str = ""
    key_points: List[str] = []
    open_questions: List[str] = []
    relevant_history: List[str] = []
    suggested_actions: List[str] = []


class SuggestionOut(BaseModel):
    type: str
    title: str
    description: str
    confidence: float = 0.5


class PatternOut(BaseModel):
    theme: str
    event_count: int
    trend: str = "stable"  # growing, stable, declining
    evidence: List[str] = []


class PersonInsightOut(BaseModel):
    person_id: str
    name: str
    interaction_count: int
    last_seen: Optional[datetime]
    top_topics: List[str] = []
    recent_events: int = 0
    follow_up_needed: bool = False


class BriefingRequest(BaseModel):
    period: str = "daily"  # daily or weekly


class PrepRequest(BaseModel):
    focus_type: str = "day"  # day, meeting, project
    context: Dict[str, Any] = Field(default_factory=dict)


# ---- LLM Prompts ----

BRIEFING_SYSTEM = """You are Einstein, a personal context intelligence assistant.
Generate a concise briefing from the user's recent context events.
Return ONLY valid JSON:
{
  "summary": "1-2 paragraph summary of what happened",
  "highlights": ["Key highlight 1", "Key highlight 2"],
  "attention_needed": ["Item needing attention"],
  "themes": ["theme1", "theme2"]
}"""

PREP_SYSTEM = """You are Einstein, a personal context intelligence assistant.
Generate a focused preparation brief based on context events.
Return ONLY valid JSON:
{
  "summary": "Preparation summary",
  "key_points": ["Point 1"],
  "open_questions": ["Question 1"],
  "relevant_history": ["Relevant past event"],
  "suggested_actions": ["Action to take"]
}"""

SUGGESTIONS_SYSTEM = """You are Einstein, a proactive assistant. Based on context events, suggest actionable items.
Return ONLY valid JSON:
{
  "suggestions": [
    {"type": "follow_up|pattern|overdue|connection", "title": "Short title", "description": "Why", "confidence": 0.8}
  ]
}"""


# ---- Router Factory ----

def create_insights_router(
    context_repo: ContextEventRepository,
    llm_service: LLMService,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/insights", tags=["insights"])

    @router.post("/briefing", response_model=BriefingResponse)
    async def generate_briefing(
        req: BriefingRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Generate a daily or weekly briefing from context events."""
        days = 1 if req.period == "daily" else 7
        since = datetime.now() - timedelta(days=days)
        events = await context_repo.get_events(user_id=user.id, since=since, limit=100)

        if not events:
            return BriefingResponse(summary="No recent activity to summarize.")

        # Build context for LLM
        events_text = "\n".join(
            f"[{e.source}/{e.event_type}] {e.timestamp.isoformat()}: {(e.content or '')[:200]}"
            for e in events[:30]
        )
        prompt = f"Generate a {req.period} briefing from these {len(events)} context events:\n\n{events_text}"

        try:
            raw = await llm_service.generate(prompt, system_prompt=BRIEFING_SYSTEM)
            data = json.loads(raw)
            return BriefingResponse(**data)
        except Exception:
            return BriefingResponse(
                summary=f"You had {len(events)} events from {len(set(e.source for e in events))} sources.",
                highlights=[f"{len(events)} total context events in the last {days} day(s)"],
            )

    @router.post("/prep", response_model=PrepPackResponse)
    async def generate_prep(
        req: PrepRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Generate a preparation pack for a day, meeting, or project."""
        since = datetime.now() - timedelta(days=7)
        events = await context_repo.get_events(user_id=user.id, since=since, limit=50)
        people = await context_repo.get_people(user.id, limit=20)

        events_text = "\n".join(
            f"[{e.source}] {e.timestamp.isoformat()}: {(e.content or '')[:200]}"
            for e in events[:20]
        )
        people_text = "\n".join(f"- {p.name} ({p.role or 'unknown role'})" for p in people[:10])
        context_text = json.dumps(req.context, default=str)[:1000]

        prompt = f"""Prepare a {req.focus_type} brief.

Context: {context_text}

Recent events ({len(events)}):
{events_text}

Known people:
{people_text}

Today: {datetime.now().isoformat()[:10]}"""

        try:
            raw = await llm_service.generate(prompt, system_prompt=PREP_SYSTEM)
            data = json.loads(raw)
            return PrepPackResponse(**data)
        except Exception:
            return PrepPackResponse(summary=f"Could not generate prep. {len(events)} recent events available.")

    @router.get("/suggestions", response_model=List[SuggestionOut])
    async def get_suggestions(user: User = Depends(auth_middleware.require_authentication)):
        """Get proactive AI suggestions based on context."""
        since = datetime.now() - timedelta(days=7)
        events = await context_repo.get_events(user_id=user.id, since=since, limit=30)
        people = await context_repo.get_people(user.id, limit=10)

        events_text = "\n".join(
            f"[{e.source}] {e.timestamp.isoformat()}: {(e.content or '')[:150]}"
            for e in events[:15]
        )
        people_text = "\n".join(
            f"- {p.name}, last seen: {p.last_seen.isoformat()[:10] if p.last_seen else 'unknown'}"
            for p in people[:10]
        )

        prompt = f"""Current context:
Recent events ({len(events)}):
{events_text}

People ({len(people)}):
{people_text}

Today: {datetime.now().isoformat()[:10]}"""

        try:
            raw = await llm_service.generate(prompt, system_prompt=SUGGESTIONS_SYSTEM)
            data = json.loads(raw)
            return [SuggestionOut(**s) for s in data.get("suggestions", [])]
        except Exception:
            return []

    @router.get("/people/{person_id}", response_model=PersonInsightOut)
    async def get_person_insights(
        person_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get insights about a specific person."""
        import uuid as uuid_mod
        people = await context_repo.get_people(user.id)
        person = next((p for p in people if str(p.id) == person_id), None)
        if not person:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Person not found")

        # Find events mentioning this person
        all_events = await context_repo.get_events(user_id=user.id, limit=200)
        person_events = [
            e for e in all_events
            if person.name.lower() in (e.content or "").lower()
            or person.name in (e.extracted_people or [])
        ]

        # Extract topics from person's events
        topics: List[str] = []
        for e in person_events:
            topics.extend(e.topics or [])
        top_topics = list(set(topics))[:5]

        return PersonInsightOut(
            person_id=str(person.id),
            name=person.name,
            interaction_count=person.interaction_count,
            last_seen=person.last_seen,
            top_topics=top_topics,
            recent_events=len(person_events),
            follow_up_needed=person.last_seen is not None
            and (datetime.now() - person.last_seen).days > 14,
        )

    @router.get("/patterns", response_model=List[PatternOut])
    async def get_patterns(
        days: int = Query(default=30, le=90),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Detect recurring patterns across context events."""
        since = datetime.now() - timedelta(days=days)
        events = await context_repo.get_events(user_id=user.id, since=since, limit=200)

        # Simple pattern detection: count topics
        topic_counts: Dict[str, int] = {}
        for e in events:
            for t in (e.topics or []):
                topic_counts[t] = topic_counts.get(t, 0) + 1

        patterns = [
            PatternOut(theme=topic, event_count=count, trend="stable")
            for topic, count in sorted(topic_counts.items(), key=lambda x: -x[1])[:10]
        ]

        return patterns

    return router
