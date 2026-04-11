import { useState, useEffect, useCallback } from "react";
import { useApp } from "../lib/store";
import { api } from "../lib/api";
import { useTranslation, LANGUAGES, setLanguage as setGlobalLanguage } from "../lib/i18n";
import type { Language } from "../lib/i18n";
import {
  Settings,
  Shield,
  Cloud,
  HardDrive,
  AlertTriangle,
  CheckCircle,
  ArrowRight,
  Info,
  Brain,
  Globe,
  Palette,
  FileText,
  Keyboard,
  Check,
  X,
  GitBranch,
  Link,
  FolderOpen,
  RefreshCw,
  Cpu,
} from "lucide-react";
import { getCloudSwitchingInfo } from "../lib/features";
import type { ConnectionMode } from "../lib/features";

type CloudService = "google-drive" | "onedrive" | "dropbox" | "github";

interface CloudConnection {
  id: CloudService;
  name: string;
  icon: React.ReactNode;
  status: "not-connected" | "connected";
}

export function SettingsPanel() {
  const { state, dispatch } = useApp();
  const { t } = useTranslation();
  const [aiStatus, setAiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [showSwitchConfirm, setShowSwitchConfirm] = useState(false);
  const [comingSoonMessage, setComingSoonMessage] = useState<string | null>(null);
  const [templateCount, setTemplateCount] = useState(0);
  const [currentLang, setCurrentLang] = useState<Language>("en");
  const [currentTheme, setCurrentTheme] = useState<"dark" | "light" | "warm">("dark");
  const [llmProvider, setLlmProvider] = useState<string>("");
  const [llmModel, setLlmModel] = useState<string>("");
  const [ollamaModels, setOllamaModels] = useState<any[]>([]);
  const [llmTestResult, setLlmTestResult] = useState<string>("");

  const targetMode: ConnectionMode = state.connectionMode === "local" ? "cloud" : "local";
  const switchInfo = getCloudSwitchingInfo(state.connectionMode);

  const [cloudConnections] = useState<CloudConnection[]>([
    { id: "google-drive", name: "Google Drive", icon: <Cloud size={18} />, status: "not-connected" },
    { id: "onedrive", name: "OneDrive", icon: <Cloud size={18} />, status: "not-connected" },
    { id: "dropbox", name: "Dropbox", icon: <Cloud size={18} />, status: "not-connected" },
    { id: "github", name: "GitHub", icon: <GitBranch size={18} />, status: "not-connected" },
  ]);

  useEffect(() => {
    api.sidecarHealth().then((h) => {
      setAiStatus(h?.status === "ok" ? "online" : "offline");
    });
    api.listTemplates().then((templates) => {
      setTemplateCount(templates.length);
    }).catch(() => setTemplateCount(0));
    api.getConfig("language").then((lang) => {
      if (lang) setCurrentLang(lang as Language);
    }).catch(() => {});
    api.getConfig("theme").then((th) => {
      if (th) setCurrentTheme(th as "dark" | "light" | "warm");
    }).catch(() => {});
  }, []);

  useEffect(() => {
    api.getSetupConfig().then(cfg => {
      setLlmProvider(cfg.llm_provider || "");
      setLlmModel(cfg.llm_model || "");
      if (cfg.llm_provider === "ollama") {
        api.getOllamaModels().then(res => {
          if (res.status === "ok") setOllamaModels(res.models || []);
        }).catch(() => {});
      }
    }).catch(() => {});
  }, []);

  const handleModeSwitch = useCallback(async () => {
    try {
      await api.setConfig("connection_mode", targetMode);
      dispatch({ type: "SET_CONNECTION_MODE", mode: targetMode });
      setShowSwitchConfirm(false);
    } catch (err) {
      console.error("Failed to switch mode:", err);
    }
  }, [targetMode, dispatch]);

  const handleConnectService = useCallback((service: CloudConnection) => {
    setComingSoonMessage(`${service.name} integration is coming soon. OAuth setup is not yet implemented.`);
    setTimeout(() => setComingSoonMessage(null), 4000);
  }, []);

  const handleLanguageChange = useCallback(async (lang: Language) => {
    setCurrentLang(lang);
    setGlobalLanguage(lang);
    try {
      await api.setConfig("language", lang);
    } catch {}
  }, []);

  const handleThemeChange = useCallback(async (theme: "dark" | "light" | "warm") => {
    setCurrentTheme(theme);
    try {
      await api.setConfig("theme", theme);
    } catch {}
  }, []);

  const shortcuts = [
    { keys: "\u2318 + N", action: "New Note" },
    { keys: "\u2318 + P", action: "Quick Search" },
    { keys: "\u2318 + S", action: "Save Note" },
    { keys: "\u2318 + \\", action: "Toggle Sidebar" },
    { keys: "\u2318 + ]", action: "Toggle Right Panel" },
    { keys: "\u2318 + Shift + D", action: "Daily Note" },
    { keys: "\u2318 + B", action: "Toggle Bookmark" },
    { keys: "\u2318 + G", action: "Knowledge Graph" },
    { keys: "\u2318 + K", action: "Kanban Board" },
    { keys: "\u2318 + E", action: "Export" },
    { keys: "\u2318 + ,", action: "Settings" },
    { keys: "Esc", action: "Close Search / Dialogs" },
  ];

  return (
    <div className="main-content">
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <Settings size={14} style={{ marginRight: 6 }} />
          <span>Settings</span>
        </div>
      </div>

      {/* Coming Soon Toast */}
      {comingSoonMessage && (
        <div
          style={{
            position: "fixed",
            top: 20,
            right: 20,
            background: "var(--bg-tertiary, #2a2a3e)",
            color: "var(--text-primary, #e0e0e0)",
            padding: "12px 20px",
            borderRadius: 8,
            border: "1px solid var(--border-color, #3a3a4e)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            gap: 8,
            boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
          }}
        >
          <Info size={16} />
          {comingSoonMessage}
          <button
            onClick={() => setComingSoonMessage(null)}
            style={{ background: "none", border: "none", color: "inherit", cursor: "pointer", padding: 2 }}
          >
            <X size={14} />
          </button>
        </div>
      )}

      <div className="settings-wrapper">
        {/* ── Connection Mode ── */}
        <div className="settings-section">
          <h3>
            <Shield size={16} /> Connection Mode
          </h3>
          <p className="settings-desc">
            Control how Einstein handles your data. Your choice, your data.
          </p>

          <div className="mode-cards">
            <div
              className={`mode-card ${state.connectionMode === "local" ? "active" : ""}`}
              onClick={() => {
                if (state.connectionMode !== "local") setShowSwitchConfirm(true);
              }}
            >
              <HardDrive size={24} />
              <div className="mode-card-title">Local Only</div>
              <div className="mode-card-desc">
                Everything stays on this device. No cloud, no sync, complete privacy.
              </div>
              {state.connectionMode === "local" && (
                <div className="mode-badge active">
                  <CheckCircle size={12} /> Active
                </div>
              )}
            </div>

            <div
              className={`mode-card ${state.connectionMode === "cloud" ? "active" : ""}`}
              onClick={() => {
                if (state.connectionMode !== "cloud") setShowSwitchConfirm(true);
              }}
            >
              <Cloud size={24} />
              <div className="mode-card-title">Cloud Connected</div>
              <div className="mode-card-desc">
                Sync across devices, real-time collaboration, cloud backup.
              </div>
              {state.connectionMode === "cloud" && (
                <div className="mode-badge active">
                  <CheckCircle size={12} /> Active
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Switch Confirmation */}
        {showSwitchConfirm && (
          <div className="settings-section switch-confirm">
            <h3>
              <AlertTriangle size={16} /> Switch to {targetMode === "local" ? "Local Only" : "Cloud Connected"}?
            </h3>

            <div className="switch-steps">
              <h4>What will happen:</h4>
              <ul>
                {switchInfo.steps.map((step, i) => (
                  <li key={i}>
                    <ArrowRight size={12} /> {step}
                  </li>
                ))}
              </ul>
            </div>

            {switchInfo.warnings.length > 0 && (
              <div className="switch-warnings">
                <h4>
                  <AlertTriangle size={12} /> Important:
                </h4>
                <ul>
                  {switchInfo.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="switch-features">
              <div className="switch-col">
                <h4>
                  <CheckCircle size={12} /> Will work:
                </h4>
                <ul>
                  {switchInfo.whatWorks.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
              <div className="switch-col">
                <h4>
                  <Info size={12} /> Won't work:
                </h4>
                <ul>
                  {switchInfo.whatDoesnt.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="switch-actions">
              <button className="btn-primary" onClick={handleModeSwitch}>
                Switch to {targetMode === "local" ? "Local Only" : "Cloud Connected"}
              </button>
              <button
                className="btn-secondary"
                onClick={() => setShowSwitchConfirm(false)}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* ── Cloud Setup (only when cloud mode is active) ── */}
        {state.connectionMode === "cloud" && (
          <div className="settings-section">
            <h3>
              <Link size={16} /> Cloud Services
            </h3>
            <p className="settings-desc">
              Connect cloud storage and sync services to your vault.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {cloudConnections.map((svc) => (
                <div
                  key={svc.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 16px",
                    background: "var(--bg-secondary, #1e1e2e)",
                    borderRadius: 8,
                    border: "1px solid var(--border-color, #2a2a3e)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    {svc.icon}
                    <div>
                      <div style={{ fontWeight: 500 }}>{svc.name}</div>
                      <div style={{ fontSize: 12, opacity: 0.6 }}>
                        {svc.id === "github" ? "Backup & version sync" : "Cloud storage sync"}
                      </div>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span
                      style={{
                        fontSize: 11,
                        padding: "3px 8px",
                        borderRadius: 12,
                        background: svc.status === "connected"
                          ? "rgba(76, 175, 80, 0.15)"
                          : "rgba(255, 255, 255, 0.05)",
                        color: svc.status === "connected"
                          ? "#66bb6a"
                          : "var(--text-secondary, #888)",
                      }}
                    >
                      {svc.status === "connected" ? "Connected" : "Not Connected"}
                    </span>
                    <button
                      className="btn-secondary"
                      style={{ fontSize: 12, padding: "5px 12px" }}
                      onClick={() => handleConnectService(svc)}
                    >
                      {svc.status === "connected" ? "Disconnect" : "Connect"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Language ── */}
        <div className="settings-section">
          <h3>
            <Globe size={16} /> Language
          </h3>
          <p className="settings-desc">
            Choose the display language for Einstein.
          </p>
          <div className="language-grid" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 8 }}>
            {LANGUAGES.map((lang) => (
              <button
                key={lang.code}
                className={`language-option ${currentLang === lang.code ? "selected" : ""}`}
                onClick={() => handleLanguageChange(lang.code)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "8px 12px",
                  borderRadius: 8,
                  border: currentLang === lang.code
                    ? "1px solid var(--accent-color, #7c5bf0)"
                    : "1px solid var(--border-color, #2a2a3e)",
                  background: currentLang === lang.code
                    ? "rgba(124, 91, 240, 0.1)"
                    : "var(--bg-secondary, #1e1e2e)",
                  color: "var(--text-primary, #e0e0e0)",
                  cursor: "pointer",
                  fontSize: 13,
                }}
              >
                <span>{lang.flag}</span>
                <span>{lang.nativeName}</span>
                {currentLang === lang.code && <Check size={12} style={{ marginLeft: "auto" }} />}
              </button>
            ))}
          </div>
        </div>

        {/* ── Theme ── */}
        <div className="settings-section">
          <h3>
            <Palette size={16} /> Theme
          </h3>
          <p className="settings-desc">
            Customize the appearance of Einstein.
          </p>
          <div className="pref-options" style={{ display: "flex", gap: 10 }}>
            {([
              { key: "dark" as const, label: "Dark", preview: "#1a1a2e" },
              { key: "light" as const, label: "Light", preview: "#f5f5f5" },
              { key: "warm" as const, label: "Warm", preview: "#2a2520" },
            ]).map((opt) => (
              <button
                key={opt.key}
                className={`pref-card ${currentTheme === opt.key ? "selected" : ""}`}
                onClick={() => handleThemeChange(opt.key)}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 6,
                  padding: "12px 20px",
                  borderRadius: 8,
                  border: currentTheme === opt.key
                    ? "1px solid var(--accent-color, #7c5bf0)"
                    : "1px solid var(--border-color, #2a2a3e)",
                  background: currentTheme === opt.key
                    ? "rgba(124, 91, 240, 0.1)"
                    : "var(--bg-secondary, #1e1e2e)",
                  color: "var(--text-primary, #e0e0e0)",
                  cursor: "pointer",
                  minWidth: 80,
                }}
              >
                <div
                  className="theme-preview"
                  style={{
                    background: opt.preview,
                    width: 40,
                    height: 40,
                    borderRadius: 8,
                    border: "1px solid var(--border-color, #3a3a4e)",
                  }}
                />
                <span style={{ fontSize: 13 }}>{opt.label}</span>
                {currentTheme === opt.key && <Check size={12} />}
              </button>
            ))}
          </div>
        </div>

        {/* ── Templates ── */}
        <div className="settings-section">
          <h3>
            <FileText size={16} /> Templates
          </h3>
          <p className="settings-desc">
            Use templates to quickly create notes with predefined structure.
          </p>

          <div
            style={{
              background: "var(--bg-secondary, #1e1e2e)",
              borderRadius: 8,
              padding: 16,
              border: "1px solid var(--border-color, #2a2a3e)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
              <FolderOpen size={14} />
              <span style={{ fontWeight: 500 }}>
                {templateCount} template{templateCount !== 1 ? "s" : ""} found
              </span>
            </div>

            <div style={{ fontSize: 13, opacity: 0.8, lineHeight: 1.6 }}>
              <p style={{ margin: "0 0 8px 0" }}>
                <strong>How to create templates:</strong>
              </p>
              <ol style={{ margin: 0, paddingLeft: 20, display: "flex", flexDirection: "column", gap: 4 }}>
                <li>Create a <code style={{ background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 3 }}>templates/</code> folder in your vault</li>
                <li>Add <code style={{ background: "rgba(255,255,255,0.08)", padding: "1px 5px", borderRadius: 3 }}>.md</code> files as templates</li>
                <li>Use variables in your templates for dynamic content</li>
              </ol>

              <p style={{ margin: "12px 0 6px 0" }}>
                <strong>Available variables:</strong>
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {[
                  { var: "{{date:YYYY-MM-DD}}", desc: "Current date" },
                  { var: "{{time:HH:mm}}", desc: "Current time" },
                  { var: "{{title}}", desc: "Note title" },
                ].map((v) => (
                  <span
                    key={v.var}
                    style={{
                      background: "rgba(124, 91, 240, 0.1)",
                      border: "1px solid rgba(124, 91, 240, 0.2)",
                      borderRadius: 6,
                      padding: "4px 10px",
                      fontSize: 12,
                    }}
                    title={v.desc}
                  >
                    <code>{v.var}</code>
                    <span style={{ opacity: 0.6, marginLeft: 6 }}>{v.desc}</span>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── Keyboard Shortcuts ── */}
        <div className="settings-section">
          <h3>
            <Keyboard size={16} /> Keyboard Shortcuts
          </h3>
          <p className="settings-desc">
            All available keyboard shortcuts for quick navigation.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
              gap: 6,
            }}
          >
            {shortcuts.map((sc) => (
              <div
                key={sc.keys}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "8px 12px",
                  background: "var(--bg-secondary, #1e1e2e)",
                  borderRadius: 6,
                  border: "1px solid var(--border-color, #2a2a3e)",
                  fontSize: 13,
                }}
              >
                <span style={{ opacity: 0.8 }}>{sc.action}</span>
                <kbd
                  style={{
                    background: "rgba(255,255,255,0.08)",
                    padding: "2px 8px",
                    borderRadius: 4,
                    fontSize: 11,
                    fontFamily: "monospace",
                    border: "1px solid rgba(255,255,255,0.1)",
                  }}
                >
                  {sc.keys}
                </kbd>
              </div>
            ))}
          </div>
        </div>

        {/* ── AI Sidecar Status ── */}
        <div className="settings-section">
          <h3>
            <Brain size={16} /> AI Sidecar
          </h3>
          <div className="ai-status-card">
            <div className={`ai-status-indicator ${aiStatus}`}>
              {aiStatus === "checking" ? (
                <div className="loading-spinner" />
              ) : aiStatus === "online" ? (
                <CheckCircle size={16} />
              ) : (
                <AlertTriangle size={16} />
              )}
              <span>
                {aiStatus === "checking"
                  ? "Checking..."
                  : aiStatus === "online"
                  ? "Connected"
                  : "Not Running"}
              </span>
            </div>
            {aiStatus === "offline" && (
              <div className="ai-help">
                <p>The AI sidecar enables entity extraction and semantic search.</p>
                <p>
                  To start it, run: <code>cd sidecar && python server.py</code>
                </p>
                <p>
                  Your notes stay local -- the AI processes everything on your machine.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── LLM Provider ── */}
        <div className="settings-section">
          <h3>
            <Cpu size={16} /> LLM Provider
          </h3>
          <div
            style={{
              background: "var(--bg-secondary, #1e1e2e)",
              borderRadius: 8,
              padding: 16,
              border: "1px solid var(--border-color, #2a2a3e)",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div>
                <div style={{ fontWeight: 500, fontSize: 14 }}>
                  Provider: <span style={{ color: "var(--accent-color, #7c5bf0)" }}>{llmProvider || "Not configured"}</span>
                </div>
                <div style={{ fontSize: 13, opacity: 0.7, marginTop: 2 }}>
                  Model: <span style={{ color: "#60a5fa" }}>{llmModel || "Not set"}</span>
                </div>
              </div>
            </div>
            {llmProvider === "ollama" && ollamaModels.length > 0 && (
              <div>
                <div style={{ fontSize: 12, opacity: 0.6, marginBottom: 4 }}>Installed Ollama models:</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {ollamaModels.map((m: any) => (
                    <span
                      key={m.name}
                      style={{
                        fontSize: 11,
                        padding: "2px 8px",
                        borderRadius: 10,
                        background: "rgba(34, 197, 94, 0.12)",
                        color: "#22c55e",
                      }}
                    >
                      {m.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
            <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
              <button
                className="btn-secondary"
                style={{ fontSize: 12, padding: "5px 12px", display: "flex", alignItems: "center", gap: 4 }}
                onClick={async () => {
                  setLlmTestResult("Testing...");
                  try {
                    const res = await api.testLLM();
                    setLlmTestResult(res.status === "ok" ? `Connected: ${res.response?.slice(0, 80)}` : `Error: ${res.message}`);
                  } catch (e: any) {
                    setLlmTestResult(`Failed: ${e.message}`);
                  }
                }}
              >
                <Brain size={12} /> Test LLM
              </button>
              <button
                className="btn-secondary"
                style={{ fontSize: 12, padding: "5px 12px", display: "flex", alignItems: "center", gap: 4 }}
                onClick={() => {
                  api.getSetupConfig().then(cfg => {
                    setLlmProvider(cfg.llm_provider || "");
                    setLlmModel(cfg.llm_model || "");
                    if (cfg.llm_provider === "ollama") {
                      api.getOllamaModels().then(res => {
                        if (res.status === "ok") setOllamaModels(res.models || []);
                      }).catch(() => {});
                    }
                  }).catch(() => {});
                }}
              >
                <RefreshCw size={12} /> Refresh
              </button>
            </div>
            {llmTestResult && (
              <div
                style={{
                  fontSize: 12,
                  color: "#94a3b8",
                  padding: "6px 10px",
                  background: "#0f172a",
                  borderRadius: 4,
                  wordBreak: "break-word",
                }}
              >
                {llmTestResult}
              </div>
            )}
          </div>
        </div>

        {/* ── Data & Privacy ── */}
        <div className="settings-section">
          <h3>
            <Shield size={16} /> Data & Privacy
          </h3>
          <div className="settings-info-grid">
            <div className="info-item">
              <span className="info-label">Storage</span>
              <span className="info-value">Plain markdown files on disk</span>
            </div>
            <div className="info-item">
              <span className="info-label">Database</span>
              <span className="info-value">.einstein/index.sqlite (local index)</span>
            </div>
            <div className="info-item">
              <span className="info-label">Vault Path</span>
              <span className="info-value">{state.vaultPath || "Not set"}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Total Notes</span>
              <span className="info-value">{state.notes.length}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Connection</span>
              <span className="info-value">
                {state.connectionMode === "local" ? "Local only -- no data leaves this device" : "Cloud connected"}
              </span>
            </div>
          </div>
        </div>

        {/* ── About ── */}
        <div className="settings-section">
          <h3>
            <Info size={16} /> About
          </h3>
          <div
            style={{
              background: "var(--bg-secondary, #1e1e2e)",
              borderRadius: 8,
              padding: 16,
              border: "1px solid var(--border-color, #2a2a3e)",
              display: "flex",
              flexDirection: "column",
              gap: 8,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <Brain size={20} />
              <div>
                <div style={{ fontWeight: 600, fontSize: 15 }}>Einstein</div>
                <div style={{ fontSize: 12, opacity: 0.6 }}>v0.1.0</div>
              </div>
            </div>
            <p style={{ fontSize: 13, opacity: 0.7, margin: 0, lineHeight: 1.5 }}>
              AI-powered second brain. Local-first markdown notes with automatic entity extraction, semantic search, and knowledge graphs. Built with Tauri, React, and Rust.
            </p>
            <div style={{ fontSize: 12, opacity: 0.5, marginTop: 4 }}>
              Made with care. Your data stays yours.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
