# Kodex — Text Expansion & Support Workflow Engine

**Version 1.0.0** — A powerful text expansion engine built for support teams.

Kodex transforms short abbreviations into full responses, auto-fills ticket data from your browser, and tracks time spent on tickets — all from your system tray.

---

## Features

### 🚀 Text Expansion
- **Instant expansion** — Type abbreviations, press trigger key, text expands
- **Trie-based matching** — O(k) lookup, handles thousands of hotstrings
- **Direct keyboard injection** — No clipboard clobbering, smooth even for long text
- **Bundle system** — Organize hotstrings into categories, enable/disable per-bundle

### 🌐 Browser Integration (Chrome Extension)
- **Freshdesk** — Auto-extract ticket data, customer info, properties
- **CSR Tool** — Pull account details, balances, security questions
- **GT3** — Extract grid/region data
- **Real-time sync** — Variables update as you switch tickets

### ⏱️ Time Tracking
- **Automatic tracking** — Time logged per-ticket, per-day
- **AFK detection** — Pauses when workstation locked
- **CSV export** — Daily logs, weekly archives
- **Visual timer** — Floating overlay shows active ticket

### 🎨 Modern GUI
- **Dark theme** — Easy on the eyes (CustomTkinter)
- **System tray** — Lives quietly until needed
- **Management window** — Search, edit, organize hotstrings
- **Preferences** — Customize behavior, view stats

---

## Quick Start

### Download & Run (Windows)

