/**
 * Kodex Context Bridge — Freshdesk Content Script
 *
 * Extracts ticket context from Freshdesk ticket detail pages and
 * sends it to the background service worker.
 *
 * Extracted fields (26 total):
 *   Contact Details:
 *     - contact_name, account_status, account_type, paid_support, agent_id
 *   Ticket Properties:
 *     - type, marketplace, marketplace_items, marketplace_order_id
 *     - purchase_date, purchase_time, avatar_name, error_message
 *     - region_name, store_name, status, priority, group, agent
 *     - related_ticket, ip_address
 *   Ticket Header:
 *     - ticket_id, subject
 *   Requester/Conversation:
 *     - requester_name, requester_email, cc_emails, ticket_description
 */

(function () {
  "use strict";

  const SOURCE = "freshdesk";
  
  // ── Timing configuration ───────────────────────────────────────────────────
  const INITIAL_DELAY_MS = 800;
  const FOCUS_DELAY_MS = 500;
  const SPA_NAV_DELAY_MS = 800;
  const DEBOUNCE_MS = 800;

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getTicketNumber() {
    const match = window.location.pathname.match(/tickets?\/(\d+)/i);
    return match ? match[1] : null;
  }

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  function getInputValue(selector) {
    const el = document.querySelector(selector);
    return el ? (el.value || "").trim() : null;
  }

  function getAttr(selector, attr) {
    const el = document.querySelector(selector);
    return el ? (el.getAttribute(attr) || "").trim() : null;
  }

  // Get text from contact details widget by field name
  function getContactField(fieldName) {
    const selector = `[data-test-id="requester-info-contact-${fieldName}"] .info-details-content`;
    return getText(selector);
  }

  // Get dropdown selection from ticket properties
  function getPropertyDropdown(testId) {
    const selector = `[data-test-id="tkt-properties-${testId}"] .ember-power-select-selected-item`;
    return getText(selector);
  }

  // Get dropdown from generic data-test-id
  function getDropdown(testId) {
    const selector = `[data-test-id="${testId}"] .ember-power-select-selected-item`;
    let text = getText(selector);
    // If no selection, check for placeholder
    if (!text) {
      const placeholder = getText(`[data-test-id="${testId}"] .custom-placeholder`);
      if (placeholder && placeholder !== "--") text = placeholder;
    }
    return text;
  }

  // ── Context extraction ─────────────────────────────────────────────────────

  function extractContext() {
    const ticketNumber = getTicketNumber();
    if (!ticketNumber) return null;

    // ── Contact Details (right sidebar widget) ───────────────────────────────
    const contactName = 
      getText(".widget-requestor-info") ||
      getText('[data-test-id="user-name"]') ||
      null;
    
    const accountStatus = getContactField("account_status");
    const accountType = getContactField("account_type");
    const paidSupport = getContactField("paid_support");
    const agentId = getContactField("agent_id");

    // ── Ticket Properties (left sidebar form) ────────────────────────────────
    const ticketType = getPropertyDropdown("ticket_type");
    const marketplace = getPropertyDropdown("marketplace");
    const marketplaceItems = getInputValue('input[name="customFields.marketplace_items"]');
    const marketplaceOrderId = getInputValue('input[name="customFields.marketplace_order_id"]');
    const purchaseDate = getInputValue('input[name="customFields.purchase_date"]') ||
                         getAttr('input[id^="freshcalendar-input"]', 'aria-label');
    const purchaseTime = getInputValue('input[name="customFields.purchase_time"]');
    const avatarName = getInputValue('input[name="customFields.avatar_name"]');
    const errorMessage = getInputValue('input[name="customFields.error_message"]');
    const regionName = getInputValue('input[name="customFields.region_name"]');
    const storeName = getInputValue('input[name="customFields.cf_store_name"]');
    const relatedTicket = getInputValue('input[name="customFields.related_ticket_number"]');
    const ipAddress = getInputValue('input[name="customFields.ip_address"]');

    const status = getPropertyDropdown("status") ||
                   getText('[data-test-id="ticket-status"]');
    
    const priority = getDropdown("priority") ||
                     getText('[data-test-id="ticket-priority"]');
    
    const group = getDropdown("Group");
    const agent = getDropdown("Agent");

    // ── Ticket Header ────────────────────────────────────────────────────────
    const subject = 
      getText(".ticket-subject-heading") ||
      getText('[data-test-id="ticket-title"]') ||
      document.title.replace(/^\[#\d+\]\s*/, "").trim() ||
      null;

    // ── Requester / Conversation ─────────────────────────────────────────────
    const requesterName = 
      getText('.sender-info [data-test-id="user-name"]') ||
      getText('.requester-wrap [data-test-id="user-name"]') ||
      contactName;
    
    // Email often derived from agent_id for SL
    const requesterEmail = 
      getAttr('a[href^="mailto:"]', "href")?.replace("mailto:", "") ||
      (agentId ? `${agentId}@secondlife.com` : null);
    
    const ccEmails = getText('.emails-info .display_emails');
    
    const ticketDescription = getText('#ticket_original_request');

    return {
      source: SOURCE,
      url: window.location.href,
      
      // Ticket Header
      ticket_id: ticketNumber,
      subject: subject,
      
      // Contact Details
      contact_name: contactName,
      account_status: accountStatus,
      account_type: accountType,
      paid_support: paidSupport,
      agent_id: agentId,
      
      // Ticket Properties
      type: ticketType,
      marketplace: marketplace,
      marketplace_items: marketplaceItems,
      marketplace_order_id: marketplaceOrderId,
      purchase_date: purchaseDate,
      purchase_time: purchaseTime,
      avatar_name: avatarName,
      error_message: errorMessage,
      region_name: regionName,
      store_name: storeName,
      status: status,
      priority: priority,
      group: group,
      agent: agent,
      related_ticket: relatedTicket,
      ip_address: ipAddress,
      
      // Requester / Conversation
      requester_name: requesterName,
      requester_email: requesterEmail,
      cc_emails: ccEmails,
      ticket_description: ticketDescription,
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
    }, DEBOUNCE_MS);
  }

  // ── Run on page load ───────────────────────────────────────────────────────
  // Delay initial extraction to ensure page content is fully rendered
  
  setTimeout(maybeSend, INITIAL_DELAY_MS);

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
      setTimeout(maybeSend, SPA_NAV_DELAY_MS); // Wait for DOM to update
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
      setTimeout(forceSend, FOCUS_DELAY_MS);
    }
  });

  // Window gains focus (user clicks into browser from another app)
  window.addEventListener("focus", () => {
    console.log("[Kodex/Freshdesk] Window focused, refreshing context");
    setTimeout(forceSend, FOCUS_DELAY_MS);
  });

  console.log("[Kodex/Freshdesk] Content script loaded on", window.location.href);
})();
