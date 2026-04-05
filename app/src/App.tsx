import { useReducer, useEffect, useCallback, useState } from "react";
import { AppContext, appReducer, initialState } from "./lib/store";
import type { SidebarView } from "./lib/store";
import { initLanguage } from "./lib/i18n";
import { api } from "./lib/api";
import { processNoteThroughPipeline, loadCentralState } from "./lib/dataPipeline";
import { Sidebar } from "./components/Sidebar";
import { Editor } from "./components/Editor";
import { RightPanel } from "./components/RightPanel";
import { SearchModal } from "./components/SearchModal";
import { GraphView } from "./components/GraphView";
import { CanvasView } from "./components/CanvasView";
import { CalendarView } from "./components/CalendarView";
import { KanbanView } from "./components/KanbanView";
import { ExportImport } from "./components/ExportImport";
import { PluginPanel } from "./components/PluginPanel";
import { BookmarksPanel } from "./components/BookmarksPanel";
import { SettingsPanel } from "./components/SettingsPanel";
import { DevHub } from "./components/DevHub";
import { IntegrationsHub } from "./components/IntegrationsHub";
import { WikilinkPreview } from "./components/WikilinkPreview";
import { AIToolsHub } from "./components/AIToolsHub";
import { InsightsDashboard } from "./components/InsightsDashboard";
import { DataExchange } from "./components/DataExchange";
import { PrivacyCenter } from "./components/PrivacyCenter";
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
  Brain, Lightbulb, ArrowLeftRight, Shield,
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
  { view: "aitools", label: "AI Tools", icon: <Brain size={13} /> },
  { view: "insights", label: "Insights", icon: <Lightbulb size={13} /> },
  { view: "dataexchange", label: "Data", icon: <ArrowLeftRight size={13} /> },
  { view: "privacy", label: "Privacy", icon: <Shield size={13} /> },
  { view: "export", label: "Export", icon: <Download size={13} /> },
  { view: "plugins", label: "Plugins", icon: <Puzzle size={13} /> },
];

// Initialize i18n before render
initLanguage();

function App() {
  const [state, dispatch] = useReducer(appReducer, initialState);
  const [noteModalOpen, setNoteModalOpen] = useState(false);

  // Initialize sync when vault opens
  useEffect(() => {
    if (state.vaultPath) {
      const vaultId = state.vaultPath.replace(/[^a-zA-Z0-9]/g, "-");
      syncManager.init(vaultId, "local");

      // Hydrate central state from DB (action items, calendar events, RAG index)
      loadCentralState(dispatch, state.notes).catch((err) =>
        console.error("Failed to load central state:", err)
      );
    }
    return () => {
      syncManager.destroy();
    };
  }, [state.vaultPath]); // eslint-disable-line react-hooks/exhaustive-deps

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

      if (mod && e.key === "p") {
        e.preventDefault();
        dispatch({ type: "TOGGLE_SEARCH" });
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
    switch (state.sidebarView) {
      case "graph":
        return <GraphView />;
      case "canvas":
        return <CanvasView />;
      case "calendar":
        return <CalendarView />;
      case "kanban":
        return <KanbanView />;
      case "export":
        return <ExportImport />;
      case "plugins":
        return <PluginPanel />;
      case "bookmarks":
        return <BookmarksPanel />;
      case "settings":
        return <SettingsPanel />;
      case "devhub":
        return <DevHub />;
      case "integrations":
        return <IntegrationsHub />;
      case "aitools":
        return <AIToolsHub />;
      case "insights":
        return <InsightsDashboard />;
      case "dataexchange":
        return <DataExchange />;
      case "privacy":
        return <PrivacyCenter />;
      case "rag":
        return <RAGPanel />;
      case "meetings":
        return <MeetingsPanel />;
      case "actions":
        return <ActionItemsDashboard />;
      case "contexthub":
        return <ContextHub />;
      default:
        return <Editor />;
    }
  };

  const showRightPanel = ["files", "backlinks", "search", "bookmarks"].includes(state.sidebarView);
  // Always show secondary tabs unless on full-page views like settings/devhub/integrations
  const fullPageViews = ["settings", "devhub", "integrations"];
  const showSecondaryTabs = !fullPageViews.includes(state.sidebarView);

  return (
    <AppContext.Provider value={{ state, dispatch }}>
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
        {showRightPanel && <RightPanel />}
      </div>
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
    </AppContext.Provider>
  );
}

export default App;
