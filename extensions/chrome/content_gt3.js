/**
 * Kodex Context Bridge — GT3 (Grid Tool 3) Content Script
 *
 * Extracts region/simulator context from Linden Lab's GT3 tool at:
 *   support-tools.agni.lindenlab.com/gridtool/region/{UUID}
 *
 * Sections: #region-summary, #billing, #simulator-host, #other-region-info
 * Table structure: <tr><th>Label</th><td>Value</td></tr>
 */

(function () {
  "use strict";

  const SOURCE = "gt3";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  /**
   * Get value from GT3 tables (uses <th> for labels, <td> for values)
   * Optionally scope to a specific widget section
   */
  function getTableValue(labelText, sectionId = null) {
    let tables;
    if (sectionId) {
      const section = document.getElementById(sectionId);
      if (!section) return null;
      tables = section.querySelectorAll("table.data");
    } else {
      tables = document.querySelectorAll("table.data.side_by_side");
    }

    for (const table of tables) {
      const rows = table.querySelectorAll("tr");
      for (const row of rows) {
        const th = row.querySelector("th");
        const td = row.querySelector("td");
        if (th && td) {
          const label = th.textContent.trim();
          if (label.toLowerCase() === labelText.toLowerCase()) {
            // Check for link inside
            const link = td.querySelector("a");
            if (link && link.textContent.trim()) {
              return link.textContent.trim();
            }
            return td.textContent.trim();
          }
        }
      }
    }
    return null;
  }

  /**
   * Get value from #customer-info sidebar
   */
  function getSidebarValue(labelText) {
    const sidebar = document.getElementById("customer-info");
    if (!sidebar) return null;

    const rows = sidebar.querySelectorAll("tr");
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

  function getUUIDFromURL() {
    // URL pattern: /gridtool/region/{UUID}
    const match = window.location.pathname.match(
      /\/gridtool\/region\/([a-f0-9-]{36})/i
    );
    return match ? match[1] : null;
  }

  // ── Context extraction ─────────────────────────────────────────────────────

  function extractContext() {
    const url = window.location.href;

    // Check if this is a GT3/gridtool page
    if (!url.includes("/gridtool/")) {
      return null;
    }

    // Extract UUID from URL
    const regionUuidFromUrl = getUUIDFromURL();

    // ── From sidebar ──
    const regionNameSidebar = getText("#customer-info span.region-name");
    const regionUuidSidebar = getText("#customer-info td.select_on_click");
    
    // Status from sidebar
    const statusEl = document.querySelector("#customer-info .region-status-up a, #customer-info .region-status-down a");
    const regionStatus = statusEl ? statusEl.textContent.trim() : null;
    const agentsText = getText("#customer-info .region-status-up .small-font, #customer-info .region-status-down .small-font");
    const agentCount = agentsText ? agentsText.replace(/[^0-9]/g, "") : null;

    // ── Region Summary section ──
    const regionName = getTableValue("Region Name", "region-summary") || regionNameSidebar;
    const estateName = getTableValue("Estate Name", "region-summary");
    const estateId = getTableValue("Estate ID", "region-summary");
    const parentEstate = getTableValue("Parent Estate", "region-summary");
    const gridCoords = getTableValue("Grid Coords", "region-summary");
    const owner = getTableValue("Owner", "region-summary");
    const altPayor = getTableValue("Alt Payor", "region-summary");

    // ── Billing section ──
    const description = getTableValue("Description", "billing");
    const product = getTableValue("Product", "billing");
    const sku = getTableValue("SKU", "billing");
    const billDate = getTableValue("Bill Date", "billing");
    const price = getTableValue("Price", "billing");

    // ── Simulator Host section ──
    const runningOn = getTableValue("Running On (PID:Host)", "simulator-host");
    const lastOn = getTableValue("Last On (PID:Host)", "simulator-host");
    const currentChannel = getTableValue("Current Channel", "simulator-host");
    const nextChannel = getTableValue("Next Channel", "simulator-host");
    const simClass = getTableValue("Class", "simulator-host");
    const simsCpu = getTableValue("Sims/CPU", "simulator-host");
    const updated = getTableValue("Updated", "simulator-host");
    const running = getTableValue("Running", "simulator-host");
    const lastSimstateSave = getTableValue("Last Simstate Save", "simulator-host");
    const hostPort = getTableValue("Host:Port", "simulator-host");

    // ── Other Region Info section ──
    const access = getTableValue("Access", "other-region-info");
    const maxAgents = getTableValue("Max Agents", "other-region-info");
    const hardMaxAgents = getTableValue("Hard Max Agents", "other-region-info");
    const isSandbox = getTableValue("Sandbox", "other-region-info");

    return {
      source: SOURCE,
      
      // Region identifiers
      region_uuid: regionUuidFromUrl || regionUuidSidebar,
      region_name: regionName,
      
      // Status
      status: regionStatus,
      agent_count: agentCount,
      
      // Estate info
      estate_name: estateName,
      estate_id: estateId,
      parent_estate: parentEstate,
      owner: owner,
      alt_payor: altPayor,
      
      // Location
      grid_coords: gridCoords,
      
      // Billing
      billing_description: description,
      product: product,
      sku: sku,
      bill_date: billDate,
      price: price,
      
      // Simulator
      running_on: runningOn,
      last_on: lastOn,
      current_channel: currentChannel,
      next_channel: nextChannel,
      sim_class: simClass,
      sims_cpu: simsCpu,
      updated: updated,
      running: running,
      last_simstate_save: lastSimstateSave,
      host_port: hostPort,
      
      // Region settings
      access: access,
      max_agents: maxAgents,
      hard_max_agents: hardMaxAgents,
      is_sandbox: isSandbox,
      
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
