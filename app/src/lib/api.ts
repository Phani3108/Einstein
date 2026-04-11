// Cloud API configuration
// On Vercel (same origin), use relative URLs; locally fall back to localhost:8000
const CLOUD_API =
  localStorage.getItem("einstein_server_url") ||
  (typeof window !== "undefined" && window.location.hostname !== "localhost"
    ? ""
    : "http://localhost:8000");

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

// DEPRECATED: AI sidecar base URL — sidecar methods now redirect to Cloud API equivalents.
// Kept for reference; all runtime calls go through CLOUD_API.
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
  getGraphData: async (): Promise<GraphData> => {
    const raw = await request<any>(`${CLOUD_API}/api/v1/vault/graph`);
    return {
      nodes: (raw.nodes || []).map((n: any) => ({
        id: n.id,
        label: n.title || n.label || n.id,
        node_type: n.node_type || "note",
        file_path: n.file_path || "",
      })),
      edges: (raw.edges || []).map((e: any) => ({
        source: e.source,
        target: e.target,
        label: e.label || "link",
        edge_type: e.edge_type || "wikilink",
      })),
    };
  },
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
    request<{bookmarked: boolean}>(`${CLOUD_API}/api/v1/vault/bookmarks/${encodeURIComponent(noteId)}/toggle`, {
      method: "POST",
    }).then(r => r.bookmarked),
  listBookmarks: (): Promise<Note[]> =>
    request<Note[]>(`${CLOUD_API}/api/v1/vault/bookmarks`),
  getAllTags: (): Promise<TagInfo[]> =>
    request<TagInfo[]>(`${CLOUD_API}/api/v1/vault/tags`),
  getConfig: (key: string): Promise<string | null> =>
    request<{value: string | null}>(`${CLOUD_API}/api/v1/vault/config/${encodeURIComponent(key)}`).then(r => r.value),
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
      method: "PATCH",
      body: JSON.stringify(changes),
    }),
  listProjects: (statusFilter?: string): Promise<Project[]> => {
    const params = statusFilter ? `?statusFilter=${encodeURIComponent(statusFilter)}` : "";
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
      method: "PATCH",
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
      method: "PATCH",
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
      method: "PATCH",
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

  // --- AI operations (redirected from sidecar to Cloud API) ---
  sidecarHealth: async (): Promise<SidecarHealth | null> => {
    // Deprecated: sidecar health check — return a synthetic healthy status
    console.warn("sidecarHealth: sidecar is deprecated, using Cloud API");
    return { status: "ok", provider: "cloud", model: "cloud" };
  },

  extractEntities: async (
    content: string,
    noteId?: string
  ): Promise<ExtractedEntity[]> => {
    try {
      return await request<ExtractedEntity[]>(`${CLOUD_API}/api/v1/tools/extract`, {
        method: "POST",
        body: JSON.stringify({ content, note_id: noteId }),
      });
    } catch {
      return [];
    }
  },

  // --- RAG operations (Cloud API) ---
  ragIndex: async (notes: { id: string; title: string; content: string }[]): Promise<{ indexed: number; chunks: number }> => {
    // No cloud equivalent for indexing — handled server-side automatically
    console.warn("ragIndex: indexing is now handled server-side; this call is a no-op");
    return { indexed: notes.length, chunks: 0 };
  },

  ragStatus: async (): Promise<{ indexed: number; chunks: number; ready: boolean; provider: string; model: string; last_indexed: string | null }> => {
    // No cloud equivalent — return a default ready status
    console.warn("ragStatus: sidecar is deprecated; returning default status");
    return { indexed: 0, chunks: 0, ready: true, provider: "cloud", model: "cloud", last_indexed: null };
  },

  // RAG ask URL — now points to Cloud API
  ragAskUrl: `${CLOUD_API}/api/v1/tools/ask`,

  // RAG vector-only search — redirected to Cloud API
  ragSearch: async (query: string, topK: number = 5): Promise<RAGSearchResult[]> => {
    try {
      return await request<RAGSearchResult[]>(`${CLOUD_API}/api/v1/tools/ask`, {
        method: "POST",
        body: JSON.stringify({ query, top_k: topK }),
      });
    } catch {
      return [];
    }
  },

  // --- Meeting operations (Cloud API) ---
  processMeeting: (content: string, title?: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/tools/extract`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ content, extract_type: "meeting", title }),
    }),

  parseWhatsApp: async (content: string): Promise<{ messages: any[] }> => {
    // Parse WhatsApp export format: [DD/MM/YY, HH:MM] Sender: Message
    const lines = content.split("\n");
    const messages: any[] = [];
    const msgRegex = /^\[?(\d{1,2}\/\d{1,2}\/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*-?\s*([^:]+):\s*(.*)/;
    let currentMsg: any = null;

    for (const line of lines) {
      const match = line.match(msgRegex);
      if (match) {
        if (currentMsg) messages.push(currentMsg);
        currentMsg = {
          timestamp: `${match[1]} ${match[2]}`,
          sender: match[3].trim(),
          content: match[4].trim(),
        };
      } else if (currentMsg) {
        currentMsg.content += "\n" + line;
      }
    }
    if (currentMsg) messages.push(currentMsg);

    // Ingest each message as a context event
    for (const msg of messages.slice(0, 100)) {
      try {
        await api.ingestContextEvent({
          source: "whatsapp",
          event_type: "message",
          content: `${msg.sender}: ${msg.content}`,
          raw_content: msg.content,
          structured_data: { sender: msg.sender },
        });
      } catch (e) { console.warn("Failed to ingest WhatsApp msg:", e); }
    }
    return { messages };
  },

  // --- Action item extraction (Cloud API) ---
  extractActions: async (content: string, noteId: string, noteTitle?: string): Promise<{ action_items: Record<string, unknown>[]; calendar_events: Record<string, unknown>[] }> => {
    try {
      return await request<{ action_items: Record<string, unknown>[]; calendar_events: Record<string, unknown>[] }>(
        `${CLOUD_API}/api/v1/tools/extract`, {
          method: "POST",
          body: JSON.stringify({ content, note_id: noteId, note_title: noteTitle || "", extract_type: "actions" }),
        }
      );
    } catch {
      return { action_items: [], calendar_events: [] };
    }
  },

  // --- Context Hub (Cloud API) ---
  generateBriefing: async (notes: Record<string, unknown>[], actionItems: Record<string, unknown>[], events: Record<string, unknown>[], period: string = "daily"): Promise<{ summary: string; highlights: string[]; attention_needed: string[]; themes: string[] }> => {
    try {
      return await request<{ summary: string; highlights: string[]; attention_needed: string[]; themes: string[] }>(
        `${CLOUD_API}/api/v1/tools/summarize`, {
          method: "POST",
          body: JSON.stringify({ notes, action_items: actionItems, events, period, summary_type: "briefing" }),
        }
      );
    } catch {
      return { summary: "", highlights: [], attention_needed: [], themes: [] };
    }
  },

  findConnections: (content: string, limit?: number): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/tools/connect`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ content, limit: limit || 10 }),
    }),

  // --- Temporal Intelligence (Phase 2 — Cloud API) ---

  /** Generate a preparation brief for a meeting, day, or project */
  prepareContext: async (
    focusType: "meeting" | "day" | "project",
    context: Record<string, unknown>,
    notes: Record<string, unknown>[],
    actions: Record<string, unknown>[],
    decisions: Record<string, unknown>[],
  ): Promise<PrepPack> => {
    try {
      return await request<PrepPack>(`${CLOUD_API}/api/v1/tools/summarize`, {
        method: "POST",
        body: JSON.stringify({
          focus_type: focusType,
          context,
          notes,
          actions,
          decisions,
          summary_type: "prep",
        }),
      });
    } catch {
      return { summary: "", key_points: [], open_questions: [], relevant_history: [], suggested_actions: [] };
    }
  },

  /** Get proactive AI suggestions based on current context */
  getSuggestions: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/insights/suggestions`),

  /** Extract associations between a note and known projects/people */
  extractAssociations: async (
    content: string,
    noteId: string,
    knownProjects: { id: string; title: string }[],
    knownPeople: { id: string; name: string }[],
  ): Promise<{ object_type: string; object_id: string; relationship: string; confidence: number }[]> => {
    try {
      const data = await request<{ associations: { object_type: string; object_id: string; relationship: string; confidence: number }[] }>(
        `${CLOUD_API}/api/v1/tools/extract`, {
          method: "POST",
          body: JSON.stringify({
            content,
            note_id: noteId,
            known_projects: knownProjects,
            known_people: knownPeople,
            extract_type: "associations",
          }),
        }
      );
      return data.associations ?? [];
    } catch {
      return [];
    }
  },

  // ─── Reflection ───────────────────────────────────
  getRelationships: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/reflection/relationships`),

  getPersonDossier: (personId: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/reflection/people/${encodeURIComponent(personId)}/dossier`),

  getWeeklyReview: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/reflection/review/weekly`),

  getMonthlyReflection: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/reflection/review/monthly`),

  mergePeople: (sourceId: string, targetId: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/reflection/people/merge`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ source_person_id: sourceId, target_person_id: targetId }),
    }),

  // ─── Insights ─────────────────────────────────────
  getCommitments: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/insights/commitments`),

  getDormantPeople: (minDays?: number): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/insights/dormant/people${minDays ? `?min_days=${minDays}` : ""}`),

  getDormantProjects: (minDays?: number): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/insights/dormant/projects${minDays ? `?min_days=${minDays}` : ""}`),

  getMorningBriefing: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/insights/briefing/morning`),

  getWeeklyDigest: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/insights/digest/weekly`),

  getPatterns: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/insights/patterns`),

  refreshFreshness: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/insights/freshness/refresh`, { method: "POST", headers: authHeaders() }),

  // ─── Distillation ─────────────────────────────────
  distillContent: (eventId?: string, content?: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/distillation/distill`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId, content }),
    }),

  getDistillationStatus: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/distillation/status`),

  triggerAutoDistill: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/distillation/auto`, { method: "POST", headers: authHeaders() }),

  // ─── Integrations ─────────────────────────────────
  connectIntegration: (provider: string, redirectUri?: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/integrations/connect`, {
      method: "POST",
      body: JSON.stringify({ provider, redirect_uri: redirectUri || `${CLOUD_API}/api/v1/integrations/callback/${provider}` }),
    }),
  listIntegrations: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/integrations`),
  disconnectIntegration: (provider: string): Promise<void> =>
    request<void>(`${CLOUD_API}/api/v1/integrations/${encodeURIComponent(provider)}`, {
      method: "DELETE",
    }),
  syncIntegration: (provider: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/integrations/${encodeURIComponent(provider)}/sync`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  // ─── Context Events ───────────────────────────────
  getContextEvents: (source?: string, since?: string, until?: string, limit?: number): Promise<any[]> => {
    const params = new URLSearchParams();
    if (source) params.set("source", source);
    if (since) params.set("since", since);
    if (until) params.set("until", until);
    if (limit) params.set("limit", String(limit));
    const qs = params.toString();
    return request<any[]>(`${CLOUD_API}/api/v1/context/events${qs ? `?${qs}` : ""}`);
  },

  getContextTimeline: (days?: number): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/context/timeline${days ? `?days=${days}` : ""}`),

  ingestContextEvent: (event: Record<string, any>): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/context/ingest`, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: JSON.stringify(event),
    }),

  // ─── Intelligence Layer (Phase 5B) ───────────────
  getUpcomingBriefings: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/intelligence/briefing/upcoming`),

  getMeetingBriefing: (meetingId: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/briefing/${encodeURIComponent(meetingId)}`),

  getWeeklyReport: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/report/weekly`),

  generateWeeklyReport: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/report/weekly/generate`),

  getFollowUps: (): Promise<any[]> =>
    request<any[]>(`${CLOUD_API}/api/v1/intelligence/followups`),

  getRelationshipDashboard: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/relationships`),

  getRelationshipScore: (personId: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/relationships/${encodeURIComponent(personId)}`),

  getIntelligenceSummary: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/intelligence/insights/summary`),

  // ─── Ask AI (Cloud RAG) ────────────────────────────
  askAI: (question: string): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/tools/ask`, {
      method: "POST",
      body: JSON.stringify({ query: question }),
    }),

  // ─── Predictions ───────────────────────────────────
  getActivityForecast: (days: number = 14): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/activity/forecast`, {
      method: "POST",
      body: JSON.stringify({ horizon: days }),
    }),

  getEmergingEntities: (days: number = 30): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/entities/emerging`, {
      method: "POST",
      body: JSON.stringify({ lookback_days: days }),
    }),

  getRelationshipForecast: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/relationships/forecast`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  getGraphEvolution: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/graph/evolution`, {
      method: "POST",
      body: JSON.stringify({}),
    }),

  getPredictionSummary: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/summary`),

  getDormancyRisk: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/dormancy-risk`),

  getForecastAccuracy: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/predictions/accuracy`),

  // ─── Setup & Getting Started ───────────────────────
  getSetupStatus: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/setup/status`),

  getSetupConfig: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/setup/config`),

  testLLM: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/setup/test-llm`, { method: "POST" }),

  initDatabase: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/setup/init-db`, { method: "POST" }),

  getOllamaModels: (): Promise<any> =>
    request<any>(`${CLOUD_API}/api/v1/setup/ollama/models`),
};
