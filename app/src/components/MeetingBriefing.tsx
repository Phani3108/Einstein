/**
 * MeetingBriefing.tsx — Pre-meeting briefing component.
 *
 * Shows upcoming meetings with attendee cards, relationship indicators,
 * talking points, and context summaries.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Calendar,
  Clock,
  Users,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  CheckCircle2,
  Lightbulb,
  FolderOpen,
  Loader2,
  Coffee,
  RefreshCw,
} from "lucide-react";
import { api } from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Attendee {
  person_id: string;
  name: string;
  role: string;
  organization: string;
  relationship_strength: "strong" | "moderate" | "weak" | "dormant";
  last_contact: string | null;
  recent_interactions: { date: string; summary: string }[];
  open_commitments: { content: string; due_date?: string }[];
  talking_points: string[];
}

interface MeetingBriefingData {
  meeting_id: string;
  title: string;
  start_time: string;
  attendees: Attendee[];
  related_projects: { id: string; title: string; status: string }[];
  suggested_agenda: string[];
  context_summary: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatCountdown(isoDate: string): string {
  const diff = new Date(isoDate).getTime() - Date.now();
  if (diff < 0) return "started";
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `in ${mins} minute${mins !== 1 ? "s" : ""}`;
  const hrs = Math.floor(mins / 60);
  const remMins = mins % 60;
  if (hrs < 24) {
    return remMins > 0 ? `in ${hrs}h ${remMins}m` : `in ${hrs} hour${hrs !== 1 ? "s" : ""}`;
  }
  const days = Math.floor(hrs / 24);
  return `in ${days} day${days !== 1 ? "s" : ""}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return "Never";
  const d = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffDays = Math.floor(diffMs / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return d.toLocaleDateString();
}

const strengthColors: Record<string, string> = {
  strong: "#10b981",
  moderate: "#eab308",
  weak: "#f97316",
  dormant: "#ef4444",
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function MeetingBriefing() {
  const [briefings, setBriefings] = useState<MeetingBriefingData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAttendees, setExpandedAttendees] = useState<Set<string>>(new Set());

  const loadBriefings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getUpcomingBriefings();
      setBriefings(data ?? []);
    } catch (err) {
      setError("Failed to load meeting briefings");
      setBriefings([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBriefings();
  }, [loadBriefings]);

  const toggleAttendee = (key: string) => {
    setExpandedAttendees((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="mb-container">
        <div className="mb-loading">
          <Loader2 size={20} className="mb-spin" />
          <span>Loading meeting briefings...</span>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="mb-container">
        <div className="mb-empty">
          <p style={{ color: "#ef4444" }}>{error}</p>
          <button className="mb-retry-btn" onClick={loadBriefings}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (briefings.length === 0) {
    return (
      <div className="mb-container">
        <div className="mb-empty">
          <Coffee size={32} style={{ color: "var(--text-muted, #71717a)", marginBottom: 12 }} />
          <h3 style={{ margin: "0 0 6px", color: "var(--text-primary, #e4e4e7)", fontSize: "1rem" }}>
            No upcoming meetings
          </h3>
          <p style={{ margin: 0, color: "var(--text-muted, #71717a)", fontSize: "0.85rem" }}>
            Enjoy your free time. Briefings will appear here before scheduled meetings.
          </p>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  return (
    <div className="mb-container">
      {briefings.map((meeting) => (
        <div key={meeting.meeting_id} className="mb-meeting-card">
          {/* Meeting header */}
          <div className="mb-meeting-header">
            <div className="mb-meeting-title-row">
              <Calendar size={16} style={{ color: "var(--accent, #3b82f6)", flexShrink: 0 }} />
              <h3 className="mb-meeting-title">{meeting.title}</h3>
            </div>
            <div className="mb-meeting-time">
              <Clock size={13} />
              <span>{new Date(meeting.start_time).toLocaleString()}</span>
              <span className="mb-countdown">{formatCountdown(meeting.start_time)}</span>
            </div>
          </div>

          {/* Context summary */}
          {meeting.context_summary && (
            <div className="mb-context-summary">
              <p>{meeting.context_summary}</p>
            </div>
          )}

          {/* Attendees */}
          {meeting.attendees && meeting.attendees.length > 0 && (
            <div className="mb-section">
              <h4 className="mb-section-title">
                <Users size={14} /> Attendees
              </h4>
              <div className="mb-attendees">
                {meeting.attendees.map((att) => {
                  const key = `${meeting.meeting_id}-${att.person_id}`;
                  const expanded = expandedAttendees.has(key);
                  return (
                    <div key={key} className="mb-attendee-card">
                      <div className="mb-attendee-header" onClick={() => toggleAttendee(key)}>
                        <div className="mb-attendee-info">
                          <span
                            className="mb-strength-dot"
                            style={{ background: strengthColors[att.relationship_strength] || "#71717a" }}
                            title={`Relationship: ${att.relationship_strength}`}
                          />
                          <div>
                            <span className="mb-attendee-name">{att.name}</span>
                            <span className="mb-attendee-role">
                              {att.role}{att.organization ? ` at ${att.organization}` : ""}
                            </span>
                          </div>
                        </div>
                        <div className="mb-attendee-meta">
                          <span className="mb-last-contact">Last: {formatDate(att.last_contact)}</span>
                          {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </div>
                      </div>

                      {expanded && (
                        <div className="mb-attendee-details">
                          {/* Recent interactions */}
                          {att.recent_interactions && att.recent_interactions.length > 0 && (
                            <div className="mb-detail-section">
                              <span className="mb-detail-label">
                                <MessageSquare size={12} /> Recent Interactions
                              </span>
                              <ul className="mb-detail-list">
                                {att.recent_interactions.map((ri, i) => (
                                  <li key={i}>
                                    <span className="mb-detail-date">{formatDate(ri.date)}</span>
                                    {ri.summary}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Open commitments */}
                          {att.open_commitments && att.open_commitments.length > 0 && (
                            <div className="mb-detail-section">
                              <span className="mb-detail-label">
                                <CheckCircle2 size={12} /> Open Commitments
                              </span>
                              <ul className="mb-detail-list">
                                {att.open_commitments.map((c, i) => (
                                  <li key={i}>
                                    {c.content}
                                    {c.due_date && (
                                      <span className="mb-detail-date" style={{ marginLeft: 6 }}>
                                        due {formatDate(c.due_date)}
                                      </span>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Talking points */}
                          {att.talking_points && att.talking_points.length > 0 && (
                            <div className="mb-detail-section">
                              <span className="mb-detail-label">
                                <Lightbulb size={12} /> Suggested Talking Points
                              </span>
                              <ul className="mb-detail-list mb-talking-points">
                                {att.talking_points.map((tp, i) => (
                                  <li key={i}>{tp}</li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Related projects */}
          {meeting.related_projects && meeting.related_projects.length > 0 && (
            <div className="mb-section">
              <h4 className="mb-section-title">
                <FolderOpen size={14} /> Related Projects
              </h4>
              <div className="mb-projects">
                {meeting.related_projects.map((proj) => (
                  <div key={proj.id} className="mb-project-chip">
                    <span className="mb-project-name">{proj.title}</span>
                    <span className={`mb-project-status mb-status-${proj.status}`}>{proj.status}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Suggested agenda */}
          {meeting.suggested_agenda && meeting.suggested_agenda.length > 0 && (
            <div className="mb-section">
              <h4 className="mb-section-title">
                <Lightbulb size={14} /> Suggested Agenda
              </h4>
              <ol className="mb-agenda-list">
                {meeting.suggested_agenda.map((item, i) => (
                  <li key={i}>{item}</li>
                ))}
              </ol>
            </div>
          )}
        </div>
      ))}
      <style>{styles}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = `
  .mb-container {
    padding: 0;
  }
  .mb-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 20px;
    justify-content: center;
    color: var(--text-muted, #71717a);
    font-size: 0.85rem;
  }
  @keyframes mb-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .mb-spin {
    animation: mb-spin 1s linear infinite;
  }
  .mb-empty {
    text-align: center;
    padding: 60px 20px;
  }
  .mb-retry-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 12px;
    padding: 6px 14px;
    border: 1px solid var(--border, #27272a);
    border-radius: 6px;
    background: none;
    color: var(--text-muted, #a1a1aa);
    cursor: pointer;
    font-size: 0.82rem;
  }
  .mb-retry-btn:hover {
    color: var(--accent, #3b82f6);
    border-color: var(--accent, #3b82f6);
  }

  .mb-meeting-card {
    background: var(--bg-secondary, #18181b);
    border: 1px solid var(--border, #27272a);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .mb-meeting-header {
    margin-bottom: 16px;
  }
  .mb-meeting-title-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }
  .mb-meeting-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
  }
  .mb-meeting-time {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: var(--text-muted, #a1a1aa);
  }
  .mb-countdown {
    background: rgba(59, 130, 246, 0.12);
    color: #60a5fa;
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 0.72rem;
    font-weight: 600;
  }
  .mb-context-summary {
    background: var(--bg-tertiary, #0f0f12);
    border-radius: 8px;
    padding: 12px 14px;
    margin-bottom: 16px;
    font-size: 0.84rem;
    line-height: 1.6;
    color: var(--text-secondary, #a1a1aa);
  }
  .mb-context-summary p {
    margin: 0;
  }

  .mb-section {
    margin-bottom: 16px;
  }
  .mb-section:last-child {
    margin-bottom: 0;
  }
  .mb-section-title {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 0 0 10px;
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--text-muted, #71717a);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .mb-attendees {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .mb-attendee-card {
    border: 1px solid var(--border, #27272a);
    border-radius: 8px;
    overflow: hidden;
  }
  .mb-attendee-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    cursor: pointer;
    transition: background 0.15s;
  }
  .mb-attendee-header:hover {
    background: var(--bg-tertiary, #0f0f12);
  }
  .mb-attendee-info {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .mb-strength-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .mb-attendee-name {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
  }
  .mb-attendee-role {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted, #71717a);
  }
  .mb-attendee-meta {
    display: flex;
    align-items: center;
    gap: 10px;
    color: var(--text-muted, #71717a);
  }
  .mb-last-contact {
    font-size: 0.72rem;
  }

  .mb-attendee-details {
    padding: 0 14px 14px;
    border-top: 1px solid var(--border, #27272a);
  }
  .mb-detail-section {
    margin-top: 10px;
  }
  .mb-detail-label {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted, #71717a);
    margin-bottom: 6px;
  }
  .mb-detail-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .mb-detail-list li {
    padding: 4px 0;
    font-size: 0.82rem;
    color: var(--text-secondary, #a1a1aa);
    border-bottom: 1px solid rgba(39, 39, 42, 0.5);
  }
  .mb-detail-list li:last-child {
    border-bottom: none;
  }
  .mb-detail-date {
    font-size: 0.7rem;
    color: var(--text-muted, #52525b);
    margin-right: 6px;
  }
  .mb-talking-points li {
    padding-left: 12px;
    position: relative;
  }
  .mb-talking-points li::before {
    content: "";
    position: absolute;
    left: 0;
    top: 10px;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--accent, #3b82f6);
  }

  .mb-projects {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .mb-project-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border: 1px solid var(--border, #27272a);
    border-radius: 6px;
    font-size: 0.82rem;
  }
  .mb-project-name {
    color: var(--text-primary, #e4e4e7);
  }
  .mb-project-status {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    padding: 1px 6px;
    border-radius: 4px;
  }
  .mb-status-active {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
  }
  .mb-status-paused {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
  }
  .mb-status-completed {
    background: rgba(59, 130, 246, 0.15);
    color: #3b82f6;
  }

  .mb-agenda-list {
    padding-left: 20px;
    margin: 0;
  }
  .mb-agenda-list li {
    padding: 4px 0;
    font-size: 0.84rem;
    color: var(--text-secondary, #a1a1aa);
  }
`;
