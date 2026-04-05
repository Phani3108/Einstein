import { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { useApp } from "../lib/store";
import {
  Plug, Zap, Key, Globe, Server, Plus, Trash2, RefreshCw,
  CheckCircle, XCircle, Copy, Check, Eye, EyeOff,
  Bell, Link, Settings, Activity
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface McpServer {
  id: string;
  name: string;
  url: string;
  transport: "stdio" | "http";
  status: "unknown" | "online" | "offline";
}

interface ApiKeySlot {
  configKey: string;
  label: string;
  value: string;
  masked: boolean;
  showInput: boolean;
}

interface WebhookEntry {
  configKey: string;
  label: string;
  trigger: string;
  url: string;
  enabled: boolean;
}

type ServiceStatus = "online" | "offline" | "checking";

/* ------------------------------------------------------------------ */
/*  Status Dot                                                         */
/* ------------------------------------------------------------------ */

function StatusDot({ status }: { status: "online" | "offline" | "unknown" | "checking" }) {
  const color =
    status === "online" ? "#22c55e" :
    status === "checking" ? "#f59e0b" :
    "#ef4444";
  return (
    <span
      className="ih-status-dot"
      style={{ background: color }}
      title={status}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Status Card (top dashboard row)                                    */
/* ------------------------------------------------------------------ */

function StatusCard({
  icon,
  label,
  status,
}: {
  icon: React.ReactNode;
  label: string;
  status: ServiceStatus;
}) {
  const statusLabel =
    status === "online" ? "Connected" :
    status === "checking" ? "Checking..." :
    "Disconnected";
  return (
    <div className="ih-status-card">
      <div className="ih-status-card-icon">{icon}</div>
      <div className="ih-status-card-info">
        <span className="ih-status-card-label">{label}</span>
        <span className={`ih-status-card-value ih-status-${status}`}>
          <StatusDot status={status} />
          {statusLabel}
        </span>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Section wrapper (collapsible)                                      */
/* ------------------------------------------------------------------ */

function Section({
  icon,
  title,
  badge,
  defaultOpen = false,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  badge?: React.ReactNode;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="ih-section">
      <button className="ih-section-header" onClick={() => setOpen((o) => !o)}>
        <span className="ih-section-icon">{icon}</span>
        <span className="ih-section-title">{title}</span>
        {badge && <span className="ih-section-badge">{badge}</span>}
        <span className="ih-chevron">{open ? "\u25BE" : "\u25B8"}</span>
      </button>
      {open && <div className="ih-section-body">{children}</div>}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Code snippet with copy                                             */
/* ------------------------------------------------------------------ */

function Snippet({ code, lang }: { code: string; lang?: string }) {
  const [copied, setCopied] = useState(false);
  const doCopy = () => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };
  return (
    <div className="ih-snippet">
      {lang && <span className="ih-snippet-lang">{lang}</span>}
      <button className="ih-snippet-copy" onClick={doCopy} title="Copy">
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <pre><code>{code}</code></pre>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function IntegrationsHub() {
  const { state } = useApp();

  // ---- Connection Status Dashboard ----
  const [sidecarStatus, setSidecarStatus] = useState<ServiceStatus>("checking");
  const [mcpStatus, setMcpStatus] = useState<ServiceStatus>("checking");
  const [a2aStatus, setA2aStatus] = useState<ServiceStatus>("checking");
  const cloudStatus: ServiceStatus =
    state.connectionMode === "cloud" ? "online" : "offline";

  // ---- MCP Servers (external) ----
  const [mcpServers, setMcpServers] = useState<McpServer[]>([]);
  const [newServerName, setNewServerName] = useState("");
  const [newServerUrl, setNewServerUrl] = useState("");
  const [newServerTransport, setNewServerTransport] = useState<"stdio" | "http">("http");

  // ---- API Keys ----
  const [apiKeys, setApiKeys] = useState<ApiKeySlot[]>([
    { configKey: "api_key_openai", label: "OpenAI API Key", value: "", masked: true, showInput: false },
    { configKey: "api_key_anthropic", label: "Anthropic API Key", value: "", masked: true, showInput: false },
    { configKey: "api_key_custom", label: "Custom API Endpoint", value: "", masked: true, showInput: false },
  ]);
  const [keyDraft, setKeyDraft] = useState<Record<string, string>>({});

  // ---- Webhooks ----
  const [webhooks, setWebhooks] = useState<WebhookEntry[]>([
    { configKey: "webhook_on_note_save", label: "On Note Save", trigger: "note.save", url: "", enabled: false },
    { configKey: "webhook_on_daily_create", label: "On Daily Note Create", trigger: "daily.create", url: "", enabled: false },
    { configKey: "webhook_on_entity_extracted", label: "On Entity Extracted", trigger: "entity.extracted", url: "", enabled: false },
  ]);

  // ---- Test result messages ----
  const [testMsg, setTestMsg] = useState<Record<string, string>>({});

  /* ---- Load persisted data on mount ---- */
  const loadPersistedData = useCallback(async () => {
    // MCP servers
    try {
      const raw = await api.getConfig("mcp_servers_external");
      if (raw) {
        const parsed = JSON.parse(raw) as McpServer[];
        setMcpServers(parsed);
      }
    } catch { /* no stored servers */ }

    // API keys (load masked previews)
    const updatedKeys = [...apiKeys];
    for (let i = 0; i < updatedKeys.length; i++) {
      try {
        const val = await api.getConfig(updatedKeys[i].configKey);
        if (val) {
          updatedKeys[i] = { ...updatedKeys[i], value: val };
        }
      } catch { /* ignore */ }
    }
    setApiKeys(updatedKeys);

    // Webhooks
    const updatedHooks = [...webhooks];
    for (let i = 0; i < updatedHooks.length; i++) {
      try {
        const raw = await api.getConfig(updatedHooks[i].configKey);
        if (raw) {
          const parsed = JSON.parse(raw);
          updatedHooks[i] = { ...updatedHooks[i], url: parsed.url || "", enabled: parsed.enabled || false };
        }
      } catch { /* ignore */ }
    }
    setWebhooks(updatedHooks);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => { loadPersistedData(); }, [loadPersistedData]);

  /* ---- Health checks ---- */
  const checkHealth = useCallback(async () => {
    setSidecarStatus("checking");
    setMcpStatus("checking");
    setA2aStatus("checking");

    // Sidecar
    const health = await api.sidecarHealth();
    setSidecarStatus(health?.status === "ok" ? "online" : "offline");

    // MCP (same sidecar, different path)
    try {
      const res = await fetch("http://localhost:9721/health");
      setMcpStatus(res.ok ? "online" : "offline");
    } catch {
      setMcpStatus("offline");
    }

    // A2A
    try {
      const res = await fetch("http://localhost:9721/.well-known/agent.json");
      setA2aStatus(res.ok ? "online" : "offline");
    } catch {
      setA2aStatus("offline");
    }
  }, []);

  useEffect(() => { checkHealth(); }, [checkHealth]);

  /* ---- MCP Server management ---- */
  const persistServers = async (servers: McpServer[]) => {
    await api.setConfig("mcp_servers_external", JSON.stringify(servers));
  };

  const addServer = async () => {
    if (!newServerName.trim() || !newServerUrl.trim()) return;
    const server: McpServer = {
      id: crypto.randomUUID(),
      name: newServerName.trim(),
      url: newServerUrl.trim(),
      transport: newServerTransport,
      status: "unknown",
    };
    const updated = [...mcpServers, server];
    setMcpServers(updated);
    await persistServers(updated);
    setNewServerName("");
    setNewServerUrl("");
  };

  const removeServer = async (id: string) => {
    const updated = mcpServers.filter((s) => s.id !== id);
    setMcpServers(updated);
    await persistServers(updated);
  };

  const testServer = async (id: string) => {
    setMcpServers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, status: "unknown" as const } : s))
    );
    const server = mcpServers.find((s) => s.id === id);
    if (!server) return;
    try {
      const res = await fetch(server.url, { method: "GET", signal: AbortSignal.timeout(5000) });
      setMcpServers((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: res.ok ? "online" : "offline" } : s))
      );
    } catch {
      setMcpServers((prev) =>
        prev.map((s) => (s.id === id ? { ...s, status: "offline" } : s))
      );
    }
    // persist updated status
    setMcpServers((prev) => {
      persistServers(prev);
      return prev;
    });
  };

  /* ---- Test built-in endpoints ---- */
  const testBuiltinMcp = async () => {
    setTestMsg((m) => ({ ...m, mcp: "Testing..." }));
    try {
      const res = await fetch("http://localhost:9721/health");
      setTestMsg((m) => ({ ...m, mcp: res.ok ? "Connection successful" : `Failed (${res.status})` }));
    } catch {
      setTestMsg((m) => ({ ...m, mcp: "Connection failed - sidecar not running" }));
    }
  };

  const testA2aDiscovery = async () => {
    setTestMsg((m) => ({ ...m, a2a: "Testing..." }));
    try {
      const res = await fetch("http://localhost:9721/.well-known/agent.json");
      if (res.ok) {
        const card = await res.json();
        setTestMsg((m) => ({ ...m, a2a: `Discovered: ${card.name || "Einstein Agent"}` }));
      } else {
        setTestMsg((m) => ({ ...m, a2a: `Failed (${res.status})` }));
      }
    } catch {
      setTestMsg((m) => ({ ...m, a2a: "Discovery failed - sidecar not running" }));
    }
  };

  /* ---- API Key management ---- */
  const maskValue = (val: string): string => {
    if (!val || val.length < 4) return "••••••••";
    return "••••••••" + val.slice(-4);
  };

  const saveApiKey = async (configKey: string) => {
    const draft = keyDraft[configKey];
    if (!draft?.trim()) return;
    await api.setConfig(configKey, draft.trim());
    setApiKeys((prev) =>
      prev.map((k) => (k.configKey === configKey ? { ...k, value: draft.trim(), showInput: false } : k))
    );
    setKeyDraft((d) => {
      const next = { ...d };
      delete next[configKey];
      return next;
    });
  };

  const clearApiKey = async (configKey: string) => {
    await api.setConfig(configKey, "");
    setApiKeys((prev) =>
      prev.map((k) => (k.configKey === configKey ? { ...k, value: "", showInput: false } : k))
    );
  };

  /* ---- Webhook management ---- */
  const updateWebhook = async (index: number, partial: Partial<WebhookEntry>) => {
    setWebhooks((prev) => {
      const updated = [...prev];
      updated[index] = { ...updated[index], ...partial };
      const entry = updated[index];
      api.setConfig(entry.configKey, JSON.stringify({ url: entry.url, enabled: entry.enabled }));
      return updated;
    });
  };

  /* ---- MCP config snippet ---- */
  const mcpConfigSnippet = `{
  "mcpServers": {
    "einstein": {
      "url": "http://localhost:9721/mcp",
      "transport": "streamable-http"
    }
  }
}`;

  const a2aSkills = [
    { name: "search_notes", desc: "Full-text and semantic search across vault" },
    { name: "create_note", desc: "Create a new note with title, content, and tags" },
    { name: "get_note", desc: "Retrieve a note by ID or title" },
    { name: "extract_entities", desc: "Run AI entity extraction on note content" },
    { name: "get_graph", desc: "Retrieve the knowledge graph (nodes & edges)" },
  ];

  /* ================================================================ */
  /*  RENDER                                                          */
  /* ================================================================ */

  return (
    <div className="main-content" style={{ overflow: "auto" }}>
      {/* Header */}
      <div className="editor-header">
        <div className="editor-breadcrumb">
          <Plug size={14} style={{ marginRight: 6 }} />
          <span>Integrations Hub</span>
        </div>
        <button className="ih-refresh-all" onClick={checkHealth} title="Refresh all statuses">
          <RefreshCw size={14} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="ih-wrapper">
        {/* -------------------------------------------------------- */}
        {/*  Connection Status Dashboard                              */}
        {/* -------------------------------------------------------- */}
        <div className="ih-dashboard-row">
          <StatusCard icon={<Activity size={18} />} label="AI Sidecar" status={sidecarStatus} />
          <StatusCard icon={<Server size={18} />} label="MCP Server" status={mcpStatus} />
          <StatusCard icon={<Zap size={18} />} label="A2A Protocol" status={a2aStatus} />
          <StatusCard icon={<Globe size={18} />} label="Cloud Sync" status={cloudStatus} />
        </div>

        {/* -------------------------------------------------------- */}
        {/*  1. MCP Server Status                                     */}
        {/* -------------------------------------------------------- */}
        <Section
          icon={<Server size={18} />}
          title="MCP Server Status"
          badge={<StatusDot status={mcpStatus === "online" ? "online" : "offline"} />}
          defaultOpen
        >
          <div className="ih-info-row">
            <span className="ih-label">Status</span>
            <span className={`ih-value ih-status-${mcpStatus}`}>
              {mcpStatus === "online" ? "Running" : mcpStatus === "checking" ? "Checking..." : "Stopped"}
            </span>
          </div>
          <div className="ih-info-row">
            <span className="ih-label">Endpoint</span>
            <code className="ih-mono">http://localhost:9721/mcp</code>
          </div>

          <div className="ih-actions-row">
            <button className="ih-btn ih-btn-primary" onClick={testBuiltinMcp}>
              <RefreshCw size={13} />
              Test Connection
            </button>
            {testMsg.mcp && (
              <span className={`ih-test-result ${testMsg.mcp.includes("successful") ? "ih-success" : "ih-error"}`}>
                {testMsg.mcp.includes("successful") ? <CheckCircle size={13} /> : <XCircle size={13} />}
                {testMsg.mcp}
              </span>
            )}
          </div>

          <h4>Add to your AI tool config</h4>
          <Snippet code={mcpConfigSnippet} lang="json" />
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  2. Connected MCP Servers (External)                      */}
        {/* -------------------------------------------------------- */}
        <Section
          icon={<Link size={18} />}
          title="Connected MCP Servers"
          badge={mcpServers.length > 0 ? String(mcpServers.length) : undefined}
        >
          {/* Add form */}
          <div className="ih-add-form">
            <input
              className="ih-input"
              placeholder="Server name"
              value={newServerName}
              onChange={(e) => setNewServerName(e.target.value)}
            />
            <input
              className="ih-input ih-input-wide"
              placeholder="URL (e.g. http://localhost:3000/mcp)"
              value={newServerUrl}
              onChange={(e) => setNewServerUrl(e.target.value)}
            />
            <select
              className="ih-select"
              value={newServerTransport}
              onChange={(e) => setNewServerTransport(e.target.value as "stdio" | "http")}
            >
              <option value="http">HTTP</option>
              <option value="stdio">stdio</option>
            </select>
            <button className="ih-btn ih-btn-primary" onClick={addServer}>
              <Plus size={13} />
              Add
            </button>
          </div>

          {/* Server list */}
          {mcpServers.length === 0 ? (
            <p className="ih-empty">No external MCP servers connected yet.</p>
          ) : (
            <div className="ih-server-list">
              {mcpServers.map((s) => (
                <div key={s.id} className="ih-server-row">
                  <StatusDot status={s.status} />
                  <div className="ih-server-info">
                    <span className="ih-server-name">{s.name}</span>
                    <span className="ih-server-url">{s.url}</span>
                    <span className="ih-server-transport">{s.transport}</span>
                  </div>
                  <div className="ih-server-actions">
                    <button className="ih-btn ih-btn-small" onClick={() => testServer(s.id)} title="Test">
                      <RefreshCw size={12} />
                      Test
                    </button>
                    <button className="ih-btn ih-btn-small ih-btn-danger" onClick={() => removeServer(s.id)} title="Remove">
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  3. A2A Agent Discovery                                   */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Zap size={18} />} title="A2A Agent Discovery">
          <div className="ih-info-row">
            <span className="ih-label">Agent Card</span>
            <code className="ih-mono">http://localhost:9721/.well-known/agent.json</code>
          </div>
          <div className="ih-info-row">
            <span className="ih-label">Agent Name</span>
            <span className="ih-value">Einstein Knowledge Agent</span>
          </div>

          <h4>Agent Skills</h4>
          <div className="ih-skills-list">
            {a2aSkills.map((skill) => (
              <div key={skill.name} className="ih-skill-row">
                <code className="ih-skill-name">{skill.name}</code>
                <span className="ih-skill-desc">{skill.desc}</span>
              </div>
            ))}
          </div>

          <div className="ih-actions-row">
            <button className="ih-btn ih-btn-primary" onClick={testA2aDiscovery}>
              <RefreshCw size={13} />
              Test Discovery
            </button>
            {testMsg.a2a && (
              <span className={`ih-test-result ${testMsg.a2a.includes("Discovered") ? "ih-success" : "ih-error"}`}>
                {testMsg.a2a.includes("Discovered") ? <CheckCircle size={13} /> : <XCircle size={13} />}
                {testMsg.a2a}
              </span>
            )}
          </div>
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  4. API Keys                                              */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Key size={18} />} title="API Keys">
          <p className="ih-section-desc">
            Store API keys for AI providers. Keys are saved locally in your vault config.
          </p>

          {apiKeys.map((slot) => (
            <div key={slot.configKey} className="ih-key-slot">
              <div className="ih-key-header">
                <span className="ih-key-label">{slot.label}</span>
                {slot.value && !slot.showInput && (
                  <span className="ih-key-masked">{maskValue(slot.value)}</span>
                )}
              </div>

              {slot.showInput ? (
                <div className="ih-key-input-row">
                  <input
                    className="ih-input ih-input-wide"
                    type="password"
                    placeholder={`Enter ${slot.label}`}
                    value={keyDraft[slot.configKey] || ""}
                    onChange={(e) => setKeyDraft((d) => ({ ...d, [slot.configKey]: e.target.value }))}
                  />
                  <button className="ih-btn ih-btn-primary" onClick={() => saveApiKey(slot.configKey)}>
                    <Check size={13} />
                    Save
                  </button>
                  <button
                    className="ih-btn ih-btn-small"
                    onClick={() =>
                      setApiKeys((prev) =>
                        prev.map((k) => (k.configKey === slot.configKey ? { ...k, showInput: false } : k))
                      )
                    }
                  >
                    Cancel
                  </button>
                </div>
              ) : (
                <div className="ih-key-actions">
                  <button
                    className="ih-btn ih-btn-small"
                    onClick={() =>
                      setApiKeys((prev) =>
                        prev.map((k) => (k.configKey === slot.configKey ? { ...k, showInput: true } : k))
                      )
                    }
                  >
                    {slot.value ? <><EyeOff size={12} /> Change</> : <><Eye size={12} /> Set Key</>}
                  </button>
                  {slot.value && (
                    <button className="ih-btn ih-btn-small ih-btn-danger" onClick={() => clearApiKey(slot.configKey)}>
                      <Trash2 size={12} />
                      Clear
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}
        </Section>

        {/* -------------------------------------------------------- */}
        {/*  5. Webhooks & Automations                                */}
        {/* -------------------------------------------------------- */}
        <Section icon={<Bell size={18} />} title="Webhooks & Automations">
          <p className="ih-section-desc">
            Configure webhook URLs to trigger external services when events occur in your vault.
          </p>

          {webhooks.map((hook, idx) => (
            <div key={hook.configKey} className="ih-webhook-slot">
              <div className="ih-webhook-header">
                <span className="ih-webhook-label">{hook.label}</span>
                <span className="ih-webhook-trigger">{hook.trigger}</span>
                <label className="ih-toggle">
                  <input
                    type="checkbox"
                    checked={hook.enabled}
                    onChange={(e) => updateWebhook(idx, { enabled: e.target.checked })}
                  />
                  <span className="ih-toggle-slider" />
                </label>
              </div>
              <input
                className="ih-input ih-input-full"
                placeholder="https://your-service.com/webhook"
                value={hook.url}
                onChange={(e) => updateWebhook(idx, { url: e.target.value })}
                disabled={!hook.enabled}
              />
            </div>
          ))}
        </Section>

        <div className="ih-footer">
          <Settings size={14} />
          <span>All integration data is stored locally in your vault configuration.</span>
        </div>
      </div>

      {/* ============================================================ */}
      {/*  Scoped Styles                                                */}
      {/* ============================================================ */}
      <style>{`
        .ih-wrapper {
          max-width: 820px;
          margin: 0 auto;
          padding: 24px 32px 64px;
        }

        /* Refresh button in header */
        .ih-refresh-all {
          display: flex;
          align-items: center;
          gap: 5px;
          background: none;
          border: 1px solid var(--border, #27272a);
          color: var(--text-muted, #a1a1aa);
          padding: 4px 10px;
          border-radius: 6px;
          font-size: 0.78rem;
          cursor: pointer;
          margin-left: auto;
        }
        .ih-refresh-all:hover {
          color: var(--text-primary, #e4e4e7);
          border-color: var(--accent, #3b82f6);
        }

        /* ---- Dashboard Row ---- */
        .ih-dashboard-row {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
          margin-bottom: 20px;
        }
        @media (max-width: 700px) {
          .ih-dashboard-row { grid-template-columns: repeat(2, 1fr); }
        }
        .ih-status-card {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 16px;
          background: var(--bg-secondary, #18181b);
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
        }
        .ih-status-card-icon {
          color: var(--accent, #3b82f6);
          display: flex;
        }
        .ih-status-card-label {
          font-size: 0.78rem;
          color: var(--text-muted, #a1a1aa);
          display: block;
        }
        .ih-status-card-value {
          font-size: 0.82rem;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .ih-status-online { color: #22c55e; }
        .ih-status-offline { color: #ef4444; }
        .ih-status-checking { color: #f59e0b; }

        /* ---- Status Dot ---- */
        .ih-status-dot {
          display: inline-block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        /* ---- Section ---- */
        .ih-section {
          border: 1px solid var(--border, #27272a);
          border-radius: 10px;
          margin-bottom: 12px;
          background: var(--bg-secondary, #18181b);
          overflow: hidden;
        }
        .ih-section-header {
          display: flex;
          align-items: center;
          gap: 10px;
          width: 100%;
          padding: 14px 18px;
          background: none;
          border: none;
          color: var(--text-primary, #e4e4e7);
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          text-align: left;
        }
        .ih-section-header:hover {
          background: var(--bg-hover, #27272a);
        }
        .ih-section-icon {
          display: flex;
          color: var(--accent, #3b82f6);
        }
        .ih-section-title {
          flex: 1;
        }
        .ih-section-badge {
          font-size: 0.72rem;
          background: var(--accent, #3b82f6);
          color: #fff;
          padding: 1px 7px;
          border-radius: 10px;
          font-weight: 600;
          display: flex;
          align-items: center;
        }
        .ih-chevron {
          color: var(--text-muted, #a1a1aa);
          font-size: 0.85rem;
        }
        .ih-section-body {
          padding: 4px 20px 20px;
          color: var(--text-secondary, #d4d4d8);
          font-size: 0.88rem;
          line-height: 1.6;
        }
        .ih-section-body h4 {
          margin: 16px 0 8px;
          font-size: 0.88rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .ih-section-desc {
          margin: 0 0 14px;
          color: var(--text-muted, #a1a1aa);
          font-size: 0.84rem;
        }

        /* ---- Info rows ---- */
        .ih-info-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 0;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .ih-info-row:last-of-type { border-bottom: none; }
        .ih-label {
          font-size: 0.82rem;
          color: var(--text-muted, #a1a1aa);
          min-width: 100px;
          flex-shrink: 0;
        }
        .ih-value {
          font-size: 0.85rem;
          font-weight: 500;
        }
        .ih-mono {
          background: var(--bg-tertiary, #27272a);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.82rem;
          font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
          color: var(--accent, #3b82f6);
        }

        /* ---- Snippet ---- */
        .ih-snippet {
          position: relative;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          margin: 10px 0;
          overflow: hidden;
        }
        .ih-snippet pre {
          margin: 0;
          padding: 14px 16px;
          overflow-x: auto;
          font-size: 0.8rem;
          line-height: 1.6;
        }
        .ih-snippet code {
          background: none;
          padding: 0;
          color: var(--text-secondary, #d4d4d8);
          font-family: "SF Mono", "Fira Code", "Cascadia Code", monospace;
        }
        .ih-snippet-lang {
          position: absolute;
          top: 6px;
          right: 36px;
          font-size: 0.68rem;
          color: var(--text-muted, #71717a);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .ih-snippet-copy {
          position: absolute;
          top: 6px;
          right: 8px;
          background: none;
          border: none;
          color: var(--text-muted, #71717a);
          cursor: pointer;
          padding: 2px;
          display: flex;
          border-radius: 4px;
        }
        .ih-snippet-copy:hover {
          color: var(--text-primary, #e4e4e7);
          background: var(--bg-hover, #27272a);
        }

        /* ---- Buttons ---- */
        .ih-btn {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 6px 12px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: var(--bg-tertiary, #27272a);
          color: var(--text-secondary, #d4d4d8);
          font-size: 0.8rem;
          cursor: pointer;
          white-space: nowrap;
          transition: all 0.15s;
        }
        .ih-btn:hover {
          border-color: var(--text-muted, #a1a1aa);
          color: var(--text-primary, #e4e4e7);
        }
        .ih-btn-primary {
          background: var(--accent, #3b82f6);
          border-color: var(--accent, #3b82f6);
          color: #fff;
        }
        .ih-btn-primary:hover {
          opacity: 0.9;
          color: #fff;
        }
        .ih-btn-small {
          padding: 4px 8px;
          font-size: 0.76rem;
        }
        .ih-btn-danger {
          color: #ef4444;
        }
        .ih-btn-danger:hover {
          border-color: #ef4444;
          background: rgba(239, 68, 68, 0.1);
          color: #ef4444;
        }

        /* ---- Actions row ---- */
        .ih-actions-row {
          display: flex;
          align-items: center;
          gap: 12px;
          margin: 14px 0 4px;
          flex-wrap: wrap;
        }
        .ih-test-result {
          display: flex;
          align-items: center;
          gap: 5px;
          font-size: 0.8rem;
          font-weight: 500;
        }
        .ih-success { color: #22c55e; }
        .ih-error { color: #ef4444; }

        /* ---- Add form (MCP servers) ---- */
        .ih-add-form {
          display: flex;
          gap: 8px;
          margin-bottom: 14px;
          flex-wrap: wrap;
        }
        .ih-input {
          padding: 7px 10px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: var(--bg-tertiary, #0f0f12);
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          outline: none;
          min-width: 0;
        }
        .ih-input:focus {
          border-color: var(--accent, #3b82f6);
        }
        .ih-input-wide { flex: 1; min-width: 180px; }
        .ih-input-full { width: 100%; }
        .ih-input:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .ih-select {
          padding: 7px 10px;
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
          background: var(--bg-tertiary, #0f0f12);
          color: var(--text-primary, #e4e4e7);
          font-size: 0.82rem;
          outline: none;
          cursor: pointer;
        }
        .ih-select:focus {
          border-color: var(--accent, #3b82f6);
        }

        /* ---- Server list ---- */
        .ih-server-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .ih-server-row {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
        }
        .ih-server-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .ih-server-name {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .ih-server-url {
          font-size: 0.76rem;
          color: var(--text-muted, #a1a1aa);
          font-family: "SF Mono", "Fira Code", monospace;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .ih-server-transport {
          font-size: 0.7rem;
          color: var(--accent, #3b82f6);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .ih-server-actions {
          display: flex;
          gap: 6px;
          flex-shrink: 0;
        }
        .ih-empty {
          color: var(--text-muted, #71717a);
          font-size: 0.84rem;
          font-style: italic;
          text-align: center;
          padding: 20px 0;
        }

        /* ---- Skills list (A2A) ---- */
        .ih-skills-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
          margin-bottom: 10px;
        }
        .ih-skill-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 8px 12px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 6px;
        }
        .ih-skill-name {
          background: var(--bg-secondary, #18181b);
          padding: 2px 8px;
          border-radius: 4px;
          font-size: 0.78rem;
          font-family: "SF Mono", "Fira Code", monospace;
          color: var(--accent, #3b82f6);
          flex-shrink: 0;
        }
        .ih-skill-desc {
          font-size: 0.82rem;
          color: var(--text-muted, #a1a1aa);
        }

        /* ---- API Key slots ---- */
        .ih-key-slot {
          padding: 12px 14px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          margin-bottom: 8px;
        }
        .ih-key-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        .ih-key-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .ih-key-masked {
          font-size: 0.8rem;
          color: var(--text-muted, #a1a1aa);
          font-family: "SF Mono", "Fira Code", monospace;
          letter-spacing: 1px;
        }
        .ih-key-input-row {
          display: flex;
          gap: 8px;
          align-items: center;
        }
        .ih-key-actions {
          display: flex;
          gap: 8px;
        }

        /* ---- Webhook slots ---- */
        .ih-webhook-slot {
          padding: 12px 14px;
          background: var(--bg-tertiary, #0f0f12);
          border: 1px solid var(--border, #27272a);
          border-radius: 8px;
          margin-bottom: 8px;
        }
        .ih-webhook-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
        }
        .ih-webhook-label {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
          flex: 1;
        }
        .ih-webhook-trigger {
          font-size: 0.72rem;
          background: var(--bg-secondary, #18181b);
          padding: 2px 8px;
          border-radius: 4px;
          color: var(--accent, #3b82f6);
          font-family: "SF Mono", "Fira Code", monospace;
        }

        /* ---- Toggle switch ---- */
        .ih-toggle {
          position: relative;
          display: inline-block;
          width: 36px;
          height: 20px;
          flex-shrink: 0;
        }
        .ih-toggle input {
          opacity: 0;
          width: 0;
          height: 0;
        }
        .ih-toggle-slider {
          position: absolute;
          cursor: pointer;
          top: 0; left: 0; right: 0; bottom: 0;
          background: var(--border, #3f3f46);
          border-radius: 20px;
          transition: background 0.2s;
        }
        .ih-toggle-slider::before {
          content: "";
          position: absolute;
          height: 14px;
          width: 14px;
          left: 3px;
          bottom: 3px;
          background: #fff;
          border-radius: 50%;
          transition: transform 0.2s;
        }
        .ih-toggle input:checked + .ih-toggle-slider {
          background: var(--accent, #3b82f6);
        }
        .ih-toggle input:checked + .ih-toggle-slider::before {
          transform: translateX(16px);
        }

        /* ---- Footer ---- */
        .ih-footer {
          text-align: center;
          margin-top: 28px;
          padding-top: 18px;
          border-top: 1px solid var(--border, #27272a);
          color: var(--text-muted, #71717a);
          font-size: 0.8rem;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
        }
      `}</style>
    </div>
  );
}
