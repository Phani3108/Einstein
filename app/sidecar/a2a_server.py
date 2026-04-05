"""
Einstein Agent-to-Agent (A2A) Protocol Server

Implements Google's A2A protocol so Einstein can act as an agent
that other AI agents can discover, negotiate with, and delegate tasks to.

Run: python a2a_server.py --vault /path/to/vault
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Optional
import uuid as uuid_mod

LOG = logging.getLogger("einstein-a2a")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------------------------------------------------------------------------
# Agent Card
# ---------------------------------------------------------------------------

AGENT_CARD = {
    "name": "Einstein Knowledge Agent",
    "description": "AI-powered personal knowledge management agent. Manages a vault of interconnected markdown notes with automatic entity extraction, semantic search, and knowledge graph visualization.",
    "url": "http://localhost:9723",
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": True,
    },
    "skills": [
        {
            "id": "note_search",
            "name": "Search Notes",
            "description": "Full-text and semantic search across all notes in the vault",
            "tags": ["search", "knowledge", "notes"],
            "examples": [
                "Find all notes about machine learning",
                "Search for meeting notes from last week",
            ],
        },
        {
            "id": "note_creation",
            "name": "Create Notes",
            "description": "Create new markdown notes with optional tags and folder placement",
            "tags": ["create", "write", "notes"],
            "examples": [
                "Create a note about our project architecture",
                "Add a meeting summary for today's standup",
            ],
        },
        {
            "id": "note_retrieval",
            "name": "Retrieve Notes",
            "description": "Get specific notes by title or ID, including backlinks and connections",
            "tags": ["read", "retrieve", "notes"],
            "examples": [
                "Get the note titled 'Project Roadmap'",
                "Show me all notes linked to the architecture doc",
            ],
        },
        {
            "id": "knowledge_graph",
            "name": "Knowledge Graph",
            "description": "Query the knowledge graph to find connections between notes, entities, and concepts",
            "tags": ["graph", "connections", "relationships"],
            "examples": [
                "Show the connections around the 'AI Strategy' note",
                "What notes are connected to John Smith?",
            ],
        },
        {
            "id": "daily_notes",
            "name": "Daily Notes",
            "description": "Manage daily journal notes with templates",
            "tags": ["daily", "journal", "routine"],
            "examples": [
                "Get today's daily note",
                "What did I write in yesterday's journal?",
            ],
        },
    ],
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
}


# ---------------------------------------------------------------------------
# Task Manager
# ---------------------------------------------------------------------------

class TaskManager:
    """Manages A2A tasks with state tracking."""

    def __init__(self, mcp_server):
        self.tasks = {}
        self.mcp = mcp_server  # Reuse MCP server for actual operations

    def create_task(self, task_data: dict) -> dict:
        task_id = str(uuid_mod.uuid4())
        message = task_data.get("message", {})
        parts = message.get("parts", [])
        text = ""
        for part in parts:
            if part.get("type") == "text":
                text = part.get("text", "")
                break

        task = {
            "id": task_id,
            "status": {"state": "working"},
            "history": [message] if message else [],
        }
        self.tasks[task_id] = task

        # Process the task
        try:
            result = self._process_text(text)
            task["status"] = {"state": "completed"}
            task["artifacts"] = [{
                "parts": [{"type": "text", "text": result}],
            }]
        except Exception as e:
            task["status"] = {
                "state": "failed",
                "message": {"role": "agent", "parts": [{"type": "text", "text": f"Error: {e}"}]},
            }

        return task

    def get_task(self, task_id: str) -> Optional[dict]:
        return self.tasks.get(task_id)

    def _process_text(self, text: str) -> str:
        """Route natural language to MCP tools."""
        text_lower = text.lower()

        # Simple intent detection
        if any(w in text_lower for w in ["search", "find", "look for", "query"]):
            # Extract search query (everything after the intent word)
            for trigger in ["search for", "find", "look for", "search"]:
                if trigger in text_lower:
                    query = text[text_lower.index(trigger) + len(trigger):].strip()
                    if query:
                        return self.mcp._handle_search({"query": query, "limit": 10})

        if any(w in text_lower for w in ["create", "add", "new note", "write"]):
            # Try to extract title and content
            lines = text.split("\n")
            title = lines[0].replace("create", "").replace("add", "").replace("new note", "").strip(": ")
            content = "\n".join(lines[1:]).strip() if len(lines) > 1 else f"# {title}\n\n"
            if title:
                return self.mcp._handle_create_note({"title": title, "content": content})

        if any(w in text_lower for w in ["daily", "today", "journal"]):
            return self.mcp._handle_daily_note({})

        if any(w in text_lower for w in ["graph", "connections", "linked", "related"]):
            return self.mcp._handle_get_graph({})

        if any(w in text_lower for w in ["tags", "categories", "topics"]):
            return self.mcp._handle_get_tags({})

        if any(w in text_lower for w in ["list", "show all", "all notes"]):
            return self.mcp._handle_list_notes({"limit": 50})

        # Default: try search
        return self.mcp._handle_search({"query": text, "limit": 10})


# ---------------------------------------------------------------------------
# A2A HTTP Server
# ---------------------------------------------------------------------------

def create_a2a_app(vault_path: str):
    try:
        import uvicorn
        from fastapi import FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        print("Error: FastAPI/uvicorn required. Install: pip install fastapi uvicorn", file=sys.stderr)
        sys.exit(1)

    # Import MCP server for tool reuse
    from mcp_server import VaultDB, MCPServer

    db = VaultDB(vault_path)
    mcp = MCPServer(db)
    task_mgr = TaskManager(mcp)

    app = FastAPI(title="Einstein A2A Agent", version="1.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    # Agent Card discovery
    @app.get("/.well-known/agent.json")
    async def agent_card():
        return AGENT_CARD

    # Send task
    @app.post("/a2a/tasks/send")
    async def send_task(request: dict):
        task_data = request.get("params", request)
        task = task_mgr.create_task(task_data)
        return {"jsonrpc": "2.0", "id": request.get("id"), "result": task}

    # Get task status
    @app.get("/a2a/tasks/{task_id}")
    async def get_task(task_id: str):
        task = task_mgr.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"jsonrpc": "2.0", "result": task}

    # Health
    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "agent": AGENT_CARD["name"],
            "skills": len(AGENT_CARD["skills"]),
            "vault": str(vault_path),
        }

    return app


def main():
    parser = argparse.ArgumentParser(description="Einstein A2A Server")
    parser.add_argument("--vault", "-v", type=str, help="Path to Einstein vault")
    parser.add_argument("--port", "-p", type=int, default=9723, help="Server port")
    args = parser.parse_args()

    vault_path = args.vault or os.environ.get("EINSTEIN_VAULT_PATH")
    if not vault_path:
        print("Error: Vault path required. Use --vault or set EINSTEIN_VAULT_PATH", file=sys.stderr)
        sys.exit(1)

    vault_path = os.path.expanduser(vault_path)

    import uvicorn
    app = create_a2a_app(vault_path)
    LOG.info(f"Einstein A2A Agent starting on port {args.port}")
    uvicorn.run(app, host="127.0.0.1", port=args.port)


if __name__ == "__main__":
    main()
