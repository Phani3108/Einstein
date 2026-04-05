import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useApp } from "../lib/store";

interface PreviewData {
  title: string;
  content: string;
  wordCount: number;
  x: number;
  y: number;
}

export function WikilinkPreview() {
  const { state } = useApp();
  const { notes } = state;
  const [preview, setPreview] = useState<PreviewData | null>(null);
  const hoverTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const previewRef = useRef<HTMLDivElement>(null);

  const noteMap = useMemo(() => {
    const map = new Map<string, typeof notes[0]>();
    for (const note of notes) {
      map.set(note.title.toLowerCase(), note);
      const stem = note.file_path.replace(".md", "").split("/").pop()?.toLowerCase();
      if (stem) map.set(stem, note);
    }
    return map;
  }, [notes]);

  const handleMouseOver = useCallback(
    (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (!target.classList.contains("wikilink") && !target.closest(".wikilink")) return;

      const linkEl = target.classList.contains("wikilink") ? target : target.closest(".wikilink") as HTMLElement;
      if (!linkEl) return;

      const linkText = linkEl.getAttribute("data-link") || linkEl.textContent || "";
      const note = noteMap.get(linkText.toLowerCase());
      if (!note) return;

      if (hoverTimer.current) clearTimeout(hoverTimer.current);
      hoverTimer.current = setTimeout(() => {
        const rect = linkEl.getBoundingClientRect();
        setPreview({
          title: note.title,
          content: note.content.slice(0, 300),
          wordCount: note.content.split(/\s+/).filter(Boolean).length,
          x: rect.left,
          y: rect.bottom + 8,
        });
      }, 350);
    },
    [noteMap]
  );

  const handleMouseOut = useCallback((e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (!target.classList.contains("wikilink") && !target.closest(".wikilink")) return;
    if (hoverTimer.current) clearTimeout(hoverTimer.current);
    // Delay hiding so user can move to preview
    setTimeout(() => {
      if (!previewRef.current?.matches(":hover")) {
        setPreview(null);
      }
    }, 200);
  }, []);

  useEffect(() => {
    document.addEventListener("mouseover", handleMouseOver);
    document.addEventListener("mouseout", handleMouseOut);
    return () => {
      document.removeEventListener("mouseover", handleMouseOver);
      document.removeEventListener("mouseout", handleMouseOut);
      if (hoverTimer.current) clearTimeout(hoverTimer.current);
    };
  }, [handleMouseOver, handleMouseOut]);

  if (!preview) return null;

  // Clamp position to viewport
  const maxX = window.innerWidth - 340;
  const maxY = window.innerHeight - 250;
  const x = Math.min(preview.x, maxX);
  const y = Math.min(preview.y, maxY);

  return (
    <div
      ref={previewRef}
      className="wikilink-preview"
      style={{ left: x, top: y }}
      onMouseLeave={() => setPreview(null)}
    >
      <div className="preview-title">{preview.title}</div>
      <div className="preview-content">{preview.content}</div>
      <div className="preview-meta">{preview.wordCount} words</div>
    </div>
  );
}
