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
  Sparkles, X, Lightbulb, Loader, AlertTriangle,
  Clock, FolderOpen, MessageSquare, Tag, BarChart3,
  Activity,
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

  const overdueCommitments = useMemo(
    () => state.commitments.filter(
      (c) => c.status === "overdue" || (c.due_date && new Date(c.due_date) < new Date())
    ),
    [state.commitments]
  );

  const briefing = state.morningBriefing;

  return (
    <>
      {briefing && (
        <Section title="Morning Briefing" icon={<Lightbulb size={14} />} defaultOpen={true}>
          {briefing.summary && (
            <p className="cp-briefing-summary">{briefing.summary}</p>
          )}
          {briefing.attention_items && briefing.attention_items.length > 0 && (
            <div className="cp-briefing-attention">
              {briefing.attention_items.map((item: any, i: number) => (
                <div key={i} className="cp-attention-item">
                  <AlertTriangle size={11} />
                  <span>{typeof item === "string" ? item : item.message ?? item.title ?? JSON.stringify(item)}</span>
                </div>
              ))}
            </div>
          )}
          {briefing.today_event_count > 0 && (
            <div className="cp-briefing-stat">
              <Calendar size={11} />
              <span>{briefing.today_event_count} event{briefing.today_event_count !== 1 ? "s" : ""} today</span>
            </div>
          )}
        </Section>
      )}

      {overdueCommitments.length > 0 && (
        <Section title="Overdue Commitments" icon={<AlertTriangle size={14} />} count={overdueCommitments.length} defaultOpen={true}>
          {overdueCommitments.map((c) => (
            <div key={c.id} className="cp-commitment-item cp-commitment-overdue">
              <Clock size={11} />
              <div className="cp-commitment-body">
                <span className="cp-commitment-text">{c.content}</span>
                <span className="cp-commitment-meta">
                  {c.person_name && <>{c.person_name}</>}
                  {c.due_date && <> &middot; {c.due_date.slice(0, 10)}</>}
                </span>
              </div>
            </div>
          ))}
        </Section>
      )}

      {state.dormantPeople.length > 0 && (
        <Section title="Dormant Contacts" icon={<Users size={14} />} count={state.dormantPeople.length} defaultOpen={false}>
          {state.dormantPeople.slice(0, 8).map((p) => (
            <button
              key={p.id}
              className="cp-link-item"
              onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "person", personId: p.id } })}
            >
              <Users size={12} />
              <span>{p.name}</span>
              <span className="cp-link-meta">
                {p.last_contact ? formatRelativeDate(p.last_contact) : "Never"}
              </span>
            </button>
          ))}
        </Section>
      )}

      {state.dormantProjects.length > 0 && (
        <Section title="Stale Projects" icon={<FolderOpen size={14} />} count={state.dormantProjects.length} defaultOpen={false}>
          {state.dormantProjects.slice(0, 8).map((p) => (
            <button
              key={p.id}
              className="cp-link-item"
              onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId: p.id } })}
            >
              <Target size={12} />
              <span>{p.title}</span>
              <span className="cp-link-meta">{formatRelativeDate(p.updated_at)}</span>
            </button>
          ))}
        </Section>
      )}

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
/*  Project Context                                                    */
/* ------------------------------------------------------------------ */

