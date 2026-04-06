/**
 * Einstein Browser Extension — Popup Logic
 *
 * Manages the popup UI: connection status, quick-note capture,
 * settings persistence, and capture count display.
 */

(() => {
  "use strict";

  const DEFAULT_API_URL = "http://localhost:8000";
  const INGEST_PATH = "/api/v1/context/ingest";

  // ---- DOM references ----

  const statusDot = document.getElementById("status-dot");
  const noteInput = document.getElementById("note-input");
  const sendBtn = document.getElementById("send-btn");
  const sendStatus = document.getElementById("send-status");
  const captureCountEl = document.getElementById("capture-count");
  const apiUrlInput = document.getElementById("api-url");
  const authTokenInput = document.getElementById("auth-token");
  const saveBtn = document.getElementById("save-btn");
  const saveStatus = document.getElementById("save-status");

  // ---- Initialise ----

  document.addEventListener("DOMContentLoaded", init);

  async function init() {
    const settings = await loadSettings();
    apiUrlInput.value = settings.apiUrl || DEFAULT_API_URL;
    authTokenInput.value = settings.authToken || "";

    await checkConnection(settings);
    await refreshCaptureCount();

    // Enable send button only when there is input.
    noteInput.addEventListener("input", () => {
      sendBtn.disabled = noteInput.value.trim().length === 0;
    });

    sendBtn.addEventListener("click", handleSend);
    saveBtn.addEventListener("click", handleSave);
  }

  // ---- Connection check ----

  async function checkConnection(settings) {
    const apiUrl = (settings && settings.apiUrl) || DEFAULT_API_URL;

    try {
      const response = await fetch(`${apiUrl}/health`, {
        method: "GET",
        signal: AbortSignal.timeout(5000),
      });

      if (response.ok) {
        setConnectionStatus("connected");
      } else {
        setConnectionStatus("disconnected");
      }
    } catch {
      setConnectionStatus("disconnected");
    }
  }

  function setConnectionStatus(state) {
    statusDot.className = "status-dot";
    if (state === "connected") {
      statusDot.classList.add("status-dot--connected");
      statusDot.title = "Connected to Einstein API";
    } else {
      statusDot.classList.add("status-dot--disconnected");
      statusDot.title = "Cannot reach Einstein API";
    }
  }

  // ---- Quick-note capture ----

  async function handleSend() {
    const note = noteInput.value.trim();
    if (!note) return;

    sendBtn.disabled = true;
    showStatus(sendStatus, "Sending...", "");

    try {
      const settings = await loadSettings();
      const apiUrl = settings.apiUrl || DEFAULT_API_URL;

      const headers = { "Content-Type": "application/json" };
      if (settings.authToken) {
        headers["Authorization"] = `Bearer ${settings.authToken}`;
      }

      const payload = {
        events: [
          {
            source: "browser",
            event_type: "web_clip",
            content: note,
            structured_data: {
              url: "",
              title: "Quick note from extension",
              description: "",
              selected_text: "",
            },
            timestamp: new Date().toISOString(),
          },
        ],
      };

      const response = await fetch(`${apiUrl}${INGEST_PATH}`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const body = await response.text().catch(() => "");
        throw new Error(`API returned ${response.status}: ${body}`);
      }

      noteInput.value = "";
      sendBtn.disabled = true;
      showStatus(sendStatus, "Sent successfully", "success");

      // Update capture count.
      await incrementCaptureCount();
      await refreshCaptureCount();
    } catch (err) {
      console.error("[Einstein] Send failed:", err);
      showStatus(sendStatus, `Failed: ${err.message}`, "error");
      sendBtn.disabled = false;
    }
  }

  // ---- Settings ----

  async function handleSave() {
    const apiUrl = apiUrlInput.value.trim() || DEFAULT_API_URL;
    const authToken = authTokenInput.value.trim();

    saveBtn.disabled = true;

    try {
      await saveSettings({ apiUrl, authToken });
      showStatus(saveStatus, "Settings saved", "success");

      // Re-check connection with new settings.
      await checkConnection({ apiUrl, authToken });
    } catch (err) {
      showStatus(saveStatus, "Failed to save", "error");
    } finally {
      saveBtn.disabled = false;
    }
  }

  // ---- Storage helpers ----

  function loadSettings() {
    return new Promise((resolve) => {
      chrome.storage.sync.get(
        { apiUrl: DEFAULT_API_URL, authToken: "", captureCount: 0 },
        (items) => resolve(items)
      );
    });
  }

  function saveSettings({ apiUrl, authToken }) {
    return new Promise((resolve, reject) => {
      chrome.storage.sync.set({ apiUrl, authToken }, () => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError);
        } else {
          resolve();
        }
      });
    });
  }

  function incrementCaptureCount() {
    return new Promise((resolve) => {
      chrome.storage.sync.get({ captureCount: 0 }, (items) => {
        chrome.storage.sync.set(
          { captureCount: items.captureCount + 1 },
          resolve
        );
      });
    });
  }

  async function refreshCaptureCount() {
    const settings = await loadSettings();
    captureCountEl.textContent = String(settings.captureCount || 0);
  }

  // ---- UI helpers ----

  function showStatus(el, message, type) {
    el.textContent = message;
    el.className = "status-message";
    if (type === "success") el.classList.add("status-message--success");
    if (type === "error") el.classList.add("status-message--error");
    el.hidden = false;

    if (type) {
      setTimeout(() => {
        el.hidden = true;
      }, 4000);
    }
  }
})();
