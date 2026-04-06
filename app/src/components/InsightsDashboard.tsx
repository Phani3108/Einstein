import { useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import type { Note } from "../lib/api";
import type { CommitmentData, PersonState, ProjectState } from "../lib/store";
import {
  Brain,
  TrendingUp,
  Lightbulb,
  Link2,
  Calendar,
  BarChart3,
  Sparkles,
  Target,
  RefreshCw,
  FileText,
  CheckSquare,
  Sun,
  ClipboardList,
  Users,
  BookOpen,
  AlertCircle,
  Loader2,
  Briefcase,
  Bell,
  Heart,
} from "lucide-react";
import { MeetingBriefing } from "./MeetingBriefing";
import { WeeklyReport } from "./WeeklyReport";
import { FollowUpSuggestions } from "./FollowUpSuggestions";
import { RelationshipDashboard } from "./RelationshipDashboard";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface TagFrequency {
  tag: string;
  count: number;
}

interface ConnectionOpp {
  noteA: string;
  noteB: string;
  sharedTerms: string[];
}

interface BuildIdea {
  title: string;
  reason: string;
  type: "theme" | "question" | "todo" | "entity";
}

interface KnowledgeGap {
  topic: string;
  mentions: number;
  depth: "shallow" | "moderate";
}

interface DayActivity {
  day: string; // YYYY-MM-DD
  count: number;
}

interface ClientAnalysis {
  totalWords: number;
  avgNoteLength: number;
  tagFrequency: TagFrequency[];
  trendingTopics: TagFrequency[];
  buildIdeas: BuildIdea[];
  knowledgeGaps: KnowledgeGap[];
  connections: ConnectionOpp[];
  heatmap: DayActivity[];
  mostActiveDay: string;
  questionsCount: number;
  todosCount: number;
}

type DashboardTab = "overview" | "weekly" | "monthly" | "meeting_prep" | "weekly_report" | "followups" | "relationships";

/* ------------------------------------------------------------------ */
/*  Client-side analysis helpers                                       */
/* ------------------------------------------------------------------ */

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function extractTags(note: Note): string[] {
  const fm = note.frontmatter;
  const tags: string[] = [];
  if (fm.tags) {
    tags.push(
      ...fm.tags
        .replace(/[\[\]]/g, "")
        .split(",")
        .map((t) => t.trim().toLowerCase())
        .filter(Boolean)
    );
  }
  // Inline #tags
  const inline = note.content.match(/#([a-zA-Z][\w-]{1,30})/g);
  if (inline) {
    tags.push(...inline.map((t) => t.slice(1).toLowerCase()));
  }
  return tags;
}

function extractQuestions(content: string): string[] {
  return content
    .split("\n")
    .filter((l) => l.trim().endsWith("?") && l.trim().length > 8)
    .map((l) => l.trim());
}

function extractTodos(content: string): string[] {
  return content
    .split("\n")
    .filter((l) => /^[-*]\s*\[[ ]\]/.test(l.trim()) || /\bTODO\b/i.test(l))
    .map((l) => l.trim().replace(/^[-*]\s*\[[ ]\]\s*/, ""));
}

function analyzeNotes(notes: Note[]): ClientAnalysis {
  if (notes.length === 0) {
    return {
      totalWords: 0,
      avgNoteLength: 0,
      tagFrequency: [],
      trendingTopics: [],
      buildIdeas: [],
      knowledgeGaps: [],
      connections: [],
      heatmap: [],
      mostActiveDay: "N/A",
      questionsCount: 0,
      todosCount: 0,
    };
  }

  // Word counts
  const wordCounts = notes.map((n) => wordCount(n.content));
  const totalWords = wordCounts.reduce((a, b) => a + b, 0);
  const avgNoteLength = Math.round(totalWords / notes.length);

  // Tag frequency
  const tagMap = new Map<string, number>();
  for (const note of notes) {
    for (const tag of extractTags(note)) {
      tagMap.set(tag, (tagMap.get(tag) ?? 0) + 1);
    }
  }
  const tagFrequency = Array.from(tagMap.entries())
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count);

  // Trending topics: notes updated in last 14 days
  const twoWeeksAgo = Date.now() - 14 * 24 * 3600 * 1000;
  const recentNotes = notes.filter(
    (n) => new Date(n.updated_at).getTime() > twoWeeksAgo
  );
  const recentTagMap = new Map<string, number>();
  for (const note of recentNotes) {
    for (const tag of extractTags(note)) {
      recentTagMap.set(tag, (recentTagMap.get(tag) ?? 0) + 1);
    }
  }
  const trendingTopics = Array.from(recentTagMap.entries())
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 8);

  // Questions & TODOs
  let questionsCount = 0;
  let todosCount = 0;
  const allQuestions: string[] = [];
  const allTodos: string[] = [];
  for (const note of notes) {
    const q = extractQuestions(note.content);
    const t = extractTodos(note.content);
    questionsCount += q.length;
    todosCount += t.length;
    allQuestions.push(...q);
    allTodos.push(...t);
  }

  // Build ideas from patterns
  const buildIdeas: BuildIdea[] = [];
  // Repeated themes
  for (const tf of tagFrequency.slice(0, 3)) {
    if (tf.count >= 2) {
      buildIdeas.push({
        title: `Build around "${tf.tag}"`,
        reason: `Appears in ${tf.count} notes — strong recurring interest`,
        type: "theme",
      });
    }
  }
  // Questions
  for (const q of allQuestions.slice(0, 2)) {
    buildIdeas.push({
      title: `Research: ${q.slice(0, 60)}${q.length > 60 ? "..." : ""}`,
      reason: "Open question found in your notes",
      type: "question",
    });
  }
  // Todos
  if (allTodos.length > 3) {
    buildIdeas.push({
      title: `Prioritize ${allTodos.length} open TODOs`,
      reason: "Multiple incomplete tasks detected across notes",
      type: "todo",
    });
  }

  // Knowledge gaps: tags mentioned but with short total content
  const tagContentLength = new Map<string, number>();
  for (const note of notes) {
    const tags = extractTags(note);
    const len = wordCount(note.content);
    for (const tag of tags) {
      tagContentLength.set(tag, (tagContentLength.get(tag) ?? 0) + len);
    }
  }
  const knowledgeGaps: KnowledgeGap[] = [];
  for (const tf of tagFrequency) {
    const totalLen = tagContentLength.get(tf.tag) ?? 0;
    const avgLen = totalLen / tf.count;
    if (tf.count >= 2 && avgLen < 150) {
      knowledgeGaps.push({
        topic: tf.tag,
        mentions: tf.count,
        depth: avgLen < 80 ? "shallow" : "moderate",
      });
    }
  }

  // Connection opportunities: notes sharing terms in titles but not linked
  const connections: ConnectionOpp[] = [];
  const titleWords = notes.map((n) => ({
    id: n.id,
    title: n.title,
    words: new Set(
      n.title
        .toLowerCase()
        .split(/\W+/)
        .filter((w) => w.length > 3)
    ),
    links: new Set(n.outgoing_links.map((l) => l.toLowerCase())),
  }));
  for (let i = 0; i < titleWords.length && connections.length < 5; i++) {
    for (let j = i + 1; j < titleWords.length && connections.length < 5; j++) {
      const a = titleWords[i];
      const b = titleWords[j];
      // Skip if already linked
      if (
        a.links.has(b.title.toLowerCase()) ||
        b.links.has(a.title.toLowerCase())
      )
        continue;
      const shared = [...a.words].filter((w) => b.words.has(w));
      if (shared.length >= 1) {
        connections.push({
          noteA: a.title,
          noteB: b.title,
          sharedTerms: shared,
        });
      }
    }
  }

  // Activity heatmap (last 30 days)
  const dayMap = new Map<string, number>();
  for (const note of notes) {
    const day = note.updated_at.slice(0, 10);
    dayMap.set(day, (dayMap.get(day) ?? 0) + 1);
  }
  const heatmap = Array.from(dayMap.entries())
    .map(([day, count]) => ({ day, count }))
    .sort((a, b) => a.day.localeCompare(b.day))
    .slice(-35);

  // Most active day of week
  const dowCounts = [0, 0, 0, 0, 0, 0, 0];
  const dowNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  for (const note of notes) {
    const d = new Date(note.updated_at).getDay();
    dowCounts[d]++;
  }
  const maxDow = dowCounts.indexOf(Math.max(...dowCounts));
  const mostActiveDay = dowNames[maxDow];

  return {
    totalWords,
    avgNoteLength,
    tagFrequency,
    trendingTopics,
    buildIdeas,
    knowledgeGaps,
    connections,
    heatmap,
    mostActiveDay,
    questionsCount,
    todosCount,
  };
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "Unknown";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function daysAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "No contact recorded";
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  const diff = Math.floor((Date.now() - d.getTime()) / (1000 * 60 * 60 * 24));
  if (diff === 0) return "Today";
  if (diff === 1) return "Yesterday";
  return `${diff} days ago`;
}

