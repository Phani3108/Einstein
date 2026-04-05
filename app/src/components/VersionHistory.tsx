import { useState, useEffect, useCallback, useMemo } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { NoteVersion } from "../lib/api";
import { History, RotateCcw, Clock, ChevronDown, ChevronUp } from "lucide-react";

export function VersionHistory() {
  const { state, dispatch } = useApp();
  const { activeNoteId, notes } = state;
  const activeNote = useMemo(
    () => notes.find((n) => n.id === activeNoteId),
    [notes, activeNoteId]
  );
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [restoring, setRestoring] = useState(false);
  const [confirmRestore, setConfirmRestore] = useState<string | null>(null);

  useEffect(() => {
    if (!activeNoteId) {
      setVersions([]);
      return;
    }
    setLoading(true);
    api
      .getNoteVersions(activeNoteId)
      .then(setVersions)
      .catch(() => setVersions([]))
      .finally(() => setLoading(false));
  }, [activeNoteId]);

  const handleRestore = useCallback(
    async (versionId: string) => {
      setRestoring(true);
      try {
        const restored = await api.restoreVersion(versionId);
        dispatch({ type: "UPDATE_NOTE", note: restored });
        setConfirmRestore(null);
        // Refresh versions list
        if (activeNoteId) {
          const updated = await api.getNoteVersions(activeNoteId);
          setVersions(updated);
        }
      } catch (err) {
        console.error("Failed to restore version:", err);
      } finally {
        setRestoring(false);
      }
    },
    [activeNoteId, dispatch]
  );

  if (!activeNote) {
    return (
      <div className="version-history">
        <div className="panel-section-title">
          <History size={12} style={{ marginRight: 4 }} />
          Version History
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          Select a note to see version history
        </p>
      </div>
    );
  }

  return (
    <div className="version-history">
      <div className="panel-section-title">
        <History size={12} style={{ marginRight: 4 }} />
        Version History
        <span className="count">{loading ? "..." : versions.length}</span>
      </div>

      {loading && (
        <div style={{ display: "flex", justifyContent: "center", padding: 16 }}>
          <div className="loading-spinner" />
        </div>
      )}

      {!loading && versions.length === 0 && (
        <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
          No previous versions yet. Versions are created automatically when you edit.
        </p>
      )}

      {!loading &&
        versions.map((version) => {
          const date = new Date(version.created_at);
          const isExpanded = expandedId === version.id;
          return (
            <div key={version.id} className="version-item">
              <div
                className="version-header"
                onClick={() => setExpandedId(isExpanded ? null : version.id)}
              >
                <Clock size={11} />
                <span className="version-date">
                  {date.toLocaleDateString()} {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="version-size">
                  {version.content.split(/\s+/).filter(Boolean).length}w
                </span>
                {isExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              </div>
              {isExpanded && (
                <div className="version-detail">
                  <pre className="version-content">{version.content.slice(0, 500)}{version.content.length > 500 ? "..." : ""}</pre>
                  {confirmRestore === version.id ? (
                    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
                      <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>
                        Restore this version? Current content will be saved.
                      </span>
                      <button
                        className="btn-secondary version-restore-btn"
                        onClick={() => handleRestore(version.id)}
                        disabled={restoring}
                        style={{ background: "var(--accent)", color: "#fff", borderColor: "var(--accent)" }}
                      >
                        <RotateCcw size={12} />
                        {restoring ? "Restoring..." : "Yes"}
                      </button>
                      <button
                        className="btn-secondary version-restore-btn"
                        onClick={() => setConfirmRestore(null)}
                        disabled={restoring}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      className="btn-secondary version-restore-btn"
                      onClick={() => setConfirmRestore(version.id)}
                      disabled={restoring}
                    >
                      <RotateCcw size={12} />
                      Restore this version
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
    </div>
  );
}
