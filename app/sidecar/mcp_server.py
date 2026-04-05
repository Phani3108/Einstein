"""
Einstein MCP Server

Exposes Einstein vault operations as MCP (Model Context Protocol) tools.
External AI agents can connect to this server to read, search, create,
and manage notes in the user's vault.

Run: python mcp_server.py --vault /path/to/vault
Or set: EINSTEIN_VAULT_PATH=/path/to/vault
"""

import os
import sys
import json
import sqlite3
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

LOG = logging.getLogger("einstein-mcp")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Vault DB Access (read/write to the same SQLite the Tauri app uses)
# ---------------------------------------------------------------------------

class VaultDB:
    """Direct SQLite access to Einstein's vault database."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.db_path = self.vault_path / ".einstein" / "index.sqlite"
        if not self.db_path.exists():
            raise FileNotFoundError(f"Vault database not found at {self.db_path}. Open the vault in Einstein first.")
        self.conn = sqlite3.connect(str(self.db_path), timeout=10)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")

    def search(self, query: str, limit: int = 20) -> list[dict]:
        """Full-text search across notes."""
        try:
            rows = self.conn.execute(
                """SELECT n.id, n.file_path, n.title, n.content, n.frontmatter, n.created_at, n.updated_at
                   FROM notes_fts fts
                   JOIN notes n ON n.rowid = fts.rowid
                   WHERE notes_fts MATCH ?
                   ORDER BY rank
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
            return [dict(r) for r in rows]
        except Exception as e:
            LOG.warning(f"FTS search failed, falling back to LIKE: {e}")
            rows = self.conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE title LIKE ? OR content LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_note(self, note_id: str = None, title: str = None) -> Optional[dict]:
        """Get a note by ID or title."""
        if note_id:
            row = self.conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE id = ?",
                (note_id,),
            ).fetchone()
        elif title:
            row = self.conn.execute(
                "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE title = ? COLLATE NOCASE",
                (title,),
            ).fetchone()
        else:
            return None
        return dict(row) if row else None

    def list_notes(self, folder: str = None, tag: str = None, limit: int = 100) -> list[dict]:
        """List notes with optional filters."""
        query = "SELECT id, file_path, title, substr(content, 1, 200) as content, frontmatter, created_at, updated_at FROM notes"
        params = []
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

        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def create_note(self, title: str, content: str, folder: str = None, tags: list[str] = None) -> dict:
        """Create a new note."""
        import uuid
        note_id = str(uuid.uuid4())
        file_name = title.replace(" ", "-").lower() + ".md"
        file_path = f"{folder}/{file_name}" if folder else file_name
        now = datetime.utcnow().isoformat()
        fm = {}
        if tags:
            fm["tags"] = ", ".join(tags)

        fm_json = json.dumps(fm)
        self.conn.execute(
            "INSERT INTO notes (id, file_path, title, content, frontmatter, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (note_id, file_path, title, content, fm_json, now, now),
        )
        self.conn.commit()

        # Write file to disk
        full_path = self.vault_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        file_content = ""
        if fm:
            file_content += "---\n"
            for k, v in fm.items():
                file_content += f"{k}: {v}\n"
            file_content += "---\n\n"
        file_content += content
        full_path.write_text(file_content)

        return {"id": note_id, "file_path": file_path, "title": title, "content": content}

    def update_note(self, note_id: str, content: str = None, title: str = None) -> Optional[dict]:
        """Update an existing note."""
        note = self.get_note(note_id=note_id)
        if not note:
            return None
        now = datetime.utcnow().isoformat()
        new_content = content if content is not None else note["content"]
        new_title = title if title is not None else note["title"]

        self.conn.execute(
            "UPDATE notes SET content = ?, title = ?, updated_at = ? WHERE id = ?",
            (new_content, new_title, now, note_id),
        )
        self.conn.commit()

        # Update file on disk
        full_path = self.vault_path / note["file_path"]
        if full_path.exists():
            full_path.write_text(new_content)

        note["content"] = new_content
        note["title"] = new_title
        note["updated_at"] = now
        return note

    def delete_note(self, note_id: str) -> bool:
        """Delete a note."""
        note = self.get_note(note_id=note_id)
        if not note:
            return False
        self.conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
        full_path = self.vault_path / note["file_path"]
        if full_path.exists():
            full_path.unlink()
        return True

    def get_backlinks(self, note_id: str) -> list[dict]:
        """Get notes that link to this note."""
        rows = self.conn.execute(
            """SELECT n.id, n.file_path, n.title, substr(n.content, 1, 200) as content
               FROM links l JOIN notes n ON n.id = l.source_note_id
               WHERE l.target_note_id = ?""",
            (note_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_graph(self, node_id: str = None, depth: int = 2) -> dict:
        """Get knowledge graph data."""
        if node_id:
            # Local graph around a node
            nodes_set = {node_id}
            edges = []
            for _ in range(depth):
                placeholders = ",".join("?" * len(nodes_set))
                link_rows = self.conn.execute(
                    f"SELECT source_note_id, target_note_id, link_text FROM links WHERE is_resolved = 1 AND (source_note_id IN ({placeholders}) OR target_note_id IN ({placeholders}))",
                    list(nodes_set) + list(nodes_set),
                ).fetchall()
                for r in link_rows:
                    nodes_set.add(r[0])
                    if r[1]:
                        nodes_set.add(r[1])
                    edges.append({"source": r[0], "target": r[1], "label": r[2]})

            nodes = []
            for nid in nodes_set:
                note = self.get_note(note_id=nid)
                if note:
                    nodes.append({"id": nid, "label": note["title"], "type": "note"})
            return {"nodes": nodes, "edges": edges}
        else:
            # Full graph
            note_rows = self.conn.execute("SELECT id, title FROM notes").fetchall()
            nodes = [{"id": r[0], "label": r[1], "type": "note"} for r in note_rows]
            link_rows = self.conn.execute(
                "SELECT source_note_id, target_note_id, link_text FROM links WHERE is_resolved = 1"
            ).fetchall()
            edges = [{"source": r[0], "target": r[1], "label": r[2]} for r in link_rows]
            return {"nodes": nodes, "edges": edges}

    def get_daily_note(self) -> dict:
        """Get or create today's daily note."""
        today = datetime.now().strftime("%Y-%m-%d")
        file_path = f"daily/{today}.md"
        row = self.conn.execute(
            "SELECT id, file_path, title, content, frontmatter, created_at, updated_at FROM notes WHERE file_path = ?",
            (file_path,),
        ).fetchone()
        if row:
            return dict(row)
        return self.create_note(
            title=today,
            content=f"# {today}\n\n## Journal\n\n\n\n## Tasks\n\n- [ ] \n\n## Notes\n\n",
            folder="daily",
        )

    def get_tags(self) -> list[dict]:
        """Get all tags with counts."""
        rows = self.conn.execute("SELECT tag, COUNT(*) as count FROM tags GROUP BY tag ORDER BY count DESC").fetchall()
        return [{"tag": r[0], "count": r[1]} for r in rows]


# ---------------------------------------------------------------------------
# MCP Server (stdio transport)
# ---------------------------------------------------------------------------

class MCPServer:
    """Simple MCP server using stdio transport (JSON-RPC 2.0)."""

    def __init__(self, vault_db: VaultDB):
        self.db = vault_db
        self.tools = self._register_tools()

    def _register_tools(self) -> dict:
        return {
            "einstein_search": {
                "description": "Search across all notes in the Einstein vault using full-text search. Returns matching notes with content snippets.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query string"},
                        "limit": {"type": "integer", "description": "Max results to return", "default": 20},
                    },
                    "required": ["query"],
                },
                "handler": self._handle_search,
            },
            "einstein_get_note": {
                "description": "Get a specific note by its ID or title. Returns the full note content and metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Note UUID"},
                        "title": {"type": "string", "description": "Note title (case-insensitive)"},
                    },
                },
                "handler": self._handle_get_note,
            },
            "einstein_create_note": {
                "description": "Create a new note in the Einstein vault. The note is saved as a markdown file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Note title"},
                        "content": {"type": "string", "description": "Note content in markdown"},
                        "folder": {"type": "string", "description": "Optional folder path"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                    },
                    "required": ["title", "content"],
                },
                "handler": self._handle_create_note,
            },
            "einstein_update_note": {
                "description": "Update an existing note's content or title.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Note UUID"},
                        "content": {"type": "string", "description": "New content"},
                        "title": {"type": "string", "description": "New title"},
                    },
                    "required": ["id"],
                },
                "handler": self._handle_update_note,
            },
            "einstein_delete_note": {
                "description": "Delete a note from the vault. This removes both the database entry and the file on disk.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Note UUID to delete"},
                    },
                    "required": ["id"],
                },
                "handler": self._handle_delete_note,
            },
            "einstein_list_notes": {
                "description": "List notes in the vault with optional folder and tag filters.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "folder": {"type": "string", "description": "Filter by folder path"},
                        "tag": {"type": "string", "description": "Filter by tag"},
                        "limit": {"type": "integer", "description": "Max results", "default": 100},
                    },
                },
                "handler": self._handle_list_notes,
            },
            "einstein_get_backlinks": {
                "description": "Get all notes that link to a specific note via [[wikilinks]].",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "note_id": {"type": "string", "description": "Note UUID"},
                    },
                    "required": ["note_id"],
                },
                "handler": self._handle_get_backlinks,
            },
            "einstein_get_graph": {
                "description": "Get the knowledge graph showing connections between notes. Optionally centered on a specific node.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "node_id": {"type": "string", "description": "Center graph on this node"},
                        "depth": {"type": "integer", "description": "Graph traversal depth", "default": 2},
                    },
                },
                "handler": self._handle_get_graph,
            },
            "einstein_daily_note": {
                "description": "Get or create today's daily note.",
                "inputSchema": {"type": "object", "properties": {}},
                "handler": self._handle_daily_note,
            },
            "einstein_get_tags": {
                "description": "Get all tags used across the vault with their usage counts.",
                "inputSchema": {"type": "object", "properties": {}},
                "handler": self._handle_get_tags,
            },
        }

    # --- Tool Handlers ---

    def _handle_search(self, args: dict) -> str:
        results = self.db.search(args["query"], args.get("limit", 20))
        for r in results:
            r["content"] = r["content"][:500]  # Truncate for response size
        return json.dumps({"results": results, "count": len(results)})

    def _handle_get_note(self, args: dict) -> str:
        note = self.db.get_note(note_id=args.get("id"), title=args.get("title"))
        if not note:
            return json.dumps({"error": "Note not found"})
        return json.dumps(note)

    def _handle_create_note(self, args: dict) -> str:
        note = self.db.create_note(
            title=args["title"],
            content=args["content"],
            folder=args.get("folder"),
            tags=args.get("tags"),
        )
        return json.dumps(note)

    def _handle_update_note(self, args: dict) -> str:
        note = self.db.update_note(
            note_id=args["id"],
            content=args.get("content"),
            title=args.get("title"),
        )
        if not note:
            return json.dumps({"error": "Note not found"})
        return json.dumps(note)

    def _handle_delete_note(self, args: dict) -> str:
        success = self.db.delete_note(args["id"])
        return json.dumps({"deleted": success})

    def _handle_list_notes(self, args: dict) -> str:
        notes = self.db.list_notes(
            folder=args.get("folder"),
            tag=args.get("tag"),
            limit=args.get("limit", 100),
        )
        return json.dumps({"notes": notes, "count": len(notes)})

    def _handle_get_backlinks(self, args: dict) -> str:
        backlinks = self.db.get_backlinks(args["note_id"])
        return json.dumps({"backlinks": backlinks, "count": len(backlinks)})

    def _handle_get_graph(self, args: dict) -> str:
        graph = self.db.get_graph(
            node_id=args.get("node_id"),
            depth=args.get("depth", 2),
        )
        return json.dumps(graph)

    def _handle_daily_note(self, args: dict) -> str:
        note = self.db.get_daily_note()
        return json.dumps(note)

    def _handle_get_tags(self, args: dict) -> str:
        tags = self.db.get_tags()
        return json.dumps({"tags": tags})

    # --- MCP Protocol ---

    def handle_message(self, message: dict) -> dict:
        """Handle a JSON-RPC 2.0 message."""
        method = message.get("method", "")
        msg_id = message.get("id")
        params = message.get("params", {})

        if method == "initialize":
            return self._response(msg_id, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {
                    "name": "einstein-mcp",
                    "version": "1.0.0",
                },
            })

        elif method == "notifications/initialized":
            return None  # No response needed for notifications

        elif method == "tools/list":
            tools_list = []
            for name, tool in self.tools.items():
                tools_list.append({
                    "name": name,
                    "description": tool["description"],
                    "inputSchema": tool["inputSchema"],
                })
            return self._response(msg_id, {"tools": tools_list})

        elif method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments", {})
            tool = self.tools.get(tool_name)
            if not tool:
                return self._error(msg_id, -32602, f"Unknown tool: {tool_name}")
            try:
                result = tool["handler"](tool_args)
                return self._response(msg_id, {
                    "content": [{"type": "text", "text": result}],
                })
            except Exception as e:
                return self._error(msg_id, -32603, str(e))

        elif method == "ping":
            return self._response(msg_id, {})

        else:
            return self._error(msg_id, -32601, f"Method not found: {method}")

    def _response(self, msg_id, result: dict) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}

    def _error(self, msg_id, code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}

    def run_stdio(self):
        """Run the MCP server using stdio transport."""
        LOG.info("Einstein MCP server started (stdio transport)")
        LOG.info(f"Vault: {self.db.vault_path}")
        LOG.info(f"Tools available: {', '.join(self.tools.keys())}")

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
                response = self.handle_message(message)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError as e:
                error_response = self._error(None, -32700, f"Parse error: {e}")
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()
            except Exception as e:
                LOG.error(f"Error handling message: {e}")
                error_response = self._error(None, -32603, str(e))
                sys.stdout.write(json.dumps(error_response) + "\n")
                sys.stdout.flush()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Einstein MCP Server")
    parser.add_argument("--vault", "-v", type=str, help="Path to Einstein vault")
    parser.add_argument("--transport", "-t", choices=["stdio", "http"], default="stdio", help="Transport mode")
    parser.add_argument("--port", "-p", type=int, default=9722, help="HTTP port (if using http transport)")
    args = parser.parse_args()

    vault_path = args.vault or os.environ.get("EINSTEIN_VAULT_PATH")
    if not vault_path:
        print("Error: Vault path required. Use --vault or set EINSTEIN_VAULT_PATH", file=sys.stderr)
        sys.exit(1)

    vault_path = os.path.expanduser(vault_path)
    if not os.path.isdir(vault_path):
        print(f"Error: Vault directory not found: {vault_path}", file=sys.stderr)
        sys.exit(1)

    try:
        db = VaultDB(vault_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    server = MCPServer(db)

    if args.transport == "stdio":
        server.run_stdio()
    else:
        # HTTP transport via FastAPI
        try:
            import uvicorn
            from fastapi import FastAPI
            from fastapi.middleware.cors import CORSMiddleware
            from pydantic import BaseModel

            http_app = FastAPI(title="Einstein MCP Server", version="1.0.0")
            http_app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

            class MCPRequest(BaseModel):
                jsonrpc: str = "2.0"
                id: Optional[int] = None
                method: str
                params: dict = {}

            @http_app.post("/mcp")
            async def handle_mcp(req: MCPRequest):
                return server.handle_message(req.dict())

            @http_app.get("/health")
            async def health():
                return {"status": "ok", "server": "einstein-mcp", "tools": len(server.tools)}

            uvicorn.run(http_app, host="127.0.0.1", port=args.port)
        except ImportError:
            print("Error: FastAPI/uvicorn required for HTTP transport. Install: pip install fastapi uvicorn", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
