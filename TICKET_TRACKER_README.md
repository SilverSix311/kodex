# Kodex Freshdesk Ticket Time Tracker

**Version**: 1.0.0  
**Status**: ✅ Complete  
**Feature Type**: Time tracking utility for Freshdesk ticket management

## Overview

The Kodex Freshdesk Ticket Time Tracker is an integrated feature that helps you track time spent on support tickets. It monitors Freshdesk ticket URLs and logs time entries to dated CSV files for reporting and analysis.

## Features

✅ **URL Detection**: Automatically detects Freshdesk ticket URLs from clipboard or selection  
✅ **Time Logging**: Records start/stop times with automatic duration calculation  
✅ **Overlay Timer**: Displays transparent, non-intrusive timer overlay while tracking  
✅ **CSV Export**: Logs entries to dated CSV files organized by username  
✅ **Hotkey Control**: Simple hotkey toggle (Ctrl+Shift+T) to start/stop tracking  
✅ **Date-Based Files**: Automatic organization into daily CSV files (USERNAME.MMDD.csv)

## Installation

### Prerequisites
- Kodex (v2.0 or later)
- AutoHotkey v2

### Setup
1. The ticketTracker.ahk is included in `includes/functions/`
2. To enable, add this line to your main script initialization:
```autohotkey
#Include %A_ScriptDir%\includes\functions\ticketTracker.ahk
```

### Configuration
Edit the configuration section in ticketTracker.ahk:
```autohotkey
; Default hotkey: Ctrl+Shift+T
global TicketHotkey := "^+t"
```

## Usage

### Basic Workflow

1. **Copy or Select a Freshdesk Ticket URL**
   ```
   https://lindenlab.freshdesk.com/a/tickets/12345
   ```

2. **Press Hotkey** (Ctrl+Shift+T)
   - Timer overlay appears showing ticket number
   - Elapsed time updates every second
   - CSV entry logged with start time

3. **Press Hotkey Again** to Stop Tracking
   - Timer overlay closes
   - End time and duration logged to CSV
   - Success message shows total hours tracked

### Output Format

**Directory**: `timeTracker/` (created automatically)

**Filename Format**: `[USERNAME].[MMDD].csv`
- Example: `john.doe.0129.csv` (January 29th)

**CSV Columns**:
| Field | Description | Example |
|-------|-------------|---------|
| Ticket # | Freshdesk ticket number | 12345 |
| Status | Started or Finished | Started |
| Timestamp | Date and time | 2026-01-29 14:30:45 |
| Duration | Hours tracked (if finished) | 2.50 |

**Sample CSV Content**:
```csv
12345,Started,2026-01-29 14:30:45,
12345,Finished,2026-01-29 17:15:22,2.75
12346,Started,2026-01-29 17:16:00,
12346,Finished,2026-01-29 18:45:30,1.49
```

## Features in Detail

### 1. Automatic URL Detection

The tracker uses regex pattern matching to detect Freshdesk URLs:
```regex
https://lindenlab\.freshdesk\.com/a/tickets/(\d+)
```

**Supported URL Formats**:
- Direct ticket URL: `https://lindenlab.freshdesk.com/a/tickets/12345`
- Any page containing the URL

### 2. Overlay Timer

**Position**: Left side of screen (25% width)  
**Transparency**: Fully opaque for visibility  
**Update Interval**: 1 second  
**Format**: `HH:MM:SS` (Hours:Minutes:Seconds)

