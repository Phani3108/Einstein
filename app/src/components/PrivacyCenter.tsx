import { useState } from "react";
import {
  Shield, Lock, Unlock, Eye, EyeOff,
  Smartphone, Monitor, Globe, Cloud, CloudOff,
  HardDrive, Key, RefreshCw, Link2, Copy,
  Trash2, Clock, CheckCircle, AlertTriangle,
  Download, Upload, FileText, ExternalLink,
} from "lucide-react";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

type SyncMethod = "icloud" | "syncthing" | "manual" | "git";
type ShareLevel = "private" | "link" | "public";

interface DeviceEntry {
  id: string;
  name: string;
  type: "desktop" | "mobile" | "tablet";
  lastSync: string;
  status: "synced" | "pending" | "error";
}

interface SharedNote {
  id: string;
  title: string;
  level: ShareLevel;
  expiresAt: string | null;
  accessCount: number;
  lastAccessed: string | null;
}

interface NetworkLogEntry {
  timestamp: string;
  direction: "outbound" | "inbound";
  destination: string;
  bytes: number;
  blocked: boolean;
}

/* ------------------------------------------------------------------ */
/*  Section toggle                                                     */
/* ------------------------------------------------------------------ */

type Section =
  | "local-first"
  | "encryption"
  | "privacy-dashboard"
  | "sync"
  | "clipper"
  | "sharing";

/* ------------------------------------------------------------------ */
/*  Mock data                                                          */
/* ------------------------------------------------------------------ */

const MOCK_DEVICES: DeviceEntry[] = [
  { id: "d1", name: "MacBook Pro", type: "desktop", lastSync: "2026-04-05T09:12:00Z", status: "synced" },
  { id: "d2", name: "iPhone 16", type: "mobile", lastSync: "2026-04-05T08:45:00Z", status: "synced" },
  { id: "d3", name: "iPad Air", type: "tablet", lastSync: "2026-04-04T22:10:00Z", status: "pending" },
];

const MOCK_SHARED_NOTES: SharedNote[] = [
  { id: "s1", title: "Project Roadmap Q2", level: "link", expiresAt: "2026-04-15T00:00:00Z", accessCount: 12, lastAccessed: "2026-04-04T14:20:00Z" },
  { id: "s2", title: "Meeting Notes - Design Sync", level: "public", expiresAt: null, accessCount: 34, lastAccessed: "2026-04-05T07:55:00Z" },
  { id: "s3", title: "Personal Journal", level: "private", expiresAt: null, accessCount: 0, lastAccessed: null },
];

