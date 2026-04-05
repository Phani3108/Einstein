import React, { useState, useRef, useCallback } from "react";
import { useApp } from "../lib/store";
import { createNoteAndProcess } from "../lib/dataPipeline";
import {
  Mail,
  MessageCircle,
  FileText,
  GitBranch,
  Globe,
  BookOpen,
  Send,
  Download,
  Upload,
  File,
  Database,
  RefreshCw,
  Check,
  X,
  ArrowLeftRight,
  CloudOff,
  Cloud,
  Smartphone,
  Monitor,
  Lock,
  ChevronRight,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type Tab = "import" | "export";

interface PlatformCard {
  id: string;
  name: string;
  icon: React.ReactNode;
  description: string;
  formats: string[];
  connectionType: "oauth" | "file" | "native";
  comingSoon?: boolean;
}

interface ConnectionStatus {
  connected: boolean;
  lastSync?: string;
}

/* ------------------------------------------------------------------ */
/*  Platform definitions                                               */
/* ------------------------------------------------------------------ */

const importPlatforms: PlatformCard[] = [
  {
    id: "whatsapp-import",
    name: "WhatsApp",
    icon: <MessageCircle size={22} />,
    description: "Chat export (.txt) parsed into notes",
    formats: [".txt"],
    connectionType: "file",
  },
  {
    id: "gmail-import",
    name: "Gmail",
    icon: <Mail size={22} />,
    description: "Email threads converted to notes",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "outlook-import",
    name: "Outlook",
    icon: <Monitor size={22} />,
    description: "Email & calendar items to notes",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "gdocs-import",
    name: "Google Docs",
    icon: <FileText size={22} />,
    description: "Documents converted to markdown",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "pdf-import",
    name: "PDF",
    icon: <File size={22} />,
    description: "Extract text, convert to markdown",
    formats: [".pdf"],
    connectionType: "file",
  },
  {
    id: "github-import",
    name: "GitHub",
    icon: <GitBranch size={22} />,
    description: "Repos, issues, READMEs to notes",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "notion-import",
    name: "Notion",
    icon: <BookOpen size={22} />,
    description: "Notion export to markdown import",
    formats: [".zip", ".md"],
    connectionType: "file",
  },
  {
    id: "slack-import",
    name: "Slack",
    icon: <Send size={22} />,
    description: "Channel history converted to notes",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "twitter-import",
    name: "Twitter / X",
    icon: <Globe size={22} />,
    description: "Bookmarks saved as notes",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "bookmarks-import",
    name: "Browser Bookmarks",
    icon: <Database size={22} />,
    description: "Chrome/Firefox export to organized notes",
    formats: [".html", ".json"],
    connectionType: "file",
  },
];

const exportPlatforms: PlatformCard[] = [
  {
    id: "whatsapp-export",
    name: "WhatsApp",
    icon: <MessageCircle size={22} />,
    description: "Share note via link or text",
    formats: ["Link", "Text"],
    connectionType: "native",
  },
  {
    id: "gmail-export",
    name: "Gmail",
    icon: <Mail size={22} />,
    description: "Send note as email draft",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "gdocs-export",
    name: "Google Docs",
    icon: <FileText size={22} />,
    description: "Export as Google Document",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "github-export",
    name: "GitHub",
    icon: <GitBranch size={22} />,
    description: "Create/update repo files & issues",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "pdf-export",
    name: "PDF",
    icon: <File size={22} />,
    description: "Export note or vault as PDF",
    formats: [".pdf"],
    connectionType: "native",
  },
  {
    id: "notion-export",
    name: "Notion",
    icon: <BookOpen size={22} />,
    description: "Push notes as Notion pages",
    formats: ["OAuth"],
    connectionType: "oauth",
    comingSoon: true,
  },
  {
    id: "markdown-export",
    name: "Markdown",
    icon: <Download size={22} />,
    description: "Export raw .md files",
    formats: [".md"],
    connectionType: "native",
  },
  {
    id: "html-export",
    name: "HTML",
    icon: <Globe size={22} />,
    description: "Formatted web page export",
    formats: [".html"],
    connectionType: "native",
  },
];

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DataExchange() {
  const { dispatch } = useApp();
  const [activeTab, setActiveTab] = useState<Tab>("import");
  const [importing, setImporting] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewPlatform, setPreviewPlatform] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<
    Record<string, ConnectionStatus>
  >({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [activePlatformForUpload, setActivePlatformForUpload] = useState<
    string | null
  >(null);

  /* helpers */
  const isConnected = (id: string) => connectionStatus[id]?.connected ?? false;

  const handleConnect = (id: string) => {
    setConnectionStatus((prev) => ({
      ...prev,
      [id]: { connected: true, lastSync: new Date().toLocaleString() },
    }));
  };

  const handleDisconnect = (id: string) => {
    setConnectionStatus((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  };

  const handleFileSelect = useCallback(
    (platformId: string) => {
      setActivePlatformForUpload(platformId);
      fileInputRef.current?.click();
    },
    []
  );

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setUploadedFile(file);
    if (file) {
      const reader = new FileReader();
      reader.onload = () => {
        const text = reader.result as string;
        setPreviewContent(text.slice(0, 2000));
        setPreviewPlatform(activePlatformForUpload);
      };
      reader.readAsText(file);
    }
    if (e.target) e.target.value = "";
  };

  const handleConfirmImport = async () => {
    if (!previewContent || !uploadedFile) {
      setPreviewContent(null);
      setPreviewPlatform(null);
      setUploadedFile(null);
      setActivePlatformForUpload(null);
      return;
    }

    setImporting(true);
    try {
      // Read full file content (preview is truncated to 2000 chars)
      const fullContent = await uploadedFile.text();
      const fileName = uploadedFile.name.replace(/\.[^.]+$/, "");
      const title = `Imported: ${fileName}`;

      // Create note and run through full pipeline
      const result = await createNoteAndProcess(title, fullContent, dispatch, {
        source: `import-${previewPlatform || "file"}`,
      });

      // Navigate to the new note
      dispatch({ type: "SET_ACTIVE_NOTE", id: result.note.id });
      dispatch({ type: "SET_SIDEBAR_VIEW", view: "files" });
    } catch (err) {
      console.error("Import failed:", err);
    } finally {
      setImporting(false);
      setPreviewContent(null);
      setPreviewPlatform(null);
      setUploadedFile(null);
      setActivePlatformForUpload(null);
    }
  };

  const handleCancelPreview = () => {
    setPreviewContent(null);
    setPreviewPlatform(null);
    setUploadedFile(null);
    setActivePlatformForUpload(null);
  };

  const handleExportAction = (id: string) => {
    /* placeholder — in production this triggers the actual export pipeline */
    alert(`Export via ${id} triggered (placeholder).`);
  };

  /* connected services for sync status */
  const connectedServices = Object.entries(connectionStatus).filter(
    ([, v]) => v.connected
  );

  /* ---- render helpers ---- */

  const renderCard = (p: PlatformCard, mode: Tab) => {
    const connected = isConnected(p.id);

    return (
      <div key={p.id} style={styles.card}>
        <div style={styles.cardHeader}>
          <div style={styles.iconWrap}>{p.icon}</div>
          <div style={{ flex: 1 }}>
            <div style={styles.cardTitle}>
              {p.name}
              {p.comingSoon && <span style={styles.comingSoon}>Coming Soon</span>}
            </div>
            <div style={styles.cardDesc}>{p.description}</div>
          </div>
          {connected ? (
            <span style={styles.connectedBadge}>
              <Cloud size={12} /> Connected
            </span>
          ) : (
            <span style={styles.disconnectedBadge}>
              <CloudOff size={12} /> Not connected
            </span>
          )}
        </div>

        <div style={styles.formatRow}>
          {p.formats.map((f) => (
            <span key={f} style={styles.formatChip}>
              {f}
            </span>
          ))}
        </div>

        <div style={styles.cardActions}>
          {p.connectionType === "oauth" && !connected && (
            <button
              style={{
                ...styles.btn,
                ...(p.comingSoon ? styles.btnDisabled : styles.btnPrimary),
              }}
              disabled={!!p.comingSoon}
              onClick={() => handleConnect(p.id)}
            >
              <Lock size={14} />
              {p.comingSoon ? "Coming Soon" : "Connect"}
            </button>
          )}

          {p.connectionType === "oauth" && connected && (
            <>
              <button
                style={{ ...styles.btn, ...styles.btnPrimary }}
                onClick={() =>
                  mode === "import"
                    ? handleConnect(p.id)
                    : handleExportAction(p.id)
                }
              >
                {mode === "import" ? (
                  <>
                    <Upload size={14} /> Import
                  </>
                ) : (
                  <>
                    <Send size={14} /> Export
                  </>
                )}
              </button>
              <button
                style={{ ...styles.btn, ...styles.btnDanger }}
                onClick={() => handleDisconnect(p.id)}
              >
                <X size={14} /> Disconnect
              </button>
            </>
          )}

          {p.connectionType === "file" && mode === "import" && (
            <button
              style={{ ...styles.btn, ...styles.btnPrimary }}
              onClick={() => handleFileSelect(p.id)}
            >
              <Upload size={14} /> Upload File
            </button>
          )}

          {p.connectionType === "native" && mode === "export" && (
            <button
              style={{ ...styles.btn, ...styles.btnPrimary }}
              onClick={() => handleExportAction(p.id)}
            >
              <Download size={14} /> Export
            </button>
          )}
        </div>
      </div>
    );
  };

  /* ---------------------------------------------------------------- */
  /*  JSX                                                              */
  /* ---------------------------------------------------------------- */

  return (
    <div style={styles.root}>
      <style>{`
        .de-tab:hover { background: rgba(99,102,241,0.08) !important; }
        .de-card:hover { border-color: #6366f1 !important; box-shadow: 0 2px 12px rgba(99,102,241,0.10) !important; }
        .de-btn:hover:not(:disabled) { filter: brightness(1.12); }
        .de-upload-zone:hover { border-color: #6366f1 !important; background: rgba(99,102,241,0.04) !important; }
      `}</style>

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />

      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <ArrowLeftRight size={26} color="#6366f1" />
          <div>
            <h2 style={styles.title}>Data Exchange</h2>
            <p style={styles.subtitle}>Seamless 2-way data flow</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={styles.tabs}>
        {(["import", "export"] as Tab[]).map((t) => (
          <button
            key={t}
            className="de-tab"
            style={{
              ...styles.tab,
              ...(activeTab === t ? styles.tabActive : {}),
            }}
            onClick={() => setActiveTab(t)}
          >
            {t === "import" ? <Upload size={16} /> : <Download size={16} />}
            {t === "import" ? "Import" : "Export"}
          </button>
        ))}
      </div>

      {/* Import preview overlay */}
      {previewContent && previewPlatform && (
        <div style={styles.previewOverlay}>
          <div style={styles.previewBox}>
            <div style={styles.previewHeader}>
              <span style={{ fontWeight: 600 }}>
                Import Preview &mdash;{" "}
                {uploadedFile?.name ?? previewPlatform}
              </span>
              <button
                style={styles.previewClose}
                onClick={handleCancelPreview}
              >
                <X size={18} />
              </button>
            </div>
            <pre style={styles.previewContent}>{previewContent}</pre>
            <div style={styles.previewActions}>
              <button
                style={{ ...styles.btn, ...styles.btnPrimary }}
                className="de-btn"
                onClick={handleConfirmImport}
              >
                <Check size={14} /> Confirm Import
              </button>
              <button
                style={{ ...styles.btn, ...styles.btnSecondary }}
                className="de-btn"
                onClick={handleCancelPreview}
              >
                <X size={14} /> Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Platform cards grid */}
      <div style={styles.grid}>
        {(activeTab === "import" ? importPlatforms : exportPlatforms).map(
          (p) => (
            <div className="de-card" key={p.id} style={{ display: "contents" }}>
              {renderCard(p, activeTab)}
            </div>
          )
        )}
      </div>

      {/* File-based upload zone (visible on Import tab) */}
      {activeTab === "import" && (
        <div
          className="de-upload-zone"
          style={styles.uploadZone}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const file = e.dataTransfer.files?.[0];
            if (file) {
              setUploadedFile(file);
              setActivePlatformForUpload("generic-drop");
              const reader = new FileReader();
              reader.onload = () => {
                setPreviewContent((reader.result as string).slice(0, 2000));
                setPreviewPlatform("generic-drop");
              };
              reader.readAsText(file);
            }
          }}
        >
          <Upload size={28} color="#6366f1" />
          <p style={{ margin: "8px 0 0", color: "#94a3b8", fontSize: 14 }}>
            Drag &amp; drop any file here, or click a platform&rsquo;s{" "}
            <strong>Upload File</strong> button above
          </p>
        </div>
      )}

      {/* Sync Status */}
      {connectedServices.length > 0 && (
        <div style={styles.syncSection}>
          <div style={styles.syncHeader}>
            <RefreshCw size={16} color="#6366f1" />
            <span style={{ fontWeight: 600 }}>Sync Status</span>
          </div>
          <div style={styles.syncList}>
            {connectedServices.map(([id, status]) => {
              const platform = [...importPlatforms, ...exportPlatforms].find(
                (p) => p.id === id
              );
              return (
                <div key={id} style={styles.syncRow}>
                  <span style={styles.syncDot} />
                  <span style={{ fontWeight: 500 }}>
                    {platform?.name ?? id}
                  </span>
                  <ChevronRight size={14} color="#94a3b8" />
                  <span style={{ color: "#64748b", fontSize: 13 }}>
                    Last sync: {status.lastSync ?? "never"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Styles                                                             */
/* ------------------------------------------------------------------ */

const styles: Record<string, React.CSSProperties> = {
  root: {
    padding: 24,
    maxWidth: 960,
    margin: "0 auto",
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    color: "#e2e8f0",
  },

  /* header */
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 20,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: 12,
  },
  title: {
    margin: 0,
    fontSize: 22,
    fontWeight: 700,
    color: "#f1f5f9",
  },
  subtitle: {
    margin: 0,
    fontSize: 13,
    color: "#94a3b8",
  },

  /* tabs */
  tabs: {
    display: "flex",
    gap: 4,
    marginBottom: 20,
    borderBottom: "1px solid #334155",
    paddingBottom: 0,
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    padding: "10px 20px",
    border: "none",
    borderBottom: "2px solid transparent",
    background: "transparent",
    color: "#94a3b8",
    fontSize: 14,
    fontWeight: 500,
    cursor: "pointer",
    transition: "all .15s",
    borderRadius: "6px 6px 0 0",
  },
  tabActive: {
    color: "#6366f1",
    borderBottomColor: "#6366f1",
    background: "rgba(99,102,241,0.06)",
  },

  /* grid */
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
    gap: 16,
  },

  /* card */
  card: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 10,
    padding: 16,
    display: "flex",
    flexDirection: "column" as const,
    gap: 12,
    transition: "border-color .15s, box-shadow .15s",
  },
  cardHeader: {
    display: "flex",
    alignItems: "flex-start",
    gap: 10,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 8,
    background: "rgba(99,102,241,0.12)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#818cf8",
    flexShrink: 0,
  },
  cardTitle: {
    fontWeight: 600,
    fontSize: 15,
    display: "flex",
    alignItems: "center",
    gap: 8,
    color: "#f1f5f9",
  },
  cardDesc: {
    fontSize: 12,
    color: "#94a3b8",
    marginTop: 2,
  },
  comingSoon: {
    fontSize: 10,
    fontWeight: 600,
    background: "rgba(234,179,8,0.15)",
    color: "#eab308",
    padding: "2px 6px",
    borderRadius: 4,
    textTransform: "uppercase" as const,
    letterSpacing: 0.5,
  },

  /* badges */
  connectedBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    fontSize: 11,
    fontWeight: 500,
    color: "#22c55e",
    background: "rgba(34,197,94,0.10)",
    padding: "3px 8px",
    borderRadius: 20,
    whiteSpace: "nowrap" as const,
  },
  disconnectedBadge: {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    fontSize: 11,
    fontWeight: 500,
    color: "#64748b",
    background: "rgba(100,116,139,0.10)",
    padding: "3px 8px",
    borderRadius: 20,
    whiteSpace: "nowrap" as const,
  },

  /* format chips */
  formatRow: {
    display: "flex",
    gap: 6,
    flexWrap: "wrap" as const,
  },
  formatChip: {
    fontSize: 11,
    background: "rgba(99,102,241,0.08)",
    color: "#818cf8",
    padding: "2px 8px",
    borderRadius: 4,
    fontFamily: "monospace",
  },

  /* buttons */
  cardActions: {
    display: "flex",
    gap: 8,
    marginTop: "auto",
  },
  btn: {
    display: "inline-flex",
    alignItems: "center",
    gap: 5,
    padding: "7px 14px",
    borderRadius: 6,
    border: "none",
    fontSize: 13,
    fontWeight: 500,
    cursor: "pointer",
    transition: "filter .15s",
  },
  btnPrimary: {
    background: "#6366f1",
    color: "#fff",
  },
  btnSecondary: {
    background: "#334155",
    color: "#e2e8f0",
  },
  btnDanger: {
    background: "rgba(239,68,68,0.12)",
    color: "#ef4444",
  },
  btnDisabled: {
    background: "#334155",
    color: "#64748b",
    cursor: "not-allowed",
  },

  /* upload zone */
  uploadZone: {
    marginTop: 20,
    border: "2px dashed #334155",
    borderRadius: 10,
    padding: "28px 20px",
    display: "flex",
    flexDirection: "column" as const,
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center" as const,
    transition: "border-color .15s, background .15s",
    cursor: "default",
  },

  /* preview */
  previewOverlay: {
    position: "fixed" as const,
    inset: 0,
    background: "rgba(0,0,0,0.6)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  previewBox: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 12,
    width: "90%",
    maxWidth: 640,
    maxHeight: "80vh",
    display: "flex",
    flexDirection: "column" as const,
    overflow: "hidden",
  },
  previewHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 18px",
    borderBottom: "1px solid #334155",
    color: "#f1f5f9",
    fontSize: 15,
  },
  previewClose: {
    background: "transparent",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    padding: 4,
    display: "flex",
  },
  previewContent: {
    flex: 1,
    overflow: "auto",
    padding: 18,
    margin: 0,
    fontSize: 13,
    lineHeight: 1.6,
    color: "#cbd5e1",
    fontFamily: "monospace",
    whiteSpace: "pre-wrap" as const,
    wordBreak: "break-word" as const,
  },
  previewActions: {
    display: "flex",
    gap: 10,
    padding: "14px 18px",
    borderTop: "1px solid #334155",
    justifyContent: "flex-end",
  },

  /* sync status */
  syncSection: {
    marginTop: 28,
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 10,
    padding: 16,
  },
  syncHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
    color: "#f1f5f9",
    fontSize: 14,
  },
  syncList: {
    display: "flex",
    flexDirection: "column" as const,
    gap: 8,
  },
  syncRow: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    fontSize: 13,
    color: "#e2e8f0",
  },
  syncDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    background: "#22c55e",
    flexShrink: 0,
  },
};

export default DataExchange;
