/**
 * Kodex Context Bridge — CSR Content Script
 *
 * Extracts customer context from Linden Lab's CSR tool at:
 *   support-tools.agni.lindenlab.com/csr/summary/{UUID}/?view=csr-concierge
 *
 * Fields extracted from #customer-info sidebar:
 *   - customer_id, agent_id, account_id, persona_id, tilia_wallet_id, real_name
 * Additional fields from page content:
 *   - avatar_name (from header), email, display_name, account_status, etc.
 * From Security Questions dialog (when opened):
 *   - security_question (question only, not answer)
 */

(function () {
  "use strict";

  const SOURCE = "csr";
  
  // Cache for security question (persists until page reload)
  let cachedSecurityQuestion = null;

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  /**
   * Get value from #customer-info sidebar table
   * Structure: <tr><td class="right">Label</td><td class="left">Value</td></tr>
   */
  function getCustomerInfoValue(labelText) {
    const table = document.querySelector("#customer-info table.short-customer-desc");
    if (!table) return null;

    const rows = table.querySelectorAll("tr");
    for (const row of rows) {
      const cells = row.querySelectorAll("td");
      if (cells.length >= 2) {
        const label = cells[0].textContent.trim();
        if (label.toLowerCase().includes(labelText.toLowerCase())) {
          return cells[1].textContent.trim();
        }
      }
    }
    return null;
  }

  /**
   * Get value from main content tables (Useful Info, All Fields sections)
   * Structure: <tr><th>Label</th><td>Value</td></tr>
   */
  function getTableValue(labelText) {
    const tables = document.querySelectorAll("table.data.side_by_side");
    for (const table of tables) {
      const rows = table.querySelectorAll("tr");
      for (const row of rows) {
        const th = row.querySelector("th");
        const td = row.querySelector("td");
        if (th && td) {
          const label = th.textContent.trim();
          if (label.toLowerCase().includes(labelText.toLowerCase())) {
            // Check for link inside
            const link = td.querySelector("a");
            if (link) {
              return link.textContent.trim();
            }
            return td.textContent.trim();
          }
        }
      }
    }
    return null;
  }

  function getUUIDFromURL() {
    // URL pattern: /csr/summary/{UUID}/ or /csr/summary/{UUID}/?view=...
    const match = window.location.pathname.match(
      /\/csr\/(?:summary|detail|view)\/([a-f0-9]{32})/i
    );
    return match ? match[1] : null;
  }

  /**
   * Extract security question from the Security Questions dialog.
   * Format: <li class="active_entry">Question text - <span class="answer">Answer</span>
   * Returns just the question part.
   */
  function extractSecurityQuestion() {
    // Look for the Security Questions dialog
    const dialogs = document.querySelectorAll(".ui-dialog");
    for (const dialog of dialogs) {
      const title = dialog.querySelector(".ui-dialog-title");
      if (title && title.textContent.trim() === "Security Questions") {
        // Found the dialog — look for active question
        const activeEntry = dialog.querySelector("li.active_entry");
        if (activeEntry) {
          // Get the full text content
          const fullText = activeEntry.textContent.trim();
          // Split on " - " to separate question from answer
          const parts = fullText.split(" - ");
          if (parts.length >= 1) {
            // Return just the question (first part)
            return parts[0].trim();
          }
        }
      }
    }
    return null;
  }

  // ── Context extraction ─────────────────────────────────────────────────────

  function extractContext() {
    const url = window.location.href;

    // Check if this is a CSR page
    if (!url.includes("/csr/")) {
      return null;
    }

    // Extract UUID from URL
    const customerIdFromUrl = getUUIDFromURL();

    // ── From #customer-info sidebar ──
    const customerId = getCustomerInfoValue("Customer ID") || customerIdFromUrl;
    const agentId = getCustomerInfoValue("Agent ID");
    const accountId = getCustomerInfoValue("Account ID");
    const personaId = getCustomerInfoValue("Persona ID");
    const tiliaWalletId = getCustomerInfoValue("Tilia Wallet ID");
    const realName = getCustomerInfoValue("Real Name");

    // ── From page header ──
    // Header format: "Klyde.Linden - Summary"
    const headerText = getText("#global-header h2");
    let avatarName = null;
    if (headerText) {
      const match = headerText.match(/^([^\s-]+)/);
      if (match) {
        avatarName = match[1];
      }
    }

    // ── From content tables ──
    const displayName = getTableValue("Display Name");
    const email = getTableValue("Email");
    const accountStatus = getTableValue("Account Status");
    const accountType = getTableValue("Account Type");
    const serviceLevel = getTableValue("Default Service Level");
    const lindenBalance = getTableValue("L$ Balance");
    const usdBalance = getTableValue("US Dollar Balance");
    const lastLogin = getTableValue("Last Login");
    const createdDate = getTableValue("Created Date");

    // Also grab from "resident" link if available
    const residentLink = document.querySelector(".resident a.type-person");
    if (!avatarName && residentLink) {
      avatarName = residentLink.textContent.trim();
    }
    
    // ── Security question (from cache or dialog) ──
    const securityQuestion = cachedSecurityQuestion || extractSecurityQuestion();

    return {
      source: SOURCE,
      
      // Primary identifiers
      customer_id: customerId,
      agent_id: agentId,
      account_id: accountId,
      persona_id: personaId,
      tilia_wallet_id: tiliaWalletId,
      
      // Names
      real_name: realName,
      avatar_name: avatarName,
      display_name: displayName,
      
      // Account info
      email: email,
      account_status: accountStatus,
      account_type: accountType,
      service_level: serviceLevel,
      security_question: securityQuestion,
      
      // Balances
      linden_balance: lindenBalance,
      usd_balance: usdBalance,
      
      // Dates
      last_login: lastLogin,
      created_date: createdDate,
      
      // Meta
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
  let lastSentQuestion = null;
  let debounceTimer = null;

  function maybeSend(forceUpdate = false) {
    const context = extractContext();
    if (!context) return;

    const currentUrl = window.location.href;
    const currentQuestion = context.security_question;
    
    // Send if URL changed, or if security question was newly captured
    const urlChanged = currentUrl !== lastSentUrl;
    const questionChanged = currentQuestion && currentQuestion !== lastSentQuestion;
    
    if (!urlChanged && !questionChanged && !forceUpdate) return;

    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      lastSentUrl = currentUrl;
      if (currentQuestion) {
        lastSentQuestion = currentQuestion;
      }
      console.log("[Kodex/CSR] Sending context:", context);
      sendContext(context);
    }, 300);
  }

  // Run on page load
  maybeSend();

  // Watch for SPA navigation
  let lastUrl = window.location.href;
  setInterval(() => {
    if (window.location.href !== lastUrl) {
      lastUrl = window.location.href;
      lastSentUrl = null;
      lastSentQuestion = null;
      cachedSecurityQuestion = null;
      setTimeout(maybeSend, 500);
    }
  }, 500);

  // ── Watch for Security Questions dialog ────────────────────────────────────
  
  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (node.nodeType === Node.ELEMENT_NODE) {
          // Check if this is a dialog or contains a dialog
          const dialog = node.classList?.contains("ui-dialog") 
            ? node 
            : node.querySelector?.(".ui-dialog");
          
          if (dialog) {
            const title = dialog.querySelector(".ui-dialog-title");
            if (title && title.textContent.trim() === "Security Questions") {
              console.log("[Kodex/CSR] Security Questions dialog detected");
              
              // Wait a moment for the dialog content to fully render
              setTimeout(() => {
                const question = extractSecurityQuestion();
                if (question) {
                  console.log("[Kodex/CSR] Captured security question:", question);
                  cachedSecurityQuestion = question;
                  maybeSend(true);
                }
              }, 200);
            }
          }
        }
      }
    }
  });

  // Start observing for dialogs
  observer.observe(document.body, {
    childList: true,
    subtree: true,
  });

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
