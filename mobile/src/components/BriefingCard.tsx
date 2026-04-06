/**
 * BriefingCard — displays the morning briefing on the home screen.
 */
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { BriefingData } from "../store/types";

interface Props {
  data: BriefingData;
}

export function BriefingCard({ data }: Props) {
  const hasAttention =
    data.attention_items.length > 0 ||
    data.overdue_commitments.length > 0 ||
    data.stale_people.length > 0;

  return (
    <View style={styles.card}>
      <View style={styles.header}>
        <Ionicons name="sunny" size={20} color="#f59e0b" />
        <Text style={styles.title}>Today's Briefing</Text>
        <Text style={styles.date}>{formatDate(data.date)}</Text>
      </View>

      {/* Summary */}
      {data.summary ? (
        <Text style={styles.summary}>{data.summary}</Text>
      ) : (
        <Text style={styles.summaryEmpty}>No briefing available</Text>
      )}

      {/* Stats row */}
      <View style={styles.statsRow}>
        <View style={styles.stat}>
          <Text style={styles.statNumber}>{data.today_event_count}</Text>
          <Text style={styles.statLabel}>events</Text>
        </View>
        <View style={styles.stat}>
          <Text style={[styles.statNumber, data.overdue_commitments.length > 0 && { color: "#ef4444" }]}>
            {data.overdue_commitments.length}
          </Text>
          <Text style={styles.statLabel}>overdue</Text>
        </View>
        <View style={styles.stat}>
          <Text style={[styles.statNumber, data.stale_people.length > 0 && { color: "#f59e0b" }]}>
            {data.stale_people.length}
          </Text>
          <Text style={styles.statLabel}>fading</Text>
        </View>
      </View>

      {/* Attention items */}
      {hasAttention && (
        <View style={styles.attention}>
          <Text style={styles.attentionTitle}>
            <Ionicons name="alert-circle" size={14} color="#ef4444" /> Needs Attention
          </Text>
          {data.attention_items.map((item, i) => (
            <View key={i} style={styles.attentionItem}>
              <View style={styles.dot} />
              <Text style={styles.attentionText}>{item}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
}

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString(undefined, {
      weekday: "long",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    gap: 12,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  title: {
    color: "#e4e4e7",
    fontSize: 16,
    fontWeight: "600",
    flex: 1,
  },
  date: {
    color: "#52525b",
    fontSize: 12,
  },
  summary: {
    color: "#a1a1aa",
    fontSize: 14,
    lineHeight: 20,
  },
  summaryEmpty: {
    color: "#52525b",
    fontSize: 14,
    fontStyle: "italic",
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-around",
    paddingVertical: 8,
    borderTopWidth: 1,
    borderTopColor: "#27272a",
  },
  stat: {
    alignItems: "center",
    gap: 2,
  },
  statNumber: {
    color: "#e4e4e7",
    fontSize: 20,
    fontWeight: "700",
  },
  statLabel: {
    color: "#52525b",
    fontSize: 11,
    textTransform: "uppercase",
  },
  attention: {
    backgroundColor: "#ef444410",
    borderRadius: 8,
    padding: 12,
    gap: 6,
  },
  attentionTitle: {
    color: "#ef4444",
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 4,
  },
  attentionItem: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 8,
  },
  dot: {
    width: 5,
    height: 5,
    borderRadius: 3,
    backgroundColor: "#ef4444",
    marginTop: 6,
  },
  attentionText: {
    color: "#fca5a5",
    fontSize: 13,
    flex: 1,
    lineHeight: 18,
  },
});
