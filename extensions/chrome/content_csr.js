/**
 * Kodex Context Bridge — CSR Content Script
 *
 * Placeholder for Linden Lab's internal CSR tool (csr.lindenlab.com).
 * Extracts whatever visible fields are available and sends them to Kodex.
 *
 * TODO: Inspect actual CSR DOM and refine selectors once we have access.
 */

(function () {
  "use strict";

  const SOURCE = "csr";

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
  // These are best-guess selectors. Update once actual CSR DOM is known.

  function extractContext() {
    // Try to detect if this is a ticket/case detail page
    const url = window.location.href;
    const ticketMatch = url.match(/[?&]ticket[_\-]?(?:id|number|num)[=\/](\d+)/i)
      || url.match(/\/(?:ticket|case|issue)s?\/(\d+)/i)
      || url.match(/\/(\d{4,})/); // bare numeric ID in path

    const ticketNumber = ticketMatch ? ticketMatch[1] : null;

    // Generic field extraction — grab whatever's visible
    const subject =
      getText("h1") ||
      getText(".ticket-subject") ||
      getText(".case-title") ||
      getText('[class*="subject"]') ||
      getText('[class*="title"]') ||
      document.title || null;

    const customerName =
      getText(".customer-name") ||
      getText(".user-name") ||
      getText('[class*="customer"]') ||
      getText('[class*="requester"]') ||
      null;

    const customerEmail =
      getAttr('a[href^="mailto:"]', "href")?.replace("mailto:", "") ||
      getText(".customer-email") ||
      getText(".email") ||
      null;

    const status =
      getText(".status") ||
      getText(".ticket-status") ||
      getText('[class*="status"]') ||
      null;

    // Grab any SL username / display name that might be visible
    const slUsername =
      getText(".sl-username") ||
      getText(".avatar-name") ||
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

  console.log("[Kodex/CSR] Content script loaded on", window.location.href);
})();
