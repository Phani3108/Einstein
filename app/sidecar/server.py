"""
Einstein AI Sidecar — lightweight FastAPI server for AI operations.
Spawned by the Tauri desktop app as a managed child process.
Handles entity extraction, embeddings, and semantic search.
"""

import os
import json
import sys
import logging
from typing import Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG = logging.getLogger("einstein-sidecar")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

PORT = int(os.environ.get("EINSTEIN_SIDECAR_PORT", "9721"))

# LLM provider — supports "openai", "anthropic", "ollama"
LLM_PROVIDER = os.environ.get("EINSTEIN_LLM_PROVIDER", "openai")
LLM_MODEL = os.environ.get("EINSTEIN_LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

# Embedding config
EMBEDDING_MODEL = os.environ.get("EINSTEIN_EMBEDDING_MODEL", "text-embedding-3-small")

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert entity extraction system for a personal semantic engine. Your task is to analyze text and extract meaningful entities along with their relationships. Be precise, thorough, and focus on extracting entities that would be valuable for a personal knowledge management system.

You should identify the following entity types:
- PERSON: Individual people mentioned in the text
- LOCATION: Physical places or geographic locations
- DATE: Temporal references including specific dates, time periods, or recurring events
- ACTIVITY: Actions, tasks, or activities mentioned
- EMOTION: Emotional states or feelings expressed
- ORGANIZATION: Companies, institutions, or formal groups
- EVENT: Specific events or occurrences

For each entity, provide:
1. The entity type (from the list above)
2. The entity value (the specific instance, e.g., "John Smith" for a PERSON)
3. A confidence score between 0 and 1

Your output must be valid JSON: {"entities": [{"type": "...", "value": "...", "confidence": 0.95}]}"""

EXTRACTION_PROMPT = """Extract all relevant entities from the following markdown note. Identify people, locations, dates, activities, emotions, organizations, and events.

Return ONLY valid JSON with no extra text.

NOTE CONTENT:
{content}"""

# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


async def call_llm(system: str, user: str) -> str:
    """Call the configured LLM and return the raw text response."""
    try:
        import litellm

        litellm.drop_params = True

        model = LLM_MODEL
        if LLM_PROVIDER == "ollama":
            model = f"ollama/{LLM_MODEL}"
        elif LLM_PROVIDER == "anthropic":
            model = f"anthropic/{LLM_MODEL}"

        response = await litellm.acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
            api_key=OPENAI_API_KEY or ANTHROPIC_API_KEY or None,
            api_base=OLLAMA_BASE_URL if LLM_PROVIDER == "ollama" else None,
        )
        return response.choices[0].message.content
    except ImportError:
        LOG.warning("litellm not installed, trying openai directly")
        return await _call_openai_direct(system, user)


async def _call_openai_direct(system: str, user: str) -> str:
    """Fallback: call OpenAI directly without litellm."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.0,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content
    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="No LLM library available. Install litellm or openai: pip install litellm openai",
        )


# ---------------------------------------------------------------------------
# Embedding Client
# ---------------------------------------------------------------------------


