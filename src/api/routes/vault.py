"""Vault API routes — desktop app's primary data interface.

Exposes all endpoints that the desktop app's api.ts calls for
notes, versions, bookmarks, tags, graph, config, templates,
projects, people, decisions, associations, action items,
calendar events, and note metadata.
"""

import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.domain.entities.context_event import PersonProfile, Project
from src.domain.entities.user import User
from src.domain.entities.vault import (
    ActionItem,
    CalendarEvent,
    NoteAssociation,
    NoteMetadata,
    VaultConfig,
    VaultDecision,
    VaultNote,
    VaultNoteVersion,
)
from src.infrastructure.database.models import (
    ActionItemModel,
    CalendarEventModel,
    NoteAssociationModel,
    NoteMetadataModel,
    PersonProfileModel,
    ProjectModel,
    VaultConfigModel,
    VaultDecisionModel,
    VaultNoteModel,
    VaultNoteVersionModel,
)
from src.infrastructure.middleware.authentication_middleware import (
    AuthenticationMiddleware,
)
from src.infrastructure.repositories.context_event_repository import (
    ContextEventRepository,
)

from sqlalchemy import select, and_, delete, desc, func, or_, update


# ---------------------------------------------------------------------------
# Request / Response Pydantic models
# ---------------------------------------------------------------------------

# --- Notes ---

class OpenVaultRequest(BaseModel):
    path: str


class SaveNoteRequest(BaseModel):
    filePath: str
    title: str
    content: str = ""
    frontmatter: Dict[str, Any] = {}


class RenameNoteRequest(BaseModel):
    newTitle: str
    newFilePath: str


class MergeNotesRequest(BaseModel):
    ids: List[str]
    newTitle: str


class NoteOut(BaseModel):
    id: str
    file_path: str
    title: str
    content: str
    frontmatter: Dict[str, Any]
    outgoing_links: List[str]
    created_at: datetime
    updated_at: datetime


# --- Versions ---

class VersionOut(BaseModel):
    id: str
    note_id: str
    content: str
    frontmatter: str
    created_at: datetime


# --- Tags ---

class TagCount(BaseModel):
    tag: str
    count: int


# --- Graph ---

class GraphNode(BaseModel):
    id: str
    title: str
    file_path: str


class GraphEdge(BaseModel):
    source: str
    target: str


