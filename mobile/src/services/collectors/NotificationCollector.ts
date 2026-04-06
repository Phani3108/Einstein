/**
 * NotificationCollector — captures incoming notifications on Android.
 *
 * Android: Uses a native NotificationListenerService (Kotlin module).
 * iOS: Not supported — iOS does not expose notification content to third-party apps.
 *
 * The collector listens for a custom event from the native module,
 * runs Tier 0 extraction, and queues the event for sync.
 */
import { Platform, NativeModules, NativeEventEmitter } from "react-native";
import { useStore } from "../../store/useStore";
import { extractTier0 } from "../tier0";
import { offlineDb } from "../../db/offline";
import type { ContextEvent } from "../../store/types";

// ---- Config ----

/** Apps to NEVER capture (system noise) */
const DEFAULT_BLOCKLIST = new Set([
  "com.android.systemui",
  "com.android.providers.downloads",
  "com.android.vending", // Play Store
  "com.google.android.packageinstaller",
]);

/** If set, ONLY capture these apps. Empty = capture all (minus blocklist). */
let allowlist: Set<string> = new Set();

// ---- Native bridge ----

interface NotificationPayload {
  packageName: string;
  appName: string;
  title: string;
  text: string;
  timestamp: number; // epoch ms
  key: string; // Android notification key (for dedup)
}

let emitter: NativeEventEmitter | null = null;
let subscription: { remove: () => void } | null = null;

// ---- Public API ----

export function startNotificationCapture(): void {
  if (Platform.OS !== "android") {
    console.log("[NotificationCollector] Not available on iOS");
    return;
  }

  const { EinsteinNotifications } = NativeModules;
  if (!EinsteinNotifications) {
    console.warn("[NotificationCollector] Native module not linked");
    return;
  }

  emitter = new NativeEventEmitter(EinsteinNotifications);
  subscription = emitter.addListener(
    "onNotificationReceived",
    handleNotification
  );

  console.log("[NotificationCollector] Listening for notifications");
}

export function stopNotificationCapture(): void {
  subscription?.remove();
  subscription = null;
  emitter = null;
}

export function setAllowlist(apps: string[]): void {
  allowlist = new Set(apps);
}

export function setBlocklist(apps: string[]): void {
  for (const app of apps) DEFAULT_BLOCKLIST.add(app);
}

export function isPermissionGranted(): Promise<boolean> {
  if (Platform.OS !== "android") return Promise.resolve(false);
  const { EinsteinNotifications } = NativeModules;
  return EinsteinNotifications?.isPermissionGranted?.() ?? Promise.resolve(false);
}

export function openPermissionSettings(): void {
  if (Platform.OS !== "android") return;
  const { EinsteinNotifications } = NativeModules;
  EinsteinNotifications?.openSettings?.();
}

// ---- Internal ----

const recentKeys = new Set<string>(); // Simple dedup window
const DEDUP_WINDOW = 1000; // Max tracked keys

async function handleNotification(payload: NotificationPayload) {
  const { packageName, appName, title, text, timestamp, key } = payload;

  // Filter
  if (DEFAULT_BLOCKLIST.has(packageName)) return;
  if (allowlist.size > 0 && !allowlist.has(packageName)) return;
  if (recentKeys.has(key)) return;

  // Track for dedup
  recentKeys.add(key);
  if (recentKeys.size > DEDUP_WINDOW) {
    const first = recentKeys.values().next().value;
    if (first) recentKeys.delete(first);
  }

  // Build content
  const content = [title, text].filter(Boolean).join(": ");
  if (!content || content.length < 3) return;

  // Tier 0 extraction
  const tier0 = extractTier0(content);

  // Create event
  const event: ContextEvent = {
    id: `notif_${key}_${timestamp}`,
    user_id: "", // Will be set by cloud on ingest
    source: "notification",
    event_type: "notification",
    content,
    timestamp: new Date(timestamp).toISOString(),
    structured_data: {
      app_package: packageName,
      app_name: appName,
      notification_title: title,
      notification_text: text,
      ...tier0,
    },
    extracted_people: tier0.extracted_people,
    topics: [],
    processing_tier: 0,
    synced: false,
  };

  // Store locally + add to state
  await offlineDb.insertEvent(event);
  useStore.getState().addEvent(event);
}
