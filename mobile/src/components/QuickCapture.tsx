/**
 * QuickCapture — floating action button for instant capture.
 * Can be embedded on any screen.
 */
import { useState, useRef } from "react";
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  Modal,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";

import { useStore } from "../store/useStore";
import { extractTier0 } from "../services/tier0";
import { offlineDb } from "../db/offline";
import type { ContextEvent } from "../store/types";

interface Props {
  onCapture?: (event: ContextEvent) => void;
}

export function QuickCapture({ onCapture }: Props) {
  const [visible, setVisible] = useState(false);
  const [text, setText] = useState("");
  const inputRef = useRef<TextInput>(null);
  const addEvent = useStore((s) => s.addEvent);

  async function handleSubmit() {
    const trimmed = text.trim();
    if (!trimmed) return;

    const tier0 = extractTier0(trimmed);

    const event: ContextEvent = {
      id: `quick_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
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

    await offlineDb.insertEvent(event);
    addEvent(event);
    onCapture?.(event);

    setText("");
    setVisible(false);
  }

  return (
    <>
      {/* FAB */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => {
          setVisible(true);
          setTimeout(() => inputRef.current?.focus(), 200);
        }}
      >
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>

      {/* Modal */}
      <Modal
        visible={visible}
        transparent
        animationType="slide"
        onRequestClose={() => setVisible(false)}
      >
        <KeyboardAvoidingView
          style={styles.modalOverlay}
          behavior={Platform.OS === "ios" ? "padding" : undefined}
        >
          <TouchableOpacity
            style={styles.modalBackdrop}
            activeOpacity={1}
            onPress={() => setVisible(false)}
          />
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Quick Capture</Text>
              <TouchableOpacity onPress={() => setVisible(false)}>
                <Ionicons name="close" size={24} color="#71717a" />
              </TouchableOpacity>
            </View>

            <TextInput
              ref={inputRef}
              style={styles.modalInput}
              placeholder="What's on your mind?"
              placeholderTextColor="#52525b"
              value={text}
              onChangeText={setText}
              multiline
              autoFocus
            />

            <TouchableOpacity
              style={[styles.submitBtn, !text.trim() && { opacity: 0.4 }]}
              onPress={handleSubmit}
              disabled={!text.trim()}
            >
              <Ionicons name="arrow-up-circle" size={20} color="#fff" />
              <Text style={styles.submitText}>Capture</Text>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: "absolute",
    right: 20,
    bottom: 20,
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: "#3b82f6",
    alignItems: "center",
    justifyContent: "center",
    elevation: 6,
    shadowColor: "#3b82f6",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  modalOverlay: {
    flex: 1,
    justifyContent: "flex-end",
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "#00000060",
  },
  modalContent: {
    backgroundColor: "#18181b",
    borderTopLeftRadius: 16,
    borderTopRightRadius: 16,
    padding: 16,
    gap: 12,
    minHeight: 200,
  },
  modalHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  modalTitle: {
    color: "#e4e4e7",
    fontSize: 16,
    fontWeight: "600",
  },
  modalInput: {
    backgroundColor: "#0a0a0f",
    borderRadius: 10,
    color: "#e4e4e7",
    fontSize: 15,
    padding: 12,
    minHeight: 80,
    textAlignVertical: "top",
  },
  submitBtn: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    backgroundColor: "#3b82f6",
    paddingVertical: 12,
    borderRadius: 10,
  },
  submitText: {
    color: "#fff",
    fontSize: 15,
    fontWeight: "600",
  },
});