function ProjectContext({ projectId }: { projectId: string }) {
  const { state, dispatch } = useApp();

  const project = state.projects.find((p) => p.id === projectId);
  const projectTitle = project?.title ?? "";

  const relatedEvents = useMemo(
    () => projectTitle
      ? state.contextEvents.filter((e) =>
          e.content.toLowerCase().includes(projectTitle.toLowerCase())
        )
      : [],
    [state.contextEvents, projectTitle]
  );

  const relatedCommitments = useMemo(
    () => state.commitments.filter(
      (c) => c.content.toLowerCase().includes(projectTitle.toLowerCase()) ||
             (c.person_name && projectTitle.toLowerCase().includes(c.person_name.toLowerCase()))
    ),
    [state.commitments, projectTitle]
  );

  const linkedPeople = useMemo(() => {
    if (!projectTitle) return [];
    const titleLower = projectTitle.toLowerCase();
    // People mentioned in events related to this project
    const mentionedNames = new Set<string>();
    relatedEvents.forEach((e) => {
      e.people_mentioned?.forEach((name) => mentionedNames.add(name.toLowerCase()));
    });
    // Also check if any person's notes mention the project
    return state.people.filter(
      (p) =>
        mentionedNames.has(p.name.toLowerCase()) ||
        (p.notes && p.notes.toLowerCase().includes(titleLower))
    );
  }, [state.people, relatedEvents, projectTitle]);

  if (!project) {
    return (
      <Section title="Project" icon={<Target size={14} />}>
        <p className="cp-empty">Project not found</p>
      </Section>
    );
  }

  return (
    <>
      <div className="cp-context-label">
        <Target size={12} />
        <span>{project.title}</span>
        <span className={`cp-status-badge cp-status-${project.status}`}>{project.status}</span>
      </div>

      <Section title="Related Events" icon={<Activity size={14} />} count={relatedEvents.length} defaultOpen={true}>
        {relatedEvents.length === 0 && <p className="cp-empty">No related events</p>}
        {relatedEvents.slice(0, 10).map((e) => (
          <div key={e.id} className="cp-event-item">
            <MessageSquare size={11} />
            <div className="cp-event-body">
              <span className="cp-event-text">{e.content.slice(0, 120)}{e.content.length > 120 ? "..." : ""}</span>
              <span className="cp-event-meta">
                {e.source} &middot; {formatRelativeDate(e.timestamp)}
              </span>
            </div>
          </div>
        ))}
      </Section>

      <Section title="Linked People" icon={<Users size={14} />} count={linkedPeople.length} defaultOpen={true}>
        {linkedPeople.length === 0 && <p className="cp-empty">No linked people</p>}
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

      <Section title="Commitments" icon={<CheckSquare size={14} />} count={relatedCommitments.length} defaultOpen={true}>
        {relatedCommitments.length === 0 && <p className="cp-empty">No commitments</p>}
        {relatedCommitments.map((c) => (
          <div key={c.id} className={`cp-commitment-item ${c.status === "overdue" || (c.due_date && new Date(c.due_date) < new Date()) ? "cp-commitment-overdue" : ""}`}>
            <span className={`cp-action-status cp-action-${c.status === "overdue" ? "pending" : c.status === "done" ? "completed" : "pending"}`} />
            <div className="cp-commitment-body">
              <span className="cp-commitment-text">{c.content}</span>
              <span className="cp-commitment-meta">
                {c.person_name && <>{c.person_name}</>}
                {c.due_date && <> &middot; {c.due_date.slice(0, 10)}</>}
              </span>
            </div>
          </div>
        ))}
      </Section>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Person Context                                                     */
/* ------------------------------------------------------------------ */

interface DossierData {
  relationship_strength?: number;
  talking_points?: string[];
  open_commitments?: { content: string; due_date?: string; status?: string }[];
  shared_topics?: string[];
  interaction_count?: number;
  last_interaction?: string;
}

function PersonContext({ personId }: { personId: string }) {
  const { state, dispatch } = useApp();
  const [dossier, setDossier] = useState<DossierData | null>(null);
  const [loading, setLoading] = useState(true);

  const person = state.people.find((p) => p.id === personId);

  useEffect(() => {
    setLoading(true);
    setDossier(null);
    api.getPersonDossier(personId)
      .then((data) => setDossier(data ?? {}))
      .catch(() => setDossier({}))
      .finally(() => setLoading(false));
  }, [personId]);

  const personCommitments = useMemo(
    () => person
      ? state.commitments.filter(
          (c) => c.person_name?.toLowerCase() === person.name.toLowerCase()
        )
      : [],
    [state.commitments, person]
  );

  if (!person) {
    return (
      <Section title="Person" icon={<Users size={14} />}>
        <p className="cp-empty">Person not found</p>
      </Section>
    );
  }

  const strength = dossier?.relationship_strength ?? 0;
  const strengthPct = Math.min(Math.max(strength * 100, 0), 100);
  const strengthColor = strengthPct >= 70 ? "#10b981" : strengthPct >= 40 ? "#f59e0b" : "#ef4444";

  return (
    <>
      <div className="cp-context-label">
        <Users size={12} />
        <span>{person.name}</span>
        {person.role && <span className="cp-link-meta">{person.role}</span>}
      </div>

      {loading && (
        <div className="cp-suggestions-loading" style={{ padding: "10px 14px" }}>
          <Loader size={12} className="cp-spin" />
          <span>Loading dossier...</span>
        </div>
      )}

      {!loading && dossier && (
        <>
          <Section title="Relationship Strength" icon={<BarChart3 size={14} />} defaultOpen={true}>
            <div className="cp-strength-bar-container">
              <div className="cp-strength-bar">
                <div
                  className="cp-strength-fill"
                  style={{ width: `${strengthPct}%`, background: strengthColor }}
                />
              </div>
              <span className="cp-strength-label" style={{ color: strengthColor }}>
                {strengthPct.toFixed(0)}%
              </span>
            </div>
            {dossier.interaction_count !== undefined && (
              <p className="cp-empty">{dossier.interaction_count} interactions
                {dossier.last_interaction && <> &middot; Last: {formatRelativeDate(dossier.last_interaction)}</>}
              </p>
            )}
          </Section>

          {dossier.talking_points && dossier.talking_points.length > 0 && (
            <Section title="Talking Points" icon={<MessageSquare size={14} />} count={dossier.talking_points.length} defaultOpen={true}>
              {dossier.talking_points.map((tp, i) => (
                <div key={i} className="cp-talking-point">
                  <Lightbulb size={11} />
                  <span>{tp}</span>
                </div>
              ))}
            </Section>
          )}

          {dossier.shared_topics && dossier.shared_topics.length > 0 && (
            <Section title="Shared Topics" icon={<Tag size={14} />} count={dossier.shared_topics.length} defaultOpen={true}>
              <div className="cp-tags-container">
                {dossier.shared_topics.map((topic, i) => (
                  <span key={i} className="cp-tag">{topic}</span>
                ))}
              </div>
            </Section>
          )}
        </>
      )}

      <Section
        title="Open Commitments"
        icon={<CheckSquare size={14} />}
        count={(dossier?.open_commitments?.length ?? 0) + personCommitments.length}
        defaultOpen={true}
      >
        {(dossier?.open_commitments?.length ?? 0) === 0 && personCommitments.length === 0 && (
          <p className="cp-empty">No open commitments</p>
        )}
        {dossier?.open_commitments?.map((c, i) => (
          <div key={`dossier-${i}`} className={`cp-commitment-item ${c.status === "overdue" || (c.due_date && new Date(c.due_date) < new Date()) ? "cp-commitment-overdue" : ""}`}>
            <Clock size={11} />
            <div className="cp-commitment-body">
              <span className="cp-commitment-text">{c.content}</span>
              {c.due_date && <span className="cp-commitment-meta">{c.due_date.slice(0, 10)}</span>}
            </div>
          </div>
        ))}
        {personCommitments.map((c) => (
          <div key={c.id} className={`cp-commitment-item ${c.status === "overdue" || (c.due_date && new Date(c.due_date) < new Date()) ? "cp-commitment-overdue" : ""}`}>
            <Clock size={11} />
            <div className="cp-commitment-body">
              <span className="cp-commitment-text">{c.content}</span>
              {c.due_date && <span className="cp-commitment-meta">{c.due_date.slice(0, 10)}</span>}
            </div>
          </div>
        ))}
      </Section>
    </>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  return `${Math.floor(diffDays / 365)}y ago`;
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
        return <ProjectContext projectId={mode.projectId} />;
      case "person":
        return <PersonContext personId={mode.personId} />;
      case "decision":
        // Decision views still use home context for now
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

        /* Briefing */
        .cp-briefing-summary {
          font-size: 12px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.5;
          margin: 0 0 8px;
        }
        .cp-briefing-attention {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .cp-attention-item {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          font-size: 11px;
          color: #f59e0b;
          line-height: 1.4;
          padding: 3px 0;
        }
        .cp-attention-item svg {
          flex-shrink: 0;
          margin-top: 1px;
        }
        .cp-attention-item span {
          color: var(--text-primary, #e4e4e7);
        }
        .cp-briefing-stat {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 11px;
          color: var(--text-muted, #71717a);
          margin-top: 6px;
        }

        /* Commitments */
        .cp-commitment-item {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          padding: 5px 0;
          font-size: 12px;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .cp-commitment-item:last-child { border-bottom: none; }
        .cp-commitment-item svg {
          flex-shrink: 0;
          margin-top: 2px;
          color: var(--text-muted, #71717a);
        }
        .cp-commitment-overdue svg {
          color: #ef4444;
        }
        .cp-commitment-body {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .cp-commitment-text {
          color: var(--text-primary, #e4e4e7);
          font-size: 12px;
          line-height: 1.4;
          overflow: hidden;
          text-overflow: ellipsis;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
        }
        .cp-commitment-meta {
          font-size: 10px;
          color: var(--text-muted, #71717a);
        }

        /* Context label (project/person header) */
        .cp-context-label {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 10px 14px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .cp-context-label svg {
          color: var(--accent, #3b82f6);
          flex-shrink: 0;
        }
        .cp-context-label span:nth-child(2) {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        /* Status badge */
        .cp-status-badge {
          padding: 1px 6px;
          border-radius: 8px;
          font-size: 10px;
          font-weight: 600;
          text-transform: capitalize;
          flex-shrink: 0;
        }
        .cp-status-active { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .cp-status-paused { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .cp-status-completed { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
        .cp-status-archived { background: rgba(113, 113, 122, 0.15); color: #71717a; }

        /* Events */
        .cp-event-item {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          padding: 5px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .cp-event-item:last-child { border-bottom: none; }
        .cp-event-item svg {
          flex-shrink: 0;
          margin-top: 2px;
          color: var(--text-muted, #71717a);
        }
        .cp-event-body {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .cp-event-text {
          font-size: 12px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.4;
        }
        .cp-event-meta {
          font-size: 10px;
          color: var(--text-muted, #71717a);
        }

        /* Relationship strength bar */
        .cp-strength-bar-container {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .cp-strength-bar {
          flex: 1;
          height: 6px;
          background: var(--bg-secondary, #27272a);
          border-radius: 3px;
          overflow: hidden;
        }
        .cp-strength-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 0.3s ease;
        }
        .cp-strength-label {
          font-size: 11px;
          font-weight: 600;
          flex-shrink: 0;
        }

        /* Talking points */
        .cp-talking-point {
          display: flex;
          align-items: flex-start;
          gap: 6px;
          padding: 4px 0;
          font-size: 12px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.4;
        }
        .cp-talking-point svg {
          flex-shrink: 0;
          margin-top: 2px;
          color: #f59e0b;
        }

        /* Tags */
        .cp-tags-container {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
        }
        .cp-tag {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 10px;
          background: rgba(59, 130, 246, 0.12);
          color: #3b82f6;
          font-size: 11px;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
