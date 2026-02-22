"""Kodex Native Messaging Host — com.kodex.context

Implements Chrome's native messaging protocol (stdio, length-prefixed JSON).

Protocol:
  Chrome → Host : 4-byte little-endian length + UTF-8 JSON bytes
  Host → Chrome : same format

On each message received from the extension:
  1. Parse the JSON context payload
  2. Write/update {source}_context.json for that source
  3. Update time_tracking.json
  4. Respond with {"success": true} or {"success": false, "error": "..."}

Usage (not normally called directly — Chrome launches via native_host.bat):
  python -m kodex_py.native_messaging
"""

from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import struct
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ── Determine data directory (portable vs installed mode) ──

def _get_data_dir() -> Path:
    """Get the Kodex data directory, respecting portable mode."""
    kodex_root = os.environ.get("KODEX_ROOT")
    if kodex_root:
        portable_data = Path(kodex_root) / "data"
        # Use portable location if it exists OR if there's no home config yet
        home_data = Path.home() / ".kodex"
        if portable_data.exists() or not home_data.exists():
            portable_data.mkdir(parents=True, exist_ok=True)
            return portable_data

    # Fall back to home directory
    data_dir = Path.home() / ".kodex"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

_DATA_DIR = _get_data_dir()

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(_DATA_DIR / "native_messaging.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("kodex.native_messaging")

# ── Known sources ──────────────────────────────────────────────────────────────

KNOWN_SOURCES = ("freshdesk", "csr", "gt3")

TIME_TRACKING_FILE = _DATA_DIR / "time_tracking.json"


def _context_file(source: str) -> Path:
    """Return the context file path for a given source."""
    return _DATA_DIR / f"{source}_context.json"


# ── Context writing ────────────────────────────────────────────────────────────

def _write_context(payload: dict) -> None:
    """Write the incoming context payload to {source}_context.json.

    Each source file is a flat dict with no nesting or cross-source prefixes.
    An ``_updated_at`` timestamp is injected automatically.
    """
    source = payload.get("source", "unknown")
    now = datetime.now().isoformat()

    # Build flat context — drop internal underscore keys from the payload so we
    # only store clean fields, then add our own metadata.
    context: dict = {
        key: value
        for key, value in payload.items()
        if not key.startswith("_")
    }
    context["_updated_at"] = now

    context_file = _context_file(source)
    tmp = context_file.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(context_file)
        log.info(
            "Context written to %s (source=%s, ticket=%s)",
            context_file, source, payload.get("ticket_number"),
        )
    except OSError as e:
        log.error("Failed to write context file: %s", e)
        raise


# ── Time tracking ──────────────────────────────────────────────────────────────
# 
# Structure (date-based):
# {
#   "entries": {
#     "2026-02-22": {
#       "12345": {"total_seconds": 6000, "source": "freshdesk", "last_seen": "..."},
#       "12346": {"total_seconds": 3000, "source": "freshdesk", "last_seen": "..."}
#     },
#     "2026-02-21": {
#       "12345": {"total_seconds": 1000, "source": "freshdesk", "last_seen": "..."}
#     }
#   },
#   "_active": {"ticket_number": "12345", "source": "freshdesk", "started_at": "..."}
# }

# Time tracking cutoff (don't track after this time)
TRACKING_CUTOFF_HOUR = 17  # 5 PM
TRACKING_CUTOFF_MINUTE = 50  # 5:50 PM


def _is_workstation_locked() -> bool:
    """Check if the Windows workstation is locked.
    
    Returns True if locked, False if unlocked or if detection fails.
    """
    if sys.platform != "win32":
        return False
    
    try:
        import ctypes
        from ctypes import wintypes
        
        user32 = ctypes.windll.user32
        
        # Method 1: Check for the Winlogon desktop (most reliable)
        # GetForegroundWindow returns NULL when locked
        hwnd = user32.GetForegroundWindow()
        if hwnd == 0:
            return True
        
        # Method 2: Check the input desktop name
        # When locked, the input desktop is "Winlogon" instead of "Default"
        # This requires more complex API calls, so we'll use a simpler approach
        
        # Method 3: OpenInputDesktop fails when workstation is locked
        DESKTOP_SWITCHDESKTOP = 0x0100
        hdesk = user32.OpenInputDesktop(0, False, DESKTOP_SWITCHDESKTOP)
        if hdesk == 0:
            # Failed to open input desktop - likely locked
            return True
        
        # Successfully opened desktop - not locked
        user32.CloseDesktop(hdesk)
        return False
        
    except Exception as e:
        log.debug("Lock detection failed: %s", e)
        return False  # Assume not locked if we can't detect


def _is_past_tracking_cutoff() -> bool:
    """Check if current time is past the tracking cutoff (5:50 PM)."""
    now = datetime.now()
    return (now.hour > TRACKING_CUTOFF_HOUR or 
            (now.hour == TRACKING_CUTOFF_HOUR and now.minute >= TRACKING_CUTOFF_MINUTE))


def _should_track_time() -> bool:
    """Check if we should be tracking time right now.
    
    Returns False if:
    - Workstation is locked (AFK)
    - Current time is past 5:50 PM (shift ended)
    """
    if _is_workstation_locked():
        log.debug("Workstation locked — not tracking time")
        return False
    
    if _is_past_tracking_cutoff():
        log.debug("Past tracking cutoff (5:50 PM) — not tracking time")
        return False
    
    return True

def _load_time_tracking() -> dict:
    """Load time_tracking.json, returning an empty structure if absent/corrupt."""
    if TIME_TRACKING_FILE.exists():
        try:
            data = json.loads(TIME_TRACKING_FILE.read_text(encoding="utf-8"))
            # Migrate old format if needed
            if "tickets" in data and "entries" not in data:
                data = _migrate_time_tracking(data)
            return data
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read time_tracking.json: %s", e)
    return {"entries": {}, "_active": None}


def _migrate_time_tracking(old_data: dict) -> dict:
    """Migrate from old flat format to date-based format."""
    today = datetime.now().strftime("%Y-%m-%d")
    new_data = {"entries": {today: {}}, "_active": old_data.get("_active")}
    
    old_tickets = old_data.get("tickets", {})
    for ticket_num, info in old_tickets.items():
        new_data["entries"][today][ticket_num] = info
    
    log.info("Migrated time_tracking.json to date-based format (%d tickets)", len(old_tickets))
    return new_data


def _save_time_tracking(data: dict) -> None:
    """Atomically write time_tracking.json."""
    tmp = TIME_TRACKING_FILE.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(TIME_TRACKING_FILE)
        log.debug("Time tracking written to %s", TIME_TRACKING_FILE)
    except OSError as e:
        log.error("Failed to write time_tracking.json: %s", e)
        raise


def _update_time_tracking(payload: dict) -> None:
    """Update time_tracking.json based on incoming context payload.

    Time is tracked per-date — same ticket on different days = separate entries.
    
    Time is NOT accumulated if:
    - Workstation is locked (AFK detection)
    - Current time is past 5:50 PM (shift ended)
    
    Logic:
    - If there's a currently active ticket, accumulate elapsed seconds for TODAY.
    - If the same ticket is still active, update last_seen but keep started_at.
    - If a new ticket (or no ticket) arrives, finalize the old entry and set new _active.
    """
    data = _load_time_tracking()
    now_str = datetime.now().isoformat()
    now_dt = datetime.now()
    today = now_dt.strftime("%Y-%m-%d")

    source = payload.get("source", "unknown")
    incoming_ticket = payload.get("ticket_number")  # May be None

    active = data.get("_active")  # None or dict
    
    # Check if we should be tracking time (not locked, not past 5:50 PM)
    should_track = _should_track_time()
    
    # Ensure today's entry dict exists
    if today not in data.get("entries", {}):
        data.setdefault("entries", {})[today] = {}

    # ── Finalize the previously active ticket (if any) ─────────────────────────
    if active:
        prev_ticket = active.get("ticket_number")
        prev_source = active.get("source", "unknown")
        started_at_str = active.get("started_at")

        if prev_ticket and started_at_str:
            try:
                started_at_dt = datetime.fromisoformat(started_at_str)
                elapsed = (now_dt - started_at_dt).total_seconds()
            except (ValueError, TypeError):
                elapsed = 0.0

            same_ticket = (
                incoming_ticket is not None
                and incoming_ticket == prev_ticket
                and source == prev_source
            )

            if same_ticket:
                # Same ticket still open
                # Only accumulate time if we should be tracking
                if should_track and elapsed > 0:
                    today_entries = data["entries"].setdefault(today, {})
                    ticket_entry = today_entries.setdefault(prev_ticket, {
                        "total_seconds": 0,
                        "source": prev_source,
                        "last_seen": now_str,
                    })
                    ticket_entry["total_seconds"] = ticket_entry.get("total_seconds", 0) + elapsed
                    ticket_entry["last_seen"] = now_str
                    log.debug(
                        "Same ticket %s still active; accumulated %.1fs (today total=%.1fs)",
                        prev_ticket, elapsed, ticket_entry["total_seconds"],
                    )
                else:
                    log.debug(
                        "Same ticket %s still active; NOT tracking (locked/after hours), skipped %.1fs",
                        prev_ticket, elapsed,
                    )
                
                # Reset started_at to now so we don't double-count on next update.
                active["started_at"] = now_str
                data["_active"] = active

                _save_time_tracking(data)
                return  # Nothing more to do

            else:
                # Different ticket (or ticket cleared) — finalize previous entry for TODAY
                # Only accumulate if we should be tracking
                if should_track and elapsed > 0:
                    today_entries = data["entries"].setdefault(today, {})
                    ticket_entry = today_entries.setdefault(prev_ticket, {
                        "total_seconds": 0,
                        "source": prev_source,
                        "last_seen": now_str,
                    })
                    ticket_entry["total_seconds"] = ticket_entry.get("total_seconds", 0) + elapsed
                    ticket_entry["last_seen"] = now_str
                    log.info(
                        "Finalized ticket %s (source=%s): added %.1fs, today total=%.1fs",
                        prev_ticket, prev_source, elapsed, ticket_entry["total_seconds"],
                    )
                else:
                    log.debug(
                        "Finalized ticket %s (source=%s): NOT tracking (locked/after hours), skipped %.1fs",
                        prev_ticket, prev_source, elapsed,
                    )

    # ── Set the new active ticket ──────────────────────────────────────────────
    if incoming_ticket:
        # Ensure an entry exists for today
        today_entries = data["entries"].setdefault(today, {})
        today_entries.setdefault(incoming_ticket, {
            "total_seconds": 0,
            "source": source,
            "last_seen": now_str,
        })
        data["_active"] = {
            "ticket_number": incoming_ticket,
            "source": source,
            "started_at": now_str,
        }
        log.info("Active ticket set: %s (source=%s)", incoming_ticket, source)
    else:
        # No ticket in this payload — clear active.
        data["_active"] = None
        log.debug("No ticket_number in payload; active cleared.")

    _save_time_tracking(data)


# ── Native messaging I/O ───────────────────────────────────────────────────────

def _read_message(stdin) -> dict | None:
    """Read one length-prefixed JSON message from Chrome.

    Returns the parsed dict, or None on EOF/error.
    """
    # Read 4-byte little-endian length prefix
    try:
        raw_len = stdin.read(4)
    except (OSError, ValueError) as e:
        # Pipe broken or closed
        log.info("stdin read error (pipe closed?): %s", e)
        return None
    
    if not raw_len or len(raw_len) < 4:
        log.info("stdin closed (EOF on length read, got %d bytes)", len(raw_len) if raw_len else 0)
        return None

    msg_len = struct.unpack("<I", raw_len)[0]

    if msg_len == 0:
        return {}

    if msg_len > 1024 * 1024:  # Sanity check: max 1 MB
        log.error("Message too large: %d bytes — ignoring", msg_len)
        stdin.read(msg_len)  # Drain
        return None

    raw_msg = stdin.read(msg_len)
    if len(raw_msg) < msg_len:
        log.warning("Short read: expected %d bytes, got %d", msg_len, len(raw_msg))
        return None

    try:
        return json.loads(raw_msg.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error("Failed to decode message: %s", e)
        return None


def _write_message(stdout, payload: dict) -> None:
    """Write one length-prefixed JSON message to Chrome."""
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    length_prefix = struct.pack("<I", len(encoded))
    stdout.write(length_prefix)
    stdout.write(encoded)
    stdout.flush()


# ── Parent process watchdog ────────────────────────────────────────────────────

_shutdown_flag = threading.Event()


def _get_parent_pid() -> int | None:
    """Get the parent process ID."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            
            kernel32 = ctypes.windll.kernel32
            
            # Get current process handle
            current_process = kernel32.GetCurrentProcess()
            
            # PROCESS_BASIC_INFORMATION structure
            class PROCESS_BASIC_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("Reserved1", ctypes.c_void_p),
                    ("PebBaseAddress", ctypes.c_void_p),
                    ("Reserved2", ctypes.c_void_p * 2),
                    ("UniqueProcessId", ctypes.POINTER(ctypes.c_ulong)),
                    ("InheritedFromUniqueProcessId", ctypes.POINTER(ctypes.c_ulong)),
                ]
            
            # Simpler approach: use os.getppid() which works on Python 3.2+
            return os.getppid()
        else:
            return os.getppid()
    except Exception as e:
        log.warning("Could not get parent PID: %s", e)
        return None


def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is still running."""
    if pid is None:
        return True  # Assume alive if we can't check
    
    try:
        if sys.platform == "win32":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            SYNCHRONIZE = 0x00100000
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            
            handle = kernel32.OpenProcess(
                SYNCHRONIZE | PROCESS_QUERY_LIMITED_INFORMATION, 
                False, 
                pid
            )
            
            if handle == 0:
                # Process doesn't exist or can't access
                return False
            
            # Check if process has exited
            WAIT_TIMEOUT = 258
            result = kernel32.WaitForSingleObject(handle, 0)
            kernel32.CloseHandle(handle)
            
            return result == WAIT_TIMEOUT  # Still running
        else:
            os.kill(pid, 0)  # Doesn't actually kill, just checks existence
            return True
    except (OSError, ProcessLookupError):
        return False
    except Exception as e:
        log.warning("Error checking parent process: %s", e)
        return True  # Assume alive on error


def _is_kodex_running() -> bool:
    """Check if Kodex app is running by checking its PID file."""
    pid_file = _DATA_DIR / "kodex.pid"
    
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        return _is_process_alive(pid)
    except (ValueError, OSError) as e:
        log.debug("Error reading Kodex PID file: %s", e)
        return False


def _watchdog_thread(parent_pid: int | None, check_interval: float = 2.0) -> None:
    """Background thread that monitors parent process AND Kodex app."""
    log.debug("Watchdog started, monitoring parent PID %s and Kodex PID file", parent_pid)
    
    while not _shutdown_flag.is_set():
        # Check if Chrome (parent) is gone
        if parent_pid and not _is_process_alive(parent_pid):
            log.info("Parent process (PID %d) is gone. Triggering shutdown.", parent_pid)
            _shutdown_flag.set()
            os._exit(0)
        
        # Check if Kodex app is running
        if not _is_kodex_running():
            log.info("Kodex app is not running. Triggering shutdown.")
            _shutdown_flag.set()
            os._exit(0)
        
        time.sleep(check_interval)


# ── Main loop ──────────────────────────────────────────────────────────────────

def run() -> None:
    """Main native messaging event loop.

    Reads messages from Chrome, processes them, and writes responses.
    Exits cleanly when Chrome closes the pipe.
    """
    log.info("Kodex native messaging host started (PID %d)", os.getpid())
    log.info("Data directory: %s", _DATA_DIR)

    # Windows requires explicit binary mode on stdin/stdout
    if sys.platform == "win32":
        import msvcrt
        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
        log.debug("Windows: set stdin/stdout to binary mode")

    # Start watchdog thread (monitors Chrome parent AND Kodex app)
    parent_pid = _get_parent_pid()
    log.info("Parent PID: %s — starting watchdog (also monitoring Kodex PID file)", parent_pid)
    watchdog = threading.Thread(
        target=_watchdog_thread, 
        args=(parent_pid,), 
        daemon=True
    )
    watchdog.start()

    # Use raw binary I/O — critical for native messaging protocol correctness.
    # DO NOT wrap in TextIOWrapper; the 4-byte length prefix is binary.
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    while True:
        try:
            message = _read_message(stdin)
        except Exception as e:
            log.error("Unexpected error reading message: %s", e, exc_info=True)
            break

        if message is None:
            # EOF — Chrome closed the connection
            log.info("Chrome closed the connection. Exiting.")
            break

        log.debug("Received message: %s", message)

        # Process the message
        try:
            if not message:
                # Empty ping — just acknowledge
                _write_message(stdout, {"success": True, "pong": True})
                continue

            source = message.get("source", "unknown")
            ticket = message.get("ticket_number")
            log.info("Processing context: source=%s ticket=%s", source, ticket)

            _write_context(message)
            _update_time_tracking(message)

            _write_message(stdout, {
                "success": True,
                "source": source,
                "ticket_number": ticket,
                "written_to": str(_context_file(source)),
            })

        except BrokenPipeError:
            log.info("Broken pipe — Chrome closed the connection. Exiting.")
            break
        except Exception as e:
            log.error("Error processing message: %s", e, exc_info=True)
            try:
                _write_message(stdout, {"success": False, "error": str(e)})
            except BrokenPipeError:
                log.info("Broken pipe on error response — exiting.")
                break
            except Exception:
                pass  # Can't write response — just continue

    log.info("Native messaging host exiting.")


def _cleanup():
    """Cleanup handler for atexit."""
    log.info("Cleanup: native messaging host shutting down (PID %d)", os.getpid())
    logging.shutdown()


def _signal_handler(signum, frame):
    """Handle termination signals."""
    log.info("Received signal %d, exiting.", signum)
    sys.exit(0)


def main() -> None:
    """Entry point for `python -m kodex_py.native_messaging`."""
    # Register cleanup
    atexit.register(_cleanup)
    
    # Handle termination signals
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    if sys.platform != "win32":
        signal.signal(signal.SIGHUP, _signal_handler)
    
    try:
        run()
    except KeyboardInterrupt:
        log.info("Interrupted by user.")
    except Exception as e:
        log.critical("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        log.info("Main function exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()
