import { useState, useCallback, useEffect, useMemo } from "react";
import { useApp } from "../lib/store";
import type { DecisionState } from "../lib/store";
import { api } from "../lib/api";
import {
  Scale,
  Clock,
  AlertTriangle,
  FileText,
  Edit2,
  Trash2,
  Save,
  X,
  RotateCcw,
} from "lucide-react";

interface RelatedNote {
  id: string;
  note_id: string;
  relationship: string;
  created_at: string;
}

const STATUS_COLORS: Record<DecisionState["status"], string> = {
  active: "#22c55e",
  revisit: "#f59e0b",
  reversed: "#ef4444",
  superseded: "#71717a",
};

const STATUS_LABELS: Record<DecisionState["status"], string> = {
  active: "Active",
  revisit: "Revisit",
  reversed: "Reversed",
  superseded: "Superseded",
};

export function DecisionDetail({ decisionId }: { decisionId: string }) {
  const { state, dispatch } = useApp();
  const decision = state.decisions.find((d) => d.id === decisionId);

  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [alternatives, setAlternatives] = useState<string[]>([]);
  const [newAlt, setNewAlt] = useState("");
  const [revisitDate, setRevisitDate] = useState("");
  const [relatedNotes, setRelatedNotes] = useState<RelatedNote[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [saving, setSaving] = useState(false);

  // Sync local state from decision
  useEffect(() => {
    if (!decision) return;
    setTitle(decision.title);
    setDescription(decision.description);
    setReasoning(decision.reasoning);
    setRevisitDate(decision.revisit_date ?? "");
    try {
      const parsed = JSON.parse(decision.alternatives || "[]");
      setAlternatives(Array.isArray(parsed) ? parsed : []);
    } catch {
      setAlternatives(decision.alternatives ? [decision.alternatives] : []);
    }
  }, [decision]);

  // Load associations on mount
  useEffect(() => {
    api
      .getAssociationsForObject("decision", decisionId)
      .then((assocs) => {
        setRelatedNotes(
          assocs.map((a) => ({
            id: a.id,
            note_id: a.note_id,
            relationship: a.relationship,
            created_at: a.created_at,
          }))
        );
      })
      .catch(() => {});
  }, [decisionId]);

  // Dirty detection: compare drafts vs saved decision
  const dirty = useMemo(() => {
    if (!decision || !editing) return false;
    const savedAlts = (() => {
      try {
        const parsed = JSON.parse(decision.alternatives || "[]");
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return decision.alternatives ? [decision.alternatives] : [];
      }
    })();
    return (
      title !== decision.title ||
      description !== decision.description ||
      reasoning !== decision.reasoning ||
      revisitDate !== (decision.revisit_date ?? "") ||
      JSON.stringify(alternatives) !== JSON.stringify(savedAlts)
    );
  }, [decision, editing, title, description, reasoning, revisitDate, alternatives]);

  // Discard all changes
  const discardChanges = useCallback(() => {
    if (!decision) return;
    setTitle(decision.title);
    setDescription(decision.description);
    setReasoning(decision.reasoning);
    setRevisitDate(decision.revisit_date ?? "");
    try {
      setAlternatives(JSON.parse(decision.alternatives || "[]"));
    } catch {
      setAlternatives(decision.alternatives ? [decision.alternatives] : []);
    }
  }, [decision]);

  const resolveNoteTitle = useCallback(
    (noteId: string) => {
      const note = state.notes.find((n) => n.id === noteId);
      return note?.title ?? noteId;
    },
    [state.notes]
  );

  const handleSave = useCallback(async () => {
    if (!decision) return;
    setSaving(true);
    try {
      const altsJson = JSON.stringify(alternatives);
      await api.updateDecision(decisionId, {
        title,
        description,
        reasoning,
        alternatives: altsJson,
        revisitDate: revisitDate || undefined,
      });
      dispatch({
        type: "UPDATE_DECISION",
        id: decisionId,
        changes: {
          title,
          description,
          reasoning,
          alternatives: altsJson,
          revisit_date: revisitDate || null,
        },
      });
      setEditing(false);
    } catch (e) {
      console.error("Failed to save decision", e);
    } finally {
      setSaving(false);
    }
  }, [decision, decisionId, title, description, reasoning, alternatives, revisitDate, dispatch]);

  // Cmd+S / Ctrl+S keyboard shortcut
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        if (dirty) {
          e.preventDefault();
          handleSave();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [dirty, handleSave]);

  const handleStatusChange = useCallback(
    async (newStatus: DecisionState["status"]) => {
      try {
        await api.updateDecision(decisionId, { status: newStatus });
        dispatch({
          type: "UPDATE_DECISION",
          id: decisionId,
          changes: { status: newStatus },
        });
      } catch (e) {
        console.error("Failed to update status", e);
      }
    },
    [decisionId, dispatch]
  );

  const handleDelete = useCallback(async () => {
    try {
      await api.deleteDecision(decisionId);
    } catch {
      // backend may not have delete — continue with local removal
    }
    dispatch({ type: "DELETE_DECISION", id: decisionId });
    dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "home" } });
  }, [decisionId, dispatch]);

  const addAlternative = useCallback(() => {
    const trimmed = newAlt.trim();
    if (!trimmed) return;
    setAlternatives((prev) => [...prev, trimmed]);
    setNewAlt("");
  }, [newAlt]);

  const removeAlternative = useCallback((idx: number) => {
    setAlternatives((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  if (!decision) {
    return (
      <div className="dd-empty">
        <AlertTriangle size={24} />
        <span>Decision not found</span>
      </div>
    );
  }

  const decidedDate = decision.decided_at
    ? new Date(decision.decided_at).toLocaleDateString()
    : "—";

  return (
    <>
      <style>{`
        .dd-container {
          max-width: 720px;
          margin: 0 auto;
          padding: 24px 16px;
          color: var(--text-primary, #e4e4e7);
        }
        .dd-header {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          margin-bottom: 4px;
        }
        .dd-header-icon {
          color: var(--accent, #3b82f6);
          flex-shrink: 0;
          margin-top: 2px;
        }
        .dd-title-row {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }
        .dd-title {
          font-size: 1.4rem;
          font-weight: 600;
          margin: 0;
          flex: 1;
          min-width: 200px;
        }
        .dd-title-input {
          font-size: 1.4rem;
          font-weight: 600;
          background: var(--bg-secondary, #27272a);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          padding: 4px 8px;
          flex: 1;
          min-width: 200px;
        }
        .dd-badge {
          display: inline-block;
          padding: 2px 10px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          flex-shrink: 0;
        }
        .dd-meta {
          font-size: 0.82rem;
          color: var(--text-muted, #71717a);
          margin: 6px 0 20px 36px;
          display: flex;
          align-items: center;
          gap: 6px;
          flex-wrap: wrap;
        }
        .dd-meta-sep {
          margin: 0 4px;
        }
        .dd-section {
          background: var(--bg-secondary, #27272a);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          padding: 16px;
          margin-bottom: 12px;
        }
        .dd-section-label {
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 8px;
        }
        .dd-text {
          font-size: 0.92rem;
          line-height: 1.6;
          white-space: pre-wrap;
        }
        .dd-textarea {
          width: 100%;
          min-height: 80px;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          font-size: 0.92rem;
          line-height: 1.6;
          padding: 8px;
          resize: vertical;
          font-family: inherit;
        }
        .dd-alt-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .dd-alt-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 4px 0;
          font-size: 0.92rem;
        }
        .dd-alt-bullet {
          color: var(--text-muted, #71717a);
        }
        .dd-alt-remove {
          background: none;
          border: none;
          color: var(--text-muted, #71717a);
          cursor: pointer;
          padding: 2px;
          display: flex;
          align-items: center;
        }
        .dd-alt-remove:hover {
          color: #ef4444;
        }
        .dd-alt-add {
          display: flex;
          gap: 6px;
          margin-top: 8px;
        }
        .dd-alt-input {
          flex: 1;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          font-size: 0.85rem;
          padding: 4px 8px;
        }
        .dd-note-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .dd-note-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 0;
          font-size: 0.9rem;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .dd-note-item:last-child {
          border-bottom: none;
        }
        .dd-note-title {
          flex: 1;
          cursor: pointer;
          color: var(--accent, #3b82f6);
        }
        .dd-note-title:hover {
          text-decoration: underline;
        }
        .dd-note-date {
          font-size: 0.78rem;
          color: var(--text-muted, #71717a);
        }
        .dd-actions {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-top: 20px;
        }
        .dd-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 14px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-secondary, #27272a);
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          cursor: pointer;
          transition: background 0.15s;
        }
        .dd-btn:hover {
          background: var(--bg-primary, #1e1e2e);
        }
        .dd-btn-accent {
          background: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          color: #fff;
        }
        .dd-btn-accent:hover {
          opacity: 0.9;
          background: var(--accent, #3b82f6);
        }
        .dd-btn-danger {
          border-color: #ef4444;
          color: #ef4444;
        }
        .dd-btn-danger:hover {
          background: #ef444420;
        }
        .dd-date-input {
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          padding: 4px 8px;
        }
        .dd-confirm-row {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          font-size: 0.85rem;
          color: #ef4444;
        }
        .dd-empty {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 40px;
          justify-content: center;
          color: var(--text-muted, #71717a);
        }
        .dd-edit-toggle {
          background: none;
          border: none;
          color: var(--text-muted, #71717a);
          cursor: pointer;
          padding: 4px;
          display: flex;
          align-items: center;
        }
        .dd-edit-toggle:hover {
          color: var(--accent, #3b82f6);
        }

        @keyframes dd-slide-up {
          from { transform: translateY(100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }

        .dd-save-bar {
          position: sticky;
          bottom: 0;
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 10px;
          padding: 12px 24px;
          margin-top: 20px;
          background: var(--bg-secondary, #27272a);
          border-top: 1px solid var(--border, #27272a);
          border-radius: 8px 8px 0 0;
          animation: dd-slide-up 0.2s ease-out;
          z-index: 30;
        }

        .dd-save-bar-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 7px 18px;
          border-radius: 6px;
          border: none;
          background: var(--accent, #3b82f6);
          color: #fff;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.15s;
        }
        .dd-save-bar-btn:hover { opacity: 0.9; }
        .dd-save-bar-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        .dd-discard-bar-btn {
          padding: 7px 18px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          background: var(--bg-primary, #1e1e2e);
          color: var(--text-primary, #e4e4e7);
          font-size: 13px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s;
        }
        .dd-discard-bar-btn:hover { background: rgba(255, 255, 255, 0.06); }
        .dd-discard-bar-btn:disabled { opacity: 0.5; cursor: not-allowed; }
      `}</style>

      <div className="dd-container">
        {/* Header */}
        <div className="dd-header">
          <Scale size={22} className="dd-header-icon" />
          <div className="dd-title-row">
            {editing ? (
              <input
                className="dd-title-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Decision title"
              />
            ) : (
              <h2 className="dd-title">{decision.title}</h2>
            )}
            <span
              className="dd-badge"
              style={{
                background: STATUS_COLORS[decision.status] + "22",
                color: STATUS_COLORS[decision.status],
              }}
            >
              {STATUS_LABELS[decision.status]}
            </span>
          </div>
          <button
            className="dd-edit-toggle"
            onClick={() => {
              if (editing) {
                // cancel
                setTitle(decision.title);
                setDescription(decision.description);
                setReasoning(decision.reasoning);
                setRevisitDate(decision.revisit_date ?? "");
                try {
                  setAlternatives(JSON.parse(decision.alternatives || "[]"));
                } catch {
                  setAlternatives([]);
                }
                setEditing(false);
              } else {
                setEditing(true);
              }
            }}
            title={editing ? "Cancel editing" : "Edit"}
          >
            {editing ? <X size={16} /> : <Edit2 size={16} />}
          </button>
        </div>

        {/* Meta line */}
        <div className="dd-meta">
          <Clock size={13} />
          Decided: {decidedDate}
          {(decision.revisit_date || editing) && (
            <>
              <span className="dd-meta-sep">&middot;</span>
              Revisit:{" "}
              {editing ? (
                <input
                  type="date"
                  className="dd-date-input"
                  value={revisitDate}
                  onChange={(e) => setRevisitDate(e.target.value)}
                />
              ) : decision.revisit_date ? (
                new Date(decision.revisit_date).toLocaleDateString()
              ) : (
                "—"
              )}
            </>
          )}
        </div>

        {/* Description */}
        <div className="dd-section">
          <div className="dd-section-label">What was decided</div>
          {editing ? (
            <textarea
              className="dd-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the decision..."
            />
          ) : (
            <div className="dd-text">{decision.description || "—"}</div>
          )}
        </div>

        {/* Reasoning */}
        <div className="dd-section">
          <div className="dd-section-label">Why</div>
          {editing ? (
            <textarea
              className="dd-textarea"
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="Explain the reasoning..."
            />
          ) : (
            <div className="dd-text">{decision.reasoning || "—"}</div>
          )}
        </div>

        {/* Alternatives */}
        <div className="dd-section">
          <div className="dd-section-label">Alternatives Considered</div>
          {alternatives.length === 0 && !editing && (
            <div className="dd-text" style={{ color: "var(--text-muted, #71717a)" }}>
              None recorded
            </div>
          )}
          <ul className="dd-alt-list">
            {alternatives.map((alt, idx) => (
              <li key={idx} className="dd-alt-item">
                <span className="dd-alt-bullet">&bull;</span>
                <span style={{ flex: 1 }}>{alt}</span>
                {editing && (
                  <button
                    className="dd-alt-remove"
                    onClick={() => removeAlternative(idx)}
                    title="Remove"
                  >
                    <X size={14} />
                  </button>
                )}
              </li>
            ))}
          </ul>
          {editing && (
            <div className="dd-alt-add">
              <input
                className="dd-alt-input"
                value={newAlt}
                onChange={(e) => setNewAlt(e.target.value)}
                placeholder="Add alternative..."
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addAlternative();
                  }
                }}
              />
              <button className="dd-btn" onClick={addAlternative}>
                + Add
              </button>
            </div>
          )}
        </div>

        {/* Related Notes */}
        {relatedNotes.length > 0 && (
          <div className="dd-section">
            <div className="dd-section-label">
              Related Notes ({relatedNotes.length})
            </div>
            <ul className="dd-note-list">
              {relatedNotes.map((rn) => (
                <li key={rn.id} className="dd-note-item">
                  <FileText size={14} style={{ color: "var(--text-muted, #71717a)", flexShrink: 0 }} />
                  <span
                    className="dd-note-title"
                    onClick={() =>
                      dispatch({
                        type: "SET_CONTEXT_MODE",
                        mode: { type: "note", noteId: rn.note_id },
                      } as any)
                    }
                  >
                    {resolveNoteTitle(rn.note_id)}
                  </span>
                  <span className="dd-note-date">
                    {new Date(rn.created_at).toLocaleDateString()}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Save bar when editing and dirty */}
        {editing && dirty && (
          <div className="dd-save-bar">
            <button
              className="dd-save-bar-btn"
              onClick={handleSave}
              disabled={saving}
            >
              <Save size={14} />
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              className="dd-discard-bar-btn"
              onClick={() => { discardChanges(); setEditing(false); }}
              disabled={saving}
            >
              Discard
            </button>
          </div>
        )}

        {/* Cancel button when editing but not dirty */}
        {editing && !dirty && (
          <div className="dd-actions">
            <button
              className="dd-btn"
              onClick={() => { discardChanges(); setEditing(false); }}
            >
              <X size={14} />
              Cancel
            </button>
          </div>
        )}

        {/* Status controls + Delete */}
        {!editing && (
          <div className="dd-actions">
            {decision.status !== "revisit" && (
              <button
                className="dd-btn"
                onClick={() => handleStatusChange("revisit")}
              >
                <Clock size={14} />
                Mark for Revisit
              </button>
            )}
            {decision.status !== "reversed" && (
              <button
                className="dd-btn"
                onClick={() => handleStatusChange("reversed")}
              >
                <RotateCcw size={14} />
                Reverse
              </button>
            )}
            {decision.status !== "superseded" && (
              <button
                className="dd-btn"
                onClick={() => handleStatusChange("superseded")}
              >
                <AlertTriangle size={14} />
                Supersede
              </button>
            )}
            {decision.status !== "active" && (
              <button
                className="dd-btn"
                onClick={() => handleStatusChange("active")}
              >
                <Scale size={14} />
                Reactivate
              </button>
            )}

            <button
              className="dd-btn dd-btn-danger"
              onClick={() => setConfirmDelete(true)}
            >
              <Trash2 size={14} />
              Delete
            </button>

            {confirmDelete && (
              <div className="dd-confirm-row">
                <span>Delete this decision?</span>
                <button className="dd-btn dd-btn-danger" onClick={handleDelete}>
                  Yes, delete
                </button>
                <button className="dd-btn" onClick={() => setConfirmDelete(false)}>
                  Cancel
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
