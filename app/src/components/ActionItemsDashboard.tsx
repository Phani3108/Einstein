import { useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  CheckSquare, Square, Calendar, AlertTriangle, User, FileText,
  Filter, ArrowUpDown, Clock, CheckCircle, Circle, Flag, Plus,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface ActionItem {
  id: string;
  task: string;
  sourceNoteId: string;
  sourceTitle: string;
  assignee: string | null;
  deadline: string | null;
  priority: "high" | "medium" | "low";
  completed: boolean;
}

type FilterMode = "all" | "pending" | "completed" | "overdue";
type SortField = "deadline" | "priority" | "source";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const PRIORITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function ActionItemsDashboard() {
  const { state, dispatch } = useApp();

  const [filter, setFilter] = useState<FilterMode>("all");
  const [sortField, setSortField] = useState<SortField>("deadline");

  const todayStr = useMemo(() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }, []);

  /* ---- Map central state to display items ---- */
  const allItems: ActionItem[] = useMemo(() => {
    return state.actionItems.map((item) => ({
      id: item.id,
      task: item.task,
      sourceNoteId: item.note_id,
      sourceTitle: item.source_title,
      assignee: item.assignee,
      deadline: item.deadline,
      priority: item.priority,
      completed: item.status === "completed",
    }));
  }, [state.actionItems]);

  /* ---- Stats ---- */
  const stats = useMemo(() => {
    const total = allItems.length;
    const completed = allItems.filter((i) => i.completed).length;
    const pending = total - completed;
    const overdue = allItems.filter(
      (i) => !i.completed && i.deadline && i.deadline < todayStr,
    ).length;
    return { total, completed, pending, overdue };
  }, [allItems, todayStr]);

  /* ---- Filter ---- */
  const filteredItems = useMemo(() => {
    let items = allItems;
    switch (filter) {
      case "pending":
        items = items.filter((i) => !i.completed);
        break;
      case "completed":
        items = items.filter((i) => i.completed);
        break;
      case "overdue":
        items = items.filter(
          (i) => !i.completed && i.deadline && i.deadline < todayStr,
        );
        break;
    }
    return items;
  }, [allItems, filter, todayStr]);

  /* ---- Sort ---- */
  const sortedItems = useMemo(() => {
    const sorted = [...filteredItems];
    sorted.sort((a, b) => {
      switch (sortField) {
        case "deadline":
          if (!a.deadline && !b.deadline) return 0;
          if (!a.deadline) return 1;
          if (!b.deadline) return -1;
          return a.deadline.localeCompare(b.deadline);
        case "priority":
          return (PRIORITY_ORDER[a.priority] ?? 1) - (PRIORITY_ORDER[b.priority] ?? 1);
        case "source":
          return a.sourceTitle.localeCompare(b.sourceTitle);
        default:
          return 0;
      }
    });
    return sorted;
  }, [filteredItems, sortField]);

  /* ---- Handlers ---- */
  const toggleComplete = useCallback(
    async (id: string) => {
      const item = state.actionItems.find((i) => i.id === id);
      if (!item) return;
      const newStatus = item.status === "completed" ? "pending" : "completed";
      // Optimistic update in central state
      dispatch({ type: "UPDATE_ACTION_ITEM", id, changes: { status: newStatus } });
      // Persist to DB
      try {
        await api.updateActionStatus(id, newStatus);
      } catch (err) {
        // Revert on failure
        dispatch({ type: "UPDATE_ACTION_ITEM", id, changes: { status: item.status } });
        console.error("Failed to update action status:", err);
      }
    },
    [state.actionItems, dispatch],
  );

  const navigateToNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    },
    [dispatch],
  );

  const cycleSort = useCallback(() => {
    setSortField((prev) => {
      if (prev === "deadline") return "priority";
      if (prev === "priority") return "source";
      return "deadline";
    });
  }, []);

  return (
    <div className="main-content" style={{ overflow: "auto" }}>
      {/* Header */}
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <CheckSquare size={14} style={{ marginRight: 6 }} />
          <span>Action Items</span>
        </div>
      </div>

      <div className="ai-wrapper">
        {/* Stats Bar */}
        <div className="ai-stats-bar">
          <div className="ai-stat-pill">
            <Circle size={12} />
            <span className="ai-stat-num">{stats.total}</span>
            <span className="ai-stat-lbl">Total</span>
          </div>
          <div className="ai-stat-pill ai-stat-completed">
            <CheckCircle size={12} />
            <span className="ai-stat-num">{stats.completed}</span>
            <span className="ai-stat-lbl">Completed</span>
          </div>
          <div className="ai-stat-pill ai-stat-pending">
            <Clock size={12} />
            <span className="ai-stat-num">{stats.pending}</span>
            <span className="ai-stat-lbl">Pending</span>
          </div>
          <div className="ai-stat-pill ai-stat-overdue">
            <AlertTriangle size={12} />
            <span className="ai-stat-num">{stats.overdue}</span>
            <span className="ai-stat-lbl">Overdue</span>
          </div>
        </div>

        {/* Controls */}
        <div className="ai-controls">
          <div className="ai-filter-group">
            <Filter size={12} />
            {(["all", "pending", "completed", "overdue"] as FilterMode[]).map((f) => (
              <button
                key={f}
                className={`ai-filter-btn ${filter === f ? "active" : ""}`}
                onClick={() => setFilter(f)}
              >
                {f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
          <button className="ai-sort-btn" onClick={cycleSort} title={`Sort by ${sortField}`}>
            <ArrowUpDown size={12} />
            {sortField.charAt(0).toUpperCase() + sortField.slice(1)}
          </button>
        </div>

        {/* Items List */}
        {sortedItems.length > 0 ? (
          <div className="ai-items-table">
            {/* Header row */}
            <div className="ai-table-header">
              <span className="ai-col-check" />
              <span className="ai-col-task">Task</span>
              <span className="ai-col-source">Source</span>
              <span className="ai-col-assignee">Assignee</span>
              <span className="ai-col-deadline">Deadline</span>
              <span className="ai-col-priority">Priority</span>
            </div>

            {/* Rows */}
            {sortedItems.map((item) => {
              const isOverdue =
                !item.completed && item.deadline && item.deadline < todayStr;
              return (
                <div
                  key={item.id}
                  className={`ai-table-row ${item.completed ? "completed" : ""} ${isOverdue ? "overdue" : ""}`}
                >
                  <span
                    className="ai-col-check"
                    onClick={() => toggleComplete(item.id)}
                  >
                    {item.completed ? (
                      <CheckSquare size={16} className="ai-check-done" />
                    ) : (
                      <Square size={16} className="ai-check-pending" />
                    )}
                  </span>

                  <span className="ai-col-task">
                    <span className="ai-task-text">{item.task}</span>
                  </span>

                  <span
                    className="ai-col-source"
                    onClick={() => navigateToNote(item.sourceNoteId)}
                  >
                    <FileText size={12} />
                    <span className="ai-source-text">{item.sourceTitle}</span>
                  </span>

                  <span className="ai-col-assignee">
                    {item.assignee ? (
                      <>
                        <User size={12} />
                        <span>{item.assignee}</span>
                      </>
                    ) : (
                      <span className="ai-no-value">--</span>
                    )}
                  </span>

                  <span className={`ai-col-deadline ${isOverdue ? "overdue" : ""}`}>
                    {item.deadline ? (
                      <>
                        {isOverdue && <AlertTriangle size={10} />}
                        <Calendar size={10} />
                        <span>{item.deadline}</span>
                      </>
                    ) : (
                      <span className="ai-no-value">--</span>
                    )}
                  </span>

                  <span className="ai-col-priority">
                    <span className="ai-priority-badge" data-priority={item.priority}>
                      <Flag size={10} />
                      {item.priority}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="ai-empty-state">
            <CheckSquare size={48} />
            <h2>No action items found</h2>
            <p>
              Action items are extracted automatically from your meeting notes
              and any note containing tasks with deadlines.
            </p>
            <p className="ai-empty-hint">
              Use <code>- [ ] task description</code> or <code>- [x] done task</code> syntax
              in your notes, or add an <code>action_items</code> field to your frontmatter.
            </p>
          </div>
        )}
      </div>

      <style>{`
        /* Wrapper */
        .ai-wrapper {
          max-width: 960px;
          margin: 0 auto;
          padding: 24px 28px 48px;
        }

        /* Stats Bar */
        .ai-stats-bar {
          display: flex;
          gap: 12px;
          margin-bottom: 20px;
          flex-wrap: wrap;
        }
        .ai-stat-pill {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 18px;
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          flex: 1;
          min-width: 120px;
        }
        .ai-stat-pill svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .ai-stat-completed svg { color: #10b981; }
        .ai-stat-pending svg { color: #f59e0b; }
        .ai-stat-overdue svg { color: #ef4444; }
        .ai-stat-num {
          font-size: 1.25rem;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ai-stat-lbl {
          font-size: 0.72rem;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        /* Controls */
        .ai-controls {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
          gap: 12px;
          flex-wrap: wrap;
        }
        .ai-filter-group {
          display: flex;
          align-items: center;
          gap: 4px;
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          padding: 3px;
        }
        .ai-filter-group > svg {
          margin-left: 8px;
          color: var(--text-muted, #71717a);
        }
        .ai-filter-btn {
          background: none;
          border: none;
          padding: 5px 14px;
          border-radius: 6px;
          font-size: 0.78rem;
          font-weight: 500;
          cursor: pointer;
          color: var(--text-muted, #71717a);
          transition: all 0.15s;
        }
        .ai-filter-btn.active {
          background: var(--accent, #3b82f6);
          color: #fff;
        }
        .ai-filter-btn:hover:not(.active) {
          color: var(--text-primary, #e4e4e7);
        }
        .ai-sort-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 5px 14px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: none;
          color: var(--text-muted, #a1a1aa);
          font-size: 0.78rem;
          font-weight: 500;
          cursor: pointer;
          transition: color 0.15s, border-color 0.15s;
        }
        .ai-sort-btn:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }

        /* Table */
        .ai-items-table {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          overflow: hidden;
        }
        .ai-table-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 0.72rem;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .ai-table-row {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border, #27272a);
          transition: background 0.12s;
        }
        .ai-table-row:last-child { border-bottom: none; }
        .ai-table-row:hover {
          background: var(--bg-tertiary, #0f0f12);
        }
        .ai-table-row.completed {
          opacity: 0.5;
        }
        .ai-table-row.completed .ai-task-text {
          text-decoration: line-through;
        }

        /* Columns */
        .ai-col-check {
          width: 28px;
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
        }
        .ai-check-done { color: #10b981; }
        .ai-check-pending { color: var(--text-muted, #71717a); }
        .ai-check-pending:hover { color: var(--text-primary, #e4e4e7); }

        .ai-col-task {
          flex: 3;
          min-width: 0;
        }
        .ai-task-text {
          font-size: 0.85rem;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          display: block;
        }
        .ai-table-row.overdue .ai-task-text {
          color: #ef4444;
        }

        .ai-col-source {
          flex: 2;
          min-width: 0;
          display: flex;
          align-items: center;
          gap: 6px;
          cursor: pointer;
          color: var(--accent, #3b82f6);
          font-size: 0.78rem;
        }
        .ai-col-source:hover {
          text-decoration: underline;
        }
        .ai-source-text {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .ai-col-assignee {
          flex: 1;
          min-width: 0;
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.78rem;
          color: var(--text-secondary, #a1a1aa);
        }

        .ai-col-deadline {
          flex: 1.2;
          min-width: 0;
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 0.78rem;
          color: var(--text-muted, #71717a);
        }
        .ai-col-deadline.overdue {
          color: #ef4444;
          font-weight: 600;
        }

        .ai-col-priority {
          width: 80px;
          flex-shrink: 0;
          display: flex;
          justify-content: flex-end;
        }
        .ai-priority-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          font-size: 0.68rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          padding: 3px 10px;
          border-radius: 6px;
        }
        .ai-priority-badge[data-priority="high"] {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .ai-priority-badge[data-priority="medium"] {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .ai-priority-badge[data-priority="low"] {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }

        .ai-no-value {
          color: var(--text-muted, #71717a);
          opacity: 0.4;
          font-size: 0.78rem;
        }

        /* Empty state */
        .ai-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 64px 24px;
          text-align: center;
          color: var(--text-muted, #71717a);
        }
        .ai-empty-state svg {
          margin-bottom: 16px;
          opacity: 0.3;
        }
        .ai-empty-state h2 {
          margin: 0 0 8px;
          font-size: 1.2rem;
          color: var(--text-secondary, #a1a1aa);
        }
        .ai-empty-state p {
          margin: 0 0 12px;
          font-size: 0.88rem;
          max-width: 460px;
          line-height: 1.6;
        }
        .ai-empty-hint {
          font-size: 0.82rem;
          color: var(--text-muted, #71717a);
        }
        .ai-empty-hint code {
          background: var(--bg-tertiary, #0f0f12);
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 0.78rem;
          color: var(--text-secondary, #a1a1aa);
        }

        /* Responsive */
        @media (max-width: 700px) {
          .ai-stats-bar {
            flex-direction: column;
          }
          .ai-col-assignee,
          .ai-col-deadline {
            display: none;
          }
          .ai-table-header .ai-col-assignee,
          .ai-table-header .ai-col-deadline {
            display: none;
          }
        }
      `}</style>
    </div>
  );
}
