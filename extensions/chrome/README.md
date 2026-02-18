# Kodex Context Bridge — Chrome Extension

Captures ticket context from Freshdesk, CSR, and GT3 and sends it to
the Kodex application via Chrome's native messaging API.

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest (Manifest V3) |
| `background.js` | Service worker — manages native messaging connection |
| `content_freshdesk.js` | Content script for `*.freshdesk.com` |
| `content_csr.js` | Content script for `csr.lindenlab.com` (placeholder) |
| `content_gt3.js` | Content script for `gt3.lindenlab.com` (placeholder) |
| `popup.html` / `popup.js` | Extension popup showing connection status |
| `com.kodex.context.json` | Native messaging host manifest |
| `install_host.bat` | Windows installer — registers the native host |
| `native_host.bat` | Windows launcher for the Python native host |

## Installation

### 1. Load the Extension in Chrome

1. Open Chrome → `chrome://extensions`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `extensions/chrome/` folder
5. Note the **Extension ID** displayed below the extension name

### 2. Install the Native Messaging Host (Windows)

Run as a regular user (no admin required):

```bat
cd extensions\chrome
install_host.bat <YOUR_EXTENSION_ID>
```

Or run `install_host.bat` without arguments and paste the ID when prompted.

This will:
- Update `com.kodex.context.json` with your extension ID and the full path to `native_host.bat`
- Register the registry key: `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.kodex.context`

### 3. Run Kodex

Make sure Kodex is running. The native host is launched on-demand by Chrome
when the extension first connects.

## How It Works

```
Freshdesk/CSR/GT3 page
   │  (DOM extraction)
   ▼
content_*.js
   │  chrome.runtime.sendMessage({ type: "TICKET_CONTEXT", context })
   ▼
background.js (service worker)
   │  chrome.runtime.connectNative("com.kodex.context")
   │  port.postMessage(payload)
   ▼
native_host.bat → python -m kodex_py.native_messaging
   │  reads stdin (length-prefixed JSON)
   ▼
~/.kodex/freshdesk_context.json  ← Kodex reads this file
```

## Data Written

The native host writes to `~/.kodex/freshdesk_context.json`:

```json
{
  "freshdesk": {
    "source": "freshdesk",
    "ticket_number": "12345",
    "subject": "Unable to log in",
    "customer_name": "Jane Doe",
    "customer_email": "jane@example.com",
    "status": "Open",
    "priority": "High",
    "_saved_at": "2026-02-18T14:30:00"
  },
  "_latest": { ... same as most recently updated source ... },
  "_updated_at": "2026-02-18T14:30:00"
}
```

## Troubleshooting

- **"Not connected" in popup** → Make sure `install_host.bat` was run and Kodex is installed
- **Extension ID mismatch** → Re-run `install_host.bat` with the correct ID
- **Logs** → Check `~/.kodex/native_messaging.log` for Python-side errors
- **Registry** → Check `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.kodex.context` exists

## Refining CSR/GT3 Selectors

The CSR and GT3 content scripts use placeholder selectors. Once you have access
to the actual tools, open DevTools on those pages and update the selectors in
`content_csr.js` and `content_gt3.js`.
