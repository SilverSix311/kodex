/**
 * Kodex Context Bridge — GT3 (Grid Tool 3) Content Script
 *
 * Extracts region/simulator context from Linden Lab's GT3 tool at:
 *   support-tools.agni.lindenlab.com/gridtool/region/{UUID}
 *
 * Fields extracted:
 *   Region Summary: region_name, region_uuid, estate_name, estate_id,
 *                   parent_estate, grid_coords, owner, alt_payor
 *   Billing: description, product, sku, bill_date, price
 *   Simulator Host: running_on, current_channel, next_channel, class,
 *                   sims_cpu, updated, last_simstate_save
 */

(function () {
  "use strict";

  const SOURCE = "gt3";

  // ── Helpers ────────────────────────────────────────────────────────────────

  function getText(selector) {
    const el = document.querySelector(selector);
    return el ? el.textContent.trim() : null;
  }

  function getTableValue(labelText) {
    // GT3 uses tables with label in first column, value in second
    // Pattern: <tr><td>Region Name</td><td>Hawt Pink (M)</td></tr>
    const rows = document.querySelectorAll("tr");
    for (const row of rows) {
      const cells = row.querySelectorAll("td, th");
      if (cells.length >= 2) {
        const label = cells[0].textContent.trim();
        if (label.toLowerCase() === labelText.toLowerCase() ||
            label.toLowerCase().includes(labelText.toLowerCase())) {
          // Get the value from the next cell (or second cell)
          const valueCell = cells[1];
          // Check if there's a link inside
          const link = valueCell.querySelector("a");
          if (link) {
            return link.textContent.trim();
          }
          return valueCell.textContent.trim();
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

    // ── Region Summary ──
    const regionName = getTableValue("Region Name");
    const estateName = getTableValue("Estate Name");
    const estateId = getTableValue("Estate ID");
    const parentEstate = getTableValue("Parent Estate");
    const gridCoords = getTableValue("Grid Coords");
    const owner = getTableValue("Owner");
    const altPayor = getTableValue("Alt Payor");

    // ── Billing ──
    const description = getTableValue("Description");
    const product = getTableValue("Product");
    const sku = getTableValue("SKU");
    const billDate = getTableValue("Bill Date");
    const price = getTableValue("Price");

    // ── Simulator Host ──
    const runningOn = getTableValue("Running On");
    const lastOn = getTableValue("Last On");
    const currentChannel = getTableValue("Current Channel");
    const nextChannel = getTableValue("Next Channel");
    const simClass = getTableValue("Class");
    const simsCpu = getTableValue("Sims/CPU");
    const updated = getTableValue("Updated");
    const lastSimstateSave = getTableValue("Last Simstate Save");

    // Extract region name from page title as fallback
    // "Hawt Pink Region Summary" → "Hawt Pink"
    let regionNameFromTitle = null;
    const titleMatch = document.title.match(/^(.+?)\s+Region\s+Summary/i);
    if (titleMatch) {
      regionNameFromTitle = titleMatch[1];
    }

    // Get header info for additional context
    const pageHeader = getText("h1, h2, .page-title");

    return {
      source: SOURCE,
      
      // Region identifiers
      region_uuid: regionUuidFromUrl,
      region_name: regionName || regionNameFromTitle,
      
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
      last_simstate_save: lastSimstateSave,
      
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