**Styling**:
- Background: Dark gray (#1e1e1e)
- Text Color: White
- Ticket Number: Centered at top
- Timer Display: Centered in green

### 3. CSV Logging

**Auto-Organization**:
- One file per user per day
- Format: `[USERNAME].[MMDD].csv`
- Example: `silver_six311.0129.csv`

**Timestamp Format**: `YYYY-MM-DD HH:MM:SS`  
**Duration Format**: Decimal hours (2.50 = 2 hours 30 minutes)

### 4. Hotkey Integration

**Default Hotkey**: `Ctrl+Shift+T` (^+t)

**To Change**: Edit the configuration:
```autohotkey
global TicketHotkey := "^+f"  ; Ctrl+F instead
```

**Hotkey Syntax**:
| Modifier | Symbol |
|----------|--------|
| Ctrl | ^ |
| Shift | + |
| Alt | ! |
| Win | # |

**Examples**:
- `^+t` = Ctrl+Shift+T
- `!t` = Alt+T
- `#t` = Win+T

## API Reference

### Functions

#### `StartTicketTracking()`
Initiates time tracking for a ticket.
- Detects URL from clipboard
- Logs start time to CSV
- Shows overlay timer
- **Returns**: Nothing (shows error dialog if URL not found)

#### `StopTicketTracking()`
Stops current tracking session.
- Logs end time and duration
- Destroys overlay timer
- Shows success message with duration
- **Returns**: Nothing

#### `LogTicketEntry(TicketNumber, Status, Timestamp, Duration := "")`
Logs a single entry to the CSV file.

**Parameters**:
- `TicketNumber`: Freshdesk ticket ID
- `Status`: "Started" or "Finished"
- `Timestamp`: AHK format timestamp (YYYYMMDDHHMMSS)
- `Duration`: Hours tracked (optional)

#### `ShowTicketTimerOverlay(TicketNumber, StartTime)`
Displays the transparent timer overlay.

**Parameters**:
- `TicketNumber`: Ticket ID to display
- `StartTime`: Timestamp when tracking started

#### `UpdateTicketTimer()`
Timer callback that updates the overlay display every second.

#### `DateTimeToUnix(Timestamp)`
Converts AHK timestamp format to Unix epoch time.

**Parameters**:
- `Timestamp`: AHK format timestamp

**Returns**: Unix timestamp (seconds since 1970-01-01)

## Troubleshooting

### Issue: "Ticket URL Not Found"
**Solution**: 
1. Ensure the full Freshdesk URL is copied to clipboard
2. URL must be in format: `https://lindenlab.freshdesk.com/a/tickets/[NUMBER]`
3. Copy directly from browser address bar if possible

### Issue: CSV Files Not Created
**Solution**:
1. Check that `timeTracker/` directory exists
2. Verify write permissions to the directory
3. Ensure username is set in Windows environment
4. Check log for error messages

### Issue: Timer Overlay Not Visible
**Solution**:
1. Check screen resolution
2. Overlay appears at left side, 25% of screen width
3. Try moving other windows to expose it
4. Increase overlay size in code (modify OverlayWidth calculation)

### Issue: Hotkey Not Responding
**Solution**:
1. Check if hotkey is disabled by another application
2. Try different hotkey combination
3. Verify hotkey syntax (e.g., `^+t` is Ctrl+Shift+T)
4. Restart Kodex application

## CSV Data Analysis

### Open in Excel
1. Place CSV file in a folder
2. Open Excel
3. File → Open → Select CSV file
4. Choose comma delimiter
5. Columns auto-populate

### Calculate Daily Totals
```excel
=SUMIF(B:B,"Finished",D:D)
```

### Filter by Date
Use Excel filters on timestamp column

### Export to Reports
1. Copy CSV to analysis tool
2. Group by date or ticket
3. Generate reports

## Advanced Usage

### Batch Import from Multiple Files
Create a consolidation script to merge multiple `.csv` files into a master report.

### Integration with External Tools
CSV format makes it easy to import into:
- Time tracking software (Toggl, Harvest, etc.)
- Project management tools
- Excel/Google Sheets
- Business intelligence tools

### Custom Reporting
Use the CSV data to create:
- Daily time reports
- Per-ticket analysis
- Productivity metrics
- Billing records

## Limitations

- **Single Session**: Can only track one ticket at a time
- **Exact Regex Match**: URL format must be exact
- **Manual Start/Stop**: No automatic detection of active ticket
- **Local Storage**: CSV files stored locally only
- **No Backup**: No automatic backup of CSV files

## Future Enhancements

Potential improvements for future versions:
- [ ] Multi-ticket tracking
- [ ] Pause/resume functionality
- [ ] Cloud sync to shared drive
- [ ] Automatic report generation
- [ ] Slack/Teams integration
- [ ] Break timer
- [ ] Manual time entry UI
- [ ] Ticket validation API
- [ ] Custom file locations
- [ ] Auto-detection of active ticket

## Data Privacy

⚠️ **Important**: 
- CSV files contain your username and work times
- Files are stored locally in the `timeTracker/` directory
- No data is sent to external servers
- You have full control over the data

## Support

For issues or feature requests:
1. Check this documentation
2. Review the troubleshooting section
3. Open an issue on GitHub with details
4. Include relevant CSV entries if applicable

## License

Part of Kodex project. See main LICENSE file.

---

**Version**: 1.0.0  
**Last Updated**: January 2026  
**Status**: Production Ready
