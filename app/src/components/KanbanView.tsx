import { useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { Note } from "../lib/api";
import { Plus, GripVertical, Trash2 } from "lucide-react";

interface KanbanColumn {
  id: string;
  title: string;
  noteIds: string[];
}

const DEFAULT_COLUMNS: KanbanColumn[] = [
  { id: "inbox", title: "Inbox", noteIds: [] },
  { id: "active", title: "Active", noteIds: [] },
  { id: "review", title: "Review", noteIds: [] },
  { id: "done", title: "Done", noteIds: [] },
];

export function KanbanView() {
  const { state, dispatch } = useApp();
  const [columns, setColumns] = useState<KanbanColumn[]>(() => {
    // Auto-categorize notes by frontmatter "status" field
    const cols = DEFAULT_COLUMNS.map((c) => ({ ...c, noteIds: [...c.noteIds] }));
    for (const note of state.notes) {
      const status = note.frontmatter?.status?.toLowerCase();
      if (status === "active" || status === "in-progress") {
        cols[1].noteIds.push(note.id);
      } else if (status === "review") {
        cols[2].noteIds.push(note.id);
      } else if (status === "done" || status === "completed") {
        cols[3].noteIds.push(note.id);
      } else {
        cols[0].noteIds.push(note.id);
      }
    }
    return cols;
  });

  const [draggedNote, setDraggedNote] = useState<string | null>(null);
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);

  const noteMap = useMemo(() => {
    const map = new Map<string, Note>();
    for (const note of state.notes) {
      map.set(note.id, note);
    }
    return map;
  }, [state.notes]);

  const handleDragStart = useCallback((noteId: string) => {
    setDraggedNote(noteId);
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, colId: string) => {
      e.preventDefault();
      setDragOverCol(colId);
    },
    []
  );

  const handleDrop = useCallback(
    async (colId: string) => {
      if (!draggedNote) return;

      setColumns((prev) => {
        const next = prev.map((col) => ({
          ...col,
          noteIds: col.noteIds.filter((id) => id !== draggedNote),
        }));
        const target = next.find((c) => c.id === colId);
        if (target) target.noteIds.push(draggedNote);
        return next;
      });

      // Update note frontmatter with new status
      const note = noteMap.get(draggedNote);
      if (note) {
        const statusMap: Record<string, string> = {
          inbox: "inbox",
          active: "active",
          review: "review",
          done: "done",
        };
        try {
          const updated = await api.saveNote(
            note.file_path,
            note.title,
            note.content,
            { ...note.frontmatter, status: statusMap[colId] ?? colId }
          );
          dispatch({ type: "UPDATE_NOTE", note: updated });
        } catch (err) {
          console.error("Failed to update note status:", err);
        }
      }

      setDraggedNote(null);
      setDragOverCol(null);
    },
    [draggedNote, noteMap, dispatch]
  );

  const handleAddColumn = useCallback(() => {
    const title = prompt("Column name:");
    if (!title) return;
    setColumns((prev) => [
      ...prev,
      { id: title.toLowerCase().replace(/\s+/g, "-"), title, noteIds: [] },
    ]);
  }, []);

  const handleRemoveColumn = useCallback((colId: string) => {
    setColumns((prev) => {
      const col = prev.find((c) => c.id === colId);
      if (!col) return prev;
      // Move notes to inbox
      const inbox = prev.find((c) => c.id === "inbox");
      return prev
        .filter((c) => c.id !== colId)
        .map((c) =>
          c.id === "inbox" && inbox
            ? { ...c, noteIds: [...c.noteIds, ...col.noteIds] }
            : c
        );
    });
  }, []);

  const openNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    },
    [dispatch]
  );

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <span>Kanban Board</span>
          <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
            &nbsp;· {state.notes.length} notes
          </span>
        </div>
        <div className="editor-actions">
          <button
            className="icon-btn"
            onClick={handleAddColumn}
            title="Add column"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      <div className="kanban-board">
        {columns.map((col) => (
          <div
            key={col.id}
            className={`kanban-column ${dragOverCol === col.id ? "drag-over" : ""}`}
            onDragOver={(e) => handleDragOver(e, col.id)}
            onDrop={() => handleDrop(col.id)}
            onDragLeave={() => setDragOverCol(null)}
          >
            <div className="kanban-column-header">
              <span className="kanban-column-title">{col.title}</span>
              <span className="kanban-column-count">{col.noteIds.length}</span>
              {col.id !== "inbox" && (
                <button
                  className="icon-btn kanban-remove-col"
                  onClick={() => handleRemoveColumn(col.id)}
                  title="Remove column"
                >
                  <Trash2 size={11} />
                </button>
              )}
            </div>
            <div className="kanban-cards">
              {col.noteIds.map((noteId) => {
                const note = noteMap.get(noteId);
                if (!note) return null;
                return (
                  <div
                    key={noteId}
                    className={`kanban-card ${draggedNote === noteId ? "dragging" : ""}`}
                    draggable
                    onDragStart={() => handleDragStart(noteId)}
                    onClick={() => openNote(noteId)}
                  >
                    <div className="kanban-card-grip">
                      <GripVertical size={12} />
                    </div>
                    <div className="kanban-card-content">
                      <div className="kanban-card-title">{note.title}</div>
                      <div className="kanban-card-preview">
                        {note.content.replace(/^#.*\n/, "").slice(0, 80)}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
