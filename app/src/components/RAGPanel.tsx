import { useState, useRef, useEffect, useCallback } from "react";
import { useApp } from "../lib/store";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  Brain, Send, RefreshCw, ChevronDown, ChevronRight,
  FileText, Loader, Zap, MessageSquare, Save,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Source {
  note_id: string;
  title: string;
  snippet: string;
  score: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: number;
}

interface RAGStatus {
  indexed: number;
  chunks: number;
  ready: boolean;
  provider: string;
  model: string;
  last_indexed: string | null;
}

const SIDECAR = "http://127.0.0.1:9721";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

let _idCounter = 0;
function uid(): string {
  return `msg_${Date.now()}_${++_idCounter}`;
}

/** Very small markdown-to-HTML converter (bold, italic, headings, lists, code). */
function miniMarkdown(md: string): string {
  let html = md
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // headings
  html = html.replace(/^#### (.+)$/gm, "<h4>$1</h4>");
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // inline code
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");

  // unordered lists (consecutive lines starting with - )
  html = html.replace(/(?:^- .+$\n?)+/gm, (block) => {
    const items = block.trim().split("\n").map((l) => `<li>${l.replace(/^- /, "")}</li>`).join("");
    return `<ul>${items}</ul>`;
  });

  // ordered lists
  html = html.replace(/(?:^\d+\. .+$\n?)+/gm, (block) => {
    const items = block.trim().split("\n").map((l) => `<li>${l.replace(/^\d+\. /, "")}</li>`).join("");
    return `<ol>${items}</ol>`;
  });

  // paragraphs (double newline)
  html = html.replace(/\n{2,}/g, "</p><p>");
  html = `<p>${html}</p>`;
  html = html.replace(/<p>\s*<(h[1-4]|ul|ol)/g, "<$1");
  html = html.replace(/<\/(h[1-4]|ul|ol)>\s*<\/p>/g, "</$1>");

  // single newlines -> <br>
  html = html.replace(/\n/g, "<br/>");

  return html;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function RAGPanel() {
  const { state, dispatch } = useApp();
  const { notes } = state;

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [generating, setGenerating] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [status, setStatus] = useState<RAGStatus | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  /* ---- auto-scroll ---- */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ---- fetch status on mount ---- */
  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${SIDECAR}/rag/status`);
      if (!res.ok) throw new Error(`Status ${res.status}`);
      const data: RAGStatus = await res.json();
      setStatus(data);
      setStatusError(null);
    } catch (err: any) {
      setStatusError(err.message ?? "Cannot reach sidecar");
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  /* ---- index notes ---- */
  const handleIndex = useCallback(async () => {
    if (indexing) return;
    setIndexing(true);
    try {
      const payload = notes.map((n) => ({ id: n.id, title: n.title, content: n.content }));
      const res = await fetch(`${SIDECAR}/rag/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: payload }),
      });
      if (!res.ok) throw new Error(`Index failed (${res.status})`);
      await fetchStatus();
    } catch (err: any) {
      console.error("Indexing error:", err);
      setStatusError(err.message);
    } finally {
      setIndexing(false);
    }
  }, [notes, indexing, fetchStatus]);

  /* ---- send question ---- */
  const handleSend = useCallback(async () => {
    const question = input.trim();
    if (!question || generating) return;

    const userMsg: Message = { id: uid(), role: "user", content: question, timestamp: Date.now() };
    const assistantMsg: Message = { id: uid(), role: "assistant", content: "", timestamp: Date.now() };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setInput("");
    setGenerating(true);

    const conversationHistory = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .map((m) => ({ role: m.role, content: m.content }));

    try {
      abortRef.current = new AbortController();
      const res = await fetch(`${SIDECAR}/rag/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, conversation_history: conversationHistory, top_k: 5 }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) throw new Error(`Ask failed (${res.status})`);

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";
      let sources: Source[] | undefined;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.type === "chunk") {
              accumulated += event.content;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsg.id ? { ...m, content: accumulated } : m))
              );
            } else if (event.type === "sources") {
              sources = event.sources;
              setMessages((prev) =>
                prev.map((m) => (m.id === assistantMsg.id ? { ...m, sources } : m))
              );
            } else if (event.type === "done") {
              // stream finished
            }
          } catch {
            // ignore parse errors for partial lines
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantMsg.id
              ? { ...m, content: `**Error:** ${err.message ?? "Failed to get response."}` }
              : m
          )
        );
      }
    } finally {
      setGenerating(false);
      abortRef.current = null;
    }
  }, [input, generating, messages]);

  /* ---- toggle source panel ---- */
  const toggleSources = useCallback((msgId: string) => {
    setExpandedSources((prev) => ({ ...prev, [msgId]: !prev[msgId] }));
  }, []);

  /* ---- navigate to note ---- */
  const navigateToNote = useCallback(
    (noteId: string) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: noteId });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    },
    [dispatch]
  );

  /* ---- save answer as note ---- */
  const saveAsNote = useCallback(
    async (msg: Message) => {
      const sourcesSection = msg.sources?.length
        ? "\n\n## Sources\n" +
          msg.sources.map((s) => `- [[${s.title}]] (${Math.round(s.score * 100)}%)`).join("\n")
        : "";
      const content = `# RAG Answer\n\n${msg.content}${sourcesSection}`;

      try {
        const result = await createNoteAndProcess(
          `RAG Answer — ${new Date().toISOString().slice(0, 16).replace("T", " ")}`,
          content,
          dispatch,
          { source: "rag-answer" },
        );
        dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
        dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
      } catch (err) {
        console.error("Failed to save RAG answer:", err);
      }
    },
    [dispatch],
  );

  /* ---- key handler ---- */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  /* ---- render ---- */
  return (
    <div className="main-content">
      <style>{`
        .rag-wrapper {
          display: flex;
          flex-direction: column;
          height: 100%;
          max-width: 820px;
          margin: 0 auto;
          padding: 0;
        }

        /* Header */
        .rag-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 18px 24px 14px;
          border-bottom: 1px solid var(--color-border, #e2e2e2);
          flex-shrink: 0;
        }
        .rag-header-title {
          font-size: 16px;
          font-weight: 600;
          color: var(--color-text, #1a1a1a);
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .rag-header-right {
          margin-left: auto;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        /* Status badges */
        .rag-badge {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 11px;
          font-weight: 500;
          padding: 3px 9px;
          border-radius: 10px;
          background: var(--color-bg-secondary, #f4f4f5);
          color: var(--color-text-secondary, #71717a);
        }
        .rag-badge--provider {
          background: #ede9fe;
          color: #7c3aed;
        }
        .rag-badge--ready {
          background: #dcfce7;
          color: #16a34a;
        }
        .rag-badge--error {
          background: #fee2e2;
          color: #dc2626;
        }

        /* Index button */
        .rag-index-btn {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          font-size: 12px;
          font-weight: 500;
          padding: 5px 12px;
          border-radius: 6px;
          border: 1px solid var(--color-border, #e2e2e2);
          background: var(--color-bg, #fff);
          color: var(--color-text, #1a1a1a);
          cursor: pointer;
          transition: background 0.15s;
        }
        .rag-index-btn:hover { background: var(--color-bg-secondary, #f4f4f5); }
        .rag-index-btn:disabled { opacity: 0.5; cursor: not-allowed; }
        .rag-index-btn svg.spin { animation: rag-spin 1s linear infinite; }
        @keyframes rag-spin { to { transform: rotate(360deg); } }

        /* Messages area */
        .rag-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px 24px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }

        /* Empty state */
        .rag-empty {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 12px;
          color: var(--color-text-secondary, #71717a);
          text-align: center;
          padding: 48px 24px;
        }
        .rag-empty svg { opacity: 0.35; }
        .rag-empty p { font-size: 14px; max-width: 360px; line-height: 1.6; }

        /* Bubbles */
        .rag-bubble {
          max-width: 85%;
          padding: 10px 14px;
          border-radius: 12px;
          font-size: 14px;
          line-height: 1.6;
          word-wrap: break-word;
        }
        .rag-bubble--user {
          align-self: flex-end;
          background: var(--color-primary, #2563eb);
          color: #fff;
          border-bottom-right-radius: 4px;
        }
        .rag-bubble--assistant {
          align-self: flex-start;
          background: var(--color-bg-secondary, #f4f4f5);
          color: var(--color-text, #1a1a1a);
          border-bottom-left-radius: 4px;
        }

        /* Markdown inside assistant bubble */
        .rag-bubble--assistant h1, .rag-bubble--assistant h2,
        .rag-bubble--assistant h3, .rag-bubble--assistant h4 {
          margin: 8px 0 4px;
          font-weight: 600;
        }
        .rag-bubble--assistant h1 { font-size: 18px; }
        .rag-bubble--assistant h2 { font-size: 16px; }
        .rag-bubble--assistant h3 { font-size: 15px; }
        .rag-bubble--assistant h4 { font-size: 14px; }
        .rag-bubble--assistant ul, .rag-bubble--assistant ol {
          margin: 6px 0;
          padding-left: 20px;
        }
        .rag-bubble--assistant li { margin: 2px 0; }
        .rag-bubble--assistant code {
          background: rgba(0,0,0,0.06);
          padding: 1px 5px;
          border-radius: 3px;
          font-size: 13px;
          font-family: "SF Mono", "Fira Code", monospace;
        }
        .rag-bubble--assistant p { margin: 4px 0; }

        /* Sources */
        .rag-sources-toggle {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          margin-top: 8px;
          font-size: 12px;
          font-weight: 500;
          color: var(--color-text-secondary, #71717a);
          cursor: pointer;
          background: none;
          border: none;
          padding: 2px 0;
        }
        .rag-sources-toggle:hover { color: var(--color-text, #1a1a1a); }
        .rag-sources-list {
          margin-top: 6px;
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .rag-source-card {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 8px 10px;
          border-radius: 8px;
          background: var(--color-bg, #fff);
          border: 1px solid var(--color-border, #e2e2e2);
          cursor: pointer;
          transition: border-color 0.15s;
        }
        .rag-source-card:hover { border-color: var(--color-primary, #2563eb); }
        .rag-source-title {
          font-size: 12px;
          font-weight: 600;
          color: var(--color-text, #1a1a1a);
        }
        .rag-source-snippet {
          font-size: 11px;
          color: var(--color-text-secondary, #71717a);
          margin-top: 2px;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .rag-source-score {
          font-size: 10px;
          font-weight: 600;
          color: var(--color-primary, #2563eb);
          white-space: nowrap;
          margin-top: 1px;
        }

        /* Thinking indicator */
        .rag-thinking {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: var(--color-text-secondary, #71717a);
          padding: 6px 0;
        }
        .rag-thinking svg { animation: rag-spin 1s linear infinite; }

        /* Input area */
        .rag-input-area {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 14px 24px 18px;
          border-top: 1px solid var(--color-border, #e2e2e2);
          flex-shrink: 0;
        }
        .rag-input {
          flex: 1;
          padding: 10px 14px;
          font-size: 14px;
          border-radius: 10px;
          border: 1px solid var(--color-border, #e2e2e2);
          background: var(--color-bg, #fff);
          color: var(--color-text, #1a1a1a);
          outline: none;
          transition: border-color 0.15s;
        }
        .rag-input:focus { border-color: var(--color-primary, #2563eb); }
        .rag-input::placeholder { color: var(--color-text-secondary, #a1a1aa); }
        .rag-send-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 38px;
          height: 38px;
          border-radius: 10px;
          border: none;
          background: var(--color-primary, #2563eb);
          color: #fff;
          cursor: pointer;
          transition: opacity 0.15s;
          flex-shrink: 0;
        }
        .rag-send-btn:hover { opacity: 0.85; }
        .rag-send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
      `}</style>

      <div className="rag-wrapper">
        {/* ---- Header ---- */}
        <div className="rag-header">
          <div className="rag-header-title">
            <Brain size={18} />
            Ask Your Notes
          </div>
          <div className="rag-header-right">
            {status && (
              <>
                <span className="rag-badge rag-badge--ready">
                  <FileText size={11} />
                  {status.indexed} notes &middot; {status.chunks} chunks
                </span>
                <span className="rag-badge rag-badge--provider">
                  <Zap size={11} />
                  {status.provider}/{status.model}
                </span>
              </>
            )}
            {statusError && (
              <span className="rag-badge rag-badge--error">Sidecar offline</span>
            )}
            <button
              className="rag-index-btn"
              onClick={handleIndex}
              disabled={indexing || notes.length === 0}
              title="Re-index all notes for RAG search"
            >
              <RefreshCw size={13} className={indexing ? "spin" : ""} />
              {indexing ? "Indexing..." : "Index Notes"}
            </button>
          </div>
        </div>

        {/* ---- Messages ---- */}
        {messages.length === 0 ? (
          <div className="rag-empty">
            <MessageSquare size={40} />
            <p>
              Ask any question about your notes. Einstein will search through your
              vault and synthesize an answer.
            </p>
            {status && !status.ready && (
              <p style={{ fontSize: 12, color: "#dc2626" }}>
                Index your notes first to enable search.
              </p>
            )}
          </div>
        ) : (
          <div className="rag-messages">
            {messages.map((msg) => (
              <div key={msg.id}>
                <div
                  className={`rag-bubble rag-bubble--${msg.role}`}
                >
                  {msg.role === "assistant" ? (
                    <div dangerouslySetInnerHTML={{ __html: miniMarkdown(msg.content) }} />
                  ) : (
                    msg.content
                  )}
                </div>

                {/* Save as Note + Sources */}
                {msg.role === "assistant" && msg.content && (
                  <button
                    className="rag-sources-toggle"
                    onClick={() => saveAsNote(msg)}
                    style={{ marginTop: 6, color: "#10b981" }}
                  >
                    <Save size={12} />
                    Save as Note
                  </button>
                )}
                {msg.role === "assistant" && msg.sources && msg.sources.length > 0 && (
                  <div style={{ maxWidth: "85%" }}>
                    <button
                      className="rag-sources-toggle"
                      onClick={() => toggleSources(msg.id)}
                    >
                      {expandedSources[msg.id] ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                      {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
                    </button>

                    {expandedSources[msg.id] && (
                      <div className="rag-sources-list">
                        {msg.sources.map((src, i) => (
                          <div
                            key={`${msg.id}-src-${i}`}
                            className="rag-source-card"
                            onClick={() => navigateToNote(src.note_id)}
                          >
                            <FileText size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                            <div style={{ flex: 1, minWidth: 0 }}>
                              <div className="rag-source-title">{src.title}</div>
                              <div className="rag-source-snippet">{src.snippet}</div>
                            </div>
                            <div className="rag-source-score">
                              {Math.round(src.score * 100)}%
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Thinking indicator while streaming */}
            {generating && messages.length > 0 && messages[messages.length - 1].content === "" && (
              <div className="rag-thinking">
                <Loader size={14} />
                Thinking...
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}

        {/* ---- Input ---- */}
        <div className="rag-input-area">
          <input
            ref={inputRef}
            className="rag-input"
            type="text"
            placeholder="Ask a question about your notes..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={generating}
          />
          <button
            className="rag-send-btn"
            onClick={handleSend}
            disabled={generating || !input.trim()}
            title="Send"
          >
            {generating ? <Loader size={16} /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
