import { useEffect, useRef, useState, useCallback } from "react";
import { Tldraw, Editor as TldrawEditor } from "tldraw";
import "tldraw/tldraw.css";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { Save, Plus, Brain, RefreshCw } from "lucide-react";

interface CanvasFile {
  name: string;
  filePath: string;
}

export function CanvasView() {
  const { state, dispatch } = useApp();
  const { notes } = state;
  const editorRef = useRef<TldrawEditor | null>(null);
  const [canvasFiles, setCanvasFiles] = useState<CanvasFile[]>([]);
  const [activeCanvas, setActiveCanvas] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [showNewCanvas, setShowNewCanvas] = useState(false);
  const [newCanvasName, setNewCanvasName] = useState("");

  // Find all canvas files
  useEffect(() => {
    const files = notes
      .filter((n) => n.file_path.endsWith(".canvas.md"))
      .map((n) => ({
        name: n.title,
        filePath: n.file_path,
      }));
    setCanvasFiles(files);
  }, [notes]);

  const handleSave = useCallback(async () => {
    if (!editorRef.current || !activeCanvas) return;
    setSaving(true);
    try {
      const editor = editorRef.current;
      // Serialize all shapes as JSON
      const shapes = editor.getCurrentPageShapes();
      const data = JSON.stringify(shapes, null, 2);
      await api.saveNote(
        activeCanvas,
        activeCanvas.replace(".canvas.md", "").replace("canvas/", ""),
        `<!-- canvas -->\n\`\`\`json\n${data}\n\`\`\``,
        { type: "canvas" }
      );
    } catch (err) {
      console.error("Failed to save canvas:", err);
    } finally {
      setSaving(false);
    }
  }, [activeCanvas]);

  const handleNewCanvas = useCallback(async () => {
    if (!newCanvasName.trim()) return;
    const filePath = `canvas/${newCanvasName.replace(/\s+/g, "-").toLowerCase()}.canvas.md`;
    try {
      const note = await api.saveNote(
        filePath,
        newCanvasName.trim(),
        `<!-- canvas -->\n\`\`\`json\n[]\n\`\`\``,
        { type: "canvas" }
      );
      dispatch({ type: "UPDATE_NOTE", note });
      setActiveCanvas(filePath);
      setShowNewCanvas(false);
      setNewCanvasName("");
    } catch (err) {
      console.error("Failed to create canvas:", err);
    }
  }, [dispatch, newCanvasName]);

  const loadCanvas = useCallback((filePath: string) => {
    setActiveCanvas(filePath);
  }, []);

  // AI auto-layout: create sticky note shapes from notes with entities
  const handleAILayout = useCallback(() => {
    if (!editorRef.current) return;
    const editor = editorRef.current;

    const notesWithContent = notes
      .filter((n) => n.content.trim().length > 20 && !n.file_path.endsWith(".canvas.md"))
      .slice(0, 20);

    if (notesWithContent.length === 0) return;

    const cols = Math.ceil(Math.sqrt(notesWithContent.length));
    const cardW = 260;
    const cardH = 180;
    const gap = 40;

    notesWithContent.forEach((_note, i) => {
      const col = i % cols;
      const row = Math.floor(i / cols);
      editor.createShape({
        type: "note",
        x: col * (cardW + gap) + 100,
        y: row * (cardH + gap) + 100,
        props: {
          color: "yellow" as const,
          size: "m" as const,
        },
      });
    });
  }, [notes]);

  const handleMount = useCallback((editor: TldrawEditor) => {
    editorRef.current = editor;
  }, []);

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <span>Canvas</span>
          {activeCanvas && (
            <span style={{ color: "var(--text-tertiary)", fontSize: 12 }}>
              &nbsp;· {activeCanvas.replace(".canvas.md", "").replace("canvas/", "")}
            </span>
          )}
        </div>
        <div className="editor-actions">
          <button className="icon-btn" onClick={() => setShowNewCanvas(true)} title="New canvas">
            <Plus size={14} />
          </button>
          {activeCanvas && (
            <>
              <button className="icon-btn" onClick={handleAILayout} title="AI auto-layout">
                <Brain size={14} />
              </button>
              <button className="icon-btn" onClick={handleSave} title="Save canvas">
                {saving ? (
                  <RefreshCw size={14} className="loading-spinner" />
                ) : (
                  <Save size={14} />
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Canvas file picker */}
      {!activeCanvas && (
        <div className="canvas-picker">
          <div className="empty-state">
            <p>Select a canvas or create a new one</p>
            <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
              {canvasFiles.map((f) => (
                <button
                  key={f.filePath}
                  className="btn-secondary"
                  onClick={() => loadCanvas(f.filePath)}
                >
                  {f.name}
                </button>
              ))}
              <button className="btn-primary" onClick={() => setShowNewCanvas(true)}>
                <Plus size={14} /> New Canvas
              </button>
            </div>
            {showNewCanvas && (
              <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
                <input
                  type="text"
                  className="onboard-input"
                  placeholder="Canvas name..."
                  value={newCanvasName}
                  onChange={(e) => setNewCanvasName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleNewCanvas()}
                  autoFocus
                  style={{ maxWidth: 240 }}
                />
                <button className="btn-primary" onClick={handleNewCanvas} disabled={!newCanvasName.trim()}>
                  Create
                </button>
                <button className="btn-ghost" onClick={() => { setShowNewCanvas(false); setNewCanvasName(""); }}>
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* tldraw canvas */}
      {activeCanvas && (
        <div className="canvas-container">
          <Tldraw onMount={handleMount} />
        </div>
      )}
    </div>
  );
}
