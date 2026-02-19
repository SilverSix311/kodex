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

def _load_time_tracking() -> dict:
    """Load time_tracking.json, returning an empty structure if absent/corrupt."""
    if TIME_TRACKING_FILE.exists():
        try:
            return json.loads(TIME_TRACKING_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read time_tracking.json: %s", e)
    return {"tickets": {}, "_active": None}


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

    Logic:
    - If there's a currently active ticket, accumulate elapsed seconds.
    - If the same ticket is still active, update last_seen but keep started_at.
    - If a new ticket (or no ticket) arrives, finalize the old entry and set new _active.
    """
    data = _load_time_tracking()
    now_str = datetime.now().isoformat()
    now_dt = datetime.now()

    source = payload.get("source", "unknown")
    incoming_ticket = payload.get("ticket_number")  # May be None

    active = data.get("_active")  # None or dict

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
                # Same ticket still open — do NOT reset started_at; just update last_seen.
                ticket_entry = data["tickets"].setdefault(prev_ticket, {
                    "total_seconds": 0,
                    "source": prev_source,
                    "last_seen": now_str,
                })
                # Add only the elapsed portion up to now, then restart the clock
                # so the next update doesn't double-count.
                ticket_entry["total_seconds"] = ticket_entry.get("total_seconds", 0) + elapsed
                ticket_entry["last_seen"] = now_str
                # Reset started_at to now so we don't double-count on next update.
                active["started_at"] = now_str
                data["_active"] = active

                log.debug(
                    "Same ticket %s still active; accumulated %.1fs (total=%.1fs)",
                    prev_ticket, elapsed, ticket_entry["total_seconds"],
                )

                _save_time_tracking(data)
                return  # Nothing more to do

            else:
                # Different ticket (or ticket cleared) — finalize previous entry.
                ticket_entry = data["tickets"].setdefault(prev_ticket, {
                    "total_seconds": 0,
                    "source": prev_source,
                    "last_seen": now_str,
                })
                ticket_entry["total_seconds"] = ticket_entry.get("total_seconds", 0) + elapsed
                ticket_entry["last_seen"] = now_str
                log.info(
                    "Finalized ticket %s (source=%s): added %.1fs, total=%.1fs",
                    prev_ticket, prev_source, elapsed, ticket_entry["total_seconds"],
                )

    # ── Set the new active ticket ──────────────────────────────────────────────
    if incoming_ticket:
        # Ensure an entry exists in tickets
        data["tickets"].setdefault(incoming_ticket, {
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
