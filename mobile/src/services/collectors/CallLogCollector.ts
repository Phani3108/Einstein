/**
 * CallLogCollector — reads call history on Android.
 *
 * Android only — requires READ_CALL_LOG permission.
 * iOS: Not available (no API to read call history).
 *
 * Each call becomes a ContextEvent(source='phone', event_type='call').
 */
import { Platform, NativeModules } from "react-native";
import { useStore } from "../../store/useStore";
import { offlineDb } from "../../db/offline";
import type { ContextEvent } from "../../store/types";

interface CallLogEntry {
  id: string;
  name: string | null;
  number: string;
  type: "incoming" | "outgoing" | "missed";
  duration: number; // seconds
  timestamp: number; // epoch ms
}

export async function collectCallLog(): Promise<number> {
  if (Platform.OS !== "android") {
    return 0;
  }

  const { EinsteinCallLog } = NativeModules;
  if (!EinsteinCallLog) {
    console.warn("[CallLogCollector] Native module not linked");
    return 0;
  }

  let entries: CallLogEntry[];
  try {
    entries = await EinsteinCallLog.getRecentCalls(100);
  } catch (err) {
    console.warn("[CallLogCollector] Failed to read call log:", err);
    return 0;
  }

  let ingested = 0;
  for (const call of entries) {
    const eventId = `call_${call.id}_${call.timestamp}`;
    const caller = call.name || call.number;
    const direction = call.type === "outgoing" ? "to" : "from";
    const duration = formatDuration(call.duration);

    const content = `${call.type === "missed" ? "Missed call" : "Phone call"} ${direction} ${caller}${call.duration > 0 ? ` (${duration})` : ""}`;

    const contextEvent: ContextEvent = {
      id: eventId,
      user_id: "",
      source: "phone",
      event_type: "call",
      content,
      timestamp: new Date(call.timestamp).toISOString(),
      structured_data: {
        call_type: call.type,
        phone_number: call.number,
        contact_name: call.name,
        duration_seconds: call.duration,
      },
      extracted_people: call.name ? [call.name] : [],
      topics: [],
      processing_tier: 0,
      synced: false,
    };

    await offlineDb.insertEvent(contextEvent);
    useStore.getState().addEvent(contextEvent);
    ingested++;
  }

  console.log(`[CallLogCollector] Ingested ${ingested} calls`);
  return ingested;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return secs > 0 ? `${mins}m ${secs}s` : `${mins}m`;
}
