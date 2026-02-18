/**
 * Kodex Context Bridge — Background Service Worker
 *
 * Manages the native messaging connection to the Kodex host
 * (com.kodex.context) and relays context messages from content scripts.
 *
 * Protocol:
 *   Content script → chrome.runtime.sendMessage({ type: "TICKET_CONTEXT", ... })
 *   Background     → native host via chrome.runtime.connectNative / postMessage
 *   Native host    → responds with { success: true|false, error?: string }
 */

const NATIVE_HOST = "com.kodex.context";

let nativePort = null;
let connectionStatus = "disconnected"; // "disconnected" | "connected" | "error"
let lastError = null;
let lastContext = null;

// ── Connection management ────────────────────────────────────────────────────

function connectNative() {
  if (nativePort) return; // Already connected

  try {
    nativePort = chrome.runtime.connectNative(NATIVE_HOST);
    connectionStatus = "connected";
    lastError = null;
    console.log("[Kodex] Connected to native host:", NATIVE_HOST);

    nativePort.onMessage.addListener((response) => {
      console.log("[Kodex] Native host response:", response);
    });

    nativePort.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError;
      nativePort = null;
      connectionStatus = "disconnected";
      if (err) {
        lastError = err.message;
        console.warn("[Kodex] Native host disconnected:", err.message);
      } else {
        console.log("[Kodex] Native host disconnected (clean)");
      }
    });
  } catch (e) {
    nativePort = null;
    connectionStatus = "error";
    lastError = e.message;
    console.error("[Kodex] Failed to connect to native host:", e);
  }
}

function sendToNative(payload) {
  // Ensure connected
  if (!nativePort) {
    connectNative();
  }

  if (!nativePort) {
    console.error("[Kodex] No native port available, dropping message");
    return;
  }

  try {
    nativePort.postMessage(payload);
    console.log("[Kodex] Sent to native host:", payload);
  } catch (e) {
    console.error("[Kodex] Error sending to native host:", e);
    lastError = e.message;
    connectionStatus = "error";
    nativePort = null;
  }
}

// ── Message listener (from content scripts & popup) ──────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  console.log("[Kodex] Received message:", message.type, "from:", sender.tab?.url);

  switch (message.type) {
    case "TICKET_CONTEXT": {
      // Context captured from a content script — forward to native host
      const payload = {
        ...message.context,
        _source_url: sender.tab?.url ?? "",
        _source_tab_id: sender.tab?.id ?? null,
        _timestamp: new Date().toISOString(),
      };
      lastContext = payload;
      sendToNative(payload);
      sendResponse({ ok: true });
      break;
    }

    case "GET_STATUS": {
      // Popup asking for current connection status
      sendResponse({
        status: connectionStatus,
        error: lastError,
        lastContext: lastContext,
      });
      break;
    }

    case "RECONNECT": {
      // Popup requesting a reconnect attempt
      if (nativePort) {
        nativePort.disconnect();
        nativePort = null;
      }
      connectNative();
      sendResponse({ status: connectionStatus, error: lastError });
      break;
    }

    default:
      console.warn("[Kodex] Unknown message type:", message.type);
      sendResponse({ ok: false, error: "Unknown message type" });
  }

  // Return true to keep the message channel open for async sendResponse
  return true;
});

// ── Startup ──────────────────────────────────────────────────────────────────

// Attempt initial connection when the service worker starts
connectNative();

console.log("[Kodex] Background service worker started.");
