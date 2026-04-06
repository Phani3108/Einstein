/**
 * ContextPanel.tsx — Content-aware right panel
 *
 * Replaces the static RightPanel. Shows different sections based on
 * what the user is currently looking at (contextMode).
 *
 * - Editor: backlinks, entities, linked projects/people, action items
 * - Project: related notes, action items, people, decisions
 * - Person: notes mentioning them, shared projects
 * - Home: quick actions, recent files, pinned items
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useApp } from "../lib/store";
import { api, type NoteAssociation, type AISuggestion } from "../lib/api";
import {
  FileText, Target, Users, Scale, CheckSquare, Link2,
  ChevronDown, ChevronRight, Plus, Eye, Calendar,
  Sparkles, X, Lightbulb, Loader,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Section component                                                  */
/* ------------------------------------------------------------------ */

function Section({
  title,
  icon,
  count,
  children,
  defaultOpen = true,
}: {
  title: string;
  icon: React.ReactNode;
  count?: number;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="cp-section">
      <button className="cp-section-header" onClick={() => setOpen(!open)}>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        {icon}
        <span className="cp-section-title">{title}</span>
        {count !== undefined && <span className="cp-section-count">{count}</span>}
      </button>
      {open && <div className="cp-section-body">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Editor Context                                                     */
/* ------------------------------------------------------------------ */

function EditorContext({ noteId }: { noteId: string }) {
  const { state, dispatch } = useApp();
  const [associations, setAssociations] = useState<NoteAssociation[]>([]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [suggestionsLoading, setSuggestionsLoading] = useState(false);

  useEffect(() => {
    api.getAssociationsForNote(noteId).then(setAssociations).catch(() => {});
  }, [noteId]);

  // Load AI suggestions (debounced — only on note change)
  useEffect(() => {
    const timeout = setTimeout(async () => {
      setSuggestionsLoading(true);
      try {
        const note = state.notes.find((n) => n.id === noteId);
        const recentNotes = state.notes
          .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
          .slice(0, 10)
          .map((n) => ({ id: n.id, title: n.title, content: n.content.slice(0, 200), updated_at: n.updated_at }));
        const result = await api.getSuggestions(
          noteId,
          note?.title ?? null,
          null,
          recentNotes,
          state.actionItems.filter((a) => a.status === "pending").map((a) => ({ task: a.task, deadline: a.deadline, status: a.status })),
          state.people.map((p) => ({ name: p.name, role: p.role, last_contact: p.last_contact })),
          state.projects.map((p) => ({ title: p.title, status: p.status, updated_at: p.updated_at })),
        );
        setSuggestions(result);
      } catch {
        setSuggestions([]);
      }
      setSuggestionsLoading(false);
    }, 2000); // 2 second delay to avoid spamming

    return () => clearTimeout(timeout);
  }, [noteId]); // Only re-run when note changes, not on every state update

  const note = state.notes.find((n) => n.id === noteId);
  const backlinks = useMemo(
    () => state.notes.filter((n) =>
      n.content.includes(`[[${note?.title}]]`) ||
      n.outgoing_links.includes(noteId)
    ),
    [state.notes, note, noteId]
  );

  const linkedProjects = useMemo(() => {
    const projectIds = associations
      .filter((a) => a.object_type === "project")
      .map((a) => a.object_id);
    return state.projects.filter((p) => projectIds.includes(p.id));
  }, [associations, state.projects]);

  const linkedPeople = useMemo(() => {
    const personIds = associations
      .filter((a) => a.object_type === "person")
      .map((a) => a.object_id);
    return state.people.filter((p) => personIds.includes(p.id));
  }, [associations, state.people]);

  const linkedDecisions = useMemo(() => {
    const decisionIds = associations
      .filter((a) => a.object_type === "decision")
      .map((a) => a.object_id);
    return state.decisions.filter((d) => decisionIds.includes(d.id));
  }, [associations, state.decisions]);

  const noteActions = useMemo(
    () => state.actionItems.filter((a) => a.note_id === noteId),
    [state.actionItems, noteId]
  );

  return (
    <>
      <Section title="Backlinks" icon={<Link2 size={14} />} count={backlinks.length}>
        {backlinks.length === 0 && <p className="cp-empty">No backlinks</p>}
        {backlinks.map((n) => (
          <button
            key={n.id}
            className="cp-link-item"
            onClick={() => {
              dispatch({ type: "SET_ACTIVE_NOTE", id: n.id });
            }}
          >
            <FileText size={12} />
            <span>{n.title}</span>
          </button>
        ))}
      </Section>

      <Section title="Projects" icon={<Target size={14} />} count={linkedProjects.length}>
        {linkedProjects.length === 0 && <p className="cp-empty">Not linked to any project</p>}
        {linkedProjects.map((p) => (
          <button
            key={p.id}
            className="cp-link-item"
            onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId: p.id } })}
          >
            <Target size={12} />
            <span>{p.title}</span>
            <span className="cp-link-meta">{p.status}</span>
          </button>
        ))}
        <button
          className="cp-add-btn"
          onClick={async () => {
            // Quick link: let user pick from existing projects
            // For now, create association to first unlinked project
            const unlinked = state.projects.filter(
              (p) => !linkedProjects.some((lp) => lp.id === p.id) && p.status === "active"
            );
            if (unlinked.length > 0) {
              await api.createAssociation(noteId, "project", unlinked[0].id, "mentions", 1.0);
              setAssociations(await api.getAssociationsForNote(noteId));
            }
          }}
        >
          <Plus size={12} /> Link Project
        </button>
      </Section>

      <Section title="People" icon={<Users size={14} />} count={linkedPeople.length}>
        {linkedPeople.length === 0 && <p className="cp-empty">No people linked</p>}
        {linkedPeople.map((p) => (
          <button
            key={p.id}
            className="cp-link-item"
            onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "person", personId: p.id } })}
          >
            <Users size={12} />
            <span>{p.name}</span>
            <span className="cp-link-meta">{p.role}</span>
          </button>
        ))}
      </Section>

      <Section title="Decisions" icon={<Scale size={14} />} count={linkedDecisions.length}>
        {linkedDecisions.length === 0 && <p className="cp-empty">No decisions linked</p>}
        {linkedDecisions.map((d) => (
          <button
            key={d.id}
            className="cp-link-item"
            onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "decision", decisionId: d.id } })}
          >
            <Scale size={12} />
            <span>{d.title}</span>
            <span className="cp-link-meta">{d.status}</span>
          </button>
        ))}
      </Section>

      <Section title="Action Items" icon={<CheckSquare size={14} />} count={noteActions.length}>
        {noteActions.length === 0 && <p className="cp-empty">No action items</p>}
        {noteActions.map((a) => (
          <div key={a.id} className="cp-action-item">
            <span className={`cp-action-status cp-action-${a.status}`} />
            <span className="cp-action-text">{a.task}</span>
            {a.deadline && <span className="cp-link-meta">{a.deadline.slice(0, 10)}</span>}
          </div>
        ))}
      </Section>

      <Section title="AI Suggestions" icon={<Lightbulb size={14} />} count={suggestions.length} defaultOpen={suggestions.length > 0}>
        {suggestionsLoading && (
          <div className="cp-suggestions-loading">
            <Loader size={12} className="cp-spin" />
            <span>Analyzing context...</span>
          </div>
        )}
        {!suggestionsLoading && suggestions.length === 0 && (
          <p className="cp-empty">No suggestions right now</p>
        )}
        {suggestions.map((s, i) => (
          <div key={i} className="cp-suggestion">
            <span className={`cp-suggestion-type cp-stype-${s.type}`}>{s.type.replace(/_/g, " ")}</span>
            <span className="cp-suggestion-title">{s.title}</span>
            <span className="cp-suggestion-desc">{s.description}</span>
          </div>
        ))}
      </Section>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Home Context                                                       */
