/**
 * IntegrationsScreen — manage third-party OAuth integrations on mobile.
 *
 * Lists providers (Gmail, Outlook, Slack, Jira, GitHub, Zoom, Linear),
 * shows connection status, and allows connect/disconnect/sync actions.
 * Connect opens the OAuth URL in the system browser via Linking.openURL.
 */
import { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Linking,
  Switch,
  TextInput,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useStore } from "../src/store/useStore";

// ---- Provider definitions ----

interface ProviderInfo {
  name: string;
  emoji: string;
  color: string;
  description: string;
}

const PROVIDERS: Record<string, ProviderInfo> = {
  gmail:   { name: "Gmail",   emoji: "\u{1F4E7}", color: "#EA4335", description: "Auto-capture emails" },
  outlook: { name: "Outlook", emoji: "\u{1F4E8}", color: "#0078D4", description: "Microsoft email sync" },
  slack:   { name: "Slack",   emoji: "\u{1F4AC}", color: "#4A154B", description: "Channel messages" },
  jira:    { name: "Jira",    emoji: "\u{2705}",  color: "#0052CC", description: "Issue tracking" },
  github:  { name: "GitHub",  emoji: "\u{1F4BB}", color: "#8B949E", description: "PRs, issues, reviews" },
  zoom:    { name: "Zoom",    emoji: "\u{1F4F9}", color: "#2D8CFF", description: "Meeting transcripts" },
  linear:  { name: "Linear",  emoji: "\u{1F3AF}", color: "#5E6AD2", description: "Project tracking" },
};

// ---- Types ----

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

// ---- Helpers ----

function getHeaders(): Record<string, string> {
  const token = useStore.getState().authToken;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function baseUrl(): string {
  return useStore.getState().serverUrl;
}

async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${baseUrl()}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: { ...getHeaders(), ...(options.headers || {}) },
  });

  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`API ${res.status} ${path}: ${body || res.statusText}`);
  }

  return res.json() as Promise<T>;
}

function formatLastSync(iso?: string): string {
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
}

// ---- Component ----

