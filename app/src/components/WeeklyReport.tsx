/**
 * WeeklyReport.tsx — Weekly pattern report component.
 *
 * Displays communication overview, commitment health, project activity,
 * relationship health, and time patterns with CSS-only visualizations.
 */

import { useState, useEffect, useCallback } from "react";
import {
  BarChart3,
  CheckCircle2,
  AlertTriangle,
  Clock,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  Users,
  FolderOpen,
  Mail,
  Loader2,
  RefreshCw,
  FileText,
} from "lucide-react";
import { api } from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface SourceBreakdown {
  source: string;
  count: number;
  change_pct: number;
}

interface TopContact {
  name: string;
  person_id?: string;
  interaction_count: number;
  trend: "up" | "down" | "stable";
}

interface CommitmentHealth {
  created: number;
  fulfilled: number;
  overdue: number;
  overdue_items: { content: string; person_name: string; due_date: string }[];
}

interface ProjectActivity {
  id: string;
  title: string;
  event_count: number;
  status: "active" | "declining" | "stale";
}

interface RelationshipTrend {
  person_id: string;
  name: string;
  trend: "growing" | "cooling" | "dormant";
  score?: number;
  suggestion?: string;
}

interface TimePattern {
  peak_hours: { hour: number; count: number }[];
  peak_days: string[];
  meeting_load: number;
}

