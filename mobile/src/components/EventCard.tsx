/**
 * EventCard — displays a single context event in timeline/inbox views.
 */
import { View, Text, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { ContextEvent } from "../store/types";

const SOURCE_CONFIG: Record<
  string,
  { icon: string; color: string; label: string }
> = {
  notification: { icon: "notifications", color: "#8b5cf6", label: "Notification" },
  calendar: { icon: "calendar", color: "#3b82f6", label: "Calendar" },
  phone: { icon: "call", color: "#10b981", label: "Phone" },
  manual_note: { icon: "create", color: "#f59e0b", label: "Note" },
  email: { icon: "mail", color: "#ec4899", label: "Email" },
  contacts: { icon: "person", color: "#06b6d4", label: "Contact" },
  sms: { icon: "chatbubble", color: "#14b8a6", label: "SMS" },
};

interface Props {
  event: ContextEvent;
  compact?: boolean;
}

export function EventCard({ event, compact = false }: Props) {
  const config = SOURCE_CONFIG[event.source] ?? {
    icon: "document",
    color: "#71717a",
    label: event.source,
  };

  const time = formatTime(event.timestamp);
  const content = event.content || "(no content)";
  const people = event.extracted_people;

  return (
    <View style={[styles.card, compact && styles.cardCompact]}>
      {/* Source icon */}
      <View style={[styles.iconWrap, { backgroundColor: config.color + "20" }]}>
        <Ionicons name={config.icon as any} size={16} color={config.color} />
      </View>

      {/* Content */}
      <View style={styles.content}>
        <View style={styles.topRow}>
          <Text style={styles.source}>{config.label}</Text>
          <Text style={styles.time}>{time}</Text>
          {!event.synced && (
            <View style={styles.unsyncedDot} />
          )}
        </View>

        <Text style={styles.text} numberOfLines={compact ? 2 : 4}>
          {content}
        </Text>

        {/* Extracted people */}
        {people.length > 0 && (
          <View style={styles.tags}>
            {people.map((name) => (
              <View key={name} style={styles.tag}>
                <Ionicons name="person" size={10} color="#3b82f6" />
                <Text style={styles.tagText}>{name}</Text>
              </View>
            ))}
          </View>
        )}
      </View>
    </View>
  );
}

function formatTime(timestamp: string): string {
  const d = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - d.getTime();

  if (diff < 60_000) return "now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;

  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    backgroundColor: "#18181b",
    borderRadius: 10,
    padding: 12,
    marginHorizontal: 16,
    marginBottom: 8,
    gap: 10,
  },
  cardCompact: {
    padding: 8,
    marginHorizontal: 0,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  content: {
    flex: 1,
    gap: 4,
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  source: {
    color: "#71717a",
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.3,
  },
  time: {
    color: "#52525b",
    fontSize: 11,
    marginLeft: "auto",
  },
  unsyncedDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: "#f59e0b",
  },
  text: {
    color: "#e4e4e7",
    fontSize: 14,
    lineHeight: 20,
  },
  tags: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 4,
    marginTop: 4,
  },
  tag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    backgroundColor: "#3b82f612",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 10,
  },
  tagText: {
    color: "#3b82f6",
    fontSize: 11,
  },
});
