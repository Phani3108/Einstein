import { useState, useCallback, useEffect } from "react";
import { useApp, type PersonState } from "../lib/store";
import { api, type NoteAssociation } from "../lib/api";
import {
  User,
  Mail,
  Building,
  Briefcase,
  FileText,
  Calendar,
  Edit2,
  Trash2,
  Save,
  X,
  TrendingUp,
  TrendingDown,
  Minus,
  MessageSquare,
  AlertCircle,
  Clock,
  Target,
  Loader,
} from "lucide-react";

interface RelatedNote {
  id: string;
  title: string;
  updated_at: string;
}

interface SharedProject {
  id: string;
  title: string;
  status: string;
}

interface PersonIntelligence {
  relationship_strength: number;
  recent_events: { date: string; source: string; content: string }[];
  shared_topics: string[];
  open_commitments: { description: string; due_date: string | null; status: string }[];
  interaction_timeline: { date: string; source: string; type: string; summary: string }[];
  suggested_talking_points: string[];
}

export function PersonDetail({ personId }: { personId: string }) {
  const { state, dispatch } = useApp();
  const person = state.people.find((p) => p.id === personId);

  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<Partial<PersonState>>({});
  const [associations, setAssociations] = useState<NoteAssociation[]>([]);
  const [relatedNotes, setRelatedNotes] = useState<RelatedNote[]>([]);
  const [sharedProjects, setSharedProjects] = useState<SharedProject[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [intelligence, setIntelligence] = useState<PersonIntelligence | null>(null);
  const [intelLoading, setIntelLoading] = useState(false);
  const [relScore, setRelScore] = useState<any>(null);

  // Load relationship health score
  useEffect(() => {
    if (personId) {
      api.getRelationshipScore(personId)
        .then(data => setRelScore(data))
        .catch(() => setRelScore(null));
    }
  }, [personId]);

  // Load person intelligence (dossier) from cloud API
  useEffect(() => {
    let cancelled = false;
    async function loadIntel() {
      setIntelLoading(true);
      try {
        const data = await api.getPersonDossier(personId);
        if (!cancelled) {
          setIntelligence({
            relationship_strength: data.relationship_strength ?? 0,
            recent_events: data.recent_events ?? [],
            shared_topics: data.shared_topics ?? [],
            open_commitments: data.open_commitments ?? [],
            interaction_timeline: data.interaction_timeline ?? [],
            suggested_talking_points: data.suggested_talking_points ?? [],
          });
        }
      } catch {
        // Cloud API not available — that's fine
      }
      if (!cancelled) setIntelLoading(false);
    }
    loadIntel();
    return () => { cancelled = true; };
  }, [personId]);

  // Load associations on mount / personId change
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const assocs = await api.getAssociationsForObject("person", personId);
        if (cancelled) return;
        setAssociations(assocs);

        // Resolve related notes
        const noteIds = [...new Set(assocs.map((a) => a.note_id))];
        const notes: RelatedNote[] = [];
        for (const nid of noteIds) {
          const n = state.notes.find((n) => n.id === nid);
          if (n) {
            notes.push({ id: n.id, title: n.title, updated_at: n.updated_at });
          }
        }
        if (!cancelled) setRelatedNotes(notes);

        // Resolve shared projects: find project associations for the same notes
        const projectIds = new Set<string>();
        for (const nid of noteIds) {
          try {
            const noteAssocs = await api.getAssociationsForNote(nid);
            for (const a of noteAssocs) {
              if (a.object_type === "project") {
                projectIds.add(a.object_id);
              }
            }
          } catch {
            // skip
          }
        }

        const projects: SharedProject[] = [];
        for (const pid of projectIds) {
          const proj = state.projects.find((p) => p.id === pid);
          if (proj) {
            projects.push({ id: proj.id, title: proj.title, status: proj.status });
          }
        }
        if (!cancelled) setSharedProjects(projects);
      } catch (err) {
        console.error("Failed to load person associations:", err);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [personId, state.notes, state.projects]);

  // Sync draft when entering edit mode
  const startEdit = useCallback(() => {
    if (!person) return;
    setDraft({
      name: person.name,
      role: person.role,
      organization: person.organization,
      email: person.email,
      notes: person.notes,
      last_contact: person.last_contact,
    });
    setEditing(true);
  }, [person]);

  const cancelEdit = useCallback(() => {
    if (!person) { setEditing(false); setDraft({}); return; }
    setDraft({
      name: person.name,
      role: person.role,
      organization: person.organization,
      email: person.email,
      notes: person.notes,
      last_contact: person.last_contact,
    });
    setEditing(false);
  }, [person]);

  const saveEdit = useCallback(async () => {
    if (!person) return;
    try {
      const changes: Record<string, string | undefined> = {};
      if (draft.name !== undefined && draft.name !== person.name) changes.name = draft.name;
      if (draft.role !== undefined && draft.role !== person.role) changes.role = draft.role;
      if (draft.organization !== undefined && draft.organization !== person.organization) changes.organization = draft.organization;
      if (draft.email !== undefined && draft.email !== person.email) changes.email = draft.email;
      if (draft.notes !== undefined && draft.notes !== person.notes) changes.notes = draft.notes;
      if (draft.last_contact !== undefined && draft.last_contact !== person.last_contact) changes.lastContact = draft.last_contact ?? undefined;

      if (Object.keys(changes).length > 0) {
        const updated = await api.updatePerson(personId, changes);
        dispatch({ type: "UPDATE_PERSON", id: personId, changes: updated });
      }
      setEditing(false);
    } catch (err) {
      console.error("Failed to update person:", err);
    }
  }, [person, draft, personId, dispatch]);

  // Cmd+S / Ctrl+S keyboard shortcut when editing
  useEffect(() => {
    if (!editing) return;
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        saveEdit();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [editing, saveEdit]);

  const handleDelete = useCallback(async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    try {
      await api.deletePerson(personId);
      dispatch({ type: "DELETE_PERSON", id: personId });
      dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "home" } });
    } catch (err) {
      console.error("Failed to delete person:", err);
    }
  }, [confirmDelete, personId, dispatch]);

  const navigateToNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "editor", noteId } });
    },
    [dispatch]
  );

  const navigateToProject = useCallback(
    (projectId: string) => {
      dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId } });
    },
    [dispatch]
  );

  if (!person) {
    return (
      <div className="prd-empty">
        <User size={48} />
        <p>Person not found</p>
      </div>
    );
  }

  const initials = person.name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  const formatDate = (d: string | null) => {
    if (!d) return "Never";
    try {
      return new Date(d).toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return d;
    }
  };

  return (
    <div className="prd-container">
      <style>{`
        .prd-container {
          max-width: 720px;
          margin: 0 auto;
          padding: 32px 24px;
          color: var(--text-primary, #e4e4e7);
          font-family: inherit;
        }

        .prd-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          padding: 80px 24px;
          color: var(--text-muted, #71717a);
        }

        .prd-header {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 24px;
        }

        .prd-avatar {
          width: 56px;
          height: 56px;
          border-radius: 50%;
          background: var(--accent, #3b82f6);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 20px;
          font-weight: 600;
          color: #fff;
          flex-shrink: 0;
        }

        .prd-header-info {
          flex: 1;
          min-width: 0;
        }

        .prd-name {
          font-size: 22px;
          font-weight: 600;
          margin: 0 0 4px;
          line-height: 1.3;
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .prd-health-badge {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
          font-weight: 600;
          padding: 3px 8px;
          border-radius: 12px;
          border: 1px solid;
          white-space: nowrap;
        }
        .prd-health-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .prd-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 12px;
          color: var(--text-muted, #71717a);
          font-size: 13px;
          line-height: 1.5;
        }

        .prd-meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .prd-actions {
          display: flex;
          gap: 6px;
          flex-shrink: 0;
        }

        .prd-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-secondary, #27272a);
          color: var(--text-primary, #e4e4e7);
          cursor: pointer;
          font-size: 13px;
          transition: opacity 0.15s;
        }

        .prd-btn:hover {
          opacity: 0.8;
        }

        .prd-btn--danger {
          border-color: #ef4444;
          color: #ef4444;
        }

        .prd-btn--danger:hover {
          background: #ef444420;
        }

        .prd-btn--primary {
          background: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          color: #fff;
        }

        .prd-section {
          background: var(--bg-secondary, #27272a);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 16px;
        }

        .prd-section-title {
          font-size: 13px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--text-muted, #71717a);
          margin: 0 0 12px;
          display: flex;
          align-items: center;
          gap: 6px;
        }

        .prd-notes-text {
          white-space: pre-wrap;
          font-size: 14px;
          line-height: 1.6;
          color: var(--text-primary, #e4e4e7);
          margin: 0;
        }

        .prd-notes-text--empty {
          color: var(--text-muted, #71717a);
          font-style: italic;
        }

        .prd-textarea {
          width: 100%;
          min-height: 100px;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          font-family: inherit;
          font-size: 14px;
          padding: 10px;
          resize: vertical;
          line-height: 1.6;
        }

        .prd-textarea:focus {
          outline: none;
          border-color: var(--accent, #3b82f6);
        }

        .prd-input {
          width: 100%;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          font-family: inherit;
          font-size: 14px;
          padding: 6px 10px;
        }

        .prd-input:focus {
          outline: none;
          border-color: var(--accent, #3b82f6);
        }

        .prd-input--name {
          font-size: 22px;
          font-weight: 600;
          padding: 4px 8px;
        }

        .prd-edit-fields {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .prd-edit-row {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .prd-edit-row label {
          font-size: 13px;
          color: var(--text-muted, #71717a);
          min-width: 90px;
          flex-shrink: 0;
        }

        .prd-list {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .prd-list-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 6px;
          cursor: pointer;
          transition: background 0.15s;
          font-size: 14px;
        }

        .prd-list-item:hover {
          background: var(--bg-primary, #1e1e2e);
        }

        .prd-list-item-title {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .prd-list-item-sub {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        .prd-badge {
          display: inline-block;
          padding: 2px 8px;
          border-radius: 10px;
          font-size: 11px;
          font-weight: 500;
          text-transform: capitalize;
          background: var(--accent, #3b82f6)22;
          color: var(--accent, #3b82f6);
        }

        .prd-empty-section {
          color: var(--text-muted, #71717a);
          font-size: 13px;
          font-style: italic;
        }

        .prd-confirm-bar {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: #ef4444;
        }

        /* ---- Person Intelligence (Phase 3) ---- */

        .prd-strength-bar {
          height: 8px;
          background: var(--bg-primary, #1e1e2e);
          border-radius: 4px;
          overflow: hidden;
          margin-bottom: 6px;
        }

        .prd-strength-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.4s var(--ease-out, ease-out);
        }

        .prd-strength-label {
          font-size: 13px;
          color: var(--text-muted, #71717a);
        }

        .prd-topics {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }

        .prd-topic-tag {
          display: inline-block;
          padding: 3px 10px;
          border-radius: 12px;
          font-size: 12px;
          font-weight: 500;
          background: var(--accent, #3b82f6)18;
          color: var(--accent, #3b82f6);
          border: 1px solid var(--accent, #3b82f6)30;
        }

        .prd-talking-points {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }

        .prd-talking-points li {
          position: relative;
          padding-left: 16px;
          font-size: 14px;
          line-height: 1.5;
          color: var(--text-primary, #e4e4e7);
        }

        .prd-talking-points li::before {
          content: "\\2022";
          position: absolute;
          left: 0;
          color: var(--accent, #3b82f6);
          font-weight: bold;
        }

        .prd-timeline {
          list-style: none;
          margin: 0;
          padding: 0;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .prd-timeline-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 0;
          border-bottom: 1px solid var(--border, #27272a)40;
          font-size: 13px;
        }

        .prd-timeline-item:last-child {
          border-bottom: none;
        }

        .prd-timeline-date {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          min-width: 80px;
          flex-shrink: 0;
        }

        .prd-timeline-badge {
          display: inline-block;
          padding: 1px 6px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 500;
          text-transform: lowercase;
          background: var(--bg-primary, #1e1e2e);
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        .prd-timeline-summary {
          flex: 1;
          min-width: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          color: var(--text-primary, #e4e4e7);
        }

        @keyframes prd-spin-anim {
          to { transform: rotate(360deg); }
        }

        .prd-spin {
          animation: prd-spin-anim 1s linear infinite;
        }

        .pd-rel-health {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-top: 8px;
        }
        .pd-rel-score-bar {
          width: 100px;
          height: 6px;
          background: var(--border, #27272a);
          border-radius: 3px;
          overflow: hidden;
        }
        .pd-rel-fill {
          height: 100%;
          border-radius: 3px;
          transition: width 0.3s;
        }
        .pd-rel-label {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          text-transform: capitalize;
        }
        .pd-rel-trend {
          font-size: 11px;
          font-weight: 600;
        }
        .pd-rel-declining {
          color: #ef4444;
        }
        .pd-rel-improving {
          color: #22c55e;
        }
      `}</style>

      {/* Header */}
      <div className="prd-header">
        <div className="prd-avatar">{initials || <User size={24} />}</div>

        <div className="prd-header-info">
          {editing ? (
            <input
              className="prd-input prd-input--name"
              value={draft.name ?? ""}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
              placeholder="Name"
            />
          ) : (
            <h2 className="prd-name">
              {person.name}
              {(() => {
                const risk = state.dormancyRisk?.find(
                  (r) => r.id === personId && r.type === "person"
                );
                if (!risk) return null;
                const color = risk.risk_level === "high" || risk.risk_level === "critical"
                  ? "#ef4444"
                  : risk.risk_level === "medium"
                    ? "#f59e0b"
                    : "#10b981";
                return (
                  <span
                    className="prd-health-badge"
                    style={{ background: `${color}22`, color, borderColor: `${color}44` }}
                    title={`${risk.days_until_dormant} days until dormant`}
                  >
                    <span className="prd-health-dot" style={{ background: color }} />
                    {risk.days_until_dormant}d
                  </span>
                );
              })()}
            </h2>
          )}

          {editing ? (
            <div className="prd-edit-fields" style={{ marginTop: 8 }}>
              <div className="prd-edit-row">
                <label><Briefcase size={14} /> Role</label>
                <input
                  className="prd-input"
                  value={draft.role ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, role: e.target.value }))}
                  placeholder="Role"
                />
              </div>
              <div className="prd-edit-row">
                <label><Building size={14} /> Org</label>
                <input
                  className="prd-input"
                  value={draft.organization ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, organization: e.target.value }))}
                  placeholder="Organization"
                />
              </div>
              <div className="prd-edit-row">
                <label><Mail size={14} /> Email</label>
                <input
                  className="prd-input"
                  value={draft.email ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, email: e.target.value }))}
                  placeholder="Email"
                  type="email"
                />
              </div>
              <div className="prd-edit-row">
                <label><Calendar size={14} /> Contact</label>
                <input
                  className="prd-input"
                  value={draft.last_contact ?? ""}
                  onChange={(e) => setDraft((d) => ({ ...d, last_contact: e.target.value || null }))}
                  placeholder="YYYY-MM-DD"
                  type="date"
                />
              </div>
            </div>
          ) : (
            <div className="prd-meta">
              {person.role && (
                <span className="prd-meta-item">
                  <Briefcase size={14} />
                  {person.role}
                </span>
              )}
              {person.organization && (
                <span className="prd-meta-item">
                  <Building size={14} />
                  {person.organization}
                </span>
              )}
              {person.email && (
                <span className="prd-meta-item">
                  <Mail size={14} />
                  {person.email}
                </span>
              )}
              <span className="prd-meta-item">
                <Calendar size={14} />
                Last contact: {formatDate(person.last_contact)}
              </span>
            </div>
          )}
          {!editing && relScore && (
            <div className="pd-rel-health">
              <div className="pd-rel-score-bar">
                <div className="pd-rel-fill" style={{ width: `${relScore.score}%`, background: relScore.score > 70 ? '#22c55e' : relScore.score > 40 ? '#f59e0b' : '#ef4444' }} />
              </div>
              <span className="pd-rel-label">{relScore.grade} ({relScore.score}/100)</span>
              {relScore.trend === "declining" && <span className="pd-rel-trend pd-rel-declining">↓ declining</span>}
              {relScore.trend === "improving" && <span className="pd-rel-trend pd-rel-improving">↑ improving</span>}
            </div>
          )}
        </div>

        <div className="prd-actions">
          {editing ? (
            <>
              <button className="prd-btn prd-btn--primary" onClick={saveEdit}>
                <Save size={14} /> Save
              </button>
              <button className="prd-btn" onClick={cancelEdit}>
                <X size={14} /> Cancel
              </button>
            </>
          ) : (
            <>
              <button className="prd-btn" onClick={startEdit}>
                <Edit2 size={14} /> Edit
              </button>
              {confirmDelete ? (
                <div className="prd-confirm-bar">
                  <span>Delete?</span>
                  <button className="prd-btn prd-btn--danger" onClick={handleDelete}>
                    Confirm
                  </button>
                  <button className="prd-btn" onClick={() => setConfirmDelete(false)}>
                    <X size={14} />
                  </button>
                </div>
              ) : (
                <button className="prd-btn prd-btn--danger" onClick={() => setConfirmDelete(true)}>
                  <Trash2 size={14} />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Notes about person */}
      <div className="prd-section">
        <h3 className="prd-section-title">
          <FileText size={14} /> Notes
        </h3>
        {editing ? (
          <textarea
            className="prd-textarea"
            value={draft.notes ?? ""}
            onChange={(e) => setDraft((d) => ({ ...d, notes: e.target.value }))}
            placeholder="Notes about this person..."
          />
        ) : person.notes ? (
          <p className="prd-notes-text">{person.notes}</p>
        ) : (
          <p className="prd-notes-text prd-notes-text--empty">No notes yet</p>
        )}
      </div>

      {/* Related Notes */}
      <div className="prd-section">
        <h3 className="prd-section-title">
          <FileText size={14} /> Related Notes ({relatedNotes.length})
        </h3>
        {relatedNotes.length > 0 ? (
          <ul className="prd-list">
            {relatedNotes.map((n) => (
              <li
                key={n.id}
                className="prd-list-item"
                onClick={() => navigateToNote(n.id)}
              >
                <FileText size={14} style={{ color: "var(--text-muted, #71717a)", flexShrink: 0 }} />
                <span className="prd-list-item-title">{n.title}</span>
                <span className="prd-list-item-sub">{formatDate(n.updated_at)}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="prd-empty-section">No related notes</p>
        )}
      </div>

      {/* Shared Projects */}
      <div className="prd-section">
        <h3 className="prd-section-title">
          <Briefcase size={14} /> Shared Projects ({sharedProjects.length})
        </h3>
        {sharedProjects.length > 0 ? (
          <ul className="prd-list">
            {sharedProjects.map((p) => (
              <li
                key={p.id}
                className="prd-list-item"
                onClick={() => navigateToProject(p.id)}
              >
                <Briefcase size={14} style={{ color: "var(--text-muted, #71717a)", flexShrink: 0 }} />
                <span className="prd-list-item-title">{p.title}</span>
                <span className="prd-badge">{p.status}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="prd-empty-section">No shared projects</p>
        )}
      </div>

      {/* ---- Person Intelligence (Phase 3) ---- */}

      {intelLoading && (
        <div className="prd-section" style={{ textAlign: "center", padding: 24 }}>
          <Loader size={18} className="prd-spin" style={{ color: "var(--text-muted)" }} />
          <span style={{ marginLeft: 8, color: "var(--text-muted)", fontSize: 13 }}>Loading intelligence...</span>
        </div>
      )}

      {intelligence && (
        <>
          {/* Relationship Strength */}
          <div className="prd-section">
            <h3 className="prd-section-title">
              <Target size={14} /> Relationship Strength
            </h3>
            <div className="prd-strength-bar">
              <div
                className="prd-strength-fill"
                style={{
                  width: `${Math.round(intelligence.relationship_strength * 100)}%`,
                  background: intelligence.relationship_strength > 0.6
                    ? "#10b981"
                    : intelligence.relationship_strength > 0.3
                    ? "#f59e0b"
                    : "#ef4444",
                }}
              />
            </div>
            <span className="prd-strength-label">
              {Math.round(intelligence.relationship_strength * 100)}% —{" "}
              {intelligence.relationship_strength > 0.6
                ? "Strong"
                : intelligence.relationship_strength > 0.3
                ? "Moderate"
                : "Fading"}
            </span>
          </div>

          {/* Shared Topics */}
          {intelligence.shared_topics.length > 0 && (
            <div className="prd-section">
              <h3 className="prd-section-title">
                <MessageSquare size={14} /> Shared Topics
              </h3>
              <div className="prd-topics">
                {intelligence.shared_topics.map((t) => (
                  <span key={t} className="prd-topic-tag">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Open Commitments */}
          {intelligence.open_commitments.length > 0 && (
            <div className="prd-section">
              <h3 className="prd-section-title">
                <AlertCircle size={14} /> Open Commitments ({intelligence.open_commitments.length})
              </h3>
              <ul className="prd-list">
                {intelligence.open_commitments.map((c, i) => (
                  <li key={i} className="prd-list-item">
                    <AlertCircle size={14} style={{ color: c.status === "overdue" ? "#ef4444" : "#f59e0b", flexShrink: 0 }} />
                    <span className="prd-list-item-title">{c.description}</span>
                    {c.due_date && (
                      <span className="prd-list-item-sub">{c.due_date}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Suggested Talking Points */}
          {intelligence.suggested_talking_points.length > 0 && (
            <div className="prd-section">
              <h3 className="prd-section-title">
                <TrendingUp size={14} /> Talking Points
              </h3>
              <ul className="prd-talking-points">
                {intelligence.suggested_talking_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Interaction Timeline */}
          {intelligence.interaction_timeline.length > 0 && (
            <div className="prd-section">
              <h3 className="prd-section-title">
                <Clock size={14} /> Interaction Timeline
              </h3>
              <ul className="prd-timeline">
                {intelligence.interaction_timeline.map((item, i) => (
                  <li key={i} className="prd-timeline-item">
                    <span className="prd-timeline-date">{item.date}</span>
                    <span className="prd-timeline-badge">{item.source}</span>
                    <span className="prd-timeline-summary">{item.summary}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </div>
  );
}
