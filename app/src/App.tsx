import { useReducer, useEffect, useCallback, useState } from "react";
import { AppContext, appReducer, initialState } from "./lib/store";
import type { SidebarView } from "./lib/store";
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
import { ContextHub } from "./components/ContextHub";
import { WelcomeScreen } from "./components/WelcomeScreen";
import { NoteNameModal } from "./components/NoteNameModal";
import { FloatingVoiceButton } from "./components/VoiceInput";
import { syncManager } from "./lib/sync";
import {
  PenTool, Columns3, Download, Link2, Puzzle,
  Lightbulb,
  MessageSquare, Video, CheckSquare, LayoutDashboard,
} from "lucide-react";
import "./styles/global.css";

/* Secondary views shown as tabs in the top toolbar of the center panel */
const SECONDARY_TABS: { view: SidebarView; label: string; icon: React.ReactNode }[] = [
  { view: "contexthub", label: "Hub", icon: <LayoutDashboard size={13} /> },
  { view: "rag", label: "Ask Notes", icon: <MessageSquare size={13} /> },
  { view: "meetings", label: "Meetings", icon: <Video size={13} /> },
  { view: "actions", label: "Actions", icon: <CheckSquare size={13} /> },
  { view: "canvas", label: "Canvas", icon: <PenTool size={13} /> },
  { view: "kanban", label: "Kanban", icon: <Columns3 size={13} /> },
  { view: "backlinks", label: "Backlinks", icon: <Link2 size={13} /> },
  { view: "insights", label: "Insights", icon: <Lightbulb size={13} /> },
  { view: "export", label: "Export", icon: <Download size={13} /> },
  { view: "plugins", label: "Plugins", icon: <Puzzle size={13} /> },
];

// Initialize i18n before render
initLanguage();

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
      case "contexthub":
        return <ErrorBoundary name="MainContent"><BrainHome /></ErrorBoundary>;
      default:
        return <ErrorBoundary name="MainContent"><Editor /></ErrorBoundary>;
    }
  };

  // Show context panel for contextMode views, legacy RightPanel for old views
  const contextModeActive = ["project", "person", "decision"].includes(state.contextMode.type);
  const showContextPanel = state.rightPanelOpen && (
    state.sidebarView === "files" || contextModeActive
  );
  const showLegacyRightPanel = state.rightPanelOpen && !showContextPanel && ["backlinks", "search", "bookmarks"].includes(state.sidebarView);
  // Always show secondary tabs unless on full-page views or contextMode detail views
  const fullPageViews = ["settings"];
  const showSecondaryTabs = !fullPageViews.includes(state.sidebarView) && !contextModeActive;

  return (
    <AppContext.Provider value={{ state, dispatch }}>
      <ErrorBoundary name="App">
      <OfflineBanner />
      <div className="app-layout">
        <Sidebar />
        <div className="center-panel">
          {showSecondaryTabs && (
            <div className="secondary-tabs">
              {SECONDARY_TABS.map((tab) => (
                <button
                  key={tab.view}
                  className={`secondary-tab ${state.sidebarView === tab.view ? "active" : ""}`}
                  onClick={() => dispatch({
                    type: "SET_SIDEBAR_VIEW",
                    view: state.sidebarView === tab.view ? "files" : tab.view,
                  })}
                  title={tab.label}
                >
                  {tab.icon}
                  <span>{tab.label}</span>
                </button>
              ))}
            </div>
          )}
          {renderMainContent()}
        </div>
        {showContextPanel && <ErrorBoundary name="ContextPanel"><ContextPanel /></ErrorBoundary>}
        {showLegacyRightPanel && <RightPanel />}
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
