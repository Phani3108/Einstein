/**
 * Zustand store — single source of truth for the mobile app.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import type {
  ContextEvent,
  Person,
  Project,
  BriefingData,
  SyncStatus,
  Commitment,
} from "./types";

interface AppState {
  // Data
  events: ContextEvent[];
  people: Person[];
  projects: Project[];
  commitments: Commitment[];
  briefing: BriefingData | null;

  // Sync
  sync: SyncStatus;

  // Auth
  authToken: string | null;
  serverUrl: string;

  // Actions — events
  addEvent: (event: ContextEvent) => void;
  addEvents: (events: ContextEvent[]) => void;
  setEvents: (events: ContextEvent[]) => void;
  markSynced: (ids: string[]) => void;

  // Actions — people
  setPeople: (people: Person[]) => void;
  upsertPerson: (person: Person) => void;

  // Actions — projects
  setProjects: (projects: Project[]) => void;

  // Actions — commitments
  setCommitments: (commitments: Commitment[]) => void;

  // Actions — briefing
  setBriefing: (briefing: BriefingData | null) => void;

  // Actions — sync
  setSyncStatus: (status: Partial<SyncStatus>) => void;

  // Actions — auth
  setAuthToken: (token: string | null) => void;
  setServerUrl: (url: string) => void;

  // Selectors
  unsynced: () => ContextEvent[];
  recentEvents: (limit?: number) => ContextEvent[];
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
  // Initial state
  events: [],
  people: [],
  projects: [],
  commitments: [],
  briefing: null,
  sync: {
    lastSyncAt: null,
    pendingCount: 0,
    isSyncing: false,
    error: null,
  },
  authToken: null,
  serverUrl: "http://localhost:8000",

  // Events
  addEvent: (event) =>
    set((s) => {
      // Deduplicate by ID
      if (s.events.some((e) => e.id === event.id)) return s;
      return {
        events: [event, ...s.events],
        sync: { ...s.sync, pendingCount: s.sync.pendingCount + 1 },
      };
    }),

  addEvents: (events) =>
    set((s) => ({
      events: [...events, ...s.events],
      sync: { ...s.sync, pendingCount: s.sync.pendingCount + events.filter((e) => !e.synced).length },
    })),

  setEvents: (events) => set({ events }),

  markSynced: (ids) =>
    set((s) => {
      const idSet = new Set(ids);
      return {
        events: s.events.map((e) =>
          idSet.has(e.id) ? { ...e, synced: true } : e
        ),
        sync: {
          ...s.sync,
          pendingCount: Math.max(0, s.sync.pendingCount - ids.length),
        },
      };
    }),

  // People
  setPeople: (people) => set({ people }),
  upsertPerson: (person) =>
    set((s) => {
      const idx = s.people.findIndex((p) => p.id === person.id);
      if (idx >= 0) {
        const updated = [...s.people];
        updated[idx] = person;
        return { people: updated };
      }
      return { people: [...s.people, person] };
    }),

  // Projects
  setProjects: (projects) => set({ projects }),

  // Commitments
  setCommitments: (commitments) => set({ commitments }),

  // Briefing
  setBriefing: (briefing) => set({ briefing }),

  // Sync
  setSyncStatus: (status) =>
    set((s) => ({ sync: { ...s.sync, ...status } })),

  // Auth
  setAuthToken: (token) => set({ authToken: token }),
  setServerUrl: (url) => set({ serverUrl: url }),

  // Selectors
  unsynced: () => get().events.filter((e) => !e.synced),
  recentEvents: (limit = 50) =>
    [...get().events]
      .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
      .slice(0, limit),
    }),
    {
      name: "einstein-app-storage",
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        serverUrl: state.serverUrl,
        authToken: state.authToken,
        events: state.events.slice(0, 100),
        people: state.people,
        projects: state.projects,
        commitments: state.commitments,
      }),
    },
  ),
);
