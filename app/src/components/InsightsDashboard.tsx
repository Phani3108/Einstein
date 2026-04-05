import { useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import type { Note } from "../lib/api";
import {
  Brain,
  TrendingUp,
  Lightbulb,
  Link2,
  Calendar,
  BarChart3,
  Sparkles,
  Target,
  ArrowRight,
  RefreshCw,
  FileText,
  CheckSquare,
} from "lucide-react";

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
/*  AI Lock Banner                                                     */
/* ------------------------------------------------------------------ */

function AiLock() {
  return (
    <div className="insights-ai-lock">
      <Sparkles size={16} />
      <span>Connect AI to unlock deeper analysis</span>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function InsightsDashboard() {
  const { state } = useApp();
  const notes = state.notes;

  const [aiAvailable, setAiAvailable] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiEntities, setAiEntities] = useState<{ type: string; value: string }[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  // Client-side analysis (memoized)
  const analysis = useMemo(() => analyzeNotes(notes), [notes]);

  // Check AI availability
  const checkAi = useCallback(async () => {
    const health = await api.sidecarHealth();
    setAiAvailable(health !== null && health.status === "ok");
    return health !== null && health.status === "ok";
  }, []);

  // Generate AI insights
  const generateAiInsights = useCallback(async () => {
    setAiLoading(true);
    try {
      const isAvailable = await checkAi();
      if (!isAvailable) {
        setAiLoading(false);
        return;
      }
      // Combine all note content for entity extraction
      const combined = notes
        .slice(0, 20) // cap to avoid overloading
        .map((n) => `# ${n.title}\n${n.content}`)
        .join("\n\n---\n\n");
      const entities = await api.extractEntities(combined);
      setAiEntities(
        entities.map((e) => ({ type: e.entity_type, value: e.entity_value }))
      );
    } catch {
      // Silently fail — client-side still works
    } finally {
      setAiLoading(false);
    }
  }, [notes, checkAi]);

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await checkAi();
    // Analysis auto-refreshes via useMemo when notes change
    setTimeout(() => setRefreshing(false), 400);
  }, [checkAi]);

  // Entity-based build ideas (from AI)
  const entityIdeas: BuildIdea[] = useMemo(() => {
    const typeCounts = new Map<string, string[]>();
    for (const e of aiEntities) {
      const vals = typeCounts.get(e.type) ?? [];
      vals.push(e.value);
      typeCounts.set(e.type, vals);
    }
    const ideas: BuildIdea[] = [];
    for (const [type, values] of typeCounts) {
      if (values.length >= 2) {
        ideas.push({
          title: `Explore ${type} relationships`,
          reason: `Found ${values.length} ${type} entities: ${values.slice(0, 3).join(", ")}${values.length > 3 ? "..." : ""}`,
          type: "entity",
        });
      }
    }
    return ideas.slice(0, 3);
  }, [aiEntities]);

  const allBuildIdeas = [...analysis.buildIdeas, ...entityIdeas];

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

        {/* AI Generate Button */}
        <div className="insights-ai-bar">
          {aiAvailable ? (
            <button
              className="insights-ai-btn"
              onClick={generateAiInsights}
              disabled={aiLoading}
            >
              {aiLoading ? (
                <RefreshCw size={14} className="insights-spin" />
              ) : (
                <Sparkles size={14} />
              )}
              {aiLoading ? "Analyzing..." : "Generate AI Insights"}
            </button>
          ) : (
            <button className="insights-ai-btn insights-ai-btn-check" onClick={checkAi}>
              <Sparkles size={14} />
              Check AI Connection
            </button>
          )}
          {aiEntities.length > 0 && (
            <span className="insights-ai-badge">
              {aiEntities.length} entities extracted
            </span>
          )}
        </div>

        {/* Cards Grid */}
        {notes.length === 0 ? (
          <div className="insights-empty-state">
            <Brain size={48} />
            <h2>No notes yet</h2>
            <p>Create some notes and come back for insights about your knowledge base.</p>
          </div>
        ) : aiLoading ? (
          <div className="insights-grid">
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
            <SkeletonCard />
          </div>
        ) : (
          <div className="insights-grid">
            {/* What to Build Next */}
            <InsightCard
              icon={<Lightbulb size={18} />}
              title="What to Build Next"
              accentColor="#f59e0b"
            >
              {allBuildIdeas.length > 0 ? (
                <ul className="insights-list">
                  {allBuildIdeas.map((idea, i) => (
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
                            // Reload action items
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
              {!aiAvailable && <AiLock />}
            </InsightCard>
          </div>
        )}
      </div>

      <style>{`
        /* Wrapper */
        .insights-wrapper {
          max-width: 900px;
          margin: 0 auto;
          padding: 24px 28px 48px;
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

        /* AI bar */
        .insights-ai-bar {
          display: flex;
          align-items: center;
          gap: 12px;
          margin-bottom: 20px;
        }
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
        .insights-ai-btn-check {
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          color: var(--text-muted, #a1a1aa);
        }
        .insights-ai-badge {
          font-size: 0.78rem;
          color: var(--accent, #3b82f6);
          background: rgba(59, 130, 246, 0.1);
          padding: 4px 10px;
          border-radius: 12px;
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

        /* AI lock banner */
        .insights-ai-lock {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 10px 14px;
          margin-top: 14px;
          background: rgba(139, 92, 246, 0.08);
          border: 1px dashed rgba(139, 92, 246, 0.3);
          border-radius: 8px;
          font-size: 0.78rem;
          color: #8b5cf6;
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

        /* Responsive */
        @media (max-width: 700px) {
          .insights-stats-row {
            grid-template-columns: repeat(2, 1fr);
          }
          .insights-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
