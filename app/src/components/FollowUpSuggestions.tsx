/**
 * FollowUpSuggestions.tsx — Follow-up suggestions component.
 *
 * Shows pending follow-ups grouped by priority with type icons,
 * suggested actions, and dismiss functionality.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Mail,
  Calendar,
  MessageSquare,
  CheckCircle2,
  X,
  Loader2,
  RefreshCw,
  PartyPopper,
  ArrowRight,
} from "lucide-react";
import { api } from "../lib/api";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface FollowUp {
  id: string;
  type: "unanswered_email" | "meeting_followup" | "stale_conversation" | "commitment_due";
  title: string;
  description: string;
  person_name: string;
  person_id?: string;
  priority: "high" | "medium" | "low";
  suggested_action?: string;
  action_url?: string;
  created_at?: string;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const typeIcons: Record<string, typeof Mail> = {
  unanswered_email: Mail,
  meeting_followup: Calendar,
  stale_conversation: MessageSquare,
  commitment_due: CheckCircle2,
};

const typeLabels: Record<string, string> = {
  unanswered_email: "Unanswered Email",
  meeting_followup: "Meeting Follow-up",
  stale_conversation: "Stale Conversation",
  commitment_due: "Commitment Due",
};

const priorityConfig: Record<string, { color: string; bg: string; label: string }> = {
  high: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.12)", label: "High" },
  medium: { color: "#eab308", bg: "rgba(234, 179, 8, 0.12)", label: "Medium" },
  low: { color: "#71717a", bg: "rgba(113, 113, 122, 0.12)", label: "Low" },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function FollowUpSuggestions() {
  const [followUps, setFollowUps] = useState<FollowUp[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());

  const loadFollowUps = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getFollowUps();
      setFollowUps(data ?? []);
    } catch {
      setError("Failed to load follow-up suggestions");
      setFollowUps([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFollowUps();
  }, [loadFollowUps]);

  const handleDismiss = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
  };

  const visibleFollowUps = followUps.filter((f) => !dismissed.has(f.id));

  const grouped = {
    high: visibleFollowUps.filter((f) => f.priority === "high"),
    medium: visibleFollowUps.filter((f) => f.priority === "medium"),
    low: visibleFollowUps.filter((f) => f.priority === "low"),
  };

  if (loading) {
    return (
      <div className="fu-container">
        <div className="fu-loading">
          <Loader2 size={20} className="fu-spin" />
          <span>Loading follow-ups...</span>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (error && visibleFollowUps.length === 0) {
    return (
      <div className="fu-container">
        <div className="fu-empty">
          <p style={{ color: "#ef4444" }}>{error}</p>
          <button className="fu-btn" onClick={loadFollowUps}>
            <RefreshCw size={14} /> Retry
          </button>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  if (visibleFollowUps.length === 0) {
    return (
      <div className="fu-container">
        <div className="fu-empty">
          <PartyPopper size={32} style={{ color: "#10b981", marginBottom: 12 }} />
          <h3 style={{ margin: "0 0 6px", color: "var(--text-primary, #e4e4e7)", fontSize: "1rem" }}>
            You're all caught up!
          </h3>
          <p style={{ margin: 0, color: "var(--text-muted, #71717a)", fontSize: "0.85rem" }}>
            No pending follow-ups. Great job staying on top of things.
          </p>
        </div>
        <style>{styles}</style>
      </div>
    );
  }

  const renderGroup = (priority: "high" | "medium" | "low", items: FollowUp[]) => {
    if (items.length === 0) return null;
    const config = priorityConfig[priority];
    return (
      <div className="fu-group" key={priority}>
        <div className="fu-group-header">
          <span className="fu-priority-badge" style={{ color: config.color, background: config.bg }}>
            {config.label} Priority
          </span>
          <span className="fu-group-count">{items.length}</span>
        </div>
        <div className="fu-cards">
          {items.map((fu) => {
            const Icon = typeIcons[fu.type] || MessageSquare;
            return (
              <div key={fu.id} className="fu-card" style={{ borderLeftColor: config.color }}>
                <div className="fu-card-header">
                  <Icon size={15} style={{ color: config.color, flexShrink: 0 }} />
                  <div className="fu-card-title-area">
                    <span className="fu-card-title">{fu.title}</span>
                    <span className="fu-card-type">{typeLabels[fu.type] || fu.type}</span>
                  </div>
                  <button
                    className="fu-dismiss-btn"
                    onClick={() => handleDismiss(fu.id)}
                    title="Dismiss"
                  >
                    <X size={14} />
                  </button>
                </div>
                <p className="fu-card-desc">{fu.description}</p>
                <div className="fu-card-footer">
                  <span className="fu-person">{fu.person_name}</span>
                  {fu.suggested_action && (
                    <a
                      className="fu-action-btn"
                      href={fu.action_url || "#"}
                      onClick={(e) => {
                        if (!fu.action_url) e.preventDefault();
                      }}
                    >
                      {fu.suggested_action}
                      <ArrowRight size={12} />
                    </a>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fu-container">
      {renderGroup("high", grouped.high)}
      {renderGroup("medium", grouped.medium)}
      {renderGroup("low", grouped.low)}
      <style>{styles}</style>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles = `
  .fu-container {
    padding: 0;
  }
  .fu-loading {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 40px 20px;
    justify-content: center;
    color: var(--text-muted, #71717a);
    font-size: 0.85rem;
  }
  @keyframes fu-spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }
  .fu-spin {
    animation: fu-spin 1s linear infinite;
  }
  .fu-empty {
    text-align: center;
    padding: 60px 20px;
  }
  .fu-btn {
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
  .fu-btn:hover {
    color: var(--accent, #3b82f6);
    border-color: var(--accent, #3b82f6);
  }

  .fu-group {
    margin-bottom: 20px;
  }
  .fu-group:last-child {
    margin-bottom: 0;
  }
  .fu-group-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }
  .fu-priority-badge {
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 3px 10px;
    border-radius: 6px;
  }
  .fu-group-count {
    font-size: 0.72rem;
    color: var(--text-muted, #52525b);
  }

  .fu-cards {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .fu-card {
    background: var(--bg-secondary, #18181b);
    border: 1px solid var(--border, #27272a);
    border-left: 3px solid;
    border-radius: 10px;
    padding: 14px 16px;
  }
  .fu-card-header {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 8px;
  }
  .fu-card-title-area {
    flex: 1;
    min-width: 0;
  }
  .fu-card-title {
    display: block;
    font-size: 0.88rem;
    font-weight: 600;
    color: var(--text-primary, #e4e4e7);
  }
  .fu-card-type {
    font-size: 0.7rem;
    color: var(--text-muted, #52525b);
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .fu-dismiss-btn {
    background: none;
    border: none;
    color: var(--text-muted, #52525b);
    cursor: pointer;
    padding: 2px;
    border-radius: 4px;
    display: flex;
    transition: color 0.15s;
  }
  .fu-dismiss-btn:hover {
    color: var(--text-primary, #e4e4e7);
  }

  .fu-card-desc {
    margin: 0 0 10px;
    font-size: 0.82rem;
    color: var(--text-secondary, #a1a1aa);
    line-height: 1.5;
  }

  .fu-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .fu-person {
    font-size: 0.78rem;
    color: var(--text-muted, #71717a);
  }
  .fu-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border: 1px solid var(--accent, #3b82f6);
    border-radius: 6px;
    background: rgba(59, 130, 246, 0.08);
    color: #60a5fa;
    font-size: 0.78rem;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.15s;
  }
  .fu-action-btn:hover {
    background: rgba(59, 130, 246, 0.18);
  }
`;