async def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts."""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
    except ImportError:
        LOG.warning("openai not installed, returning empty embeddings")
        return [[0.0] * 256 for _ in texts]
    except Exception as e:
        LOG.error(f"Embedding error: {e}")
        return [[0.0] * 256 for _ in texts]


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    content: str = Field(..., description="Markdown note content")
    note_id: Optional[str] = Field(None, description="Note ID for tracking")


class Entity(BaseModel):
    entity_type: str
    entity_value: str
    confidence: float = 0.0


class ExtractResponse(BaseModel):
    entities: list[Entity] = []
    note_id: Optional[str] = None


class EmbedRequest(BaseModel):
    texts: list[str]


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    dimension: int


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 10


class HealthResponse(BaseModel):
    status: str = "ok"
    provider: str = ""
    model: str = ""


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    LOG.info(f"Einstein AI sidecar starting on port {PORT}")
    LOG.info(f"LLM provider={LLM_PROVIDER} model={LLM_MODEL}")
    yield
    LOG.info("Einstein AI sidecar shutting down")


app = FastAPI(title="Einstein AI Sidecar", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", provider=LLM_PROVIDER, model=LLM_MODEL)


@app.post("/extract", response_model=ExtractResponse)
async def extract_entities(req: ExtractRequest):
    """Extract entities from note content using LLM."""
    if not req.content.strip():
        return ExtractResponse(entities=[], note_id=req.note_id)

    # Skip very short content
    if len(req.content.strip()) < 20:
        return ExtractResponse(entities=[], note_id=req.note_id)

    try:
        prompt = EXTRACTION_PROMPT.format(content=req.content[:8000])
        raw = await call_llm(SYSTEM_PROMPT, prompt)

        # Parse JSON response
        data = json.loads(raw)
        entities_raw = data.get("entities", [])

        entities = []
        for e in entities_raw:
            entity_type = e.get("type", "").lower()
            entity_value = e.get("value", "")
            confidence = float(e.get("confidence", 0.5))

            if entity_type and entity_value:
                entities.append(
                    Entity(
                        entity_type=entity_type,
                        entity_value=entity_value,
                        confidence=min(max(confidence, 0.0), 1.0),
                    )
                )

        LOG.info(f"Extracted {len(entities)} entities from note {req.note_id}")
        return ExtractResponse(entities=entities, note_id=req.note_id)

    except json.JSONDecodeError as e:
        LOG.error(f"LLM returned invalid JSON: {e}")
        return ExtractResponse(entities=[], note_id=req.note_id)
    except Exception as e:
        LOG.error(f"Entity extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embed", response_model=EmbedResponse)
async def embed_texts(req: EmbedRequest):
    """Generate embeddings for texts."""
    embeddings = await get_embeddings(req.texts)
    dim = len(embeddings[0]) if embeddings else 0
    return EmbedResponse(embeddings=embeddings, dimension=dim)


# ---------------------------------------------------------------------------
# RAG Endpoints
# ---------------------------------------------------------------------------

from rag_engine import (
    rag_engine,
    RAGIndexRequest,
    RAGIndexResponse,
    RAGAskRequest,
    RAGStatusResponse,
)


@app.post("/rag/index", response_model=RAGIndexResponse)
async def rag_index(req: RAGIndexRequest):
    """Index all notes into the RAG vector store."""
    try:
        result = await rag_engine.index_notes(req.notes)
        return result
    except Exception as e:
        LOG.error(f"RAG indexing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rag/ask")
async def rag_ask(req: RAGAskRequest):
    """Answer a question using RAG with SSE streaming."""

    async def event_stream():
        async for event in rag_engine.ask(
            question=req.question,
            conversation_history=req.conversation_history,
            top_k=req.top_k,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/rag/status", response_model=RAGStatusResponse)
async def rag_status():
    """Get current RAG index status."""
    return rag_engine.get_status()


class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")


class RAGSearchResultItem(BaseModel):
    note_id: str = ""
    title: str = ""
    chunk: str = ""
    score: float = 0.0


class RAGSearchResponse(BaseModel):
    results: list[RAGSearchResultItem] = []


@app.post("/rag/search", response_model=RAGSearchResponse)
async def rag_search(req: RAGSearchRequest):
    """Vector-only search — no LLM generation. Cheap and fast.
    Used by AI Tools Hub for context assembly."""
    if not rag_engine.index or not rag_engine.index.chunks:
        return RAGSearchResponse(results=[])

    try:
        from embedding_adapter import get_embedding

        query_emb = await get_embedding(req.query)
        chunk_results = rag_engine.index.search(query_emb, req.top_k)

        results = []
        seen_notes: set[str] = set()
        for cr in chunk_results:
            # Deduplicate by note — keep highest-scoring chunk per note
            if cr.chunk.note_id in seen_notes:
                continue
            seen_notes.add(cr.chunk.note_id)
            results.append(
                RAGSearchResultItem(
                    note_id=cr.chunk.note_id,
                    title=cr.chunk.title,
                    chunk=cr.chunk.text,
                    score=cr.score,
                )
            )
        return RAGSearchResponse(results=results)
    except Exception as e:
        LOG.error(f"RAG search failed: {e}")
        return RAGSearchResponse(results=[])


# ---------------------------------------------------------------------------
# Meeting Processing Endpoints
# ---------------------------------------------------------------------------

MEETING_SYSTEM_PROMPT = """You are an expert meeting analyst. Given a meeting transcript, extract structured information.

Return ONLY valid JSON with this structure:
{
  "title": "Meeting title inferred from content",
  "date": "ISO date if mentioned, otherwise null",
  "participants": ["Person1", "Person2"],
  "summary": "2-3 sentence summary of the meeting",
  "key_points": ["Point 1", "Point 2", "Point 3"],
  "action_items": [
    {"task": "What needs to be done", "assignee": "Person or null", "deadline": "ISO date or null", "priority": "high/medium/low"}
  ],
  "decisions": ["Decision 1", "Decision 2"],
  "follow_ups": [
    {"item": "Follow-up item", "date": "ISO date or null"}
  ]
}"""

MEETING_EXTRACTION_PROMPT = """Analyze the following {source} transcript and extract all structured information.

