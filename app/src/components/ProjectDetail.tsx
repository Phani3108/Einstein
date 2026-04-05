import { useState, useCallback, useEffect, useMemo } from "react";
import { useApp } from "../lib/store";
import type { ProjectState, ActionItemState, NoteAssociationState } from "../lib/store";
import { api } from "../lib/api";
import type { NoteAssociation } from "../lib/api";
import {
  ArrowLeft,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  Edit3,
  FileText,
  Folder,
  MoreVertical,
  Trash2,
  User,
  ListTodo,
  Users,
  ChevronDown,
} from "lucide-react";

type Tab = "notes" | "actions" | "people";

const STATUS_COLORS: Record<string, string> = {
  active: "#22c55e",
  paused: "#eab308",
  completed: "#3b82f6",
  archived: "#71717a",
};

export function ProjectDetail({ projectId }: { projectId: string }) {
  const { state, dispatch } = useApp();
  const project = state.projects.find((p) => p.id === projectId);

  const [tab, setTab] = useState<Tab>("notes");
  const [associations, setAssociations] = useState<NoteAssociation[]>([]);
  const [editingTitle, setEditingTitle] = useState(false);
  const [editingGoal, setEditingGoal] = useState(false);
  const [editingDesc, setEditingDesc] = useState(false);
  const [editingDeadline, setEditingDeadline] = useState(false);
  const [titleDraft, setTitleDraft] = useState("");
  const [goalDraft, setGoalDraft] = useState("");
  const [descDraft, setDescDraft] = useState("");
  const [deadlineDraft, setDeadlineDraft] = useState("");
  const [statusOpen, setStatusOpen] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Load associations on mount
  useEffect(() => {
    api
      .getAssociationsForObject("project", projectId)
      .then(setAssociations)
      .catch(() => setAssociations([]));
  }, [projectId]);

  // Derived: related notes
  const relatedNotes = useMemo(() => {
    const noteIds = associations
      .filter((a) => a.object_type === "project")
      .map((a) => a.note_id);
    return state.notes.filter((n) => noteIds.includes(n.id));
  }, [associations, state.notes]);

  // Derived: related people
  const relatedPeople = useMemo(() => {
    // Find person associations that share notes with this project
    const noteIds = new Set(associations.map((a) => a.note_id));
    // Also check direct person-project links through shared notes
    return state.people.filter((person) => {
      return associations.some(
        (a) => a.object_type === "project" && a.object_id === projectId
      ) || state.notes.some((n) => {
        if (!noteIds.has(n.id)) return false;
        return n.content.toLowerCase().includes(person.name.toLowerCase());
      });
    });
  }, [associations, state.people, state.notes, projectId]);

  // Derived: action items linked to this project's notes
  const projectActions = useMemo(() => {
    const noteIds = new Set(associations.map((a) => a.note_id));
    return state.actionItems.filter((item) => noteIds.has(item.note_id));
  }, [associations, state.actionItems]);

  const updateField = useCallback(
    async (changes: Partial<ProjectState>) => {
      try {
        await api.updateProject(projectId, changes);
        dispatch({ type: "UPDATE_PROJECT", id: projectId, changes });
      } catch (e) {
        console.error("Failed to update project:", e);
      }
    },
    [projectId, dispatch]
  );

  const saveTitle = useCallback(() => {
    setEditingTitle(false);
    if (titleDraft.trim() && titleDraft !== project?.title) {
      updateField({ title: titleDraft.trim() });
    }
  }, [titleDraft, project?.title, updateField]);

  const saveGoal = useCallback(() => {
    setEditingGoal(false);
    if (goalDraft !== project?.goal) {
      updateField({ goal: goalDraft });
    }
  }, [goalDraft, project?.goal, updateField]);

  const saveDesc = useCallback(() => {
    setEditingDesc(false);
    if (descDraft !== project?.description) {
      updateField({ description: descDraft });
    }
  }, [descDraft, project?.description, updateField]);

  const saveDeadline = useCallback(() => {
    setEditingDeadline(false);
    if (deadlineDraft !== (project?.deadline ?? "")) {
      updateField({ deadline: deadlineDraft || undefined });
    }
  }, [deadlineDraft, project?.deadline, updateField]);

  const changeStatus = useCallback(
    (status: ProjectState["status"]) => {
      setStatusOpen(false);
      updateField({ status });
    },
    [updateField]
  );

  const handleDelete = useCallback(async () => {
    try {
      await api.deleteProject(projectId);
      dispatch({ type: "DELETE_PROJECT", id: projectId });
      dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "home" } });
    } catch (e) {
      console.error("Failed to delete project:", e);
    }
  }, [projectId, dispatch]);

  const toggleActionComplete = useCallback(
    async (item: ActionItemState) => {
      const newStatus = item.status === "completed" ? "pending" : "completed";
      try {
        await api.updateActionStatus(item.id, newStatus);
        dispatch({
          type: "UPDATE_ACTION_ITEM",
          id: item.id,
          changes: { status: newStatus },
        });
      } catch (e) {
        console.error("Failed to toggle action:", e);
      }
    },
    [dispatch]
  );

  const navigateToNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
      dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "editor", noteId } });
    },
    [dispatch]
  );

  if (!project) {
    return (
      <div className="pd-empty">
        <p>Project not found.</p>
        <button
          className="pd-back-btn"
          onClick={() =>
            dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "home" } })
          }
        >
          <ArrowLeft size={14} /> Back
        </button>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="pd-container">
      <style>{styles}</style>

      {/* Header */}
      <header className="pd-header">
        <div className="pd-header-top">
          <button
            className="pd-back-btn"
            onClick={() =>
              dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "home" } })
            }
          >
            <ArrowLeft size={14} />
          </button>

          {/* Status badge */}
          <div className="pd-status-wrapper">
            <button
              className="pd-status-badge"
              style={{
                background: `${STATUS_COLORS[project.status]}22`,
                color: STATUS_COLORS[project.status],
                borderColor: `${STATUS_COLORS[project.status]}44`,
              }}
              onClick={() => setStatusOpen(!statusOpen)}
            >
              {project.status}
              <ChevronDown size={12} />
            </button>
            {statusOpen && (
              <div className="pd-status-dropdown">
                {(["active", "paused", "completed", "archived"] as const).map(
                  (s) => (
                    <button
                      key={s}
                      className={`pd-status-option ${
                        s === project.status ? "pd-status-active" : ""
                      }`}
                      onClick={() => changeStatus(s)}
                    >
                      <span
                        className="pd-status-dot"
                        style={{ background: STATUS_COLORS[s] }}
                      />
                      {s}
                    </button>
                  )
                )}
              </div>
            )}
          </div>

          <button
            className="pd-delete-btn"
            onClick={() => setShowDeleteConfirm(true)}
            title="Delete project"
          >
            <Trash2 size={14} />
          </button>
        </div>

        {/* Title */}
        <div className="pd-title-row">
          {editingTitle ? (
            <input
              className="pd-title-input"
              value={titleDraft}
              onChange={(e) => setTitleDraft(e.target.value)}
              onBlur={saveTitle}
              onKeyDown={(e) => {
                if (e.key === "Enter") saveTitle();
                if (e.key === "Escape") setEditingTitle(false);
              }}
              autoFocus
            />
          ) : (
            <h1
              className="pd-title"
              onClick={() => {
                setTitleDraft(project.title);
                setEditingTitle(true);
              }}
            >
              {project.title}
            </h1>
          )}
        </div>

        {/* Meta row */}
        <div className="pd-meta">
          {project.category && (
            <span className="pd-category">
              <Folder size={12} />
              {project.category}
            </span>
          )}
          <span className="pd-deadline-display">
            <Calendar size={12} />
            {editingDeadline ? (
              <input
                type="date"
                className="pd-deadline-input"
                value={deadlineDraft}
                onChange={(e) => setDeadlineDraft(e.target.value)}
                onBlur={saveDeadline}
                onKeyDown={(e) => {
                  if (e.key === "Enter") saveDeadline();
                  if (e.key === "Escape") setEditingDeadline(false);
                }}
                autoFocus
              />
            ) : (
              <span
                className="pd-deadline-text"
                onClick={() => {
                  setDeadlineDraft(project.deadline ?? "");
                  setEditingDeadline(true);
                }}
              >
                {project.deadline
                  ? new Date(project.deadline).toLocaleDateString()
                  : "No deadline"}
              </span>
            )}
          </span>
        </div>
      </header>

      {/* Goal */}
      <section className="pd-section">
        <h3 className="pd-section-label">Goal</h3>
        {editingGoal ? (
          <textarea
            className="pd-textarea"
            value={goalDraft}
            onChange={(e) => setGoalDraft(e.target.value)}
            onBlur={saveGoal}
            onKeyDown={(e) => {
              if (e.key === "Escape") setEditingGoal(false);
            }}
            rows={3}
            autoFocus
          />
        ) : (
          <p
            className="pd-text-block"
            onClick={() => {
              setGoalDraft(project.goal);
              setEditingGoal(true);
            }}
          >
            {project.goal || "Click to add a goal..."}
          </p>
        )}
      </section>

      {/* Description */}
      <section className="pd-section">
        <h3 className="pd-section-label">Description</h3>
        {editingDesc ? (
          <textarea
            className="pd-textarea"
            value={descDraft}
            onChange={(e) => setDescDraft(e.target.value)}
            onBlur={saveDesc}
            onKeyDown={(e) => {
              if (e.key === "Escape") setEditingDesc(false);
            }}
            rows={4}
            autoFocus
          />
        ) : (
          <p
            className="pd-text-block"
            onClick={() => {
              setDescDraft(project.description);
              setEditingDesc(true);
            }}
          >
            {project.description || "Click to add a description..."}
          </p>
        )}
      </section>

      {/* Tab bar */}
      <div className="pd-tab-bar">
        <button
          className={`pd-tab ${tab === "notes" ? "pd-tab-active" : ""}`}
          onClick={() => setTab("notes")}
        >
          <FileText size={14} />
          Notes
          {relatedNotes.length > 0 && (
            <span className="pd-tab-count">{relatedNotes.length}</span>
          )}
        </button>
        <button
          className={`pd-tab ${tab === "actions" ? "pd-tab-active" : ""}`}
          onClick={() => setTab("actions")}
        >
          <ListTodo size={14} />
          Actions
          {projectActions.length > 0 && (
            <span className="pd-tab-count">{projectActions.length}</span>
          )}
        </button>
        <button
          className={`pd-tab ${tab === "people" ? "pd-tab-active" : ""}`}
          onClick={() => setTab("people")}
        >
          <Users size={14} />
          People
          {relatedPeople.length > 0 && (
            <span className="pd-tab-count">{relatedPeople.length}</span>
          )}
        </button>
      </div>

      {/* Tab content */}
      <div className="pd-tab-content">
        {tab === "notes" && (
          <div className="pd-list">
            {relatedNotes.length === 0 ? (
              <p className="pd-empty-text">No notes linked to this project.</p>
            ) : (
              relatedNotes.map((note) => (
                <button
                  key={note.id}
                  className="pd-list-item"
                  onClick={() => navigateToNote(note.id)}
                >
                  <FileText size={14} className="pd-list-icon" />
                  <div className="pd-list-info">
                    <span className="pd-list-title">{note.title}</span>
                    <span className="pd-list-sub">
                      {new Date(note.updated_at).toLocaleDateString()}
                    </span>
                  </div>
                </button>
              ))
            )}
          </div>
        )}

        {tab === "actions" && (
          <div className="pd-list">
            {projectActions.length === 0 ? (
              <p className="pd-empty-text">No action items for this project.</p>
            ) : (
              projectActions.map((item) => (
                <div key={item.id} className="pd-action-item">
                  <button
                    className="pd-action-toggle"
                    onClick={() => toggleActionComplete(item)}
                    title={
                      item.status === "completed"
                        ? "Mark pending"
                        : "Mark complete"
                    }
                  >
                    {item.status === "completed" ? (
                      <CheckCircle2 size={16} color="#22c55e" />
                    ) : (
                      <Circle size={16} />
                    )}
                  </button>
                  <div className="pd-action-info">
                    <span
                      className={`pd-action-task ${
                        item.status === "completed"
                          ? "pd-action-done"
                          : ""
                      }`}
                    >
                      {item.task}
                    </span>
                    <div className="pd-action-meta">
                      <span
                        className="pd-priority"
                        data-priority={item.priority}
                      >
                        {item.priority}
                      </span>
                      {item.deadline && (
                        <span className="pd-action-deadline">
                          <Clock size={10} />
                          {new Date(item.deadline).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {tab === "people" && (
          <div className="pd-list">
            {relatedPeople.length === 0 ? (
              <p className="pd-empty-text">
                No people linked to this project.
              </p>
            ) : (
              relatedPeople.map((person) => (
                <button
                  key={person.id}
                  className="pd-list-item"
                  onClick={() =>
                    dispatch({
                      type: "SET_CONTEXT_MODE",
                      mode: { type: "person", personId: person.id },
                    })
                  }
                >
                  <User size={14} className="pd-list-icon" />
                  <div className="pd-list-info">
                    <span className="pd-list-title">{person.name}</span>
                    <span className="pd-list-sub">{person.role}</span>
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>

      {/* Delete confirmation */}
      {showDeleteConfirm && (
        <div
          className="pd-confirm-overlay"
          onClick={() => setShowDeleteConfirm(false)}
        >
          <div
            className="pd-confirm-dialog"
            onClick={(e) => e.stopPropagation()}
          >
            <p>
              Delete <strong>{project.title}</strong>? This cannot be undone.
            </p>
            <div className="pd-confirm-actions">
              <button
                className="pd-confirm-cancel"
                onClick={() => setShowDeleteConfirm(false)}
              >
                Cancel
              </button>
              <button className="pd-confirm-delete" onClick={handleDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = `
.pd-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  background: var(--bg-primary, #1e1e2e);
  color: var(--text-primary, #e4e4e7);
  padding: 24px 32px;
}

.pd-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--text-muted, #71717a);
}

/* Header */
.pd-header {
  margin-bottom: 20px;
}

.pd-header-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.pd-back-btn {
  background: none;
  border: 1px solid var(--border, #27272a);
  color: var(--text-muted, #71717a);
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  transition: color 0.15s;
}
.pd-back-btn:hover {
  color: var(--text-primary, #e4e4e7);
}

.pd-status-wrapper {
  position: relative;
}

.pd-status-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 12px;
  border: 1px solid;
  font-size: 11px;
  font-weight: 600;
  text-transform: capitalize;
  cursor: pointer;
  background: transparent;
}

.pd-status-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: var(--bg-secondary, #27272a);
  border: 1px solid var(--border, #27272a);
  border-radius: 8px;
  padding: 4px;
  z-index: 20;
  min-width: 130px;
}

.pd-status-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: none;
  color: var(--text-primary, #e4e4e7);
  font-size: 12px;
  text-transform: capitalize;
  cursor: pointer;
  border-radius: 4px;
}
.pd-status-option:hover {
  background: rgba(255, 255, 255, 0.06);
}
.pd-status-active {
  background: rgba(255, 255, 255, 0.04);
}

.pd-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.pd-delete-btn {
  margin-left: auto;
  background: none;
  border: 1px solid var(--border, #27272a);
  color: var(--text-muted, #71717a);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  transition: color 0.15s, border-color 0.15s;
}
.pd-delete-btn:hover {
  color: #ef4444;
  border-color: #ef444466;
}

/* Title */
.pd-title-row {
  margin-bottom: 8px;
}

.pd-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  cursor: pointer;
  padding: 2px 0;
  border-bottom: 1px dashed transparent;
}
.pd-title:hover {
  border-bottom-color: var(--border, #27272a);
}

.pd-title-input {
  width: 100%;
  font-size: 24px;
  font-weight: 700;
  background: var(--bg-secondary, #27272a);
  border: 1px solid var(--accent, #3b82f6);
  border-radius: 6px;
  color: var(--text-primary, #e4e4e7);
  padding: 4px 8px;
  outline: none;
}

/* Meta */
.pd-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-muted, #71717a);
  font-size: 12px;
}

.pd-category {
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--bg-secondary, #27272a);
  padding: 2px 8px;
  border-radius: 8px;
}

.pd-deadline-display {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pd-deadline-text {
  cursor: pointer;
  border-bottom: 1px dashed transparent;
}
.pd-deadline-text:hover {
  border-bottom-color: var(--text-muted, #71717a);
}

.pd-deadline-input {
  background: var(--bg-secondary, #27272a);
  border: 1px solid var(--accent, #3b82f6);
  border-radius: 4px;
  color: var(--text-primary, #e4e4e7);
  font-size: 12px;
  padding: 2px 6px;
  outline: none;
}

/* Sections */
.pd-section {
  border-top: 1px solid var(--border, #27272a);
  padding: 16px 0;
}

.pd-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted, #71717a);
  margin: 0 0 8px;
}

.pd-text-block {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 6px;
  min-height: 28px;
  white-space: pre-wrap;
}
.pd-text-block:hover {
  background: var(--bg-secondary, #27272a);
}

.pd-textarea {
  width: 100%;
  background: var(--bg-secondary, #27272a);
  border: 1px solid var(--accent, #3b82f6);
  border-radius: 6px;
  color: var(--text-primary, #e4e4e7);
  font-size: 14px;
  line-height: 1.6;
  padding: 8px;
  resize: vertical;
  outline: none;
  font-family: inherit;
}

/* Tab bar */
.pd-tab-bar {
  display: flex;
  gap: 2px;
  border-top: 1px solid var(--border, #27272a);
  border-bottom: 1px solid var(--border, #27272a);
  padding: 0;
}

.pd-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border: none;
  background: none;
  color: var(--text-muted, #71717a);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.pd-tab:hover {
  color: var(--text-primary, #e4e4e7);
}
.pd-tab-active {
  color: var(--accent, #3b82f6);
  border-bottom-color: var(--accent, #3b82f6);
}

.pd-tab-count {
  background: var(--bg-secondary, #27272a);
  padding: 0 6px;
  border-radius: 8px;
  font-size: 11px;
  line-height: 18px;
}

/* Tab content */
.pd-tab-content {
  flex: 1;
  padding: 12px 0;
  min-height: 0;
}

.pd-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.pd-empty-text {
  color: var(--text-muted, #71717a);
  font-size: 13px;
  padding: 16px 0;
  text-align: center;
}

.pd-list-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  background: none;
  color: var(--text-primary, #e4e4e7);
  cursor: pointer;
  border-radius: 6px;
  text-align: left;
  width: 100%;
  transition: background 0.12s;
}
.pd-list-item:hover {
  background: var(--bg-secondary, #27272a);
}

.pd-list-icon {
  color: var(--text-muted, #71717a);
  flex-shrink: 0;
}

.pd-list-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pd-list-title {
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pd-list-sub {
  font-size: 11px;
  color: var(--text-muted, #71717a);
}

/* Action items */
.pd-action-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
}
.pd-action-item:hover {
  background: var(--bg-secondary, #27272a);
}

.pd-action-toggle {
  background: none;
  border: none;
  color: var(--text-muted, #71717a);
  cursor: pointer;
  padding: 2px;
  flex-shrink: 0;
  display: flex;
}

.pd-action-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.pd-action-task {
  font-size: 13px;
  line-height: 1.4;
}

.pd-action-done {
  text-decoration: line-through;
  color: var(--text-muted, #71717a);
}

.pd-action-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
}

.pd-priority {
  text-transform: capitalize;
  font-weight: 600;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
}
.pd-priority[data-priority="high"] {
  color: #ef4444;
  background: #ef444420;
}
.pd-priority[data-priority="medium"] {
  color: #eab308;
  background: #eab30820;
}
.pd-priority[data-priority="low"] {
  color: #22c55e;
  background: #22c55e20;
}

.pd-action-deadline {
  display: flex;
  align-items: center;
  gap: 3px;
  color: var(--text-muted, #71717a);
}

/* Delete confirmation */
.pd-confirm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.pd-confirm-dialog {
  background: var(--bg-secondary, #27272a);
  border: 1px solid var(--border, #27272a);
  border-radius: 12px;
  padding: 20px 24px;
  max-width: 360px;
  font-size: 14px;
}

.pd-confirm-dialog p {
  margin: 0 0 16px;
}

.pd-confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.pd-confirm-cancel,
.pd-confirm-delete {
  padding: 6px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
}

.pd-confirm-cancel {
  background: var(--bg-primary, #1e1e2e);
  color: var(--text-primary, #e4e4e7);
  border: 1px solid var(--border, #27272a);
}
.pd-confirm-cancel:hover {
  background: rgba(255, 255, 255, 0.06);
}

.pd-confirm-delete {
  background: #ef4444;
  color: #fff;
}
.pd-confirm-delete:hover {
  background: #dc2626;
}
`;
