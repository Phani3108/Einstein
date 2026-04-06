/**
 * ShareReceiver — handles content shared TO Einstein from other apps.
 *
 * Android: Content arrives via Android share sheet (ACTION_SEND intent).
 * iOS: Content is buffered by the Share Extension into App Group UserDefaults
 *       and picked up on next app launch.
 *
 * The service detects the source app, parses the content for URLs/mentions/hashtags,
 * creates a ContextEvent, and posts it to the Einstein API.
 */
import { Alert, Platform } from "react-native";
import { useStore } from "../../store/useStore";
import { extractTier0 } from "../tier0";
import { offlineDb } from "../../db/offline";
import type { ContextEvent } from "../../store/types";

// ---- Source detection ----

/** Map Android package names (and iOS bundle hints) to human-readable source labels. */
const SOURCE_MAP: Record<string, string> = {
  // WhatsApp
  "com.whatsapp": "whatsapp",
  "com.whatsapp.w4b": "whatsapp",
  // Gmail
  "com.google.android.gm": "gmail",
  // Slack
  "com.slack": "slack",
  // Browsers
  "com.android.chrome": "browser",
  "org.mozilla.firefox": "browser",
  "com.brave.browser": "browser",
  "com.opera.browser": "browser",
  "com.microsoft.emmx": "browser", // Edge
  // Safari (iOS — bundle id hint, may come as partial match)
  "com.apple.mobilesafari": "browser",
};

function detectSource(sourceApp?: string): string {
  if (!sourceApp) return "shared";
  // Exact match first
  if (SOURCE_MAP[sourceApp]) return SOURCE_MAP[sourceApp];
  // Partial/prefix match for variants (e.g. com.whatsapp.something)
  for (const [prefix, label] of Object.entries(SOURCE_MAP)) {
    if (sourceApp.startsWith(prefix)) return label;
  }
  return "shared";
}

// ---- Content parsing ----

const URL_PATTERN = /https?:\/\/[^\s<>"{}|\\^`[\]]+/g;
const MENTION_PATTERN = /@[\w.-]+/g;
const HASHTAG_PATTERN = /#[\w]+/g;

interface ParsedContent {
  urls: string[];
  mentions: string[];
  hashtags: string[];
  cleanText: string;
}

function parseContent(text: string): ParsedContent {
  URL_PATTERN.lastIndex = 0;
  MENTION_PATTERN.lastIndex = 0;
  HASHTAG_PATTERN.lastIndex = 0;

  const urls = [...new Set(text.match(URL_PATTERN) ?? [])];
  const mentions = [...new Set(text.match(MENTION_PATTERN) ?? [])];
  const hashtags = [...new Set(text.match(HASHTAG_PATTERN) ?? [])];

  // Clean text: remove URLs for a more readable summary
  const cleanText = text
    .replace(URL_PATTERN, "")
    .replace(/\s{2,}/g, " ")
    .trim();

  return { urls, mentions, hashtags, cleanText };
}

// ---- Event type resolution ----

function resolveEventType(source: string, parsed: ParsedContent): string {
  if (parsed.urls.length > 0) return "link_share";
  if (source === "whatsapp" || source === "slack") return "message";
  if (source === "gmail") return "email";
  return "note";
}

// ---- Public API ----

/**
 * Process raw shared content into a ContextEvent.
 * Does NOT submit to the API — returns the event for the caller to handle.
 */
export function processSharedContent(
  text: string,
  sourceApp?: string,
): ContextEvent {
  const source = detectSource(sourceApp);
  const parsed = parseContent(text);
  const tier0 = extractTier0(text);
  const eventType = resolveEventType(source, parsed);
  const timestamp = new Date().toISOString();
  const id = `share_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

  const event: ContextEvent = {
    id,
    user_id: "", // Set by the cloud API on ingest
    source: source as ContextEvent["source"],
    event_type: eventType,
    content: text,
    timestamp,
    structured_data: {
      shared_from: sourceApp ?? "unknown",
      urls: parsed.urls,
      mentions: parsed.mentions,
      hashtags: parsed.hashtags,
      clean_text: parsed.cleanText,
      ...tier0,
    },
    extracted_people: tier0.extracted_people,
    topics: parsed.hashtags.map((h) => h.replace("#", "")),
    processing_tier: 0,
    synced: false,
  };

  return event;
}

/**
 * Full handler for an incoming share intent.
 * Processes the content, stores it locally, adds to state, and submits to the API.
 * Shows a success or error toast via Alert.
 */
export async function handleIncomingShare(intent: {
  text?: string;
  url?: string;
  source?: string;
}): Promise<void> {
  // Combine text and URL — some intents send only one or both
  const parts: string[] = [];
  if (intent.text) parts.push(intent.text);
  if (intent.url && !intent.text?.includes(intent.url)) parts.push(intent.url);
  const combinedText = parts.join("\n").trim();

  if (!combinedText) {
    Alert.alert("Nothing to save", "The shared content was empty.");
    return;
  }

  try {
    const event = processSharedContent(combinedText, intent.source);

    // Store locally first (offline-first)
    await offlineDb.insertEvent(event);
    useStore.getState().addEvent(event);

    // Attempt API submission
    const serverUrl = useStore.getState().serverUrl;
    const authToken = useStore.getState().authToken;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    };

    try {
      const res = await fetch(`${serverUrl}/api/v1/context/ingest`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          id: event.id,
          source: event.source,
          event_type: event.event_type,
          content: event.content,
          timestamp: event.timestamp,
          structured_data: event.structured_data,
          extracted_people: event.extracted_people,
          topics: event.topics,
          processing_tier: event.processing_tier,
        }),
      });

      if (res.ok) {
        // Mark as synced
        useStore.getState().markSynced([event.id]);
        showToast("Saved to Einstein", "Content captured and synced.");
      } else {
        // Stored locally, will sync later
        showToast(
          "Saved locally",
          "Content saved offline. It will sync when the server is reachable.",
        );
      }
    } catch {
      // Network error — stored locally, will sync later
      showToast(
        "Saved locally",
        "Content saved offline. It will sync when the server is reachable.",
      );
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Unknown error";
    Alert.alert("Error", `Failed to process shared content: ${message}`);
  }
}

/**
 * Check for pending shares from the iOS Share Extension.
 * The Share Extension writes to shared App Group UserDefaults under key "pendingShares".
 * Call this on app launch / foreground to pick up any buffered shares.
 */
export async function processPendingIOSShares(): Promise<number> {
  if (Platform.OS !== "ios") return 0;

  try {
    // Access shared UserDefaults via the react-native-shared-group-preferences
    // or a custom native module. This is a placeholder — the actual implementation
    // depends on the native bridge being configured.
    //
    // Example using a hypothetical native module:
    //   const { SharedUserDefaults } = NativeModules;
    //   const raw = await SharedUserDefaults.getString("pendingShares", APP_GROUP_ID);
    //
    // For now, we log and return 0 until the native bridge is set up.
    console.log("[ShareReceiver] Checking for pending iOS shares...");
    return 0;
  } catch (err) {
    console.warn("[ShareReceiver] Failed to check pending iOS shares:", err);
    return 0;
  }
}

// ---- Internal ----

function showToast(title: string, message: string): void {
  // On both platforms, use Alert as a simple toast.
  // A proper implementation would use a toast library (e.g. react-native-toast-message).
  Alert.alert(title, message);
}