TRANSCRIPT:
{content}"""


class MeetingProcessRequest(BaseModel):
    transcript: str = Field(..., description="Meeting transcript text")
    source: str = Field(default="other", description="zoom/teams/meet/whatsapp/phone/other")
    metadata: dict = Field(default_factory=dict)


class MeetingProcessResponse(BaseModel):
    title: str = ""
    date: Optional[str] = None
    participants: list[str] = []
    summary: str = ""
    key_points: list[str] = []
    action_items: list[dict] = []
    decisions: list[str] = []
    follow_ups: list[dict] = []
    full_transcript: str = ""
    source: str = ""


@app.post("/meetings/process", response_model=MeetingProcessResponse)
async def process_meeting(req: MeetingProcessRequest):
    """Process a meeting transcript and extract structured information."""
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")

    try:
        prompt = MEETING_EXTRACTION_PROMPT.format(
            source=req.source, content=req.transcript[:12000]
        )
        raw = await call_llm(MEETING_SYSTEM_PROMPT, prompt)
        data = json.loads(raw)

        return MeetingProcessResponse(
            title=data.get("title", req.metadata.get("title", "Untitled Meeting")),
            date=data.get("date", req.metadata.get("date")),
            participants=data.get("participants", req.metadata.get("participants", [])),
            summary=data.get("summary", ""),
            key_points=data.get("key_points", []),
            action_items=data.get("action_items", []),
            decisions=data.get("decisions", []),
            follow_ups=data.get("follow_ups", []),
            full_transcript=req.transcript,
            source=req.source,
        )
    except json.JSONDecodeError:
        LOG.error("Meeting processing returned invalid JSON")
        raise HTTPException(status_code=500, detail="Failed to parse meeting data")
    except Exception as e:
        LOG.error(f"Meeting processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class WhatsAppParseRequest(BaseModel):
    content: str = Field(..., description="WhatsApp chat export text")


@app.post("/meetings/parse-whatsapp", response_model=MeetingProcessResponse)
async def parse_whatsapp(req: WhatsAppParseRequest):
    """Parse a WhatsApp chat export and extract meeting-like information."""
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Empty content")

    # Process as a meeting transcript with WhatsApp source
    meeting_req = MeetingProcessRequest(
        transcript=req.content, source="whatsapp", metadata={}
    )
    return await process_meeting(meeting_req)


# ---------------------------------------------------------------------------
# Action Item Extraction Endpoints
# ---------------------------------------------------------------------------

ACTION_SYSTEM_PROMPT = """You are an expert at extracting actionable items from notes and documents. Given text content, identify:
1. Action items / tasks with deadlines, assignees, and priorities
2. Calendar events with dates
3. Follow-ups with dates

For relative dates like "next Tuesday" or "in 2 weeks", resolve them to ISO dates relative to today's date.

Return ONLY valid JSON:
{
  "action_items": [
    {"task": "Description", "assignee": "Person or null", "deadline": "YYYY-MM-DD or null", "priority": "high/medium/low"}
  ],
  "calendar_events": [
    {"title": "Event name", "event_date": "YYYY-MM-DD", "event_type": "deadline/follow_up/meeting/reminder", "description": "Brief description"}
  ]
}"""

ACTION_EXTRACTION_PROMPT = """Today's date is {today}. Extract all action items, deadlines, and calendar events from the following note:

NOTE TITLE: {title}
NOTE CONTENT:
{content}"""


class ActionExtractRequest(BaseModel):
    content: str = Field(..., description="Note content")
    note_id: str = Field(..., description="Note ID")
    note_title: str = Field(default="", description="Note title")


class ActionExtractResponse(BaseModel):
    action_items: list[dict] = []
    calendar_events: list[dict] = []


@app.post("/extract-actions", response_model=ActionExtractResponse)
async def extract_actions(req: ActionExtractRequest):
    """Extract action items and calendar events from note content."""
    if not req.content.strip() or len(req.content.strip()) < 10:
        return ActionExtractResponse()

    try:
        from datetime import date

        prompt = ACTION_EXTRACTION_PROMPT.format(
            today=date.today().isoformat(),
            title=req.note_title,
            content=req.content[:8000],
        )
        raw = await call_llm(ACTION_SYSTEM_PROMPT, prompt)
        data = json.loads(raw)

        return ActionExtractResponse(
            action_items=data.get("action_items", []),
            calendar_events=data.get("calendar_events", []),
        )
    except json.JSONDecodeError:
        LOG.error("Action extraction returned invalid JSON")
        return ActionExtractResponse()
    except Exception as e:
        LOG.error(f"Action extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Context Hub Endpoints
# ---------------------------------------------------------------------------

BRIEFING_SYSTEM_PROMPT = """You are Einstein, an AI assistant that generates insightful daily/weekly briefings from a user's personal notes.

