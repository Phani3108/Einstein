/**
 * InboxScreen — zero-friction capture.
 *
 * - Single-tap text capture (no title, no folder, just type)
 * - Voice input via speech-to-text
 * - Triage view for unprocessed items
 * - Everything lands as ContextEvent(source='manual_note')
 */
import { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  FlatList,
  Alert,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as Crypto from "expo-crypto";

import { useStore } from "../src/store/useStore";
import { extractTier0 } from "../src/services/tier0";
import { offlineDb } from "../src/db/offline";
import { EventCard } from "../src/components/EventCard";
import type { ContextEvent } from "../src/store/types";

export default function InboxScreen() {
  const { events, addEvent } = useStore();
  const [text, setText] = useState("");
  const [showTriage, setShowTriage] = useState(false);
  const inputRef = useRef<TextInput>(null);

  // Unprocessed = events from manual_note that haven't been synced
  const unprocessed = events
    .filter((e) => e.source === "manual_note" && !e.synced)
    .sort((a, b) => b.timestamp.localeCompare(a.timestamp));

  async function handleCapture() {
    const trimmed = text.trim();
    if (!trimmed) return;

    // Run Tier 0 extraction
    const tier0 = extractTier0(trimmed);

    const event: ContextEvent = {
      id: `note_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      user_id: "",
      source: "manual_note",
      event_type: "note",
      content: trimmed,
      timestamp: new Date().toISOString(),
      structured_data: { ...tier0 },
      extracted_people: tier0.extracted_people,
      topics: [],
      processing_tier: 0,
      synced: false,
    };

    // Save to offline DB + store
    await offlineDb.insertEvent(event);
    addEvent(event);

    setText("");
    inputRef.current?.focus();

    // Show what was extracted
    if (tier0.extracted_people.length > 0) {
      Alert.alert(
        "Captured",
        `People detected: ${tier0.extracted_people.join(", ")}`,
        [{ text: "OK" }],
        { cancelable: true }
      );
    }
  }

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
      keyboardVerticalOffset={88}
    >
      {/* Toggle: Capture vs Triage */}
      <View style={styles.toggleBar}>
        <TouchableOpacity
          style={[styles.toggleBtn, !showTriage && styles.toggleActive]}
          onPress={() => setShowTriage(false)}
        >
          <Ionicons name="create" size={16} color={!showTriage ? "#3b82f6" : "#71717a"} />
          <Text style={[styles.toggleLabel, !showTriage && styles.toggleLabelActive]}>
            Capture
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.toggleBtn, showTriage && styles.toggleActive]}
          onPress={() => setShowTriage(true)}
        >
          <Ionicons name="list" size={16} color={showTriage ? "#3b82f6" : "#71717a"} />
          <Text style={[styles.toggleLabel, showTriage && styles.toggleLabelActive]}>
            Triage ({unprocessed.length})
          </Text>
        </TouchableOpacity>
      </View>

      {showTriage ? (
        /* ---- Triage View ---- */
        <FlatList
          data={unprocessed}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => <EventCard event={item} />}
          ListEmptyComponent={
            <View style={styles.empty}>
              <Ionicons name="checkmark-circle" size={48} color="#10b981" />
              <Text style={styles.emptyText}>All caught up!</Text>
            </View>
          }
          contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 40 }}
        />
      ) : (
        /* ---- Capture View ---- */
        <View style={styles.captureArea}>
          <View style={styles.inputWrapper}>
            <TextInput
              ref={inputRef}
              style={styles.textInput}
              placeholder="What's on your mind?"
              placeholderTextColor="#52525b"
              value={text}
              onChangeText={setText}
              multiline
              autoFocus
              textAlignVertical="top"
            />
          </View>

          {/* Extraction preview */}
          {text.length > 5 && (
            <ExtractionPreview text={text} />
          )}

          <View style={styles.captureActions}>
            <TouchableOpacity
              style={[styles.captureBtn, !text.trim() && styles.captureBtnDisabled]}
              onPress={handleCapture}
              disabled={!text.trim()}
            >
              <Ionicons name="arrow-up-circle" size={24} color="#fff" />
              <Text style={styles.captureBtnText}>Capture</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

/** Live preview of Tier 0 extraction as user types */
function ExtractionPreview({ text }: { text: string }) {
  const tier0 = extractTier0(text);
  const hasSomething =
    tier0.extracted_people.length > 0 ||
    tier0.dates.length > 0 ||
    tier0.amounts.length > 0;

  if (!hasSomething) return null;

  return (
    <View style={styles.preview}>
      {tier0.extracted_people.length > 0 && (
        <View style={styles.previewRow}>
          <Ionicons name="person" size={14} color="#3b82f6" />
          <Text style={styles.previewText}>
            {tier0.extracted_people.join(", ")}
          </Text>
        </View>
      )}
      {tier0.dates.length > 0 && (
        <View style={styles.previewRow}>
          <Ionicons name="calendar" size={14} color="#10b981" />
          <Text style={styles.previewText}>{tier0.dates.join(", ")}</Text>
        </View>
      )}
      {tier0.amounts.length > 0 && (
        <View style={styles.previewRow}>
          <Ionicons name="cash" size={14} color="#f59e0b" />
          <Text style={styles.previewText}>{tier0.amounts.join(", ")}</Text>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0a0a0f",
  },
  toggleBar: {
    flexDirection: "row",
    margin: 16,
    marginBottom: 8,
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 4,
  },
  toggleBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: 6,
  },
  toggleActive: {
    backgroundColor: "#27272a",
  },
  toggleLabel: {
    color: "#71717a",
    fontSize: 14,
    fontWeight: "500",
  },
  toggleLabelActive: {
    color: "#3b82f6",
  },
  captureArea: {
    flex: 1,
    padding: 16,
  },
  inputWrapper: {
    flex: 1,
    backgroundColor: "#18181b",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
  },
  textInput: {
    flex: 1,
    color: "#e4e4e7",
    fontSize: 16,
    lineHeight: 24,
  },
  preview: {
    backgroundColor: "#18181b",
    borderRadius: 8,
    padding: 12,
    marginBottom: 12,
    gap: 6,
  },
  previewRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  previewText: {
    color: "#a1a1aa",
    fontSize: 13,
  },
  captureActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  captureBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "#3b82f6",
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
  },
  captureBtnDisabled: {
    opacity: 0.4,
  },
  captureBtnText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
  empty: {
    alignItems: "center",
    paddingTop: 80,
    gap: 12,
  },
  emptyText: {
    color: "#71717a",
    fontSize: 16,
    fontWeight: "600",
  },
});
