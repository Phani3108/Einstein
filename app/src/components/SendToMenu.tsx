/**
 * SendToMenu.tsx — Universal "Send to..." dropdown
 *
 * Reusable component that appears on any content block across Einstein.
 * Provides consistent actions: Send to Editor, Send to AI Tool,
 * Create Action Item, Create Calendar Event.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  Send,
  FileText,
  Brain,
  CheckSquare,
  Calendar,
  ChevronDown,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface SendToMenuProps {
  /** The text content to send */
  content: string;
  /** Optional title for the content */
  title?: string;
  /** Source label for provenance */
  source?: string;
  /** Compact mode (icon only, no label) */
  compact?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function SendToMenu({ content, title, source, compact }: SendToMenuProps) {
  const { dispatch } = useApp();
  const [open, setOpen] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const showFeedback = useCallback((msg: string) => {
    setFeedback(msg);
    setTimeout(() => setFeedback(null), 2000);
  }, []);

  const handleSendToEditor = useCallback(async () => {
    setOpen(false);
    try {
      const noteTitle = title || `Note — ${new Date().toISOString().slice(0, 16).replace("T", " ")}`;
      const result = await createNoteAndProcess(noteTitle, content, dispatch, {
        source: source || "send-to",
      });
      dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
      showFeedback("Saved as note");
    } catch (err) {
      console.error("Send to editor failed:", err);
    }
  }, [content, title, source, dispatch, showFeedback]);

  const handleSendToAI = useCallback(() => {
    setOpen(false);
    // Store content in sessionStorage for AI Tools Hub to pick up
    sessionStorage.setItem("einstein-ai-context", JSON.stringify({
      content,
      title: title || "",
      source: source || "",
    }));
    dispatch({ type: "SET_SIDEBAR_VIEW", view: "aitools" });
    showFeedback("Sent to AI Tools");
  }, [content, title, source, dispatch, showFeedback]);

  const handleCreateTask = useCallback(async () => {
    setOpen(false);
    try {
      const taskText = title || content.slice(0, 100);
      await api.saveActionItems("manual", [{
        task: taskText,
        assignee: null,
        deadline: null,
        priority: "medium",
      }]);
      // Reload action items into central state
      const items = await api.getActionItems();
      dispatch({
        type: "SET_ACTION_ITEMS",
        items: items.map((item) => ({
          ...item,
          priority: item.priority as "high" | "medium" | "low",
          status: item.status as "pending" | "completed" | "cancelled",
          source_title: source || "Manual",
        })),
      });
      showFeedback("Task created");
    } catch (err) {
      console.error("Create task failed:", err);
    }
  }, [content, title, source, dispatch, showFeedback]);

  const handleCreateEvent = useCallback(async () => {
    setOpen(false);
    try {
      const eventTitle = title || content.slice(0, 80);
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      const dateStr = tomorrow.toISOString().slice(0, 10);

      await api.saveCalendarEvents("manual", [{
        title: eventTitle,
        event_date: dateStr,
        event_type: "reminder",
        description: content.slice(0, 200),
      }]);
      // Reload calendar events into central state
      const events = await api.getCalendarEvents("2020-01-01", "2030-12-31");
      dispatch({
        type: "SET_CALENDAR_EVENTS",
        events: events.map((ev) => ({
          ...ev,
          event_type: ev.event_type as "deadline" | "follow_up" | "meeting" | "reminder",
          source_title: source || "Manual",
        })),
      });
      showFeedback("Event created");
    } catch (err) {
      console.error("Create event failed:", err);
    }
  }, [content, title, source, dispatch, showFeedback]);

  return (
    <div className="stm-container" ref={menuRef}>
      <button
        className="stm-trigger"
        onClick={() => setOpen(!open)}
        title="Send to..."
      >
        <Send size={12} />
        {!compact && <span>Send to</span>}
        <ChevronDown size={10} />
      </button>

      {feedback && <span className="stm-feedback">{feedback}</span>}

      {open && (
        <div className="stm-dropdown">
          <button className="stm-option" onClick={handleSendToEditor}>
            <FileText size={14} />
            <span>Save as Note</span>
          </button>
          <button className="stm-option" onClick={handleSendToAI}>
            <Brain size={14} />
            <span>Send to AI Tools</span>
          </button>
          <div className="stm-divider" />
          <button className="stm-option" onClick={handleCreateTask}>
            <CheckSquare size={14} />
            <span>Create Action Item</span>
          </button>
          <button className="stm-option" onClick={handleCreateEvent}>
            <Calendar size={14} />
            <span>Create Calendar Event</span>
          </button>
        </div>
      )}

      <style>{`
        .stm-container {
          position: relative;
          display: inline-flex;
          align-items: center;
          gap: 6px;
        }
        .stm-trigger {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 10px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: none;
          color: var(--text-muted, #71717a);
          font-size: 11px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.15s;
        }
        .stm-trigger:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }
        .stm-feedback {
          font-size: 11px;
          color: #10b981;
          font-weight: 500;
          animation: stm-fade 2s ease forwards;
        }
        @keyframes stm-fade {
          0% { opacity: 1; }
          70% { opacity: 1; }
          100% { opacity: 0; }
        }
        .stm-dropdown {
          position: absolute;
          top: calc(100% + 4px);
          right: 0;
          z-index: 100;
          min-width: 200px;
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
          padding: 4px;
          animation: stm-slidein 0.12s ease;
        }
        @keyframes stm-slidein {
          from { opacity: 0; transform: translateY(-4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .stm-option {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 8px 12px;
          border: none;
          border-radius: 6px;
          background: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 13px;
          cursor: pointer;
          transition: background 0.1s;
          text-align: left;
        }
        .stm-option:hover {
          background: var(--bg-secondary, #27272a);
        }
        .stm-option svg {
          color: var(--text-muted, #71717a);
          flex-shrink: 0;
        }
        .stm-divider {
          height: 1px;
          background: var(--border, #27272a);
          margin: 4px 8px;
        }
      `}</style>
    </div>
  );
}