/* ------------------------------------------------------------------ */

function HomeContext() {
  const { state, dispatch } = useApp();

  const recentNotes = useMemo(
    () => [...state.notes]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 10),
    [state.notes]
  );

  return (
    <>
      <Section title="Recent Notes" icon={<FileText size={14} />} count={recentNotes.length}>
        {recentNotes.map((n) => (
          <button
            key={n.id}
            className="cp-link-item"
            onClick={() => {
              dispatch({ type: "SET_ACTIVE_NOTE", id: n.id });
              dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
            }}
          >
            <FileText size={12} />
            <span>{n.title}</span>
          </button>
        ))}
      </Section>

      <Section title="Quick Actions" icon={<Sparkles size={14} />}>
        <button
          className="cp-quick-action"
          onClick={() => window.dispatchEvent(new CustomEvent("einstein-create-note"))}
        >
          <Plus size={12} /> New Note
        </button>
        <button
          className="cp-quick-action"
          onClick={() => window.dispatchEvent(new CustomEvent("einstein-create-project"))}
        >
          <Target size={12} /> New Project
        </button>
        <button
          className="cp-quick-action"
          onClick={() => dispatch({ type: "SET_SIDEBAR_VIEW", view: "rag" })}
        >
          <Sparkles size={12} /> Ask Notes
        </button>
      </Section>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Main ContextPanel                                                  */
/* ------------------------------------------------------------------ */

export function ContextPanel() {
  const { state } = useApp();

  const renderContent = () => {
    const mode = state.contextMode;
    switch (mode.type) {
      case "editor":
        return <EditorContext noteId={mode.noteId} />;
      case "home":
        return <HomeContext />;
      case "project":
      case "person":
      case "decision":
        // These views have their own detail panels — show minimal context
        return <HomeContext />;
      default:
        return <HomeContext />;
    }
  };

  return (
    <div className="cp-container">
      <div className="cp-header">
        <Eye size={14} />
        <span>Context</span>
      </div>
      <div className="cp-content">
        {renderContent()}
      </div>

      <style>{`
        .cp-container {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: var(--bg-primary, #1e1e2e);
          border-left: 1px solid var(--border, #27272a);
          width: 280px;
          overflow: hidden;
        }
        .cp-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 14px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .cp-content {
          flex: 1;
          overflow-y: auto;
          padding: 4px 0;
        }

        .cp-section {
          border-bottom: 1px solid var(--border, #27272a);
        }
        .cp-section-header {
          display: flex;
          align-items: center;
          gap: 6px;
          width: 100%;
          padding: 10px 14px;
          border: none;
          background: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          text-align: left;
        }
        .cp-section-header:hover {
          background: var(--bg-secondary, #27272a);
        }
        .cp-section-header svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .cp-section-title { flex: 1; }
        .cp-section-count {
          padding: 1px 6px;
          border-radius: 8px;
          background: var(--bg-secondary, #27272a);
          font-size: 10px;
          color: var(--text-muted, #71717a);
        }
        .cp-section-body {
          padding: 0 14px 10px;
        }

        .cp-empty {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          margin: 4px 0;
        }

        .cp-link-item {
          display: flex;
          align-items: center;
          gap: 6px;
          width: 100%;
          padding: 5px 4px;
          border: none;
          background: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 12px;
          cursor: pointer;
          text-align: left;
          border-radius: 4px;
          transition: background 0.1s;
        }
        .cp-link-item:hover {
          background: var(--bg-secondary, #27272a);
        }
        .cp-link-item svg { color: var(--text-muted, #71717a); flex-shrink: 0; }
        .cp-link-item span:nth-child(2) {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .cp-link-meta {
          font-size: 10px;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        .cp-add-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          padding: 4px 6px;
          border: 1px dashed var(--border, #27272a);
          border-radius: 4px;
          background: none;
          color: var(--text-muted, #71717a);
          font-size: 11px;
          cursor: pointer;
          margin-top: 6px;
          width: 100%;
          transition: all 0.15s;
        }
        .cp-add-btn:hover {
          color: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
        }

        .cp-action-item {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 4px 0;
          font-size: 12px;
        }
        .cp-action-status {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .cp-action-pending { background: #f59e0b; }
        .cp-action-completed { background: #10b981; }
        .cp-action-cancelled { background: #71717a; }
        .cp-action-text {
          flex: 1;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .cp-quick-action {
          display: flex;
          align-items: center;
          gap: 6px;
          width: 100%;
          padding: 6px 4px;
          border: none;
          background: none;
          color: var(--text-muted, #71717a);
          font-size: 12px;
          cursor: pointer;
          border-radius: 4px;
        }
        .cp-quick-action:hover {
          background: var(--bg-secondary, #27272a);
          color: var(--text-primary, #e4e4e7);
        }

        .cp-suggestions-loading {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: var(--text-muted, #71717a);
          padding: 4px 0;
        }
        @keyframes cp-spin-anim {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .cp-spin { animation: cp-spin-anim 1s linear infinite; }

        .cp-suggestion {
          display: flex;
          flex-direction: column;
          gap: 3px;
          padding: 6px 4px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 12px;
        }
        .cp-suggestion:last-child { border-bottom: none; }
        .cp-suggestion-type {
          display: inline-block;
          padding: 1px 5px;
          border-radius: 3px;
          font-size: 9px;
          font-weight: 600;
          text-transform: uppercase;
          width: fit-content;
        }
        .cp-stype-related_note { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
        .cp-stype-overdue_action { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .cp-stype-stale_project { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .cp-stype-person_followup { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
        .cp-stype-pattern { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .cp-stype-decision_needed { background: rgba(236, 72, 153, 0.15); color: #ec4899; }
        .cp-suggestion-title {
          color: var(--text-primary, #e4e4e7);
          font-weight: 500;
        }
        .cp-suggestion-desc {
          color: var(--text-muted, #71717a);
          font-size: 11px;
          line-height: 1.4;
        }
      `}</style>
    </div>
  );
}
