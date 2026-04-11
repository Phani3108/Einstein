import { useReducer, useEffect, useCallback, useState } from "react";
import { AppContext, appReducer, initialState } from "./lib/store";
import { initLanguage } from "./lib/i18n";
import { api } from "./lib/api";
import { processNoteThroughPipeline, loadCentralState } from "./lib/dataPipeline";
import ErrorBoundary from "./components/ErrorBoundary";
import OfflineBanner from "./components/OfflineBanner";
import { Sidebar } from "./components/Sidebar";
import { Editor } from "./components/Editor";
import { RightPanel } from "./components/RightPanel";
import { ContextPanel } from "./components/ContextPanel";
import { CommandPalette } from "./components/CommandPalette";
import { SearchModal } from "./components/SearchModal";
import { BrainHome } from "./components/BrainHome";
import { ProjectDetail } from "./components/ProjectDetail";
import { PersonDetail } from "./components/PersonDetail";
import { DecisionDetail } from "./components/DecisionDetail";
import { GraphView } from "./components/GraphView";
import { CanvasView } from "./components/CanvasView";
import { CalendarView } from "./components/CalendarView";
import { KanbanView } from "./components/KanbanView";
import { ExportImport } from "./components/ExportImport";
import { PluginPanel } from "./components/PluginPanel";
import { BookmarksPanel } from "./components/BookmarksPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { WikilinkPreview } from "./components/WikilinkPreview";
import { InsightsDashboard } from "./components/InsightsDashboard";
import { RAGPanel } from "./components/RAGPanel";
import { MeetingsPanel } from "./components/MeetingsPanel";
import { ActionItemsDashboard } from "./components/ActionItemsDashboard";
import { IntegrationsPanel } from "./components/IntegrationsPanel";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { NoteNameModal } from "./components/NoteNameModal";
import { FloatingVoiceButton } from "./components/VoiceInput";
import { syncManager } from "./lib/sync";
import "./styles/global.css";

// Initialize i18n before render
initLanguage();

// Auto-provision auth token for development (cloud mode)
if (!localStorage.getItem("einstein_auth_token")) {
  // Development token — replace with real auth flow in production
  localStorage.setItem("einstein_auth_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2MGJkOTVlMC0xZDg2LTQ5YTAtOTljNC0xYjcyNzczYmE0NTAiLCJlbWFpbCI6ImFkbWluQGVpbnN0ZWluLmFwcCIsImV4cCI6MTgwNzAxODEwM30.atuZ75fSz9rQjo34IylgN3ZTv7wkD4-Sy7nX5Q-Ck4Y");
}

