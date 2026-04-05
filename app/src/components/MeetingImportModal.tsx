import { useState, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { processNoteThroughPipeline } from "../lib/dataPipeline";
import { X, Upload, Mic, FileText, Loader, Check, Video, Phone, Monitor, MessageCircle } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type SourceType = "zoom" | "teams" | "meet" | "whatsapp" | "phone" | "other";
type ImportTab = "paste" | "audio" | "file";

interface ProcessedMeeting {
  title: string;
  participants: string[];
  summary: string;
  keyPoints: string[];
  actionItems: string[];
  decisions: string[];
  transcript: string;
}

export interface MeetingImportModalProps {
  open: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const SOURCE_OPTIONS: { value: SourceType; label: string; icon: React.ReactNode }[] = [
  { value: "zoom",     label: "Zoom",     icon: <Video size={14} /> },
  { value: "teams",    label: "Teams",    icon: <Monitor size={14} /> },
  { value: "meet",     label: "Meet",     icon: <Video size={14} /> },
  { value: "whatsapp", label: "WhatsApp", icon: <MessageCircle size={14} /> },
  { value: "phone",    label: "Phone",    icon: <Phone size={14} /> },
  { value: "other",    label: "Other",    icon: <FileText size={14} /> },
];

const TABS: { key: ImportTab; label: string; icon: React.ReactNode }[] = [
  { key: "paste", label: "Paste Transcript", icon: <FileText size={14} /> },
  { key: "audio", label: "Upload Audio",     icon: <Mic size={14} /> },
  { key: "file",  label: "Upload File",      icon: <Upload size={14} /> },
];

function todayISO(): string {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function MeetingImportModal({ open, onClose }: MeetingImportModalProps) {
  const { dispatch } = useApp();

  /* form state */
  const [tab, setTab] = useState<ImportTab>("paste");
  const [source, setSource] = useState<SourceType>("zoom");
  const [transcript, setTranscript] = useState("");
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(todayISO());
  const [participants, setParticipants] = useState("");

  /* audio / file upload state */
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);

  /* processing state */
  const [processing, setProcessing] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [processed, setProcessed] = useState<ProcessedMeeting | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ---- Actions ---- */

  const resetForm = useCallback(() => {
    setTab("paste");
    setSource("zoom");
    setTranscript("");
    setTitle("");
    setDate(todayISO());
    setParticipants("");
    setAudioFile(null);
    setUploadFile(null);
    setProcessed(null);
    setSaved(false);
    setError(null);
  }, []);

  const handleClose = useCallback(() => {
    resetForm();
    onClose();
  }, [onClose, resetForm]);

  const handleTranscribe = useCallback(async () => {
    if (!audioFile) return;
    setTranscribing(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", audioFile);
      formData.append("source", source);
      const res = await fetch("http://127.0.0.1:9721/meetings/transcribe", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Transcription failed: ${res.statusText}`);
      const data = await res.json();
      setTranscript(data.transcript ?? "");
      setTab("paste");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transcription failed");
    } finally {
      setTranscribing(false);
    }
  }, [audioFile, source]);

  const handleFileUpload = useCallback(async () => {
    if (!uploadFile) return;
    setProcessing(true);
    setError(null);
    try {
      const text = await uploadFile.text();
      setTranscript(text);
      setTab("paste");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to read file");
    } finally {
      setProcessing(false);
    }
  }, [uploadFile]);

  const handleProcess = useCallback(async () => {
    if (!transcript.trim()) return;
    setProcessing(true);
    setError(null);
    setProcessed(null);
    try {
      const res = await fetch("http://127.0.0.1:9721/meetings/process", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: transcript.trim(),
          source,
          title: title.trim() || undefined,
          date: date || undefined,
          participants: participants
            .split(",")
            .map((p) => p.trim())
            .filter(Boolean),
        }),
      });
      if (!res.ok) throw new Error(`Processing failed: ${res.statusText}`);
      const data: ProcessedMeeting = await res.json();
      setProcessed(data);
      if (data.title && !title.trim()) setTitle(data.title);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Processing failed");
    } finally {
      setProcessing(false);
    }
  }, [transcript, source, title, date, participants]);

  const handleSave = useCallback(async () => {
    if (!processed) return;
    setSaving(true);
    setError(null);
    try {
      const meetTitle = title.trim() || processed.title || "Untitled Meeting";
      const meetDate = date || todayISO();
      const meetParticipants =
        participants.trim() ||
        (processed.participants ?? []).join(",");

      const content = [
        `# ${meetTitle}`,
        "",
        "## Summary",
        processed.summary || "_No summary extracted._",
        "",
        "## Key Points",
        ...(processed.keyPoints?.length
          ? processed.keyPoints.map((p) => `- ${p}`)
          : ["_No key points extracted._"]),
        "",
        "## Action Items",
        ...(processed.actionItems?.length
          ? processed.actionItems.map((a) => `- [ ] ${a}`)
          : ["_No action items extracted._"]),
        "",
        "## Decisions",
        ...(processed.decisions?.length
          ? processed.decisions.map((d) => `- ${d}`)
          : ["_No decisions extracted._"]),
        "",
        "## Full Transcript",
        processed.transcript || transcript,
      ].join("\n");

      const slug = meetTitle
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      const filePath = `meetings/${meetDate}-${slug}.md`;

      const note = await api.saveNote(filePath, meetTitle, content, {
        type: "meeting",
        source,
        date: meetDate,
        participants: meetParticipants,
      });

      dispatch({ type: "UPDATE_NOTE", note });
      dispatch({ type: "SET_ACTIVE_NOTE", id: note.id });

      // Run through unified pipeline: extract entities, action items, calendar events, RAG index
      processNoteThroughPipeline(note, dispatch, {
        alreadySaved: true,
        source: `meeting-${source}`,
      }).catch((err) => console.error("Pipeline failed for meeting note:", err));

      setSaved(true);
      setTimeout(() => handleClose(), 800);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setSaving(false);
    }
  }, [processed, title, date, participants, source, transcript, dispatch, handleClose]);

  /* ---- Drop handlers ---- */

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) setUploadFile(file);
  }, []);

  if (!open) return null;

  /* ---- Render ---- */

  return (
    <>
      <style>{`
        .mim-overlay {
          position: fixed; inset: 0;
          background: rgba(0,0,0,0.55);
          display: flex; align-items: center; justify-content: center;
          z-index: 1000;
          animation: mim-fadein 0.15s ease;
        }
        @keyframes mim-fadein { from { opacity: 0; } to { opacity: 1; } }
        .mim-modal {
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #333);
          border-radius: 12px;
          width: 620px; max-width: 94vw;
          max-height: 88vh;
          display: flex; flex-direction: column;
          box-shadow: 0 20px 60px rgba(0,0,0,0.4);
          animation: mim-slidein 0.2s ease;
        }
        @keyframes mim-slidein { from { transform: translateY(16px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
        .mim-header {
          display: flex; align-items: center; justify-content: space-between;
          padding: 16px 20px; border-bottom: 1px solid var(--border, #333);
        }
        .mim-header h2 {
          margin: 0; font-size: 16px; font-weight: 600;
          display: flex; align-items: center; gap: 8px;
          color: var(--text-primary, #cdd6f4);
        }
        .mim-close {
          background: none; border: none; color: var(--text-secondary, #888);
          cursor: pointer; padding: 4px; border-radius: 6px;
          display: flex; align-items: center;
        }
        .mim-close:hover { background: var(--bg-tertiary, #333); color: var(--text-primary, #cdd6f4); }
        .mim-body {
          padding: 16px 20px; overflow-y: auto; flex: 1;
          display: flex; flex-direction: column; gap: 14px;
        }
        .mim-tabs {
          display: flex; gap: 4px; background: var(--bg-secondary, #181825);
          border-radius: 8px; padding: 3px;
        }
        .mim-tab {
          flex: 1; padding: 7px 10px; border: none; border-radius: 6px;
          background: transparent; color: var(--text-secondary, #888);
          cursor: pointer; font-size: 12px; font-weight: 500;
          display: flex; align-items: center; justify-content: center; gap: 5px;
          transition: all 0.15s;
        }
        .mim-tab.active {
          background: var(--accent, #89b4fa); color: #11111b; font-weight: 600;
        }
        .mim-tab:not(.active):hover { background: var(--bg-tertiary, #333); color: var(--text-primary, #cdd6f4); }
        .mim-row { display: flex; gap: 10px; }
        .mim-field { display: flex; flex-direction: column; gap: 4px; flex: 1; }
        .mim-field label {
          font-size: 11px; font-weight: 600; text-transform: uppercase;
          letter-spacing: 0.04em; color: var(--text-secondary, #888);
        }
        .mim-field input, .mim-field select, .mim-field textarea {
          background: var(--bg-secondary, #181825);
          border: 1px solid var(--border, #333);
          border-radius: 6px; padding: 8px 10px;
          color: var(--text-primary, #cdd6f4);
          font-size: 13px; font-family: inherit;
          outline: none; transition: border-color 0.15s;
        }
        .mim-field input:focus, .mim-field select:focus, .mim-field textarea:focus {
          border-color: var(--accent, #89b4fa);
        }
        .mim-field textarea { resize: vertical; min-height: 140px; line-height: 1.5; }
        .mim-source-select {
          display: flex; gap: 4px; flex-wrap: wrap;
        }
        .mim-source-btn {
          display: flex; align-items: center; gap: 4px;
          padding: 5px 10px; border-radius: 6px; border: 1px solid var(--border, #333);
          background: var(--bg-secondary, #181825); color: var(--text-secondary, #888);
          cursor: pointer; font-size: 12px; transition: all 0.15s;
        }
        .mim-source-btn.active {
          border-color: var(--accent, #89b4fa); color: var(--accent, #89b4fa);
          background: rgba(137,180,250,0.08);
        }
        .mim-source-btn:not(.active):hover { border-color: var(--text-secondary, #888); }
        .mim-dropzone {
          border: 2px dashed var(--border, #333); border-radius: 8px;
          padding: 32px; text-align: center;
          color: var(--text-secondary, #888); font-size: 13px;
          transition: all 0.2s; cursor: pointer;
        }
        .mim-dropzone.dragover {
          border-color: var(--accent, #89b4fa);
          background: rgba(137,180,250,0.05);
        }
        .mim-dropzone p { margin: 8px 0 0; }
        .mim-file-info {
          display: flex; align-items: center; gap: 8px;
          padding: 8px 12px; border-radius: 6px;
          background: var(--bg-secondary, #181825);
          font-size: 12px; color: var(--text-primary, #cdd6f4);
        }
        .mim-actions {
          display: flex; gap: 8px; justify-content: flex-end;
          padding: 14px 20px; border-top: 1px solid var(--border, #333);
        }
        .mim-btn {
          padding: 8px 16px; border: none; border-radius: 6px;
          font-size: 13px; font-weight: 500; cursor: pointer;
          display: flex; align-items: center; gap: 6px; transition: all 0.15s;
        }
        .mim-btn-secondary {
          background: var(--bg-secondary, #181825);
          color: var(--text-primary, #cdd6f4);
          border: 1px solid var(--border, #333);
        }
        .mim-btn-secondary:hover { background: var(--bg-tertiary, #333); }
        .mim-btn-primary {
          background: var(--accent, #89b4fa); color: #11111b; font-weight: 600;
        }
        .mim-btn-primary:hover { filter: brightness(1.1); }
        .mim-btn-primary:disabled {
          opacity: 0.5; cursor: not-allowed; filter: none;
        }
        .mim-btn-success {
          background: #a6e3a1; color: #11111b; font-weight: 600;
        }
        .mim-error {
          padding: 8px 12px; border-radius: 6px;
          background: rgba(243,139,168,0.1); border: 1px solid rgba(243,139,168,0.3);
          color: #f38ba8; font-size: 12px;
        }
        .mim-preview {
          border: 1px solid var(--border, #333); border-radius: 8px;
          background: var(--bg-secondary, #181825); padding: 14px;
          display: flex; flex-direction: column; gap: 10px;
        }
        .mim-preview h4 {
          margin: 0; font-size: 14px; color: var(--text-primary, #cdd6f4);
          display: flex; align-items: center; gap: 6px;
        }
        .mim-preview-section h5 {
          margin: 0 0 4px; font-size: 11px; text-transform: uppercase;
          letter-spacing: 0.04em; color: var(--text-secondary, #888);
        }
        .mim-preview-section ul {
          margin: 0; padding-left: 18px; font-size: 12px;
          color: var(--text-primary, #cdd6f4); line-height: 1.6;
        }
        .mim-preview-section p {
          margin: 0; font-size: 12px;
          color: var(--text-primary, #cdd6f4); line-height: 1.5;
        }
        .mim-participants-preview {
          display: flex; gap: 4px; flex-wrap: wrap;
        }
        .mim-avatar {
          width: 26px; height: 26px; border-radius: 50%;
          background: var(--accent, #89b4fa); color: #11111b;
          display: flex; align-items: center; justify-content: center;
          font-size: 10px; font-weight: 700;
        }
        .mim-spinner {
          width: 16px; height: 16px; border: 2px solid transparent;
          border-top-color: currentColor; border-radius: 50%;
          animation: mim-spin 0.6s linear infinite;
        }
        @keyframes mim-spin { to { transform: rotate(360deg); } }
      `}</style>

      <div className="mim-overlay" onClick={(e) => { if (e.target === e.currentTarget) handleClose(); }}>
        <div className="mim-modal">
          {/* Header */}
          <div className="mim-header">
            <h2><Video size={18} /> Import Meeting</h2>
            <button className="mim-close" onClick={handleClose}><X size={18} /></button>
          </div>

          {/* Body */}
          <div className="mim-body">
            {/* Source selector */}
            <div className="mim-field">
              <label>Source</label>
              <div className="mim-source-select">
                {SOURCE_OPTIONS.map((s) => (
                  <button
                    key={s.value}
                    className={`mim-source-btn ${source === s.value ? "active" : ""}`}
                    onClick={() => setSource(s.value)}
                  >
                    {s.icon} {s.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Tabs */}
            <div className="mim-tabs">
              {TABS.map((t) => (
                <button
                  key={t.key}
                  className={`mim-tab ${tab === t.key ? "active" : ""}`}
                  onClick={() => setTab(t.key)}
                >
                  {t.icon} {t.label}
                </button>
              ))}
            </div>

            {/* ---- Paste Transcript tab ---- */}
            {tab === "paste" && (
              <>
                <div className="mim-row">
                  <div className="mim-field">
                    <label>Title (optional)</label>
                    <input
                      type="text" placeholder="Meeting title..."
                      value={title} onChange={(e) => setTitle(e.target.value)}
                    />
                  </div>
                  <div className="mim-field" style={{ maxWidth: 150 }}>
                    <label>Date</label>
                    <input
                      type="date" value={date}
                      onChange={(e) => setDate(e.target.value)}
                    />
                  </div>
                </div>
                <div className="mim-field">
                  <label>Participants (comma-separated)</label>
                  <input
                    type="text" placeholder="Alice, Bob, Carol..."
                    value={participants}
                    onChange={(e) => setParticipants(e.target.value)}
                  />
                </div>
                <div className="mim-field">
                  <label>Transcript</label>
                  <textarea
                    placeholder="Paste your meeting transcript here..."
                    value={transcript}
                    onChange={(e) => setTranscript(e.target.value)}
                  />
                </div>
              </>
            )}

            {/* ---- Upload Audio tab ---- */}
            {tab === "audio" && (
              <>
                <div className="mim-field">
                  <label>Audio File</label>
                  <input
                    type="file" accept="audio/*"
                    onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                    style={{ fontSize: 13 }}
                  />
                </div>
                {audioFile && (
                  <div className="mim-file-info">
                    <Mic size={14} />
                    <span>{audioFile.name}</span>
                    <span style={{ color: "var(--text-secondary)", marginLeft: "auto", fontSize: 11 }}>
                      {(audioFile.size / (1024 * 1024)).toFixed(1)} MB
                    </span>
                  </div>
                )}
                <button
                  className="mim-btn mim-btn-primary"
                  disabled={!audioFile || transcribing}
                  onClick={handleTranscribe}
                  style={{ alignSelf: "flex-start" }}
                >
                  {transcribing ? (
                    <><div className="mim-spinner" /> Transcribing...</>
                  ) : (
                    <><Mic size={14} /> Transcribe</>
                  )}
                </button>
              </>
            )}

            {/* ---- Upload File tab ---- */}
            {tab === "file" && (
              <>
                <div
                  className={`mim-dropzone ${dragOver ? "dragover" : ""}`}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => {
                    const input = document.createElement("input");
                    input.type = "file";
                    input.accept = ".txt,.vtt,.srt,.md";
                    input.onchange = (e) => {
                      const f = (e.target as HTMLInputElement).files?.[0];
                      if (f) setUploadFile(f);
                    };
                    input.click();
                  }}
                >
                  <Upload size={28} />
                  <p>Drop a file here or click to browse</p>
                  <p style={{ fontSize: 11, opacity: 0.6 }}>
                    Supports .txt, .vtt, .srt, .md (WhatsApp exports, etc.)
                  </p>
                </div>
                {uploadFile && (
                  <>
                    <div className="mim-file-info">
                      <FileText size={14} />
                      <span>{uploadFile.name}</span>
                      <span style={{ color: "var(--text-secondary)", marginLeft: "auto", fontSize: 11 }}>
                        {(uploadFile.size / 1024).toFixed(1)} KB
                      </span>
                    </div>
                    <button
                      className="mim-btn mim-btn-primary"
                      onClick={handleFileUpload}
                      style={{ alignSelf: "flex-start" }}
                    >
                      <Upload size={14} /> Load into Transcript
                    </button>
                  </>
                )}
              </>
            )}

            {/* Error */}
            {error && <div className="mim-error">{error}</div>}

            {/* Preview */}
            {processed && (
              <div className="mim-preview">
                <h4><Check size={16} color="#a6e3a1" /> Processed Meeting</h4>

                {processed.participants?.length > 0 && (
                  <div className="mim-preview-section">
                    <h5>Participants</h5>
                    <div className="mim-participants-preview">
                      {processed.participants.map((p, i) => (
                        <div key={i} className="mim-avatar" title={p}>
                          {p.slice(0, 2).toUpperCase()}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {processed.summary && (
                  <div className="mim-preview-section">
                    <h5>Summary</h5>
                    <p>{processed.summary}</p>
                  </div>
                )}

                {processed.keyPoints?.length > 0 && (
                  <div className="mim-preview-section">
                    <h5>Key Points</h5>
                    <ul>{processed.keyPoints.map((p, i) => <li key={i}>{p}</li>)}</ul>
                  </div>
                )}

                {processed.actionItems?.length > 0 && (
                  <div className="mim-preview-section">
                    <h5>Action Items ({processed.actionItems.length})</h5>
                    <ul>{processed.actionItems.map((a, i) => <li key={i}>{a}</li>)}</ul>
                  </div>
                )}

                {processed.decisions?.length > 0 && (
                  <div className="mim-preview-section">
                    <h5>Decisions</h5>
                    <ul>{processed.decisions.map((d, i) => <li key={i}>{d}</li>)}</ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer actions */}
          <div className="mim-actions">
            <button className="mim-btn mim-btn-secondary" onClick={handleClose}>
              Cancel
            </button>
            {!processed ? (
              <button
                className="mim-btn mim-btn-primary"
                disabled={!transcript.trim() || processing}
                onClick={handleProcess}
              >
                {processing ? (
                  <><Loader size={14} className="mim-spinner" /> Processing...</>
                ) : (
                  <><FileText size={14} /> Process Transcript</>
                )}
              </button>
            ) : (
              <button
                className={`mim-btn ${saved ? "mim-btn-success" : "mim-btn-primary"}`}
                disabled={saving || saved}
                onClick={handleSave}
              >
                {saved ? (
                  <><Check size={14} /> Saved!</>
                ) : saving ? (
                  <><Loader size={14} className="mim-spinner" /> Saving...</>
                ) : (
                  <><FileText size={14} /> Save as Note</>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
