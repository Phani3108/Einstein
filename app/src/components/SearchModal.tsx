import React, { useState, useEffect, useRef, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import type { Note } from "../lib/api";
import { Search, FileText, Hash } from "lucide-react";

export function SearchModal() {
  const { state, dispatch } = useApp();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Note[]>([]);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when modal opens
  useEffect(() => {
    if (state.searchOpen) {
      inputRef.current?.focus();
      setQuery("");
      setResults(state.notes.slice(0, 12));
      setSelectedIdx(0);
    }
  }, [state.searchOpen, state.notes]);

  // Debounced search
  const doSearch = useCallback(
    async (q: string) => {
      if (!q.trim()) {
        setResults(state.notes.slice(0, 12));
        return;
      }
      try {
        const found = await api.searchNotes(q);
        setResults(found);
      } catch {
        // Client-side fallback
        const lower = q.toLowerCase();
        setResults(
          state.notes
            .filter(
              (n) =>
                n.title.toLowerCase().includes(lower) ||
                n.content.toLowerCase().includes(lower)
            )
            .slice(0, 20)
        );
      }
    },
    [state.notes]
  );

  useEffect(() => {
    const timer = setTimeout(() => doSearch(query), 150);
    return () => clearTimeout(timer);
  }, [query, doSearch]);

  const selectResult = useCallback(
    (note: Note) => {
      dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });
      dispatch({ type: "CLOSE_SEARCH" });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    },
    [dispatch]
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "Escape":
          dispatch({ type: "CLOSE_SEARCH" });
          break;
        case "ArrowDown":
          e.preventDefault();
          setSelectedIdx((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
          break;
        case "ArrowUp":
          e.preventDefault();
          setSelectedIdx((i) => Math.max(i - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (results[selectedIdx]) selectResult(results[selectedIdx]);
          break;
      }
    },
    [dispatch, results, selectedIdx, selectResult]
  );

  if (!state.searchOpen) return null;

  return (
    <div
      className="search-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) dispatch({ type: "CLOSE_SEARCH" });
      }}
    >
      <div className="search-modal" onKeyDown={handleKeyDown}>
        <div className="search-input-row">
          <Search size={16} className="search-icon" />
          <input
            ref={inputRef}
            className="search-input"
            placeholder="Search notes..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIdx(0);
            }}
            onKeyDown={handleKeyDown}
          />
          <span className="search-hint">{results.length} results</span>
        </div>

        <div className="search-results">
          {results.map((note, idx) => (
            <SearchResult
              key={note.id}
              note={note}
              query={query}
              selected={idx === selectedIdx}
              onClick={() => selectResult(note)}
              onHover={() => setSelectedIdx(idx)}
            />
          ))}
          {results.length === 0 && query && (
            <div className="empty-state" style={{ padding: 32, height: "auto" }}>
              <p>No results for &ldquo;{query}&rdquo;</p>
              <p className="hint">Try different keywords</p>
            </div>
          )}
        </div>

        <div className="search-footer">
          <span>
            <kbd>↑↓</kbd> navigate &nbsp; <kbd>↵</kbd> open &nbsp;{" "}
            <kbd>esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}

const SearchResult = React.memo(function SearchResult({
  note,
  query,
  selected,
  onClick,
  onHover,
}: {
  note: Note;
  query: string;
  selected: boolean;
  onClick: () => void;
  onHover: () => void;
}) {
  const hasFolder = note.file_path.includes("/");

  return (
    <div
      className={`search-result ${selected ? "selected" : ""}`}
      onClick={onClick}
      onMouseEnter={onHover}
    >
      <div className="result-icon">
        {hasFolder ? <Hash size={16} /> : <FileText size={16} />}
      </div>
      <div className="result-info">
        <div className="result-title">{note.title}</div>
        <div className="result-path">{note.file_path}</div>
        {query && (
          <div
            className="result-snippet"
            dangerouslySetInnerHTML={{
              __html: highlightSnippet(note.content, query),
            }}
          />
        )}
      </div>
    </div>
  );
});

function highlightSnippet(content: string, query: string): string {
  if (!query) return escapeHtml(content.slice(0, 120));
  const lower = content.toLowerCase();
  const idx = lower.indexOf(query.toLowerCase());
  if (idx === -1) return escapeHtml(content.slice(0, 120));

  const start = Math.max(0, idx - 40);
  const end = Math.min(content.length, idx + query.length + 80);
  let snippet = content.slice(start, end);

  // Highlight the match
  const matchStart = idx - start;
  const before = escapeHtml(snippet.slice(0, matchStart));
  const match = escapeHtml(snippet.slice(matchStart, matchStart + query.length));
  const after = escapeHtml(snippet.slice(matchStart + query.length));

  return (
    (start > 0 ? "..." : "") +
    before +
    `<mark>${match}</mark>` +
    after +
    (end < content.length ? "..." : "")
  );
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