function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const [noteModalOpen, setNoteModalOpen] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);

  // Initialize sync when vault opens
  useEffect(() => {
    if (state.vaultPath) {
      const vaultId = state.vaultPath.replace(/[^a-zA-Z0-9]/g, "-");
      syncManager.init(vaultId, "local");

      // Hydrate central state from DB (action items, calendar events, RAG index)
      loadCentralState(dispatch, state.notes).catch((err) =>
        console.error("Failed to load central state:", err)
      );

      // Load first-class objects (projects, people, decisions)
      api.listProjects().then((projects) =>
        dispatch({ type: "SET_PROJECTS", projects: projects.map((p) => ({ ...p, status: p.status as "active" | "paused" | "completed" | "archived" })) })
      ).catch((err) => console.error("Failed to load projects:", err));

      api.listPeople().then((people) =>
        dispatch({ type: "SET_PEOPLE", people })
      ).catch((err) => console.error("Failed to load people:", err));

      api.listDecisions().then((decisions) =>
        dispatch({ type: "SET_DECISIONS", decisions: decisions.map((d) => ({ ...d, status: d.status as "active" | "revisit" | "reversed" | "superseded" })) })
      ).catch((err) => console.error("Failed to load decisions:", err));

      // Load intelligence data
      api.getMorningBriefing().then(b => dispatch({ type: "SET_BRIEFING", briefing: b })).catch(() => {});
      api.getDormantPeople().then(p => dispatch({ type: "SET_DORMANT_PEOPLE", people: p })).catch(() => {});
      api.getDormantProjects().then(p => dispatch({ type: "SET_DORMANT_PROJECTS", projects: p })).catch(() => {});
      api.getCommitments().then(c => dispatch({ type: "SET_COMMITMENTS", commitments: c })).catch(() => {});
      api.getContextEvents(undefined, undefined, undefined, 50).then(e => dispatch({ type: "SET_CONTEXT_EVENTS", events: e })).catch(() => {});

      // Load prediction data
      api.getPredictionSummary().then(s => dispatch({ type: "SET_PREDICTION_SUMMARY", summary: s })).catch(() => {});
      api.getDormancyRisk().then(r => dispatch({ type: "SET_DORMANCY_RISK", entries: Array.isArray(r) ? r : r?.entries ?? [] })).catch(() => {});
    }
    return () => {
      syncManager.destroy();
    };
  }, [state.vaultPath]); // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for custom events from other components
  useEffect(() => {
    const handleCreateProject = async () => {
      try {
        const project = await api.createProject("New Project", "", "", "", undefined);
        dispatch({ type: "ADD_PROJECT", project: { ...project, status: project.status as "active" | "paused" | "completed" | "archived" } });
        dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId: project.id } });
      } catch (err) {
        console.error("Failed to create project:", err);
      }
    };
    const handleCreateNote = () => setNoteModalOpen(true);

    window.addEventListener("einstein-create-project", handleCreateProject);
    window.addEventListener("einstein-create-note", handleCreateNote);
    return () => {
      window.removeEventListener("einstein-create-project", handleCreateProject);
      window.removeEventListener("einstein-create-note", handleCreateNote);
    };
  }, [dispatch]);

  const handleCreateNote = useCallback(
    async (name: string) => {
      const filePath = `${name.replace(/\s+/g, "-").toLowerCase()}.md`;
      try {
        const note = await api.saveNote(filePath, name, `# ${name}\n\n`, {});
        dispatch({ type: "UPDATE_NOTE", note });
        dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
        // Run through pipeline (note is already saved)
        processNoteThroughPipeline(note, dispatch, {
          alreadySaved: true,
          source: "new-note",
        }).catch((err) => console.error("Pipeline failed for new note:", err));
      } catch (err) {
        console.error("Failed to create note:", err);
      }
    },
    [dispatch]
  );

  // Global keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;

      if (mod && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
      if (mod && e.key === "p") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
      if (mod && e.key === "n") {
        e.preventDefault();
        setNoteModalOpen(true);
      }
      if (mod && e.key === "s") {
        e.preventDefault();
        // Save handled by editor
      }
      if (mod && e.key === "\\") {
        e.preventDefault();
        dispatch({ type: "TOGGLE_SIDEBAR" });
      }
      if (e.key === "Escape" && state.searchOpen) {
        dispatch({ type: "CLOSE_SEARCH" });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [state.searchOpen]);

  if (!state.vaultPath) {
    return (
      <AppContext.Provider value={{ state, dispatch }}>
        <WelcomeScreen />
      </AppContext.Provider>
    );
  }

  const renderMainContent = () => {
    // ContextMode routing (new system) — checked first
    const mode = state.contextMode;
    switch (mode.type) {
      case "home":
        // Only render BrainHome if sidebarView is "contexthub" or "files" (default)
        if (state.sidebarView === "contexthub" || state.sidebarView === "files") {
          return <ErrorBoundary name="MainContent"><BrainHome /></ErrorBoundary>;
        }
        break;
      case "project":
        return <ErrorBoundary name="MainContent"><ProjectDetail projectId={mode.projectId} /></ErrorBoundary>;
      case "person":
        return <ErrorBoundary name="MainContent"><PersonDetail personId={mode.personId} /></ErrorBoundary>;
      case "decision":
        return <ErrorBoundary name="MainContent"><DecisionDetail decisionId={mode.decisionId} /></ErrorBoundary>;
      // Other contextMode types fall through to sidebarView
    }

    // Legacy sidebarView routing (preserved during migration)
    switch (state.sidebarView) {
      case "graph":
        return <ErrorBoundary name="MainContent"><GraphView /></ErrorBoundary>;
      case "canvas":
        return <ErrorBoundary name="MainContent"><CanvasView /></ErrorBoundary>;
      case "calendar":
        return <ErrorBoundary name="MainContent"><CalendarView /></ErrorBoundary>;
      case "kanban":
        return <ErrorBoundary name="MainContent"><KanbanView /></ErrorBoundary>;
      case "export":
        return <ErrorBoundary name="MainContent"><ExportImport /></ErrorBoundary>;
      case "plugins":
        return <ErrorBoundary name="MainContent"><PluginPanel /></ErrorBoundary>;
      case "bookmarks":
        return <ErrorBoundary name="MainContent"><BookmarksPanel /></ErrorBoundary>;
      case "settings":
        return <ErrorBoundary name="MainContent"><SettingsPanel /></ErrorBoundary>;
      case "insights":
        return <ErrorBoundary name="MainContent"><InsightsDashboard /></ErrorBoundary>;
      case "rag":
        return <ErrorBoundary name="MainContent"><RAGPanel /></ErrorBoundary>;
      case "meetings":
        return <ErrorBoundary name="MainContent"><MeetingsPanel /></ErrorBoundary>;
      case "actions":
        return <ErrorBoundary name="MainContent"><ActionItemsDashboard /></ErrorBoundary>;
      case "integrations":
        return <ErrorBoundary name="MainContent"><IntegrationsPanel /></ErrorBoundary>;
      case "contexthub":
        return <ErrorBoundary name="MainContent"><BrainHome /></ErrorBoundary>;
      default:
        return <ErrorBoundary name="MainContent"><Editor /></ErrorBoundary>;
    }
  };

  // Show context panel when right panel is open — ContextPanel handles everything
  const showContextPanel = state.rightPanelOpen;
  // Secondary tabs removed — navigation handled via Sidebar and ContextMode

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      <ErrorBoundary name="App">
      <OfflineBanner />
      <div className="app-layout">
        <Sidebar />
        <div className="center-panel">
          {renderMainContent()}
        </div>
        {showContextPanel && (
          state.activeNoteId
            ? <ErrorBoundary name="RightPanel"><RightPanel /></ErrorBoundary>
            : <ErrorBoundary name="ContextPanel"><ContextPanel /></ErrorBoundary>
        )}
      </div>
      <ErrorBoundary name="CommandPalette"><CommandPalette open={commandPaletteOpen} onClose={() => setCommandPaletteOpen(false)} /></ErrorBoundary>
      <SearchModal />
      <WikilinkPreview />
      <NoteNameModal
        open={noteModalOpen}
        onClose={() => setNoteModalOpen(false)}
        onSubmit={handleCreateNote}
      />
      <FloatingVoiceButton
        onTranscript={(text) => {
          // Insert voice transcript into active editor if available
          const editor = document.querySelector(".tiptap") as HTMLElement;
          if (editor) {
            // Dispatch a custom event that the Editor component can listen to
            window.dispatchEvent(new CustomEvent("einstein-voice-input", { detail: text }));
          }
        }}
      />
      </ErrorBoundary>
    </AppContext.Provider>
  );
}

export default App;
