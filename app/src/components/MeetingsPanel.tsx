import { useState, useMemo } from "react";
import { useApp } from "../lib/store";
import { Video, Plus, Phone, Monitor, MessageCircle, Users, Calendar, CheckSquare, ChevronRight, FileText } from "lucide-react";
import { MeetingImportModal } from "./MeetingImportModal";
import type { Note } from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type SourceFilter = "all" | "zoom" | "teams" | "meet" | "whatsapp" | "phone";

interface MeetingCard {
  note: Note;
  title: string;
  date: string;
  source: string;
  participants: string[];
  actionItemCount: number;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const SOURCE_FILTERS: { key: SourceFilter; label: string }[] = [
  { key: "all",      label: "All" },
  { key: "zoom",     label: "Zoom" },
  { key: "teams",    label: "Teams" },
  { key: "meet",     label: "Meet" },
  { key: "whatsapp", label: "WhatsApp" },
  { key: "phone",    label: "Phone" },
];

function sourceIcon(source: string, size = 16): React.ReactNode {
  switch (source.toLowerCase()) {
    case "zoom":     return <Video size={size} />;
    case "teams":    return <Monitor size={size} />;
    case "meet":     return <Video size={size} />;
    case "whatsapp": return <MessageCircle size={size} />;
    case "phone":    return <Phone size={size} />;
    default:         return <FileText size={size} />;
  }
}

function sourceColor(source: string): string {
  switch (source.toLowerCase()) {
    case "zoom":     return "#2d8cff";
    case "teams":    return "#6264a7";
    case "meet":     return "#00897b";
    case "whatsapp": return "#25d366";
    case "phone":    return "#f59e0b";
    default:         return "var(--accent, #89b4fa)";
  }
}

function countActionItems(content: string): number {
  const matches = content.match(/- \[ \]/g);
  return matches ? matches.length : 0;
}

function parseParticipants(fm: Record<string, string>): string[] {
  const raw = fm.participants ?? "";
  return raw
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
}

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function MeetingsPanel() {
  const { state, dispatch } = useApp();
  const [filter, setFilter] = useState<SourceFilter>("all");
  const [importOpen, setImportOpen] = useState(false);

  /* Build meeting cards from notes */
  const meetings: MeetingCard[] = useMemo(() => {
    return state.notes
      .filter((n) => n.frontmatter?.type === "meeting")
      .map((n) => ({
        note: n,
        title: n.title || "Untitled Meeting",
        date: n.frontmatter?.date ?? n.created_at?.slice(0, 10) ?? "",
        source: n.frontmatter?.source ?? "other",
        participants: parseParticipants(n.frontmatter),
        actionItemCount: countActionItems(n.content),
      }))
      .sort((a, b) => (b.date > a.date ? 1 : b.date < a.date ? -1 : 0));
  }, [state.notes]);

  /* Apply source filter */
  const filtered = useMemo(() => {
    if (filter === "all") return meetings;
    return meetings.filter((m) => m.source.toLowerCase() === filter);
  }, [meetings, filter]);

  /* Aggregate stats */
  const totalActionItems = useMemo(
    () => meetings.reduce((sum, m) => sum + m.actionItemCount, 0),
    [meetings]
  );

  const handleOpenNote = (noteId: string) => {
    dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
    dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
  };

  return (
    <>
      <style>{`
        .mp-wrapper {
          display: flex; flex-direction: column; height: 100%;
          background: var(--bg-primary, #1e1e2e);
        }
        .mp-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 16px 20px 12px;
          border-bottom: 1px solid var(--border, #333);
        }
        .mp-header-left {
          display: flex; align-items: center; gap: 8px;
          font-size: 16px; font-weight: 600;
          color: var(--text-primary, #cdd6f4);
        }
        .mp-import-btn {
          display: flex; align-items: center; gap: 5px;
          padding: 6px 14px; border: none; border-radius: 6px;
          background: var(--accent, #89b4fa); color: #11111b;
          font-size: 12px; font-weight: 600; cursor: pointer;
          transition: filter 0.15s;
        }
        .mp-import-btn:hover { filter: brightness(1.1); }
        .mp-filters {
          display: flex; gap: 4px; padding: 10px 20px;
          border-bottom: 1px solid var(--border, #333);
          overflow-x: auto;
        }
        .mp-filter-btn {
          padding: 5px 12px; border: 1px solid var(--border, #333);
          border-radius: 14px; background: transparent;
          color: var(--text-secondary, #888); font-size: 12px;
          cursor: pointer; white-space: nowrap; transition: all 0.15s;
        }
        .mp-filter-btn.active {
          border-color: var(--accent, #89b4fa); color: var(--accent, #89b4fa);
          background: rgba(137,180,250,0.08);
        }
        .mp-filter-btn:not(.active):hover {
          border-color: var(--text-secondary, #888);
          color: var(--text-primary, #cdd6f4);
        }
        .mp-list {
          flex: 1; overflow-y: auto; padding: 12px 16px;
          display: flex; flex-direction: column; gap: 8px;
        }
        .mp-card {
          display: flex; align-items: center; gap: 12px;
          padding: 12px 14px; border-radius: 8px;
          border: 1px solid var(--border, #333);
          background: var(--bg-secondary, #181825);
          cursor: pointer; transition: all 0.15s;
        }
        .mp-card:hover {
          border-color: var(--accent, #89b4fa);
          background: rgba(137,180,250,0.04);
        }
        .mp-card-icon {
          width: 36px; height: 36px; border-radius: 8px;
          display: flex; align-items: center; justify-content: center;
          flex-shrink: 0;
        }
        .mp-card-body {
          flex: 1; min-width: 0;
        }
        .mp-card-title {
          font-size: 13px; font-weight: 600;
          color: var(--text-primary, #cdd6f4);
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        .mp-card-meta {
          display: flex; align-items: center; gap: 10px;
          font-size: 11px; color: var(--text-secondary, #888);
          margin-top: 3px;
        }
        .mp-card-meta-item {
          display: flex; align-items: center; gap: 3px;
        }
        .mp-card-participants {
          display: flex; gap: 0; margin-left: auto;
        }
        .mp-avatar {
          width: 24px; height: 24px; border-radius: 50%;
          display: flex; align-items: center; justify-content: center;
          font-size: 9px; font-weight: 700; color: #11111b;
          border: 2px solid var(--bg-secondary, #181825);
          margin-left: -6px;
          flex-shrink: 0;
        }
        .mp-avatar:first-child { margin-left: 0; }
        .mp-action-badge {
          display: flex; align-items: center; gap: 3px;
          padding: 2px 8px; border-radius: 10px;
          background: rgba(166,227,161,0.12); color: #a6e3a1;
          font-size: 11px; font-weight: 600; flex-shrink: 0;
        }
        .mp-chevron {
          color: var(--text-secondary, #888); flex-shrink: 0;
          opacity: 0; transition: opacity 0.15s;
        }
        .mp-card:hover .mp-chevron { opacity: 1; }
        .mp-footer {
          display: flex; align-items: center; gap: 16px;
          padding: 10px 20px;
          border-top: 1px solid var(--border, #333);
          font-size: 11px; color: var(--text-secondary, #888);
        }
        .mp-footer-stat {
          display: flex; align-items: center; gap: 4px;
        }
        .mp-empty {
          flex: 1; display: flex; flex-direction: column;
          align-items: center; justify-content: center; gap: 10px;
          color: var(--text-secondary, #888); padding: 40px;
          text-align: center;
        }
        .mp-empty-icon { opacity: 0.3; }
        .mp-empty p { margin: 0; font-size: 13px; }
        .mp-empty .hint { font-size: 12px; opacity: 0.7; }
        .mp-empty-btn {
          margin-top: 8px; padding: 8px 18px; border: none;
          border-radius: 6px; background: var(--accent, #89b4fa);
          color: #11111b; font-size: 13px; font-weight: 600;
          cursor: pointer; display: flex; align-items: center; gap: 6px;
        }
        .mp-empty-btn:hover { filter: brightness(1.1); }
      `}</style>

      <div className="mp-wrapper">
        {/* Header */}
        <div className="mp-header">
          <div className="mp-header-left">
            <Video size={18} />
            <span>Meetings</span>
          </div>
          <button className="mp-import-btn" onClick={() => setImportOpen(true)}>
            <Plus size={14} /> Import Meeting
          </button>
        </div>

        {/* Filter bar */}
        <div className="mp-filters">
          {SOURCE_FILTERS.map((f) => (
            <button
              key={f.key}
              className={`mp-filter-btn ${filter === f.key ? "active" : ""}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Meeting list or empty state */}
        {filtered.length === 0 ? (
          <div className="mp-empty">
            <Video size={48} className="mp-empty-icon" />
            <p>
              {meetings.length === 0
                ? "No meeting notes yet"
                : `No ${filter} meetings found`}
            </p>
            <p className="hint">
              {meetings.length === 0
                ? "Import a meeting transcript to get started"
                : "Try a different filter or import a new meeting"}
            </p>
            {meetings.length === 0 && (
              <button className="mp-empty-btn" onClick={() => setImportOpen(true)}>
                <Plus size={14} /> Import Your First Meeting
              </button>
            )}
          </div>
        ) : (
          <div className="mp-list">
            {filtered.map((m) => (
              <div
                key={m.note.id}
                className="mp-card"
                onClick={() => handleOpenNote(m.note.id)}
              >
                {/* Source icon */}
                <div
                  className="mp-card-icon"
                  style={{ background: `${sourceColor(m.source)}18`, color: sourceColor(m.source) }}
                >
                  {sourceIcon(m.source, 18)}
                </div>

                {/* Body */}
                <div className="mp-card-body">
                  <div className="mp-card-title">{m.title}</div>
                  <div className="mp-card-meta">
                    <span className="mp-card-meta-item">
                      <Calendar size={11} /> {formatDate(m.date)}
                    </span>
                    {m.participants.length > 0 && (
                      <span className="mp-card-meta-item">
                        <Users size={11} /> {m.participants.length}
                      </span>
                    )}
                  </div>
                </div>

                {/* Participant avatars */}
                {m.participants.length > 0 && (
                  <div className="mp-card-participants">
                    {m.participants.slice(0, 4).map((p, i) => (
                      <div
                        key={i}
                        className="mp-avatar"
                        style={{ background: sourceColor(m.source) }}
                        title={p}
                      >
                        {getInitials(p)}
                      </div>
                    ))}
                    {m.participants.length > 4 && (
                      <div
                        className="mp-avatar"
                        style={{ background: "var(--bg-tertiary, #333)", color: "var(--text-secondary, #888)" }}
                      >
                        +{m.participants.length - 4}
                      </div>
                    )}
                  </div>
                )}

                {/* Action item badge */}
                {m.actionItemCount > 0 && (
                  <div className="mp-action-badge">
                    <CheckSquare size={11} /> {m.actionItemCount}
                  </div>
                )}

                <ChevronRight size={14} className="mp-chevron" />
              </div>
            ))}
          </div>
        )}

        {/* Footer stats */}
        {meetings.length > 0 && (
          <div className="mp-footer">
            <span className="mp-footer-stat">
              <Video size={12} /> {meetings.length} meeting{meetings.length !== 1 ? "s" : ""}
            </span>
            <span className="mp-footer-stat">
              <CheckSquare size={12} /> {totalActionItems} action item{totalActionItems !== 1 ? "s" : ""}
            </span>
          </div>
        )}
      </div>

      {/* Import modal */}
      <MeetingImportModal open={importOpen} onClose={() => setImportOpen(false)} />
    </>
  );
}
