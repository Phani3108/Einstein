import { useMemo, useCallback } from "react";
import { useApp } from "../lib/store";
import { List } from "lucide-react";

interface HeadingItem {
  level: number;
  text: string;
  index: number;
}

export function OutlinePanel() {
  const { state } = useApp();
  const { activeNoteId, notes } = state;
  const activeNote = useMemo(
    () => notes.find((n) => n.id === activeNoteId),
    [notes, activeNoteId]
  );

  const headings = useMemo((): HeadingItem[] => {
    if (!activeNote) return [];
    const items: HeadingItem[] = [];
    const lines = activeNote.content.split("\n");
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim();
      const match = line.match(/^(#{1,6})\s+(.+)/);
      if (match) {
        items.push({
          level: match[1].length,
          text: match[2].replace(/[*_`]/g, ""),
          index: i,
        });
      }
    }
    return items;
  }, [activeNote]);

  const scrollToHeading = useCallback((text: string) => {
    // Find the heading element in the editor
    const editor = document.querySelector(".tiptap");
    if (!editor) return;
    const headingEls = editor.querySelectorAll("h1, h2, h3, h4, h5, h6");
    for (const el of headingEls) {
      if (el.textContent?.trim() === text) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        break;
      }
    }
  }, []);

  if (!activeNote) {
    return (
      <div className="outline-panel">
        <div className="panel-section-title">
          <List size={12} style={{ marginRight: 4 }} />
          Outline
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", padding: "8px 0" }}>
          No note selected
        </p>
      </div>
    );
  }

  if (headings.length === 0) {
    return (
      <div className="outline-panel">
        <div className="panel-section-title">
          <List size={12} style={{ marginRight: 4 }} />
          Outline
        </div>
        <p style={{ fontSize: 12, color: "var(--text-tertiary)", padding: "8px 0" }}>
          No headings found
        </p>
      </div>
    );
  }

  return (
    <div className="outline-panel">
      <div className="panel-section-title">
        <List size={12} style={{ marginRight: 4 }} />
        Outline
        <span className="count">{headings.length}</span>
      </div>
      <div className="outline-list">
        {headings.map((h, i) => (
          <div
            key={i}
            className="outline-item"
            style={{ paddingLeft: (h.level - 1) * 12 + 4 }}
            onClick={() => scrollToHeading(h.text)}
            title={h.text}
          >
            <span className="outline-level">H{h.level}</span>
            <span className="outline-text">{h.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