const MOCK_NETWORK_LOG: NetworkLogEntry[] = [];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function Badge({ text, color }: { text: string; color: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 4,
        fontSize: 11,
        fontWeight: 600,
        padding: "2px 8px",
        borderRadius: 9999,
        background: `${color}18`,
        color,
        border: `1px solid ${color}30`,
      }}
    >
      {text}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function PrivacyCenter() {
  /* Section expansion */
  const [open, setOpen] = useState<Set<Section>>(new Set(["local-first"]));
  const toggle = (s: Section) =>
    setOpen((prev) => {
      const next = new Set(prev);
      next.has(s) ? next.delete(s) : next.add(s);
      return next;
    });

  /* Encryption */
  const [encrypted, setEncrypted] = useState(false);
  const [showPassphrase, setShowPassphrase] = useState(false);
  const [passphrase, setPassphrase] = useState("");

  /* Sync */
  const [syncMethod, setSyncMethod] = useState<SyncMethod>("icloud");
  const [devices] = useState<DeviceEntry[]>(MOCK_DEVICES);

  /* Sharing */
  const [sharedNotes, setSharedNotes] = useState<SharedNote[]>(MOCK_SHARED_NOTES);

  /* Privacy dashboard */
  const [localMode] = useState(true);
  const [networkLog] = useState<NetworkLogEntry[]>(MOCK_NETWORK_LOG);

  /* Data inventory (mock) */
  const stats = { notes: 247, words: 89420, attachments: 38, vaultSizeMb: 14.7 };

  /* ---------------------------------------------------------------- */
  /*  Section header                                                   */
  /* ---------------------------------------------------------------- */

  const SectionHeader = ({
    id,
    icon,
    title,
    subtitle,
  }: {
    id: Section;
    icon: React.ReactNode;
    title: string;
    subtitle: string;
  }) => (
    <button className="pc-section-header" onClick={() => toggle(id)}>
      <span className="pc-section-icon">{icon}</span>
      <span style={{ flex: 1, textAlign: "left" }}>
        <span className="pc-section-title">{title}</span>
        <span className="pc-section-sub">{subtitle}</span>
      </span>
      <span
        style={{
          transform: open.has(id) ? "rotate(90deg)" : "rotate(0deg)",
          transition: "transform .15s",
          fontSize: 14,
          opacity: 0.5,
        }}
      >
        &#9654;
      </span>
    </button>
  );

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="pc-root">
      <div className="pc-wrapper">
        {/* Hero */}
        <div className="pc-hero">
          <Shield size={32} style={{ color: "#6366f1" }} />
          <h1 className="pc-hero-title">Privacy &amp; Security Center</h1>
          <p className="pc-hero-sub">
            Full visibility into what Einstein stores, where it goes, and who can
            access it.
          </p>
        </div>

        {/* =========================================================== */}
        {/*  1. Local-First Value Proposition                            */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="local-first"
            icon={<HardDrive size={18} />}
            title="Your Data, Your Control"
            subtitle="Local-first architecture"
          />
          {open.has("local-first") && (
            <div className="pc-body">
              <ul className="pc-bullets">
                <li><CheckCircle size={14} style={{ color: "#22c55e" }} /> All notes stored as plain <code>.md</code> files</li>
                <li><CheckCircle size={14} style={{ color: "#22c55e" }} /> No cloud required &mdash; works fully offline</li>
                <li><CheckCircle size={14} style={{ color: "#22c55e" }} /> Zero telemetry or tracking</li>
                <li><CheckCircle size={14} style={{ color: "#22c55e" }} /> Export everything, anytime</li>
                <li><CheckCircle size={14} style={{ color: "#22c55e" }} /> Open file format &mdash; no lock-in</li>
              </ul>

              {/* Feature comparison table */}
              <h4 className="pc-h4">Feature Comparison</h4>
              <table className="pc-table">
                <thead>
                  <tr>
                    <th>Feature</th>
                    <th>Local-Only</th>
                    <th>Cloud-Enhanced</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>Markdown storage</td><td><CheckCircle size={14} style={{ color: "#22c55e" }} /></td><td><CheckCircle size={14} style={{ color: "#22c55e" }} /></td></tr>
                  <tr><td>Offline access</td><td><CheckCircle size={14} style={{ color: "#22c55e" }} /></td><td><CheckCircle size={14} style={{ color: "#22c55e" }} /></td></tr>
                  <tr><td>AI completions</td><td>On-device only</td><td>Cloud LLM</td></tr>
                  <tr><td>Cross-device sync</td><td>Manual / folder</td><td>Automatic</td></tr>
                  <tr><td>Semantic search</td><td>Local index</td><td>Vector DB</td></tr>
                  <tr><td>Data residency</td><td>Your device</td><td>Your chosen region</td></tr>
                  <tr><td>Network calls</td><td>None</td><td>Encrypted TLS only</td></tr>
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* =========================================================== */}
        {/*  2. Encryption Status                                        */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="encryption"
            icon={<Lock size={18} />}
            title="Encryption Status"
            subtitle="At-rest encryption for .einstein/ index"
          />
          {open.has("encryption") && (
            <div className="pc-body">
              <div className="pc-card" style={{ display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>
                    Vault Encryption
                  </div>
                  <div style={{ fontSize: 12, opacity: 0.6 }}>
                    Encrypt <code>.einstein/</code> index data at rest
                  </div>
                </div>
                {encrypted ? (
                  <Badge text="Encrypted" color="#22c55e" />
                ) : (
                  <Badge text="Not Encrypted" color="#f59e0b" />
                )}
                <button
                  className="pc-toggle"
                  data-on={encrypted}
                  onClick={() => setEncrypted(!encrypted)}
                  aria-label="Toggle encryption"
                >
                  <span className="pc-toggle-knob" />
                </button>
              </div>

              {encrypted && (
                <div className="pc-card" style={{ marginTop: 10 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 8 }}>
                    <Key size={14} style={{ marginRight: 6, verticalAlign: -2 }} />
                    Encryption Key Management
                  </div>
                  <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <div style={{ position: "relative", flex: 1 }}>
                      <input
                        type={showPassphrase ? "text" : "password"}
                        className="pc-input"
                        placeholder="Enter passphrase..."
                        value={passphrase}
                        onChange={(e) => setPassphrase(e.target.value)}
                      />
                      <button
                        className="pc-icon-btn"
                        style={{ position: "absolute", right: 4, top: "50%", transform: "translateY(-50%)" }}
                        onClick={() => setShowPassphrase(!showPassphrase)}
                        aria-label="Toggle passphrase visibility"
                      >
                        {showPassphrase ? <EyeOff size={14} /> : <Eye size={14} />}
                      </button>
                    </div>
                    <button className="pc-btn pc-btn-primary" disabled={!passphrase}>
                      Set Passphrase
                    </button>
                  </div>
                  <p style={{ fontSize: 11, opacity: 0.5, marginTop: 6 }}>
                    Your passphrase never leaves this device. Losing it means losing access to encrypted data.
                  </p>
                </div>
              )}

              {!encrypted && (
                <div className="pc-warning" style={{ marginTop: 10 }}>
                  <AlertTriangle size={14} style={{ color: "#f59e0b", flexShrink: 0 }} />
                  <span>
                    Your <code>.einstein/</code> index is unencrypted. Enable vault encryption
                    to protect your data at rest.
                  </span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* =========================================================== */}
        {/*  3. Privacy Dashboard                                        */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="privacy-dashboard"
            icon={<Eye size={18} />}
            title="Privacy Dashboard"
            subtitle="Data inventory and network activity"
          />
          {open.has("privacy-dashboard") && (
            <div className="pc-body">
              {/* Data inventory */}
              <h4 className="pc-h4">Data Inventory</h4>
              <div className="pc-stat-grid">
                <div className="pc-stat-card">
                  <FileText size={18} style={{ color: "#6366f1" }} />
                  <div className="pc-stat-value">{stats.notes}</div>
                  <div className="pc-stat-label">Notes</div>
                </div>
                <div className="pc-stat-card">
                  <FileText size={18} style={{ color: "#a78bfa" }} />
                  <div className="pc-stat-value">{stats.words.toLocaleString()}</div>
                  <div className="pc-stat-label">Words</div>
                </div>
                <div className="pc-stat-card">
                  <Download size={18} style={{ color: "#14b8a6" }} />
                  <div className="pc-stat-value">{stats.attachments}</div>
                  <div className="pc-stat-label">Attachments</div>
                </div>
                <div className="pc-stat-card">
                  <HardDrive size={18} style={{ color: "#f59e0b" }} />
                  <div className="pc-stat-value">{stats.vaultSizeMb} MB</div>
                  <div className="pc-stat-label">Vault Size</div>
                </div>
              </div>

              {/* Local vs Cloud */}
              <h4 className="pc-h4">Data Residency</h4>
              <div className="pc-card">
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  {localMode ? (
                    <>
                      <CloudOff size={16} style={{ color: "#22c55e" }} />
                      <span style={{ fontWeight: 600, fontSize: 13, color: "#22c55e" }}>
                        Local-Only Mode Active
                      </span>
                    </>
                  ) : (
                    <>
                      <Cloud size={16} style={{ color: "#6366f1" }} />
                      <span style={{ fontWeight: 600, fontSize: 13 }}>Cloud-Enhanced Mode</span>
                    </>
                  )}
                </div>
                <table className="pc-table pc-table-sm">
                  <thead>
                    <tr><th>Data</th><th>Stored</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>Markdown notes</td><td>Local filesystem</td></tr>
                    <tr><td>Search index</td><td>Local <code>.einstein/</code></td></tr>
                    <tr><td>Attachments</td><td>Local vault folder</td></tr>
                    <tr><td>Sent to cloud</td><td>{localMode ? <Badge text="Nothing" color="#22c55e" /> : "Encrypted queries"}</td></tr>
                  </tbody>
                </table>
              </div>

              {/* Network activity log */}
              <h4 className="pc-h4">Network Activity Log</h4>
              <div className="pc-card">
                {networkLog.length === 0 ? (
                  <div className="pc-empty">
                    <CloudOff size={24} style={{ opacity: 0.3 }} />
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Zero network calls</span>
                    <span style={{ fontSize: 12, opacity: 0.5 }}>
                      No outbound or inbound network activity detected.
                    </span>
                  </div>
                ) : (
                  <div>
                    {networkLog.map((entry, i) => (
                      <div key={i} className="pc-log-row">
                        <span>{entry.timestamp}</span>
                        <span>{entry.destination}</span>
                        <span>{entry.bytes}B</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {localMode && (
                <div className="pc-assurance">
                  <Shield size={16} style={{ color: "#22c55e" }} />
                  <span>Data never leaves your device in local-only mode.</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* =========================================================== */}
        {/*  4. Cross-Device Sync                                        */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="sync"
            icon={<RefreshCw size={18} />}
            title="Cross-Device Sync"
            subtitle="Keep your vault in sync across devices"
          />
          {open.has("sync") && (
            <div className="pc-body">
              {/* Sync method picker */}
              <h4 className="pc-h4">Sync Method</h4>
              <div className="pc-method-grid">
                {([
                  { key: "icloud" as SyncMethod, icon: <Cloud size={18} />, label: "iCloud Drive", desc: "Apple ecosystem auto-sync" },
                  { key: "syncthing" as SyncMethod, icon: <RefreshCw size={18} />, label: "Syncthing", desc: "Open-source P2P sync" },
                  { key: "manual" as SyncMethod, icon: <Upload size={18} />, label: "Manual", desc: "USB / folder copy" },
                  { key: "git" as SyncMethod, icon: <Globe size={18} />, label: "Git-Based", desc: "Version-controlled sync" },
                ]).map((m) => (
                  <button
                    key={m.key}
                    className={`pc-method-card${syncMethod === m.key ? " active" : ""}`}
                    onClick={() => setSyncMethod(m.key)}
                  >
                    <span style={{ color: syncMethod === m.key ? "#6366f1" : "inherit" }}>
                      {m.icon}
                    </span>
                    <span className="pc-method-label">{m.label}</span>
                    <span className="pc-method-desc">{m.desc}</span>
                  </button>
                ))}
              </div>

              {/* Setup instructions per method */}
              <div className="pc-card" style={{ marginTop: 12 }}>
                <h4 className="pc-h4" style={{ marginTop: 0 }}>Setup: {syncMethod === "icloud" ? "iCloud Drive" : syncMethod === "syncthing" ? "Syncthing" : syncMethod === "manual" ? "Manual (USB / Folder)" : "Git-Based Sync"}</h4>
                {syncMethod === "icloud" && (
                  <ol className="pc-steps">
                    <li>Move your vault folder into <code>~/Library/Mobile Documents/com~apple~CloudDocs/Einstein</code></li>
                    <li>Point Einstein to this folder in Settings &rarr; Vault Path</li>
                    <li>On other Apple devices, Einstein will auto-detect the vault</li>
                  </ol>
                )}
                {syncMethod === "syncthing" && (
                  <ol className="pc-steps">
                    <li>Install Syncthing on all devices</li>
                    <li>Share your vault folder between devices</li>
                    <li>Syncthing handles conflict resolution automatically</li>
                  </ol>
                )}
                {syncMethod === "manual" && (
                  <ol className="pc-steps">
                    <li>Use Settings &rarr; Export to create a vault archive (.zip)</li>
                    <li>Transfer via USB drive, AirDrop, or any file-sharing method</li>
                    <li>Use Settings &rarr; Import on the target device</li>
                  </ol>
                )}
                {syncMethod === "git" && (
                  <ol className="pc-steps">
                    <li>Initialize a git repo in your vault folder: <code>git init</code></li>
                    <li>Add a remote (GitHub, GitLab, or self-hosted)</li>
                    <li>Einstein auto-commits on save; pull on other devices to sync</li>
                  </ol>
                )}
              </div>

              {/* QR Code placeholder for mobile pairing */}
              <div className="pc-card" style={{ marginTop: 12, textAlign: "center" }}>
                <Smartphone size={20} style={{ color: "#6366f1", marginBottom: 6 }} />
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 4 }}>Mobile Pairing</div>
                <div className="pc-qr-placeholder">
                  <Smartphone size={40} style={{ opacity: 0.2 }} />
                  <span style={{ fontSize: 11, opacity: 0.4 }}>QR code generated on pairing request</span>
                </div>
                <p style={{ fontSize: 12, opacity: 0.5, marginTop: 8 }}>
                  <strong>Carry Context:</strong> Start a note on mobile, continue seamlessly on desktop.
                </p>
              </div>

              {/* Device list & last sync status */}
              <h4 className="pc-h4">Linked Devices</h4>
              <div className="pc-device-list">
                {devices.map((d) => (
                  <div key={d.id} className="pc-device-row">
                    <span className="pc-device-icon">
                      {d.type === "desktop" ? <Monitor size={16} /> : <Smartphone size={16} />}
                    </span>
                    <span style={{ flex: 1 }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{d.name}</span>
                      <span style={{ display: "block", fontSize: 11, opacity: 0.5 }}>
                        Last sync: {relativeTime(d.lastSync)}
                      </span>
                    </span>
                    <Badge
                      text={d.status === "synced" ? "Synced" : d.status === "pending" ? "Pending" : "Error"}
                      color={d.status === "synced" ? "#22c55e" : d.status === "pending" ? "#f59e0b" : "#ef4444"}
                    />
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* =========================================================== */}
        {/*  5. Web Clipper & .md Extraction                             */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="clipper"
            icon={<ExternalLink size={18} />}
            title="Web Clipper & .md Extraction"
            subtitle="Capture web content as markdown"
          />
          {open.has("clipper") && (
            <div className="pc-body">
              {/* Browser extensions */}
              <h4 className="pc-h4">Browser Extensions</h4>
              <div className="pc-ext-grid">
                {[
                  { name: "Chrome", status: "Available" },
                  { name: "Firefox", status: "Available" },
                  { name: "Safari", status: "Available" },
                ].map((ext) => (
                  <div key={ext.name} className="pc-card pc-ext-card">
                    <Globe size={16} style={{ color: "#6366f1" }} />
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{ext.name}</span>
                    <Badge text={ext.status} color="#22c55e" />
                    <button className="pc-btn pc-btn-sm">
                      <Download size={12} /> Install
                    </button>
                  </div>
                ))}
              </div>

              {/* Capabilities */}
              <h4 className="pc-h4">Capabilities</h4>
              <ul className="pc-bullets">
                <li><FileText size={14} style={{ color: "#6366f1" }} /> Clip any webpage &rarr; auto-extract to <code>.md</code></li>
                <li><Globe size={14} style={{ color: "#6366f1" }} /> Clip GitHub repos (README, issues) &rarr; structured <code>.md</code> notes</li>
                <li><Link2 size={14} style={{ color: "#6366f1" }} /> URL bookmarking with auto-summary</li>
              </ul>

              {/* Supported formats */}
              <h4 className="pc-h4">Supported Formats</h4>
              <div className="pc-format-grid">
                {[
                  { from: "HTML", to: ".md" },
                  { from: "PDF", to: ".md" },
                  { from: "EPUB", to: ".md" },
                ].map((f) => (
                  <div key={f.from} className="pc-card" style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 14px" }}>
                    <FileText size={14} style={{ color: "#a78bfa" }} />
                    <span style={{ fontSize: 13 }}>{f.from}</span>
                    <span style={{ opacity: 0.3 }}>&rarr;</span>
                    <code style={{ fontSize: 13 }}>{f.to}</code>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* =========================================================== */}
        {/*  6. Sharing Controls                                         */}
        {/* =========================================================== */}
        <div className="pc-section">
          <SectionHeader
            id="sharing"
            icon={<Link2 size={18} />}
            title="Sharing Controls"
            subtitle="Manage access to shared notes"
          />
          {open.has("sharing") && (
            <div className="pc-body">
              <div className="pc-shared-list">
                {sharedNotes.map((note) => (
                  <div key={note.id} className="pc-shared-row">
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                        <FileText size={13} style={{ marginRight: 6, verticalAlign: -2, opacity: 0.5 }} />
                        {note.title}
                      </div>
                      <div style={{ display: "flex", gap: 10, fontSize: 11, opacity: 0.5 }}>
                        {note.expiresAt && (
                          <span>
                            <Clock size={10} style={{ marginRight: 3, verticalAlign: -1 }} />
                            Expires {relativeTime(note.expiresAt)}
                          </span>
                        )}
                        <span>
                          <Eye size={10} style={{ marginRight: 3, verticalAlign: -1 }} />
                          {note.accessCount} views
                        </span>
                        {note.lastAccessed && (
                          <span>Last accessed {relativeTime(note.lastAccessed)}</span>
                        )}
                      </div>
                    </div>

                    {/* Share level selector */}
                    <select
                      className="pc-select"
                      value={note.level}
                      onChange={(e) => {
                        setSharedNotes((prev) =>
                          prev.map((n) =>
                            n.id === note.id ? { ...n, level: e.target.value as ShareLevel } : n
                          )
                        );
                      }}
                    >
                      <option value="private">Private</option>
                      <option value="link">Link-shared</option>
                      <option value="public">Public</option>
                    </select>

                    {/* Actions */}
                    <div style={{ display: "flex", gap: 4 }}>
                      {note.level !== "private" && (
                        <button className="pc-icon-btn" title="Copy share link">
                          <Copy size={14} />
                        </button>
                      )}
                      {note.level !== "private" && (
                        <button
                          className="pc-icon-btn pc-icon-btn-danger"
                          title="Revoke access"
                          onClick={() =>
                            setSharedNotes((prev) =>
                              prev.map((n) =>
                                n.id === note.id ? { ...n, level: "private" as ShareLevel, accessCount: 0 } : n
                              )
                            )
                          }
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ============================================================= */}
      {/*  Styles                                                        */}
      {/* ============================================================= */}
      <style>{`
        .pc-root {
          height: 100%;
          overflow: auto;
          background: var(--bg-primary, #09090b);
          color: var(--text-primary, #e4e4e7);
        }
        .pc-wrapper {
          max-width: 820px;
          margin: 0 auto;
          padding: 24px 32px 64px;
        }

        /* Hero */
        .pc-hero {
          text-align: center;
          padding: 32px 0 24px;
        }
        .pc-hero-title {
          font-size: 24px;
          font-weight: 700;
          margin: 10px 0 6px;
        }
        .pc-hero-sub {
          font-size: 13px;
          opacity: 0.55;
          max-width: 480px;
          margin: 0 auto;
          line-height: 1.5;
        }

        /* Sections */
        .pc-section {
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 10px;
          margin-bottom: 10px;
          overflow: hidden;
          background: rgba(255,255,255,0.02);
        }
        .pc-section-header {
          width: 100%;
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 14px 16px;
          background: none;
          border: none;
          color: inherit;
          cursor: pointer;
          font: inherit;
          text-align: left;
        }
        .pc-section-header:hover {
          background: rgba(255,255,255,0.03);
        }
        .pc-section-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: rgba(99,102,241,0.12);
          color: #6366f1;
          flex-shrink: 0;
        }
        .pc-section-title {
          display: block;
          font-size: 14px;
          font-weight: 600;
        }
        .pc-section-sub {
          display: block;
          font-size: 11px;
          opacity: 0.45;
          margin-top: 1px;
        }
        .pc-body {
          padding: 4px 16px 18px;
        }

        /* Cards */
        .pc-card {
          background: rgba(255,255,255,0.04);
          border: 1px solid rgba(255,255,255,0.07);
          border-radius: 8px;
          padding: 14px 16px;
        }

        /* Headings */
        .pc-h4 {
          font-size: 12px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          opacity: 0.5;
          margin: 16px 0 8px;
        }

        /* Bullets */
        .pc-bullets {
          list-style: none;
          padding: 0;
          margin: 0;
        }
        .pc-bullets li {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          padding: 6px 0;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .pc-bullets li:last-child {
          border-bottom: none;
        }
        .pc-bullets code, .pc-card code, .pc-table code {
          background: rgba(99,102,241,0.12);
          padding: 1px 5px;
          border-radius: 4px;
          font-size: 12px;
          color: #a78bfa;
        }

        /* Table */
        .pc-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 13px;
        }
        .pc-table th {
          text-align: left;
          font-weight: 600;
          font-size: 11px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          opacity: 0.5;
          padding: 8px 10px;
          border-bottom: 1px solid rgba(255,255,255,0.08);
        }
        .pc-table td {
          padding: 8px 10px;
          border-bottom: 1px solid rgba(255,255,255,0.04);
        }
        .pc-table-sm td, .pc-table-sm th {
          padding: 6px 8px;
          font-size: 12px;
        }

        /* Toggle switch */
        .pc-toggle {
          position: relative;
          width: 40px;
          height: 22px;
          border-radius: 12px;
          border: none;
          cursor: pointer;
          background: rgba(255,255,255,0.12);
          transition: background .2s;
          flex-shrink: 0;
        }
        .pc-toggle[data-on="true"] {
          background: #6366f1;
        }
        .pc-toggle-knob {
          position: absolute;
          top: 3px;
          left: 3px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          transition: transform .2s;
        }
        .pc-toggle[data-on="true"] .pc-toggle-knob {
          transform: translateX(18px);
        }

        /* Inputs */
        .pc-input {
          width: 100%;
          padding: 8px 32px 8px 10px;
          border: 1px solid rgba(255,255,255,0.10);
          border-radius: 6px;
          background: rgba(0,0,0,0.3);
          color: inherit;
          font-size: 13px;
          outline: none;
          box-sizing: border-box;
        }
        .pc-input:focus {
          border-color: #6366f1;
        }

        /* Buttons */
        .pc-btn {
          display: inline-flex;
          align-items: center;
          gap: 5px;
          padding: 7px 14px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.10);
          background: rgba(255,255,255,0.06);
          color: inherit;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          white-space: nowrap;
        }
        .pc-btn:hover:not(:disabled) {
          background: rgba(255,255,255,0.10);
        }
        .pc-btn:disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }
        .pc-btn-primary {
          background: #6366f1;
          border-color: #6366f1;
          color: #fff;
        }
        .pc-btn-primary:hover:not(:disabled) {
          background: #4f46e5;
        }
        .pc-btn-sm {
          padding: 4px 10px;
          font-size: 11px;
        }

        .pc-icon-btn {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border-radius: 6px;
          border: none;
          background: none;
          color: inherit;
          opacity: 0.5;
          cursor: pointer;
        }
        .pc-icon-btn:hover {
          background: rgba(255,255,255,0.08);
          opacity: 1;
        }
        .pc-icon-btn-danger:hover {
          color: #ef4444;
          background: rgba(239,68,68,0.12);
        }

        /* Warning */
        .pc-warning {
          display: flex;
          align-items: flex-start;
          gap: 8px;
          padding: 10px 14px;
          border-radius: 8px;
          background: rgba(245,158,11,0.08);
          border: 1px solid rgba(245,158,11,0.18);
          font-size: 12px;
          line-height: 1.5;
        }

        /* Assurance banner */
        .pc-assurance {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 14px;
          padding: 10px 14px;
          border-radius: 8px;
          background: rgba(34,197,94,0.06);
          border: 1px solid rgba(34,197,94,0.15);
          font-size: 13px;
          font-weight: 500;
          color: #22c55e;
        }

        /* Stats grid */
        .pc-stat-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 10px;
        }
        .pc-stat-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          padding: 14px 8px;
          border-radius: 8px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
        }
        .pc-stat-value {
          font-size: 18px;
          font-weight: 700;
        }
        .pc-stat-label {
          font-size: 11px;
          opacity: 0.5;
        }

        /* Empty state */
        .pc-empty {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          padding: 24px;
        }

        /* Sync method grid */
        .pc-method-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 8px;
        }
        .pc-method-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 5px;
          padding: 14px 8px;
          border-radius: 8px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.07);
          color: inherit;
          cursor: pointer;
          font: inherit;
          text-align: center;
        }
        .pc-method-card:hover {
          border-color: rgba(99,102,241,0.3);
        }
        .pc-method-card.active {
          border-color: #6366f1;
          background: rgba(99,102,241,0.08);
        }
        .pc-method-label {
          font-size: 12px;
          font-weight: 600;
        }
        .pc-method-desc {
          font-size: 10px;
          opacity: 0.5;
        }

        /* Steps */
        .pc-steps {
          padding-left: 18px;
          margin: 0;
        }
        .pc-steps li {
          font-size: 12px;
          line-height: 1.6;
          padding: 3px 0;
        }
        .pc-steps code {
          background: rgba(99,102,241,0.12);
          padding: 1px 5px;
          border-radius: 4px;
          font-size: 11px;
          color: #a78bfa;
        }

        /* QR placeholder */
        .pc-qr-placeholder {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          padding: 24px;
          border: 2px dashed rgba(255,255,255,0.08);
          border-radius: 8px;
          margin-top: 8px;
        }

        /* Device list */
        .pc-device-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .pc-device-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 10px 14px;
          border-radius: 8px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
        }
        .pc-device-icon {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border-radius: 8px;
          background: rgba(99,102,241,0.10);
          color: #6366f1;
        }

        /* Extension grid */
        .pc-ext-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }
        .pc-ext-card {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          padding: 14px 10px;
          text-align: center;
        }

        /* Format grid */
        .pc-format-grid {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 8px;
        }

        /* Shared notes */
        .pc-shared-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }
        .pc-shared-row {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 14px;
          border-radius: 8px;
          background: rgba(255,255,255,0.03);
          border: 1px solid rgba(255,255,255,0.06);
        }

        /* Select */
        .pc-select {
          padding: 5px 8px;
          border-radius: 6px;
          border: 1px solid rgba(255,255,255,0.10);
          background: rgba(0,0,0,0.3);
          color: inherit;
          font-size: 12px;
          outline: none;
          cursor: pointer;
        }
        .pc-select:focus {
          border-color: #6366f1;
        }

        /* Log row */
        .pc-log-row {
          display: flex;
          gap: 16px;
          font-size: 11px;
          font-family: monospace;
          padding: 4px 0;
          border-bottom: 1px solid rgba(255,255,255,0.04);
          opacity: 0.6;
        }

        /* Responsive */
        @media (max-width: 640px) {
          .pc-wrapper { padding: 16px; }
          .pc-stat-grid { grid-template-columns: repeat(2, 1fr); }
          .pc-method-grid { grid-template-columns: repeat(2, 1fr); }
          .pc-ext-grid { grid-template-columns: 1fr; }
          .pc-format-grid { grid-template-columns: 1fr; }
        }
      `}</style>
    </div>
  );
}
