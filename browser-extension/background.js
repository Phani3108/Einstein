/**
 * Einstein Browser Extension — Background Service Worker
 *
 * Handles context menu actions, keyboard shortcuts, and API communication
 * for capturing web content into the Einstein second brain.
 */

const DEFAULT_API_URL = "http://localhost:8000";
const INGEST_PATH = "/api/v1/context/ingest";
const BADGE_CLEAR_DELAY_MS = 3000;

// ---------------------------------------------------------------------------
// Context menu setup
// ---------------------------------------------------------------------------

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "send-to-einstein",
    title: "Send to Einstein",
    contexts: ["selection", "page"],
  });
});

// ---------------------------------------------------------------------------
// Context menu click handler
// ---------------------------------------------------------------------------

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== "send-to-einstein") return;
  await captureFromTab(tab, info.selectionText || null);
});

// ---------------------------------------------------------------------------
// Keyboard shortcut handler (Ctrl+Shift+E / Cmd+Shift+E)
// ---------------------------------------------------------------------------

chrome.commands.onCommand.addListener(async (command) => {
  if (command !== "quick-capture") return;

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  await captureFromTab(tab, null);
});

// ---------------------------------------------------------------------------
// Core capture logic
// ---------------------------------------------------------------------------

/**
 * Capture content from the active tab and send it to the Einstein API.
 *
 * @param {chrome.tabs.Tab} tab - The active tab.
 * @param {string|null} selectionText - Pre-selected text from context menu, if any.
 */
async function captureFromTab(tab, selectionText) {
  setBadge("...", "#888888");

  try {
    // Gather page metadata and selected text from the content script.
    const pageData = await getPageData(tab.id);
    const selectedText =
      selectionText || pageData.selectedText || "";

    const payload = buildPayload({
      url: tab.url || pageData.canonicalUrl || "",
      title: tab.title || pageData.title || "",
      description: pageData.description || "",
      selectedText,
    });

    await sendToApi(payload);

    // Track capture count.
    await incrementCaptureCount();

    setBadge("OK", "#22c55e");
  } catch (err) {
    console.error("[Einstein] Capture failed:", err);
    setBadge("ERR", "#ef4444");
  } finally {
    setTimeout(() => clearBadge(), BADGE_CLEAR_DELAY_MS);
  }
}

// ---------------------------------------------------------------------------
// Content script communication
// ---------------------------------------------------------------------------

/**
 * Request page metadata and selected text from the content script.
 * Falls back gracefully if the content script is unreachable.
 */
function getPageData(tabId) {
  return new Promise((resolve) => {
    chrome.tabs.sendMessage(tabId, { action: "getPageData" }, (response) => {
      if (chrome.runtime.lastError || !response) {
        resolve({ selectedText: "", title: "", description: "", canonicalUrl: "" });
        return;
      }
      resolve(response);
    });
  });
}

// ---------------------------------------------------------------------------
// API communication
// ---------------------------------------------------------------------------

/**
 * Build the ingestion payload matching the Einstein API schema.
 */
function buildPayload({ url, title, description, selectedText }) {
  const content = selectedText || `Page: ${title}`;
  return {
    events: [
      {
        source: "browser",
        event_type: "web_clip",
        content,
        structured_data: {
          url,
          title,
          description,
          selected_text: selectedText,
        },
        timestamp: new Date().toISOString(),
      },
    ],
  };
}

/**
 * POST the payload to the Einstein context ingestion endpoint.
 */
async function sendToApi(payload) {
  const { apiUrl, authToken } = await getSettings();

  const headers = {
    "Content-Type": "application/json",
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${apiUrl}${INGEST_PATH}`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`API returned ${response.status}: ${body}`);
  }

  return response.json();
}

// ---------------------------------------------------------------------------
// Settings helpers
// ---------------------------------------------------------------------------

/**
 * Read extension settings from chrome.storage.sync.
 */
function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.sync.get(
      { apiUrl: DEFAULT_API_URL, authToken: "" },
      (items) => resolve(items)
    );
  });
}

// ---------------------------------------------------------------------------
// Badge helpers
// ---------------------------------------------------------------------------

function setBadge(text, color) {
  chrome.action.setBadgeText({ text });
  chrome.action.setBadgeBackgroundColor({ color });
}

function clearBadge() {
  chrome.action.setBadgeText({ text: "" });
}

// ---------------------------------------------------------------------------
// Capture count tracking
// ---------------------------------------------------------------------------

async function incrementCaptureCount() {
  return new Promise((resolve) => {
    chrome.storage.sync.get({ captureCount: 0 }, (items) => {
      chrome.storage.sync.set(
        { captureCount: items.captureCount + 1 },
        resolve
      );
    });
  });
}
