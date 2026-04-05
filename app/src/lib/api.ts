import { invoke } from "@tauri-apps/api/core";

export interface Note {
  id: string;
  file_path: string;
  title: string;
  content: string;
  frontmatter: Record<string, string>;
  outgoing_links: string[];
  created_at: string;
  updated_at: string;
}

export interface GraphNode {
  id: string;
  label: string;
  node_type: string;
  file_path: string | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  label: string;
  edge_type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Entity {
  id: string;
  note_id: string;
  entity_type: string;
  entity_value: string;
  confidence: number;
  context: string;
  extracted_at: string;
}

export interface NoteVersion {
  id: string;
  note_id: string;
  content: string;
  frontmatter: string;
  created_at: string;
}

export interface TagInfo {
  tag: string;
  count: number;
}

export interface TemplateInfo {
  name: string;
  content: string;
}

// AI sidecar base URL
const SIDECAR_URL = "http://127.0.0.1:9721";

export interface ExtractedEntity {
  entity_type: string;
  entity_value: string;
  confidence: number;
}

export interface SidecarHealth {
  status: string;
  provider: string;
  model: string;
}

/* ------------------------------------------------------------------ */
/*  Structured types for action items & calendar events                 */
/* ------------------------------------------------------------------ */

export interface ActionItemData {
  task: string;
  assignee: string | null;
  deadline: string | null;
  priority: "high" | "medium" | "low";
  status?: string;
}

export interface CalendarEventData {
  title: string;
  event_date: string;
  event_type: "deadline" | "follow_up" | "meeting" | "reminder";
  description: string;
}

export interface ActionItemRecord {
  id: string;
  note_id: string;
  task: string;
  assignee: string | null;
  deadline: string | null;
  priority: string;
  status: string;
  created_at: string;
}

export interface CalendarEventRecord {
  id: string;
  note_id: string;
  title: string;
  event_date: string;
  event_type: string;
  description: string;
  created_at: string;
}

export interface RAGSearchResult {
  note_id: string;
  title: string;
  chunk: string;
  score: number;
}

/* ------------------------------------------------------------------ */
/*  First-class object types                                           */
/* ------------------------------------------------------------------ */

export interface Project {
  id: string;
  title: string;
  description: string;
  status: string;
  category: string;
  goal: string;
  deadline: string | null;
  created_at: string;
  updated_at: string;
}

export interface Person {
  id: string;
  name: string;
  role: string;
  organization: string;
  email: string;
  notes: string;
  last_contact: string | null;
  created_at: string;
  updated_at: string;
}

export interface Decision {
  id: string;
  title: string;
  description: string;
  reasoning: string;
  alternatives: string;
  status: string;
  decided_at: string;
  revisit_date: string | null;
  created_at: string;
}

export interface NoteAssociation {
  id: string;
  note_id: string;
  object_type: string;
  object_id: string;
  relationship: string;
  confidence: number;
  created_at: string;
}

export interface NoteMetadataRecord {
  note_id: string;
  lifecycle: string;
  last_meaningful_edit: string | null;
  view_count: number;
  importance_score: number;
  distilled_at: string | null;
  source_type: string;
}

export const api = {
  // --- Vault operations (Tauri IPC) ---
  openVault: (path: string): Promise<Note[]> => invoke("open_vault", { path }),
  listNotes: (): Promise<Note[]> => invoke("list_notes"),
  getNote: (id: string): Promise<Note | null> => invoke("get_note", { id }),
  saveNote: (
    filePath: string,
    title: string,
    content: string,
    frontmatter: Record<string, string>
  ): Promise<Note> =>
    invoke("save_note", {
      filePath,
      title,
      content,
      frontmatter,
    }),
  deleteNote: (id: string): Promise<void> => invoke("delete_note", { id }),
  searchNotes: (query: string): Promise<Note[]> =>
    invoke("search_notes", { query }),
  getBacklinks: (noteId: string): Promise<Note[]> =>
    invoke("get_backlinks", { noteId }),
  getGraphData: (): Promise<GraphData> => invoke("get_graph_data"),
  createDailyNote: (): Promise<Note> => invoke("create_daily_note"),

  // --- New vault operations ---
  renameNote: (id: string, newTitle: string, newFilePath: string): Promise<Note> =>
    invoke("rename_note", { id, newTitle, newFilePath }),
  getNoteVersions: (noteId: string): Promise<NoteVersion[]> =>
    invoke("get_note_versions", { noteId }),
  restoreVersion: (versionId: string): Promise<Note> =>
    invoke("restore_version", { versionId }),
  toggleBookmark: (noteId: string): Promise<boolean> =>
    invoke("toggle_bookmark", { noteId }),
  listBookmarks: (): Promise<Note[]> =>
    invoke("list_bookmarks"),
  getAllTags: (): Promise<TagInfo[]> =>
    invoke("get_all_tags"),
  getConfig: (key: string): Promise<string | null> =>
    invoke("get_config", { key }),
  setConfig: (key: string, value: string): Promise<void> =>
    invoke("set_config", { key, value }),
  listTemplates: (): Promise<TemplateInfo[]> =>
    invoke("list_templates"),
  createFromTemplate: (templateName: string, noteTitle: string): Promise<Note> =>
    invoke("create_from_template", { templateName, noteTitle }),
  mergeNotes: (ids: string[], newTitle: string): Promise<Note> =>
    invoke("merge_notes", { ids, newTitle }),

  // --- Projects (Tauri IPC) ---
  createProject: (title: string, description: string, category: string, goal: string, deadline?: string): Promise<Project> =>
    invoke("create_project", { title, description, category, goal, deadline: deadline ?? null }),
  updateProject: (id: string, changes: { title?: string; description?: string; status?: string; category?: string; goal?: string; deadline?: string }): Promise<Project> =>
    invoke("update_project", { id, ...changes }),
  listProjects: (statusFilter?: string): Promise<Project[]> =>
    invoke("list_projects", { statusFilter: statusFilter ?? null }),
  getProject: (id: string): Promise<Project> =>
    invoke("get_project", { id }),
  deleteProject: (id: string): Promise<void> =>
    invoke("delete_project", { id }),

  // --- People (Tauri IPC) ---
  createPerson: (name: string, role: string, organization: string, email: string, notes: string): Promise<Person> =>
    invoke("create_person", { name, role, organization, email, notes }),
  updatePerson: (id: string, changes: { name?: string; role?: string; organization?: string; email?: string; notes?: string; lastContact?: string }): Promise<Person> =>
    invoke("update_person", { id, ...changes }),
  listPeople: (): Promise<Person[]> =>
    invoke("list_people"),
  getPerson: (id: string): Promise<Person> =>
    invoke("get_person", { id }),
  deletePerson: (id: string): Promise<void> =>
    invoke("delete_person", { id }),
  searchPeople: (query: string): Promise<Person[]> =>
    invoke("search_people", { query }),

  // --- Decisions (Tauri IPC) ---
  createDecision: (title: string, description: string, reasoning: string, alternatives: string, revisitDate?: string): Promise<Decision> =>
    invoke("create_decision", { title, description, reasoning, alternatives, revisitDate: revisitDate ?? null }),
  updateDecision: (id: string, changes: { title?: string; description?: string; reasoning?: string; alternatives?: string; status?: string; revisitDate?: string }): Promise<Decision> =>
    invoke("update_decision", { id, ...changes }),
  listDecisions: (statusFilter?: string): Promise<Decision[]> =>
    invoke("list_decisions", { statusFilter: statusFilter ?? null }),
  getDecision: (id: string): Promise<Decision> =>
    invoke("get_decision", { id }),

  // --- Note Associations (Tauri IPC) ---
  createAssociation: (noteId: string, objectType: string, objectId: string, relationship: string, confidence: number): Promise<NoteAssociation> =>
    invoke("create_association", { noteId, objectType, objectId, relationship, confidence }),
  getAssociationsForNote: (noteId: string): Promise<NoteAssociation[]> =>
    invoke("get_associations_for_note", { noteId }),
  getAssociationsForObject: (objectType: string, objectId: string): Promise<NoteAssociation[]> =>
    invoke("get_associations_for_object", { objectType, objectId }),
  deleteAssociation: (id: string): Promise<void> =>
    invoke("delete_association", { id }),

  // --- Note Metadata (Tauri IPC) ---
  getNoteMetadata: (noteId: string): Promise<NoteMetadataRecord> =>
    invoke("get_note_metadata", { noteId }),
  updateNoteMetadata: (noteId: string, changes: { lifecycle?: string; lastMeaningfulEdit?: string; viewCount?: number; importanceScore?: number; distilledAt?: string; sourceType?: string }): Promise<NoteMetadataRecord> =>
    invoke("update_note_metadata", { noteId, ...changes }),
  getStaleNotes: (daysThreshold: number): Promise<Note[]> =>
    invoke("get_stale_notes", { daysThreshold }),

  // --- Action items & Calendar events (Tauri IPC) ---
  saveActionItems: (noteId: string, items: ActionItemData[]): Promise<void> =>
    invoke("save_action_items", { noteId, items }),
  getActionItems: (noteId?: string, status?: string): Promise<ActionItemRecord[]> =>
    invoke("get_action_items", { noteId: noteId ?? null, status: status ?? null }),
  updateActionStatus: (id: string, status: string): Promise<void> =>
    invoke("update_action_status", { id, status }),
  saveCalendarEvents: (noteId: string, events: CalendarEventData[]): Promise<void> =>
    invoke("save_calendar_events", { noteId, events }),
  getCalendarEvents: (startDate: string, endDate: string): Promise<CalendarEventRecord[]> =>
    invoke("get_calendar_events", { startDate, endDate }),

  // --- AI sidecar operations (HTTP) ---
  sidecarHealth: async (): Promise<SidecarHealth | null> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/health`);
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },

  extractEntities: async (
    content: string,
    noteId?: string
  ): Promise<ExtractedEntity[]> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/extract`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, note_id: noteId }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.entities ?? [];
    } catch {
      return [];
    }
  },

  // --- RAG operations ---
  ragIndex: async (notes: { id: string; title: string; content: string }[]): Promise<{ indexed: number; chunks: number }> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/rag/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (!res.ok) throw new Error("Index failed");
      return res.json();
    } catch {
      return { indexed: 0, chunks: 0 };
    }
  },

  ragStatus: async (): Promise<{ indexed: number; chunks: number; ready: boolean; provider: string; model: string; last_indexed: string | null }> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/rag/status`);
      if (!res.ok) return { indexed: 0, chunks: 0, ready: false, provider: "", model: "", last_indexed: null };
      return res.json();
    } catch {
      return { indexed: 0, chunks: 0, ready: false, provider: "", model: "", last_indexed: null };
    }
  },

  // RAG ask returns a ReadableStream (SSE) — consumed directly by RAGPanel
  ragAskUrl: `${SIDECAR_URL}/rag/ask`,

  // RAG vector-only search (no LLM generation — cheap and fast)
  ragSearch: async (query: string, topK: number = 5): Promise<RAGSearchResult[]> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/rag/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: topK }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.results ?? [];
    } catch {
      return [];
    }
  },

  // --- Meeting operations ---
  processMeeting: async (transcript: string, source: string, metadata?: Record<string, unknown>): Promise<Record<string, unknown>> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/meetings/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript, source, metadata: metadata || {} }),
      });
      if (!res.ok) throw new Error("Meeting processing failed");
      return res.json();
    } catch (e) {
      console.error("Meeting processing error:", e);
      return {};
    }
  },

  parseWhatsApp: async (content: string): Promise<Record<string, unknown>> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/meetings/parse-whatsapp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });
      if (!res.ok) throw new Error("WhatsApp parsing failed");
      return res.json();
    } catch (e) {
      console.error("WhatsApp parse error:", e);
      return {};
    }
  },

  // --- Action item extraction ---
  extractActions: async (content: string, noteId: string, noteTitle?: string): Promise<{ action_items: Record<string, unknown>[]; calendar_events: Record<string, unknown>[] }> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/extract-actions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content, note_id: noteId, note_title: noteTitle || "" }),
      });
      if (!res.ok) return { action_items: [], calendar_events: [] };
      return res.json();
    } catch {
      return { action_items: [], calendar_events: [] };
    }
  },

  // --- Context Hub ---
  generateBriefing: async (notes: Record<string, unknown>[], actionItems: Record<string, unknown>[], events: Record<string, unknown>[], period: string = "daily"): Promise<{ summary: string; highlights: string[]; attention_needed: string[]; themes: string[] }> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/context/briefing`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes, action_items: actionItems, events, period }),
      });
      if (!res.ok) return { summary: "", highlights: [], attention_needed: [], themes: [] };
      return res.json();
    } catch {
      return { summary: "", highlights: [], attention_needed: [], themes: [] };
    }
  },

  findConnections: async (notes: Record<string, unknown>[]): Promise<{ connections: Record<string, unknown>[] }> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/context/connections`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes }),
      });
      if (!res.ok) return { connections: [] };
      return res.json();
    } catch {
      return { connections: [] };
    }
  },
};
