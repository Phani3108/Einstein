"""Einstein SDK — client for vault operations."""

import json
import sqlite3
import os
from pathlib import Path
from typing import Optional, Union
from .types import Note, GraphData, GraphNode, GraphEdge, Entity, Tag


class EinsteinClient:
    """
    Client for Einstein vault operations.

    Supports two modes:
    1. Direct SQLite access (vault_path) — works without any server running
    2. HTTP client (url) — connects to a running Einstein sidecar or MCP server

    Args:
        vault_path: Path to the Einstein vault directory
        url: URL of the Einstein sidecar/MCP server
    """

    def __init__(self, vault_path: str = None, url: str = None):
        self.vault_path = Path(os.path.expanduser(vault_path)) if vault_path else None
        self.url = url
        self._conn: Optional[sqlite3.Connection] = None

        if self.vault_path:
            db_path = self.vault_path / ".einstein" / "index.sqlite"
            if not db_path.exists():
                raise FileNotFoundError(
                    f"Einstein vault database not found at {db_path}. "
                    "Open the vault in Einstein desktop app first."
                )
            self._conn = sqlite3.connect(str(db_path), timeout=10)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")

    def __del__(self):
        if self._conn:
            self._conn.close()

    def _require_db(self):
        if not self._conn:
            raise RuntimeError("No vault connection. Initialize with vault_path or url.")

    # --- Search ---

    def search(self, query: str, limit: int = 20) -> list[Note]:
        """Search notes by content or title."""
        if self.url:
            return self._http_search(query, limit)
        self._require_db()
        try:
            rows = self._conn.execute(
                """SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
                   FROM notes_fts fts JOIN notes n ON n.rowid = fts.rowid
                   WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?""",
                (query, limit),
            ).fetchall()
        except Exception:
            rows = self._conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE title LIKE ? OR content LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [self._row_to_note(r) for r in rows]

    # --- CRUD ---

    def get_note(self, note_id: str = None, title: str = None) -> Optional[Note]:
        """Get a note by ID or title."""
        self._require_db()
        if note_id:
            row = self._conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        elif title:
            row = self._conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE title = ? COLLATE NOCASE",
                (title,),
            ).fetchone()
        else:
            return None
        return self._row_to_note(row) if row else None

    def create_note(self, title: str, content: str, folder: str = None, tags: list[str] = None) -> Note:
        """Create a new note."""
        self._require_db()
        import uuid
        from datetime import datetime

        note_id = str(uuid.uuid4())
        file_name = title.replace(" ", "-").lower() + ".md"
        file_path = f"{folder}/{file_name}" if folder else file_name
        now = datetime.utcnow().isoformat()
        fm = {}
        if tags:
            fm["tags"] = ", ".join(tags)

        self._conn.execute(
            "INSERT INTO notes (id, file_path, title, content, frontmatter, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (note_id, file_path, title, content, json.dumps(fm), now, now),
        )
        self._conn.commit()

        # Write to disk
        if self.vault_path:
            full_path = self.vault_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            file_content = content
            if fm:
                header = "---\n" + "".join(f"{k}: {v}\n" for k, v in fm.items()) + "---\n\n"
                file_content = header + content
            full_path.write_text(file_content)

        return Note(id=note_id, file_path=file_path, title=title, content=content, frontmatter=fm, created_at=now, updated_at=now)

    def update_note(self, note_id: str, content: str = None, title: str = None) -> Optional[Note]:
        """Update a note."""
        self._require_db()
        note = self.get_note(note_id=note_id)
        if not note:
            return None
        from datetime import datetime

        now = datetime.utcnow().isoformat()
        new_content = content if content is not None else note.content
        new_title = title if title is not None else note.title

        self._conn.execute(
            "UPDATE notes SET content = ?, title = ?, updated_at = ? WHERE id = ?",
            (new_content, new_title, now, note_id),
        )
        self._conn.commit()
        note.content = new_content
        note.title = new_title
        note.updated_at = now
        return note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        self._require_db()
        note = self.get_note(note_id=note_id)
        if not note:
            return False
        self._conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self._conn.commit()
        if self.vault_path:
            full_path = self.vault_path / note.file_path
            if full_path.exists():
                full_path.unlink()
        return True

    def list_notes(self, folder: str = None, tag: str = None, limit: int = 100) -> list[Note]:
        """List notes with optional filters."""
        self._require_db()
        query = "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes"
        params: list = []
        conditions = []
        if folder:
            conditions.append("file_path LIKE ?")
            params.append(f"{folder}/%")
        if tag:
            conditions.append("id IN (SELECT note_id FROM tags WHERE tag = ?)")
            params.append(tag)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_note(r) for r in rows]

    # --- Graph ---

    def get_graph(self) -> GraphData:
        """Get the full knowledge graph."""
        self._require_db()
        nodes_rows = self._conn.execute("SELECT id, title FROM notes").fetchall()
        nodes = [GraphNode(id=r[0], label=r[1]) for r in nodes_rows]
        edges_rows = self._conn.execute(
            "SELECT source_note_id, target_note_id, link_text FROM links WHERE is_resolved = 1"
        ).fetchall()
        edges = [GraphEdge(source=r[0], target=r[1], label=r[2]) for r in edges_rows]
        return GraphData(nodes=nodes, edges=edges)

    def get_backlinks(self, note_id: str) -> list[Note]:
        """Get notes linking to this note."""
        self._require_db()
        rows = self._conn.execute(
            "SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at FROM links l JOIN notes n ON n.id = l.source_note_id WHERE l.target_note_id = ?",
            (note_id,),
        ).fetchall()
        return [self._row_to_note(r) for r in rows]

    # --- Tags ---

    def get_tags(self) -> list[Tag]:
        """Get all tags with counts."""
        self._require_db()
        rows = self._conn.execute("SELECT tag, COUNT(*) FROM tags GROUP BY tag ORDER BY COUNT(*) DESC").fetchall()
        return [Tag(tag=r[0], count=r[1]) for r in rows]

    # --- Entities ---

    def extract_entities(self, content: str, note_id: str = None) -> list[Entity]:
        """Extract entities via the AI sidecar (requires sidecar running)."""
        import urllib.request
        url = self.url or "http://127.0.0.1:9721"
        req = urllib.request.Request(
            f"{url}/extract",
            data=json.dumps({"content": content, "note_id": note_id}).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return [Entity(entity_type=e["entity_type"], entity_value=e["entity_value"], confidence=e.get("confidence", 0)) for e in data.get("entities", [])]
        except Exception:
            return []

    # --- Helpers ---

    def _row_to_note(self, row) -> Note:
        fm = {}
        try:
            fm = json.loads(row["frontmatter"]) if row["frontmatter"] else {}
        except (json.JSONDecodeError, TypeError):
            pass
        return Note(
            id=row["id"],
            file_path=row["file_path"],
            title=row["title"],
            content=row["content"],
            frontmatter=fm,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _http_search(self, query: str, limit: int) -> list[Note]:
        """Search via HTTP (sidecar/MCP server)."""
        import urllib.request
        req = urllib.request.Request(
            f"{self.url}/mcp",
            data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "einstein_search", "arguments": {"query": query, "limit": limit}},
            }).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
                results = json.loads(data.get("result", {}).get("content", [{}])[0].get("text", "{}"))
                return [Note(**r) for r in results.get("results", [])]
        except Exception:
            return []
