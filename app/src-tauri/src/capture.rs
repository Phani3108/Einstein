//! Desktop passive context capture — clipboard monitoring and active window tracking.
//!
//! This module provides background monitors that detect new clipboard content
//! and active window transitions, emitting Tauri events for the frontend to
//! forward to the Einstein API.

use std::collections::VecDeque;
use std::hash::{DefaultHasher, Hash, Hasher};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::time::Duration;

use tauri::{AppHandle, Emitter, Manager};

/// Minimum clipboard text length to consider for capture.
const MIN_CLIPBOARD_LEN: usize = 20;
/// How many recent clipboard hashes to keep for deduplication.
const DEDUP_HISTORY_SIZE: usize = 10;
/// Clipboard poll interval.
const POLL_INTERVAL: Duration = Duration::from_secs(5);

// ---------------------------------------------------------------------------
// Shared state: privacy toggle
// ---------------------------------------------------------------------------

/// Managed Tauri state that gates all passive capture.
pub struct CapturePrivacy(pub AtomicBool);

impl Default for CapturePrivacy {
    fn default() -> Self {
        // Capture is disabled by default — user must opt in.
        Self(AtomicBool::new(false))
    }
}

/// Tauri command: enable or disable passive capture at runtime.
#[tauri::command]
pub fn set_capture_enabled(enabled: bool, state: tauri::State<CapturePrivacy>) {
    state.0.store(enabled, Ordering::Relaxed);
    log::info!("Passive capture enabled = {enabled}");
}

/// Tauri command: query whether passive capture is enabled.
#[tauri::command]
pub fn is_capture_enabled(state: tauri::State<CapturePrivacy>) -> bool {
    state.0.load(Ordering::Relaxed)
}

// ---------------------------------------------------------------------------
// Clipboard monitoring
// ---------------------------------------------------------------------------

/// Start a background thread that polls the system clipboard every
/// [`POLL_INTERVAL`] seconds.  When new, non-duplicate text of at least
/// [`MIN_CLIPBOARD_LEN`] characters is detected (and privacy is enabled),
/// a `clipboard-capture` event is emitted to the frontend.
pub fn start_clipboard_monitor(app: AppHandle) {
    let privacy = app.state::<CapturePrivacy>().inner().0.clone();
    let privacy = Arc::new(privacy);

    std::thread::spawn(move || {
        // Ring buffer of recent content hashes for dedup.
        let recent_hashes: Mutex<VecDeque<u64>> =
            Mutex::new(VecDeque::with_capacity(DEDUP_HISTORY_SIZE));

        loop {
            std::thread::sleep(POLL_INTERVAL);

            // Respect privacy toggle.
            if !app.state::<CapturePrivacy>().0.load(Ordering::Relaxed) {
                continue;
            }

            let text = match get_clipboard_text() {
                Some(t) => t,
                None => continue,
            };

            if text.len() < MIN_CLIPBOARD_LEN {
                continue;
            }

            let hash = hash_string(&text);

            {
                let mut ring = recent_hashes.lock().unwrap();
                if ring.contains(&hash) {
                    continue; // duplicate
                }
                if ring.len() >= DEDUP_HISTORY_SIZE {
                    ring.pop_front();
                }
                ring.push_back(hash);
            }

            // Emit event to the frontend.
            if let Err(e) = app.emit("clipboard-capture", text) {
                log::warn!("Failed to emit clipboard-capture event: {e}");
            }
        }
    });
}

/// Read current clipboard text.  Returns `None` when the clipboard is empty
/// or contains non-text data.
fn get_clipboard_text() -> Option<String> {
    // Use `pbpaste` on macOS; on other platforms fall back to a no-op.
    #[cfg(target_os = "macos")]
    {
        let output = std::process::Command::new("pbpaste")
            .output()
            .ok()?;
        if output.status.success() {
            let text = String::from_utf8_lossy(&output.stdout).to_string();
            if text.is_empty() {
                None
            } else {
                Some(text)
            }
        } else {
            None
        }
    }

    #[cfg(target_os = "windows")]
    {
        // On Windows, reading the clipboard from a background thread requires
        // the win32 clipboard API (OpenClipboard / GetClipboardData).  For now
        // return None — a full implementation would use the `clipboard-win` crate.
        None
    }

    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    {
        // Linux: could use `xclip -o` or `wl-paste`.
        let output = std::process::Command::new("xclip")
            .args(["-selection", "clipboard", "-o"])
            .output()
            .ok()?;
        if output.status.success() {
            let text = String::from_utf8_lossy(&output.stdout).to_string();
            if text.is_empty() { None } else { Some(text) }
        } else {
            None
        }
    }
}

fn hash_string(s: &str) -> u64 {
    let mut hasher = DefaultHasher::new();
    s.hash(&mut hasher);
    hasher.finish()
}

// ---------------------------------------------------------------------------
// Active window tracking (optional, privacy-gated)
// ---------------------------------------------------------------------------

/// Return the title of the currently focused window, if available.
#[cfg(target_os = "macos")]
pub fn get_active_window_title() -> Option<String> {
    let script = r#"
        tell application "System Events"
            set frontApp to name of first application process whose frontmost is true
            try
                tell process frontApp
                    set winTitle to name of front window
                end tell
                return frontApp & " — " & winTitle
            on error
                return frontApp
            end try
        end tell
    "#;

    let output = std::process::Command::new("osascript")
        .arg("-e")
        .arg(script)
        .output()
        .ok()?;

    if output.status.success() {
        let title = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if title.is_empty() { None } else { Some(title) }
    } else {
        None
    }
}

#[cfg(target_os = "windows")]
pub fn get_active_window_title() -> Option<String> {
    // Windows implementation requires win32 API (GetForegroundWindow +
    // GetWindowTextW).  Left as a stub — consider the `windows` crate.
    None
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
pub fn get_active_window_title() -> Option<String> {
    // Linux: could use `xdotool getactivewindow getwindowname`.
    let output = std::process::Command::new("xdotool")
        .args(["getactivewindow", "getwindowname"])
        .output()
        .ok()?;
    if output.status.success() {
        let title = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if title.is_empty() { None } else { Some(title) }
    } else {
        None
    }
}

/// Start a background thread that tracks active window title transitions
/// and emits `window-transition` events.  Only fires when the title
/// actually changes, not continuously.
pub fn start_window_monitor(app: AppHandle) {
    std::thread::spawn(move || {
        let mut last_title: Option<String> = None;

        loop {
            std::thread::sleep(Duration::from_secs(3));

            if !app.state::<CapturePrivacy>().0.load(Ordering::Relaxed) {
                continue;
            }

            let current = get_active_window_title();
            if current != last_title {
                if let Some(ref title) = current {
                    let _ = app.emit("window-transition", title.clone());
                }
                last_title = current;
            }
        }
    });
}

// ---------------------------------------------------------------------------
// Setup entry point
// ---------------------------------------------------------------------------

/// Initialize all passive capture monitors.  Call this from the Tauri
/// `.setup()` closure after managing `CapturePrivacy` state.
pub fn setup_capture(app: &tauri::App) {
    let handle = app.handle().clone();
    start_clipboard_monitor(handle.clone());
    start_window_monitor(handle);
    log::info!("Passive capture monitors started (privacy-gated, disabled by default)");
}
