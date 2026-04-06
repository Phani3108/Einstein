"""Vault repository — CRUD for notes, versions, decisions, associations, metadata, action items, calendar events."""

import json
import re
import uuid as uuid_mod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select, update, delete, func, and_, or_, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.infrastructure.database.connection import Database
from src.infrastructure.database.models import (
    VaultNoteModel,
    VaultNoteVersionModel,
    VaultDecisionModel,
    NoteAssociationModel,
    NoteMetadataModel,
    ActionItemModel,
    CalendarEventModel,
    VaultConfigModel,
)
from src.domain.entities.vault import (
    VaultNote,
    VaultNoteVersion,
    VaultDecision,
    NoteAssociation,
    NoteMetadata,
    ActionItem,
    CalendarEvent,
    VaultConfig,
)


class VaultRepository:
    def __init__(self, database: Database):
        self._database = database

    # ================================================================
    # NOTES
    # ================================================================

    async def list_notes(self, user_id: UUID) -> List[VaultNote]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(VaultNoteModel.user_id == user_id)
                .order_by(desc(VaultNoteModel.updated_at))
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def get_note(self, user_id: UUID, note_id: UUID) -> Optional[VaultNote]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(VaultNoteModel.id == note_id, VaultNoteModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            return row.to_domain() if row else None

    async def save_note(self, note: VaultNote) -> VaultNote:
        """Upsert a note — create or update."""
        async with self._database.session() as session:
            existing = await session.execute(
                select(VaultNoteModel).where(VaultNoteModel.id == note.id)
            )
            row = existing.scalar_one_or_none()
            if row:
                # Save version before overwriting
                version = VaultNoteVersionModel(
                    id=uuid_mod.uuid4(),
                    note_id=row.id,
                    content=row.content or "",
                    frontmatter=json.dumps(row.frontmatter or {}),
                    created_at=row.updated_at or datetime.now(),
                )
                session.add(version)
                # Update
                row.file_path = note.file_path
                row.title = note.title
                row.content = note.content
                row.frontmatter = note.frontmatter
                row.outgoing_links = note.outgoing_links
                row.updated_at = datetime.now()
            else:
                row = VaultNoteModel.from_domain(note)
                session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    async def delete_note(self, user_id: UUID, note_id: UUID) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(VaultNoteModel)
                .where(and_(VaultNoteModel.id == note_id, VaultNoteModel.user_id == user_id))
            )
            await session.commit()

    async def search_notes(self, user_id: UUID, query: str) -> List[VaultNote]:
        async with self._database.session() as session:
            q = f"%{query}%"
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(
                    VaultNoteModel.user_id == user_id,
                    or_(
                        VaultNoteModel.title.ilike(q),
                        VaultNoteModel.content.ilike(q),
                    )
                ))
                .order_by(desc(VaultNoteModel.updated_at))
                .limit(50)
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def get_backlinks(self, user_id: UUID, note_id: UUID) -> List[VaultNote]:
        """Find notes that link TO this note."""
        note = await self.get_note(user_id, note_id)
        if not note:
            return []
        async with self._database.session() as session:
            # Notes whose outgoing_links contain this note's title or file_path
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(
                    VaultNoteModel.user_id == user_id,
                    VaultNoteModel.id != note_id,
                    or_(
                        VaultNoteModel.content.ilike(f"%[[{note.title}]]%"),
                        VaultNoteModel.content.ilike(f"%[[{note.file_path}]]%"),
                    )
                ))
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def create_daily_note(self, user_id: UUID) -> VaultNote:
        today = datetime.now().strftime("%Y-%m-%d")
        title = f"Daily Note — {today}"
        file_path = f"daily/{today}.md"

        # Check if already exists
        existing = await self.search_notes(user_id, title)
        for n in existing:
            if n.title == title:
                return n

        note = VaultNote(
            id=uuid_mod.uuid4(),
            user_id=user_id,
            file_path=file_path,
            title=title,
            content=f"# {title}\n\n",
            frontmatter={"type": "daily"},
        )
        return await self.save_note(note)

    async def rename_note(self, user_id: UUID, note_id: UUID, new_title: str, new_file_path: str) -> Optional[VaultNote]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(VaultNoteModel.id == note_id, VaultNoteModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            row.title = new_title
            row.file_path = new_file_path
            row.updated_at = datetime.now()
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    async def get_stale_notes(self, user_id: UUID, days_threshold: int) -> List[VaultNote]:
        cutoff = datetime.now() - timedelta(days=days_threshold)
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(
                    VaultNoteModel.user_id == user_id,
                    VaultNoteModel.updated_at < cutoff,
                ))
                .order_by(VaultNoteModel.updated_at)
                .limit(50)
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def merge_notes(self, user_id: UUID, ids: List[UUID], new_title: str) -> Optional[VaultNote]:
        notes = []
        for nid in ids:
            n = await self.get_note(user_id, nid)
            if n:
                notes.append(n)
        if not notes:
            return None

        merged_content = "\n\n---\n\n".join(
            f"## {n.title}\n\n{n.content}" for n in notes
        )
        merged = VaultNote(
            id=uuid_mod.uuid4(),
            user_id=user_id,
            file_path=f"{new_title.replace(' ', '-').lower()}.md",
            title=new_title,
            content=merged_content,
            frontmatter={"merged_from": [str(nid) for nid in ids]},
        )
        saved = await self.save_note(merged)
        # Delete originals
        for nid in ids:
            await self.delete_note(user_id, nid)
        return saved

    # ================================================================
    # BOOKMARKS
    # ================================================================

    async def toggle_bookmark(self, user_id: UUID, note_id: UUID) -> bool:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(VaultNoteModel.id == note_id, VaultNoteModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            if not row:
                return False
            row.is_bookmarked = not row.is_bookmarked
            await session.commit()
            return row.is_bookmarked

    async def list_bookmarks(self, user_id: UUID) -> List[VaultNote]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteModel)
                .where(and_(VaultNoteModel.user_id == user_id, VaultNoteModel.is_bookmarked == True))
                .order_by(desc(VaultNoteModel.updated_at))
            )
            return [row.to_domain() for row in result.scalars().all()]

    # ================================================================
    # VERSIONS
    # ================================================================

    async def get_note_versions(self, note_id: UUID) -> List[VaultNoteVersion]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultNoteVersionModel)
                .where(VaultNoteVersionModel.note_id == note_id)
                .order_by(desc(VaultNoteVersionModel.created_at))
                .limit(50)
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def restore_version(self, user_id: UUID, version_id: UUID) -> Optional[VaultNote]:
        async with self._database.session() as session:
            vresult = await session.execute(
                select(VaultNoteVersionModel).where(VaultNoteVersionModel.id == version_id)
            )
            version = vresult.scalar_one_or_none()
            if not version:
                return None
            nresult = await session.execute(
                select(VaultNoteModel)
                .where(and_(VaultNoteModel.id == version.note_id, VaultNoteModel.user_id == user_id))
            )
            note = nresult.scalar_one_or_none()
            if not note:
                return None
            # Save current as a new version
            cur_version = VaultNoteVersionModel(
                id=uuid_mod.uuid4(), note_id=note.id,
                content=note.content or "", frontmatter=json.dumps(note.frontmatter or {}),
                created_at=note.updated_at or datetime.now(),
            )
            session.add(cur_version)
            # Restore
            note.content = version.content
            try:
                note.frontmatter = json.loads(version.frontmatter or "{}")
            except Exception:
                note.frontmatter = {}
            note.updated_at = datetime.now()
            await session.commit()
            await session.refresh(note)
            return note.to_domain()

    # ================================================================
    # TAGS
    # ================================================================

    async def get_all_tags(self, user_id: UUID) -> List[Dict[str, Any]]:
        notes = await self.list_notes(user_id)
        tag_counts: Dict[str, int] = {}
        for n in notes:
            fm_tags = n.frontmatter.get("tags", [])
            if isinstance(fm_tags, list):
                for t in fm_tags:
                    tag_counts[str(t)] = tag_counts.get(str(t), 0) + 1
            # Also extract #hashtags from content
            hashtags = re.findall(r"#([a-zA-Z]\w{1,30})", n.content or "")
            for h in hashtags:
                tag_counts[h] = tag_counts.get(h, 0) + 1
        return [{"tag": t, "count": c} for t, c in sorted(tag_counts.items(), key=lambda x: -x[1])]

    # ================================================================
    # GRAPH
    # ================================================================

    async def get_graph_data(self, user_id: UUID) -> Dict[str, Any]:
        notes = await self.list_notes(user_id)
        nodes = []
        edges = []
        title_to_id: Dict[str, str] = {}
        for n in notes:
            nid = str(n.id)
            nodes.append({"id": nid, "label": n.title, "node_type": "note", "file_path": n.file_path})
            title_to_id[n.title.lower()] = nid
        # Build edges from wikilinks in content
        for n in notes:
            links = re.findall(r"\[\[([^\]]+)\]\]", n.content or "")
            for link in links:
                target_id = title_to_id.get(link.lower())
                if target_id and target_id != str(n.id):
                    edges.append({"source": str(n.id), "target": target_id, "label": "links_to", "edge_type": "wikilink"})
        return {"nodes": nodes, "edges": edges}

    # ================================================================
    # TEMPLATES
    # ================================================================

    async def list_templates(self, user_id: UUID) -> List[Dict[str, str]]:
        """Templates are notes with frontmatter type=template."""
        notes = await self.list_notes(user_id)
        return [
            {"name": n.title, "content": n.content}
            for n in notes
            if n.frontmatter.get("type") == "template"
        ]

    async def create_from_template(self, user_id: UUID, template_name: str, note_title: str) -> Optional[VaultNote]:
        templates = await self.list_templates(user_id)
        template = next((t for t in templates if t["name"] == template_name), None)
        if not template:
            return None
        note = VaultNote(
            id=uuid_mod.uuid4(),
            user_id=user_id,
            file_path=f"{note_title.replace(' ', '-').lower()}.md",
            title=note_title,
            content=template["content"].replace(template_name, note_title),
            frontmatter={"from_template": template_name},
        )
        return await self.save_note(note)

    # ================================================================
    # CONFIG (key-value)
    # ================================================================

    async def get_config(self, user_id: UUID, key: str) -> Optional[str]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultConfigModel)
                .where(and_(VaultConfigModel.user_id == user_id, VaultConfigModel.key == key))
            )
            row = result.scalar_one_or_none()
            return row.value if row else None

    async def set_config(self, user_id: UUID, key: str, value: str) -> None:
        async with self._database.session() as session:
            stmt = pg_insert(VaultConfigModel).values(user_id=user_id, key=key, value=value)
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "key"],
                set_={"value": value},
            )
            await session.execute(stmt)
            await session.commit()

    # ================================================================
    # DECISIONS
    # ================================================================

    async def create_decision(self, decision: VaultDecision) -> VaultDecision:
        async with self._database.session() as session:
            row = VaultDecisionModel.from_domain(decision)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    async def update_decision(self, user_id: UUID, decision_id: UUID, changes: Dict[str, Any]) -> Optional[VaultDecision]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultDecisionModel)
                .where(and_(VaultDecisionModel.id == decision_id, VaultDecisionModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            if not row:
                return None
            for k, v in changes.items():
                if hasattr(row, k) and v is not None:
                    setattr(row, k, v)
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    async def list_decisions(self, user_id: UUID, status_filter: Optional[str] = None) -> List[VaultDecision]:
        async with self._database.session() as session:
            stmt = select(VaultDecisionModel).where(VaultDecisionModel.user_id == user_id)
            if status_filter:
                stmt = stmt.where(VaultDecisionModel.status == status_filter)
            stmt = stmt.order_by(desc(VaultDecisionModel.created_at))
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def get_decision(self, user_id: UUID, decision_id: UUID) -> Optional[VaultDecision]:
        async with self._database.session() as session:
            result = await session.execute(
                select(VaultDecisionModel)
                .where(and_(VaultDecisionModel.id == decision_id, VaultDecisionModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            return row.to_domain() if row else None

    async def delete_decision(self, user_id: UUID, decision_id: UUID) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(VaultDecisionModel)
                .where(and_(VaultDecisionModel.id == decision_id, VaultDecisionModel.user_id == user_id))
            )
            await session.commit()

    # ================================================================
    # ASSOCIATIONS
    # ================================================================

    async def create_association(self, assoc: NoteAssociation) -> NoteAssociation:
        async with self._database.session() as session:
            row = NoteAssociationModel.from_domain(assoc)
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    async def get_associations_for_note(self, note_id: UUID) -> List[NoteAssociation]:
        async with self._database.session() as session:
            result = await session.execute(
                select(NoteAssociationModel).where(NoteAssociationModel.note_id == note_id)
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def get_associations_for_object(self, object_type: str, object_id: UUID) -> List[NoteAssociation]:
        async with self._database.session() as session:
            result = await session.execute(
                select(NoteAssociationModel)
                .where(and_(NoteAssociationModel.object_type == object_type, NoteAssociationModel.object_id == object_id))
            )
            return [row.to_domain() for row in result.scalars().all()]

    async def delete_association(self, assoc_id: UUID) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(NoteAssociationModel).where(NoteAssociationModel.id == assoc_id)
            )
            await session.commit()

    # ================================================================
    # NOTE METADATA
    # ================================================================

    async def get_note_metadata(self, user_id: UUID, note_id: UUID) -> Optional[NoteMetadata]:
        async with self._database.session() as session:
            result = await session.execute(
                select(NoteMetadataModel)
                .where(and_(NoteMetadataModel.note_id == note_id, NoteMetadataModel.user_id == user_id))
            )
            row = result.scalar_one_or_none()
            return row.to_domain() if row else None

    async def upsert_note_metadata(self, metadata: NoteMetadata) -> NoteMetadata:
        async with self._database.session() as session:
            result = await session.execute(
                select(NoteMetadataModel).where(NoteMetadataModel.note_id == metadata.note_id)
            )
            row = result.scalar_one_or_none()
            if row:
                if metadata.lifecycle:
                    row.lifecycle = metadata.lifecycle
                if metadata.last_meaningful_edit:
                    row.last_meaningful_edit = metadata.last_meaningful_edit
                if metadata.view_count:
                    row.view_count = metadata.view_count
                if metadata.importance_score:
                    row.importance_score = metadata.importance_score
                if metadata.distilled_at:
                    row.distilled_at = metadata.distilled_at
                if metadata.source_type:
                    row.source_type = metadata.source_type
            else:
                row = NoteMetadataModel.from_domain(metadata)
                session.add(row)
            await session.commit()
            await session.refresh(row)
            return row.to_domain()

    # ================================================================
    # ACTION ITEMS
    # ================================================================

    async def save_action_items(self, user_id: UUID, note_id: UUID, items: List[Dict[str, Any]]) -> None:
        async with self._database.session() as session:
            # Remove existing items for this note
            await session.execute(
                delete(ActionItemModel)
                .where(and_(ActionItemModel.note_id == note_id, ActionItemModel.user_id == user_id))
            )
            # Insert new
            for item in items:
                row = ActionItemModel(
                    id=uuid_mod.uuid4(), user_id=user_id, note_id=note_id,
                    task=item.get("task", ""), assignee=item.get("assignee"),
                    deadline=item.get("deadline"), priority=item.get("priority", "medium"),
                    status=item.get("status", "pending"),
                )
                session.add(row)
            await session.commit()

    async def get_action_items(self, user_id: UUID, note_id: Optional[UUID] = None, status: Optional[str] = None) -> List[ActionItem]:
        async with self._database.session() as session:
            stmt = select(ActionItemModel).where(ActionItemModel.user_id == user_id)
            if note_id:
                stmt = stmt.where(ActionItemModel.note_id == note_id)
            if status:
                stmt = stmt.where(ActionItemModel.status == status)
            stmt = stmt.order_by(desc(ActionItemModel.created_at))
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]

    async def update_action_status(self, user_id: UUID, item_id: UUID, status: str) -> None:
        async with self._database.session() as session:
            await session.execute(
                update(ActionItemModel)
                .where(and_(ActionItemModel.id == item_id, ActionItemModel.user_id == user_id))
                .values(status=status)
            )
            await session.commit()

    # ================================================================
    # CALENDAR EVENTS
    # ================================================================

    async def save_calendar_events(self, user_id: UUID, note_id: UUID, events: List[Dict[str, Any]]) -> None:
        async with self._database.session() as session:
            await session.execute(
                delete(CalendarEventModel)
                .where(and_(CalendarEventModel.note_id == note_id, CalendarEventModel.user_id == user_id))
            )
            for ev in events:
                row = CalendarEventModel(
                    id=uuid_mod.uuid4(), user_id=user_id, note_id=note_id,
                    title=ev.get("title", ""), event_date=ev.get("event_date", ""),
                    event_type=ev.get("event_type", "reminder"),
                    description=ev.get("description", ""),
                )
                session.add(row)
            await session.commit()

    async def get_calendar_events(self, user_id: UUID, start_date: str, end_date: str) -> List[CalendarEvent]:
        async with self._database.session() as session:
            stmt = (
                select(CalendarEventModel)
                .where(and_(
                    CalendarEventModel.user_id == user_id,
                    CalendarEventModel.event_date >= start_date,
                    CalendarEventModel.event_date <= end_date,
                ))
                .order_by(CalendarEventModel.event_date)
            )
            result = await session.execute(stmt)
            return [row.to_domain() for row in result.scalars().all()]