export default function IntegrationsScreen() {
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

  // Load integration statuses on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    apiRequest<IntegrationStatus[]>("/api/v1/integrations")
      .then((data) => {
        if (!cancelled) setIntegrations(data);
      })
      .catch(() => {
        // API not available — show all as disconnected
        if (!cancelled) setIntegrations([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const getStatus = useCallback(
    (provider: string): IntegrationStatus | undefined =>
      integrations.find((i) => i.provider === provider),
    [integrations],
  );

  const refreshStatuses = useCallback(async () => {
    try {
      const data = await apiRequest<IntegrationStatus[]>("/api/v1/integrations");
      setIntegrations(data);
    } catch {
      // Silently ignore refresh failures
    }
  }, []);

  const handleConnect = useCallback(
    async (provider: string) => {
      setConnectingProvider(provider);
      try {
        const result = await apiRequest<{ oauth_url?: string }>(
          "/api/v1/integrations/connect",
          {
            method: "POST",
            body: JSON.stringify({ provider }),
          },
        );
        if (result.oauth_url) {
          await Linking.openURL(result.oauth_url);
        }
        // Refresh statuses after a short delay (OAuth redirect takes time)
        setTimeout(refreshStatuses, 3000);
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        Alert.alert("Connection Failed", `Could not connect ${PROVIDERS[provider]?.name ?? provider}: ${message}`);
      } finally {
        setConnectingProvider(null);
      }
    },
    [refreshStatuses],
  );

  const handleDisconnect = useCallback(
    async (provider: string) => {
      Alert.alert(
        "Disconnect Integration",
        `Are you sure you want to disconnect ${PROVIDERS[provider]?.name ?? provider}?`,
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Disconnect",
            style: "destructive",
            onPress: async () => {
              try {
                await apiRequest(`/api/v1/integrations/${provider}`, {
                  method: "DELETE",
                });
                setIntegrations((prev) =>
                  prev.map((i) =>
                    i.provider === provider
                      ? { ...i, connected: false, last_sync: undefined }
                      : i,
                  ),
                );
              } catch (err) {
                const message = err instanceof Error ? err.message : "Unknown error";
                Alert.alert("Error", `Failed to disconnect: ${message}`);
              }
            },
          },
        ],
      );
    },
    [],
  );

  const handleSync = useCallback(
    async (provider: string) => {
      setSyncingProvider(provider);
      try {
        await apiRequest(`/api/v1/integrations/${provider}/sync`, {
          method: "POST",
        });
        await refreshStatuses();
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unknown error";
        Alert.alert("Sync Failed", message);
      } finally {
        setSyncingProvider(null);
      }
    },
    [refreshStatuses],
  );

  return (
    <ScrollView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.title}>Integrations</Text>
        <Text style={styles.subtitle}>
          Connect your tools to capture context automatically
        </Text>
      </View>

      {/* Loading */}
      {loading ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="small" color="#3b82f6" />
          <Text style={styles.loadingText}>Loading integrations...</Text>
        </View>
      ) : (
        /* Provider list */
        <View style={styles.providerList}>
          {Object.entries(PROVIDERS).map(([key, provider]) => {
            const status = getStatus(key);
            const isConnected = status?.connected ?? false;
            const isConnecting = connectingProvider === key;
            const isSyncing = syncingProvider === key;

            return (
              <View
                key={key}
                style={[
                  styles.card,
                  isConnected && styles.cardConnected,
                ]}
              >
                {/* Top row: icon + info + badge */}
                <View style={styles.cardHeader}>
                  <View
                    style={[
                      styles.iconContainer,
                      { backgroundColor: provider.color + "20" },
                    ]}
                  >
                    <Text style={styles.iconEmoji}>{provider.emoji}</Text>
                  </View>
                  <View style={styles.cardInfo}>
                    <Text style={styles.providerName}>{provider.name}</Text>
                    <Text style={styles.providerDesc}>{provider.description}</Text>
                  </View>
                  <View
                    style={[
                      styles.badge,
                      isConnected ? styles.badgeConnected : styles.badgeDisconnected,
                    ]}
                  >
                    <Text
                      style={[
                        styles.badgeText,
                        isConnected
                          ? styles.badgeTextConnected
                          : styles.badgeTextDisconnected,
                      ]}
                    >
                      {isConnected ? "Connected" : "Not connected"}
                    </Text>
                  </View>
                </View>

                {/* Last sync */}
                {isConnected && status?.last_sync && (
                  <Text style={styles.lastSync}>
                    Synced {formatLastSync(status.last_sync)}
                  </Text>
                )}

                {/* Actions */}
                <View style={styles.cardActions}>
                  {isConnected ? (
                    <>
                      <TouchableOpacity
                        style={styles.btnSync}
                        onPress={() => handleSync(key)}
                        disabled={isSyncing}
                      >
                        {isSyncing ? (
                          <ActivityIndicator size="small" color="#3b82f6" />
                        ) : (
                          <Ionicons name="sync" size={16} color="#3b82f6" />
                        )}
                        <Text style={styles.btnSyncText}>
                          {isSyncing ? "Syncing..." : "Sync"}
                        </Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={styles.btnDisconnect}
                        onPress={() => handleDisconnect(key)}
                      >
                        <Text style={styles.btnDisconnectText}>Disconnect</Text>
                      </TouchableOpacity>
                    </>
                  ) : (
                    <TouchableOpacity
                      style={styles.btnConnect}
                      onPress={() => handleConnect(key)}
                      disabled={isConnecting}
                    >
                      {isConnecting ? (
                        <ActivityIndicator size="small" color="#60a5fa" />
                      ) : (
                        <Ionicons
                          name="open-outline"
                          size={16}
                          color="#60a5fa"
                        />
                      )}
                      <Text style={styles.btnConnectText}>
                        {isConnecting ? "Connecting..." : "Connect"}
                      </Text>
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            );
          })}
        </View>
      )}

      {/* Privacy Controls */}
      <View style={styles.privacySection}>
        <View style={styles.privacySectionHeader}>
          <Ionicons name="shield-checkmark" size={18} color="#e4e4e7" />
          <Text style={styles.privacySectionTitle}>Privacy Controls</Text>
        </View>
        <View style={styles.card}>
          <View style={styles.privacyRow}>
            <Text style={styles.privacyLabel}>
              Sync full email body (not just metadata)
            </Text>
            <Switch
              value={privacy.emailBodySync}
              onValueChange={(val) =>
                setPrivacy((p) => ({ ...p, emailBodySync: val }))
              }
              trackColor={{ false: "#3f3f46", true: "#3b82f680" }}
              thumbColor={privacy.emailBodySync ? "#3b82f6" : "#71717a"}
            />
          </View>

          <View style={styles.privacyRow}>
            <Text style={styles.privacyLabel}>
              Include private repositories (GitHub)
            </Text>
            <Switch
              value={privacy.githubPrivateRepos}
              onValueChange={(val) =>
                setPrivacy((p) => ({ ...p, githubPrivateRepos: val }))
              }
              trackColor={{ false: "#3f3f46", true: "#3b82f680" }}
              thumbColor={privacy.githubPrivateRepos ? "#3b82f6" : "#71717a"}
            />
          </View>

          <View style={styles.privacyRow}>
            <Text style={styles.privacyLabel}>
              Capture meeting transcripts (Zoom)
            </Text>
            <Switch
              value={privacy.meetingTranscripts}
              onValueChange={(val) =>
                setPrivacy((p) => ({ ...p, meetingTranscripts: val }))
              }
              trackColor={{ false: "#3f3f46", true: "#3b82f680" }}
              thumbColor={privacy.meetingTranscripts ? "#3b82f6" : "#71717a"}
            />
          </View>

          <View style={styles.privacyField}>
            <Text style={styles.privacyFieldLabel}>
              Slack channels to sync (comma-separated, empty = all)
            </Text>
            <TextInput
              style={styles.privacyInput}
              value={privacy.slackChannels}
              onChangeText={(val) =>
                setPrivacy((p) => ({ ...p, slackChannels: val }))
              }
              placeholder="#general, #engineering, #design"
              placeholderTextColor="#52525b"
              autoCapitalize="none"
              autoCorrect={false}
            />
          </View>
        </View>
      </View>

      <View style={{ height: 60 }} />
    </ScrollView>
  );
}

// ---- Styles ----

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0f",
    padding: 16,
  },
  header: {
    marginBottom: 20,
  },
  title: {
    color: "#e4e4e7",
    fontSize: 24,
    fontWeight: "700",
  },
  subtitle: {
    color: "#71717a",
    fontSize: 14,
    marginTop: 4,
  },

  // Loading
  loadingContainer: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingVertical: 40,
  },
  loadingText: {
    color: "#71717a",
    fontSize: 13,
  },

  // Provider list
  providerList: {
    gap: 12,
  },

  // Card
  card: {
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: "#27272a",
  },
  cardConnected: {
    borderColor: "#22c55e40",
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: "center",
    justifyContent: "center",
  },
  iconEmoji: {
    fontSize: 20,
  },
  cardInfo: {
    flex: 1,
  },
  providerName: {
    color: "#e4e4e7",
    fontSize: 15,
    fontWeight: "600",
  },
  providerDesc: {
    color: "#71717a",
    fontSize: 12,
    marginTop: 2,
  },

  // Badge
  badge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 10,
  },
  badgeConnected: {
    backgroundColor: "#22c55e20",
  },
  badgeDisconnected: {
    backgroundColor: "#71717a20",
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.3,
  },
  badgeTextConnected: {
    color: "#4ade80",
  },
  badgeTextDisconnected: {
    color: "#a1a1aa",
  },

  // Last sync
  lastSync: {
    color: "#71717a",
    fontSize: 11,
    marginLeft: 52, // align with text after icon
  },

  // Actions
  cardActions: {
    flexDirection: "row",
    gap: 8,
    marginTop: 4,
  },
  btnConnect: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#3b82f620",
    borderWidth: 1,
    borderColor: "#3b82f640",
    flex: 1,
  },
  btnConnectText: {
    color: "#60a5fa",
    fontSize: 14,
    fontWeight: "500",
  },
  btnSync: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#27272a",
    flex: 1,
  },
  btnSyncText: {
    color: "#3b82f6",
    fontSize: 14,
    fontWeight: "500",
  },
  btnDisconnect: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  btnDisconnectText: {
    color: "#f87171",
    fontSize: 14,
    fontWeight: "500",
  },

  // Privacy
  privacySection: {
    marginTop: 24,
  },
  privacySectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 12,
  },
  privacySectionTitle: {
    color: "#e4e4e7",
    fontSize: 15,
    fontWeight: "600",
  },
  privacyRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  privacyLabel: {
    color: "#e4e4e7",
    fontSize: 13,
    flex: 1,
    marginRight: 12,
  },
  privacyField: {
    gap: 6,
  },
  privacyFieldLabel: {
    color: "#71717a",
    fontSize: 12,
  },
  privacyInput: {
    backgroundColor: "#0a0a0f",
    borderRadius: 8,
    color: "#e4e4e7",
    fontSize: 14,
    padding: 10,
    borderWidth: 1,
    borderColor: "#27272a",
  },
});
