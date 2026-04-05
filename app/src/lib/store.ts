import { createContext, useContext } from "react";
import type { Note } from "./api";

export type SidebarView = "files" | "search" | "graph" | "backlinks" | "canvas" | "calendar" | "kanban" | "export" | "plugins" | "settings" | "bookmarks" | "devhub" | "integrations" | "aitools" | "insights" | "dataexchange" | "privacy" | "rag" | "meetings" | "actions" | "contexthub";

/* ------------------------------------------------------------------ */
/*  Context Mode — replaces tab-based routing with contextual routing   */
/* ------------------------------------------------------------------ */

export type ContextMode =
  | { type: "home" }
  | { type: "editor"; noteId: string }
  | { type: "project"; projectId: string }
  | { type: "person"; personId: string }
  | { type: "decision"; decisionId: string }
  | { type: "search"; query?: string }
  | { type: "graph" }
  | { type: "canvas" }
  | { type: "settings" }
  | { type: "tool"; toolId: string };

/* ------------------------------------------------------------------ */
/*  First-class object types                                           */
/* ------------------------------------------------------------------ */

export interface ProjectState {
  id: string;
  title: string;
  description: string;
  status: "active" | "paused" | "completed" | "archived";
  category: string;
  goal: string;
  deadline: string | null;
  created_at: string;
  updated_at: string;
}

