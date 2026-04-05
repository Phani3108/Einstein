/**
 * CommandPalette.tsx — Universal Cmd+K search & actions
 *
 * Replaces the old SearchModal with a richer palette that searches across
 * notes, projects, people, decisions + provides quick actions.
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import {
  Search,
  FileText,
  Target,
  Users,
  Scale,
  Plus,
  ArrowRight,
  Brain,
  Calendar,
  CheckSquare,
  Zap,
  Command,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface PaletteItem {
  id: string;
  type: "note" | "project" | "person" | "decision" | "action";
  title: string;
  subtitle?: string;
  icon: React.ReactNode;
  onSelect: () => void;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { state, dispatch } = useApp();
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQuery("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Close on Escape
  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open, onClose]);

  const navigate = useCallback(
    (mode: Parameters<typeof dispatch>[0]) => {
      dispatch(mode);
      onClose();
    },
    [dispatch, onClose]
  );

  // Quick actions (always shown when query is empty)
  const quickActions: PaletteItem[] = useMemo(
    () => [
      {
        id: "action-new-note",
        type: "action" as const,
        title: "New Note",
        subtitle: "Create a blank note",
        icon: <Plus size={16} />,
        onSelect: () => {
          // Dispatch will be handled by App.tsx
          dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
          onClose();
          // Trigger new note via custom event
          window.dispatchEvent(new CustomEvent("einstein-create-note"));
        },
      },
      {
        id: "action-new-project",
        type: "action" as const,
        title: "New Project",
        subtitle: "Create a new project",
        icon: <Target size={16} />,
        onSelect: () => {
          navigate({ type: "SET_CONTEXT_MODE", mode: { type: "home" } });
          setTimeout(() => window.dispatchEvent(new CustomEvent("einstein-create-project")), 100);
        },
      },
      {
        id: "action-ask-notes",
        type: "action" as const,
        title: "Ask Notes (RAG)",
        subtitle: "Ask questions about your knowledge base",
        icon: <Brain size={16} />,
        onSelect: () => {
          dispatch({ type: "SET_SIDEBAR_VIEW", view: "rag" });
          onClose();
        },
      },
      {
        id: "action-daily-note",
        type: "action" as const,
        title: "Today's Daily Note",
        subtitle: "Open or create today's journal",
        icon: <Calendar size={16} />,
        onSelect: async () => {
          try {
            const note = await api.createDailyNote();
            dispatch({ type: "UPDATE_NOTE", note });
            dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
            dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
          } catch (e) {
            console.error("Failed to create daily note:", e);
          }
          onClose();
        },
      },
      {
        id: "action-import",
        type: "action" as const,
        title: "Import Meeting",
        subtitle: "Import a meeting transcript",
        icon: <ArrowRight size={16} />,
        onSelect: () => {
          dispatch({ type: "SET_SIDEBAR_VIEW", view: "meetings" });
          onClose();
        },
      },
    ],
    [dispatch, onClose, navigate]
  );

  // Build search results
  const results: PaletteItem[] = useMemo(() => {
    if (!query.trim()) return quickActions;

    const q = query.toLowerCase();
    const items: PaletteItem[] = [];

    // Search notes
    state.notes
      .filter(
        (n) =>
          n.title.toLowerCase().includes(q) ||
          n.content.toLowerCase().includes(q)
      )
      .slice(0, 8)
      .forEach((n) => {
        items.push({
          id: `note-${n.id}`,
          type: "note",
          title: n.title,
          subtitle: n.file_path,
          icon: <FileText size={16} />,
          onSelect: () => {
            dispatch({ type: "SET_ACTIVE_NOTE", id: n.id });
            dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
            onClose();
          },
        });
      });

    // Search projects
    state.projects
      .filter(
        (p) =>
          p.title.toLowerCase().includes(q) ||
          p.description.toLowerCase().includes(q) ||
          p.category.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .forEach((p) => {
        items.push({
          id: `project-${p.id}`,
          type: "project",
          title: p.title,
          subtitle: `${p.status} ${p.category ? `· ${p.category}` : ""}`,
          icon: <Target size={16} />,
          onSelect: () => {
            navigate({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId: p.id } });
          },
        });
      });

    // Search people
    state.people
      .filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          p.role.toLowerCase().includes(q) ||
          p.organization.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .forEach((p) => {
        items.push({
          id: `person-${p.id}`,
          type: "person",
          title: p.name,
          subtitle: [p.role, p.organization].filter(Boolean).join(" · "),
          icon: <Users size={16} />,
          onSelect: () => {
            navigate({ type: "SET_CONTEXT_MODE", mode: { type: "person", personId: p.id } });
          },
        });
      });

    // Search decisions
    state.decisions
      .filter(
        (d) =>
          d.title.toLowerCase().includes(q) ||
          d.description.toLowerCase().includes(q)
      )
      .slice(0, 5)
      .forEach((d) => {
        items.push({
          id: `decision-${d.id}`,
          type: "decision",
          title: d.title,
          subtitle: `${d.status} · ${d.decided_at.slice(0, 10)}`,
          icon: <Scale size={16} />,
          onSelect: () => {
            navigate({ type: "SET_CONTEXT_MODE", mode: { type: "decision", decisionId: d.id } });
          },
        });
      });

    // Search action items
    state.actionItems
      .filter((a) => a.task.toLowerCase().includes(q))
      .slice(0, 3)
      .forEach((a) => {
        items.push({
          id: `action-${a.id}`,
          type: "action",
          title: a.task,
          subtitle: `${a.status} · ${a.priority}`,
          icon: <CheckSquare size={16} />,
          onSelect: () => {
            dispatch({ type: "SET_SIDEBAR_VIEW", view: "actions" });
            onClose();
          },
        });
      });

    // Add quick actions that match
    quickActions
      .filter((a) => a.title.toLowerCase().includes(q))
      .forEach((a) => items.push(a));

    return items;
  }, [query, state.notes, state.projects, state.people, state.decisions, state.actionItems, quickActions, dispatch, onClose, navigate]);

  const [selectedIndex, setSelectedIndex] = useState(0);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, results.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter" && results[selectedIndex]) {
        e.preventDefault();
        results[selectedIndex].onSelect();
      }
    },
    [results, selectedIndex]
  );

  if (!open) return null;

  return (
    <div className="cmd-overlay" onClick={onClose}>
      <div className="cmd-palette" onClick={(e) => e.stopPropagation()}>
        <div className="cmd-input-row">
          <Search size={18} className="cmd-search-icon" />
          <input
            ref={inputRef}
            className="cmd-input"
            placeholder="Search notes, projects, people, or type a command..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <kbd className="cmd-kbd">ESC</kbd>
        </div>

        <div className="cmd-results">
          {!query.trim() && (
            <div className="cmd-section-label">Quick Actions</div>
          )}
          {results.length === 0 && (
            <div className="cmd-empty">No results found</div>
          )}
          {results.map((item, i) => (
            <button
              key={item.id}
              className={`cmd-item ${i === selectedIndex ? "cmd-item-selected" : ""}`}
              onClick={item.onSelect}
              onMouseEnter={() => setSelectedIndex(i)}
            >
              <span className="cmd-item-icon">{item.icon}</span>
              <div className="cmd-item-text">
                <span className="cmd-item-title">{item.title}</span>
                {item.subtitle && (
                  <span className="cmd-item-subtitle">{item.subtitle}</span>
                )}
              </div>
              <span className="cmd-item-type">{item.type}</span>
            </button>
          ))}
        </div>

        <div className="cmd-footer">
          <span><Command size={12} /> K to open</span>
          <span><ArrowRight size={12} /> to select</span>
          <span><Zap size={12} /> to navigate</span>
        </div>
      </div>

      <style>{`
        .cmd-overlay {
          position: fixed;
          inset: 0;
          z-index: 9999;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: flex-start;
          justify-content: center;
          padding-top: 15vh;
          backdrop-filter: blur(4px);
        }
        .cmd-palette {
          width: 600px;
          max-height: 480px;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          animation: cmd-fadein 0.15s ease;
        }
        @keyframes cmd-fadein {
          from { opacity: 0; transform: translateY(-8px) scale(0.98); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        .cmd-input-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 16px;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .cmd-search-icon {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .cmd-input {
          flex: 1;
          background: none;
          border: none;
          outline: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 15px;
          font-family: inherit;
        }
        .cmd-input::placeholder {
          color: var(--text-muted, #71717a);
        }
        .cmd-kbd {
          padding: 2px 6px;
          border: 1px solid var(--border, #27272a);
          border-radius: 4px;
          font-size: 11px;
          color: var(--text-muted, #71717a);
          font-family: monospace;
        }
        .cmd-results {
          flex: 1;
          overflow-y: auto;
          padding: 6px;
        }
        .cmd-section-label {
          padding: 6px 10px 4px;
          font-size: 11px;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .cmd-empty {
          padding: 24px;
          text-align: center;
          color: var(--text-muted, #71717a);
          font-size: 14px;
        }
        .cmd-item {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 10px 12px;
          border: none;
          border-radius: 8px;
          background: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 14px;
          cursor: pointer;
          text-align: left;
          transition: background 0.1s;
        }
        .cmd-item:hover,
        .cmd-item-selected {
          background: var(--bg-secondary, #27272a);
        }
        .cmd-item-icon {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
          display: flex;
        }
        .cmd-item-text {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .cmd-item-title {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .cmd-item-subtitle {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .cmd-item-type {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          background: var(--bg-tertiary, #1a1a2e);
          padding: 2px 6px;
          border-radius: 4px;
          flex-shrink: 0;
          text-transform: capitalize;
        }
        .cmd-footer {
          display: flex;
          gap: 16px;
          padding: 8px 16px;
          border-top: 1px solid var(--border, #27272a);
          font-size: 11px;
          color: var(--text-muted, #71717a);
        }
        .cmd-footer span {
          display: flex;
          align-items: center;
          gap: 4px;
        }
      `}</style>
    </div>
  );
}
