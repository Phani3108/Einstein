import React, { useEffect, useState, useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { Note } from "../lib/api";
import { OutlinePanel } from "./OutlinePanel";
import { VersionHistory } from "./VersionHistory";
import {
  User,
  MapPin,
  Building,
  Activity,
  Heart,
  CalendarDays,
  Zap,
  LinkIcon,
  Star,
} from "lucide-react";

interface Entity {
  entity_type: string;
  entity_value: string;
  confidence: number;
}

const ENTITY_ICONS: Record<string, React.ReactNode> = {
  person: <User size={11} />,
  location: <MapPin size={11} />,
  organization: <Building size={11} />,
  activity: <Activity size={11} />,
  emotion: <Heart size={11} />,
  event: <Zap size={11} />,
  date: <CalendarDays size={11} />,
};

export function RightPanel() {
  const { state, dispatch } = useApp();
  const { activeNoteId, notes, rightPanelOpen } = state;
  const activeNote = useMemo(
    () => notes.find((n) => n.id === activeNoteId),
    [notes, activeNoteId]
  );
  const [backlinks, setBacklinks] = useState<Note[]>([]);
  const [loadingBacklinks, setLoadingBacklinks] = useState(false);
  const [unlinkedMentions, setUnlinkedMentions] = useState<
    { note: Note; snippet: string }[]
  >([]);

  useEffect(() => {
    if (!activeNoteId) {
      setBacklinks([]);
      return;
    }
    setLoadingBacklinks(true);
    api
      .getBacklinks(activeNoteId)
      .then(setBacklinks)
      .catch(() => setBacklinks([]))
      .finally(() => setLoadingBacklinks(false));
  }, [activeNoteId]);

  // Unlinked mentions: other notes that mention this note's title but don't link to it
  useEffect(() => {
    if (!activeNote) {
      setUnlinkedMentions([]);
      return;
    }
    const title = activeNote.title.toLowerCase();
    if (title.length < 3) {
      setUnlinkedMentions([]);
      return;
    }
    const backlinkIds = new Set(backlinks.map((b) => b.id));
    const mentions: { note: Note; snippet: string }[] = [];
    for (const note of notes) {
      if (note.id === activeNoteId) continue;
      if (backlinkIds.has(note.id)) continue;
      const lower = note.content.toLowerCase();
      const idx = lower.indexOf(title);
      if (idx !== -1) {
        const start = Math.max(0, idx - 30);
        const end = Math.min(note.content.length, idx + title.length + 60);
        mentions.push({
          note,
          snippet: (start > 0 ? "..." : "") + note.content.slice(start, end) + (end < note.content.length ? "..." : ""),
        });
      }
    }
    setUnlinkedMentions(mentions.slice(0, 20));
  }, [activeNote, activeNoteId, notes, backlinks]);

  const outgoingLinks = useMemo(() => {
    if (!activeNote) return [];
    const links: string[] = [];
    const regex = /\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]/g;
    let match;
    while ((match = regex.exec(activeNote.content)) !== null) {
      if (!links.includes(match[1])) links.push(match[1]);
    }
    return links;
  }, [activeNote]);

  const entities = useMemo((): Entity[] => {
    if (!activeNote?.frontmatter?.entities) return [];
    try {
      return JSON.parse(activeNote.frontmatter.entities);
    } catch {
      return [];
    }
  }, [activeNote]);

  const navigateToLink = useCallback(
    (linkText: string) => {
      const lower = linkText.toLowerCase();
      const target = notes.find(
        (n) =>
          n.title.toLowerCase() === lower ||
          n.file_path.replace(".md", "").toLowerCase() === lower ||
          n.file_path.toLowerCase().endsWith(`/${lower}.md`)
      );
      if (target) {
        dispatch({ type: "SET_ACTIVE_NOTE", id: target.id });
      }
    },
    [notes, dispatch]
  );

  if (!rightPanelOpen) return null;

  if (!activeNote) {
    return (
      <div className="right-panel">
        <div className="empty-state">
          <p style={{ fontSize: 12 }}>No note selected</p>
        </div>
      </div>
    );
  }

  const wordCount = activeNote.content.split(/\s+/).filter(Boolean).length;
  const updatedDate = new Date(activeNote.updated_at);

  return (
    <div className="right-panel">
      {/* Outline */}
      <OutlinePanel />

      {/* Properties */}
      <div className="panel-section">
        <div className="panel-section-title" style={{ display: "flex", alignItems: "center" }}>
          <span>Properties</span>
          <button
            className="icon-btn"
            onClick={async () => {
              if (!activeNoteId) return;
              try {
                await api.toggleBookmark(activeNoteId);
              } catch (err) {
                console.error("Bookmark toggle failed:", err);
              }
            }}
            title="Toggle bookmark"
            style={{ marginLeft: "auto", padding: 2 }}
          >
            <Star size={12} color={state.bookmarks.includes(activeNoteId ?? "") ? "var(--accent)" : undefined} fill={state.bookmarks.includes(activeNoteId ?? "") ? "var(--accent)" : "none"} />
          </button>
        </div>
        <div className="meta-field">
          <span className="meta-key">Path</span>
          <span className="meta-value">{activeNote.file_path}</span>
        </div>
        <div className="meta-field">
          <span className="meta-key">Words</span>
          <span className="meta-value">{wordCount}</span>
        </div>
        <div className="meta-field">
          <span className="meta-key">Updated</span>
          <span className="meta-value">
            {updatedDate.toLocaleDateString()} {updatedDate.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        {Object.entries(activeNote.frontmatter)
          .filter(([k]) => k !== "entities")
          .map(([key, value]) => (
            <div key={key} className="meta-field">
              <span className="meta-key">{key}</span>
              <span className="meta-value">{value}</span>
            </div>
          ))}
      </div>

      {/* AI Entities */}
      {entities.length > 0 && (
        <div className="panel-section">
          <div className="panel-section-title">
            AI Entities
            <span className="count">{entities.length}</span>
          </div>
          <div className="entity-tags">
            {entities.map((entity, i) => (
              <span
                key={i}
                className={`entity-tag ${entity.entity_type.toLowerCase()}`}
                title={`${entity.entity_type} · ${Math.round(entity.confidence * 100)}% confidence`}
              >
                {ENTITY_ICONS[entity.entity_type.toLowerCase()]}
                {entity.entity_value}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Outgoing Links */}
      {outgoingLinks.length > 0 && (
        <div className="panel-section">
          <div className="panel-section-title">
            Outgoing Links
            <span className="count">{outgoingLinks.length}</span>
          </div>
          {outgoingLinks.map((link, i) => (
            <div
              key={i}
              className="backlink-item"
              onClick={() => navigateToLink(link)}
            >
              <div className="backlink-title">{link}</div>
            </div>
          ))}
        </div>
      )}

      {/* Backlinks */}
      <div className="panel-section">
        <div className="panel-section-title">
          Backlinks
          <span className="count">
            {loadingBacklinks ? "..." : backlinks.length}
          </span>
        </div>
        {loadingBacklinks && (
          <div style={{ display: "flex", justifyContent: "center", padding: 16 }}>
            <div className="loading-spinner" />
          </div>
        )}
        {!loadingBacklinks && backlinks.length === 0 && (
          <p style={{ fontSize: 12, color: "var(--text-tertiary)" }}>
            No other notes link here
          </p>
        )}
        {!loadingBacklinks &&
          backlinks.map((note) => (
            <div
              key={note.id}
              className="backlink-item"
              onClick={() => dispatch({ type: "SET_ACTIVE_NOTE", id: note.id })}
            >
              <div className="backlink-title">{note.title}</div>
              <div className="backlink-context">
                {note.content.slice(0, 100)}
              </div>
            </div>
          ))}
      </div>
      {/* Unlinked Mentions */}
      {unlinkedMentions.length > 0 && (
        <div className="panel-section">
          <div className="panel-section-title">
            <LinkIcon size={11} style={{ marginRight: 4 }} />
            Unlinked Mentions
            <span className="count">{unlinkedMentions.length}</span>
          </div>
          {unlinkedMentions.map(({ note, snippet }) => (
            <div
              key={note.id}
              className="backlink-item"
              onClick={() =>
                dispatch({ type: "SET_ACTIVE_NOTE", id: note.id })
              }
            >
              <div className="backlink-title">{note.title}</div>
              <div className="backlink-context">{snippet}</div>
            </div>
          ))}
        </div>
      )}

      {/* Version History */}
      <VersionHistory />
    </div>
  );
}
