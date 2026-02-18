/**
 * Kodex Context Bridge — Popup Script
 *
 * Queries the background service worker for connection status and the
 * last captured ticket context, then renders it.
 */

(function () {
  "use strict";

  const statusRow = document.getElementById("status-row");
  const statusLabel = document.getElementById("status-label");
  const statusDetail = document.getElementById("status-detail");
  const contextArea = document.getElementById("context-area");
  const btnReconnect = document.getElementById("btn-reconnect");
  const btnClear = document.getElementById("btn-clear");

  // ── Render helpers ─────────────────────────────────────────────────────────

  function renderStatus(status, error) {
    // Reset classes
    statusRow.className = "status-row " + status;

    switch (status) {
      case "connected":
        statusLabel.textContent = "Connected to Kodex";
        statusDetail.textContent = "Native host active";
        break;
      case "disconnected":
        statusLabel.textContent = "Not connected";
        statusDetail.textContent = error || "Native host not running. Run Kodex first.";
        break;
      case "error":
        statusLabel.textContent = "Connection error";
        statusDetail.textContent = error || "Unknown error";
        break;
      default:
        statusLabel.textContent = "Unknown";
        statusDetail.textContent = status;
    }
  }

  function contextRow(label, value, mono = false) {
    if (!value) return "";
    const cls = mono ? "value mono" : "value";
    const escaped = String(value).replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `
      <div class="context-row">
        <span class="label">${label}</span>
        <span class="${cls}">${escaped}</span>
      </div>`;
  }

  function renderContext(ctx) {
    if (!ctx) {
      contextArea.innerHTML = '<div class="empty-state">No context captured yet.<br/>Open a ticket page to capture context.</div>';
      return;
    }

    const sourceLabels = { freshdesk: "Freshdesk", csr: "CSR", gt3: "GT3" };
    const sourceLabel = sourceLabels[ctx.source] || ctx.source || "Unknown";

    let html = "";
    html += contextRow("Source", sourceLabel);
    html += contextRow("Ticket #", ctx.ticket_number, true);
    html += contextRow("Subject", ctx.subject);
    html += contextRow("Customer", ctx.customer_name);
    html += contextRow("Email", ctx.customer_email, true);
    html += contextRow("SL User", ctx.sl_username, true);
    html += contextRow("Account ID", ctx.account_id, true);
    html += contextRow("Status", ctx.status);
    html += contextRow("Priority", ctx.priority);

    if (ctx._timestamp) {
      const ts = new Date(ctx._timestamp);
      html += contextRow("Captured", ts.toLocaleTimeString());
    }

    if (!html) {
      html = '<div class="empty-state">Context captured but fields are empty.</div>';
    }

    contextArea.innerHTML = html;
  }

  // ── Load status from background ────────────────────────────────────────────

  function refresh() {
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
      if (chrome.runtime.lastError) {
        renderStatus("error", chrome.runtime.lastError.message);
        renderContext(null);
        return;
      }
      renderStatus(response.status || "disconnected", response.error);
      renderContext(response.lastContext);
    });
  }

  // ── Button handlers ────────────────────────────────────────────────────────

  btnReconnect.addEventListener("click", () => {
    btnReconnect.disabled = true;
    btnReconnect.textContent = "Connecting...";

    chrome.runtime.sendMessage({ type: "RECONNECT" }, (response) => {
      btnReconnect.disabled = false;
      btnReconnect.textContent = "Reconnect";
      if (response) {
        renderStatus(response.status || "disconnected", response.error);
      }
    });
  });

  btnClear.addEventListener("click", () => {
    renderContext(null);
  });

  // ── Init ───────────────────────────────────────────────────────────────────

  refresh();
})();
