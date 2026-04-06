/**
 * RelationshipDashboard.tsx — Relationship health dashboard.
 *
 * Visual dashboard showing relationship scores, trends, and attention items
 * with color-coded indicators and actionable suggestions.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Users,
  TrendingUp,
  TrendingDown,
  ArrowRight,
  AlertTriangle,
  Mail,
  Loader2,
  RefreshCw,
  MessageSquare,
  Phone,
  Video,
  Calendar,
} from "lucide-react";
import { api } from "../lib/api";
import { useApp } from "../lib/store";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface RelationshipSummary {
  total: number;
  strong: number;
  moderate: number;
  weak: number;
  dormant: number;
}

interface RelationshipEntry {
  person_id: string;
  name: string;
  score: number;
  grade: string;
  trend: "improving" | "stable" | "declining";
  primary_channel: string;
  last_contact?: string;
  suggestion?: string;
}

interface RelationshipDashboardData {
  summary: RelationshipSummary;
  top_relationships: RelationshipEntry[];
  needs_attention: RelationshipEntry[];
  dormant_contacts: RelationshipEntry[];
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function scoreColor(score: number): string {
  if (score >= 75) return "#10b981";
  if (score >= 50) return "#eab308";
  if (score >= 25) return "#f97316";
  return "#ef4444";
}

function gradeColor(grade: string): string {
  const g = grade.toUpperCase();
  if (g === "A" || g === "A+") return "#10b981";
  if (g === "B" || g === "B+") return "#22c55e";
  if (g === "C" || g === "C+") return "#eab308";
  if (g === "D" || g === "D+") return "#f97316";
  return "#ef4444";
}

const channelIcons: Record<string, typeof Mail> = {
  email: Mail,
  chat: MessageSquare,
  phone: Phone,
  video: Video,
  meeting: Calendar,
};

function formatLastContact(iso?: string): string {
  if (!iso) return "Never";
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / 86400000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function RelationshipDashboard() {
  const { dispatch } = useApp();
  const [data, setData] = useState<RelationshipDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getRelationshipDashboard();
      setData(result);
    } catch {
      setError("Failed to load relationship data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const navigateToPerson = (personId: string) => {
    dispatch({ type: "SET_CONTEXT_MODE", mode: { type: "person", personId } });
  };

  const trendIcon = (trend: string) => {
    if (trend === "improving") return <TrendingUp size={13} style={{ color: "#10b981" }} />;
    if (trend === "declining") return <TrendingDown size={13} style={{ color: "#ef4444" }} />;
    return <ArrowRight size={13} style={{ color: "#71717a" }} />;
  };

  if (loading) {
    return (
      <div className="rd-container">
        <div className="rd-loading">
          <Loader2 size={20} className="rd-spin" />
          <span>Loading relationship data...</span>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="rd-container">
        <div className="rd-empty">
          <p style={{ color: "#ef4444" }}>{error}</p>
          <button className="rd-btn" onClick={loadData}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (!data) return null;

  const summary = data.summary || { total: 0, strong: 0, moderate: 0, weak: 0, dormant: 0 };

  return (
    <div className="rd-container">
      {/* Summary stats */}
      <div className="rd-stats-row">
        <div className="rd-stat">
          <span className="rd-stat-value">{summary.total}</span>
          <span className="rd-stat-label">Total</span>
        </div>
        <div className="rd-stat">
          <span className="rd-stat-value" style={{ color: "#10b981" }}>{summary.strong}</span>
          <span className="rd-stat-label">Strong</span>
        </div>
        <div className="rd-stat">
          <span className="rd-stat-value" style={{ color: "#eab308" }}>{summary.moderate}</span>
          <span className="rd-stat-label">Moderate</span>
        </div>
        <div className="rd-stat">
          <span className="rd-stat-value" style={{ color: "#f97316" }}>{summary.weak}</span>
          <span className="rd-stat-label">Weak</span>
        </div>
        <div className="rd-stat">
          <span className="rd-stat-value" style={{ color: "#ef4444" }}>{summary.dormant}</span>
          <span className="rd-stat-label">Dormant</span>
        </div>
      </div>

      {/* Top Relationships */}
      {data.top_relationships && data.top_relationships.length > 0 && (
        <div className="rd-card">
          <div className="rd-card-header">
            <Users size={16} style={{ color: "#10b981" }} />
            <h3 className="rd-card-title">Top Relationships</h3>
          </div>
          <div className="rd-list">
            {data.top_relationships.map((r) => {
              const ChannelIcon = channelIcons[r.primary_channel] || MessageSquare;
              return (
                <div
                  key={r.person_id}
                  className="rd-list-item rd-clickable"
                  onClick={() => navigateToPerson(r.person_id)}
                >
                  <div className="rd-person-info">
                    <span className="rd-person-name">{r.name}</span>
                    <div className="rd-score-bar-container">
                      <div className="rd-score-bar-track">
                        <div
                          className="rd-score-bar-fill"
                          style={{ width: `${r.score}%`, background: scoreColor(r.score) }}
                        />
                      </div>
                      <span className="rd-score-value">{r.score}</span>
                    </div>
                  </div>
                  <div className="rd-person-meta">
                    <span className="rd-grade" style={{ color: gradeColor(r.grade), borderColor: gradeColor(r.grade) }}>
                      {r.grade}
                    </span>
                    <ChannelIcon size={13} style={{ color: "var(--text-muted, #71717a)" }} />
                    {trendIcon(r.trend)}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Needs Attention */}
      {data.needs_attention && data.needs_attention.length > 0 && (
        <div className="rd-card">
          <div className="rd-card-header">
            <AlertTriangle size={16} style={{ color: "#f59e0b" }} />
            <h3 className="rd-card-title">Needs Attention</h3>
          </div>
          <div className="rd-list">
            {data.needs_attention.map((r) => (
              <div
                key={r.person_id}
                className="rd-list-item rd-clickable"
                onClick={() => navigateToPerson(r.person_id)}
              >
                <div className="rd-person-info">
                  <span className="rd-person-name">{r.name}</span>
                  {r.suggestion && <span className="rd-suggestion">{r.suggestion}</span>}
                </div>
                <div className="rd-person-meta">
                  <span className="rd-last-contact">{formatLastContact(r.last_contact)}</span>
                  {trendIcon(r.trend)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dormant Contacts */}
      {data.dormant_contacts && data.dormant_contacts.length > 0 && (
        <div className="rd-card">
          <div className="rd-card-header">
            <Users size={16} style={{ color: "#ef4444" }} />
            <h3 className="rd-card-title">Dormant Contacts</h3>
          </div>
          <div className="rd-list">
            {data.dormant_contacts.map((r) => (
              <div key={r.person_id} className="rd-list-item">
                <div className="rd-person-info">
                  <span className="rd-person-name">{r.name}</span>
                  <span className="rd-dormant-meta">
                    Last contact: {formatLastContact(r.last_contact)}
                  </span>
                </div>
                <button
                  className="rd-reach-out-btn"
                  onClick={() => navigateToPerson(r.person_id)}
                >
                  <Mail size={13} />
                  Reach out
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <style>{styles}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = `
  .rd-container {
    padding: 0;
  }
  .rd-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 20px;
    justify-content: center;
    color: var(--text-muted, #71717a);
    font-size: 0.85rem;
  }
  @keyframes rd-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .rd-spin {
    animation: rd-spin 1s linear infinite;
  }
  .rd-empty {
    text-align: center;
    padding: 60px 20px;
  }
  .rd-btn {
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
  .rd-btn:hover {
    color: var(--accent, #3b82f6);
    border-color: var(--accent, #3b82f6);
  }

  .rd-stats-row {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 20px;
  }
  .rd-stat {
    background: var(--bg-secondary, #18181b);
    border: 1px solid var(--border, #27272a);
    border-radius: 10px;
    padding: 14px 10px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
  }
  .rd-stat-value {
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text-primary, #e4e4e7);
  }
  .rd-stat-label {
    font-size: 0.7rem;
    color: var(--text-muted, #71717a);
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .rd-card {
    background: var(--bg-secondary, #18181b);
    border: 1px solid var(--border, #27272a);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .rd-card-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 14px;
  }
  .rd-card-title {
    margin: 0;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
  }

  .rd-list {
    display: flex;
    flex-direction: column;
  }
  .rd-list-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid rgba(39, 39, 42, 0.5);
  }
  .rd-list-item:last-child {
    border-bottom: none;
  }
  .rd-clickable {
    cursor: pointer;
    transition: background 0.15s;
    border-radius: 6px;
    padding: 10px 8px;
    margin: 0 -8px;
  }
  .rd-clickable:hover {
    background: var(--bg-tertiary, #0f0f12);
  }

  .rd-person-info {
    flex: 1;
    min-width: 0;
  }
  .rd-person-name {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
    margin-bottom: 4px;
  }
  .rd-score-bar-container {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .rd-score-bar-track {
    flex: 1;
    height: 6px;
    background: var(--bg-tertiary, #0f0f12);
    border-radius: 3px;
    overflow: hidden;
    max-width: 120px;
  }
  .rd-score-bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 0.3s ease;
  }
  .rd-score-value {
    font-size: 0.72rem;
    color: var(--text-muted, #71717a);
    width: 24px;
    flex-shrink: 0;
  }

  .rd-person-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }
  .rd-grade {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 2px 6px;
    border: 1px solid;
    border-radius: 4px;
  }
  .rd-last-contact {
    font-size: 0.72rem;
    color: var(--text-muted, #52525b);
  }
  .rd-suggestion {
    display: block;
    font-size: 0.75rem;
    color: var(--text-muted, #71717a);
    font-style: italic;
  }
  .rd-dormant-meta {
    display: block;
    font-size: 0.72rem;
    color: var(--text-muted, #52525b);
  }

  .rd-reach-out-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border: 1px solid var(--accent, #3b82f6);
    border-radius: 6px;
    background: rgba(59, 130, 246, 0.08);
    color: #60a5fa;
    font-size: 0.78rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
    flex-shrink: 0;
  }
  .rd-reach-out-btn:hover {
    background: rgba(59, 130, 246, 0.18);
  }
`;
