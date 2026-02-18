/**
 * Kodex Context Bridge — GT3 Content Script
 *
 * Placeholder for Linden Lab's internal GT3 tool (gt3.lindenlab.com).
 * Extracts whatever visible fields are available and sends them to Kodex.
 *
 * TODO: Inspect actual GT3 DOM and refine selectors once we have access.
 */

(function () {
  "use strict";

  const SOURCE = "gt3";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  function getAttr(selector, attr) {
    const el = document.querySelector(selector);
    return el ? (el.getAttribute(attr) || "").trim() : null;
  }

  // ── Context extraction ─────────────────────────────────────────────────────
  // These are best-guess selectors. Update once actual GT3 DOM is known.

  function extractContext() {
    const url = window.location.href;

    // Try to detect a ticket/issue/case ID from the URL
    const ticketMatch = url.match(/[?&](?:ticket|issue|case|id)[_\-]?(?:id|number)?[=\/](\d+)/i)
      || url.match(/\/(?:ticket|issue|case)s?\/(\d+)/i)
      || url.match(/\/(\d{4,})/);

    const ticketNumber = ticketMatch ? ticketMatch[1] : null;

    // Generic field extraction
    const subject =
      getText("h1") ||
      getText(".issue-title") ||
      getText(".ticket-title") ||
      getText('[class*="title"]') ||
      getText('[class*="subject"]') ||
      document.title || null;

    const customerName =
      getText(".customer-name") ||
      getText(".requester-name") ||
      getText('[class*="customer"]') ||
      getText('[class*="requester"]') ||
      getText('[class*="user-name"]') ||
      null;

    const customerEmail =
      getAttr('a[href^="mailto:"]', "href")?.replace("mailto:", "") ||
      getText(".email") ||
      getText('[class*="email"]') ||
      null;

    const status =
      getText(".status") ||
      getText(".issue-status") ||
      getText('[class*="status"]') ||
      null;

    // GT3 might show account/SL-specific fields
    const accountId =
      getText(".account-id") ||
      getText('[data-field="account_id"]') ||
      getText('[class*="account-id"]') ||
      null;

    const slUsername =
      getText(".sl-username") ||
      getText('[class*="username"]') ||
      getText('[data-field="username"]') ||
      null;

    return {
      source: SOURCE,
      ticket_number: ticketNumber,
      subject: subject,
      customer_name: customerName,
      customer_email: customerEmail,
      sl_username: slUsername,
      account_id: accountId,
      status: status,
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
          console.debug("[Kodex/GT3] sendMessage error:", chrome.runtime.lastError.message);
        } else {
          console.log("[Kodex/GT3] Context sent, response:", response);
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
      console.log("[Kodex/GT3] Sending context:", context);
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
      console.log("[Kodex/GT3] Tab became visible, refreshing context");
      setTimeout(forceSend, 100);
    }
  });

  window.addEventListener("focus", () => {
    console.log("[Kodex/GT3] Window focused, refreshing context");
    setTimeout(forceSend, 100);
  });

  console.log("[Kodex/GT3] Content script loaded on", window.location.href);
})();
