import { useState, useEffect, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { Note } from "../lib/api";
import { Star, FileText } from "lucide-react";

export function BookmarksPanel() {
  const { state, dispatch } = useApp();
  const [bookmarkedNotes, setBookmarkedNotes] = useState<Note[]>([]);
  const [loading, setLoading] = useState(true);

  const loadBookmarks = useCallback(async () => {
    setLoading(true);
    try {
      const notes = await api.listBookmarks();
      setBookmarkedNotes(notes);
      dispatch({ type: "SET_BOOKMARKS", bookmarks: notes.map((n) => n.id) });
    } catch {
      setBookmarkedNotes([]);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  useEffect(() => {
    loadBookmarks();
  }, [loadBookmarks]);

  const handleToggle = useCallback(
    async (noteId: string) => {
      try {
        await api.toggleBookmark(noteId);
        dispatch({ type: "TOGGLE_BOOKMARK", noteId });
        loadBookmarks();
      } catch (err) {
        console.error("Failed to toggle bookmark:", err);
      }
    },
    [dispatch, loadBookmarks]
  );

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <Star size={14} style={{ marginRight: 6 }} />
          <span>Bookmarks</span>
        </div>
      </div>

      <div className="bookmarks-wrapper">
        {loading && (
          <div className="empty-state">
            <div className="loading-spinner" />
          </div>
        )}

        {!loading && bookmarkedNotes.length === 0 && (
          <div className="empty-state">
            <Star size={48} className="empty-icon" />
            <p>No bookmarked notes</p>
            <p className="hint">Click the star icon on any note to bookmark it</p>
          </div>
        )}

        {!loading &&
          bookmarkedNotes.map((note) => (
            <div
              key={note.id}
              className="bookmark-item"
              onClick={() => {
                dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
                dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
              }}
            >
              <FileText size={14} className="file-icon" />
              <div className="bookmark-info">
                <div className="bookmark-title">{note.title}</div>
                <div className="bookmark-path">{note.file_path}</div>
              </div>
              <button
                className="icon-btn bookmark-star"
                onClick={(e) => {
                  e.stopPropagation();
                  handleToggle(note.id);
                }}
                title="Remove bookmark"
              >
                <Star size={14} fill="var(--accent)" color="var(--accent)" />
              </button>
            </div>
          ))}
      </div>
    </div>
  );
}
