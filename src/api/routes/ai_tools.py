"""Contextual AI tools API routes.

Five AI-powered tools: summarize, connect, prepare, extract, ask.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.infrastructure.repositories.context_event_repository import ContextEventRepository
from src.infrastructure.middleware.authentication_middleware import AuthenticationMiddleware
from src.infrastructure.llm.llm_service import LLMService
from src.domain.entities.user import User

# Reuse PrepPackResponse from insights
from src.api.routes.insights import PrepPackResponse, PREP_SYSTEM


# ---- Request / Response Models ----

# 1. Summarize
class SummarizeRequest(BaseModel):
    content: str
    context_event_ids: List[str] = Field(default_factory=list)


class SummarizeResponse(BaseModel):
    summary: str
    key_points: List[str] = []
    word_count: int


# 2. Connect
class ConnectionItem(BaseModel):
    event_id: str
    source: str
    content_preview: str
    relevance: float
    connection_type: str  # mention, topic_overlap, person_overlap


class ConnectRequest(BaseModel):
    content: str
    limit: int = 10


class ConnectResponse(BaseModel):
    connections: List[ConnectionItem] = []


# 3. Prepare
class PrepareRequest(BaseModel):
    focus_type: str  # person, project, meeting
    focus_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)


# 4. Extract
class ActionItem(BaseModel):
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None


class Decision(BaseModel):
    title: str
    description: str = ""
    reasoning: str = ""


class CommitmentItem(BaseModel):
    description: str
    due_date: Optional[str] = None
    person: Optional[str] = None


class ExtractRequest(BaseModel):
    content: str


class ExtractResponse(BaseModel):
    action_items: List[ActionItem] = []
    decisions: List[Decision] = []
    commitments: List[CommitmentItem] = []


# 5. Ask
class AskRequest(BaseModel):
    query: str
    limit: int = 10


class SourceItem(BaseModel):
    event_id: str
    source: str
    content_preview: str
    relevance: float


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceItem] = []


# ---- LLM Prompts ----

SUMMARIZE_SYSTEM = (
    "You are Einstein, a context intelligence assistant. "
    "Summarize the following concisely. "
    'Return ONLY valid JSON: {"summary": "...", "key_points": ["..."]}'
)

EXTRACT_SYSTEM = (
    "You are Einstein, a context intelligence assistant. "
    "Extract action items, decisions, and commitments from the following content. "
    "Return ONLY valid JSON: "
    '{"action_items": [{"task": "...", "assignee": null, "deadline": null, "priority": null}], '
    '"decisions": [{"title": "...", "description": "...", "reasoning": "..."}], '
    '"commitments": [{"description": "...", "due_date": null, "person": null}]}'
)

ASK_SYSTEM = (
    "You are Einstein, a context intelligence assistant. "
    "Answer the user's question using ONLY the provided context. "
    'Return ONLY valid JSON: {"answer": "..."}'
)


# ---- Router Factory ----

def create_ai_tools_router(
    context_repo: ContextEventRepository,
    llm_service: LLMService,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1/tools", tags=["tools"])

    # ---- 1. Summarize ----

    @router.post("/summarize", response_model=SummarizeResponse)
    async def summarize(
        req: SummarizeRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Summarize any event, note, or thread with optional context events."""
        parts = [req.content]

        # Fetch additional context events if provided
        if req.context_event_ids:
            all_events = await context_repo.get_events(user_id=user.id, limit=500)
            event_map = {str(e.id): e for e in all_events}
            for eid in req.context_event_ids:
                evt = event_map.get(eid)
                if evt and evt.content:
                    parts.append(f"[Context from {evt.source}]: {evt.content[:500]}")

        full_text = "\n\n".join(parts)
        word_count = len(full_text.split())

        try:
            raw = await llm_service.generate(full_text, system_prompt=SUMMARIZE_SYSTEM)
            data = json.loads(raw)
            return SummarizeResponse(
                summary=data.get("summary", ""),
                key_points=data.get("key_points", []),
                word_count=word_count,
            )
        except Exception:
            # Graceful fallback
            truncated = full_text[:500].rsplit(" ", 1)[0] + "..."
            return SummarizeResponse(
                summary=truncated,
                key_points=[],
                word_count=word_count,
            )

    # ---- 2. Connect ----

    @router.post("/connect", response_model=ConnectResponse)
    async def connect(
        req: ConnectRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Find events related to the given content via mentions, topics, and people."""
        all_events = await context_repo.get_events(user_id=user.id, limit=500)
        query_lower = req.content.lower()

        # Extract simple keywords (words > 3 chars)
        keywords = [w for w in query_lower.split() if len(w) > 3]

        # Extract people names from query by checking against known people
        people = await context_repo.get_people(user.id, limit=100)
        known_names = {p.name.lower(): p.name for p in people}

        scored: List[Dict[str, Any]] = []

        for evt in all_events:
            content = (evt.content or "").lower()
            if not content:
                continue

            relevance = 0.0
            connection_type = "mention"

            # Direct content mention
            for kw in keywords:
                if kw in content:
                    relevance += 0.2

            # Topic overlap
            evt_topics = [t.lower() for t in (evt.topics or [])]
            for kw in keywords:
                if kw in evt_topics:
                    relevance += 0.3
                    connection_type = "topic_overlap"

            # Person overlap
            evt_people = [p.lower() for p in (evt.extracted_people or [])]
            for name_lower in known_names:
                if name_lower in query_lower and name_lower in " ".join(evt_people):
                    relevance += 0.4
                    connection_type = "person_overlap"

            if relevance > 0:
                scored.append({
                    "event_id": str(evt.id),
                    "source": evt.source,
                    "content_preview": (evt.content or "")[:200],
                    "relevance": round(min(1.0, relevance), 3),
                    "connection_type": connection_type,
                })

        # Sort by relevance descending, take top N
        scored.sort(key=lambda x: x["relevance"], reverse=True)
        connections = [ConnectionItem(**item) for item in scored[: req.limit]]

        return ConnectResponse(connections=connections)

    # ---- 3. Prepare ----

    @router.post("/prepare", response_model=PrepPackResponse)
    async def prepare(
        req: PrepareRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Generate a prep pack for a meeting, person, or project."""
        since = datetime.now() - timedelta(days=30)
        events = await context_repo.get_events(user_id=user.id, since=since, limit=100)
        people = await context_repo.get_people(user.id, limit=20)

        focus_text = ""

        if req.focus_type == "person" and req.focus_id:
            # Fetch person dossier data
            person = next((p for p in people if str(p.id) == req.focus_id), None)
            if person:
                person_events = [
                    e for e in events
                    if person.name.lower() in (e.content or "").lower()
                    or person.name in (e.extracted_people or [])
                ]
                focus_text = f"Person: {person.name} ({person.role or 'unknown role'} at {person.organization or 'unknown org'})\n"
                focus_text += f"Interactions: {person.interaction_count}\n"
                focus_text += "Recent events:\n" + "\n".join(
                    f"- [{e.source}] {e.timestamp.isoformat()[:10]}: {(e.content or '')[:150]}"
                    for e in person_events[:10]
                )
            else:
                focus_text = f"Person ID {req.focus_id} not found in contacts."

        elif req.focus_type == "project" and req.focus_id:
            # Fetch project events
            projects = await context_repo.get_projects(user.id)
            project = next((p for p in projects if str(p.id) == req.focus_id), None)
            if project:
                project_events = [
                    e for e in events
                    if project.title.lower() in (e.content or "").lower()
                ]
                focus_text = f"Project: {project.title} (status: {project.status})\n"
                focus_text += "Recent events:\n" + "\n".join(
                    f"- [{e.source}] {e.timestamp.isoformat()[:10]}: {(e.content or '')[:150]}"
                    for e in project_events[:10]
                )
            else:
                focus_text = f"Project ID {req.focus_id} not found."

        elif req.focus_type == "meeting":
            # Use context dict (title, attendees, etc.)
            ctx = req.context
            focus_text = f"Meeting: {ctx.get('title', 'Untitled')}\n"
            attendees = ctx.get("attendees", [])
            if attendees:
                focus_text += f"Attendees: {', '.join(attendees)}\n"
                # Find events mentioning attendees
                for attendee in attendees[:5]:
                    attendee_events = [
                        e for e in events
                        if attendee.lower() in (e.content or "").lower()
                    ]
                    if attendee_events:
                        focus_text += f"\nRecent context for {attendee}:\n"
                        focus_text += "\n".join(
                            f"- [{e.source}] {(e.content or '')[:100]}"
                            for e in attendee_events[:3]
                        )
            if ctx.get("agenda"):
                focus_text += f"\nAgenda: {ctx['agenda']}"
        else:
            focus_text = f"Focus: {req.focus_type}\nContext: {json.dumps(req.context, default=str)[:500]}"

        # General context
        events_text = "\n".join(
            f"[{e.source}] {e.timestamp.isoformat()[:10]}: {(e.content or '')[:150]}"
            for e in events[:15]
        )
        people_text = "\n".join(f"- {p.name} ({p.role or 'unknown role'})" for p in people[:10])

        prompt = f"""{focus_text}

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
            return PrepPackResponse(
                summary=f"Could not generate prep pack for {req.focus_type}. {len(events)} recent events available."
            )

    # ---- 4. Extract ----

    @router.post("/extract", response_model=ExtractResponse)
    async def extract(
        req: ExtractRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Extract action items, decisions, and commitments from content."""
        if not req.content.strip():
            raise HTTPException(status_code=400, detail="Content is required")

        try:
            raw = await llm_service.generate(req.content, system_prompt=EXTRACT_SYSTEM)
            data = json.loads(raw)
            return ExtractResponse(
                action_items=[ActionItem(**a) for a in data.get("action_items", [])],
                decisions=[Decision(**d) for d in data.get("decisions", [])],
                commitments=[CommitmentItem(**c) for c in data.get("commitments", [])],
            )
        except Exception:
            return ExtractResponse()

    # ---- 5. Ask ----

    @router.post("/ask", response_model=AskResponse)
    async def ask(
        req: AskRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """RAG search: answer a question using the entire context graph."""
        query_lower = req.query.lower()
        keywords = [w for w in query_lower.split() if len(w) > 3]

        # Search events by content match + entity match
        all_events = await context_repo.get_events(user_id=user.id, limit=500)
        people = await context_repo.get_people(user.id, limit=100)

        scored: List[Dict[str, Any]] = []
        for evt in all_events:
            content = (evt.content or "").lower()
            if not content:
                continue

            score = 0.0
            # Keyword match
            for kw in keywords:
                if kw in content:
                    score += 0.3

            # Entity match (people mentioned in query)
            for p in people:
                if p.name.lower() in query_lower and p.name.lower() in content:
                    score += 0.5

            # Topic match
            for t in (evt.topics or []):
                if t.lower() in query_lower:
                    score += 0.4

            if score > 0:
                scored.append({
                    "event": evt,
                    "event_id": str(evt.id),
                    "source": evt.source,
                    "content_preview": (evt.content or "")[:200],
                    "relevance": round(min(1.0, score), 3),
                })

        scored.sort(key=lambda x: x["relevance"], reverse=True)
        top = scored[: req.limit]

        sources = [
            SourceItem(
                event_id=item["event_id"],
                source=item["source"],
                content_preview=item["content_preview"],
                relevance=item["relevance"],
            )
            for item in top
        ]

        if not top:
            return AskResponse(
                answer="I couldn't find any relevant context to answer your question.",
                sources=[],
            )

        # Build context for LLM
        context_text = "\n\n".join(
            f"[{item['source']}] {(item['event'].content or '')[:300]}"
            for item in top[:10]
        )
        prompt = f"Question: {req.query}\n\nContext:\n{context_text}"

        try:
            raw = await llm_service.generate(prompt, system_prompt=ASK_SYSTEM)
            data = json.loads(raw)
            answer = data.get("answer", "Could not generate an answer.")
        except Exception:
            answer = f"Found {len(top)} relevant events but could not generate an answer."

        return AskResponse(answer=answer, sources=sources)

    return router