Generate a concise, actionable briefing that:
1. Summarizes key themes and recent activity
2. Highlights items needing attention (overdue tasks, upcoming deadlines)
3. Identifies interesting connections between different notes/topics
4. Suggests what to focus on next

Return ONLY valid JSON:
{
  "summary": "2-3 paragraph briefing in markdown format",
  "highlights": ["Top highlight 1", "Top highlight 2", "Top highlight 3"],
  "attention_needed": ["Urgent item 1", "Overdue task"],
  "themes": ["Theme 1", "Theme 2", "Theme 3"]
}"""

BRIEFING_PROMPT = """Generate a {period} briefing based on the following data:

RECENT NOTES ({note_count} notes):
{notes_summary}

PENDING ACTION ITEMS ({action_count}):
{actions_summary}

UPCOMING EVENTS ({event_count}):
{events_summary}"""

CONNECTIONS_SYSTEM_PROMPT = """You are an expert at finding meaningful connections between notes and ideas. Given a set of notes, identify non-obvious connections — shared themes, complementary ideas, contradictions, or opportunities.

Return ONLY valid JSON:
{
  "connections": [
    {
      "source_note_id": "id1",
      "target_note_id": "id2",
      "connection_type": "entity_overlap/semantic/temporal/topic",
      "description": "Clear description of the connection",
      "strength": 0.85
    }
  ]
}"""


class BriefingRequest(BaseModel):
    notes: list[dict] = Field(default_factory=list)
    action_items: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    period: str = Field(default="daily")


class BriefingResponse(BaseModel):
    summary: str = ""
    highlights: list[str] = []
    attention_needed: list[str] = []
    themes: list[str] = []


class ConnectionsRequest(BaseModel):
    notes: list[dict] = Field(default_factory=list)


class ConnectionsResponse(BaseModel):
    connections: list[dict] = []


@app.post("/context/briefing", response_model=BriefingResponse)
async def generate_briefing(req: BriefingRequest):
    """Generate an AI daily/weekly briefing from recent data."""
    if not req.notes:
        return BriefingResponse(
            summary="No recent notes found. Start writing to get personalized briefings!",
            highlights=["Create your first note to get started"],
            attention_needed=[],
            themes=[],
        )

    try:
        # Build summaries for the prompt
        notes_summary = "\n".join(
            f"- [{n.get('title', 'Untitled')}] ({n.get('created_at', 'unknown date')}): {n.get('content', '')[:200]}"
            for n in req.notes[:20]
        )
        actions_summary = "\n".join(
            f"- {a.get('task', '')} (deadline: {a.get('deadline', 'none')}, status: {a.get('status', 'pending')})"
            for a in req.action_items[:20]
        ) or "None"
        events_summary = "\n".join(
            f"- {e.get('title', '')} on {e.get('event_date', 'unknown')}"
            for e in req.events[:20]
        ) or "None"

        prompt = BRIEFING_PROMPT.format(
            period=req.period,
            note_count=len(req.notes),
            notes_summary=notes_summary,
            action_count=len(req.action_items),
            actions_summary=actions_summary,
            event_count=len(req.events),
            events_summary=events_summary,
        )
        raw = await call_llm(BRIEFING_SYSTEM_PROMPT, prompt)
        data = json.loads(raw)

        return BriefingResponse(
            summary=data.get("summary", ""),
            highlights=data.get("highlights", []),
            attention_needed=data.get("attention_needed", []),
            themes=data.get("themes", []),
        )
    except Exception as e:
        LOG.error(f"Briefing generation failed: {e}")
        return BriefingResponse(
            summary=f"Could not generate briefing: {str(e)}",
            highlights=[],
            attention_needed=[],
            themes=[],
        )


@app.post("/context/connections", response_model=ConnectionsResponse)
async def find_connections(req: ConnectionsRequest):
    """Find meaningful connections between notes."""
    if len(req.notes) < 2:
        return ConnectionsResponse(connections=[])

    try:
        notes_text = "\n\n".join(
            f"[Note ID: {n.get('id', '')}] Title: {n.get('title', 'Untitled')}\nContent: {n.get('content', '')[:300]}"
            for n in req.notes[:15]
        )
        prompt = f"Find meaningful connections between these notes:\n\n{notes_text}"
        raw = await call_llm(CONNECTIONS_SYSTEM_PROMPT, prompt)
        data = json.loads(raw)

        return ConnectionsResponse(connections=data.get("connections", []))
    except Exception as e:
        LOG.error(f"Connection finding failed: {e}")
        return ConnectionsResponse(connections=[])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")
