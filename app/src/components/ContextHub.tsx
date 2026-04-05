import { useState, useEffect, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  LayoutDashboard, Brain, Calendar, CheckSquare, Link2, Bell,
  TrendingUp, Clock, AlertTriangle, RefreshCw, ChevronRight,
  FileText, Loader, Sparkles, Sun, Moon, Coffee, Save, Plus,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Briefing {
  summary: string;
  highlights: string[];
  attention_items: string[];
  themes: string[];
}

interface Connection {
  source: string;
  target: string;
  description: string;
  strength: number; // 0-1
}

interface TimelineEntry {
  noteId: string;
  title: string;
  source: string; // e.g. "daily", "meeting", "note"
  date: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getGreeting(): { text: string; icon: React.ReactNode } {
  const hour = new Date().getHours();
  if (hour < 12) return { text: "Good morning", icon: <Coffee size={20} /> };
  if (hour < 17) return { text: "Good afternoon", icon: <Sun size={20} /> };
  return { text: "Good evening", icon: <Moon size={20} /> };
}

function formatDate(d: Date): string {
  return d.toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function daysBetween(a: string, b: Date): number {
  const msPerDay = 86400000;
  return Math.floor((b.getTime() - new Date(a).getTime()) / msPerDay);
}

function groupByDay(entries: TimelineEntry[]): Map<string, TimelineEntry[]> {
  const map = new Map<string, TimelineEntry[]>();
  for (const e of entries) {
    const day = e.date.slice(0, 10);
    const arr = map.get(day) ?? [];
    arr.push(e);
    map.set(day, arr);
  }
  return map;
}

function sourceBadge(source: string): string {
  switch (source) {
    case "daily": return "Daily";
    case "meeting": return "Meeting";
    case "project": return "Project";
    default: return "Note";
  }
}

function inferSource(filePath: string): string {
  if (filePath.startsWith("daily/")) return "daily";
  if (filePath.includes("meeting")) return "meeting";
  if (filePath.includes("project")) return "project";
  return "note";
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/* parseActionItems and parseCalendarEvents removed —
   ContextHub now reads from central state (state.actionItems, state.calendarEvents)
   which are populated by the unified data pipeline. */

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function DashCard({
  icon,
  title,
  children,
  accentColor,
  action,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  accentColor?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="ctx-card"
      style={{ "--card-accent": accentColor ?? "var(--accent, #3b82f6)" } as React.CSSProperties}
    >
      <div className="ctx-card-header">
        <span className="ctx-card-icon">{icon}</span>
        <h3 className="ctx-card-title">{title}</h3>
        {action && <div className="ctx-card-action">{action}</div>}
      </div>
      <div className="ctx-card-body">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function ContextHub() {
  const { state, dispatch } = useApp();
  const notes = state.notes;
  const now = useMemo(() => new Date(), []);
  const greeting = useMemo(() => getGreeting(), []);

  // Briefing state
  const [briefingMode, setBriefingMode] = useState<"daily" | "weekly">("daily");
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);

  // Connections state
  const [connections, setConnections] = useState<Connection[]>([]);
  const [connectionsLoading, setConnectionsLoading] = useState(false);

  // Briefing save state
  const [savingBriefing, setSavingBriefing] = useState(false);

  /* ---- Quick Stats (from central state) ---- */
  const stats = useMemo(() => {
    const sevenDaysAgo = new Date(now.getTime() - 7 * 86400000);
    let wordsThisWeek = 0;

    for (const note of notes) {
      const updated = new Date(note.updated_at);
      if (updated >= sevenDaysAgo) {
        wordsThisWeek += wordCount(note.content);
      }
    }

    const pendingActions = state.actionItems.filter((i) => i.status === "pending").length;
    const todayISO = now.toISOString().slice(0, 10);
    const nextWeekISO = new Date(now.getTime() + 7 * 86400000).toISOString().slice(0, 10);
    const upcomingEventsCount = state.calendarEvents.filter(
      (e) => e.event_date >= todayISO && e.event_date <= nextWeekISO,
    ).length;

    return {
      totalNotes: notes.length,
      wordsThisWeek,
      pendingActions,
      upcomingEvents: upcomingEventsCount,
    };
  }, [notes, now, state.actionItems, state.calendarEvents]);

  /* ---- What's New (last 7 days) ---- */
  const whatsNew = useMemo(() => {
    const sevenDaysAgo = new Date(now.getTime() - 7 * 86400000);
    const entries: TimelineEntry[] = [];
    for (const note of notes) {
      const updated = new Date(note.updated_at);
      if (updated >= sevenDaysAgo) {
        entries.push({
          noteId: note.id,
          title: note.title,
          source: inferSource(note.file_path),
          date: note.updated_at,
        });
      }
    }
    entries.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    return groupByDay(entries);
  }, [notes, now]);

  /* ---- Action Items (from central state) ---- */
  const actionItems = useMemo(() => {
    const today = now.toISOString().slice(0, 10);
    const items = state.actionItems.map((item) => ({
      id: item.id,
      task: item.task,
      sourceNoteId: item.note_id,
      sourceTitle: item.source_title,
      deadline: item.deadline,
      priority: item.priority,
      completed: item.status === "completed",
    }));
    // Sort: overdue first, then by deadline, then pending before completed
    items.sort((a, b) => {
      if (a.completed !== b.completed) return a.completed ? 1 : -1;
      const aOverdue = a.deadline && a.deadline < today && !a.completed;
      const bOverdue = b.deadline && b.deadline < today && !b.completed;
      if (aOverdue && !bOverdue) return -1;
      if (!aOverdue && bOverdue) return 1;
      if (a.deadline && b.deadline) return a.deadline.localeCompare(b.deadline);
      if (a.deadline) return -1;
      return 1;
    });
    return items.slice(0, 8); // show top 8
  }, [state.actionItems, now]);

  /* ---- Upcoming Events (from central state) ---- */
  const upcomingEvents = useMemo(() => {
    const today = now.toISOString().slice(0, 10);
    const nextWeek = new Date(now.getTime() + 7 * 86400000).toISOString().slice(0, 10);
    return state.calendarEvents
      .filter((e) => e.event_date >= today && e.event_date <= nextWeek)
      .map((e) => ({
        id: e.id,
        title: e.title,
        date: e.event_date,
        sourceNoteId: e.note_id,
        sourceTitle: e.source_title,
        description: e.description,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [state.calendarEvents, now]);

  /* ---- API calls ---- */
  const generateBriefing = useCallback(async () => {
    setBriefingLoading(true);
    try {
      const data = await api.generateBriefing(
        notes.slice(0, 30).map((n) => ({
          id: n.id,
          title: n.title,
          content: n.content.slice(0, 2000),
          created_at: n.created_at,
          updated_at: n.updated_at,
        })),
        state.actionItems.map((i) => ({
          task: i.task,
          deadline: i.deadline,
          status: i.status,
          priority: i.priority,
        })),
        state.calendarEvents.map((e) => ({
          title: e.title,
          event_date: e.event_date,
          event_type: e.event_type,
        })),
        briefingMode,
      );
      setBriefing({
        summary: data.summary,
        highlights: data.highlights,
        attention_items: data.attention_needed,
        themes: data.themes,
      });
    } catch {
      // sidecar not available
    } finally {
      setBriefingLoading(false);
    }
  }, [briefingMode, notes, state.actionItems, state.calendarEvents]);

  const saveBriefingAsNote = useCallback(async () => {
    if (!briefing) return;
    setSavingBriefing(true);
    try {
      const todayISO = now.toISOString().slice(0, 10);
      const content = [
        `# ${briefingMode === "daily" ? "Daily" : "Weekly"} Briefing — ${todayISO}`,
        "",
        briefing.summary,
        "",
        "## Highlights",
        ...briefing.highlights.map((h) => `- ${h}`),
        "",
        "## Needs Attention",
        ...briefing.attention_items.map((a) => `- ${a}`),
        "",
        "## Themes",
        ...briefing.themes.map((t) => `- ${t}`),
      ].join("\n");

      const result = await createNoteAndProcess(
        `Briefing ${todayISO}`,
        content,
        dispatch,
        { source: "briefing" },
      );
      dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      console.error("Failed to save briefing:", err);
    } finally {
      setSavingBriefing(false);
    }
  }, [briefing, briefingMode, now, dispatch]);

  const findConnections = useCallback(async () => {
    setConnectionsLoading(true);
    try {
      const data = await api.findConnections(
        notes.slice(0, 30).map((n) => ({
          id: n.id,
          title: n.title,
          content: n.content.slice(0, 2000),
        })),
      );
      setConnections(
        (data.connections ?? []).map((c: Record<string, unknown>) => ({
          source: String(c.source_note_id || c.source || ""),
          target: String(c.target_note_id || c.target || ""),
          description: String(c.description || ""),
          strength: Number(c.strength || 0),
        })),
      );
    } catch {
      // sidecar not available
    } finally {
      setConnectionsLoading(false);
    }
  }, [notes]);

  const navigateToNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    },
    [dispatch],
  );

  const todayStr = now.toISOString().slice(0, 10);

  return (
    <div className="main-content" style={{ overflow: "auto" }}>
      {/* Header */}
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <LayoutDashboard size={14} style={{ marginRight: 6 }} />
          <span>Command Center</span>
        </div>
      </div>

      <div className="ctx-wrapper">
        {/* Greeting */}
        <div className="ctx-greeting">
          <div className="ctx-greeting-left">
            <span className="ctx-greeting-icon">{greeting.icon}</span>
            <div>
              <h1 className="ctx-greeting-text">{greeting.text}</h1>
              <p className="ctx-greeting-date">{formatDate(now)}</p>
            </div>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="ctx-stats-row">
          <div className="ctx-stat">
            <FileText size={16} className="ctx-stat-icon" />
            <span className="ctx-stat-value">{stats.totalNotes}</span>
            <span className="ctx-stat-label">Total Notes</span>
          </div>
          <div className="ctx-stat">
            <TrendingUp size={16} className="ctx-stat-icon" />
            <span className="ctx-stat-value">{stats.wordsThisWeek.toLocaleString()}</span>
            <span className="ctx-stat-label">Words This Week</span>
          </div>
          <div className="ctx-stat">
            <CheckSquare size={16} className="ctx-stat-icon" />
            <span className="ctx-stat-value">{stats.pendingActions}</span>
            <span className="ctx-stat-label">Pending Actions</span>
          </div>
          <div className="ctx-stat">
            <Calendar size={16} className="ctx-stat-icon" />
            <span className="ctx-stat-value">{stats.upcomingEvents}</span>
            <span className="ctx-stat-label">Upcoming Events</span>
          </div>
        </div>

        {/* Grid */}
        <div className="ctx-grid">
          {/* ---- AI Briefing ---- */}
          <DashCard
            icon={<Brain size={18} />}
            title="AI Briefing"
            accentColor="#8b5cf6"
            action={
              <div className="ctx-briefing-controls">
                <button
                  className={`ctx-toggle-btn ${briefingMode === "daily" ? "active" : ""}`}
                  onClick={() => setBriefingMode("daily")}
                >
                  Daily
                </button>
                <button
                  className={`ctx-toggle-btn ${briefingMode === "weekly" ? "active" : ""}`}
                  onClick={() => setBriefingMode("weekly")}
                >
                  Weekly
                </button>
              </div>
            }
          >
            {briefing ? (
              <div className="ctx-briefing">
                <p className="ctx-briefing-summary">{briefing.summary}</p>
                {briefing.highlights.length > 0 && (
                  <div className="ctx-briefing-section">
                    <h4><Sparkles size={12} /> Highlights</h4>
                    <ul>
                      {briefing.highlights.map((h, i) => (
                        <li key={i}>{h}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {briefing.attention_items.length > 0 && (
                  <div className="ctx-briefing-section">
                    <h4><AlertTriangle size={12} /> Needs Attention</h4>
                    <ul>
                      {briefing.attention_items.map((a, i) => (
                        <li key={i}>{a}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {briefing.themes.length > 0 && (
                  <div className="ctx-briefing-themes">
                    {briefing.themes.map((t, i) => (
                      <span key={i} className="ctx-theme-tag">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="ctx-briefing-empty">
                <Sparkles size={24} />
                <p>Generate an AI-powered briefing of your notes and activity.</p>
              </div>
            )}
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="ctx-generate-btn"
                onClick={generateBriefing}
                disabled={briefingLoading}
              >
                {briefingLoading ? (
                  <>
                    <RefreshCw size={14} className="ctx-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    Generate Briefing
                  </>
                )}
              </button>
              {briefing && (
                <button
                  className="ctx-generate-btn"
                  onClick={saveBriefingAsNote}
                  disabled={savingBriefing}
                  style={{ background: "rgba(16, 185, 129, 0.15)", color: "#10b981" }}
                >
                  <Save size={14} />
                  {savingBriefing ? "Saving..." : "Save as Note"}
                </button>
              )}
            </div>
          </DashCard>

          {/* ---- What's New ---- */}
          <DashCard
            icon={<Bell size={18} />}
            title="What's New"
            accentColor="#10b981"
          >
            {whatsNew.size > 0 ? (
              <div className="ctx-timeline">
                {Array.from(whatsNew.entries()).map(([day, entries]) => (
                  <div key={day} className="ctx-timeline-group">
                    <div className="ctx-timeline-day">
                      {day === todayStr
                        ? "Today"
                        : new Date(day + "T00:00:00").toLocaleDateString("en-US", {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                          })}
                    </div>
                    {entries.map((entry) => (
                      <div
                        key={entry.noteId}
                        className="ctx-timeline-item"
                        onClick={() => navigateToNote(entry.noteId)}
                      >
                        <FileText size={14} />
                        <span className="ctx-timeline-title">{entry.title}</span>
                        <span
                          className="ctx-source-badge"
                          data-source={entry.source}
                        >
                          {sourceBadge(entry.source)}
                        </span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            ) : (
              <p className="ctx-empty">No new notes in the last 7 days.</p>
            )}
          </DashCard>

          {/* ---- Action Items ---- */}
          <DashCard
            icon={<CheckSquare size={18} />}
            title="Action Items"
            accentColor="#f59e0b"
          >
            {actionItems.length > 0 ? (
              <div className="ctx-actions-list">
                {actionItems.map((item, i) => {
                  const isOverdue =
                    item.deadline &&
                    item.deadline < todayStr &&
                    !item.completed;
                  return (
                    <div
                      key={i}
                      className={`ctx-action-row ${item.completed ? "completed" : ""} ${isOverdue ? "overdue" : ""}`}
                    >
                      <span className="ctx-action-check">
                        {item.completed ? (
                          <CheckSquare size={14} />
                        ) : (
                          <Clock size={14} />
                        )}
                      </span>
                      <div className="ctx-action-info">
                        <span className="ctx-action-task">{item.task}</span>
                        <span
                          className="ctx-action-source"
                          onClick={() => navigateToNote(item.sourceNoteId)}
                        >
                          {item.sourceTitle}
                        </span>
                      </div>
                      {item.deadline && (
                        <span className={`ctx-action-deadline ${isOverdue ? "overdue" : ""}`}>
                          {isOverdue && <AlertTriangle size={10} />}
                          {item.deadline}
                        </span>
                      )}
                      <span className="ctx-priority-badge" data-priority={item.priority}>
                        {item.priority}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className="ctx-empty">No action items found across your notes.</p>
            )}
          </DashCard>

          {/* ---- Upcoming Events ---- */}
          <DashCard
            icon={<Calendar size={18} />}
            title="Upcoming Events"
            accentColor="#06b6d4"
          >
            {upcomingEvents.length > 0 ? (
              <div className="ctx-events-list">
                {upcomingEvents.map((ev) => (
                  <div
                    key={ev.id}
                    className="ctx-event-row"
                    onClick={() => navigateToNote(ev.sourceNoteId)}
                  >
                    <div className="ctx-event-date-col">
                      <span className="ctx-event-day">
                        {new Date(ev.date + "T00:00:00").toLocaleDateString("en-US", {
                          weekday: "short",
                        })}
                      </span>
                      <span className="ctx-event-num">
                        {new Date(ev.date + "T00:00:00").getDate()}
                      </span>
                    </div>
                    <div className="ctx-event-info">
                      <span className="ctx-event-title">{ev.title}</span>
                      {ev.description && (
                        <span className="ctx-event-time">
                          {ev.description}
                        </span>
                      )}
                    </div>
                    <ChevronRight size={14} className="ctx-event-arrow" />
                  </div>
                ))}
              </div>
            ) : (
              <p className="ctx-empty">No upcoming events in the next 7 days.</p>
            )}
          </DashCard>

          {/* ---- Connections ---- */}
          <DashCard
            icon={<Link2 size={18} />}
            title="Connections"
            accentColor="#ec4899"
            action={
              <button
                className="ctx-find-btn"
                onClick={findConnections}
                disabled={connectionsLoading}
              >
                {connectionsLoading ? (
                  <RefreshCw size={12} className="ctx-spin" />
                ) : (
                  <Sparkles size={12} />
                )}
                {connectionsLoading ? "Finding..." : "Find Connections"}
              </button>
            }
          >
            {connections.length > 0 ? (
              <div className="ctx-connections-list">
                {connections.map((conn, i) => (
                  <div key={i} className="ctx-connection-card">
                    <div className="ctx-connection-pair">
                      <span className="ctx-connection-node">{conn.source}</span>
                      <ChevronRight size={12} />
                      <span className="ctx-connection-node">{conn.target}</span>
                    </div>
                    <p className="ctx-connection-desc">{conn.description}</p>
                    <div className="ctx-strength-bar">
                      <div
                        className="ctx-strength-fill"
                        style={{ width: `${Math.round(conn.strength * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="ctx-briefing-empty">
                <Link2 size={24} />
                <p>Discover hidden connections between your notes using AI.</p>
              </div>
            )}
          </DashCard>
        </div>
      </div>

      <style>{`
        /* Wrapper */
        .ctx-wrapper {
          max-width: 960px;
          margin: 0 auto;
          padding: 24px 28px 48px;
        }

        /* Greeting */
        .ctx-greeting {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 24px;
        }
        .ctx-greeting-left {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .ctx-greeting-icon {
          color: var(--accent, #3b82f6);
          display: flex;
          align-items: center;
        }
        .ctx-greeting-text {
          margin: 0;
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ctx-greeting-date {
          margin: 2px 0 0;
          font-size: 0.82rem;
          color: var(--text-muted, #71717a);
        }

        /* Stats Row */
        .ctx-stats-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 24px;
        }
        .ctx-stat {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        .ctx-stat-icon {
          color: var(--accent, #3b82f6);
          margin-bottom: 4px;
        }
        .ctx-stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ctx-stat-label {
          font-size: 0.72rem;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        /* Grid */
        .ctx-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }

        /* Card */
        .ctx-card {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          padding: 20px;
          transition: border-color 0.15s;
        }
        .ctx-card:hover {
          border-color: var(--card-accent, var(--accent, #3b82f6));
        }
        .ctx-card-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }
        .ctx-card-icon {
          color: var(--card-accent, var(--accent, #3b82f6));
          display: flex;
          align-items: center;
        }
        .ctx-card-title {
          margin: 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .ctx-card-action {
          margin-left: auto;
          display: flex;
          align-items: center;
        }
        .ctx-card-body {
          font-size: 0.85rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.6;
        }

        /* Toggle buttons (daily/weekly) */
        .ctx-briefing-controls {
          display: flex;
          gap: 2px;
          background: var(--bg-tertiary, #0f0f12);
          border-radius: 6px;
          padding: 2px;
        }
        .ctx-toggle-btn {
          background: none;
          border: none;
          padding: 4px 12px;
          border-radius: 5px;
          font-size: 0.72rem;
          font-weight: 500;
          cursor: pointer;
          color: var(--text-muted, #71717a);
          transition: all 0.15s;
        }
        .ctx-toggle-btn.active {
          background: var(--accent, #3b82f6);
          color: #fff;
        }

        /* Briefing */
        .ctx-briefing-summary {
          margin: 0 0 12px;
          font-size: 0.85rem;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.6;
        }
        .ctx-briefing-section {
          margin-bottom: 12px;
        }
        .ctx-briefing-section h4 {
          margin: 0 0 6px;
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--text-secondary, #a1a1aa);
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .ctx-briefing-section ul {
          margin: 0;
          padding-left: 16px;
        }
        .ctx-briefing-section li {
          font-size: 0.82rem;
          color: var(--text-secondary, #a1a1aa);
          margin-bottom: 4px;
          line-height: 1.5;
        }
        .ctx-briefing-themes {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 10px;
        }
        .ctx-theme-tag {
          font-size: 0.72rem;
          padding: 3px 10px;
          border-radius: 12px;
          background: rgba(139, 92, 246, 0.12);
          color: #8b5cf6;
          font-weight: 500;
        }
        .ctx-briefing-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 16px 0;
          color: var(--text-muted, #71717a);
        }
        .ctx-briefing-empty svg {
          opacity: 0.3;
          margin-bottom: 8px;
        }
        .ctx-briefing-empty p {
          margin: 0;
          font-size: 0.82rem;
        }
        .ctx-generate-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          margin-top: 14px;
          padding: 8px 18px;
          border: none;
          border-radius: 8px;
          background: var(--accent, #3b82f6);
          color: #fff;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.15s, transform 0.1s;
          width: 100%;
          justify-content: center;
        }
        .ctx-generate-btn:hover { opacity: 0.9; }
        .ctx-generate-btn:active { transform: scale(0.97); }
        .ctx-generate-btn:disabled { opacity: 0.6; cursor: not-allowed; }

        /* Find connections btn */
        .ctx-find-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 4px 12px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: none;
          color: var(--text-muted, #a1a1aa);
          font-size: 0.72rem;
          font-weight: 500;
          cursor: pointer;
          transition: color 0.15s, border-color 0.15s;
        }
        .ctx-find-btn:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }
        .ctx-find-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Timeline (What's New) */
        .ctx-timeline {
          max-height: 280px;
          overflow-y: auto;
        }
        .ctx-timeline-group {
          margin-bottom: 12px;
        }
        .ctx-timeline-day {
          font-size: 0.72rem;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
          margin-bottom: 6px;
          padding-bottom: 4px;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .ctx-timeline-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 8px;
          border-radius: 6px;
          cursor: pointer;
          transition: background 0.12s;
        }
        .ctx-timeline-item:hover {
          background: var(--bg-tertiary, #0f0f12);
        }
        .ctx-timeline-item svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .ctx-timeline-title {
          flex: 1;
          font-size: 0.82rem;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ctx-source-badge {
          font-size: 0.65rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          padding: 2px 8px;
          border-radius: 6px;
          flex-shrink: 0;
        }
        .ctx-source-badge[data-source="daily"] {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }
        .ctx-source-badge[data-source="meeting"] {
          background: rgba(59, 130, 246, 0.15);
          color: #3b82f6;
        }
        .ctx-source-badge[data-source="project"] {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .ctx-source-badge[data-source="note"] {
          background: rgba(139, 92, 246, 0.15);
          color: #8b5cf6;
        }

        /* Action Items */
        .ctx-actions-list {
          max-height: 280px;
          overflow-y: auto;
        }
        .ctx-action-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 8px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .ctx-action-row:last-child { border-bottom: none; }
        .ctx-action-row.completed {
          opacity: 0.5;
        }
        .ctx-action-row.overdue .ctx-action-task {
          color: #ef4444;
        }
        .ctx-action-check {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          color: var(--text-muted, #71717a);
        }
        .ctx-action-row.completed .ctx-action-check {
          color: #10b981;
        }
        .ctx-action-info {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .ctx-action-task {
          font-size: 0.82rem;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ctx-action-source {
          font-size: 0.72rem;
          color: var(--accent, #3b82f6);
          cursor: pointer;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ctx-action-source:hover {
          text-decoration: underline;
        }
        .ctx-action-deadline {
          font-size: 0.72rem;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .ctx-action-deadline.overdue {
          color: #ef4444;
          font-weight: 600;
        }
        .ctx-priority-badge {
          font-size: 0.65rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          padding: 2px 8px;
          border-radius: 6px;
          flex-shrink: 0;
        }
        .ctx-priority-badge[data-priority="high"] {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .ctx-priority-badge[data-priority="medium"] {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .ctx-priority-badge[data-priority="low"] {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }

        /* Upcoming Events */
        .ctx-events-list {
          max-height: 280px;
          overflow-y: auto;
        }
        .ctx-event-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px;
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.12s;
          margin-bottom: 4px;
        }
        .ctx-event-row:hover {
          background: var(--bg-tertiary, #0f0f12);
        }
        .ctx-event-date-col {
          display: flex;
          flex-direction: column;
          align-items: center;
          min-width: 36px;
          flex-shrink: 0;
        }
        .ctx-event-day {
          font-size: 0.65rem;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
        }
        .ctx-event-num {
          font-size: 1.1rem;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ctx-event-info {
          flex: 1;
          min-width: 0;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .ctx-event-title {
          font-size: 0.82rem;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ctx-event-time {
          font-size: 0.72rem;
          color: var(--text-muted, #71717a);
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .ctx-event-arrow {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        /* Connections */
        .ctx-connections-list {
          max-height: 280px;
          overflow-y: auto;
        }
        .ctx-connection-card {
          padding: 10px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .ctx-connection-card:last-child { border-bottom: none; }
        .ctx-connection-pair {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }
        .ctx-connection-pair svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .ctx-connection-node {
          font-size: 0.82rem;
          font-weight: 500;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ctx-connection-desc {
          margin: 0 0 6px;
          font-size: 0.78rem;
          color: var(--text-muted, #71717a);
        }
        .ctx-strength-bar {
          height: 4px;
          background: var(--bg-tertiary, #0f0f12);
          border-radius: 2px;
          overflow: hidden;
        }
        .ctx-strength-fill {
          height: 100%;
          background: #ec4899;
          border-radius: 2px;
          transition: width 0.4s ease;
        }

        /* Spin animation */
        @keyframes ctx-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .ctx-spin {
          animation: ctx-spin 1s linear infinite;
        }

        /* Empty text */
        .ctx-empty {
          color: var(--text-muted, #71717a);
          font-size: 0.82rem;
          font-style: italic;
          margin: 0;
        }

        /* Responsive */
        @media (max-width: 700px) {
          .ctx-stats-row {
            grid-template-columns: repeat(2, 1fr);
          }
          .ctx-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
