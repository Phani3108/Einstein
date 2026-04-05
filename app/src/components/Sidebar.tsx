import React, { useState, useMemo, useCallback } from "react";
import {
  FileText,
  Search,
  GitBranch,
  Link2,
  Plus,
  Calendar,
  ChevronRight,
  FolderClosed,
  Star,
  Plug,
  BookOpen,
  Settings,
} from "lucide-react";
import { useApp } from "../lib/store";
import { useTranslation } from "../lib/i18n";
import { api } from "../lib/api";
import type { Note } from "../lib/api";
import { NoteNameModal } from "./NoteNameModal";

import type { SidebarView } from "../lib/store";

interface NavItem {
  icon: React.ReactNode;
  title: string;
  view?: SidebarView;
  action?: () => void;
  divider?: boolean;
}

function useNavItems(dispatch: React.Dispatch<import("../lib/store").AppAction>): NavItem[] {
  const { t } = useTranslation();
  return useMemo(() => [
    // Core navigation — always visible in sidebar
    { icon: <FileText size={16} />, title: t("sidebar.files"), view: "files" as SidebarView },
    { icon: <Search size={16} />, title: `${t("sidebar.search")} (\u2318P)`, action: () => dispatch({ type: "TOGGLE_SEARCH" }) },
    { icon: <GitBranch size={16} />, title: t("sidebar.graph"), view: "graph" as SidebarView },
    { icon: <Calendar size={16} />, title: t("sidebar.calendar"), view: "calendar" as SidebarView },
    { icon: <Star size={16} />, title: t("sidebar.bookmarks"), view: "bookmarks" as SidebarView, divider: true },
    // Tools
    { icon: <Plug size={16} />, title: "Integrations", view: "integrations" as SidebarView },
    { icon: <BookOpen size={16} />, title: "Developer Hub", view: "devhub" as SidebarView, divider: true },
    // System
    { icon: <Settings size={16} />, title: t("sidebar.settings"), view: "settings" as SidebarView },
  ], [dispatch, t]);
}

export function Sidebar() {
  const { state, dispatch } = useApp();
  const { t } = useTranslation();
  const { notes, activeNoteId, sidebarView, sidebarCollapsed } = state;
  const NAV_ITEMS = useNavItems(dispatch);
  const [noteModalOpen, setNoteModalOpen] = useState(false);

  const handleCreateNote = useCallback(async (name: string) => {
    const filePath = `${name.replace(/\s+/g, "-").toLowerCase()}.md`;
    try {
      const note = await api.saveNote(filePath, name, `# ${name}\n\n`, {});
      dispatch({ type: "UPDATE_NOTE", note });
      dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
    } catch (err) {
      console.error("Failed to create note:", err);
    }
  }, [dispatch]);

  const handleDailyNote = useCallback(async () => {
    try {
      const note = await api.createDailyNote();
      dispatch({ type: "UPDATE_NOTE", note });
      dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
    } catch (err) {
      console.error("Failed to create daily note:", err);
    }
  }, [dispatch]);

  if (sidebarCollapsed) {
    return (
      <div className="sidebar collapsed">
        <div className="sidebar-header" style={{ justifyContent: "center" }}>
          <div className="logo" />
        </div>
        <div className="sidebar-nav" style={{ flexDirection: "column" }}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.view ?? item.title}
              className={`icon-btn ${item.view && sidebarView === item.view ? "active" : ""}`}
              onClick={() => item.view ? dispatch({ type: "SET_SIDEBAR_VIEW", view: item.view }) : item.action?.()}
              title={item.title}
            >
              {item.icon}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="logo" />
        <h2>Einstein</h2>
        <div className="sidebar-actions">
          <button className="icon-btn" onClick={() => setNoteModalOpen(true)} title={`${t("sidebar.newNote")} (\u2318N)`}>
            <Plus size={15} />
          </button>
          <button className="icon-btn" onClick={handleDailyNote} title={t("sidebar.dailyNote")}>
            <Calendar size={15} />
          </button>
        </div>
      </div>

      <div className="sidebar-nav">
        {NAV_ITEMS.map((item) => (
          <React.Fragment key={item.title}>
            {item.divider && <div className="nav-divider" />}
            <button
              className={`icon-btn ${item.view && sidebarView === item.view ? "active" : ""}`}
              onClick={() => item.view ? dispatch({ type: "SET_SIDEBAR_VIEW", view: item.view }) : item.action?.()}
              title={item.title}
            >
              {item.icon}
            </button>
          </React.Fragment>
        ))}
      </div>

      <div className="sidebar-content">
        {sidebarView === "files" && (
          <FileTree notes={notes} activeNoteId={activeNoteId} dispatch={dispatch} />
        )}
        {sidebarView === "backlinks" && activeNoteId && (
          <BacklinksPanel noteId={activeNoteId} dispatch={dispatch} />
        )}
        {sidebarView === "backlinks" && !activeNoteId && (
          <div className="empty-state">
            <p>Select a note to see backlinks</p>
          </div>
        )}
      </div>
      <NoteNameModal
        open={noteModalOpen}
        onClose={() => setNoteModalOpen(false)}
        onSubmit={handleCreateNote}
      />
    </div>
  );
}

