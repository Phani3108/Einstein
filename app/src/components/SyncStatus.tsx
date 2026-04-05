import { useSyncState } from "../lib/sync";
import type { SyncStatus as SyncStatusType } from "../lib/sync";
import { Cloud, CloudOff, RefreshCw, Check, AlertCircle } from "lucide-react";

const STATUS_CONFIG: Record<SyncStatusType, { icon: React.ReactNode; label: string; color: string }> = {
  idle: { icon: <Cloud size={11} />, label: "Ready", color: "var(--text-tertiary)" },
  syncing: { icon: <RefreshCw size={11} className="loading-spinner" />, label: "Syncing...", color: "var(--accent)" },
  synced: { icon: <Check size={11} />, label: "Synced", color: "#22c55e" },
  error: { icon: <AlertCircle size={11} />, label: "Error", color: "#ef4444" },
  offline: { icon: <CloudOff size={11} />, label: "Offline", color: "var(--text-tertiary)" },
};

export function SyncStatusBadge() {
  const syncState = useSyncState();
  const config = STATUS_CONFIG[syncState.status];

  return (
    <div
      className="status-item sync-badge"
      title={
        syncState.lastSynced
          ? `Last synced: ${syncState.lastSynced.toLocaleTimeString()}`
          : "Not yet synced"
      }
      style={{ color: config.color }}
    >
      {config.icon}
      <span>{config.label}</span>
      {syncState.connectedPeers > 0 && (
        <span className="sync-peers">{syncState.connectedPeers}</span>
      )}
    </div>
  );
}
