/**
 * PeopleScreen — first-class people view with relationship strength.
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
import { ConnectionBadge } from "../src/components/ConnectionBadge";
import type { Person } from "../src/store/types";

export default function PeopleScreen() {
  const people = useStore((s) => s.people);
  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    let result = [...people].sort(
      (a, b) => b.freshness_score - a.freshness_score
    );

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.role || "").toLowerCase().includes(q) ||
          (p.organization || "").toLowerCase().includes(q)
      );
    }

    return result;
  }, [people, search]);

  const renderPerson = ({ item }: { item: Person }) => {
    const initials = item.name
      .split(" ")
      .map((w) => w[0])
      .join("")
      .slice(0, 2)
      .toUpperCase();

    return (
      <TouchableOpacity style={styles.personCard}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials}</Text>
        </View>
        <View style={styles.personInfo}>
          <Text style={styles.personName}>{item.name}</Text>
          <View style={styles.personMeta}>
            {item.role && (
              <Text style={styles.metaText}>{item.role}</Text>
            )}
            {item.organization && (
              <Text style={styles.metaText}>{item.organization}</Text>
            )}
          </View>
          <View style={styles.personStats}>
            <ConnectionBadge
              score={item.freshness_score}
              label={
                item.freshness_score > 0.7
                  ? "Active"
                  : item.freshness_score > 0.3
                  ? "Moderate"
                  : "Fading"
              }
            />
            <Text style={styles.interactionCount}>
              {item.interaction_count} interactions
            </Text>
          </View>
        </View>
        <Ionicons name="chevron-forward" size={18} color="#27272a" />
      </TouchableOpacity>
    );
  };

  return (
    <View style={styles.container}>
      {/* Search */}
      <View style={styles.searchBar}>
        <Ionicons name="search" size={18} color="#71717a" />
        <TextInput
          style={styles.searchInput}
          placeholder="Search people..."
          placeholderTextColor="#52525b"
          value={search}
          onChangeText={setSearch}
        />
      </View>

      {/* Stats */}
      <View style={styles.statsRow}>
        <Text style={styles.statsText}>{people.length} people tracked</Text>
        <Text style={styles.statsText}>
          {people.filter((p) => p.freshness_score < 0.3).length} fading
        </Text>
      </View>

      {/* List */}
      <FlatList
        data={filtered}
        keyExtractor={(item) => item.id}
        renderItem={renderPerson}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="people-outline" size={48} color="#27272a" />
            <Text style={styles.emptyText}>No people yet</Text>
            <Text style={styles.emptySubtext}>
              Sync your contacts or capture context to build your network
            </Text>
          </View>
        }
        contentContainerStyle={{ paddingBottom: 40 }}
      />
    </View>
  );
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
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  statsText: {
    color: "#52525b",
    fontSize: 12,
  },
  personCard: {
    flexDirection: "row",
    alignItems: "center",
    padding: 12,
    marginHorizontal: 16,
    marginBottom: 8,
    backgroundColor: "#18181b",
    borderRadius: 10,
    gap: 12,
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#3b82f6",
    alignItems: "center",
    justifyContent: "center",
  },
  avatarText: {
    color: "#fff",
    fontSize: 16,
    fontWeight: "600",
  },
  personInfo: {
    flex: 1,
    gap: 2,
  },
  personName: {
    color: "#e4e4e7",
    fontSize: 15,
    fontWeight: "600",
  },
  personMeta: {
    flexDirection: "row",
    gap: 8,
  },
  metaText: {
    color: "#71717a",
    fontSize: 12,
  },
  personStats: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  interactionCount: {
    color: "#52525b",
    fontSize: 11,
  },
  empty: {
    alignItems: "center",
    paddingTop: 80,
    gap: 8,
  },
  emptyText: {
    color: "#71717a",
    fontSize: 16,
    fontWeight: "600",
  },
  emptySubtext: {
    color: "#52525b",
    fontSize: 13,
    textAlign: "center",
    paddingHorizontal: 40,
  },
});