/* ------------------------------------------------------------------ */
/*  Skeleton loader                                                    */
/* ------------------------------------------------------------------ */

function Skeleton({ width = "100%", height = 16 }: { width?: string | number; height?: number }) {
  return (
    <div
      className="insights-skeleton"
      style={{ width, height, borderRadius: 6 }}
    />
  );
}

function SkeletonCard() {
  return (
    <div className="insights-card">
      <div className="insights-card-header">
        <Skeleton width={24} height={24} />
        <Skeleton width="60%" height={18} />
      </div>
      <div className="insights-card-body">
        <Skeleton width="90%" />
        <Skeleton width="75%" />
        <Skeleton width="80%" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Insight Card                                                       */
/* ------------------------------------------------------------------ */

function InsightCard({
  icon,
  title,
  children,
  accentColor,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
  accentColor?: string;
}) {
  return (
    <div className="insights-card" style={{ "--card-accent": accentColor ?? "var(--accent, #3b82f6)" } as React.CSSProperties}>
      <div className="insights-card-header">
        <span className="insights-card-icon">{icon}</span>
        <h3 className="insights-card-title">{title}</h3>
      </div>
      <div className="insights-card-body">{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Heatmap Grid                                                       */
/* ------------------------------------------------------------------ */

function Heatmap({ data }: { data: DayActivity[] }) {
  if (data.length === 0) {
    return <p className="insights-empty">No activity data yet.</p>;
  }
  const maxCount = Math.max(...data.map((d) => d.count), 1);
  return (
    <div className="insights-heatmap">
      {data.map((d) => {
        const intensity = d.count / maxCount;
        const bg =
          intensity === 0
            ? "var(--bg-tertiary, #0f0f12)"
            : `rgba(59, 130, 246, ${0.15 + intensity * 0.75})`;
        return (
          <div
            key={d.day}
            className="insights-heatmap-cell"
            style={{ background: bg }}
            title={`${d.day}: ${d.count} note${d.count !== 1 ? "s" : ""}`}
          />
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Commitments grouped by status                                      */
/* ------------------------------------------------------------------ */

function CommitmentsTracker({ commitments }: { commitments: CommitmentData[] }) {
  if (commitments.length === 0) {
    return <p className="insights-empty">No commitments tracked yet.</p>;
  }

  const overdue = commitments.filter((c) => c.status === "overdue");
  const pending = commitments.filter((c) => c.status === "pending" || c.status === "open");
  const completed = commitments.filter((c) => c.status === "completed" || c.status === "done");

  const renderGroup = (items: CommitmentData[], label: string, statusClass: string) => {
    if (items.length === 0) return null;
    return (
      <div className="insights-commitment-group">
        <div className={`insights-commitment-label ${statusClass}`}>
          {label} ({items.length})
        </div>
        {items.slice(0, 5).map((c) => (
          <div key={c.id} className={`insights-commitment-item ${statusClass}`}>
            <span className="insights-commitment-content">{c.content}</span>
            <span className="insights-commitment-meta">
              {c.person_name && <span>{c.person_name}</span>}
              {c.due_date && <span> &middot; {formatDate(c.due_date)}</span>}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="insights-commitments">
      {renderGroup(overdue, "Overdue", "commitment-overdue")}
      {renderGroup(pending, "Pending", "commitment-pending")}
      {renderGroup(completed, "Completed", "commitment-completed")}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Relationship Health                                                */
/* ------------------------------------------------------------------ */

function RelationshipHealth({
  dormantPeople,
  dormantProjects,
}: {
  dormantPeople: PersonState[];
  dormantProjects: ProjectState[];
}) {
  if (dormantPeople.length === 0 && dormantProjects.length === 0) {
    return <p className="insights-empty">All relationships are fresh. Great job staying connected!</p>;
  }

  return (
    <div>
      {dormantPeople.length > 0 && (
        <div className="insights-relationship-section">
          <h4 className="insights-section-label">Contacts needing attention</h4>
          <ul className="insights-list">
            {dormantPeople.slice(0, 5).map((p) => (
              <li key={p.id} className="insights-list-item">
                <Users size={14} style={{ color: "#ef4444", flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <strong>{p.name}</strong>
                  {p.role && <span style={{ fontWeight: 400, marginLeft: 6, fontSize: "0.75rem", color: "var(--text-muted, #71717a)" }}>{p.role}{p.organization ? ` at ${p.organization}` : ""}</span>}
                  <p>Last contact: {daysAgo(p.last_contact)}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      {dormantProjects.length > 0 && (
        <div className="insights-relationship-section" style={{ marginTop: dormantPeople.length > 0 ? 12 : 0 }}>
          <h4 className="insights-section-label">Projects going stale</h4>
          <ul className="insights-list">
            {dormantProjects.slice(0, 5).map((p) => (
              <li key={p.id} className="insights-list-item">
                <BookOpen size={14} style={{ color: "#f59e0b", flexShrink: 0, marginTop: 2 }} />
                <div style={{ flex: 1 }}>
                  <strong>{p.title}</strong>
                  <p>Updated {daysAgo(p.updated_at)} &middot; Status: {p.status}</p>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Reflection Tab Content (Weekly / Monthly)                          */
/* ------------------------------------------------------------------ */

function ReflectionTab({
  label,
  loadFn,
}: {
  label: string;
  loadFn: () => Promise<any>;
}) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await loadFn();
      setData(result);
    } catch (e: any) {
      setError(e?.message || `Failed to load ${label.toLowerCase()}`);
    } finally {
      setLoading(false);
    }
  }, [loadFn, label]);

  if (!data && !loading && !error) {
    return (
      <div className="insights-reflection-empty">
        <BookOpen size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
        <h3>{label}</h3>
        <p>Generate a {label.toLowerCase()} to reflect on your progress and patterns.</p>
        <button className="insights-ai-btn" onClick={load}>
          <Sparkles size={14} />
          Load {label}
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="insights-reflection-loading">
        <Loader2 size={24} className="insights-spin" />
        <p>Generating {label.toLowerCase()}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="insights-reflection-error">
        <AlertCircle size={18} />
        <span>{error}</span>
        <button className="insights-ai-btn" onClick={load} style={{ marginLeft: 12 }}>
          Retry
        </button>
      </div>
    );
  }

  // Render the review/reflection data
  return (
    <div className="insights-reflection-content">
      <div className="insights-reflection-header">
        <h3>{label}</h3>
        <button className="insights-refresh-btn" onClick={load} title={`Reload ${label.toLowerCase()}`}>
          <RefreshCw size={14} />
        </button>
      </div>
      {typeof data === "string" ? (
        <div className="insights-reflection-text">{data}</div>
      ) : (
        <div className="insights-reflection-structured">
          {data.summary && (
            <div className="insights-reflection-section">
              <h4>Summary</h4>
              <p>{data.summary}</p>
            </div>
          )}
          {data.highlights && data.highlights.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Highlights</h4>
              <ul>{data.highlights.map((h: string, i: number) => <li key={i}>{h}</li>)}</ul>
            </div>
          )}
          {data.themes && data.themes.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Themes</h4>
              <div className="insights-tags-cloud">
                {data.themes.map((t: string, i: number) => (
                  <span key={i} className="insights-tag">{t}</span>
                ))}
              </div>
            </div>
          )}
          {data.accomplishments && data.accomplishments.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Accomplishments</h4>
              <ul>{data.accomplishments.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul>
            </div>
          )}
          {data.challenges && data.challenges.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Challenges</h4>
              <ul>{data.challenges.map((c: string, i: number) => <li key={i}>{c}</li>)}</ul>
            </div>
          )}
          {data.recommendations && data.recommendations.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Recommendations</h4>
              <ul>{data.recommendations.map((r: string, i: number) => <li key={i}>{r}</li>)}</ul>
            </div>
          )}
          {data.attention_needed && data.attention_needed.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Needs Attention</h4>
              <ul>{data.attention_needed.map((a: string, i: number) => <li key={i}>{a}</li>)}</ul>
            </div>
          )}
          {data.patterns && (typeof data.patterns === "string" ? (
            <div className="insights-reflection-section">
              <h4>Patterns</h4>
              <p>{data.patterns}</p>
            </div>
          ) : Array.isArray(data.patterns) && data.patterns.length > 0 && (
            <div className="insights-reflection-section">
              <h4>Patterns</h4>
              <ul>{data.patterns.map((p: string, i: number) => <li key={i}>{p}</li>)}</ul>
            </div>
          ))}
          {/* Fallback: render any remaining top-level string/array keys */}
          {Object.entries(data).filter(([k]) =>
            !["summary", "highlights", "themes", "accomplishments", "challenges", "recommendations", "attention_needed", "patterns"].includes(k)
          ).map(([key, val]) => {
            if (typeof val === "string" && val.length > 0) {
              return (
                <div key={key} className="insights-reflection-section">
                  <h4>{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</h4>
                  <p>{val}</p>
                </div>
              );
            }
            if (Array.isArray(val) && val.length > 0 && typeof val[0] === "string") {
              return (
                <div key={key} className="insights-reflection-section">
                  <h4>{key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</h4>
                  <ul>{(val as string[]).map((item, i) => <li key={i}>{item}</li>)}</ul>
                </div>
              );
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function InsightsDashboard() {
  const { state, dispatch } = useApp();
  const notes = state.notes;

  const [activeTab, setActiveTab] = useState<DashboardTab>("overview");
  const [refreshing, setRefreshing] = useState(false);

  // Client-side analysis (memoized)
  const analysis = useMemo(() => analyzeNotes(notes), [notes]);

  // Backend intelligence data from store
  const briefing = state.morningBriefing;
  const commitments = state.commitments;
  const dormantPeople = state.dormantPeople;
  const dormantProjects = state.dormantProjects;

  // Refresh handler — reload intelligence data from backend
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      const [newBriefing, newCommitments, newDormantPeople, newDormantProjects] = await Promise.allSettled([
        api.getMorningBriefing(),
        api.getCommitments(),
        api.getDormantPeople(),
        api.getDormantProjects(),
      ]);
      if (newBriefing.status === "fulfilled" && newBriefing.value) {
        dispatch({ type: "SET_BRIEFING", briefing: newBriefing.value });
      }
      if (newCommitments.status === "fulfilled" && newCommitments.value) {
        dispatch({ type: "SET_COMMITMENTS", commitments: newCommitments.value });
      }
      if (newDormantPeople.status === "fulfilled" && newDormantPeople.value) {
        dispatch({ type: "SET_DORMANT_PEOPLE", people: newDormantPeople.value });
      }
      if (newDormantProjects.status === "fulfilled" && newDormantProjects.value) {
        dispatch({ type: "SET_DORMANT_PROJECTS", projects: newDormantProjects.value });
      }
    } catch {
      // Silently fail — existing data remains
    } finally {
      setRefreshing(false);
    }
  }, [dispatch]);

  // Smart suggestions
  const suggestions = useMemo(() => {
    const s: { text: string; icon: React.ReactNode }[] = [];
    if (notes.length > 5 && analysis.tagFrequency.length === 0) {
      s.push({
        text: "Add tags to your notes to unlock pattern detection.",
        icon: <Target size={14} />,
      });
    }
    if (analysis.connections.length > 0) {
      s.push({
        text: `${analysis.connections.length} notes could be cross-linked to strengthen your knowledge graph.`,
        icon: <Link2 size={14} />,
      });
    }
    if (analysis.todosCount > 5) {
      s.push({
        text: `You have ${analysis.todosCount} open TODOs. Consider a weekly review to stay on top.`,
        icon: <Target size={14} />,
      });
    }
    if (analysis.knowledgeGaps.length > 0) {
      s.push({
        text: `Expand on "${analysis.knowledgeGaps[0].topic}" — you mention it often but haven't gone deep.`,
        icon: <Brain size={14} />,
      });
    }
    if (notes.length > 0 && notes.length < 10) {
      s.push({
        text: "Keep writing! Insights improve significantly after 10+ notes.",
        icon: <Sparkles size={14} />,
      });
    }
    if (analysis.questionsCount > 0) {
      s.push({
        text: `${analysis.questionsCount} open question${analysis.questionsCount > 1 ? "s" : ""} detected. Turn them into research projects.`,
        icon: <Lightbulb size={14} />,
      });
    }
    return s;
  }, [notes, analysis]);

  return (
    <div className="main-content" style={{ overflow: "auto" }}>
      {/* Header */}
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <Brain size={14} style={{ marginRight: 6 }} />
          <span>Insights &amp; Ideas</span>
        </div>
        <button
          className="insights-refresh-btn"
          onClick={handleRefresh}
          disabled={refreshing}
          title="Refresh insights"
        >
          <RefreshCw size={14} className={refreshing ? "insights-spin" : ""} />
        </button>
      </div>

      <div className="insights-wrapper">
        {/* Tab Bar */}
        <div className="insights-tab-bar">
          <button
            className={`insights-tab ${activeTab === "overview" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            <BarChart3 size={14} />
            Overview
          </button>
          <button
            className={`insights-tab ${activeTab === "weekly" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("weekly")}
          >
            <Calendar size={14} />
            Weekly Review
          </button>
          <button
            className={`insights-tab ${activeTab === "monthly" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("monthly")}
          >
            <BookOpen size={14} />
            Monthly Reflection
          </button>
          <button
            className={`insights-tab ${activeTab === "meeting_prep" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("meeting_prep")}
          >
            <Briefcase size={14} />
            Meeting Prep
          </button>
          <button
            className={`insights-tab ${activeTab === "weekly_report" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("weekly_report")}
          >
            <BarChart3 size={14} />
            Weekly Report
          </button>
          <button
            className={`insights-tab ${activeTab === "followups" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("followups")}
          >
            <Bell size={14} />
            Follow-ups
          </button>
          <button
            className={`insights-tab ${activeTab === "relationships" ? "insights-tab-active" : ""}`}
            onClick={() => setActiveTab("relationships")}
          >
            <Heart size={14} />
            Relationships
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <>
            {/* Stats Row */}
            <div className="insights-stats-row">
              <div className="insights-stat">
                <span className="insights-stat-value">{notes.length}</span>
                <span className="insights-stat-label">Total Notes</span>
              </div>
              <div className="insights-stat">
                <span className="insights-stat-value">
                  {analysis.totalWords.toLocaleString()}
                </span>
                <span className="insights-stat-label">Total Words</span>
              </div>
              <div className="insights-stat">
                <span className="insights-stat-value">
                  {analysis.avgNoteLength.toLocaleString()}
                </span>
                <span className="insights-stat-label">Avg Note Length</span>
              </div>
              <div className="insights-stat">
                <span className="insights-stat-value">{analysis.mostActiveDay}</span>
                <span className="insights-stat-label">Most Active Day</span>
              </div>
            </div>

            {/* Cards Grid */}
            {notes.length === 0 ? (
              <div className="insights-empty-state">
                <Brain size={48} />
                <h2>No notes yet</h2>
                <p>Create some notes and come back for insights about your knowledge base.</p>
              </div>
            ) : (
              <div className="insights-grid">
                {/* Morning Briefing */}
                <InsightCard
                  icon={<Sun size={18} />}
                  title="Morning Briefing"
                  accentColor="#3b82f6"
                >
                  {briefing ? (
                    <div>
                      {briefing.summary && (
                        <p style={{ marginTop: 0, marginBottom: 12, lineHeight: 1.6 }}>{briefing.summary}</p>
                      )}
                      {briefing.attention_items && briefing.attention_items.length > 0 && (
                        <div>
                          <h4 className="insights-section-label">Attention items</h4>
                          <ul className="insights-attention-list">
                            {briefing.attention_items.map((item: any, i: number) => (
                              <li key={i}>
                                <AlertCircle size={12} />
                                <span>{typeof item === "string" ? item : item.description || item.title || JSON.stringify(item)}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {briefing.today_event_count > 0 && (
                        <p className="insights-meta-line">
                          <Calendar size={12} /> {briefing.today_event_count} event{briefing.today_event_count !== 1 ? "s" : ""} today
                        </p>
                      )}
                    </div>
                  ) : (
                    <p className="insights-empty">
                      No briefing available yet. Hit refresh to generate one.
                    </p>
                  )}
                </InsightCard>

                {/* Commitments Tracker */}
                <InsightCard
                  icon={<ClipboardList size={18} />}
                  title="Commitments Tracker"
                  accentColor="#8b5cf6"
                >
                  <CommitmentsTracker commitments={commitments} />
                </InsightCard>

                {/* Relationship Health */}
                <InsightCard
                  icon={<Users size={18} />}
                  title="Relationship Health"
                  accentColor="#ef4444"
                >
                  <RelationshipHealth
                    dormantPeople={dormantPeople}
                    dormantProjects={dormantProjects}
                  />
                </InsightCard>

                {/* What to Build Next */}
                <InsightCard
                  icon={<Lightbulb size={18} />}
                  title="What to Build Next"
                  accentColor="#f59e0b"
                >
                  {analysis.buildIdeas.length > 0 ? (
                    <ul className="insights-list">
                      {analysis.buildIdeas.map((idea, i) => (
                        <li key={i} className="insights-list-item">
                          <span
                            className="insights-idea-type"
                            data-type={idea.type}
                          >
                            {idea.type}
                          </span>
                          <div style={{ flex: 1 }}>
                            <strong>{idea.title}</strong>
                            <p>{idea.reason}</p>
                          </div>
                          <div className="insights-actions">
                            <button
                              className="insights-action-btn"
                              title="Create Note"
                              onClick={async () => {
                                const content = `# ${idea.title}\n\n${idea.reason}\n\n## Plan\n\n- [ ] \n\n## Notes\n\n`;
                                const result = await createNoteAndProcess(idea.title, content, dispatch, { source: "insight-build-idea" });
                                dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
                                dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
                              }}
                            >
                              <FileText size={12} />
                            </button>
                            <button
                              className="insights-action-btn"
                              title="Create Task"
                              onClick={async () => {
                                await api.saveActionItems("insight", [{
                                  task: `Build: ${idea.title}`,
                                  assignee: null,
                                  deadline: null,
                                  priority: "medium",
                                }]);
                                const items = await api.getActionItems();
                                dispatch({ type: "SET_ACTION_ITEMS", items: items.map(item => ({
                                  ...item,
                                  priority: item.priority as "high" | "medium" | "low",
                                  status: item.status as "pending" | "completed" | "cancelled",
                                  source_title: "Insight",
                                })) });
                              }}
                            >
                              <CheckSquare size={12} />
                            </button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="insights-empty">
                      Add more notes with tags and questions to generate project ideas.
                    </p>
                  )}
                </InsightCard>

                {/* Knowledge Gaps */}
                <InsightCard
                  icon={<Target size={18} />}
                  title="Knowledge Gaps"
                  accentColor="#ef4444"
                >
                  {analysis.knowledgeGaps.length > 0 ? (
                    <ul className="insights-list">
                      {analysis.knowledgeGaps.slice(0, 5).map((gap, i) => (
                        <li key={i} className="insights-list-item">
                          <span
                            className="insights-depth-badge"
                            data-depth={gap.depth}
                          >
                            {gap.depth}
                          </span>
                          <div style={{ flex: 1 }}>
                            <strong>{gap.topic}</strong>
                            <p>
                              Mentioned {gap.mentions} times but content is thin.
                            </p>
                          </div>
                          <button
                            className="insights-action-btn"
                            title="Create Note to fill gap"
                            onClick={async () => {
                              const content = `# ${gap.topic}\n\nThis topic has been mentioned ${gap.mentions} times across notes but needs deeper exploration.\n\n## Key Questions\n\n- \n\n## Research\n\n`;
                              const result = await createNoteAndProcess(gap.topic, content, dispatch, { source: "insight-knowledge-gap" });
                              dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
                              dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
                            }}
                          >
                            <FileText size={12} />
                          </button>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="insights-empty">
                      No knowledge gaps detected. Your notes are well-covered!
                    </p>
                  )}
                </InsightCard>

                {/* Trending Topics */}
                <InsightCard
                  icon={<TrendingUp size={18} />}
                  title="Trending Topics"
                  accentColor="#10b981"
                >
                  {analysis.trendingTopics.length > 0 ? (
                    <div className="insights-tags-cloud">
                      {analysis.trendingTopics.map((t) => (
                        <span key={t.tag} className="insights-tag">
                          #{t.tag}
                          <span className="insights-tag-count">{t.count}</span>
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="insights-empty">
                      No trending topics in the last 2 weeks.
                    </p>
                  )}
                  {analysis.tagFrequency.length > 0 && (
                    <div className="insights-all-tags">
                      <h4>All-time top tags</h4>
                      <div className="insights-bar-list">
                        {analysis.tagFrequency.slice(0, 6).map((t) => (
                          <div key={t.tag} className="insights-bar-row">
                            <span className="insights-bar-label">#{t.tag}</span>
                            <div className="insights-bar-track">
                              <div
                                className="insights-bar-fill"
                                style={{
                                  width: `${(t.count / (analysis.tagFrequency[0]?.count || 1)) * 100}%`,
                                }}
                              />
                            </div>
                            <span className="insights-bar-value">{t.count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </InsightCard>

                {/* Connection Opportunities */}
                <InsightCard
                  icon={<Link2 size={18} />}
                  title="Connection Opportunities"
                  accentColor="#8b5cf6"
                >
                  {analysis.connections.length > 0 ? (
                    <ul className="insights-list">
                      {analysis.connections.map((c, i) => (
                        <li key={i} className="insights-connection-item">
                          <div className="insights-connection-pair">
                            <span className="insights-connection-note">
                              {c.noteA}
                            </span>
                            <Link2 size={12} />
                            <span className="insights-connection-note">
                              {c.noteB}
                            </span>
                          </div>
                          <p className="insights-connection-reason">
                            Shared: {c.sharedTerms.join(", ")}
                          </p>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="insights-empty">
                      No unlinked connections found. Your notes are well-connected!
                    </p>
                  )}
                </InsightCard>

                {/* Activity Heatmap */}
                <InsightCard
                  icon={<Calendar size={18} />}
                  title="Activity Heatmap"
                  accentColor="#06b6d4"
                >
                  <Heatmap data={analysis.heatmap} />
                  <div className="insights-heatmap-legend">
                    <span>Less</span>
                    <div className="insights-heatmap-scale">
                      <div style={{ background: "var(--bg-tertiary, #0f0f12)" }} />
                      <div style={{ background: "rgba(59,130,246,0.25)" }} />
                      <div style={{ background: "rgba(59,130,246,0.5)" }} />
                      <div style={{ background: "rgba(59,130,246,0.75)" }} />
                      <div style={{ background: "rgba(59,130,246,0.9)" }} />
                    </div>
                    <span>More</span>
                  </div>
                </InsightCard>

                {/* Smart Suggestions */}
                <InsightCard
                  icon={<BarChart3 size={18} />}
                  title="Smart Suggestions"
                  accentColor="#f97316"
                >
                  {suggestions.length > 0 ? (
                    <ul className="insights-suggestions">
                      {suggestions.map((s, i) => (
                        <li key={i}>
                          {s.icon}
                          <span>{s.text}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="insights-empty">
                      Looking good! No suggestions right now.
                    </p>
                  )}
                </InsightCard>
              </div>
            )}
          </>
        )}

        {activeTab === "weekly" && (
          <ReflectionTab label="Weekly Review" loadFn={api.getWeeklyReview} />
        )}

        {activeTab === "monthly" && (
          <ReflectionTab label="Monthly Reflection" loadFn={api.getMonthlyReflection} />
        )}

        {activeTab === "meeting_prep" && <MeetingBriefing />}
        {activeTab === "weekly_report" && <WeeklyReport />}
        {activeTab === "followups" && <FollowUpSuggestions />}
        {activeTab === "relationships" && <RelationshipDashboard />}
      </div>

      <style>{`
        /* Wrapper */
        .insights-wrapper {
          max-width: 900px;
          margin: 0 auto;
          padding: 24px 28px 48px;
        }

        /* Tab bar */
        .insights-tab-bar {
          display: flex;
          gap: 4px;
          margin-bottom: 20px;
          padding: 4px;
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          flex-wrap: wrap;
        }
        .insights-tab {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 8px 16px;
          border: none;
          border-radius: 7px;
          background: none;
          color: var(--text-muted, #a1a1aa);
          font-size: 0.82rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s;
          flex: 1;
          justify-content: center;
        }
        .insights-tab:hover {
          color: var(--text-primary, #e4e4e7);
          background: var(--bg-tertiary, #0f0f12);
        }
        .insights-tab-active {
          background: var(--accent, #3b82f6);
          color: #fff;
        }
        .insights-tab-active:hover {
          background: var(--accent, #3b82f6);
          color: #fff;
        }

        /* Refresh button */
        .insights-refresh-btn {
          background: none;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          padding: 4px 8px;
          cursor: pointer;
          color: var(--text-muted, #a1a1aa);
          display: flex;
          align-items: center;
          margin-left: auto;
          transition: color 0.15s, border-color 0.15s;
        }
        .insights-refresh-btn:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }
        .insights-refresh-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        /* Spin animation */
        @keyframes insights-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .insights-spin {
          animation: insights-spin 1s linear infinite;
        }

        /* Stats row */
        .insights-stats-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 12px;
          margin-bottom: 20px;
        }
        .insights-stat {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        .insights-stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .insights-stat-label {
          font-size: 0.75rem;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        /* Cards grid */
        .insights-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 16px;
        }

        /* Card */
        .insights-card {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          padding: 20px;
          transition: border-color 0.15s;
        }
        .insights-card:hover {
          border-color: var(--card-accent, var(--accent, #3b82f6));
        }
        .insights-card-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 14px;
        }
        .insights-card-icon {
          color: var(--card-accent, var(--accent, #3b82f6));
          display: flex;
          align-items: center;
        }
        .insights-card-title {
          margin: 0;
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .insights-card-body {
          font-size: 0.85rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.6;
        }

        /* Section label */
        .insights-section-label {
          margin: 0 0 8px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--text-muted, #71717a);
        }

        /* Attention list (briefing) */
        .insights-attention-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .insights-attention-list li {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 6px 0;
          font-size: 0.82rem;
          color: var(--text-secondary, #a1a1aa);
        }
        .insights-attention-list li svg {
          color: #f59e0b;
          flex-shrink: 0;
          margin-top: 2px;
        }

        /* Meta line */
        .insights-meta-line {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 12px;
          padding-top: 10px;
          border-top: 1px solid var(--border, #27272a);
          font-size: 0.78rem;
          color: var(--text-muted, #71717a);
        }
        .insights-meta-line svg {
          flex-shrink: 0;
        }

        /* Commitments */
        .insights-commitments {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .insights-commitment-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .insights-commitment-label {
          font-size: 0.72rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 2px 8px;
          border-radius: 4px;
          display: inline-block;
          width: fit-content;
          margin-bottom: 4px;
        }
        .insights-commitment-label.commitment-overdue {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .insights-commitment-label.commitment-pending {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .insights-commitment-label.commitment-completed {
          background: rgba(16, 185, 129, 0.15);
          color: #10b981;
        }
        .insights-commitment-item {
          padding: 6px 10px;
          border-radius: 6px;
          border-left: 3px solid transparent;
        }
        .insights-commitment-item.commitment-overdue {
          border-left-color: #ef4444;
          background: rgba(239, 68, 68, 0.05);
        }
        .insights-commitment-item.commitment-pending {
          border-left-color: #f59e0b;
          background: rgba(245, 158, 11, 0.05);
        }
        .insights-commitment-item.commitment-completed {
          border-left-color: #10b981;
          background: rgba(16, 185, 129, 0.05);
        }
        .insights-commitment-content {
          display: block;
          font-size: 0.82rem;
          color: var(--text-primary, #e4e4e7);
          margin-bottom: 2px;
        }
        .insights-commitment-meta {
          font-size: 0.72rem;
          color: var(--text-muted, #71717a);
        }

        /* Relationship sections */
        .insights-relationship-section {
          margin-bottom: 4px;
        }

        /* Lists */
        .insights-list {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .insights-list-item {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 10px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .insights-list-item:last-child {
          border-bottom: none;
        }
        .insights-list-item strong {
          display: block;
          color: var(--text-primary, #e4e4e7);
          font-size: 0.85rem;
          margin-bottom: 2px;
        }
        .insights-list-item p {
          margin: 0;
          font-size: 0.78rem;
          color: var(--text-muted, #71717a);
        }
        .insights-arrow {
          color: var(--text-muted, #71717a);
          margin-left: auto;
          flex-shrink: 0;
          margin-top: 4px;
        }
        .insights-actions {
          display: flex;
          gap: 4px;
          flex-shrink: 0;
          margin-left: 8px;
        }
        .insights-action-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 26px;
          height: 26px;
          border-radius: 6px;
          border: 1px solid var(--border, #27272a);
          background: none;
          color: var(--text-muted, #71717a);
          cursor: pointer;
          transition: all 0.15s;
        }
        .insights-action-btn:hover {
          color: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          background: rgba(59, 130, 246, 0.08);
        }

        /* Idea type badge */
        .insights-idea-type {
          font-size: 0.68rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 2px 8px;
          border-radius: 6px;
          flex-shrink: 0;
          margin-top: 2px;
        }
        .insights-idea-type[data-type="theme"] {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }
        .insights-idea-type[data-type="question"] {
          background: rgba(59, 130, 246, 0.15);
          color: #3b82f6;
        }
        .insights-idea-type[data-type="todo"] {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .insights-idea-type[data-type="entity"] {
          background: rgba(139, 92, 246, 0.15);
          color: #8b5cf6;
        }

        /* Depth badge */
        .insights-depth-badge {
          font-size: 0.68rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 2px 8px;
          border-radius: 6px;
          flex-shrink: 0;
          margin-top: 2px;
        }
        .insights-depth-badge[data-depth="shallow"] {
          background: rgba(239, 68, 68, 0.15);
          color: #ef4444;
        }
        .insights-depth-badge[data-depth="moderate"] {
          background: rgba(245, 158, 11, 0.15);
          color: #f59e0b;
        }

        /* Tags cloud */
        .insights-tags-cloud {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 16px;
        }
        .insights-tag {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 5px 12px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 16px;
          font-size: 0.82rem;
          color: var(--text-primary, #e4e4e7);
        }
        .insights-tag-count {
          font-size: 0.72rem;
          color: var(--accent, #3b82f6);
          font-weight: 600;
        }

        /* All-time tags bar chart */
        .insights-all-tags {
          margin-top: 12px;
          padding-top: 12px;
          border-top: 1px solid var(--border, #27272a);
        }
        .insights-all-tags h4 {
          margin: 0 0 10px;
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }
        .insights-bar-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .insights-bar-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .insights-bar-label {
          width: 80px;
          font-size: 0.78rem;
          color: var(--text-secondary, #a1a1aa);
          text-align: right;
          flex-shrink: 0;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .insights-bar-track {
          flex: 1;
          height: 8px;
          background: var(--bg-tertiary, #0f0f12);
          border-radius: 4px;
          overflow: hidden;
        }
        .insights-bar-fill {
          height: 100%;
          background: var(--accent, #3b82f6);
          border-radius: 4px;
          transition: width 0.4s ease;
        }
        .insights-bar-value {
          width: 24px;
          font-size: 0.75rem;
          color: var(--text-muted, #71717a);
          text-align: right;
          flex-shrink: 0;
        }

        /* Connections */
        .insights-connection-item {
          padding: 10px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .insights-connection-item:last-child {
          border-bottom: none;
        }
        .insights-connection-pair {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }
        .insights-connection-pair svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .insights-connection-note {
          font-size: 0.82rem;
          font-weight: 500;
          color: var(--text-primary, #e4e4e7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .insights-connection-reason {
          margin: 0;
          font-size: 0.75rem;
          color: var(--text-muted, #71717a);
          padding-left: 2px;
        }

        /* Heatmap */
        .insights-heatmap {
          display: grid;
          grid-template-columns: repeat(7, 1fr);
          gap: 3px;
        }
        .insights-heatmap-cell {
          aspect-ratio: 1;
          border-radius: 3px;
          border: 1px solid var(--border, #27272a);
          transition: transform 0.1s;
        }
        .insights-heatmap-cell:hover {
          transform: scale(1.3);
          z-index: 1;
        }
        .insights-heatmap-legend {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          gap: 6px;
          margin-top: 10px;
          font-size: 0.7rem;
          color: var(--text-muted, #71717a);
        }
        .insights-heatmap-scale {
          display: flex;
          gap: 2px;
        }
        .insights-heatmap-scale div {
          width: 12px;
          height: 12px;
          border-radius: 2px;
          border: 1px solid var(--border, #27272a);
        }

        /* Suggestions */
        .insights-suggestions {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .insights-suggestions li {
          display: flex;
          align-items: flex-start;
          gap: 10px;
          padding: 10px 12px;
          border-left: 3px solid var(--card-accent, var(--accent, #3b82f6));
          margin-bottom: 8px;
          background: var(--bg-tertiary, #0f0f12);
          border-radius: 0 8px 8px 0;
          font-size: 0.82rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.5;
        }
        .insights-suggestions li svg {
          flex-shrink: 0;
          margin-top: 2px;
          color: var(--card-accent, var(--accent, #3b82f6));
        }

        /* Empty text */
        .insights-empty {
          color: var(--text-muted, #71717a);
          font-size: 0.82rem;
          font-style: italic;
        }

        /* Empty state */
        .insights-empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 64px 24px;
          text-align: center;
          color: var(--text-muted, #71717a);
        }
        .insights-empty-state svg {
          margin-bottom: 16px;
          opacity: 0.3;
        }
        .insights-empty-state h2 {
          margin: 0 0 8px;
          font-size: 1.2rem;
          color: var(--text-secondary, #a1a1aa);
        }
        .insights-empty-state p {
          margin: 0;
          font-size: 0.88rem;
        }

        /* Skeleton */
        .insights-skeleton {
          background: linear-gradient(
            90deg,
            var(--bg-tertiary, #0f0f12) 25%,
            var(--border, #27272a) 50%,
            var(--bg-tertiary, #0f0f12) 75%
          );
          background-size: 200% 100%;
          animation: insights-shimmer 1.5s infinite;
          margin-bottom: 8px;
        }
        @keyframes insights-shimmer {
          0% { background-position: 200% 0; }
          100% { background-position: -200% 0; }
        }

        /* Reflection tab content */
        .insights-reflection-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 48px 24px;
          text-align: center;
          color: var(--text-muted, #71717a);
        }
        .insights-reflection-empty h3 {
          margin: 0 0 8px;
          font-size: 1.1rem;
          color: var(--text-secondary, #a1a1aa);
        }
        .insights-reflection-empty p {
          margin: 0 0 20px;
          font-size: 0.88rem;
          max-width: 400px;
        }
        .insights-reflection-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 64px 24px;
          color: var(--text-muted, #71717a);
          gap: 12px;
        }
        .insights-reflection-error {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 18px;
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.2);
          border-radius: 10px;
          color: #ef4444;
          font-size: 0.85rem;
        }
        .insights-reflection-content {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 12px;
          padding: 24px;
        }
        .insights-reflection-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 20px;
        }
        .insights-reflection-header h3 {
          margin: 0;
          font-size: 1.1rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .insights-reflection-text {
          font-size: 0.88rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.7;
          white-space: pre-wrap;
        }
        .insights-reflection-structured {
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .insights-reflection-section h4 {
          margin: 0 0 8px;
          font-size: 0.82rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.04em;
          color: var(--accent, #3b82f6);
        }
        .insights-reflection-section p {
          margin: 0;
          font-size: 0.85rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.7;
        }
        .insights-reflection-section ul {
          margin: 0;
          padding-left: 18px;
        }
        .insights-reflection-section li {
          font-size: 0.85rem;
          color: var(--text-secondary, #a1a1aa);
          line-height: 1.6;
          margin-bottom: 4px;
        }

        /* AI button (shared) */
        .insights-ai-btn {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          padding: 8px 18px;
          border: none;
          border-radius: 8px;
          background: var(--accent, #3b82f6);
          color: #fff;
          font-size: 0.85rem;
          font-weight: 600;
          cursor: pointer;
          transition: opacity 0.15s, transform 0.1s;
        }
        .insights-ai-btn:hover {
          opacity: 0.9;
        }
        .insights-ai-btn:active {
          transform: scale(0.97);
        }
        .insights-ai-btn:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }

        /* Responsive */
        @media (max-width: 700px) {
          .insights-stats-row {
            grid-template-columns: repeat(2, 1fr);
          }
          .insights-grid {
            grid-template-columns: 1fr;
          }
          .insights-tab-bar {
            flex-wrap: wrap;
          }
        }
      `}</style>
    </div>
  );
}
