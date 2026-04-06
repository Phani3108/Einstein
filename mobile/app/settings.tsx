/**
 * SettingsScreen — server config, sync status, notification permissions.
 */
import { useState, useEffect } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
  Alert,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useStore } from "../src/store/useStore";
import { syncNow, registerBackgroundSync, unregisterBackgroundSync } from "../src/services/sync";
import { collectContacts } from "../src/services/collectors/ContactsCollector";
import { collectCalendarEvents } from "../src/services/collectors/CalendarCollector";
import { collectCallLog } from "../src/services/collectors/CallLogCollector";
import {
  isPermissionGranted,
  openPermissionSettings,
} from "../src/services/collectors/NotificationCollector";
import * as api from "../src/services/api";
import { offlineDb } from "../src/db/offline";

export default function SettingsScreen() {
  const { serverUrl, setServerUrl, authToken, setAuthToken, sync } = useStore();
  const [urlDraft, setUrlDraft] = useState(serverUrl);
  const [tokenDraft, setTokenDraft] = useState(authToken ?? "");
  const [notifPermission, setNotifPermission] = useState(false);
  const [offlineCount, setOfflineCount] = useState(0);

  useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    if (Platform.OS === "android") {
      const granted = await isPermissionGranted();
      setNotifPermission(granted);
    }
    const count = await offlineDb.count();
    setOfflineCount(count);
  }

  async function handleSaveConnection() {
    setServerUrl(urlDraft);
    setAuthToken(tokenDraft || null);

    const healthy = await api.healthCheck();
    Alert.alert(
      healthy ? "Connected" : "Connection Failed",
      healthy
        ? `Connected to ${urlDraft}`
        : "Could not reach the server. Check the URL.",
    );
  }

  async function handleSyncNow() {
    const result = await syncNow();
    Alert.alert(
      "Sync Complete",
      `Uploaded: ${result.uploaded}\nDownloaded: ${result.downloaded}${result.error ? `\nError: ${result.error}` : ""}`,
    );
    checkStatus();
  }

  async function handleCollectAll() {
    const [contacts, calendar, calls] = await Promise.all([
      collectContacts(),
      collectCalendarEvents(),
      collectCallLog(),
    ]);
    Alert.alert(
      "Collection Complete",
      `Contacts: ${contacts}\nCalendar events: ${calendar}\nCall logs: ${calls}`,
    );
    checkStatus();
  }

  async function handlePrune() {
    const pruned = await offlineDb.pruneOld();
    Alert.alert("Cleanup", `Removed ${pruned} old synced events`);
    checkStatus();
  }

  return (
    <ScrollView style={styles.container}>
      {/* Server Connection */}
      <Text style={styles.sectionTitle}>Server Connection</Text>
      <View style={styles.card}>
        <View style={styles.inputRow}>
          <Text style={styles.label}>Server URL</Text>
          <TextInput
            style={styles.input}
            value={urlDraft}
            onChangeText={setUrlDraft}
            placeholder="http://localhost:8000"
            placeholderTextColor="#52525b"
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
        <View style={styles.inputRow}>
          <Text style={styles.label}>Auth Token</Text>
          <TextInput
            style={styles.input}
            value={tokenDraft}
            onChangeText={setTokenDraft}
            placeholder="JWT token"
            placeholderTextColor="#52525b"
            autoCapitalize="none"
            secureTextEntry
          />
        </View>
        <TouchableOpacity style={styles.btn} onPress={handleSaveConnection}>
          <Ionicons name="checkmark-circle" size={18} color="#3b82f6" />
          <Text style={styles.btnText}>Save & Test</Text>
        </TouchableOpacity>
      </View>

      {/* Sync */}
      <Text style={styles.sectionTitle}>Sync</Text>
      <View style={styles.card}>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Last sync</Text>
          <Text style={styles.infoValue}>
            {sync.lastSyncAt
              ? new Date(sync.lastSyncAt).toLocaleTimeString()
              : "Never"}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Pending upload</Text>
          <Text style={[styles.infoValue, sync.pendingCount > 0 && { color: "#f59e0b" }]}>
            {sync.pendingCount}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoLabel}>Offline events</Text>
          <Text style={styles.infoValue}>{offlineCount}</Text>
        </View>
        {sync.error && (
          <Text style={styles.errorText}>{sync.error}</Text>
        )}
        <View style={styles.btnRow}>
          <TouchableOpacity style={styles.btn} onPress={handleSyncNow}>
            <Ionicons name="cloud-upload" size={18} color="#3b82f6" />
            <Text style={styles.btnText}>Sync Now</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.btn} onPress={handlePrune}>
            <Ionicons name="trash" size={18} color="#71717a" />
            <Text style={[styles.btnText, { color: "#71717a" }]}>Cleanup</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Data Collection */}
      <Text style={styles.sectionTitle}>Data Collection</Text>
      <View style={styles.card}>
        {Platform.OS === "android" && (
          <View style={styles.infoRow}>
            <Text style={styles.infoLabel}>Notification access</Text>
            <TouchableOpacity onPress={openPermissionSettings}>
              <Text style={[styles.infoValue, { color: notifPermission ? "#10b981" : "#ef4444" }]}>
                {notifPermission ? "Granted" : "Not granted — tap to enable"}
              </Text>
            </TouchableOpacity>
          </View>
        )}
        <TouchableOpacity style={styles.btn} onPress={handleCollectAll}>
          <Ionicons name="download" size={18} color="#3b82f6" />
          <Text style={styles.btnText}>Collect All Sources</Text>
        </TouchableOpacity>
      </View>

      <View style={{ height: 60 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0f",
    padding: 16,
  },
  sectionTitle: {
    color: "#71717a",
    fontSize: 13,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 16,
    marginBottom: 8,
  },
  card: {
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 16,
    gap: 12,
    marginBottom: 8,
  },
  inputRow: {
    gap: 4,
  },
  label: {
    color: "#71717a",
    fontSize: 12,
    fontWeight: "500",
  },
  input: {
    backgroundColor: "#0a0a0f",
    borderRadius: 8,
    color: "#e4e4e7",
    fontSize: 14,
    padding: 10,
    borderWidth: 1,
    borderColor: "#27272a",
  },
  infoRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  infoLabel: {
    color: "#71717a",
    fontSize: 14,
  },
  infoValue: {
    color: "#e4e4e7",
    fontSize: 14,
  },
  errorText: {
    color: "#ef4444",
    fontSize: 12,
  },
  btnRow: {
    flexDirection: "row",
    gap: 8,
  },
  btn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
    backgroundColor: "#27272a",
    flex: 1,
  },
  btnText: {
    color: "#3b82f6",
    fontSize: 14,
    fontWeight: "500",
  },
});
