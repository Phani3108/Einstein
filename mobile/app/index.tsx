/**
 * HomeScreen — dashboard with morning briefing + quick actions.
 */
import { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  ActivityIndicator,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";

import { useStore } from "../src/store/useStore";
import { syncNow } from "../src/services/sync";
import * as api from "../src/services/api";
import { BriefingCard } from "../src/components/BriefingCard";
import { EventCard } from "../src/components/EventCard";

export default function HomeScreen() {
  const router = useRouter();
  const {
    briefing,
    setBriefing,
    events,
    sync,
    people,
    commitments,
  } = useStore();

  const [refreshing, setRefreshing] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const briefingData = await api.getMorningBriefing();
      setBriefing(briefingData);
    } catch {
      // Offline — use cached
    }
    setLoading(false);
  }

  async function onRefresh() {
    setRefreshing(true);
    await syncNow();
    await loadData();
    setRefreshing(false);
  }

  const recentEvents = [...events]
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp))
    .slice(0, 5);

  const overdueCount = commitments.filter((c) => c.status === "overdue").length;
  const pendingSync = sync.pendingCount;

  return (
    <ScrollView
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#3b82f6"
        />
      }
    >
      {/* Status bar */}
      <View style={styles.statusBar}>
        <View style={styles.statusItem}>
          <Ionicons name="people" size={16} color="#71717a" />
          <Text style={styles.statusText}>{people.length} people</Text>
        </View>
        <View style={styles.statusItem}>
          <Ionicons
            name="cloud-upload"
            size={16}
            color={pendingSync > 0 ? "#f59e0b" : "#10b981"}
          />
          <Text style={styles.statusText}>
            {pendingSync > 0 ? `${pendingSync} pending` : "Synced"}
          </Text>
        </View>
        {overdueCount > 0 && (
          <View style={styles.statusItem}>
            <Ionicons name="alert-circle" size={16} color="#ef4444" />
            <Text style={[styles.statusText, { color: "#ef4444" }]}>
              {overdueCount} overdue
            </Text>
          </View>
        )}
      </View>

      {/* Briefing */}
      {loading ? (
        <View style={styles.loadingCard}>
          <ActivityIndicator color="#3b82f6" />
          <Text style={styles.loadingText}>Loading briefing...</Text>
        </View>
      ) : briefing ? (
        <BriefingCard data={briefing} />
      ) : (
        <View style={styles.emptyCard}>
          <Ionicons name="sunny" size={32} color="#71717a" />
          <Text style={styles.emptyText}>No briefing yet today</Text>
          <Text style={styles.emptySubtext}>
            Capture some context to get started
          </Text>
        </View>
      )}

      {/* Quick Actions */}
      <View style={styles.quickActions}>
        <TouchableOpacity
          style={styles.quickBtn}
          onPress={() => router.push("/inbox")}
        >
          <Ionicons name="add-circle" size={24} color="#3b82f6" />
          <Text style={styles.quickLabel}>Capture</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.quickBtn}
          onPress={() => router.push("/timeline")}
        >
          <Ionicons name="time" size={24} color="#3b82f6" />
          <Text style={styles.quickLabel}>Timeline</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={styles.quickBtn}
          onPress={() => router.push("/people")}
        >
          <Ionicons name="people" size={24} color="#3b82f6" />
          <Text style={styles.quickLabel}>People</Text>
        </TouchableOpacity>
      </View>

      {/* Recent Activity */}
      <Text style={styles.sectionTitle}>Recent Activity</Text>
      {recentEvents.length > 0 ? (
        recentEvents.map((event) => (
          <EventCard key={event.id} event={event} />
        ))
      ) : (
        <Text style={styles.emptySection}>
          No events yet. Start capturing!
        </Text>
      )}

      <View style={{ height: 40 }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0f",
    padding: 16,
  },
  statusBar: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 12,
    marginBottom: 16,
    borderRadius: 8,
    backgroundColor: "#18181b",
  },
  statusItem: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  statusText: {
    color: "#71717a",
    fontSize: 13,
  },
  loadingCard: {
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 32,
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
  },
  loadingText: {
    color: "#71717a",
    fontSize: 13,
  },
  emptyCard: {
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 32,
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
  },
  emptyText: {
    color: "#e4e4e7",
    fontSize: 16,
    fontWeight: "600",
  },
  emptySubtext: {
    color: "#71717a",
    fontSize: 13,
  },
  quickActions: {
    flexDirection: "row",
    justifyContent: "space-around",
    marginBottom: 24,
  },
  quickBtn: {
    alignItems: "center",
    gap: 4,
    padding: 12,
  },
  quickLabel: {
    color: "#e4e4e7",
    fontSize: 12,
  },
  sectionTitle: {
    color: "#71717a",
    fontSize: 13,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  emptySection: {
    color: "#52525b",
    fontSize: 14,
    fontStyle: "italic",
    textAlign: "center",
    paddingVertical: 24,
  },
});
