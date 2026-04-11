/**
 * BrainHome.tsx — The Brain Homepage
 *
 * This is the first thing users see when they open Einstein.
 * Shows: Today's Focus, Active Projects, Waiting On, Needs Attention,
 * Recent Activity, and AI Briefing — all from central state.
 *
 * Replaces ContextHub as the primary dashboard.
 */

import { useState, useEffect, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { PrepPack, Note } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  Home, Target, Users, Scale, CheckSquare, Calendar, Clock,
  AlertTriangle, TrendingUp, FileText, Plus, ChevronRight,
  Brain, Sun, Moon, Coffee, Loader, Sparkles, Save, Send,
  Eye, Zap, Archive, Newspaper, CalendarDays, Bell, Heart,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function getGreeting(): { text: string; icon: React.ReactNode } {
  const hour = new Date().getHours();
  if (hour < 12) return { text: "Good morning", icon: <Coffee size={20} /> };
  if (hour < 17) return { text: "Good afternoon", icon: <Sun size={20} /> };
  return { text: "Good evening", icon: <Moon size={20} /> };
}

function formatRelativeDate(dateStr: string): string {
  const now = new Date();
  const d = new Date(dateStr);
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function isOverdue(deadline: string | null): boolean {
  if (!deadline) return false;
  return new Date(deadline) < new Date(new Date().toDateString());
}

function isDueToday(deadline: string | null): boolean {
  if (!deadline) return false;
  return deadline.slice(0, 10) === new Date().toISOString().slice(0, 10);
}

function isDueThisWeek(deadline: string | null): boolean {
  if (!deadline) return false;
  const d = new Date(deadline);
  const now = new Date();
  const endOfWeek = new Date(now);
  endOfWeek.setDate(endOfWeek.getDate() + 7);
  return d >= now && d <= endOfWeek;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function BrainHome() {
  const { state, dispatch } = useApp();
  const [briefing, setBriefing] = useState<{
    summary: string;
    highlights: string[];
    attention_needed: string[];
    themes: string[];
  } | null>(null);
  const [briefingLoading, setBriefingLoading] = useState(false);
  const [quickCapture, setQuickCapture] = useState("");
  const [captureStatus, setCaptureStatus] = useState<string | null>(null);
  const [staleNotes, setStaleNotes] = useState<Note[]>([]);
  const [prepPack, setPrepPack] = useState<PrepPack | null>(null);
  const [prepLoading, setPrepLoading] = useState(false);
  const [morningBriefing, setMorningBriefing] = useState<any>(null);
  const [morningBriefingLoading, setMorningBriefingLoading] = useState(false);
  const [meetingPreps, setMeetingPreps] = useState<any[]>([]);
  const [followUps, setFollowUps] = useState<any[]>([]);
  const [relationshipDashboard, setRelationshipDashboard] = useState<any>(null);

  const greeting = useMemo(() => getGreeting(), []);
  const today = useMemo(() => new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  }), []);

  // --- Load stale notes from DB ---
  useEffect(() => {
    api.getStaleNotes(14).then(setStaleNotes).catch(() => setStaleNotes([]));
  }, []);

  // --- Load morning briefing ---
  useEffect(() => {
    setMorningBriefingLoading(true);
    api.getMorningBriefing()
      .then(data => setMorningBriefing(data))
      .catch(() => setMorningBriefing(null))
      .finally(() => setMorningBriefingLoading(false));
  }, []);

  // --- Load meeting preps ---
  useEffect(() => {
    api.getUpcomingBriefings()
      .then(data => setMeetingPreps(data || []))
      .catch(() => setMeetingPreps([]));
  }, []);

  // --- Load follow-ups ---
  useEffect(() => {
    api.getFollowUps()
      .then(data => setFollowUps(data || []))
      .catch(() => setFollowUps([]));
  }, []);

  // --- Load relationship dashboard ---
  useEffect(() => {
    api.getRelationshipDashboard()
      .then(data => setRelationshipDashboard(data))
      .catch(() => setRelationshipDashboard(null));
  }, []);

  // --- Prepare for Today ---
  const generatePrepPack = useCallback(async () => {
    setPrepLoading(true);
    try {
      const recentNotes = state.notes
        .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
        .slice(0, 15)
        .map((n) => ({ id: n.id, title: n.title, content: n.content.slice(0, 500), updated_at: n.updated_at }));

      const pendingActions = state.actionItems
        .filter((a) => a.status === "pending")
        .map((a) => ({ task: a.task, deadline: a.deadline, priority: a.priority, assignee: a.assignee }));

      const activeDecisions = state.decisions
        .filter((d) => d.status === "active")
        .map((d) => ({ title: d.title, description: d.description, status: d.status, revisit_date: d.revisit_date }));

      const result = await api.prepareContext("day", {}, recentNotes, pendingActions, activeDecisions);
      setPrepPack(result);
    } catch (err) {
      console.error("Prep pack failed:", err);
    }
    setPrepLoading(false);
  }, [state.notes, state.actionItems, state.decisions]);

  // --- Computed data from central state ---

  const todaysFocus = useMemo(() => {
    const items: Array<{ type: string; title: string; subtitle?: string; id: string }> = [];
    // Overdue + due today action items
    state.actionItems
      .filter((a) => a.status === "pending" && (isOverdue(a.deadline) || isDueToday(a.deadline)))
      .forEach((a) => items.push({
        type: "action",
        title: a.task,
        subtitle: isOverdue(a.deadline) ? "Overdue" : "Due today",
        id: a.id,
      }));
    // Calendar events today
    const todayStr = new Date().toISOString().slice(0, 10);
    state.calendarEvents
      .filter((e) => e.event_date.slice(0, 10) === todayStr)
      .forEach((e) => items.push({
        type: "event",
        title: e.title,
        subtitle: e.event_type,
        id: e.id,
      }));
    return items;
  }, [state.actionItems, state.calendarEvents]);

  const thisWeek = useMemo(() => {
    const items: Array<{ type: string; title: string; subtitle?: string; id: string }> = [];
    state.actionItems
      .filter((a) => a.status === "pending" && isDueThisWeek(a.deadline) && !isDueToday(a.deadline))
      .forEach((a) => items.push({
        type: "action",
        title: a.task,
        subtitle: `Due ${a.deadline?.slice(0, 10)}`,
        id: a.id,
      }));
    state.projects
      .filter((p) => p.status === "active" && isDueThisWeek(p.deadline))
      .forEach((p) => items.push({
        type: "project",
        title: p.title,
        subtitle: `Deadline ${p.deadline?.slice(0, 10)}`,
        id: p.id,
      }));
    state.decisions
      .filter((d) => d.status === "active" && isDueThisWeek(d.revisit_date))
      .forEach((d) => items.push({
        type: "decision",
        title: d.title,
        subtitle: "Revisit this week",
        id: d.id,
      }));
    return items;
  }, [state.actionItems, state.projects, state.decisions]);

  const activeProjects = useMemo(() => {
    return state.projects
      .filter((p) => p.status === "active")
      .map((p) => {
        // Count notes that mention this project title
        const noteCount = state.notes.filter((n) =>
          n.content.toLowerCase().includes(p.title.toLowerCase())
        ).length;
        return { ...p, noteCount };
      })
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 6);
  }, [state.projects, state.notes]);

  const waitingOn = useMemo(() => {
    return state.actionItems
      .filter((a) => a.status === "pending" && a.assignee)
      .map((a) => ({
        task: a.task,
        assignee: a.assignee!,
        source: a.source_title,
        id: a.id,
      }))
      .slice(0, 8);
  }, [state.actionItems]);

  const needsAttention = useMemo(() => {
    const items: Array<{ type: string; title: string; subtitle: string; id: string }> = [];
    // Overdue actions
    state.actionItems
      .filter((a) => a.status === "pending" && isOverdue(a.deadline))
      .forEach((a) => items.push({
        type: "overdue",
        title: a.task,
        subtitle: `Overdue since ${a.deadline?.slice(0, 10)}`,
        id: a.id,
      }));
    // Decisions past revisit date
    state.decisions
      .filter((d) => d.status === "active" && d.revisit_date && isOverdue(d.revisit_date))
      .forEach((d) => items.push({
        type: "revisit",
        title: d.title,
        subtitle: `Revisit was ${d.revisit_date?.slice(0, 10)}`,
        id: d.id,
      }));
    // Overdue projects
    state.projects
      .filter((p) => p.status === "active" && isOverdue(p.deadline))
      .forEach((p) => items.push({
        type: "project_overdue",
        title: p.title,
        subtitle: `Deadline was ${p.deadline?.slice(0, 10)}`,
        id: p.id,
      }));
    // Stale notes (not edited in 14+ days)
    staleNotes.slice(0, 5).forEach((n) => items.push({
      type: "stale",
      title: n.title,
      subtitle: `Last edited ${formatRelativeDate(n.updated_at)}`,
      id: n.id,
    }));
    return items;
  }, [state.actionItems, state.decisions, state.projects, staleNotes]);

  const recentActivity = useMemo(() => {
    return [...state.notes]
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 8)
      .map((n) => ({
        id: n.id,
        title: n.title,
        date: formatRelativeDate(n.updated_at),
        source: n.file_path.split("/")[0] || "notes",
      }));
  }, [state.notes]);

  // --- Quick Capture ---

  const handleQuickCapture = useCallback(async () => {
    if (!quickCapture.trim()) return;
    setCaptureStatus("Saving...");
    try {
      const title = `Quick Capture — ${new Date().toISOString().slice(0, 16).replace("T", " ")}`;
      const result = await createNoteAndProcess(title, quickCapture, dispatch, { source: "quick-capture" });
      dispatch({ type: "UPDATE_NOTE", note: result.note });
      setQuickCapture("");
      setCaptureStatus("Saved!");
      setTimeout(() => setCaptureStatus(null), 2000);
    } catch (err) {
      console.error("Quick capture failed:", err);
      setCaptureStatus("Failed");
      setTimeout(() => setCaptureStatus(null), 2000);
    }
  }, [quickCapture, dispatch]);

  // --- Briefing ---

  const generateBriefing = useCallback(async (period: string = "daily") => {
    setBriefingLoading(true);
    try {
      const recentNotes = state.notes
        .filter((n) => {
          const days = Math.floor((Date.now() - new Date(n.updated_at).getTime()) / 86400000);
          return days <= (period === "weekly" ? 7 : 1);
        })
        .slice(0, 15)
        .map((n) => ({ id: n.id, title: n.title, content: n.content.slice(0, 500) }));

      const result = await api.generateBriefing(
        recentNotes,
        state.actionItems.filter((a) => a.status === "pending").map((a) => ({ task: a.task, deadline: a.deadline, priority: a.priority })),
        state.calendarEvents.slice(0, 10).map((e) => ({ title: e.title, event_date: e.event_date, event_type: e.event_type })),
        period
      );
      setBriefing(result);
    } catch (err) {
      console.error("Briefing failed:", err);
    }
    setBriefingLoading(false);
  }, [state.notes, state.actionItems, state.calendarEvents]);

  // --- Stats ---

  const stats = useMemo(() => ({
    totalNotes: state.notes.length,
    activeProjects: state.projects.filter((p) => p.status === "active").length,
    pendingActions: state.actionItems.filter((a) => a.status === "pending").length,
    peopleTracked: state.people.length,
  }), [state.notes, state.projects, state.actionItems, state.people]);

  return (
    <div className="bh-container">
      {/* --- Greeting + Quick Capture --- */}
      <div className="bh-header">
        <div className="bh-greeting">
          {greeting.icon}
          <div>
            <h1 className="bh-greeting-text">{greeting.text}</h1>
            <p className="bh-date">{today}</p>
          </div>
        </div>
        <div className="bh-quick-capture">
          <input
            className="bh-capture-input"
            placeholder="Quick capture — type anything and press Enter..."
            value={quickCapture}
            onChange={(e) => setQuickCapture(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleQuickCapture()}
          />
          {captureStatus && <span className="bh-capture-status">{captureStatus}</span>}
          {quickCapture && (
            <button className="bh-capture-btn" onClick={handleQuickCapture}>
              <Send size={14} />
            </button>
          )}
        </div>
      </div>

      {/* --- Stats Bar --- */}
      <div className="bh-stats">
        <div className="bh-stat">
          <FileText size={16} />
          <span className="bh-stat-value">{stats.totalNotes}</span>
          <span className="bh-stat-label">Notes</span>
        </div>
        <div className="bh-stat">
          <Target size={16} />
          <span className="bh-stat-value">{stats.activeProjects}</span>
          <span className="bh-stat-label">Projects</span>
        </div>
        <div className="bh-stat">
          <CheckSquare size={16} />
          <span className="bh-stat-value">{stats.pendingActions}</span>
          <span className="bh-stat-label">Actions</span>
        </div>
        <div className="bh-stat">
          <Users size={16} />
          <span className="bh-stat-value">{stats.peopleTracked}</span>
          <span className="bh-stat-label">People</span>
        </div>
      </div>

      {/* --- Main Grid --- */}
      <div className="bh-grid">
        {/* Morning Briefing */}
        {morningBriefing && (
          <div className="bh-card bh-card-wide bh-briefing-card">
            <div className="bh-card-header">
              <Newspaper size={16} />
              <h3>Morning Briefing</h3>
            </div>
            <div className="bh-briefing-content">
              {morningBriefing.summary && <p className="bh-briefing-summary">{morningBriefing.summary}</p>}
              {morningBriefing.highlights?.length > 0 && (
                <div className="bh-briefing-section">
                  <h4>Highlights</h4>
                  <ul>{morningBriefing.highlights.map((h: string, i: number) => <li key={i}>{h}</li>)}</ul>
                </div>
              )}
              {morningBriefing.attention_needed?.length > 0 && (
                <div className="bh-briefing-section">
                  <h4>Needs Attention</h4>
                  <ul>{morningBriefing.attention_needed.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Upcoming Meetings */}
        {meetingPreps.length > 0 && (
          <div className="bh-card">
            <div className="bh-card-header">
              <CalendarDays size={16} />
              <h3>Upcoming Meetings</h3>
            </div>
            <div className="bh-meetings-list">
              {meetingPreps.slice(0, 3).map((m: any, i: number) => (
                <div key={i} className="bh-meeting-item">
                  <div className="bh-meeting-title">{m.meeting_title}</div>
                  <div className="bh-meeting-time">{m.meeting_time}</div>
                  {m.attendees?.length > 0 && (
                    <div className="bh-meeting-attendees">
                      {m.attendees.map((a: any, j: number) => (
                        <span key={j} className="bh-attendee-badge">{a.name}</span>
                      ))}
                    </div>
                  )}
                  {m.suggested_agenda?.length > 0 && (
                    <div className="bh-meeting-agenda">
                      {m.suggested_agenda.slice(0, 3).map((a: string, j: number) => (
                        <div key={j} className="bh-agenda-item">{a}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Follow-ups */}
        {followUps.length > 0 && (
          <div className="bh-card">
            <div className="bh-card-header">
              <Bell size={16} />
              <h3>Follow-ups ({followUps.length})</h3>
            </div>
            <div className="bh-followups-list">
              {followUps.slice(0, 5).map((f: any, i: number) => (
                <div key={i} className={`bh-followup-item bh-followup--${f.priority || 'medium'}`}>
                  <div className="bh-followup-title">{f.title}</div>
                  <div className="bh-followup-desc">{f.description}</div>
                  {f.person && <span className="bh-followup-person">{f.person}</span>}
                  <div className="bh-followup-action">{f.suggested_action}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Relationships Needing Attention */}
        {relationshipDashboard?.declining?.length > 0 && (
          <div className="bh-card">
            <div className="bh-card-header">
              <Heart size={16} />
              <h3>Relationships Needing Attention</h3>
            </div>
            <div className="bh-relationships-list">
              {relationshipDashboard.declining.slice(0, 5).map((r: any, i: number) => (
                <div key={i} className="bh-relationship-item" onClick={() => {
                  if (r.person_id) dispatch({ type: "SET_CONTEXT_MODE", payload: { type: "person", id: r.person_id } });
                }}>
                  <div className="bh-rel-name">{r.person_name}</div>
                  <div className="bh-rel-score">
                    <div className="bh-rel-bar" style={{ width: `${r.score}%` }} />
                    <span>{r.score}/100</span>
                  </div>
                  <div className="bh-rel-grade">{r.grade}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Today's Focus */}
        <div className="bh-card">
          <div className="bh-card-header">
            <CheckSquare size={16} />
            <span>Today's Focus</span>
            <span className="bh-card-count">{todaysFocus.length}</span>
          </div>
          <div className="bh-card-body">
            {todaysFocus.length === 0 && (
              <p className="bh-empty">Nothing urgent today</p>
            )}
            {todaysFocus.map((item) => (
              <div key={item.id} className="bh-list-item">
                <span className={`bh-badge bh-badge-${item.type === "action" ? "warn" : "info"}`}>
                  {item.subtitle}
                </span>
                <span className="bh-list-title">{item.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* This Week */}
        <div className="bh-card">
          <div className="bh-card-header">
            <Calendar size={16} />
            <span>This Week</span>
            <span className="bh-card-count">{thisWeek.length}</span>
          </div>
          <div className="bh-card-body">
            {thisWeek.length === 0 && (
              <p className="bh-empty">Clear week ahead</p>
            )}
            {thisWeek.map((item) => (
              <div key={item.id} className="bh-list-item">
                <span className="bh-list-subtitle">{item.subtitle}</span>
                <span className="bh-list-title">{item.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Active Projects */}
        <div className="bh-card bh-card-wide">
          <div className="bh-card-header">
            <Target size={16} />
            <span>Active Projects</span>
            <span className="bh-card-count">{activeProjects.length}</span>
            <button
              className="bh-card-action"
              onClick={() => window.dispatchEvent(new CustomEvent("einstein-create-project"))}
            >
              <Plus size={14} /> New
            </button>
          </div>
          <div className="bh-card-body bh-projects-grid">
            {activeProjects.length === 0 && (
              <p className="bh-empty">No active projects — create one to get started</p>
            )}
            {activeProjects.map((p) => (
              <button
                key={p.id}
                className="bh-project-card"
                onClick={() => dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "project", projectId: p.id } })}
              >
                <span className="bh-project-title">{p.title}</span>
                {p.category && <span className="bh-project-category">{p.category}</span>}
                <div className="bh-project-meta">
                  {p.noteCount > 0 && <span className="bh-project-stat"><FileText size={10} /> {p.noteCount} notes</span>}
                  {p.deadline && (
                    <span className={`bh-project-deadline ${isOverdue(p.deadline) ? "bh-overdue" : ""}`}>
                      {isOverdue(p.deadline) ? "Overdue" : `Due ${p.deadline.slice(0, 10)}`}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Waiting On */}
        <div className="bh-card">
          <div className="bh-card-header">
            <Clock size={16} />
            <span>Waiting On</span>
            <span className="bh-card-count">{waitingOn.length}</span>
          </div>
          <div className="bh-card-body">
            {waitingOn.length === 0 && (
              <p className="bh-empty">Nothing pending from others</p>
            )}
            {waitingOn.map((item) => (
              <div key={item.id} className="bh-list-item">
                <span className="bh-assignee">{item.assignee}</span>
                <span className="bh-list-title">{item.task}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Needs Attention */}
        <div className="bh-card">
          <div className="bh-card-header">
            <AlertTriangle size={16} />
            <span>Needs Attention</span>
            {needsAttention.length > 0 && (
              <span className="bh-card-count bh-count-warn">{needsAttention.length}</span>
            )}
          </div>
          <div className="bh-card-body">
            {needsAttention.length === 0 && (
              <p className="bh-empty">Everything looks good</p>
            )}
            {needsAttention.map((item) => (
              <div key={item.id} className="bh-list-item bh-attention-item">
                <span className="bh-badge bh-badge-danger">{item.type.replace("_", " ")}</span>
                <span className="bh-list-title">{item.title}</span>
                <span className="bh-list-subtitle">{item.subtitle}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Predictions */}
        <div className="bh-card bh-card-wide">
          <div className="bh-card-header">
            <Sparkles size={16} />
            <span>Predictions</span>
          </div>
          <div className="bh-card-body bh-predictions-grid">
            {/* Activity Outlook */}
            <div className="bh-prediction-card">
              <div className="bh-prediction-icon bh-pred-activity">
                <TrendingUp size={16} />
              </div>
              <div className="bh-prediction-content">
                <h4 className="bh-prediction-title">Activity Outlook</h4>
                <p className="bh-prediction-text">
                  {state.predictionSummary?.activity_summary
                    ? (state.predictionSummary.activity_summary.trend === "increasing"
                        ? "Busy period ahead — activity is trending up"
                        : state.predictionSummary.activity_summary.trend === "decreasing"
                          ? "Quieter week ahead — activity is trending down"
                          : "Steady pace expected — activity is stable")
                    : "Gathering activity data..."}
                </p>
              </div>
            </div>

            {/* Emerging Topics */}
            <div className="bh-prediction-card">
              <div className="bh-prediction-icon bh-pred-topics">
                <Eye size={16} />
              </div>
              <div className="bh-prediction-content">
                <h4 className="bh-prediction-title">Emerging Topics</h4>
                {state.predictionSummary?.entity_summary && state.predictionSummary.entity_summary.top_emerging.length > 0 ? (
                  <div className="bh-emerging-list">
                    {state.predictionSummary.entity_summary.top_emerging.slice(0, 3).map((name: string, i: number) => (
                      <span key={i} className="bh-emerging-item">
                        <span className="bh-trend-arrow bh-trend-up">{"\u2191"}</span>
                        {name.includes(":") ? name.split(":")[1] : name}
                      </span>
                    ))}
                    {state.predictionSummary.entity_summary.fading_count > 0 && (
                      <span className="bh-emerging-item">
                        <span className="bh-trend-arrow bh-trend-down">{"\u2193"}</span>
                        {state.predictionSummary.entity_summary.fading_count} fading
                      </span>
                    )}
                  </div>
                ) : (
                  <p className="bh-prediction-text">No emerging topics yet</p>
                )}
              </div>
            </div>

            {/* Dormancy Risk */}
            <div className="bh-prediction-card">
              <div className="bh-prediction-icon bh-pred-dormancy">
                <AlertTriangle size={16} />
              </div>
              <div className="bh-prediction-content">
                <h4 className="bh-prediction-title">Dormancy Risk</h4>
                {state.dormancyRisk.length > 0 ? (
                  <div className="bh-dormancy-list">
                    {state.dormancyRisk.slice(0, 3).map((entry) => (
                      <button
                        key={entry.id}
                        className="bh-dormancy-item"
                        onClick={() =>
                          dispatch({
                            type: "SET_CONTEXT_MODE",
                            mode: entry.type === "person"
                              ? { type: "person", personId: entry.id }
                              : { type: "project", projectId: entry.id },
                          })
                        }
                      >
                        <span className={`bh-risk-dot bh-risk-${entry.risk_level}`} />
                        <span className="bh-dormancy-name">{entry.name}</span>
                        <span className="bh-dormancy-days">{entry.days_until_dormant}d left</span>
                      </button>
                    ))}
                  </div>
                ) : (
                  <p className="bh-prediction-text">All connections healthy</p>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bh-card bh-card-wide">
          <div className="bh-card-header">
            <TrendingUp size={16} />
            <span>Recent Activity</span>
          </div>
          <div className="bh-card-body">
            {recentActivity.map((item) => (
              <button
                key={item.id}
                className="bh-activity-item"
                onClick={() => {
                  dispatch({ type: "SET_ACTIVE_NOTE", id: item.id });
                  dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
                }}
              >
                <FileText size={14} />
                <span className="bh-activity-title">{item.title}</span>
                <span className="bh-activity-source">{item.source}</span>
                <span className="bh-activity-date">{item.date}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Prep Pack — Prepare for Today */}
        <div className="bh-card bh-card-wide">
          <div className="bh-card-header">
            <Zap size={16} />
            <span>Prepare for Today</span>
            <button
              className="bh-card-action"
              onClick={generatePrepPack}
              disabled={prepLoading}
            >
              {prepLoading ? <Loader size={14} className="bh-spin" /> : <Sparkles size={14} />}
              Generate
            </button>
          </div>
          <div className="bh-card-body">
            {!prepPack && !prepLoading && (
              <p className="bh-empty">Click "Generate" for an AI-powered daily prep brief</p>
            )}
            {prepPack && prepPack.summary && (
              <div className="bh-prep">
                <p className="bh-prep-summary">{prepPack.summary}</p>
                {prepPack.key_points.length > 0 && (
                  <div className="bh-prep-section">
                    <h4>Key Points</h4>
                    <ul>{prepPack.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
                  </div>
                )}
                {prepPack.open_questions.length > 0 && (
                  <div className="bh-prep-section">
                    <h4>Open Questions</h4>
                    <ul>{prepPack.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul>
                  </div>
                )}
                {prepPack.suggested_actions.length > 0 && (
                  <div className="bh-prep-section">
                    <h4>Suggested Actions</h4>
                    <ul>{prepPack.suggested_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
                  </div>
                )}
                {prepPack.relevant_history.length > 0 && (
                  <div className="bh-prep-section">
                    <h4>Relevant History</h4>
                    <ul>{prepPack.relevant_history.map((h, i) => <li key={i}>{h}</li>)}</ul>
                  </div>
                )}
                <button
                  className="bh-card-action"
                  style={{ marginTop: 12 }}
                  onClick={async () => {
                    const content = `# Daily Prep — ${new Date().toISOString().slice(0, 10)}\n\n${prepPack.summary}\n\n## Key Points\n${prepPack.key_points.map((p) => `- ${p}`).join("\n")}\n\n## Open Questions\n${prepPack.open_questions.map((q) => `- ${q}`).join("\n")}\n\n## Suggested Actions\n${prepPack.suggested_actions.map((a) => `- ${a}`).join("\n")}`;
                    await createNoteAndProcess(`Daily Prep — ${new Date().toISOString().slice(0, 10)}`, content, dispatch, { source: "prep-pack" });
                  }}
                >
                  <Save size={14} /> Save as Note
                </button>
              </div>
            )}
          </div>
        </div>

        {/* AI Briefing */}
        <div className="bh-card bh-card-wide">
          <div className="bh-card-header">
            <Brain size={16} />
            <span>AI Briefing</span>
            <div className="bh-briefing-actions">
              <button
                className="bh-card-action"
                onClick={() => generateBriefing("daily")}
                disabled={briefingLoading}
              >
                {briefingLoading ? <Loader size={14} className="bh-spin" /> : <Sparkles size={14} />}
                Daily
              </button>
              <button
                className="bh-card-action"
                onClick={() => generateBriefing("weekly")}
                disabled={briefingLoading}
              >
                Weekly
              </button>
            </div>
          </div>
          <div className="bh-card-body">
            {!briefing && !briefingLoading && (
              <p className="bh-empty">Click "Daily" or "Weekly" to generate your AI briefing</p>
            )}
            {briefing && (
              <div className="bh-briefing">
                <p className="bh-briefing-summary">{briefing.summary}</p>
                {briefing.highlights.length > 0 && (
                  <div className="bh-briefing-section">
                    <h4>Highlights</h4>
                    <ul>
                      {briefing.highlights.map((h, i) => <li key={i}>{h}</li>)}
                    </ul>
                  </div>
                )}
                {briefing.attention_needed.length > 0 && (
                  <div className="bh-briefing-section">
                    <h4>Attention Needed</h4>
                    <ul>
                      {briefing.attention_needed.map((a, i) => <li key={i}>{a}</li>)}
                    </ul>
                  </div>
                )}
                {briefing.themes.length > 0 && (
                  <div className="bh-briefing-section">
                    <h4>Themes</h4>
                    <div className="bh-themes">
                      {briefing.themes.map((t, i) => (
                        <span key={i} className="bh-theme-tag">{t}</span>
                      ))}
                    </div>
                  </div>
                )}
                <button
                  className="bh-card-action"
                  style={{ marginTop: 12 }}
                  onClick={async () => {
                    const content = `# AI Briefing — ${new Date().toISOString().slice(0, 10)}\n\n${briefing.summary}\n\n## Highlights\n${briefing.highlights.map((h) => `- ${h}`).join("\n")}\n\n## Attention\n${briefing.attention_needed.map((a) => `- ${a}`).join("\n")}\n\n## Themes\n${briefing.themes.join(", ")}`;
                    await createNoteAndProcess(`Briefing — ${new Date().toISOString().slice(0, 10)}`, content, dispatch, { source: "briefing" });
                  }}
                >
                  <Save size={14} /> Save as Note
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <style>{`
        .bh-container {
          padding: 24px 32px;
          max-width: none;
          margin: 0;
          overflow-y: auto;
          height: 100%;
        }
        .bh-header {
          margin-bottom: 20px;
        }
        .bh-greeting {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 16px;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-greeting-text {
          font-size: 22px;
          font-weight: 600;
          margin: 0;
        }
        .bh-date {
          font-size: 13px;
          color: var(--text-muted, #71717a);
          margin: 2px 0 0;
        }
        .bh-quick-capture {
          display: flex;
          align-items: center;
          gap: 8px;
          position: relative;
        }
        .bh-capture-input {
          flex: 1;
          padding: 10px 14px;
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          background: var(--bg-secondary, #27272a);
          color: var(--text-primary, #e4e4e7);
          font-size: 14px;
          outline: none;
          transition: border-color 0.15s;
        }
        .bh-capture-input:focus {
          border-color: var(--accent, #3b82f6);
        }
        .bh-capture-input::placeholder {
          color: var(--text-muted, #71717a);
        }
        .bh-capture-btn {
          padding: 8px 12px;
          border: none;
          border-radius: 8px;
          background: var(--accent, #3b82f6);
          color: white;
          cursor: pointer;
          display: flex;
          align-items: center;
        }
        .bh-capture-status {
          font-size: 12px;
          color: #10b981;
          font-weight: 500;
          position: absolute;
          right: 50px;
        }

        .bh-stats {
          display: flex;
          gap: 16px;
          margin-bottom: 20px;
        }
        .bh-stat {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 16px;
          background: var(--bg-secondary, #27272a);
          border-radius: 8px;
          border: 1px solid var(--border, #27272a);
          flex: 1;
        }
        .bh-stat svg { color: var(--text-muted, #71717a); }
        .bh-stat-value {
          font-size: 18px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-stat-label {
          font-size: 12px;
          color: var(--text-muted, #71717a);
        }

        .bh-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 16px;
        }
        .bh-card {
          background: var(--bg-secondary, #27272a);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          overflow: hidden;
        }
        .bh-card-wide {
          grid-column: 1 / -1;
        }
        .bh-card-header {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 12px 16px;
          border-bottom: 1px solid var(--border, #27272a);
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-card-header svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .bh-card-count {
          margin-left: auto;
          padding: 2px 8px;
          border-radius: 10px;
          background: var(--bg-primary, #1e1e2e);
          font-size: 11px;
          color: var(--text-muted, #71717a);
        }
        .bh-count-warn {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .bh-card-action {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 10px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: none;
          color: var(--text-muted, #71717a);
          font-size: 11px;
          cursor: pointer;
          transition: all 0.15s;
          margin-left: auto;
        }
        .bh-card-action:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }
        .bh-card-action:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .bh-briefing-actions {
          display: flex;
          gap: 6px;
          margin-left: auto;
        }
        .bh-card-body {
          padding: 12px 16px;
          max-height: 280px;
          overflow-y: auto;
        }
        .bh-empty {
          color: var(--text-muted, #71717a);
          font-size: 13px;
          text-align: center;
          padding: 16px 0;
          margin: 0;
        }

        .bh-list-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0;
          border-bottom: 1px solid var(--border, #1e1e2e);
          font-size: 13px;
        }
        .bh-list-item:last-child { border-bottom: none; }
        .bh-list-title {
          color: var(--text-primary, #e4e4e7);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
          flex: 1;
        }
        .bh-list-subtitle {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        .bh-badge {
          padding: 2px 6px;
          border-radius: 4px;
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
          flex-shrink: 0;
        }
        .bh-badge-warn { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .bh-badge-info { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
        .bh-badge-danger { background: rgba(239, 68, 68, 0.15); color: #ef4444; }

        .bh-assignee {
          padding: 2px 8px;
          border-radius: 4px;
          background: rgba(139, 92, 246, 0.15);
          color: #8b5cf6;
          font-size: 11px;
          font-weight: 500;
          flex-shrink: 0;
        }

        .bh-attention-item {
          flex-wrap: wrap;
        }

        .bh-projects-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
          gap: 10px;
        }
        .bh-project-card {
          display: flex;
          flex-direction: column;
          gap: 6px;
          padding: 12px;
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          background: var(--bg-primary, #1e1e2e);
          cursor: pointer;
          transition: border-color 0.15s;
          text-align: left;
        }
        .bh-project-card:hover {
          border-color: var(--accent, #3b82f6);
        }
        .bh-project-title {
          font-size: 14px;
          font-weight: 500;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-project-category {
          font-size: 11px;
          color: var(--accent, #3b82f6);
        }
        .bh-project-deadline {
          font-size: 11px;
          color: var(--text-muted, #71717a);
        }
        .bh-overdue { color: #ef4444; }

        .bh-activity-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 6px 0;
          border: none;
          background: none;
          width: 100%;
          text-align: left;
          cursor: pointer;
          color: var(--text-primary, #e4e4e7);
          font-size: 13px;
          transition: color 0.1s;
          border-bottom: 1px solid var(--border, #1e1e2e);
        }
        .bh-activity-item:hover { color: var(--accent, #3b82f6); }
        .bh-activity-item:last-child { border-bottom: none; }
        .bh-activity-item svg { color: var(--text-muted, #71717a); flex-shrink: 0; }
        .bh-activity-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .bh-activity-source {
          padding: 2px 6px;
          border-radius: 4px;
          background: var(--bg-secondary, #27272a);
          font-size: 10px;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .bh-activity-date { font-size: 11px; color: var(--text-muted, #71717a); flex-shrink: 0; }

        .bh-briefing p { margin: 0 0 8px; color: var(--text-primary, #e4e4e7); font-size: 14px; line-height: 1.6; }
        .bh-briefing-section { margin: 12px 0; }
        .bh-briefing-section h4 {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin: 0 0 6px;
        }
        .bh-briefing-section ul {
          margin: 0;
          padding-left: 18px;
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.6;
        }
        .bh-themes {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .bh-theme-tag {
          padding: 4px 10px;
          border-radius: 12px;
          background: rgba(59, 130, 246, 0.1);
          color: var(--accent, #3b82f6);
          font-size: 12px;
        }

        .bh-project-meta {
          display: flex;
          align-items: center;
          gap: 10px;
          flex-wrap: wrap;
        }
        .bh-project-stat {
          display: flex;
          align-items: center;
          gap: 3px;
          font-size: 11px;
          color: var(--text-muted, #71717a);
        }

        .bh-prep p { margin: 0 0 8px; color: var(--text-primary, #e4e4e7); font-size: 14px; line-height: 1.6; }
        .bh-prep-section { margin: 12px 0; }
        .bh-prep-section h4 {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin: 0 0 6px;
        }
        .bh-prep-section ul {
          margin: 0;
          padding-left: 18px;
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.6;
        }

        .bh-predictions-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 12px;
        }
        .bh-prediction-card {
          display: flex;
          gap: 12px;
          padding: 14px;
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          background: var(--bg-primary, #1e1e2e);
        }
        .bh-prediction-icon {
          width: 36px;
          height: 36px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .bh-pred-activity { background: rgba(59, 130, 246, 0.15); color: #3b82f6; }
        .bh-pred-topics { background: rgba(139, 92, 246, 0.15); color: #8b5cf6; }
        .bh-pred-dormancy { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .bh-prediction-content { flex: 1; min-width: 0; }
        .bh-prediction-title {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin: 0 0 4px;
        }
        .bh-prediction-text {
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
          margin: 0;
          line-height: 1.5;
        }
        .bh-emerging-list {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
        }
        .bh-emerging-item {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 3px 8px;
          border-radius: 4px;
          background: rgba(139, 92, 246, 0.1);
          color: #c4b5fd;
          font-size: 12px;
        }
        .bh-trend-arrow { font-weight: 700; }
        .bh-trend-up { color: #10b981; }
        .bh-trend-down { color: #ef4444; }
        .bh-dormancy-list {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .bh-dormancy-item {
          display: flex;
          align-items: center;
          gap: 8px;
          background: none;
          border: none;
          padding: 4px 0;
          cursor: pointer;
          text-align: left;
          font-size: 12px;
          color: var(--text-primary, #e4e4e7);
          transition: color 0.1s;
        }
        .bh-dormancy-item:hover { color: var(--accent, #3b82f6); }
        .bh-risk-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }
        .bh-risk-low { background: #10b981; }
        .bh-risk-medium { background: #f59e0b; }
        .bh-risk-high, .bh-risk-critical { background: #ef4444; }
        .bh-dormancy-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .bh-dormancy-days {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }

        @keyframes bh-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .bh-spin { animation: bh-spin 1s linear infinite; }

        .bh-briefing-card {
          background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
          border: 1px solid #334155;
        }
        .bh-briefing-content {
          padding: 12px 16px;
        }
        .bh-briefing-content .bh-briefing-summary {
          font-size: 14px;
          color: var(--text-primary, #e4e4e7);
          line-height: 1.6;
          margin-bottom: 12px;
        }
        .bh-briefing-content .bh-briefing-section h4 {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #94a3b8);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin: 8px 0 4px;
        }
        .bh-briefing-content .bh-briefing-section ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .bh-briefing-content .bh-briefing-section li {
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
          padding: 3px 0;
          padding-left: 12px;
          position: relative;
        }
        .bh-briefing-content .bh-briefing-section li::before {
          content: "•";
          position: absolute;
          left: 0;
          color: #60a5fa;
        }

        .bh-meetings-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 12px 16px;
        }
        .bh-meeting-item {
          padding: 10px;
          background: var(--bg-primary, #1e1e2e);
          border-radius: 8px;
          border: 1px solid var(--border, #27272a);
        }
        .bh-meeting-title {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-meeting-time {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          margin-top: 2px;
        }
        .bh-meeting-attendees {
          display: flex;
          gap: 4px;
          flex-wrap: wrap;
          margin-top: 6px;
        }
        .bh-attendee-badge {
          font-size: 11px;
          padding: 2px 8px;
          border-radius: 10px;
          background: #3b82f620;
          color: #60a5fa;
        }
        .bh-meeting-agenda {
          margin-top: 6px;
        }
        .bh-agenda-item {
          font-size: 12px;
          color: var(--text-muted, #a1a1aa);
          padding: 2px 0;
          padding-left: 12px;
          position: relative;
        }
        .bh-agenda-item::before {
          content: "→";
          position: absolute;
          left: 0;
          color: #22c55e;
        }

        .bh-followups-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding: 12px 16px;
        }
        .bh-followup-item {
          padding: 10px;
          background: var(--bg-primary, #1e1e2e);
          border-radius: 8px;
          border-left: 3px solid #71717a;
        }
        .bh-followup--high {
          border-left-color: #f59e0b;
        }
        .bh-followup--urgent {
          border-left-color: #ef4444;
        }
        .bh-followup-title {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .bh-followup-desc {
          font-size: 12px;
          color: var(--text-muted, #a1a1aa);
          margin-top: 2px;
        }
        .bh-followup-person {
          display: inline-block;
          font-size: 11px;
          padding: 1px 6px;
          border-radius: 8px;
          background: #8b5cf620;
          color: #a78bfa;
          margin-top: 4px;
        }
        .bh-followup-action {
          font-size: 12px;
          color: #60a5fa;
          margin-top: 4px;
        }

        .bh-relationships-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
          padding: 12px 16px;
        }
        .bh-relationship-item {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 10px;
          background: var(--bg-primary, #1e1e2e);
          border-radius: 8px;
          cursor: pointer;
          transition: background 0.15s;
        }
        .bh-relationship-item:hover {
          background: var(--bg-secondary, #27272a);
        }
        .bh-rel-name {
          font-size: 13px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
          min-width: 120px;
        }
        .bh-rel-score {
          flex: 1;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .bh-rel-bar {
          height: 4px;
          background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e);
          border-radius: 2px;
          transition: width 0.3s;
        }
        .bh-rel-score span {
          font-size: 11px;
          color: var(--text-muted, #71717a);
          min-width: 40px;
        }
        .bh-rel-grade {
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          color: var(--text-muted, #71717a);
        }
      `}</style>
    </div>
  );
}
