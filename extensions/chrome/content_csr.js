/**
 * Kodex Context Bridge — CSR Content Script
 *
 * Extracts customer context from Linden Lab's CSR tool at:
 *   support-tools.agni.lindenlab.com/csr/summary/{UUID}/?view=csr-concierge
 *
 * Fields extracted:
 *   - customer_id (UUID from URL and page)
 *   - real_name
 *   - agent_id
 *   - account_id
 *   - persona_id
 *   - tilia_wallet_id
 *   - avatar_name (from page header)
 */

(function () {
  "use strict";

  const SOURCE = "csr";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  function getTextByLabel(labelText) {
    // Find a label element and get the adjacent value
    // Works for patterns like: <td>Customer ID</td><td>value</td>
    // or <span>Customer ID:</span><span>value</span>
    const labels = document.querySelectorAll("td, th, span, div, dt, label");
    for (const label of labels) {
      const text = label.textContent.trim();
      if (text.toLowerCase().includes(labelText.toLowerCase())) {
        // Try next sibling
        let next = label.nextElementSibling;
        if (next) {
          const val = next.textContent.trim();
          if (val && val !== text) return val;
        }
        // Try parent's next sibling (for nested structures)
        if (label.parentElement) {
          next = label.parentElement.nextElementSibling;
          if (next) {
            const val = next.textContent.trim();
            if (val && val !== text) return val;
          }
        }
      }
    }
    return null;
  }

  function getUUIDFromURL() {
    // URL pattern: /csr/summary/{UUID}/?view=csr-concierge
    const match = window.location.pathname.match(
      /\/csr\/(?:summary|detail|view)\/([a-f0-9]{32})/i
    );
    return match ? match[1] : null;
  }

  // ── Context extraction ─────────────────────────────────────────────────────

  function extractContext() {
    const url = window.location.href;

    // Check if this is a CSR page
    if (!url.includes("/csr/") && !url.includes("view=csr")) {
      return null;
    }

    // Extract UUID from URL
    const customerIdFromUrl = getUUIDFromURL();

    // Extract fields from the page info panel
    const customerId =
      getTextByLabel("Customer ID") ||
      customerIdFromUrl ||
      null;

    const realName =
      getTextByLabel("Real Name") ||
      getTextByLabel("Name") ||
      null;

    const agentId =
      getTextByLabel("Agent ID") ||
      null;

    const accountId =
      getTextByLabel("Account ID") ||
      null;

    const personaId =
      getTextByLabel("Persona ID") ||
      null;

    const tiliaWalletId =
      getTextByLabel("Tilia Wallet ID") ||
      getTextByLabel("Wallet ID") ||
      null;

    // Avatar/resident name from header (e.g., "Gimmesamoa.Resident - Summary")
    const headerText = getText("h1, h2, .page-title, .header-title");
    let avatarName = null;
    if (headerText) {
      // Extract "Username.Resident" or just "Username" from header
      const avatarMatch = headerText.match(/([A-Za-z0-9]+(?:\.[A-Za-z]+)?)\s*[-–—]/);
      if (avatarMatch) {
        avatarName = avatarMatch[1];
      } else if (headerText.includes(".Resident")) {
        avatarName = headerText.split(/\s*[-–—]/)[0].trim();
      }
    }

    // Also try the link that shows avatar name
    if (!avatarName) {
      const avatarLink = document.querySelector('a[href*="secondlife.com"]');
      if (avatarLink) {
        avatarName = avatarLink.textContent.trim();
      }
    }

    // Grid name (from "AGNI" header if visible)
    const gridName =
      getText(".grid-name") ||
      getText("h1:first-of-type") ||
      null;

    return {
      source: SOURCE,
      customer_id: customerId,
      real_name: realName,
      agent_id: agentId,
      account_id: accountId,
      persona_id: personaId,
      tilia_wallet_id: tiliaWalletId,
      avatar_name: avatarName,
      grid: gridName,
      url: url,
      page_title: document.title,
    };
  }

  // ── Send context to background ─────────────────────────────────────────────

  function sendContext(context) {
    chrome.runtime.sendMessage(
      { type: "TICKET_CONTEXT", context },
      (response) => {
        if (chrome.runtime.lastError) {
          console.debug("[Kodex/CSR] sendMessage error:", chrome.runtime.lastError.message);
        } else {
          console.log("[Kodex/CSR] Context sent, response:", response);
        }
      }
    );
  }

  // ── Trigger logic ──────────────────────────────────────────────────────────

  let lastSentUrl = null;
  let debounceTimer = null;

  function maybeSend() {
    const context = extractContext();
    if (!context) return;

    const currentUrl = window.location.href;
    if (currentUrl === lastSentUrl) return;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      lastSentUrl = currentUrl;
      console.log("[Kodex/CSR] Sending context:", context);
      sendContext(context);
    }, 800);
  }

  // Run on page load
  maybeSend();

  // Watch for SPA navigation
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastSentUrl = null;
      setTimeout(maybeSend, 500);
    }
  }, 500);

  // ── Send context when tab gains focus ────────────────────────────────────

  function forceSend() {
    lastSentUrl = null;
    maybeSend();
  }

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      console.log("[Kodex/CSR] Tab became visible, refreshing context");
      setTimeout(forceSend, 100);
    }
  });

  window.addEventListener("focus", () => {
    console.log("[Kodex/CSR] Window focused, refreshing context");
    setTimeout(forceSend, 100);
  });

  console.log("[Kodex/CSR] Content script loaded on", window.location.href);
})();
