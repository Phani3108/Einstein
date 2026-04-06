/**
 * IntegrationsPanel.tsx — Settings panel for connecting third-party integrations.
 *
 * Lets users connect/disconnect OAuth-based integrations (Gmail, Slack, Jira, etc.)
 * and configure privacy controls for data sync.
 */

import { useState, useEffect, useCallback } from "react";
import {
  Mail,
  MessageSquare,
  CheckSquare,
  GitBranch,
  Video,
  Target,
  RefreshCw,
  ExternalLink,
  Shield,
  Loader,
} from "lucide-react";
import { api } from "../lib/api";
import type { LucideIcon } from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Provider definitions                                               */
/* ------------------------------------------------------------------ */

interface ProviderInfo {
  name: string;
  icon: LucideIcon;
  color: string;
  description: string;
}

const PROVIDERS: Record<string, ProviderInfo> = {
  gmail:   { name: "Gmail",   icon: Mail,          color: "#EA4335", description: "Auto-capture emails" },
  outlook: { name: "Outlook", icon: Mail,          color: "#0078D4", description: "Microsoft email sync" },
  slack:   { name: "Slack",   icon: MessageSquare, color: "#4A154B", description: "Channel messages" },
  jira:    { name: "Jira",    icon: CheckSquare,   color: "#0052CC", description: "Issue tracking" },
  github:  { name: "GitHub",  icon: GitBranch,     color: "#333",    description: "PRs, issues, reviews" },
  zoom:    { name: "Zoom",    icon: Video,         color: "#2D8CFF", description: "Meeting transcripts" },
  linear:  { name: "Linear",  icon: Target,        color: "#5E6AD2", description: "Project tracking" },
};

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface IntegrationStatus {
  provider: string;
  connected: boolean;
  last_sync?: string;
  scopes?: string[];
}

