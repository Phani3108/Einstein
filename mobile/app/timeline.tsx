/**
 * TimelineScreen — chronological feed of all context events.
 *
 * Grouped by date, filterable by source, searchable.
 */
import { useState, useMemo } from "react";
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TextInput,
  TouchableOpacity,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useStore } from "../src/store/useStore";
import { EventCard } from "../src/components/EventCard";
import type { ContextEvent, EventSource } from "../src/store/types";

const SOURCE_FILTERS: { key: EventSource | "all"; label: string; icon: string }[] = [
  { key: "all", label: "All", icon: "apps" },
  { key: "notification", label: "Notifs", icon: "notifications" },
  { key: "calendar", label: "Calendar", icon: "calendar" },
  { key: "phone", label: "Calls", icon: "call" },
  { key: "manual_note", label: "Notes", icon: "create" },
];

export default function TimelineScreen() {
  const events = useStore((s) => s.events);
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<EventSource | "all">("all");

  const filtered = useMemo(() => {
    let result = [...events].sort((a, b) =>
      b.timestamp.localeCompare(a.timestamp)
    );

    if (sourceFilter !== "all") {
      result = result.filter((e) => e.source === sourceFilter);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (e) =>
          (e.content || "").toLowerCase().includes(q) ||
          e.extracted_people.some((p) => p.toLowerCase().includes(q)) ||
          e.source.includes(q)
      );
    }

    return result;
  }, [events, sourceFilter, search]);

  // Group by date
  const grouped = useMemo(() => {
    const groups: { date: string; events: ContextEvent[] }[] = [];
    let currentDate = "";

    for (const event of filtered) {
      const date = event.timestamp.slice(0, 10);
      if (date !== currentDate) {
        currentDate = date;
        groups.push({ date, events: [] });
      }
      groups[groups.length - 1].events.push(event);
    }

    return groups;
  }, [filtered]);

  return (
    <View style={styles.container}>
      {/* Search */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color="#71717a" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search events..."
          placeholderTextColor="#52525b"
          value={search}
          onChangeText={setSearch}
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={() => setSearch("")}>
            <Ionicons name="close-circle" size={18} color="#71717a" />
          </TouchableOpacity>
        )}
      </View>

      {/* Source Filters */}
      <View style={styles.filters}>
        {SOURCE_FILTERS.map((f) => (
          <TouchableOpacity
            key={f.key}
            style={[
              styles.filterChip,
              sourceFilter === f.key && styles.filterChipActive,
            ]}
            onPress={() => setSourceFilter(f.key)}
          >
            <Ionicons
              name={f.icon as any}
              size={14}
              color={sourceFilter === f.key ? "#3b82f6" : "#71717a"}
            />
            <Text
              style={[
                styles.filterLabel,
                sourceFilter === f.key && styles.filterLabelActive,
              ]}
            >
              {f.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Timeline */}
      <FlatList
        data={grouped}
        keyExtractor={(item) => item.date}
        renderItem={({ item }) => (
          <View>
            <Text style={styles.dateHeader}>{formatDateHeader(item.date)}</Text>
            {item.events.map((event) => (
              <EventCard key={event.id} event={event} />
            ))}
          </View>
        )}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="time-outline" size={48} color="#27272a" />
            <Text style={styles.emptyText}>No events found</Text>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 40 }}
      />
    </View>
  );
}

function formatDateHeader(isoDate: string): string {
  const date = new Date(isoDate);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);

  if (isoDate === today.toISOString().slice(0, 10)) return "Today";
  if (isoDate === yesterday.toISOString().slice(0, 10)) return "Yesterday";

  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0f",
  },
  searchBar: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#18181b",
    borderRadius: 8,
    margin: 16,
    marginBottom: 8,
    paddingHorizontal: 12,
    gap: 8,
  },
  searchInput: {
    flex: 1,
    color: "#e4e4e7",
    fontSize: 15,
    paddingVertical: 10,
  },
  filters: {
    flexDirection: "row",
    paddingHorizontal: 16,
    gap: 8,
    marginBottom: 12,
  },
  filterChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: "#18181b",
  },
  filterChipActive: {
    backgroundColor: "#3b82f618",
    borderWidth: 1,
    borderColor: "#3b82f640",
  },
  filterLabel: {
    color: "#71717a",
    fontSize: 12,
  },
  filterLabelActive: {
    color: "#3b82f6",
  },
  dateHeader: {
    color: "#71717a",
    fontSize: 13,
    fontWeight: "600",
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
  },
  empty: {
    alignItems: "center",
    paddingTop: 80,
    gap: 12,
  },
  emptyText: {
    color: "#52525b",
    fontSize: 15,
  },
});