1. Download the latest release from [Releases](https://github.com/SilverSix311/kodex/releases)
2. Extract to any folder
3. Run `kodex-gui.vbs` (silent) or `kodex-run.bat` (with console)
4. Look for the Kodex icon in your system tray

### Install Chrome Extension

1. Open `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `extensions/chrome/` folder from your Kodex installation
5. Configure native messaging (see [Chrome Extension Setup](#chrome-extension-setup))

---

## Variable Reference

### Built-in Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `%clipboard%` | Clipboard contents | (current clipboard) |
| `%time%` | Current time | `2:30 PM` |
| `%time_long%` | Long time format | `14:30:45 PM` |
| `%date_short%` | Short date | `2/23/2026` |
| `%date_long%` | Long date | `February 23, 2026` |
| `%prompt%` | Ask for input | Opens dialog |

### Freshdesk Variables (`%fd_*`)

Automatically populated when viewing a Freshdesk ticket:

**Contact Details:**
| Variable | Description |
|----------|-------------|
| `%fd_contact_name%` | Customer name |
| `%fd_account_status%` | Account status code |
| `%fd_account_type%` | Account type (Base, Premium, etc.) |
| `%fd_paid_support%` | Paid support level |
| `%fd_agent_id%` | Customer's agent/avatar ID |

**Ticket Properties:**
| Variable | Description |
|----------|-------------|
| `%fd_ticket_id%` | Ticket number |
| `%fd_subject%` | Ticket subject line |
| `%fd_status%` | Ticket status (Open, Pending, etc.) |
| `%fd_priority%` | Priority level |
| `%fd_type%` | Ticket type |
| `%fd_group%` | Assigned group |
| `%fd_agent%` | Assigned agent |

**Custom Fields:**
| Variable | Description |
|----------|-------------|
| `%fd_marketplace%` | Marketplace category |
| `%fd_marketplace_items%` | Item names |
| `%fd_marketplace_order_id%` | Order ID |
| `%fd_purchase_date%` | Purchase date |
| `%fd_purchase_time%` | Purchase time |
| `%fd_avatar_name%` | Avatar name |
| `%fd_error_message%` | Error message |
| `%fd_region_name%` | Region name |
| `%fd_store_name%` | Store name |
| `%fd_related_ticket%` | Related ticket number |
| `%fd_ip_address%` | Customer IP address |

**Requester Info:**
| Variable | Description |
|----------|-------------|
| `%fd_requester_name%` | Requester display name |
| `%fd_requester_email%` | Requester email |
| `%fd_cc_emails%` | CC'd email addresses |
| `%fd_ticket_description%` | Ticket body text |

### CSR Variables (`%csr_*`)

Populated from CSR tool pages:

| Variable | Description |
|----------|-------------|
| `%csr_url%` | CSR page URL |
| `%csr_usd_bal_due%` | USD balance due |
| `%csr_usd_balance%` | USD account balance |
| `%csr_security_question%` | Security question |
| `%csr_security_answer%` | Security answer |

### GT3 Variables (`%gt3_*`)

Populated from GT3 pages:

| Variable | Description |
|----------|-------------|
| `%gt3_grid%` | Grid name |
| `%gt3_region%` | Region name |
| `%gt3_estate%` | Estate name |
| `%gt3_coordinates%` | Region coordinates |

### Agent Info Variables (`%agent_*`)

Set in Preferences → Agent Info:

| Variable | Description |
|----------|-------------|
| `%agent_name%` | Your display name |
| `%agent_id%` | Your agent ID |
| `%agent_email%` | Your email |

### Time Tracking Variables

| Variable | Description |
|----------|-------------|
| `%ticket_time%` | Seconds on current ticket |
| `%ticket_time_formatted%` | Time as `HH:MM:SS` |

---

## Chrome Extension Setup

The Chrome extension captures ticket data and sends it to Kodex via native messaging.

### 1. Register the Native Host

Run this in PowerShell (as Administrator):

```powershell
# Find your Kodex installation path
$kodexPath = "C:\path\to\kodex"

# Create the native host manifest
$manifest = @{
    name = "com.kodex.context"
    description = "Kodex Context Bridge"
    path = "$kodexPath\extensions\chrome\native_host.bat"
    type = "stdio"
    allowed_origins = @("chrome-extension://YOUR_EXTENSION_ID/")
} | ConvertTo-Json

# Write manifest to registry location
$manifestPath = "$env:LOCALAPPDATA\Kodex\com.kodex.context.json"
New-Item -Path (Split-Path $manifestPath) -ItemType Directory -Force
$manifest | Out-File -FilePath $manifestPath -Encoding UTF8

# Register in Windows Registry
$regPath = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.kodex.context"
New-Item -Path $regPath -Force
Set-ItemProperty -Path $regPath -Name "(Default)" -Value $manifestPath
```

### 2. Get Your Extension ID

1. Go to `chrome://extensions/`
2. Find "Kodex Context Bridge"
3. Copy the ID (looks like `abcdefghijklmnopqrstuvwxyz123456`)
4. Update the `allowed_origins` in the manifest above

### 3. Reload & Test

1. Reload the extension in `chrome://extensions/`
2. Open a Freshdesk ticket
3. Check Kodex → Tools → View Variables
4. You should see `%fd_*` variables populated

---

## Time Tracking

### How It Works

1. **Automatic detection** — When you view a Freshdesk ticket, tracking starts
2. **Per-ticket, per-day** — Time is logged separately for each ticket each day
3. **AFK-aware** — Tracking pauses when your workstation is locked
4. **Shift cutoff** — Tracking stops at 5:50 PM (configurable)

### Viewing Time

- **Tray menu** → Time Tracking — Opens the time tracking window
- **Daily totals** — See time per ticket for any date
- **Export CSV** — Download logs for reporting

### Time Tracking Window

| Column | Description |
|--------|-------------|
| Ticket | Ticket number |
| Time | Total time (HH:MM:SS) |
| Source | Where it came from (freshdesk, csr, gt3) |
| Last Seen | Last activity timestamp |

---

## GUI Reference

### System Tray Menu

| Menu Item | Action |
|-----------|--------|
| Manage Hotstrings | Open management window |
| Create New Hotstring | Quick-add dialog |
| Preferences | Settings, stats, agent info |
| Start Ticket Tracker | Manual tracking toggle |
| Time Tracking | View/export time logs |
| Disable/Enable | Toggle all hotstrings |
| Exit | Quit Kodex |

### Management Window

- **Tabs** — One per bundle (Default, CSR Notes, etc.)
- **Search** — Filter by name or replacement text
- **Edit** — Click a hotstring to modify
- **Triggers** — Space, Tab, Enter, or Instant
- **Script Mode** — For complex expansions with logic

### Preferences Window

- **General** — Hotkeys, sounds, startup behavior
- **Agent Info** — Your name, ID, email for `%agent_*` variables
- **Statistics** — Expansions count, characters saved

### View Variables (Tools Menu)

Shows all currently available variables:
- Built-in (`%clipboard%`, `%time%`, etc.)
- Freshdesk context (`%fd_*`)
- CSR context (`%csr_*`)
- GT3 context (`%gt3_*`)
- Global variables (user-defined)

---

## CLI Reference

```bash
kodex run                         # Start engine + tray
kodex list                        # List all hotstrings
kodex add NAME REPLACEMENT        # Add hotstring
kodex remove NAME                 # Remove hotstring
kodex bundles                     # List bundles
kodex bundle-create NAME          # Create bundle
kodex bundle-toggle NAME          # Enable/disable bundle
kodex stats                       # Show statistics
kodex cheatsheet [FILE]           # Generate HTML reference
kodex time-log [-d DATE]          # View time log
```

---

## File Locations

### Portable Mode (Recommended)

When running from the distribution folder:

```
kodex/
├── data/
│   ├── kodex.db                  # Hotstring database
│   ├── freshdesk_context.json    # Current Freshdesk data
│   ├── csr_context.json          # Current CSR data
│   ├── gt3_context.json          # Current GT3 data
│   ├── time_tracking.json        # Time tracking state
│   ├── global_variables.json     # User-defined variables
│   ├── agent_info.json           # Agent preferences
│   └── timeTracker/              # CSV exports
├── extensions/
│   └── chrome/                   # Browser extension
├── python/                       # Embedded Python runtime
├── app/                          # Application code
└── kodex-gui.vbs                 # Launch script
```

### Installed Mode

When installed system-wide, data goes to:
- Windows: `%USERPROFILE%\.kodex\`
- Linux/macOS: `~/.kodex/`

---

## Hotkeys

| Hotkey | Action |
|--------|--------|
| `Ctrl+Shift+H` | Create new hotstring |
| `Ctrl+Shift+M` | Open management window |
| `Ctrl+Shift+T` | Toggle ticket tracker |

---

## Building from Source

### Requirements

- Python 3.11+
- Windows 10+ (for full functionality)
- tkinter (included with Python on Windows)

### Development Setup

```bash
git clone https://github.com/SilverSix311/kodex.git
cd kodex
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
kodex run
```

### Build Portable Distribution

```cmd
build.bat
```

Creates `dist/kodex/` with embedded Python — zip and distribute.

See [BUILD.md](BUILD.md) for detailed build instructions.

---

## Troubleshooting

### Variables not populating

1. Check the Chrome extension is loaded and enabled
2. Refresh the Freshdesk/CSR/GT3 page
3. Check Tools → View Variables in Kodex
4. Look at `data/native_messaging.log` for errors

### Time not tracking

1. Ensure Kodex is running (check system tray)
2. Make sure it's before 5:50 PM
3. Check if workstation was locked (pauses tracking)
4. View Time Tracking window for current state

### Hotstrings not expanding

1. Check if Kodex is enabled (tray icon should be normal, not grayed)
2. Verify the trigger key (Space, Tab, Enter, or Instant)
3. Check if the bundle is enabled
4. Try restarting Kodex

### Chrome extension not connecting

1. Verify native host is registered (check Registry)
2. Check the extension ID matches `allowed_origins`
3. Look at `data/native_messaging.log`
4. Try reloading the extension

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Credits

Built by [SilverSix311](https://github.com/SilverSix311) with assistance from [Silas Vane](https://github.com/SilasVane).

Originally inspired by AutoHotkey, rebuilt in Python for portability and extensibility.
