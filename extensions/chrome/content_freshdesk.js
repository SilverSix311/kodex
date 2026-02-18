/**
 * Kodex Context Bridge — Freshdesk Content Script
 *
 * Extracts ticket context from Freshdesk ticket detail pages and
 * sends it to the background service worker.
 *
 * Extracted fields:
 *   - ticket_number    (from URL: /tickets/12345)
 *   - subject          (ticket title)
 *   - customer_name    (requester name)
 *   - customer_email   (requester email)
 *   - status           (e.g. "Open", "Pending", "Resolved")
 *   - priority         (e.g. "Low", "Medium", "High", "Urgent")
 */

(function () {
  "use strict";

  const SOURCE = "freshdesk";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getTicketNumber() {
    const match = window.location.pathname.match(/tickets?\/(\d+)/i);
    return match ? match[1] : null;
  }

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  function getAttr(selector, attr) {
    const el = document.querySelector(selector);
    return el ? (el.getAttribute(attr) || "").trim() : null;
  }

  // ── Context extraction ─────────────────────────────────────────────────────

  function extractContext() {
    const ticketNumber = getTicketNumber();
    if (!ticketNumber) return null; // Not a ticket page

    // Subject / title — try multiple selectors for robustness across FD versions
    const subject =
      getText(".ticket-title") ||
      getText('[data-test-id="ticket-title"]') ||
      getText(".subject") ||
      getText("h1.ticket-heading") ||
      document.title.replace(/^\[#\d+\]\s*/, "").trim() ||
      null;

    // Requester name
    const customerName =
      getText(".requester-name") ||
      getText('[data-test-id="requester-name"]') ||
      getText(".contact-name") ||
      getText(".requester .name") ||
      null;

    // Requester email — often in an href or data attribute
    const customerEmail =
      getAttr('a[href^="mailto:"]', "href")?.replace("mailto:", "") ||
      getText(".requester-email") ||
      getText('[data-test-id="requester-email"]') ||
      getText(".contact-email") ||
      null;

    // Status badge
    const status =
      getText(".ticket-status-badge") ||
      getText('[data-test-id="ticket-status"]') ||
      getText(".status-badge") ||
      getText(".ticket-status") ||
      null;

    // Priority badge
    const priority =
      getText(".ticket-priority-badge") ||
      getText('[data-test-id="ticket-priority"]') ||
      getText(".priority-badge") ||
      getText(".priority-label") ||
      null;

    return {
      source: SOURCE,
      ticket_number: ticketNumber,
      subject: subject,
      customer_name: customerName,
      customer_email: customerEmail,
      status: status,
      priority: priority,
      url: window.location.href,
    };
  }

  // ── Send context to background ─────────────────────────────────────────────

  function sendContext(context) {
    chrome.runtime.sendMessage(
      { type: "TICKET_CONTEXT", context },
      (response) => {
        if (chrome.runtime.lastError) {
          // Background may not be ready yet — that's fine
          console.debug("[Kodex/Freshdesk] sendMessage error:", chrome.runtime.lastError.message);
        } else {
          console.log("[Kodex/Freshdesk] Context sent, response:", response);
        }
      }
    );
  }

  // ── Trigger logic ──────────────────────────────────────────────────────────

  let lastSentTicket = null;
  let debounceTimer = null;

  function maybeSend() {
    const context = extractContext();
    if (!context) return;

    // Debounce: only send if ticket changed or 5s elapsed since last send
    if (context.ticket_number === lastSentTicket) return;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      lastSentTicket = context.ticket_number;
      console.log("[Kodex/Freshdesk] Sending context for ticket", context.ticket_number, context);
      sendContext(context);
    }, 800);
  }

  // Run on page load
  maybeSend();

  // Watch for SPA navigation (Freshdesk is a single-page app)
  // MutationObserver on the body catches route changes that update the DOM
  let navObserver = new MutationObserver(() => {
    maybeSend();
  });

  navObserver.observe(document.body, {
    childList: true,
    subtree: false, // just top-level is enough to catch major navigation
  });

  // Also watch URL changes (pushState / replaceState)
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastSentTicket = null; // Reset so the new ticket gets sent
      setTimeout(maybeSend, 500); // Wait for DOM to update
    }
  }, 500);

  // ── Send context when tab gains focus ────────────────────────────────────
  // This ensures switching between tickets updates the context immediately

  function forceSend() {
    lastSentTicket = null; // Reset so we always send
    maybeSend();
  }

  // Tab becomes visible (user switches to this tab)
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible") {
      console.log("[Kodex/Freshdesk] Tab became visible, refreshing context");
      setTimeout(forceSend, 100);
    }
  });

  // Window gains focus (user clicks into browser from another app)
  window.addEventListener("focus", () => {
    console.log("[Kodex/Freshdesk] Window focused, refreshing context");
    setTimeout(forceSend, 100);
  });

  console.log("[Kodex/Freshdesk] Content script loaded on", window.location.href);
})();