class GraphOut(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# --- Config ---

class ConfigValueRequest(BaseModel):
    value: str


# --- Templates ---

class TemplateOut(BaseModel):
    name: str
    content: str


class ApplyTemplateRequest(BaseModel):
    templateName: str
    noteTitle: str


# --- Projects (desktop shape) ---

class ProjectCreateRequest(BaseModel):
    title: str
    description: str = ""
    category: str = ""
    goal: str = ""
    deadline: Optional[str] = None


class ProjectUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    category: Optional[str] = None
    goal: Optional[str] = None
    deadline: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    title: str
    description: str
    status: str
    category: str
    goal: str
    deadline: Optional[str]
    created_at: datetime
    updated_at: datetime


# --- People (desktop shape) ---

class PersonCreateRequest(BaseModel):
    name: str
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    notes: str = ""


class PersonUpdateRequest(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    organization: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None


class PersonOut(BaseModel):
    id: str
    name: str
    role: Optional[str]
    organization: Optional[str]
    email: Optional[str]
    notes: str
    last_contact: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# --- Decisions ---

class DecisionCreateRequest(BaseModel):
    title: str
    description: str = ""
    reasoning: str = ""
    alternatives: str = ""
    status: str = "active"
    decided_at: str = ""
    revisit_date: Optional[str] = None


class DecisionUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    reasoning: Optional[str] = None
    alternatives: Optional[str] = None
    status: Optional[str] = None
    decided_at: Optional[str] = None
    revisit_date: Optional[str] = None


class DecisionOut(BaseModel):
    id: str
    title: str
    description: str
    reasoning: str
    alternatives: str
    status: str
    decided_at: str
    revisit_date: Optional[str]
    created_at: datetime


# --- Associations ---

class AssociationCreateRequest(BaseModel):
    noteId: str
    objectType: str
    objectId: str
    relationship: str = ""
    confidence: float = 0.5


class AssociationOut(BaseModel):
    id: str
    note_id: str
    object_type: str
    object_id: str
    relationship: str
    confidence: float
    created_at: datetime


# --- Note Metadata ---

class MetadataUpdateRequest(BaseModel):
    lifecycle: Optional[str] = None
    last_meaningful_edit: Optional[datetime] = None
    view_count: Optional[int] = None
    importance_score: Optional[float] = None
    distilled_at: Optional[datetime] = None
    source_type: Optional[str] = None


class MetadataOut(BaseModel):
    note_id: str
    lifecycle: str
    last_meaningful_edit: Optional[datetime]
    view_count: int
    importance_score: float
    distilled_at: Optional[datetime]
    source_type: str


# --- Action Items ---

class ActionItemIn(BaseModel):
    task: str
    assignee: Optional[str] = None
    deadline: Optional[str] = None
    priority: str = "medium"


class ActionItemCreateRequest(BaseModel):
    noteId: str
    items: List[ActionItemIn]


class ActionItemUpdateRequest(BaseModel):
    status: str


class ActionItemOut(BaseModel):
    id: str
    note_id: str
    task: str
    assignee: Optional[str]
    deadline: Optional[str]
    priority: str
    status: str
    created_at: datetime


# --- Calendar Events ---

class CalendarEventIn(BaseModel):
    title: str
    event_date: str
    event_type: str = "reminder"
    description: str = ""


class CalendarEventCreateRequest(BaseModel):
    noteId: str
    events: List[CalendarEventIn]


class CalendarEventOut(BaseModel):
    id: str
    note_id: str
    title: str
    event_date: str
    event_type: str
    description: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _note_out(note: VaultNote) -> NoteOut:
    return NoteOut(
        id=str(note.id),
        file_path=note.file_path,
        title=note.title,
        content=note.content,
        frontmatter=note.frontmatter,
        outgoing_links=note.outgoing_links,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def _person_out(p: PersonProfile) -> PersonOut:
    """Map context-engine PersonProfile to desktop Person shape."""
    return PersonOut(
        id=str(p.id),
        name=p.name,
        role=p.role,
        organization=p.organization,
        email=p.email,
        notes=p.notes if hasattr(p, "notes") and p.notes else "",
        last_contact=p.last_seen,
        created_at=p.created_at,
        updated_at=p.created_at,  # PersonProfile has no updated_at, use created_at
    )


def _project_out(p: Project) -> ProjectOut:
    """Map context-engine Project to desktop Project shape."""
    return ProjectOut(
        id=str(p.id),
        title=p.title,
        description=p.description,
        status=p.status,
        category="",  # context engine Project has no category field
        goal="",      # context engine Project has no goal field
        deadline=p.deadline.isoformat() if p.deadline else None,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


# ---------------------------------------------------------------------------
# Router factory
# ---------------------------------------------------------------------------

def create_vault_router(
    vault_repo: "VaultRepository",
    context_repo: ContextEventRepository,
    auth_middleware: AuthenticationMiddleware,
) -> APIRouter:
    """Create the vault API router.

    Args:
        vault_repo: Not used directly — we go straight to the DB models
                    via context_repo._database for vault-specific tables.
        context_repo: For people and projects (existing context engine tables).
        auth_middleware: JWT authentication middleware.

    Returns:
        Configured APIRouter for vault endpoints.
    """
    router = APIRouter(prefix="/api/v1/vault", tags=["vault"])
    db = context_repo._database

    # ------------------------------------------------------------------
    # NOTES
    # ------------------------------------------------------------------

    @router.post("/open", response_model=List[NoteOut])
    async def open_vault(
        req: OpenVaultRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Open a vault path and return all notes for the user."""
        async with db.session() as session:
            stmt = (
                select(VaultNoteModel)
                .where(VaultNoteModel.user_id == user.id)
                .order_by(desc(VaultNoteModel.updated_at))
            )
            result = await session.execute(stmt)
            return [_note_out(row.to_domain()) for row in result.scalars().all()]

    @router.get("/notes", response_model=List[NoteOut])
    async def get_notes(
        stale: Optional[int] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get all notes, optionally filtering for stale notes."""
        async with db.session() as session:
            stmt = select(VaultNoteModel).where(VaultNoteModel.user_id == user.id)
            if stale is not None:
                cutoff = datetime.fromtimestamp(
                    datetime.now().timestamp() - stale * 86400
                )
                stmt = stmt.where(VaultNoteModel.updated_at < cutoff)
            stmt = stmt.order_by(desc(VaultNoteModel.updated_at))
            result = await session.execute(stmt)
            return [_note_out(row.to_domain()) for row in result.scalars().all()]

    @router.get("/notes/search", response_model=List[NoteOut])
    async def search_notes(
        q: str = Query(...),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Search notes by title or content."""
        async with db.session() as session:
            pattern = f"%{q}%"
            stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        or_(
                            VaultNoteModel.title.ilike(pattern),
                            VaultNoteModel.content.ilike(pattern),
                        ),
                    )
                )
                .order_by(desc(VaultNoteModel.updated_at))
            )
            result = await session.execute(stmt)
            return [_note_out(row.to_domain()) for row in result.scalars().all()]

    @router.get("/notes/{note_id}", response_model=Optional[NoteOut])
    async def get_note(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a single note by id."""
        async with db.session() as session:
            stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                return None
            return _note_out(row.to_domain())

    @router.put("/notes", response_model=NoteOut)
    async def save_note(
        req: SaveNoteRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create or update a note. Upserts by file_path."""
        async with db.session() as session:
            # Check if note exists by file_path for this user
            stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.user_id == user.id,
                    VaultNoteModel.file_path == req.filePath,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Snapshot current version before overwriting
                version = VaultNoteVersionModel(
                    id=uuid.uuid4(),
                    note_id=existing.id,
                    content=existing.content or "",
                    frontmatter=json.dumps(existing.frontmatter or {}),
                    created_at=datetime.now(),
                )
                session.add(version)
                # Update existing note
                existing.title = req.title
                existing.content = req.content
                existing.frontmatter = req.frontmatter
                existing.updated_at = datetime.now()
                await session.commit()
                await session.refresh(existing)
                return _note_out(existing.to_domain())
            else:
                # Create new note
                note = VaultNoteModel(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    file_path=req.filePath,
                    title=req.title,
                    content=req.content,
                    frontmatter=req.frontmatter,
                    outgoing_links=[],
                    is_bookmarked=False,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(note)
                await session.commit()
                await session.refresh(note)
                return _note_out(note.to_domain())

    @router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_note(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Delete a note."""
        async with db.session() as session:
            stmt = delete(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            await session.execute(stmt)
            await session.commit()

    @router.get("/notes/{note_id}/backlinks", response_model=List[NoteOut])
    async def get_backlinks(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get notes that link to the given note."""
        async with db.session() as session:
            # First get the target note to find its file_path
            target_stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            target_result = await session.execute(target_stmt)
            target = target_result.scalar_one_or_none()
            if not target:
                return []
            # Find notes whose outgoing_links contain the target file_path
            stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        VaultNoteModel.outgoing_links.contains([target.file_path]),
                    )
                )
            )
            result = await session.execute(stmt)
            return [_note_out(row.to_domain()) for row in result.scalars().all()]

    @router.post("/notes/daily", response_model=NoteOut)
    async def create_daily_note(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create or return today's daily note."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"daily/{today}.md"
        title = f"Daily Note - {today}"

        async with db.session() as session:
            stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.user_id == user.id,
                    VaultNoteModel.file_path == file_path,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return _note_out(existing.to_domain())

            note = VaultNoteModel(
                id=uuid.uuid4(),
                user_id=user.id,
                file_path=file_path,
                title=title,
                content="",
                frontmatter={"type": "daily", "date": today},
                outgoing_links=[],
                is_bookmarked=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(note)
            await session.commit()
            await session.refresh(note)
            return _note_out(note.to_domain())

    @router.patch("/notes/{note_id}/rename", response_model=NoteOut)
    async def rename_note(
        note_id: str,
        req: RenameNoteRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Rename a note (title and file path)."""
        async with db.session() as session:
            stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            note = result.scalar_one_or_none()
            if not note:
                raise HTTPException(status_code=404, detail="Note not found")
            note.title = req.newTitle
            note.file_path = req.newFilePath
            note.updated_at = datetime.now()
            await session.commit()
            await session.refresh(note)
            return _note_out(note.to_domain())

    @router.post("/notes/merge", response_model=NoteOut)
    async def merge_notes(
        req: MergeNotesRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Merge multiple notes into one new note."""
        async with db.session() as session:
            note_ids = [uuid.UUID(nid) for nid in req.ids]
            stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        VaultNoteModel.id.in_(note_ids),
                    )
                )
                .order_by(VaultNoteModel.created_at)
            )
            result = await session.execute(stmt)
            notes = result.scalars().all()
            if not notes:
                raise HTTPException(status_code=404, detail="No notes found to merge")

            merged_content = "\n\n---\n\n".join(
                f"## {n.title}\n\n{n.content or ''}" for n in notes
            )
            all_links: List[str] = []
            for n in notes:
                all_links.extend(n.outgoing_links or [])

            new_note = VaultNoteModel(
                id=uuid.uuid4(),
                user_id=user.id,
                file_path=f"merged/{req.newTitle.replace(' ', '_')}.md",
                title=req.newTitle,
                content=merged_content,
                frontmatter={"type": "merged", "source_ids": req.ids},
                outgoing_links=list(set(all_links)),
                is_bookmarked=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(new_note)

            # Delete originals
            del_stmt = delete(VaultNoteModel).where(
                and_(
                    VaultNoteModel.user_id == user.id,
                    VaultNoteModel.id.in_(note_ids),
                )
            )
            await session.execute(del_stmt)
            await session.commit()
            await session.refresh(new_note)
            return _note_out(new_note.to_domain())

    # ------------------------------------------------------------------
    # VERSIONS
    # ------------------------------------------------------------------

    @router.get("/versions/{note_id}", response_model=List[VersionOut])
    async def list_versions(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List all versions for a note."""
        async with db.session() as session:
            # Verify note belongs to user
            note_stmt = select(VaultNoteModel.id).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            note_result = await session.execute(note_stmt)
            if not note_result.scalar_one_or_none():
                raise HTTPException(status_code=404, detail="Note not found")

            stmt = (
                select(VaultNoteVersionModel)
                .where(VaultNoteVersionModel.note_id == uuid.UUID(note_id))
                .order_by(desc(VaultNoteVersionModel.created_at))
            )
            result = await session.execute(stmt)
            return [
                VersionOut(
                    id=str(v.id),
                    note_id=str(v.note_id),
                    content=v.content or "",
                    frontmatter=v.frontmatter or "{}",
                    created_at=v.created_at,
                )
                for v in result.scalars().all()
            ]

    @router.post("/versions/{version_id}/restore", response_model=NoteOut)
    async def restore_version(
        version_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Restore a note from a previous version."""
        async with db.session() as session:
            ver_stmt = select(VaultNoteVersionModel).where(
                VaultNoteVersionModel.id == uuid.UUID(version_id)
            )
            ver_result = await session.execute(ver_stmt)
            version = ver_result.scalar_one_or_none()
            if not version:
                raise HTTPException(status_code=404, detail="Version not found")

            note_stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == version.note_id,
                    VaultNoteModel.user_id == user.id,
                )
            )
            note_result = await session.execute(note_stmt)
            note = note_result.scalar_one_or_none()
            if not note:
                raise HTTPException(status_code=404, detail="Note not found")

            # Snapshot current state as a version first
            snapshot = VaultNoteVersionModel(
                id=uuid.uuid4(),
                note_id=note.id,
                content=note.content or "",
                frontmatter=json.dumps(note.frontmatter or {}),
                created_at=datetime.now(),
            )
            session.add(snapshot)

            # Restore
            note.content = version.content
            try:
                note.frontmatter = json.loads(version.frontmatter or "{}")
            except (json.JSONDecodeError, TypeError):
                note.frontmatter = {}
            note.updated_at = datetime.now()
            await session.commit()
            await session.refresh(note)
            return _note_out(note.to_domain())

    # ------------------------------------------------------------------
    # BOOKMARKS
    # ------------------------------------------------------------------

    @router.post("/bookmarks/{note_id}/toggle")
    async def toggle_bookmark(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Toggle bookmark status for a note. Returns the new bookmark state."""
        async with db.session() as session:
            stmt = select(VaultNoteModel).where(
                and_(
                    VaultNoteModel.id == uuid.UUID(note_id),
                    VaultNoteModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            note = result.scalar_one_or_none()
            if not note:
                raise HTTPException(status_code=404, detail="Note not found")
            note.is_bookmarked = not note.is_bookmarked
            await session.commit()
            return {"bookmarked": note.is_bookmarked}

    @router.get("/bookmarks", response_model=List[NoteOut])
    async def get_bookmarks(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List all bookmarked notes."""
        async with db.session() as session:
            stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        VaultNoteModel.is_bookmarked == True,  # noqa: E712
                    )
                )
                .order_by(desc(VaultNoteModel.updated_at))
            )
            result = await session.execute(stmt)
            return [_note_out(row.to_domain()) for row in result.scalars().all()]

    # ------------------------------------------------------------------
    # TAGS
    # ------------------------------------------------------------------

    @router.get("/tags", response_model=List[TagCount])
    async def get_tags(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get all tags with counts, extracted from note frontmatter."""
        async with db.session() as session:
            stmt = select(VaultNoteModel.frontmatter).where(
                VaultNoteModel.user_id == user.id
            )
            result = await session.execute(stmt)
            tag_counts: Dict[str, int] = {}
            for (fm,) in result.all():
                if fm and isinstance(fm, dict):
                    tags = fm.get("tags", [])
                    if isinstance(tags, list):
                        for t in tags:
                            tag_counts[str(t)] = tag_counts.get(str(t), 0) + 1
            return [TagCount(tag=t, count=c) for t, c in sorted(tag_counts.items())]

    # ------------------------------------------------------------------
    # GRAPH
    # ------------------------------------------------------------------

    @router.get("/graph", response_model=GraphOut)
    async def get_graph(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Build the note link graph (nodes + edges)."""
        async with db.session() as session:
            stmt = select(VaultNoteModel).where(VaultNoteModel.user_id == user.id)
            result = await session.execute(stmt)
            notes = result.scalars().all()

            path_to_id: Dict[str, str] = {}
            nodes: List[GraphNode] = []
            for n in notes:
                nid = str(n.id)
                path_to_id[n.file_path] = nid
                nodes.append(GraphNode(id=nid, title=n.title, file_path=n.file_path))

            edges: List[GraphEdge] = []
            for n in notes:
                source_id = str(n.id)
                for link in (n.outgoing_links or []):
                    target_id = path_to_id.get(link)
                    if target_id:
                        edges.append(GraphEdge(source=source_id, target=target_id))

            return GraphOut(nodes=nodes, edges=edges)

    # ------------------------------------------------------------------
    # CONFIG
    # ------------------------------------------------------------------

    @router.get("/config/{key}")
    async def get_config(
        key: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a config value. Returns null if not set."""
        async with db.session() as session:
            stmt = select(VaultConfigModel).where(
                and_(
                    VaultConfigModel.user_id == user.id,
                    VaultConfigModel.key == key,
                )
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            return {"value": row.value if row else None}

    @router.put("/config/{key}")
    async def set_config(
        key: str,
        req: ConfigValueRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Set a config value."""
        async with db.session() as session:
            stmt = select(VaultConfigModel).where(
                and_(
                    VaultConfigModel.user_id == user.id,
                    VaultConfigModel.key == key,
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = req.value
            else:
                session.add(
                    VaultConfigModel(user_id=user.id, key=key, value=req.value)
                )
            await session.commit()
            return {"value": req.value}

    # ------------------------------------------------------------------
    # TEMPLATES
    # ------------------------------------------------------------------

    # Templates are stored as vault notes with frontmatter.type = "template".
    # The template name is the note title, and its content is the template body.

    @router.get("/templates", response_model=List[TemplateOut])
    async def list_templates(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List all templates."""
        async with db.session() as session:
            stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        VaultNoteModel.frontmatter["type"].astext == "template",
                    )
                )
                .order_by(VaultNoteModel.title)
            )
            result = await session.execute(stmt)
            return [
                TemplateOut(name=n.title, content=n.content or "")
                for n in result.scalars().all()
            ]

    @router.post("/templates/apply", response_model=NoteOut)
    async def apply_template(
        req: ApplyTemplateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create a new note from a template."""
        async with db.session() as session:
            # Find the template
            tmpl_stmt = (
                select(VaultNoteModel)
                .where(
                    and_(
                        VaultNoteModel.user_id == user.id,
                        VaultNoteModel.frontmatter["type"].astext == "template",
                        VaultNoteModel.title == req.templateName,
                    )
                )
            )
            tmpl_result = await session.execute(tmpl_stmt)
            template = tmpl_result.scalar_one_or_none()
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")

            file_path = f"notes/{req.noteTitle.replace(' ', '_')}.md"
            note = VaultNoteModel(
                id=uuid.uuid4(),
                user_id=user.id,
                file_path=file_path,
                title=req.noteTitle,
                content=template.content or "",
                frontmatter={"template": req.templateName},
                outgoing_links=[],
                is_bookmarked=False,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(note)
            await session.commit()
            await session.refresh(note)
            return _note_out(note.to_domain())

    # ------------------------------------------------------------------
    # PROJECTS (context engine tables, adapted to desktop shape)
    # ------------------------------------------------------------------

    @router.post("/projects", response_model=ProjectOut)
    async def create_project(
        req: ProjectCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create a new project."""
        deadline_dt = None
        if req.deadline:
            try:
                deadline_dt = datetime.fromisoformat(req.deadline)
            except ValueError:
                pass

        # Store category and goal in description as structured prefix
        desc_parts = []
        if req.goal:
            desc_parts.append(f"[goal:{req.goal}]")
        if req.category:
            desc_parts.append(f"[category:{req.category}]")
        if req.description:
            desc_parts.append(req.description)
        full_description = " ".join(desc_parts) if desc_parts else ""

        project = Project(
            id=uuid.uuid4(),
            user_id=user.id,
            title=req.title,
            description=full_description,
            status="active",
            deadline=deadline_dt,
        )
        result = await context_repo.create_project(project)
        return _project_out_with_extras(result, req.category, req.goal)

    @router.patch("/projects/{project_id}", response_model=ProjectOut)
    async def update_project(
        project_id: str,
        req: ProjectUpdateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Update a project."""
        async with db.session() as session:
            stmt = select(ProjectModel).where(
                and_(
                    ProjectModel.id == uuid.UUID(project_id),
                    ProjectModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            proj = result.scalar_one_or_none()
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")

            if req.title is not None:
                proj.title = req.title
            if req.description is not None:
                proj.description = req.description
            if req.status is not None:
                proj.status = req.status
            if req.deadline is not None:
                try:
                    proj.deadline = datetime.fromisoformat(req.deadline)
                except ValueError:
                    proj.deadline = None
            proj.updated_at = datetime.now()
            await session.commit()
            await session.refresh(proj)
            domain = proj.to_domain()
            category = req.category or _extract_bracket_field(domain.description, "category")
            goal = req.goal or _extract_bracket_field(domain.description, "goal")
            return _project_out_with_extras(domain, category, goal)

    @router.get("/projects", response_model=List[ProjectOut])
    async def get_projects(
        statusFilter: Optional[str] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List projects."""
        projects = await context_repo.get_projects(user.id, status=statusFilter)
        return [_project_out(p) for p in projects]

    @router.get("/projects/{project_id}", response_model=ProjectOut)
    async def get_project(
        project_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a single project."""
        async with db.session() as session:
            stmt = select(ProjectModel).where(
                and_(
                    ProjectModel.id == uuid.UUID(project_id),
                    ProjectModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            proj = result.scalar_one_or_none()
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")
            return _project_out(proj.to_domain())

    @router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_project(
        project_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Delete a project."""
        async with db.session() as session:
            stmt = delete(ProjectModel).where(
                and_(
                    ProjectModel.id == uuid.UUID(project_id),
                    ProjectModel.user_id == user.id,
                )
            )
            await session.execute(stmt)
            await session.commit()

    # ------------------------------------------------------------------
    # PEOPLE (context engine tables, adapted to desktop shape)
    # ------------------------------------------------------------------

    @router.post("/people", response_model=PersonOut)
    async def create_person(
        req: PersonCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create a person."""
        person = PersonProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            name=req.name,
            aliases=[],
            role=req.role,
            organization=req.organization,
            email=req.email,
            notes=req.notes,
        )
        result = await context_repo.upsert_person(person)
        return _person_out(result)

    @router.patch("/people/{person_id}", response_model=PersonOut)
    async def update_person(
        person_id: str,
        req: PersonUpdateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Update a person."""
        async with db.session() as session:
            stmt = select(PersonProfileModel).where(
                and_(
                    PersonProfileModel.id == uuid.UUID(person_id),
                    PersonProfileModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            person = result.scalar_one_or_none()
            if not person:
                raise HTTPException(status_code=404, detail="Person not found")

            if req.name is not None:
                person.name = req.name
            if req.role is not None:
                person.role = req.role
            if req.organization is not None:
                person.organization = req.organization
            if req.email is not None:
                person.email = req.email
            if req.notes is not None:
                person.notes = req.notes
            await session.commit()
            await session.refresh(person)
            return _person_out(person.to_domain())

    @router.get("/people", response_model=List[PersonOut])
    async def get_people(
        q: Optional[str] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List people, optionally filtering by name."""
        if q:
            async with db.session() as session:
                pattern = f"%{q}%"
                stmt = (
                    select(PersonProfileModel)
                    .where(
                        and_(
                            PersonProfileModel.user_id == user.id,
                            PersonProfileModel.name.ilike(pattern),
                        )
                    )
                    .order_by(desc(PersonProfileModel.interaction_count))
                )
                result = await session.execute(stmt)
                return [_person_out(row.to_domain()) for row in result.scalars().all()]
        else:
            people = await context_repo.get_people(user.id)
            return [_person_out(p) for p in people]

    @router.get("/people/{person_id}", response_model=PersonOut)
    async def get_person(
        person_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a single person."""
        async with db.session() as session:
            stmt = select(PersonProfileModel).where(
                and_(
                    PersonProfileModel.id == uuid.UUID(person_id),
                    PersonProfileModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            person = result.scalar_one_or_none()
            if not person:
                raise HTTPException(status_code=404, detail="Person not found")
            return _person_out(person.to_domain())

    @router.delete("/people/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_person(
        person_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Delete a person."""
        async with db.session() as session:
            stmt = delete(PersonProfileModel).where(
                and_(
                    PersonProfileModel.id == uuid.UUID(person_id),
                    PersonProfileModel.user_id == user.id,
                )
            )
            await session.execute(stmt)
            await session.commit()

    # ------------------------------------------------------------------
    # DECISIONS
    # ------------------------------------------------------------------

    @router.post("/decisions", response_model=DecisionOut)
    async def create_decision(
        req: DecisionCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create a decision."""
        async with db.session() as session:
            model = VaultDecisionModel(
                id=uuid.uuid4(),
                user_id=user.id,
                title=req.title,
                description=req.description,
                reasoning=req.reasoning,
                alternatives=req.alternatives,
                status=req.status,
                decided_at=req.decided_at,
                revisit_date=req.revisit_date,
                created_at=datetime.now(),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _decision_out(model)

    @router.patch("/decisions/{decision_id}", response_model=DecisionOut)
    async def update_decision(
        decision_id: str,
        req: DecisionUpdateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Update a decision."""
        async with db.session() as session:
            stmt = select(VaultDecisionModel).where(
                and_(
                    VaultDecisionModel.id == uuid.UUID(decision_id),
                    VaultDecisionModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            dec = result.scalar_one_or_none()
            if not dec:
                raise HTTPException(status_code=404, detail="Decision not found")

            if req.title is not None:
                dec.title = req.title
            if req.description is not None:
                dec.description = req.description
            if req.reasoning is not None:
                dec.reasoning = req.reasoning
            if req.alternatives is not None:
                dec.alternatives = req.alternatives
            if req.status is not None:
                dec.status = req.status
            if req.decided_at is not None:
                dec.decided_at = req.decided_at
            if req.revisit_date is not None:
                dec.revisit_date = req.revisit_date
            await session.commit()
            await session.refresh(dec)
            return _decision_out(dec)

    @router.get("/decisions", response_model=List[DecisionOut])
    async def list_decisions(
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """List all decisions."""
        async with db.session() as session:
            stmt = (
                select(VaultDecisionModel)
                .where(VaultDecisionModel.user_id == user.id)
                .order_by(desc(VaultDecisionModel.created_at))
            )
            result = await session.execute(stmt)
            return [_decision_out(d) for d in result.scalars().all()]

    @router.get("/decisions/{decision_id}", response_model=DecisionOut)
    async def get_decision(
        decision_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get a single decision."""
        async with db.session() as session:
            stmt = select(VaultDecisionModel).where(
                and_(
                    VaultDecisionModel.id == uuid.UUID(decision_id),
                    VaultDecisionModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            dec = result.scalar_one_or_none()
            if not dec:
                raise HTTPException(status_code=404, detail="Decision not found")
            return _decision_out(dec)

    @router.delete("/decisions/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_decision(
        decision_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Delete a decision."""
        async with db.session() as session:
            stmt = delete(VaultDecisionModel).where(
                and_(
                    VaultDecisionModel.id == uuid.UUID(decision_id),
                    VaultDecisionModel.user_id == user.id,
                )
            )
            await session.execute(stmt)
            await session.commit()

    # ------------------------------------------------------------------
    # ASSOCIATIONS
    # ------------------------------------------------------------------

    @router.post("/associations", response_model=AssociationOut)
    async def create_association(
        req: AssociationCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create a note-to-object association."""
        async with db.session() as session:
            model = NoteAssociationModel(
                id=uuid.uuid4(),
                user_id=user.id,
                note_id=uuid.UUID(req.noteId),
                object_type=req.objectType,
                object_id=uuid.UUID(req.objectId),
                relationship=req.relationship,
                confidence=req.confidence,
                created_at=datetime.now(),
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return _association_out(model)

    @router.get("/associations", response_model=List[AssociationOut])
    async def get_associations(
        noteId: Optional[str] = None,
        objectType: Optional[str] = None,
        objectId: Optional[str] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get associations filtered by note or object."""
        async with db.session() as session:
            stmt = select(NoteAssociationModel).where(
                NoteAssociationModel.user_id == user.id
            )
            if noteId:
                stmt = stmt.where(
                    NoteAssociationModel.note_id == uuid.UUID(noteId)
                )
            if objectType:
                stmt = stmt.where(NoteAssociationModel.object_type == objectType)
            if objectId:
                stmt = stmt.where(
                    NoteAssociationModel.object_id == uuid.UUID(objectId)
                )
            stmt = stmt.order_by(desc(NoteAssociationModel.created_at))
            result = await session.execute(stmt)
            return [_association_out(a) for a in result.scalars().all()]

    @router.delete(
        "/associations/{association_id}", status_code=status.HTTP_204_NO_CONTENT
    )
    async def delete_association(
        association_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Delete an association."""
        async with db.session() as session:
            stmt = delete(NoteAssociationModel).where(
                and_(
                    NoteAssociationModel.id == uuid.UUID(association_id),
                    NoteAssociationModel.user_id == user.id,
                )
            )
            await session.execute(stmt)
            await session.commit()

    # ------------------------------------------------------------------
    # NOTE METADATA
    # ------------------------------------------------------------------

    @router.get("/metadata/{note_id}", response_model=MetadataOut)
    async def get_metadata(
        note_id: str,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get metadata for a note. Creates default if not found."""
        async with db.session() as session:
            stmt = select(NoteMetadataModel).where(
                and_(
                    NoteMetadataModel.note_id == uuid.UUID(note_id),
                    NoteMetadataModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            meta = result.scalar_one_or_none()
            if not meta:
                # Return defaults
                return MetadataOut(
                    note_id=note_id,
                    lifecycle="active",
                    last_meaningful_edit=None,
                    view_count=0,
                    importance_score=0.5,
                    distilled_at=None,
                    source_type="manual",
                )
            return _metadata_out(meta)

    @router.patch("/metadata/{note_id}", response_model=MetadataOut)
    async def update_metadata(
        note_id: str,
        req: MetadataUpdateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Update metadata for a note (upserts)."""
        async with db.session() as session:
            stmt = select(NoteMetadataModel).where(
                and_(
                    NoteMetadataModel.note_id == uuid.UUID(note_id),
                    NoteMetadataModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            meta = result.scalar_one_or_none()
            if not meta:
                meta = NoteMetadataModel(
                    note_id=uuid.UUID(note_id),
                    user_id=user.id,
                )
                session.add(meta)

            if req.lifecycle is not None:
                meta.lifecycle = req.lifecycle
            if req.last_meaningful_edit is not None:
                meta.last_meaningful_edit = req.last_meaningful_edit
            if req.view_count is not None:
                meta.view_count = req.view_count
            if req.importance_score is not None:
                meta.importance_score = req.importance_score
            if req.distilled_at is not None:
                meta.distilled_at = req.distilled_at
            if req.source_type is not None:
                meta.source_type = req.source_type
            await session.commit()
            await session.refresh(meta)
            return _metadata_out(meta)

    # ------------------------------------------------------------------
    # ACTION ITEMS
    # ------------------------------------------------------------------

    @router.post("/action-items", response_model=List[ActionItemOut])
    async def create_action_items(
        req: ActionItemCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create action items for a note."""
        async with db.session() as session:
            created = []
            for item in req.items:
                model = ActionItemModel(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    note_id=uuid.UUID(req.noteId),
                    task=item.task,
                    assignee=item.assignee,
                    deadline=item.deadline,
                    priority=item.priority,
                    status="pending",
                    created_at=datetime.now(),
                )
                session.add(model)
                created.append(model)
            await session.commit()
            for m in created:
                await session.refresh(m)
            return [_action_item_out(m) for m in created]

    @router.get("/action-items", response_model=List[ActionItemOut])
    async def get_action_items(
        noteId: Optional[str] = None,
        status_filter: Optional[str] = Query(None, alias="status"),
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get action items, optionally filtered by note or status."""
        async with db.session() as session:
            stmt = select(ActionItemModel).where(ActionItemModel.user_id == user.id)
            if noteId:
                stmt = stmt.where(ActionItemModel.note_id == uuid.UUID(noteId))
            if status_filter:
                stmt = stmt.where(ActionItemModel.status == status_filter)
            stmt = stmt.order_by(desc(ActionItemModel.created_at))
            result = await session.execute(stmt)
            return [_action_item_out(a) for a in result.scalars().all()]

    @router.patch("/action-items/{item_id}", response_model=ActionItemOut)
    async def update_action_item(
        item_id: str,
        req: ActionItemUpdateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Update an action item's status."""
        async with db.session() as session:
            stmt = select(ActionItemModel).where(
                and_(
                    ActionItemModel.id == uuid.UUID(item_id),
                    ActionItemModel.user_id == user.id,
                )
            )
            result = await session.execute(stmt)
            item = result.scalar_one_or_none()
            if not item:
                raise HTTPException(status_code=404, detail="Action item not found")
            item.status = req.status
            await session.commit()
            await session.refresh(item)
            return _action_item_out(item)

    # ------------------------------------------------------------------
    # CALENDAR EVENTS
    # ------------------------------------------------------------------

    @router.post("/calendar-events", response_model=List[CalendarEventOut])
    async def create_calendar_events(
        req: CalendarEventCreateRequest,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Create calendar events linked to a note."""
        async with db.session() as session:
            created = []
            for ev in req.events:
                model = CalendarEventModel(
                    id=uuid.uuid4(),
                    user_id=user.id,
                    note_id=uuid.UUID(req.noteId),
                    title=ev.title,
                    event_date=ev.event_date,
                    event_type=ev.event_type,
                    description=ev.description,
                    created_at=datetime.now(),
                )
                session.add(model)
                created.append(model)
            await session.commit()
            for m in created:
                await session.refresh(m)
            return [_calendar_event_out(m) for m in created]

    @router.get("/calendar-events", response_model=List[CalendarEventOut])
    async def get_calendar_events(
        startDate: Optional[str] = None,
        endDate: Optional[str] = None,
        user: User = Depends(auth_middleware.require_authentication),
    ):
        """Get calendar events within a date range."""
        async with db.session() as session:
            stmt = select(CalendarEventModel).where(
                CalendarEventModel.user_id == user.id
            )
            if startDate:
                stmt = stmt.where(CalendarEventModel.event_date >= startDate)
            if endDate:
                stmt = stmt.where(CalendarEventModel.event_date <= endDate)
            stmt = stmt.order_by(CalendarEventModel.event_date)
            result = await session.execute(stmt)
            return [_calendar_event_out(e) for e in result.scalars().all()]

    # ------------------------------------------------------------------
    # Internal helpers (defined inside factory to keep them close)
    # ------------------------------------------------------------------

    return router


# ---------------------------------------------------------------------------
# Module-level helper functions used by the router
# ---------------------------------------------------------------------------

def _decision_out(d) -> DecisionOut:
    return DecisionOut(
        id=str(d.id),
        title=d.title,
        description=d.description or "",
        reasoning=d.reasoning or "",
        alternatives=d.alternatives or "",
        status=d.status or "active",
        decided_at=d.decided_at or "",
        revisit_date=d.revisit_date,
        created_at=d.created_at,
    )


def _association_out(a) -> AssociationOut:
    return AssociationOut(
        id=str(a.id),
        note_id=str(a.note_id),
        object_type=a.object_type,
        object_id=str(a.object_id),
        relationship=a.relationship or "",
        confidence=a.confidence or 0.5,
        created_at=a.created_at,
    )


def _metadata_out(m) -> MetadataOut:
    return MetadataOut(
        note_id=str(m.note_id),
        lifecycle=m.lifecycle or "active",
        last_meaningful_edit=m.last_meaningful_edit,
        view_count=m.view_count or 0,
        importance_score=m.importance_score or 0.5,
        distilled_at=m.distilled_at,
        source_type=m.source_type or "manual",
    )


def _action_item_out(a) -> ActionItemOut:
    return ActionItemOut(
        id=str(a.id),
        note_id=str(a.note_id),
        task=a.task,
        assignee=a.assignee,
        deadline=a.deadline,
        priority=a.priority or "medium",
        status=a.status or "pending",
        created_at=a.created_at,
    )


def _calendar_event_out(e) -> CalendarEventOut:
    return CalendarEventOut(
        id=str(e.id),
        note_id=str(e.note_id),
        title=e.title,
        event_date=e.event_date,
        event_type=e.event_type or "reminder",
        description=e.description or "",
        created_at=e.created_at,
    )


def _extract_bracket_field(text: str, field: str) -> str:
    """Extract [field:value] from description text."""
    import re
    match = re.search(rf"\[{field}:([^\]]*)\]", text or "")
    return match.group(1) if match else ""


def _project_out_with_extras(p: Project, category: str, goal: str) -> ProjectOut:
    """Build ProjectOut with explicit category/goal (not extracted from description)."""
    return ProjectOut(
        id=str(p.id),
        title=p.title,
        description=p.description,
        status=p.status,
        category=category or "",
        goal=goal or "",
        deadline=p.deadline.isoformat() if p.deadline else None,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )
