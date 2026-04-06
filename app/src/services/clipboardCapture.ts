/**
 * Clipboard capture service — listens for Tauri `clipboard-capture` events
 * from the Rust backend and forwards captured text to the Einstein API.
 *
 * Privacy: capture is only forwarded when the user has opted in via settings.
 */

// Tauri v2 event API
import { listen, type UnlistenFn } from "@tauri-apps/api/event";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";
const INGEST_ENDPOINT = `${API_BASE}/api/v1/context/ingest`;

/** Minimum interval (ms) between forwarded captures (debounce). */
const DEBOUNCE_MS = 2_000;

/** In-memory privacy flag — mirrors the Rust-side CapturePrivacy state. */
let captureEnabled = false;

/** Timestamp of the last forwarded capture. */
let lastCaptureTime = 0;

/**
 * POST captured text to the Einstein context ingest API.
 */
async function sendCapture(text: string): Promise<void> {
  try {
    const resp = await fetch(INGEST_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source: "desktop",
        event_type: "clipboard_capture",
        content: text,
        timestamp: new Date().toISOString(),
      }),
    });

    if (!resp.ok) {
      console.warn(
        `[clipboardCapture] Ingest failed: ${resp.status} ${resp.statusText}`
      );
    }
  } catch (err) {
    console.error("[clipboardCapture] Network error sending capture:", err);
  }
}

/**
 * Handle an incoming clipboard-capture event from the Tauri backend.
 */
function onClipboardCapture(event: { payload: string }): void {
  if (!captureEnabled) return;

  const now = Date.now();
  if (now - lastCaptureTime < DEBOUNCE_MS) return;
  lastCaptureTime = now;

  const text = event.payload;
  if (!text || typeof text !== "string") return;

  // Fire-and-forget — errors are logged inside sendCapture.
  void sendCapture(text);
}

/**
 * Enable or disable clipboard capture forwarding.
 */
export function setCaptureEnabled(enabled: boolean): void {
  captureEnabled = enabled;
}

/**
 * Query whether clipboard capture forwarding is currently enabled.
 */
export function isCaptureEnabled(): boolean {
  return captureEnabled;
}

/**
 * Start listening for clipboard-capture events.
 * Returns an unlisten function to tear down the listener.
 */
export async function startClipboardCapture(): Promise<UnlistenFn> {
  const unlisten = await listen<string>("clipboard-capture", onClipboardCapture);
  console.info("[clipboardCapture] Listener registered (forwarding disabled until opted in)");
  return unlisten;
}