interface PrivacySettings {
  emailBodySync: boolean;
  slackChannels: string;
  githubPrivateRepos: boolean;
  meetingTranscripts: boolean;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function IntegrationsPanel() {
  const [integrations, setIntegrations] = useState<IntegrationStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [syncingProvider, setSyncingProvider] = useState<string | null>(null);
  const [privacy, setPrivacy] = useState<PrivacySettings>({
    emailBodySync: false,
    slackChannels: "",
    githubPrivateRepos: false,
    meetingTranscripts: true,
  });

  // Load integration statuses
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.listIntegrations()
      .then((data: IntegrationStatus[]) => {
        if (!cancelled) setIntegrations(data);
      })
      .catch(() => {
        // API not available yet — show all as disconnected
        if (!cancelled) setIntegrations([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, []);

  const getStatus = useCallback(
    (provider: string): IntegrationStatus | undefined =>
      integrations.find((i) => i.provider === provider),
    [integrations]
  );

  const handleConnect = useCallback(async (provider: string) => {
    setConnectingProvider(provider);
    try {
      const result = await api.connectIntegration(provider);
      if (result && (result as any).oauth_url) {
        window.open((result as any).oauth_url, "_blank", "noopener");
      }
      // Refresh statuses after a short delay (OAuth redirect takes time)
      setTimeout(() => {
        api.listIntegrations()
          .then((data: IntegrationStatus[]) => setIntegrations(data))
          .catch(() => {});
      }, 2000);
    } catch (err) {
      console.error(`Failed to connect ${provider}:`, err);
    } finally {
      setConnectingProvider(null);
    }
  }, []);

  const handleDisconnect = useCallback(async (provider: string) => {
    try {
      await api.disconnectIntegration(provider);
      setIntegrations((prev) =>
        prev.map((i) =>
          i.provider === provider ? { ...i, connected: false, last_sync: undefined } : i
        )
      );
    } catch (err) {
      console.error(`Failed to disconnect ${provider}:`, err);
    }
  }, []);

  const handleSync = useCallback(async (provider: string) => {
    setSyncingProvider(provider);
    try {
      await api.syncIntegration(provider);
      // Refresh statuses
      const data = await api.listIntegrations();
      setIntegrations(data);
    } catch (err) {
      console.error(`Failed to sync ${provider}:`, err);
    } finally {
      setSyncingProvider(null);
    }
  }, []);

  const formatLastSync = (iso?: string): string => {
    if (!iso) return "";
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  return (
    <div className="ip-container">
      {/* Header */}
      <div className="ip-header">
        <h2 className="ip-title">Integrations</h2>
        <p className="ip-subtitle">Connect your tools to capture context automatically</p>
      </div>

      {/* Integration cards grid */}
      <div className="ip-content">
        {loading ? (
          <div className="ip-loading">
            <Loader size={20} className="ip-spinner" />
            <span>Loading integrations...</span>
          </div>
        ) : (
          <div className="ip-grid">
            {Object.entries(PROVIDERS).map(([key, provider]) => {
              const status = getStatus(key);
              const isConnected = status?.connected ?? false;
              const isConnecting = connectingProvider === key;
              const isSyncing = syncingProvider === key;
              const Icon = provider.icon;

              return (
                <div key={key} className={`ip-card ${isConnected ? "ip-card--connected" : ""}`}>
                  <div className="ip-card-header">
                    <div className="ip-card-icon" style={{ backgroundColor: provider.color + "20" }}>
                      <Icon size={20} style={{ color: provider.color }} />
                    </div>
                    <div className="ip-card-info">
                      <div className="ip-card-name">{provider.name}</div>
                      <div className="ip-card-desc">{provider.description}</div>
                    </div>
                  </div>

                  <div className="ip-card-status">
                    <span className={`ip-badge ${isConnected ? "ip-badge--connected" : "ip-badge--disconnected"}`}>
                      {isConnected ? "Connected" : "Not connected"}
                    </span>
                    {isConnected && status?.last_sync && (
                      <span className="ip-last-sync">
                        Synced {formatLastSync(status.last_sync)}
                      </span>
                    )}
                  </div>

                  <div className="ip-card-actions">
                    {isConnected ? (
                      <>
                        <button
                          className="ip-btn ip-btn--sync"
                          onClick={() => handleSync(key)}
                          disabled={isSyncing}
                          title="Sync now"
                        >
                          <RefreshCw size={14} className={isSyncing ? "ip-spinner" : ""} />
                          {isSyncing ? "Syncing..." : "Sync"}
                        </button>
                        <button
                          className="ip-btn ip-btn--disconnect"
                          onClick={() => handleDisconnect(key)}
                        >
                          Disconnect
                        </button>
                      </>
                    ) : (
                      <button
                        className="ip-btn ip-btn--connect"
                        onClick={() => handleConnect(key)}
                        disabled={isConnecting}
                      >
                        {isConnecting ? (
                          <>
                            <Loader size={14} className="ip-spinner" />
                            Connecting...
                          </>
                        ) : (
                          <>
                            <ExternalLink size={14} />
                            Connect
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Privacy Controls */}
        <div className="ip-privacy">
          <div className="ip-privacy-header">
            <Shield size={16} />
            <h3>Privacy Controls</h3>
          </div>
          <div className="ip-privacy-body">
            <label className="ip-checkbox">
              <input
                type="checkbox"
                checked={privacy.emailBodySync}
                onChange={(e) => setPrivacy((p) => ({ ...p, emailBodySync: e.target.checked }))}
              />
              <span>Sync full email body (not just metadata)</span>
            </label>
            <label className="ip-checkbox">
              <input
                type="checkbox"
                checked={privacy.githubPrivateRepos}
                onChange={(e) => setPrivacy((p) => ({ ...p, githubPrivateRepos: e.target.checked }))}
              />
              <span>Include private repositories (GitHub)</span>
            </label>
            <label className="ip-checkbox">
              <input
                type="checkbox"
                checked={privacy.meetingTranscripts}
                onChange={(e) => setPrivacy((p) => ({ ...p, meetingTranscripts: e.target.checked }))}
              />
              <span>Capture meeting transcripts (Zoom)</span>
            </label>
            <div className="ip-field">
              <label className="ip-field-label">Slack channels to sync (comma-separated, empty = all)</label>
              <input
                type="text"
                className="ip-field-input"
                placeholder="#general, #engineering, #design"
                value={privacy.slackChannels}
                onChange={(e) => setPrivacy((p) => ({ ...p, slackChannels: e.target.value }))}
              />
            </div>
          </div>
        </div>
      </div>

      <style>{`
        .ip-container {
          height: 100%;
          display: flex;
          flex-direction: column;
          background: var(--bg-primary, #1e1e2e);
          overflow: hidden;
        }
        .ip-header {
          padding: 24px 28px 16px;
          border-bottom: 1px solid var(--border, #27272a);
        }
        .ip-title {
          margin: 0 0 4px;
          font-size: 20px;
          font-weight: 700;
          color: var(--text-primary, #e4e4e7);
        }
        .ip-subtitle {
          margin: 0;
          font-size: 13px;
          color: var(--text-muted, #71717a);
        }
        .ip-content {
          flex: 1;
          overflow-y: auto;
          padding: 20px 28px;
        }
        .ip-loading {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 10px;
          padding: 40px 0;
          color: var(--text-muted, #71717a);
          font-size: 13px;
        }
        .ip-spinner {
          animation: ip-spin 1s linear infinite;
        }
        @keyframes ip-spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        /* Grid */
        .ip-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 14px;
          margin-bottom: 28px;
        }

        /* Card */
        .ip-card {
          background: var(--bg-secondary, #27272a);
          border: 1px solid var(--border, #3f3f46);
          border-radius: 10px;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
          transition: border-color 0.15s;
        }
        .ip-card:hover {
          border-color: var(--text-muted, #52525b);
        }
        .ip-card--connected {
          border-color: #22c55e40;
        }
        .ip-card-header {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .ip-card-icon {
          width: 40px;
          height: 40px;
          border-radius: 8px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }
        .ip-card-info {
          min-width: 0;
        }
        .ip-card-name {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary, #e4e4e7);
        }
        .ip-card-desc {
          font-size: 12px;
          color: var(--text-muted, #71717a);
          margin-top: 2px;
        }

        /* Status */
        .ip-card-status {
          display: flex;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap;
        }
        .ip-badge {
          font-size: 11px;
          font-weight: 600;
          padding: 2px 8px;
          border-radius: 10px;
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .ip-badge--connected {
          background: #22c55e20;
          color: #4ade80;
        }
        .ip-badge--disconnected {
          background: #71717a20;
          color: #a1a1aa;
        }
        .ip-last-sync {
          font-size: 11px;
          color: var(--text-muted, #71717a);
        }

        /* Actions */
        .ip-card-actions {
          display: flex;
          gap: 8px;
          margin-top: auto;
        }
        .ip-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 6px;
          border: 1px solid var(--border, #3f3f46);
          background: none;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.15s, border-color 0.15s;
          color: var(--text-primary, #e4e4e7);
        }
        .ip-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .ip-btn--connect {
          background: #3b82f620;
          border-color: #3b82f640;
          color: #60a5fa;
        }
        .ip-btn--connect:hover:not(:disabled) {
          background: #3b82f630;
        }
        .ip-btn--sync:hover:not(:disabled) {
          background: var(--bg-primary, #1e1e2e);
        }
        .ip-btn--disconnect {
          color: #f87171;
          border-color: transparent;
        }
        .ip-btn--disconnect:hover {
          background: #ef444420;
        }

        /* Privacy section */
        .ip-privacy {
          border-top: 1px solid var(--border, #27272a);
          padding-top: 20px;
        }
        .ip-privacy-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 14px;
          color: var(--text-primary, #e4e4e7);
        }
        .ip-privacy-header h3 {
          margin: 0;
          font-size: 14px;
          font-weight: 600;
        }
        .ip-privacy-body {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .ip-checkbox {
          display: flex;
          align-items: center;
          gap: 10px;
          cursor: pointer;
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
        }
        .ip-checkbox input[type="checkbox"] {
          width: 16px;
          height: 16px;
          accent-color: #3b82f6;
          cursor: pointer;
          flex-shrink: 0;
        }
        .ip-field {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .ip-field-label {
          font-size: 12px;
          color: var(--text-muted, #71717a);
        }
        .ip-field-input {
          background: var(--bg-primary, #1e1e2e);
          border: 1px solid var(--border, #3f3f46);
          border-radius: 6px;
          padding: 8px 10px;
          font-size: 13px;
          color: var(--text-primary, #e4e4e7);
          outline: none;
        }
        .ip-field-input:focus {
          border-color: #3b82f6;
        }
        .ip-field-input::placeholder {
          color: var(--text-muted, #52525b);
        }
      `}</style>
    </div>
  );
}