export interface PersonState {
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

export interface DecisionState {
  id: string;
  title: string;
  description: string;
  reasoning: string;
  alternatives: string;
  status: "active" | "revisit" | "reversed" | "superseded";
  decided_at: string;
  revisit_date: string | null;
  created_at: string;
}

export interface NoteAssociationState {
  id: string;
  note_id: string;
  object_type: "project" | "person" | "decision";
  object_id: string;
  relationship: string;
  confidence: number;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Shared types for cross-feature state                               */
/* ------------------------------------------------------------------ */

export interface ActionItemState {
  id: string;
  note_id: string;
  task: string;
  assignee: string | null;
  deadline: string | null;
  priority: "high" | "medium" | "low";
  status: "pending" | "completed" | "cancelled";
  created_at: string;
  // Denormalized for display — avoids lookup on every render
  source_title: string;
}

export interface CalendarEventState {
  id: string;
  note_id: string;
  title: string;
  event_date: string;
  event_type: "deadline" | "follow_up" | "meeting" | "reminder";
  description: string;
  created_at: string;
  // Denormalized
  source_title: string;
}

export interface AppState {
  vaultPath: string | null;
  notes: Note[];
  activeNoteId: string | null;
  searchOpen: boolean;
  sidebarView: SidebarView;
  sidebarCollapsed: boolean;
  rightPanelOpen: boolean;
  loading: boolean;
  error: string | null;
  connectionMode: "local" | "cloud";
  bookmarks: string[];  // note IDs
  // First-class objects
  projects: ProjectState[];
  people: PersonState[];
  decisions: DecisionState[];
  // Context mode (new contextual routing — coexists with sidebarView during migration)
  contextMode: ContextMode;
  // Central state for cross-feature data
  actionItems: ActionItemState[];
  calendarEvents: CalendarEventState[];
  pipelineRunning: boolean;
}

export const initialState: AppState = {
  vaultPath: null,
  notes: [],
  activeNoteId: null,
  searchOpen: false,
  sidebarView: "files",
  sidebarCollapsed: false,
  rightPanelOpen: true,
  loading: false,
  error: null,
  connectionMode: "local",
  bookmarks: [],
  projects: [],
  people: [],
  decisions: [],
  contextMode: { type: "home" },
  actionItems: [],
  calendarEvents: [],
  pipelineRunning: false,
};

export type AppAction =
  | { type: "SET_VAULT"; path: string; notes: Note[] }
  | { type: "SET_NOTES"; notes: Note[] }
  | { type: "SET_ACTIVE_NOTE"; id: string | null }
  | { type: "UPDATE_NOTE"; note: Note }
  | { type: "DELETE_NOTE"; id: string }
  | { type: "TOGGLE_SEARCH" }
  | { type: "CLOSE_SEARCH" }
  | { type: "SET_SIDEBAR_VIEW"; view: SidebarView }
  | { type: "TOGGLE_SIDEBAR" }
  | { type: "TOGGLE_RIGHT_PANEL" }
  | { type: "SET_LOADING"; loading: boolean }
  | { type: "SET_ERROR"; error: string | null }
  | { type: "SET_CONNECTION_MODE"; mode: "local" | "cloud" }
  | { type: "SET_BOOKMARKS"; bookmarks: string[] }
  | { type: "TOGGLE_BOOKMARK"; noteId: string }
  // Context mode
  | { type: "SET_CONTEXT_MODE"; mode: ContextMode }
  // Projects
  | { type: "SET_PROJECTS"; projects: ProjectState[] }
  | { type: "ADD_PROJECT"; project: ProjectState }
  | { type: "UPDATE_PROJECT"; id: string; changes: Partial<ProjectState> }
  | { type: "DELETE_PROJECT"; id: string }
  // People
  | { type: "SET_PEOPLE"; people: PersonState[] }
  | { type: "ADD_PERSON"; person: PersonState }
  | { type: "UPDATE_PERSON"; id: string; changes: Partial<PersonState> }
  | { type: "DELETE_PERSON"; id: string }
  // Decisions
  | { type: "SET_DECISIONS"; decisions: DecisionState[] }
  | { type: "ADD_DECISION"; decision: DecisionState }
  | { type: "UPDATE_DECISION"; id: string; changes: Partial<DecisionState> }
  | { type: "DELETE_DECISION"; id: string }
  // Cross-feature actions
  | { type: "SET_ACTION_ITEMS"; items: ActionItemState[] }
  | { type: "ADD_ACTION_ITEMS"; items: ActionItemState[] }
  | { type: "UPDATE_ACTION_ITEM"; id: string; changes: Partial<ActionItemState> }
  | { type: "REMOVE_ACTION_ITEMS_FOR_NOTE"; noteId: string }
  | { type: "SET_CALENDAR_EVENTS"; events: CalendarEventState[] }
  | { type: "ADD_CALENDAR_EVENTS"; events: CalendarEventState[] }
  | { type: "REMOVE_CALENDAR_EVENTS_FOR_NOTE"; noteId: string }
  | { type: "SET_PIPELINE_RUNNING"; running: boolean };

export function appReducer(state: AppState, action: AppAction): AppState {
  switch (action.type) {
    case "SET_VAULT":
      return {
        ...state,
        vaultPath: action.path,
        notes: action.notes,
        activeNoteId: action.notes[0]?.id ?? null,
        loading: false,
        error: null,
      };
    case "SET_NOTES":
      return { ...state, notes: action.notes };
    case "SET_ACTIVE_NOTE":
      return { ...state, activeNoteId: action.id };
    case "UPDATE_NOTE": {
      const exists = state.notes.some((n) => n.id === action.note.id);
      return {
        ...state,
        notes: exists
          ? state.notes.map((n) => (n.id === action.note.id ? action.note : n))
          : [action.note, ...state.notes],
      };
    }
    case "DELETE_NOTE":
      return {
        ...state,
        notes: state.notes.filter((n) => n.id !== action.id),
        activeNoteId:
          state.activeNoteId === action.id ? null : state.activeNoteId,
      };
    case "TOGGLE_SEARCH":
      return { ...state, searchOpen: !state.searchOpen };
    case "CLOSE_SEARCH":
      return { ...state, searchOpen: false };
    case "SET_SIDEBAR_VIEW":
      return { ...state, sidebarView: action.view };
    case "TOGGLE_SIDEBAR":
      return { ...state, sidebarCollapsed: !state.sidebarCollapsed };
    case "TOGGLE_RIGHT_PANEL":
      return { ...state, rightPanelOpen: !state.rightPanelOpen };
    case "SET_LOADING":
      return { ...state, loading: action.loading };
    case "SET_ERROR":
      return { ...state, error: action.error, loading: false };
    case "SET_CONNECTION_MODE":
      return { ...state, connectionMode: action.mode };
    case "SET_BOOKMARKS":
      return { ...state, bookmarks: action.bookmarks };
    case "TOGGLE_BOOKMARK":
      return {
        ...state,
        bookmarks: state.bookmarks.includes(action.noteId)
          ? state.bookmarks.filter((id) => id !== action.noteId)
          : [...state.bookmarks, action.noteId],
      };
    // --- Context mode ---
    case "SET_CONTEXT_MODE":
      return { ...state, contextMode: action.mode };
    // --- Projects ---
    case "SET_PROJECTS":
      return { ...state, projects: action.projects };
    case "ADD_PROJECT":
      return { ...state, projects: [action.project, ...state.projects] };
    case "UPDATE_PROJECT":
      return {
        ...state,
        projects: state.projects.map((p) =>
          p.id === action.id ? { ...p, ...action.changes } : p
        ),
      };
    case "DELETE_PROJECT":
      return {
        ...state,
        projects: state.projects.filter((p) => p.id !== action.id),
      };
    // --- People ---
    case "SET_PEOPLE":
      return { ...state, people: action.people };
    case "ADD_PERSON":
      return { ...state, people: [action.person, ...state.people] };
    case "UPDATE_PERSON":
      return {
        ...state,
        people: state.people.map((p) =>
          p.id === action.id ? { ...p, ...action.changes } : p
        ),
      };
    case "DELETE_PERSON":
      return {
        ...state,
        people: state.people.filter((p) => p.id !== action.id),
      };
    // --- Decisions ---
    case "SET_DECISIONS":
      return { ...state, decisions: action.decisions };
    case "ADD_DECISION":
      return { ...state, decisions: [action.decision, ...state.decisions] };
    case "UPDATE_DECISION":
      return {
        ...state,
        decisions: state.decisions.map((d) =>
          d.id === action.id ? { ...d, ...action.changes } : d
        ),
      };
    case "DELETE_DECISION":
      return {
        ...state,
        decisions: state.decisions.filter((d) => d.id !== action.id),
      };
    // --- Cross-feature state ---
    case "SET_ACTION_ITEMS":
      return { ...state, actionItems: action.items };
    case "ADD_ACTION_ITEMS": {
      // Merge: replace items for same note, add new ones
      const noteIds = new Set(action.items.map((i) => i.note_id));
      const kept = state.actionItems.filter((i) => !noteIds.has(i.note_id));
      return { ...state, actionItems: [...kept, ...action.items] };
    }
    case "UPDATE_ACTION_ITEM":
      return {
        ...state,
        actionItems: state.actionItems.map((i) =>
          i.id === action.id ? { ...i, ...action.changes } : i
        ),
      };
    case "REMOVE_ACTION_ITEMS_FOR_NOTE":
      return {
        ...state,
        actionItems: state.actionItems.filter((i) => i.note_id !== action.noteId),
      };
    case "SET_CALENDAR_EVENTS":
      return { ...state, calendarEvents: action.events };
    case "ADD_CALENDAR_EVENTS": {
      const noteIds = new Set(action.events.map((e) => e.note_id));
      const kept = state.calendarEvents.filter((e) => !noteIds.has(e.note_id));
      return { ...state, calendarEvents: [...kept, ...action.events] };
    }
    case "REMOVE_CALENDAR_EVENTS_FOR_NOTE":
      return {
        ...state,
        calendarEvents: state.calendarEvents.filter((e) => e.note_id !== action.noteId),
      };
    case "SET_PIPELINE_RUNNING":
      return { ...state, pipelineRunning: action.running };
    default:
      return state;
  }
}

export const AppContext = createContext<{
  state: AppState;
  dispatch: React.Dispatch<AppAction>;
}>({ state: initialState, dispatch: () => {} });

export function useApp() {
  return useContext(AppContext);
}