interface WeeklyReportData {
  period_start: string;
  period_end: string;
  source_breakdown: SourceBreakdown[];
  top_contacts: TopContact[];
  commitment_health: CommitmentHealth;
  project_activity: ProjectActivity[];
  relationship_trends: RelationshipTrend[];
  time_patterns: TimePattern;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function WeeklyReport() {
  const [report, setReport] = useState<WeeklyReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadReport = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getWeeklyReport();
      setReport(data);
    } catch {
      setError("Failed to load weekly report");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadReport();
  }, [loadReport]);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const data = await api.generateWeeklyReport();
      setReport(data);
    } catch {
      setError("Failed to generate report");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="wr-container">
        <div className="wr-loading">
          <Loader2 size={20} className="wr-spin" />
          <span>Loading weekly report...</span>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="wr-container">
        <div className="wr-empty">
          <p style={{ color: "#ef4444" }}>{error}</p>
          <button className="wr-btn" onClick={loadReport}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  const maxSourceCount = Math.max(1, ...(report?.source_breakdown?.map((s) => s.count) ?? [1]));
  const maxHourCount = Math.max(1, ...(report?.time_patterns?.peak_hours?.map((h) => h.count) ?? [1]));

  const trendIcon = (trend: string) => {
    if (trend === "up" || trend === "growing") return <TrendingUp size={13} style={{ color: "#10b981" }} />;
    if (trend === "down" || trend === "cooling") return <TrendingDown size={13} style={{ color: "#ef4444" }} />;
    return <ArrowRight size={13} style={{ color: "#71717a" }} />;
  };

  const changeBadge = (pct: number) => {
    if (pct === 0) return null;
    const color = pct > 0 ? "#10b981" : "#ef4444";
    const arrow = pct > 0 ? "\u2191" : "\u2193";
    return (
      <span className="wr-change-badge" style={{ color, background: pct > 0 ? "rgba(16,185,129,0.12)" : "rgba(239,68,68,0.12)" }}>
        {arrow}{Math.abs(pct)}%
      </span>
    );
  };

  return (
    <div className="wr-container">
      {/* Generate button */}
      <div className="wr-actions">
        <button className="wr-btn wr-btn-primary" onClick={handleGenerate} disabled={generating}>
          {generating ? <Loader2 size={14} className="wr-spin" /> : <RefreshCw size={14} />}
          {generating ? "Generating..." : "Generate Report"}
        </button>
      </div>

      {report && (
        <>
          {/* Communication Overview */}
          <div className="wr-card">
            <div className="wr-card-header">
              <BarChart3 size={16} style={{ color: "#3b82f6" }} />
              <h3 className="wr-card-title">Communication Overview</h3>
            </div>

            {/* Source breakdown */}
            {report.source_breakdown && report.source_breakdown.length > 0 && (
              <div className="wr-subsection">
                <span className="wr-label">Source Breakdown</span>
                <div className="wr-bars">
                  {report.source_breakdown.map((s) => (
                    <div key={s.source} className="wr-bar-row">
                      <span className="wr-bar-label">{s.source}</span>
                      <div className="wr-bar-track">
                        <div
                          className="wr-bar-fill"
                          style={{ width: `${(s.count / maxSourceCount) * 100}%` }}
                        />
                      </div>
                      <span className="wr-bar-value">{s.count}</span>
                      {changeBadge(s.change_pct)}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Top contacts */}
            {report.top_contacts && report.top_contacts.length > 0 && (
              <div className="wr-subsection">
                <span className="wr-label">Top Contacts</span>
                <div className="wr-list">
                  {report.top_contacts.map((c, i) => (
                    <div key={i} className="wr-list-item">
                      <span className="wr-contact-name">{c.name}</span>
                      <span className="wr-contact-count">{c.interaction_count} interactions</span>
                      {trendIcon(c.trend)}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Commitment Health */}
          {report.commitment_health && (
            <div className="wr-card">
              <div className="wr-card-header">
                <CheckCircle2 size={16} style={{ color: "#10b981" }} />
                <h3 className="wr-card-title">Commitment Health</h3>
              </div>
              <div className="wr-metrics-row">
                <div className="wr-metric">
                  <span className="wr-metric-value">{report.commitment_health.created}</span>
                  <span className="wr-metric-label">Created</span>
                </div>
                <div className="wr-metric">
                  <span className="wr-metric-value" style={{ color: "#10b981" }}>{report.commitment_health.fulfilled}</span>
                  <span className="wr-metric-label">Fulfilled</span>
                </div>
                <div className="wr-metric">
                  <span className="wr-metric-value" style={{ color: "#ef4444" }}>{report.commitment_health.overdue}</span>
                  <span className="wr-metric-label">Overdue</span>
                </div>
              </div>

              {report.commitment_health.overdue_items && report.commitment_health.overdue_items.length > 0 && (
                <div className="wr-subsection">
                  <span className="wr-label">Overdue Items</span>
                  <div className="wr-list">
                    {report.commitment_health.overdue_items.map((item, i) => (
                      <div key={i} className="wr-list-item wr-overdue-item">
                        <div>
                          <span className="wr-overdue-content">{item.content}</span>
                          <span className="wr-overdue-meta">
                            {item.person_name} &middot; due {new Date(item.due_date).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Project Activity */}
          {report.project_activity && report.project_activity.length > 0 && (
            <div className="wr-card">
              <div className="wr-card-header">
                <FolderOpen size={16} style={{ color: "#8b5cf6" }} />
                <h3 className="wr-card-title">Project Activity</h3>
              </div>
              <div className="wr-list">
                {report.project_activity.map((proj) => (
                  <div key={proj.id} className="wr-list-item">
                    <span className="wr-contact-name">{proj.title}</span>
                    <span className="wr-contact-count">{proj.event_count} events</span>
                    <span className={`wr-status-badge wr-status-${proj.status}`}>
                      {proj.status === "declining" && <AlertTriangle size={11} />}
                      {proj.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relationship Health */}
          {report.relationship_trends && report.relationship_trends.length > 0 && (
            <div className="wr-card">
              <div className="wr-card-header">
                <Users size={16} style={{ color: "#f59e0b" }} />
                <h3 className="wr-card-title">Relationship Health</h3>
              </div>

              {/* Growing */}
              {report.relationship_trends.filter((r) => r.trend === "growing").length > 0 && (
                <div className="wr-subsection">
                  <span className="wr-label" style={{ color: "#10b981" }}>Growing</span>
                  <div className="wr-list">
                    {report.relationship_trends.filter((r) => r.trend === "growing").map((r, i) => (
                      <div key={i} className="wr-list-item">
                        <span className="wr-contact-name">{r.name}</span>
                        {trendIcon(r.trend)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Cooling */}
              {report.relationship_trends.filter((r) => r.trend === "cooling").length > 0 && (
                <div className="wr-subsection">
                  <span className="wr-label" style={{ color: "#eab308" }}>Cooling</span>
                  <div className="wr-list">
                    {report.relationship_trends.filter((r) => r.trend === "cooling").map((r, i) => (
                      <div key={i} className="wr-list-item">
                        <span className="wr-contact-name">{r.name}</span>
                        {trendIcon(r.trend)}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Dormant */}
              {report.relationship_trends.filter((r) => r.trend === "dormant").length > 0 && (
                <div className="wr-subsection">
                  <span className="wr-label" style={{ color: "#ef4444" }}>Dormant</span>
                  <div className="wr-list">
                    {report.relationship_trends.filter((r) => r.trend === "dormant").map((r, i) => (
                      <div key={i} className="wr-list-item">
                        <span className="wr-contact-name">{r.name}</span>
                        {r.suggestion && <span className="wr-suggestion">{r.suggestion}</span>}
                        <Mail size={13} style={{ color: "#71717a" }} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Time Patterns */}
          {report.time_patterns && (
            <div className="wr-card">
              <div className="wr-card-header">
                <Clock size={16} style={{ color: "#06b6d4" }} />
                <h3 className="wr-card-title">Time Patterns</h3>
              </div>

              {report.time_patterns.peak_hours && report.time_patterns.peak_hours.length > 0 && (
                <div className="wr-subsection">
                  <span className="wr-label">Peak Hours</span>
                  <div className="wr-hour-bars">
                    {report.time_patterns.peak_hours.map((h) => (
                      <div key={h.hour} className="wr-hour-row">
                        <span className="wr-hour-label">{String(h.hour).padStart(2, "0")}:00</span>
                        <div className="wr-bar-track">
                          <div
                            className="wr-bar-fill wr-bar-fill-cyan"
                            style={{ width: `${(h.count / maxHourCount) * 100}%` }}
                          />
                        </div>
                        <span className="wr-bar-value">{h.count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="wr-metrics-row">
                {report.time_patterns.peak_days && report.time_patterns.peak_days.length > 0 && (
                  <div className="wr-metric">
                    <span className="wr-metric-value" style={{ fontSize: "0.95rem" }}>
                      {report.time_patterns.peak_days.join(", ")}
                    </span>
                    <span className="wr-metric-label">Peak Days</span>
                  </div>
                )}
                <div className="wr-metric">
                  <span className="wr-metric-value">{report.time_patterns.meeting_load}</span>
                  <span className="wr-metric-label">Meetings This Week</span>
                </div>
              </div>
            </div>
          )}
        </>
      )}
      <style>{styles}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = `
  .wr-container {
    padding: 0;
  }
  .wr-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 20px;
    justify-content: center;
    color: var(--text-muted, #71717a);
    font-size: 0.85rem;
  }
  @keyframes wr-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .wr-spin {
    animation: wr-spin 1s linear infinite;
  }
  .wr-empty {
    text-align: center;
    padding: 60px 20px;
  }

  .wr-actions {
    display: flex;
    justify-content: flex-end;
    margin-bottom: 16px;
  }
  .wr-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    border: 1px solid var(--border, #27272a);
    border-radius: 6px;
    background: none;
    color: var(--text-muted, #a1a1aa);
    cursor: pointer;
    font-size: 0.82rem;
    transition: all 0.15s;
  }
  .wr-btn:hover {
    color: var(--accent, #3b82f6);
    border-color: var(--accent, #3b82f6);
  }
  .wr-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .wr-btn-primary {
    background: var(--accent, #3b82f6);
    color: #fff;
    border-color: var(--accent, #3b82f6);
  }
  .wr-btn-primary:hover {
    opacity: 0.9;
    color: #fff;
  }

  .wr-card {
    background: var(--bg-secondary, #18181b);
    border: 1px solid var(--border, #27272a);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .wr-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
  }
  .wr-card-title {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
  }

  .wr-subsection {
    margin-bottom: 16px;
  }
  .wr-subsection:last-child {
    margin-bottom: 0;
  }
  .wr-label {
    display: block;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted, #71717a);
    margin-bottom: 8px;
  }

  .wr-bars, .wr-hour-bars {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .wr-bar-row, .wr-hour-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .wr-bar-label, .wr-hour-label {
    width: 70px;
    font-size: 0.78rem;
    color: var(--text-muted, #a1a1aa);
    text-transform: capitalize;
    flex-shrink: 0;
  }
  .wr-hour-label {
    width: 50px;
  }
  .wr-bar-track {
    flex: 1;
    height: 8px;
    background: var(--bg-tertiary, #0f0f12);
    border-radius: 4px;
    overflow: hidden;
  }
  .wr-bar-fill {
    height: 100%;
    background: var(--accent, #3b82f6);
    border-radius: 4px;
    transition: width 0.3s ease;
  }
  .wr-bar-fill-cyan {
    background: #06b6d4;
  }
  .wr-bar-value {
    font-size: 0.75rem;
    color: var(--text-muted, #a1a1aa);
    width: 35px;
    text-align: right;
    flex-shrink: 0;
  }

  .wr-change-badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 1px 6px;
    border-radius: 4px;
    flex-shrink: 0;
  }

  .wr-metrics-row {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }
  .wr-metric {
    flex: 1;
    background: var(--bg-tertiary, #0f0f12);
    border-radius: 8px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .wr-metric-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-primary, #e4e4e7);
  }
  .wr-metric-label {
    font-size: 0.72rem;
    color: var(--text-muted, #71717a);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .wr-list {
    display: flex;
    flex-direction: column;
  }
  .wr-list-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 0;
    border-bottom: 1px solid rgba(39, 39, 42, 0.5);
  }
  .wr-list-item:last-child {
    border-bottom: none;
  }
  .wr-contact-name {
    font-size: 0.84rem;
    color: var(--text-primary, #e4e4e7);
    font-weight: 500;
  }
  .wr-contact-count {
    font-size: 0.75rem;
    color: var(--text-muted, #71717a);
    margin-left: auto;
  }

  .wr-overdue-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    border-left: 3px solid #ef4444;
    padding-left: 10px;
    margin-left: 0;
  }
  .wr-overdue-content {
    display: block;
    font-size: 0.84rem;
    color: var(--text-primary, #e4e4e7);
  }
  .wr-overdue-meta {
    font-size: 0.72rem;
    color: var(--text-muted, #71717a);
  }

  .wr-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 4px;
    flex-shrink: 0;
  }
  .wr-status-active {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
  }
  .wr-status-declining {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
  }
  .wr-status-stale {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .wr-suggestion {
    font-size: 0.75rem;
    color: var(--text-muted, #71717a);
    font-style: italic;
    margin-left: auto;
  }
`;
