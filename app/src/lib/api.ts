// Cloud API configuration
const CLOUD_API = localStorage.getItem("einstein_server_url") || "http://localhost:8000";

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem("einstein_auth_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = { ...authHeaders(), ...(options.headers as Record<string, string> || {}) };
  let res = await fetch(url, { ...options, headers });

  // Retry once on 5xx
  if (res.status >= 500) {
    await new Promise((r) => setTimeout(r, 1000));
    res = await fetch(url, { ...options, headers });
  }

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${body}`);
  }

  // Handle 204 No Content
  if (res.status === 204) return undefined as unknown as T;

  return res.json();
}

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

/* ------------------------------------------------------------------ */
/*  Temporal intelligence types (Phase 2)                              */
/* ------------------------------------------------------------------ */

export interface PrepPack {
  summary: string;
  key_points: string[];
  open_questions: string[];
  relevant_history: string[];
  suggested_actions: string[];
}

export interface AISuggestion {
  type: "related_note" | "overdue_action" | "stale_project" | "person_followup" | "pattern" | "decision_needed";
  title: string;
  description: string;
  confidence: number;
}

export const api = {
  // --- Vault operations (Cloud API) ---
  openVault: (path: string): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/open`, {
      method: "POST",
      body: JSON.stringify({ path }),
    }),
  listNotes: (): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/notes`),
  getNote: (id: string): Promise<Note | null> =>
    request<Note | null>(`${CLOUD_API}/api/v1/vault/notes/${encodeURIComponent(id)}`),
  saveNote: (
    filePath: string,
    title: string,
    content: string,
    frontmatter: Record<string, string>
  ): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/notes`, {
      method: "PUT",
      body: JSON.stringify({ filePath, title, content, frontmatter }),
    }),
  deleteNote: (id: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/notes/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  searchNotes: (query: string): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/notes/search?q=${encodeURIComponent(query)}`),
  getBacklinks: (noteId: string): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/notes/${encodeURIComponent(noteId)}/backlinks`),
  getGraphData: (): Promise<GraphData> =>
    request<GraphData>(`${CLOUD_API}/api/v1/vault/graph`),
  createDailyNote: (): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/notes/daily`, {
      method: "POST",
    }),

  // --- New vault operations ---
  renameNote: (id: string, newTitle: string, newFilePath: string): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/notes/${encodeURIComponent(id)}/rename`, {
      method: "PATCH",
      body: JSON.stringify({ newTitle, newFilePath }),
    }),
  getNoteVersions: (noteId: string): Promise<NoteVersion[]> =>
    request<NoteVersion[]>(`${CLOUD_API}/api/v1/vault/versions/${encodeURIComponent(noteId)}`),
  restoreVersion: (versionId: string): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/versions/${encodeURIComponent(versionId)}/restore`, {
      method: "POST",
    }),
  toggleBookmark: (noteId: string): Promise<boolean> =>
    request<boolean>(`${CLOUD_API}/api/v1/vault/bookmarks/${encodeURIComponent(noteId)}/toggle`, {
      method: "POST",
    }),
  listBookmarks: (): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/bookmarks`),
  getAllTags: (): Promise<TagInfo[]> =>
    request<TagInfo[]>(`${CLOUD_API}/api/v1/vault/tags`),
  getConfig: (key: string): Promise<string | null> =>
    request<string | null>(`${CLOUD_API}/api/v1/vault/config/${encodeURIComponent(key)}`),
  setConfig: (key: string, value: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/config/${encodeURIComponent(key)}`, {
      method: "PUT",
      body: JSON.stringify({ value }),
    }),
  listTemplates: (): Promise<TemplateInfo[]> =>
    request<TemplateInfo[]>(`${CLOUD_API}/api/v1/vault/templates`),
  createFromTemplate: (templateName: string, noteTitle: string): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/templates/apply`, {
      method: "POST",
      body: JSON.stringify({ templateName, noteTitle }),
    }),
  mergeNotes: (ids: string[], newTitle: string): Promise<Note> =>
    request<Note>(`${CLOUD_API}/api/v1/vault/notes/merge`, {
      method: "POST",
      body: JSON.stringify({ ids, newTitle }),
    }),

  // --- Projects (Cloud API) ---
  createProject: (title: string, description: string, category: string, goal: string, deadline?: string): Promise<Project> =>
    request<Project>(`${CLOUD_API}/api/v1/vault/projects`, {
      method: "POST",
      body: JSON.stringify({ title, description, category, goal, deadline: deadline ?? null }),
    }),
  updateProject: (id: string, changes: { title?: string; description?: string; status?: string; category?: string; goal?: string; deadline?: string }): Promise<Project> =>
    request<Project>(`${CLOUD_API}/api/v1/vault/projects/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(changes),
    }),
  listProjects: (statusFilter?: string): Promise<Project[]> => {
    const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    return request<Project[]>(`${CLOUD_API}/api/v1/vault/projects${params}`);
  },
  getProject: (id: string): Promise<Project> =>
    request<Project>(`${CLOUD_API}/api/v1/vault/projects/${encodeURIComponent(id)}`),
  deleteProject: (id: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/projects/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  // --- People (Cloud API) ---
  createPerson: (name: string, role: string, organization: string, email: string, notes: string): Promise<Person> =>
    request<Person>(`${CLOUD_API}/api/v1/vault/people`, {
      method: "POST",
      body: JSON.stringify({ name, role, organization, email, notes }),
    }),
  updatePerson: (id: string, changes: { name?: string; role?: string; organization?: string; email?: string; notes?: string; lastContact?: string }): Promise<Person> =>
    request<Person>(`${CLOUD_API}/api/v1/vault/people/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(changes),
    }),
  listPeople: (): Promise<Person[]> =>
    request<Person[]>(`${CLOUD_API}/api/v1/vault/people`),
  getPerson: (id: string): Promise<Person> =>
    request<Person>(`${CLOUD_API}/api/v1/vault/people/${encodeURIComponent(id)}`),
  deletePerson: (id: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/people/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  searchPeople: (query: string): Promise<Person[]> =>
    request<Person[]>(`${CLOUD_API}/api/v1/vault/people?q=${encodeURIComponent(query)}`),

  // --- Decisions (Cloud API) ---
  createDecision: (title: string, description: string, reasoning: string, alternatives: string, revisitDate?: string): Promise<Decision> =>
    request<Decision>(`${CLOUD_API}/api/v1/vault/decisions`, {
      method: "POST",
      body: JSON.stringify({ title, description, reasoning, alternatives, revisitDate: revisitDate ?? null }),
    }),
  updateDecision: (id: string, changes: { title?: string; description?: string; reasoning?: string; alternatives?: string; status?: string; revisitDate?: string }): Promise<Decision> =>
    request<Decision>(`${CLOUD_API}/api/v1/vault/decisions/${encodeURIComponent(id)}`, {
      method: "PUT",
      body: JSON.stringify(changes),
    }),
  listDecisions: (statusFilter?: string): Promise<Decision[]> => {
    const params = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    return request<Decision[]>(`${CLOUD_API}/api/v1/vault/decisions${params}`);
  },
  getDecision: (id: string): Promise<Decision> =>
    request<Decision>(`${CLOUD_API}/api/v1/vault/decisions/${encodeURIComponent(id)}`),
  deleteDecision: (id: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/decisions/${encodeURIComponent(id)}`, { method: "DELETE" }),

  // --- Note Associations (Cloud API) ---
  createAssociation: (noteId: string, objectType: string, objectId: string, relationship: string, confidence: number): Promise<NoteAssociation> =>
    request<NoteAssociation>(`${CLOUD_API}/api/v1/vault/associations`, {
      method: "POST",
      body: JSON.stringify({ noteId, objectType, objectId, relationship, confidence }),
    }),
  getAssociationsForNote: (noteId: string): Promise<NoteAssociation[]> =>
    request<NoteAssociation[]>(`${CLOUD_API}/api/v1/vault/associations?noteId=${encodeURIComponent(noteId)}`),
  getAssociationsForObject: (objectType: string, objectId: string): Promise<NoteAssociation[]> =>
    request<NoteAssociation[]>(`${CLOUD_API}/api/v1/vault/associations?objectType=${encodeURIComponent(objectType)}&objectId=${encodeURIComponent(objectId)}`),
  deleteAssociation: (id: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/associations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),

  // --- Note Metadata (Cloud API) ---
  getNoteMetadata: (noteId: string): Promise<NoteMetadataRecord> =>
    request<NoteMetadataRecord>(`${CLOUD_API}/api/v1/vault/metadata/${encodeURIComponent(noteId)}`),
  updateNoteMetadata: (noteId: string, changes: { lifecycle?: string; lastMeaningfulEdit?: string; viewCount?: number; importanceScore?: number; distilledAt?: string; sourceType?: string }): Promise<NoteMetadataRecord> =>
    request<NoteMetadataRecord>(`${CLOUD_API}/api/v1/vault/metadata/${encodeURIComponent(noteId)}`, {
      method: "PUT",
      body: JSON.stringify(changes),
    }),
  getStaleNotes: (daysThreshold: number): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/notes?stale=${encodeURIComponent(daysThreshold)}`),

  // --- Action items & Calendar events (Cloud API) ---
  saveActionItems: (noteId: string, items: ActionItemData[]): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/action-items`, {
      method: "POST",
      body: JSON.stringify({ noteId, items }),
    }),
  getActionItems: (noteId?: string, status?: string): Promise<ActionItemRecord[]> => {
    const params = new URLSearchParams();
    if (noteId) params.set("noteId", noteId);
    if (status) params.set("status", status);
    const qs = params.toString();
    return request<ActionItemRecord[]>(`${CLOUD_API}/api/v1/vault/action-items${qs ? `?${qs}` : ""}`);
  },
  updateActionStatus: (id: string, status: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/action-items/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  saveCalendarEvents: (noteId: string, events: CalendarEventData[]): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/vault/calendar-events`, {
      method: "POST",
      body: JSON.stringify({ noteId, events }),
    }),
  getCalendarEvents: (startDate: string, endDate: string): Promise<CalendarEventRecord[]> =>
    request<CalendarEventRecord[]>(`${CLOUD_API}/api/v1/vault/calendar-events?startDate=${encodeURIComponent(startDate)}&endDate=${encodeURIComponent(endDate)}`),

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

  // --- Temporal Intelligence (Phase 2) ---

  /** Generate a preparation brief for a meeting, day, or project */
  prepareContext: async (
    focusType: "meeting" | "day" | "project",
    context: Record<string, unknown>,
    notes: Record<string, unknown>[],
    actions: Record<string, unknown>[],
    decisions: Record<string, unknown>[],
  ): Promise<PrepPack> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/context/prepare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          focus_type: focusType,
          context,
          notes,
          actions,
          decisions,
        }),
      });
      if (!res.ok) return { summary: "", key_points: [], open_questions: [], relevant_history: [], suggested_actions: [] };
      return res.json();
    } catch {
      return { summary: "", key_points: [], open_questions: [], relevant_history: [], suggested_actions: [] };
    }
  },

  /** Get proactive AI suggestions based on current context */
  getSuggestions: async (
    currentNoteId: string | null,
    currentNoteTitle: string | null,
    currentProjectId: string | null,
    recentNotes: Record<string, unknown>[],
    actions: Record<string, unknown>[],
    people: Record<string, unknown>[],
    projects: Record<string, unknown>[],
  ): Promise<AISuggestion[]> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/context/suggestions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_note_id: currentNoteId,
          current_note_title: currentNoteTitle,
          current_project_id: currentProjectId,
          recent_notes: recentNotes,
          actions,
          people,
          projects,
        }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.suggestions ?? [];
    } catch {
      return [];
    }
  },

  /** Extract associations between a note and known projects/people */
  extractAssociations: async (
    content: string,
    noteId: string,
    knownProjects: { id: string; title: string }[],
    knownPeople: { id: string; name: string }[],
  ): Promise<{ object_type: string; object_id: string; relationship: string; confidence: number }[]> => {
    try {
      const res = await fetch(`${SIDECAR_URL}/extract-associations`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          content,
          note_id: noteId,
          known_projects: knownProjects,
          known_people: knownPeople,
        }),
      });
      if (!res.ok) return [];
      const data = await res.json();
      return data.associations ?? [];
    } catch {
      return [];
    }
  },
};