const FileTree = React.memo(function FileTree({
  notes,
  activeNoteId,
  dispatch,
}: {
  notes: Note[];
  activeNoteId: string | null;
  dispatch: React.Dispatch<import("../lib/store").AppAction>;
}) {
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});

  const grouped = useMemo(() => {
    const groups: Record<string, Note[]> = {};
    for (const note of notes) {
      const parts = note.file_path.split("/");
      const folder = parts.length > 1 ? parts[0] : "";
      if (!groups[folder]) groups[folder] = [];
      groups[folder].push(note);
    }
    return groups;
  }, [notes]);

  const toggleFolder = useCallback((folder: string) => {
    setCollapsed((prev) => ({ ...prev, [folder]: !prev[folder] }));
  }, []);

  const sortedFolders = useMemo(
    () => Object.keys(grouped).sort((a, b) => a.localeCompare(b)),
    [grouped]
  );

  return (
    <>
      {sortedFolders.map((folder) => (
        <div key={folder}>
          {folder && (
            <div className="folder-item" onClick={() => toggleFolder(folder)}>
              <ChevronRight
                size={12}
                className={`chevron ${!collapsed[folder] ? "open" : ""}`}
              />
              <FolderClosed size={13} />
              <span>{folder}</span>
            </div>
          )}
          {!collapsed[folder] &&
            grouped[folder].map((note) => (
              <div
                key={note.id}
                className={`file-item ${note.id === activeNoteId ? "active" : ""}`}
                onClick={() => dispatch({ type: "SET_ACTIVE_NOTE", id: note.id })}
                style={folder ? { paddingLeft: 24 } : undefined}
              >
                <FileText size={14} className="file-icon" />
                <span className="file-name">{note.title}</span>
              </div>
            ))}
        </div>
      ))}
    </>
  );
});

function BacklinksPanel({
  noteId,
  dispatch,
}: {
  noteId: string;
  dispatch: React.Dispatch<import("../lib/store").AppAction>;
}) {
  const [backlinks, setBacklinks] = React.useState<Note[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    setLoading(true);
    api
      .getBacklinks(noteId)
      .then(setBacklinks)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [noteId]);

  if (loading) {
    return (
      <div className="empty-state">
        <div className="loading-spinner" />
      </div>
    );
  }

  if (backlinks.length === 0) {
    return (
      <div className="empty-state">
        <p>No backlinks found</p>
      </div>
    );
  }

  return (
    <>
      <div className="section-label">Backlinks ({backlinks.length})</div>
      {backlinks.map((note) => (
        <div
          key={note.id}
          className="backlink-item"
          onClick={() => dispatch({ type: "SET_ACTIVE_NOTE", id: note.id })}
        >
          <div className="backlink-title">{note.title}</div>
          <div className="backlink-context">
            {note.content.slice(0, 100)}
          </div>
        </div>
      ))}
    </>
  );
}
